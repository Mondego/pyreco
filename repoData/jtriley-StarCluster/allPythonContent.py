__FILENAME__ = check
#!/usr/bin/env python
import os
import re
import ast
import sys
import glob
import subprocess

import pep8
from pyflakes import checker


def check(codeString, filename):
    """
    Check the Python source given by C{codeString} for flakes.

    @param codeString: The Python source to check.
    @type codeString: C{str}

    @param filename: The name of the file the source came from, used to report
        errors.
    @type filename: C{str}

    @return: The number of warnings emitted.
    @rtype: C{int}
    """
    # First, compile into an AST and handle syntax errors.
    try:
        tree = compile(codeString, filename, "exec", ast.PyCF_ONLY_AST)
    except SyntaxError, value:
        msg = value.args[0]

        (lineno, offset, text) = value.lineno, value.offset, value.text

        # If there's an encoding problem with the file, the text is None.
        if text is None:
            # Avoid using msg, since for the only known case, it contains a
            # bogus message that claims the encoding the file declared was
            # unknown.
            print >> sys.stderr, "%s: problem decoding source" % (filename, )
        else:
            line = text.splitlines()[-1]

            if offset is not None:
                offset = offset - (len(text) - len(line))

            print >> sys.stderr, '%s:%d: %s' % (filename, lineno, msg)
            print >> sys.stderr, line

            if offset is not None:
                print >> sys.stderr, " " * offset, "^"

        return 1
    else:
        # Okay, it's syntactically valid.  Now check it.
        w = checker.Checker(tree, filename)
        lines = codeString.split('\n')
        messages = [message for message in w.messages
                    if lines[message.lineno - 1].find('pyflakes:ignore') < 0]
        messages.sort(lambda a, b: cmp(a.lineno, b.lineno))
        for warning in messages:
            print warning
        return len(messages)


def checkPath(filename):
    """
    Check the given path, printing out any warnings detected.

    @return: the number of warnings printed
    """
    try:
        return check(file(filename, 'U').read() + '\n', filename)
    except IOError, msg:
        print >> sys.stderr, "%s: %s" % (filename, msg.args[1])
        return 1


def matches_file(file_name, match_files):
    return any(re.compile(match_file).match(file_name) for match_file in
               match_files)


def check_files(files, check):
    clean = True
    print check['start_msg']
    for file_name in files:
        if not matches_file(file_name, check.get('match_files', [])):
            continue
        if matches_file(file_name, check.get('ignore_files', [])):
            continue
        print 'checking file: %s' % file_name
        process = subprocess.Popen(check['command'] % file_name,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, shell=True)
        out, err = process.communicate()
        output = out + err
        if output:
            output_lines = ['%s: %s' % (file_name, line) for line in
                            (out + err).splitlines()]
            print '\n'.join(output_lines)
        if process.returncode != 0:
            clean = False
    if not clean:
        raise Exception("ERROR: checks failed on some source files")


def find_py_files(path):
    for cfile in glob.glob(os.path.join(path, '*')):
        if os.path.isdir(cfile):
            for py in find_py_files(cfile):
                yield py
        if cfile.endswith('.py'):
            yield cfile


def check_pyflakes(files):
    print(">>> Running pyflakes...")
    clean = True
    for pyfile in files:
        if checkPath(pyfile) != 0:
            clean = False
    if not clean:
        raise Exception("ERROR: pyflakes failed on some source files")


def check_pep8(files):
    print(">>> Running pep8...")
    sg = pep8.StyleGuide(parse_argv=False, config_file=False)
    sg.options.repeat = True
    sg.options.show_pep8 = True
    report = sg.check_files(files)
    if report.total_errors:
        raise Exception("ERROR: pep8 failed on some source files")


def main(git_index=False, filetypes=['.py']):
    files = []
    if git_index:
        p = subprocess.Popen(['git', 'status', '--porcelain'],
                             stdout=subprocess.PIPE)
        out, err = p.communicate()
        modified = re.compile('^(?:MM|M|A)(\s+)(?P<name>.*)')
        for line in out.splitlines():
            match = modified.match(line)
            if match:
                f = match.group('name')
                if filetypes:
                    if f.endswith(tuple(filetypes)):
                        files.append(f)
                else:
                    files.append(f)
    else:
        src = os.path.join(os.path.dirname(__file__), 'starcluster')
        files = list(find_py_files(src))
    if not files:
        return
    try:
        check_pyflakes(files)
        check_pep8(files)
        print(">>> Clean!")
    except Exception, e:
        print
        print(e)
        print("ERROR: please fix the errors and re-run this script")
        sys.exit(1)

if __name__ == '__main__':
    git_index = '--git-index' in sys.argv
    main(git_index=git_index)

########NEW FILE########
__FILENAME__ = clean
#!/usr/bin/env python
import os
import glob


def find_cruft(path, extensions=['.pyc', '.pyo']):
    for cfile in glob.glob(os.path.join(path, '*')):
        if os.path.isdir(cfile):
            for cruft in find_cruft(cfile):
                yield cruft
        fname, ext = os.path.splitext(cfile)
        if ext in extensions:
            yield cfile


def main():
    repo_root = os.path.dirname(__file__)
    sc_src = os.path.join(repo_root, 'starcluster')
    for i in find_cruft(sc_src):
        os.unlink(i)
    for i in glob.glob('*.pyc'):
        os.unlink(i)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# StarCluster documentation build configuration file, created by
# sphinx-quickstart on Mon Mar  1 13:47:45 2010.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.append(os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.todo', 'sphinx.ext.coverage',
              'sphinx.ext.pngmath', 'sphinxcontrib.issuetracker']

issuetracker = 'github'
issuetracker_project = 'jtriley/StarCluster'

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'StarCluster'
copyright = u'2011, Software Tools for Academics and Researchers'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
static_mod = os.path.join('..', '..', 'starcluster', 'static.py')
execfile(static_mod)
version = VERSION
# The full version, including alpha/beta/rc tags.
release = VERSION

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of documents that shouldn't be included in the build.
#unused_docs = []

# List of directories, relative to source directory, that shouldn't be searched
# for source files.
exclude_trees = ['_build']

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

# The theme to use for HTML and HTML Help pages.  Major themes that come with
# Sphinx are currently 'default' and 'sphinxdoc'.
html_theme = 'starcluster'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
html_theme_path = ['_themes']

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = '_static/logo.png'

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

#Content template for the index page
html_index = {'index': 'index.html'}

# Custom sidebar templates, maps document names to template names.
html_sidebars = {'index': 'indexsidebar.html'}

# Additional templates that should be rendered to pages, maps page names to
# template names.
html_additional_pages = {'index': 'index.html'}

# If false, no module index is generated.
#html_use_modindex = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# If nonempty, this is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = ''

# Output file base name for HTML help builder.
htmlhelp_basename = 'StarClusterdoc'

# Google Analytics Tracker (theme must be GA-aware)
#html_context = {'gatracker': 'your-ga-tracker-id'}

# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'StarCluster.tex', u'StarCluster Documentation',
   u'Justin Riley', 'manual'),
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

########NEW FILE########
__FILENAME__ = pylons_theme_support
# -*- coding: utf-8 -*-
from pygments.style import Style
from pygments.token import Keyword, Name, Comment, String, Error, \
     Number, Operator, Generic, Whitespace, Punctuation, Other, Literal


class PylonsStyle(Style):
    """
    Pylons pygments style based on friendly style
    """

    # work in progress...

    background_color = "#f8f8f8"
    default_style = ""

    styles = {
        Whitespace:                "#bbbbbb",
        Comment:                   "italic #60a0b0",
        Comment.Preproc:           "noitalic #007020",
        Comment.Special:           "noitalic bg:#fff0f0",

        Keyword:                   "bold #007020",
        Keyword.Pseudo:            "nobold",
        Keyword.Type:              "nobold #902000",

        Operator:                  "#666666",
        Operator.Word:             "bold #007020",

        Name.Builtin:              "#007020",
        Name.Function:             "#06287e",
        Name.Class:                "bold #0e84b5",
        Name.Namespace:            "bold #0e84b5",
        Name.Exception:            "#007020",
        Name.Variable:             "#bb60d5",
        Name.Constant:             "#60add5",
        Name.Label:                "bold #002070",
        Name.Entity:               "bold #d55537",
        Name.Attribute:            "#0e84b5",
        Name.Tag:                  "bold #062873",
        Name.Decorator:            "bold #555555",

        String:                    "#4070a0",
        String.Doc:                "italic",
        String.Interpol:           "italic #70a0d0",
        String.Escape:             "bold #4070a0",
        String.Regex:              "#235388",
        String.Symbol:             "#517918",
        String.Other:              "#c65d09",
        Number:                    "#40a070",

        Generic.Heading:           "bold #000080",
        Generic.Subheading:        "bold #800080",
        Generic.Deleted:           "#A00000",
        Generic.Inserted:          "#00A000",
        Generic.Error:             "#FF0000",
        Generic.Emph:              "italic",
        Generic.Strong:            "bold",
        Generic.Prompt:            "bold #c65d09",
        Generic.Output:            "#888",
        Generic.Traceback:         "#04D",

        Error:                     "#a40000 bg:#fbe3e4"
    }


class PylonsBWStyle(Style):

    background_color = "#ffffff"
    default_style = "bw"

    styles = {
        Error:                     ""
    }


########NEW FILE########
__FILENAME__ = awsutils
# Copyright 2009-2014 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

"""
EC2/S3 Utility Classes
"""

import os
import re
import time
import base64
import string
import tempfile

import boto
import boto.ec2
import boto.s3.connection
from boto import config as boto_config
from boto.connection import HAVE_HTTPS_CONNECTION

from starcluster import image
from starcluster import utils
from starcluster import static
from starcluster import spinner
from starcluster import sshutils
from starcluster import webtools
from starcluster import exception
from starcluster import progressbar
from starcluster.utils import print_timing
from starcluster.logger import log


class EasyAWS(object):
    def __init__(self, aws_access_key_id, aws_secret_access_key,
                 connection_authenticator, **kwargs):
        """
        Create an EasyAWS object.

        Requires aws_access_key_id/aws_secret_access_key from an Amazon Web
        Services (AWS) account and a connection_authenticator function that
        returns an authenticated AWS connection object

        Providing only the keys will default to using Amazon EC2

        kwargs are passed to the connection_authenticator's constructor
        """
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.connection_authenticator = connection_authenticator
        self._conn = None
        self._kwargs = kwargs

    def reload(self):
        self._conn = None
        return self.conn

    @property
    def conn(self):
        if self._conn is None:
            log.debug('creating self._conn w/ connection_authenticator ' +
                      'kwargs = %s' % self._kwargs)
            validate_certs = self._kwargs.get('validate_certs', True)
            if validate_certs:
                if not HAVE_HTTPS_CONNECTION:
                    raise exception.AWSError(
                        "Failed to validate AWS SSL certificates. "
                        "SSL certificate validation is only supported "
                        "on Python>=2.6.\n\nSet AWS_VALIDATE_CERTS=False in "
                        "the [aws info] section of your config to skip SSL "
                        "certificate verification and suppress this error AT "
                        "YOUR OWN RISK.")
            if not boto_config.has_section('Boto'):
                boto_config.add_section('Boto')
            # Hack to get around the fact that boto ignores validate_certs
            # if https_validate_certificates is declared in the boto config
            boto_config.setbool('Boto', 'https_validate_certificates',
                                validate_certs)
            self._conn = self.connection_authenticator(
                self.aws_access_key_id, self.aws_secret_access_key,
                **self._kwargs)
            self._conn.https_validate_certificates = validate_certs
        return self._conn


class EasyEC2(EasyAWS):
    def __init__(self, aws_access_key_id, aws_secret_access_key,
                 aws_ec2_path='/', aws_s3_host=None, aws_s3_path='/',
                 aws_port=None, aws_region_name=None, aws_is_secure=True,
                 aws_region_host=None, aws_proxy=None, aws_proxy_port=None,
                 aws_proxy_user=None, aws_proxy_pass=None,
                 aws_validate_certs=True, **kwargs):
        aws_region = None
        if aws_region_name and aws_region_host:
            aws_region = boto.ec2.regioninfo.RegionInfo(
                name=aws_region_name, endpoint=aws_region_host)
        kwds = dict(is_secure=aws_is_secure, region=aws_region, port=aws_port,
                    path=aws_ec2_path, proxy=aws_proxy,
                    proxy_port=aws_proxy_port, proxy_user=aws_proxy_user,
                    proxy_pass=aws_proxy_pass,
                    validate_certs=aws_validate_certs)
        super(EasyEC2, self).__init__(aws_access_key_id, aws_secret_access_key,
                                      boto.connect_vpc, **kwds)
        self._conn = kwargs.get('connection')
        kwds = dict(aws_s3_host=aws_s3_host, aws_s3_path=aws_s3_path,
                    aws_port=aws_port, aws_is_secure=aws_is_secure,
                    aws_proxy=aws_proxy, aws_proxy_port=aws_proxy_port,
                    aws_proxy_user=aws_proxy_user,
                    aws_proxy_pass=aws_proxy_pass,
                    aws_validate_certs=aws_validate_certs)
        self.s3 = EasyS3(aws_access_key_id, aws_secret_access_key, **kwds)
        self._regions = None
        self._account_attrs = None
        self._account_attrs_region = None

    def __repr__(self):
        return '<EasyEC2: %s (%s)>' % (self.region.name, self.region.endpoint)

    def _fetch_account_attrs(self):
        acct_attrs = self._account_attrs
        if not acct_attrs or self._account_attrs_region != self.region.name:
            resp = self.conn.describe_account_attributes(
                ['default-vpc', 'supported-platforms'])
            self._account_attrs = acct_attrs = {}
            for attr in resp:
                acct_attrs[attr.attribute_name] = attr.attribute_values
            self._account_attrs_region = self.region.name
        return self._account_attrs

    @property
    def supported_platforms(self):
        return self._fetch_account_attrs()['supported-platforms']

    @property
    def default_vpc(self):
        default_vpc = self._fetch_account_attrs()['default-vpc'][0]
        if default_vpc == 'none':
            default_vpc = None
        return default_vpc

    def connect_to_region(self, region_name):
        """
        Connects to a given region if it exists, raises RegionDoesNotExist
        otherwise. Once connected, this object will return only data from the
        given region.
        """
        region = self.get_region(region_name)
        self._kwargs['region'] = region
        self._platforms = None
        self._default_vpc = None
        self.reload()
        return self

    @property
    def region(self):
        """
        Returns the current EC2 region used by this EasyEC2 object
        """
        return self.conn.region

    @property
    def regions(self):
        """
        This property returns all AWS Regions, caching the results the first
        time a request is made to Amazon
        """
        if not self._regions:
            self._regions = {}
            regions = self.conn.get_all_regions()
            for region in regions:
                self._regions[region.name] = region
        return self._regions

    def get_region(self, region_name):
        """
        Returns boto Region object if it exists, raises RegionDoesNotExist
        otherwise.
        """
        if region_name not in self.regions:
            raise exception.RegionDoesNotExist(region_name)
        return self.regions.get(region_name)

    def list_regions(self):
        """
        Print name/endpoint for all AWS regions
        """
        regions = self.regions.items()
        regions.sort(reverse=True)
        for name, endpoint in regions:
            print 'name: ', name
            print 'endpoint: ', endpoint.endpoint
            print

    @property
    def registered_images(self):
        return self.conn.get_all_images(owners=["self"])

    @property
    def executable_images(self):
        return self.conn.get_all_images(executable_by=["self"])

    def get_registered_image(self, image_id):
        if not image_id.startswith('ami') or len(image_id) != 12:
            raise TypeError("invalid AMI name/id requested: %s" % image_id)
        for img in self.registered_images:
            if img.id == image_id:
                return img

    def _wait_for_group_deletion_propagation(self, group):
        if isinstance(group, boto.ec2.placementgroup.PlacementGroup):
            while self.get_placement_group_or_none(group.name):
                time.sleep(5)
        else:
            assert isinstance(group, boto.ec2.securitygroup.SecurityGroup)
            while self.get_group_or_none(group.name):
                time.sleep(5)

    def get_subnet(self, subnet_id):
        try:
            return self.get_subnets(filters={'subnet_id': subnet_id})[0]
        except IndexError:
            raise exception.SubnetDoesNotExist(subnet_id)

    def get_subnets(self, filters=None):
        return self.conn.get_all_subnets(filters=filters)

    def get_internet_gateways(self, filters=None):
        return self.conn.get_all_internet_gateways(filters=filters)

    def get_route_tables(self, filters=None):
        return self.conn.get_all_route_tables(filters=filters)

    def get_network_spec(self, *args, **kwargs):
        return boto.ec2.networkinterface.NetworkInterfaceSpecification(
            *args, **kwargs)

    def get_network_collection(self, *args, **kwargs):
        return boto.ec2.networkinterface.NetworkInterfaceCollection(
            *args, **kwargs)

    def delete_group(self, group, max_retries=60, retry_delay=5):
        """
        This method deletes a security or placement group using group.delete()
        but in the case that group.delete() throws a DependencyViolation error
        or InvalidPlacementGroup.InUse error it will keep retrying until it's
        successful. Waits 5 seconds between each retry.
        """
        label = 'security'
        if hasattr(group, 'strategy') and group.strategy == 'cluster':
            label = 'placement'
        s = utils.get_spinner("Removing %s group: %s" % (label, group.name))
        try:
            for i in range(max_retries):
                try:
                    ret_val = group.delete()
                    self._wait_for_group_deletion_propagation(group)
                    return ret_val
                except boto.exception.EC2ResponseError as e:
                    if i == max_retries - 1:
                        raise
                    if e.error_code == 'DependencyViolation':
                        log.debug('DependencyViolation error - retrying in 5s',
                                  exc_info=True)
                        time.sleep(retry_delay)
                    elif e.error_code == 'InvalidPlacementGroup.InUse':
                        log.debug('Placement group in use - retrying in 5s',
                                  exc_info=True)
                        time.sleep(retry_delay)
                    else:
                        raise
        finally:
            s.stop()

    def create_group(self, name, description, auth_ssh=False,
                     auth_group_traffic=False, vpc_id=None):
        """
        Create security group with name/description. auth_ssh=True
        will open port 22 to world (0.0.0.0/0). auth_group_traffic
        will allow all traffic between instances in the same security
        group
        """
        log.info("Creating security group %s..." % name)
        sg = self.conn.create_security_group(name, description, vpc_id=vpc_id)
        if not self.get_group_or_none(name):
            s = utils.get_spinner("Waiting for security group %s..." % name)
            try:
                while not self.get_group_or_none(name):
                    time.sleep(3)
            finally:
                s.stop()
        if auth_ssh:
            ssh_port = static.DEFAULT_SSH_PORT
            sg.authorize(ip_protocol='tcp', from_port=ssh_port,
                         to_port=ssh_port, cidr_ip=static.WORLD_CIDRIP)
        if auth_group_traffic:
            sg.authorize(src_group=sg, ip_protocol='icmp', from_port=-1,
                         to_port=-1)
            sg.authorize(src_group=sg, ip_protocol='tcp', from_port=1,
                         to_port=65535)
            sg.authorize(src_group=sg, ip_protocol='udp', from_port=1,
                         to_port=65535)
        return sg

    def get_all_security_groups(self, groupnames=[]):
        """
        Returns all security groups

        groupnames - optional list of group names to retrieve
        """
        filters = {}
        if groupnames:
            filters = {'group-name': groupnames}
        return self.get_security_groups(filters=filters)

    def get_group_or_none(self, name):
        """
        Returns group with name if it exists otherwise returns None
        """
        try:
            return self.get_security_group(name)
        except exception.SecurityGroupDoesNotExist:
            pass

    def get_or_create_group(self, name, description, auth_ssh=True,
                            auth_group_traffic=False, vpc_id=None):
        """
        Try to return a security group by name. If the group is not found,
        attempt to create it.  Description only applies to creation.

        auth_ssh - authorize ssh traffic from world
        auth_group_traffic - authorizes all traffic between members of the
                             group
        """
        sg = self.get_group_or_none(name)
        if not sg:
            sg = self.create_group(name, description, auth_ssh=auth_ssh,
                                   auth_group_traffic=auth_group_traffic,
                                   vpc_id=vpc_id)
        return sg

    def get_security_group(self, groupname):
        try:
            return self.get_security_groups(
                filters={'group-name': groupname})[0]
        except boto.exception.EC2ResponseError as e:
            if e.error_code == "InvalidGroup.NotFound":
                raise exception.SecurityGroupDoesNotExist(groupname)
            raise
        except IndexError:
            raise exception.SecurityGroupDoesNotExist(groupname)

    def get_security_groups(self, filters=None):
        """
        Returns all security groups on this EC2 account
        """
        return self.conn.get_all_security_groups(filters=filters)

    def get_permission_or_none(self, group, ip_protocol, from_port, to_port,
                               cidr_ip=None):
        """
        Returns the rule with the specified port range permission (ip_protocol,
        from_port, to_port, cidr_ip) defined or None if no such rule exists
        """
        for rule in group.rules:
            if rule.ip_protocol != ip_protocol:
                continue
            if int(rule.from_port) != from_port:
                continue
            if int(rule.to_port) != to_port:
                continue
            if cidr_ip:
                cidr_grants = [g for g in rule.grants if g.cidr_ip == cidr_ip]
                if not cidr_grants:
                    continue
            return rule

    def has_permission(self, group, ip_protocol, from_port, to_port, cidr_ip):
        """
        Checks whether group has the specified port range permission
        (ip_protocol, from_port, to_port, cidr_ip) defined
        """
        for rule in group.rules:
            if rule.ip_protocol != ip_protocol:
                continue
            if int(rule.from_port) != from_port:
                continue
            if int(rule.to_port) != to_port:
                continue
            cidr_grants = [g for g in rule.grants if g.cidr_ip == cidr_ip]
            if not cidr_grants:
                continue
            return True
        return False

    def create_placement_group(self, name):
        """
        Create a new placement group for your account.
        This will create the placement group within the region you
        are currently connected to.
        """
        log.info("Creating placement group %s..." % name)
        success = self.conn.create_placement_group(name)
        if not success:
            log.debug(
                "failed to create placement group '%s' (error = %s)" %
                (name, success))
            raise exception.AWSError(
                "failed to create placement group '%s'" % name)
        pg = self.get_placement_group_or_none(name)
        while not pg:
            log.info("Waiting for placement group %s..." % name)
            time.sleep(3)
            pg = self.get_placement_group_or_none(name)
        return pg

    def get_placement_groups(self, filters=None):
        return self.conn.get_all_placement_groups(filters=filters)

    def get_placement_group(self, groupname=None):
        try:
            return self.get_placement_groups(filters={'group-name':
                                                      groupname})[0]
        except boto.exception.EC2ResponseError as e:
            if e.error_code == "InvalidPlacementGroup.Unknown":
                raise exception.PlacementGroupDoesNotExist(groupname)
            raise
        except IndexError:
            raise exception.PlacementGroupDoesNotExist(groupname)

    def get_placement_group_or_none(self, name):
        """
        Returns placement group with name if it exists otherwise returns None
        """
        try:
            return self.get_placement_group(name)
        except exception.PlacementGroupDoesNotExist:
            pass

    def get_or_create_placement_group(self, name):
        """
        Try to return a placement group by name.
        If the group is not found, attempt to create it.
        """
        try:
            return self.get_placement_group(name)
        except exception.PlacementGroupDoesNotExist:
            pg = self.create_placement_group(name)
            return pg

    def request_instances(self, image_id, price=None, instance_type='m1.small',
                          min_count=1, max_count=1, count=1, key_name=None,
                          security_groups=None, security_group_ids=None,
                          launch_group=None,
                          availability_zone_group=None, placement=None,
                          user_data=None, placement_group=None,
                          block_device_map=None, subnet_id=None,
                          network_interfaces=None):
        """
        Convenience method for running spot or flat-rate instances
        """
        if not block_device_map:
            img = self.get_image(image_id)
            instance_store = img.root_device_type == 'instance-store'
            if instance_type == 'm1.small' and img.architecture == "i386":
                # Needed for m1.small + 32bit AMI (see gh-329)
                instance_store = True
            use_ephemeral = instance_type != 't1.micro'
            bdmap = self.create_block_device_map(
                add_ephemeral_drives=use_ephemeral,
                num_ephemeral_drives=24,
                instance_store=instance_store)
            # Prune drives from runtime block device map that may override EBS
            # volumes specified in the AMIs block device map
            for dev in img.block_device_mapping:
                bdt = img.block_device_mapping.get(dev)
                if not bdt.ephemeral_name and dev in bdmap:
                    log.debug("EBS volume already mapped to %s by AMI" % dev)
                    log.debug("Removing %s from runtime block device map" %
                              dev)
                    bdmap.pop(dev)
            if img.root_device_name in img.block_device_mapping:
                log.debug("Forcing delete_on_termination for AMI: %s" % img.id)
                root = img.block_device_mapping[img.root_device_name]
                # specifying the AMI's snapshot in the custom block device
                # mapping when you dont own the AMI causes an error on launch
                root.snapshot_id = None
                root.delete_on_termination = True
                bdmap[img.root_device_name] = root
            block_device_map = bdmap
        shared_kwargs = dict(instance_type=instance_type,
                             key_name=key_name,
                             subnet_id=subnet_id,
                             placement=placement,
                             placement_group=placement_group,
                             user_data=user_data,
                             block_device_map=block_device_map,
                             network_interfaces=network_interfaces)
        if price:
            return self.request_spot_instances(
                price, image_id,
                count=count, launch_group=launch_group,
                security_group_ids=security_group_ids,
                availability_zone_group=availability_zone_group,
                **shared_kwargs)
        else:
            return self.run_instances(
                image_id,
                min_count=min_count, max_count=max_count,
                security_groups=security_groups,
                **shared_kwargs)

    def request_spot_instances(self, price, image_id, instance_type='m1.small',
                               count=1, launch_group=None, key_name=None,
                               availability_zone_group=None,
                               security_group_ids=None, subnet_id=None,
                               placement=None, placement_group=None,
                               user_data=None, block_device_map=None,
                               network_interfaces=None):
        kwargs = locals()
        kwargs.pop('self')
        return self.conn.request_spot_instances(**kwargs)

    def _wait_for_propagation(self, obj_ids, fetch_func, id_filter, obj_name,
                              max_retries=60, interval=5):
        """
        Wait for a list of object ids to appear in the AWS API. Requires a
        function that fetches the objects and also takes a filters kwarg. The
        id_filter specifies the id filter to use for the objects and
        obj_name describes the objects for log messages.
        """
        filters = {id_filter: obj_ids}
        num_objs = len(obj_ids)
        num_reqs = 0
        reqs_ids = []
        max_retries = max(1, max_retries)
        interval = max(1, interval)
        widgets = ['', progressbar.Fraction(), ' ',
                   progressbar.Bar(marker=progressbar.RotatingMarker()), ' ',
                   progressbar.Percentage(), ' ', ' ']
        log.info("Waiting for %s to propagate..." % obj_name)
        pbar = progressbar.ProgressBar(widgets=widgets,
                                       maxval=num_objs).start()
        try:
            for i in range(max_retries + 1):
                reqs = fetch_func(filters=filters)
                reqs_ids = [req.id for req in reqs]
                num_reqs = len(reqs)
                pbar.update(num_reqs)
                if num_reqs != num_objs:
                    log.debug("%d: only %d/%d %s have "
                              "propagated - sleeping..." %
                              (i, num_reqs, num_objs, obj_name))
                    if i != max_retries:
                        time.sleep(interval)
                else:
                    return
        finally:
            if not pbar.finished:
                pbar.finish()
        missing = [oid for oid in obj_ids if oid not in reqs_ids]
        raise exception.PropagationException(
            "Failed to fetch %d/%d %s after %d seconds: %s" %
            (num_reqs, num_objs, obj_name, max_retries * interval,
             ', '.join(missing)))

    def wait_for_propagation(self, instances=None, spot_requests=None,
                             max_retries=60, interval=5):
        """
        Wait for newly created instances and/or spot_requests to register in
        the AWS API by repeatedly calling get_all_{instances, spot_requests}.
        Calling this method directly after creating new instances or spot
        requests before operating on them helps to avoid eventual consistency
        errors about instances or spot requests not existing.
        """
        if spot_requests:
            spot_ids = [getattr(s, 'id', s) for s in spot_requests]
            self._wait_for_propagation(
                spot_ids, self.get_all_spot_requests,
                'spot-instance-request-id', 'spot requests',
                max_retries=max_retries, interval=interval)
        if instances:
            instance_ids = [getattr(i, 'id', i) for i in instances]
            self._wait_for_propagation(
                instance_ids, self.get_all_instances, 'instance-id',
                'instances', max_retries=max_retries, interval=interval)

    def run_instances(self, image_id, instance_type='m1.small', min_count=1,
                      max_count=1, key_name=None, security_groups=None,
                      placement=None, user_data=None, placement_group=None,
                      block_device_map=None, subnet_id=None,
                      network_interfaces=None):
        kwargs = dict(
            instance_type=instance_type,
            min_count=min_count,
            max_count=max_count,
            key_name=key_name,
            subnet_id=subnet_id,
            placement=placement,
            user_data=user_data,
            placement_group=placement_group,
            block_device_map=block_device_map,
            network_interfaces=network_interfaces
        )
        if subnet_id:
            kwargs.update(
                security_group_ids=self.get_securityids_from_names(
                    security_groups))
            return self.conn.run_instances(image_id, **kwargs)
        else:
            kwargs.update(security_groups=security_groups)
            return self.conn.run_instances(image_id, **kwargs)

    def create_image(self, instance_id, name, description=None,
                     no_reboot=False):
        return self.conn.create_image(instance_id, name,
                                      description=description,
                                      no_reboot=no_reboot)

    def register_image(self, name, description=None, image_location=None,
                       architecture=None, kernel_id=None, ramdisk_id=None,
                       root_device_name=None, block_device_map=None,
                       virtualization_type=None, sriov_net_support=None,
                       snapshot_id=None):
        kwargs = locals()
        kwargs.pop('self')
        return self.conn.register_image(**kwargs)

    def delete_keypair(self, name):
        return self.conn.delete_key_pair(name)

    def import_keypair(self, name, rsa_key_file):
        """
        Import an existing RSA key file to EC2

        Returns boto.ec2.keypair.KeyPair
        """
        k = sshutils.get_rsa_key(rsa_key_file)
        pub_material = sshutils.get_public_key(k)
        return self.conn.import_key_pair(name, pub_material)

    def create_keypair(self, name, output_file=None):
        """
        Create a new EC2 keypair and optionally save to output_file

        Returns boto.ec2.keypair.KeyPair
        """
        if output_file:
            output_dir = os.path.dirname(output_file)
            if output_dir and not os.path.exists(output_dir):
                raise exception.BaseException(
                    "output directory does not exist")
            if os.path.exists(output_file):
                raise exception.BaseException(
                    "cannot save keypair %s: file already exists" %
                    output_file)
        try:
            kp = self.conn.create_key_pair(name)
        except boto.exception.EC2ResponseError as e:
            if e.error_code == "InvalidKeyPair.Duplicate":
                raise exception.KeyPairAlreadyExists(name)
            raise
        if output_file:
            try:
                kfile = open(output_file, 'wb')
                kfile.write(kp.material)
                kfile.close()
                os.chmod(output_file, 0400)
            except IOError as e:
                raise exception.BaseException(str(e))
        return kp

    def get_keypairs(self, filters={}):
        return self.conn.get_all_key_pairs(filters=filters)

    def get_keypair(self, keypair):
        try:
            return self.get_keypairs(filters={'key-name': keypair})[0]
        except boto.exception.EC2ResponseError as e:
            if e.error_code == "InvalidKeyPair.NotFound":
                raise exception.KeyPairDoesNotExist(keypair)
            raise
        except IndexError:
            raise exception.KeyPairDoesNotExist(keypair)

    def get_keypair_or_none(self, keypair):
        try:
            return self.get_keypair(keypair)
        except exception.KeyPairDoesNotExist:
            pass

    def __print_header(self, msg):
        print msg
        print "-" * len(msg)

    def get_image_name(self, img):
        image_name = re.sub('\.manifest\.xml$', '',
                            img.location.split('/')[-1])
        return image_name

    def get_instance_user_data(self, instance_id):
        try:
            attrs = self.conn.get_instance_attribute(instance_id, 'userData')
            user_data = attrs.get('userData', '') or ''
            return base64.b64decode(user_data)
        except boto.exception.EC2ResponseError as e:
            if e.error_code == "InvalidInstanceID.NotFound":
                raise exception.InstanceDoesNotExist(instance_id)
            raise e

    def get_securityids_from_names(self, groupnames):
        name_id = dict([(sec.name, sec.id) for sec in
                        self.get_all_security_groups(groupnames)])
        return [name_id[gname] for gname in groupnames if gname in name_id]

    def get_all_instances(self, instance_ids=[], filters={}):
        # little path to since vpc can't hadle filters with group-name
        # TODO : dev Tue Apr 24 18:25:58 2012
        # should move all code to instance.group-id
        if 'group-name' in filters:
            groupname = filters['group-name']
            try:
                secid = self.get_securityids_from_names([groupname])[0]
                filters['instance.group-id'] = secid
            except IndexError:
                return []  # Haven't created the security group in aws yet
            del filters['group-name']

        reservations = self.conn.get_all_instances(instance_ids,
                                                   filters=filters)
        instances = []
        for res in reservations:
            insts = res.instances
            instances.extend(insts)
        return instances

    def get_instance(self, instance_id):
        try:
            return self.get_all_instances(
                filters={'instance-id': instance_id})[0]
        except boto.exception.EC2ResponseError as e:
            if e.error_code == "InvalidInstanceID.NotFound":
                raise exception.InstanceDoesNotExist(instance_id)
            raise
        except IndexError:
            raise exception.InstanceDoesNotExist(instance_id)

    def is_valid_conn(self):
        try:
            self.get_all_instances()
            return True
        except boto.exception.EC2ResponseError as e:
            cred_errs = ['AuthFailure', 'SignatureDoesNotMatch']
            if e.error_code in cred_errs:
                return False
            raise

    def get_all_spot_requests(self, spot_ids=[], filters=None):
        spots = self.conn.get_all_spot_instance_requests(spot_ids,
                                                         filters=filters)
        return spots

    def list_all_spot_instances(self, show_closed=False):
        s = self.conn.get_all_spot_instance_requests()
        if not s:
            log.info("No spot instance requests found...")
            return
        spots = []
        for spot in s:
            if spot.state in ['closed', 'cancelled'] and not show_closed:
                continue
            state = spot.state or 'N/A'
            spot_id = spot.id or 'N/A'
            spots.append(spot_id)
            type = spot.type
            instance_id = spot.instance_id or 'N/A'
            create_time = spot.create_time or 'N/A'
            launch_group = spot.launch_group or 'N/A'
            zone_group = spot.availability_zone_group or 'N/A'
            price = spot.price or 'N/A'
            status = spot.status.code or 'N/A'
            message = spot.status.message or 'N/A'
            lspec = spot.launch_specification
            instance_type = lspec.instance_type
            image_id = lspec.image_id
            zone = lspec.placement
            groups = ', '.join([g.id for g in lspec.groups])
            print "id: %s" % spot_id
            print "price: $%0.2f" % price
            print "status: %s" % status
            print "message: %s" % message
            print "spot_request_type: %s" % type
            print "state: %s" % state
            print "instance_id: %s" % instance_id
            print "instance_type: %s" % instance_type
            print "image_id: %s" % image_id
            print "zone: %s" % zone
            print "create_time: %s" % create_time
            print "launch_group: %s" % launch_group
            print "zone_group: %s" % zone_group
            print "security_groups: %s" % groups
            print
        if not spots:
            log.info("No spot instance requests found...")
        else:
            print 'Total: %s' % len(spots)

    def show_instance(self, instance):
        instance_id = instance.id or 'N/A'
        groups = ', '.join([g.name for g in instance.groups])
        dns_name = instance.dns_name or 'N/A'
        private_dns_name = instance.private_dns_name or 'N/A'
        state = instance.state or 'N/A'
        private_ip = instance.private_ip_address or 'N/A'
        public_ip = instance.ip_address or 'N/A'
        zone = instance.placement or 'N/A'
        ami = instance.image_id or 'N/A'
        virt_type = instance.virtualization_type or 'N/A'
        instance_type = instance.instance_type or 'N/A'
        keypair = instance.key_name or 'N/A'
        uptime = utils.get_elapsed_time(instance.launch_time) or 'N/A'
        tags = ', '.join(['%s=%s' % (k, v) for k, v in
                          instance.tags.iteritems()]) or 'N/A'
        vpc_id = instance.vpc_id or 'N/A'
        subnet_id = instance.subnet_id or 'N/A'
        if state == 'stopped':
            uptime = 'N/A'
        print "id: %s" % instance_id
        print "dns_name: %s" % dns_name
        print "private_dns_name: %s" % private_dns_name
        if instance.reason:
            print "state: %s (%s)" % (state, instance.reason)
        else:
            print "state: %s" % state
        print "public_ip: %s" % public_ip
        print "private_ip: %s" % private_ip
        print "vpc: %s" % vpc_id
        print "subnet: %s" % subnet_id
        print "zone: %s" % zone
        print "ami: %s" % ami
        print "virtualization: %s" % virt_type
        print "type: %s" % instance_type
        print "groups: %s" % groups
        print "keypair: %s" % keypair
        print "uptime: %s" % uptime
        print "tags: %s" % tags
        print

    def list_all_instances(self, show_terminated=False):
        tstates = ['shutting-down', 'terminated']
        insts = self.get_all_instances()
        if not show_terminated:
            insts = [i for i in insts if i.state not in tstates]
        if not insts:
            log.info("No instances found")
            return
        for instance in insts:
            self.show_instance(instance)
        print 'Total: %s' % len(insts)

    def list_images(self, images, sort_key=None, reverse=False):
        def get_key(obj):
            return ' '.join([obj.region.name, obj.location])
        if not sort_key:
            sort_key = get_key
        imgs_i386 = [img for img in images if img.architecture == "i386"]
        imgs_i386.sort(key=sort_key, reverse=reverse)
        imgs_x86_64 = [img for img in images if img.architecture == "x86_64"]
        imgs_x86_64.sort(key=sort_key, reverse=reverse)
        print
        self.__list_images("32bit Images:", imgs_i386)
        self.__list_images("\n64bit Images:", imgs_x86_64)
        print "\ntotal images: %d" % len(images)
        print

    def list_registered_images(self):
        images = self.registered_images
        log.info("Your registered images:")
        self.list_images(images)

    def list_executable_images(self):
        images = self.executable_images
        log.info("Private images owned by other users that you can execute:")
        self.list_images(images)

    def __list_images(self, msg, imgs):
        counter = 0
        self.__print_header(msg)
        for img in imgs:
            name = self.get_image_name(img)
            template = "[%d] %s %s %s"
            if img.virtualization_type == 'hvm':
                template += ' (HVM-EBS)'
            elif img.root_device_type == 'ebs':
                template += ' (EBS)'
            print template % (counter, img.id, img.region.name, name)
            counter += 1

    def remove_image_files(self, image_name, pretend=True):
        if pretend:
            log.info("Pretending to remove image files...")
        else:
            log.info('Removing image files...')
        files = self.get_image_files(image_name)
        for f in files:
            if pretend:
                log.info("Would remove file: %s" % f.name)
            else:
                log.info('Removing file %s' % f.name)
                f.delete()
        if not pretend:
            files = self.get_image_files(image_name)
            if len(files) != 0:
                log.warn('Not all files deleted, recursing...')
                self.remove_image_files(image_name, pretend)

    @print_timing("Removing image")
    def remove_image(self, image_name, pretend=True, keep_image_data=True):
        img = self.get_image(image_name)
        if pretend:
            log.info('Pretending to deregister AMI: %s' % img.id)
        else:
            log.info('Deregistering AMI: %s' % img.id)
            img.deregister()
        if img.root_device_type == "instance-store" and not keep_image_data:
            self.remove_image_files(img, pretend=pretend)
        elif img.root_device_type == "ebs" and not keep_image_data:
            rootdevtype = img.block_device_mapping.get('/dev/sda1', None)
            if rootdevtype:
                snapid = rootdevtype.snapshot_id
                if snapid:
                    snap = self.get_snapshot(snapid)
                    if pretend:
                        log.info("Would remove snapshot: %s" % snapid)
                    else:
                        log.info("Removing snapshot: %s" % snapid)
                        snap.delete()

    def list_starcluster_public_images(self):
        images = self.conn.get_all_images(owners=[static.STARCLUSTER_OWNER_ID])
        log.info("Listing all public StarCluster images...")
        imgs = [img for img in images if img.is_public]

        def sc_public_sort(obj):
            split = obj.name.split('-')
            osname, osversion, arch = split[2:5]
            osversion = float(osversion)
            rc = 0
            if split[-1].startswith('rc'):
                rc = int(split[-1].replace('rc', ''))
            return (osversion, rc)
        self.list_images(imgs, sort_key=sc_public_sort, reverse=True)

    def create_volume(self, size, zone, snapshot_id=None):
        msg = "Creating %sGB volume in zone %s" % (size, zone)
        if snapshot_id:
            msg += " from snapshot %s" % snapshot_id
        log.info(msg)
        return self.conn.create_volume(size, zone, snapshot_id)

    def remove_volume(self, volume_id):
        vol = self.get_volume(volume_id)
        vol.delete()

    def list_keypairs(self):
        keypairs = self.keypairs
        if not keypairs:
            log.info("No keypairs found...")
            return
        max_length = max([len(key.name) for key in keypairs])
        templ = "%" + str(max_length) + "s  %s"
        for key in self.keypairs:
            print templ % (key.name, key.fingerprint)

    def list_zones(self, region=None):
        conn = self.conn
        if region:
            regs = self.conn.get_all_regions()
            regions = [r.name for r in regs]
            if region not in regions:
                raise exception.RegionDoesNotExist(region)
            for reg in regs:
                if reg.name == region:
                    region = reg
                    break
            kwargs = {}
            kwargs.update(self._kwargs)
            kwargs.update(dict(region=region))
            conn = self.connection_authenticator(
                self.aws_access_key_id, self.aws_secret_access_key, **kwargs)
        for zone in conn.get_all_zones():
            print 'name: ', zone.name
            print 'region: ', zone.region.name
            print 'status: ', zone.state
            print

    def get_zones(self, filters=None):
        return self.conn.get_all_zones(filters=filters)

    def get_zone(self, zone):
        """
        Return zone object representing an EC2 availability zone
        Raises exception.ZoneDoesNotExist if not successful
        """
        try:
            return self.get_zones(filters={'zone-name': zone})[0]
        except boto.exception.EC2ResponseError as e:
            if e.error_code == "InvalidZone.NotFound":
                raise exception.ZoneDoesNotExist(zone, self.region.name)
        except IndexError:
            raise exception.ZoneDoesNotExist(zone, self.region.name)

    def get_zone_or_none(self, zone):
        """
        Return zone object representing an EC2 availability zone
        Returns None if unsuccessful
        """
        try:
            return self.get_zone(zone)
        except exception.ZoneDoesNotExist:
            pass

    def create_s3_image(self, instance_id, key_location, aws_user_id,
                        ec2_cert, ec2_private_key, bucket, image_name="image",
                        description=None, kernel_id=None, ramdisk_id=None,
                        remove_image_files=False, **kwargs):
        """
        Create instance-store (S3) image from running instance
        """
        icreator = image.S3ImageCreator(self, instance_id, key_location,
                                        aws_user_id, ec2_cert,
                                        ec2_private_key, bucket,
                                        image_name=image_name,
                                        description=description,
                                        kernel_id=kernel_id,
                                        ramdisk_id=ramdisk_id,
                                        remove_image_files=remove_image_files)
        return icreator.create_image()

    def create_ebs_image(self, instance_id, key_location, name,
                         description=None, snapshot_description=None,
                         kernel_id=None, ramdisk_id=None, root_vol_size=15,
                         **kwargs):
        """
        Create EBS-backed image from running instance
        """
        sdescription = snapshot_description
        icreator = image.EBSImageCreator(self, instance_id, key_location,
                                         name, description=description,
                                         snapshot_description=sdescription,
                                         kernel_id=kernel_id,
                                         ramdisk_id=ramdisk_id,
                                         **kwargs)
        return icreator.create_image(size=root_vol_size)

    def get_images(self, filters=None):
        return self.conn.get_all_images(filters=filters)

    def get_image(self, image_id):
        """
        Return image object representing an AMI.
        Raises exception.AMIDoesNotExist if unsuccessful
        """
        try:
            return self.get_images(filters={'image-id': image_id})[0]
        except boto.exception.EC2ResponseError as e:
            if e.error_code == "InvalidAMIID.NotFound":
                raise exception.AMIDoesNotExist(image_id)
            raise
        except IndexError:
            raise exception.AMIDoesNotExist(image_id)

    def get_image_or_none(self, image_id):
        """
        Return image object representing an AMI.
        Returns None if unsuccessful
        """
        try:
            return self.get_image(image_id)
        except exception.AMIDoesNotExist:
            pass

    def get_image_files(self, image):
        """
        Returns a list of files on S3 for an EC2 instance-store (S3-backed)
        image. This includes the image's manifest and part files.
        """
        if not hasattr(image, 'id'):
            image = self.get_image(image)
        if image.root_device_type == 'ebs':
            raise exception.AWSError(
                "Image %s is an EBS image. No image files on S3." % image.id)
        bucket = self.get_image_bucket(image)
        bname = re.escape(bucket.name)
        prefix = re.sub('^%s\/' % bname, '', image.location)
        prefix = re.sub('\.manifest\.xml$', '', prefix)
        files = bucket.list(prefix=prefix)
        manifest_regex = re.compile(r'%s\.manifest\.xml' % prefix)
        part_regex = re.compile(r'%s\.part\.(\d*)' % prefix)
        # boto with eucalyptus returns boto.s3.prefix.Prefix class at the
        # end of the list, we ignore these by checking for delete attr
        files = [f for f in files if hasattr(f, 'delete') and
                 part_regex.match(f.name) or manifest_regex.match(f.name)]
        return files

    def get_image_bucket(self, image):
        bucket_name = image.location.split('/')[0]
        return self.s3.get_bucket(bucket_name)

    def get_image_manifest(self, image):
        return image.location.split('/')[-1]

    @print_timing("Migrating image")
    def migrate_image(self, image_id, destbucket, migrate_manifest=False,
                      kernel_id=None, ramdisk_id=None, region=None, cert=None,
                      private_key=None):
        """
        Migrate image_id files to destbucket
        """
        if migrate_manifest:
            utils.check_required(['ec2-migrate-manifest'])
            if not cert:
                raise exception.BaseException("no cert specified")
            if not private_key:
                raise exception.BaseException("no private_key specified")
            if not kernel_id:
                raise exception.BaseException("no kernel_id specified")
            if not ramdisk_id:
                raise exception.BaseException("no ramdisk_id specified")
        image = self.get_image(image_id)
        if image.root_device_type == "ebs":
            raise exception.AWSError(
                "The image you wish to migrate is EBS-based. " +
                "This method only works for instance-store images")
        files = self.get_image_files(image)
        if not files:
            log.info("No files found for image: %s" % image_id)
            return
        log.info("Migrating image: %s" % image_id)
        widgets = [files[0].name, progressbar.Percentage(), ' ',
                   progressbar.Bar(marker=progressbar.RotatingMarker()), ' ',
                   progressbar.ETA(), ' ', ' ']
        counter = 0
        num_files = len(files)
        pbar = progressbar.ProgressBar(widgets=widgets,
                                       maxval=num_files).start()
        for f in files:
            widgets[0] = "%s: (%s/%s)" % (f.name, counter + 1, num_files)
            # copy file to destination bucket with the same name
            f.copy(destbucket, f.name)
            pbar.update(counter)
            counter += 1
        pbar.finish()
        if migrate_manifest:
            dbucket = self.s3.get_bucket(destbucket)
            manifest_key = dbucket.get_key(self.get_image_manifest(image))
            f = tempfile.NamedTemporaryFile()
            manifest_key.get_contents_to_file(f.file)
            f.file.close()
            cmd = ('ec2-migrate-manifest -c %s -k %s -m %s --kernel %s ' +
                   '--ramdisk %s --no-mapping ') % (cert, private_key,
                                                    f.name, kernel_id,
                                                    ramdisk_id)
            register_cmd = "ec2-register %s/%s" % (destbucket,
                                                   manifest_key.name)
            if region:
                cmd += '--region %s' % region
                register_cmd += " --region %s" % region
            log.info("Migrating manifest file...")
            retval = os.system(cmd)
            if retval != 0:
                raise exception.BaseException(
                    "ec2-migrate-manifest failed with status %s" % retval)
            f.file = open(f.name, 'r')
            manifest_key.set_contents_from_file(f.file)
            # needed so that EC2 has permission to READ the manifest file
            manifest_key.add_email_grant('READ', 'za-team@amazon.com')
            f.close()
            os.unlink(f.name + '.bak')
            log.info("Manifest migrated successfully. You can now run:\n" +
                     register_cmd + "\nto register your migrated image.")

    def copy_image(self, source_region, source_image_id, name=None,
                   description=None, client_token=None, wait_for_copy=False):
        kwargs = locals()
        kwargs.pop('self')
        kwargs.pop('wait_for_copy')
        log.info("Copying %s from %s to %s" % (source_image_id, source_region,
                                               self.region.name))
        resp = self.conn.copy_image(**kwargs)
        log.info("New AMI in region %s: %s" %
                 (self.region.name, resp.image_id))
        if wait_for_copy:
            img = self.get_image(resp.image_id)
            self.wait_for_ami(img)
        return resp

    def wait_for_ami(self, ami):
        if ami.root_device_type == 'ebs':
            root = ami.block_device_mapping.get(ami.root_device_name)
            if root.snapshot_id:
                self.wait_for_snapshot(self.get_snapshot(root.snapshot_id))
            else:
                log.warn("The root device snapshot id is not yet available")
        s = utils.get_spinner("Waiting for '%s' to become available" % ami.id)
        try:
            while ami.state != 'available':
                ami.update()
                time.sleep(10)
        finally:
            s.stop()

    def copy_image_to_all_regions(self, source_region, source_image_id,
                                  name=None, description=None,
                                  client_token=None, add_region_to_desc=False,
                                  wait_for_copies=False):
        current_region = self.region
        self.connect_to_region(source_region)
        src_img = self.get_image(source_image_id)
        regions = self.regions.copy()
        regions.pop(source_region)
        log.info("Copying %s to regions:\n%s" %
                 (src_img.id, ', '.join(regions.keys())))
        name = name or src_img.name
        resps = {}
        for r in regions:
            self.connect_to_region(r)
            desc = description or ''
            if add_region_to_desc:
                desc += ' (%s)' % r.upper()
            resp = self.copy_image(src_img.region.name, src_img.id, name=name,
                                   description=desc,
                                   client_token=client_token)
            resps[r] = resp
        if wait_for_copies:
            for r in resps:
                self.connect_to_region(r)
                img = self.get_image(resps[r].image_id)
                self.wait_for_ami(img)
        self.connect_to_region(current_region.name)
        return resps

    def create_block_device_map(self, root_snapshot_id=None,
                                root_device_name='/dev/sda1',
                                add_ephemeral_drives=False,
                                num_ephemeral_drives=24, instance_store=False):
        """
        Utility method for building a new block_device_map for a given snapshot
        id. This is useful when creating a new image from a volume snapshot.
        The returned block device map can be used with self.register_image
        """
        bmap = boto.ec2.blockdevicemapping.BlockDeviceMapping()
        if root_snapshot_id:
            sda1 = boto.ec2.blockdevicemapping.BlockDeviceType()
            sda1.snapshot_id = root_snapshot_id
            sda1.delete_on_termination = True
            bmap[root_device_name] = sda1
        if add_ephemeral_drives:
            if not instance_store:
                drives = ['/dev/xvd%s%%s' % s for s in string.lowercase]
                for i in range(num_ephemeral_drives):
                    j, k = i % 26, i / 26
                    device_fmt = drives[k]
                    eph = boto.ec2.blockdevicemapping.BlockDeviceType()
                    eph.ephemeral_name = 'ephemeral%d' % i
                    bmap[device_fmt % chr(ord('a') + j)] = eph
            else:
                drives = ['sd%s%d' % (s, i) for i in range(1, 10)
                          for s in string.lowercase[1:]]
                for i in range(num_ephemeral_drives):
                    eph = boto.ec2.blockdevicemapping.BlockDeviceType()
                    eph.ephemeral_name = 'ephemeral%d' % i
                    bmap[drives[i]] = eph
        return bmap

    @print_timing("Downloading image")
    def download_image_files(self, image_id, destdir):
        """
        Downloads the manifest.xml and all AMI parts for image_id to destdir
        """
        if not os.path.isdir(destdir):
            raise exception.BaseException(
                "destination directory '%s' does not exist" % destdir)
        widgets = ['file: ', progressbar.Percentage(), ' ',
                   progressbar.Bar(marker=progressbar.RotatingMarker()), ' ',
                   progressbar.ETA(), ' ', progressbar.FileTransferSpeed()]
        files = self.get_image_files(image_id)

        def _dl_progress_cb(trans, total):
            pbar.update(trans)
        log.info("Downloading image: %s" % image_id)
        for file in files:
            widgets[0] = "%s:" % file.name
            pbar = progressbar.ProgressBar(widgets=widgets,
                                           maxval=file.size).start()
            file.get_contents_to_filename(os.path.join(destdir, file.name),
                                          cb=_dl_progress_cb)
            pbar.finish()

    def list_image_files(self, image_id):
        """
        Print a list of files for image_id to the screen
        """
        files = self.get_image_files(image_id)
        for file in files:
            print file.name

    @property
    def instances(self):
        return self.get_all_instances()

    @property
    def keypairs(self):
        return self.get_keypairs()

    def terminate_instances(self, instances=None):
        if instances:
            self.conn.terminate_instances(instances)

    def get_volumes(self, filters=None):
        """
        Returns a list of all EBS volumes
        """
        return self.conn.get_all_volumes(filters=filters)

    def get_volume(self, volume_id):
        """
        Returns EBS volume object representing volume_id.
        Raises exception.VolumeDoesNotExist if unsuccessful
        """
        try:
            return self.get_volumes(filters={'volume-id': volume_id})[0]
        except boto.exception.EC2ResponseError as e:
            if e.error_code == "InvalidVolume.NotFound":
                raise exception.VolumeDoesNotExist(volume_id)
            raise
        except IndexError:
            raise exception.VolumeDoesNotExist(volume_id)

    def get_volume_or_none(self, volume_id):
        """
        Returns EBS volume object representing volume_id.
        Returns None if unsuccessful
        """
        try:
            return self.get_volume(volume_id)
        except exception.VolumeDoesNotExist:
            pass

    def wait_for_volume(self, volume, status=None, state=None,
                        refresh_interval=5, log_func=log.info):
        if status:
            log_func("Waiting for %s to become '%s'..." % (volume.id, status),
                     extra=dict(__nonewline__=True))
            s = spinner.Spinner()
            s.start()
            while volume.update() != status:
                time.sleep(refresh_interval)
            s.stop()
        if state:
            log_func("Waiting for %s to transition to: %s... " %
                     (volume.id, state), extra=dict(__nonewline__=True))
            if not status:
                volume.update()
            s = spinner.Spinner()
            s.start()
            while volume.attachment_state() != state:
                time.sleep(refresh_interval)
                volume.update()
            s.stop()

    def wait_for_snapshot(self, snapshot, refresh_interval=30):
        snap = snapshot
        log.info("Waiting for snapshot to complete: %s" % snap.id)
        widgets = ['%s: ' % snap.id, '',
                   progressbar.Bar(marker=progressbar.RotatingMarker()),
                   '', progressbar.Percentage(), ' ', progressbar.ETA()]
        pbar = progressbar.ProgressBar(widgets=widgets, maxval=100).start()
        while snap.status != 'completed':
            try:
                progress = int(snap.update().replace('%', ''))
                if not pbar.finished:
                    pbar.update(progress)
            except ValueError:
                time.sleep(5)
                continue
            if snap.status != 'completed':
                time.sleep(refresh_interval)
        if not pbar.finished:
            pbar.finish()

    def create_snapshot(self, vol, description=None, wait_for_snapshot=False,
                        refresh_interval=30):
        log.info("Creating snapshot of volume: %s" % vol.id)
        snap = vol.create_snapshot(description)
        if wait_for_snapshot:
            self.wait_for_snapshot(snap, refresh_interval)
        return snap

    def get_snapshots(self, volume_ids=[], filters=None, owner='self'):
        """
        Returns a list of all EBS volume snapshots
        """
        filters = filters or {}
        if volume_ids:
            filters['volume-id'] = volume_ids
        return self.conn.get_all_snapshots(owner=owner, filters=filters)

    def get_snapshot(self, snapshot_id, owner='self'):
        """
        Returns EBS snapshot object for snapshot_id.

        Raises exception.SnapshotDoesNotExist if unsuccessful
        """
        try:
            return self.get_snapshots(filters={'snapshot-id': snapshot_id},
                                      owner=owner)[0]
        except boto.exception.EC2ResponseError as e:
            if e.error_code == "InvalidSnapshot.NotFound":
                raise exception.SnapshotDoesNotExist(snapshot_id)
            raise
        except IndexError:
            raise exception.SnapshotDoesNotExist(snapshot_id)

    def list_volumes(self, volume_id=None, status=None, attach_status=None,
                     size=None, zone=None, snapshot_id=None,
                     show_deleted=False, tags=None, name=None):
        """
        Print a list of volumes to the screen
        """
        filters = {}
        if status:
            filters['status'] = status
        else:
            filters['status'] = ['creating', 'available', 'in-use', 'error']
            if show_deleted:
                filters['status'] += ['deleting', 'deleted']
        if attach_status:
            filters['attachment.status'] = attach_status
        if volume_id:
            filters['volume-id'] = volume_id
        if size:
            filters['size'] = size
        if zone:
            filters['availability-zone'] = zone
        if snapshot_id:
            filters['snapshot-id'] = snapshot_id
        if tags:
            tagkeys = []
            for tag in tags:
                val = tags.get(tag)
                if val:
                    filters["tag:%s" % tag] = val
                elif tag:
                    tagkeys.append(tag)
            if tagkeys:
                filters['tag-key'] = tagkeys
        if name:
            filters['tag:Name'] = name
        vols = self.get_volumes(filters=filters)
        vols.sort(key=lambda x: x.create_time)
        if vols:
            for vol in vols:
                print "volume_id: %s" % vol.id
                print "size: %sGB" % vol.size
                print "status: %s" % vol.status
                if vol.attachment_state():
                    print "attachment_status: %s" % vol.attachment_state()
                print "availability_zone: %s" % vol.zone
                if vol.snapshot_id:
                    print "snapshot_id: %s" % vol.snapshot_id
                snapshots = self.get_snapshots(volume_ids=[vol.id])
                if snapshots:
                    snap_list = ' '.join([snap.id for snap in snapshots])
                    print 'snapshots: %s' % snap_list
                if vol.create_time:
                    lt = utils.iso_to_localtime_tuple(vol.create_time)
                print "create_time: %s" % lt
                tags = []
                for tag in vol.tags:
                    val = vol.tags.get(tag)
                    if val:
                        tags.append("%s=%s" % (tag, val))
                    else:
                        tags.append(tag)
                if tags:
                    print "tags: %s" % ', '.join(tags)
                print
        print 'Total: %s' % len(vols)

    def get_spot_history(self, instance_type, start=None, end=None, zone=None,
                         plot=False, plot_server_interface="localhost",
                         plot_launch_browser=True, plot_web_browser=None,
                         plot_shutdown_server=True, classic=False, vpc=False):
        if start and not utils.is_iso_time(start):
            raise exception.InvalidIsoDate(start)
        if end and not utils.is_iso_time(end):
            raise exception.InvalidIsoDate(end)
        if classic and vpc:
            raise exception.BaseException(
                "classic and vpc kwargs are mutually exclusive")
        if not classic and not vpc:
            vpc = self.default_vpc is not None
            classic = not vpc
        if classic:
            pdesc = "Linux/UNIX"
            short_pdesc = "EC2-Classic"
        else:
            pdesc = "Linux/UNIX (Amazon VPC)"
            short_pdesc = "VPC"
        log.info("Fetching spot history for %s (%s)" %
                 (instance_type, short_pdesc))
        hist = self.conn.get_spot_price_history(start_time=start, end_time=end,
                                                availability_zone=zone,
                                                instance_type=instance_type,
                                                product_description=pdesc)
        if not hist:
            raise exception.SpotHistoryError(start, end)
        dates = []
        prices = []
        data = []
        for item in hist:
            timestamp = utils.iso_to_javascript_timestamp(item.timestamp)
            price = item.price
            dates.append(timestamp)
            prices.append(price)
            data.append([timestamp, price])
        maximum = max(prices)
        avg = sum(prices) / float(len(prices))
        log.info("Current price: $%.4f" % prices[0])
        log.info("Max price: $%.4f" % maximum)
        log.info("Average price: $%.4f" % avg)
        if plot:
            xaxisrange = dates[-1] - dates[0]
            xpanrange = [dates[0] - xaxisrange / 2.,
                         dates[-1] + xaxisrange / 2.]
            xzoomrange = [0.1, xpanrange[-1] - xpanrange[0]]
            minimum = min(prices)
            yaxisrange = maximum - minimum
            ypanrange = [minimum - yaxisrange / 2., maximum + yaxisrange / 2.]
            yzoomrange = [0.1, ypanrange[-1] - ypanrange[0]]
            context = dict(instance_type=instance_type,
                           start=hist[-1].timestamp, end=hist[0].timestamp,
                           time_series_data=str(data).replace('L', ''),
                           shutdown=plot_shutdown_server,
                           xpanrange=xpanrange, ypanrange=ypanrange,
                           xzoomrange=xzoomrange, yzoomrange=yzoomrange)
            log.info("", extra=dict(__raw__=True))
            log.info("Starting StarCluster Webserver...")
            s = webtools.get_template_server('web', context=context,
                                             interface=plot_server_interface)
            base_url = "http://%s:%s" % s.server_address
            shutdown_url = '/'.join([base_url, 'shutdown'])
            spot_url = "http://%s:%s/spothistory.html" % s.server_address
            log.info("Server address is %s" % base_url)
            log.info("(use CTRL-C or navigate to %s to shutdown server)" %
                     shutdown_url)
            if plot_launch_browser:
                webtools.open_browser(spot_url, plot_web_browser)
            else:
                log.info("Browse to %s to view the spot history plot" %
                         spot_url)
            s.serve_forever()
        return data

    def show_console_output(self, instance_id):
        instance = self.get_instance(instance_id)
        console_output = instance.get_console_output().output or ''
        console_output = ''.join([c for c in console_output if c in
                                  string.printable])
        if console_output:
            print console_output
        else:
            log.info("No console output available...")


class EasyS3(EasyAWS):
    DefaultHost = 's3.amazonaws.com'
    _calling_format = boto.s3.connection.OrdinaryCallingFormat()

    def __init__(self, aws_access_key_id, aws_secret_access_key,
                 aws_s3_path='/', aws_port=None, aws_is_secure=True,
                 aws_s3_host=DefaultHost, aws_proxy=None, aws_proxy_port=None,
                 aws_proxy_user=None, aws_proxy_pass=None,
                 aws_validate_certs=True, **kwargs):
        kwargs = dict(is_secure=aws_is_secure, host=aws_s3_host or
                      self.DefaultHost, port=aws_port, path=aws_s3_path,
                      proxy=aws_proxy, proxy_port=aws_proxy_port,
                      proxy_user=aws_proxy_user, proxy_pass=aws_proxy_pass,
                      validate_certs=aws_validate_certs)
        if aws_s3_host:
            kwargs.update(dict(calling_format=self._calling_format))
        super(EasyS3, self).__init__(aws_access_key_id, aws_secret_access_key,
                                     boto.connect_s3, **kwargs)

    def __repr__(self):
        return '<EasyS3: %s>' % self.conn.server_name()

    def create_bucket(self, bucket_name):
        """
        Create a new bucket on S3. bucket_name must be unique, the bucket
        namespace is shared by all AWS users
        """
        bucket_name = bucket_name.split('/')[0]
        try:
            return self.conn.create_bucket(bucket_name)
        except boto.exception.S3CreateError as e:
            if e.error_code == "BucketAlreadyExists":
                raise exception.BucketAlreadyExists(bucket_name)
            raise

    def bucket_exists(self, bucket_name):
        """
        Check if bucket_name exists on S3
        """
        try:
            return self.get_bucket(bucket_name) is not None
        except exception.BucketDoesNotExist:
            return False

    def get_or_create_bucket(self, bucket_name):
        try:
            return self.get_bucket(bucket_name)
        except exception.BucketDoesNotExist:
            log.info("Creating bucket '%s'" % bucket_name)
            return self.create_bucket(bucket_name)

    def get_bucket_or_none(self, bucket_name):
        """
        Returns bucket object representing S3 bucket
        Returns None if unsuccessful
        """
        try:
            return self.get_bucket(bucket_name)
        except exception.BucketDoesNotExist:
            pass

    def get_bucket(self, bucketname):
        """
        Returns bucket object representing S3 bucket
        """
        try:
            return self.conn.get_bucket(bucketname)
        except boto.exception.S3ResponseError as e:
            if e.error_code == "NoSuchBucket":
                raise exception.BucketDoesNotExist(bucketname)
            raise

    def list_bucket(self, bucketname):
        bucket = self.get_bucket(bucketname)
        for file in bucket.list():
            if file.name:
                print file.name

    def get_buckets(self):
        try:
            buckets = self.conn.get_all_buckets()
        except TypeError:
            # hack until boto (or eucalyptus) fixes get_all_buckets
            raise exception.AWSError("AWS credentials are not valid")
        return buckets

    def list_buckets(self):
        for bucket in self.get_buckets():
            print bucket.name

    def get_bucket_files(self, bucketname):
        bucket = self.get_bucket(bucketname)
        files = [file for file in bucket.list()]
        return files


if __name__ == "__main__":
    from starcluster.config import get_easy_ec2
    ec2 = get_easy_ec2()
    ec2.list_all_instances()
    ec2.list_registered_images()

########NEW FILE########
__FILENAME__ = visualizer
# Copyright 2009-2014 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

"""
StarCluster SunGrinEngine stats visualizer module
"""
import os
import numpy as np
from datetime import datetime
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from starcluster.logger import log


class SGEVisualizer(object):
    """
    Stats Visualizer for SGE Load Balancer
    stats_file - file containing SGE load balancer stats
    pngpath - directory to dump the stat plots to
    """
    def __init__(self, stats_file, pngpath):
        self.pngpath = pngpath
        self.stats_file = stats_file
        self.records = None

    def read(self):
        list = []
        file = open(self.stats_file, 'r')
        for line in file:
            parts = line.rstrip().split(',')
            a = [datetime.strptime(parts[0], '%Y-%m-%d %H:%M:%S.%f'),
                 int(parts[1]), int(parts[2]), int(parts[3]), int(parts[4]),
                 int(parts[5]), int(parts[6]), float(parts[7])]
            list.append(a)
        file.close()
        names = ['dt', 'hosts', 'running_jobs', 'queued_jobs',
                 'slots', 'avg_duration', 'avg_wait', 'avg_load']
        self.records = np.rec.fromrecords(list, names=','.join(names))

    def graph(self, yaxis, title):
        if self.records is None:
            log.error("ERROR: File hasn't been read() yet.")
            return -1
        fig = plt.figure()
        ax = fig.add_subplot(111)
        ax.plot(self.records.dt, yaxis)
        ax.grid(True)
        fig.autofmt_xdate()
        filename = os.path.join(self.pngpath, title + '.png')
        plt.savefig(filename, dpi=100)
        log.debug("saved graph %s." % title)
        plt.close(fig)  # close it when its done

    def graph_all(self):
        self.read()
        vals = {'queued': self.records.queued_jobs,
                'running': self.records.running_jobs,
                'num_hosts': self.records.hosts,
                # 'slots': self.records.slots,
                'avg_duration': self.records.avg_duration,
                'avg_wait': self.records.avg_wait,
                'avg_load': self.records.avg_load}
        for sub in vals:
            self.graph(vals[sub], sub)
        log.info("Done making graphs.")

########NEW FILE########
__FILENAME__ = cli
# Copyright 2009-2014 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

"""
StarCluster Command Line Interface:

starcluster [global-opts] action [action-opts] [<action-args> ...]
"""
import os
import sys
import shlex
import socket
import optparse
import platform

from boto.exception import BotoServerError, EC2ResponseError, S3ResponseError

from starcluster import config
from starcluster import static
from starcluster import logger
from starcluster import commands
from starcluster import exception
from starcluster import completion
from starcluster.logger import log, console
from starcluster import __version__

__description__ = """
StarCluster - (http://star.mit.edu/cluster) (v. %s)
Software Tools for Academics and Researchers (STAR)
Please submit bug reports to starcluster@mit.edu
""" % __version__


class StarClusterCLI(object):
    """
    StarCluster Command Line Interface
    """
    def __init__(self):
        self._gparser = None
        self.subcmds_map = {}

    @property
    def gparser(self):
        if not self._gparser:
            self._gparser = self.create_global_parser()
        return self._gparser

    def print_header(self):
        print >> sys.stderr, __description__.replace('\n', '', 1)

    def parse_subcommands(self, gparser=None):
        """
        Parse global arguments, find subcommand from list of subcommand
        objects, parse local subcommand arguments and return a tuple of
        global options, selected command object, command options, and
        command arguments.

        Call execute() on the command object to run. The command object has
        members 'gopts' and 'opts' set for global and command options
        respectively, you don't need to call execute with those but you could
        if you wanted to.
        """
        gparser = gparser or self.gparser
        # parse global options.
        gopts, args = gparser.parse_args()
        if not args:
            gparser.print_help()
            raise SystemExit("\nError: you must specify an action.")
        # set debug level if specified
        if gopts.DEBUG:
            console.setLevel(logger.DEBUG)
            config.DEBUG_CONFIG = True
        # load StarClusterConfig into global options
        try:
            cfg = config.StarClusterConfig(gopts.CONFIG)
            cfg.load()
        except exception.ConfigNotFound, e:
            log.error(e.msg)
            e.display_options()
            sys.exit(1)
        except exception.ConfigError, e:
            log.error(e.msg)
            sys.exit(1)
        gopts.CONFIG = cfg
        # Parse command arguments and invoke command.
        subcmdname, subargs = args[0], args[1:]
        try:
            sc = self.subcmds_map[subcmdname]
            lparser = optparse.OptionParser(sc.__doc__.strip())
            sc.gopts = gopts
            sc.parser = lparser
            sc.gparser = gparser
            sc.subcmds_map = self.subcmds_map
            sc.addopts(lparser)
            sc.opts, subsubargs = lparser.parse_args(subargs)
        except KeyError:
            raise SystemExit("Error: invalid command '%s'" % subcmdname)
        return gopts, sc, sc.opts, subsubargs

    def create_global_parser(self, subcmds=None, no_usage=False,
                             add_help=True):
        if no_usage:
            gparser = optparse.OptionParser(usage=optparse.SUPPRESS_USAGE,
                                            add_help_option=add_help)
        else:
            gparser = optparse.OptionParser(__doc__.strip(),
                                            version=__version__,
                                            add_help_option=add_help)
            # Build map of name -> command and docstring.
            cmds_header = 'Available Commands:'
            gparser.usage += '\n\n%s\n' % cmds_header
            gparser.usage += '%s\n' % ('-' * len(cmds_header))
            gparser.usage += "NOTE: Pass --help to any command for a list of "
            gparser.usage += 'its options and detailed usage information\n\n'
            subcmds = subcmds or commands.all_cmds
            for sc in subcmds:
                helptxt = sc.__doc__.splitlines()[3].strip()
                gparser.usage += '- %s: %s\n' % (', '.join(sc.names), helptxt)
                for n in sc.names:
                    assert n not in self.subcmds_map
                    self.subcmds_map[n] = sc
        gparser.add_option("-d", "--debug", dest="DEBUG",
                           action="store_true", default=False,
                           help="print debug messages (useful for "
                           "diagnosing problems)")
        gparser.add_option("-c", "--config", dest="CONFIG", action="store",
                           metavar="FILE",
                           help="use alternate config file (default: %s)" %
                           static.STARCLUSTER_CFG_FILE)
        gparser.add_option("-r", "--region", dest="REGION", action="store",
                           help="specify a region to use (default: us-east-1)")
        gparser.disable_interspersed_args()
        return gparser

    def __write_module_version(self, modname, fp):
        """
        Write module version information to a file
        """
        try:
            mod = __import__(modname)
            fp.write("%s: %s\n" % (mod.__name__, mod.__version__))
        except Exception, e:
            print "error getting version for '%s' module: %s" % (modname, e)

    def bug_found(self):
        """
        Builds a crash-report when StarCluster encounters an unhandled
        exception. Report includes system info, python version, dependency
        versions, and a full debug log and stack-trace of the crash.
        """
        dashes = '-' * 10
        header = dashes + ' %s ' + dashes + '\n'
        crashfile = open(static.CRASH_FILE, 'w')
        argv = sys.argv[:]
        argv[0] = os.path.basename(argv[0])
        argv = ' '.join(argv)
        crashfile.write(header % "SYSTEM INFO")
        crashfile.write("StarCluster: %s\n" % __version__)
        crashfile.write("Python: %s\n" % sys.version.replace('\n', ' '))
        crashfile.write("Platform: %s\n" % platform.platform())
        dependencies = ['boto', 'paramiko', 'Crypto']
        for dep in dependencies:
            self.__write_module_version(dep, crashfile)
        crashfile.write("\n" + header % "CRASH DETAILS")
        crashfile.write('Command: %s\n\n' % argv)
        for line in logger.get_session_log():
            crashfile.write(line)
        crashfile.close()
        print
        log.error("Oops! Looks like you've found a bug in StarCluster")
        log.error("Crash report written to: %s" % static.CRASH_FILE)
        log.error("Please remove any sensitive data from the crash report")
        log.error("and submit it to starcluster@mit.edu")
        sys.exit(1)

    def get_global_opts(self):
        """
        Parse and return global options. This method will silently return None
        if any errors are encountered during parsing.
        """
        gparser = self.create_global_parser(no_usage=True, add_help=False)
        try:
            sys.stdout = open(os.devnull, 'w')
            sys.stderr = open(os.devnull, 'w')
            gopts, _ = gparser.parse_args()
            return gopts
        except SystemExit:
            pass
        finally:
            sys.stdout = sys.__stdout__
            sys.stderr = sys.__stderr__

    def is_completion_active(self):
        return 'OPTPARSE_AUTO_COMPLETE' in os.environ

    def _init_completion(self):
        """
        Restore original sys.argv from COMP_LINE in the case that starcluster
        is being called by Bash/ZSH for completion options. Bash/ZSH will
        simply call 'starcluster' with COMP_LINE environment variable set to
        the current (partial) argv for completion.

        StarCluster's Bash/ZSH completion code needs to read the global config
        option in case an alternate config is specified at the command line
        when completing options. StarCluster's completion code uses the config
        to generate completion options. Setting sys.argv to $COMP_LINE in this
        case allows the global option parser to be used to extract the global
        -c option (if specified) and load the proper config in the completion
        code.
        """
        if 'COMP_LINE' in os.environ:
            newargv = shlex.split(os.environ.get('COMP_LINE'))
            for i, arg in enumerate(newargv):
                arg = os.path.expanduser(arg)
                newargv[i] = os.path.expandvars(arg)
            sys.argv = newargv

    def handle_completion(self):
        if self.is_completion_active():
            gparser = self.create_global_parser(no_usage=True, add_help=False)
            # set sys.path to COMP_LINE if it exists
            self._init_completion()
            # fetch the global options
            gopts = self.get_global_opts()
            # try to load StarClusterConfig into global options
            if gopts:
                try:
                    cfg = config.StarClusterConfig(gopts.CONFIG)
                    cfg.load()
                except exception.ConfigError:
                    cfg = None
                gopts.CONFIG = cfg
            scmap = {}
            for sc in commands.all_cmds:
                sc.gopts = gopts
                for n in sc.names:
                    scmap[n] = sc
            listcter = completion.ListCompleter(scmap.keys())
            subcter = completion.NoneCompleter()
            completion.autocomplete(gparser, listcter, None, subcter,
                                    subcommands=scmap)
            sys.exit(1)

    def main(self):
        """
        StarCluster main
        """
        # Handle Bash/ZSH completion if necessary
        self.handle_completion()
        # Show StarCluster header
        self.print_header()
        # Parse subcommand options and args
        gopts, sc, opts, args = self.parse_subcommands()
        if args and args[0] == 'help':
            # make 'help' subcommand act like --help option
            sc.parser.print_help()
            sys.exit(0)
        # run the subcommand and handle exceptions
        try:
            sc.execute(args)
        except (EC2ResponseError, S3ResponseError, BotoServerError), e:
            log.error("%s: %s" % (e.error_code, e.error_message),
                      exc_info=True)
            sys.exit(1)
        except socket.error, e:
            log.exception("Connection error:")
            log.error("Check your internet connection?")
            sys.exit(1)
        except exception.ThreadPoolException, e:
            log.error(e.format_excs())
            self.bug_found()
        except exception.ClusterDoesNotExist, e:
            cm = gopts.CONFIG.get_cluster_manager()
            cls = ''
            try:
                cls = cm.get_clusters(load_plugins=False, load_receipt=False)
            except:
                log.debug("Error fetching cluster list", exc_info=True)
            log.error(e.msg)
            if cls:
                taglist = ', '.join([c.cluster_tag for c in cls])
                active_clusters = "(active clusters: %s)" % taglist
                log.error(active_clusters)
            sys.exit(1)
        except exception.BaseException, e:
            log.error(e.msg, extra={'__textwrap__': True})
            log.debug(e.msg, exc_info=True)
            sys.exit(1)
        except SystemExit:
            # re-raise SystemExit to avoid the bug-catcher below
            raise
        except Exception:
            log.error("Unhandled exception occured", exc_info=True)
            self.bug_found()


def warn_debug_file_moved():
    old_file = os.path.join(static.TMP_DIR, 'starcluster-debug-%s.log' %
                            static.CURRENT_USER)
    if os.path.exists(old_file):
        stars = '*' * 50
        log.warn(stars)
        log.warn("The default log file location is now:")
        log.warn("")
        log.warn(static.DEBUG_FILE)
        log.warn("")
        log.warn("Please delete or move the old log file located at:")
        log.warn("")
        log.warn(old_file)
        log.warn(stars)


def main():
    try:
        static.create_sc_config_dirs()
        logger.configure_sc_logging()
        warn_debug_file_moved()
        StarClusterCLI().main()
    except KeyboardInterrupt:
        print "Interrupted, exiting."
        sys.exit(1)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = cluster
# Copyright 2009-2014 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

import os
import re
import time
import string
import pprint
import warnings
import datetime

import iptools

from starcluster import utils
from starcluster import static
from starcluster import sshutils
from starcluster import managers
from starcluster import userdata
from starcluster import deathrow
from starcluster import exception
from starcluster import threadpool
from starcluster import validators
from starcluster import progressbar
from starcluster import clustersetup
from starcluster.node import Node
from starcluster.plugins import sge
from starcluster.utils import print_timing
from starcluster.templates import user_msgs
from starcluster.logger import log


class ClusterManager(managers.Manager):
    """
    Manager class for Cluster objects
    """
    def __repr__(self):
        return "<ClusterManager: %s>" % self.ec2.region.name

    def get_cluster(self, cluster_name, group=None, load_receipt=True,
                    load_plugins=True, load_volumes=True, require_keys=True):
        """
        Returns a Cluster object representing an active cluster
        """
        try:
            clname = self._get_cluster_name(cluster_name)
            cltag = self.get_tag_from_sg(clname)
            if not group:
                group = self.ec2.get_security_group(clname)
            cl = Cluster(ec2_conn=self.ec2, cluster_tag=cltag,
                         cluster_group=group)
            if load_receipt:
                cl.load_receipt(load_plugins=load_plugins,
                                load_volumes=load_volumes)
            try:
                cl.keyname = cl.keyname or cl.master_node.key_name
                key_location = self.cfg.get_key(cl.keyname).get('key_location')
                cl.key_location = key_location
                if require_keys:
                    cl.validator.validate_keypair()
            except (exception.KeyNotFound, exception.MasterDoesNotExist):
                if require_keys:
                    raise
                cl.key_location = ''
            return cl
        except exception.SecurityGroupDoesNotExist:
            raise exception.ClusterDoesNotExist(cluster_name)

    def get_clusters(self, load_receipt=True, load_plugins=True):
        """
        Returns a list of all active clusters
        """
        cluster_groups = self.get_cluster_security_groups()
        clusters = [self.get_cluster(g.name, group=g,
                                     load_receipt=load_receipt,
                                     load_plugins=load_plugins)
                    for g in cluster_groups]
        return clusters

    def get_default_cluster_template(self):
        """
        Returns name of the default cluster template defined in the config
        """
        return self.cfg.get_default_cluster_template()

    def get_cluster_template(self, template_name, tag_name=None):
        """
        Returns a new Cluster object using the settings from the cluster
        template template_name

        If tag_name is passed, the Cluster object's cluster_tag setting will
        be set to tag_name
        """
        cl = self.cfg.get_cluster_template(template_name, tag_name=tag_name,
                                           ec2_conn=self.ec2)
        return cl

    def get_cluster_or_none(self, cluster_name, **kwargs):
        """
        Same as get_cluster but returns None instead of throwing an exception
        if the cluster does not exist
        """
        try:
            return self.get_cluster(cluster_name, **kwargs)
        except exception.ClusterDoesNotExist:
            pass

    def cluster_exists(self, tag_name):
        """
        Returns True if cluster exists
        """
        return self.get_cluster_or_none(tag_name) is not None

    def ssh_to_master(self, cluster_name, user='root', command=None,
                      forward_x11=False, forward_agent=False,
                      pseudo_tty=False):
        """
        ssh to master node of cluster_name

        user keyword specifies an alternate user to login as
        """
        cluster = self.get_cluster(cluster_name, load_receipt=False,
                                   require_keys=True)
        return cluster.ssh_to_master(user=user, command=command,
                                     forward_x11=forward_x11,
                                     forward_agent=forward_agent,
                                     pseudo_tty=pseudo_tty)

    def ssh_to_cluster_node(self, cluster_name, node_id, user='root',
                            command=None, forward_x11=False,
                            forward_agent=False, pseudo_tty=False):
        """
        ssh to a node in cluster_name that has either an id,
        dns name, or alias matching node_id

        user keyword specifies an alternate user to login as
        """
        cluster = self.get_cluster(cluster_name, load_receipt=False,
                                   require_keys=False)
        node = cluster.get_node(node_id)
        key_location = self.cfg.get_key(node.key_name).get('key_location')
        cluster.key_location = key_location
        cluster.keyname = node.key_name
        cluster.validator.validate_keypair()
        return node.shell(user=user, forward_x11=forward_x11,
                          forward_agent=forward_agent,
                          pseudo_tty=pseudo_tty, command=command)

    def _get_cluster_name(self, cluster_name):
        """
        Returns human readable cluster name/tag prefixed with '@sc-'
        """
        if not cluster_name.startswith(static.SECURITY_GROUP_PREFIX):
            cluster_name = static.SECURITY_GROUP_TEMPLATE % cluster_name
        return cluster_name

    def add_node(self, cluster_name, alias=None, no_create=False,
                 image_id=None, instance_type=None, zone=None,
                 placement_group=None, spot_bid=None):
        cl = self.get_cluster(cluster_name)
        return cl.add_node(alias=alias, image_id=image_id,
                           instance_type=instance_type, zone=zone,
                           placement_group=placement_group, spot_bid=spot_bid,
                           no_create=no_create)

    def add_nodes(self, cluster_name, num_nodes, aliases=None, no_create=False,
                  image_id=None, instance_type=None, zone=None,
                  placement_group=None, spot_bid=None):
        """
        Add one or more nodes to cluster
        """
        cl = self.get_cluster(cluster_name)
        return cl.add_nodes(num_nodes, aliases=aliases, image_id=image_id,
                            instance_type=instance_type, zone=zone,
                            placement_group=placement_group, spot_bid=spot_bid,
                            no_create=no_create)

    def remove_node(self, cluster_name, alias=None, terminate=True,
                    force=False):
        """
        Remove a single node from a cluster
        """
        cl = self.get_cluster(cluster_name)
        n = cl.get_node(alias) if alias else None
        return cl.remove_node(node=n, terminate=terminate, force=force)

    def remove_nodes(self, cluster_name, num_nodes=None, aliases=None,
                     terminate=True, force=False):
        """
        Remove one or more nodes from cluster
        """
        cl = self.get_cluster(cluster_name)
        nodes = cl.get_nodes(aliases) if aliases else None
        return cl.remove_nodes(nodes=nodes, num_nodes=num_nodes,
                               terminate=terminate, force=force)

    def restart_cluster(self, cluster_name, reboot_only=False):
        """
        Reboots and reconfigures cluster_name
        """
        cl = self.get_cluster(cluster_name)
        cl.restart_cluster(reboot_only=reboot_only)

    def stop_cluster(self, cluster_name, terminate_unstoppable=False,
                     force=False):
        """
        Stop an EBS-backed cluster
        """
        cl = self.get_cluster(cluster_name, load_receipt=not force,
                              require_keys=not force)
        cl.stop_cluster(terminate_unstoppable, force=force)

    def terminate_cluster(self, cluster_name, force=False):
        """
        Terminates cluster_name
        """
        cl = self.get_cluster(cluster_name, load_receipt=not force,
                              require_keys=not force)
        cl.terminate_cluster(force=force)

    def get_cluster_security_group(self, group_name):
        """
        Return cluster security group by appending '@sc-' to group_name and
        querying EC2.
        """
        gname = self._get_cluster_name(group_name)
        return self.ec2.get_security_group(gname)

    def get_cluster_group_or_none(self, group_name):
        try:
            return self.get_cluster_security_group(group_name)
        except exception.SecurityGroupDoesNotExist:
            pass

    def get_cluster_security_groups(self):
        """
        Return all security groups on EC2 that start with '@sc-'
        """
        glob = static.SECURITY_GROUP_TEMPLATE % '*'
        sgs = self.ec2.get_security_groups(filters={'group-name': glob})
        return sgs

    def get_tag_from_sg(self, sg):
        """
        Returns the cluster tag name from a security group name that starts
        with static.SECURITY_GROUP_PREFIX

        Example:
            sg = '@sc-mycluster'
            print get_tag_from_sg(sg)
            mycluster
        """
        regex = re.compile('^' + static.SECURITY_GROUP_TEMPLATE % '(.*)')
        match = regex.match(sg)
        tag = None
        if match:
            tag = match.groups()[0]
        if not tag:
            raise ValueError("Invalid cluster group name: %s" % sg)
        return tag

    def list_clusters(self, cluster_groups=None, show_ssh_status=False):
        """
        Prints a summary for each active cluster on EC2
        """
        if not cluster_groups:
            cluster_groups = self.get_cluster_security_groups()
            if not cluster_groups:
                log.info("No clusters found...")
        else:
            try:
                cluster_groups = [self.get_cluster_security_group(g) for g
                                  in cluster_groups]
            except exception.SecurityGroupDoesNotExist:
                raise exception.ClusterDoesNotExist(g)
        for scg in cluster_groups:
            tag = self.get_tag_from_sg(scg.name)
            try:
                cl = self.get_cluster(tag, group=scg, load_plugins=False,
                                      load_volumes=False, require_keys=False)
            except exception.IncompatibleCluster as e:
                sep = '*' * 60
                log.error('\n'.join([sep, e.msg, sep]),
                          extra=dict(__textwrap__=True))
                print
                continue
            header = '%s (security group: %s)' % (tag, scg.name)
            print '-' * len(header)
            print header
            print '-' * len(header)
            nodes = cl.nodes
            try:
                n = nodes[0]
            except IndexError:
                n = None
            state = getattr(n, 'state', None)
            ltime = 'N/A'
            uptime = 'N/A'
            if state in ['pending', 'running']:
                ltime = getattr(n, 'local_launch_time', 'N/A')
                uptime = getattr(n, 'uptime', 'N/A')
            print 'Launch time: %s' % ltime
            print 'Uptime: %s' % uptime
            if scg.vpc_id:
                print 'VPC: %s' % scg.vpc_id
                print 'Subnet: %s' % getattr(n, 'subnet_id', 'N/A')
            print 'Zone: %s' % getattr(n, 'placement', 'N/A')
            print 'Keypair: %s' % getattr(n, 'key_name', 'N/A')
            ebs_vols = []
            for node in nodes:
                devices = node.attached_vols
                if not devices:
                    continue
                node_id = node.alias or node.id
                for dev in devices:
                    d = devices.get(dev)
                    vol_id = d.volume_id
                    status = d.status
                    ebs_vols.append((vol_id, node_id, dev, status))
            if ebs_vols:
                print 'EBS volumes:'
                for vid, nid, dev, status in ebs_vols:
                    print('    %s on %s:%s (status: %s)' %
                          (vid, nid, dev, status))
            else:
                print 'EBS volumes: N/A'
            spot_reqs = cl.spot_requests
            if spot_reqs:
                active = len([s for s in spot_reqs if s.state == 'active'])
                opn = len([s for s in spot_reqs if s.state == 'open'])
                msg = ''
                if active != 0:
                    msg += '%d active' % active
                if opn != 0:
                    if msg:
                        msg += ', '
                    msg += '%d open' % opn
                print 'Spot requests: %s' % msg
            if nodes:
                print 'Cluster nodes:'
                for node in nodes:
                    nodeline = "    %7s %s %s %s" % (node.alias, node.state,
                                                     node.id, node.addr or '')
                    if node.spot_id:
                        nodeline += ' (spot %s)' % node.spot_id
                    if show_ssh_status:
                        ssh_status = {True: 'Up', False: 'Down'}
                        nodeline += ' (SSH: %s)' % ssh_status[node.is_up()]
                    print nodeline
                print 'Total nodes: %d' % len(nodes)
            else:
                print 'Cluster nodes: N/A'
            print

    def run_plugin(self, plugin_name, cluster_tag):
        """
        Run a plugin defined in the config.

        plugin_name must match the plugin's section name in the config
        cluster_tag specifies the cluster to run the plugin on
        """
        cl = self.get_cluster(cluster_tag, load_plugins=False)
        if not cl.is_cluster_up():
            raise exception.ClusterNotRunning(cluster_tag)
        plugs = [self.cfg.get_plugin(plugin_name)]
        plug = deathrow._load_plugins(plugs)[0]
        cl.run_plugin(plug, name=plugin_name)


class Cluster(object):

    def __init__(self,
                 ec2_conn=None,
                 spot_bid=None,
                 cluster_tag=None,
                 cluster_description=None,
                 cluster_size=None,
                 cluster_user=None,
                 cluster_shell=None,
                 dns_prefix=None,
                 master_image_id=None,
                 master_instance_type=None,
                 node_image_id=None,
                 node_instance_type=None,
                 node_instance_types=[],
                 availability_zone=None,
                 keyname=None,
                 key_location=None,
                 volumes=[],
                 plugins=[],
                 permissions=[],
                 userdata_scripts=[],
                 refresh_interval=30,
                 disable_queue=False,
                 num_threads=20,
                 disable_threads=False,
                 cluster_group=None,
                 force_spot_master=False,
                 disable_cloudinit=False,
                 subnet_id=None,
                 public_ips=None,
                 **kwargs):
        # update class vars with given vars
        _vars = locals().copy()
        del _vars['cluster_group']
        del _vars['ec2_conn']
        self.__dict__.update(_vars)

        # more configuration
        now = time.strftime("%Y%m%d%H%M")
        if self.cluster_tag is None:
            self.cluster_tag = "cluster%s" % now
        if cluster_description is None:
            self.cluster_description = "Cluster created at %s" % now
        self.ec2 = ec2_conn
        self.cluster_size = cluster_size or 0
        self.volumes = self.load_volumes(volumes)
        self.plugins = self.load_plugins(plugins)
        self.userdata_scripts = userdata_scripts or []
        self.dns_prefix = dns_prefix and cluster_tag

        self._cluster_group = None
        self._placement_group = None
        self._subnet = None
        self._zone = None
        self._master = None
        self._nodes = []
        self._pool = None
        self._progress_bar = None
        self.__default_plugin = None
        self.__sge_plugin = None

    def __repr__(self):
        return '<Cluster: %s (%s-node)>' % (self.cluster_tag,
                                            self.cluster_size)

    @property
    def zone(self):
        if not self._zone:
            self._zone = self._get_cluster_zone()
        return self._zone

    def _get_cluster_zone(self):
        """
        Returns the cluster's zone. If volumes are specified, this method
        determines the common zone between those volumes. If a zone is
        explicitly specified in the config and does not match the common zone
        of the volumes, an exception is raised. If all volumes are not in the
        same zone an exception is raised. If no volumes are specified, returns
        the user-specified zone if it exists. Returns None if no volumes and no
        zone is specified.
        """
        zone = None
        if self.availability_zone:
            zone = self.ec2.get_zone(self.availability_zone)
        common_zone = None
        for volume in self.volumes:
            volid = self.volumes.get(volume).get('volume_id')
            vol = self.ec2.get_volume(volid)
            if not common_zone:
                common_zone = vol.zone
            elif vol.zone != common_zone:
                vols = [self.volumes.get(v).get('volume_id')
                        for v in self.volumes]
                raise exception.VolumesZoneError(vols)
        if common_zone and zone and zone.name != common_zone:
            raise exception.InvalidZone(zone.name, common_zone)
        if not zone and common_zone:
            zone = self.ec2.get_zone(common_zone)
        if not zone:
            try:
                zone = self.ec2.get_zone(self.master_node.placement)
            except exception.MasterDoesNotExist:
                pass
        return zone

    @property
    def _plugins(self):
        return [p.__plugin_metadata__ for p in self.plugins]

    def load_plugins(self, plugins):
        if plugins and isinstance(plugins[0], dict):
            warnings.warn("In a future release the plugins kwarg for Cluster "
                          "will require a list of plugin objects and not a "
                          "list of dicts", DeprecationWarning)
            plugins = deathrow._load_plugins(plugins)
        return plugins

    @property
    def _default_plugin(self):
        if not self.__default_plugin:
            self.__default_plugin = clustersetup.DefaultClusterSetup(
                disable_threads=self.disable_threads,
                num_threads=self.num_threads)
        return self.__default_plugin

    @property
    def _sge_plugin(self):
        if not self.__sge_plugin:
            self.__sge_plugin = sge.SGEPlugin(
                disable_threads=self.disable_threads,
                num_threads=self.num_threads)
        return self.__sge_plugin

    def load_volumes(self, vols):
        """
        Iterate through vols and set device/partition settings automatically if
        not specified.

        This method assigns the first volume to /dev/sdz, second to /dev/sdy,
        etc. for all volumes that do not include a device/partition setting
        """
        devices = ['/dev/sd%s' % s for s in string.lowercase]
        devmap = {}
        for volname in vols:
            vol = vols.get(volname)
            dev = vol.get('device')
            if dev in devices:
                # rm user-defined devices from the list of auto-assigned
                # devices
                devices.remove(dev)
            volid = vol.get('volume_id')
            if dev and volid not in devmap:
                devmap[volid] = dev
        volumes = utils.AttributeDict()
        for volname in vols:
            vol = vols.get(volname)
            vol_id = vol.get('volume_id')
            device = vol.get('device')
            if not device:
                if vol_id in devmap:
                    device = devmap.get(vol_id)
                else:
                    device = devices.pop()
                    devmap[vol_id] = device
            if not utils.is_valid_device(device):
                raise exception.InvalidDevice(device)
            v = volumes[volname] = utils.AttributeDict()
            v.update(vol)
            v['device'] = device
            part = vol.get('partition')
            if part:
                partition = device + str(part)
                if not utils.is_valid_partition(partition):
                    raise exception.InvalidPartition(part)
                v['partition'] = partition
        return volumes

    def update(self, kwargs):
        for key in kwargs.keys():
            if hasattr(self, key):
                self.__dict__[key] = kwargs[key]

    def get(self, name):
        return self.__dict__.get(name)

    def __str__(self):
        cfg = self.__getstate__()
        return pprint.pformat(cfg)

    def load_receipt(self, load_plugins=True, load_volumes=True):
        """
        Load the original settings used to launch this cluster into this
        Cluster object. Settings are loaded from cluster group tags and the
        master node's user data.
        """
        try:
            tags = self.cluster_group.tags
            version = tags.get(static.VERSION_TAG, '')
            if utils.program_version_greater(version, static.VERSION):
                d = dict(cluster=self.cluster_tag, old_version=static.VERSION,
                         new_version=version)
                msg = user_msgs.version_mismatch % d
                sep = '*' * 60
                log.warn('\n'.join([sep, msg, sep]), extra={'__textwrap__': 1})
            self.update(self._get_settings_from_tags())
            if not (load_plugins or load_volumes):
                return True
            try:
                master = self.master_node
            except exception.MasterDoesNotExist:
                unfulfilled_spots = [sr for sr in self.spot_requests if not
                                     sr.instance_id]
                if unfulfilled_spots:
                    self.wait_for_active_spots()
                    master = self.master_node
                else:
                    raise
            if load_plugins:
                self.plugins = self.load_plugins(master.get_plugins())
            if load_volumes:
                self.volumes = master.get_volumes()
        except exception.PluginError:
            log.error("An error occurred while loading plugins: ",
                      exc_info=True)
            raise
        except exception.MasterDoesNotExist:
            raise
        except Exception:
            log.debug('load receipt exception: ', exc_info=True)
            raise exception.IncompatibleCluster(self.cluster_group)
        return True

    def __getstate__(self):
        cfg = {}
        exclude = ['key_location', 'plugins']
        include = ['_zone', '_plugins']
        for key in self.__dict__.keys():
            private = key.startswith('_')
            if (not private or key in include) and key not in exclude:
                val = getattr(self, key)
                if type(val) in [str, unicode, bool, int, float, list, dict]:
                    cfg[key] = val
                elif isinstance(val, utils.AttributeDict):
                    cfg[key] = dict(val)
        return cfg

    @property
    def _security_group(self):
        return static.SECURITY_GROUP_TEMPLATE % self.cluster_tag

    @property
    def subnet(self):
        if not self._subnet and self.subnet_id:
            self._subnet = self.ec2.get_subnet(self.subnet_id)
        return self._subnet

    @property
    def cluster_group(self):
        if self._cluster_group:
            return self._cluster_group
        sg = self.ec2.get_group_or_none(self._security_group)
        if not sg:
            desc = 'StarCluster-%s' % static.VERSION.replace('.', '_')
            if self.subnet:
                desc += ' (VPC)'
            vpc_id = getattr(self.subnet, 'vpc_id', None)
            sg = self.ec2.create_group(self._security_group,
                                       description=desc,
                                       auth_ssh=True,
                                       auth_group_traffic=True,
                                       vpc_id=vpc_id)
            self._add_tags_to_sg(sg)
        self._add_permissions_to_sg(sg)
        self._cluster_group = sg
        return sg

    def _add_permissions_to_sg(self, sg):
        ssh_port = static.DEFAULT_SSH_PORT
        for p in self.permissions:
            perm = self.permissions.get(p)
            ip_protocol = perm.get('ip_protocol', 'tcp')
            from_port = perm.get('from_port')
            to_port = perm.get('to_port')
            cidr_ip = perm.get('cidr_ip', static.WORLD_CIDRIP)
            if not self.ec2.has_permission(sg, ip_protocol, from_port,
                                           to_port, cidr_ip):
                log.info("Opening %s port range %s-%s for CIDR %s" %
                         (ip_protocol, from_port, to_port, cidr_ip))
                sg.authorize(ip_protocol, from_port, to_port, cidr_ip)
            else:
                log.info("Already open: %s port range %s-%s for CIDR %s" %
                         (ip_protocol, from_port, to_port, cidr_ip))
            includes_ssh = from_port <= ssh_port <= to_port
            open_to_world = cidr_ip == static.WORLD_CIDRIP
            if ip_protocol == 'tcp' and includes_ssh and not open_to_world:
                sg.revoke(ip_protocol, ssh_port, ssh_port,
                          static.WORLD_CIDRIP)

    def _add_chunked_tags(self, sg, chunks, base_tag_name):
        for i, chunk in enumerate(chunks):
            tag = "%s-%s" % (base_tag_name, i) if i != 0 else base_tag_name
            if tag not in sg.tags:
                sg.add_tag(tag, chunk)

    def _add_tags_to_sg(self, sg):
        if static.VERSION_TAG not in sg.tags:
            sg.add_tag(static.VERSION_TAG, str(static.VERSION))
        core_settings = dict(cluster_size=self.cluster_size,
                             master_image_id=self.master_image_id,
                             master_instance_type=self.master_instance_type,
                             node_image_id=self.node_image_id,
                             node_instance_type=self.node_instance_type,
                             availability_zone=self.availability_zone,
                             dns_prefix=self.dns_prefix,
                             subnet_id=self.subnet_id,
                             public_ips=self.public_ips,
                             disable_queue=self.disable_queue,
                             disable_cloudinit=self.disable_cloudinit)
        user_settings = dict(cluster_user=self.cluster_user,
                             cluster_shell=self.cluster_shell,
                             keyname=self.keyname, spot_bid=self.spot_bid)
        core = utils.dump_compress_encode(core_settings, use_json=True,
                                          chunk_size=static.MAX_TAG_LEN)
        self._add_chunked_tags(sg, core, static.CORE_TAG)
        user = utils.dump_compress_encode(user_settings, use_json=True,
                                          chunk_size=static.MAX_TAG_LEN)
        self._add_chunked_tags(sg, user, static.USER_TAG)

    def _load_chunked_tags(self, sg, base_tag_name):
        tags = [i for i in sg.tags if i.startswith(base_tag_name)]
        tags.sort()
        chunks = [sg.tags[i] for i in tags if i.startswith(base_tag_name)]
        return utils.decode_uncompress_load(chunks, use_json=True)

    def _get_settings_from_tags(self, sg=None):
        sg = sg or self.cluster_group
        cluster = {}
        if static.CORE_TAG in sg.tags:
            cluster.update(self._load_chunked_tags(sg, static.CORE_TAG))
        if static.USER_TAG in sg.tags:
            cluster.update(self._load_chunked_tags(sg, static.USER_TAG))
        return cluster

    @property
    def placement_group(self):
        if self._placement_group is None:
            pg = self.ec2.get_or_create_placement_group(self._security_group)
            self._placement_group = pg
        return self._placement_group

    @property
    def master_node(self):
        if not self._master:
            for node in self.nodes:
                if node.is_master():
                    self._master = node
            if not self._master:
                raise exception.MasterDoesNotExist()
        self._master.key_location = self.key_location
        return self._master

    @property
    def nodes(self):
        states = ['pending', 'running', 'stopping', 'stopped']
        filters = {'instance-state-name': states,
                   'instance.group-name': self._security_group}
        nodes = self.ec2.get_all_instances(filters=filters)
        # remove any cached nodes not in the current node list from EC2
        current_ids = [n.id for n in nodes]
        remove_nodes = [n for n in self._nodes if n.id not in current_ids]
        for node in remove_nodes:
            self._nodes.remove(node)
        # update node cache with latest instance data from EC2
        existing_nodes = dict([(n.id, n) for n in self._nodes])
        log.debug('existing nodes: %s' % existing_nodes)
        for node in nodes:
            if node.id in existing_nodes:
                log.debug('updating existing node %s in self._nodes' % node.id)
                enode = existing_nodes.get(node.id)
                enode.key_location = self.key_location
                enode.instance = node
            else:
                log.debug('adding node %s to self._nodes list' % node.id)
                n = Node(node, self.key_location)
                if n.is_master():
                    self._master = n
                    self._nodes.insert(0, n)
                else:
                    self._nodes.append(n)
        self._nodes.sort(key=lambda n: n.alias)
        log.debug('returning self._nodes = %s' % self._nodes)
        return self._nodes

    def get_nodes_or_raise(self):
        nodes = self.nodes
        if not nodes:
            filters = {'instance.group-name': self._security_group}
            terminated_nodes = self.ec2.get_all_instances(filters=filters)
            raise exception.NoClusterNodesFound(terminated_nodes)
        return nodes

    def get_node(self, identifier, nodes=None):
        """
        Returns a node if the identifier specified matches any unique instance
        attribute (e.g. instance id, alias, spot id, dns name, private ip,
        public ip, etc.)
        """
        nodes = nodes or self.nodes
        for node in self.nodes:
            if node.alias == identifier:
                return node
            if node.id == identifier:
                return node
            if node.spot_id == identifier:
                return node
            if node.dns_name == identifier:
                return node
            if node.ip_address == identifier:
                return node
            if node.private_ip_address == identifier:
                return node
            if node.public_dns_name == identifier:
                return node
            if node.private_dns_name == identifier:
                return node
        raise exception.InstanceDoesNotExist(identifier, label='node')

    def get_nodes(self, identifiers, nodes=None):
        """
        Same as get_node but takes a list of identifiers and returns a list of
        nodes.
        """
        nodes = nodes or self.nodes
        node_list = []
        for i in identifiers:
            n = self.get_node(i, nodes=nodes)
            if n in node_list:
                continue
            else:
                node_list.append(n)
        return node_list

    def get_node_by_dns_name(self, dns_name, nodes=None):
        warnings.warn("Please update your code to use Cluster.get_node()",
                      DeprecationWarning)
        return self.get_node(dns_name, nodes=nodes)

    def get_node_by_id(self, instance_id, nodes=None):
        warnings.warn("Please update your code to use Cluster.get_node()",
                      DeprecationWarning)
        return self.get_node(instance_id, nodes=nodes)

    def get_node_by_alias(self, alias, nodes=None):
        warnings.warn("Please update your code to use Cluster.get_node()",
                      DeprecationWarning)
        return self.get_node(alias, nodes=nodes)

    def _nodes_in_states(self, states):
        return filter(lambda x: x.state in states, self.nodes)

    def _make_alias(self, id=None, master=False):
        if master:
            if self.dns_prefix:
                return "%s-master" % self.dns_prefix
            else:
                return "master"
        elif id is not None:
            if self.dns_prefix:
                alias = '%s-node%.3d' % (self.dns_prefix, id)
            else:
                alias = 'node%.3d' % id
        else:
            raise AttributeError("_make_alias(...) must receive either"
                                 " master=True or a node id number")
        return alias

    @property
    def running_nodes(self):
        return self._nodes_in_states(['running'])

    @property
    def stopped_nodes(self):
        return self._nodes_in_states(['stopping', 'stopped'])

    @property
    def spot_requests(self):
        group_id = self.cluster_group.id
        states = ['active', 'open']
        filters = {'state': states}
        vpc_id = self.cluster_group.vpc_id
        if vpc_id and self.subnet_id:
            # According to the EC2 API docs this *should* be
            # launch.network-interface.group-id but it doesn't work
            filters['network-interface.group-id'] = group_id
        else:
            filters['launch.group-id'] = group_id
        return self.ec2.get_all_spot_requests(filters=filters)

    def get_spot_requests_or_raise(self):
        spots = self.spot_requests
        if not spots:
            raise exception.NoClusterSpotRequests
        return spots

    def create_node(self, alias, image_id=None, instance_type=None, zone=None,
                    placement_group=None, spot_bid=None, force_flat=False):
        return self.create_nodes([alias], image_id=image_id,
                                 instance_type=instance_type, zone=zone,
                                 placement_group=placement_group,
                                 spot_bid=spot_bid, force_flat=force_flat)[0]

    def _get_cluster_userdata(self, aliases):
        alias_file = utils.string_to_file('\n'.join(['#ignored'] + aliases),
                                          static.UD_ALIASES_FNAME)
        plugins = utils.dump_compress_encode(self._plugins)
        plugins_file = utils.string_to_file('\n'.join(['#ignored', plugins]),
                                            static.UD_PLUGINS_FNAME)
        volumes = utils.dump_compress_encode(self.volumes)
        volumes_file = utils.string_to_file('\n'.join(['#ignored', volumes]),
                                            static.UD_VOLUMES_FNAME)
        udfiles = [alias_file, plugins_file, volumes_file]
        user_scripts = self.userdata_scripts or []
        udfiles += [open(f) for f in user_scripts]
        use_cloudinit = not self.disable_cloudinit
        udata = userdata.bundle_userdata_files(udfiles,
                                               use_cloudinit=use_cloudinit)
        log.debug('Userdata size in KB: %.2f' % utils.size_in_kb(udata))
        return udata

    def create_nodes(self, aliases, image_id=None, instance_type=None,
                     zone=None, placement_group=None, spot_bid=None,
                     force_flat=False):
        """
        Convenience method for requesting instances with this cluster's
        settings. All settings (kwargs) except force_flat default to cluster
        settings if not provided. Passing force_flat=True ignores spot_bid
        completely forcing a flat-rate instance to be requested.
        """
        spot_bid = spot_bid or self.spot_bid
        if force_flat:
            spot_bid = None
        cluster_sg = self.cluster_group.name
        instance_type = instance_type or self.node_instance_type
        if placement_group or instance_type in static.PLACEMENT_GROUP_TYPES:
            region = self.ec2.region.name
            if region not in static.PLACEMENT_GROUP_REGIONS:
                cluster_regions = ', '.join(static.PLACEMENT_GROUP_REGIONS)
                log.warn("Placement groups are only supported in the "
                         "following regions:\n%s" % cluster_regions)
                log.warn("Instances will not be launched in a placement group")
                placement_group = None
            elif not placement_group:
                placement_group = self.placement_group.name
        image_id = image_id or self.node_image_id
        count = len(aliases) if not spot_bid else 1
        user_data = self._get_cluster_userdata(aliases)
        kwargs = dict(price=spot_bid, instance_type=instance_type,
                      min_count=count, max_count=count, count=count,
                      key_name=self.keyname,
                      availability_zone_group=cluster_sg,
                      launch_group=cluster_sg,
                      placement=zone or getattr(self.zone, 'name', None),
                      user_data=user_data,
                      placement_group=placement_group)
        if self.subnet_id:
            netif = self.ec2.get_network_spec(
                device_index=0, associate_public_ip_address=self.public_ips,
                subnet_id=self.subnet_id, groups=[self.cluster_group.id])
            kwargs.update(
                network_interfaces=self.ec2.get_network_collection(netif))
        else:
            kwargs.update(security_groups=[cluster_sg])
        resvs = []
        if spot_bid:
            security_group_id = self.cluster_group.id
            for alias in aliases:
                if not self.subnet_id:
                    kwargs['security_group_ids'] = [security_group_id]
                kwargs['user_data'] = self._get_cluster_userdata([alias])
                resvs.extend(self.ec2.request_instances(image_id, **kwargs))
        else:
            resvs.append(self.ec2.request_instances(image_id, **kwargs))
        for resv in resvs:
            log.info(str(resv), extra=dict(__raw__=True))
        return resvs

    def _get_next_node_num(self):
        nodes = self._nodes_in_states(['pending', 'running'])
        nodes = filter(lambda x: not x.is_master(), nodes)
        highest = 0
        for n in nodes:
            match = re.search('node(\d{3})', n.alias)
            try:
                _possible_highest = match.group(1)
            except AttributeError:
                continue
            highest = max(int(_possible_highest), highest)
        next = int(highest) + 1
        log.debug("Highest node number is %d. choosing %d." % (highest, next))
        return next

    def add_node(self, alias=None, no_create=False, image_id=None,
                 instance_type=None, zone=None, placement_group=None,
                 spot_bid=None):
        """
        Add a single node to this cluster
        """
        aliases = [alias] if alias else None
        return self.add_nodes(1, aliases=aliases, image_id=image_id,
                              instance_type=instance_type, zone=zone,
                              placement_group=placement_group,
                              spot_bid=spot_bid, no_create=no_create)

    def add_nodes(self, num_nodes, aliases=None, image_id=None,
                  instance_type=None, zone=None, placement_group=None,
                  spot_bid=None, no_create=False):
        """
        Add new nodes to this cluster

        aliases - list of aliases to assign to new nodes (len must equal
        num_nodes)
        """
        running_pending = self._nodes_in_states(['pending', 'running'])
        aliases = aliases or []
        if not aliases:
            next_node_id = self._get_next_node_num()
            for i in range(next_node_id, next_node_id + num_nodes):
                alias = self._make_alias(i)
                aliases.append(alias)
        assert len(aliases) == num_nodes
        if self._make_alias(master=True) in aliases:
            raise exception.ClusterValidationError(
                "worker nodes cannot have master as an alias")
        if not no_create:
            if self.subnet:
                ip_count = self.subnet.available_ip_address_count
                if ip_count < len(aliases):
                    raise exception.ClusterValidationError(
                        "Not enough IP addresses available in %s (%d)" %
                        (self.subnet.id, ip_count))
            for node in running_pending:
                if node.alias in aliases:
                    raise exception.ClusterValidationError(
                        "node with alias %s already exists" % node.alias)
            log.info("Launching node(s): %s" % ', '.join(aliases))
            resp = self.create_nodes(aliases, image_id=image_id,
                                     instance_type=instance_type, zone=zone,
                                     placement_group=placement_group,
                                     spot_bid=spot_bid)
            if spot_bid or self.spot_bid:
                self.ec2.wait_for_propagation(spot_requests=resp)
            else:
                self.ec2.wait_for_propagation(instances=resp[0].instances)
        self.wait_for_cluster(msg="Waiting for node(s) to come up...")
        log.debug("Adding node(s): %s" % aliases)
        for alias in aliases:
            node = self.get_node(alias)
            self.run_plugins(method_name="on_add_node", node=node)

    def remove_node(self, node=None, terminate=True, force=False):
        """
        Remove a single node from this cluster
        """
        nodes = [node] if node else None
        return self.remove_nodes(nodes=nodes, num_nodes=1, terminate=terminate,
                                 force=force)

    def remove_nodes(self, nodes=None, num_nodes=None, terminate=True,
                     force=False):
        """
        Remove a list of nodes from this cluster
        """
        if nodes is None and num_nodes is None:
            raise exception.BaseException(
                "please specify either nodes or num_nodes kwargs")
        if not nodes:
            worker_nodes = self.nodes[1:]
            nodes = worker_nodes[-num_nodes:]
            nodes.reverse()
            if len(nodes) != num_nodes:
                raise exception.BaseException(
                    "cant remove %d nodes - only %d nodes exist" %
                    (num_nodes, len(worker_nodes)))
        else:
            for node in nodes:
                if node.is_master():
                    raise exception.InvalidOperation(
                        "cannot remove master node")
        for node in nodes:
            try:
                self.run_plugins(method_name="on_remove_node", node=node,
                                 reverse=True)
            except:
                if not force:
                    raise
            if not terminate:
                continue
            node.terminate()

    def _get_launch_map(self, reverse=False):
        """
        Groups all node-aliases that have similar instance types/image ids
        Returns a dictionary that's used to launch all similar instance types
        and image ids in the same request. Example return value:

        {('c1.xlarge', 'ami-a5c02dcc'): ['node001', 'node002'],
         ('m1.large', 'ami-a5c02dcc'): ['node003'],
         ('m1.small', 'ami-17b15e7e'): ['master', 'node005', 'node006'],
         ('m1.small', 'ami-19e17a2b'): ['node004']}

        Passing reverse=True will return the same information only keyed by
        node aliases:

        {'master': ('m1.small', 'ami-17b15e7e'),
         'node001': ('c1.xlarge', 'ami-a5c02dcc'),
         'node002': ('c1.xlarge', 'ami-a5c02dcc'),
         'node003': ('m1.large', 'ami-a5c02dcc'),
         'node004': ('m1.small', 'ami-19e17a2b'),
         'node005': ('m1.small', 'ami-17b15e7e'),
         'node006': ('m1.small', 'ami-17b15e7e')}
        """
        lmap = {}
        mtype = self.master_instance_type or self.node_instance_type
        mimage = self.master_image_id or self.node_image_id
        lmap[(mtype, mimage)] = [self._make_alias(master=True)]
        id_start = 1
        for itype in self.node_instance_types:
            count = itype['size']
            image_id = itype['image'] or self.node_image_id
            type = itype['type'] or self.node_instance_type
            if not (type, image_id) in lmap:
                lmap[(type, image_id)] = []
            for id in range(id_start, id_start + count):
                alias = self._make_alias(id)
                log.debug("Launch map: %s (ami: %s, type: %s)..." %
                          (alias, image_id, type))
                lmap[(type, image_id)].append(alias)
                id_start += 1
        ntype = self.node_instance_type
        nimage = self.node_image_id
        if not (ntype, nimage) in lmap:
            lmap[(ntype, nimage)] = []
        for id in range(id_start, self.cluster_size):
            alias = self._make_alias(id)
            log.debug("Launch map: %s (ami: %s, type: %s)..." %
                      (alias, nimage, ntype))
            lmap[(ntype, nimage)].append(alias)
        if reverse:
            rlmap = {}
            for (itype, image_id) in lmap:
                aliases = lmap.get((itype, image_id))
                for alias in aliases:
                    rlmap[alias] = (itype, image_id)
            return rlmap
        return lmap

    def _get_type_and_image_id(self, alias):
        """
        Returns (instance_type,image_id) for a given alias based
        on the map returned from self._get_launch_map
        """
        lmap = self._get_launch_map()
        for (type, image) in lmap:
            key = (type, image)
            if alias in lmap.get(key):
                return key

    def create_cluster(self):
        """
        Launches all EC2 instances based on this cluster's settings.
        """
        log.info("Launching a %d-node %s" % (self.cluster_size, ' '.join(
            ['VPC' if self.subnet_id else '', 'cluster...']).strip()))
        mtype = self.master_instance_type or self.node_instance_type
        self.master_instance_type = mtype
        if self.spot_bid:
            self._create_spot_cluster()
        else:
            self._create_flat_rate_cluster()

    def _create_flat_rate_cluster(self):
        """
        Launches cluster using flat-rate instances. This method attempts to
        minimize the number of launch requests by grouping nodes of the same
        type/ami and launching each group simultaneously within a single launch
        request. This is especially important for Cluster Compute instances
        given that Amazon *highly* recommends requesting all CCI in a single
        launch request.
        """
        lmap = self._get_launch_map()
        zone = None
        insts = []
        master_alias = self._make_alias(master=True)
        itype, image = [i for i in lmap if master_alias in lmap[i]][0]
        aliases = lmap.get((itype, image))
        for alias in aliases:
            log.debug("Launching %s (ami: %s, type: %s)" %
                      (alias, image, itype))
        master_response = self.create_nodes(aliases, image_id=image,
                                            instance_type=itype,
                                            force_flat=True)[0]
        zone = master_response.instances[0].placement
        insts.extend(master_response.instances)
        lmap.pop((itype, image))
        for (itype, image) in lmap:
            aliases = lmap.get((itype, image))
            if not aliases:
                continue
            for alias in aliases:
                log.debug("Launching %s (ami: %s, type: %s)" %
                          (alias, image, itype))
            resv = self.create_nodes(aliases, image_id=image,
                                     instance_type=itype, zone=zone,
                                     force_flat=True)
            insts.extend(resv[0].instances)
        self.ec2.wait_for_propagation(instances=insts)

    def _create_spot_cluster(self):
        """
        Launches cluster using spot instances for all worker nodes. This method
        makes a single spot request for each node in the cluster since spot
        instances *always* have an ami_launch_index of 0. This is needed in
        order to correctly assign aliases to nodes.
        """
        master_alias = self._make_alias(master=True)
        (mtype, mimage) = self._get_type_and_image_id(master_alias)
        log.info("Launching master node (ami: %s, type: %s)..." %
                 (mimage, mtype))
        force_flat = not self.force_spot_master
        master_response = self.create_node(master_alias,
                                           image_id=mimage,
                                           instance_type=mtype,
                                           force_flat=force_flat)
        insts, spot_reqs = [], []
        zone = None
        if not force_flat and self.spot_bid:
            # Make sure nodes are in same zone as master
            launch_spec = master_response.launch_specification
            zone = launch_spec.placement
            spot_reqs.append(master_response)
        else:
            # Make sure nodes are in same zone as master
            zone = master_response.instances[0].placement
            insts.extend(master_response.instances)
        for id in range(1, self.cluster_size):
            alias = self._make_alias(id)
            (ntype, nimage) = self._get_type_and_image_id(alias)
            log.info("Launching %s (ami: %s, type: %s)" %
                     (alias, nimage, ntype))
            spot_req = self.create_node(alias, image_id=nimage,
                                        instance_type=ntype, zone=zone)
            spot_reqs.append(spot_req)
        self.ec2.wait_for_propagation(instances=insts, spot_requests=spot_reqs)

    def is_spot_cluster(self):
        """
        Returns True if all nodes are spot instances
        """
        nodes = self.nodes
        if not nodes:
            return False
        for node in nodes:
            if not node.is_spot():
                return False
        return True

    def has_spot_nodes(self):
        """
        Returns True if any nodes are spot instances
        """
        for node in self.nodes:
            if node.is_spot():
                return True
        return False

    def is_ebs_cluster(self):
        """
        Returns True if all nodes are EBS-backed
        """
        nodes = self.nodes
        if not nodes:
            return False
        for node in nodes:
            if not node.is_ebs_backed():
                return False
        return True

    def has_ebs_nodes(self):
        """
        Returns True if any nodes are EBS-backed
        """
        for node in self.nodes:
            if node.is_ebs_backed():
                return True
        return False

    def is_stoppable(self):
        """
        Returns True if all nodes are stoppable (i.e. non-spot and EBS-backed)
        """
        nodes = self.nodes
        if not nodes:
            return False
        for node in self.nodes:
            if not node.is_stoppable():
                return False
        return True

    def has_stoppable_nodes(self):
        """
        Returns True if any nodes are stoppable (i.e. non-spot and EBS-backed)
        """
        nodes = self.nodes
        if not nodes:
            return False
        for node in nodes:
            if node.is_stoppable():
                return True
        return False

    def is_cluster_compute(self):
        """
        Returns true if all instances are Cluster/GPU Compute type
        """
        nodes = self.nodes
        if not nodes:
            return False
        for node in nodes:
            if not node.is_cluster_compute():
                return False
        return True

    def has_cluster_compute_nodes(self):
        for node in self.nodes:
            if node.is_cluster_compute():
                return True
        return False

    def is_cluster_up(self):
        """
        Check that all nodes are 'running' and that ssh is up on all nodes
        This method will return False if any spot requests are in an 'open'
        state.
        """
        spots = self.spot_requests
        active_spots = filter(lambda x: x.state == 'active', spots)
        if len(spots) != len(active_spots):
            return False
        nodes = self.nodes
        if not nodes:
            return False
        for node in nodes:
            if not node.is_up():
                return False
        return True

    @property
    def progress_bar(self):
        if not self._progress_bar:
            widgets = ['', progressbar.Fraction(), ' ',
                       progressbar.Bar(marker=progressbar.RotatingMarker()),
                       ' ', progressbar.Percentage(), ' ', ' ']
            pbar = progressbar.ProgressBar(widgets=widgets,
                                           maxval=self.cluster_size,
                                           force_update=True)
            self._progress_bar = pbar
        return self._progress_bar

    @property
    def pool(self):
        if not self._pool:
            self._pool = threadpool.get_thread_pool(
                size=self.num_threads, disable_threads=self.disable_threads)
        return self._pool

    @property
    def validator(self):
        return ClusterValidator(self)

    def is_valid(self):
        return self.validator.is_valid()

    def validate(self):
        return self.validator.validate()

    def wait_for_active_spots(self, spots=None):
        """
        Wait for all open spot requests for this cluster to transition to
        'active'.
        """
        spots = spots or self.spot_requests
        open_spots = [spot for spot in spots if spot.state == "open"]
        if open_spots:
            pbar = self.progress_bar.reset()
            log.info('Waiting for open spot requests to become active...')
            pbar.maxval = len(spots)
            pbar.update(0)
            while not pbar.finished:
                active_spots = [s for s in spots if s.state == "active" and
                                s.instance_id]
                pbar.maxval = len(spots)
                pbar.update(len(active_spots))
                if not pbar.finished:
                    time.sleep(self.refresh_interval)
                    spots = self.get_spot_requests_or_raise()
            pbar.reset()
        self.ec2.wait_for_propagation(
            instances=[s.instance_id for s in spots])

    def wait_for_running_instances(self, nodes=None,
                                   kill_pending_after_mins=15):
        """
        Wait until all cluster nodes are in a 'running' state
        """
        log.info("Waiting for all nodes to be in a 'running' state...")
        nodes = nodes or self.get_nodes_or_raise()
        pbar = self.progress_bar.reset()
        pbar.maxval = len(nodes)
        pbar.update(0)
        now = datetime.datetime.utcnow()
        timeout = now + datetime.timedelta(minutes=kill_pending_after_mins)
        while not pbar.finished:
            running_nodes = [n for n in nodes if n.state == "running"]
            pbar.maxval = len(nodes)
            pbar.update(len(running_nodes))
            if not pbar.finished:
                if datetime.datetime.utcnow() > timeout:
                    pending = [n for n in nodes if n not in running_nodes]
                    log.warn("%d nodes have been pending for >= %d mins "
                             "- terminating" % (len(pending),
                                                kill_pending_after_mins))
                    for node in pending:
                        node.terminate()
                else:
                    time.sleep(self.refresh_interval)
                nodes = self.get_nodes_or_raise()
        pbar.reset()

    def wait_for_ssh(self, nodes=None):
        """
        Wait until all cluster nodes are in a 'running' state
        """
        log.info("Waiting for SSH to come up on all nodes...")
        nodes = nodes or self.get_nodes_or_raise()
        self.pool.map(lambda n: n.wait(interval=self.refresh_interval), nodes,
                      jobid_fn=lambda n: n.alias)

    @print_timing("Waiting for cluster to come up")
    def wait_for_cluster(self, msg="Waiting for cluster to come up..."):
        """
        Wait for cluster to come up and display progress bar. Waits for all
        spot requests to become 'active', all instances to be in a 'running'
        state, and for all SSH daemons to come up.

        msg - custom message to print out before waiting on the cluster
        """
        interval = self.refresh_interval
        log.info("%s %s" % (msg, "(updating every %ds)" % interval))
        try:
            self.wait_for_active_spots()
            self.wait_for_running_instances()
            self.wait_for_ssh()
        except Exception:
            self.progress_bar.finish()
            raise

    def is_cluster_stopped(self):
        """
        Check whether all nodes are in the 'stopped' state
        """
        nodes = self.nodes
        if not nodes:
            return False
        for node in nodes:
            if node.state != 'stopped':
                return False
        return True

    def is_cluster_terminated(self):
        """
        Check whether all nodes are in a 'terminated' state
        """
        states = filter(lambda x: x != 'terminated', static.INSTANCE_STATES)
        filters = {'instance.group-name': self._security_group,
                   'instance-state-name': states}
        insts = self.ec2.get_all_instances(filters=filters)
        return len(insts) == 0

    def attach_volumes_to_master(self):
        """
        Attach each volume to the master node
        """
        wait_for_volumes = []
        for vol in self.volumes:
            volume = self.volumes.get(vol)
            device = volume.get('device')
            vol_id = volume.get('volume_id')
            vol = self.ec2.get_volume(vol_id)
            if vol.attach_data.instance_id == self.master_node.id:
                log.info("Volume %s already attached to master...skipping" %
                         vol.id)
                continue
            if vol.status != "available":
                log.error('Volume %s not available...'
                          'please check and try again' % vol.id)
                continue
            log.info("Attaching volume %s to master node on %s ..." %
                     (vol.id, device))
            resp = vol.attach(self.master_node.id, device)
            log.debug("resp = %s" % resp)
            wait_for_volumes.append(vol)
        for vol in wait_for_volumes:
            self.ec2.wait_for_volume(vol, state='attached')

    def detach_volumes(self):
        """
        Detach all volumes from all nodes
        """
        for node in self.nodes:
            node.detach_external_volumes()

    @print_timing('Restarting cluster')
    def restart_cluster(self, reboot_only=False):
        """
        Reboot all instances and reconfigure the cluster
        """
        nodes = self.nodes
        if not nodes:
            raise exception.ClusterValidationError("No running nodes found")
        self.run_plugins(method_name="on_restart", reverse=True)
        log.info("Rebooting cluster...")
        for node in nodes:
            node.reboot()
        if reboot_only:
            return
        sleep = 20
        log.info("Sleeping for %d seconds..." % sleep)
        time.sleep(sleep)
        self.setup_cluster()

    def stop_cluster(self, terminate_unstoppable=False, force=False):
        """
        Shutdown this cluster by detaching all volumes and 'stopping' all nodes

        In general, all nodes in the cluster must be 'stoppable' meaning all
        nodes are backed by flat-rate EBS-backed instances. If any
        'unstoppable' nodes are found an exception is raised. A node is
        'unstoppable' if it is backed by either a spot or S3-backed instance.

        If the cluster contains a mix of 'stoppable' and 'unstoppable' nodes
        you can stop all stoppable nodes and terminate any unstoppable nodes by
        setting terminate_unstoppable=True.
        """
        nodes = self.nodes
        if not nodes:
            raise exception.ClusterValidationError("No running nodes found")
        if not self.is_stoppable():
            has_stoppable_nodes = self.has_stoppable_nodes()
            if not terminate_unstoppable and has_stoppable_nodes:
                raise exception.InvalidOperation(
                    "Cluster contains nodes that are not stoppable")
            if not has_stoppable_nodes:
                raise exception.InvalidOperation(
                    "Cluster does not contain any stoppable nodes")
        try:
            self.run_plugins(method_name="on_shutdown", reverse=True)
        except exception.MasterDoesNotExist as e:
            if force:
                log.warn("Cannot run plugins: %s" % e)
            else:
                raise
        self.detach_volumes()
        for node in nodes:
            node.shutdown()

    def terminate_cluster(self, force=False):
        """
        Destroy this cluster by first detaching all volumes, shutting down all
        instances, canceling all spot requests (if any), removing its placement
        group (if any), and removing its security group.
        """
        try:
            self.run_plugins(method_name="on_shutdown", reverse=True)
        except exception.MasterDoesNotExist as e:
            if force:
                log.warn("Cannot run plugins: %s" % e)
            else:
                raise
        self.detach_volumes()
        nodes = self.nodes
        for node in nodes:
            node.terminate()
        for spot in self.spot_requests:
            if spot.state not in ['cancelled', 'closed']:
                log.info("Canceling spot instance request: %s" % spot.id)
                spot.cancel()
        s = utils.get_spinner("Waiting for cluster to terminate...")
        try:
            while not self.is_cluster_terminated():
                time.sleep(5)
        finally:
            s.stop()
        region = self.ec2.region.name
        if region in static.PLACEMENT_GROUP_REGIONS:
            pg = self.ec2.get_placement_group_or_none(self._security_group)
            if pg:
                self.ec2.delete_group(pg)
        sg = self.ec2.get_group_or_none(self._security_group)
        if sg:
            self.ec2.delete_group(sg)

    def start(self, create=True, create_only=False, validate=True,
              validate_only=False, validate_running=False):
        """
        Creates and configures a cluster from this cluster template's settings.

        create - create new nodes when starting the cluster. set to False to
                 use existing nodes
        create_only - only create the cluster node instances, don't configure
                      the cluster
        validate - whether or not to validate the cluster settings used.
                   False will ignore validate_only and validate_running
                   keywords and is effectively the same as running _start
        validate_only - only validate cluster settings, do not create or
                        configure cluster
        validate_running - whether or not to validate the existing instances
                           being used against this cluster's settings
        """
        if validate:
            validator = self.validator
            if not create and validate_running:
                try:
                    validator.validate_running_instances()
                except exception.ClusterValidationError as e:
                    msg = "Existing nodes are not compatible with cluster "
                    msg += "settings:\n"
                    e.msg = msg + e.msg
                    raise
            validator.validate()
            if validate_only:
                return
        else:
            log.warn("SKIPPING VALIDATION - USE AT YOUR OWN RISK")
        return self._start(create=create, create_only=create_only)

    @print_timing("Starting cluster")
    def _start(self, create=True, create_only=False):
        """
        Create and configure a cluster from this cluster template's settings
        (Does not attempt to validate before running)

        create - create new nodes when starting the cluster. set to False to
                 use existing nodes
        create_only - only create the cluster node instances, don't configure
                      the cluster
        """
        log.info("Starting cluster...")
        if create:
            self.create_cluster()
        else:
            assert self.master_node is not None
            for node in self.stopped_nodes:
                log.info("Starting stopped node: %s" % node.alias)
                node.start()
        if create_only:
            return
        self.setup_cluster()

    def setup_cluster(self):
        """
        Waits for all nodes to come up and then runs the default
        StarCluster setup routines followed by any additional plugin setup
        routines
        """
        self.wait_for_cluster()
        self._setup_cluster()

    @print_timing("Configuring cluster")
    def _setup_cluster(self):
        """
        Runs the default StarCluster setup routines followed by any additional
        plugin setup routines. Does not wait for nodes to come up.
        """
        log.info("The master node is %s" % self.master_node.dns_name)
        log.info("Configuring cluster...")
        if self.volumes:
            self.attach_volumes_to_master()
        self.run_plugins()

    def run_plugins(self, plugins=None, method_name="run", node=None,
                    reverse=False):
        """
        Run all plugins specified in this Cluster object's self.plugins list
        Uses plugins list instead of self.plugins if specified.

        plugins must be a tuple: the first element is the plugin's name, the
        second element is the plugin object (a subclass of ClusterSetup)
        """
        plugs = [self._default_plugin]
        if not self.disable_queue:
            plugs.append(self._sge_plugin)
        plugs += (plugins or self.plugins)[:]
        if reverse:
            plugs.reverse()
        for plug in plugs:
            self.run_plugin(plug, method_name=method_name, node=node)

    def run_plugin(self, plugin, name='', method_name='run', node=None):
        """
        Run a StarCluster plugin.

        plugin - an instance of the plugin's class
        name - a user-friendly label for the plugin
        method_name - the method to run within the plugin (default: "run")
        node - optional node to pass as first argument to plugin method (used
        for on_add_node/on_remove_node)
        """
        plugin_name = name or getattr(plugin, '__name__',
                                      utils.get_fq_class_name(plugin))
        try:
            func = getattr(plugin, method_name, None)
            if not func:
                log.warn("Plugin %s has no %s method...skipping" %
                         (plugin_name, method_name))
                return
            args = [self.nodes, self.master_node, self.cluster_user,
                    self.cluster_shell, self.volumes]
            if node:
                args.insert(0, node)
            log.info("Running plugin %s" % plugin_name)
            func(*args)
        except NotImplementedError:
            log.debug("method %s not implemented by plugin %s" % (method_name,
                                                                  plugin_name))
        except exception.MasterDoesNotExist:
            raise
        except KeyboardInterrupt:
            raise
        except Exception:
            log.error("Error occured while running plugin '%s':" % plugin_name)
            raise

    def ssh_to_master(self, user='root', command=None, forward_x11=False,
                      forward_agent=False, pseudo_tty=False):
        return self.master_node.shell(user=user, command=command,
                                      forward_x11=forward_x11,
                                      forward_agent=forward_agent,
                                      pseudo_tty=pseudo_tty)

    def ssh_to_node(self, alias, user='root', command=None, forward_x11=False,
                    forward_agent=False, pseudo_tty=False):
        node = self.get_node(alias)
        return node.shell(user=user, forward_x11=forward_x11,
                          forward_agent=forward_agent,
                          pseudo_tty=pseudo_tty,
                          command=command)


class ClusterValidator(validators.Validator):

    """
    Validates that cluster settings define a sane launch configuration.
    Throws exception.ClusterValidationError for all validation failures
    """
    def __init__(self, cluster):
        self.cluster = cluster

    def is_running_valid(self):
        """
        Checks whether the current running instances are compatible
        with this cluster template's settings
        """
        try:
            self.validate_running_instances()
            return True
        except exception.ClusterValidationError as e:
            log.error(e.msg)
            return False

    def validate_required_settings(self):
        has_all_required = True
        for opt in static.CLUSTER_SETTINGS:
            requirements = static.CLUSTER_SETTINGS[opt]
            name = opt
            required = requirements[1]
            if required and self.cluster.get(name.lower()) is None:
                log.warn('Missing required setting %s' % name)
                has_all_required = False
        return has_all_required

    def validate_running_instances(self):
        """
        Validate existing instances against this cluster's settings
        """
        cluster = self.cluster
        cluster.wait_for_active_spots()
        nodes = cluster.nodes
        if not nodes:
            raise exception.ClusterValidationError("No existing nodes found!")
        log.info("Validating existing instances...")
        mazone = cluster.master_node.placement
        # reset zone cache
        cluster._zone = None
        if cluster.zone and cluster.zone.name != mazone:
            raise exception.ClusterValidationError(
                "Running cluster's availability_zone (%s) != %s" %
                (mazone, cluster.zone.name))
        for node in nodes:
            if node.key_name != cluster.keyname:
                raise exception.ClusterValidationError(
                    "%s's key_name (%s) != %s" % (node.alias, node.key_name,
                                                  cluster.keyname))

    def validate(self):
        """
        Checks that all cluster template settings are valid and raises an
        exception.ClusterValidationError exception if not.
        """
        log.info("Validating cluster template settings...")
        try:
            self.validate_required_settings()
            self.validate_vpc()
            self.validate_dns_prefix()
            self.validate_spot_bid()
            self.validate_cluster_size()
            self.validate_cluster_user()
            self.validate_shell_setting()
            self.validate_permission_settings()
            self.validate_credentials()
            self.validate_keypair()
            self.validate_zone()
            self.validate_ebs_settings()
            self.validate_ebs_aws_settings()
            self.validate_image_settings()
            self.validate_instance_types()
            self.validate_userdata()
            log.info('Cluster template settings are valid')
            return True
        except exception.ClusterValidationError as e:
            e.msg = 'Cluster settings are not valid:\n%s' % e.msg
            raise

    def is_valid(self):
        """
        Returns True if all cluster template settings are valid
        """
        try:
            self.validate()
            return True
        except exception.ClusterValidationError as e:
            log.error(e.msg)
            return False

    def validate_dns_prefix(self):
        if not self.cluster.dns_prefix:
            return True

        # check that the dns prefix is a valid hostname
        is_valid = utils.is_valid_hostname(self.cluster.dns_prefix)
        if not is_valid:
            raise exception.ClusterValidationError(
                "The cluster name you chose, {dns_prefix}, is"
                " not a valid dns name. "
                " Since you have chosen to prepend the hostnames"
                " via the dns_prefix option, {dns_prefix} should only have"
                " alphanumeric characters and a '-' or '.'".format(
                    dns_prefix=self.cluster.dns_prefix))
        return True

    def validate_spot_bid(self):
        cluster = self.cluster
        if cluster.spot_bid is not None:
            if type(cluster.spot_bid) not in [int, float]:
                raise exception.ClusterValidationError(
                    'spot_bid must be integer or float')
            if cluster.spot_bid <= 0:
                raise exception.ClusterValidationError(
                    'spot_bid must be an integer or float > 0')
        return True

    def validate_cluster_size(self):
        cluster = self.cluster
        try:
            int(cluster.cluster_size)
            if cluster.cluster_size < 1:
                raise ValueError
        except (ValueError, TypeError):
            raise exception.ClusterValidationError(
                'cluster_size must be an integer >= 1')
        num_itypes = sum([i.get('size') for i in
                          cluster.node_instance_types])
        num_nodes = cluster.cluster_size - 1
        if num_itypes > num_nodes:
            raise exception.ClusterValidationError(
                "total number of nodes specified in node_instance_type (%s) "
                "must be <= cluster_size-1 (%s)" % (num_itypes, num_nodes))
        return True

    def validate_cluster_user(self):
        if self.cluster.cluster_user == "root":
            raise exception.ClusterValidationError(
                'cluster_user cannot be "root"')
        return True

    def validate_shell_setting(self):
        cluster_shell = self.cluster.cluster_shell
        if not static.AVAILABLE_SHELLS.get(cluster_shell):
            raise exception.ClusterValidationError(
                'Invalid user shell specified. Options are %s' %
                ' '.join(static.AVAILABLE_SHELLS.keys()))
        return True

    def validate_image_settings(self):
        cluster = self.cluster
        master_image_id = cluster.master_image_id
        node_image_id = cluster.node_image_id
        conn = cluster.ec2
        image = conn.get_image_or_none(node_image_id)
        if not image or image.id != node_image_id:
            raise exception.ClusterValidationError(
                'node_image_id %s does not exist' % node_image_id)
        if image.state != 'available':
            raise exception.ClusterValidationError(
                'node_image_id %s is not available' % node_image_id)
        if master_image_id:
            master_image = conn.get_image_or_none(master_image_id)
            if not master_image or master_image.id != master_image_id:
                raise exception.ClusterValidationError(
                    'master_image_id %s does not exist' % master_image_id)
            if master_image.state != 'available':
                raise exception.ClusterValidationError(
                    'master_image_id %s is not available' % master_image_id)
        return True

    def validate_zone(self):
        """
        Validates that the cluster's availability zone exists and is available.
        The 'zone' property additionally checks that all EBS volumes are in the
        same zone and that the cluster's availability zone setting, if
        specified, matches the EBS volume(s) zone.
        """
        zone = self.cluster.zone
        if zone and zone.state != 'available':
            raise exception.ClusterValidationError(
                "The '%s' availability zone is not available at this time" %
                zone.name)
        return True

    def __check_platform(self, image_id, instance_type):
        """
        Validates whether an image_id (AMI) is compatible with a given
        instance_type. image_id_setting and instance_type_setting are the
        setting labels in the config file.
        """
        image = self.cluster.ec2.get_image_or_none(image_id)
        if not image:
            raise exception.ClusterValidationError('Image %s does not exist' %
                                                   image_id)
        image_platform = image.architecture
        image_is_hvm = (image.virtualization_type == "hvm")
        if image_is_hvm and instance_type not in static.HVM_TYPES:
            cctypes_list = ', '.join(static.HVM_TYPES)
            raise exception.ClusterValidationError(
                "Image '%s' is a hardware virtual machine (HVM) image and "
                "cannot be used with instance type '%s'.\n\nHVM images "
                "require one of the following HVM instance types:\n%s" %
                (image_id, instance_type, cctypes_list))
        if instance_type in static.HVM_ONLY_TYPES and not image_is_hvm:
            raise exception.ClusterValidationError(
                "The '%s' instance type can only be used with hardware "
                "virtual machine (HVM) images. Image '%s' is not an HVM "
                "image." % (instance_type, image_id))
        instance_platforms = static.INSTANCE_TYPES[instance_type]
        if image_platform not in instance_platforms:
            error_msg = "Instance type %(instance_type)s is for an " \
                        "%(instance_platform)s platform while " \
                        "%(image_id)s is an %(image_platform)s platform"
            error_dict = {'instance_type': instance_type,
                          'instance_platform': ', '.join(instance_platforms),
                          'image_id': image_id,
                          'image_platform': image_platform}
            raise exception.ClusterValidationError(error_msg % error_dict)
        image_is_ebs = (image.root_device_type == 'ebs')
        if instance_type in static.EBS_ONLY_TYPES and not image_is_ebs:
            error_msg = ("Instance type %s can only be used with an "
                         "EBS-backed AMI and '%s' is not EBS-backed " %
                         (instance_type, image.id))
            raise exception.ClusterValidationError(error_msg)
        return True

    def validate_instance_types(self):
        cluster = self.cluster
        master_image_id = cluster.master_image_id
        node_image_id = cluster.node_image_id
        master_instance_type = cluster.master_instance_type
        node_instance_type = cluster.node_instance_type
        instance_types = static.INSTANCE_TYPES
        instance_type_list = ', '.join(instance_types.keys())
        if node_instance_type not in instance_types:
            raise exception.ClusterValidationError(
                "You specified an invalid node_instance_type %s\n"
                "Possible options are:\n%s" %
                (node_instance_type, instance_type_list))
        elif master_instance_type:
            if master_instance_type not in instance_types:
                raise exception.ClusterValidationError(
                    "You specified an invalid master_instance_type %s\n"
                    "Possible options are:\n%s" %
                    (master_instance_type, instance_type_list))
        try:
            self.__check_platform(node_image_id, node_instance_type)
        except exception.ClusterValidationError as e:
            raise exception.ClusterValidationError(
                'Incompatible node_image_id and node_instance_type:\n' + e.msg)
        if master_image_id and not master_instance_type:
            try:
                self.__check_platform(master_image_id, node_instance_type)
            except exception.ClusterValidationError as e:
                raise exception.ClusterValidationError(
                    'Incompatible master_image_id and node_instance_type\n' +
                    e.msg)
        elif master_image_id and master_instance_type:
            try:
                self.__check_platform(master_image_id, master_instance_type)
            except exception.ClusterValidationError as e:
                raise exception.ClusterValidationError(
                    'Incompatible master_image_id and master_instance_type\n' +
                    e.msg)
        elif master_instance_type and not master_image_id:
            try:
                self.__check_platform(node_image_id, master_instance_type)
            except exception.ClusterValidationError as e:
                raise exception.ClusterValidationError(
                    'Incompatible node_image_id and master_instance_type\n' +
                    e.msg)
        for itype in cluster.node_instance_types:
            type = itype.get('type')
            img = itype.get('image') or node_image_id
            if type not in instance_types:
                raise exception.ClusterValidationError(
                    "You specified an invalid instance type %s\n"
                    "Possible options are:\n%s" % (type, instance_type_list))
            try:
                self.__check_platform(img, type)
            except exception.ClusterValidationError as e:
                raise exception.ClusterValidationError(
                    "Invalid settings for node_instance_type %s: %s" %
                    (type, e.msg))
        return True

    def validate_permission_settings(self):
        permissions = self.cluster.permissions
        for perm in permissions:
            permission = permissions.get(perm)
            protocol = permission.get('ip_protocol')
            if protocol not in static.PROTOCOLS:
                raise exception.InvalidProtocol(protocol)
            from_port = permission.get('from_port')
            to_port = permission.get('to_port')
            try:
                from_port = int(from_port)
                to_port = int(to_port)
            except ValueError:
                raise exception.InvalidPortRange(
                    from_port, to_port, reason="integer range required")
            if from_port < 0 or to_port < 0:
                raise exception.InvalidPortRange(
                    from_port, to_port,
                    reason="from/to must be positive integers")
            if from_port > to_port:
                raise exception.InvalidPortRange(
                    from_port, to_port,
                    reason="'from_port' must be <= 'to_port'")
            cidr_ip = permission.get('cidr_ip')
            if not iptools.ipv4.validate_cidr(cidr_ip):
                raise exception.InvalidCIDRSpecified(cidr_ip)

    def validate_ebs_settings(self):
        """
        Check EBS vols for missing/duplicate DEVICE/PARTITION/MOUNT_PATHs and
        validate these settings.
        """
        volmap = {}
        devmap = {}
        mount_paths = []
        cluster = self.cluster
        for vol in cluster.volumes:
            vol_name = vol
            vol = cluster.volumes.get(vol)
            vol_id = vol.get('volume_id')
            device = vol.get('device')
            partition = vol.get('partition')
            mount_path = vol.get("mount_path")
            vmap = volmap.get(vol_id, {})
            devices = vmap.get('device', [])
            partitions = vmap.get('partition', [])
            if devices and device not in devices:
                raise exception.ClusterValidationError(
                    "Can't attach volume %s to more than one device" % vol_id)
            elif partitions and partition in partitions:
                raise exception.ClusterValidationError(
                    "Multiple configurations for %s\n"
                    "Either pick one or specify a separate partition for "
                    "each configuration" % vol_id)
            vmap['partition'] = partitions + [partition]
            vmap['device'] = devices + [device]
            volmap[vol_id] = vmap
            dmap = devmap.get(device, {})
            vol_ids = dmap.get('volume_id', [])
            if vol_ids and vol_id not in vol_ids:
                raise exception.ClusterValidationError(
                    "Can't attach more than one volume on device %s" % device)
            dmap['volume_id'] = vol_ids + [vol_id]
            devmap[device] = dmap
            mount_paths.append(mount_path)
            if not device:
                raise exception.ClusterValidationError(
                    'Missing DEVICE setting for volume %s' % vol_name)
            if not utils.is_valid_device(device):
                raise exception.ClusterValidationError(
                    "Invalid DEVICE value for volume %s" % vol_name)
            if partition:
                if not utils.is_valid_partition(partition):
                    raise exception.ClusterValidationError(
                        "Invalid PARTITION value for volume %s" % vol_name)
                if not partition.startswith(device):
                    raise exception.ClusterValidationError(
                        "Volume PARTITION must start with %s" % device)
            if not mount_path:
                raise exception.ClusterValidationError(
                    'Missing MOUNT_PATH setting for volume %s' % vol_name)
            if not mount_path.startswith('/'):
                raise exception.ClusterValidationError(
                    "MOUNT_PATH for volume %s should start with /" % vol_name)
            if mount_path == "/":
                raise exception.ClusterValidationError(
                    "MOUNT_PATH for volume %s cannot be /" % vol_name)
        for path in mount_paths:
            if mount_paths.count(path) > 1:
                raise exception.ClusterValidationError(
                    "Can't mount more than one volume on %s" % path)
        return True

    def validate_ebs_aws_settings(self):
        """
        Verify that all EBS volumes exist and are available.
        """
        cluster = self.cluster
        for vol in cluster.volumes:
            v = cluster.volumes.get(vol)
            vol_id = v.get('volume_id')
            vol = cluster.ec2.get_volume(vol_id)
            if vol.status != 'available':
                try:
                    if vol.attach_data.instance_id == cluster.master_node.id:
                        continue
                except exception.MasterDoesNotExist:
                    pass
                raise exception.ClusterValidationError(
                    "Volume '%s' is not available (status: %s)" %
                    (vol_id, vol.status))

    def validate_credentials(self):
        if not self.cluster.ec2.is_valid_conn():
            raise exception.ClusterValidationError(
                'Invalid AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY combination.')
        return True

    def validate_keypair(self):
        cluster = self.cluster
        key_location = cluster.key_location
        if not key_location:
            raise exception.ClusterValidationError(
                "no key_location specified for key '%s'" %
                cluster.keyname)
        if not os.path.exists(key_location):
            raise exception.ClusterValidationError(
                "key_location '%s' does not exist" % key_location)
        elif not os.path.isfile(key_location):
            raise exception.ClusterValidationError(
                "key_location '%s' is not a file" % key_location)
        keyname = cluster.keyname
        keypair = cluster.ec2.get_keypair_or_none(keyname)
        if not keypair:
            raise exception.ClusterValidationError(
                "Keypair '%s' does not exist in region '%s'" %
                (keyname, cluster.ec2.region.name))
        fingerprint = keypair.fingerprint
        try:
            open(key_location, 'r').close()
        except IOError as e:
            raise exception.ClusterValidationError(
                "Error loading key_location '%s':\n%s\n"
                "Please check that the file is readable" % (key_location, e))
        if len(fingerprint) == 59:
            keyfingerprint = sshutils.get_private_rsa_fingerprint(key_location)
        elif len(fingerprint) == 47:
            keyfingerprint = sshutils.get_public_rsa_fingerprint(key_location)
        else:
            raise exception.ClusterValidationError(
                "Unrecognized fingerprint for %s: %s" % (keyname, fingerprint))
        if keyfingerprint != fingerprint:
            raise exception.ClusterValidationError(
                "Incorrect fingerprint for key_location '%s'\n\n"
                "local fingerprint: %s\n\nkeypair fingerprint: %s"
                % (key_location, keyfingerprint, fingerprint))
        return True

    def validate_userdata(self):
        for script in self.cluster.userdata_scripts:
            if not os.path.exists(script):
                raise exception.ClusterValidationError(
                    "Userdata script does not exist: %s" % script)
            if not os.path.isfile(script):
                raise exception.ClusterValidationError(
                    "Userdata script is not a file: %s" % script)
        if self.cluster.spot_bid is None:
            lmap = self.cluster._get_launch_map()
            aliases = max(lmap.values(), key=lambda x: len(x))
            ud = self.cluster._get_cluster_userdata(aliases)
        else:
            ud = self.cluster._get_cluster_userdata(
                [self.cluster._make_alias(id=1)])
        ud_size_kb = utils.size_in_kb(ud)
        if ud_size_kb > 16:
            raise exception.ClusterValidationError(
                "User data is too big! (%.2fKB)\n"
                "User data scripts combined and compressed must be <= 16KB\n"
                "NOTE: StarCluster uses anywhere from 0.5-2KB "
                "to store internal metadata" % ud_size_kb)

    def validate_vpc(self):
        if self.cluster.subnet_id:
            try:
                assert self.cluster.subnet is not None
            except exception.SubnetDoesNotExist as e:
                raise exception.ClusterValidationError(e)
            azone = self.cluster.availability_zone
            szone = self.cluster.subnet.availability_zone
            if azone and szone != azone:
                raise exception.ClusterValidationError(
                    "The cluster availability_zone (%s) does not match the "
                    "subnet zone (%s)" % (azone, szone))
            ip_count = self.cluster.subnet.available_ip_address_count
            nodes = self.cluster.nodes
            if not nodes and ip_count < self.cluster.cluster_size:
                raise exception.ClusterValidationError(
                    "Not enough IP addresses available in %s (%d)" %
                    (self.cluster.subnet.id, ip_count))
            if self.cluster.public_ips:
                gws = self.cluster.ec2.get_internet_gateways(filters={
                    'attachment.vpc-id': self.cluster.subnet.vpc_id})
                if not gws:
                    raise exception.ClusterValidationError(
                        "No internet gateway attached to VPC: %s" %
                        self.cluster.subnet.vpc_id)
                rtables = self.cluster.ec2.get_route_tables(filters={
                    'association.subnet-id': self.cluster.subnet_id,
                    'route.destination-cidr-block': static.WORLD_CIDRIP,
                    'route.gateway-id': gws[0].id})
                if not rtables:
                    raise exception.ClusterValidationError(
                        "No route to %s found for subnet: %s" %
                        (static.WORLD_CIDRIP, self.cluster.subnet_id))
            else:
                log.warn(user_msgs.public_ips_disabled %
                         dict(vpc_id=self.cluster.subnet.vpc_id))
        elif self.cluster.public_ips is False:
            raise exception.ClusterValidationError(
                "Only VPC clusters can disable public IP addresses")


if __name__ == "__main__":
    from starcluster.config import StarClusterConfig
    cfg = StarClusterConfig().load()
    sc = cfg.get_cluster_template('smallcluster', 'mynewcluster')
    if sc.is_valid():
        sc.start(create=True)

########NEW FILE########
__FILENAME__ = addnode
# Copyright 2009-2014 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

from starcluster import static
from completers import ClusterCompleter


class CmdAddNode(ClusterCompleter):
    """
    addnode [options] <cluster_tag>

    Add a node to a running cluster

    Examples:

        $ starcluster addnode mycluster

    This will launch a new node and add it to mycluster. The node's alias will
    be autogenerated based on the existing node aliases in the cluster.

    If you want to provide your own alias for the node use the -a option:

        $ starcluster addnode -a mynode mycluster

    This will add a new node called 'mynode' to mycluster.

    You can also add multiple nodes using the -n option:

        $ starcluster addnode -n 3 mycluster

    The above example will add three new nodes to mycluster with autogenerated
    aliases. If you'd rather provide your own aliases:

        $ starcluster addnode -a mynode1,mynode2,mynode3 mycluster

    This will add three new nodes to mycluster named mynode1, mynode2, and
    mynode3.

    If you've previously attempted to add a node and it failed due to a plugin
    error or other bug or if you used the 'removenode' command with the '-k'
    option and wish to re-add the node to the cluster without launching a new
    instance you can use the '-x' option:

        $ starcluster addnode -x -a mynode1 mycluster

    NOTE: The -x option requires the -a option

    This will add 'mynode1' to mycluster using the existing instance. If no
    instance exists with the alias specified by the '-a' option an error is
    reported. You can also do this for multiple nodes:

        $ starcluster addnode -x -a mynode1,mynode2,mynode3 mycluster
    """
    names = ['addnode', 'an']

    tag = None

    def addopts(self, parser):
        parser.add_option(
            "-a", "--alias", dest="alias", action="append", type="string",
            default=[], help="alias to give to the new node "
            "(e.g. node007, mynode, etc.)")
        parser.add_option(
            "-n", "--num-nodes", dest="num_nodes", action="store", type="int",
            default=1, help="number of new nodes to launch")
        parser.add_option(
            "-i", "--image-id", dest="image_id", action="store", type="string",
            default=None, help="image id for new node(s) "
            "(e.g. ami-12345678).")
        parser.add_option(
            "-I", "--instance-type", dest="instance_type",
            action="store", type="choice", default=None,
            choices=sorted(static.INSTANCE_TYPES.keys()),
            help="instance type to use when launching node")
        parser.add_option(
            "-z", "--availability-zone", dest="zone", action="store",
            type="string", default=None, help="availability zone for "
            "new node(s) (e.g. us-east-1)")
        parser.add_option(
            "-b", "--bid", dest="spot_bid", action="store", type="float",
            default=None, help="spot bid for new node(s) (in $ per hour)")
        parser.add_option(
            "-x", "--no-create", dest="no_create", action="store_true",
            default=False, help="do not launch new EC2 instances when "
            "adding nodes (use existing instances instead)")

    def execute(self, args):
        if len(args) != 1:
            self.parser.error("please specify a cluster <cluster_tag>")
        tag = self.tag = args[0]
        aliases = []
        for alias in self.opts.alias:
            aliases.extend(alias.split(','))
        if ('master' in aliases) or ('%s-master' % tag in aliases):
            self.parser.error(
                "'master' and '%s-master' are reserved aliases" % tag)
        num_nodes = self.opts.num_nodes
        if num_nodes == 1 and aliases:
            num_nodes = len(aliases)
        if num_nodes > 1 and aliases and len(aliases) != num_nodes:
            self.parser.error("you must specify the same number of aliases "
                              "(-a) as nodes (-n)")
        dupe = self._get_duplicate(aliases)
        if dupe:
            self.parser.error("cannot have duplicate aliases (duplicate: %s)" %
                              dupe)
        if not self.opts.alias and self.opts.no_create:
            self.parser.error("you must specify one or more node aliases via "
                              "the -a option when using -x")
        self.cm.add_nodes(tag, num_nodes, aliases=aliases,
                          image_id=self.opts.image_id,
                          instance_type=self.opts.instance_type,
                          zone=self.opts.zone, spot_bid=self.opts.spot_bid,
                          no_create=self.opts.no_create)

########NEW FILE########
__FILENAME__ = base
# Copyright 2009-2014 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

import os
import sys
import time

from starcluster import node
from starcluster import utils
from starcluster import cluster
from starcluster import completion
from starcluster.logger import log


class CmdBase(completion.CmdComplete):
    """
    Base class for StarCluster commands

    Each command consists of a class, which has the following properties:

    - Must have a class member 'names' which is a list of the names for
    the command

    - Can optionally define an addopts(self, parser) method which adds options
    to the given parser. This defines the command's options.
    """
    parser = None
    opts = None
    gopts = None
    gparser = None
    subcmds_map = None
    _cfg = None
    _ec2 = None
    _s3 = None
    _cm = None
    _nm = None

    @property
    def comp_words(self):
        """
        Property that returns COMP_WORDS from Bash/Zsh completion
        """
        return os.environ.get('COMP_WORDS', '').split()

    @property
    def goptions_dict(self):
        """
        Returns global options dictionary
        """
        return dict(getattr(self.gopts, '__dict__', {}))

    @property
    def options_dict(self):
        """
        Returns dictionary of options for this command
        """
        return dict(getattr(self.opts, '__dict__', {}))

    @property
    def specified_options_dict(self):
        """
        Return only those options with a non-None value
        """
        specified = {}
        options = self.options_dict
        for opt in options:
            if options[opt] is not None:
                specified[opt] = options[opt]
        return specified

    @property
    def log(self):
        return log

    @property
    def cfg(self):
        """
        Get global StarClusterConfig object
        """
        if not self._cfg:
            self._cfg = self.goptions_dict.get('CONFIG')
        return self._cfg

    @property
    def ec2(self):
        """
        Get EasyEC2 object from config and connect to the region specified
        by the user in the global options (if any)
        """
        if not self._ec2:
            ec2 = self.cfg.get_easy_ec2()
            if self.gopts.REGION:
                ec2.connect_to_region(self.gopts.REGION)
            self._ec2 = ec2
        return self._ec2

    @property
    def cluster_manager(self):
        """
        Returns ClusterManager object configured with self.cfg and self.ec2
        """
        if not self._cm:
            cm = cluster.ClusterManager(self.cfg, ec2=self.ec2)
            self._cm = cm
        return self._cm

    cm = cluster_manager

    @property
    def node_manager(self):
        """
        Returns NodeManager object configured with self.cfg and self.ec2
        """
        if not self._nm:
            nm = node.NodeManager(self.cfg, ec2=self.ec2)
            self._nm = nm
        return self._nm

    nm = node_manager

    @property
    def s3(self):
        if not self._s3:
            self._s3 = self.cfg.get_easy_s3()
        return self._s3

    def addopts(self, parser):
        pass

    def cancel_command(self, signum, frame):
        """
        Exits program with return value of 1
        """
        print
        log.info("Exiting...")
        sys.exit(1)

    def warn_experimental(self, msg, num_secs=10):
        """
        Warn user that an experimental feature is being used
        Counts down from num_secs before continuing
        """
        sep = '*' * 60
        log.warn('\n'.join([sep, msg, sep]), extra=dict(__textwrap__=True))
        r = range(1, num_secs + 1)
        r.reverse()
        print
        log.warn("Waiting %d seconds before continuing..." % num_secs)
        log.warn("Press CTRL-C to cancel...")
        for i in r:
            sys.stdout.write('%d...' % i)
            sys.stdout.flush()
            time.sleep(1)
        print

    def _positive_int(self, option, opt_str, value, parser):
        if value <= 0:
            parser.error("option %s must be a positive integer" % opt_str)
        setattr(parser.values, option.dest, value)

    def _iso_timestamp(self, option, opt_str, value, parser):
        if not utils.is_iso_time(value):
            parser.error("option %s must be an iso8601 formatted timestamp" %
                         opt_str)
        setattr(parser.values, option.dest, value)

    def _file_exists(self, option, opt_str, value, parser):
        path = os.path.abspath(os.path.expanduser(os.path.expandvars(value)))
        if not os.path.exists(path):
            parser.error("(%s) file does not exist: %s" % (opt_str, path))
        if not os.path.isfile(path):
            parser.error("(%s) path is not a file: %s" % (opt_str, path))
        setattr(parser.values, option.dest, path)

    def _build_dict(self, option, opt_str, value, parser):
        tagdict = getattr(parser.values, option.dest)
        tags = value.split(',')
        for tag in tags:
            tagparts = tag.split('=')
            if len(tagparts) != 2:
                parser.error("invalid tag: '%s' (correct example: key=value)" %
                             tag)
            key = tagparts[0]
            if not key:
                continue
            value = None
            if len(tagparts) == 2:
                value = tagparts[1]
            tagstore = tagdict.get(key)
            if isinstance(tagstore, basestring) and value:
                tagstore = [tagstore, value]
            elif isinstance(tagstore, list) and value:
                tagstore.append(value)
            else:
                tagstore = value
            tagdict[key] = tagstore
        setattr(parser.values, option.dest, tagdict)

    def _get_duplicate(self, lst):
        d = {}
        for item in lst:
            if item in d:
                return item
            else:
                d[item] = 0

########NEW FILE########
__FILENAME__ = completers
# Copyright 2009-2014 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

from starcluster import completion
from starcluster.logger import log

from base import CmdBase


class Completer(CmdBase):
    """
    Base class for all completer classes
    """

    @property
    def completer(self):
        return self._completer()


class ClusterCompleter(Completer):
    """
    Returns a list of all cluster names as completion options
    """
    def _completer(self):
        try:
            cm = self.cm
            clusters = cm.get_cluster_security_groups()
            completion_list = [cm.get_tag_from_sg(sg.name)
                               for sg in clusters]
            return completion.ListCompleter(completion_list)
        except Exception, e:
            log.error('something went wrong fix me: %s' % e)


class NodeCompleter(Completer):
    """
    Returns a list of all node names as completion options
    """
    def _completer(self):
        try:
            cm = self.cm
            clusters = cm.get_cluster_security_groups()
            compl_list = [cm.get_tag_from_sg(sg.name) for sg in clusters]
            max_num_nodes = 0
            for scluster in clusters:
                num_instances = len(scluster.instances())
                if num_instances > max_num_nodes:
                    max_num_nodes = num_instances
            compl_list.extend(['master'])
            compl_list.extend([str(i) for i in range(0, num_instances)])
            compl_list.extend(["node%03d" % i
                               for i in range(1, num_instances)])
            return completion.ListCompleter(compl_list)
        except Exception, e:
            print e
            log.error('something went wrong fix me: %s' % e)


class ImageCompleter(Completer):
    """
    Returns a list of all registered image ids as completion options
    """
    def _completer(self):
        try:
            rimages = self.ec2.registered_images
            completion_list = [i.id for i in rimages]
            return completion.ListCompleter(completion_list)
        except Exception, e:
            log.error('something went wrong fix me: %s' % e)


class EBSImageCompleter(Completer):
    """
    Returns a list of all registered EBS image ids as completion options
    """
    def _completer(self):
        try:
            rimages = self.ec2.registered_images
            completion_list = [i.id for i in rimages if
                               i.root_device_type == "ebs"]
            return completion.ListCompleter(completion_list)
        except Exception, e:
            log.error('something went wrong fix me: %s' % e)


class S3ImageCompleter(Completer):
    """
    Returns a list of all registered S3 image ids as completion options
    """
    def _completer(self):
        try:
            rimages = self.ec2.registered_images
            completion_list = [i.id for i in rimages if
                               i.root_device_type == "instance-store"]
            return completion.ListCompleter(completion_list)
        except Exception, e:
            log.error('something went wrong fix me: %s' % e)


class InstanceCompleter(Completer):
    """
    Returns a list of all instance ids as completion options
    """
    show_dns_names = False

    def _completer(self):
        try:
            instances = self.ec2.get_all_instances()
            completion_list = [i.id for i in instances]
            if self.show_dns_names:
                completion_list.extend([i.dns_name for i in instances])
            return completion.ListCompleter(completion_list)
        except Exception, e:
            log.error('something went wrong fix me: %s' % e)


class VolumeCompleter(Completer):
    """
    Returns a list of all volume ids as completion options
    """
    def _completer(self):
        try:
            completion_list = [v.id for v in self.ec2.get_volumes()]
            return completion.ListCompleter(completion_list)
        except Exception, e:
            log.error('something went wrong fix me: %s' % e)

########NEW FILE########
__FILENAME__ = createkey
# Copyright 2009-2014 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

from starcluster.logger import log

from base import CmdBase


class CmdCreateKey(CmdBase):
    """
    createkey [options] <name>

    Create a new Amazon EC2 keypair
    """
    names = ['createkey', 'ck']

    def addopts(self, parser):
        parser.add_option("-o", "--output-file", dest="output_file",
                          action="store", type="string", default=None,
                          help="Save the new keypair to a file")
        parser.add_option("-i", "--import-key", dest="rsa_key_file",
                          action="callback", type="string", default=None,
                          callback=self._file_exists,
                          help="Import an existing RSA key to EC2")
        # parser.add_option("-a","--add-to-config", dest="add_to_config",
        #                   action="store_true", default=False, help="add new
        #                   keypair to StarCluster config")

    def execute(self, args):
        if len(args) != 1:
            self.parser.error("please provide a key name")
        name = args[0]
        ofile = self.opts.output_file
        rsa_file = self.opts.rsa_key_file
        if rsa_file:
            kp = self.ec2.import_keypair(name, rsa_file)
        else:
            kp = self.ec2.create_keypair(name, output_file=ofile)
        log.info("Successfully created keypair: %s" % name)
        log.info("fingerprint: %s" % kp.fingerprint)
        if ofile and not rsa_file:
            log.info("keypair written to %s" % ofile)
        elif kp.material:
            log.info("contents: \n%s" % kp.material)

########NEW FILE########
__FILENAME__ = createvolume
# Copyright 2009-2014 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

import os

from starcluster import node
from starcluster import volume
from starcluster import static
from starcluster import exception

from base import CmdBase


class CmdCreateVolume(CmdBase):
    """
    createvolume [options] <volume_size> <volume_zone>

    Create a new EBS volume for use with StarCluster
    """

    names = ['createvolume', 'cv']

    def addopts(self, parser):
        parser.add_option(
            "-n", "--name", dest="name", action="store", type="string",
            default=None, help="Give the volume a user-friendly name "
            "(displayed in listvolumes command and in AWS console)")
        parser.add_option(
            "-b", "--bid", dest="spot_bid", action="store", type="float",
            default=None, help="Requests spot instances instead of flat "
            "rate instances. Uses SPOT_BID as max bid for the request.")
        parser.add_option(
            "-k", "--keypair", dest="keypair",
            action="store", type="string", default=None,
            help="The keypair to use when launching host instance "
            "(must be defined in the config)")
        parser.add_option(
            "-H", "--host-instance", dest="host_instance",
            action="store", type="string", default=None,
            help="Use specified instance as volume host rather than "
            "launching a new host")
        parser.add_option(
            "-d", "--detach-volume", dest="detach_vol",
            action="store_true", default=False,
            help="Detach new volume from host instance after creation")
        parser.add_option(
            "-s", "--shutdown-volume-host", dest="shutdown_instance",
            action="store_true", default=False,
            help="Shutdown host instance after creating new volume")
        parser.add_option(
            "-m", "--mkfs-cmd", dest="mkfs_cmd",
            action="store", type="string", default="mkfs.ext3",
            help="Specify alternate mkfs command to use when "
            "formatting volume (default: mkfs.ext3)")
        parser.add_option(
            "-i", "--image-id", dest="image_id",
            action="store", type="string", default=None,
            help="The AMI to use when launching volume host instance")
        parser.add_option(
            "-I", "--instance-type", dest="instance_type",
            action="store", type="choice", default="t1.micro",
            choices=sorted(static.INSTANCE_TYPES.keys()),
            help="The instance type to use when launching volume "
            "host instance (default: t1.micro)")
        parser.add_option(
            "-t", "--tag", dest="tags", action="callback", type="string",
            default={}, callback=self._build_dict,
            help="One or more tags to apply to the new volume (key=value)")

    def _load_keypair(self, keypair=None):
        key_location = None
        if keypair:
            kp = self.ec2.get_keypair(keypair)
            key = self.cfg.get_key(kp.name)
            key_location = key.get('key_location', '')
        else:
            self.log.info("No keypair specified, picking one from config...")
            for kp in self.ec2.keypairs:
                if kp.name in self.cfg.keys:
                    keypair = kp.name
                    kl = self.cfg.get_key(kp.name).get('key_location', '')
                    if os.path.exists(kl) and os.path.isfile(kl):
                        self.log.info('Using keypair: %s' % keypair)
                        key_location = kl
                        break
        if not keypair:
            raise exception.ConfigError(
                "no keypairs in region %s defined in config" %
                self.ec2.region.name)
        if not key_location:
            raise exception.ConfigError(
                "cannot determine key_location for keypair %s" % keypair)
        if not os.path.exists(key_location):
            raise exception.ValidationError(
                "key_location '%s' does not exist." % key_location)
        elif not os.path.isfile(key_location):
            raise exception.ValidationError(
                "key_location '%s' is not a file." % key_location)
        return (keypair, key_location)

    def _get_size_arg(self, size):
        errmsg = "size argument must be an integer >= 1"
        try:
            size = int(size)
            if size <= 0:
                self.parser.error(errmsg)
            return size
        except ValueError:
            self.parser.error(errmsg)

    def execute(self, args):
        if len(args) != 2:
            self.parser.error(
                "you must specify a size (in GB) and an availability zone")
        size, zone = args
        size = self._get_size_arg(size)
        zone = self.ec2.get_zone(zone).name
        key = self.opts.keypair
        host_instance = None
        if self.opts.host_instance:
            host_instance = self.ec2.get_instance(self.opts.host_instance)
            key = host_instance.key_name
        keypair, key_location = self._load_keypair(key)
        if host_instance:
            host_instance = node.Node(host_instance, key_location,
                                      alias="volumecreator_host")
        kwargs = self.specified_options_dict
        kwargs.update(dict(keypair=keypair, key_location=key_location,
                           host_instance=host_instance))
        vc = volume.VolumeCreator(self.ec2, **kwargs)
        if host_instance:
            vc._validate_host_instance(host_instance, zone)
        try:
            vc.create(size, zone, name=self.opts.name, tags=self.opts.tags)
        except KeyboardInterrupt:
            raise exception.CancelledCreateVolume()

########NEW FILE########
__FILENAME__ = downloadimage
# Copyright 2009-2014 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

from starcluster.logger import log

from completers import S3ImageCompleter


class CmdDownloadImage(S3ImageCompleter):
    """
    downloadimage [options] <image_id> <destination_directory>

    Download the manifest.xml and all AMI parts for an instance-store AMI

    Example:

        $ starcluster downloadimage ami-asdfasdf /data/myamis/ami-asdfasdf
    """
    names = ['downloadimage', 'di']

    bucket = None
    image_name = None

    def execute(self, args):
        if len(args) != 2:
            self.parser.error(
                'you must specify an <image_id> and <destination_directory>')
        image_id, destdir = args
        self.ec2.download_image_files(image_id, destdir)
        log.info("Finished downloading AMI: %s" % image_id)

########NEW FILE########
__FILENAME__ = ebsimage
# Copyright 2009-2014 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

import time

from starcluster import exception
from starcluster.logger import log

from completers import InstanceCompleter


class CmdEbsImage(InstanceCompleter):
    """
    ebsimage [options] <instance-id> <image_name>

    Create a new EBS image (AMI) from a running EC2 instance

    Example:

        $ starcluster ebsimage i-999999 my-new-image-ebs

    NOTE: It should now be safe to create an image from an instance launched by
    StarCluster. If you have issues please submit a bug report to the mailing
    list.
    """
    names = ['ebsimage', 'eimg']

    def addopts(self, parser):
        parser.add_option(
            "-d", "--description", dest="description", action="store",
            type="string",
            default="Image created @ %s" % time.strftime("%Y%m%d%H%M"),
            help="short description of this AMI")
        parser.add_option(
            "-D", "--snapshot-description", dest="snapshot_description",
            action="store", type="string",
            default="Snapshot created @ %s" % time.strftime("%Y%m%d%H%M"),
            help="short description for new EBS snapshot")
        parser.add_option(
            "-k", "--kernel-id", dest="kernel_id", action="store",
            type="string", default=None,
            help="kernel id for the new AMI")
        parser.add_option(
            "-r", "--ramdisk-id", dest="ramdisk_id", action="store",
            type="string", default=None,
            help="ramdisk id for the new AMI")
        parser.add_option(
            "-s", "--root-volume-size", dest="root_vol_size", type="int",
            action="callback", default=15, callback=self._positive_int,
            help="size of root volume (only used when creating an "
            "EBS image from an S3 instance)")

    def execute(self, args):
        if len(args) != 2:
            self.parser.error(
                'you must specify an instance-id and image name')
        instanceid, image_name = args
        i = self.ec2.get_instance(instanceid)
        is_ebs_backed = (i.root_device_type == "ebs")
        key_location = self.cfg.get_key(i.key_name).get('key_location')
        try:
            ami_id = self.ec2.create_ebs_image(instanceid, key_location,
                                               image_name,
                                               **self.specified_options_dict)
            log.info("Your new AMI id is: %s" % ami_id)
        except KeyboardInterrupt:
            raise exception.CancelledEBSImageCreation(image_name,
                                                      is_ebs_backed)

########NEW FILE########
__FILENAME__ = get
# Copyright 2009-2014 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

import glob

from starcluster import exception
from completers import ClusterCompleter


class CmdGet(ClusterCompleter):
    """
    get [options] <cluster_tag> [<remote_file_or_dir> ...] <local_destination>

    Copy one or more files from a running cluster to your local machine

    Examples:

        # Copy a file or dir from the master as root
        $ starcluster get mycluster /path/on/remote/server /local/file/or/dir

        # Copy a file and a dir from the master as root
        $ starcluster get mycluster /remote/file /remote/dir /local/dir

        # Copy a file or dir from the master as normal user
        $ starcluster get mycluster --user myuser /remote/path /local/path

        # Copy a file or dir from a node (node001 in this example)
        $ starcluster get mycluster --node node001 /remote/path /local/path

    """
    names = ['get']

    def addopts(self, parser):
        parser.add_option("-u", "--user", dest="user", default=None,
                          help="Transfer files as USER ")
        parser.add_option("-n", "--node", dest="node", default="master",
                          help="Transfer files from NODE (defaults to master)")

    def execute(self, args):
        if len(args) < 3:
            self.parser.error("please specify a cluster, remote file or " +
                              "directory, and a local destination path")
        ctag = args[0]
        lpath = args[-1]
        rpaths = args[1:-1]
        cl = self.cm.get_cluster(ctag, load_receipt=False)
        node = cl.get_node(self.opts.node)
        if self.opts.user:
            node.ssh.switch_user(self.opts.user)
        for rpath in rpaths:
            if not glob.has_magic(rpath) and not node.ssh.path_exists(rpath):
                raise exception.BaseException(
                    "Remote file or directory does not exist: %s" % rpath)
        node.ssh.get(rpaths, lpath)

########NEW FILE########
__FILENAME__ = help
# Copyright 2009-2014 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

import optparse

from base import CmdBase


class CmdHelp(CmdBase):
    """
    help

    Show StarCluster usage
    """
    names = ['help']

    def execute(self, args):
        if args:
            cmdname = args[0]
            try:
                sc = self.subcmds_map[cmdname]
                lparser = optparse.OptionParser(sc.__doc__.strip())
                if hasattr(sc, 'addopts'):
                    sc.addopts(lparser)
                lparser.print_help()
            except KeyError:
                raise SystemExit("Error: invalid command '%s'" % cmdname)
        else:
            self.gparser.parse_args(['--help'])

########NEW FILE########
__FILENAME__ = listbuckets
# Copyright 2009-2014 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

from base import CmdBase


class CmdListBuckets(CmdBase):
    """
    listbuckets

    List all S3 buckets
    """
    names = ['listbuckets', 'lb']

    def execute(self, args):
        self.s3.list_buckets()

########NEW FILE########
__FILENAME__ = listclusters
# Copyright 2009-2014 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

from completers import ClusterCompleter


class CmdListClusters(ClusterCompleter):
    """
    listclusters [<cluster_tag> ...]

    List all active clusters
    """
    names = ['listclusters', 'lc']

    def addopts(self, parser):
        parser.add_option("-s", "--show-ssh-status", dest="show_ssh_status",
                          action="store_true", default=False,
                          help="output whether SSH is up on each node or not")

    def execute(self, args):
        self.cm.list_clusters(cluster_groups=args,
                              show_ssh_status=self.opts.show_ssh_status)

########NEW FILE########
__FILENAME__ = listimages
# Copyright 2009-2014 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

from base import CmdBase


class CmdListImages(CmdBase):
    """
    listimages [options]

    List all registered EC2 images (AMIs)
    """
    names = ['listimages', 'li']

    def addopts(self, parser):
        parser.add_option(
            "-x", "--executable-by-me", dest="executable",
            action="store_true", default=False,
            help=("Show images owned by other users that " +
                  "you have permission to execute"))

    def execute(self, args):
        if self.opts.executable:
            self.ec2.list_executable_images()
        else:
            self.ec2.list_registered_images()

########NEW FILE########
__FILENAME__ = listinstances
# Copyright 2009-2014 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

from base import CmdBase


class CmdListInstances(CmdBase):
    """
    listinstances [options]

    List all running EC2 instances
    """
    names = ['listinstances', 'lsi']

    def addopts(self, parser):
        parser.add_option("-t", "--show-terminated", dest="show_terminated",
                          action="store_true", default=False,
                          help="show terminated instances")

    def execute(self, args):
        self.ec2.list_all_instances(self.opts.show_terminated)

########NEW FILE########
__FILENAME__ = listkeypairs
# Copyright 2009-2014 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

from base import CmdBase


class CmdListKeyPairs(CmdBase):
    """
    listkeypairs

    List all EC2 keypairs
    """
    names = ['listkeypairs', 'lk']

    def execute(self, args):
        self.ec2.list_keypairs()

########NEW FILE########
__FILENAME__ = listpublic
# Copyright 2009-2014 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

from base import CmdBase


class CmdListPublic(CmdBase):
    """
    listpublic

    List all public StarCluster images on EC2
    """
    names = ['listpublic', 'lp']

    def execute(self, args):
        self.ec2.list_starcluster_public_images()

########NEW FILE########
__FILENAME__ = listregions
# Copyright 2009-2014 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

from base import CmdBase


class CmdListRegions(CmdBase):
    """
    listregions

    List all EC2 regions
    """
    names = ['listregions', 'lr']

    def execute(self, args):
        self.ec2.list_regions()

########NEW FILE########
__FILENAME__ = listspots
# Copyright 2009-2014 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

from base import CmdBase


class CmdListSpots(CmdBase):
    """
    listspots

    List all EC2 spot instance requests
    """
    names = ['listspots', 'ls']

    def addopts(self, parser):
        parser.add_option("-c", "--show-closed", dest="show_closed",
                          action="store_true", default=False,
                          help="show closed/cancelled spot instance requests")

    def execute(self, args):
        self.ec2.list_all_spot_instances(self.opts.show_closed)

########NEW FILE########
__FILENAME__ = listvolumes
# Copyright 2009-2014 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

from starcluster import static

from base import CmdBase


class CmdListVolumes(CmdBase):
    """
    listvolumes

    List all EBS volumes
    """
    names = ['listvolumes', 'lv']

    def addopts(self, parser):
        parser.add_option("-n", "--name", dest="name", type="string",
                          default=None, action="store",
                          help="show all volumes with a given 'Name' tag")
        parser.add_option("-d", "--show-deleted", dest="show_deleted",
                          action="store_true", default=False,
                          help="show volumes that are being deleted")
        parser.add_option("-v", "--volume-id", dest="volume_id",
                          action="store", type="string", default=None,
                          help="show a single volume with id VOLUME_ID")
        parser.add_option("-s", "--size", dest="size", action="store",
                          type="string", default=None,
                          help="show all volumes of a particular size")
        parser.add_option("-S", "--status", dest="status", action="store",
                          default=None, choices=static.VOLUME_STATUS,
                          help="show all volumes with status")
        parser.add_option("-a", "--attach-status", dest="attach_status",
                          action="store", default=None,
                          choices=static.VOLUME_ATTACH_STATUS,
                          help="show all volumes with attachment status")
        parser.add_option("-z", "--zone", dest="zone", action="store",
                          type="string", default=None,
                          help="show all volumes in zone")
        parser.add_option("-i", "--snapshot-id", dest="snapshot_id",
                          action="store", type="string", default=None,
                          help="show all volumes created from snapshot")
        parser.add_option("-t", "--tag", dest="tags", type="string",
                          default={}, action="callback",
                          callback=self._build_dict,
                          help="show all volumes with a given tag")

    def execute(self, args):
        self.ec2.list_volumes(**self.options_dict)

########NEW FILE########
__FILENAME__ = listzones
# Copyright 2009-2014 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

from base import CmdBase


class CmdListZones(CmdBase):
    """
    listzones

    List all EC2 availability zones in the current region (default: us-east-1)
    """
    names = ['listzones', 'lz']

    def addopts(self, parser):
        parser.add_option("-r", "--region", dest="region", default=None,
                          help="Show all zones in a given region "
                          "(see listregions)")

    def execute(self, args):
        self.ec2.list_zones(region=self.opts.region)

########NEW FILE########
__FILENAME__ = loadbalance
# Copyright 2009-2014 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

from starcluster import exception
from starcluster.balancers import sge

from completers import ClusterCompleter


class CmdLoadBalance(ClusterCompleter):
    """
    loadbalance <cluster_tag>

    Start the SGE Load Balancer.

    Example:

        $ starcluster loadbalance mycluster

    This command will endlessly attempt to monitor and load balance 'mycluster'
    based on the current SGE load. You can also have the load balancer plot the
    various stats it's monitoring over time using the --plot-stats option:

        $ starcluster loadbalance -p mycluster

    If you just want the stats data and not the plots use the --dump-stats
    option instead:

        $ starcluster loadbalance -d mycluster

    See "starcluster loadbalance --help" for more details on the '-p' and '-d'
    options as well as other options for tuning the SGE load balancer
    algorithm.
    """

    names = ['loadbalance', 'bal']

    def addopts(self, parser):
        parser.add_option("-d", "--dump-stats", dest="dump_stats",
                          action="store_true", default=False,
                          help="Output stats to a csv file at each iteration")
        parser.add_option("-D", "--dump-stats-file", dest="stats_file",
                          action="store", default=None,
                          help="File to dump stats to (default: %s)" %
                          sge.DEFAULT_STATS_FILE % "<cluster_tag>")
        parser.add_option("-p", "--plot-stats", dest="plot_stats",
                          action="store_true", default=False,
                          help="Plot usage stats at each iteration")
        parser.add_option("-P", "--plot-output-dir", dest="plot_output_dir",
                          action="store", default=None,
                          help="Output directory for stats plots "
                          "(default: %s)" % sge.DEFAULT_STATS_DIR %
                          "<cluster_tag>")
        parser.add_option("-i", "--interval", dest="interval",
                          action="callback", type="int", default=None,
                          callback=self._positive_int,
                          help="Load balancer polling interval in seconds "
                          "(max: 300s)")
        parser.add_option("-m", "--max_nodes", dest="max_nodes",
                          action="callback", type="int", default=None,
                          callback=self._positive_int,
                          help="Maximum # of nodes in cluster")
        parser.add_option("-w", "--job_wait_time", dest="wait_time",
                          action="callback", type="int", default=None,
                          callback=self._positive_int,
                          help=("Maximum wait time for a job before "
                                "adding nodes, seconds"))
        parser.add_option("-a", "--add_nodes_per_iter", dest="add_pi",
                          action="callback", type="int", default=None,
                          callback=self._positive_int,
                          help="Number of nodes to add per iteration")
        parser.add_option("-k", "--kill_after", dest="kill_after",
                          action="callback", type="int", default=None,
                          callback=self._positive_int,
                          help="Minutes after which a node can be killed")
        parser.add_option("-s", "--stabilization_time", dest="stab",
                          action="callback", type="int", default=None,
                          callback=self._positive_int,
                          help="Seconds to wait before cluster "
                          "stabilizes (default: 180)")
        parser.add_option("-l", "--lookback_window", dest="lookback_win",
                          action="callback", type="int", default=None,
                          callback=self._positive_int,
                          help="Minutes to look back for past job history")
        parser.add_option("-n", "--min_nodes", dest="min_nodes",
                          action="callback", type="int", default=None,
                          callback=self._positive_int,
                          help="Minimum number of nodes in cluster")
        parser.add_option("-K", "--kill-cluster", dest="kill_cluster",
                          action="store_true", default=False,
                          help="Terminate the cluster when the queue is empty")

    def execute(self, args):
        if not self.cfg.globals.enable_experimental:
            raise exception.ExperimentalFeature("The 'loadbalance' command")
        if len(args) != 1:
            self.parser.error("please specify a <cluster_tag>")
        cluster_tag = args[0]
        cluster = self.cm.get_cluster(cluster_tag)
        lb = sge.SGELoadBalancer(**self.specified_options_dict)
        lb.run(cluster)

########NEW FILE########
__FILENAME__ = put
# Copyright 2009-2014 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

import os

from starcluster import exception
from completers import ClusterCompleter


class CmdPut(ClusterCompleter):
    """
    put [options] <cluster_tag> [<local_file_or_dir> ...] <remote_destination>

    Copy files to a running cluster

    Examples:

        # Copy a file or dir to the master as root
        $ starcluster put mycluster /path/to/file/or/dir /path/on/remote/server

        # Copy one or more files or dirs to the master as root
        $ starcluster put mycluster /local/dir /local/file /remote/dir

        # Copy a file or dir to the master as normal user
        $ starcluster put mycluster --user myuser /local/path /remote/path

        # Copy a file or dir to a node (node001 in this example)
        $ starcluster put mycluster --node node001 /local/path /remote/path


    This will copy a file or directory to the remote server
    """
    names = ['put']

    def addopts(self, parser):
        parser.add_option("-u", "--user", dest="user", default=None,
                          help="Transfer files as USER ")
        parser.add_option("-n", "--node", dest="node", default="master",
                          help="Transfer files to NODE (defaults to master)")

    def execute(self, args):
        if len(args) < 3:
            self.parser.error("please specify a cluster, local files or " +
                              "directories, and a remote destination path")
        ctag = args[0]
        rpath = args[-1]
        lpaths = args[1:-1]
        for lpath in lpaths:
            if not os.path.exists(lpath):
                raise exception.BaseException(
                    "Local file or directory does not exist: %s" % lpath)
        cl = self.cm.get_cluster(ctag, load_receipt=False)
        node = cl.get_node(self.opts.node)
        if self.opts.user:
            node.ssh.switch_user(self.opts.user)
        if len(lpaths) > 1 and not node.ssh.isdir(rpath):
            raise exception.BaseException("Remote path does not exist: %s" %
                                          rpath)
        node.ssh.put(lpaths, rpath)

########NEW FILE########
__FILENAME__ = removeimage
# Copyright 2009-2014 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

from starcluster.logger import log

from completers import ImageCompleter


class CmdRemoveImage(ImageCompleter):
    """
    removeimage [options] <imageid>

    Deregister an EC2 image (AMI)

    WARNING: This command, by default, will *permanently* remove an AMI from
    EC2. This includes removing any AMI files in the S3-backed case and the
    root volume snapshot in the EBS-backed case. Be careful!

    Example:

        $ starcluster removeimage ami-999999

    If the image is S3-backed then the image files on S3 will be removed in
    addition to deregistering the AMI.

    If the image is EBS-backed then the image's snapshot on EBS will be removed
    in addition to deregistering the AMI.

    If you'd rather keep the S3 files/EBS Snapshot backing the image use the
    --keep-image-data:

        $ starcluster removeimage -k ami-999999

    For S3-backed images this will leave the AMI's files on S3 instead of
    deleting them. For EBS-backed images this will leave the root volume
    snapshot on EBS instead of deleting it.
    """
    names = ['removeimage', 'ri']

    def addopts(self, parser):
        parser.add_option("-p", "--pretend", dest="pretend",
                          action="store_true", default=False,
                          help="pretend run, do not actually remove anything")
        parser.add_option("-c", "--confirm", dest="confirm",
                          action="store_true", default=False,
                          help="do not prompt for confirmation, "
                          "just remove the image")
        parser.add_option("-k", "--keep-image-data", dest="keep_image_data",
                          action="store_true", default=False,
                          help="only deregister the AMI, do not remove files "
                          "from S3 or delete EBS snapshot")

    def execute(self, args):
        if not args:
            self.parser.error("no images specified. exiting...")
        for arg in args:
            imageid = arg
            self.ec2.get_image(imageid)
            confirmed = self.opts.confirm
            pretend = self.opts.pretend
            keep_image_data = self.opts.keep_image_data
            if not confirmed:
                if not pretend:
                    resp = raw_input("**PERMANENTLY** delete %s (y/n)? " %
                                     imageid)
                    if resp not in ['y', 'Y', 'yes']:
                        log.info("Aborting...")
                        return
            self.ec2.remove_image(imageid, pretend=pretend,
                                  keep_image_data=keep_image_data)

########NEW FILE########
__FILENAME__ = removekey
# Copyright 2009-2014 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

from starcluster.logger import log

from base import CmdBase


class CmdRemoveKey(CmdBase):
    """
    removekey [options] <name>

    Remove a keypair from Amazon EC2
    """
    names = ['removekey', 'rk']

    def addopts(self, parser):
        parser.add_option("-c", "--confirm", dest="confirm",
                          action="store_true", default=False,
                          help="do not prompt for confirmation, just "
                          "remove the keypair")

    def execute(self, args):
        if len(args) != 1:
            self.parser.error("please provide a key name")
        name = args[0]
        kp = self.ec2.get_keypair(name)
        if not self.opts.confirm:
            resp = raw_input("**PERMANENTLY** delete keypair %s (y/n)? " %
                             name)
            if resp not in ['y', 'Y', 'yes']:
                log.info("Aborting...")
                return
        log.info("Removing keypair: %s" % name)
        kp.delete()

########NEW FILE########
__FILENAME__ = removenode
# Copyright 2009-2014 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.
import warnings

from starcluster.logger import log
from starcluster.commands.completers import ClusterCompleter


class CmdRemoveNode(ClusterCompleter):
    """
    removenode [options] <cluster_tag>

    Terminate one or more nodes in the cluster

    Examples:

        $ starcluster removenode mycluster

    This will automatically fetch a single worker node, detach it from the
    cluster, and then terminate it. If you'd rather be specific about which
    node(s) to remove then use the -a option:

        $ starcluster removenode mycluster -a node003

    You can also specify multiple nodes to remove and terminate one after
    another, e.g.:

        $ starcluster removenode mycluster -n 3

    or

        $ starcluster removenode mycluster -a node001,node002,node003

    If you'd rather not terminate the node(s) after detaching from the cluster,
    use the -k option:

        $ starcluster removenode -k mycluster -a node001,node002,node003

    This will detach the nodes from the cluster but leave the instances
    running. These nodes can then later be reattached to the cluster using:

        $ starcluster addnode mycluster -x -a node001,node002,node003

    This can be useful, for example, when testing on_add_node and
    on_remove_node methods in a StarCluster plugin.
    """
    names = ['removenode', 'rn']

    tag = None

    def addopts(self, parser):
        parser.add_option("-f", "--force", dest="force", action="store_true",
                          default=False,  help="Terminate node regardless "
                          "of errors if possible ")
        parser.add_option("-k", "--keep-instance", dest="terminate",
                          action="store_false", default=True,
                          help="do not terminate nodes "
                          "after detaching them from the cluster")
        parser.add_option("-c", "--confirm", dest="confirm",
                          action="store_true", default=False,
                          help="Do not prompt for confirmation, "
                          "just remove the node(s)")
        parser.add_option("-n", "--num-nodes", dest="num_nodes",
                          action="store", type="int", default=1,
                          help="number of nodes to remove")
        parser.add_option("-a", "--aliases", dest="aliases", action="append",
                          type="string", default=[],
                          help="list of nodes to remove (e.g. "
                          "node001,node002,node003)")

    def execute(self, args):
        if not len(args) >= 1:
            self.parser.error("please specify a cluster <cluster_tag>")
        if len(args) >= 2:
            warnings.warn(
                "Passing node names as arguments is deprecated. Please "
                "start using the -a option. Pass --help for more details",
                DeprecationWarning)
        tag = self.tag = args[0]
        aliases = []
        for alias in self.opts.aliases:
            aliases.extend(alias.split(','))
        old_form_aliases = args[1:]
        if old_form_aliases:
            if aliases:
                self.parser.error(
                    "you must either use a list of nodes as arguments OR "
                    "use the -a option - not both")
            else:
                aliases = old_form_aliases
        if ('master' in aliases) or ('%s-master' % tag in aliases):
            self.parser.error(
                "'master' and '%s-master' are reserved aliases" % tag)
        num_nodes = self.opts.num_nodes
        if num_nodes == 1 and aliases:
            num_nodes = len(aliases)
        if num_nodes > 1 and aliases and len(aliases) != num_nodes:
            self.parser.error("you must specify the same number of aliases "
                              "(-a) as nodes (-n)")
        dupe = self._get_duplicate(aliases)
        if dupe:
            self.parser.error("cannot have duplicate aliases (duplicate: %s)" %
                              dupe)
        if not self.opts.confirm:
            resp = raw_input("Remove %s from %s (y/n)? " %
                             (', '.join(aliases) or '%s nodes' % num_nodes,
                              tag))
            if resp not in ['y', 'Y', 'yes']:
                log.info("Aborting...")
                return
        self.cm.remove_nodes(tag, aliases=aliases, num_nodes=num_nodes,
                             terminate=self.opts.terminate,
                             force=self.opts.force)

########NEW FILE########
__FILENAME__ = removevolume
# Copyright 2009-2014 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

from starcluster.logger import log

from completers import VolumeCompleter


class CmdRemoveVolume(VolumeCompleter):
    """
    removevolume [options] <volume_id>

    Delete one or more EBS volumes

    WARNING: This command will *PERMANENTLY* remove an EBS volume.
    Please use caution!

    Example:

        $ starcluster removevolume vol-999999
    """
    names = ['removevolume', 'rv']

    def addopts(self, parser):
        parser.add_option("-c", "--confirm", dest="confirm",
                          action="store_true", default=False,
                          help="do not prompt for confirmation, just "
                          "remove the volume")

    def execute(self, args):
        if not args:
            self.parser.error("no volumes specified. exiting...")
        for arg in args:
            volid = arg
            vol = self.ec2.get_volume(volid)
            if vol.status in ['attaching', 'in-use']:
                log.error("volume is currently in use. aborting...")
                return
            if vol.status == 'detaching':
                log.error("volume is currently detaching. "
                          "please wait a few moments and try again...")
                return
            if not self.opts.confirm:
                resp = raw_input("**PERMANENTLY** delete %s (y/n)? " % volid)
                if resp not in ['y', 'Y', 'yes']:
                    log.info("Aborting...")
                    return
            if vol.delete():
                log.info("Volume %s deleted successfully" % vol.id)
            else:
                log.error("Error deleting volume %s" % vol.id)

########NEW FILE########
__FILENAME__ = resizevolume
# Copyright 2009-2014 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

from starcluster import node
from starcluster import volume
from starcluster import static

from createvolume import CmdCreateVolume


class CmdResizeVolume(CmdCreateVolume):
    """
    resizevolume [options] <volume_id> <volume_size>

    Resize an existing EBS volume

    NOTE: The EBS volume must either be unpartitioned or contain only a single
    partition. Any other configuration will be aborted.
    """

    names = ['resizevolume', 'res']

    def addopts(self, parser):
        parser.add_option(
            "-z", "--zone", dest="dest_zone",
            action="store", type="string", default=None,
            help="Create the resized volume in a different zone than the "
            "original volume (must be within the same region)")
        parser.add_option(
            "-k", "--keypair", dest="keypair",
            action="store", type="string", default=None,
            help="The keypair to use when launching host instance "
            "(must be defined in the config)")
        parser.add_option(
            "-H", "--host-instance", dest="host_instance",
            action="store", type="string", default=None,
            help="Use existing instance as volume host rather than "
            "launching a new host")
        parser.add_option(
            "-d", "--detach-volume", dest="detach_vol",
            action="store_true", default=False,
            help="Detach new volume from host instance after creation")
        parser.add_option(
            "-s", "--shutdown-volume-host", dest="shutdown_instance",
            action="store_true", default=False,
            help="Shutdown host instance after creating volume")
        parser.add_option(
            "-i", "--image-id", dest="image_id",
            action="store", type="string", default=None,
            help="The AMI to use when launching volume host instance")
        parser.add_option(
            "-I", "--instance-type", dest="instance_type",
            action="store", type="choice", default="t1.micro",
            choices=sorted(static.INSTANCE_TYPES.keys()),
            help="The instance type to use when launching volume "
            "host instance (default: t1.micro)")
        parser.add_option(
            "-r", "--resizefs-cmd", dest="resizefs_cmd",
            action="store", type="string", default="resize2fs",
            help="Specify alternate resizefs command to use when "
            "formatting volume (default: resize2fs)")

    def execute(self, args):
        if len(args) != 2:
            self.parser.error(
                "you must specify a volume id and a size (in GB)")
        volid, size = args
        size = self._get_size_arg(size)
        vol = self.ec2.get_volume(volid)
        zone = vol.zone
        if self.opts.dest_zone:
            zone = self.ec2.get_zone(self.opts.dest_zone).name
        key = self.opts.keypair
        host_instance = None
        if self.opts.host_instance:
            host_instance = self.ec2.get_instance(self.opts.host_instance)
            key = host_instance.key_name
        keypair, key_location = self._load_keypair(key)
        if host_instance:
            host_instance = node.Node(host_instance, key_location,
                                      alias="volumecreator_host")
        kwargs = self.specified_options_dict
        kwargs.update(dict(keypair=keypair, key_location=key_location,
                           host_instance=host_instance))
        vc = volume.VolumeCreator(self.ec2, **kwargs)
        if host_instance:
            vc._validate_host_instance(host_instance, zone)
        try:
            new_volid = vc.resize(vol, size, dest_zone=self.opts.dest_zone)
            if new_volid:
                self.log.info("Volume %s was successfully resized to %sGB" %
                              (volid, size))
                self.log.info("New volume id is: %s" % new_volid)
            else:
                self.log.error("failed to resize volume %s" % volid)
        except KeyboardInterrupt:
            self.cancel_command()

########NEW FILE########
__FILENAME__ = restart
# Copyright 2009-2014 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

from completers import ClusterCompleter


class CmdRestart(ClusterCompleter):
    """
    restart [options] <cluster_tag>

    Restart an existing cluster

    Example:

        $ starcluster restart mynewcluster

    This command will reboot each node (without terminating), wait for the
    nodes to come back up, and then reconfigures the cluster without losing
    any data on the node's local disk
    """
    names = ['restart', 'reboot']

    def addopts(self, parser):
        parser.add_option("-o", "--reboot-only", dest="reboot_only",
                          action="store_true", default=False,
                          help="only reboot EC2 instances (skip plugins)")

    tag = None

    def execute(self, args):
        if not args:
            self.parser.error("please specify a cluster <tag_name>")
        for arg in args:
            self.cm.restart_cluster(arg, reboot_only=self.opts.reboot_only)

########NEW FILE########
__FILENAME__ = runplugin
# Copyright 2009-2014 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

from base import CmdBase


class CmdRunPlugin(CmdBase):
    """
    runplugin <plugin_name> <cluster_tag>

    Run a StarCluster plugin on a running cluster

    plugin_name - name of plugin section defined in the config
    cluster_tag - tag name of a running StarCluster

    Example:

       $ starcluster runplugin myplugin mycluster
    """
    names = ['runplugin', 'rp']

    def execute(self, args):
        if len(args) != 2:
            self.parser.error("Please provide a plugin_name and <cluster_tag>")
        plugin_name, cluster_tag = args
        self.cm.run_plugin(plugin_name, cluster_tag)

########NEW FILE########
__FILENAME__ = s3image
# Copyright 2009-2014 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

import sys
import time
import warnings

from starcluster import exception
from starcluster.logger import log

from completers import InstanceCompleter


class CmdS3Image(InstanceCompleter):
    """
    s3image [options] <instance-id> <image_name> [<bucket>]

    Create a new instance-store (S3) AMI from a running EC2 instance

    Example:

        $ starcluster s3image i-999999 my-new-image mybucket

    NOTE: It should now be safe to create an image from an instance launched by
    StarCluster. If you have issues please submit a bug report to the mailing
    list.
    """
    names = ['s3image', 'simg', 'createimage']

    bucket = None
    image_name = None

    def addopts(self, parser):
        parser.add_option(
            "-d", "--description", dest="description", action="store",
            type="string",
            default="Image created @ %s" % time.strftime("%Y%m%d%H%M"),
            help="short description of this AMI")
        parser.add_option(
            "-k", "--kernel-id", dest="kernel_id", action="store",
            type="string", default=None,
            help="kernel id for the new AMI")
        parser.add_option(
            "-R", "--ramdisk-id", dest="ramdisk_id", action="store",
            type="string", default=None,
            help="ramdisk id for the new AMI")
        parser.add_option(
            "-r", "--remove-image-files", dest="remove_image_files",
            action="store_true", default=False,
            help="Remove generated image files on the "
            "instance after registering (for S3 AMIs)")

    def execute(self, args):
        if "createimage" in sys.argv:
            warnings.warn("createimage is deprecated and will go away in the "
                          "next release. please use the s3image/ebsimage "
                          "commands instead", DeprecationWarning)
        if len(args) != 3:
            self.parser.error(
                'you must specify an instance-id, image name, and bucket')
        bucket = None
        instanceid, image_name, bucket = args
        self.bucket = bucket
        self.image_name = image_name
        i = self.ec2.get_instance(instanceid)
        key_location = self.cfg.get_key(i.key_name).get('key_location')
        aws_user_id = self.cfg.aws.get('aws_user_id')
        ec2_cert = self.cfg.aws.get('ec2_cert')
        ec2_private_key = self.cfg.aws.get('ec2_private_key')
        try:
            ami_id = self.ec2.create_s3_image(instanceid, key_location,
                                              aws_user_id, ec2_cert,
                                              ec2_private_key, bucket,
                                              image_name=image_name,
                                              **self.specified_options_dict)
            log.info("Your new AMI id is: %s" % ami_id)
        except KeyboardInterrupt:
            raise exception.CancelledS3ImageCreation(self.bucket,
                                                     self.image_name)

########NEW FILE########
__FILENAME__ = shell
# Copyright 2009-2014 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

import os
import sys
import base64
import posixpath

import starcluster
from starcluster import utils
from starcluster import static
from starcluster.logger import log

from base import CmdBase


class CmdShell(CmdBase):
    """
    shell

    Load an interactive IPython shell configured for starcluster development

    The following objects are automatically available at the prompt:

        cfg - starcluster.config.StarClusterConfig instance
        cm - starcluster.cluster.ClusterManager instance
        ec2 - starcluster.awsutils.EasyEC2 instance
        s3 - starcluster.awsutils.EasyS3 instance

    All StarCluster modules are automatically imported in the IPython session
    along with all StarCluster dependencies (e.g. boto, ssh, etc.)

    If the --ipcluster=CLUSTER (-p) is passed, the IPython session will be
    automatically be configured to connect to the remote CLUSTER using
    IPython's parallel interface (requires IPython 0.11+). In this mode you
    will have the following additional objects available at the prompt:

        ipcluster - starcluster.cluster.Cluster instance for the cluster
        ipclient - IPython.parallel.Client instance for the cluster
        ipview - IPython.parallel.client.view.DirectView for the cluster

    Here's an example of how to run a parallel map across all nodes in the
    cluster:

        [~]> ipclient.ids
        [0, 1, 2, 3]
        [~]> res = ipview.map_async(lambda x: x**30, range(8))
        [~]> print res.get()
        [0,
         1,
         1073741824,
         205891132094649L,
         1152921504606846976L,
         931322574615478515625L,
         221073919720733357899776L,
         22539340290692258087863249L]

    See IPython parallel docs for more details
    (http://ipython.org/ipython-doc/stable/parallel)
    """

    names = ['shell', 'sh']

    def _add_to_known_hosts(self, node):
        log.info("Configuring local known_hosts file")
        user_home = os.path.expanduser('~')
        khosts = os.path.join(user_home, '.ssh', 'known_hosts')
        if not os.path.isfile(khosts):
            log.warn("Unable to configure known_hosts: file does not exist")
            return
        contents = open(khosts).read()
        if node.dns_name not in contents:
            server_pkey = node.ssh.get_server_public_key()
            khostsf = open(khosts, 'a')
            if contents[-1] != '\n':
                khostsf.write('\n')
            name_entry = '%s,%s' % (node.dns_name, node.ip_address)
            khostsf.write(' '.join([name_entry, server_pkey.get_name(),
                                    base64.b64encode(str(server_pkey)), '\n']))
            khostsf.close()

    def addopts(self, parser):
        parser.add_option("-p", "--ipcluster", dest="ipcluster",
                          action="store", type="string", default=None,
                          metavar="CLUSTER", help="configure a parallel "
                          "IPython session on CLUSTER")

    def execute(self, args):
        local_ns = dict(cfg=self.cfg, ec2=self.ec2, s3=self.s3, cm=self.cm,
                        starcluster=starcluster, log=log)
        if self.opts.ipcluster:
            log.info("Loading parallel IPython library")
            try:
                from IPython.parallel import Client
            except ImportError, e:
                self.parser.error(
                    "Error loading parallel IPython:"
                    "\n\n%s\n\n"
                    "NOTE: IPython 0.11+ must be installed to use -p" % e)
            tag = self.opts.ipcluster
            cl = self.cm.get_cluster(tag)
            region = cl.master_node.region.name
            ipcluster_dir = os.path.join(static.STARCLUSTER_CFG_DIR,
                                         'ipcluster')
            local_json = os.path.join(ipcluster_dir,
                                      "%s-%s.json" % (tag, region))
            if not os.path.exists(local_json):
                user_home = cl.master_node.getpwnam(cl.cluster_user).pw_dir
                profile_dir = posixpath.join(user_home, '.ipython',
                                             'profile_default')
                json = posixpath.join(profile_dir, 'security',
                                      'ipcontroller-client.json')
                if cl.master_node.ssh.isfile(json):
                    log.info("Fetching connector file from cluster...")
                    if not os.path.exists(ipcluster_dir):
                        os.makedirs(ipcluster_dir)
                    cl.master_node.ssh.get(json, local_json)
                else:
                    self.parser.error(
                        "IPython json file %s does not exist locally or on "
                        "the cluster. Make sure the ipcluster plugin has "
                        "been executed and completed successfully.")
            key_location = cl.master_node.key_location
            self._add_to_known_hosts(cl.master_node)
            log.info("Loading parallel IPython client and view")
            rc = Client(local_json, sshkey=key_location)
            local_ns['Client'] = Client
            local_ns['ipcluster'] = cl
            local_ns['ipclient'] = rc
            local_ns['ipview'] = rc[:]
        modules = [(starcluster.__name__ + '.' + module, module)
                   for module in starcluster.__all__]
        modules += [('boto', 'boto'), ('paramiko', 'paramiko'),
                    ('workerpool', 'workerpool'), ('jinja2', 'jinja2'),
                    ('Crypto', 'Crypto'), ('iptools', 'iptools')]
        for fullname, modname in modules:
            log.info('Importing module %s' % modname)
            try:
                __import__(fullname)
                local_ns[modname] = sys.modules[fullname]
            except ImportError, e:
                log.error("Error loading module %s: %s" % (modname, e))
        utils.ipy_shell(local_ns=local_ns)

########NEW FILE########
__FILENAME__ = showbucket
# Copyright 2009-2014 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

from base import CmdBase


class CmdShowBucket(CmdBase):
    """
    showbucket <bucket>

    Show all files in an S3 bucket

    Example:

        $ starcluster showbucket mybucket
    """
    names = ['showbucket', 'sb']

    def execute(self, args):
        if not args:
            self.parser.error('please specify an S3 bucket')
        for arg in args:
            self.s3.list_bucket(arg)

########NEW FILE########
__FILENAME__ = showconsole
# Copyright 2009-2014 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

from completers import InstanceCompleter


class CmdShowConsole(InstanceCompleter):
    """
    showconsole <instance-id>

    Show console output for an EC2 instance

    Example:

        $ starcluster showconsole i-999999

    This will display the startup logs for instance i-999999
    """
    names = ['showconsole', 'sc']

    def execute(self, args):
        if not len(args) == 1:
            self.parser.error('please provide an instance id')
        instance_id = args[0]
        self.ec2.show_console_output(instance_id)

########NEW FILE########
__FILENAME__ = showimage
# Copyright 2009-2014 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

from completers import S3ImageCompleter


class CmdShowImage(S3ImageCompleter):
    """
    showimage <image_id>

    Show all AMI parts and manifest files on S3 for an instance-store AMI

    Example:

        $ starcluster showimage ami-999999
    """
    names = ['showimage', 'shimg']

    def execute(self, args):
        if not args:
            self.parser.error('please specify an AMI id')
        for arg in args:
            self.ec2.list_image_files(arg)

########NEW FILE########
__FILENAME__ = spothistory
# Copyright 2009-2014 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

from datetime import timedelta

from starcluster import utils
from starcluster import static

from base import CmdBase


class CmdSpotHistory(CmdBase):
    """
    spothistory [options] <instance_type>

    Show spot instance pricing history stats (last 30 days by default)

    Examples:

    Show the current, max, and average spot price for m1.small instance type:

        $ starcluster spothistory m1.small

    Do the same but also plot the spot history over time in a web browser:

        $ starcluster spothistory -p m1.small
    """
    names = ['spothistory', 'shi']

    def addopts(self, parser):
        parser.add_option("-z", "--zone", dest="zone", default=None,
                          help="limit results to specific availability zone")
        parser.add_option("-d", "--days", dest="days_ago",
                          action="store", type="float", default=None,
                          help="provide history in the last DAYS_AGO days "
                          "(overrides -s option)")
        parser.add_option("-s", "--start-time", dest="start_time",
                          action="callback", type="string", default=None,
                          callback=self._iso_timestamp,
                          help="show price history after START_TIME (UTC)"
                          "(e.g. 2010-01-15T22:22:22Z)")
        parser.add_option("-e", "--end-time", dest="end_time",
                          action="callback", type="string", default=None,
                          callback=self._iso_timestamp,
                          help="show price history up until END_TIME (UTC)"
                          "(e.g. 2010-02-15T22:22:22Z)")
        parser.add_option("-p", "--plot", dest="plot",
                          action="store_true", default=False,
                          help="plot spot history in a web browser")
        parser.add_option("-v", "--vpc", dest="vpc",
                          action="store_true", default=False,
                          help="show spot prices for VPC")
        parser.add_option("-c", "--classic", dest="classic",
                          action="store_true", default=False,
                          help="show spot prices for EC2-Classic")

    def execute(self, args):
        instance_types = ', '.join(sorted(static.INSTANCE_TYPES.keys()))
        if len(args) != 1:
            self.parser.error(
                'please provide an instance type (options: %s)' %
                instance_types)
        if self.opts.classic and self.opts.vpc:
            self.parser.error("options -c and -v cannot be specified at "
                              "the same time")
        instance_type = args[0]
        if instance_type not in static.INSTANCE_TYPES:
            self.parser.error('invalid instance type. possible options: %s' %
                              instance_types)
        start = self.opts.start_time
        end = self.opts.end_time
        if self.opts.days_ago:
            if self.opts.start_time:
                self.parser.error("options -d and -s cannot be specified at "
                                  "the same time")
            if self.opts.end_time:
                end_tup = utils.iso_to_datetime_tuple(self.opts.end_time)
            else:
                end_tup = utils.get_utc_now()
            start = utils.datetime_tuple_to_iso(
                end_tup - timedelta(days=self.opts.days_ago))
        browser_cmd = self.cfg.globals.get("web_browser")
        self.ec2.get_spot_history(instance_type, start, end,
                                  zone=self.opts.zone, plot=self.opts.plot,
                                  plot_web_browser=browser_cmd,
                                  vpc=self.opts.vpc,
                                  classic=self.opts.classic)

########NEW FILE########
__FILENAME__ = sshinstance
# Copyright 2009-2014 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

import sys
from completers import InstanceCompleter


class CmdSshInstance(InstanceCompleter):
    """
    sshinstance [options] <instance-id> [<remote-command>]

    SSH to an EC2 instance

    Examples:

        $ starcluster sshinstance i-14e9157c
        $ starcluster sshinstance ec2-123-123-123-12.compute-1.amazonaws.com

    You can also execute commands without directly logging in:

        $ starcluster sshinstance i-14e9157c 'cat /etc/hosts'
    """
    names = ['sshinstance', 'si']
    show_dns_names = True

    def addopts(self, parser):
        parser.add_option("-u", "--user", dest="user", action="store",
                          type="string", default='root',
                          help="login as USER (defaults to root)")
        parser.add_option("-X", "--forward-x11", dest="forward_x11",
                          action="store_true", default=False,
                          help="enable X11 forwarding")
        parser.add_option("-A", "--forward-agent", dest="forward_agent",
                          action="store_true", default=False,
                          help="enable authentication agent forwarding")

    def execute(self, args):
        if not args:
            self.parser.error(
                "please specify an instance id or dns name to connect to")
        instance = args[0]
        cmd = ' '.join(args[1:])
        retval = self.nm.ssh_to_node(instance, user=self.opts.user,
                                     command=cmd,
                                     forward_x11=self.opts.forward_x11,
                                     forward_agent=self.opts.forward_agent)
        if cmd and retval is not None:
            sys.exit(retval)

########NEW FILE########
__FILENAME__ = sshmaster
# Copyright 2009-2014 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

import sys
from completers import ClusterCompleter


class CmdSshMaster(ClusterCompleter):
    """
    sshmaster [options] <cluster> [<remote-command>]

    SSH to a cluster's master node

    Example:

        $ sshmaster mycluster

    You can also execute commands without directly logging in:

        $ starcluster sshmaster mycluster 'cat /etc/hosts'
    """
    names = ['sshmaster', 'sm']

    def addopts(self, parser):
        parser.add_option("-u", "--user", dest="user", action="store",
                          type="string", default='root',
                          help="login as USER (defaults to root)")
        parser.add_option("-X", "--forward-x11", dest="forward_x11",
                          action="store_true", default=False,
                          help="enable X11 forwarding")
        parser.add_option("-A", "--forward-agent", dest="forward_agent",
                          action="store_true", default=False,
                          help="enable authentication agent forwarding")
        parser.add_option("-t", "--pseudo-tty", dest="pseudo_tty",
                          action="store_true", default=False,
                          help="enable pseudo-tty allocation (for interactive "
                          "commands and screens)")

    def execute(self, args):
        if not args:
            self.parser.error("please specify a cluster")
        clname = args[0]
        cmd = ' '.join(args[1:])
        retval = self.cm.ssh_to_master(clname, user=self.opts.user,
                                       command=cmd,
                                       pseudo_tty=self.opts.pseudo_tty,
                                       forward_x11=self.opts.forward_x11,
                                       forward_agent=self.opts.forward_agent)
        if cmd and retval is not None:
            sys.exit(retval)

########NEW FILE########
__FILENAME__ = sshnode
# Copyright 2009-2014 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

import sys
from completers import NodeCompleter


class CmdSshNode(NodeCompleter):
    """
    sshnode <cluster> <node> [<remote-command>]

    SSH to a cluster node

    Examples:

        $ starcluster sshnode mycluster master
        $ starcluster sshnode mycluster node001
        ...

    or same thing in shorthand:

        $ starcluster sshnode mycluster 0
        $ starcluster sshnode mycluster 1
        ...

    You can also execute commands without directly logging in:

        $ starcluster sshnode mycluster node001 'cat /etc/hosts'
    """
    names = ['sshnode', 'sn']

    def addopts(self, parser):
        parser.add_option("-u", "--user", dest="user", action="store",
                          type="string", default='root',
                          help="login as USER (defaults to root)")
        parser.add_option("-X", "--forward-x11", dest="forward_x11",
                          action="store_true", default=False,
                          help="enable X11 forwarding ")
        parser.add_option("-A", "--forward-agent", dest="forward_agent",
                          action="store_true", default=False,
                          help="enable authentication agent forwarding")
        parser.add_option("-t", "--pseudo-tty", dest="pseudo_tty",
                          action="store_true", default=False,
                          help="enable pseudo-tty allocation (for interactive "
                          "commands and screens)")

    def execute(self, args):
        if len(args) < 2:
            self.parser.error(
                "please specify a cluster and node to connect to")
        scluster = args[0]
        node = args[1]
        cmd = ' '.join(args[2:])
        retval = self.cm.ssh_to_cluster_node(
            scluster, node, user=self.opts.user, command=cmd,
            forward_x11=self.opts.forward_x11, pseudo_tty=self.opts.pseudo_tty,
            forward_agent=self.opts.forward_agent)
        if cmd and retval is not None:
            sys.exit(retval)

########NEW FILE########
__FILENAME__ = start
# Copyright 2009-2014 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

import time

from starcluster import static
from starcluster import exception
from starcluster import completion
from starcluster.templates import user_msgs
from starcluster.logger import log

from completers import ClusterCompleter


class CmdStart(ClusterCompleter):
    """
    start [options] <cluster_tag>

    Start a new cluster

    Example:

        $ starcluster start mynewcluster

    This will launch a cluster named "mynewcluster" using the settings from
    the default cluster template defined in the configuration file. The
    default cluster template is specified by the 'default_template' option in
    the [global] section of the config. To use another template besides the
    default use the -c (--cluster-template) option:

        $ starcluster start -c largecluster mynewcluster

    This will launch a cluster named "mynewcluster" using the settings from
    the "largecluster" cluster template instead of the default template.
    """
    names = ['start']

    def addopts(self, parser):
        templates = []
        if self.cfg:
            templates = self.cfg.clusters.keys()
        parser.add_option("-x", "--no-create", dest="no_create",
                          action="store_true", default=False,
                          help="do not launch new EC2 instances when "
                          "starting cluster (use existing instances instead)")
        parser.add_option("-o", "--create-only", dest="create_only",
                          action="store_true", default=False,
                          help="only launch/start EC2 instances, "
                          "do not perform any setup routines")
        parser.add_option("-v", "--validate-only", dest="validate_only",
                          action="store_true", default=False,
                          help="only validate cluster settings, do "
                          "not start a cluster")
        parser.add_option("-V", "--skip-validation", dest="validate",
                          action="store_false", default=True,
                          help="do not validate cluster settings")
        parser.add_option("-l", "--login-master", dest="login_master",
                          action="store_true", default=False,
                          help="login to master node after launch")
        parser.add_option("-q", "--disable-queue", dest="disable_queue",
                          action="store_true", default=None,
                          help="do not configure a queueing system (SGE)")
        parser.add_option("-Q", "--enable-queue", dest="disable_queue",
                          action="store_false", default=None,
                          help="configure a queueing system (SGE) (default)")
        parser.add_option("--force-spot-master",
                          dest="force_spot_master", action="store_true",
                          default=None, help="when creating a spot cluster "
                          "the default is to launch the master as "
                          "a flat-rate instance for stability. this option "
                          "forces launching the master node as a spot "
                          "instance when a spot cluster is requested.")
        parser.add_option("--no-spot-master", dest="force_spot_master",
                          action="store_false", default=None,
                          help="Do not launch the master node as a spot "
                          "instance when a spot cluster is requested. "
                          "(default)")
        parser.add_option("--public-ips", dest="public_ips",
                          default=None, action='store_true',
                          help="Assign public IPs to all VPC nodes "
                          "(VPC clusters only)"),
        parser.add_option("--no-public-ips", dest="public_ips",
                          default=None, action='store_false',
                          help="Do NOT assign public ips to all VPC nodes "
                          "(VPC clusters only) (default)"),
        opt = parser.add_option("-c", "--cluster-template", action="store",
                                dest="cluster_template", choices=templates,
                                default=None, help="cluster template to use "
                                "from the config file")
        if completion:
            opt.completer = completion.ListCompleter(opt.choices)
        parser.add_option("-r", "--refresh-interval", dest="refresh_interval",
                          type="int", action="callback", default=None,
                          callback=self._positive_int,
                          help="refresh interval when waiting for cluster "
                          "nodes to come up (default: 30)")
        parser.add_option("-b", "--bid", dest="spot_bid", action="store",
                          type="float", default=None,
                          help="requests spot instances instead of flat "
                          "rate instances. Uses SPOT_BID as max bid for "
                          "the request.")
        parser.add_option("-d", "--description", dest="cluster_description",
                          action="store", type="string",
                          default="Cluster requested at %s" %
                          time.strftime("%Y%m%d%H%M"),
                          help="brief description of cluster")
        parser.add_option("-s", "--cluster-size", dest="cluster_size",
                          action="callback", type="int", default=None,
                          callback=self._positive_int,
                          help="number of ec2 instances to launch")
        parser.add_option("-u", "--cluster-user", dest="cluster_user",
                          action="store", type="string", default=None,
                          help="name of user to create on cluster "
                          "(defaults to sgeadmin)")
        opt = parser.add_option("-S", "--cluster-shell", dest="cluster_shell",
                                action="store",
                                choices=static.AVAILABLE_SHELLS.keys(),
                                default=None,
                                help="shell for cluster user "
                                "(defaults to bash)")
        if completion:
            opt.completer = completion.ListCompleter(opt.choices)
        parser.add_option("-m", "--master-image-id", dest="master_image_id",
                          action="store", type="string", default=None,
                          help="AMI to use when launching master")
        parser.add_option("-n", "--node-image-id", dest="node_image_id",
                          action="store", type="string", default=None,
                          help="AMI to use when launching nodes")
        parser.add_option("-I", "--master-instance-type",
                          dest="master_instance_type", action="store",
                          choices=sorted(static.INSTANCE_TYPES.keys()),
                          default=None, help="instance type for the master "
                          "instance")
        opt = parser.add_option("-i", "--node-instance-type",
                                dest="node_instance_type", action="store",
                                choices=sorted(static.INSTANCE_TYPES.keys()),
                                default=None,
                                help="instance type for the node instances")
        if completion:
            opt.completer = completion.ListCompleter(opt.choices)
        parser.add_option("-a", "--availability-zone",
                          dest="availability_zone", action="store",
                          type="string", default=None,
                          help="availability zone to launch instances in")
        parser.add_option("-k", "--keyname", dest="keyname", action="store",
                          type="string", default=None,
                          help="name of the keypair to use when "
                          "launching the cluster")
        parser.add_option("-K", "--key-location", dest="key_location",
                          action="store", type="string", default=None,
                          metavar="FILE",
                          help="path to an ssh private key that matches the "
                          "cluster keypair")
        parser.add_option("-U", "--userdata-script", dest="userdata_scripts",
                          action="append", default=None, metavar="FILE",
                          help="Path to userdata script that will run on "
                          "each node on start-up. Can be used multiple times.")
        parser.add_option("-P", "--dns-prefix", dest="dns_prefix",
                          action='store_true',
                          help="Prefix dns names of all nodes in the cluster "
                          "with the cluster tag")
        parser.add_option("-p", "--no-dns-prefix", dest="dns_prefix",
                          action='store_false',
                          help="Do NOT prefix dns names of all nodes in the "
                          "cluster with the cluster tag (default)")
        parser.add_option("-N", "--subnet-id", dest="subnet_id",
                          action="store", type="string",
                          help=("Launch cluster into a VPC subnet"))

    def execute(self, args):
        if len(args) != 1:
            self.parser.error("please specify a <cluster_tag>")
        tag = args[0]
        create = not self.opts.no_create
        scluster = self.cm.get_cluster_group_or_none(tag)
        if scluster and create:
            scluster = self.cm.get_cluster(tag, group=scluster,
                                           load_receipt=False,
                                           require_keys=False)
            stopped_ebs = scluster.is_cluster_stopped()
            is_ebs = False
            if not stopped_ebs:
                is_ebs = scluster.is_ebs_cluster()
            raise exception.ClusterExists(tag, is_ebs=is_ebs,
                                          stopped_ebs=stopped_ebs)
        if not create and not scluster:
            raise exception.ClusterDoesNotExist(tag)
        create_only = self.opts.create_only
        validate = self.opts.validate
        validate_running = self.opts.no_create
        validate_only = self.opts.validate_only
        if scluster:
            scluster = self.cm.get_cluster(tag, group=scluster)
            validate_running = True
        else:
            template = self.opts.cluster_template
            if not template:
                try:
                    template = self.cm.get_default_cluster_template()
                except exception.NoDefaultTemplateFound, e:
                    try:
                        ctmpl = e.options[0]
                    except IndexError:
                        ctmpl = "smallcluster"
                    e.msg += " \n\nAlternatively, you can specify a cluster "
                    e.msg += "template to use by passing the '-c' option to "
                    e.msg += "the 'start' command, e.g.:\n\n"
                    e.msg += "    $ starcluster start -c %s %s" % (ctmpl, tag)
                    raise e
                log.info("Using default cluster template: %s" % template)
            scluster = self.cm.get_cluster_template(template, tag)
        scluster.update(self.specified_options_dict)
        if self.opts.keyname and not self.opts.key_location:
            key = self.cfg.get_key(self.opts.keyname)
            scluster.key_location = key.key_location
        if not self.opts.refresh_interval:
            interval = self.cfg.globals.get("refresh_interval")
            if interval is not None:
                scluster.refresh_interval = interval
        if self.opts.spot_bid is not None and not self.opts.no_create:
            msg = user_msgs.spotmsg % {'size': scluster.cluster_size,
                                       'tag': tag}
            if not validate_only and not create_only:
                self.warn_experimental(msg, num_secs=5)
        if self.opts.dns_prefix:
            scluster.dns_prefix = tag
        try:
            scluster.start(create=create, create_only=create_only,
                           validate=validate, validate_only=validate_only,
                           validate_running=validate_running)
        except KeyboardInterrupt:
            if validate_only:
                raise
            else:
                raise exception.CancelledStartRequest(tag)
        if validate_only:
            return
        if not create_only and not self.opts.login_master:
            log.info(user_msgs.cluster_started_msg %
                     dict(tag=scluster.cluster_tag),
                     extra=dict(__textwrap__=True, __raw__=True))
        if self.opts.login_master:
            scluster.ssh_to_master()

########NEW FILE########
__FILENAME__ = stop
# Copyright 2009-2014 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

from starcluster.logger import log
from starcluster import exception

from completers import ClusterCompleter


class CmdStop(ClusterCompleter):
    """
    stop [options] <cluster_tag> ...

    Stop a running EBS-backed cluster

    Example:

        $ starcluster stop mycluster

    The above command will put all flat-rate EBS-backed nodes in 'mycluster'
    into a 'stopped' state preserving the local disks. You can then use the
    start command with the -x (--no-create) option to resume the cluster later
    on without losing data on the local disks:

        $ starcluster start -x mycluster

    This will 'start' all 'stopped' non-spot EBS-backed instances and
    reconfigure the cluster.

    In general, all nodes in the cluster must be 'stoppable' meaning all nodes
    are backed by flat-rate EBS-backed instances. If any 'unstoppable' nodes
    are found an error is raised. A node is 'unstoppable' if it is backed by
    either a spot or S3-backed instance.

    However, if the cluster contains a mix of 'stoppable' and 'unstoppable'
    nodes you can stop all stoppable nodes and terminate any unstoppable nodes
    using the --terminate-unstoppable (-t) option:

        $ starcluster stop --terminate-unstoppable mycluster

    This will stop all nodes that can be stopped and terminate the rest.
    """
    names = ['stop']

    def addopts(self, parser):
        parser.add_option("-c", "--confirm", dest="confirm",
                          action="store_true", default=False,
                          help="Do not prompt for confirmation, "
                          "just stop the cluster")
        parser.add_option("-t", "--terminate-unstoppable",
                          dest="terminate_unstoppable", action="store_true",
                          default=False,  help="Terminate nodes that are not "
                          "stoppable (i.e. spot or S3-backed nodes)")
        parser.add_option("-f", "--force", dest="force", action="store_true",
                          default=False,  help="Stop cluster regardless of "
                          " errors if possible")

    def execute(self, args):
        if not args:
            cls = [c.cluster_tag for c in
                   self.cm.get_clusters(load_plugins=False,
                                        load_receipt=False)]
            msg = "please specify a cluster"
            if cls:
                opts = ', '.join(cls)
                msg = " ".join([msg, '(options:', opts, ')'])
            self.parser.error(msg)
        for cluster_name in args:
            try:
                cl = self.cm.get_cluster(cluster_name)
            except exception.ClusterDoesNotExist:
                raise
            except Exception, e:
                log.debug("Failed to load cluster settings!", exc_info=True)
                log.error("Failed to load cluster settings!")
                if self.opts.force:
                    log.warn("Ignoring cluster settings due to --force option")
                    cl = self.cm.get_cluster(cluster_name, load_receipt=False,
                                             require_keys=False)
                else:
                    if not isinstance(e, exception.IncompatibleCluster):
                        log.error("Use -f to forcefully stop the cluster")
                    raise
            is_stoppable = cl.is_stoppable()
            if not is_stoppable:
                has_stoppable_nodes = cl.has_stoppable_nodes()
                if not self.opts.terminate_unstoppable and has_stoppable_nodes:
                    raise exception.BaseException(
                        "Cluster '%s' contains 'stoppable' and 'unstoppable' "
                        "nodes. Your options are:\n\n"
                        "1. Use the --terminate-unstoppable option to "
                        "stop all 'stoppable' nodes and terminate all "
                        "'unstoppable' nodes\n\n"
                        "2. Use the 'terminate' command to destroy the "
                        "cluster.\n\nPass --help for more info." %
                        cluster_name)
                if not has_stoppable_nodes:
                    raise exception.BaseException(
                        "Cluster '%s' does not contain any 'stoppable' nodes "
                        "and can only be terminated. Please use the "
                        "'terminate' command instead to destroy the cluster."
                        "\n\nPass --help for more info" % cluster_name)
            if not self.opts.confirm:
                resp = raw_input("Stop cluster %s (y/n)? " % cluster_name)
                if resp not in ['y', 'Y', 'yes']:
                    log.info("Aborting...")
                    continue
            cl.stop_cluster(self.opts.terminate_unstoppable,
                            force=self.opts.force)
            log.warn("All non-spot, EBS-backed nodes are now in a "
                     "'stopped' state")
            log.warn("You can restart this cluster by passing -x "
                     "to the 'start' command")
            log.warn("Use the 'terminate' command to *completely* "
                     "terminate this cluster")

########NEW FILE########
__FILENAME__ = terminate
# Copyright 2009-2014 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

from starcluster import exception
from starcluster.logger import log

from completers import ClusterCompleter


class CmdTerminate(ClusterCompleter):
    """
    terminate [options] <cluster_tag> ...

    Terminate a running or stopped cluster

    Example:

        $ starcluster terminate mycluster

    This will terminate a currently running or stopped cluster tagged
    "mycluster".

    All nodes will be terminated, all spot requests (if any) will be
    cancelled, and the cluster's security group will be removed. If the
    cluster uses EBS-backed nodes then each node's root volume will be
    deleted.  If the cluster uses "cluster compute" instance types the
    cluster's placement group will also be removed.
    """
    names = ['terminate']

    def addopts(self, parser):
        parser.add_option("-c", "--confirm", dest="confirm",
                          action="store_true", default=False,
                          help="Do not prompt for confirmation, "
                          "just terminate the cluster")
        parser.add_option("-f", "--force", dest="force", action="store_true",
                          default=False,  help="Terminate cluster regardless "
                          "of errors if possible ")

    def _terminate_cluster(self, cl):
        if not self.opts.confirm:
            action = 'Terminate'
            if cl.is_ebs_cluster():
                action = 'Terminate EBS'
            resp = raw_input(
                "%s cluster %s (y/n)? " % (action, cl.cluster_tag))
            if resp not in ['y', 'Y', 'yes']:
                log.info("Aborting...")
                return
        cl.terminate_cluster()

    def _terminate_manually(self, cl):
        if not self.opts.confirm:
            resp = raw_input("Terminate cluster %s (y/n)? " % cl.cluster_tag)
            if resp not in ['y', 'Y', 'yes']:
                log.info("Aborting...")
                return
        insts = cl.cluster_group.instances()
        for inst in insts:
            log.info("Terminating %s" % inst.id)
            inst.terminate()
        cl.terminate_cluster(force=True)

    def terminate(self, cluster_name, force=False):
        if force:
            log.warn("Ignoring cluster settings due to --force option")
        try:
            cl = self.cm.get_cluster(cluster_name, load_receipt=not force,
                                     require_keys=not force)
            if force:
                self._terminate_manually(cl)
            else:
                self._terminate_cluster(cl)
        except exception.ClusterDoesNotExist:
            raise
        except Exception:
            log.error("Failed to terminate cluster!", exc_info=True)
            if not force:
                log.error("Use -f to forcefully terminate the cluster")
            raise

    def execute(self, args):
        if not args:
            self.parser.error("please specify a cluster")
        for cluster_name in args:
            try:
                self.terminate(cluster_name, force=self.opts.force)
            except EOFError:
                print 'Interrupted, exiting...'
                return

########NEW FILE########
__FILENAME__ = completion
# Copyright 2009-2014 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

#  Bash Protocol Description
#  -------------------------
#
#  `COMP_CWORD'
#       An index into `${COMP_WORDS}' of the word containing the current
#       cursor position.  This variable is available only in shell
#       functions invoked by the programmable completion facilities (*note
#       Programmable Completion::).
#
#  `COMP_LINE'
#       The current command line.  This variable is available only in
#       shell functions and external commands invoked by the programmable
#       completion facilities (*note Programmable Completion::).
#
#  `COMP_POINT'
#       The index of the current cursor position relative to the beginning
#       of the current command.  If the current cursor position is at the
#       end of the current command, the value of this variable is equal to
#       `${#COMP_LINE}'.  This variable is available only in shell
#       functions and external commands invoked by the programmable
#       completion facilities (*note Programmable Completion::).
#
#  `COMP_WORDS'
#       An array variable consisting of the individual words in the
#       current command line.  This variable is available only in shell
#       functions invoked by the programmable completion facilities (*note
#       Programmable Completion::).
#
#  `COMPREPLY'
#       An array variable from which Bash reads the possible completions
#       generated by a shell function invoked by the programmable
#       completion facility (*note Programmable Completion::).


import os
import re
import sys
import copy
import types
import logging
import optparse

from pprint import pformat
from optparse import OptionParser

import optcomplete
from optcomplete import AllCompleter
from optcomplete import DirCompleter
from optcomplete import ListCompleter
from optcomplete import NoneCompleter
from optcomplete import RegexCompleter

from starcluster import static

debugfn = os.path.join(static.STARCLUSTER_LOG_DIR, 'completion-debug.log')


def autocomplete(parser,
                 arg_completer=None,  # means use default.
                 opt_completer=None,
                 subcmd_completer=None,
                 subcommands=None):

    """Automatically detect if we are requested completing and if so generate
    completion automatically from given parser.

    'parser' is the options parser to use.

    'arg_completer' is a callable object that gets invoked to produce a list of
    completions for arguments completion (oftentimes files).

    'opt_completer' is the default completer to the options that require a
    value. 'subcmd_completer' is the default completer for the subcommand
    arguments.

    If 'subcommands' is specified, the script expects it to be a map of
    command-name to an object of any kind.  We are assuming that this object is
    a map from command name to a pair of (options parser, completer) for the
    command. If the value is not such a tuple, the method
    'autocomplete(completer)' is invoked on the resulting object.

    This will attempt to match the first non-option argument into a subcommand
    name and if so will use the local parser in the corresponding map entry's
    value.  This is used to implement completion for subcommand syntax and will
    not be needed in most cases."""

    # If we are not requested for complete, simply return silently, let the
    # code caller complete. This is the normal path of execution.
    if 'OPTPARSE_AUTO_COMPLETE' not in os.environ:
        return

    # Set default completers.
    if arg_completer is None:
        arg_completer = NoneCompleter()
    if opt_completer is None:
        opt_completer = NoneCompleter()
    if subcmd_completer is None:
        # subcmd_completer = arg_completer
        subcmd_completer = NoneCompleter()

    # By default, completion will be arguments completion, unless we find out
    # later we're trying to complete for an option.
    completer = arg_completer

    #
    # Completing...
    #

    # Fetching inputs... not sure if we're going to use these.

    # zsh's bashcompinit does not pass COMP_WORDS, replace with
    # COMP_LINE for now...
    if 'COMP_WORDS' not in os.environ:
        os.environ['COMP_WORDS'] = os.environ['COMP_LINE']

    cwords = os.environ['COMP_WORDS'].split()
    cline = os.environ['COMP_LINE']
    cpoint = int(os.environ['COMP_POINT'])
    cword = int(os.environ['COMP_CWORD'])

    # If requested, try subcommand syntax to find an options parser for that
    # subcommand.
    if subcommands:
        assert isinstance(subcommands, types.DictType)
        value = guess_first_nonoption(parser, subcommands)
        if value:
            if isinstance(value, (types.ListType, types.TupleType)):
                parser = value[0]
                if len(value) > 1 and value[1]:
                    # override completer for command if it is present.
                    completer = value[1]
                else:
                    completer = subcmd_completer
                return autocomplete(parser, completer)
            else:
                # Call completion method on object. This should call
                # autocomplete() recursively with appropriate arguments.
                if hasattr(value, 'autocomplete'):
                    return value.autocomplete(subcmd_completer)
                else:
                    sys.exit(1)  # no completions for that command object

    # Extract word enclosed word.
    prefix, suffix = optcomplete.extract_word(cline, cpoint)
    # The following would be less exact, but will work nonetheless .
    # prefix, suffix = cwords[cword], None

    # Look at previous word, if it is an option and it requires an argument,
    # check for a local completer.  If there is no completer, what follows
    # directly cannot be another option, so mark to not add those to
    # completions.
    optarg = False
    try:
        # Look for previous word, which will be containing word if the option
        # has an equals sign in it.
        prev = None
        if cword < len(cwords):
            mo = re.search('(--.*)=(.*)', cwords[cword])
            if mo:
                prev, prefix = mo.groups()
        if not prev:
            prev = cwords[cword - 1]

        if prev and prev.startswith('-'):
            option = parser.get_option(prev)
            if option:
                if option.nargs > 0:
                    optarg = True
                    if hasattr(option, 'completer'):
                        completer = option.completer
                    elif option.type != 'string':
                        completer = NoneCompleter()
                    else:
                        completer = opt_completer
                # Warn user at least, it could help him figure out the problem.
                elif hasattr(option, 'completer'):
                    raise SystemExit(
                        "Error: optparse option with a completer "
                        "does not take arguments: %s" % str(option))
    except KeyError:
        pass

    completions = []

    # Options completion.
    if not optarg and (not prefix or prefix.startswith('-')):
        completions += parser._short_opt.keys()
        completions += parser._long_opt.keys()
        # Note: this will get filtered properly below.

    # File completion.
    if completer and (not prefix or not prefix.startswith('-')):

        # Call appropriate completer depending on type.
        if isinstance(completer, (types.StringType, types.ListType,
                                  types.TupleType)):
            completer = RegexCompleter(completer)
            completions += completer(os.getcwd(), cline,
                                     cpoint, prefix, suffix)
        elif isinstance(completer, (types.FunctionType, types.LambdaType,
                                    types.ClassType, types.ObjectType)):
            completions += completer(os.getcwd(), cline,
                                     cpoint, prefix, suffix)

    # Filter using prefix.
    if prefix:
        completions = filter(lambda x: x.startswith(prefix), completions)

    # Print result.
    print ' '.join(completions)

    # Print debug output (if needed).  You can keep a shell with 'tail -f' to
    # the log file to monitor what is happening.
    if debugfn:
        f = open(debugfn, 'a')
        print >> f, '---------------------------------------------------------'
        print >> f, 'CWORDS', cwords
        print >> f, 'CLINE', cline
        print >> f, 'CPOINT', cpoint
        print >> f, 'CWORD', cword
        print >> f, '\nShort options'
        print >> f, pformat(parser._short_opt)
        print >> f, '\nLong options'
        print >> f, pformat(parser._long_opt)
        print >> f, 'Prefix/Suffix:', prefix, suffix
        print >> f, 'completions', completions
        f.close()

    # Exit with error code (we do not let the caller continue on purpose, this
    # is a run for completions only.)
    sys.exit(1)


def error_override(self, msg):
    """Hack to keep OptionParser from writing to sys.stderr when
    calling self.exit from self.error"""
    self.exit(2, msg=None)


def guess_first_nonoption(gparser, subcmds_map):

    """Given a global options parser, try to guess the first non-option without
    generating an exception. This is used for scripts that implement a
    subcommand syntax, so that we can generate the appropriate completions for
    the subcommand."""

    gparser = copy.deepcopy(gparser)

    def print_usage_nousage(self, file=None):
        pass
    gparser.print_usage = print_usage_nousage

    # save state to restore
    prev_interspersed = gparser.allow_interspersed_args
    gparser.disable_interspersed_args()

    cwords = os.environ['COMP_WORDS'].split()

    # save original error_func so we can put it back after the hack
    error_func = gparser.error
    try:
        try:
            instancemethod = type(OptionParser.error)
            # hack to keep OptionParser from wrinting to sys.stderr
            gparser.error = instancemethod(error_override,
                                           gparser, OptionParser)
            gopts, args = gparser.parse_args(cwords[1:])
        except SystemExit:
            return None
    finally:
        # undo the hack and restore original OptionParser error function
        gparser.error = instancemethod(error_func, gparser, OptionParser)

    value = None
    if args:
        subcmdname = args[0]
        try:
            value = subcmds_map[subcmdname]
        except KeyError:
            pass

    gparser.allow_interspersed_args = prev_interspersed  # restore state

    return value  # can be None, indicates no command chosen.


class CmdComplete(optcomplete.CmdComplete):
    """Simple default base class implementation for a subcommand that supports
    command completion.  This class is assuming that there might be a method
    addopts(self, parser) to declare options for this subcommand, and an
    optional completer data member to contain command-specific completion.  Of
    course, you don't really have to use this, but if you do it is convenient
    to have it here."""

    def autocomplete(self, completer):
        logging.disable(logging.CRITICAL)
        parser = optparse.OptionParser(self.__doc__.strip())
        if hasattr(self, 'addopts'):
            self.addopts(parser)
        if hasattr(self, 'completer'):
            completer = self.completer
        logging.disable(logging.NOTSET)
        return autocomplete(parser, completer)

NoneCompleter = NoneCompleter
ListCompleter = ListCompleter
AllCompleter = AllCompleter
DirCompleter = DirCompleter
RegexCompleter = RegexCompleter


if __name__ == '__main__':
    optcomplete.test()

########NEW FILE########
__FILENAME__ = config
# Copyright 2009-2014 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

import os
import urllib
import StringIO
import ConfigParser

from starcluster import utils
from starcluster import static
from starcluster import cluster
from starcluster import awsutils
from starcluster import deathrow
from starcluster import exception
from starcluster.cluster import Cluster
from starcluster.utils import AttributeDict

from starcluster.logger import log

DEBUG_CONFIG = False


def get_easy_s3(config_file=None, cache=False):
    """
    Factory for EasyS3 class that attempts to load AWS credentials from
    the StarCluster config file. Returns an EasyS3 object if
    successful.
    """
    cfg = get_config(config_file, cache)
    return cfg.get_easy_s3()


def get_easy_ec2(config_file=None, cache=False):
    """
    Factory for EasyEC2 class that attempts to load AWS credentials from
    the StarCluster config file. Returns an EasyEC2 object if
    successful.
    """
    cfg = get_config(config_file, cache)
    return cfg.get_easy_ec2()


def get_cluster_manager(config_file=None, cache=False):
    """
    Factory for ClusterManager class that attempts to load AWS credentials from
    the StarCluster config file. Returns a ClusterManager object if successful
    """
    cfg = get_config(config_file, cache)
    return cfg.get_cluster_manager()


def get_config(config_file=None, cache=False):
    """Factory for StarClusterConfig object"""
    return StarClusterConfig(config_file, cache).load()


class StarClusterConfig(object):
    """
    Loads StarCluster configuration settings defined in config_file
    which defaults to ~/.starclustercfg

    Settings are available as follows:

    cfg = StarClusterConfig()
    or
    cfg = StarClusterConfig('/path/to/my/config.cfg')
    cfg.load()
    aws_info = cfg.aws
    cluster_cfg = cfg.clusters['mycluster']
    key_cfg = cfg.keys['gsg-keypair']
    print cluster_cfg
    """

    global_settings = static.GLOBAL_SETTINGS
    aws_settings = static.AWS_SETTINGS
    key_settings = static.KEY_SETTINGS
    volume_settings = static.EBS_VOLUME_SETTINGS
    plugin_settings = static.PLUGIN_SETTINGS
    cluster_settings = static.CLUSTER_SETTINGS
    permission_settings = static.PERMISSION_SETTINGS

    # until i can find a way to query AWS for instance types...
    instance_types = static.INSTANCE_TYPES

    def __init__(self, config_file=None, cache=False):
        self.cfg_file = config_file \
            or os.environ.get('STARCLUSTER_CONFIG') \
            or static.STARCLUSTER_CFG_FILE
        self.cfg_file = os.path.expanduser(self.cfg_file)
        self.cfg_file = os.path.expandvars(self.cfg_file)
        self.type_validators = {
            int: self._get_int,
            float: self._get_float,
            str: self._get_string,
            bool: self._get_bool,
            list: self._get_list,
        }
        self._config = None
        self.globals = AttributeDict()
        self.aws = AttributeDict()
        self.clusters = AttributeDict()
        self.keys = AttributeDict()
        self.vols = AttributeDict()
        self.plugins = AttributeDict()
        self.permissions = AttributeDict()
        self.cache = cache

    def __repr__(self):
        return "<StarClusterConfig: %s>" % self.cfg_file

    def _get_urlfp(self, url):
        log.debug("Loading url: %s" % url)
        try:
            fp = urllib.urlopen(url)
            if fp.getcode() == 404:
                raise exception.ConfigError("url %s does not exist" % url)
            fp.name = url
            return fp
        except IOError, e:
            raise exception.ConfigError(
                "error loading config from url %s\n%s" % (url, e))

    def _get_fp(self, cfg_file):
        log.debug("Loading file: %s" % cfg_file)
        if os.path.exists(cfg_file):
            if not os.path.isfile(cfg_file):
                raise exception.ConfigError(
                    'config %s exists but is not a regular file' % cfg_file)
        else:
            raise exception.ConfigNotFound("config file %s does not exist\n" %
                                           cfg_file, cfg_file)
        return open(cfg_file)

    def _get_cfg_fp(self, cfg_file=None):
        cfg = cfg_file or self.cfg_file
        if utils.is_url(cfg):
            return self._get_urlfp(cfg)
        else:
            return self._get_fp(cfg)

    def _get_bool(self, config, section, option):
        try:
            opt = config.getboolean(section, option)
            return opt
        except ConfigParser.NoSectionError:
            pass
        except ConfigParser.NoOptionError:
            pass
        except ValueError:
            raise exception.ConfigError(
                "Expected True/False value for setting %s in section [%s]" %
                (option, section))

    def _get_int(self, config, section, option):
        try:
            opt = config.getint(section, option)
            return opt
        except ConfigParser.NoSectionError:
            pass
        except ConfigParser.NoOptionError:
            pass
        except ValueError:
            raise exception.ConfigError(
                "Expected integer value for setting %s in section [%s]" %
                (option, section))

    def _get_float(self, config, section, option):
        try:
            opt = config.getfloat(section, option)
            return opt
        except ConfigParser.NoSectionError:
            pass
        except ConfigParser.NoOptionError:
            pass
        except ValueError:
            raise exception.ConfigError(
                "Expected float value for setting %s in section [%s]" %
                (option, section))

    def _get_string(self, config, section, option):
        try:
            opt = config.get(section, option)
            return opt
        except ConfigParser.NoSectionError:
            pass
        except ConfigParser.NoOptionError:
            pass

    def _get_list(self, config, section, option):
        val = self._get_string(config, section, option)
        if val:
            val = [v.strip() for v in val.split(',')]
        return val

    def __load_config(self):
        """
        Populates self._config with a new ConfigParser instance
        """
        cfg = self._get_cfg_fp()
        try:
            cp = InlineCommentsIgnoredConfigParser()
            cp.readfp(cfg)
            self._config = cp
            try:
                self.globals = self._load_section('global',
                                                  self.global_settings)
                includes = self.globals.get('include')
                if not includes:
                    return cp
                mashup = StringIO.StringIO()
                cfg = self._get_cfg_fp()
                mashup.write(cfg.read() + '\n')
                for include in includes:
                    include = os.path.expanduser(include)
                    include = os.path.expandvars(include)
                    try:
                        contents = self._get_cfg_fp(include).read()
                        mashup.write(contents + '\n')
                    except exception.ConfigNotFound:
                        raise exception.ConfigError("include %s not found" %
                                                    include)
                mashup.seek(0)
                cp = InlineCommentsIgnoredConfigParser()
                cp.readfp(mashup)
                self._config = cp
            except exception.ConfigSectionMissing:
                pass
            return cp
        except ConfigParser.MissingSectionHeaderError:
            raise exception.ConfigHasNoSections(cfg.name)
        except ConfigParser.ParsingError, e:
            raise exception.ConfigError(e)

    def reload(self):
        """
        Reloads the configuration file
        """
        self.__load_config()
        return self.load()

    @property
    def config(self):
        if self._config is None:
            self._config = self.__load_config()
        return self._config

    def _load_settings(self, section_name, settings, store,
                       filter_settings=True):
        """
        Load section settings into a dictionary
        """
        section = self.config._sections.get(section_name)
        if not section:
            raise exception.ConfigSectionMissing(
                'Missing section %s in config' % section_name)
        store.update(section)
        section_conf = store
        for setting in settings:
            requirements = settings[setting]
            func, required, default, options, callback = requirements
            func = self.type_validators.get(func)
            value = func(self.config, section_name, setting)
            if value is not None:
                if options and value not in options:
                    raise exception.ConfigError(
                        '"%s" setting in section "%s" must be one of: %s' %
                        (setting, section_name,
                         ', '.join([str(o) for o in options])))
                if callback:
                    value = callback(value)
                section_conf[setting] = value
        if filter_settings:
            for key in store.keys():
                if key not in settings and key != '__name__':
                    store.pop(key)

    def _check_required(self, section_name, settings, store):
        """
        Check that all required settings were specified in the config.
        Raises ConfigError otherwise.

        Note that if a setting specified has required=True and
        default is not None then this method will not raise an error
        because a default was given. In short, if a setting is required
        you must provide None as the 'default' value.
        """
        section_conf = store
        for setting in settings:
            requirements = settings[setting]
            required = requirements[1]
            value = section_conf.get(setting)
            if value is None and required:
                raise exception.ConfigError(
                    'missing required option %s in section "%s"' %
                    (setting, section_name))

    def _load_defaults(self, settings, store):
        """
        Sets the default for each setting in settings regardless of whether
        the setting was specified in the config or not.
        """
        section_conf = store
        for setting in settings:
            default = settings[setting][2]
            if section_conf.get(setting) is None:
                if DEBUG_CONFIG:
                    log.debug('%s setting not specified. Defaulting to %s' %
                              (setting, default))
                section_conf[setting] = default

    def _load_extends_settings(self, section_name, store):
        """
        Loads all settings from other template(s) specified by a section's
        'extends' setting.

        This method walks a dependency tree of sections from bottom up. Each
        step is a group of settings for a section in the form of a dictionary.
        A 'master' dictionary is updated with the settings at each step. This
        causes the next group of settings to override the previous, and so on.
        The 'section_name' settings are at the top of the dependency tree.
        """
        section = store[section_name]
        extends = section.get('extends')
        if extends is None:
            return
        if DEBUG_CONFIG:
            log.debug('%s extends %s' % (section_name, extends))
        extensions = [section]
        while extends is not None:
            try:
                section = store[extends]
                if section in extensions:
                    exts = ', '.join([self._get_section_name(x['__name__'])
                                      for x in extensions])
                    raise exception.ConfigError(
                        "Cyclical dependency between sections %s. "
                        "Check your EXTENDS settings." % exts)
                extensions.insert(0, section)
            except KeyError:
                raise exception.ConfigError(
                    "%s can't extend non-existent section %s" %
                    (section_name, extends))
            extends = section.get('extends')
        transform = AttributeDict()
        for extension in extensions:
            transform.update(extension)
        store[section_name] = transform

    def _load_keypairs(self, store):
        cluster_section = store
        keyname = cluster_section.get('keyname')
        if not keyname:
            return
        keypair = self.keys.get(keyname)
        if keypair is None:
            raise exception.ConfigError(
                "keypair '%s' not defined in config" % keyname)
        cluster_section['keyname'] = keyname
        cluster_section['key_location'] = keypair.get('key_location')

    def _load_volumes(self, store):
        cluster_section = store
        volumes = cluster_section.get('volumes')
        if not volumes or isinstance(volumes, AttributeDict):
            return
        vols = AttributeDict()
        cluster_section['volumes'] = vols
        for volume in volumes:
            if volume not in self.vols:
                raise exception.ConfigError(
                    "volume '%s' not defined in config" % volume)
            vol = self.vols.get(volume).copy()
            del vol['__name__']
            vols[volume] = vol

    def _load_plugins(self, store):
        cluster_section = store
        plugins = cluster_section.get('plugins')
        if not plugins or isinstance(plugins[0], AttributeDict):
            return
        plugs = []
        for plugin in plugins:
            if plugin not in self.plugins:
                raise exception.ConfigError(
                    "plugin '%s' not defined in config" % plugin)
            plugs.append(self.plugins.get(plugin))
        cluster_section['plugins'] = plugs

    def _load_permissions(self, store):
        cluster_section = store
        permissions = cluster_section.get('permissions')
        if not permissions or isinstance(permissions, AttributeDict):
            return
        perms = AttributeDict()
        cluster_section['permissions'] = perms
        for perm in permissions:
            if perm in self.permissions:
                p = self.permissions.get(perm)
                p['__name__'] = p['__name__'].split()[-1]
                perms[perm] = p
            else:
                raise exception.ConfigError(
                    "permission '%s' not defined in config" % perm)

    def _load_instance_types(self, store):
        cluster_section = store
        instance_types = cluster_section.get('node_instance_type')
        if isinstance(instance_types, basestring):
            return
        itypes = []
        cluster_section['node_instance_types'] = itypes
        total_num_nodes = 0
        choices_string = ', '.join(static.INSTANCE_TYPES.keys())
        try:
            default_instance_type = instance_types[-1]
            if default_instance_type not in static.INSTANCE_TYPES:
                raise exception.ConfigError(
                    "invalid node_instance_type specified: '%s'\n"
                    "must be one of: %s" %
                    (default_instance_type, choices_string))
        except IndexError:
            default_instance_type = None
        cluster_section['node_instance_type'] = default_instance_type
        for type_spec in instance_types[:-1]:
            type_spec = type_spec.split(':')
            if len(type_spec) > 3:
                raise exception.ConfigError(
                    "invalid node_instance_type item specified: %s" %
                    type_spec)
            itype = type_spec[0]
            itype_image = None
            itype_num = 1
            if itype not in static.INSTANCE_TYPES:
                raise exception.ConfigError(
                    "invalid type specified (%s) in node_instance_type "
                    "item: '%s'\nmust be one of: %s" %
                    (itype, type_spec, choices_string))
            if len(type_spec) == 2:
                itype, next_var = type_spec
                try:
                    itype_num = int(next_var)
                except (TypeError, ValueError):
                    itype_image = next_var
            elif len(type_spec) == 3:
                itype, itype_image, itype_num = type_spec
            try:
                itype_num = int(itype_num)
                if itype_num < 1:
                    raise TypeError
                total_num_nodes += itype_num
            except (ValueError, TypeError):
                raise exception.ConfigError(
                    "number of instances (%s) of type '%s' must "
                    "be an integer > 1" % (itype_num, itype))
            itype_dic = AttributeDict(size=itype_num, image=itype_image,
                                      type=itype)
            itypes.append(itype_dic)

    def _load_section(self, section_name, section_settings,
                      filter_settings=True):
        """
        Returns a dictionary containing all section_settings for a given
        section_name by first loading the settings in the config, loading
        the defaults for all settings not specified, and then checking
        that all required options have been specified
        """
        store = AttributeDict()
        self._load_settings(section_name, section_settings, store,
                            filter_settings)
        self._load_defaults(section_settings, store)
        self._check_required(section_name, section_settings, store)
        return store

    def _get_section_name(self, section):
        """
        Returns section name minus prefix
        e.g.
        $ print self._get_section('cluster smallcluster')
        $ smallcluster
        """
        return section.split()[1]

    def _get_sections(self, section_prefix):
        """
        Returns all sections starting with section_prefix
        e.g.
        $ print self._get_sections('cluster')
        $ ['cluster smallcluster', 'cluster mediumcluster', ..]
        """
        return [s for s in self.config.sections() if
                s.startswith(section_prefix)]

    def _load_sections(self, section_prefix, section_settings,
                       filter_settings=True):
        """
        Loads all sections starting with section_prefix and returns a
        dictionary containing the name and dictionary of settings for each
        section.
        keys --> section name (as returned by self._get_section_name)
        values --> dictionary of settings for a given section

        e.g.
        $ print self._load_sections('volumes', self.plugin_settings)

        {'myvol': {'__name__': 'volume myvol',
                    'device': None,
                    'mount_path': '/home',
                    'partition': 1,
                    'volume_id': 'vol-999999'},
         'myvol2': {'__name__': 'volume myvol2',
                       'device': None,
                       'mount_path': '/myvol2',
                       'partition': 1,
                       'volume_id': 'vol-999999'},
        """
        sections = self._get_sections(section_prefix)
        sections_store = AttributeDict()
        for sec in sections:
            name = self._get_section_name(sec)
            sections_store[name] = self._load_section(sec, section_settings,
                                                      filter_settings)
        return sections_store

    def _load_cluster_sections(self, cluster_sections):
        """
        Loads all cluster sections. Similar to _load_sections but also handles
        populating specified keypair, volume, plugins, permissions, etc.
        settings
        """
        clusters = cluster_sections
        cluster_store = AttributeDict()
        for cl in clusters:
            name = self._get_section_name(cl)
            cluster_store[name] = AttributeDict()
            self._load_settings(cl, self.cluster_settings, cluster_store[name])
        for cl in clusters:
            name = self._get_section_name(cl)
            self._load_extends_settings(name, cluster_store)
            self._load_defaults(self.cluster_settings, cluster_store[name])
            self._load_keypairs(cluster_store[name])
            self._load_volumes(cluster_store[name])
            self._load_plugins(cluster_store[name])
            self._load_permissions(cluster_store[name])
            self._load_instance_types(cluster_store[name])
            self._check_required(cl, self.cluster_settings,
                                 cluster_store[name])
        return cluster_store

    def load(self):
        """
        Populate this config object from the StarCluster config
        """
        log.debug('Loading config')
        try:
            self.globals = self._load_section('global', self.global_settings)
        except exception.ConfigSectionMissing:
            pass
        try:
            self.aws = self._load_section('aws info', self.aws_settings)
        except exception.ConfigSectionMissing:
            log.warn("No [aws info] section found in the config!")
        self.aws.update(self.get_settings_from_env(self.aws_settings))
        self.keys = self._load_sections('key', self.key_settings)
        self.vols = self._load_sections('volume', self.volume_settings)
        self.vols.update(self._load_sections('vol', self.volume_settings))
        self.plugins = self._load_sections('plugin', self.plugin_settings,
                                           filter_settings=False)
        self.permissions = self._load_sections('permission',
                                               self.permission_settings)
        sections = self._get_sections('cluster')
        self.clusters = self._load_cluster_sections(sections)
        return self

    def get_settings_from_env(self, settings):
        """
        Returns AWS credentials defined in the user's shell
        environment.
        """
        found = {}
        for key in settings:
            if key.upper() in os.environ:
                log.warn("Setting '%s' from environment..." % key.upper())
                found[key] = os.environ.get(key.upper())
            elif key in os.environ:
                log.warn("Setting '%s' from environment..." % key)
                found[key] = os.environ.get(key)
        return found

    def get_cluster_template(self, template_name, tag_name=None,
                             ec2_conn=None):
        """
        Returns Cluster instance configured with the settings in the
        config file.

        template_name is the name of a cluster section defined in the config

        tag_name if not specified will be set to template_name
        """
        try:
            kwargs = {}
            tag_name = tag_name or template_name
            kwargs.update(dict(cluster_tag=tag_name))
            kwargs.update(self.clusters[template_name])
            plugs = kwargs.get('plugins')
            kwargs['plugins'] = deathrow._load_plugins(plugs,
                                                       debug=DEBUG_CONFIG)
            if not ec2_conn:
                ec2_conn = self.get_easy_ec2()

            clust = Cluster(ec2_conn, **kwargs)
            return clust
        except KeyError:
            raise exception.ClusterTemplateDoesNotExist(template_name)

    def get_default_cluster_template(self):
        """
        Returns the default_template specified in the [global] section
        of the config. Raises NoDefaultTemplateFound if no default cluster
        template has been specified in the config.
        """
        default = self.globals.get('default_template')
        if not default:
            raise exception.NoDefaultTemplateFound(
                options=self.clusters.keys())
        if default not in self.clusters:
            raise exception.ClusterTemplateDoesNotExist(default)
        return default

    def get_clusters(self):
        clusters = []
        for cl in self.clusters:
            clusters.append(self.get_cluster_template(cl, tag_name=cl))
        return clusters

    def get_plugin(self, plugin):
        try:
            return self.plugins[plugin]
        except KeyError:
            raise exception.PluginNotFound(plugin)

    def get_key(self, keyname):
        try:
            return self.keys[keyname]
        except KeyError:
            raise exception.KeyNotFound(keyname)

    def get_easy_s3(self):
        """
        Factory for EasyEC2 class that attempts to load AWS credentials from
        the StarCluster config file. Returns an EasyS3 object if
        successful.
        """
        try:
            s3 = awsutils.EasyS3(**self.aws)
            return s3
        except TypeError:
            raise exception.ConfigError("no aws credentials found")

    def get_easy_ec2(self):
        """
        Factory for EasyEC2 class that attempts to load AWS credentials from
        the StarCluster config file. Returns an EasyEC2 object if
        successful.
        """
        try:
            ec2 = awsutils.EasyEC2(**self.aws)
            return ec2
        except TypeError:
            raise exception.ConfigError("no aws credentials found")

    def get_cluster_manager(self):
        ec2 = self.get_easy_ec2()
        return cluster.ClusterManager(self, ec2)


class InlineCommentsIgnoredConfigParser(ConfigParser.ConfigParser):
    """
    Class for custom config file parsing that ignores inline comments.

    By default, ConfigParser.ConfigParser only ignores inline comments denoted
    by a semicolon. This class extends this support to allow inline comments
    denoted by '#' as well. Just as with semicolons, a spacing character must
    precede the pound sign for it to be considered an inline comment.

    For example, the following line would have the inline comment ignored:

        FOO = bar # some comment...

    And would be parsed as:

        FOO = bar

    The following would NOT have the comment removed:

        FOO = bar# some comment...
    """

    def readfp(self, fp, filename=None):
        """
        Overrides ConfigParser.ConfigParser.readfp() to ignore inline comments.
        """
        if filename is None:
            try:
                filename = fp.name
            except AttributeError:
                filename = '<???>'

        # We don't use the file iterator here because ConfigParser.readfp()
        # guarantees to only call readline() on fp, so we want to adhere to
        # this as well.
        commentless_fp = StringIO.StringIO()
        line = fp.readline()
        while line:
            pound_pos = line.find('#')

            # A pound sign only starts an inline comment if it is preceded by
            # whitespace.
            if pound_pos > 0 and line[pound_pos - 1].isspace():
                line = line[:pound_pos].rstrip() + '\n'
            commentless_fp.write(line)
            line = fp.readline()
        commentless_fp.seek(0)

        # Cannot use super() because ConfigParser is not a new-style class.
        ConfigParser.ConfigParser.readfp(self, commentless_fp, filename)


if __name__ == "__main__":
    from pprint import pprint
    cfg = StarClusterConfig().load()
    pprint(cfg.aws)
    pprint(cfg.clusters)
    pprint(cfg.keys)
    pprint(cfg.vols)

########NEW FILE########
__FILENAME__ = deathrow
# Copyright 2009-2014 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

"""
Contains code that should eventually be removed. Mostly used for maintaining
backwards compatibility while still moving the code forward.
"""
from starcluster import utils
from starcluster import exception
from starcluster import clustersetup
from starcluster.logger import log


def _load_plugins(plugins, debug=True):
    """
    Do not use - will be removed in the next release!

    Merge this into StarClusterConfig._load_plugins in a future release.
    Currently used to provide backwards compatibility for the plugin kwarg for
    Cluster. Cluster now expects the plugins kwarg to be a list of plugin
    objects not a list of dicts. This should be merged into
    StarClusterConfig._load_plugins in a future release after warning about the
    change in a previous release.
    """
    plugs = []
    for plugin in plugins:
        setup_class = plugin.get('setup_class')
        plugin_name = plugin.get('__name__').split()[-1]
        mod_name = '.'.join(setup_class.split('.')[:-1])
        class_name = setup_class.split('.')[-1]
        try:
            mod = __import__(mod_name, globals(), locals(), [class_name])
        except SyntaxError, e:
            raise exception.PluginSyntaxError(
                "Plugin %s (%s) contains a syntax error at line %s" %
                (plugin_name, e.filename, e.lineno))
        except ImportError, e:
            raise exception.PluginLoadError(
                "Failed to import plugin %s: %s" %
                (plugin_name, e[0]))
        klass = getattr(mod, class_name, None)
        if not klass:
            raise exception.PluginError(
                'Plugin class %s does not exist' % setup_class)
        if not issubclass(klass, clustersetup.ClusterSetup):
            raise exception.PluginError(
                "Plugin %s must be a subclass of "
                "starcluster.clustersetup.ClusterSetup" % setup_class)
        args, kwargs = utils.get_arg_spec(klass.__init__, debug=debug)
        config_args = []
        missing_args = []
        for arg in args:
            if arg in plugin:
                config_args.append(plugin.get(arg))
            else:
                missing_args.append(arg)
        if debug:
            log.debug("config_args = %s" % config_args)
        if missing_args:
            raise exception.PluginError(
                "Not enough settings provided for plugin %s (missing: %s)"
                % (plugin_name, ', '.join(missing_args)))
        config_kwargs = {}
        for arg in kwargs:
            if arg in plugin:
                config_kwargs[arg] = plugin.get(arg)
        if debug:
            log.debug("config_kwargs = %s" % config_kwargs)
        try:
            plug_obj = klass(*config_args, **config_kwargs)
        except Exception as exc:
            log.error("Error occured:", exc_info=True)
            raise exception.PluginLoadError(
                "Failed to load plugin %s with "
                "the following error: %s - %s" %
                (setup_class, exc.__class__.__name__, exc.message))
        if not hasattr(plug_obj, '__name__'):
            setattr(plug_obj, '__name__', plugin_name)
        plugs.append(plug_obj)
    return plugs

########NEW FILE########
__FILENAME__ = exception
# Copyright 2009-2014 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

"""
StarCluster Exception Classes
"""

import os

from starcluster import static
from starcluster.logger import log
from starcluster.templates import config, user_msgs


class BaseException(Exception):
    def __init__(self, *args):
        self.args = args
        self.msg = args[0]

    def __str__(self):
        return self.msg

    def explain(self):
        return "%s: %s" % (self.__class__.__name__, self.msg)


class CommandNotFound(BaseException):
    """Raised when command is not found on the system's PATH """
    def __init__(self, cmd):
        self.msg = "command not found: '%s'" % cmd


class RemoteCommandNotFound(CommandNotFound):
    """Raised when command is not found on a *remote* system's PATH """
    def __init__(self, cmd):
        self.msg = "command not found on remote system: '%s'" % cmd


class SSHError(BaseException):
    """Base class for all SSH related errors"""


class SSHConnectionError(SSHError):
    """Raised when ssh fails to to connect to a host (socket error)"""
    def __init__(self, host, port):
        self.msg = "failed to connect to host %s on port %s" % (host, port)


class SSHAuthException(SSHError):
    """Raised when an ssh connection fails to authenticate"""
    def __init__(self, user, host):
        self.msg = "failed to authenticate to host %s as user %s" % (host,
                                                                     user)


class SSHNoCredentialsError(SSHError):
    def __init__(self):
        self.msg = "No password or key specified"


class RemoteCommandFailed(SSHError):
    def __init__(self, msg, command, exit_status, output):
        self.msg = msg
        self.command = command
        self.exit_status = exit_status
        self.output = output


class SSHAccessDeniedViaAuthKeys(BaseException):
    """
    Raised when SSH access for a given user has been restricted via
    authorized_keys (common approach on UEC AMIs to allow root SSH access to be
    'toggled' via cloud-init)
    """
    def __init__(self, user):
        self.msg = user_msgs.authkeys_access_denied % dict(user=user)


class SCPException(BaseException):
    """SCP exception class"""
    pass


class AWSError(BaseException):
    """Base exception for all AWS related errors"""


class RegionDoesNotExist(AWSError):
    def __init__(self, region_name):
        self.msg = "region %s does not exist" % region_name


class AMIDoesNotExist(AWSError):
    def __init__(self, image_id):
        self.msg = "AMI %s does not exist" % image_id


class InstanceDoesNotExist(AWSError):
    def __init__(self, instance_id, label='instance'):
        self.msg = "%s '%s' does not exist" % (label, instance_id)


class InstanceNotRunning(AWSError):
    def __init__(self, instance_id, state, label='instance'):
        self.msg = "%s %s is not running (%s)" % (label, instance_id, state)


class SubnetDoesNotExist(AWSError):
    def __init__(self, subnet_id):
        self.msg = "subnet does not exist: %s" % subnet_id


class SecurityGroupDoesNotExist(AWSError):
    def __init__(self, sg_name):
        self.msg = "security group %s does not exist" % sg_name


class PlacementGroupDoesNotExist(AWSError):
    def __init__(self, pg_name):
        self.msg = "placement group %s does not exist" % pg_name


class KeyPairAlreadyExists(AWSError):
    def __init__(self, keyname):
        self.msg = "keypair %s already exists" % keyname


class KeyPairDoesNotExist(AWSError):
    def __init__(self, keyname):
        self.msg = "keypair %s does not exist" % keyname


class ZoneDoesNotExist(AWSError):
    def __init__(self, zone, region):
        self.msg = "zone %s does not exist in region %s" % (zone, region)


class VolumeDoesNotExist(AWSError):
    def __init__(self, vol_id):
        self.msg = "volume %s does not exist" % vol_id


class SnapshotDoesNotExist(AWSError):
    def __init__(self, snap_id):
        self.msg = "snapshot %s does not exist" % snap_id


class BucketAlreadyExists(AWSError):
    def __init__(self, bucket_name):
        self.msg = "bucket with name '%s' already exists on S3\n" % bucket_name
        self.msg += "(NOTE: S3's bucket namespace is shared by all AWS users)"


class BucketDoesNotExist(AWSError):
    def __init__(self, bucket_name):
        self.msg = "bucket '%s' does not exist" % bucket_name


class InvalidOperation(AWSError):
    pass


class InvalidBucketName(AWSError):
    def __init__(self, bucket_name):
        self.msg = "bucket name %s is not valid" % bucket_name


class InvalidImageName(AWSError):
    def __init__(self, image_name):
        self.msg = "image name %s is not valid" % image_name


class AWSUserIdRequired(AWSError):
    def __init__(self):
        self.msg = "No Amazon user id specified in config (AWS_USER_ID)"


class EC2CertRequired(AWSError):
    def __init__(self):
        self.msg = "No certificate file (pem) specified in config (EC2_CERT)"


class EC2PrivateKeyRequired(AWSError):
    def __init__(self):
        self.msg = "No private certificate file (pem) file specified in "
        self.msg += "config (EC2_PRIVATE_KEY)"


class EC2CertDoesNotExist(AWSError):
    def __init__(self, key):
        self.msg = "EC2 certificate file %s does not exist" % key


class EC2PrivateKeyDoesNotExist(AWSError):
    def __init__(self, key):
        self.msg = "EC2 private key file %s does not exist" % key


class SpotHistoryError(AWSError):
    def __init__(self, start, end):
        self.msg = "no spot price history for the dates specified: "
        self.msg += "%s - %s" % (start, end)


class PropagationException(AWSError):
    pass


class InvalidIsoDate(BaseException):
    def __init__(self, date):
        self.msg = "Invalid date specified: %s" % date


class InvalidHostname(BaseException):
    pass


class ConfigError(BaseException):
    """Base class for all config related errors"""


class ConfigSectionMissing(ConfigError):
    pass


class ConfigHasNoSections(ConfigError):
    def __init__(self, cfg_file):
        self.msg = "No valid sections defined in config file %s" % cfg_file


class PluginNotFound(ConfigError):
    def __init__(self, plugin):
        self.msg = 'Plugin "%s" not found in config' % plugin


class NoDefaultTemplateFound(ConfigError):
    def __init__(self, options=None):
        msg = "No default cluster template specified.\n\n"
        msg += "To set the default cluster template, set DEFAULT_TEMPLATE "
        msg += "in the [global] section of the config to the name of one of "
        msg += "your cluster templates"
        optlist = ', '.join(options)
        if options:
            msg += '\n\nCurrent Templates:\n\n' + optlist
        self.msg = msg
        self.options = options
        self.options_list = optlist


class ConfigNotFound(ConfigError):
    def __init__(self, *args):
        self.msg = args[0]
        self.cfg = args[1]
        self.template = config.copy_paste_template

    def create_config(self):
        cfg_parent_dir = os.path.dirname(self.cfg)
        if not os.path.exists(cfg_parent_dir):
            os.makedirs(cfg_parent_dir)
        cfg_file = open(self.cfg, 'w')
        cfg_file.write(config.config_template)
        cfg_file.close()
        os.chmod(self.cfg, 0600)
        log.info("Config template written to %s" % self.cfg)
        log.info("Please customize the config template")

    def display_options(self):
        print 'Options:'
        print '--------'
        print '[1] Show the StarCluster config template'
        print '[2] Write config template to %s' % self.cfg
        print '[q] Quit'
        resp = raw_input('\nPlease enter your selection: ')
        if resp == '1':
            print self.template
        elif resp == '2':
            print
            self.create_config()


class KeyNotFound(ConfigError):
    def __init__(self, keyname):
        self.msg = "key %s not found in config" % keyname


class InvalidDevice(BaseException):
    def __init__(self, device):
        self.msg = "invalid device specified: %s" % device


class InvalidPartition(BaseException):
    def __init__(self, part):
        self.msg = "invalid partition specified: %s" % part


class PluginError(BaseException):
    """Base class for plugin errors"""


class PluginLoadError(PluginError):
    """Raised when an error is encountered while loading a plugin"""


class PluginSyntaxError(PluginError):
    """Raised when plugin contains syntax errors"""


class ValidationError(BaseException):
    """Base class for validation related errors"""


class ClusterReceiptError(BaseException):
    """Raised when creating/loading a cluster receipt fails"""


class ClusterValidationError(ValidationError):
    """Cluster validation related errors"""


class NoClusterNodesFound(ValidationError):
    """Raised if no cluster nodes are found"""
    def __init__(self, terminated=None):
        self.msg = "No active cluster nodes found!"
        if not terminated:
            return
        self.msg += "\n\nBelow is a list of terminated instances:\n"
        for tnode in terminated:
            id = tnode.id
            reason = 'N/A'
            if tnode.state_reason:
                reason = tnode.state_reason['message']
            state = tnode.state
            self.msg += "\n%s (%s) %s" % (id, state, reason)


class NoClusterSpotRequests(ValidationError):
    """Raised if no spot requests belonging to a cluster are found"""
    def __init__(self):
        self.msg = "No cluster spot requests found!"


class MasterDoesNotExist(ClusterValidationError):
    """Raised when no master node is available"""
    def __init__(self):
        self.msg = "No master node found!"


class IncompatibleSettings(ClusterValidationError):
    """Raised when two or more settings conflict with each other"""


class InvalidProtocol(ClusterValidationError):
    """Raised when user specifies an invalid IP protocol for permission"""
    def __init__(self, protocol):
        self.msg = "protocol %s is not a valid ip protocol. options: %s"
        self.msg %= (protocol, ', '.join(static.PROTOCOLS))


class InvalidPortRange(ClusterValidationError):
    """Raised when user specifies an invalid port range for permission"""
    def __init__(self, from_port, to_port, reason=None):
        self.msg = ''
        if reason:
            self.msg += "%s\n" % reason
        self.msg += "port range is invalid: from %s to %s" % (from_port,
                                                              to_port)


class InvalidCIDRSpecified(ClusterValidationError):
    """Raised when user specifies an invalid CIDR ip for permission"""
    def __init__(self, cidr):
        self.msg = "cidr_ip is invalid: %s" % cidr


class InvalidZone(ClusterValidationError):
    """
    Raised when a zone has been specified that does not match the common
    zone of the volumes being attached
    """
    def __init__(self, zone, common_vol_zone):
        cvz = common_vol_zone
        self.msg = ("availability_zone setting '%s' does not "
                    "match the common volume zone '%s'") % (zone, cvz)


class VolumesZoneError(ClusterValidationError):
    def __init__(self, volumes):
        vlist = ', '.join(volumes)
        self.msg = 'Volumes %s are not in the same availability zone' % vlist


class ClusterTemplateDoesNotExist(BaseException):
    """
    Exception raised when user requests a cluster template that does not exist
    """
    def __init__(self, cluster_name):
        self.msg = "cluster template %s does not exist" % cluster_name


class ClusterNotRunning(BaseException):
    """
    Exception raised when user requests a running cluster that does not exist
    """
    def __init__(self, cluster_name):
        self.msg = "cluster %s is not running" % cluster_name


class ClusterDoesNotExist(BaseException):
    """
    Exception raised when user requests a running cluster that does not exist
    """
    def __init__(self, cluster_name):
        self.msg = "cluster '%s' does not exist" % cluster_name


class ClusterExists(BaseException):
    def __init__(self, cluster_name, is_ebs=False, stopped_ebs=False):
        ctx = dict(cluster_name=cluster_name)
        if stopped_ebs:
            self.msg = user_msgs.stopped_ebs_cluster % ctx
        elif is_ebs:
            self.msg = user_msgs.active_ebs_cluster % ctx
        else:
            self.msg = user_msgs.cluster_exists % ctx


class CancelledStartRequest(BaseException):
    def __init__(self, tag):
        self.msg = "Request to start cluster '%s' was cancelled!!!" % tag
        self.msg += "\n\nPlease be aware that instances may still be running."
        self.msg += "\nYou can check this from the output of:"
        self.msg += "\n\n   $ starcluster listclusters"
        self.msg += "\n\nIf you wish to destroy these instances please run:"
        self.msg += "\n\n   $ starcluster terminate %s" % tag
        self.msg += "\n\nYou can then use:\n\n   $ starcluster listclusters"
        self.msg += "\n\nto verify that the cluster has been terminated."
        self.msg += "\n\nIf you would like to re-use these instances, rerun"
        self.msg += "\nthe same start command with the -x (--no-create) option"


class CancelledCreateVolume(BaseException):
    def __init__(self):
        self.msg = "Request to create a new volume was cancelled!!!"
        self.msg += "\n\nPlease be aware that volume host instances"
        self.msg += " may still be running. "
        self.msg += "\n\nTo destroy these instances:"
        self.msg += "\n\n   $ starcluster terminate %s"
        self.msg += "\n\nYou can then use\n\n   $ starcluster listinstances"
        self.msg += "\n\nto verify that the volume hosts have been terminated."
        self.msg %= static.VOLUME_GROUP_NAME


class CancelledCreateImage(BaseException):
    def __init__(self, bucket, image_name):
        self.msg = "Request to create an S3 AMI was cancelled"
        self.msg += "\n\nDepending on how far along the process was before it "
        self.msg += "was cancelled, \nsome intermediate files might still be "
        self.msg += "around in /mnt on the instance."
        self.msg += "\n\nAlso, some of these intermediate files might "
        self.msg += "have been uploaded to \nS3 in the '%(bucket)s' bucket "
        self.msg += "you specified. You can check this using:"
        self.msg += "\n\n   $ starcluster showbucket %(bucket)s\n\n"
        self.msg += "Look for files like: "
        self.msg += "'%(iname)s.manifest.xml' or '%(iname)s.part.*'"
        self.msg += "\nRe-executing the same s3image command "
        self.msg += "should clean up these \nintermediate files and "
        self.msg += "also automatically override any\npartially uploaded "
        self.msg += "files in S3."
        self.msg = self.msg % {'bucket': bucket, 'iname': image_name}


CancelledS3ImageCreation = CancelledCreateImage


class CancelledEBSImageCreation(BaseException):
    def __init__(self, is_ebs_backed, image_name):
        self.msg = "Request to create EBS image %s was cancelled" % image_name
        if is_ebs_backed:
            self.msg += "\n\nDepending on how far along the process was "
            self.msg += "before it was cancelled, \na snapshot of the image "
            self.msg += "host's root volume may have been created.\nPlease "
            self.msg += "inspect the output of:\n\n"
            self.msg += "   $ starcluster listsnapshots\n\n"
            self.msg += "and clean up any unwanted snapshots"
        else:
            self.msg += "\n\nDepending on how far along the process was "
            self.msg += "before it was cancelled, \na new volume and a "
            self.msg += "snapshot of that new volume may have been created.\n"
            self.msg += "Please inspect the output of:\n\n"
            self.msg += "   $ starcluster listvolumes\n\n"
            self.msg += "   and\n\n"
            self.msg += "   $ starcluster listsnapshots\n\n"
            self.msg += "and clean up any unwanted volumes or snapshots"


class ExperimentalFeature(BaseException):
    def __init__(self, feature_name):
        self.msg = "%s is an experimental feature for this " % feature_name
        self.msg += "release. If you wish to test this feature, please set "
        self.msg += "ENABLE_EXPERIMENTAL=True in the [global] section of the"
        self.msg += " config. \n\nYou've officially been warned :D"


class ThreadPoolException(BaseException):
    def __init__(self, msg, exceptions):
        self.msg = msg
        self.exceptions = exceptions

    def print_excs(self):
        print self.format_excs()

    def format_excs(self):
        excs = []
        for exception in self.exceptions:
            e, tb_msg, jobid = exception
            excs.append('error occurred in job (id=%s): %s' % (jobid, str(e)))
            excs.append(tb_msg)
        return '\n'.join(excs)


class IncompatibleCluster(BaseException):
    default_msg = """\
INCOMPATIBLE CLUSTER: %(tag)s

The cluster '%(tag)s' is not compatible with StarCluster %(version)s. \
Possible reasons are:

1. The '%(group)s' group was created using an incompatible version of \
StarCluster (stable or development).

2. The '%(group)s' group was manually created outside of StarCluster.

3. One of the nodes belonging to '%(group)s' was manually created outside of \
StarCluster.

4. StarCluster was interrupted very early on when first creating the \
cluster's security group.

In any case '%(tag)s' and its nodes cannot be used with this version of \
StarCluster (%(version)s).

The cluster '%(tag)s' currently has %(num_nodes)d active nodes.

Please terminate the cluster using:

    $ starcluster terminate --force %(tag)s
"""

    def __init__(self, group):
        tag = group.name.replace(static.SECURITY_GROUP_PREFIX, '')
        states = ['pending', 'running', 'stopping', 'stopped']
        insts = group.connection.get_all_instances(
            filters={'instance-state-name': states,
                     'instance.group-name': group.name})
        ctx = dict(group=group.name, tag=tag, num_nodes=len(insts),
                   version=static.VERSION)
        self.msg = self.default_msg % ctx

########NEW FILE########
__FILENAME__ = image
# Copyright 2009-2014 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

import os
import time
import string

from starcluster import utils
from starcluster import sshutils
from starcluster import exception
from starcluster.spinner import Spinner
from starcluster.utils import print_timing
from starcluster.logger import log


class ImageCreator(object):
    """
    Base class for S3/EBS Image Creators. Handles fetching the host and setting
    up a connection object as well as setting common attributes (description,
    kernel_id, ramdisk_id)

    easy_ec2 must be an awsutils.EasyEC2 object

    instance_id is the id of the instance to be imaged

    key_location must point to the private key file corresponding to the
    keypair used to launch instance_id
    """
    def __init__(self, easy_ec2, instance_id, key_location, description=None,
                 kernel_id=None, ramdisk_id=None):
        self.ec2 = easy_ec2
        self.host = self.ec2.get_instance(instance_id)
        if self.host.state != 'running':
            raise exception.InstanceNotRunning(
                self.host.id, self.host.state,
                self.host.dns_name or self.host.private_ip_address)
        self.host_ssh = sshutils.SSHClient(
            self.host.dns_name or self.host.private_ip_address,
            username='root', private_key=key_location)
        self.description = description
        self.kernel_id = kernel_id or self.host.kernel
        self.ramdisk_id = ramdisk_id or self.host.ramdisk

    def clean_private_data(self):
        log.info('Removing private data...')
        conn = self.host_ssh
        conn.execute('find /home -maxdepth 1 -type d -exec rm -rf {}/.ssh \;')
        log.info("Cleaning up SSH host keys")
        conn.execute('rm -f /etc/ssh/ssh_host*key*')
        log.info("Cleaning up /var/log")
        conn.execute('rm -f /var/log/secure')
        conn.execute('rm -f /var/log/lastlog')
        conn.execute('rm -rf /var/log/*.gz')
        log.info("Cleaning out /root")
        conn.execute('rm -rf /root/*')
        conn.execute('rm -f /root/.bash_history')
        conn.execute('rm -rf /root/*.hist*')
        log.info("Cleaning up /tmp")
        conn.execute('rm -rf /tmp/*')


class S3ImageCreator(ImageCreator):
    """
    Class for creating a new instance-store AMI from a running instance
    """
    def __init__(self, easy_ec2, instance_id, key_location, aws_user_id,
                 ec2_cert, ec2_private_key, bucket, image_name='image',
                 description=None, kernel_id=None, ramdisk_id=None,
                 remove_image_files=False, **kwargs):
        super(S3ImageCreator, self).__init__(easy_ec2, instance_id,
                                             key_location, description,
                                             kernel_id, ramdisk_id)
        self.userid = aws_user_id
        self.cert = ec2_cert
        self.private_key = ec2_private_key
        self.bucket = bucket
        self.prefix = image_name
        self.description = description
        self.remove_image_files = remove_image_files
        for name in self.bucket.split("/"):
            if not utils.is_valid_bucket_name(name):
                raise exception.InvalidBucketName(self.bucket)
        if not utils.is_valid_image_name(self.prefix):
            raise exception.InvalidImageName(self.prefix)
        if not self.cert:
            try:
                self.cert = os.environ['EC2_CERT']
            except KeyError:
                raise exception.EC2CertRequired()
        if not self.private_key:
            try:
                self.private_key = os.environ['EC2_PRIVATE_KEY']
            except KeyError:
                raise exception.EC2PrivateKeyRequired()
        if not self.userid:
            raise exception.AWSUserIdRequired()
        if not os.path.exists(self.cert):
            raise exception.EC2CertDoesNotExist(self.cert)
        if not os.path.exists(self.private_key):
            raise exception.EC2PrivateKeyDoesNotExist(self.private_key)
        self.config_dict = {
            'access_key': self.ec2.aws_access_key_id,
            'secret_key': self.ec2.aws_secret_access_key,
            'private_key': os.path.split(self.private_key)[-1],
            'userid': self.userid,
            'cert': os.path.split(self.cert)[-1],
            'bucket': self.bucket,
            'prefix': self.prefix,
            'arch': self.host.architecture,
            'bmap': self._instance_store_bmap_str()
        }

    def __repr__(self):
        return "<S3ImageCreator: %s>" % self.host.id

    @print_timing
    def create_image(self):
        log.info("Checking for EC2 API tools...")
        self.host_ssh.check_required(['ec2-upload-bundle', 'ec2-bundle-vol'])
        self.ec2.s3.get_or_create_bucket(self.bucket)
        self._remove_image_files()
        self._bundle_image()
        self._upload_image()
        ami_id = self._register_image()
        if self.remove_image_files:
            self._remove_image_files()
        return ami_id

    def _remove_image_files(self):
        conn = self.host_ssh
        conn.execute('umount /mnt/img-mnt', ignore_exit_status=True)
        conn.execute('rm -rf /mnt/img-mnt')
        conn.execute('rm -rf /mnt/%(prefix)s*' % self.config_dict)

    def _transfer_pem_files(self):
        """copy pem files to /mnt on image host"""
        conn = self.host_ssh
        pkey_dest = "/mnt/" + os.path.basename(self.private_key)
        cert_dest = "/mnt/" + os.path.basename(self.cert)
        conn.put(self.private_key, pkey_dest)
        conn.put(self.cert, cert_dest)

    def _instance_store_bmap_str(self):
        bmap = self.ec2.create_block_device_map(add_ephemeral_drives=True,
                                                instance_store=True)
        bmaps = ','.join(["%s=%s" % (t.ephemeral_name, d)
                          for d, t in bmap.items()])
        return ','.join(['ami=sda1', bmaps])

    @print_timing
    def _bundle_image(self):
        # run script to prepare the host
        conn = self.host_ssh
        config_dict = self.config_dict
        self._transfer_pem_files()
        self.clean_private_data()
        log.info('Creating the bundled image: (please be patient)')
        conn.execute('ec2-bundle-vol -d /mnt -k /mnt/%(private_key)s '
                     '-c /mnt/%(cert)s -p %(prefix)s -u %(userid)s '
                     '-r %(arch)s -e /root/.ssh -B %(bmap)s' % config_dict,
                     silent=False)
        self._cleanup_pem_files()

    @print_timing
    def _upload_image(self):
        log.info('Uploading bundled image: (please be patient)')
        conn = self.host_ssh
        config_dict = self.config_dict
        conn.execute('ec2-upload-bundle -b %(bucket)s '
                     '-m /mnt/%(prefix)s.manifest.xml -a %(access_key)s '
                     '-s %(secret_key)s' % config_dict, silent=False)

    def _cleanup(self):
        self._cleanup_pem_files()
        conn = self.host_ssh
        conn.execute('rm -f ~/.bash_history', silent=False)

    def _cleanup_pem_files(self):
        log.info('Cleaning up...')
        # delete keys and remove bash history
        conn = self.host_ssh
        conn.execute('rm -f /mnt/*.pem /mnt/*.pem', silent=False)

    def _register_image(self):
        # register image in s3 with ec2
        conn = self.ec2
        config_dict = self.config_dict
        return conn.register_image(
            self.prefix,
            description=self.description,
            image_location="%(bucket)s/%(prefix)s.manifest.xml" % config_dict,
            kernel_id=self.kernel_id,
            ramdisk_id=self.ramdisk_id,
            architecture=config_dict.get('arch'),
        )


class EBSImageCreator(ImageCreator):
    """
    Creates a new EBS image from a running instance

    If the instance is an instance-store image, then this class will create a
    new volume, attach it to the instance, sync the root filesystem to the
    volume, detach the volume, snapshot it, and then create a new AMI from the
    snapshot

    If the instance is EBS-backed, this class simply calls ec2.create_image
    which tells Amazon to create a new image in a single API call.
    """

    def __init__(self, easy_ec2, instance_id, key_location, name,
                 description=None, snapshot_description=None,
                 kernel_id=None, ramdisk_id=None, **kwargs):
        super(EBSImageCreator, self).__init__(easy_ec2, instance_id,
                                              key_location, description,
                                              kernel_id, ramdisk_id)
        self.name = name
        self.description = description
        self.snapshot_description = snapshot_description or description
        self._snap = None
        self._vol = None

    @print_timing
    def create_image(self, size=15):
        try:
            self.clean_private_data()
            if self.host.root_device_type == "ebs":
                return self._create_image_from_ebs(size)
            return self._create_image_from_instance_store(size)
        except:
            log.error("Error occurred while creating image")
            if self._snap:
                log.error("Removing generated snapshot '%s'" % self._snap)
                self._snap.delete()
            if self._vol:
                log.error("Removing generated volume '%s'" % self._vol.id)
                self._vol.detach(force=True)
                self._vol.delete()
            raise

    def _create_image_from_ebs(self, size=15):
        log.info("Creating new EBS AMI...")
        imgid = self.ec2.create_image(self.host.id, self.name,
                                      self.description)
        img = self.ec2.get_image(imgid)
        log.info("New EBS AMI created: %s" % imgid)
        root_dev = self.host.root_device_name
        if root_dev in self.host.block_device_mapping:
            log.info("Fetching block device mapping for %s" % imgid,
                     extra=dict(__nonewline__=True))
            s = Spinner()
            try:
                s.start()
                while root_dev not in img.block_device_mapping:
                    img = self.ec2.get_image(imgid)
                    time.sleep(5)
            finally:
                s.stop()
            snapshot_id = img.block_device_mapping[root_dev].snapshot_id
            snap = self.ec2.get_snapshot(snapshot_id)
            self.ec2.wait_for_snapshot(snap)
        else:
            log.warn("Unable to find root device - cant wait for snapshot")
        log.info("Waiting for %s to become available..." % imgid,
                 extra=dict(__nonewline__=True))
        s = Spinner()
        try:
            s.start()
            while img.state == "pending":
                time.sleep(15)
                if img.update() == "failed":
                    raise exception.AWSError(
                        "EBS image creation failed for %s" % imgid)
        finally:
            s.stop()
        return imgid

    def _create_image_from_instance_store(self, size=15):
        host = self.host
        host_ssh = self.host_ssh
        log.info("Creating new EBS-backed image from instance-store instance")
        log.info("Creating new root volume...")
        vol = self._vol = self.ec2.create_volume(size, host.placement)
        log.info("Created new volume: %s" % vol.id)
        while vol.update() != 'available':
            time.sleep(5)
        dev = None
        for i in string.ascii_lowercase[::-1]:
            dev = '/dev/sd%s' % i
            if dev not in host.block_device_mapping:
                break
        log.info("Attaching volume %s to instance %s on %s" %
                 (vol.id, host.id, dev))
        vol.attach(host.id, dev)
        while vol.update() != 'in-use':
            time.sleep(5)
        while not host_ssh.path_exists(dev):
            time.sleep(5)
        log.info("Formatting %s..." % vol.id)
        host_ssh.execute('mkfs.ext3 -F %s' % dev, silent=False)
        log.info("Setting filesystem label on %s" % dev)
        host_ssh.execute('e2label %s /' % dev)
        mount_point = '/ebs'
        while host_ssh.path_exists(mount_point):
            mount_point += '1'
        host_ssh.mkdir(mount_point)
        log.info("Mounting %s on %s" % (dev, mount_point))
        host_ssh.execute('mount %s %s' % (dev, mount_point))
        log.info("Configuring /etc/fstab")
        host_ssh.remove_lines_from_file('/etc/fstab', '/mnt')
        fstab = host_ssh.remote_file('/etc/fstab', 'a')
        fstab.write('/dev/sdb1 /mnt auto defaults,nobootwait 0 0\n')
        fstab.close()
        log.info("Syncing root filesystem to new volume (%s)" % vol.id)
        host_ssh.execute(
            'rsync -aqx --exclude %(mpt)s --exclude /root/.ssh / %(mpt)s' %
            {'mpt': mount_point}, silent=False)
        log.info("Unmounting %s from %s" % (dev, mount_point))
        host_ssh.execute('umount %s' % mount_point)
        log.info("Detaching volume %s from %s" % (dev, mount_point))
        vol.detach()
        while vol.update() != 'available':
            time.sleep(5)
        sdesc = self.snapshot_description
        snap = self._snap = self.ec2.create_snapshot(vol,
                                                     description=sdesc,
                                                     wait_for_snapshot=True)
        log.info("New snapshot created: %s" % snap.id)
        log.info("Removing generated volume %s" % vol.id)
        vol.delete()
        log.info("Creating root block device map using snapshot %s" % snap.id)
        bmap = self.ec2.create_block_device_map(root_snapshot_id=snap.id,
                                                instance_store=True,
                                                num_ephemeral_drives=1,
                                                add_ephemeral_drives=True)
        log.info("Registering new image...")
        img_id = self.ec2.register_image(name=self.name,
                                         description=self.description,
                                         architecture=host.architecture,
                                         kernel_id=self.kernel_id,
                                         ramdisk_id=self.ramdisk_id,
                                         root_device_name='/dev/sda1',
                                         block_device_map=bmap)
        return img_id


# for backwards compatibility
EC2ImageCreator = S3ImageCreator

########NEW FILE########
__FILENAME__ = logger
# Copyright 2009-2014 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

"""
StarCluster logging module
"""
import os
import sys
import glob
import types
import logging
import logging.handlers
import textwrap
import fileinput

from starcluster import static

INFO = logging.INFO
DEBUG = logging.DEBUG
WARN = logging.WARN
ERROR = logging.ERROR
CRITICAL = logging.CRITICAL
FATAL = logging.FATAL
RAW = "raw"

RAW_FORMAT = "%(message)s"
INFO_FORMAT = " ".join([">>>", RAW_FORMAT])
DEFAULT_CONSOLE_FORMAT = " - ".join(["%(levelname)s", RAW_FORMAT])
ERROR_CONSOLE_FORMAT = " ".join(["!!!", DEFAULT_CONSOLE_FORMAT])
WARN_CONSOLE_FORMAT = " ".join(["***", DEFAULT_CONSOLE_FORMAT])
FILE_INFO_FORMAT = " - ".join(["%(filename)s:%(lineno)d",
                               DEFAULT_CONSOLE_FORMAT])
DEBUG_FORMAT = " ".join(["%(asctime)s", FILE_INFO_FORMAT])
DEBUG_FORMAT_PID = " ".join(["%(asctime)s", "PID: %s" % str(static.PID),
                             FILE_INFO_FORMAT])


class ConsoleLogger(logging.StreamHandler):

    formatters = {
        INFO: logging.Formatter(INFO_FORMAT),
        DEBUG: logging.Formatter(DEBUG_FORMAT),
        WARN: logging.Formatter(WARN_CONSOLE_FORMAT),
        ERROR: logging.Formatter(ERROR_CONSOLE_FORMAT),
        CRITICAL: logging.Formatter(ERROR_CONSOLE_FORMAT),
        FATAL: logging.Formatter(ERROR_CONSOLE_FORMAT),
        RAW: logging.Formatter(RAW_FORMAT),
    }

    def __init__(self, stream=sys.stdout, error_stream=sys.stderr):
        self.error_stream = error_stream or sys.stderr
        logging.StreamHandler.__init__(self, stream or sys.stdout)

    def format(self, record):
        if hasattr(record, '__raw__'):
            result = self.formatters[RAW].format(record)
        else:
            result = self.formatters[record.levelno].format(record)
        return result

    def _wrap(self, msg):
        tw = textwrap.TextWrapper(width=60, replace_whitespace=False)
        if hasattr(tw, 'break_on_hyphens'):
            tw.break_on_hyphens = False
        if hasattr(tw, 'drop_whitespace'):
            tw.drop_whitespace = True
        return tw.wrap(msg) or ['']

    def _emit_textwrap(self, record):
        lines = []
        for line in record.msg.splitlines():
            lines.extend(self._wrap(line))
        if hasattr(record, '__nosplitlines__'):
            lines = ['\n'.join(lines)]
        for line in lines:
            record.msg = line
            self._emit(record)

    def _emit(self, record):
        msg = self.format(record)
        fs = "%s\n"
        if hasattr(record, '__nonewline__'):
            msg = msg.rstrip()
            fs = "%s"
        stream = self.stream
        if record.levelno in [ERROR, CRITICAL, FATAL]:
            stream = self.error_stream
        if not hasattr(types, "UnicodeType"):
            # if no unicode support...
            stream.write(fs % msg)
        else:
            try:
                stream.write(fs % msg)
            except UnicodeError:
                stream.write(fs % msg.encode("UTF-8"))
        self.flush()

    def emit(self, record):
        try:
            if hasattr(record, '__textwrap__'):
                self._emit_textwrap(record)
            else:
                self._emit(record)
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)


class NullHandler(logging.Handler):
    def emit(self, record):
        pass


def get_starcluster_logger():
    log = logging.getLogger('starcluster')
    log.addHandler(NullHandler())
    return log


log = get_starcluster_logger()
console = ConsoleLogger()


def configure_sc_logging(use_syslog=False):
    """
    Configure logging for StarCluster *application* code

    By default StarCluster's logger has no formatters and a NullHandler so that
    other developers using StarCluster as a library can configure logging as
    they see fit. This method is used in StarCluster's application code (i.e.
    the 'starcluster' command) to toggle StarCluster's application specific
    formatters/handlers

    use_syslog - enable logging all messages to syslog. currently only works if
    /dev/log exists on the system (standard for most Linux distros)
    """
    log.setLevel(logging.DEBUG)
    formatter = logging.Formatter(DEBUG_FORMAT_PID)
    static.create_sc_config_dirs()
    rfh = logging.handlers.RotatingFileHandler(static.DEBUG_FILE,
                                               maxBytes=1048576,
                                               backupCount=2)
    rfh.setLevel(logging.DEBUG)
    rfh.setFormatter(formatter)
    log.addHandler(rfh)
    console.setLevel(logging.INFO)
    log.addHandler(console)
    syslog_device = '/dev/log'
    if use_syslog and os.path.exists(syslog_device):
        log.debug("Logging to %s" % syslog_device)
        syslog_handler = logging.handlers.SysLogHandler(address=syslog_device)
        syslog_handler.setFormatter(formatter)
        syslog_handler.setLevel(logging.DEBUG)
        log.addHandler(syslog_handler)


def configure_paramiko_logging():
    """
    Configure ssh to log to a file for debug
    """
    l = logging.getLogger("paramiko")
    l.setLevel(logging.DEBUG)
    static.create_sc_config_dirs()
    lh = logging.handlers.RotatingFileHandler(static.SSH_DEBUG_FILE,
                                              maxBytes=1048576,
                                              backupCount=2)
    lh.setLevel(logging.DEBUG)
    format = (('PID: %s ' % str(static.PID)) +
              '%(levelname)-.3s [%(asctime)s.%(msecs)03d] '
              'thr=%(_threadid)-3d %(name)s: %(message)s')
    date_format = '%Y%m%d-%H:%M:%S'
    lh.setFormatter(logging.Formatter(format, date_format))
    l.addHandler(lh)


def configure_boto_logging():
    """
    Configure boto to log to a file for debug
    """
    l = logging.getLogger("boto")
    l.setLevel(logging.DEBUG)
    static.create_sc_config_dirs()
    lh = logging.handlers.RotatingFileHandler(static.AWS_DEBUG_FILE,
                                              maxBytes=1048576,
                                              backupCount=2)
    lh.setLevel(logging.DEBUG)
    format = (('PID: %s ' % str(static.PID)) +
              '%(levelname)-.3s [%(asctime)s.%(msecs)03d] '
              '%(name)s: %(message)s')
    date_format = '%Y%m%d-%H:%M:%S'
    lh.setFormatter(logging.Formatter(format, date_format))
    l.addHandler(lh)


def get_log_for_pid(pid):
    """
    Fetches the logs from the debug log file for a given StarCluster run by PID
    """
    found_pid = False
    pid_str = ' PID: %s ' % pid
    for line in fileinput.input(glob.glob(static.DEBUG_FILE + '*')):
        if pid_str in line:
            yield line
            found_pid = True
        elif found_pid and ' PID: ' not in line:
            yield line
        else:
            found_pid = False


def get_session_log():
    """
    Fetches the logs for the current active session from the debug log file.
    """
    return get_log_for_pid(static.PID)

########NEW FILE########
__FILENAME__ = managers
# Copyright 2009-2014 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.


class Manager(object):
    """
    Base class for all Manager classes in StarCluster
    """
    def __init__(self, cfg, ec2=None):
        self.cfg = cfg
        self.ec2 = ec2 or cfg.get_easy_ec2()

########NEW FILE########
__FILENAME__ = node
# Copyright 2009-2014 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

import re
import time
import stat
import base64
import posixpath
import subprocess

from starcluster import utils
from starcluster import static
from starcluster import sshutils
from starcluster import awsutils
from starcluster import managers
from starcluster import userdata
from starcluster import exception
from starcluster.logger import log


class NodeManager(managers.Manager):
    """
    Manager class for Node objects
    """
    def ssh_to_node(self, node_id, user='root', command=None,
                    forward_x11=False, forward_agent=False):
        node = self.get_node(node_id, user=user)
        return node.shell(user=user, command=command, forward_x11=forward_x11,
                          forward_agent=forward_agent)

    def get_node(self, node_id, user='root'):
        """Factory for Node class"""
        instances = self.ec2.get_all_instances()
        node = None
        for instance in instances:
            if instance.dns_name == node_id:
                node = instance
                break
            elif instance.id == node_id:
                node = instance
                break
        if not node:
            raise exception.InstanceDoesNotExist(node_id)
        key = self.cfg.get_key(node.key_name)
        node = Node(node, key.key_location, user=user)
        return node


class Node(object):
    """
    This class represents a single compute node in a StarCluster.

    It contains all useful metadata for the node such as the internal/external
    hostnames, ips, etc. as well as an ssh object for executing commands,
    creating/modifying files on the node.

    'instance' arg must be an instance of boto.ec2.instance.Instance

    'key_location' arg is a string that contains the full path to the
    private key corresponding to the keypair used to launch this node

    'alias' keyword arg optionally names the node. If no alias is provided,
    the alias is retrieved from the node's user_data based on the node's
    launch index

    'user' keyword optionally specifies user to ssh as (defaults to root)
    """
    def __init__(self, instance, key_location, alias=None, user='root'):
        self.instance = instance
        self.ec2 = awsutils.EasyEC2(instance.connection.aws_access_key_id,
                                    instance.connection.aws_secret_access_key,
                                    connection=instance.connection)
        self.key_location = key_location
        self.user = user
        self._alias = alias
        self._groups = None
        self._ssh = None
        self._num_procs = None
        self._memory = None
        self._user_data = None

    def __repr__(self):
        return '<Node: %s (%s)>' % (self.alias, self.id)

    def _get_user_data(self, tries=5):
        tries = range(tries)
        last_try = tries[-1]
        for i in tries:
            try:
                user_data = self.ec2.get_instance_user_data(self.id)
                return user_data
            except exception.InstanceDoesNotExist:
                if i == last_try:
                    log.debug("failed fetching user data")
                    raise
                log.debug("InvalidInstanceID.NotFound: "
                          "retrying fetching user data (tries: %s)" % (i + 1))
                time.sleep(5)

    @property
    def user_data(self):
        if not self._user_data:
            try:
                raw = self._get_user_data()
                self._user_data = userdata.unbundle_userdata(raw)
            except IOError, e:
                parent_cluster = self.parent_cluster
                if self.parent_cluster:
                    raise exception.IncompatibleCluster(parent_cluster)
                else:
                    raise exception.BaseException(
                        "Error occurred unbundling userdata: %s" % e)
        return self._user_data

    @property
    def alias(self):
        """
        Fetches the node's alias stored in a tag from either the instance
        or the instance's parent spot request. If no alias tag is found an
        exception is raised.
        """
        if not self._alias:
            alias = self.tags.get('alias')
            if not alias:
                aliasestxt = self.user_data.get(static.UD_ALIASES_FNAME, '')
                aliases = aliasestxt.splitlines()[2:]
                index = self.ami_launch_index
                try:
                    alias = aliases[index]
                except IndexError:
                    alias = None
                    log.debug("invalid aliases file in user_data:\n%s" %
                              aliasestxt)
                if not alias:
                    raise exception.BaseException(
                        "instance %s has no alias" % self.id)
                self.add_tag('alias', alias)
            if not self.tags.get('Name'):
                self.add_tag('Name', alias)
            self._alias = alias
        return self._alias

    def get_plugins(self):
        plugstxt = self.user_data.get(static.UD_PLUGINS_FNAME)
        payload = plugstxt.split('\n', 2)[2]
        plugins_metadata = utils.decode_uncompress_load(payload)
        plugs = []
        for klass, args, kwargs in plugins_metadata:
            mod_path, klass_name = klass.rsplit('.', 1)
            try:
                mod = __import__(mod_path, fromlist=[klass_name])
                plug = getattr(mod, klass_name)(*args, **kwargs)
            except SyntaxError, e:
                raise exception.PluginSyntaxError(
                    "Plugin %s (%s) contains a syntax error at line %s" %
                    (klass_name, e.filename, e.lineno))
            except ImportError, e:
                raise exception.PluginLoadError(
                    "Failed to import plugin %s: %s" %
                    (klass_name, e[0]))
            except Exception as exc:
                log.error("Error occured:", exc_info=True)
                raise exception.PluginLoadError(
                    "Failed to load plugin %s with "
                    "the following error: %s - %s" %
                    (klass_name, exc.__class__.__name__, exc.message))
            plugs.append(plug)
        return plugs

    def get_volumes(self):
        volstxt = self.user_data.get(static.UD_VOLUMES_FNAME)
        payload = volstxt.split('\n', 2)[2]
        return utils.decode_uncompress_load(payload)

    def _remove_all_tags(self):
        tags = self.tags.keys()[:]
        for t in tags:
            self.remove_tag(t)

    @property
    def tags(self):
        return self.instance.tags

    def add_tag(self, key, value=None):
        return self.instance.add_tag(key, value)

    def remove_tag(self, key, value=None):
        return self.instance.remove_tag(key, value)

    @property
    def groups(self):
        if not self._groups:
            groups = map(lambda x: x.name, self.instance.groups)
            self._groups = self.ec2.get_all_security_groups(groupnames=groups)
        return self._groups

    @property
    def cluster_groups(self):
        sg_prefix = static.SECURITY_GROUP_PREFIX
        return filter(lambda x: x.name.startswith(sg_prefix), self.groups)

    @property
    def parent_cluster(self):
        try:
            return self.cluster_groups[0]
        except IndexError:
            pass

    @property
    def num_processors(self):
        if not self._num_procs:
            self._num_procs = int(
                self.ssh.execute(
                    'cat /proc/cpuinfo | grep processor | wc -l')[0])
        return self._num_procs

    @property
    def memory(self):
        if not self._memory:
            self._memory = float(
                self.ssh.execute(
                    "free -m | grep -i mem | awk '{print $2}'")[0])
        return self._memory

    @property
    def ip_address(self):
        return self.instance.ip_address

    @property
    def public_dns_name(self):
        return self.instance.public_dns_name

    @property
    def private_ip_address(self):
        return self.instance.private_ip_address

    @property
    def private_dns_name(self):
        return self.instance.private_dns_name

    @property
    def private_dns_name_short(self):
        return self.instance.private_dns_name.split('.')[0]

    @property
    def id(self):
        return self.instance.id

    @property
    def block_device_mapping(self):
        return self.instance.block_device_mapping

    @property
    def dns_name(self):
        return self.instance.dns_name

    @property
    def state(self):
        return self.instance.state

    @property
    def launch_time(self):
        return self.instance.launch_time

    @property
    def local_launch_time(self):
        ltime = utils.iso_to_localtime_tuple(self.launch_time)
        return time.strftime("%Y-%m-%d %H:%M:%S", ltime.timetuple())

    @property
    def uptime(self):
        return utils.get_elapsed_time(self.launch_time)

    @property
    def ami_launch_index(self):
        try:
            return int(self.instance.ami_launch_index)
        except TypeError:
            log.error("instance %s (state: %s) has no ami_launch_index" %
                      (self.id, self.state))
            log.error("returning 0 as ami_launch_index...")
            return 0

    @property
    def key_name(self):
        return self.instance.key_name

    @property
    def arch(self):
        return self.instance.architecture

    @property
    def kernel(self):
        return self.instance.kernel

    @property
    def ramdisk(self):
        return self.instance.ramdisk

    @property
    def instance_type(self):
        return self.instance.instance_type

    @property
    def image_id(self):
        return self.instance.image_id

    @property
    def placement(self):
        return self.instance.placement

    @property
    def region(self):
        return self.instance.region

    @property
    def vpc_id(self):
        return self.instance.vpc_id

    @property
    def subnet_id(self):
        return self.instance.subnet_id

    @property
    def root_device_name(self):
        root_dev = self.instance.root_device_name
        bmap = self.block_device_mapping
        if bmap and root_dev not in bmap and self.is_ebs_backed():
            # Hack for misconfigured AMIs (e.g. CentOS 6.3 Marketplace) These
            # AMIs have root device name set to /dev/sda1 but no /dev/sda1 in
            # block device map - only /dev/sda. These AMIs somehow magically
            # work so check if /dev/sda exists and return that instead to
            # prevent detach_external_volumes() from trying to detach the root
            # volume on these AMIs.
            log.warn("Root device %s is not in the block device map" %
                     root_dev)
            log.warn("This means the AMI was registered with either "
                     "an incorrect root device name or an incorrect block "
                     "device mapping")
            sda, sda1 = '/dev/sda', '/dev/sda1'
            if root_dev == sda1:
                log.info("Searching for possible root device: %s" % sda)
                if sda in self.block_device_mapping:
                    log.warn("Found '%s' - assuming its the real root device" %
                             sda)
                    root_dev = sda
                else:
                    log.warn("Device %s isn't in the block device map either" %
                             sda)
        return root_dev

    @property
    def root_device_type(self):
        return self.instance.root_device_type

    def add_user_to_group(self, user, group):
        """
        Add user (if exists) to group (if exists)
        """
        if user not in self.get_user_map():
            raise exception.BaseException("user %s does not exist" % user)
        if group in self.get_group_map():
            self.ssh.execute('gpasswd -a %s %s' % (user, 'utmp'))
        else:
            raise exception.BaseException("group %s does not exist" % group)

    def get_group_map(self, key_by_gid=False):
        """
        Returns dictionary where keys are remote group names and values are
        grp.struct_grp objects from the standard grp module

        key_by_gid=True will use the integer gid as the returned dictionary's
        keys instead of the group's name
        """
        grp_file = self.ssh.remote_file('/etc/group', 'r')
        groups = [l.strip().split(':') for l in grp_file.readlines()]
        grp_file.close()
        grp_map = {}
        for group in groups:
            name, passwd, gid, mems = group
            gid = int(gid)
            mems = mems.split(',')
            key = name
            if key_by_gid:
                key = gid
            grp_map[key] = utils.struct_group([name, passwd, gid, mems])
        return grp_map

    def get_user_map(self, key_by_uid=False):
        """
        Returns dictionary where keys are remote usernames and values are
        pwd.struct_passwd objects from the standard pwd module

        key_by_uid=True will use the integer uid as the returned dictionary's
        keys instead of the user's login name
        """
        etc_passwd = self.ssh.remote_file('/etc/passwd', 'r')
        users = [l.strip().split(':') for l in etc_passwd.readlines()]
        etc_passwd.close()
        user_map = {}
        for user in users:
            name, passwd, uid, gid, gecos, home, shell = user
            uid = int(uid)
            gid = int(gid)
            key = name
            if key_by_uid:
                key = uid
            user_map[key] = utils.struct_passwd([name, passwd, uid, gid, gecos,
                                                 home, shell])
        return user_map

    def getgrgid(self, gid):
        """
        Remote version of the getgrgid method in the standard grp module

        returns a grp.struct_group
        """
        gmap = self.get_group_map(key_by_gid=True)
        return gmap.get(gid)

    def getgrnam(self, groupname):
        """
        Remote version of the getgrnam method in the standard grp module

        returns a grp.struct_group
        """
        gmap = self.get_group_map()
        return gmap.get(groupname)

    def getpwuid(self, uid):
        """
        Remote version of the getpwuid method in the standard pwd module

        returns a pwd.struct_passwd
        """
        umap = self.get_user_map(key_by_uid=True)
        return umap.get(uid)

    def getpwnam(self, username):
        """
        Remote version of the getpwnam method in the standard pwd module

        returns a pwd.struct_passwd
        """
        umap = self.get_user_map()
        return umap.get(username)

    def add_user(self, name, uid=None, gid=None, shell="bash"):
        """
        Add a user to the remote system.

        name - the username of the user being added
        uid - optional user id to use when creating new user
        gid - optional group id to use when creating new user
        shell - optional shell assign to new user (default: bash)
        """
        if gid:
            self.ssh.execute('groupadd -o -g %s %s' % (gid, name))
        user_add_cmd = 'useradd -o '
        if uid:
            user_add_cmd += '-u %s ' % uid
        if gid:
            user_add_cmd += '-g %s ' % gid
        if shell:
            user_add_cmd += '-s `which %s` ' % shell
        user_add_cmd += "-m %s" % name
        self.ssh.execute(user_add_cmd)

    def generate_key_for_user(self, username, ignore_existing=False,
                              auth_new_key=False, auth_conn_key=False):
        """
        Generates an id_rsa/id_rsa.pub keypair combo for a user on the remote
        machine.

        ignore_existing - if False, any existing key combos will be used rather
        than generating a new RSA key

        auth_new_key - if True, add the newly generated public key to the
        remote user's authorized_keys file

        auth_conn_key - if True, add the public key used to establish this ssh
        connection to the remote user's authorized_keys
        """
        user = self.getpwnam(username)
        home_folder = user.pw_dir
        ssh_folder = posixpath.join(home_folder, '.ssh')
        if not self.ssh.isdir(ssh_folder):
            self.ssh.mkdir(ssh_folder)
        self.ssh.chown(user.pw_uid, user.pw_gid, ssh_folder)
        private_key = posixpath.join(ssh_folder, 'id_rsa')
        public_key = private_key + '.pub'
        authorized_keys = posixpath.join(ssh_folder, 'authorized_keys')
        key_exists = self.ssh.isfile(private_key)
        if key_exists and not ignore_existing:
            log.debug("Using existing key: %s" % private_key)
            key = self.ssh.load_remote_rsa_key(private_key)
        else:
            key = sshutils.generate_rsa_key()
        pubkey_contents = sshutils.get_public_key(key)
        if not key_exists or ignore_existing:
            # copy public key to remote machine
            pub_key = self.ssh.remote_file(public_key, 'w')
            pub_key.write(pubkey_contents)
            pub_key.chown(user.pw_uid, user.pw_gid)
            pub_key.chmod(0400)
            pub_key.close()
            # copy private key to remote machine
            priv_key = self.ssh.remote_file(private_key, 'w')
            key.write_private_key(priv_key)
            priv_key.chown(user.pw_uid, user.pw_gid)
            priv_key.chmod(0400)
            priv_key.close()
        if not auth_new_key or not auth_conn_key:
            return key
        auth_keys_contents = ''
        if self.ssh.isfile(authorized_keys):
            auth_keys = self.ssh.remote_file(authorized_keys, 'r')
            auth_keys_contents = auth_keys.read()
            auth_keys.close()
        auth_keys = self.ssh.remote_file(authorized_keys, 'a')
        if auth_new_key:
            # add newly generated public key to user's authorized_keys
            if pubkey_contents not in auth_keys_contents:
                log.debug("adding auth_key_contents")
                auth_keys.write('%s\n' % pubkey_contents)
        if auth_conn_key and self.ssh._pkey:
            # add public key used to create the connection to user's
            # authorized_keys
            conn_key = self.ssh._pkey
            conn_pubkey_contents = sshutils.get_public_key(conn_key)
            if conn_pubkey_contents not in auth_keys_contents:
                log.debug("adding conn_pubkey_contents")
                auth_keys.write('%s\n' % conn_pubkey_contents)
        auth_keys.chown(user.pw_uid, user.pw_gid)
        auth_keys.chmod(0600)
        auth_keys.close()
        return key

    def add_to_known_hosts(self, username, nodes, add_self=True):
        """
        Populate user's known_hosts file with pub keys from hosts in nodes list

        username - name of the user to add to known hosts for
        nodes - the nodes to add to the user's known hosts file
        add_self - add this Node to known_hosts in addition to nodes
        """
        user = self.getpwnam(username)
        known_hosts_file = posixpath.join(user.pw_dir, '.ssh', 'known_hosts')
        khosts = []
        if add_self and self not in nodes:
            nodes.append(self)
        self.remove_from_known_hosts(username, nodes)
        for node in nodes:
            server_pkey = node.ssh.get_server_public_key()
            node_names = {}.fromkeys([node.alias, node.private_dns_name,
                                      node.private_dns_name_short],
                                     node.private_ip_address)
            node_names[node.public_dns_name] = node.ip_address
            for name, ip in node_names.items():
                name_ip = "%s,%s" % (name, ip)
                khosts.append(' '.join([name_ip, server_pkey.get_name(),
                                        base64.b64encode(str(server_pkey))]))
        khostsf = self.ssh.remote_file(known_hosts_file, 'a')
        khostsf.write('\n'.join(khosts) + '\n')
        khostsf.chown(user.pw_uid, user.pw_gid)
        khostsf.close()

    def remove_from_known_hosts(self, username, nodes):
        """
        Remove all network names for nodes from username's known_hosts file
        on this Node
        """
        user = self.getpwnam(username)
        known_hosts_file = posixpath.join(user.pw_dir, '.ssh', 'known_hosts')
        hostnames = []
        for node in nodes:
            hostnames += [node.alias, node.private_dns_name,
                          node.private_dns_name_short, node.public_dns_name]
        if self.ssh.isfile(known_hosts_file):
            regex = '|'.join(hostnames)
            self.ssh.remove_lines_from_file(known_hosts_file, regex)

    def enable_passwordless_ssh(self, username, nodes):
        """
        Configure passwordless ssh for user between this Node and nodes
        """
        user = self.getpwnam(username)
        ssh_folder = posixpath.join(user.pw_dir, '.ssh')
        priv_key_file = posixpath.join(ssh_folder, 'id_rsa')
        pub_key_file = priv_key_file + '.pub'
        known_hosts_file = posixpath.join(ssh_folder, 'known_hosts')
        auth_key_file = posixpath.join(ssh_folder, 'authorized_keys')
        self.add_to_known_hosts(username, nodes)
        # exclude this node from copying
        nodes = filter(lambda n: n.id != self.id, nodes)
        # copy private key and public key to node
        self.copy_remote_file_to_nodes(priv_key_file, nodes)
        self.copy_remote_file_to_nodes(pub_key_file, nodes)
        # copy authorized_keys and known_hosts to node
        self.copy_remote_file_to_nodes(auth_key_file, nodes)
        self.copy_remote_file_to_nodes(known_hosts_file, nodes)

    def copy_remote_file_to_node(self, remote_file, node, dest=None):
        return self.copy_remote_file_to_nodes(remote_file, [node], dest=dest)

    def copy_remote_file_to_nodes(self, remote_file, nodes, dest=None):
        """
        Copies a remote file from this Node instance to another Node instance
        without passwordless ssh between the two.

        dest - path to store the data in on the node (defaults to remote_file)
        """
        if not dest:
            dest = remote_file
        rf = self.ssh.remote_file(remote_file, 'r')
        contents = rf.read()
        sts = rf.stat()
        mode = stat.S_IMODE(sts.st_mode)
        uid = sts.st_uid
        gid = sts.st_gid
        rf.close()
        for node in nodes:
            if self.id == node.id and remote_file == dest:
                log.warn("src and destination are the same: %s, skipping" %
                         remote_file)
                continue
            nrf = node.ssh.remote_file(dest, 'w')
            nrf.write(contents)
            nrf.chown(uid, gid)
            nrf.chmod(mode)
            nrf.close()

    def remove_user(self, name):
        """
        Remove a user from the remote system
        """
        self.ssh.execute('userdel %s' % name)
        self.ssh.execute('groupdel %s' % name)

    def export_fs_to_nodes(self, nodes, export_paths):
        """
        Export each path in export_paths to each node in nodes via NFS

        nodes - list of nodes to export each path to
        export_paths - list of paths on this remote host to export to each node

        Example:
        # export /home and /opt/sge6 to each node in nodes
        $ node.start_nfs_server()
        $ node.export_fs_to_nodes(nodes=[node1,node2],
                                  export_paths=['/home', '/opt/sge6'])
        """
        log.debug("Cleaning up potentially stale NFS entries")
        self.stop_exporting_fs_to_nodes(nodes, paths=export_paths)
        log.info("Configuring NFS exports path(s):\n%s" %
                 ' '.join(export_paths))
        nfs_export_settings = "(async,no_root_squash,no_subtree_check,rw)"
        etc_exports = self.ssh.remote_file('/etc/exports', 'r')
        contents = etc_exports.read()
        etc_exports.close()
        etc_exports = self.ssh.remote_file('/etc/exports', 'a')
        for node in nodes:
            for path in export_paths:
                export_line = ' '.join(
                    [path, node.alias + nfs_export_settings + '\n'])
                if export_line not in contents:
                    etc_exports.write(export_line)
        etc_exports.close()
        self.ssh.execute('exportfs -fra')

    def stop_exporting_fs_to_nodes(self, nodes, paths=None):
        """
        Removes nodes from this node's /etc/exportfs

        nodes - list of nodes to stop

        Example:
        $ node.remove_export_fs_to_nodes(nodes=[node1,node2])
        """
        if paths:
            regex = '|'.join([' '.join([path, node.alias]) for path in paths
                              for node in nodes])
        else:
            regex = '|'.join([n.alias for n in nodes])
        self.ssh.remove_lines_from_file('/etc/exports', regex)
        self.ssh.execute('exportfs -fra')

    def start_nfs_server(self):
        log.info("Starting NFS server on %s" % self.alias)
        self.ssh.execute('/etc/init.d/portmap start', ignore_exit_status=True)
        self.ssh.execute('mount -t rpc_pipefs sunrpc /var/lib/nfs/rpc_pipefs/',
                         ignore_exit_status=True)
        EXPORTSD = '/etc/exports.d'
        DUMMY_EXPORT_DIR = '/dummy_export_for_broken_init_script'
        DUMMY_EXPORT_LINE = ' '.join([DUMMY_EXPORT_DIR,
                                      '127.0.0.1(ro,no_subtree_check)'])
        DUMMY_EXPORT_FILE = posixpath.join(EXPORTSD, 'dummy.exports')
        # Hack to get around broken debian nfs-kernel-server script
        # http://bugs.debian.org/cgi-bin/bugreport.cgi?bug=679274
        self.ssh.execute("mkdir -p %s" % EXPORTSD)
        self.ssh.execute("mkdir -p %s" % DUMMY_EXPORT_DIR)
        with self.ssh.remote_file(DUMMY_EXPORT_FILE, 'w') as dummyf:
            dummyf.write(DUMMY_EXPORT_LINE)
        self.ssh.execute('/etc/init.d/nfs start')
        self.ssh.execute('rm -f %s' % DUMMY_EXPORT_FILE)
        self.ssh.execute('rm -rf %s' % DUMMY_EXPORT_DIR)
        self.ssh.execute('exportfs -fra')

    def mount_nfs_shares(self, server_node, remote_paths):
        """
        Mount each path in remote_paths from the remote server_node

        server_node - remote server node that is sharing the remote_paths
        remote_paths - list of remote paths to mount from server_node
        """
        self.ssh.execute('/etc/init.d/portmap start')
        # TODO: move this fix for xterm somewhere else
        self.ssh.execute('mount -t devpts none /dev/pts',
                         ignore_exit_status=True)
        mount_map = self.get_mount_map()
        mount_paths = []
        for path in remote_paths:
            network_device = "%s:%s" % (server_node.alias, path)
            if network_device in mount_map:
                mount_path, typ, options = mount_map.get(network_device)
                log.debug('nfs share %s already mounted to %s on '
                          'node %s, skipping...' %
                          (network_device, mount_path, self.alias))
            else:
                mount_paths.append(path)
        remote_paths = mount_paths
        remote_paths_regex = '|'.join(map(lambda x: x.center(len(x) + 2),
                                          remote_paths))
        self.ssh.remove_lines_from_file('/etc/fstab', remote_paths_regex)
        fstab = self.ssh.remote_file('/etc/fstab', 'a')
        mount_opts = 'rw,exec,noauto'
        for path in remote_paths:
            fstab.write('%s:%s %s nfs %s 0 0\n' %
                        (server_node.alias, path, path, mount_opts))
        fstab.close()
        for path in remote_paths:
            if not self.ssh.path_exists(path):
                self.ssh.makedirs(path)
            self.ssh.execute('mount %s' % path)

    def get_mount_map(self):
        mount_map = {}
        mount_lines = self.ssh.execute('mount')
        for line in mount_lines:
            dev, on_label, path, type_label, fstype, options = line.split()
            mount_map[dev] = [path, fstype, options]
        return mount_map

    def get_device_map(self):
        """
        Returns a dictionary mapping devices->(# of blocks) based on
        'fdisk -l' and /proc/partitions
        """
        dev_regex = '/dev/[A-Za-z0-9/]+'
        r = re.compile('Disk (%s):' % dev_regex)
        fdiskout = '\n'.join(self.ssh.execute("fdisk -l 2>/dev/null"))
        proc_parts = '\n'.join(self.ssh.execute("cat /proc/partitions"))
        devmap = {}
        for dev in r.findall(fdiskout):
            short_name = dev.replace('/dev/', '')
            r = re.compile("(\d+)\s+%s(?:\s+|$)" % short_name)
            devmap[dev] = int(r.findall(proc_parts)[0])
        return devmap

    def get_partition_map(self, device=None):
        """
        Returns a dictionary mapping partitions->(start, end, blocks, id) based
        on 'fdisk -l'
        """
        fdiskout = '\n'.join(self.ssh.execute("fdisk -l %s 2>/dev/null" %
                                              (device or '')))
        part_regex = '/dev/[A-Za-z0-9/]+'
        r = re.compile('(%s)\s+\*?\s+'
                       '(\d+)(?:[-+])?\s+'
                       '(\d+)(?:[-+])?\s+'
                       '(\d+)(?:[-+])?\s+'
                       '([\da-fA-F][\da-fA-F]?)' % part_regex)
        partmap = {}
        for match in r.findall(fdiskout):
            part, start, end, blocks, sys_id = match
            partmap[part] = [int(start), int(end), int(blocks), sys_id]
        return partmap

    def mount_device(self, device, path):
        """
        Mount device to path
        """
        self.ssh.remove_lines_from_file('/etc/fstab',
                                        path.center(len(path) + 2))
        master_fstab = self.ssh.remote_file('/etc/fstab', mode='a')
        master_fstab.write("%s %s auto noauto,defaults 0 0\n" %
                           (device, path))
        master_fstab.close()
        if not self.ssh.path_exists(path):
            self.ssh.makedirs(path)
        self.ssh.execute('mount %s' % path)

    def add_to_etc_hosts(self, nodes):
        """
        Adds all names for node in nodes arg to this node's /etc/hosts file
        """
        self.remove_from_etc_hosts(nodes)
        host_file = self.ssh.remote_file('/etc/hosts', 'a')
        for node in nodes:
            print >> host_file, node.get_hosts_entry()
        host_file.close()

    def remove_from_etc_hosts(self, nodes):
        """
        Remove all network names for node in nodes arg from this node's
        /etc/hosts file
        """
        aliases = map(lambda x: x.alias, nodes)
        self.ssh.remove_lines_from_file('/etc/hosts', '|'.join(aliases))

    def set_hostname(self, hostname=None):
        """
        Set this node's hostname to self.alias

        hostname - optional hostname to set (defaults to self.alias)
        """
        hostname = hostname or self.alias
        hostname_file = self.ssh.remote_file("/etc/hostname", "w")
        hostname_file.write(hostname)
        hostname_file.close()
        try:
            self.ssh.execute('hostname -F /etc/hostname')
        except:
            if not utils.is_valid_hostname(hostname):
                raise exception.InvalidHostname(
                    "Please terminate and recreate this cluster with a name"
                    " that is also a valid hostname.  This hostname is"
                    " invalid: %s" % hostname)
            else:
                raise

    @property
    def network_names(self):
        """ Returns all network names for this node in a dictionary"""
        names = {}
        names['INTERNAL_IP'] = self.private_ip_address
        names['INTERNAL_NAME'] = self.private_dns_name
        names['INTERNAL_NAME_SHORT'] = self.private_dns_name_short
        names['INTERNAL_ALIAS'] = self.alias
        return names

    @property
    def attached_vols(self):
        """
        Returns a dictionary of all attached volumes minus the root device in
        the case of EBS backed instances
        """
        attached_vols = {}
        attached_vols.update(self.block_device_mapping)
        if self.is_ebs_backed():
            # exclude the root device from the list
            root_dev = self.root_device_name
            if root_dev in attached_vols:
                attached_vols.pop(root_dev)
        return attached_vols

    def detach_external_volumes(self):
        """
        Detaches all volumes returned by self.attached_vols
        """
        block_devs = self.attached_vols
        for dev in block_devs:
            vol_id = block_devs[dev].volume_id
            vol = self.ec2.get_volume(vol_id)
            log.info("Detaching volume %s from %s" % (vol.id, self.alias))
            if vol.status not in ['available', 'detaching']:
                vol.detach()

    def delete_root_volume(self):
        """
        Detach and destroy EBS root volume (EBS-backed node only)
        """
        if not self.is_ebs_backed():
            return
        root_vol = self.block_device_mapping[self.root_device_name]
        vol_id = root_vol.volume_id
        vol = self.ec2.get_volume(vol_id)
        vol.detach()
        while vol.update() != 'available':
            time.sleep(5)
        log.info("Deleting node %s's root volume" % self.alias)
        root_vol.delete()

    @property
    def spot_id(self):
        if self.instance.spot_instance_request_id:
            return self.instance.spot_instance_request_id

    def get_spot_request(self):
        spot = self.ec2.get_all_spot_requests(
            filters={'spot-instance-request-id': self.spot_id})
        if spot:
            return spot[0]

    def is_master(self):
        return self.alias == 'master' or self.alias.endswith("-master")

    def is_instance_store(self):
        return self.instance.root_device_type == "instance-store"

    def is_ebs_backed(self):
        return self.instance.root_device_type == "ebs"

    def is_cluster_compute(self):
        return self.instance.instance_type in static.CLUSTER_COMPUTE_TYPES

    def is_gpu_compute(self):
        return self.instance.instance_type in static.CLUSTER_GPU_TYPES

    def is_cluster_type(self):
        return self.instance.instance_type in static.HVM_ONLY_TYPES

    def is_spot(self):
        return self.spot_id is not None

    def is_stoppable(self):
        return self.is_ebs_backed() and not self.is_spot()

    def is_stopped(self):
        return self.state == "stopped"

    def start(self):
        """
        Starts EBS-backed instance and puts it in the 'running' state.
        Only works if this node is EBS-backed, raises
        exception.InvalidOperation otherwise.
        """
        if not self.is_ebs_backed():
            raise exception.InvalidOperation(
                "Only EBS-backed instances can be started")
        return self.instance.start()

    def stop(self):
        """
        Shutdown EBS-backed instance and put it in the 'stopped' state.
        Only works if this node is EBS-backed, raises
        exception.InvalidOperation otherwise.

        NOTE: The EBS root device will *not* be deleted and the instance can
        be 'started' later on.
        """
        if self.is_spot():
            raise exception.InvalidOperation(
                "spot instances can not be stopped")
        elif not self.is_ebs_backed():
            raise exception.InvalidOperation(
                "Only EBS-backed instances can be stopped")
        if not self.is_stopped():
            log.info("Stopping node: %s (%s)" % (self.alias, self.id))
            return self.instance.stop()
        else:
            log.info("Node '%s' is already stopped" % self.alias)

    def terminate(self):
        """
        Shutdown and destroy this instance. For EBS-backed nodes, this
        will also destroy the node's EBS root device. Puts this node
        into a 'terminated' state.
        """
        if self.spot_id:
            log.info("Canceling spot request %s" % self.spot_id)
            self.get_spot_request().cancel()
        log.info("Terminating node: %s (%s)" % (self.alias, self.id))
        return self.instance.terminate()

    def shutdown(self):
        """
        Shutdown this instance. This method will terminate traditional
        instance-store instances and stop EBS-backed instances
        (i.e. not destroy EBS root dev)
        """
        if self.is_stoppable():
            self.stop()
        else:
            self.terminate()

    def reboot(self):
        """
        Reboot this instance.
        """
        self.instance.reboot()

    def is_ssh_up(self):
        try:
            return self.ssh.transport is not None
        except exception.SSHError:
            return False

    def wait(self, interval=30):
        while not self.is_up():
            time.sleep(interval)

    def is_up(self):
        if self.update() != 'running':
            return False
        if not self.is_ssh_up():
            return False
        if self.private_ip_address is None:
            log.debug("instance %s has no private_ip_address" % self.id)
            log.debug("attempting to determine private_ip_address for "
                      "instance %s" % self.id)
            try:
                private_ip = self.ssh.execute(
                    'python -c '
                    '"import socket; print socket.gethostbyname(\'%s\')"' %
                    self.private_dns_name)[0].strip()
                log.debug("determined instance %s's private ip to be %s" %
                          (self.id, private_ip))
                self.instance.private_ip_address = private_ip
            except Exception, e:
                print e
                return False
        return True

    def update(self):
        res = self.ec2.get_all_instances(filters={'instance-id': self.id})
        self.instance = res[0]
        return self.state

    @property
    def addr(self):
        """
        Returns the most widely accessible address for the instance. This
        property first checks if dns_name is available, then the public ip, and
        finally the private ip. If none of these addresses are available it
        returns None.
        """
        if not self.dns_name:
            if self.ip_address:
                return self.ip_address
            else:
                return self.private_ip_address
        else:
            return self.dns_name

    @property
    def ssh(self):
        if not self._ssh:
            self._ssh = sshutils.SSHClient(self.addr,
                                           username=self.user,
                                           private_key=self.key_location)
        return self._ssh

    def shell(self, user=None, forward_x11=False, forward_agent=False,
              pseudo_tty=False, command=None):
        """
        Attempts to launch an interactive shell by first trying the system's
        ssh client. If the system does not have the ssh command it falls back
        to a pure-python ssh shell.
        """
        if self.update() != 'running':
            try:
                alias = self.alias
            except exception.BaseException:
                alias = None
            label = 'instance'
            if alias == "master":
                label = "master"
                alias = "node"
            elif alias:
                label = "node"
            instance_id = alias or self.id
            raise exception.InstanceNotRunning(instance_id, self.state,
                                               label=label)
        user = user or self.user
        if utils.has_required(['ssh']):
            log.debug("Using native OpenSSH client")
            sshopts = '-i %s' % self.key_location
            if forward_x11:
                sshopts += ' -Y'
            if forward_agent:
                sshopts += ' -A'
            if pseudo_tty:
                sshopts += ' -t'
            ssh_cmd = static.SSH_TEMPLATE % dict(opts=sshopts, user=user,
                                                 host=self.addr)
            if command:
                command = "'source /etc/profile && %s'" % command
                ssh_cmd = ' '.join([ssh_cmd, command])
            log.debug("ssh_cmd: %s" % ssh_cmd)
            return subprocess.call(ssh_cmd, shell=True)
        else:
            log.debug("Using Pure-Python SSH client")
            if forward_x11:
                log.warn("X11 Forwarding not available in Python SSH client")
            if forward_agent:
                log.warn("Authentication agent forwarding not available in " +
                         "Python SSH client")
            if pseudo_tty:
                log.warn("Pseudo-tty allocation is not available in " +
                         "Python SSH client")
            if command:
                orig_user = self.ssh.get_current_user()
                self.ssh.switch_user(user)
                self.ssh.execute(command, silent=False)
                self.ssh.switch_user(orig_user)
                return self.ssh.get_last_status()
            self.ssh.interactive_shell(user=user)

    def get_hosts_entry(self):
        """ Returns /etc/hosts entry for this node """
        etc_hosts_line = "%(INTERNAL_IP)s %(INTERNAL_ALIAS)s"
        etc_hosts_line = etc_hosts_line % self.network_names
        return etc_hosts_line

    def apt_command(self, cmd):
        """
        Run an apt-get command with all the necessary options for
        non-interactive use (DEBIAN_FRONTEND=interactive, -y, --force-yes, etc)
        """
        dpkg_opts = "Dpkg::Options::='--force-confnew'"
        cmd = "apt-get -o %s -y --force-yes %s" % (dpkg_opts, cmd)
        cmd = "DEBIAN_FRONTEND='noninteractive' " + cmd
        self.ssh.execute(cmd)

    def apt_install(self, pkgs):
        """
        Install a set of packages via apt-get.

        pkgs is a string that contains one or more packages separated by a
        space
        """
        self.apt_command('update')
        self.apt_command('install %s' % pkgs)

    def yum_command(self, cmd):
        """
        Run a yum command with all necessary options for non-interactive use.
        "-d 0 -e 0 -y"
        """
        yum_opts = ['-d', '0', '-e', '0', '-y']
        cmd = "yum " + " ".join(yum_opts) + " " + cmd
        self.ssh.execute(cmd)

    def yum_install(self, pkgs):
        """
        Install a set of packages via yum.

        pkgs is a string that contains one or more packages separated by a
        space
        """
        self.yum_command('install %s' % pkgs)

    @property
    def package_provider(self):
        """
        In order to determine which packaging system to use, check to see if
        /usr/bin/apt exists on the node, and use apt if it exists. Otherwise
        test to see if /usr/bin/yum exists and use that.
        """
        if self.ssh.isfile('/usr/bin/apt-get'):
            return "apt"
        elif self.ssh.isfile('/usr/bin/yum'):
            return "yum"

    def package_install(self, pkgs):
        """
        Provides a declarative install packages on systems, regardless
        of the system's packging type (apt/yum).
        """
        if self.package_provider == "apt":
            self.apt_install(pkgs)
        elif self.package_provider == "yum":
            self.yum_install(pkgs)

    def __del__(self):
        if self._ssh:
            self._ssh.close()

########NEW FILE########
__FILENAME__ = boto
# Copyright 2009-2014 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

import os

from starcluster import clustersetup
from starcluster.logger import log


BOTO_CFG_TEMPLATE = """\
[Credentials]
aws_access_key_id = %(aws_access_key_id)s
aws_secret_access_key = %(aws_secret_access_key)s

[Boto]
https_validate_certificates=True
"""


class BotoPlugin(clustersetup.ClusterSetup):
    """
    Plugin that configures a ~/.boto file for CLUSTER_USER
    """
    def __init__(self, boto_cfg=None):
        self.boto_cfg = os.path.expanduser(boto_cfg or '') or None

    def run(self, nodes, master, user, shell, volumes):
        mssh = master.ssh
        mssh.switch_user(user)
        botocfg = '/home/%s/.boto' % user
        if not mssh.path_exists(botocfg):
            log.info("Installing AWS credentials for user: %s" % user)
            if self.boto_cfg:
                log.info("Copying %s to %s" % (self.boto_cfg, botocfg))
                mssh.put(self.boto_cfg, botocfg)
            else:
                log.info("Installing current credentials to: %s" % botocfg)
                f = mssh.remote_file(botocfg, 'w')
                f.write(BOTO_CFG_TEMPLATE % master.ec2.__dict__)
                f.close()
            mssh.chmod(0400, botocfg)
        else:
            log.warn("AWS credentials already present - skipping install")

########NEW FILE########
__FILENAME__ = condor
# Copyright 2009-2014 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

from starcluster import clustersetup
from starcluster.templates import condor
from starcluster.logger import log

CONDOR_CFG = '/etc/condor/config.d/40starcluster'
FS_REMOTE_DIR = '/home/._condor_tmp'


class CondorPlugin(clustersetup.DefaultClusterSetup):

    def _add_condor_node(self, node):
        condorcfg = node.ssh.remote_file(CONDOR_CFG, 'w')
        daemon_list = "MASTER, STARTD, SCHEDD"
        if node.is_master():
            daemon_list += ", COLLECTOR, NEGOTIATOR"
        ctx = dict(CONDOR_HOST='master', DAEMON_LIST=daemon_list,
                   FS_REMOTE_DIR=FS_REMOTE_DIR)
        condorcfg.write(condor.condor_tmpl % ctx)
        condorcfg.close()
        node.ssh.execute('pkill condor', ignore_exit_status=True)
        config_vars = ["LOCAL_DIR", "LOG", "SPOOL", "RUN", "EXECUTE", "LOCK",
                       "CRED_STORE_DIR"]
        config_vals = ['$(condor_config_val %s)' % var for var in config_vars]
        node.ssh.execute('mkdir -p %s' % ' '.join(config_vals))
        node.ssh.execute('chown -R condor:condor %s' % ' '.join(config_vals))
        node.ssh.execute('/etc/init.d/condor start')

    def _setup_condor(self, master=None, nodes=None):
        log.info("Setting up Condor grid")
        master = master or self._master
        if not master.ssh.isdir(FS_REMOTE_DIR):
            # TODO: below should work but doesn't for some reason...
            # master.ssh.mkdir(FS_REMOTE_DIR, mode=01777)
            master.ssh.mkdir(FS_REMOTE_DIR)
            master.ssh.chmod(01777, FS_REMOTE_DIR)
        nodes = nodes or self.nodes
        log.info("Starting Condor master")
        self._add_condor_node(master)
        log.info("Starting Condor nodes")
        for node in nodes:
            self.pool.simple_job(self._add_condor_node, (node,),
                                 jobid=node.alias)
        self.pool.wait(numtasks=len(nodes))

    def run(self, nodes, master, user, user_shell, volumes):
        self._nodes = nodes
        self._master = master
        self._user = user
        self._user_shell = user_shell
        self._volumes = volumes
        self._setup_condor()

    def on_add_node(self, node, nodes, master, user, user_shell, volumes):
        self._nodes = nodes
        self._master = master
        self._user = user
        self._user_shell = user_shell
        self._volumes = volumes
        log.info("Adding %s to Condor" % node.alias)
        self._add_condor_node(node)

    def on_remove_node(self, node, nodes, master, user, user_shell, volumes):
        self._nodes = nodes
        self._master = master
        self._user = user
        self._user_shell = user_shell
        self._volumes = volumes
        log.info("Removing %s from Condor peacefully..." % node.alias)
        master.ssh.execute("condor_off -peaceful %s" % node.alias)
        node.ssh.execute("pkill condor", ignore_exit_status=True)

########NEW FILE########
__FILENAME__ = hadoop
# Copyright 2009-2014 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

import posixpath

from starcluster import threadpool
from starcluster import clustersetup
from starcluster.logger import log

core_site_templ = """\
<?xml version="1.0"?>
<?xml-stylesheet type="text/xsl" href="configuration.xsl"?>

<!-- Put site-specific property overrides in this file. -->

<configuration>
<!-- In: conf/core-site.xml -->
<property>
  <name>hadoop.tmp.dir</name>
  <value>%(hadoop_tmpdir)s</value>
  <description>A base for other temporary directories.</description>
</property>

<property>
  <name>fs.default.name</name>
  <value>hdfs://%(master)s:54310</value>
  <description>The name of the default file system.  A URI whose
  scheme and authority determine the FileSystem implementation.  The
  uri's scheme determines the config property (fs.SCHEME.impl) naming
  the FileSystem implementation class.  The uri's authority is used to
  determine the host, port, etc. for a filesystem.</description>
</property>

</configuration>
"""

hdfs_site_templ = """\
<?xml version="1.0"?>
<?xml-stylesheet type="text/xsl" href="configuration.xsl"?>

<!-- Put site-specific property overrides in this file. -->

<configuration>
<!-- In: conf/hdfs-site.xml -->
<property>
  <name>dfs.permissions</name>
  <value>false</value>
</property>
<property>
  <name>dfs.replication</name>
  <value>%(replication)d</value>
  <description>Default block replication.
  The actual number of replications can be specified when the file is created.
  The default is used if replication is not specified in create time.
  </description>
</property>
</configuration>
"""

mapred_site_templ = """\
<?xml version="1.0"?>
<?xml-stylesheet type="text/xsl" href="configuration.xsl"?>

<!-- Put site-specific property overrides in this file. -->

<configuration>
<!-- In: conf/mapred-site.xml -->
<property>
  <name>mapred.job.tracker</name>
  <value>%(master)s:54311</value>
  <description>The host and port that the MapReduce job tracker runs
  at.  If "local", then jobs are run in-process as a single map
  and reduce task.
  </description>
</property>
<property>
  <name>mapred.tasktracker.map.tasks.maximum</name>
  <value>%(map_tasks_max)d</value>
</property>
<property>
  <name>mapred.tasktracker.reduce.tasks.maximum</name>
  <value>%(reduce_tasks_max)d</value>
</property>
</configuration>
"""


class Hadoop(clustersetup.ClusterSetup):
    """
    Configures Hadoop using Cloudera packages on StarCluster
    """

    def __init__(self, hadoop_tmpdir='/mnt/hadoop', map_to_proc_ratio='1.0',
                 reduce_to_proc_ratio='0.3'):
        self.hadoop_tmpdir = hadoop_tmpdir
        self.hadoop_home = '/usr/lib/hadoop'
        self.hadoop_conf = '/etc/hadoop-0.20/conf.starcluster'
        self.empty_conf = '/etc/hadoop-0.20/conf.empty'
        self.centos_java_home = '/usr/lib/jvm/java'
        self.centos_alt_cmd = 'alternatives'
        self.ubuntu_javas = ['/usr/lib/jvm/java-6-sun/jre',
                             '/usr/lib/jvm/java-6-openjdk/jre',
                             '/usr/lib/jvm/default-java/jre']
        self.ubuntu_alt_cmd = 'update-alternatives'
        self.map_to_proc_ratio = float(map_to_proc_ratio)
        self.reduce_to_proc_ratio = float(reduce_to_proc_ratio)
        self._pool = None

    @property
    def pool(self):
        if self._pool is None:
            self._pool = threadpool.get_thread_pool(20, disable_threads=False)
        return self._pool

    def _get_java_home(self, node):
        # check for CentOS, otherwise default to Ubuntu 10.04's JAVA_HOME
        if node.ssh.isfile('/etc/redhat-release'):
            return self.centos_java_home
        for java in self.ubuntu_javas:
            if node.ssh.isdir(java):
                return java
        raise Exception("Cant find JAVA jre")

    def _get_alternatives_cmd(self, node):
        # check for CentOS, otherwise default to Ubuntu 10.04
        if node.ssh.isfile('/etc/redhat-release'):
            return self.centos_alt_cmd
        return self.ubuntu_alt_cmd

    def _setup_hadoop_user(self, node, user):
        node.ssh.execute('gpasswd -a %s hadoop' % user)

    def _install_empty_conf(self, node):
        node.ssh.execute('cp -r %s %s' % (self.empty_conf, self.hadoop_conf))
        alternatives_cmd = self._get_alternatives_cmd(node)
        cmd = '%s --install /etc/hadoop-0.20/conf ' % alternatives_cmd
        cmd += 'hadoop-0.20-conf %s 50' % self.hadoop_conf
        node.ssh.execute(cmd)

    def _configure_env(self, node):
        env_file_sh = posixpath.join(self.hadoop_conf, 'hadoop-env.sh')
        node.ssh.remove_lines_from_file(env_file_sh, 'JAVA_HOME')
        env_file = node.ssh.remote_file(env_file_sh, 'a')
        env_file.write('export JAVA_HOME=%s\n' % self._get_java_home(node))
        env_file.close()

    def _configure_mapreduce_site(self, node, cfg):
        mapred_site_xml = posixpath.join(self.hadoop_conf, 'mapred-site.xml')
        mapred_site = node.ssh.remote_file(mapred_site_xml)
        # Hadoop default: 2 maps, 1 reduce
        # AWS EMR uses approx 1 map per proc and .3 reduce per proc
        map_tasks_max = max(
            2,
            int(self.map_to_proc_ratio * node.num_processors))
        reduce_tasks_max = max(
            1,
            int(self.reduce_to_proc_ratio * node.num_processors))
        cfg.update({
            'map_tasks_max': map_tasks_max,
            'reduce_tasks_max': reduce_tasks_max})
        mapred_site.write(mapred_site_templ % cfg)
        mapred_site.close()

    def _configure_core(self, node, cfg):
        core_site_xml = posixpath.join(self.hadoop_conf, 'core-site.xml')
        core_site = node.ssh.remote_file(core_site_xml)
        core_site.write(core_site_templ % cfg)
        core_site.close()

    def _configure_hdfs_site(self, node, cfg):
        hdfs_site_xml = posixpath.join(self.hadoop_conf, 'hdfs-site.xml')
        hdfs_site = node.ssh.remote_file(hdfs_site_xml)
        hdfs_site.write(hdfs_site_templ % cfg)
        hdfs_site.close()

    def _configure_masters(self, node, master):
        masters_file = posixpath.join(self.hadoop_conf, 'masters')
        masters_file = node.ssh.remote_file(masters_file)
        masters_file.write(master.alias)
        masters_file.close()

    def _configure_slaves(self, node, node_aliases):
        slaves_file = posixpath.join(self.hadoop_conf, 'slaves')
        slaves_file = node.ssh.remote_file(slaves_file)
        slaves_file.write('\n'.join(node_aliases))
        slaves_file.close()

    def _setup_hdfs(self, node, user):
        self._setup_hadoop_dir(node, self.hadoop_tmpdir, 'hdfs', 'hadoop')
        mapred_dir = posixpath.join(self.hadoop_tmpdir, 'hadoop-mapred')
        self._setup_hadoop_dir(node, mapred_dir, 'mapred', 'hadoop')
        userdir = posixpath.join(self.hadoop_tmpdir, 'hadoop-%s' % user)
        self._setup_hadoop_dir(node, userdir, user, 'hadoop')
        hdfsdir = posixpath.join(self.hadoop_tmpdir, 'hadoop-hdfs')
        if not node.ssh.isdir(hdfsdir):
            node.ssh.execute("su hdfs -c 'hadoop namenode -format'")
        self._setup_hadoop_dir(node, hdfsdir, 'hdfs', 'hadoop')

    def _setup_dumbo(self, node):
        if not node.ssh.isfile('/etc/dumbo.conf'):
            f = node.ssh.remote_file('/etc/dumbo.conf')
            f.write('[hadoops]\nstarcluster: %s\n' % self.hadoop_home)
            f.close()

    def _configure_hadoop(self, master, nodes, user):
        log.info("Configuring Hadoop...")
        log.info("Adding user %s to hadoop group" % user)
        for node in nodes:
            self.pool.simple_job(self._setup_hadoop_user, (node, user),
                                 jobid=node.alias)
        self.pool.wait(numtasks=len(nodes))
        node_aliases = map(lambda n: n.alias, nodes)
        cfg = {'master': master.alias, 'replication': 3,
               'hadoop_tmpdir': posixpath.join(self.hadoop_tmpdir,
                                               'hadoop-${user.name}')}
        log.info("Installing configuration templates...")
        for node in nodes:
            self.pool.simple_job(self._install_empty_conf, (node,),
                                 jobid=node.alias)
        self.pool.wait(numtasks=len(nodes))
        log.info("Configuring environment...")
        for node in nodes:
            self.pool.simple_job(self._configure_env, (node,),
                                 jobid=node.alias)
        self.pool.wait(numtasks=len(nodes))
        log.info("Configuring MapReduce Site...")
        for node in nodes:
            self.pool.simple_job(self._configure_mapreduce_site, (node, cfg),
                                 jobid=node.alias)
        self.pool.wait(numtasks=len(nodes))
        log.info("Configuring Core Site...")
        for node in nodes:
            self.pool.simple_job(self._configure_core, (node, cfg),
                                 jobid=node.alias)
        self.pool.wait(numtasks=len(nodes))
        log.info("Configuring HDFS Site...")
        for node in nodes:
            self.pool.simple_job(self._configure_hdfs_site, (node, cfg),
                                 jobid=node.alias)
        self.pool.wait(numtasks=len(nodes))
        log.info("Configuring masters file...")
        for node in nodes:
            self.pool.simple_job(self._configure_masters, (node, master),
                                 jobid=node.alias)
        self.pool.wait(numtasks=len(nodes))
        log.info("Configuring slaves file...")
        for node in nodes:
            self.pool.simple_job(self._configure_slaves, (node, node_aliases),
                                 jobid=node.alias)
        self.pool.wait(numtasks=len(nodes))
        log.info("Configuring HDFS...")
        for node in nodes:
            self.pool.simple_job(self._setup_hdfs, (node, user),
                                 jobid=node.alias)
        self.pool.wait(numtasks=len(nodes))
        log.info("Configuring dumbo...")
        for node in nodes:
            self.pool.simple_job(self._setup_dumbo, (node,), jobid=node.alias)
        self.pool.wait(numtasks=len(nodes))

    def _setup_hadoop_dir(self, node, path, user, group, permission="775"):
        if not node.ssh.isdir(path):
            node.ssh.mkdir(path)
        node.ssh.execute("chown -R %s:hadoop %s" % (user, path))
        node.ssh.execute("chmod -R %s %s" % (permission, path))

    def _start_datanode(self, node):
        node.ssh.execute('/etc/init.d/hadoop-0.20-datanode restart')

    def _start_tasktracker(self, node):
        node.ssh.execute('/etc/init.d/hadoop-0.20-tasktracker restart')

    def _start_hadoop(self, master, nodes):
        log.info("Starting namenode...")
        master.ssh.execute('/etc/init.d/hadoop-0.20-namenode restart')
        log.info("Starting secondary namenode...")
        master.ssh.execute('/etc/init.d/hadoop-0.20-secondarynamenode restart')
        log.info("Starting datanode on all nodes...")
        for node in nodes:
            self.pool.simple_job(self._start_datanode, (node,),
                                 jobid=node.alias)
        self.pool.wait()
        log.info("Starting jobtracker...")
        master.ssh.execute('/etc/init.d/hadoop-0.20-jobtracker restart')
        log.info("Starting tasktracker on all nodes...")
        for node in nodes:
            self.pool.simple_job(self._start_tasktracker, (node,),
                                 jobid=node.alias)
        self.pool.wait()

    def _open_ports(self, master):
        ports = [50070, 50030]
        ec2 = master.ec2
        for group in master.cluster_groups:
            for port in ports:
                has_perm = ec2.has_permission(group, 'tcp', port, port,
                                              '0.0.0.0/0')
                if not has_perm:
                    ec2.conn.authorize_security_group(group_id=group.id,
                                                      ip_protocol='tcp',
                                                      from_port=port,
                                                      to_port=port,
                                                      cidr_ip='0.0.0.0/0')

    def run(self, nodes, master, user, user_shell, volumes):
        self._configure_hadoop(master, nodes, user)
        self._start_hadoop(master, nodes)
        self._open_ports(master)
        log.info("Job tracker status: http://%s:50030" % master.dns_name)
        log.info("Namenode status: http://%s:50070" % master.dns_name)

########NEW FILE########
__FILENAME__ = ipcluster
# Copyright 2009-2014 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

"""
A starcluster plugin for running an IPython cluster
(requires IPython 0.13+)
"""
import json
import os
import time
import posixpath

from starcluster import utils
from starcluster import static
from starcluster import spinner
from starcluster import exception
from starcluster.utils import print_timing
from starcluster.clustersetup import DefaultClusterSetup

from starcluster.logger import log

IPCLUSTER_CACHE = os.path.join(static.STARCLUSTER_CFG_DIR, 'ipcluster')
CHANNEL_NAMES = (
    "control",
    "task",
    "notification",
    "mux",
    "iopub",
    "registration",
)

STARTED_MSG = """\
IPCluster has been started on %(cluster)s for user '%(user)s'
with %(n_engines)d engines on %(n_nodes)d nodes.

To connect to cluster from your local machine use:

from IPython.parallel import Client
client = Client('%(connector_file)s', sshkey='%(key_location)s')

See the IPCluster plugin doc for usage details:
http://star.mit.edu/cluster/docs/latest/plugins/ipython.html
"""


def _start_engines(node, user, n_engines=None, kill_existing=False):
    """Launch IPython engines on the given node

    Start one engine per CPU except on master where 1 CPU is reserved for house
    keeping tasks when possible.

    If kill_existing is True, any running of IPython engines on the same node
    are killed first.

    """
    if n_engines is None:
        n_engines = node.num_processors
    node.ssh.switch_user(user)
    if kill_existing:
        node.ssh.execute("pkill -f ipengineapp", ignore_exit_status=True)
    node.ssh.execute("ipcluster engines --n=%i --daemonize" % n_engines)
    node.ssh.switch_user('root')


class IPCluster(DefaultClusterSetup):
    """Start an IPython (>= 0.13) cluster

    Example config:

    [plugin ipcluster]
    setup_class = starcluster.plugins.ipcluster.IPCluster
    enable_notebook = True
    notebook_passwd = secret
    notebook_directory = /home/user/notebooks
    packer = pickle
    log_level = info

    """
    def __init__(self, enable_notebook=False, notebook_passwd=None,
                 notebook_directory=None, packer=None, log_level='INFO'):
        super(IPCluster, self).__init__()
        if isinstance(enable_notebook, basestring):
            self.enable_notebook = enable_notebook.lower().strip() == 'true'
        else:
            self.enable_notebook = enable_notebook
        self.notebook_passwd = notebook_passwd or utils.generate_passwd(16)
        self.notebook_directory = notebook_directory
        self.log_level = log_level
        if packer not in (None, 'json', 'pickle', 'msgpack'):
            log.error("Unsupported packer: %s", packer)
            self.packer = None
        else:
            self.packer = packer

    def _check_ipython_installed(self, node):
        has_ipy = node.ssh.has_required(['ipython', 'ipcluster'])
        if not has_ipy:
            raise exception.PluginError("IPython is not installed!")
        return has_ipy

    def _write_config(self, master, user, profile_dir):
        """Create cluster configuration files."""
        log.info("Writing IPython cluster config files")
        master.ssh.execute("rm -rf '%s'" % profile_dir)
        master.ssh.execute('ipython profile create')
        f = master.ssh.remote_file('%s/ipcontroller_config.py' % profile_dir)
        ssh_server = "@".join([user, master.public_dns_name])
        f.write('\n'.join([
            "c = get_config()",
            "c.HubFactory.ip='%s'" % master.private_ip_address,
            "c.IPControllerApp.ssh_server='%s'" % ssh_server,
            "c.Application.log_level = '%s'" % self.log_level,
            "",
        ]))
        f.close()
        f = master.ssh.remote_file('%s/ipengine_config.py' % profile_dir)
        f.write('\n'.join([
            "c = get_config()",
            "c.EngineFactory.timeout = 10",
            # Engines should wait a while for url files to arrive,
            # in case Controller takes a bit to start:
            "c.IPEngineApp.wait_for_url_file = 30",
            "c.Application.log_level = '%s'" % self.log_level,
            "",
        ]))
        f.close()
        f = master.ssh.remote_file('%s/ipython_config.py' % profile_dir)
        f.write('\n'.join([
            "c = get_config()",
            "c.EngineFactory.timeout = 10",
            # Engines should wait a while for url files to arrive,
            # in case Controller takes a bit to start
            "c.IPEngineApp.wait_for_url_file = 30",
            "c.Application.log_level = '%s'" % self.log_level,
            "",
        ]))
        if self.packer == 'msgpack':
            f.write('\n'.join([
                "c.Session.packer='msgpack.packb'",
                "c.Session.unpacker='msgpack.unpackb'",
                "",
            ]))
        elif self.packer == 'pickle':
            f.write('\n'.join([
                "c.Session.packer='pickle'",
                "",
            ]))
        # else: use the slow default JSON packer
        f.close()

    def _start_cluster(self, master, profile_dir):
        n_engines = max(1, master.num_processors - 1)
        log.info("Starting the IPython controller and %i engines on master"
                 % n_engines)
        # cleanup existing connection files, to prevent their use
        master.ssh.execute("rm -f %s/security/*.json" % profile_dir)
        master.ssh.execute("ipcluster start --n=%i --delay=5 --daemonize"
                           % n_engines)
        # wait for JSON file to exist
        json_filename = '%s/security/ipcontroller-client.json' % profile_dir
        log.info("Waiting for JSON connector file...",
                 extra=dict(__nonewline__=True))
        s = spinner.Spinner()
        s.start()
        try:
            found_file = False
            for i in range(30):
                if master.ssh.isfile(json_filename):
                    found_file = True
                    break
                time.sleep(1)
            if not found_file:
                raise ValueError(
                    "Timeout while waiting for the cluser json file: "
                    + json_filename)
        finally:
            s.stop()
        # Retrieve JSON connection info to make it possible to connect a local
        # client to the cluster controller
        if not os.path.isdir(IPCLUSTER_CACHE):
            log.info("Creating IPCluster cache directory: %s" %
                     IPCLUSTER_CACHE)
            os.makedirs(IPCLUSTER_CACHE)
        local_json = os.path.join(IPCLUSTER_CACHE,
                                  '%s-%s.json' % (master.parent_cluster,
                                                  master.region.name))
        master.ssh.get(json_filename, local_json)
        # Configure security group for remote access
        connection_params = json.load(open(local_json, 'rb'))
        # For IPython version 0.14+ the list of channel ports is explicitly
        # provided in the connector file
        channel_authorized = False
        for channel in CHANNEL_NAMES:
            port = connection_params.get(channel)
            if port is not None:
                self._authorize_port(master, port, channel)
                channel_authorized = True
        # For versions prior to 0.14, the channel port numbers are not given in
        # the connector file: let's open everything in high port numbers
        if not channel_authorized:
            self._authorize_port(master, (1000, 65535), "IPython controller")
        return local_json, n_engines

    def _start_notebook(self, master, user, profile_dir):
        log.info("Setting up IPython web notebook for user: %s" % user)
        user_cert = posixpath.join(profile_dir, '%s.pem' % user)
        ssl_cert = posixpath.join(profile_dir, '%s.pem' % user)
        if not master.ssh.isfile(user_cert):
            log.info("Creating SSL certificate for user %s" % user)
            ssl_subj = "/C=US/ST=SC/L=STAR/O=Dis/CN=%s" % master.dns_name
            master.ssh.execute(
                "openssl req -new -newkey rsa:4096 -days 365 "
                '-nodes -x509 -subj %s -keyout %s -out %s' %
                (ssl_subj, ssl_cert, ssl_cert))
        else:
            log.info("Using existing SSL certificate...")
        f = master.ssh.remote_file('%s/ipython_notebook_config.py' %
                                   profile_dir)
        notebook_port = 8888
        sha1py = 'from IPython.lib import passwd; print passwd("%s")'
        sha1cmd = "python -c '%s'" % sha1py
        sha1pass = master.ssh.execute(sha1cmd % self.notebook_passwd)[0]
        f.write('\n'.join([
            "c = get_config()",
            "c.IPKernelApp.pylab = 'inline'",
            "c.NotebookApp.certfile = u'%s'" % ssl_cert,
            "c.NotebookApp.ip = '*'",
            "c.NotebookApp.open_browser = False",
            "c.NotebookApp.password = u'%s'" % sha1pass,
            "c.NotebookApp.port = %d" % notebook_port,
        ]))
        f.close()
        if self.notebook_directory is not None:
            if not master.ssh.path_exists(self.notebook_directory):
                master.ssh.makedirs(self.notebook_directory)
            master.ssh.execute_async(
                "ipython notebook --no-browser --notebook-dir='%s'"
                % self.notebook_directory)
        else:
            master.ssh.execute_async("ipython notebook --no-browser")
        self._authorize_port(master, notebook_port, 'notebook')
        log.info("IPython notebook URL: https://%s:%s" %
                 (master.dns_name, notebook_port))
        log.info("The notebook password is: %s" % self.notebook_passwd)
        log.warn("Please check your local firewall settings if you're having "
                 "issues connecting to the IPython notebook",
                 extra=dict(__textwrap__=True))

    def _authorize_port(self, node, port, service_name, protocol='tcp'):
        group = node.cluster_groups[0]
        world_cidr = '0.0.0.0/0'
        if isinstance(port, tuple):
            port_min, port_max = port
        else:
            port_min, port_max = port, port
        port_open = node.ec2.has_permission(group, protocol, port_min,
                                            port_max, world_cidr)
        if not port_open:
            log.info("Authorizing tcp ports [%s-%s] on %s for: %s" %
                     (port_min, port_max, world_cidr, service_name))
            node.ec2.conn.authorize_security_group(
                group_id=group.id, ip_protocol='tcp', from_port=port_min,
                to_port=port_max, cidr_ip=world_cidr)

    @print_timing("IPCluster")
    def run(self, nodes, master, user, user_shell, volumes):
        self._check_ipython_installed(master)
        user_home = master.getpwnam(user).pw_dir
        profile_dir = posixpath.join(user_home, '.ipython', 'profile_default')
        master.ssh.switch_user(user)
        self._write_config(master, user, profile_dir)
        # Start the cluster and some engines on the master (leave 1
        # processor free to handle cluster house keeping)
        cfile, n_engines_master = self._start_cluster(master, profile_dir)
        # Start engines on each of the non-master nodes
        non_master_nodes = [node for node in nodes if not node.is_master()]
        for node in non_master_nodes:
            self.pool.simple_job(
                _start_engines, (node, user, node.num_processors),
                jobid=node.alias)
        n_engines_non_master = sum(node.num_processors
                                   for node in non_master_nodes)
        if len(non_master_nodes) > 0:
            log.info("Adding %d engines on %d nodes",
                     n_engines_non_master, len(non_master_nodes))
            self.pool.wait(len(non_master_nodes))
        if self.enable_notebook:
            self._start_notebook(master, user, profile_dir)
        n_engines_total = n_engines_master + n_engines_non_master
        log.info(STARTED_MSG % dict(cluster=master.parent_cluster,
                                    user=user, connector_file=cfile,
                                    key_location=master.key_location,
                                    n_engines=n_engines_total,
                                    n_nodes=len(nodes)))
        master.ssh.switch_user('root')

    def on_add_node(self, node, nodes, master, user, user_shell, volumes):
        self._check_ipython_installed(node)
        n_engines = node.num_processors
        log.info("Adding %d engines on %s", n_engines, node.alias)
        _start_engines(node, user)

    def on_remove_node(self, node, nodes, master, user, user_shell, volumes):
        raise NotImplementedError("on_remove_node method not implemented")


class IPClusterStop(DefaultClusterSetup):
    """Shutdown all the IPython processes of the cluster

    This plugin is meant to be run manually with:

      starcluster runplugin plugin_conf_name cluster_name

    """
    def run(self, nodes, master, user, user_shell, volumes):
        log.info("Shutting down IPython cluster")
        master.ssh.switch_user(user)
        master.ssh.execute("ipcluster stop", ignore_exit_status=True)
        time.sleep(2)
        log.info("Stopping IPython controller on %s", master.alias)
        master.ssh.execute("pkill -f ipcontrollerapp",
                           ignore_exit_status=True)
        master.ssh.execute("pkill -f 'ipython notebook'",
                           ignore_exit_status=True)
        master.ssh.switch_user('root')
        log.info("Stopping IPython engines on %d nodes", len(nodes))
        for node in nodes:
            self.pool.simple_job(self._stop_engines, (node, user))
        self.pool.wait(len(nodes))

    def _stop_engines(self, node, user):
        node.ssh.switch_user(user)
        node.ssh.execute("pkill -f ipengineapp", ignore_exit_status=True)
        node.ssh.switch_user('root')

    def on_add_node(self, node, nodes, master, user, user_shell, volumes):
        raise NotImplementedError("on_add_node method not implemented")

    def on_remove_node(self, node, nodes, master, user, user_shell, volumes):
        raise NotImplementedError("on_remove_node method not implemented")


class IPClusterRestartEngines(DefaultClusterSetup):
    """Plugin to kill and restart all engines of an IPython cluster

    This plugin can be useful to hard-reset the all the engines, for instance
    to be sure to free all the used memory even when dealing with memory leaks
    in compiled extensions.

    This plugin is meant to be run manually with:

      starcluster runplugin plugin_conf_name cluster_name

    """
    def run(self, nodes, master, user, user_shell, volumes):
        n_total = 0
        for node in nodes:
            n_engines = node.num_processors
            if node.is_master() and n_engines > 2:
                n_engines -= 1
            self.pool.simple_job(
                _start_engines, (node, user, n_engines, True),
                jobid=node.alias)
            n_total += n_engines
        log.info("Restarting %d engines on %d nodes", n_total, len(nodes))
        self.pool.wait(len(nodes))

    def on_add_node(self, node, nodes, master, user, user_shell, volumes):
        raise NotImplementedError("on_add_node method not implemented")

    def on_remove_node(self, node, nodes, master, user, user_shell, volumes):
        raise NotImplementedError("on_remove_node method not implemented")

########NEW FILE########
__FILENAME__ = mpich2
# Copyright 2009-2014 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

from starcluster import clustersetup
from starcluster.logger import log


class MPICH2Setup(clustersetup.DefaultClusterSetup):

    MPICH2_HOSTS = '/home/mpich2.hosts'
    MPICH2_PROFILE = '/etc/profile.d/mpich2.sh'

    def _configure_profile(self, node, aliases):
        mpich2_profile = node.ssh.remote_file(self.MPICH2_PROFILE, 'w')
        mpich2_profile.write("export HYDRA_HOST_FILE=%s" % self.MPICH2_HOSTS)

    def _update_alternatives(self, node):
        mpi_choices = node.ssh.execute("update-alternatives --list mpi")
        mpirun_choices = node.ssh.execute("update-alternatives --list mpirun")
        mpipath = None
        for choice in mpi_choices:
            if 'mpich2' in choice:
                mpipath = choice
                break
        mpirunpath = None
        for choice in mpirun_choices:
            if 'mpich2' in choice:
                mpirunpath = choice
                break
        node.ssh.execute("update-alternatives --set mpi %s" % mpipath)
        node.ssh.execute("update-alternatives --set mpirun %s" % mpirunpath)

    def run(self, nodes, master, user, shell, volumes):
        log.info("Creating MPICH2 hosts file")
        aliases = [n.alias for n in nodes]
        mpich2_hosts = master.ssh.remote_file(self.MPICH2_HOSTS, 'w')
        mpich2_hosts.write('\n'.join(aliases) + '\n')
        mpich2_hosts.close()
        log.info("Configuring MPICH2 profile")
        for node in nodes:
            self.pool.simple_job(self._configure_profile,
                                 (node, aliases),
                                 jobid=node.alias)
        self.pool.wait(len(nodes))
        log.info("Setting MPICH2 as default MPI on all nodes")
        for node in nodes:
            self.pool.simple_job(self._update_alternatives, (node),
                                 jobid=node.alias)
        self.pool.wait(len(nodes))
        log.info("MPICH2 is now ready to use")
        log.info(
            "Use mpicc, mpif90, mpirun, etc. to compile and run your MPI apps")

    def on_add_node(self, new_node, nodes, master, user, user_shell, volumes):
        log.info("Adding %s to MPICH2 hosts file" % new_node.alias)
        mpich2_hosts = master.ssh.remote_file(self.MPICH2_HOSTS, 'a')
        mpich2_hosts.write(new_node.alias + '\n')
        mpich2_hosts.close()
        log.info("Setting MPICH2 as default MPI on %s" % new_node.alias)
        self._update_alternatives(new_node)

    def on_remove_node(self, remove_node, nodes, master, user, user_shell,
                       volumes):
        log.info("Removing %s from MPICH2 hosts file" % remove_node.alias)
        master.ssh.remove_lines_from_file(self.MPICH2_HOSTS, remove_node.alias)

########NEW FILE########
__FILENAME__ = mysql
# Copyright 2009-2014 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

import posixpath
from starcluster.clustersetup import DefaultClusterSetup
from starcluster.logger import log

ndb_mgmd_template = """
[NDBD DEFAULT]
NoOfReplicas=%(num_replicas)s
DataMemory=%(data_memory)s    # How much memory to allocate for data storage
IndexMemory=%(index_memory)s   # How much memory to allocate for index storage
[MYSQLD DEFAULT]
[NDB_MGMD DEFAULT]
[TCP DEFAULT]
# Section for the cluster management node
[NDB_MGMD]
# IP address of the management node (this system)
HostName=%(mgm_ip)s
# Section for the storage nodes
"""

ndb_mgmd_storage = """
[NDBD]
HostName=%(storage_ip)s
DataDir=%(data_dir)s
BackupDataDir=%(backup_data_dir)s
"""

MY_CNF = """
#
# The MySQL database server configuration file.
#
# You can copy this to one of:
# - "/etc/mysql/my.cnf" to set global options,
# - "~/.my.cnf" to set user-specific options.
#
# One can use all long options that the program supports.
# Run program with --help to get a list of available options and with
# --log.info-defaults to see which it would actually understand and use.
#
# For explanations see
# http://dev.mysql.com/doc/mysql/en/server-system-variables.html

# This will be passed to all mysql clients
# It has been reported that passwords should be enclosed with ticks/quotes
# especially if they contain "#" chars...
# Remember to edit /etc/mysql/debian.cnf when changing the socket location.
[client]
port            = 3306
socket          = /var/run/mysqld/mysqld.sock

# Here is entries for some specific programs
# The following values assume you have at least 32M ram

# This was formally known as [safe_mysqld]. Both versions are currently parsed.
[mysqld_safe]
socket          = /var/run/mysqld/mysqld.sock
nice            = 0

[mysqld]
#
# * Basic Settings
#

#
# * IMPORTANT
#   If you make changes to these settings and your system uses apparmor, you
#   may also need to also adjust /etc/apparmor.d/usr.sbin.mysqld.
#

user            = mysql
socket          = /var/run/mysqld/mysqld.sock
port            = 3306
basedir         = /usr
datadir         = /var/lib/mysql
tmpdir          = /tmp
skip-external-locking
#
# Instead of skip-networking the default is now to listen only on
# localhost which is more compatible and is not less secure.
bind-address            = 127.0.0.1
#
# * Fine Tuning
#
key_buffer              = 16M
max_allowed_packet      = 16M
thread_stack            = 192K
thread_cache_size       = 8
# This replaces the startup script and checks MyISAM tables if needed
# the first time they are touched
myisam-recover         = BACKUP
#max_connections        = 100
#table_cache            = 64
#thread_concurrency     = 10
#
# * Query Cache Configuration
#
query_cache_limit       = 1M
query_cache_size        = 16M
#
# * Logging and Replication
#
# Both location gets rotated by the cronjob.
# Be aware that this log type is a performance killer.
# As of 5.1 you can enable the log at runtime!
#general_log_file        = /var/log/mysql/mysql.log
#general_log             = 1

log_error                = /var/log/mysql/error.log

# Here you can see queries with especially long duration
#log_slow_queries       = /var/log/mysql/mysql-slow.log
#long_query_time = 2
#log-queries-not-using-indexes
#
# The following can be used as easy to replay backup logs or for replication.
# note: if you are setting up a replication slave, see README.Debian about
#       other settings you may need to change.
#server-id              = 1
#log_bin                        = /var/log/mysql/mysql-bin.log
expire_logs_days        = 10
max_binlog_size         = 100M
#binlog_do_db           = include_database_name
#binlog_ignore_db       = include_database_name
#
# * InnoDB
#
# InnoDB is enabled by default with a 10MB datafile in /var/lib/mysql/.
# Read the manual for more InnoDB related options. There are many!
#
# * Security Features
#
# Read the manual, too, if you want chroot!
# chroot = /var/lib/mysql/
#
# For generating SSL certificates I recommend the OpenSSL GUI "tinyca".
#
# ssl-ca=/etc/mysql/cacert.pem
# ssl-cert=/etc/mysql/server-cert.pem
# ssl-key=/etc/mysql/server-key.pem

# Cluster Configuration
ndbcluster
# IP address of management node
ndb-connectstring=%(mgm_ip)s

[mysqldump]
quick
quote-names
max_allowed_packet      = 16M

[mysql]
#no-auto-rehash # faster start of mysql but no tab completion

[isamchk]
key_buffer              = 16M

[MYSQL_CLUSTER]
ndb-connectstring=%(mgm_ip)s

#
# * IMPORTANT: Additional settings that can override those from this file!
#   The files must end with '.cnf', otherwise they'll be ignored.
#
!includedir /etc/mysql/conf.d/
"""


class MysqlCluster(DefaultClusterSetup):
    """
    This plugin configures a mysql cluster on StarCluster
    Author: Marc Resnick

    Steps for mysql-cluster to work:
    1. mkdir -p /var/lib/mysql-cluster/backup
    2. chown -R mysql:mysql /var/lib/mysql-cluster/
    3. generate ndb-mgmd for master
    4. generate my.cnf for data nodes
    5. /etc/init.d/mysql-ndb-mgm restart on master
    6. pkill -9 mysql on data nodes
    7. /etc/init.d/mysql start on data nodes
    8. /etc/init.d/mysql-ndb restart on data nodes

    Correction to above, do this:
    1. define plugin section in config named mysql
    2. start cluster mysql (will fail)
    3. starcluster runplugin mysql mysql
    """
    def __init__(self, num_replicas, data_memory, index_memory, dump_file,
                 dump_interval, dedicated_query, num_data_nodes):
        super(MysqlCluster, self).__init__()
        self._num_replicas = int(num_replicas)
        self._data_memory = data_memory
        self._index_memory = index_memory
        self._dump_file = dump_file
        self._dump_interval = dump_interval
        self._dedicated_query = dedicated_query.lower() == 'true'
        self._num_data_nodes = int(num_data_nodes)

    def _install_mysql_cluster(self, node):
        preseedf = '/tmp/mysql-preseed.txt'
        mysqlpreseed = node.ssh.remote_file(preseedf, 'w')
        preseeds = """\
    mysql-server mysql-server/root_password select
    mysql-server mysql-server/root_password seen true
    mysql-server mysql-server/root_password_again select
    mysql-server mysql-server/root_password_again seen true
        """
        mysqlpreseed.write(preseeds)
        mysqlpreseed.close()
        node.ssh.execute('debconf-set-selections < %s' % mysqlpreseed.name)
        node.ssh.execute('rm %s' % mysqlpreseed.name)
        node.apt_install('mysql-cluster-server')

    def _backup_and_reset(self, node):
        nconn = node.ssh
        nconn.execute('pkill -9 mysql; pkill -9 ndb',
                      ignore_exit_status=True)
        nconn.execute('mkdir -p /var/lib/mysql-cluster/BACKUP')
        nconn.execute('chown -R mysql:mysql /var/lib/mysql-cluster')

    def _write_my_cnf(self, node):
        nconn = node.ssh
        my_cnf = nconn.remote_file('/etc/mysql/my.cnf')
        my_cnf.write(self.generate_my_cnf())
        my_cnf.close()

    def run(self, nodes, master, user, user_shell, volumes):
        log.info("Installing mysql-cluster-server on all nodes...")
        for node in nodes:
            self.pool.simple_job(self._install_mysql_cluster, (node),
                                 jobid=node.alias)
        self.pool.wait(len(nodes))
        mconn = master.ssh
        mconn.execute('rm -f /usr/mysql-cluster/*')
        # Get IPs for all nodes
        self.mgm_ip = master.private_ip_address
        if not self._dedicated_query:
            self.storage_ips = [x.private_ip_address for x in nodes[1:]]
            self.query_ips = self.storage_ips
            self.data_nodes = nodes[1:]
            self.query_nodes = nodes
        else:
            self.data_nodes = nodes[1:self._num_data_nodes + 1]
            self.query_nodes = nodes[self._num_data_nodes + 1:]
            self.query_nodes.append(master)
            self.storage_ips = [x.private_ip_address for x in self.data_nodes]
            self.query_ips = [x.private_ip_address for x in self.query_nodes]
        # Create backup dir and change ownership of mysql-cluster dir
        log.info('Backing up and stopping all mysql processes on all nodes')
        for node in nodes:
            self.pool.simple_job(self._backup_and_reset, (node),
                                 jobid=node.alias)
        self.pool.wait(len(nodes))
        # Generate and place ndb_mgmd configuration file
        log.info('Generating ndb_mgmd.cnf...')
        ndb_mgmd = mconn.remote_file('/etc/mysql/ndb_mgmd.cnf')
        ndb_mgmd.write(self.generate_ndb_mgmd())
        ndb_mgmd.close()
        # Generate and place my.cnf configuration file on each data node
        log.info('Generating my.cnf on all nodes')
        for node in nodes:
            self.pool.simple_job(self._write_my_cnf, (node), jobid=node.alias)
        self.pool.wait(len(nodes))
        # Restart mysql-ndb-mgm on master
        log.info('Restarting mysql-ndb-mgm on master node...')
        mconn.execute('/etc/init.d/mysql-ndb-mgm restart')
        # Start mysqld-ndb on data nodes
        log.info('Restarting mysql-ndb on all data nodes...')
        for node in self.data_nodes:
            self.pool.simple_job(node.ssh.execute,
                                 ('/etc/init.d/mysql-ndb restart'),
                                 jobid=node.alias)
        self.pool.wait(len(self.data_nodes))
        # Start mysql on query nodes
        log.info('Starting mysql on all query nodes')
        for node in self.query_nodes:
            self.pool.simple_job(node.ssh.execute,
                                 ('/etc/init.d/mysql restart'),
                                 dict(ignore_exit_status=True),
                                 jobid=node.alias)
        self.pool.wait(len(self.query_nodes))
        # Import sql dump
        dump_file = self._dump_file
        dump_dir = '/mnt/mysql-cluster-backup'
        if posixpath.isabs(self._dump_file):
            dump_dir, dump_file = posixpath.split(self._dump_file)
        else:
            log.warn("%s is not an absolute path, defaulting to %s" %
                     (self._dump_file, posixpath.join(dump_dir, dump_file)))
        name, ext = posixpath.splitext(dump_file)
        sc_path = posixpath.join(dump_dir, name + '.sc' + ext)
        orig_path = posixpath.join(dump_dir, dump_file)
        if not mconn.isdir(dump_dir):
            log.info("Directory %s does not exist, creating..." % dump_dir)
            mconn.makedirs(dump_dir)
        if mconn.isfile(sc_path):
            mconn.execute('mysql < %s' % sc_path)
        elif mconn.isfile(orig_path):
            mconn.execute('mysql < %s' % orig_path)
        else:
            log.info('No dump file found, not importing.')
        log.info('Adding MySQL dump cronjob to master node')
        cronjob = self.generate_mysqldump_crontab(sc_path)
        mconn.remove_lines_from_file('/etc/crontab', '#starcluster-mysql')
        crontab_file = mconn.remote_file('/etc/crontab', 'a')
        crontab_file.write(cronjob)
        crontab_file.close()
        log.info('Management Node: %s' % master.alias)
        log.info('Data Nodes: \n%s' % '\n'.join([x.alias for x in
                                                 self.data_nodes]))
        log.info('Query Nodes: \n%s' % '\n'.join([x.alias for x in
                                                  self.query_nodes]))

    def generate_ndb_mgmd(self):
        ndb_mgmd = ndb_mgmd_template % {'num_replicas': self._num_replicas,
                                        'data_memory': self._data_memory,
                                        'index_memory': self._index_memory,
                                        'mgm_ip': self.mgm_ip}
        for x in self.storage_ips:
            ctx = {'storage_ip': x,
                   'data_dir': '/var/lib/mysql-cluster',
                   'backup_data_dir': '/var/lib/mysql-cluster'}
            ndb_mgmd += ndb_mgmd_storage % ctx
            ndb_mgmd += '\n'
        if self._dedicated_query:
            for x in self.query_nodes:
                ndb_mgmd += '[MYSQLD]\nHostName=%s\n' % x.private_ip_address
        else:
            for x in self.query_nodes:
                ndb_mgmd += '[MYSQLD]\n'
        return ndb_mgmd

    def generate_my_cnf(self):
        return MY_CNF % dict(mgm_ip=self.mgm_ip)

    def generate_mysqldump_crontab(self, path):
        crontab = (
            '\n*/%(dump_interval)s * * * * root ' +
            'mysql --batch --skip-column-names --execute="show databases"' +
            " | egrep -v '(mysql|information_schema)' | " +
            "xargs mysqldump --add-drop-table --add-drop-database -Y -B" +
            '> %(loc)s #starcluster-mysql\n'
        ) % {'dump_interval': self._dump_interval, 'loc': path}
        return crontab

    def on_add_node(self, node, nodes, master, user, user_shell, volumes):
        raise NotImplementedError("on_add_node method not implemented")

    def on_remove_node(self, node, nodes, master, user, user_shell, volumes):
        raise NotImplementedError("on_remove_node method not implemented")

########NEW FILE########
__FILENAME__ = pkginstaller
# Copyright 2009-2014 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

from starcluster import clustersetup
from starcluster.logger import log


class PackageInstaller(clustersetup.DefaultClusterSetup):
    """
    This plugin installs Ubuntu packages on all nodes in the cluster. The
    packages are specified in the plugin's config:

    [plugin pkginstaller]
    setup_class = starcluster.plugins.pkginstaller.PackageInstaller
    packages = mongodb, python-mongodb
    """
    def __init__(self, packages=None):
        super(PackageInstaller, self).__init__()
        self.packages = packages
        if packages:
            self.packages = [pkg.strip() for pkg in packages.split(',')]

    def run(self, nodes, master, user, user_shell, volumes):
        if not self.packages:
            log.info("No packages specified!")
            return
        log.info('Installing the following packages on all nodes:')
        log.info(', '.join(self.packages), extra=dict(__raw__=True))
        pkgs = ' '.join(self.packages)
        for node in nodes:
            self.pool.simple_job(node.apt_install, (pkgs), jobid=node.alias)
        self.pool.wait(len(nodes))

    def on_add_node(self, new_node, nodes, master, user, user_shell, volumes):
        log.info('Installing the following packages on %s:' % new_node.alias)
        pkgs = ' '.join(self.packages)
        new_node.apt_install(pkgs)

    def on_remove_node(self, node, nodes, master, user, user_shell, volumes):
        raise NotImplementedError("on_remove_node method not implemented")

########NEW FILE########
__FILENAME__ = pypkginstaller
# Copyright 2009-2014 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

"""Install python packages using pip

Packages are downloaded/installed in parallel, allowing for faster installs
when using many nodes.

For example to install the flask and SQLAlchemy packages on all the nodes::

    [plugin webapp-packages]
    setup_class = starcluster.plugins.pypkginstaller.PyPkgInstaller
    packages = flask, SQLAlchemy

It can also be used to install the development version of packages from
github, for instance if you want to install the master branch of IPython
and the latest released version of some dependencies::

    [plugin ipython-dev]
    setup_class = starcluster.plugins.pypkginstaller.PyPkgInstaller
    install_command = pip install -U %s
    packages = pyzmq,
               python-msgpack,
               git+http://github.com/ipython/ipython.git

"""
from starcluster.clustersetup import DefaultClusterSetup
from starcluster.logger import log
from starcluster.utils import print_timing


class PyPkgInstaller(DefaultClusterSetup):
    """Install Python packages with pip."""

    def __init__(self, packages="", install_command="pip install %s"):
        super(PyPkgInstaller, self).__init__()
        self.install_command = install_command
        self.packages = [p.strip() for p in packages.split(",") if p.strip()]

    @print_timing("PyPkgInstaller")
    def install_packages(self, nodes, dest='all nodes'):
        log.info("Installing Python packages on %s:" % dest)
        commands = [self.install_command % p for p in self.packages]
        for command in commands:
            log.info("$ " + command)
        cmd = "\n".join(commands)
        for node in nodes:
            self.pool.simple_job(node.ssh.execute, (cmd,), jobid=node.alias)
        self.pool.wait(len(nodes))

    def run(self, nodes, master, user, user_shell, volumes):
        self.install_packages(nodes)

    def on_add_node(self, node, nodes, master, user, user_shell, volumes):
        self.install_packages([node], dest=node.alias)

    def on_remove_node(self, node, nodes, master, user, user_shell, volumes):
        raise NotImplementedError("on_remove_node method not implemented")

########NEW FILE########
__FILENAME__ = sge
# Copyright 2009-2014 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.
import posixpath

from starcluster import clustersetup
from starcluster.templates import sge
from starcluster.logger import log


class SGEPlugin(clustersetup.DefaultClusterSetup):
    SGE_ROOT = "/opt/sge6"
    SGE_FRESH = "/opt/sge6-fresh"
    SGE_PROFILE = "/etc/profile.d/sge.sh"
    SGE_INST = "inst_sge_sc"
    SGE_CONF = "ec2_sge.conf"

    def __init__(self, master_is_exec_host=True, slots_per_host=None,
                 **kwargs):
        self.master_is_exec_host = str(master_is_exec_host).lower() == "true"
        self.slots_per_host = None
        if slots_per_host is not None:
            self.slots_per_host = int(slots_per_host)
        super(SGEPlugin, self).__init__(**kwargs)

    def _add_sge_submit_host(self, node):
        mssh = self._master.ssh
        mssh.execute('qconf -as %s' % node.alias)

    def _add_sge_admin_host(self, node):
        mssh = self._master.ssh
        mssh.execute('qconf -ah %s' % node.alias)

    def _setup_sge_profile(self, node):
        sge_profile = node.ssh.remote_file(self.SGE_PROFILE, "w")
        arch = node.ssh.execute(self._sge_path("util/arch"))[0]
        sge_profile.write(sge.sgeprofile_template % dict(arch=arch))
        sge_profile.close()

    def _add_to_sge(self, node):
        node.ssh.execute('pkill -9 sge', ignore_exit_status=True)
        node.ssh.execute('rm /etc/init.d/sge*', ignore_exit_status=True)
        self._inst_sge(node, exec_host=True)

    def _create_sge_pe(self, name="orte", nodes=None, queue="all.q"):
        """
        Create or update an SGE parallel environment

        name - name of parallel environment
        nodes - list of nodes to include in the parallel environment
                (default: all)
        queue - configure queue to use the new parallel environment
        """
        mssh = self._master.ssh
        pe_exists = mssh.get_status('qconf -sp %s' % name) == 0
        verb = 'Updating' if pe_exists else 'Creating'
        log.info("%s SGE parallel environment '%s'" % (verb, name))
        if not nodes:
            nodes = self._nodes if self.master_is_exec_host else self.nodes
        if self.slots_per_host is None:
            pe_slots = sum(self.pool.map(lambda n: n.num_processors, nodes,
                                         jobid_fn=lambda n: n.alias))
        else:
            pe_slots = self.slots_per_host * len(nodes)
        if not pe_exists:
            penv = mssh.remote_file("/tmp/pe.txt", "w")
            penv.write(sge.sge_pe_template % (name, pe_slots))
            penv.close()
            mssh.execute("qconf -Ap %s" % penv.name)
        else:
            mssh.execute("qconf -mattr pe slots %s %s" % (pe_slots, name))
        if queue:
            log.info("Adding parallel environment '%s' to queue '%s'" %
                     (name, queue))
            mssh.execute('qconf -mattr queue pe_list "%s" %s' % (name, queue))

    def _inst_sge(self, node, exec_host=True):
        self._setup_sge_profile(node)
        inst_sge = 'cd %s && TERM=rxvt ./%s ' % (self.SGE_ROOT, self.SGE_INST)
        if node.is_master():
            inst_sge += '-m '
        if exec_host:
            inst_sge += '-x '
        inst_sge += '-noremote -auto ./%s' % self.SGE_CONF
        node.ssh.execute(inst_sge, silent=True, only_printable=True)
        if exec_host:
            num_slots = self.slots_per_host
            if num_slots is None:
                num_slots = node.num_processors
            node.ssh.execute("qconf -aattr hostgroup hostlist %s @allhosts" %
                             node.alias)
            node.ssh.execute('qconf -aattr queue slots "[%s=%d]" all.q' %
                             (node.alias, num_slots))

    def _sge_path(self, path):
        return posixpath.join(self.SGE_ROOT, path)

    def _disable_add_queue(self):
        """
        Disables the install script from automatically adding the exec host to
        the queue with slots=num_cpus so that this plugin can customize the
        number of slots *before* the node is available to accept jobs.
        """
        master = self._master
        master.ssh.execute("cd %s && sed 's/AddQueue/#AddQueue/g' inst_sge > "
                           "%s" % (self.SGE_ROOT, self.SGE_INST))
        master.ssh.chmod(0755, self._sge_path(self.SGE_INST))

    def _setup_sge(self):
        """
        Install Sun Grid Engine with a default parallel environment on
        StarCluster
        """
        master = self._master
        if not master.ssh.isdir(self.SGE_ROOT):
            # copy fresh sge installation files to SGE_ROOT
            master.ssh.execute('cp -r %s %s' % (self.SGE_FRESH, self.SGE_ROOT))
            master.ssh.execute('chown -R %(user)s:%(user)s %(sge_root)s' %
                               {'user': self._user, 'sge_root': self.SGE_ROOT})
        self._disable_add_queue()
        self._setup_nfs(self.nodes, export_paths=[self.SGE_ROOT],
                        start_server=False)
        # setup sge auto install file
        default_cell = self._sge_path('default')
        if master.ssh.isdir(default_cell):
            log.info("Removing previous SGE installation...")
            master.ssh.execute('rm -rf %s' % default_cell)
            master.ssh.execute('exportfs -fr')
        admin_hosts = ' '.join(map(lambda n: n.alias, self._nodes))
        submit_hosts = admin_hosts
        exec_hosts = admin_hosts
        sge_conf = master.ssh.remote_file(self._sge_path(self.SGE_CONF), "w")
        conf = sge.sgeinstall_template % dict(admin_hosts=admin_hosts,
                                              submit_hosts=submit_hosts,
                                              exec_hosts=exec_hosts)
        sge_conf.write(conf)
        sge_conf.close()
        log.info("Installing Sun Grid Engine...")
        self._inst_sge(master, exec_host=self.master_is_exec_host)
        # set all.q shell to bash
        master.ssh.execute('qconf -mattr queue shell "/bin/bash" all.q')
        for node in self.nodes:
            self.pool.simple_job(self._add_to_sge, (node,), jobid=node.alias)
        self.pool.wait(numtasks=len(self.nodes))
        self._create_sge_pe()

    def _remove_from_sge(self, node):
        master = self._master
        master.ssh.execute('qconf -dattr hostgroup hostlist %s @allhosts' %
                           node.alias)
        master.ssh.execute('qconf -purge queue slots all.q@%s' % node.alias)
        master.ssh.execute('qconf -dconf %s' % node.alias)
        master.ssh.execute('qconf -de %s' % node.alias)
        node.ssh.execute('pkill -9 sge_execd')
        nodes = filter(lambda n: n.alias != node.alias, self._nodes)
        self._create_sge_pe(nodes=nodes)

    def run(self, nodes, master, user, user_shell, volumes):
        if not master.ssh.isdir(self.SGE_FRESH):
            log.error("SGE is not installed on this AMI, skipping...")
            return
        log.info("Configuring SGE...")
        self._nodes = nodes
        self._master = master
        self._user = user
        self._user_shell = user_shell
        self._volumes = volumes
        self._setup_sge()

    def on_add_node(self, node, nodes, master, user, user_shell, volumes):
        self._nodes = nodes
        self._master = master
        self._user = user
        self._user_shell = user_shell
        self._volumes = volumes
        log.info("Adding %s to SGE" % node.alias)
        self._setup_nfs(nodes=[node], export_paths=[self.SGE_ROOT],
                        start_server=False)
        self._add_sge_admin_host(node)
        self._add_sge_submit_host(node)
        self._add_to_sge(node)
        self._create_sge_pe()

    def on_remove_node(self, node, nodes, master, user, user_shell, volumes):
        self._nodes = nodes
        self._master = master
        self._user = user
        self._user_shell = user_shell
        self._volumes = volumes
        log.info("Removing %s from SGE" % node.alias)
        self._remove_from_sge(node)
        self._remove_nfs_exports(node)

########NEW FILE########
__FILENAME__ = tmux
# Copyright 2009-2014 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

from starcluster import utils
from starcluster import exception
from starcluster import clustersetup
from starcluster.logger import log


class TmuxControlCenter(clustersetup.DefaultClusterSetup):
    """
    Starts a TMUX session on StarCluster configured with split panes for all
    nodes. This allows you to interactively run commands on all nodes and see
    all the output at once.
    """
    _layouts = ['even-horizontal', 'even-vertical', 'main-horizontal',
                'main-vertical', 'tiled']

    def __init__(self, envname="starcluster"):
        self._envname = envname
        self._nodes = None
        self._master = None
        self._user = None
        self._user_shell = None
        self._volumes = None

    def _supports_layout(self, node, envname, layout, window=''):
        if layout not in self._layouts:
            raise exception.PluginError("unknown layout (options: %s)" %
                                        ", ".join(self._layouts))
        return self._select_layout(node, envname, layout, window) == 0

    def _select_layout(self, node, envname, layout="main-vertical", window=''):
        if layout not in self._layouts:
            raise exception.PluginError("unknown layout (options: %s)" %
                                        ", ".join(self._layouts))
        cmd = 'tmux select-layout -t %s:%s %s'
        return node.ssh.get_status(cmd % (envname, window, layout))

    def _resize_pane(self, node, envname, pane, units, up=False):
        upordown = '-D %s' % units
        if up:
            upordown = '-D %s' % units
        cmd = 'tmux resize-pane -t %s:%s %s' % (envname, pane, upordown)
        return node.ssh.execute(cmd)

    def _split_window(self, node, envname, window='', vertical=False):
        cmd = 'tmux split-window'
        if vertical:
            cmd += ' -h'
        return node.ssh.execute('%s -t %s:%s' % (cmd, envname, window))

    def _rename_window(self, node, envname, window, name):
        cmd = 'tmux rename-window -t %s:%s %s' % (envname, window, name)
        return node.ssh.execute(cmd)

    def _has_session(self, node, envname):
        status = node.ssh.get_status('tmux has-session -t %s' % envname)
        return status == 0

    def _send_keys(self, node, envname, cmd, window=''):
        node.ssh.execute('tmux send-keys -t %s:%s "%s"' % (envname, window,
                                                           cmd))
        node.ssh.execute('tmux send-keys -t %s:%s "Enter"' % (envname, window))

    def _new_session(self, node, envname):
        node.ssh.execute('tmux new-session -d -s %s' % envname)

    def _kill_session(self, node, envname):
        node.ssh.execute('tmux kill-session -t %s' % envname)

    def _kill_window(self, node, envname, window):
        node.ssh.execute('tmux kill-window -t %s:%s' % (envname, window))

    def _new_window(self, node, envname, title):
        node.ssh.execute('tmux new-window -n %s -t %s:' % (title, envname))

    def _select_window(self, node, envname, window=''):
        node.ssh.execute('tmux select-window -t %s:%s' % (envname, window))

    def _select_pane(self, node, envname, window, pane):
        node.ssh.execute('tmux select-pane -t %s:%s.%s' %
                         (envname, window, pane))

    def create_session(self, node, envname, num_windows=5):
        if not self._has_session(node, envname):
            self._new_session(node, envname)
        for i in range(1, num_windows):
            self._new_window(node, envname, i)

    def setup_tmuxcc(self, client=None, nodes=None, user='root',
                     layout='tiled'):
        log.info("Creating TMUX Control Center for user '%s'" % user)
        client = client or self._master
        nodes = nodes or self._nodes
        envname = self._envname
        orig_user = client.ssh._username
        if orig_user != user:
            client.ssh.connect(username=user)
        chunks = [chunk for chunk in utils.chunk_list(nodes, items=8)]
        num_windows = len(chunks) + len(nodes)
        if len(nodes) == 0:
            log.error("Cluster has no nodes, exiting...")
            return
        self.create_session(client, envname, num_windows=num_windows)
        if len(nodes) == 1 and client == nodes[0]:
            return
        if not self._supports_layout(client, envname, layout, window=0):
            log.warn("failed to select layout '%s', defaulting to "
                     "'main-vertical'" % layout)
            layout = "main-vertical"
            status = self._select_layout(client, envname, layout, window=0)
            if status != 0:
                raise exception.PluginError("failed to set a layout")
        for i, chunk in enumerate(chunks):
            self._rename_window(client, envname, i, 'all%s' % i)
            for j, node in enumerate(chunk):
                if j != 0:
                    self._split_window(client, envname, i)
                self._select_layout(client, envname, window=i, layout=layout)
                if node.alias != client.alias:
                    self._send_keys(client, envname, cmd='ssh %s' % node.alias,
                                    window="%d.%d" % (i, j))
        for i, node in enumerate(nodes):
            window = i + len(chunks)
            self._rename_window(client, envname, window, node.alias)
            if node.alias != client.alias:
                self._send_keys(client, envname, cmd='ssh %s' % node.alias,
                                window=window)
        self._select_window(client, envname, window=0)
        self._select_pane(client, envname, window=0, pane=0)
        if orig_user != user:
            client.ssh.connect(username=orig_user)

    def add_to_utmp_group(self, client, user):
        """
        Adds user (if exists) to 'utmp' group (if exists)
        """
        try:
            client.add_user_to_group(user, 'utmp')
        except exception.BaseException:
            pass

    def run(self, nodes, master, user, user_shell, volumes):
        log.info("Starting TMUX Control Center...")
        self._nodes = nodes
        self._master = master
        self._user = user
        self._user_shell = user_shell
        self._volumes = volumes
        self.add_to_utmp_group(master, user)
        self.setup_tmuxcc(user='root')
        self.setup_tmuxcc(user=user)

    def _add_to_tmuxcc(self, client, node, user='root'):
        orig_user = client.ssh._username
        if orig_user != user:
            client.ssh.connect(username=user)
        self._new_window(client, self._envname, node.alias)
        self._send_keys(client, self._envname, cmd='ssh %s' % node.alias,
                        window=node.alias)
        if orig_user != user:
            client.ssh.connect(username=orig_user)

    def _remove_from_tmuxcc(self, client, node, user='root'):
        orig_user = client.ssh._username
        if orig_user != user:
            client.ssh.connect(username=user)
        self._kill_window(client, self._envname, node.alias)
        if orig_user != user:
            client.ssh.connect(username=orig_user)

    def on_add_node(self, node, nodes, master, user, user_shell, volumes):
        log.info("Adding %s to TMUX Control Center" % node.alias)
        self._add_to_tmuxcc(master, node, user='root')
        self._add_to_tmuxcc(master, node, user=user)

    def on_remove_node(self, node, nodes, master, user, user_shell, volumes):
        log.info("Removing %s from TMUX Control Center" % node.alias)
        self._remove_from_tmuxcc(master, node, user='root')
        self._remove_from_tmuxcc(master, node, user=user)

########NEW FILE########
__FILENAME__ = users
# Copyright 2009-2014 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

import os
import posixpath

from starcluster import utils
from starcluster import static
from starcluster import exception
from starcluster import clustersetup
from starcluster.logger import log


class CreateUsers(clustersetup.DefaultClusterSetup):
    """
    Plugin for creating one or more cluster users
    """

    DOWNLOAD_KEYS_DIR = os.path.join(static.STARCLUSTER_CFG_DIR, 'user_keys')
    BATCH_USER_FILE = "/root/.users/users.txt"

    def __init__(self, num_users=None, usernames=None, download_keys=None,
                 download_keys_dir=None):
        if usernames:
            usernames = [user.strip() for user in usernames.split(',')]
        if num_users:
            try:
                num_users = int(num_users)
            except ValueError:
                raise exception.BaseException("num_users must be an integer")
        elif usernames:
            num_users = len(usernames)
        else:
            raise exception.BaseException(
                "you must provide num_users or usernames or both")
        if usernames and num_users and len(usernames) != num_users:
            raise exception.BaseException(
                "only %d usernames provided - %d required" %
                (len(usernames), num_users))
        self._num_users = num_users
        if not usernames:
            usernames = ['user%.3d' % i for i in range(1, num_users + 1)]
        self._usernames = usernames
        self._download_keys = str(download_keys).lower() == "true"
        self._download_keys_dir = download_keys_dir or self.DOWNLOAD_KEYS_DIR
        super(CreateUsers, self).__init__()

    def run(self, nodes, master, user, user_shell, volumes):
        self._nodes = nodes
        self._master = master
        self._user = user
        self._user_shell = user_shell
        self._volumes = volumes
        log.info("Creating %d cluster users" % self._num_users)
        newusers = self._get_newusers_batch_file(master, self._usernames,
                                                 user_shell)
        for node in nodes:
            self.pool.simple_job(node.ssh.execute,
                                 ("echo -n '%s' | newusers" % newusers),
                                 jobid=node.alias)
        self.pool.wait(numtasks=len(nodes))
        log.info("Configuring passwordless ssh for %d cluster users" %
                 self._num_users)
        pbar = self.pool.progress_bar.reset()
        pbar.maxval = self._num_users
        for i, user in enumerate(self._usernames):
            master.generate_key_for_user(user, auth_new_key=True,
                                         auth_conn_key=True)
            master.add_to_known_hosts(user, nodes)
            pbar.update(i + 1)
        pbar.finish()
        self._setup_scratch(nodes, self._usernames)
        if self._download_keys:
            self._download_user_keys(master, self._usernames)

    def _download_user_keys(self, master, usernames):
        pardir = posixpath.dirname(self.BATCH_USER_FILE)
        bfile = posixpath.basename(self.BATCH_USER_FILE)
        if not master.ssh.isdir(pardir):
            master.ssh.makedirs(pardir)
        log.info("Tarring all SSH keys for cluster users...")
        for user in usernames:
            master.ssh.execute(
                "cp /home/%(user)s/.ssh/id_rsa %(keydest)s" %
                dict(user=user, keydest=posixpath.join(pardir, user + '.rsa')))
        cluster_tag = master.cluster_groups[0].name.replace(
            static.SECURITY_GROUP_PREFIX, '')
        tarfile = "%s-%s.tar.gz" % (cluster_tag, master.region.name)
        master.ssh.execute("tar -C %s -czf ~/%s . --exclude=%s" %
                           (pardir, tarfile, bfile))
        if not os.path.exists(self._download_keys_dir):
            os.makedirs(self._download_keys_dir)
        log.info("Copying cluster users SSH keys to: %s" %
                 os.path.join(self._download_keys_dir, tarfile))
        master.ssh.get(tarfile, self._download_keys_dir)
        master.ssh.unlink(tarfile)

    def _get_newusers_batch_file(self, master, usernames, shell,
                                 batch_file=None):
        batch_file = batch_file or self.BATCH_USER_FILE
        if master.ssh.isfile(batch_file):
            bfile = master.ssh.remote_file(batch_file, 'r')
            bfilecontents = bfile.read()
            bfile.close()
            return bfilecontents
        bfilecontents = ''
        tmpl = "%(username)s:%(password)s:%(uid)d:%(gid)d:"
        tmpl += "Cluster user account %(username)s:"
        tmpl += "/home/%(username)s:%(shell)s\n"
        shpath = master.ssh.which(shell)[0]
        ctx = dict(shell=shpath)
        base_uid, base_gid = self._get_max_unused_user_id()
        for user in usernames:
            home_folder = '/home/%s' % user
            if master.ssh.path_exists(home_folder):
                s = master.ssh.stat(home_folder)
                uid = s.st_uid
                gid = s.st_gid
            else:
                uid = base_uid
                gid = base_gid
                base_uid += 1
                base_gid += 1
            passwd = utils.generate_passwd(8)
            ctx.update(username=user, uid=uid, gid=gid, password=passwd)
            bfilecontents += tmpl % ctx
        pardir = posixpath.dirname(batch_file)
        if not master.ssh.isdir(pardir):
            master.ssh.makedirs(pardir)
        bfile = master.ssh.remote_file(batch_file, 'w')
        bfile.write(bfilecontents)
        bfile.close()
        return bfilecontents

    def on_add_node(self, node, nodes, master, user, user_shell, volumes):
        self._nodes = nodes
        self._master = master
        self._user = user
        self._user_shell = user_shell
        self._volumes = volumes
        log.info("Creating %d users on %s" % (self._num_users, node.alias))
        newusers = self._get_newusers_batch_file(master, self._usernames,
                                                 user_shell)
        node.ssh.execute("echo -n '%s' | newusers" % newusers)
        log.info("Adding %s to known_hosts for %d users" %
                 (node.alias, self._num_users))
        pbar = self.pool.progress_bar.reset()
        pbar.maxval = self._num_users
        for i, user in enumerate(self._usernames):
            master.add_to_known_hosts(user, [node])
            pbar.update(i + 1)
        pbar.finish()
        self._setup_scratch(nodes=[node], users=self._usernames)

    def on_remove_node(self, node, nodes, master, user, user_shell, volumes):
        raise NotImplementedError('on_remove_node method not implemented')

########NEW FILE########
__FILENAME__ = xvfb
# Copyright 2009-2014 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

from starcluster import clustersetup
from starcluster.logger import log


class XvfbSetup(clustersetup.DefaultClusterSetup):
    """
    Installs, configures, and sets up an Xvfb server
    (thanks to Adam Marsh for his contribution)
    """
    def _install_xvfb(self, node):
        node.apt_install('xvfb')

    def _launch_xvfb(self, node):
        node.ssh.execute('screen -d -m Xvfb :1 -screen 0 1024x768x16')
        profile = node.ssh.remote_file('/etc/profile.d/scxvfb.sh', 'w')
        profile.write('export DISPLAY=":1"')
        profile.close()

    def run(self, nodes, master, user, user_shell, volumes):
        log.info("Installing Xvfb on all nodes")
        for node in nodes:
            self.pool.simple_job(self._install_xvfb, (node), jobid=node.alias)
        self.pool.wait(numtasks=len(nodes))
        log.info("Launching Xvfb Server on all nodes")
        for node in nodes:
            self.pool.simple_job(self._launch_xvfb, (node), jobid=node.alias)
        self.pool.wait(numtasks=len(nodes))

    def _terminate(self, nodes):
        for node in nodes:
            self.pool.simple_job(node.ssh.execute, ('pkill Xvfb'),
                                 jobid=node.alias)
        self.pool.wait(numtasks=len(nodes))

    def on_add_node(self, new_node, nodes, master, user, user_shell, volumes):
        log.info("Installing Xvfb on %s" % new_node.alias)
        self._install_xvfb(new_node)
        log.info("Launching Xvfb Server on %s" % new_node.alias)
        self._launch_xvfb(new_node)

    def on_remove_node(self, node, nodes, master, user, user_shell, volumes):
        raise NotImplementedError('on_remove_node method not implemented')

########NEW FILE########
__FILENAME__ = progressbar
# -*- coding: iso-8859-1 -*-
#
# progressbar  - Text progressbar library for python.
# Copyright (c) 2005 Nilton Volpato
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA


"""Text progressbar library for python.

This library provides a text mode progressbar. This is typically used
to display the progress of a long running operation, providing a
visual clue that processing is underway.

The ProgressBar class manages the progress, and the format of the line
is given by a number of widgets. A widget is an object that may
display differently depending on the state of the progress. There are
three types of widget:
- a string, which always shows itself;
- a ProgressBarWidget, which may return a different value every time
it's update method is called; and
- a ProgressBarWidgetHFill, which is like ProgressBarWidget, except it
expands to fill the remaining width of the line.

The progressbar module is very easy to use, yet very powerful. And
automatically supports features like auto-resizing when available.
"""

__author__ = "Nilton Volpato"
__author_email__ = "first-name dot last-name @ gmail.com"
__date__ = "2006-05-07"
__version__ = "2.2"

# Changelog
#
# 2006-05-07: v2.2 fixed bug in windows
# 2005-12-04: v2.1 autodetect terminal width, added start method
# 2005-12-04: v2.0 everything is now a widget (wow!)
# 2005-12-03: v1.0 rewrite using widgets
# 2005-06-02: v0.5 rewrite
# 2004-??-??: v0.1 first version

import sys
import time
from array import array
try:
    from fcntl import ioctl
    import termios
except ImportError:
    pass
import signal


class ProgressBarWidget(object):
    """This is an element of ProgressBar formatting.

    The ProgressBar object will call it's update value when an update
    is needed. It's size may change between call, but the results will
    not be good if the size changes drastically and repeatedly.
    """
    def update(self, pbar):
        """Returns the string representing the widget.

        The parameter pbar is a reference to the calling ProgressBar,
        where one can access attributes of the class for knowing how
        the update must be made.

        At least this function must be overridden."""
        pass


class ProgressBarWidgetHFill(object):
    """This is a variable width element of ProgressBar formatting.

    The ProgressBar object will call it's update value, informing the
    width this object must the made. This is like TeX \\hfill, it will
    expand to fill the line. You can use more than one in the same
    line, and they will all have the same width, and together will
    fill the line.
    """
    def update(self, pbar, width):
        """Returns the string representing the widget.

        The parameter pbar is a reference to the calling ProgressBar,
        where one can access attributes of the class for knowing how
        the update must be made. The parameter width is the total
        horizontal width the widget must have.

        At least this function must be overridden."""
        pass


class ETA(ProgressBarWidget):
    "Widget for the Estimated Time of Arrival"
    def format_time(self, seconds):
        return time.strftime('%H:%M:%S', time.gmtime(seconds))

    def update(self, pbar):
        if pbar.currval == 0:
            return 'ETA:  --:--:--'
        elif pbar.finished:
            return 'Time: %s' % self.format_time(pbar.seconds_elapsed)
        else:
            elapsed = pbar.seconds_elapsed
            eta = elapsed * pbar.maxval / pbar.currval - elapsed
            return 'ETA:  %s' % self.format_time(eta)


class FileTransferSpeed(ProgressBarWidget):
    "Widget for showing the transfer speed (useful for file transfers)."
    def __init__(self):
        self.fmt = '%6.2f %s'
        self.units = ['B', 'K', 'M', 'G', 'T', 'P']

    def update(self, pbar):
        if pbar.seconds_elapsed < 2e-6:  # == 0:
            bps = 0.0
        else:
            bps = float(pbar.currval) / pbar.seconds_elapsed
        spd = bps
        for u in self.units:
            if spd < 1000:
                break
            spd /= 1000
        return self.fmt % (spd, u + '/s')


class RotatingMarker(ProgressBarWidget):
    "A rotating marker for filling the bar of progress."
    def __init__(self, markers='|/-\\'):
        self.markers = markers
        self.curmark = -1

    def update(self, pbar):
        if pbar.finished:
            return self.markers[0]
        self.curmark = (self.curmark + 1) % len(self.markers)
        return self.markers[self.curmark]


class Percentage(ProgressBarWidget):
    "Just the percentage done."
    def update(self, pbar):
        return '%3d%%' % pbar.percentage()


class Fraction(ProgressBarWidget):
    "Just the fraction done."
    def update(self, pbar):
        return "%d/%d" % (pbar.currval, pbar.maxval)


class Bar(ProgressBarWidgetHFill):
    "The bar of progress. It will stretch to fill the line."
    def __init__(self, marker='#', left='|', right='|'):
        self.marker = marker
        self.left = left
        self.right = right

    def _format_marker(self, pbar):
        if isinstance(self.marker, (str, unicode)):
            return self.marker
        else:
            return self.marker.update(pbar)

    def update(self, pbar, width):
        percent = pbar.percentage()
        cwidth = width - len(self.left) - len(self.right)
        marked_width = int(percent * cwidth / 100)
        m = self._format_marker(pbar)
        bar = (self.left + (m * marked_width).ljust(cwidth) + self.right)
        return bar


class ReverseBar(Bar):
    "The reverse bar of progress, or bar of regress. :)"
    def update(self, pbar, width):
        percent = pbar.percentage()
        cwidth = width - len(self.left) - len(self.right)
        marked_width = int(percent * cwidth / 100)
        m = self._format_marker(pbar)
        bar = (self.left + (m * marked_width).rjust(cwidth) + self.right)
        return bar

default_widgets = [Percentage(), ' ', Bar()]


class ProgressBarBase(object):
    """ Base progress bar class, independent of UI
    """
    def __init__(self, maxval=100, force_update=False):
        assert maxval > 0
        self.maxval = maxval
        self.force_update = force_update

        self.currval = 0
        self.finished = False
        self.prev_percentage = -1
        self.start_time = None
        self.seconds_elapsed = 0

    def percentage(self):
        "Returns the percentage of the progress."
        return self.currval * 100.0 / self.maxval

    def reset(self):
        if not self.finished and self.start_time:
            self.finish()
        self.finished = False
        self.currval = 0
        self.start_time = None
        self.seconds_elapsed = None
        self.prev_percentage = None
        return self

    def _need_update(self):
        if self.force_update:
            return True
        return int(self.percentage()) != int(self.prev_percentage)

    def update(self, value):
        "Updates the progress bar to a new value."
        assert 0 <= value <= self.maxval
        self.currval = value
        if not self._need_update() or self.finished:
            return
        if not self.start_time:
            self.start_time = time.time()
        self.seconds_elapsed = time.time() - self.start_time
        self.prev_percentage = self.percentage()
        if value == self.maxval:
            self.finished = True

    def start(self):
        """Start measuring time, and prints the bar at 0%.

        It returns self so you can use it like this:
        >>> pbar = ProgressBar().start()
        >>> for i in xrange(100):
        ...    # do something
        ...    pbar.update(i+1)
        ...
        >>> pbar.finish()
        """
        self.update(0)
        return self

    def finish(self):
        """Used to tell the progress is finished."""
        self.update(self.maxval)


class ProgressBar(ProgressBarBase):
    """This is the ProgressBar class, it updates and prints the bar.

    The term_width parameter may be an integer. Or None, in which case
    it will try to guess it, if it fails it will default to 80 columns.

    The simple use is like this:
    >>> pbar = ProgressBar().start()
    >>> for i in xrange(100):
    ...    # do something
    ...    pbar.update(i+1)
    ...
    >>> pbar.finish()

    But anything you want to do is possible (well, almost anything).
    You can supply different widgets of any type in any order. And you
    can even write your own widgets! There are many widgets already
    shipped and you should experiment with them.

    When implementing a widget update method you may access any
    attribute or function of the ProgressBar object calling the
    widget's update method. The most important attributes you would
    like to access are:
    - currval: current value of the progress, 0 <= currval <= maxval
    - maxval: maximum (and final) value of the progress
    - finished: True if the bar is have finished (reached 100%), False o/w
    - start_time: first time update() method of ProgressBar was called
    - seconds_elapsed: seconds elapsed since start_time
    - percentage(): percentage of the progress (this is a method)
    """
    def __init__(self, maxval=100, widgets=default_widgets, term_width=79,
                 fd=sys.stderr, force_update=False):
        super(ProgressBar, self).__init__(maxval, force_update=force_update)
        self.widgets = widgets
        self.fd = fd
        self.signal_set = False
        if term_width is None:
            try:
                self.handle_resize(None, None)
                signal.signal(signal.SIGWINCH, self.handle_resize)
                self.signal_set = True
            except:
                self.term_width = 79
        else:
            self.term_width = term_width

    def handle_resize(self, signum, frame):
        h, w = array('h', ioctl(self.fd, termios.TIOCGWINSZ, '\0' * 8))[:2]
        self.term_width = w

    def _format_widgets(self):
        r = []
        hfill_inds = []
        num_hfill = 0
        currwidth = 0
        for i, w in enumerate(self.widgets):
            if isinstance(w, ProgressBarWidgetHFill):
                r.append(w)
                hfill_inds.append(i)
                num_hfill += 1
            elif isinstance(w, (str, unicode)):
                r.append(w)
                currwidth += len(w)
            else:
                weval = w.update(self)
                currwidth += len(weval)
                r.append(weval)
        for iw in hfill_inds:
            r[iw] = r[iw].update(self,
                                 (self.term_width - currwidth) / num_hfill)
        return r

    def _format_line(self):
        return ''.join(self._format_widgets()).ljust(self.term_width)

    def update(self, value):
        "Updates the progress bar to a new value."
        super(ProgressBar, self).update(value)
        term = '\r' if value != self.maxval else '\n'
        self.fd.write(self._format_line() + term)

    def finish(self):
        """Used to tell the progress is finished."""
        super(ProgressBar, self).finish()
        if self.signal_set:
            signal.signal(signal.SIGWINCH, signal.SIG_DFL)


def example1():
    widgets = ['Test: ', Percentage(), ' ', Bar(marker=RotatingMarker()),
               ' ', ETA(), ' ', FileTransferSpeed()]
    pbar = ProgressBar(widgets=widgets, maxval=10000000).start()
    for i in range(1000000):
        # do something
        pbar.update(10 * i + 1)
    pbar.finish()
    return pbar


def example2():
    class CrazyFileTransferSpeed(FileTransferSpeed):
        "It's bigger between 45 and 80 percent"
        def update(self, pbar):
            if 45 < pbar.percentage() < 80:
                return 'Bigger Now ' + FileTransferSpeed.update(self, pbar)
            else:
                return FileTransferSpeed.update(self, pbar)

    widgets = [CrazyFileTransferSpeed(), ' <<<',
               Bar(), '>>> ', Percentage(), ' ', ETA()]
    pbar = ProgressBar(widgets=widgets, maxval=10000000)
    # maybe do something
    pbar.start()
    for i in range(2000000):
        # do something
        pbar.update(5 * i + 1)
    pbar.finish()
    return pbar


def example3():
    widgets = [Bar('>'), ' ', ETA(), ' ', ReverseBar('<')]
    pbar = ProgressBar(widgets=widgets, maxval=10000000).start()
    for i in range(1000000):
        # do something
        pbar.update(10 * i + 1)
    pbar.finish()
    return pbar


def example4():
    widgets = ['Test: ', Percentage(), ' ',
               Bar(marker='0', left='[', right=']'),
               ' ', ETA(), ' ', FileTransferSpeed()]
    pbar = ProgressBar(widgets=widgets, maxval=500)
    pbar.start()
    for i in range(100, 500 + 1, 50):
        time.sleep(0.2)
        pbar.update(i)
    pbar.finish()
    return pbar


def example5():
    widgets = ['Test: ', Fraction(), ' ', Bar(marker=RotatingMarker()),
               ' ', ETA(), ' ', FileTransferSpeed()]
    pbar = ProgressBar(widgets=widgets, maxval=10, force_update=True).start()
    for i in range(1, 11):
        # do something
        time.sleep(0.5)
        pbar.update(i)
    pbar.finish()
    return pbar


def main():
    example1()
    print
    example2()
    print
    example3()
    print
    example4()
    print
    example5()
    print

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = spinner
# Copyright 2009-2014 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

import sys
import time
from threading import Thread


class Spinner(Thread):
    # Set the screen position of the spinner (chars from the left).
    spin_screen_pos = 1
    # Set the current index position in the spinner character list.
    char_index_pos = 0
    # Set the time between character changes in the spinner.
    sleep_time = 1
    # Set the spinner type: 0-3
    spin_type = 2

    def __init__(self, type=spin_type):
        Thread.__init__(self)
        self.setDaemon(True)
        self.stop_spinner = False
        self.stopped = False
        if type == 0:
            self.char = ['O', 'o', '-', 'o', '0']
        elif type == 1:
            self.char = ['.', 'o', 'O', 'o', '.']
        elif type == 2:
            self.char = ['|', '/', '-', '\\', '-']
        else:
            self.char = ['*', '#', '@', '%', '+']
        self.len = len(self.char)

    def Print(self, crnt):
        str, crnt = self.curr(crnt)
        sys.stdout.write("\b \b%s" % str)
        sys.stdout.flush()  # Flush stdout to get output before sleeping!
        time.sleep(self.sleep_time)
        return crnt

    def curr(self, crnt):
        """
        Iterator for the character list position
        """
        if crnt == 4:
            return self.char[4], 0
        elif crnt == 0:
            return self.char[0], 1
        else:
            test = crnt
            crnt += 1
        return self.char[test], crnt

    def done(self):
        sys.stdout.write("\b \b\n")

    def stop(self):
        self.stop_spinner = True
        while not self.stopped:
            time.sleep(0.5)  # give time for run to get the message

    def run(self):
        # the comma keeps print from ending with a newline.
        print " " * self.spin_screen_pos,
        while True:
            if self.stop_spinner:
                self.done()
                self.stopped = True
                return
            self.char_index_pos = self.Print(self.char_index_pos)

    def test(self, sleep=3.4):
        print 'Waiting for process...',
        self.start()
        time.sleep(sleep)
        self.stop()
        print 'Process is finished...'

if __name__ == "__main__":
    for i in range(0, 10):
        s = Spinner()
        s.test(sleep=float('3.' + str(i)))

########NEW FILE########
__FILENAME__ = sshutils
# Copyright 2009-2014 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

import os
import re
import sys
import stat
import glob
import atexit
import string
import socket
import fnmatch
import hashlib
import warnings
import posixpath

import scp
import paramiko
from Crypto.PublicKey import RSA
from Crypto.PublicKey import DSA

# windows does not have termios...
try:
    import termios
    import tty
    HAS_TERMIOS = True
except ImportError:
    HAS_TERMIOS = False

from starcluster import exception
from starcluster import progressbar
from starcluster.logger import log


class SSHClient(object):
    """
    Establishes an SSH connection to a remote host using either password or
    private key authentication. Once established, this object allows executing
    commands, copying files to/from the remote host, various file querying
    similar to os.path.*, and much more.
    """

    def __init__(self,
                 host,
                 username=None,
                 password=None,
                 private_key=None,
                 private_key_pass=None,
                 compress=False,
                 port=22,
                 timeout=30):
        self._host = host
        self._port = port
        self._pkey = None
        self._username = username or os.environ['LOGNAME']
        self._password = password
        self._timeout = timeout
        self._sftp = None
        self._scp = None
        self._transport = None
        self._progress_bar = None
        self._compress = compress
        if private_key:
            self._pkey = self.load_private_key(private_key, private_key_pass)
        elif not password:
            raise exception.SSHNoCredentialsError()
        self._glob = SSHGlob(self)
        self.__last_status = None
        atexit.register(self.close)

    def load_private_key(self, private_key, private_key_pass=None):
        # Use Private Key.
        log.debug('loading private key %s' % private_key)
        if private_key.endswith('rsa') or private_key.count('rsa'):
            pkey = self._load_rsa_key(private_key, private_key_pass)
        elif private_key.endswith('dsa') or private_key.count('dsa'):
            pkey = self._load_dsa_key(private_key, private_key_pass)
        else:
            log.debug(
                "specified key does not end in either rsa or dsa, trying both")
            pkey = self._load_rsa_key(private_key, private_key_pass)
            if pkey is None:
                pkey = self._load_dsa_key(private_key, private_key_pass)
        return pkey

    def connect(self, host=None, username=None, password=None,
                private_key=None, private_key_pass=None, port=None, timeout=30,
                compress=None):
        host = host or self._host
        username = username or self._username
        password = password or self._password
        compress = compress or self._compress
        port = port if port is not None else self._port
        pkey = self._pkey
        if private_key:
            pkey = self.load_private_key(private_key, private_key_pass)
        log.debug("connecting to host %s on port %d as user %s" % (host, port,
                                                                   username))
        try:
            sock = self._get_socket(host, port)
            transport = paramiko.Transport(sock)
            transport.banner_timeout = timeout
        except socket.error:
            raise exception.SSHConnectionError(host, port)
        # Enable/disable compression
        transport.use_compression(compress)
        # Authenticate the transport.
        try:
            transport.connect(username=username, pkey=pkey, password=password)
        except paramiko.AuthenticationException:
            raise exception.SSHAuthException(username, host)
        except paramiko.SSHException, e:
            msg = e.args[0]
            raise exception.SSHError(msg)
        except socket.error:
            raise exception.SSHConnectionError(host, port)
        except EOFError:
            raise exception.SSHConnectionError(host, port)
        except Exception, e:
            raise exception.SSHError(str(e))
        self.close()
        self._transport = transport
        try:
            assert self.sftp is not None
        except paramiko.SFTPError, e:
            if 'Garbage packet received' in e:
                log.debug("Garbage packet received", exc_info=True)
                raise exception.SSHAccessDeniedViaAuthKeys(username)
            raise
        return self

    @property
    def transport(self):
        """
        This property attempts to return an active SSH transport
        """
        if not self._transport or not self._transport.is_active():
            self.connect(self._host, self._username, self._password,
                         port=self._port, timeout=self._timeout,
                         compress=self._compress)
        return self._transport

    def get_server_public_key(self):
        return self.transport.get_remote_server_key()

    def is_active(self):
        if self._transport:
            return self._transport.is_active()
        return False

    def _get_socket(self, hostname, port):
        addrinfo = socket.getaddrinfo(hostname, port, socket.AF_UNSPEC,
                                      socket.SOCK_STREAM)
        for (family, socktype, proto, canonname, sockaddr) in addrinfo:
            if socktype == socket.SOCK_STREAM:
                af = family
                break
            else:
                raise exception.SSHError(
                    'No suitable address family for %s' % hostname)
        sock = socket.socket(af, socket.SOCK_STREAM)
        sock.settimeout(self._timeout)
        sock.connect((hostname, port))
        return sock

    def _load_rsa_key(self, private_key, private_key_pass=None):
        private_key_file = os.path.expanduser(private_key)
        try:
            rsa_key = get_rsa_key(key_location=private_key_file,
                                  passphrase=private_key_pass)
            log.debug("Using private key %s (RSA)" % private_key)
            return rsa_key
        except (paramiko.SSHException, exception.SSHError):
            log.error('invalid rsa key or passphrase specified')

    def _load_dsa_key(self, private_key, private_key_pass=None):
        private_key_file = os.path.expanduser(private_key)
        try:
            dsa_key = get_dsa_key(key_location=private_key_file,
                                  passphrase=private_key_pass)
            log.info("Using private key %s (DSA)" % private_key)
            return dsa_key
        except (paramiko.SSHException, exception.SSHError):
            log.error('invalid dsa key or passphrase specified')

    @property
    def sftp(self):
        """Establish the SFTP connection."""
        if not self._sftp or self._sftp.sock.closed:
            log.debug("creating sftp connection")
            self._sftp = paramiko.SFTPClient.from_transport(self.transport)
        return self._sftp

    @property
    def scp(self):
        """Initialize the SCP client."""
        if not self._scp or not self._scp.transport.is_active():
            log.debug("creating scp connection")
            self._scp = scp.SCPClient(self.transport,
                                      progress=self._file_transfer_progress)
        return self._scp

    def generate_rsa_key(self):
        warnings.warn("This method is deprecated: please use "
                      "starcluster.sshutils.generate_rsa_key instead")
        return generate_rsa_key()

    def get_public_key(self, key):
        warnings.warn("This method is deprecated: please use "
                      "starcluster.sshutils.get_public_key instead")
        return get_public_key(key)

    def load_remote_rsa_key(self, remote_filename):
        """
        Returns paramiko.RSAKey object for an RSA key located on the remote
        machine
        """
        rfile = self.remote_file(remote_filename, 'r')
        key = get_rsa_key(key_file_obj=rfile)
        rfile.close()
        return key

    def makedirs(self, path, mode=0755):
        """
        Same as os.makedirs - makes a new directory and automatically creates
        all parent directories if they do not exist.

        mode specifies unix permissions to apply to the new dir
        """
        head, tail = posixpath.split(path)
        if not tail:
            head, tail = posixpath.split(head)
        if head and tail and not self.path_exists(head):
            try:
                self.makedirs(head, mode)
            except OSError, e:
                # be happy if someone already created the path
                if e.errno != os.errno.EEXIST:
                    raise
            # xxx/newdir/. exists if xxx/newdir exists
            if tail == posixpath.curdir:
                return
        self.mkdir(path, mode)

    def mkdir(self, path, mode=0755, ignore_failure=False):
        """
        Make a new directory on the remote machine

        If parent is True, create all parent directories that do not exist

        mode specifies unix permissions to apply to the new dir
        """
        try:
            return self.sftp.mkdir(path, mode)
        except IOError:
            if not ignore_failure:
                raise

    def get_remote_file_lines(self, remote_file, regex=None, matching=True):
        """
        Returns list of lines in a remote_file

        If regex is passed only lines that contain a pattern that matches
        regex will be returned

        If matching is set to False then only lines *not* containing a pattern
        that matches regex will be returned
        """
        f = self.remote_file(remote_file, 'r')
        flines = f.readlines()
        f.close()
        if regex is None:
            return flines
        r = re.compile(regex)
        lines = []
        for line in flines:
            match = r.search(line)
            if matching and match:
                lines.append(line)
            elif not matching and not match:
                lines.append(line)
        return lines

    def remove_lines_from_file(self, remote_file, regex):
        """
        Removes lines matching regex from remote_file
        """
        if regex in [None, '']:
            log.debug('no regex supplied...returning')
            return
        lines = self.get_remote_file_lines(remote_file, regex, matching=False)
        log.debug("new %s after removing regex (%s) matches:\n%s" %
                  (remote_file, regex, ''.join(lines)))
        f = self.remote_file(remote_file)
        f.writelines(lines)
        f.close()

    def unlink(self, remote_file):
        return self.sftp.unlink(remote_file)

    def remote_file(self, file, mode='w'):
        """
        Returns a remote file descriptor
        """
        rfile = self.sftp.open(file, mode)
        rfile.name = file
        return rfile

    def path_exists(self, path):
        """
        Test whether a remote path exists.
        Returns False for broken symbolic links
        """
        try:
            self.stat(path)
            return True
        except IOError:
            return False

    def lpath_exists(self, path):
        """
        Test whether a remote path exists.
        Returns True for broken symbolic links
        """
        try:
            self.lstat(path)
            return True
        except IOError:
            return False

    def chown(self, uid, gid, remote_path):
        """
        Set user (uid) and group (gid) owner for remote_path
        """
        return self.sftp.chown(remote_path, uid, gid)

    def chmod(self, mode, remote_path):
        """
        Apply permissions (mode) to remote_path
        """
        return self.sftp.chmod(remote_path, mode)

    def ls(self, path):
        """
        Return a list containing the names of the entries in the remote path.
        """
        return [posixpath.join(path, f) for f in self.sftp.listdir(path)]

    def glob(self, pattern):
        return self._glob.glob(pattern)

    def isdir(self, path):
        """
        Return true if the remote path refers to an existing directory.
        """
        try:
            s = self.stat(path)
        except IOError:
            return False
        return stat.S_ISDIR(s.st_mode)

    def isfile(self, path):
        """
        Return true if the remote path refers to an existing file.
        """
        try:
            s = self.stat(path)
        except IOError:
            return False
        return stat.S_ISREG(s.st_mode)

    def stat(self, path):
        """
        Perform a stat system call on the given remote path.
        """
        return self.sftp.stat(path)

    def lstat(self, path):
        """
        Same as stat but doesn't follow symlinks
        """
        return self.sftp.lstat(path)

    @property
    def progress_bar(self):
        if not self._progress_bar:
            widgets = ['FileTransfer: ', ' ', progressbar.Percentage(), ' ',
                       progressbar.Bar(marker=progressbar.RotatingMarker()),
                       ' ', progressbar.ETA(), ' ',
                       progressbar.FileTransferSpeed()]
            pbar = progressbar.ProgressBar(widgets=widgets,
                                           maxval=1,
                                           force_update=True)
            self._progress_bar = pbar
        return self._progress_bar

    def _file_transfer_progress(self, filename, size, sent):
        pbar = self.progress_bar
        pbar.widgets[0] = filename
        pbar.maxval = size
        pbar.update(sent)
        if pbar.finished:
            pbar.reset()

    def _make_list(self, obj):
        if not isinstance(obj, (list, tuple)):
            return [obj]
        return obj

    def get(self, remotepaths, localpath=''):
        """
        Copies one or more files from the remote host to the local host.
        """
        remotepaths = self._make_list(remotepaths)
        localpath = localpath or os.getcwd()
        globs = []
        noglobs = []
        for rpath in remotepaths:
            if glob.has_magic(rpath):
                globs.append(rpath)
            else:
                noglobs.append(rpath)
        globresults = [self.glob(g) for g in globs]
        remotepaths = noglobs
        for globresult in globresults:
            remotepaths.extend(globresult)
        recursive = False
        for rpath in remotepaths:
            if not self.path_exists(rpath):
                raise exception.BaseException(
                    "Remote file or directory does not exist: %s" % rpath)
        for rpath in remotepaths:
            if self.isdir(rpath):
                recursive = True
                break
        try:
            self.scp.get(remotepaths, local_path=localpath,
                         recursive=recursive)
        except Exception, e:
            log.debug("get failed: remotepaths=%s, localpath=%s",
                      str(remotepaths), localpath)
            raise exception.SCPException(str(e))

    def put(self, localpaths, remotepath='.'):
        """
        Copies one or more files from the local host to the remote host.
        """
        localpaths = self._make_list(localpaths)
        recursive = False
        for lpath in localpaths:
            if os.path.isdir(lpath):
                recursive = True
                break
        try:
            self.scp.put(localpaths, remote_path=remotepath,
                         recursive=recursive)
        except Exception, e:
            log.debug("put failed: localpaths=%s, remotepath=%s",
                      str(localpaths), remotepath)
            raise exception.SCPException(str(e))

    def execute_async(self, command, source_profile=True):
        """
        Executes a remote command so that it continues running even after this
        SSH connection closes. The remote process will be put into the
        background via nohup. Does not return output or check for non-zero exit
        status.
        """
        return self.execute(command, detach=True,
                            source_profile=source_profile)

    def get_last_status(self):
        return self.__last_status

    def get_status(self, command, source_profile=True):
        """
        Execute a remote command and return the exit status
        """
        channel = self.transport.open_session()
        if source_profile:
            command = "source /etc/profile && %s" % command
        channel.exec_command(command)
        self.__last_status = channel.recv_exit_status()
        return self.__last_status

    def _get_output(self, channel, silent=True, only_printable=False):
        """
        Returns the stdout/stderr output from a ssh channel as a list of
        strings (non-interactive only)
        """
        # stdin = channel.makefile('wb', -1)
        stdout = channel.makefile('rb', -1)
        stderr = channel.makefile_stderr('rb', -1)
        if silent:
            output = stdout.readlines() + stderr.readlines()
        else:
            output = []
            line = None
            while line != '':
                line = stdout.readline()
                if only_printable:
                    line = ''.join(c for c in line if c in string.printable)
                if line != '':
                    output.append(line)
                    print line,
            for line in stderr.readlines():
                output.append(line)
                print line,
        if only_printable:
            output = map(lambda line: ''.join(c for c in line if c in
                                              string.printable), output)
        output = map(lambda line: line.strip(), output)
        return output

    def execute(self, command, silent=True, only_printable=False,
                ignore_exit_status=False, log_output=True, detach=False,
                source_profile=True, raise_on_failure=True):
        """
        Execute a remote command and return stdout/stderr

        NOTE: this function blocks until the process finishes

        kwargs:
        silent - don't print the command's output to the console
        only_printable - filter the command's output to allow only printable
                         characters
        ignore_exit_status - don't warn about non-zero exit status
        log_output - log all remote output to the debug file
        detach - detach the remote process so that it continues to run even
                 after the SSH connection closes (does NOT return output or
                 check for non-zero exit status if detach=True)
        source_profile - if True prefix the command with "source /etc/profile"
        raise_on_failure - raise exception.SSHError if command fails
        returns List of output lines
        """
        channel = self.transport.open_session()
        if detach:
            command = "nohup %s &" % command
            if source_profile:
                command = "source /etc/profile && %s" % command
            channel.exec_command(command)
            channel.close()
            self.__last_status = None
            return
        if source_profile:
            command = "source /etc/profile && %s" % command
        log.debug("executing remote command: %s" % command)
        channel.exec_command(command)
        output = self._get_output(channel, silent=silent,
                                  only_printable=only_printable)
        exit_status = channel.recv_exit_status()
        self.__last_status = exit_status
        out_str = '\n'.join(output)
        if exit_status != 0:
            msg = "remote command '%s' failed with status %d"
            msg %= (command, exit_status)
            if log_output:
                msg += ":\n%s" % out_str
            else:
                msg += " (no output log requested)"
            if not ignore_exit_status:
                if raise_on_failure:
                    raise exception.RemoteCommandFailed(
                        msg, command, exit_status, out_str)
                else:
                    log.error(msg)
            else:
                log.debug("(ignored) " + msg)
        else:
            if log_output:
                log.debug("output of '%s':\n%s" % (command, out_str))
            else:
                log.debug("output of '%s' has been hidden" % command)
        return output

    def has_required(self, progs):
        """
        Same as check_required but returns False if not all commands exist
        """
        try:
            return self.check_required(progs)
        except exception.RemoteCommandNotFound:
            return False

    def check_required(self, progs):
        """
        Checks that all commands in the progs list exist on the remote system.
        Returns True if all commands exist and raises exception.CommandNotFound
        if not.
        """
        for prog in progs:
            if not self.which(prog):
                raise exception.RemoteCommandNotFound(prog)
        return True

    def which(self, prog):
        return self.execute('which %s' % prog, ignore_exit_status=True)

    def get_path(self):
        """Returns the PATH environment variable on the remote machine"""
        return self.get_env()['PATH']

    def get_env(self):
        """Returns the remote machine's environment as a dictionary"""
        env = {}
        for line in self.execute('env'):
            key, val = line.split('=', 1)
            env[key] = val
        return env

    def close(self):
        """Closes the connection and cleans up."""
        if self._sftp:
            self._sftp.close()
        if self._transport:
            self._transport.close()

    def _invoke_shell(self, term='screen', cols=80, lines=24):
        chan = self.transport.open_session()
        chan.get_pty(term, cols, lines)
        chan.invoke_shell()
        return chan

    def get_current_user(self):
        if not self.is_active():
            return
        return self.transport.get_username()

    def switch_user(self, user):
        """
        Reconnect, if necessary, to host as user
        """
        if not self.is_active() or user and self.get_current_user() != user:
            self.connect(username=user)
        else:
            user = user or self._username
            log.debug("already connected as user %s" % user)

    def interactive_shell(self, user='root'):
        orig_user = self.get_current_user()
        self.switch_user(user)
        chan = self._invoke_shell()
        log.info('Starting Pure-Python SSH shell...')
        if HAS_TERMIOS:
            self._posix_shell(chan)
        else:
            self._windows_shell(chan)
        chan.close()
        self.switch_user(orig_user)

    def _posix_shell(self, chan):
        import select

        oldtty = termios.tcgetattr(sys.stdin)
        try:
            tty.setraw(sys.stdin.fileno())
            tty.setcbreak(sys.stdin.fileno())
            chan.settimeout(0.0)

            # needs to be sent to give vim correct size FIX
            chan.send('eval $(resize)\n')

            while True:
                r, w, e = select.select([chan, sys.stdin], [], [])
                if chan in r:
                    try:
                        x = chan.recv(1024)
                        if len(x) == 0:
                            print '\r\n*** EOF\r\n',
                            break
                        sys.stdout.write(x)
                        sys.stdout.flush()
                    except socket.timeout:
                        pass
                if sys.stdin in r:
                    # fixes up arrow problem
                    x = os.read(sys.stdin.fileno(), 1)
                    if len(x) == 0:
                        break
                    chan.send(x)
        finally:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, oldtty)

    # thanks to Mike Looijmans for this code
    def _windows_shell(self, chan):
        import threading

        sys.stdout.write("Line-buffered terminal emulation. "
                         "Press F6 or ^Z to send EOF.\r\n\r\n")

        def writeall(sock):
            while True:
                data = sock.recv(256)
                if not data:
                    sys.stdout.write('\r\n*** EOF ***\r\n\r\n')
                    sys.stdout.flush()
                    break
                sys.stdout.write(data)
                sys.stdout.flush()

        writer = threading.Thread(target=writeall, args=(chan,))
        writer.start()

        # needs to be sent to give vim correct size FIX
        chan.send('eval $(resize)\n')

        try:
            while True:
                d = sys.stdin.read(1)
                if not d:
                    break
                chan.send(d)
        except EOFError:
            # user hit ^Z or F6
            pass

    def __del__(self):
        """Attempt to clean up if not explicitly closed."""
        log.debug('__del__ called')
        self.close()


# for backwards compatibility
Connection = SSHClient


class SSHGlob(object):

    def __init__(self, ssh_client):
        self.ssh = ssh_client

    def glob(self, pathname):
        return list(self.iglob(pathname))

    def iglob(self, pathname):
        """
        Return an iterator which yields the paths matching a pathname pattern.
        The pattern may contain simple shell-style wildcards a la fnmatch.
        """
        if not glob.has_magic(pathname):
            if self.ssh.lpath_exists(pathname):
                yield pathname
            return
        dirname, basename = posixpath.split(pathname)
        if not dirname:
            for name in self.glob1(posixpath.curdir, basename):
                yield name
            return
        if glob.has_magic(dirname):
            dirs = self.iglob(dirname)
        else:
            dirs = [dirname]
        if glob.has_magic(basename):
            glob_in_dir = self.glob1
        else:
            glob_in_dir = self.glob0
        for dirname in dirs:
            for name in glob_in_dir(dirname, basename):
                yield posixpath.join(dirname, name)

    def glob0(self, dirname, basename):
        if basename == '':
            # `os.path.split()` returns an empty basename for paths ending with
            # a directory separator.  'q*x/' should match only directories.
            if self.ssh.isdir(dirname):
                return [basename]
        else:
            if self.ssh.lexists(posixpath.join(dirname, basename)):
                return [basename]
        return []

    def glob1(self, dirname, pattern):
        if not dirname:
            dirname = posixpath.curdir
        if isinstance(pattern, unicode) and not isinstance(dirname, unicode):
            # enc = sys.getfilesystemencoding() or sys.getdefaultencoding()
            # dirname = unicode(dirname, enc)
            dirname = unicode(dirname, 'UTF-8')
        try:
            names = [posixpath.basename(n) for n in self.ssh.ls(dirname)]
        except os.error:
            return []
        if pattern[0] != '.':
            names = filter(lambda x: x[0] != '.', names)
        return fnmatch.filter(names, pattern)


def insert_char_every_n_chars(string, char='\n', every=64):
    return char.join(
        string[i:i + every] for i in xrange(0, len(string), every))


def get_rsa_key(key_location=None, key_file_obj=None, passphrase=None,
                use_pycrypto=False):
    key_fobj = key_file_obj or open(key_location)
    try:
        if use_pycrypto:
            key = RSA.importKey(key_fobj, passphrase=passphrase)
        else:
            key = paramiko.RSAKey.from_private_key(key_fobj,
                                                   password=passphrase)
        return key
    except (paramiko.SSHException, ValueError):
        raise exception.SSHError(
            "Invalid RSA private key file or missing passphrase: %s" %
            key_location)


def get_dsa_key(key_location=None, key_file_obj=None, passphrase=None,
                use_pycrypto=False):
    key_fobj = key_file_obj or open(key_location)
    try:
        key = paramiko.DSSKey.from_private_key(key_fobj,
                                               password=passphrase)
        if use_pycrypto:
            key = DSA.construct((key.y, key.g, key.p, key.q, key.x))
        return key
    except (paramiko.SSHException, ValueError):
        raise exception.SSHError(
            "Invalid DSA private key file or missing passphrase: %s" %
            key_location)


def get_public_key(key):
    return ' '.join([key.get_name(), key.get_base64()])


def generate_rsa_key():
    return paramiko.RSAKey.generate(2048)


def get_private_rsa_fingerprint(key_location=None, key_file_obj=None,
                                passphrase=None):
    """
    Returns the fingerprint of a private RSA key as a 59-character string (40
    characters separated every 2 characters by a ':'). The fingerprint is
    computed using the SHA1 (hex) digest of the DER-encoded (pkcs8) RSA private
    key.
    """
    k = get_rsa_key(key_location=key_location, key_file_obj=key_file_obj,
                    passphrase=passphrase, use_pycrypto=True)
    sha1digest = hashlib.sha1(k.exportKey('DER', pkcs=8)).hexdigest()
    fingerprint = insert_char_every_n_chars(sha1digest, ':', 2)
    key = key_location or key_file_obj
    log.debug("rsa private key fingerprint (%s): %s" % (key, fingerprint))
    return fingerprint


def get_public_rsa_fingerprint(key_location=None, key_file_obj=None,
                               passphrase=None):
    """
    Returns the fingerprint of the public portion of an RSA key as a
    47-character string (32 characters separated every 2 characters by a ':').
    The fingerprint is computed using the MD5 (hex) digest of the DER-encoded
    RSA public key.
    """
    privkey = get_rsa_key(key_location=key_location, key_file_obj=key_file_obj,
                          passphrase=passphrase, use_pycrypto=True)
    pubkey = privkey.publickey()
    md5digest = hashlib.md5(pubkey.exportKey('DER')).hexdigest()
    fingerprint = insert_char_every_n_chars(md5digest, ':', 2)
    key = key_location or key_file_obj
    log.debug("rsa public key fingerprint (%s): %s" % (key, fingerprint))
    return fingerprint


def test_create_keypair_fingerprint(keypair=None):
    """
    TODO: move this to 'live' tests
    """
    from starcluster import config
    cfg = config.StarClusterConfig().load()
    ec2 = cfg.get_easy_ec2()
    if keypair is None:
        keypair = cfg.keys.keys()[0]
    key_location = cfg.get_key(keypair).key_location
    localfprint = get_private_rsa_fingerprint(key_location)
    ec2fprint = ec2.get_keypair(keypair).fingerprint
    print 'local fingerprint: %s' % localfprint
    print '  ec2 fingerprint: %s' % ec2fprint
    assert localfprint == ec2fprint


def test_import_keypair_fingerprint(keypair):
    """
    TODO: move this to 'live' tests
    """
    from starcluster import config
    cfg = config.StarClusterConfig().load()
    ec2 = cfg.get_easy_ec2()
    key_location = cfg.get_key(keypair).key_location
    localfprint = get_public_rsa_fingerprint(key_location)
    ec2fprint = ec2.get_keypair(keypair).fingerprint
    print 'local fingerprint: %s' % localfprint
    print '  ec2 fingerprint: %s' % ec2fprint
    assert localfprint == ec2fprint

########NEW FILE########
__FILENAME__ = static
# Copyright 2009-2014 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

"""
Module for storing static data structures
"""
import os
import sys
import getpass
import tempfile


def __expand_all(path):
    path = os.path.expanduser(path)
    path = os.path.expandvars(path)
    return path


def __expand_all_in_list(lst):
    for i, path in enumerate(lst):
        lst[i] = __expand_all(path)
    return lst


def __makedirs(path, exit_on_failure=False):
    if not os.path.exists(path):
        try:
            os.makedirs(path)
        except OSError:
            if exit_on_failure:
                sys.stderr.write("!!! ERROR - %s *must* be a directory\n" %
                                 path)
    elif not os.path.isdir(path) and exit_on_failure:
        sys.stderr.write("!!! ERROR - %s *must* be a directory\n" % path)
        sys.exit(1)


def create_sc_config_dirs():
    __makedirs(STARCLUSTER_CFG_DIR, exit_on_failure=True)
    __makedirs(STARCLUSTER_PLUGIN_DIR)
    __makedirs(STARCLUSTER_LOG_DIR)


VERSION = "0.95.5"
PID = os.getpid()
TMP_DIR = tempfile.gettempdir()
if os.path.exists("/tmp"):
    TMP_DIR = "/tmp"
CURRENT_USER = 'unknown_user'
try:
    CURRENT_USER = getpass.getuser()
except:
    pass
SSH_TEMPLATE = 'ssh %(opts)s %(user)s@%(host)s'

STARCLUSTER_CFG_DIR = os.path.join(os.path.expanduser('~'), '.starcluster')
STARCLUSTER_CFG_FILE = os.path.join(STARCLUSTER_CFG_DIR, 'config')
STARCLUSTER_PLUGIN_DIR = os.path.join(STARCLUSTER_CFG_DIR, 'plugins')
STARCLUSTER_LOG_DIR = os.path.join(STARCLUSTER_CFG_DIR, 'logs')
STARCLUSTER_RECEIPT_DIR = "/var/run/starcluster"
STARCLUSTER_RECEIPT_FILE = os.path.join(STARCLUSTER_RECEIPT_DIR, "receipt.pkl")
STARCLUSTER_OWNER_ID = 342652561657

DEBUG_FILE = os.path.join(STARCLUSTER_LOG_DIR, 'debug.log')
SSH_DEBUG_FILE = os.path.join(STARCLUSTER_LOG_DIR, 'ssh-debug.log')
AWS_DEBUG_FILE = os.path.join(STARCLUSTER_LOG_DIR, 'aws-debug.log')
CRASH_FILE = os.path.join(STARCLUSTER_LOG_DIR, 'crash-report-%d.txt' % PID)

# StarCluster BASE AMIs (us-east-1)
BASE_AMI_32 = "ami-9bf9c9f2"
BASE_AMI_64 = "ami-3393a45a"
BASE_AMI_HVM = "ami-6b211202"

SECURITY_GROUP_PREFIX = "@sc-"
SECURITY_GROUP_TEMPLATE = SECURITY_GROUP_PREFIX + "%s"
VOLUME_GROUP_NAME = "volumecreator"
VOLUME_GROUP = SECURITY_GROUP_PREFIX + VOLUME_GROUP_NAME

# Cluster group tag keys
VERSION_TAG = SECURITY_GROUP_PREFIX + 'version'
CORE_TAG = SECURITY_GROUP_PREFIX + 'core'
USER_TAG = SECURITY_GROUP_PREFIX + 'user'
MAX_TAG_LEN = 255

# Internal StarCluster userdata filenames
UD_PLUGINS_FNAME = "_sc_plugins.txt"
UD_VOLUMES_FNAME = "_sc_volumes.txt"
UD_ALIASES_FNAME = "_sc_aliases.txt"

INSTANCE_METADATA_URI = "http://169.254.169.254/latest"
INSTANCE_STATES = ['pending', 'running', 'shutting-down',
                   'terminated', 'stopping', 'stopped']
VOLUME_STATUS = ['creating', 'available', 'in-use',
                 'deleting', 'deleted', 'error']
VOLUME_ATTACH_STATUS = ['attaching', 'attached', 'detaching', 'detached']

INSTANCE_TYPES = {
    't1.micro': ['i386', 'x86_64'],
    'm1.small': ['i386', 'x86_64'],
    'm1.medium': ['i386', 'x86_64'],
    'm1.large': ['x86_64'],
    'm1.xlarge': ['x86_64'],
    'c1.medium': ['i386', 'x86_64'],
    'c1.xlarge': ['x86_64'],
    'm2.xlarge': ['x86_64'],
    'm2.2xlarge': ['x86_64'],
    'm2.4xlarge': ['x86_64'],
    'm3.medium': ['x86_64'],
    'm3.large': ['x86_64'],
    'm3.xlarge': ['x86_64'],
    'm3.2xlarge': ['x86_64'],
    'r3.large': ['x86_64'],
    'r3.xlarge': ['x86_64'],
    'r3.2xlarge': ['x86_64'],
    'r3.4xlarge': ['x86_64'],
    'r3.8xlarge': ['x86_64'],
    'cc1.4xlarge': ['x86_64'],
    'cc2.8xlarge': ['x86_64'],
    'cg1.4xlarge': ['x86_64'],
    'g2.2xlarge': ['x86_64'],
    'cr1.8xlarge': ['x86_64'],
    'hi1.4xlarge': ['x86_64'],
    'hs1.8xlarge': ['x86_64'],
    'c3.large': ['x86_64'],
    'c3.xlarge': ['x86_64'],
    'c3.2xlarge': ['x86_64'],
    'c3.4xlarge': ['x86_64'],
    'c3.8xlarge': ['x86_64'],
    'i2.xlarge': ['x86_64'],
    'i2.2xlarge': ['x86_64'],
    'i2.4xlarge': ['x86_64'],
    'i2.8xlarge': ['x86_64'],
}

MICRO_INSTANCE_TYPES = ['t1.micro']

SEC_GEN_TYPES = ['m3.medium', 'm3.large', 'm3.xlarge', 'm3.2xlarge']

CLUSTER_COMPUTE_TYPES = ['cc1.4xlarge', 'cc2.8xlarge']

CLUSTER_GPU_TYPES = ['g2.2xlarge', 'cg1.4xlarge']

CLUSTER_HIMEM_TYPES = ['cr1.8xlarge']

HIMEM_TYPES = ['r3.large', 'r3.xlarge', 'r3.2xlarge', 'r3.4xlarge',
               'r3.8xlarge']

HI_IO_TYPES = ['hi1.4xlarge']

HI_STORAGE_TYPES = ['hs1.8xlarge']

M3_COMPUTE_TYPES = ['c3.large', 'c3.xlarge', 'c3.2xlarge', 'c3.4xlarge',
                    'c3.8xlarge']

I2_STORAGE_TYPES = ['i2.xlarge', 'i2.2xlarge', 'i2.4xlarge', 'i2.8xlarge']

HVM_ONLY_TYPES = (CLUSTER_COMPUTE_TYPES + CLUSTER_GPU_TYPES +
                  CLUSTER_HIMEM_TYPES + I2_STORAGE_TYPES + HIMEM_TYPES)

HVM_TYPES = (HVM_ONLY_TYPES + HI_IO_TYPES + HI_STORAGE_TYPES + SEC_GEN_TYPES +
             M3_COMPUTE_TYPES)

EBS_ONLY_TYPES = MICRO_INSTANCE_TYPES

# Always make sure these match instances listed here:
# http://docs.aws.amazon.com/AWSEC2/latest/UserGuide/placement-groups.html
# StarCluster additionally adds cc1.4xlarge to the list - EC2 is slowly
# migrating folks away from this type in favor of cc2.8xlarge but the type
# still works for some older accounts.
PLACEMENT_GROUP_TYPES = (M3_COMPUTE_TYPES + HVM_ONLY_TYPES + HI_IO_TYPES +
                         HI_STORAGE_TYPES)

# Only add a region to this list after testing that you can create and delete a
# placement group there.
PLACEMENT_GROUP_REGIONS = ['us-east-1', 'us-west-2', 'eu-west-1',
                           'ap-northeast-1', 'ap-southeast-1',
                           'ap-southeast-2']

PROTOCOLS = ['tcp', 'udp', 'icmp']

WORLD_CIDRIP = '0.0.0.0/0'

DEFAULT_SSH_PORT = 22

AVAILABLE_SHELLS = {
    "bash": True,
    "zsh": True,
    "csh": True,
    "ksh": True,
    "tcsh": True,
}

GLOBAL_SETTINGS = {
    # setting, type, required?, default, options, callback
    'default_template': (str, False, None, None, None),
    'enable_experimental': (bool, False, False, None, None),
    'refresh_interval': (int, False, 30, None, None),
    'web_browser': (str, False, None, None, None),
    'include': (list, False, [], None, None),
}

AWS_SETTINGS = {
    'aws_access_key_id': (str, True, None, None, None),
    'aws_secret_access_key': (str, True, None, None, None),
    'aws_user_id': (str, False, None, None, None),
    'ec2_cert': (str, False, None, None, __expand_all),
    'ec2_private_key': (str, False, None, None, __expand_all),
    'aws_port': (int, False, None, None, None),
    'aws_ec2_path': (str, False, '/', None, None),
    'aws_s3_path': (str, False, '/', None, None),
    'aws_is_secure': (bool, False, True, None, None),
    'aws_region_name': (str, False, None, None, None),
    'aws_region_host': (str, False, None, None, None),
    'aws_s3_host': (str, False, None, None, None),
    'aws_proxy': (str, False, None, None, None),
    'aws_proxy_port': (int, False, None, None, None),
    'aws_proxy_user': (str, False, None, None, None),
    'aws_proxy_pass': (str, False, None, None, None),
    'aws_validate_certs': (bool, False, True, None, None),
}

KEY_SETTINGS = {
    'key_location': (str, True, None, None, __expand_all),
}

EBS_VOLUME_SETTINGS = {
    'volume_id': (str, True, None, None, None),
    'device': (str, False, None, None, None),
    'partition': (int, False, None, None, None),
    'mount_path': (str, True, None, None, None),
}

PLUGIN_SETTINGS = {
    'setup_class': (str, True, None, None, None),
}

PERMISSION_SETTINGS = {
    # either you're specifying an ip-based rule
    'ip_protocol': (str, False, 'tcp', PROTOCOLS, None),
    'from_port': (int, True, None, None, None),
    'to_port': (int, True, None, None, None),
    'cidr_ip': (str, False, '0.0.0.0/0', None, None),
    # or you're allowing full access to another security group
    # skip this for now...these two options are mutually exclusive to
    # the four settings above and source_group is  less commonly
    # used. address this when someone requests it.
    # 'source_group': (str, False, None),
    # 'source_group_owner': (int, False, None),
}

CLUSTER_SETTINGS = {
    'spot_bid': (float, False, None, None, None),
    'cluster_size': (int, True, None, None, None),
    'cluster_user': (str, False, 'sgeadmin', None, None),
    'cluster_shell': (str, False, 'bash', AVAILABLE_SHELLS.keys(), None),
    'subnet_id': (str, False, None, None, None),
    'public_ips': (bool, False, None, None, None),
    'master_image_id': (str, False, None, None, None),
    'master_instance_type': (str, False, None, INSTANCE_TYPES.keys(), None),
    'node_image_id': (str, True, None, None, None),
    'node_instance_type': (list, True, [], None, None),
    'availability_zone': (str, False, None, None, None),
    'keyname': (str, True, None, None, None),
    'extends': (str, False, None, None, None),
    'volumes': (list, False, [], None, None),
    'plugins': (list, False, [], None, None),
    'permissions': (list, False, [], None, None),
    'userdata_scripts': (list, False, [], None, __expand_all_in_list),
    'disable_queue': (bool, False, False, None, None),
    'force_spot_master': (bool, False, False, None, None),
    'disable_cloudinit': (bool, False, False, None, None),
    'dns_prefix': (bool, False, False, None, None),
}

########NEW FILE########
__FILENAME__ = condor
# Copyright 2009-2014 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

condor_tmpl = """\
LOCAL_CONFIG_FILE =
LOCAL_CONFIG_DIR = /etc/condor/config.d
LOCAL_DIR = /var/lib/condor
RUN = $(LOCAL_DIR)/run
LOG = $(LOCAL_DIR)/logs
LOCK = $(LOCAL_DIR)/locks
SPOOL = $(LOCAL_DIR)/spool
EXECUTE = $(LOCAL_DIR)/execute
CRED_STORE_DIR = $(LOCAL_DIR)/cred_dir
CONDOR_HOST = %(CONDOR_HOST)s
UID_DOMAIN      = $(CONDOR_HOST)
FILESYSTEM_DOMAIN   = $(CONDOR_HOST)
TRUST_UID_DOMAIN = True
DAEMON_LIST = %(DAEMON_LIST)s
ALLOW_ADMINISTRATOR = $(CONDOR_HOST), node*
ALLOW_OWNER = $(FULL_HOSTNAME), $(ALLOW_ADMINISTRATOR), $(CONDOR_HOST), node*
ALLOW_READ = $(FULL_HOSTNAME), $(CONDOR_HOST), node*
ALLOW_WRITE = $(FULL_HOSTNAME), $(CONDOR_HOST), node*
SCHEDD_HOST = $(CONDOR_HOST)@$(CONDOR_HOST)
SCHEDD_NAME = $(FULL_HOSTNAME)@$(FULL_HOSTNAME)
START = True
SUSPEND = False
CONTINUE = True
PREEMPT = False
KILL = False
WANT_SUSPEND = False
WANT_VACATE = False
RANK = Scheduler =?= $(DedicatedScheduler)
DedicatedScheduler = "DedicatedScheduler@$(CONDOR_HOST)"
STARTD_ATTRS = $(STARTD_ATTRS), DedicatedScheduler
SEC_DEFAULT_AUTHENTICATION_METHODS = FS, KERBEROS, GSI, FS_REMOTE
FS_REMOTE_DIR = %(FS_REMOTE_DIR)s
"""

########NEW FILE########
__FILENAME__ = config
# Copyright 2009-2014 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

from starcluster import static

config_template = """\
####################################
## StarCluster Configuration File ##
####################################
[global]
# Configure the default cluster template to use when starting a cluster
# defaults to 'smallcluster' defined below. This template should be usable
# out-of-the-box provided you've configured your keypair correctly
DEFAULT_TEMPLATE=smallcluster
# enable experimental features for this release
#ENABLE_EXPERIMENTAL=True
# number of seconds to wait when polling instances (default: 30s)
#REFRESH_INTERVAL=15
# specify a web browser to launch when viewing spot history plots
#WEB_BROWSER=chromium
# split the config into multiple files
#INCLUDE=~/.starcluster/aws, ~/.starcluster/keys, ~/.starcluster/vols

#############################################
## AWS Credentials and Connection Settings ##
#############################################
[aws info]
# This is the AWS credentials section (required).
# These settings apply to all clusters
# replace these with your AWS keys
AWS_ACCESS_KEY_ID = #your_aws_access_key_id
AWS_SECRET_ACCESS_KEY = #your_secret_access_key
# replace this with your account number
AWS_USER_ID= #your userid
# Uncomment to specify a different Amazon AWS region  (OPTIONAL)
# (defaults to us-east-1 if not specified)
# NOTE: AMIs have to be migrated!
#AWS_REGION_NAME = eu-west-1
#AWS_REGION_HOST = ec2.eu-west-1.amazonaws.com
# Uncomment these settings when creating an instance-store (S3) AMI (OPTIONAL)
#EC2_CERT = /path/to/your/cert-asdf0as9df092039asdfi02089.pem
#EC2_PRIVATE_KEY = /path/to/your/pk-asdfasd890f200909.pem
# Uncomment these settings to use a proxy host when connecting to AWS
#AWS_PROXY = your.proxyhost.com
#AWS_PROXY_PORT = 8080
#AWS_PROXY_USER = yourproxyuser
#AWS_PROXY_PASS = yourproxypass

###########################
## Defining EC2 Keypairs ##
###########################
# Sections starting with "key" define your keypairs. See "starcluster createkey
# --help" for instructions on how to create a new keypair. Section name should
# match your key name e.g.:
[key mykey]
KEY_LOCATION=~/.ssh/mykey.rsa

# You can of course have multiple keypair sections
# [key myotherkey]
# KEY_LOCATION=~/.ssh/myotherkey.rsa

################################
## Defining Cluster Templates ##
################################
# Sections starting with "cluster" represent a cluster template. These
# "templates" are a collection of settings that define a single cluster
# configuration and are used when creating and configuring a cluster. You can
# change which template to use when creating your cluster using the -c option
# to the start command:
#
#     $ starcluster start -c mediumcluster mycluster
#
# If a template is not specified then the template defined by DEFAULT_TEMPLATE
# in the [global] section above is used. Below is the "default" template named
# "smallcluster". You can rename it but dont forget to update the
# DEFAULT_TEMPLATE setting in the [global] section above. See the next section
# on defining multiple templates.

[cluster smallcluster]
# change this to the name of one of the keypair sections defined above
KEYNAME = mykey
# number of ec2 instances to launch
CLUSTER_SIZE = 2
# create the following user on the cluster
CLUSTER_USER = sgeadmin
# optionally specify shell (defaults to bash)
# (options: %(shells)s)
CLUSTER_SHELL = bash
# Uncomment to prepent the cluster tag to the dns name of all nodes created
# using this cluster config.  ie: mycluster-master and mycluster-node001
# If you choose to enable this option, it's recommended that you enable it in
# the DEFAULT_TEMPLATE so all nodes will automatically have the prefix
# DNS_PREFIX = True
# AMI to use for cluster nodes. These AMIs are for the us-east-1 region.
# Use the 'listpublic' command to list StarCluster AMIs in other regions
# The base i386 StarCluster AMI is %(x86_ami)s
# The base x86_64 StarCluster AMI is %(x86_64_ami)s
# The base HVM StarCluster AMI is %(hvm_ami)s
NODE_IMAGE_ID = %(x86_64_ami)s
# instance type for all cluster nodes
# (options: %(instance_types)s)
NODE_INSTANCE_TYPE = m1.small
# Launch cluster in a VPC subnet (OPTIONAL)
#SUBNET_ID=subnet-99999999
# Uncomment to assign public IPs to cluster nodes (VPC-ONLY) (OPTIONAL)
# WARNING: Using public IPs with a VPC requires:
# 1. An internet gateway attached to the VPC
# 2. A route table entry linked to the VPC's internet gateway and associated
#    with the VPC subnet with a destination CIDR block of 0.0.0.0/0
# WARNING: Public IPs allow direct access to your VPC nodes from the internet
#PUBLIC_IPS=True
# Uncomment to disable installing/configuring a queueing system on the
# cluster (SGE)
#DISABLE_QUEUE=True
# Uncomment to specify a different instance type for the master node (OPTIONAL)
# (defaults to NODE_INSTANCE_TYPE if not specified)
#MASTER_INSTANCE_TYPE = m1.small
# Uncomment to specify a separate AMI to use for the master node. (OPTIONAL)
# (defaults to NODE_IMAGE_ID if not specified)
#MASTER_IMAGE_ID = %(x86_64_ami)s (OPTIONAL)
# availability zone to launch the cluster in (OPTIONAL)
# (automatically determined based on volumes (if any) or
# selected by Amazon if not specified)
#AVAILABILITY_ZONE = us-east-1c
# list of volumes to attach to the master node (OPTIONAL)
# these volumes, if any, will be NFS shared to the worker nodes
# see "Configuring EBS Volumes" below on how to define volume sections
#VOLUMES = oceandata, biodata
# list of plugins to load after StarCluster's default setup routines (OPTIONAL)
# see "Configuring StarCluster Plugins" below on how to define plugin sections
#PLUGINS = myplugin, myplugin2
# list of permissions (or firewall rules) to apply to the cluster's security
# group (OPTIONAL).
#PERMISSIONS = ssh, http
# Uncomment to always create a spot cluster when creating a new cluster from
# this template. The following example will place a $0.50 bid for each spot
# request.
#SPOT_BID = 0.50
# Uncomment to specify one or more userdata scripts to use when launching
# cluster instances. Supports cloudinit. All scripts combined must be less than
# 16KB
#USERDATA_SCRIPTS = /path/to/script1, /path/to/script2

###########################################
## Defining Additional Cluster Templates ##
###########################################
# You can also define multiple cluster templates. You can either supply all
# configuration options as with smallcluster above, or create an
# EXTENDS=<cluster_name> variable in the new cluster section to use all
# settings from <cluster_name> as defaults. Below are example templates that
# use the EXTENDS feature:

# [cluster mediumcluster]
# Declares that this cluster uses smallcluster as defaults
# EXTENDS=smallcluster
# This section is the same as smallcluster except for the following settings:
# KEYNAME=myotherkey
# NODE_INSTANCE_TYPE = c1.xlarge
# CLUSTER_SIZE=8
# VOLUMES = biodata2

# [cluster largecluster]
# Declares that this cluster uses mediumcluster as defaults
# EXTENDS=mediumcluster
# This section is the same as mediumcluster except for the following variables:
# CLUSTER_SIZE=16

#############################
## Configuring EBS Volumes ##
#############################
# StarCluster can attach one or more EBS volumes to the master and then
# NFS_share these volumes to all of the worker nodes. A new [volume] section
# must be created for each EBS volume you wish to use with StarCluser. The
# section name is a tag for your volume. This tag is used in the VOLUMES
# setting of a cluster template to declare that an EBS volume is to be mounted
# and nfs shared on the cluster. (see the commented VOLUMES setting in the
# example 'smallcluster' template above) Below are some examples of defining
# and configuring EBS volumes to be used with StarCluster:

# Sections starting with "volume" define your EBS volumes
# [volume biodata]
# attach vol-c9999999 to /home on master node and NFS-shre to worker nodes
# VOLUME_ID = vol-c999999
# MOUNT_PATH = /home

# Same volume as above, but mounts to different location
# [volume biodata2]
# VOLUME_ID = vol-c999999
# MOUNT_PATH = /opt/

# Another volume example
# [volume oceandata]
# VOLUME_ID = vol-d7777777
# MOUNT_PATH = /mydata

# By default StarCluster will attempt first to mount the entire volume device,
# failing that it will try the first partition. If you have more than one
# partition you will need to set the PARTITION number, e.g.:
# [volume oceandata]
# VOLUME_ID = vol-d7777777
# MOUNT_PATH = /mydata
# PARTITION = 2

############################################
## Configuring Security Group Permissions ##
############################################
# Sections starting with "permission" define security group rules to
# automatically apply to newly created clusters. IP_PROTOCOL in the following
# examples can be can be: tcp, udp, or icmp. CIDR_IP defaults to 0.0.0.0/0 or
# "open to the # world"

# open port 80 on the cluster to the world
# [permission http]
# IP_PROTOCOL = tcp
# FROM_PORT = 80
# TO_PORT = 80

# open https on the cluster to the world
# [permission https]
# IP_PROTOCOL = tcp
# FROM_PORT = 443
# TO_PORT = 443

# open port 80 on the cluster to an ip range using CIDR_IP
# [permission http]
# IP_PROTOCOL = tcp
# FROM_PORT = 80
# TO_PORT = 80
# CIDR_IP = 18.0.0.0/8

# restrict ssh access to a single ip address (<your_ip>)
# [permission ssh]
# IP_PROTOCOL = tcp
# FROM_PORT = 22
# TO_PORT = 22
# CIDR_IP = <your_ip>/32


#####################################
## Configuring StarCluster Plugins ##
#####################################
# Sections starting with "plugin" define a custom python class which perform
# additional configurations to StarCluster's default routines. These plugins
# can be assigned to a cluster template to customize the setup procedure when
# starting a cluster from this template (see the commented PLUGINS setting in
# the 'smallcluster' template above). Below is an example of defining a user
# plugin called 'myplugin':

# [plugin myplugin]
# NOTE: myplugin module must either live in ~/.starcluster/plugins or be
# on your PYTHONPATH
# SETUP_CLASS = myplugin.SetupClass
# extra settings are passed as __init__ arguments to your plugin:
# SOME_PARAM_FOR_MY_PLUGIN = 1
# SOME_OTHER_PARAM = 2

######################
## Built-in Plugins ##
######################
# The following plugins ship with StarCluster and should work out-of-the-box.
# Uncomment as needed. Don't forget to update your PLUGINS list!
# See http://star.mit.edu/cluster/docs/latest/plugins for plugin details.
#
# Use this plugin to install one or more packages on all nodes
# [plugin pkginstaller]
# SETUP_CLASS = starcluster.plugins.pkginstaller.PackageInstaller
# # list of apt-get installable packages
# PACKAGES = mongodb, python-pymongo
#
# Use this plugin to create one or more cluster users and download all user ssh
# keys to $HOME/.starcluster/user_keys/<cluster>-<region>.tar.gz
# [plugin createusers]
# SETUP_CLASS = starcluster.plugins.users.CreateUsers
# NUM_USERS = 30
# # you can also comment out NUM_USERS and specify exact usernames, e.g.
# # usernames = linus, tux, larry
# DOWNLOAD_KEYS = True
#
# Use this plugin to configure the Condor queueing system
# [plugin condor]
# SETUP_CLASS = starcluster.plugins.condor.CondorPlugin
#
# The SGE plugin is enabled by default and not strictly required. Only use this
# if you want to tweak advanced settings in which case you should also set
# DISABLE_QUEUE=TRUE in your cluster template. See the plugin doc for more
# details.
# [plugin sge]
# SETUP_CLASS = starcluster.plugins.sge.SGEPlugin
# MASTER_IS_EXEC_HOST = False
#
# The IPCluster plugin configures a parallel IPython cluster with optional
# web notebook support. This allows you to run Python code in parallel with low
# latency message passing via ZeroMQ.
# [plugin ipcluster]
# SETUP_CLASS = starcluster.plugins.ipcluster.IPCluster
# # Enable the IPython notebook server (optional)
# ENABLE_NOTEBOOK = True
# # Set a password for the notebook for increased security
# # This is optional but *highly* recommended
# NOTEBOOK_PASSWD = a-secret-password
# # Set a custom directory for storing/loading notebooks (optional)
# NOTEBOOK_DIRECTORY = /path/to/notebook/dir
# # Set a custom packer. Must be one of 'json', 'pickle', or 'msgpack'
# # This is optional.
# PACKER = pickle
#
# Use this plugin to create a cluster SSH "dashboard" using tmux. The plugin
# creates a tmux session on the master node that automatically connects to all
# the worker nodes over SSH. Attaching to the session shows a separate window
# for each node and each window is logged into the node via SSH.
# [plugin tmux]
# SETUP_CLASS = starcluster.plugins.tmux.TmuxControlCenter
#
# Use this plugin to change the default MPI implementation on the
# cluster from OpenMPI to MPICH2.
# [plugin mpich2]
# SETUP_CLASS = starcluster.plugins.mpich2.MPICH2Setup
#
# Configure a hadoop cluster. (includes dumbo setup)
# [plugin hadoop]
# SETUP_CLASS = starcluster.plugins.hadoop.Hadoop
#
# Configure a distributed MySQL Cluster
# [plugin mysqlcluster]
# SETUP_CLASS = starcluster.plugins.mysql.MysqlCluster
# NUM_REPLICAS = 2
# DATA_MEMORY = 80M
# INDEX_MEMORY = 18M
# DUMP_FILE = test.sql
# DUMP_INTERVAL = 60
# DEDICATED_QUERY = True
# NUM_DATA_NODES = 2
#
# Install and setup an Xvfb server on each cluster node
# [plugin xvfb]
# SETUP_CLASS = starcluster.plugins.xvfb.XvfbSetup
""" % {
    'x86_ami': static.BASE_AMI_32,
    'x86_64_ami': static.BASE_AMI_64,
    'hvm_ami': static.BASE_AMI_HVM,
    'instance_types': ', '.join(static.INSTANCE_TYPES.keys()),
    'shells': ', '.join(static.AVAILABLE_SHELLS.keys()),
}

DASHES = '-' * 10
copy_below = ' '.join([DASHES, 'COPY BELOW THIS LINE', DASHES])
end_copy = ' '.join([DASHES, 'END COPY', DASHES])
copy_paste_template = '\n'.join([copy_below, config_template, end_copy]) + '\n'

########NEW FILE########
__FILENAME__ = sge
# Copyright 2009-2014 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

sgeinstall_template = """
SGE_CLUSTER_NAME="starcluster"
SGE_ROOT="/opt/sge6"
SGE_QMASTER_PORT="63231"
SGE_EXECD_PORT="63232"
SGE_ENABLE_SMF="false"
CELL_NAME="default"
ADMIN_USER=""
QMASTER_SPOOL_DIR="/opt/sge6/default/spool/qmaster"
EXECD_SPOOL_DIR="/opt/sge6/default/spool"
GID_RANGE="20000-20100"
SPOOLING_METHOD="classic"
DB_SPOOLING_SERVER="none"
DB_SPOOLING_DIR="/opt/sge6/default/spooldb"
PAR_EXECD_INST_COUNT="20"
ADMIN_HOST_LIST="%(admin_hosts)s"
SUBMIT_HOST_LIST="%(submit_hosts)s"
EXEC_HOST_LIST="%(exec_hosts)s"
EXECD_SPOOL_DIR_LOCAL="/opt/sge6/default/spool/exec_spool_local"
HOSTNAME_RESOLVING="true"
SHELL_NAME="ssh"
COPY_COMMAND="scp"
DEFAULT_DOMAIN="none"
ADMIN_MAIL="none@none.edu"
ADD_TO_RC="false"
SET_FILE_PERMS="true"
RESCHEDULE_JOBS="wait"
SCHEDD_CONF="1"
SHADOW_HOST=""
EXEC_HOST_LIST_RM=""
REMOVE_RC="true"
WINDOWS_SUPPORT="false"
WIN_ADMIN_NAME="Administrator"
WIN_DOMAIN_ACCESS="false"
CSP_RECREATE="false"
CSP_COPY_CERTS="false"
CSP_COUNTRY_CODE="US"
CSP_STATE="MA"
CSP_LOCATION="BOSTON"
CSP_ORGA="MIT"
CSP_ORGA_UNIT="OEIT"
CSP_MAIL_ADDRESS="none@none.edu"
"""

sge_pe_template = """
pe_name           %s
slots             %s
user_lists        NONE
xuser_lists       NONE
start_proc_args   /bin/true
stop_proc_args    /bin/true
allocation_rule   $fill_up
control_slaves    TRUE
job_is_first_task FALSE
urgency_slots     min
accounting_summary FALSE
"""

sgeprofile_template = """
export SGE_ROOT="/opt/sge6"
export SGE_CELL="default"
export SGE_CLUSTER_NAME="starcluster"
export SGE_QMASTER_PORT="63231"
export SGE_EXECD_PORT="63232"
export MANTYPE="man"
export MANPATH="$MANPATH:$SGE_ROOT/man"
export PATH="$PATH:$SGE_ROOT/bin/%(arch)s"
export ROOTPATH="$ROOTPATH:$SGE_ROOT/bin/%(arch)s"
export LDPATH="$LDPATH:$SGE_ROOT/lib/%(arch)s"
export DRMAA_LIBRARY_PATH="$SGE_ROOT/lib/%(arch)s/libdrmaa.so"
"""

########NEW FILE########
__FILENAME__ = user_msgs
# Copyright 2009-2014 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

active_ebs_cluster = """EBS Cluster '%(cluster_name)s' already exists.

Either choose a different tag name, or terminate the existing EBS cluster \
using:

    $ starcluster terminate %(cluster_name)s

WARNING: Terminating an EBS cluster will destroy the local disks (volumes) \
backing the nodes.

If you encountered an issue while starting or using '%(cluster_name)s' you \
can reboot and reconfigure the cluster using the 'restart' command:

    $ starcluster restart %(cluster_name)s

This will reboot all existing nodes and completely reconfigure the cluster \
without wasting instance hours.

"""

stopped_ebs_cluster = """Stopped EBS Cluster '%(cluster_name)s' already exists.

Either choose a different tag name, or start the 'stopped' cluster using:

    $ starcluster start -x %(cluster_name)s

Another option is to terminate the stopped EBS Cluster using:

    $ starcluster terminate %(cluster_name)s

WARNING: Terminating an EBS cluster will destroy the local disks (volumes) \
backing the nodes.
"""

cluster_exists = """Cluster '%(cluster_name)s' already exists.

Either choose a different tag name, or terminate the existing cluster using:

    $ starcluster terminate %(cluster_name)s

If you encountered an issue while starting or using '%(cluster_name)s' you \
can reboot and reconfigure the cluster using the 'restart' command:

    $ starcluster restart %(cluster_name)s

This will reboot all existing nodes and completely reconfigure the cluster \
without wasting instance hours.

"""

cluster_started_msg = """
The cluster is now ready to use. To login to the master node as root, run:

    $ starcluster sshmaster %(tag)s

If you're having issues with the cluster you can reboot the instances and \
completely reconfigure the cluster from scratch using:

    $ starcluster restart %(tag)s

When you're finished using the cluster and wish to terminate it and stop \
paying for service:

    $ starcluster terminate %(tag)s

Alternatively, if the cluster uses EBS instances, you can use the 'stop' \
command to shutdown all nodes and put them into a 'stopped' state preserving \
the EBS volumes backing the nodes:

    $ starcluster stop %(tag)s

WARNING: Any data stored in ephemeral storage (usually /mnt) will be lost!

You can activate a 'stopped' cluster by passing the -x option to the 'start' \
command:

    $ starcluster start -x %(tag)s

This will start all 'stopped' nodes and reconfigure the cluster.
"""

spotmsg = """SPOT INSTANCES ARE NOT GUARANTEED TO COME UP

Spot instances can take a long time to come up and may not come up at all \
depending on the current AWS load and your max spot bid price.

StarCluster will wait indefinitely until all instances (%(size)s) come up. \
If this takes too long, you can cancel the start command using CTRL-C. \
You can then resume the start command later on using the --no-create (-x) \
option:

    $ starcluster start -x %(tag)s

This will use the existing spot instances launched previously and continue \
starting the cluster. If you don't wish to wait on the cluster any longer \
after pressing CTRL-C simply terminate the cluster using the 'terminate' \
command.\
"""

version_mismatch = """\
The cluster '%(cluster)s' was created with a newer version of StarCluster \
(%(new_version)s). You're currently using version %(old_version)s.

This may or may not be a problem depending on what's changed between these \
versions, however, it's highly recommended that you use version \
%(new_version)s when using the '%(cluster)s' cluster.\
"""

authkeys_access_denied = """\
Remote SSH access for user '%(user)s' denied via authorized_keys

This usually means the AMI you're using has been configured to deny SSH \
access for the '%(user)s' user. Either fix your AMI or use one of the \
StarCluster supported AMIs. You can obtain a list of StarCluster supported \
AMIs using the 'listpublic' command:

    $ starcluster listpublic

If you need to customize one of the StarCluster supported AMIs simply launch \
an instance of the AMI, login remotely, configure the instance, and then use \
the 'ebsimage' command to create a new EBS AMI from the instance with your \
changes:

    $ starcluster ebsimage <instance-id> <image-name>

Pass the --help flag to the 'ebsimage' command for more details.
"""

public_ips_disabled = """\
PUBLIC IPS HAVE BEEN DISABLED!!!

This means StarCluster must be executed from a machine within the cluster's VPC
(%(vpc_id)s) otherwise it will hang forever trying to connect to the instances.
"""

########NEW FILE########
__FILENAME__ = conftest
# Copyright 2009-2014 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

import pytest

from starcluster import static
from starcluster import config as sconfig
from starcluster import cluster as scluster

VPC_CIDR = '10.0.0.0/16'
SUBNET_CIDR = '10.0.0.0/24'


def pytest_addoption(parser):
    parser.addoption("-L", "--live", action="store_true", default=False,
                     help="Run live StarCluster tests on a real AWS account")
    parser.addoption("-C", "--coverage", action="store_true", default=False,
                     help="Produce a coverage report for StarCluster")


def pytest_runtest_setup(item):
    if 'live' in item.keywords and not item.config.getoption("--live"):
        pytest.skip("pass --live option to run")


def pytest_configure(config):
    if config.getoption("--coverage"):
        config.option.cov_source = ['starcluster']
        config.option.cov_report = ['term-missing']


@pytest.fixture(scope="module")
def keypair(ec2, config):
    keypairs = ec2.get_keypairs()
    for key in keypairs:
        if key.name in config.keys:
            key.key_location = config.keys[key.name].key_location
            return key
    raise Exception("no keypair on ec2 defined in config")


@pytest.fixture(scope="module")
def config():
    cfg = sconfig.StarClusterConfig().load()
    assert cfg.aws.aws_access_key_id
    assert cfg.aws.aws_secret_access_key
    return cfg


@pytest.fixture(scope="module")
def ec2(config):
    return config.get_easy_ec2()


@pytest.fixture(scope="module")
def vpc(ec2):
    vpcs = ec2.conn.get_all_vpcs(filters={'tag:test': True})
    if not vpcs:
        vpc = ec2.conn.create_vpc(VPC_CIDR)
        vpc.add_tag('test', True)
    else:
        vpc = vpcs.pop()
    return vpc


@pytest.fixture(scope="module")
def gw(ec2, vpc):
    igw = ec2.conn.get_all_internet_gateways(
        filters={'attachment.vpc-id': vpc.id})
    if not igw:
        gw = ec2.conn.create_internet_gateway()
        ec2.conn.attach_internet_gateway(gw.id, vpc.id)
    else:
        gw = igw.pop()
    return gw


@pytest.fixture(scope="module")
def subnet(ec2, vpc, gw):
    subnets = ec2.conn.get_all_subnets(
        filters={'vpcId': vpc.id, 'cidrBlock': SUBNET_CIDR})
    if not subnets:
        subnet = ec2.conn.create_subnet(vpc.id, SUBNET_CIDR)
    else:
        subnet = subnets.pop()
    rtables = ec2.get_route_tables(filters={'vpc-id': vpc.id})
    if not rtables:
        rt = ec2.conn.create_route_table(vpc.id)
    else:
        rt = rtables.pop()
    ec2.conn.associate_route_table(rt.id, subnet.id)
    ec2.conn.create_route(rt.id, static.WORLD_CIDRIP, gateway_id=gw.id)
    return subnet


@pytest.fixture(scope="module")
def ami(ec2):
    img = ec2.conn.get_all_images(
        filters={'owner_id': static.STARCLUSTER_OWNER_ID,
                 'name': 'starcluster-base-ubuntu-13.04-x86_64'})
    assert len(img) == 1
    return img[0]


@pytest.fixture(scope="module",
                params=['flat', 'spot', 'vpc-flat', 'vpc-spot'])
def cluster(request, ec2, keypair, subnet, ami):
    size = 2
    shell = 'bash'
    user = 'testuser'
    subnet_id = subnet.id if 'vpc' in request.param else None
    public_ips = True if 'vpc' in request.param else None
    spot_bid = 0.08 if 'spot' in request.param else None
    instance_type = 't1.micro'
    cl = scluster.Cluster(ec2_conn=ec2,
                          cluster_tag=request.param,
                          cluster_size=size,
                          cluster_user=user,
                          keyname=keypair.name,
                          key_location=keypair.key_location,
                          cluster_shell=shell,
                          master_instance_type=instance_type,
                          master_image_id=ami.id,
                          node_instance_type=instance_type,
                          node_image_id=ami.id,
                          spot_bid=spot_bid,
                          subnet_id=subnet_id,
                          public_ips=public_ips)
    cl.start()
    assert cl.master_node
    assert len(cl.nodes) == size

    def terminate():
        try:
            cl.terminate_cluster()
        except:
            cl.terminate_cluster(force=True)
    request.addfinalizer(terminate)
    return cl


@pytest.fixture(scope="module")
def nodes(cluster):
    return cluster.nodes

########NEW FILE########
__FILENAME__ = mytestplugin
# Copyright 2009-2014 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

from starcluster.logger import log
from starcluster.clustersetup import ClusterSetup


class SetupClass(ClusterSetup):
    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def __init__(self, my_arg, my_other_arg):
        self.my_arg = my_arg
        self.my_other_arg = my_other_arg
        log.debug(
            "setupclass: my_arg = %s, my_other_arg = %s" % (my_arg,
                                                            my_other_arg))

    def run(self, nodes, master, user, shell, volumes):
        log.debug('Hello from MYPLUGIN :D')
        for node in nodes:
            node.ssh.execute('apt-get install -y imagemagick')
            node.ssh.execute('echo "i ran foo" >> /tmp/iran')


class SetupClass2(ClusterSetup):
    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def __init__(self, my_arg, my_other_arg):
        self.my_arg = my_arg
        self.my_other_arg = my_other_arg
        log.debug("setupclass2: my_arg = %s, my_other_arg = %s" %
                  (my_arg, my_other_arg))

    def run(self, nodes, master, user, shell, volumes):
        log.debug('Hello from MYPLUGIN2 :D')
        for node in nodes:
            node.ssh.execute('apt-get install -y python-utidylib')
            node.ssh.execute('echo "i ran too foo" >> /tmp/iran')


class SetupClass3(ClusterSetup):
    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def __init__(self, my_arg, my_other_arg, my_other_other_arg):
        self.my_arg = my_arg
        self.my_other_arg = my_other_arg
        self.my_other_other_arg = my_other_other_arg
        msg = "setupclass3: my_arg = %s, my_other_arg = %s"
        msg += " my_other_other_arg = %s"
        log.debug(msg % (my_arg, my_other_arg, my_other_other_arg))

    def run(self, nodes, master, user, shell, volumes):
        log.debug('Hello from MYPLUGIN3 :D')
        for node in nodes:
            node.ssh.execute('apt-get install -y python-boto')
            node.ssh.execute('echo "i ran also foo" >> /tmp/iran')

########NEW FILE########
__FILENAME__ = config
# Copyright 2009-2014 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

default_config = {
    'default_template': 'c1',
    'enable_experimental': 'False',
    'aws_access_key_id': 'asd0asd9f0asd0fas0d9f0',
    'aws_secret_access_key': 'asdf0a9sdf09203fj0asdf',
    'aws_user_id': 9009230923,
    'k1_location': '~/.path/to/k1_rsa',
    'k2_location': '/path/to/k2_rsa',
    'k3_location': '/path/to/k3_rsa',
    'v1_id': 'vol-c999999',
    'v1_device': '/dev/sdj',
    'v1_partition': 1,
    'v1_mount_path': '/volume1',
    'v2_id': 'vol-c888888',
    'v2_device': '/dev/sdk',
    'v2_partition': 1,
    'v2_mount_path': '/volume2',
    'v3_id': 'vol-c777777',
    'v3_device': '/dev/sdl',
    'v3_partition': 1,
    'v3_mount_path': '/volume3',
    'v4_id': 'vol-c666666',
    'v4_partition': 1,
    'v4_mount_path': '/volume4',
    'v5_id': 'vol-c555555',
    'v5_partition': 1,
    'v5_mount_path': '/volume5',
    'p1_class': 'starcluster.tests.mytestplugin.SetupClass',
    'p1_param1': 23,
    'p1_param2': 'skidoo',
    'p2_class': 'starcluster.tests.mytestplugin.SetupClass2',
    'p2_param1': 'hello',
    'p2_param2': 'world',
    'p3_class': 'starcluster.tests.mytestplugin.SetupClass3',
    'p3_param1': 'bon',
    'p3_param2': 'jour',
    'p3_param3': 'monsignour',
    's1_protocol': 'udp',
    's1_from_port': 20,
    's1_to_port': 20,
    's1_cidr_ip': '192.168.1.0/24',
    's2_protocol': 'tcp',
    's2_from_port': 80,
    's2_to_port': 20,
    's2_cidr_ip': '192.168.233.0/24',
    's3_from_port': 20,
    's3_to_port': 30,
    'c1_keyname': 'k1',
    'c1_size': 4,
    'c1_user': 'testuser',
    'c1_shell': 'zsh',
    'c1_master_id': 'ami-8f9e71e6',
    'c1_node_id': 'ami-8f9e71e6',
    'c1_master_type': 'm1.small',
    'c1_node_type': 'm1.small',
    'c1_vols': 'v1,v2,v3',
    'c1_plugs': 'p1,p2,p3',
    'c1_zone': 'us-east-1c',
    'c2_extends': 'c1',
    'c2_keyname': 'k2',
    'c2_size': 6,
    'c2_master_type': 'c1.xlarge',
    'c2_node_type': 'c1.xlarge',
    'c2_vols': 'v1,v2',
    'c3_extends': 'c2',
    'c3_keyname': 'k3',
    'c3_size': 8,
    'c3_vols': 'v3',
    'c4_extends': 'c3',
    'c4_permissions': 's1',
}

config_test_template = """
[global]
DEFAULT_TEMPLATE=%(default_template)s
ENABLE_EXPERIMENTAL=%(enable_experimental)s

[aws info]
AWS_ACCESS_KEY_ID = %(aws_access_key_id)s
AWS_SECRET_ACCESS_KEY = %(aws_secret_access_key)s
AWS_USER_ID= %(aws_user_id)s

[key k1]
KEY_LOCATION=%(k1_location)s

[key k2]
KEY_LOCATION=%(k2_location)s

[key k3]
KEY_LOCATION=%(k3_location)s

[volume v1]
VOLUME_ID = %(v1_id)s
DEVICE = %(v1_device)s
PARTITION = %(v1_partition)s
MOUNT_PATH = %(v1_mount_path)s

[volume v2]
VOLUME_ID = %(v2_id)s
DEVICE = %(v2_device)s
PARTITION = %(v2_partition)s
MOUNT_PATH = %(v2_mount_path)s

[volume v3]
VOLUME_ID = %(v3_id)s
DEVICE = %(v3_device)s
PARTITION = %(v3_partition)s
MOUNT_PATH = %(v3_mount_path)s

[volume v4]
VOLUME_ID = %(v4_id)s
PARTITION = %(v4_partition)s
MOUNT_PATH = %(v4_mount_path)s

[volume v5]
VOLUME_ID = %(v5_id)s
PARTITION = %(v5_partition)s
MOUNT_PATH = %(v5_mount_path)s

[plugin p1]
SETUP_CLASS = %(p1_class)s
MY_ARG = %(p1_param1)s
MY_OTHER_ARG = %(p1_param2)s

[plugin p2]
SETUP_CLASS = %(p2_class)s
MY_ARG = %(p2_param1)s
MY_OTHER_ARG = %(p2_param2)s

[plugin p3]
SETUP_CLASS = %(p3_class)s
MY_ARG = %(p3_param1)s
MY_OTHER_ARG = %(p3_param2)s
MY_OTHER_OTHER_ARG = %(p3_param3)s

[permission s1]
protocol = %(s1_protocol)s
from_port = %(s1_from_port)s
to_port = %(s1_to_port)s
cidr_ip = %(s1_cidr_ip)s

[permission s2]
protocol = %(s2_protocol)s
from_port = %(s2_from_port)s
to_port = %(s2_to_port)s
cidr_ip = %(s2_cidr_ip)s

[permission s3]
from_port = %(s3_from_port)s
to_port = %(s3_to_port)s

[cluster c1]
KEYNAME = %(c1_keyname)s
CLUSTER_SIZE = %(c1_size)s
CLUSTER_USER = %(c1_user)s
CLUSTER_SHELL = %(c1_shell)s
MASTER_IMAGE_ID = %(c1_master_id)s
MASTER_INSTANCE_TYPE = %(c1_master_type)s
NODE_IMAGE_ID = %(c1_node_id)s
NODE_INSTANCE_TYPE = %(c1_node_type)s
AVAILABILITY_ZONE = %(c1_zone)s
VOLUMES = %(c1_vols)s
PLUGINS = %(c1_plugs)s

[cluster c2]
EXTENDS=%(c2_extends)s
KEYNAME = %(c2_keyname)s
CLUSTER_SIZE= %(c2_size)s
MASTER_INSTANCE_TYPE = %(c2_master_type)s
NODE_INSTANCE_TYPE = %(c2_node_type)s
VOLUMES = %(c2_vols)s

[cluster c3]
EXTENDS=%(c3_extends)s
KEYNAME = %(c3_keyname)s
CLUSTER_SIZE= %(c3_size)s
VOLUMES = %(c3_vols)s

[cluster c4]
EXTENDS=%(c4_extends)s
PERMISSIONS=%(c4_permissions)s
"""

########NEW FILE########
__FILENAME__ = sge_balancer
# Copyright 2009-2014 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

qhost_xml = """<?xml version='1.0'?>
<qhost xmlns:xsd="http://gridengine.sunsource.net/source/browse/*checkout*/\
gridengine/source/dist/util/resources/schemas/qhost/qhost.xsd?revision=1.2">
 <host name='global'>
   <hostvalue name='arch_string'>-</hostvalue>
   <hostvalue name='num_proc'>-</hostvalue>
   <hostvalue name='load_avg'>-</hostvalue>
   <hostvalue name='mem_total'>-</hostvalue>
   <hostvalue name='mem_used'>-</hostvalue>
   <hostvalue name='swap_total'>-</hostvalue>
   <hostvalue name='swap_used'>-</hostvalue>
 </host>
 <host name='ip-10-196-142-180.ec2.internal'>
   <hostvalue name='arch_string'>lx24-x86</hostvalue>
   <hostvalue name='num_proc'>1</hostvalue>
   <hostvalue name='load_avg'>0.03</hostvalue>
   <hostvalue name='mem_total'>1.7G</hostvalue>
   <hostvalue name='mem_used'>75.4M</hostvalue>
   <hostvalue name='swap_total'>896.0M</hostvalue>
   <hostvalue name='swap_used'>0.0</hostvalue>
 </host>
 <host name='ip-10-196-214-162.ec2.internal'>
   <hostvalue name='arch_string'>lx24-x86</hostvalue>
   <hostvalue name='num_proc'>1</hostvalue>
   <hostvalue name='load_avg'>0.21</hostvalue>
   <hostvalue name='mem_total'>1.7G</hostvalue>
   <hostvalue name='mem_used'>88.9M</hostvalue>
   <hostvalue name='swap_total'>896.0M</hostvalue>
   <hostvalue name='swap_used'>0.0</hostvalue>
 </host>
 <host name='ip-10-196-215-50.ec2.internal'>
   <hostvalue name='arch_string'>lx24-x86</hostvalue>
   <hostvalue name='num_proc'>1</hostvalue>
   <hostvalue name='load_avg'>0.06</hostvalue>
   <hostvalue name='mem_total'>1.7G</hostvalue>
   <hostvalue name='mem_used'>75.9M</hostvalue>
   <hostvalue name='swap_total'>896.0M</hostvalue>
   <hostvalue name='swap_used'>0.0</hostvalue>
 </host>
</qhost>"""

qstat_xml = """<?xml version='1.0'?>
<job_info  xmlns:xsd="http://gridengine.sunsource.net/source/browse/*checkout*\
/gridengine/source/dist/util/resources/schemas/qstat/qstat.xsd?revision=1.11">
  <queue_info>
    <Queue-List>
      <name>all.q@ip-10-196-142-180.ec2.internal</name>
      <qtype>BIP</qtype>
      <slots_used>0</slots_used>
      <slots_resv>0</slots_resv>
      <slots_total>8</slots_total>
      <load_avg>0.01000</load_avg>
      <arch>linux-x64</arch>
      <job_list state="running">
        <JB_job_number>1</JB_job_number>
        <JAT_prio>0.55500</JAT_prio>
        <JB_name>sleep</JB_name>
        <JB_owner>root</JB_owner>
        <state>r</state>
        <JAT_start_time>2010-06-18T23:39:24</JAT_start_time>
        <queue_name>all.q@ip-10-196-142-180.ec2.internal</queue_name>
        <slots>1</slots>
      </job_list>
    </Queue-List>
    <Queue-List>
      <name>all.q@ip-10-196-215-50.ec2.internal</name>
      <qtype>BIP</qtype>
      <slots_used>0</slots_used>
      <slots_resv>0</slots_resv>
      <slots_total>8</slots_total>
      <load_avg>0.01000</load_avg>
      <arch>linux-x64</arch>
      <job_list state="running">
        <JB_job_number>2</JB_job_number>
        <JAT_prio>0.55500</JAT_prio>
        <JB_name>sleep</JB_name>
        <JB_owner>root</JB_owner>
        <state>r</state>
        <JAT_start_time>2010-06-18T23:39:24</JAT_start_time>
        <queue_name>all.q@ip-10-196-215-50.ec2.internal</queue_name>
        <slots>1</slots>
      </job_list>
    </Queue-List>
    <Queue-List>
      <name>all.q@ip-10-196-214-162.ec2.internal</name>
      <qtype>BIP</qtype>
      <slots_used>0</slots_used>
      <slots_resv>0</slots_resv>
      <slots_total>8</slots_total>
      <load_avg>0.01000</load_avg>
      <arch>linux-x64</arch>
      <job_list state="running">
        <JB_job_number>3</JB_job_number>
        <JAT_prio>0.55500</JAT_prio>
        <JB_name>sleep</JB_name>
        <JB_owner>root</JB_owner>
        <state>r</state>
        <JAT_start_time>2010-06-18T23:39:24</JAT_start_time>
        <queue_name>all.q@ip-10-196-214-162.ec2.internal</queue_name>
        <slots>1</slots>
      </job_list>
    </Queue-List>
  </queue_info>
  <job_info>
    <job_list state="pending">
      <JB_job_number>4</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sleep</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-06-18T23:39:14</JB_submission_time>
      <queue_name></queue_name>
      <slots>1</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>5</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sleep</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-06-18T23:39:14</JB_submission_time>
      <queue_name></queue_name>
      <slots>1</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>6</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sleep</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-06-18T23:39:14</JB_submission_time>
      <queue_name></queue_name>
      <slots>1</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>7</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sleep</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-06-18T23:39:15</JB_submission_time>
      <queue_name></queue_name>
      <slots>1</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>8</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sleep</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-06-18T23:39:15</JB_submission_time>
      <queue_name></queue_name>
      <slots>1</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>9</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sleep</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-06-18T23:39:16</JB_submission_time>
      <queue_name></queue_name>
      <slots>1</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>10</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sleep</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-06-18T23:39:16</JB_submission_time>
      <queue_name></queue_name>
      <slots>1</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>11</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sleep</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-06-18T23:39:17</JB_submission_time>
      <queue_name></queue_name>
      <slots>1</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>12</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sleep</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-06-18T23:39:35</JB_submission_time>
      <queue_name></queue_name>
      <slots>1</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>13</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sleep</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-06-18T23:39:35</JB_submission_time>
      <queue_name></queue_name>
      <slots>1</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>14</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sleep</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-06-18T23:39:36</JB_submission_time>
      <queue_name></queue_name>
      <slots>1</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>15</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sleep</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-06-18T23:39:36</JB_submission_time>
      <queue_name></queue_name>
      <slots>1</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>16</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sleep</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-06-18T23:39:37</JB_submission_time>
      <queue_name></queue_name>
      <slots>1</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>17</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sleep</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-06-18T23:39:37</JB_submission_time>
      <queue_name></queue_name>
      <slots>1</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>18</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sleep</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-06-18T23:39:38</JB_submission_time>
      <queue_name></queue_name>
      <slots>1</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>19</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sleep</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-06-18T23:39:38</JB_submission_time>
      <queue_name></queue_name>
      <slots>1</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>20</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sleep</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-06-18T23:39:38</JB_submission_time>
      <queue_name></queue_name>
      <slots>1</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>21</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sleep</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-06-18T23:39:39</JB_submission_time>
      <queue_name></queue_name>
      <slots>1</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>22</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sleep</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-06-18T23:39:39</JB_submission_time>
      <queue_name></queue_name>
      <slots>1</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>23</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sleep</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-06-18T23:39:40</JB_submission_time>
      <queue_name></queue_name>
      <slots>1</slots>
    </job_list>
  </job_info>
</job_info>"""

loaded_qhost_xml = """<?xml version='2.0'?>
<qhost xmlns:xsd="http://gridengine.sunsource.net/source/browse/*checkout*/\
gridengine/source/dist/util/resources/schemas/qhost/qhost.xsd?revision=1.2">
 <host name='global'>
   <hostvalue name='arch_string'>-</hostvalue>
   <hostvalue name='num_proc'>-</hostvalue>
   <hostvalue name='load_avg'>-</hostvalue>
   <hostvalue name='mem_total'>-</hostvalue>
   <hostvalue name='mem_used'>-</hostvalue>
   <hostvalue name='swap_total'>-</hostvalue>
   <hostvalue name='swap_used'>-</hostvalue>
 </host>
 <host name='domU-12-31-39-0B-C4-61.compute-1.internal'>
   <hostvalue name='arch_string'>lx24-amd64</hostvalue>
   <hostvalue name='num_proc'>8</hostvalue>
   <hostvalue name='load_avg'>8.32</hostvalue>
   <hostvalue name='mem_total'>7.0G</hostvalue>
   <hostvalue name='mem_used'>997.4M</hostvalue>
   <hostvalue name='swap_total'>0.0</hostvalue>
   <hostvalue name='swap_used'>0.0</hostvalue>
 </host>
 <host name='domU-12-31-39-0B-C4-C1.compute-1.internal'>
   <hostvalue name='arch_string'>lx24-amd64</hostvalue>
   <hostvalue name='num_proc'>8</hostvalue>
   <hostvalue name='load_avg'>9.65</hostvalue>
   <hostvalue name='mem_total'>7.0G</hostvalue>
   <hostvalue name='mem_used'>1.0G</hostvalue>
   <hostvalue name='swap_total'>0.0</hostvalue>
   <hostvalue name='swap_used'>0.0</hostvalue>
 </host>
 <host name='domU-12-31-39-0B-C6-51.compute-1.internal'>
   <hostvalue name='arch_string'>lx24-amd64</hostvalue>
   <hostvalue name='num_proc'>8</hostvalue>
   <hostvalue name='load_avg'>8.25</hostvalue>
   <hostvalue name='mem_total'>7.0G</hostvalue>
   <hostvalue name='mem_used'>996.6M</hostvalue>
   <hostvalue name='swap_total'>0.0</hostvalue>
   <hostvalue name='swap_used'>0.0</hostvalue>
 </host>
 <host name='domU-12-31-39-0E-FC-31.compute-1.internal'>
   <hostvalue name='arch_string'>lx24-amd64</hostvalue>
   <hostvalue name='num_proc'>8</hostvalue>
   <hostvalue name='load_avg'>8.21</hostvalue>
   <hostvalue name='mem_total'>7.0G</hostvalue>
   <hostvalue name='mem_used'>997.2M</hostvalue>
   <hostvalue name='swap_total'>0.0</hostvalue>
   <hostvalue name='swap_used'>0.0</hostvalue>
 </host>
 <host name='domU-12-31-39-0E-FC-71.compute-1.internal'>
   <hostvalue name='arch_string'>lx24-amd64</hostvalue>
   <hostvalue name='num_proc'>8</hostvalue>
   <hostvalue name='load_avg'>8.10</hostvalue>
   <hostvalue name='mem_total'>7.0G</hostvalue>
   <hostvalue name='mem_used'>997.0M</hostvalue>
   <hostvalue name='swap_total'>0.0</hostvalue>
   <hostvalue name='swap_used'>0.0</hostvalue>
 </host>
 <host name='domU-12-31-39-0E-FC-D1.compute-1.internal'>
   <hostvalue name='arch_string'>lx24-amd64</hostvalue>
   <hostvalue name='num_proc'>8</hostvalue>
   <hostvalue name='load_avg'>8.31</hostvalue>
   <hostvalue name='mem_total'>7.0G</hostvalue>
   <hostvalue name='mem_used'>996.7M</hostvalue>
   <hostvalue name='swap_total'>0.0</hostvalue>
   <hostvalue name='swap_used'>0.0</hostvalue>
 </host>
 <host name='domU-12-31-39-0E-FD-01.compute-1.internal'>
   <hostvalue name='arch_string'>lx24-amd64</hostvalue>
   <hostvalue name='num_proc'>8</hostvalue>
   <hostvalue name='load_avg'>8.08</hostvalue>
   <hostvalue name='mem_total'>7.0G</hostvalue>
   <hostvalue name='mem_used'>997.3M</hostvalue>
   <hostvalue name='swap_total'>0.0</hostvalue>
   <hostvalue name='swap_used'>0.0</hostvalue>
 </host>
 <host name='domU-12-31-39-0E-FD-81.compute-1.internal'>
   <hostvalue name='arch_string'>lx24-amd64</hostvalue>
   <hostvalue name='num_proc'>8</hostvalue>
   <hostvalue name='load_avg'>8.12</hostvalue>
   <hostvalue name='mem_total'>7.0G</hostvalue>
   <hostvalue name='mem_used'>995.7M</hostvalue>
   <hostvalue name='swap_total'>0.0</hostvalue>
   <hostvalue name='swap_used'>0.0</hostvalue>
 </host>
 <host name='domU-12-31-39-0E-FE-51.compute-1.internal'>
   <hostvalue name='arch_string'>lx24-amd64</hostvalue>
   <hostvalue name='num_proc'>8</hostvalue>
   <hostvalue name='load_avg'>8.06</hostvalue>
   <hostvalue name='mem_total'>7.0G</hostvalue>
   <hostvalue name='mem_used'>996.8M</hostvalue>
   <hostvalue name='swap_total'>0.0</hostvalue>
   <hostvalue name='swap_used'>0.0</hostvalue>
 </host>
 <host name='domU-12-31-39-0E-FE-71.compute-1.internal'>
   <hostvalue name='arch_string'>lx24-amd64</hostvalue>
   <hostvalue name='num_proc'>8</hostvalue>
   <hostvalue name='load_avg'>8.17</hostvalue>
   <hostvalue name='mem_total'>7.0G</hostvalue>
   <hostvalue name='mem_used'>996.1M</hostvalue>
   <hostvalue name='swap_total'>0.0</hostvalue>
   <hostvalue name='swap_used'>0.0</hostvalue>
 </host>
</qhost>"""

qacct_txt = """==============================================================
qname        all.q
hostname     domU-12-31-38-00-A6-41.compute-1.internal
group        root
owner        root
project      NONE
department   defaultdepartment
jobname      sleep
jobnumber    2
taskid       undefined
account      sge
priority     0
qsub_time    Thu Jul 15 18:18:33 2010
start_time   Thu Jul 15 18:18:41 2010
end_time     Thu Jul 15 18:19:41 2010
granted_pe   NONE
slots        1
failed       0
exit_status  0
ru_wallclock 60
ru_utime     0.000
ru_stime     0.000
ru_maxrss    0
ru_ixrss     0
ru_ismrss    0
ru_idrss     0
ru_isrss     0
ru_minflt    771
ru_majflt    0
ru_nswap     0
ru_inblock   16
ru_oublock   8
ru_msgsnd    0
ru_msgrcv    0
ru_nsignals  0
ru_nvcsw     4
ru_nivcsw    0
cpu          0.000
mem          0.000
io           0.000
iow          0.000
maxvmem      2.902M
arid         undefined
==============================================================
qname        all.q
hostname     domU-12-31-38-00-A5-A1.compute-1.internal
group        root
owner        root
project      NONE
department   defaultdepartment
jobname      sleep
jobnumber    1
taskid       undefined
account      sge
priority     0
qsub_time    Thu Jul 15 18:18:31 2010
start_time   Thu Jul 15 18:18:41 2010
end_time     Thu Jul 15 18:19:41 2010
granted_pe   NONE
slots        1
failed       0
exit_status  0
ru_wallclock 60
ru_utime     0.000
ru_stime     0.000
ru_maxrss    0
ru_ixrss     0
ru_ismrss    0
ru_idrss     0
ru_isrss     0
ru_minflt    792
ru_majflt    0
ru_nswap     0
ru_inblock   16
ru_oublock   160
ru_msgsnd    0
ru_msgrcv    0
ru_nsignals  0
ru_nvcsw     86
ru_nivcsw    0
cpu          0.000
mem          0.000
io           0.000
iow          0.000
maxvmem      2.902M
arid         undefined
==============================================================
qname        all.q
hostname     domU-12-31-38-00-A6-41.compute-1.internal
group        root
owner        root
project      NONE
department   defaultdepartment
jobname      sleep
jobnumber    4
taskid       undefined
account      sge
priority     0
qsub_time    Thu Jul 15 18:18:35 2010
start_time   Thu Jul 15 18:19:56 2010
end_time     Thu Jul 15 18:20:56 2010
granted_pe   NONE
slots        1
failed       0
exit_status  0
ru_wallclock 60
ru_utime     0.010
ru_stime     0.000
ru_maxrss    0
ru_ixrss     0
ru_ismrss    0
ru_idrss     0
ru_isrss     0
ru_minflt    773
ru_majflt    0
ru_nswap     0
ru_inblock   0
ru_oublock   8
ru_msgsnd    0
ru_msgrcv    0
ru_nsignals  0
ru_nvcsw     2
ru_nivcsw    1
cpu          0.010
mem          0.000
io           0.000
iow          0.000
maxvmem      0.000
arid         undefined
==============================================================
qname        all.q
hostname     domU-12-31-38-00-A5-A1.compute-1.internal
group        root
owner        root
project      NONE
department   defaultdepartment
jobname      sleep
jobnumber    3
taskid       undefined
account      sge
priority     0
qsub_time    Thu Jul 15 18:18:34 2010
start_time   Thu Jul 15 18:19:56 2010
end_time     Thu Jul 15 18:20:56 2010
granted_pe   NONE
slots        1
failed       0
exit_status  0
ru_wallclock 60
ru_utime     0.000
ru_stime     0.010
ru_maxrss    0
ru_ixrss     0
ru_ismrss    0
ru_idrss     0
ru_isrss     0
ru_minflt    790
ru_majflt    0
ru_nswap     0
ru_inblock   0
ru_oublock   160
ru_msgsnd    0
ru_msgrcv    0
ru_nsignals  0
ru_nvcsw     84
ru_nivcsw    0
cpu          0.010
mem          0.000
io           0.000
iow          0.000
maxvmem      2.902M
arid         undefined
==============================================================
qname        all.q
hostname     domU-12-31-38-00-A6-41.compute-1.internal
group        root
owner        root
project      NONE
department   defaultdepartment
jobname      sleep
jobnumber    6
taskid       undefined
account      sge
priority     0
qsub_time    Thu Jul 15 18:18:38 2010
start_time   Thu Jul 15 18:21:11 2010
end_time     Thu Jul 15 18:22:11 2010
granted_pe   NONE
slots        1
failed       0
exit_status  0
ru_wallclock 60
ru_utime     0.010
ru_stime     0.000
ru_maxrss    0
ru_ixrss     0
ru_ismrss    0
ru_idrss     0
ru_isrss     0
ru_minflt    773
ru_majflt    0
ru_nswap     0
ru_inblock   0
ru_oublock   8
ru_msgsnd    0
ru_msgrcv    0
ru_nsignals  0
ru_nvcsw     2
ru_nivcsw    1
cpu          0.010
mem          0.000
io           0.000
iow          0.000
maxvmem      2.902M
arid         undefined
==============================================================
qname        all.q
hostname     domU-12-31-38-00-A5-A1.compute-1.internal
group        root
owner        root
project      NONE
department   defaultdepartment
jobname      sleep
jobnumber    5
taskid       undefined
account      sge
priority     0
qsub_time    Thu Jul 15 18:18:36 2010
start_time   Thu Jul 15 18:21:11 2010
end_time     Thu Jul 15 18:22:11 2010
granted_pe   NONE
slots        1
failed       0
exit_status  0
ru_wallclock 60
ru_utime     0.000
ru_stime     0.000
ru_maxrss    0
ru_ixrss     0
ru_ismrss    0
ru_idrss     0
ru_isrss     0
ru_minflt    792
ru_majflt    0
ru_nswap     0
ru_inblock   0
ru_oublock   160
ru_msgsnd    0
ru_msgrcv    0
ru_nsignals  0
ru_nvcsw     84
ru_nivcsw    0
cpu          0.000
mem          0.000
io           0.000
iow          0.000
maxvmem      2.902M
arid         undefined
==============================================================
qname        all.q
hostname     domU-12-31-38-00-A6-41.compute-1.internal
group        root
owner        root
project      NONE
department   defaultdepartment
jobname      sleep
jobnumber    7
taskid       undefined
account      sge
priority     0
qsub_time    Thu Jul 15 18:34:13 2010
start_time   Thu Jul 15 18:34:26 2010
end_time     Thu Jul 15 18:35:26 2010
granted_pe   NONE
slots        1
failed       0
exit_status  0
ru_wallclock 60
ru_utime     0.010
ru_stime     0.000
ru_maxrss    0
ru_ixrss     0
ru_ismrss    0
ru_idrss     0
ru_isrss     0
ru_minflt    773
ru_majflt    0
ru_nswap     0
ru_inblock   0
ru_oublock   8
ru_msgsnd    0
ru_msgrcv    0
ru_nsignals  0
ru_nvcsw     2
ru_nivcsw    1
cpu          0.010
mem          0.000
io           0.000
iow          0.000
maxvmem      2.902M
arid         undefined
==============================================================
qname        all.q
hostname     domU-12-31-38-00-A6-41.compute-1.internal
group        root
owner        root
project      NONE
department   defaultdepartment
jobname      sleep
jobnumber    8
taskid       undefined
account      sge
priority     0
qsub_time    Thu Jul 15 18:34:14 2010
start_time   Thu Jul 15 18:35:41 2010
end_time     Thu Jul 15 18:36:41 2010
granted_pe   NONE
slots        1
failed       0
exit_status  0
ru_wallclock 60
ru_utime     0.000
ru_stime     0.010
ru_maxrss    0
ru_ixrss     0
ru_ismrss    0
ru_idrss     0
ru_isrss     0
ru_minflt    773
ru_majflt    0
ru_nswap     0
ru_inblock   0
ru_oublock   8
ru_msgsnd    0
ru_msgrcv    0
ru_nsignals  0
ru_nvcsw     2
ru_nivcsw    0
cpu          0.010
mem          0.000
io           0.000
iow          0.000
maxvmem      2.902M
arid         undefined
==============================================================
qname        all.q
hostname     domU-12-31-38-00-A6-41.compute-1.internal
group        root
owner        root
project      NONE
department   defaultdepartment
jobname      sleep
jobnumber    9
taskid       undefined
account      sge
priority     0
qsub_time    Thu Jul 15 18:34:14 2010
start_time   Thu Jul 15 18:36:56 2010
end_time     Thu Jul 15 18:37:56 2010
granted_pe   NONE
slots        1
failed       0
exit_status  0
ru_wallclock 60
ru_utime     0.010
ru_stime     0.000
ru_maxrss    0
ru_ixrss     0
ru_ismrss    0
ru_idrss     0
ru_isrss     0
ru_minflt    775
ru_majflt    0
ru_nswap     0
ru_inblock   0
ru_oublock   8
ru_msgsnd    0
ru_msgrcv    0
ru_nsignals  0
ru_nvcsw     2
ru_nivcsw    0
cpu          0.010
mem          0.000
io           0.000
iow          0.000
maxvmem      2.902M
arid         undefined
==============================================================
qname        all.q
hostname     domU-12-31-38-00-A6-41.compute-1.internal
group        root
owner        root
project      NONE
department   defaultdepartment
jobname      sleep
jobnumber    10
taskid       undefined
account      sge
priority     0
qsub_time    Thu Jul 15 18:34:15 2010
start_time   Thu Jul 15 18:38:11 2010
end_time     Thu Jul 15 18:39:11 2010
granted_pe   NONE
slots        1
failed       0
exit_status  0
ru_wallclock 60
ru_utime     0.000
ru_stime     0.000
ru_maxrss    0
ru_ixrss     0
ru_ismrss    0
ru_idrss     0
ru_isrss     0
ru_minflt    774
ru_majflt    0
ru_nswap     0
ru_inblock   0
ru_oublock   8
ru_msgsnd    0
ru_msgrcv    0
ru_nsignals  0
ru_nvcsw     2
ru_nivcsw    0
cpu          0.000
mem          0.000
io           0.000
iow          0.000
maxvmem      2.902M
arid         undefined
==============================================================
qname        all.q
hostname     domU-12-31-38-00-A6-41.compute-1.internal
group        root
owner        root
project      NONE
department   defaultdepartment
jobname      sleep
jobnumber    11
taskid       undefined
account      sge
priority     0
qsub_time    Thu Jul 15 18:34:15 2010
start_time   Thu Jul 15 18:39:26 2010
end_time     Thu Jul 15 18:40:26 2010
granted_pe   NONE
slots        1
failed       0
exit_status  0
ru_wallclock 60
ru_utime     0.010
ru_stime     0.000
ru_maxrss    0
ru_ixrss     0
ru_ismrss    0
ru_idrss     0
ru_isrss     0
ru_minflt    775
ru_majflt    0
ru_nswap     0
ru_inblock   0
ru_oublock   8
ru_msgsnd    0
ru_msgrcv    0
ru_nsignals  0
ru_nvcsw     2
ru_nivcsw    0
cpu          0.010
mem          0.000
io           0.000
iow          0.000
maxvmem      2.902M
arid         undefined
==============================================================
qname        all.q
hostname     domU-12-31-38-00-A6-41.compute-1.internal
group        root
owner        root
project      NONE
department   defaultdepartment
jobname      sleep
jobnumber    12
taskid       undefined
account      sge
priority     0
qsub_time    Thu Jul 15 18:34:16 2010
start_time   Thu Jul 15 18:40:41 2010
end_time     Thu Jul 15 18:41:41 2010
granted_pe   NONE
slots        1
failed       0
exit_status  0
ru_wallclock 60
ru_utime     0.000
ru_stime     0.000
ru_maxrss    0
ru_ixrss     0
ru_ismrss    0
ru_idrss     0
ru_isrss     0
ru_minflt    775
ru_majflt    0
ru_nswap     0
ru_inblock   0
ru_oublock   8
ru_msgsnd    0
ru_msgrcv    0
ru_nsignals  0
ru_nvcsw     2
ru_nivcsw    0
cpu          0.000
mem          0.000
io           0.000
iow          0.000
maxvmem      2.902M
arid         undefined
==============================================================
qname        all.q
hostname     domU-12-31-38-00-A6-41.compute-1.internal
group        root
owner        root
project      NONE
department   defaultdepartment
jobname      sleep
jobnumber    13
taskid       undefined
account      sge
priority     0
qsub_time    Thu Jul 15 18:34:16 2010
start_time   Thu Jul 15 18:41:56 2010
end_time     Thu Jul 15 18:42:56 2010
granted_pe   NONE
slots        1
failed       0
exit_status  0
ru_wallclock 60
ru_utime     0.000
ru_stime     0.000
ru_maxrss    0
ru_ixrss     0
ru_ismrss    0
ru_idrss     0
ru_isrss     0
ru_minflt    774
ru_majflt    0
ru_nswap     0
ru_inblock   0
ru_oublock   8
ru_msgsnd    0
ru_msgrcv    0
ru_nsignals  0
ru_nvcsw     2
ru_nivcsw    0
cpu          0.000
mem          0.000
io           0.000
iow          0.000
maxvmem      2.902M
arid         undefined
==============================================================
qname        all.q
hostname     domU-12-31-38-00-A6-41.compute-1.internal
group        root
owner        root
project      NONE
department   defaultdepartment
jobname      sleep
jobnumber    14
taskid       undefined
account      sge
priority     0
qsub_time    Thu Jul 15 18:34:17 2010
start_time   Thu Jul 15 18:43:11 2010
end_time     Thu Jul 15 18:44:11 2010
granted_pe   NONE
slots        1
failed       0
exit_status  0
ru_wallclock 60
ru_utime     0.000
ru_stime     0.000
ru_maxrss    0
ru_ixrss     0
ru_ismrss    0
ru_idrss     0
ru_isrss     0
ru_minflt    774
ru_majflt    0
ru_nswap     0
ru_inblock   0
ru_oublock   8
ru_msgsnd    0
ru_msgrcv    0
ru_nsignals  0
ru_nvcsw     2
ru_nivcsw    0
cpu          0.000
mem          0.000
io           0.000
iow          0.000
maxvmem      2.902M
arid         undefined
==============================================================
qname        all.q
hostname     domU-12-31-38-00-A6-41.compute-1.internal
group        root
owner        root
project      NONE
department   defaultdepartment
jobname      sleep
jobnumber    15
taskid       undefined
account      sge
priority     0
qsub_time    Thu Jul 15 18:34:17 2010
start_time   Thu Jul 15 18:44:26 2010
end_time     Thu Jul 15 18:45:26 2010
granted_pe   NONE
slots        1
failed       0
exit_status  0
ru_wallclock 60
ru_utime     0.000
ru_stime     0.010
ru_maxrss    0
ru_ixrss     0
ru_ismrss    0
ru_idrss     0
ru_isrss     0
ru_minflt    773
ru_majflt    0
ru_nswap     0
ru_inblock   0
ru_oublock   8
ru_msgsnd    0
ru_msgrcv    0
ru_nsignals  0
ru_nvcsw     2
ru_nivcsw    1
cpu          0.010
mem          0.000
io           0.000
iow          0.000
maxvmem      2.902M
arid         undefined
==============================================================
qname        all.q
hostname     domU-12-31-38-00-A6-41.compute-1.internal
group        root
owner        root
project      NONE
department   defaultdepartment
jobname      sleep
jobnumber    16
taskid       undefined
account      sge
priority     0
qsub_time    Thu Jul 15 18:34:18 2010
start_time   Thu Jul 15 18:45:41 2010
end_time     Thu Jul 15 18:46:41 2010
granted_pe   NONE
slots        1
failed       0
exit_status  0
ru_wallclock 60
ru_utime     0.000
ru_stime     0.010
ru_maxrss    0
ru_ixrss     0
ru_ismrss    0
ru_idrss     0
ru_isrss     0
ru_minflt    772
ru_majflt    0
ru_nswap     0
ru_inblock   0
ru_oublock   8
ru_msgsnd    0
ru_msgrcv    0
ru_nsignals  0
ru_nvcsw     2
ru_nivcsw    1
cpu          0.010
mem          0.000
io           0.000
iow          0.000
maxvmem      2.902M
arid         undefined
==============================================================
qname        all.q
hostname     domU-12-31-38-00-A6-41.compute-1.internal
group        root
owner        root
project      NONE
department   defaultdepartment
jobname      sleep
jobnumber    17
taskid       undefined
account      sge
priority     0
qsub_time    Thu Jul 15 18:34:20 2010
start_time   Thu Jul 15 18:46:56 2010
end_time     Thu Jul 15 18:47:56 2010
granted_pe   NONE
slots        1
failed       0
exit_status  0
ru_wallclock 60
ru_utime     0.000
ru_stime     0.010
ru_maxrss    0
ru_ixrss     0
ru_ismrss    0
ru_idrss     0
ru_isrss     0
ru_minflt    774
ru_majflt    0
ru_nswap     0
ru_inblock   0
ru_oublock   8
ru_msgsnd    0
ru_msgrcv    0
ru_nsignals  0
ru_nvcsw     2
ru_nivcsw    0
cpu          0.010
mem          0.000
io           0.000
iow          0.000
maxvmem      2.902M
arid         undefined
==============================================================
qname        all.q
hostname     domU-12-31-38-00-A6-41.compute-1.internal
group        root
owner        root
project      NONE
department   defaultdepartment
jobname      sleep
jobnumber    18
taskid       undefined
account      sge
priority     0
qsub_time    Thu Jul 15 18:50:58 2010
start_time   Thu Jul 15 18:51:11 2010
end_time     Thu Jul 15 19:01:11 2010
granted_pe   NONE
slots        1
failed       0
exit_status  0
ru_wallclock 600
ru_utime     0.010
ru_stime     0.000
ru_maxrss    0
ru_ixrss     0
ru_ismrss    0
ru_idrss     0
ru_isrss     0
ru_minflt    773
ru_majflt    0
ru_nswap     0
ru_inblock   0
ru_oublock   8
ru_msgsnd    0
ru_msgrcv    0
ru_nsignals  0
ru_nvcsw     2
ru_nivcsw    1
cpu          0.010
mem          0.000
io           0.000
iow          0.000
maxvmem      2.902M
arid         undefined
Total System Usage
    WALLCLOCK         UTIME         STIME           CPU             \
MEMORY                 IO                IOW
====================================================================\
============================================
         1620         0.060         0.050         0.110              \
0.000              0.000              0.000
"""

loaded_qstat_xml = """<?xml version='1.0'?>
<job_info  xmlns:xsd="http://gridengine.sunsource.net/source/browse/*checkout\
*/gridengine/source/dist/util/resources/schemas/qstat/qstat.xsd?revision=1.11">
  <queue_info>
    <Queue-List>
      <name>all.q@domU-12-31-39-0B-C4-C1.compute-1.internal</name>
      <qtype>BIP</qtype>
      <slots_used>0</slots_used>
      <slots_resv>0</slots_resv>
      <slots_total>8</slots_total>
      <load_avg>0.01000</load_avg>
      <arch>linux-x64</arch>
      <job_list state="running">
        <JB_job_number>385</JB_job_number>
        <JAT_prio>0.55500</JAT_prio>
        <JB_name>sm-haar-str-kconico-r4-dc10</JB_name>
        <JB_owner>root</JB_owner>
        <state>r</state>
        <JAT_start_time>2010-07-08T04:40:46</JAT_start_time>
        <queue_name>\
all.q@domU-12-31-39-0B-C4-C1.compute-1.internal</queue_name>
        <slots>20</slots>
      </job_list>
      <job_list state="running">
        <JB_job_number>386</JB_job_number>
        <JAT_prio>0.55500</JAT_prio>
        <JB_name>sm-haar-str-kconico-r4-dc7</JB_name>
        <JB_owner>root</JB_owner>
        <state>r</state>
        <JAT_start_time>2010-07-08T04:40:47</JAT_start_time>
        <queue_name>\
all.q@domU-12-31-39-0B-C4-C1.compute-1.internal</queue_name>
        <slots>20</slots>
      </job_list>
      <job_list state="running">
        <JB_job_number>387</JB_job_number>
        <JAT_prio>0.55500</JAT_prio>
        <JB_name>sm-haar-str-kconico-r4-dc8</JB_name>
        <JB_owner>root</JB_owner>
        <state>r</state>
        <JAT_start_time>2010-07-08T04:40:47</JAT_start_time>
        <queue_name>\
all.q@domU-12-31-39-0B-C4-C1.compute-1.internal</queue_name>
        <slots>20</slots>
      </job_list>
      <job_list state="running">
        <JB_job_number>388</JB_job_number>
        <JAT_prio>0.55500</JAT_prio>
        <JB_name>sm-haar-str-kconico-r4-dc9</JB_name>
        <JB_owner>root</JB_owner>
        <state>r</state>
        <JAT_start_time>2010-07-08T04:40:47</JAT_start_time>
        <queue_name>\
all.q@domU-12-31-39-0B-C4-C1.compute-1.internal</queue_name>
        <slots>20</slots>
      </job_list>
    </Queue-List>
    <Queue-List>
      <name>all.q@domU-12-31-39-0B-C4-61.compute-1.internal</name>
      <qtype>BIP</qtype>
      <slots_used>0</slots_used>
      <slots_resv>0</slots_resv>
      <slots_total>8</slots_total>
      <load_avg>0.01000</load_avg>
      <arch>linux-x64</arch>
    </Queue-List>
    <Queue-List>
      <name>all.q@domU-12-31-39-0B-C6-51.compute-1.internal</name>
      <qtype>BIP</qtype>
      <slots_used>0</slots_used>
      <slots_resv>0</slots_resv>
      <slots_total>8</slots_total>
      <load_avg>0.01000</load_avg>
      <arch>linux-x64</arch>
    </Queue-List>
    <Queue-List>
      <name>all.q@domU-12-31-39-0E-FC-31.compute-1.internal</name>
      <qtype>BIP</qtype>
      <slots_used>0</slots_used>
      <slots_resv>0</slots_resv>
      <slots_total>8</slots_total>
      <load_avg>0.01000</load_avg>
      <arch>linux-x64</arch>
    </Queue-List>
    <Queue-List>
      <name>all.q@domU-12-31-39-0E-FC-71.compute-1.internal</name>
      <qtype>BIP</qtype>
      <slots_used>0</slots_used>
      <slots_resv>0</slots_resv>
      <slots_total>8</slots_total>
      <load_avg>0.01000</load_avg>
      <arch>linux-x64</arch>
    </Queue-List>
    <Queue-List>
      <name>all.q@domU-12-31-39-0E-FC-D1.compute-1.internal</name>
      <qtype>BIP</qtype>
      <slots_used>0</slots_used>
      <slots_resv>0</slots_resv>
      <slots_total>8</slots_total>
      <load_avg>0.01000</load_avg>
      <arch>linux-x64</arch>
    </Queue-List>
    <Queue-List>
      <name>all.q@domU-12-31-39-0E-FD-01.compute-1.internal</name>
      <qtype>BIP</qtype>
      <slots_used>0</slots_used>
      <slots_resv>0</slots_resv>
      <slots_total>8</slots_total>
      <load_avg>0.01000</load_avg>
      <arch>linux-x64</arch>
    </Queue-List>
    <Queue-List>
      <name>all.q@domU-12-31-39-0E-FD-81.compute-1.internal</name>
      <qtype>BIP</qtype>
      <slots_used>0</slots_used>
      <slots_resv>0</slots_resv>
      <slots_total>8</slots_total>
      <load_avg>0.01000</load_avg>
      <arch>linux-x64</arch>
    </Queue-List>
    <Queue-List>
      <name>all.q@domU-12-31-39-0E-FE-51.compute-1.internal</name>
      <qtype>BIP</qtype>
      <slots_used>0</slots_used>
      <slots_resv>0</slots_resv>
      <slots_total>8</slots_total>
      <load_avg>0.01000</load_avg>
      <arch>linux-x64</arch>
    </Queue-List>
    <Queue-List>
      <name>all.q@domU-12-31-39-0E-FE-71.compute-1.internal</name>
      <qtype>BIP</qtype>
      <slots_used>0</slots_used>
      <slots_resv>0</slots_resv>
      <slots_total>8</slots_total>
      <load_avg>0.01000</load_avg>
      <arch>linux-x64</arch>
    </Queue-List>
  </queue_info>
  <job_info>
    <job_list state="pending">
      <JB_job_number>389</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kconico-r5-dc10</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:32</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>390</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kconico-r5-dc7</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:32</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>391</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kconico-r5-dc8</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:32</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>392</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kconico-r5-dc9</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:32</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>393</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kconico-r6-dc10</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:32</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>394</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kconico-r6-dc7</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:32</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>395</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kconico-r6-dc8</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:32</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>396</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kconico-r6-dc9</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:32</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>397</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kconico-r7-dc10</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:32</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>398</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kconico-r7-dc7</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:32</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>399</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kconico-r7-dc8</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:32</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>400</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kconico-r7-dc9</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:32</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>401</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kconic-r4-dc10</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:32</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>402</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kconic-r4-dc7</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:32</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>403</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kconic-r4-dc8</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:32</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>404</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kconic-r4-dc9</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:32</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>405</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kconic-r5-dc10</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:32</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>406</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kconic-r5-dc7</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:32</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>407</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kconic-r5-dc8</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:32</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>408</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kconic-r5-dc9</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:32</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>409</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kconic-r6-dc10</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:32</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>410</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kconic-r6-dc7</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:32</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>411</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kconic-r6-dc8</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:32</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>412</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kconic-r6-dc9</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:32</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>413</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kconic-r7-dc10</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:32</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>414</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kconic-r7-dc7</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:32</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>415</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kconic-r7-dc8</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:32</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>416</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kconic-r7-dc9</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:32</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>417</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kcylo-r4-dc10</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:32</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>418</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kcylo-r4-dc7</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:32</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>419</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kcylo-r4-dc8</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:32</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>420</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kcylo-r4-dc9</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:32</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>421</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kcylo-r5-dc10</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:32</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>422</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kcylo-r5-dc7</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:32</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>423</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kcylo-r5-dc8</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:32</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>424</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kcylo-r5-dc9</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:32</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>425</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kcylo-r6-dc10</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:32</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>426</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kcylo-r6-dc7</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:32</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>427</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kcylo-r6-dc8</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:33</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>428</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kcylo-r6-dc9</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:33</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>429</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kcylo-r7-dc10</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:33</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>430</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kcylo-r7-dc7</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:33</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>431</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kcylo-r7-dc8</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:33</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>432</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kcylo-r7-dc9</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:33</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>433</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kcyl-r4-dc10</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:33</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>434</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kcyl-r4-dc7</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:33</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>435</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kcyl-r4-dc8</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:33</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>436</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kcyl-r4-dc9</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:33</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>437</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kcyl-r5-dc10</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:33</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>438</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kcyl-r5-dc7</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:33</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>439</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kcyl-r5-dc8</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:33</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>440</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kcyl-r5-dc9</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:33</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>441</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kcyl-r6-dc10</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:33</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>442</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kcyl-r6-dc7</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:33</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>443</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kcyl-r6-dc8</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:33</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>444</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kcyl-r6-dc9</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:33</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>445</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kcyl-r7-dc10</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:33</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>446</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kcyl-r7-dc7</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:33</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>447</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kcyl-r7-dc8</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:33</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>448</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kcyl-r7-dc9</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:33</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>449</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kquado-r4-dc10</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:33</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>450</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kquado-r4-dc7</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:33</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>451</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kquado-r4-dc8</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:33</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>452</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kquado-r4-dc9</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:33</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>453</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kquado-r5-dc10</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:33</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>454</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kquado-r5-dc7</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:33</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>455</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kquado-r5-dc8</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:33</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>456</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kquado-r5-dc9</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:33</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>457</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kquado-r6-dc10</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:33</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>458</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kquado-r6-dc7</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:33</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>459</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kquado-r6-dc8</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:33</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>460</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kquado-r6-dc9</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:33</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>461</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kquado-r7-dc10</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:33</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>462</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kquado-r7-dc7</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:33</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>463</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kquado-r7-dc8</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:33</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>464</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kquado-r7-dc9</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:33</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>465</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kquad-r4-dc10</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:33</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>466</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kquad-r4-dc7</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:33</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>467</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kquad-r4-dc8</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:33</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>468</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kquad-r4-dc9</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:33</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>469</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kquad-r5-dc10</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:33</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>470</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kquad-r5-dc7</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:33</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>471</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kquad-r5-dc8</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:33</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>472</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kquad-r5-dc9</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:33</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>473</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kquad-r6-dc10</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:33</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>474</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kquad-r6-dc7</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:33</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>475</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kquad-r6-dc8</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:33</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>476</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kquad-r6-dc9</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:33</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>477</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kquad-r7-dc10</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:33</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>478</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kquad-r7-dc7</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:33</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>479</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kquad-r7-dc8</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:33</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>480</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-haar-str-kquad-r7-dc9</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:33</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>481</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kconico-r4-dc10</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:34</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>482</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kconico-r4-dc7</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:34</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>483</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kconico-r4-dc8</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:34</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>484</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kconico-r4-dc9</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:34</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>485</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kconico-r5-dc10</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:34</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>486</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kconico-r5-dc7</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:34</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>487</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kconico-r5-dc8</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:34</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>488</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kconico-r5-dc9</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:34</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>489</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kconico-r6-dc10</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:34</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>490</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kconico-r6-dc7</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:34</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>491</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kconico-r6-dc8</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:34</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>492</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kconico-r6-dc9</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:34</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>493</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kconico-r7-dc10</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:34</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>494</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kconico-r7-dc7</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:34</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>495</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kconico-r7-dc8</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:34</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>496</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kconico-r7-dc9</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:34</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>497</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kconic-r4-dc10</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:34</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>498</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kconic-r4-dc7</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:34</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>499</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kconic-r4-dc8</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:34</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>500</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kconic-r4-dc9</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:34</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>501</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kconic-r5-dc10</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:34</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>502</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kconic-r5-dc7</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:34</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>503</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kconic-r5-dc8</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:34</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>504</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kconic-r5-dc9</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:34</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>505</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kconic-r6-dc10</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:34</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>506</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kconic-r6-dc7</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:34</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>507</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kconic-r6-dc8</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:34</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>508</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kconic-r6-dc9</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:34</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>509</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kconic-r7-dc10</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:34</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>510</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kconic-r7-dc7</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:34</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>511</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kconic-r7-dc8</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:34</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>512</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kconic-r7-dc9</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:34</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>513</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kcylo-r4-dc10</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:34</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>514</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kcylo-r4-dc7</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:34</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>515</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kcylo-r4-dc8</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:34</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>516</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kcylo-r4-dc9</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:34</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>517</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kcylo-r5-dc10</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:34</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>518</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kcylo-r5-dc7</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:34</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>519</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kcylo-r5-dc8</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:34</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>520</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kcylo-r5-dc9</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:34</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>521</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kcylo-r6-dc10</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:34</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>522</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kcylo-r6-dc7</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:34</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>523</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kcylo-r6-dc8</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:34</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>524</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kcylo-r6-dc9</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:34</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>525</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kcylo-r7-dc10</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:34</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>526</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kcylo-r7-dc7</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:34</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>527</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kcylo-r7-dc8</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:34</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>528</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kcylo-r7-dc9</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:34</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>529</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kcyl-r4-dc10</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:34</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>530</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kcyl-r4-dc7</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:34</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>531</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kcyl-r4-dc8</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:34</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>532</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kcyl-r4-dc9</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:34</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>533</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kcyl-r5-dc10</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:34</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>534</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kcyl-r5-dc7</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:35</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>535</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kcyl-r5-dc8</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:35</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>536</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kcyl-r5-dc9</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:35</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>537</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kcyl-r6-dc10</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:35</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>538</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kcyl-r6-dc7</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:35</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>539</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kcyl-r6-dc8</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:35</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>540</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kcyl-r6-dc9</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:35</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>541</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kcyl-r7-dc10</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:35</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>542</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kcyl-r7-dc7</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:35</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>543</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kcyl-r7-dc8</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:35</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>544</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kcyl-r7-dc9</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:35</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>545</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kquado-r4-dc10</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:35</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>546</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kquado-r4-dc7</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:35</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>547</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kquado-r4-dc8</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:35</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>548</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kquado-r4-dc9</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:35</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>549</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kquado-r5-dc10</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:35</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>550</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kquado-r5-dc7</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:35</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>551</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kquado-r5-dc8</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:35</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>552</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kquado-r5-dc9</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:35</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>553</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kquado-r6-dc10</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:35</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>554</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kquado-r6-dc7</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:35</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>555</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kquado-r6-dc8</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:35</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>556</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kquado-r6-dc9</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:35</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>557</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kquado-r7-dc10</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:35</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>558</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kquado-r7-dc7</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:35</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>559</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kquado-r7-dc8</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:35</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>560</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kquado-r7-dc9</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:35</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>561</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kquad-r4-dc10</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:35</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>562</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kquad-r4-dc7</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:35</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>563</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kquad-r4-dc8</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:35</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>564</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kquad-r4-dc9</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:35</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>565</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kquad-r5-dc10</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:35</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>566</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kquad-r5-dc7</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:35</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>567</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kquad-r5-dc8</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:35</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>568</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kquad-r5-dc9</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:35</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>569</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kquad-r6-dc10</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:35</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>570</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kquad-r6-dc7</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:35</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>571</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kquad-r6-dc8</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:35</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>572</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kquad-r6-dc9</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:35</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>573</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kquad-r7-dc10</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:35</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>574</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kquad-r7-dc7</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:35</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>575</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kquad-r7-dc8</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:35</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>576</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sm-main-kquad-r7-dc9</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-07-08T04:40:35</JB_submission_time>
      <queue_name></queue_name>
      <slots>20</slots>
    </job_list>
  </job_info>
</job_info>"""

########NEW FILE########
__FILENAME__ = test_cluster_validation
# Copyright 2009-2014 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

import os
import tempfile

from starcluster import exception
from starcluster.cluster import Cluster
from starcluster.tests import StarClusterTest


class TestClusterValidation(StarClusterTest):

    def test_plugin_loading(self):
        # default test template should have valid plugins by default
        # make them invalid
        cases = [
            {'p1_class': 'None'},
            {'p1_class': 'unittest.TestCase'},
        ]
        for case in cases:
            try:
                cfg = self.get_custom_config(**case)
                cfg.get_cluster_template('c1')
            except exception.PluginError:
                pass
            else:
                raise Exception(
                    'cluster allows non-valid plugin setup class (case: %s)' %
                    case)

    def test_cluster_size_validation(self):
        cases = [
            {'c1_size': -1},
            {'c1_size': 0},
        ]
        for case in cases:
            cfg = self.get_custom_config(**case)
            try:
                cluster = cfg.get_cluster_template('c1')
                cluster.validator.validate_cluster_size()
            except exception.ClusterValidationError:
                pass
            else:
                raise Exception(
                    'cluster allows invalid size (case: %s)' % case)

    def test_shell_validation(self):
        cases = [
            {'cluster_shell': ''},
            {'cluster_shell': 'nosh'},
            {'cluster_shell': 2},
        ]
        failed = self.__test_cases_from_cluster(
            cases, 'validate_shell_setting')
        if failed:
            raise Exception('cluster allows invalid cluster shell (cases: %s)'
                            % failed)

    def test_keypair_validation(self):
        tmpfile = tempfile.NamedTemporaryFile()
        tmp_file = tmpfile.name
        tmpfile.close()
        tmpdir = tempfile.mkdtemp()
        cases = [{'k1_location': tmp_file}, {'k1_location': tmpdir}]
        for case in cases:
            cfg = self.get_custom_config(**case)
            cluster = cfg.get_cluster_template('c1')
            try:
                cluster.validator.validate_keypair()
            except exception.ClusterValidationError:
                pass
            else:
                raise Exception('cluster allows invalid key_location')
        os.rmdir(tmpdir)

    def __test_cases_from_cfg(self, cases, test, cluster_name='c1'):
        """
        Tests all cases by loading a cluster template from the test config.
        This method will write a custom test config for each case using its
        settings.
        """
        failed = []
        for case in cases:
            cfg = self.get_custom_config(**case)
            cluster = cfg.get_cluster_template(cluster_name)
            try:
                getattr(cluster.validator, test)()
            except exception.ClusterValidationError, e:
                print "case: %s, error: %s" % (str(case), e)
                continue
            else:
                failed.append(case)
        return failed

    def __test_cases_from_cluster(self, cases, test):
        """
        Tests all cases by manually loading a cluster template using the
        Cluster class. All settings for a case are passed in as constructor
        keywords.  Avoids the config module by using the Cluster object
        directly to create a test case.
        """
        failed = []
        for case in cases:
            cluster = Cluster(**case)
            try:
                getattr(cluster.validator, test)()
            except exception.ClusterValidationError:
                continue
            else:
                failed.append(case)
        return failed

    def test_instance_type_validation(self):
        cases = [
            {'node_instance_type': 'asdf'},
            {'master_instance_type': 'fdsa', 'node_instance_type': 'm1.small'},
        ]
        failed = self.__test_cases_from_cluster(cases,
                                                "validate_instance_types")
        if failed:
            raise Exception(
                'cluster allows invalid instance type settings (cases: %s)' %
                failed)

    def test_ebs_validation(self):
        try:
            failed = self.__test_cases_from_cfg(
                [{'v1_device': '/dev/asd'}], 'validate_ebs_settings')
            raise Exception(
                'cluster allows invalid ebs settings (cases: %s)' % failed)
        except exception.InvalidDevice:
            pass
        try:
            failed = self.__test_cases_from_cfg(
                [{'v1_partition': -1}], 'validate_ebs_settings')
            raise Exception(
                'cluster allows invalid ebs settings (cases: %s)' % failed)
        except exception.InvalidPartition:
            pass
        cases = [
            {'v1_mount_path': 'home'},
            {'v1_mount_path': '/home', 'v2_mount_path': '/home'},
            {'v4_id': 'vol-abcdefg', 'v5_id': 'vol-abcdefg',
             'v4_partition': 2, 'v5_partition': 2, 'c1_vols': 'v4, v5'},
            {'v1_id': 'vol-abcdefg', 'v2_id': 'vol-gfedcba',
             'v1_device': '/dev/sdd', 'v2_device': '/dev/sdd',
             'c1_vols': 'v1, v2'},
            {'v1_id': 'vol-abcdefg', 'v2_id': 'vol-abcdefg',
             'v1_device': '/dev/sdz', 'v2_device': '/dev/sdd',
             'c1_vols': 'v1, v2'}
        ]
        failed = self.__test_cases_from_cfg(cases, 'validate_ebs_settings')
        if failed:
            raise Exception(
                'cluster allows invalid ebs settings (cases: %s)' % failed)

        cases = [
            {'v4_id': 'vol-abcdefg', 'v5_id': 'vol-abcdefg',
             'v4_partition': 1, 'v5_partition': 2, 'c1_vols': 'v4, v5'},
        ]
        passed = self.__test_cases_from_cfg(cases, 'validate_ebs_settings')
        if len(passed) != len(cases):
            raise Exception("validation fails on valid cases: %s" %
                            str(passed))

    def test_permission_validation(self):
        assert self.config.permissions.s3.ip_protocol == 'tcp'
        assert self.config.permissions.s3.cidr_ip == '0.0.0.0/0'
        cases = [
            {'s1_from_port': 90, 's1_to_port': 10},
            {'s1_from_port': -1},
            {'s1_cidr_ip': 'asdfasdf'},
        ]
        failed = self.__test_cases_from_cfg(cases,
                                            'validate_permission_settings',
                                            cluster_name='c4')
        if failed:
            raise Exception(
                "cluster allows invalid permission settings (cases %s)" %
                failed)

    # def test_image_validation(self):
    #     pass

    # def test_zone_validation(self):
    #     pass

    # def test_platform_validation(self):
    #     pass

########NEW FILE########
__FILENAME__ = test_config
# Copyright 2009-2014 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

import os
import copy
import tempfile

import logging
logging.disable(logging.WARN)

from starcluster import exception
from starcluster import tests
from starcluster import static
from starcluster import config
from starcluster import utils


class TestStarClusterConfig(tests.StarClusterTest):

    def test_valid_config_template(self):
        self.config

    def test_config_dne(self):
        tmp_file = tempfile.NamedTemporaryFile()
        non_existent_file = tmp_file.name
        tmp_file.close()
        assert not os.path.exists(non_existent_file)
        try:
            config.StarClusterConfig(non_existent_file, cache=True).load()
        except exception.ConfigNotFound:
            pass
        else:
            raise Exception('config loaded non-existent config file %s' %
                            non_existent_file)

    def test_get_cluster(self):
        try:
            self.config.get_cluster_template('no_such_cluster')
        except exception.ClusterTemplateDoesNotExist:
            pass
        else:
            raise Exception('config returned non-existent cluster')

    def test_int_required(self):
        cases = [{'c1_size': '-s'}, {'c1_size': 2.5}, {'v1_partition': 'asdf'},
                 {'v1_partition': 0.33}]
        for case in cases:
            try:
                self.get_custom_config(**case)
            except exception.ConfigError:
                pass
            else:
                raise Exception('config is not enforcing ints correctly')

    def test_bool_required(self):
        cases = [{'enable_experimental': 2}]
        for case in cases:
            try:
                self.get_custom_config(**case)
            except exception.ConfigError:
                pass
            else:
                raise Exception("config is not enforcing strs correctly")

    def test_missing_required(self):
        cfg = self.config._config
        section_copy = copy.deepcopy(cfg._sections)
        for setting in static.CLUSTER_SETTINGS:
            if not static.CLUSTER_SETTINGS[setting][1]:
                continue
            del cfg._sections['cluster c1'][setting]
            try:
                self.config.load()
            except exception.ConfigError:
                pass
            else:
                raise Exception(
                    "config is not enforcing required setting '%s'" % setting)
            cfg._sections = copy.deepcopy(section_copy)

    def test_volumes(self):
        c1 = self.config.get_cluster_template('c1')
        vols = c1.volumes
        assert len(vols) == 3
        assert 'v1' in vols
        v1 = vols['v1']
        assert 'volume_id' in v1 and v1['volume_id'] == 'vol-c999999'
        assert 'device' in v1 and v1['device'] == '/dev/sdj'
        assert 'partition' in v1 and v1['partition'] == '/dev/sdj1'
        assert 'mount_path' in v1 and v1['mount_path'] == '/volume1'
        assert 'v2' in vols
        v2 = vols['v2']
        assert 'volume_id' in v2 and v2['volume_id'] == 'vol-c888888'
        assert 'device' in v2 and v2['device'] == '/dev/sdk'
        assert 'partition' in v2 and v2['partition'] == '/dev/sdk1'
        assert 'mount_path' in v2 and v2['mount_path'] == '/volume2'
        assert 'v3' in vols
        v3 = vols['v3']
        assert 'volume_id' in v3 and v3['volume_id'] == 'vol-c777777'
        assert 'device' in v3 and v3['device'] == '/dev/sdl'
        assert 'partition' in v3 and v3['partition'] == '/dev/sdl1'
        assert 'mount_path' in v3 and v3['mount_path'] == '/volume3'

    def test_volume_not_defined(self):
        try:
            self.get_custom_config(**{'c1_vols': 'v1,v2,v2323'})
        except exception.ConfigError:
            pass
        else:
            raise Exception(
                'config allows non-existent volumes to be specified')

    def test_clusters(self):
        assert 'c1' in self.config.clusters
        assert 'c2' in self.config.clusters
        assert 'c3' in self.config.clusters

    def test_extends(self):
        c1 = self.config.clusters.get('c1')
        c2 = self.config.clusters.get('c2')
        c3 = self.config.clusters.get('c3')
        c2_settings = ['__name__', 'extends', 'keyname', 'key_location',
                       'cluster_size', 'node_instance_type',
                       'master_instance_type', 'volumes']
        c3_settings = ['__name__', 'extends', 'keyname', 'key_location',
                       'cluster_size', 'volumes']
        for key in c1:
            if key in c2 and key not in c2_settings:
                assert c2[key] == c1[key]
            else:
                # below only true for default test config
                # not required in general
                assert c2[key] != c1[key]
        for key in c2:
            if key in c3 and key not in c3_settings:
                assert c3[key] == c2[key]
            else:
                # below only true for default test config
                # not required in general
                assert c3[key] != c2[key]

    def test_order_invariance(self):
        """
        Loads all cluster sections in the test config in all possible orders
        (i.e. c1,c2,c3, c3,c1,c2, etc.) and test that the results are the same
        """
        cfg = self.config
        orig = cfg.clusters
        cfg.clusters = None
        sections = cfg._get_sections('cluster')
        for perm in utils.permute(sections):
            new = cfg._load_cluster_sections(perm)
            assert new == orig

    def test_plugins(self):
        c1 = self.config.get_cluster_template('c1')
        plugs = c1.plugins
        assert len(plugs) == 3
        # test that order is preserved
        p1, p2, p3 = plugs
        p1_name = p1.__name__
        p1_class = utils.get_fq_class_name(p1)
        p2_name = p2.__name__
        p2_class = utils.get_fq_class_name(p2)
        p3_name = p3.__name__
        p3_class = utils.get_fq_class_name(p3)
        assert p1_name == 'p1'
        assert p1_class == 'starcluster.tests.mytestplugin.SetupClass'
        assert p1.my_arg == '23'
        assert p1.my_other_arg == 'skidoo'
        assert p2_name == 'p2'
        setup_class2 = 'starcluster.tests.mytestplugin.SetupClass2'
        assert p2_class == setup_class2
        assert p2.my_arg == 'hello'
        assert p2.my_other_arg == 'world'
        assert p3_name == 'p3'
        setup_class3 = 'starcluster.tests.mytestplugin.SetupClass3'
        assert p3_class == setup_class3
        assert p3.my_arg == 'bon'
        assert p3.my_other_arg == 'jour'
        assert p3.my_other_other_arg == 'monsignour'

    def test_plugin_not_defined(self):
        try:
            self.get_custom_config(**{'c1_plugs': 'p1,p2,p233'})
        except exception.ConfigError:
            pass
        else:
            raise Exception(
                'config allows non-existent plugins to be specified')

    def test_keypairs(self):
        kpairs = self.config.keys
        assert len(kpairs) == 3
        k1 = kpairs.get('k1')
        k2 = kpairs.get('k2')
        k3 = kpairs.get('k3')
        dcfg = tests.templates.config.default_config
        k1_location = os.path.expanduser(dcfg['k1_location'])
        k2_location = dcfg['k2_location']
        k3_location = dcfg['k3_location']
        assert k1 and k1['key_location'] == k1_location
        assert k2 and k2['key_location'] == k2_location
        assert k3 and k3['key_location'] == k3_location

    def test_keypair_not_defined(self):
        try:
            self.get_custom_config(**{'c1_keyname': 'k2323'})
        except exception.ConfigError:
            pass
        else:
            raise Exception(
                'config allows non-existent keypairs to be specified')

    def test_invalid_config(self):
        """
        Test that reading a non-INI formatted file raises an exception
        """
        tmp_file = tempfile.NamedTemporaryFile()
        tmp_file.write(
            "<html>random garbage file with no section headings</html>")
        tmp_file.flush()
        try:
            config.StarClusterConfig(tmp_file.name, cache=True).load()
        except exception.ConfigHasNoSections:
            pass
        else:
            raise Exception("config allows non-INI formatted files")

    def test_empty_config(self):
        """
        Test that reading an empty config generates no errors and that aws
        credentials can be read from the environment.
        """
        aws_key = 'testkey'
        aws_secret_key = 'testsecret'
        os.environ['AWS_ACCESS_KEY_ID'] = aws_key
        os.environ['AWS_SECRET_ACCESS_KEY'] = aws_secret_key
        tmp_file = tempfile.NamedTemporaryFile()
        cfg = config.StarClusterConfig(tmp_file.name, cache=True).load()
        assert cfg.aws['aws_access_key_id'] == aws_key
        assert cfg.aws['aws_secret_access_key'] == aws_secret_key
        del os.environ['AWS_ACCESS_KEY_ID']
        del os.environ['AWS_SECRET_ACCESS_KEY']

    def test_cyclical_extends(self):
        """
        Test that cyclical extends in the config raises an exception
        """
        try:
            self.get_custom_config(**{'c2_extends': 'c3',
                                      'c3_extends': 'c2'})
            self.get_custom_config(**{'c2_extends': 'c3',
                                      'c3_extends': 'c4',
                                      'c4_extends': 'c2'})
        except exception.ConfigError:
            pass
        else:
            raise Exception('config allows cyclical extends graph')

    def test_choices(self):
        """
        Test that config enforces a value to be one of a list of choices if
        specified
        """
        try:
            self.get_custom_config(**{'c1_shell': 'blahblah'})
        except exception.ConfigError:
            pass
        else:
            raise Exception('config not enforcing choices for setting')

    def test_multiple_instance_types(self):
        """
        Test that config properly handles multiple instance types syntax
        (within node_instance_type setting)
        """
        invalid_cases = [
            {'c1_node_type': 'c1.xlarge:ami-asdffdas'},
            {'c1_node_type': 'c1.xlarge:3'},
            {'c1_node_type': 'c1.xlarge:ami-asdffdas:3'},
            {'c1_node_type': 'c1.xlarge:asdf:asdf:asdf,m1.small'},
            {'c1_node_type': 'c1.asdf:4, m1.small'},
            {'c1_node_type': 'c1.xlarge: 0, m1.small'},
            {'c1_node_type': 'c1.xlarge:-1, m1.small'}]
        for case in invalid_cases:
            try:
                self.get_custom_config(**case)
            except exception.ConfigError:
                pass
            else:
                raise Exception(('config allows invalid multiple instance ' +
                                 'type syntax: %s') % case)
        valid_cases = [
            {'c1_node_type': 'c1.xlarge:3, m1.small'},
            {'c1_node_type': 'c1.xlarge:ami-asdfasdf:3, m1.small'},
            {'c1_node_type': 'c1.xlarge:ami-asdfasdf:3, m1.large, m1.small'},
            {'c1_node_type': 'm1.large, c1.xlarge:ami-asdfasdf:3, m1.large, ' +
             'm1.small'},
            {'c1_node_type': 'c1.xlarge:ami-asdfasdf:2, m1.large:2, m1.small'},
        ]
        for case in valid_cases:
            try:
                self.get_custom_config(**case)
            except exception.ConfigError:
                raise Exception(('config rejects valid multiple instance ' +
                                 'type syntax: %s') % case)

    def test_inline_comments(self):
        """
        Test that config ignores inline comments.
        """
        invalid_case = {'c1_node_type': 'c1.xlarge:3, m1.small# some comment'}
        try:
            self.get_custom_config(**invalid_case)
        except exception.ConfigError:
            pass
        else:
            raise Exception(('config incorrectly ignores line with non-inline '
                             'comment pound sign: %s') % invalid_case)
        valid_case = {'c1_node_type': 'c1.xlarge:3, m1.small # some #comment '}
        try:
            self.get_custom_config(**valid_case)
        except exception.ConfigError:
            raise Exception(('config does not ignore inline '
                             'comment: %s') % valid_case)

########NEW FILE########
__FILENAME__ = test_live
# Copyright 2009-2014 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

import pytest

from starcluster.plugins.sge import SGEPlugin
from starcluster.balancers import sge

live = pytest.mark.live


@live
def test_hostnames(nodes):
    for node in nodes:
        assert node.ssh.execute("hostname")[0] == node.alias


@live
def test_cluster_user(cluster, nodes):
    for node in nodes:
        assert cluster.cluster_user in node.get_user_map()


@live
def test_scratch_dirs(cluster, nodes):
    for node in nodes:
        assert node.ssh.isdir("/scratch")
        assert node.ssh.isdir("/scratch/%s" % cluster.cluster_user)


@live
def test_etc_hosts(cluster, nodes):
    for node in nodes:
        with node.ssh.remote_file('/etc/hosts', 'r') as rf:
            etc_hosts = rf.read()
            for snode in nodes:
                hosts_entry = snode.get_hosts_entry()
                assert hosts_entry in etc_hosts


@live
def test_nfs(nodes):
    for node in nodes[1:]:
        mmap = node.get_mount_map()
        assert 'master:/home' in mmap
        assert 'master:/opt/sge6' in mmap


@live
def test_passwordless_ssh(nodes):
    for node in nodes:
        for snode in nodes:
            resp = node.ssh.execute("ssh %s hostname" % snode.alias)[0]
            assert resp == snode.alias


@live
def test_sge(cluster, nodes):
    master_is_exec_host = True
    for plugin in cluster.plugins:
        if isinstance(plugin, SGEPlugin):
            master_is_exec_host = plugin.master_is_exec_host
    s = sge.SGEStats()
    qhost_xml = cluster.master_node.ssh.execute("qhost -xml")
    qhosts = s.parse_qhost('\n'.join(qhost_xml))
    qhost_aliases = [h['name'] for h in qhosts]
    for node in nodes:
        if not master_is_exec_host and node.alias == 'master':
            continue
        assert node.alias in qhost_aliases

########NEW FILE########
__FILENAME__ = test_sge_balancer
# Copyright 2009-2014 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

import iso8601
import datetime

from starcluster import utils
from starcluster.balancers import sge
from starcluster.tests import StarClusterTest
from starcluster.tests.templates import sge_balancer


class TestSGELoadBalancer(StarClusterTest):

    def test_qhost_parser(self):
        stat = sge.SGEStats()
        host_hash = stat.parse_qhost(sge_balancer.qhost_xml)
        assert len(host_hash) == 3
        assert len(host_hash) == stat.count_hosts()

    def test_loaded_qhost_parser(self):
        stat = sge.SGEStats()
        host_hash = stat.parse_qhost(sge_balancer.loaded_qhost_xml)
        assert len(host_hash) == 10
        assert len(host_hash) == stat.count_hosts()

    def test_qstat_parser(self):
        stat = sge.SGEStats()
        stat_hash = stat.parse_qstat(sge_balancer.qstat_xml)
        assert len(stat_hash) == 23
        assert stat.first_job_id == 1
        assert stat.last_job_id == 23
        assert len(stat.get_queued_jobs()) == 20
        assert len(stat.get_running_jobs()) == 3
        assert stat.num_slots_for_job(21) == 1
        oldest = datetime.datetime(2010, 6, 18, 23, 39, 14,
                                   tzinfo=iso8601.iso8601.UTC)
        assert stat.oldest_queued_job_age() == oldest
        assert len(stat.queues) == 3

    def test_qacct_parser(self):
        stat = sge.SGEStats()
        now = utils.get_utc_now()
        self.jobstats = stat.parse_qacct(sge_balancer.qacct_txt, now)
        assert stat.avg_job_duration() == 90
        assert stat.avg_wait_time() == 263

    def test_loaded_qstat_parser(self):
        stat = sge.SGEStats()
        stat_hash = stat.parse_qstat(sge_balancer.loaded_qstat_xml)
        assert len(stat_hash) == 192
        assert stat.first_job_id == 385
        assert stat.last_job_id == 576
        assert len(stat.get_queued_jobs()) == 188
        assert len(stat.get_running_jobs()) == 4
        assert stat.num_slots_for_job(576) == 20
        oldest = datetime.datetime(2010, 7, 8, 4, 40, 32,
                                   tzinfo=iso8601.iso8601.UTC)
        assert stat.oldest_queued_job_age() == oldest
        assert len(stat.queues) == 10
        assert stat.count_total_slots() == 80
        stat.parse_qhost(sge_balancer.loaded_qhost_xml)
        assert stat.slots_per_host() == 8

    def test_node_working(self):
        # TODO : FINISH THIS
        pass

########NEW FILE########
__FILENAME__ = test_threadpool
# Copyright 2009-2014 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

import logging
import tempfile
logging.disable(logging.WARN)

from starcluster import tests
from starcluster import exception
from starcluster import threadpool


class TestThreadPool(tests.StarClusterTest):

    _jobs = 5
    _mykw = 'StarCluster!!!'
    _pool = None

    @property
    def pool(self):
        if not self._pool:
            self._pool = threadpool.get_thread_pool(10, disable_threads=False)
            fd = tempfile.TemporaryFile()
            self._pool.progress_bar.fd = fd
        return self._pool

    def _no_args(self):
        pass

    def _args_only(self, i):
        return i

    def _kwargs_only(self, mykw=None):
        return mykw

    def _args_and_kwargs(self, i, mykw=None):
        return (i, dict(mykw=mykw))

    def test_no_args(self):
        pool = self.pool
        try:
            for i in range(self._jobs):
                pool.simple_job(self._no_args, jobid=i)
            results = pool.wait(numtasks=self._jobs)
            print "no_args: %s" % results
            assert results.count(None) == self._jobs
        except exception.ThreadPoolException, e:
            raise Exception(e.format_excs())

    def test_args_only(self):
        try:
            pool = self.pool
            for i in range(self._jobs):
                pool.simple_job(self._args_only, i, jobid=i)
            results = pool.wait(numtasks=self._jobs)
            results.sort()
            print "args_only: %s" % results
            assert results == range(self._jobs)
        except exception.ThreadPoolException, e:
            raise Exception(e.format_excs())

    def test_kwargs_only(self):
        pool = self.pool
        try:
            for i in range(self._jobs):
                pool.simple_job(self._kwargs_only,
                                kwargs=dict(mykw=self._mykw), jobid=i)
            results = pool.wait(numtasks=self._jobs)
            print "kwargs_only: %s" % results
            assert results.count(self._mykw) == self._jobs
        except exception.ThreadPoolException, e:
            raise Exception(e.format_excs())

    def test_args_and_kwargs(self):
        pool = self.pool
        try:
            for i in range(self._jobs):
                pool.simple_job(self._args_and_kwargs, i,
                                kwargs=dict(mykw=self._mykw), jobid=i)
            results = pool.wait(numtasks=self._jobs)
            results.sort()
            print "args_and_kwargs: %s" % results
            assert results == zip(range(self._jobs),
                                  [dict(mykw=self._mykw)] * self._jobs)
        except exception.ThreadPoolException, e:
            raise Exception(e.format_excs())

    def test_map(self):
        try:
            r = 20
            ref = map(lambda x: x ** 2, range(r))
            calc = self.pool.map(lambda x: x ** 2, range(r))
            calc.sort()
            assert ref == calc
            for i in range(r):
                self.pool.simple_job(lambda x: x ** 2, i, jobid=i)
            self.pool.wait(return_results=False)
            calc = self.pool.map(lambda x: x ** 2, range(r))
            calc.sort()
            assert ref == calc
        except exception.ThreadPoolException, e:
            raise Exception(e.format_excs())

    def test_map_with_jobid(self):
        try:
            r = 20
            ref = map(lambda x: x ** 2, range(r))
            calc = self.pool.map(lambda x: x ** 2, range(r),
                                 jobid_fn=lambda x: x)
            calc.sort()
            assert ref == calc
            self.pool.map(lambda x: x ** 2, range(r) + ['21'],
                          jobid_fn=lambda x: x)
        except exception.ThreadPoolException, e:
            exc, tb_msg, jobid = e.exceptions[0]
            assert jobid == '21'

    def test_exception_queue(self):
        assert self.pool._exception_queue.qsize() == 0
        r = 10
        try:
            self.pool.map(lambda x: x ** 2, [str(i) for i in range(r)])
        except exception.ThreadPoolException, e:
            assert len(e.exceptions) == r
            assert self.pool._exception_queue.qsize() == 0

########NEW FILE########
__FILENAME__ = test_userdata_utils
# Copyright 2009-2014 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

from starcluster import utils
from starcluster import userdata

IGNORED = '#ignored\nThis file will not be executed.'
BASH_SCRIPT = '#!/bin/bash\nhostname'


def _get_sample_userdata(scripts=[IGNORED, BASH_SCRIPT], compress=True,
                         use_cloudinit=True):
    files = utils.strings_to_files(scripts, fname_prefix='sc')
    return userdata.bundle_userdata_files(files, compress=compress,
                                          use_cloudinit=use_cloudinit)


def _test_bundle_userdata(compress=False, use_cloudinit=True):
    ud = _get_sample_userdata(compress=compress, use_cloudinit=use_cloudinit)
    unbundled = userdata.unbundle_userdata(ud, decompress=compress)
    if use_cloudinit:
        cloud_cfg = unbundled.get('starcluster_cloud_config.txt')
        assert cloud_cfg.startswith('#cloud-config')
    else:
        enable_root = unbundled.get('starcluster_enable_root_login.sh')
        assert enable_root == userdata.ENABLE_ROOT_LOGIN_SCRIPT
    # ignored files should have #!/bin/false prepended automagically
    ilines = unbundled.get('sc_0').splitlines()
    assert ilines[0] == '#!/bin/false'
    # removing the auto-inserted #!/bin/false should get us back to the
    # original ignored script
    ignored_mod = '\n'.join(ilines[1:])
    assert IGNORED == ignored_mod
    # check that second file is bscript
    assert unbundled.get('sc_1') == BASH_SCRIPT


def _test_append_userdata(compress=True, use_cloudinit=True):
    ud = _get_sample_userdata(compress=compress, use_cloudinit=use_cloudinit)
    unbundled = userdata.unbundle_userdata(ud, decompress=compress)
    new_script = '#!/bin/bash\ndate'
    new_fname = 'newfile.sh'
    assert new_fname not in unbundled
    unbundled[new_fname] = new_script
    new_fobj = utils.string_to_file(new_script, new_fname)
    new_ud = userdata.append_to_userdata(ud, [new_fobj], decompress=compress)
    new_unbundled = userdata.unbundle_userdata(new_ud, decompress=compress)
    assert new_unbundled == unbundled


def _test_remove_userdata(compress=True, use_cloudinit=True):
    ud = _get_sample_userdata(compress=compress, use_cloudinit=use_cloudinit)
    unbundled = userdata.unbundle_userdata(ud, decompress=compress)
    new_ud = userdata.remove_from_userdata(ud, ['sc_0'], decompress=compress)
    new_ud = userdata.unbundle_userdata(new_ud, decompress=compress)
    assert 'sc_0' in unbundled
    del unbundled['sc_0']
    assert unbundled == new_ud


def test_cloudinit_compessed():
    _test_bundle_userdata(compress=True, use_cloudinit=True)


def test_cloudinit_no_compression():
    _test_bundle_userdata(compress=False, use_cloudinit=True)


def test_non_cloudinit():
    _test_bundle_userdata(use_cloudinit=False)


def test_cloudinit_append():
    _test_append_userdata(compress=True, use_cloudinit=True)


def test_cloudinit_append_no_compression():
    _test_append_userdata(compress=False, use_cloudinit=True)


def test_non_cloudinit_append():
    _test_append_userdata(use_cloudinit=False)


def test_cloudinit_remove():
    _test_remove_userdata(compress=True, use_cloudinit=True)


def test_cloudinit_remove_no_compression():
    _test_remove_userdata(compress=False, use_cloudinit=True)


def test_non_cloudinit_remove():
    _test_remove_userdata(use_cloudinit=False)

########NEW FILE########
__FILENAME__ = threadpool
# Copyright 2009-2014 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

"""
ThreadPool module for StarCluster based on WorkerPool
"""
import time
import Queue
import thread
import traceback
import workerpool

from starcluster import exception
from starcluster import progressbar
from starcluster.logger import log


class DaemonWorker(workerpool.workers.Worker):
    """
    Improved Worker that sets daemon = True by default and also handles
    communicating exceptions to the parent pool object by adding them to
    the parent pool's exception queue
    """
    def __init__(self, *args, **kwargs):
        super(DaemonWorker, self).__init__(*args, **kwargs)
        self.daemon = True

    def run(self):
        "Get jobs from the queue and perform them as they arrive."
        while 1:
            # Sleep until there is a job to perform.
            job = self.jobs.get()
            try:
                job.run()
            except workerpool.exceptions.TerminationNotice:
                break
            except Exception, e:
                tb_msg = traceback.format_exc()
                jid = job.jobid or str(thread.get_ident())
                self.jobs.store_exception([e, tb_msg, jid])
            finally:
                self.jobs.task_done()


def _worker_factory(parent):
    return DaemonWorker(parent)


class SimpleJob(workerpool.jobs.SimpleJob):
    def __init__(self, method, args=[], kwargs={}, jobid=None,
                 results_queue=None):
        self.method = method
        self.args = args
        self.kwargs = kwargs
        self.jobid = jobid
        self.results_queue = results_queue

    def run(self):
        if isinstance(self.args, list) or isinstance(self.args, tuple):
            if isinstance(self.kwargs, dict):
                r = self.method(*self.args, **self.kwargs)
            else:
                r = self.method(*self.args)
        elif self.args is not None and self.args is not []:
            if isinstance(self.kwargs, dict):
                r = self.method(self.args, **self.kwargs)
            else:
                r = self.method(self.args)
        else:
            r = self.method()
        if self.results_queue:
            return self.results_queue.put(r)
        return r


class ThreadPool(workerpool.WorkerPool):
    def __init__(self, size=1, maxjobs=0, worker_factory=_worker_factory,
                 disable_threads=False):
        self.disable_threads = disable_threads
        self._exception_queue = Queue.Queue()
        self._results_queue = Queue.Queue()
        self._progress_bar = None
        if self.disable_threads:
            size = 0
        workerpool.WorkerPool.__init__(self, size, maxjobs, worker_factory)

    @property
    def progress_bar(self):
        if not self._progress_bar:
            widgets = ['', progressbar.Fraction(), ' ',
                       progressbar.Bar(marker=progressbar.RotatingMarker()),
                       ' ', progressbar.Percentage(), ' ', ' ']
            pbar = progressbar.ProgressBar(widgets=widgets, maxval=1,
                                           force_update=True)
            self._progress_bar = pbar
        return self._progress_bar

    def simple_job(self, method, args=[], kwargs={}, jobid=None,
                   results_queue=None):
        results_queue = results_queue or self._results_queue
        job = SimpleJob(method, args, kwargs, jobid,
                        results_queue=results_queue)
        if not self.disable_threads:
            return self.put(job)
        else:
            return job.run()

    def get_results(self):
        results = []
        for i in range(self._results_queue.qsize()):
            results.append(self._results_queue.get())
        return results

    def map(self, fn, *seq, **kwargs):
        """
        Uses the threadpool to return a list of the results of applying the
        function to the items of the argument sequence(s). If more than one
        sequence is given, the function is called with an argument list
        consisting of the corresponding item of each sequence. If more than one
        sequence is given with different lengths the argument list will be
        truncated to the length of the smallest sequence.

        If the kwarg jobid_fn is specified then each threadpool job will be
        assigned a jobid based on the return value of jobid_fn(item) for each
        item in the map.
        """
        if self._results_queue.qsize() > 0:
            self.get_results()
        args = zip(*seq)
        jobid_fn = kwargs.get('jobid_fn')
        for seq in args:
            jobid = None
            if jobid_fn:
                jobid = jobid_fn(*seq)
            self.simple_job(fn, seq, jobid=jobid)
        return self.wait(numtasks=len(args))

    def store_exception(self, e):
        self._exception_queue.put(e)

    def shutdown(self):
        log.info("Shutting down threads...")
        workerpool.WorkerPool.shutdown(self)
        self.wait(numtasks=self.size())

    def wait(self, numtasks=None, return_results=True):
        pbar = self.progress_bar.reset()
        pbar.maxval = self.unfinished_tasks
        if numtasks is not None:
            pbar.maxval = max(numtasks, self.unfinished_tasks)
        while self.unfinished_tasks != 0:
            finished = pbar.maxval - self.unfinished_tasks
            pbar.update(finished)
            log.debug("unfinished_tasks = %d" % self.unfinished_tasks)
            time.sleep(1)
        if pbar.maxval != 0:
            pbar.finish()
        self.join()
        exc_queue = self._exception_queue
        if exc_queue.qsize() > 0:
            excs = [exc_queue.get() for i in range(exc_queue.qsize())]
            raise exception.ThreadPoolException(
                "An error occurred in ThreadPool", excs)
        if return_results:
            return self.get_results()

    def __del__(self):
        log.debug('del called in threadpool')
        self.shutdown()
        self.join()


def get_thread_pool(size=10, worker_factory=_worker_factory,
                    disable_threads=False):
    return ThreadPool(size=size, worker_factory=_worker_factory,
                      disable_threads=disable_threads)

########NEW FILE########
__FILENAME__ = userdata
# Copyright 2009-2014 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

import os
import re
import time
import gzip
import email
import base64
import tarfile
import StringIO

from email import encoders
from email.mime import base
from email.mime import text
from email.mime import multipart

from starcluster import utils
from starcluster import exception


starts_with_mappings = {
    '#include': 'text/x-include-url',
    '#!': 'text/x-shellscript',
    '#cloud-config': 'text/cloud-config',
    '#cloud-config-archive': 'text/cloud-config-archive',
    '#upstart-job': 'text/upstart-job',
    '#part-handler': 'text/part-handler',
    '#cloud-boothook': 'text/cloud-boothook',
    '#ignored': 'text/ignore'
}


def _get_type_from_fp(fp):
    line = fp.readline()
    fp.seek(0)
    # slist is sorted longest first
    slist = starts_with_mappings.keys()
    slist.sort(key=lambda e: -1 * len(e))
    for sstr in slist:
        if line.startswith(sstr):
            return starts_with_mappings[sstr]
    raise exception.BaseException("invalid user data type: %s" % line)


def mp_userdata_from_files(files, compress=False, multipart_mime=None):
    outer = multipart_mime or multipart.MIMEMultipart()
    mtypes = []
    for i, fp in enumerate(files):
        mtype = _get_type_from_fp(fp)
        mtypes.append(mtype)
        maintype, subtype = mtype.split('/', 1)
        if maintype == 'text':
            # Note: we should handle calculating the charset
            msg = text.MIMEText(fp.read(), _subtype=subtype)
            fp.close()
        else:
            if hasattr(fp, 'name'):
                fp = open(fp.name, 'rb')
            msg = base.MIMEBase(maintype, subtype)
            msg.set_payload(fp.read())
            fp.close()
            # Encode the payload using Base64
            encoders.encode_base64(msg)
        # Set the filename parameter
        fname = getattr(fp, 'name', "sc_%d" % i)
        msg.add_header('Content-Disposition', 'attachment',
                       filename=os.path.basename(fname))
        outer.attach(msg)
    userdata = outer.as_string()
    if compress:
        s = StringIO.StringIO()
        gfile = gzip.GzipFile(fileobj=s, mode='w')
        gfile.write(userdata)
        gfile.close()
        s.seek(0)
        userdata = s.read()
    return userdata


def get_mp_from_userdata(userdata, decompress=False):
    if decompress:
        zfile = StringIO.StringIO(userdata)
        gfile = gzip.GzipFile(fileobj=zfile, mode='r')
        userdata = gfile.read()
        gfile.close()
    return email.message_from_string(userdata)


SCRIPT_TEMPLATE = """\
#!/usr/bin/env python
import os, sys, stat, gzip, tarfile, StringIO
os.chdir(os.path.dirname(sys.argv[0]))
decoded = StringIO.StringIO('''%s'''.decode('base64'))
gf = gzip.GzipFile(mode='r', fileobj=decoded)
tf = tarfile.TarFile(mode='r', fileobj=gf)
for ti in tf:
    tf.extract(ti)
    is_exec = (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH) & ti.mode != 0
    if ti.isfile() and is_exec:
        os.system(os.path.abspath(ti.name))
"""


def userdata_script_from_files(fileobjs, tar_fname=None, tar_file=None):
    tar_fname = tar_fname or 'sc_userdata.tar'
    if tar_file:
        tf = tar_file
        tfd = tf.fileobj
    else:
        tfd = StringIO.StringIO()
        tf = tar_file or tarfile.TarFile(tar_fname, mode='w', fileobj=tfd)
    for f in fileobjs:
        if hasattr(f, 'fileno'):
            ti = tf.gettarinfo(fileobj=f)
        else:
            ti = tarfile.TarInfo()
        ti.name = os.path.basename(f.name)
        ti.mtime = time.time()
        if f.read(2) == '#!':
            ti.mode = 0755
        f.seek(0)
        if hasattr(f, 'buf'):
            ti.size = len(f.buf)
        tf.addfile(ti, f)
    tf.close()
    tfd.seek(0)
    gfd = StringIO.StringIO()
    gzip_fname = os.path.extsep.join([tar_fname, '.gz'])
    gf = gzip.GzipFile(gzip_fname, mode='w', fileobj=gfd)
    gf.write(tfd.read())
    gf.close()
    gfd.seek(0)
    gfs = StringIO.StringIO(gfd.read())
    b64str = base64.b64encode(gfs.read())
    script = SCRIPT_TEMPLATE % b64str
    return script


def get_tar_from_userdata(string, mode='r'):
    r = re.compile("\('''(.*)'''\.decode")
    b64str = r.search(string).groups()[0]
    gzf = StringIO.StringIO(b64str.decode('base64'))
    tarstr = StringIO.StringIO(gzip.GzipFile(fileobj=gzf, mode='r').read())
    return tarfile.TarFile(fileobj=tarstr, mode=mode)


ENABLE_ROOT_LOGIN_SCRIPT = """\
#!/usr/bin/env python
import re;
r = re.compile(',?command=".*",?')
akf = '/root/.ssh/authorized_keys'
fixed = r.subn('', open(akf).read())[0]
open(akf, 'w').write(fixed)
"""


def bundle_userdata_files(fileobjs, tar_fname=None, compress=True,
                          use_cloudinit=True):
    script_type = starts_with_mappings['#!']
    ignored_type = starts_with_mappings['#ignored']
    for i, fobj in enumerate(fileobjs):
        ftype = _get_type_from_fp(fobj)
        if ftype == ignored_type:
            fileobjs[i] = utils.string_to_file("#!/bin/false\n" + fobj.read(),
                                               fobj.name)
            continue
        elif ftype != script_type:
            use_cloudinit = True
    if use_cloudinit:
        fileobjs += [utils.string_to_file('#cloud-config\ndisable_root: 0',
                                          'starcluster_cloud_config.txt')]
        return mp_userdata_from_files(fileobjs, compress=compress)
    else:
        fileobjs += [utils.string_to_file(ENABLE_ROOT_LOGIN_SCRIPT,
                                          'starcluster_enable_root_login.sh')]
        return userdata_script_from_files(fileobjs, tar_fname=tar_fname)


def unbundle_userdata(string, decompress=True):
    udata = {}
    if string.startswith('#!'):
        tf = get_tar_from_userdata(string)
        files = tf.getmembers()
        for f in files:
            udata[f.name] = tf.extractfile(f).read()
    else:
        mpmime = get_mp_from_userdata(string, decompress=decompress)
        files = mpmime.get_payload()
        for f in files:
            udata[f.get_filename()] = f.get_payload()
    return udata


def append_to_userdata(userdata_string, fileobjs, decompress=True):
    if userdata_string.startswith('#!'):
        tf = get_tar_from_userdata(userdata_string, mode='a')
        return userdata_script_from_files(fileobjs, tar_file=tf)
    else:
        mpmime = get_mp_from_userdata(userdata_string, decompress=decompress)
        return mp_userdata_from_files(fileobjs, multipart_mime=mpmime,
                                      compress=decompress)


def remove_from_userdata(userdata_string, filenames, decompress=True):
    if userdata_string.startswith('#!'):
        orig_tf = get_tar_from_userdata(userdata_string)
        tarstr = StringIO.StringIO()
        new_tf = tarfile.TarFile(fileobj=tarstr, mode='w')
        for f in orig_tf.getmembers():
            if f.name in filenames:
                continue
            contents = StringIO.StringIO(orig_tf.extractfile(f).read())
            new_tf.addfile(f, contents)
        new_tf.close()
        tarstr.seek(0)
        new_tf = tarfile.TarFile(fileobj=tarstr, mode='r')
        return userdata_script_from_files([], tar_file=new_tf)
    else:
        mpmime = get_mp_from_userdata(userdata_string, decompress=decompress)
        msgs = []
        for msg in mpmime.get_payload():
            if msg.get_filename() in filenames:
                continue
            msgs.append(msg)
        mpmime.set_payload(msgs)
        return mp_userdata_from_files([], multipart_mime=mpmime,
                                      compress=decompress)


if __name__ == '__main__':
    files = utils.strings_to_files(['#!/bin/bash\nhostname',
                                    '#!/bin/bash\ndate'],
                                   fname_prefix='sc_userdata_file')
    files += utils.string_to_file('#ignored\nblahblahblah', 'sc_metadata')
    script = bundle_userdata_files(files, use_cloudinit=False)
    f = open('/tmp/tester.sh', 'w')
    f.write(script)
    f.close()
    os.chmod('/tmp/tester.sh', 0750)

########NEW FILE########
__FILENAME__ = utils
# Copyright 2009-2014 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

"""
Utils module for StarCluster
"""

import os
import re
import sys
import zlib
import time
import json
import types
import string
import random
import inspect
import cPickle
import StringIO
import calendar
import urlparse
from datetime import datetime

import iptools
import iso8601
import decorator

from starcluster import spinner
from starcluster import exception
from starcluster.logger import log


def ipy_shell(local_ns=None):
    try:
        import IPython
        if IPython.__version__ < '0.11':
            from IPython.Shell import IPShellEmbed
            return IPShellEmbed(argv=[])(local_ns)
        else:
            from IPython import embed
            return embed(user_ns=local_ns)
    except ImportError as e:
        log.error("Unable to load IPython:\n\n%s\n" % e)
        log.error("Please check that IPython is installed and working.")
        log.error("If not, you can install it via: easy_install ipython")


def set_trace():
    try:
        import pudb
        return pudb.set_trace()
    except ImportError:
        log.error("Unable to load PuDB")
        log.error("Please check that PuDB is installed and working.")
        log.error("If not, you can install it via: easy_install pudb")


class AttributeDict(dict):
    """
    Subclass of dict that allows read-only attribute-like access to
    dictionary key/values
    """
    def __getattr__(self, name):
        try:
            return self.__getitem__(name)
        except KeyError:
            return super(AttributeDict, self).__getattribute__(name)


def print_timing(msg=None, debug=False):
    """
    Decorator for printing execution time (in mins) of a function
    Optionally takes a user-friendly msg as argument. This msg will
    appear in the sentence "[msg] took XXX mins". If no msg is specified,
    msg will default to the decorated function's name. e.g:

    >>> @print_timing
    ... def myfunc():
    ...     print 'Running myfunc'
    >>> myfunc()
    Running myfunc
    myfunc took 0.000 mins

    >>> @print_timing('My function')
    ... def myfunc():
    ...    print 'Running myfunc'
    >>> myfunc()
    Running myfunc
    My function took 0.000 mins
    """
    prefix = msg
    if isinstance(msg, types.FunctionType):
        prefix = msg.func_name

    def wrap_f(func, *arg, **kargs):
        """Raw timing function """
        time1 = time.time()
        res = func(*arg, **kargs)
        time2 = time.time()
        msg = '%s took %0.3f mins' % (prefix, (time2 - time1) / 60.0)
        if debug:
            log.debug(msg)
        else:
            log.info(msg)
        return res

    if isinstance(msg, types.FunctionType):
        return decorator.decorator(wrap_f, msg)
    else:
        return decorator.decorator(wrap_f)


def is_valid_device(dev):
    """
    Checks that dev matches the following regular expression:
    /dev/sd[a-z]$
    """
    regex = re.compile('/dev/sd[a-z]$')
    try:
        return regex.match(dev) is not None
    except TypeError:
        return False


def is_valid_partition(part):
    """
    Checks that part matches the following regular expression:
    /dev/sd[a-z][1-9][0-9]?$
    """
    regex = re.compile('/dev/sd[a-z][1-9][0-9]?$')
    try:
        return regex.match(part) is not None
    except TypeError:
        return False


def is_valid_bucket_name(bucket_name):
    """
    Check if bucket_name is a valid S3 bucket name (as defined by the AWS
    docs):

    1. 3 <= len(bucket_name) <= 255
    2. all chars one of: a-z 0-9 .  _ -
    3. first char one of: a-z 0-9
    4. name must not be a valid ip
    """
    regex = re.compile('[a-z0-9][a-z0-9\._-]{2,254}$')
    if not regex.match(bucket_name):
        return False
    if iptools.ipv4.validate_ip(bucket_name):
        return False
    return True


def is_valid_image_name(image_name):
    """
    Check if image_name is a valid AWS image name (as defined by the AWS docs)

    1. 3<= len(image_name) <=128
    2. all chars one of: a-z A-Z 0-9 ( ) . - / _
    """
    regex = re.compile('[\w\(\)\.\-\/_]{3,128}$')
    try:
        return regex.match(image_name) is not None
    except TypeError:
        return False


def is_valid_hostname(hostname):
    """From StackOverflow on 2013-10-04:

    http://stackoverflow.com
    /questions/2532053/validate-a-hostname-string#answer-2532344
    """
    if len(hostname) > 255:
        return False
    if hostname[-1] == ".":
        hostname = hostname[:-1]  # strip exactly one dot from the right
    allowed = re.compile("(?!-)[A-Z\d-]{1,63}(?<!-)$", re.IGNORECASE)
    return all(allowed.match(x) for x in hostname.split("."))


def make_one_liner(script):
    """
    Returns command to execute python script as a one-line python program

    e.g.

        import os
        script = '''
        import os
        print os.path.exists('hi')
        '''
        os.system(make_one_liner(script))

    Will print out:

        <module 'os' from ...>
        False
    """
    return 'python -c "%s"' % script.strip().replace('\n', ';')


def is_url(url):
    """
    Returns True if the provided string is a valid url
    """
    try:
        parts = urlparse.urlparse(url)
        scheme = parts[0]
        netloc = parts[1]
        if scheme and netloc:
            return True
        else:
            return False
    except:
        return False


def is_iso_time(iso):
    """
    Returns True if provided time can be parsed in iso format
    to a datetime tuple
    """
    try:
        iso_to_datetime_tuple(iso)
        return True
    except iso8601.ParseError:
        return False


def iso_to_datetime_tuple(iso):
    """
    Converts an iso time string to a datetime tuple
    """
    return iso8601.parse_date(iso)


def get_utc_now(iso=False):
    """
    Returns datetime.utcnow with UTC timezone info
    """
    now = datetime.utcnow().replace(tzinfo=iso8601.iso8601.UTC)
    if iso:
        return datetime_tuple_to_iso(now)
    else:
        return now


def datetime_tuple_to_iso(tup):
    """
    Converts a datetime tuple to a UTC iso time string
    """
    iso = datetime.strftime(tup.astimezone(iso8601.iso8601.UTC),
                            "%Y-%m-%dT%H:%M:%S.%fZ")
    return iso


def get_elapsed_time(past_time):
    ptime = iso_to_localtime_tuple(past_time)
    now = datetime.now()
    delta = now - ptime
    timestr = time.strftime("%H:%M:%S", time.gmtime(delta.seconds))
    if delta.days != -1:
        timestr = "%d days, %s" % (delta.days, timestr)
    return timestr


def iso_to_unix_time(iso):
    dtup = iso_to_datetime_tuple(iso)
    secs = calendar.timegm(dtup.timetuple())
    return secs


def iso_to_javascript_timestamp(iso):
    """
    Convert dates to Javascript timestamps (number of milliseconds since
    January 1st 1970 UTC)
    """
    secs = iso_to_unix_time(iso)
    return secs * 1000


def iso_to_localtime_tuple(iso):
    secs = iso_to_unix_time(iso)
    t = time.mktime(time.localtime(secs))
    return datetime.fromtimestamp(t)


def permute(a):
    """
    Returns generator of all permutations of a

    The following code is an in-place permutation of a given list, implemented
    as a generator. Since it only returns references to the list, the list
    should not be modified outside the generator. The solution is
    non-recursive, so uses low memory. Work well also with multiple copies of
    elements in the input list.

    Retrieved from:
        http://stackoverflow.com/questions/104420/ \
        how-to-generate-all-permutations-of-a-list-in-python
    """
    a.sort()
    yield list(a)
    if len(a) <= 1:
        return
    first = 0
    last = len(a)
    while 1:
        i = last - 1
        while 1:
            i = i - 1
            if a[i] < a[i + 1]:
                j = last - 1
                while not (a[i] < a[j]):
                    j = j - 1
                # swap the values
                a[i], a[j] = a[j], a[i]
                r = a[i + 1:last]
                r.reverse()
                a[i + 1:last] = r
                yield list(a)
                break
            if i == first:
                a.reverse()
                return


def has_required(programs):
    """
    Same as check_required but returns False if not all commands exist
    """
    try:
        return check_required(programs)
    except exception.CommandNotFound:
        return False


def check_required(programs):
    """
    Checks that all commands in the programs list exist. Returns
    True if all commands exist and raises exception.CommandNotFound if not.
    """
    for prog in programs:
        if not which(prog):
            raise exception.CommandNotFound(prog)
    return True


def which(program):
    """
    Returns the path to the program provided it exists and
    is on the system's PATH

    retrieved from code snippet by Jay:

    http://stackoverflow.com/questions/377017/ \
    test-if-executable-exists-in-python
    """
    def is_exe(fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)
    fpath, fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file


def tailf(filename):
    """
    Constantly displays the last lines in filename
    Similar to 'tail -f' unix command
    """
    # Set the filename and open the file
    file = open(filename, 'r')

    # Find the size of the file and move to the end
    st_results = os.stat(filename)
    st_size = st_results[6]
    file.seek(st_size)

    while True:
        where = file.tell()
        line = file.readline()
        if not line:
            time.sleep(1)
            file.seek(where)
            continue
        print line,  # already has newline


def v2fhelper(v, suff, version, weight):
    parts = v.split(suff)
    if 2 != len(parts):
        return v
    version[4] = weight
    version[5] = parts[1]
    return parts[0]


def version_to_float(v):
    # This code was written by Krzysztof Kowalczyk (http://blog.kowalczyk.info)
    # and is placed in public domain.
    """
    Convert a Mozilla-style version string into a floating-point number
    1.2.3.4, 1.2a5, 2.3.4b1pre, 3.0rc2, etc.
    """
    version = [
        0, 0, 0, 0,  # 4-part numerical revision
        4,  # Alpha, beta, RC or (default) final
        0,  # Alpha, beta, or RC version revision
        1   # Pre or (default) final
    ]
    parts = v.split("pre")
    if 2 == len(parts):
        version[6] = 0
        v = parts[0]

    v = v2fhelper(v, "a",  version, 1)
    v = v2fhelper(v, "b",  version, 2)
    v = v2fhelper(v, "rc", version, 3)

    parts = v.split(".")[:4]
    for (p, i) in zip(parts, range(len(parts))):
        version[i] = p
    ver = float(version[0])
    ver += float(version[1]) / 100.
    ver += float(version[2]) / 10000.
    ver += float(version[3]) / 1000000.
    ver += float(version[4]) / 100000000.
    ver += float(version[5]) / 10000000000.
    ver += float(version[6]) / 1000000000000.
    return ver


def program_version_greater(ver1, ver2):
    """
    Return True if ver1 > ver2 using semantics of comparing version
    numbers
    """
    v1f = version_to_float(ver1)
    v2f = version_to_float(ver2)
    return v1f > v2f


def test_version_to_float():
    assert program_version_greater("1", "0.9")
    assert program_version_greater("0.0.0.2", "0.0.0.1")
    assert program_version_greater("1.0", "0.9")
    assert program_version_greater("2.0.1", "2.0.0")
    assert program_version_greater("2.0.1", "2.0")
    assert program_version_greater("2.0.1", "2")
    assert program_version_greater("0.9.1", "0.9.0")
    assert program_version_greater("0.9.2", "0.9.1")
    assert program_version_greater("0.9.11", "0.9.2")
    assert program_version_greater("0.9.12", "0.9.11")
    assert program_version_greater("0.10", "0.9")
    assert program_version_greater("2.0", "2.0b35")
    assert program_version_greater("1.10.3", "1.10.3b3")
    assert program_version_greater("88", "88a12")
    assert program_version_greater("0.0.33", "0.0.33rc23")
    assert program_version_greater("0.91.2", "0.91.1")
    assert program_version_greater("0.9999", "0.91.1")
    assert program_version_greater("0.9999", "0.92")
    assert program_version_greater("0.91.10", "0.91.1")
    assert program_version_greater("0.92", "0.91.11")
    assert program_version_greater("0.92", "0.92b1")
    assert program_version_greater("0.9999", "0.92b3")
    print("All tests passed")


def get_arg_spec(func, debug=True):
    """
    Convenience wrapper around inspect.getargspec

    Returns a tuple whose first element is a list containing the names of all
    required arguments and whose second element is a list containing the names
    of all keyword (optional) arguments.
    """
    allargs, varargs, keywords, defaults = inspect.getargspec(func)
    if 'self' in allargs:
        allargs.remove('self')  # ignore self
    nargs = len(allargs)
    ndefaults = 0
    if defaults:
        ndefaults = len(defaults)
    nrequired = nargs - ndefaults
    args = allargs[:nrequired]
    kwargs = allargs[nrequired:]
    if debug:
        log.debug('nargs = %s' % nargs)
        log.debug('ndefaults = %s' % ndefaults)
        log.debug('nrequired = %s' % nrequired)
        log.debug('args = %s' % args)
        log.debug('kwargs = %s' % kwargs)
        log.debug('defaults = %s' % str(defaults))
    return args, kwargs


def chunk_list(ls, items=8):
    """
    iterate through 'chunks' of a list. final chunk consists of remaining
    elements if items does not divide len(ls) evenly.

    items - size of 'chunks'
    """
    itms = []
    for i, v in enumerate(ls):
        if i >= items and i % items == 0:
            yield itms
            itms = [v]
        else:
            itms.append(v)
    if itms:
        yield itms


def generate_passwd(length):
    return "".join(random.sample(string.letters + string.digits, length))


class struct_group(tuple):
    """
    grp.struct_group: Results from getgr*() routines.

    This object may be accessed either as a tuple of
      (gr_name,gr_passwd,gr_gid,gr_mem)
    or via the object attributes as named in the above tuple.
    """

    attrs = ['gr_name', 'gr_passwd', 'gr_gid', 'gr_mem']

    def __new__(cls, grp):
        if type(grp) not in (list, str, tuple):
            grp = (grp.name, grp.password, int(grp.GID),
                   [member for member in grp.members])
        if len(grp) != 4:
            raise TypeError('expecting a 4-sequence (%d-sequence given)' %
                            len(grp))
        return tuple.__new__(cls, grp)

    def __getattr__(self, attr):
        try:
            return self[self.attrs.index(attr)]
        except ValueError:
            raise AttributeError


class struct_passwd(tuple):
    """
    pwd.struct_passwd: Results from getpw*() routines.

    This object may be accessed either as a tuple of
      (pw_name,pw_passwd,pw_uid,pw_gid,pw_gecos,pw_dir,pw_shell)
    or via the object attributes as named in the above tuple.
    """

    attrs = ['pw_name', 'pw_passwd', 'pw_uid', 'pw_gid', 'pw_gecos',
             'pw_dir', 'pw_shell']

    def __new__(cls, pwd):
        if type(pwd) not in (list, str, tuple):
            pwd = (pwd.loginName, pwd.password, int(pwd.UID), int(pwd.GID),
                   pwd.GECOS, pwd.home, pwd.shell)
        if len(pwd) != 7:
            raise TypeError('expecting a 4-sequence (%d-sequence given)' %
                            len(pwd))
        return tuple.__new__(cls, pwd)

    def __getattr__(self, attr):
        try:
            return self[self.attrs.index(attr)]
        except ValueError:
            raise AttributeError


def dump_compress_encode(obj, use_json=False, chunk_size=None):
    serializer = cPickle
    if use_json:
        serializer = json
    p = zlib.compress(serializer.dumps(obj)).encode('base64')
    if chunk_size is not None:
        return [p[i:i + chunk_size] for i in range(0, len(p), chunk_size)]
    return p


def decode_uncompress_load(string, use_json=False):
    string = ''.join(string)
    serializer = cPickle
    if use_json:
        serializer = json
    return serializer.loads(zlib.decompress(string.decode('base64')))


def string_to_file(string, filename):
    s = StringIO.StringIO(string)
    s.name = filename
    return s


def strings_to_files(strings, fname_prefix=''):
    fileobjs = [StringIO.StringIO(s) for s in strings]
    if fname_prefix:
        fname_prefix += '_'
    for i, f in enumerate(fileobjs):
        f.name = '%s%d' % (fname_prefix, i)
    return fileobjs


def get_fq_class_name(obj):
    return '.'.join([obj.__module__, obj.__class__.__name__])


def size_in_kb(obj):
    return sys.getsizeof(obj) / 1024.


def get_spinner(msg):
    """
    Logs a status msg, starts a spinner, and returns the spinner object.
    This is useful for long running processes:

    s = get_spinner("Long running process running...")
    try:
        (do something)
    finally:
        s.stop()
    """
    s = spinner.Spinner()
    log.info(msg, extra=dict(__nonewline__=True))
    s.start()
    return s

########NEW FILE########
__FILENAME__ = validators
# Copyright 2009-2014 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.


class Validator(object):
    """
    Base class for all validating classes
    """
    def validate(self):
        """
        Raises an exception if any validation tests fail
        """
        pass

    def is_valid(self):
        """
        Returns False if any validation tests fail, otherwise returns True
        """
        pass

########NEW FILE########
__FILENAME__ = volume
# Copyright 2009-2014 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

import time
import string

from starcluster import utils
from starcluster import static
from starcluster import exception
from starcluster import cluster
from starcluster.utils import print_timing
from starcluster.logger import log


class VolumeCreator(cluster.Cluster):
    """
    Handles creating, partitioning, and formatting a new EBS volume.
    By default this class will format the entire drive (without partitioning)
    using the ext3 filesystem.

    host_instance - EC2 instance to use when formatting volume. must exist in
    the same zone as the new volume. if not specified this class will look for
    host instances in the @sc-volumecreator security group.  If it can't find
    an instance in the @sc-volumecreator group that matches the zone of the
    new volume, a new instance is launched.

    shutdown_instance - True will shutdown the host instance after volume
    creation
    """
    def __init__(self, ec2_conn, spot_bid=None, keypair=None,
                 key_location=None, host_instance=None, device='/dev/sdz',
                 image_id=static.BASE_AMI_32, instance_type="t1.micro",
                 shutdown_instance=False, detach_vol=False,
                 mkfs_cmd='mkfs.ext3 -F', resizefs_cmd='resize2fs', **kwargs):
        self._host_instance = host_instance
        self._instance = None
        self._volume = None
        self._aws_block_device = device or '/dev/sdz'
        self._real_device = None
        self._image_id = image_id or static.BASE_AMI_32
        self._instance_type = instance_type or 'm1.small'
        self._shutdown = shutdown_instance
        self._detach_vol = detach_vol
        self._mkfs_cmd = mkfs_cmd
        self._resizefs_cmd = resizefs_cmd
        self._alias_tmpl = "volhost-%s"
        super(VolumeCreator, self).__init__(
            ec2_conn=ec2_conn, spot_bid=spot_bid, keyname=keypair,
            key_location=key_location, cluster_tag=static.VOLUME_GROUP_NAME,
            cluster_size=1, cluster_user="sgeadmin", cluster_shell="bash",
            node_image_id=self._image_id, subnet_id=kwargs.get('subnet_id'),
            node_instance_type=self._instance_type, force_spot_master=True)

    def __repr__(self):
        return "<VolumeCreator: %s>" % self._mkfs_cmd

    def _get_existing_instance(self, zone):
        """
        Returns any existing instance in the @sc-volumecreator group that's
        located in zone.
        """
        active_states = ['pending', 'running']
        i = self._host_instance
        if i and self._validate_host_instance(i, zone):
            log.info("Using specified host instance %s" % i.id)
            return i
        for node in self.nodes:
            if node.state in active_states and node.placement == zone:
                log.info("Using existing instance %s in group %s" %
                         (node.id, self.cluster_group.name))
                return node

    def _request_instance(self, zone):
        self._instance = self._get_existing_instance(zone)
        if not self._instance:
            alias = self._alias_tmpl % zone
            self._validate_image_and_type(self._image_id, self._instance_type)
            log.info(
                "No instance in group %s for zone %s, launching one now." %
                (self.cluster_group.name, zone))
            self._resv = self.create_node(alias, image_id=self._image_id,
                                          instance_type=self._instance_type,
                                          zone=zone)
            self.wait_for_cluster(msg="Waiting for volume host to come up...")
            self._instance = self.get_node(alias)
        else:
            s = utils.get_spinner("Waiting for instance %s to come up..." %
                                  self._instance.id)
            while not self._instance.is_up():
                time.sleep(self.refresh_interval)
            s.stop()
        return self._instance

    def _create_volume(self, size, zone, snapshot_id=None):
        vol = self.ec2.create_volume(size, zone, snapshot_id)
        self._volume = vol
        log.info("New volume id: %s" % vol.id)
        self.ec2.wait_for_volume(vol, status='available')
        return vol

    def _create_snapshot(self, volume):
        snap = self.ec2.create_snapshot(volume, wait_for_snapshot=True)
        log.info("New snapshot id: %s" % snap.id)
        self._snapshot = snap
        return snap

    def _determine_device(self):
        block_dev_map = self._instance.block_device_mapping
        for char in string.lowercase[::-1]:
            dev = '/dev/sd%s' % char
            if not block_dev_map.get(dev):
                self._aws_block_device = dev
                return self._aws_block_device

    def _get_volume_device(self, device=None):
        dev = device or self._aws_block_device
        inst = self._instance
        if inst.ssh.path_exists(dev):
            self._real_device = dev
            return dev
        xvdev = '/dev/xvd' + dev[-1]
        if inst.ssh.path_exists(xvdev):
            self._real_device = xvdev
            return xvdev
        raise exception.BaseException("Can't find volume device")

    def _attach_volume(self, vol, instance_id, device):
        log.info("Attaching volume %s to instance %s..." %
                 (vol.id, instance_id))
        vol.attach(instance_id, device)
        self.ec2.wait_for_volume(vol, state='attached')
        return self._volume

    def _validate_host_instance(self, instance, zone):
        if instance.state not in ['pending', 'running']:
            raise exception.InstanceNotRunning(instance.id)
        if instance.placement != zone:
            raise exception.ValidationError(
                "specified host instance %s is not in zone %s" %
                (instance.id, zone))
        return True

    def _validate_image_and_type(self, image, itype):
        img = self.ec2.get_image_or_none(image)
        if not img:
            raise exception.ValidationError(
                'image %s does not exist' % image)
        if itype not in static.INSTANCE_TYPES:
            choices = ', '.join(static.INSTANCE_TYPES)
            raise exception.ValidationError(
                'instance_type must be one of: %s' % choices)
        itype_platform = static.INSTANCE_TYPES.get(itype)
        img_platform = img.architecture
        if img_platform not in itype_platform:
            error_msg = "instance_type %(itype)s is for an "
            error_msg += "%(iplat)s platform while image_id "
            error_msg += "%(img)s is an %(imgplat)s platform"
            error_msg %= {'itype': itype, 'iplat': ', '.join(itype_platform),
                          'img': img.id, 'imgplat': img_platform}
            raise exception.ValidationError(error_msg)

    def _validate_zone(self, zone):
        z = self.ec2.get_zone(zone)
        if z.state != 'available':
            log.warn('zone %s is not available at this time' % zone)
        return True

    def _validate_size(self, size):
        try:
            volume_size = int(size)
            if volume_size < 1:
                raise exception.ValidationError(
                    "volume_size must be an integer >= 1")
        except ValueError:
            raise exception.ValidationError("volume_size must be an integer")

    def _validate_device(self, device):
        if not utils.is_valid_device(device):
            raise exception.ValidationError("volume device %s is not valid" %
                                            device)

    def _validate_required_progs(self, progs):
        log.info("Checking for required remote commands...")
        self._instance.ssh.check_required(progs)

    def validate(self, size, zone, device):
        self._validate_size(size)
        self._validate_zone(zone)
        self._validate_device(device)

    def is_valid(self, size, zone, device):
        try:
            self.validate(size, zone, device)
            return True
        except exception.BaseException, e:
            log.error(e.msg)
            return False

    def _repartition_volume(self):
        conn = self._instance.ssh
        partmap = self._instance.get_partition_map()
        part = self._real_device + '1'
        start = partmap.get(part)[0]
        conn.execute('echo "%s,,L" | sfdisk -f -uS %s' %
                     (start, self._real_device), silent=False)
        conn.execute('e2fsck -p -f %s' % part, silent=False)

    def _format_volume(self):
        log.info("Formatting volume...")
        self._instance.ssh.execute('%s %s' %
                                   (self._mkfs_cmd, self._real_device),
                                   silent=False)

    def _warn_about_volume_hosts(self):
        sg = self.ec2.get_group_or_none(static.VOLUME_GROUP)
        vol_hosts = []
        if sg:
            vol_hosts = filter(lambda x: x.state in ['running', 'pending'],
                               sg.instances())
        if self._instance:
            vol_hosts.append(self._instance)
        vol_hosts = list(set([h.id for h in vol_hosts]))
        if vol_hosts:
            log.warn("There are still volume hosts running: %s" %
                     ', '.join(vol_hosts))
            if not self._instance:
                log.warn("Run 'starcluster terminate -f %s' to terminate all "
                         "volume host instances" % static.VOLUME_GROUP_NAME,
                         extra=dict(__textwrap__=True))
        elif sg:
            log.info("No active volume hosts found. Run 'starcluster "
                     "terminate -f %(g)s' to remove the '%(g)s' group" %
                     {'g': static.VOLUME_GROUP_NAME},
                     extra=dict(__textwrap__=True))

    def shutdown(self):
        vol = self._volume
        host = self._instance
        if self._detach_vol:
            log.info("Detaching volume %s from instance %s" %
                     (vol.id, host.id))
            vol.detach()
        else:
            log.info("Leaving volume %s attached to instance %s" %
                     (vol.id, host.id))
        if self._shutdown:
            log.info("Terminating host instance %s" % host.id)
            host.terminate()
        else:
            log.info("Not terminating host instance %s" %
                     host.id)

    def _delete_new_volume(self):
        """
        Should only be used during clean-up in the case of an error
        """
        newvol = self._volume
        if newvol:
            log.error("Detaching and deleting *new* volume: %s" % newvol.id)
            if newvol.update() != 'available':
                newvol.detach(force=True)
                self.ec2.wait_for_volume(newvol, status='available')
            newvol.delete()
            self._volume = None

    @print_timing("Creating volume")
    def create(self, volume_size, volume_zone, name=None, tags=None):
        try:
            self.validate(volume_size, volume_zone, self._aws_block_device)
            instance = self._request_instance(volume_zone)
            self._validate_required_progs([self._mkfs_cmd.split()[0]])
            self._determine_device()
            vol = self._create_volume(volume_size, volume_zone)
            if tags:
                for tag in tags:
                    tagval = tags.get(tag)
                    tagmsg = "Adding volume tag: %s" % tag
                    if tagval:
                        tagmsg += "=%s" % tagval
                    log.info(tagmsg)
                    vol.add_tag(tag, tagval)
            if name:
                vol.add_tag("Name", name)
            self._attach_volume(self._volume, instance.id,
                                self._aws_block_device)
            self._get_volume_device(self._aws_block_device)
            self._format_volume()
            self.shutdown()
            log.info("Your new %sGB volume %s has been created successfully" %
                     (volume_size, vol.id))
            return vol
        except Exception:
            log.error("Failed to create new volume", exc_info=True)
            self._delete_new_volume()
            raise
        finally:
            self._warn_about_volume_hosts()

    def _validate_resize(self, vol, size):
        self._validate_size(size)
        if vol.size > size:
            log.warn("You are attempting to shrink an EBS volume. "
                     "Data loss may occur")

    @print_timing("Resizing volume")
    def resize(self, vol, size, dest_zone=None):
        """
        Resize EBS volume

        vol - boto volume object
        size - new volume size
        dest_zone - zone to create the new resized volume in. this must be
        within the original volume's region otherwise a manual copy (rsync)
        is required. this is currently not implemented.
        """
        try:
            self._validate_device(self._aws_block_device)
            self._validate_resize(vol, size)
            zone = vol.zone
            if dest_zone:
                self._validate_zone(dest_zone)
                zone = dest_zone
            host = self._request_instance(zone)
            resizefs_exe = self._resizefs_cmd.split()[0]
            required = [resizefs_exe]
            if resizefs_exe == 'resize2fs':
                required.append('e2fsck')
            self._validate_required_progs(required)
            self._determine_device()
            snap = self._create_snapshot(vol)
            new_vol = self._create_volume(size, zone, snap.id)
            self._attach_volume(new_vol, host.id, self._aws_block_device)
            device = self._get_volume_device()
            devs = filter(lambda x: x.startswith(device), host.ssh.ls('/dev'))
            if len(devs) == 1:
                log.info("No partitions found, resizing entire device")
            elif len(devs) == 2:
                log.info("One partition found, resizing partition...")
                self._repartition_volume()
                device += '1'
            else:
                raise exception.InvalidOperation(
                    "EBS volume %s has more than 1 partition. "
                    "You must resize this volume manually" % vol.id)
            if resizefs_exe == "resize2fs":
                log.info("Running e2fsck on new volume")
                host.ssh.execute("e2fsck -y -f %s" % device)
            log.info("Running %s on new volume" % self._resizefs_cmd)
            host.ssh.execute(' '.join([self._resizefs_cmd, device]))
            self.shutdown()
            return new_vol.id
        except Exception:
            log.error("Failed to resize volume %s" % vol.id)
            self._delete_new_volume()
            raise
        finally:
            snap = self._snapshot
            if snap:
                log_func = log.info if self._volume else log.error
                log_func("Deleting snapshot %s" % snap.id)
                snap.delete()
            self._warn_about_volume_hosts()

########NEW FILE########
__FILENAME__ = webtools
# Copyright 2009-2014 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

import os
import sys
import shlex
import optparse
import mimetypes
import posixpath
import webbrowser
import subprocess
import BaseHTTPServer as httpserv

from starcluster import templates
from starcluster import exception
from starcluster.logger import log

ERROR_MSG = """\
<head>
<title>DOH!</title>
</head>
<body>
<pre>
 _  _    ___  _  _
| || |  / _ \| || |
| || |_| | | | || |_
|__   _| |_| |__   _|
   |_|  \___/   |_|

</pre>
<h1>Error response</h1>
<p>Error code %(code)d.
<p>Message: %(message)s.
<p>Error code explanation: %(code)s = %(explain)s.
</body>
"""


class StoppableHttpServer(httpserv.HTTPServer):
    """http server that reacts to self.stop flag"""

    def serve_forever(self):
        """Handle one request at a time until stopped."""
        self.stop = False
        while not self.stop:
            self.handle_request()


class BaseHandler(httpserv.BaseHTTPRequestHandler):
    error_message_format = ERROR_MSG

    def do_GET(self):
        print 'GET not supported'

    def do_POST(self):
        print 'POSTing not supported'

    def do_shutdown(self):
        log.info("Shutting down server...")
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.server.stop = True


class DocrootHandler(BaseHandler):

    def do_GET(self):
        try:
            docroot = globals()['DOCUMENTROOT']
            fname = posixpath.join(docroot, self.path[1:])
            # remove query args. query args are ignored in static server
            fname = fname.split('?')[0]
            if fname.endswith('/') or os.path.isdir(fname):
                fname = posixpath.join(fname, 'index.html')
            f = open(fname)  # self.path has /test.html
            content_type = mimetypes.guess_type(fname)[0]
            self.send_response(200)
            self.send_header('Content-type', content_type)
            self.end_headers()
            while True:
                data = f.read(2097152)
                if not data:
                    break
                self.wfile.write(data)
            # self.wfile.write(f.read())
            f.close()
            return
        except IOError:
            self.send_error(404, 'File Not Found: %s' % self.path)


class TemplateHandler(DocrootHandler):
    """
    Simple GET handler that loads and renders files/templates within a package
    under the starcluster.templates package. You can set the _root_template_pkg
    attribute on this class before passing to BaseHTTPServer to specify a
    starcluster.templates subpackage to render templates from. Defaults to
    rendering starcluster.templates (i.e. '/')
    """
    _root_template_pkg = '/'
    _tmpl_context = {}
    _bin_exts = ('.ico', '.gif', '.jpg', '.png')

    def do_GET(self):
        relpath = self.path[1:].split('?')[0]
        if relpath == "shutdown":
            self.do_shutdown()
            return
        fullpath = posixpath.join(self._root_template_pkg, relpath)
        try:
            if relpath.endswith(self._bin_exts):
                data = templates.get_resource(fullpath).read()
            else:
                tmpl = templates.get_web_template(fullpath)
                data = tmpl.render(**self._tmpl_context)
            content_type = mimetypes.guess_type(os.path.basename(relpath))[0]
            self.send_response(200)
            self.send_header('Content-type', content_type)
            self.end_headers()
            self.wfile.write(data)
        except IOError, templates.TemplateNotFound:
            self.send_error(404, 'File Not Found: %s' % self.path)
            return


def get_template_server(root_template_pkg='/', interface="localhost",
                        port=None, context={}):
    TemplateHandler._root_template_pkg = root_template_pkg
    TemplateHandler._tmpl_context = context
    server = get_webserver(interface=interface, port=port,
                           handler=TemplateHandler)
    return server


def get_webserver(interface="localhost", port=None, handler=DocrootHandler):
    if port is None:
        port = 0
    server = StoppableHttpServer((interface, port), handler)
    return server


class BackgroundBrowser(webbrowser.GenericBrowser):
    """Class for all browsers which are to be started in the background."""
    def open(self, url, new=0, autoraise=1):
        cmdline = [self.name] + [arg.replace("%s", url)
                                 for arg in self.args]
        try:
            if sys.platform[:3] == 'win':
                p = subprocess.Popen(cmdline, stdout=subprocess.PIPE)
            else:
                setsid = getattr(os, 'setsid', None)
                if not setsid:
                    setsid = getattr(os, 'setpgrp', None)
                p = subprocess.Popen(cmdline, close_fds=True,
                                     preexec_fn=setsid, stdout=subprocess.PIPE)
            return (p.poll() is None)
        except OSError:
            return False


def _is_exe(fpath):
    return os.path.exists(fpath) and os.access(fpath, os.X_OK)


def _which(program):
    fpath, fname = os.path.split(program)
    if fpath:
        if _is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            exe_file = os.path.join(path, program)
            if _is_exe(exe_file):
                return exe_file


def open_browser(url, browser_cmd=None):
    if browser_cmd:
        cmd = shlex.split(browser_cmd)
        arg0 = cmd[0]
        if not _which(arg0):
            raise exception.BaseException("browser %s does not exist" % arg0)
        if "%s" not in browser_cmd:
            cmd.append("%s")
        browser = BackgroundBrowser(cmd)
    else:
        # use 'default' browser from webbrowser module
        browser = webbrowser.get()
    browser_name = getattr(browser, 'name', None)
    if not browser_name:
        browser_name = getattr(browser, '_name', 'UNKNOWN')
    log.info("Browsing %s using '%s'..." % (url, browser_name))
    return browser.open(url)


def main(path, interface="localhost", port=8080):
    try:
        docroot = os.path.realpath(path)
        globals()['DOCUMENTROOT'] = docroot
        server = get_webserver(interface=interface, port=port,
                               handler=DocrootHandler)
        log.info('Starting httpserver...')
        log.info('Document_root = %s' % docroot)
        server.serve_forever()
    except KeyboardInterrupt:
        print '^C received, shutting down server'
        server.socket.close()


if __name__ == '__main__':
    parser = optparse.OptionParser()
    parser.add_option("-i", "--interface", dest="interface", action="store",
                      default="localhost")
    parser.add_option("-p", "--port", dest="port", action="store", type="int",
                      default=8080)
    opts, args = parser.parse_args()
    if len(args) != 1:
        parser.error('usage:  webserver.py <document_root>')
    path = args[0]
    main(path, **opts.__dict__)

########NEW FILE########
__FILENAME__ = gitlog2changelog
#!/usr/bin/python
# Copyright 2008 Marcus D. Hanwell <marcus@cryos.org>
# Distributed under the terms of the GNU General Public License v2 or later

import string, re, os

# Execute git log with the desired command line options.
fin = os.popen('git log --summary --stat --no-merges --date=short', 'r')
# Create a ChangeLog file in the current directory.
fout = open('ChangeLog', 'w')

# Set up the loop variables in order to locate the blocks we want
authorFound = False
dateFound = False
messageFound = False
filesFound = False
message = ""
messageNL = False
files = ""
prevAuthorLine = ""

# The main part of the loop
for line in fin:
    # The commit line marks the start of a new commit object.
    if string.find(line, 'commit') >= 0:
        # Start all over again...
        authorFound = False
        dateFound = False
        messageFound = False
        messageNL = False
        message = ""
        filesFound = False
        files = ""
        continue
    # Match the author line and extract the part we want
    elif re.match('Author:', line) >=0:
        authorList = re.split(': ', line, 1)
        author = authorList[1]
        author = author[0:len(author)-1]
        authorFound = True
    # Match the date line
    elif re.match('Date:', line) >= 0:
        dateList = re.split(':   ', line, 1)
        date = dateList[1]
        date = date[0:len(date)-1]
        dateFound = True
    # The svn-id lines are ignored
    elif re.match('    git-svn-id:', line) >= 0:
        continue
    # The sign off line is ignored too
    elif re.search('Signed-off-by', line) >= 0:
        continue
    # Extract the actual commit message for this commit
    elif authorFound & dateFound & messageFound == False:
        # Find the commit message if we can
        if len(line) == 1:
            if messageNL:
                messageFound = True
            else:
                messageNL = True
        elif len(line) == 4:
            messageFound = True
        else:
            if len(message) == 0:
                message = message + line.strip()
            else:
                message = message + " " + line.strip()
    # If this line is hit all of the files have been stored for this commit
    elif re.search('files changed', line) >= 0:
        filesFound = True
        continue
    # Collect the files for this commit. FIXME: Still need to add +/- to files
    elif authorFound & dateFound & messageFound:
        fileList = re.split(' \| ', line, 2)
        if len(fileList) > 1:
            if len(files) > 0:
                files = files + ", " + fileList[0].strip()
            else:
                files = fileList[0].strip()
    # All of the parts of the commit have been found - write out the entry
    if authorFound & dateFound & messageFound & filesFound:
        # First the author line, only outputted if it is the first for that
        # author on this day
        authorLine = date + "  " + author
        if len(prevAuthorLine) == 0:
            fout.write(authorLine + "\n")
        elif authorLine == prevAuthorLine:
            pass
        else:
            fout.write("\n" + authorLine + "\n")

        # Assemble the actual commit message line(s) and limit the line length
        # to 80 characters.
        commitLine = "* " + files + ": " + message
        i = 0
        commit = ""
        while i < len(commitLine):
            if len(commitLine) < i + 78:
                commit = commit + "\n  " + commitLine[i:len(commitLine)]
                break
            index = commitLine.rfind(' ', i, i+78)
            if index > i:
                commit = commit + "\n  " + commitLine[i:index]
                i = index+1
            else:
                commit = commit + "\n  " + commitLine[i:78]
                i = i+79

        # Write out the commit line
        fout.write(commit + "\n")

        #Now reset all the variables ready for a new commit block.
        authorFound = False
        dateFound = False
        messageFound = False
        messageNL = False
        message = ""
        filesFound = False
        files = ""
        prevAuthorLine = authorLine

# Close the input and output lines now that we are finished.
fin.close()
fout.close()

########NEW FILE########
__FILENAME__ = missingcloud
import sys
import time
import json
import urllib2
import traceback

from BeautifulSoup import BeautifulSoup as bs

from starcluster import config


class MissingCloud(object):

    ITYPES_HTML_URL = "http://aws.amazon.com/ec2/instance-types/"
    LINUX_OD_JSON = " http://aws.amazon.com/ec2/pricing/json/linux-od.json"
    DEFAULT_REGION = "us-east-1"
    HVM_AMI = "ami-52a0c53b"
    NON_HVM_AMI = "ami-765b3e1f"
    SPOT_BID = "0.80"

    def __init__(self):
        self._ec2 = None
        self._itypes_html = None
        self._linux_od_json = None
        self._itypes = None
        self._region_types_map = None
        self._hvm_types = None
        self._hvm_only_types = None
        self._placement_group_regions = None
        self._placement_group_types = None

    def fetch(self):
        print self.INSTANCE_TYPES
        print self.REGION_TYPES_MAP
        print self.PLACEMENT_GROUP_TYPES
        print self.PLACEMENT_GROUP_REGIONS
        print self.HVM_ONLY_TYPES
        print self.HVM_TYPES

    def dump(self):
        pass

    @property
    def ec2(self):
        if not self._ec2:
            cfg = config.StarClusterConfig().load()
            self._ec2 = cfg.get_easy_ec2()
        return self._ec2

    @property
    def html(self):
        if not self._itypes_html:
            f = urllib2.urlopen(self.ITYPES_HTML_URL)
            self._itypes_html = bs(f.read())
            f.close()
        return self._itypes_html

    @property
    def json(self):
        if not self._linux_od_json:
            f = urllib2.urlopen(self.LINUX_OD_JSON)
            self._linux_od_json = json.loads(f.read())
            f.close()
        return self._linux_od_json

    @property
    def REGION_TYPES_MAP(self):
        if not self._region_types_map:
            self._region_types_map = self._get_regions_to_types_map()
        return self._region_types_map

    @property
    def INSTANCE_TYPES(self):
        if not self._itypes:
            self._itypes = {}
            itypes_tab = self._get_tables()[0]
            for itype in itypes_tab[1:]:
                _arch_map = {'64-bit': 'x86_64', '32-bit': 'i386'}
                arches = [_arch_map[a.strip()] for a in itype[2].split('or')]
                self._itypes[itype[1]] = arches
        return self._itypes

    @property
    def PLACEMENT_GROUP_TYPES(self):
        if not self._placement_group_types:
            itypes_tab = self._get_tables()[0]
            pgtypes = []
            for itype in itypes_tab[1:]:
                if '10 Gigabit4' in itype:
                    pgtypes.append(itype[1])
            self._placement_group_types = pgtypes
        return self._placement_group_types

    @property
    def PLACEMENT_GROUP_REGIONS(self):
        if not self._placement_group_regions:
            self._placement_group_regions = self._get_placement_group_regions()
        return self._placement_group_regions

    @property
    def HVM_TYPES(self):
        if not self._hvm_types:
            self._hvm_types = self._get_hvm_types()
        return self._hvm_types

    @property
    def HVM_ONLY_TYPES(self):
        if not self._hvm_only_types:
            self._hvm_only_types = self._get_hvm_only_types()
        return self._hvm_only_types

    def show_types_by_region(self, region_types_map):
        header = '*' * 80
        for region in region_types_map:
            print header
            print region
            print header
            counter = 0
            itypes = region_types_map[region]
            for itype in itypes:
                print itype
                counter += 1
            print 'Total = %d\n' % counter

    def _get_regions_to_types_map(self):
        regions = self.json['config']['regions']
        m = {}
        for r in regions:
            i_types = []
            m[r['region']] = i_types
            itypes = r['instanceTypes']
            for it in itypes:
                sizes = it['sizes']
                for s in sizes:
                    i_types.append(s['size'])
        return m

    def __table_to_list(self, table):
        result = []
        allrows = table.findAll('tr')
        for row in allrows:
            result.append([])
            allcols = row.findAll('td')
            for col in allcols:
                thestrings = [unicode(s) for s in col.findAll(text=True)]
                thetext = ''.join(thestrings)
                result[-1].append(thetext.strip())
        return result

    def _get_tables(self):
        tables = []
        for table in self.html.findAll('table'):
            tables.append(self.__table_to_list(table))
        return tables

    def _get_placement_group_regions(self):
        regions = self.ec2.regions
        pgregions = []
        for region in regions:
            self.ec2.connect_to_region(region)
            try:
                pg = self.ec2.create_placement_group('tester')
                time.sleep(5)
                pg.delete()
                pgregions.append(region)
            except Exception:
                print "Region %s does not support placement groups" % region
                traceback.print_exc(file=sys.stdout)
        return pgregions

    def _get_hvm_types(self):
        self.ec2.connect_to_region(self.DEFAULT_REGION)
        hvm_types = []
        for itype in self.INSTANCE_TYPES:
            try:
                r = self.ec2.request_instances(self.HVM_AMI,
                                               price=self.SPOT_BID,
                                               instance_type=itype,
                                               security_groups=['default'])
                self.ec2.wait_for_propagation(spot_requests=r)
                for s in r:
                    s.cancel()
                print "Instance type '%s' supports HVM!" % itype
                hvm_types.append(itype)
            except:
                print "Instance type '%s' does not support HVM" % itype
                traceback.print_exc(file=sys.stdout)
        return hvm_types

    def _get_hvm_only_types(self):
        self.ec2.connect_to_region(self.DEFAULT_REGION)
        hvm_only_types = []
        for itype in self.HVM_TYPES:
            try:
                r = self.ec2.request_instances(self.NON_HVM_AMI,
                                               price=self.SPOT_BID,
                                               instance_type=itype,
                                               security_groups=['default'])
                self.ec2.wait_for_propagation(spot_requests=r)
                for s in r:
                    s.cancel()
                print "Instance type '%s' supports both HVM and NON-HVM!" % itype
            except:
                print "Instance type '%s' ONLY supports HVM" % itype
                traceback.print_exc(file=sys.stdout)
                hvm_only_types.append(itype)
        return hvm_only_types


def main():
    MissingCloud().fetch()

if __name__ == '__main__':
    main()



########NEW FILE########
__FILENAME__ = s3mount
#!/usr/bin/env python
import os
import sys

from starcluster.config import StarClusterConfig

print 'Simple wrapper script for s3fs (http://s3fs.googlecode.com/)'

cfg = StarClusterConfig().load()
ec2 = cfg.get_easy_ec2()
buckets = ec2.s3.get_buckets()
counter = 0
for bucket in buckets:
    print "[%d] %s" % (counter,bucket.name)
    counter += 1

try:
    inp = int(raw_input('>>> Enter the bucket to mnt: '))
    selection = buckets[inp].name
    print 'you selected: %s' % selection
    mountpt = raw_input('>>> please enter the mnt point: ')
    print 'mounting %s at: %s' % (selection,mountpt)
except KeyboardInterrupt,e:
    print
    print 'Exiting...'
    sys.exit(1)

try:
    os.system('s3fs %s -o accessKeyId=%s -o secretAccessKey=%s %s' % (selection,
                                                                      cfg.aws.get('aws_access_key_id'),
                                                                      cfg.aws.get('aws_secret_access_key'),mountpt))
except KeyboardInterrupt,e:
    print
    print 'Attempting to umount %s' % mountpt
    os.system('sudo umount %s' % mountpt)
    print 'Exiting...'
    sys.exit(1)

########NEW FILE########
__FILENAME__ = scimage
#!/usr/bin/env python
"""
This script is meant to be run inside of a ubuntu cloud image available at
uec-images.ubuntu.com::

    $ EC2_UBUNTU_IMG_URL=http://uec-images.ubuntu.com/precise/current
    $ wget $EC2_UBUNTU_IMG_URL/precise-server-cloudimg-amd64.tar.gz

or::

    $ wget $EC2_UBUNTU_IMG_URL/precise-server-cloudimg-i386.tar.gz

After downloading a Ubuntu cloud image the next step is to extract the image::

    $ tar xvzf precise-server-cloudimg-amd64.tar.gz

Then resize it to 10GB::

    $ e2fsck -f precise-server-cloudimg-amd64.img
    $ resize2fs precise-server-cloudimg-amd64.img 10G

Next you need to mount the image::

    $ mkdir /tmp/img-mount
    $ mount precise-server-cloudimg-amd64.img /tmp/img-mount
    $ mount -t proc none /tmp/img-mount/proc
    $ mount -t sysfs none /tmp/img-mount/sys
    $ mount -o bind /dev /tmp/img-mount/dev
    $ mount -t devpts none /tmp/img-mount/dev/pts
    $ mount -o rbind /var/run/dbus /tmp/img-mount/var/run/dbus

Copy /etc/resolv.conf and /etc/mtab to the image::

    $ mkdir -p /tmp/img-mount/var/run/resolvconf
    $ cp /etc/resolv.conf /tmp/img-mount/var/run/resolvconf/resolv.conf
    $ grep -v rootfs /etc/mtab > /tmp/img-mount/etc/mtab

Next copy this script inside the image::

    $ cp /path/to/scimage.py /tmp/img-mount/root/scimage.py

Finally chroot inside the image and run this script:

    $ chroot /tmp/img-mount /bin/bash
    $ cd $HOME
    $ python scimage.py
"""

import os
import sys
import glob
import shutil
import fileinput
import subprocess
import multiprocessing

SRC_DIR = "/usr/local/src"
APT_SOURCES_FILE = "/etc/apt/sources.list"
BUILD_UTILS_PKGS = "build-essential devscripts debconf debconf-utils dpkg-dev "
BUILD_UTILS_PKGS += "cdbs patch python-setuptools python-pip python-nose"
CLOUD_CFG_FILE = '/etc/cloud/cloud.cfg'
GRID_SCHEDULER_GIT = 'git://github.com/jtriley/gridscheduler.git'
CLOUDERA_ARCHIVE_KEY = 'http://archive.cloudera.com/debian/archive.key'
CLOUDERA_APT = 'http://archive.cloudera.com/debian maverick-cdh3u5 contrib'
CONDOR_APT = 'http://www.cs.wisc.edu/condor/debian/development lenny contrib'
NUMPY_SCIPY_SITE_CFG = """\
[DEFAULT]
library_dirs = /usr/lib
include_dirs = /usr/include:/usr/include/suitesparse

[blas_opt]
libraries = ptf77blas, ptcblas, atlas

[lapack_opt]
libraries = lapack, ptf77blas, ptcblas, atlas

[amd]
amd_libs = amd

[umfpack]
umfpack_libs = umfpack

[fftw]
libraries = fftw3
"""
STARCLUSTER_MOTD = """\
#!/bin/sh
cat<<"EOF"
          _                 _           _
__/\_____| |_ __ _ _ __ ___| |_   _ ___| |_ ___ _ __
\    / __| __/ _` | '__/ __| | | | / __| __/ _ \ '__|
/_  _\__ \ || (_| | | | (__| | |_| \__ \ ||  __/ |
  \/ |___/\__\__,_|_|  \___|_|\__,_|___/\__\___|_|

StarCluster Ubuntu 12.04 AMI
Software Tools for Academics and Researchers (STAR)
Homepage: http://star.mit.edu/cluster
Documentation: http://star.mit.edu/cluster/docs/latest
Code: https://github.com/jtriley/StarCluster
Mailing list: starcluster@mit.edu

This AMI Contains:

  * Open Grid Scheduler (OGS - formerly SGE) queuing system
  * Condor workload management system
  * OpenMPI compiled with Open Grid Scheduler support
  * OpenBLAS- Highly optimized Basic Linear Algebra Routines
  * NumPy/SciPy linked against OpenBlas
  * IPython 0.13 with parallel support
  * and more! (use 'dpkg -l' to show all installed packages)

Open Grid Scheduler/Condor cheat sheet:

  * qstat/condor_q - show status of batch jobs
  * qhost/condor_status- show status of hosts, queues, and jobs
  * qsub/condor_submit - submit batch jobs (e.g. qsub -cwd ./job.sh)
  * qdel/condor_rm - delete batch jobs (e.g. qdel 7)
  * qconf - configure Open Grid Scheduler system

Current System Stats:

EOF

landscape-sysinfo | grep -iv 'graph this data'
"""
CLOUD_INIT_CFG = """\
user: ubuntu
disable_root: 0
preserve_hostname: False
# datasource_list: [ "NoCloud", "OVF", "Ec2" ]

cloud_init_modules:
 - bootcmd
 - resizefs
 - set_hostname
 - update_hostname
 - update_etc_hosts
 - rsyslog
 - ssh

cloud_config_modules:
 - mounts
 - ssh-import-id
 - locale
 - set-passwords
 - grub-dpkg
 - timezone
 - puppet
 - chef
 - mcollective
 - disable-ec2-metadata
 - runcmd

cloud_final_modules:
 - rightscale_userdata
 - scripts-per-once
 - scripts-per-boot
 - scripts-per-instance
 - scripts-user
 - keys-to-console
 - final-message

apt_sources:
 - source: deb $MIRROR $RELEASE multiverse
 - source: deb %(CLOUDERA_APT)s
 - source: deb-src %(CLOUDERA_APT)s
 - source: deb %(CONDOR_APT)s
""" % dict(CLOUDERA_APT=CLOUDERA_APT, CONDOR_APT=CONDOR_APT)
OPENBLAS_0_1ALPHA_2_PATCH = """\
diff --git a/Makefile.system b/Makefile.system
index f0487ac..84f41a7 100644
--- a/Makefile.system
+++ b/Makefile.system
@@ -27,7 +27,13 @@ HOSTCC    = $(CC)
 endif

 ifdef TARGET
-GETARCH_FLAGS += -DFORCE_$(TARGET)
+GETARCH_FLAGS := -DFORCE_$(TARGET)
+endif
+
+#TARGET_CORE will override TARGET which is used in DYNAMIC_ARCH=1.
+#
+ifdef TARGET_CORE
+GETARCH_FLAGS := -DFORCE_$(TARGET_CORE)
 endif

 ifdef INTERFACE64
"""


def run_command(cmd, ignore_failure=False, failure_callback=None,
                get_output=False):
    kwargs = {}
    if get_output:
        kwargs.update(dict(stdout=subprocess.PIPE, stderr=subprocess.PIPE))
    p = subprocess.Popen(cmd, shell=True, **kwargs)
    output = []
    if get_output:
        line = None
        while line != '':
            line = p.stdout.readline()
            if line != '':
                output.append(line)
                print line,
        for line in p.stderr.readlines():
            if line != '':
                output.append(line)
                print line,
    retval = p.wait()
    if retval != 0:
        errmsg = "command '%s' failed with status %d" % (cmd, retval)
        if failure_callback:
            ignore_failure = failure_callback(retval)
        if not ignore_failure:
            raise Exception(errmsg)
        else:
            sys.stderr.write(errmsg + '\n')
    if get_output:
        return retval, ''.join(output)
    return retval


def apt_command(cmd):
    dpkg_opts = "Dpkg::Options::='--force-confnew'"
    cmd = "apt-get -o %s -y --force-yes %s" % (dpkg_opts, cmd)
    cmd = "DEBIAN_FRONTEND='noninteractive' " + cmd
    run_command(cmd)


def apt_install(pkgs):
    apt_command('install %s' % pkgs)


def chdir(directory):
    opts = glob.glob(directory)
    isdirlist = [o for o in opts if os.path.isdir(o)]
    if len(isdirlist) > 1:
        raise Exception("more than one dir matches: %s" % directory)
    os.chdir(isdirlist[0])


def _fix_atlas_rules(rules_file='debian/rules'):
    for line in fileinput.input(rules_file, inplace=1):
        if 'ATLAS=None' not in line:
            print line,


def configure_apt_sources():
    srcfile = open(APT_SOURCES_FILE)
    contents = srcfile.readlines()
    srcfile.close()
    srclines = []
    for line in contents:
        if not line.strip() or line.startswith('#'):
            continue
        parts = line.split()
        if parts[0] == 'deb':
            parts[0] = 'deb-src'
            srclines.append(' '.join(parts).strip())
    srcfile = open(APT_SOURCES_FILE, 'w')
    srcfile.write(''.join(contents))
    srcfile.write('\n'.join(srclines) + '\n')
    srcfile.write('deb %s\n' % CLOUDERA_APT)
    srcfile.write('deb-src %s\n' % CLOUDERA_APT)
    srcfile.write('deb %s\n' % CONDOR_APT)
    srcfile.close()
    run_command('gpg --keyserver keyserver.ubuntu.com --recv-keys 0F932C9C')
    run_command('curl -s %s | sudo apt-key add -' % CLOUDERA_ARCHIVE_KEY)
    apt_install('debian-archive-keyring')


def upgrade_packages():
    apt_command('update')
    apt_command('upgrade')


def install_build_utils():
    """docstring for configure_build"""
    apt_install(BUILD_UTILS_PKGS)


def install_gridscheduler():
    chdir(SRC_DIR)
    apt_command('build-dep gridengine')
    if os.path.isfile('gridscheduler-scbuild.tar.gz'):
        run_command('tar xvzf gridscheduler-scbuild.tar.gz')
        run_command('mv gridscheduler /opt/sge6-fresh')
        return
    run_command('git clone %s' % GRID_SCHEDULER_GIT)
    sts, out = run_command('readlink -f `which java`', get_output=True)
    java_home = out.strip().split('/jre')[0]
    chdir(os.path.join(SRC_DIR, 'gridscheduler', 'source'))
    run_command('git checkout -t -b develop origin/develop')
    env = 'JAVA_HOME=%s' % java_home
    run_command('%s ./aimk -only-depend' % env)
    run_command('%s scripts/zerodepend' % env)
    run_command('%s ./aimk depend' % env)
    run_command('%s ./aimk -no-secure -no-gui-inst' % env)
    sge_root = '/opt/sge6-fresh'
    os.mkdir(sge_root)
    env += ' SGE_ROOT=%s' % sge_root
    run_command('%s scripts/distinst -all -local -noexit -y -- man' % env)


def install_condor():
    chdir(SRC_DIR)
    run_command("rm /var/lock")
    apt_install('condor=7.7.2-1')
    run_command('echo condor hold | dpkg --set-selections')
    run_command('ln -s /etc/condor/condor_config /etc/condor_config.local')
    run_command('mkdir /var/lib/condor/log')
    run_command('mkdir /var/lib/condor/run')
    run_command('chown -R condor:condor /var/lib/condor/log')
    run_command('chown -R condor:condor /var/lib/condor/run')


def install_torque():
    chdir(SRC_DIR)
    apt_install('torque-server torque-mom torque-client')


def install_pydrmaa():
    chdir(SRC_DIR)
    run_command('pip install drmaa')


def install_atlas():
    """docstring for install_atlas"""
    chdir(SRC_DIR)
    apt_command('build-dep atlas')
    if glob.glob("*atlas*.deb"):
        run_command('dpkg -i *atlas*.deb')
        return
    apt_command('source atlas')
    chdir('atlas-*')
    run_command('fakeroot debian/rules custom')
    run_command('dpkg -i ../*atlas*.deb')


def install_openblas():
    """docstring for install_openblas"""
    chdir(SRC_DIR)
    apt_command('build-dep libopenblas-dev')
    if glob.glob("*openblas*.deb"):
        run_command('dpkg -i *openblas*.deb')
    else:
        apt_command('source libopenblas-dev')
        chdir('openblas-*')
        patch = open('fix_makefile_system.patch', 'w')
        patch.write(OPENBLAS_0_1ALPHA_2_PATCH)
        patch.close()
        run_command('patch -p1 < %s' % patch.name)
        rule_file = open('Makefile.rule', 'a')
        # NO_AFFINITY=1 is required to utilize all cores on all non
        # cluster-compute/GPU instance types due to the shared virtualization
        # layer not supporting processor affinity properly. However, Cluster
        # Compute/GPU instance types use a near-bare-metal hypervisor which
        # *does* support processor affinity. From minimal testing it appears
        # that there is a ~20% increase in performance when using affinity on
        # cc1/cg1 types implying NO_AFFINITY=1 should *not* be set for cluster
        # compute/GPU AMIs.
        lines = ['DYNAMIC_ARCH=1', 'NUM_THREADS=64', 'NO_LAPACK=1',
                 'NO_AFFINITY=1']
        rule_file.write('\n'.join(lines))
        rule_file.close()
        run_command('fakeroot debian/rules custom')
        run_command('dpkg -i ../*openblas*.deb')
    run_command('echo libopenblas-base hold | dpkg --set-selections')
    run_command('echo libopenblas-dev hold | dpkg --set-selections')


def install_numpy():
    """docstring for install_numpy"""
    chdir(SRC_DIR)
    apt_command('build-dep python-numpy')
    if glob.glob('*numpy*.deb'):
        run_command('dpkg -i *numpy*.deb')
        return
    apt_command('source python-numpy')
    chdir('python-numpy*')
    sitecfg = open('site.cfg', 'w')
    sitecfg.write(NUMPY_SCIPY_SITE_CFG)
    sitecfg.close()
    _fix_atlas_rules()

    def _deb_failure_callback(retval):
        if not glob.glob('../*numpy*.deb'):
            return False
        return True
    run_command('dpkg-buildpackage -rfakeroot -b',
                failure_callback=_deb_failure_callback)
    run_command('dpkg -i ../*numpy*.deb')


def install_scipy():
    """docstring for install_scipy"""
    chdir(SRC_DIR)
    apt_command('build-dep python-scipy')
    if glob.glob('*scipy*.deb'):
        run_command('dpkg -i *scipy*.deb')
        return
    apt_command('source python-scipy')
    chdir('python-scipy*')
    sitecfg = open('site.cfg', 'w')
    sitecfg.write(NUMPY_SCIPY_SITE_CFG)
    sitecfg.close()
    _fix_atlas_rules()

    def _deb_failure_callback(retval):
        if not glob.glob('../*numpy*.deb'):
            return False
        return True
    run_command('dpkg-buildpackage -rfakeroot -b',
                failure_callback=_deb_failure_callback)
    run_command('dpkg -i ../*scipy*.deb')


def install_pandas():
    """docstring for install_pandas"""
    chdir(SRC_DIR)
    apt_command('build-dep pandas')
    run_command('pip install pandas')


def install_openmpi():
    chdir(SRC_DIR)
    apt_command('build-dep openmpi')
    apt_install('blcr-util')
    if glob.glob('*openmpi*.deb'):
        run_command('dpkg -i *openmpi*.deb')
    else:
        apt_command('source openmpi')
        chdir('openmpi*')
        for line in fileinput.input('debian/rules', inplace=1):
            print line,
            if '--enable-heterogeneous' in line:
                print '                        --with-sge \\'

        def _deb_failure_callback(retval):
            if not glob.glob('../*openmpi*.deb'):
                return False
            return True
        run_command('dch --local=\'+custom\' '
                    '"custom build on: `uname -s -r -v -m -p -i -o`"')
        run_command('dpkg-buildpackage -rfakeroot -b',
                    failure_callback=_deb_failure_callback)
        run_command('dpkg -i ../*openmpi*.deb')
    sts, out = run_command('ompi_info | grep -i grid', get_output=True)
    if 'gridengine' not in out:
        raise Exception("failed to build OpenMPI with "
                        "Open Grid Scheduler support")
    run_command('echo libopenmpi1.3 hold | dpkg --set-selections')
    run_command('echo libopenmpi-dev hold | dpkg --set-selections')
    run_command('echo libopenmpi-dbg hold | dpkg --set-selections')
    run_command('echo openmpi-bin hold | dpkg --set-selections')
    run_command('echo openmpi-checkpoint hold | dpkg --set-selections')
    run_command('echo openmpi-common hold | dpkg --set-selections')
    run_command('echo openmpi-doc hold | dpkg --set-selections')


def install_hadoop():
    chdir(SRC_DIR)
    hadoop_pkgs = ['namenode', 'datanode', 'tasktracker', 'jobtracker',
                   'secondarynamenode']
    pkgs = ['hadoop-0.20'] + ['hadoop-0.20-%s' % pkg for pkg in hadoop_pkgs]
    apt_install(' '.join(pkgs))
    run_command('easy_install dumbo')


def install_ipython():
    chdir(SRC_DIR)
    apt_install('libzmq-dev')
    run_command('pip install ipython tornado pygments pyzmq')
    mjax_install = 'from IPython.external.mathjax import install_mathjax'
    mjax_install += '; install_mathjax()'
    run_command("python -c '%s'" % mjax_install)


def configure_motd():
    for f in glob.glob('/etc/update-motd.d/*'):
        os.unlink(f)
    motd = open('/etc/update-motd.d/00-starcluster', 'w')
    motd.write(STARCLUSTER_MOTD)
    motd.close()
    os.chmod(motd.name, 0755)


def configure_cloud_init():
    """docstring for configure_cloud_init"""
    cloudcfg = open('/etc/cloud/cloud.cfg', 'w')
    cloudcfg.write(CLOUD_INIT_CFG)
    cloudcfg.close()


def configure_bash():
    completion_line_found = False
    for line in fileinput.input('/etc/bash.bashrc', inplace=1):
        if 'bash_completion' in line and line.startswith('#'):
            print line.replace('#', ''),
            completion_line_found = True
        elif completion_line_found:
            print line.replace('#', ''),
            completion_line_found = False
        else:
            print line,
    aliasfile = open('/root/.bash_aliases', 'w')
    aliasfile.write("alias ..='cd ..'\n")
    aliasfile.close()


def setup_environ():
    num_cpus = multiprocessing.cpu_count()
    os.environ['MAKEFLAGS'] = '-j%d' % (num_cpus + 1)
    os.environ['DEBIAN_FRONTEND'] = "noninteractive"
    if os.path.isfile('/sbin/initctl') and not os.path.islink('/sbin/initctl'):
        run_command('mv /sbin/initctl /sbin/initctl.bak')
        run_command('ln -s /bin/true /sbin/initctl')


def install_nfs():
    chdir(SRC_DIR)
    run_command('initctl reload-configuration')
    apt_install('nfs-kernel-server')
    run_command('ln -s /etc/init.d/nfs-kernel-server /etc/init.d/nfs')


def install_default_packages():
    # stop mysql for interactively asking for password
    preseedf = '/tmp/mysql-preseed.txt'
    mysqlpreseed = open(preseedf, 'w')
    preseeds = """\
mysql-server mysql-server/root_password select
mysql-server mysql-server/root_password seen true
mysql-server mysql-server/root_password_again select
mysql-server mysql-server/root_password_again seen true
    """
    mysqlpreseed.write(preseeds)
    mysqlpreseed.close()
    run_command('debconf-set-selections < %s' % mysqlpreseed.name)
    run_command('rm %s' % mysqlpreseed.name)
    pkgs = "python-dev git vim mercurial subversion cvs encfs "
    pkgs += "openmpi-bin libopenmpi-dev python-django "
    pkgs += "keychain screen tmux zsh ksh csh tcsh python-mpi4py "
    pkgs += "python-virtualenv python-imaging python-boto python-matplotlib "
    pkgs += "unzip rar unace build-essential gfortran ec2-api-tools "
    pkgs += "ec2-ami-tools mysql-server mysql-client apache2 liblapack-dev "
    pkgs += "libapache2-mod-wsgi sysv-rc-conf pssh emacs cython irssi htop "
    pkgs += "python-distutils-extra vim-scripts python-ctypes python-pudb "
    pkgs += "mosh python-scipy python-numpy default-jdk mpich2 xvfb"
    apt_install(pkgs)


def configure_init():
    for script in ['nfs-kernel-server', 'hadoop', 'condor', 'apache', 'mysql']:
        run_command('find /etc/rc* -iname \*%s\* -delete' % script)


def cleanup():
    run_command('rm -f /etc/resolv.conf')
    run_command('rm -rf /var/run/resolvconf')
    run_command('rm -f /etc/mtab')
    run_command('rm -rf /root/*')
    exclude = ['/root/.bashrc', '/root/.profile', '/root/.bash_aliases']
    for dot in glob.glob("/root/.*"):
        if dot not in exclude:
            run_command('rm -rf %s' % dot)
    for path in glob.glob('/usr/local/src/*'):
        if os.path.isdir(path):
            shutil.rmtree(path)
    run_command('rm -f /var/cache/apt/archives/*.deb')
    run_command('rm -f /var/cache/apt/archives/partial/*')
    for f in glob.glob('/etc/profile.d'):
        if 'byobu' in f:
            run_command('rm -f %s' % f)
    if os.path.islink('/sbin/initctl') and os.path.isfile('/sbin/initctl.bak'):
        run_command('mv -f /sbin/initctl.bak /sbin/initctl')


def main():
    """docstring for main"""
    if os.getuid() != 0:
        sys.stderr.write('you must be root to run this script\n')
        return
    setup_environ()
    configure_motd()
    configure_cloud_init()
    configure_bash()
    configure_apt_sources()
    upgrade_packages()
    install_build_utils()
    install_default_packages()
    install_gridscheduler()
    install_condor()
    #install_torque()
    install_pydrmaa()
    # Replace ATLAS with OpenBLAS
    # install_atlas()
    install_openblas()
    # Custom NumPy/SciPy install is no longer needed in 12.04
    # install_numpy()
    # install_scipy()
    install_pandas()
    install_ipython()
    install_openmpi()
    install_hadoop()
    install_nfs()
    configure_init()
    cleanup()

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = scimage_11_10
#!/usr/bin/env python
"""
This script is meant to be run inside of a ubuntu cloud image available at
uec-images.ubuntu.com::

    $ EC2_UBUNTU_IMG_URL=http://uec-images.ubuntu.com/oneiric/current
    $ wget $EC2_UBUNTU_IMG_URL/oneiric-server-cloudimg-amd64.tar.gz

or::

    $ wget $EC2_UBUNTU_IMG_URL/oneiric-server-cloudimg-i386.tar.gz

After downloading a Ubuntu cloud image the next step is to extract the image::

    $ tar xvzf oneiric-server-cloudimg-amd64.tar.gz

Then resize it to 10GB::

    $ e2fsck -f oneiric-server-cloudimg-amd64.img
    $ resize2fs oneiric-server-cloudimg-amd64.img 10G

Next you need to mount the image::

    $ mkdir /tmp/img-mount
    $ mount oneiric-server-cloudimg-amd64.img /tmp/img-mount
    $ mount -t proc none /tmp/img-mount/proc
    $ mount -o bind /dev /tmp/img-mount/dev

Copy /etc/resolv.conf and /etc/mtab to the image::

    $ cp /etc/resolv.conf /tmp/img-mount/etc/resolv.conf
    $ grep -v rootfs /etc/mtab > /tmp/img-mount/etc/mtab

Next copy this script inside the image::

    $ cp /path/to/scimage.py /tmp/img-mount/root/scimage.py

Finally chroot inside the image and run this script:

    $ chroot /tmp/img-mount /bin/bash
    $ cd $HOME
    $ python scimage.py
"""

import os
import sys
import glob
import shutil
import fileinput
import subprocess
import multiprocessing

SRC_DIR = "/usr/local/src"
APT_SOURCES_FILE = "/etc/apt/sources.list"
BUILD_UTILS_PKGS = "build-essential devscripts debconf debconf-utils "
BUILD_UTILS_PKGS += "python-setuptools python-pip python-nose"
CLOUD_CFG_FILE = '/etc/cloud/cloud.cfg'
GRID_SCHEDULER_GIT = 'git://github.com/jtriley/gridscheduler.git'
CLOUDERA_ARCHIVE_KEY = 'http://archive.cloudera.com/debian/archive.key'
CLOUDERA_APT = 'http://archive.cloudera.com/debian maverick-cdh3 contrib'
CONDOR_APT = 'http://www.cs.wisc.edu/condor/debian/development lenny contrib'
NUMPY_SCIPY_SITE_CFG = """\
[DEFAULT]
library_dirs = /usr/lib
include_dirs = /usr/include:/usr/include/suitesparse

[blas_opt]
libraries = ptf77blas, ptcblas, atlas

[lapack_opt]
libraries = lapack, ptf77blas, ptcblas, atlas

[amd]
amd_libs = amd

[umfpack]
umfpack_libs = umfpack

[fftw]
libraries = fftw3
"""
STARCLUSTER_MOTD = """\
#!/bin/sh
cat<<"EOF"
          _                 _           _
__/\_____| |_ __ _ _ __ ___| |_   _ ___| |_ ___ _ __
\    / __| __/ _` | '__/ __| | | | / __| __/ _ \ '__|
/_  _\__ \ || (_| | | | (__| | |_| \__ \ ||  __/ |
  \/ |___/\__\__,_|_|  \___|_|\__,_|___/\__\___|_|

StarCluster Ubuntu 11.10 AMI
Software Tools for Academics and Researchers (STAR)
Homepage: http://web.mit.edu/starcluster
Documentation: http://web.mit.edu/starcluster/docs/latest
Code: https://github.com/jtriley/StarCluster
Mailing list: starcluster@mit.edu

This AMI Contains:

  * Custom-Compiled Atlas, Numpy, Scipy, etc
  * Open Grid Scheduler (OGS) queuing system
  * Condor workload management system
  * OpenMPI compiled with Open Grid Scheduler support
  * IPython 0.12 with parallel support
  * and more! (use 'dpkg -l' to show all installed packages)

Open Grid Scheduler/Condor cheat sheet:

  * qstat/condor_q - show status of batch jobs
  * qhost/condor_status- show status of hosts, queues, and jobs
  * qsub/condor_submit - submit batch jobs (e.g. qsub -cwd ./jobscript.sh)
  * qdel/condor_rm - delete batch jobs (e.g. qdel 7)
  * qconf - configure Open Grid Scheduler system

Current System Stats:

EOF

landscape-sysinfo | grep -iv 'graph this data'
"""
CLOUD_INIT_CFG = """\
user: ubuntu
disable_root: 0
preserve_hostname: False
# datasource_list: [ "NoCloud", "OVF", "Ec2" ]

cloud_init_modules:
 - bootcmd
 - resizefs
 - set_hostname
 - update_hostname
 - update_etc_hosts
 - rsyslog
 - ssh

cloud_config_modules:
 - mounts
 - ssh-import-id
 - locale
 - set-passwords
 - grub-dpkg
 - timezone
 - puppet
 - chef
 - mcollective
 - disable-ec2-metadata
 - runcmd

cloud_final_modules:
 - rightscale_userdata
 - scripts-per-once
 - scripts-per-boot
 - scripts-per-instance
 - scripts-user
 - keys-to-console
 - final-message

apt_sources:
 - source: deb $MIRROR $RELEASE multiverse
 - source: deb %(CLOUDERA_APT)s
 - source: deb-src %(CLOUDERA_APT)s
 - source: deb %(CONDOR_APT)s
""" % dict(CLOUDERA_APT=CLOUDERA_APT, CONDOR_APT=CONDOR_APT)


def run_command(cmd, ignore_failure=False, failure_callback=None,
                get_output=False):
    kwargs = {}
    if get_output:
        kwargs.update(dict(stdout=subprocess.PIPE, stderr=subprocess.PIPE))
    p = subprocess.Popen(cmd, shell=True, **kwargs)
    output = []
    if get_output:
        line = None
        while line != '':
            line = p.stdout.readline()
            if line != '':
                output.append(line)
                print line,
        for line in p.stderr.readlines():
            if line != '':
                output.append(line)
                print line,
    retval = p.wait()
    if retval != 0:
        errmsg = "command '%s' failed with status %d" % (cmd, retval)
        if failure_callback:
            ignore_failure = failure_callback(retval)
        if not ignore_failure:
            raise Exception(errmsg)
        else:
            sys.stderr.write(errmsg + '\n')
    if get_output:
        return retval, ''.join(output)
    return retval


def apt_command(cmd):
    dpkg_opts = "Dpkg::Options::='--force-confnew'"
    cmd = "apt-get -o %s -y --force-yes %s" % (dpkg_opts, cmd)
    cmd = "DEBIAN_FRONTEND='noninteractive' " + cmd
    run_command(cmd)


def apt_install(pkgs):
    apt_command('install %s' % pkgs)


def chdir(directory):
    opts = glob.glob(directory)
    isdirlist = [o for o in opts if os.path.isdir(o)]
    if len(isdirlist) > 1:
        raise Exception("more than one dir matches: %s" % directory)
    os.chdir(isdirlist[0])


def _fix_atlas_rules(rules_file='debian/rules'):
    for line in fileinput.input(rules_file, inplace=1):
        if 'ATLAS=None' not in line:
            print line,


def configure_apt_sources():
    srcfile = open(APT_SOURCES_FILE)
    contents = srcfile.readlines()
    srcfile.close()
    srclines = []
    for line in contents:
        if not line.strip() or line.startswith('#'):
            continue
        parts = line.split()
        if parts[0] == 'deb':
            parts[0] = 'deb-src'
            srclines.append(' '.join(parts).strip())
    srcfile = open(APT_SOURCES_FILE, 'w')
    srcfile.write(''.join(contents))
    srcfile.write('\n'.join(srclines) + '\n')
    srcfile.write('deb %s\n' % CLOUDERA_APT)
    srcfile.write('deb-src %s\n' % CLOUDERA_APT)
    srcfile.write('deb %s\n' % CONDOR_APT)
    srcfile.close()
    run_command('gpg --keyserver keyserver.ubuntu.com --recv-keys 0F932C9C')
    run_command('curl -s %s | sudo apt-key add -' % CLOUDERA_ARCHIVE_KEY)
    apt_install('debian-archive-keyring')


def upgrade_packages():
    apt_command('update')
    apt_command('upgrade')


def install_build_utils():
    """docstring for configure_build"""
    apt_install(BUILD_UTILS_PKGS)


def install_gridscheduler():
    chdir(SRC_DIR)
    apt_command('build-dep gridengine')
    if os.path.isfile('gridscheduler-scbuild.tar.gz'):
        run_command('tar xvzf gridscheduler-scbuild.tar.gz')
        run_command('mv gridscheduler /opt/sge6-fresh')
        return
    apt_install('git')
    run_command('git clone %s' % GRID_SCHEDULER_GIT)
    sts, out = run_command('readlink -f `which java`', get_output=True)
    java_home = out.strip().split('/jre')[0]
    chdir(os.path.join(SRC_DIR, 'gridscheduler', 'source'))
    run_command('git checkout -t -b develop origin/develop')
    env = 'JAVA_HOME=%s' % java_home
    run_command('%s ./aimk -only-depend' % env)
    run_command('%s scripts/zerodepend' % env)
    run_command('%s ./aimk depend' % env)
    run_command('%s ./aimk -no-secure -no-gui-inst' % env)
    sge_root = '/opt/sge6-fresh'
    os.mkdir(sge_root)
    env += ' SGE_ROOT=%s' % sge_root
    run_command('%s scripts/distinst -all -local -noexit -y -- man' % env)


def install_condor():
    chdir(SRC_DIR)
    run_command("rm /var/lock")
    apt_install('condor')
    run_command('ln -s /etc/condor/condor_config /etc/condor_config.local')
    run_command('mkdir /var/lib/condor/log')
    run_command('mkdir /var/lib/condor/run')
    run_command('chown -R condor:condor /var/lib/condor/log')
    run_command('chown -R condor:condor /var/lib/condor/run')


def install_torque():
    chdir(SRC_DIR)
    apt_install('torque-server torque-mom torque-client')


def install_pydrmaa():
    chdir(SRC_DIR)
    run_command('pip install drmaa')


def install_atlas():
    """docstring for install_atlas"""
    chdir(SRC_DIR)
    apt_command('build-dep atlas')
    if glob.glob("*atlas*.deb"):
        run_command('dpkg -i *atlas*.deb')
        return
    apt_command('source atlas')
    chdir('atlas-*')
    run_command('fakeroot debian/rules custom')
    run_command('dpkg -i ../*atlas*.deb')


def install_numpy():
    """docstring for install_numpy"""
    chdir(SRC_DIR)
    apt_command('build-dep python-numpy')
    if glob.glob('*numpy*.deb'):
        run_command('dpkg -i *numpy*.deb')
        return
    apt_command('source python-numpy')
    chdir('python-numpy*')
    sitecfg = open('site.cfg', 'w')
    sitecfg.write(NUMPY_SCIPY_SITE_CFG)
    sitecfg.close()
    _fix_atlas_rules()

    def _deb_failure_callback(retval):
        if not glob.glob('../*numpy*.deb'):
            return False
        return True
    run_command('dpkg-buildpackage -rfakeroot -b',
                failure_callback=_deb_failure_callback)
    run_command('dpkg -i ../*numpy*.deb')


def install_scipy():
    """docstring for install_scipy"""
    chdir(SRC_DIR)
    apt_command('build-dep python-scipy')
    if glob.glob('*scipy*.deb'):
        run_command('dpkg -i *scipy*.deb')
        return
    apt_command('source python-scipy')
    chdir('python-scipy*')
    sitecfg = open('site.cfg', 'w')
    sitecfg.write(NUMPY_SCIPY_SITE_CFG)
    sitecfg.close()
    _fix_atlas_rules()

    def _deb_failure_callback(retval):
        if not glob.glob('../*numpy*.deb'):
            return False
        return True
    run_command('dpkg-buildpackage -rfakeroot -b',
                failure_callback=_deb_failure_callback)
    run_command('dpkg -i ../*scipy*.deb')


def install_openmpi():
    chdir(SRC_DIR)
    apt_command('build-dep libopenmpi-dev')
    apt_install('blcr-util')
    if glob.glob('*openmpi*.deb'):
        run_command('dpkg -i *openmpi*.deb')
        return
    apt_command('source libopenmpi-dev')
    chdir('openmpi*')
    for line in fileinput.input('debian/rules', inplace=1):
        print line,
        if '--enable-heterogeneous' in line:
            print '                        --with-sge \\'

    def _deb_failure_callback(retval):
        if not glob.glob('../*openmpi*.deb'):
            return False
        return True
    run_command('dpkg-buildpackage -rfakeroot -b',
                failure_callback=_deb_failure_callback)
    run_command('dpkg -i ../*openmpi*.deb')
    sts, out = run_command('ompi_info | grep -i grid', get_output=True)
    if 'gridengine' not in out:
        raise Exception("failed to build openmpi with Grid Engine support")


def install_hadoop():
    chdir(SRC_DIR)
    hadoop_pkgs = ['namenode', 'datanode', 'tasktracker', 'jobtracker',
                   'secondarynamenode']
    pkgs = ['hadoop-0.20'] + ['hadoop-0.20-%s' % pkg for pkg in hadoop_pkgs]
    apt_install(' '.join(pkgs))
    run_command('easy_install dumbo')


def install_ipython():
    chdir(SRC_DIR)
    apt_install('libzmq-dev')
    run_command('pip install pyzmq==2.1.9')
    run_command('pip install ipython tornado pygments')
    mjax_install = 'from IPython.external.mathjax import install_mathjax'
    mjax_install += '; install_mathjax()'
    run_command("python -c '%s'" % mjax_install)


def configure_motd():
    for f in glob.glob('/etc/update-motd.d/*'):
        os.unlink(f)
    motd = open('/etc/update-motd.d/00-starcluster', 'w')
    motd.write(STARCLUSTER_MOTD)
    motd.close()
    os.chmod(motd.name, 0755)


def configure_cloud_init():
    """docstring for configure_cloud_init"""
    cloudcfg = open('/etc/cloud/cloud.cfg', 'w')
    cloudcfg.write(CLOUD_INIT_CFG)
    cloudcfg.close()


def configure_bash():
    completion_line_found = False
    for line in fileinput.input('/etc/bash.bashrc', inplace=1):
        if 'bash_completion' in line and line.startswith('#'):
            print line.replace('#', ''),
            completion_line_found = True
        elif completion_line_found:
            print line.replace('#', ''),
            completion_line_found = False
        else:
            print line,
    aliasfile = open('/root/.bash_aliases', 'w')
    aliasfile.write("alias ..='cd ..'\n")
    aliasfile.close()


def setup_environ():
    num_cpus = multiprocessing.cpu_count()
    os.environ['MAKEFLAGS'] = '-j%d' % (num_cpus + 1)
    os.environ['DEBIAN_FRONTEND'] = "noninteractive"


def install_nfs():
    chdir(SRC_DIR)
    run_command('initctl reload-configuration')
    apt_install('nfs-kernel-server')
    run_command('ln -s /etc/init.d/nfs-kernel-server /etc/init.d/nfs')


def install_default_packages():
    # stop mysql for interactively asking for password
    preseedf = '/tmp/mysql-preseed.txt'
    mysqlpreseed = open(preseedf, 'w')
    preseeds = """\
mysql-server mysql-server/root_password select
mysql-server mysql-server/root_password seen true
mysql-server mysql-server/root_password_again select
mysql-server mysql-server/root_password_again seen true
    """
    mysqlpreseed.write(preseeds)
    mysqlpreseed.close()
    run_command('debconf-set-selections < %s' % mysqlpreseed.name)
    run_command('rm %s' % mysqlpreseed.name)
    pkgs = "python-dev git vim mercurial subversion cvs encfs "
    pkgs += "openmpi-bin libopenmpi-dev python-django "
    pkgs += "keychain screen tmux zsh ksh csh tcsh python-mpi4py "
    pkgs += "python-virtualenv python-imaging python-boto python-matplotlib "
    pkgs += "unzip rar unace build-essential gfortran ec2-api-tools "
    pkgs += "ec2-ami-tools mysql-server mysql-client apache2 "
    pkgs += "libapache2-mod-wsgi sysv-rc-conf pssh emacs cython irssi "
    pkgs += "python-distutils-extra htop vim-scripts python-ctypes python-pudb"
    apt_install(pkgs)


def configure_init():
    for script in ['nfs-kernel-server', 'hadoop', 'condor', 'apache', 'mysql']:
        run_command('find /etc/rc* -iname \*%s\* -delete' % script)


def cleanup():
    run_command('rm /etc/resolv.conf')
    run_command('rm /etc/mtab')
    run_command('rm -rf /root/*')
    exclude = ['/root/.bashrc', '/root/.profile', '/root/.bash_aliases']
    for dot in glob.glob("/root/.*"):
        if dot not in exclude:
            run_command('rm -rf %s' % dot)
    for path in glob.glob('/usr/local/src/*'):
        if os.path.isdir(path):
            shutil.rmtree(path)
    run_command('rm -f /var/cache/apt/archives/*.deb')
    run_command('rm -f /var/cache/apt/archives/partial/*')
    for f in glob.glob('/etc/profile.d'):
        if 'byobu' in f:
            run_command('rm %s' % f)


def main():
    """docstring for main"""
    if os.getuid() != 0:
        sys.stderr.write('you must be root to run this script\n')
        return
    setup_environ()
    configure_motd()
    configure_cloud_init()
    configure_bash()
    configure_apt_sources()
    upgrade_packages()
    install_build_utils()
    install_gridscheduler()
    install_condor()
    #install_torque()
    install_pydrmaa()
    install_atlas()
    install_numpy()
    install_scipy()
    install_ipython()
    install_openmpi()
    install_hadoop()
    install_nfs()
    install_default_packages()
    configure_init()
    cleanup()

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = scimage_12_04
#!/usr/bin/env python
"""
This script is meant to be run inside of a ubuntu cloud image available at
uec-images.ubuntu.com::

    $ EC2_UBUNTU_IMG_URL=http://uec-images.ubuntu.com/precise/current
    $ wget $EC2_UBUNTU_IMG_URL/precise-server-cloudimg-amd64.tar.gz

or::

    $ wget $EC2_UBUNTU_IMG_URL/precise-server-cloudimg-i386.tar.gz

After downloading a Ubuntu cloud image the next step is to extract the image::

    $ tar xvzf precise-server-cloudimg-amd64.tar.gz

Then resize it to 10GB::

    $ e2fsck -f precise-server-cloudimg-amd64.img
    $ resize2fs precise-server-cloudimg-amd64.img 10G

Next you need to mount the image::

    $ mkdir /tmp/img-mount
    $ mount precise-server-cloudimg-amd64.img /tmp/img-mount
    $ mount -t proc none /tmp/img-mount/proc
    $ mount -t sysfs none /tmp/img-mount/sys
    $ mount -o bind /dev /tmp/img-mount/dev
    $ mount -t devpts none /tmp/img-mount/dev/pts
    $ mount -o rbind /var/run/dbus /tmp/img-mount/var/run/dbus

Copy /etc/resolv.conf and /etc/mtab to the image::

    $ mkdir -p /tmp/img-mount/var/run/resolvconf
    $ cp /etc/resolv.conf /tmp/img-mount/var/run/resolvconf/resolv.conf
    $ grep -v rootfs /etc/mtab > /tmp/img-mount/etc/mtab

Next copy this script inside the image::

    $ cp /path/to/scimage.py /tmp/img-mount/root/scimage.py

Finally chroot inside the image and run this script:

    $ chroot /tmp/img-mount /bin/bash
    $ cd $HOME
    $ python scimage.py
"""

import os
import sys
import glob
import shutil
import fileinput
import subprocess
import multiprocessing

SRC_DIR = "/usr/local/src"
APT_SOURCES_FILE = "/etc/apt/sources.list"
BUILD_UTILS_PKGS = "build-essential devscripts debconf debconf-utils dpkg-dev "
BUILD_UTILS_PKGS += "gfortran llvm-3.2-dev swig cdbs patch python-dev "
BUILD_UTILS_PKGS += "python-distutils-extra python-setuptools python-pip "
BUILD_UTILS_PKGS += "python-nose"
CLOUD_CFG_FILE = '/etc/cloud/cloud.cfg'
GRID_SCHEDULER_GIT = 'git://github.com/jtriley/gridscheduler.git'
CLOUDERA_ARCHIVE_KEY = 'http://archive.cloudera.com/debian/archive.key'
CLOUDERA_APT = 'http://archive.cloudera.com/debian maverick-cdh3u5 contrib'
CONDOR_APT = 'http://www.cs.wisc.edu/condor/debian/development lenny contrib'
NUMPY_SCIPY_SITE_CFG = """\
[DEFAULT]
library_dirs = /usr/lib
include_dirs = /usr/include:/usr/include/suitesparse

[blas_opt]
libraries = ptf77blas, ptcblas, atlas

[lapack_opt]
libraries = lapack, ptf77blas, ptcblas, atlas

[amd]
amd_libs = amd

[umfpack]
umfpack_libs = umfpack

[fftw]
libraries = fftw3
"""
STARCLUSTER_MOTD = """\
#!/bin/sh
cat<<"EOF"
          _                 _           _
__/\_____| |_ __ _ _ __ ___| |_   _ ___| |_ ___ _ __
\    / __| __/ _` | '__/ __| | | | / __| __/ _ \ '__|
/_  _\__ \ || (_| | | | (__| | |_| \__ \ ||  __/ |
  \/ |___/\__\__,_|_|  \___|_|\__,_|___/\__\___|_|

StarCluster Ubuntu 12.04 AMI
Software Tools for Academics and Researchers (STAR)
Homepage: http://star.mit.edu/cluster
Documentation: http://star.mit.edu/cluster/docs/latest
Code: https://github.com/jtriley/StarCluster
Mailing list: starcluster@mit.edu

This AMI Contains:

  * Open Grid Scheduler (OGS - formerly SGE) queuing system
  * Condor workload management system
  * OpenMPI compiled with Open Grid Scheduler support
  * OpenBLAS - Highly optimized Basic Linear Algebra Routines
  * NumPy/SciPy linked against OpenBlas
  * IPython 0.13 with parallel and notebook support
  * and more! (use 'dpkg -l' to show all installed packages)

Open Grid Scheduler/Condor cheat sheet:

  * qstat/condor_q - show status of batch jobs
  * qhost/condor_status- show status of hosts, queues, and jobs
  * qsub/condor_submit - submit batch jobs (e.g. qsub -cwd ./job.sh)
  * qdel/condor_rm - delete batch jobs (e.g. qdel 7)
  * qconf - configure Open Grid Scheduler system

Current System Stats:

EOF

landscape-sysinfo | grep -iv 'graph this data'
"""
CLOUD_INIT_CFG = """\
user: ubuntu
disable_root: 0
preserve_hostname: False
# datasource_list: [ "NoCloud", "OVF", "Ec2" ]

cloud_init_modules:
 - bootcmd
 - resizefs
 - set_hostname
 - update_hostname
 - update_etc_hosts
 - rsyslog
 - ssh

cloud_config_modules:
 - mounts
 - ssh-import-id
 - locale
 - set-passwords
 - grub-dpkg
 - timezone
 - puppet
 - chef
 - mcollective
 - disable-ec2-metadata
 - runcmd

cloud_final_modules:
 - rightscale_userdata
 - scripts-per-once
 - scripts-per-boot
 - scripts-per-instance
 - scripts-user
 - keys-to-console
 - final-message

apt_sources:
 - source: deb $MIRROR $RELEASE multiverse
 - source: deb %(CLOUDERA_APT)s
 - source: deb-src %(CLOUDERA_APT)s
 - source: deb %(CONDOR_APT)s
""" % dict(CLOUDERA_APT=CLOUDERA_APT, CONDOR_APT=CONDOR_APT)


def run_command(cmd, ignore_failure=False, failure_callback=None,
                get_output=False):
    kwargs = {}
    if get_output:
        kwargs.update(dict(stdout=subprocess.PIPE, stderr=subprocess.PIPE))
    p = subprocess.Popen(cmd, shell=True, **kwargs)
    output = []
    if get_output:
        line = None
        while line != '':
            line = p.stdout.readline()
            if line != '':
                output.append(line)
                print line,
        for line in p.stderr.readlines():
            if line != '':
                output.append(line)
                print line,
    retval = p.wait()
    if retval != 0:
        errmsg = "command '%s' failed with status %d" % (cmd, retval)
        if failure_callback:
            ignore_failure = failure_callback(retval)
        if not ignore_failure:
            raise Exception(errmsg)
        else:
            sys.stderr.write(errmsg + '\n')
    if get_output:
        return retval, ''.join(output)
    return retval


def apt_command(cmd):
    dpkg_opts = "Dpkg::Options::='--force-confnew'"
    cmd = "apt-get -o %s -y --force-yes %s" % (dpkg_opts, cmd)
    cmd = "DEBIAN_FRONTEND='noninteractive' " + cmd
    run_command(cmd)


def apt_install(pkgs):
    apt_command('install %s' % pkgs)


def chdir(directory):
    opts = glob.glob(directory)
    isdirlist = [o for o in opts if os.path.isdir(o)]
    if len(isdirlist) > 1:
        raise Exception("more than one dir matches: %s" % directory)
    os.chdir(isdirlist[0])


def _fix_atlas_rules(rules_file='debian/rules'):
    for line in fileinput.input(rules_file, inplace=1):
        if 'ATLAS=None' not in line:
            print line,


def configure_apt_sources():
    srcfile = open(APT_SOURCES_FILE)
    contents = srcfile.readlines()
    srcfile.close()
    srclines = []
    for line in contents:
        if not line.strip() or line.startswith('#'):
            continue
        parts = line.split()
        if parts[0] == 'deb':
            parts[0] = 'deb-src'
            srclines.append(' '.join(parts).strip())
    srcfile = open(APT_SOURCES_FILE, 'w')
    srcfile.write(''.join(contents))
    srcfile.write('\n'.join(srclines) + '\n')
    srcfile.write('deb %s\n' % CLOUDERA_APT)
    srcfile.write('deb-src %s\n' % CLOUDERA_APT)
    srcfile.write('deb %s\n' % CONDOR_APT)
    srcfile.close()
    run_command('add-apt-repository ppa:staticfloat/julia-deps -y')
    run_command('gpg --keyserver keyserver.ubuntu.com --recv-keys 0F932C9C')
    run_command('curl -s %s | sudo apt-key add -' % CLOUDERA_ARCHIVE_KEY)
    apt_install('debian-archive-keyring')


def upgrade_packages():
    apt_command('update')
    apt_command('upgrade')


def install_build_utils():
    """docstring for configure_build"""
    apt_install(BUILD_UTILS_PKGS)


def install_gridscheduler():
    chdir(SRC_DIR)
    apt_command('build-dep gridengine')
    if os.path.isfile('gridscheduler-scbuild.tar.gz'):
        run_command('tar xvzf gridscheduler-scbuild.tar.gz')
        run_command('mv gridscheduler /opt/sge6-fresh')
        return
    run_command('git clone %s' % GRID_SCHEDULER_GIT)
    sts, out = run_command('readlink -f `which java`', get_output=True)
    java_home = out.strip().split('/jre')[0]
    chdir(os.path.join(SRC_DIR, 'gridscheduler', 'source'))
    run_command('git checkout -t -b develop origin/develop')
    env = 'JAVA_HOME=%s' % java_home
    run_command('%s ./aimk -only-depend' % env)
    run_command('%s scripts/zerodepend' % env)
    run_command('%s ./aimk depend' % env)
    run_command('%s ./aimk -no-secure -no-gui-inst' % env)
    sge_root = '/opt/sge6-fresh'
    os.mkdir(sge_root)
    env += ' SGE_ROOT=%s' % sge_root
    run_command('%s scripts/distinst -all -local -noexit -y -- man' % env)


def install_condor():
    chdir(SRC_DIR)
    run_command("rm /var/lock")
    apt_install('condor=7.7.2-1')
    run_command('echo condor hold | dpkg --set-selections')
    run_command('ln -s /etc/condor/condor_config /etc/condor_config.local')
    run_command('mkdir /var/lib/condor/log')
    run_command('mkdir /var/lib/condor/run')
    run_command('chown -R condor:condor /var/lib/condor/log')
    run_command('chown -R condor:condor /var/lib/condor/run')


def install_torque():
    chdir(SRC_DIR)
    apt_install('torque-server torque-mom torque-client')


def install_pydrmaa():
    chdir(SRC_DIR)
    run_command('pip install drmaa')


def install_blas_lapack():
    """docstring for install_openblas"""
    chdir(SRC_DIR)
    apt_install("libopenblas-dev")


def install_numpy_scipy():
    """docstring for install_numpy"""
    chdir(SRC_DIR)
    run_command('pip install -d . numpy')
    run_command('unzip numpy*.zip')
    run_command("sed -i 's/return None #/pass #/' numpy*/numpy/core/setup.py")
    run_command('pip install scipy')


def install_pandas():
    """docstring for install_pandas"""
    chdir(SRC_DIR)
    apt_command('build-dep pandas')
    run_command('pip install pandas')


def install_matplotlib():
    chdir(SRC_DIR)
    run_command('pip install matplotlib')


def install_julia():
    apt_install("libsuitesparse-dev libncurses5-dev "
                "libopenblas-dev libarpack2-dev libfftw3-dev libgmp-dev "
                "libunwind7-dev libreadline-dev zlib1g-dev")
    buildopts = """\
BUILDOPTS="LLVM_CONFIG=llvm-config-3.2 USE_QUIET=0 USE_LIB64=0"; for lib in \
LLVM ZLIB SUITESPARSE ARPACK BLAS FFTW LAPACK GMP LIBUNWIND READLINE GLPK \
NGINX; do export BUILDOPTS="$BUILDOPTS USE_SYSTEM_$lib=1"; done"""
    chdir(SRC_DIR)
    if not os.path.exists("julia"):
        run_command("git clone git://github.com/JuliaLang/julia.git")
    run_command("%s && cd julia && make $BUILDOPTS PREFIX=/usr install" %
                buildopts)


def install_mpi():
    chdir(SRC_DIR)
    apt_install('mpich2')
    apt_command('build-dep openmpi')
    apt_install('blcr-util')
    if glob.glob('*openmpi*.deb'):
        run_command('dpkg -i *openmpi*.deb')
    else:
        apt_command('source openmpi')
        chdir('openmpi*')
        for line in fileinput.input('debian/rules', inplace=1):
            print line,
            if '--enable-heterogeneous' in line:
                print '                        --with-sge \\'

        def _deb_failure_callback(retval):
            if not glob.glob('../*openmpi*.deb'):
                return False
            return True
        run_command('dch --local=\'+custom\' '
                    '"custom build on: `uname -s -r -v -m -p -i -o`"')
        run_command('dpkg-buildpackage -rfakeroot -b',
                    failure_callback=_deb_failure_callback)
        run_command('dpkg -i ../*openmpi*.deb')
    sts, out = run_command('ompi_info | grep -i grid', get_output=True)
    if 'gridengine' not in out:
        raise Exception("failed to build OpenMPI with "
                        "Open Grid Scheduler support")
    run_command('echo libopenmpi1.3 hold | dpkg --set-selections')
    run_command('echo libopenmpi-dev hold | dpkg --set-selections')
    run_command('echo libopenmpi-dbg hold | dpkg --set-selections')
    run_command('echo openmpi-bin hold | dpkg --set-selections')
    run_command('echo openmpi-checkpoint hold | dpkg --set-selections')
    run_command('echo openmpi-common hold | dpkg --set-selections')
    run_command('echo openmpi-doc hold | dpkg --set-selections')
    run_command('pip install mpi4py')


def install_hadoop():
    chdir(SRC_DIR)
    hadoop_pkgs = ['namenode', 'datanode', 'tasktracker', 'jobtracker',
                   'secondarynamenode']
    pkgs = ['hadoop-0.20'] + ['hadoop-0.20-%s' % pkg for pkg in hadoop_pkgs]
    apt_install(' '.join(pkgs))
    run_command('easy_install dumbo')


def install_ipython():
    chdir(SRC_DIR)
    apt_install('libzmq-dev')
    run_command('pip install ipython tornado pygments pyzmq')
    mjax_install = 'from IPython.external.mathjax import install_mathjax'
    mjax_install += '; install_mathjax()'
    run_command("python -c '%s'" % mjax_install)


def configure_motd():
    for f in glob.glob('/etc/update-motd.d/*'):
        os.unlink(f)
    motd = open('/etc/update-motd.d/00-starcluster', 'w')
    motd.write(STARCLUSTER_MOTD)
    motd.close()
    os.chmod(motd.name, 0755)


def configure_cloud_init():
    """docstring for configure_cloud_init"""
    cloudcfg = open('/etc/cloud/cloud.cfg', 'w')
    cloudcfg.write(CLOUD_INIT_CFG)
    cloudcfg.close()


def configure_bash():
    completion_line_found = False
    for line in fileinput.input('/etc/bash.bashrc', inplace=1):
        if 'bash_completion' in line and line.startswith('#'):
            print line.replace('#', ''),
            completion_line_found = True
        elif completion_line_found:
            print line.replace('#', ''),
            completion_line_found = False
        else:
            print line,
    aliasfile = open('/root/.bash_aliases', 'w')
    aliasfile.write("alias ..='cd ..'\n")
    aliasfile.close()


def setup_environ():
    num_cpus = multiprocessing.cpu_count()
    os.environ['MAKEFLAGS'] = '-j%d' % (num_cpus + 1)
    os.environ['DEBIAN_FRONTEND'] = "noninteractive"
    if os.path.isfile('/sbin/initctl') and not os.path.islink('/sbin/initctl'):
        run_command('mv /sbin/initctl /sbin/initctl.bak')
        run_command('ln -s /bin/true /sbin/initctl')


def install_nfs():
    chdir(SRC_DIR)
    run_command('initctl reload-configuration')
    apt_install('nfs-kernel-server')
    run_command('ln -s /etc/init.d/nfs-kernel-server /etc/init.d/nfs')


def install_default_packages():
    # stop mysql for interactively asking for password
    preseedf = '/tmp/mysql-preseed.txt'
    mysqlpreseed = open(preseedf, 'w')
    preseeds = """\
mysql-server mysql-server/root_password select
mysql-server mysql-server/root_password seen true
mysql-server mysql-server/root_password_again select
mysql-server mysql-server/root_password_again seen true
    """
    mysqlpreseed.write(preseeds)
    mysqlpreseed.close()
    run_command('debconf-set-selections < %s' % mysqlpreseed.name)
    run_command('rm %s' % mysqlpreseed.name)
    pkgs = ["git", "mercurial", "subversion", "cvs", "vim",  "vim-scripts",
            "emacs", "tmux", "screen", "zsh", "ksh", "csh", "tcsh", "encfs",
            "keychain", "unzip", "rar", "unace", "ec2-api-tools",
            "ec2-ami-tools", "mysql-server", "mysql-client", "apache2",
            "libapache2-mod-wsgi", "sysv-rc-conf", "pssh", "cython", "irssi",
            "htop", "mosh", "default-jdk", "xvfb", "python-imaging",
            "python-ctypes"]
    apt_install(' '.join(pkgs))


def install_python_packges():
    pypkgs = ['python-boto', 'python-paramiko', 'python-django',
              'python-pudb']
    for pypkg in pypkgs:
        if pypkg.startswith('python-'):
            apt_command('build-dep %s' % pypkg.split('python-')[1])
        run_command('pip install %s')


def configure_init():
    for script in ['nfs-kernel-server', 'hadoop', 'condor', 'apache', 'mysql']:
        run_command('find /etc/rc* -iname \*%s\* -delete' % script)


def cleanup():
    run_command('rm -f /etc/resolv.conf')
    run_command('rm -rf /var/run/resolvconf')
    run_command('rm -f /etc/mtab')
    run_command('rm -rf /root/*')
    exclude = ['/root/.bashrc', '/root/.profile', '/root/.bash_aliases']
    for dot in glob.glob("/root/.*"):
        if dot not in exclude:
            run_command('rm -rf %s' % dot)
    for path in glob.glob('/usr/local/src/*'):
        if os.path.isdir(path):
            shutil.rmtree(path)
    run_command('rm -f /var/cache/apt/archives/*.deb')
    run_command('rm -f /var/cache/apt/archives/partial/*')
    for f in glob.glob('/etc/profile.d'):
        if 'byobu' in f:
            run_command('rm -f %s' % f)
    if os.path.islink('/sbin/initctl') and os.path.isfile('/sbin/initctl.bak'):
        run_command('mv -f /sbin/initctl.bak /sbin/initctl')


def main():
    """docstring for main"""
    if os.getuid() != 0:
        sys.stderr.write('you must be root to run this script\n')
        return
    setup_environ()
    configure_motd()
    configure_cloud_init()
    configure_bash()
    configure_apt_sources()
    upgrade_packages()
    install_build_utils()
    install_default_packages()
    install_gridscheduler()
    install_condor()
    #install_torque()
    install_pydrmaa()
    install_blas_lapack()
    install_numpy_scipy()
    install_matplotlib()
    install_pandas()
    install_ipython()
    install_mpi()
    install_hadoop()
    install_nfs()
    install_julia()
    configure_init()
    cleanup()

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = scimage_13_04
#!/usr/bin/env python
"""
This script is meant to be run inside of a ubuntu cloud image available at
uec-images.ubuntu.com::

    $ EC2_UBUNTU_IMG_URL=http://uec-images.ubuntu.com/precise/current
    $ wget $EC2_UBUNTU_IMG_URL/precise-server-cloudimg-amd64.tar.gz

or::

    $ wget $EC2_UBUNTU_IMG_URL/precise-server-cloudimg-i386.tar.gz

After downloading a Ubuntu cloud image the next step is to extract the image::

    $ tar xvzf precise-server-cloudimg-amd64.tar.gz

Then resize it to 10GB::

    $ e2fsck -f precise-server-cloudimg-amd64.img
    $ resize2fs precise-server-cloudimg-amd64.img 10G

Next you need to mount the image::

    $ mkdir /tmp/img-mount
    $ mount precise-server-cloudimg-amd64.img /tmp/img-mount
    $ mount -t proc none /tmp/img-mount/proc
    $ mount -t sysfs none /tmp/img-mount/sys
    $ mount -o bind /dev /tmp/img-mount/dev
    $ mount -t devpts none /tmp/img-mount/dev/pts
    $ mount -o rbind /var/run/dbus /tmp/img-mount/var/run/dbus

Copy /etc/resolv.conf and /etc/mtab to the image::

    $ mkdir -p /tmp/img-mount/var/run/resolvconf
    $ cp /etc/resolv.conf /tmp/img-mount/var/run/resolvconf/resolv.conf
    $ grep -v rootfs /etc/mtab > /tmp/img-mount/etc/mtab

Next copy this script inside the image::

    $ cp /path/to/scimage.py /tmp/img-mount/root/scimage.py

Finally chroot inside the image and run this script:

    $ chroot /tmp/img-mount /bin/bash
    $ cd $HOME
    $ python scimage.py
"""

import os
import sys
import glob
import shutil
import fileinput
import subprocess
import multiprocessing

SRC_DIR = "/usr/local/src"
APT_SOURCES_FILE = "/etc/apt/sources.list"
BUILD_UTILS_PKGS = "build-essential devscripts debconf debconf-utils dpkg-dev "
BUILD_UTILS_PKGS += "python-dev python-setuptools python-pip python-nose rar "
BUILD_UTILS_PKGS += "python-distutils-extra gfortran unzip unace cdbs patch "
GRID_SCHEDULER_GIT = 'git://github.com/jtriley/gridscheduler.git'
CLOUDERA_ARCHIVE_KEY = 'http://archive.cloudera.com/debian/archive.key'
CLOUDERA_APT = 'http://archive.cloudera.com/debian squeeze-cdh3u5 contrib'
PPAS = ["ppa:staticfloat/julia-deps", "ppa:justin-t-riley/starcluster",
        "ppa:staticfloat/julianightlies"]
STARCLUSTER_MOTD = """\
#!/bin/sh
cat<<"EOF"
          _                 _           _
__/\_____| |_ __ _ _ __ ___| |_   _ ___| |_ ___ _ __
\    / __| __/ _` | '__/ __| | | | / __| __/ _ \ '__|
/_  _\__ \ || (_| | | | (__| | |_| \__ \ ||  __/ |
  \/ |___/\__\__,_|_|  \___|_|\__,_|___/\__\___|_|

StarCluster Ubuntu 13.04 AMI
Software Tools for Academics and Researchers (STAR)
Homepage: http://star.mit.edu/cluster
Documentation: http://star.mit.edu/cluster/docs/latest
Code: https://github.com/jtriley/StarCluster
Mailing list: http://star.mit.edu/cluster/mailinglist.html

This AMI Contains:

  * Open Grid Scheduler (OGS - formerly SGE) queuing system
  * Condor workload management system
  * OpenMPI compiled with Open Grid Scheduler support
  * OpenBLAS - Highly optimized Basic Linear Algebra Routines
  * NumPy/SciPy linked against OpenBlas
  * Pandas - Data Analysis Library
  * IPython 1.1.0 with parallel and notebook support
  * Julia 0.3pre
  * and more! (use 'dpkg -l' to show all installed packages)

Open Grid Scheduler/Condor cheat sheet:

  * qstat/condor_q - show status of batch jobs
  * qhost/condor_status- show status of hosts, queues, and jobs
  * qsub/condor_submit - submit batch jobs (e.g. qsub -cwd ./job.sh)
  * qdel/condor_rm - delete batch jobs (e.g. qdel 7)
  * qconf - configure Open Grid Scheduler system

Current System Stats:

EOF

landscape-sysinfo | grep -iv 'graph this data'
"""


def run_command(cmd, ignore_failure=False, failure_callback=None,
                get_output=False):
    kwargs = {}
    if get_output:
        kwargs.update(dict(stdout=subprocess.PIPE, stderr=subprocess.PIPE))
    p = subprocess.Popen(cmd, shell=True, **kwargs)
    output = []
    if get_output:
        line = None
        while line != '':
            line = p.stdout.readline()
            if line != '':
                output.append(line)
                print line,
        for line in p.stderr.readlines():
            if line != '':
                output.append(line)
                print line,
    retval = p.wait()
    if retval != 0:
        errmsg = "command '%s' failed with status %d" % (cmd, retval)
        if failure_callback:
            ignore_failure = failure_callback(retval)
        if not ignore_failure:
            raise Exception(errmsg)
        else:
            sys.stderr.write(errmsg + '\n')
    if get_output:
        return retval, ''.join(output)
    return retval


def apt_command(cmd):
    dpkg_opts = "Dpkg::Options::='--force-confnew'"
    cmd = "apt-get -o %s -y --force-yes %s" % (dpkg_opts, cmd)
    cmd = "DEBIAN_FRONTEND='noninteractive' " + cmd
    run_command(cmd)


def apt_install(pkgs):
    apt_command('install %s' % pkgs)


def chdir(directory):
    opts = glob.glob(directory)
    isdirlist = [o for o in opts if os.path.isdir(o)]
    if len(isdirlist) > 1:
        raise Exception("more than one dir matches: %s" % directory)
    os.chdir(isdirlist[0])


def _fix_atlas_rules(rules_file='debian/rules'):
    for line in fileinput.input(rules_file, inplace=1):
        if 'ATLAS=None' not in line:
            print line,


def configure_apt_sources():
    srcfile = open(APT_SOURCES_FILE)
    contents = srcfile.readlines()
    srcfile.close()
    srclines = []
    for line in contents:
        if not line.strip() or line.startswith('#'):
            continue
        parts = line.split()
        if parts[0] == 'deb':
            parts[0] = 'deb-src'
            srclines.append(' '.join(parts).strip())
    with open(APT_SOURCES_FILE, 'w') as srcfile:
        srcfile.write(''.join(contents))
        srcfile.write('\n'.join(srclines) + '\n')
    with open('/etc/apt/sources.list.d/cloudera-hadoop.list', 'w') as srcfile:
        srcfile.write('deb %s\n' % CLOUDERA_APT)
        srcfile.write('deb-src %s\n' % CLOUDERA_APT)
    run_command('gpg --keyserver keyserver.ubuntu.com --recv-keys 0F932C9C')
    run_command('curl -s %s | sudo apt-key add -' % CLOUDERA_ARCHIVE_KEY)
    apt_install('debian-archive-keyring')
    for ppa in PPAS:
        run_command('add-apt-repository %s -y -s' % ppa)


def upgrade_packages():
    apt_command('update')
    apt_command('upgrade')


def install_build_utils():
    """docstring for configure_build"""
    apt_install(BUILD_UTILS_PKGS)


def install_gridscheduler():
    chdir(SRC_DIR)
    apt_command('build-dep gridengine')
    if os.path.isfile('gridscheduler-scbuild.tar.gz'):
        run_command('tar xvzf gridscheduler-scbuild.tar.gz')
        run_command('mv gridscheduler /opt/sge6-fresh')
        return
    run_command('git clone %s' % GRID_SCHEDULER_GIT)
    sts, out = run_command('readlink -f `which java`', get_output=True)
    java_home = out.strip().split('/jre')[0]
    chdir(os.path.join(SRC_DIR, 'gridscheduler', 'source'))
    run_command('git checkout -t -b develop origin/develop')
    env = 'JAVA_HOME=%s' % java_home
    run_command('%s ./aimk -only-depend' % env)
    run_command('%s scripts/zerodepend' % env)
    run_command('%s ./aimk depend' % env)
    run_command('%s ./aimk -no-secure -no-gui-inst -man' % env)
    sge_root = '/opt/sge6-fresh'
    os.mkdir(sge_root)
    env += ' SGE_ROOT=%s' % sge_root
    run_command('%s scripts/distinst -all -local -noexit -y -- man' % env)


def install_condor():
    chdir(SRC_DIR)
    run_command("rm -f /var/lock")
    #apt_install('condor=7.7.2-1')
    #run_command('echo condor hold | dpkg --set-selections')
    #run_command('ln -s /etc/condor/condor_config /etc/condor_config.local')
    #run_command('mkdir /var/lib/condor/log')
    #run_command('mkdir /var/lib/condor/run')
    #run_command('chown -R condor:condor /var/lib/condor/log')
    #run_command('chown -R condor:condor /var/lib/condor/run')
    apt_install('condor')


def install_pydrmaa():
    chdir(SRC_DIR)
    run_command('pip install drmaa')


def install_atlas():
    """docstring for install_atlas"""
    chdir(SRC_DIR)
    apt_command('build-dep atlas')
    if glob.glob("*atlas*.deb"):
        run_command('dpkg -i *atlas*.deb')
        return
    apt_command('source atlas')
    chdir('atlas-*')
    run_command('fakeroot debian/rules custom')
    run_command('dpkg -i ../*atlas*.deb')


def install_openblas():
    """docstring for install_openblas"""
    chdir(SRC_DIR)
    apt_command('build-dep libopenblas-dev')
    if glob.glob("*openblas*.deb"):
        run_command('dpkg -i *openblas*.deb')
    else:
        apt_command('source libopenblas-dev')
        chdir('openblas-*')
        rule_file = open('Makefile.rule', 'a')
        # NO_AFFINITY=1 is required to utilize all cores on all non
        # cluster-compute/GPU instance types due to the shared virtualization
        # layer not supporting processor affinity properly. However, Cluster
        # Compute/GPU instance types use a near-bare-metal hypervisor which
        # *does* support processor affinity. From minimal testing it appears
        # that there is a ~20% increase in performance when using affinity on
        # cc1/cg1 types implying NO_AFFINITY=1 should *not* be set for cluster
        # compute/GPU AMIs.
        lines = ['DYNAMIC_ARCH=1', 'NUM_THREADS=64', 'NO_LAPACK=1',
                 'NO_AFFINITY=1']
        rule_file.write('\n'.join(lines))
        rule_file.close()
        run_command('fakeroot debian/rules custom')
        run_command('dpkg -i ../*openblas*.deb')
    run_command('echo libopenblas-base hold | dpkg --set-selections')
    run_command('echo libopenblas-dev hold | dpkg --set-selections')
    run_command("ldconfig")


def install_python_packages():
    install_pydrmaa()
    install_numpy_scipy()
    install_pandas()
    install_ipython()
    apt_command('build-dep python-imaging')
    pkgs = "virtualenv pillow boto matplotlib django mpi4py ctypes Cython "
    pkgs += "pudb supervisor "
    run_command("pip install %s" % pkgs)


def install_numpy_scipy():
    """docstring for install_numpy"""
    chdir(SRC_DIR)
    apt_command('build-dep python-numpy')
    apt_command('build-dep python-scipy')
    run_command('pip install -d . numpy')
    run_command('tar xvzf numpy*.tar.gz')
    run_command("sed -i 's/return None #/pass #/' numpy*/numpy/core/setup.py")
    run_command("cd numpy* && python setup.py install")
    run_command('pip install scipy')


def install_pandas():
    """docstring for install_pandas"""
    chdir(SRC_DIR)
    apt_command('build-dep pandas')
    run_command('pip install pandas')


def install_openmpi():
    chdir(SRC_DIR)
    apt_command('build-dep openmpi')
    apt_install('blcr-util')
    if glob.glob('*openmpi*.deb'):
        run_command('dpkg -i *openmpi*.deb')
    else:
        apt_command('source openmpi')
        chdir('openmpi*')
        for line in fileinput.input('debian/rules', inplace=1):
            print line,
            if '--enable-heterogeneous' in line:
                print '                        --with-sge \\'

        def _deb_failure_callback(retval):
            if not glob.glob('../*openmpi*.deb'):
                return False
            return True
        run_command('dch --local=\'+custom\' '
                    '"custom build on: `uname -s -r -v -m -p -i -o`"')
        run_command('dpkg-buildpackage -rfakeroot -b',
                    failure_callback=_deb_failure_callback)
        run_command('dpkg -i ../*openmpi*.deb')
    sts, out = run_command('ompi_info | grep -i grid', get_output=True)
    if 'gridengine' not in out:
        raise Exception("failed to build OpenMPI with "
                        "Open Grid Scheduler support")
    run_command('echo libopenmpi1.3 hold | dpkg --set-selections')
    run_command('echo libopenmpi-dev hold | dpkg --set-selections')
    run_command('echo libopenmpi-dbg hold | dpkg --set-selections')
    run_command('echo openmpi-bin hold | dpkg --set-selections')
    run_command('echo openmpi-checkpoint hold | dpkg --set-selections')
    run_command('echo openmpi-common hold | dpkg --set-selections')
    run_command('echo openmpi-doc hold | dpkg --set-selections')
    run_command('ldconfig')


def install_hadoop():
    chdir(SRC_DIR)
    hadoop_pkgs = ['namenode', 'datanode', 'tasktracker', 'jobtracker',
                   'secondarynamenode']
    pkgs = ['hadoop-0.20'] + ['hadoop-0.20-%s' % pkg for pkg in hadoop_pkgs]
    apt_install(' '.join(pkgs))
    run_command('easy_install dumbo')


def install_ipython():
    chdir(SRC_DIR)
    apt_install('libzmq-dev')
    run_command('pip install ipython[parallel,notebook]')
    # This is broken in IPy 1.1.0
    #mjax_install = 'from IPython.external.mathjax import install_mathjax'
    #mjax_install += '; install_mathjax()'
    #run_command("python -c '%s'" % mjax_install)


def install_julia():
    #chdir(SRC_DIR)
    #apt_install('zlib1g-dev patchelf llvm-3.3-dev libsuitesparse-dev '
    #            'libncurses5-dev libopenblas-dev liblapack-dev '
    #            'libarpack2-dev libfftw3-dev libgmp-dev libpcre3-dev '
    #            'libunwind8-dev libreadline-dev libdouble-conversion-dev '
    #            'libopenlibm-dev librmath-dev libmpfr-dev')
    #run_command('git clone git://github.com/JuliaLang/julia.git')
    #buildopts = 'LLVM_CONFIG=llvm-config-3.3 VERBOSE=1 USE_BLAS64=0 '
    #libs = ['LLVM', 'ZLIB', 'SUITESPARSE', 'ARPACK', 'BLAS', 'FFTW', 'LAPACK',
    #        'GMP', 'MPFR', 'PCRE', 'LIBUNWIND', 'READLINE', 'GRISU',
    #        'OPENLIBM', 'RMATH']
    #buildopts += ' '.join(['USE_SYSTEM_%s=1' % lib for lib in libs])
    #run_command('cd julia && make %s PREFIX=/usr install' % buildopts)
    apt_install("julia")


def configure_motd():
    for f in glob.glob('/etc/update-motd.d/*'):
        os.unlink(f)
    motd = open('/etc/update-motd.d/00-starcluster', 'w')
    motd.write(STARCLUSTER_MOTD)
    motd.close()
    os.chmod(motd.name, 0755)


def configure_bash():
    completion_line_found = False
    for line in fileinput.input('/etc/bash.bashrc', inplace=1):
        if 'bash_completion' in line and line.startswith('#'):
            print line.replace('#', ''),
            completion_line_found = True
        elif completion_line_found:
            print line.replace('#', ''),
            completion_line_found = False
        else:
            print line,
    aliasfile = open('/root/.bash_aliases', 'w')
    aliasfile.write("alias ..='cd ..'\n")
    aliasfile.close()


def setup_environ():
    num_cpus = multiprocessing.cpu_count()
    os.environ['MAKEFLAGS'] = '-j%d' % (num_cpus + 1)
    os.environ['DEBIAN_FRONTEND'] = "noninteractive"
    if os.path.isfile('/sbin/initctl') and not os.path.islink('/sbin/initctl'):
        run_command('mv /sbin/initctl /sbin/initctl.bak')
        run_command('ln -s /bin/true /sbin/initctl')


def install_nfs():
    chdir(SRC_DIR)
    run_command('initctl reload-configuration')
    apt_install('nfs-kernel-server')
    run_command('ln -s /etc/init.d/nfs-kernel-server /etc/init.d/nfs')


def install_default_packages():
    # stop mysql for interactively asking for password
    preseedf = '/tmp/mysql-preseed.txt'
    mysqlpreseed = open(preseedf, 'w')
    preseeds = """\
mysql-server mysql-server/root_password select
mysql-server mysql-server/root_password seen true
mysql-server mysql-server/root_password_again select
mysql-server mysql-server/root_password_again seen true
    """
    mysqlpreseed.write(preseeds)
    mysqlpreseed.close()
    run_command('debconf-set-selections < %s' % mysqlpreseed.name)
    run_command('rm %s' % mysqlpreseed.name)
    pkgs = "git vim mercurial subversion cvs encfs keychain screen tmux zsh "
    pkgs += "ksh csh tcsh ec2-api-tools ec2-ami-tools mysql-server "
    pkgs += "mysql-client apache2 libapache2-mod-wsgi nginx sysv-rc-conf "
    pkgs += "pssh emacs irssi htop vim-scripts mosh default-jdk mpich2 xvfb "
    pkgs += "openmpi-bin libopenmpi-dev libopenblas-dev liblapack-dev julia"
    apt_install(pkgs)


def configure_init():
    scripts = ['nfs-kernel-server', 'hadoop', 'condor', 'apache', 'mysql',
               'nginx']
    for script in scripts:
        run_command('find /etc/rc* -iname \*%s\* -delete' % script)


def cleanup():
    run_command('rm -rf /run/resolvconf')
    run_command('rm -f /etc/mtab')
    run_command('rm -rf /root/*')
    exclude = ['/root/.bashrc', '/root/.profile', '/root/.bash_aliases']
    for dot in glob.glob("/root/.*"):
        if dot not in exclude:
            run_command('rm -rf %s' % dot)
    for path in glob.glob('/usr/local/src/*'):
        if os.path.isdir(path):
            shutil.rmtree(path)
    run_command('rm -f /var/cache/apt/archives/*.deb')
    run_command('rm -f /var/cache/apt/archives/partial/*')
    for f in glob.glob('/etc/profile.d'):
        if 'byobu' in f:
            run_command('rm -f %s' % f)
    if os.path.islink('/sbin/initctl') and os.path.isfile('/sbin/initctl.bak'):
        run_command('mv -f /sbin/initctl.bak /sbin/initctl')


def main():
    """docstring for main"""
    if os.getuid() != 0:
        sys.stderr.write('you must be root to run this script\n')
        return
    setup_environ()
    configure_motd()
    configure_bash()
    configure_apt_sources()
    upgrade_packages()
    install_build_utils()
    install_nfs()
    install_default_packages()
    install_python_packages()
    # Only use these to build the packages locally
    # These should normally be installed from the PPAs
    #install_openblas()
    #install_openmpi()
    #install_julia()
    install_gridscheduler()
    install_condor()
    install_hadoop()
    configure_init()
    cleanup()

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = scimgdeploy
#!/usr/bin/env python
import os
import sys
import time
import optparse

from starcluster import config
from starcluster import cluster
from starcluster import spinner
from starcluster import exception
from starcluster import logger
logger.configure_sc_logging()
log = logger.log


def deploy_img(img_path, vol_size, arch, region, src_ami, dev=None,
               kernel_id=None, ramdisk_id=None, platform=None,
               remove_old=False, **cluster_kwargs):
    """
    Deploy a filesystem image as a new AMI in a given region.

    This method creates a 1-node host cluster in the desired `region`, copies
    the filesystem image to the cluster, creates and attaches a new EBS volume
    with size `vol_size`, installs the image onto the new EBS volume, creates a
    snapshot of the resulting volume and registers a new AMI in the `region`.
    """
    cfg = config.StarClusterConfig().load()
    ec2 = cfg.get_easy_ec2()
    ec2.connect_to_region(region)
    src_img = ec2.get_image(src_ami)
    kernel_id = kernel_id or src_img.kernel_id
    ramdisk_id = ramdisk_id or src_img.ramdisk_id
    itypemap = dict(i386='m1.small', x86_64='m1.large')
    dev = dev or dict(i386='/dev/sdj', x86_64='/dev/sdz')[arch]
    cm = cluster.ClusterManager(cfg, ec2)
    try:
        log.info("Checking for existing imghost cluster")
        cl = cm.get_cluster('imghost')
        log.info("Using existing imghost cluster")
    except exception.ClusterDoesNotExist:
        log.info("No imghost cluster found, creating...")
        default = cm.get_default_cluster_template()
        cl = cm.get_cluster_template(default, 'imghost')
        keys = ec2.get_keypairs()
        key = None
        for k in keys:
            if k.name in cfg.keys:
                key = cfg.keys.get(k.name)
                key['keyname'] = k.name
                break
        if key:
            cluster_kwargs.update(key)
        hostitype = itypemap[src_img.architecture]
        cluster_kwargs.update(dict(cluster_size=1, cluster_shell="bash",
                                   node_image_id=src_ami,
                                   node_instance_type=hostitype))
        cl.update(cluster_kwargs)
        cl.start(create_only=True, validate=True)
    cl.wait_for_cluster()
    host = cl.master_node
    log.info("Copying %s to /mnt on master..." % img_path)
    host.ssh.put(img_path, '/mnt/')
    bname = os.path.basename(img_path)
    if bname.endswith('.tar.gz'):
        log.info("Extracting image(s)...")
        host.ssh.execute('cd /mnt && tar xvzf %s' % bname)
        bname = bname.replace('.tar.gz', '')
    if not host.ssh.isfile('/mnt/%s' % bname):
        raise exception.BaseException("/mnt/%s does not exist" % bname)
    log.info("Creating EBS volume")
    vol = ec2.create_volume(vol_size, host.placement)
    log.info("Attaching EBS volume %s to master as %s" % (vol.id, dev))
    vol.attach(host.id, dev)
    log.info("Waiting for drive to attach...")
    s = spinner.Spinner()
    s.start()
    realdev = '/dev/xvd%s' % dev[-1]
    while not host.ssh.path_exists(realdev):
        time.sleep(10)
    s.stop()
    log.info("Installing image on volume %s ..." % vol.id)
    host.ssh.execute("cat /mnt/%s > %s" % (bname, realdev))
    log.info("Checking filesystem...")
    host.ssh.execute("e2fsck -pf %s" % realdev)
    log.info("Resizing filesystem to fit EBS volume...")
    host.ssh.execute("resize2fs %s" % realdev)
    vol.detach()
    while vol.update() != 'available':
        time.sleep(10)
    xarch = arch
    if xarch == 'i386':
        xarch = 'x86'
    snapdesc = 'StarCluster %s %s EBS AMI Snapshot' % (platform, xarch)
    snap = ec2.create_snapshot(vol, description=snapdesc,
                               wait_for_snapshot=True)
    vol.delete()
    bmap = ec2.create_root_block_device_map(snap.id, add_ephemeral_drives=True)
    imgname = platform.replace(' ', '-').lower()
    imgname = 'starcluster-base-%s-%s' % (imgname, xarch)
    imgdesc = 'StarCluster Base %s %s (%s)' % (platform, xarch, region.upper())
    oldimg = ec2.get_images(filters=dict(name=imgname))
    if oldimg:
        oldimg = oldimg[0]
        oldsnap_id = oldimg.block_device_mapping['/dev/sda1'].snapshot_id
        oldsnap = ec2.get_snapshot(oldsnap_id)
        if remove_old:
            log.info("Deregistering old AMI: %s" % oldimg.id)
            oldimg.deregister()
            log.info("Deleting old snapshot: %s" % oldsnap.id)
            oldsnap.delete()
        else:
            log.info("Existing image %s already has name '%s'" %
                     (oldimg.id, imgname))
            log.info("Please remove old image %s and snapshot %s" %
                     (oldimg.id, oldsnap.id))
            log.info("Then register new AMI with snapshot %s and name '%s'" %
                     (snap.id, imgname))
            return
    img = ec2.register_image(name=imgname, description=imgdesc,
                             architecture=arch, kernel_id=kernel_id,
                             ramdisk_id=ramdisk_id,
                             root_device_name='/dev/sda1',
                             block_device_map=bmap)
    return img


def main():
    parser = optparse.OptionParser('deploy disk image to region')
    parser.usage = '%s [options] <img_path> <vol_size> <img_arch> '
    parser.usage += '<region> <src_ami>'
    parser.usage = parser.usage % sys.argv[0]
    parser.add_option('-d', '--device', action="store", dest='dev',
                      default=None, help="device to attach volume to"
                      "(defaults to /dev/sdj for 32bit, /dev/sdz for 64bit)")
    parser.add_option('-k', '--kernel-id', action="store", dest='kernel_id',
                      default=None, help="kernel to use for AMI (defaults to "
                      "same as src_ami)")
    parser.add_option('-r', '--ramdisk-id', action="store", dest='ramdisk_id',
                      default=None, help="ramdisk to use for AMI (defaults to "
                      "same as src_ami)")
    parser.add_option('-R', '--remove-old-ami', action="store_true",
                      dest='remove_old', default=False,
                      help="remove any AMI with same name as generated AMI")
    parser.add_option('-p', '--platform', action="store", dest='platform',
                      default=None, help="platform name (e.g. Ubuntu 11.10)")
    opts, args = parser.parse_args()
    if len(args) != 5:
        parser.error('not enough arguments specified (pass --help for usage)')
    img_path, vol_size, arch, region, src_ami = args
    size_err = 'vol_size must be an integer > 0'
    try:
        vol_size = int(vol_size)
        if vol_size <= 0:
            parser.error(size_err)
    except ValueError:
            parser.error(size_err)
    if not os.path.exists(img_path):
        parser.error('img_path %s does not exist' % img_path)
    arches = ['i386', 'x86_64']
    if arch not in arches:
        parser.error('arch must be one of: %s' % ', '.join(arches))
        return False
    try:
        img = deploy_img(*args, **opts.__dict__)
        log.info("Successfully deployed new AMI: %s" % img)
    except exception.BaseException, e:
        log.error(e)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = webserver
#!/usr/bin/env python
import os
import optparse
import mimetypes
import posixpath
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer

ERROR_MSG = """\
<head>
<title>DOH!</title>
</head>
<body>
<pre>
 _  _    ___  _  _
| || |  / _ \| || |
| || |_| | | | || |_
|__   _| |_| |__   _|
   |_|  \___/   |_|

</pre>
<h1>Error response</h1>
<p>Error code %(code)d.
<p>Message: %(message)s.
<p>Error code explanation: %(code)s = %(explain)s.
</body>
"""


class MyHandler(BaseHTTPRequestHandler):
    error_message_format = ERROR_MSG

    def do_GET(self):
        try:
            docroot = globals()['DOCUMENTROOT']
            fname = posixpath.join(docroot, self.path[1:])
            #remove query args. query args are ignored in static server
            fname = fname.split('?')[0]
            if fname.endswith('/') or os.path.isdir(fname):
                fname = posixpath.join(fname, 'index.html')
            f = open(fname)  # self.path has /test.html
            content_type = mimetypes.guess_type(fname)[0]
            self.send_response(200)
            self.send_header('Content-type', content_type)
            self.end_headers()
            while True:
                data = f.read(2097152)
                if not data:
                    break
                self.wfile.write(data)
            #self.wfile.write(f.read())
            f.close()
            return
        except IOError:
            self.send_error(404, 'File Not Found: %s' % self.path)

    def do_POST(self):
        try:
            print 'no posting!'
        except IOError:
            self.send_error(404, 'File Not Found: %s' % self.path)


def main(path, interface="localhost", port=8080):
    try:
        docroot = os.path.realpath(path)
        globals()['DOCUMENTROOT'] = docroot
        server = HTTPServer((interface, port), MyHandler)
        print 'started httpserver...'
        print 'document_root = %s' % docroot
        server.serve_forever()
    except KeyboardInterrupt:
        print '^C received, shutting down server'
        server.socket.close()

if __name__ == '__main__':
    parser = optparse.OptionParser()
    parser.add_option("-i", "--interface", dest="interface", action="store",
                      default="localhost")
    parser.add_option("-p", "--port", dest="port", action="store", type="int",
                      default=8080)
    opts, args = parser.parse_args()
    if len(args) != 1:
        parser.error('usage:  webserver.py <document_root>')
    path = args[0]
    main(path, **opts.__dict__)

########NEW FILE########
