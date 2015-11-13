__FILENAME__ = build-site
#!/usr/bin/env python
# (c) 2012, Michael DeHaan <michael.dehaan@gmail.com>
#
# This file is part of the Ansible Documentation
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

__docformat__ = 'restructuredtext'

import os
import sys
import traceback
try:
    from sphinx.application import Sphinx
except ImportError:
    print "#################################"
    print "Dependency missing: Python Sphinx"
    print "#################################"
    sys.exit(1)
import os


class SphinxBuilder(object):
    """
    Creates HTML documentation using Sphinx.
    """

    def __init__(self):
        """
        Run the DocCommand.
        """
        print "Creating html documentation ..."

        try:
            buildername = 'html'

            outdir = os.path.abspath(os.path.join(os.getcwd(), "htmlout"))
            # Create the output directory if it doesn't exist
            if not os.access(outdir, os.F_OK):
                os.mkdir(outdir)

            doctreedir = os.path.join('./', '.doctrees')

            confdir = os.path.abspath('./')
            srcdir = os.path.abspath('rst')
            freshenv = True

            # Create the builder
            app = Sphinx(srcdir,
                              confdir,
                              outdir,
                              doctreedir,
                              buildername,
                              {},
                              sys.stdout,
                              sys.stderr,
                              freshenv)

            app.builder.build_all()

        except ImportError, ie:
            traceback.print_exc()
        except Exception, ex:
            print >> sys.stderr, "FAIL! exiting ... (%s)" % ex

    def build_docs(self):
        self.app.builder.build_all()


def build_rst_docs():
    docgen = SphinxBuilder()

if __name__ == '__main__':
    if '-h' in sys.argv or '--help' in sys.argv:
        print "This script builds the html documentation from rst/asciidoc sources.\n"
        print "    Run 'make docs' to build everything."
        print "    Run 'make viewdocs' to build and then preview in a web browser."
        sys.exit(0)

    # The 'htmldocs' make target will call this scrip twith the 'rst'
    # parameter' We don't need to run the 'htmlman' target then.
    if "rst" in sys.argv:
        build_rst_docs()
    else:
        # By default, preform the rst->html transformation and then
        # the asciidoc->html trasnformation
        build_rst_docs()

    if "view" in sys.argv:
        import webbrowser
        if not webbrowser.open('htmlout/index.html'):
            print >> sys.stderr, "Could not open on your webbrowser."

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# documentation build configuration file, created by
# sphinx-quickstart on Sat Sep 27 13:23:22 2008-2009.
#
# This file is execfile()d with the current directory set to its
# containing dir.
#
# The contents of this file are pickled, so don't put values in the namespace
# that aren't pickleable (module imports are okay, they're removed
# automatically).
#
# All configuration values have a default value; values that are commented out
# serve to show the default value.

import sys
import os

# pip install sphinx_rtd_theme
#import sphinx_rtd_theme
#html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]

# If your extensions are in another directory, add it here. If the directory
# is relative to the documentation root, use os.path.abspath to make it
# absolute, like shown here.
#sys.path.append(os.path.abspath('some/directory'))
#
sys.path.insert(0, os.path.join('ansible', 'lib'))
sys.path.append(os.path.abspath('_themes'))

VERSION='0.01'
AUTHOR='Ansible, Inc'


# General configuration
# ---------------------

# Add any Sphinx extension module names here, as strings.
# They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc']

# Later on, add 'sphinx.ext.viewcode' to the list if you want to have
# colorized code generated too for references.


# Add any paths that contain templates here, relative to this directory.
templates_path = ['.templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

# General substitutions.
project = 'Ansible Documentation'
copyright = "2013 Ansible, Inc"

# The default replacements for |version| and |release|, also used in various
# other places throughout the built documents.
#
# The short X.Y version.
version = VERSION
# The full version, including alpha/beta/rc tags.
release = VERSION

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
today_fmt = '%B %d, %Y'

# List of documents that shouldn't be included in the build.
#unused_docs = []

# List of directories, relative to source directories, that shouldn't be
# searched for source files.
#exclude_dirs = []

# A list of glob-style patterns that should be excluded when looking
# for source files.
exclude_patterns = ['modules']

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


# Options for HTML output
# -----------------------

html_theme_path = ['_themes']
html_theme = 'srtd'
html_short_title = 'Ansible Documentation'

# The style sheet to use for HTML and HTML Help pages. A file of that name
# must exist either in Sphinx' static/ path, or in one of the custom paths
# given in html_static_path.
#html_style = 'solar.css'

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
html_title = 'Ansible Documentation'

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (within the static path) to place at the top of
# the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = 'favicon.ico'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
#html_static_path = ['.static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_use_modindex = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, the reST sources are included in the HTML build as _sources/<name>.
html_copy_source = False

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# If nonempty, this is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = ''

# Output file base name for HTML help builder.
htmlhelp_basename = 'Poseidodoc'


# Options for LaTeX output
# ------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, document class
# [howto/manual]).
latex_documents = [
  ('index', 'ansible.tex', 'Ansible 1.2 Documentation',
   AUTHOR, 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_use_modindex = True

autoclass_content = 'both'

########NEW FILE########
__FILENAME__ = uptime
#!/usr/bin/python
# (c) 2012, Michael DeHaan <michael.dehaan@gmail.com>
# example of getting the uptime of all hosts, 10 at a time

import ansible.runner
import sys

# construct the ansible runner and execute on all hosts
results = ansible.runner.Runner(
    pattern='*', forks=10,
    module_name='command', module_args='/usr/bin/uptime',
).run()

if results is None:
   print "No hosts found"
   sys.exit(1)

print "UP ***********"
for (hostname, result) in results['contacted'].items():
    if not 'failed' in result:
        print "%s >>> %s" % (hostname, result['stdout'])

print "FAILED *******"
for (hostname, result) in results['contacted'].items():
    if 'failed' in result:
        print "%s >>> %s" % (hostname, result['msg'])

print "DOWN *********"
for (hostname, result) in results['dark'].items():
    print "%s >>> %s" % (hostname, result)


########NEW FILE########
__FILENAME__ = yaml_to_ini
# (c) 2012, Michael DeHaan <michael.dehaan@gmail.com>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

import ansible.constants as C
from ansible.inventory.host import Host
from ansible.inventory.group import Group
from ansible import errors
from ansible import utils
import os
import yaml
import sys

class InventoryParserYaml(object):
    ''' Host inventory parser for ansible '''

    def __init__(self, filename=C.DEFAULT_HOST_LIST):

        sys.stderr.write("WARNING: YAML inventory files are deprecated in 0.6 and will be removed in 0.7, to migrate" +
            " download and run https://github.com/ansible/ansible/blob/devel/examples/scripts/yaml_to_ini.py\n")

        fh = open(filename)
        data = fh.read()
        fh.close()
        self._hosts = {}
        self._parse(data)

    def _make_host(self, hostname):

        if hostname in self._hosts:
            return self._hosts[hostname]
        else:
            host = Host(hostname)
            self._hosts[hostname] = host
            return host

    # see file 'test/yaml_hosts' for syntax

    def _parse(self, data):
        # FIXME: refactor into subfunctions

        all = Group('all')

        ungrouped = Group('ungrouped')
        all.add_child_group(ungrouped)

        self.groups = dict(all=all, ungrouped=ungrouped)
        grouped_hosts = []

        yaml = utils.parse_yaml(data)

        # first add all groups
        for item in yaml:
            if type(item) == dict and 'group' in item:
                group = Group(item['group'])

                for subresult in item.get('hosts',[]):

                    if type(subresult) in [ str, unicode ]:
                        host = self._make_host(subresult)
                        group.add_host(host)
                        grouped_hosts.append(host)
                    elif type(subresult) == dict:
                        host = self._make_host(subresult['host'])
                        vars = subresult.get('vars',{})
                        if type(vars) == list:
                            for subitem in vars:
                                for (k,v) in subitem.items():
                                    host.set_variable(k,v)
                        elif type(vars) == dict:
                            for (k,v) in subresult.get('vars',{}).items():
                                host.set_variable(k,v)
                        else:
                            raise errors.AnsibleError("unexpected type for variable")
                        group.add_host(host)
                        grouped_hosts.append(host)

                vars = item.get('vars',{})
                if type(vars) == dict:
                    for (k,v) in item.get('vars',{}).items():
                        group.set_variable(k,v)
                elif type(vars) == list:
                    for subitem in vars:
                        if type(subitem) != dict:
                            raise errors.AnsibleError("expected a dictionary")
                        for (k,v) in subitem.items():
                            group.set_variable(k,v)

                self.groups[group.name] = group
                all.add_child_group(group)

        # add host definitions
        for item in yaml:
            if type(item) in [ str, unicode ]:
                host = self._make_host(item)
                if host not in grouped_hosts:
                    ungrouped.add_host(host)

            elif type(item) == dict and 'host' in item:
                host = self._make_host(item['host'])

                vars = item.get('vars', {})
                if type(vars)==list:
                    varlist, vars = vars, {}
                    for subitem in varlist:
                        vars.update(subitem)
                for (k,v) in vars.items():
                    host.set_variable(k,v)

                groups = item.get('groups', {})
                if type(groups) in [ str, unicode ]:
                    groups = [ groups ]
                if type(groups)==list:
                    for subitem in groups:
                        if subitem in self.groups:
                            group = self.groups[subitem]
                        else:
                            group = Group(subitem)
                            self.groups[group.name] = group
                            all.add_child_group(group)
                        group.add_host(host)
                        grouped_hosts.append(host)

                if host not in grouped_hosts:
                    ungrouped.add_host(host)

        # make sure ungrouped.hosts is the complement of grouped_hosts
        ungrouped_hosts = [host for host in ungrouped.hosts if host not in grouped_hosts]

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print "usage: yaml_to_ini.py /path/to/ansible/hosts"
        sys.exit(1)

    result = ""

    original = sys.argv[1]
    yamlp = InventoryParserYaml(filename=sys.argv[1])
    dirname = os.path.dirname(original)

    group_names = [ g.name for g in yamlp.groups.values() ]

    for group_name in sorted(group_names):

        record = yamlp.groups[group_name]

        if group_name == 'all':
            continue

        hosts = record.hosts
        result = result + "[%s]\n" % record.name
        for h in hosts:
            result = result + "%s\n" % h.name
        result = result + "\n"

        groupfiledir = os.path.join(dirname, "group_vars")
        if not os.path.exists(groupfiledir):
            print "* creating: %s" % groupfiledir
            os.makedirs(groupfiledir)
        groupfile = os.path.join(groupfiledir, group_name)
        print "* writing group variables for %s into %s" % (group_name, groupfile)
        groupfh = open(groupfile, 'w')
        groupfh.write(yaml.dump(record.get_variables()))
        groupfh.close()

    for (host_name, host_record) in yamlp._hosts.iteritems():
        hostfiledir = os.path.join(dirname, "host_vars")
        if not os.path.exists(hostfiledir):
            print "* creating: %s" % hostfiledir
            os.makedirs(hostfiledir)
        hostfile = os.path.join(hostfiledir, host_record.name)
        print "* writing host variables for %s into %s" % (host_record.name, hostfile)
        hostfh = open(hostfile, 'w')
        hostfh.write(yaml.dump(host_record.get_variables()))
        hostfh.close()


    # also need to keep a hash of variables per each host
    # and variables per each group
    # and write those to disk

    newfilepath = os.path.join(dirname, "hosts.new")
    fdh = open(newfilepath, 'w')
    fdh.write(result)
    fdh.close()

    print "* COMPLETE: review your new inventory file and replace your original when ready"
    print "*           new inventory file saved as %s" % newfilepath
    print "*           edit group specific variables in %s/group_vars/" % dirname
    print "*           edit host specific variables in %s/host_vars/" % dirname

    # now need to write this to disk as (oldname).new
    # and inform the user

########NEW FILE########
__FILENAME__ = get_library
#!/usr/bin/env python

# (c) 2014, Will Thames <will@thames.id.au>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.
#

import ansible.constants as C
import sys

def main():
    print C.DEFAULT_MODULE_PATH
    return 0

if __name__ == '__main__':
    sys.exit(main())

########NEW FILE########
__FILENAME__ = module_formatter
#!/usr/bin/env python
# (c) 2012, Jan-Piet Mens <jpmens () gmail.com>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.
#

import os
import glob
import sys
import yaml
import codecs
import json
import ast
import re
import optparse
import time
import datetime
import subprocess
import cgi
from jinja2 import Environment, FileSystemLoader

import ansible.utils
import ansible.utils.module_docs as module_docs

#####################################################################################
# constants and paths

# if a module is added in a version of Ansible older than this, don't print the version added information
# in the module documentation because everyone is assumed to be running something newer than this already.
TO_OLD_TO_BE_NOTABLE = 1.0

# Get parent directory of the directory this script lives in
MODULEDIR=os.path.abspath(os.path.join(
    os.path.dirname(os.path.realpath(__file__)), os.pardir, 'library'
))

# The name of the DOCUMENTATION template
EXAMPLE_YAML=os.path.abspath(os.path.join(
    os.path.dirname(os.path.realpath(__file__)), os.pardir, 'examples', 'DOCUMENTATION.yml'
))

_ITALIC = re.compile(r"I\(([^)]+)\)")
_BOLD   = re.compile(r"B\(([^)]+)\)")
_MODULE = re.compile(r"M\(([^)]+)\)")
_URL    = re.compile(r"U\(([^)]+)\)")
_CONST  = re.compile(r"C\(([^)]+)\)")

#####################################################################################

def rst_ify(text):
    ''' convert symbols like I(this is in italics) to valid restructured text '''

    t = _ITALIC.sub(r'*' + r"\1" + r"*", text)
    t = _BOLD.sub(r'**' + r"\1" + r"**", t)
    t = _MODULE.sub(r'``' + r"\1" + r"``", t)
    t = _URL.sub(r"\1", t)
    t = _CONST.sub(r'``' + r"\1" + r"``", t)

    return t

#####################################################################################

def html_ify(text):
    ''' convert symbols like I(this is in italics) to valid HTML '''

    t = cgi.escape(text)
    t = _ITALIC.sub("<em>" + r"\1" + "</em>", t)
    t = _BOLD.sub("<b>" + r"\1" + "</b>", t)
    t = _MODULE.sub("<span class='module'>" + r"\1" + "</span>", t)
    t = _URL.sub("<a href='" + r"\1" + "'>" + r"\1" + "</a>", t)
    t = _CONST.sub("<code>" + r"\1" + "</code>", t)

    return t


#####################################################################################

def rst_fmt(text, fmt):
    ''' helper for Jinja2 to do format strings '''

    return fmt % (text)

#####################################################################################

def rst_xline(width, char="="):
    ''' return a restructured text line of a given length '''

    return char * width

#####################################################################################

def write_data(text, options, outputname, module):
    ''' dumps module output to a file or the screen, as requested '''

    if options.output_dir is not None:
        f = open(os.path.join(options.output_dir, outputname % module), 'w')
        f.write(text.encode('utf-8'))
        f.close()
    else:
        print text

#####################################################################################

def list_modules(module_dir):
    ''' returns a hash of categories, each category being a hash of module names to file paths '''

    categories = dict(all=dict())
    files = glob.glob("%s/*" % module_dir)
    for d in files:
        if os.path.isdir(d):
            files2 = glob.glob("%s/*" % d)
            for f in files2:
                tokens = f.split("/")
                module = tokens[-1]
                category = tokens[-2]
                if not category in categories:
                    categories[category] = {}
                categories[category][module] = f
                categories['all'][module] = f
    return categories

#####################################################################################

def generate_parser():
    ''' generate an optparse parser '''

    p = optparse.OptionParser(
        version='%prog 1.0',
        usage='usage: %prog [options] arg1 arg2',
        description='Generate module documentation from metadata',
    )

    p.add_option("-A", "--ansible-version", action="store", dest="ansible_version", default="unknown", help="Ansible version number")
    p.add_option("-M", "--module-dir", action="store", dest="module_dir", default=MODULEDIR, help="Ansible library path")
    p.add_option("-T", "--template-dir", action="store", dest="template_dir", default="hacking/templates", help="directory containing Jinja2 templates")
    p.add_option("-t", "--type", action='store', dest='type', choices=['rst'], default='rst', help="Document type")
    p.add_option("-v", "--verbose", action='store_true', default=False, help="Verbose")
    p.add_option("-o", "--output-dir", action="store", dest="output_dir", default=None, help="Output directory for module files")
    p.add_option("-I", "--includes-file", action="store", dest="includes_file", default=None, help="Create a file containing list of processed modules")
    p.add_option('-V', action='version', help='Show version number and exit')
    return p

#####################################################################################

def jinja2_environment(template_dir, typ):

    env = Environment(loader=FileSystemLoader(template_dir),
        variable_start_string="@{",
        variable_end_string="}@",
        trim_blocks=True,
    )
    env.globals['xline'] = rst_xline

    if typ == 'rst':
        env.filters['convert_symbols_to_format'] = rst_ify
        env.filters['html_ify'] = html_ify
        env.filters['fmt'] = rst_fmt
        env.filters['xline'] = rst_xline
        template = env.get_template('rst.j2')
        outputname = "%s_module.rst"
    else:
        raise Exception("unknown module format type: %s" % typ)

    return env, template, outputname

#####################################################################################

def process_module(module, options, env, template, outputname, module_map):

    print "rendering: %s" % module

    fname = module_map[module]

    # ignore files with extensions
    if "." in os.path.basename(fname):
        return

    # use ansible core library to parse out doc metadata YAML and plaintext examples
    doc, examples = ansible.utils.module_docs.get_docstring(fname, verbose=options.verbose)

    # crash if module is missing documentation and not explicitly hidden from docs index
    if doc is None and module not in ansible.utils.module_docs.BLACKLIST_MODULES:
        sys.stderr.write("*** ERROR: CORE MODULE MISSING DOCUMENTATION: %s, %s ***\n" % (fname, module))
        sys.exit(1)
    if doc is None:
        return "SKIPPED"

    all_keys = []

    if not 'version_added' in doc:
        sys.stderr.write("*** ERROR: missing version_added in: %s ***\n" % module)
        sys.exit(1)

    added = 0
    if doc['version_added'] == 'historical':
        del doc['version_added']
    else:
        added = doc['version_added']

    # don't show version added information if it's too old to be called out
    if added:
        added_tokens = str(added).split(".")
        added = added_tokens[0] + "." + added_tokens[1]
        added_float = float(added)
        if added and added_float < TO_OLD_TO_BE_NOTABLE:
            del doc['version_added']

    for (k,v) in doc['options'].iteritems():
        all_keys.append(k)
    all_keys = sorted(all_keys)
    doc['option_keys'] = all_keys

    doc['filename']         = fname
    doc['docuri']           = doc['module'].replace('_', '-')
    doc['now_date']         = datetime.date.today().strftime('%Y-%m-%d')
    doc['ansible_version']  = options.ansible_version
    doc['plainexamples']    = examples  #plain text

    # here is where we build the table of contents...

    text = template.render(doc)
    write_data(text, options, outputname, module)

#####################################################################################

def process_category(category, categories, options, env, template, outputname):

    module_map = categories[category]

    category_file_path = os.path.join(options.output_dir, "list_of_%s_modules.rst" % category)
    category_file = open(category_file_path, "w")
    print "*** recording category %s in %s ***" % (category, category_file_path)

    # TODO: start a new category file

    category = category.replace("_"," ")
    category = category.title()

    modules = module_map.keys()
    modules.sort()

    category_header = "%s Modules" % (category.title())
    underscores = "`" * len(category_header)

    category_file.write("""\
%s
%s

.. toctree::
   :maxdepth: 1

""" % (category_header, underscores))

    for module in modules:
        result = process_module(module, options, env, template, outputname, module_map)
        if result != "SKIPPED":
            category_file.write("   %s_module\n" % module)


    category_file.close()

    # TODO: end a new category file

#####################################################################################

def validate_options(options):
    ''' validate option parser options '''

    if not options.module_dir:
        print >>sys.stderr, "--module-dir is required"
        sys.exit(1)
    if not os.path.exists(options.module_dir):
        print >>sys.stderr, "--module-dir does not exist: %s" % options.module_dir
        sys.exit(1)
    if not options.template_dir:
        print "--template-dir must be specified"
        sys.exit(1)

#####################################################################################

def main():

    p = generate_parser()

    (options, args) = p.parse_args()
    validate_options(options)

    env, template, outputname = jinja2_environment(options.template_dir, options.type)

    categories = list_modules(options.module_dir)
    last_category = None
    category_names = categories.keys()
    category_names.sort()

    category_list_path = os.path.join(options.output_dir, "modules_by_category.rst")
    category_list_file = open(category_list_path, "w")
    category_list_file.write("Module Index\n")
    category_list_file.write("============\n")
    category_list_file.write("\n\n")
    category_list_file.write(".. toctree::\n")
    category_list_file.write("   :maxdepth: 1\n\n")

    for category in category_names:
        category_list_file.write("   list_of_%s_modules\n" % category)
        process_category(category, categories, options, env, template, outputname)

    category_list_file.close()

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = gce_tests
#!/usr/bin/env python
# Copyright 2013 Google Inc.
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

# This is a custom functional test script for the Google Compute Engine
# ansible modules.  In order to run these tests, you must:
# 1) Create a Google Cloud Platform account and enable the Google
#    Compute Engine service and billing
# 2) Download, install, and configure  'gcutil'
#    see [https://developers.google.com/compute/docs/gcutil/]
# 3) Convert your GCE Service Account private key from PKCS12 to PEM format
#    $ openssl pkcs12 -in pkey.pkcs12 -passin pass:notasecret \
#    > -nodes -nocerts | openssl rsa -out pkey.pem 
# 4) Make sure you have libcloud 0.13.3 or later installed.
# 5) Make sure you have a libcloud 'secrets.py' file in your PYTHONPATH
# 6) Set GCE_PARAMS and GCE_KEYWORD_PARMS in your 'secrets.py' file.
# 7) Set up a simple hosts file
#    $ echo 127.0.0.1 > ~/ansible_hosts
#    $ echo "export ANSIBLE_HOSTS='~/ansible_hosts'" >> ~/.bashrc
#    $ . ~/.bashrc
# 8) Set up your ansible 'hacking' environment
#    $ cd ~/ansible
#    $ . hacking/env-setup
#    $ export ANSIBLE_HOST_KEY_CHECKING=no
#    $ ansible all -m ping
# 9) Set your PROJECT variable below
# 10) Run and time the tests and log output, take ~30 minutes to run
#    $ time stdbuf -oL python test/gce_tests.py 2>&1 | tee log
#
# Last update: gcutil-1.11.0 and v1beta16

# Set this to your test Project ID
PROJECT="google.com:erjohnso"

# debugging
DEBUG=False   # lots of debugging output
VERBOSE=True  # on failure, display ansible command and expected/actual result

# location - note that some tests rely on the module's 'default'
# region/zone, which should match the settings below.
REGION="us-central1"
ZONE="%s-a" % REGION

# Peeking is a way to trigger looking at a specified set of resources
# before and/or after a test run.  The 'test_cases' data structure below
# has a few tests with 'peek_before' and 'peek_after'.  When those keys
# are set and PEEKING_ENABLED is True, then these steps will be executed
# to aid in debugging tests.  Normally, this is not needed.
PEEKING_ENABLED=False

# disks
DNAME="aaaaa-ansible-disk"
DNAME2="aaaaa-ansible-disk2"
DNAME6="aaaaa-ansible-inst6"
DNAME7="aaaaa-ansible-inst7"
USE_PD="true"
KERNEL="https://www.googleapis.com/compute/v1beta16/projects/google/global/kernels/gce-no-conn-track-v20130813"

# instances
INAME="aaaaa-ansible-inst"
INAME2="aaaaa-ansible-inst2"
INAME3="aaaaa-ansible-inst3"
INAME4="aaaaa-ansible-inst4"
INAME5="aaaaa-ansible-inst5"
INAME6="aaaaa-ansible-inst6"
INAME7="aaaaa-ansible-inst7"
TYPE="n1-standard-1"
IMAGE="https://www.googleapis.com/compute/v1beta16/projects/debian-cloud/global/images/debian-7-wheezy-v20131014"
NETWORK="default"
SCOPES="https://www.googleapis.com/auth/userinfo.email,https://www.googleapis.com/auth/compute,https://www.googleapis.com/auth/devstorage.full_control"

# networks / firewalls
NETWK1="ansible-network1"
NETWK2="ansible-network2"
NETWK3="ansible-network3"
CIDR1="10.240.16.0/24"
CIDR2="10.240.32.0/24"
CIDR3="10.240.64.0/24"
GW1="10.240.16.1"
GW2="10.240.32.1"
FW1="ansible-fwrule1"
FW2="ansible-fwrule2"
FW3="ansible-fwrule3"
FW4="ansible-fwrule4"

# load-balancer tests
HC1="ansible-hc1"
HC2="ansible-hc2"
HC3="ansible-hc3"
LB1="ansible-lb1"
LB2="ansible-lb2"

from commands import getstatusoutput as run
import sys

test_cases = [
    {'id': '01', 'desc': 'Detach / Delete disk tests',
     'setup': ['gcutil addinstance "%s" --wait_until_running --zone=%s --machine_type=%s --network=%s --service_account_scopes="%s" --image="%s" --persistent_boot_disk=%s' % (INAME, ZONE, TYPE, NETWORK, SCOPES, IMAGE, USE_PD),
               'gcutil adddisk "%s" --size_gb=2 --zone=%s --wait_until_complete' % (DNAME, ZONE)],

     'tests': [
       {'desc': 'DETACH_ONLY but disk not found [success]',
        'm': 'gce_pd',
        'a': 'name=%s instance_name=%s zone=%s detach_only=yes state=absent' % ("missing-disk", INAME, ZONE),
        'r': '127.0.0.1 | success >> {"changed": false, "detach_only": true, "detached_from_instance": "%s", "name": "missing-disk", "state": "absent", "zone": "%s"}' % (INAME, ZONE),
       },
       {'desc': 'DETACH_ONLY but instance not found [success]',
        'm': 'gce_pd',
        'a': 'name=%s instance_name=%s zone=%s detach_only=yes state=absent' % (DNAME, "missing-instance", ZONE),
        'r': '127.0.0.1 | success >> {"changed": false, "detach_only": true, "detached_from_instance": "missing-instance", "name": "%s", "size_gb": 2, "state": "absent", "zone": "%s"}' % (DNAME, ZONE),
       },
       {'desc': 'DETACH_ONLY but neither disk nor instance exists [success]',
        'm': 'gce_pd',
        'a': 'name=%s instance_name=%s zone=%s detach_only=yes state=absent' % ("missing-disk", "missing-instance", ZONE),
        'r': '127.0.0.1 | success >> {"changed": false, "detach_only": true, "detached_from_instance": "missing-instance", "name": "missing-disk", "state": "absent", "zone": "%s"}' % (ZONE),
       },
       {'desc': 'DETACH_ONLY but disk is not currently attached [success]',
        'm': 'gce_pd',
        'a': 'name=%s instance_name=%s zone=%s detach_only=yes state=absent' % (DNAME, INAME, ZONE),
        'r': '127.0.0.1 | success >> {"changed": false, "detach_only": true, "detached_from_instance": "%s", "name": "%s", "size_gb": 2, "state": "absent", "zone": "%s"}' % (INAME, DNAME, ZONE),
       },
       {'desc': 'DETACH_ONLY disk is attached and should be detached [success]',
        'setup': ['gcutil attachdisk --disk="%s,mode=READ_ONLY" --zone=%s %s' % (DNAME, ZONE, INAME), 'sleep 10'],
        'm': 'gce_pd',
        'a': 'name=%s instance_name=%s zone=%s detach_only=yes state=absent' % (DNAME, INAME, ZONE),
        'r': '127.0.0.1 | success >> {"attached_mode": "READ_ONLY", "attached_to_instance": "%s", "changed": true, "detach_only": true, "detached_from_instance": "%s", "name": "%s", "size_gb": 2, "state": "absent", "zone": "%s"}' % (INAME, INAME, DNAME, ZONE),
        'teardown': ['gcutil detachdisk --zone=%s --device_name=%s %s' % (ZONE, DNAME, INAME)],
       },
       {'desc': 'DETACH_ONLY but not instance specified [FAIL]',
        'm': 'gce_pd',
        'a': 'name=%s zone=%s detach_only=yes state=absent' % (DNAME, ZONE),
        'r': '127.0.0.1 | FAILED >> {"changed": false, "failed": true, "msg": "Must specify an instance name when detaching a disk"}',
       },
       {'desc': 'DELETE but disk not found [success]',
        'm': 'gce_pd',
        'a': 'name=%s zone=%s state=absent' % ("missing-disk", ZONE),
        'r': '127.0.0.1 | success >> {"changed": false, "name": "missing-disk", "state": "absent", "zone": "%s"}' % (ZONE),
       },
       {'desc': 'DELETE but disk is attached [FAIL]',
        'setup': ['gcutil attachdisk --disk="%s,mode=READ_ONLY" --zone=%s %s' % (DNAME, ZONE, INAME), 'sleep 10'],
        'm': 'gce_pd',
        'a': 'name=%s zone=%s state=absent' % (DNAME, ZONE),
        'r': "127.0.0.1 | FAILED >> {\"changed\": false, \"failed\": true, \"msg\": \"The disk resource 'projects/%s/zones/%s/disks/%s' is already being used by 'projects/%s/zones/%s/instances/%s'\"}" % (PROJECT, ZONE, DNAME, PROJECT, ZONE, INAME),
        'teardown': ['gcutil detachdisk --zone=%s --device_name=%s %s' % (ZONE, DNAME, INAME)],
       },
       {'desc': 'DELETE disk [success]',
        'm': 'gce_pd',
        'a': 'name=%s zone=%s state=absent' % (DNAME, ZONE),
        'r': '127.0.0.1 | success >> {"changed": true, "name": "%s", "size_gb": 2, "state": "absent", "zone": "%s"}' % (DNAME, ZONE),
       },
     ],
     'teardown': ['gcutil deleteinstance -f "%s" --zone=%s' % (INAME, ZONE),
                  'sleep 15',
                  'gcutil deletedisk -f "%s" --zone=%s' % (INAME, ZONE),
                  'sleep 10',
                  'gcutil deletedisk -f "%s" --zone=%s' % (DNAME, ZONE),
                  'sleep 10'],
    },

    {'id': '02', 'desc': 'Create disk but do not attach (e.g. no instance_name param)',
     'setup': [],
     'tests': [
       {'desc': 'CREATE_NO_ATTACH "string" for size_gb [FAIL]',
        'm': 'gce_pd',
        'a': 'name=%s size_gb="foo" zone=%s' % (DNAME, ZONE),
        'r': '127.0.0.1 | FAILED >> {"changed": false, "failed": true, "msg": "Must supply a size_gb larger than 1 GB"}',
       },
       {'desc': 'CREATE_NO_ATTACH negative size_gb [FAIL]',
        'm': 'gce_pd',
        'a': 'name=%s size_gb=-2 zone=%s' % (DNAME, ZONE),
        'r': '127.0.0.1 | FAILED >> {"changed": false, "failed": true, "msg": "Must supply a size_gb larger than 1 GB"}',
       },
       {'desc': 'CREATE_NO_ATTACH size_gb exceeds quota [FAIL]',
        'm': 'gce_pd',
        'a': 'name=%s size_gb=9999 zone=%s' % ("big-disk", ZONE),
        'r': '127.0.0.1 | FAILED >> {"changed": false, "failed": true, "msg": "Requested disk size exceeds quota"}',
       },
       {'desc': 'CREATE_NO_ATTACH create the disk [success]',
        'm': 'gce_pd',
        'a': 'name=%s zone=%s' % (DNAME, ZONE),
        'r': '127.0.0.1 | success >> {"changed": true, "name": "%s", "size_gb": 10, "state": "present", "zone": "%s"}' % (DNAME, ZONE),
       },
       {'desc': 'CREATE_NO_ATTACH but disk already exists [success]',
        'm': 'gce_pd',
        'a': 'name=%s zone=%s' % (DNAME, ZONE),
        'r': '127.0.0.1 | success >> {"changed": false, "name": "%s", "size_gb": 10, "state": "present", "zone": "%s"}' % (DNAME, ZONE),
       },
     ],
     'teardown': ['gcutil deletedisk -f "%s" --zone=%s' % (DNAME, ZONE),
                  'sleep 10'],
    },

    {'id': '03', 'desc': 'Create and attach disk',
     'setup': ['gcutil addinstance "%s" --zone=%s --machine_type=%s --network=%s --service_account_scopes="%s" --image="%s" --persistent_boot_disk=%s' % (INAME2, ZONE, TYPE, NETWORK, SCOPES, IMAGE, USE_PD),
               'gcutil addinstance "%s" --zone=%s --machine_type=%s --network=%s --service_account_scopes="%s" --image="%s" --persistent_boot_disk=%s' % (INAME, ZONE, "g1-small", NETWORK, SCOPES, IMAGE, USE_PD),
               'gcutil adddisk "%s" --size_gb=2 --zone=%s' % (DNAME, ZONE),
               'gcutil adddisk "%s" --size_gb=2 --zone=%s --wait_until_complete' % (DNAME2, ZONE),],
     'tests': [
       {'desc': 'CREATE_AND_ATTACH "string" for size_gb [FAIL]',
        'm': 'gce_pd',
        'a': 'name=%s size_gb="foo" instance_name=%s zone=%s' % (DNAME, INAME, ZONE),
        'r': '127.0.0.1 | FAILED >> {"changed": false, "failed": true, "msg": "Must supply a size_gb larger than 1 GB"}',
       },
       {'desc': 'CREATE_AND_ATTACH negative size_gb [FAIL]',
        'm': 'gce_pd',
        'a': 'name=%s size_gb=-2 instance_name=%s zone=%s' % (DNAME, INAME, ZONE),
        'r': '127.0.0.1 | FAILED >> {"changed": false, "failed": true, "msg": "Must supply a size_gb larger than 1 GB"}',
       },
       {'desc': 'CREATE_AND_ATTACH size_gb exceeds quota [FAIL]',
        'm': 'gce_pd',
        'a': 'name=%s size_gb=9999 instance_name=%s zone=%s' % ("big-disk", INAME, ZONE),
        'r': '127.0.0.1 | FAILED >> {"changed": false, "failed": true, "msg": "Requested disk size exceeds quota"}',
       },
       {'desc': 'CREATE_AND_ATTACH missing instance [FAIL]',
        'm': 'gce_pd',
        'a': 'name=%s instance_name=%s zone=%s' % (DNAME, "missing-instance", ZONE),
        'r': '127.0.0.1 | FAILED >> {"changed": false, "failed": true, "msg": "Instance %s does not exist in zone %s"}' % ("missing-instance", ZONE),
       },
       {'desc': 'CREATE_AND_ATTACH disk exists but not attached [success]',
        'peek_before': ["gcutil --format=csv listinstances --zone=%s --filter=\"name eq 'aaaa.*'\"" % (ZONE)],
        'm': 'gce_pd',
        'a': 'name=%s instance_name=%s zone=%s' % (DNAME, INAME, ZONE),
        'r': '127.0.0.1 | success >> {"attached_mode": "READ_ONLY", "attached_to_instance": "%s", "changed": true, "name": "%s", "size_gb": 2, "state": "present", "zone": "%s"}' % (INAME, DNAME, ZONE),
        'peek_after': ["gcutil --format=csv listinstances --zone=%s --filter=\"name eq 'aaaa.*'\"" % (ZONE)],
       },
       {'desc': 'CREATE_AND_ATTACH disk exists already attached [success]',
        'm': 'gce_pd',
        'a': 'name=%s instance_name=%s zone=%s' % (DNAME, INAME, ZONE),
        'r': '127.0.0.1 | success >> {"attached_mode": "READ_ONLY", "attached_to_instance": "%s", "changed": false, "name": "%s", "size_gb": 2, "state": "present", "zone": "%s"}' % (INAME, DNAME, ZONE),
       },
       {'desc': 'CREATE_AND_ATTACH attached RO, attempt RO to 2nd inst [success]',
        'peek_before': ["gcutil --format=csv listinstances --zone=%s --filter=\"name eq 'aaaa.*'\"" % (ZONE)],
        'm': 'gce_pd',
        'a': 'name=%s instance_name=%s zone=%s' % (DNAME, INAME2, ZONE),
        'r': '127.0.0.1 | success >> {"attached_mode": "READ_ONLY", "attached_to_instance": "%s", "changed": true, "name": "%s", "size_gb": 2, "state": "present", "zone": "%s"}' % (INAME2, DNAME, ZONE),
        'peek_after': ["gcutil --format=csv listinstances --zone=%s --filter=\"name eq 'aaaa.*'\"" % (ZONE)],
       },
       {'desc': 'CREATE_AND_ATTACH attached RO, attach RW to self [FAILED no-op]',
        'peek_before': ["gcutil --format=csv listinstances --zone=%s --filter=\"name eq 'aaaa.*'\"" % (ZONE)],
        'm': 'gce_pd',
        'a': 'name=%s instance_name=%s zone=%s mode=READ_WRITE' % (DNAME, INAME, ZONE),
        'r': '127.0.0.1 | success >> {"attached_mode": "READ_ONLY", "attached_to_instance": "%s", "changed": false, "name": "%s", "size_gb": 2, "state": "present", "zone": "%s"}' % (INAME, DNAME, ZONE),
       },
       {'desc': 'CREATE_AND_ATTACH attached RW, attach RW to other [FAIL]',
        'setup': ['gcutil attachdisk --disk=%s,mode=READ_WRITE --zone=%s %s' % (DNAME2, ZONE, INAME), 'sleep 10'],
        'peek_before': ["gcutil --format=csv listinstances --zone=%s --filter=\"name eq 'aaaa.*'\"" % (ZONE)],
        'm': 'gce_pd',
        'a': 'name=%s instance_name=%s zone=%s mode=READ_WRITE' % (DNAME2, INAME2, ZONE),
        'r': "127.0.0.1 | FAILED >> {\"changed\": false, \"failed\": true, \"msg\": \"Unexpected response: HTTP return_code[200], API error code[RESOURCE_IN_USE] and message: The disk resource 'projects/%s/zones/%s/disks/%s' is already being used in read-write mode\"}" % (PROJECT, ZONE, DNAME2),
        'peek_after': ["gcutil --format=csv listinstances --zone=%s --filter=\"name eq 'aaaa.*'\"" % (ZONE)],
       },
       {'desc': 'CREATE_AND_ATTACH attach too many disks to inst [FAIL]',
        'setup': ['gcutil adddisk aa-disk-dummy --size_gb=2 --zone=%s' % (ZONE),
                  'gcutil adddisk aa-disk-dummy2 --size_gb=2 --zone=%s --wait_until_complete' % (ZONE),
                  'gcutil attachdisk --disk=aa-disk-dummy --zone=%s %s' % (ZONE, INAME),
                  'sleep 5'],
        'peek_before': ["gcutil --format=csv listinstances --zone=%s --filter=\"name eq 'aaaa.*'\"" % (ZONE)],
        'm': 'gce_pd',
        'a': 'name=%s instance_name=%s zone=%s' % ("aa-disk-dummy2", INAME, ZONE),
        'r': "127.0.0.1 | FAILED >> {\"changed\": false, \"failed\": true, \"msg\": \"Unexpected response: HTTP return_code[200], API error code[LIMIT_EXCEEDED] and message: Exceeded limit 'maximum_persistent_disks' on resource 'projects/%s/zones/%s/instances/%s'. Limit: 4\"}" % (PROJECT, ZONE, INAME),
        'teardown': ['gcutil detachdisk --device_name=aa-disk-dummy --zone=%s %s' % (ZONE, INAME),
                     'sleep 3',
                     'gcutil deletedisk -f aa-disk-dummy --zone=%s' % (ZONE),
                     'sleep 10',
                     'gcutil deletedisk -f aa-disk-dummy2 --zone=%s' % (ZONE),
                     'sleep 10'],
       },
     ],
     'teardown': ['gcutil deleteinstance -f "%s" --zone=%s' % (INAME2, ZONE),
                  'sleep 15',
                  'gcutil deleteinstance -f "%s" --zone=%s' % (INAME, ZONE),
                  'sleep 15',
                  'gcutil deletedisk -f "%s" --zone=%s' % (INAME, ZONE),
                  'sleep 10',
                  'gcutil deletedisk -f "%s" --zone=%s' % (INAME2, ZONE),
                  'sleep 10',
                  'gcutil deletedisk -f "%s" --zone=%s' % (DNAME, ZONE),
                  'sleep 10',
                  'gcutil deletedisk -f "%s" --zone=%s' % (DNAME2, ZONE),
                  'sleep 10'],
    },

    {'id': '04', 'desc': 'Delete / destroy instances',
     'setup': ['gcutil addinstance "%s" --zone=%s --machine_type=%s --image="%s" --persistent_boot_disk=false' % (INAME, ZONE, TYPE, IMAGE),
               'gcutil addinstance "%s" --zone=%s --machine_type=%s --image="%s" --persistent_boot_disk=false' % (INAME2, ZONE, TYPE, IMAGE),
               'gcutil addinstance "%s" --zone=%s --machine_type=%s --image="%s" --persistent_boot_disk=false' % (INAME3, ZONE, TYPE, IMAGE),
               'gcutil addinstance "%s" --zone=%s --machine_type=%s --image="%s" --persistent_boot_disk=false' % (INAME4, ZONE, TYPE, IMAGE),
               'gcutil addinstance "%s" --wait_until_running --zone=%s --machine_type=%s --image="%s" --persistent_boot_disk=false' % (INAME5, ZONE, TYPE, IMAGE)],
     'tests': [
       {'desc': 'DELETE instance, bad zone param [FAIL]',
        'm': 'gce',
        'a': 'name=missing-inst zone=bogus state=absent',
        'r': '127.0.0.1 | FAILED >> {"failed": true, "msg": "value of zone must be one of: us-central1-a,us-central1-b,us-central2-a,europe-west1-a,europe-west1-b, got: bogus"}',
       },
       {'desc': 'DELETE non-existent instance, no-op [success]',
        'm': 'gce',
        'a': 'name=missing-inst zone=%s state=absent' % (ZONE),
        'r': '127.0.0.1 | success >> {"changed": false, "name": "missing-inst", "state": "absent", "zone": "%s"}' % (ZONE),
       },
       {'desc': 'DELETE an existing named instance [success]',
        'm': 'gce',
        'a': 'name=%s zone=%s state=absent' % (INAME, ZONE),
        'r': '127.0.0.1 | success >> {"changed": true, "name": "%s", "state": "absent", "zone": "%s"}' % (INAME, ZONE),
       },
       {'desc': 'DELETE list of instances with a non-existent one [success]',
        'm': 'gce',
        'a': 'instance_names=%s,missing,%s zone=%s state=absent' % (INAME2,INAME3, ZONE),
        'r': '127.0.0.1 | success >> {"changed": true, "instance_names": ["%s", "%s"], "state": "absent", "zone": "%s"}' % (INAME2, INAME3, ZONE),
       },
       {'desc': 'DELETE list of instances all pre-exist [success]',
        'm': 'gce',
        'a': 'instance_names=%s,%s zone=%s state=absent' % (INAME4,INAME5, ZONE),
        'r': '127.0.0.1 | success >> {"changed": true, "instance_names": ["%s", "%s"], "state": "absent", "zone": "%s"}' % (INAME4, INAME5, ZONE),
       },
     ],
     'teardown': ['gcutil deleteinstance -f "%s" --zone=%s' % (INAME, ZONE),
                  'gcutil deleteinstance -f "%s" --zone=%s' % (INAME2, ZONE),
                  'gcutil deleteinstance -f "%s" --zone=%s' % (INAME3, ZONE),
                  'gcutil deleteinstance -f "%s" --zone=%s' % (INAME4, ZONE),
                  'gcutil deleteinstance -f "%s" --zone=%s' % (INAME5, ZONE),
                  'sleep 10'],
    },

    {'id': '05', 'desc': 'Create instances',
     'setup': ['gcutil adddisk --source_image=%s --zone=%s %s --wait_until_complete' % (IMAGE, ZONE, DNAME7),
              'gcutil addinstance boo --wait_until_running --zone=%s --machine_type=%s --network=%s --disk=%s,mode=READ_WRITE,boot --kernel=%s' % (ZONE,TYPE,NETWORK,DNAME7,KERNEL),
              ],
     'tests': [
       {'desc': 'CREATE_INSTANCE invalid image arg [FAIL]',
        'm': 'gce',
        'a': 'name=foo image=foo',
        'r': '127.0.0.1 | FAILED >> {"changed": false, "failed": true, "msg": "Missing required create instance variable"}',
       },
       {'desc': 'CREATE_INSTANCE metadata a list [FAIL]',
        'strip_numbers': True,
        'm': 'gce',
        'a': 'name=%s zone=%s metadata=\'[\\"foo\\":\\"bar\\",\\"baz\\":1]\'' % (INAME,ZONE),
        'r': '127.0.0.1 | FAILED >> {"failed": true, "msg": "bad metadata syntax"}',
       },
       {'desc': 'CREATE_INSTANCE metadata not a dict [FAIL]',
        'strip_numbers': True,
        'm': 'gce',
        'a': 'name=%s zone=%s metadata=\\"foo\\":\\"bar\\",\\"baz\\":1' % (INAME,ZONE),
        'r': '127.0.0.1 | FAILED >> {"failed": true, "msg": "bad metadata syntax"}',
       },
       {'desc': 'CREATE_INSTANCE with metadata form1 [FAIL]',
        'strip_numbers': True,
        'm': 'gce',
        'a': 'name=%s zone=%s metadata=\'{"foo":"bar","baz":1}\'' % (INAME,ZONE),
        'r': '127.0.0.1 | FAILED >> {"failed": true, "msg": "bad metadata: malformed string"}',
       },
       {'desc': 'CREATE_INSTANCE with metadata form2 [FAIL]',
        'strip_numbers': True,
        'm': 'gce',
        'a': 'name=%s zone=%s metadata={\'foo\':\'bar\',\'baz\':1}' % (INAME,ZONE),
        'r': '127.0.0.1 | FAILED >> {"failed": true, "msg": "bad metadata: malformed string"}',
       },
       {'desc': 'CREATE_INSTANCE with metadata form3 [FAIL]',
        'strip_numbers': True,
        'm': 'gce',
        'a': 'name=%s zone=%s metadata="foo:bar" '% (INAME,ZONE),
        'r': '127.0.0.1 | FAILED >> {"failed": true, "msg": "bad metadata syntax"}',
       },
       {'desc': 'CREATE_INSTANCE with metadata form4 [FAIL]',
        'strip_numbers': True,
        'm': 'gce',
        'a': 'name=%s zone=%s metadata="{\'foo\':\'bar\'}"'% (INAME,ZONE),
        'r': '127.0.0.1 | FAILED >> {"failed": true, "msg": "bad metadata: malformed string"}',
       },
       {'desc': 'CREATE_INSTANCE invalid image arg [FAIL]',
        'm': 'gce',
        'a': 'instance_names=foo,bar image=foo',
        'r': '127.0.0.1 | FAILED >> {"changed": false, "failed": true, "msg": "Missing required create instance variable"}',
       },
       {'desc': 'CREATE_INSTANCE single inst, using defaults [success]',
        'strip_numbers': True,
        'm': 'gce',
        'a': 'name=%s' % (INAME),
        'r': '127.0.0.1 | success >> {"changed": true, "instance_data": [{"image": "debian-7-wheezy-v20130816", "machine_type": "n1-standard-1", "metadata": {}, "name": "%s", "network": "default", "private_ip": "10.240.175.15", "public_ip": "173.255.120.190", "status": "RUNNING", "tags": [], "zone": "%s"}], "name": "%s", "state": "present", "zone": "%s"}' % (INAME, ZONE, INAME, ZONE),
       },
       {'desc': 'CREATE_INSTANCE the same instance again, no-op [success]',
        'strip_numbers': True,
        'm': 'gce',
        'a': 'name=%s' % (INAME),
        'r': '127.0.0.1 | success >> {"changed": false, "instance_data": [{"image": "debian-7-wheezy-v20130816", "machine_type": "n1-standard-1", "metadata": {}, "name": "%s", "network": "default", "private_ip": "10.240.175.15", "public_ip": "173.255.120.190", "status": "RUNNING", "tags": [], "zone": "%s"}], "name": "%s", "state": "present", "zone": "%s"}' % (INAME, ZONE, INAME, ZONE),
       },
       {'desc': 'CREATE_INSTANCE instance with alt type [success]',
        'strip_numbers': True,
        'm': 'gce',
        'a': 'name=%s machine_type=n1-standard-2' % (INAME2),
        'r': '127.0.0.1 | success >> {"changed": true, "instance_data": [{"image": "debian-7-wheezy-v20130816", "machine_type": "n1-standard-2", "metadata": {}, "name": "%s", "network": "default", "private_ip": "10.240.192.227", "public_ip": "173.255.121.233", "status": "RUNNING", "tags": [], "zone": "%s"}], "name": "%s", "state": "present", "zone": "%s"}' % (INAME2, ZONE, INAME2, ZONE),
       },
       {'desc': 'CREATE_INSTANCE instance with root pd [success]',
        'strip_numbers': True,
        'm': 'gce',
        'a': 'name=%s persistent_boot_disk=yes' % (INAME3),
        'r': '127.0.0.1 | success >> {"changed": true, "instance_data": [{"image": null, "machine_type": "n1-standard-1", "metadata": {}, "name": "%s", "network": "default", "private_ip": "10.240.178.140", "public_ip": "173.255.121.176", "status": "RUNNING", "tags": [], "zone": "%s"}], "name": "%s", "state": "present", "zone": "%s"}' % (INAME3, ZONE, INAME3, ZONE),
       },
       {'desc': 'CREATE_INSTANCE instance with root pd, that already exists [success]',
        'setup': ['gcutil adddisk --source_image=%s --zone=%s %s --wait_until_complete' % (IMAGE, ZONE, DNAME6),],
        'strip_numbers': True,
        'm': 'gce',
        'a': 'name=%s zone=%s persistent_boot_disk=yes' % (INAME6, ZONE),
        'r': '127.0.0.1 | success >> {"changed": true, "instance_data": [{"image": null, "machine_type": "n1-standard-1", "metadata": {}, "name": "%s", "network": "default", "private_ip": "10.240.178.140", "public_ip": "173.255.121.176", "status": "RUNNING", "tags": [], "zone": "%s"}], "name": "%s", "state": "present", "zone": "%s"}' % (INAME6, ZONE, INAME6, ZONE),
       },
       {'desc': 'CREATE_INSTANCE instance with root pd attached to other inst [FAIL]',
        'm': 'gce',
        'a': 'name=%s zone=%s persistent_boot_disk=yes' % (INAME7, ZONE),
        'r': '127.0.0.1 | FAILED >> {"failed": true, "msg": "Unexpected error attempting to create instance %s, error: The disk resource \'projects/%s/zones/%s/disks/%s\' is already being used in read-write mode"}' % (INAME7,PROJECT,ZONE,DNAME7),
       },
       {'desc': 'CREATE_INSTANCE use *all* the options! [success]',
        'strip_numbers': True,
        'm': 'gce',
        'a': 'instance_names=%s,%s metadata=\'{\\"foo\\":\\"bar\\", \\"baz\\":1}\' tags=t1,t2,t3 zone=%s image=centos-6-v20130731 persistent_boot_disk=yes' % (INAME4,INAME5,ZONE),
        'r': '127.0.0.1 | success >> {"changed": true, "instance_data": [{"image": null, "machine_type": "n1-standard-1", "metadata": {"baz": "1", "foo": "bar"}, "name": "%s", "network": "default", "private_ip": "10.240.130.4", "public_ip": "173.255.121.97", "status": "RUNNING", "tags": ["t1", "t2", "t3"], "zone": "%s"}, {"image": null, "machine_type": "n1-standard-1", "metadata": {"baz": "1", "foo": "bar"}, "name": "%s", "network": "default", "private_ip": "10.240.207.226", "public_ip": "173.255.121.85", "status": "RUNNING", "tags": ["t1", "t2", "t3"], "zone": "%s"}], "instance_names": ["%s", "%s"], "state": "present", "zone": "%s"}' % (INAME4, ZONE, INAME5, ZONE, INAME4, INAME5, ZONE),
       },
     ],
     'teardown': ['gcutil deleteinstance -f "%s" --zone=%s' % (INAME, ZONE),
                  'gcutil deleteinstance -f "%s" --zone=%s' % (INAME2, ZONE),
                  'gcutil deleteinstance -f "%s" --zone=%s' % (INAME3, ZONE),
                  'gcutil deleteinstance -f "%s" --zone=%s' % (INAME4, ZONE),
                  'gcutil deleteinstance -f "%s" --zone=%s' % (INAME5, ZONE),
                  'gcutil deleteinstance -f "%s" --zone=%s' % (INAME6, ZONE),
                  'gcutil deleteinstance -f "%s" --zone=%s' % (INAME7, ZONE),
                  'gcutil deleteinstance -f boo --zone=%s' % (ZONE),
                  'sleep 10',
                  'gcutil deletedisk -f "%s" --zone=%s' % (INAME3, ZONE),
                  'gcutil deletedisk -f "%s" --zone=%s' % (INAME4, ZONE),
                  'gcutil deletedisk -f "%s" --zone=%s' % (INAME5, ZONE),
                  'gcutil deletedisk -f "%s" --zone=%s' % (INAME6, ZONE),
                  'gcutil deletedisk -f "%s" --zone=%s' % (INAME7, ZONE),
                  'sleep 10'],
    },

    {'id': '06', 'desc': 'Delete / destroy networks and firewall rules',
     'setup': ['gcutil addnetwork --range="%s" --gateway="%s" %s' % (CIDR1, GW1, NETWK1),
               'gcutil addnetwork --range="%s" --gateway="%s" %s' % (CIDR2, GW2, NETWK2),
               'sleep 5',
               'gcutil addfirewall --allowed="tcp:80" --network=%s %s' % (NETWK1, FW1),
               'gcutil addfirewall --allowed="tcp:80" --network=%s %s' % (NETWK2, FW2),
               'sleep 5'],
     'tests': [
       {'desc': 'DELETE bogus named firewall [success]',
        'm': 'gce_net',
        'a': 'fwname=missing-fwrule state=absent',
        'r': '127.0.0.1 | success >> {"changed": false, "fwname": "missing-fwrule", "state": "absent"}',
       },
       {'desc': 'DELETE bogus named network [success]',
        'm': 'gce_net',
        'a': 'name=missing-network state=absent',
        'r': '127.0.0.1 | success >> {"changed": false, "name": "missing-network", "state": "absent"}',
       },
       {'desc': 'DELETE named firewall rule [success]',
        'm': 'gce_net',
        'a': 'fwname=%s state=absent' % (FW1),
        'r': '127.0.0.1 | success >> {"changed": true, "fwname": "%s", "state": "absent"}' % (FW1),
        'teardown': ['sleep 5'], # pause to give GCE time to delete fwrule
       },
       {'desc': 'DELETE unused named network [success]',
        'm': 'gce_net',
        'a': 'name=%s state=absent' % (NETWK1),
        'r': '127.0.0.1 | success >> {"changed": true, "name": "%s", "state": "absent"}' % (NETWK1),
       },
       {'desc': 'DELETE named network *and* fwrule [success]',
        'm': 'gce_net',
        'a': 'name=%s fwname=%s state=absent' % (NETWK2, FW2),
        'r': '127.0.0.1 | success >> {"changed": true, "fwname": "%s", "name": "%s", "state": "absent"}' % (FW2, NETWK2),
       },
     ],
     'teardown': ['gcutil deletenetwork -f %s' % (NETWK1),
                  'gcutil deletenetwork -f %s' % (NETWK2),
                  'sleep 5',
                  'gcutil deletefirewall -f %s' % (FW1),
                  'gcutil deletefirewall -f %s' % (FW2)],
    },

    {'id': '07', 'desc': 'Create networks and firewall rules',
     'setup': ['gcutil addnetwork --range="%s" --gateway="%s" %s' % (CIDR1, GW1, NETWK1),
               'sleep 5',
               'gcutil addfirewall --allowed="tcp:80" --network=%s %s' % (NETWK1, FW1),
               'sleep 5'],
     'tests': [
       {'desc': 'CREATE network without specifying ipv4_range [FAIL]',
        'm': 'gce_net',
        'a': 'name=fail',
        'r': "127.0.0.1 | FAILED >> {\"changed\": false, \"failed\": true, \"msg\": \"Missing required 'ipv4_range' parameter\"}",
       },
       {'desc': 'CREATE network with specifying bad ipv4_range [FAIL]',
        'm': 'gce_net',
        'a': 'name=fail ipv4_range=bad_value',
        'r': "127.0.0.1 | FAILED >> {\"changed\": false, \"failed\": true, \"msg\": \"Unexpected response: HTTP return_code[400], API error code[None] and message: Invalid value for field 'resource.IPv4Range': 'bad_value'.  Must be a CIDR address range that is contained in the RFC1918 private address blocks: [10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16]\"}",
       },
       {'desc': 'CREATE existing network, not changed [success]',
        'm': 'gce_net',
        'a': 'name=%s ipv4_range=%s' % (NETWK1, CIDR1),
        'r': '127.0.0.1 | success >> {"changed": false, "ipv4_range": "%s", "name": "%s", "state": "present"}' % (CIDR1, NETWK1),
       },
       {'desc': 'CREATE new network, changed [success]',
        'm': 'gce_net',
        'a': 'name=%s ipv4_range=%s' % (NETWK2, CIDR2),
        'r': '127.0.0.1 | success >> {"changed": true, "ipv4_range": "10.240.32.0/24", "name": "%s", "state": "present"}' % (NETWK2),
       },
       {'desc': 'CREATE new fw rule missing params [FAIL]',
        'm': 'gce_net',
        'a': 'name=%s fwname=%s' % (NETWK1, FW1),
        'r': '127.0.0.1 | FAILED >> {"changed": false, "failed": true, "msg": "Missing required firewall rule parameter(s)"}',
       },
       {'desc': 'CREATE new fw rule bad params [FAIL]',
        'm': 'gce_net',
        'a': 'name=%s fwname=broken allowed=blah src_tags="one,two"' % (NETWK1),
        'r': "127.0.0.1 | FAILED >> {\"changed\": false, \"failed\": true, \"msg\": \"Unexpected response: HTTP return_code[400], API error code[None] and message: Invalid value for field 'resource.allowed[0].IPProtocol': 'blah'.  Must be one of [\\\"tcp\\\", \\\"udp\\\", \\\"icmp\\\"] or an IP protocol number between 0 and 255\"}",
       },
       {'desc': 'CREATE existing fw rule [success]',
        'm': 'gce_net',
        'a': 'name=%s fwname=%s allowed="tcp:80" src_tags="one,two"' % (NETWK1, FW1),
        'r': '127.0.0.1 | success >> {"allowed": "tcp:80", "changed": false, "fwname": "%s", "ipv4_range": "%s", "name": "%s", "src_range": null, "src_tags": ["one", "two"], "state": "present"}' % (FW1, CIDR1, NETWK1),
       },
       {'desc': 'CREATE new fw rule [success]',
        'm': 'gce_net',
        'a': 'name=%s fwname=%s allowed="tcp:80" src_tags="one,two"' % (NETWK1, FW3),
        'r': '127.0.0.1 | success >> {"allowed": "tcp:80", "changed": true, "fwname": "%s", "ipv4_range": "%s", "name": "%s", "src_range": null, "src_tags": ["one", "two"], "state": "present"}' % (FW3, CIDR1, NETWK1),
       },
       {'desc': 'CREATE new network *and* fw rule [success]',
        'm': 'gce_net',
        'a': 'name=%s ipv4_range=%s fwname=%s allowed="tcp:80" src_tags="one,two"' % (NETWK3, CIDR3, FW4),
        'r': '127.0.0.1 | success >> {"allowed": "tcp:80", "changed": true, "fwname": "%s", "ipv4_range": "%s", "name": "%s", "src_range": null, "src_tags": ["one", "two"], "state": "present"}' % (FW4, CIDR3, NETWK3),
       },
     ],
     'teardown': ['gcutil deletefirewall -f %s' % (FW1),
                  'gcutil deletefirewall -f %s' % (FW2),
                  'gcutil deletefirewall -f %s' % (FW3),
                  'gcutil deletefirewall -f %s' % (FW4),
                  'sleep 5',
                  'gcutil deletenetwork -f %s' % (NETWK1),
                  'gcutil deletenetwork -f %s' % (NETWK2),
                  'gcutil deletenetwork -f %s' % (NETWK3),
                  'sleep 5'],
    },

    {'id': '08', 'desc': 'Create load-balancer resources',
     'setup': ['gcutil addinstance "%s" --zone=%s --machine_type=%s --network=%s --service_account_scopes="%s" --image="%s" --nopersistent_boot_disk' % (INAME, ZONE, TYPE, NETWORK, SCOPES, IMAGE),
               'gcutil addinstance "%s" --wait_until_running --zone=%s --machine_type=%s --network=%s --service_account_scopes="%s" --image="%s" --nopersistent_boot_disk' % (INAME2, ZONE, TYPE, NETWORK, SCOPES, IMAGE),
              ],
     'tests': [
       {'desc': 'Do nothing [FAIL]',
        'm': 'gce_lb',
        'a': 'httphealthcheck_port=7',
        'r': '127.0.0.1 | FAILED >> {"changed": false, "failed": true, "msg": "Nothing to do, please specify a \\\"name\\\" or \\\"httphealthcheck_name\\\" parameter"}',
       },
       {'desc': 'CREATE_HC create basic http healthcheck [success]',
        'm': 'gce_lb',
        'a': 'httphealthcheck_name=%s' % (HC1),
        'r': '127.0.0.1 | success >> {"changed": true, "httphealthcheck_healthy_count": 2, "httphealthcheck_host": null, "httphealthcheck_interval": 5, "httphealthcheck_name": "%s", "httphealthcheck_path": "/", "httphealthcheck_port": 80, "httphealthcheck_timeout": 5, "httphealthcheck_unhealthy_count": 2, "name": null, "state": "present"}' % (HC1),
       },
       {'desc': 'CREATE_HC (repeat, no-op) create basic http healthcheck [success]',
        'm': 'gce_lb',
        'a': 'httphealthcheck_name=%s' % (HC1),
        'r': '127.0.0.1 | success >> {"changed": false, "httphealthcheck_healthy_count": 2, "httphealthcheck_host": null, "httphealthcheck_interval": 5, "httphealthcheck_name": "%s", "httphealthcheck_path": "/", "httphealthcheck_port": 80, "httphealthcheck_timeout": 5, "httphealthcheck_unhealthy_count": 2, "name": null, "state": "present"}' % (HC1),
       },
       {'desc': 'CREATE_HC create custom http healthcheck [success]',
        'm': 'gce_lb',
        'a': 'httphealthcheck_name=%s httphealthcheck_port=1234 httphealthcheck_path="/whatup" httphealthcheck_host="foo" httphealthcheck_interval=300' % (HC2),
        'r': '127.0.0.1 | success >> {"changed": true, "httphealthcheck_healthy_count": 2, "httphealthcheck_host": "foo", "httphealthcheck_interval": 300, "httphealthcheck_name": "%s", "httphealthcheck_path": "/whatup", "httphealthcheck_port": 1234, "httphealthcheck_timeout": 5, "httphealthcheck_unhealthy_count": 2, "name": null, "state": "present"}' % (HC2),
       },
       {'desc': 'CREATE_HC create (broken) custom http healthcheck [FAIL]',
        'm': 'gce_lb',
        'a': 'httphealthcheck_name=%s httphealthcheck_port="string" httphealthcheck_path=7' % (HC3),
        'r': '127.0.0.1 | FAILED >> {"changed": false, "failed": true, "msg": "Unexpected response: HTTP return_code[400], API error code[None] and message: Invalid value for: Expected a signed integer, got \'string\' (class java.lang.String)"}',
       },
       {'desc': 'CREATE_LB create lb, missing region [FAIL]',
        'm': 'gce_lb',
        'a': 'name=%s' % (LB1),
        'r': '127.0.0.1 | FAILED >> {"changed": false, "failed": true, "msg": "Missing required region name"}',
       },
       {'desc': 'CREATE_LB create lb, bogus region [FAIL]',
        'm': 'gce_lb',
        'a': 'name=%s region=bogus' % (LB1),
        'r': '127.0.0.1 | FAILED >> {"changed": false, "failed": true, "msg": "Unexpected response: HTTP return_code[404], API error code[None] and message: The resource \'projects/%s/regions/bogus\' was not found"}' % (PROJECT),
       },
       {'desc': 'CREATE_LB create lb, minimal params [success]',
        'strip_numbers': True,
        'm': 'gce_lb',
        'a': 'name=%s region=%s' % (LB1, REGION),
        'r': '127.0.0.1 | success >> {"changed": true, "external_ip": "173.255.123.245", "httphealthchecks": [], "members": [], "name": "%s", "port_range": "1-65535", "protocol": "tcp", "region": "%s", "state": "present"}' % (LB1, REGION),
       },
       {'desc': 'CREATE_LB create lb full params [success]',
        'strip_numbers': True,
        'm': 'gce_lb',
        'a': 'httphealthcheck_name=%s httphealthcheck_port=5055 httphealthcheck_path="/howami" name=%s port_range=8000-8888 region=%s members=%s/%s,%s/%s' % (HC3,LB2,REGION,ZONE,INAME,ZONE,INAME2),
        'r': '127.0.0.1 | success >> {"changed": true, "external_ip": "173.255.126.81", "httphealthcheck_healthy_count": 2, "httphealthcheck_host": null, "httphealthcheck_interval": 5, "httphealthcheck_name": "%s", "httphealthcheck_path": "/howami", "httphealthcheck_port": 5055, "httphealthcheck_timeout": 5, "httphealthcheck_unhealthy_count": 2, "httphealthchecks": ["%s"], "members": ["%s/%s", "%s/%s"], "name": "%s", "port_range": "8000-8888", "protocol": "tcp", "region": "%s", "state": "present"}' % (HC3,HC3,ZONE,INAME,ZONE,INAME2,LB2,REGION),
       },
      ],
      'teardown': [
        'gcutil deleteinstance --zone=%s -f %s %s' % (ZONE, INAME, INAME2),
        'gcutil deleteforwardingrule --region=%s -f %s %s' % (REGION, LB1, LB2),
        'sleep 10',
        'gcutil deletetargetpool --region=%s -f %s-tp %s-tp' % (REGION, LB1, LB2),
        'sleep 10',
        'gcutil deletehttphealthcheck -f %s %s %s' % (HC1, HC2, HC3),
      ],
    },

    {'id': '09', 'desc': 'Destroy load-balancer resources',
     'setup': ['gcutil addhttphealthcheck %s' % (HC1),
               'sleep 5',
               'gcutil addhttphealthcheck %s' % (HC2),
               'sleep 5',
               'gcutil addtargetpool --health_checks=%s --region=%s %s-tp' % (HC1, REGION, LB1),
               'sleep 5',
               'gcutil addforwardingrule --target=%s-tp --region=%s %s' % (LB1, REGION, LB1),
               'sleep 5',
               'gcutil addtargetpool --region=%s %s-tp' % (REGION, LB2),
               'sleep 5',
               'gcutil addforwardingrule --target=%s-tp --region=%s %s' % (LB2, REGION, LB2),
               'sleep 5',
              ],
     'tests': [
       {'desc': 'DELETE_LB: delete a non-existent LB [success]',
        'm': 'gce_lb',
        'a': 'name=missing state=absent',
        'r': '127.0.0.1 | success >> {"changed": false, "name": "missing", "state": "absent"}',
       },
       {'desc': 'DELETE_LB: delete a non-existent LB+HC [success]',
        'm': 'gce_lb',
        'a': 'name=missing httphealthcheck_name=alsomissing state=absent',
        'r': '127.0.0.1 | success >> {"changed": false, "httphealthcheck_name": "alsomissing", "name": "missing", "state": "absent"}',
       },
       {'desc': 'DELETE_LB: destroy standalone healthcheck [success]',
        'm': 'gce_lb',
        'a': 'httphealthcheck_name=%s state=absent' % (HC2),
        'r': '127.0.0.1 | success >> {"changed": true, "httphealthcheck_name": "%s", "name": null, "state": "absent"}' % (HC2),
       },
       {'desc': 'DELETE_LB: destroy standalone balancer [success]',
        'm': 'gce_lb',
        'a': 'name=%s state=absent' % (LB2),
        'r': '127.0.0.1 | success >> {"changed": true, "name": "%s", "state": "absent"}' % (LB2),
       },
       {'desc': 'DELETE_LB: destroy LB+HC [success]',
        'm': 'gce_lb',
        'a': 'name=%s httphealthcheck_name=%s state=absent' % (LB1, HC1),
        'r': '127.0.0.1 | success >> {"changed": true, "httphealthcheck_name": "%s", "name": "%s", "state": "absent"}' % (HC1,LB1),
       },
     ],
      'teardown': [
        'gcutil deleteforwardingrule --region=%s -f %s %s' % (REGION, LB1, LB2),
        'sleep 10',
        'gcutil deletetargetpool --region=%s -f %s-tp %s-tp' % (REGION, LB1, LB2),
        'sleep 10',
        'gcutil deletehttphealthcheck -f %s %s' % (HC1, HC2),
      ],
    },
]

def main(tests_to_run=[]):
    for test in test_cases:
        if tests_to_run and test['id'] not in tests_to_run:
            continue
        print "=> starting/setup '%s:%s'"% (test['id'], test['desc'])
        if DEBUG: print "=debug>", test['setup']
        for c in test['setup']:
            (s,o) = run(c)
        test_i = 1
        for t in test['tests']:
            if DEBUG: print "=>debug>", test_i, t['desc']
            # run any test-specific setup commands
            if t.has_key('setup'):
                for setup in t['setup']:
                    (status, output) = run(setup)

            # run any 'peek_before' commands
            if t.has_key('peek_before') and PEEKING_ENABLED:
                for setup in t['peek_before']:
                    (status, output) = run(setup)

            # run the ansible test if 'a' exists, otherwise
            # an empty 'a' directive allows test to run
            # setup/teardown for a subsequent test.
            if t['a']:
                if DEBUG: print "=>debug>", t['m'], t['a']
                acmd = "ansible all -o -m %s -a \"%s\"" % (t['m'],t['a'])
                #acmd = "ANSIBLE_KEEP_REMOTE_FILES=1 ansible all -vvv -m %s -a \"%s\"" % (t['m'],t['a'])
                (s,o) = run(acmd)

                # check expected output
                if DEBUG: print "=debug>", o.strip(), "!=", t['r']
                print "=> %s.%02d '%s':" % (test['id'], test_i, t['desc']),
                if t.has_key('strip_numbers'):
                    # strip out all numbers so we don't trip over different
                    # IP addresses
                    is_good = (o.strip().translate(None, "0123456789") == t['r'].translate(None, "0123456789"))
                else:
                    is_good = (o.strip() == t['r'])

                if is_good:
                    print "PASS"
                else:
                    print "FAIL"
                    if VERBOSE:
                        print "=>", acmd
                        print "=> Expected:", t['r']
                        print "=>      Got:", o.strip()

            # run any 'peek_after' commands
            if t.has_key('peek_after') and PEEKING_ENABLED:
                for setup in t['peek_after']:
                    (status, output) = run(setup)

            # run any test-specific teardown commands
            if t.has_key('teardown'):
                for td in t['teardown']:
                    (status, output) = run(td)
            test_i += 1

        print "=> completing/teardown '%s:%s'" % (test['id'], test['desc'])
        if DEBUG: print "=debug>", test['teardown']
        for c in test['teardown']:
            (s,o) = run(c)


if __name__ == '__main__':
    tests_to_run = []
    if len(sys.argv) == 2:
        if sys.argv[1] in ["--help", "--list"]:
            print "usage: %s [id1,id2,...,idN]" % sys.argv[0]
            print "  * An empty argument list will execute all tests"
            print "  * Do not need to specify tests in numerical order"
            print "  * List test categories with --list or --help"
            print ""
            for test in test_cases:
                print "\t%s:%s" % (test['id'], test['desc'])
            sys.exit(0)
        else:
            tests_to_run = sys.argv[1].split(',')
    main(tests_to_run)

########NEW FILE########
__FILENAME__ = callbacks
# (C) 2012-2014, Michael DeHaan, <michael.dehaan@gmail.com>

# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

import utils
import sys
import getpass
import os
import subprocess
import random
import fnmatch
import tempfile
import fcntl
import constants
from ansible.color import stringc

import logging
if constants.DEFAULT_LOG_PATH != '':
    path = constants.DEFAULT_LOG_PATH

    if (os.path.exists(path) and not os.access(path, os.W_OK)) and not os.access(os.path.dirname(path), os.W_OK):
        sys.stderr.write("log file at %s is not writeable, aborting\n" % path)
        sys.exit(1)


    logging.basicConfig(filename=path, level=logging.DEBUG, format='%(asctime)s %(name)s %(message)s')
    mypid = str(os.getpid())
    user = getpass.getuser()
    logger = logging.getLogger("p=%s u=%s | " % (mypid, user))

callback_plugins = []

def load_callback_plugins():
    global callback_plugins
    callback_plugins = [x for x in utils.plugins.callback_loader.all()]

def get_cowsay_info():
    if constants.ANSIBLE_NOCOWS:
        return (None, None)
    cowsay = None
    if os.path.exists("/usr/bin/cowsay"):
        cowsay = "/usr/bin/cowsay"
    elif os.path.exists("/usr/games/cowsay"):
        cowsay = "/usr/games/cowsay"
    elif os.path.exists("/usr/local/bin/cowsay"):
        # BSD path for cowsay
        cowsay = "/usr/local/bin/cowsay"
    elif os.path.exists("/opt/local/bin/cowsay"):
        # MacPorts path for cowsay
        cowsay = "/opt/local/bin/cowsay"

    noncow = os.getenv("ANSIBLE_COW_SELECTION",None)
    if cowsay and noncow == 'random':
        cmd = subprocess.Popen([cowsay, "-l"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (out, err) = cmd.communicate()
        cows = out.split()
        cows.append(False)
        noncow = random.choice(cows)
    return (cowsay, noncow)

cowsay, noncow = get_cowsay_info()

def log_lockfile():
    # create the path for the lockfile and open it
    tempdir = tempfile.gettempdir()
    uid = os.getuid()
    path = os.path.join(tempdir, ".ansible-lock.%s" % uid)
    lockfile = open(path, 'w')
    # use fcntl to set FD_CLOEXEC on the file descriptor, 
    # so that we don't leak the file descriptor later
    lockfile_fd = lockfile.fileno()
    old_flags = fcntl.fcntl(lockfile_fd, fcntl.F_GETFD)
    fcntl.fcntl(lockfile_fd, fcntl.F_SETFD, old_flags | fcntl.FD_CLOEXEC)
    return lockfile
    
LOG_LOCK = log_lockfile()

def log_flock(runner):
    if runner is not None:
        try:
            fcntl.lockf(runner.output_lockfile, fcntl.LOCK_EX)
        except OSError:
            # already got closed?
            pass
    else:
        try:
            fcntl.lockf(LOG_LOCK, fcntl.LOCK_EX)
        except OSError:
            pass


def log_unflock(runner):
    if runner is not None:
        try:
            fcntl.lockf(runner.output_lockfile, fcntl.LOCK_UN)
        except OSError:
            # already got closed?
            pass
    else:
        try:
            fcntl.lockf(LOG_LOCK, fcntl.LOCK_UN)
        except OSError:
            pass

def set_playbook(callback, playbook):
    ''' used to notify callback plugins of playbook context '''
    callback.playbook = playbook
    for callback_plugin in callback_plugins:
        callback_plugin.playbook = playbook

def set_play(callback, play):
    ''' used to notify callback plugins of context '''
    callback.play = play
    for callback_plugin in callback_plugins:
        callback_plugin.play = play

def set_task(callback, task):
    ''' used to notify callback plugins of context '''
    callback.task = task
    for callback_plugin in callback_plugins:
        callback_plugin.task = task

def display(msg, color=None, stderr=False, screen_only=False, log_only=False, runner=None):
    # prevent a very rare case of interlaced multiprocess I/O
    log_flock(runner)
    msg2 = msg
    if color:
        msg2 = stringc(msg, color)
    if not log_only:
        if not stderr:
            try:
                print msg2
            except UnicodeEncodeError:
                print msg2.encode('utf-8')
        else:
            try:
                print >>sys.stderr, msg2
            except UnicodeEncodeError:
                print >>sys.stderr, msg2.encode('utf-8')
    if constants.DEFAULT_LOG_PATH != '':
        while msg.startswith("\n"):
            msg = msg.replace("\n","")
        if not screen_only:
            if color == 'red':
                logger.error(msg)
            else:
                logger.info(msg)
    log_unflock(runner)

def call_callback_module(method_name, *args, **kwargs):

    for callback_plugin in callback_plugins:
        # a plugin that set self.disabled to True will not be called
        # see osx_say.py example for such a plugin
        if getattr(callback_plugin, 'disabled', False):
            continue
        methods = [
            getattr(callback_plugin, method_name, None),
            getattr(callback_plugin, 'on_any', None)
        ]
        for method in methods:
            if method is not None:
                method(*args, **kwargs)

def vv(msg, host=None):
    return verbose(msg, host=host, caplevel=1)

def vvv(msg, host=None):
    return verbose(msg, host=host, caplevel=2)

def vvvv(msg, host=None):
    return verbose(msg, host=host, caplevel=3)

def verbose(msg, host=None, caplevel=2):
    msg = utils.sanitize_output(msg)
    if utils.VERBOSITY > caplevel:
        if host is None:
            display(msg, color='blue')
        else:
            display("<%s> %s" % (host, msg), color='blue')

class AggregateStats(object):
    ''' holds stats about per-host activity during playbook runs '''

    def __init__(self):

        self.processed   = {}
        self.failures    = {}
        self.ok          = {}
        self.dark        = {}
        self.changed     = {}
        self.skipped     = {}

    def _increment(self, what, host):
        ''' helper function to bump a statistic '''

        self.processed[host] = 1
        prev = (getattr(self, what)).get(host, 0)
        getattr(self, what)[host] = prev+1

    def compute(self, runner_results, setup=False, poll=False, ignore_errors=False):
        ''' walk through all results and increment stats '''

        for (host, value) in runner_results.get('contacted', {}).iteritems():
            if not ignore_errors and (('failed' in value and bool(value['failed'])) or
                ('failed_when_result' in value and [value['failed_when_result']] or ['rc' in value and value['rc'] != 0])[0]):
                self._increment('failures', host)
            elif 'skipped' in value and bool(value['skipped']):
                self._increment('skipped', host)
            elif 'changed' in value and bool(value['changed']):
                if not setup and not poll:
                    self._increment('changed', host)
                self._increment('ok', host)
            else:
                if not poll or ('finished' in value and bool(value['finished'])):
                    self._increment('ok', host)

        for (host, value) in runner_results.get('dark', {}).iteritems():
            self._increment('dark', host)


    def summarize(self, host):
        ''' return information about a particular host '''

        return dict(
            ok          = self.ok.get(host, 0),
            failures    = self.failures.get(host, 0),
            unreachable = self.dark.get(host,0),
            changed     = self.changed.get(host, 0),
            skipped     = self.skipped.get(host, 0)
        )

########################################################################

def regular_generic_msg(hostname, result, oneline, caption):
    ''' output on the result of a module run that is not command '''

    if not oneline:
        return "%s | %s >> %s\n" % (hostname, caption, utils.jsonify(result,format=True))
    else:
        return "%s | %s >> %s\n" % (hostname, caption, utils.jsonify(result))


def banner_cowsay(msg):

    if ": [" in msg:
        msg = msg.replace("[","")
        if msg.endswith("]"):
            msg = msg[:-1]
    runcmd = [cowsay,"-W", "60"]
    if noncow:
        runcmd.append('-f')
        runcmd.append(noncow)
    runcmd.append(msg)
    cmd = subprocess.Popen(runcmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (out, err) = cmd.communicate()
    return "%s\n" % out

def banner_normal(msg):

    width = 78 - len(msg)
    if width < 3:
        width = 3
    filler = "*" * width
    return "\n%s %s " % (msg, filler)

def banner(msg):
    if cowsay:
        try:
            return banner_cowsay(msg)
        except OSError:
            # somebody cleverly deleted cowsay or something during the PB run.  heh.
            return banner_normal(msg)
    return banner_normal(msg)

def command_generic_msg(hostname, result, oneline, caption):
    ''' output the result of a command run '''

    rc     = result.get('rc', '0')
    stdout = result.get('stdout','')
    stderr = result.get('stderr', '')
    msg    = result.get('msg', '')

    hostname = hostname.encode('utf-8')
    caption  = caption.encode('utf-8')

    if not oneline:
        buf = "%s | %s | rc=%s >>\n" % (hostname, caption, result.get('rc',0))
        if stdout:
            buf += stdout
        if stderr:
            buf += stderr
        if msg:
            buf += msg
        return buf + "\n"
    else:
        if stderr:
            return "%s | %s | rc=%s | (stdout) %s (stderr) %s" % (hostname, caption, rc, stdout, stderr)
        else:
            return "%s | %s | rc=%s | (stdout) %s" % (hostname, caption, rc, stdout)

def host_report_msg(hostname, module_name, result, oneline):
    ''' summarize the JSON results for a particular host '''

    failed = utils.is_failed(result)
    msg = ('', None)
    if module_name in [ 'command', 'shell', 'raw' ] and 'ansible_job_id' not in result and result.get('parsed',True) != False:
        if not failed:
            msg = (command_generic_msg(hostname, result, oneline, 'success'), 'green')
        else:
            msg = (command_generic_msg(hostname, result, oneline, 'FAILED'), 'red')
    else:
        if not failed:
            msg = (regular_generic_msg(hostname, result, oneline, 'success'), 'green')
        else:
            msg = (regular_generic_msg(hostname, result, oneline, 'FAILED'), 'red')
    return msg

###############################################

class DefaultRunnerCallbacks(object):
    ''' no-op callbacks for API usage of Runner() if no callbacks are specified '''

    def __init__(self):
        pass

    def on_failed(self, host, res, ignore_errors=False):
        call_callback_module('runner_on_failed', host, res, ignore_errors=ignore_errors)

    def on_ok(self, host, res):
        call_callback_module('runner_on_ok', host, res)

    def on_error(self, host, msg):
        call_callback_module('runner_on_error', host, msg)

    def on_skipped(self, host, item=None):
        call_callback_module('runner_on_skipped', host, item=item)

    def on_unreachable(self, host, res):
        call_callback_module('runner_on_unreachable', host, res)

    def on_no_hosts(self):
        call_callback_module('runner_on_no_hosts')

    def on_async_poll(self, host, res, jid, clock):
        call_callback_module('runner_on_async_poll', host, res, jid, clock)

    def on_async_ok(self, host, res, jid):
        call_callback_module('runner_on_async_ok', host, res, jid)

    def on_async_failed(self, host, res, jid):
        call_callback_module('runner_on_async_failed', host, res, jid)

    def on_file_diff(self, host, diff):
        call_callback_module('runner_on_file_diff', host, diff)

########################################################################

class CliRunnerCallbacks(DefaultRunnerCallbacks):
    ''' callbacks for use by /usr/bin/ansible '''

    def __init__(self):
        # set by /usr/bin/ansible later
        self.options = None
        self._async_notified = {}

    def on_failed(self, host, res, ignore_errors=False):
        self._on_any(host,res)
        super(CliRunnerCallbacks, self).on_failed(host, res, ignore_errors=ignore_errors)

    def on_ok(self, host, res):
        # hide magic variables used for ansible-playbook
        res.pop('verbose_override', None)
        res.pop('verbose_always', None)

        self._on_any(host,res)
        super(CliRunnerCallbacks, self).on_ok(host, res)

    def on_unreachable(self, host, res):
        if type(res) == dict:
            res = res.get('msg','')
        display("%s | FAILED => %s" % (host, res), stderr=True, color='red', runner=self.runner)
        if self.options.tree:
            utils.write_tree_file(
                self.options.tree, host,
                utils.jsonify(dict(failed=True, msg=res),format=True)
            )
        super(CliRunnerCallbacks, self).on_unreachable(host, res)

    def on_skipped(self, host, item=None):
        display("%s | skipped" % (host), runner=self.runner)
        super(CliRunnerCallbacks, self).on_skipped(host, item)

    def on_error(self, host, err):
        display("err: [%s] => %s\n" % (host, err), stderr=True, runner=self.runner)
        super(CliRunnerCallbacks, self).on_error(host, err)

    def on_no_hosts(self):
        display("no hosts matched\n", stderr=True, runner=self.runner)
        super(CliRunnerCallbacks, self).on_no_hosts()

    def on_async_poll(self, host, res, jid, clock):
        if jid not in self._async_notified:
            self._async_notified[jid] = clock + 1
        if self._async_notified[jid] > clock:
            self._async_notified[jid] = clock
            display("<job %s> polling, %ss remaining" % (jid, clock), runner=self.runner)
        super(CliRunnerCallbacks, self).on_async_poll(host, res, jid, clock)

    def on_async_ok(self, host, res, jid):
        display("<job %s> finished on %s => %s"%(jid, host, utils.jsonify(res,format=True)), runner=self.runner)
        super(CliRunnerCallbacks, self).on_async_ok(host, res, jid)

    def on_async_failed(self, host, res, jid):
        display("<job %s> FAILED on %s => %s"%(jid, host, utils.jsonify(res,format=True)), color='red', stderr=True, runner=self.runner)
        super(CliRunnerCallbacks, self).on_async_failed(host,res,jid)

    def _on_any(self, host, result):
        result2 = result.copy()
        result2.pop('invocation', None)
        (msg, color) = host_report_msg(host, self.options.module_name, result2, self.options.one_line)
        display(msg, color=color, runner=self.runner)
        if self.options.tree:
            utils.write_tree_file(self.options.tree, host, utils.jsonify(result2,format=True))

    def on_file_diff(self, host, diff):
        display(utils.get_diff(diff), runner=self.runner)
        super(CliRunnerCallbacks, self).on_file_diff(host, diff)

########################################################################

class PlaybookRunnerCallbacks(DefaultRunnerCallbacks):
    ''' callbacks used for Runner() from /usr/bin/ansible-playbook '''

    def __init__(self, stats, verbose=None):

        if verbose is None:
            verbose = utils.VERBOSITY

        self.verbose = verbose
        self.stats = stats
        self._async_notified = {}

    def on_unreachable(self, host, results):
        item = None
        if type(results) == dict:
            item = results.get('item', None)
        if item:
            msg = "fatal: [%s] => (item=%s) => %s" % (host, item, results)
        else:
            msg = "fatal: [%s] => %s" % (host, results)
        display(msg, color='red', runner=self.runner)
        super(PlaybookRunnerCallbacks, self).on_unreachable(host, results)

    def on_failed(self, host, results, ignore_errors=False):


        results2 = results.copy()
        results2.pop('invocation', None)

        item = results2.get('item', None)
        parsed = results2.get('parsed', True)
        module_msg = ''
        if not parsed:
            module_msg  = results2.pop('msg', None)
        stderr = results2.pop('stderr', None)
        stdout = results2.pop('stdout', None)
        returned_msg = results2.pop('msg', None)

        if item:
            msg = "failed: [%s] => (item=%s) => %s" % (host, item, utils.jsonify(results2))
        else:
            msg = "failed: [%s] => %s" % (host, utils.jsonify(results2))
        display(msg, color='red', runner=self.runner)

        if stderr:
            display("stderr: %s" % stderr, color='red', runner=self.runner)
        if stdout:
            display("stdout: %s" % stdout, color='red', runner=self.runner)
        if returned_msg:
            display("msg: %s" % returned_msg, color='red', runner=self.runner)
        if not parsed and module_msg:
            display("invalid output was: %s" % module_msg, color='red', runner=self.runner)
        if ignore_errors:
            display("...ignoring", color='cyan', runner=self.runner)
        super(PlaybookRunnerCallbacks, self).on_failed(host, results, ignore_errors=ignore_errors)

    def on_ok(self, host, host_result):

        item = host_result.get('item', None)

        host_result2 = host_result.copy()
        host_result2.pop('invocation', None)
        verbose_always = host_result2.pop('verbose_always', False)
        changed = host_result.get('changed', False)
        ok_or_changed = 'ok'
        if changed:
            ok_or_changed = 'changed'

        # show verbose output for non-setup module results if --verbose is used
        msg = ''
        if (not self.verbose or host_result2.get("verbose_override",None) is not
                None) and not verbose_always:
            if item:
                msg = "%s: [%s] => (item=%s)" % (ok_or_changed, host, item)
            else:
                if 'ansible_job_id' not in host_result or 'finished' in host_result:
                    msg = "%s: [%s]" % (ok_or_changed, host)
        else:
            # verbose ...
            if item:
                msg = "%s: [%s] => (item=%s) => %s" % (ok_or_changed, host, item, utils.jsonify(host_result2, format=verbose_always))
            else:
                if 'ansible_job_id' not in host_result or 'finished' in host_result2:
                    msg = "%s: [%s] => %s" % (ok_or_changed, host, utils.jsonify(host_result2, format=verbose_always))

        if msg != '':
            if not changed:
                display(msg, color='green', runner=self.runner)
            else:
                display(msg, color='yellow', runner=self.runner)
        super(PlaybookRunnerCallbacks, self).on_ok(host, host_result)

    def on_error(self, host, err):

        item = err.get('item', None)
        msg = ''
        if item:
            msg = "err: [%s] => (item=%s) => %s" % (host, item, err)
        else:
            msg = "err: [%s] => %s" % (host, err)

        display(msg, color='red', stderr=True, runner=self.runner)
        super(PlaybookRunnerCallbacks, self).on_error(host, err)

    def on_skipped(self, host, item=None):
        if constants.DISPLAY_SKIPPED_HOSTS:
            msg = ''
            if item:
                msg = "skipping: [%s] => (item=%s)" % (host, item)
            else:
                msg = "skipping: [%s]" % host
            display(msg, color='cyan', runner=self.runner)
            super(PlaybookRunnerCallbacks, self).on_skipped(host, item)

    def on_no_hosts(self):
        display("FATAL: no hosts matched or all hosts have already failed -- aborting\n", color='red', runner=self.runner)
        super(PlaybookRunnerCallbacks, self).on_no_hosts()

    def on_async_poll(self, host, res, jid, clock):
        if jid not in self._async_notified:
            self._async_notified[jid] = clock + 1
        if self._async_notified[jid] > clock:
            self._async_notified[jid] = clock
            msg = "<job %s> polling, %ss remaining"%(jid, clock)
            display(msg, color='cyan', runner=self.runner)
        super(PlaybookRunnerCallbacks, self).on_async_poll(host,res,jid,clock)

    def on_async_ok(self, host, res, jid):
        msg = "<job %s> finished on %s"%(jid, host)
        display(msg, color='cyan', runner=self.runner)
        super(PlaybookRunnerCallbacks, self).on_async_ok(host, res, jid)

    def on_async_failed(self, host, res, jid):
        msg = "<job %s> FAILED on %s" % (jid, host)
        display(msg, color='red', stderr=True, runner=self.runner)
        super(PlaybookRunnerCallbacks, self).on_async_failed(host,res,jid)

    def on_file_diff(self, host, diff):
        display(utils.get_diff(diff), runner=self.runner)
        super(PlaybookRunnerCallbacks, self).on_file_diff(host, diff)

########################################################################

class PlaybookCallbacks(object):
    ''' playbook.py callbacks used by /usr/bin/ansible-playbook '''

    def __init__(self, verbose=False):

        self.verbose = verbose

    def on_start(self):
        call_callback_module('playbook_on_start')

    def on_notify(self, host, handler):
        call_callback_module('playbook_on_notify', host, handler)

    def on_no_hosts_matched(self):
        display("skipping: no hosts matched", color='cyan')
        call_callback_module('playbook_on_no_hosts_matched')

    def on_no_hosts_remaining(self):
        display("\nFATAL: all hosts have already failed -- aborting", color='red')
        call_callback_module('playbook_on_no_hosts_remaining')

    def on_task_start(self, name, is_conditional):
        msg = "TASK: [%s]" % name
        if is_conditional:
            msg = "NOTIFIED: [%s]" % name

        if hasattr(self, 'start_at'):
            if name == self.start_at or fnmatch.fnmatch(name, self.start_at):
                # we found out match, we can get rid of this now
                del self.start_at
            elif self.task.role_name:
                # handle tasks prefixed with rolenames
                actual_name = name.split('|', 1)[1].lstrip()
                if actual_name == self.start_at or fnmatch.fnmatch(actual_name, self.start_at):
                    del self.start_at

        if hasattr(self, 'start_at'): # we still have start_at so skip the task
            self.skip_task = True
        elif hasattr(self, 'step') and self.step:
            msg = ('Perform task: %s (y/n/c): ' % name).encode(sys.stdout.encoding)
            resp = raw_input(msg)
            if resp.lower() in ['y','yes']:
                self.skip_task = False
                display(banner(msg))
            elif resp.lower() in ['c', 'continue']:
                self.skip_task = False
                self.step = False
                display(banner(msg))
            else:
                self.skip_task = True
        else:
            self.skip_task = False
            display(banner(msg))

        call_callback_module('playbook_on_task_start', name, is_conditional)

    def on_vars_prompt(self, varname, private=True, prompt=None, encrypt=None, confirm=False, salt_size=None, salt=None, default=None):

        if prompt and default is not None:
            msg = "%s [%s]: " % (prompt, default)
        elif prompt:
            msg = "%s: " % prompt
        else:
            msg = 'input for %s: ' % varname

        def prompt(prompt, private):
            msg = prompt.encode(sys.stdout.encoding)
            if private:
                return getpass.getpass(msg)
            return raw_input(msg)


        if confirm:
            while True:
                result = prompt(msg, private)
                second = prompt("confirm " + msg, private)
                if result == second:
                    break
                display("***** VALUES ENTERED DO NOT MATCH ****")
        else:
            result = prompt(msg, private)

        # if result is false and default is not None
        if not result and default:
            result = default


        if encrypt:
            result = utils.do_encrypt(result,encrypt,salt_size,salt)

        call_callback_module( 'playbook_on_vars_prompt', varname, private=private, prompt=prompt,
                               encrypt=encrypt, confirm=confirm, salt_size=salt_size, salt=None, default=default
                            )

        return result

    def on_setup(self):
        display(banner("GATHERING FACTS"))
        call_callback_module('playbook_on_setup')

    def on_import_for_host(self, host, imported_file):
        msg = "%s: importing %s" % (host, imported_file)
        display(msg, color='cyan')
        call_callback_module('playbook_on_import_for_host', host, imported_file)

    def on_not_import_for_host(self, host, missing_file):
        msg = "%s: not importing file: %s" % (host, missing_file)
        display(msg, color='cyan')
        call_callback_module('playbook_on_not_import_for_host', host, missing_file)

    def on_play_start(self, pattern):
        display(banner("PLAY [%s]" % pattern))
        call_callback_module('playbook_on_play_start', pattern)

    def on_stats(self, stats):
        call_callback_module('playbook_on_stats', stats)



########NEW FILE########
__FILENAME__ = noop
# (C) 2012-2014, Michael DeHaan, <michael.dehaan@gmail.com>

# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.


class CallbackModule(object):

    """
    this is an example ansible callback file that does nothing.  You can drop
    other classes in the same directory to define your own handlers.  Methods
    you do not use can be omitted. If self.disabled is set to True, the plugin
    methods will not be called.

    example uses include: logging, emailing, storing info, etc
    """

    def __init__(self):
        #if foo:
        #    self.disabled = True
        pass

    def on_any(self, *args, **kwargs):
        pass

    def runner_on_failed(self, host, res, ignore_errors=False):
        pass

    def runner_on_ok(self, host, res):
        pass

    def runner_on_error(self, host, msg):
        pass

    def runner_on_skipped(self, host, item=None):
        pass

    def runner_on_unreachable(self, host, res):
        pass

    def runner_on_no_hosts(self):
        pass

    def runner_on_async_poll(self, host, res, jid, clock):
        pass

    def runner_on_async_ok(self, host, res, jid):
        pass

    def runner_on_async_failed(self, host, res, jid):
        pass

    def playbook_on_start(self):
        pass

    def playbook_on_notify(self, host, handler):
        pass

    def playbook_on_no_hosts_matched(self):
        pass

    def playbook_on_no_hosts_remaining(self):
        pass

    def playbook_on_task_start(self, name, is_conditional):
        pass

    def playbook_on_vars_prompt(self, varname, private=True, prompt=None, encrypt=None, confirm=False, salt_size=None, salt=None, default=None):
        pass

    def playbook_on_setup(self):
        pass

    def playbook_on_import_for_host(self, host, imported_file):
        pass

    def playbook_on_not_import_for_host(self, host, missing_file):
        pass

    def playbook_on_play_start(self, pattern):
        pass

    def playbook_on_stats(self, stats):
        pass


########NEW FILE########
__FILENAME__ = color
# (c) 2012-2014, Michael DeHaan <michael.dehaan@gmail.com>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

import sys
import constants

ANSIBLE_COLOR=True
if constants.ANSIBLE_NOCOLOR:
    ANSIBLE_COLOR=False
elif not hasattr(sys.stdout, 'isatty') or not sys.stdout.isatty():
    ANSIBLE_COLOR=False
else:
    try:
        import curses
        curses.setupterm()
        if curses.tigetnum('colors') < 0:
            ANSIBLE_COLOR=False
    except ImportError:
        # curses library was not found
        pass
    except curses.error:
        # curses returns an error (e.g. could not find terminal)
        ANSIBLE_COLOR=False

if constants.ANSIBLE_FORCE_COLOR:
        ANSIBLE_COLOR=True

# --- begin "pretty"
#
# pretty - A miniature library that provides a Python print and stdout
# wrapper that makes colored terminal text easier to use (eg. without
# having to mess around with ANSI escape sequences). This code is public
# domain - there is no license except that you must leave this header.
#
# Copyright (C) 2008 Brian Nez <thedude at bri1 dot com>
#
# http://nezzen.net/2008/06/23/colored-text-in-python-using-ansi-escape-sequences/

codeCodes = {
    'black':     '0;30', 'bright gray':    '0;37',
    'blue':      '0;34', 'white':          '1;37',
    'green':     '0;32', 'bright blue':    '1;34',
    'cyan':      '0;36', 'bright green':   '1;32',
    'red':       '0;31', 'bright cyan':    '1;36',
    'purple':    '0;35', 'bright red':     '1;31',
    'yellow':    '0;33', 'bright purple':  '1;35',
    'dark gray': '1;30', 'bright yellow':  '1;33',
    'normal':    '0'
}

def stringc(text, color):
    """String in color."""

    if ANSIBLE_COLOR:
        return "\033["+codeCodes[color]+"m"+text+"\033[0m"
    else:
        return text

# --- end "pretty"


########NEW FILE########
__FILENAME__ = constants
# (c) 2012-2014, Michael DeHaan <michael.dehaan@gmail.com>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

import os
import pwd
import sys
import ConfigParser
from string import ascii_letters, digits

# copied from utils, avoid circular reference fun :)
def mk_boolean(value):
    if value is None:
        return False
    val = str(value)
    if val.lower() in [ "true", "t", "y", "1", "yes" ]:
        return True
    else:
        return False

def get_config(p, section, key, env_var, default, boolean=False, integer=False, floating=False):
    ''' return a configuration variable with casting '''
    value = _get_config(p, section, key, env_var, default)
    if boolean:
        return mk_boolean(value)
    if value and integer:
        return int(value)
    if value and floating:
        return float(value)
    return value

def _get_config(p, section, key, env_var, default):
    ''' helper function for get_config '''
    if env_var is not None:
        value = os.environ.get(env_var, None)
        if value is not None:
            return value
    if p is not None:
        try:
            return p.get(section, key, raw=True)
        except:
            return default
    return default

def load_config_file():
    ''' Load Config File order(first found is used): ENV, CWD, HOME, /etc/ansible '''

    p = ConfigParser.ConfigParser()

    path0 = os.getenv("ANSIBLE_CONFIG", None)
    if path0 is not None:
        path0 = os.path.expanduser(path0)
    path1 = os.getcwd() + "/ansible.cfg"
    path2 = os.path.expanduser("~/.ansible.cfg")
    path3 = "/etc/ansible/ansible.cfg"

    for path in [path0, path1, path2, path3]:
        if path is not None and os.path.exists(path):
            p.read(path)
            return p
    return None

def shell_expand_path(path):
    ''' shell_expand_path is needed as os.path.expanduser does not work
        when path is None, which is the default for ANSIBLE_PRIVATE_KEY_FILE '''
    if path:
        path = os.path.expanduser(path)
    return path

p = load_config_file()

active_user   = pwd.getpwuid(os.geteuid())[0]

# Needed so the RPM can call setup.py and have modules land in the
# correct location. See #1277 for discussion
if getattr(sys, "real_prefix", None):
    # in a virtualenv
    DIST_MODULE_PATH = os.path.join(sys.prefix, 'share/ansible/')
else:
    DIST_MODULE_PATH = '/usr/share/ansible/'

# check all of these extensions when looking for yaml files for things like
# group variables -- really anything we can load
YAML_FILENAME_EXTENSIONS = [ "", ".yml", ".yaml", ".json" ]

# sections in config file
DEFAULTS='defaults'

# configurable things
DEFAULT_HOST_LIST         = shell_expand_path(get_config(p, DEFAULTS, 'hostfile', 'ANSIBLE_HOSTS', '/etc/ansible/hosts'))
DEFAULT_MODULE_PATH       = get_config(p, DEFAULTS, 'library',          'ANSIBLE_LIBRARY',          DIST_MODULE_PATH)
DEFAULT_ROLES_PATH        = get_config(p, DEFAULTS, 'roles_path',       'ANSIBLE_ROLES_PATH',       '/etc/ansible/roles')
DEFAULT_REMOTE_TMP        = shell_expand_path(get_config(p, DEFAULTS, 'remote_tmp',       'ANSIBLE_REMOTE_TEMP',      '$HOME/.ansible/tmp'))
DEFAULT_MODULE_NAME       = get_config(p, DEFAULTS, 'module_name',      None,                       'command')
DEFAULT_PATTERN           = get_config(p, DEFAULTS, 'pattern',          None,                       '*')
DEFAULT_FORKS             = get_config(p, DEFAULTS, 'forks',            'ANSIBLE_FORKS',            5, integer=True)
DEFAULT_MODULE_ARGS       = get_config(p, DEFAULTS, 'module_args',      'ANSIBLE_MODULE_ARGS',      '')
DEFAULT_MODULE_LANG       = get_config(p, DEFAULTS, 'module_lang',      'ANSIBLE_MODULE_LANG',      'en_US.UTF-8')
DEFAULT_TIMEOUT           = get_config(p, DEFAULTS, 'timeout',          'ANSIBLE_TIMEOUT',          10, integer=True)
DEFAULT_POLL_INTERVAL     = get_config(p, DEFAULTS, 'poll_interval',    'ANSIBLE_POLL_INTERVAL',    15, integer=True)
DEFAULT_REMOTE_USER       = get_config(p, DEFAULTS, 'remote_user',      'ANSIBLE_REMOTE_USER',      active_user)
DEFAULT_ASK_PASS          = get_config(p, DEFAULTS, 'ask_pass',  'ANSIBLE_ASK_PASS',    False, boolean=True)
DEFAULT_PRIVATE_KEY_FILE  = shell_expand_path(get_config(p, DEFAULTS, 'private_key_file', 'ANSIBLE_PRIVATE_KEY_FILE', None))
DEFAULT_SUDO_USER         = get_config(p, DEFAULTS, 'sudo_user',        'ANSIBLE_SUDO_USER',        'root')
DEFAULT_ASK_SUDO_PASS     = get_config(p, DEFAULTS, 'ask_sudo_pass',    'ANSIBLE_ASK_SUDO_PASS',    False, boolean=True)
DEFAULT_REMOTE_PORT       = get_config(p, DEFAULTS, 'remote_port',      'ANSIBLE_REMOTE_PORT',      None, integer=True)
DEFAULT_ASK_VAULT_PASS    = get_config(p, DEFAULTS, 'ask_vault_pass',    'ANSIBLE_ASK_VAULT_PASS',    False, boolean=True)
DEFAULT_TRANSPORT         = get_config(p, DEFAULTS, 'transport',        'ANSIBLE_TRANSPORT',        'smart')
DEFAULT_SCP_IF_SSH        = get_config(p, 'ssh_connection', 'scp_if_ssh',       'ANSIBLE_SCP_IF_SSH',       False, boolean=True)
DEFAULT_MANAGED_STR       = get_config(p, DEFAULTS, 'ansible_managed',  None,           'Ansible managed: {file} modified on %Y-%m-%d %H:%M:%S by {uid} on {host}')
DEFAULT_SYSLOG_FACILITY   = get_config(p, DEFAULTS, 'syslog_facility',  'ANSIBLE_SYSLOG_FACILITY', 'LOG_USER')
DEFAULT_KEEP_REMOTE_FILES = get_config(p, DEFAULTS, 'keep_remote_files', 'ANSIBLE_KEEP_REMOTE_FILES', False, boolean=True)
DEFAULT_SUDO              = get_config(p, DEFAULTS, 'sudo', 'ANSIBLE_SUDO', False, boolean=True)
DEFAULT_SUDO_EXE          = get_config(p, DEFAULTS, 'sudo_exe', 'ANSIBLE_SUDO_EXE', 'sudo')
DEFAULT_SUDO_FLAGS        = get_config(p, DEFAULTS, 'sudo_flags', 'ANSIBLE_SUDO_FLAGS', '-H')
DEFAULT_HASH_BEHAVIOUR    = get_config(p, DEFAULTS, 'hash_behaviour', 'ANSIBLE_HASH_BEHAVIOUR', 'replace')
DEFAULT_JINJA2_EXTENSIONS = get_config(p, DEFAULTS, 'jinja2_extensions', 'ANSIBLE_JINJA2_EXTENSIONS', None)
DEFAULT_EXECUTABLE        = get_config(p, DEFAULTS, 'executable', 'ANSIBLE_EXECUTABLE', '/bin/sh')
DEFAULT_SU_EXE = get_config(p, DEFAULTS, 'su_exe', 'ANSIBLE_SU_EXE', 'su')
DEFAULT_SU = get_config(p, DEFAULTS, 'su', 'ANSIBLE_SU', False, boolean=True)
DEFAULT_SU_FLAGS = get_config(p, DEFAULTS, 'su_flags', 'ANSIBLE_SU_FLAGS', '')
DEFAULT_SU_USER = get_config(p, DEFAULTS, 'su_user', 'ANSIBLE_SU_USER', 'root')
DEFAULT_ASK_SU_PASS = get_config(p, DEFAULTS, 'ask_su_pass', 'ANSIBLE_ASK_SU_PASS', False, boolean=True)
DEFAULT_GATHERING = get_config(p, DEFAULTS, 'gathering', 'ANSIBLE_GATHERING', 'implicit').lower()

DEFAULT_ACTION_PLUGIN_PATH     = get_config(p, DEFAULTS, 'action_plugins',     'ANSIBLE_ACTION_PLUGINS', '/usr/share/ansible_plugins/action_plugins')
DEFAULT_CALLBACK_PLUGIN_PATH   = get_config(p, DEFAULTS, 'callback_plugins',   'ANSIBLE_CALLBACK_PLUGINS', '/usr/share/ansible_plugins/callback_plugins')
DEFAULT_CONNECTION_PLUGIN_PATH = get_config(p, DEFAULTS, 'connection_plugins', 'ANSIBLE_CONNECTION_PLUGINS', '/usr/share/ansible_plugins/connection_plugins')
DEFAULT_LOOKUP_PLUGIN_PATH     = get_config(p, DEFAULTS, 'lookup_plugins',     'ANSIBLE_LOOKUP_PLUGINS', '/usr/share/ansible_plugins/lookup_plugins')
DEFAULT_VARS_PLUGIN_PATH       = get_config(p, DEFAULTS, 'vars_plugins',       'ANSIBLE_VARS_PLUGINS', '/usr/share/ansible_plugins/vars_plugins')
DEFAULT_FILTER_PLUGIN_PATH     = get_config(p, DEFAULTS, 'filter_plugins',     'ANSIBLE_FILTER_PLUGINS', '/usr/share/ansible_plugins/filter_plugins')
DEFAULT_LOG_PATH               = shell_expand_path(get_config(p, DEFAULTS, 'log_path',           'ANSIBLE_LOG_PATH', ''))

ANSIBLE_FORCE_COLOR            = get_config(p, DEFAULTS, 'force_color', 'ANSIBLE_FORCE_COLOR', None, boolean=True)
ANSIBLE_NOCOLOR                = get_config(p, DEFAULTS, 'nocolor', 'ANSIBLE_NOCOLOR', None, boolean=True)
ANSIBLE_NOCOWS                 = get_config(p, DEFAULTS, 'nocows', 'ANSIBLE_NOCOWS', None, boolean=True)
DISPLAY_SKIPPED_HOSTS          = get_config(p, DEFAULTS, 'display_skipped_hosts', 'DISPLAY_SKIPPED_HOSTS', True, boolean=True)
DEFAULT_UNDEFINED_VAR_BEHAVIOR = get_config(p, DEFAULTS, 'error_on_undefined_vars', 'ANSIBLE_ERROR_ON_UNDEFINED_VARS', True, boolean=True)
HOST_KEY_CHECKING              = get_config(p, DEFAULTS, 'host_key_checking',  'ANSIBLE_HOST_KEY_CHECKING',    True, boolean=True)
SYSTEM_WARNINGS                = get_config(p, DEFAULTS, 'system_warnings', 'ANSIBLE_SYSTEM_WARNINGS', True, boolean=True)
DEPRECATION_WARNINGS           = get_config(p, DEFAULTS, 'deprecation_warnings', 'ANSIBLE_DEPRECATION_WARNINGS', True, boolean=True)

# CONNECTION RELATED
ANSIBLE_SSH_ARGS               = get_config(p, 'ssh_connection', 'ssh_args', 'ANSIBLE_SSH_ARGS', None)
ANSIBLE_SSH_CONTROL_PATH       = get_config(p, 'ssh_connection', 'control_path', 'ANSIBLE_SSH_CONTROL_PATH', "%(directory)s/ansible-ssh-%%h-%%p-%%r")
ANSIBLE_SSH_PIPELINING         = get_config(p, 'ssh_connection', 'pipelining', 'ANSIBLE_SSH_PIPELINING', False, boolean=True)
PARAMIKO_RECORD_HOST_KEYS      = get_config(p, 'paramiko_connection', 'record_host_keys', 'ANSIBLE_PARAMIKO_RECORD_HOST_KEYS', True, boolean=True)
# obsolete -- will be formally removed in 1.6
ZEROMQ_PORT                    = get_config(p, 'fireball_connection', 'zeromq_port', 'ANSIBLE_ZEROMQ_PORT', 5099, integer=True)
ACCELERATE_PORT                = get_config(p, 'accelerate', 'accelerate_port', 'ACCELERATE_PORT', 5099, integer=True)
ACCELERATE_TIMEOUT             = get_config(p, 'accelerate', 'accelerate_timeout', 'ACCELERATE_TIMEOUT', 30, integer=True)
ACCELERATE_CONNECT_TIMEOUT     = get_config(p, 'accelerate', 'accelerate_connect_timeout', 'ACCELERATE_CONNECT_TIMEOUT', 1.0, floating=True)
ACCELERATE_DAEMON_TIMEOUT      = get_config(p, 'accelerate', 'accelerate_daemon_timeout', 'ACCELERATE_DAEMON_TIMEOUT', 30, integer=True)
ACCELERATE_KEYS_DIR            = get_config(p, 'accelerate', 'accelerate_keys_dir', 'ACCELERATE_KEYS_DIR', '~/.fireball.keys')
ACCELERATE_KEYS_DIR_PERMS      = get_config(p, 'accelerate', 'accelerate_keys_dir_perms', 'ACCELERATE_KEYS_DIR_PERMS', '700')
ACCELERATE_KEYS_FILE_PERMS     = get_config(p, 'accelerate', 'accelerate_keys_file_perms', 'ACCELERATE_KEYS_FILE_PERMS', '600')
ACCELERATE_MULTI_KEY           = get_config(p, 'accelerate', 'accelerate_multi_key', 'ACCELERATE_MULTI_KEY', False, boolean=True)
PARAMIKO_PTY                   = get_config(p, 'paramiko_connection', 'pty', 'ANSIBLE_PARAMIKO_PTY', True, boolean=True)

# characters included in auto-generated passwords
DEFAULT_PASSWORD_CHARS = ascii_letters + digits + ".,:-_"

# non-configurable things
DEFAULT_SUDO_PASS         = None
DEFAULT_REMOTE_PASS       = None
DEFAULT_SUBSET            = None
DEFAULT_SU_PASS           = None
VAULT_VERSION_MIN         = 1.0
VAULT_VERSION_MAX         = 1.0

########NEW FILE########
__FILENAME__ = errors
# (c) 2012-2014, Michael DeHaan <michael.dehaan@gmail.com>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

class AnsibleError(Exception):
    ''' The base Ansible exception from which all others should subclass '''

    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return self.msg

class AnsibleFileNotFound(AnsibleError):
    pass

class AnsibleConnectionFailed(AnsibleError):
    pass

class AnsibleYAMLValidationFailed(AnsibleError):
    pass

class AnsibleUndefinedVariable(AnsibleError):
    pass

class AnsibleFilterError(AnsibleError):
    pass

########NEW FILE########
__FILENAME__ = dir
# (c) 2013, Daniel Hokka Zakrisson <daniel@hozac.com>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

#############################################

import os
import ansible.constants as C
from ansible.inventory.host import Host
from ansible.inventory.group import Group
from ansible.inventory.ini import InventoryParser
from ansible.inventory.script import InventoryScript
from ansible import utils
from ansible import errors

class InventoryDirectory(object):
    ''' Host inventory parser for ansible using a directory of inventories. '''

    def __init__(self, filename=C.DEFAULT_HOST_LIST):
        self.names = os.listdir(filename)
        self.names.sort()
        self.directory = filename
        self.parsers = []
        self.hosts = {}
        self.groups = {}

        for i in self.names:

            # Skip files that end with certain extensions or characters
            if any(i.endswith(ext) for ext in ("~", ".orig", ".bak", ".ini", ".retry", ".pyc", ".pyo")):
                continue
            # Skip hidden files
            if i.startswith('.') and not i.startswith('./'):
                continue
            # These are things inside of an inventory basedir
            if i in ("host_vars", "group_vars", "vars_plugins"):
                continue
            fullpath = os.path.join(self.directory, i)
            if os.path.isdir(fullpath):
                parser = InventoryDirectory(filename=fullpath)
            elif utils.is_executable(fullpath):
                parser = InventoryScript(filename=fullpath)
            else:
                parser = InventoryParser(filename=fullpath)
            self.parsers.append(parser)
            # This takes a lot of code because we can't directly use any of the objects, as they have to blend
            for name, group in parser.groups.iteritems():
                if name not in self.groups:
                    self.groups[name] = group
                else:
                    # group is already there, copy variables
                    # note: depth numbers on duplicates may be bogus
                    for k, v in group.get_variables().iteritems():
                        self.groups[name].set_variable(k, v)
                for host in group.get_hosts():
                    if host.name not in self.hosts:
                        self.hosts[host.name] = host
                    else:
                        # host is already there, copy variables
                        # note: depth numbers on duplicates may be bogus
                        for k, v in host.vars.iteritems():
                            self.hosts[host.name].set_variable(k, v)
                    self.groups[name].add_host(self.hosts[host.name])

            # This needs to be a second loop to ensure all the parent groups exist
            for name, group in parser.groups.iteritems():
                for ancestor in group.get_ancestors():
                    self.groups[ancestor.name].add_child_group(self.groups[name])

    def get_host_variables(self, host):
        """ Gets additional host variables from all inventories """
        vars = {}
        for i in self.parsers:
            vars.update(i.get_host_variables(host))
        return vars


########NEW FILE########
__FILENAME__ = expand_hosts
# (c) 2012, Zettar Inc.
# Written by Chin Fang <fangchin@zettar.com>
#
# This file is part of Ansible
#
# This module is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this software.  If not, see <http://www.gnu.org/licenses/>.
#

'''
This module is for enhancing ansible's inventory parsing capability such
that it can deal with hostnames specified using a simple pattern in the
form of [beg:end], example: [1:5], [a:c], [D:G]. If beg is not specified,
it defaults to 0.

If beg is given and is left-zero-padded, e.g. '001', it is taken as a
formatting hint when the range is expanded. e.g. [001:010] is to be
expanded into 001, 002 ...009, 010.

Note that when beg is specified with left zero padding, then the length of
end must be the same as that of beg, else a exception is raised.
'''
import string

from ansible import errors

def detect_range(line = None):
    '''
    A helper function that checks a given host line to see if it contains
    a range pattern descibed in the docstring above.

    Returnes True if the given line contains a pattern, else False.
    '''
    if 0 <= line.find("[") < line.find(":") < line.find("]"):
        return True
    else:
        return False

def expand_hostname_range(line = None):
    '''
    A helper function that expands a given line that contains a pattern
    specified in top docstring, and returns a list that consists of the
    expanded version.

    The '[' and ']' characters are used to maintain the pseudo-code
    appearance. They are replaced in this function with '|' to ease
    string splitting.

    References: http://ansible.github.com/patterns.html#hosts-and-groups
    '''
    all_hosts = []
    if line:
        # A hostname such as db[1:6]-node is considered to consists
        # three parts:
        # head: 'db'
        # nrange: [1:6]; range() is a built-in. Can't use the name
        # tail: '-node'

        # Add support for multiple ranges in a host so:
        # db[01:10:3]node-[01:10]
        # - to do this we split off at the first [...] set, getting the list
        #   of hosts and then repeat until none left.
        # - also add an optional third parameter which contains the step. (Default: 1)
        #   so range can be [01:10:2] -> 01 03 05 07 09
        # FIXME: make this work for alphabetic sequences too.

        (head, nrange, tail) = line.replace('[','|',1).replace(']','|',1).split('|')
        bounds = nrange.split(":")
        if len(bounds) != 2 and len(bounds) != 3:
            raise errors.AnsibleError("host range incorrectly specified")
        beg = bounds[0]
        end = bounds[1]
        if len(bounds) == 2:
            step = 1
        else:
            step = bounds[2]
        if not beg:
            beg = "0"
        if not end:
            raise errors.AnsibleError("host range end value missing")
        if beg[0] == '0' and len(beg) > 1:
            rlen = len(beg) # range length formatting hint
            if rlen != len(end):
                raise errors.AnsibleError("host range format incorrectly specified!")
            fill = lambda _: str(_).zfill(rlen)  # range sequence
        else:
            fill = str

        try:
            i_beg = string.ascii_letters.index(beg)
            i_end = string.ascii_letters.index(end)
            if i_beg > i_end:
                raise errors.AnsibleError("host range format incorrectly specified!")
            seq = string.ascii_letters[i_beg:i_end+1]
        except ValueError:  # not a alpha range
            seq = range(int(beg), int(end)+1, int(step))

        for rseq in seq:
            hname = ''.join((head, fill(rseq), tail))

            if detect_range(hname):
                all_hosts.extend( expand_hostname_range( hname ) )
            else:
                all_hosts.append(hname)

        return all_hosts

########NEW FILE########
__FILENAME__ = group
# (c) 2012-2014, Michael DeHaan <michael.dehaan@gmail.com>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

class Group(object):
    ''' a group of ansible hosts '''

    __slots__ = [ 'name', 'hosts', 'vars', 'child_groups', 'parent_groups', 'depth', '_hosts_cache' ]

    def __init__(self, name=None):

        self.depth = 0
        self.name = name
        self.hosts = []
        self.vars = {}
        self.child_groups = []
        self.parent_groups = []
        self.clear_hosts_cache()
        if self.name is None:
            raise Exception("group name is required")

    def add_child_group(self, group):

        if self == group:
            raise Exception("can't add group to itself")

        # don't add if it's already there
        if not group in self.child_groups:
            self.child_groups.append(group)
            group.depth = max([self.depth+1, group.depth])
            group.parent_groups.append(self)
            self.clear_hosts_cache()

    def add_host(self, host):

        self.hosts.append(host)
        host.add_group(self)
        self.clear_hosts_cache()

    def set_variable(self, key, value):

        self.vars[key] = value

    def clear_hosts_cache(self):

        self._hosts_cache = None
        for g in self.parent_groups:
            g.clear_hosts_cache()

    def get_hosts(self):

        if self._hosts_cache is None:
            self._hosts_cache = self._get_hosts()

        return self._hosts_cache

    def _get_hosts(self):

        hosts = []
        seen = {}
        for kid in self.child_groups:
            kid_hosts = kid.get_hosts()
            for kk in kid_hosts:
                if kk not in seen:
                    seen[kk] = 1
                    hosts.append(kk)
        for mine in self.hosts:
            if mine not in seen:
                seen[mine] = 1
                hosts.append(mine)
        return hosts

    def get_variables(self):
        return self.vars.copy()

    def _get_ancestors(self):

        results = {}
        for g in self.parent_groups:
            results[g.name] = g
            results.update(g._get_ancestors())
        return results

    def get_ancestors(self):

        return self._get_ancestors().values()


########NEW FILE########
__FILENAME__ = host
# (c) 2012-2014, Michael DeHaan <michael.dehaan@gmail.com>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

import ansible.constants as C
from ansible import utils

class Host(object):
    ''' a single ansible host '''

    __slots__ = [ 'name', 'vars', 'groups' ]

    def __init__(self, name=None, port=None):

        self.name = name
        self.vars = {}
        self.groups = []
        if port and port != C.DEFAULT_REMOTE_PORT:
            self.set_variable('ansible_ssh_port', int(port))

        if self.name is None:
            raise Exception("host name is required")

    def add_group(self, group):

        self.groups.append(group)

    def set_variable(self, key, value):

        self.vars[key]=value

    def get_groups(self):

        groups = {}
        for g in self.groups:
            groups[g.name] = g
            ancestors = g.get_ancestors()
            for a in ancestors:
                groups[a.name] = a
        return groups.values()

    def get_variables(self):

        results = {}
        groups = self.get_groups()
        for group in sorted(groups, key=lambda g: g.depth):
            results = utils.combine_vars(results, group.get_variables())
        results.update(self.vars)
        results['inventory_hostname'] = self.name
        results['inventory_hostname_short'] = self.name.split('.')[0]
        results['group_names'] = sorted([ g.name for g in groups if g.name != 'all'])
        return results



########NEW FILE########
__FILENAME__ = ini
# (c) 2012-2014, Michael DeHaan <michael.dehaan@gmail.com>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

#############################################

import ansible.constants as C
from ansible.inventory.host import Host
from ansible.inventory.group import Group
from ansible.inventory.expand_hosts import detect_range
from ansible.inventory.expand_hosts import expand_hostname_range
from ansible import errors
from ansible import utils
import shlex
import re
import ast

class InventoryParser(object):
    """
    Host inventory for ansible.
    """

    def __init__(self, filename=C.DEFAULT_HOST_LIST):

        with open(filename) as fh:
            self.lines = fh.readlines()
            self.groups = {}
            self.hosts = {}
            self._parse()

    def _parse(self):

        self._parse_base_groups()
        self._parse_group_children()
        self._parse_group_variables()
        return self.groups

    @staticmethod
    def _parse_value(v):
        if "#" not in v:
            try:
                return ast.literal_eval(v)
            # Using explicit exceptions.
            # Likely a string that literal_eval does not like. We wil then just set it.
            except ValueError:
                # For some reason this was thought to be malformed.
                pass
            except SyntaxError:
                # Is this a hash with an equals at the end?
                pass
        return v

    # [webservers]
    # alpha
    # beta:2345
    # gamma sudo=True user=root
    # delta asdf=jkl favcolor=red

    def _parse_base_groups(self):
        # FIXME: refactor

        ungrouped = Group(name='ungrouped')
        all = Group(name='all')
        all.add_child_group(ungrouped)

        self.groups = dict(all=all, ungrouped=ungrouped)
        active_group_name = 'ungrouped'

        for line in self.lines:
            line = utils.before_comment(line).strip()
            if line.startswith("[") and line.endswith("]"):
                active_group_name = line.replace("[","").replace("]","")
                if ":vars" in line or ":children" in line:
                    active_group_name = active_group_name.rsplit(":", 1)[0]
                    if active_group_name not in self.groups:
                        new_group = self.groups[active_group_name] = Group(name=active_group_name)
                        all.add_child_group(new_group)
                    active_group_name = None
                elif active_group_name not in self.groups:
                    new_group = self.groups[active_group_name] = Group(name=active_group_name)
                    all.add_child_group(new_group)
            elif line.startswith(";") or line == '':
                pass
            elif active_group_name:
                tokens = shlex.split(line)
                if len(tokens) == 0:
                    continue
                hostname = tokens[0]
                port = C.DEFAULT_REMOTE_PORT
                # Three cases to check:
                # 0. A hostname that contains a range pesudo-code and a port
                # 1. A hostname that contains just a port
                if hostname.count(":") > 1:
                    # Possible an IPv6 address, or maybe a host line with multiple ranges
                    # IPv6 with Port  XXX:XXX::XXX.port
                    # FQDN            foo.example.com
                    if hostname.count(".") == 1:
                        (hostname, port) = hostname.rsplit(".", 1)
                elif ("[" in hostname and
                    "]" in hostname and
                    ":" in hostname and
                    (hostname.rindex("]") < hostname.rindex(":")) or
                    ("]" not in hostname and ":" in hostname)):
                        (hostname, port) = hostname.rsplit(":", 1)

                hostnames = []
                if detect_range(hostname):
                    hostnames = expand_hostname_range(hostname)
                else:
                    hostnames = [hostname]

                for hn in hostnames:
                    host = None
                    if hn in self.hosts:
                        host = self.hosts[hn]
                    else:
                        host = Host(name=hn, port=port)
                        self.hosts[hn] = host
                    if len(tokens) > 1:
                        for t in tokens[1:]:
                            if t.startswith('#'):
                                break
                            try:
                                (k,v) = t.split("=", 1)
                            except ValueError, e:
                                raise errors.AnsibleError("Invalid ini entry: %s - %s" % (t, str(e)))
                            host.set_variable(k, self._parse_value(v))
                    self.groups[active_group_name].add_host(host)

    # [southeast:children]
    # atlanta
    # raleigh

    def _parse_group_children(self):
        group = None

        for line in self.lines:
            line = line.strip()
            if line is None or line == '':
                continue
            if line.startswith("[") and ":children]" in line:
                line = line.replace("[","").replace(":children]","")
                group = self.groups.get(line, None)
                if group is None:
                    group = self.groups[line] = Group(name=line)
            elif line.startswith("#") or line.startswith(";"):
                pass
            elif line.startswith("["):
                group = None
            elif group:
                kid_group = self.groups.get(line, None)
                if kid_group is None:
                    raise errors.AnsibleError("child group is not defined: (%s)" % line)
                else:
                    group.add_child_group(kid_group)


    # [webservers:vars]
    # http_port=1234
    # maxRequestsPerChild=200

    def _parse_group_variables(self):
        group = None
        for line in self.lines:
            line = line.strip()
            if line.startswith("[") and ":vars]" in line:
                line = line.replace("[","").replace(":vars]","")
                group = self.groups.get(line, None)
                if group is None:
                    raise errors.AnsibleError("can't add vars to undefined group: %s" % line)
            elif line.startswith("#") or line.startswith(";"):
                pass
            elif line.startswith("["):
                group = None
            elif line == '':
                pass
            elif group:
                if "=" not in line:
                    raise errors.AnsibleError("variables assigned to group must be in key=value form")
                else:
                    (k, v) = [e.strip() for e in line.split("=", 1)]
                    group.set_variable(k, self._parse_value(v))

    def get_host_variables(self, host):
        return {}

########NEW FILE########
__FILENAME__ = script
# (c) 2012-2014, Michael DeHaan <michael.dehaan@gmail.com>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

#############################################

import os
import subprocess
import ansible.constants as C
from ansible.inventory.host import Host
from ansible.inventory.group import Group
from ansible import utils
from ansible import errors
import sys

class InventoryScript(object):
    ''' Host inventory parser for ansible using external inventory scripts. '''

    def __init__(self, filename=C.DEFAULT_HOST_LIST):

        # Support inventory scripts that are not prefixed with some
        # path information but happen to be in the current working
        # directory when '.' is not in PATH.
        self.filename = os.path.abspath(filename)
        cmd = [ self.filename, "--list" ]
        try:
            sp = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except OSError, e:
            raise errors.AnsibleError("problem running %s (%s)" % (' '.join(cmd), e))
        (stdout, stderr) = sp.communicate()
        self.data = stdout
        # see comment about _meta below
        self.host_vars_from_top = None
        self.groups = self._parse(stderr)

    def _parse(self, err):

        all_hosts = {}
        self.raw  = utils.parse_json(self.data)
        all       = Group('all')
        groups    = dict(all=all)
        group     = None


        if 'failed' in self.raw:
            sys.stderr.write(err + "\n")
            raise errors.AnsibleError("failed to parse executable inventory script results: %s" % self.raw)

        for (group_name, data) in self.raw.items():
 
            # in Ansible 1.3 and later, a "_meta" subelement may contain
            # a variable "hostvars" which contains a hash for each host
            # if this "hostvars" exists at all then do not call --host for each
            # host.  This is for efficiency and scripts should still return data
            # if called with --host for backwards compat with 1.2 and earlier.

            if group_name == '_meta':
                if 'hostvars' in data:
                    self.host_vars_from_top = data['hostvars']
                    continue

            if group_name != all.name:
                group = groups[group_name] = Group(group_name)
            else:
                group = all
            host = None

            if not isinstance(data, dict):
                data = {'hosts': data}
            elif not any(k in data for k in ('hosts','vars')):
                data = {'hosts': [group_name], 'vars': data}

            if 'hosts' in data:

                for hostname in data['hosts']:
                    if not hostname in all_hosts:
                        all_hosts[hostname] = Host(hostname)
                    host = all_hosts[hostname]
                    group.add_host(host)

            if 'vars' in data:
                for k, v in data['vars'].iteritems():
                    if group.name == all.name:
                        all.set_variable(k, v)
                    else:
                        group.set_variable(k, v)
            if group.name != all.name:
                all.add_child_group(group)

        # Separate loop to ensure all groups are defined
        for (group_name, data) in self.raw.items():
            if group_name == '_meta':
                continue
            if isinstance(data, dict) and 'children' in data:
                for child_name in data['children']:
                    if child_name in groups:
                        groups[group_name].add_child_group(groups[child_name])
        return groups

    def get_host_variables(self, host):
        """ Runs <script> --host <hostname> to determine additional host variables """
        if self.host_vars_from_top is not None:
            got = self.host_vars_from_top.get(host.name, {})
            return got


        cmd = [self.filename, "--host", host.name]
        try:
            sp = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except OSError, e:
            raise errors.AnsibleError("problem running %s (%s)" % (' '.join(cmd), e))
        (out, err) = sp.communicate()
        return utils.parse_json(out)

########NEW FILE########
__FILENAME__ = group_vars
# (c) 2012-2014, Michael DeHaan <michael.dehaan@gmail.com>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

import os
import stat
import errno

from ansible import errors
from ansible import utils
import ansible.constants as C

def _load_vars(basepath, results, vault_password=None):
    """
    Load variables from any potential yaml filename combinations of basepath,
    returning result.
    """

    paths_to_check = [ "".join([basepath, ext]) 
                       for ext in C.YAML_FILENAME_EXTENSIONS ]

    found_paths = []

    for path in paths_to_check:
        found, results = _load_vars_from_path(path, results, vault_password=vault_password)
        if found:
            found_paths.append(path)


    # disallow the potentially confusing situation that there are multiple
    # variable files for the same name. For example if both group_vars/all.yml
    # and group_vars/all.yaml
    if len(found_paths) > 1:
        raise errors.AnsibleError("Multiple variable files found. "
            "There should only be one. %s" % ( found_paths, ))

    return results

def _load_vars_from_path(path, results, vault_password=None):
    """
    Robustly access the file at path and load variables, carefully reporting
    errors in a friendly/informative way.

    Return the tuple (found, new_results, )
    """

    try:
        # in the case of a symbolic link, we want the stat of the link itself,
        # not its target
        pathstat = os.lstat(path)
    except os.error, err:
        # most common case is that nothing exists at that path.
        if err.errno == errno.ENOENT:
            return False, results
        # otherwise this is a condition we should report to the user
        raise errors.AnsibleError(
            "%s is not accessible: %s." 
            " Please check its permissions." % ( path, err.strerror))

    # symbolic link
    if stat.S_ISLNK(pathstat.st_mode):
        try:
            target = os.path.realpath(path)
        except os.error, err2:
            raise errors.AnsibleError("The symbolic link at %s "
                "is not readable: %s.  Please check its permissions."
                % (path, err2.strerror, ))
        # follow symbolic link chains by recursing, so we repeat the same
        # permissions checks above and provide useful errors.
        return _load_vars_from_path(target, results)

    # directory
    if stat.S_ISDIR(pathstat.st_mode):

        # support organizing variables across multiple files in a directory
        return True, _load_vars_from_folder(path, results, vault_password=vault_password)

    # regular file
    elif stat.S_ISREG(pathstat.st_mode):
        data = utils.parse_yaml_from_file(path, vault_password=vault_password)
        if type(data) != dict:
            raise errors.AnsibleError(
                "%s must be stored as a dictionary/hash" % path)

        # combine vars overrides by default but can be configured to do a
        # hash merge in settings
        results = utils.combine_vars(results, data)
        return True, results

    # something else? could be a fifo, socket, device, etc.
    else:
        raise errors.AnsibleError("Expected a variable file or directory "
            "but found a non-file object at path %s" % (path, ))

def _load_vars_from_folder(folder_path, results, vault_password=None):
    """
    Load all variables within a folder recursively.
    """

    # this function and _load_vars_from_path are mutually recursive

    try:
        names = os.listdir(folder_path)
    except os.error, err:
        raise errors.AnsibleError(
            "This folder cannot be listed: %s: %s." 
             % ( folder_path, err.strerror))
        
    # evaluate files in a stable order rather than whatever order the
    # filesystem lists them.
    names.sort() 

    # do not parse hidden files or dirs, e.g. .svn/
    paths = [os.path.join(folder_path, name) for name in names if not name.startswith('.')]
    for path in paths:
        _found, results = _load_vars_from_path(path, results, vault_password=vault_password)
    return results

            
class VarsModule(object):

    """
    Loads variables from group_vars/<groupname> and host_vars/<hostname> in directories parallel
    to the inventory base directory or in the same directory as the playbook.  Variables in the playbook
    dir will win over the inventory dir if files are in both.
    """

    def __init__(self, inventory):

        """ constructor """

        self.inventory = inventory

    def run(self, host, vault_password=None):

        """ main body of the plugin, does actual loading """

        inventory = self.inventory
        basedir = inventory.playbook_basedir()
        if basedir is not None: 
            basedir = os.path.abspath(basedir)
        self.pb_basedir = basedir

        # sort groups by depth so deepest groups can override the less deep ones
        groupz = sorted(inventory.groups_for_host(host.name), key=lambda g: g.depth)
        groups = [ g.name for g in groupz ]
        inventory_basedir = inventory.basedir()

        results = {}
        scan_pass = 0

        # look in both the inventory base directory and the playbook base directory
        for basedir in [ inventory_basedir, self.pb_basedir ]:


            # this can happen from particular API usages, particularly if not run
            # from /usr/bin/ansible-playbook
            if basedir is None:
                continue

            scan_pass = scan_pass + 1

            # it's not an eror if the directory does not exist, keep moving
            if not os.path.exists(basedir):
                continue

            # save work of second scan if the directories are the same
            if inventory_basedir == self.pb_basedir and scan_pass != 1:
                continue

            # load vars in dir/group_vars/name_of_group
            for group in groups:
                base_path = os.path.join(basedir, "group_vars/%s" % group)
                results = _load_vars(base_path, results, vault_password=vault_password)

            # same for hostvars in dir/host_vars/name_of_host
            base_path = os.path.join(basedir, "host_vars/%s" % host.name)
            results = _load_vars(base_path, results, vault_password=vault_password)

        # all done, results is a dictionary of variables for this particular host.
        return results


########NEW FILE########
__FILENAME__ = module_common
# (c) 2013-2014, Michael DeHaan <michael.dehaan@gmail.com>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

# from python and deps
from cStringIO import StringIO
import inspect
import os
import shlex

# from Ansible
from ansible import errors
from ansible import utils
from ansible import constants as C

REPLACER = "#<<INCLUDE_ANSIBLE_MODULE_COMMON>>"
REPLACER_ARGS = "\"<<INCLUDE_ANSIBLE_MODULE_ARGS>>\""
REPLACER_COMPLEX = "\"<<INCLUDE_ANSIBLE_MODULE_COMPLEX_ARGS>>\""

class ModuleReplacer(object):

    """
    The Replacer is used to insert chunks of code into modules before
    transfer.  Rather than doing classical python imports, this allows for more
    efficient transfer in a no-bootstrapping scenario by not moving extra files
    over the wire, and also takes care of embedding arguments in the transferred
    modules.  

    This version is done in such a way that local imports can still be
    used in the module code, so IDEs don't have to be aware of what is going on.

    Example:

    from ansible.module_utils.basic import * 

    will result in a template evaluation of

    {{ include 'basic.py' }} 

    from the module_utils/ directory in the source tree.

    All modules are required to import at least basic, though there will also
    be other snippets.
    """

    # ******************************************************************************

    def __init__(self, strip_comments=False):
        this_file = inspect.getfile(inspect.currentframe())
        self.snippet_path = os.path.join(os.path.dirname(this_file), 'module_utils')
        self.strip_comments = strip_comments # TODO: implement

    # ******************************************************************************


    def slurp(self, path):
        if not os.path.exists(path):
            raise errors.AnsibleError("imported module support code does not exist at %s" % path)
        fd = open(path)
        data = fd.read()
        fd.close()
        return data

    def _find_snippet_imports(self, module_data, module_path):
        """
        Given the source of the module, convert it to a Jinja2 template to insert
        module code and return whether it's a new or old style module.
        """

        module_style = 'old'
        if REPLACER in module_data:
            module_style = 'new'
        elif 'from ansible.module_utils.' in module_data:
            module_style = 'new'
        elif 'WANT_JSON' in module_data:
            module_style = 'non_native_want_json'
      
        output = StringIO()
        lines = module_data.split('\n')
        snippet_names = []

        for line in lines:

            if REPLACER in line:
                output.write(self.slurp(os.path.join(self.snippet_path, "basic.py")))
                snippet_names.append('basic')
            elif line.startswith('from ansible.module_utils.'):
                tokens=line.split(".")
                import_error = False
                if len(tokens) != 3:
                    import_error = True
                if " import *" not in line:
                    import_error = True
                if import_error:
                    raise errors.AnsibleError("error importing module in %s, expecting format like 'from ansible.module_utils.basic import *'" % module_path)
                snippet_name = tokens[2].split()[0]
                snippet_names.append(snippet_name)
                output.write(self.slurp(os.path.join(self.snippet_path, snippet_name + ".py")))

            else:
                if self.strip_comments and line.startswith("#") or line == '':
                    pass
                output.write(line)
                output.write("\n")

        if len(snippet_names) > 0 and not 'basic' in snippet_names:
            raise errors.AnsibleError("missing required import in %s: from ansible.module_utils.basic import *" % module_path) 

        return (output.getvalue(), module_style)

    # ******************************************************************************

    def modify_module(self, module_path, complex_args, module_args, inject):

        with open(module_path) as f:

            # read in the module source
            module_data = f.read()

            (module_data, module_style) = self._find_snippet_imports(module_data, module_path)

            complex_args_json = utils.jsonify(complex_args)
            # We force conversion of module_args to str because module_common calls shlex.split,
            # a standard library function that incorrectly handles Unicode input before Python 2.7.3.
            try:
                encoded_args = repr(module_args.encode('utf-8'))
            except UnicodeDecodeError:
                encoded_args = repr(module_args)
            encoded_complex = repr(complex_args_json)

            # these strings should be part of the 'basic' snippet which is required to be included
            module_data = module_data.replace(REPLACER_ARGS, encoded_args)
            module_data = module_data.replace(REPLACER_COMPLEX, encoded_complex)

            if module_style == 'new':
                facility = C.DEFAULT_SYSLOG_FACILITY
                if 'ansible_syslog_facility' in inject:
                    facility = inject['ansible_syslog_facility']
                module_data = module_data.replace('syslog.LOG_USER', "syslog.%s" % facility)

            lines = module_data.split("\n")
            shebang = None
            if lines[0].startswith("#!"):
                shebang = lines[0].strip()
                args = shlex.split(str(shebang[2:]))
                interpreter = args[0]
                interpreter_config = 'ansible_%s_interpreter' % os.path.basename(interpreter)

                if interpreter_config in inject:
                    lines[0] = shebang = "#!%s %s" % (inject[interpreter_config], " ".join(args[1:]))
                    module_data = "\n".join(lines)

            return (module_data, module_style, shebang)


########NEW FILE########
__FILENAME__ = basic
# This code is part of Ansible, but is an independent component.
# This particular file snippet, and this file snippet only, is BSD licensed.
# Modules you write using this snippet, which is embedded dynamically by Ansible
# still belong to the author of the module, and may assign their own license
# to the complete work.
# 
# Copyright (c), Michael DeHaan <michael.dehaan@gmail.com>, 2012-2013
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification, 
# are permitted provided that the following conditions are met:
#
#    * Redistributions of source code must retain the above copyright 
#      notice, this list of conditions and the following disclaimer.
#    * Redistributions in binary form must reproduce the above copyright notice, 
#      this list of conditions and the following disclaimer in the documentation 
#      and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND 
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED 
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. 
# IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, 
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, 
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS 
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT 
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE 
# USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#

# == BEGIN DYNAMICALLY INSERTED CODE ==

MODULE_ARGS = "<<INCLUDE_ANSIBLE_MODULE_ARGS>>"
MODULE_COMPLEX_ARGS = "<<INCLUDE_ANSIBLE_MODULE_COMPLEX_ARGS>>"

BOOLEANS_TRUE = ['yes', 'on', '1', 'true', 1]
BOOLEANS_FALSE = ['no', 'off', '0', 'false', 0]
BOOLEANS = BOOLEANS_TRUE + BOOLEANS_FALSE

# ansible modules can be written in any language.  To simplify
# development of Python modules, the functions available here
# can be inserted in any module source automatically by including
# #<<INCLUDE_ANSIBLE_MODULE_COMMON>> on a blank line by itself inside
# of an ansible module. The source of this common code lives
# in lib/ansible/module_common.py

import locale
import os
import re
import pipes
import shlex
import subprocess
import sys
import syslog
import types
import time
import shutil
import stat
import tempfile
import traceback
import grp
import pwd
import platform
import errno
import tempfile

try:
    import json
except ImportError:
    try:
        import simplejson as json
    except ImportError:
        sys.stderr.write('Error: ansible requires a json module, none found!')
        sys.exit(1)
    except SyntaxError:
        sys.stderr.write('SyntaxError: probably due to json and python being for different versions')
        sys.exit(1)

HAVE_SELINUX=False
try:
    import selinux
    HAVE_SELINUX=True
except ImportError:
    pass

HAVE_HASHLIB=False
try:
    from hashlib import md5 as _md5
    HAVE_HASHLIB=True
except ImportError:
    from md5 import md5 as _md5

try:
    from hashlib import sha256 as _sha256
except ImportError:
    pass

try:
    from systemd import journal
    has_journal = True
except ImportError:
    import syslog
    has_journal = False

FILE_COMMON_ARGUMENTS=dict(
    src = dict(),
    mode = dict(),
    owner = dict(),
    group = dict(),
    seuser = dict(),
    serole = dict(),
    selevel = dict(),
    setype = dict(),
    # not taken by the file module, but other modules call file so it must ignore them.
    content = dict(),
    backup = dict(),
    force = dict(),
    remote_src = dict(), # used by assemble
    delimiter = dict(), # used by assemble
    directory_mode = dict(), # used by copy
)


def get_platform():
    ''' what's the platform?  example: Linux is a platform. '''
    return platform.system()

def get_distribution():
    ''' return the distribution name '''
    if platform.system() == 'Linux':
        try:
            distribution = platform.linux_distribution()[0].capitalize()
            if not distribution and os.path.isfile('/etc/system-release'):
                distribution = platform.linux_distribution(supported_dists=['system'])[0].capitalize()
                if 'Amazon' in distribution:
                    distribution = 'Amazon'
                else:
                    distribution = 'OtherLinux'
        except:
            # FIXME: MethodMissing, I assume?
            distribution = platform.dist()[0].capitalize()
    else:
        distribution = None
    return distribution

def load_platform_subclass(cls, *args, **kwargs):
    '''
    used by modules like User to have different implementations based on detected platform.  See User
    module for an example.
    '''

    this_platform = get_platform()
    distribution = get_distribution()
    subclass = None

    # get the most specific superclass for this platform
    if distribution is not None:
        for sc in cls.__subclasses__():
            if sc.distribution is not None and sc.distribution == distribution and sc.platform == this_platform:
                subclass = sc
    if subclass is None:
        for sc in cls.__subclasses__():
            if sc.platform == this_platform and sc.distribution is None:
                subclass = sc
    if subclass is None:
        subclass = cls

    return super(cls, subclass).__new__(subclass)


class AnsibleModule(object):

    def __init__(self, argument_spec, bypass_checks=False, no_log=False,
        check_invalid_arguments=True, mutually_exclusive=None, required_together=None,
        required_one_of=None, add_file_common_args=False, supports_check_mode=False):

        '''
        common code for quickly building an ansible module in Python
        (although you can write modules in anything that can return JSON)
        see library/* for examples
        '''

        self.argument_spec = argument_spec
        self.supports_check_mode = supports_check_mode
        self.check_mode = False
        self.no_log = no_log
        self.cleanup_files = []
        
        self.aliases = {}
        
        if add_file_common_args:
            for k, v in FILE_COMMON_ARGUMENTS.iteritems():
                if k not in self.argument_spec:
                    self.argument_spec[k] = v

        # check the locale as set by the current environment, and
        # reset to LANG=C if it's an invalid/unavailable locale
        self._check_locale()

        (self.params, self.args) = self._load_params()

        self._legal_inputs = ['CHECKMODE', 'NO_LOG']
        
        self.aliases = self._handle_aliases()

        if check_invalid_arguments:
            self._check_invalid_arguments()
        self._check_for_check_mode()
        self._check_for_no_log()

        # check exclusive early 
        if not bypass_checks:
            self._check_mutually_exclusive(mutually_exclusive)

        self._set_defaults(pre=True)

        if not bypass_checks:
            self._check_required_arguments()
            self._check_argument_values()
            self._check_argument_types()
            self._check_required_together(required_together)
            self._check_required_one_of(required_one_of)

        self._set_defaults(pre=False)
        if not self.no_log:
            self._log_invocation()

        # finally, make sure we're in a sane working dir
        self._set_cwd()

    def load_file_common_arguments(self, params):
        '''
        many modules deal with files, this encapsulates common
        options that the file module accepts such that it is directly
        available to all modules and they can share code.
        '''

        path = params.get('path', params.get('dest', None))
        if path is None:
            return {}
        else:
            path = os.path.expanduser(path)

        mode   = params.get('mode', None)
        owner  = params.get('owner', None)
        group  = params.get('group', None)

        # selinux related options
        seuser    = params.get('seuser', None)
        serole    = params.get('serole', None)
        setype    = params.get('setype', None)
        selevel   = params.get('selevel', None)
        secontext = [seuser, serole, setype]

        if self.selinux_mls_enabled():
            secontext.append(selevel)

        default_secontext = self.selinux_default_context(path)
        for i in range(len(default_secontext)):
            if i is not None and secontext[i] == '_default':
                secontext[i] = default_secontext[i]

        return dict(
            path=path, mode=mode, owner=owner, group=group,
            seuser=seuser, serole=serole, setype=setype,
            selevel=selevel, secontext=secontext,
        )


    # Detect whether using selinux that is MLS-aware.
    # While this means you can set the level/range with
    # selinux.lsetfilecon(), it may or may not mean that you
    # will get the selevel as part of the context returned
    # by selinux.lgetfilecon().

    def selinux_mls_enabled(self):
        if not HAVE_SELINUX:
            return False
        if selinux.is_selinux_mls_enabled() == 1:
            return True
        else:
            return False

    def selinux_enabled(self):
        if not HAVE_SELINUX:
            seenabled = self.get_bin_path('selinuxenabled')
            if seenabled is not None:
                (rc,out,err) = self.run_command(seenabled)
                if rc == 0:
                    self.fail_json(msg="Aborting, target uses selinux but python bindings (libselinux-python) aren't installed!")
            return False
        if selinux.is_selinux_enabled() == 1:
            return True
        else:
            return False

    # Determine whether we need a placeholder for selevel/mls
    def selinux_initial_context(self):
        context = [None, None, None]
        if self.selinux_mls_enabled():
            context.append(None)
        return context

    def _to_filesystem_str(self, path):
        '''Returns filesystem path as a str, if it wasn't already.

        Used in selinux interactions because it cannot accept unicode
        instances, and specifying complex args in a playbook leaves
        you with unicode instances.  This method currently assumes
        that your filesystem encoding is UTF-8.

        '''
        if isinstance(path, unicode):
            path = path.encode("utf-8")
        return path

    # If selinux fails to find a default, return an array of None
    def selinux_default_context(self, path, mode=0):
        context = self.selinux_initial_context()
        if not HAVE_SELINUX or not self.selinux_enabled():
            return context
        try:
            ret = selinux.matchpathcon(self._to_filesystem_str(path), mode)
        except OSError:
            return context
        if ret[0] == -1:
            return context
        # Limit split to 4 because the selevel, the last in the list,
        # may contain ':' characters
        context = ret[1].split(':', 3)
        return context

    def selinux_context(self, path):
        context = self.selinux_initial_context()
        if not HAVE_SELINUX or not self.selinux_enabled():
            return context
        try:
            ret = selinux.lgetfilecon_raw(self._to_filesystem_str(path))
        except OSError, e:
            if e.errno == errno.ENOENT:
                self.fail_json(path=path, msg='path %s does not exist' % path)
            else:
                self.fail_json(path=path, msg='failed to retrieve selinux context')
        if ret[0] == -1:
            return context
        # Limit split to 4 because the selevel, the last in the list,
        # may contain ':' characters
        context = ret[1].split(':', 3)
        return context

    def user_and_group(self, filename):
        filename = os.path.expanduser(filename)
        st = os.lstat(filename)
        uid = st.st_uid
        gid = st.st_gid
        return (uid, gid)

    def find_mount_point(self, path):
        path = os.path.abspath(os.path.expanduser(os.path.expandvars(path)))
        while not os.path.ismount(path):
            path = os.path.dirname(path)
        return path

    def is_nfs_path(self, path):
        """
        Returns a tuple containing (True, selinux_context) if the given path
        is on a NFS mount point, otherwise the return will be (False, None).
        """
        try:
            f = open('/proc/mounts', 'r')
            mount_data = f.readlines()
            f.close()
        except:
            return (False, None)
        path_mount_point = self.find_mount_point(path)
        for line in mount_data:
            (device, mount_point, fstype, options, rest) = line.split(' ', 4)
            if path_mount_point == mount_point and 'nfs' in fstype:
                nfs_context = self.selinux_context(path_mount_point)
                return (True, nfs_context)
        return (False, None)

    def set_default_selinux_context(self, path, changed):
        if not HAVE_SELINUX or not self.selinux_enabled():
            return changed
        context = self.selinux_default_context(path)
        return self.set_context_if_different(path, context, False)

    def set_context_if_different(self, path, context, changed):

        if not HAVE_SELINUX or not self.selinux_enabled():
            return changed
        cur_context = self.selinux_context(path)
        new_context = list(cur_context)
        # Iterate over the current context instead of the
        # argument context, which may have selevel.

        (is_nfs, nfs_context) = self.is_nfs_path(path)
        if is_nfs:
            new_context = nfs_context
        else:
            for i in range(len(cur_context)):
                if len(context) > i:
                    if context[i] is not None and context[i] != cur_context[i]:
                        new_context[i] = context[i]
                    if context[i] is None:
                        new_context[i] = cur_context[i]

        if cur_context != new_context:
            try:
                if self.check_mode:
                    return True
                rc = selinux.lsetfilecon(self._to_filesystem_str(path),
                                         str(':'.join(new_context)))
            except OSError:
                self.fail_json(path=path, msg='invalid selinux context', new_context=new_context, cur_context=cur_context, input_was=context)
            if rc != 0:
                self.fail_json(path=path, msg='set selinux context failed')
            changed = True
        return changed

    def set_owner_if_different(self, path, owner, changed):
        path = os.path.expanduser(path)
        if owner is None:
            return changed
        orig_uid, orig_gid = self.user_and_group(path)
        try:
            uid = int(owner)
        except ValueError:
            try:
                uid = pwd.getpwnam(owner).pw_uid
            except KeyError:
                self.fail_json(path=path, msg='chown failed: failed to look up user %s' % owner)
        if orig_uid != uid:
            if self.check_mode:
                return True
            try:
                os.lchown(path, uid, -1)
            except OSError:
                self.fail_json(path=path, msg='chown failed')
            changed = True
        return changed

    def set_group_if_different(self, path, group, changed):
        path = os.path.expanduser(path)
        if group is None:
            return changed
        orig_uid, orig_gid = self.user_and_group(path)
        try:
            gid = int(group)
        except ValueError:
            try:
                gid = grp.getgrnam(group).gr_gid
            except KeyError:
                self.fail_json(path=path, msg='chgrp failed: failed to look up group %s' % group)
        if orig_gid != gid:
            if self.check_mode:
                return True
            try:
                os.lchown(path, -1, gid)
            except OSError:
                self.fail_json(path=path, msg='chgrp failed')
            changed = True
        return changed

    def set_mode_if_different(self, path, mode, changed):
        path = os.path.expanduser(path)
        if mode is None:
            return changed
        try:
            # FIXME: support English modes
            if not isinstance(mode, int):
                mode = int(mode, 8)
        except Exception, e:
            self.fail_json(path=path, msg='mode needs to be something octalish', details=str(e))

        st = os.lstat(path)
        prev_mode = stat.S_IMODE(st[stat.ST_MODE])

        if prev_mode != mode:
            if self.check_mode:
                return True
            # FIXME: comparison against string above will cause this to be executed
            # every time
            try:
                if 'lchmod' in dir(os):
                    os.lchmod(path, mode)
                else:
                    os.chmod(path, mode)
            except OSError, e:
                if os.path.islink(path) and e.errno == errno.EPERM:  # Can't set mode on symbolic links
                    pass
                elif e.errno == errno.ENOENT: # Can't set mode on broken symbolic links
                    pass
                else:
                    raise e
            except Exception, e:
                self.fail_json(path=path, msg='chmod failed', details=str(e))

            st = os.lstat(path)
            new_mode = stat.S_IMODE(st[stat.ST_MODE])

            if new_mode != prev_mode:
                changed = True
        return changed

    def set_fs_attributes_if_different(self, file_args, changed):
        # set modes owners and context as needed
        changed = self.set_context_if_different(
            file_args['path'], file_args['secontext'], changed
        )
        changed = self.set_owner_if_different(
            file_args['path'], file_args['owner'], changed
        )
        changed = self.set_group_if_different(
            file_args['path'], file_args['group'], changed
        )
        changed = self.set_mode_if_different(
            file_args['path'], file_args['mode'], changed
        )
        return changed

    def set_directory_attributes_if_different(self, file_args, changed):
        return self.set_fs_attributes_if_different(file_args, changed)

    def set_file_attributes_if_different(self, file_args, changed):
        return self.set_fs_attributes_if_different(file_args, changed)

    def add_path_info(self, kwargs):
        '''
        for results that are files, supplement the info about the file
        in the return path with stats about the file path.
        '''

        path = kwargs.get('path', kwargs.get('dest', None))
        if path is None:
            return kwargs
        if os.path.exists(path):
            (uid, gid) = self.user_and_group(path)
            kwargs['uid'] = uid
            kwargs['gid'] = gid
            try:
                user = pwd.getpwuid(uid)[0]
            except KeyError:
                user = str(uid)
            try:
                group = grp.getgrgid(gid)[0]
            except KeyError:
                group = str(gid)
            kwargs['owner'] = user
            kwargs['group'] = group
            st = os.lstat(path)
            kwargs['mode']  = oct(stat.S_IMODE(st[stat.ST_MODE]))
            # secontext not yet supported
            if os.path.islink(path):
                kwargs['state'] = 'link'
            elif os.path.isdir(path):
                kwargs['state'] = 'directory'
            elif os.stat(path).st_nlink > 1:
                kwargs['state'] = 'hard'
            else:
                kwargs['state'] = 'file'
            if HAVE_SELINUX and self.selinux_enabled():
                kwargs['secontext'] = ':'.join(self.selinux_context(path))
            kwargs['size'] = st[stat.ST_SIZE]
        else:
            kwargs['state'] = 'absent'
        return kwargs

    def _check_locale(self):
        '''
        Uses the locale module to test the currently set locale
        (per the LANG and LC_CTYPE environment settings)
        '''
        try:
            # setting the locale to '' uses the default locale
            # as it would be returned by locale.getdefaultlocale()
            locale.setlocale(locale.LC_ALL, '')
        except locale.Error, e:
            # fallback to the 'C' locale, which may cause unicode
            # issues but is preferable to simply failing because
            # of an unknown locale
            locale.setlocale(locale.LC_ALL, 'C')
            os.environ['LANG']     = 'C'
            os.environ['LC_CTYPE'] = 'C'
        except Exception, e:
            self.fail_json(msg="An unknown error was encountered while attempting to validate the locale: %s" % e)

    def _handle_aliases(self):
        aliases_results = {} #alias:canon
        for (k,v) in self.argument_spec.iteritems():
            self._legal_inputs.append(k)
            aliases = v.get('aliases', None)
            default = v.get('default', None)
            required = v.get('required', False)
            if default is not None and required:
                # not alias specific but this is a good place to check this
                self.fail_json(msg="internal error: required and default are mutally exclusive for %s" % k)
            if aliases is None:
                continue
            if type(aliases) != list:
                self.fail_json(msg='internal error: aliases must be a list')
            for alias in aliases:
                self._legal_inputs.append(alias)
                aliases_results[alias] = k
                if alias in self.params:
                    self.params[k] = self.params[alias]
        
        return aliases_results

    def _check_for_check_mode(self):
        for (k,v) in self.params.iteritems():
            if k == 'CHECKMODE':
                if not self.supports_check_mode:
                    self.exit_json(skipped=True, msg="remote module does not support check mode")
                if self.supports_check_mode:
                    self.check_mode = True

    def _check_for_no_log(self):
        for (k,v) in self.params.iteritems():
            if k == 'NO_LOG':
                self.no_log = self.boolean(v)

    def _check_invalid_arguments(self):
        for (k,v) in self.params.iteritems():
            # these should be in legal inputs already
            #if k in ('CHECKMODE', 'NO_LOG'):
            #    continue
            if k not in self._legal_inputs:
                self.fail_json(msg="unsupported parameter for module: %s" % k)

    def _count_terms(self, check):
        count = 0
        for term in check:
            if term in self.params:
                count += 1
        return count

    def _check_mutually_exclusive(self, spec):
        if spec is None:
            return
        for check in spec:
            count = self._count_terms(check)
            if count > 1:
                self.fail_json(msg="parameters are mutually exclusive: %s" % check)

    def _check_required_one_of(self, spec):
        if spec is None:
            return
        for check in spec:
            count = self._count_terms(check)
            if count == 0:
                self.fail_json(msg="one of the following is required: %s" % ','.join(check))

    def _check_required_together(self, spec):
        if spec is None:
            return
        for check in spec:
            counts = [ self._count_terms([field]) for field in check ]
            non_zero = [ c for c in counts if c > 0 ]
            if len(non_zero) > 0:
                if 0 in counts:
                    self.fail_json(msg="parameters are required together: %s" % check)

    def _check_required_arguments(self):
        ''' ensure all required arguments are present '''
        missing = []
        for (k,v) in self.argument_spec.iteritems():
            required = v.get('required', False)
            if required and k not in self.params:
                missing.append(k)
        if len(missing) > 0:
            self.fail_json(msg="missing required arguments: %s" % ",".join(missing))

    def _check_argument_values(self):
        ''' ensure all arguments have the requested values, and there are no stray arguments '''
        for (k,v) in self.argument_spec.iteritems():
            choices = v.get('choices',None)
            if choices is None:
                continue
            if type(choices) == list:
                if k in self.params:
                    if self.params[k] not in choices:
                        choices_str=",".join([str(c) for c in choices])
                        msg="value of %s must be one of: %s, got: %s" % (k, choices_str, self.params[k])
                        self.fail_json(msg=msg)
            else:
                self.fail_json(msg="internal error: do not know how to interpret argument_spec")

    def _check_argument_types(self):
        ''' ensure all arguments have the requested type '''
        for (k, v) in self.argument_spec.iteritems():
            wanted = v.get('type', None)
            if wanted is None:
                continue
            if k not in self.params:
                continue

            value = self.params[k]
            is_invalid = False

            if wanted == 'str':
                if not isinstance(value, basestring):
                    self.params[k] = str(value)
            elif wanted == 'list':
                if not isinstance(value, list):
                    if isinstance(value, basestring):
                        self.params[k] = value.split(",")
                    elif isinstance(value, int) or isinstance(value, float):
                        self.params[k] = [ str(value) ]
                    else:
                        is_invalid = True
            elif wanted == 'dict':
                if not isinstance(value, dict):
                    if isinstance(value, basestring):
                        if value.startswith("{"):
                            try:
                                self.params[k] = json.loads(value)
                            except:
                                (result, exc) = self.safe_eval(value, dict(), include_exceptions=True)
                                if exc is not None:
                                    self.fail_json(msg="unable to evaluate dictionary for %s" % k)
                                self.params[k] = result
                        elif '=' in value:
                            self.params[k] = dict([x.split("=", 1) for x in value.split(",")])
                        else:
                            self.fail_json(msg="dictionary requested, could not parse JSON or key=value")
                    else:
                        is_invalid = True
            elif wanted == 'bool':
                if not isinstance(value, bool):
                    if isinstance(value, basestring):
                        self.params[k] = self.boolean(value)
                    else:
                        is_invalid = True
            elif wanted == 'int':
                if not isinstance(value, int):
                    if isinstance(value, basestring):
                        self.params[k] = int(value)
                    else:
                        is_invalid = True
            elif wanted == 'float':
                if not isinstance(value, float):
                    if isinstance(value, basestring):
                        self.params[k] = float(value)
                    else:
                        is_invalid = True
            else:
                self.fail_json(msg="implementation error: unknown type %s requested for %s" % (wanted, k))

            if is_invalid:
                self.fail_json(msg="argument %s is of invalid type: %s, required: %s" % (k, type(value), wanted))

    def _set_defaults(self, pre=True):
        for (k,v) in self.argument_spec.iteritems():
            default = v.get('default', None)
            if pre == True:
                # this prevents setting defaults on required items
                if default is not None and k not in self.params:
                    self.params[k] = default
            else:
                # make sure things without a default still get set None
                if k not in self.params:
                    self.params[k] = default

    def _load_params(self):
        ''' read the input and return a dictionary and the arguments string '''
        args = MODULE_ARGS
        items   = shlex.split(args)
        params = {}
        for x in items:
            try:
                (k, v) = x.split("=",1)
            except Exception, e:
                self.fail_json(msg="this module requires key=value arguments (%s)" % (items))
            params[k] = v
        params2 = json.loads(MODULE_COMPLEX_ARGS)
        params2.update(params)
        return (params2, args)

    def _log_invocation(self):
        ''' log that ansible ran the module '''
        # TODO: generalize a separate log function and make log_invocation use it
        # Sanitize possible password argument when logging.
        log_args = dict()
        passwd_keys = ['password', 'login_password']

        filter_re = [
            # filter out things like user:pass@foo/whatever
            # and http://username:pass@wherever/foo
            re.compile('^(?P<before>.*:)(?P<password>.*)(?P<after>\@.*)$'), 
        ]

        for param in self.params:
            canon  = self.aliases.get(param, param)
            arg_opts = self.argument_spec.get(canon, {})
            no_log = arg_opts.get('no_log', False)
                
            if no_log:
                log_args[param] = 'NOT_LOGGING_PARAMETER'
            elif param in passwd_keys:
                log_args[param] = 'NOT_LOGGING_PASSWORD'
            else:
                found = False
                for filter in filter_re:
                    if isinstance(self.params[param], unicode):
                        m = filter.match(self.params[param])
                    else:
                        m = filter.match(str(self.params[param]))
                    if m:
                        d = m.groupdict()
                        log_args[param] = d['before'] + "********" + d['after']
                        found = True
                        break
                if not found:
                    log_args[param] = self.params[param]

        module = 'ansible-%s' % os.path.basename(__file__)
        msg = ''
        for arg in log_args:
            if isinstance(log_args[arg], basestring):
                msg = msg + arg + '=' + log_args[arg].decode('utf-8') + ' '
            else:
                msg = msg + arg + '=' + str(log_args[arg]) + ' '
        if msg:
            msg = 'Invoked with %s' % msg
        else:
            msg = 'Invoked'

        # 6655 - allow for accented characters
        try:
            msg = msg.encode('utf8')
        except UnicodeDecodeError, e:
            pass

        if (has_journal):
            journal_args = ["MESSAGE=%s %s" % (module, msg)]
            journal_args.append("MODULE=%s" % os.path.basename(__file__))
            for arg in log_args:
                journal_args.append(arg.upper() + "=" + str(log_args[arg]))
            try:
                journal.sendv(*journal_args)
            except IOError, e:
                # fall back to syslog since logging to journal failed
                syslog.openlog(str(module), 0, syslog.LOG_USER)
                syslog.syslog(syslog.LOG_NOTICE, msg) #1
        else:
            syslog.openlog(str(module), 0, syslog.LOG_USER)
            syslog.syslog(syslog.LOG_NOTICE, msg) #2

    def _set_cwd(self):
        try:
            cwd = os.getcwd()
            if not os.access(cwd, os.F_OK|os.R_OK):
                raise
            return cwd
        except:
            # we don't have access to the cwd, probably because of sudo. 
            # Try and move to a neutral location to prevent errors
            for cwd in [os.path.expandvars('$HOME'), tempfile.gettempdir()]:
                try:
                    if os.access(cwd, os.F_OK|os.R_OK):
                        os.chdir(cwd)
                        return cwd
                except:
                    pass
        # we won't error here, as it may *not* be a problem, 
        # and we don't want to break modules unnecessarily
        return None    

    def get_bin_path(self, arg, required=False, opt_dirs=[]):
        '''
        find system executable in PATH.
        Optional arguments:
           - required:  if executable is not found and required is true, fail_json
           - opt_dirs:  optional list of directories to search in addition to PATH
        if found return full path; otherwise return None
        '''
        sbin_paths = ['/sbin', '/usr/sbin', '/usr/local/sbin']
        paths = []
        for d in opt_dirs:
            if d is not None and os.path.exists(d):
                paths.append(d)
        paths += os.environ.get('PATH', '').split(os.pathsep)
        bin_path = None
        # mangle PATH to include /sbin dirs
        for p in sbin_paths:
            if p not in paths and os.path.exists(p):
                paths.append(p)
        for d in paths:
            path = os.path.join(d, arg)
            if os.path.exists(path) and self.is_executable(path):
                bin_path = path
                break
        if required and bin_path is None:
            self.fail_json(msg='Failed to find required executable %s' % arg)
        return bin_path

    def boolean(self, arg):
        ''' return a bool for the arg '''
        if arg is None or type(arg) == bool:
            return arg
        if type(arg) in types.StringTypes:
            arg = arg.lower()
        if arg in BOOLEANS_TRUE:
            return True
        elif arg in BOOLEANS_FALSE:
            return False
        else:
            self.fail_json(msg='Boolean %s not in either boolean list' % arg)

    def jsonify(self, data):
        for encoding in ("utf-8", "latin-1", "unicode_escape"):
            try:
                return json.dumps(data, encoding=encoding)
            # Old systems using simplejson module does not support encoding keyword.
            except TypeError, e:
                return json.dumps(data)
            except UnicodeDecodeError, e:
                continue
        self.fail_json(msg='Invalid unicode encoding encountered')

    def from_json(self, data):
        return json.loads(data)

    def add_cleanup_file(self, path):
        if path not in self.cleanup_files:
            self.cleanup_files.append(path)

    def do_cleanup_files(self):
        for path in self.cleanup_files:
            self.cleanup(path)

    def exit_json(self, **kwargs):
        ''' return from the module, without error '''
        self.add_path_info(kwargs)
        if not 'changed' in kwargs:
            kwargs['changed'] = False
        self.do_cleanup_files()
        print self.jsonify(kwargs)
        sys.exit(0)

    def fail_json(self, **kwargs):
        ''' return from the module, with an error message '''
        self.add_path_info(kwargs)
        assert 'msg' in kwargs, "implementation error -- msg to explain the error is required"
        kwargs['failed'] = True
        self.do_cleanup_files()
        print self.jsonify(kwargs)
        sys.exit(1)

    def is_executable(self, path):
        '''is the given path executable?'''
        return (stat.S_IXUSR & os.stat(path)[stat.ST_MODE]
                or stat.S_IXGRP & os.stat(path)[stat.ST_MODE]
                or stat.S_IXOTH & os.stat(path)[stat.ST_MODE])

    def digest_from_file(self, filename, digest_method):
        ''' Return hex digest of local file for a given digest_method, or None if file is not present. '''
        if not os.path.exists(filename):
            return None
        if os.path.isdir(filename):
            self.fail_json(msg="attempted to take checksum of directory: %s" % filename)
        digest = digest_method
        blocksize = 64 * 1024
        infile = open(filename, 'rb')
        block = infile.read(blocksize)
        while block:
            digest.update(block)
            block = infile.read(blocksize)
        infile.close()
        return digest.hexdigest()

    def md5(self, filename):
        ''' Return MD5 hex digest of local file using digest_from_file(). '''
        return self.digest_from_file(filename, _md5())

    def sha256(self, filename):
        ''' Return SHA-256 hex digest of local file using digest_from_file(). '''
        if not HAVE_HASHLIB:
            self.fail_json(msg="SHA-256 checksums require hashlib, which is available in Python 2.5 and higher")
        return self.digest_from_file(filename, _sha256())

    def backup_local(self, fn):
        '''make a date-marked backup of the specified file, return True or False on success or failure'''
        # backups named basename-YYYY-MM-DD@HH:MM~
        ext = time.strftime("%Y-%m-%d@%H:%M~", time.localtime(time.time()))
        backupdest = '%s.%s' % (fn, ext)

        try:
            shutil.copy2(fn, backupdest)
        except shutil.Error, e:
            self.fail_json(msg='Could not make backup of %s to %s: %s' % (fn, backupdest, e))
        return backupdest

    def cleanup(self, tmpfile):
        if os.path.exists(tmpfile):
            try:
                os.unlink(tmpfile)
            except OSError, e:
                sys.stderr.write("could not cleanup %s: %s" % (tmpfile, e))

    def atomic_move(self, src, dest):
        '''atomically move src to dest, copying attributes from dest, returns true on success
        it uses os.rename to ensure this as it is an atomic operation, rest of the function is
        to work around limitations, corner cases and ensure selinux context is saved if possible'''
        context = None
        dest_stat = None
        if os.path.exists(dest):
            try:
                dest_stat = os.stat(dest)
                os.chmod(src, dest_stat.st_mode & 07777)
                os.chown(src, dest_stat.st_uid, dest_stat.st_gid)
            except OSError, e:
                if e.errno != errno.EPERM:
                    raise
            if self.selinux_enabled():
                context = self.selinux_context(dest)
        else:
            if self.selinux_enabled():
                context = self.selinux_default_context(dest)

        creating = not os.path.exists(dest)

        try:
            # Optimistically try a rename, solves some corner cases and can avoid useless work, throws exception if not atomic.
            os.rename(src, dest)
        except (IOError,OSError), e:
            # only try workarounds for errno 18 (cross device), 1 (not permited) and 13 (permission denied)
            if e.errno != errno.EPERM and e.errno != errno.EXDEV and e.errno != errno.EACCES:
                self.fail_json(msg='Could not replace file: %s to %s: %s' % (src, dest, e))

            dest_dir = os.path.dirname(dest)
            dest_file = os.path.basename(dest)
            tmp_dest = tempfile.NamedTemporaryFile(
                prefix=".ansible_tmp", dir=dest_dir, suffix=dest_file)

            try: # leaves tmp file behind when sudo and  not root
                if os.getenv("SUDO_USER") and os.getuid() != 0:
                    # cleanup will happen by 'rm' of tempdir
                    # copy2 will preserve some metadata
                    shutil.copy2(src, tmp_dest.name)
                else:
                    shutil.move(src, tmp_dest.name)
                if self.selinux_enabled():
                    self.set_context_if_different(
                        tmp_dest.name, context, False)
                tmp_stat = os.stat(tmp_dest.name)
                if dest_stat and (tmp_stat.st_uid != dest_stat.st_uid or tmp_stat.st_gid != dest_stat.st_gid):
                    os.chown(tmp_dest.name, dest_stat.st_uid, dest_stat.st_gid)
                os.rename(tmp_dest.name, dest)
            except (shutil.Error, OSError, IOError), e:
                self.cleanup(tmp_dest.name)
                self.fail_json(msg='Could not replace file: %s to %s: %s' % (src, dest, e))

        if creating:
            # make sure the file has the correct permissions
            # based on the current value of umask
            umask = os.umask(0)
            os.umask(umask)
            os.chmod(dest, 0666 ^ umask)
            if os.getenv("SUDO_USER"):
                os.chown(dest, os.getuid(), os.getgid())

        if self.selinux_enabled():
            # rename might not preserve context
            self.set_context_if_different(dest, context, False)

    def run_command(self, args, check_rc=False, close_fds=False, executable=None, data=None, binary_data=False, path_prefix=None, cwd=None, use_unsafe_shell=False):
        '''
        Execute a command, returns rc, stdout, and stderr.
        args is the command to run
        If args is a list, the command will be run with shell=False.
        If args is a string and use_unsafe_shell=False it will split args to a list and run with shell=False
        If args is a string and use_unsafe_shell=True it run with shell=True.
        Other arguments:
        - check_rc (boolean)  Whether to call fail_json in case of
                              non zero RC.  Default is False.
        - close_fds (boolean) See documentation for subprocess.Popen().
                              Default is False.
        - executable (string) See documentation for subprocess.Popen().
                              Default is None.
        '''

        shell = False
        if isinstance(args, list):
            if use_unsafe_shell:
                args = " ".join([pipes.quote(x) for x in args])
                shell = True
        elif isinstance(args, basestring) and use_unsafe_shell:
            shell = True
        elif isinstance(args, basestring):
            args = shlex.split(args.encode('utf-8'))
        else:
            msg = "Argument 'args' to run_command must be list or string"
            self.fail_json(rc=257, cmd=args, msg=msg)

        # expand things like $HOME and ~
        if not shell:
            args = [ os.path.expandvars(os.path.expanduser(x)) for x in args ]

        rc = 0
        msg = None
        st_in = None

        # Set a temporart env path if a prefix is passed
        env=os.environ
        if path_prefix:
            env['PATH']="%s:%s" % (path_prefix, env['PATH'])

        # create a printable version of the command for use
        # in reporting later, which strips out things like
        # passwords from the args list
        if isinstance(args, list):
            clean_args = " ".join(pipes.quote(arg) for arg in args)
        else:
            clean_args = args

        # all clean strings should return two match groups, 
        # where the first is the CLI argument and the second 
        # is the password/key/phrase that will be hidden
        clean_re_strings = [
            # this removes things like --password, --pass, --pass-wd, etc.
            # optionally followed by an '=' or a space. The password can 
            # be quoted or not too, though it does not care about quotes
            # that are not balanced
            # source: http://blog.stevenlevithan.com/archives/match-quoted-string
            r'([-]{0,2}pass[-]?(?:word|wd)?[=\s]?)((?:["\'])?(?:[^\s])*(?:\1)?)',
            # TODO: add more regex checks here
        ]
        for re_str in clean_re_strings:
            r = re.compile(re_str)
            clean_args = r.sub(r'\1********', clean_args)

        if data:
            st_in = subprocess.PIPE

        kwargs = dict(
            executable=executable,
            shell=shell,
            close_fds=close_fds,
            stdin= st_in,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE 
        )

        if path_prefix:
            kwargs['env'] = env
        if cwd and os.path.isdir(cwd):
            kwargs['cwd'] = cwd

        # store the pwd
        prev_dir = os.getcwd()

        # make sure we're in the right working directory
        if cwd and os.path.isdir(cwd):
            try:
                os.chdir(cwd)
            except (OSError, IOError), e:
                self.fail_json(rc=e.errno, msg="Could not open %s , %s" % (cwd, str(e)))

        try:
            cmd = subprocess.Popen(args, **kwargs)

            if data:
                if not binary_data:
                    data += '\n'
            out, err = cmd.communicate(input=data)
            rc = cmd.returncode
        except (OSError, IOError), e:
            self.fail_json(rc=e.errno, msg=str(e), cmd=clean_args)
        except:
            self.fail_json(rc=257, msg=traceback.format_exc(), cmd=clean_args)

        if rc != 0 and check_rc:
            msg = err.rstrip()
            self.fail_json(cmd=clean_args, rc=rc, stdout=out, stderr=err, msg=msg)

        # reset the pwd
        os.chdir(prev_dir)

        return (rc, out, err)

    def append_to_file(self, filename, str):
        filename = os.path.expandvars(os.path.expanduser(filename))
        fh = open(filename, 'a')
        fh.write(str)
        fh.close()

    def pretty_bytes(self,size):
        ranges = (
                (1<<70L, 'ZB'),
                (1<<60L, 'EB'),
                (1<<50L, 'PB'),
                (1<<40L, 'TB'),
                (1<<30L, 'GB'),
                (1<<20L, 'MB'),
                (1<<10L, 'KB'),
                (1, 'Bytes')
            )
        for limit, suffix in ranges:
            if size >= limit:
                break
        return '%.2f %s' % (float(size)/ limit, suffix)

def get_module_path():
    return os.path.dirname(os.path.realpath(__file__))

########NEW FILE########
__FILENAME__ = ec2
# This code is part of Ansible, but is an independent component.
# This particular file snippet, and this file snippet only, is BSD licensed.
# Modules you write using this snippet, which is embedded dynamically by Ansible
# still belong to the author of the module, and may assign their own license
# to the complete work.
#
# Copyright (c), Michael DeHaan <michael.dehaan@gmail.com>, 2012-2013
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#
#    * Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#    * Redistributions in binary form must reproduce the above copyright notice,
#      this list of conditions and the following disclaimer in the documentation
#      and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
# IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE
# USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

try:
    from distutils.version import LooseVersion
    HAS_LOOSE_VERSION = True
except:
    HAS_LOOSE_VERSION = False

AWS_REGIONS = ['ap-northeast-1',
               'ap-southeast-1',
               'ap-southeast-2',
               'eu-west-1',
               'sa-east-1',
               'us-east-1',
               'us-west-1',
               'us-west-2']


def aws_common_argument_spec():
    return dict(
        ec2_url=dict(),
        aws_secret_key=dict(aliases=['ec2_secret_key', 'secret_key'], no_log=True),
        aws_access_key=dict(aliases=['ec2_access_key', 'access_key']),
        validate_certs=dict(default=True, type='bool'),
        security_token=dict(no_log=True),
        profile=dict(),
    )
    return spec


def ec2_argument_spec():
    spec = aws_common_argument_spec()
    spec.update(
        dict(
            region=dict(aliases=['aws_region', 'ec2_region'], choices=AWS_REGIONS),
        )
    )
    return spec


def boto_supports_profile_name():
    return hasattr(boto.ec2.EC2Connection, 'profile_name')


def get_aws_connection_info(module):

    # Check module args for credentials, then check environment vars
    # access_key

    ec2_url = module.params.get('ec2_url')
    access_key = module.params.get('aws_access_key')
    secret_key = module.params.get('aws_secret_key')
    security_token = module.params.get('security_token')
    region = module.params.get('region')
    profile_name = module.params.get('profile')
    validate_certs = module.params.get('validate_certs')

    if not ec2_url:
        if 'EC2_URL' in os.environ:
            ec2_url = os.environ['EC2_URL']
        elif 'AWS_URL' in os.environ:
            ec2_url = os.environ['AWS_URL']

    if not access_key:
        if 'EC2_ACCESS_KEY' in os.environ:
            access_key = os.environ['EC2_ACCESS_KEY']
        elif 'AWS_ACCESS_KEY_ID' in os.environ:
            access_key = os.environ['AWS_ACCESS_KEY_ID']
        elif 'AWS_ACCESS_KEY' in os.environ:
            access_key = os.environ['AWS_ACCESS_KEY']
        else:
            # in case access_key came in as empty string
            access_key = None

    if not secret_key:
        if 'EC2_SECRET_KEY' in os.environ:
            secret_key = os.environ['EC2_SECRET_KEY']
        elif 'AWS_SECRET_ACCESS_KEY' in os.environ:
            secret_key = os.environ['AWS_SECRET_ACCESS_KEY']
        elif 'AWS_SECRET_KEY' in os.environ:
            secret_key = os.environ['AWS_SECRET_KEY']
        else:
            # in case secret_key came in as empty string
            secret_key = None

    if not region:
        if 'EC2_REGION' in os.environ:
            region = os.environ['EC2_REGION']
        elif 'AWS_REGION' in os.environ:
            region = os.environ['AWS_REGION']
        else:
            # boto.config.get returns None if config not found
            region = boto.config.get('Boto', 'aws_region')
            if not region:
                region = boto.config.get('Boto', 'ec2_region')

    if not security_token:
        if 'AWS_SECURITY_TOKEN' in os.environ:
            security_token = os.environ['AWS_SECURITY_TOKEN']
        else:
            # in case security_token came in as empty string
            security_token = None

    boto_params = dict(aws_access_key_id=access_key,
                       aws_secret_access_key=secret_key,
                       security_token=security_token)

    # profile_name only works as a key in boto >= 2.24
    # so only set profile_name if passed as an argument
    if profile_name:
        if not boto_supports_profile_name():
            module.fail_json("boto does not support profile_name before 2.24")
        boto_params['profile_name'] = profile_name

    if validate_certs and HAS_LOOSE_VERSION and LooseVersion(boto.Version) >= LooseVersion("2.6.0"):
        boto_params['validate_certs'] = validate_certs

    return region, ec2_url, boto_params


def get_ec2_creds(module):
    ''' for compatibility mode with old modules that don't/can't yet
        use ec2_connect method '''
    region, ec2_url, boto_params = get_aws_connection_info(module)
    return ec2_url, boto_params['aws_access_key_id'], boto_params['aws_secret_access_key'], region


def boto_fix_security_token_in_profile(conn, profile_name):
    ''' monkey patch for boto issue boto/boto#2100 '''
    profile = 'profile ' + profile_name
    if boto.config.has_option(profile, 'aws_security_token'):
        conn.provider.set_security_token(boto.config.get(profile, 'aws_security_token'))
    return conn


def connect_to_aws(aws_module, region, **params):
    conn = aws_module.connect_to_region(region, **params)
    if params.get('profile_name'):
        conn = boto_fix_security_token_in_profile(conn, params['profile_name'])
    return conn


def ec2_connect(module):

    """ Return an ec2 connection"""

    region, ec2_url, boto_params = get_aws_connection_info(module)

    # If we have a region specified, connect to its endpoint.
    if region:
        try:
            ec2 = connect_to_aws(boto.ec2, region, **boto_params)
        except boto.exception.NoAuthHandlerFound, e:
            module.fail_json(msg=str(e))
    # Otherwise, no region so we fallback to the old connection method
    elif ec2_url:
        try:
            ec2 = boto.connect_ec2_endpoint(ec2_url, **boto_params)
        except boto.exception.NoAuthHandlerFound, e:
            module.fail_json(msg=str(e))
    else:
        module.fail_json(msg="Either region or ec2_url must be specified")

    return ec2

########NEW FILE########
__FILENAME__ = facts
# (c) 2012, Michael DeHaan <michael.dehaan@gmail.com>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

import os
import array
import errno
import fcntl
import fnmatch
import glob
import platform
import re
import signal
import socket
import struct
import datetime
import getpass
import ConfigParser
import StringIO

try:
    import selinux
    HAVE_SELINUX=True
except ImportError:
    HAVE_SELINUX=False

try:
    import json
except ImportError:
    import simplejson as json

# --------------------------------------------------------------
# timeout function to make sure some fact gathering 
# steps do not exceed a time limit

class TimeoutError(Exception):
    pass

def timeout(seconds=10, error_message="Timer expired"):
    def decorator(func):
        def _handle_timeout(signum, frame):
            raise TimeoutError(error_message)

        def wrapper(*args, **kwargs):
            signal.signal(signal.SIGALRM, _handle_timeout)
            signal.alarm(seconds)
            try:
                result = func(*args, **kwargs)
            finally:
                signal.alarm(0)
            return result

        return wrapper

    return decorator

# --------------------------------------------------------------

class Facts(object):
    """
    This class should only attempt to populate those facts that
    are mostly generic to all systems.  This includes platform facts,
    service facts (eg. ssh keys or selinux), and distribution facts.
    Anything that requires extensive code or may have more than one
    possible implementation to establish facts for a given topic should
    subclass Facts.
    """

    _I386RE = re.compile(r'i[3456]86')
    # For the most part, we assume that platform.dist() will tell the truth.
    # This is the fallback to handle unknowns or exceptions
    OSDIST_DICT = { '/etc/redhat-release': 'RedHat',
                    '/etc/vmware-release': 'VMwareESX',
                    '/etc/openwrt_release': 'OpenWrt',
                    '/etc/system-release': 'OtherLinux',
                    '/etc/alpine-release': 'Alpine',
                    '/etc/release': 'Solaris',
                    '/etc/arch-release': 'Archlinux',
                    '/etc/SuSE-release': 'SuSE',
                    '/etc/gentoo-release': 'Gentoo',
                    '/etc/os-release': 'Debian' }
    SELINUX_MODE_DICT = { 1: 'enforcing', 0: 'permissive', -1: 'disabled' }

    # A list of dicts.  If there is a platform with more than one
    # package manager, put the preferred one last.  If there is an
    # ansible module, use that as the value for the 'name' key.
    PKG_MGRS = [ { 'path' : '/usr/bin/yum',         'name' : 'yum' },
                 { 'path' : '/usr/bin/apt-get',     'name' : 'apt' },
                 { 'path' : '/usr/bin/zypper',      'name' : 'zypper' },
                 { 'path' : '/usr/sbin/urpmi',      'name' : 'urpmi' },
                 { 'path' : '/usr/bin/pacman',      'name' : 'pacman' },
                 { 'path' : '/bin/opkg',            'name' : 'opkg' },
                 { 'path' : '/opt/local/bin/pkgin', 'name' : 'pkgin' },
                 { 'path' : '/opt/local/bin/port',  'name' : 'macports' },
                 { 'path' : '/sbin/apk',            'name' : 'apk' },
                 { 'path' : '/usr/sbin/pkg',        'name' : 'pkgng' },
                 { 'path' : '/usr/sbin/swlist',     'name' : 'SD-UX' },
                 { 'path' : '/usr/bin/emerge',      'name' : 'portage' },
                 { 'path' : '/usr/sbin/pkgadd',     'name' : 'svr4pkg' },
                 { 'path' : '/usr/bin/pkg',         'name' : 'pkg' },
    ]

    def __init__(self):
        self.facts = {}
        self.get_platform_facts()
        self.get_distribution_facts()
        self.get_cmdline()
        self.get_public_ssh_host_keys()
        self.get_selinux_facts()
        self.get_pkg_mgr_facts()
        self.get_lsb_facts()
        self.get_date_time_facts()
        self.get_user_facts()
        self.get_local_facts()
        self.get_env_facts()

    def populate(self):
        return self.facts

    # Platform
    # platform.system() can be Linux, Darwin, Java, or Windows
    def get_platform_facts(self):
        self.facts['system'] = platform.system()
        self.facts['kernel'] = platform.release()
        self.facts['machine'] = platform.machine()
        self.facts['python_version'] = platform.python_version()
        self.facts['fqdn'] = socket.getfqdn()
        self.facts['hostname'] = platform.node().split('.')[0]
        self.facts['nodename'] = platform.node()
        self.facts['domain'] = '.'.join(self.facts['fqdn'].split('.')[1:])
        arch_bits = platform.architecture()[0]
        self.facts['userspace_bits'] = arch_bits.replace('bit', '')
        if self.facts['machine'] == 'x86_64':
            self.facts['architecture'] = self.facts['machine']
            if self.facts['userspace_bits'] == '64':
                self.facts['userspace_architecture'] = 'x86_64'
            elif self.facts['userspace_bits'] == '32':
                self.facts['userspace_architecture'] = 'i386'
        elif Facts._I386RE.search(self.facts['machine']):
            self.facts['architecture'] = 'i386'
            if self.facts['userspace_bits'] == '64':
                self.facts['userspace_architecture'] = 'x86_64'
            elif self.facts['userspace_bits'] == '32':
                self.facts['userspace_architecture'] = 'i386'
        else:
            self.facts['architecture'] = self.facts['machine']
        if self.facts['system'] == 'Linux':
            self.get_distribution_facts()
        elif self.facts['system'] == 'AIX':
            rc, out, err = module.run_command("/usr/sbin/bootinfo -p")
            data = out.split('\n')
            self.facts['architecture'] = data[0]


    def get_local_facts(self):

        fact_path = module.params.get('fact_path', None)
        if not fact_path or not os.path.exists(fact_path):
            return

        local = {}
        for fn in sorted(glob.glob(fact_path + '/*.fact')):
            # where it will sit under local facts
            fact_base = os.path.basename(fn).replace('.fact','')
            if os.access(fn, os.X_OK):
                # run it
                # try to read it as json first
                # if that fails read it with ConfigParser
                # if that fails, skip it
                rc, out, err = module.run_command(fn)
            else:
                out = open(fn).read()

            # load raw json
            fact = 'loading %s' % fact_base
            try:
                fact = json.loads(out)
            except ValueError, e:
                # load raw ini
                cp = ConfigParser.ConfigParser()
                try:
                    cp.readfp(StringIO.StringIO(out))
                except ConfigParser.Error, e:
                    fact="error loading fact - please check content"
                else:
                    fact = {}
                    #print cp.sections()
                    for sect in cp.sections():
                        if sect not in fact:
                            fact[sect] = {}
                        for opt in cp.options(sect):
                            val = cp.get(sect, opt)
                            fact[sect][opt]=val

            local[fact_base] = fact
        if not local:
            return
        self.facts['local'] = local

    # platform.dist() is deprecated in 2.6
    # in 2.6 and newer, you should use platform.linux_distribution()
    def get_distribution_facts(self):

        # A list with OS Family members
        OS_FAMILY = dict(
            RedHat = 'RedHat', Fedora = 'RedHat', CentOS = 'RedHat', Scientific = 'RedHat',
            SLC = 'RedHat', Ascendos = 'RedHat', CloudLinux = 'RedHat', PSBM = 'RedHat',
            OracleLinux = 'RedHat', OVS = 'RedHat', OEL = 'RedHat', Amazon = 'RedHat',
            XenServer = 'RedHat', Ubuntu = 'Debian', Debian = 'Debian', SLES = 'Suse',
            SLED = 'Suse', OpenSuSE = 'Suse', SuSE = 'Suse', Gentoo = 'Gentoo', Funtoo = 'Gentoo',
            Archlinux = 'Archlinux', Mandriva = 'Mandrake', Mandrake = 'Mandrake',
            Solaris = 'Solaris', Nexenta = 'Solaris', OmniOS = 'Solaris', OpenIndiana = 'Solaris',
            SmartOS = 'Solaris', AIX = 'AIX', Alpine = 'Alpine', MacOSX = 'Darwin',
            FreeBSD = 'FreeBSD', HPUX = 'HP-UX'
        )

        if self.facts['system'] == 'AIX':
            self.facts['distribution'] = 'AIX'
            rc, out, err = module.run_command("/usr/bin/oslevel")
            data = out.split('.')
            self.facts['distribution_version'] = data[0]
            self.facts['distribution_release'] = data[1]
        elif self.facts['system'] == 'HP-UX':
            self.facts['distribution'] = 'HP-UX'
            rc, out, err = module.run_command("/usr/sbin/swlist |egrep 'HPUX.*OE.*[AB].[0-9]+\.[0-9]+'", use_unsafe_shell=True)
            data = re.search('HPUX.*OE.*([AB].[0-9]+\.[0-9]+)\.([0-9]+).*', out)
            if data:
                self.facts['distribution_version'] = data.groups()[0]
                self.facts['distribution_release'] = data.groups()[1]
        elif self.facts['system'] == 'Darwin':
            self.facts['distribution'] = 'MacOSX'
            rc, out, err = module.run_command("/usr/bin/sw_vers -productVersion")
            data = out.split()[-1]
            self.facts['distribution_version'] = data
        elif self.facts['system'] == 'FreeBSD':
            self.facts['distribution'] = 'FreeBSD'
            self.facts['distribution_release'] = platform.release()
            self.facts['distribution_version'] = platform.version()
        elif self.facts['system'] == 'OpenBSD':
            self.facts['distribution'] = 'OpenBSD'
            self.facts['distribution_release'] = platform.release()
            rc, out, err = module.run_command("/sbin/sysctl -n kern.version")
            match = re.match('OpenBSD\s[0-9]+.[0-9]+-(\S+)\s.*', out)
            if match:
                self.facts['distribution_version'] = match.groups()[0]
            else:
                self.facts['distribution_version'] = 'release'
        else:
            dist = platform.dist()
            self.facts['distribution'] = dist[0].capitalize() or 'NA'
            self.facts['distribution_version'] = dist[1] or 'NA'
            self.facts['distribution_major_version'] = dist[1].split('.')[0] or 'NA'
            self.facts['distribution_release'] = dist[2] or 'NA'
            # Try to handle the exceptions now ...
            for (path, name) in Facts.OSDIST_DICT.items():
                if os.path.exists(path):
                    if self.facts['distribution'] == 'Fedora':
                        pass
                    elif name == 'RedHat':
                        data = get_file_content(path)
                        if 'Red Hat' in data:
                            self.facts['distribution'] = name
                        else:
                            self.facts['distribution'] = data.split()[0]
                    elif name == 'OtherLinux':
                        data = get_file_content(path)
                        if 'Amazon' in data:
                            self.facts['distribution'] = 'Amazon'
                            self.facts['distribution_version'] = data.split()[-1]
                    elif name == 'OpenWrt':
                        data = get_file_content(path)
                        if 'OpenWrt' in data:
                            self.facts['distribution'] = name
                        version = re.search('DISTRIB_RELEASE="(.*)"', data)
                        if version:
                            self.facts['distribution_version'] = version.groups()[0]
                        release = re.search('DISTRIB_CODENAME="(.*)"', data)
                        if release:
                            self.facts['distribution_release'] = release.groups()[0]
                    elif name == 'Alpine':
                        data = get_file_content(path)
                        self.facts['distribution'] = 'Alpine'
                        self.facts['distribution_version'] = data
                    elif name == 'Solaris':
                        data = get_file_content(path).split('\n')[0]
                        ora_prefix = ''
                        if 'Oracle Solaris' in data:
                            data = data.replace('Oracle ','')
                            ora_prefix = 'Oracle '
                        self.facts['distribution'] = data.split()[0]
                        self.facts['distribution_version'] = data.split()[1]
                        self.facts['distribution_release'] = ora_prefix + data
                    elif name == 'SuSE':
                        data = get_file_content(path).splitlines()
                        for line in data:
                            if '=' in line:
                            	self.facts['distribution_release'] = line.split('=')[1].strip()
                    elif name == 'Debian':
                        data = get_file_content(path).split('\n')[0]
                        release = re.search("PRETTY_NAME.+ \(?([^ ]+?)\)?\"", data)
                        if release:
                            self.facts['distribution_release'] = release.groups()[0]
                    else:
                        self.facts['distribution'] = name

        self.facts['os_family'] = self.facts['distribution']
        if self.facts['distribution'] in OS_FAMILY:
            self.facts['os_family'] = OS_FAMILY[self.facts['distribution']]

    def get_cmdline(self):
        data = get_file_content('/proc/cmdline')
        if data:
            self.facts['cmdline'] = {}
            for piece in shlex.split(data):
                item = piece.split('=', 1)
                if len(item) == 1:
                    self.facts['cmdline'][item[0]] = True
                else:
                    self.facts['cmdline'][item[0]] = item[1]

    def get_public_ssh_host_keys(self):
        dsa_filename = '/etc/ssh/ssh_host_dsa_key.pub'
        rsa_filename = '/etc/ssh/ssh_host_rsa_key.pub'
        ecdsa_filename = '/etc/ssh/ssh_host_ecdsa_key.pub'

        if self.facts['system'] == 'Darwin':
            dsa_filename = '/etc/ssh_host_dsa_key.pub'
            rsa_filename = '/etc/ssh_host_rsa_key.pub'
            ecdsa_filename = '/etc/ssh_host_ecdsa_key.pub'
        dsa = get_file_content(dsa_filename)
        rsa = get_file_content(rsa_filename)
        ecdsa = get_file_content(ecdsa_filename)
        if dsa is None:
            dsa = 'NA'
        else:
            self.facts['ssh_host_key_dsa_public'] = dsa.split()[1]
        if rsa is None:
            rsa = 'NA'
        else:
            self.facts['ssh_host_key_rsa_public'] = rsa.split()[1]
        if ecdsa is None:
            ecdsa = 'NA'
        else:
            self.facts['ssh_host_key_ecdsa_public'] = ecdsa.split()[1]

    def get_pkg_mgr_facts(self):
        self.facts['pkg_mgr'] = 'unknown'
        for pkg in Facts.PKG_MGRS:
            if os.path.exists(pkg['path']):
                self.facts['pkg_mgr'] = pkg['name']
        if self.facts['system'] == 'OpenBSD':
                self.facts['pkg_mgr'] = 'openbsd_pkg'

    def get_lsb_facts(self):
        lsb_path = module.get_bin_path('lsb_release')
        if lsb_path:
            rc, out, err = module.run_command([lsb_path, "-a"])
            if rc == 0:
                self.facts['lsb'] = {}
            for line in out.split('\n'):
                if len(line) < 1:
                    continue
                value = line.split(':', 1)[1].strip()
                if 'LSB Version:' in line:
                    self.facts['lsb']['release'] = value
                elif 'Distributor ID:' in line:
                    self.facts['lsb']['id'] = value
                elif 'Description:' in line:
                    self.facts['lsb']['description'] = value
                elif 'Release:' in line:
                    self.facts['lsb']['release'] = value
                elif 'Codename:' in line:
                    self.facts['lsb']['codename'] = value
            if 'lsb' in self.facts and 'release' in self.facts['lsb']:
                self.facts['lsb']['major_release'] = self.facts['lsb']['release'].split('.')[0]
        elif lsb_path is None and os.path.exists('/etc/lsb-release'):
            self.facts['lsb'] = {}
            f = open('/etc/lsb-release', 'r')
            try:
                for line in f.readlines():
                    value = line.split('=',1)[1].strip()
                    if 'DISTRIB_ID' in line:
                        self.facts['lsb']['id'] = value
                    elif 'DISTRIB_RELEASE' in line:
                        self.facts['lsb']['release'] = value
                    elif 'DISTRIB_DESCRIPTION' in line:
                        self.facts['lsb']['description'] = value
                    elif 'DISTRIB_CODENAME' in line:
                        self.facts['lsb']['codename'] = value
            finally:
                f.close()
        else:
            return self.facts

        if 'lsb' in self.facts and 'release' in self.facts['lsb']:
            self.facts['lsb']['major_release'] = self.facts['lsb']['release'].split('.')[0]


    def get_selinux_facts(self):
        if not HAVE_SELINUX:
            self.facts['selinux'] = False
            return
        self.facts['selinux'] = {}
        if not selinux.is_selinux_enabled():
            self.facts['selinux']['status'] = 'disabled'
        else:
            self.facts['selinux']['status'] = 'enabled'
            try:
                self.facts['selinux']['policyvers'] = selinux.security_policyvers()
            except OSError, e:
                self.facts['selinux']['policyvers'] = 'unknown'
            try:
                (rc, configmode) = selinux.selinux_getenforcemode()
                if rc == 0:
                    self.facts['selinux']['config_mode'] = Facts.SELINUX_MODE_DICT.get(configmode, 'unknown')
                else:
                    self.facts['selinux']['config_mode'] = 'unknown'
            except OSError, e:
                self.facts['selinux']['config_mode'] = 'unknown'
            try:
                mode = selinux.security_getenforce()
                self.facts['selinux']['mode'] = Facts.SELINUX_MODE_DICT.get(mode, 'unknown')
            except OSError, e:
                self.facts['selinux']['mode'] = 'unknown'
            try:
                (rc, policytype) = selinux.selinux_getpolicytype()
                if rc == 0:
                    self.facts['selinux']['type'] = policytype
                else:
                    self.facts['selinux']['type'] = 'unknown'
            except OSError, e:
                self.facts['selinux']['type'] = 'unknown'


    def get_date_time_facts(self):
        self.facts['date_time'] = {}

        now = datetime.datetime.now()
        self.facts['date_time']['year'] = now.strftime('%Y')
        self.facts['date_time']['month'] = now.strftime('%m')
        self.facts['date_time']['weekday'] = now.strftime('%A')
        self.facts['date_time']['day'] = now.strftime('%d')
        self.facts['date_time']['hour'] = now.strftime('%H')
        self.facts['date_time']['minute'] = now.strftime('%M')
        self.facts['date_time']['second'] = now.strftime('%S')
        self.facts['date_time']['epoch'] = now.strftime('%s')
        if self.facts['date_time']['epoch'] == '' or self.facts['date_time']['epoch'][0] == '%':
            self.facts['date_time']['epoch'] = str(int(time.time()))
        self.facts['date_time']['date'] = now.strftime('%Y-%m-%d')
        self.facts['date_time']['time'] = now.strftime('%H:%M:%S')
        self.facts['date_time']['iso8601_micro'] = now.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        self.facts['date_time']['iso8601'] = now.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        self.facts['date_time']['tz'] = time.strftime("%Z")
        self.facts['date_time']['tz_offset'] = time.strftime("%z")


    # User
    def get_user_facts(self):
        self.facts['user_id'] = getpass.getuser()

    def get_env_facts(self):
        self.facts['env'] = {}
        for k,v in os.environ.iteritems():
            self.facts['env'][k] = v

class Hardware(Facts):
    """
    This is a generic Hardware subclass of Facts.  This should be further
    subclassed to implement per platform.  If you subclass this, it
    should define:
    - memfree_mb
    - memtotal_mb
    - swapfree_mb
    - swaptotal_mb
    - processor (a list)
    - processor_cores
    - processor_count

    All subclasses MUST define platform.
    """
    platform = 'Generic'

    def __new__(cls, *arguments, **keyword):
        subclass = cls
        for sc in Hardware.__subclasses__():
            if sc.platform == platform.system():
                subclass = sc
        return super(cls, subclass).__new__(subclass, *arguments, **keyword)

    def __init__(self):
        Facts.__init__(self)

    def populate(self):
        return self.facts

class LinuxHardware(Hardware):
    """
    Linux-specific subclass of Hardware.  Defines memory and CPU facts:
    - memfree_mb
    - memtotal_mb
    - swapfree_mb
    - swaptotal_mb
    - processor (a list)
    - processor_cores
    - processor_count

    In addition, it also defines number of DMI facts and device facts.
    """

    platform = 'Linux'
    MEMORY_FACTS = ['MemTotal', 'SwapTotal', 'MemFree', 'SwapFree']

    def __init__(self):
        Hardware.__init__(self)

    def populate(self):
        self.get_cpu_facts()
        self.get_memory_facts()
        self.get_dmi_facts()
        self.get_device_facts()
        try:
            self.get_mount_facts()
        except TimeoutError:
            pass
        return self.facts

    def get_memory_facts(self):
        if not os.access("/proc/meminfo", os.R_OK):
            return
        for line in open("/proc/meminfo").readlines():
            data = line.split(":", 1)
            key = data[0]
            if key in LinuxHardware.MEMORY_FACTS:
                val = data[1].strip().split(' ')[0]
                self.facts["%s_mb" % key.lower()] = long(val) / 1024

    def get_cpu_facts(self):
        i = 0
        physid = 0
        coreid = 0
        sockets = {}
        cores = {}
        if not os.access("/proc/cpuinfo", os.R_OK):
            return
        self.facts['processor'] = []
        for line in open("/proc/cpuinfo").readlines():
            data = line.split(":", 1)
            key = data[0].strip()
            # model name is for Intel arch, Processor (mind the uppercase P)
            # works for some ARM devices, like the Sheevaplug.
            if key == 'model name' or key == 'Processor':
                if 'processor' not in self.facts:
                    self.facts['processor'] = []
                self.facts['processor'].append(data[1].strip())
                i += 1
            elif key == 'physical id':
                physid = data[1].strip()
                if physid not in sockets:
                    sockets[physid] = 1
            elif key == 'core id':
                coreid = data[1].strip()
                if coreid not in sockets:
                    cores[coreid] = 1
            elif key == 'cpu cores':
                sockets[physid] = int(data[1].strip())
            elif key == 'siblings':
                cores[coreid] = int(data[1].strip())
        self.facts['processor_count'] = sockets and len(sockets) or i
        self.facts['processor_cores'] = sockets.values() and sockets.values()[0] or 1
        self.facts['processor_threads_per_core'] = ((cores.values() and
            cores.values()[0] or 1) / self.facts['processor_cores'])
        self.facts['processor_vcpus'] = (self.facts['processor_threads_per_core'] *
            self.facts['processor_count'] * self.facts['processor_cores'])

    def get_dmi_facts(self):
        ''' learn dmi facts from system

        Try /sys first for dmi related facts.
        If that is not available, fall back to dmidecode executable '''

        if os.path.exists('/sys/devices/virtual/dmi/id/product_name'):
            # Use kernel DMI info, if available

            # DMI SPEC -- http://www.dmtf.org/sites/default/files/standards/documents/DSP0134_2.7.0.pdf
            FORM_FACTOR = [ "Unknown", "Other", "Unknown", "Desktop",
                            "Low Profile Desktop", "Pizza Box", "Mini Tower", "Tower",
                            "Portable", "Laptop", "Notebook", "Hand Held", "Docking Station",
                            "All In One", "Sub Notebook", "Space-saving", "Lunch Box",
                            "Main Server Chassis", "Expansion Chassis", "Sub Chassis",
                            "Bus Expansion Chassis", "Peripheral Chassis", "RAID Chassis",
                            "Rack Mount Chassis", "Sealed-case PC", "Multi-system",
                            "CompactPCI", "AdvancedTCA", "Blade" ]

            DMI_DICT = {
                    'bios_date': '/sys/devices/virtual/dmi/id/bios_date',
                    'bios_version': '/sys/devices/virtual/dmi/id/bios_version',
                    'form_factor': '/sys/devices/virtual/dmi/id/chassis_type',
                    'product_name': '/sys/devices/virtual/dmi/id/product_name',
                    'product_serial': '/sys/devices/virtual/dmi/id/product_serial',
                    'product_uuid': '/sys/devices/virtual/dmi/id/product_uuid',
                    'product_version': '/sys/devices/virtual/dmi/id/product_version',
                    'system_vendor': '/sys/devices/virtual/dmi/id/sys_vendor'
                    }

            for (key,path) in DMI_DICT.items():
                data = get_file_content(path)
                if data is not None:
                    if key == 'form_factor':
                        try:
                            self.facts['form_factor'] = FORM_FACTOR[int(data)]
                        except IndexError, e:
                            self.facts['form_factor'] = 'unknown (%s)' % data
                    else:
                        self.facts[key] = data
                else:
                    self.facts[key] = 'NA'

        else:
            # Fall back to using dmidecode, if available
            dmi_bin = module.get_bin_path('dmidecode')
            DMI_DICT = {
                    'bios_date': 'bios-release-date',
                    'bios_version': 'bios-version',
                    'form_factor': 'chassis-type',
                    'product_name': 'system-product-name',
                    'product_serial': 'system-serial-number',
                    'product_uuid': 'system-uuid',
                    'product_version': 'system-version',
                    'system_vendor': 'system-manufacturer'
                    }
            for (k, v) in DMI_DICT.items():
                if dmi_bin is not None:
                    (rc, out, err) = module.run_command('%s -s %s' % (dmi_bin, v))
                    if rc == 0:
                        # Strip out commented lines (specific dmidecode output)
                        thisvalue = ''.join([ line for line in out.split('\n') if not line.startswith('#') ])
                        try:
                            json.dumps(thisvalue)
                        except UnicodeDecodeError:
                            thisvalue = "NA"

                        self.facts[k] = thisvalue
                    else:
                        self.facts[k] = 'NA'
                else:
                    self.facts[k] = 'NA'

    @timeout(10)
    def get_mount_facts(self):
        self.facts['mounts'] = []
        mtab = get_file_content('/etc/mtab', '')
        for line in mtab.split('\n'):
            if line.startswith('/'):
                fields = line.rstrip('\n').split()
                if(fields[2] != 'none'):
                    size_total = None
                    size_available = None
                    try:
                        statvfs_result = os.statvfs(fields[1])
                        size_total = statvfs_result.f_bsize * statvfs_result.f_blocks
                        size_available = statvfs_result.f_bsize * (statvfs_result.f_bavail)
                    except OSError, e:
                        continue

                    self.facts['mounts'].append(
                        {'mount': fields[1],
                         'device':fields[0],
                         'fstype': fields[2],
                         'options': fields[3],
                         # statvfs data
                         'size_total': size_total,
                         'size_available': size_available,
                         })

    def get_device_facts(self):
        self.facts['devices'] = {}
        lspci = module.get_bin_path('lspci')
        if lspci:
            rc, pcidata, err = module.run_command([lspci, '-D'])
        else:
            pcidata = None

        try:
            block_devs = os.listdir("/sys/block")
        except OSError:
            return

        for block in block_devs:
            virtual = 1
            sysfs_no_links = 0
            try:
                path = os.readlink(os.path.join("/sys/block/", block))
            except OSError, e:
                if e.errno == errno.EINVAL:
                    path = block
                    sysfs_no_links = 1
                else:
                    continue
            if "virtual" in path:
                continue
            sysdir = os.path.join("/sys/block", path)
            if sysfs_no_links == 1:
                for folder in os.listdir(sysdir):
                    if "device" in folder:
                        virtual = 0
                        break
                if virtual:
                    continue
            d = {}
            diskname = os.path.basename(sysdir)
            for key in ['vendor', 'model']:
                d[key] = get_file_content(sysdir + "/device/" + key)

            for key,test in [ ('removable','/removable'), \
                              ('support_discard','/queue/discard_granularity'),
                              ]:
                d[key] = get_file_content(sysdir + test)

            d['partitions'] = {}
            for folder in os.listdir(sysdir):
                m = re.search("(" + diskname + "\d+)", folder)
                if m:
                    part = {}
                    partname = m.group(1)
                    part_sysdir = sysdir + "/" + partname

                    part['start'] = get_file_content(part_sysdir + "/start",0)
                    part['sectors'] = get_file_content(part_sysdir + "/size",0)
                    part['sectorsize'] = get_file_content(part_sysdir + "/queue/hw_sector_size",512)
                    part['size'] = module.pretty_bytes((float(part['sectors']) * float(part['sectorsize'])))
                    d['partitions'][partname] = part

            d['rotational'] = get_file_content(sysdir + "/queue/rotational")
            d['scheduler_mode'] = ""
            scheduler = get_file_content(sysdir + "/queue/scheduler")
            if scheduler is not None:
                m = re.match(".*?(\[(.*)\])", scheduler)
                if m:
                    d['scheduler_mode'] = m.group(2)

            d['sectors'] = get_file_content(sysdir + "/size")
            if not d['sectors']:
                d['sectors'] = 0
            d['sectorsize'] = get_file_content(sysdir + "/queue/hw_sector_size")
            if not d['sectorsize']:
                d['sectorsize'] = 512
            d['size'] = module.pretty_bytes(float(d['sectors']) * float(d['sectorsize']))

            d['host'] = ""

            # domains are numbered (0 to ffff), bus (0 to ff), slot (0 to 1f), and function (0 to 7).
            m = re.match(".+/([a-f0-9]{4}:[a-f0-9]{2}:[0|1][a-f0-9]\.[0-7])/", sysdir)
            if m and pcidata:
                pciid = m.group(1)
                did = re.escape(pciid)
                m = re.search("^" + did + "\s(.*)$", pcidata, re.MULTILINE)
                d['host'] = m.group(1)

            d['holders'] = []
            if os.path.isdir(sysdir + "/holders"):
                for folder in os.listdir(sysdir + "/holders"):
                    if not folder.startswith("dm-"):
                        continue
                    name = get_file_content(sysdir + "/holders/" + folder + "/dm/name")
                    if name:
                        d['holders'].append(name)
                    else:
                        d['holders'].append(folder)

            self.facts['devices'][diskname] = d


class SunOSHardware(Hardware):
    """
    In addition to the generic memory and cpu facts, this also sets
    swap_reserved_mb and swap_allocated_mb that is available from *swap -s*.
    """
    platform = 'SunOS'

    def __init__(self):
        Hardware.__init__(self)

    def populate(self):
        self.get_cpu_facts()
        self.get_memory_facts()
        return self.facts

    def get_cpu_facts(self):
        physid = 0
        sockets = {}
        rc, out, err = module.run_command("/usr/bin/kstat cpu_info")
        self.facts['processor'] = []
        for line in out.split('\n'):
            if len(line) < 1:
                continue
            data = line.split(None, 1)
            key = data[0].strip()
            # "brand" works on Solaris 10 & 11. "implementation" for Solaris 9.
            if key == 'module:':
                brand = ''
            elif key == 'brand':
                brand = data[1].strip()
            elif key == 'clock_MHz':
                clock_mhz = data[1].strip()
            elif key == 'implementation':
                processor = brand or data[1].strip()
                # Add clock speed to description for SPARC CPU
                if self.facts['machine'] != 'i86pc':
                    processor += " @ " + clock_mhz + "MHz"
                if 'processor' not in self.facts:
                    self.facts['processor'] = []
                self.facts['processor'].append(processor)
            elif key == 'chip_id':
                physid = data[1].strip()
                if physid not in sockets:
                    sockets[physid] = 1
                else:
                    sockets[physid] += 1
        # Counting cores on Solaris can be complicated.
        # https://blogs.oracle.com/mandalika/entry/solaris_show_me_the_cpu
        # Treat 'processor_count' as physical sockets and 'processor_cores' as
        # virtual CPUs visisble to Solaris. Not a true count of cores for modern SPARC as
        # these processors have: sockets -> cores -> threads/virtual CPU.
        if len(sockets) > 0:
            self.facts['processor_count'] = len(sockets)
            self.facts['processor_cores'] = reduce(lambda x, y: x + y, sockets.values())
        else:
            self.facts['processor_cores'] = 'NA'
            self.facts['processor_count'] = len(self.facts['processor'])

    def get_memory_facts(self):
        rc, out, err = module.run_command(["/usr/sbin/prtconf"])
        for line in out.split('\n'):
            if 'Memory size' in line:
                self.facts['memtotal_mb'] = line.split()[2]
        rc, out, err = module.run_command("/usr/sbin/swap -s")
        allocated = long(out.split()[1][:-1])
        reserved = long(out.split()[5][:-1])
        used = long(out.split()[8][:-1])
        free = long(out.split()[10][:-1])
        self.facts['swapfree_mb'] = free / 1024
        self.facts['swaptotal_mb'] = (free + used) / 1024
        self.facts['swap_allocated_mb'] = allocated / 1024
        self.facts['swap_reserved_mb'] = reserved / 1024

class OpenBSDHardware(Hardware):
    """
    OpenBSD-specific subclass of Hardware. Defines memory, CPU and device facts:
    - memfree_mb
    - memtotal_mb
    - swapfree_mb
    - swaptotal_mb
    - processor (a list)
    - processor_cores
    - processor_count
    - processor_speed
    - devices
    """
    platform = 'OpenBSD'
    DMESG_BOOT = '/var/run/dmesg.boot'

    def __init__(self):
        Hardware.__init__(self)

    def populate(self):
        self.sysctl = self.get_sysctl()
        self.get_memory_facts()
        self.get_processor_facts()
        self.get_device_facts()
        return self.facts

    def get_sysctl(self):
        rc, out, err = module.run_command(["/sbin/sysctl", "hw"])
        if rc != 0:
            return dict()
        sysctl = dict()
        for line in out.splitlines():
            (key, value) = line.split('=')
            sysctl[key] = value.strip()
        return sysctl

    def get_memory_facts(self):
        # Get free memory. vmstat output looks like:
        #  procs    memory       page                    disks    traps          cpu
        #  r b w    avm     fre  flt  re  pi  po  fr  sr wd0 fd0  int   sys   cs us sy id
        #  0 0 0  47512   28160   51   0   0   0   0   0   1   0  116    89   17  0  1 99
        rc, out, err = module.run_command("/usr/bin/vmstat")
        if rc == 0:
            self.facts['memfree_mb'] = long(out.splitlines()[-1].split()[4]) / 1024
            self.facts['memtotal_mb'] = long(self.sysctl['hw.usermem']) / 1024 / 1024

        # Get swapctl info. swapctl output looks like:
        # total: 69268 1K-blocks allocated, 0 used, 69268 available
        # And for older OpenBSD:
        # total: 69268k bytes allocated = 0k used, 69268k available
        rc, out, err = module.run_command("/sbin/swapctl -sk")
        if rc == 0:
            data = out.split()
            self.facts['swapfree_mb'] = long(data[-2].translate(None, "kmg")) / 1024
            self.facts['swaptotal_mb'] = long(data[1].translate(None, "kmg")) / 1024

    def get_processor_facts(self):
        processor = []
        dmesg_boot = get_file_content(OpenBSDHardware.DMESG_BOOT)
        if not dmesg_boot:
            rc, dmesg_boot, err = module.run_command("/sbin/dmesg")
        i = 0
        for line in dmesg_boot.splitlines():
            if line.split(' ', 1)[0] == 'cpu%i:' % i:
                processor.append(line.split(' ', 1)[1])
                i = i + 1
        processor_count = i
        self.facts['processor'] = processor
        self.facts['processor_count'] = processor_count
        # I found no way to figure out the number of Cores per CPU in OpenBSD
        self.facts['processor_cores'] = 'NA'

    def get_device_facts(self):
        devices = []
        devices.extend(self.sysctl['hw.disknames'].split(','))
        self.facts['devices'] = devices

class FreeBSDHardware(Hardware):
    """
    FreeBSD-specific subclass of Hardware.  Defines memory and CPU facts:
    - memfree_mb
    - memtotal_mb
    - swapfree_mb
    - swaptotal_mb
    - processor (a list)
    - processor_cores
    - processor_count
    - devices
    """
    platform = 'FreeBSD'
    DMESG_BOOT = '/var/run/dmesg.boot'

    def __init__(self):
        Hardware.__init__(self)

    def populate(self):
        self.get_cpu_facts()
        self.get_memory_facts()
        self.get_dmi_facts()
        self.get_device_facts()
        try:
            self.get_mount_facts()
        except TimeoutError:
            pass
        return self.facts

    def get_cpu_facts(self):
        self.facts['processor'] = []
        rc, out, err = module.run_command("/sbin/sysctl -n hw.ncpu")
        self.facts['processor_count'] = out.strip()

        dmesg_boot = get_file_content(FreeBSDHardware.DMESG_BOOT)
        if not dmesg_boot:
            rc, dmesg_boot, err = module.run_command("/sbin/dmesg")
        for line in dmesg_boot.split('\n'):
            if 'CPU:' in line:
                cpu = re.sub(r'CPU:\s+', r"", line)
                self.facts['processor'].append(cpu.strip())
            if 'Logical CPUs per core' in line:
                self.facts['processor_cores'] = line.split()[4]


    def get_memory_facts(self):
        rc, out, err = module.run_command("/sbin/sysctl vm.stats")
        for line in out.split('\n'):
            data = line.split()
            if 'vm.stats.vm.v_page_size' in line:
                pagesize = long(data[1])
            if 'vm.stats.vm.v_page_count' in line:
                pagecount = long(data[1])
            if 'vm.stats.vm.v_free_count' in line:
                freecount = long(data[1])
        self.facts['memtotal_mb'] = pagesize * pagecount / 1024 / 1024
        self.facts['memfree_mb'] = pagesize * freecount / 1024 / 1024
        # Get swapinfo.  swapinfo output looks like:
        # Device          1M-blocks     Used    Avail Capacity
        # /dev/ada0p3        314368        0   314368     0%
        #
        rc, out, err = module.run_command("/usr/sbin/swapinfo -m")
        lines = out.split('\n')
        if len(lines[-1]) == 0:
            lines.pop()
        data = lines[-1].split()
        self.facts['swaptotal_mb'] = data[1]
        self.facts['swapfree_mb'] = data[3]

    @timeout(10)
    def get_mount_facts(self):
        self.facts['mounts'] = []
        fstab = get_file_content('/etc/fstab')
        if fstab:
            for line in fstab.split('\n'):
                if line.startswith('#') or line.strip() == '':
                    continue
                fields = re.sub(r'\s+',' ',line.rstrip('\n')).split()
                self.facts['mounts'].append({'mount': fields[1] , 'device': fields[0], 'fstype' : fields[2], 'options': fields[3]})

    def get_device_facts(self):
        sysdir = '/dev'
        self.facts['devices'] = {}
        drives = re.compile('(ada?\d+|da\d+|a?cd\d+)') #TODO: rc, disks, err = module.run_command("/sbin/sysctl kern.disks")
        slices = re.compile('(ada?\d+s\d+\w*|da\d+s\d+\w*)')
        if os.path.isdir(sysdir):
            dirlist = sorted(os.listdir(sysdir))
            for device in dirlist:
                d = drives.match(device)
                if d:
                    self.facts['devices'][d.group(1)] = []
                s = slices.match(device)
                if s:
                    self.facts['devices'][d.group(1)].append(s.group(1))

    def get_dmi_facts(self):
        ''' learn dmi facts from system

        Use dmidecode executable if available'''

        # Fall back to using dmidecode, if available
        dmi_bin = module.get_bin_path('dmidecode')
        DMI_DICT = dict(
            bios_date='bios-release-date',
            bios_version='bios-version',
            form_factor='chassis-type',
            product_name='system-product-name',
            product_serial='system-serial-number',
            product_uuid='system-uuid',
            product_version='system-version',
            system_vendor='system-manufacturer'
        )
        for (k, v) in DMI_DICT.items():
            if dmi_bin is not None:
                (rc, out, err) = module.run_command('%s -s %s' % (dmi_bin, v))
                if rc == 0:
                    # Strip out commented lines (specific dmidecode output)
                    self.facts[k] = ''.join([ line for line in out.split('\n') if not line.startswith('#') ])
                    try:
                        json.dumps(self.facts[k])
                    except UnicodeDecodeError:
                        self.facts[k] = 'NA'
                else:
                    self.facts[k] = 'NA'
            else:
                self.facts[k] = 'NA'


class NetBSDHardware(Hardware):
    """
    NetBSD-specific subclass of Hardware.  Defines memory and CPU facts:
    - memfree_mb
    - memtotal_mb
    - swapfree_mb
    - swaptotal_mb
    - processor (a list)
    - processor_cores
    - processor_count
    - devices
    """
    platform = 'NetBSD'
    MEMORY_FACTS = ['MemTotal', 'SwapTotal', 'MemFree', 'SwapFree']

    def __init__(self):
        Hardware.__init__(self)

    def populate(self):
        self.get_cpu_facts()
        self.get_memory_facts()
        try:
            self.get_mount_facts()
        except TimeoutError:
            pass
        return self.facts

    def get_cpu_facts(self):

        i = 0
        physid = 0
        sockets = {}
        if not os.access("/proc/cpuinfo", os.R_OK):
            return
        self.facts['processor'] = []
        for line in open("/proc/cpuinfo").readlines():
            data = line.split(":", 1)
            key = data[0].strip()
            # model name is for Intel arch, Processor (mind the uppercase P)
            # works for some ARM devices, like the Sheevaplug.
            if key == 'model name' or key == 'Processor':
                if 'processor' not in self.facts:
                    self.facts['processor'] = []
                self.facts['processor'].append(data[1].strip())
                i += 1
            elif key == 'physical id':
                physid = data[1].strip()
                if physid not in sockets:
                    sockets[physid] = 1
            elif key == 'cpu cores':
                sockets[physid] = int(data[1].strip())
        if len(sockets) > 0:
            self.facts['processor_count'] = len(sockets)
            self.facts['processor_cores'] = reduce(lambda x, y: x + y, sockets.values())
        else:
            self.facts['processor_count'] = i
            self.facts['processor_cores'] = 'NA'

    def get_memory_facts(self):
        if not os.access("/proc/meminfo", os.R_OK):
            return
        for line in open("/proc/meminfo").readlines():
            data = line.split(":", 1)
            key = data[0]
            if key in NetBSDHardware.MEMORY_FACTS:
                val = data[1].strip().split(' ')[0]
                self.facts["%s_mb" % key.lower()] = long(val) / 1024

    @timeout(10)
    def get_mount_facts(self):
        self.facts['mounts'] = []
        fstab = get_file_content('/etc/fstab')
        if fstab:
            for line in fstab.split('\n'):
                if line.startswith('#') or line.strip() == '':
                    continue
                fields = re.sub(r'\s+',' ',line.rstrip('\n')).split()
                self.facts['mounts'].append({'mount': fields[1] , 'device': fields[0], 'fstype' : fields[2], 'options': fields[3]})

class AIX(Hardware):
    """
    AIX-specific subclass of Hardware.  Defines memory and CPU facts:
    - memfree_mb
    - memtotal_mb
    - swapfree_mb
    - swaptotal_mb
    - processor (a list)
    - processor_cores
    - processor_count
    """
    platform = 'AIX'

    def __init__(self):
        Hardware.__init__(self)

    def populate(self):
        self.get_cpu_facts()
        self.get_memory_facts()
        self.get_dmi_facts()
        return self.facts

    def get_cpu_facts(self):
        self.facts['processor'] = []


        rc, out, err = module.run_command("/usr/sbin/lsdev -Cc processor")
        if out:
            i = 0
            for line in out.split('\n'):

                if 'Available' in line:
                    if i == 0:
                        data = line.split(' ')
                        cpudev = data[0]

                    i += 1
            self.facts['processor_count'] = int(i)

            rc, out, err = module.run_command("/usr/sbin/lsattr -El " + cpudev + " -a type")

            data = out.split(' ')
            self.facts['processor'] = data[1]

            rc, out, err = module.run_command("/usr/sbin/lsattr -El " + cpudev + " -a smt_threads")

            data = out.split(' ')
            self.facts['processor_cores'] = int(data[1])

    def get_memory_facts(self):
        pagesize = 4096
        rc, out, err = module.run_command("/usr/bin/vmstat -v")
        for line in out.split('\n'):
            data = line.split()
            if 'memory pages' in line:
                pagecount = long(data[0])
            if 'free pages' in line:
                freecount = long(data[0])
        self.facts['memtotal_mb'] = pagesize * pagecount / 1024 / 1024
        self.facts['memfree_mb'] = pagesize * freecount / 1024 / 1024
        # Get swapinfo.  swapinfo output looks like:
        # Device          1M-blocks     Used    Avail Capacity
        # /dev/ada0p3        314368        0   314368     0%
        #
        rc, out, err = module.run_command("/usr/sbin/lsps -s")
        if out:
            lines = out.split('\n')
            data = lines[1].split()
            swaptotal_mb = long(data[0].rstrip('MB'))
            percused = int(data[1].rstrip('%'))
            self.facts['swaptotal_mb'] = swaptotal_mb
            self.facts['swapfree_mb'] = long(swaptotal_mb * ( 100 - percused ) / 100)

    def get_dmi_facts(self):
        rc, out, err = module.run_command("/usr/sbin/lsattr -El sys0 -a fwversion")
        data = out.split()
        self.facts['firmware_version'] = data[1].strip('IBM,')

class HPUX(Hardware):
    """
    HP-UX-specifig subclass of Hardware. Defines memory and CPU facts:
    - memfree_mb
    - memtotal_mb
    - swapfree_mb
    - swaptotal_mb
    - processor
    - processor_cores
    - processor_count
    - model
    - firmware
    """

    platform = 'HP-UX'

    def __init__(self):
        Hardware.__init__(self)

    def populate(self):
        self.get_cpu_facts()
        self.get_memory_facts()
        self.get_hw_facts()
        return self.facts

    def get_cpu_facts(self):
        if self.facts['architecture'] == '9000/800':
            rc, out, err = module.run_command("ioscan -FkCprocessor | wc -l", use_unsafe_shell=True)
            self.facts['processor_count'] = int(out.strip())
        #Working with machinfo mess
        elif self.facts['architecture'] == 'ia64':
            if self.facts['distribution_version'] == "B.11.23":
                rc, out, err = module.run_command("/usr/contrib/bin/machinfo | grep 'Number of CPUs'", use_unsafe_shell=True)
                self.facts['processor_count'] = int(out.strip().split('=')[1])
                rc, out, err = module.run_command("/usr/contrib/bin/machinfo | grep 'processor family'", use_unsafe_shell=True)
                self.facts['processor'] = re.search('.*(Intel.*)', out).groups()[0].strip()
                rc, out, err = module.run_command("ioscan -FkCprocessor | wc -l", use_unsafe_shell=True)
                self.facts['processor_cores'] = int(out.strip())
            if self.facts['distribution_version'] == "B.11.31":
                #if machinfo return cores strings release B.11.31 > 1204
                rc, out, err = module.run_command("/usr/contrib/bin/machinfo | grep core | wc -l", use_unsafe_shell=True)
                if out.strip()== '0':
                    rc, out, err = module.run_command("/usr/contrib/bin/machinfo | grep Intel", use_unsafe_shell=True)
                    self.facts['processor_count'] = int(out.strip().split(" ")[0])
                    #If hyperthreading is active divide cores by 2
                    rc, out, err = module.run_command("/usr/sbin/psrset | grep LCPU", use_unsafe_shell=True)
                    data = re.sub(' +',' ',out).strip().split(' ')
                    if len(data) == 1:
                        hyperthreading = 'OFF'
                    else:
                        hyperthreading = data[1]
                    rc, out, err = module.run_command("/usr/contrib/bin/machinfo | grep logical", use_unsafe_shell=True)
                    data = out.strip().split(" ")
                    if hyperthreading == 'ON':
                        self.facts['processor_cores'] = int(data[0])/2
                    else:
                        if len(data) == 1:
                            self.facts['processor_cores'] = self.facts['processor_count']
                        else:
                            self.facts['processor_cores'] = int(data[0])
                    rc, out, err = module.run_command("/usr/contrib/bin/machinfo | grep Intel |cut -d' ' -f4-", use_unsafe_shell=True)
                    self.facts['processor'] = out.strip()
                else:
                    rc, out, err = module.run_command("/usr/contrib/bin/machinfo | egrep 'socket[s]?$' | tail -1", use_unsafe_shell=True)
                    self.facts['processor_count'] = int(out.strip().split(" ")[0])
                    rc, out, err = module.run_command("/usr/contrib/bin/machinfo | grep -e '[0-9] core' | tail -1", use_unsafe_shell=True)
                    self.facts['processor_cores'] = int(out.strip().split(" ")[0])
                    rc, out, err = module.run_command("/usr/contrib/bin/machinfo | grep Intel", use_unsafe_shell=True)
                    self.facts['processor'] = out.strip()

    def get_memory_facts(self):
        pagesize = 4096
        rc, out, err = module.run_command("/usr/bin/vmstat | tail -1", use_unsafe_shell=True)
        data = int(re.sub(' +',' ',out).split(' ')[5].strip())
        self.facts['memfree_mb'] = pagesize * data / 1024 / 1024
        if self.facts['architecture'] == '9000/800':
            rc, out, err = module.run_command("grep Physical /var/adm/syslog/syslog.log")
            data = re.search('.*Physical: ([0-9]*) Kbytes.*',out).groups()[0].strip()
            self.facts['memtotal_mb'] = int(data) / 1024
        else:
            rc, out, err = module.run_command("/usr/contrib/bin/machinfo | grep Memory", use_unsafe_shell=True)
            data = re.search('Memory[\ :=]*([0-9]*).*MB.*',out).groups()[0].strip()
            self.facts['memtotal_mb'] = int(data)
        rc, out, err = module.run_command("/usr/sbin/swapinfo -m -d -f -q")
        self.facts['swaptotal_mb'] = int(out.strip())
        rc, out, err = module.run_command("/usr/sbin/swapinfo -m -d -f | egrep '^dev|^fs'", use_unsafe_shell=True)
        swap = 0
        for line in out.strip().split('\n'):
            swap += int(re.sub(' +',' ',line).split(' ')[3].strip())
        self.facts['swapfree_mb'] = swap

    def get_hw_facts(self):
        rc, out, err = module.run_command("model")
        self.facts['model'] = out.strip()
        if self.facts['architecture'] == 'ia64':
            separator = ':'
            if self.facts['distribution_version'] == "B.11.23":
                separator = '='
            rc, out, err = module.run_command("/usr/contrib/bin/machinfo |grep -i 'Firmware revision' | grep -v BMC", use_unsafe_shell=True)
            self.facts['firmware_version'] = out.split(separator)[1].strip()


class Darwin(Hardware):
    """
    Darwin-specific subclass of Hardware.  Defines memory and CPU facts:
    - processor
    - processor_cores
    - memtotal_mb
    - memfree_mb
    - model
    - osversion
    - osrevision
    """
    platform = 'Darwin'

    def __init__(self):
        Hardware.__init__(self)

    def populate(self):
        self.sysctl = self.get_sysctl()
        self.get_mac_facts()
        self.get_cpu_facts()
        self.get_memory_facts()
        return self.facts

    def get_sysctl(self):
        rc, out, err = module.run_command(["/usr/sbin/sysctl", "hw", "machdep", "kern"])
        if rc != 0:
            return dict()
        sysctl = dict()
        for line in out.splitlines():
            if line.rstrip("\n"):
                (key, value) = re.split(' = |: ', line, maxsplit=1)
                sysctl[key] = value.strip()
        return sysctl

    def get_system_profile(self):
        rc, out, err = module.run_command(["/usr/sbin/system_profiler", "SPHardwareDataType"])
        if rc != 0:
            return dict()
        system_profile = dict()
        for line in out.splitlines():
            if ': ' in line:
                (key, value) = line.split(': ', 1)
                system_profile[key.strip()] = ' '.join(value.strip().split())
        return system_profile

    def get_mac_facts(self):
        self.facts['model'] = self.sysctl['hw.model']
        self.facts['osversion'] = self.sysctl['kern.osversion']
        self.facts['osrevision'] = self.sysctl['kern.osrevision']

    def get_cpu_facts(self):
        if 'machdep.cpu.brand_string' in self.sysctl: # Intel
            self.facts['processor'] = self.sysctl['machdep.cpu.brand_string']
            self.facts['processor_cores'] = self.sysctl['machdep.cpu.core_count']
        else: # PowerPC
            system_profile = self.get_system_profile()
            self.facts['processor'] = '%s @ %s' % (system_profile['Processor Name'], system_profile['Processor Speed'])
            self.facts['processor_cores'] = self.sysctl['hw.physicalcpu']

    def get_memory_facts(self):
        self.facts['memtotal_mb'] = long(self.sysctl['hw.memsize']) / 1024 / 1024
        self.facts['memfree_mb'] = long(self.sysctl['hw.usermem']) / 1024 / 1024

class Network(Facts):
    """
    This is a generic Network subclass of Facts.  This should be further
    subclassed to implement per platform.  If you subclass this,
    you must define:
    - interfaces (a list of interface names)
    - interface_<name> dictionary of ipv4, ipv6, and mac address information.

    All subclasses MUST define platform.
    """
    platform = 'Generic'

    IPV6_SCOPE = { '0' : 'global',
                   '10' : 'host',
                   '20' : 'link',
                   '40' : 'admin',
                   '50' : 'site',
                   '80' : 'organization' }

    def __new__(cls, *arguments, **keyword):
        subclass = cls
        for sc in Network.__subclasses__():
            if sc.platform == platform.system():
                subclass = sc
        return super(cls, subclass).__new__(subclass, *arguments, **keyword)

    def __init__(self, module):
        self.module = module
        Facts.__init__(self)

    def populate(self):
        return self.facts

class LinuxNetwork(Network):
    """
    This is a Linux-specific subclass of Network.  It defines
    - interfaces (a list of interface names)
    - interface_<name> dictionary of ipv4, ipv6, and mac address information.
    - all_ipv4_addresses and all_ipv6_addresses: lists of all configured addresses.
    - ipv4_address and ipv6_address: the first non-local address for each family.
    """
    platform = 'Linux'

    def __init__(self, module):
        Network.__init__(self, module)

    def populate(self):
        ip_path = self.module.get_bin_path('ip')
        if ip_path is None:
            return self.facts
        default_ipv4, default_ipv6 = self.get_default_interfaces(ip_path)
        interfaces, ips = self.get_interfaces_info(ip_path, default_ipv4, default_ipv6)
        self.facts['interfaces'] = interfaces.keys()
        for iface in interfaces:
            self.facts[iface] = interfaces[iface]
        self.facts['default_ipv4'] = default_ipv4
        self.facts['default_ipv6'] = default_ipv6
        self.facts['all_ipv4_addresses'] = ips['all_ipv4_addresses']
        self.facts['all_ipv6_addresses'] = ips['all_ipv6_addresses']
        return self.facts

    def get_default_interfaces(self, ip_path):
        # Use the commands:
        #     ip -4 route get 8.8.8.8                     -> Google public DNS
        #     ip -6 route get 2404:6800:400a:800::1012    -> ipv6.google.com
        # to find out the default outgoing interface, address, and gateway
        command = dict(
            v4 = [ip_path, '-4', 'route', 'get', '8.8.8.8'],
            v6 = [ip_path, '-6', 'route', 'get', '2404:6800:400a:800::1012']
        )
        interface = dict(v4 = {}, v6 = {})
        for v in 'v4', 'v6':
            if v == 'v6' and self.facts['os_family'] == 'RedHat' \
                and self.facts['distribution_version'].startswith('4.'):
                continue
            if v == 'v6' and not socket.has_ipv6:
                continue
            rc, out, err = module.run_command(command[v])
            if not out:
                # v6 routing may result in
                #   RTNETLINK answers: Invalid argument
                continue
            words = out.split('\n')[0].split()
            # A valid output starts with the queried address on the first line
            if len(words) > 0 and words[0] == command[v][-1]:
                for i in range(len(words) - 1):
                    if words[i] == 'dev':
                        interface[v]['interface'] = words[i+1]
                    elif words[i] == 'src':
                        interface[v]['address'] = words[i+1]
                    elif words[i] == 'via' and words[i+1] != command[v][-1]:
                        interface[v]['gateway'] = words[i+1]
        return interface['v4'], interface['v6']

    def get_interfaces_info(self, ip_path, default_ipv4, default_ipv6):
        interfaces = {}
        ips = dict(
            all_ipv4_addresses = [],
            all_ipv6_addresses = [],
        )

        for path in glob.glob('/sys/class/net/*'):
            if not os.path.isdir(path):
                continue
            device = os.path.basename(path)
            interfaces[device] = { 'device': device }
            if os.path.exists(os.path.join(path, 'address')):
                macaddress = open(os.path.join(path, 'address')).read().strip()
                if macaddress and macaddress != '00:00:00:00:00:00':
                    interfaces[device]['macaddress'] = macaddress
            if os.path.exists(os.path.join(path, 'mtu')):
                interfaces[device]['mtu'] = int(open(os.path.join(path, 'mtu')).read().strip())
            if os.path.exists(os.path.join(path, 'operstate')):
                interfaces[device]['active'] = open(os.path.join(path, 'operstate')).read().strip() != 'down'
#            if os.path.exists(os.path.join(path, 'carrier')):
#                interfaces[device]['link'] = open(os.path.join(path, 'carrier')).read().strip() == '1'
            if os.path.exists(os.path.join(path, 'device','driver', 'module')):
                interfaces[device]['module'] = os.path.basename(os.path.realpath(os.path.join(path, 'device', 'driver', 'module')))
            if os.path.exists(os.path.join(path, 'type')):
                type = open(os.path.join(path, 'type')).read().strip()
                if type == '1':
                    interfaces[device]['type'] = 'ether'
                elif type == '512':
                    interfaces[device]['type'] = 'ppp'
                elif type == '772':
                    interfaces[device]['type'] = 'loopback'
            if os.path.exists(os.path.join(path, 'bridge')):
                interfaces[device]['type'] = 'bridge'
                interfaces[device]['interfaces'] = [ os.path.basename(b) for b in glob.glob(os.path.join(path, 'brif', '*')) ]
                if os.path.exists(os.path.join(path, 'bridge', 'bridge_id')):
                    interfaces[device]['id'] = open(os.path.join(path, 'bridge', 'bridge_id')).read().strip()
                if os.path.exists(os.path.join(path, 'bridge', 'stp_state')):
                    interfaces[device]['stp'] = open(os.path.join(path, 'bridge', 'stp_state')).read().strip() == '1'
            if os.path.exists(os.path.join(path, 'bonding')):
                interfaces[device]['type'] = 'bonding'
                interfaces[device]['slaves'] = open(os.path.join(path, 'bonding', 'slaves')).read().split()
                interfaces[device]['mode'] = open(os.path.join(path, 'bonding', 'mode')).read().split()[0]
                interfaces[device]['miimon'] = open(os.path.join(path, 'bonding', 'miimon')).read().split()[0]
                interfaces[device]['lacp_rate'] = open(os.path.join(path, 'bonding', 'lacp_rate')).read().split()[0]
                primary = open(os.path.join(path, 'bonding', 'primary')).read()
                if primary:
                    interfaces[device]['primary'] = primary
                    path = os.path.join(path, 'bonding', 'all_slaves_active')
                    if os.path.exists(path):
                        interfaces[device]['all_slaves_active'] = open(path).read() == '1'

            # Check whether a interface is in promiscuous mode
            if os.path.exists(os.path.join(path,'flags')):
                promisc_mode = False
                # The second byte indicates whether the interface is in promiscuous mode.
                # 1 = promisc
                # 0 = no promisc
                data = int(open(os.path.join(path, 'flags')).read().strip(),16)
                promisc_mode = (data & 0x0100 > 0)
                interfaces[device]['promisc'] = promisc_mode

            def parse_ip_output(output, secondary=False):
                for line in output.split('\n'):
                    if not line:
                        continue
                    words = line.split()
                    if words[0] == 'inet':
                        if '/' in words[1]:
                            address, netmask_length = words[1].split('/')
                        else:
                            # pointopoint interfaces do not have a prefix
                            address = words[1]
                            netmask_length = "32"
                        address_bin = struct.unpack('!L', socket.inet_aton(address))[0]
                        netmask_bin = (1<<32) - (1<<32>>int(netmask_length))
                        netmask = socket.inet_ntoa(struct.pack('!L', netmask_bin))
                        network = socket.inet_ntoa(struct.pack('!L', address_bin & netmask_bin))
                        iface = words[-1]
                        if iface != device:
                            interfaces[iface] = {}
                        if not secondary or "ipv4" not in interfaces[iface]:
                            interfaces[iface]['ipv4'] = {'address': address,
                                                         'netmask': netmask,
                                                         'network': network}
                        else:
                            if "ipv4_secondaries" not in interfaces[iface]:
                                interfaces[iface]["ipv4_secondaries"] = []
                            interfaces[iface]["ipv4_secondaries"].append({
                                'address': address,
                                'netmask': netmask,
                                'network': network,
                            })

                        # add this secondary IP to the main device
                        if secondary:
                            if "ipv4_secondaries" not in interfaces[device]:
                                interfaces[device]["ipv4_secondaries"] = []
                            interfaces[device]["ipv4_secondaries"].append({
                                'address': address,
                                'netmask': netmask,
                                'network': network,
                            })

                        # If this is the default address, update default_ipv4
                        if 'address' in default_ipv4 and default_ipv4['address'] == address:
                            default_ipv4['netmask'] = netmask
                            default_ipv4['network'] = network
                            default_ipv4['macaddress'] = macaddress
                            default_ipv4['mtu'] = interfaces[device]['mtu']
                            default_ipv4['type'] = interfaces[device].get("type", "unknown")
                            default_ipv4['alias'] = words[-1]
                        if not address.startswith('127.'):
                            ips['all_ipv4_addresses'].append(address)
                    elif words[0] == 'inet6':
                        address, prefix = words[1].split('/')
                        scope = words[3]
                        if 'ipv6' not in interfaces[device]:
                            interfaces[device]['ipv6'] = []
                        interfaces[device]['ipv6'].append({
                            'address' : address,
                            'prefix'  : prefix,
                            'scope'   : scope
                        })
                        # If this is the default address, update default_ipv6
                        if 'address' in default_ipv6 and default_ipv6['address'] == address:
                            default_ipv6['prefix']     = prefix
                            default_ipv6['scope']      = scope
                            default_ipv6['macaddress'] = macaddress
                            default_ipv6['mtu']        = interfaces[device]['mtu']
                            default_ipv6['type']       = interfaces[device].get("type", "unknown")
                        if not address == '::1':
                            ips['all_ipv6_addresses'].append(address)

            ip_path = module.get_bin_path("ip")

            args = [ip_path, 'addr', 'show', 'primary', device]
            rc, stdout, stderr = self.module.run_command(args)
            primary_data = stdout

            args = [ip_path, 'addr', 'show', 'secondary', device]
            rc, stdout, stderr = self.module.run_command(args)
            secondary_data = stdout

            parse_ip_output(primary_data)
            parse_ip_output(secondary_data, secondary=True)

        # replace : by _ in interface name since they are hard to use in template
        new_interfaces = {}
        for i in interfaces:
            if ':' in i:
                new_interfaces[i.replace(':','_')] = interfaces[i]
            else:
                new_interfaces[i] = interfaces[i]
        return new_interfaces, ips

class GenericBsdIfconfigNetwork(Network):
    """
    This is a generic BSD subclass of Network using the ifconfig command.
    It defines
    - interfaces (a list of interface names)
    - interface_<name> dictionary of ipv4, ipv6, and mac address information.
    - all_ipv4_addresses and all_ipv6_addresses: lists of all configured addresses.
    It currently does not define
    - default_ipv4 and default_ipv6
    - type, mtu and network on interfaces
    """
    platform = 'Generic_BSD_Ifconfig'

    def __init__(self, module):
        Network.__init__(self, module)

    def populate(self):

        ifconfig_path = module.get_bin_path('ifconfig')

        if ifconfig_path is None:
            return self.facts
        route_path = module.get_bin_path('route')

        if route_path is None:
            return self.facts

        default_ipv4, default_ipv6 = self.get_default_interfaces(route_path)
        interfaces, ips = self.get_interfaces_info(ifconfig_path)
        self.merge_default_interface(default_ipv4, interfaces, 'ipv4')
        self.merge_default_interface(default_ipv6, interfaces, 'ipv6')
        self.facts['interfaces'] = interfaces.keys()

        for iface in interfaces:
            self.facts[iface] = interfaces[iface]

        self.facts['default_ipv4'] = default_ipv4
        self.facts['default_ipv6'] = default_ipv6
        self.facts['all_ipv4_addresses'] = ips['all_ipv4_addresses']
        self.facts['all_ipv6_addresses'] = ips['all_ipv6_addresses']

        return self.facts

    def get_default_interfaces(self, route_path):

        # Use the commands:
        #     route -n get 8.8.8.8                            -> Google public DNS
        #     route -n get -inet6 2404:6800:400a:800::1012    -> ipv6.google.com
        # to find out the default outgoing interface, address, and gateway

        command = dict(
            v4 = [route_path, '-n', 'get', '8.8.8.8'],
            v6 = [route_path, '-n', 'get', '-inet6', '2404:6800:400a:800::1012']
        )

        interface = dict(v4 = {}, v6 = {})

        for v in 'v4', 'v6':

            if v == 'v6' and not socket.has_ipv6:
                continue
            rc, out, err = module.run_command(command[v])
            if not out:
                # v6 routing may result in
                #   RTNETLINK answers: Invalid argument
                continue
            lines = out.split('\n')
            for line in lines:
                words = line.split()
                # Collect output from route command
                if len(words) > 1:
                    if words[0] == 'interface:':
                        interface[v]['interface'] = words[1]
                    if words[0] == 'gateway:':
                        interface[v]['gateway'] = words[1]

        return interface['v4'], interface['v6']

    def get_interfaces_info(self, ifconfig_path):
        interfaces = {}
        current_if = {}
        ips = dict(
            all_ipv4_addresses = [],
            all_ipv6_addresses = [],
        )
        # FreeBSD, DragonflyBSD, NetBSD, OpenBSD and OS X all implicitly add '-a'
        # when running the command 'ifconfig'.
        # Solaris must explicitly run the command 'ifconfig -a'.
        rc, out, err = module.run_command([ifconfig_path, '-a'])

        for line in out.split('\n'):

            if line:
                words = line.split()

                if words[0] == 'pass':
                    continue
                elif re.match('^\S', line) and len(words) > 3:
                    current_if = self.parse_interface_line(words)
                    interfaces[ current_if['device'] ] = current_if
                elif words[0].startswith('options='):
                    self.parse_options_line(words, current_if, ips)
                elif words[0] == 'nd6':
                    self.parse_nd6_line(words, current_if, ips)
                elif words[0] == 'ether':
                    self.parse_ether_line(words, current_if, ips)
                elif words[0] == 'media:':
                    self.parse_media_line(words, current_if, ips)
                elif words[0] == 'status:':
                    self.parse_status_line(words, current_if, ips)
                elif words[0] == 'lladdr':
                    self.parse_lladdr_line(words, current_if, ips)
                elif words[0] == 'inet':
                    self.parse_inet_line(words, current_if, ips)
                elif words[0] == 'inet6':
                    self.parse_inet6_line(words, current_if, ips)
                else:
                    self.parse_unknown_line(words, current_if, ips)

        return interfaces, ips

    def parse_interface_line(self, words):
        device = words[0][0:-1]
        current_if = {'device': device, 'ipv4': [], 'ipv6': [], 'type': 'unknown'}
        current_if['flags']  = self.get_options(words[1])
        current_if['macaddress'] = 'unknown'    # will be overwritten later

        if len(words) >= 5 : # Newer FreeBSD versions
            current_if['metric'] = words[3]
            current_if['mtu'] = words[5]
        else:
            current_if['mtu'] = words[3]

        return current_if

    def parse_options_line(self, words, current_if, ips):
        # Mac has options like this...
        current_if['options'] = self.get_options(words[0])

    def parse_nd6_line(self, words, current_if, ips):
        # FreBSD has options like this...
        current_if['options'] = self.get_options(words[1])

    def parse_ether_line(self, words, current_if, ips):
        current_if['macaddress'] = words[1]

    def parse_media_line(self, words, current_if, ips):
        # not sure if this is useful - we also drop information
        current_if['media'] = words[1]
        if len(words) > 2:
            current_if['media_select'] = words[2]
        if len(words) > 3:
            current_if['media_type'] = words[3][1:]
        if len(words) > 4:
            current_if['media_options'] = self.get_options(words[4])

    def parse_status_line(self, words, current_if, ips):
        current_if['status'] = words[1]

    def parse_lladdr_line(self, words, current_if, ips):
        current_if['lladdr'] = words[1]

    def parse_inet_line(self, words, current_if, ips):
        address = {'address': words[1]}
        # deal with hex netmask
        if re.match('([0-9a-f]){8}', words[3]) and len(words[3]) == 8:
            words[3] = '0x' + words[3]
        if words[3].startswith('0x'):
            address['netmask'] = socket.inet_ntoa(struct.pack('!L', int(words[3], base=16)))
        else:
            # otherwise assume this is a dotted quad
            address['netmask'] = words[3]
        # calculate the network
        address_bin = struct.unpack('!L', socket.inet_aton(address['address']))[0]
        netmask_bin = struct.unpack('!L', socket.inet_aton(address['netmask']))[0]
        address['network'] = socket.inet_ntoa(struct.pack('!L', address_bin & netmask_bin))
        # broadcast may be given or we need to calculate
        if len(words) > 5:
            address['broadcast'] = words[5]
        else:
            address['broadcast'] = socket.inet_ntoa(struct.pack('!L', address_bin | (~netmask_bin & 0xffffffff)))
        # add to our list of addresses
        if not words[1].startswith('127.'):
            ips['all_ipv4_addresses'].append(address['address'])
        current_if['ipv4'].append(address)

    def parse_inet6_line(self, words, current_if, ips):
        address = {'address': words[1]}
        if (len(words) >= 4) and (words[2] == 'prefixlen'):
            address['prefix'] = words[3]
        if (len(words) >= 6) and (words[4] == 'scopeid'):
            address['scope'] = words[5]
        localhost6 = ['::1', '::1/128', 'fe80::1%lo0']
        if address['address'] not in localhost6:
            ips['all_ipv6_addresses'].append(address['address'])
        current_if['ipv6'].append(address)

    def parse_unknown_line(self, words, current_if, ips):
        # we are going to ignore unknown lines here - this may be
        # a bad idea - but you can override it in your subclass
        pass

    def get_options(self, option_string):
        start = option_string.find('<') + 1
        end = option_string.rfind('>')
        if (start > 0) and (end > 0) and (end > start + 1):
            option_csv = option_string[start:end]
            return option_csv.split(',')
        else:
            return []

    def merge_default_interface(self, defaults, interfaces, ip_type):
        if not 'interface' in defaults.keys():
            return
        if not defaults['interface'] in interfaces:
            return
        ifinfo = interfaces[defaults['interface']]
        # copy all the interface values across except addresses
        for item in ifinfo.keys():
            if item != 'ipv4' and item != 'ipv6':
                defaults[item] = ifinfo[item]
        if len(ifinfo[ip_type]) > 0:
            for item in ifinfo[ip_type][0].keys():
                defaults[item] = ifinfo[ip_type][0][item]

class DarwinNetwork(GenericBsdIfconfigNetwork, Network):
    """
    This is the Mac OS X/Darwin Network Class.
    It uses the GenericBsdIfconfigNetwork unchanged
    """
    platform = 'Darwin'

    # media line is different to the default FreeBSD one
    def parse_media_line(self, words, current_if, ips):
        # not sure if this is useful - we also drop information
        current_if['media'] = 'Unknown' # Mac does not give us this
        current_if['media_select'] = words[1]
        if len(words) > 2:
            current_if['media_type'] = words[2][1:]
        if len(words) > 3:
            current_if['media_options'] = self.get_options(words[3])


class FreeBSDNetwork(GenericBsdIfconfigNetwork, Network):
    """
    This is the FreeBSD Network Class.
    It uses the GenericBsdIfconfigNetwork unchanged.
    """
    platform = 'FreeBSD'

class AIXNetwork(GenericBsdIfconfigNetwork, Network):
    """
    This is the AIX Network Class.
    It uses the GenericBsdIfconfigNetwork unchanged.
    """
    platform = 'AIX'

    # AIX 'ifconfig -a' does not have three words in the interface line
    def get_interfaces_info(self, ifconfig_path):
        interfaces = {}
        current_if = {}
        ips = dict(
            all_ipv4_addresses = [],
            all_ipv6_addresses = [],
        )
        rc, out, err = module.run_command([ifconfig_path, '-a'])

        for line in out.split('\n'):

            if line:
                words = line.split()

		# only this condition differs from GenericBsdIfconfigNetwork
                if re.match('^\w*\d*:', line):
                    current_if = self.parse_interface_line(words)
                    interfaces[ current_if['device'] ] = current_if
                elif words[0].startswith('options='):
                    self.parse_options_line(words, current_if, ips)
                elif words[0] == 'nd6':
                    self.parse_nd6_line(words, current_if, ips)
                elif words[0] == 'ether':
                    self.parse_ether_line(words, current_if, ips)
                elif words[0] == 'media:':
                    self.parse_media_line(words, current_if, ips)
                elif words[0] == 'status:':
                    self.parse_status_line(words, current_if, ips)
                elif words[0] == 'lladdr':
                    self.parse_lladdr_line(words, current_if, ips)
                elif words[0] == 'inet':
                    self.parse_inet_line(words, current_if, ips)
                elif words[0] == 'inet6':
                    self.parse_inet6_line(words, current_if, ips)
                else:
                    self.parse_unknown_line(words, current_if, ips)

        return interfaces, ips

    # AIX 'ifconfig -a' does not inform about MTU, so remove current_if['mtu'] here
    def parse_interface_line(self, words):
        device = words[0][0:-1]
        current_if = {'device': device, 'ipv4': [], 'ipv6': [], 'type': 'unknown'}
        current_if['flags'] = self.get_options(words[1])
        current_if['macaddress'] = 'unknown'    # will be overwritten later
        return current_if

class OpenBSDNetwork(GenericBsdIfconfigNetwork, Network):
    """
    This is the OpenBSD Network Class.
    It uses the GenericBsdIfconfigNetwork.
    """
    platform = 'OpenBSD'

    # Return macaddress instead of lladdr
    def parse_lladdr_line(self, words, current_if, ips):
        current_if['macaddress'] = words[1]

class SunOSNetwork(GenericBsdIfconfigNetwork, Network):
    """
    This is the SunOS Network Class.
    It uses the GenericBsdIfconfigNetwork.

    Solaris can have different FLAGS and MTU for IPv4 and IPv6 on the same interface
    so these facts have been moved inside the 'ipv4' and 'ipv6' lists.
    """
    platform = 'SunOS'

    # Solaris 'ifconfig -a' will print interfaces twice, once for IPv4 and again for IPv6.
    # MTU and FLAGS also may differ between IPv4 and IPv6 on the same interface.
    # 'parse_interface_line()' checks for previously seen interfaces before defining
    # 'current_if' so that IPv6 facts don't clobber IPv4 facts (or vice versa).
    def get_interfaces_info(self, ifconfig_path):
        interfaces = {}
        current_if = {}
        ips = dict(
            all_ipv4_addresses = [],
            all_ipv6_addresses = [],
        )
        rc, out, err = module.run_command([ifconfig_path, '-a'])

        for line in out.split('\n'):

            if line:
                words = line.split()

                if re.match('^\S', line) and len(words) > 3:
                    current_if = self.parse_interface_line(words, current_if, interfaces)
                    interfaces[ current_if['device'] ] = current_if
                elif words[0].startswith('options='):
                    self.parse_options_line(words, current_if, ips)
                elif words[0] == 'nd6':
                    self.parse_nd6_line(words, current_if, ips)
                elif words[0] == 'ether':
                    self.parse_ether_line(words, current_if, ips)
                elif words[0] == 'media:':
                    self.parse_media_line(words, current_if, ips)
                elif words[0] == 'status:':
                    self.parse_status_line(words, current_if, ips)
                elif words[0] == 'lladdr':
                    self.parse_lladdr_line(words, current_if, ips)
                elif words[0] == 'inet':
                    self.parse_inet_line(words, current_if, ips)
                elif words[0] == 'inet6':
                    self.parse_inet6_line(words, current_if, ips)
                else:
                    self.parse_unknown_line(words, current_if, ips)

        # 'parse_interface_line' and 'parse_inet*_line' leave two dicts in the
        # ipv4/ipv6 lists which is ugly and hard to read.
        # This quick hack merges the dictionaries. Purely cosmetic.
        for iface in interfaces:
            for v in 'ipv4', 'ipv6':
                combined_facts = {}
                for facts in interfaces[iface][v]:
                    combined_facts.update(facts)
                if len(combined_facts.keys()) > 0:
                    interfaces[iface][v] = [combined_facts]

        return interfaces, ips

    def parse_interface_line(self, words, current_if, interfaces):
        device = words[0][0:-1]
        if device not in interfaces.keys():
            current_if = {'device': device, 'ipv4': [], 'ipv6': [], 'type': 'unknown'}
        else:
            current_if = interfaces[device]
        flags = self.get_options(words[1])
        if 'IPv4' in flags:
            v = 'ipv4'
        if 'IPv6' in flags:
            v = 'ipv6'
        current_if[v].append({'flags': flags, 'mtu': words[3]})
        current_if['macaddress'] = 'unknown'    # will be overwritten later
        return current_if

    # Solaris displays single digit octets in MAC addresses e.g. 0:1:2:d:e:f
    # Add leading zero to each octet where needed.
    def parse_ether_line(self, words, current_if, ips):
        macaddress = ''
        for octet in words[1].split(':'):
            octet = ('0' + octet)[-2:None]
            macaddress += (octet + ':')
        current_if['macaddress'] = macaddress[0:-1]

class Virtual(Facts):
    """
    This is a generic Virtual subclass of Facts.  This should be further
    subclassed to implement per platform.  If you subclass this,
    you should define:
    - virtualization_type
    - virtualization_role
    - container (e.g. solaris zones, freebsd jails, linux containers)

    All subclasses MUST define platform.
    """

    def __new__(cls, *arguments, **keyword):
        subclass = cls
        for sc in Virtual.__subclasses__():
            if sc.platform == platform.system():
                subclass = sc
        return super(cls, subclass).__new__(subclass, *arguments, **keyword)

    def __init__(self):
        Facts.__init__(self)

    def populate(self):
        return self.facts

class LinuxVirtual(Virtual):
    """
    This is a Linux-specific subclass of Virtual.  It defines
    - virtualization_type
    - virtualization_role
    """
    platform = 'Linux'

    def __init__(self):
        Virtual.__init__(self)

    def populate(self):
        self.get_virtual_facts()
        return self.facts

    # For more information, check: http://people.redhat.com/~rjones/virt-what/
    def get_virtual_facts(self):
        if os.path.exists("/proc/xen"):
            self.facts['virtualization_type'] = 'xen'
            self.facts['virtualization_role'] = 'guest'
            try:
                for line in open('/proc/xen/capabilities'):
                    if "control_d" in line:
                        self.facts['virtualization_role'] = 'host'
            except IOError:
                pass
            return

        if os.path.exists('/proc/vz'):
            self.facts['virtualization_type'] = 'openvz'
            if os.path.exists('/proc/bc'):
                self.facts['virtualization_role'] = 'host'
            else:
                self.facts['virtualization_role'] = 'guest'
            return

        if os.path.exists('/proc/1/cgroup'):
            for line in open('/proc/1/cgroup').readlines():
                if re.search('/lxc/', line):
                    self.facts['virtualization_type'] = 'lxc'
                    self.facts['virtualization_role'] = 'guest'
                    return

        product_name = get_file_content('/sys/devices/virtual/dmi/id/product_name')

        if product_name in ['KVM', 'Bochs']:
            self.facts['virtualization_type'] = 'kvm'
            self.facts['virtualization_role'] = 'guest'
            return

        if product_name == 'RHEV Hypervisor':
            self.facts['virtualization_type'] = 'RHEV'
            self.facts['virtualization_role'] = 'guest'
            return

        if product_name == 'VMware Virtual Platform':
            self.facts['virtualization_type'] = 'VMware'
            self.facts['virtualization_role'] = 'guest'
            return

        bios_vendor = get_file_content('/sys/devices/virtual/dmi/id/bios_vendor')

        if bios_vendor == 'Xen':
            self.facts['virtualization_type'] = 'xen'
            self.facts['virtualization_role'] = 'guest'
            return

        if bios_vendor == 'innotek GmbH':
            self.facts['virtualization_type'] = 'virtualbox'
            self.facts['virtualization_role'] = 'guest'
            return

        sys_vendor = get_file_content('/sys/devices/virtual/dmi/id/sys_vendor')

        # FIXME: This does also match hyperv
        if sys_vendor == 'Microsoft Corporation':
            self.facts['virtualization_type'] = 'VirtualPC'
            self.facts['virtualization_role'] = 'guest'
            return

        if sys_vendor == 'Parallels Software International Inc.':
            self.facts['virtualization_type'] = 'parallels'
            self.facts['virtualization_role'] = 'guest'
            return

        if os.path.exists('/proc/self/status'):
            for line in open('/proc/self/status').readlines():
                if re.match('^VxID: \d+', line):
                    self.facts['virtualization_type'] = 'linux_vserver'
                    if re.match('^VxID: 0', line):
                        self.facts['virtualization_role'] = 'host'
                    else:
                        self.facts['virtualization_role'] = 'guest'
                    return

        if os.path.exists('/proc/cpuinfo'):
            for line in open('/proc/cpuinfo').readlines():
                if re.match('^model name.*QEMU Virtual CPU', line):
                    self.facts['virtualization_type'] = 'kvm'
                elif re.match('^vendor_id.*User Mode Linux', line):
                    self.facts['virtualization_type'] = 'uml'
                elif re.match('^model name.*UML', line):
                    self.facts['virtualization_type'] = 'uml'
                elif re.match('^vendor_id.*PowerVM Lx86', line):
                    self.facts['virtualization_type'] = 'powervm_lx86'
                elif re.match('^vendor_id.*IBM/S390', line):
                    self.facts['virtualization_type'] = 'ibm_systemz'
                else:
                    continue
                self.facts['virtualization_role'] = 'guest'
                return

        # Beware that we can have both kvm and virtualbox running on a single system
        if os.path.exists("/proc/modules") and os.access('/proc/modules', os.R_OK):
            modules = []
            for line in open("/proc/modules").readlines():
                data = line.split(" ", 1)
                modules.append(data[0])

            if 'kvm' in modules:
                self.facts['virtualization_type'] = 'kvm'
                self.facts['virtualization_role'] = 'host'
                return

            if 'vboxdrv' in modules:
                self.facts['virtualization_type'] = 'virtualbox'
                self.facts['virtualization_role'] = 'host'
                return

        # If none of the above matches, return 'NA' for virtualization_type
        # and virtualization_role. This allows for proper grouping.
        self.facts['virtualization_type'] = 'NA'
        self.facts['virtualization_role'] = 'NA'
        return


class HPUXVirtual(Virtual):
    """
    This is a HP-UX specific subclass of Virtual. It defines
    - virtualization_type
    - virtualization_role
    """
    platform = 'HP-UX'

    def __init__(self):
        Virtual.__init__(self)

    def populate(self):
        self.get_virtual_facts()
        return self.facts

    def get_virtual_facts(self):
        if os.path.exists('/usr/sbin/vecheck'):
            rc, out, err = module.run_command("/usr/sbin/vecheck")
            if rc == 0:
                self.facts['virtualization_type'] = 'guest'
                self.facts['virtualization_role'] = 'HP vPar'
        if os.path.exists('/opt/hpvm/bin/hpvminfo'):
            rc, out, err = module.run_command("/opt/hpvm/bin/hpvminfo")
            if rc == 0 and re.match('.*Running.*HPVM vPar.*', out):
                self.facts['virtualization_type'] = 'guest'
                self.facts['virtualization_role'] = 'HPVM vPar'
            elif rc == 0 and re.match('.*Running.*HPVM guest.*', out):
                self.facts['virtualization_type'] = 'guest'
                self.facts['virtualization_role'] = 'HPVM IVM'
            elif rc == 0 and re.match('.*Running.*HPVM host.*', out):
                self.facts['virtualization_type'] = 'host'
                self.facts['virtualization_role'] = 'HPVM'
        if os.path.exists('/usr/sbin/parstatus'):
            rc, out, err = module.run_command("/usr/sbin/parstatus")
            if rc == 0:
                self.facts['virtualization_type'] = 'guest'
                self.facts['virtualization_role'] = 'HP nPar'


class SunOSVirtual(Virtual):
    """
    This is a SunOS-specific subclass of Virtual.  It defines
    - virtualization_type
    - virtualization_role
    - container
    """
    platform = 'SunOS'

    def __init__(self):
        Virtual.__init__(self)

    def populate(self):
        self.get_virtual_facts()
        return self.facts

    def get_virtual_facts(self):
        rc, out, err = module.run_command("/usr/sbin/prtdiag")
        for line in out.split('\n'):
            if 'VMware' in line:
                self.facts['virtualization_type'] = 'vmware'
                self.facts['virtualization_role'] = 'guest'
            if 'Parallels' in line:
                self.facts['virtualization_type'] = 'parallels'
                self.facts['virtualization_role'] = 'guest'
            if 'VirtualBox' in line:
                self.facts['virtualization_type'] = 'virtualbox'
                self.facts['virtualization_role'] = 'guest'
            if 'HVM domU' in line:
                self.facts['virtualization_type'] = 'xen'
                self.facts['virtualization_role'] = 'guest'
        # Check if it's a zone
        if os.path.exists("/usr/bin/zonename"):
            rc, out, err = module.run_command("/usr/bin/zonename")
            if out.rstrip() != "global":
                self.facts['container'] = 'zone'
        # Check if it's a branded zone (i.e. Solaris 8/9 zone)
        if os.path.isdir('/.SUNWnative'):
            self.facts['container'] = 'zone'
        # If it's a zone check if we can detect if our global zone is itself virtualized.
        # Relies on the "guest tools" (e.g. vmware tools) to be installed
        if 'container' in self.facts and self.facts['container'] == 'zone':
            rc, out, err = module.run_command("/usr/sbin/modinfo")
            for line in out.split('\n'):
                if 'VMware' in line:
                    self.facts['virtualization_type'] = 'vmware'
                    self.facts['virtualization_role'] = 'guest'
                if 'VirtualBox' in line:
                    self.facts['virtualization_type'] = 'virtualbox'
                    self.facts['virtualization_role'] = 'guest'

def get_file_content(path, default=None):
    data = default
    if os.path.exists(path) and os.access(path, os.R_OK):
        data = open(path).read().strip()
        if len(data) == 0:
            data = default
    return data

def ansible_facts(module):
    facts = {}
    facts.update(Facts().populate())
    facts.update(Hardware().populate())
    facts.update(Network(module).populate())
    facts.update(Virtual().populate())
    return facts

# ===========================================

def get_all_facts(module):

    setup_options = dict(module_setup=True)
    facts = ansible_facts(module)

    for (k, v) in facts.items():
        setup_options["ansible_%s" % k.replace('-', '_')] = v

    # Look for the path to the facter and ohai binary and set
    # the variable to that path.

    facter_path = module.get_bin_path('facter')
    ohai_path = module.get_bin_path('ohai')

    # if facter is installed, and we can use --json because
    # ruby-json is ALSO installed, include facter data in the JSON

    if facter_path is not None:
        rc, out, err = module.run_command(facter_path + " --json")
        facter = True
        try:
            facter_ds = json.loads(out)
        except:
            facter = False
        if facter:
            for (k,v) in facter_ds.items():
                setup_options["facter_%s" % k] = v

    # ditto for ohai

    if ohai_path is not None:
        rc, out, err = module.run_command(ohai_path)
        ohai = True
        try:
            ohai_ds = json.loads(out)
        except:
            ohai = False
        if ohai:
            for (k,v) in ohai_ds.items():
                k2 = "ohai_%s" % k.replace('-', '_')
                setup_options[k2] = v

    setup_result = { 'ansible_facts': {} }

    for (k,v) in setup_options.items():
        if module.params['filter'] == '*' or fnmatch.fnmatch(k, module.params['filter']):
            setup_result['ansible_facts'][k] = v

    # hack to keep --verbose from showing all the setup module results
    setup_result['verbose_override'] = True

    return setup_result


########NEW FILE########
__FILENAME__ = gce
# This code is part of Ansible, but is an independent component.
# This particular file snippet, and this file snippet only, is BSD licensed.
# Modules you write using this snippet, which is embedded dynamically by Ansible
# still belong to the author of the module, and may assign their own license
# to the complete work.
#
# Copyright (c), Franck Cuny <franck.cuny@gmail.com>, 2014
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#
#    * Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#    * Redistributions in binary form must reproduce the above copyright notice,
#      this list of conditions and the following disclaimer in the documentation
#      and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
# IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE
# USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#

USER_AGENT_PRODUCT="Ansible-gce"
USER_AGENT_VERSION="v1"

def gce_connect(module):
    """Return a Google Cloud Engine connection."""
    service_account_email = module.params.get('service_account_email', None)
    pem_file = module.params.get('pem_file', None)
    project_id = module.params.get('project_id', None)

    if service_account_email is None or pem_file is None:
        # Load in the libcloud secrets file
        try:
            import secrets
        except ImportError:
            secrets = None

        service_account_email, pem_file = getattr(secrets, 'GCE_PARAMS', (None, None))
        keyword_params = getattr(secrets, 'GCE_KEYWORD_PARAMS', {})
        project_id = keyword_params.get('project', None)

    if service_account_email is None or pem_file is None or project_id is None:
        module.fail_json(msg='Missing GCE connection parameters in libcloud secrets file.')
        return None

    try:
        gce = get_driver(Provider.GCE)(service_account_email, pem_file, datacenter=module.params.get('zone'), project=project_id)
        gce.connection.user_agent_append("%s/%s" % (
            USER_AGENT_PRODUCT, USER_AGENT_VERSION))
    except (RuntimeError, ValueError), e:
        module.fail_json(msg=str(e), changed=False)
    except Exception, e:
        module.fail_json(msg=unexpected_error_msg(e), changed=False)

    return gce

def unexpected_error_msg(error):
    """Create an error string based on passed in error."""
    msg='Unexpected response: HTTP return_code['
    msg+='%s], API error code[%s] and message: %s' % (
        error.http_code, error.code, str(error.value))
    return msg

########NEW FILE########
__FILENAME__ = known_hosts
# This code is part of Ansible, but is an independent component.
# This particular file snippet, and this file snippet only, is BSD licensed.
# Modules you write using this snippet, which is embedded dynamically by Ansible
# still belong to the author of the module, and may assign their own license
# to the complete work.
#
# Copyright (c), Michael DeHaan <michael.dehaan@gmail.com>, 2012-2013
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#
#    * Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#    * Redistributions in binary form must reproduce the above copyright notice,
#      this list of conditions and the following disclaimer in the documentation
#      and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
# IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE
# USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import hmac

try:
    from hashlib import sha1
except ImportError:
    import sha as sha1

HASHED_KEY_MAGIC = "|1|"

def add_git_host_key(module, url, accept_hostkey=True, create_dir=True):

    """ idempotently add a git url hostkey """

    fqdn = get_fqdn(module.params['repo'])

    if fqdn:
        known_host = check_hostkey(module, fqdn)
        if not known_host:
            if accept_hostkey:
                rc, out, err = add_host_key(module, fqdn, create_dir=create_dir)
                if rc != 0:
                    module.fail_json(msg="failed to add %s hostkey: %s" % (fqdn, out + err))
            else:
                module.fail_json(msg="%s has an unknown hostkey. Set accept_hostkey to True or manually add the hostkey prior to running the git module" % fqdn)                    

def get_fqdn(repo_url):

    """ chop the hostname out of a giturl """

    result = None
    if "@" in repo_url and not repo_url.startswith("http"):
        repo_url = repo_url.split("@", 1)[1]
        if ":" in repo_url:
            repo_url = repo_url.split(":")[0]
            result = repo_url
        elif "/" in repo_url:
            repo_url = repo_url.split("/")[0]
            result = repo_url

    return result

def check_hostkey(module, fqdn):
   return not not_in_host_file(module, fqdn)

# this is a variant of code found in connection_plugins/paramiko.py and we should modify
# the paramiko code to import and use this.

def not_in_host_file(self, host):


    if 'USER' in os.environ:
        user_host_file = os.path.expandvars("~${USER}/.ssh/known_hosts")
    else:
        user_host_file = "~/.ssh/known_hosts"
    user_host_file = os.path.expanduser(user_host_file)

    host_file_list = []
    host_file_list.append(user_host_file)
    host_file_list.append("/etc/ssh/ssh_known_hosts")
    host_file_list.append("/etc/ssh/ssh_known_hosts2")

    hfiles_not_found = 0
    for hf in host_file_list:
        if not os.path.exists(hf):
            hfiles_not_found += 1
            continue

        try:
            host_fh = open(hf)
        except IOError, e:
            hfiles_not_found += 1
            continue
        else:
            data = host_fh.read()
            host_fh.close()

        for line in data.split("\n"):
            if line is None or " " not in line:
                continue
            tokens = line.split()
            if tokens[0].find(HASHED_KEY_MAGIC) == 0:
                # this is a hashed known host entry
                try:
                    (kn_salt,kn_host) = tokens[0][len(HASHED_KEY_MAGIC):].split("|",2)
                    hash = hmac.new(kn_salt.decode('base64'), digestmod=sha1)
                    hash.update(host)
                    if hash.digest() == kn_host.decode('base64'):
                        return False
                except:
                    # invalid hashed host key, skip it
                    continue
            else:
                # standard host file entry
                if host in tokens[0]:
                    return False

    return True


def add_host_key(module, fqdn, key_type="rsa", create_dir=False):

    """ use ssh-keyscan to add the hostkey """

    result = False
    keyscan_cmd = module.get_bin_path('ssh-keyscan', True)

    if 'USER' in os.environ:
        user_ssh_dir = os.path.expandvars("~${USER}/.ssh/")
        user_host_file = os.path.expandvars("~${USER}/.ssh/known_hosts")
    else:
        user_ssh_dir = "~/.ssh/"
        user_host_file = "~/.ssh/known_hosts"
    user_ssh_dir = os.path.expanduser(user_ssh_dir)

    if not os.path.exists(user_ssh_dir):
        if create_dir:
            try:
                os.makedirs(user_ssh_dir, 0700)
            except:
                module.fail_json(msg="failed to create host key directory: %s" % user_ssh_dir)
        else:
            module.fail_json(msg="%s does not exist" % user_ssh_dir)
    elif not os.path.isdir(user_ssh_dir):
        module.fail_json(msg="%s is not a directory" % user_ssh_dir)

    this_cmd = "%s -t %s %s" % (keyscan_cmd, key_type, fqdn)

    rc, out, err = module.run_command(this_cmd)
    module.append_to_file(user_host_file, out)

    return rc, out, err


########NEW FILE########
__FILENAME__ = rax
# This code is part of Ansible, but is an independent component.
# This particular file snippet, and this file snippet only, is BSD licensed.
# Modules you write using this snippet, which is embedded dynamically by Ansible
# still belong to the author of the module, and may assign their own license
# to the complete work.
#
# Copyright (c), Michael DeHaan <michael.dehaan@gmail.com>, 2012-2013
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#
#    * Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#    * Redistributions in binary form must reproduce the above copyright notice,
#      this list of conditions and the following disclaimer in the documentation
#      and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
# IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE
# USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import os

def rax_argument_spec():
    return dict(
        api_key=dict(type='str', aliases=['password'], no_log=True),
        auth_endpoint=dict(type='str'),
        credentials=dict(type='str', aliases=['creds_file']),
        env=dict(type='str'),
        identity_type=dict(type='str', default='rackspace'),
        region=dict(type='str'),
        tenant_id=dict(type='str'),
        tenant_name=dict(type='str'),
        username=dict(type='str'),
        verify_ssl=dict(choices=BOOLEANS, type='bool'),
    )


def rax_required_together():
    return [['api_key', 'username']]


def setup_rax_module(module, rax_module):
    api_key = module.params.get('api_key')
    auth_endpoint = module.params.get('auth_endpoint')
    credentials = module.params.get('credentials')
    env = module.params.get('env')
    identity_type = module.params.get('identity_type')
    region = module.params.get('region')
    tenant_id = module.params.get('tenant_id')
    tenant_name = module.params.get('tenant_name')
    username = module.params.get('username')
    verify_ssl = module.params.get('verify_ssl')

    if env is not None:
        rax_module.set_environment(env)

    rax_module.set_setting('identity_type', identity_type)
    if verify_ssl is not None:
        rax_module.set_setting('verify_ssl', verify_ssl)
    if auth_endpoint is not None:
        rax_module.set_setting('auth_endpoint', auth_endpoint)
    if tenant_id is not None:
        rax_module.set_setting('tenant_id', tenant_id)
    if tenant_name is not None:
        rax_module.set_setting('tenant_name', tenant_name)

    try:
        username = username or os.environ.get('RAX_USERNAME')
        if not username:
            username = rax_module.get_setting('keyring_username')
            if username:
                api_key = 'USE_KEYRING'
        if not api_key:
            api_key = os.environ.get('RAX_API_KEY')
        credentials = (credentials or os.environ.get('RAX_CREDENTIALS') or
                       os.environ.get('RAX_CREDS_FILE'))
        region = (region or os.environ.get('RAX_REGION') or
                  rax_module.get_setting('region'))
    except KeyError, e:
        module.fail_json(msg='Unable to load %s' % e.message)

    try:
        if api_key and username:
            if api_key == 'USE_KEYRING':
                rax_module.keyring_auth(username, region=region)
            else:
                rax_module.set_credentials(username, api_key=api_key,
                                           region=region)
        elif credentials:
            credentials = os.path.expanduser(credentials)
            rax_module.set_credential_file(credentials, region=region)
        else:
            raise Exception('No credentials supplied!')
    except Exception, e:
        module.fail_json(msg='%s' % e.message)

    return rax_module

########NEW FILE########
__FILENAME__ = redhat
# This code is part of Ansible, but is an independent component.
# This particular file snippet, and this file snippet only, is BSD licensed.
# Modules you write using this snippet, which is embedded dynamically by Ansible
# still belong to the author of the module, and may assign their own license
# to the complete work.
#
# Copyright (c), James Laska
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#
#    * Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#    * Redistributions in binary form must reproduce the above copyright notice,
#      this list of conditions and the following disclaimer in the documentation
#      and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
# IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE
# USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import os
import re
import types
import ConfigParser
import shlex


class RegistrationBase(object):
    def __init__(self, module, username=None, password=None):
        self.module = module
        self.username = username
        self.password = password

    def configure(self):
        raise NotImplementedError("Must be implemented by a sub-class")

    def enable(self):
        # Remove any existing redhat.repo
        redhat_repo = '/etc/yum.repos.d/redhat.repo'
        if os.path.isfile(redhat_repo):
            os.unlink(redhat_repo)

    def register(self):
        raise NotImplementedError("Must be implemented by a sub-class")

    def unregister(self):
        raise NotImplementedError("Must be implemented by a sub-class")

    def unsubscribe(self):
        raise NotImplementedError("Must be implemented by a sub-class")

    def update_plugin_conf(self, plugin, enabled=True):
        plugin_conf = '/etc/yum/pluginconf.d/%s.conf' % plugin
        if os.path.isfile(plugin_conf):
            cfg = ConfigParser.ConfigParser()
            cfg.read([plugin_conf])
            if enabled:
                cfg.set('main', 'enabled', 1)
            else:
                cfg.set('main', 'enabled', 0)
            fd = open(plugin_conf, 'rwa+')
            cfg.write(fd)
            fd.close()

    def subscribe(self, **kwargs):
        raise NotImplementedError("Must be implemented by a sub-class")


class Rhsm(RegistrationBase):
    def __init__(self, module, username=None, password=None):
        RegistrationBase.__init__(self, module, username, password)
        self.config = self._read_config()
        self.module = module

    def _read_config(self, rhsm_conf='/etc/rhsm/rhsm.conf'):
        '''
            Load RHSM configuration from /etc/rhsm/rhsm.conf.
            Returns:
             * ConfigParser object
        '''

        # Read RHSM defaults ...
        cp = ConfigParser.ConfigParser()
        cp.read(rhsm_conf)

        # Add support for specifying a default value w/o having to standup some configuration
        # Yeah, I know this should be subclassed ... but, oh well
        def get_option_default(self, key, default=''):
            sect, opt = key.split('.', 1)
            if self.has_section(sect) and self.has_option(sect, opt):
                return self.get(sect, opt)
            else:
                return default

        cp.get_option = types.MethodType(get_option_default, cp, ConfigParser.ConfigParser)

        return cp

    def enable(self):
        '''
            Enable the system to receive updates from subscription-manager.
            This involves updating affected yum plugins and removing any
            conflicting yum repositories.
        '''
        RegistrationBase.enable(self)
        self.update_plugin_conf('rhnplugin', False)
        self.update_plugin_conf('subscription-manager', True)

    def configure(self, **kwargs):
        '''
            Configure the system as directed for registration with RHN
            Raises:
              * Exception - if error occurs while running command
        '''
        args = ['subscription-manager', 'config']

        # Pass supplied **kwargs as parameters to subscription-manager.  Ignore
        # non-configuration parameters and replace '_' with '.'.  For example,
        # 'server_hostname' becomes '--system.hostname'.
        for k,v in kwargs.items():
            if re.search(r'^(system|rhsm)_', k):
                args.append('--%s=%s' % (k.replace('_','.'), v))
        
        self.module.run_command(args, check_rc=True)

    @property
    def is_registered(self):
        '''
            Determine whether the current system
            Returns:
              * Boolean - whether the current system is currently registered to
                          RHN.
        '''
        # Quick version...
        if False:
            return os.path.isfile('/etc/pki/consumer/cert.pem') and \
                   os.path.isfile('/etc/pki/consumer/key.pem')

        args = ['subscription-manager', 'identity']
        rc, stdout, stderr = self.module.run_command(args, check_rc=False)
        if rc == 0:
            return True
        else:
            return False

    def register(self, username, password, autosubscribe, activationkey):
        '''
            Register the current system to the provided RHN server
            Raises:
              * Exception - if error occurs while running command
        '''
        args = ['subscription-manager', 'register']

        # Generate command arguments
        if activationkey:
            args.append('--activationkey "%s"' % activationkey)
        else:
            if autosubscribe:
                args.append('--autosubscribe')
            if username:
                args.extend(['--username', username])
            if password:
                args.extend(['--password', password])

        # Do the needful...
        rc, stderr, stdout = self.module.run_command(args, check_rc=True)

    def unsubscribe(self):
        '''
            Unsubscribe a system from all subscribed channels
            Raises:
              * Exception - if error occurs while running command
        '''
        args = ['subscription-manager', 'unsubscribe', '--all']
        rc, stderr, stdout = self.module.run_command(args, check_rc=True)

    def unregister(self):
        '''
            Unregister a currently registered system
            Raises:
              * Exception - if error occurs while running command
        '''
        args = ['subscription-manager', 'unregister']
        rc, stderr, stdout = self.module.run_command(args, check_rc=True)

    def subscribe(self, regexp):
        '''
            Subscribe current system to available pools matching the specified
            regular expression
            Raises:
              * Exception - if error occurs while running command
        '''

        # Available pools ready for subscription
        available_pools = RhsmPools(self.module)

        for pool in available_pools.filter(regexp):
            pool.subscribe()


class RhsmPool(object):
    '''
        Convenience class for housing subscription information
    '''

    def __init__(self, module, **kwargs):
        self.module = module
        for k,v in kwargs.items():
            setattr(self, k, v)

    def __str__(self):
        return str(self.__getattribute__('_name'))

    def subscribe(self):
        args = "subscription-manager subscribe --pool %s" % self.PoolId
        rc, stdout, stderr = self.module.run_command(args, check_rc=True)
        if rc == 0:
            return True
        else:
            return False


class RhsmPools(object):
    """
        This class is used for manipulating pools subscriptions with RHSM
    """
    def __init__(self, module):
        self.module = module
        self.products = self._load_product_list()

    def __iter__(self):
        return self.products.__iter__()

    def _load_product_list(self):
        """
            Loads list of all availaible pools for system in data structure
        """
        args = "subscription-manager list --available"
        rc, stdout, stderr = self.module.run_command(args, check_rc=True)

        products = []
        for line in stdout.split('\n'):
            # Remove leading+trailing whitespace
            line = line.strip()
            # An empty line implies the end of a output group
            if len(line) == 0:
                continue
            # If a colon ':' is found, parse
            elif ':' in line:
                (key, value) = line.split(':',1)
                key = key.strip().replace(" ", "")  # To unify
                value = value.strip()
                if key in ['ProductName', 'SubscriptionName']:
                    # Remember the name for later processing
                    products.append(RhsmPool(self.module, _name=value, key=value))
                elif products:
                    # Associate value with most recently recorded product
                    products[-1].__setattr__(key, value)
                # FIXME - log some warning?
                #else:
                    # warnings.warn("Unhandled subscription key/value: %s/%s" % (key,value))
        return products

    def filter(self, regexp='^$'):
        '''
            Return a list of RhsmPools whose name matches the provided regular expression
        '''
        r = re.compile(regexp)
        for product in self.products:
            if r.search(product._name):
                yield product


########NEW FILE########
__FILENAME__ = urls
# This code is part of Ansible, but is an independent component.
# This particular file snippet, and this file snippet only, is BSD licensed.
# Modules you write using this snippet, which is embedded dynamically by Ansible
# still belong to the author of the module, and may assign their own license
# to the complete work.
#
# Copyright (c), Michael DeHaan <michael.dehaan@gmail.com>, 2012-2013
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#
#    * Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#    * Redistributions in binary form must reproduce the above copyright notice,
#      this list of conditions and the following disclaimer in the documentation
#      and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
# IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE
# USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

try:
    import urllib
    HAS_URLLIB = True
except:
    HAS_URLLIB = False

try:
    import urllib2
    HAS_URLLIB2 = True
except:
    HAS_URLLIB2 = False

try:
    import urlparse
    HAS_URLPARSE = True
except:
    HAS_URLPARSE = False

try:
    import ssl
    HAS_SSL=True
except:
    HAS_SSL=False

import os
import re
import socket
import tempfile


# This is a dummy cacert provided for Mac OS since you need at least 1
# ca cert, regardless of validity, for Python on Mac OS to use the
# keychain functionality in OpenSSL for validating SSL certificates.
# See: http://mercurial.selenic.com/wiki/CACertificates#Mac_OS_X_10.6_and_higher
DUMMY_CA_CERT = """-----BEGIN CERTIFICATE-----
MIICvDCCAiWgAwIBAgIJAO8E12S7/qEpMA0GCSqGSIb3DQEBBQUAMEkxCzAJBgNV
BAYTAlVTMRcwFQYDVQQIEw5Ob3J0aCBDYXJvbGluYTEPMA0GA1UEBxMGRHVyaGFt
MRAwDgYDVQQKEwdBbnNpYmxlMB4XDTE0MDMxODIyMDAyMloXDTI0MDMxNTIyMDAy
MlowSTELMAkGA1UEBhMCVVMxFzAVBgNVBAgTDk5vcnRoIENhcm9saW5hMQ8wDQYD
VQQHEwZEdXJoYW0xEDAOBgNVBAoTB0Fuc2libGUwgZ8wDQYJKoZIhvcNAQEBBQAD
gY0AMIGJAoGBANtvpPq3IlNlRbCHhZAcP6WCzhc5RbsDqyh1zrkmLi0GwcQ3z/r9
gaWfQBYhHpobK2Tiq11TfraHeNB3/VfNImjZcGpN8Fl3MWwu7LfVkJy3gNNnxkA1
4Go0/LmIvRFHhbzgfuo9NFgjPmmab9eqXJceqZIlz2C8xA7EeG7ku0+vAgMBAAGj
gaswgagwHQYDVR0OBBYEFPnN1nPRqNDXGlCqCvdZchRNi/FaMHkGA1UdIwRyMHCA
FPnN1nPRqNDXGlCqCvdZchRNi/FaoU2kSzBJMQswCQYDVQQGEwJVUzEXMBUGA1UE
CBMOTm9ydGggQ2Fyb2xpbmExDzANBgNVBAcTBkR1cmhhbTEQMA4GA1UEChMHQW5z
aWJsZYIJAO8E12S7/qEpMAwGA1UdEwQFMAMBAf8wDQYJKoZIhvcNAQEFBQADgYEA
MUB80IR6knq9K/tY+hvPsZer6eFMzO3JGkRFBh2kn6JdMDnhYGX7AXVHGflrwNQH
qFy+aenWXsC0ZvrikFxbQnX8GVtDADtVznxOi7XzFw7JOxdsVrpXgSN0eh0aMzvV
zKPZsZ2miVGclicJHzm5q080b1p/sZtuKIEZk6vZqEg=
-----END CERTIFICATE-----
"""

def generic_urlparse(parts):
    '''
    Returns a dictionary of url parts as parsed by urlparse,
    but accounts for the fact that older versions of that
    library do not support named attributes (ie. .netloc)
    '''
    generic_parts = dict()
    if hasattr(parts, 'netloc'):
        # urlparse is newer, just read the fields straight
        # from the parts object
        generic_parts['scheme']   = parts.scheme
        generic_parts['netloc']   = parts.netloc
        generic_parts['path']     = parts.path
        generic_parts['params']   = parts.params
        generic_parts['query']    = parts.query
        generic_parts['fragment'] = parts.fragment
        generic_parts['username'] = parts.username
        generic_parts['password'] = parts.password
        generic_parts['hostname'] = parts.hostname
        generic_parts['port']     = parts.port
    else:
        # we have to use indexes, and then parse out
        # the other parts not supported by indexing
        generic_parts['scheme']   = parts[0]
        generic_parts['netloc']   = parts[1]
        generic_parts['path']     = parts[2]
        generic_parts['params']   = parts[3]
        generic_parts['query']    = parts[4]
        generic_parts['fragment'] = parts[5]
        # get the username, password, etc.
        try:
            netloc_re = re.compile(r'^((?:\w)+(?::(?:\w)+)?@)?([A-Za-z0-9.-]+)(:\d+)?$')
            (auth, hostname, port) = netloc_re.match(parts[1])
            if port:
                # the capture group for the port will include the ':',
                # so remove it and convert the port to an integer
                port = int(port[1:])
            if auth:
                # the capture group above inclues the @, so remove it
                # and then split it up based on the first ':' found
                auth = auth[:-1]
                username, password = auth.split(':', 1)
            generic_parts['username'] = username
            generic_parts['password'] = password
            generic_parts['hostname'] = hostnme
            generic_parts['port']     = port
        except:
            generic_parts['username'] = None
            generic_parts['password'] = None
            generic_parts['hostname'] = None
            generic_parts['port']     = None
    return generic_parts

class RequestWithMethod(urllib2.Request):
    '''
    Workaround for using DELETE/PUT/etc with urllib2
    Originally contained in library/net_infrastructure/dnsmadeeasy
    '''

    def __init__(self, url, method, data=None, headers={}):
        self._method = method
        urllib2.Request.__init__(self, url, data, headers)

    def get_method(self):
        if self._method:
            return self._method
        else:
            return urllib2.Request.get_method(self)


class SSLValidationHandler(urllib2.BaseHandler):
    '''
    A custom handler class for SSL validation.

    Based on:
    http://stackoverflow.com/questions/1087227/validate-ssl-certificates-with-python
    http://techknack.net/python-urllib2-handlers/
    '''
    CONNECT_COMMAND = "CONNECT %s:%s HTTP/1.0\r\nConnection: close\r\n"

    def __init__(self, module, hostname, port):
        self.module = module
        self.hostname = hostname
        self.port = port

    def get_ca_certs(self):
        # tries to find a valid CA cert in one of the
        # standard locations for the current distribution

        ca_certs = []
        paths_checked = []
        platform = get_platform()
        distribution = get_distribution()

        # build a list of paths to check for .crt/.pem files
        # based on the platform type
        paths_checked.append('/etc/ssl/certs')
        if platform == 'Linux':
            paths_checked.append('/etc/pki/ca-trust/extracted/pem')
            paths_checked.append('/etc/pki/tls/certs')
            paths_checked.append('/usr/share/ca-certificates/cacert.org')
        elif platform == 'FreeBSD':
            paths_checked.append('/usr/local/share/certs')
        elif platform == 'OpenBSD':
            paths_checked.append('/etc/ssl')
        elif platform == 'NetBSD':
            ca_certs.append('/etc/openssl/certs')

        # fall back to a user-deployed cert in a standard
        # location if the OS platform one is not available
        paths_checked.append('/etc/ansible')

        tmp_fd, tmp_path = tempfile.mkstemp()

        # Write the dummy ca cert if we are running on Mac OS X
        if platform == 'Darwin':
            os.write(tmp_fd, DUMMY_CA_CERT)

        # for all of the paths, find any  .crt or .pem files
        # and compile them into single temp file for use
        # in the ssl check to speed up the test
        for path in paths_checked:
            if os.path.exists(path) and os.path.isdir(path):
                dir_contents = os.listdir(path)
                for f in dir_contents:
                    full_path = os.path.join(path, f)
                    if os.path.isfile(full_path) and os.path.splitext(f)[1] in ('.crt','.pem'):
                        try:
                            cert_file = open(full_path, 'r')
                            os.write(tmp_fd, cert_file.read())
                            os.write(tmp_fd, '\n')
                            cert_file.close()
                        except:
                            pass

        return (tmp_path, paths_checked)

    def validate_proxy_response(self, response, valid_codes=[200]):
        '''
        make sure we get back a valid code from the proxy
        '''
        try:
            (http_version, resp_code, msg) = re.match(r'(HTTP/\d\.\d) (\d\d\d) (.*)', response).groups()
            if int(resp_code) not in valid_codes:
                raise Exception
        except:
            self.module.fail_json(msg='Connection to proxy failed')

    def http_request(self, req):
        tmp_ca_cert_path, paths_checked = self.get_ca_certs()
        https_proxy = os.environ.get('https_proxy')
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            if https_proxy:
                proxy_parts = generic_urlparse(urlparse.urlparse(https_proxy))
                s.connect((proxy_parts.get('hostname'), proxy_parts.get('port')))
                if proxy_parts.get('scheme') == 'http':
                    s.sendall(self.CONNECT_COMMAND % (self.hostname, self.port))
                    if proxy_parts.get('username'):
                        credentials = "%s:%s" % (proxy_parts.get('username',''), proxy_parts.get('password',''))
                        s.sendall('Proxy-Authorization: Basic %s\r\n' % credentials.encode('base64').strip())
                    s.sendall('\r\n')
                    connect_result = s.recv(4096)
                    self.validate_proxy_response(connect_result)
                    ssl_s = ssl.wrap_socket(s, ca_certs=tmp_ca_cert_path, cert_reqs=ssl.CERT_REQUIRED)
                else:
                    self.module.fail_json(msg='Unsupported proxy scheme: %s. Currently ansible only supports HTTP proxies.' % proxy_parts.get('scheme'))
            else:
                s.connect((self.hostname, self.port))
                ssl_s = ssl.wrap_socket(s, ca_certs=tmp_ca_cert_path, cert_reqs=ssl.CERT_REQUIRED)
            # close the ssl connection
            #ssl_s.unwrap()
            s.close()
        except (ssl.SSLError, socket.error), e:
            # fail if we tried all of the certs but none worked
            if 'connection refused' in str(e).lower():
                self.module.fail_json(msg='Failed to connect to %s:%s.' % (self.hostname, self.port))
            else:
                self.module.fail_json(
                    msg='Failed to validate the SSL certificate for %s:%s. ' % (self.hostname, self.port) + \
                    'Use validate_certs=no or make sure your managed systems have a valid CA certificate installed. ' + \
                    'Paths checked for this platform: %s' % ", ".join(paths_checked)
                )
        try:
            # cleanup the temp file created, don't worry
            # if it fails for some reason
            os.remove(tmp_ca_cert_path)
        except:
            pass

        return req

    https_request = http_request


def url_argument_spec():
    '''
    Creates an argument spec that can be used with any module
    that will be requesting content via urllib/urllib2
    '''
    return dict(
        url = dict(),
        force = dict(default='no', aliases=['thirsty'], type='bool'),
        http_agent = dict(default='ansible-httpget'),
        use_proxy = dict(default='yes', type='bool'),
        validate_certs = dict(default='yes', type='bool'),
        url_username = dict(required=False),
        url_password = dict(required=False),
    )


def fetch_url(module, url, data=None, headers=None, method=None, 
              use_proxy=True, force=False, last_mod_time=None, timeout=10):
    '''
    Fetches a file from an HTTP/FTP server using urllib2
    '''

    if not HAS_URLLIB:
        module.fail_json(msg='urllib is not installed')
    if not HAS_URLLIB2:
        module.fail_json(msg='urllib2 is not installed')
    elif not HAS_URLPARSE:
        module.fail_json(msg='urlparse is not installed')

    r = None
    handlers = []
    info = dict(url=url)

    distribution = get_distribution()
    # Get validate_certs from the module params
    validate_certs = module.params.get('validate_certs', True)

    # FIXME: change the following to use the generic_urlparse function
    #        to remove the indexed references for 'parsed'
    parsed = urlparse.urlparse(url)
    if parsed[0] == 'https':
        if not HAS_SSL and validate_certs:
            if distribution == 'Redhat':
                module.fail_json(msg='SSL validation is not available in your version of python. You can use validate_certs=no, however this is unsafe and not recommended. You can also install python-ssl from EPEL')
            else:
                module.fail_json(msg='SSL validation is not available in your version of python. You can use validate_certs=no, however this is unsafe and not recommended')

        elif validate_certs:
            # do the cert validation
            netloc = parsed[1]
            if '@' in netloc:
                netloc = netloc.split('@', 1)[1]
            if ':' in netloc:
                hostname, port = netloc.split(':', 1)
            else:
                hostname = netloc
                port = 443
            # create the SSL validation handler and
            # add it to the list of handlers
            ssl_handler = SSLValidationHandler(module, hostname, port)
            handlers.append(ssl_handler)

    if parsed[0] != 'ftp':
        username = module.params.get('url_username', '')
        if username:
            password = module.params.get('url_password', '')
            netloc = parsed[1]
        elif '@' in parsed[1]:
            credentials, netloc = parsed[1].split('@', 1)
            if ':' in credentials:
                username, password = credentials.split(':', 1)
            else:
                username = credentials
                password = ''

            parsed = list(parsed)
            parsed[1] = netloc

            # reconstruct url without credentials
            url = urlparse.urlunparse(parsed)

        if username:
            passman = urllib2.HTTPPasswordMgrWithDefaultRealm()

            # this creates a password manager
            passman.add_password(None, netloc, username, password)

            # because we have put None at the start it will always
            # use this username/password combination for  urls
            # for which `theurl` is a super-url
            authhandler = urllib2.HTTPBasicAuthHandler(passman)

            # create the AuthHandler
            handlers.append(authhandler)

    if not use_proxy:
        proxyhandler = urllib2.ProxyHandler({})
        handlers.append(proxyhandler)

    opener = urllib2.build_opener(*handlers)
    urllib2.install_opener(opener)

    if method:
        if method.upper() not in ('OPTIONS','GET','HEAD','POST','PUT','DELETE','TRACE','CONNECT'):
            module.fail_json(msg='invalid HTTP request method; %s' % method.upper())
        request = RequestWithMethod(url, method.upper(), data)
    else:
        request = urllib2.Request(url, data)

    # add the custom agent header, to help prevent issues 
    # with sites that block the default urllib agent string 
    request.add_header('User-agent', module.params.get('http_agent'))

    # if we're ok with getting a 304, set the timestamp in the 
    # header, otherwise make sure we don't get a cached copy
    if last_mod_time and not force:
        tstamp = last_mod_time.strftime('%a, %d %b %Y %H:%M:%S +0000')
        request.add_header('If-Modified-Since', tstamp)
    else:
        request.add_header('cache-control', 'no-cache')

    # user defined headers now, which may override things we've set above
    if headers:
        if not isinstance(headers, dict):
            module.fail_json("headers provided to fetch_url() must be a dict")
        for header in headers:
            request.add_header(header, headers[header])

    try:
        if sys.version_info < (2,6,0):
            # urlopen in python prior to 2.6.0 did not
            # have a timeout parameter
            r = urllib2.urlopen(request, None)
        else:
            r = urllib2.urlopen(request, None, timeout)
        info.update(r.info())
        info['url'] = r.geturl()  # The URL goes in too, because of redirects.
        info.update(dict(msg="OK (%s bytes)" % r.headers.get('Content-Length', 'unknown'), status=200))
    except urllib2.HTTPError, e:
        info.update(dict(msg=str(e), status=e.code))
    except urllib2.URLError, e:
        code = int(getattr(e, 'code', -1))
        info.update(dict(msg="Request failed: %s" % str(e), status=code))

    return r, info


########NEW FILE########
__FILENAME__ = play
# (c) 2012-2014, Michael DeHaan <michael.dehaan@gmail.com>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

#############################################

from ansible.utils.template import template
from ansible import utils
from ansible import errors
from ansible.playbook.task import Task
import ansible.constants as C
import pipes
import shlex
import os
import sys
import uuid

class Play(object):

    __slots__ = [
       'hosts', 'name', 'vars', 'default_vars', 'vars_prompt', 'vars_files',
       'handlers', 'remote_user', 'remote_port', 'included_roles', 'accelerate',
       'accelerate_port', 'accelerate_ipv6', 'sudo', 'sudo_user', 'transport', 'playbook',
       'tags', 'gather_facts', 'serial', '_ds', '_handlers', '_tasks',
       'basedir', 'any_errors_fatal', 'roles', 'max_fail_pct', '_play_hosts', 'su', 'su_user', 'vault_password'
    ]

    # to catch typos and so forth -- these are userland names
    # and don't line up 1:1 with how they are stored
    VALID_KEYS = [
       'hosts', 'name', 'vars', 'vars_prompt', 'vars_files',
       'tasks', 'handlers', 'remote_user', 'user', 'port', 'include', 'accelerate', 'accelerate_port', 'accelerate_ipv6',
       'sudo', 'sudo_user', 'connection', 'tags', 'gather_facts', 'serial',
       'any_errors_fatal', 'roles', 'pre_tasks', 'post_tasks', 'max_fail_percentage',
       'su', 'su_user', 'vault_password'
    ]

    # *************************************************

    def __init__(self, playbook, ds, basedir, vault_password=None):
        ''' constructor loads from a play datastructure '''

        for x in ds.keys():
            if not x in Play.VALID_KEYS:
                raise errors.AnsibleError("%s is not a legal parameter in an Ansible Playbook" % x)

        # allow all playbook keys to be set by --extra-vars
        self.vars             = ds.get('vars', {})
        self.vars_prompt      = ds.get('vars_prompt', {})
        self.playbook         = playbook
        self.vars             = self._get_vars()
        self.basedir          = basedir
        self.roles            = ds.get('roles', None)
        self.tags             = ds.get('tags', None)
        self.vault_password   = vault_password

        if self.tags is None:
            self.tags = []
        elif type(self.tags) in [ str, unicode ]:
            self.tags = self.tags.split(",")
        elif type(self.tags) != list:
            self.tags = []

        # We first load the vars files from the datastructure
        # so we have the default variables to pass into the roles
        self.vars_files = ds.get('vars_files', [])
        if not isinstance(self.vars_files, list):
            raise errors.AnsibleError('vars_files must be a list')
        self._update_vars_files_for_host(None)

        # now we load the roles into the datastructure
        self.included_roles = []
        ds = self._load_roles(self.roles, ds)
        
        # and finally re-process the vars files as they may have
        # been updated by the included roles
        self.vars_files = ds.get('vars_files', [])
        if not isinstance(self.vars_files, list):
            raise errors.AnsibleError('vars_files must be a list')

        self._update_vars_files_for_host(None)

        # apply any extra_vars specified on the command line now
        if type(self.playbook.extra_vars) == dict:
            self.vars = utils.combine_vars(self.vars, self.playbook.extra_vars)

        # template everything to be efficient, but do not pre-mature template
        # tasks/handlers as they may have inventory scope overrides
        _tasks    = ds.pop('tasks', [])
        _handlers = ds.pop('handlers', [])
        ds = template(basedir, ds, self.vars)
        ds['tasks'] = _tasks
        ds['handlers'] = _handlers

        self._ds = ds

        hosts = ds.get('hosts')
        if hosts is None:
            raise errors.AnsibleError('hosts declaration is required')
        elif isinstance(hosts, list):
            hosts = ';'.join(hosts)
        self.serial           = int(ds.get('serial', 0))
        self.hosts            = hosts
        self.name             = ds.get('name', self.hosts)
        self._tasks           = ds.get('tasks', [])
        self._handlers        = ds.get('handlers', [])
        self.remote_user      = ds.get('remote_user', ds.get('user', self.playbook.remote_user))
        self.remote_port      = ds.get('port', self.playbook.remote_port)
        self.sudo             = ds.get('sudo', self.playbook.sudo)
        self.sudo_user        = ds.get('sudo_user', self.playbook.sudo_user)
        self.transport        = ds.get('connection', self.playbook.transport)
        self.remote_port      = self.remote_port
        self.any_errors_fatal = utils.boolean(ds.get('any_errors_fatal', 'false'))
        self.accelerate       = utils.boolean(ds.get('accelerate', 'false'))
        self.accelerate_port  = ds.get('accelerate_port', None)
        self.accelerate_ipv6  = ds.get('accelerate_ipv6', False)
        self.max_fail_pct     = int(ds.get('max_fail_percentage', 100))
        self.su               = ds.get('su', self.playbook.su)
        self.su_user          = ds.get('su_user', self.playbook.su_user)

        # gather_facts is not a simple boolean, as None means  that a 'smart'
        # fact gathering mode will be used, so we need to be careful here as
        # calling utils.boolean(None) returns False
        self.gather_facts = ds.get('gather_facts', None)
        if self.gather_facts:
            self.gather_facts = utils.boolean(self.gather_facts)

        # Fail out if user specifies a sudo param with a su param in a given play
        if (ds.get('sudo') or ds.get('sudo_user')) and (ds.get('su') or ds.get('su_user')):
            raise errors.AnsibleError('sudo params ("sudo", "sudo_user") and su params '
                                      '("su", "su_user") cannot be used together')

        load_vars = {}
        load_vars['role_names'] = ds.get('role_names',[])
        load_vars['playbook_dir'] = self.basedir
        if self.playbook.inventory.basedir() is not None:
            load_vars['inventory_dir'] = self.playbook.inventory.basedir()

        self._tasks      = self._load_tasks(self._ds.get('tasks', []), load_vars)
        self._handlers   = self._load_tasks(self._ds.get('handlers', []), load_vars)

        # apply any missing tags to role tasks
        self._late_merge_role_tags()

        if self.sudo_user != 'root':
            self.sudo = True

        # place holder for the discovered hosts to be used in this play
        self._play_hosts = None

    # *************************************************

    def _get_role_path(self, role):
        """
        Returns the path on disk to the directory containing
        the role directories like tasks, templates, etc. Also 
        returns any variables that were included with the role
        """
        orig_path = template(self.basedir,role,self.vars)

        role_vars = {}
        if type(orig_path) == dict:
            # what, not a path?
            role_name = orig_path.get('role', None)
            if role_name is None:
                raise errors.AnsibleError("expected a role name in dictionary: %s" % orig_path)
            role_vars = orig_path
            orig_path = role_name

        role_path = None

        possible_paths = [
            utils.path_dwim(self.basedir, os.path.join('roles', orig_path)),
            utils.path_dwim(self.basedir, orig_path)
        ]

        if C.DEFAULT_ROLES_PATH:
            search_locations = C.DEFAULT_ROLES_PATH.split(os.pathsep)
            for loc in search_locations:
                loc = os.path.expanduser(loc)
                possible_paths.append(utils.path_dwim(loc, orig_path))

        for path_option in possible_paths:
            if os.path.isdir(path_option):
                role_path = path_option
                break

        if role_path is None:
            raise errors.AnsibleError("cannot find role in %s" % " or ".join(possible_paths))

        return (role_path, role_vars)

    def _build_role_dependencies(self, roles, dep_stack, passed_vars={}, level=0):
        # this number is arbitrary, but it seems sane
        if level > 20:
            raise errors.AnsibleError("too many levels of recursion while resolving role dependencies")
        for role in roles:
            role_path,role_vars = self._get_role_path(role)
            role_vars = utils.combine_vars(passed_vars, role_vars)
            vars = self._resolve_main(utils.path_dwim(self.basedir, os.path.join(role_path, 'vars')))
            vars_data = {}
            if os.path.isfile(vars):
                vars_data = utils.parse_yaml_from_file(vars, vault_password=self.vault_password)
                if vars_data:
                    if not isinstance(vars_data, dict):
                        raise errors.AnsibleError("vars from '%s' are not a dict" % vars)
                    role_vars = utils.combine_vars(vars_data, role_vars)
            defaults = self._resolve_main(utils.path_dwim(self.basedir, os.path.join(role_path, 'defaults')))
            defaults_data = {}
            if os.path.isfile(defaults):
                defaults_data = utils.parse_yaml_from_file(defaults, vault_password=self.vault_password)
            # the meta directory contains the yaml that should
            # hold the list of dependencies (if any)
            meta = self._resolve_main(utils.path_dwim(self.basedir, os.path.join(role_path, 'meta')))
            if os.path.isfile(meta):
                data = utils.parse_yaml_from_file(meta, vault_password=self.vault_password)
                if data:
                    dependencies = data.get('dependencies',[])
                    if dependencies is None:
                        dependencies = []
                    for dep in dependencies:
                        allow_dupes = False
                        (dep_path,dep_vars) = self._get_role_path(dep)
                        meta = self._resolve_main(utils.path_dwim(self.basedir, os.path.join(dep_path, 'meta')))
                        if os.path.isfile(meta):
                            meta_data = utils.parse_yaml_from_file(meta, vault_password=self.vault_password)
                            if meta_data:
                                allow_dupes = utils.boolean(meta_data.get('allow_duplicates',''))

                        # if any tags were specified as role/dep variables, merge
                        # them into the current dep_vars so they're passed on to any 
                        # further dependencies too, and so we only have one place
                        # (dep_vars) to look for tags going forward
                        def __merge_tags(var_obj):
                            old_tags = dep_vars.get('tags', [])
                            if isinstance(old_tags, basestring):
                                old_tags = [old_tags, ]
                            if isinstance(var_obj, dict):
                                new_tags = var_obj.get('tags', [])
                                if isinstance(new_tags, basestring):
                                    new_tags = [new_tags, ]
                            else:
                                new_tags = []
                            return list(set(old_tags).union(set(new_tags)))

                        dep_vars['tags'] = __merge_tags(role_vars)
                        dep_vars['tags'] = __merge_tags(passed_vars)

                        # if tags are set from this role, merge them
                        # into the tags list for the dependent role
                        if "tags" in passed_vars:
                            for included_role_dep in dep_stack:
                                included_dep_name = included_role_dep[0]
                                included_dep_vars = included_role_dep[2]
                                if included_dep_name == dep:
                                    if "tags" in included_dep_vars:
                                        included_dep_vars["tags"] = list(set(included_dep_vars["tags"]).union(set(passed_vars["tags"])))
                                    else:
                                        included_dep_vars["tags"] = passed_vars["tags"][:]

                        dep_vars = utils.combine_vars(passed_vars, dep_vars)
                        dep_vars = utils.combine_vars(role_vars, dep_vars)
                        vars = self._resolve_main(utils.path_dwim(self.basedir, os.path.join(dep_path, 'vars')))
                        vars_data = {}
                        if os.path.isfile(vars):
                            vars_data = utils.parse_yaml_from_file(vars, vault_password=self.vault_password)
                            if vars_data:
                                dep_vars = utils.combine_vars(vars_data, dep_vars)
                        defaults = self._resolve_main(utils.path_dwim(self.basedir, os.path.join(dep_path, 'defaults')))
                        dep_defaults_data = {}
                        if os.path.isfile(defaults):
                            dep_defaults_data = utils.parse_yaml_from_file(defaults, vault_password=self.vault_password)
                        if 'role' in dep_vars:
                            del dep_vars['role']

                        if not allow_dupes:
                            if dep in self.included_roles:
                                # skip back to the top, since we don't want to
                                # do anything else with this role
                                continue
                            else:
                                self.included_roles.append(dep)

                        def _merge_conditional(cur_conditionals, new_conditionals):
                            if isinstance(new_conditionals, (basestring, bool)):
                                cur_conditionals.append(new_conditionals)
                            elif isinstance(new_conditionals, list):
                                cur_conditionals.extend(new_conditionals)

                        # pass along conditionals from roles to dep roles
                        passed_when = passed_vars.get('when')
                        role_when = role_vars.get('when')
                        dep_when = dep_vars.get('when')

                        tmpcond = []
                        _merge_conditional(tmpcond, passed_when)
                        _merge_conditional(tmpcond, role_when)
                        _merge_conditional(tmpcond, dep_when)

                        if len(tmpcond) > 0:
                            dep_vars['when'] = tmpcond

                        self._build_role_dependencies([dep], dep_stack, passed_vars=dep_vars, level=level+1)
                        dep_stack.append([dep,dep_path,dep_vars,dep_defaults_data])

            # only add the current role when we're at the top level,
            # otherwise we'll end up in a recursive loop 
            if level == 0:
                self.included_roles.append(role)
                dep_stack.append([role,role_path,role_vars,defaults_data])
        return dep_stack

    def _load_role_defaults(self, defaults_files):
        # process default variables
        default_vars = {}
        for filename in defaults_files:
            if os.path.exists(filename):
                new_default_vars = utils.parse_yaml_from_file(filename, vault_password=self.vault_password)
                if new_default_vars:
                    if type(new_default_vars) != dict:
                        raise errors.AnsibleError("%s must be stored as dictionary/hash: %s" % (filename, type(new_default_vars)))

                    default_vars = utils.combine_vars(default_vars, new_default_vars)

        return default_vars

    def _load_roles(self, roles, ds):
        # a role is a name that auto-includes the following if they exist
        #    <rolename>/tasks/main.yml
        #    <rolename>/handlers/main.yml
        #    <rolename>/vars/main.yml
        #    <rolename>/library
        # and it auto-extends tasks/handlers/vars_files/module paths as appropriate if found

        if roles is None:
            roles = []
        if type(roles) != list:
            raise errors.AnsibleError("value of 'roles:' must be a list")

        new_tasks = []
        new_handlers = []
        new_vars_files = []
        defaults_files = []

        pre_tasks = ds.get('pre_tasks', None)
        if type(pre_tasks) != list:
            pre_tasks = []
        for x in pre_tasks:
            new_tasks.append(x)

        # flush handlers after pre_tasks
        new_tasks.append(dict(meta='flush_handlers'))

        roles = self._build_role_dependencies(roles, [], self.vars)

        # give each role a uuid
        for idx, val in enumerate(roles):
            this_uuid = str(uuid.uuid4())
            roles[idx][-2]['role_uuid'] = this_uuid

        role_names = []

        for (role,role_path,role_vars,default_vars) in roles:
            # special vars must be extracted from the dict to the included tasks
            special_keys = [ "sudo", "sudo_user", "when", "with_items" ]
            special_vars = {}
            for k in special_keys:
                if k in role_vars:
                    special_vars[k] = role_vars[k]

            task_basepath     = utils.path_dwim(self.basedir, os.path.join(role_path, 'tasks'))
            handler_basepath  = utils.path_dwim(self.basedir, os.path.join(role_path, 'handlers'))
            vars_basepath     = utils.path_dwim(self.basedir, os.path.join(role_path, 'vars'))
            meta_basepath     = utils.path_dwim(self.basedir, os.path.join(role_path, 'meta'))
            defaults_basepath = utils.path_dwim(self.basedir, os.path.join(role_path, 'defaults'))

            task      = self._resolve_main(task_basepath)
            handler   = self._resolve_main(handler_basepath)
            vars_file = self._resolve_main(vars_basepath)
            meta_file = self._resolve_main(meta_basepath)
            defaults_file = self._resolve_main(defaults_basepath)

            library   = utils.path_dwim(self.basedir, os.path.join(role_path, 'library'))

            missing = lambda f: not os.path.isfile(f)
            if missing(task) and missing(handler) and missing(vars_file) and missing(defaults_file) and missing(meta_file) and missing(library):
                raise errors.AnsibleError("found role at %s, but cannot find %s or %s or %s or %s or %s or %s" % (role_path, task, handler, vars_file, defaults_file, meta_file, library))

            if isinstance(role, dict):
                role_name = role['role']
            else:
                role_name = role

            role_names.append(role_name)
            if os.path.isfile(task):
                nt = dict(include=pipes.quote(task), vars=role_vars, default_vars=default_vars, role_name=role_name)
                for k in special_keys:
                    if k in special_vars:
                        nt[k] = special_vars[k]
                new_tasks.append(nt)
            if os.path.isfile(handler):
                nt = dict(include=pipes.quote(handler), vars=role_vars, role_name=role_name)
                for k in special_keys:
                    if k in special_vars:
                        nt[k] = special_vars[k]
                new_handlers.append(nt)
            if os.path.isfile(vars_file):
                new_vars_files.append(vars_file)
            if os.path.isfile(defaults_file):
                defaults_files.append(defaults_file)
            if os.path.isdir(library):
                utils.plugins.module_finder.add_directory(library)

        tasks      = ds.get('tasks', None)
        post_tasks = ds.get('post_tasks', None)
        handlers   = ds.get('handlers', None)
        vars_files = ds.get('vars_files', None)

        if type(tasks) != list:
            tasks = []
        if type(handlers) != list:
            handlers = []
        if type(vars_files) != list:
            vars_files = []
        if type(post_tasks) != list:
            post_tasks = []

        new_tasks.extend(tasks)
        # flush handlers after tasks + role tasks
        new_tasks.append(dict(meta='flush_handlers'))
        new_tasks.extend(post_tasks)
        # flush handlers after post tasks
        new_tasks.append(dict(meta='flush_handlers'))

        new_handlers.extend(handlers)
        new_vars_files.extend(vars_files)

        ds['tasks'] = new_tasks
        ds['handlers'] = new_handlers
        ds['vars_files'] = new_vars_files
        ds['role_names'] = role_names

        self.default_vars = self._load_role_defaults(defaults_files)

        return ds

    # *************************************************

    def _resolve_main(self, basepath):
        ''' flexibly handle variations in main filenames '''
        # these filenames are acceptable:
        mains = (
                 os.path.join(basepath, 'main'),
                 os.path.join(basepath, 'main.yml'),
                 os.path.join(basepath, 'main.yaml'),
                 os.path.join(basepath, 'main.json'),
                )
        if sum([os.path.isfile(x) for x in mains]) > 1:
            raise errors.AnsibleError("found multiple main files at %s, only one allowed" % (basepath))
        else:
            for m in mains:
                if os.path.isfile(m):
                    return m # exactly one main file
            return mains[0] # zero mains (we still need to return something)

    # *************************************************

    def _load_tasks(self, tasks, vars=None, default_vars=None, sudo_vars=None,
                    additional_conditions=None, original_file=None, role_name=None):
        ''' handle task and handler include statements '''

        results = []
        if tasks is None:
            # support empty handler files, and the like.
            tasks = []
        if additional_conditions is None:
            additional_conditions = []
        if vars is None:
            vars = {}
        if default_vars is None:
            default_vars = {}
        if sudo_vars is None:
            sudo_vars = {}

        old_conditions = list(additional_conditions)

        for x in tasks:

            # prevent assigning the same conditions to each task on an include
            included_additional_conditions = list(old_conditions)

            if not isinstance(x, dict):
                raise errors.AnsibleError("expecting dict; got: %s, error in %s" % (x, original_file))

            # evaluate sudo vars for current and child tasks 
            included_sudo_vars = {}
            for k in ["sudo", "sudo_user"]:
                if k in x:
                    included_sudo_vars[k] = x[k]
                elif k in sudo_vars:
                    included_sudo_vars[k] = sudo_vars[k]
                    x[k] = sudo_vars[k]

            if 'meta' in x:
                if x['meta'] == 'flush_handlers':
                    results.append(Task(self, x))
                    continue

            task_vars = self.vars.copy()
            task_vars.update(vars)
            if original_file:
                task_vars['_original_file'] = original_file

            if 'include' in x:
                tokens = shlex.split(str(x['include']))
                items = ['']
                included_additional_conditions = list(additional_conditions)
                include_vars = {}
                for k in x:
                    if k.startswith("with_"):
                        if original_file:
                            offender = " (in %s)" % original_file
                        else:
                            offender = ""
                        utils.deprecated("include + with_items is a removed deprecated feature" + offender, "1.5", removed=True)
                    elif k.startswith("when_"):
                        utils.deprecated("\"when_<criteria>:\" is a removed deprecated feature, use the simplified 'when:' conditional directly", None, removed=True)
                    elif k == 'when':
                        if type(x[k]) is str:
                            included_additional_conditions.insert(0, x[k])
                        elif type(x[k]) is list:
                            for i in x[k]:
                                included_additional_conditions.insert(0, i)
                    elif k in ("include", "vars", "default_vars", "sudo", "sudo_user", "role_name", "no_log"):
                        continue
                    else:
                        include_vars[k] = x[k]

                default_vars = x.get('default_vars', {})
                if not default_vars:
                    default_vars = self.default_vars
                else:
                    default_vars = utils.combine_vars(self.default_vars, default_vars)

                # append the vars defined with the include (from above) 
                # as well as the old-style 'vars' element. The old-style
                # vars are given higher precedence here (just in case)
                task_vars = utils.combine_vars(task_vars, include_vars)
                if 'vars' in x:
                    task_vars = utils.combine_vars(task_vars, x['vars'])

                if 'when' in x:
                    if isinstance(x['when'], (basestring, bool)):
                        included_additional_conditions.append(x['when'])
                    elif isinstance(x['when'], list):
                        included_additional_conditions.extend(x['when'])

                new_role = None
                if 'role_name' in x:
                    new_role = x['role_name']

                for item in items:
                    mv = task_vars.copy()
                    mv['item'] = item
                    for t in tokens[1:]:
                        (k,v) = t.split("=", 1)
                        mv[k] = template(self.basedir, v, mv)
                    dirname = self.basedir
                    if original_file:
                        dirname = os.path.dirname(original_file)
                    include_file = template(dirname, tokens[0], mv)
                    include_filename = utils.path_dwim(dirname, include_file)
                    data = utils.parse_yaml_from_file(include_filename, vault_password=self.vault_password)
                    if 'role_name' in x and data is not None:
                        for y in data:
                            if isinstance(y, dict) and 'include' in y:
                                y['role_name'] = new_role
                    loaded = self._load_tasks(data, mv, default_vars, included_sudo_vars, list(included_additional_conditions), original_file=include_filename, role_name=new_role)
                    results += loaded
            elif type(x) == dict:
                task = Task(
                    self, x,
                    module_vars=task_vars,
                    default_vars=default_vars,
                    additional_conditions=list(additional_conditions),
                    role_name=role_name
                )
                results.append(task)
            else:
                raise Exception("unexpected task type")

        for x in results:
            if self.tags is not None:
                x.tags.extend(self.tags)

        return results

    # *************************************************

    def _is_valid_tag(self, tag_list):
        """
        Check to see if the list of tags passed in is in the list of tags 
        we only want (playbook.only_tags), or if it is not in the list of 
        tags we don't want (playbook.skip_tags).
        """
        matched_skip_tags = set(tag_list) & set(self.playbook.skip_tags)
        matched_only_tags = set(tag_list) & set(self.playbook.only_tags)
        if len(matched_skip_tags) > 0 or (self.playbook.only_tags != ['all'] and len(matched_only_tags) == 0):
            return False
        return True

    # *************************************************

    def tasks(self):
        ''' return task objects for this play '''
        return self._tasks

    def handlers(self):
        ''' return handler objects for this play '''
        return self._handlers

    # *************************************************

    def _get_vars(self):
        ''' load the vars section from a play, accounting for all sorts of variable features
        including loading from yaml files, prompting, and conditional includes of the first
        file found in a list. '''

        if self.vars is None:
            self.vars = {}

        if type(self.vars) not in [dict, list]:
            raise errors.AnsibleError("'vars' section must contain only key/value pairs")

        vars = {}

        # translate a list of vars into a dict
        if type(self.vars) == list:
            for item in self.vars:
                if getattr(item, 'items', None) is None:
                    raise errors.AnsibleError("expecting a key-value pair in 'vars' section")
                k, v = item.items()[0]
                vars[k] = v
        else:
            vars.update(self.vars)

        if type(self.vars_prompt) == list:
            for var in self.vars_prompt:
                if not 'name' in var:
                    raise errors.AnsibleError("'vars_prompt' item is missing 'name:'")

                vname = var['name']
                prompt = var.get("prompt", vname)
                default = var.get("default", None)
                private = var.get("private", True)

                confirm = var.get("confirm", False)
                encrypt = var.get("encrypt", None)
                salt_size = var.get("salt_size", None)
                salt = var.get("salt", None)

                if vname not in self.playbook.extra_vars:
                    vars[vname] = self.playbook.callbacks.on_vars_prompt(
                                     vname, private, prompt, encrypt, confirm, salt_size, salt, default
                                  )

        elif type(self.vars_prompt) == dict:
            for (vname, prompt) in self.vars_prompt.iteritems():
                prompt_msg = "%s: " % prompt
                if vname not in self.playbook.extra_vars:
                    vars[vname] = self.playbook.callbacks.on_vars_prompt(
                                     varname=vname, private=False, prompt=prompt_msg, default=None
                                  )

        else:
            raise errors.AnsibleError("'vars_prompt' section is malformed, see docs")

        if type(self.playbook.extra_vars) == dict:
            vars = utils.combine_vars(vars, self.playbook.extra_vars)

        return vars

    # *************************************************

    def update_vars_files(self, hosts, vault_password=None):
        ''' calculate vars_files, which requires that setup runs first so ansible facts can be mixed in '''

        # now loop through all the hosts...
        for h in hosts:
            self._update_vars_files_for_host(h, vault_password=vault_password)

    # *************************************************

    def compare_tags(self, tags):
        ''' given a list of tags that the user has specified, return two lists:
        matched_tags:   tags were found within the current play and match those given
                        by the user
        unmatched_tags: tags that were found within the current play but do not match
                        any provided by the user '''

        # gather all the tags in all the tasks and handlers into one list
        # FIXME: isn't this in self.tags already?

        all_tags = []
        for task in self._tasks:
            if not task.meta:
                all_tags.extend(task.tags)
        for handler in self._handlers:
            all_tags.extend(handler.tags)

        # compare the lists of tags using sets and return the matched and unmatched
        all_tags_set = set(all_tags)
        tags_set = set(tags)
        matched_tags = all_tags_set & tags_set
        unmatched_tags = all_tags_set - tags_set

        return matched_tags, unmatched_tags

    # *************************************************

    def _late_merge_role_tags(self):
        # build a local dict of tags for roles
        role_tags = {}
        for task in self._ds['tasks']:
            if 'role_name' in task:
                this_role = task['role_name'] + "-" + task['vars']['role_uuid']

                if this_role not in role_tags:
                    role_tags[this_role] = []

                if 'tags' in task['vars']:
                    if isinstance(task['vars']['tags'], basestring):
                        role_tags[this_role] += shlex.split(task['vars']['tags'])
                    else:
                        role_tags[this_role] += task['vars']['tags']

        # apply each role's tags to it's tasks
        for idx, val in enumerate(self._tasks):
            if getattr(val, 'role_name', None) is not None:
                this_role = val.role_name + "-" + val.module_vars['role_uuid']
                if this_role in role_tags:
                    self._tasks[idx].tags = sorted(set(self._tasks[idx].tags + role_tags[this_role]))

    # *************************************************

    def _has_vars_in(self, msg):
        return "$" in msg or "{{" in msg

    # *************************************************

    def _update_vars_files_for_host(self, host, vault_password=None):

        def generate_filenames(host, inject, filename):

            """ Render the raw filename into 3 forms """

            filename2 = template(self.basedir, filename, self.vars)
            filename3 = filename2
            if host is not None:
                filename3 = template(self.basedir, filename2, inject)
            if self._has_vars_in(filename3) and host is not None:
                # allow play scoped vars and host scoped vars to template the filepath
                inject.update(self.vars)
                filename4 = template(self.basedir, filename3, inject)
                filename4 = utils.path_dwim(self.basedir, filename4)
            else:    
                filename4 = utils.path_dwim(self.basedir, filename3)
            return filename2, filename3, filename4


        def update_vars_cache(host, inject, data, filename):

            """ update a host's varscache with new var data """

            data = utils.combine_vars(inject, data)
            self.playbook.VARS_CACHE[host] = utils.combine_vars(self.playbook.VARS_CACHE.get(host, {}), data)
            self.playbook.callbacks.on_import_for_host(host, filename4)

        def process_files(filename, filename2, filename3, filename4, host=None):

            """ pseudo-algorithm for deciding where new vars should go """

            data = utils.parse_yaml_from_file(filename4, vault_password=self.vault_password)
            if data:
                if type(data) != dict:
                    raise errors.AnsibleError("%s must be stored as a dictionary/hash" % filename4)
                if host is not None:
                    if self._has_vars_in(filename2) and not self._has_vars_in(filename3):
                        # running a host specific pass and has host specific variables
                        # load into setup cache
                        update_vars_cache(host, inject, data, filename4)
                    elif self._has_vars_in(filename3) and not self._has_vars_in(filename4):
                        # handle mixed scope variables in filepath
                        update_vars_cache(host, inject, data, filename4)

                elif not self._has_vars_in(filename4):
                    # found a non-host specific variable, load into vars and NOT
                    # the setup cache
                    if host is not None:
                        self.vars.update(data)
                    else:
                        self.vars = utils.combine_vars(self.vars, data)

        # Enforce that vars_files is always a list
        if type(self.vars_files) != list:
            self.vars_files = [ self.vars_files ]

        # Build an inject if this is a host run started by self.update_vars_files
        if host is not None:
            inject = {}
            inject.update(self.playbook.inventory.get_variables(host, vault_password=vault_password))
            inject.update(self.playbook.SETUP_CACHE.get(host, {}))
            inject.update(self.playbook.VARS_CACHE.get(host, {}))
        else:
            inject = None            

        for filename in self.vars_files:
            if type(filename) == list:
                # loop over all filenames, loading the first one, and failing if none found
                found = False
                sequence = []
                for real_filename in filename:
                    filename2, filename3, filename4 = generate_filenames(host, inject, real_filename)
                    sequence.append(filename4)
                    if os.path.exists(filename4):
                        found = True
                        process_files(filename, filename2, filename3, filename4, host=host)
                    elif host is not None:
                        self.playbook.callbacks.on_not_import_for_host(host, filename4)
                    if found:
                        break
                if not found and host is not None:
                    raise errors.AnsibleError(
                        "%s: FATAL, no files matched for vars_files import sequence: %s" % (host, sequence)
                    )

            else:
                # just one filename supplied, load it!
                filename2, filename3, filename4 = generate_filenames(host, inject, filename)
                if self._has_vars_in(filename4):
                    continue
                process_files(filename, filename2, filename3, filename4, host=host)

        # finally, update the VARS_CACHE for the host, if it is set
        if host is not None:
            self.playbook.VARS_CACHE[host].update(self.playbook.extra_vars)

########NEW FILE########
__FILENAME__ = task
# (c) 2012-2014, Michael DeHaan <michael.dehaan@gmail.com>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

from ansible import errors
from ansible import utils
import os
import ansible.utils.template as template
import sys

class Task(object):

    __slots__ = [
        'name', 'meta', 'action', 'when', 'async_seconds', 'async_poll_interval',
        'notify', 'module_name', 'module_args', 'module_vars', 'default_vars',
        'play', 'notified_by', 'tags', 'register', 'role_name',
        'delegate_to', 'first_available_file', 'ignore_errors',
        'local_action', 'transport', 'sudo', 'remote_user', 'sudo_user', 'sudo_pass',
        'items_lookup_plugin', 'items_lookup_terms', 'environment', 'args',
        'any_errors_fatal', 'changed_when', 'failed_when', 'always_run', 'delay', 'retries', 'until',
        'su', 'su_user', 'su_pass', 'no_log',
    ]

    # to prevent typos and such
    VALID_KEYS = [
         'name', 'meta', 'action', 'when', 'async', 'poll', 'notify',
         'first_available_file', 'include', 'tags', 'register', 'ignore_errors',
         'delegate_to', 'local_action', 'transport', 'remote_user', 'sudo', 'sudo_user',
         'sudo_pass', 'when', 'connection', 'environment', 'args',
         'any_errors_fatal', 'changed_when', 'failed_when', 'always_run', 'delay', 'retries', 'until',
         'su', 'su_user', 'su_pass', 'no_log',
    ]

    def __init__(self, play, ds, module_vars=None, default_vars=None, additional_conditions=None, role_name=None):
        ''' constructor loads from a task or handler datastructure '''

        # meta directives are used to tell things like ansible/playbook to run
        # operations like handler execution.  Meta tasks are not executed
        # normally.
        if 'meta' in ds:
            self.meta = ds['meta']
            self.tags = []
            return
        else:
            self.meta = None


        library = os.path.join(play.basedir, 'library')
        if os.path.exists(library):
            utils.plugins.module_finder.add_directory(library)

        for x in ds.keys():

            # code to allow for saying "modulename: args" versus "action: modulename args"
            if x in utils.plugins.module_finder:

                if 'action' in ds:
                    raise errors.AnsibleError("multiple actions specified in task: '%s' and '%s'" % (x, ds.get('name', ds['action'])))
                if isinstance(ds[x], dict):
                    if 'args' in ds:
                        raise errors.AnsibleError("can't combine args: and a dict for %s: in task %s" % (x, ds.get('name', "%s: %s" % (x, ds[x]))))
                    ds['args'] = ds[x]
                    ds[x] = ''
                elif ds[x] is None:
                    ds[x] = ''
                if not isinstance(ds[x], basestring):
                    raise errors.AnsibleError("action specified for task %s has invalid type %s" % (ds.get('name', "%s: %s" % (x, ds[x])), type(ds[x])))
                ds['action'] = x + " " + ds[x]
                ds.pop(x)

            # code to allow "with_glob" and to reference a lookup plugin named glob
            elif x.startswith("with_"):

                if isinstance(ds[x], basestring) and ds[x].lstrip().startswith("{{"):
                    utils.warning("It is unnecessary to use '{{' in loops, leave variables in loop expressions bare.")

                plugin_name = x.replace("with_","")
                if plugin_name in utils.plugins.lookup_loader:
                    ds['items_lookup_plugin'] = plugin_name
                    ds['items_lookup_terms'] = ds[x]
                    ds.pop(x)
                else:
                    raise errors.AnsibleError("cannot find lookup plugin named %s for usage in with_%s" % (plugin_name, plugin_name))

            elif x in [ 'changed_when', 'failed_when', 'when']:
                if isinstance(ds[x], basestring) and ds[x].lstrip().startswith("{{"):
                    utils.warning("It is unnecessary to use '{{' in conditionals, leave variables in loop expressions bare.")
            elif x.startswith("when_"):
                utils.deprecated("The 'when_' conditional has been removed. Switch to using the regular unified 'when' statements as described on docs.ansible.com.","1.5", removed=True)

                if 'when' in ds:
                    raise errors.AnsibleError("multiple when_* statements specified in task %s" % (ds.get('name', ds['action'])))
                when_name = x.replace("when_","")
                ds['when'] = "%s %s" % (when_name, ds[x])
                ds.pop(x)
            elif not x in Task.VALID_KEYS:
                raise errors.AnsibleError("%s is not a legal parameter in an Ansible task or handler" % x)

        self.module_vars  = module_vars
        self.default_vars = default_vars
        self.play         = play

        # load various attributes
        self.name         = ds.get('name', None)
        self.tags         = [ 'all' ]
        self.register     = ds.get('register', None)
        self.sudo         = utils.boolean(ds.get('sudo', play.sudo))
        self.su           = utils.boolean(ds.get('su', play.su))
        self.environment  = ds.get('environment', {})
        self.role_name    = role_name
        self.no_log       = utils.boolean(ds.get('no_log', "false"))

        #Code to allow do until feature in a Task 
        if 'until' in ds:
            if not ds.get('register'):
                raise errors.AnsibleError("register keyword is mandatory when using do until feature")
            self.module_vars['delay']     = ds.get('delay', 5)
            self.module_vars['retries']   = ds.get('retries', 3)
            self.module_vars['register']  = ds.get('register', None)
            self.until                    = ds.get('until')
            self.module_vars['until']     = self.until

        # rather than simple key=value args on the options line, these represent structured data and the values
        # can be hashes and lists, not just scalars
        self.args         = ds.get('args', {})

        # get remote_user for task, then play, then playbook
        if ds.get('remote_user') is not None:
            self.remote_user      = ds.get('remote_user')
        elif ds.get('remote_user', play.remote_user) is not None:
            self.remote_user      = ds.get('remote_user', play.remote_user)
        else:
            self.remote_user      = ds.get('remote_user', play.playbook.remote_user)

        self.sudo_user    = None
        self.sudo_pass    = None
        self.su_user      = None
        self.su_pass      = None

        if self.sudo:
            self.sudo_user    = ds.get('sudo_user', play.sudo_user)
            self.sudo_pass    = ds.get('sudo_pass', play.playbook.sudo_pass)
        elif self.su:
            self.su_user      = ds.get('su_user', play.su_user)
            self.su_pass      = ds.get('su_pass', play.playbook.su_pass)

        # Fail out if user specifies a sudo param with a su param in a given play
        if (ds.get('sudo') or ds.get('sudo_user') or ds.get('sudo_pass')) and \
                (ds.get('su') or ds.get('su_user') or ds.get('su_pass')):
            raise errors.AnsibleError('sudo params ("sudo", "sudo_user", "sudo_pass") '
                                      'and su params "su", "su_user", "su_pass") '
                                      'cannot be used together')

        # Both are defined
        if ('action' in ds) and ('local_action' in ds):
            raise errors.AnsibleError("the 'action' and 'local_action' attributes can not be used together")
        # Both are NOT defined
        elif (not 'action' in ds) and (not 'local_action' in ds):
            raise errors.AnsibleError("'action' or 'local_action' attribute missing in task \"%s\"" % ds.get('name', '<Unnamed>'))
        # Only one of them is defined
        elif 'local_action' in ds:
            self.action      = ds.get('local_action', '')
            self.delegate_to = '127.0.0.1'
        else:
            self.action      = ds.get('action', '')
            self.delegate_to = ds.get('delegate_to', None)
            self.transport   = ds.get('connection', ds.get('transport', play.transport))

        if isinstance(self.action, dict):
            if 'module' not in self.action:
                raise errors.AnsibleError("'module' attribute missing from action in task \"%s\"" % ds.get('name', '%s' % self.action))
            if self.args:
                raise errors.AnsibleError("'args' cannot be combined with dict 'action' in task \"%s\"" % ds.get('name', '%s' % self.action))
            self.args = self.action
            self.action = self.args.pop('module')

        # delegate_to can use variables
        if not (self.delegate_to is None):
            # delegate_to: localhost should use local transport
            if self.delegate_to in ['127.0.0.1', 'localhost']:
                self.transport   = 'local'

        # notified by is used by Playbook code to flag which hosts
        # need to run a notifier
        self.notified_by = []

        # if no name is specified, use the action line as the name
        if self.name is None:
            self.name = self.action

        # load various attributes
        self.when    = ds.get('when', None)
        self.changed_when = ds.get('changed_when', None)
        self.failed_when = ds.get('failed_when', None)

        self.async_seconds = ds.get('async', 0)  # not async by default
        self.async_seconds = template.template_from_string(play.basedir, self.async_seconds, self.module_vars)
        self.async_seconds = int(self.async_seconds)
        self.async_poll_interval = ds.get('poll', 10)  # default poll = 10 seconds
        self.async_poll_interval = template.template_from_string(play.basedir, self.async_poll_interval, self.module_vars)
        self.async_poll_interval = int(self.async_poll_interval)
        self.notify = ds.get('notify', [])
        self.first_available_file = ds.get('first_available_file', None)

        self.items_lookup_plugin = ds.get('items_lookup_plugin', None)
        self.items_lookup_terms  = ds.get('items_lookup_terms', None)
     

        self.ignore_errors = ds.get('ignore_errors', False)
        self.any_errors_fatal = ds.get('any_errors_fatal', play.any_errors_fatal)

        self.always_run = ds.get('always_run', False)

        # action should be a string
        if not isinstance(self.action, basestring):
            raise errors.AnsibleError("action is of type '%s' and not a string in task. name: %s" % (type(self.action).__name__, self.name))

        # notify can be a string or a list, store as a list
        if isinstance(self.notify, basestring):
            self.notify = [ self.notify ]

        # split the action line into a module name + arguments
        tokens = self.action.split(None, 1)
        if len(tokens) < 1:
            raise errors.AnsibleError("invalid/missing action in task. name: %s" % self.name)
        self.module_name = tokens[0]
        self.module_args = ''
        if len(tokens) > 1:
            self.module_args = tokens[1]

        import_tags = self.module_vars.get('tags',[])
        if type(import_tags) in [int,float]:
            import_tags = str(import_tags)
        elif type(import_tags) in [str,unicode]:
            # allow the user to list comma delimited tags
            import_tags = import_tags.split(",")

        # handle mutually incompatible options
        incompatibles = [ x for x in [ self.first_available_file, self.items_lookup_plugin ] if x is not None ]
        if len(incompatibles) > 1:
            raise errors.AnsibleError("with_(plugin), and first_available_file are mutually incompatible in a single task")

        # make first_available_file accessable to Runner code
        if self.first_available_file:
            self.module_vars['first_available_file'] = self.first_available_file

        if self.items_lookup_plugin is not None:
            self.module_vars['items_lookup_plugin'] = self.items_lookup_plugin
            self.module_vars['items_lookup_terms'] = self.items_lookup_terms

        # allow runner to see delegate_to option
        self.module_vars['delegate_to'] = self.delegate_to

        # make some task attributes accessible to Runner code
        self.module_vars['ignore_errors'] = self.ignore_errors
        self.module_vars['register'] = self.register
        self.module_vars['changed_when'] = self.changed_when
        self.module_vars['failed_when'] = self.failed_when
        self.module_vars['always_run'] = self.always_run

        # tags allow certain parts of a playbook to be run without running the whole playbook
        apply_tags = ds.get('tags', None)
        if apply_tags is not None:
            if type(apply_tags) in [ str, unicode ]:
                self.tags.append(apply_tags)
            elif type(apply_tags) in [ int, float ]:
                self.tags.append(str(apply_tags))
            elif type(apply_tags) == list:
                self.tags.extend(apply_tags)
        self.tags.extend(import_tags)

        if additional_conditions:
            new_conditions = additional_conditions
            new_conditions.append(self.when)
            self.when = new_conditions

########NEW FILE########
__FILENAME__ = add_host
# Copyright 2012, Seth Vidal <skvidal@fedoraproject.org>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

import ansible

from ansible.callbacks import vv
from ansible.errors import AnsibleError as ae
from ansible.runner.return_data import ReturnData
from ansible.utils import parse_kv
from ansible.inventory.host import Host
from ansible.inventory.group import Group

class ActionModule(object):
    ''' Create inventory hosts and groups in the memory inventory'''

    ### We need to be able to modify the inventory
    BYPASS_HOST_LOOP = True
    TRANSFERS_FILES = False

    def __init__(self, runner):
        self.runner = runner

    def run(self, conn, tmp, module_name, module_args, inject, complex_args=None, **kwargs):

        if self.runner.noop_on_check(inject):
            return ReturnData(conn=conn, comm_ok=True, result=dict(skipped=True, msg='check mode not supported for this module'))

        args = {}
        if complex_args:
            args.update(complex_args)
        args.update(parse_kv(module_args))
        if not 'hostname' in args and not 'name' in args:
            raise ae("'name' is a required argument.")

        result = {}

        # Parse out any hostname:port patterns
        new_name = args.get('name', args.get('hostname', None))
        vv("creating host via 'add_host': hostname=%s" % new_name)

        if ":" in new_name:
            new_name, new_port = new_name.split(":")
            args['ansible_ssh_port'] = new_port
        
        # redefine inventory and get group "all"
        inventory = self.runner.inventory
        allgroup = inventory.get_group('all')

        # check if host in cache, add if not
        if new_name in inventory._hosts_cache:
            new_host = inventory._hosts_cache[new_name]
        else:
            new_host = Host(new_name)
            # only groups can be added directly to inventory
            inventory._hosts_cache[new_name] = new_host
            allgroup.add_host(new_host)

        # Add any variables to the new_host
        for k in args.keys():
            if not k in [ 'name', 'hostname', 'groupname', 'groups' ]:
                new_host.set_variable(k, args[k]) 
                
        
        groupnames = args.get('groupname', args.get('groups', args.get('group', ''))) 
        # add it to the group if that was specified
        if groupnames != '':
            for group_name in groupnames.split(","):
                group_name = group_name.strip()
                if not inventory.get_group(group_name):
                    new_group = Group(group_name)
                    inventory.add_group(new_group)
                grp = inventory.get_group(group_name)
                grp.add_host(new_host)

                # add this host to the group cache
                if inventory._groups_list is not None:
                    if group_name in inventory._groups_list:
                        if new_host.name not in inventory._groups_list[group_name]:
                            inventory._groups_list[group_name].append(new_host.name)

                vv("added host to group via add_host module: %s" % group_name)
            result['new_groups'] = groupnames.split(",")
            
        result['new_host'] = new_name

        # clear pattern caching completely since it's unpredictable what
        # patterns may have referenced the group
        inventory.clear_pattern_cache()
        
        return ReturnData(conn=conn, comm_ok=True, result=result)




########NEW FILE########
__FILENAME__ = assemble
# (c) 2013-2014, Michael DeHaan <michael.dehaan@gmail.com>
#           Stephen Fromm <sfromm@gmail.com>
#           Brian Coca  <briancoca+dev@gmail.com>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License

import os
import os.path
import pipes
import shutil
import tempfile
import base64
from ansible import utils
from ansible.runner.return_data import ReturnData

class ActionModule(object):

    TRANSFERS_FILES = True

    def __init__(self, runner):
        self.runner = runner

    def _assemble_from_fragments(self, src_path, delimiter=None, compiled_regexp=None):
        ''' assemble a file from a directory of fragments '''
        tmpfd, temp_path = tempfile.mkstemp()
        tmp = os.fdopen(tmpfd,'w')
        delimit_me = False
        add_newline = False

        for f in sorted(os.listdir(src_path)):
            if compiled_regexp and not compiled_regexp.search(f):
                continue
            fragment = "%s/%s" % (src_path, f)
            if not os.path.isfile(fragment):
                continue
            fragment_content = file(fragment).read()

            # always put a newline between fragments if the previous fragment didn't end with a newline.
            if add_newline:
                tmp.write('\n')

            # delimiters should only appear between fragments
            if delimit_me:
                if delimiter:
                    # un-escape anything like newlines
                    delimiter = delimiter.decode('unicode-escape')
                    tmp.write(delimiter)
                    # always make sure there's a newline after the
                    # delimiter, so lines don't run together
                    if delimiter[-1] != '\n':
                        tmp.write('\n')

            tmp.write(fragment_content)
            delimit_me = True
            if fragment_content.endswith('\n'):
                add_newline = False
            else:
                add_newline = True

        tmp.close()
        return temp_path

    def run(self, conn, tmp, module_name, module_args, inject, complex_args=None, **kwargs):

        # load up options
        options  = {}
        if complex_args:
            options.update(complex_args)

        options.update(utils.parse_kv(module_args))

        src = options.get('src', None)
        dest = options.get('dest', None)
        delimiter = options.get('delimiter', None)
        remote_src = utils.boolean(options.get('remote_src', 'yes'))


        if src is None or dest is None:
            result = dict(failed=True, msg="src and dest are required")
            return ReturnData(conn=conn, comm_ok=False, result=result)

        if remote_src:
            return self.runner._execute_module(conn, tmp, 'assemble', module_args, inject=inject, complex_args=complex_args)
        elif '_original_file' in inject:
            src = utils.path_dwim_relative(inject['_original_file'], 'files', src, self.runner.basedir)
        else:
            # the source is local, so expand it here
            src = os.path.expanduser(src)

        # Does all work assembling the file
        path = self._assemble_from_fragments(src, delimiter)

        pathmd5 = utils.md5s(path)
        remote_md5 = self.runner._remote_md5(conn, tmp, dest)

        if pathmd5 != remote_md5:
            resultant = file(path).read()
            if self.runner.diff:
                dest_result = self.runner._execute_module(conn, tmp, 'slurp', "path=%s" % dest, inject=inject, persist_files=True)
                if 'content' in dest_result.result:
                    dest_contents = dest_result.result['content']
                    if dest_result.result['encoding'] == 'base64':
                        dest_contents = base64.b64decode(dest_contents)
                    else:
                        raise Exception("unknown encoding, failed: %s" % dest_result.result)
            xfered = self.runner._transfer_str(conn, tmp, 'src', resultant)

            # fix file permissions when the copy is done as a different user
            if self.runner.sudo and self.runner.sudo_user != 'root':
                self.runner._low_level_exec_command(conn, "chmod a+r %s" % xfered, tmp)

            # run the copy module
            module_args = "%s src=%s dest=%s original_basename=%s" % (module_args, pipes.quote(xfered), pipes.quote(dest), pipes.quote(os.path.basename(src)))

            if self.runner.noop_on_check(inject):
                return ReturnData(conn=conn, comm_ok=True, result=dict(changed=True), diff=dict(before_header=dest, after_header=src, after=resultant))
            else:
                res = self.runner._execute_module(conn, tmp, 'copy', module_args, inject=inject)
                res.diff = dict(after=resultant)
                return res
        else:
            module_args = "%s src=%s dest=%s original_basename=%s" % (module_args, pipes.quote(xfered), pipes.quote(dest), pipes.quote(os.path.basename(src)))
            return self.runner._execute_module(conn, tmp, 'file', module_args, inject=inject)

########NEW FILE########
__FILENAME__ = assert
# Copyright 2012, Dag Wieers <dag@wieers.com>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

import ansible

from ansible import utils, errors
from ansible.runner.return_data import ReturnData

class ActionModule(object):
    ''' Fail with custom message '''

    TRANSFERS_FILES = False

    def __init__(self, runner):
        self.runner = runner

    def run(self, conn, tmp, module_name, module_args, inject, complex_args=None, **kwargs):

        # note: the fail module does not need to pay attention to check mode
        # it always runs.

        args = {}
        if complex_args:
            args.update(complex_args)
        args.update(utils.parse_kv(module_args))

        msg = ''

        if 'msg' in args:
            msg = args['msg']

        if not 'that' in args:
            raise errors.AnsibleError('conditional required in "that" string')

        if not isinstance(args['that'], list):
            args['that'] = [ args['that'] ]

        for that in args['that']:
            result = utils.check_conditional(that, self.runner.basedir, inject, fail_on_undefined=True)
            if not result:
                return ReturnData(conn=conn, result=dict(failed=True, assertion=that, evaluated_to=result))

        return ReturnData(conn=conn, result=dict(msg='all assertions passed'))

########NEW FILE########
__FILENAME__ = async
# (c) 2012-2014, Michael DeHaan <michael.dehaan@gmail.com>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

from ansible.runner.return_data import ReturnData

class ActionModule(object):

    def __init__(self, runner):
        self.runner = runner

    def run(self, conn, tmp, module_name, module_args, inject, complex_args=None, **kwargs):
        ''' transfer the given module name, plus the async module, then run it '''

        if self.runner.noop_on_check(inject):
            return ReturnData(conn=conn, comm_ok=True, result=dict(skipped=True, msg='check mode not supported for this module'))

        # shell and command module are the same
        if module_name == 'shell':
            module_name = 'command'
            module_args += " #USE_SHELL"

        if "tmp" not in tmp:
            tmp = self.runner._make_tmp_path(conn)

        (module_path, is_new_style, shebang) = self.runner._copy_module(conn, tmp, module_name, module_args, inject, complex_args=complex_args)
        self.runner._low_level_exec_command(conn, "chmod a+rx %s" % module_path, tmp)

        return self.runner._execute_module(conn, tmp, 'async_wrapper', module_args,
           async_module=module_path,
           async_jid=self.runner.generated_jid,
           async_limit=self.runner.background,
           inject=inject
        )


########NEW FILE########
__FILENAME__ = copy
# (c) 2012-2014, Michael DeHaan <michael.dehaan@gmail.com>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

import os

from ansible import utils
import ansible.constants as C
import ansible.utils.template as template
from ansible import errors
from ansible.runner.return_data import ReturnData
import base64
import json
import stat
import tempfile
import pipes

## fixes https://github.com/ansible/ansible/issues/3518
# http://mypy.pythonblogs.com/12_mypy/archive/1253_workaround_for_python_bug_ascii_codec_cant_encode_character_uxa0_in_position_111_ordinal_not_in_range128.html
import sys
reload(sys)
sys.setdefaultencoding("utf8")


class ActionModule(object):

    def __init__(self, runner):
        self.runner = runner

    def run(self, conn, tmp_path, module_name, module_args, inject, complex_args=None, **kwargs):
        ''' handler for file transfer operations '''

        # load up options
        options = {}
        if complex_args:
            options.update(complex_args)
        options.update(utils.parse_kv(module_args))
        source  = options.get('src', None)
        content = options.get('content', None)
        dest    = options.get('dest', None)
        raw     = utils.boolean(options.get('raw', 'no'))
        force   = utils.boolean(options.get('force', 'yes'))

        # content with newlines is going to be escaped to safely load in yaml
        # now we need to unescape it so that the newlines are evaluated properly
        # when writing the file to disk
        if content:
            if isinstance(content, unicode):
                try:
                    content = content.decode('unicode-escape')
                except UnicodeDecodeError:
                    pass

        if (source is None and content is None and not 'first_available_file' in inject) or dest is None:
            result=dict(failed=True, msg="src (or content) and dest are required")
            return ReturnData(conn=conn, result=result)
        elif (source is not None or 'first_available_file' in inject) and content is not None:
            result=dict(failed=True, msg="src and content are mutually exclusive")
            return ReturnData(conn=conn, result=result)

        # Check if the source ends with a "/"
        source_trailing_slash = False
        if source:
            source_trailing_slash = source.endswith("/")

        # Define content_tempfile in case we set it after finding content populated.
        content_tempfile = None

        # If content is defined make a temp file and write the content into it.
        if content is not None:
            try:
                # If content comes to us as a dict it should be decoded json.
                # We need to encode it back into a string to write it out.
                if type(content) is dict:
                    content_tempfile = self._create_content_tempfile(json.dumps(content))
                else:
                    content_tempfile = self._create_content_tempfile(content)
                source = content_tempfile
            except Exception, err:
                result = dict(failed=True, msg="could not write content temp file: %s" % err)
                return ReturnData(conn=conn, result=result)
        # if we have first_available_file in our vars
        # look up the files and use the first one we find as src
        elif 'first_available_file' in inject:
            found = False
            for fn in inject.get('first_available_file'):
                fn_orig = fn
                fnt = template.template(self.runner.basedir, fn, inject)
                fnd = utils.path_dwim(self.runner.basedir, fnt)
                if not os.path.exists(fnd) and '_original_file' in inject:
                    fnd = utils.path_dwim_relative(inject['_original_file'], 'files', fnt, self.runner.basedir, check=False)
                if os.path.exists(fnd):
                    source = fnd
                    found = True
                    break
            if not found:
                results = dict(failed=True, msg="could not find src in first_available_file list")
                return ReturnData(conn=conn, result=results)
        else:
            source = template.template(self.runner.basedir, source, inject)
            if '_original_file' in inject:
                source = utils.path_dwim_relative(inject['_original_file'], 'files', source, self.runner.basedir)
            else:
                source = utils.path_dwim(self.runner.basedir, source)

        # A list of source file tuples (full_path, relative_path) which will try to copy to the destination
        source_files = []

        # If source is a directory populate our list else source is a file and translate it to a tuple.
        if os.path.isdir(source):
            # Get the amount of spaces to remove to get the relative path.
            if source_trailing_slash:
                sz = len(source) + 1
            else:
                sz = len(source.rsplit('/', 1)[0]) + 1

            # Walk the directory and append the file tuples to source_files.
            for base_path, sub_folders, files in os.walk(source):
                for file in files:
                    full_path = os.path.join(base_path, file)
                    rel_path = full_path[sz:]
                    source_files.append((full_path, rel_path))

            # If it's recursive copy, destination is always a dir,
            # explicitly mark it so (note - copy module relies on this).
            if not dest.endswith("/"):
                dest += "/"
        else:
            source_files.append((source, os.path.basename(source)))

        changed = False
        diffs = []
        module_result = {"changed": False}

        # A register for if we executed a module.
        # Used to cut down on command calls when not recursive.
        module_executed = False

        # Tell _execute_module to delete the file if there is one file.
        delete_remote_tmp = (len(source_files) == 1)

        # If this is a recursive action create a tmp_path that we can share as the _exec_module create is too late.
        if not delete_remote_tmp:
            if "-tmp-" not in tmp_path:
                tmp_path = self.runner._make_tmp_path(conn)

        for source_full, source_rel in source_files:
            # Generate the MD5 hash of the local file.
            local_md5 = utils.md5(source_full)

            # If local_md5 is not defined we can't find the file so we should fail out.
            if local_md5 is None:
                result = dict(failed=True, msg="could not find src=%s" % source_full)
                return ReturnData(conn=conn, result=result)

            # This is kind of optimization - if user told us destination is
            # dir, do path manipulation right away, otherwise we still check
            # for dest being a dir via remote call below.
            if dest.endswith("/"):
                dest_file = os.path.join(dest, source_rel)
            else:
                dest_file = dest

            # Attempt to get the remote MD5 Hash.
            remote_md5 = self.runner._remote_md5(conn, tmp_path, dest_file)

            if remote_md5 == '3':
                # The remote_md5 was executed on a directory.
                if content is not None:
                    # If source was defined as content remove the temporary file and fail out.
                    self._remove_tempfile_if_content_defined(content, content_tempfile)
                    result = dict(failed=True, msg="can not use content with a dir as dest")
                    return ReturnData(conn=conn, result=result)
                else:
                    # Append the relative source location to the destination and retry remote_md5.
                    dest_file = os.path.join(dest, source_rel)
                    remote_md5 = self.runner._remote_md5(conn, tmp_path, dest_file)

            if remote_md5 != '1' and not force:
                # remote_file does not exist so continue to next iteration.
                continue

            if local_md5 != remote_md5:
                # The MD5 hashes don't match and we will change or error out.
                changed = True

                # Create a tmp_path if missing only if this is not recursive.
                # If this is recursive we already have a tmp_path.
                if delete_remote_tmp:
                    if "-tmp-" not in tmp_path:
                        tmp_path = self.runner._make_tmp_path(conn)

                if self.runner.diff and not raw:
                    diff = self._get_diff_data(conn, tmp_path, inject, dest_file, source_full)
                else:
                    diff = {}

                if self.runner.noop_on_check(inject):
                    self._remove_tempfile_if_content_defined(content, content_tempfile)
                    diffs.append(diff)
                    changed = True
                    module_result = dict(changed=True)
                    continue

                # Define a remote directory that we will copy the file to.
                tmp_src = tmp_path + 'source'

                if not raw:
                    conn.put_file(source_full, tmp_src)
                else:
                    conn.put_file(source_full, dest_file)

                # We have copied the file remotely and no longer require our content_tempfile
                self._remove_tempfile_if_content_defined(content, content_tempfile)

                # fix file permissions when the copy is done as a different user
                if self.runner.sudo and self.runner.sudo_user != 'root' and not raw:
                    self.runner._low_level_exec_command(conn, "chmod a+r %s" % tmp_src, tmp_path)

                if raw:
                    # Continue to next iteration if raw is defined.
                    continue

                # Run the copy module

                # src and dest here come after original and override them
                # we pass dest only to make sure it includes trailing slash in case of recursive copy
                module_args_tmp = "%s src=%s dest=%s original_basename=%s" % (module_args,
                                  pipes.quote(tmp_src), pipes.quote(dest), pipes.quote(source_rel))

                if self.runner.no_log:
                    module_args_tmp = "%s NO_LOG=True" % module_args_tmp

                module_return = self.runner._execute_module(conn, tmp_path, 'copy', module_args_tmp, inject=inject, complex_args=complex_args, delete_remote_tmp=delete_remote_tmp)
                module_executed = True

            else:
                # no need to transfer the file, already correct md5, but still need to call
                # the file module in case we want to change attributes
                self._remove_tempfile_if_content_defined(content, content_tempfile)

                if raw:
                    # Continue to next iteration if raw is defined.
                    # self.runner._remove_tmp_path(conn, tmp_path)
                    continue

                tmp_src = tmp_path + source_rel

                # Build temporary module_args.
                module_args_tmp = "%s src=%s original_basename=%s" % (module_args,
                                  pipes.quote(tmp_src), pipes.quote(source_rel))
                if self.runner.noop_on_check(inject):
                    module_args_tmp = "%s CHECKMODE=True" % module_args_tmp
                if self.runner.no_log:
                    module_args_tmp = "%s NO_LOG=True" % module_args_tmp

                # Execute the file module.
                module_return = self.runner._execute_module(conn, tmp_path, 'file', module_args_tmp, inject=inject, complex_args=complex_args, delete_remote_tmp=delete_remote_tmp)
                module_executed = True

            module_result = module_return.result
            if not module_result.get('md5sum'):
                module_result['md5sum'] = local_md5
            if module_result.get('failed') == True:
                return module_return
            if module_result.get('changed') == True:
                changed = True

        # Delete tmp_path if we were recursive or if we did not execute a module.
        if (not C.DEFAULT_KEEP_REMOTE_FILES and not delete_remote_tmp) \
            or (not C.DEFAULT_KEEP_REMOTE_FILES and delete_remote_tmp and not module_executed):
            self.runner._remove_tmp_path(conn, tmp_path)

        # the file module returns the file path as 'path', but 
        # the copy module uses 'dest', so add it if it's not there
        if 'path' in module_result and 'dest' not in module_result:
            module_result['dest'] = module_result['path']

        # TODO: Support detailed status/diff for multiple files
        if len(source_files) == 1:
            result = module_result
        else:
            result = dict(dest=dest, src=source, changed=changed)
        if len(diffs) == 1:
            return ReturnData(conn=conn, result=result, diff=diffs[0])
        else:
            return ReturnData(conn=conn, result=result)

    def _create_content_tempfile(self, content):
        ''' Create a tempfile containing defined content '''
        fd, content_tempfile = tempfile.mkstemp()
        f = os.fdopen(fd, 'w')
        try:
            f.write(content)
        except Exception, err:
            os.remove(content_tempfile)
            raise Exception(err)
        finally:
            f.close()
        return content_tempfile

    def _get_diff_data(self, conn, tmp, inject, destination, source):
        peek_result = self.runner._execute_module(conn, tmp, 'file', "path=%s diff_peek=1" % destination, inject=inject, persist_files=True)

        if not peek_result.is_successful():
            return {}

        diff = {}
        if peek_result.result['state'] == 'absent':
            diff['before'] = ''
        elif peek_result.result['appears_binary']:
            diff['dst_binary'] = 1
        elif peek_result.result['size'] > utils.MAX_FILE_SIZE_FOR_DIFF:
            diff['dst_larger'] = utils.MAX_FILE_SIZE_FOR_DIFF
        else:
            dest_result = self.runner._execute_module(conn, tmp, 'slurp', "path=%s" % destination, inject=inject, persist_files=True)
            if 'content' in dest_result.result:
                dest_contents = dest_result.result['content']
                if dest_result.result['encoding'] == 'base64':
                    dest_contents = base64.b64decode(dest_contents)
                else:
                    raise Exception("unknown encoding, failed: %s" % dest_result.result)
                diff['before_header'] = destination
                diff['before'] = dest_contents

        src = open(source)
        src_contents = src.read(8192)
        st = os.stat(source)
        if "\x00" in src_contents:
            diff['src_binary'] = 1
        elif st[stat.ST_SIZE] > utils.MAX_FILE_SIZE_FOR_DIFF:
            diff['src_larger'] = utils.MAX_FILE_SIZE_FOR_DIFF
        else:
            src.seek(0)
            diff['after_header'] = source
            diff['after'] = src.read()

        return diff

    def _remove_tempfile_if_content_defined(self, content, content_tempfile):
        if content is not None:
            os.remove(content_tempfile)

    
    def _result_key_merge(self, options, results):
        # add keys to file module results to mimic copy
        if 'path' in results.result and 'dest' not in results.result:
            results.result['dest'] = results.result['path']
            del results.result['path']
        return results

########NEW FILE########
__FILENAME__ = debug
# Copyright 2012, Dag Wieers <dag@wieers.com>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

import ansible

from ansible import utils
from ansible.utils import template
from ansible.runner.return_data import ReturnData

class ActionModule(object):
    ''' Print statements during execution '''

    TRANSFERS_FILES = False

    def __init__(self, runner):
        self.runner = runner
        self.basedir = runner.basedir

    def run(self, conn, tmp, module_name, module_args, inject, complex_args=None, **kwargs):
        args = {}
        if complex_args:
            args.update(complex_args)

        # attempt to prevent confusing messages when the variable didn't interpolate
        module_args = module_args.replace("{{ ","{{").replace(" }}","}}")

        kv = utils.parse_kv(module_args)
        args.update(kv)

        if not 'msg' in args and not 'var' in args:
            args['msg'] = 'Hello world!'

        result = {}
        if 'msg' in args:
            if 'fail' in args and utils.boolean(args['fail']):
                result = dict(failed=True, msg=args['msg'])
            else:
                result = dict(msg=args['msg'])
        elif 'var' in args:
            results = template.template(self.basedir, "{{ %s }}" % args['var'], inject)
            result[args['var']] = results

        # force flag to make debug output module always verbose
        result['verbose_always'] = True

        return ReturnData(conn=conn, result=result)

########NEW FILE########
__FILENAME__ = fail
# Copyright 2012, Dag Wieers <dag@wieers.com>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

import ansible

from ansible import utils
from ansible.runner.return_data import ReturnData

class ActionModule(object):
    ''' Fail with custom message '''

    TRANSFERS_FILES = False

    def __init__(self, runner):
        self.runner = runner

    def run(self, conn, tmp, module_name, module_args, inject, complex_args=None, **kwargs):

        # note: the fail module does not need to pay attention to check mode
        # it always runs.

        args = {}
        if complex_args:
            args.update(complex_args)
        args.update(utils.parse_kv(module_args))
        if not 'msg' in args:
            args['msg'] = 'Failed as requested from task'

        result = dict(failed=True, msg=args['msg'])
        return ReturnData(conn=conn, result=result)

########NEW FILE########
__FILENAME__ = fetch
# (c) 2012-2014, Michael DeHaan <michael.dehaan@gmail.com>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

import os
import pwd
import random
import traceback
import tempfile
import base64

import ansible.constants as C
from ansible import utils
from ansible import errors
from ansible import module_common
from ansible.runner.return_data import ReturnData

class ActionModule(object):

    def __init__(self, runner):
        self.runner = runner

    def run(self, conn, tmp, module_name, module_args, inject, complex_args=None, **kwargs):
        ''' handler for fetch operations '''

        if self.runner.noop_on_check(inject):
            return ReturnData(conn=conn, comm_ok=True, result=dict(skipped=True, msg='check mode not (yet) supported for this module'))

        # load up options
        options = {}
        if complex_args:
            options.update(complex_args)
        options.update(utils.parse_kv(module_args))
        source = options.get('src', None)
        dest = options.get('dest', None)
        flat = options.get('flat', False)
        flat = utils.boolean(flat)
        fail_on_missing = options.get('fail_on_missing', False)
        fail_on_missing = utils.boolean(fail_on_missing)
        validate_md5 = options.get('validate_md5', True)
        validate_md5 = utils.boolean(validate_md5)
        if source is None or dest is None:
            results = dict(failed=True, msg="src and dest are required")
            return ReturnData(conn=conn, result=results)

        source = os.path.expanduser(source)

        if flat:
            if dest.endswith("/"):
                # if the path ends with "/", we'll use the source filename as the
                # destination filename
                base = os.path.basename(source)
                dest = os.path.join(dest, base)
            if not dest.startswith("/"):
                # if dest does not start with "/", we'll assume a relative path
                dest = utils.path_dwim(self.runner.basedir, dest)
        else:
            # files are saved in dest dir, with a subdir for each host, then the filename
            dest = "%s/%s/%s" % (utils.path_dwim(self.runner.basedir, dest), conn.host, source)

        dest = os.path.expanduser(dest.replace("//","/"))

        # calculate md5 sum for the remote file
        remote_md5 = self.runner._remote_md5(conn, tmp, source)

        # use slurp if sudo and permissions are lacking
        remote_data = None
        if remote_md5 in ('1', '2') or self.runner.sudo:
            slurpres = self.runner._execute_module(conn, tmp, 'slurp', 'src=%s' % source, inject=inject)
            if slurpres.is_successful():
                if slurpres.result['encoding'] == 'base64':
                    remote_data = base64.b64decode(slurpres.result['content'])
                if remote_data is not None:
                    remote_md5 = utils.md5s(remote_data)

        # these don't fail because you may want to transfer a log file that possibly MAY exist
        # but keep going to fetch other log files
        if remote_md5 == '0':
            result = dict(msg="unable to calculate the md5 sum of the remote file", file=source, changed=False)
            return ReturnData(conn=conn, result=result)
        if remote_md5 == '1':
            if fail_on_missing:
                result = dict(failed=True, msg="the remote file does not exist", file=source)
            else:
                result = dict(msg="the remote file does not exist, not transferring, ignored", file=source, changed=False)
            return ReturnData(conn=conn, result=result)
        if remote_md5 == '2':
            result = dict(msg="no read permission on remote file, not transferring, ignored", file=source, changed=False)
            return ReturnData(conn=conn, result=result)

        # calculate md5 sum for the local file
        local_md5 = utils.md5(dest)

        if remote_md5 != local_md5:
            # create the containing directories, if needed
            if not os.path.isdir(os.path.dirname(dest)):
                os.makedirs(os.path.dirname(dest))

            # fetch the file and check for changes
            if remote_data is None:
                conn.fetch_file(source, dest)
            else:
                f = open(dest, 'w')
                f.write(remote_data)
                f.close()
            new_md5 = utils.md5(dest)
            if validate_md5 and new_md5 != remote_md5:
                result = dict(failed=True, md5sum=new_md5, msg="md5 mismatch", file=source, dest=dest, remote_md5sum=remote_md5)
                return ReturnData(conn=conn, result=result)
            result = dict(changed=True, md5sum=new_md5, dest=dest, remote_md5sum=remote_md5)
            return ReturnData(conn=conn, result=result)
        else:
            result = dict(changed=False, md5sum=local_md5, file=source, dest=dest)
            return ReturnData(conn=conn, result=result)


########NEW FILE########
__FILENAME__ = group_by
# Copyright 2012, Jeroen Hoekx <jeroen@hoekx.be>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

import ansible

from ansible.callbacks import vv
from ansible.errors import AnsibleError as ae
from ansible.runner.return_data import ReturnData
from ansible.utils import parse_kv, check_conditional
import ansible.utils.template as template

class ActionModule(object):
    ''' Create inventory groups based on variables '''

    ### We need to be able to modify the inventory
    BYPASS_HOST_LOOP = True
    TRANSFERS_FILES = False

    def __init__(self, runner):
        self.runner = runner

    def run(self, conn, tmp, module_name, module_args, inject, complex_args=None, **kwargs):

        # the group_by module does not need to pay attention to check mode.
        # it always runs.

        # module_args and complex_args have already been templated for the first host.
        # Use them here only to check that a key argument is provided.
        args = {}
        if complex_args:
            args.update(complex_args)
        args.update(parse_kv(module_args))
        if not 'key' in args:
            raise ae("'key' is a required argument.")

        vv("created 'group_by' ActionModule: key=%s"%(args['key']))

        inventory = self.runner.inventory

        result = {'changed': False}

        ### find all groups
        groups = {}

        for host in self.runner.host_set:
            data = {}
            data.update(inject)
            data.update(inject['hostvars'][host])
            conds = self.runner.conditional
            if type(conds) != list:
                conds = [ conds ]
            next_host = False
            for cond in conds:
                if not check_conditional(cond, self.runner.basedir, data, fail_on_undefined=self.runner.error_on_undefined_vars):
                    next_host = True
                    break
            if next_host:
                continue

            # Template original module_args and complex_args from runner for each host.
            host_module_args = template.template(self.runner.basedir, self.runner.module_args, data)
            host_complex_args = template.template(self.runner.basedir, self.runner.complex_args, data)
            host_args  = {}
            if host_complex_args:
                host_args.update(host_complex_args)
            host_args.update(parse_kv(host_module_args))

            group_name = host_args['key']
            group_name = group_name.replace(' ','-')
            if group_name not in groups:
                groups[group_name] = []
            groups[group_name].append(host)

        result['groups'] = groups

        ### add to inventory
        for group, hosts in groups.items():
            inv_group = inventory.get_group(group)
            if not inv_group:
                inv_group = ansible.inventory.Group(name=group)
                inventory.add_group(inv_group)
            for host in hosts:
                if host in self.runner.inventory._vars_per_host:
                    del self.runner.inventory._vars_per_host[host]
                inv_host = inventory.get_host(host)
                if not inv_host:
                    inv_host = ansible.inventory.Host(name=host)
                if inv_group not in inv_host.get_groups():
                    result['changed'] = True
                    inv_group.add_host(inv_host)

        return ReturnData(conn=conn, comm_ok=True, result=result)

########NEW FILE########
__FILENAME__ = include_vars
# (c) 2013-2014, Benno Joy <benno@ansible.com>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

import os
from ansible.utils import template
from ansible import utils
from ansible import errors
from ansible.runner.return_data import ReturnData

class ActionModule(object):

    TRANSFERS_FILES = False

    def __init__(self, runner):
        self.runner = runner

    def run(self, conn, tmp, module_name, module_args, inject, complex_args=None, **kwargs):

        if not module_args:
            result = dict(failed=True, msg="No source file given")
            return ReturnData(conn=conn, comm_ok=True, result=result)

        source = module_args
        source = template.template(self.runner.basedir, source, inject)

        if '_original_file' in inject:
            source = utils.path_dwim_relative(inject['_original_file'], 'vars', source, self.runner.basedir)
        else:
            source = utils.path_dwim(self.runner.basedir, source)

        if os.path.exists(source):
            data = utils.parse_yaml_from_file(source, vault_password=self.runner.vault_pass)
            if type(data) != dict:
                raise errors.AnsibleError("%s must be stored as a dictionary/hash" % source)
            result = dict(ansible_facts=data)
            return ReturnData(conn=conn, comm_ok=True, result=result)
        else:
            result = dict(failed=True, msg="Source file not found.", file=source)
            return ReturnData(conn=conn, comm_ok=True, result=result)


########NEW FILE########
__FILENAME__ = normal
# (c) 2012, Michael DeHaan <michael.dehaan@gmail.com>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

import os
import pwd
import random
import traceback
import tempfile

import ansible.constants as C
from ansible import utils
from ansible import errors
from ansible import module_common
from ansible.runner.return_data import ReturnData
from ansible.callbacks import vv, vvv

class ActionModule(object):

    def __init__(self, runner):
        self.runner = runner

    def run(self, conn, tmp, module_name, module_args, inject, complex_args=None, **kwargs):
        ''' transfer & execute a module that is not 'copy' or 'template' '''

        module_args = self.runner._complex_args_hack(complex_args, module_args)

        if self.runner.noop_on_check(inject):
            if module_name in [ 'shell', 'command' ]:
                return ReturnData(conn=conn, comm_ok=True, result=dict(skipped=True, msg='check mode not supported for %s' % module_name))
            # else let the module parsing code decide, though this will only be allowed for AnsibleModuleCommon using
            # python modules for now
            module_args += " CHECKMODE=True"

        if self.runner.no_log:
            module_args += " NO_LOG=True"

        # shell and command are the same module
        if module_name == 'shell':
            module_name = 'command'
            module_args += " #USE_SHELL"

        vv("REMOTE_MODULE %s %s" % (module_name, module_args), host=conn.host)
        return self.runner._execute_module(conn, tmp, module_name, module_args, inject=inject, complex_args=complex_args)



########NEW FILE########
__FILENAME__ = pause
# Copyright 2012, Tim Bielawa <tbielawa@redhat.com>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

from ansible.callbacks import vv
from ansible.errors import AnsibleError as ae
from ansible.runner.return_data import ReturnData
from ansible.utils import getch, parse_kv
import ansible.utils.template as template
from termios import tcflush, TCIFLUSH
import datetime
import sys
import time


class ActionModule(object):
    ''' pauses execution for a length or time, or until input is received '''

    PAUSE_TYPES = ['seconds', 'minutes', 'prompt', '']
    BYPASS_HOST_LOOP = True

    def __init__(self, runner):
        self.runner = runner
        # Set defaults
        self.duration_unit = 'minutes'
        self.prompt = None
        self.seconds = None
        self.result = {'changed': False,
                       'rc': 0,
                       'stderr': '',
                       'stdout': '',
                       'start': None,
                       'stop': None,
                       'delta': None,
                       }

    def run(self, conn, tmp, module_name, module_args, inject, complex_args=None, **kwargs):
        ''' run the pause action module '''

        # note: this module does not need to pay attention to the 'check'
        # flag, it always runs

        hosts = ', '.join(self.runner.host_set)
        args = {}
        if complex_args:
            args.update(complex_args)
        # extra template call unneeded?
        args.update(parse_kv(template.template(self.runner.basedir, module_args, inject)))

        # Are 'minutes' or 'seconds' keys that exist in 'args'?
        if 'minutes' in args or 'seconds' in args:
            try:
                if 'minutes' in args:
                    self.pause_type = 'minutes'
                    # The time() command operates in seconds so we need to
                    # recalculate for minutes=X values.
                    self.seconds = int(args['minutes']) * 60
                else:
                    self.pause_type = 'seconds'
                    self.seconds = int(args['seconds'])
                    self.duration_unit = 'seconds'
            except ValueError, e:
                raise ae("non-integer value given for prompt duration:\n%s" % str(e))
        # Is 'prompt' a key in 'args'?
        elif 'prompt' in args:
            self.pause_type = 'prompt'
            self.prompt = "[%s]\n%s:\n" % (hosts, args['prompt'])
        # Is 'args' empty, then this is the default prompted pause
        elif len(args.keys()) == 0:
            self.pause_type = 'prompt'
            self.prompt = "[%s]\nPress enter to continue:\n" % hosts
        # I have no idea what you're trying to do. But it's so wrong.
        else:
            raise ae("invalid pause type given. must be one of: %s" % \
                         ", ".join(self.PAUSE_TYPES))

        vv("created 'pause' ActionModule: pause_type=%s, duration_unit=%s, calculated_seconds=%s, prompt=%s" % \
                (self.pause_type, self.duration_unit, self.seconds, self.prompt))

        ########################################################################
        # Begin the hard work!
        try:
            self._start()
            if not self.pause_type == 'prompt':
                print "[%s]\nPausing for %s seconds" % (hosts, self.seconds)
                time.sleep(self.seconds)
            else:
                # Clear out any unflushed buffered input which would
                # otherwise be consumed by raw_input() prematurely.
                tcflush(sys.stdin, TCIFLUSH)
                self.result['user_input'] = raw_input(self.prompt.encode(sys.stdout.encoding))
        except KeyboardInterrupt:
            while True:
                print '\nAction? (a)bort/(c)ontinue: '
                c = getch()
                if c == 'c':
                    # continue playbook evaluation
                    break
                elif c == 'a':
                    # abort further playbook evaluation
                    raise ae('user requested abort!')
        finally:
            self._stop()

        return ReturnData(conn=conn, result=self.result)

    def _start(self):
        ''' mark the time of execution for duration calculations later '''
        self.start = time.time()
        self.result['start'] = str(datetime.datetime.now())
        if not self.pause_type == 'prompt':
            print "(^C-c = continue early, ^C-a = abort)"

    def _stop(self):
        ''' calculate the duration we actually paused for and then
        finish building the task result string '''
        duration = time.time() - self.start
        self.result['stop'] = str(datetime.datetime.now())
        self.result['delta'] = int(duration)

        if self.duration_unit == 'minutes':
            duration = round(duration / 60.0, 2)
        else:
            duration = round(duration, 2)

        self.result['stdout'] = "Paused for %s %s" % (duration, self.duration_unit)

########NEW FILE########
__FILENAME__ = raw
# (c) 2012, Michael DeHaan <michael.dehaan@gmail.com>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

import re

import ansible.constants as C
from ansible import utils
from ansible import errors
from ansible.runner.return_data import ReturnData

class ActionModule(object):
    TRANSFERS_FILES = False

    def __init__(self, runner):
        self.runner = runner

    def run(self, conn, tmp, module_name, module_args, inject, complex_args=None, **kwargs):

        if self.runner.noop_on_check(inject):
            # in --check mode, always skip this module execution
            return ReturnData(conn=conn, comm_ok=True, result=dict(skipped=True))

        executable = ''
        # From library/command, keep in sync
        r = re.compile(r'(^|\s)(executable)=(?P<quote>[\'"])?(.*?)(?(quote)(?<!\\)(?P=quote))((?<!\\)\s|$)')
        for m in r.finditer(module_args):
            v = m.group(4).replace("\\", "")
            if m.group(2) == "executable":
                executable = v
        module_args = r.sub("", module_args)

        result = self.runner._low_level_exec_command(conn, module_args, tmp, sudoable=True, executable=executable,
                                                     su=self.runner.su)
        # for some modules (script, raw), the sudo success key
        # may leak into the stdout due to the way the sudo/su
        # command is constructed, so we filter that out here
        if result.get('stdout','').strip().startswith('SUDO-SUCCESS-'):
            result['stdout'] = re.sub(r'^(\r)?\nSUDO-SUCCESS.*(\r)?\n', '', result['stdout'])

        return ReturnData(conn=conn, result=result)

########NEW FILE########
__FILENAME__ = script
# (c) 2012, Michael DeHaan <michael.dehaan@gmail.com>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

import os
import re
import shlex

import ansible.constants as C
from ansible.utils import template
from ansible import utils
from ansible import errors
from ansible.runner.return_data import ReturnData


class ActionModule(object):
    TRANSFERS_FILES = True

    def __init__(self, runner):
        self.runner = runner

    def run(self, conn, tmp, module_name, module_args, inject, complex_args=None, **kwargs):
        ''' handler for file transfer operations '''

        if self.runner.noop_on_check(inject):
            # in check mode, always skip this module
            return ReturnData(conn=conn, comm_ok=True,
                              result=dict(skipped=True, msg='check mode not supported for this module'))

        # extract ansible reserved parameters
        # From library/command keep in sync
        creates = None
        removes = None
        r = re.compile(r'(^|\s)(creates|removes)=(?P<quote>[\'"])?(.*?)(?(quote)(?<!\\)(?P=quote))((?<!\\)(?=\s)|$)')
        for m in r.finditer(module_args):
            v = m.group(4).replace("\\", "")
            if m.group(2) == "creates":
                creates = v
            elif m.group(2) == "removes":
                removes = v
        module_args = r.sub("", module_args)

        if creates:
            # do not run the command if the line contains creates=filename
            # and the filename already exists. This allows idempotence
            # of command executions.
            module_args_tmp = "path=%s" % creates
            module_return = self.runner._execute_module(conn, tmp, 'stat', module_args_tmp, inject=inject,
                                                        complex_args=complex_args, persist_files=True)
            stat = module_return.result.get('stat', None)
            if stat and stat.get('exists', False):
                return ReturnData(
                    conn=conn,
                    comm_ok=True,
                    result=dict(
                        skipped=True,
                        msg=("skipped, since %s exists" % creates)
                    )
                )
        if removes:
            # do not run the command if the line contains removes=filename
            # and the filename does not exist. This allows idempotence
            # of command executions.
            module_args_tmp = "path=%s" % removes
            module_return = self.runner._execute_module(conn, tmp, 'stat', module_args_tmp, inject=inject,
                                                        complex_args=complex_args, persist_files=True)
            stat = module_return.result.get('stat', None)
            if stat and not stat.get('exists', False):
                return ReturnData(
                    conn=conn,
                    comm_ok=True,
                    result=dict(
                        skipped=True,
                        msg=("skipped, since %s does not exist" % removes)
                    )
                )

        # Decode the result of shlex.split() to UTF8 to get around a bug in that's been fixed in Python 2.7 but not Python 2.6.
        # See: http://bugs.python.org/issue6988
        tokens = shlex.split(module_args.encode('utf8'))
        tokens = [s.decode('utf8') for s in tokens]
        # extract source script
        source = tokens[0]

        # FIXME: error handling
        args = " ".join(tokens[1:])
        source = template.template(self.runner.basedir, source, inject)
        if '_original_file' in inject:
            source = utils.path_dwim_relative(inject['_original_file'], 'files', source, self.runner.basedir)
        else:
            source = utils.path_dwim(self.runner.basedir, source)

        # transfer the file to a remote tmp location
        source = source.replace('\x00', '')  # why does this happen here?
        args = args.replace('\x00', '')  # why does this happen here?
        tmp_src = os.path.join(tmp, os.path.basename(source))
        tmp_src = tmp_src.replace('\x00', '')

        conn.put_file(source, tmp_src)

        sudoable = True
        # set file permissions, more permisive when the copy is done as a different user
        if ((self.runner.sudo and self.runner.sudo_user != 'root') or
                (self.runner.su and self.runner.su_user != 'root')):
            cmd_args_chmod = "chmod a+rx %s" % tmp_src
            sudoable = False
        else:
            cmd_args_chmod = "chmod +rx %s" % tmp_src
        self.runner._low_level_exec_command(conn, cmd_args_chmod, tmp, sudoable=sudoable, su=self.runner.su)

        # add preparation steps to one ssh roundtrip executing the script
        env_string = self.runner._compute_environment_string(inject)
        module_args = env_string + tmp_src + ' ' + args

        handler = utils.plugins.action_loader.get('raw', self.runner)
        result = handler.run(conn, tmp, 'raw', module_args, inject)

        # clean up after
        if "tmp" in tmp and not C.DEFAULT_KEEP_REMOTE_FILES:
            self.runner._low_level_exec_command(conn, 'rm -rf %s >/dev/null 2>&1' % tmp, tmp)

        result.result['changed'] = True

        return result

########NEW FILE########
__FILENAME__ = set_fact
# Copyright 2013 Dag Wieers <dag@wieers.com>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

from ansible import utils
from ansible.runner.return_data import ReturnData

class ActionModule(object):

    TRANSFERS_FILES = False

    def __init__(self, runner):
        self.runner = runner

    def run(self, conn, tmp, module_name, module_args, inject, complex_args=None, **kwargs):
        ''' handler for running operations on master '''

        # load up options
        options  = {}
        if complex_args:
            options.update(complex_args)
        options.update(utils.parse_kv(module_args))

        return ReturnData(conn=conn, result=dict(ansible_facts=options))

########NEW FILE########
__FILENAME__ = synchronize
#!/usr/bin/python
# -*- coding: utf-8 -*-

# (c) 2012-2013, Timothy Appnel <tim@appnel.com>
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

import os.path

from ansible import utils
from ansible.runner.return_data import ReturnData
import ansible.utils.template as template

class ActionModule(object):

    def __init__(self, runner):
        self.runner = runner
        self.inject = None

    def _get_absolute_path(self, path=None):
        if 'vars' in self.inject:
            if '_original_file' in self.inject['vars']:
                # roles
                original_path = path
                path = utils.path_dwim_relative(self.inject['_original_file'], 'files', path, self.runner.basedir)
                if original_path and original_path[-1] == '/' and path[-1] != '/':
                    # make sure the dwim'd path ends in a trailing "/"
                    # if the original path did
                    path += '/'

        return path

    def _process_origin(self, host, path, user):

        if not host in ['127.0.0.1', 'localhost']:
            if user:
                return '%s@%s:%s' % (user, host, path)
            else:
                return '%s:%s' % (host, path)
        else:
            if not ':' in path:
                if not path.startswith('/'):
                    path = self._get_absolute_path(path=path)
            return path

    def _process_remote(self, host, path, user):
        transport = self.runner.transport
        return_data = None
        if not host in ['127.0.0.1', 'localhost'] or transport != "local":
            if user:
                return_data = '%s@%s:%s' % (user, host, path)
            else:
                return_data = '%s:%s' % (host, path)
        else:
            return_data = path

        if not ':' in return_data:
            if not return_data.startswith('/'):
                return_data = self._get_absolute_path(path=return_data)

        return return_data

    def setup(self, module_name, inject):
        ''' Always default to localhost as delegate if None defined '''
   
        self.inject = inject
    
        # Store original transport and sudo values.
        self.original_transport = inject.get('ansible_connection', self.runner.transport)
        self.original_sudo = self.runner.sudo
        self.transport_overridden = False

        if inject.get('delegate_to') is None:
            inject['delegate_to'] = '127.0.0.1'
            # IF original transport is not local, override transport and disable sudo.
            if self.original_transport != 'local':
                inject['ansible_connection'] = 'local'
                self.transport_overridden = True
                self.runner.sudo = False

    def run(self, conn, tmp, module_name, module_args,
        inject, complex_args=None, **kwargs):

        ''' generates params and passes them on to the rsync module '''

        self.inject = inject

        # load up options
        options = {}
        if complex_args:
            options.update(complex_args)
        options.update(utils.parse_kv(module_args))

        src = options.get('src', None)
        dest = options.get('dest', None)

        src = template.template(self.runner.basedir, src, inject)
        dest = template.template(self.runner.basedir, dest, inject)

        try:
            options['local_rsync_path'] = inject['ansible_rsync_path']
        except KeyError:
            pass

        # from the perspective of the rsync call the delegate is the localhost
        src_host = '127.0.0.1'
        dest_host = inject.get('ansible_ssh_host', inject['inventory_hostname'])

        # allow ansible_ssh_host to be templated
        dest_host = template.template(self.runner.basedir, dest_host, inject, fail_on_undefined=True)
        dest_is_local = dest_host in ['127.0.0.1', 'localhost']

        # CHECK FOR NON-DEFAULT SSH PORT
        dest_port = options.get('dest_port')
        inv_port = inject.get('ansible_ssh_port', inject['inventory_hostname'])
        if inv_port != dest_port and inv_port != inject['inventory_hostname']:
            options['dest_port'] = inv_port

        # edge case: explicit delegate and dest_host are the same
        if dest_host == inject['delegate_to']:
            dest_host = '127.0.0.1'

        # SWITCH SRC AND DEST PER MODE
        if options.get('mode', 'push') == 'pull':
            (dest_host, src_host) = (src_host, dest_host)

        # CHECK DELEGATE HOST INFO
        use_delegate = False
        if conn.delegate != conn.host:
            if 'hostvars' in inject:
                if conn.delegate in inject['hostvars'] and self.original_transport != 'local':
                    # use a delegate host instead of localhost
                    use_delegate = True

        # COMPARE DELEGATE, HOST AND TRANSPORT                             
        process_args = False
        if not dest_host is src_host and self.original_transport != 'local':
            # interpret and inject remote host info into src or dest
            process_args = True

        # MUNGE SRC AND DEST PER REMOTE_HOST INFO
        if process_args or use_delegate:

            user = None
            if utils.boolean(options.get('set_remote_user', 'yes')):
                if use_delegate:
                    user = inject['hostvars'][conn.delegate].get('ansible_ssh_user')

                if not use_delegate or not user:
                    user = inject.get('ansible_ssh_user',
                                    self.runner.remote_user)
                
            if use_delegate:
                # FIXME
                private_key = inject.get('ansible_ssh_private_key_file', self.runner.private_key_file)
            else:
                private_key = inject.get('ansible_ssh_private_key_file', self.runner.private_key_file)

            private_key = template.template(self.runner.basedir, private_key, inject, fail_on_undefined=True)

            if not private_key is None:
                private_key = os.path.expanduser(private_key)
                options['private_key'] = private_key
                
            # use the mode to define src and dest's url
            if options.get('mode', 'push') == 'pull':
                # src is a remote path: <user>@<host>, dest is a local path
                src = self._process_remote(src_host, src, user)
                dest = self._process_origin(dest_host, dest, user)
            else:
                # src is a local path, dest is a remote path: <user>@<host>
                src = self._process_origin(src_host, src, user)
                dest = self._process_remote(dest_host, dest, user)

        options['src'] = src
        options['dest'] = dest
        if 'mode' in options:
            del options['mode']

        # Allow custom rsync path argument.
        rsync_path = options.get('rsync_path', None)

        # If no rsync_path is set, sudo was originally set, and dest is remote then add 'sudo rsync' argument.
        if not rsync_path and self.transport_overridden and self.original_sudo and not dest_is_local:
            rsync_path = 'sudo rsync'

        # make sure rsync path is quoted.
        if rsync_path:
            options['rsync_path'] = '"' + rsync_path + '"'

        module_args = ""
        if self.runner.noop_on_check(inject):
            module_args = "CHECKMODE=True"

        # run the module and store the result
        result = self.runner._execute_module(conn, tmp, 'synchronize', module_args, complex_args=options, inject=inject)

        # reset the sudo property                 
        self.runner.sudo = self.original_sudo

        return result


########NEW FILE########
__FILENAME__ = template
# (c) 2012, Michael DeHaan <michael.dehaan@gmail.com>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

import os
import pipes
from ansible.utils import template
from ansible import utils
from ansible import errors
from ansible.runner.return_data import ReturnData
import base64

class ActionModule(object):

    TRANSFERS_FILES = True

    def __init__(self, runner):
        self.runner = runner

    def run(self, conn, tmp, module_name, module_args, inject, complex_args=None, **kwargs):
        ''' handler for template operations '''

        # note: since this module just calls the copy module, the --check mode support
        # can be implemented entirely over there

        if not self.runner.is_playbook:
            raise errors.AnsibleError("in current versions of ansible, templates are only usable in playbooks")

        # load up options
        options  = {}
        if complex_args:
            options.update(complex_args)
        options.update(utils.parse_kv(module_args))

        source   = options.get('src', None)
        dest     = options.get('dest', None)

        if (source is None and 'first_available_file' not in inject) or dest is None:
            result = dict(failed=True, msg="src and dest are required")
            return ReturnData(conn=conn, comm_ok=False, result=result)

        # if we have first_available_file in our vars
        # look up the files and use the first one we find as src

        if 'first_available_file' in inject:
            found = False
            for fn in self.runner.module_vars.get('first_available_file'):
                fn_orig = fn
                fnt = template.template(self.runner.basedir, fn, inject)
                fnd = utils.path_dwim(self.runner.basedir, fnt)
                if not os.path.exists(fnd) and '_original_file' in inject:
                    fnd = utils.path_dwim_relative(inject['_original_file'], 'templates', fnt, self.runner.basedir, check=False)
                if os.path.exists(fnd):
                    source = fnd
                    found = True
                    break
            if not found:
                result = dict(failed=True, msg="could not find src in first_available_file list")
                return ReturnData(conn=conn, comm_ok=False, result=result)
        else:
            source = template.template(self.runner.basedir, source, inject)
                
            if '_original_file' in inject:
                source = utils.path_dwim_relative(inject['_original_file'], 'templates', source, self.runner.basedir)
            else:
                source = utils.path_dwim(self.runner.basedir, source)


        if dest.endswith("/"):
            base = os.path.basename(source)
            dest = os.path.join(dest, base)

        # template the source data locally & get ready to transfer
        try:
            resultant = template.template_from_file(self.runner.basedir, source, inject, vault_password=self.runner.vault_pass)
        except Exception, e:
            result = dict(failed=True, msg=str(e))
            return ReturnData(conn=conn, comm_ok=False, result=result)

        local_md5 = utils.md5s(resultant)
        remote_md5 = self.runner._remote_md5(conn, tmp, dest)

        if local_md5 != remote_md5:

            # template is different from the remote value

            # if showing diffs, we need to get the remote value
            dest_contents = ''

            if self.runner.diff:
                # using persist_files to keep the temp directory around to avoid needing to grab another
                dest_result = self.runner._execute_module(conn, tmp, 'slurp', "path=%s" % dest, inject=inject, persist_files=True)
                if 'content' in dest_result.result:
                    dest_contents = dest_result.result['content']
                    if dest_result.result['encoding'] == 'base64':
                        dest_contents = base64.b64decode(dest_contents)
                    else:
                        raise Exception("unknown encoding, failed: %s" % dest_result.result)
 
            xfered = self.runner._transfer_str(conn, tmp, 'source', resultant)

            # fix file permissions when the copy is done as a different user
            if self.runner.sudo and self.runner.sudo_user != 'root':
                self.runner._low_level_exec_command(conn, "chmod a+r %s" % xfered, tmp)

            # run the copy module
            module_args = "%s src=%s dest=%s original_basename=%s" % (module_args, pipes.quote(xfered), pipes.quote(dest), pipes.quote(os.path.basename(source)))

            if self.runner.noop_on_check(inject):
                return ReturnData(conn=conn, comm_ok=True, result=dict(changed=True), diff=dict(before_header=dest, after_header=source, before=dest_contents, after=resultant))
            else:
                res = self.runner._execute_module(conn, tmp, 'copy', module_args, inject=inject, complex_args=complex_args)
                if res.result.get('changed', False):
                    res.diff = dict(before=dest_contents, after=resultant)
                return res
        else:
            return self.runner._execute_module(conn, tmp, 'file', module_args, inject=inject, complex_args=complex_args)


########NEW FILE########
__FILENAME__ = unarchive
# (c) 2012, Michael DeHaan <michael.dehaan@gmail.com>
# (c) 2013, Dylan Martin <dmartin@seattlecentral.edu>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

import os

from ansible import utils
import ansible.utils.template as template
from ansible import errors
from ansible.runner.return_data import ReturnData

## fixes https://github.com/ansible/ansible/issues/3518
# http://mypy.pythonblogs.com/12_mypy/archive/1253_workaround_for_python_bug_ascii_codec_cant_encode_character_uxa0_in_position_111_ordinal_not_in_range128.html
import sys
reload(sys)
sys.setdefaultencoding("utf8")
import pipes


class ActionModule(object):

    TRANSFERS_FILES = True

    def __init__(self, runner):
        self.runner = runner

    def run(self, conn, tmp, module_name, module_args, inject, complex_args=None, **kwargs):
        ''' handler for file transfer operations '''

        # load up options
        options = {}
        if complex_args:
            options.update(complex_args)
        options.update(utils.parse_kv(module_args))
        source  = options.get('src', None)
        dest    = options.get('dest', None)
        copy    = utils.boolean(options.get('copy', 'yes'))

        if source is None or dest is None:
            result = dict(failed=True, msg="src (or content) and dest are required")
            return ReturnData(conn=conn, result=result)

        dest = os.path.expanduser(dest)
        source = template.template(self.runner.basedir, os.path.expanduser(source), inject)
        if copy:
            if '_original_file' in inject:
                source = utils.path_dwim_relative(inject['_original_file'], 'files', source, self.runner.basedir)
            else:
                source = utils.path_dwim(self.runner.basedir, source)

        remote_md5 = self.runner._remote_md5(conn, tmp, dest)
        if remote_md5 != '3':
            result = dict(failed=True, msg="dest '%s' must be an existing dir" % dest)
            return ReturnData(conn=conn, result=result)

        if copy:
            # transfer the file to a remote tmp location
            tmp_src = tmp + 'source'
            conn.put_file(source, tmp_src)

        # handle diff mode client side
        # handle check mode client side
        # fix file permissions when the copy is done as a different user
        if copy:
            if self.runner.sudo and self.runner.sudo_user != 'root':
                self.runner._low_level_exec_command(conn, "chmod a+r %s" % tmp_src, tmp)
            module_args = "%s src=%s original_basename=%s" % (module_args, pipes.quote(tmp_src), pipes.quote(os.path.basename(source)))
        else:
            module_args = "%s original_basename=%s" % (module_args, pipes.quote(os.path.basename(source)))
        return self.runner._execute_module(conn, tmp, 'unarchive', module_args, inject=inject, complex_args=complex_args)

########NEW FILE########
__FILENAME__ = connection
# (c) 2012-2013, Michael DeHaan <michael.dehaan@gmail.com>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.
#

################################################

from ansible import utils
from ansible.errors import AnsibleError
import ansible.constants as C

import os
import os.path

class Connection(object):
    ''' Handles abstract connections to remote hosts '''

    def __init__(self, runner):
        self.runner = runner

    def connect(self, host, port, user, password, transport, private_key_file):
        conn = None
        conn = utils.plugins.connection_loader.get(transport, self.runner, host, port, user=user, password=password, private_key_file=private_key_file)
        if conn is None:
            raise AnsibleError("unsupported connection type: %s" % transport)
        self.active = conn.connect()
        return self.active



########NEW FILE########
__FILENAME__ = accelerate
# (c) 2012, Michael DeHaan <michael.dehaan@gmail.com>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

import json
import os
import base64
import socket
import struct
import time
from ansible.callbacks import vvv, vvvv
from ansible.errors import AnsibleError, AnsibleFileNotFound
from ansible.runner.connection_plugins.ssh import Connection as SSHConnection
from ansible.runner.connection_plugins.paramiko_ssh import Connection as ParamikoConnection
from ansible import utils
from ansible import constants

# the chunk size to read and send, assuming mtu 1500 and
# leaving room for base64 (+33%) encoding and header (8 bytes)
# ((1400-8)/4)*3) = 1044
# which leaves room for the TCP/IP header. We set this to a 
# multiple of the value to speed up file reads.
CHUNK_SIZE=1044*20

class Connection(object):
    ''' raw socket accelerated connection '''

    def __init__(self, runner, host, port, user, password, private_key_file, *args, **kwargs):

        self.runner = runner
        self.host = host
        self.context = None
        self.conn = None
        self.user = user
        self.key = utils.key_for_hostname(host)
        self.port = port[0]
        self.accport = port[1]
        self.is_connected = False
        self.has_pipelining = False

        if not self.port:
            self.port = constants.DEFAULT_REMOTE_PORT
        elif not isinstance(self.port, int):
            self.port = int(self.port)

        if not self.accport:
            self.accport = constants.ACCELERATE_PORT
        elif not isinstance(self.accport, int):
            self.accport = int(self.accport)

        if self.runner.original_transport == "paramiko":
            self.ssh = ParamikoConnection(
                runner=self.runner,
                host=self.host,
                port=self.port,
                user=self.user,
                password=password,
                private_key_file=private_key_file
            )
        else:
            self.ssh = SSHConnection(
                runner=self.runner,
                host=self.host,
                port=self.port,
                user=self.user,
                password=password,
                private_key_file=private_key_file
            )

        # attempt to work around shared-memory funness
        if getattr(self.runner, 'aes_keys', None):
            utils.AES_KEYS = self.runner.aes_keys

    def _execute_accelerate_module(self):
        args = "password=%s port=%s minutes=%d debug=%d ipv6=%s" % (
            base64.b64encode(self.key.__str__()), 
            str(self.accport), 
            constants.ACCELERATE_DAEMON_TIMEOUT, 
            int(utils.VERBOSITY), 
            self.runner.accelerate_ipv6,
        )
        if constants.ACCELERATE_MULTI_KEY:
            args += " multi_key=yes"
        inject = dict(password=self.key)
        if getattr(self.runner, 'accelerate_inventory_host', False):
            inject = utils.combine_vars(inject, self.runner.inventory.get_variables(self.runner.accelerate_inventory_host))
        else:
            inject = utils.combine_vars(inject, self.runner.inventory.get_variables(self.host))
        vvvv("attempting to start up the accelerate daemon...")
        self.ssh.connect()
        tmp_path = self.runner._make_tmp_path(self.ssh)
        return self.runner._execute_module(self.ssh, tmp_path, 'accelerate', args, inject=inject)

    def connect(self, allow_ssh=True):
        ''' activates the connection object '''

        try:
            if not self.is_connected:
                wrong_user = False
                tries = 3
                self.conn = socket.socket()
                self.conn.settimeout(constants.ACCELERATE_CONNECT_TIMEOUT)
                vvvv("attempting connection to %s via the accelerated port %d" % (self.host,self.accport))
                while tries > 0:
                    try:
                        self.conn.connect((self.host,self.accport))
                        break
                    except socket.error:
                        vvvv("connection to %s failed, retrying..." % self.host)
                        time.sleep(0.1)
                        tries -= 1
                if tries == 0:
                    vvv("Could not connect via the accelerated connection, exceeded # of tries")
                    raise AnsibleError("FAILED")
                elif wrong_user:
                    vvv("Restarting daemon with a different remote_user")
                    raise AnsibleError("WRONG_USER")

                self.conn.settimeout(constants.ACCELERATE_TIMEOUT)
                if not self.validate_user():
                    # the accelerated daemon was started with a 
                    # different remote_user. The above command
                    # should have caused the accelerate daemon to
                    # shutdown, so we'll reconnect.
                    wrong_user = True

        except AnsibleError, e:
            if allow_ssh:
                if "WRONG_USER" in e:
                    vvv("Switching users, waiting for the daemon on %s to shutdown completely..." % self.host)
                    time.sleep(5)
                vvv("Falling back to ssh to startup accelerated mode")
                res = self._execute_accelerate_module()
                if not res.is_successful():
                    raise AnsibleError("Failed to launch the accelerated daemon on %s (reason: %s)" % (self.host,res.result.get('msg')))
                return self.connect(allow_ssh=False)
            else:
                raise AnsibleError("Failed to connect to %s:%s" % (self.host,self.accport))
        self.is_connected = True
        return self

    def send_data(self, data):
        packed_len = struct.pack('!Q',len(data))
        return self.conn.sendall(packed_len + data)

    def recv_data(self):
        header_len = 8 # size of a packed unsigned long long
        data = b""
        try:
            vvvv("%s: in recv_data(), waiting for the header" % self.host)
            while len(data) < header_len:
                d = self.conn.recv(header_len - len(data))
                if not d:
                    vvvv("%s: received nothing, bailing out" % self.host)
                    return None
                data += d
            vvvv("%s: got the header, unpacking" % self.host)
            data_len = struct.unpack('!Q',data[:header_len])[0]
            data = data[header_len:]
            vvvv("%s: data received so far (expecting %d): %d" % (self.host,data_len,len(data)))
            while len(data) < data_len:
                d = self.conn.recv(data_len - len(data))
                if not d:
                    vvvv("%s: received nothing, bailing out" % self.host)
                    return None
                vvvv("%s: received %d bytes" % (self.host, len(d)))
                data += d
            vvvv("%s: received all of the data, returning" % self.host)
            return data
        except socket.timeout:
            raise AnsibleError("timed out while waiting to receive data")

    def validate_user(self):
        '''
        Checks the remote uid of the accelerated daemon vs. the 
        one specified for this play and will cause the accel 
        daemon to exit if they don't match
        '''

        vvvv("%s: sending request for validate_user" % self.host)
        data = dict(
            mode='validate_user',
            username=self.user,
        )
        data = utils.jsonify(data)
        data = utils.encrypt(self.key, data)
        if self.send_data(data):
            raise AnsibleError("Failed to send command to %s" % self.host)

        vvvv("%s: waiting for validate_user response" % self.host)
        while True:
            # we loop here while waiting for the response, because a
            # long running command may cause us to receive keepalive packets
            # ({"pong":"true"}) rather than the response we want.
            response = self.recv_data()
            if not response:
                raise AnsibleError("Failed to get a response from %s" % self.host)
            response = utils.decrypt(self.key, response)
            response = utils.parse_json(response)
            if "pong" in response:
                # it's a keepalive, go back to waiting
                vvvv("%s: received a keepalive packet" % self.host)
                continue
            else:
                vvvv("%s: received the validate_user response: %s" % (self.host, response))
                break

        if response.get('failed'):
            return False
        else:
            return response.get('rc') == 0

    def exec_command(self, cmd, tmp_path, sudo_user=None, sudoable=False, executable='/bin/sh', in_data=None, su=None, su_user=None):
        ''' run a command on the remote host '''

        if su or su_user:
            raise AnsibleError("Internal Error: this module does not support running commands via su")

        if in_data:
            raise AnsibleError("Internal Error: this module does not support optimized module pipelining")

        if executable == "":
            executable = constants.DEFAULT_EXECUTABLE

        if self.runner.sudo and sudoable and sudo_user:
            cmd, prompt, success_key = utils.make_sudo_cmd(sudo_user, executable, cmd)

        vvv("EXEC COMMAND %s" % cmd)

        data = dict(
            mode='command',
            cmd=cmd,
            tmp_path=tmp_path,
            executable=executable,
        )
        data = utils.jsonify(data)
        data = utils.encrypt(self.key, data)
        if self.send_data(data):
            raise AnsibleError("Failed to send command to %s" % self.host)
        
        while True:
            # we loop here while waiting for the response, because a 
            # long running command may cause us to receive keepalive packets
            # ({"pong":"true"}) rather than the response we want. 
            response = self.recv_data()
            if not response:
                raise AnsibleError("Failed to get a response from %s" % self.host)
            response = utils.decrypt(self.key, response)
            response = utils.parse_json(response)
            if "pong" in response:
                # it's a keepalive, go back to waiting
                vvvv("%s: received a keepalive packet" % self.host)
                continue
            else:
                vvvv("%s: received the response" % self.host)
                break

        return (response.get('rc',None), '', response.get('stdout',''), response.get('stderr',''))

    def put_file(self, in_path, out_path):

        ''' transfer a file from local to remote '''
        vvv("PUT %s TO %s" % (in_path, out_path), host=self.host)

        if not os.path.exists(in_path):
            raise AnsibleFileNotFound("file or module does not exist: %s" % in_path)

        fd = file(in_path, 'rb')
        fstat = os.stat(in_path)
        try:
            vvv("PUT file is %d bytes" % fstat.st_size)
            last = False
            while fd.tell() <= fstat.st_size and not last:
                vvvv("file position currently %ld, file size is %ld" % (fd.tell(), fstat.st_size))
                data = fd.read(CHUNK_SIZE)
                if fd.tell() >= fstat.st_size:
                    last = True
                data = dict(mode='put', data=base64.b64encode(data), out_path=out_path, last=last)
                if self.runner.sudo:
                    data['user'] = self.runner.sudo_user
                data = utils.jsonify(data)
                data = utils.encrypt(self.key, data)

                if self.send_data(data):
                    raise AnsibleError("failed to send the file to %s" % self.host)

                response = self.recv_data()
                if not response:
                    raise AnsibleError("Failed to get a response from %s" % self.host)
                response = utils.decrypt(self.key, response)
                response = utils.parse_json(response)

                if response.get('failed',False):
                    raise AnsibleError("failed to put the file in the requested location")
        finally:
            fd.close()
            vvvv("waiting for final response after PUT")
            response = self.recv_data()
            if not response:
                raise AnsibleError("Failed to get a response from %s" % self.host)
            response = utils.decrypt(self.key, response)
            response = utils.parse_json(response)

            if response.get('failed',False):
                raise AnsibleError("failed to put the file in the requested location")

    def fetch_file(self, in_path, out_path):
        ''' save a remote file to the specified path '''
        vvv("FETCH %s TO %s" % (in_path, out_path), host=self.host)

        data = dict(mode='fetch', in_path=in_path)
        data = utils.jsonify(data)
        data = utils.encrypt(self.key, data)
        if self.send_data(data):
            raise AnsibleError("failed to initiate the file fetch with %s" % self.host)

        fh = open(out_path, "w")
        try:
            bytes = 0
            while True:
                response = self.recv_data()
                if not response:
                    raise AnsibleError("Failed to get a response from %s" % self.host)
                response = utils.decrypt(self.key, response)
                response = utils.parse_json(response)
                if response.get('failed', False):
                    raise AnsibleError("Error during file fetch, aborting")
                out = base64.b64decode(response['data'])
                fh.write(out)
                bytes += len(out)
                # send an empty response back to signify we 
                # received the last chunk without errors
                data = utils.jsonify(dict())
                data = utils.encrypt(self.key, data)
                if self.send_data(data):
                    raise AnsibleError("failed to send ack during file fetch")
                if response.get('last', False):
                    break
        finally:
            # we don't currently care about this final response,
            # we just receive it and drop it. It may be used at some
            # point in the future or we may just have the put/fetch
            # operations not send back a final response at all
            response = self.recv_data()
            vvv("FETCH wrote %d bytes to %s" % (bytes, out_path))
            fh.close()

    def close(self):
        ''' terminate the connection '''
        # Be a good citizen
        try:
            self.conn.close()
        except:
            pass


########NEW FILE########
__FILENAME__ = chroot
# Based on local.py (c) 2012, Michael DeHaan <michael.dehaan@gmail.com>
# (c) 2013, Maykel Moya <mmoya@speedyrails.com>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

import distutils.spawn
import traceback
import os
import shutil
import subprocess
from ansible import errors
from ansible import utils
from ansible.callbacks import vvv

class Connection(object):
    ''' Local chroot based connections '''

    def __init__(self, runner, host, port, *args, **kwargs):
        self.chroot = host
        self.has_pipelining = False

        if os.geteuid() != 0:
            raise errors.AnsibleError("chroot connection requires running as root")

        # we're running as root on the local system so do some
        # trivial checks for ensuring 'host' is actually a chroot'able dir
        if not os.path.isdir(self.chroot):
            raise errors.AnsibleError("%s is not a directory" % self.chroot)

        chrootsh = os.path.join(self.chroot, 'bin/sh')
        if not utils.is_executable(chrootsh):
            raise errors.AnsibleError("%s does not look like a chrootable dir (/bin/sh missing)" % self.chroot)

        self.chroot_cmd = distutils.spawn.find_executable('chroot')
        if not self.chroot_cmd:
            raise errors.AnsibleError("chroot command not found in PATH")

        self.runner = runner
        self.host = host
        # port is unused, since this is local
        self.port = port

    def connect(self, port=None):
        ''' connect to the chroot; nothing to do here '''

        vvv("THIS IS A LOCAL CHROOT DIR", host=self.chroot)

        return self

    def exec_command(self, cmd, tmp_path, sudo_user=None, sudoable=False, executable='/bin/sh', in_data=None, su=None, su_user=None):
        ''' run a command on the chroot '''

        if su or su_user:
            raise errors.AnsibleError("Internal Error: this module does not support running commands via su")

        if in_data:
            raise errors.AnsibleError("Internal Error: this module does not support optimized module pipelining")

        # We enter chroot as root so sudo stuff can be ignored

        if executable:
            local_cmd = [self.chroot_cmd, self.chroot, executable, '-c', cmd]
        else:
            local_cmd = '%s "%s" %s' % (self.chroot_cmd, self.chroot, cmd)

        vvv("EXEC %s" % (local_cmd), host=self.chroot)
        p = subprocess.Popen(local_cmd, shell=isinstance(local_cmd, basestring),
                             cwd=self.runner.basedir,
                             stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        stdout, stderr = p.communicate()
        return (p.returncode, '', stdout, stderr)

    def put_file(self, in_path, out_path):
        ''' transfer a file from local to chroot '''

        if not out_path.startswith(os.path.sep):
            out_path = os.path.join(os.path.sep, out_path)
        normpath = os.path.normpath(out_path)
        out_path = os.path.join(self.chroot, normpath[1:])

        vvv("PUT %s TO %s" % (in_path, out_path), host=self.chroot)
        if not os.path.exists(in_path):
            raise errors.AnsibleFileNotFound("file or module does not exist: %s" % in_path)
        try:
            shutil.copyfile(in_path, out_path)
        except shutil.Error:
            traceback.print_exc()
            raise errors.AnsibleError("failed to copy: %s and %s are the same" % (in_path, out_path))
        except IOError:
            traceback.print_exc()
            raise errors.AnsibleError("failed to transfer file to %s" % out_path)

    def fetch_file(self, in_path, out_path):
        ''' fetch a file from chroot to local '''

        if not in_path.startswith(os.path.sep):
            in_path = os.path.join(os.path.sep, in_path)
        normpath = os.path.normpath(in_path)
        in_path = os.path.join(self.chroot, normpath[1:])

        vvv("FETCH %s TO %s" % (in_path, out_path), host=self.chroot)
        if not os.path.exists(in_path):
            raise errors.AnsibleFileNotFound("file or module does not exist: %s" % in_path)
        try:
            shutil.copyfile(in_path, out_path)
        except shutil.Error:
            traceback.print_exc()
            raise errors.AnsibleError("failed to copy: %s and %s are the same" % (in_path, out_path))
        except IOError:
            traceback.print_exc()
            raise errors.AnsibleError("failed to transfer file to %s" % out_path)

    def close(self):
        ''' terminate the connection; nothing to do here '''
        pass

########NEW FILE########
__FILENAME__ = fireball
# (c) 2012, Michael DeHaan <michael.dehaan@gmail.com>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

import json
import os
import base64
from ansible.callbacks import vvv
from ansible import utils
from ansible import errors
from ansible import constants

HAVE_ZMQ=False

try:
    import zmq
    HAVE_ZMQ=True
except ImportError:
    pass

class Connection(object):
    ''' ZeroMQ accelerated connection '''

    def __init__(self, runner, host, port, *args, **kwargs):

        self.runner = runner
        self.has_pipelining = False

        # attempt to work around shared-memory funness
        if getattr(self.runner, 'aes_keys', None):
            utils.AES_KEYS = self.runner.aes_keys

        self.host = host
        self.key = utils.key_for_hostname(host)
        self.context = None
        self.socket = None

        if  port is None:
            self.port = constants.ZEROMQ_PORT
        else:
            self.port = port

    def connect(self):
        ''' activates the connection object '''

        if not HAVE_ZMQ:
            raise errors.AnsibleError("zmq is not installed")
        
        # this is rough/temporary and will likely be optimized later ...
        self.context = zmq.Context()
        socket = self.context.socket(zmq.REQ)
        addr = "tcp://%s:%s" % (self.host, self.port)
        socket.connect(addr)
        self.socket = socket    

        return self

    def exec_command(self, cmd, tmp_path, sudo_user, sudoable=False, executable='/bin/sh', in_data=None, su_user=None, su=None):
        ''' run a command on the remote host '''

        if in_data:
            raise errors.AnsibleError("Internal Error: this module does not support optimized module pipelining")

        vvv("EXEC COMMAND %s" % cmd)

        if (self.runner.sudo and sudoable) or (self.runner.su and su):
            raise errors.AnsibleError(
                "When using fireball, do not specify sudo or su to run your tasks. " +
                "Instead sudo the fireball action with sudo. " +
                "Task will communicate with the fireball already running in sudo mode."
            )

        data = dict(
            mode='command',
            cmd=cmd,
            tmp_path=tmp_path,
            executable=executable,
        )
        data = utils.jsonify(data)
        data = utils.encrypt(self.key, data)
        self.socket.send(data)
        
        response = self.socket.recv()
        response = utils.decrypt(self.key, response)
        response = utils.parse_json(response)

        return (response.get('rc',None), '', response.get('stdout',''), response.get('stderr',''))

    def put_file(self, in_path, out_path):

        ''' transfer a file from local to remote '''
        vvv("PUT %s TO %s" % (in_path, out_path), host=self.host)

        if not os.path.exists(in_path):
            raise errors.AnsibleFileNotFound("file or module does not exist: %s" % in_path)
        data = file(in_path).read()
        data = base64.b64encode(data)

        data = dict(mode='put', data=data, out_path=out_path)
        # TODO: support chunked file transfer
        data = utils.jsonify(data)
        data = utils.encrypt(self.key, data)
        self.socket.send(data)

        response = self.socket.recv()
        response = utils.decrypt(self.key, response)
        response = utils.parse_json(response)

        # no meaningful response needed for this

    def fetch_file(self, in_path, out_path):
        ''' save a remote file to the specified path '''
        vvv("FETCH %s TO %s" % (in_path, out_path), host=self.host)

        data = dict(mode='fetch', in_path=in_path)
        data = utils.jsonify(data)
        data = utils.encrypt(self.key, data)
        self.socket.send(data)

        response = self.socket.recv()
        response = utils.decrypt(self.key, response)
        response = utils.parse_json(response)
        response = response['data']
        response = base64.b64decode(response)        

        fh = open(out_path, "w")
        fh.write(response)
        fh.close()

    def close(self):
        ''' terminate the connection '''
        # Be a good citizen
        try:
            self.socket.close()
            self.context.term()
        except:
            pass


########NEW FILE########
__FILENAME__ = funcd
# Based on local.py (c) 2012, Michael DeHaan <michael.dehaan@gmail.com>
# Based on chroot.py (c) 2013, Maykel Moya <mmoya@speedyrails.com>
# (c) 2013, Michael Scherer <misc@zarb.org>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

# ---
# The func transport permit to use ansible over func. For people who have already setup
# func and that wish to play with ansible, this permit to move gradually to ansible
# without having to redo completely the setup of the network.

HAVE_FUNC=False
try:
    import func.overlord.client as fc
    HAVE_FUNC=True
except ImportError:
    pass

import os
from ansible.callbacks import vvv
from ansible import errors
import tempfile
import shutil


class Connection(object):
    ''' Func-based connections '''

    def __init__(self, runner, host, port, *args, **kwargs):
        self.runner = runner
        self.host = host
        self.has_pipelining = False
        # port is unused, this go on func
        self.port = port

    def connect(self, port=None):
        if not HAVE_FUNC:
            raise errors.AnsibleError("func is not installed")

        self.client = fc.Client(self.host)
        return self

    def exec_command(self, cmd, tmp_path, sudo_user=None, sudoable=False,
                     executable='/bin/sh', in_data=None, su=None, su_user=None):
        ''' run a command on the remote minion '''

        if su or su_user:
            raise errors.AnsibleError("Internal Error: this module does not support running commands via su")

        if in_data:
            raise errors.AnsibleError("Internal Error: this module does not support optimized module pipelining")

        vvv("EXEC %s" % (cmd), host=self.host)
        p = self.client.command.run(cmd)[self.host]
        return (p[0], '', p[1], p[2])

    def _normalize_path(self, path, prefix):
        if not path.startswith(os.path.sep):
            path = os.path.join(os.path.sep, path)
        normpath = os.path.normpath(path)
        return os.path.join(prefix, normpath[1:])

    def put_file(self, in_path, out_path):
        ''' transfer a file from local to remote '''

        out_path = self._normalize_path(out_path, '/')
        vvv("PUT %s TO %s" % (in_path, out_path), host=self.host)
        self.client.local.copyfile.send(in_path, out_path)

    def fetch_file(self, in_path, out_path):
        ''' fetch a file from remote to local '''

        in_path = self._normalize_path(in_path, '/')
        vvv("FETCH %s TO %s" % (in_path, out_path), host=self.host)
        # need to use a tmp dir due to difference of semantic for getfile
        # ( who take a # directory as destination) and fetch_file, who
        # take a file directly
        tmpdir = tempfile.mkdtemp(prefix="func_ansible")
        self.client.local.getfile.get(in_path, tmpdir)
        shutil.move(os.path.join(tmpdir, self.host, os.path.basename(in_path)),
                    out_path)
        shutil.rmtree(tmpdir)

    def close(self):
        ''' terminate the connection; nothing to do here '''
        pass

########NEW FILE########
__FILENAME__ = jail
# Based on local.py (c) 2012, Michael DeHaan <michael.dehaan@gmail.com>
# and chroot.py     (c) 2013, Maykel Moya <mmoya@speedyrails.com>
# (c) 2013, Michael Scherer <misc@zarb.org>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

import distutils.spawn
import traceback
import os
import shutil
import subprocess
from ansible import errors
from ansible.callbacks import vvv

class Connection(object):
    ''' Local chroot based connections '''

    def _search_executable(self, executable):
        cmd = distutils.spawn.find_executable(executable)
        if not cmd:
            raise errors.AnsibleError("%s command not found in PATH") % executable
        return cmd

    def list_jails(self):
        p = subprocess.Popen([self.jls_cmd, '-q', 'name'],
                             cwd=self.runner.basedir,
                             stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        stdout, stderr = p.communicate()

        return stdout.split()

    def get_jail_path(self):
        p = subprocess.Popen([self.jls_cmd, '-j', self.jail, '-q', 'path'],
                             cwd=self.runner.basedir,
                             stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        stdout, stderr = p.communicate()
        # remove \n
        return stdout[:-1]

 
        
    def __init__(self, runner, host, port, *args, **kwargs):
        self.jail = host
        self.runner = runner
        self.host = host
        self.has_pipelining = False

        if os.geteuid() != 0:
            raise errors.AnsibleError("jail connection requires running as root")

        self.jls_cmd = self._search_executable('jls')
        self.jexec_cmd = self._search_executable('jexec')
        
        if not self.jail in self.list_jails():
            raise errors.AnsibleError("incorrect jail name %s" % self.jail)


        self.host = host
        # port is unused, since this is local
        self.port = port

    def connect(self, port=None):
        ''' connect to the chroot; nothing to do here '''

        vvv("THIS IS A LOCAL CHROOT DIR", host=self.jail)

        return self

    # a modifier
    def _generate_cmd(self, executable, cmd):
        if executable:
            local_cmd = [self.jexec_cmd, self.jail, executable, '-c', cmd]
        else:
            local_cmd = '%s "%s" %s' % (self.jexec_cmd, self.jail, cmd)
        return local_cmd

    def exec_command(self, cmd, tmp_path, sudo_user=None, sudoable=False, executable='/bin/sh', in_data=None, su=None, su_user=None):
        ''' run a command on the chroot '''

        if su or su_user:
            raise errors.AnsibleError("Internal Error: this module does not support running commands via su")

        if in_data:
            raise errors.AnsibleError("Internal Error: this module does not support optimized module pipelining")

        # We enter chroot as root so sudo stuff can be ignored
        local_cmd = self._generate_cmd(executable, cmd)

        vvv("EXEC %s" % (local_cmd), host=self.jail)
        p = subprocess.Popen(local_cmd, shell=isinstance(local_cmd, basestring),
                             cwd=self.runner.basedir,
                             stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        stdout, stderr = p.communicate()
        return (p.returncode, '', stdout, stderr)

    def _normalize_path(self, path, prefix):
        if not path.startswith(os.path.sep):
            path = os.path.join(os.path.sep, path)
        normpath = os.path.normpath(path)
        return os.path.join(prefix, normpath[1:])

    def _copy_file(self, in_path, out_path):
        if not os.path.exists(in_path):
            raise errors.AnsibleFileNotFound("file or module does not exist: %s" % in_path)
        try:
            shutil.copyfile(in_path, out_path)
        except shutil.Error:
            traceback.print_exc()
            raise errors.AnsibleError("failed to copy: %s and %s are the same" % (in_path, out_path))
        except IOError:
            traceback.print_exc()
            raise errors.AnsibleError("failed to transfer file to %s" % out_path)

    def put_file(self, in_path, out_path):
        ''' transfer a file from local to chroot '''

        out_path = self._normalize_path(out_path, self.get_jail_path())
        vvv("PUT %s TO %s" % (in_path, out_path), host=self.jail)

        self._copy_file(in_path, out_path)

    def fetch_file(self, in_path, out_path):
        ''' fetch a file from chroot to local '''

        in_path = self._normalize_path(in_path, self.get_jail_path())
        vvv("FETCH %s TO %s" % (in_path, out_path), host=self.jail)

        self._copy_file(in_path, out_path)

    def close(self):
        ''' terminate the connection; nothing to do here '''
        pass

########NEW FILE########
__FILENAME__ = libvirt_lxc
# Based on local.py (c) 2012, Michael DeHaan <michael.dehaan@gmail.com>
# Based on chroot.py (c) 2013, Maykel Moya <mmoya@speedyrails.com>
# (c) 2013, Michael Scherer <misc@zarb.org>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

import distutils.spawn
import os
import subprocess
from ansible import errors
from ansible.callbacks import vvv

class Connection(object):
    ''' Local lxc based connections '''

    def _search_executable(self, executable):
        cmd = distutils.spawn.find_executable(executable)
        if not cmd:
            raise errors.AnsibleError("%s command not found in PATH") % executable
        return cmd

    def _check_domain(self, domain):
        p = subprocess.Popen([self.cmd, '-q', '-c', 'lxc:///', 'dominfo', domain],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        p.communicate()
        if p.returncode:
            raise errors.AnsibleError("%s is not a lxc defined in libvirt" % domain)

    def __init__(self, runner, host, port, *args, **kwargs):
        self.lxc = host

        self.cmd = self._search_executable('virsh')

        self._check_domain(host)

        self.runner = runner
        self.host = host
        # port is unused, since this is local
        self.port = port

    def connect(self, port=None):
        ''' connect to the lxc; nothing to do here '''

        vvv("THIS IS A LOCAL LXC DIR", host=self.lxc)

        return self

    def _generate_cmd(self, executable, cmd):
        if executable:
            local_cmd = [self.cmd, '-q', '-c', 'lxc:///', 'lxc-enter-namespace', self.lxc, '--', executable , '-c', cmd]
        else:
            local_cmd = '%s -q -c lxc:/// lxc-enter-namespace %s -- %s' % (self.cmd, self.lxc, cmd)
        return local_cmd

    def exec_command(self, cmd, tmp_path, sudo_user, sudoable=False, executable='/bin/sh'):
        ''' run a command on the chroot '''

        # We enter lxc as root so sudo stuff can be ignored
        local_cmd = self._generate_cmd(executable, cmd)

        vvv("EXEC %s" % (local_cmd), host=self.lxc)
        p = subprocess.Popen(local_cmd, shell=isinstance(local_cmd, basestring),
                             cwd=self.runner.basedir,
                             stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        stdout, stderr = p.communicate()
        return (p.returncode, '', stdout, stderr)

    def _normalize_path(self, path, prefix):
        if not path.startswith(os.path.sep):
            path = os.path.join(os.path.sep, path)
        normpath = os.path.normpath(path)
        return os.path.join(prefix, normpath[1:])

    def put_file(self, in_path, out_path):
        ''' transfer a file from local to lxc '''

        out_path = self._normalize_path(out_path, '/')
        vvv("PUT %s TO %s" % (in_path, out_path), host=self.lxc)
        
        local_cmd = [self.cmd, '-q', '-c', 'lxc:///', 'lxc-enter-namespace', self.lxc, '--', '/bin/tee', out_path]
        vvv("EXEC %s" % (local_cmd), host=self.lxc)

        p = subprocess.Popen(local_cmd, cwd=self.runner.basedir,
                             stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE) 
        stdout, stderr = p.communicate(open(in_path,'rb').read())
 
    def fetch_file(self, in_path, out_path):
        ''' fetch a file from lxc to local '''

        in_path = self._normalize_path(in_path, '/')
        vvv("FETCH %s TO %s" % (in_path, out_path), host=self.lxc)

        local_cmd = [self.cmd, '-q', '-c', 'lxc:///', 'lxc-enter-namespace', self.lxc, '--', '/bin/cat', in_path]
        vvv("EXEC %s" % (local_cmd), host=self.lxc)

        p = subprocess.Popen(local_cmd, cwd=self.runner.basedir,
                             stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = p.communicate()
        open(out_path,'wb').write(stdout)


    def close(self):
        ''' terminate the connection; nothing to do here '''
        pass

########NEW FILE########
__FILENAME__ = local
# (c) 2012, Michael DeHaan <michael.dehaan@gmail.com>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

import traceback
import os
import pipes
import shutil
import subprocess
import select
import fcntl
from ansible import errors
from ansible import utils
from ansible.callbacks import vvv

class Connection(object):
    ''' Local based connections '''

    def __init__(self, runner, host, port, *args, **kwargs):
        self.runner = runner
        self.host = host
        # port is unused, since this is local
        self.port = port 
        self.has_pipelining = False

    def connect(self, port=None):
        ''' connect to the local host; nothing to do here '''

        return self

    def exec_command(self, cmd, tmp_path, sudo_user=None, sudoable=False, executable='/bin/sh', in_data=None, su=None, su_user=None):
        ''' run a command on the local host '''

        # su requires to be run from a terminal, and therefore isn't supported here (yet?)
        if su or su_user:
            raise errors.AnsibleError("Internal Error: this module does not support running commands via su")

        if in_data:
            raise errors.AnsibleError("Internal Error: this module does not support optimized module pipelining")

        if not self.runner.sudo or not sudoable:
            if executable:
                local_cmd = [executable, '-c', cmd]
            else:
                local_cmd = cmd
        else:
            local_cmd, prompt, success_key = utils.make_sudo_cmd(sudo_user, executable, cmd)

        vvv("EXEC %s" % (local_cmd), host=self.host)
        p = subprocess.Popen(local_cmd, shell=isinstance(local_cmd, basestring),
                             cwd=self.runner.basedir, executable=executable or None,
                             stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        if self.runner.sudo and sudoable and self.runner.sudo_pass:
            fcntl.fcntl(p.stdout, fcntl.F_SETFL,
                        fcntl.fcntl(p.stdout, fcntl.F_GETFL) | os.O_NONBLOCK)
            fcntl.fcntl(p.stderr, fcntl.F_SETFL,
                        fcntl.fcntl(p.stderr, fcntl.F_GETFL) | os.O_NONBLOCK)
            sudo_output = ''
            while not sudo_output.endswith(prompt) and success_key not in sudo_output:
                rfd, wfd, efd = select.select([p.stdout, p.stderr], [],
                                              [p.stdout, p.stderr], self.runner.timeout)
                if p.stdout in rfd:
                    chunk = p.stdout.read()
                elif p.stderr in rfd:
                    chunk = p.stderr.read()
                else:
                    stdout, stderr = p.communicate()
                    raise errors.AnsibleError('timeout waiting for sudo password prompt:\n' + sudo_output)
                if not chunk:
                    stdout, stderr = p.communicate()
                    raise errors.AnsibleError('sudo output closed while waiting for password prompt:\n' + sudo_output)
                sudo_output += chunk
            if success_key not in sudo_output:
                p.stdin.write(self.runner.sudo_pass + '\n')
            fcntl.fcntl(p.stdout, fcntl.F_SETFL, fcntl.fcntl(p.stdout, fcntl.F_GETFL) & ~os.O_NONBLOCK)
            fcntl.fcntl(p.stderr, fcntl.F_SETFL, fcntl.fcntl(p.stderr, fcntl.F_GETFL) & ~os.O_NONBLOCK)

        stdout, stderr = p.communicate()
        return (p.returncode, '', stdout, stderr)

    def put_file(self, in_path, out_path):
        ''' transfer a file from local to local '''

        vvv("PUT %s TO %s" % (in_path, out_path), host=self.host)
        if not os.path.exists(in_path):
            raise errors.AnsibleFileNotFound("file or module does not exist: %s" % in_path)
        try:
            shutil.copyfile(in_path, out_path)
        except shutil.Error:
            traceback.print_exc()
            raise errors.AnsibleError("failed to copy: %s and %s are the same" % (in_path, out_path))
        except IOError:
            traceback.print_exc()
            raise errors.AnsibleError("failed to transfer file to %s" % out_path)

    def fetch_file(self, in_path, out_path):
        vvv("FETCH %s TO %s" % (in_path, out_path), host=self.host)
        ''' fetch a file from local to local -- for copatibility '''
        self.put_file(in_path, out_path)

    def close(self):
        ''' terminate the connection; nothing to do here '''
        pass

########NEW FILE########
__FILENAME__ = paramiko_ssh
# (c) 2012, Michael DeHaan <michael.dehaan@gmail.com>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.


# ---
# The paramiko transport is provided because many distributions, in particular EL6 and before
# do not support ControlPersist in their SSH implementations.  This is needed on the Ansible
# control machine to be reasonably efficient with connections.  Thus paramiko is faster
# for most users on these platforms.  Users with ControlPersist capability can consider
# using -c ssh or configuring the transport in ansible.cfg.

import warnings
import os
import pipes
import socket
import random
import logging
import traceback
import fcntl
import re
import sys
from termios import tcflush, TCIFLUSH
from binascii import hexlify
from ansible.callbacks import vvv
from ansible import errors
from ansible import utils
from ansible import constants as C
            
AUTHENTICITY_MSG="""
paramiko: The authenticity of host '%s' can't be established. 
The %s key fingerprint is %s. 
Are you sure you want to continue connecting (yes/no)?
"""

# prevent paramiko warning noise -- see http://stackoverflow.com/questions/3920502/
HAVE_PARAMIKO=False
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    try:
        import paramiko
        HAVE_PARAMIKO=True
        logging.getLogger("paramiko").setLevel(logging.WARNING)
    except ImportError:
        pass

class MyAddPolicy(object):
    """
    Based on AutoAddPolicy in paramiko so we can determine when keys are added
    and also prompt for input.

    Policy for automatically adding the hostname and new host key to the
    local L{HostKeys} object, and saving it.  This is used by L{SSHClient}.
    """

    def __init__(self, runner): 
        self.runner = runner

    def missing_host_key(self, client, hostname, key):

        if C.HOST_KEY_CHECKING:

            fcntl.lockf(self.runner.process_lockfile, fcntl.LOCK_EX)
            fcntl.lockf(self.runner.output_lockfile, fcntl.LOCK_EX)

            old_stdin = sys.stdin
            sys.stdin = self.runner._new_stdin
            fingerprint = hexlify(key.get_fingerprint())
            ktype = key.get_name()
            
            # clear out any premature input on sys.stdin
            tcflush(sys.stdin, TCIFLUSH)

            inp = raw_input(AUTHENTICITY_MSG % (hostname, ktype, fingerprint))
            sys.stdin = old_stdin
            if inp not in ['yes','y','']:
                fcntl.flock(self.runner.output_lockfile, fcntl.LOCK_UN)
                fcntl.flock(self.runner.process_lockfile, fcntl.LOCK_UN)
                raise errors.AnsibleError("host connection rejected by user")

            fcntl.lockf(self.runner.output_lockfile, fcntl.LOCK_UN)
            fcntl.lockf(self.runner.process_lockfile, fcntl.LOCK_UN)


        key._added_by_ansible_this_time = True

        # existing implementation below:
        client._host_keys.add(hostname, key.get_name(), key)

        # host keys are actually saved in close() function below
        # in order to control ordering.
        

# keep connection objects on a per host basis to avoid repeated attempts to reconnect

SSH_CONNECTION_CACHE = {}
SFTP_CONNECTION_CACHE = {}

class Connection(object):
    ''' SSH based connections with Paramiko '''

    def __init__(self, runner, host, port, user, password, private_key_file, *args, **kwargs):

        self.ssh = None
        self.sftp = None
        self.runner = runner
        self.host = host
        self.port = port or 22
        self.user = user
        self.password = password
        self.private_key_file = private_key_file
        self.has_pipelining = False

    def _cache_key(self):
        return "%s__%s__" % (self.host, self.user)

    def connect(self):
        cache_key = self._cache_key()
        if cache_key in SSH_CONNECTION_CACHE:
            self.ssh = SSH_CONNECTION_CACHE[cache_key]
        else:
            self.ssh = SSH_CONNECTION_CACHE[cache_key] = self._connect_uncached()
        return self

    def _connect_uncached(self):
        ''' activates the connection object '''

        if not HAVE_PARAMIKO:
            raise errors.AnsibleError("paramiko is not installed")

        vvv("ESTABLISH CONNECTION FOR USER: %s on PORT %s TO %s" % (self.user, self.port, self.host), host=self.host)

        ssh = paramiko.SSHClient()
     
        self.keyfile = os.path.expanduser("~/.ssh/known_hosts")

        if C.HOST_KEY_CHECKING:
            ssh.load_system_host_keys()
        ssh.set_missing_host_key_policy(MyAddPolicy(self.runner))

        allow_agent = True
        if self.password is not None:
            allow_agent = False
        try:
            if self.private_key_file:
                key_filename = os.path.expanduser(self.private_key_file)
            elif self.runner.private_key_file:
                key_filename = os.path.expanduser(self.runner.private_key_file)
            else:
                key_filename = None
            ssh.connect(self.host, username=self.user, allow_agent=allow_agent, look_for_keys=True,
                key_filename=key_filename, password=self.password,
                timeout=self.runner.timeout, port=self.port)
        except Exception, e:
            msg = str(e)
            if "PID check failed" in msg:
                raise errors.AnsibleError("paramiko version issue, please upgrade paramiko on the machine running ansible")
            elif "Private key file is encrypted" in msg:
                msg = 'ssh %s@%s:%s : %s\nTo connect as a different user, use -u <username>.' % (
                    self.user, self.host, self.port, msg)
                raise errors.AnsibleConnectionFailed(msg)
            else:
                raise errors.AnsibleConnectionFailed(msg)

        return ssh

    def exec_command(self, cmd, tmp_path, sudo_user=None, sudoable=False, executable='/bin/sh', in_data=None, su=None, su_user=None):
        ''' run a command on the remote host '''

        if in_data:
            raise errors.AnsibleError("Internal Error: this module does not support optimized module pipelining")

        bufsize = 4096
        try:
            chan = self.ssh.get_transport().open_session()
        except Exception, e:
            msg = "Failed to open session"
            if len(str(e)) > 0:
                msg += ": %s" % str(e)
            raise errors.AnsibleConnectionFailed(msg)

        if not (self.runner.sudo and sudoable) and not (self.runner.su and su):
            if executable:
                quoted_command = executable + ' -c ' + pipes.quote(cmd)
            else:
                quoted_command = cmd
            vvv("EXEC %s" % quoted_command, host=self.host)
            chan.exec_command(quoted_command)
        else:
            # sudo usually requires a PTY (cf. requiretty option), therefore
            # we give it one by default (pty=True in ansble.cfg), and we try
            # to initialise from the calling environment
            if C.PARAMIKO_PTY:
                chan.get_pty(term=os.getenv('TERM', 'vt100'),
                             width=int(os.getenv('COLUMNS', 0)),
                             height=int(os.getenv('LINES', 0)))
            if self.runner.sudo or sudoable:
                shcmd, prompt, success_key = utils.make_sudo_cmd(sudo_user, executable, cmd)
            elif self.runner.su or su:
                shcmd, prompt, success_key = utils.make_su_cmd(su_user, executable, cmd)
                prompt_re = re.compile(prompt)
            vvv("EXEC %s" % shcmd, host=self.host)
            sudo_output = ''
            try:
                chan.exec_command(shcmd)
                if self.runner.sudo_pass or self.runner.su_pass:
                    while True:
                        if success_key in sudo_output or \
                            (self.runner.sudo_pass and sudo_output.endswith(prompt)) or \
                            (self.runner.su_pass and prompt_re.match(sudo_output)):
                            break
                        chunk = chan.recv(bufsize)
                        if not chunk:
                            if 'unknown user' in sudo_output:
                                raise errors.AnsibleError(
                                    'user %s does not exist' % sudo_user)
                            else:
                                raise errors.AnsibleError('ssh connection ' +
                                    'closed waiting for password prompt')
                        sudo_output += chunk
                    if success_key not in sudo_output:
                        if sudoable:
                            chan.sendall(self.runner.sudo_pass + '\n')
                        elif su:
                            chan.sendall(self.runner.su_pass + '\n')
            except socket.timeout:
                raise errors.AnsibleError('ssh timed out waiting for sudo.\n' + sudo_output)

        stdout = ''.join(chan.makefile('rb', bufsize))
        stderr = ''.join(chan.makefile_stderr('rb', bufsize))
        return (chan.recv_exit_status(), '', stdout, stderr)

    def put_file(self, in_path, out_path):
        ''' transfer a file from local to remote '''
        vvv("PUT %s TO %s" % (in_path, out_path), host=self.host)
        if not os.path.exists(in_path):
            raise errors.AnsibleFileNotFound("file or module does not exist: %s" % in_path)
        try:
            self.sftp = self.ssh.open_sftp()
        except Exception, e:
            raise errors.AnsibleError("failed to open a SFTP connection (%s)" % e)
        try:
            self.sftp.put(in_path, out_path)
        except IOError:
            raise errors.AnsibleError("failed to transfer file to %s" % out_path)

    def _connect_sftp(self):
        cache_key = "%s__%s__" % (self.host, self.user)
        if cache_key in SFTP_CONNECTION_CACHE:
            return SFTP_CONNECTION_CACHE[cache_key]
        else:
            result = SFTP_CONNECTION_CACHE[cache_key] = self.connect().ssh.open_sftp()
            return result

    def fetch_file(self, in_path, out_path):
        ''' save a remote file to the specified path '''
        vvv("FETCH %s TO %s" % (in_path, out_path), host=self.host)
        try:
            self.sftp = self._connect_sftp()
        except Exception, e:
            raise errors.AnsibleError("failed to open a SFTP connection (%s)", e)
        try:
            self.sftp.get(in_path, out_path)
        except IOError:
            raise errors.AnsibleError("failed to transfer file from %s" % in_path)

    def _any_keys_added(self):
        added_any = False        
        for hostname, keys in self.ssh._host_keys.iteritems():
            for keytype, key in keys.iteritems():
                added_this_time = getattr(key, '_added_by_ansible_this_time', False)
                if added_this_time:
                    return True
        return False

    def _save_ssh_host_keys(self, filename):
        ''' 
        not using the paramiko save_ssh_host_keys function as we want to add new SSH keys at the bottom so folks 
        don't complain about it :) 
        '''

        if not self._any_keys_added():
            return False

        path = os.path.expanduser("~/.ssh")
        if not os.path.exists(path):
            os.makedirs(path)

        f = open(filename, 'w')
        for hostname, keys in self.ssh._host_keys.iteritems():
            for keytype, key in keys.iteritems():
                # was f.write
                added_this_time = getattr(key, '_added_by_ansible_this_time', False)
                if not added_this_time:
                    f.write("%s %s %s\n" % (hostname, keytype, key.get_base64()))
        for hostname, keys in self.ssh._host_keys.iteritems():
            for keytype, key in keys.iteritems():
                added_this_time = getattr(key, '_added_by_ansible_this_time', False)
                if added_this_time:
                    f.write("%s %s %s\n" % (hostname, keytype, key.get_base64()))
        f.close()

    def close(self):
        ''' terminate the connection '''
        cache_key = self._cache_key()
        SSH_CONNECTION_CACHE.pop(cache_key, None)
        SFTP_CONNECTION_CACHE.pop(cache_key, None)
        if self.sftp is not None:
            self.sftp.close()

        if C.PARAMIKO_RECORD_HOST_KEYS and self._any_keys_added():

            # add any new SSH host keys -- warning -- this could be slow
            lockfile = self.keyfile.replace("known_hosts",".known_hosts.lock") 
            dirname = os.path.dirname(self.keyfile)
            if not os.path.exists(dirname):
                os.makedirs(dirname)

            KEY_LOCK = open(lockfile, 'w')
            fcntl.lockf(KEY_LOCK, fcntl.LOCK_EX)
            try:
                # just in case any were added recently
                self.ssh.load_system_host_keys()
                self.ssh._host_keys.update(self.ssh._system_host_keys)
                self._save_ssh_host_keys(self.keyfile)
            except:
                # unable to save keys, including scenario when key was invalid
                # and caught earlier
                traceback.print_exc()
                pass
            fcntl.lockf(KEY_LOCK, fcntl.LOCK_UN)

        self.ssh.close()
        

########NEW FILE########
__FILENAME__ = ssh
# (c) 2012, Michael DeHaan <michael.dehaan@gmail.com>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.
#

import os
import re
import subprocess
import shlex
import pipes
import random
import select
import fcntl
import hmac
import pwd
import gettext
import pty
from hashlib import sha1
import ansible.constants as C
from ansible.callbacks import vvv
from ansible import errors
from ansible import utils

class Connection(object):
    ''' ssh based connections '''

    def __init__(self, runner, host, port, user, password, private_key_file, *args, **kwargs):
        self.runner = runner
        self.host = host
        self.ipv6 = ':' in self.host
        self.port = port
        self.user = str(user)
        self.password = password
        self.private_key_file = private_key_file
        self.HASHED_KEY_MAGIC = "|1|"
        self.has_pipelining = True

        fcntl.lockf(self.runner.process_lockfile, fcntl.LOCK_EX)
        self.cp_dir = utils.prepare_writeable_dir('$HOME/.ansible/cp',mode=0700)
        fcntl.lockf(self.runner.process_lockfile, fcntl.LOCK_UN)

    def connect(self):
        ''' connect to the remote host '''

        vvv("ESTABLISH CONNECTION FOR USER: %s" % self.user, host=self.host)

        self.common_args = []
        extra_args = C.ANSIBLE_SSH_ARGS
        if extra_args is not None:
            # make sure there is no empty string added as this can produce weird errors
            self.common_args += [x.strip() for x in shlex.split(extra_args) if x.strip()]
        else:
            self.common_args += ["-o", "ControlMaster=auto",
                                 "-o", "ControlPersist=60s",
                                 "-o", "ControlPath=%s" % (C.ANSIBLE_SSH_CONTROL_PATH % dict(directory=self.cp_dir))]

        cp_in_use = False
        cp_path_set = False
        for arg in self.common_args:
            if "ControlPersist" in arg:
                cp_in_use = True
            if "ControlPath" in arg:
                cp_path_set = True

        if cp_in_use and not cp_path_set:
            self.common_args += ["-o", "ControlPath=%s" % (C.ANSIBLE_SSH_CONTROL_PATH % dict(directory=self.cp_dir))]

        if not C.HOST_KEY_CHECKING:
            self.common_args += ["-o", "StrictHostKeyChecking=no"]

        if self.port is not None:
            self.common_args += ["-o", "Port=%d" % (self.port)]
        if self.private_key_file is not None:
            self.common_args += ["-o", "IdentityFile="+os.path.expanduser(self.private_key_file)]
        elif self.runner.private_key_file is not None:
            self.common_args += ["-o", "IdentityFile="+os.path.expanduser(self.runner.private_key_file)]
        if self.password:
            self.common_args += ["-o", "GSSAPIAuthentication=no",
                                 "-o", "PubkeyAuthentication=no"]
        else:
            self.common_args += ["-o", "KbdInteractiveAuthentication=no",
                                 "-o", "PreferredAuthentications=gssapi-with-mic,gssapi-keyex,hostbased,publickey",
                                 "-o", "PasswordAuthentication=no"]
        if self.user != pwd.getpwuid(os.geteuid())[0]:
            self.common_args += ["-o", "User="+self.user]
        self.common_args += ["-o", "ConnectTimeout=%d" % self.runner.timeout]

        return self

    def _run(self, cmd, indata):
        if indata:
            # do not use pseudo-pty
            p = subprocess.Popen(cmd, stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdin = p.stdin
        else:
            # try to use upseudo-pty
            try:
                # Make sure stdin is a proper (pseudo) pty to avoid: tcgetattr errors
                master, slave = pty.openpty()
                p = subprocess.Popen(cmd, stdin=slave,
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                stdin = os.fdopen(master, 'w', 0)
                os.close(slave)
            except:
                p = subprocess.Popen(cmd, stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                stdin = p.stdin

        return (p, stdin)

    def _password_cmd(self):
        if self.password:
            try:
                p = subprocess.Popen(["sshpass"], stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                p.communicate()
            except OSError:
                raise errors.AnsibleError("to use the 'ssh' connection type with passwords, you must install the sshpass program")
            (self.rfd, self.wfd) = os.pipe()
            return ["sshpass", "-d%d" % self.rfd]
        return []

    def _send_password(self):
        if self.password:
            os.close(self.rfd)
            os.write(self.wfd, "%s\n" % self.password)
            os.close(self.wfd)

    def _communicate(self, p, stdin, indata, su=False, sudoable=False, prompt=None):
        fcntl.fcntl(p.stdout, fcntl.F_SETFL, fcntl.fcntl(p.stdout, fcntl.F_GETFL) & ~os.O_NONBLOCK)
        fcntl.fcntl(p.stderr, fcntl.F_SETFL, fcntl.fcntl(p.stderr, fcntl.F_GETFL) & ~os.O_NONBLOCK)
        # We can't use p.communicate here because the ControlMaster may have stdout open as well
        stdout = ''
        stderr = ''
        rpipes = [p.stdout, p.stderr]
        if indata:
            try:
                stdin.write(indata)
                stdin.close()
            except:
                raise errors.AnsibleError('SSH Error: data could not be sent to the remote host. Make sure this host can be reached over ssh')
        # Read stdout/stderr from process
        while True:
            rfd, wfd, efd = select.select(rpipes, [], rpipes, 1)

            # fail early if the sudo/su password is wrong
            if self.runner.sudo and sudoable:
                if self.runner.sudo_pass:
                    incorrect_password = gettext.dgettext(
                        "sudo", "Sorry, try again.")
                    if stdout.endswith("%s\r\n%s" % (incorrect_password,
                                                     prompt)):
                        raise errors.AnsibleError('Incorrect sudo password')

                if stdout.endswith(prompt):
                    raise errors.AnsibleError('Missing sudo password')

            if self.runner.su and su and self.runner.su_pass:
                incorrect_password = gettext.dgettext(
                    "su", "Sorry")
                if stdout.endswith("%s\r\n%s" % (incorrect_password, prompt)):
                    raise errors.AnsibleError('Incorrect su password')

            if p.stdout in rfd:
                dat = os.read(p.stdout.fileno(), 9000)
                stdout += dat
                if dat == '':
                    rpipes.remove(p.stdout)
            if p.stderr in rfd:
                dat = os.read(p.stderr.fileno(), 9000)
                stderr += dat
                if dat == '':
                    rpipes.remove(p.stderr)
            # only break out if no pipes are left to read or
            # the pipes are completely read and
            # the process is terminated
            if (not rpipes or not rfd) and p.poll() is not None:
                break
            # No pipes are left to read but process is not yet terminated
            # Only then it is safe to wait for the process to be finished
            # NOTE: Actually p.poll() is always None here if rpipes is empty
            elif not rpipes and p.poll() == None:
                p.wait()
                # The process is terminated. Since no pipes to read from are
                # left, there is no need to call select() again.
                break
        # close stdin after process is terminated and stdout/stderr are read
        # completely (see also issue #848)
        stdin.close()
        return (p.returncode, stdout, stderr)

    def not_in_host_file(self, host):
        if 'USER' in os.environ:
            user_host_file = os.path.expandvars("~${USER}/.ssh/known_hosts")
        else:
            user_host_file = "~/.ssh/known_hosts"
        user_host_file = os.path.expanduser(user_host_file)
        
        host_file_list = []
        host_file_list.append(user_host_file)
        host_file_list.append("/etc/ssh/ssh_known_hosts")
        host_file_list.append("/etc/ssh/ssh_known_hosts2")
        
        hfiles_not_found = 0
        for hf in host_file_list:
            if not os.path.exists(hf):
                hfiles_not_found += 1
                continue
            host_fh = open(hf)
            data = host_fh.read()
            host_fh.close()
            for line in data.split("\n"):
                if line is None or " " not in line:
                    continue
                tokens = line.split()
                if tokens[0].find(self.HASHED_KEY_MAGIC) == 0:
                    # this is a hashed known host entry
                    try:
                        (kn_salt,kn_host) = tokens[0][len(self.HASHED_KEY_MAGIC):].split("|",2)
                        hash = hmac.new(kn_salt.decode('base64'), digestmod=sha1)
                        hash.update(host)
                        if hash.digest() == kn_host.decode('base64'):
                            return False
                    except:
                        # invalid hashed host key, skip it
                        continue
                else:
                    # standard host file entry
                    if host in tokens[0]:
                        return False

        if (hfiles_not_found == len(host_file_list)):
            vvv("EXEC previous known host file not found for %s" % host)
        return True

    def exec_command(self, cmd, tmp_path, sudo_user=None, sudoable=False, executable='/bin/sh', in_data=None, su_user=None, su=False):
        ''' run a command on the remote host '''

        ssh_cmd = self._password_cmd()
        ssh_cmd += ["ssh", "-C"]
        if not in_data:
            # we can only use tty when we are not pipelining the modules. piping data into /usr/bin/python
            # inside a tty automatically invokes the python interactive-mode but the modules are not
            # compatible with the interactive-mode ("unexpected indent" mainly because of empty lines)
            ssh_cmd += ["-tt"]
        if utils.VERBOSITY > 3:
            ssh_cmd += ["-vvv"]
        else:
            ssh_cmd += ["-q"]
        ssh_cmd += self.common_args

        if self.ipv6:
            ssh_cmd += ['-6']
        ssh_cmd += [self.host]

        if su and su_user:
            sudocmd, prompt, success_key = utils.make_su_cmd(su_user, executable, cmd)
            prompt_re = re.compile(prompt)
            ssh_cmd.append(sudocmd)
        elif not self.runner.sudo or not sudoable:
            prompt = None
            if executable:
                ssh_cmd.append(executable + ' -c ' + pipes.quote(cmd))
            else:
                ssh_cmd.append(cmd)
        else:
            sudocmd, prompt, success_key = utils.make_sudo_cmd(sudo_user, executable, cmd)
            ssh_cmd.append(sudocmd)

        vvv("EXEC %s" % ssh_cmd, host=self.host)

        not_in_host_file = self.not_in_host_file(self.host)

        if C.HOST_KEY_CHECKING and not_in_host_file:
            # lock around the initial SSH connectivity so the user prompt about whether to add 
            # the host to known hosts is not intermingled with multiprocess output.
            fcntl.lockf(self.runner.process_lockfile, fcntl.LOCK_EX)
            fcntl.lockf(self.runner.output_lockfile, fcntl.LOCK_EX)

        # create process
        (p, stdin) = self._run(ssh_cmd, in_data)

        self._send_password()

        if (self.runner.sudo and sudoable and self.runner.sudo_pass) or \
                (self.runner.su and su and self.runner.su_pass):
            # several cases are handled for sudo privileges with password
            # * NOPASSWD (tty & no-tty): detect success_key on stdout
            # * without NOPASSWD:
            #   * detect prompt on stdout (tty)
            #   * detect prompt on stderr (no-tty)
            fcntl.fcntl(p.stdout, fcntl.F_SETFL,
                        fcntl.fcntl(p.stdout, fcntl.F_GETFL) | os.O_NONBLOCK)
            fcntl.fcntl(p.stderr, fcntl.F_SETFL,
                        fcntl.fcntl(p.stderr, fcntl.F_GETFL) | os.O_NONBLOCK)
            sudo_output = ''
            sudo_errput = ''

            while True:
                if success_key in sudo_output or \
                    (self.runner.sudo_pass and sudo_output.endswith(prompt)) or \
                    (self.runner.su_pass and prompt_re.match(sudo_output)):
                    break

                rfd, wfd, efd = select.select([p.stdout, p.stderr], [],
                                              [p.stdout], self.runner.timeout)
                if p.stderr in rfd:
                    chunk = p.stderr.read()
                    if not chunk:
                        raise errors.AnsibleError('ssh connection closed waiting for sudo or su password prompt')
                    sudo_errput += chunk
                    incorrect_password = gettext.dgettext(
                        "sudo", "Sorry, try again.")
                    if sudo_errput.strip().endswith("%s%s" % (prompt, incorrect_password)):
                        raise errors.AnsibleError('Incorrect sudo password')
                    elif sudo_errput.endswith(prompt):
                        stdin.write(self.runner.sudo_pass + '\n')

                if p.stdout in rfd:
                    chunk = p.stdout.read()
                    if not chunk:
                        raise errors.AnsibleError('ssh connection closed waiting for sudo or su password prompt')
                    sudo_output += chunk

                if not rfd:
                    # timeout. wrap up process communication
                    stdout = p.communicate()
                    raise errors.AnsibleError('ssh connection error waiting for sudo or su password prompt')

            if success_key not in sudo_output:
                if sudoable:
                    stdin.write(self.runner.sudo_pass + '\n')
                elif su:
                    stdin.write(self.runner.su_pass + '\n')

        (returncode, stdout, stderr) = self._communicate(p, stdin, in_data, su=su, sudoable=sudoable, prompt=prompt)

        if C.HOST_KEY_CHECKING and not_in_host_file:
            # lock around the initial SSH connectivity so the user prompt about whether to add 
            # the host to known hosts is not intermingled with multiprocess output.
            fcntl.lockf(self.runner.output_lockfile, fcntl.LOCK_UN)
            fcntl.lockf(self.runner.process_lockfile, fcntl.LOCK_UN)
        controlpersisterror = 'Bad configuration option: ControlPersist' in stderr or \
                              'unknown configuration option: ControlPersist' in stderr

        if C.HOST_KEY_CHECKING:
            if ssh_cmd[0] == "sshpass" and p.returncode == 6:
                raise errors.AnsibleError('Using a SSH password instead of a key is not possible because Host Key checking is enabled and sshpass does not support this.  Please add this host\'s fingerprint to your known_hosts file to manage this host.')

        if p.returncode != 0 and controlpersisterror:
            raise errors.AnsibleError('using -c ssh on certain older ssh versions may not support ControlPersist, set ANSIBLE_SSH_ARGS="" (or ssh_args in [ssh_connection] section of the config file) before running again')
        if p.returncode == 255 and (in_data or self.runner.module_name == 'raw'):
            raise errors.AnsibleError('SSH Error: data could not be sent to the remote host. Make sure this host can be reached over ssh')

        return (p.returncode, '', stdout, stderr)

    def put_file(self, in_path, out_path):
        ''' transfer a file from local to remote '''
        vvv("PUT %s TO %s" % (in_path, out_path), host=self.host)
        if not os.path.exists(in_path):
            raise errors.AnsibleFileNotFound("file or module does not exist: %s" % in_path)
        cmd = self._password_cmd()

        host = self.host
        if self.ipv6:
            host = '[%s]' % host

        if C.DEFAULT_SCP_IF_SSH:
            cmd += ["scp"] + self.common_args
            cmd += [in_path,host + ":" + pipes.quote(out_path)]
            indata = None
        else:
            cmd += ["sftp"] + self.common_args + [host]
            indata = "put %s %s\n" % (pipes.quote(in_path), pipes.quote(out_path))

        (p, stdin) = self._run(cmd, indata)

        self._send_password()

        (returncode, stdout, stderr) = self._communicate(p, stdin, indata)

        if returncode != 0:
            raise errors.AnsibleError("failed to transfer file to %s:\n%s\n%s" % (out_path, stdout, stderr))

    def fetch_file(self, in_path, out_path):
        ''' fetch a file from remote to local '''
        vvv("FETCH %s TO %s" % (in_path, out_path), host=self.host)
        cmd = self._password_cmd()

        host = self.host
        if self.ipv6:
            host = '[%s]' % host

        if C.DEFAULT_SCP_IF_SSH:
            cmd += ["scp"] + self.common_args
            cmd += [host + ":" + in_path, out_path]
            indata = None
        else:
            cmd += ["sftp"] + self.common_args + [host]
            indata = "get %s %s\n" % (in_path, out_path)

        p = subprocess.Popen(cmd, stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self._send_password()
        stdout, stderr = p.communicate(indata)

        if p.returncode != 0:
            raise errors.AnsibleError("failed to transfer file from %s:\n%s\n%s" % (in_path, stdout, stderr))

    def close(self):
        ''' not applicable since we're executing openssh binaries '''
        pass


########NEW FILE########
__FILENAME__ = core
# (c) 2012, Jeroen Hoekx <jeroen@hoekx.be>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

import base64
import json
import os.path
import yaml
import types
import pipes
import glob
import re
import operator as py_operator
from ansible import errors
from ansible.utils import md5s
from distutils.version import LooseVersion, StrictVersion
from random import SystemRandom

def to_nice_yaml(*a, **kw):
    '''Make verbose, human readable yaml'''
    return yaml.safe_dump(*a, indent=4, allow_unicode=True, default_flow_style=False, **kw)

def to_json(a, *args, **kw):
    ''' Convert the value to JSON '''
    return json.dumps(a, *args, **kw)

def to_nice_json(a, *args, **kw):
    '''Make verbose, human readable JSON'''
    return json.dumps(a, indent=4, sort_keys=True, *args, **kw)

def failed(*a, **kw):
    ''' Test if task result yields failed '''
    item = a[0]
    if type(item) != dict:
        raise errors.AnsibleFilterError("|failed expects a dictionary")
    rc = item.get('rc',0)
    failed = item.get('failed',False)
    if rc != 0 or failed:
        return True
    else:
        return False

def success(*a, **kw):
    ''' Test if task result yields success '''
    return not failed(*a, **kw)

def changed(*a, **kw):
    ''' Test if task result yields changed '''
    item = a[0]
    if type(item) != dict:
        raise errors.AnsibleFilterError("|changed expects a dictionary")
    if not 'changed' in item:
        changed = False
        if ('results' in item    # some modules return a 'results' key
                and type(item['results']) == list
                and type(item['results'][0]) == dict):
            for result in item['results']:
                changed = changed or result.get('changed', False)
    else:
        changed = item.get('changed', False)
    return changed

def skipped(*a, **kw):
    ''' Test if task result yields skipped '''
    item = a[0]
    if type(item) != dict:
        raise errors.AnsibleFilterError("|skipped expects a dictionary")
    skipped = item.get('skipped', False)
    return skipped

def mandatory(a):
    ''' Make a variable mandatory '''
    try:
        a
    except NameError:
        raise errors.AnsibleFilterError('Mandatory variable not defined.')
    else:
        return a

def bool(a):
    ''' return a bool for the arg '''
    if a is None or type(a) == bool:
        return a
    if type(a) in types.StringTypes:
        a = a.lower()
    if a in ['yes', 'on', '1', 'true', 1]:
        return True
    else:
        return False

def quote(a):
    ''' return its argument quoted for shell usage '''
    return pipes.quote(a)

def fileglob(pathname):
    ''' return list of matched files for glob '''
    return glob.glob(pathname)

def regex(value='', pattern='', ignorecase=False, match_type='search'):
    ''' Expose `re` as a boolean filter using the `search` method by default.
        This is likely only useful for `search` and `match` which already
        have their own filters.
    '''
    if ignorecase:
        flags = re.I
    else:
        flags = 0
    _re = re.compile(pattern, flags=flags)
    _bool = __builtins__.get('bool')
    return _bool(getattr(_re, match_type, 'search')(value))

def match(value, pattern='', ignorecase=False):
    ''' Perform a `re.match` returning a boolean '''
    return regex(value, pattern, ignorecase, 'match')

def search(value, pattern='', ignorecase=False):
    ''' Perform a `re.search` returning a boolean '''
    return regex(value, pattern, ignorecase, 'search')

def regex_replace(value='', pattern='', replacement='', ignorecase=False):
    ''' Perform a `re.sub` returning a string '''

    if not isinstance(value, basestring):
        value = str(value)

    if ignorecase:
        flags = re.I
    else:
        flags = 0
    _re = re.compile(pattern, flags=flags)
    return _re.sub(replacement, value)

def unique(a):
    return set(a)

def intersect(a, b):
    return set(a).intersection(b)

def difference(a, b):
    return set(a).difference(b)

def symmetric_difference(a, b):
    return set(a).symmetric_difference(b)

def union(a, b):
    return set(a).union(b)

def version_compare(value, version, operator='eq', strict=False):
    ''' Perform a version comparison on a value '''
    op_map = {
        '==': 'eq', '=':  'eq', 'eq': 'eq',
        '<':  'lt', 'lt': 'lt',
        '<=': 'le', 'le': 'le',
        '>':  'gt', 'gt': 'gt',
        '>=': 'ge', 'ge': 'ge',
        '!=': 'ne', '<>': 'ne', 'ne': 'ne'
    }

    if strict:
        Version = StrictVersion
    else:
        Version = LooseVersion

    if operator in op_map:
        operator = op_map[operator]
    else:
        raise errors.AnsibleFilterError('Invalid operator type')

    try:
        method = getattr(py_operator, operator)
        return method(Version(str(value)), Version(str(version)))
    except Exception, e:
        raise errors.AnsibleFilterError('Version comparison: %s' % e)

def rand(end, start=None, step=None):
    r = SystemRandom()
    if isinstance(end, (int, long)):
        if not start:
            start = 0
        if not step:
            step = 1
        return r.randrange(start, end, step)
    elif hasattr(end, '__iter__'):
        if start or step:
            raise errors.AnsibleFilterError('start and step can only be used with integer values')
        return r.choice(end)
    else:
        raise errors.AnsibleFilterError('random can only be used on sequences and integers')

class FilterModule(object):
    ''' Ansible core jinja2 filters '''

    def filters(self):
        return {
            # base 64
            'b64decode': base64.b64decode,
            'b64encode': base64.b64encode,

            # json
            'to_json': to_json,
            'to_nice_json': to_nice_json,
            'from_json': json.loads,

            # yaml
            'to_yaml': yaml.safe_dump,
            'to_nice_yaml': to_nice_yaml,
            'from_yaml': yaml.safe_load,

            # path
            'basename': os.path.basename,
            'dirname': os.path.dirname,
            'expanduser': os.path.expanduser,
            'realpath': os.path.realpath,

            # failure testing
            'failed'  : failed,
            'success' : success,

            # changed testing
            'changed' : changed,

            # skip testing
            'skipped' : skipped,

            # variable existence
            'mandatory': mandatory,

            # value as boolean
            'bool': bool,

            # quote string for shell usage
            'quote': quote,

            # md5 hex digest of string
            'md5': md5s,

            # file glob
            'fileglob': fileglob,

            # regex
            'match': match,
            'search': search,
            'regex': regex,
            'regex_replace': regex_replace,

            # list
            'unique' : unique,
            'intersect': intersect,
            'difference': difference,
            'symmetric_difference': symmetric_difference,
            'union': union,

            # version comparison
            'version_compare': version_compare,

            # random numbers
            'random': rand,
        }


########NEW FILE########
__FILENAME__ = csvfile
# (c) 2013, Jan-Piet Mens <jpmens(at)gmail.com>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

from ansible import utils, errors
import os
import codecs
import csv

class LookupModule(object):

    def __init__(self, basedir=None, **kwargs):
        self.basedir = basedir

    def read_csv(self, filename, key, delimiter, dflt=None, col=1):

        try:
            f = codecs.open(filename, 'r', encoding='utf-8')
            creader = csv.reader(f, delimiter=delimiter)

            for row in creader:
                if row[0] == key:
                    return row[int(col)]
        except Exception, e:
            raise errors.AnsibleError("csvfile: %s" % str(e))

        return dflt

    def run(self, terms, inject=None, **kwargs):

        terms = utils.listify_lookup_plugin_terms(terms, self.basedir, inject)

        if isinstance(terms, basestring):
            terms = [ terms ]

        ret = []
        for term in terms:
            params = term.split()
            key = params[0]

            paramvals = {
                'file' : 'ansible.csv',
                'default' : None,
                'delimiter' : "TAB",
                'col' : "1",          # column to return
            }

            # parameters specified?
            try:
                for param in params[1:]:
                    name, value = param.split('=')
                    assert(name in paramvals)
                    paramvals[name] = value
            except (ValueError, AssertionError), e:
                raise errors.AnsibleError(e)

            if paramvals['delimiter'] == 'TAB':
                paramvals['delimiter'] = "\t"

            path = utils.path_dwim(self.basedir, paramvals['file'])

            var = self.read_csv(path, key, paramvals['delimiter'], paramvals['default'], paramvals['col'])
            if var is not None:
                if type(var) is list:
                    for v in var:
                        ret.append(v)
                else:
                    ret.append(var)
        return ret

########NEW FILE########
__FILENAME__ = dict
# (c) 2014, Kent R. Spillner <kspillner@acm.org>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

from ansible.utils import safe_eval
import ansible.utils as utils
import ansible.errors as errors

def flatten_hash_to_list(terms):
    ret = []
    for key in terms:
        ret.append({'key': key, 'value': terms[key]})
    return ret

class LookupModule(object):

    def __init__(self, basedir=None, **kwargs):
        self.basedir = basedir

    def run(self, terms, inject=None, **kwargs):
        terms = utils.listify_lookup_plugin_terms(terms, self.basedir, inject)

        if not isinstance(terms, dict):
            raise errors.AnsibleError("with_dict expects a dict")

        return flatten_hash_to_list(terms)

########NEW FILE########
__FILENAME__ = dnstxt
# (c) 2012, Jan-Piet Mens <jpmens(at)gmail.com>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

from ansible import utils, errors
import os
HAVE_DNS=False
try:
    import dns.resolver
    from dns.exception import DNSException
    HAVE_DNS=True
except ImportError:
    pass

# ==============================================================
# DNSTXT: DNS TXT records
#
#       key=domainname
# TODO: configurable resolver IPs
# --------------------------------------------------------------

class LookupModule(object):

    def __init__(self, basedir=None, **kwargs):
        self.basedir = basedir

        if HAVE_DNS == False:
            raise errors.AnsibleError("Can't LOOKUP(dnstxt): module dns.resolver is not installed")

    def run(self, terms, inject=None, **kwargs):

        terms = utils.listify_lookup_plugin_terms(terms, self.basedir, inject) 

        if isinstance(terms, basestring):
            terms = [ terms ]

        ret = []
        for term in terms:
            domain = term.split()[0]
            string = []
            try:
                answers = dns.resolver.query(domain, 'TXT')
                for rdata in answers:
                    s = rdata.to_text()
                    string.append(s[1:-1])  # Strip outside quotes on TXT rdata

            except dns.resolver.NXDOMAIN:
                string = 'NXDOMAIN'
            except dns.resolver.Timeout:
                string = ''
            except dns.exception.DNSException, e:
                raise errors.AnsibleError("dns.resolver unhandled exception", e)

            ret.append(''.join(string))
        return ret

########NEW FILE########
__FILENAME__ = env
# (c) 2012, Jan-Piet Mens <jpmens(at)gmail.com>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

from ansible import utils, errors
from ansible.utils import template
import os

class LookupModule(object):

    def __init__(self, basedir=None, **kwargs):
        self.basedir = basedir

    def run(self, terms, inject=None, **kwargs):

        try:
            terms = template.template(self.basedir, terms, inject)
        except Exception, e:
            pass

        if isinstance(terms, basestring):
            terms = [ terms ]

        ret = []
        for term in terms:
            var = term.split()[0]
            ret.append(os.getenv(var, ''))
        return ret

########NEW FILE########
__FILENAME__ = etcd
# (c) 2013, Jan-Piet Mens <jpmens(at)gmail.com>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

from ansible import utils
import os
import urllib2
try:
    import json
except ImportError:
    import simplejson as json

# this can be made configurable, not should not use ansible.cfg
ANSIBLE_ETCD_URL = 'http://127.0.0.1:4001'
if os.getenv('ANSIBLE_ETCD_URL') is not None:
    ANSIBLE_ETCD_URL = os.environ['ANSIBLE_ETCD_URL']

class etcd():
    def __init__(self, url=ANSIBLE_ETCD_URL):
        self.url = url
        self.baseurl = '%s/v1/keys' % (self.url)

    def get(self, key):
        url = "%s/%s" % (self.baseurl, key)

        data = None
        value = ""
        try:
            r = urllib2.urlopen(url)
            data = r.read()
        except:
            return value

        try:
            # {"action":"get","key":"/name","value":"Jane Jolie","index":5}
            item = json.loads(data)
            if 'value' in item:
                value = item['value']
            if 'errorCode' in item:
                value = "ENOENT"
        except:
            raise
            pass

        return value

class LookupModule(object):

    def __init__(self, basedir=None, **kwargs):
        self.basedir = basedir
        self.etcd = etcd()

    def run(self, terms, inject=None, **kwargs):

        terms = utils.listify_lookup_plugin_terms(terms, self.basedir, inject)

        if isinstance(terms, basestring):
            terms = [ terms ]

        ret = []
        for term in terms:
            key = term.split()[0]
            value = self.etcd.get(key)
            ret.append(value)
        return ret

########NEW FILE########
__FILENAME__ = file
# (c) 2012, Daniel Hokka Zakrisson <daniel@hozac.com>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

from ansible import utils, errors
import os
import codecs

class LookupModule(object):

    def __init__(self, basedir=None, **kwargs):
        self.basedir = basedir

    def run(self, terms, inject=None, **kwargs):

        terms = utils.listify_lookup_plugin_terms(terms, self.basedir, inject)
        ret = []

        # this can happen if the variable contains a string, strictly not desired for lookup
        # plugins, but users may try it, so make it work.
        if not isinstance(terms, list):
            terms = [ terms ]

        for term in terms:
            path = utils.path_dwim(self.basedir, term)
            if not os.path.exists(path):
                raise errors.AnsibleError("%s does not exist" % path)

            ret.append(codecs.open(path, encoding="utf8").read().rstrip())


        return ret

########NEW FILE########
__FILENAME__ = fileglob
# (c) 2012, Michael DeHaan <michael.dehaan@gmail.com>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

import os
import glob
from ansible import utils

class LookupModule(object):

    def __init__(self, basedir=None, **kwargs):
        self.basedir = basedir

    def run(self, terms, inject=None, **kwargs):

        terms = utils.listify_lookup_plugin_terms(terms, self.basedir, inject)

        ret = []

        for term in terms:

            dwimmed = utils.path_dwim(self.basedir, term)
            globbed = glob.glob(dwimmed)
            ret.extend(g for g in globbed if os.path.isfile(g))

        return ret

########NEW FILE########
__FILENAME__ = first_found
# (c) 2013, seth vidal <skvidal@fedoraproject.org> red hat, inc
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.


# take a list of files and (optionally) a list of paths
# return the first existing file found in the paths
# [file1, file2, file3], [path1, path2, path3]
# search order is:
# path1/file1
# path1/file2
# path1/file3
# path2/file1
# path2/file2
# path2/file3
# path3/file1
# path3/file2
# path3/file3

# first file found with os.path.exists() is returned
# no file matches raises ansibleerror
# EXAMPLES
#  - name: copy first existing file found to /some/file
#    action: copy src=$item dest=/some/file
#    with_first_found: 
#     - files: foo ${inventory_hostname} bar
#       paths: /tmp/production /tmp/staging

# that will look for files in this order:
# /tmp/production/foo
#                 ${inventory_hostname}
#                 bar
# /tmp/staging/foo
#              ${inventory_hostname}
#              bar
                  
#  - name: copy first existing file found to /some/file
#    action: copy src=$item dest=/some/file
#    with_first_found: 
#     - files: /some/place/foo ${inventory_hostname} /some/place/else

#  that will look for files in this order:
#  /some/place/foo
#  $relative_path/${inventory_hostname}
#  /some/place/else

# example - including tasks:
#  tasks:
#  - include: $item
#    with_first_found:
#     - files: generic
#       paths: tasks/staging tasks/production
# this will include the tasks in the file generic where it is found first (staging or production)

# example simple file lists
#tasks:
#- name: first found file
#  action: copy src=$item dest=/etc/file.cfg
#  with_first_found:
#  - files: foo.${inventory_hostname} foo


# example skipping if no matched files
# First_found also offers the ability to control whether or not failing
# to find a file returns an error or not
#
#- name: first found file - or skip
#  action: copy src=$item dest=/etc/file.cfg
#  with_first_found:
#  - files: foo.${inventory_hostname}
#    skip: true

# example a role with default configuration and configuration per host
# you can set multiple terms with their own files and paths to look through.
# consider a role that sets some configuration per host falling back on a default config.
#
#- name: some configuration template
#  template: src={{ item }} dest=/etc/file.cfg mode=0444 owner=root group=root
#  with_first_found:
#   - files:
#      - ${inventory_hostname}/etc/file.cfg
#     paths:
#      - ../../../templates.overwrites
#      - ../../../templates
#   - files:
#      - etc/file.cfg
#     paths:
#      - templates

# the above will return an empty list if the files cannot be found at all
# if skip is unspecificed or if it is set to false then it will return a list 
# error which can be caught bye ignore_errors: true for that action.

# finally - if you want you can use it, in place to replace first_available_file:
# you simply cannot use the - files, path or skip options. simply replace
# first_available_file with with_first_found and leave the file listing in place
#
#
#  - name: with_first_found like first_available_file
#    action: copy src=$item dest=/tmp/faftest
#    with_first_found:
#     - ../files/foo
#     - ../files/bar
#     - ../files/baz
#    ignore_errors: true


from ansible import utils, errors
import os

class LookupModule(object):

    def __init__(self, basedir=None, **kwargs):
        self.basedir = basedir

    def run(self, terms, inject=None, **kwargs):

        terms = utils.listify_lookup_plugin_terms(terms, self.basedir, inject)

        result = None
        anydict = False
        skip = False

        for term in terms:
            if isinstance(term, dict):
                anydict = True

        total_search = []
        if anydict:
            for term in terms:
                if isinstance(term, dict):
                    files = term.get('files', [])
                    paths = term.get('paths', [])
                    skip  = utils.boolean(term.get('skip', False))

                    filelist = files
                    if isinstance(files, basestring):
                        files = files.replace(',', ' ')
                        files = files.replace(';', ' ')
                        filelist = files.split(' ')

                    pathlist = paths
                    if paths:
                        if isinstance(paths, basestring):
                            paths = paths.replace(',', ' ')
                            paths = paths.replace(':', ' ')
                            paths = paths.replace(';', ' ')
                            pathlist = paths.split(' ')

                    if not pathlist:
                        total_search = filelist
                    else:
                        for path in pathlist:
                            for fn in filelist:
                                f = os.path.join(path, fn)
                                total_search.append(f)
                else:
                    total_search.append(term)
        else:
            total_search = terms

        result = None
        for fn in total_search:
            path = utils.path_dwim(self.basedir, fn)
            if os.path.exists(path):
                return [path]


        if not result:
            if skip:
                return []
            else:
                return [None]


########NEW FILE########
__FILENAME__ = flattened
# (c) 2013, Serge van Ginderachter <serge@vanginderachter.be>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

import ansible.utils as utils
import ansible.errors as errors


def check_list_of_one_list(term):
    # make sure term is not a list of one (list of one..) item
    # return the final non list item if so

    if isinstance(term,list) and len(term) == 1:
        term = term[0]
        if isinstance(term,list):
            term = check_list_of_one_list(term)

    return term



class LookupModule(object):

    def __init__(self, basedir=None, **kwargs):
        self.basedir = basedir


    def flatten(self, terms, inject):

        ret = []
        for term in terms:
            term = check_list_of_one_list(term)

            if term == 'None' or term == 'null':
                # ignore undefined items
                break

            if isinstance(term, basestring):
                # convert a variable to a list
                term2 = utils.listify_lookup_plugin_terms(term, self.basedir, inject)
                # but avoid converting a plain string to a list of one string
                if term2 != [ term ]:
                    term = term2

            if isinstance(term, list):
                # if it's a list, check recursively for items that are a list
                term = self.flatten(term, inject)
                ret.extend(term)
            else:   
                ret.append(term)

        return ret


    def run(self, terms, inject=None, **kwargs):

        # see if the string represents a list and convert to list if so
        terms = utils.listify_lookup_plugin_terms(terms, self.basedir, inject)

        if not isinstance(terms, list):
            raise errors.AnsibleError("with_flattened expects a list")

        ret = self.flatten(terms, inject)
        return ret


########NEW FILE########
__FILENAME__ = indexed_items
# (c) 2012, Michael DeHaan <michael.dehaan@gmail.com>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

from ansible.utils import safe_eval
import ansible.utils as utils
import ansible.errors as errors

def flatten(terms):
    ret = []
    for term in terms:
        if isinstance(term, list):
            ret.extend(term)
        else:
            ret.append(term)
    return ret

class LookupModule(object):

    def __init__(self, basedir=None, **kwargs):
        self.basedir = basedir

    def run(self, terms, inject=None, **kwargs):
        terms = utils.listify_lookup_plugin_terms(terms, self.basedir, inject)

        if not isinstance(terms, list):
            raise errors.AnsibleError("with_indexed_items expects a list")

        items = flatten(terms)
        return zip(range(len(items)), items)


########NEW FILE########
__FILENAME__ = inventory_hostnames
# (c) 2012, Michael DeHaan <michael.dehaan@gmail.com>
# (c) 2013, Steven Dossett <sdossett@panath.com>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

from ansible.utils import safe_eval
import ansible.utils as utils
import ansible.errors as errors
import ansible.inventory as inventory

def flatten(terms):
    ret = []
    for term in terms:
        if isinstance(term, list):
            ret.extend(term)
        else:
            ret.append(term)
    return ret

class LookupModule(object):

    def __init__(self, basedir=None, **kwargs):
        self.basedir = basedir
        if 'runner' in kwargs:
            self.host_list = kwargs['runner'].inventory.host_list
        else:
            raise errors.AnsibleError("inventory_hostnames must be used as a loop. Example: \"with_inventory_hostnames: \'all\'\"")

    def run(self, terms, inject=None, **kwargs):
        terms = utils.listify_lookup_plugin_terms(terms, self.basedir, inject) 

        if not isinstance(terms, list):
            raise errors.AnsibleError("with_inventory_hostnames expects a list")
        return flatten(inventory.Inventory(self.host_list).list_hosts(terms))


########NEW FILE########
__FILENAME__ = items
# (c) 2012, Michael DeHaan <michael.dehaan@gmail.com>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

from ansible.utils import safe_eval
import ansible.utils as utils
import ansible.errors as errors

def flatten(terms):
    ret = []
    for term in terms:
        if isinstance(term, list):
            ret.extend(term)
        else:
            ret.append(term)
    return ret

class LookupModule(object):

    def __init__(self, basedir=None, **kwargs):
        self.basedir = basedir

    def run(self, terms, inject=None, **kwargs):
        terms = utils.listify_lookup_plugin_terms(terms, self.basedir, inject) 

        if not isinstance(terms, list) and not isinstance(terms,set):
            raise errors.AnsibleError("with_items expects a list or a set")

        return flatten(terms)



########NEW FILE########
__FILENAME__ = lines
# (c) 2012, Daniel Hokka Zakrisson <daniel@hozac.com>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

import subprocess
from ansible import utils, errors

class LookupModule(object):

    def __init__(self, basedir=None, **kwargs):
        self.basedir = basedir

    def run(self, terms, inject=None, **kwargs):

        terms = utils.listify_lookup_plugin_terms(terms, self.basedir, inject) 

        ret = []
        for term in terms:
            p = subprocess.Popen(term, cwd=self.basedir, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            (stdout, stderr) = p.communicate()
            if p.returncode == 0:
                ret.extend(stdout.splitlines())
            else:
                raise errors.AnsibleError("lookup_plugin.lines(%s) returned %d" % (term, p.returncode))
        return ret

########NEW FILE########
__FILENAME__ = nested
# (c) 2012, Michael DeHaan <michael.dehaan@gmail.com>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

import ansible.utils as utils
from ansible.utils import safe_eval
import ansible.errors as errors

def flatten(terms):
    ret = []
    for term in terms:
        if isinstance(term, list):
            ret.extend(term)
        elif isinstance(term, tuple):
            ret.extend(term)
        else:
            ret.append(term)
    return ret

def combine(a,b):
    results = []
    for x in a:
        for y in b:
            results.append(flatten([x,y]))
    return results

class LookupModule(object):

    def __init__(self, basedir=None, **kwargs):
        self.basedir = basedir

    def __lookup_injects(self, terms, inject):
        results = []
        for x in terms:
            intermediate = utils.listify_lookup_plugin_terms(x, self.basedir, inject)
            results.append(intermediate)
        return results

    def run(self, terms, inject=None, **kwargs):

        # this code is common with 'items.py' consider moving to utils if we need it again

        terms = utils.listify_lookup_plugin_terms(terms, self.basedir, inject)
        terms = self.__lookup_injects(terms, inject)

        my_list = terms[:]
        my_list.reverse()
        result = []
        if len(my_list) == 0:
            raise errors.AnsibleError("with_nested requires at least one element in the nested list")
        result = my_list.pop()
        while len(my_list) > 0:
            result2 = combine(result, my_list.pop())
            result  = result2
        new_result = []
        for x in result:
            new_result.append(flatten(x))
        return new_result



########NEW FILE########
__FILENAME__ = password
# (c) 2012, Daniel Hokka Zakrisson <daniel@hozac.com>
# (c) 2013, Javier Candeira <javier@candeira.com>
# (c) 2013, Maykel Moya <mmoya@speedyrails.com>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

from ansible import utils, errors
import os
import errno
from string import ascii_letters, digits
import string
import random


class LookupModule(object):

    LENGTH = 20

    def __init__(self, length=None, encrypt=None, basedir=None, **kwargs):
        self.basedir = basedir

    def random_salt(self):
        salt_chars = ascii_letters + digits + './'
        return utils.random_password(length=8, chars=salt_chars)

    def run(self, terms, inject=None, **kwargs):

        terms = utils.listify_lookup_plugin_terms(terms, self.basedir, inject) 

        ret = []

        for term in terms:
            # you can't have escaped spaces in yor pathname
            params = term.split()
            relpath = params[0]

            paramvals = {
                'length': LookupModule.LENGTH,
                'encrypt': None,
                'chars': ['ascii_letters','digits',".,:-_"],
            }

            # get non-default parameters if specified
            try:
                for param in params[1:]:
                    name, value = param.split('=')
                    assert(name in paramvals)
                    if name == 'length':
                        paramvals[name] = int(value)
                    elif name == 'chars':
                        use_chars=[]
                        if ",," in value: 
                            use_chars.append(',')
                        use_chars.extend(value.replace(',,',',').split(','))
                        paramvals['chars'] = use_chars
                    else:
                        paramvals[name] = value
            except (ValueError, AssertionError), e:
                raise errors.AnsibleError(e)

            length  = paramvals['length']
            encrypt = paramvals['encrypt']
            use_chars = paramvals['chars']

            # get password or create it if file doesn't exist
            path = utils.path_dwim(self.basedir, relpath)
            if not os.path.exists(path):
                pathdir = os.path.dirname(path)
                if not os.path.isdir(pathdir):
                    os.makedirs(pathdir)

                chars = "".join([getattr(string,c,c) for c in use_chars]).replace('"','').replace("'",'')
                password = ''.join(random.choice(chars) for _ in range(length))

                if encrypt is not None:
                    salt = self.random_salt()
                    content = '%s salt=%s' % (password, salt)
                else:
                    content = password
                with open(path, 'w') as f:
                    f.write(content + '\n')
            else:
                content = open(path).read().rstrip()
                sep = content.find(' ')

                if sep >= 0:
                    password = content[:sep]
                    salt = content[sep+1:].split('=')[1]
                else:
                    password = content
                    salt = None

                # crypt requested, add salt if missing
                if (encrypt is not None and not salt):
                    salt = self.random_salt()
                    content = '%s salt=%s' % (password, salt)
                    with open(path, 'w') as f:
                        f.write(content + '\n')
                # crypt not requested, remove salt if present
                elif (encrypt is None and salt):
                    with open(path, 'w') as f:
                        f.write(password + '\n')

            if encrypt:
                password = utils.do_encrypt(password, encrypt, salt=salt)

            ret.append(password)

        return ret


########NEW FILE########
__FILENAME__ = pipe
# (c) 2012, Daniel Hokka Zakrisson <daniel@hozac.com>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

import subprocess
from ansible import utils, errors

class LookupModule(object):

    def __init__(self, basedir=None, **kwargs):
        self.basedir = basedir

    def run(self, terms, inject=None, **kwargs):

        terms = utils.listify_lookup_plugin_terms(terms, self.basedir, inject) 

        if isinstance(terms, basestring):
            terms = [ terms ] 

        ret = []
        for term in terms:
            '''
            http://docs.python.org/2/library/subprocess.html#popen-constructor

            The shell argument (which defaults to False) specifies whether to use the 
            shell as the program to execute. If shell is True, it is recommended to pass 
            args as a string rather than as a sequence

            https://github.com/ansible/ansible/issues/6550
            '''
            term = str(term)

            p = subprocess.Popen(term, cwd=self.basedir, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            (stdout, stderr) = p.communicate()
            if p.returncode == 0:
                ret.append(stdout.decode("utf-8").rstrip())
            else:
                raise errors.AnsibleError("lookup_plugin.pipe(%s) returned %d" % (term, p.returncode))
        return ret

########NEW FILE########
__FILENAME__ = random_choice
# (c) 2013, Michael DeHaan <michael.dehaan@gmail.com>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

import random
from ansible import utils

# useful for introducing chaos ... or just somewhat reasonably fair selection
# amongst available mirrors
#
#    tasks:
#        - debug: msg=$item
#          with_random_choice:
#             - one
#             - two 
#             - three

class LookupModule(object):

    def __init__(self, basedir=None, **kwargs):
        self.basedir = basedir

    def run(self, terms, inject=None, **kwargs):

        terms = utils.listify_lookup_plugin_terms(terms, self.basedir, inject) 

        return [ random.choice(terms) ]


########NEW FILE########
__FILENAME__ = redis_kv
# (c) 2012, Jan-Piet Mens <jpmens(at)gmail.com>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

from ansible import utils, errors
import os
HAVE_REDIS=False
try:
    import redis        # https://github.com/andymccurdy/redis-py/
    HAVE_REDIS=True
except ImportError:
    pass
import re

# ==============================================================
# REDISGET: Obtain value from a GET on a Redis key. Terms
# expected: 0 = URL, 1 = Key
# URL may be empty, in which case redis://localhost:6379 assumed
# --------------------------------------------------------------

class LookupModule(object):

    def __init__(self, basedir=None, **kwargs):
        self.basedir = basedir

        if HAVE_REDIS == False:
            raise errors.AnsibleError("Can't LOOKUP(redis_kv): module redis is not installed")

    def run(self, terms, inject=None, **kwargs):

        terms = utils.listify_lookup_plugin_terms(terms, self.basedir, inject) 

        ret = []
        for term in terms:
            (url,key) = term.split(',')
            if url == "":
                url = 'redis://localhost:6379'

            # urlsplit on Python 2.6.1 is broken. Hmm. Probably also the reason
            # Redis' from_url() doesn't work here.

            p = '(?P<scheme>[^:]+)://?(?P<host>[^:/ ]+).?(?P<port>[0-9]*).*'

            try:
                m = re.search(p, url)
                host = m.group('host')
                port = int(m.group('port'))
            except AttributeError:
                raise errors.AnsibleError("Bad URI in redis lookup")

            try:
                conn = redis.Redis(host=host, port=port)
                res = conn.get(key)
                if res is None:
                    res = ""
                ret.append(res)
            except:
                ret.append("")  # connection failed or key not found
        return ret

########NEW FILE########
__FILENAME__ = sequence
# (c) 2013, Jayson Vantuyl <jayson@aggressive.ly>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

from ansible.errors import AnsibleError
import ansible.utils as utils
from re import compile as re_compile, IGNORECASE

# shortcut format
NUM = "(0?x?[0-9a-f]+)"
SHORTCUT = re_compile(
    "^(" +        # Group 0
    NUM +         # Group 1: Start
    "-)?" +
    NUM +         # Group 2: End
    "(/" +        # Group 3
    NUM +         # Group 4: Stride
    ")?" +
    "(:(.+))?$",  # Group 5, Group 6: Format String
    IGNORECASE
)


class LookupModule(object):
    """
    sequence lookup module

    Used to generate some sequence of items. Takes arguments in two forms.

    The simple / shortcut form is:

      [start-]end[/stride][:format]

    As indicated by the brackets: start, stride, and format string are all
    optional.  The format string is in the style of printf.  This can be used
    to pad with zeros, format in hexadecimal, etc.  All of the numerical values
    can be specified in octal (i.e. 0664) or hexadecimal (i.e. 0x3f8).
    Negative numbers are not supported.

    Some examples:

      5 -> ["1","2","3","4","5"]
      5-8 -> ["5", "6", "7", "8"]
      2-10/2 -> ["2", "4", "6", "8", "10"]
      4:host%02d -> ["host01","host02","host03","host04"]

    The standard Ansible key-value form is accepted as well.  For example:

      start=5 end=11 stride=2 format=0x%02x -> ["0x05","0x07","0x09","0x0a"]

    This format takes an alternate form of "end" called "count", which counts
    some number from the starting value.  For example:

      count=5 -> ["1", "2", "3", "4", "5"]
      start=0x0f00 count=4 format=%04x -> ["0f00", "0f01", "0f02", "0f03"]
      start=0 count=5 stride=2 -> ["0", "2", "4", "6", "8"]
      start=1 count=5 stride=2 -> ["1", "3", "5", "7", "9"]

    The count option is mostly useful for avoiding off-by-one errors and errors
    calculating the number of entries in a sequence when a stride is specified.
    """

    def __init__(self, basedir, **kwargs):
        """absorb any keyword args"""
        self.basedir = basedir

    def reset(self):
        """set sensible defaults"""
        self.start = 1
        self.count = None
        self.end = None
        self.stride = 1
        self.format = "%d"

    def parse_kv_args(self, args):
        """parse key-value style arguments"""
        for arg in ["start", "end", "count", "stride"]:
            try:
                arg_raw = args.pop(arg, None)
                if arg_raw is None:
                    continue
                arg_cooked = int(arg_raw, 0)
                setattr(self, arg, arg_cooked)
            except ValueError:
                raise AnsibleError(
                    "can't parse arg %s=%r as integer"
                        % (arg, arg_raw)
                )
            if 'format' in args:
                self.format = args.pop("format")
        if args:
            raise AnsibleError(
                "unrecognized arguments to with_sequence: %r"
                % args.keys()
            )

    def parse_simple_args(self, term):
        """parse the shortcut forms, return True/False"""
        match = SHORTCUT.match(term)
        if not match:
            return False

        _, start, end, _, stride, _, format = match.groups()

        if start is not None:
            try:
                start = int(start, 0)
            except ValueError:
                raise AnsibleError("can't parse start=%s as integer" % start)
        if end is not None:
            try:
                end = int(end, 0)
            except ValueError:
                raise AnsibleError("can't parse end=%s as integer" % end)
        if stride is not None:
            try:
                stride = int(stride, 0)
            except ValueError:
                raise AnsibleError("can't parse stride=%s as integer" % stride)

        if start is not None:
            self.start = start
        if end is not None:
            self.end = end
        if stride is not None:
            self.stride = stride
        if format is not None:
            self.format = format

    def sanity_check(self):
        if self.count is None and self.end is None:
            raise AnsibleError(
                "must specify count or end in with_sequence"
            )
        elif self.count is not None and self.end is not None:
            raise AnsibleError(
                "can't specify both count and end in with_sequence"
            )
        elif self.count is not None:
            # convert count to end
            self.end = self.start + self.count * self.stride - 1
            del self.count
        if self.end < self.start:
            raise AnsibleError("can't count backwards")
        if self.format.count('%') != 1:
            raise AnsibleError("bad formatting string: %s" % self.format)

    def generate_sequence(self):
        numbers = xrange(self.start, self.end + 1, self.stride)

        for i in numbers:
            try:
                formatted = self.format % i
                yield formatted
            except (ValueError, TypeError):
                raise AnsibleError(
                    "problem formatting %r with %r" % self.format
                )

    def run(self, terms, inject=None, **kwargs):
        results = []

        terms = utils.listify_lookup_plugin_terms(terms, self.basedir, inject)

        if isinstance(terms, basestring):
            terms = [ terms ]

        for term in terms:
            try:
                self.reset()  # clear out things for this iteration

                try:
                    if not self.parse_simple_args(term):
                        self.parse_kv_args(utils.parse_kv(term))
                except Exception:
                    raise AnsibleError(
                        "unknown error parsing with_sequence arguments: %r"
                        % term
                    )

                self.sanity_check()

                results.extend(self.generate_sequence())
            except AnsibleError:
                raise
            except Exception:
                raise AnsibleError(
                    "unknown error generating sequence"
                )

        return results

########NEW FILE########
__FILENAME__ = subelements
# (c) 2013, Serge van Ginderachter <serge@vanginderachter.be>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

import ansible.utils as utils
import ansible.errors as errors


class LookupModule(object):

    def __init__(self, basedir=None, **kwargs):
        self.basedir = basedir


    def run(self, terms, inject=None, **kwargs):
        terms = utils.listify_lookup_plugin_terms(terms, self.basedir, inject)
        terms[0] = utils.listify_lookup_plugin_terms(terms[0], self.basedir, inject)

        if not isinstance(terms, list) or not len(terms) == 2:
            raise errors.AnsibleError(
                "subelements lookup expects a list of two items, first a dict or a list, and second a string")
        terms[0] = utils.listify_lookup_plugin_terms(terms[0], self.basedir, inject)
        if not isinstance(terms[0], (list, dict)) or not isinstance(terms[1], basestring):
            raise errors.AnsibleError(
                "subelements lookup expects a list of two items, first a dict or a list, and second a string")

        if isinstance(terms[0], dict): # convert to list:
            if terms[0].get('skipped',False) != False:
                # the registered result was completely skipped
                return []
            elementlist = []
            for key in terms[0].iterkeys():
                elementlist.append(terms[0][key])
        else: 
            elementlist = terms[0]
        subelement = terms[1]

        ret = []
        for item0 in elementlist:
            if not isinstance(item0, dict):
                raise errors.AnsibleError("subelements lookup expects a dictionary, got '%s'" %item0)
            if item0.get('skipped',False) != False:
                # this particular item is to be skipped
                continue 
            if not subelement in item0:
                raise errors.AnsibleError("could not find '%s' key in iterated item '%s'" % (subelement, item0))
            if not isinstance(item0[subelement], list):
                raise errors.AnsibleError("the key %s should point to a list, got '%s'" % (subelement, item0[subelement]))
            sublist = item0.pop(subelement, [])
            for item1 in sublist:
                ret.append((item0, item1))

        return ret


########NEW FILE########
__FILENAME__ = template
# (c) 2012, Michael DeHaan <michael.dehaan@gmail.com>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

from ansible.utils import template
import ansible.utils as utils

class LookupModule(object):

    def __init__(self, basedir=None, **kwargs):
        self.basedir = basedir

    def run(self, terms, inject=None, **kwargs):

        terms = utils.listify_lookup_plugin_terms(terms, self.basedir, inject) 

        ret = []
        for term in terms:
            ret.append(template.template_from_file(self.basedir, term, inject))
        return ret

########NEW FILE########
__FILENAME__ = together
# (c) 2013, Bradley Young <young.bradley@gmail.com>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

import ansible.utils as utils
from ansible.utils import safe_eval
import ansible.errors as errors
from itertools import izip_longest

def flatten(terms):
    ret = []
    for term in terms:
        if isinstance(term, list):
            ret.extend(term)
        elif isinstance(term, tuple):
            ret.extend(term)
        else:
            ret.append(term)
    return ret

class LookupModule(object):
    """
    Transpose a list of arrays:
    [1, 2, 3], [4, 5, 6] -> [1, 4], [2, 5], [3, 6]
    Replace any empty spots in 2nd array with None:
    [1, 2], [3] -> [1, 3], [2, None]
    """

    def __init__(self, basedir=None, **kwargs):
        self.basedir = basedir

    def __lookup_injects(self, terms, inject):
        results = []
        for x in terms:
            intermediate = utils.listify_lookup_plugin_terms(x, self.basedir, inject)
            results.append(intermediate)
        return results

    def run(self, terms, inject=None, **kwargs):

        # this code is common with 'items.py' consider moving to utils if we need it again

        terms = utils.listify_lookup_plugin_terms(terms, self.basedir, inject)
        terms = self.__lookup_injects(terms, inject)

        my_list = terms[:]
        if len(my_list) == 0:
            raise errors.AnsibleError("with_together requires at least one element in each list")
        return [flatten(x) for x in izip_longest(*my_list, fillvalue=None)]



########NEW FILE########
__FILENAME__ = poller
# (c) 2012-2014, Michael DeHaan <michael.dehaan@gmail.com>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.
#

import time

from ansible import errors

class AsyncPoller(object):
    """ Manage asynchronous jobs. """

    def __init__(self, results, runner):
        self.runner = runner

        self.results = { 'contacted': {}, 'dark': {}}
        self.hosts_to_poll = []
        self.completed = False

        # flag to determine if at least one host was contacted
        self.active = False
        # True to work with & below
        skipped = True
        for (host, res) in results['contacted'].iteritems():
            if res.get('started', False):
                self.hosts_to_poll.append(host)
                jid = res.get('ansible_job_id', None)
                self.runner.vars_cache[host]['ansible_job_id'] = jid
                self.active = True
            else:
                skipped = skipped & res.get('skipped', False)
                self.results['contacted'][host] = res
        for (host, res) in results['dark'].iteritems():
            self.runner.vars_cache[host]['ansible_job_id'] = ''
            self.results['dark'][host] = res

        if not skipped:
            if jid is None:
                raise errors.AnsibleError("unexpected error: unable to determine jid")
            if len(self.hosts_to_poll)==0:
                raise errors.AnsibleError("unexpected error: no hosts to poll")

    def poll(self):
        """ Poll the job status.

            Returns the changes in this iteration."""
        self.runner.module_name = 'async_status'
        self.runner.module_args = "jid={{ansible_job_id}}"
        self.runner.pattern = "*"
        self.runner.background = 0
        self.runner.complex_args = None

        self.runner.inventory.restrict_to(self.hosts_to_poll)
        results = self.runner.run()
        self.runner.inventory.lift_restriction()

        hosts = []
        poll_results = { 'contacted': {}, 'dark': {}, 'polled': {}}
        for (host, res) in results['contacted'].iteritems():
            if res.get('started',False):
                hosts.append(host)
                poll_results['polled'][host] = res
            else:
                self.results['contacted'][host] = res
                poll_results['contacted'][host] = res
                if res.get('failed', False) or res.get('rc', 0) != 0:
                    self.runner.callbacks.on_async_failed(host, res, self.runner.vars_cache[host]['ansible_job_id'])
                else:
                    self.runner.callbacks.on_async_ok(host, res, self.runner.vars_cache[host]['ansible_job_id'])
        for (host, res) in results['dark'].iteritems():
            self.results['dark'][host] = res
            poll_results['dark'][host] = res
            if host in self.hosts_to_poll:
                self.runner.callbacks.on_async_failed(host, res, self.runner.vars_cache[host].get('ansible_job_id','XX'))

        self.hosts_to_poll = hosts
        if len(hosts)==0:
            self.completed = True

        return poll_results

    def wait(self, seconds, poll_interval):
        """ Wait a certain time for job completion, check status every poll_interval. """
        # jid is None when all hosts were skipped
        if not self.active:
            return self.results

        clock = seconds - poll_interval
        while (clock >= 0 and not self.completed):
            time.sleep(poll_interval)

            poll_results = self.poll()

            for (host, res) in poll_results['polled'].iteritems():
                if res.get('started'):
                    self.runner.callbacks.on_async_poll(host, res, self.runner.vars_cache[host]['ansible_job_id'], clock)

            clock = clock - poll_interval

        return self.results

########NEW FILE########
__FILENAME__ = return_data
# (c) 2012-2014, Michael DeHaan <michael.dehaan@gmail.com>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

from ansible import utils

class ReturnData(object):
    ''' internal return class for runner execute methods, not part of public API signature '''

    __slots__ = [ 'result', 'comm_ok', 'host', 'diff' ]

    def __init__(self, conn=None, host=None, result=None, 
        comm_ok=True, diff=dict()):

        # which host is this ReturnData about?
        if conn is not None:
            self.host = conn.host
            delegate = getattr(conn, 'delegate', None)
            if delegate is not None:
                self.host = delegate

        else:
            self.host = host

        self.result = result
        self.comm_ok = comm_ok

        # if these values are set and used with --diff we can show
        # changes made to particular files
        self.diff = diff

        if type(self.result) in [ str, unicode ]:
            self.result = utils.parse_json(self.result)


        if self.host is None:
            raise Exception("host not set")
        if type(self.result) != dict:
            raise Exception("dictionary result expected")

    def communicated_ok(self):
        return self.comm_ok

    def is_successful(self):
        return self.comm_ok and (self.result.get('failed', False) == False) and ('failed_when_result' in self.result and [not self.result['failed_when_result']] or [self.result.get('rc',0) == 0])[0]


########NEW FILE########
__FILENAME__ = cmd_functions
# (c) 2012, Michael DeHaan <michael.dehaan@gmail.com>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

import os
import sys
import shlex
import subprocess
import select

def run_cmd(cmd, live=False, readsize=10):

    #readsize = 10

    cmdargs = shlex.split(cmd)
    p = subprocess.Popen(cmdargs, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    stdout = ''
    stderr = ''
    rpipes = [p.stdout, p.stderr]
    while True:
        rfd, wfd, efd = select.select(rpipes, [], rpipes, 1)

        if p.stdout in rfd:
            dat = os.read(p.stdout.fileno(), readsize)
            if live:
                sys.stdout.write(dat)
            stdout += dat
            if dat == '':
                rpipes.remove(p.stdout)
        if p.stderr in rfd:
            dat = os.read(p.stderr.fileno(), readsize)
            stderr += dat
            if live:
                sys.stdout.write(dat)
            if dat == '':
                rpipes.remove(p.stderr)
        # only break out if we've emptied the pipes, or there is nothing to
        # read from and the process has finished.
        if (not rpipes or not rfd) and p.poll() is not None:
            break
        # Calling wait while there are still pipes to read can cause a lock
        elif not rpipes and p.poll() == None:
            p.wait()

    return p.returncode, stdout, stderr

########NEW FILE########
__FILENAME__ = display_functions
# (c) 2014, Michael DeHaan <michael.dehaan@gmail.com>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

import textwrap

from ansible import constants as C
from ansible import errors
from ansible.callbacks import display

__all__ = ['deprecated', 'warning', 'system_warning']

# list of all deprecation messages to prevent duplicate display
deprecations = {}
warns = {}

def deprecated(msg, version, removed=False):
    ''' used to print out a deprecation message.'''

    if not removed and not C.DEPRECATION_WARNINGS:
        return

    if not removed:
        if version:
            new_msg = "\n[DEPRECATION WARNING]: %s. This feature will be removed in version %s." % (msg, version)
        else:
            new_msg = "\n[DEPRECATION WARNING]: %s. This feature will be removed in a future release." % (msg)
        new_msg = new_msg + " Deprecation warnings can be disabled by setting deprecation_warnings=False in ansible.cfg.\n\n"
    else:
        raise errors.AnsibleError("[DEPRECATED]: %s.  Please update your playbooks." % msg)

    wrapped = textwrap.wrap(new_msg, 79)
    new_msg = "\n".join(wrapped) + "\n"

    if new_msg not in deprecations:
        display(new_msg, color='purple', stderr=True)
        deprecations[new_msg] = 1

def warning(msg):
    new_msg = "\n[WARNING]: %s" % msg
    wrapped = textwrap.wrap(new_msg, 79)
    new_msg = "\n".join(wrapped) + "\n"
    if new_msg not in warns:
        display(new_msg, color='bright purple', stderr=True)
        warns[new_msg] = 1

def system_warning(msg):
    if C.SYSTEM_WARNINGS:
        warning(msg)


########NEW FILE########
__FILENAME__ = module_docs
#!/usr/bin/env python
# (c) 2012, Jan-Piet Mens <jpmens () gmail.com>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.
#

import os
import sys
import ast
import yaml
import traceback

from ansible import utils

# modules that are ok that they do not have documentation strings
BLACKLIST_MODULES = [
   'async_wrapper', 'accelerate', 'async_status'
]

def get_docstring(filename, verbose=False):
    """
    Search for assignment of the DOCUMENTATION and EXAMPLES variables
    in the given file.
    Parse DOCUMENTATION from YAML and return the YAML doc or None
    together with EXAMPLES, as plain text.

    DOCUMENTATION can be extended using documentation fragments
    loaded by the PluginLoader from the module_docs_fragments
    directory.
    """

    doc = None
    plainexamples = None

    try:
        # Thank you, Habbie, for this bit of code :-)
        M = ast.parse(''.join(open(filename)))
        for child in M.body:
            if isinstance(child, ast.Assign):
                if 'DOCUMENTATION' in (t.id for t in child.targets):
                    doc = yaml.safe_load(child.value.s)
                    fragment_slug = doc.get('extends_documentation_fragment',
                                            'doesnotexist').lower()

                    # Allow the module to specify a var other than DOCUMENTATION
                    # to pull the fragment from, using dot notation as a separator
                    if '.' in fragment_slug:
                        fragment_name, fragment_var = fragment_slug.split('.', 1)
                        fragment_var = fragment_var.upper()
                    else:
                        fragment_name, fragment_var = fragment_slug, 'DOCUMENTATION'


                    if fragment_slug != 'doesnotexist':
                        fragment_class = utils.plugins.fragment_loader.get(fragment_name)
                        assert fragment_class is not None

                        fragment_yaml = getattr(fragment_class, fragment_var, '{}')
                        fragment = yaml.safe_load(fragment_yaml)

                        if fragment.has_key('notes'):
                            notes = fragment.pop('notes')
                            if notes:
                                if not doc.has_key('notes'):
                                    doc['notes'] = []
                                doc['notes'].extend(notes)

                        if 'options' not in fragment.keys():
                            raise Exception("missing options in fragment, possibly misformatted?")

                        for key, value in fragment.items():
                            if not doc.has_key(key):
                                doc[key] = value
                            else:
                                doc[key].update(value)

                if 'EXAMPLES' in (t.id for t in child.targets):
                    plainexamples = child.value.s[1:]  # Skip first empty line
    except:
        traceback.print_exc() # temp
        if verbose == True:
            traceback.print_exc()
            print "unable to parse %s" % filename
    return doc, plainexamples


########NEW FILE########
__FILENAME__ = aws
# (c) 2014, Will Thames <will@thames.id.au>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.


class ModuleDocFragment(object):

    # AWS only documentation fragment
    DOCUMENTATION = """
options:
  ec2_url:
    description:
      - Url to use to connect to EC2 or your Eucalyptus cloud (by default the module will use EC2 endpoints).  Must be specified if region is not used. If not set then the value of the EC2_URL environment variable, if any, is used
    required: false
    default: null
    aliases: []
  aws_secret_key:
    description:
      - AWS secret key. If not set then the value of the AWS_SECRET_KEY environment variable is used. 
    required: false
    default: null
    aliases: [ 'ec2_secret_key', 'secret_key' ]
  aws_access_key:
    description:
      - AWS access key. If not set then the value of the AWS_ACCESS_KEY environment variable is used.
    required: false
    default: null
    aliases: [ 'ec2_access_key', 'access_key' ]
  validate_certs:
    description:
      - When set to "no", SSL certificates will not be validated for boto versions >= 2.6.0.
    required: false
    default: "yes"
    choices: ["yes", "no"]
    aliases: []
    version_added: "1.5"
  profile:
    description:
      - uses a boto profile. Only works with boto >= 2.24.0
    required: false
    default: null
    aliases: []
    version_added: "1.6"
  security_token:
    description:
      - security token to authenticate against AWS
    required: false
    default: null
    aliases: []
    version_added: "1.6"
requirements:
  - boto
notes:
  - The following environment variables can be used C(AWS_ACCESS_KEY) or 
    C(EC2_ACCESS_KEY) or C(AWS_ACCESS_KEY_ID),
    C(AWS_SECRET_KEY) or C(EC2_SECRET_KEY) or C(AWS_SECRET_ACCESS_KEY), 
    C(AWS_REGION) or C(EC2_REGION), C(AWS_SECURITY_TOKEN)
  - Ansible uses the boto configuration file (typically ~/.boto) if no
    credentials are provided. See http://boto.readthedocs.org/en/latest/boto_config_tut.html 
  - C(AWS_REGION) or C(EC2_REGION) can be typically be used to specify the 
    AWS region, when required, but
    this can also be configured in the boto config file
"""

########NEW FILE########
__FILENAME__ = files
# (c) 2014, Matt Martz <matt@sivel.net>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.


class ModuleDocFragment(object):

    # Standard files documentation fragment
    DOCUMENTATION = """
options:
options:
  path:
    description:
      - 'path to the file being managed.  Aliases: I(dest), I(name)'
    required: true
    default: []
    aliases: ['dest', 'name'] 
  state:
    description:
      - If C(directory), all immediate subdirectories will be created if they
        do not exist, since 1.7 they will be created with the supplied permissions.
        If C(file), the file will NOT be created if it does not exist, see the M(copy)
        or M(template) module if you want that behavior.  If C(link), the symbolic
        link will be created or changed. Use C(hard) for hardlinks. If C(absent),
        directories will be recursively deleted, and files or symlinks will be unlinked.
        If C(touch) (new in 1.4), an empty file will be created if the c(path) does not
        exist, while an existing file or directory will receive updated file access and
        modification times (similar to the way `touch` works from the command line).
    required: false
    default: file
    choices: [ file, link, directory, hard, touch, absent ]
  mode:
    required: false
    default: null
    choices: []
    description:
      - mode the file or directory should be, such as 0644 as would be fed to I(chmod)
  owner:
    required: false
    default: null
    choices: []
    description:
      - name of the user that should own the file/directory, as would be fed to I(chown)
  group:
    required: false
    default: null
    choices: []
    description:
      - name of the group that should own the file/directory, as would be fed to I(chown)
  src:
    required: false
    default: null
    choices: []
    description:
      - path of the file to link to (applies only to C(state=link)). Will accept absolute,
        relative and nonexisting paths. Relative paths are not expanded.
  seuser:
    required: false
    default: null
    choices: []
    description:
      - user part of SELinux file context. Will default to system policy, if
        applicable. If set to C(_default), it will use the C(user) portion of the
        policy if available
  serole:
    required: false
    default: null
    choices: []
    description:
      - role part of SELinux file context, C(_default) feature works as for I(seuser).
  setype:
    required: false
    default: null
    choices: []
    description:
      - type part of SELinux file context, C(_default) feature works as for I(seuser).
  selevel:
    required: false
    default: "s0"
    choices: []
    description:
      - level part of the SELinux file context. This is the MLS/MCS attribute,
        sometimes known as the C(range). C(_default) feature works as for
        I(seuser).
  recurse:
    required: false
    default: "no"
    choices: [ "yes", "no" ]
    version_added: "1.1"
    description:
      - recursively set the specified file attributes (applies only to state=directory)
  force:
    required: false
    default: "no"
    choices: [ "yes", "no" ]
    description:
      - 'force the creation of the symlinks in two cases: the source file does 
        not exist (but will appear later); the destination exists and is a file (so, we need to unlink the
        "path" file and create symlink to the "src" file in place of it).'
"""

########NEW FILE########
__FILENAME__ = rackspace
# (c) 2014, Matt Martz <matt@sivel.net>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.


class ModuleDocFragment(object):

    # Standard Rackspace only documentation fragment
    DOCUMENTATION = """
options:
  api_key:
    description:
      - Rackspace API key (overrides I(credentials))
    aliases:
      - password
  credentials:
    description:
      - File to find the Rackspace credentials in (ignored if I(api_key) and
        I(username) are provided)
    default: null
    aliases:
      - creds_file
  env:
    description:
      - Environment as configured in ~/.pyrax.cfg,
        see U(https://github.com/rackspace/pyrax/blob/master/docs/getting_started.md#pyrax-configuration)
    version_added: 1.5
  region:
    description:
      - Region to create an instance in
    default: DFW
  username:
    description:
      - Rackspace username (overrides I(credentials))
  verify_ssl:
    description:
      - Whether or not to require SSL validation of API endpoints
    version_added: 1.5
requirements:
  - pyrax
notes:
  - The following environment variables can be used, C(RAX_USERNAME),
    C(RAX_API_KEY), C(RAX_CREDS_FILE), C(RAX_CREDENTIALS), C(RAX_REGION).
  - C(RAX_CREDENTIALS) and C(RAX_CREDS_FILE) points to a credentials file
    appropriate for pyrax. See U(https://github.com/rackspace/pyrax/blob/master/docs/getting_started.md#authenticating)
  - C(RAX_USERNAME) and C(RAX_API_KEY) obviate the use of a credentials file
  - C(RAX_REGION) defines a Rackspace Public Cloud region (DFW, ORD, LON, ...)
"""

    # Documentation fragment including attributes to enable communication
    # of other OpenStack clouds. Not all rax modules support this.
    OPENSTACK = """
options:
  api_key:
    description:
      - Rackspace API key (overrides I(credentials))
    aliases:
      - password
  auth_endpoint:
    description:
      - The URI of the authentication service
    default: https://identity.api.rackspacecloud.com/v2.0/
    version_added: 1.5
  credentials:
    description:
      - File to find the Rackspace credentials in (ignored if I(api_key) and
        I(username) are provided)
    default: null
    aliases:
      - creds_file
  env:
    description:
      - Environment as configured in ~/.pyrax.cfg,
        see U(https://github.com/rackspace/pyrax/blob/master/docs/getting_started.md#pyrax-configuration)
    version_added: 1.5
  identity_type:
    description:
      - Authentication machanism to use, such as rackspace or keystone
    default: rackspace
    version_added: 1.5
  region:
    description:
      - Region to create an instance in
    default: DFW
  tenant_id:
    description:
      - The tenant ID used for authentication
    version_added: 1.5
  tenant_name:
    description:
      - The tenant name used for authentication
    version_added: 1.5
  username:
    description:
      - Rackspace username (overrides I(credentials))
  verify_ssl:
    description:
      - Whether or not to require SSL validation of API endpoints
    version_added: 1.5
requirements:
  - pyrax
notes:
  - The following environment variables can be used, C(RAX_USERNAME),
    C(RAX_API_KEY), C(RAX_CREDS_FILE), C(RAX_CREDENTIALS), C(RAX_REGION).
  - C(RAX_CREDENTIALS) and C(RAX_CREDS_FILE) points to a credentials file
    appropriate for pyrax. See U(https://github.com/rackspace/pyrax/blob/master/docs/getting_started.md#authenticating)
  - C(RAX_USERNAME) and C(RAX_API_KEY) obviate the use of a credentials file
  - C(RAX_REGION) defines a Rackspace Public Cloud region (DFW, ORD, LON, ...)
"""

########NEW FILE########
__FILENAME__ = plugins
# (c) 2012, Daniel Hokka Zakrisson <daniel@hozac.com>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

import os
import os.path
import sys
import glob
import imp
from ansible import constants as C
from ansible import errors

MODULE_CACHE = {}
PATH_CACHE = {}
PLUGIN_PATH_CACHE = {}
_basedirs = []

def push_basedir(basedir):
    # avoid pushing the same absolute dir more than once
    basedir = os.path.realpath(basedir)
    if basedir not in _basedirs:
        _basedirs.insert(0, basedir)

class PluginLoader(object):

    '''
    PluginLoader loads plugins from the configured plugin directories.

    It searches for plugins by iterating through the combined list of
    play basedirs, configured paths, and the python path.
    The first match is used.
    '''

    def __init__(self, class_name, package, config, subdir, aliases={}):

        self.class_name         = class_name
        self.package            = package
        self.config             = config
        self.subdir             = subdir
        self.aliases            = aliases

        if not class_name in MODULE_CACHE:
            MODULE_CACHE[class_name] = {}
        if not class_name in PATH_CACHE:
            PATH_CACHE[class_name] = None
        if not class_name in PLUGIN_PATH_CACHE:
            PLUGIN_PATH_CACHE[class_name] = {}

        self._module_cache      = MODULE_CACHE[class_name]
        self._paths             = PATH_CACHE[class_name]
        self._plugin_path_cache = PLUGIN_PATH_CACHE[class_name]

        self._extra_dirs = []

    def print_paths(self):
        ''' Returns a string suitable for printing of the search path '''

        # Uses a list to get the order right
        ret = []
        for i in self._get_paths():
            if i not in ret:
                ret.append(i)
        return os.pathsep.join(ret)

    def _get_package_paths(self):
        ''' Gets the path of a Python package '''

        paths = []
        if not self.package:
            return []
        if not hasattr(self, 'package_path'):
            m = __import__(self.package)
            parts = self.package.split('.')[1:]
            self.package_path = os.path.join(os.path.dirname(m.__file__), *parts)
            paths.append(self.package_path)
            return paths
        else:
            return [ self.package_path ]

    def _get_paths(self):
        ''' Return a list of paths to search for plugins in '''

        if self._paths is not None:
            return self._paths

        ret = []
        ret += self._extra_dirs
        for basedir in _basedirs:
            fullpath = os.path.realpath(os.path.join(basedir, self.subdir))
            if os.path.isdir(fullpath):
                files = glob.glob("%s/*" % fullpath)
                for file in files:
                    if os.path.isdir(file) and file not in ret:
                        ret.append(file)
                if fullpath not in ret:
                    ret.append(fullpath)

        # look in any configured plugin paths, allow one level deep for subcategories 
        configured_paths = self.config.split(os.pathsep)
        for path in configured_paths:
            path = os.path.realpath(os.path.expanduser(path))
            contents = glob.glob("%s/*" % path)
            for c in contents:
                if os.path.isdir(c) and c not in ret:
                    ret.append(c)       
            if path not in ret:
                ret.append(path)

        # look for any plugins installed in the package subtree
        ret.extend(self._get_package_paths())

        self._paths = ret

        return ret


    def add_directory(self, directory, with_subdir=False):
        ''' Adds an additional directory to the search path '''

        self._paths = None
        directory = os.path.realpath(directory)

        if directory is not None:
            if with_subdir:
                directory = os.path.join(directory, self.subdir)
            if directory not in self._extra_dirs:
                self._extra_dirs.append(directory)

    def find_plugin(self, name):
        ''' Find a plugin named name '''

        if name in self._plugin_path_cache:
            return self._plugin_path_cache[name]

        suffix = ".py"
        if not self.class_name:
            suffix = ""

        for i in self._get_paths():
            path = os.path.join(i, "%s%s" % (name, suffix))
            if os.path.isfile(path):
                self._plugin_path_cache[name] = path
                return path

        return None

    def has_plugin(self, name):
        ''' Checks if a plugin named name exists '''

        return self.find_plugin(name) is not None

    __contains__ = has_plugin

    def get(self, name, *args, **kwargs):
        ''' instantiates a plugin of the given name using arguments '''

        if name in self.aliases:
            name = self.aliases[name]
        path = self.find_plugin(name)
        if path is None:
            return None
        if path not in self._module_cache:
            self._module_cache[path] = imp.load_source('.'.join([self.package, name]), path)
        return getattr(self._module_cache[path], self.class_name)(*args, **kwargs)

    def all(self, *args, **kwargs):
        ''' instantiates all plugins with the same arguments '''       

        for i in self._get_paths():
            matches = glob.glob(os.path.join(i, "*.py"))
            matches.sort()
            for path in matches:
                name, ext = os.path.splitext(os.path.basename(path))
                if name.startswith("_"):
                    continue
                if path not in self._module_cache:
                    self._module_cache[path] = imp.load_source('.'.join([self.package, name]), path)
                yield getattr(self._module_cache[path], self.class_name)(*args, **kwargs)

action_loader = PluginLoader(
    'ActionModule',   
    'ansible.runner.action_plugins',
    C.DEFAULT_ACTION_PLUGIN_PATH,
    'action_plugins'
)

callback_loader = PluginLoader(
    'CallbackModule', 
    'ansible.callback_plugins', 
    C.DEFAULT_CALLBACK_PLUGIN_PATH, 
    'callback_plugins'
)

connection_loader = PluginLoader(
    'Connection', 
    'ansible.runner.connection_plugins', 
    C.DEFAULT_CONNECTION_PLUGIN_PATH, 
    'connection_plugins', 
    aliases={'paramiko': 'paramiko_ssh'}
)

module_finder = PluginLoader(
    '', 
    '', 
    C.DEFAULT_MODULE_PATH, 
    'library'
)

lookup_loader = PluginLoader(
    'LookupModule',   
    'ansible.runner.lookup_plugins', 
    C.DEFAULT_LOOKUP_PLUGIN_PATH, 
    'lookup_plugins'
)

vars_loader = PluginLoader(
    'VarsModule', 
    'ansible.inventory.vars_plugins', 
    C.DEFAULT_VARS_PLUGIN_PATH, 
    'vars_plugins'
)

filter_loader = PluginLoader(
    'FilterModule', 
    'ansible.runner.filter_plugins', 
    C.DEFAULT_FILTER_PLUGIN_PATH, 
    'filter_plugins'
)

fragment_loader = PluginLoader(
    'ModuleDocFragment',
    'ansible.utils.module_docs_fragments',
    os.path.join(os.path.dirname(__file__), 'module_docs_fragments'),
    '',
)

########NEW FILE########
__FILENAME__ = string_functions
def isprintable(instring):
    if isinstance(instring, str):
        #http://stackoverflow.com/a/3637294
        import string
        printset = set(string.printable)
        isprintable = set(instring).issubset(printset)
        return isprintable
    else:
        return True

def count_newlines_from_end(str):
    i = len(str)
    while i > 0:
        if str[i-1] != '\n':
            break
        i -= 1
    return len(str) - i


########NEW FILE########
__FILENAME__ = template
# (c) 2012, Michael DeHaan <michael.dehaan@gmail.com>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

import os
import re
import codecs
import jinja2
from jinja2.runtime import StrictUndefined
from jinja2.exceptions import TemplateSyntaxError
import yaml
import json
from ansible import errors
import ansible.constants as C
import time
import subprocess
import datetime
import pwd
import ast
import traceback

from ansible.utils.string_functions import count_newlines_from_end

class Globals(object):

    FILTERS = None

    def __init__(self):
        pass

def _get_filters():
    ''' return filter plugin instances '''

    if Globals.FILTERS is not None:
        return Globals.FILTERS

    from ansible import utils
    plugins = [ x for x in utils.plugins.filter_loader.all()]
    filters = {}
    for fp in plugins:
        filters.update(fp.filters())
    Globals.FILTERS = filters

    return Globals.FILTERS

def _get_extensions():
    ''' return jinja2 extensions to load '''

    '''
    if some extensions are set via jinja_extensions in ansible.cfg, we try
    to load them with the jinja environment
    '''
    jinja_exts = []
    if C.DEFAULT_JINJA2_EXTENSIONS:
        '''
        Let's make sure the configuration directive doesn't contain spaces
        and split extensions in an array
        '''
        jinja_exts = C.DEFAULT_JINJA2_EXTENSIONS.replace(" ", "").split(',')

    return jinja_exts

class Flags:
    LEGACY_TEMPLATE_WARNING = False

# TODO: refactor this file

FILTER_PLUGINS = None
_LISTRE = re.compile(r"(\w+)\[(\d+)\]")
JINJA2_OVERRIDE='#jinja2:'

def lookup(name, *args, **kwargs):
    from ansible import utils
    instance = utils.plugins.lookup_loader.get(name.lower(), basedir=kwargs.get('basedir',None))
    vars = kwargs.get('vars', None)

    if instance is not None:
        # safely catch run failures per #5059
        try:
            ran = instance.run(*args, inject=vars, **kwargs)
        except Exception, e:
            ran = None
        if ran:
            ran = ",".join(ran)
        return ran
    else:
        raise errors.AnsibleError("lookup plugin (%s) not found" % name)

def template(basedir, varname, vars, lookup_fatal=True, depth=0, expand_lists=True, convert_bare=False, fail_on_undefined=False, filter_fatal=True):
    ''' templates a data structure by traversing it and substituting for other data structures '''
    from ansible import utils

    try:
        if convert_bare and isinstance(varname, basestring):
            first_part = varname.split(".")[0].split("[")[0]
            if first_part in vars and '{{' not in varname and '$' not in varname:
                varname = "{{%s}}" % varname
    
        if isinstance(varname, basestring):
            if '{{' in varname or '{%' in varname:
                varname = template_from_string(basedir, varname, vars, fail_on_undefined)

                if (varname.startswith("{") and not varname.startswith("{{")) or varname.startswith("["):
                    eval_results = utils.safe_eval(varname, locals=vars, include_exceptions=True)
                    if eval_results[1] is None:
                        varname = eval_results[0]

            return varname
    
        elif isinstance(varname, (list, tuple)):
            return [template(basedir, v, vars, lookup_fatal, depth, expand_lists, fail_on_undefined=fail_on_undefined) for v in varname]
        elif isinstance(varname, dict):
            d = {}
            for (k, v) in varname.iteritems():
                d[k] = template(basedir, v, vars, lookup_fatal, depth, expand_lists, fail_on_undefined=fail_on_undefined)
            return d
        else:
            return varname
    except errors.AnsibleFilterError:
        if filter_fatal:
            raise
        else:
            return varname


class _jinja2_vars(object):
    '''
    Helper class to template all variable content before jinja2 sees it.
    This is done by hijacking the variable storage that jinja2 uses, and
    overriding __contains__ and __getitem__ to look like a dict. Added bonus
    is avoiding duplicating the large hashes that inject tends to be.
    To facilitate using builtin jinja2 things like range, globals are handled
    here.
    extras is a list of locals to also search for variables.
    '''

    def __init__(self, basedir, vars, globals, fail_on_undefined, *extras):
        self.basedir = basedir
        self.vars = vars
        self.globals = globals
        self.fail_on_undefined = fail_on_undefined
        self.extras = extras

    def __contains__(self, k):
        if k in self.vars:
            return True
        for i in self.extras:
            if k in i:
                return True
        if k in self.globals:
            return True
        return False

    def __getitem__(self, varname):
        if varname not in self.vars:
            for i in self.extras:
                if varname in i:
                    return i[varname]
            if varname in self.globals:
                return self.globals[varname]
            else:
                raise KeyError("undefined variable: %s" % varname)
        var = self.vars[varname]
        # HostVars is special, return it as-is
        if isinstance(var, dict) and type(var) != dict:
            return var
        else:
            return template(self.basedir, var, self.vars, fail_on_undefined=self.fail_on_undefined)

    def add_locals(self, locals):
        '''
        If locals are provided, create a copy of self containing those
        locals in addition to what is already in this variable proxy.
        '''
        if locals is None:
            return self
        return _jinja2_vars(self.basedir, self.vars, self.globals, self.fail_on_undefined, locals, *self.extras)

class J2Template(jinja2.environment.Template):
    '''
    This class prevents Jinja2 from running _jinja2_vars through dict()
    Without this, {% include %} and similar will create new contexts unlike
    the special one created in template_from_file. This ensures they are all
    alike, with the exception of potential locals.
    '''
    def new_context(self, vars=None, shared=False, locals=None):
        return jinja2.runtime.Context(self.environment, vars.add_locals(locals), self.name, self.blocks)

def template_from_file(basedir, path, vars, vault_password=None):
    ''' run a file through the templating engine '''

    fail_on_undefined = C.DEFAULT_UNDEFINED_VAR_BEHAVIOR

    from ansible import utils
    realpath = utils.path_dwim(basedir, path)
    loader=jinja2.FileSystemLoader([basedir,os.path.dirname(realpath)])

    def my_lookup(*args, **kwargs):
        kwargs['vars'] = vars
        return lookup(*args, basedir=basedir, **kwargs)
    def my_finalize(thing):
        return thing if thing is not None else ''

    environment = jinja2.Environment(loader=loader, trim_blocks=True, extensions=_get_extensions())
    environment.filters.update(_get_filters())
    environment.globals['lookup'] = my_lookup
    environment.globals['finalize'] = my_finalize
    if fail_on_undefined:
        environment.undefined = StrictUndefined

    try:
        data = codecs.open(realpath, encoding="utf8").read()
    except UnicodeDecodeError:
        raise errors.AnsibleError("unable to process as utf-8: %s" % realpath)
    except:
        raise errors.AnsibleError("unable to read %s" % realpath)


    # Get jinja env overrides from template
    if data.startswith(JINJA2_OVERRIDE):
        eol = data.find('\n')
        line = data[len(JINJA2_OVERRIDE):eol]
        data = data[eol+1:]
        for pair in line.split(','):
            (key,val) = pair.split(':')
            setattr(environment,key.strip(),ast.literal_eval(val.strip()))

    environment.template_class = J2Template
    try:
        t = environment.from_string(data)
    except TemplateSyntaxError, e:
        # Throw an exception which includes a more user friendly error message
        values = {'name': realpath, 'lineno': e.lineno, 'error': str(e)}
        msg = 'file: %(name)s, line number: %(lineno)s, error: %(error)s' % \
               values
        error = errors.AnsibleError(msg)
        raise error
    vars = vars.copy()
    try:
        template_uid = pwd.getpwuid(os.stat(realpath).st_uid).pw_name
    except:
        template_uid = os.stat(realpath).st_uid
    vars['template_host']   = os.uname()[1]
    vars['template_path']   = realpath
    vars['template_mtime']  = datetime.datetime.fromtimestamp(os.path.getmtime(realpath))
    vars['template_uid']    = template_uid
    vars['template_fullpath'] = os.path.abspath(realpath)
    vars['template_run_date'] = datetime.datetime.now()

    managed_default = C.DEFAULT_MANAGED_STR
    managed_str = managed_default.format(
        host = vars['template_host'],
        uid  = vars['template_uid'],
        file = vars['template_path']
    )
    vars['ansible_managed'] = time.strftime(
        managed_str,
        time.localtime(os.path.getmtime(realpath))
    )

    # This line performs deep Jinja2 magic that uses the _jinja2_vars object for vars
    # Ideally, this could use some API where setting shared=True and the object won't get
    # passed through dict(o), but I have not found that yet.
    try:
        res = jinja2.utils.concat(t.root_render_func(t.new_context(_jinja2_vars(basedir, vars, t.globals, fail_on_undefined), shared=True)))
    except jinja2.exceptions.UndefinedError, e:
        raise errors.AnsibleUndefinedVariable("One or more undefined variables: %s" % str(e))

    # The low level calls above do not preserve the newline
    # characters at the end of the input data, so we use the
    # calculate the difference in newlines and append them 
    # to the resulting output for parity
    res_newlines  = count_newlines_from_end(res)
    data_newlines = count_newlines_from_end(data)
    if data_newlines > res_newlines:
        res += '\n' * (data_newlines - res_newlines)

    if isinstance(res, unicode):
        # do not try to re-template a unicode string
        result = res
    else:
        result = template(basedir, res, vars)

    return result

def template_from_string(basedir, data, vars, fail_on_undefined=False):
    ''' run a string through the (Jinja2) templating engine '''

    try:
        if type(data) == str:
            data = unicode(data, 'utf-8')

        def my_finalize(thing):
            return thing if thing is not None else ''

        environment = jinja2.Environment(trim_blocks=True, undefined=StrictUndefined, extensions=_get_extensions(), finalize=my_finalize)
        environment.filters.update(_get_filters())
        environment.template_class = J2Template

        if '_original_file' in vars:
            basedir = os.path.dirname(vars['_original_file'])
            filesdir = os.path.abspath(os.path.join(basedir, '..', 'files'))
            if os.path.exists(filesdir):
                basedir = filesdir

        # 6227
        if isinstance(data, unicode):
            try:
                data = data.decode('utf-8')
            except UnicodeEncodeError, e:
                pass

        try:
            t = environment.from_string(data)
        except Exception, e:
            if 'recursion' in str(e):
                raise errors.AnsibleError("recursive loop detected in template string: %s" % data)
            else:
                return data

        def my_lookup(*args, **kwargs):
            kwargs['vars'] = vars
            return lookup(*args, basedir=basedir, **kwargs)

        t.globals['lookup'] = my_lookup
        t.globals['finalize'] = my_finalize
        jvars =_jinja2_vars(basedir, vars, t.globals, fail_on_undefined)
        new_context = t.new_context(jvars, shared=True)
        rf = t.root_render_func(new_context)
        try:
            res = jinja2.utils.concat(rf)
        except TypeError, te:
            if 'StrictUndefined' in str(te):
                raise errors.AnsibleUndefinedVariable(
                    "Unable to look up a name or access an attribute in template string. " + \
                    "Make sure your variable name does not contain invalid characters like '-'."
                )
            else:
                raise errors.AnsibleError("an unexpected type error occured. Error was %s" % te)
        return res
    except (jinja2.exceptions.UndefinedError, errors.AnsibleUndefinedVariable):
        if fail_on_undefined:
            raise
        else:
            return data


########NEW FILE########
__FILENAME__ = vault
# (c) 2014, James Tanner <tanner.jc@gmail.com>
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.
#
# ansible-pull is a script that runs ansible in local mode
# after checking out a playbooks directory from source repo.  There is an
# example playbook to bootstrap this script in the examples/ dir which
# installs ansible and sets it up to run on cron.

import os
import shlex
import shutil
import tempfile
from io import BytesIO
from subprocess import call
from ansible import errors
from hashlib import sha256
from hashlib import md5
from binascii import hexlify
from binascii import unhexlify
from ansible import constants as C

try:
    from Crypto.Hash import SHA256, HMAC
    HAS_HASH = True
except ImportError:
    HAS_HASH = False

# Counter import fails for 2.0.1, requires >= 2.6.1 from pip
try:
    from Crypto.Util import Counter
    HAS_COUNTER = True
except ImportError:
    HAS_COUNTER = False

# KDF import fails for 2.0.1, requires >= 2.6.1 from pip
try:
    from Crypto.Protocol.KDF import PBKDF2
    HAS_PBKDF2 = True
except ImportError:
    HAS_PBKDF2 = False

# AES IMPORTS
try:
    from Crypto.Cipher import AES as AES
    HAS_AES = True   
except ImportError:
    HAS_AES = False    

CRYPTO_UPGRADE = "ansible-vault requires a newer version of pycrypto than the one installed on your platform. You may fix this with OS-specific commands such as: yum install python-devel; rpm -e --nodeps python-crypto; pip install pycrypto"

HEADER='$ANSIBLE_VAULT'
CIPHER_WHITELIST=['AES', 'AES256']

class VaultLib(object):

    def __init__(self, password):
        self.password = password
        self.cipher_name = None
        self.version = '1.1'

    def is_encrypted(self, data): 
        if data.startswith(HEADER):
            return True
        else:
            return False

    def encrypt(self, data):

        if self.is_encrypted(data):
            raise errors.AnsibleError("data is already encrypted")

        if not self.cipher_name:
            self.cipher_name = "AES256"
            #raise errors.AnsibleError("the cipher must be set before encrypting data")

        if 'Vault' + self.cipher_name in globals() and self.cipher_name in CIPHER_WHITELIST: 
            cipher = globals()['Vault' + self.cipher_name]
            this_cipher = cipher()
        else:
            raise errors.AnsibleError("%s cipher could not be found" % self.cipher_name)

        """
        # combine sha + data
        this_sha = sha256(data).hexdigest()
        tmp_data = this_sha + "\n" + data
        """

        # encrypt sha + data
        enc_data = this_cipher.encrypt(data, self.password)

        # add header 
        tmp_data = self._add_header(enc_data)
        return tmp_data

    def decrypt(self, data):
        if self.password is None:
            raise errors.AnsibleError("A vault password must be specified to decrypt data")

        if not self.is_encrypted(data):
            raise errors.AnsibleError("data is not encrypted")

        # clean out header
        data = self._split_header(data)

        # create the cipher object
        if 'Vault' + self.cipher_name in globals() and self.cipher_name in CIPHER_WHITELIST: 
            cipher = globals()['Vault' + self.cipher_name]
            this_cipher = cipher()
        else:
            raise errors.AnsibleError("%s cipher could not be found" % self.cipher_name)

        # try to unencrypt data
        data = this_cipher.decrypt(data, self.password)
        if data is None:
            raise errors.AnsibleError("Decryption failed")

        return data            

    def _add_header(self, data):     
        # combine header and encrypted data in 80 char columns

        #tmpdata = hexlify(data)
        tmpdata = [data[i:i+80] for i in range(0, len(data), 80)]

        if not self.cipher_name:
            raise errors.AnsibleError("the cipher must be set before adding a header")

        dirty_data = HEADER + ";" + str(self.version) + ";" + self.cipher_name + "\n"

        for l in tmpdata:
            dirty_data += l + '\n'

        return dirty_data


    def _split_header(self, data):        
        # used by decrypt

        tmpdata = data.split('\n')
        tmpheader = tmpdata[0].strip().split(';')

        self.version = str(tmpheader[1].strip())
        self.cipher_name = str(tmpheader[2].strip())
        clean_data = '\n'.join(tmpdata[1:])

        """
        # strip out newline, join, unhex        
        clean_data = [ x.strip() for x in clean_data ]
        clean_data = unhexlify(''.join(clean_data))
        """

        return clean_data

    def __enter__(self):
        return self

    def __exit__(self, *err):
        pass

class VaultEditor(object):
    # uses helper methods for write_file(self, filename, data) 
    # to write a file so that code isn't duplicated for simple 
    # file I/O, ditto read_file(self, filename) and launch_editor(self, filename) 
    # ... "Don't Repeat Yourself", etc.

    def __init__(self, cipher_name, password, filename):
        # instantiates a member variable for VaultLib
        self.cipher_name = cipher_name
        self.password = password
        self.filename = filename

    def create_file(self):
        """ create a new encrypted file """

        if not HAS_AES or not HAS_COUNTER or not HAS_PBKDF2 or not HAS_HASH:
            raise errors.AnsibleError(CRYPTO_UPGRADE)

        if os.path.isfile(self.filename):
            raise errors.AnsibleError("%s exists, please use 'edit' instead" % self.filename)

        # drop the user into vim on file
        old_umask = os.umask(0077)
        call(self._editor_shell_command(self.filename))
        tmpdata = self.read_data(self.filename)
        this_vault = VaultLib(self.password)
        this_vault.cipher_name = self.cipher_name
        enc_data = this_vault.encrypt(tmpdata)
        self.write_data(enc_data, self.filename)
        os.umask(old_umask)

    def decrypt_file(self):

        if not HAS_AES or not HAS_COUNTER or not HAS_PBKDF2 or not HAS_HASH:
            raise errors.AnsibleError(CRYPTO_UPGRADE)

        if not os.path.isfile(self.filename):
            raise errors.AnsibleError("%s does not exist" % self.filename)
        
        tmpdata = self.read_data(self.filename)
        this_vault = VaultLib(self.password)
        if this_vault.is_encrypted(tmpdata):
            dec_data = this_vault.decrypt(tmpdata)
            if dec_data is None:
                raise errors.AnsibleError("Decryption failed")
            else:
                self.write_data(dec_data, self.filename)
        else:
            raise errors.AnsibleError("%s is not encrypted" % self.filename)

    def edit_file(self):

        if not HAS_AES or not HAS_COUNTER or not HAS_PBKDF2 or not HAS_HASH:
            raise errors.AnsibleError(CRYPTO_UPGRADE)

        # make sure the umask is set to a sane value
        old_mask = os.umask(0077)

        # decrypt to tmpfile
        tmpdata = self.read_data(self.filename)
        this_vault = VaultLib(self.password)
        dec_data = this_vault.decrypt(tmpdata)
        _, tmp_path = tempfile.mkstemp()
        self.write_data(dec_data, tmp_path)

        # drop the user into vim on the tmp file
        call(self._editor_shell_command(tmp_path))
        new_data = self.read_data(tmp_path)

        # create new vault
        new_vault = VaultLib(self.password)

        # we want the cipher to default to AES256
        #new_vault.cipher_name = this_vault.cipher_name

        # encrypt new data a write out to tmp
        enc_data = new_vault.encrypt(new_data)
        self.write_data(enc_data, tmp_path)

        # shuffle tmp file into place
        self.shuffle_files(tmp_path, self.filename)

        # and restore the old umask
        os.umask(old_mask)

    def encrypt_file(self):

        if not HAS_AES or not HAS_COUNTER or not HAS_PBKDF2 or not HAS_HASH:
            raise errors.AnsibleError(CRYPTO_UPGRADE)

        if not os.path.isfile(self.filename):
            raise errors.AnsibleError("%s does not exist" % self.filename)
        
        tmpdata = self.read_data(self.filename)
        this_vault = VaultLib(self.password)
        this_vault.cipher_name = self.cipher_name
        if not this_vault.is_encrypted(tmpdata):
            enc_data = this_vault.encrypt(tmpdata)
            self.write_data(enc_data, self.filename)
        else:
            raise errors.AnsibleError("%s is already encrypted" % self.filename)

    def rekey_file(self, new_password):

        if not HAS_AES or not HAS_COUNTER or not HAS_PBKDF2 or not HAS_HASH:
            raise errors.AnsibleError(CRYPTO_UPGRADE)

        # decrypt 
        tmpdata = self.read_data(self.filename)
        this_vault = VaultLib(self.password)
        dec_data = this_vault.decrypt(tmpdata)

        # create new vault
        new_vault = VaultLib(new_password)

        # we want to force cipher to the default
        #new_vault.cipher_name = this_vault.cipher_name

        # re-encrypt data and re-write file
        enc_data = new_vault.encrypt(dec_data)
        self.write_data(enc_data, self.filename)

    def read_data(self, filename):
        f = open(filename, "rb")
        tmpdata = f.read()
        f.close()
        return tmpdata

    def write_data(self, data, filename):
        if os.path.isfile(filename): 
            os.remove(filename)
        f = open(filename, "wb")
        f.write(data)
        f.close()

    def shuffle_files(self, src, dest):
        # overwrite dest with src
        if os.path.isfile(dest):
            os.remove(dest)
        shutil.move(src, dest)

    def _editor_shell_command(self, filename):
        EDITOR = os.environ.get('EDITOR','vim')
        editor = shlex.split(EDITOR)
        editor.append(filename)

        return editor

########################################
#               CIPHERS                #
########################################

class VaultAES(object):

    # this version has been obsoleted by the VaultAES256 class
    # which uses encrypt-then-mac (fixing order) and also improving the KDF used
    # code remains for upgrade purposes only
    # http://stackoverflow.com/a/16761459

    def __init__(self):
        if not HAS_AES:
            raise errors.AnsibleError(CRYPTO_UPGRADE)

    def aes_derive_key_and_iv(self, password, salt, key_length, iv_length):

        """ Create a key and an initialization vector """

        d = d_i = ''
        while len(d) < key_length + iv_length:
            d_i = md5(d_i + password + salt).digest()
            d += d_i

        key = d[:key_length]
        iv = d[key_length:key_length+iv_length]

        return key, iv

    def encrypt(self, data, password, key_length=32):

        """ Read plaintext data from in_file and write encrypted to out_file """


        # combine sha + data
        this_sha = sha256(data).hexdigest()
        tmp_data = this_sha + "\n" + data

        in_file = BytesIO(tmp_data)
        in_file.seek(0)
        out_file = BytesIO()

        bs = AES.block_size

        # Get a block of random data. EL does not have Crypto.Random.new() 
        # so os.urandom is used for cross platform purposes
        salt = os.urandom(bs - len('Salted__'))

        key, iv = self.aes_derive_key_and_iv(password, salt, key_length, bs)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        out_file.write('Salted__' + salt)
        finished = False
        while not finished:
            chunk = in_file.read(1024 * bs)
            if len(chunk) == 0 or len(chunk) % bs != 0:
                padding_length = (bs - len(chunk) % bs) or bs
                chunk += padding_length * chr(padding_length)
                finished = True
            out_file.write(cipher.encrypt(chunk))

        out_file.seek(0)
        enc_data = out_file.read()
        tmp_data = hexlify(enc_data)

        return tmp_data

 
    def decrypt(self, data, password, key_length=32):

        """ Read encrypted data from in_file and write decrypted to out_file """

        # http://stackoverflow.com/a/14989032

        data = ''.join(data.split('\n'))
        data = unhexlify(data)

        in_file = BytesIO(data)
        in_file.seek(0)
        out_file = BytesIO()

        bs = AES.block_size
        salt = in_file.read(bs)[len('Salted__'):]
        key, iv = self.aes_derive_key_and_iv(password, salt, key_length, bs)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        next_chunk = ''
        finished = False

        while not finished:
            chunk, next_chunk = next_chunk, cipher.decrypt(in_file.read(1024 * bs))
            if len(next_chunk) == 0:
                padding_length = ord(chunk[-1])
                chunk = chunk[:-padding_length]
                finished = True
            out_file.write(chunk)

        # reset the stream pointer to the beginning
        out_file.seek(0)
        new_data = out_file.read()

        # split out sha and verify decryption
        split_data = new_data.split("\n")
        this_sha = split_data[0]
        this_data = '\n'.join(split_data[1:])
        test_sha = sha256(this_data).hexdigest()

        if this_sha != test_sha:
            raise errors.AnsibleError("Decryption failed")

        #return out_file.read()
        return this_data


class VaultAES256(object):

    """
    Vault implementation using AES-CTR with an HMAC-SHA256 authentication code. 
    Keys are derived using PBKDF2
    """

    # http://www.daemonology.net/blog/2009-06-11-cryptographic-right-answers.html

    def __init__(self):

        if not HAS_PBKDF2 or not HAS_COUNTER or not HAS_HASH:
            raise errors.AnsibleError(CRYPTO_UPGRADE)

    def gen_key_initctr(self, password, salt):
        # 16 for AES 128, 32 for AES256
        keylength = 32

        # match the size used for counter.new to avoid extra work
        ivlength = 16 

        hash_function = SHA256

        # make two keys and one iv
        pbkdf2_prf = lambda p, s: HMAC.new(p, s, hash_function).digest()


        derivedkey = PBKDF2(password, salt, dkLen=(2 * keylength) + ivlength, 
                            count=10000, prf=pbkdf2_prf)

        key1 = derivedkey[:keylength]
        key2 = derivedkey[keylength:(keylength * 2)]
        iv = derivedkey[(keylength * 2):(keylength * 2) + ivlength]

        return key1, key2, hexlify(iv)


    def encrypt(self, data, password):

        salt = os.urandom(32)
        key1, key2, iv = self.gen_key_initctr(password, salt)

        # PKCS#7 PAD DATA http://tools.ietf.org/html/rfc5652#section-6.3
        bs = AES.block_size
        padding_length = (bs - len(data) % bs) or bs
        data += padding_length * chr(padding_length)

        # COUNTER.new PARAMETERS
        # 1) nbits (integer) - Length of the counter, in bits.
        # 2) initial_value (integer) - initial value of the counter. "iv" from gen_key_initctr

        ctr = Counter.new(128, initial_value=long(iv, 16))

        # AES.new PARAMETERS
        # 1) AES key, must be either 16, 24, or 32 bytes long -- "key" from gen_key_initctr
        # 2) MODE_CTR, is the recommended mode
        # 3) counter=<CounterObject>

        cipher = AES.new(key1, AES.MODE_CTR, counter=ctr)

        # ENCRYPT PADDED DATA
        cryptedData = cipher.encrypt(data)                

        # COMBINE SALT, DIGEST AND DATA
        hmac = HMAC.new(key2, cryptedData, SHA256)
        message = "%s\n%s\n%s" % ( hexlify(salt), hmac.hexdigest(), hexlify(cryptedData) )
        message = hexlify(message)
        return message

    def decrypt(self, data, password):

        # SPLIT SALT, DIGEST, AND DATA
        data = ''.join(data.split("\n"))
        data = unhexlify(data)
        salt, cryptedHmac, cryptedData = data.split("\n", 2)
        salt = unhexlify(salt)
        cryptedData = unhexlify(cryptedData)

        key1, key2, iv = self.gen_key_initctr(password, salt)

        # EXIT EARLY IF DIGEST DOESN'T MATCH 
        hmacDecrypt = HMAC.new(key2, cryptedData, SHA256)
        if not self.is_equal(cryptedHmac, hmacDecrypt.hexdigest()):
            return None

        # SET THE COUNTER AND THE CIPHER
        ctr = Counter.new(128, initial_value=long(iv, 16))
        cipher = AES.new(key1, AES.MODE_CTR, counter=ctr)

        # DECRYPT PADDED DATA
        decryptedData = cipher.decrypt(cryptedData)

        # UNPAD DATA
        padding_length = ord(decryptedData[-1])
        decryptedData = decryptedData[:-padding_length]

        return decryptedData

    def is_equal(self, a, b):
        # http://codahale.com/a-lesson-in-timing-attacks/
        if len(a) != len(b):
            return False
        
        result = 0
        for x, y in zip(a, b):
            result |= ord(x) ^ ord(y)
        return result == 0     



########NEW FILE########
__FILENAME__ = context_demo
# (C) 2012, Michael DeHaan, <michael.dehaan@gmail.com>

# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

import os
import time
import json

class CallbackModule(object):
    """
    This is a very trivial example of how any callback function can get at play and task objects.
    play will be 'None' for runner invocations, and task will be None for 'setup' invocations.
    """

    def on_any(self, *args, **kwargs):
        play = getattr(self, 'play', None)
        task = getattr(self, 'task', None)
        print "play = %s, task = %s, args = %s, kwargs = %s" % (play,task,args,kwargs)

########NEW FILE########
__FILENAME__ = hipchat
# (C) 2014, Matt Martz <matt@sivel.net>

# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

import os
import urllib
import urllib2

from ansible import utils

try:
    import prettytable
    HAS_PRETTYTABLE = True
except ImportError:
    HAS_PRETTYTABLE = False


class CallbackModule(object):
    """This is an example ansible callback plugin that sends status
    updates to a HipChat channel during playbook execution.

    This plugin makes use of the following environment variables:
        HIPCHAT_TOKEN (required): HipChat API token
        HIPCHAT_ROOM  (optional): HipChat room to post in. Default: ansible
        HIPCHAT_FROM  (optional): Name to post as. Default: ansible
        HIPCHAT_NOTIFY (optional): Add notify flag to important messages ("true" or "false"). Default: true

    Requires:
        prettytable

    """

    def __init__(self):
        if not HAS_PRETTYTABLE:
            self.disabled = True
            utils.warning('The `prettytable` python module is not installed. '
                          'Disabling the HipChat callback plugin.')

        self.msg_uri = 'https://api.hipchat.com/v1/rooms/message'
        self.token = os.getenv('HIPCHAT_TOKEN')
        self.room = os.getenv('HIPCHAT_ROOM', 'ansible')
        self.from_name = os.getenv('HIPCHAT_FROM', 'ansible')
        self.allow_notify = (os.getenv('HIPCHAT_NOTIFY') != 'false')

        if self.token is None:
            self.disabled = True
            utils.warning('HipChat token could not be loaded. The HipChat '
                          'token can be provided using the `HIPCHAT_TOKEN` '
                          'environment variable.')

        self.printed_playbook = False
        self.playbook_name = None

    def send_msg(self, msg, msg_format='text', color='yellow', notify=False):
        """Method for sending a message to HipChat"""

        params = {}
        params['room_id'] = self.room
        params['from'] = self.from_name[:15]  # max length is 15
        params['message'] = msg
        params['message_format'] = msg_format
        params['color'] = color
        params['notify'] = int(self.allow_notify and notify)

        url = ('%s?auth_token=%s' % (self.msg_uri, self.token))
        try:
            response = urllib2.urlopen(url, urllib.urlencode(params))
            return response.read()
        except:
            utils.warning('Could not submit message to hipchat')

    def on_any(self, *args, **kwargs):
        pass

    def runner_on_failed(self, host, res, ignore_errors=False):
        pass

    def runner_on_ok(self, host, res):
        pass

    def runner_on_error(self, host, msg):
        pass

    def runner_on_skipped(self, host, item=None):
        pass

    def runner_on_unreachable(self, host, res):
        pass

    def runner_on_no_hosts(self):
        pass

    def runner_on_async_poll(self, host, res, jid, clock):
        pass

    def runner_on_async_ok(self, host, res, jid):
        pass

    def runner_on_async_failed(self, host, res, jid):
        pass

    def playbook_on_start(self):
        pass

    def playbook_on_notify(self, host, handler):
        pass

    def playbook_on_no_hosts_matched(self):
        pass

    def playbook_on_no_hosts_remaining(self):
        pass

    def playbook_on_task_start(self, name, is_conditional):
        pass

    def playbook_on_vars_prompt(self, varname, private=True, prompt=None,
                                encrypt=None, confirm=False, salt_size=None,
                                salt=None, default=None):
        pass

    def playbook_on_setup(self):
        pass

    def playbook_on_import_for_host(self, host, imported_file):
        pass

    def playbook_on_not_import_for_host(self, host, missing_file):
        pass

    def playbook_on_play_start(self, pattern):
        """Display Playbook and play start messages"""

        # This block sends information about a playbook when it starts
        # The playbook object is not immediately available at
        # playbook_on_start so we grab it via the play
        #
        # Displays info about playbook being started by a person on an
        # inventory, as well as Tags, Skip Tags and Limits
        if not self.printed_playbook:
            self.playbook_name, _ = os.path.splitext(
                os.path.basename(self.play.playbook.filename))
            host_list = self.play.playbook.inventory.host_list
            inventory = os.path.basename(os.path.realpath(host_list))
            self.send_msg("%s: Playbook initiated by %s against %s" %
                          (self.playbook_name,
                           self.play.playbook.remote_user,
                           inventory), notify=True)
            self.printed_playbook = True
            subset = self.play.playbook.inventory._subset
            skip_tags = self.play.playbook.skip_tags
            self.send_msg("%s:\nTags: %s\nSkip Tags: %s\nLimit: %s" %
                          (self.playbook_name,
                           ', '.join(self.play.playbook.only_tags),
                           ', '.join(skip_tags) if skip_tags else None,
                           ', '.join(subset) if subset else subset))

        # This is where we actually say we are starting a play
        self.send_msg("%s: Starting play: %s" %
                      (self.playbook_name, pattern))

    def playbook_on_stats(self, stats):
        """Display info about playbook statistics"""
        hosts = sorted(stats.processed.keys())

        t = prettytable.PrettyTable(['Host', 'Ok', 'Changed', 'Unreachable',
                                     'Failures'])

        failures = False
        unreachable = False

        for h in hosts:
            s = stats.summarize(h)

            if s['failures'] > 0:
                failures = True
            if s['unreachable'] > 0:
                unreachable = True

            t.add_row([h] + [s[k] for k in ['ok', 'changed', 'unreachable',
                                            'failures']])

        self.send_msg("%s: Playbook complete" % self.playbook_name,
                      notify=True)

        if failures or unreachable:
            color = 'red'
            self.send_msg("%s: Failures detected" % self.playbook_name,
                          color=color, notify=True)
        else:
            color = 'green'

        self.send_msg("/code %s:\n%s" % (self.playbook_name, t), color=color)

########NEW FILE########
__FILENAME__ = log_plays
# (C) 2012, Michael DeHaan, <michael.dehaan@gmail.com>

# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

import os
import time
import json

# NOTE: in Ansible 1.2 or later general logging is available without
# this plugin, just set ANSIBLE_LOG_PATH as an environment variable
# or log_path in the DEFAULTS section of your ansible configuration
# file.  This callback is an example of per hosts logging for those
# that want it.

TIME_FORMAT="%b %d %Y %H:%M:%S"
MSG_FORMAT="%(now)s - %(category)s - %(data)s\n\n"

if not os.path.exists("/var/log/ansible/hosts"):
    os.makedirs("/var/log/ansible/hosts")

def log(host, category, data):
    if type(data) == dict:
        if 'verbose_override' in data:
            # avoid logging extraneous data from facts
            data = 'omitted'
        else:
            data = data.copy()
            invocation = data.pop('invocation', None)
            data = json.dumps(data)
            if invocation is not None:
                data = json.dumps(invocation) + " => %s " % data

    path = os.path.join("/var/log/ansible/hosts", host)
    now = time.strftime(TIME_FORMAT, time.localtime())
    fd = open(path, "a")
    fd.write(MSG_FORMAT % dict(now=now, category=category, data=data))
    fd.close()

class CallbackModule(object):
    """
    logs playbook results, per host, in /var/log/ansible/hosts
    """

    def on_any(self, *args, **kwargs):
        pass

    def runner_on_failed(self, host, res, ignore_errors=False):
        log(host, 'FAILED', res)

    def runner_on_ok(self, host, res):
        log(host, 'OK', res)

    def runner_on_error(self, host, msg):
        log(host, 'ERROR', msg)

    def runner_on_skipped(self, host, item=None):
        log(host, 'SKIPPED', '...')

    def runner_on_unreachable(self, host, res):
        log(host, 'UNREACHABLE', res)

    def runner_on_no_hosts(self):
        pass

    def runner_on_async_poll(self, host, res, jid, clock):
        pass

    def runner_on_async_ok(self, host, res, jid):
        pass

    def runner_on_async_failed(self, host, res, jid):
        log(host, 'ASYNC_FAILED', res)

    def playbook_on_start(self):
        pass

    def playbook_on_notify(self, host, handler):
        pass

    def playbook_on_no_hosts_matched(self):
        pass

    def playbook_on_no_hosts_remaining(self):
        pass

    def playbook_on_task_start(self, name, is_conditional):
        pass

    def playbook_on_vars_prompt(self, varname, private=True, prompt=None, encrypt=None, confirm=False, salt_size=None, salt=None, default=None):
        pass

    def playbook_on_setup(self):
        pass

    def playbook_on_import_for_host(self, host, imported_file):
        log(host, 'IMPORTED', imported_file)

    def playbook_on_not_import_for_host(self, host, missing_file):
        log(host, 'NOTIMPORTED', missing_file)

    def playbook_on_play_start(self, pattern):
        pass

    def playbook_on_stats(self, stats):
        pass


########NEW FILE########
__FILENAME__ = mail
# Copyright 2012 Dag Wieers <dag@wieers.com>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

import smtplib

def mail(subject='Ansible error mail', sender='<root>', to='root', cc=None, bcc=None, body=None):
    if not body:
        body = subject

    smtp = smtplib.SMTP('localhost')

    content = 'From: %s\n' % sender
    content += 'To: %s\n' % to
    if cc:
        content += 'Cc: %s\n' % cc
    content += 'Subject: %s\n\n' % subject
    content += body

    addresses = to.split(',')
    if cc:
        addresses += cc.split(',')
    if bcc:
        addresses += bcc.split(',')

    for address in addresses:
        smtp.sendmail(sender, address, content)

    smtp.quit()


class CallbackModule(object):

    """
    This Ansible callback plugin mails errors to interested parties.
    """

    def runner_on_failed(self, host, res, ignore_errors=False):
        if ignore_errors:
            return
        sender = '"Ansible: %s" <root>' % host
        subject = 'Failed: %(module_name)s %(module_args)s' % res['invocation']
        body = 'The following task failed for host ' + host + ':\n\n%(module_name)s %(module_args)s\n\n' % res['invocation']
        if 'stdout' in res.keys() and res['stdout']:
            subject = res['stdout'].strip('\r\n').split('\n')[-1]
            body += 'with the following output in standard output:\n\n' + res['stdout'] + '\n\n'
        if 'stderr' in res.keys() and res['stderr']:
            subject = res['stderr'].strip('\r\n').split('\n')[-1]
            body += 'with the following output in standard error:\n\n' + res['stderr'] + '\n\n'
        if 'msg' in res.keys() and res['msg']:
            subject = res['msg'].strip('\r\n').split('\n')[0]
            body += 'with the following message:\n\n' + res['msg'] + '\n\n'
        body += 'A complete dump of the error:\n\n' + str(res)
        mail(sender=sender, subject=subject, body=body)
                  
    def runner_on_error(self, host, msg):
        sender = '"Ansible: %s" <root>' % host
        subject = 'Error: %s' % msg.strip('\r\n').split('\n')[0]
        body = 'An error occured for host ' + host + ' with the following message:\n\n' + msg
        mail(sender=sender, subject=subject, body=body)

    def runner_on_unreachable(self, host, res):
        sender = '"Ansible: %s" <root>' % host
        if isinstance(res, basestring):
            subject = 'Unreachable: %s' % res.strip('\r\n').split('\n')[-1]
            body = 'An error occured for host ' + host + ' with the following message:\n\n' + res
        else:
            subject = 'Unreachable: %s' % res['msg'].strip('\r\n').split('\n')[0]
            body = 'An error occured for host ' + host + ' with the following message:\n\n' + \
                   res['msg'] + '\n\nA complete dump of the error:\n\n' + str(res)
        mail(sender=sender, subject=subject, body=body)

    def runner_on_async_failed(self, host, res, jid):
        sender = '"Ansible: %s" <root>' % host
        if isinstance(res, basestring):
            subject = 'Async failure: %s' % res.strip('\r\n').split('\n')[-1]
            body = 'An error occured for host ' + host + ' with the following message:\n\n' + res
        else:
            subject = 'Async failure: %s' % res['msg'].strip('\r\n').split('\n')[0]
            body = 'An error occured for host ' + host + ' with the following message:\n\n' + \
                   res['msg'] + '\n\nA complete dump of the error:\n\n' + str(res)
        mail(sender=sender, subject=subject, body=body)

########NEW FILE########
__FILENAME__ = osx_say

# (C) 2012, Michael DeHaan, <michael.dehaan@gmail.com>

# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

import subprocess
import os

FAILED_VOICE="Zarvox"
REGULAR_VOICE="Trinoids"
HAPPY_VOICE="Cellos"
LASER_VOICE="Princess"
SAY_CMD="/usr/bin/say"

def say(msg, voice):
    subprocess.call([SAY_CMD, msg, "--voice=%s" % (voice)])

class CallbackModule(object):
    """
    makes Ansible much more exciting on OS X.
    """
    def __init__(self):
        # plugin disable itself if say is not present
        # ansible will not call any callback if disabled is set to True
        if not os.path.exists(SAY_CMD):
            self.disabled = True
            print "%s does not exist, plugin %s disabled" % \
                    (SAY_CMD, os.path.basename(__file__))

    def on_any(self, *args, **kwargs):
        pass

    def runner_on_failed(self, host, res, ignore_errors=False):
        say("Failure on host %s" % host, FAILED_VOICE)

    def runner_on_ok(self, host, res):
        say("pew", LASER_VOICE)

    def runner_on_error(self, host, msg):
        pass

    def runner_on_skipped(self, host, item=None):
        say("pew", LASER_VOICE)

    def runner_on_unreachable(self, host, res):
        say("Failure on host %s" % host, FAILED_VOICE)

    def runner_on_no_hosts(self):
        pass

    def runner_on_async_poll(self, host, res, jid, clock):
        pass

    def runner_on_async_ok(self, host, res, jid):
        say("pew", LASER_VOICE)

    def runner_on_async_failed(self, host, res, jid):
        say("Failure on host %s" % host, FAILED_VOICE)

    def playbook_on_start(self):
        say("Running Playbook", REGULAR_VOICE)

    def playbook_on_notify(self, host, handler):
        say("pew", LASER_VOICE)

    def playbook_on_no_hosts_matched(self):
        pass

    def playbook_on_no_hosts_remaining(self):
        pass

    def playbook_on_task_start(self, name, is_conditional):
        if not is_conditional:
            say("Starting task: %s" % name, REGULAR_VOICE)
        else:
            say("Notifying task: %s" % name, REGULAR_VOICE)

    def playbook_on_vars_prompt(self, varname, private=True, prompt=None, encrypt=None, confirm=False, salt_size=None, salt=None, default=None):
        pass

    def playbook_on_setup(self):
        say("Gathering facts", REGULAR_VOICE)

    def playbook_on_import_for_host(self, host, imported_file):
        pass

    def playbook_on_not_import_for_host(self, host, missing_file):
        pass

    def playbook_on_play_start(self, pattern):
        say("Starting play: %s" % pattern, HAPPY_VOICE)

    def playbook_on_stats(self, stats):
        say("Play complete", HAPPY_VOICE)


########NEW FILE########
__FILENAME__ = abiquo
#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
External inventory script for Abiquo
====================================

Shamelessly copied from an existing inventory script.

This script generates an inventory that Ansible can understand by making API requests to Abiquo API
Requires some python libraries, ensure to have them installed when using this script.

This script has been tested in Abiquo 3.0 but it may work also for Abiquo 2.6.

Before using this script you may want to modify abiquo.ini config file.

This script generates an Ansible hosts file with these host groups:

ABQ_xxx: Defines a hosts itself by Abiquo VM name label
all: Contains all hosts defined in Abiquo user's enterprise
virtualdatecenter: Creates a host group for each virtualdatacenter containing all hosts defined on it 
virtualappliance: Creates a host group for each virtualappliance containing all hosts defined on it
imagetemplate: Creates a host group for each image template containing all hosts using it

'''

# (c) 2014, Daniel Beneyto <daniel.beneyto@abiquo.com>
#
# This file is part of Ansible,
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

import os
import sys
import time
import ConfigParser
import urllib2
import base64

try:
    import json
except ImportError:
    import simplejson as json

def api_get(link, config):
    try:
        if link == None:
            request = urllib2.Request(config.get('api','uri')+config.get('api','login_path'))
            request.add_header("Accept",config.get('api','login_type'))
        else:
            request = urllib2.Request(link['href']+'?limit=0')
            request.add_header("Accept",link['type'])
        # Auth
        base64string = base64.encodestring('%s:%s' % (config.get('auth','apiuser'),config.get('auth','apipass'))).replace('\n', '')
        request.add_header("Authorization", "Basic %s" % base64string)
        result = urllib2.urlopen(request)
        return json.loads(result.read())
    except:
        return None

def save_cache(data, config):
    ''' saves item to cache '''
    dpath = config.get('cache','cache_dir')
    try:
        cache = open('/'.join([dpath,'inventory']), 'w')
        cache.write(json.dumps(data))
        cache.close()
    except IOError, e:
        pass # not really sure what to do here


def get_cache(cache_item, config):
    ''' returns cached item  '''
    dpath = config.get('cache','cache_dir')
    inv = {}
    try:
        cache = open('/'.join([dpath,'inventory']), 'r')
        inv = cache.read()
        cache.close()
    except IOError, e:
        pass # not really sure what to do here

    return inv

def cache_available(config):
    ''' checks if we have a 'fresh' cache available for item requested '''

    if config.has_option('cache','cache_dir'):
        dpath = config.get('cache','cache_dir')

        try:
            existing = os.stat( '/'.join([dpath,'inventory']))
        except:
            # cache doesn't exist or isn't accessible
            return False

        if config.has_option('cache', 'cache_max_age'):
            maxage = config.get('cache', 'cache_max_age')
            if ((int(time.time()) - int(existing.st_mtime)) <= int(maxage)):
                return True

    return False

def generate_inv_from_api(enterprise_entity,config):    
    try:
        inventory['all'] = {}
        inventory['all']['children'] = []
        inventory['all']['hosts'] = []
        inventory['_meta'] = {}
        inventory['_meta']['hostvars'] = {}

        enterprise = api_get(enterprise_entity,config)
        vms_entity = next(link for link in (enterprise['links']) if (link['rel']=='virtualmachines'))
        vms = api_get(vms_entity,config)
        for vmcollection in vms['collection']:
            vm_vapp = next(link for link in (vmcollection['links']) if (link['rel']=='virtualappliance'))['title'].replace('[','').replace(']','').replace(' ','_')
            vm_vdc = next(link for link in (vmcollection['links']) if (link['rel']=='virtualdatacenter'))['title'].replace('[','').replace(']','').replace(' ','_')
            vm_template = next(link for link in (vmcollection['links']) if (link['rel']=='virtualmachinetemplate'))['title'].replace('[','').replace(']','').replace(' ','_')

            # From abiquo.ini: Only adding to inventory VMs with public IP
            if (config.getboolean('defaults', 'public_ip_only')) == True:
                for link in vmcollection['links']:
                    if (link['type']=='application/vnd.abiquo.publicip+json' and link['rel']=='ip'):
                      vm_nic = link['title']
                      break
                    else:
                      vm_nic = None
            # Otherwise, assigning defined network interface IP address
            else:
                for link in vmcollection['links']:
                    if (link['rel']==config.get('defaults', 'default_net_interface')):
                      vm_nic = link['title']
                      break
                    else:
                      vm_nic = None
            
            vm_state = True
            # From abiquo.ini: Only adding to inventory VMs deployed
            if ((config.getboolean('defaults', 'deployed_only') == True) and (vmcollection['state'] == 'NOT_ALLOCATED')):
                vm_state = False

            if not vm_nic == None and vm_state:
                if not vm_vapp in inventory.keys():
                    inventory[vm_vapp] = {}
                    inventory[vm_vapp]['children'] = []
                    inventory[vm_vapp]['hosts'] = []
                if not vm_vdc in inventory.keys():
                    inventory[vm_vdc] = {}
                    inventory[vm_vdc]['hosts'] = []
                    inventory[vm_vdc]['children'] = []
                if not vm_template in inventory.keys():
                    inventory[vm_template] = {}
                    inventory[vm_template]['children'] = []
                    inventory[vm_template]['hosts'] = []
                if config.getboolean('defaults', 'get_metadata') == True:
                    meta_entity = next(link for link in (vmcollection['links']) if (link['rel']=='metadata'))
                    try:
                        metadata = api_get(meta_entity,config)
                        inventory['_meta']['hostvars'][vm_nic] = metadata['metadata']['metadata']
                    except Exception, e:
                        pass

                inventory[vm_vapp]['children'].append(vmcollection['name'])
                inventory[vm_vdc]['children'].append(vmcollection['name'])
                inventory[vm_template]['children'].append(vmcollection['name'])
                inventory['all']['children'].append(vmcollection['name'])
                inventory[vmcollection['name']] = []
                inventory[vmcollection['name']].append(vm_nic)

        return inventory
    except Exception, e:
        # Return empty hosts output
        return { 'all': {'hosts': []}, '_meta': { 'hostvars': {} } }

def get_inventory(enterprise, config):
    ''' Reads the inventory from cache or Abiquo api '''

    if cache_available(config):
        inv = get_cache('inventory', config)
    else:
        default_group = os.path.basename(sys.argv[0]).rstrip('.py')
        # MAKE ABIQUO API CALLS #
        inv = generate_inv_from_api(enterprise,config)

    save_cache(inv, config)
    return json.dumps(inv)

if __name__ == '__main__':
    inventory = {}
    enterprise = {}

    # Read config
    config = ConfigParser.SafeConfigParser()
    for configfilename in [os.path.abspath(sys.argv[0]).rstrip('.py') + '.ini', 'abiquo.ini']:
        if os.path.exists(configfilename):
            config.read(configfilename)
            break

    try:
        login = api_get(None,config)
        enterprise = next(link for link in (login['links']) if (link['rel']=='enterprise'))
    except Exception, e:
        enterprise = None

    if cache_available(config):
        inventory = get_cache('inventory', config)
    else:
        inventory = get_inventory(enterprise, config)

    # return to ansible
    sys.stdout.write(str(inventory))
    sys.stdout.flush()

########NEW FILE########
__FILENAME__ = apache-libcloud
#!/usr/bin/env python

# (c) 2013, Sebastien Goasguen <runseb@gmail.com>
#
# This file is part of Ansible,
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

######################################################################

'''
Apache Libcloud generic external inventory script
=================================

Generates inventory that Ansible can understand by making API request to
Cloud providers using the Apache libcloud library.

This script also assumes there is a libcloud.ini file alongside it

'''

import sys
import os
import argparse
import re
from time import time
import ConfigParser

from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver
import libcloud.security as sec

try:
    import json
except ImportError:
    import simplejson as json


class LibcloudInventory(object):
    def __init__(self):
        ''' Main execution path '''

        # Inventory grouped by instance IDs, tags, security groups, regions,
        # and availability zones
        self.inventory = {}

        # Index of hostname (address) to instance ID
        self.index = {}

        # Read settings and parse CLI arguments
        self.read_settings()
        self.parse_cli_args()

        # Cache
        if self.args.refresh_cache:
            self.do_api_calls_update_cache()
        elif not self.is_cache_valid():
            self.do_api_calls_update_cache()

        # Data to print
        if self.args.host:
            data_to_print = self.get_host_info()

        elif self.args.list:
            # Display list of instances for inventory
            if len(self.inventory) == 0:
                data_to_print = self.get_inventory_from_cache()
            else:
                data_to_print = self.json_format_dict(self.inventory, True)

        print data_to_print


    def is_cache_valid(self):
        ''' Determines if the cache files have expired, or if it is still valid '''

        if os.path.isfile(self.cache_path_cache):
            mod_time = os.path.getmtime(self.cache_path_cache)
            current_time = time()
            if (mod_time + self.cache_max_age) > current_time:
                if os.path.isfile(self.cache_path_index):
                    return True

        return False


    def read_settings(self):
        ''' Reads the settings from the libcloud.ini file '''

        config = ConfigParser.SafeConfigParser()
        libcloud_default_ini_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'libcloud.ini')
        libcloud_ini_path = os.environ.get('LIBCLOUD_INI_PATH', libcloud_default_ini_path)
        config.read(libcloud_ini_path)

        if not config.has_section('driver'):
            raise ValueError('libcloud.ini file must contain a [driver] section')

        if config.has_option('driver', 'provider'):
            self.provider = config.get('driver','provider')
        else:
            raise ValueError('libcloud.ini does not have a provider defined')

        if config.has_option('driver', 'key'):
            self.key = config.get('driver','key')
        else:
            raise ValueError('libcloud.ini does not have a key defined')

        if config.has_option('driver', 'secret'):
            self.secret = config.get('driver','secret')
        else:
            raise ValueError('libcloud.ini does not have a secret defined')

        if config.has_option('driver', 'host'):
            self.host = config.get('driver', 'host')
        if config.has_option('driver', 'secure'):
            self.secure = config.get('driver', 'secure')
        if config.has_option('driver', 'verify_ssl_cert'):
            self.verify_ssl_cert = config.get('driver', 'verify_ssl_cert')
        if config.has_option('driver', 'port'):
            self.port = config.get('driver', 'port')
        if config.has_option('driver', 'path'):
            self.path = config.get('driver', 'path')
        if config.has_option('driver', 'api_version'):
            self.api_version = config.get('driver', 'api_version')    

        Driver = get_driver(getattr(Provider, self.provider))

        self.conn = Driver(key=self.key, secret=self.secret, secure=self.secure,
                           host=self.host, path=self.path)

        # Cache related
        cache_path = config.get('cache', 'cache_path')
        self.cache_path_cache = cache_path + "/ansible-libcloud.cache"
        self.cache_path_index = cache_path + "/ansible-libcloud.index"
        self.cache_max_age = config.getint('cache', 'cache_max_age')
        

    def parse_cli_args(self):
        '''
        Command line argument processing
        '''

        parser = argparse.ArgumentParser(description='Produce an Ansible Inventory file based on libcloud supported providers')
        parser.add_argument('--list', action='store_true', default=True,
                           help='List instances (default: True)')
        parser.add_argument('--host', action='store',
                           help='Get all the variables about a specific instance')
        parser.add_argument('--refresh-cache', action='store_true', default=False,
                           help='Force refresh of cache by making API requests to libcloud supported providers (default: False - use cache files)')
        self.args = parser.parse_args()


    def do_api_calls_update_cache(self):
        ''' 
        Do API calls to a location, and save data in cache files 
        '''

        self.get_nodes()

        self.write_to_cache(self.inventory, self.cache_path_cache)
        self.write_to_cache(self.index, self.cache_path_index)


    def get_nodes(self):
        '''
        Gets the list of all nodes
        '''

        for node in self.conn.list_nodes():
            self.add_node(node)


    def get_node(self, node_id):
        '''
        Gets details about a specific node
        '''

        return [node for node in self.conn.list_nodes() if node.id == node_id][0]


    def add_node(self, node):
        '''
        Adds a node to the inventory and index, as long as it is
        addressable 
        '''

        # Only want running instances
        if node.state != 0:
            return

        # Select the best destination address
        if not node.public_ips == []:
            dest = node.public_ips[0]
        if not dest:
            # Skip instances we cannot address (e.g. private VPC subnet)
            return

        # Add to index
        self.index[dest] = node.name

        # Inventory: Group by instance ID (always a group of 1)
        self.inventory[node.name] = [dest]
        '''
        # Inventory: Group by region
        self.push(self.inventory, region, dest)

        # Inventory: Group by availability zone
        self.push(self.inventory, node.placement, dest)

        # Inventory: Group by instance type
        self.push(self.inventory, self.to_safe('type_' + node.instance_type), dest)
        '''
        # Inventory: Group by key pair
        if node.extra['keyname']:
            self.push(self.inventory, self.to_safe('key_' + node.extra['keyname']), dest)
            
        # Inventory: Group by security group, quick thing to handle single sg
        if node.extra['securitygroup']:
            self.push(self.inventory, self.to_safe('sg_' + node.extra['securitygroup'][0]), dest)

    def get_host_info(self):
        '''
        Get variables about a specific host
        '''

        if len(self.index) == 0:
            # Need to load index from cache
            self.load_index_from_cache()

        if not self.args.host in self.index:
            # try updating the cache
            self.do_api_calls_update_cache()
            if not self.args.host in self.index:
                # host migh not exist anymore
                return self.json_format_dict({}, True)

        node_id = self.index[self.args.host]

        node = self.get_node(node_id)
        instance_vars = {}
        for key in vars(instance):
            value = getattr(instance, key)
            key = self.to_safe('ec2_' + key)

            # Handle complex types
            if type(value) in [int, bool]:
                instance_vars[key] = value
            elif type(value) in [str, unicode]:
                instance_vars[key] = value.strip()
            elif type(value) == type(None):
                instance_vars[key] = ''
            elif key == 'ec2_region':
                instance_vars[key] = value.name
            elif key == 'ec2_tags':
                for k, v in value.iteritems():
                    key = self.to_safe('ec2_tag_' + k)
                    instance_vars[key] = v
            elif key == 'ec2_groups':
                group_ids = []
                group_names = []
                for group in value:
                    group_ids.append(group.id)
                    group_names.append(group.name)
                instance_vars["ec2_security_group_ids"] = ','.join(group_ids)
                instance_vars["ec2_security_group_names"] = ','.join(group_names)
            else:
                pass
                # TODO Product codes if someone finds them useful
                #print key
                #print type(value)
                #print value

        return self.json_format_dict(instance_vars, True)


    def push(self, my_dict, key, element):
        '''
        Pushed an element onto an array that may not have been defined in
        the dict
        '''

        if key in my_dict:
            my_dict[key].append(element);
        else:
            my_dict[key] = [element]


    def get_inventory_from_cache(self):
        '''
        Reads the inventory from the cache file and returns it as a JSON
        object
        '''

        cache = open(self.cache_path_cache, 'r')
        json_inventory = cache.read()
        return json_inventory


    def load_index_from_cache(self):
        '''
        Reads the index from the cache file sets self.index
        '''

        cache = open(self.cache_path_index, 'r')
        json_index = cache.read()
        self.index = json.loads(json_index)


    def write_to_cache(self, data, filename):
        '''
        Writes data in JSON format to a file
        '''

        json_data = self.json_format_dict(data, True)
        cache = open(filename, 'w')
        cache.write(json_data)
        cache.close()


    def to_safe(self, word):
        '''
        Converts 'bad' characters in a string to underscores so they can be
        used as Ansible groups
        '''

        return re.sub("[^A-Za-z0-9\-]", "_", word)


    def json_format_dict(self, data, pretty=False):
        '''
        Converts a dict to a JSON object and dumps it as a formatted
        string
        '''

        if pretty:
            return json.dumps(data, sort_keys=True, indent=2)
        else:
            return json.dumps(data)

def main():
    LibcloudInventory()

if __name__ == '__main__':
	main()

########NEW FILE########
__FILENAME__ = cobbler
#!/usr/bin/python

"""
Cobbler external inventory script
=================================

Ansible has a feature where instead of reading from /etc/ansible/hosts
as a text file, it can query external programs to obtain the list
of hosts, groups the hosts are in, and even variables to assign to each host.

To use this, copy this file over /etc/ansible/hosts and chmod +x the file.
This, more or less, allows you to keep one central database containing
info about all of your managed instances.

This script is an example of sourcing that data from Cobbler
(http://cobbler.github.com).  With cobbler each --mgmt-class in cobbler
will correspond to a group in Ansible, and --ks-meta variables will be
passed down for use in templates or even in argument lines.

NOTE: The cobbler system names will not be used.  Make sure a
cobbler --dns-name is set for each cobbler system.   If a system
appears with two DNS names we do not add it twice because we don't want
ansible talking to it twice.  The first one found will be used. If no
--dns-name is set the system will NOT be visible to ansible.  We do
not add cobbler system names because there is no requirement in cobbler
that those correspond to addresses.

See http://ansible.github.com/api.html for more info

Tested with Cobbler 2.0.11.

Changelog:
    - 2013-09-01 pgehres: Refactored implementation to make use of caching and to
        limit the number of connections to external cobbler server for performance.
        Added use of cobbler.ini file to configure settings. Tested with Cobbler 2.4.0
"""

# (c) 2012, Michael DeHaan <michael.dehaan@gmail.com>
#
# This file is part of Ansible,
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

######################################################################


import argparse
import ConfigParser
import os
import re
from time import time
import xmlrpclib

try:
    import json
except ImportError:
    import simplejson as json

# NOTE -- this file assumes Ansible is being accessed FROM the cobbler
# server, so it does not attempt to login with a username and password.
# this will be addressed in a future version of this script.


class CobblerInventory(object):

    def __init__(self):
        """ Main execution path """
        self.conn = None

        self.inventory = dict()  # A list of groups and the hosts in that group
        self.cache = dict()  # Details about hosts in the inventory

        # Read settings and parse CLI arguments
        self.read_settings()
        self.parse_cli_args()

        # Cache
        if self.args.refresh_cache:
            self.update_cache()
        elif not self.is_cache_valid():
            self.update_cache()
        else:
            self.load_inventory_from_cache()
            self.load_cache_from_cache()

        data_to_print = ""

        # Data to print
        if self.args.host:
            data_to_print = self.get_host_info()

        elif self.args.list:
            # Display list of instances for inventory
            data_to_print = self.json_format_dict(self.inventory, True)

        else:  # default action with no options
            data_to_print = self.json_format_dict(self.inventory, True)

        print data_to_print

    def _connect(self):
        if not self.conn:
            self.conn = xmlrpclib.Server(self.cobbler_host, allow_none=True)

    def is_cache_valid(self):
        """ Determines if the cache files have expired, or if it is still valid """

        if os.path.isfile(self.cache_path_cache):
            mod_time = os.path.getmtime(self.cache_path_cache)
            current_time = time()
            if (mod_time + self.cache_max_age) > current_time:
                if os.path.isfile(self.cache_path_inventory):
                    return True

        return False

    def read_settings(self):
        """ Reads the settings from the cobbler.ini file """

        config = ConfigParser.SafeConfigParser()
        config.read(os.path.dirname(os.path.realpath(__file__)) + '/cobbler.ini')

        self.cobbler_host = config.get('cobbler', 'host')

        # Cache related
        cache_path = config.get('cobbler', 'cache_path')
        self.cache_path_cache = cache_path + "/ansible-cobbler.cache"
        self.cache_path_inventory = cache_path + "/ansible-cobbler.index"
        self.cache_max_age = config.getint('cobbler', 'cache_max_age')

    def parse_cli_args(self):
        """ Command line argument processing """

        parser = argparse.ArgumentParser(description='Produce an Ansible Inventory file based on Cobbler')
        parser.add_argument('--list', action='store_true', default=True, help='List instances (default: True)')
        parser.add_argument('--host', action='store', help='Get all the variables about a specific instance')
        parser.add_argument('--refresh-cache', action='store_true', default=False,
                            help='Force refresh of cache by making API requests to cobbler (default: False - use cache files)')
        self.args = parser.parse_args()

    def update_cache(self):
        """ Make calls to cobbler and save the output in a cache """

        self._connect()
        self.groups = dict()
        self.hosts = dict()

        data = self.conn.get_systems()

        for host in data:
            # Get the FQDN for the host and add it to the right groups
            dns_name = None
            ksmeta = None
            interfaces = host['interfaces']
            for (iname, ivalue) in interfaces.iteritems():
                if ivalue['management']:
                    this_dns_name = ivalue.get('dns_name', None)
                    if this_dns_name is not None and this_dns_name is not "":
                        dns_name = this_dns_name

            if dns_name is None:
                continue

            status = host['status']
            profile = host['profile']
            classes = host['mgmt_classes']

            if status not in self.inventory:
                self.inventory[status] = []
            self.inventory[status].append(dns_name)

            if profile not in self.inventory:
                self.inventory[profile] = []
            self.inventory[profile].append(dns_name)

            for cls in classes:
                if cls not in self.inventory:
                    self.inventory[cls] = []
                self.inventory[cls].append(dns_name)

            # Since we already have all of the data for the host, update the host details as well

            # The old way was ksmeta only -- provide backwards compatibility

            self.cache[dns_name] = dict()
            if "ks_meta" in host:
                for key, value in host["ks_meta"].iteritems():
                    self.cache[dns_name][key] = value

        self.write_to_cache(self.cache, self.cache_path_cache)
        self.write_to_cache(self.inventory, self.cache_path_inventory)

    def get_host_info(self):
        """ Get variables about a specific host """

        if not self.cache or len(self.cache) == 0:
            # Need to load index from cache
            self.load_cache_from_cache()

        if not self.args.host in self.cache:
            # try updating the cache
            self.update_cache()

            if not self.args.host in self.cache:
                # host might not exist anymore
                return self.json_format_dict({}, True)

        return self.json_format_dict(self.cache[self.args.host], True)

    def push(self, my_dict, key, element):
        """ Pushed an element onto an array that may not have been defined in the dict """

        if key in my_dict:
            my_dict[key].append(element)
        else:
            my_dict[key] = [element]

    def load_inventory_from_cache(self):
        """ Reads the index from the cache file sets self.index """

        cache = open(self.cache_path_inventory, 'r')
        json_inventory = cache.read()
        self.inventory = json.loads(json_inventory)

    def load_cache_from_cache(self):
        """ Reads the cache from the cache file sets self.cache """

        cache = open(self.cache_path_cache, 'r')
        json_cache = cache.read()
        self.cache = json.loads(json_cache)

    def write_to_cache(self, data, filename):
        """ Writes data in JSON format to a file """

        json_data = self.json_format_dict(data, True)
        cache = open(filename, 'w')
        cache.write(json_data)
        cache.close()

    def to_safe(self, word):
        """ Converts 'bad' characters in a string to underscores so they can be used as Ansible groups """

        return re.sub("[^A-Za-z0-9\-]", "_", word)

    def json_format_dict(self, data, pretty=False):
        """ Converts a dict to a JSON object and dumps it as a formatted string """

        if pretty:
            return json.dumps(data, sort_keys=True, indent=2)
        else:
            return json.dumps(data)

CobblerInventory()

########NEW FILE########
__FILENAME__ = digital_ocean
#!/usr/bin/env python

'''
DigitalOcean external inventory script
======================================

Generates Ansible inventory of DigitalOcean Droplets.

In addition to the --list and --host options used by Ansible, there are options
for generating JSON of other DigitalOcean data.  This is useful when creating
droplets.  For example, --regions will return all the DigitalOcean Regions.
This information can also be easily found in the cache file, whose default
location is /tmp/ansible-digital_ocean.cache).

The --pretty (-p) option pretty-prints the output for better human readability.

----
Although the cache stores all the information received from DigitalOcean,
the cache is not used for current droplet information (in --list, --host,
--all, and --droplets).  This is so that accurate droplet information is always
found.  You can force this script to use the cache with --force-cache.

----
Configuration is read from `digital_ocean.ini`, then from environment variables,
then and command-line arguments.

Most notably, the DigitalOcean Client ID and API Key must be specified.  They
can be specified in the INI file or with the following environment variables:
    export DO_CLIENT_ID='DO123' DO_API_KEY='abc123'

Alternatively, they can be passed on the command-line with --client-id and
--api-key.

If you specify DigitalOcean credentials in the INI file, a handy way to
get them into your environment (e.g., to use the digital_ocean module)
is to use the output of the --env option with export:
    export $(digital_ocean.py --env)

----
The following groups are generated from --list:
 - ID    (droplet ID)
 - NAME  (droplet NAME)
 - image_ID
 - image_NAME
 - distro_NAME  (distribution NAME from image)
 - region_ID
 - region_NAME
 - size_ID
 - size_NAME
 - status_STATUS

When run against a specific host, this script returns the following variables:
 - do_created_at
 - do_distroy
 - do_id
 - do_image
 - do_image_id
 - do_ip_address
 - do_name
 - do_region
 - do_region_id
 - do_size
 - do_size_id
 - do_status

-----
```
usage: digital_ocean.py [-h] [--list] [--host HOST] [--all]
                                 [--droplets] [--regions] [--images] [--sizes]
                                 [--ssh-keys] [--domains] [--pretty]
                                 [--cache-path CACHE_PATH]
                                 [--cache-max_age CACHE_MAX_AGE]
                                 [--refresh-cache] [--client-id CLIENT_ID]
                                 [--api-key API_KEY]

Produce an Ansible Inventory file based on DigitalOcean credentials

optional arguments:
  -h, --help            show this help message and exit
  --list                List all active Droplets as Ansible inventory
                        (default: True)
  --host HOST           Get all Ansible inventory variables about a specific
                        Droplet
  --all                 List all DigitalOcean information as JSON
  --droplets            List Droplets as JSON
  --regions             List Regions as JSON
  --images              List Images as JSON
  --sizes               List Sizes as JSON
  --ssh-keys            List SSH keys as JSON
  --domains             List Domains as JSON
  --pretty, -p          Pretty-print results
  --cache-path CACHE_PATH
                        Path to the cache files (default: .)
  --cache-max_age CACHE_MAX_AGE
                        Maximum age of the cached items (default: 0)
  --refresh-cache       Force refresh of cache by making API requests to
                        DigitalOcean (default: False - use cache files)
  --client-id CLIENT_ID, -c CLIENT_ID
                        DigitalOcean Client ID
  --api-key API_KEY, -a API_KEY
                        DigitalOcean API Key
```

'''

# (c) 2013, Evan Wies <evan@neomantra.net>
#
# Inspired by the EC2 inventory plugin:
# https://github.com/ansible/ansible/blob/devel/plugins/inventory/ec2.py
#
# This file is part of Ansible,
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

######################################################################

import os
import sys
import re
import argparse
from time import time
import ConfigParser

try:
    import json
except ImportError:
    import simplejson as json

try:
    from dopy.manager import DoError, DoManager
except ImportError, e:
    print "failed=True msg='`dopy` library required for this script'"
    sys.exit(1)



class DigitalOceanInventory(object):

    ###########################################################################
    # Main execution path
    ###########################################################################

    def __init__(self):
        ''' Main execution path '''

        # DigitalOceanInventory data
        self.data = {}      # All DigitalOcean data
        self.inventory = {} # Ansible Inventory
        self.index = {}     # Varous indices of Droplet metadata

        # Define defaults
        self.cache_path = '.'
        self.cache_max_age = 0

        # Read settings, environment variables, and CLI arguments
        self.read_settings()
        self.read_environment()
        self.read_cli_args()

        # Verify credentials were set
        if not hasattr(self, 'client_id') or not hasattr(self, 'api_key'):
            print '''Could not find values for DigitalOcean client_id and api_key.
They must be specified via either ini file, command line argument (--client-id and --api-key),
or environment variables (DO_CLIENT_ID and DO_API_KEY)'''
            sys.exit(-1)

        # env command, show DigitalOcean credentials
        if self.args.env:
            print "DO_CLIENT_ID=%s DO_API_KEY=%s" % (self.client_id, self.api_key)
            sys.exit(0)

        # Manage cache
        self.cache_filename = self.cache_path + "/ansible-digital_ocean.cache"
        self.cache_refreshed = False

        if not self.args.force_cache and self.args.refresh_cache or not self.is_cache_valid():
            self.load_all_data_from_digital_ocean()
        else:
            self.load_from_cache()
            if len(self.data) == 0:
                if self.args.force_cache:
                    print '''Cache is empty and --force-cache was specified'''
                    sys.exit(-1)
                self.load_all_data_from_digital_ocean()
            else:
                # We always get fresh droplets for --list, --host, --all, and --droplets
                # unless --force-cache is specified
                if not self.args.force_cache and (
                   self.args.list or self.args.host or self.args.all or self.args.droplets):
                    self.load_droplets_from_digital_ocean()

        # Pick the json_data to print based on the CLI command
        if self.args.droplets:   json_data = { 'droplets': self.data['droplets'] }
        elif self.args.regions:  json_data = { 'regions':  self.data['regions'] }
        elif self.args.images:   json_data = { 'images':   self.data['images'] }
        elif self.args.sizes:    json_data = { 'sizes':    self.data['sizes'] }
        elif self.args.ssh_keys: json_data = { 'ssh_keys': self.data['ssh_keys'] }
        elif self.args.domains:  json_data = { 'domains':  self.data['domains'] }
        elif self.args.all:      json_data = self.data

        elif self.args.host:     json_data = self.load_droplet_variables_for_host()
        else:    # '--list' this is last to make it default
                                 json_data = self.inventory

        if self.args.pretty:
            print json.dumps(json_data, sort_keys=True, indent=2)
        else:
            print json.dumps(json_data)
        # That's all she wrote...


    ###########################################################################
    # Script configuration
    ###########################################################################

    def read_settings(self):
        ''' Reads the settings from the digital_ocean.ini file '''
        config = ConfigParser.SafeConfigParser()
        config.read(os.path.dirname(os.path.realpath(__file__)) + '/digital_ocean.ini')

        # Credentials
        if config.has_option('digital_ocean', 'client_id'):
            self.client_id = config.get('digital_ocean', 'client_id')
        if config.has_option('digital_ocean', 'api_key'):
            self.api_key = config.get('digital_ocean', 'api_key')

        # Cache related
        if config.has_option('digital_ocean', 'cache_path'):
            self.cache_path = config.get('digital_ocean', 'cache_path')
        if config.has_option('digital_ocean', 'cache_max_age'):
            self.cache_max_age = config.getint('digital_ocean', 'cache_max_age')


    def read_environment(self):
        ''' Reads the settings from environment variables '''
        # Setup credentials
        if os.getenv("DO_CLIENT_ID"): self.client_id = os.getenv("DO_CLIENT_ID")
        if os.getenv("DO_API_KEY"):   self.api_key = os.getenv("DO_API_KEY")


    def read_cli_args(self):
        ''' Command line argument processing '''
        parser = argparse.ArgumentParser(description='Produce an Ansible Inventory file based on DigitalOcean credentials')

        parser.add_argument('--list', action='store_true', help='List all active Droplets as Ansible inventory (default: True)')
        parser.add_argument('--host', action='store', help='Get all Ansible inventory variables about a specific Droplet')

        parser.add_argument('--all', action='store_true', help='List all DigitalOcean information as JSON')
        parser.add_argument('--droplets','-d', action='store_true', help='List Droplets as JSON')
        parser.add_argument('--regions', action='store_true', help='List Regions as JSON')
        parser.add_argument('--images', action='store_true', help='List Images as JSON')
        parser.add_argument('--sizes', action='store_true', help='List Sizes as JSON')
        parser.add_argument('--ssh-keys', action='store_true', help='List SSH keys as JSON')
        parser.add_argument('--domains', action='store_true',help='List Domains as JSON')

        parser.add_argument('--pretty','-p', action='store_true', help='Pretty-print results')

        parser.add_argument('--cache-path', action='store', help='Path to the cache files (default: .)')
        parser.add_argument('--cache-max_age', action='store', help='Maximum age of the cached items (default: 0)')
        parser.add_argument('--force-cache', action='store_true', default=False, help='Only use data from the cache')
        parser.add_argument('--refresh-cache','-r', action='store_true', default=False, help='Force refresh of cache by making API requests to DigitalOcean (default: False - use cache files)')

        parser.add_argument('--env','-e', action='store_true', help='Display DO_CLIENT_ID and DO_API_KEY')
        parser.add_argument('--client-id','-c', action='store', help='DigitalOcean Client ID')
        parser.add_argument('--api-key','-a', action='store', help='DigitalOcean API Key')

        self.args = parser.parse_args()

        if self.args.client_id: self.client_id = self.args.client_id
        if self.args.api_key: self.api_key = self.args.api_key
        if self.args.cache_path: self.cache_path = self.args.cache_path
        if self.args.cache_max_age: self.cache_max_age = self.args.cache_max_age

        # Make --list default if none of the other commands are specified
        if (not self.args.droplets and not self.args.regions and not self.args.images and
            not self.args.sizes and not self.args.ssh_keys and not self.args.domains and
            not self.args.all and not self.args.host):
                self.args.list = True


    ###########################################################################
    # Data Management
    ###########################################################################

    def load_all_data_from_digital_ocean(self):
        ''' Use dopy to get all the information from DigitalOcean and save data in cache files '''
        manager  = DoManager(self.client_id, self.api_key)

        self.data = {}
        self.data['droplets'] = self.sanitize_list(manager.all_active_droplets())
        self.data['regions']  = self.sanitize_list(manager.all_regions())
        self.data['images']   = self.sanitize_list(manager.all_images(filter=None))
        self.data['sizes']    = self.sanitize_list(manager.sizes())
        self.data['ssh_keys'] = self.sanitize_list(manager.all_ssh_keys())
        self.data['domains']  = self.sanitize_list(manager.all_domains())

        self.index = {}
        self.index['region_to_name']  = self.build_index(self.data['regions'], 'id', 'name')
        self.index['size_to_name']    = self.build_index(self.data['sizes'], 'id', 'name')
        self.index['image_to_name']   = self.build_index(self.data['images'], 'id', 'name')
        self.index['image_to_distro'] = self.build_index(self.data['images'], 'id', 'distribution')
        self.index['host_to_droplet'] = self.build_index(self.data['droplets'], 'ip_address', 'id', False)

        self.build_inventory()

        self.write_to_cache()


    def load_droplets_from_digital_ocean(self):
        ''' Use dopy to get droplet information from DigitalOcean and save data in cache files '''
        manager  = DoManager(self.client_id, self.api_key)
        self.data['droplets'] = self.sanitize_list(manager.all_active_droplets())
        self.index['host_to_droplet'] = self.build_index(self.data['droplets'], 'ip_address', 'id', False)
        self.build_inventory()
        self.write_to_cache()


    def build_index(self, source_seq, key_from, key_to, use_slug=True):
        dest_dict = {}
        for item in source_seq:
            name = (use_slug and item.has_key('slug')) and item['slug'] or item[key_to]
            key = item[key_from]
            dest_dict[key] = name
        return dest_dict


    def build_inventory(self):
        '''Build Ansible inventory of droplets'''
        self.inventory = {}

        # add all droplets by id and name
        for droplet in self.data['droplets']:
            dest = droplet['ip_address']

            self.inventory[droplet['id']] = [dest]
            self.push(self.inventory, droplet['name'], dest)
            self.push(self.inventory, 'region_'+droplet['region_id'], dest)
            self.push(self.inventory, 'image_' +droplet['image_id'], dest)
            self.push(self.inventory, 'size_'  +droplet['size_id'], dest)
            self.push(self.inventory, 'status_'+droplet['status'], dest)

            region_name = self.index['region_to_name'].get(droplet['region_id'])
            if region_name:
                self.push(self.inventory, 'region_'+region_name, dest)

            size_name = self.index['size_to_name'].get(droplet['size_id'])
            if size_name:
                self.push(self.inventory, 'size_'+size_name, dest)

            image_name = self.index['image_to_name'].get(droplet['image_id'])
            if image_name:
                self.push(self.inventory, 'image_'+image_name, dest)

            distro_name = self.index['image_to_distro'].get(droplet['image_id'])
            if distro_name:
                self.push(self.inventory, 'distro_'+distro_name, dest)


    def load_droplet_variables_for_host(self):
        '''Generate a JSON reponse to a --host call'''
        host = self.to_safe(str(self.args.host))

        if not host in self.index['host_to_droplet']:
            # try updating cache
            if not self.args.force_cache:
                self.load_all_data_from_digital_ocean()
            if not host in self.index['host_to_droplet']:
                # host might not exist anymore
                return {}

        droplet = None
        if self.cache_refreshed:
            for drop in self.data['droplets']:
                if drop['ip_address'] == host:
                    droplet = self.sanitize_dict(drop)
                    break
        else:
            # Cache wasn't refreshed this run, so hit DigitalOcean API
            manager = DoManager(self.client_id, self.api_key)
            droplet_id = self.index['host_to_droplet'][host]
            droplet = self.sanitize_dict(manager.show_droplet(droplet_id))
       
        if not droplet:
            return {}

        # Put all the information in a 'do_' namespace
        info = {}
        for k, v in droplet.items():
            info['do_'+k] = v

        # Generate user-friendly variables (i.e. not the ID's) 
        if droplet.has_key('region_id'):
            info['do_region'] = self.index['region_to_name'].get(droplet['region_id'])
        if droplet.has_key('size_id'):
            info['do_size'] = self.index['size_to_name'].get(droplet['size_id'])
        if droplet.has_key('image_id'):
            info['do_image']  = self.index['image_to_name'].get(droplet['image_id'])
            info['do_distro'] = self.index['image_to_distro'].get(droplet['image_id'])

        return info



    ###########################################################################
    # Cache Management
    ###########################################################################

    def is_cache_valid(self):
        ''' Determines if the cache files have expired, or if it is still valid '''
        if os.path.isfile(self.cache_filename):
            mod_time = os.path.getmtime(self.cache_filename)
            current_time = time()
            if (mod_time + self.cache_max_age) > current_time:
                return True
        return False


    def load_from_cache(self):
        ''' Reads the data from the cache file and assigns it to member variables as Python Objects'''
        cache = open(self.cache_filename, 'r')
        json_data = cache.read()
        cache.close()
        data = json.loads(json_data)

        self.data = data['data']
        self.inventory = data['inventory']
        self.index = data['index']


    def write_to_cache(self):
        ''' Writes data in JSON format to a file '''
        data = { 'data': self.data, 'index': self.index, 'inventory': self.inventory }
        json_data = json.dumps(data, sort_keys=True, indent=2)

        cache = open(self.cache_filename, 'w')
        cache.write(json_data)
        cache.close()



    ###########################################################################
    # Utilities
    ###########################################################################

    def push(self, my_dict, key, element):
        ''' Pushed an element onto an array that may not have been defined in the dict '''
        if key in my_dict:
            my_dict[key].append(element);
        else:
            my_dict[key] = [element]


    def to_safe(self, word):
        ''' Converts 'bad' characters in a string to underscores so they can be used as Ansible groups '''
        return re.sub("[^A-Za-z0-9\-\.]", "_", word)


    def sanitize_dict(self, d):
        new_dict = {}
        for k, v in d.items():
            if v != None:
                new_dict[self.to_safe(str(k))] = self.to_safe(str(v))
        return new_dict


    def sanitize_list(self, seq):
        new_seq = []
        for d in seq:
            new_seq.append(self.sanitize_dict(d))
        return new_seq



###########################################################################
# Run the script
DigitalOceanInventory()

########NEW FILE########
__FILENAME__ = docker
#!/usr/bin/env python

# (c) 2013, Paul Durivage <paul.durivage@gmail.com>
#
# This file is part of Ansible.
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.
#
#
# Author: Paul Durivage <paul.durivage@gmail.com>
#
# Description:
# This module queries local or remote Docker daemons and generates
# inventory information.
#
# This plugin does not support targeting of specific hosts using the --host
# flag. Instead, it it queries the Docker API for each container, running
# or not, and returns this data all once.
#
# The plugin returns the following custom attributes on Docker containers:
#    docker_args
#    docker_config
#    docker_created
#    docker_driver
#    docker_exec_driver
#    docker_host_config
#    docker_hostname_path
#    docker_hosts_path
#    docker_id
#    docker_image
#    docker_name
#    docker_network_settings
#    docker_path
#    docker_resolv_conf_path
#    docker_state
#    docker_volumes
#    docker_volumes_rw
#
# Requirements:
# The docker-py module: https://github.com/dotcloud/docker-py
#
# Notes:
# A config file can be used to configure this inventory module, and there
# are several environment variables that can be set to modify the behavior
# of the plugin at runtime:
#    DOCKER_CONFIG_FILE
#    DOCKER_HOST
#    DOCKER_VERSION
#    DOCKER_TIMEOUT
#    DOCKER_PRIVATE_SSH_PORT
#    DOCKER_DEFAULT_IP
#
# Environment Variables:
# environment variable: DOCKER_CONFIG_FILE
#     description:
#         - A path to a Docker inventory hosts/defaults file in YAML format
#         - A sample file has been provided, colocated with the inventory
#           file called 'docker.yml'
#     required: false
#     default: Uses docker.docker.Client constructor defaults
# environment variable: DOCKER_HOST
#     description:
#         - The socket on which to connect to a Docker daemon API
#     required: false
#     default: Uses docker.docker.Client constructor defaults
# environment variable: DOCKER_VERSION
#     description:
#         - Version of the Docker API to use
#     default: Uses docker.docker.Client constructor defaults
#     required: false
# environment variable: DOCKER_TIMEOUT
#     description:
#         - Timeout in seconds for connections to Docker daemon API
#     default: Uses docker.docker.Client constructor defaults
#     required: false
# environment variable: DOCKER_PRIVATE_SSH_PORT
#     description:
#         - The private port (container port) on which SSH is listening
#           for connections
#     default: 22
#     required: false
# environment variable: DOCKER_DEFAULT_IP
#     description:
#         - This environment variable overrides the container SSH connection
#           IP address (aka, 'ansible_ssh_host')
#
#           This option allows one to override the ansible_ssh_host whenever
#           Docker has exercised its default behavior of binding private ports
#           to all interfaces of the Docker host.  This behavior, when dealing
#           with remote Docker hosts, does not allow Ansible to determine
#           a proper host IP address on which to connect via SSH to containers.
#           By default, this inventory module assumes all 0.0.0.0-exposed
#           ports to be bound to localhost:<port>.  To override this
#           behavior, for example, to bind a container's SSH port to the public
#           interface of its host, one must manually set this IP.
#
#           It is preferable to begin to launch Docker containers with
#           ports exposed on publicly accessible IP addresses, particularly
#           if the containers are to be targeted by Ansible for remote
#           configuration, not accessible via localhost SSH connections.
#
#           Docker containers can be explicitly exposed on IP addresses by
#           a) starting the daemon with the --ip argument
#           b) running containers with the -P/--publish ip::containerPort
#              argument
#     default: 127.0.0.1 if port exposed on 0.0.0.0 by Docker
#     required: false
#
# Examples:
#  Use the config file:
#  DOCKER_CONFIG_FILE=./docker.yml docker.py --list
#
#  Connect to docker instance on localhost port 4243
#  DOCKER_HOST=tcp://localhost:4243 docker.py --list
#
#  Any container's ssh port exposed on 0.0.0.0 will mapped to
#  another IP address (where Ansible will attempt to connect via SSH)
#  DOCKER_DEFAULT_IP=1.2.3.4 docker.py --list

import os
import sys
import json
import argparse

from UserDict import UserDict
from collections import defaultdict

import yaml

from requests import HTTPError, ConnectionError

# Manipulation of the path is needed because the docker-py
# module is imported by the name docker, and because this file
# is also named docker
for path in [os.getcwd(), '', os.path.dirname(os.path.abspath(__file__))]:
    try:
        del sys.path[sys.path.index(path)]
    except:
        pass

try:
    import docker
except ImportError:
    print('docker-py is required for this module')
    sys.exit(1)


class HostDict(UserDict):
    def __setitem__(self, key, value):
        if value is not None:
            self.data[key] = value

    def update(self, dict=None, **kwargs):
        if dict is None:
            pass
        elif isinstance(dict, UserDict):
            for k, v in dict.data.items():
                self[k] = v
        else:
            for k, v in dict.items():
                self[k] = v
        if len(kwargs):
            for k, v in kwargs.items():
                self[k] = v


def write_stderr(string):
    sys.stderr.write('%s\n' % string)


def setup():
    config = dict()
    config_file = os.environ.get('DOCKER_CONFIG_FILE')
    if config_file:
        try:
            config_file = os.path.abspath(config_file)
        except Exception as e:
            write_stderr(e)
            sys.exit(1)

        with open(config_file) as f:
            try:
                config = yaml.safe_load(f.read())
            except Exception as e:
                write_stderr(e)
                sys.exit(1)

    # Enviroment Variables
    env_base_url = os.environ.get('DOCKER_HOST')
    env_version = os.environ.get('DOCKER_VERSION')
    env_timeout = os.environ.get('DOCKER_TIMEOUT')
    env_ssh_port = os.environ.get('DOCKER_PRIVATE_SSH_PORT', '22')
    env_default_ip = os.environ.get('DOCKER_DEFAULT_IP', '127.0.0.1')
    # Config file defaults
    defaults = config.get('defaults', dict())
    def_host = defaults.get('host')
    def_version = defaults.get('version')
    def_timeout = defaults.get('timeout')
    def_default_ip = defaults.get('default_ip')
    def_ssh_port = defaults.get('private_ssh_port')

    hosts = list()

    if config:
        hosts_list = config.get('hosts', list())
        # Look to the config file's defined hosts
        if hosts_list:
            for host in hosts_list:
                baseurl = host.get('host') or def_host or env_base_url
                version = host.get('version') or def_version or env_version
                timeout = host.get('timeout') or def_timeout or env_timeout
                default_ip = host.get('default_ip') or def_default_ip or env_default_ip
                ssh_port = host.get('private_ssh_port') or def_ssh_port or env_ssh_port

                hostdict = HostDict(
                    base_url=baseurl,
                    version=version,
                    timeout=timeout,
                    default_ip=default_ip,
                    private_ssh_port=ssh_port,
                )
                hosts.append(hostdict)
        # Look to the defaults
        else:
            hostdict = HostDict(
                base_url=def_host,
                version=def_version,
                timeout=def_timeout,
                default_ip=def_default_ip,
                private_ssh_port=def_ssh_port,
            )
            hosts.append(hostdict)
    # Look to the environment
    else:
        hostdict = HostDict(
            base_url=env_base_url,
            version=env_version,
            timeout=env_timeout,
            default_ip=env_default_ip,
            private_ssh_port=env_ssh_port,
        )
        hosts.append(hostdict)

    return hosts


def list_groups():
    hosts = setup()
    groups = defaultdict(list)
    hostvars = defaultdict(dict)

    for host in hosts:
        ssh_port = host.pop('private_ssh_port', None)
        default_ip = host.pop('default_ip', None)
        hostname = host.get('base_url')

        try:
            client = docker.Client(**host)
            containers = client.containers(all=True)
        except (HTTPError, ConnectionError) as e:
            write_stderr(e)
            sys.exit(1)

        for container in containers:
            id = container.get('Id')
            short_id = id[:13]
            try:
                name = container.get('Names', list()).pop(0).lstrip('/')
            except IndexError:
                name = short_id

            if not id:
                continue

            inspect = client.inspect_container(id)
            running = inspect.get('State', dict()).get('Running')

            groups[id].append(name)
            groups[name].append(name)
            if not short_id in groups.keys():
                groups[short_id].append(name)
            groups[hostname].append(name)

            if running is True:
                groups['running'].append(name)
            else:
                groups['stopped'].append(name)

            try:
                port = client.port(container, ssh_port)[0]
            except (IndexError, AttributeError, TypeError):
                port = dict()

            try:
                ip = default_ip if port['HostIp'] == '0.0.0.0' else port['HostIp']
            except KeyError:
                ip = ''

            container_info = dict(
                ansible_ssh_host=ip,
                ansible_ssh_port=port.get('HostPort', int()),
                docker_args=inspect.get('Args'),
                docker_config=inspect.get('Config'),
                docker_created=inspect.get('Created'),
                docker_driver=inspect.get('Driver'),
                docker_exec_driver=inspect.get('ExecDriver'),
                docker_host_config=inspect.get('HostConfig'),
                docker_hostname_path=inspect.get('HostnamePath'),
                docker_hosts_path=inspect.get('HostsPath'),
                docker_id=inspect.get('ID'),
                docker_image=inspect.get('Image'),
                docker_name=name,
                docker_network_settings=inspect.get('NetworkSettings'),
                docker_path=inspect.get('Path'),
                docker_resolv_conf_path=inspect.get('ResolvConfPath'),
                docker_state=inspect.get('State'),
                docker_volumes=inspect.get('Volumes'),
                docker_volumes_rw=inspect.get('VolumesRW'),
            )

            hostvars[name].update(container_info)

    groups['docker_hosts'] = [host.get('base_url') for host in hosts]
    groups['_meta'] = dict()
    groups['_meta']['hostvars'] = hostvars
    print json.dumps(groups, sort_keys=True, indent=4)
    sys.exit(0)


def parse_args():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--list', action='store_true')
    group.add_argument('--host', action='store_true')
    return parser.parse_args()


def main():
    args = parse_args()
    if args.list:
        list_groups()
    elif args.host:
        write_stderr('This option is not supported.')
        sys.exit(1)
    sys.exit(0)


main()

########NEW FILE########
__FILENAME__ = ec2
#!/usr/bin/env python

'''
EC2 external inventory script
=================================

Generates inventory that Ansible can understand by making API request to
AWS EC2 using the Boto library.

NOTE: This script assumes Ansible is being executed where the environment
variables needed for Boto have already been set:
    export AWS_ACCESS_KEY_ID='AK123'
    export AWS_SECRET_ACCESS_KEY='abc123'

This script also assumes there is an ec2.ini file alongside it.  To specify a
different path to ec2.ini, define the EC2_INI_PATH environment variable:

    export EC2_INI_PATH=/path/to/my_ec2.ini

If you're using eucalyptus you need to set the above variables and
you need to define:

    export EC2_URL=http://hostname_of_your_cc:port/services/Eucalyptus

For more details, see: http://docs.pythonboto.org/en/latest/boto_config_tut.html

When run against a specific host, this script returns the following variables:
 - ec2_ami_launch_index
 - ec2_architecture
 - ec2_association
 - ec2_attachTime
 - ec2_attachment
 - ec2_attachmentId
 - ec2_client_token
 - ec2_deleteOnTermination
 - ec2_description
 - ec2_deviceIndex
 - ec2_dns_name
 - ec2_eventsSet
 - ec2_group_name
 - ec2_hypervisor
 - ec2_id
 - ec2_image_id
 - ec2_instanceState
 - ec2_instance_type
 - ec2_ipOwnerId
 - ec2_ip_address
 - ec2_item
 - ec2_kernel
 - ec2_key_name
 - ec2_launch_time
 - ec2_monitored
 - ec2_monitoring
 - ec2_networkInterfaceId
 - ec2_ownerId
 - ec2_persistent
 - ec2_placement
 - ec2_platform
 - ec2_previous_state
 - ec2_private_dns_name
 - ec2_private_ip_address
 - ec2_publicIp
 - ec2_public_dns_name
 - ec2_ramdisk
 - ec2_reason
 - ec2_region
 - ec2_requester_id
 - ec2_root_device_name
 - ec2_root_device_type
 - ec2_security_group_ids
 - ec2_security_group_names
 - ec2_shutdown_state
 - ec2_sourceDestCheck
 - ec2_spot_instance_request_id
 - ec2_state
 - ec2_state_code
 - ec2_state_reason
 - ec2_status
 - ec2_subnet_id
 - ec2_tenancy
 - ec2_virtualization_type
 - ec2_vpc_id

These variables are pulled out of a boto.ec2.instance object. There is a lack of
consistency with variable spellings (camelCase and underscores) since this
just loops through all variables the object exposes. It is preferred to use the
ones with underscores when multiple exist.

In addition, if an instance has AWS Tags associated with it, each tag is a new
variable named:
 - ec2_tag_[Key] = [Value]

Security groups are comma-separated in 'ec2_security_group_ids' and
'ec2_security_group_names'.
'''

# (c) 2012, Peter Sankauskas
#
# This file is part of Ansible,
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

######################################################################

import sys
import os
import argparse
import re
from time import time
import boto
from boto import ec2
from boto import rds
from boto import route53
import ConfigParser

try:
    import json
except ImportError:
    import simplejson as json


class Ec2Inventory(object):
    def _empty_inventory(self):
        return {"_meta" : {"hostvars" : {}}}

    def __init__(self):
        ''' Main execution path '''

        # Inventory grouped by instance IDs, tags, security groups, regions,
        # and availability zones
        self.inventory = self._empty_inventory()

        # Index of hostname (address) to instance ID
        self.index = {}

        # Read settings and parse CLI arguments
        self.read_settings()
        self.parse_cli_args()

        # Cache
        if self.args.refresh_cache:
            self.do_api_calls_update_cache()
        elif not self.is_cache_valid():
            self.do_api_calls_update_cache()

        # Data to print
        if self.args.host:
            data_to_print = self.get_host_info()

        elif self.args.list:
            # Display list of instances for inventory
            if self.inventory == self._empty_inventory():
                data_to_print = self.get_inventory_from_cache()
            else:
                data_to_print = self.json_format_dict(self.inventory, True)

        print data_to_print


    def is_cache_valid(self):
        ''' Determines if the cache files have expired, or if it is still valid '''

        if os.path.isfile(self.cache_path_cache):
            mod_time = os.path.getmtime(self.cache_path_cache)
            current_time = time()
            if (mod_time + self.cache_max_age) > current_time:
                if os.path.isfile(self.cache_path_index):
                    return True

        return False


    def read_settings(self):
        ''' Reads the settings from the ec2.ini file '''

        config = ConfigParser.SafeConfigParser()
        ec2_default_ini_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'ec2.ini')
        ec2_ini_path = os.environ.get('EC2_INI_PATH', ec2_default_ini_path)
        config.read(ec2_ini_path)

        # is eucalyptus?
        self.eucalyptus_host = None
        self.eucalyptus = False
        if config.has_option('ec2', 'eucalyptus'):
            self.eucalyptus = config.getboolean('ec2', 'eucalyptus')
        if self.eucalyptus and config.has_option('ec2', 'eucalyptus_host'):
            self.eucalyptus_host = config.get('ec2', 'eucalyptus_host')

        # Regions
        self.regions = []
        configRegions = config.get('ec2', 'regions')
        configRegions_exclude = config.get('ec2', 'regions_exclude')
        if (configRegions == 'all'):
            if self.eucalyptus_host:
                self.regions.append(boto.connect_euca(host=self.eucalyptus_host).region.name)
            else:
                for regionInfo in ec2.regions():
                    if regionInfo.name not in configRegions_exclude:
                        self.regions.append(regionInfo.name)
        else:
            self.regions = configRegions.split(",")

        # Destination addresses
        self.destination_variable = config.get('ec2', 'destination_variable')
        self.vpc_destination_variable = config.get('ec2', 'vpc_destination_variable')

        # Route53
        self.route53_enabled = config.getboolean('ec2', 'route53')
        self.route53_excluded_zones = []
        if config.has_option('ec2', 'route53_excluded_zones'):
            self.route53_excluded_zones.extend(
                config.get('ec2', 'route53_excluded_zones', '').split(','))

        # Cache related
        cache_dir = os.path.expanduser(config.get('ec2', 'cache_path'))
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)

        self.cache_path_cache = cache_dir + "/ansible-ec2.cache"
        self.cache_path_index = cache_dir + "/ansible-ec2.index"
        self.cache_max_age = config.getint('ec2', 'cache_max_age')
        


    def parse_cli_args(self):
        ''' Command line argument processing '''

        parser = argparse.ArgumentParser(description='Produce an Ansible Inventory file based on EC2')
        parser.add_argument('--list', action='store_true', default=True,
                           help='List instances (default: True)')
        parser.add_argument('--host', action='store',
                           help='Get all the variables about a specific instance')
        parser.add_argument('--refresh-cache', action='store_true', default=False,
                           help='Force refresh of cache by making API requests to EC2 (default: False - use cache files)')
        self.args = parser.parse_args()


    def do_api_calls_update_cache(self):
        ''' Do API calls to each region, and save data in cache files '''

        if self.route53_enabled:
            self.get_route53_records()

        for region in self.regions:
            self.get_instances_by_region(region)
            self.get_rds_instances_by_region(region)

        self.write_to_cache(self.inventory, self.cache_path_cache)
        self.write_to_cache(self.index, self.cache_path_index)


    def get_instances_by_region(self, region):
        ''' Makes an AWS EC2 API call to the list of instances in a particular
        region '''

        try:
            if self.eucalyptus:
                conn = boto.connect_euca(host=self.eucalyptus_host)
                conn.APIVersion = '2010-08-31'
            else:
                conn = ec2.connect_to_region(region)

            # connect_to_region will fail "silently" by returning None if the region name is wrong or not supported
            if conn is None:
                print("region name: %s likely not supported, or AWS is down.  connection to region failed." % region)
                sys.exit(1)
 
            reservations = conn.get_all_instances()
            for reservation in reservations:
                for instance in reservation.instances:
                    self.add_instance(instance, region)
        
        except boto.exception.BotoServerError, e:
            if  not self.eucalyptus:
                print "Looks like AWS is down again:"
            print e
            sys.exit(1)

    def get_rds_instances_by_region(self, region):
	''' Makes an AWS API call to the list of RDS instances in a particular
        region '''

        try:
            conn = rds.connect_to_region(region)
            if conn:
                instances = conn.get_all_dbinstances()
                for instance in instances:
                    self.add_rds_instance(instance, region)
        except boto.exception.BotoServerError, e:
            if not e.reason == "Forbidden":
                print "Looks like AWS RDS is down: "
                print e
                sys.exit(1)

    def get_instance(self, region, instance_id):
        ''' Gets details about a specific instance '''
        if self.eucalyptus:
            conn = boto.connect_euca(self.eucalyptus_host)
            conn.APIVersion = '2010-08-31'
        else:
            conn = ec2.connect_to_region(region)

        # connect_to_region will fail "silently" by returning None if the region name is wrong or not supported
        if conn is None:
            print("region name: %s likely not supported, or AWS is down.  connection to region failed." % region)
            sys.exit(1)

        reservations = conn.get_all_instances([instance_id])
        for reservation in reservations:
            for instance in reservation.instances:
                return instance


    def add_instance(self, instance, region):
        ''' Adds an instance to the inventory and index, as long as it is
        addressable '''

        # Only want running instances
        if instance.state != 'running':
            return

        # Select the best destination address
        if instance.subnet_id:
            dest = getattr(instance, self.vpc_destination_variable)
        else:
            dest =  getattr(instance, self.destination_variable)

        if not dest:
            # Skip instances we cannot address (e.g. private VPC subnet)
            return

        # Add to index
        self.index[dest] = [region, instance.id]

        # Inventory: Group by instance ID (always a group of 1)
        self.inventory[instance.id] = [dest]

        # Inventory: Group by region
        self.push(self.inventory, region, dest)

        # Inventory: Group by availability zone
        self.push(self.inventory, instance.placement, dest)

        # Inventory: Group by instance type
        self.push(self.inventory, self.to_safe('type_' + instance.instance_type), dest)

        # Inventory: Group by key pair
        if instance.key_name:
            self.push(self.inventory, self.to_safe('key_' + instance.key_name), dest)
        
        # Inventory: Group by security group
        try:
            for group in instance.groups:
                key = self.to_safe("security_group_" + group.name)
                self.push(self.inventory, key, dest)
        except AttributeError:
            print 'Package boto seems a bit older.'
            print 'Please upgrade boto >= 2.3.0.'
            sys.exit(1)

        # Inventory: Group by tag keys
        for k, v in instance.tags.iteritems():
            key = self.to_safe("tag_" + k + "=" + v)
            self.push(self.inventory, key, dest)

        # Inventory: Group by Route53 domain names if enabled
        if self.route53_enabled:
            route53_names = self.get_instance_route53_names(instance)
            for name in route53_names:
                self.push(self.inventory, name, dest)

        # Global Tag: tag all EC2 instances
        self.push(self.inventory, 'ec2', dest)

        self.inventory["_meta"]["hostvars"][dest] = self.get_host_info_dict_from_instance(instance)


    def add_rds_instance(self, instance, region):
        ''' Adds an RDS instance to the inventory and index, as long as it is
        addressable '''

        # Only want available instances
        if instance.status != 'available':
            return

        # Select the best destination address
        #if instance.subnet_id:
            #dest = getattr(instance, self.vpc_destination_variable)
        #else:
            #dest =  getattr(instance, self.destination_variable)
        dest = instance.endpoint[0]

        if not dest:
            # Skip instances we cannot address (e.g. private VPC subnet)
            return

        # Add to index
        self.index[dest] = [region, instance.id]

        # Inventory: Group by instance ID (always a group of 1)
        self.inventory[instance.id] = [dest]

        # Inventory: Group by region
        self.push(self.inventory, region, dest)

        # Inventory: Group by availability zone
        self.push(self.inventory, instance.availability_zone, dest)
        
        # Inventory: Group by instance type
        self.push(self.inventory, self.to_safe('type_' + instance.instance_class), dest)
        
        # Inventory: Group by security group
        try:
            if instance.security_group:
                key = self.to_safe("security_group_" + instance.security_group.name)
                self.push(self.inventory, key, dest)
        except AttributeError:
            print 'Package boto seems a bit older.'
            print 'Please upgrade boto >= 2.3.0.'
            sys.exit(1)

        # Inventory: Group by engine
        self.push(self.inventory, self.to_safe("rds_" + instance.engine), dest)

        # Inventory: Group by parameter group
        self.push(self.inventory, self.to_safe("rds_parameter_group_" + instance.parameter_group.name), dest)

        # Global Tag: all RDS instances
        self.push(self.inventory, 'rds', dest)


    def get_route53_records(self):
        ''' Get and store the map of resource records to domain names that
        point to them. '''

        r53_conn = route53.Route53Connection()
        all_zones = r53_conn.get_zones()

        route53_zones = [ zone for zone in all_zones if zone.name[:-1]
                          not in self.route53_excluded_zones ]

        self.route53_records = {}

        for zone in route53_zones:
            rrsets = r53_conn.get_all_rrsets(zone.id)

            for record_set in rrsets:
                record_name = record_set.name

                if record_name.endswith('.'):
                    record_name = record_name[:-1]

                for resource in record_set.resource_records:
                    self.route53_records.setdefault(resource, set())
                    self.route53_records[resource].add(record_name)


    def get_instance_route53_names(self, instance):
        ''' Check if an instance is referenced in the records we have from
        Route53. If it is, return the list of domain names pointing to said
        instance. If nothing points to it, return an empty list. '''

        instance_attributes = [ 'public_dns_name', 'private_dns_name',
                                'ip_address', 'private_ip_address' ]

        name_list = set()

        for attrib in instance_attributes:
            try:
                value = getattr(instance, attrib)
            except AttributeError:
                continue

            if value in self.route53_records:
                name_list.update(self.route53_records[value])

        return list(name_list)


    def get_host_info_dict_from_instance(self, instance):
        instance_vars = {}
        for key in vars(instance):
            value = getattr(instance, key)
            key = self.to_safe('ec2_' + key)

            # Handle complex types
            # state/previous_state changed to properties in boto in https://github.com/boto/boto/commit/a23c379837f698212252720d2af8dec0325c9518
            if key == 'ec2__state':
                instance_vars['ec2_state'] = instance.state or ''
                instance_vars['ec2_state_code'] = instance.state_code
            elif key == 'ec2__previous_state':
                instance_vars['ec2_previous_state'] = instance.previous_state or ''
                instance_vars['ec2_previous_state_code'] = instance.previous_state_code
            elif type(value) in [int, bool]:
                instance_vars[key] = value
            elif type(value) in [str, unicode]:
                instance_vars[key] = value.strip()
            elif type(value) == type(None):
                instance_vars[key] = ''
            elif key == 'ec2_region':
                instance_vars[key] = value.name
            elif key == 'ec2__placement':
                instance_vars['ec2_placement'] = value.zone
            elif key == 'ec2_tags':
                for k, v in value.iteritems():
                    key = self.to_safe('ec2_tag_' + k)
                    instance_vars[key] = v
            elif key == 'ec2_groups':
                group_ids = []
                group_names = []
                for group in value:
                    group_ids.append(group.id)
                    group_names.append(group.name)
                instance_vars["ec2_security_group_ids"] = ','.join(group_ids)
                instance_vars["ec2_security_group_names"] = ','.join(group_names)
            else:
                pass
                # TODO Product codes if someone finds them useful
                #print key
                #print type(value)
                #print value

        return instance_vars

    def get_host_info(self):
        ''' Get variables about a specific host '''

        if len(self.index) == 0:
            # Need to load index from cache
            self.load_index_from_cache()

        if not self.args.host in self.index:
            # try updating the cache
            self.do_api_calls_update_cache()
            if not self.args.host in self.index:
                # host migh not exist anymore
                return self.json_format_dict({}, True)

        (region, instance_id) = self.index[self.args.host]

        instance = self.get_instance(region, instance_id)
        return self.json_format_dict(self.get_host_info_dict_from_instance(instance), True)

    def push(self, my_dict, key, element):
        ''' Pushed an element onto an array that may not have been defined in
        the dict '''

        if key in my_dict:
            my_dict[key].append(element);
        else:
            my_dict[key] = [element]


    def get_inventory_from_cache(self):
        ''' Reads the inventory from the cache file and returns it as a JSON
        object '''

        cache = open(self.cache_path_cache, 'r')
        json_inventory = cache.read()
        return json_inventory


    def load_index_from_cache(self):
        ''' Reads the index from the cache file sets self.index '''

        cache = open(self.cache_path_index, 'r')
        json_index = cache.read()
        self.index = json.loads(json_index)


    def write_to_cache(self, data, filename):
        ''' Writes data in JSON format to a file '''

        json_data = self.json_format_dict(data, True)
        cache = open(filename, 'w')
        cache.write(json_data)
        cache.close()


    def to_safe(self, word):
        ''' Converts 'bad' characters in a string to underscores so they can be
        used as Ansible groups '''

        return re.sub("[^A-Za-z0-9\-]", "_", word)


    def json_format_dict(self, data, pretty=False):
        ''' Converts a dict to a JSON object and dumps it as a formatted
        string '''

        if pretty:
            return json.dumps(data, sort_keys=True, indent=2)
        else:
            return json.dumps(data)


# Run the script
Ec2Inventory()


########NEW FILE########
__FILENAME__ = gce
#!/usr/bin/python
# Copyright 2013 Google Inc.
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

'''
GCE external inventory script
=================================

Generates inventory that Ansible can understand by making API requests
Google Compute Engine via the libcloud library.  Full install/configuration
instructions for the gce* modules can be found in the comments of
ansible/test/gce_tests.py.

When run against a specific host, this script returns the following variables
based on the data obtained from the libcloud Node object:
 - gce_uuid
 - gce_id
 - gce_image
 - gce_machine_type
 - gce_private_ip
 - gce_public_ip
 - gce_name
 - gce_description
 - gce_status
 - gce_zone
 - gce_tags
 - gce_metadata
 - gce_network

When run in --list mode, instances are grouped by the following categories:
 - zone:
   zone group name examples are us-central1-b, europe-west1-a, etc.
 - instance tags:
   An entry is created for each tag.  For example, if you have two instances
   with a common tag called 'foo', they will both be grouped together under
   the 'tag_foo' name.
 - network name:
   the name of the network is appended to 'network_' (e.g. the 'default'
   network will result in a group named 'network_default')
 - machine type
   types follow a pattern like n1-standard-4, g1-small, etc.
 - running status:
   group name prefixed with 'status_' (e.g. status_running, status_stopped,..)
 - image:
   when using an ephemeral/scratch disk, this will be set to the image name
   used when creating the instance (e.g. debian-7-wheezy-v20130816).  when
   your instance was created with a root persistent disk it will be set to
   'persistent_disk' since there is no current way to determine the image.

Examples:
  Execute uname on all instances in the us-central1-a zone
  $ ansible -i gce.py us-central1-a -m shell -a "/bin/uname -a"

  Use the GCE inventory script to print out instance specific information
  $ plugins/inventory/gce.py --host my_instance

Author: Eric Johnson <erjohnso@google.com>
Version: 0.0.1
'''

USER_AGENT_PRODUCT="Ansible-gce_inventory_plugin"
USER_AGENT_VERSION="v1"

import sys
import os
import argparse
import ConfigParser

try:
    import json
except ImportError:
    import simplejson as json

try:
    from libcloud.compute.types import Provider
    from libcloud.compute.providers import get_driver
    _ = Provider.GCE
except:
    print("GCE inventory script requires libcloud >= 0.13")
    sys.exit(1)


class GceInventory(object):
    def __init__(self):
        # Read settings and parse CLI arguments
        self.parse_cli_args()
        self.driver = self.get_gce_driver()

        # Just display data for specific host
        if self.args.host:
            print self.json_format_dict(self.node_to_dict(
                    self.get_instance(self.args.host)))
            sys.exit(0)

        # Otherwise, assume user wants all instances grouped
        print self.json_format_dict(self.group_instances())
        sys.exit(0)


    def get_gce_driver(self):
        '''Determine GCE authorization settings and return libcloud driver.'''

        gce_ini_default_path = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), "gce.ini")
        gce_ini_path = os.environ.get('GCE_INI_PATH', gce_ini_default_path)

        config = ConfigParser.SafeConfigParser()
        config.read(gce_ini_path)

        # the GCE params in 'secrets.py' will override these
        secrets_path = config.get('gce', 'libcloud_secrets')

        secrets_found = False
        try:
            import secrets
            args = getattr(secrets, 'GCE_PARAMS', ())
            kwargs = getattr(secrets, 'GCE_KEYWORD_PARAMS', {})
            secrets_found = True
        except:
            pass

        if not secrets_found and secrets_path:
            if not secrets_path.endswith('secrets.py'):
                err = "Must specify libcloud secrets file as "
                err += "/absolute/path/to/secrets.py"
                print(err)
                sys.exit(1)
            sys.path.append(os.path.dirname(secrets_path))
            try:
                import secrets
                args = getattr(secrets, 'GCE_PARAMS', ())
                kwargs = getattr(secrets, 'GCE_KEYWORD_PARAMS', {})
                secrets_found = True
            except:
                pass
        if not secrets_found:
            args = (
                config.get('gce','gce_service_account_email_address'),
                config.get('gce','gce_service_account_pem_file_path')
            )
            kwargs = {'project': config.get('gce','gce_project_id')}

        gce = get_driver(Provider.GCE)(*args, **kwargs)
        gce.connection.user_agent_append("%s/%s" % (
                USER_AGENT_PRODUCT, USER_AGENT_VERSION))
        return gce


    def parse_cli_args(self):
        ''' Command line argument processing '''

        parser = argparse.ArgumentParser(
                description='Produce an Ansible Inventory file based on GCE')
        parser.add_argument('--list', action='store_true', default=True,
                           help='List instances (default: True)')
        parser.add_argument('--host', action='store',
                           help='Get all information about an instance')
        self.args = parser.parse_args()


    def node_to_dict(self, inst):
        md = {}

        if inst is None:
            return {}

        if inst.extra['metadata'].has_key('items'):
            for entry in inst.extra['metadata']['items']:
                md[entry['key']] = entry['value']

        net = inst.extra['networkInterfaces'][0]['network'].split('/')[-1]
        return {
            'gce_uuid': inst.uuid,
            'gce_id': inst.id,
            'gce_image': inst.image,
            'gce_machine_type': inst.size,
            'gce_private_ip': inst.private_ips[0],
            'gce_public_ip': inst.public_ips[0],
            'gce_name': inst.name,
            'gce_description': inst.extra['description'],
            'gce_status': inst.extra['status'],
            'gce_zone': inst.extra['zone'].name,
            'gce_tags': inst.extra['tags'],
            'gce_metadata': md,
            'gce_network': net,
            # Hosts don't have a public name, so we add an IP
            'ansible_ssh_host': inst.public_ips[0]
        }

    def get_instance(self, instance_name):
        '''Gets details about a specific instance '''
        try:
            return self.driver.ex_get_node(instance_name)
        except Exception, e:
            return None

    def group_instances(self):
        '''Group all instances'''
        groups = {}
        for node in self.driver.list_nodes():
            name = node.name

            zone = node.extra['zone'].name
            if groups.has_key(zone): groups[zone].append(name)
            else: groups[zone] = [name]

            tags = node.extra['tags']
            for t in tags:
                tag = 'tag_%s' % t
                if groups.has_key(tag): groups[tag].append(name)
                else: groups[tag] = [name]

            net = node.extra['networkInterfaces'][0]['network'].split('/')[-1]
            net = 'network_%s' % net
            if groups.has_key(net): groups[net].append(name)
            else: groups[net] = [name]

            machine_type = node.size
            if groups.has_key(machine_type): groups[machine_type].append(name)
            else: groups[machine_type] = [name]

            image = node.image and node.image or 'persistent_disk'
            if groups.has_key(image): groups[image].append(name)
            else: groups[image] = [name]

            status = node.extra['status']
            stat = 'status_%s' % status.lower()
            if groups.has_key(stat): groups[stat].append(name)
            else: groups[stat] = [name]
        return groups

    def json_format_dict(self, data, pretty=False):
        ''' Converts a dict to a JSON object and dumps it as a formatted
        string '''

        if pretty:
            return json.dumps(data, sort_keys=True, indent=2)
        else:
            return json.dumps(data)


# Run the script
GceInventory()

########NEW FILE########
__FILENAME__ = jail
#!/usr/bin/env python

# (c) 2013, Michael Scherer <misc@zarb.org>
#
# This file is part of Ansible,
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

from subprocess import Popen,PIPE
import sys
import json

result = {}
result['all'] = {}

pipe = Popen(['jls', '-q', 'name'], stdout=PIPE, universal_newlines=True)
result['all']['hosts'] = [x[:-1] for x in pipe.stdout.readlines()]
result['all']['vars'] = {}
result['all']['vars']['ansible_connection'] = 'jail'

if len(sys.argv) == 2 and sys.argv[1] == '--list':
    print json.dumps(result)
elif len(sys.argv) == 3 and sys.argv[1] == '--host':
    print json.dumps({'ansible_connection': 'jail'})
else:
    print "Need a argument, either --list or --host <host>"

########NEW FILE########
__FILENAME__ = libvirt_lxc
#!/usr/bin/env python

# (c) 2013, Michael Scherer <misc@zarb.org>
#
# This file is part of Ansible,
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

from subprocess import Popen,PIPE
import sys
import json

result = {}
result['all'] = {}

pipe = Popen(['virsh', '-q', '-c', 'lxc:///', 'list', '--name', '--all'], stdout=PIPE, universal_newlines=True)
result['all']['hosts'] = [x[:-1] for x in pipe.stdout.readlines()]
result['all']['vars'] = {}
result['all']['vars']['ansible_connection'] = 'lxc'

if len(sys.argv) == 2 and sys.argv[1] == '--list':
    print json.dumps(result)
elif len(sys.argv) == 3 and sys.argv[1] == '--host':
    print json.dumps({'ansible_connection': 'lxc'})
else:
    print "Need a argument, either --list or --host <host>"

########NEW FILE########
__FILENAME__ = linode
#!/usr/bin/env python

'''
Linode external inventory script
=================================

Generates inventory that Ansible can understand by making API request to
Linode using the Chube library.

NOTE: This script assumes Ansible is being executed where Chube is already
installed and has a valid config at ~/.chube. If not, run:

    pip install chube
    echo -e "---\napi_key: <YOUR API KEY GOES HERE>" > ~/.chube

For more details, see: https://github.com/exosite/chube

NOTE: This script also assumes that the Linodes in your account all have
labels that correspond to hostnames that are in your resolver search path.
Your resolver search path resides in /etc/hosts.

When run against a specific host, this script returns the following variables:

    - api_id
    - datacenter_id
    - datacenter_city (lowercase city name of data center, e.g. 'tokyo')
    - label
    - display_group
    - create_dt
    - total_hd
    - total_xfer
    - total_ram
    - status
    - public_ip (The first public IP found)
    - private_ip (The first private IP found, or empty string if none)
    - alert_cpu_enabled
    - alert_cpu_threshold
    - alert_diskio_enabled
    - alert_diskio_threshold
    - alert_bwin_enabled
    - alert_bwin_threshold
    - alert_bwout_enabled
    - alert_bwout_threshold
    - alert_bwquota_enabled
    - alert_bwquota_threshold
    - backup_weekly_daily
    - backup_window
    - watchdog

Peter Sankauskas did most of the legwork here with his linode plugin; I
just adapted that for Linode.
'''

# (c) 2013, Dan Slimmon
#
# This file is part of Ansible,
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

######################################################################

# Standard imports
import os
import re
import sys
import argparse
from time import time

try:
    import json
except ImportError:
    import simplejson as json

try:
    from chube import load_chube_config
    from chube import api as chube_api
    from chube.datacenter import Datacenter
    from chube.linode_obj import Linode
except:
    try:
        # remove local paths and other stuff that may
        # cause an import conflict, as chube is sensitive
        # to name collisions on importing
        old_path = sys.path
        sys.path = [d for d in sys.path if d not in ('', os.getcwd(), os.path.dirname(os.path.realpath(__file__)))]

        from chube import load_chube_config
        from chube import api as chube_api
        from chube.datacenter import Datacenter
        from chube.linode_obj import Linode

        sys.path = old_path
    except Exception, e:
        raise Exception("could not import chube")

load_chube_config()

# Imports for ansible
import ConfigParser

class LinodeInventory(object):
    def __init__(self):
        """Main execution path."""
        # Inventory grouped by display group
        self.inventory = {}
        # Index of label to Linode ID
        self.index = {}
        # Local cache of Datacenter objects populated by populate_datacenter_cache()
        self._datacenter_cache = None

        # Read settings and parse CLI arguments
        self.read_settings()
        self.parse_cli_args()

        # Cache
        if self.args.refresh_cache:
            self.do_api_calls_update_cache()
        elif not self.is_cache_valid():
            self.do_api_calls_update_cache()

        # Data to print
        if self.args.host:
            data_to_print = self.get_host_info()
        elif self.args.list:
            # Display list of nodes for inventory
            if len(self.inventory) == 0:
                data_to_print = self.get_inventory_from_cache()
            else:
                data_to_print = self.json_format_dict(self.inventory, True)

        print data_to_print

    def is_cache_valid(self):
        """Determines if the cache file has expired, or if it is still valid."""
        if os.path.isfile(self.cache_path_cache):
            mod_time = os.path.getmtime(self.cache_path_cache)
            current_time = time()
            if (mod_time + self.cache_max_age) > current_time:
                if os.path.isfile(self.cache_path_index):
                    return True
        return False

    def read_settings(self):
        """Reads the settings from the .ini file."""
        config = ConfigParser.SafeConfigParser()
        config.read(os.path.dirname(os.path.realpath(__file__)) + '/linode.ini')

        # Cache related
        cache_path = config.get('linode', 'cache_path')
        self.cache_path_cache = cache_path + "/ansible-linode.cache"
        self.cache_path_index = cache_path + "/ansible-linode.index"
        self.cache_max_age = config.getint('linode', 'cache_max_age')

    def parse_cli_args(self):
        """Command line argument processing"""
        parser = argparse.ArgumentParser(description='Produce an Ansible Inventory file based on Linode')
        parser.add_argument('--list', action='store_true', default=True,
                           help='List nodes (default: True)')
        parser.add_argument('--host', action='store',
                           help='Get all the variables about a specific node')
        parser.add_argument('--refresh-cache', action='store_true', default=False,
                           help='Force refresh of cache by making API requests to Linode (default: False - use cache files)')
        self.args = parser.parse_args()

    def do_api_calls_update_cache(self):
        """Do API calls, and save data in cache files."""
        self.get_nodes()
        self.write_to_cache(self.inventory, self.cache_path_cache)
        self.write_to_cache(self.index, self.cache_path_index)

    def get_nodes(self):
        """Makes an Linode API call to get the list of nodes."""
        try:
            for node in Linode.search(status=Linode.STATUS_RUNNING):
                self.add_node(node)
        except chube_api.linode_api.ApiError, e:
            print "Looks like Linode's API is down:"
            print
            print e
            sys.exit(1)

    def get_node(self, linode_id):
        """Gets details about a specific node."""
        try:
            return Linode.find(api_id=linode_id)
        except chube_api.linode_api.ApiError, e:
            print "Looks like Linode's API is down:"
            print
            print e
            sys.exit(1)

    def populate_datacenter_cache(self):
        """Creates self._datacenter_cache, containing all Datacenters indexed by ID."""
        self._datacenter_cache = {}
        dcs = Datacenter.search()
        for dc in dcs:
            self._datacenter_cache[dc.api_id] = dc

    def get_datacenter_city(self, node):
        """Returns a the lowercase city name of the node's data center."""
        if self._datacenter_cache is None:
            self.populate_datacenter_cache()
        location = self._datacenter_cache[node.datacenter_id].location
        location = location.lower()
        location = location.split(",")[0]
        return location

    def add_node(self, node):
        """Adds an node to the inventory and index."""

        dest = node.label

        # Add to index
        self.index[dest] = node.api_id

        # Inventory: Group by node ID (always a group of 1)
        self.inventory[node.api_id] = [dest]

        # Inventory: Group by datacenter city
        self.push(self.inventory, self.get_datacenter_city(node), dest)

        # Inventory: Group by dipslay group
        self.push(self.inventory, node.display_group, dest)

    def get_host_info(self):
        """Get variables about a specific host."""

        if len(self.index) == 0:
            # Need to load index from cache
            self.load_index_from_cache()

        if not self.args.host in self.index:
            # try updating the cache
            self.do_api_calls_update_cache()
            if not self.args.host in self.index:
                # host might not exist anymore
                return self.json_format_dict({}, True)

        node_id = self.index[self.args.host]

        node = self.get_node(node_id)
        node_vars = {}
        for direct_attr in [
            "api_id",
            "datacenter_id",
            "label",
            "display_group",
            "create_dt",
            "total_hd",
            "total_xfer",
            "total_ram",
            "status",
            "alert_cpu_enabled",
            "alert_cpu_threshold",
            "alert_diskio_enabled",
            "alert_diskio_threshold",
            "alert_bwin_enabled",
            "alert_bwin_threshold",
            "alert_bwout_enabled",
            "alert_bwout_threshold",
            "alert_bwquota_enabled",
            "alert_bwquota_threshold",
            "backup_weekly_daily",
            "backup_window",
            "watchdog"
        ]:
            node_vars[direct_attr] = getattr(node, direct_attr)

        node_vars["datacenter_city"] = self.get_datacenter_city(node)
        node_vars["public_ip"] = [addr.address for addr in node.ipaddresses if addr.is_public][0]

        private_ips = [addr.address for addr in node.ipaddresses if not addr.is_public]

        if private_ips:
            node_vars["private_ip"] = private_ips[0]

        return self.json_format_dict(node_vars, True)

    def push(self, my_dict, key, element):
        """Pushed an element onto an array that may not have been defined in the dict."""
        if key in my_dict:
            my_dict[key].append(element);
        else:
            my_dict[key] = [element]

    def get_inventory_from_cache(self):
        """Reads the inventory from the cache file and returns it as a JSON object."""
        cache = open(self.cache_path_cache, 'r')
        json_inventory = cache.read()
        return json_inventory

    def load_index_from_cache(self):
        """Reads the index from the cache file and sets self.index."""
        cache = open(self.cache_path_index, 'r')
        json_index = cache.read()
        self.index = json.loads(json_index)

    def write_to_cache(self, data, filename):
        """Writes data in JSON format to a file."""
        json_data = self.json_format_dict(data, True)
        cache = open(filename, 'w')
        cache.write(json_data)
        cache.close()

    def to_safe(self, word):
        """Escapes any characters that would be invalid in an ansible group name."""
        return re.sub("[^A-Za-z0-9\-]", "_", word)

    def json_format_dict(self, data, pretty=False):
        """Converts a dict to a JSON object and dumps it as a formatted string."""
        if pretty:
            return json.dumps(data, sort_keys=True, indent=2)
        else:
            return json.dumps(data)


LinodeInventory()

########NEW FILE########
__FILENAME__ = nova
#!/usr/bin/env python

# (c) 2012, Marco Vito Moscaritolo <marco@agavee.com>
#
# This file is part of Ansible,
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

DOCUMENTATION = '''
---
inventory: nova
short_description: OpenStack external inventory script
description:
  - Generates inventory that Ansible can understand by making API request to OpenStack endpoint using the novaclient library.
  - |
    When run against a specific host, this script returns the following variables:
        os_os-ext-sts_task_state
        os_addresses
        os_links
        os_image
        os_os-ext-sts_vm_state
        os_flavor
        os_id
        os_rax-bandwidth_bandwidth
        os_user_id
        os_os-dcf_diskconfig
        os_accessipv4
        os_accessipv6
        os_progress
        os_os-ext-sts_power_state
        os_metadata
        os_status
        os_updated
        os_hostid
        os_name
        os_created
        os_tenant_id
        os__info
        os__loaded

    where some item can have nested structure.
  - All information are set on B(nova.ini) file
version_added: None
options:
  version:
    description:
      - OpenStack version to use.
    required: true
    default: null
    choices: [ "1.1", "2" ]
  username:
    description:
      - Username used to authenticate in OpenStack.
    required: true
    default: null
  api_key:
    description:
      - Password used to authenticate in OpenStack, can be the ApiKey on some authentication system.
    required: true
    default: null
  auth_url:
    description:
      - Authentication URL required to generate token.
      - To manage RackSpace use I(https://identity.api.rackspacecloud.com/v2.0/)
    required: true
    default: null
  auth_system:
    description:
      - Authentication system used to login
      - To manage RackSpace install B(rackspace-novaclient) and insert I(rackspace)
    required: true
    default: null
  region_name:
    description:
      - Region name to use in request
      - In RackSpace some value can be I(ORD) or I(DWF).
    required: true
    default: null
  project_id:
    description:
      - Project ID to use in connection
      - In RackSpace use OS_TENANT_NAME
    required: false
    default: null
  endpoint_type:
    description:
      - The endpoint type for novaclient
      - In RackSpace use 'publicUrl'
    required: false
    default: null
  service_type:
    description:
      - The service type you are managing.
      - In RackSpace use 'compute'
    required: false
    default: null
  service_name:
    description:
      - The service name you are managing.
      - In RackSpace use 'cloudServersOpenStack'
    required: false
    default: null
  insicure:
    description:
      - To no check security
    required: false
    default: false
    choices: [ "true", "false" ]
author: Marco Vito Moscaritolo
notes:
  - This script assumes Ansible is being executed where the environment variables needed for novaclient have already been set on nova.ini file
  - For more details, see U(https://github.com/openstack/python-novaclient)
examples:
    - description: List instances
      code: nova.py --list
    - description: Instance property
      code: nova.py --instance INSTANCE_IP
'''


import sys
import re
import os
import ConfigParser
from novaclient import client as nova_client

try:
    import json
except:
    import simplejson as json

###################################################
# executed with no parameters, return the list of
# all groups and hosts

def nova_load_config_file():
    p = ConfigParser.SafeConfigParser()
    path1 = os.getcwd() + "/nova.ini"
    path2 = os.path.expanduser(os.environ.get('ANSIBLE_CONFIG', "~/nova.ini"))
    path3 = "/etc/ansible/nova.ini"

    if os.path.exists(path1):
        p.read(path1)
    elif os.path.exists(path2):
        p.read(path2)
    elif os.path.exists(path3):
        p.read(path3)
    else:
        return None
    return p

config = nova_load_config_file()

client = nova_client.Client(
    version     = config.get('openstack', 'version'),
    username    = config.get('openstack', 'username'),
    api_key     = config.get('openstack', 'api_key'),
    auth_url    = config.get('openstack', 'auth_url'),
    region_name = config.get('openstack', 'region_name'),
    project_id  = config.get('openstack', 'project_id'),
    auth_system = config.get('openstack', 'auth_system')
)

if len(sys.argv) == 2 and (sys.argv[1] == '--list'):
    groups = {}

    # Cycle on servers
    for f in client.servers.list():
	private = [ x['addr'] for x in getattr(f, 'addresses').itervalues().next() if x['OS-EXT-IPS:type'] == 'fixed']
	public  = [ x['addr'] for x in getattr(f, 'addresses').itervalues().next() if x['OS-EXT-IPS:type'] == 'floating']
	    
	# Define group (or set to empty string)
        group = f.metadata['group'] if f.metadata.has_key('group') else 'undefined'

        # Create group if not exist
        if group not in groups:
            groups[group] = []

        # Append group to list
	if f.accessIPv4:
        	groups[group].append(f.accessIPv4)
		continue
	if public:
        	groups[group].append(''.join(public))
		continue
	if private:
        	groups[group].append(''.join(private))
		continue

    # Return server list
    print json.dumps(groups)
    sys.exit(0)

#####################################################
# executed with a hostname as a parameter, return the
# variables for that host

elif len(sys.argv) == 3 and (sys.argv[1] == '--host'):
    results = {}
    ips = []
    for instance in client.servers.list():
	private = [ x['addr'] for x in getattr(instance, 'addresses').itervalues().next() if x['OS-EXT-IPS:type'] == 'fixed']
	public =  [ x['addr'] for x in getattr(instance, 'addresses').itervalues().next() if x['OS-EXT-IPS:type'] == 'floating']
        ips.append( instance.accessIPv4)
	ips.append(''.join(private))
	ips.append(''.join(public))
	if sys.argv[2] in ips:
            for key in vars(instance):
                # Extract value
                value = getattr(instance, key)

                # Generate sanitized key
                key = 'os_' + re.sub("[^A-Za-z0-9\-]", "_", key).lower()

                # Att value to instance result (exclude manager class)
                #TODO: maybe use value.__class__ or similar inside of key_name
                if key != 'os_manager':
                    results[key] = value

    print json.dumps(results)
    sys.exit(0)

else:
    print "usage: --list  ..OR.. --host <hostname>"
    sys.exit(1)

########NEW FILE########
__FILENAME__ = openshift
#!/usr/bin/env python

# (c) 2013, Michael Scherer <misc@zarb.org>
#
# This file is part of Ansible,
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

DOCUMENTATION = '''
---
inventory: openshift
short_description: Openshift gears external inventory script
description:
  - Generates inventory of Openshift gears using the REST interface
  - this permit to reuse playbook to setup a Openshift gear
version_added: None
author: Michael Scherer
'''

import urllib2
try:
    import json
except ImportError:
    import simplejson as json
import os
import os.path
import sys
import ConfigParser
import StringIO

configparser = None


def get_from_rhc_config(variable):
    global configparser
    CONF_FILE = os.path.expanduser('~/.openshift/express.conf')
    if os.path.exists(CONF_FILE):
        if not configparser:
            ini_str = '[root]\n' + open(CONF_FILE, 'r').read()
            configparser = ConfigParser.SafeConfigParser()
            configparser.readfp(StringIO.StringIO(ini_str))
        try:
            return configparser.get('root', variable)
        except ConfigParser.NoOptionError:
            return None


def get_config(env_var, config_var):
    result = os.getenv(env_var)
    if not result:
        result = get_from_rhc_config(config_var)
    if not result:
        print "failed=True msg='missing %s'" % env_var
        sys.exit(1)
    return result


def get_json_from_api(url):
    req = urllib2.Request(url, None, {'Accept': 'application/json; version=1.5'})
    response = urllib2.urlopen(req)
    return json.loads(response.read())['data']


def passwd_setup(top_level_url, username, password):
    # create a password manager
    password_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
    password_mgr.add_password(None, top_level_url, username, password)

    handler = urllib2.HTTPBasicAuthHandler(password_mgr)
    opener = urllib2.build_opener(handler)

    urllib2.install_opener(opener)


username = get_config('ANSIBLE_OPENSHIFT_USERNAME', 'default_rhlogin')
password = get_config('ANSIBLE_OPENSHIFT_PASSWORD', 'password')
broker_url = 'https://%s/broker/rest/' % get_config('ANSIBLE_OPENSHIFT_BROKER', 'libra_server')


passwd_setup(broker_url, username, password)

response = get_json_from_api(broker_url + '/domains')

response = get_json_from_api("%s/domains/%s/applications" %
                             (broker_url, response[0]['id']))

result = {}
for app in response:

    # ssh://520311404832ce3e570000ff@blog-johndoe.example.org
    (user, host) = app['ssh_url'][6:].split('@')
    app_name = host.split('-')[0]

    result[app_name] = {}
    result[app_name]['hosts'] = []
    result[app_name]['hosts'].append(host)
    result[app_name]['vars'] = {}
    result[app_name]['vars']['ansible_ssh_user'] = user

if len(sys.argv) == 2 and sys.argv[1] == '--list':
    print json.dumps(result)
elif len(sys.argv) == 3 and sys.argv[1] == '--host':
    print json.dumps({})
else:
    print "Need a argument, either --list or --host <host>"

########NEW FILE########
__FILENAME__ = rax
#!/usr/bin/env python

# (c) 2013, Jesse Keating <jesse.keating@rackspace.com>
#
# This file is part of Ansible,
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

DOCUMENTATION = '''
---
inventory: rax
short_description: Rackspace Public Cloud external inventory script
description:
  - Generates inventory that Ansible can understand by making API request to
    Rackspace Public Cloud API
  - |
    When run against a specific host, this script returns the following
    variables:
        rax_os-ext-sts_task_state
        rax_addresses
        rax_links
        rax_image
        rax_os-ext-sts_vm_state
        rax_flavor
        rax_id
        rax_rax-bandwidth_bandwidth
        rax_user_id
        rax_os-dcf_diskconfig
        rax_accessipv4
        rax_accessipv6
        rax_progress
        rax_os-ext-sts_power_state
        rax_metadata
        rax_status
        rax_updated
        rax_hostid
        rax_name
        rax_created
        rax_tenant_id
        rax_loaded

    where some item can have nested structure.
  - credentials are set in a credentials file
version_added: None
options:
  creds_file:
    description:
     - File to find the Rackspace Public Cloud credentials in
    required: true
    default: null
  region:
    description:
     - An optional value to narrow inventory scope, i.e. DFW, ORD, IAD, LON
     required: false
     default: null
authors:
  - Jesse Keating <jesse.keating@rackspace.com>
  - Paul Durivage <paul.durivage@rackspace.com>
  - Matt Martz <matt@sivel.net>
notes:
  - RAX_CREDS_FILE is an optional environment variable that points to a
    pyrax-compatible credentials file.
  - If RAX_CREDS_FILE is not supplied, rax.py will look for a credentials file
    at ~/.rackspace_cloud_credentials.
  - See https://github.com/rackspace/pyrax/blob/master/docs/getting_started.md#authenticating
  - RAX_REGION is an optional environment variable to narrow inventory search
    scope
  - RAX_REGION, if used, needs a value like ORD, DFW, SYD (a Rackspace
    datacenter) and optionally accepts a comma-separated list
  - RAX_ENV is an environment variable that will use an environment as
    configured in ~/.pyrax.cfg, see
    https://github.com/rackspace/pyrax/blob/master/docs/getting_started.md#pyrax-configuration
  - RAX_META_PREFIX is an environment variable that changes the prefix used
    for meta key/value groups. For compatibility with ec2.py set to
    RAX_META_PREFIX=tag
requirements: [ "pyrax" ]
examples:
    - description: List server instances
      code: RAX_CREDS_FILE=~/.raxpub rax.py --list
    - description: List servers in ORD datacenter only
      code: RAX_CREDS_FILE=~/.raxpub RAX_REGION=ORD rax.py --list
    - description: List servers in ORD and DFW datacenters
      code: RAX_CREDS_FILE=~/.raxpub RAX_REGION=ORD,DFW rax.py --list
    - description: Get server details for server named "server.example.com"
      code: RAX_CREDS_FILE=~/.raxpub rax.py --host server.example.com
'''

import os
import re
import sys
import argparse
import collections

from types import NoneType

try:
    import json
except:
    import simplejson as json

try:
    import pyrax
except ImportError:
    print('pyrax is required for this module')
    sys.exit(1)

NON_CALLABLES = (basestring, bool, dict, int, list, NoneType)


def rax_slugify(value):
    return 'rax_%s' % (re.sub('[^\w-]', '_', value).lower().lstrip('_'))


def to_dict(obj):
    instance = {}
    for key in dir(obj):
        value = getattr(obj, key)
        if (isinstance(value, NON_CALLABLES) and not key.startswith('_')):
            key = rax_slugify(key)
            instance[key] = value

    return instance


def host(regions, hostname):
    hostvars = {}

    for region in regions:
        # Connect to the region
        cs = pyrax.connect_to_cloudservers(region=region)
        for server in cs.servers.list():
            if server.name == hostname:
                for key, value in to_dict(server).items():
                    hostvars[key] = value

                # And finally, add an IP address
                hostvars['ansible_ssh_host'] = server.accessIPv4
    print(json.dumps(hostvars, sort_keys=True, indent=4))


def _list(regions):
    groups = collections.defaultdict(list)
    hostvars = collections.defaultdict(dict)
    images = {}

    # Go through all the regions looking for servers
    for region in regions:
        # Connect to the region
        cs = pyrax.connect_to_cloudservers(region=region)
        for server in cs.servers.list():
            # Create a group on region
            groups[region].append(server.name)

            # Check if group metadata key in servers' metadata
            group = server.metadata.get('group')
            if group:
                groups[group].append(server.name)

            for extra_group in server.metadata.get('groups', '').split(','):
                if extra_group:
                    groups[extra_group].append(server.name)

            # Add host metadata
            for key, value in to_dict(server).items():
                hostvars[server.name][key] = value

            hostvars[server.name]['rax_region'] = region

            for key, value in server.metadata.iteritems():
                prefix = os.getenv('RAX_META_PREFIX', 'meta')
                groups['%s_%s_%s' % (prefix, key, value)].append(server.name)

            groups['instance-%s' % server.id].append(server.name)
            groups['flavor-%s' % server.flavor['id']].append(server.name)
            try:
                imagegroup = 'image-%s' % images[server.image['id']]
                groups[imagegroup].append(server.name)
                groups['image-%s' % server.image['id']].append(server.name)
            except KeyError:
                try:
                    image = cs.images.get(server.image['id'])
                except cs.exceptions.NotFound:
                    groups['image-%s' % server.image['id']].append(server.name)
                else:
                    images[image.id] = image.human_id
                    groups['image-%s' % image.human_id].append(server.name)
                    groups['image-%s' % server.image['id']].append(server.name)

            # And finally, add an IP address
            hostvars[server.name]['ansible_ssh_host'] = server.accessIPv4

    if hostvars:
        groups['_meta'] = {'hostvars': hostvars}
    print(json.dumps(groups, sort_keys=True, indent=4))


def parse_args():
    parser = argparse.ArgumentParser(description='Ansible Rackspace Cloud '
                                                 'inventory module')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--list', action='store_true',
                       help='List active servers')
    group.add_argument('--host', help='List details about the specific host')
    return parser.parse_args()


def setup():
    default_creds_file = os.path.expanduser('~/.rackspace_cloud_credentials')

    env = os.getenv('RAX_ENV', None)
    if env:
        pyrax.set_environment(env)

    keyring_username = pyrax.get_setting('keyring_username')

    # Attempt to grab credentials from environment first
    try:
        creds_file = os.path.expanduser(os.environ['RAX_CREDS_FILE'])
    except KeyError, e:
        # But if that fails, use the default location of
        # ~/.rackspace_cloud_credentials
        if os.path.isfile(default_creds_file):
            creds_file = default_creds_file
        elif not keyring_username:
            sys.stderr.write('No value in environment variable %s and/or no '
                             'credentials file at %s\n'
                             % (e.message, default_creds_file))
            sys.exit(1)

    identity_type = pyrax.get_setting('identity_type')
    pyrax.set_setting('identity_type', identity_type or 'rackspace')

    region = pyrax.get_setting('region')

    try:
        if keyring_username:
            pyrax.keyring_auth(keyring_username, region=region)
        else:
            pyrax.set_credential_file(creds_file, region=region)
    except Exception, e:
        sys.stderr.write("%s: %s\n" % (e, e.message))
        sys.exit(1)

    regions = []
    if region:
        regions.append(region)
    else:
        for region in os.getenv('RAX_REGION', 'all').split(','):
            region = region.strip().upper()
            if region == 'ALL':
                regions = pyrax.regions
                break
            elif region not in pyrax.regions:
                sys.stderr.write('Unsupported region %s' % region)
                sys.exit(1)
            elif region not in regions:
                regions.append(region)

    return regions


def main():
    args = parse_args()
    regions = setup()
    if args.list:
        _list(regions)
    elif args.host:
        host(regions, args.host)
    sys.exit(0)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = spacewalk
#!/bin/env python

"""
Spacewalk external inventory script
=================================

Ansible has a feature where instead of reading from /etc/ansible/hosts
as a text file, it can query external programs to obtain the list
of hosts, groups the hosts are in, and even variables to assign to each host.

To use this, copy this file over /etc/ansible/hosts and chmod +x the file.
This, more or less, allows you to keep one central database containing
info about all of your managed instances.

This script is dependent upon the spacealk-reports package being installed
on the same machine. It is basically a CSV-to-JSON converter from the
output of "spacewalk-report system-groups-systems|inventory".

Tested with Ansible 1.1
"""
# 
# Author:: Jon Miller <jonEbird@gmail.com>
# Copyright:: Copyright (c) 2013, Jon Miller
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or (at
# your option) any later version.
# 
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
# 

import sys
import os
import time
from optparse import OptionParser
import subprocess

try:
    import json
except:
    import simplejson as json

base_dir  = os.path.dirname(os.path.realpath(__file__))
SW_REPORT = '/usr/bin/spacewalk-report'
CACHE_DIR = os.path.join(base_dir, ".spacewalk_reports")
CACHE_AGE = 300 # 5min

# Sanity check
if not os.path.exists(SW_REPORT):
    print >> sys.stderr, 'Error: %s is required for operation.' % (SW_REPORT)
    sys.exit(1)

# Pre-startup work
if not os.path.exists(CACHE_DIR):
    os.mkdir(CACHE_DIR)
    os.chmod(CACHE_DIR, 2775)

# Helper functions
#------------------------------

def spacewalk_report(name):
    """Yield a dictionary form of each CSV output produced by the specified
    spacewalk-report
    """
    cache_filename = os.path.join(CACHE_DIR, name)
    if not os.path.exists(cache_filename) or \
            (time.time() - os.stat(cache_filename).st_mtime) > CACHE_AGE:
        # Update the cache
        fh = open(cache_filename, 'w')
        p = subprocess.Popen([SW_REPORT, name], stdout=fh)
        p.wait()
        fh.close()

    lines = open(cache_filename, 'r').readlines()
    keys = lines[0].strip().split(',')
    for line in lines[1:]:
        values = line.strip().split(',')
        if len(keys) == len(values):
            yield dict(zip(keys, values))


# Options
#------------------------------

parser = OptionParser(usage="%prog [options] --list | --host <machine>")
parser.add_option('--list', default=False, dest="list", action="store_true",
                  help="Produce a JSON consumable grouping of servers for Ansible")
parser.add_option('--host', default=None, dest="host",
                  help="Generate additional host specific details for given host for Ansible")
parser.add_option('-H', '--human', dest="human",
                  default=False, action="store_true",
                  help="Produce a friendlier version of either server list or host detail")
(options, args) = parser.parse_args()


# List out the known server from Spacewalk
#------------------------------
if options.list:

    groups = {}
    try:
        for system in spacewalk_report('system-groups-systems'):
            if system['group_name'] not in groups:
                groups[system['group_name']] = set()

            groups[system['group_name']].add(system['server_name'])

    except (OSError), e:
        print >> sys.stderr, 'Problem executing the command "%s system-groups-systems": %s' % \
            (SW_REPORT, str(e))
        sys.exit(2)

    if options.human:
        for group, systems in groups.iteritems():
            print '[%s]\n%s\n' % (group, '\n'.join(systems))
    else:
        print json.dumps(dict([ (k, list(s)) for k, s in groups.iteritems() ]))

    sys.exit(0)


# Return a details information concerning the spacewalk server
#------------------------------
elif options.host:

    host_details = {}
    try:
        for system in spacewalk_report('inventory'):
            if system['hostname'] == options.host:
                host_details = system
                break

    except (OSError), e:
        print >> sys.stderr, 'Problem executing the command "%s inventory": %s' % \
            (SW_REPORT, str(e))
        sys.exit(2)
    
    if options.human:
        print 'Host: %s' % options.host
        for k, v in host_details.iteritems():
            print '  %s: %s' % (k, '\n    '.join(v.split(';')))
    else:
        print json.dumps(host_details)

    sys.exit(0)

else:

    parser.print_help()
    sys.exit(1)

########NEW FILE########
__FILENAME__ = ssh_config
#!/usr/bin/env python

# (c) 2014, Tomas Karasek <tomas.karasek@digile.fi>
#
# This file is part of Ansible.
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible. If not, see <http://www.gnu.org/licenses/>.

# Dynamic inventory script which lets you use aliases from ~/.ssh/config.
#
# It prints inventory based on parsed ~/.ssh/config. You can refer to hosts
# with their alias, rather than with the IP or hostname. It takes advantage
# of the ansible_ssh_{host,port,user,private_key_file}.
#
# If you have in your .ssh/config:
#   Host git
#       HostName git.domain.org
#       User tkarasek
#       IdentityFile /home/tomk/keys/thekey
#
#   You can do
#       $ ansible git -m ping
#
# Example invocation:
#    ssh_config.py --list
#    ssh_config.py --host <alias>

import argparse
import os.path
import sys

import paramiko

try:
    import json
except ImportError:
    import simplejson as json

_key = 'ssh_config'

_ssh_to_ansible = [('user', 'ansible_ssh_user'),
                  ('hostname', 'ansible_ssh_host'),
                  ('identityfile', 'ansible_ssh_private_key_file'),
                  ('port', 'ansible_ssh_port')]


def get_config():
    with open(os.path.expanduser('~/.ssh/config')) as f:
        cfg = paramiko.SSHConfig()
        cfg.parse(f)
        ret_dict = {}
        for d in cfg._config:
            _copy = dict(d)
            del _copy['host']
            for host in d['host']:
                ret_dict[host] = _copy['config']
        return ret_dict


def print_list():
    cfg = get_config()
    meta = {'hostvars': {}}
    for alias, attributes in cfg.items():
        tmp_dict = {}
        for ssh_opt, ans_opt in _ssh_to_ansible:
            if ssh_opt in attributes:
                tmp_dict[ans_opt] = attributes[ssh_opt]
        if tmp_dict:
            meta['hostvars'][alias] = tmp_dict

    print json.dumps({_key: list(set(meta['hostvars'].keys())), '_meta': meta})


def print_host(host):
    cfg = get_config()
    print json.dumps(cfg[host])


def get_args(args_list):
    parser = argparse.ArgumentParser(
            description='ansible inventory script parsing .ssh/config')
    mutex_group = parser.add_mutually_exclusive_group(required=True)
    help_list = 'list all hosts from .ssh/config inventory'
    mutex_group.add_argument('--list', action='store_true', help=help_list)
    help_host = 'display variables for a host'
    mutex_group.add_argument('--host', help=help_host)
    return parser.parse_args(args_list)


def main(args_list):

    args = get_args(args_list)
    if args.list:
        print_list()
    if args.host:
        print_host(args.host)


if __name__ == '__main__':
    main(sys.argv[1:])

########NEW FILE########
__FILENAME__ = vagrant
#!/usr/bin/env python
"""
Vagrant external inventory script. Automatically finds the IP of the booted vagrant vm(s), and
returns it under the host group 'vagrant'

Example Vagrant configuration using this script:

    config.vm.provision :ansible do |ansible|
      ansible.playbook = "./provision/your_playbook.yml"
      ansible.inventory_file = "./provision/inventory/vagrant.py"
      ansible.verbose = true
    end
"""

# Copyright (C) 2013  Mark Mandel <mark@compoundtheory.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

#
# Thanks to the spacewalk.py inventory script for giving me the basic structure
# of this.
#

import sys
import subprocess
import re
import string
from optparse import OptionParser
try:
    import json
except:
    import simplejson as json

# Options
#------------------------------

parser = OptionParser(usage="%prog [options] --list | --host <machine>")
parser.add_option('--list', default=False, dest="list", action="store_true",
                  help="Produce a JSON consumable grouping of Vagrant servers for Ansible")
parser.add_option('--host', default=None, dest="host",
                  help="Generate additional host specific details for given host for Ansible")
(options, args) = parser.parse_args()

#
# helper functions
#

# get all the ssh configs for all boxes in an array of dictionaries.
def get_ssh_config():
    configs = []

    boxes = list_running_boxes()

    for box in boxes:
        config = get_a_ssh_config(box)
        configs.append(config)

    return configs

#list all the running boxes
def list_running_boxes():
    output = subprocess.check_output(["vagrant", "status"]).split('\n')

    boxes = []

    for line in output:
        matcher = re.search("([^\s]+)[\s]+running \(.+", line)
        if matcher:
            boxes.append(matcher.group(1))


    return boxes

#get the ssh config for a single box
def get_a_ssh_config(box_name):
    """Gives back a map of all the machine's ssh configurations"""

    output = subprocess.check_output(["vagrant", "ssh-config", box_name]).split('\n')

    config = {}
    for line in output:
        if line.strip() != '':
            matcher = re.search("(  )?([a-zA-Z]+) (.*)", line)
            config[matcher.group(2)] = matcher.group(3)

    return config


# List out servers that vagrant has running
#------------------------------
if options.list:
    ssh_config = get_ssh_config()
    hosts = { 'vagrant': []}

    for data in ssh_config:
        hosts['vagrant'].append(data['HostName'])

    print json.dumps(hosts)
    sys.exit(1)

# Get out the host details
#------------------------------
elif options.host:
    result = {}
    ssh_config = get_ssh_config()

    details = filter(lambda x: (x['HostName'] == options.host), ssh_config)
    if len(details) > 0:
        #pass through the port, in case it's non standard.
        result = details[0]
        result['ansible_ssh_port'] = result['Port']

    print json.dumps(result)
    sys.exit(1)


# Print out help
#------------------------------
else:
    parser.print_help()
    sys.exit(1)
########NEW FILE########
__FILENAME__ = vmware
#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
VMWARE external inventory script
=================================

shamelessly copied from existing inventory scripts.

This script and it's ini can be used more than once,

i.e vmware.py/vmware_colo.ini vmware_idf.py/vmware_idf.ini
(script can be link)

so if you don't have clustered vcenter  but multiple esx machines or
just diff clusters you can have a inventory  per each and automatically
group hosts based on file name or specify a group in the ini.
'''

import os
import sys
import time
import ConfigParser
from psphere.client import Client
from psphere.managedobjects import HostSystem

try:
    import json
except ImportError:
    import simplejson as json


def save_cache(cache_item, data, config):
    ''' saves item to cache '''
    dpath = config.get('defaults', 'cache_dir')
    try:
        cache = open('/'.join([dpath,cache_item]), 'w')
        cache.write(json.dumps(data))
        cache.close()
    except IOError, e:
        pass # not really sure what to do here


def get_cache(cache_item, config):
    ''' returns cached item  '''
    dpath = config.get('defaults', 'cache_dir')
    inv = {}
    try:
        cache = open('/'.join([dpath,cache_item]), 'r')
        inv = json.loads(cache.read())
        cache.close()
    except IOError, e:
        pass # not really sure what to do here

    return inv

def cache_available(cache_item, config):
    ''' checks if we have a 'fresh' cache available for item requested '''

    if config.has_option('defaults', 'cache_dir'):
        dpath = config.get('defaults', 'cache_dir')

        try:
            existing = os.stat( '/'.join([dpath,cache_item]))
        except:
            # cache doesn't exist or isn't accessible
            return False

        if config.has_option('defaults', 'cache_max_age'):
            maxage = config.get('defaults', 'cache_max_age')

            if (existing.st_mtime - int(time.time())) <= maxage:
                return True

    return False

def get_host_info(host):
    ''' Get variables about a specific host '''

    hostinfo = {
                'vmware_name' : host.name,
                'vmware_tag' : host.tag,
                'vmware_parent': host.parent.name,
               }
    for k in host.capability.__dict__.keys():
        if k.startswith('_'):
           continue
        try:
            hostinfo['vmware_' + k] = str(host.capability[k])
        except:
           continue

    return hostinfo


def get_inventory(client, config):
    ''' Reads the inventory from cache or vmware api '''

    if cache_available('inventory', config):
        inv = get_cache('inventory',config)
    else:
        inv= { 'all': {'hosts': []}, '_meta': { 'hostvars': {} } }
        default_group = os.path.basename(sys.argv[0]).rstrip('.py')

        if config.has_option('defaults', 'guests_only'):
            guests_only = config.get('defaults', 'guests_only')
        else:
            guests_only = True

        if not guests_only:
            if config.has_option('defaults','hw_group'):
                hw_group = config.get('defaults','hw_group')
            else:
                hw_group = default_group + '_hw'
            inv[hw_group] = []

        if config.has_option('defaults','vm_group'):
            vm_group = config.get('defaults','vm_group')
        else:
            vm_group = default_group + '_vm'
        inv[vm_group] = []

        # Loop through physical hosts:
        hosts = HostSystem.all(client)
        for host in hosts:
            if not guests_only:
                inv['all']['hosts'].append(host.name)
                inv[hw_group].append(host.name)
                if host.tag:
                    taggroup = 'vmware_' + host.tag
                    if taggroup in inv:
                        inv[taggroup].append(host.name)
                    else:
                        inv[taggroup] = [ host.name ]

                inv['_meta']['hostvars'][host.name] = get_host_info(host)
                save_cache(vm.name, inv['_meta']['hostvars'][host.name], config)

            for vm in host.vm:
                inv['all']['hosts'].append(vm.name)
                inv[vm_group].append(vm.name)
                if vm.tag:
                    taggroup = 'vmware_' + vm.tag
                    if taggroup in inv:
                        inv[taggroup].append(vm.name)
                    else:
                        inv[taggroup] = [ vm.name ]

                inv['_meta']['hostvars'][vm.name] = get_host_info(host)
                save_cache(vm.name, inv['_meta']['hostvars'][vm.name], config)

    save_cache('inventory', inv, config)
    return json.dumps(inv)

def get_single_host(client, config, hostname):

    inv = {}

    if cache_available(hostname, config):
        inv = get_cache(hostname,config)
    else:
        hosts = HostSystem.all(client) #TODO: figure out single host getter
        for host in hosts:
            if hostname == host.name:
                inv = get_host_info(host)
                break
            for vm in host.vm:
                if hostname == vm.name:
                    inv = get_host_info(host)
                    break
        save_cache(hostname,inv,config)

    return json.dumps(inv)

if __name__ == '__main__':
    inventory = {}
    hostname = None

    if len(sys.argv) > 1:
        if sys.argv[1] == "--host":
            hostname = sys.argv[2]

    # Read config
    config = ConfigParser.SafeConfigParser()
    for configfilename in [os.path.abspath(sys.argv[0]).rstrip('.py') + '.ini', 'vmware.ini']:
        if os.path.exists(configfilename):
            config.read(configfilename)
            break

    try:
        client =  Client( config.get('auth','host'),
                          config.get('auth','user'),
                          config.get('auth','password'),
                        )
    except Exception, e:
        client = None
        #print >> STDERR "Unable to login (only cache avilable): %s", str(e)

    # acitually do the work
    if hostname is None:
        inventory = get_inventory(client, config)
    else:
        inventory = get_single_host(client, config, hostname)

    # return to ansible
    print inventory

########NEW FILE########
__FILENAME__ = zabbix
#!/usr/bin/env python

# (c) 2013, Greg Buehler
#
# This file is part of Ansible,
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

######################################################################

"""
Zabbix Server external inventory script. 
========================================

Returns hosts and hostgroups from Zabbix Server.

Configuration is read from `zabbix.ini`.

Tested with Zabbix Server 2.0.6.
"""

import os, sys
import json
import argparse
import ConfigParser

try:
    from zabbix_api import ZabbixAPI
except:
    print >> sys.stderr, "Error: Zabbix API library must be installed: pip install zabbix-api."
    sys.exit(1)

try:
    import json
except:
    import simplejson as json

class ZabbixInventory(object):

    def read_settings(self):
        config = ConfigParser.SafeConfigParser()
        config.read(os.path.dirname(os.path.realpath(__file__)) + '/zabbix.ini')
        # server
        if config.has_option('zabbix', 'server'):
            self.zabbix_server = config.get('zabbix', 'server')

        # login   
        if config.has_option('zabbix', 'username'):
            self.zabbix_username = config.get('zabbix', 'username')
        if config.has_option('zabbix', 'password'):
            self.zabbix_password = config.get('zabbix', 'password')

    def read_cli(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('--host')
        parser.add_argument('--list', action='store_true')
        self.options = parser.parse_args()

    def hoststub(self):
        return {
            'hosts': []
        }

    def get_host(self, api, name):
        data = {}
        return data

    def get_list(self, api):
        hostsData = api.host.get({'output': 'extend', 'selectGroups': 'extend'})

        data = {}
        data[self.defaultgroup] = self.hoststub()

        for host in hostsData:
            hostname = host['name']
            data[self.defaultgroup]['hosts'].append(hostname)   

            for group in host['groups']:
                groupname = group['name']

                if not groupname in data:
                    data[groupname] = self.hoststub()

                data[groupname]['hosts'].append(hostname)

        return data

    def __init__(self):

        self.defaultgroup = 'group_all'
        self.zabbix_server = None
        self.zabbix_username = None
        self.zabbix_password = None

        self.read_settings()
        self.read_cli()

        if self.zabbix_server and self.zabbix_username:
            try:
                api = ZabbixAPI(server=self.zabbix_server)
                api.login(user=self.zabbix_username, password=self.zabbix_password)
            except BaseException, e:
                print >> sys.stderr, "Error: Could not login to Zabbix server. Check your zabbix.ini."
                sys.exit(1)

            if self.options.host:
                data = self.get_host(api, self.options.host)
                print json.dumps(data, indent=2)

            elif self.options.list:
                data = self.get_list(api)
                print json.dumps(data, indent=2)

            else:
                print >> sys.stderr, "usage: --list  ..OR.. --host <hostname>"
                sys.exit(1)

        else:
            print >> sys.stderr, "Error: Configuration of server and credentials are required. See zabbix.ini."
            sys.exit(1)

ZabbixInventory()

########NEW FILE########
__FILENAME__ = cleanup_ec2
'''
Find and delete AWS resources matching the provided --match string.  Unless
--yes|-y is provided, the prompt for confirmation prior to deleting resources.
Please use caution, you can easily delete you're *ENTIRE* EC2 infrastructure.
'''

import os
import re
import sys
import boto
import optparse
import yaml
import os.path
import boto.ec2.elb

def delete_aws_resources(get_func, attr, opts):
    for item in get_func():
        val = getattr(item, attr)
        if re.search(opts.match_re, val):
            prompt_and_delete(item, "Delete matching %s? [y/n]: " % (item,), opts.assumeyes)

def delete_aws_eips(get_func, attr, opts):

    # the file might not be there if the integration test wasn't run
    try:
      eip_log = open(opts.eip_log, 'r').read().splitlines()
    except IOError:
      print opts.eip_log, 'not found.'
      return

    for item in get_func():
        val = getattr(item, attr)
        if val in eip_log:
          prompt_and_delete(item, "Delete matching %s? [y/n]: " % (item,), opts.assumeyes)

def delete_aws_instances(reservation, opts):
    for list in reservation:
        for item in list.instances:
            prompt_and_delete(item, "Delete matching %s? [y/n]: " % (item,), opts.assumeyes)

def prompt_and_delete(item, prompt, assumeyes):
    if not assumeyes:
        assumeyes = raw_input(prompt).lower() == 'y'
    assert hasattr(item, 'delete') or hasattr(item, 'terminate') , "Class <%s> has no delete or terminate attribute" % item.__class__
    if assumeyes:
        if  hasattr(item, 'delete'):
            item.delete()
            print ("Deleted %s" % item)
        if  hasattr(item, 'terminate'):
            item.terminate()
            print ("Terminated %s" % item)

def parse_args():
    # Load details from credentials.yml
    default_aws_access_key = os.environ.get('AWS_ACCESS_KEY', None)
    default_aws_secret_key = os.environ.get('AWS_SECRET_KEY', None)
    if os.path.isfile('credentials.yml'):
        credentials = yaml.load(open('credentials.yml', 'r'))

        if default_aws_access_key is None:
            default_aws_access_key = credentials['ec2_access_key']
        if default_aws_secret_key is None:
            default_aws_secret_key = credentials['ec2_secret_key']

    parser = optparse.OptionParser(usage="%s [options]" % (sys.argv[0],),
                description=__doc__)
    parser.add_option("--access",
        action="store", dest="ec2_access_key",
        default=default_aws_access_key,
        help="Amazon ec2 access id.  Can use EC2_ACCESS_KEY environment variable, or a values from credentials.yml.")
    parser.add_option("--secret",
        action="store", dest="ec2_secret_key",
        default=default_aws_secret_key,
        help="Amazon ec2 secret key.  Can use EC2_SECRET_KEY environment variable, or a values from credentials.yml.")
    parser.add_option("--eip-log",
        action="store", dest="eip_log",
        default = None,
        help = "Path to log of EIPs created during test.")
    parser.add_option("--integration-config",
        action="store", dest="int_config",
        default = "integration_config.yml",
        help = "path to integration config")
    parser.add_option("--credentials", "-c",
        action="store", dest="credential_file",
        default="credentials.yml",
        help="YAML file to read cloud credentials (default: %default)")
    parser.add_option("--yes", "-y",
        action="store_true", dest="assumeyes",
        default=False,
        help="Don't prompt for confirmation")
    parser.add_option("--match",
        action="store", dest="match_re",
        default="^ansible-testing-",
        help="Regular expression used to find AWS resources (default: %default)")

    (opts, args) = parser.parse_args()
    for required in ['ec2_access_key', 'ec2_secret_key']:
        if getattr(opts, required) is None:
            parser.error("Missing required parameter: --%s" % required)


    return (opts, args)

if __name__ == '__main__':

    (opts, args) = parse_args()

    int_config = yaml.load(open(opts.int_config).read())
    if not opts.eip_log:
        output_dir = os.path.expanduser(int_config["output_dir"])
        opts.eip_log = output_dir + '/' + opts.match_re.replace('^','') + '-eip_integration_tests.log'

    # Connect to AWS
    aws = boto.connect_ec2(aws_access_key_id=opts.ec2_access_key,
            aws_secret_access_key=opts.ec2_secret_key)

    elb = boto.connect_elb(aws_access_key_id=opts.ec2_access_key,
            aws_secret_access_key=opts.ec2_secret_key)

    try:
        # Delete matching keys
        delete_aws_resources(aws.get_all_key_pairs, 'name', opts)

        # Delete matching groups
        delete_aws_resources(aws.get_all_security_groups, 'name', opts)

        # Delete ELBs
        delete_aws_resources(elb.get_all_load_balancers, 'name', opts)

        # Delete recorded EIPs
        delete_aws_eips(aws.get_all_addresses, 'public_ip', opts)

        # Delete temporary instances
        filters = {"tag:Name":opts.match_re.replace('^',''), "instance-state-name": ['running', 'pending', 'stopped' ]}
        delete_aws_instances(aws.get_all_instances(filters=filters), opts)

    except KeyboardInterrupt, e:
        print "\nExiting on user command."

########NEW FILE########
__FILENAME__ = inventory_api
#!/usr/bin/env python

import json
import sys

from optparse import OptionParser

parser = OptionParser()
parser.add_option('-l', '--list', default=False, dest="list_hosts", action="store_true")
parser.add_option('-H', '--host', default=None, dest="host")
parser.add_option('-e', '--extra-vars', default=None, dest="extra")

options, args = parser.parse_args()

systems = {
    "ungrouped": [ "jupiter", "saturn" ],
    "greek": [ "zeus", "hera", "poseidon" ],
    "norse": [ "thor", "odin", "loki" ],
    "major-god": [ "zeus", "odin" ],
}

variables = {
    "thor": {
        "hammer": True
        },
    "zeus": {},
}

if options.list_hosts == True:
    print json.dumps(systems)
    sys.exit(0)

if options.host is not None:
    if options.extra:
        k,v = options.extra.split("=")
        variables[options.host][k] = v
    print json.dumps(variables[options.host])
    sys.exit(0)

parser.print_help()
sys.exit(1)
########NEW FILE########
__FILENAME__ = TestConstants
# -*- coding: utf-8 -*-

import unittest

from ansible.constants import get_config
import ConfigParser
import random
import string
import os


def random_string(length):
    return ''.join(random.choice(string.ascii_uppercase) for x in range(6))

p = ConfigParser.ConfigParser()
p.read(os.path.join(os.path.dirname(__file__), 'ansible.cfg'))

class TestConstants(unittest.TestCase):

    #####################################
    ### get_config unit tests

    
    def test_configfile_and_env_both_set(self):
        r = random_string(6)
        env_var = 'ANSIBLE_TEST_%s' % r
        os.environ[env_var] = r

        res = get_config(p, 'defaults', 'test_key', env_var, 'default')
        del os.environ[env_var]

        assert res == r


    def test_configfile_set_env_not_set(self):
        r = random_string(6)
        env_var = 'ANSIBLE_TEST_%s' % r
        assert env_var not in os.environ
        
        res = get_config(p, 'defaults', 'test_key', env_var, 'default')

        print res
        assert res == 'test_value'


    def test_configfile_not_set_env_set(self):
        r = random_string(6)
        env_var = 'ANSIBLE_TEST_%s' % r
        os.environ[env_var] = r

        res = get_config(p, 'defaults', 'doesnt_exist', env_var, 'default')
        del os.environ[env_var]

        assert res == r


    def test_configfile_not_set_env_not_set(self):
        r = random_string(6)
        env_var = 'ANSIBLE_TEST_%s' % r
        assert env_var not in os.environ
        
        res = get_config(p, 'defaults', 'doesnt_exist', env_var, 'default')

        assert res == 'default'

########NEW FILE########
__FILENAME__ = TestFilters
'''
Test bundled filters
'''

import os.path
import unittest, tempfile, shutil
from ansible import playbook, inventory, callbacks
import ansible.runner.filter_plugins.core

INVENTORY = inventory.Inventory(['localhost'])

BOOK = '''
- hosts: localhost
  vars:
    var: { a: [1,2,3] }
  tasks:
  - template: src=%s dest=%s
'''

SRC = '''
-
{{ var|to_json }}
-
{{ var|to_nice_json }}
-
{{ var|to_yaml }}
-
{{ var|to_nice_yaml }}
'''

DEST = '''
-
{"a": [1, 2, 3]}
-
{
    "a": [
        1, 
        2, 
        3
    ]
}
-
a: [1, 2, 3]

-
a:
- 1
- 2
- 3
'''

class TestFilters(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(dir='/tmp')

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def temp(self, name, data=''):
        '''write a temporary file and return the name'''
        name = self.tmpdir + '/' + name
        with open(name, 'w') as f:
            f.write(data)
        return name

    def test_bool_none(self):
        a = ansible.runner.filter_plugins.core.bool(None)
        assert a == None

    def test_bool_true(self):
        a = ansible.runner.filter_plugins.core.bool(True)
        assert a == True

    def test_bool_yes(self):
        a = ansible.runner.filter_plugins.core.bool('Yes')
        assert a == True

    def test_bool_no(self):
        a = ansible.runner.filter_plugins.core.bool('Foo')
        assert a == False

    def test_quotes(self):
        a = ansible.runner.filter_plugins.core.quote('ls | wc -l')
        assert a == "'ls | wc -l'"

    def test_fileglob(self):
        pathname = os.path.join(os.path.dirname(__file__), '*')
        a = ansible.runner.filter_plugins.core.fileglob(pathname)
        assert __file__ in a

    def test_regex(self):
        a = ansible.runner.filter_plugins.core.regex('ansible', 'ansible',
                                                     match_type='findall')
        assert a == True

    def test_match_case_sensitive(self):
        a = ansible.runner.filter_plugins.core.match('ansible', 'ansible')
        assert a == True

    def test_match_case_insensitive(self):
        a = ansible.runner.filter_plugins.core.match('ANSIBLE', 'ansible',
                                                     True)
        assert a == True

    def test_match_no_match(self):
        a = ansible.runner.filter_plugins.core.match(' ansible', 'ansible')
        assert a == False

    def test_search_case_sensitive(self):
        a = ansible.runner.filter_plugins.core.search(' ansible ', 'ansible')
        assert a == True

    def test_search_case_insensitive(self):
        a = ansible.runner.filter_plugins.core.search(' ANSIBLE ', 'ansible',
                                                      True)
        assert a == True

    def test_regex_replace_case_sensitive(self):
        a = ansible.runner.filter_plugins.core.regex_replace('ansible', '^a.*i(.*)$',
                                                      'a\\1')
        assert a == 'able'

    def test_regex_replace_case_insensitive(self):
        a = ansible.runner.filter_plugins.core.regex_replace('ansible', '^A.*I(.*)$',
                                                      'a\\1', True)
        assert a == 'able'

    def test_regex_replace_no_match(self):
        a = ansible.runner.filter_plugins.core.regex_replace('ansible', '^b.*i(.*)$',
                                                      'a\\1')
        assert a == 'ansible'

    #def test_filters(self):

        # this test is pretty low level using a playbook, hence I am disabling it for now -- MPD.
        #return

        #src = self.temp('src.j2', SRC)
        #dest = self.temp('dest.txt')
        #book = self.temp('book', BOOK % (src, dest))

        #playbook.PlayBook(
        #    playbook  = book,
        #    inventory = INVENTORY,
        #    transport = 'local',
        #    callbacks = callbacks.PlaybookCallbacks(),
        #    runner_callbacks = callbacks.DefaultRunnerCallbacks(),
        #    stats  = callbacks.AggregateStats(),
        #).run()

        #out = open(dest).read()
        #self.assertEqual(DEST, out)

    def test_version_compare(self):
        self.assertTrue(ansible.runner.filter_plugins.core.version_compare(0, 1.1, 'lt', False))
        self.assertTrue(ansible.runner.filter_plugins.core.version_compare(1.1, 1.2, '<'))

        self.assertTrue(ansible.runner.filter_plugins.core.version_compare(1.2, 1.2, '=='))
        self.assertTrue(ansible.runner.filter_plugins.core.version_compare(1.2, 1.2, '='))
        self.assertTrue(ansible.runner.filter_plugins.core.version_compare(1.2, 1.2, 'eq'))


        self.assertTrue(ansible.runner.filter_plugins.core.version_compare(1.3, 1.2, 'gt'))
        self.assertTrue(ansible.runner.filter_plugins.core.version_compare(1.3, 1.2, '>'))

        self.assertTrue(ansible.runner.filter_plugins.core.version_compare(1.3, 1.2, 'ne'))
        self.assertTrue(ansible.runner.filter_plugins.core.version_compare(1.3, 1.2, '!='))
        self.assertTrue(ansible.runner.filter_plugins.core.version_compare(1.3, 1.2, '<>'))

        self.assertTrue(ansible.runner.filter_plugins.core.version_compare(1.1, 1.1, 'ge'))
        self.assertTrue(ansible.runner.filter_plugins.core.version_compare(1.2, 1.1, '>='))

        self.assertTrue(ansible.runner.filter_plugins.core.version_compare(1.1, 1.1, 'le'))
        self.assertTrue(ansible.runner.filter_plugins.core.version_compare(1.0, 1.1, '<='))

        self.assertTrue(ansible.runner.filter_plugins.core.version_compare('12.04', 12, 'ge'))

########NEW FILE########
__FILENAME__ = TestInventory
import os
import unittest
from nose.tools import raises

from ansible import errors
from ansible.inventory import Inventory

class TestInventory(unittest.TestCase):

    def setUp(self):

        self.cwd = os.getcwd()
        self.test_dir = os.path.join(self.cwd, 'inventory_test_data')

        self.inventory_file             = os.path.join(self.test_dir, 'simple_hosts')
        self.large_range_inventory_file = os.path.join(self.test_dir, 'large_range')
        self.complex_inventory_file     = os.path.join(self.test_dir, 'complex_hosts')
        self.inventory_script           = os.path.join(self.test_dir, 'inventory_api.py')
        self.inventory_dir              = os.path.join(self.test_dir, 'inventory_dir')

        os.chmod(self.inventory_script, 0755)

    def tearDown(self):
        os.chmod(self.inventory_script, 0644)

    def compare(self, left, right, sort=True):
        if sort:
            left = sorted(left)
            right = sorted(right)
        print left
        print right
        assert left == right

    def empty_inventory(self):
        return Inventory(None)

    def simple_inventory(self):
        return Inventory(self.inventory_file)

    def large_range_inventory(self):
        return Inventory(self.large_range_inventory_file)

    def script_inventory(self):
        return Inventory(self.inventory_script)

    def complex_inventory(self):
        return Inventory(self.complex_inventory_file)

    def dir_inventory(self):
        return Inventory(self.inventory_dir)

    all_simple_hosts=['jupiter', 'saturn', 'zeus', 'hera',
            'cerberus001','cerberus002','cerberus003',
            'cottus99', 'cottus100',
            'poseidon', 'thor', 'odin', 'loki',
            'thrudgelmir0', 'thrudgelmir1', 'thrudgelmir2',
            'thrudgelmir3', 'thrudgelmir4', 'thrudgelmir5',
            'Hotep-a', 'Hotep-b', 'Hotep-c',
            'BastC', 'BastD', 'neptun', ]

    #####################################
    ### Empty inventory format tests

    def test_empty(self):
        inventory = self.empty_inventory()
        hosts = inventory.list_hosts()
        self.assertEqual(hosts, [])

    #####################################
    ### Simple inventory format tests

    def test_simple(self):
        inventory = self.simple_inventory()
        hosts = inventory.list_hosts()
        self.assertEqual(sorted(hosts), sorted(self.all_simple_hosts))

    def test_simple_all(self):
        inventory = self.simple_inventory()
        hosts = inventory.list_hosts('all')
        self.assertEqual(sorted(hosts), sorted(self.all_simple_hosts))

    def test_get_hosts(self):
        inventory = Inventory('127.0.0.1,192.168.1.1')
        hosts = inventory.get_hosts('!10.0.0.1')
        hosts_all = inventory.get_hosts('all')
        self.assertEqual(sorted(hosts), sorted(hosts_all))

    def test_no_src(self):
        inventory = Inventory('127.0.0.1,')
        self.assertEqual(inventory.src(), None)

    def test_simple_norse(self):
        inventory = self.simple_inventory()
        hosts = inventory.list_hosts("norse")

        expected_hosts=['thor', 'odin', 'loki']
        assert sorted(hosts) == sorted(expected_hosts)

    def test_simple_ungrouped(self):
        inventory = self.simple_inventory()
        hosts = inventory.list_hosts("ungrouped")

        expected_hosts=['jupiter', 'saturn',
                        'thrudgelmir0', 'thrudgelmir1', 'thrudgelmir2',
                        'thrudgelmir3', 'thrudgelmir4', 'thrudgelmir5']
        assert sorted(hosts) == sorted(expected_hosts)

    def test_simple_combined(self):
        inventory = self.simple_inventory()
        hosts = inventory.list_hosts("norse:greek")

        expected_hosts=['zeus', 'hera', 'poseidon',
                        'cerberus001','cerberus002','cerberus003',
                        'cottus99','cottus100',
                        'thor', 'odin', 'loki']
        assert sorted(hosts) == sorted(expected_hosts)

    def test_simple_restrict(self):
        inventory = self.simple_inventory()

        restricted_hosts = ['hera', 'poseidon', 'thor']
        expected_hosts=['zeus', 'hera', 'poseidon',
                        'cerberus001','cerberus002','cerberus003',
                        'cottus99', 'cottus100',
                        'thor', 'odin', 'loki']

        inventory.restrict_to(restricted_hosts)
        hosts = inventory.list_hosts("norse:greek")

        assert sorted(hosts) == sorted(restricted_hosts)

        inventory.lift_restriction()
        hosts = inventory.list_hosts("norse:greek")

        assert sorted(hosts) == sorted(expected_hosts)

    def test_simple_string_ipv4(self):
        inventory = Inventory('127.0.0.1,192.168.1.1')
        hosts = inventory.list_hosts()
        self.assertEqual(sorted(hosts), sorted(['127.0.0.1','192.168.1.1']))

    def test_simple_string_ipv4_port(self):
        inventory = Inventory('127.0.0.1:2222,192.168.1.1')
        hosts = inventory.list_hosts()
        self.assertEqual(sorted(hosts), sorted(['127.0.0.1','192.168.1.1']))

    def test_simple_string_ipv4_vars(self):
        inventory = Inventory('127.0.0.1:2222,192.168.1.1')
        var = inventory.get_variables('127.0.0.1')
        self.assertEqual(var['ansible_ssh_port'], 2222)

    def test_simple_string_ipv6(self):
        inventory = Inventory('FE80:EF45::12:1,192.168.1.1')
        hosts = inventory.list_hosts()
        self.assertEqual(sorted(hosts), sorted(['FE80:EF45::12:1','192.168.1.1']))

    def test_simple_string_ipv6_port(self):
        inventory = Inventory('[FE80:EF45::12:1]:2222,192.168.1.1')
        hosts = inventory.list_hosts()
        self.assertEqual(sorted(hosts), sorted(['FE80:EF45::12:1','192.168.1.1']))

    def test_simple_string_ipv6_vars(self):
        inventory = Inventory('[FE80:EF45::12:1]:2222,192.168.1.1')
        var = inventory.get_variables('FE80:EF45::12:1')
        self.assertEqual(var['ansible_ssh_port'], 2222)

    def test_simple_string_fqdn(self):
        inventory = Inventory('foo.example.com,bar.example.com')
        hosts = inventory.list_hosts()
        self.assertEqual(sorted(hosts), sorted(['foo.example.com','bar.example.com']))

    def test_simple_string_fqdn_port(self):
        inventory = Inventory('foo.example.com:2222,bar.example.com')
        hosts = inventory.list_hosts()
        self.assertEqual(sorted(hosts), sorted(['foo.example.com','bar.example.com']))

    def test_simple_string_fqdn_vars(self):
        inventory = Inventory('foo.example.com:2222,bar.example.com')
        var = inventory.get_variables('foo.example.com')
        self.assertEqual(var['ansible_ssh_port'], 2222)

    def test_simple_vars(self):
        inventory = self.simple_inventory()
        vars = inventory.get_variables('thor')

        assert vars == {'group_names': ['norse'],
                        'inventory_hostname': 'thor',
                        'inventory_hostname_short': 'thor'}

    def test_simple_port(self):
        inventory = self.simple_inventory()
        vars = inventory.get_variables('hera')

        expected = { 'ansible_ssh_port': 3000,
                     'group_names': ['greek'],
                     'inventory_hostname': 'hera',
                     'inventory_hostname_short': 'hera' }
        assert vars == expected

    def test_large_range(self):
        inventory = self.large_range_inventory()
        hosts = inventory.list_hosts()
        self.assertEqual(sorted(hosts),  sorted('bob%03i' %i  for i in range(0, 143)))

    def test_subset(self):
        inventory = self.simple_inventory()
        inventory.subset('odin;thor,loki')
        self.assertEqual(sorted(inventory.list_hosts()),  sorted(['thor','odin','loki']))

    def test_subset_range(self):
        inventory = self.simple_inventory()
        inventory.subset('greek[0-2];norse[0]')
        self.assertEqual(sorted(inventory.list_hosts()),  sorted(['zeus','hera','thor']))

    def test_subet_range_empty_group(self):
        inventory = self.simple_inventory()
        inventory.subset('missing[0]')
        self.assertEqual(sorted(inventory.list_hosts()), sorted([]))

    def test_subset_filename(self):
        inventory = self.simple_inventory()
        inventory.subset('@' + os.path.join(self.test_dir, 'restrict_pattern'))
        self.assertEqual(sorted(inventory.list_hosts()),  sorted(['thor','odin']))

    @raises(errors.AnsibleError)
    def testinvalid_entry(self):
       Inventory('1234')

    ###################################################
    ### INI file advanced tests

    def test_complex_vars(self):
        inventory = self.complex_inventory()

        vars = inventory.get_variables('rtp_a')
        print vars

        expected = dict(
            a=1, b=2, c=3, d=10002, e=10003, f='10004 != 10005',
            g='  g  ', h='  h  ', i="'  i  \"", j='"  j',
            k=[ 'k1', 'k2' ],
            rga=1, rgb=2, rgc=3,
            inventory_hostname='rtp_a', inventory_hostname_short='rtp_a',
            group_names=[ 'eastcoast', 'nc', 'redundantgroup', 'redundantgroup2', 'redundantgroup3', 'rtp', 'us' ]
        )
        print vars
        print expected
        assert vars == expected

    def test_complex_group_names(self):
        inventory = self.complex_inventory()
        tests = {
            'host1': [ 'role1', 'role3' ],
            'host2': [ 'role1', 'role2' ],
            'host3': [ 'role2', 'role3' ]
        }
        for host, roles in tests.iteritems():
            group_names = inventory.get_variables(host)['group_names']
            assert sorted(group_names) == sorted(roles)

    def test_complex_exclude(self):
        inventory = self.complex_inventory()
        hosts = inventory.list_hosts("nc:florida:!triangle:!orlando")
        expected_hosts = ['miami', 'rtp_a', 'rtp_b', 'rtp_c']
        print "HOSTS=%s" % sorted(hosts)
        print "EXPECTED=%s" % sorted(expected_hosts)
        assert sorted(hosts) == sorted(expected_hosts)

    def test_regex_exclude(self):
        inventory = self.complex_inventory()
        hosts = inventory.list_hosts("~rtp_[ac]")
        expected_hosts = ['rtp_a', 'rtp_c']
        print "HOSTS=%s" % sorted(hosts)
        print "EXPECTED=%s" % sorted(expected_hosts)
        assert sorted(hosts) == sorted(expected_hosts)

    def test_complex_enumeration(self):


        expected1 = ['rtp_b']
        expected2 = ['rtp_a', 'rtp_b']
        expected3 = ['rtp_a', 'rtp_b', 'rtp_c', 'tri_a', 'tri_b', 'tri_c']
        expected4 = ['rtp_b', 'orlando' ]
        expected5 = ['blade-a-1']

        inventory = self.complex_inventory()
        hosts = inventory.list_hosts("nc[1]")
        self.compare(hosts, expected1, sort=False)
        hosts = inventory.list_hosts("nc[0-2]")
        self.compare(hosts, expected2, sort=False)
        hosts = inventory.list_hosts("nc[0-99999]")
        self.compare(hosts, expected3, sort=False)
        hosts = inventory.list_hosts("nc[1-2]:florida[0-1]")
        self.compare(hosts, expected4, sort=False)
        hosts = inventory.list_hosts("blade-a-1")
        self.compare(hosts, expected5, sort=False)

    def test_complex_intersect(self):
        inventory = self.complex_inventory()
        hosts = inventory.list_hosts("nc:&redundantgroup:!rtp_c")
        self.compare(hosts, ['rtp_a'])
        hosts = inventory.list_hosts("nc:&triangle:!tri_c")
        self.compare(hosts, ['tri_a', 'tri_b'])

    @raises(errors.AnsibleError)
    def test_invalid_range(self):
        Inventory(os.path.join(self.test_dir, 'inventory','test_incorrect_range'))

    @raises(errors.AnsibleError)
    def test_missing_end(self):
        Inventory(os.path.join(self.test_dir, 'inventory','test_missing_end'))

    @raises(errors.AnsibleError)
    def test_incorrect_format(self):
        Inventory(os.path.join(self.test_dir, 'inventory','test_incorrect_format'))

    @raises(errors.AnsibleError)
    def test_alpha_end_before_beg(self):
        Inventory(os.path.join(self.test_dir, 'inventory','test_alpha_end_before_beg'))

    def test_combined_range(self):
        i = Inventory(os.path.join(self.test_dir, 'inventory','test_combined_range'))
        hosts = i.list_hosts('test')
        expected_hosts=['host1A','host2A','host1B','host2B']
        assert sorted(hosts) == sorted(expected_hosts)

    def test_leading_range(self):
        i = Inventory(os.path.join(self.test_dir, 'inventory','test_leading_range'))
        hosts = i.list_hosts('test')
        expected_hosts=['1.host','2.host','A.host','B.host']
        assert sorted(hosts) == sorted(expected_hosts)

        hosts2 = i.list_hosts('test2')
        expected_hosts2=['1.host','2.host','3.host']
        assert sorted(hosts2) == sorted(expected_hosts2)

    ###################################################
    ### Inventory API tests

    def test_script(self):
        inventory = self.script_inventory()
        hosts = inventory.list_hosts()

        expected_hosts=['jupiter', 'saturn', 'zeus', 'hera', 'poseidon', 'thor', 'odin', 'loki']

        print "Expected: %s"%(expected_hosts)
        print "Got     : %s"%(hosts)
        assert sorted(hosts) == sorted(expected_hosts)

    def test_script_all(self):
        inventory = self.script_inventory()
        hosts = inventory.list_hosts('all')

        expected_hosts=['jupiter', 'saturn', 'zeus', 'hera', 'poseidon', 'thor', 'odin', 'loki']
        assert sorted(hosts) == sorted(expected_hosts)

    def test_script_norse(self):
        inventory = self.script_inventory()
        hosts = inventory.list_hosts("norse")

        expected_hosts=['thor', 'odin', 'loki']
        assert sorted(hosts) == sorted(expected_hosts)

    def test_script_combined(self):
        inventory = self.script_inventory()
        hosts = inventory.list_hosts("norse:greek")

        expected_hosts=['zeus', 'hera', 'poseidon', 'thor', 'odin', 'loki']
        assert sorted(hosts) == sorted(expected_hosts)

    def test_script_restrict(self):
        inventory = self.script_inventory()

        restricted_hosts = ['hera', 'poseidon', 'thor']
        expected_hosts=['zeus', 'hera', 'poseidon', 'thor', 'odin', 'loki']

        inventory.restrict_to(restricted_hosts)
        hosts = inventory.list_hosts("norse:greek")

        assert sorted(hosts) == sorted(restricted_hosts)

        inventory.lift_restriction()
        hosts = inventory.list_hosts("norse:greek")

        assert sorted(hosts) == sorted(expected_hosts)

    def test_script_vars(self):
        inventory = self.script_inventory()
        vars = inventory.get_variables('thor')

        print "VARS=%s" % vars

        assert vars == {'hammer':True,
                        'group_names': ['norse'],
                        'inventory_hostname': 'thor',
                        'inventory_hostname_short': 'thor'}

    def test_hosts_list(self):
        # Test the case when playbook 'hosts' var is a list.
        inventory = self.script_inventory()
        host_names = sorted(['thor', 'loki', 'odin'])       # Not sure if sorting is in the contract or not
        actual_hosts = inventory.get_hosts(host_names)
        actual_host_names = [host.name for host in actual_hosts]
        assert host_names == actual_host_names

    def test_script_multiple_groups(self):
        inventory = self.script_inventory()
        vars = inventory.get_variables('zeus')

        print "VARS=%s" % vars

        assert vars == {'inventory_hostname': 'zeus',
                        'inventory_hostname_short': 'zeus',
                        'group_names': ['greek', 'major-god']}

    def test_allows_equals_sign_in_var(self):
        inventory = self.simple_inventory()
        auth = inventory.get_variables('neptun')['auth']
        assert auth == 'YWRtaW46YWRtaW4='

    def test_dir_inventory(self):
        inventory = self.dir_inventory()

        host_vars = inventory.get_variables('zeus')

        expected_vars = {'inventory_hostname': 'zeus',
                         'inventory_hostname_short': 'zeus',
                         'group_names': ['greek', 'major-god', 'ungrouped'],
                         'var_a': '3#4'}

        print "HOST     VARS=%s" % host_vars
        print "EXPECTED VARS=%s" % expected_vars

        assert host_vars == expected_vars

    def test_dir_inventory_multiple_groups(self):
        inventory = self.dir_inventory()
        group_greek = inventory.get_hosts('greek')
        actual_host_names = [host.name for host in group_greek]
        print "greek : %s " % actual_host_names
        assert actual_host_names == ['zeus', 'morpheus']

    def test_dir_inventory_skip_extension(self):
        inventory = self.dir_inventory()
        assert 'skipme' not in [h.name for h in inventory.get_hosts()]

########NEW FILE########
__FILENAME__ = TestModules
# -*- coding: utf-8 -*-

import os
import ast
import unittest
from ansible import utils


class TestModules(unittest.TestCase):

    def list_all_modules(self):
        paths = utils.plugins.module_finder._get_paths()
        paths = [x for x in paths if os.path.isdir(x)]
        module_list = []
        for path in paths:
            for (dirpath, dirnames, filenames) in os.walk(path):
                for filename in filenames:
                    module_list.append(os.path.join(dirpath, filename))
        return module_list

    def test_ast_parse(self):
        module_list = self.list_all_modules()
        ERRORS = []
        # attempt to parse each module with ast
        for m in module_list:
            try:
                ast.parse(''.join(open(m)))
            except Exception, e:
                ERRORS.append((m, e))
        assert len(ERRORS) == 0, "get_docstring errors: %s" % ERRORS

########NEW FILE########
__FILENAME__ = TestModuleUtilsBasic
import os
import tempfile

import unittest
from nose.tools import raises

from ansible import errors
from ansible.module_common import ModuleReplacer
from ansible.utils import md5 as utils_md5

TEST_MODULE_DATA = """
from ansible.module_utils.basic import *

def get_module():
    return AnsibleModule(
        argument_spec = dict(),
        supports_check_mode = True,
        no_log = True,
    )

get_module()

"""

class TestModuleUtilsBasic(unittest.TestCase):
 
    def cleanup_temp_file(self, fd, path):
        try:
            os.close(fd)
            os.remove(path)
        except:
            pass

    def cleanup_temp_dir(self, path):
        try:
            os.rmdir(path)
        except:
            pass

    def setUp(self):
        # create a temporary file for the test module 
        # we're about to generate
        self.tmp_fd, self.tmp_path = tempfile.mkstemp()
        os.write(self.tmp_fd, TEST_MODULE_DATA)

        # template the module code and eval it
        module_data, module_style, shebang = ModuleReplacer().modify_module(self.tmp_path, {}, "", {})

        d = {}
        exec(module_data, d, d)
        self.module = d['get_module']()

        # module_utils/basic.py screws with CWD, let's save it and reset
        self.cwd = os.getcwd()

    def tearDown(self):
        self.cleanup_temp_file(self.tmp_fd, self.tmp_path)
        # Reset CWD back to what it was before basic.py changed it
        os.chdir(self.cwd)

    #################################################################################
    # run_command() tests

    # test run_command with a string command
    def test_run_command_string(self):
        (rc, out, err) = self.module.run_command("/bin/echo -n 'foo bar'")
        self.assertEqual(rc, 0)
        self.assertEqual(out, 'foo bar')
        (rc, out, err) = self.module.run_command("/bin/echo -n 'foo bar'", use_unsafe_shell=True)
        self.assertEqual(rc, 0)
        self.assertEqual(out, 'foo bar')

    # test run_command with an array of args (with both use_unsafe_shell=True|False)
    def test_run_command_args(self):
        (rc, out, err) = self.module.run_command(['/bin/echo', '-n', "foo bar"])
        self.assertEqual(rc, 0)
        self.assertEqual(out, 'foo bar')
        (rc, out, err) = self.module.run_command(['/bin/echo', '-n', "foo bar"], use_unsafe_shell=True)
        self.assertEqual(rc, 0)
        self.assertEqual(out, 'foo bar')

    # test run_command with leading environment variables
    @raises(SystemExit)
    def test_run_command_string_with_env_variables(self):
        self.module.run_command('FOO=bar /bin/echo -n "foo bar"')
        
    @raises(SystemExit)
    def test_run_command_args_with_env_variables(self):
        self.module.run_command(['FOO=bar', '/bin/echo', '-n', 'foo bar'])

    def test_run_command_string_unsafe_with_env_variables(self):
        (rc, out, err) = self.module.run_command('FOO=bar /bin/echo -n "foo bar"', use_unsafe_shell=True)
        self.assertEqual(rc, 0)
        self.assertEqual(out, 'foo bar')

    # test run_command with a command pipe (with both use_unsafe_shell=True|False)
    def test_run_command_string_unsafe_with_pipe(self):
        (rc, out, err) = self.module.run_command('echo "foo bar" | cat', use_unsafe_shell=True)
        self.assertEqual(rc, 0)
        self.assertEqual(out, 'foo bar\n')

    # test run_command with a shell redirect in (with both use_unsafe_shell=True|False)
    def test_run_command_string_unsafe_with_redirect_in(self):
        (rc, out, err) = self.module.run_command('cat << EOF\nfoo bar\nEOF', use_unsafe_shell=True)
        self.assertEqual(rc, 0)
        self.assertEqual(out, 'foo bar\n')

    # test run_command with a shell redirect out (with both use_unsafe_shell=True|False)
    def test_run_command_string_unsafe_with_redirect_out(self):
        tmp_fd, tmp_path = tempfile.mkstemp()
        try:
            (rc, out, err) = self.module.run_command('echo "foo bar" > %s' % tmp_path, use_unsafe_shell=True)
            self.assertEqual(rc, 0)
            self.assertTrue(os.path.exists(tmp_path))
            md5sum = utils_md5(tmp_path)
            self.assertEqual(md5sum, '5ceaa7ed396ccb8e959c02753cb4bd18')
        except:
            raise
        finally:
            self.cleanup_temp_file(tmp_fd, tmp_path)

    # test run_command with a double shell redirect out (append) (with both use_unsafe_shell=True|False)
    def test_run_command_string_unsafe_with_double_redirect_out(self):
        tmp_fd, tmp_path = tempfile.mkstemp()
        try:
            (rc, out, err) = self.module.run_command('echo "foo bar" >> %s' % tmp_path, use_unsafe_shell=True)
            self.assertEqual(rc, 0)
            self.assertTrue(os.path.exists(tmp_path))
            md5sum = utils_md5(tmp_path)
            self.assertEqual(md5sum, '5ceaa7ed396ccb8e959c02753cb4bd18')
        except:
            raise
        finally:
            self.cleanup_temp_file(tmp_fd, tmp_path)

    # test run_command with data
    def test_run_command_string_with_data(self):
        (rc, out, err) = self.module.run_command('cat', data='foo bar')
        self.assertEqual(rc, 0)
        self.assertEqual(out, 'foo bar\n')

    # test run_command with binary data
    def test_run_command_string_with_binary_data(self):
        (rc, out, err) = self.module.run_command('cat', data='\x41\x42\x43\x44', binary_data=True)
        self.assertEqual(rc, 0)
        self.assertEqual(out, 'ABCD')

    # test run_command with a cwd set
    def test_run_command_string_with_cwd(self):
        tmp_path = tempfile.mkdtemp()
        try:
            (rc, out, err) = self.module.run_command('pwd', cwd=tmp_path)
            self.assertEqual(rc, 0)
            self.assertTrue(os.path.exists(tmp_path))
            self.assertEqual(out.strip(), os.path.realpath(tmp_path))
        except:
            raise
        finally:
            self.cleanup_temp_dir(tmp_path)



########NEW FILE########
__FILENAME__ = TestPlayVarsFiles
#!/usr/bin/env python

import os
import shutil
from tempfile import mkstemp
from tempfile import mkdtemp
from ansible.playbook.play import Play
import ansible

import unittest
from nose.plugins.skip import SkipTest


class FakeCallBacks(object):
    def __init__(self):
        pass
    def on_vars_prompt(self):
        pass
    def on_import_for_host(self, host, filename):
        pass

class FakeInventory(object):
    def __init__(self):
        self.hosts = {}
    def basedir(self):
        return "."        
    def get_variables(self, host, vault_password=None):
        if host in self.hosts:
            return self.hosts[host]        
        else:
            return {}            

class FakePlayBook(object):
    def __init__(self):
        self.extra_vars = {}
        self.remote_user = None
        self.remote_port = None
        self.sudo = None
        self.sudo_user = None
        self.su = None
        self.su_user = None
        self.transport = None
        self.only_tags = None
        self.skip_tags = None
        self.VARS_CACHE = {}
        self.SETUP_CACHE = {}
        self.inventory = FakeInventory()
        self.callbacks = FakeCallBacks()

        self.VARS_CACHE['localhost'] = {}


class TestMe(unittest.TestCase):

    ########################################
    # BASIC FILE LOADING BEHAVIOR TESTS
    ########################################

    def test_play_constructor(self):
        # __init__(self, playbook, ds, basedir, vault_password=None)
        playbook = FakePlayBook()
        ds = { "hosts": "localhost"}
        basedir = "."
        play = Play(playbook, ds, basedir)

    def test_vars_file(self):

        # make a vars file
        fd, temp_path = mkstemp()
        f = open(temp_path, "wb")
        f.write("foo: bar\n")
        f.close()

        # create a play with a vars_file
        playbook = FakePlayBook()
        ds = { "hosts": "localhost",
               "vars_files": [temp_path]}
        basedir = "."
        play = Play(playbook, ds, basedir)
        os.remove(temp_path)

        # make sure the variable was loaded
        assert 'foo' in play.vars, "vars_file was not loaded into play.vars"
        assert play.vars['foo'] == 'bar', "foo was not set to bar in play.vars"

    def test_vars_file_nonlist_error(self):

        # make a vars file
        fd, temp_path = mkstemp()
        f = open(temp_path, "wb")
        f.write("foo: bar\n")
        f.close()

        # create a play with a string for vars_files
        playbook = FakePlayBook()
        ds = { "hosts": "localhost",
               "vars_files": temp_path}
        basedir = "."
        error_hit = False
        try:
            play = Play(playbook, ds, basedir)
        except:
            error_hit = True
        os.remove(temp_path)

        assert error_hit == True, "no error was thrown when vars_files was not a list"


    def test_multiple_vars_files(self):

        # make a vars file
        fd, temp_path = mkstemp()
        f = open(temp_path, "wb")
        f.write("foo: bar\n")
        f.close()

        # make a second vars file
        fd, temp_path2 = mkstemp()
        f = open(temp_path2, "wb")
        f.write("baz: bang\n")
        f.close()


        # create a play with two vars_files
        playbook = FakePlayBook()
        ds = { "hosts": "localhost",
               "vars_files": [temp_path, temp_path2]}
        basedir = "."
        play = Play(playbook, ds, basedir)
        os.remove(temp_path)
        os.remove(temp_path2)

        # make sure the variables were loaded
        assert 'foo' in play.vars, "vars_file was not loaded into play.vars"
        assert play.vars['foo'] == 'bar', "foo was not set to bar in play.vars"
        assert 'baz' in play.vars, "vars_file2 was not loaded into play.vars"
        assert play.vars['baz'] == 'bang', "baz was not set to bang in play.vars"

    def test_vars_files_first_found(self):

        # make a vars file
        fd, temp_path = mkstemp()
        f = open(temp_path, "wb")
        f.write("foo: bar\n")
        f.close()

        # get a random file path        
        fd, temp_path2 = mkstemp()
        # make sure this file doesn't exist
        os.remove(temp_path2)

        # create a play
        playbook = FakePlayBook()
        ds = { "hosts": "localhost",
               "vars_files": [[temp_path2, temp_path]]}
        basedir = "."
        play = Play(playbook, ds, basedir)
        os.remove(temp_path)

        # make sure the variable was loaded
        assert 'foo' in play.vars, "vars_file was not loaded into play.vars"
        assert play.vars['foo'] == 'bar', "foo was not set to bar in play.vars"

    def test_vars_files_multiple_found(self):

        # make a vars file
        fd, temp_path = mkstemp()
        f = open(temp_path, "wb")
        f.write("foo: bar\n")
        f.close()

        # make a second vars file
        fd, temp_path2 = mkstemp()
        f = open(temp_path2, "wb")
        f.write("baz: bang\n")
        f.close()

        # create a play
        playbook = FakePlayBook()
        ds = { "hosts": "localhost",
               "vars_files": [[temp_path, temp_path2]]}
        basedir = "."
        play = Play(playbook, ds, basedir)
        os.remove(temp_path)
        os.remove(temp_path2)

        # make sure the variables were loaded
        assert 'foo' in play.vars, "vars_file was not loaded into play.vars"
        assert play.vars['foo'] == 'bar', "foo was not set to bar in play.vars"
        assert 'baz' not in play.vars, "vars_file2 was loaded after vars_file1 was loaded"

    def test_vars_files_assert_all_found(self):

        # make a vars file
        fd, temp_path = mkstemp()
        f = open(temp_path, "wb")
        f.write("foo: bar\n")
        f.close()

        # make a second vars file
        fd, temp_path2 = mkstemp()
        # make sure it doesn't exist
        os.remove(temp_path2)

        # create a play
        playbook = FakePlayBook()
        ds = { "hosts": "localhost",
               "vars_files": [temp_path, temp_path2]}
        basedir = "."

        error_hit = False
        error_msg = None

        try:
            play = Play(playbook, ds, basedir)
        except ansible.errors.AnsibleError, e:
            error_hit = True
            error_msg = e

        os.remove(temp_path)
        assert error_hit == True, "no error was thrown for missing vars_file"


    ########################################
    # VARIABLE PRECEDENCE TESTS
    ########################################

    # On the first run vars_files are loaded into play.vars by host == None
    #   * only files with vars from host==None will work here
    # On the secondary run(s), a host is given and the vars_files are loaded into VARS_CACHE
    #   * this only occurs if host is not None, filename2 has vars in the name, and filename3 does not

    # filename  -- the original string
    # filename2 -- filename templated with play vars
    # filename3 -- filename2 template with inject (hostvars + setup_cache + vars_cache)
    # filename4 -- path_dwim(filename3)

    def test_vars_files_for_host(self):

        # host != None
        # vars in filename2
        # no vars in filename3

        # make a vars file
        fd, temp_path = mkstemp()
        f = open(temp_path, "wb")
        f.write("foo: bar\n")
        f.close()

        # build play attributes
        playbook = FakePlayBook()
        ds = { "hosts": "localhost",
               "vars_files": ["{{ temp_path }}"]}
        basedir = "."
        playbook.VARS_CACHE['localhost']['temp_path'] = temp_path

        # create play and do first run        
        play = Play(playbook, ds, basedir)

        # the second run is started by calling update_vars_files        
        play.update_vars_files(['localhost'])
        os.remove(temp_path)

        assert 'foo' in play.playbook.VARS_CACHE['localhost'], "vars_file vars were not loaded into vars_cache"
        assert play.playbook.VARS_CACHE['localhost']['foo'] == 'bar', "foo does not equal bar"

    def test_vars_files_for_host_with_extra_vars(self):

        # host != None
        # vars in filename2
        # no vars in filename3

        # make a vars file
        fd, temp_path = mkstemp()
        f = open(temp_path, "wb")
        f.write("foo: bar\n")
        f.close()

        # build play attributes
        playbook = FakePlayBook()
        ds = { "hosts": "localhost",
               "vars_files": ["{{ temp_path }}"]}
        basedir = "."
        playbook.VARS_CACHE['localhost']['temp_path'] = temp_path
        playbook.extra_vars = {"foo": "extra"}

        # create play and do first run        
        play = Play(playbook, ds, basedir)

        # the second run is started by calling update_vars_files        
        play.update_vars_files(['localhost'])
        os.remove(temp_path)

        assert 'foo' in play.vars, "extra vars were not set in play.vars"
        assert 'foo' in play.playbook.VARS_CACHE['localhost'], "vars_file vars were not loaded into vars_cache"
        assert play.playbook.VARS_CACHE['localhost']['foo'] == 'extra', "extra vars did not overwrite vars_files vars"


    ########################################
    # COMPLEX FILENAME TEMPLATING TESTS
    ########################################

    def test_vars_files_two_vars_in_name(self):

        # self.vars = ds['vars']
        # self.vars += _get_vars() ... aka extra_vars

        # make a temp dir
        temp_dir = mkdtemp()

        # make a temp file
        fd, temp_file = mkstemp(dir=temp_dir)
        f = open(temp_file, "wb")
        f.write("foo: bar\n")
        f.close()

        # build play attributes
        playbook = FakePlayBook()
        ds = { "hosts": "localhost",
               "vars": { "temp_dir": os.path.dirname(temp_file),
                         "temp_file": os.path.basename(temp_file) },
               "vars_files": ["{{ temp_dir + '/' + temp_file }}"]}
        basedir = "."

        # create play and do first run        
        play = Play(playbook, ds, basedir)

        # cleanup
        shutil.rmtree(temp_dir)

        assert 'foo' in play.vars, "double var templated vars_files filename not loaded"
    
    def test_vars_files_two_vars_different_scope(self):

        #
        # Use a play var and an inventory var to create the filename
        #

        # self.playbook.inventory.get_variables(host)
        #   {'group_names': ['ungrouped'], 'inventory_hostname': 'localhost', 
        #   'ansible_ssh_user': 'root', 'inventory_hostname_short': 'localhost'}

        # make a temp dir
        temp_dir = mkdtemp()

        # make a temp file
        fd, temp_file = mkstemp(dir=temp_dir)
        f = open(temp_file, "wb")
        f.write("foo: bar\n")
        f.close()

        # build play attributes
        playbook = FakePlayBook()
        playbook.inventory.hosts['localhost'] = {'inventory_hostname': os.path.basename(temp_file)}
        ds = { "hosts": "localhost",
               "vars": { "temp_dir": os.path.dirname(temp_file)},
               "vars_files": ["{{ temp_dir + '/' + inventory_hostname }}"]}
        basedir = "."

        # create play and do first run        
        play = Play(playbook, ds, basedir)

        # do the host run        
        play.update_vars_files(['localhost'])

        # cleanup
        shutil.rmtree(temp_dir)

        assert 'foo' not in play.vars, \
            "mixed scope vars_file loaded into play vars"
        assert 'foo' in play.playbook.VARS_CACHE['localhost'], \
            "differently scoped templated vars_files filename not loaded"
        assert play.playbook.VARS_CACHE['localhost']['foo'] == 'bar', \
            "foo is not bar"    

    def test_vars_files_two_vars_different_scope_first_found(self):

        #
        # Use a play var and an inventory var to create the filename
        #

        # make a temp dir
        temp_dir = mkdtemp()

        # make a temp file
        fd, temp_file = mkstemp(dir=temp_dir)
        f = open(temp_file, "wb")
        f.write("foo: bar\n")
        f.close()

        # build play attributes
        playbook = FakePlayBook()
        playbook.inventory.hosts['localhost'] = {'inventory_hostname': os.path.basename(temp_file)}
        ds = { "hosts": "localhost",
               "vars": { "temp_dir": os.path.dirname(temp_file)},
               "vars_files": [["{{ temp_dir + '/' + inventory_hostname }}"]]}
        basedir = "."

        # create play and do first run        
        play = Play(playbook, ds, basedir)

        # do the host run        
        play.update_vars_files(['localhost'])

        # cleanup
        shutil.rmtree(temp_dir)

        assert 'foo' not in play.vars, \
            "mixed scope vars_file loaded into play vars"
        assert 'foo' in play.playbook.VARS_CACHE['localhost'], \
            "differently scoped templated vars_files filename not loaded"
        assert play.playbook.VARS_CACHE['localhost']['foo'] == 'bar', \
            "foo is not bar"    
    


########NEW FILE########
__FILENAME__ = TestSynchronize

import unittest
import getpass
import os
import shutil
import time
import tempfile
from nose.plugins.skip import SkipTest

from ansible.runner.action_plugins.synchronize import ActionModule as Synchronize

class FakeRunner(object):
    def __init__(self):
        self.connection = None
        self.transport = None
        self.basedir = None
        self.sudo = None
        self.remote_user = None
        self.private_key_file = None
        self.check = False

    def _execute_module(self, conn, tmp, module_name, args,
        async_jid=None, async_module=None, async_limit=None, inject=None, 
        persist_files=False, complex_args=None, delete_remote_tmp=True):
        self.executed_conn = conn
        self.executed_tmp = tmp
        self.executed_module_name = module_name
        self.executed_args = args
        self.executed_async_jid = async_jid
        self.executed_async_module = async_module
        self.executed_async_limit = async_limit
        self.executed_inject = inject
        self.executed_persist_files = persist_files
        self.executed_complex_args = complex_args
        self.executed_delete_remote_tmp = delete_remote_tmp

    def noop_on_check(self, inject):
        return self.check

class FakeConn(object):
    def __init__(self):
        self.host = None
        self.delegate = None

class TestSynchronize(unittest.TestCase):


    def test_synchronize_action_basic(self):

        """ verify the synchronize action plugin sets 
            the delegate to 127.0.0.1 and remote path to user@host:/path """

        runner = FakeRunner()
        runner.remote_user = "root"
        runner.transport = "ssh"
        conn = FakeConn()
        inject = {
                    'inventory_hostname': "el6.lab.net",
                    'inventory_hostname_short': "el6",
                    'ansible_connection': None,
                    'ansible_ssh_user': 'root',
                    'delegate_to': None,
                    'playbook_dir': '.',
                 }

        x = Synchronize(runner)
        x.setup("synchronize", inject)
        x.run(conn, "/tmp", "synchronize", "src=/tmp/foo dest=/tmp/bar", inject)

        assert runner.executed_inject['delegate_to'] == "127.0.0.1", "was not delegated to 127.0.0.1"
        assert runner.executed_complex_args == {"dest":"root@el6.lab.net:/tmp/bar", "src":"/tmp/foo"}, "wrong args used"
        assert runner.sudo == None, "sudo was not reset to None" 

    def test_synchronize_action_sudo(self):

        """ verify the synchronize action plugin unsets and then sets sudo """ 

        runner = FakeRunner()
        runner.sudo = True
        runner.remote_user = "root"
        runner.transport = "ssh"
        conn = FakeConn()
        inject = {
                    'inventory_hostname': "el6.lab.net",
                    'inventory_hostname_short': "el6",
                    'ansible_connection': None,
                    'ansible_ssh_user': 'root',
                    'delegate_to': None,
                    'playbook_dir': '.',
                 }

        x = Synchronize(runner)
        x.setup("synchronize", inject)
        x.run(conn, "/tmp", "synchronize", "src=/tmp/foo dest=/tmp/bar", inject)

        assert runner.executed_inject['delegate_to'] == "127.0.0.1", "was not delegated to 127.0.0.1"
        assert runner.executed_complex_args == {'dest':'root@el6.lab.net:/tmp/bar',
                                                'src':'/tmp/foo',
                                                'rsync_path':'"sudo rsync"'}, "wrong args used"
        assert runner.sudo == True, "sudo was not reset to True" 


    def test_synchronize_action_local(self):

        """ verify the synchronize action plugin sets 
            the delegate to 127.0.0.1 and does not alter the dest """

        runner = FakeRunner()
        runner.remote_user = "jtanner"
        runner.transport = "paramiko"
        conn = FakeConn()
        conn.host = "127.0.0.1"
        conn.delegate = "thishost"
        inject = {
                    'inventory_hostname': "thishost",
                    'ansible_ssh_host': '127.0.0.1',
                    'ansible_connection': 'local',
                    'delegate_to': None,
                    'playbook_dir': '.',
                 }

        x = Synchronize(runner)
        x.setup("synchronize", inject)
        x.run(conn, "/tmp", "synchronize", "src=/tmp/foo dest=/tmp/bar", inject)

        assert runner.transport == "paramiko", "runner transport was changed"
        assert runner.remote_user == "jtanner", "runner remote_user was changed"
        assert runner.executed_inject['delegate_to'] == "127.0.0.1", "was not delegated to 127.0.0.1"
        assert "dest_port" not in runner.executed_complex_args, "dest_port should not have been set"
        assert runner.executed_complex_args.get("src") == "/tmp/foo", "source was set incorrectly"
        assert runner.executed_complex_args.get("dest") == "/tmp/bar", "dest was set incorrectly"


    def test_synchronize_action_vagrant(self):

        """ Verify the action plugin accomodates the common 
            scenarios for vagrant boxes. """

        runner = FakeRunner()
        runner.remote_user = "jtanner"
        runner.transport = "ssh"
        conn = FakeConn()
        conn.host = "127.0.0.1"
        conn.delegate = "thishost"
        inject = {
                    'inventory_hostname': "thishost",
                    'ansible_ssh_user': 'vagrant',
                    'ansible_ssh_host': '127.0.0.1',
                    'ansible_ssh_port': '2222',
                    'delegate_to': None,
                    'playbook_dir': '.',
                    'hostvars': {
                        'thishost': {
                            'inventory_hostname': 'thishost',
                            'ansible_ssh_port': '2222',
                            'ansible_ssh_host': '127.0.0.1',
                            'ansible_ssh_user': 'vagrant'
                        }
                    }
                 }

        x = Synchronize(runner)
        x.setup("synchronize", inject)
        x.run(conn, "/tmp", "synchronize", "src=/tmp/foo dest=/tmp/bar", inject)

        assert runner.transport == "ssh", "runner transport was changed"
        assert runner.remote_user == "jtanner", "runner remote_user was changed"
        assert runner.executed_inject['delegate_to'] == "127.0.0.1", "was not delegated to 127.0.0.1"
        assert runner.executed_inject['ansible_ssh_user'] == "vagrant", "runner user was changed"
        assert runner.executed_complex_args.get("dest_port") == "2222", "remote port was not set to 2222"
        assert runner.executed_complex_args.get("src") == "/tmp/foo", "source was set incorrectly"
        assert runner.executed_complex_args.get("dest") == "vagrant@127.0.0.1:/tmp/bar", "dest was set incorrectly"


########NEW FILE########
__FILENAME__ = TestUtils
# -*- coding: utf-8 -*-

import unittest
import os
import os.path
import re
import tempfile
import yaml
import passlib.hash
import string
import StringIO
import copy

from nose.plugins.skip import SkipTest

import ansible.utils
import ansible.errors
import ansible.constants as C
import ansible.utils.template as template2

from ansible import __version__

import sys
reload(sys)
sys.setdefaultencoding("utf8") 

class TestUtils(unittest.TestCase):

    def test_before_comment(self):
        ''' see if we can detect the part of a string before a comment.  Used by INI parser in inventory '''
 
        input    = "before # comment"
        expected = "before "
        actual   = ansible.utils.before_comment(input)
        self.assertEqual(expected, actual)

        input    = "before \# not a comment"
        expected = "before # not a comment"
        actual  =  ansible.utils.before_comment(input)
        self.assertEqual(expected, actual)

        input = ""
        expected = ""
        actual = ansible.utils.before_comment(input)
        self.assertEqual(expected, actual)

        input = "#"
        expected = ""
        actual = ansible.utils.before_comment(input)
        self.assertEqual(expected, actual)

    #####################################
    ### check_conditional tests

    def test_check_conditional_jinja2_literals(self):
        # see http://jinja.pocoo.org/docs/templates/#literals

        # none
        self.assertEqual(ansible.utils.check_conditional(
            None, '/', {}), True)
        self.assertEqual(ansible.utils.check_conditional(
            '', '/', {}), True)

        # list
        self.assertEqual(ansible.utils.check_conditional(
            ['true'], '/', {}), True)
        self.assertEqual(ansible.utils.check_conditional(
            ['false'], '/', {}), False)

        # non basestring or list
        self.assertEqual(ansible.utils.check_conditional(
            {}, '/', {}), {})

        # boolean
        self.assertEqual(ansible.utils.check_conditional(
            'true', '/', {}), True)
        self.assertEqual(ansible.utils.check_conditional(
            'false', '/', {}), False)
        self.assertEqual(ansible.utils.check_conditional(
            'True', '/', {}), True)
        self.assertEqual(ansible.utils.check_conditional(
            'False', '/', {}), False)

        # integer
        self.assertEqual(ansible.utils.check_conditional(
            '1', '/', {}), True)
        self.assertEqual(ansible.utils.check_conditional(
            '0', '/', {}), False)

        # string, beware, a string is truthy unless empty
        self.assertEqual(ansible.utils.check_conditional(
            '"yes"', '/', {}), True)
        self.assertEqual(ansible.utils.check_conditional(
            '"no"', '/', {}), True)
        self.assertEqual(ansible.utils.check_conditional(
            '""', '/', {}), False)


    def test_check_conditional_jinja2_variable_literals(self):
        # see http://jinja.pocoo.org/docs/templates/#literals

        # boolean
        self.assertEqual(ansible.utils.check_conditional(
            'var', '/', {'var': 'True'}), True)
        self.assertEqual(ansible.utils.check_conditional(
            'var', '/', {'var': 'true'}), True)
        self.assertEqual(ansible.utils.check_conditional(
            'var', '/', {'var': 'False'}), False)
        self.assertEqual(ansible.utils.check_conditional(
            'var', '/', {'var': 'false'}), False)

        # integer
        self.assertEqual(ansible.utils.check_conditional(
            'var', '/', {'var': '1'}), True)
        self.assertEqual(ansible.utils.check_conditional(
            'var', '/', {'var': 1}), True)
        self.assertEqual(ansible.utils.check_conditional(
            'var', '/', {'var': '0'}), False)
        self.assertEqual(ansible.utils.check_conditional(
            'var', '/', {'var': 0}), False)

        # string, beware, a string is truthy unless empty
        self.assertEqual(ansible.utils.check_conditional(
            'var', '/', {'var': '"yes"'}), True)
        self.assertEqual(ansible.utils.check_conditional(
            'var', '/', {'var': '"no"'}), True)
        self.assertEqual(ansible.utils.check_conditional(
            'var', '/', {'var': '""'}), False)

        # Python boolean in Jinja2 expression
        self.assertEqual(ansible.utils.check_conditional(
            'var', '/', {'var': True}), True)
        self.assertEqual(ansible.utils.check_conditional(
            'var', '/', {'var': False}), False)


    def test_check_conditional_jinja2_expression(self):
        self.assertEqual(ansible.utils.check_conditional(
            '1 == 1', '/', {}), True)
        self.assertEqual(ansible.utils.check_conditional(
            'bar == 42', '/', {'bar': 42}), True)
        self.assertEqual(ansible.utils.check_conditional(
            'bar != 42', '/', {'bar': 42}), False)


    def test_check_conditional_jinja2_expression_in_variable(self):
        self.assertEqual(ansible.utils.check_conditional(
            'var', '/', {'var': '1 == 1'}), True)
        self.assertEqual(ansible.utils.check_conditional(
            'var', '/', {'var': 'bar == 42', 'bar': 42}), True)
        self.assertEqual(ansible.utils.check_conditional(
            'var', '/', {'var': 'bar != 42', 'bar': 42}), False)

    def test_check_conditional_jinja2_unicode(self):
        self.assertEqual(ansible.utils.check_conditional(
            u'"\u00df"', '/', {}), True)
        self.assertEqual(ansible.utils.check_conditional(
            u'var == "\u00df"', '/', {'var': u'\u00df'}), True)


    #####################################
    ### key-value parsing

    def test_parse_kv_basic(self):
        self.assertEqual(ansible.utils.parse_kv('a=simple b="with space" c="this=that"'),
                {'a': 'simple', 'b': 'with space', 'c': 'this=that'})


    def test_jsonify(self):
        self.assertEqual(ansible.utils.jsonify(None), '{}')
        self.assertEqual(ansible.utils.jsonify(dict(foo='bar', baz=['qux'])),
               '{"baz": ["qux"], "foo": "bar"}')
        expected = '''{
    "baz": [
        "qux"
    ], 
    "foo": "bar"
}'''
        self.assertEqual(ansible.utils.jsonify(dict(foo='bar', baz=['qux']), format=True), expected)

    def test_is_failed(self):
        self.assertEqual(ansible.utils.is_failed(dict(rc=0)), False)
        self.assertEqual(ansible.utils.is_failed(dict(rc=1)), True)
        self.assertEqual(ansible.utils.is_failed(dict()), False)
        self.assertEqual(ansible.utils.is_failed(dict(failed=False)), False)
        self.assertEqual(ansible.utils.is_failed(dict(failed=True)), True)
        self.assertEqual(ansible.utils.is_failed(dict(failed='True')), True)
        self.assertEqual(ansible.utils.is_failed(dict(failed='true')), True)

    def test_is_changed(self):
        self.assertEqual(ansible.utils.is_changed(dict()), False)
        self.assertEqual(ansible.utils.is_changed(dict(changed=False)), False)
        self.assertEqual(ansible.utils.is_changed(dict(changed=True)), True)
        self.assertEqual(ansible.utils.is_changed(dict(changed='True')), True)
        self.assertEqual(ansible.utils.is_changed(dict(changed='true')), True)

    def test_path_dwim(self):
        self.assertEqual(ansible.utils.path_dwim(None, __file__),
               __file__)
        self.assertEqual(ansible.utils.path_dwim(None, '~'),
               os.path.expanduser('~'))
        self.assertEqual(ansible.utils.path_dwim(None, 'TestUtils.py'),
               __file__.rstrip('c'))

    def test_path_dwim_relative(self):
        self.assertEqual(ansible.utils.path_dwim_relative(__file__, 'units', 'TestUtils.py',
                                                          os.path.dirname(os.path.dirname(__file__))),
               __file__.rstrip('c'))

    def test_json_loads(self):
        self.assertEqual(ansible.utils.json_loads('{"foo": "bar"}'), dict(foo='bar'))

    def test_parse_json(self):
        # leading junk
        self.assertEqual(ansible.utils.parse_json('ansible\n{"foo": "bar"}'), dict(foo="bar"))

        # "baby" json
        self.assertEqual(ansible.utils.parse_json('foo=bar baz=qux'), dict(foo='bar', baz='qux'))

        # No closing quotation
        try:
            ansible.utils.parse_json('foo=bar "')
        except ValueError:
            pass
        else:
            raise AssertionError('Incorrect exception, expected ValueError')

        # Failed to parse
        try:
            ansible.utils.parse_json('{')
        except ansible.errors.AnsibleError:
            pass
        else:
            raise AssertionError('Incorrect exception, expected ansible.errors.AnsibleError')

        # boolean changed/failed
        self.assertEqual(ansible.utils.parse_json('changed=true'), dict(changed=True))
        self.assertEqual(ansible.utils.parse_json('changed=false'), dict(changed=False))
        self.assertEqual(ansible.utils.parse_json('failed=true'), dict(failed=True))
        self.assertEqual(ansible.utils.parse_json('failed=false'), dict(failed=False))

        # rc
        self.assertEqual(ansible.utils.parse_json('rc=0'), dict(rc=0))

        # Just a string
        self.assertEqual(ansible.utils.parse_json('foo'), dict(failed=True, parsed=False, msg='foo'))

    def test_smush_braces(self):
        self.assertEqual(ansible.utils.smush_braces('{{ foo}}'), '{{foo}}')
        self.assertEqual(ansible.utils.smush_braces('{{foo }}'), '{{foo}}')
        self.assertEqual(ansible.utils.smush_braces('{{ foo }}'), '{{foo}}')

    def test_smush_ds(self):
        # list
        self.assertEqual(ansible.utils.smush_ds(['foo={{ foo }}']), ['foo={{foo}}'])

        # dict
        self.assertEqual(ansible.utils.smush_ds(dict(foo='{{ foo }}')), dict(foo='{{foo}}'))

        # string
        self.assertEqual(ansible.utils.smush_ds('foo={{ foo }}'), 'foo={{foo}}')

        # int
        self.assertEqual(ansible.utils.smush_ds(0), 0)

    def test_parse_yaml(self):
        #json
        self.assertEqual(ansible.utils.parse_yaml('{"foo": "bar"}'), dict(foo='bar'))

        # broken json
        try:
            ansible.utils.parse_yaml('{')
        except ansible.errors.AnsibleError:
            pass
        else:
            raise AssertionError

        # broken json with path_hint
        try:
            ansible.utils.parse_yaml('{', path_hint='foo')
        except ansible.errors.AnsibleError:
            pass
        else:
            raise AssertionError

        # yaml with front-matter
        self.assertEqual(ansible.utils.parse_yaml("---\nfoo: bar"), dict(foo='bar'))
        # yaml no front-matter
        self.assertEqual(ansible.utils.parse_yaml('foo: bar'), dict(foo='bar'))
        # yaml indented first line (See #6348)
        self.assertEqual(ansible.utils.parse_yaml(' - foo: bar\n   baz: qux'), [dict(foo='bar', baz='qux')])

    def test_process_common_errors(self):
        # no quote
        self.assertTrue('YAML thought it' in ansible.utils.process_common_errors('', 'foo: {{bar}}', 6))

        # extra colon
        self.assertTrue('an extra unquoted colon' in ansible.utils.process_common_errors('', 'foo: bar:', 8))

        # match
        self.assertTrue('same kind of quote' in ansible.utils.process_common_errors('', 'foo: "{{bar}}"baz', 6))
        self.assertTrue('same kind of quote' in ansible.utils.process_common_errors('', "foo: '{{bar}}'baz", 6))

        # unbalanced
        self.assertTrue('We could be wrong' in ansible.utils.process_common_errors('', 'foo: "bad" "wolf"', 6))
        self.assertTrue('We could be wrong' in ansible.utils.process_common_errors('', "foo: 'bad' 'wolf'", 6))


    def test_process_yaml_error(self):
        data = 'foo: bar\n baz: qux'
        try:
            ansible.utils.parse_yaml(data)
        except yaml.YAMLError, exc:
            try:
                ansible.utils.process_yaml_error(exc, data, __file__)
            except ansible.errors.AnsibleYAMLValidationFailed, e:
                self.assertTrue('Syntax Error while loading' in e.msg)
            else:
                raise AssertionError('Incorrect exception, expected AnsibleYAMLValidationFailed')

        data = 'foo: bar\n baz: {{qux}}'
        try:
            ansible.utils.parse_yaml(data)
        except yaml.YAMLError, exc:
            try:
                ansible.utils.process_yaml_error(exc, data, __file__)
            except ansible.errors.AnsibleYAMLValidationFailed, e:
                self.assertTrue('Syntax Error while loading' in e.msg)
            else:
                raise AssertionError('Incorrect exception, expected AnsibleYAMLValidationFailed')

        data = '\xFF'
        try:
            ansible.utils.parse_yaml(data)
        except yaml.YAMLError, exc:
            try:
                ansible.utils.process_yaml_error(exc, data, __file__)
            except ansible.errors.AnsibleYAMLValidationFailed, e:
                self.assertTrue('Check over' in e.msg)
            else:
                raise AssertionError('Incorrect exception, expected AnsibleYAMLValidationFailed')

        data = '\xFF'
        try:
            ansible.utils.parse_yaml(data)
        except yaml.YAMLError, exc:
            try:
                ansible.utils.process_yaml_error(exc, data, None)
            except ansible.errors.AnsibleYAMLValidationFailed, e:
                self.assertTrue('Could not parse YAML.' in e.msg)
            else:
                raise AssertionError('Incorrect exception, expected AnsibleYAMLValidationFailed')

    def test_parse_yaml_from_file(self):
        test = os.path.join(os.path.dirname(__file__), 'inventory_test_data',
                            'common_vars.yml')
        encrypted = os.path.join(os.path.dirname(__file__), 'inventory_test_data',
                                 'encrypted.yml')
        broken = os.path.join(os.path.dirname(__file__), 'inventory_test_data',
                              'broken.yml')

        try:
            ansible.utils.parse_yaml_from_file(os.path.dirname(__file__))
        except ansible.errors.AnsibleError:
            pass
        else:
            raise AssertionError('Incorrect exception, expected AnsibleError')

        self.assertEqual(ansible.utils.parse_yaml_from_file(test), yaml.safe_load(open(test)))

        self.assertEqual(ansible.utils.parse_yaml_from_file(encrypted, 'ansible'), dict(foo='bar'))

        try:
            ansible.utils.parse_yaml_from_file(broken)
        except ansible.errors.AnsibleYAMLValidationFailed, e:
            self.assertTrue('Syntax Error while loading' in e.msg)
        else:
            raise AssertionError('Incorrect exception, expected AnsibleYAMLValidationFailed')

    def test_merge_hash(self):
        self.assertEqual(ansible.utils.merge_hash(dict(foo='bar', baz='qux'), dict(foo='baz')),
               dict(foo='baz', baz='qux'))
        self.assertEqual(ansible.utils.merge_hash(dict(foo=dict(bar='baz')), dict(foo=dict(bar='qux'))),
               dict(foo=dict(bar='qux')))

    def test_md5s(self):
        self.assertEqual(ansible.utils.md5s('ansible'), '640c8a5376aa12fa15cf02130ce239a6')
        # Need a test that causes UnicodeEncodeError See 4221

    def test_md5(self):
        self.assertEqual(ansible.utils.md5(os.path.join(os.path.dirname(__file__), 'ansible.cfg')),
                         'fb7b5b90ea63f04bde33e804b6fad42c')
        self.assertEqual(ansible.utils.md5(os.path.join(os.path.dirname(__file__), 'ansible.cf')),
                         None)

    def test_default(self):
        self.assertEqual(ansible.utils.default(None, lambda: {}), {})
        self.assertEqual(ansible.utils.default(dict(foo='bar'), lambda: {}), dict(foo='bar'))

    def test__gitinfo(self):
        # this fails if not run from git clone
        # self.assertEqual('last updated' in ansible.utils._gitinfo())
        # missing test for git submodule
        # missing test outside of git clone
        pass

    def test_version(self):
        version = ansible.utils.version('ansible')
        self.assertTrue(version.startswith('ansible %s' % __version__))
        # this fails if not run from git clone
        # self.assertEqual('last updated' in version)

    def test_getch(self):
        # figure out how to test this
        pass

    def test_sanitize_output(self):
        self.assertEqual(ansible.utils.sanitize_output('password=foo'), 'password=VALUE_HIDDEN')
        self.assertEqual(ansible.utils.sanitize_output('foo=user:pass@foo/whatever'),
                         'foo=user:********@foo/whatever')
        self.assertEqual(ansible.utils.sanitize_output('foo=http://username:pass@wherever/foo'),
                         'foo=http://username:********@wherever/foo')
        self.assertEqual(ansible.utils.sanitize_output('foo=http://wherever/foo'),
                         'foo=http://wherever/foo')

    def test_increment_debug(self):
        ansible.utils.VERBOSITY = 0
        ansible.utils.increment_debug(None, None, None, None)
        self.assertEqual(ansible.utils.VERBOSITY, 1)

    def test_base_parser(self):
        output = ansible.utils.base_parser(output_opts=True)
        self.assertTrue(output.has_option('--one-line') and output.has_option('--tree'))

        runas = ansible.utils.base_parser(runas_opts=True)
        for opt in ['--sudo', '--sudo-user', '--user', '--su', '--su-user']:
            self.assertTrue(runas.has_option(opt))

        async = ansible.utils.base_parser(async_opts=True)
        self.assertTrue(async.has_option('--poll') and async.has_option('--background'))

        connect = ansible.utils.base_parser(connect_opts=True)
        self.assertTrue(connect.has_option('--connection'))

        subset = ansible.utils.base_parser(subset_opts=True)
        self.assertTrue(subset.has_option('--limit'))

        check = ansible.utils.base_parser(check_opts=True)
        self.assertTrue(check.has_option('--check'))

        diff = ansible.utils.base_parser(diff_opts=True)
        self.assertTrue(diff.has_option('--diff'))

    def test_do_encrypt(self):
        salt_chars = string.ascii_letters + string.digits + './'
        salt = ansible.utils.random_password(length=8, chars=salt_chars)
        hash = ansible.utils.do_encrypt('ansible', 'sha256_crypt', salt=salt)
        self.assertTrue(passlib.hash.sha256_crypt.verify('ansible', hash))

        hash = ansible.utils.do_encrypt('ansible', 'sha256_crypt')
        self.assertTrue(passlib.hash.sha256_crypt.verify('ansible', hash))

        hash = ansible.utils.do_encrypt('ansible', 'md5_crypt', salt_size=4)
        self.assertTrue(passlib.hash.md5_crypt.verify('ansible', hash))


        try:
            ansible.utils.do_encrypt('ansible', 'ansible')
        except ansible.errors.AnsibleError:
            pass
        else:
            raise AssertionError('Incorrect exception, expected AnsibleError')

    def test_last_non_blank_line(self):
        self.assertEqual(ansible.utils.last_non_blank_line('a\n\nb\n\nc'), 'c')
        self.assertEqual(ansible.utils.last_non_blank_line(''), '')

    def test_filter_leading_non_json_lines(self):
        self.assertEqual(ansible.utils.filter_leading_non_json_lines('a\nb\nansible!\n{"foo": "bar"}'),
                         '{"foo": "bar"}\n')
        self.assertEqual(ansible.utils.filter_leading_non_json_lines('a\nb\nansible!\n["foo", "bar"]'),
                         '["foo", "bar"]\n')
        self.assertEqual(ansible.utils.filter_leading_non_json_lines('a\nb\nansible!\nfoo=bar'),
                         'foo=bar\n')

    def test_boolean(self):
        self.assertEqual(ansible.utils.boolean("true"), True)
        self.assertEqual(ansible.utils.boolean("True"), True)
        self.assertEqual(ansible.utils.boolean("TRUE"), True)
        self.assertEqual(ansible.utils.boolean("t"), True)
        self.assertEqual(ansible.utils.boolean("T"), True)
        self.assertEqual(ansible.utils.boolean("Y"), True)
        self.assertEqual(ansible.utils.boolean("y"), True)
        self.assertEqual(ansible.utils.boolean("1"), True)
        self.assertEqual(ansible.utils.boolean(1), True)
        self.assertEqual(ansible.utils.boolean("false"), False)
        self.assertEqual(ansible.utils.boolean("False"), False)
        self.assertEqual(ansible.utils.boolean("0"), False)
        self.assertEqual(ansible.utils.boolean(0), False)
        self.assertEqual(ansible.utils.boolean("foo"), False)

    #def test_make_sudo_cmd(self):
    #    cmd = ansible.utils.make_sudo_cmd('root', '/bin/sh', '/bin/ls')
    #    self.assertTrue(isinstance(cmd, tuple))
    #    self.assertEqual(len(cmd), 3)
    #    self.assertTrue('-u root' in cmd[0])
    #    self.assertTrue('-p "[sudo via ansible, key=' in cmd[0] and cmd[1].startswith('[sudo via ansible, key'))
    #    self.assertTrue('echo SUDO-SUCCESS-' in cmd[0] and cmd[2].startswith('SUDO-SUCCESS-'))
    #    self.assertTrue('sudo -k' in cmd[0])

    def test_make_su_cmd(self):
        cmd = ansible.utils.make_su_cmd('root', '/bin/sh', '/bin/ls')
        self.assertTrue(isinstance(cmd, tuple))
        self.assertEqual(len(cmd), 3)
        self.assertTrue('root -c "/bin/sh' in cmd[0])
        self.assertTrue(re.compile(cmd[1]))
        self.assertTrue('echo SUDO-SUCCESS-' in cmd[0] and cmd[2].startswith('SUDO-SUCCESS-'))

    def test_to_unicode(self):
        uni = ansible.utils.to_unicode(u'ansible')
        self.assertTrue(isinstance(uni, unicode))
        self.assertEqual(uni, u'ansible')

        none = ansible.utils.to_unicode(None)
        self.assertTrue(isinstance(none, type(None)))
        self.assertTrue(none is None)

        utf8 = ansible.utils.to_unicode('ansible')
        self.assertTrue(isinstance(utf8, unicode))
        self.assertEqual(utf8, u'ansible')

    def test_is_list_of_strings(self):
        self.assertEqual(ansible.utils.is_list_of_strings(['foo', 'bar', u'baz']), True)
        self.assertEqual(ansible.utils.is_list_of_strings(['foo', 'bar', True]), False)
        self.assertEqual(ansible.utils.is_list_of_strings(['one', 2, 'three']), False)

    def test_safe_eval(self):
        # Not basestring
        self.assertEqual(ansible.utils.safe_eval(len), len)
        self.assertEqual(ansible.utils.safe_eval(1), 1)
        self.assertEqual(ansible.utils.safe_eval(len, include_exceptions=True), (len, None))
        self.assertEqual(ansible.utils.safe_eval(1, include_exceptions=True), (1, None))

        # module
        self.assertEqual(ansible.utils.safe_eval('foo.bar('), 'foo.bar(')
        self.assertEqual(ansible.utils.safe_eval('foo.bar(', include_exceptions=True), ('foo.bar(', None))

        # import
        self.assertEqual(ansible.utils.safe_eval('import foo'), 'import foo')
        self.assertEqual(ansible.utils.safe_eval('import foo', include_exceptions=True), ('import foo', None))

        # valid simple eval
        self.assertEqual(ansible.utils.safe_eval('True'), True)
        self.assertEqual(ansible.utils.safe_eval('True', include_exceptions=True), (True, None))

        # valid eval with lookup
        self.assertEqual(ansible.utils.safe_eval('foo + bar', dict(foo=1, bar=2)), 3)
        self.assertEqual(ansible.utils.safe_eval('foo + bar', dict(foo=1, bar=2), include_exceptions=True), (3, None))

        # invalid eval
        self.assertEqual(ansible.utils.safe_eval('foo'), 'foo')
        nameerror = ansible.utils.safe_eval('foo', include_exceptions=True)
        self.assertTrue(isinstance(nameerror, tuple))
        self.assertEqual(nameerror[0], 'foo')
        self.assertTrue(isinstance(nameerror[1], NameError))

    def test_listify_lookup_plugin_terms(self):
        basedir = os.path.dirname(__file__)
        self.assertEqual(ansible.utils.listify_lookup_plugin_terms('things', basedir, dict()),
                         ['things'])
        self.assertEqual(ansible.utils.listify_lookup_plugin_terms('things', basedir, dict(things=['one', 'two'])),
                         ['one', 'two'])

    def test_deprecated(self):
        sys_stderr = sys.stderr
        sys.stderr = StringIO.StringIO()
        ansible.utils.deprecated('Ack!', '0.0')
        out = sys.stderr.getvalue()
        self.assertTrue('0.0' in out)
        self.assertTrue('[DEPRECATION WARNING]' in out)

        sys.stderr = StringIO.StringIO()
        ansible.utils.deprecated('Ack!', None)
        out = sys.stderr.getvalue()
        self.assertTrue('0.0' not in out)
        self.assertTrue('[DEPRECATION WARNING]' in out)

        sys.stderr = StringIO.StringIO()
        warnings = C.DEPRECATION_WARNINGS
        C.DEPRECATION_WARNINGS = False
        ansible.utils.deprecated('Ack!', None)
        out = sys.stderr.getvalue()
        self.assertTrue(not out)
        C.DEPRECATION_WARNINGS = warnings

        sys.stderr = sys_stderr

        try:
            ansible.utils.deprecated('Ack!', '0.0', True)
        except ansible.errors.AnsibleError, e:
            self.assertTrue('0.0' not in e.msg)
            self.assertTrue('[DEPRECATED]' in e.msg)
        else:
            raise AssertionError("Incorrect exception, expected AnsibleError")

    def test_warning(self):
        sys_stderr = sys.stderr
        sys.stderr = StringIO.StringIO()
        ansible.utils.warning('ANSIBLE')
        out = sys.stderr.getvalue()
        sys.stderr = sys_stderr
        self.assertTrue('[WARNING]: ANSIBLE' in out)

    def test_combine_vars(self):
        one = {'foo': {'bar': True}, 'baz': {'one': 'qux'}}
        two = {'baz': {'two': 'qux'}}
        replace = {'baz': {'two': 'qux'}, 'foo': {'bar': True}}
        merge = {'baz': {'two': 'qux', 'one': 'qux'}, 'foo': {'bar': True}}

        C.DEFAULT_HASH_BEHAVIOUR = 'replace'
        self.assertEqual(ansible.utils.combine_vars(one, two), replace)

        C.DEFAULT_HASH_BEHAVIOUR = 'merge'
        self.assertEqual(ansible.utils.combine_vars(one, two), merge)

    def test_err(self):
        sys_stderr = sys.stderr
        sys.stderr = StringIO.StringIO()
        ansible.utils.err('ANSIBLE')
        out = sys.stderr.getvalue()
        sys.stderr = sys_stderr
        self.assertEqual(out, 'ANSIBLE\n')

    def test_exit(self):
        sys_stderr = sys.stderr
        sys.stderr = StringIO.StringIO()
        try:
            ansible.utils.exit('ansible')
        except SystemExit, e:
            self.assertEqual(e.code, 1)
            self.assertEqual(sys.stderr.getvalue(), 'ansible\n')
        else:
            raise AssertionError('Incorrect exception, expected SystemExit')
        finally:
            sys.stderr = sys_stderr

    def test_unfrackpath(self):
        os.environ['TEST_ROOT'] = os.path.dirname(os.path.dirname(__file__))
        self.assertEqual(ansible.utils.unfrackpath('$TEST_ROOT/units/../units/TestUtils.py'), __file__.rstrip('c'))

    def test_is_executable(self):
        self.assertEqual(ansible.utils.is_executable(__file__), 0)

        bin_ansible = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                                   'bin', 'ansible')
        self.assertNotEqual(ansible.utils.is_executable(bin_ansible), 0)

    def test_get_diff(self):
        standard = dict(
            before_header='foo',
            after_header='bar',
            before='fooo',
            after='foo'
        )

        standard_expected = """--- before: foo
+++ after: bar
@@ -1 +1 @@
-fooo+foo"""

        # workaround py26 and py27 difflib differences        
        standard_expected = """-fooo+foo"""
        diff = ansible.utils.get_diff(standard)
        diff = diff.split('\n')
        del diff[0]
        del diff[0]
        del diff[0]
        diff = '\n'.join(diff)
        self.assertEqual(diff, unicode(standard_expected))


########NEW FILE########
__FILENAME__ = TestUtilsStringFunctions
# -*- coding: utf-8 -*-

import unittest
import os
import os.path
import tempfile
import yaml
import passlib.hash
import string
import StringIO
import copy

from nose.plugins.skip import SkipTest

from ansible.utils import string_functions
import ansible.errors
import ansible.constants as C
import ansible.utils.template as template2

from ansible import __version__

import sys
reload(sys)
sys.setdefaultencoding("utf8") 

class TestUtilsStringFunctions(unittest.TestCase):
    def test_isprintable(self):
        self.assertFalse(string_functions.isprintable(chr(7)))
        self.assertTrue(string_functions.isprintable('hello'))

    def test_count_newlines_from_end(self):
        self.assertEqual(string_functions.count_newlines_from_end('foo\n\n\n\n'), 4)
        self.assertEqual(string_functions.count_newlines_from_end('\nfoo'), 0)

########NEW FILE########
__FILENAME__ = TestVault
#!/usr/bin/env python

from unittest import TestCase
import getpass
import os
import shutil
import time
import tempfile
from binascii import unhexlify
from binascii import hexlify
from nose.plugins.skip import SkipTest

from ansible import errors
from ansible.utils.vault import VaultLib

# Counter import fails for 2.0.1, requires >= 2.6.1 from pip
try:
    from Crypto.Util import Counter
    HAS_COUNTER = True
except ImportError:
    HAS_COUNTER = False

# KDF import fails for 2.0.1, requires >= 2.6.1 from pip
try:
    from Crypto.Protocol.KDF import PBKDF2
    HAS_PBKDF2 = True
except ImportError:
    HAS_PBKDF2 = False

# AES IMPORTS
try:
    from Crypto.Cipher import AES as AES
    HAS_AES = True
except ImportError:
    HAS_AES = False

class TestVaultLib(TestCase):

    def test_methods_exist(self):
        v = VaultLib('ansible')
        slots = ['is_encrypted',
                 'encrypt',
                 'decrypt',
                 '_add_header',
                 '_split_header',]
        for slot in slots:         
            assert hasattr(v, slot), "VaultLib is missing the %s method" % slot

    def test_is_encrypted(self):
        v = VaultLib(None)
        assert not v.is_encrypted("foobar"), "encryption check on plaintext failed"
        data = "$ANSIBLE_VAULT;9.9;TEST\n%s" % hexlify("ansible")
        assert v.is_encrypted(data), "encryption check on headered text failed"

    def test_add_header(self):
        v = VaultLib('ansible')
        v.cipher_name = "TEST"
        sensitive_data = "ansible"
        data = v._add_header(sensitive_data)
        lines = data.split('\n')
        assert len(lines) > 1, "failed to properly add header"
        header = lines[0]
        assert header.endswith(';TEST'), "header does end with cipher name"
        header_parts = header.split(';')
        assert len(header_parts) == 3, "header has the wrong number of parts"        
        assert header_parts[0] == '$ANSIBLE_VAULT', "header does not start with $ANSIBLE_VAULT"
        assert header_parts[1] == v.version, "header version is incorrect"
        assert header_parts[2] == 'TEST', "header does end with cipher name"

    def test_split_header(self):
        v = VaultLib('ansible')
        data = "$ANSIBLE_VAULT;9.9;TEST\nansible" 
        rdata = v._split_header(data)        
        lines = rdata.split('\n')
        assert lines[0] == "ansible"
        assert v.cipher_name == 'TEST', "cipher name was not set"
        assert v.version == "9.9"

    def test_encrypt_decrypt_aes(self):
        if not HAS_AES or not HAS_COUNTER or not HAS_PBKDF2:
            raise SkipTest
        v = VaultLib('ansible')
        v.cipher_name = 'AES'
        enc_data = v.encrypt("foobar")
        dec_data = v.decrypt(enc_data)
        assert enc_data != "foobar", "encryption failed"
        assert dec_data == "foobar", "decryption failed"           

    def test_encrypt_decrypt_aes256(self):
        if not HAS_AES or not HAS_COUNTER or not HAS_PBKDF2:
            raise SkipTest
        v = VaultLib('ansible')
        v.cipher_name = 'AES256'
        enc_data = v.encrypt("foobar")
        dec_data = v.decrypt(enc_data)
        assert enc_data != "foobar", "encryption failed"
        assert dec_data == "foobar", "decryption failed"           

    def test_encrypt_encrypted(self):
        if not HAS_AES or not HAS_COUNTER or not HAS_PBKDF2:
            raise SkipTest
        v = VaultLib('ansible')
        v.cipher_name = 'AES'
        data = "$ANSIBLE_VAULT;9.9;TEST\n%s" % hexlify("ansible")
        error_hit = False
        try:
            enc_data = v.encrypt(data)
        except errors.AnsibleError, e:
            error_hit = True
        assert error_hit, "No error was thrown when trying to encrypt data with a header"    

    def test_decrypt_decrypted(self):
        if not HAS_AES or not HAS_COUNTER or not HAS_PBKDF2:
            raise SkipTest
        v = VaultLib('ansible')
        data = "ansible"
        error_hit = False
        try:
            dec_data = v.decrypt(data)
        except errors.AnsibleError, e:
            error_hit = True
        assert error_hit, "No error was thrown when trying to decrypt data without a header"    

    def test_cipher_not_set(self):
        # not setting the cipher should default to AES256
        if not HAS_AES or not HAS_COUNTER or not HAS_PBKDF2:
            raise SkipTest
        v = VaultLib('ansible')
        data = "ansible"
        error_hit = False
        try:
            enc_data = v.encrypt(data)
        except errors.AnsibleError, e:
            error_hit = True
        assert not error_hit, "An error was thrown when trying to encrypt data without the cipher set"    
        assert v.cipher_name == "AES256", "cipher name is not set to AES256: %s" % v.cipher_name               

########NEW FILE########
__FILENAME__ = TestVaultEditor
#!/usr/bin/env python

from unittest import TestCase
import getpass
import os
import shutil
import time
import tempfile
from binascii import unhexlify
from binascii import hexlify
from nose.plugins.skip import SkipTest

from ansible import errors
from ansible.utils.vault import VaultLib
from ansible.utils.vault import VaultEditor

# Counter import fails for 2.0.1, requires >= 2.6.1 from pip
try:
    from Crypto.Util import Counter
    HAS_COUNTER = True
except ImportError:
    HAS_COUNTER = False

# KDF import fails for 2.0.1, requires >= 2.6.1 from pip
try:
    from Crypto.Protocol.KDF import PBKDF2
    HAS_PBKDF2 = True
except ImportError:
    HAS_PBKDF2 = False

# AES IMPORTS
try:
    from Crypto.Cipher import AES as AES
    HAS_AES = True
except ImportError:
    HAS_AES = False

class TestVaultEditor(TestCase):

    def test_methods_exist(self):
        v = VaultEditor(None, None, None)
        slots = ['create_file',
                 'decrypt_file',
                 'edit_file',
                 'encrypt_file',
                 'rekey_file',
                 'read_data',
                 'write_data',
                 'shuffle_files']
        for slot in slots:         
            assert hasattr(v, slot), "VaultLib is missing the %s method" % slot

    def test_decrypt_1_0(self):
        if not HAS_AES or not HAS_COUNTER or not HAS_PBKDF2:
            raise SkipTest
        dirpath = tempfile.mkdtemp()
        filename = os.path.join(dirpath, "foo-ansible-1.0.yml")
        shutil.rmtree(dirpath)
        shutil.copytree("vault_test_data", dirpath)
        ve = VaultEditor(None, "ansible", filename)

        # make sure the password functions for the cipher
        error_hit = False
        try:        
            ve.decrypt_file()
        except errors.AnsibleError, e:
            error_hit = True

        # verify decrypted content
        f = open(filename, "rb")
        fdata = f.read()
        f.close()

        shutil.rmtree(dirpath)
        assert error_hit == False, "error decrypting 1.0 file"            
        assert fdata.strip() == "foo", "incorrect decryption of 1.0 file: %s" % fdata.strip() 

    def test_decrypt_1_0_newline(self):
        if not HAS_AES or not HAS_COUNTER or not HAS_PBKDF2:
            raise SkipTest
        dirpath = tempfile.mkdtemp()
        filename = os.path.join(dirpath, "foo-ansible-1.0-ansible-newline-ansible.yml")
        shutil.rmtree(dirpath)
        shutil.copytree("vault_test_data", dirpath)
        ve = VaultEditor(None, "ansible\nansible\n", filename)

        # make sure the password functions for the cipher
        error_hit = False
        try:        
            ve.decrypt_file()
        except errors.AnsibleError, e:
            error_hit = True

        # verify decrypted content
        f = open(filename, "rb")
        fdata = f.read()
        f.close()

        shutil.rmtree(dirpath)
        assert error_hit == False, "error decrypting 1.0 file with newline in password"            
        #assert fdata.strip() == "foo", "incorrect decryption of 1.0 file: %s" % fdata.strip() 


    def test_decrypt_1_1(self):
        if not HAS_AES or not HAS_COUNTER or not HAS_PBKDF2:
            raise SkipTest
        dirpath = tempfile.mkdtemp()
        filename = os.path.join(dirpath, "foo-ansible-1.1.yml")
        shutil.rmtree(dirpath)
        shutil.copytree("vault_test_data", dirpath)
        ve = VaultEditor(None, "ansible", filename)

        # make sure the password functions for the cipher
        error_hit = False
        try:        
            ve.decrypt_file()
        except errors.AnsibleError, e:
            error_hit = True

        # verify decrypted content
        f = open(filename, "rb")
        fdata = f.read()
        f.close()

        shutil.rmtree(dirpath)
        assert error_hit == False, "error decrypting 1.0 file"            
        assert fdata.strip() == "foo", "incorrect decryption of 1.0 file: %s" % fdata.strip() 


    def test_rekey_migration(self):
        if not HAS_AES or not HAS_COUNTER or not HAS_PBKDF2:
            raise SkipTest
        dirpath = tempfile.mkdtemp()
        filename = os.path.join(dirpath, "foo-ansible-1.0.yml")
        shutil.rmtree(dirpath)
        shutil.copytree("vault_test_data", dirpath)
        ve = VaultEditor(None, "ansible", filename)

        # make sure the password functions for the cipher
        error_hit = False
        try:        
            ve.rekey_file('ansible2')
        except errors.AnsibleError, e:
            error_hit = True

        # verify decrypted content
        f = open(filename, "rb")
        fdata = f.read()
        f.close()

        shutil.rmtree(dirpath)
        assert error_hit == False, "error rekeying 1.0 file to 1.1"            

        # ensure filedata can be decrypted, is 1.1 and is AES256
        vl = VaultLib("ansible2")
        dec_data = None
        error_hit = False
        try:
            dec_data = vl.decrypt(fdata)
        except errors.AnsibleError, e:
            error_hit = True

        assert vl.cipher_name == "AES256", "wrong cipher name set after rekey: %s" % vl.cipher_name
        assert error_hit == False, "error decrypting migrated 1.0 file"            
        assert dec_data.strip() == "foo", "incorrect decryption of rekeyed/migrated file: %s" % dec_data



########NEW FILE########
