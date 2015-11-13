__FILENAME__ = example_dnst
from ooni.templates import dnst

class ExampleDNSTest(dnst.DNSTest):
    inputFile = ['file', 'f', None, 'foobar']

    def test_a_lookup(self):
        def gotResult(result):
            # Result is an array containing all the A record lookup results
            print result

        d = self.performALookup('torproject.org', ('8.8.8.8', 53))
        d.addCallback(gotResult)
        return d

########NEW FILE########
__FILENAME__ = example_dns_http
from twisted.internet import defer
from ooni.templates import httpt, dnst

class TestDNSandHTTP(httpt.HTTPTest, dnst.DNSTest):

    @defer.inlineCallbacks
    def test_http_and_dns(self):
        yield self.doRequest('http://torproject.org')
        yield self.performALookup('torproject.org', ('8.8.8.8', 53))



########NEW FILE########
__FILENAME__ = example_httpt
# -*- encoding: utf-8 -*-
#
# :authors: Arturo Filastò
# :licence: see LICENSE

from ooni.utils import log
from ooni.templates import httpt

class ExampleHTTP(httpt.HTTPTest):
    name = "Example HTTP Test"
    author = "Arturo Filastò"
    version = 0.1

    inputs = ['http://google.com/', 'http://wikileaks.org/',
              'http://torproject.org/']

    def test_http(self):
        if self.input:
            url = self.input
            return self.doRequest(url)
        else:
            raise Exception("No input specified")

    def processResponseBody(self, body):
        # XXX here shall go your logic
        #     for processing the body
        if 'blocked' in body:
            self.report['censored'] = True
        else:
            self.report['censored'] = False

    def processResponseHeaders(self, headers):
        # XXX place in here all the logic for handling the processing of HTTP
        #     Headers.
        pass


########NEW FILE########
__FILENAME__ = example_http_checksum
# -*- encoding: utf-8 -*-
#
# :authors: Aaron Gibson
# :licence: see LICENSE

from ooni.utils import log
from ooni.templates import httpt
from hashlib import sha256

class SHA256HTTPBodyTest(httpt.HTTPTest):
    name = "ChecksumHTTPBodyTest"
    author = "Aaron Gibson"
    version = 0.1

    inputFile = ['file', 'f', None, 
            'List of URLS to perform GET requests to']

    def test_http(self):
        if self.input:
            url = self.input
            return self.doRequest(url)
        else:
            raise Exception("No input specified")

    def processResponseBody(self, body):
        body_sha256sum = sha256(body).digest()
        self.report['checksum'] = body_sha256sum

########NEW FILE########
__FILENAME__ = example_myip
# -*- encoding: utf-8 -*-
#
# :authors: Arturo Filastò
# :licence: see LICENSE

from ooni.templates import httpt
class MyIP(httpt.HTTPTest):
    inputs = ['https://check.torproject.org']

    def test_lookup(self):
        return self.doRequest(self.input)

    def processResponseBody(self, body):
        import re
        regexp = "Your IP address appears to be: <b>(.+?)<\/b>"
        match = re.search(regexp, body)
        try:
            self.report['myip'] = match.group(1)
        except:
            self.report['myip'] = None


########NEW FILE########
__FILENAME__ = example_scapyt
# -*- encoding: utf-8 -*-
#
# :licence: see LICENSE

from twisted.python import usage

from scapy.all import IP, ICMP

from ooni.templates import scapyt

class UsageOptions(usage.Options):
    optParameters = [['target', 't', '8.8.8.8', "Specify the target to ping"]]
    
class ExampleICMPPingScapy(scapyt.BaseScapyTest):
    name = "Example ICMP Ping Test"

    usageOptions = UsageOptions

    def test_icmp_ping(self):
        def finished(packets):
            print packets
            answered, unanswered = packets
            for snd, rcv in answered:
                rcv.show()

        packets = IP(dst=self.localOptions['target'])/ICMP()
        d = self.sr(packets)
        d.addCallback(finished)
        return d

########NEW FILE########
__FILENAME__ = example_scapyt_yield
# -*- encoding: utf-8 -*-
#
# :licence: see LICENSE

from twisted.python import usage
from twisted.internet import defer

from scapy.all import IP, ICMP

from ooni.templates import scapyt

class UsageOptions(usage.Options):
    optParameters = [['target', 't', self.localOptions['target'], "Specify the target to ping"]]

class ExampleICMPPingScapyYield(scapyt.BaseScapyTest):
    name = "Example ICMP Ping Test"

    usageOptions = UsageOptions

    @defer.inlineCallbacks
    def test_icmp_ping(self):
        packets = IP(dst=self.localOptions['target'])/ICMP()
        answered, unanswered = yield self.sr(packets)
        for snd, rcv in answered:
            rcv.show()

########NEW FILE########
__FILENAME__ = example_simple
from twisted.internet import defer
from ooni import nettest

class MyIP(nettest.NetTestCase):
    def test_simple(self):
        self.report['foobar'] = 'antani'
        return defer.succeed(42)


########NEW FILE########
__FILENAME__ = example_tcpt

from twisted.internet.error import ConnectionRefusedError
from ooni.utils import log
from ooni.templates import tcpt

class ExampleTCPT(tcpt.TCPTest):
    def test_hello_world(self):
        def got_response(response):
            print "Got this data %s" % response

        def connection_failed(failure):
            failure.trap(ConnectionRefusedError)
            print "Connection Refused"

        self.address = "127.0.0.1"
        self.port = 57002
        payload = "Hello World!\n\r"
        d = self.sendPayload(payload)
        d.addErrback(connection_failed)
        d.addCallback(got_response)
        return d

########NEW FILE########
__FILENAME__ = fabfile
import os
from fabric.api import run, env
from fabric.context_managers import settings
from fabric.operations import sudo, local, put

env.use_ssh_config = True

def update_docs():
    local('make html')
    build_dir = os.path.join(os.getcwd(), 'build', 'html')
    put(build_dir, '/tmp')

    run("sudo -u ooni rm -rf /home/ooni/website/build/docs/")
    run("sudo -u ooni cp -R /tmp/html/ /home/ooni/website/build/docs")

    run("rm -rf /tmp/html")
    update_website()

def update_website():
    run("sudo -u mirroradm /usr/local/bin/static-master-update-component ooni.torproject.org")



########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# OONI documentation build configuration file, created by
# sphinx-quickstart on Sat Jun  2 19:54:47 2012.
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
sys.path.insert(0,
            os.path.join(os.path.dirname(__file__), '..', '..'))


# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.todo', 'sphinx.ext.coverage', 'sphinx.ext.pngmath',
'sphinx.ext.viewcode', 'sphinx.ext.autodoc']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'OONI'
copyright = u'2012, The Tor Project'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.1'
# The full version, including alpha/beta/rc tags.
release = '0.1-alpha'

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
exclude_patterns = []

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
htmlhelp_basename = 'OONIdoc'


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
  ('index', 'OONI.tex', u'OONI Documentation',
   u'The Tor Project', 'manual'),
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
    ('index', 'ooniprobe', u'an internet censorship measurement tool',
     [u'The Tor Project'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'OONI', u'OONI Documentation',
   u'The Tor Project', 'OONI', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

########NEW FILE########
__FILENAME__ = fabfile
#-*- coding: utf-8 -*-
#
# :authors: Arturo Filastò, Isis Lovecruft
# :license: see included LICENSE file
import os
import sys
import yaml
import xmlrpclib
from StringIO import StringIO

from fabric.operations import get
from fabric.api import run, cd, sudo, env

api_auth = {}
# Set these values 
api_auth['Username'] = "you@example.com"
api_auth['AuthString'] = "your_password"
slice_name = "your_slice_name"

### Do not change this
api_auth['AuthMethod'] = "password"

env.user = 'root'
def set_hosts(host_file):
    with open(host_file) as f:
        for host in f:
            env.hosts.append(host)

def search_node(nfilter="*.cert.org.cn"):
    api_server = xmlrpclib.ServerProxy('https://www.planet-lab.org/PLCAPI/')
    if api_server.AuthCheck(api_auth):
        print "We are authenticated"
    else:
        print "We are not authenticated"
    node_filter = {'hostname': nfilter}
    return_fields = ['hostname', 'site_id']
    all_nodes = api_server.GetNodes(api_auth, node_filter, return_fields)
    print all_nodes

def add_node(nodeid):
    node_id = int(nodeid)
    api_server = xmlrpclib.ServerProxy('https://www.planet-lab.org/PLCAPI/')
    node_filter = {'node_id': node_id}
    return_fields = ['hostname', 'site_id']
    nodes = api_server.GetNodes(api_auth, node_filter, return_fields)
    print 'Adding nodes %s' % nodes
    api_server.AddNode(api_auth, node_id, slice_name)

def deployooniprobe(distro="debian"):
    """
    This is used to deploy ooni-probe on debian based systems.
    """
    run("git clone https://git.torproject.org/ooni-probe.git ooni-probe")
    cd("ooni-probe")
    if distro == "debian":
        sudo("apt-get install git-core python python-pip python-dev")
    else:
        print "The selected distro is not supported"
        print "The following commands may fail"
    run("virtualenv env")
    run("source env/bin/activate")
    run("pip install https://hg.secdev.org/scapy/archive/tip.zip")
    run("pip install -r requirements.txt")

def generate_bouncer_file(install_directory='/data/oonib/', bouncer_file="bouncer.yaml"):
    output = StringIO()
    get(os.path.join(install_directory, 'oonib.conf'), output)
    output.seek(0)
    oonib_configuration = yaml.safe_load(output)
    
    output.truncate(0)
    get(os.path.join(oonib_configuration['main']['tor_datadir'], 'collector', 'hostname'),
        output)
    output.seek(0)
    collector_hidden_service = output.readlines()[0].strip()

    address = env.host
    test_helpers = {
            'dns': address + ':' + str(oonib_configuration['helpers']['dns']['tcp_port']),
            'ssl': 'https://' + address,
            'traceroute': address,
    }
    if oonib_configuration['helpers']['tcp-echo']['port'] == 80:
        test_helpers['tcp-echo'] = address
    else:
        test_helpers['http-return-json-headers'] = 'http://' + address

    bouncer_data = {
            'collector': 
                {
                    'httpo://'+collector_hidden_service: {'test-helper': test_helpers}
                }
    }
    with open(bouncer_file) as f:
        old_bouncer_data = yaml.safe_load(f)

    with open(bouncer_file, 'w+') as f:
        old_bouncer_data['collector']['httpo://'+collector_hidden_service] = {}
        old_bouncer_data['collector']['httpo://'+collector_hidden_service]['test-helper'] = test_helpers
        yaml.dump(old_bouncer_data, f)

########NEW FILE########
__FILENAME__ = spec
import os
import re
import copy
import json
import types
import tempfile
import functools

from twisted.python import usage
from cyclone import web, escape

from ooni.reporter import YAMLReporter, OONIBReporter, collector_supported
from ooni import errors
from ooni.nettest import NetTestLoader
from ooni.settings import config

class InvalidInputFilename(Exception):
    pass

class FilenameExists(Exception):
    pass

def check_xsrf(method):
    @functools.wraps(method)
    def wrapper(self, *args, **kw):
        xsrf_header = self.request.headers.get("X-XSRF-TOKEN")
        if self.xsrf_token != xsrf_header:
            raise web.HTTPError(403, "Invalid XSRF token.")
        return method(self, *args, **kw)
    return wrapper

class ORequestHandler(web.RequestHandler):
    serialize_lists = True
    xsrf_cookie_name = "XSRF-TOKEN"

    def write(self, chunk):
        """
        XXX This is a patch that can be removed once
        https://github.com/fiorix/cyclone/pull/92 makes it into a release.
        """
        if isinstance(chunk, types.ListType):
            chunk = escape.json_encode(chunk)
            self.set_header("Content-Type", "application/json")
        web.RequestHandler.write(self, chunk)

class Status(ORequestHandler):
    @check_xsrf
    def get(self):
        result = {'active_tests': oonidApplication.director.activeNetTests}
        self.write(result)

def list_inputs():
    input_list = []
    for filename in os.listdir(config.inputs_directory):
        input_list.append({'filename': filename})
    return input_list

class Inputs(ORequestHandler):
    """
    This handler is responsible for listing and adding new inputs.
    """

    @check_xsrf
    def get(self):
        """
        Obtain the list of currently installed inputs. Inputs are stored inside
        of $OONI_HOME/inputs/.
        """
        input_list = list_inputs()
        self.write(input_list)

    @check_xsrf
    def post(self):
        """
        Add a new input to the currently installed inputs.
        """
        input_file = self.request.files.get("file")[0]
        filename = input_file['filename']

        if not filename or not re.match('(\w.*\.\w.*).*', filename):
            raise InvalidInputFilename

        if os.path.exists(filename):
            raise FilenameExists

        content_type = input_file["content_type"]
        body = input_file["body"]

        fn = os.path.join(config.inputs_directory, filename)
        with open(os.path.abspath(fn), "w") as fp:
            fp.write(body)

class ListTests(ORequestHandler):

    @check_xsrf
    def get(self):
        test_list = copy.deepcopy(oonidApplication.director.netTests)
        for test_id in test_list.keys():
            test_list[test_id].pop('path')
        self.write(test_list)

def get_net_test_loader(test_options, test_file):
    """
    Args:
        test_options: (dict) containing as keys the option names.

        test_file: (string) the path to the test_file to be run.
    Returns:
        an instance of :class:`ooni.nettest.NetTestLoader` with the specified
        test_file and the specified options.
        """
    options = []
    for k, v in test_options.items():
        options.append('--'+k)
        options.append(v)

    net_test_loader = NetTestLoader(options,
            test_file=test_file)
    return net_test_loader

def get_reporters(net_test_loader):
    """
    Determines which reports are able to run and returns an instance of them.

    We always report to flat file via the :class:`ooni.reporters.YAMLReporter`
    and the :class:`ooni.reporters.OONIBReporter`.

    The later will be used only if we determine that Tor is running.

    Returns:
        a list of reporter instances
    """
    test_details = net_test_loader.testDetails
    reporters = []
    yaml_reporter = YAMLReporter(test_details, config.reports_directory)
    reporters.append(yaml_reporter)

    if config.reports.collector and collector_supported(config.reports.collector):
        oonib_reporter = OONIBReporter(test_details, collector)
        reporters.append(oonib_reporter)
    return reporters

def write_temporary_input(content):
    """
    Creates a temporary file for the given content.

    Returns:
        the path to the temporary file.
    """
    fd, path = tempfile.mkstemp()
    with open(path, 'w') as f:
        f.write(content)
        f.close()
    print "This is the path %s" % path
    return fd, path

class StartTest(ORequestHandler):

    @check_xsrf
    def post(self, test_name):
        """
        Starts a test with the specified options.
        """
        test_file = oonidApplication.director.netTests[test_name]['path']
        test_options = json.loads(self.request.body)
        tmp_files = []
        if ('manual_input' in test_options):
            for option, content in test_options['manual_input'].items():
                fd, path = write_temporary_input(content)
                test_options[option] = path
                tmp_files.append((fd, path))
            test_options.pop('manual_input')

        net_test_loader = get_net_test_loader(test_options, test_file)
        try:
            net_test_loader.checkOptions()
            d = oonidApplication.director.startNetTest(net_test_loader,
                                                       get_reporters(net_test_loader))
            @d.addBoth
            def cleanup(result):
                for fd, path in tmp_files:
                    os.close(fd)
                    os.remove(path)

        except errors.MissingRequiredOption, option_name:
            self.write({'error':
                        'Missing required option: "%s"' % option_name})
        except usage.UsageError, e:
            self.write({'error':
                        'Error in parsing options'})
        except errors.InsufficientPrivileges:
            self.write({'error':
                        'Insufficient priviledges'})

class StopTest(ORequestHandler):

    @check_xsrf
    def delete(self, test_name):
        pass

def get_test_results(test_id):
    """
    Returns:
        a list of test dicts that correspond to the test results for the given
        test_id.
        The dict is made like so:
        {
            'name': The name of the report,
            'content': The content of the report
        }
    """
    test_results = []
    for test_result in os.listdir(config.reports_directory):
        if test_result.startswith('report-'+test_id):
            with open(os.path.join(config.reports_directory, test_result)) as f:
                test_content = ''.join(f.readlines())
            test_results.append({'name': test_result,
                                 'content': test_content})
    test_results.reverse()
    return test_results

class TestStatus(ORequestHandler):

    @check_xsrf
    def get(self, test_id):
        """
        Returns the requested test_id details and the stored results for such
        test.
        """
        try:
            test = copy.deepcopy(oonidApplication.director.netTests[test_id])
            test.pop('path')
            test['results'] = get_test_results(test_id)
            self.write(test)
        except KeyError:
            self.write({'error':
                        'Test with such ID not found!'})

config.read_config_file()
oonidAPI = [
    (r"/status", Status),
    (r"/inputs", Inputs),
    (r"/test", ListTests),
    (r"/test/(.*)/start", StartTest),
    (r"/test/(.*)/stop", StopTest),
    (r"/test/(.*)", TestStatus),
    (r"/(.*)", web.StaticFileHandler,
        {"path": os.path.join(config.data_directory, 'ui', 'app'),
         "default_filename": "index.html"})
]

oonidApplication = web.Application(oonidAPI, debug=True)


########NEW FILE########
__FILENAME__ = deck
#-*- coding: utf-8 -*-

from ooni.oonibclient import OONIBClient
from ooni.nettest import NetTestLoader
from ooni.settings import config
from ooni.utils import log
from ooni import errors as e

from twisted.python.filepath import FilePath
from twisted.internet import reactor, defer

import os
import re
import yaml
import json
from hashlib import sha256

class InputFile(object):
    def __init__(self, input_hash, base_path=config.inputs_directory):
        self.id = input_hash
        cache_path = os.path.join(os.path.abspath(base_path), input_hash)
        self.cached_file = cache_path
        self.cached_descriptor = cache_path + '.desc'

    @property
    def descriptorCached(self):
        if os.path.exists(self.cached_descriptor):
            with open(self.cached_descriptor) as f:
                descriptor = json.load(f)
                self.load(descriptor)
            return True
        return False

    @property
    def fileCached(self):
        if os.path.exists(self.cached_file):
            try:
                self.verify()
            except AssertionError:
                log.err("The input %s failed validation. Going to consider it not cached." % self.id)
                return False
            return True
        return False

    def save(self):
        with open(self.cached_descriptor, 'w+') as f:
            json.dump({
                'name': self.name,
                'id': self.id,
                'version': self.version,
                'author': self.author,
                'date': self.date,
                'description': self.description
            }, f)

    def load(self, descriptor):
        self.name = descriptor['name']
        self.version = descriptor['version']
        self.author = descriptor['author']
        self.date = descriptor['date']
        self.description = descriptor['description']

    def verify(self):
        digest = os.path.basename(self.cached_file)
        with open(self.cached_file) as f:
            file_hash = sha256(f.read())
            assert file_hash.hexdigest() == digest

def nettest_to_path(path, allow_arbitrary_paths=False):
    """
    Takes as input either a path or a nettest name.

    Args:

        allow_arbitrary_paths:
            allow also paths that are not relative to the nettest_directory.

    Returns:

        full path to the nettest file.
    """
    if allow_arbitrary_paths and os.path.exists(path):
        return path

    fp = FilePath(config.nettest_directory).preauthChild(path + '.py')
    if fp.exists():
        return fp.path
    else:
        raise e.NetTestNotFound(path)

class Deck(InputFile):
    def __init__(self, deck_hash=None,
                 deckFile=None,
                 decks_directory=config.decks_directory):
        self.id = deck_hash
        self.requiresTor = False
        self.bouncer = ''
        self.netTestLoaders = []
        self.inputs = []
        self.testHelpers = {}

        self.oonibclient = OONIBClient(self.bouncer)

        self.decksDirectory = os.path.abspath(decks_directory)
        self.deckHash = deck_hash

        if deckFile: self.loadDeck(deckFile)

    @property
    def cached_file(self):
        return os.path.join(self.decksDirectory, self.deckHash)

    @property
    def cached_descriptor(self):
        return self.cached_file + '.desc'

    def loadDeck(self, deckFile):
        with open(deckFile) as f:
            self.deckHash = sha256(f.read()).hexdigest()
            f.seek(0)
            test_deck = yaml.safe_load(f)

        for test in test_deck:
            try:
                nettest_path = nettest_to_path(test['options']['test_file'])
            except e.NetTestNotFound:
                log.err("Could not find %s" % test['options']['test_file'])
                log.msg("Skipping...")
                continue
            net_test_loader = NetTestLoader(test['options']['subargs'],
                    test_file=nettest_path)
            self.insert(net_test_loader)
            #XXX: If the deck specifies the collector, we use the specified collector
            # And it should also specify the test helper address to use
            # net_test_loader.collector = test['options']['collector']

    def insert(self, net_test_loader):
        """ Add a NetTestLoader to this test deck """
        def has_test_helper(missing_option):
            for rth in net_test_loader.requiredTestHelpers:
                if missing_option == rth['option']:
                    return True
            return False
        try:
            net_test_loader.checkOptions()
            if net_test_loader.requiresTor:
                self.requiresTor = True
        except e.MissingRequiredOption, missing_options:
            if not self.bouncer:
                raise
            for missing_option in missing_options.message:
                if not has_test_helper(missing_option):
                    raise
            self.requiresTor = True
        self.netTestLoaders.append(net_test_loader)

    @defer.inlineCallbacks
    def setup(self):
        """ fetch and verify inputs for all NetTests in the deck """
        log.msg("Fetching required net test inputs...")
        for net_test_loader in self.netTestLoaders:
            yield self.fetchAndVerifyNetTestInput(net_test_loader)

        if self.bouncer:
            log.msg("Looking up test helpers...")
            yield self.lookupTestHelpers()

    @defer.inlineCallbacks
    def lookupTestHelpers(self):
        self.oonibclient.address = self.bouncer

        required_test_helpers = []
        requires_collector = []
        for net_test_loader in self.netTestLoaders:
            if not net_test_loader.collector:
                requires_collector.append(net_test_loader)

            for th in net_test_loader.requiredTestHelpers:
                # {'name':'', 'option':'', 'test_class':''}
                if th['test_class'].localOptions[th['option']]:
                    continue
                required_test_helpers.append(th['name'])

        if not required_test_helpers and not requires_collector:
            defer.returnValue(None)

        response = yield self.oonibclient.lookupTestHelpers(required_test_helpers)

        for net_test_loader in self.netTestLoaders:
            log.msg("Setting collector and test helpers for %s" % net_test_loader.testDetails['test_name'])

            # Only set the collector if the no collector has been specified
            # from the command line or via the test deck.
            if not required_test_helpers and net_test_loader in requires_collector:
                log.msg("Using the default collector: %s" % response['default']['collector'])
                net_test_loader.collector = response['default']['collector'].encode('utf-8')
                continue

            for th in net_test_loader.requiredTestHelpers:
                # Only set helpers which are not already specified
                if th['name'] not in required_test_helpers:
                    continue
                test_helper = response[th['name']]
                log.msg("Using this helper: %s" % test_helper)
                th['test_class'].localOptions[th['option']] = test_helper['address'].encode('utf-8')
                if net_test_loader in requires_collector:
                    net_test_loader.collector = test_helper['collector'].encode('utf-8')

    @defer.inlineCallbacks
    def fetchAndVerifyNetTestInput(self, net_test_loader):
        """ fetch and verify a single NetTest's inputs """
        log.debug("Fetching and verifying inputs")
        for i in net_test_loader.inputFiles:
            if 'url' in i:
                log.debug("Downloading %s" % i['url'])
                self.oonibclient.address = i['address']

                try:
                    input_file = yield self.oonibclient.downloadInput(i['hash'])
                except:
                    raise e.UnableToLoadDeckInput

                try:
                    input_file.verify()
                except AssertionError:
                    raise e.UnableToLoadDeckInput, cached_path

                i['test_class'].localOptions[i['key']] = input_file.cached_file

########NEW FILE########
__FILENAME__ = director
import os

from ooni.managers import ReportEntryManager, MeasurementManager
from ooni.reporter import Report
from ooni.utils import log, pushFilenameStack
from ooni.utils.net import randomFreePort
from ooni.nettest import NetTest, getNetTestInformation
from ooni.settings import config
from ooni import errors

from txtorcon import TorConfig, TorState, launch_tor, build_tor_connection

from twisted.internet import defer, reactor
from twisted.internet.endpoints import TCP4ClientEndpoint

class Director(object):
    """
    Singleton object responsible for coordinating the Measurements Manager and the
    Reporting Manager.

    How this all looks like is as follows:

    +------------------------------------------------+
    |                   Director                     |<--+
    +------------------------------------------------+   |
        ^                                ^               |
        |        Measurement             |               |
    +---------+  [---------]    +--------------------+   |
    |         |                 | MeasurementManager |   |
    | NetTest |  [---------]    +--------------------+   |
    |         |                 | [----------------] |   |
    +---------+  [---------]    | [----------------] |   |
        |                       | [----------------] |   |
        |                       +--------------------+   |
        v                                                |
    +---------+   ReportEntry                            |
    |         |   [---------]    +--------------------+  |
    |  Report |                  | ReportEntryManager |  |
    |         |   [---------]    +--------------------+  |
    +---------+                  | [----------------] |  |
                  [---------]    | [----------------] |--
                                 | [----------------] |
                                 +--------------------+

    [------------] are Tasks

    +------+
    |      |  are TaskManagers
    +------+
    |      |
    +------+

    +------+
    |      |  are general purpose objects
    +------+

    """
    _scheduledTests = 0
    # Only list NetTests belonging to these categories
    categories = ['blocking', 'manipulation']

    def __init__(self):
        self.activeNetTests = []

        self.measurementManager = MeasurementManager()
        self.measurementManager.director = self

        self.reportEntryManager = ReportEntryManager()
        self.reportEntryManager.director = self
        # Link the TaskManager's by least available slots.
        self.measurementManager.child = self.reportEntryManager
        # Notify the parent when tasks complete # XXX deadlock!?
        self.reportEntryManager.parent = self.measurementManager

        self.successfulMeasurements = 0
        self.failedMeasurements = 0

        self.totalMeasurements = 0

        # The cumulative runtime of all the measurements
        self.totalMeasurementRuntime = 0

        self.failures = []

        self.torControlProtocol = None

        # This deferred is fired once all the measurements and their reporting
        # tasks are completed.
        self.allTestsDone = defer.Deferred()
        self.sniffer = None

    def getNetTests(self):
        nettests = {}
        def is_nettest(filename):
            return not filename == '__init__.py' \
                    and filename.endswith('.py')

        for category in self.categories:
            dirname = os.path.join(config.nettest_directory, category)
            # print path to all filenames.
            for filename in os.listdir(dirname):
                if is_nettest(filename):
                    net_test_file = os.path.join(dirname, filename)
                    nettest = getNetTestInformation(net_test_file)
                    nettest['category'] = category.replace('/', '')

                    if nettest['id'] in nettests:
                        log.err("Found a two tests with the same name %s, %s" %
                                (net_test_file, nettests[nettest['id']]['path']))
                    else:
                        category = dirname.replace(config.nettest_directory, '')
                        nettests[nettest['id']] = nettest

        return nettests

    @defer.inlineCallbacks
    def start(self, start_tor=False):
        self.netTests = self.getNetTests()

        if config.advanced.start_tor and start_tor:
            yield self.startTor()
        elif config.tor.control_port:
            log.msg("Connecting to Tor Control Port...")
            yield self.getTorState()

        if config.global_options['no-geoip']:
            aux = [False]
            if config.global_options.get('annotations') is not None:
                annotations = [k.lower() for k in config.global_options['annotations'].keys()]
                aux = map(lambda x: x in annotations, ["city", "country", "asn"])
            if not all(aux):
                log.msg("You should add annotations for the country, city and ASN")
        else:
            yield config.probe_ip.lookup()

    @property
    def measurementSuccessRatio(self):
        if self.totalMeasurements == 0:
            return 0

        return self.successfulMeasurements / self.totalMeasurements

    @property
    def measurementFailureRatio(self):
        if self.totalMeasurements == 0:
            return 0

        return self.failedMeasurements / self.totalMeasurements

    @property
    def measurementSuccessRate(self):
        """
        The speed at which tests are succeeding globally.

        This means that fast tests that perform a lot of measurements will
        impact this value quite heavily.
        """
        if self.totalMeasurementRuntime == 0:
            return 0

        return self.successfulMeasurements / self.totalMeasurementRuntime

    @property
    def measurementFailureRate(self):
        """
        The speed at which tests are failing globally.
        """
        if self.totalMeasurementRuntime == 0:
            return 0

        return self.failedMeasurements / self.totalMeasurementRuntime

    def measurementTimedOut(self, measurement):
        """
        This gets called every time a measurement times out independenty from
        the fact that it gets re-scheduled or not.
        """
        pass

    def measurementStarted(self, measurement):
        self.totalMeasurements += 1

    def measurementSucceeded(self, result, measurement):
        log.debug("Successfully completed measurement: %s" % measurement)
        self.totalMeasurementRuntime += measurement.runtime
        self.successfulMeasurements += 1
        measurement.result = result
        return measurement

    def measurementFailed(self, failure, measurement):
        log.msg("Failed doing measurement: %s" % measurement)
        self.totalMeasurementRuntime += measurement.runtime

        self.failedMeasurements += 1
        self.failures.append((failure, measurement))
        measurement.result = failure
        return measurement

    def reporterFailed(self, failure, net_test):
        """
        This gets called every time a reporter is failing and has been removed
        from the reporters of a NetTest.
        Once a report has failed to be created that net_test will never use the
        reporter again.

        XXX hook some logic here.
        note: failure contains an extra attribute called failure.reporter
        """
        pass

    def netTestDone(self, net_test):
        self.activeNetTests.remove(net_test)
        if len(self.activeNetTests) == 0:
            self.allTestsDone.callback(None)

    @defer.inlineCallbacks
    def startNetTest(self, net_test_loader, reporters):
        """
        Create the Report for the NetTest and start the report NetTest.

        Args:
            net_test_loader:
                an instance of :class:ooni.nettest.NetTestLoader
        """
        if self.allTestsDone.called:
            self.allTestsDone = defer.Deferred()

        if config.privacy.includepcap:
            if not config.reports.pcap:
                config.reports.pcap = config.generate_pcap_filename(net_test_loader.testDetails)
            self.startSniffing()

        report = Report(reporters, self.reportEntryManager)

        net_test = NetTest(net_test_loader, report)
        net_test.director = self

        yield net_test.report.open()

        yield net_test.initializeInputProcessor()
        try:
            self.activeNetTests.append(net_test)
            self.measurementManager.schedule(net_test.generateMeasurements())

            yield net_test.done
            yield report.close()
        finally:
            self.netTestDone(net_test)

    def startSniffing(self):
        """ Start sniffing with Scapy. Exits if required privileges (root) are not
        available.
        """
        from ooni.utils.txscapy import ScapyFactory, ScapySniffer
        config.scapyFactory = ScapyFactory(config.advanced.interface)

        if os.path.exists(config.reports.pcap):
            log.msg("Report PCAP already exists with filename %s" % config.reports.pcap)
            log.msg("Renaming files with such name...")
            pushFilenameStack(config.reports.pcap)

        if self.sniffer:
            config.scapyFactory.unRegisterProtocol(self.sniffer)
        self.sniffer = ScapySniffer(config.reports.pcap)
        config.scapyFactory.registerProtocol(self.sniffer)
        log.msg("Starting packet capture to: %s" % config.reports.pcap)

    @defer.inlineCallbacks
    def getTorState(self):
        connection = TCP4ClientEndpoint(reactor, '127.0.0.1',
                config.tor.control_port)
        config.tor_state = yield build_tor_connection(connection)


    def startTor(self):
        """ Starts Tor
        Launches a Tor with :param: socks_port :param: control_port
        :param: tor_binary set in ooniprobe.conf
        """
        log.msg("Starting Tor...")
        @defer.inlineCallbacks
        def state_complete(state):
            config.tor_state = state
            log.msg("Successfully bootstrapped Tor")
            log.debug("We now have the following circuits: ")
            for circuit in state.circuits.values():
                log.debug(" * %s" % circuit)

            socks_port = yield state.protocol.get_conf("SocksPort")
            control_port = yield state.protocol.get_conf("ControlPort")

            config.tor.socks_port = int(socks_port.values()[0])
            config.tor.control_port = int(control_port.values()[0])

        def setup_failed(failure):
            log.exception(failure)
            raise errors.UnableToStartTor

        def setup_complete(proto):
            """
            Called when we read from stdout that Tor has reached 100%.
            """
            log.debug("Building a TorState")
            config.tor.protocol = proto
            state = TorState(proto.tor_protocol)
            state.post_bootstrap.addCallback(state_complete)
            state.post_bootstrap.addErrback(setup_failed)
            return state.post_bootstrap

        def updates(prog, tag, summary):
            log.msg("%d%%: %s" % (prog, summary))

        tor_config = TorConfig()
        if config.tor.control_port:
            tor_config.ControlPort = config.tor.control_port

        if config.tor.socks_port:
            tor_config.SocksPort = config.tor.socks_port

        if config.tor.data_dir:
            data_dir = os.path.expanduser(config.tor.data_dir)

            if not os.path.exists(data_dir):
                log.msg("%s does not exist. Creating it." % data_dir)
                os.makedirs(data_dir)
            tor_config.DataDirectory = data_dir

        if config.tor.bridges:
            tor_config.UseBridges = 1
            if config.advanced.obfsproxy_binary:
                tor_config.ClientTransportPlugin = \
                        'obfs2,obfs3 exec %s managed' % \
                        config.advanced.obfsproxy_binary
            bridges = []
            with open(config.tor.bridges) as f:
                for bridge in f:
                    if 'obfs' in bridge:
                        if config.advanced.obfsproxy_binary:
                            bridges.append(bridge.strip())
                    else:
                        bridges.append(bridge.strip())
            tor_config.Bridge = bridges

        if config.tor.torrc:
            for i in config.tor.torrc.keys():
                setattr(tor_config, i, config.tor.torrc[i])

        tor_config.save()

        if not hasattr(tor_config,'ControlPort'):
            control_port = int(randomFreePort())
            tor_config.ControlPort = control_port
            config.tor.control_port = control_port

        if not hasattr(tor_config,'SocksPort'):
            socks_port = int(randomFreePort())
            tor_config.SocksPort = socks_port
            config.tor.socks_port = socks_port

        tor_config.save()
        log.debug("Setting control port as %s" % tor_config.ControlPort)
        log.debug("Setting SOCKS port as %s" % tor_config.SocksPort)

        if config.advanced.tor_binary:
            d = launch_tor(tor_config, reactor,
                           tor_binary=config.advanced.tor_binary,
                           progress_updates=updates)
        else:
            d = launch_tor(tor_config, reactor,
                           progress_updates=updates)
        d.addCallback(setup_complete)
        d.addErrback(setup_failed)
        return d

########NEW FILE########
__FILENAME__ = errors
from twisted.internet.defer import CancelledError
from twisted.internet.defer import TimeoutError as DeferTimeoutError
from twisted.web._newclient import ResponseNeverReceived

from twisted.internet.error import ConnectionRefusedError, TCPTimedOutError
from twisted.internet.error import DNSLookupError, ConnectError, ConnectionLost
from twisted.internet.error import TimeoutError as GenericTimeoutError

from txsocksx.errors import SOCKSError
from txsocksx.errors import MethodsNotAcceptedError, AddressNotSupported
from txsocksx.errors import ConnectionError, NetworkUnreachable
from txsocksx.errors import ConnectionLostEarly, ConnectionNotAllowed
from txsocksx.errors import NoAcceptableMethods, ServerFailure
from txsocksx.errors import HostUnreachable, ConnectionRefused
from txsocksx.errors import TTLExpired, CommandNotSupported

from socket import gaierror
def handleAllFailures(failure):
    """
    Here we make sure to trap all the failures that are supported by the
    failureToString function and we return the the string that represents the
    failure.
    """
    failure.trap(ConnectionRefusedError, gaierror, DNSLookupError,
            TCPTimedOutError, ResponseNeverReceived, DeferTimeoutError,
            GenericTimeoutError,
            SOCKSError, MethodsNotAcceptedError, AddressNotSupported,
            ConnectionError, NetworkUnreachable, ConnectionLostEarly,
            ConnectionNotAllowed, NoAcceptableMethods, ServerFailure,
            HostUnreachable, ConnectionRefused, TTLExpired, CommandNotSupported,
            ConnectError, ConnectionLost, CancelledError)

    return failureToString(failure)

def failureToString(failure):
    """
    Given a failure instance return a string representing the kind of error
    that occurred.

    Args:

        failure: a :class:twisted.internet.error instance

    Returns:

        A string representing the HTTP response error message.
    """
    from ooni.utils import log

    string = None
    if isinstance(failure.value, ConnectionRefusedError):
        log.err("Connection refused.")
        string = 'connection_refused_error'

    elif isinstance(failure.value, ConnectionLost):
        log.err("Connection lost.")
        string = 'connection_lost_error'

    elif isinstance(failure.value, ConnectError):
        log.err("Connect error.")
        string = 'connect_error'

    elif isinstance(failure.value, gaierror):
        log.err("Address family for hostname not supported")
        string = 'address_family_not_supported_error'

    elif isinstance(failure.value, DNSLookupError):
        log.err("DNS lookup failure")
        string = 'dns_lookup_error'

    elif isinstance(failure.value, TCPTimedOutError):
        log.err("TCP Timed Out Error")
        string = 'tcp_timed_out_error'

    elif isinstance(failure.value, ResponseNeverReceived):
        log.err("Response Never Received")
        string = 'response_never_received'

    elif isinstance(failure.value, DeferTimeoutError):
        log.err("Deferred Timeout Error")
        string = 'deferred_timeout_error'

    elif isinstance(failure.value, GenericTimeoutError):
        log.err("Time Out Error")
        string = 'generic_timeout_error'

    elif isinstance(failure.value, ServerFailure):
        log.err("SOCKS error: ServerFailure")
        string = 'socks_server_failure'

    elif isinstance(failure.value, ConnectionNotAllowed):
        log.err("SOCKS error: ConnectionNotAllowed")
        string = 'socks_connection_not_allowed'

    elif isinstance(failure.value, NetworkUnreachable):
        log.err("SOCKS error: NetworkUnreachable")
        string = 'socks_network_unreachable'

    elif isinstance(failure.value, HostUnreachable):
        log.err("SOCKS error: HostUnreachable")
        string = 'socks_host_unreachable'

    elif isinstance(failure.value, ConnectionRefused):
        log.err("SOCKS error: ConnectionRefused")
        string = 'socks_connection_refused'

    elif isinstance(failure.value, TTLExpired):
        log.err("SOCKS error: TTLExpired")
        string = 'socks_ttl_expired'

    elif isinstance(failure.value, CommandNotSupported):
        log.err("SOCKS error: CommandNotSupported")
        string = 'socks_command_not_supported'

    elif isinstance(failure.value, AddressNotSupported):
        log.err("SOCKS error: AddressNotSupported")
        string = 'socks_address_not_supported'

    elif isinstance(failure.value, SOCKSError):
        log.err("Generic SOCKS error")
        string = 'socks_error'
    
    elif isinstance(failure.value, CancelledError):
        log.err("Task timed out")
        string = 'task_timed_out'

    else:
        log.err("Unknown failure type: %s" % type(failure.value))
        string = 'unknown_failure %s' % str(failure.value)

    return string

class DirectorException(Exception):
    pass

class UnableToStartTor(DirectorException):
    pass

class InvalidOONIBCollectorAddress(Exception):
    pass

class InvalidOONIBBouncerAddress(Exception):
    pass

class AllReportersFailed(Exception):
    pass

class GeoIPDataFilesNotFound(Exception):
    pass

class ReportNotCreated(Exception):
    pass

class ReportAlreadyClosed(Exception):
    pass

class TorStateNotFound(Exception):
    pass

class TorControlPortNotFound(Exception):
    pass

class ReportNotCreated(Exception):
    pass

class InsufficientPrivileges(Exception):
    pass

class ProbeIPUnknown(Exception):
    pass

class GeoIPDataFilesNotFound(Exception):
    pass

class NoMoreReporters(Exception):
    pass

class TorNotRunning(Exception):
    pass

class OONIBError(Exception):
    pass

class OONIBReportError(OONIBError):
    pass

class OONIBReportUpdateError(OONIBReportError):
    pass

class OONIBReportCreationError(OONIBReportError):
    pass

class OONIBTestDetailsLookupError(OONIBReportError):
    pass

class UnableToLoadDeckInput(Exception):
    pass

class CouldNotFindTestHelper(Exception):
    pass

class CouldNotFindTestCollector(Exception):
    pass

class NetTestNotFound(Exception):
    pass

class MissingRequiredOption(Exception):
    pass

class FailureToLoadNetTest(Exception):
    pass

class NoPostProcessor(Exception):
    pass

class InvalidOption(Exception):
    pass

class TaskTimedOut(Exception):
    pass

class InvalidInputFile(Exception):
    pass

def get_error(error_key):
    if error_key == 'test-helpers-key-missing':
        return CouldNotFindTestHelper
    else:
        return OONIBError

########NEW FILE########
__FILENAME__ = geoip
import re
import os
import random

from twisted.web import client, http_headers
client._HTTP11ClientFactory.noisy = False

from twisted.internet import reactor, defer, protocol

from ooni.utils import log, net, checkForRoot
from ooni import errors

try:
    from pygeoip import GeoIP
except ImportError:
    try:
        import GeoIP as CGeoIP
        def GeoIP(database_path, *args, **kwargs):
            return CGeoIP.open(database_path, CGeoIP.GEOIP_STANDARD)
    except ImportError:
        log.err("Unable to import pygeoip. We will not be able to run geo IP related measurements")

class GeoIPDataFilesNotFound(Exception):
    pass

def IPToLocation(ipaddr):
    from ooni.settings import config

    city_file = os.path.join(config.advanced.geoip_data_dir, 'GeoLiteCity.dat')
    country_file = os.path.join(config.advanced.geoip_data_dir, 'GeoIP.dat')
    asn_file = os.path.join(config.advanced.geoip_data_dir, 'GeoIPASNum.dat')

    location = {'city': None, 'countrycode': 'ZZ', 'asn': 'AS0'}
    
    try:
        country_dat = GeoIP(country_file)
        location['countrycode'] = country_dat.country_code_by_addr(ipaddr)
        if not location['countrycode']:
            location['countrycode'] = 'ZZ'
    except IOError:
        log.err("Could not find GeoIP data file. Go into %s "
                "and make sure GeoIP.dat is present or change the location "
                "in the config file" % config.advanced.geoip_data_dir)
    try:
        city_dat = GeoIP(city_file)
        location['city'] = city_dat.record_by_addr(ipaddr)['city']
    except:
         log.err("Could not find the city your IP is from. "
                "Download the GeoLiteCity.dat file into the geoip_data_dir"
                " or install geoip-database-contrib.")
    try:
        asn_dat = GeoIP(asn_file)
        location['asn'] = asn_dat.org_by_addr(ipaddr).split(' ')[0]
    except:
        log.err("Could not find the ASN for your IP. "
                "Download the GeoIPASNum.dat file into the geoip_data_dir"
                " or install geoip-database-contrib.")
    
    return location

class HTTPGeoIPLookupper(object):
    url = None

    _agent = client.Agent

    def __init__(self):
        self.agent = self._agent(reactor)

    def _response(self, response):
        from ooni.utils.net import BodyReceiver

        content_length = response.headers.getRawHeaders('content-length')

        finished = defer.Deferred()
        response.deliverBody(BodyReceiver(finished, content_length))
        finished.addCallback(self.parseResponse)
        return finished

    def parseResponse(self, response_body):
        """
        Override this with the logic for parsing the response.

        Should return the IP address of the probe.
        """
        pass

    def failed(self, failure):
        log.err("Failed to lookup via %s" % self.url)
        log.exception(failure)
        return failure

    def lookup(self):
        from ooni.utils.net import userAgents

        headers = {}
        headers['User-Agent'] = [random.choice(userAgents)]

        d = self.agent.request("GET", self.url, http_headers.Headers(headers))
        d.addCallback(self._response)
        d.addErrback(self.failed)
        return d

class UbuntuGeoIP(HTTPGeoIPLookupper):
    url = "http://geoip.ubuntu.com/lookup"

    def parseResponse(self, response_body):
        m = re.match(".*<Ip>(.*)</Ip>.*", response_body)
        probe_ip = m.group(1)
        return probe_ip

class TorProjectGeoIP(HTTPGeoIPLookupper):
    url = "https://check.torproject.org/"

    def parseResponse(self, response_body):
        regexp = "Your IP address appears to be:  <strong>((\d+\.)+(\d+))"
        probe_ip = re.search(regexp, response_body).group(1)
        return probe_ip

class ProbeIP(object):
    strategy = None
    address = None

    def __init__(self):
        self.geoIPServices = {
            'ubuntu': UbuntuGeoIP,
            'torproject': TorProjectGeoIP
        }
        self.geodata = {
            'asn': 'AS0',
            'city': None,
            'countrycode': 'ZZ',
            'ip': '127.0.0.1'
        }
    
    def resolveGeodata(self):
        from ooni.settings import config

        self.geodata = IPToLocation(self.address)
        self.geodata['ip'] = self.address
        if not config.privacy.includeasn:
            self.geodata['asn'] = 'AS0'
        if not config.privacy.includecity:
            self.geodata['city'] = None
        if not config.privacy.includecountry:
            self.geodata['countrycode'] = 'ZZ'
        if not config.privacy.includeip:
            self.geodata['ip'] = '127.0.0.1'

    @defer.inlineCallbacks
    def lookup(self):
        try:
            yield self.askTor()
            log.msg("Found your IP via Tor %s" % self.address)
            self.resolveGeodata()
            defer.returnValue(self.address)
        except errors.TorStateNotFound:
            log.debug("Tor is not running. Skipping IP lookup via Tor.")
        except Exception:
            log.msg("Unable to lookup the probe IP via Tor.")

        try:
            yield self.askTraceroute()
            log.msg("Found your IP via Traceroute %s" % self.address)
            self.resolveGeodata()
            defer.returnValue(self.address)
        except errors.InsufficientPrivileges:
            log.debug("Cannot determine the probe IP address with a traceroute, becase of insufficient priviledges")
        except:
            log.msg("Unable to lookup the probe IP via traceroute")

        try:
            yield self.askGeoIPService()
            log.msg("Found your IP via a GeoIP service: %s" % self.address)
            self.resolveGeodata()
            defer.returnValue(self.address)
        except Exception, e:
            log.msg("Unable to lookup the probe IP via GeoIPService")
            raise e

    @defer.inlineCallbacks
    def askGeoIPService(self):
        # Shuffle the order in which we test the geoip services.
        services = self.geoIPServices.items()
        random.shuffle(services)
        for service_name, service in services:
            s = service()
            log.msg("Looking up your IP address via %s" % service_name)
            try:
                self.address = yield s.lookup()
                self.strategy = 'geo_ip_service-' + service_name
                break
            except Exception, e:
                log.msg("Failed to lookup your IP via %s" % service_name)

        if not self.address:
            raise errors.ProbeIPUnknown

    def askTraceroute(self):
        """
        Perform a UDP traceroute to determine the probes IP address.
        """
        checkForRoot()
        raise NotImplemented

    def askTor(self):
        """
        Obtain the probes IP address by asking the Tor Control port via GET INFO
        address.

        XXX this lookup method is currently broken when there are cached descriptors or consensus documents
        see: https://trac.torproject.org/projects/tor/ticket/8214
        """
        from ooni.settings import config

        if config.tor_state:
            d = config.tor_state.protocol.get_info("address")
            @d.addCallback
            def cb(result):
                self.strategy = 'tor_get_info_address'
                self.address = result.values()[0]
            return d
        else:
            raise errors.TorStateNotFound

########NEW FILE########
__FILENAME__ = daphn3
import sys
import yaml

from twisted.internet import protocol, defer
from twisted.internet.error import ConnectionDone

from ooni.utils import log

def read_pcap(filename):
    """
    @param filename: Filesystem path to the pcap.

    Returns:
      [{"client": "\x17\x52\x15"}, {"server": "\x17\x15\x13"}]
    """
    from scapy.all import IP, Raw, rdpcap

    packets = rdpcap(filename)

    checking_first_packet = True
    client_ip_addr = None
    server_ip_addr = None

    ssl_packets = []
    messages = []

    """
    pcap assumptions:

    pcap only contains packets exchanged between a Tor client and a Tor
    server.  (This assumption makes sure that there are only two IP addresses
    in the pcap file)

    The first packet of the pcap is sent from the client to the server. (This
    assumption is used to get the IP address of the client.)

    All captured packets are TLS packets: that is TCP session
    establishment/teardown packets should be filtered out (no SYN/SYN+ACK)
    """

    """
    Minimally validate the pcap and also find out what's the client
    and server IP addresses.
    """
    for packet in packets:
        if checking_first_packet:
            client_ip_addr = packet[IP].src
            checking_first_packet = False
        else:
            if packet[IP].src != client_ip_addr:
                server_ip_addr = packet[IP].src

        try:
            if (packet[Raw]):
                ssl_packets.append(packet)
        except IndexError:
            pass

    """Form our list."""
    for packet in ssl_packets:
        if packet[IP].src == client_ip_addr:
            messages.append({"client": str(packet[Raw])})
        elif packet[IP].src == server_ip_addr:
            messages.append({"server": str(packet[Raw])})
        else:
            raise("Detected third IP address! pcap is corrupted.")

    return messages

def read_yaml(filename):
    f = open(filename)
    obj = yaml.safe_load(f)
    f.close()
    return obj

class NoInputSpecified(Exception):
    pass

class StepError(Exception):
    pass

def daphn3MutateString(string, i):
    """
    Takes a string and mutates the ith bytes of it.
    """
    mutated = ""
    for y in range(len(string)):
        if y == i:
            mutated += chr(ord(string[i]) + 1)
        else:
            mutated += string[y]
    return mutated

def daphn3Mutate(steps, step_idx, mutation_idx):
    """
    Take a set of steps and a step index and mutates the step of that
    index at the mutation_idx'th byte.
    """
    mutated_steps = []
    for idx, step in enumerate(steps):
        if idx == step_idx:
            step_string = step.values()[0]
            step_key = step.keys()[0]
            mutated_string = daphn3MutateString(step_string, 
                    mutation_idx)
            mutated_steps.append({step_key: mutated_string})
        else:
            mutated_steps.append(step)
    return mutated_steps

class Daphn3Protocol(protocol.Protocol):
    steps = None
    role = "client"
    report = None
    # We use this index to keep track of where we are in the state machine
    current_step = 0
    current_data_received = 0

    # We use this to keep track of the mutated steps
    mutated_steps = None
    d = defer.Deferred()

    def _current_step_role(self):
        return self.steps[self.current_step].keys()[0]

    def _current_step_data(self):
        step_idx, mutation_idx = self.factory.mutation
        log.debug("Mutating %s %s" % (step_idx, mutation_idx))
        mutated_step = daphn3Mutate(self.steps, 
                step_idx, mutation_idx)
        log.debug("Mutated packet into %s" % mutated_step)
        return mutated_step[self.current_step].values()[0]

    def sendPayload(self):
        self.debug("Sending payload")
        current_step_role = self._current_step_role()
        current_step_data = self._current_step_data()
        if current_step_role == self.role:
            print "In a state to do shit %s" % current_step_data
            self.transport.write(current_step_data)
            self.nextStep()
        else:
            print "Not in a state to do anything"

    def connectionMade(self):
        print "Got connection"

    def debug(self, msg):
        log.debug("Current step %s" % self.current_step)
        log.debug("Current data received %s" % self.current_data_received)
        log.debug("Current role %s" % self.role)
        log.debug("Current steps %s" % self.steps)
        log.debug("Current step data %s" % self._current_step_data())

    def nextStep(self):
        """
        XXX this method is overwritten individually by client and server transport.
        There is probably a smarter way to do this and refactor the common
        code into one place, but for the moment like this is good.
        """
        pass

    def dataReceived(self, data):
        current_step_role = self.steps[self.current_step].keys()[0]
        log.debug("Current step role %s" % current_step_role)
        if current_step_role == self.role:
            log.debug("Got a state error!")
            raise StepError("I should not have gotten data, while I did, \
                    perhaps there is something wrong with the state machine?")

        self.current_data_received += len(data)
        expected_data_in_this_state = len(self.steps[self.current_step].values()[0])

        log.debug("Current data received %s" %  self.current_data_received)
        if self.current_data_received >= expected_data_in_this_state:
            self.nextStep()

    def nextMutation(self):
        log.debug("Moving onto next mutation")
        # [step_idx, mutation_idx]
        c_step_idx, c_mutation_idx = self.factory.mutation
        log.debug("[%s]: c_step_idx: %s | c_mutation_idx: %s" % (self.role,
            c_step_idx, c_mutation_idx))

        if c_step_idx >= (len(self.steps) - 1):
            log.err("No censorship fingerprint bisected.")
            log.err("Givinig up.")
            self.transport.loseConnection()
            return

        # This means we have mutated all bytes in the step
        # we should proceed to mutating the next step.
        log.debug("steps: %s | %s" % (self.steps, self.steps[c_step_idx]))
        if c_mutation_idx >= (len(self.steps[c_step_idx].values()[0]) - 1):
            log.debug("Finished mutating step")
            # increase step
            self.factory.mutation[0] += 1
            # reset mutation idx
            self.factory.mutation[1] = 0
        else:
            log.debug("Mutating next byte in step")
            # increase mutation index
            self.factory.mutation[1] += 1

    def connectionLost(self, reason):
        self.debug("--- Lost the connection ---")
        self.nextMutation()


########NEW FILE########
__FILENAME__ = domclass
"""
how this works
--------------

This classifier uses the DOM structure of a website to determine how similar
the two sites are.
The procedure we use is the following:
   * First we parse all the DOM tree of the web page and we build a list of
     TAG parent child relationships (ex. <html><a><b></b></a><c></c></html> =>
     (html, a), (a, b), (html, c)).

   * We then use this information to build a matrix (M) where m[i][j] = P(of
     transitioning from tag[i] to tag[j]). If tag[i] does not exists P() = 0.
     Note: M is a square matrix that is number_of_tags wide.

   * We then calculate the eigenvectors (v_i) and eigenvalues (e) of M.

   * The corelation between page A and B is given via this formula:
     correlation = dot_product(e_A, e_B), where e_A and e_B are
     resepectively the eigenvalues for the probability matrix A and the
     probability matrix B.
"""

import yaml
import numpy
import time

from ooni import log

# All HTML4 tags
# XXX add link to W3C page where these came from
alltags = ['A', 'ABBR', 'ACRONYM', 'ADDRESS', 'APPLET', 'AREA', 'B', 'BASE',
           'BASEFONT', 'BD', 'BIG', 'BLOCKQUOTE', 'BODY', 'BR', 'BUTTON', 'CAPTION',
           'CENTER', 'CITE', 'CODE', 'COL', 'COLGROUP', 'DD', 'DEL', 'DFN', 'DIR', 'DIV',
           'DL', 'DT', 'E M', 'FIELDSET', 'FONT', 'FORM', 'FRAME', 'FRAMESET', 'H1', 'H2',
           'H3', 'H4', 'H5', 'H6', 'HEAD', 'HR', 'HTML', 'I', 'IFRAME ', 'IMG',
           'INPUT', 'INS', 'ISINDEX', 'KBD', 'LABEL', 'LEGEND', 'LI', 'LINK', 'MAP',
           'MENU', 'META', 'NOFRAMES', 'NOSCRIPT', 'OBJECT', 'OL', 'OPTGROUP', 'OPTION',
           'P', 'PARAM', 'PRE', 'Q', 'S', 'SAMP', 'SCRIPT', 'SELECT', 'SMALL', 'SPAN',
           'STRIKE', 'STRONG', 'STYLE', 'SUB', 'SUP', 'TABLE', 'TBODY', 'TD',
           'TEXTAREA', 'TFOOT', 'TH', 'THEAD', 'TITLE', 'TR', 'TT', 'U', 'UL', 'VAR']

# Reduced subset of only the most common tags
commontags = ['A', 'B', 'BLOCKQUOTE', 'BODY', 'BR', 'BUTTON', 'CAPTION',
           'CENTER', 'CITE', 'CODE', 'COL', 'DD', 'DIV',
           'DL', 'DT', 'EM', 'FIELDSET', 'FONT', 'FORM', 'FRAME', 'FRAMESET', 'H1', 'H2',
           'H3', 'H4', 'H5', 'H6', 'HEAD', 'HR', 'HTML', 'IFRAME ', 'IMG',
           'INPUT', 'INS', 'LABEL', 'LEGEND', 'LI', 'LINK', 'MAP',
           'MENU', 'META', 'NOFRAMES', 'NOSCRIPT', 'OBJECT', 'OL', 'OPTION',
           'P', 'PRE', 'SCRIPT', 'SELECT', 'SMALL', 'SPAN',
           'STRIKE', 'STRONG', 'STYLE', 'SUB', 'SUP', 'TABLE', 'TBODY', 'TD',
           'TEXTAREA', 'TFOOT', 'TH', 'THEAD', 'TITLE', 'TR', 'TT', 'U', 'UL']

# The tags we are intested in using for our analysis
thetags = ['A', 'DIV', 'FRAME', 'H1', 'H2',
           'H3', 'H4', 'IFRAME ', 'INPUT',
           'LABEL','LI', 'P', 'SCRIPT', 'SPAN',
           'STYLE', 'TR']

def compute_probability_matrix(dataset):
    """
    Compute the probability matrix based on the input dataset.

    :dataset: an array of pairs representing the parent child relationships.
    """
    import itertools
    ret = {}
    matrix = numpy.zeros((len(thetags) + 1, len(thetags) + 1))

    for data in dataset:
        x = data[0].upper()
        y = data[1].upper()
        try:
            x = thetags.index(x)
        except:
            x = len(thetags)

        try:
            y = thetags.index(y)
        except:
            y = len(thetags)

        matrix[x,y] += 1

    for x in xrange(len(thetags) + 1):
        possibilities = 0
        for y in matrix[x]:
            possibilities += y

        for i in xrange(len(matrix[x])):
            if possibilities != 0:
                matrix[x][i] = matrix[x][i]/possibilities

    return matrix

def compute_eigenvalues(matrix):
    """
    Returns the eigenvalues of the supplied square matrix.

    :matrix: must be a square matrix and diagonalizable.
    """
    return numpy.linalg.eigvals(matrix)

def readDOM(content=None, filename=None, debug=False):
    """
    Parses the DOM of the HTML page and returns an array of parent, child
    pairs.

    :content: the content of the HTML page to be read.

    :filename: the filename to be read from for getting the content of the
               page.
    """
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        log.err("BeautifulSoup is not installed. This test canno run")
        raise Exception

    if filename:
        f = open(filename)
        content = ''.join(f.readlines())
        f.close()

    if debug:
        start = time.time()
        print "Running BeautifulSoup on content"
    dom = BeautifulSoup(content)
    if debug:
        print "done in %s" % (time.time() - start)

    if debug:
        start = time.time()
        print "Creating couples matrix"
    couples = []
    for x in dom.findAll():
        couples.append((str(x.parent.name), str(x.name)))
    if debug:
        print "done in %s" % (time.time() - start)

    return couples

def compute_eigenvalues_from_DOM(*arg,**kw):
    dom = readDOM(*arg, **kw)
    probability_matrix = compute_probability_matrix(dom)
    eigenvalues = compute_eigenvalues(probability_matrix)
    return eigenvalues

def compute_correlation(matrix_a, matrix_b):
    correlation = numpy.vdot(matrix_a, matrix_b)
    correlation /= numpy.linalg.norm(matrix_a)*numpy.linalg.norm(matrix_b)
    correlation = (correlation + 1)/2
    return correlation

def benchmark():
    """
    Running some very basic benchmarks on this input data:

    Data files:
    683 filea.txt
    678 fileb.txt

    diff file* | wc -l
    283

    We get such results:

    Read file B
    Running BeautifulSoup on content
    done in 0.768223047256
    Creating couples matrix
    done in 0.023903131485
    --------
    total done in 0.796372890472
    Read file A
    Running BeautifulSoup on content
    done in 0.752885818481
    Creating couples matrix
    done in 0.0163578987122
    --------
    total done in 0.770951986313
    Computing prob matrix
    done in 0.0475239753723
    Computing eigenvalues
    done in 0.00161099433899
    Computing prob matrix B
    done in 0.0408289432526
    Computing eigen B
    done in 0.000268936157227
    Computing correlation
    done in 0.00016713142395
    Corelation: 0.999999079331

    What this means is that the bottleneck is not in the maths, but is rather
    in the computation of the DOM tree matrix.

    XXX We should focus on optimizing the parsing of the HTML (this depends on
    beautiful soup). Perhaps we can find and alternative to it that is
    sufficient for us.
    """
    start = time.time()
    print "Read file B"
    site_a = readDOM(filename='filea.txt', debug=True)
    print "--------"
    print "total done in %s" % (time.time() - start)

    start = time.time()
    print "Read file A"
    site_b = readDOM(filename='fileb.txt', debug=True)
    print "--------"
    print "total done in %s" % (time.time() - start)

    a = {}
    b = {}

    start = time.time()
    print "Computing prob matrix"
    a['matrix'] = compute_probability_matrix(site_a)
    print "done in %s" % (time.time() - start)
    start = time.time()

    print "Computing eigenvalues"
    a['eigen'] = compute_eigenvalues(a['matrix'])
    print "done in %s" % (time.time() - start)
    start = time.time()

    start = time.time()
    print "Computing prob matrix B"
    b['matrix'] = compute_probability_matrix(site_b)
    print "done in %s" % (time.time() - start)

    start = time.time()
    print "Computing eigen B"
    b['eigen'] = compute_eigenvalues(b['matrix'])
    print "done in %s" % (time.time() - start)

    start = time.time()
    print "Computing correlation"
    correlation = compute_correlation(a['eigen'], b['eigen'])
    print "done in %s" % (time.time() - start)

    print "Corelation: %s" % correlation

#benchmark()

########NEW FILE########
__FILENAME__ = managers
import itertools

from twisted.internet import defer
from ooni.utils import log
from ooni.settings import config

def makeIterable(item):
    """
    Takes as argument or an iterable and if it's not an iterable object then it
    will return a listiterator.
    """
    try:
        iterable = iter(item)
    except TypeError:
        iterable = iter([item])
    return iterable

class TaskManager(object):
    retries = 2
    concurrency = 10

    def __init__(self):
        self._tasks = iter(())
        self._active_tasks = []
        self.failures = 0

    def _failed(self, failure, task):
        """
        The has failed to complete, we append it to the end of the task chain
        to be re-run once all the currently scheduled tasks have run.
        """
        log.err("Task %s has failed %s times" % (task, task.failures))
        if config.advanced.debug:
            log.exception(failure)

        self._active_tasks.remove(task)
        self.failures = self.failures + 1

        if task.failures <= self.retries:
            log.debug("Rescheduling...")
            self._tasks = itertools.chain(makeIterable(task), self._tasks)

        else:
            # This fires the errback when the task is done but has failed.
            log.err('Permanent failure for %s' % task)
            task.done.errback(failure)

        self._fillSlots()

        self.failed(failure, task)

    def _fillSlots(self):
        """
        Called on test completion and schedules measurements to be run for the
        available slots.
        """
        for _ in range(self.availableSlots):
            try:
                task = self._tasks.next()
                self._run(task)
            except StopIteration:
                break
            except ValueError as exc:
                # XXX this is a workaround the race condition that leads the
                # _tasks generator to throw the exception
                # ValueError: generator already called.
                continue

    def _run(self, task):
        """
        This gets called to add a task to the list of currently active and
        running tasks.
        """
        self._active_tasks.append(task)

        d = task.start()
        d.addCallback(self._succeeded, task)
        d.addErrback(self._failed, task)

    def _succeeded(self, result, task):
        """
        We have successfully completed a measurement.
        """
        self._active_tasks.remove(task)

        # Fires the done deferred when the task has completed
        task.done.callback(result)

        self._fillSlots()

        self.succeeded(result, task)

    @property
    def failedMeasurements(self):
        return self.failures

    @property
    def availableSlots(self):
        """
        Returns the number of available slots for running tests.
        """
        return self.concurrency - len(self._active_tasks)

    def schedule(self, task_or_task_iterator):
        """
        Takes as argument a single task or a task iterable and appends it to the task
        generator queue.
        """
        log.debug("Starting this task %s" % repr(task_or_task_iterator))

        iterable = makeIterable(task_or_task_iterator)

        self._tasks = itertools.chain(self._tasks, iterable)
        self._fillSlots()

    def start(self):
        """
        This is called to start the task manager.
        """
        self.failures = 0

        self._fillSlots()

    def failed(self, failure, task):
        """
        This hoook is called every time a task has failed.

        The default failure handling logic is to reschedule the task up until
        we reach the maximum number of retries.
        """
        raise NotImplemented

    def succeeded(self, result, task):
        """
        This hook is called every time a task has been successfully executed.
        """
        raise NotImplemented

class LinkedTaskManager(TaskManager):
    def __init__(self):
        super(LinkedTaskManager, self).__init__()
        self.child = None
        self.parent = None

    @property
    def availableSlots(self):
        mySlots = self.concurrency - len(self._active_tasks)
        if self.child:
            s = self.child.availableSlots
            return min(s, mySlots)
        return mySlots

    def _succeeded(self, result, task):
        super(LinkedTaskManager, self)._succeeded(result, task)
        if self.parent:
            self.parent._fillSlots()

    def _failed(self, result, task):
        super(LinkedTaskManager, self)._failed(result, task)
        if self.parent:
            self.parent._fillSlots()

class MeasurementManager(LinkedTaskManager):
    """
    This is the Measurement Tracker. In here we keep track of active measurements
    and issue new measurements once the active ones have been completed.

    MeasurementTracker does not keep track of the typology of measurements that
    it is running. It just considers a measurement something that has an input
    and a method to be called.

    NetTest on the contrary is aware of the typology of measurements that it is
    dispatching as they are logically grouped by test file.
    """
    def __init__(self):
        if config.advanced.measurement_retries:
            self.retries = config.advanced.measurement_retries
        if config.advanced.measurement_concurrency:
            self.concurrency = config.advanced.measurement_concurrency
        super(MeasurementManager, self).__init__()

    def succeeded(self, result, measurement):
        log.debug("Successfully performed measurement %s" % measurement)
        log.debug("%s" % result)

    def failed(self, failure, measurement):
        pass

class ReportEntryManager(LinkedTaskManager):
    def __init__(self):
        if config.advanced.reporting_retries:
            self.retries = config.advanced.reporting_retries
        if config.advanced.reporting_concurrency:
            self.concurrency = config.advanced.reporting_concurrency
        super(ReportEntryManager, self).__init__()

    def succeeded(self, result, task):
        log.debug("Successfully performed report %s" % task)
        log.debug(result)

    def failed(self, failure, task):
        pass


########NEW FILE########
__FILENAME__ = nettest
import os
import re
import time
from hashlib import sha256

from twisted.internet import defer, reactor
from twisted.trial.runner import filenameToModule
from twisted.python import usage, reflect

from ooni import geoip
from ooni.tasks import Measurement
from ooni.utils import log, checkForRoot
from ooni import otime
from ooni.settings import config

from ooni import errors as e

from inspect import getmembers
from StringIO import StringIO

class NoTestCasesFound(Exception):
    pass

def get_test_methods(item, method_prefix="test_"):
    """
    Look for test_ methods in subclasses of NetTestCase
    """
    test_cases = []
    try:
        assert issubclass(item, NetTestCase)
        methods = reflect.prefixedMethodNames(item, method_prefix)
        test_methods = []
        for method in methods:
            test_methods.append(method_prefix + method)
        if test_methods:
            test_cases.append((item, test_methods))
    except (TypeError, AssertionError):
        pass
    return test_cases

def getTestClassFromFile(net_test_file):
    """
    Will return the first class that is an instance of NetTestCase.

    XXX this means that if inside of a test there are more than 1 test case
        then we will only run the first one.
    """
    module = filenameToModule(net_test_file)
    for __, item in getmembers(module):
        try:
            assert issubclass(item, NetTestCase)
            return item
        except (TypeError, AssertionError):
            pass

def getOption(opt_parameter, required_options, type='text'):
    """
    Arguments:
        usage_options: a list as should be the optParameters of an UsageOptions class.

        required_options: a list containing the strings of the options that are
            required.

        type: a string containing the type of the option.

    Returns:
        a dict containing
            {
                'description': the description of the option,
                'default': the default value of the option,
                'required': True|False if the option is required or not,
                'type': the type of the option ('text' or 'file')
            }
    """
    option_name, _, default, description = opt_parameter
    if option_name in required_options:
        required = True
    else:
        required = False

    return {'description': description,
        'value': default, 'required': required,
        'type': type
    }

def getArguments(test_class):
    arguments = {}
    if test_class.inputFile:
        option_name = test_class.inputFile[0]
        arguments[option_name] = getOption(test_class.inputFile,
                test_class.requiredOptions, type='file')
    try:
        list(test_class.usageOptions.optParameters)
    except AttributeError:
        return arguments

    for opt_parameter in test_class.usageOptions.optParameters:
        option_name = opt_parameter[0]
        opt_type="text"
        if opt_parameter[3].lower().startswith("file"):
            opt_type="file"
        arguments[option_name] = getOption(opt_parameter,
                test_class.requiredOptions, type=opt_type)

    return arguments

def test_class_name_to_name(test_class_name):
    return test_class_name.lower().replace(' ','_')

def getNetTestInformation(net_test_file):
    """
    Returns a dict containing:

    {
        'id': the test filename excluding the .py extension,
        'name': the full name of the test,
        'description': the description of the test,
        'version': version number of this test,
        'arguments': a dict containing as keys the supported arguments and as
            values the argument description.
    }
    """
    test_class = getTestClassFromFile(net_test_file)

    test_id = os.path.basename(net_test_file).replace('.py', '')
    information = {'id': test_id,
        'name': test_class.name,
        'description': test_class.description,
        'version': test_class.version,
        'arguments': getArguments(test_class),
        'path': net_test_file,
    }
    return information

class NetTestLoader(object):
    method_prefix = 'test'
    collector = None
    requiresTor = False

    def __init__(self, options, test_file=None, test_string=None):
        self.onionInputRegex = re.compile("(httpo://[a-z0-9]{16}\.onion)/input/([a-z0-9]{64})$")
        self.options = options
        self.testCases = []

        if test_file:
            self.loadNetTestFile(test_file)
        elif test_string:
            self.loadNetTestString(test_string)

    @property
    def requiredTestHelpers(self):
        required_test_helpers = []
        if not self.testCases:
            return required_test_helpers

        for test_class, test_methods in self.testCases:
            for option, name in test_class.requiredTestHelpers.items():
                required_test_helpers.append({
                    'name': name,
                    'option': option,
                    'test_class': test_class
                })
        return required_test_helpers

    @property
    def inputFiles(self):
        input_files = []
        if not self.testCases:
            return input_files

        for test_class, test_methods in self.testCases:
            if test_class.inputFile:
                key = test_class.inputFile[0]
                filename = test_class.localOptions[key]
                if not filename:
                    continue
                input_file = {
                    'key': key,
                    'test_class': test_class
                }
                m = self.onionInputRegex.match(filename)
                if m:
                    input_file['url'] = filename
                    input_file['address'] = m.group(1)
                    input_file['hash'] = m.group(2)
                else:
                    input_file['filename'] = filename
                    try:
                        with open(filename) as f:
                            h = sha256()
                            for l in f:
                                h.update(l)
                    except:
                        raise e.InvalidInputFile(filename)
                    input_file['hash'] = h.hexdigest()
                input_files.append(input_file)

        return input_files

    @property
    def testDetails(self):
        from ooni import __version__ as software_version

        input_file_hashes = []
        for input_file in self.inputFiles:
            input_file_hashes.append(input_file['hash'])

        test_details = {'start_time': time.time(),
            'probe_asn': config.probe_ip.geodata['asn'],
            'probe_cc': config.probe_ip.geodata['countrycode'],
            'probe_ip': config.probe_ip.geodata['ip'],
            'probe_city': config.probe_ip.geodata['city'],
            'test_name': self.testName,
            'test_version': self.testVersion,
            'software_name': 'ooniprobe',
            'software_version': software_version,
            'options': self.options,
            'input_hashes': input_file_hashes
        }
        return test_details


    def _parseNetTestOptions(self, klass):
        """
        Helper method to assemble the options into a single UsageOptions object
        """
        usage_options = klass.usageOptions

        if not hasattr(usage_options, 'optParameters'):
            usage_options.optParameters = []
        else:
            for parameter in usage_options.optParameters:
                if len(parameter) == 5:
                    parameter.pop()

        if klass.inputFile:
            usage_options.optParameters.append(klass.inputFile)

        if klass.baseParameters:
            for parameter in klass.baseParameters:
                usage_options.optParameters.append(parameter)

        if klass.baseFlags:
            if not hasattr(usage_options, 'optFlags'):
                usage_options.optFlags = []
            for flag in klass.baseFlags:
                usage_options.optFlags.append(flag)

        return usage_options

    @property
    def usageOptions(self):
        usage_options = None
        for test_class, test_method in self.testCases:
            if not usage_options:
                usage_options = self._parseNetTestOptions(test_class)
            else:
                assert usage_options == test_class.usageOptions
        return usage_options

    def loadNetTestString(self, net_test_string):
        """
        Load NetTest from a string.
        WARNING input to this function *MUST* be sanitized and *NEVER* take
        untrusted input.
        Failure to do so will result in code exec.

        net_test_string:

            a string that contains the net test to be run.
        """
        net_test_file_object = StringIO(net_test_string)

        ns = {}
        test_cases = []
        exec net_test_file_object.read() in ns
        for item in ns.itervalues():
            test_cases.extend(self._get_test_methods(item))

        if not test_cases:
            raise e.NoTestCasesFound

        self.setupTestCases(test_cases)

    def loadNetTestFile(self, net_test_file):
        """
        Load NetTest from a file.
        """
        test_cases = []
        module = filenameToModule(net_test_file)
        for __, item in getmembers(module):
            test_cases.extend(self._get_test_methods(item))

        if not test_cases:
            raise e.NoTestCasesFound

        self.setupTestCases(test_cases)

    def setupTestCases(self, test_cases):
        """
        Creates all the necessary test_cases (a list of tuples containing the
        NetTestCase (test_class, test_method))

        example:
            [(test_classA, test_method1),
            (test_classA, test_method2),
            (test_classA, test_method3),
            (test_classA, test_method4),
            (test_classA, test_method5),

            (test_classB, test_method1),
            (test_classB, test_method2)]

        Note: the inputs must be valid for test_classA and test_classB.

        net_test_file:
            is either a file path or a file like object that will be used to
            generate the test_cases.
        """
        test_class, _ = test_cases[0]
        self.testVersion = test_class.version
        self.testName = test_class_name_to_name(test_class.name)
        self.testCases = test_cases
        self.testClasses = set([])
        for test_class, test_method in self.testCases:
            self.testClasses.add(test_class)

    def checkOptions(self):
        """
        Call processTest and processOptions methods of each NetTestCase
        """
        for klass in self.testClasses:
            options = self.usageOptions()
            options.parseOptions(self.options)

            if options:
                klass.localOptions = options

            test_instance = klass()
            if test_instance.requiresRoot:
                checkForRoot()
            if test_instance.requiresTor:
                self.requiresTor = True
            test_instance.requirements()
            test_instance._checkRequiredOptions()
            test_instance._checkValidOptions()

    def _get_test_methods(self, item):
        """
        Look for test_ methods in subclasses of NetTestCase
        """
        test_cases = []
        try:
            assert issubclass(item, NetTestCase)
            methods = reflect.prefixedMethodNames(item, self.method_prefix)
            test_methods = []
            for method in methods:
                test_methods.append(self.method_prefix + method)
            if test_methods:
                test_cases.append((item, test_methods))
        except (TypeError, AssertionError):
            pass
        return test_cases

class NetTestState(object):
    def __init__(self, allTasksDone):
        """
        This keeps track of the state of a running NetTests case.

        Args:
            allTasksDone is a deferred that will get fired once all the NetTest
            cases have reached a final done state.
        """
        self.doneTasks = 0
        self.tasks = 0

        self.completedScheduling = False
        self.allTasksDone = allTasksDone

    def taskCreated(self):
        self.tasks += 1

    def checkAllTasksDone(self):
        log.debug("Checking all tasks for completion %s == %s" %
                  (self.doneTasks, self.tasks))
        if self.completedScheduling and \
                self.doneTasks == self.tasks:
            self.allTasksDone.callback(self.doneTasks)

    def taskDone(self):
        """
        This is called every time a task has finished running.
        """
        self.doneTasks += 1
        self.checkAllTasksDone()

    def allTasksScheduled(self):
        """
        This should be called once all the tasks that need to run have been
        scheduled.

        XXX this is ghetto.
        The reason for which we are calling allTasksDone inside of the
        allTasksScheduled method is called after all tasks are done, then we
        will run into a race condition. The race is that we don't end up
        checking that all the tasks are complete because no task is to be
        scheduled.
        """
        self.completedScheduling = True
        self.checkAllTasksDone()

class NetTest(object):
    director = None

    def __init__(self, net_test_loader, report):
        """
        net_test_loader:
             an instance of :class:ooni.nettest.NetTestLoader containing
             the test to be run.

        report:
            an instance of :class:ooni.reporter.Reporter
        """
        self.report = report
        self.testCases = net_test_loader.testCases
        self.testClasses = net_test_loader.testClasses
        self.testDetails = net_test_loader.testDetails

        self.summary = {}

        # This will fire when all the measurements have been completed and
        # all the reports are done. Done means that they have either completed
        # successfully or all the possible retries have been reached.
        self.done = defer.Deferred()
        self.done.addCallback(self.doneNetTest)

        self.state = NetTestState(self.done)

    def __str__(self):
        return ' '.join(tc.name for tc, _ in self.testCases)

    def doneNetTest(self, result):
        if not self.summary:
            return
        print "Summary for %s" % self.testDetails['test_name']
        print "------------" + "-"*len(self.testDetails['test_name'])
        for test_class in self.testClasses:
            test_instance = test_class()
            test_instance.displaySummary(self.summary)

    def doneReport(self, report_results):
        """
        This will get called every time a report is done and therefore a
        measurement is done.

        The state for the NetTest is informed of the fact that another task has
        reached the done state.
        """
        self.state.taskDone()

        if len(self.report.reporters) == 0:
            raise e.AllReportersFailed

        return report_results

    def makeMeasurement(self, test_instance, test_method, test_input=None):
        """
        Creates a new instance of :class:ooni.tasks.Measurement and add's it's
        callbacks and errbacks.

        Args:
            test_class:
                a subclass of :class:ooni.nettest.NetTestCase

            test_method:
                a string that represents the method to be called on test_class

            test_input:
                optional argument that represents the input to be passed to the
                NetTestCase

        """
        measurement = Measurement(test_instance, test_method, test_input)
        measurement.netTest = self

        if self.director:
            measurement.done.addCallback(self.director.measurementSucceeded,
                    measurement)
            measurement.done.addErrback(self.director.measurementFailed,
                    measurement)
        return measurement

    @defer.inlineCallbacks
    def initializeInputProcessor(self):
        for test_class, _ in self.testCases:
            test_class.inputs = yield defer.maybeDeferred(test_class().getInputProcessor)
            if not test_class.inputs:
                test_class.inputs = [None]

    def generateMeasurements(self):
        """
        This is a generator that yields measurements and registers the
        callbacks for when a measurement is successful or has failed.
        """

        for test_class, test_methods in self.testCases:
            # load the input processor as late as possible
            for input in test_class.inputs:
                measurements = []
                test_instance = test_class()
                test_instance.summary = self.summary
                for method in test_methods:
                    log.debug("Running %s %s" % (test_class, method))
                    measurement = self.makeMeasurement(test_instance, method, input)
                    measurements.append(measurement.done)
                    self.state.taskCreated()
                    yield measurement

                # When the measurement.done callbacks have all fired
                # call the postProcessor before writing the report
                if self.report:
                    post = defer.DeferredList(measurements)

                    # Call the postProcessor, which must return a single report
                    # or a deferred
                    post.addCallback(test_instance.postProcessor)
                    def noPostProcessor(failure, report):
                        failure.trap(e.NoPostProcessor)
                        return report
                    post.addErrback(noPostProcessor, test_instance.report)
                    post.addCallback(self.report.write)

                if self.report and self.director:
                    #ghetto hax to keep NetTestState counts are accurate
                    [post.addBoth(self.doneReport) for _ in measurements]

        self.state.allTasksScheduled()

class NetTestCase(object):
    """
    This is the base of the OONI nettest universe. When you write a nettest
    you will subclass this object.

    * inputs: can be set to a static set of inputs. All the tests (the methods
      starting with the "test" prefix) will be run once per input.  At every run
      the _input_ attribute of the TestCase instance will be set to the value of
      the current iteration over inputs.  Any python iterable object can be set
      to inputs.

    * inputFile: attribute should be set to an array containing the command line
      argument that should be used as the input file. Such array looks like
      this:

          ``["commandlinearg", "c", "default value" "The description"]``

      The second value of such arrray is the shorthand for the command line arg.
      The user will then be able to specify inputs to the test via:

          ``ooniprobe mytest.py --commandlinearg path/to/file.txt``

      or

          ``ooniprobe mytest.py -c path/to/file.txt``


    * inputProcessor: should be set to a function that takes as argument a
      filename and it will return the input to be passed to the test
      instance.

    * name: should be set to the name of the test.

    * author: should contain the name and contact details for the test author.
      The format for such string is as follows:

          ``The Name <email@example.com>``

    * version: is the version string of the test.

    * requiresRoot: set to True if the test must be run as root.

    * usageOptions: a subclass of twisted.python.usage.Options for processing of command line arguments

    * localOptions: contains the parsed command line arguments.

    Quirks:
    Every class that is prefixed with test *must* return a twisted.internet.defer.Deferred.
    """
    name = "This test is nameless"
    author = "Jane Doe <foo@example.com>"
    version = "0.0.0"
    description = "Sorry, this test has no description :("

    inputs = None
    inputFile = None
    inputFilename = None

    report = {}

    usageOptions = usage.Options

    optParameters = None
    baseParameters = None
    baseFlags = None

    requiredTestHelpers = {}
    requiredOptions = []
    requiresRoot = False
    requiresTor = False

    localOptions = {}
    def _setUp(self):
        """
        This is the internal setup method to be overwritten by templates.
        """
        self.report = {}
        self.inputs = None

    def requirements(self):
        """
        Place in here logic that will be executed before the test is to be run.
        If some condition is not met then you should raise an exception.
        """
        pass

    def setUp(self):
        """
        Place here your logic to be executed when the test is being setup.
        """
        pass

    def postProcessor(self, measurements):
        """
        Subclass this to do post processing tasks that are to occur once all
        the test methods have been called once per input.
        postProcessing works exactly like test methods, in the sense that
        anything that gets written to the object self.report[] will be added to
        the final test report.
        You should also place in this method any logic that is required for
        generating the summary.
        """
        raise e.NoPostProcessor

    def displaySummary(self, summary):
        """
        This gets called after the test has run to allow printing out of a
        summary of the test run.
        """
        pass

    def inputProcessor(self, filename):
        """
        You may replace this with your own custom input processor. It takes as
        input a file name.

        An inputProcessor is an iterator that will yield one item from the file
        and takes as argument a filename.

        This can be useful when you have some input data that is in a certain
        format and you want to set the input attribute of the test to something
        that you will be able to properly process.

        For example you may wish to have an input processor that will allow you
        to ignore comments in files. This can be easily achieved like so::

            fp = open(filename)
            for x in fp.xreadlines():
                if x.startswith("#"):
                    continue
                yield x.strip()
            fp.close()

        Other fun stuff is also possible.
        """
        log.debug("Running default input processor")
        with open(filename) as f:
            for line in f:
                l = line.strip()
                # Skip empty lines
                if not l:
                    continue
                # Skip comment lines
                elif l.startswith('#'):
                    continue
                yield l

    @property
    def inputFileSpecified(self):
        """
        Returns:
            True
                when inputFile is supported and is specified
            False
                when input is either not support or not specified
        """
        if not self.inputFile:
            return False

        k = self.inputFile[0]
        if self.localOptions.get(k):
            return True
        else:
            return False

    def getInputProcessor(self):
        """
        This method must be called after all options are validated by
        _checkValidOptions and _checkRequiredOptions, which ensure that
        if the inputFile is a required option it will be present.

        We check to see if it's possible to have an input file and if the user
        has specified such file.


        If the operations to be done here are network related or blocking, they
        should be wrapped in a deferred. That is the return value of this
        method should be a :class:`twisted.internet.defer.Deferred`.

        Returns:
            a generator that will yield one item from the file based on the
            inputProcessor.
        """
        if self.inputFileSpecified:
            self.inputFilename = self.localOptions[self.inputFile[0]]
            return self.inputProcessor(self.inputFilename)

        if self.inputs:
            return self.inputs

        return None

    def _checkValidOptions(self):
        for option in self.localOptions:
            if option not in self.usageOptions():
                if not self.inputFile or option not in self.inputFile:
                    raise e.InvalidOption

    def _checkRequiredOptions(self):
        missing_options = []
        for required_option in self.requiredOptions:
            log.debug("Checking if %s is present" % required_option)
            if required_option not in self.localOptions or \
                self.localOptions[required_option] == None:
                    missing_options.append(required_option)
        if missing_options:
            raise e.MissingRequiredOption(missing_options)

    def __repr__(self):
        return "<%s inputs=%s>" % (self.__class__, self.inputs)

########NEW FILE########
__FILENAME__ = bridge_reachability
# -*- encoding: utf-8 -*-
import random
from distutils.spawn import find_executable

from twisted.python import usage
from twisted.internet import reactor, error

import txtorcon

from ooni.utils import log, onion
from ooni import nettest


class TorIsNotInstalled(Exception):
    pass


class UsageOptions(usage.Options):
    optParameters = [
        ['timeout', 't', 120,
         'Specify the timeout after which to consider '
         'the Tor bootstrapping process to have failed'], ]


class BridgeReachability(nettest.NetTestCase):
    name = "Bridge Reachability"
    description = "A test for checking if bridges are reachable " \
                  "from a given location."
    author = "Arturo Filastò"
    version = "0.1"

    usageOptions = UsageOptions

    inputFile = ['file', 'f', None,
                 'File containing bridges to test reachability for. '
                 'They should be one per line IP:ORPort or '
                 'TransportType IP:ORPort (ex. obfs2 127.0.0.1:443)']

    requiredOptions = ['file']

    def requirements(self):
        if not onion.find_tor_binary():
            raise TorIsNotInstalled(
                "For instructions on installing Tor see: "
                "https://www.torproject.org/download/download")

    def setUp(self):
        self.tor_progress = 0
        self.timeout = int(self.localOptions['timeout'])

        self.report['error'] = None
        self.report['success'] = None
        self.report['timeout'] = self.timeout
        self.report['transport_name'] = 'vanilla'
        self.report['tor_version'] = str(onion.tor_details['version'])
        self.report['tor_progress'] = 0
        self.report['tor_progress_tag'] = None
        self.report['tor_progress_summary'] = None
        self.report['tor_log'] = None
        self.report['bridge_address'] = None

        self.bridge = self.input
        if self.input.startswith('Bridge'):
            self.bridge = self.input.replace('Bridge ', '')
        self.pyobfsproxy_bin = find_executable('obfsproxy')
        self.fteproxy_bin = find_executable('fteproxy')

    def postProcessor(self, measurements):
        if 'successes' not in self.summary:
            self.summary['successes'] = []
        if 'failures' not in self.summary:
            self.summary['failures'] = []

        details = {
            'address': self.report['bridge_address'],
            'transport_name': self.report['transport_name'],
            'tor_progress': self.report['tor_progress']
        }
        if self.report['success']:
            self.summary['successes'].append(details)
        else:
            self.summary['failures'].append(details)
        return self.report

    def displaySummary(self, summary):
        successful_count = {}
        failure_count = {}

        def count(results, counter):
            for result in results:
                if result['transport_name'] not in counter:
                    counter[result['transport_name']] = 0
                counter[result['transport_name']] += 1
        count(summary['successes'], successful_count)
        count(summary['failures'], failure_count)

        working_bridges = ', '.join(
            ["%s %s" % (x['transport_name'], x['address'])
             for x in summary['successes']])
        failing_bridges = ', '.join(
            ["%s %s (at %s%%)"
             % (x['transport_name'], x['address'], x['tor_progress'])
             for x in summary['failures']])

        log.msg("Total successes: %d" % len(summary['successes']))
        log.msg("Total failures: %d" % len(summary['failures']))

        for transport, count in successful_count.items():
            log.msg("%s successes: %d" % (transport.title(), count))
        for transport, count in failure_count.items():
            log.msg("%s failures: %d" % (transport.title(), count))

        log.msg("Working bridges: %s" % working_bridges)
        log.msg("Failing bridges: %s" % failing_bridges)

    def test_full_tor_connection(self):
        config = txtorcon.TorConfig()
        config.ControlPort = random.randint(2**14, 2**16)
        config.SocksPort = random.randint(2**14, 2**16)
        log.msg(
            "Connecting to %s with tor %s" %
            (self.bridge, onion.tor_details['version']))

        transport_name = onion.transport_name(self.bridge)
        if transport_name and transport_name == 'fte' and self.fteproxy_bin:
            config.ClientTransportPlugin = "%s exec %s --managed" % (
                transport_name, self.fteproxy_bin)
            self.report['transport_name'] = transport_name
            self.report['bridge_address'] = self.bridge.split(' ')[1]
        elif transport_name and transport_name == 'fte'\
                and not self.fteproxy_bin:
            log.err("Unable to test bridge because fteproxy is not installed")
            self.report['error'] = 'missing-fteproxy'
            return
        elif transport_name and self.pyobfsproxy_bin:
            config.ClientTransportPlugin = "%s exec %s managed" % (
                transport_name, self.pyobfsproxy_bin)
            self.report['transport_name'] = transport_name
            self.report['bridge_address'] = self.bridge.split(' ')[1]
        elif transport_name and not self.pyobfsproxy_bin:
            log.err(
                "Unable to test bridge because pyobfsproxy is not installed")
            self.report['error'] = 'missing-pyobfsproxy'
            return
        else:
            self.report['bridge_address'] = self.bridge.split(' ')[0]

        if transport_name and transport_name == 'scramblesuit' and \
                onion.TorVersion('0.2.5.1') > onion.tor_details['version']:
            self.report['error'] = 'unsupported-tor-version'
            log.err("Unsupported Tor version.")
            return
        elif transport_name and \
                onion.TorVersion('0.2.4.1') > onion.tor_details['version']:
            self.report['error'] = 'unsupported-tor-version'
            log.err("Unsupported Tor version.")
            return

        config.Bridge = self.bridge
        config.UseBridges = 1
        config.log = 'notice'
        config.save()

        def updates(prog, tag, summary):
            log.msg("%s: %s%%" % (self.bridge, prog))
            self.report['tor_progress'] = int(prog)
            self.report['tor_progress_tag'] = tag
            self.report['tor_progress_summary'] = summary

        d = txtorcon.launch_tor(config, reactor, timeout=self.timeout,
                                progress_updates=updates)

        @d.addCallback
        def setup_complete(proto):
            try:
                proto.transport.signalProcess('TERM')
            except error.ProcessExitedAlready:
                proto.transport.loseConnection()
            log.msg("Successfully connected to %s" % self.bridge)
            self.report['success'] = True

        @d.addErrback
        def setup_failed(failure):
            log.msg("Failed to connect to %s" % self.bridge)
            self.report['tor_log'] = failure.value.message
            self.report['success'] = False

        return d

########NEW FILE########
__FILENAME__ = dns_consistency
# -*- encoding: utf-8 -*-
#
#  dnsconsistency
#  **************
#
#  The test reports censorship if the cardinality of the intersection of
#  the query result set from the control server and the query result set
#  from the experimental server is zero, which is to say, if the two sets
#  have no matching results whatsoever.
#
#  NOTE: This test frequently results in false positives due to GeoIP-based
#  load balancing on major global sites such as google, facebook, and
#  youtube, etc.
#
# :authors: Arturo Filastò, Isis Lovecruft
# :licence: see LICENSE


from twisted.python import usage
from twisted.internet import defer

from ooni.templates import dnst

from ooni.utils import log


class UsageOptions(usage.Options):
    optParameters = [['backend', 'b', None,
                      'The OONI backend that runs the DNS resolver'],
                     ['testresolvers', 'T', None,
                      'File containing list of DNS resolvers to test against'],
                     ['testresolver', 't', None,
                         'Specify a single test resolver to use for testing']
                     ]


class DNSConsistencyTest(dnst.DNSTest):

    name = "DNS Consistency"
    description = "Checks to see if the DNS responses from a "\
                  "set of DNS resolvers are consistent."
    version = "0.6"
    authors = "Arturo Filastò, Isis Lovecruft"

    inputFile = ['file', 'f', None,
                 'Input file of list of hostnames to attempt to resolve']

    requiredTestHelpers = {'backend': 'dns'}
    requiresRoot = False
    requiresTor = False

    usageOptions = UsageOptions
    requiredOptions = ['backend', 'file']

    def setUp(self):
        if (not self.localOptions['testresolvers'] and
                not self.localOptions['testresolver']):
            self.test_resolvers = []
            with open('/etc/resolv.conf') as f:
                for line in f:
                    if line.startswith('nameserver'):
                        self.test_resolvers.append(line.split(' ')[1].strip())
            self.report['test_resolvers'] = self.test_resolvers

        elif self.localOptions['testresolvers']:
            test_resolvers_file = self.localOptions['testresolvers']

        elif self.localOptions['testresolver']:
            self.test_resolvers = [self.localOptions['testresolver']]

        try:
            with open(test_resolvers_file) as f:
                self.test_resolvers = [
                    x.split('#')[0].strip() for x in f.readlines()]
                self.report['test_resolvers'] = self.test_resolvers
            f.close()

        except IOError as e:
            log.exception(e)
            raise usage.UsageError("Invalid test resolvers file")

        except NameError:
            log.debug("No test resolver file configured")

        dns_ip, dns_port = self.localOptions['backend'].split(':')
        self.control_dns_server = (str(dns_ip), int(dns_port))

        self.report['control_resolver'] = "%s:%d" % self.control_dns_server

    @defer.inlineCallbacks
    def test_a_lookup(self):
        """
        We perform an A lookup on the DNS test servers for the domains to be
        tested and an A lookup on the known good DNS server.

        We then compare the results from test_resolvers and that from
        control_resolver and see if they match up.
        If they match up then no censorship is happening (tampering: false).

        If they do not we do a reverse lookup (PTR) on the test_resolvers and
        the control resolver for every IP address we got back and check to see
        if anyone of them matches the control ones.

        If they do, then we take note of the fact that censorship is probably not
        happening (tampering: reverse-match).

        If they do not match then censorship is probably going on (tampering:
        true).
        """
        log.msg("Doing the test lookups on %s" % self.input)
        hostname = self.input

        self.report['tampering'] = {}

        control_answers = yield self.performALookup(hostname,
                                                    self.control_dns_server)
        if not control_answers:
            log.err(
                "Got no response from control DNS server %s:%d, "
                "perhaps the DNS resolver is down?" %
                self.control_dns_server[0])
            self.report['tampering'][
                "%s:%d" %
                self.control_dns_server] = 'no_answer'
            return

        for test_resolver in self.test_resolvers:
            log.msg("Testing resolver: %s" % test_resolver)
            test_dns_server = (test_resolver, 53)

            try:
                experiment_answers = yield self.performALookup(hostname,
                                                               test_dns_server)
            except Exception as e:
                log.err("Problem performing the DNS lookup")
                log.exception(e)
                self.report['tampering'][test_resolver] = 'dns_lookup_error'
                continue

            if not experiment_answers:
                log.err("Got no response, perhaps the DNS resolver is down?")
                self.report['tampering'][test_resolver] = 'no_answer'
                continue
            else:
                log.debug(
                    "Got the following A lookup answers %s from %s" %
                    (experiment_answers, test_resolver))

            def lookup_details():
                """
                A closure useful for printing test details.
                """
                log.msg("test resolver: %s" % test_resolver)
                log.msg("experiment answers: %s" % experiment_answers)
                log.msg("control answers: %s" % control_answers)

            log.debug(
                "Comparing %s with %s" %
                (experiment_answers, control_answers))
            if set(experiment_answers) & set(control_answers):
                lookup_details()
                log.msg("tampering: false")
                self.report['tampering'][test_resolver] = False
            else:
                log.msg("Trying to do reverse lookup")
                experiment_reverse = yield self.performPTRLookup(experiment_answers[0],
                                                                 test_dns_server)
                control_reverse = yield self.performPTRLookup(control_answers[0],
                                                              self.control_dns_server)

                if experiment_reverse == control_reverse:
                    log.msg("Further testing has eliminated false positives")
                    lookup_details()
                    log.msg("tampering: reverse_match")
                    self.report['tampering'][test_resolver] = 'reverse_match'
                else:
                    log.msg("Reverse lookups do not match")
                    lookup_details()
                    log.msg("tampering: true")
                    self.report['tampering'][test_resolver] = True

    def inputProcessor(self, filename=None):
        """
        This inputProcessor extracts domain names from urls
        """
        log.debug("Running dnsconsistency default processor")
        if filename:
            fp = open(filename)
            for x in fp.readlines():
                yield x.strip().split('//')[-1].split('/')[0]
            fp.close()
        else:
            pass

########NEW FILE########
__FILENAME__ = http_requests
# -*- encoding: utf-8 -*-
#
# :authors: Arturo Filastò
# :licence: see LICENSE

import random
from twisted.python import usage, failure

from ooni.utils import log
from ooni.utils.net import userAgents
from ooni.templates import httpt
from ooni.errors import failureToString


class UsageOptions(usage.Options):
    optParameters = [
        ['url', 'u', None, 'Specify a single URL to test.'],
        ['factor', 'f', 0.8,
         'What factor should be used for triggering censorship (0.8 == 80%)']]


class HTTPRequestsTest(httpt.HTTPTest):

    """
    Performs a two GET requests to the set of sites to be tested for
    censorship, one over a known good control channel (Tor), the other over the
    test network.

    We check to see if the response headers match and if the response body
    lengths match.
    """
    name = "HTTP Requests"
    description = "Performs a HTTP GET request over Tor and one over the " \
                  "local network and compares the two results."
    author = "Arturo Filastò"
    version = "0.2.4"

    usageOptions = UsageOptions

    inputFile = ['file', 'f', None,
                 'List of URLS to perform GET and POST requests to']
    requiresRoot = False
    requiresTor = False

    # These values are used for determining censorship based on response body
    # lengths
    control_body_length = None
    experiment_body_length = None

    def setUp(self):
        """
        Check for inputs.
        """
        if self.input:
            self.url = self.input
        elif self.localOptions['url']:
            self.url = self.localOptions['url']
        else:
            raise Exception("No input specified")

        self.factor = self.localOptions['factor']
        self.report['control_failure'] = None
        self.report['experiment_failure'] = None
        self.report['body_length_match'] = None
        self.report['body_proportion'] = None
        self.report['factor'] = float(self.factor)
        self.report['headers_diff'] = None
        self.report['headers_match'] = None

        self.headers = {'User-Agent': [random.choice(userAgents)]}

    def compare_body_lengths(self, body_length_a, body_length_b):

        if body_length_b == 0 and body_length_a != 0:
            rel = float(body_length_b)/float(body_length_a)
        elif body_length_b == 0 and body_length_a == 0:
            rel = float(1)
        else:
            rel = float(body_length_a)/float(body_length_b)

        if rel > 1:
            rel = 1/rel

        self.report['body_proportion'] = rel
        if rel > float(self.factor):
            log.msg("The two body lengths appear to match")
            log.msg("censorship is probably not happening")
            self.report['body_length_match'] = True
        else:
            log.msg("The two body lengths appear to not match")
            log.msg("censorship could be happening")
            self.report['body_length_match'] = False

    def compare_headers(self, headers_a, headers_b):
        diff = headers_a.getDiff(headers_b)
        if diff:
            log.msg("Headers appear to *not* match")
            self.report['headers_diff'] = diff
            self.report['headers_match'] = False
        else:
            log.msg("Headers appear to match")
            self.report['headers_diff'] = diff
            self.report['headers_match'] = True

    def test_get_experiment(self):
        log.msg("Performing GET request to %s" % self.url)
        return self.doRequest(self.url, method="GET",
                              use_tor=False, headers=self.headers)

    def test_get_control(self):
        log.msg("Performing GET request to %s over Tor" % self.url)
        return self.doRequest(self.url, method="GET",
                              use_tor=True, headers=self.headers)

    def postProcessor(self, measurements):
        experiment = control = None
        for status, measurement in measurements:
            if 'experiment' in str(measurement.netTestMethod):
                if isinstance(measurement.result, failure.Failure):
                    self.report['experiment_failure'] = failureToString(
                        measurement.result)
                else:
                    experiment = measurement.result
            elif 'control' in str(measurement.netTestMethod):
                if isinstance(measurement.result, failure.Failure):
                    self.report['control_failure'] = failureToString(
                        measurement.result)
                else:
                    control = measurement.result

        if experiment and control:
            self.compare_body_lengths(len(control.body),
                                      len(experiment.body))
            self.compare_headers(control.headers,
                                 experiment.headers)
        return self.report

########NEW FILE########
__FILENAME__ = tcp_connect
# -*- encoding: utf-8 -*-
from twisted.internet.protocol import Factory, Protocol
from twisted.internet.endpoints import TCP4ClientEndpoint

from ooni import nettest
from ooni.errors import handleAllFailures
from ooni.utils import log


class TCPFactory(Factory):

    def buildProtocol(self, addr):
        return Protocol()


class TCPConnectTest(nettest.NetTestCase):
    name = "TCP Connect"
    description = "Performs a TCP connect scan of all the " \
                  "host port combinations given as input."
    author = "Arturo Filastò"
    version = "0.1"
    inputFile = [
        'file',
        'f',
        None,
        'File containing the IP:PORT combinations to be tested, one per line']

    requiresTor = False
    requiresRoot = False
    requiredOptions = ['file']

    def test_connect(self):
        """
        This test performs a TCP connection to the remote host on the
        specified port.
        The report will contains the string 'success' if the test has
        succeeded, or the reason for the failure if it has failed.
        """
        host, port = self.input.split(":")

        def connectionSuccess(protocol):
            protocol.transport.loseConnection()
            log.debug("Got a connection to %s" % self.input)
            self.report["connection"] = 'success'

        def connectionFailed(failure):
            self.report['connection'] = handleAllFailures(failure)

        from twisted.internet import reactor
        point = TCP4ClientEndpoint(reactor, host, int(port))
        d = point.connect(TCPFactory())
        d.addCallback(connectionSuccess)
        d.addErrback(connectionFailed)
        return d

    def inputProcessor(self, filename=None):
        """
        This inputProcessor extracts name:port pairs from urls
        XXX: Does not support unusual port numbers
        """
        def strip_url(address):
            proto, path = x.strip().split('://')
            proto = proto.lower()
            host = path.split('/')[0]
            if proto == 'http':
                return "%s:80" % host
            if proto == 'https':
                return "%s:443" % host

        if filename:
            fp = open(filename)
            for x in fp.readlines():
                if x.startswith("http"):
                    yield strip_url(x)
                else:
                    yield x.strip()
            fp.close()
        else:
            pass

########NEW FILE########
__FILENAME__ = bridget
#!/usr/bin/env python
# -*- encoding: utf-8 -*-
#
#  +-----------+
#  |  BRIDGET  |
#  |        +--------------------------------------------+
#  +--------| Use a Tor process to test making a Tor     |
#           | connection to a list of bridges or relays. |
#           +--------------------------------------------+
#
# :authors: Isis Lovecruft, Arturo Filasto
# :licence: see included LICENSE
# :version: 0.1.0-alpha

from __future__           import with_statement
from functools            import partial
from random               import randint

import os
import sys

from twisted.python       import usage
from twisted.internet     import defer, error, reactor

from ooni                 import nettest

from ooni.utils           import log, date
from ooni.utils.config    import ValueChecker

from ooni.utils.onion     import TxtorconImportError
from ooni.utils.onion     import PTNoBridgesException, PTNotFoundException


try:
    from ooni.utils.onion     import parse_data_dir
except:
    log.msg("Please go to /ooni/lib and do 'make txtorcon' to run this test!")

class MissingAssetException(Exception):
    pass

class RandomPortException(Exception):
    """Raised when using a random port conflicts with configured ports."""
    def __init__(self):
        log.msg("Unable to use random and specific ports simultaneously")
        return sys.exit()

class BridgetArgs(usage.Options):
    """Commandline options."""
    allowed = "Port to use for Tor's %s, must be between 1024 and 65535."
    sock_check = ValueChecker(allowed % "SocksPort").port_check
    ctrl_check = ValueChecker(allowed % "ControlPort").port_check

    optParameters = [
        ['bridges', 'b', None,
         'File listing bridge IP:ORPorts to test'],
        ['relays', 'f', None,
         'File listing relay IPs to test'],
        ['socks', 's', 9049, None, sock_check],
        ['control', 'c', 9052, None, ctrl_check],
        ['torpath', 'p', None,
         'Path to the Tor binary to use'],
        ['datadir', 'd', None,
         'Tor DataDirectory to use'],
        ['transport', 't', None,
         'Tor ClientTransportPlugin'],
        ['resume', 'r', 0,
         'Resume at this index']]
    optFlags = [['random', 'x', 'Use random ControlPort and SocksPort']]

    def postOptions(self):
        if not self['bridges'] and not self['relays']:
            raise MissingAssetException(
                "Bridget can't run without bridges or relays to test!")
        if self['transport']:
            ValueChecker.uid_check(
                "Can't run bridget as root with pluggable transports!")
            if not self['bridges']:
                raise PTNoBridgesException
        if self['socks'] or self['control']:
            if self['random']:
                raise RandomPortException
        if self['datadir']:
            ValueChecker.dir_check(self['datadir'])
        if self['torpath']:
            ValueChecker.file_check(self['torpath'])

class BridgetTest(nettest.NetTestCase):
    """
    XXX fill me in

    :ivar config:
        An :class:`ooni.lib.txtorcon.TorConfig` instance.
    :ivar relays:
        A list of all provided relays to test.
    :ivar bridges:
        A list of all provided bridges to test.
    :ivar socks_port:
        Integer for Tor's SocksPort.
    :ivar control_port:
        Integer for Tor's ControlPort.
    :ivar transport:
        String defining the Tor's ClientTransportPlugin, for testing
        a bridge's pluggable transport functionality.
    :ivar tor_binary:
        Path to the Tor binary to use, e.g. \'/usr/sbin/tor\'
    """
    name    = "bridget"
    author  = "Isis Lovecruft <isis@torproject.org>"
    version = "0.1"
    description   = "Use a Tor process to test connecting to bridges or relays"
    usageOptions = BridgetArgs

    def setUp(self):
        """
        Extra initialization steps. We only want one child Tor process
        running, so we need to deal with most of the TorConfig() only once,
        before the experiment runs.
        """
        self.socks_port      = 9049
        self.control_port    = 9052
        self.circuit_timeout = 90
        self.tor_binary      = '/usr/sbin/tor'
        self.data_directory  = None

        def read_from_file(filename):
            log.msg("Loading information from %s ..." % opt)
            with open(filename) as fp:
                lst = []
                for line in fp.readlines():
                    if line.startswith('#'):
                        continue
                    else:
                        lst.append(line.replace('\n',''))
                return lst

        def __count_remaining__(which):
            total, reach, unreach = map(lambda x: which[x],
                                        ['all', 'reachable', 'unreachable'])
            count = len(total) - reach() - unreach()
            return count

        ## XXX should we do report['bridges_up'].append(self.bridges['current'])
        self.bridges = {}
        self.bridges['all'], self.bridges['up'], self.bridges['down'] = \
            ([] for i in range(3))
        self.bridges['reachable']   = lambda: len(self.bridges['up'])
        self.bridges['unreachable'] = lambda: len(self.bridges['down'])
        self.bridges['remaining']   = lambda: __count_remaining__(self.bridges)
        self.bridges['current']     = None
        self.bridges['pt_type']     = None
        self.bridges['use_pt']      = False

        self.relays = {}
        self.relays['all'], self.relays['up'], self.relays['down'] = \
            ([] for i in range(3))
        self.relays['reachable']   = lambda: len(self.relays['up'])
        self.relays['unreachable'] = lambda: len(self.relays['down'])
        self.relays['remaining']   = lambda: __count_remaining__(self.relays)
        self.relays['current']     = None

        if self.localOptions:
            try:
                from txtorcon import TorConfig
            except ImportError:
                raise TxtorconImportError
            else:
                self.config = TorConfig()
            finally:
                options = self.localOptions

            if options['bridges']:
                self.config.UseBridges = 1
                self.bridges['all'] = read_from_file(options['bridges'])
            if options['relays']:
                ## first hop must be in TorState().guards
                # XXX where is this defined?
                self.config.EntryNodes = ','.join(relay_list)
                self.relays['all'] = read_from_file(options['relays'])
            if options['socks']:
                self.socks_port = options['socks']
            if options['control']:
                self.control_port = options['control']
            if options['random']:
                log.msg("Using randomized ControlPort and SocksPort ...")
                self.socks_port   = randint(1024, 2**16)
                self.control_port = randint(1024, 2**16)
            if options['torpath']:
                self.tor_binary = options['torpath']
            if options['datadir']:
                self.data_directory = parse_data_dir(options['datadir'])
            if options['transport']:
                ## ClientTransportPlugin transport exec pathtobinary [options]
                ## XXX we need a better way to deal with all PTs
                log.msg("Using ClientTransportPlugin %s" % options['transport'])
                self.bridges['use_pt'] = True
                [self.bridges['pt_type'], pt_exec] = \
                    options['transport'].split(' ', 1)

                if self.bridges['pt_type'] == "obfs2":
                    self.config.ClientTransportPlugin = \
                        self.bridges['pt_type'] + " " + pt_exec
                else:
                    raise PTNotFoundException

            self.config.SocksPort            = self.socks_port
            self.config.ControlPort          = self.control_port
            self.config.CookieAuthentication = 1

    def test_bridget(self):
        """
        if bridges:
            1. configure first bridge line
            2a. configure data_dir, if it doesn't exist
            2b. write torrc to a tempfile in data_dir
            3. start tor                              } if any of these
            4. remove bridges which are public relays } fail, add current
            5. SIGHUP for each bridge                 } bridge to unreach-
                                                      } able bridges.
        if relays:
            1a. configure the data_dir, if it doesn't exist
            1b. write torrc to a tempfile in data_dir
            2. start tor
            3. remove any of our relays which are already part of current
               circuits
            4a. attach CustomCircuit() to self.state
            4b. RELAY_EXTEND for each relay } if this fails, add
                                            } current relay to list
                                            } of unreachable relays
            5.
        if bridges and relays:
            1. configure first bridge line
            2a. configure data_dir if it doesn't exist
            2b. write torrc to a tempfile in data_dir
            3. start tor
            4. remove bridges which are public relays
            5. remove any of our relays which are already part of current
               circuits
            6a. attach CustomCircuit() to self.state
            6b. for each bridge, build three circuits, with three
                relays each
            6c. RELAY_EXTEND for each relay } if this fails, add
                                            } current relay to list
                                            } of unreachable relays

        :param args:
            The :class:`BridgetAsset` line currently being used. Except that it
            in Bridget it doesn't, so it should be ignored and avoided.
        """
        try:
            from ooni.utils         import process
            from ooni.utils.onion   import remove_public_relays, start_tor
            from ooni.utils.onion   import start_tor_filter_nodes
            from ooni.utils.onion   import setup_fail, setup_done
            from ooni.utils.onion   import CustomCircuit
            from ooni.utils.timer   import deferred_timeout, TimeoutError
            from ooni.lib.txtorcon  import TorConfig, TorState
        except ImportError:
            raise TxtorconImportError
        except TxtorconImportError, tie:
            log.err(tie)
            sys.exit()

        def reconfigure_done(state, bridges):
            """
            Append :ivar:`bridges['current']` to the list
            :ivar:`bridges['up'].
            """
            log.msg("Reconfiguring with 'Bridge %s' successful"
                    % bridges['current'])
            bridges['up'].append(bridges['current'])
            return state

        def reconfigure_fail(state, bridges):
            """
            Append :ivar:`bridges['current']` to the list
            :ivar:`bridges['down'].
            """
            log.msg("Reconfiguring TorConfig with parameters %s failed"
                    % state)
            bridges['down'].append(bridges['current'])
            return state

        @defer.inlineCallbacks
        def reconfigure_bridge(state, bridges):
            """
            Rewrite the Bridge line in our torrc. If use of pluggable
            transports was specified, rewrite the line as:
                Bridge <transport_type> <IP>:<ORPort>
            Otherwise, rewrite in the standard form:
                Bridge <IP>:<ORPort>

            :param state:
                A fully bootstrapped instance of
                :class:`ooni.lib.txtorcon.TorState`.
            :param bridges:
                A dictionary of bridges containing the following keys:

                bridges['remaining'] :: A function returning and int for the
                                        number of remaining bridges to test.
                bridges['current']   :: A string containing the <IP>:<ORPort>
                                        of the current bridge.
                bridges['use_pt']    :: A boolean, True if we're testing
                                        bridges with a pluggable transport;
                                        False otherwise.
                bridges['pt_type']   :: If :ivar:`bridges['use_pt'] is True,
                                        this is a string containing the type
                                        of pluggable transport to test.
            :return:
                :param:`state`
            """
            log.msg("Current Bridge: %s" % bridges['current'])
            log.msg("We now have %d bridges remaining to test..."
                    % bridges['remaining']())
            try:
                if bridges['use_pt'] is False:
                    controller_response = yield state.protocol.set_conf(
                        'Bridge', bridges['current'])
                elif bridges['use_pt'] and bridges['pt_type'] is not None:
                    controller_reponse = yield state.protocol.set_conf(
                        'Bridge', bridges['pt_type'] +' '+ bridges['current'])
                else:
                    raise PTNotFoundException

                if controller_response == 'OK':
                    finish = yield reconfigure_done(state, bridges)
                else:
                    log.err("SETCONF for %s responded with error:\n %s"
                            % (bridges['current'], controller_response))
                    finish = yield reconfigure_fail(state, bridges)

                defer.returnValue(finish)

            except Exception, e:
                log.err("Reconfiguring torrc with Bridge line %s failed:\n%s"
                        % (bridges['current'], e))
                defer.returnValue(None)

        def attacher_extend_circuit(attacher, deferred, router):
            ## XXX todo write me
            ## state.attacher.extend_circuit
            raise NotImplemented
            #attacher.extend_circuit

        def state_attach(state, path):
            log.msg("Setting up custom circuit builder...")
            attacher = CustomCircuit(state)
            state.set_attacher(attacher, reactor)
            state.add_circuit_listener(attacher)
            return state

            ## OLD
            #for circ in state.circuits.values():
            #    for relay in circ.path:
            #        try:
            #            relay_list.remove(relay)
            #        except KeyError:
            #            continue
            ## XXX how do we attach to circuits with bridges?
            d = defer.Deferred()
            attacher.request_circuit_build(d)
            return d

        def state_attach_fail(state):
            log.err("Attaching custom circuit builder failed: %s" % state)

        log.msg("Bridget: initiating test ... ")  ## Start the experiment

        ## if we've at least one bridge, and our config has no 'Bridge' line
        if self.bridges['remaining']() >= 1 \
                and not 'Bridge' in self.config.config:

            ## configure our first bridge line
            self.bridges['current'] = self.bridges['all'][0]
            self.config.Bridge = self.bridges['current']
                                                  ## avoid starting several
            self.config.save()                    ## processes
            assert self.config.config.has_key('Bridge'), "No Bridge Line"

            ## start tor and remove bridges which are public relays
            from ooni.utils.onion import start_tor_filter_nodes
            state = start_tor_filter_nodes(reactor, self.config,
                                           self.control_port, self.tor_binary,
                                           self.data_directory, self.bridges)
            #controller = defer.Deferred()
            #controller.addCallback(singleton_semaphore, tor)
            #controller.addErrback(setup_fail)
            #bootstrap = defer.gatherResults([controller, filter_bridges],
            #                                consumeErrors=True)

            if state is not None:
                log.debug("state:\n%s" % state)
                log.debug("Current callbacks on TorState():\n%s"
                          % state.callbacks)

        ## if we've got more bridges
        if self.bridges['remaining']() >= 2:
            #all = []
            for bridge in self.bridges['all'][1:]:
                self.bridges['current'] = bridge
                #new = defer.Deferred()
                #new.addCallback(reconfigure_bridge, state, self.bridges)
                #all.append(new)
            #check_remaining = defer.DeferredList(all, consumeErrors=True)
            #state.chainDeferred(check_remaining)
                state.addCallback(reconfigure_bridge, self.bridges)

        if self.relays['remaining']() > 0:
            while self.relays['remaining']() >= 3:
                #path = list(self.relays.pop() for i in range(3))
                #log.msg("Trying path %s" % '->'.join(map(lambda node:
                #                                         node, path)))
                self.relays['current'] = self.relays['all'].pop()
                for circ in state.circuits.values():
                    for node in circ.path:
                        if node == self.relays['current']:
                            self.relays['up'].append(self.relays['current'])
                    if len(circ.path) < 3:
                        try:
                            ext = attacher_extend_circuit(state.attacher, circ,
                                                          self.relays['current'])
                            ext.addCallback(attacher_extend_circuit_done,
                                            state.attacher, circ,
                                            self.relays['current'])
                        except Exception, e:
                            log.err("Extend circuit failed: %s" % e)
                    else:
                        continue

        #state.callback(all)
        #self.reactor.run()
        return state

    def disabled_startTest(self, args):
        """
        Local override of :meth:`OONITest.startTest` to bypass calling
        self.control.

        :param args:
            The current line of :class:`Asset`, not used but kept for
            compatibility reasons.
        :return:
            A fired deferred which callbacks :meth:`experiment` and
            :meth:`OONITest.finished`.
        """
        self.start_time = date.now()
        self.d = self.experiment(args)
        self.d.addErrback(log.err)
        self.d.addCallbacks(self.finished, log.err)
        return self.d

## ISIS' NOTES
## -----------
## TODO:
##       x  cleanup documentation
##       x  add DataDirectory option
##       x  check if bridges are public relays
##       o  take bridge_desc file as input, also be able to give same
##          format as output
##       x  Add asynchronous timeout for deferred, so that we don't wait
##       o  Add assychronous timout for deferred, so that we don't wait
##          forever for bridges that don't work.

########NEW FILE########
__FILENAME__ = echo
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  +---------+
#  | echo.py |
#  +---------+
#     A simple ICMP-8 ping test.
#
# @authors: Isis Lovecruft, <isis@torproject.org>
# @version: 0.0.2-pre-alpha
# @license: copyright (c) 2012 Isis Lovecruft
#           see attached LICENCE file
#

import os
import sys

from twisted.python   import usage
from twisted.internet import reactor, defer
from ooni             import nettest
from ooni.utils       import log, net, Storage, txscapy

try:
    from scapy.all             import IP, ICMP
    from scapy.all             import sr1
    from ooni.lib              import txscapy
    from ooni.lib.txscapy      import txsr, txsend
    from ooni.templates.scapyt import BaseScapyTest
except:
    log.msg("This test requires scapy, see www.secdev.org/projects/scapy")

class UsageOptions(usage.Options):
    optParameters = [
        ['dst', 'd', None, 'Host IP to ping'],
        ['file', 'f', None, 'File of list of IPs to ping'],
        ['interface', 'i', None, 'Network interface to use'],
        ['count', 'c', 1, 'Number of packets to send', int],
        ['size', 's', 56, 'Number of bytes to send in ICMP data field', int],
        ['ttl', 'l', 25, 'Set the IP Time to Live', int],
        ['timeout', 't', 2, 'Seconds until timeout if no response', int],
        ['pcap', 'p', None, 'Save pcap to this file'],
        ['receive', 'r', True, 'Receive response packets']]

class EchoTest(nettest.NetTestCase):
    """
    xxx fill me in
    """
    name         = 'echo'
    author       = 'Isis Lovecruft <isis@torproject.org>'
    description  = 'A simple ping test to see if a host is reachable.'
    version      = '0.0.2'
    requiresRoot = True

    usageOptions    = UsageOptions
    #requiredOptions = ['dst']

    def setUp(self, *a, **kw):
        self.destinations = {}

        if self.localOptions:
            for key, value in self.localOptions.items():
                log.debug("setting self.%s = %s" % (key, value))
                setattr(self, key, value)

        self.timeout *= 1000            ## convert to milliseconds

        if not self.interface:
            try:
                iface = txscapy.getDefaultIface()
            except Exception, e:
                log.msg("No network interface specified!")
                log.err(e)
            else:
                log.msg("Using system default interface: %s" % iface)
                self.interface = iface

        if self.pcap:
            try:
                self.pcapfile = open(self.pcap, 'a+')
            except:
                log.msg("Unable to write to pcap file %s" % self.pcap)
            else:
                self.pcap = net.capturePacket(self.pcapfile)

        if not self.dst:
            if self.file:
                self.dstProcessor(self.file)
                for key, value in self.destinations.items():
                    for label, data in value.items():
                        if not 'ans' in data:
                            self.dst = label
        else:
            self.addDest(self.dst)
        log.debug("self.dst is now: %s" % self.dst)

        log.debug("Initialization of %s test completed." % self.name)

    def addDest(self, dest):
        d = dest.strip()
        self.destinations[d] = {'dst_ip': d}

    def dstProcessor(self, inputfile):
        from ipaddr import IPAddress

        if os.path.isfile(inputfile):
            with open(inputfile) as f:
                for line in f.readlines():
                    if line.startswith('#'):
                        continue
                    self.addDest(line)

    def test_icmp(self):
        def process_response(echo_reply, dest):
           ans, unans = echo_reply
           if ans:
               log.msg("Recieved echo reply from %s: %s" % (dest, ans))
           else:
               log.msg("No reply was received from %s. Possible censorship event." % dest)
               log.debug("Unanswered packets: %s" % unans)
           self.report[dest] = echo_reply

        for label, data in self.destinations.items():
            reply = sr1(IP(dst=lebal)/ICMP())
            process = process_reponse(reply, label)

        #(ans, unans) = ping
        #self.destinations[self.dst].update({'ans': ans,
        #                                    'unans': unans,
        #                                    'response_packet': ping})
        #return ping

        #return reply

########NEW FILE########
__FILENAME__ = chinatrigger
import random
import string
import struct
import time

from twisted.python import usage
from ooni.templates.scapyt import BaseScapyTest

class UsageOptions(usage.Options):
    optParameters = [['dst', 'd', None, 'Specify the target address'],
                     ['port', 'p', None, 'Specify the target port']
                    ]

class ChinaTriggerTest(BaseScapyTest):
    """
    This test is a OONI based implementation of the C tool written
    by Philipp Winter to engage chinese probes in active scanning.

    Example of running it:
    ./bin/ooniprobe chinatrigger -d 127.0.0.1 -p 8080
    """

    name = "chinatrigger"
    usageOptions = UsageOptions
    requiredOptions = ['dst', 'port']
    timeout = 2

    def setUp(self):
        self.dst = self.localOptions['dst']
        self.port = int(self.localOptions['port'])

    @staticmethod
    def set_random_servername(pkt):
        ret = pkt[:121]
        for i in range(16):
            ret += random.choice(string.ascii_lowercase)
        ret += pkt[121+16:]
        return ret

    @staticmethod
    def set_random_time(pkt):
        ret = pkt[:11]
        ret += struct.pack('!I', int(time.time()))
        ret += pkt[11+4:]
        return ret

    @staticmethod
    def set_random_field(pkt):
        ret = pkt[:15]
        for i in range(28):
            ret += chr(random.randint(0, 255))
        ret += pkt[15+28:]
        return ret

    @staticmethod
    def mutate(pkt, idx):
        """
        Slightly changed mutate function.
        """
        ret = pkt[:idx-1]
        mutation = chr(random.randint(0, 255))
        while mutation == pkt[idx]:
            mutation = chr(random.randint(0, 255))
        ret += mutation
        ret += pkt[idx:]
        return ret

    @staticmethod
    def set_all_random_fields(pkt):
        pkt = ChinaTriggerTest.set_random_servername(pkt)
        pkt = ChinaTriggerTest.set_random_time(pkt)
        pkt = ChinaTriggerTest.set_random_field(pkt)
        return pkt

    def test_send_mutations(self):
        from scapy.all import IP, TCP
        pkt = "\x16\x03\x01\x00\xcc\x01\x00\x00\xc8"\
              "\x03\x01\x4f\x12\xe5\x63\x3f\xef\x7d"\
              "\x20\xb9\x94\xaa\x04\xb0\xc1\xd4\x8c"\
              "\x50\xcd\xe2\xf9\x2f\xa9\xfb\x78\xca"\
              "\x02\xa8\x73\xe7\x0e\xa8\xf9\x00\x00"\
              "\x3a\xc0\x0a\xc0\x14\x00\x39\x00\x38"\
              "\xc0\x0f\xc0\x05\x00\x35\xc0\x07\xc0"\
              "\x09\xc0\x11\xc0\x13\x00\x33\x00\x32"\
              "\xc0\x0c\xc0\x0e\xc0\x02\xc0\x04\x00"\
              "\x04\x00\x05\x00\x2f\xc0\x08\xc0\x12"\
              "\x00\x16\x00\x13\xc0\x0d\xc0\x03\xfe"\
              "\xff\x00\x0a\x00\xff\x01\x00\x00\x65"\
              "\x00\x00\x00\x1d\x00\x1b\x00\x00\x18"\
              "\x77\x77\x77\x2e\x67\x6e\x6c\x69\x67"\
              "\x78\x7a\x70\x79\x76\x6f\x35\x66\x76"\
              "\x6b\x64\x2e\x63\x6f\x6d\x00\x0b\x00"\
              "\x04\x03\x00\x01\x02\x00\x0a\x00\x34"\
              "\x00\x32\x00\x01\x00\x02\x00\x03\x00"\
              "\x04\x00\x05\x00\x06\x00\x07\x00\x08"\
              "\x00\x09\x00\x0a\x00\x0b\x00\x0c\x00"\
              "\x0d\x00\x0e\x00\x0f\x00\x10\x00\x11"\
              "\x00\x12\x00\x13\x00\x14\x00\x15\x00"\
              "\x16\x00\x17\x00\x18\x00\x19\x00\x23"\
              "\x00\x00"

        pkt = ChinaTriggerTest.set_all_random_fields(pkt)
        pkts = [IP(dst=self.dst)/TCP(dport=self.port)/pkt]
        for x in range(len(pkt)):
            mutation = IP(dst=self.dst)/TCP(dport=self.port)/ChinaTriggerTest.mutate(pkt, x)
            pkts.append(mutation)
        return self.sr(pkts, timeout=2)


########NEW FILE########
__FILENAME__ = dns_injection
# -*- encoding: utf-8 -*-
from twisted.python import usage
from twisted.internet import defer

from ooni.templates import dnst
from ooni import nettest
from ooni.utils import log

class UsageOptions(usage.Options):
    optParameters = [
            ['resolver', 'r', '8.8.8.1', 'an invalid DNS resolver'],
            ['timeout', 't', 3, 'timeout after which we should consider the query failed']
    ]

class DNSInjectionTest(dnst.DNSTest):
    """
    This test detects DNS spoofed DNS responses by performing UDP based DNS
    queries towards an invalid DNS resolver.

    For it to work we must be traversing the network segment of a machine that
    is actively injecting DNS query answers.
    """
    name = "DNS Injection"
    description = "Checks for injection of spoofed DNS answers"
    version = "0.1"
    authors = "Arturo Filastò"

    inputFile = ['file', 'f', None,
                 'Input file of list of hostnames to attempt to resolve']

    usageOptions = UsageOptions
    requiredOptions = ['resolver', 'file']
    requiresRoot = False
    requiresTor = False

    def setUp(self):
        self.resolver = (self.localOptions['resolver'], 53)
        self.queryTimeout = [self.localOptions['timeout']]

    def inputProcessor(self, filename):
        fp = open(filename)
        for line in fp:
            if line.startswith('http://'):
                yield line.replace('http://', '').replace('/', '').strip()
            else:
                yield line.strip()
        fp.close()

    def test_injection(self):
        self.report['injected'] = None

        d = self.performALookup(self.input, self.resolver)
        @d.addCallback
        def cb(res):
            log.msg("The DNS query for %s is injected" % self.input)
            self.report['injected'] = True

        @d.addErrback
        def err(err):
            err.trap(defer.TimeoutError)
            log.msg("The DNS query for %s is not injected" % self.input)
            self.report['injected'] = False

        return d


########NEW FILE########
__FILENAME__ = domclass_collector
# -*- encoding: utf-8 -*-
#
# The purpose of this collector is to compute the eigenvector for the input
# file containing a list of sites.
#
#
# :authors: Arturo Filastò
# :licence: see LICENSE

from twisted.internet import threads, defer

from ooni.kit import domclass
from ooni.templates import httpt

class DOMClassCollector(httpt.HTTPTest):
    name = "DOM class collector"
    author = "Arturo Filastò"
    version = 0.1

    followRedirects = True

    inputFile = ['file', 'f', None, 'The list of urls to build a domclass for']
    requiresTor = False
    requiresRoot = False

    def test_collect(self):
        if self.input:
            url = self.input
            return self.doRequest(url)
        else:
            raise Exception("No input specified")

    def processResponseBody(self, body):
        eigenvalues = domclass.compute_eigenvalues_from_DOM(content=body)
        self.report['eigenvalues'] = eigenvalues.tolist()

########NEW FILE########
__FILENAME__ = http_filtering_bypassing
# -*- encoding: utf-8 -*-
from twisted.python import usage

from ooni.utils import log
from ooni.utils import randomStr, randomSTR
from ooni.templates import tcpt

class UsageOptions(usage.Options):
    optParameters = [['backend', 'b', '127.0.0.1',
                        'The OONI backend that runs a TCP echo server'],
                    ['backendport', 'p', 80, 'Specify the port that the TCP echo server is running (should only be set for debugging)']]

class HTTPFilteringBypass(tcpt.TCPTest):
    name = "HTTPFilteringBypass"
    version = "0.1"
    authors = "xx"

    inputFile = ['file', 'f', None,
            'Specify a list of hostnames to use as inputs']

    usageOptions = UsageOptions
    requiredOptions = ['backend']
    requiresRoot = False
    requiresTor = False

    def setUp(self):
        self.port = int(self.localOptions['backendport'])
        self.address = self.localOptions['backend']
        self.report['tampering'] = None

    def check_for_manipulation(self, response, payload):
        log.debug("Checking if %s == %s" % (response, payload))
        if response != payload:
            self.report['tampering'] = True
        else:
            self.report['tampering'] = False

    def test_prepend_newline(self):
        payload = "\nGET / HTTP/1.1\n\r"
        payload += "Host: %s\n\r" % self.input

        d = self.sendPayload(payload)
        d.addCallback(self.check_for_manipulation, payload)
        return d

    def test_tab_trick(self):
        payload = "GET / HTTP/1.1\n\r"
        payload += "Host: %s\t\n\r" % self.input

        d = self.sendPayload(payload)
        d.addCallback(self.check_for_manipulation, payload)
        return d

    def test_subdomain_blocking(self):
        payload = "GET / HTTP/1.1\n\r"
        payload += "Host: %s\n\r" % randomStr(10) + '.' + self.input

        d = self.sendPayload(payload)
        d.addCallback(self.check_for_manipulation, payload)
        return d

    def test_fuzzy_domain_blocking(self):
        hostname_field = randomStr(10) + '.' + self.input + '.' + randomStr(10)
        payload = "GET / HTTP/1.1\n\r"
        payload += "Host: %s\n\r" % hostname_field

        d = self.sendPayload(payload)
        d.addCallback(self.check_for_manipulation, payload)
        return d

    def test_fuzzy_match_blocking(self):
        hostname_field = randomStr(10) + self.input + randomStr(10)
        payload = "GET / HTTP/1.1\n\r"
        payload += "Host: %s\n\r" % hostname_field

        d = self.sendPayload(payload)
        d.addCallback(self.check_for_manipulation, payload)
        return d

    def test_normal_request(self):
        payload = "GET / HTTP/1.1\n\r"
        payload += "Host: %s\n\r" % self.input

        d = self.sendPayload(payload)
        d.addCallback(self.check_for_manipulation, payload)
        return d


########NEW FILE########
__FILENAME__ = http_keyword_filtering
# -*- encoding: utf-8 -*-
#
# :authors: Arturo Filastò
# :licence: see LICENSE

from twisted.python import usage

from ooni.templates import httpt

class UsageOptions(usage.Options):
    optParameters = [['backend', 'b', 'http://127.0.0.1:57001',
                        'URL of the test backend to use']]

class HTTPKeywordFiltering(httpt.HTTPTest):
    """
    This test involves performing HTTP requests containing to be tested for
    censorship keywords.

    It does not detect censorship on the client, but just logs the response from the 
    HTTP backend server.
    """
    name = "HTTP Keyword Filtering"
    author = "Arturo Filastò"
    version = "0.1.1"

    inputFile = ['file', 'f', None, 'List of keywords to use for censorship testing']

    usageOptions = UsageOptions
    requiresTor = False
    requiresRoot = False

    requiredOptions = ['backend']

    def test_get(self):
        """
        Perform a HTTP GET request to the backend containing the keyword to be
        tested inside of the request body.
        """
        return self.doRequest(self.localOptions['backend'], method="GET", body=self.input)

    def test_post(self):
        """
        Perform a HTTP POST request to the backend containing the keyword to be
        tested inside of the request body.
        """
        return self.doRequest(self.localOptions['backend'], method="POST", body=self.input)


########NEW FILE########
__FILENAME__ = http_trix
# -*- encoding: utf-8 -*-
from twisted.python import usage

from ooni.utils import log
from ooni.utils import randomStr, randomSTR
from ooni.templates import tcpt

class UsageOptions(usage.Options):
    optParameters = [['backend', 'b', '127.0.0.1',
                        'The OONI backend that runs a TCP echo server'],
                    ['backendport', 'p', 80, 'Specify the port that the TCP echo server is running (should only be set for debugging)']]

class HTTPTrix(tcpt.TCPTest):
    name = "HTTPTrix"
    version = "0.1"
    authors = "Arturo Filastò"

    usageOptions = UsageOptions
    requiresTor = False
    requiresRoot = False
    requiredOptions = ['backend']

    def setUp(self):
        self.port = int(self.localOptions['backendport'])
        self.address = self.localOptions['backend']

    def check_for_manipulation(self, response, payload):
        log.debug("Checking if %s == %s" % (response, payload))
        if response != payload:
            self.report['tampering'] = True
        else:
            self.report['tampering'] = False

    def test_for_squid_cache_object(self):
        """
        This detects the presence of a squid transparent HTTP proxy by sending
        a request for cache_object://localhost/info.

        This tests for the presence of a Squid Transparent proxy by sending:

            GET cache_object://localhost/info HTTP/1.1
        """
        payload = 'GET cache_object://localhost/info HTTP/1.1'
        payload += '\n\r'

        d = self.sendPayload(payload)
        d.addCallback(self.check_for_manipulation, payload)
        return d


########NEW FILE########
__FILENAME__ = http_uk_mobile_networks
# -*- encoding: utf-8 -*-
import yaml

from twisted.python import usage
from twisted.plugin import IPlugin

from ooni.templates import httpt
from ooni.utils import log

class UsageOptions(usage.Options):
    """
    See https://github.com/hellais/ooni-inputs/processed/uk_mobile_networks_redirects.yaml 
    to see how the rules file should look like.
    """
    optParameters = [
                     ['rules', 'y', None, 
                    'Specify the redirect rules file ']
                    ]

class HTTPUKMobileNetworksTest(httpt.HTTPTest):
    """
    This test was thought of by Open Rights Group and implemented with the
    purpose of detecting censorship in the UK.
    For more details on this test see:
    https://trac.torproject.org/projects/tor/ticket/6437
    XXX port the knowledge from the trac ticket into this test docstring
    """
    name = "HTTP UK mobile network redirect test"

    usageOptions = UsageOptions

    followRedirects = True

    inputFile = ['urls', 'f', None, 'List of urls one per line to test for censorship']
    requiredOptions = ['urls']
    requiresRoot = False
    requiresTor = False

    def testPattern(self, value, pattern, type):
        if type == 'eq':
            return value == pattern
        elif type == 're':
            import re
            if re.match(pattern, value):
                return True
            else:
                return False
        else:
            return None

    def testPatterns(self, patterns, location):
        test_result = False

        if type(patterns) == list:
            for pattern in patterns:
                test_result |= self.testPattern(location, pattern['value'], pattern['type'])
        rules_file = self.localOptions['rules']

        return test_result

    def testRules(self, rules, location):
        result = {}
        blocked = False
        for rule, value in rules.items():
            current_rule = {}
            current_rule['name'] = value['name']
            current_rule['patterns'] = value['patterns']
            current_rule['test'] = self.testPatterns(value['patterns'], location)
            blocked |= current_rule['test']
            result[rule] = current_rule
        result['blocked'] = blocked
        return result

    def processRedirect(self, location):
        self.report['redirect'] = None
        rules_file = self.localOptions['rules']

        fp = open(rules_file)
        rules = yaml.safe_load(fp)
        fp.close()

        log.msg("Testing rules %s" % rules)
        redirect = self.testRules(rules, location)
        self.report['redirect'] = redirect

########NEW FILE########
__FILENAME__ = keyword_filtering
# -*- encoding: utf-8 -*-
#
# :authors: Arturo Filastò
# :licence: see LICENSE

from twisted.python import usage
from twisted.internet import defer

from ooni.utils import log
from ooni.templates import scapyt

from scapy.all import *

class UsageOptions(usage.Options):
    optParameters = [
                    ['backend', 'b', '127.0.0.1:57002', 'Test backend running TCP echo'],
                    ['timeout', 't', 5, 'Timeout after which to give up waiting for RST packets']
                    ]

class KeywordFiltering(scapyt.BaseScapyTest):
    name = "Keyword Filtering detection based on RST packets"
    author = "Arturo Filastò"
    version = "0.1"

    usageOptions = UsageOptions

    inputFile = ['file', 'f', None, 
            'List of keywords to use for censorship testing']
    requiresRoot = True
    requiresTor = False

    def test_tcp_keyword_filtering(self):
        """
        Places the keyword to be tested in the payload of a TCP packet.
        XXX need to implement bisection method for enumerating keywords.
            though this should not be an issue since we are testing all 
            the keywords in parallel.
        """
        def finished(packets):
            log.debug("Finished running TCP traceroute test on port %s" % port)
            answered, unanswered = packets
            self.report['rst_packets'] = []
            for snd, rcv in answered:
                # The received packet has the RST flag
                if rcv[TCP].flags == 4:
                    self.report['rst_packets'].append(rcv)

        backend_ip, backend_port = self.localOptions['backend']
        keyword_to_test = str(self.input)
        packets = IP(dst=backend_ip,id=RandShort())/TCP(dport=backend_port)/keyword_to_test
        d = self.sr(packets, timeout=timeout)
        d.addCallback(finished)
        return d


########NEW FILE########
__FILENAME__ = parasitictraceroute
from twisted.python import usage
from twisted.internet import defer, reactor
from ooni.templates import scapyt
from ooni.utils import log
from ooni.utils.txscapy import ParasiticTraceroute
from ooni.settings import config

from scapy.all import TCPerror, IPerror

class ParasiticTracerouteTest(scapyt.BaseScapyTest):
    name = "Parasitic Traceroute Test"
    description = "Injects duplicate TCP packets with varying TTL values by sniffing traffic"
    version = '0.1'

    samplePeriod = 40
    requiresTor = False
    requiresRoot = False

    def setUp(self):
        self.report['parasitic_traceroute'] = {}

    def test_parasitic_traceroute(self):
        self.pt = ParasiticTraceroute()
        config.scapyFactory.registerProtocol(self.pt)
        d = defer.Deferred()
        reactor.callLater(self.samplePeriod, d.callback, self.pt)
        return d

    def postProcessor(self, *args, **kwargs):
        self.pt.stopListening()
        self.report['received_packets'] = self.pt.received_packets

        for packet in self.pt.received_packets:
            k = (packet[IPerror].id, packet[TCPerror].sport, packet[TCPerror].dport, packet[TCPerror].seq)
            if k in self.pt.matched_packets:
                ttl = self.pt.matched_packets[k]['ttl']
            else:
                ttl = 'unknown'
            hop = (ttl, packet.src)
            path = 'hops_%s' % packet[IPerror].dst
            if path in self.report['parasitic_traceroute']:
               self.report['parasitic_traceroute'][path].append(hop)
            else:
               self.report['parasitic_traceroute'][path] = [hop]
        for p in self.report['parasitic_traceroute'].keys():
            self.report['parasitic_traceroute'][p].sort(key=lambda x: x[0])
                
        self.report['sent_packets'] = self.pt.sent_packets
        return self.report


########NEW FILE########
__FILENAME__ = script
from ooni import nettest
from ooni.utils import log
from twisted.internet import defer, protocol, reactor
from twisted.python import usage

import os


def which(program):
    def is_exe(fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    fpath, fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            path = path.strip('"')
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file
    return None


class UsageOptions(usage.Options):
    optParameters = [
        ['interpreter', 'i', '', 'The interpreter to use'],
        ['script', 's', '', 'The script to run']
    ]


class ScriptProcessProtocol(protocol.ProcessProtocol):
    def __init__(self, test_case):
        self.test_case = test_case
        self.deferred = defer.Deferred()

    def connectionMade(self):
        log.debug("connectionMade")
        self.transport.closeStdin()
        self.test_case.report['lua_output'] = ""

    def outReceived(self, data):
        log.debug('outReceived: %s' % data)
        self.test_case.report['lua_output'] += data

    def errReceived(self, data):
        log.err('Script error: %s' % data)
        self.transport.signalProcess('KILL')

    def processEnded(self, status):
        rc = status.value.exitCode
        log.debug('processEnded: %s, %s' % \
                  (rc, self.test_case.report['lua_output']))
        if rc == 0:
            self.deferred.callback(self)
        else:
            self.deferred.errback(rc)


# TODO: Maybe the script requires a back-end.
class Script(nettest.NetTestCase):
    name = "Script test"
    version = "0.1"
    authors = "Dominic Hamon"

    usageOptions = UsageOptions
    requiredOptions = ['interpreter', 'script']
    requiresRoot = False
    requiresTor = False

    def test_run_script(self):
        """
        We run the script specified in the usage options and take whatever
        is printed to stdout as the results of the test.
        """
        processProtocol = ScriptProcessProtocol(self)

        interpreter = self.localOptions['interpreter']
        if not which(interpreter):
            log.err('Unable to find %s executable in PATH.' % interpreter)
            return

        reactor.spawnProcess(processProtocol,
                             interpreter,
                             args=[interpreter, self.localOptions['script']],
                             env={'HOME': os.environ['HOME']},
                             usePTY=True)

        if not reactor.running:
            reactor.run()
        return processProtocol.deferred

########NEW FILE########
__FILENAME__ = squid
# -*- encoding: utf-8 -*-
#
# Squid transparent HTTP proxy detector
# *************************************
#
# :authors: Arturo Filastò
# :licence: see LICENSE

from ooni import utils
from ooni.utils import log
from ooni.templates import httpt

class SquidTest(httpt.HTTPTest):
    """
    This test aims at detecting the presence of a squid based transparent HTTP
    proxy. It also tries to detect the version number.
    """
    name = "Squid test"
    author = "Arturo Filastò"
    version = "0.1"

    optParameters = [['backend', 'b', 'http://ooni.nu/test/', 'Test backend to use']]

    #inputFile = ['urls', 'f', None, 'Urls file']
    inputs =['http://google.com']

    requiresRoot = False
    requiresTor = False

    def test_cacheobject(self):
        """
        This detects the presence of a squid transparent HTTP proxy by sending
        a request for cache_object://localhost/info.

        The response to this request will usually also contain the squid
        version number.
        """
        log.debug("Running")
        def process_body(body):
            if "Access Denied." in body:
                self.report['transparent_http_proxy'] = True
            else:
                self.report['transparent_http_proxy'] = False

        log.msg("Testing Squid proxy presence by sending a request for "\
                "cache_object")
        headers = {}
        #headers["Host"] = [self.input]
        self.report['trans_http_proxy'] = None
        method = "GET"
        body = "cache_object://localhost/info"
        return self.doRequest(self.localOptions['backend'], method=method, body=body,
                        headers=headers, body_processor=process_body)

    def test_search_bad_request(self):
        """
        Attempts to perform a request with a random invalid HTTP method.

        If we are being MITMed by a Transparent Squid HTTP proxy we will get
        back a response containing the X-Squid-Error header.
        """
        def process_headers(headers):
            log.debug("Processing headers in test_search_bad_request")
            if 'X-Squid-Error' in headers:
                log.msg("Detected the presence of a transparent HTTP "\
                        "squid proxy")
                self.report['trans_http_proxy'] = True
            else:
                log.msg("Did not detect the presence of transparent HTTP "\
                        "squid proxy")
                self.report['transparent_http_proxy'] = False

        log.msg("Testing Squid proxy presence by sending a random bad request")
        headers = {}
        #headers["Host"] = [self.input]
        method = utils.randomSTR(10, True)
        self.report['transparent_http_proxy'] = None
        return self.doRequest(self.localOptions['backend'], method=method,
                        headers=headers, headers_processor=process_headers)

    def test_squid_headers(self):
        """
        Detects the presence of a squid transparent HTTP proxy based on the
        response headers it adds to the responses to requests.
        """
        def process_headers(headers):
            """
            Checks if any of the headers that squid is known to add match the
            squid regexp.

            We are looking for something that looks like this:

                via: 1.0 cache_server:3128 (squid/2.6.STABLE21)
                x-cache: MISS from cache_server
                x-cache-lookup: MISS from cache_server:3128
            """
            squid_headers = {'via': r'.* \((squid.*)\)',
                        'x-cache': r'MISS from (\w+)',
                        'x-cache-lookup': r'MISS from (\w+:?\d+?)'
                        }

            self.report['transparent_http_proxy'] = False
            for key in squid_headers.keys():
                if key in headers:
                    log.debug("Found %s in headers" % key)
                    m = re.search(squid_headers[key], headers[key])
                    if m:
                        log.msg("Detected the presence of squid transparent"\
                                " HTTP Proxy")
                        self.report['transparent_http_proxy'] = True

        log.msg("Testing Squid proxy by looking at response headers")
        headers = {}
        #headers["Host"] = [self.input]
        method = "GET"
        self.report['transparent_http_proxy'] = None
        d = self.doRequest(self.localOptions['backend'], method=method,
                        headers=headers, headers_processor=process_headers)
        return d



########NEW FILE########
__FILENAME__ = tls_handshake
#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
  tls_handshake.py
  ----------------

  This file contains test cases for determining if a TLS handshake completes
  successfully, including ways to test if a TLS handshake which uses Mozilla
  Firefox's current ciphersuite list completes. Rather than using Twisted and
  OpenSSL's methods for automatically completing a handshake, which includes
  setting all the parameters, such as the ciphersuite list, these tests use
  non-blocking sockets and implement asychronous error-handling transversal of
  OpenSSL's memory BIO state machine, allowing us to determine where and why a
  handshake fails.

  This network test is a complete rewrite of a pseudonymously contributed
  script by Hackerberry Finn, in order to fit into OONI's core network tests.

  @authors: Isis Agora Lovecruft <isis@torproject.org>
  @license: see included LICENSE file
  @copyright: © 2013 Isis Lovecruft, The Tor Project Inc.
"""

from socket import error   as socket_error
from socket import timeout as socket_timeout
from socket import inet_aton as socket_inet_aton
from socket import gethostbyname as socket_gethostbyname
from time   import sleep

import os
import socket
import struct
import sys
import types

import ipaddr
import OpenSSL

from OpenSSL                import SSL, crypto
from twisted.internet       import defer, threads
from twisted.python         import usage, failure

from ooni       import nettest
from ooni.utils import log
from ooni.errors import InsufficientPrivileges
from ooni.settings import config

## For a way to obtain the current version of Firefox's default ciphersuite
## list, see https://trac.torproject.org/projects/tor/attachment/ticket/4744/
## and the attached file "get_mozilla_files.py".
##
## Note, however, that doing so requires the source code to the version of
## firefox that you wish to emulate.

firefox_ciphers = ["ECDHE-ECDSA-AES256-SHA",
                   "ECDHE-RSA-AES256-SHA",
                   "DHE-RSA-CAMELLIA256-SHA",
                   "DHE-DSS-CAMELLIA256-SHA",
                   "DHE-RSA-AES256-SHA",
                   "DHE-DSS-AES256-SHA",
                   "ECDH-ECDSA-AES256-CBC-SHA",
                   "ECDH-RSA-AES256-CBC-SHA",
                   "CAMELLIA256-SHA",
                   "AES256-SHA",
                   "ECDHE-ECDSA-RC4-SHA",
                   "ECDHE-ECDSA-AES128-SHA",
                   "ECDHE-RSA-RC4-SHA",
                   "ECDHE-RSA-AES128-SHA",
                   "DHE-RSA-CAMELLIA128-SHA",
                   "DHE-DSS-CAMELLIA128-SHA",]


class SSLContextError(usage.UsageError):
    """Raised when we're missing the SSL context method, or incompatible
    contexts were provided. The SSL context method should be one of the
    following:

        :attr:`OpenSSL.SSL.SSLv2_METHOD <OpenSSL.SSL.SSLv2_METHOD>`
        :attr:`OpenSSL.SSL.SSLv23_METHOD <OpenSSL.SSL.SSLv23_METHOD>`
        :attr:`OpenSSL.SSL.SSLv3_METHOD <OpenSSL.SSL.SSLv3_METHOD>`
        :attr:`OpenSSL.SSL.TLSv1_METHOD <OpenSSL.SSL.TLSv1_METHOD>`

    To use the pre-defined error messages, construct with one of the
    :meth:`SSLContextError.errors.keys <keys>` as the ``message`` string, like
    so:

        ``SSLContextError('NO_CONTEXT')``
    """

    #: Pre-defined error messages.
    errors = {
        'NO_CONTEXT': 'No SSL/TLS context chosen! Defaulting to TLSv1.',
        'INCOMPATIBLE': str("Testing TLSv1 (option '--tls1') is incompatible "
                            + "with testing SSL ('--ssl2' and '--ssl3')."),
        'MISSING_SSLV2': str("Your version of OpenSSL was compiled without "
                             + "support for SSLv2. This is normal on newer "
                             + "versions of OpenSSL, but it means that you "
                             + "will be unable to test SSLv2 handshakes "
                             + "without recompiling OpenSSL."), }

    def __init__(self, message):
        if message in self.errors.keys():
            message = self.errors[message]
        super(usage.UsageError, self).__init__(message)

class HostUnreachableError(Exception):
    """Raised when the host IP address appears to be unreachable."""
    pass

class HostUnresolveableError(Exception):
    """Raised when the host address appears to be unresolveable."""
    pass

class ConnectionTimeout(Exception):
    """Raised when we receive a :class:`socket.timeout <timeout>`, in order to
    pass the Exception along to
    :func:`TLSHandshakeTest.test_handshake.connectionFailed
    <connectionFailed>`.
    """
    pass

class HandshakeOptions(usage.Options):
    """ :class:`usage.Options <Options>` parser for the tls-handshake test."""
    optParameters = [
        ['host', 'h', None,
         'Remote host IP address (v4/v6) and port, i.e. "1.2.3.4:443"'],
        ['port', 'p', None,
         'Use this port for all hosts, regardless of port specified in file'],
        ['ciphersuite', 'c', None ,
         'File containing ciphersuite list, one per line'],]
    optFlags = [
        ['ssl2', '2', 'Use SSLv2'],
        ['ssl3', '3', 'Use SSLv3'],
        ['tls1', 't', 'Use TLSv1'],]

class HandshakeTest(nettest.NetTestCase):
    """An ooniprobe NetTestCase for determining if we can complete a TLS/SSL
    handshake with a remote host.
    """
    name         = 'tls-handshake'
    author       = 'Isis Lovecruft <isis@torproject.org>'
    description  = 'A test to determing if we can complete a TLS hankshake.'
    version      = '0.0.3'

    requiresRoot = False
    requiresTor  = False
    usageOptions = HandshakeOptions

    host = None
    inputFile = ['file', 'f', None, 'List of <HOST>:<PORT>s to test']

    #: Default SSL/TLS context method.
    context = SSL.Context(SSL.TLSv1_METHOD)

    def setUp(self, *args, **kwargs):
        """Set defaults for a :class:`HandshakeTest <HandshakeTest>`."""

        self.ciphers = list()

        if self.localOptions:
            options = self.localOptions

            ## check that we're testing an IP:PORT, else exit gracefully:
            if not (options['host']  or options['file']):
                raise SystemExit("Need --host or --file!")
            if options['host']:
                self.host = options['host']

            ## If no context was chosen, explain our default to the user:
            if not (options['ssl2'] or options['ssl3'] or options['tls1']):
                try: raise SSLContextError('NO_CONTEXT')
                except SSLContextError as sce: log.err(sce.message)
                context = None
            else:
                ## If incompatible contexts were chosen, inform the user:
                if options['tls1'] and (options['ssl2'] or options['ssl3']):
                    try: raise SSLContextError('INCOMPATIBLE')
                    except SSLContextError as sce: log.err(sce.message)
                    finally: log.msg('Defaulting to testing only TLSv1.')
                elif options['ssl2']:
                    try:
                        if not options['ssl3']:
                            context = SSL.Context(SSL.SSLv2_METHOD)
                        else:
                            context = SSL.Context(SSL.SSLv23_METHOD)
                    except ValueError as ve:
                        log.err(ve.message)
                        try: raise SSLContextError('MISSING_SSLV2')
                        except SSLContextError as sce:
                            log.err(sce.message)
                            log.msg("Falling back to testing only TLSv1.")
                            context = SSL.Context(SSL.TLSv1_METHOD)
                elif options['ssl3']:
                    context = SSL.Context(SSL.SSLv3_METHOD)
            ## finally, reset the context if the user's choice was okay:
            if context: self.context = context

            ## if we weren't given a file with a list of ciphersuites to use,
            ## then use the firefox default list:
            if not options['ciphersuite']:
                self.ciphers = firefox_ciphers
                log.msg('Using default Firefox ciphersuite list.')
            else:
                if os.path.isfile(options['ciphersuite']):
                    log.msg('Using ciphersuite list from "%s"'
                            % options['ciphersuite'])
                    with open(options['ciphersuite']) as cipherfile:
                        for line in cipherfile.readlines():
                            self.ciphers.append(line.strip())
            self.ciphersuite = ":".join(self.ciphers)

        if getattr(config.advanced, 'default_timeout', None) is not None:
            self.timeout = config.advanced.default_timeout
        else:
            self.timeout = 30   ## default the timeout to 30 seconds

        ## xxx For debugging, set the socket timeout higher anyway:
        self.timeout = 30

        ## We have to set the default timeout on our sockets before creation:
        socket.setdefaulttimeout(self.timeout)
    def isIP(self,addr):
        try:
            socket_inet_aton(addr)
            return True
        except socket_error:
            return False

    def resolveHost(self,addr):
        try:
            return socket_gethostbyname(addr)
        except socket_error:
            raise HostUnresolveableError

    def splitInput(self, input):
        addr, port = input.strip().rsplit(':', 1)

        #if addr is hostname it is resolved to ip
        if not self.isIP(addr):
            addr=self.resolveHost(addr)

        if self.localOptions['port']:
            port = self.localOptions['port']
        return (str(addr), int(port))

    def inputProcessor(self, file=None):
        if self.host:
            yield self.splitInput(self.host)
        if os.path.isfile(file):
            with open(file) as fh:
                for line in fh.readlines():
                    if line.startswith('#'):
                        continue
                    try:
                        yield self.splitInput(line)
                    except HostUnresolveableError:
                        continue

    def buildSocket(self, addr):
        global s
        ip = ipaddr.IPAddress(addr) ## learn if we're IPv4 or IPv6
        if ip.version == 4:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        elif ip.version == 6:
            s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        return s

    def getContext(self):
        self.context.set_cipher_list(self.ciphersuite)
        return self.context

    @staticmethod
    def getPeerCert(connection, get_chain=False):
        """Get the PEM-encoded certificate or cert chain of the remote host.

        :param connection: A :class:`OpenSSL.SSL.Connection <Connection>`.
        :param bool get_chain: If True, get the all certificates in the
            chain. Otherwise, only get the remote host's certificate.
        :returns: A PEM-encoded x509 certificate. If
            :param:`getPeerCert.get_chain <get_chain>` is True, returns a list
            of PEM-encoded x509 certificates.
        """
        if not get_chain:
            x509_cert = connection.get_peer_certificate()
            pem_cert = crypto.dump_certificate(crypto.FILETYPE_PEM, x509_cert)
            return pem_cert
        else:
            cert_chain = []
            x509_cert_chain = connection.get_peer_cert_chain()
            for x509_cert in x509_cert_chain:
                pem_cert = crypto.dump_certificate(crypto.FILETYPE_PEM,
                                                   x509_cert)
                cert_chain.append(pem_cert)
            return cert_chain

    @staticmethod
    def getX509Name(certificate, get_components=False):
        """Get the DER-encoded form of the Name fields of an X509 certificate.

        @param certificate: A :class:`OpenSSL.crypto.X509Name` object.
        @param get_components: A boolean. If True, returns a list of tuples of
                               the (name, value)s of each Name field in the
                               :param:`certificate`. If False, returns the DER
                               encoded form of the Name fields of the
                               :param:`certificate`.
        """
        x509_name = None

        try:
            assert isinstance(certificate, crypto.X509Name), \
                "getX509Name takes OpenSSL.crypto.X509Name as first argument!"
            x509_name = crypto.X509Name(certificate)
        except AssertionError as ae:
            log.err(ae)
        except Exception as exc:
            log.exception(exc)

        if not x509_name is None:
            if not get_components:
                return x509_name.der()
            else:
                return x509_name.get_components()
        else:
            log.debug("getX509Name: got None for ivar x509_name")

    @staticmethod
    def getPublicKey(key):
        """Get the PEM-encoded format of a host certificate's public key.

        :param key: A :class:`OpenSSL.crypto.PKey <crypto.PKey>` object.
        """
        try:
            assert isinstance(key, crypto.PKey), \
                "getPublicKey expects type OpenSSL.crypto.PKey for parameter key"
        except AssertionError as ae:
            log.err(ae)
        else:
            pubkey = crypto.dump_privatekey(crypto.FILETYPE_PEM, key)
            return pubkey

    def test_handshake(self):
        """xxx fill me in"""

        def makeConnection(host):
            """Create a socket to the remote host's IP address, then get the
            TLS/SSL context method and ciphersuite list. Lastly, initiate a
            connection to the host.

            :param tuple host: A tuple of the remote host's IP address as a
                string, and an integer specifying the remote host port, i.e.
                ('1.1.1.1',443)
            :raises: :exc:`ConnectionTimeout` if the socket timed out.
            :returns: A :class:`OpenSSL.SSL.Connection <Connection>`.
            """
            addr, port = host
            sckt = self.buildSocket(addr)
            context = self.getContext()
            connection = SSL.Connection(context, sckt)
            try:
               connection.connect(host)
            except socket_timeout as stmo:
               error = ConnectionTimeout(stmo.message)
               return failure.Failure(error)
            else:
               return connection

        def connectionFailed(connection, host):
            """Handle errors raised while attempting to create the socket and
            :class:`OpenSSL.SSL.Connection <Connection>`, and setting the
            TLS/SSL context.

            :type connection: :exc:Exception
            :param connection: The exception that was raised in
                :func:`HandshakeTest.test_handshake.makeConnection
                <makeConnection>`.
            :param tuple host: A tuple of the host IP address as a string, and
                an int specifying the host port, i.e. ('1.1.1.1', 443)
            :rtype: :exc:Exception
            :returns: The original exception.
            """
            addr, port = host

            if not isinstance(connection, SSL.Connection):
                if isinstance(connection, IOError):
                    ## On some *nix distros, /dev/random is 0600 root:root and
                    ## we get a permissions error when trying to read
                    if connection.message.find("[Errno 13]"):
                        raise InsufficientPrivileges(
                            "%s" % connection.message.split("[Errno 13]", 1)[1])
                elif isinstance(connection, socket_error):
                    if connection.message.find("[Errno 101]"):
                        raise HostUnreachableError(
                            "Host unreachable: %s:%s" % (addr, port))
                elif isinstance(connection, Exception):
                    log.debug("connectionFailed: got Exception:")
                    log.err("Connection failed with reason: %s"
                            % connection.message)
                else:
                    log.err("Connection failed with reason: %s" % str(connection))

            self.report['host'] = addr
            self.report['port'] = port
            self.report['state'] = 'CONNECTION_FAILED'

            return connection

        def connectionSucceeded(connection, host, timeout):
            """If we have created a connection, set the socket options, and log
            the connection state and peer name.

            :param connection: A :class:`OpenSSL.SSL.Connection <Connection>`.
            :param tuple host: A tuple of the remote host's IP address as a
                string, and an integer specifying the remote host port, i.e.
                ('1.1.1.1',443)
            """

            ## xxx TODO to get this to work with a non-blocking socket, see how
            ##     twisted.internet.tcp.Client handles socket objects.
            connection.setblocking(1)

            ## Set the timeout on the connection:
            ##
            ## We want to set SO_RCVTIMEO and SO_SNDTIMEO, which both are
            ## defined in the socket option definitions in <sys/socket.h>, and
            ## which both take as their value, according to socket(7), a
            ## struct timeval, which is defined in the libc manual:
            ## https://www.gnu.org/software/libc/manual/html_node/Elapsed-Time.html
            timeval = struct.pack('ll', int(timeout), 0)
            connection.setsockopt(socket.SOL_SOCKET, socket.SO_RCVTIMEO, timeval)
            connection.setsockopt(socket.SOL_SOCKET, socket.SO_SNDTIMEO, timeval)

            ## Set the connection state to client mode:
            connection.set_connect_state()

            peer_name, peer_port = connection.getpeername()
            if peer_name:
                log.msg("Connected to %s" % peer_name)
            else:
                log.debug("Couldn't get peer name from connection: %s" % host)
                log.msg("Connected to %s" % host)
            log.debug("Connection state: %s " % connection.state_string())

            return connection

        def connectionRenegotiate(connection, host, error_message):
            """Handle a server-initiated SSL/TLS handshake renegotiation.

            :param connection: A :class:`OpenSSL.SSL.Connection <Connection>`.
            :param tuple host: A tuple of the remote host's IP address as a
                string, and an integer specifying the remote host port, i.e.
                ('1.1.1.1',443)
            """

            log.msg("Server requested renegotiation from: %s" % host)
            log.debug("Renegotiation reason: %s" % error_message)
            log.debug("State: %s" % connection.state_string())

            if connection.renegotiate():
                log.debug("Renegotiation possible.")
                log.msg("Retrying handshake with %s..." % host)
                try:
                    connection.do_handshake()
                    while connection.renegotiate_pending():
                        log.msg("Renegotiation with %s in progress..." % host)
                        log.debug("State: %s" % connection.state_string())
                        sleep(1)
                    else:
                        log.msg("Renegotiation with %s complete!" % host)
                except SSL.WantReadError, wre:
                    connection = handleWantRead(connection)
                    log.debug("State: %s" % connection.state_string())
                except SSL.WantWriteError, wwe:
                    connection = handleWantWrite(connection)
                    log.debug("State: %s" % connection.state_string())
            return connection

        def connectionShutdown(connection, host):
            """Handle shutting down a :class:`OpenSSL.SSL.Connection
            <Connection>`, including correct handling of halfway shutdown
            connections.

            Calls to :meth:`OpenSSL.SSL.Connection.shutdown
            <Connection.shutdown()>` return a boolean value -- if the
            connection is already shutdown, it returns True, else it returns
            false. Thus we loop through a block which detects if the connection
            is an a partial shutdown state and corrects that if that is the
            case, else it waits for one second, then attempts shutting down the
            connection again.

            Detection of a partial shutdown state is done through
            :meth:`OpenSSL.SSL.Connection.get_shutdown
            <Connection.get_shutdown()>` which queries OpenSSL for a bitvector
            of the server and client shutdown states. For example, the binary
            string '0b00' is an open connection, and '0b10' is a partially
            closed connection that has been shutdown on the serverside.

            :param connection: A :class:`OpenSSL.SSL.Connection <Connection>`.
            :param tuple host: A tuple of the remote host's IP address as a
                string, and an integer specifying the remote host port, i.e.
                ('1.1.1.1',443)
            """

            peername, peerport = host

            if isinstance(connection, SSL.Connection):
                log.msg("Closing connection to %s:%d..." % (peername, peerport))
                while not connection.shutdown():
                    ## if the connection is halfway shutdown, we have to
                    ## wait for a ZeroReturnError on connection.recv():
                    if (bin(connection.get_shutdown()) == '0b01') \
                            or (bin(connection.get_shutdown()) == '0b10'):
                        try:
                            _read_buffer = connection.pending()
                            connection.recv(_read_buffer)
                        except SSL.ZeroReturnError, zre: continue
                    else:
                        sleep(1)
                else:
                    log.msg("Closed connection to %s:%d"
                            % (peername, peerport))
            elif isinstance(connection, types.NoneType):
                log.debug("connectionShutdown: got NoneType for connection")
                return
            else:
                log.debug("connectionShutdown: expected connection, got %r"
                          % connection.__repr__())

            return connection

        def handleWantRead(connection):
            """From OpenSSL memory BIO documentation on ssl_read():

                If the underlying BIO is blocking, SSL_read() will only
                return, once the read operation has been finished or an error
                occurred, except when a renegotiation take place, in which
                case a SSL_ERROR_WANT_READ may occur. This behaviour can be
                controlled with the SSL_MODE_AUTO_RETRY flag of the
                SSL_CTX_set_mode(3) call.

                If the underlying BIO is non-blocking, SSL_read() will also
                return when the underlying BIO could not satisfy the needs of
                SSL_read() to continue the operation. In this case a call to
                SSL_get_error(3) with the return value of SSL_read() will
                yield SSL_ERROR_WANT_READ or SSL_ERROR_WANT_WRITE. As at any
                time a re-negotiation is possible, a call to SSL_read() can
                also cause write operations!  The calling process then must
                repeat the call after taking appropriate action to satisfy the
                needs of SSL_read(). The action depends on the underlying
                BIO. When using a non-blocking socket, nothing is to be done,
                but select() can be used to check for the required condition.

            And from the OpenSSL memory BIO documentation on ssl_get_error():

                SSL_ERROR_WANT_READ, SSL_ERROR_WANT_WRITE

                The operation did not complete; the same TLS/SSL I/O function
                should be called again later. If, by then, the underlying BIO
                has data available for reading (if the result code is
                SSL_ERROR_WANT_READ) or allows writing data
                (SSL_ERROR_WANT_WRITE), then some TLS/SSL protocol progress
                will take place, i.e. at least part of an TLS/SSL record will
                be read or written. Note that the retry may again lead to a
                SSL_ERROR_WANT_READ or SSL_ERROR_WANT_WRITE condition. There
                is no fixed upper limit for the number of iterations that may
                be necessary until progress becomes visible at application
                protocol level.

                For socket BIOs (e.g. when SSL_set_fd() was used), select() or
                poll() on the underlying socket can be used to find out when
                the TLS/SSL I/O function should be retried.

                Caveat: Any TLS/SSL I/O function can lead to either of
                SSL_ERROR_WANT_READ and SSL_ERROR_WANT_WRITE. In particular,
                SSL_read() or SSL_peek() may want to write data and
                SSL_write() may want to read data. This is mainly because
                TLS/SSL handshakes may occur at any time during the protocol
                (initiated by either the client or the server); SSL_read(),
                SSL_peek(), and SSL_write() will handle any pending
                handshakes.

            Also, see http://stackoverflow.com/q/3952104
            """
            try:
                while connection.want_read():
                    self.state = connection.state_string()
                    log.debug("Connection to %s HAS want_read" % host)
                    _read_buffer = connection.pending()
                    log.debug("Rereading %d bytes..." % _read_buffer)
                    sleep(1)
                    rereceived = connection.recv(int(_read_buffer))
                    log.debug("Received %d bytes" % rereceived)
                    log.debug("State: %s" % connection.state_string())
                else:
                    self.state = connection.state_string()
                    peername, peerport = connection.getpeername()
                    log.debug("Connection to %s:%s DOES NOT HAVE want_read"
                              % (peername, peerport))
                    log.debug("State: %s" % connection.state_string())
            except SSL.WantWriteError, wwe:
                self.state = connection.state_string()
                log.debug("Got WantWriteError while handling want_read")
                log.debug("WantWriteError: %s" % wwe.message)
                log.debug("Switching to handleWantWrite()...")
                handleWantWrite(connection)
            return connection

        def handleWantWrite(connection):
            """See :func:HandshakeTest.test_hanshake.handleWantRead """
            try:
                while connection.want_write():
                    self.state = connection.state_string()
                    log.debug("Connection to %s HAS want_write" % host)
                    sleep(1)
                    resent = connection.send("o\r\n")
                    log.debug("Sent: %d" % resent)
                    log.debug("State: %s" % connection.state_string())
            except SSL.WantReadError, wre:
                self.state = connection.state_string()
                log.debug("Got WantReadError while handling want_write")
                log.debug("WantReadError: %s" % wre.message)
                log.debug("Switching to handleWantRead()...")
                handleWantRead(connection)
            return connection

        def doHandshake(connection):
            """Attempt a TLS/SSL handshake with the host.

            If, after the first attempt at handshaking, OpenSSL's memory BIO
            state machine does not report success, then try reading and
            writing from the connection, and handle any SSL_ERROR_WANT_READ or
            SSL_ERROR_WANT_WRITE which occurs.

            If multiple want_reads occur, then try renegotiation with the
            host, and start over. If multiple want_writes occur, then it is
            possible that the connection has timed out, and move on to the
            connectionShutdown step.

            :param connection: A :class:`OpenSSL.SSL.Connection <Connection>`.
            :ivar peername: The host IP address, as reported by
                :meth:`Connection.getpeername <connection.getpeername()>`.
            :ivar peerport: The host port, reported by
                :meth:`Connection.getpeername <connection.getpeername()>`.
            :ivar int sent: The number of bytes sent to to the remote host.
            :ivar int received: The number of bytes received from the remote
                                host.
            :ivar int _read_buffer: The max bytes that can be read from the
                                    connection.
            :returns: The :param:`doHandshake.connection <connection>` with
                      handshake completed, else the unhandled error that was
                      raised.
            """
            peername, peerport = connection.getpeername()

            try:
                log.msg("Attempting handshake: %s" % peername)
                connection.do_handshake()
            except OpenSSL.SSL.WantReadError() as wre:
                self.state = connection.state_string()
                log.debug("Handshake state: %s" % self.state)
                log.debug("doHandshake: WantReadError on first handshake attempt.")
                connection = handleWantRead(connection)
            except OpenSSL.SSL.WantWriteError() as wwe:
                self.state = connection.state_string()
                log.debug("Handshake state: %s" % self.state)
                log.debug("doHandshake: WantWriteError on first handshake attempt.")
                connection = handleWantWrite(connection)
            else:
                self.state = connection.state_string()

            if self.state == 'SSL negotiation finished successfully':
                ## jump to handshakeSuccessful and get certchain
                return connection
            else:
                sent = connection.send("o\r\n")
                self.state = connection.state_string()
                log.debug("Handshake state: %s" % self.state)
                log.debug("Transmitted %d bytes" % sent)

                _read_buffer = connection.pending()
                log.debug("Max bytes in receive buffer: %d" % _read_buffer)

                try:
                    received = connection.recv(int(_read_buffer))
                except SSL.WantReadError, wre:
                    if connection.want_read():
                        self.state = connection.state_string()
                        connection = handleWantRead(connection)
                    else:
                        ## if we still have an SSL_ERROR_WANT_READ, then try to
                        ## renegotiate
                        self.state = connection.state_string()
                        connection = connectionRenegotiate(connection,
                                                           connection.getpeername(),
                                                           wre.message)
                except SSL.WantWriteError, wwe:
                    self.state = connection.state_string()
                    log.debug("Handshake state: %s" % self.state)
                    if connection.want_write():
                        connection = handleWantWrite(connection)
                    else:
                        raise ConnectionTimeout("Connection to %s:%d timed out."
                                                % (peername, peerport))
                else:
                    log.msg("Received: %s" % received)
                    self.state = connection.state_string()
                    log.debug("Handshake state: %s" % self.state)

            return connection

        def handshakeSucceeded(connection):
            """Get the details from the server certificate, cert chain, and
            server ciphersuite list, and put them in our report.

            WARNING: do *not* do this:
            >>> server_cert.get_pubkey()
                <OpenSSL.crypto.PKey at 0x4985d28>
            >>> pk = server_cert.get_pubkey()
            >>> pk.check()
                Segmentation fault

            :param connection: A :class:`OpenSSL.SSL.Connection <Connection>`.
            :returns: :param:`handshakeSucceeded.connection <connection>`.
            """
            host, port = connection.getpeername()
            log.msg("Handshake with %s:%d successful!" % (host, port))

            server_cert = self.getPeerCert(connection)
            server_cert_chain = self.getPeerCert(connection, get_chain=True)

            renegotiations = connection.total_renegotiations()
            cipher_list    = connection.get_cipher_list()
            session_key    = connection.master_key()
            rawcert        = connection.get_peer_certificate()
            ## xxx TODO this hash needs to be formatted as SHA1, not long
            cert_subj_hash = rawcert.subject_name_hash()
            cert_serial    = rawcert.get_serial_number()
            cert_sig_algo  = rawcert.get_signature_algorithm()
            cert_subject   = self.getX509Name(rawcert.get_subject(),
                                              get_components=True)
            cert_issuer    = self.getX509Name(rawcert.get_issuer(),
                                              get_components=True)
            cert_pubkey    = self.getPublicKey(rawcert.get_pubkey())

            self.report['host'] = host
            self.report['port'] = port
            self.report['state'] = self.state
            self.report['renegotiations'] = renegotiations
            self.report['server_cert'] = server_cert
            self.report['server_cert_chain'] = \
                ''.join([cert for cert in server_cert_chain])
            self.report['server_ciphersuite'] = cipher_list
            self.report['cert_subject'] = cert_subject
            self.report['cert_subj_hash'] = cert_subj_hash
            self.report['cert_issuer'] = cert_issuer
            self.report['cert_public_key'] = cert_pubkey
            self.report['cert_serial_no'] = cert_serial
            self.report['cert_sig_algo'] = cert_sig_algo
            ## The session's master key is only valid for that session, and
            ## will allow us to decrypt any packet captures (if they were
            ## collected). Because we are not requesting URLs, only host:port
            ## (which would be visible in pcaps anyway, since the FQDN is
            ## never encrypted) I do not see a way for this to log any user or
            ## identifying information. Correct me if I'm wrong.
            self.report['session_key'] = session_key

            log.msg("Server certificate:\n\n%s" % server_cert)
            log.msg("Server certificate chain:\n\n%s"
                    % ''.join([cert for cert in server_cert_chain]))
            log.msg("Negotiated ciphersuite:\n%s"
                    % '\n\t'.join([cipher for cipher in cipher_list]))
            log.msg("Certificate subject: %s" % cert_subject)
            log.msg("Certificate subject hash: %d" % cert_subj_hash)
            log.msg("Certificate issuer: %s" % cert_issuer)
            log.msg("Certificate public key:\n\n%s" % cert_pubkey)
            log.msg("Certificate signature algorithm: %s" % cert_sig_algo)
            log.msg("Certificate serial number: %s" % cert_serial)
            log.msg("Total renegotiations: %d" % renegotiations)

            return connection

        def handshakeFailed(connection, host):
            """Handle a failed handshake attempt and report the failure reason.

            :type connection: :class:`twisted.python.failure.Failure <Failure>`
                or :exc:Exception
            :param connection: The failed connection.
            :param tuple host: A tuple of the remote host's IP address as a
                string, and an integer specifying the remote host port, i.e.
                ('1.1.1.1',443)
            :returns: None
            """
            addr, port = host
            log.msg("Handshake with %s:%d failed!" % host)

            self.report['host'] = host
            self.report['port'] = port

            if isinstance(connection, Exception) \
                    or isinstance(connection, ConnectionTimeout):
                log.msg("Handshake failed with reason: %s" % connection.message)
                self.report['state'] = connection.message
            elif isinstance(connection, failure.Failure):
                log.msg("Handshake failed with reason: Socket %s"
                        % connection.getErrorMessage())
                self.report['state'] = connection.getErrorMessage()
                ctmo = connection.trap(ConnectionTimeout)
                if ctmo == ConnectionTimeout:
                    connection.cleanFailure()
            else:
                log.msg("Handshake failed with reason: %s" % str(connection))
                if not 'state' in self.report.keys():
                    self.report['state'] = str(connection)

            return None

        def deferMakeConnection(host):
            return threads.deferToThread(makeConnection, self.input)

        if self.host and not self.input:
            self.input = self.splitInput(self.host)
        log.msg("Beginning handshake test for %s:%s" % self.input)

        connection = deferMakeConnection(self.input)
        connection.addCallbacks(connectionSucceeded, connectionFailed,
                                callbackArgs=[self.input, self.timeout],
                                errbackArgs=[self.input])

        handshake = defer.Deferred()
        handshake.addCallback(doHandshake)
        handshake.addCallbacks(handshakeSucceeded, handshakeFailed,
                               errbackArgs=[self.input])

        connection.chainDeferred(handshake)
        connection.addCallbacks(connectionShutdown, defer.passthru,
                                callbackArgs=[self.input])
        connection.addBoth(log.exception)

        return connection

########NEW FILE########
__FILENAME__ = captiveportal
# -*- coding: utf-8 -*-
# captiveportal
# *************
#
# This test is a collection of tests to detect the presence of a
# captive portal. Code is taken, in part, from the old ooni-probe,
# which was written by Jacob Appelbaum and Arturo Filastò.
#
# This module performs multiple tests that match specific vendor captive
# portal tests. This is a basic internet captive portal filter tester written
# for RECon 2011.
#
# Read the following URLs to understand the captive portal detection process
# for various vendors:
#
# http://technet.microsoft.com/en-us/library/cc766017%28WS.10%29.aspx
# http://blog.superuser.com/2011/05/16/windows-7-network-awareness/
# http://isc.sans.org/diary.html?storyid=10312&
# http://src.chromium.org/viewvc/chrome?view=rev&revision=74608
# http://code.google.com/p/chromium-os/issues/detail?3281ttp,
# http://crbug.com/52489
# http://crbug.com/71736
# https://bugzilla.mozilla.org/show_bug.cgi?id=562917
# https://bugzilla.mozilla.org/show_bug.cgi?id=603505
# http://lists.w3.org/Archives/Public/ietf-http-wg/2011JanMar/0086.html
# http://tools.ietf.org/html/draft-nottingham-http-portal-02
#
# :authors: Jacob Appelbaum, Arturo Filastò, Isis Lovecruft
# :license: see LICENSE for more details

import base64
import os
import random
import re
import string
from urlparse import urlparse

from twisted.names import error
from twisted.python import usage
from twisted.internet import defer, threads

from ooni import nettest
from ooni.templates import httpt, dnst
from ooni.utils import net
from ooni.utils import log

__plugoo__ = "captiveportal"
__desc__ = "Captive portal detection test"


class UsageOptions(usage.Options):
    optParameters = [['asset', 'a', None, 'Asset file'],
                     ['experiment-url', 'e', 'http://google.com/', 'Experiment URL'],
                     ['user-agent', 'u', random.choice(net.userAgents),
                      'User agent for HTTP requests']
    ]


class CaptivePortal(httpt.HTTPTest, dnst.DNSTest):
    """
    Compares content and status codes of HTTP responses, and attempts
    to determine if content has been altered.
    """

    name = "captiveportal"
    description = "Captive Portal Test"
    version = '0.3'
    author = "Isis Lovecruft"
    usageOptions = UsageOptions
    requiresRoot = False
    requiresTor = False

    @defer.inlineCallbacks
    def http_fetch(self, url, headers={}):
        """
        Parses an HTTP url, fetches it, and returns a response
        object.
        """
        url = urlparse(url).geturl()
        #XXX: HTTP Error 302: The HTTP server returned a redirect error that
        #would lead to an infinite loop.  The last 30x error message was: Found
        try:
            response = yield self.doRequest(url, "GET", headers)
            defer.returnValue(response)
        except Exception:
            log.err("HTTPError")
            defer.returnValue(None)

    @defer.inlineCallbacks
    def http_content_match_fuzzy_opt(self, experimental_url, control_result,
                                     headers=None, fuzzy=False):
        """
        Makes an HTTP request on port 80 for experimental_url, then
        compares the response_content of experimental_url with the
        control_result. Optionally, if the fuzzy parameter is set to
        True, the response_content is compared with a regex of the
        control_result. If the response_content from the
        experimental_url and the control_result match, returns True
        with the HTTP status code and headers; False, status code, and
        headers if otherwise.
        """

        if headers is None:
            default_ua = self.local_options['user-agent']
            headers = {'User-Agent': default_ua}

        response = yield self.http_fetch(experimental_url, headers)
        response_headers = response.headers

        response_content = response.body if response else None
        response_code = response.code if response else None
        if response_content is None:
            log.err("HTTP connection appears to have failed.")
            r = (False, False, False)
            defer.returnValue(r)

        if fuzzy:
            pattern = re.compile(control_result)
            match = pattern.search(response_content)
            log.msg("Fuzzy HTTP content comparison for experiment URL")
            log.msg("'%s'" % experimental_url)
            if not match:
                log.msg("does not match!")
                r = (False, response_code, response_headers)
                defer.returnValue(r)
            else:
                log.msg("and the expected control result yielded a match.")
                r = (True, response_code, response_headers)
                defer.returnValue(r)
        else:
            if str(response_content) != str(control_result):
                log.msg("HTTP content comparison of experiment URL")
                log.msg("'%s'" % experimental_url)
                log.msg("and the expected control result do not match.")
                r = (False, response_code, response_headers)
                defer.returnValue(r)
            else:
                r = (True, response_code, response_headers)
                defer.returnValue(r)

    def http_status_code_match(self, experiment_code, control_code):
        """
        Compare two HTTP status codes, returns True if they match.
        """
        return int(experiment_code) == int(control_code)

    def http_status_code_no_match(self, experiment_code, control_code):
        """
        Compare two HTTP status codes, returns True if they do not match.
        """
        return int(experiment_code) != int(control_code)

    @defer.inlineCallbacks
    def dns_resolve(self, hostname, nameserver=None):
        """
        Resolves hostname(s) though nameserver to corresponding
        address(es). hostname may be either a single hostname string,
        or a list of strings. If nameserver is not given, use local
        DNS resolver, and if that fails try using 8.8.8.8.
        """
        if isinstance(hostname, str):
            hostname = [hostname]

        response = []
        answer = None
        for hn in hostname:
            try:
                answer = yield self.performALookup(hn)
                if not answer:
                    answer = yield self.performALookup(hn, ('8.8.8.8', 53))
            except error.DNSNameError:
                log.msg("DNS resolution for %s returned NXDOMAIN" % hn)
                response.append('NXDOMAIN')
            except Exception:
                log.err("DNS Resolution failed")
            finally:
                if not answer:
                    defer.returnValue(response)
                for addr in answer:
                    response.append(addr)
        defer.returnValue(response)

    @defer.inlineCallbacks
    def dns_resolve_match(self, experiment_hostname, control_address):
        """
        Resolve experiment_hostname, and check to see that it returns
        an experiment_address which matches the control_address.  If
        they match, returns True and experiment_address; otherwise
        returns False and experiment_address.
        """
        experiment_address = yield self.dns_resolve(experiment_hostname)
        if not experiment_address:
            log.debug("dns_resolve() for %s failed" % experiment_hostname)
            ret = None, experiment_address
            defer.returnValue(ret)

        if len(set(experiment_address) & set([control_address])) > 0:
            ret = True, experiment_address
            defer.returnValue(ret)
        else:
            log.msg("DNS comparison of control '%s' does not" % control_address)
            log.msg("match experiment response '%s'" % experiment_address)
            ret = False, experiment_address
            defer.returnValue(ret)

    @defer.inlineCallbacks
    def get_auth_nameservers(self, hostname):
        """
        Many CPs set a nameserver to be used. Let's query that
        nameserver for the authoritative nameservers of hostname.

        The equivalent of:
        $ dig +short NS ooni.nu
        """
        auth_nameservers = yield self.performNSLookup(hostname)
        defer.returnValue(auth_nameservers)

    def hostname_to_0x20(self, hostname):
        """
        MaKEs yOur HOsTnaME lOoK LiKE THis.

        For more information, see:
        D. Dagon, et. al. "Increased DNS Forgery Resistance
        Through 0x20-Bit Encoding". Proc. CSS, 2008.
        """
        hostname_0x20 = ''
        for char in hostname:
            l33t = random.choice(['caps', 'nocaps'])
            if l33t == 'caps':
                hostname_0x20 += char.capitalize()
            else:
                hostname_0x20 += char.lower()
        return hostname_0x20

    @defer.inlineCallbacks
    def check_0x20_to_auth_ns(self, hostname, sample_size=None):
        """
        Resolve a 0x20 DNS request for hostname over hostname's
        authoritative nameserver(s), and check to make sure that
        the capitalization in the 0x20 request matches that of the
        response. Also, check the serial numbers of the SOA (Start
        of Authority) records on the authoritative nameservers to
        make sure that they match.

        If sample_size is given, a random sample equal to that number
        of authoritative nameservers will be queried; default is 5.
        """
        log.msg("")
        log.msg("Testing random capitalization of DNS queries...")
        log.msg("Testing that Start of Authority serial numbers match...")

        auth_nameservers = yield self.get_auth_nameservers(hostname)

        if sample_size is None:
            sample_size = 5
        res = yield self.dns_resolve(auth_nameservers)
        resolved_auth_ns = random.sample(res, sample_size)

        querynames = []
        answernames = []
        serials = []

        # Even when gevent monkey patching is on, the requests here
        # are sent without being 0x20'd, so we need to 0x20 them.
        hostname = self.hostname_to_0x20(hostname)

        for auth_ns in resolved_auth_ns:
            querynames.append(hostname)
            try:
                answer = yield self.performSOALookup(hostname, (auth_ns, 53))
            except Exception:
                continue
            for soa in answer:
                answernames.append(soa[0])
                serials.append(str(soa[1]))

        if len(set(querynames).intersection(answernames)) == 1:
            log.msg("Capitalization in DNS queries and responses match.")
            name_match = True
        else:
            log.msg("The random capitalization '%s' used in" % hostname)
            log.msg("DNS queries to that hostname's authoritative")
            log.msg("nameservers does not match the capitalization in")
            log.msg("the response.")
            name_match = False

        if len(set(serials)) == 1:
            log.msg("Start of Authority serial numbers all match.")
            serial_match = True
        else:
            log.msg("Some SOA serial numbers did not match the rest!")
            serial_match = False

        if name_match and serial_match:
            log.msg("Your DNS queries do not appear to be tampered.")
        elif name_match or serial_match:
            log.msg("Something is tampering with your DNS queries.")
        elif not name_match and not serial_match:
            log.msg("Your DNS queries are definitely being tampered with.")

        ret = {
            'result': name_match and serial_match,
            'name_match': name_match,
            'serial_match': serial_match,
            'querynames': querynames,
            'answernames': answernames,
            'SOA_serials': serials
        }
        defer.returnValue(ret)

    def get_random_url_safe_string(self, length):
        """
        Returns a random url-safe string of specified length, where
        0 < length <= 256. The returned string will always start with
        an alphabetic character.
        """
        if length <= 0:
            length = 1
        elif length > 256:
            length = 256

        random_string = ''
        while length > 0:
            random_string += random.choice(string.lowercase)
            length -= 1

        return random_string

    def get_random_hostname(self, length=None):
        """
        Returns a random hostname with SLD of specified length. If
        length is unspecified, length=32 is used.

        These *should* all resolve to NXDOMAIN. If they actually
        resolve to a box that isn't part of a captive portal that
        would be rather interesting.
        """
        if length is None:
            length = 32

        random_sld = self.get_random_url_safe_string(length)
        tld_list = ['.com', '.net', '.org', '.info', '.test', '.invalid']
        random_tld = random.choice(tld_list)
        random_hostname = random_sld + random_tld
        return random_hostname

    @defer.inlineCallbacks
    def compare_random_hostnames(self, hostname_count=None, hostname_length=None):
        """
        Get hostname_count number of random hostnames with SLD length
        of hostname_length, and then attempt DNS resolution. If no
        arguments are given, default to three hostnames of 32 bytes
        each. These random hostnames *should* resolve to NXDOMAIN,
        except in the case where a user is presented with a captive
        portal and remains unauthenticated, in which case the captive
        portal may return the address of the authentication page.

        If the cardinality of the intersection of the set of resolved
        random hostnames and the single element control set
        (['NXDOMAIN']) are equal to one, then DNS properly resolved.

        Returns true if only NXDOMAINs were returned, otherwise returns
        False with the relative complement of the control set in the
        response set.
        """
        if hostname_count is None:
            hostname_count = 3

        log.msg("Generating random hostnames...")
        log.msg("Resolving DNS for %d random hostnames..." % hostname_count)

        control = ['NXDOMAIN']
        responses = []

        for x in range(hostname_count):
            random_hostname = self.get_random_hostname(hostname_length)
            response_match, response_address = yield self.dns_resolve_match(random_hostname,
                                                                            control[0])
            for address in response_address:
                if response_match is False:
                    log.msg("Strangely, DNS resolution of the random hostname")
                    log.msg("%s actually points to %s"
                            % (random_hostname, response_address))
                    responses = responses + [address]
                else:
                    responses = responses + [address]

        intersection = set(responses) & set(control)
        relative_complement = set(responses) - set(control)
        r = set(responses)

        if len(intersection) == 1:
            log.msg("All %d random hostnames properly resolved to NXDOMAIN."
                    % hostname_count)
            ret = True, relative_complement
            defer.returnValue(ret)
        elif (len(intersection) == 0) and (len(r) > 1):
            log.msg("Something odd happened. Some random hostnames correctly")
            log.msg("resolved to NXDOMAIN, but several others resolved to")
            log.msg("to the following addresses: %s" % relative_complement)
            ret = False, relative_complement
            defer.returnValue(ret)
        elif (len(intersection) == 0) and (len(r) == 1):
            log.msg("All random hostnames resolved to the IP address ")
            log.msg("'%s', which is indicative of a captive portal." % r)
            ret = False, relative_complement
            defer.returnValue(ret)
        else:
            log.debug("Apparently, pigs are flying on your network, 'cause a")
            log.debug("bunch of hostnames made from 32-byte random strings")
            log.debug("just magically resolved to a bunch of random addresses.")
            log.debug("That is definitely highly improbable. In fact, my napkin")
            log.debug("tells me that the probability of just one of those")
            log.debug("hostnames resolving to an address is 1.68e-59, making")
            log.debug("it nearly twice as unlikely as an MD5 hash collision.")
            log.debug("Either someone is seriously messing with your network,")
            log.debug("or else you are witnessing the impossible. %s" % r)
            ret = False, relative_complement
            defer.returnValue(ret)

    @defer.inlineCallbacks
    def google_dns_cp_test(self):
        """
        Google Chrome resolves three 10-byte random hostnames.
        """
        subtest = "Google Chrome DNS-based"
        log.msg("Running the Google Chrome DNS-based captive portal test...")

        gmatch, google_dns_result = yield self.compare_random_hostnames(3, 10)
        ret = {
            'result': gmatch,
            'addresses': google_dns_result
        }

        if gmatch:
            log.msg("Google Chrome DNS-based captive portal test did not")
            log.msg("detect a captive portal.")
            defer.returnValue(ret)
        else:
            log.msg("Google Chrome DNS-based captive portal test believes")
            log.msg("you are in a captive portal, or else something very")
            log.msg("odd is happening with your DNS.")
            defer.returnValue(ret)

    @defer.inlineCallbacks
    def ms_dns_cp_test(self):
        """
        Microsoft "phones home" to a server which will always resolve
        to the same address.
        """
        subtest = "Microsoft NCSI DNS-based"

        log.msg("")
        log.msg("Running the Microsoft NCSI DNS-based captive portal")
        log.msg("test...")

        msmatch, ms_dns_result = yield self.dns_resolve_match("dns.msftncsi.com",
                                                              "131.107.255.255")
        ret = {
            'result': msmatch,
            'address': ms_dns_result
        }
        if msmatch:
            log.msg("Microsoft NCSI DNS-based captive portal test did not")
            log.msg("detect a captive portal.")
            defer.returnValue(ms_dns_result)
        else:
            log.msg("Microsoft NCSI DNS-based captive portal test ")
            log.msg("believes you are in a captive portal.")
            defer.returnValue(ms_dns_result)

    @defer.inlineCallbacks
    def run_vendor_dns_tests(self):
        """
        Run the vendor DNS tests.
        """
        report = {}
        report['google_dns_cp'] = yield self.google_dns_cp_test()
        report['ms_dns_cp'] = yield self.ms_dns_cp_test()
        defer.returnValue(report)

    @defer.inlineCallbacks
    def run_vendor_tests(self, *a, **kw):
        """
        These are several vendor tests used to detect the presence of
        a captive portal. Each test compares HTTP status code and
        content to the control results and has its own User-Agent
        string, in order to emulate the test as it would occur on the
        device it was intended for. Vendor tests are defined in the
        format:
        [exp_url, ctrl_result, ctrl_code, ua, test_name]
        """

        vendor_tests = [['http://www.apple.com/library/test/success.html',
                         'Success',
                         '200',
                         'Mozilla/5.0 (iPhone; U; CPU like Mac OS X; en) AppleWebKit/420+ (KHTML, like Gecko) Version/3.0 Mobile/1A543a Safari/419.3',
                         'Apple HTTP Captive Portal'],
                        ['http://tools.ietf.org/html/draft-nottingham-http-portal-02',
                         '428 Network Authentication Required',
                         '428',
                         'Mozilla/5.0 (Windows NT 6.1; rv:5.0) Gecko/20100101 Firefox/5.0',
                         'W3 Captive Portal'],
                        ['http://www.msftncsi.com/ncsi.txt',
                         'Microsoft NCSI',
                         '200',
                         'Microsoft NCSI',
                         'MS HTTP Captive Portal', ]]

        cm = self.http_content_match_fuzzy_opt
        sm = self.http_status_code_match
        snm = self.http_status_code_no_match

        @defer.inlineCallbacks
        def compare_content(status_func, fuzzy, experiment_url, control_result,
                            control_code, headers, test_name):
            log.msg("")
            log.msg("Running the %s test..." % test_name)

            content_match, experiment_code, experiment_headers = yield cm(experiment_url,
                                                                          control_result,
                                                                          headers, fuzzy)
            status_match = status_func(experiment_code, control_code)
            if status_match and content_match:
                log.msg("The %s test was unable to detect" % test_name)
                log.msg("a captive portal.")
                defer.returnValue(True)
            else:
                log.msg("The %s test shows that your network" % test_name)
                log.msg("is filtered.")
                defer.returnValue(False)

        result = {}
        for vt in vendor_tests:
            report = {}

            experiment_url = vt[0]
            control_result = vt[1]
            control_code = vt[2]
            headers = {'User-Agent': vt[3]}
            test_name = vt[4]

            args = (experiment_url, control_result, control_code, headers, test_name)

            if test_name == "MS HTTP Captive Portal":
                report['result'] = yield compare_content(sm, False, *args)

            elif test_name == "Apple HTTP Captive Portal":
                report['result'] = yield compare_content(sm, True, *args)

            elif test_name == "W3 Captive Portal":
                report['result'] = yield compare_content(snm, True, *args)

            else:
                log.err("Ooni is trying to run an undefined CP vendor test.")

            report['URL'] = experiment_url
            report['http_status_summary'] = control_result
            report['http_status_number'] = control_code
            report['User_Agent'] = vt[3]
            result[test_name] = report

        defer.returnValue(result)

    @defer.inlineCallbacks
    def control(self, experiment_result, args):
        """
        Compares the content and status code of the HTTP response for
        experiment_url with the control_result and control_code
        respectively. If the status codes match, but the experimental
        content and control_result do not match, fuzzy matching is enabled
        to determine if the control_result is at least included somewhere
        in the experimental content. Returns True if matches are found,
        and False if otherwise.
        """
        # XXX put this back to being parametrized
        #experiment_url = self.local_options['experiment-url']
        experiment_url = 'http://google.com/'
        control_result = 'XX'
        control_code = 200
        ua = self.local_options['user-agent']

        cm = self.http_content_match_fuzzy_opt
        sm = self.http_status_code_match
        snm = self.http_status_code_no_match

        log.msg("Running test for '%s'..." % experiment_url)
        content_match, experiment_code, experiment_headers = yield cm(experiment_url,
                                                                      control_result)
        status_match = sm(experiment_code, control_code)
        if status_match and content_match:
            log.msg("The test for '%s'" % experiment_url)
            log.msg("was unable to detect a captive portal.")

            self.report['result'] = True

        elif status_match and not content_match:
            log.msg("Retrying '%s' with fuzzy match enabled."
                    % experiment_url)
            fuzzy_match, experiment_code, experiment_headers = yield cm(experiment_url,
                                                                        control_result,
                                                                        fuzzy=True)
            if fuzzy_match:
                self.report['result'] = True
            else:
                log.msg("Found modified content on '%s'," % experiment_url)
                log.msg("which could indicate a captive portal.")

                self.report['result'] = False
        else:
            log.msg("The content comparison test for ")
            log.msg("'%s'" % experiment_url)
            log.msg("shows that your HTTP traffic is filtered.")

            self.report['result'] = False

    @defer.inlineCallbacks
    def test_captive_portal(self):
        """
        Runs the CaptivePortal(Test).

        CONFIG OPTIONS
        --------------

        If "do_captive_portal_vendor_tests" is set to "true", then vendor
        specific captive portal HTTP-based tests will be run.

        If "do_captive_portal_dns_tests" is set to "true", then vendor
        specific captive portal DNS-based tests will be run.

        If "check_dns_requests" is set to "true", then Ooni-probe will
        attempt to check that your DNS requests are not being tampered with
        by a captive portal.

        If "captive_portal" = "yourfilename.txt", then user-specified tests
        will be run.

        Any combination of the above tests can be run.
        """

        log.msg("")
        log.msg("Running vendor tests...")
        self.report['vendor_tests'] = yield self.run_vendor_tests()

        log.msg("")
        log.msg("Running vendor DNS-based tests...")
        self.report['vendor_dns_tests'] = yield self.run_vendor_dns_tests()

        log.msg("")
        log.msg("Checking that DNS requests are not being tampered...")
        self.report['check0x20'] = yield self.check_0x20_to_auth_ns('ooni.nu')

        log.msg("")
        log.msg("Captive portal test finished!")


########NEW FILE########
__FILENAME__ = daphne
# -*- encoding: utf-8 -*-
from twisted.python import usage
from twisted.internet import protocol, endpoints, reactor

from ooni import nettest
from ooni.kit import daphn3
from ooni.utils import log

class Daphn3ClientProtocol(daphn3.Daphn3Protocol):
    def nextStep(self):
        log.debug("Moving on to next step in the state walk")
        self.current_data_received = 0
        if self.current_step >= (len(self.steps) - 1):
            log.msg("Reached the end of the state machine")
            log.msg("Censorship fingerpint bisected!")
            step_idx, mutation_idx = self.factory.mutation
            log.msg("step_idx: %s | mutation_id: %s" % (step_idx, mutation_idx))
            #self.transport.loseConnection()
            if self.report:
                self.report['mutation_idx'] = mutation_idx
                self.report['step_idx'] = step_idx
            self.d.callback(None)
            return
        else:
            self.current_step += 1
        if self._current_step_role() == self.role:
            # We need to send more data because we are again responsible for
            # doing so.
            self.sendPayload()


class Daphn3ClientFactory(protocol.ClientFactory):
    protocol = daphn3.Daphn3Protocol
    mutation = [0,0]
    steps = None

    def buildProtocol(self, addr):
        p = self.protocol()
        p.steps = self.steps
        p.factory = self
        return p

    def startedConnecting(self, connector):
        log.msg("Started connecting %s" % connector)

    def clientConnectionFailed(self, reason, connector):
        log.err("We failed connecting the the OONIB")
        log.err("Cannot perform test. Perhaps it got blocked?")
        log.err("Please report this to tor-assistants@torproject.org")

    def clientConnectionLost(self, reason, connector):
        log.err("Daphn3 client connection lost")
        print reason

class daphn3Args(usage.Options):
    optParameters = [
                     ['host', 'h', '127.0.0.1', 'Target Hostname'],
                     ['port', 'p', 57003, 'Target port number']]

    optFlags = [['pcap', 'c', 'Specify that the input file is a pcap file'],
                ['yaml', 'y', 'Specify that the input file is a YAML file (default)']]

class daphn3Test(nettest.NetTestCase):

    name = "Daphn3"
    description = "Bisects the censors fingerprint by mutating the given input packets."
    usageOptions = daphn3Args
    inputFile = ['file', 'f', None, 
            'Specify the pcap or YAML file to be used as input to the test']

    #requiredOptions = ['file']
    requiresRoot = False
    requiresTor = False
    steps = None

    def inputProcessor(self, filename):
        """
        step_idx is the step in the packet exchange
        ex.
        [.X.] are packets sent by a client or a server

            client:  [.1.]        [.3.] [.4.]
            server:         [.2.]             [.5.]

        mutation_idx: is the sub index of the packet as in the byte of the
        packet at the step_idx that is to be mutated

        """
        if self.localOptions['pcap']:
            daphn3Steps = daphn3.read_pcap(filename)
        else:
            daphn3Steps = daphn3.read_yaml(filename)
        log.debug("Loaded these steps %s" % daphn3Steps)
        yield daphn3Steps

    def test_daphn3(self):
        host = self.localOptions['host']
        port = int(self.localOptions['port'])

        def failure(failure):
            log.msg("Failed to connect")
            self.report['censored'] = True
            self.report['mutation'] = 0
            raise Exception("Error in connection, perhaps the backend is censored")
            return

        def success(protocol):
            log.msg("Successfully connected")
            protocol.sendPayload()
            return protocol.d

        log.msg("Connecting to %s:%s" % (host, port))
        endpoint = endpoints.TCP4ClientEndpoint(reactor, host, port)
        daphn3_factory = Daphn3ClientFactory()
        daphn3_factory.steps = self.input
        daphn3_factory.report = self.report
        d = endpoint.connect(daphn3_factory)
        d.addErrback(failure)
        d.addCallback(success)
        return d


########NEW FILE########
__FILENAME__ = dns_spoof
# -*- encoding: utf-8 -*-
#
# :authors: Arturo Filastò
# :licence: see LICENSE

from twisted.internet import defer
from twisted.python import usage

from scapy.all import IP, UDP, DNS, DNSQR

from ooni.templates import scapyt
from ooni.utils import log


class UsageOptions(usage.Options):
    optParameters = [
        ['resolver', 'r', None,
         'Specify the resolver that should be used for DNS queries (ip:port)'],
        ['hostname', 'h', None, 'Specify the hostname of a censored site'],
        ['backend', 'b', None,
         'Specify the IP address of a good DNS resolver (ip:port)']]


class DNSSpoof(scapyt.ScapyTest):
    name = "DNS Spoof"
    description = "Used to validate if the type of censorship " \
                  "happening is DNS spoofing or not."
    author = "Arturo Filastò"
    version = "0.0.1"
    timeout = 2

    usageOptions = UsageOptions

    requiredTestHelpers = {'backend': 'dns'}
    requiredOptions = ['hostname', 'resolver']
    requiresRoot = True
    requiresTor = False

    def setUp(self):
        self.resolverAddr, self.resolverPort = self.localOptions[
            'resolver'].split(':')
        self.resolverPort = int(self.resolverPort)

        self.controlResolverAddr, self.controlResolverPort = self.localOptions[
            'backend'].split(':')
        self.controlResolverPort = int(self.controlResolverPort)

        self.hostname = self.localOptions['hostname']

    def postProcessor(self, report):
        """
        This is not tested, but the concept is that if the two responses
        match up then spoofing is occuring.
        """
        try:
            test_answer = report['test_a_lookup']['answered_packets'][0][1]
            control_answer = report['test_control_a_lookup'][
                'answered_packets'][0][1]
        except IndexError:
            self.report['spoofing'] = 'no_answer'
            return

        if test_answer[UDP] == control_answer[UDP]:
            self.report['spoofing'] = True
        else:
            self.report['spoofing'] = False
        return

    @defer.inlineCallbacks
    def test_a_lookup(self):
        question = IP(dst=self.resolverAddr)/UDP()
        question /= DNS(rd=1, qd=DNSQR(qtype="A",
                                       qclass="IN",
                                       qname=self.hostname))
        log.msg(
            "Performing query to %s with %s:%s" %
            (self.hostname, self.resolverAddr, self.resolverPort))
        yield self.sr1(question)

    @defer.inlineCallbacks
    def test_control_a_lookup(self):
        question = IP(dst=self.controlResolverAddr)/UDP() / \
            DNS(rd=1, qd=DNSQR(qtype="A", qclass="IN", qname=self.hostname))
        log.msg(
            "Performing query to %s with %s:%s" %
            (self.hostname,
             self.controlResolverAddr,
             self.controlResolverPort))
        yield self.sr1(question)

########NEW FILE########
__FILENAME__ = http_header_field_manipulation
# -*- encoding: utf-8 -*-
#
# :authors: Arturo Filastò
# :licence: see LICENSE

import random
import json
import yaml

from twisted.python import usage

from ooni.utils import log, net, randomStr
from ooni.templates import httpt
from ooni.utils.trueheaders import TrueHeaders


def random_capitalization(string):
    output = ""
    original_string = string
    string = string.swapcase()
    for i in range(len(string)):
        if random.randint(0, 1):
            output += string[i].swapcase()
        else:
            output += string[i]
    if original_string == output:
        return random_capitalization(output)
    else:
        return output


class UsageOptions(usage.Options):
    optParameters = [
        ['backend', 'b', None,
         'URL of the backend to use for sending the requests'],
        ['headers', 'h', None,
         'Specify a yaml formatted file from which to read '
         'the request headers to send']
        ]


class HTTPHeaderFieldManipulation(httpt.HTTPTest):

    """
    It performes HTTP requests with request headers that vary capitalization
    towards a backend. If the headers reported by the server differ from
    the ones we sent, then we have detected tampering.
    """
    name = "HTTP Header Field Manipulation"
    description = "Checks if the HTTP request the server " \
                  "sees is the same as the one that the client has created."
    author = "Arturo Filastò"
    version = "0.1.4"

    randomizeUA = False
    usageOptions = UsageOptions

    requiredTestHelpers = {'backend': 'http-return-json-headers'}
    requiredOptions = ['backend']
    requiresTor = False
    requiresRoot = False

    def get_headers(self):
        headers = {}
        if self.localOptions['headers']:
            try:
                f = open(self.localOptions['headers'])
            except IOError:
                raise Exception("Specified input file does not exist")
            content = ''.join(f.readlines())
            f.close()
            headers = yaml.safe_load(content)
            return headers
        else:
            # XXX generate these from a random choice taken from
            # whatheaders.com
            # http://s3.amazonaws.com/data.whatheaders.com/whatheaders-latest.xml.zip
            headers = {
                "User-Agent": [
                    random.choice(
                        net.userAgents)],
                "Accept": ["text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"],
                "Accept-Encoding": ["gzip,deflate,sdch"],
                "Accept-Language": ["en-US,en;q=0.8"],
                "Accept-Charset": ["ISO-8859-1,utf-8;q=0.7,*;q=0.3"],
                "Host": [
                    randomStr(15) +
                    '.com']}
            return headers

    def get_random_caps_headers(self):
        headers = {}
        normal_headers = self.get_headers()
        for k, v in normal_headers.items():
            new_key = random_capitalization(k)
            headers[new_key] = v
        return headers

    def processInputs(self):
        if self.localOptions['backend']:
            self.url = self.localOptions['backend']
        else:
            raise Exception("No backend specified")

    def processResponseBody(self, data):
        self.check_for_tampering(data)

    def check_for_tampering(self, data):
        """
        Here we do checks to verify if the request we made has been tampered
        with. We have 3 categories of tampering:

        *  **total** when the response is not a json object and therefore we were not
        able to reach the ooniprobe test backend

        *  **request_line_capitalization** when the HTTP Request line (e.x. GET /
        HTTP/1.1) does not match the capitalization we set.

        *  **header_field_number** when the number of headers we sent does not match
        with the ones the backend received

        *  **header_name_capitalization** when the header field names do not match
        those that we sent.

        *  **header_field_value** when the header field value does not match with the
        one we transmitted.
        """
        log.msg("Checking for tampering on %s" % self.url)

        self.report['tampering'] = {
            'total': False,
            'request_line_capitalization': False,
            'header_name_capitalization': False,
            'header_field_value': False,
            'header_field_number': False
        }
        try:
            response = json.loads(data)
        except ValueError:
            self.report['tampering']['total'] = True
            return

        request_request_line = "%s / HTTP/1.1" % self.request_method

        try:
            response_request_line = response['request_line']
            response_headers_dict = response['headers_dict']
        except KeyError:
            self.report['tampering']['total'] = True
            return

        if request_request_line != response_request_line:
            self.report['tampering']['request_line_capitalization'] = True

        request_headers = TrueHeaders(self.request_headers)
        diff = request_headers.getDiff(TrueHeaders(response_headers_dict),
                                       ignore=['Connection'])
        if diff:
            self.report['tampering']['header_field_name'] = True
        else:
            self.report['tampering']['header_field_name'] = False
        self.report['tampering']['header_name_diff'] = list(diff)
        log.msg("    total: %(total)s" % self.report['tampering'])
        log.msg(
            "    request_line_capitalization: %(request_line_capitalization)s" %
            self.report['tampering'])
        log.msg(
            "    header_name_capitalization: %(header_name_capitalization)s" %
            self.report['tampering'])
        log.msg(
            "    header_field_value: %(header_field_value)s" %
            self.report['tampering'])
        log.msg(
            "    header_field_number: %(header_field_number)s" %
            self.report['tampering'])

    def test_get_random_capitalization(self):
        self.request_method = random_capitalization("GET")
        self.request_headers = self.get_random_caps_headers()
        return self.doRequest(self.url, self.request_method,
                              headers=self.request_headers)

########NEW FILE########
__FILENAME__ = http_host
# -*- encoding: utf-8 -*-
#
# HTTP Host Test
# **************
#
# :authors: Arturo Filastò
# :licence: see LICENSE

import sys
import json
from twisted.internet import defer
from twisted.python import usage

from ooni.utils import randomStr

from ooni.utils import log
from ooni.templates import httpt


class UsageOptions(usage.Options):
    optParameters = [['backend', 'b', None,
                      'URL of the test backend to use. Should be \
                              listening on port 80 and be a \
                              HTTPReturnJSONHeadersHelper'],
                     ['content', 'c', None, 'The file to read \
                            from containing the content of a block page']]


class HTTPHost(httpt.HTTPTest):

    """
    This test performs various manipulations of the HTTP Host header field and
    attempts to detect which filter bypassing strategies will work against the
    censor.

    Usually this test should be run with a list of sites that are known to be
    blocked inside of a particular network to assess which filter evasion
    strategies will work.
    """
    name = "HTTP Host"
    description = "Tests a variety of different filter bypassing techniques " \
                  "based on the HTTP Host header field."
    author = "Arturo Filastò"
    version = "0.2.4"

    randomizeUA = False
    usageOptions = UsageOptions

    inputFile = ['file', 'f', None,
                 'List of hostnames to test for censorship']

    requiredTestHelpers = {'backend': 'http-return-json-headers'}
    requiredOptions = ['backend']
    requiresTor = False
    requiresRoot = False

    def setUp(self):
        self.report['transparent_http_proxy'] = False

    def check_for_censorship(self, body, test_name):
        """
        XXX this is to be filled in with either a domclass based classified or
        with a rule that will allow to detect that the body of the result is
        that of a censored site.
        """
        # If we don't see a json dict we know that something is wrong for
        # sure
        if not body.startswith("{"):
            log.msg("This does not appear to be JSON")
            self.report['transparent_http_proxy'] = True
            self.check_for_censorship(body)
            return
        try:
            content = json.loads(body)
        except:
            log.msg("The json does not parse, this is not what we expected")
            self.report['transparent_http_proxy'] = True
            self.check_for_censorship(body)
            return

        # We base the determination of the presence of a transparent HTTP
        # proxy on the basis of the response containing the json that is to be
        # returned by a HTTP Request Test Helper
        if 'request_headers' in content and \
                'request_line' in content and \
                'headers_dict' in content:
            log.msg("Found the keys I expected in %s" % content)
            self.report['transparent_http_proxy'] = self.report[
                'transparent_http_proxy'] | False
            self.report[test_name] = False
        else:
            log.msg("Did not find the keys I expected in %s" % content)
            self.report['transparent_http_proxy'] = True
            if self.localOptions['content']:
                self.report[test_name] = True
                censorship_page = open(self.localOptions['content'])
                response_page = iter(body.split("\n"))

                for censorship_line in censorship_page:
                    response_line = response_page.next()
                    if response_line != censorship_line:
                        self.report[test_name] = False
                        break

                censorship_page.close()

    @defer.inlineCallbacks
    def test_filtering_prepend_newline_to_method(self):
        test_name = sys._getframe().f_code.co_name.replace('test_', '')
        headers = {}
        headers["Host"] = [self.input]
        response = yield self.doRequest(self.localOptions['backend'],
                                        method="\nGET",
                                        headers=headers)
        self.check_for_censorship(response.body, test_name)

    @defer.inlineCallbacks
    def test_filtering_add_tab_to_host(self):
        test_name = sys._getframe().f_code.co_name.replace('test_', '')
        headers = {}
        headers["Host"] = [self.input + '\t']
        response = yield self.doRequest(self.localOptions['backend'],
                                        headers=headers)
        self.check_for_censorship(response.body, test_name)

    @defer.inlineCallbacks
    def test_filtering_of_subdomain(self):
        test_name = sys._getframe().f_code.co_name.replace('test_', '')
        headers = {}
        headers["Host"] = [randomStr(10) + '.' + self.input]
        response = yield self.doRequest(self.localOptions['backend'],
                                        headers=headers)
        self.check_for_censorship(response.body, test_name)

    @defer.inlineCallbacks
    def test_filtering_via_fuzzy_matching(self):
        test_name = sys._getframe().f_code.co_name.replace('test_', '')
        headers = {}
        headers["Host"] = [randomStr(10) + self.input + randomStr(10)]
        response = yield self.doRequest(self.localOptions['backend'],
                                        headers=headers)
        self.check_for_censorship(response.body, test_name)

    @defer.inlineCallbacks
    def test_send_host_header(self):
        """
        Stuffs the HTTP Host header field with the site to be tested for
        censorship and does an HTTP request of this kind to our backend.

        We randomize the HTTP User Agent headers.
        """
        test_name = sys._getframe().f_code.co_name.replace('test_', '')
        headers = {}
        headers["Host"] = [self.input]
        response = yield self.doRequest(self.localOptions['backend'],
                                        headers=headers)
        self.check_for_censorship(response.body, test_name)

    def inputProcessor(self, filename=None):
        """
        This inputProcessor extracts domain names from urls
        """
        if filename:
            fp = open(filename)
            for x in fp.readlines():
                yield x.strip().split('//')[-1].split('/')[0]
            fp.close()
        else:
            pass

########NEW FILE########
__FILENAME__ = http_invalid_request_line
# -*- encoding: utf-8 -*-
from twisted.python import usage

from ooni.utils import log
from ooni.utils import randomStr, randomSTR
from ooni.templates import tcpt


class UsageOptions(usage.Options):
    optParameters = [
        ['backend', 'b', None, 'The OONI backend that runs a TCP echo server'],
        ['backendport', 'p', 80,
         'Specify the port that the TCP echo server is running '
         '(should only be set for debugging)']]


class HTTPInvalidRequestLine(tcpt.TCPTest):

    """
    The goal of this test is to do some very basic and not very noisy fuzzing
    on the HTTP request line. We generate a series of requests that are not
    valid HTTP requests.

    Unless elsewhere stated 'Xx'*N refers to N*2 random upper or lowercase
    ascii letters or numbers ('XxXx' will be 4).
    """
    name = "HTTP Invalid Request Line"
    description = "Performs out of spec HTTP requests in the attempt to "\
                  "trigger a proxy error message."
    version = "0.2"
    authors = "Arturo Filastò"

    usageOptions = UsageOptions

    requiredTestHelpers = {'backend': 'tcp-echo'}
    requiredOptions = ['backend']
    requiresRoot = False
    requiresTor = False

    def setUp(self):
        self.port = int(self.localOptions['backendport'])
        self.address = self.localOptions['backend']
        self.report['tampering'] = False

    def check_for_manipulation(self, response, payload):
        log.debug("Checking if %s == %s" % (response, payload))
        if response != payload:
            self.report['tampering'] = True
        else:
            self.report['tampering'] = self.report['tampering'] | False

    def test_random_invalid_method(self):
        """
        We test sending data to a TCP echo server listening on port 80, if what
        we get back is not what we have sent then there is tampering going on.
        This is for example what squid will return when performing such
        request:

            HTTP/1.0 400 Bad Request
            Server: squid/2.6.STABLE21
            Date: Sat, 23 Jul 2011 02:22:44 GMT
            Content-Type: text/html
            Content-Length: 1178
            Expires: Sat, 23 Jul 2011 02:22:44 GMT
            X-Squid-Error: ERR_INVALID_REQ 0
            X-Cache: MISS from cache_server
            X-Cache-Lookup: NONE from cache_server:3128
            Via: 1.0 cache_server:3128 (squid/2.6.STABLE21)
            Proxy-Connection: close

        """
        payload = randomSTR(4) + " / HTTP/1.1\n\r"

        d = self.sendPayload(payload)
        d.addCallback(self.check_for_manipulation, payload)
        return d

    def test_random_invalid_field_count(self):
        """
        This generates a request that looks like this:

        XxXxX XxXxX XxXxX XxXxX

        This may trigger some bugs in the HTTP parsers of transparent HTTP
        proxies.
        """
        payload = ' '.join(randomStr(5) for x in range(4))
        payload += "\n\r"

        d = self.sendPayload(payload)
        d.addCallback(self.check_for_manipulation, payload)
        return d

    def test_random_big_request_method(self):
        """
        This generates a request that looks like this:

        Xx*512 / HTTP/1.1
        """
        payload = randomStr(1024) + ' / HTTP/1.1\n\r'

        d = self.sendPayload(payload)
        d.addCallback(self.check_for_manipulation, payload)
        return d

    def test_random_invalid_version_number(self):
        """
        This generates a request that looks like this:

        GET / HTTP/XxX
        """
        payload = 'GET / HTTP/' + randomStr(3)
        payload += '\n\r'

        d = self.sendPayload(payload)
        d.addCallback(self.check_for_manipulation, payload)
        return d

########NEW FILE########
__FILENAME__ = traceroute
# -*- encoding: utf-8 -*-

from twisted.python import usage

from ooni.templates import scapyt

from ooni.utils.txscapy import MPTraceroute
from ooni.settings import config


class UsageOptions(usage.Options):
    optParameters = [
                    ['backend', 'b', None, 'Test backend to use'],
                    ['timeout', 't', 5, 'The timeout for the traceroute test'],
                    ['maxttl', 'm', 30,
                     'The maximum value of ttl to set on packets'],
                    ['dstport', 'd', None,
                     'Specify a single destination port. May be repeated.'],
                    ['interval', 'i', None,
                     'Specify the inter-packet delay in seconds'],
                    ['numPackets', 'n', None,
                     'Specify the number of packets to send per hop'],
        ]


class Traceroute(scapyt.BaseScapyTest):
    name = "Traceroute"
    description = "Performs a UDP, TCP, ICMP traceroute with destination port number "\
                  "set to 0, 22, 23, 53, 80, 123, 443, 8080 and 65535"

    requiredTestHelpers = {'backend': 'traceroute'}
    requiresRoot = True
    requiresTor = False

    usageOptions = UsageOptions
    dst_ports = [0, 22, 23, 53, 80, 123, 443, 8080, 65535]
    version = "0.3"

    def setUp(self):
        self.st = MPTraceroute()
        if self.localOptions['maxttl']:
            self.st.ttl_max = int(self.localOptions['maxttl'])
        if self.localOptions['dstport']:
            self.st.dst_ports = [int(self.localOptions['dstport'])]
        if self.localOptions['interval']:
            self.st.interval = float(self.localOptions['interval'])

        config.scapyFactory.registerProtocol(self.st)

        self.report['test_tcp_traceroute'] = dict(
            [('hops_%d' % d, []) for d in self.dst_ports])
        self.report['test_udp_traceroute'] = dict(
            [('hops_%d' % d, []) for d in self.dst_ports])
        self.report['test_icmp_traceroute'] = {'hops': []}

    def test_icmp_traceroute(self):
        return self.st.ICMPTraceroute(self.localOptions['backend'])

    def test_tcp_traceroute(self):
        return self.st.TCPTraceroute(self.localOptions['backend'])

    def test_udp_traceroute(self):
        return self.st.UDPTraceroute(self.localOptions['backend'])

    def postProcessor(self, measurements):
        # should be called after all deferreds have calledback
        self.st.stopListening()
        self.st.matchResponses()

        if measurements[0][1].result == self.st:
            for packet in self.st.sent_packets:
                self.report['sent_packets'].append(packet)
            for packet in self.st.matched_packets.values():
                self.report['answered_packets'].extend(packet)

            for ttl in xrange(self.st.ttl_min, self.st.ttl_max):
                matchedPackets = filter(
                    lambda x: x.ttl == ttl,
                    self.st.matched_packets.keys())
                for packet in matchedPackets:
                    for response in self.st.matched_packets[packet]:
                        self.addToReport(packet, response)
        return self.report

    def addToReport(self, packet, response):
        if packet.proto == 1:
            self.report['test_icmp_traceroute']['hops'].append(
                {'ttl': packet.ttl, 'rtt': response.time - packet.time,
                 'address': response.src})
        elif packet.proto == 6:
            self.report['test_tcp_traceroute'][
                'hops_%s' % packet.dport].append(
                {'ttl': packet.ttl, 'rtt': response.time - packet.time,
                 'address': response.src, 'sport': response.sport})
        else:
            self.report['test_udp_traceroute'][
                'hops_%s' % packet.dport].append(
                {'ttl': packet.ttl, 'rtt': response.time - packet.time,
                 'address': response.src, 'sport': response.sport})

########NEW FILE########
__FILENAME__ = http_url_list
# -*- encoding: utf-8 -*-
#
# :authors: Arturo Filastò
# :licence: see LICENSE

from twisted.internet import defer
from twisted.python import usage
from ooni.templates import httpt
from ooni.utils import log

class UsageOptions(usage.Options):
    optParameters = [['content', 'c', None,
                        'The file to read from containing the content of a block page'],
                     ['url', 'u', None, 'Specify a single URL to test.']
                    ]

class HTTPURLList(httpt.HTTPTest):
    """
    Performs GET, POST and PUT requests to a list of URLs specified as
    input and checks if the page that we get back as a result matches that
    of a block page given as input.

    If no block page is given as input to the test it will simply collect the
    responses to the HTTP requests and write them to a report file.
    """
    name = "HTTP URL List"
    author = "Arturo Filastò"
    version = "0.1.3"

    usageOptions = UsageOptions

    requiresRoot = False
    requiresTor = False

    inputFile = ['file', 'f', None, 
            'List of URLS to perform GET and POST requests to']

    def setUp(self):
        """
        Check for inputs.
        """
        if self.input:
            self.url = self.input
        elif self.localOptions['url']:
            self.url = self.localOptions['url']
        else:
            raise Exception("No input specified")

    def check_for_content_censorship(self, body):
        """
        If we have specified what a censorship page looks like here we will
        check if the page we are looking at matches it.

        XXX this is not tested, though it is basically what was used to detect
        censorship in the palestine case.
        """
        self.report['censored'] = True

        censorship_page = open(self.localOptions['content']).xreadlines()
        response_page = iter(body.split("\n"))

        # We first allign the two pages to the first HTML tag (something
        # starting with <). This is useful so that we can give as input to this
        # test something that comes from the output of curl -kis
        # http://the_page/
        for line in censorship_page:
            if line.strip().startswith("<"):
                break
        for line in response_page:
            if line.strip().startswith("<"):
                break

        for censorship_line in censorship_page:
            try:
                response_line = response_page.next()
            except StopIteration:
                # The censored page and the response we got do not match in
                # length.
                self.report['censored'] = False
                break
            censorship_line = censorship_line.replace("\n", "")
            if response_line != censorship_line:
                self.report['censored'] = False

        censorship_page.close()

    def processResponseBody(self, body):
        if self.localOptions['content']:
            log.msg("Checking for censorship in response body")
            self.check_for_content_censorship(body)

    def test_get(self):
        return self.doRequest(self.url, method="GET")

    def test_post(self):
        return self.doRequest(self.url, method="POST")

    def test_put(self):
        return self.doRequest(self.url, method="PUT")

########NEW FILE########
__FILENAME__ = netalyzr
# -*- encoding: utf-8 -*-
#
# This is a wrapper around the Netalyzer Java command line client
#
# :authors: Jacob Appelbaum <jacob@appelbaum.net>
#           Arturo "hellais" Filastò <art@fuffa.org>
# :licence: see LICENSE

from ooni import nettest
from ooni.utils import log
import time
import os
from twisted.internet import reactor, threads, defer

class NetalyzrWrapperTest(nettest.NetTestCase):
    name = "NetalyzrWrapper"
    requiresRoot = False
    requiresTor = False

    def setUp(self):
        cwd = os.path.abspath(os.path.join(os.path.abspath(__file__), '..'))

        # XXX set the output directory to something more uniform
        outputdir = os.path.join(cwd, '..', '..')

        program_path = os.path.join(cwd, 'NetalyzrCLI.jar')
        program = "java -jar %s -d" % program_path

        test_token = time.asctime(time.gmtime()).replace(" ", "_").strip()

        self.output_file = os.path.join(outputdir,
                "NetalyzrCLI_" + test_token + ".out")
        self.output_file.strip()
        self.run_me = program + " 2>&1 >> " + self.output_file

    def blocking_call(self):
        try:
            result = threads.blockingCallFromThread(reactor, os.system, self.run_me) 
        except:
            log.debug("Netalyzr had an error, please see the log file: %s" % self.output_file)
        finally:
            self.clean_up()

    def clean_up(self):
        self.report['netalyzr_report'] = self.output_file
        log.debug("finished running NetalzrWrapper")
        log.debug("Please check %s for Netalyzr output" % self.output_file)

    def test_run_netalyzr(self):
        """
        This test simply wraps netalyzr and runs it from command line
        """
        log.msg("Running NetalyzrWrapper (this will take some time, be patient)")
        log.debug("with command '%s'" % self.run_me)
        # XXX we probably want to use a processprotocol here to obtain the
        # stdout from Netalyzr. This would allows us to visualize progress
        # (currently there is no progress because the stdout of os.system is
        # trapped by twisted) and to include the link to the netalyzr report
        # directly in the OONI report, perhaps even downloading it.
        reactor.callInThread(self.blocking_call)

########NEW FILE########
__FILENAME__ = oonibclient
import os
import json

from hashlib import sha256

from twisted.web.client import Agent
from twisted.internet import defer, reactor
from twisted.internet.endpoints import TCP4ClientEndpoint

from ooni import errors as e
from ooni.settings import config
from ooni.utils import log
from ooni.utils.net import BodyReceiver, StringProducer, Downloader
from ooni.utils.trueheaders import TrueHeadersSOCKS5Agent

class Collector(object):
    def __init__(self, address):
        self.address = address

        self.nettest_policy = None
        self.input_policy = None
    
    @defer.inlineCallbacks
    def loadPolicy(self):
        # XXX implement caching of policies
        oonibclient = OONIBClient(self.address)
        log.msg("Looking up nettest policy for %s" % self.address)
        self.nettest_policy = yield oonibclient.getNettestPolicy()
        log.msg("Looking up input policy for %s" % self.address)
        self.input_policy = yield oonibclient.getInputPolicy()

    def validateInput(self, input_hash):
        for i in self.input_policy:
            if i['id'] == input_hash:
                return True
        return False

    def validateNettest(self, nettest_name):
        for i in self.nettest_policy:
            if nettest_name == i['name']:
                return True
        return False

class OONIBClient(object):
    retries = 3

    def __init__(self, address):
        self.address = address

    def _request(self, method, urn, genReceiver, bodyProducer=None):
        address = self.address
        if self.address.startswith('httpo://'):
            address = self.address.replace('httpo://', 'http://')
            agent = TrueHeadersSOCKS5Agent(reactor,
                proxyEndpoint=TCP4ClientEndpoint(reactor, '127.0.0.1',
                    config.tor.socks_port))

        elif self.address.startswith('https://'):
            log.err("HTTPS based bouncers are currently not supported.")
            raise e.InvalidOONIBBouncerAddress

        elif self.address.startswith('http://'):
            log.msg("Warning using unencrypted collector")
            agent = Agent(reactor)

        attempts = 0

        finished = defer.Deferred()

        def perform_request(attempts):
            uri = address + urn
            headers = {}
            d = agent.request(method, uri, bodyProducer=bodyProducer)

            @d.addCallback
            def callback(response):
                try:
                    content_length = int(response.headers.getRawHeaders('content-length')[0])
                except:
                    content_length = None
                response.deliverBody(genReceiver(finished, content_length))

            def errback(err, attempts):
                # We we will recursively keep trying to perform a request until
                # we have reached the retry count.
                if attempts < self.retries:
                    log.err("Lookup failed. Retrying.")
                    attempts += 1
                    perform_request(attempts)
                else:
                    log.err("Failed. Giving up.")
                    finished.errback(err)
            d.addErrback(errback, attempts)

        perform_request(attempts)

        return finished

    def queryBackend(self, method, urn, query=None):
        bodyProducer = None
        if query:
            bodyProducer = StringProducer(json.dumps(query))
        
        def genReceiver(finished, content_length):
            def process_response(s):
                # If empty string then don't parse it.
                if not s:
                    return
                try:
                    response = json.loads(s)
                except ValueError:
                    raise e.get_error(None)
                if 'error' in response:
                    print "Got this backend error message %s" % response
                    log.err("Got this backend error message %s" % response)
                    raise e.get_error(response['error'])
                return response
            return BodyReceiver(finished, content_length, process_response)

        return self._request(method, urn, genReceiver, bodyProducer)

    def download(self, urn, download_path):

        def genReceiver(finished, content_length):
            return Downloader(download_path, finished, content_length)

        return self._request('GET', urn, genReceiver)
    
    def getNettestPolicy(self):
        pass

    def getInput(self, input_hash):
        from ooni.deck import InputFile
        input_file = InputFile(input_hash)
        if input_file.descriptorCached:
            return defer.succeed(input_file)
        else:
            d = self.queryBackend('GET', '/input/' + input_hash)

            @d.addCallback
            def cb(descriptor):
                input_file.load(descriptor)
                input_file.save()
                return input_file

            @d.addErrback
            def err(err):
                log.err("Failed to get descriptor for input %s" % input_hash)
                log.exception(err)

            return d

    def getInputList(self):
        return self.queryBackend('GET', '/input')

    def downloadInput(self, input_hash):
        from ooni.deck import InputFile
        input_file = InputFile(input_hash)

        if input_file.fileCached:
            return defer.succeed(input_file)
        else:
            d = self.download('/input/'+input_hash+'/file', input_file.cached_file)

            @d.addCallback
            def cb(res):
                input_file.verify()
                return input_file

            @d.addErrback
            def err(err):
                log.err("Failed to download the input file %s" % input_hash)
                log.exception(err)

            return d

    def getInputPolicy(self):
        return self.queryBackend('GET', '/policy/input')

    def getNettestPolicy(self):
        return self.queryBackend('GET', '/policy/nettest')

    def getDeckList(self):
        return self.queryBackend('GET', '/deck')

    def getDeck(self, deck_hash):
        from ooni.deck import Deck
        deck = Deck(deck_hash)
        if deck.descriptorCached:
            return defer.succeed(deck)
        else:
            d = self.queryBackend('GET', '/deck/' + deck_hash)

            @d.addCallback
            def cb(descriptor):
                deck.load(descriptor)
                deck.save()
                return deck

            @d.addErrback
            def err(err):
                log.err("Failed to get descriptor for deck %s" % deck_hash)
                print err
                log.exception(err)

            return d

    def downloadDeck(self, deck_hash):
        from ooni.deck import Deck
        deck = Deck(deck_hash)
        if deck.fileCached:
            return defer.succeed(deck)
        else:
            d = self.download('/deck/'+deck_hash+'/file', deck.cached_file)

            @d.addCallback
            def cb(res):
                deck.verify()
                return deck

            @d.addErrback
            def err(err):
                log.err("Failed to download the deck %s" % deck_hash)
                print err
                log.exception(err)

            return d

    @defer.inlineCallbacks
    def lookupTestCollector(self, test_name):
        try:
            test_collector = yield self.queryBackend('POST', '/bouncer',
                    query={'test-collector': test_name})
        except Exception:
            raise e.CouldNotFindTestCollector

        defer.returnValue(test_collector)

    @defer.inlineCallbacks
    def lookupTestHelpers(self, test_helper_names):
        try:

            test_helper = yield self.queryBackend('POST', '/bouncer', 
                            query={'test-helpers': test_helper_names})
        except Exception, exc:
            log.exception(exc)
            raise e.CouldNotFindTestHelper

        if not test_helper:
            raise e.CouldNotFindTestHelper

        defer.returnValue(test_helper)

########NEW FILE########
__FILENAME__ = oonicli
#-*- coding: utf-8 -*-

import sys
import os
import yaml

from twisted.python import usage
from twisted.python.util import spewer
from twisted.internet import defer

from ooni import errors, __version__

from ooni.settings import config
from ooni.director import Director
from ooni.deck import Deck, nettest_to_path
from ooni.reporter import YAMLReporter, OONIBReporter
from ooni.nettest import NetTestLoader

from ooni.utils import log, checkForRoot

class Options(usage.Options):
    synopsis = """%s [options] [path to test].py
    """ % (os.path.basename(sys.argv[0]),)

    longdesc = ("ooniprobe loads and executes a suite or a set of suites of"
                " network tests. These are loaded from modules, packages and"
                " files listed on the command line")

    optFlags = [["help", "h"],
                ["resume", "r"],
                ["no-collector", "n"],
                ["no-geoip", "g"],
                ["list", "s"],
                ["printdeck", "p"],
                ["verbose", "v"]
                ]

    optParameters = [["reportfile", "o", None, "report file name"],
                     ["testdeck", "i", None,
                         "Specify as input a test deck: a yaml file containing the tests to run and their arguments"],
                     ["collector", "c", None,
                         "Address of the collector of test results. This option should not be used, but you should always use a bouncer."],
                     ["bouncer", "b", 'httpo://nkvphnp3p6agi5qq.onion',
                         "Address of the bouncer for test helpers. default: httpo://nkvphnp3p6agi5qq.onion"],
                     ["logfile", "l", None, "log file name"],
                     ["pcapfile", "O", None, "pcap file name"],
                     ["configfile", "f", None,
                         "Specify a path to the ooniprobe configuration file"],
                     ["datadir", "d", None,
                         "Specify a path to the ooniprobe data directory"],
                     ["annotations", "a", None,
                         "Annotate the report with a key:value[, key:value] format."]
                     ]

    compData = usage.Completions(
        extraActions=[usage.CompleteFiles(
                "*.py", descr="file | module | package | TestCase | testMethod",
                repeat=True)],)

    tracer = None

    def __init__(self):
        self['test'] = None
        usage.Options.__init__(self)

    def opt_spew(self):
        """
        Print an insanely verbose log of everything that happens.  Useful
        when debugging freezes or locks in complex code.
        """
        sys.settrace(spewer)

    def opt_version(self):
        """
        Display the ooniprobe version and exit.
        """
        print "ooniprobe version:", __version__
        sys.exit(0)

    def parseArgs(self, *args):
        if self['testdeck'] or self['list']:
            return
        try:
            self['test_file'] = args[0]
            self['subargs'] = args[1:]
        except:
            raise usage.UsageError("No test filename specified!")

def parseOptions():
    print "WARNING: running ooniprobe involves some risk that varies greatly"
    print "         from country to country. You should be aware of this when"
    print "         running the tool. Read more about this in the manpage or README."
    cmd_line_options = Options()
    if len(sys.argv) == 1:
        cmd_line_options.getUsage()
    try:
        cmd_line_options.parseOptions()
    except usage.UsageError, ue:
        print cmd_line_options.getUsage()
        raise SystemExit, "%s: %s" % (sys.argv[0], ue)

    return dict(cmd_line_options)

def runWithDirector(logging=True, start_tor=True):
    """
    Instance the director, parse command line options and start an ooniprobe
    test!
    """
    global_options = parseOptions()
    config.global_options = global_options
    config.set_paths()
    config.initialize_ooni_home()
    config.read_config_file()
    if global_options['verbose']:
        config.advanced.debug = True
    if not start_tor:
        config.advanced.start_tor = False

    if logging:
        log.start(global_options['logfile'])

    if config.privacy.includepcap:
        try:
            checkForRoot()
        except errors.InsufficientPrivileges:
             log.err("Insufficient Privileges to capture packets."
                     " See ooniprobe.conf privacy.includepcap")
             sys.exit(2)

    director = Director()
    if global_options['list']:
        print "# Installed nettests"
        for net_test_id, net_test in director.getNetTests().items():
            print "* %s (%s/%s)" % (net_test['name'],
                                    net_test['category'],
                                    net_test['id'])
            print "  %s" % net_test['description']

        sys.exit(0)

    elif global_options['printdeck']:
        del global_options['printdeck']
        print "# Copy and paste the lines below into a test deck to run the specified test with the specified arguments"
        print yaml.safe_dump([{'options': global_options}]).strip()

        sys.exit(0)

    if global_options.get('annotations') is not None:
        annotations = {}
        for annotation in global_options["annotations"].split(","):
            pair = annotation.split(":")
            if len(pair) == 2:
                key = pair[0].strip()
                value = pair[1].strip()
                annotations[key] = value
            else:
                log.err("Invalid annotation: %s" % annotation)
                sys.exit(1)
        global_options["annotations"] = annotations

    #XXX: This should mean no bouncer either!
    if global_options['no-collector']:
        log.msg("Not reporting using a collector")
        collector = global_options['collector'] = None
        global_options['bouncer'] = None

    deck = Deck()
    deck.bouncer = global_options['bouncer']
    start_tor = deck.requiresTor
    if global_options['bouncer']:
        start_tor = True
    if global_options['collector']:
        start_tor = True

    try:
        if global_options['testdeck']:
            deck.loadDeck(global_options['testdeck'])
        else:
            log.debug("No test deck detected")
            test_file = nettest_to_path(global_options['test_file'], True)
            net_test_loader = NetTestLoader(global_options['subargs'],
                    test_file=test_file)
            deck.insert(net_test_loader)
    except errors.MissingRequiredOption, option_name:
        log.err('Missing required option: "%s"' % option_name)
        print net_test_loader.usageOptions().getUsage()
        sys.exit(2)
    except errors.NetTestNotFound, path:
        log.err('Requested NetTest file not found (%s)' % path)
        sys.exit(3)
    except usage.UsageError, e:
        log.err(e)
        print net_test_loader.usageOptions().getUsage()
        sys.exit(4)
    except Exception as e:
        log.err(e)
        sys.exit(5)

    d = director.start(start_tor=start_tor)

    def setup_nettest(_):
        try:
            return deck.setup()
        except errors.UnableToLoadDeckInput as error:
            return defer.failure.Failure(error)

    def director_startup_failed(failure):
        log.err("Failed to start the director")
        r = failure.trap(errors.TorNotRunning,
                errors.InvalidOONIBCollectorAddress,
                errors.UnableToLoadDeckInput, errors.CouldNotFindTestHelper,
                errors.CouldNotFindTestCollector, errors.ProbeIPUnknown,
                errors.InvalidInputFile)

        if isinstance(failure.value, errors.TorNotRunning):
            log.err("Tor does not appear to be running")
            log.err("Reporting with the collector %s is not possible" %
                    global_options['collector'])
            log.msg("Try with a different collector or disable collector reporting with -n")

        elif isinstance(failure.value, errors.InvalidOONIBCollectorAddress):
            log.err("Invalid format for oonib collector address.")
            log.msg("Should be in the format http://<collector_address>:<port>")
            log.msg("for example: ooniprobe -c httpo://nkvphnp3p6agi5qq.onion")

        elif isinstance(failure.value, errors.UnableToLoadDeckInput):
            log.err("Unable to fetch the required inputs for the test deck.")
            log.msg("Please file a ticket on our issue tracker: https://github.com/thetorproject/ooni-probe/issues")

        elif isinstance(failure.value, errors.CouldNotFindTestHelper):
            log.err("Unable to obtain the required test helpers.")
            log.msg("Try with a different bouncer or check that Tor is running properly.")

        elif isinstance(failure.value, errors.CouldNotFindTestCollector):
            log.err("Could not find a valid collector.")
            log.msg("Try with a different bouncer, specify a collector with -c or disable reporting to a collector with -n.")

        elif isinstance(failure.value, errors.ProbeIPUnknown):
            log.err("Failed to lookup probe IP address.")
            log.msg("Check your internet connection.")

        elif isinstance(failure.value, errors.InvalidInputFile):
            log.err("Invalid input file \"%s\"" % failure.value)

        if config.advanced.debug:
            log.exception(failure)

    # Wait until director has started up (including bootstrapping Tor)
    # before adding tests
    def post_director_start(_):
        for net_test_loader in deck.netTestLoaders:
            # Decks can specify different collectors
            # for each net test, so that each NetTest
            # may be paired with a test_helper and its collector
            # However, a user can override this behavior by
            # specifying a collector from the command-line (-c).
            # If a collector is not specified in the deck, or the
            # deck is a singleton, the default collector set in
            # ooniprobe.conf will be used

            collector = None
            if not global_options['no-collector']:
                if global_options['collector']:
                    collector = global_options['collector']
                elif 'collector' in config.reports and config.reports['collector']:
                    collector = config.reports['collector']
                elif net_test_loader.collector:
                    collector = net_test_loader.collector

            if collector and collector.startswith('httpo:') \
                    and (not (config.tor_state or config.tor.socks_port)):
                raise errors.TorNotRunning

            test_details = net_test_loader.testDetails
            test_details['annotations'] = global_options['annotations']

            yaml_reporter = YAMLReporter(test_details,
                                         report_filename=global_options['reportfile'])
            reporters = [yaml_reporter]

            if collector:
                log.msg("Reporting using collector: %s" % collector)
                try:
                    oonib_reporter = OONIBReporter(test_details, collector)
                    reporters.append(oonib_reporter)
                except errors.InvalidOONIBCollectorAddress, e:
                    raise e

            netTestDone = director.startNetTest(net_test_loader, reporters)
        return director.allTestsDone

    def start():
        d.addCallback(setup_nettest)
        d.addCallback(post_director_start)
        d.addErrback(director_startup_failed)
        return d

    return start()

########NEW FILE########
__FILENAME__ = oonid
import os
import random

from twisted.application import service, internet
from twisted.web import static, server

from ooni.settings import config
from ooni.api.spec import oonidApplication
from ooni.director import Director
from ooni.reporter import YAMLReporter, OONIBReporter

def getOonid():
    director = Director()
    director.start()
    oonidApplication.director = director
    return internet.TCPServer(int(config.advanced.oonid_api_port), oonidApplication)

application = service.Application("ooniprobe")
service = getOonid()
service.setServiceParent(application)

########NEW FILE########
__FILENAME__ = otime
import time
from datetime import datetime

def utcDateNow():
    """
    Returns the datetime object of the current UTC time.
    """
    return datetime.utcnow()

def utcTimeNow():
    """
    Returns seconds since epoch in UTC time, it's of type float.
    """
    return time.mktime(time.gmtime())

def dateToTime(date):
    """
    Takes as input a datetime object and outputs the seconds since epoch.
    """
    return time.mktime(date.timetuple())

def prettyDateNow():
    """
    Returns a good looking string for the local time.
    """
    return datetime.now().ctime()

def utcPrettyDateNow():
    """
    Returns a good looking string for utc time.
    """
    return datetime.utcnow().ctime()

def timeToPrettyDate(time_val):
    return time.ctime(time_val)

class InvalidTimestampFormat(Exception):
    pass

def fromTimestamp(s):
    """
    Converts a string that is output from the timestamp function back to a
    datetime object

    Args:
        s (str): a ISO8601 formatted string.
            ex. 1912-06-23T101234Z"

    Note: we currently only support parsing strings that are generated from the
        timestamp function and have no intention in supporting the full standard.
    """
    try:
        date_part, time_part = s.split('T')
        hours, minutes, seconds = time_part[:2], time_part[2:4], time_part[4:6]
        year, month, day = date_part.split('-')
    except:
        raise InvalidTimestampFormat(s)

    return datetime(int(year), int(month), int(day), int(hours), int(minutes),
            int(seconds))

def timestamp(t=None):
    """
    The timestamp for ooni reports follows ISO 8601 in
    UTC time format.
    We do not inlcude ':' and include seconds.

    Example:

        if the current date is "10:12:34 AM, June 23 1912" (datetime(1912, 6,
            23, 10, 12, 34))

        the timestamp will be:

           "1912-06-23T101234Z"

    Args:
        t (datetime): a datetime object representing the
            time to be represented (*MUST* be expressed
            in UTC).

        If not specified will default to the current time
        in UTC.
    """
    if not t:
        t = datetime.utcnow()
    ISO8601 = "%Y-%m-%dT%H%M%SZ"
    return t.strftime(ISO8601)

def epochToTimestamp(seconds):
    return timestamp(datetime.utcfromtimestamp(seconds))

########NEW FILE########
__FILENAME__ = ratelimiting
class RateLimiter(object):
    """
    The abstract class that imposes limits over how measurements are scheduled,
    how retries are handled and when we should be giving up on a certain
    measurement.
    """
    @property
    def timeout(self):
        """
        After what timeout a certain test should be considered to have failed
        and attempt a retry if the maximum retry has not been reached.
        """
        raise NotImplemented

    @property
    def maxTimeout(self):
        """
        This is the maximum value that timeout can reach.
        """
        raise NotImplemented

    @property
    def concurrency(self):
        """
        How many concurrent requests should happen at the same time.
        """
        raise NotImplemented

    def timedOut(self, measurement):
        raise NotImplemented

    def completed(self, measurement):
        raise NotImplemented

    def failed(self, measurement):
        raise NotImplemented

class StaticRateLimiter(RateLimiter):
    """
    This is a static ratelimiter that returns constant values.
    """
    @property
    def timeout(self):
        return 10

    @property
    def maxTimeout(self):
        return 5 * 60

    @property
    def concurrency(self):
        return 10

    def timedOut(self, measurement):
        pass

    def completed(self, measurement):
        pass

    def failed(self, measurement, failure):
        pass

class TimeoutRateLimiter(RateLimiter):
    pass

class BandwidthRateLimiter(RateLimiter):
    pass


########NEW FILE########
__FILENAME__ = reporter
import time
import yaml
import json
import os
import re

from yaml.representer import *
from yaml.emitter import *
from yaml.serializer import *
from yaml.resolver import *
from twisted.python.util import untilConcludes
from twisted.internet import defer
from twisted.internet.error import ConnectionRefusedError
from twisted.python.failure import Failure
from twisted.internet.endpoints import TCP4ClientEndpoint

from ooni.utils import log
from ooni.tasks import Measurement
try:
    from scapy.packet import Packet
except ImportError:
    log.err("Scapy is not installed.")
    class Packet(object):
        pass

from ooni import errors

from ooni import otime
from ooni.utils import pushFilenameStack
from ooni.utils.net import BodyReceiver, StringProducer

from ooni.settings import config

from ooni.tasks import ReportEntry, ReportTracker
class ReporterException(Exception):
    pass

def createPacketReport(packet_list):
    """
    Takes as input a packet a list.

    Returns a dict containing a dict with the packet
    summary and the raw packet.
    """
    report = []
    for packet in packet_list:
        report.append({'raw_packet': str(packet),
            'summary': str([packet])})
    return report

class OSafeRepresenter(SafeRepresenter):
    """
    This is a custom YAML representer that allows us to represent reports
    safely.
    It extends the SafeRepresenter to be able to also represent complex
    numbers and scapy packet.
    """
    def represent_data(self, data):
        """
        This is very hackish. There is for sure a better way either by using
        the add_multi_representer or add_representer, the issue though lies in
        the fact that Scapy packets are metaclasses that leads to
        yaml.representer.get_classobj_bases to not be able to properly get the
        base of class of a Scapy packet.
        XXX fully debug this problem
        """
        if isinstance(data, Packet):
            data = createPacketReport(data)
        return SafeRepresenter.represent_data(self, data)

    def represent_complex(self, data):
        if data.imag == 0.0:
            data = u'%r' % data.real
        elif data.real == 0.0:
            data = u'%rj' % data.imag
        elif data.imag > 0:
            data = u'%r+%rj' % (data.real, data.imag)
        else:
            data = u'%r%rj' % (data.real, data.imag)
        return self.represent_scalar(u'tag:yaml.org,2002:python/complex', data)

OSafeRepresenter.add_representer(complex,
                                 OSafeRepresenter.represent_complex)

class OSafeDumper(Emitter, Serializer, OSafeRepresenter, Resolver):
    """
    This is a modification of the YAML Safe Dumper to use our own Safe
    Representer that supports complex numbers.
    """
    def __init__(self, stream,
            default_style=None, default_flow_style=None,
            canonical=None, indent=None, width=None,
            allow_unicode=None, line_break=None,
            encoding=None, explicit_start=None, explicit_end=None,
            version=None, tags=None):
        Emitter.__init__(self, stream, canonical=canonical,
                indent=indent, width=width,
                allow_unicode=allow_unicode, line_break=line_break)
        Serializer.__init__(self, encoding=encoding,
                explicit_start=explicit_start, explicit_end=explicit_end,
                version=version, tags=tags)
        OSafeRepresenter.__init__(self, default_style=default_style,
                default_flow_style=default_flow_style)
        Resolver.__init__(self)

class NoTestIDSpecified(Exception):
    pass

def safe_dump(data, stream=None, **kw):
    """
    Safely dump to a yaml file the specified data.
    """
    return yaml.dump_all([data], stream, Dumper=OSafeDumper, **kw)

class OReporter(object):
    def __init__(self, test_details):
        self.testDetails = test_details

    def createReport(self):
        """
        Override this with your own logic to implement tests.
        """
        raise NotImplemented

    def writeReportEntry(self, entry):
        """
        Takes as input an entry and writes a report for it.
        """
        raise NotImplemented

    def finish(self):
        pass

    def testDone(self, test, test_name):
        # XXX put this inside of Report.close
        # or perhaps put something like this inside of netTestDone
        log.msg("Finished running %s" % test_name)
        test_report = dict(test.report)

        if isinstance(test.input, Packet):
            test_input = createPacketReport(test.input)
        else:
            test_input = test.input

        test_report['input'] = test_input
        test_report['test_name'] = test_name
        test_report['test_started'] = test._start_time
        test_report['test_runtime'] = time.time() - test._start_time

        return defer.maybeDeferred(self.writeReportEntry, test_report)

class InvalidDestination(ReporterException):
    pass

class YAMLReporter(OReporter):
    """
    These are useful functions for reporting to YAML format.

    report_destination:
        the destination directory of the report

    """
    def __init__(self, test_details, report_destination='.', report_filename=None):
        self.reportDestination = report_destination

        if not os.path.isdir(report_destination):
            raise InvalidDestination

        if not report_filename:
            report_filename = "report-" + \
                              test_details['test_name'] + "-" + \
                              otime.timestamp() + ".yamloo"

        report_path = os.path.join(self.reportDestination, report_filename)

        if os.path.exists(report_path):
            log.msg("Report already exists with filename %s" % report_path)
            pushFilenameStack(report_path)

        self.report_path = report_path
        OReporter.__init__(self, test_details)

    def _writeln(self, line):
        self._write("%s\n" % line)

    def _write(self, format_string, *args):
        if not self._stream:
            raise errors.ReportNotCreated
        if self._stream.closed:
            raise errors.ReportAlreadyClosed
        s = str(format_string)
        assert isinstance(s, type(''))
        if args:
            self._stream.write(s % args)
        else:
            self._stream.write(s)
        untilConcludes(self._stream.flush)

    def writeReportEntry(self, entry):
        log.debug("Writing report with YAML reporter")
        self._write('---\n')
        if isinstance(entry, Measurement):
            self._write(safe_dump(entry.testInstance.report))
        elif isinstance(entry, Failure):
            self._write(entry.value)
        elif isinstance(entry, dict):
            self._write(safe_dump(entry))
        self._write('...\n')

    def createReport(self):
        """
        Writes the report header and fire callbacks on self.created
        """
        log.debug("Creating %s" % self.report_path)
        self._stream = open(self.report_path, 'w+')

        self._writeln("###########################################")

        self._writeln("# OONI Probe Report for %s (%s)" % (self.testDetails['test_name'],
                    self.testDetails['test_version']))
        self._writeln("# %s" % otime.prettyDateNow())
        self._writeln("###########################################")

        self.writeReportEntry(self.testDetails)

    def finish(self):
        self._stream.close()

def collector_supported(collector_address):
    if collector_address.startswith('httpo') \
            and (not (config.tor_state or config.tor.socks_port)):
        return False
    return True

class OONIBReporter(OReporter):
    def __init__(self, test_details, collector_address):
        self.collectorAddress = collector_address
        self.validateCollectorAddress()

        self.reportID = None

        OReporter.__init__(self, test_details)

    def validateCollectorAddress(self):
        """
        Will raise :class:ooni.errors.InvalidOONIBCollectorAddress an exception
        if the oonib reporter is not valid.
        """
        regexp = '^(http|httpo):\/\/[a-zA-Z0-9\-\.]+(:\d+)?$'
        if not re.match(regexp, self.collectorAddress):
            raise errors.InvalidOONIBCollectorAddress

    @defer.inlineCallbacks
    def writeReportEntry(self, entry):
        log.debug("Writing report with OONIB reporter")
        content = '---\n'
        if isinstance(entry, Measurement):
            content += safe_dump(entry.testInstance.report)
        elif isinstance(entry, Failure):
            content += entry.value
        elif isinstance(entry, dict):
            content += safe_dump(entry)
        content += '...\n'

        url = self.collectorAddress + '/report'

        request = {'report_id': self.reportID,
                'content': content}

        log.debug("Updating report with id %s (%s)" % (self.reportID, url))
        request_json = json.dumps(request)
        log.debug("Sending %s" % request_json)

        bodyProducer = StringProducer(json.dumps(request))

        try:
            response = yield self.agent.request("PUT", url,
                                bodyProducer=bodyProducer)
        except:
            # XXX we must trap this in the runner and make sure to report the
            # data later.
            log.err("Error in writing report entry")
            raise errors.OONIBReportUpdateError

    @defer.inlineCallbacks
    def createReport(self):
        """
        Creates a report on the oonib collector.
        """
        # XXX we should probably be setting this inside of the constructor,
        # however config.tor.socks_port is not set until Tor is started and the
        # reporter is instantiated before Tor is started. We probably want to
        # do this with some deferred kung foo or instantiate the reporter after
        # tor is started.

        from txsocksx.http import SOCKS5Agent
        from twisted.internet import reactor

        if self.collectorAddress.startswith('httpo://'):
            self.collectorAddress = \
                    self.collectorAddress.replace('httpo://', 'http://')
            self.agent = SOCKS5Agent(reactor,
                    proxyEndpoint=TCP4ClientEndpoint(reactor, '127.0.0.1',
                        config.tor.socks_port))

        elif self.collectorAddress.startswith('https://'):
            # XXX add support for securely reporting to HTTPS collectors.
            log.err("HTTPS based collectors are currently not supported.")

        url = self.collectorAddress + '/report'

        content = '---\n'
        content += safe_dump(self.testDetails)
        content += '...\n'

        request = {'software_name': self.testDetails['software_name'],
            'software_version': self.testDetails['software_version'],
            'probe_asn': self.testDetails['probe_asn'],
            'test_name': self.testDetails['test_name'],
            'test_version': self.testDetails['test_version'],
            'input_hashes': self.testDetails['input_hashes'],
            # XXX there is a bunch of redundancy in the arguments getting sent
            # to the backend. This may need to get changed in the client and the
            # backend.
            'content': content
        }

        log.msg("Reporting %s" % url)
        request_json = json.dumps(request)
        log.debug("Sending %s" % request_json)

        bodyProducer = StringProducer(json.dumps(request))

        log.msg("Creating report with OONIB Reporter. Please be patient.")
        log.msg("This may take up to 1-2 minutes...")

        try:
            response = yield self.agent.request("POST", url,
                                bodyProducer=bodyProducer)
        except ConnectionRefusedError:
            log.err("Connection to reporting backend failed (ConnectionRefusedError)")
            raise errors.OONIBReportCreationError

        except errors.HostUnreachable:
            log.err("Host is not reachable (HostUnreachable error")
            raise errors.OONIBReportCreationError

        except Exception, e:
            log.err("Failed to connect to reporter backend")
            log.exception(e)
            raise errors.OONIBReportCreationError

        # This is a little trix to allow us to unspool the response. We create
        # a deferred and call yield on it.
        response_body = defer.Deferred()
        response.deliverBody(BodyReceiver(response_body))

        backend_response = yield response_body

        try:
            parsed_response = json.loads(backend_response)
        except Exception, e:
            log.err("Failed to parse collector response %s" % backend_response)
            log.exception(e)
            raise errors.OONIBReportCreationError

        if response.code == 406:
            # XXX make this more strict
            log.err("The specified input or nettests cannot be submitted to this collector.")
            log.msg("Try running a different test or try reporting to a different collector.")
            raise errors.OONIBReportCreationError

        self.reportID = parsed_response['report_id']
        self.backendVersion = parsed_response['backend_version']
        log.debug("Created report with id %s" % parsed_response['report_id'])

    @defer.inlineCallbacks
    def finish(self):
        url = self.collectorAddress + '/report/' + self.reportID + '/close'
        log.debug("Closing the report %s" % url)
        response = yield self.agent.request("POST", str(url))

class ReportClosed(Exception):
    pass

class Report(object):
    def __init__(self, reporters, reportEntryManager):
        """
        This is an abstraction layer on top of all the configured reporters.

        It allows to lazily write to the reporters that are to be used.

        Args:

            reporters:
                a list of :class:ooni.reporter.OReporter instances

            reportEntryManager:
                an instance of :class:ooni.tasks.ReportEntryManager
        """
        self.reporters = reporters

        self.done = defer.Deferred()
        self.reportEntryManager = reportEntryManager

        self._reporters_openned = 0
        self._reporters_written = 0
        self._reporters_closed = 0

    def open(self):
        """
        This will create all the reports that need to be created and fires the
        created callback of the reporter whose report got created.
        """
        all_openned = defer.Deferred()

        def are_all_openned():
            if len(self.reporters) == self._reporters_openned:
                all_openned.callback(self._reporters_openned)

        for reporter in self.reporters[:]:

            def report_created(result):
                log.debug("Created report with %s" % reporter)
                self._reporters_openned += 1
                are_all_openned()

            def report_failed(failure):
                try:
                    self.failedOpeningReport(failure, reporter)
                except errors.NoMoreReporters, e:
                    all_openned.errback(defer.fail(e))
                else:
                    are_all_openned()
                return

            d = defer.maybeDeferred(reporter.createReport)
            d.addCallback(report_created)
            d.addErrback(report_failed)

        return all_openned

    def write(self, measurement):
        """
        Will return a deferred that will fire once the report for the specified
        measurement have been written to all the reporters.

        Args:

            measurement:
                an instance of :class:ooni.tasks.Measurement

        Returns:
            a deferred that will fire once all the report entries have
            been written or errbacks when no more reporters
        """

        all_written = defer.Deferred()
        report_tracker = ReportTracker(self.reporters)

        for reporter in self.reporters[:]:
            def report_completed(task):
                report_tracker.completed()
                if report_tracker.finished():
                    all_written.callback(report_tracker)

            def report_failed(failure):
                log.debug("Report Write Failure")
                try:
                    report_tracker.failedReporters.append(reporter)
                    self.failedWritingReport(failure, reporter)
                except errors.NoMoreReporters, e:
                    log.err("No More Reporters!")
                    all_written.errback(defer.fail(e))
                else:
                    report_tracker.completed()
                    if report_tracker.finished():
                        all_written.callback(report_tracker)
                return

            report_entry_task = ReportEntry(reporter, measurement)
            self.reportEntryManager.schedule(report_entry_task)

            report_entry_task.done.addCallback(report_completed)
            report_entry_task.done.addErrback(report_failed)

        return all_written

    def failedWritingReport(self, failure, reporter):
        """
        This errback gets called every time we fail to write a report.
        By fail we mean that the number of retries has exceeded.
        Once a report has failed to be written with a reporter we give up and
        remove the reporter from the list of reporters to write to.
        """

        # XXX: may have been removed already by another failure.
        if reporter in self.reporters:
            log.err("Failed to write to %s reporter, giving up..." % reporter)
            self.reporters.remove(reporter)
        else:
            log.err("Failed to write to (already) removed reporter %s" % reporter)

        # Don't forward the exception unless there are no more reporters
        if len(self.reporters) == 0:
            log.err("Removed last reporter %s" % reporter)
            raise errors.NoMoreReporters
        return

    def failedOpeningReport(self, failure, reporter):
        """
        This errback get's called every time we fail to create a report.
        By fail we mean that the number of retries has exceeded.
        Once a report has failed to be created with a reporter we give up and
        remove the reporter from the list of reporters to write to.
        """
        log.err("Failed to open %s reporter, giving up..." % reporter)
        log.err("Reporter %s failed, removing from report..." % reporter)
        #log.exception(failure)
        if reporter in self.reporters:
            self.reporters.remove(reporter)
        # Don't forward the exception unless there are no more reporters
        if len(self.reporters) == 0:
            log.err("Removed last reporter %s" % reporter)
            raise errors.NoMoreReporters
        return

    def close(self):
        """
        Close the report by calling it's finish method.

        Returns:
            a :class:twisted.internet.defer.DeferredList that will fire when
            all the reports have been closed.

        """
        all_closed = defer.Deferred()

        for reporter in self.reporters[:]:
            def report_closed(result):
                self._reporters_closed += 1
                if len(self.reporters) == self._reporters_closed:
                    all_closed.callback(self._reporters_closed)

            def report_failed(failure):
                log.err("Failed closing report")
                log.exception(failure)

            d = defer.maybeDeferred(reporter.finish)
            d.addCallback(report_closed)
            d.addErrback(report_failed)

        return all_closed

########NEW FILE########
__FILENAME__ = settings
import os
import sys
import yaml
import getpass

from os.path import abspath, expanduser

from ooni import otime, geoip
from ooni.utils import Storage

class OConfig(object):
    _custom_home = None

    def __init__(self):
        self.current_user = getpass.getuser()
        self.global_options = {}
        self.reports = Storage()
        self.scapyFactory = None
        self.tor_state = None
        # This is used to store the probes IP address obtained via Tor
        self.probe_ip = geoip.ProbeIP()
        # This is used to keep track of the state of the sniffer
        self.sniffer_running = None
        self.logging = True
        self.basic = Storage()
        self.advanced = Storage()
        self.tor = Storage()
        self.privacy = Storage()
        self.set_paths()

    def set_paths(self, ooni_home=None):
        if ooni_home:
            self._custom_home = ooni_home

        if self.global_options.get('datadir'):
            self.data_directory = abspath(expanduser(self.global_options['datadir']))
        elif self.advanced.get('data_dir'):
            self.data_directory = self.advanced['data_dir']
        elif hasattr(sys, 'real_prefix'):
            self.data_directory = os.path.abspath(os.path.join(sys.prefix, 'share', 'ooni'))
        else:
            self.data_directory = '/usr/share/ooni/'

        self.nettest_directory = abspath(os.path.join(__file__, '..', 'nettests'))

        self.ooni_home = os.path.join(expanduser('~'+self.current_user), '.ooni')
        if self._custom_home:
            self.ooni_home = self._custom_home
        self.inputs_directory = os.path.join(self.ooni_home, 'inputs')
        self.decks_directory = os.path.join(self.ooni_home, 'decks')
        self.reports_directory = os.path.join(self.ooni_home, 'reports')

        if self.global_options.get('configfile'):
            config_file = self.global_options['configfile']
            self.config_file = expanduser(config_file)
        else:
            self.config_file = os.path.join(self.ooni_home, 'ooniprobe.conf')

        if 'logfile' in self.basic:
            self.basic.logfile = expanduser(self.basic.logfile.replace('~','~'+self.current_user))

    def initialize_ooni_home(self, ooni_home=None):
        if ooni_home:
            self.set_paths(ooni_home)

        if not os.path.isdir(self.ooni_home):
            print "Ooni home directory does not exist."
            print "Creating it in '%s'." % self.ooni_home
            os.mkdir(self.ooni_home)
            os.mkdir(self.inputs_directory)
            os.mkdir(self.decks_directory)
        if not os.path.isdir(self.reports_directory):
            os.mkdir(self.reports_directory)

    def _create_config_file(self):
        sample_config_file = os.path.join(self.data_directory,
                                          'ooniprobe.conf.sample')
        target_config_file = self.config_file
        print "Creating it for you in '%s'." % target_config_file
        usr_share_path = '/usr/share'
        if hasattr(sys, 'real_prefix'):
            usr_share_path = os.path.abspath(os.path.join(sys.prefix, 'share'))

        with open(sample_config_file) as f:
            with open(target_config_file, 'w+') as w:
                for line in f:
                    if line.startswith('    data_dir: '):
                        w.write('    data_dir: %s\n' % os.path.join(usr_share_path, 'ooni'))
                    elif line.startswith('    geoip_data_dir: '):
                        w.write('    geoip_data_dir: %s\n' % os.path.join(usr_share_path, 'GeoIP'))
                    else:
                        w.write(line)

    def read_config_file(self):
        try:
            with open(self.config_file) as f: pass
        except IOError:
            print "Configuration file does not exist."
            self._create_config_file()
            self.read_config_file()

        with open(self.config_file) as f:
            config_file_contents = '\n'.join(f.readlines())
            configuration = yaml.safe_load(config_file_contents)

            for setting in ['basic', 'reports', 'advanced', 'privacy', 'tor']:
                try:
                    for k, v in configuration[setting].items():
                        getattr(self, setting)[k] = v
                except AttributeError:
                    pass
        self.set_paths()

    def generate_pcap_filename(self, testDetails):
        test_name, start_time = testDetails['test_name'], testDetails['start_time']
        start_time = otime.epochToTimestamp(start_time)
        return "report-%s-%s.%s" % (test_name, start_time, "pcap")

config = OConfig()

########NEW FILE########
__FILENAME__ = tasks
import time

from ooni import errors as e
from ooni.settings import config
from twisted.internet import defer, reactor

class BaseTask(object):
    _timer = None

    _running = None

    def __init__(self):
        """
        If you want to schedule a task multiple times, remember to create fresh
        instances of it.
        """
        self.failures = 0

        self.startTime = time.time()
        self.runtime = 0

        # This is a deferred that gets called when a test has reached it's
        # final status, this means: all retries have been attempted or the test
        # has successfully executed.
        # Such deferred will be called on completion by the TaskManager.
        self.done = defer.Deferred()

    def _failed(self, failure):
        self.failures += 1
        self.failed(failure)
        return failure

    def _succeeded(self, result):
        self.runtime = time.time() - self.startTime
        self.succeeded(result)
        return result

    def start(self):
        self._running = defer.maybeDeferred(self.run)
        self._running.addErrback(self._failed)
        self._running.addCallback(self._succeeded)
        return self._running

    def succeeded(self, result):
        """
        Place here the logic to handle a successful execution of the task.
        """
        pass

    def failed(self, failure):
        """
        Place in here logic to handle failure.
        """
        pass

    def run(self):
        """
        Override this with the logic of your task.
        Must return a deferred.
        """
        pass

class TaskWithTimeout(BaseTask):
    timeout = 30
    # So that we can test the callLater calls
    clock = reactor

    def _timedOut(self):
        """Internal method for handling timeout failure"""
        if self._running:
            self._failed(e.TaskTimedOut)
            self._running.cancel()

    def _cancelTimer(self):
        if self._timer.active():
            self._timer.cancel()

    def _succeeded(self, result):
        self._cancelTimer()
        return BaseTask._succeeded(self, result)

    def _failed(self, failure):
        self._cancelTimer()
        return BaseTask._failed(self, failure)

    def start(self):
        self._timer = self.clock.callLater(self.timeout, self._timedOut)
        return BaseTask.start(self)

class Measurement(TaskWithTimeout):
    def __init__(self, test_instance, test_method, test_input):
        """
        test_class:
            is the class, subclass of NetTestCase, of the test to be run

        test_method:
            is a string representing the test method to be called to perform
            this measurement

        test_input:
            is the input to the test

        net_test:
            a reference to the net_test object such measurement belongs to.
        """
        self.testInstance = test_instance
        self.testInstance.input = test_input
        self.testInstance._setUp()
        if 'input' not in self.testInstance.report.keys():
            self.testInstance.report['input'] = test_input
        self.testInstance._start_time = time.time()
        self.testInstance.setUp()

        self.netTestMethod = getattr(self.testInstance, test_method)

        if config.advanced.measurement_timeout:
            self.timeout = config.advanced.measurement_timeout
        TaskWithTimeout.__init__(self)

    def succeeded(self, result):
        pass

    def failed(self, failure):
        pass

    def run(self):
        return self.netTestMethod()

class ReportTracker(object):
    def __init__(self, reporters):
        self.report_completed = 0
        self.reporters = reporters
        self.failedReporters = []

    def finished(self):
        """
        Returns true if all the tasks are done. False if not.
        """
        # If a reporter fails and is removed, the report
        # is considered completed but failed, but the number
        # of reporters is now decreased by the number of failed
        # reporters.
        if self.report_completed == (len(self.reporters) + len(self.failedReporters)):
            return True
        return False

    def completed(self):
        """
        Called when a new report is completed.
        """
        self.report_completed += 1

class ReportEntry(TaskWithTimeout):
    def __init__(self, reporter, entry):
        self.reporter = reporter
        self.entry = entry 

        if config.advanced.reporting_timeout:
            self.timeout = config.advanced.reporting_timeout
        TaskWithTimeout.__init__(self)

    def run(self):
        return self.reporter.writeReportEntry(self.entry)

########NEW FILE########
__FILENAME__ = dnst
# -*- encoding: utf-8 -*-
#
# :authors: Arturo Filastò
# :licence: see LICENSE

from twisted.internet import defer, udp, error, base
from twisted.internet.defer import TimeoutError
from twisted.names import client, dns
from twisted.names.client import Resolver

from twisted.names.error import DNSQueryRefusedError

from ooni.utils import log
from ooni.nettest import NetTestCase
from ooni.errors import failureToString

import socket
from socket import gaierror

dns.DNSDatagramProtocol.noisy = False

def _bindSocket(self):
    """
    _bindSocket taken from Twisted 13.1.0 to suppress logging.
    """
    try:
        skt = self.createInternetSocket()
        skt.bind((self.interface, self.port))
    except socket.error as le:
        raise error.CannotListenError(self.interface, self.port, le)

    # Make sure that if we listened on port 0, we update that to
    # reflect what the OS actually assigned us.
    self._realPortNumber = skt.getsockname()[1]
    
    # Here we remove the logging.
    # log.msg("%s starting on %s" % (
    #         self._getLogPrefix(self.protocol), self._realPortNumber))

    self.connected = 1
    self.socket = skt
    self.fileno = self.socket.fileno
udp.Port._bindSocket = _bindSocket

def connectionLost(self, reason=None):
    """
    Taken from Twisted 13.1.0 to suppress log.msg printing.
    """
    # Here we remove the logging.
    # log.msg('(UDP Port %s Closed)' % self._realPortNumber)
    self._realPortNumber = None
    base.BasePort.connectionLost(self, reason)
    self.protocol.doStop()
    self.socket.close()
    del self.socket
    del self.fileno
    if hasattr(self, "d"):
        self.d.callback(None)
        del self.d
udp.Port.connectionLost = connectionLost

def representAnswer(answer):
    # We store the resource record and the answer payload in a
    # tuple
    return (repr(answer), repr(answer.payload))

class DNSTest(NetTestCase):
    name = "Base DNS Test"
    version = 0.1

    requiresRoot = False
    queryTimeout = [1]

    def _setUp(self):
        super(DNSTest, self)._setUp()

        self.report['queries'] = []

    def performPTRLookup(self, address, dns_server = None):
        """
        Does a reverse DNS lookup on the input ip address

        :address: the IP Address as a dotted quad to do a reverse lookup on.

        :dns_server: is the dns_server that should be used for the lookup as a
                     tuple of ip port (ex. ("127.0.0.1", 53))

                     if None, system dns settings will be used
        """
        ptr = '.'.join(address.split('.')[::-1]) + '.in-addr.arpa'
        return self.dnsLookup(ptr, 'PTR', dns_server)

    def performALookup(self, hostname, dns_server = None):
        """
        Performs an A lookup and returns an array containg all the dotted quad
        IP addresses in the response.

        :hostname: is the hostname to perform the A lookup on

        :dns_server: is the dns_server that should be used for the lookup as a
                     tuple of ip port (ex. ("127.0.0.1", 53))

                     if None, system dns settings will be used
        """
        return self.dnsLookup(hostname, 'A', dns_server)

    def performNSLookup(self, hostname, dns_server = None):
        """
        Performs a NS lookup and returns an array containg all nameservers in
        the response.

        :hostname: is the hostname to perform the NS lookup on

        :dns_server: is the dns_server that should be used for the lookup as a
                     tuple of ip port (ex. ("127.0.0.1", 53))

                     if None, system dns settings will be used
        """
        return self.dnsLookup(hostname, 'NS', dns_server)

    def performSOALookup(self, hostname, dns_server = None):
        """
        Performs a SOA lookup and returns the response (name,serial).

        :hostname: is the hostname to perform the SOA lookup on
        :dns_server: is the dns_server that should be used for the lookup as a
                     tuple of ip port (ex. ("127.0.0.1", 53))

                     if None, system dns settings will be used
        """
        return self.dnsLookup(hostname,'SOA',dns_server)

    def dnsLookup(self, hostname, dns_type, dns_server = None):
        """
        Performs a DNS lookup and returns the response.

        :hostname: is the hostname to perform the DNS lookup on
        :dns_type: type of lookup 'NS'/'A'/'SOA'
        :dns_server: is the dns_server that should be used for the lookup as a
                     tuple of ip port (ex. ("127.0.0.1", 53))
        """
        types={'NS':dns.NS,'A':dns.A,'SOA':dns.SOA,'PTR':dns.PTR}
        dnsType=types[dns_type]
        query = [dns.Query(hostname, dnsType, dns.IN)]
        def gotResponse(message):
            log.debug(dns_type+" Lookup successful")
            log.debug(message)
            addrs = []
            answers = []
            if dns_server:
                msg = message.answers
            else:
                msg = message[0]
            for answer in msg:
                if answer.type is dnsType:
                    if dnsType is dns.SOA:
                        addr = (answer.name.name,answer.payload.serial)
                    elif dnsType in [dns.NS,dns.PTR]:
                        addr = answer.payload.name.name
                    elif dnsType is dns.A:
                        addr = answer.payload.dottedQuad()
                    else:
                        addr = None
                    addrs.append(addr)
                answers.append(representAnswer(answer))

            DNSTest.addToReport(self, query, resolver=dns_server, query_type=dns_type,
                        answers=answers, addrs=addrs)
            return addrs

        def gotError(failure):
            failure.trap(gaierror, TimeoutError)
            DNSTest.addToReport(self, query, resolver=dns_server, query_type=dns_type,
                        failure=failure)
            return failure

        if dns_server:
            resolver = Resolver(servers=[dns_server])
            d = resolver.queryUDP(query, timeout=self.queryTimeout)
        else:
            lookupFunction={'NS':client.lookupNameservers, 'SOA':client.lookupAuthority, 'A':client.lookupAddress, 'PTR':client.lookupPointer}
            d = lookupFunction[dns_type](hostname)

        d.addCallback(gotResponse)
        d.addErrback(gotError)
        return d


    def addToReport(self, query, resolver=None, query_type=None,
                    answers=None, name=None, addrs=None, failure=None):
        log.debug("Adding %s to report)" % query)
        result = {}
        result['resolver'] = resolver
        result['query_type'] = query_type
        result['query'] = repr(query)
        if failure:
            result['failure'] = failureToString(failure)

        if answers:
            result['answers'] = answers
            if name:
                result['name'] = name
            if addrs:
                result['addrs'] = addrs

        self.report['queries'].append(result)

########NEW FILE########
__FILENAME__ = httpt
import random

from twisted.internet import defer

from txtorcon.interface import StreamListenerMixin

from twisted.internet import reactor
from twisted.internet.endpoints import TCP4ClientEndpoint
from ooni.utils.trueheaders import TrueHeadersAgent, TrueHeadersSOCKS5Agent

from ooni.nettest import NetTestCase
from ooni.utils import log
from ooni.settings import config

from ooni.utils.net import BodyReceiver, StringProducer, userAgents
from ooni.utils.trueheaders import TrueHeaders
from ooni.errors import handleAllFailures


class InvalidSocksProxyOption(Exception):
    pass

class StreamListener(StreamListenerMixin):

    def __init__(self, request):
        self.request = request

    def stream_succeeded(self, stream):
        host=self.request['url'].split('/')[2]
        try:
            if stream.target_host == host and len(self.request['tor']) == 1:
                self.request['tor']['exit_ip'] = stream.circuit.path[-1].ip
                self.request['tor']['exit_name'] = stream.circuit.path[-1].name
                config.tor_state.stream_listeners.remove(self)
        except:
            log.err("Tor Exit ip detection failed")

class HTTPTest(NetTestCase):
    """
    A utility class for dealing with HTTP based testing. It provides methods to
    be overriden for dealing with HTTP based testing.
    The main functions to look at are processResponseBody and
    processResponseHeader that are invoked once the headers have been received
    and once the request body has been received.

    To perform requests over Tor you will have to use the special URL schema
    "shttp". For example to request / on example.com you will have to do
    specify as URL "shttp://example.com/".

    XXX all of this requires some refactoring.
    """
    name = "HTTP Test"
    version = "0.1.1"

    randomizeUA = False
    followRedirects = False

    baseParameters = [['socksproxy', 's', None,
        'Specify a socks proxy to use for requests (ip:port)']]

    def _setUp(self):
        super(HTTPTest, self)._setUp()

        try:
            import OpenSSL
        except:
            log.err("Warning! pyOpenSSL is not installed. https websites will "
                     "not work")

        self.control_agent = TrueHeadersSOCKS5Agent(reactor,
                proxyEndpoint=TCP4ClientEndpoint(reactor, '127.0.0.1',
                    config.tor.socks_port))

        self.report['socksproxy'] = None
        sockshost, socksport = (None, None)
        if self.localOptions['socksproxy']:
            try:
                sockshost, socksport = self.localOptions['socksproxy'].split(':')
                self.report['socksproxy'] = self.localOptions['socksproxy']
            except ValueError:
                raise InvalidSocksProxyOption
            socksport = int(socksport)
            self.agent = TrueHeadersSOCKS5Agent(reactor,
                proxyEndpoint=TCP4ClientEndpoint(reactor, sockshost,
                    socksport))
        else:
            self.agent = TrueHeadersAgent(reactor)

        self.report['agent'] = 'agent'

        if self.followRedirects:
            try:
                from twisted.web.client import RedirectAgent
                self.control_agent = RedirectAgent(self.control_agent)
                self.agent = RedirectAgent(self.agent)
                self.report['agent'] = 'redirect'
            except:
                log.err("Warning! You are running an old version of twisted"\
                        "(<= 10.1). I will not be able to follow redirects."\
                        "This may make the testing less precise.")

        self.processInputs()
        log.debug("Finished test setup")

    def randomize_useragent(self, request):
        user_agent = random.choice(userAgents)
        request['headers']['User-Agent'] = [user_agent]

    def processInputs(self):
        pass

    def addToReport(self, request, response=None, response_body=None, failure_string=None):
        """
        Adds to the report the specified request and response.

        Args:
            request (dict): A dict describing the request that was made

            response (instance): An instance of
                :class:twisted.web.client.Response.
                Note: headers is our modified True Headers version.

            failure (instance): An instance of :class:twisted.internet.failure.Failure
        """
        log.debug("Adding %s to report" % request)
        request_headers = TrueHeaders(request['headers'])
        request_response = {
            'request': {
                'headers': list(request_headers.getAllRawHeaders()),
                'body': request['body'],
                'url': request['url'],
                'method': request['method'],
                'tor': request['tor']
            }
        }
        if response:
            request_response['response'] = {
                'headers': list(response.headers.getAllRawHeaders()),
                'body': response_body,
                'code': response.code
        }
        if failure_string:
            request_response['failure'] = failure_string

        self.report['requests'].append(request_response)

    def _processResponseBody(self, response_body, request, response, body_processor):
        log.debug("Processing response body")
        HTTPTest.addToReport(self, request, response, response_body)
        if body_processor:
            body_processor(response_body)
        else:
            self.processResponseBody(response_body)
        response.body = response_body
        return response

    def processResponseBody(self, body):
        """
        Overwrite this method if you wish to interact with the response body of
        every request that is made.

        Args:

            body (str): The body of the HTTP response
        """
        pass

    def processResponseHeaders(self, headers):
        """
        This should take care of dealing with the returned HTTP headers.

        Args:

            headers (dict): The returned header fields.
        """
        pass

    def processRedirect(self, location):
        """
        Handle a redirection via a 3XX HTTP status code.

        Here you may place logic that evaluates the destination that you are
        being redirected to. Matches against known censor redirects, etc.

        Note: if self.followRedirects is set to True, then this method will
            never be called.
            XXX perhaps we may want to hook _handleResponse in RedirectAgent to
            call processRedirect every time we get redirected.

        Args:

            location (str): the url that we are being redirected to.
        """
        pass

    def _cbResponse(self, response, request,
            headers_processor, body_processor):
        """
        This callback is fired once we have gotten a response for our request.
        If we are using a RedirectAgent then this will fire once we have
        reached the end of the redirect chain.

        Args:

            response (:twisted.web.iweb.IResponse:): a provider for getting our response

            request (dict): the dict containing our response (XXX this should be dropped)

            header_processor (func): a function to be called with argument a
                dict containing the response headers. This will lead
                self.headerProcessor to not be called.

            body_processor (func): a function to be called with as argument the
                body of the response. This will lead self.bodyProcessor to not
                be called.

        """
        if not response:
            log.err("Got no response for request %s" % request)
            HTTPTest.addToReport(self, request, response)
            return
        else:
            log.debug("Got response %s" % response)

        if str(response.code).startswith('3'):
            self.processRedirect(response.headers.getRawHeaders('Location')[0])

        # [!] We are passing to the headers_processor the headers dict and
        # not the Headers() object
        response_headers_dict = list(response.headers.getAllRawHeaders())
        if headers_processor:
            headers_processor(response_headers_dict)
        else:
            self.processResponseHeaders(response_headers_dict)

        try:
            content_length = int(response.headers.getRawHeaders('content-length')[0])
        except Exception:
            content_length = None

        finished = defer.Deferred()
        response.deliverBody(BodyReceiver(finished, content_length))
        finished.addCallback(self._processResponseBody, request,
                response, body_processor)
        return finished

    def doRequest(self, url, method="GET",
                  headers={}, body=None, headers_processor=None,
                  body_processor=None, use_tor=False):
        """
        Perform an HTTP request with the specified method and headers.

        Args:

            url (str): the full URL of the request. The scheme may be either
                http, https, or httpo for http over Tor Hidden Service.

        Kwargs:

            method (str): the HTTP method name to use for the request

            headers (dict): the request headers to send

            body (str): the request body

            headers_processor : a function to be used for processing the HTTP
                header responses (defaults to self.processResponseHeaders).
                This function takes as argument the HTTP headers as a dict.

            body_processory: a function to be used for processing the HTTP
                response body (defaults to self.processResponseBody). This
                function takes the response body as an argument.

            use_tor (bool): specify if the HTTP request should be done over Tor
                or not.

        """

        # We prefix the URL with 's' to make the connection go over the
        # configured socks proxy
        if use_tor:
            log.debug("Using Tor for the request to %s" % url)
            agent = self.control_agent
        else:
            agent = self.agent

        if self.localOptions['socksproxy']:
            log.debug("Using SOCKS proxy %s for request" % (self.localOptions['socksproxy']))

        log.debug("Performing request %s %s %s" % (url, method, headers))

        request = {}
        request['method'] = method
        request['url'] = url
        request['headers'] = headers
        request['body'] = body
        request['tor'] = {}
        if use_tor:
            request['tor']['is_tor'] = True
        else:
            request['tor']['is_tor'] = False

        if self.randomizeUA:
            log.debug("Randomizing user agent")
            self.randomize_useragent(request)

        if 'requests' not in self.report:
            self.report['requests'] = []

        # If we have a request body payload, set the request body to such
        # content
        if body:
            body_producer = StringProducer(request['body'])
        else:
            body_producer = None

        headers = TrueHeaders(request['headers'])

        def errback(failure, request):
            if request['tor']['is_tor']:
                log.err("Error performing torified request: %s" % request['url'])
            else:
                log.err("Error performing request: %s" % request['url'])
            failure_string = handleAllFailures(failure)
            self.addToReport(request, failure_string=failure_string)
            return failure

        if use_tor:
            state = config.tor_state
            if state:
                state.add_stream_listener(StreamListener(request))

        d = agent.request(request['method'], request['url'], headers,
                body_producer)
        d.addErrback(errback, request)
        d.addCallback(self._cbResponse, request, headers_processor,
                body_processor)
        return d

########NEW FILE########
__FILENAME__ = scapyt
import random
from zope.interface import implements
from twisted.plugin import IPlugin
from twisted.internet import protocol, defer, threads

from scapy.all import send, sr, IP, TCP, config

from ooni.reporter import createPacketReport
from ooni.nettest import NetTestCase
from ooni.utils import log
from ooni.settings import config

from ooni.utils.txscapy import ScapySender, getDefaultIface, ScapyFactory
from ooni.utils.txscapy import hasRawSocketPermission

class BaseScapyTest(NetTestCase):
    """
    The report of a test run with scapy looks like this:

    report:
        sent_packets: [{'raw_packet': BASE64Encoding of packet,
                        'summary': 'IP / TCP 192.168.2.66:ftp_data > 8.8.8.8:http S'}]

        answered_packets: []

    """
    name = "Base Scapy Test"
    version = 0.1

    requiresRoot = not hasRawSocketPermission()
    baseFlags = [
            ['ipsrc', 's',
                'Does *not* check if IP src and ICMP IP citation matches when processing answers'],
            ['seqack', 'k',
                'Check if TCP sequence number and ACK match in the ICMP citation when processing answers'],
            ['ipid', 'i',
                'Check if the IPID matches when processing answers']
            ]

    def _setUp(self):
        super(BaseScapyTest, self)._setUp()

        if not config.scapyFactory:
            log.debug("Scapy factory not set, registering it.")
            config.scapyFactory = ScapyFactory(config.advanced.interface)

        self.report['answer_flags'] = []
        if self.localOptions['ipsrc']:
            config.checkIPsrc = 0
        else:
            self.report['answer_flags'].append('ipsrc')
            config.checkIPsrc = 1

        if self.localOptions['ipid']:
            self.report['answer_flags'].append('ipid')
            config.checkIPID = 1
        else:
            config.checkIPID = 0
        # XXX we don't support strict matching
        # since (from scapy's documentation), some stacks have a bug for which
        # the bytes in the IPID are swapped.
        # Perhaps in the future we will want to have more fine grained control
        # over this.

        if self.localOptions['seqack']:
            self.report['answer_flags'].append('seqack')
            config.check_TCPerror_seqack = 1
        else:
            config.check_TCPerror_seqack = 0

        self.report['sent_packets'] = []
        self.report['answered_packets'] = []

    def finishedSendReceive(self, packets):
        """
        This gets called when all packets have been sent and received.
        """
        answered, unanswered = packets

        for snd, rcv in answered:
            log.debug("Writing report for scapy test")
            sent_packet = snd
            received_packet = rcv

            if not config.privacy.includeip:
                log.debug("Detected you would not like to include your ip in the report")
                log.debug("Stripping source and destination IPs from the reports")
                sent_packet.src = '127.0.0.1'
                received_packet.dst = '127.0.0.1'

            self.report['sent_packets'].append(sent_packet)
            self.report['answered_packets'].append(received_packet)
        return packets

    def sr(self, packets, *arg, **kw):
        """
        Wrapper around scapy.sendrecv.sr for sending and receiving of packets
        at layer 3.
        """
        scapySender = ScapySender()

        config.scapyFactory.registerProtocol(scapySender)
        log.debug("Using sending with hash %s" % scapySender.__hash__)

        d = scapySender.startSending(packets)
        d.addCallback(self.finishedSendReceive)
        return d

    def sr1(self, packets, *arg, **kw):
        def done(packets):
            """
            We do this so that the returned value is only the one packet that
            we expected a response for, identical to the scapy implementation
            of sr1.
            """
            try:
                return packets[0][0][1]
            except IndexError:
                log.err("Got no response...")
                return packets

        scapySender = ScapySender()
        scapySender.expected_answers = 1

        config.scapyFactory.registerProtocol(scapySender)

        log.debug("Running sr1")
        d = scapySender.startSending(packets)
        log.debug("Started to send")
        d.addCallback(self.finishedSendReceive)
        d.addCallback(done)
        return d

    def send(self, packets, *arg, **kw):
        """
        Wrapper around scapy.sendrecv.send for sending of packets at layer 3
        """
        scapySender = ScapySender()

        config.scapyFactory.registerProtocol(scapySender)
        scapySender.startSending(packets)

        scapySender.stopSending()
        for sent_packet in packets:
            self.report['sent_packets'].append(sent_packet)

ScapyTest = BaseScapyTest

########NEW FILE########
__FILENAME__ = tcpt
from twisted.internet import protocol, defer, reactor
from twisted.internet.error import ConnectionDone
from twisted.internet.endpoints import TCP4ClientEndpoint

from ooni.nettest import NetTestCase
from ooni.errors import failureToString
from ooni.utils import log

class TCPSender(protocol.Protocol):
    def __init__(self):
        self.received_data = ''
        self.sent_data = ''

    def dataReceived(self, data):
        """
        We receive data until the total amount of data received reaches that
        which we have sent. At that point we append the received data to the
        report and we fire the callback of the test template sendPayload
        function.

        This is used in pair with a TCP Echo server.

        The reason why we put the data received inside of an array is that in
        future we may want to expand this to support state and do something
        similar to what daphne does, but without the mutation.

        XXX Actually daphne will probably be refactored to be a subclass of the
        TCP Test Template.
        """
        if self.payload_len:
            self.received_data += data

    def sendPayload(self, payload):
        """
        Write the payload to the wire and set the expected size of the payload
        we are to receive.

        Args:

            payload: the data to be sent on the wire.

        """
        self.payload_len = len(payload)
        self.sent_data = payload
        self.transport.write(payload)

class TCPSenderFactory(protocol.Factory):
    def buildProtocol(self, addr):
        return TCPSender()

class TCPTest(NetTestCase):
    name = "Base TCP Test"
    version = "0.1"

    requiresRoot = False
    timeout = 5
    address = None
    port = None

    def _setUp(self):
        super(TCPTest, self)._setUp()

        self.report['sent'] = []
        self.report['received'] = []

    def sendPayload(self, payload):
        d1 = defer.Deferred()

        def closeConnection(proto):
            self.report['sent'].append(proto.sent_data)
            self.report['received'].append(proto.received_data)
            proto.transport.loseConnection()
            log.debug("Closing connection")
            d1.callback(proto.received_data)

        def timedOut(proto):
            self.report['failure'] = 'tcp_timed_out_error'
            proto.transport.loseConnection()

        def errback(failure):
            self.report['failure'] = failureToString(failure)
            d1.errback(failure)

        def connected(proto):
            log.debug("Connected to %s:%s" % (self.address, self.port))
            proto.report = self.report
            proto.deferred = d1
            proto.sendPayload(payload)
            if self.timeout:
                # XXX-Twisted this logic should probably go inside of the protocol
                reactor.callLater(self.timeout, closeConnection, proto)

        point = TCP4ClientEndpoint(reactor, self.address, self.port)
        log.debug("Connecting to %s:%s" % (self.address, self.port))
        d2 = point.connect(TCPSenderFactory())
        d2.addCallback(connected)
        d2.addErrback(errback)
        return d1


########NEW FILE########
__FILENAME__ = disable_test_dns
#
# This unittest is to verify that our usage of the twisted DNS resolver does
# not break with new versions of twisted.

import pdb
from twisted.trial import unittest

from twisted.internet import reactor

from twisted.names import dns
from twisted.names.client import Resolver

class DNSTest(unittest.TestCase):
    def test_a_lookup_ooni_query(self):
        def done_query(message, *arg):
            answer = message.answers[0]
            self.assertEqual(answer.type, 1)

        dns_query = [dns.Query('ooni.nu', type=dns.A)]
        resolver = Resolver(servers=[('8.8.8.8', 53)])
        d = resolver.queryUDP(dns_query)
        d.addCallback(done_query)
        return d


########NEW FILE########
__FILENAME__ = mocks
from twisted.python import failure
from twisted.internet import defer

from ooni.tasks import BaseTask, TaskWithTimeout
from ooni.nettest import NetTest
from ooni.managers import TaskManager

class MockMeasurementFailOnce(BaseTask):
    def run(self):
        f = open('dummyTaskFailOnce.txt', 'w')
        f.write('fail')
        f.close()
        if self.failure >= 1:
            return defer.succeed(self)
        else:
            return defer.fail(failure.Failure)

class MockMeasurementManager(TaskManager):
    def __init__(self):
        self.successes = []
        TaskManager.__init__(self)

    def failed(self, failure, task):
        pass

    def succeeded(self, result, task):
        self.successes.append((result, task))

class MockReporter(object):
    def __init__(self):
        self.created = defer.Deferred()

    def writeReportEntry(self, entry):
        pass

    def createReport(self):
        self.created.callback(self)

    def finish(self):
        pass

class MockFailure(Exception):
    pass

## from test_managers
mockFailure = failure.Failure(MockFailure('mock'))

class MockSuccessTask(BaseTask):
    def run(self):
        return defer.succeed(42)

class MockFailTask(BaseTask):
    def run(self):
        return defer.fail(mockFailure)

class MockFailOnceTask(BaseTask):
    def run(self):
        if self.failures >= 1:
            return defer.succeed(42)
        else:
            return defer.fail(mockFailure)

class MockSuccessTaskWithTimeout(TaskWithTimeout):
    def run(self):
        return defer.succeed(42)

class MockFailTaskThatTimesOut(TaskWithTimeout):
    def run(self):
        return defer.Deferred()

class MockTimeoutOnceTask(TaskWithTimeout):
    def run(self):
        if self.failures >= 1:
            return defer.succeed(42)
        else:
            return defer.Deferred()

class MockFailTaskWithTimeout(TaskWithTimeout):
    def run(self):
        return defer.fail(mockFailure)


class MockNetTest(object):
    def __init__(self):
        self.successes = []

    def succeeded(self, measurement):
        self.successes.append(measurement)

class MockMeasurement(TaskWithTimeout):
    def __init__(self, net_test):
        TaskWithTimeout.__init__(self)
        self.netTest = net_test

    def succeeded(self, result):
        return self.netTest.succeeded(42)

class MockSuccessMeasurement(MockMeasurement):
    def run(self):
        return defer.succeed(42)

class MockFailMeasurement(MockMeasurement):
    def run(self):
        return defer.fail(mockFailure)

class MockFailOnceMeasurement(MockMeasurement):
    def run(self):
        if self.failures >= 1:
            return defer.succeed(42)
        else:
            return defer.fail(mockFailure)

class MockDirector(object):
    def __init__(self):
        self.successes = []

    def measurementFailed(self, failure, measurement):
        pass

    def measurementSucceeded(self, measurement):
        self.successes.append(measurement)

## from test_reporter.py
class MockOReporter(object):
    def __init__(self):
        self.created = defer.Deferred()

    def writeReportEntry(self, entry):
        return defer.succeed(42)

    def finish(self):
        pass

    def createReport(self):
        from ooni.utils import log
        log.debug("Creating report with %s" % self)
        self.created.callback(self)

class MockOReporterThatFailsWrite(MockOReporter):
    def writeReportEntry(self, entry):
        raise MockFailure

class MockOReporterThatFailsOpen(MockOReporter):
    def createReport(self):
        raise MockFailure

class MockOReporterThatFailsWriteOnce(MockOReporter):
    def __init__(self):
        self.failure = 0
        MockOReporter.__init__(self)

    def writeReportEntry(self, entry):
        if self.failure >= 1:
            return defer.succeed(42)
        else:
            self.failure += 1
            raise MockFailure 

class MockTaskManager(TaskManager):
    def __init__(self):
        self.successes = []
        TaskManager.__init__(self)

    def failed(self, failure, task):
        pass

    def succeeded(self, result, task):
        self.successes.append((result, task))


########NEW FILE########
__FILENAME__ = test_deck
import os

from twisted.internet import defer
from twisted.trial import unittest

from hashlib import sha256
from ooni.deck import InputFile, Deck

net_test_string = """
from twisted.python import usage
from ooni.nettest import NetTestCase

class UsageOptions(usage.Options):
    optParameters = [['spam', 's', None, 'ham']]

class DummyTestCase(NetTestCase):

    usageOptions = UsageOptions
    requiredTestHelpers = {'spam': 'test-helper-typeA'}

    def test_a(self):
        self.report['bar'] = 'bar'

    def test_b(self):
        self.report['foo'] = 'foo'
"""


class BaseTestCase(unittest.TestCase):
    def setUp(self):
        self.cwd = os.getcwd()
        self.dummy_deck_content = """- options:
            collector: null
            help: 0
            logfile: null
            no-default-reporter: 0
            parallelism: null
            pcapfile: null
            reportfile: null
            resume: 0
            subargs: []
            test_file: manipulation/http_invalid_request_line
            testdeck: null
"""

class TestInputFile(BaseTestCase):
    def test_file_cached(self):
        file_hash = sha256(self.dummy_deck_content).hexdigest()
        input_file = InputFile(file_hash, base_path='.')
        with open(file_hash, 'w+') as f:
            f.write(self.dummy_deck_content)
        assert input_file.fileCached

    def test_file_invalid_hash(self):
        invalid_hash = 'a'*64
        with open(invalid_hash, 'w+') as f:
            f.write("b"*100)
        input_file = InputFile(invalid_hash, base_path='.')
        self.assertRaises(AssertionError, input_file.verify)

    def test_save_descriptor(self):
        descriptor = {
                'name': 'spam',
                'id': 'spam',
                'version': 'spam',
                'author': 'spam',
                'date': 'spam',
                'description': 'spam'
        }
        file_id = 'a'*64
        input_file = InputFile(file_id, base_path='.')
        input_file.load(descriptor)
        input_file.save()
        assert os.path.isfile(file_id)

        assert input_file.descriptorCached

class MockOONIBClient(object):
    def lookupTestHelpers(self, required_test_helpers):
        ret = {
            'default': {
                'address': '127.0.0.1',
                'collector': 'httpo://thirteenchars1234.onion'
            }
        }
        for required_test_helper in required_test_helpers:
            ret[required_test_helper] = {
                    'address': '127.0.0.1',
                    'collector': 'httpo://thirteenchars1234.onion'
        }
        return defer.succeed(ret)

class TestDeck(BaseTestCase):
    def setUp(self):
        super(TestDeck, self).setUp()
        deck_hash = sha256(self.dummy_deck_content).hexdigest()
        self.deck_file = os.path.join(self.cwd, deck_hash)
        with open(self.deck_file, 'w+') as f:
            f.write(self.dummy_deck_content)
        with open(os.path.join(self.cwd, 'dummy_test.py'), 'w+') as f:
            f.write(net_test_string)

    def test_open_deck(self):
        deck = Deck(decks_directory=".")
        deck.bouncer = "httpo://foo.onion"
        deck.loadDeck(self.deck_file)
        assert len(deck.netTestLoaders) == 1

    def test_save_deck_descriptor(self):
        deck = Deck(decks_directory=".")
        deck.bouncer = "httpo://foo.onion"
        deck.loadDeck(self.deck_file)
        deck.load({'name': 'spam',
            'id': 'spam',
            'version': 'spam',
            'author': 'spam',
            'date': 'spam',
            'description': 'spam'
        })
        deck.save()
        deck.verify()
    
    @defer.inlineCallbacks
    def test_lookuptest_helpers(self):
        deck = Deck(decks_directory=".")
        deck.bouncer = "httpo://foo.onion"
        deck.oonibclient = MockOONIBClient()
        deck.loadDeck(self.deck_file)
        yield deck.lookupTestHelpers()

        assert deck.netTestLoaders[0].collector == 'httpo://thirteenchars1234.onion'

        required_test_helpers = deck.netTestLoaders[0].requiredTestHelpers
        assert len(required_test_helpers) == 1
        assert required_test_helpers[0]['test_class'].localOptions['backend'] == '127.0.0.1'

########NEW FILE########
__FILENAME__ = test_director
from mock import patch, MagicMock

from ooni.settings import config
from ooni.director import Director

from twisted.internet import defer
from twisted.trial import unittest

from txtorcon import TorControlProtocol
proto = MagicMock()
proto.tor_protocol = TorControlProtocol()

mock_TorState = MagicMock()
# We use the instance of mock_TorState so that the mock caching will
# return the same instance when TorState is created.
mts = mock_TorState()
mts.protocol.get_conf = lambda x: defer.succeed({'SocksPort': '4242'})
mts.post_bootstrap = defer.succeed(mts)

# Set the tor_protocol to be already fired
state = MagicMock()
proto.tor_protocol.post_bootstrap = defer.succeed(state)

mock_launch_tor = MagicMock()
mock_launch_tor.return_value = defer.succeed(proto)

class TestDirector(unittest.TestCase):
    def tearDown(self):
        config.tor_state = None
        config.tor.socks_port = None
        config.tor.control_port = None

    def test_get_net_tests(self):
        director = Director()
        nettests = director.getNetTests()
        assert 'http_requests' in nettests
        assert 'dns_consistency' in nettests
        assert 'http_header_field_manipulation' in nettests
        assert 'traceroute' in nettests

    @patch('ooni.director.TorState', mock_TorState)
    @patch('ooni.director.launch_tor', mock_launch_tor)
    def test_start_tor(self):
        @defer.inlineCallbacks
        def director_start_tor():
            director = Director()
            yield director.startTor()
            assert config.tor.socks_port == 4242
            assert config.tor.control_port == 4242

        return director_start_tor()

########NEW FILE########
__FILENAME__ = test_geoip
import os

from twisted.internet import defer
from twisted.trial import unittest

from ooni.tests import is_internet_connected
from ooni.settings import config
from ooni import geoip


class TestGeoIP(unittest.TestCase):
    def setUp(self):
        config.initialize_ooni_home('ooni_home')
        config.read_config_file()

    def test_ip_to_location(self):
        location = geoip.IPToLocation('8.8.8.8')
        assert 'countrycode' in location
        assert 'asn' in location
        assert 'city' in location

    @defer.inlineCallbacks
    def test_probe_ip(self):
        if not is_internet_connected():
            self.skipTest(
                "You must be connected to the internet to run this test"
            )
        probe_ip = geoip.ProbeIP()
        res = yield probe_ip.lookup()
        assert len(res.split('.')) == 4

########NEW FILE########
__FILENAME__ = test_managers
import os

from twisted.trial import unittest
from twisted.python import failure
from twisted.internet import defer, task

from ooni.tasks import BaseTask, TaskWithTimeout
from ooni.managers import TaskManager, MeasurementManager

from ooni.tests.mocks import MockSuccessTask, MockFailTask, MockFailOnceTask, MockFailure
from ooni.tests.mocks import MockSuccessTaskWithTimeout, MockFailTaskThatTimesOut
from ooni.tests.mocks import MockTimeoutOnceTask, MockFailTaskWithTimeout
from ooni.tests.mocks import MockTaskManager, mockFailure, MockDirector
from ooni.tests.mocks import MockNetTest, MockMeasurement, MockSuccessMeasurement
from ooni.tests.mocks import MockFailMeasurement, MockFailOnceMeasurement
from ooni.settings import config


class TestTaskManager(unittest.TestCase):
    timeout = 1
    def setUp(self):
        self.measurementManager = MockTaskManager()
        self.measurementManager.concurrency = 20
        self.measurementManager.retries = 2

        self.measurementManager.start()

        self.clock = task.Clock()
        data_dir = os.path.dirname(os.path.abspath(__file__))
        data_dir = os.path.join(data_dir, '..', '..', 'data')
        config.global_options['datadir'] = data_dir
        config.set_paths()

    def schedule_successful_tasks(self, task_type, number=1):
        all_done = []
        for x in range(number):
            mock_task = task_type()
            all_done.append(mock_task.done)
            self.measurementManager.schedule(mock_task)

        d = defer.DeferredList(all_done)
        @d.addCallback
        def done(res):
            for task_result, task_instance in self.measurementManager.successes:
                self.assertEqual(task_result, 42)
                self.assertIsInstance(task_instance, task_type)

        return d

    def schedule_failing_tasks(self, task_type, number=1):
        all_done = []
        for x in range(number):
            mock_task = task_type()
            all_done.append(mock_task.done)
            mock_task.done.addErrback(lambda x: None)
            self.measurementManager.schedule(mock_task)

        d = defer.DeferredList(all_done)
        @d.addCallback
        def done(res):
            # 10*2 because 2 is the number of retries
            self.assertEqual(self.measurementManager.failures, number*3)
            # XXX @aagbsn is there a reason why you switched to using an int
            # over a using a list?
            # self.assertEqual(len(self.measurementManager.failures), number*3)
            # for task_result, task_instance in self.measurementManager.failures:
            #     self.assertEqual(task_result, mockFailure)
            #     self.assertIsInstance(task_instance, task_type)

        return d

    def test_schedule_failing_with_mock_failure_task(self):
        mock_task = MockFailTask()
        self.measurementManager.schedule(mock_task)
        self.assertFailure(mock_task.done, MockFailure)
        return mock_task.done

    def test_schedule_successful_one_task(self):
        return self.schedule_successful_tasks(MockSuccessTask)

    def test_schedule_successful_one_task_with_timeout(self):
        return self.schedule_successful_tasks(MockSuccessTaskWithTimeout)

    def test_schedule_failing_tasks_that_timesout(self):
        self.measurementManager.retries = 0

        task_type = MockFailTaskThatTimesOut
        task_timeout = 5

        mock_task = task_type()
        mock_task.timeout = task_timeout
        mock_task.clock = self.clock

        self.measurementManager.schedule(mock_task)

        self.clock.advance(task_timeout)

        @mock_task.done.addBoth
        def done(res):
            self.assertEqual(self.measurementManager.failures, 1)
            # self.assertEqual(len(self.measurementManager.failures), 1)
            # for task_result, task_instance in self.measurementManager.failures:
            #     self.assertIsInstance(task_instance, task_type)

        return mock_task.done

    def test_schedule_time_out_once(self):
        task_type = MockTimeoutOnceTask
        task_timeout = 5

        mock_task = task_type()
        mock_task.timeout = task_timeout
        mock_task.clock = self.clock

        self.measurementManager.schedule(mock_task)

        self.clock.advance(task_timeout)

        @mock_task.done.addBoth
        def done(res):
            self.assertEqual(self.measurementManager.failures, 1)
            #self.assertEqual(len(self.measurementManager.failures), 1)
            # for task_result, task_instance in self.measurementManager.failures:
            #     self.assertIsInstance(task_instance, task_type)

            for task_result, task_instance in self.measurementManager.successes:
                self.assertEqual(task_result, 42)
                self.assertIsInstance(task_instance, task_type)

        return mock_task.done


    def test_schedule_failing_one_task(self):
        return self.schedule_failing_tasks(MockFailTask)

    def test_schedule_failing_one_task_with_timeout(self):
        return self.schedule_failing_tasks(MockFailTaskWithTimeout)

    def test_schedule_successful_ten_tasks(self):
        return self.schedule_successful_tasks(MockSuccessTask, number=10)

    def test_schedule_failing_ten_tasks(self):
        return self.schedule_failing_tasks(MockFailTask, number=10)

    def test_schedule_successful_27_tasks(self):
        return self.schedule_successful_tasks(MockSuccessTask, number=27)

    def test_schedule_failing_27_tasks(self):
        return self.schedule_failing_tasks(MockFailTask, number=27)

    def test_task_retry_and_succeed(self):
        mock_task = MockFailOnceTask()
        self.measurementManager.schedule(mock_task)

        @mock_task.done.addCallback
        def done(res):
            self.assertEqual(self.measurementManager.failures, 1)
            #self.assertEqual(len(self.measurementManager.failures), 1)
            # self.assertEqual(self.measurementManager.failures,
            #         [(mockFailure, mock_task)])
            self.assertEqual(self.measurementManager.successes,
                    [(42, mock_task)])

        return mock_task.done

    def test_task_retry_and_succeed_56_tasks(self):
        """
        XXX this test fails in a non-deterministic manner.
        """
        all_done = []
        number = 56
        for x in range(number):
            mock_task = MockFailOnceTask()
            all_done.append(mock_task.done)
            self.measurementManager.schedule(mock_task)

        d = defer.DeferredList(all_done)

        @d.addCallback
        def done(res):
            self.assertEqual(self.measurementManager.failures, number)
            #self.assertEqual(len(self.measurementManager.failures), number)
            for task_result, task_instance in self.measurementManager.successes:
                self.assertEqual(task_result, 42)
                self.assertIsInstance(task_instance, MockFailOnceTask)

        return d

class TestMeasurementManager(unittest.TestCase):
    def setUp(self):
        mock_director = MockDirector()

        self.measurementManager = MeasurementManager()
        self.measurementManager.director = mock_director

        self.measurementManager.concurrency = 10
        self.measurementManager.retries = 2

        self.measurementManager.start()

        self.mockNetTest = MockNetTest()

    def test_schedule_and_net_test_notified(self, number=1):
        # XXX we should probably be inheriting from the base test class
        mock_task = MockSuccessMeasurement(self.mockNetTest)
        self.measurementManager.schedule(mock_task)

        @mock_task.done.addCallback
        def done(res):
            self.assertEqual(self.mockNetTest.successes,
                    [42])

            self.assertEqual(len(self.mockNetTest.successes), 1)
        return mock_task.done

    def test_schedule_failing_one_measurement(self):
        mock_task = MockFailMeasurement(self.mockNetTest)
        self.measurementManager.schedule(mock_task)

        @mock_task.done.addErrback
        def done(failure):
            self.assertEqual(self.measurementManager.failures, 3)
            #self.assertEqual(len(self.measurementManager.failures), 3)

            self.assertEqual(failure, mockFailure)
            self.assertEqual(len(self.mockNetTest.successes), 0)

        return mock_task.done

########NEW FILE########
__FILENAME__ = test_mutate
import unittest
from ooni.kit import daphn3

class TestDaphn3(unittest.TestCase):
    def test_mutate_string(self):
        original_string = '\x00\x00\x00'
        mutated = daphn3.daphn3MutateString(original_string, 1)
        self.assertEqual(mutated, '\x00\x01\x00')
    def test_mutate_daphn3(self):
        original_dict = [{'client': '\x00\x00\x00'},
                {'server': '\x00\x00\x00'}]
        mutated_dict = daphn3.daphn3Mutate(original_dict,  1, 1)
        self.assertEqual(mutated_dict, [{'client': '\x00\x00\x00'},
            {'server': '\x00\x01\x00'}])


########NEW FILE########
__FILENAME__ = test_nettest
import os
from StringIO import StringIO
from tempfile import TemporaryFile, mkstemp

from twisted.trial import unittest
from twisted.internet import defer, reactor
from twisted.python.usage import UsageError

from ooni.settings import config
from ooni.errors import MissingRequiredOption, InvalidOption, FailureToLoadNetTest
from ooni.nettest import NetTest, NetTestLoader
from ooni.tasks import BaseTask

from ooni.director import Director
from ooni.managers import TaskManager

from ooni.tests.mocks import MockMeasurement, MockMeasurementFailOnce
from ooni.tests.mocks import MockNetTest, MockDirector, MockReporter
from ooni.tests.mocks import MockMeasurementManager

net_test_string = """
from twisted.python import usage
from ooni.nettest import NetTestCase

class UsageOptions(usage.Options):
    optParameters = [['spam', 's', None, 'ham']]

class DummyTestCase(NetTestCase):

    usageOptions = UsageOptions

    def test_a(self):
        self.report['bar'] = 'bar'

    def test_b(self):
        self.report['foo'] = 'foo'
"""

net_test_root_required = net_test_string+"""
    requiresRoot = True
"""

net_test_string_with_file = """
from twisted.python import usage
from ooni.nettest import NetTestCase

class UsageOptions(usage.Options):
    optParameters = [['spam', 's', None, 'ham']]

class DummyTestCase(NetTestCase):
    inputFile = ['file', 'f', None, 'The input File']

    usageOptions = UsageOptions

    def test_a(self):
        self.report['bar'] = 'bar'

    def test_b(self):
        self.report['foo'] = 'foo'
"""

net_test_string_with_required_option = """
from twisted.python import usage
from ooni.nettest import NetTestCase

class UsageOptions(usage.Options):
    optParameters = [['spam', 's', None, 'ham'],
                     ['foo', 'o', None, 'moo'],
                     ['bar', 'o', None, 'baz'],
    ]

class DummyTestCase(NetTestCase):
    inputFile = ['file', 'f', None, 'The input File']

    usageOptions = UsageOptions

    def test_a(self):
        self.report['bar'] = 'bar'

    def test_b(self):
        self.report['foo'] = 'foo'

    requiredOptions = ['foo', 'bar']
"""

http_net_test = """
from twisted.internet import defer
from twisted.python import usage, failure

from ooni.utils import log
from ooni.utils.net import userAgents
from ooni.templates import httpt
from ooni.errors import failureToString, handleAllFailures

class UsageOptions(usage.Options):
    optParameters = [
                     ['url', 'u', None, 'Specify a single URL to test.'],
                     ['factor', 'f', 0.8, 'What factor should be used for triggering censorship (0.8 == 80%)']
                    ]

class HTTPBasedTest(httpt.HTTPTest):
    usageOptions = UsageOptions
    def test_get(self):
        return self.doRequest(self.localOptions['url'], method="GET",
                              use_tor=False)
"""

dummyInputs = range(1)
dummyArgs = ('--spam', 'notham')
dummyOptions = {'spam':'notham'}
dummyInvalidArgs = ('--cram', 'jam')
dummyInvalidOptions= {'cram':'jam'}
dummyArgsWithRequiredOptions = ('--foo', 'moo', '--bar', 'baz')
dummyRequiredOptions = {'foo':'moo', 'bar':'baz'}
dummyArgsWithFile = ('--spam', 'notham', '--file', 'dummyInputFile.txt')

class TestNetTest(unittest.TestCase):
    timeout = 1
    def setUp(self):
        with open('dummyInputFile.txt', 'w') as f:
            for i in range(10):
                f.write("%s\n" % i)

        config.initialize_ooni_home('ooni_home')
        config.read_config_file()

    def assertCallable(self, thing):
        self.assertIn('__call__', dir(thing))

    def verifyMethods(self, testCases):
        uniq_test_methods = set()
        for test_class, test_methods in testCases:
            instance = test_class()
            for test_method in test_methods:
                c = getattr(instance, test_method)
                self.assertCallable(c)
                uniq_test_methods.add(test_method)
        self.assertEqual(set(['test_a', 'test_b']), uniq_test_methods)

    def test_load_net_test_from_file(self):
        """
        Given a file verify that the net test cases are properly
        generated.
        """
        __, net_test_file = mkstemp()
        with open(net_test_file, 'w') as f:
            f.write(net_test_string)
        f.close()

        ntl = NetTestLoader(dummyArgs)
        ntl.loadNetTestFile(net_test_file)

        self.verifyMethods(ntl.testCases)
        os.unlink(net_test_file)

    def test_load_net_test_from_str(self):
        """
        Given a file like object verify that the net test cases are properly
        generated.
        """
        ntl = NetTestLoader(dummyArgs)
        ntl.loadNetTestString(net_test_string)

        self.verifyMethods(ntl.testCases)

    def test_load_net_test_from_StringIO(self):
        """
        Given a file like object verify that the net test cases are properly
        generated.
        """
        ntl = NetTestLoader(dummyArgs)
        ntl.loadNetTestString(net_test_string)

        self.verifyMethods(ntl.testCases)

    def test_load_with_option(self):
        ntl = NetTestLoader(dummyArgs)
        ntl.loadNetTestString(net_test_string)

        self.assertIsInstance(ntl, NetTestLoader)
        for test_klass, test_meth in ntl.testCases:
            for option in dummyOptions.keys():
                self.assertIn(option, test_klass.usageOptions())

    def test_load_with_invalid_option(self):
        try:
            ntl = NetTestLoader(dummyInvalidArgs)
            ntl.loadNetTestString(net_test_string)

            ntl.checkOptions()
            raise Exception
        except UsageError:
            pass

    def test_load_with_required_option(self):
        ntl = NetTestLoader(dummyArgsWithRequiredOptions)
        ntl.loadNetTestString(net_test_string_with_required_option)

        self.assertIsInstance(ntl, NetTestLoader)

    def test_load_with_missing_required_option(self):
        try:
            ntl = NetTestLoader(dummyArgs)
            ntl.loadNetTestString(net_test_string_with_required_option)

        except MissingRequiredOption:
            pass

    def test_net_test_inputs(self):
        ntl = NetTestLoader(dummyArgsWithFile)
        ntl.loadNetTestString(net_test_string_with_file)

        ntl.checkOptions()
        nt = NetTest(ntl,None)
        nt.initializeInputProcessor()

        # XXX: if you use the same test_class twice you will have consumed all
        # of its inputs!
        tested = set([])
        for test_class, test_method in ntl.testCases:
            if test_class not in tested:
                tested.update([test_class])
                self.assertEqual(len(list(test_class.inputs)), 10)

    def test_setup_local_options_in_test_cases(self):
        ntl = NetTestLoader(dummyArgs)
        ntl.loadNetTestString(net_test_string)

        ntl.checkOptions()

        for test_class, test_method in ntl.testCases:
            self.assertEqual(test_class.localOptions, dummyOptions)

    def test_generate_measurements_size(self):
        ntl = NetTestLoader(dummyArgsWithFile)
        ntl.loadNetTestString(net_test_string_with_file)

        ntl.checkOptions()
        net_test = NetTest(ntl, None)

        net_test.initializeInputProcessor()
        measurements = list(net_test.generateMeasurements())
        self.assertEqual(len(measurements), 20)

    def test_net_test_completed_callback(self):
        ntl = NetTestLoader(dummyArgsWithFile)
        ntl.loadNetTestString(net_test_string_with_file)

        ntl.checkOptions()
        director = Director()

        d = director.startNetTest(ntl, [MockReporter()])

        @d.addCallback
        def complete(result):
            self.assertEqual(result, None)
            self.assertEqual(director.successfulMeasurements, 20)

        return d

    def test_require_root_succeed(self):
        #XXX: will require root to run
        ntl = NetTestLoader(dummyArgs)
        ntl.loadNetTestString(net_test_root_required)

        for test_class, method in ntl.testCases:
            self.assertTrue(test_class.requiresRoot)

class TestNettestTimeout(unittest.TestCase):
    @defer.inlineCallbacks
    def setUp(self):
        from twisted.internet.protocol import Protocol, Factory
        from twisted.internet.endpoints import TCP4ServerEndpoint

        class DummyProtocol(Protocol):
            def dataReceived(self, data):
                pass

        class DummyFactory(Factory):
            def __init__(self):
                self.protocols = []

            def buildProtocol(self, addr):
                proto = DummyProtocol()
                self.protocols.append(proto)
                return proto

            def stopFactory(self):
                for proto in self.protocols:
                    proto.transport.loseConnection()

        self.factory = DummyFactory()
        endpoint = TCP4ServerEndpoint(reactor, 8007)
        self.port = yield endpoint.listen(self.factory)

        config.advanced.measurement_timeout = 2

    def tearDown(self):
        self.factory.stopFactory()
        self.port.stopListening()

    def test_nettest_timeout(self):
        ntl = NetTestLoader(('-u', 'http://localhost:8007/'))
        ntl.loadNetTestString(http_net_test)

        ntl.checkOptions()
        director = Director()

        d = director.startNetTest(ntl, [MockReporter()])

        @d.addCallback
        def complete(result):
            assert director.failedMeasurements == 1

        return d

########NEW FILE########
__FILENAME__ = test_onion
from twisted.trial import unittest 
from ooni.utils import onion

class TestOnion(unittest.TestCase):
    def test_tor_details(self):
        assert isinstance(onion.tor_details, dict)
        assert onion.tor_details['version']
        assert onion.tor_details['binary']

########NEW FILE########
__FILENAME__ = test_oonibclient
import os
import shutil
import socket

from twisted.trial import unittest
from twisted.internet import defer

from ooni import errors as e
from ooni.utils import log
from ooni.settings import config
from ooni.oonibclient import OONIBClient

input_id = '37e60e13536f6afe47a830bfb6b371b5cf65da66d7ad65137344679b24fdccd1'
deck_id = 'd4ae40ecfb3c1b943748cce503ab8233efce7823f3e391058fc0f87829c644ed'

class TestOONIBClient(unittest.TestCase):
    def setUp(self):
        host = '127.0.0.1'
        port = 8889
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.connect((host, port))
            s.shutdown(2)

            data_dir = '/tmp/testooni'
            config.advanced.data_dir = data_dir

            try: shutil.rmtree(data_dir)
            except: pass
            os.mkdir(data_dir)
            os.mkdir(os.path.join(data_dir, 'inputs'))
            os.mkdir(os.path.join(data_dir, 'decks'))
        except Exception as ex:
            self.skipTest("OONIB must be listening on port 8888 to run this test (tor_hidden_service: false)")
        self.oonibclient = OONIBClient('http://' + host + ':' + str(port))
    
    @defer.inlineCallbacks
    def test_query(self):
        res = yield self.oonibclient.queryBackend('GET', '/policy/input')
        self.assertTrue(isinstance(res, list))
    
    @defer.inlineCallbacks
    def test_get_input_list(self):
        input_list = yield self.oonibclient.getInputList()
        self.assertTrue(isinstance(input_list, list))

    @defer.inlineCallbacks
    def test_get_input_descriptor(self):
        input_descriptor = yield self.oonibclient.getInput(input_id)
        for key in ['name', 'description', 
                    'version', 'author', 'date', 'id']:
            self.assertTrue(hasattr(input_descriptor, key))

    @defer.inlineCallbacks
    def test_download_input(self):
        yield self.oonibclient.downloadInput(input_id)

    @defer.inlineCallbacks
    def test_get_deck_list(self):
        deck_list = yield self.oonibclient.getDeckList()
        self.assertTrue(isinstance(deck_list, list))

    @defer.inlineCallbacks
    def test_get_deck_descriptor(self):
        deck_descriptor = yield self.oonibclient.getDeck(deck_id)
        for key in ['name', 'description', 
                    'version', 'author', 'date', 'id']:
            self.assertTrue(hasattr(deck_descriptor, key))

    @defer.inlineCallbacks
    def test_download_deck(self):
        yield self.oonibclient.downloadDeck(deck_id)

    def test_lookup_invalid_helpers(self):
        self.oonibclient.address = 'http://127.0.0.1:8888'
        return self.failUnlessFailure(
                self.oonibclient.lookupTestHelpers([
                    'sdadsadsa', 'dns'
                ]), e.CouldNotFindTestHelper)

    @defer.inlineCallbacks
    def test_lookup_no_test_helpers(self):
        self.oonibclient.address = 'http://127.0.0.1:8888'
        required_helpers = []
        helpers = yield self.oonibclient.lookupTestHelpers(required_helpers)
        self.assertTrue('default' in helpers.keys())

    @defer.inlineCallbacks
    def test_lookup_test_helpers(self):
        self.oonibclient.address = 'http://127.0.0.1:8888'
        required_helpers = [u'http-return-json-headers', u'dns']
        helpers = yield self.oonibclient.lookupTestHelpers(required_helpers)
        self.assertEqual(set(helpers.keys()), set(required_helpers + [u'default']))
        self.assertTrue(helpers['http-return-json-headers']['address'].startswith('http'))
        self.assertTrue(int(helpers['dns']['address'].split('.')[0]))

    @defer.inlineCallbacks
    def test_invalid_requests(self):

        @defer.inlineCallbacks
        def all_requests(path):
            for mthd in ['GET', 'POST', 'PUT', 'OPTION']:
                try:
                    yield self.oonibclient.queryBackend(mthd, path)
                except:
                    pass

        for path in ['/policy/input', '/policy/nettest', 
                '/input', '/input/'+'a'*64, '/fooo']:
            yield all_requests(path)

        for path in ['/bouncer']:
            self.oonibclient.address = 'http://127.0.0.1:8888'
            yield all_requests(path)

    @defer.inlineCallbacks
    def test_create_report(self):
        res = yield self.oonibclient.queryBackend('POST', '/report', {
                'software_name': 'spam',
                'software_version': '2.0',
                'probe_asn': 'AS0',
                'probe_cc': 'ZZ',
                'test_name': 'foobar',
                'test_version': '1.0',
                'input_hashes': []
        })
        assert isinstance(res['report_id'], unicode)

    @defer.inlineCallbacks
    def test_report_lifecycle(self):
        res = yield self.oonibclient.queryBackend('POST', '/report', {
                'software_name': 'spam',
                'software_version': '2.0',
                'probe_asn': 'AS0',
                'probe_cc': 'ZZ',
                'test_name': 'foobar',
                'test_version': '1.0',
                'input_hashes': []
        })
        report_id = str(res['report_id'])

        res = yield self.oonibclient.queryBackend('POST', '/report/'+report_id, {
            'content': '---\nspam: ham\n...\n'
        })

        res = yield self.oonibclient.queryBackend('POST', '/report/'+report_id, {
            'content': '---\nspam: ham\n...\n'
        })
        
        res = yield self.oonibclient.queryBackend('POST', '/report/'+report_id+'/close')

########NEW FILE########
__FILENAME__ = test_oonicli
import os
import sys
import yaml

from twisted.internet import defer
from twisted.trial import unittest

from ooni.tests import is_internet_connected
from ooni.settings import config
from ooni.oonicli import runWithDirector

def verify_header(header):
    assert 'input_hashes' in header.keys()
    assert 'options' in header.keys()
    assert 'probe_asn' in header.keys()
    assert 'probe_cc' in header.keys()
    assert 'probe_ip' in header.keys()
    assert 'software_name' in header.keys()
    assert 'software_version' in header.keys()
    assert 'test_name' in header.keys()
    assert 'test_version' in header.keys()

def verify_entry(entry):
    assert 'input' in entry


class TestRunDirector(unittest.TestCase):
    def setUp(self):
        if not is_internet_connected():
            self.skipTest("You must be connected to the internet to run this test")
        config.tor.socks_port = 9050
        config.tor.control_port = None
        with open('example-input.txt', 'w+') as f:
            f.write('http://torproject.org/\n')
            f.write('http://bridges.torproject.org/\n')
            f.write('http://blog.torproject.org/\n')

    def tearDown(self):
        try:
            os.remove('test_report.yaml')
        except:
            pass
        try:
            os.remove('example-input.txt')
        except:
            pass

    @defer.inlineCallbacks
    def run_test(self, test_name, args, verify_function):
        output_file = 'test_report.yaml'
        sys.argv = ['', '-n', '-o', output_file, test_name]
        sys.argv.extend(args)
        yield runWithDirector(False, False)
        with open(output_file) as f:
            entries = yaml.safe_load_all(f)
            header = entries.next()
            try:
                first_entry = entries.next()
            except StopIteration:
                raise Exception("Missing entry in report")
        verify_header(header)
        verify_entry(first_entry)
        verify_function(first_entry)

    @defer.inlineCallbacks
    def test_http_requests(self):
        def verify_function(entry):
            assert 'body_length_match' in entry
            assert 'body_proportion' in entry
            assert 'control_failure' in entry
            assert 'experiment_failure' in entry
            assert 'factor' in entry
            assert 'headers_diff' in entry
            assert 'headers_match' in entry
        yield self.run_test('blocking/http_requests',
                      ['-u', 'http://torproject.org/'],
                      verify_function)

    @defer.inlineCallbacks
    def test_http_requests_with_file(self):
        def verify_function(entry):
            assert 'body_length_match' in entry
            assert 'body_proportion' in entry
            assert 'control_failure' in entry
            assert 'experiment_failure' in entry
            assert 'factor' in entry
            assert 'headers_diff' in entry
            assert 'headers_match' in entry
        yield self.run_test('blocking/http_requests',
                      ['-f', 'example-input.txt'],
                      verify_function)

    @defer.inlineCallbacks
    def test_dnsconsistency(self):
        def verify_function(entry):
            assert 'queries' in entry
            assert 'control_resolver' in entry
            assert 'tampering' in entry
            assert len(entry['tampering']) == 1
        yield self.run_test('blocking/dns_consistency',
                            ['-b', '8.8.8.8:53',
                             '-t', '8.8.8.8',
                             '-f', 'example-input.txt'],
                            verify_function)

    @defer.inlineCallbacks
    def test_http_header_field_manipulation(self):
        def verify_function(entry):
            assert 'agent' in entry
            assert 'requests' in entry
            assert 'socksproxy' in entry
            assert 'tampering' in entry
            assert 'header_field_name' in entry['tampering']
            assert 'header_field_number' in entry['tampering']
            assert 'header_field_value' in entry['tampering']
            assert 'header_name_capitalization' in entry['tampering']
            assert 'header_name_diff' in entry['tampering']
            assert 'request_line_capitalization' in entry['tampering']
            assert 'total' in entry['tampering']

        yield self.run_test('manipulation/http_header_field_manipulation',
                            ['-b', 'http://64.9.225.221'],
                           verify_function)

########NEW FILE########
__FILENAME__ = test_otime
import unittest
from datetime import datetime
from ooni import otime

test_date = datetime(2002, 6, 26, 22, 45, 49)

class TestOtime(unittest.TestCase):
    def test_timestamp(self):
        self.assertEqual(otime.timestamp(test_date), "2002-06-26T224549Z")

    def test_fromTimestamp(self):
        time_stamp = otime.timestamp(test_date)
        self.assertEqual(test_date, otime.fromTimestamp(time_stamp))



########NEW FILE########
__FILENAME__ = test_reporter
import yaml
import json
import time
from mock import MagicMock

from twisted.internet import defer
from twisted.trial import unittest

from ooni.utils.net import StringProducer
from ooni import errors as e
from ooni.reporter import YAMLReporter, OONIBReporter

class MockTest(object):
    _start_time = time.time()
    report = {'report_content': 'ham'}
    input = 'spam'

test_details = {
    'test_name': 'spam',
    'test_version': '1.0',
    'software_name': 'spam',
    'software_version': '1.0',
    'input_hashes': [],
    'probe_asn': 'AS0'
}

oonib_new_report_message = {
    'report_id': "2014-01-29T202038Z_AS0_"+"A"*50,
    'backend_version': "1.0"
}

oonib_generic_error_message = {
    'error': 'generic-error'
}

class TestYAMLReporter(unittest.TestCase):
    def setUp(self):
        pass

    def test_write_report(self):
        test = MockTest()

        y_reporter = YAMLReporter(test_details)
        y_reporter.createReport()
        y_reporter.testDone(test, 'spam')
        with open(y_reporter.report_path) as f:
            report_entries = yaml.safe_load_all(f)
            # Check for keys in header
            entry = report_entries.next()
            assert all(x in entry for x in ['test_name', 'test_version'])

            entry = report_entries.next()
            # Check for first entry of report
            assert all(x in entry \
                       for x in ['report_content', 'input', \
                                 'test_name', 'test_started', \
                                 'test_runtime'])

class TestOONIBReporter(unittest.TestCase):
    
    def setUp(self):
        self.mock_response = {}
        self.collector_address = 'http://example.com'

        self.oonib_reporter = OONIBReporter(test_details, self.collector_address)
        self.oonib_reporter.agent = MagicMock()
        self.mock_agent_response = MagicMock()
        def deliverBody(body_receiver):
            body_receiver.dataReceived(json.dumps(self.mock_response))
            body_receiver.connectionLost(None)
        self.mock_agent_response.deliverBody = deliverBody
        self.oonib_reporter.agent.request.return_value = defer.succeed(self.mock_agent_response)
    
    @defer.inlineCallbacks
    def test_create_report(self):
        self.mock_response = oonib_new_report_message
        yield self.oonib_reporter.createReport()
        assert self.oonib_reporter.reportID == oonib_new_report_message['report_id']

    @defer.inlineCallbacks
    def test_create_report_failure(self):
        self.mock_response = oonib_generic_error_message
        self.mock_agent_response.code = 406
        yield self.assertFailure(self.oonib_reporter.createReport(), e.OONIBReportCreationError)

    @defer.inlineCallbacks
    def test_write_report_entry(self):
        req = {'content': 'something'}
        yield self.oonib_reporter.writeReportEntry(req)
        assert self.oonib_reporter.agent.request.called


########NEW FILE########
__FILENAME__ = test_safe_represent
import yaml

from twisted.trial import unittest

from ooni.reporter import OSafeDumper

from scapy.all import IP, UDP

class TestScapyRepresent(unittest.TestCase):
    def test_represent_scapy(self):
        data = IP()/UDP()
        yaml.dump_all([data], Dumper=OSafeDumper)



########NEW FILE########
__FILENAME__ = test_templates
from ooni.templates import httpt

from twisted.internet.error import DNSLookupError
from twisted.internet import reactor, defer
from twisted.trial import unittest

class TestHTTPT(unittest.TestCase):
    def setUp(self):
        from twisted.web.resource import Resource
        from twisted.web.server import Site
        class DummyResource(Resource):
            isLeaf = True
            def render_GET(self, request):
                return "%s" % request.method
        r = DummyResource()
        factory = Site(r)
        self.port = reactor.listenTCP(8880, factory)
    
    def tearDown(self):
        self.port.stopListening()

    @defer.inlineCallbacks
    def test_do_request(self):
        http_test = httpt.HTTPTest()
        http_test.localOptions['socksproxy'] = None
        http_test._setUp()
        response = yield http_test.doRequest('http://localhost:8880/')
        assert response.body == "GET"
        assert len(http_test.report['requests']) == 1
        assert 'request' in http_test.report['requests'][0]
        assert 'response' in http_test.report['requests'][0]

    @defer.inlineCallbacks
    def test_do_failing_request(self):
        http_test = httpt.HTTPTest()
        http_test.localOptions['socksproxy'] = None
        http_test._setUp()
        yield self.assertFailure(http_test.doRequest('http://invaliddomain/'), DNSLookupError)
        assert http_test.report['requests'][0]['failure'] == 'dns_lookup_error'

########NEW FILE########
__FILENAME__ = test_trueheaders
from twisted.trial import unittest

from ooni.utils.trueheaders import TrueHeaders

dummy_headers_dict = {
        'Header1': ['Value1', 'Value2'],
        'Header2': ['ValueA', 'ValueB']
}

dummy_headers_dict2 = {
        'Header1': ['Value1', 'Value2'],
        'Header2': ['ValueA', 'ValueB'],
        'Header3': ['ValueA', 'ValueB'],
}

dummy_headers_dict3 = {
        'Header1': ['Value1', 'Value2'],
        'Header2': ['ValueA', 'ValueB'],
        'Header4': ['ValueA', 'ValueB'],
}


class TestTrueHeaders(unittest.TestCase):
    def test_names_match(self):
        th = TrueHeaders(dummy_headers_dict)
        self.assertEqual(th.getDiff(TrueHeaders(dummy_headers_dict)), set())

    def test_names_not_match(self):
        th = TrueHeaders(dummy_headers_dict)
        self.assertEqual(th.getDiff(TrueHeaders(dummy_headers_dict2)), set(['Header3']))

        th = TrueHeaders(dummy_headers_dict3)
        self.assertEqual(th.getDiff(TrueHeaders(dummy_headers_dict2)), set(['Header3', 'Header4']))

    def test_names_match_expect_ignore(self):
        th = TrueHeaders(dummy_headers_dict)
        self.assertEqual(th.getDiff(TrueHeaders(dummy_headers_dict2), ignore=['Header3']), set())





########NEW FILE########
__FILENAME__ = test_txscapy
from mock import MagicMock
from twisted.internet import defer
from twisted.trial import unittest

from ooni.utils import txscapy

defer.setDebugging(True)
class TestTxScapy(unittest.TestCase):
    def setUp(self):
        # if not txscapy.hasRawSocketPermission():
        #     self.skipTest("No raw socket permissions...")
        mock_super_socket = MagicMock()
        mock_super_socket.ins.fileno.return_value = 1
        self.scapy_factory = txscapy.ScapyFactory('foo', mock_super_socket)

    def tearDown(self):
        self.scapy_factory.connectionLost(None)

    def test_pcapdnet_installed(self):
        assert txscapy.pcapdnet_installed() == True
    
    def test_send_packet_no_answer(self):
        from scapy.all import IP, TCP
        sender = txscapy.ScapySender()
        self.scapy_factory.registerProtocol(sender)
        packet = IP(dst='8.8.8.8')/TCP(dport=53)
        sender.startSending([packet])
        self.scapy_factory.super_socket.send.assert_called_with(packet)
        assert len(sender.sent_packets) == 1
    
    @defer.inlineCallbacks
    def test_send_packet_with_answer(self):
        from scapy.all import IP, TCP
        sender = txscapy.ScapySender()
        self.scapy_factory.registerProtocol(sender)

        packet_sent = IP(dst='8.8.8.8',src='127.0.0.1')/TCP(dport=53, sport=5300)
        packet_received = IP(dst='127.0.0.1', src='8.8.8.8')/TCP(sport=53, dport=5300)
        
        d = sender.startSending([packet_sent])
        self.scapy_factory.super_socket.send.assert_called_with(packet_sent)

        sender.packetReceived(packet_received)

        result = yield d
        assert result[0][0][0] == packet_sent
        assert result[0][0][1] == packet_received

########NEW FILE########
__FILENAME__ = test_utils
import os
from twisted.trial import unittest

from ooni.utils import pushFilenameStack, log


class TestUtils(unittest.TestCase):
    def test_pushFilenameStack(self):
        basefilename = os.path.join(os.getcwd(), 'dummyfile')
        f = open(basefilename, "w+")
        f.write("0\n")
        f.close()
        for i in xrange(1, 20):
            f = open(basefilename+".%s" % i, "w+")
            f.write("%s\n" % i)
            f.close()

        pushFilenameStack(basefilename)
        for i in xrange(1, 20):
            f = open(basefilename+".%s" % i)
            c = f.readlines()[0].strip()
            self.assertEqual(str(i-1), str(c))
            f.close()

    def test_log_encode(self):
        logmsgs = (
            (r"spam\x07\x08", "spam\a\b"),
            (r"spam\x07\x08", u"spam\a\b"),
            (r"ham\u237e", u"ham"+u"\u237e")
        )
        for encoded_logmsg, logmsg in logmsgs:
            self.assertEqual(log.log_encode(logmsg), encoded_logmsg)

########NEW FILE########
__FILENAME__ = hacks
# When some software has issues and we need to fix it in a
# hackish way, we put it in here. This one day will be empty.

import copy_reg

def patched_reduce_ex(self, proto):
    """
    This is a hack to overcome a bug in one of pythons core functions. It is
    located inside of copy_reg and is called _reduce_ex.

    Some background on the issue can be found here:

    http://stackoverflow.com/questions/569754/how-to-tell-for-which-object-attribute-pickle
    http://stackoverflow.com/questions/2049849/why-cant-i-pickle-this-object

    There was also an open bug on the pyyaml trac repo, but it got closed because
    they could not reproduce.
    http://pyyaml.org/ticket/190

    It turned out to be easier to patch the python core library than to monkey
    patch yaml.

    XXX see if there is a better way. sigh...
    """
    _HEAPTYPE = 1<<9
    assert proto < 2
    for base in self.__class__.__mro__:
        if hasattr(base, '__flags__') and not base.__flags__ & _HEAPTYPE:
            break
    else:
        base = object # not really reachable
    if base is object:
        state = None
    elif base is int:
        state = None
    else:
        if base is self.__class__:
            raise TypeError, "can't pickle %s objects" % base.__name__
        state = base(self)
    args = (self.__class__, base, state)
    try:
        getstate = self.__getstate__
    except AttributeError:
        if getattr(self, "__slots__", None):
            raise TypeError("a class that defines __slots__ without "
                            "defining __getstate__ cannot be pickled")
        try:
            dict = self.__dict__
        except AttributeError:
            dict = None
    else:
        dict = getstate()
    if dict:
        return copy_reg._reconstructor, args, dict
    else:
        return copy_reg._reconstructor, args


########NEW FILE########
__FILENAME__ = log
import os
import sys
import codecs
import logging
import traceback

from twisted.python import log as txlog
from twisted.python import util
from twisted.python.failure import Failure
from twisted.python.logfile import DailyLogFile

from ooni import otime

# Get rid of the annoying "No route found for
# IPv6 destination warnings":
logging.getLogger("scapy.runtime").setLevel(logging.ERROR)


def log_encode(logmsg):
    """
    I encode logmsg (a str or unicode) as printable ASCII. Each case
    gets a distinct prefix, so that people differentiate a unicode
    from a utf-8-encoded-byte-string or binary gunk that would
    otherwise result in the same final output.
    """
    if isinstance(logmsg, unicode):
        return codecs.encode(logmsg, 'unicode_escape')
    elif isinstance(logmsg, str):
        try:
            unicodelogmsg = logmsg.decode('utf-8')
        except UnicodeDecodeError:
            return codecs.encode(logmsg, 'string_escape')
        else:
            return codecs.encode(unicodelogmsg, 'unicode_escape')
    else:
        raise Exception("I accept only a unicode object or a string, "
                        "not a %s object like %r" % (type(logmsg),
                                                     repr(logmsg)))


class LogWithNoPrefix(txlog.FileLogObserver):
    def emit(self, eventDict):
        text = txlog.textFromEventDict(eventDict)
        if text is None:
            return

        util.untilConcludes(self.write, "%s\n" % text)
        util.untilConcludes(self.flush)  # Hoorj!


class OONILogger(object):
    def start(self, logfile=None, application_name="ooniprobe"):
        from ooni.settings import config

        daily_logfile = None

        if not logfile:
            logfile = os.path.expanduser(config.basic.logfile)

        log_folder = os.path.dirname(logfile)
        log_filename = os.path.basename(logfile)

        daily_logfile = DailyLogFile(log_filename, log_folder)

        txlog.msg("Starting %s on %s (%s UTC)" % (application_name,
                                                  otime.prettyDateNow(),
                                                  otime.utcPrettyDateNow()))

        self.fileObserver = txlog.FileLogObserver(daily_logfile)
        self.stdoutObserver = LogWithNoPrefix(sys.stdout)

        txlog.startLoggingWithObserver(self.stdoutObserver.emit)
        txlog.addObserver(self.fileObserver.emit)

    def stop(self):
        self.stdoutObserver.stop()
        self.fileObserver.stop()

oonilogger = OONILogger()


def start(logfile=None, application_name="ooniprobe"):
    oonilogger.start(logfile, application_name)


def stop():
    oonilogger.stop()


def msg(msg, *arg, **kw):
    from ooni.settings import config
    if config.logging:
        print "%s" % log_encode(msg)


def debug(msg, *arg, **kw):
    from ooni.settings import config
    if config.advanced.debug and config.logging:
        print "[D] %s" % log_encode(msg)


def err(msg, *arg, **kw):
    from ooni.settings import config
    if config.logging:
        if isinstance(msg, Exception):
            msg = "%s: %s" % (msg.__class__.__name__, msg)
        print "[!] %s" % log_encode(msg)


def exception(error):
    """
    Error can either be an error message to print to stdout and to the logfile
    or it can be a twisted.python.failure.Failure instance.
    """
    if isinstance(error, Failure):
        error.printTraceback()
    else:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_exception(exc_type, exc_value, exc_traceback)

########NEW FILE########
__FILENAME__ = net
import sys
import socket
from random import randint

from zope.interface import implements
from twisted.internet import protocol, defer
from twisted.internet import threads, reactor
from twisted.web.iweb import IBodyProducer

from ooni.utils import log

#if sys.platform.system() == 'Windows':
#    import _winreg as winreg

# These user agents are taken from the "How Unique Is Your Web Browser?"
# (https://panopticlick.eff.org/browser-uniqueness.pdf) paper as the browser user
# agents with largest anonymity set.

userAgents = ("Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.1.7) Gecko/20091221 Firefox/3.5.7",
    "Mozilla/5.0 (iPhone; U; CPU iPhone OS 3 1 2 like Mac OS X; en-us) AppleWebKit/528.18 (KHTML, like Gecko) Mobile/7D11",
    "Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US; rv:1.9.2) Gecko/20100115 Firefox/3.6",
    "Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.2) Gecko/20100115 Firefox/3.6",
    "Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.2) Gecko/20100115 Firefox/3.6",
    "Mozilla/5.0 (Windows; U; Windows NT 5.1; de; rv:1.9.2) Gecko/20100115 Firefox/3.6",
    "Mozilla/5.0 (Windows; U; Windows NT 6.1; de; rv:1.9.2) Gecko/20100115 Firefox/3.6",
    "Mozilla/5.0 (Windows; U; Windows NT 5.1; de; rv:1.9.2) Gecko/20100115 Firefox/3.6",
    "Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US; rv:1.9.1.7) Gecko/20091221 Firefox/3.5.7",
    "Mozilla/5.0 (Windows; U; Windows NT 5.1; de; rv:1.9.1.7) Gecko/20091221 Firefox/3.5.7 (.NET CLR 3.5.30729)")

class UnsupportedPlatform(Exception):
    """Support for this platform is not currently available."""

class IfaceError(Exception):
    """Could not find default network interface."""

class PermissionsError(SystemExit):
    """This test requires admin or root privileges to run. Exiting..."""

PLATFORMS = {'LINUX': sys.platform.startswith("linux"),
             'OPENBSD': sys.platform.startswith("openbsd"),
             'FREEBSD': sys.platform.startswith("freebsd"),
             'NETBSD': sys.platform.startswith("netbsd"),
             'DARWIN': sys.platform.startswith("darwin"),
             'SOLARIS': sys.platform.startswith("sunos"),
             'WINDOWS': sys.platform.startswith("win32")}

class StringProducer(object):
    implements(IBodyProducer)

    def __init__(self, body):
        self.body = body
        self.length = len(body)

    def startProducing(self, consumer):
        consumer.write(self.body)
        return defer.succeed(None)

    def pauseProducing(self):
        pass

    def stopProducing(self):
        pass

class BodyReceiver(protocol.Protocol):
    def __init__(self, finished, content_length=None, body_processor=None):
        self.finished = finished
        self.data = ""
        self.bytes_remaining = content_length
        self.body_processor = body_processor

    def dataReceived(self, b):
        self.data += b
        if self.bytes_remaining:
            if self.bytes_remaining == 0:
                self.connectionLost(None)
            else:
                self.bytes_remaining -= len(b)

    def connectionLost(self, reason):
        try:
            if self.body_processor:
                self.data = self.body_processor(self.data)
            self.finished.callback(self.data)
        except Exception as exc:
            self.finished.errback(exc)

class Downloader(protocol.Protocol):
    def __init__(self,  download_path,
                 finished, content_length=None):
        self.finished = finished
        self.bytes_remaining = content_length
        self.fp = open(download_path, 'w+')

    def dataReceived(self, b):
        self.fp.write(b)
        if self.bytes_remaining:
            if self.bytes_remaining == 0:
                self.connectionLost(None)
            else:
                self.bytes_remaining -= len(b)

    def connectionLost(self, reason):
        self.fp.flush()
        self.fp.close()
        self.finished.callback(None)

def getSystemResolver():
    """
    XXX implement a function that returns the resolver that is currently
    default on the system.
    """

def getClientPlatform(platform_name=None):
    for name, test in PLATFORMS.items():
        if not platform_name or platform_name.upper() == name:
            if test:
                return name, test

def getPosixIfaces():
    from twisted.internet.test import _posixifaces

    log.msg("Attempting to discover network interfaces...")
    ifaces = _posixifaces._interfaces()
    ifup = tryInterfaces(ifaces)
    return ifup

def getWindowsIfaces():
    from twisted.internet.test import _win32ifaces

    log.msg("Attempting to discover network interfaces...")
    ifaces = _win32ifaces._interfaces()
    ifup = tryInterfaces(ifaces)
    return ifup

def getIfaces(platform_name=None):
    client, test = getClientPlatform(platform_name)
    if client:
        if client == ('LINUX' or 'DARWIN') or client[-3:] == 'BSD':
            return getPosixIfaces()
        elif client == 'WINDOWS':
            return getWindowsIfaces()
        ## XXX fixme figure out how to get iface for Solaris
        else:
            return None
    else:
        raise UnsupportedPlatform

def randomFreePort(addr="127.0.0.1"):
    """
    Args:

        addr (str): the IP address to attempt to bind to.

    Returns an int representing the free port number at the moment of calling

    Note: there is no guarantee that some other application will attempt to
    bind to this port once this function has been called.
    """
    free = False
    while not free:
        port = randint(1024, 65535)
        s = socket.socket()
        try:
            s.bind((addr, port))
            free = True
        except:
            pass
        s.close()
    return port


def checkInterfaces(ifaces=None, timeout=1):
    """
    @param ifaces:
        A dictionary in the form of ifaces['if_name'] = 'if_addr'.
    """
    try:
        from scapy.all import IP, ICMP
        from scapy.all import sr1   ## we want this check to be blocking
    except:
        log.msg(("Scapy required: www.secdev.org/projects/scapy"))

    ifup = {}
    if not ifaces:
        log.debug("checkInterfaces(): no interfaces specified!")
        return None

    for iface in ifaces:
        for ifname, ifaddr in iface:
            log.debug("checkInterfaces(): testing iface {} by pinging"
                      + " local address {}".format(ifname, ifaddr))
            try:
                pkt = IP(dst=ifaddr)/ICMP()
                ans, unans = sr(pkt, iface=ifname, timeout=5, retry=3)
            except Exception, e:
                raise PermissionsError if e.find("Errno 1") else log.err(e)
            else:
                if ans.summary():
                    log.debug("checkInterfaces(): got answer on interface %s"
                             + ":\n%s".format(ifname, ans.summary()))
                    ifup.update(ifname, ifaddr)
                else:
                    log.debug("Interface test packet was unanswered:\n%s"
                             % unans.summary())
    if len(ifup) > 0:
        log.msg("Discovered working network interfaces: %s" % ifup)
        return ifup
    else:
        raise IfaceError

def getNonLoopbackIfaces(platform_name=None):
    try:
        ifaces = getIfaces(platform_name)
    except UnsupportedPlatform, up:
        log.err(up)

    if not ifaces:
        log.msg("Unable to discover network interfaces...")
        return None
    else:
        found = [{i[0]: i[2]} for i in ifaces if i[0] != 'lo']
        log.debug("getNonLoopbackIfaces: Found non-loopback interfaces: %s"
                  % found)
        try:
            interfaces = checkInterfaces(found)
        except IfaceError, ie:
            log.err(ie)
            return None
        else:
            return interfaces


def getLocalAddress():
    default_iface = getDefaultIface()
    return default_iface.ipaddr


########NEW FILE########
__FILENAME__ = onion
import string
import subprocess
from distutils.version import LooseVersion

from txtorcon.util import find_tor_binary as tx_find_tor_binary

from ooni.settings import config

class TorVersion(LooseVersion):
    pass

def find_tor_binary():
    if config.advanced.tor_binary:
        return config.advanced.tor_binary
    return tx_find_tor_binary()

def tor_version():
    tor_binary = find_tor_binary()
    if not tor_binary:
        return None
    try:
        proc = subprocess.Popen((tor_binary, '--version'),
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except OSError:
        pass
    else:
        stdout, _ = proc.communicate()
        if proc.poll() == 0 and stdout != '':
            return TorVersion(stdout.strip().split(' ')[2])
    return None

def transport_name(address):
    """
    If the address of the bridge starts with a valid c identifier then
    we consider it to be a bridge.
    Returns:
        The transport_name if it's a transport.
        None if it's not a obfsproxy bridge.
    """
    transport_name = address.split(' ')[0]
    transport_name_chars = string.ascii_letters + string.digits
    if all(c in transport_name_chars for c in transport_name):
        return transport_name
    else:
        return None

tor_details = {
    'binary': find_tor_binary(),
    'version': tor_version()
}

########NEW FILE########
__FILENAME__ = trueheaders
# :authors: Giovanni Pellerano
# :licence: see LICENSE
#
# Here we make sure that the HTTP Headers sent and received are True. By this
# we mean that they are not normalized and that the ordering is maintained.

import struct
import itertools
from copy import copy

from zope.interface import implements
from twisted.web import client, _newclient, http_headers
from twisted.web._newclient import Request, RequestNotSent, RequestGenerationFailed, TransportProxyProducer, STATUS
from twisted.internet import protocol, reactor
from twisted.internet.protocol import ClientFactory, Protocol
from twisted.internet.endpoints import TCP4ClientEndpoint, SSL4ClientEndpoint
from twisted.internet import interfaces, defer
from twisted.internet.defer import Deferred, succeed, fail, maybeDeferred

from txsocksx.http import SOCKS5Agent
from txsocksx.client import SOCKS5ClientFactory
SOCKS5ClientFactory.noisy = False

from ooni.utils import log

class TrueHeaders(http_headers.Headers):
    def __init__(self, rawHeaders=None):
        self._rawHeaders = dict()
        if rawHeaders is not None:
            for name, values in rawHeaders.iteritems():
                if type(values) is list:
                  self.setRawHeaders(name, values[:])
                elif type(values) is dict:
                  self._rawHeaders[name.lower()] = values
                elif type(values) is str:
                  self.setRawHeaders(name, values)

    def setRawHeaders(self, name, values):
        if name.lower() not in self._rawHeaders:
          self._rawHeaders[name.lower()] = dict()
        self._rawHeaders[name.lower()]['name'] = name
        self._rawHeaders[name.lower()]['values'] = values

    def getDiff(self, headers, ignore=[]):
        """

        Args:

            headers: a TrueHeaders object

            ignore: specify a list of header fields to ignore

        Returns:

            a set containing the header names that are not present in
            header_dict or not present in self.
        """
        diff = set()
        field_names = []

        headers_a = copy(self)
        headers_b = copy(headers)
        for name in ignore:
            try:
                del headers_a._rawHeaders[name.lower()]
            except KeyError:
                pass
            try:
                del headers_b._rawHeaders[name.lower()]
            except KeyError:
                pass

        for k, v in itertools.chain(headers_a.getAllRawHeaders(), \
                headers_b.getAllRawHeaders()):
            field_names.append(k)

        for name in field_names:
            if self.getRawHeaders(name) and headers.getRawHeaders(name):
                pass
            else:
                diff.add(name)
        return diff

    def getAllRawHeaders(self):
        for k, v in self._rawHeaders.iteritems():
            yield v['name'], v['values']

    def getRawHeaders(self, name, default=None):
        if name.lower() in self._rawHeaders:
            return self._rawHeaders[name.lower()]['values']
        return default

class HTTPClientParser(_newclient.HTTPClientParser):
    def logPrefix(self):
        return 'HTTPClientParser'

    def connectionMade(self):
        self.headers = TrueHeaders()
        self.connHeaders = TrueHeaders()
        self.state = STATUS
        self._partialHeader = None

    def headerReceived(self, name, value):
        if self.isConnectionControlHeader(name):
            headers = self.connHeaders
        else:
            headers = self.headers
        headers.addRawHeader(name, value)

class HTTP11ClientProtocol(_newclient.HTTP11ClientProtocol):
    def request(self, request):
        if self._state != 'QUIESCENT':
            return fail(RequestNotSent())

        self._state = 'TRANSMITTING'
        _requestDeferred = maybeDeferred(request.writeTo, self.transport)
        self._finishedRequest = Deferred()

        self._currentRequest = request

        self._transportProxy = TransportProxyProducer(self.transport)
        self._parser = HTTPClientParser(request, self._finishResponse)
        self._parser.makeConnection(self._transportProxy)
        self._responseDeferred = self._parser._responseDeferred

        def cbRequestWrotten(ignored):
            if self._state == 'TRANSMITTING':
                self._state = 'WAITING'
                self._responseDeferred.chainDeferred(self._finishedRequest)

        def ebRequestWriting(err):
            if self._state == 'TRANSMITTING':
                self._state = 'GENERATION_FAILED'
                self.transport.loseConnection()
                self._finishedRequest.errback(
                    Failure(RequestGenerationFailed([err])))
            else:
                log.err(err, 'Error writing request, but not in valid state '
                             'to finalize request: %s' % self._state)

        _requestDeferred.addCallbacks(cbRequestWrotten, ebRequestWriting)

        return self._finishedRequest

class _HTTP11ClientFactory(client._HTTP11ClientFactory):
    noisy = False
    def buildProtocol(self, addr):
        return HTTP11ClientProtocol(self._quiescentCallback)

class HTTPConnectionPool(client.HTTPConnectionPool):
    _factory = _HTTP11ClientFactory

class TrueHeadersAgent(client.Agent):
    def __init__(self, *args, **kw):
        super(TrueHeadersAgent, self).__init__(*args, **kw)
        self._pool = HTTPConnectionPool(reactor, False)

class TrueHeadersSOCKS5Agent(SOCKS5Agent):
    def __init__(self, *args, **kw):
        super(TrueHeadersSOCKS5Agent, self).__init__(*args, **kw)
        self._pool = HTTPConnectionPool(reactor, False)

########NEW FILE########
__FILENAME__ = txscapy
import ipaddr
import struct
import socket
import os
import sys
import time
import random

from twisted.internet import protocol, base, fdesc
from twisted.internet import reactor, threads, error
from twisted.internet import defer, abstract
from zope.interface import implements

from scapy.config import conf
from scapy.supersocket import L3RawSocket
from scapy.all import RandShort, IP, IPerror, ICMP, ICMPerror
from scapy.all import TCP, TCPerror, UDP, UDPerror

from ooni.utils import log
from ooni.settings import config

class LibraryNotInstalledError(Exception):
    pass

def pcapdnet_installed():
    """
    Checks to see if libdnet or libpcap are installed and set the according
    variables.

    Returns:

        True
            if pypcap and libdnet are installed

        False
            if one of the two is absent
    """
    # In debian libdnet is called dumbnet instead of dnet, but scapy is
    # expecting "dnet" so we try and import it under such name.
    try:
        import dumbnet
        sys.modules['dnet'] = dumbnet
    except ImportError: pass

    try:
        conf.use_pcap = True
        conf.use_dnet = True
        from scapy.arch import pcapdnet

        config.pcap_dnet = True

    except ImportError:
        log.err("pypcap or dnet not installed. "
                "Certain tests may not work.")

        config.pcap_dnet = False
        conf.use_pcap = False
        conf.use_dnet = False

    # This is required for unix systems that are different than linux (OSX for
    # example) since scapy explicitly wants pcap and libdnet installed for it
    # to work.
    try:
        from scapy.arch import pcapdnet
    except ImportError:
        log.err("Your platform requires to having libdnet and libpcap installed.")
        raise LibraryNotInstalledError

    return config.pcap_dnet

if pcapdnet_installed():
    from scapy.all import PcapWriter

else:
    class DummyPcapWriter:
        def __init__(self, pcap_filename, *arg, **kw):
            log.err("Initializing DummyPcapWriter. We will not actually write to a pcapfile")

        @staticmethod
        def write(self):
            pass

    PcapWriter = DummyPcapWriter

from scapy.all import Gen, SetGen, MTU

def getNetworksFromRoutes():
    """ Return a list of networks from the routing table """
    from scapy.all import conf, ltoa, read_routes
    from ipaddr    import IPNetwork, IPAddress

    ## Hide the 'no routes' warnings
    conf.verb = 0

    networks = []
    for nw, nm, gw, iface, addr in read_routes():
        n = IPNetwork( ltoa(nw) )
        (n.netmask, n.gateway, n.ipaddr) = [IPAddress(x) for x in [nm, gw, addr]]
        n.iface = iface
        if not n.compressed in networks:
            networks.append(n)

    return networks

class IfaceError(Exception):
    pass

def getAddresses():
    from scapy.all import get_if_addr, get_if_list
    from ipaddr import IPAddress
    addresses = set()
    for i in get_if_list():
        try:
            addresses.add(get_if_addr(i))
        except:
            pass
    if '0.0.0.0' in addresses:
        addresses.remove('0.0.0.0')
    return [IPAddress(addr) for addr in addresses]

def getDefaultIface():
    """ Return the default interface or raise IfaceError """
    #XXX: currently broken on OpenVZ environments, because
    # the routing table does not contain a default route
    # Workaround: Set the default interface in ooniprobe.conf
    networks = getNetworksFromRoutes()
    for net in networks:
        if net.is_private:
            return net.iface
    raise IfaceError

def hasRawSocketPermission():
    try:
        socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_RAW)
        return True
    except socket.error:
        return False

class ProtocolNotRegistered(Exception):
    pass

class ProtocolAlreadyRegistered(Exception):
    pass

class ScapyFactory(abstract.FileDescriptor):
    """
    Inspired by muxTCP scapyLink:
    https://github.com/enki/muXTCP/blob/master/scapyLink.py
    """
    def __init__(self, interface, super_socket=None, timeout=5):

        abstract.FileDescriptor.__init__(self, reactor)
        if interface == 'auto':
            interface = getDefaultIface()
        if not super_socket and sys.platform == 'darwin':
            super_socket = conf.L3socket(iface=interface, promisc=True, filter='')
        elif not super_socket:
            super_socket = L3RawSocket(iface=interface, promisc=True)

        self.protocols = []
        fdesc._setCloseOnExec(super_socket.ins.fileno())
        self.super_socket = super_socket

    def writeSomeData(self, data):
        """
        XXX we actually want to use this, but this requires overriding doWrite
        or writeSequence.
        """
        pass

    def send(self, packet):
        """
        Write a scapy packet to the wire.
        """
        return self.super_socket.send(packet)

    def fileno(self):
        return self.super_socket.ins.fileno()

    def doRead(self):
        packet = self.super_socket.recv(MTU)
        if packet:
            for protocol in self.protocols:
                protocol.packetReceived(packet)

    def registerProtocol(self, protocol):
        if not self.connected:
            self.startReading()

        if protocol not in self.protocols:
            protocol.factory = self
            self.protocols.append(protocol)
        else:
            raise ProtocolAlreadyRegistered

    def unRegisterProtocol(self, protocol):
        if protocol in self.protocols:
            self.protocols.remove(protocol)
            if len(self.protocols) == 0:
                self.loseConnection()
        else:
            raise ProtocolNotRegistered

class ScapyProtocol(object):
    factory = None

    def packetReceived(self, packet):
        """
        When you register a protocol, this method will be called with argument
        the packet it received.

        Every protocol that is registered will have this method called.
        """
        raise NotImplementedError

class ScapySender(ScapyProtocol):
    timeout = 5

    # This deferred will fire when we have finished sending a receiving packets.
    # Should we look for multiple answers for the same sent packet?
    multi = False

    # When 0 we stop when all the packets we have sent have received an
    # answer
    expected_answers = 0

    def processPacket(self, packet):
        """
        Hook useful for processing packets as they come in.
        """

    def processAnswer(self, packet, answer_hr):
        log.debug("Got a packet from %s" % packet.src)
        log.debug("%s" % self.__hash__)
        for i in range(len(answer_hr)):
            if packet.answers(answer_hr[i]):
                self.answered_packets.append((answer_hr[i], packet))
                if not self.multi:
                    del(answer_hr[i])
                break

        if len(self.answered_packets) == len(self.sent_packets):
            log.debug("All of our questions have been answered.")
            self.stopSending()
            return

        if self.expected_answers and \
                self.expected_answers == len(self.answered_packets):
            log.debug("Got the number of expected answers")
            self.stopSending()

    def packetReceived(self, packet):
        timeout = time.time() - self._start_time
        if self.timeout and time.time() - self._start_time > self.timeout:
            self.stopSending()
        if packet:
            self.processPacket(packet)
            # A string that has the same value for the request than for the
            # response.
            hr = packet.hashret()
            if hr in self.hr_sent_packets:
                answer_hr = self.hr_sent_packets[hr]
                self.processAnswer(packet, answer_hr)

    def stopSending(self):
        result = (self.answered_packets, self.sent_packets)
        self.d.callback(result)
        self.factory.unRegisterProtocol(self)

    def sendPackets(self, packets):
        if not isinstance(packets, Gen):
            packets = SetGen(packets)
        for packet in packets:
            hashret = packet.hashret()
            if hashret in self.hr_sent_packets:
                self.hr_sent_packets[hashret].append(packet)
            else:
                self.hr_sent_packets[hashret] = [packet]
            self.sent_packets.append(packet)
            self.factory.send(packet)

    def startSending(self, packets):
        # This dict is used to store the unique hashes that allow scapy to
        # match up request with answer
        self.hr_sent_packets = {}

        # These are the packets we have received as answer to the ones we sent
        self.answered_packets = []

        # These are the packets we send
        self.sent_packets = []

        self._start_time = time.time()
        self.d = defer.Deferred()
        self.sendPackets(packets)
        return self.d

class ScapySniffer(ScapyProtocol):
    def __init__(self, pcap_filename, *arg, **kw):
        self.pcapwriter = PcapWriter(pcap_filename, *arg, **kw)

    def packetReceived(self, packet):
        self.pcapwriter.write(packet)

class ParasiticTraceroute(ScapyProtocol):
    def __init__(self):
        self.numHosts = 7
        self.rate = 15
        self.hosts = {}
        self.ttl_max = 15
        self.ttl_min = 1
        self.sent_packets = []
        self.received_packets = []
        self.matched_packets = {}
        self.addresses = [str(x) for x in getAddresses()]

    def sendPacket(self, packet):
        self.factory.send(packet)

    def packetReceived(self, packet):
        try:
            packet[IP]
        except IndexError:
            return

        if isinstance(packet.getlayer(3), TCPerror):
            self.received_packets.append(packet)
            return

        elif packet.dst in self.hosts:
            if random.randint(1, 100) > self.rate:
                return
            try:
                packet[IP].ttl = self.hosts[packet.dst]['ttl'].pop()
                del packet.chksum #XXX Why is this incorrect?
                log.debug("Sent packet to %s with ttl %d" % (packet.dst, packet.ttl))
                self.sendPacket(packet)
                k = (packet.id, packet[TCP].sport, packet[TCP].dport, packet[TCP].seq)
                self.matched_packets[k] = {'ttl': packet.ttl}
                return
            except IndexError:
                pass
            return

        def maxttl(packet=None):
            if packet:
                return min(self.ttl_max,
                        min(
                            abs( 64  - packet.ttl ),
                            abs( 128 - packet.ttl ),
                            abs( 256 - packet.ttl ))) - 1
            else:
                return self.ttl_max

        def genttl(packet=None):
            ttl = range(self.ttl_min, maxttl(packet))
            random.shuffle(ttl)
            return ttl

        if len(self.hosts) < self.numHosts:
            if packet.dst not in self.hosts \
                    and packet.dst not in self.addresses \
                    and isinstance(packet.getlayer(1), TCP):

                self.hosts[packet.dst] = {'ttl' : genttl()}
                log.debug("Tracing to %s" % packet.dst)

            elif packet.src not in self.hosts \
                    and packet.src not in self.addresses \
                    and isinstance(packet.getlayer(1), TCP):

                self.hosts[packet.src] = {'ttl' : genttl(packet),
                        'ttl_max': maxttl(packet)}
                log.debug("Tracing to %s" % packet.src)
            return

        elif packet.src in self.hosts and not 'ttl_max' in self.hosts[packet.src]:
            self.hosts[packet.src]['ttl_max'] = ttl_max = maxttl(packet)
            log.debug("set ttl_max to %d for host %s" % (ttl_max, packet.src))
            ttl = []
            for t in self.hosts[packet.src]['ttl']:
                if t < ttl_max:
                    ttl.append(t)
            self.hosts[packet.src]['ttl'] = ttl
            return

    def stopListening(self):
        self.factory.unRegisterProtocol(self)

class MPTraceroute(ScapyProtocol):
    dst_ports = [0, 22, 23, 53, 80, 123, 443, 8080, 65535]
    ttl_min = 1
    ttl_max = 30

    def __init__(self):
        self.sent_packets = []
        self._recvbuf = []
        self.received_packets = {}
        self.matched_packets = {}
        self.hosts = []
        self.interval = 0.2
        self.timeout = ((self.ttl_max - self.ttl_min) * len(self.dst_ports) * self.interval) + 5
        self.numPackets = 1

    def ICMPTraceroute(self, host):
        if host not in self.hosts: self.hosts.append(host)

        d = defer.Deferred()
        reactor.callLater(self.timeout, d.callback, self)

        self.sendPackets(IP(dst=host,ttl=(self.ttl_min,self.ttl_max), id=RandShort())/ICMP(id=RandShort()))
        return d

    def UDPTraceroute(self, host):
        if host not in self.hosts: self.hosts.append(host)

        d = defer.Deferred()
        reactor.callLater(self.timeout, d.callback, self)

        for dst_port in self.dst_ports:
            self.sendPackets(IP(dst=host,ttl=(self.ttl_min,self.ttl_max), id=RandShort())/UDP(dport=dst_port, sport=RandShort()))
        return d

    def TCPTraceroute(self, host):
        if host not in self.hosts: self.hosts.append(host)

        d = defer.Deferred()
        reactor.callLater(self.timeout, d.callback, self)

        for dst_port in self.dst_ports:
            self.sendPackets(IP(dst=host,ttl=(self.ttl_min,self.ttl_max), id=RandShort())/TCP(flags=2L, dport=dst_port, sport=RandShort(), seq=RandShort()))
        return d

    @defer.inlineCallbacks
    def sendPackets(self, packets):
        def sleep(seconds):
            d = defer.Deferred()
            reactor.callLater(seconds, d.callback, seconds)
            return d

        if not isinstance(packets, Gen):
            packets = SetGen(packets)

        for packet in packets:
            for i in xrange(self.numPackets):
                self.sent_packets.append(packet)
                self.factory.super_socket.send(packet)
                yield sleep(self.interval)

    def matchResponses(self):
        def addToReceivedPackets(key, packet):
            """
            Add a packet into the received packets dictionary,
            typically the key is a tuple of packet fields used
            to correlate sent packets with recieved packets.
            """

            # Initialize or append to the lists of packets
            # with the same key
            if key in self.received_packets:
                self.received_packets[key].append(packet)
            else:
                self.received_packets[key] = [packet]

        def matchResponse(k, p):
            if k in self.received_packets:
                if p in self.matched_packets:
                    log.debug("Matched sent packet to more than one response!")
                    self.matched_packets[p].extend(self.received_packets[k])
                else:
                    self.matched_packets[p] = self.received_packets[k]
                log.debug("Packet %s matched %s" % ([p], self.received_packets[k]))
                return 1
            return 0

        for p in self._recvbuf:
            l = p.getlayer(2)
            if isinstance(l, IPerror):
                pid = l.id
                l = p.getlayer(3)
                if isinstance(l, ICMPerror):
                    addToReceivedPackets(('icmp', l.id), p)
                elif isinstance(l, TCPerror):
                    addToReceivedPackets(('tcp', l.dport, l.sport), p)
                elif isinstance(l, UDPerror):
                    addToReceivedPackets(('udp', l.dport, l.sport), p)
            elif hasattr(p, 'src') and p.src in self.hosts:
                l = p.getlayer(1)
                if isinstance(l, ICMP):
                    addToReceivedPackets(('icmp', l.id), p)
                elif isinstance(l, TCP):
                    addToReceivedPackets(('tcp', l.ack - 1, l.dport, l.sport), p)
                elif isinstance(l, UDP):
                    addToReceivedPackets(('udp', l.dport, l.sport), p)

        for p in self.sent_packets:
            # for each sent packet, find corresponding
            # received packets
            l = p.getlayer(1)
            i = 0
            if isinstance(l, ICMP):
                i += matchResponse(('icmp', p.id), p) # match by ipid
                i += matchResponse(('icmp', l.id), p) # match by icmpid
            if isinstance(l, TCP):
                i += matchResponse(('tcp', l.dport, l.sport), p) # match by s|dport 
                i += matchResponse(('tcp', l.seq, l.sport, l.dport), p)
            if isinstance(l, UDP):
                i += matchResponse(('udp', l.dport, l.sport), p)
                i += matchResponse(('udp', l.sport, l.dport), p)
            if i == 0:
                log.debug("No response for packet %s" % [p])

        del self._recvbuf

    def packetReceived(self, packet):
        l = packet.getlayer(1)
        if not l:
            return
        elif (isinstance(l, ICMP) or isinstance(l, UDP) or
                isinstance(l, TCP)):
            self._recvbuf.append(packet)

    def stopListening(self):
        self.factory.unRegisterProtocol(self)

########NEW FILE########
__FILENAME__ = example_parser
# This is an example of how to parse ooniprobe reports

from pprint import pprint
import yaml
import sys
print "Opening %s" % sys.argv[1]
f = open(sys.argv[1])
yamloo = yaml.safe_load_all(f)

report_header = yamloo.next()
print "ASN: %s" % report_header['probe_asn']
print "CC: %s" % report_header['probe_cc']
print "IP: %s" % report_header['probe_ip']
print "Start Time: %s" % report_header['start_time']
print "Test name: %s" % report_header['test_name']
print "Test version: %s" % report_header['test_version']

for report_entry in yamloo:
    pprint(report_entry)

f.close()

########NEW FILE########
