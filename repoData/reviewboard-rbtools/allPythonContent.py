__FILENAME__ = release
#!/usr/bin/env python
#
# Performs a release of RBTools. This can only be run by the core
# developers with release permissions.
#

import hashlib
import mimetools
import os
import shutil
import subprocess
import sys
import tempfile
import urllib2

from fabazon.s3 import S3Bucket

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from rbtools import __version__, __version_info__, is_release


PY_VERSIONS = ["2.5", "2.6", "2.7"]

LATEST_PY_VERSION = PY_VERSIONS[-1]

PACKAGE_NAME = 'RBTools'

RELEASES_BUCKET_NAME = 'downloads.reviewboard.org'
RELEASES_BUCKET_KEY = '/releases/%s/%s.%s/' % (PACKAGE_NAME,
                                               __version_info__[0],
                                               __version_info__[1])

RBWEBSITE_API_URL = 'http://www.reviewboard.org/api/'
RELEASES_API_URL = '%sproducts/rbtools/releases/' % RBWEBSITE_API_URL


built_files = []


def load_config():
    filename = os.path.join(os.path.expanduser('~'), '.rbwebsiterc')

    if not os.path.exists(filename):
        sys.stderr.write("A .rbwebsiterc file must exist in the form of:\n")
        sys.stderr.write("\n")
        sys.stderr.write("USERNAME = '<username>'\n")
        sys.stderr.write("PASSWORD = '<password>'\n")
        sys.exit(1)

    user_config = {}

    try:
        execfile(filename, user_config)
    except SyntaxError, e:
        sys.stderr.write('Syntax error in config file: %s\n'
                         'Line %i offset %i\n' % (filename, e.lineno, e.offset))
        sys.exit(1)

    auth_handler = urllib2.HTTPBasicAuthHandler()
    auth_handler.add_password(realm='Web API',
                              uri=RBWEBSITE_API_URL,
                              user=user_config['USERNAME'],
                              passwd=user_config['PASSWORD'])
    opener = urllib2.build_opener(auth_handler)
    urllib2.install_opener(opener)


def execute(cmdline):
    if isinstance(cmdline, list):
        print ">>> %s" % subprocess.list2cmdline(cmdline)
    else:
        print ">>> %s" % cmdline

    p = subprocess.Popen(cmdline,
                         shell=True,
                         stdout=subprocess.PIPE)

    s = ''

    for data in p.stdout.readlines():
        s += data
        sys.stdout.write(data)

    rc = p.wait()

    if rc != 0:
        print "!!! Error invoking command."
        sys.exit(1)

    return s


def run_setup(target, pyver=LATEST_PY_VERSION):
    execute("python%s ./setup.py release %s" % (pyver, target))


def clone_git_tree(git_dir):
    new_git_dir = tempfile.mkdtemp(prefix='rbtools-release.')

    os.chdir(new_git_dir)
    execute('git clone %s .' % git_dir)

    return new_git_dir


def build_targets():
    for pyver in PY_VERSIONS:
        run_setup('bdist_egg', pyver)
        built_files.append(('dist/%s-%s-py%s.egg'
                            % (PACKAGE_NAME, __version__, pyver),
                            'application/octet-stream'))

    run_setup('sdist')
    built_files.append(('dist/%s-%s.tar.gz' % (PACKAGE_NAME, __version__),
                        'application/x-tar'))


def build_checksums():
    sha_filename = 'dist/%s-%s.sha256sum' % (PACKAGE_NAME, __version__)
    out_f = open(sha_filename, 'w')

    for filename, mimetype in built_files:
        m = hashlib.sha256()

        in_f = open(filename, 'r')
        m.update(in_f.read())
        in_f.close()

        out_f.write('%s  %s\n' % (m.hexdigest(), os.path.basename(filename)))

    out_f.close()
    built_files.append((sha_filename, 'text/plain'))


def upload_files():
    bucket = S3Bucket(RELEASES_BUCKET_NAME)

    for filename, mimetype in built_files:
        bucket.upload(filename,
                      '%s/%s' % (RELEASES_BUCKET_KEY,
                                 filename.split('/')[-1]),
                      mimetype=mimetype,
                      public=True)

    bucket.upload_directory_index(RELEASES_BUCKET_KEY)

    # This may be a new directory, so rebuild the parent as well.
    parent_key = '/'.join(RELEASES_BUCKET_KEY.split('/')[:-2])
    bucket.upload_directory_index(parent_key)


def tag_release():
    execute("git tag release-%s" % __version__)


def register_release():
    if __version_info__[4] == 'final':
        run_setup("register")

    scm_revision = execute(['git rev-parse', 'release-%s' % __version__])

    data = {
        'major_version': __version_info__[0],
        'minor_version': __version_info__[1],
        'micro_version': __version_info__[2],
        'patch_version': __version_info__[3],
        'release_type': __version_info__[4],
        'release_num': __version_info__[5],
        'scm_revision': scm_revision,
    }

    boundary = mimetools.choose_boundary()
    content = ''

    for key, value in data.iteritems():
        content += '--%s\r\n' % boundary
        content += 'Content-Disposition: form-data; name="%s"\r\n' % key
        content += '\r\n'
        content += str(value) + '\r\n'

    content += '--%s--\r\n' % boundary
    content += '\r\n'

    headers = {
        'Content-Type': 'multipart/form-data; boundary=%s' % boundary,
        'Content-Length': str(len(content)),
    }

    print 'Posting release to reviewboard.org'
    try:
        f = urllib2.urlopen(urllib2.Request(url=RELEASES_API_URL, data=content,
                                            headers=headers))
        f.read()
    except urllib2.HTTPError, e:
        print "Error uploading. Got HTTP code %d:" % e.code
        print e.read()
    except urllib2.URLError, e:
        try:
            print "Error uploading. Got URL error:" % e.code
            print e.read()
        except AttributeError:
            pass


def main():
    if not os.path.exists("setup.py"):
        sys.stderr.write("This must be run from the root of the "
                         "RBTools tree.\n")
        sys.exit(1)

    load_config()

    if not is_release():
        sys.stderr.write("This version is not listed as a release.\n")
        sys.exit(1)

    cur_dir = os.getcwd()
    git_dir = clone_git_tree(cur_dir)

    build_targets()
    build_checksums()
    upload_files()

    os.chdir(cur_dir)
    shutil.rmtree(git_dir)

    tag_release()
    register_release()


if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# RBTools documentation build configuration file, created by sphinx-
# quickstart on Thu Feb 12 02:10:34 2009.
#
# This file is execfile()d with the current directory set to its
# containing dir.
#
# The contents of this file are pickled, so don't put values in the
# namespace that aren't pickleable (module imports are okay, they're
# removed automatically).
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented
# out serve to show the default.

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
import rbtools


# If your extensions are in another directory, add it here. If the
# directory is relative to the documentation root, use os.path.abspath
# to make it absolute, like shown here.
# sys.path.append(os.path.abspath('.'))


# General configuration
# ---------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.doctest',
    'sphinx.ext.intersphinx',
]

# Add any paths that contain templates here, relative to this
# directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'RBTools Documentation'
copyright = u'2013, Beanbag, Inc.'

# The version info for the project you're documenting, acts as
# replacement for |version| and |release|, also used in various other
# places throughout the built documents.
#
# The short X.Y version.
version = '.'.join([str(i) for i in rbtools.VERSION[:-1][:2]])
# The full version, including alpha/beta/rc tags.
release = rbtools.get_version_string()

# The language for content autogenerated by Sphinx. Refer to
# documentation for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today
# to some non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of documents that shouldn't be included in the build.
#unused_docs = []

# List of directories, relative to source directory, that shouldn't be searched
# for source files.
exclude_trees = ['_build']

# The reST default role (used for this markup: `text`) to use for all
# documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
add_function_parentheses = True

# If true, the current module name will be prepended to all
# description unit titles (such as .. function::).
add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in
# the output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'


# Options for HTML output
# -----------------------

# The style sheet to use for HTML and HTML Help pages. A file of that
# name must exist either in Sphinx' static/ path, or in one of the
# custom paths given in html_static_path.
html_style = 'default.css'

# The name for this set of Sphinx documents. If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar. Default is the same as
# html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at
# the top of the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon
# of the docs. This file should be a Windows icon file (.ico) being
# 16x16 or 32x32 pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style
# sheets) here, relative to this directory. They are copied after the
# builtin static files, so a file named "default.css" will overwrite
# the builtin "default.css".
html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page
# bottom, using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page
# names to template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_use_modindex = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, the reST sources are included in the HTML build as
# _sources/<name>.
#html_copy_source = True

# If true, an OpenSearch description file will be output, and all
# pages will contain a <link> tag referring to it. The value of this
# option must be the base URL from which the finished HTML is served.
#html_use_opensearch = ''

# If nonempty, this is the file name suffix for HTML files (e.g.
# ".xhtml").
#html_file_suffix = ''

# Output file base name for HTML help builder.
htmlhelp_basename = 'RBtoolsdoc'


# Options for LaTeX output
# ------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples (source
# start file, target name, title, author, document class
# [howto/manual]).
latex_documents = [
    (
        'index',
        'RBtools.tex',
        ur'RBTools Documentation',
        ur'Steven MacLeod',
        'manual'
    ),
]

# The name of an image file (relative to this directory) to place at
# the top of the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are
# parts, not chapters.
#latex_use_parts = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_use_modindex = True


# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {
    'http://docs.python.org/dev': None,
    'http://www.reviewboard.org/docs/manual/dev/': None,
}

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Release Notes build configuration file, created by
# sphinx-quickstart on Thu Feb 12 02:10:34 2009.
#
# This file is execfile()d with the current directory set to its
# containing dir.
#
# The contents of this file are pickled, so don't put values in the
# namespace that aren't pickleable (module imports are okay, they're
# removed automatically).
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented
# out serve to show the default.


# If your extensions are in another directory, add it here. If the
# directory is relative to the documentation root, use os.path.abspath
# to make it absolute, like shown here.
import os
import sys
sys.path.append(os.path.abspath('_ext'))

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
import rbtools


# General configuration
# ---------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.intersphinx',
    'extralinks',
]

# Add any paths that contain templates here, relative to this
# directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Release Notes'
copyright = u'2009-2013, Beanbag, Inc.'
bugtracker_url = 'http://www.reviewboard.org/bugs/%s'

# The version info for the project you're documenting, acts as
# replacement for |version| and |release|, also used in various other
# places throughout the built documents.
#
# The short X.Y version.
version = '.'.join([str(i) for i in rbtools.VERSION[:-1][:2]])
# The full version, including alpha/beta/rc tags.
release = rbtools.get_version_string()

# The language for content autogenerated by Sphinx. Refer to
# documentation for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today
# to some non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of documents that shouldn't be included in the build.
#unused_docs = []

# List of directories, relative to source directory, that shouldn't be
# searched for source files.
exclude_trees = ['_build']

# The reST default role (used for this markup: `text`) to use for all
# documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
add_function_parentheses = True

# If true, the current module name will be prepended to all
# description unit titles (such as .. function::).
add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in
# the output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'


# Options for HTML output
# -----------------------

html_theme = 'default'

# The style sheet to use for HTML and HTML Help pages. A file of that
# name must exist either in Sphinx' static/ path, or in one of the
# custom paths given in html_static_path.
html_style = 'default.css'

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
html_title = "Release Notes"

# A shorter title for the navigation bar.  Default is the same as
# html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at
# the top of the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon
# of the docs.  This file should be a Windows icon file (.ico) being
# 16x16 or 32x32 pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style
# sheets) here, relative to this directory. They are copied after the
# builtin static files, so a file named "default.css" will overwrite
# the builtin "default.css".
html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page
# bottom, using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page
# names to template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_use_modindex = True

# If false, no index is generated.
html_use_index = False

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, the reST sources are included in the HTML build as
# _sources/<name>.
html_copy_source = True

# If true, an OpenSearch description file will be output, and all
# pages will contain a <link> tag referring to it.  The value of this
# option must be the base URL from which the finished HTML is served.
#html_use_opensearch = ''

# If nonempty, this is the file name suffix for HTML files (e.g.
# ".xhtml").
#html_file_suffix = ''

# Output file base name for HTML help builder.
htmlhelp_basename = 'ReleaseNotes'


# Options for LaTeX output
# ------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples (source
# start file, target name, title, author, document class
# [howto/manual]).
latex_documents = [
    ('contents', 'ReleaseNotes.tex', ur'Release Notes',
     ur'Christian Hammond', 'manual'),
]

# The name of an image file (relative to this directory) to place at
# the top of the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are
# parts, not chapters.
#latex_use_parts = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_use_modindex = True


# Example configuration for intersphinx: refer to the Python standard
# library.
intersphinx_mapping = {
    'http://www.reviewboard.org/docs/manual/dev': None,
    'http://www.reviewboard.org/docs/rbtools/dev': None,
}

########NEW FILE########
__FILENAME__ = extralinks
"""
Sphinx plugins for special links in the Release Notes.
"""
from docutils import nodes, utils


def setup(app):
    app.add_config_value('bugtracker_url', '', True)
    app.add_role('bug', bug_role)


def bug_role(role, rawtext, text, linenum, inliner, options={}, content=[]):
    try:
        bugnum = int(text)
        if bugnum <= 0:
            raise ValueError
    except ValueError:
        msg = inliner.reporter.error(
            'Bug number must be a number greater than or equal to 1; '
            '"%s" is invalid.' % text,
            line=linenum)
        prb = inliner.problematic(rawtext, rawtext, msg)
        return [prb], [msg]

    bugtracker_url = inliner.document.settings.env.config.bugtracker_url

    if not bugtracker_url or not '%s' in bugtracker_url:
        msg = inliner.reporter.error('bugtracker_url must be configured.',
                                     line=linenum)
        prb = inliner.problematic(rawtext, rawtext, msg)
        return [prb], [msg]

    ref = bugtracker_url % bugnum
    node = nodes.reference(rawtext, 'Bug #' + utils.unescape(text),
                           refuri=ref, **options)

    return [node], []

########NEW FILE########
__FILENAME__ = capabilities
class Capabilities(object):
    """Stores and retrieves Review Board server capabilities."""
    def __init__(self, capabilities):
        self.capabilities = capabilities

    def has_capability(self, *args):
        caps = self.capabilities

        try:
            for arg in args:
                caps = caps[arg]

            # If only part of a capability path is specified, we don't want
            # to evaluate to True just because it has contents. We want to
            # only say we have a capability if it is indeed 'True'.
            return caps is True
        except (TypeError, KeyError):
            # The server either doesn't support the capability,
            # or returned no capabilities at all.
            return False

########NEW FILE########
__FILENAME__ = client
from rbtools.api.transport.sync import SyncTransport


class RBClient(object):
    """Entry point for accessing RB resources through the web API.

    By default the synchronous transport will be used. To use a
    different transport, provide the transport class in the
    'transport_cls' parameter.
    """
    def __init__(self, url, transport_cls=SyncTransport, *args, **kwargs):
        self.url = url
        self._transport = transport_cls(url, *args, **kwargs)

    def get_root(self, *args, **kwargs):
        return self._transport.get_root(*args, **kwargs)

    def get_path(self, path, *args, **kwargs):
        return self._transport.get_path(path, *args, **kwargs)

    def get_url(self, url, *args, **kwargs):
        return self._transport.get_url(url, *args, **kwargs)

    def login(self, *args, **kwargs):
        return self._transport.login(*args, **kwargs)

########NEW FILE########
__FILENAME__ = decode
try:
    import json
except ImportError:
    import simplejson as json

from rbtools.api.utils import parse_mimetype


DECODER_MAP = {}


def DefaultDecoder(payload):
    """Default decoder for API payloads.

    The default decoder is used when a decoder is not found in the
    DECODER_MAP. This will stick the body of the response into the
    'data' field.
    """
    return {
        'resource': {
            'data': payload,
        },
    }

DEFAULT_DECODER = DefaultDecoder


def JsonDecoder(payload):
    return json.loads(payload)

DECODER_MAP['application/json'] = JsonDecoder


def decode_response(payload, mime_type):
    """Decode a Web API response.

    The body of a Web API response will be decoded into a dictionary,
    according to the provided mime_type.
    """
    mime = parse_mimetype(mime_type)

    format = '%s/%s' % (mime['main_type'], mime['format'])

    if format in DECODER_MAP:
        decoder = DECODER_MAP[format]
    else:
        decoder = DEFAULT_DECODER

    return decoder(payload)

########NEW FILE########
__FILENAME__ = decorators
def request_method_decorator(f):
    """Wraps methods returned from a resource to capture HttpRequests.

    When a method which returns HttpRequests is called, it will
    pass the method and arguments off to the transport to be executed.

    This wrapping allows the transport to skim arguments off the top
    of the method call, and modify any return values (such as executing
    a returned HttpRequest).

    However, if called with the ``internal`` argument set to True,
    the method itself will be executed and the value returned as-is.
    Thus, any method calls embedded inside the code for another method
    should use the ``internal`` argument to access the expected value.
    """
    def request_method(self, *args, **kwargs):
        if kwargs.pop('internal', False):
            return f(self, *args, **kwargs)
        else:
            def method_wrapper(*args, **kwargs):
                return f(self, *args, **kwargs)

            return self._transport.execute_request_method(method_wrapper,
                                                          *args, **kwargs)

    request_method.__name__ = f.__name__
    request_method.__doc__ = f.__doc__
    request_method.__dict__.update(f.__dict__)
    return request_method

########NEW FILE########
__FILENAME__ = errors
class APIError(Exception):
    def __init__(self, http_status, error_code, rsp=None, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)
        self.http_status = http_status
        self.error_code = error_code
        self.rsp = rsp

    def __str__(self):
        code_str = "HTTP %d" % self.http_status

        if self.error_code:
            code_str += ', API Error %d' % self.error_code

        if self.rsp and 'err' in self.rsp:
            return '%s (%s)' % (self.rsp['err']['msg'], code_str)
        else:
            return code_str


class AuthorizationError(APIError):
    pass


class BadRequestError(APIError):
    def __str__(self):
        lines = [super(BadRequestError, self).__str__()]

        if self.rsp and 'fields' in self.rsp:
            lines.append('')

            for field, error in self.rsp['fields'].iteritems():
                lines.append('    %s: %s' % (field, '; '.join(error)))

        return '\n'.join(lines)


class ServerInterfaceError(Exception):
    def __init__(self, msg, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)
        self.msg = msg

    def __str__(self):
        return self.msg


API_ERROR_TYPE = {
    400: BadRequestError,
    401: AuthorizationError,
}


def create_api_error(http_status, *args, **kwargs):
    error_type = API_ERROR_TYPE.get(http_status, APIError)
    return error_type(http_status, *args, **kwargs)

########NEW FILE########
__FILENAME__ = factory
from rbtools.api.resource import (CountResource, ItemResource,
                                  ListResource, RESOURCE_MAP)
from rbtools.api.utils import rem_mime_format


SPECIAL_KEYS = set(('links', 'total_results', 'stat', 'count'))


def create_resource(transport, payload, url, mime_type=None,
                    item_mime_type=None, guess_token=True):
    """Construct and return a resource object.

    The mime type will be used to find a resource specific base class.
    Alternatively, if no resource specific base class exists, one of
    the generic base classes, Resource or ResourceList, will be used.

    If an item mime type is provided, it will be used by list
    resources to construct item resources from the list.

    If 'guess_token' is True, we will try and guess what key the
    resources body lives under. If False, we assume that the resource
    body is the body of the payload itself. This is important for
    constructing Item resources from a resource list.
    """

    # Determine the key for the resources data.
    token = None

    if guess_token:
        other_keys = set(payload.keys()).difference(SPECIAL_KEYS)
        if len(other_keys) == 1:
            token = other_keys.pop()

    # Select the base class for the resource.
    if 'count' in payload:
        resource_class = CountResource
    elif mime_type and rem_mime_format(mime_type) in RESOURCE_MAP:
        resource_class = RESOURCE_MAP[rem_mime_format(mime_type)]
    elif token and isinstance(payload[token], list):
        resource_class = ListResource
    else:
        resource_class = ItemResource

    return resource_class(transport, payload, url, token=token,
                          item_mime_type=item_mime_type)

########NEW FILE########
__FILENAME__ = request
import base64
import cookielib
import httplib
import logging
import mimetools
import mimetypes
import os
import shutil
import urllib
import urllib2
from StringIO import StringIO
from urlparse import urlparse, urlunparse

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

try:
    # Specifically import json_loads, to work around some issues with
    # installations containing incompatible modules named "json".
    from json import loads as json_loads
except ImportError:
    from simplejson import loads as json_loads

try:
    # In python 2.6, parse_qsl was deprectated in cgi, and
    # moved to urlparse.
    from urlparse import parse_qsl
except ImportError:
    from cgi import parse_qsl


from rbtools import get_package_version
from rbtools.api.errors import APIError, create_api_error, ServerInterfaceError
from rbtools.utils.filesystem import get_home_path


RBTOOLS_COOKIE_FILE = '.rbtools-cookies'
RB_COOKIE_NAME = 'rbsessionid'


class HttpRequest(object):
    """High-level HTTP-request object."""
    def __init__(self, url, method='GET', query_args={}):
        self.method = method
        self.headers = {}
        self._fields = {}
        self._files = {}

        # Replace all underscores in each query argument
        # key with dashes.
        query_args = dict([
            (key.replace('_', '-'), value)
            for key, value in query_args.iteritems()
        ])

        # Add the query arguments to the url
        # TODO: Make work with Python < 2.6. In 2.6
        # parse_qsl was moved from cgi to urlparse.
        url_parts = list(urlparse(url))
        query = dict(parse_qsl(url_parts[4]))
        query.update(query_args)
        url_parts[4] = urllib.urlencode(query)
        self.url = urlunparse(url_parts)

    def add_field(self, name, value):
        self._fields[name] = value

    def add_file(self, name, filename, content):
        self._files[name] = {
            'filename': filename,
            'content': content,
        }

    def del_field(self, name):
        del self._fields[name]

    def del_file(self, filename):
        del self._files[filename]

    def encode_multipart_formdata(self):
        """ Encodes data for use in an HTTP request.

        Parameters:
            fields - the fields to be encoded.  This should be a dict in a
                     key:value format
            files  - the files to be encoded.  This should be a dict in a
                     key:dict, filename:value and content:value format
        """
        if not (self._fields or self._files):
            return None, None

        NEWLINE = '\r\n'
        BOUNDARY = mimetools.choose_boundary()
        content = StringIO()

        for key in self._fields:
            content.write('--' + BOUNDARY + NEWLINE)
            content.write('Content-Disposition: form-data; name="%s"' % key)
            content.write(NEWLINE + NEWLINE)
            content.write(str(self._fields[key]) + NEWLINE)

        for key in self._files:
            filename = self._files[key]['filename']
            value = self._files[key]['content']
            mime_type = (mimetypes.guess_type(filename)[0] or
                         'application/octet-stream')
            content.write('--' + BOUNDARY + NEWLINE)
            content.write('Content-Disposition: form-data; name="%s"; ' % key)
            content.write('filename="%s"' % filename + NEWLINE)
            content.write('Content-Type: %s' % mime_type + NEWLINE)
            content.write(NEWLINE)
            content.write(value)
            content.write(NEWLINE)

        content.write('--' + BOUNDARY + '--' + NEWLINE + NEWLINE)
        content_type = 'multipart/form-data; boundary=%s' % BOUNDARY

        return content_type, content.getvalue()


class Request(urllib2.Request):
    """A request which contains a method attribute."""
    def __init__(self, url, body='', headers={}, method="PUT"):
        urllib2.Request.__init__(self, url, body, headers)
        self.method = method

    def get_method(self):
        return self.method


class PresetHTTPAuthHandler(urllib2.BaseHandler):
    """urllib2 handler that presets the use of HTTP Basic Auth."""
    handler_order = 480  # After Basic auth

    def __init__(self, url, password_mgr):
        self.url = url
        self.password_mgr = password_mgr
        self.used = False

    def reset(self, username, password):
        self.password_mgr.rb_user = username
        self.password_mgr.rb_pass = password
        self.used = False

    def http_request(self, request):
        if not self.used and self.password_mgr.rb_user:
            # Note that we call password_mgr.find_user_password to get the
            # username and password we're working with.
            username, password = \
                self.password_mgr.find_user_password('Web API', self.url)
            raw = '%s:%s' % (username, password)
            request.add_header(
                urllib2.HTTPBasicAuthHandler.auth_header,
                'Basic %s' % base64.b64encode(raw).strip())
            self.used = True

        return request

    https_request = http_request


class ReviewBoardHTTPErrorProcessor(urllib2.HTTPErrorProcessor):
    """Processes HTTP error codes.

    Python 2.6 gets HTTP error code processing right, but 2.4 and 2.5
    only accepts HTTP 200 and 206 as success codes. This handler
    ensures that anything in the 200 range is a success.
    """
    def http_response(self, request, response):
        if not (200 <= response.code < 300):
            response = self.parent.error('http', request, response,
                                         response.code, response.msg,
                                         response.info())

        return response

    https_response = http_response


class ReviewBoardHTTPBasicAuthHandler(urllib2.HTTPBasicAuthHandler):
    """Custom Basic Auth handler that doesn't retry excessively.

    urllib2's HTTPBasicAuthHandler retries over and over, which is
    useless. This subclass only retries once to make sure we've
    attempted with a valid username and password. It will then fail so
    we can use our own retry handler.

    This also supports two-factor auth, for Review Board servers that
    support it. When requested by the server, the client will be prompted
    for a one-time password token, which would be sent generally through
    a mobile device. In this case, the client will prompt up to a set
    number of times until a valid token is entered.
    """
    OTP_TOKEN_HEADER = 'X-ReviewBoard-OTP'
    MAX_OTP_TOKEN_ATTEMPTS = 5

    def __init__(self, *args, **kwargs):
        urllib2.HTTPBasicAuthHandler.__init__(self, *args, **kwargs)
        self._retried = False
        self._lasturl = ""
        self._needs_otp_token = False
        self._otp_token_attempts = 0

    def retry_http_basic_auth(self, host, request, realm, *args, **kwargs):
        if self._lasturl != host:
            self._retried = False

        self._lasturl = host

        if self._retried:
            return None

        self._retried = True

        response = self._do_http_basic_auth(host, request, realm)

        if response and response.code != httplib.UNAUTHORIZED:
            self._retried = False

        return response

    def _do_http_basic_auth(self, host, request, realm):
        user, password = self.passwd.find_user_password(realm, host)

        if password is None:
            return None

        raw = "%s:%s" % (user, password)
        auth = 'Basic %s' % base64.b64encode(raw).strip()

        if (request.headers.get(self.auth_header, None) == auth and
            (not self._needs_otp_token or
             self._otp_token_attempts > self.MAX_OTP_TOKEN_ATTEMPTS)):
            # We've already tried with these credentials. No point
            # trying again.
            return None

        request.add_unredirected_header(self.auth_header, auth)

        try:
            response = self.parent.open(request, timeout=request.timeout)
            return response
        except urllib2.HTTPError, e:
            if e.code == 401:
                headers = e.info()
                otp_header = headers.get(self.OTP_TOKEN_HEADER, '')

                if otp_header.startswith('required'):
                    self._needs_otp_token = True

                    # The server has requested a one-time password token, sent
                    # through an external channel (cell phone or application).
                    # Request this token from the user.
                    required, token_method = otp_header.split(';')

                    token = self.passwd.get_otp_token(request.get_full_url(),
                                                      token_method.strip())

                    if not token:
                        return None

                    request.add_unredirected_header(self.OTP_TOKEN_HEADER,
                                                    token)
                    self._otp_token_attempts += 1

                    return self._do_http_basic_auth(host, request, realm)

            raise

        return None


class ReviewBoardHTTPPasswordMgr(urllib2.HTTPPasswordMgr):
    """Adds HTTP authentication support for URLs.

    Python 2.4's password manager has a bug in http authentication
    when the target server uses a non-standard port.  This works
    around that bug on Python 2.4 installs.

    See: http://bugs.python.org/issue974757
    """
    def __init__(self, reviewboard_url, rb_user=None, rb_pass=None,
                 auth_callback=None, otp_token_callback=None):
        urllib2.HTTPPasswordMgr.__init__(self)
        self.passwd = {}
        self.rb_url = reviewboard_url
        self.rb_user = rb_user
        self.rb_pass = rb_pass
        self.auth_callback = auth_callback
        self.otp_token_callback = otp_token_callback

    def find_user_password(self, realm, uri):
        if realm == 'Web API':
            if self.auth_callback:
                username, password = self.auth_callback(realm, uri,
                                                        username=self.rb_user,
                                                        password=self.rb_pass)
                self.rb_user = username
                self.rb_pass = password

            return self.rb_user, self.rb_pass
        else:
            # If this is an auth request for some other domain (since HTTP
            # handlers are global), fall back to standard password management.
            return urllib2.HTTPPasswordMgr.find_user_password(self, realm, uri)

    def get_otp_token(self, uri, method):
        if self.otp_token_callback:
            return self.otp_token_callback(uri, method)


def create_cookie_jar(cookie_file=None):
    """Return a cookie jar backed by cookie_file

    If cooie_file is not provided, we will default it. If the
    cookie_file does not exist, we will create it with the proper
    permissions.

    In the case where we default cookie_file, and it does not exist,
    we will attempt to copy the .post-review-cookies.txt file.
    """
    home_path = get_home_path()

    if not cookie_file:
        cookie_file = os.path.join(home_path, RBTOOLS_COOKIE_FILE)
        post_review_cookies = os.path.join(home_path,
                                           '.post-review-cookies.txt')

        if (not os.path.isfile(cookie_file) and
            os.path.isfile(post_review_cookies)):
                try:
                    shutil.copyfile(post_review_cookies, cookie_file)
                    os.chmod(cookie_file, 0600)
                except IOError, e:
                    logging.warning("There was an error while copying "
                                    "post-review's cookies: %s" % e)

    if not os.path.isfile(cookie_file):
        try:
            open(cookie_file, 'w').close()
            os.chmod(cookie_file, 0600)
        except IOError, e:
            logging.warning("There was an error while creating a "
                            "cookie file: %s" % e)

    return cookielib.MozillaCookieJar(cookie_file), cookie_file


class ReviewBoardServer(object):
    """Represents a Review Board server we are communicating with.

    Provides methods for executing HTTP requests on a Review Board
    server's Web API.

    The ``auth_callback`` parameter can be used to specify a callable
    which will be called when authentication fails. This callable will
    be passed the realm, and url of the Review Board server and should
    return a 2-tuple of username, password. The user can be prompted
    for their credentials using this mechanism.
    """
    def __init__(self, url, cookie_file=None, username=None, password=None,
                 agent=None, session=None, disable_proxy=False,
                 auth_callback=None, otp_token_callback=None):
        self.url = url
        if self.url[-1] != '/':
            self.url += '/'

        self.url = self.url + 'api/'
        self.cookie_jar, self.cookie_file = create_cookie_jar(
            cookie_file=cookie_file)

        try:
            self.cookie_jar.load(ignore_expires=True)
        except IOError:
            pass

        if session:
            parsed_url = urlparse(url)
            # Get the cookie domain from the url. If the domain
            # does not contain a '.' (e.g. 'localhost'), we assume
            # it is a local domain and suffix it (See RFC 2109).
            domain = parsed_url[1].partition(':')[0]  # Remove Port.
            if domain.count('.') < 1:
                domain = "%s.local" % domain

            cookie = cookielib.Cookie(
                version=0,
                name=RB_COOKIE_NAME,
                value=session,
                port=None,
                port_specified=False,
                domain=domain,
                domain_specified=True,
                domain_initial_dot=True,
                path=parsed_url[2],
                path_specified=True,
                secure=False,
                expires=None,
                discard=False,
                comment=None,
                comment_url=None,
                rest={'HttpOnly': None})
            self.cookie_jar.set_cookie(cookie)
            self.cookie_jar.save()

        # Set up the HTTP libraries to support all of the features we need.
        password_mgr = ReviewBoardHTTPPasswordMgr(self.url,
                                                  username,
                                                  password,
                                                  auth_callback,
                                                  otp_token_callback)
        self.preset_auth_handler = PresetHTTPAuthHandler(self.url,
                                                         password_mgr)

        handlers = []

        if disable_proxy:
            handlers.append(urllib2.ProxyHandler({}))

        handlers += [
            urllib2.HTTPCookieProcessor(self.cookie_jar),
            ReviewBoardHTTPBasicAuthHandler(password_mgr),
            urllib2.HTTPDigestAuthHandler(password_mgr),
            self.preset_auth_handler,
            ReviewBoardHTTPErrorProcessor(),
        ]

        if agent:
            self.agent = agent
        else:
            self.agent = 'RBTools/' + get_package_version()

        opener = urllib2.build_opener(*handlers)
        opener.addheaders = [
            ('User-agent', self.agent),
        ]
        urllib2.install_opener(opener)

    def login(self, username, password):
        """Reset the user information"""
        self.preset_auth_handler.reset(username, password)

    def process_error(self, http_status, data):
        """Processes an error, raising an APIError with the information."""
        try:
            rsp = json_loads(data)

            assert rsp['stat'] == 'fail'

            logging.debug('Got API Error %d (HTTP code %d): %s' %
                          (rsp['err']['code'], http_status, rsp['err']['msg']))
            logging.debug('Error data: %r' % rsp)

            raise create_api_error(http_status, rsp['err']['code'], rsp,
                                   rsp['err']['msg'])
        except ValueError:
            logging.debug('Got HTTP error: %s: %s' % (http_status, data))
            raise APIError(http_status, None, None, data)

    def make_request(self, request):
        """Perform an http request.

        The request argument should be an instance of
        'rbtools.api.request.HttpRequest'.
        """
        try:
            content_type, body = request.encode_multipart_formdata()
            headers = request.headers

            if body:
                headers.update({
                    'Content-Type': content_type,
                    'Content-Length': str(len(body)),
                })
            else:
                headers['Content-Length'] = "0"

            r = Request(request.url.encode('utf-8'), body, headers,
                        request.method)
            rsp = urllib2.urlopen(r)
        except urllib2.HTTPError, e:
            self.process_error(e.code, e.read())
        except urllib2.URLError, e:
            raise ServerInterfaceError("%s" % e.reason)

        try:
            self.cookie_jar.save()
        except IOError:
            pass

        return rsp

########NEW FILE########
__FILENAME__ = resource
import re
import urlparse

from rbtools.api.decorators import request_method_decorator
from rbtools.api.request import HttpRequest


RESOURCE_MAP = {}
LINKS_TOK = 'links'
LINK_KEYS = set(['href', 'method', 'title'])
_EXCLUDE_ATTRS = [LINKS_TOK, 'stat']


@request_method_decorator
def _create(resource, data=None, query_args={}, *args, **kwargs):
    """Generate a POST request on a resource.

    Unlike other methods, any additional query args must be passed in
    using the 'query_args' parameter, since kwargs is used for the
    fields which will be sent.
    """
    request = HttpRequest(resource._links['create']['href'], method='POST',
                          query_args=query_args)

    if data is None:
        data = {}

    kwargs.update(data)

    for name, value in kwargs.iteritems():
        request.add_field(name, value)

    return request


@request_method_decorator
def _delete(resource, *args, **kwargs):
    """Generate a DELETE request on a resource."""
    return HttpRequest(resource._links['delete']['href'], method='DELETE',
                       query_args=kwargs)


@request_method_decorator
def _get_self(resource, *args, **kwargs):
    """Generate a request for a resource's 'self' link."""
    return HttpRequest(resource._links['self']['href'], query_args=kwargs)


@request_method_decorator
def _update(resource, data=None, query_args={}, *args, **kwargs):
    """Generate a PUT request on a resource.

    Unlike other methods, any additional query args must be passed in
    using the 'query_args' parameter, since kwargs is used for the
    fields which will be sent.
    """
    request = HttpRequest(resource._links['update']['href'], method='PUT',
                          query_args=query_args)

    if data is None:
        data = {}

    kwargs.update(data)

    for name, value in kwargs.iteritems():
        request.add_field(name, value)

    return request


# This dictionary is a mapping of special keys in a resources links,
# to a name and method used for generating a request for that link.
# This is used to special case the REST operation links. Any link
# included in this dictionary will be generated separately, and links
# with a None for the method will be ignored.
SPECIAL_LINKS = {
    'create': ['create', _create],
    'delete': ['delete', _delete],
    'next': ['get_next', None],
    'prev': ['get_prev', None],
    'self': ['get_self', _get_self],
    'update': ['update', _update],
}


class Resource(object):
    """Defines common functionality for Item and List Resources.

    Resources are able to make requests to the Web API by returning an
    HttpRequest object. When an HttpRequest is returned from a method
    call, the transport layer will execute this request and return the
    result to the user.

    Methods for constructing requests to perform each of the supported
    REST operations will be generated automatically. These methods
    will have names corresponding to the operation (e.g. 'update()').
    An additional method for re-requesting the resource using the
    'self' link will be generated with the name 'get_self'. Each
    additional link will have a method generated which constructs a
    request for retrieving the linked resource.
    """
    _excluded_attrs = []

    def __init__(self, transport, payload, url, token=None, **kwargs):
        self._url = url
        self._transport = transport
        self._token = token
        self._payload = payload
        self._excluded_attrs = self._excluded_attrs + _EXCLUDE_ATTRS

        # Determine where the links live in the payload. This
        # can either be at the root, or inside the resources
        # token.
        if LINKS_TOK in self._payload:
            self._links = self._payload[LINKS_TOK]
        elif (token and isinstance(self._payload[token], dict) and
              LINKS_TOK in self._payload[token]):
            self._links = self._payload[token][LINKS_TOK]
        else:
            self._payload[LINKS_TOK] = {}
            self._links = {}

        # Add a method for each supported REST operation, and
        # for retrieving 'self'.
        for link, method in SPECIAL_LINKS.iteritems():
            if link in self._links and method[1]:
                setattr(self,
                        method[0],
                        lambda resource=self, meth=method[1], **kwargs: (
                            meth(resource, **kwargs)))

        # Generate request methods for any additional links
        # the resource has.
        for link, body in self._links.iteritems():
            if link not in SPECIAL_LINKS:
                setattr(self,
                        "get_%s" % link,
                        lambda resource=self, url=body['href'], **kwargs: (
                            self._get_url(url, **kwargs)))

    def _wrap_field(self, field):
        if isinstance(field, dict):
            dict_keys = set(field.keys())

            if ('href' in dict_keys and
                len(dict_keys.difference(LINK_KEYS)) == 0):
                return ResourceLinkField(self, field)
            else:
                return ResourceDictField(self, field)
        elif isinstance(field, list):
            return ResourceListField(self, field)
        else:
            return field

    @property
    def links(self):
        """Get the resource's links.

        This is a special property which allows direct access to the links
        dictionary for a resource. Unlike other properties which come from the
        resource fields, this one is only accessible as a property, and not
        using array syntax."""
        return ResourceDictField(self, self._links)

    @request_method_decorator
    def _get_url(self, url, **kwargs):
        return HttpRequest(url, query_args=kwargs)

    @property
    def rsp(self):
        """Return the response payload used to create the resource."""
        return self._payload


class ResourceDictField(object):
    """Wrapper for dictionaries returned from a resource.

    Any dictionary returned from a resource will be wrapped using this
    class. Attribute access will correspond to accessing the
    dictionary key with the name of the attribute.
    """
    def __init__(self, resource, fields):
        self._resource = resource
        self._fields = fields

    def __getattr__(self, name):
        if name in self._fields:
            return self._resource._wrap_field(self._fields[name])
        else:
            raise AttributeError

    def __getitem__(self, key):
        try:
            return self.__getattr__(key)
        except AttributeError:
            raise KeyError

    def __contains__(self, key):
        return key in self._fields

    def iterfields(self):
        for field in self._fields:
            yield field

    def iteritems(self):
        for key, value in self._fields.iteritems():
            yield key, self._resource._wrap_field(value)

    def __repr__(self):
        return '%s(resource=%r, fields=%r)' % (
            self.__class__.__name__,
            self._resource,
            self._fields)


class ResourceLinkField(ResourceDictField):
    """Wrapper for link dictionaries returned from a resource.

    In order to support operations on links found outside of a
    resource's links dictionary, detected links are wrapped with this
    class.

    A links fields (href, method, and title) are accessed as
    attributes, and link operations are supported through method
    calls. Currently the only supported method is "GET", which can be
    invoked using the 'get' method.
    """
    def __init__(self, resource, fields):
        super(ResourceLinkField, self).__init__(resource, fields)
        self._transport = resource._transport

    @request_method_decorator
    def get(self):
        return HttpRequest(self._fields['href'])


class ResourceListField(list):
    """Wrapper for lists returned from a resource.

    Acts as a normal list, but wraps any returned items.
    """
    def __init__(self, resource, list_field):
        super(ResourceListField, self).__init__(list_field)
        self._resource = resource

    def __getitem__(self, key):
        item = super(ResourceListField, self).__getitem__(key)
        return self._resource._wrap_field(item)

    def __iter__(self):
        for item in super(ResourceListField, self).__iter__():
            yield self._resource._wrap_field(item)

    def __repr__(self):
        return '%s(resource=%r, list_field=%s)' % (
            self.__class__.__name__,
            self._resource,
            super(ResourceListField, self).__repr__())


class ItemResource(Resource):
    """The base class for Item Resources.

    Any resource specific base classes for Item Resources should
    inherit from this class. If a resource specific base class does
    not exist for an Item Resource payload, this class will be used to
    create the resource.

    The body of the resource is copied into the fields dictionary. The
    Transport is responsible for providing access to this data,
    preferably as attributes for the wrapping class.
    """
    _excluded_attrs = []

    def __init__(self, transport, payload, url, token=None, **kwargs):
        super(ItemResource, self).__init__(transport, payload, url,
                                           token=token, **kwargs)
        self._fields = {}

        # Determine the body of the resource's data.
        if token is not None:
            data = self._payload[token]
        else:
            data = self._payload

        for name, value in data.iteritems():
            if name not in self._excluded_attrs:
                self._fields[name] = value

    def __getattr__(self, name):
        if name in self._fields:
            return self._wrap_field(self._fields[name])
        else:
            raise AttributeError

    def __getitem__(self, key):
        try:
            return self.__getattr__(key)
        except AttributeError:
            raise KeyError

    def __contains__(self, key):
        return key in self._fields

    def iterfields(self):
        for key in self._fields:
            yield key

    def iteritems(self):
        for key, value in self._fields.iteritems():
            yield (key, self._wrap_field(value))

    def __repr__(self):
        return '%s(transport=%r, payload=%r, url=%r, token=%r)' % (
            self.__class__.__name__,
            self._transport,
            self._payload,
            self._url,
            self._token)


class CountResource(ItemResource):
    """Resource returned by a query with 'counts-only' true.

    When a resource is requested using 'counts-only', the payload will
    not contain the regular fields for the resource. In order to
    special case all payloads of this form, this class is used for
    resource construction.
    """
    def __init__(self, transport, payload, url, **kwargs):
        super(CountResource, self).__init__(transport, payload, url,
                                            token=None)

    @request_method_decorator
    def get_self(self, **kwargs):
        """Generate an GET request for the resource list.

        This will return an HttpRequest to retrieve the list resource
        which this resource is a count for. Any query arguments used
        in the request for the count will still be present, only the
        'counts-only' argument will be removed
        """
        # TODO: Fix this. It is generating a new request
        # for a URL with 'counts-only' set to False, but
        # RB treats the  argument being set to any value
        # as true.
        kwargs.update({'counts_only': False})
        return HttpRequest(self._url, query_args=kwargs)


class ListResource(Resource):
    """The base class for List Resources.

    Any resource specific base classes for List Resources should
    inherit from this class. If a resource specific base class does
    not exist for a List Resource payload, this class will be used to
    create the resource.

    Instances of this class will act as a sequence, providing access
    to the payload for each Item resource in the list. Iteration is
    over the page of item resources returned by a single request, and
    not the entire list of resources. To iterate over all item
    resources 'get_next()' or 'get_prev()' should be used to grab
    additional pages of items.
    """
    def __init__(self, transport, payload, url, token=None,
                 item_mime_type=None, **kwargs):
        super(ListResource, self).__init__(transport, payload, url,
                                           token=token, **kwargs)
        self._item_mime_type = item_mime_type

        if token:
            self._item_list = payload[self._token]
        else:
            self._item_list = payload

        self.num_items = len(self._item_list)
        self.total_results = payload['total_results']

    def __len__(self):
        return self.num_items

    def __nonzero__(self):
        return True

    def __getitem__(self, key):
        payload = self._item_list[key]

        # TODO: Should try and guess the url based on the parent url,
        # and the id number if the self link doesn't exist.
        try:
            url = payload['links']['self']['href']
        except KeyError:
            url = ''

        # We need to import this here because of the mutual imports.
        from rbtools.api.factory import create_resource

        return create_resource(self._transport,
                               payload,
                               url,
                               mime_type=self._item_mime_type,
                               guess_token=False)

    def __iter__(self):
        for i in xrange(self.num_items):
            yield self[i]

    @request_method_decorator
    def get_next(self, **kwargs):
        if 'next' not in self._links:
            raise StopIteration()

        return HttpRequest(self._links['next']['href'], query_args=kwargs)

    @request_method_decorator
    def get_prev(self, **kwargs):
        if 'prev' not in self._links:
            raise StopIteration()

        return HttpRequest(self._links['prev']['href'], query_args=kwargs)

    @request_method_decorator
    def get_item(self, pk, **kwargs):
        """Retrieve the item resource with the corresponding primary key."""
        return HttpRequest(urlparse.urljoin(self._url, '%s/' % pk),
                           query_args=kwargs)

    def __repr__(self):
        return ('%s(transport=%r, payload=%r, url=%r, token=%r, '
                'item_mime_type=%r)' % (self.__class__.__name__,
                                        self._transport,
                                        self._payload,
                                        self._url,
                                        self._token,
                                        self._item_mime_type))


class RootResource(ItemResource):
    """The Root resource specific base class.

    Provides additional methods for fetching any resource directly
    using the uri templates. A method of the form "get_<uri-template-name>"
    is called to retrieve the HttpRequest corresponding to the
    resource. Template replacement values should be passed in as a
    dictionary to the values parameter.
    """
    _excluded_attrs = ['uri_templates']
    _TEMPLATE_PARAM_RE = re.compile('\{(?P<key>[A-Za-z_0-9]*)\}')

    def __init__(self, transport, payload, url, **kwargs):
        super(RootResource, self).__init__(transport, payload, url, token=None)
        # Generate methods for accessing resources directly using
        # the uri-templates.
        for name, url in payload['uri_templates'].iteritems():
            attr_name = "get_%s" % name

            if not hasattr(self, attr_name):
                setattr(self,
                        attr_name,
                        lambda resource=self, url=url, **kwargs: (
                            self._get_template_request(url, **kwargs)))

    @request_method_decorator
    def _get_template_request(self, url_template, values={}, **kwargs):
        """Generate an HttpRequest from a uri-template.

        This will replace each '{variable}' in the template with the
        value from kwargs['variable'], or if it does not exist, the
        value from values['variable']. The resulting url is used to
        create an HttpRequest.
        """
        def get_template_value(m):
            try:
                return str(kwargs.pop(m.group('key'), None) or
                           values[m.group('key')])
            except KeyError:
                raise ValueError("Template was not provided a value for '%s'" %
                                 m.group('key'))

        url = self._TEMPLATE_PARAM_RE.sub(get_template_value, url_template)
        return HttpRequest(url, query_args=kwargs)

RESOURCE_MAP['application/vnd.reviewboard.org.root'] = RootResource


class DiffListResource(ListResource):
    """The Diff List resource specific base class.

    Provides additional functionality to assist in the uploading of
    new diffs.
    """
    @request_method_decorator
    def upload_diff(self, diff, parent_diff=None, base_dir=None,
                    base_commit_id=None, **kwargs):
        """Uploads a new diff.

        The diff and parent_diff arguments should be strings containing
        the diff output.
        """
        request = HttpRequest(self._url, method='POST', query_args=kwargs)
        request.add_file('path', 'diff', diff)

        if parent_diff:
            request.add_file('parent_diff_path', 'parent_diff', parent_diff)

        if base_dir:
            request.add_field("basedir", base_dir)

        if base_commit_id:
            request.add_field('base_commit_id', base_commit_id)

        return request

RESOURCE_MAP['application/vnd.reviewboard.org.diffs'] = DiffListResource


class DiffResource(ItemResource):
    """The Diff resource specific base class.

    Provides the 'get_patch' method for retrieving the content of the
    actual diff file itself.
    """
    @request_method_decorator
    def get_patch(self, **kwargs):
        """Retrieves the actual diff file contents."""
        request = HttpRequest(self._url, query_args=kwargs)
        request.headers['Accept'] = 'text/x-patch'
        return request

RESOURCE_MAP['application/vnd.reviewboard.org.diff'] = DiffResource


class FileDiffResource(ItemResource):
    """The File Diff resource specific base class."""
    @request_method_decorator
    def get_patch(self, **kwargs):
        """Retrieves the actual diff file contents."""
        request = HttpRequest(self._url, query_args=kwargs)
        request.headers['Accept'] = 'text/x-patch'
        return request

    @request_method_decorator
    def get_diff_data(self, **kwargs):
        """Retrieves the actual raw diff data for the file."""
        request = HttpRequest(self._url, query_args=kwargs)
        request.headers['Accept'] = \
            'application/vnd.reviewboard.org.diff.data+json'
        return request

RESOURCE_MAP['application/vnd.reviewboard.org.file'] = FileDiffResource


class FileAttachmentListResource(ListResource):
    """The File Attachment List resource specific base class."""
    @request_method_decorator
    def upload_attachment(self, filename, content, caption=None, **kwargs):
        """Uploads a new attachment.

        The content argument should contain the body of the file to be
        uploaded, in string format.
        """
        request = HttpRequest(self._url, method='POST', query_args=kwargs)
        request.add_file('path', filename, content)

        if caption:
            request.add_field('caption', caption)

        return request

RESOURCE_MAP['application/vnd.reviewboard.org.file-attachments'] = \
    FileAttachmentListResource


class DraftFileAttachmentListResource(FileAttachmentListResource):
    """The Draft File Attachment List resource specific base class."""
    pass

RESOURCE_MAP['application/vnd.reviewboard.org.draft-file-attachments'] = \
    DraftFileAttachmentListResource


class ScreenshotListResource(ListResource):
    """The Screenshot List resource specific base class."""
    @request_method_decorator
    def upload_screenshot(self, filename, content, caption=None, **kwargs):
        """Uploads a new screenshot.

        The content argument should contain the body of the screenshot
        to be uploaded, in string format.
        """
        request = HttpRequest(self._url, method='POST', query_args=kwargs)
        request.add_file('path', filename, content)

        if caption:
            request.add_field('caption', caption)

        return request

RESOURCE_MAP['application/vnd.reviewboard.org.screenshots'] = \
    ScreenshotListResource


class DraftScreenshotListResource(ScreenshotListResource):
    """The Draft Screenshot List resource specific base class."""
    pass

RESOURCE_MAP['application/vnd.reviewboard.org.draft-screenshots'] = \
    DraftScreenshotListResource


class ReviewRequestResource(ItemResource):
    """The Review Request resource specific base class."""

    @property
    def absolute_url(self):
        """Returns the absolute URL for the Review Request.

        The value of absolute_url is returned if it's defined.
        Otherwise the absolute URL is generated and returned.
        """
        if 'absolute_url' in self._fields:
            return self._fields['absolute_url']
        else:
            base_url = self._url.split('/api/')[0]
            return urlparse.urljoin(base_url, self.url)

    @request_method_decorator
    def submit(self, description=None, changenum=None):
        """Submit a review request"""
        data = {
            'status': 'submitted',
        }

        if description:
            data['description'] = description

        if changenum:
            data['changenum'] = changenum

        return self.update(data=data, internal=True)

    @request_method_decorator
    def get_or_create_draft(self, **kwargs):
        request = self.get_draft(internal=True)
        request.method = 'POST'

        for name, value in kwargs.iteritems():
            request.add_field(name, value)

        return request

RESOURCE_MAP['application/vnd.reviewboard.org.review-request'] = \
    ReviewRequestResource

########NEW FILE########
__FILENAME__ = tests
import re
import unittest

from rbtools.api.capabilities import Capabilities
from rbtools.api.factory import create_resource
from rbtools.api.request import HttpRequest
from rbtools.api.resource import (CountResource,
                                  ItemResource,
                                  ListResource,
                                  ResourceDictField,
                                  ResourceLinkField,
                                  RootResource)
from rbtools.api.transport import Transport


class CapabilitiesTests(unittest.TestCase):
    """Tests for rbtools.api.capabilities.Capabilities"""
    def test_has_capability(self):
        """Testing Capabilities.has_capability with supported capability"""
        caps = Capabilities({
            'foo': {
                'bar': {
                    'value': True,
                }
            }
        })

        self.assertTrue(caps.has_capability('foo', 'bar', 'value'))

    def test_has_capability_with_unknown_capability(self):
        """Testing Capabilities.has_capability with unknown capability"""
        caps = Capabilities({})
        self.assertFalse(caps.has_capability('mycap'))

    def test_has_capability_with_partial_path(self):
        """Testing Capabilities.has_capability with partial capability path"""
        caps = Capabilities({
            'foo': {
                'bar': {
                    'value': True,
                }
            }
        })

        self.assertFalse(caps.has_capability('foo', 'bar'))


class MockTransport(Transport):
    """Mock transport which returns HttpRequests without executing them"""
    def __init__(self):
        pass


class TestWithPayloads(unittest.TestCase):
    transport = MockTransport()
    item_payload = {
        'resource_token': {
            'field1': 1,
            'field2': 2,
            'nested_field': {
                'nested1': 1,
                'nested2': 2,
            },
            'nested_list': [
                {
                    'href': 'http://localhost:8080/api/',
                    'method': 'GET',
                },
                {
                    'href': 'http://localhost:8080/api/',
                    'method': 'GET',
                },
            ],
            'link_field': {
                'href': 'http://localhost:8080/api/',
                'method': 'GET',
                'title': 'Link Field'
            },
        },
        'links': {
            'self': {
                'href': 'http://localhost:8080/api/',
                'method': 'GET',
            },
            'update': {
                'href': 'http://localhost:8080/api/',
                'method': 'PUT',
            },
            'delete': {
                'href': 'http://localhost:8080/api/',
                'method': 'DELETE',
            },
            'other_link': {
                'href': 'http://localhost:8080/api/',
                'method': 'GET',
            },
        },
        'stat': 'ok',
    }
    list_payload = {
        'resource_token': [
            {
                'field1': 1,
                'field2': 2,
                'links': {
                    'self': {
                        'href': 'http://localhost:8080/api/',
                        'method': 'GET',
                    },
                },
            },
            {
                'field1': 1,
                'field2': 2,
                'links': {
                    'self': {
                        'href': 'http://localhost:8080/api/',
                        'method': 'GET',
                    },
                },
            },
        ],
        'links': {
            'self': {
                'href': 'http://localhost:8080/api/',
                'method': 'GET',
            },
            'create': {
                'href': 'http://localhost:8080/api/',
                'method': 'POST',
            },
            'other_link': {
                'href': 'http://localhost:8080/api/',
                'method': 'GET',
            },
        },
        'total_results': 10,
        'stat': 'ok',
    }
    count_payload = {
        'count': 10,
        'stat': 'ok'
    }
    root_payload = {
        'uri_templates': {
            'reviews': ('http://localhost:8080/api/review-requests/'
                        '{review_request_id}/reviews/'),
        },
        'links': {
            'self': {
                'href': 'http://localhost:8080/api/',
                'method': 'GET',
            },
            'groups': {
                'href': 'http://localhost:8080/api/groups',
                'method': 'GET',
            },
        },
        'stat': 'ok',
    }


class ResourceFactoryTests(TestWithPayloads):
    def test_token_guessing(self):
        """Testing guessing the resource's token."""
        r = create_resource(self.transport, self.item_payload, '')
        self.assertTrue('resource_token' not in r._fields)

        for field in self.item_payload['resource_token']:
            self.assertTrue(field in r)

        r = create_resource(self.transport, self.count_payload, '')
        self.assertTrue('count' in r)

    def test_no_token_guessing(self):
        """Testing constructing without guessing the resource token."""
        r = create_resource(self.transport, self.item_payload, '',
                            guess_token=False)
        self.assertTrue('resource_token' in r)
        self.assertTrue('field1' not in r)
        self.assertTrue('field1' in r.resource_token)

        r = create_resource(self.transport, self.list_payload, '',
                            guess_token=False)
        self.assertTrue('resource_token' in r)

    def test_item_construction(self):
        """Testing constructing an item resource."""
        r = create_resource(self.transport, self.item_payload, '')
        self.assertTrue(isinstance(r, ItemResource))
        self.assertEqual(r.field1,
                         self.item_payload['resource_token']['field1'])
        self.assertEqual(r.field2,
                         self.item_payload['resource_token']['field2'])

    def test_list_construction(self):
        """Testing constructing a list resource."""
        r = create_resource(self.transport, self.list_payload, '')
        self.assertTrue(isinstance(r, ListResource))

    def test_count_construction(self):
        """Testing constructing a count resource."""
        r = create_resource(self.transport, self.count_payload, '')
        self.assertTrue(isinstance(r, CountResource))
        self.assertEqual(r.count, self.count_payload['count'])

    def test_resource_specific_base_class(self):
        """Testing constructing a resource with a specific base class."""
        r = create_resource(self.transport, self.root_payload, '')
        self.assertFalse(isinstance(r, RootResource))
        r = create_resource(
            self.transport,
            self.root_payload,
            '',
            mime_type='application/vnd.reviewboard.org.root+json')
        self.assertTrue(isinstance(r, RootResource))


class ResourceTests(TestWithPayloads):
    def test_item_resource_fields(self):
        """Testing item resource fields."""
        r = create_resource(self.transport, self.item_payload, '')
        for field in self.item_payload['resource_token']:
            self.assertTrue(field in r)
            self.assertTrue(hasattr(r, field))

    def test_item_resource_links(self):
        """Testing item resource link generation."""
        r = create_resource(self.transport, self.item_payload, '')

        self.assertTrue(hasattr(r, 'get_self'))
        self.assertTrue(callable(r.get_self))
        request = r.get_self()
        self.assertTrue(isinstance(request, HttpRequest))
        self.assertEqual(request.method, 'GET')
        self.assertEqual(request.url,
                         self.item_payload['links']['self']['href'])

        self.assertTrue(hasattr(r, 'update'))
        self.assertTrue(callable(r.update))
        request = r.update()
        self.assertTrue(isinstance(request, HttpRequest))
        self.assertEqual(request.method, 'PUT')
        self.assertEqual(request.url,
                         self.item_payload['links']['update']['href'])

        self.assertTrue(hasattr(r, 'delete'))
        self.assertTrue(callable(r.delete))
        request = r.delete()
        self.assertTrue(isinstance(request, HttpRequest))
        self.assertEqual(request.method, 'DELETE')
        self.assertEqual(request.url,
                         self.item_payload['links']['delete']['href'])

        self.assertTrue(hasattr(r, 'get_other_link'))
        self.assertTrue(callable(r.get_other_link))
        request = r.get_other_link()
        self.assertTrue(isinstance(request, HttpRequest))
        self.assertEqual(request.method, 'GET')
        self.assertEqual(request.url,
                         self.item_payload['links']['other_link']['href'])

        self.assertFalse(hasattr(r, 'create'))

    def test_list_resource_list(self):
        """Testing list resource lists."""
        r = create_resource(self.transport, self.list_payload, '')
        self.assertEqual(r.num_items, len(self.list_payload['resource_token']))
        self.assertEqual(r.total_results, self.list_payload['total_results'])

        for index in range(r.num_items):
            for field in r[index].iterfields():
                self.assertEqual(
                    r[index][field],
                    self.list_payload['resource_token'][index][field])

    def test_list_resource_links(self):
        """Testing link resource link generation."""
        r = create_resource(self.transport, self.list_payload, '')

        self.assertTrue(hasattr(r, 'get_self'))
        self.assertTrue(callable(r.get_self))
        request = r.get_self()
        self.assertTrue(isinstance(request, HttpRequest))
        self.assertEqual(request.method, 'GET')
        self.assertEqual(request.url,
                         self.list_payload['links']['self']['href'])

        self.assertTrue(hasattr(r, 'create'))
        self.assertTrue(callable(r.create))
        request = r.create()
        self.assertTrue(isinstance(request, HttpRequest))
        self.assertEqual(request.method, 'POST')
        self.assertEqual(request.url,
                         self.list_payload['links']['create']['href'])

        self.assertTrue(hasattr(r, 'get_other_link'))
        self.assertTrue(callable(r.get_other_link))
        request = r.get_other_link()
        self.assertTrue(isinstance(request, HttpRequest))
        self.assertEqual(request.method, 'GET')
        self.assertEqual(request.url,
                         self.list_payload['links']['other_link']['href'])

        self.assertFalse(hasattr(r, 'update'))
        self.assertFalse(hasattr(r, 'delete'))

    def test_root_resource_templates(self):
        """Testing generation of methods for the root resource uri templates."""
        r = create_resource(
            self.transport,
            self.root_payload,
            '',
            mime_type='application/vnd.reviewboard.org.root+json')

        for template_name in self.root_payload['uri_templates']:
            method_name = "get_%s" % template_name
            self.assertTrue(hasattr(r, method_name))
            self.assertTrue(callable(getattr(r, method_name)))

    def test_resource_dict_field(self):
        """Testing access of a dictionary field."""
        r = create_resource(self.transport, self.item_payload, '')

        field = r.nested_field

        self.assertTrue(isinstance(field, ResourceDictField))
        self.assertEqual(
            field.nested1,
            self.item_payload['resource_token']['nested_field']['nested1'])

    def test_resource_dict_field_iteration(self):
        """Testing iterating sub-fields of a dictionary field."""
        r = create_resource(self.transport, self.item_payload, '')

        field = r.nested_field
        iterated_fields = set(f for f in field.iterfields())
        nested_fields = set(
            f for f in self.item_payload['resource_token']['nested_field'])

        self.assertEqual(set(),
                         nested_fields.symmetric_difference(iterated_fields))

    def test_link_field(self):
        """Testing access of a link field."""
        r = create_resource(self.transport, self.item_payload, '')

        field = r.link_field
        self.assertTrue(isinstance(field, ResourceLinkField))

        request = field.get()
        self.assertEqual(request.method, 'GET')
        self.assertEqual(
            request.url,
            self.item_payload['resource_token']['link_field']['href'])


class HttpRequestTests(unittest.TestCase):
    def setUp(self):
        self.request = HttpRequest('/')

    def test_default_values(self):
        """Testing the default values."""
        self.assertEquals(self.request.url, '/')
        self.assertEquals(self.request.method, 'GET')
        content_type, content = self.request.encode_multipart_formdata()
        self.assertTrue(content_type is None)
        self.assertTrue(content is None)

    def test_post_form_data(self):
        """Testing the multipart form data generation."""
        request = HttpRequest('/', 'POST')
        request.add_field('foo', 'bar')
        request.add_field('bar', 42)
        request.add_field('err', 'must-be-deleted')
        request.add_field('name', 'somestring')
        request.del_field('err')

        ctype, content = request.encode_multipart_formdata()
        m = re.match('^multipart/form-data; boundary=(.*)$', ctype)
        self.assertFalse(m is None)
        fields = [l.strip() for l in content.split('--' + m.group(1))][1:-1]

        d = {}

        for f in fields:
            lst = f.split('\r\n\r\n')
            self.assertEquals(len(lst), 2)
            k, v = lst

            m = re.match('Content-Disposition: form-data; name="(.*?)"$', k)
            self.assertFalse(m is None)
            d[m.group(1)] = v

        self.assertEquals(d, {'foo': 'bar', 'bar': '42', 'name': 'somestring'})

########NEW FILE########
__FILENAME__ = sync
import logging

from rbtools.api.decode import decode_response
from rbtools.api.factory import create_resource
from rbtools.api.request import HttpRequest, ReviewBoardServer
from rbtools.api.transport import Transport


class SyncTransport(Transport):
    """A synchronous transport layer for the API client.

    The file provided in cookie_file is used to store and retrieve
    the authentication cookies for the API.

    The optional agent parameter can be used to specify a custom
    User-Agent string for the API. If not provided, the default
    RBTools User-Agent will be used.

    The optional session can be used to specify an 'rbsessionid'
    to use when authenticating with reviewboard.
    """
    def __init__(self, url, cookie_file=None, username=None, password=None,
                 agent=None, session=None, disable_proxy=False,
                 auth_callback=None, otp_token_callback=None, *args, **kwargs):
        super(SyncTransport, self).__init__(url, *args, **kwargs)
        self.server = ReviewBoardServer(self.url,
                                        cookie_file=cookie_file,
                                        username=username,
                                        password=password,
                                        session=session,
                                        disable_proxy=disable_proxy,
                                        auth_callback=auth_callback,
                                        otp_token_callback=otp_token_callback)

    def get_root(self):
        return self._execute_request(HttpRequest(self.server.url))

    def get_path(self, path, *args, **kwargs):
        if not path.endswith('/'):
            path = path + '/'

        if path.startswith('/'):
            path = path[1:]

        return self._execute_request(
            HttpRequest(self.server.url + path, query_args=kwargs))

    def get_url(self, url, *args, **kwargs):
        if not url.endswith('/'):
            url = url + '/'

        return self._execute_request(HttpRequest(url, query_args=kwargs))

    def login(self, username, password):
        self.server.login(username, password)

    def execute_request_method(self, method, *args, **kwargs):
        request = method(*args, **kwargs)

        if isinstance(request, HttpRequest):
            return self._execute_request(request)

        return request

    def _execute_request(self, request):
        """Execute an HTTPRequest and construct a resource from the payload"""
        logging.debug('Making HTTP %s request to %s' % (request.method,
                                                        request.url))

        rsp = self.server.make_request(request)
        info = rsp.info()
        mime_type = info['Content-Type']
        item_content_type = info.get('Item-Content-Type', None)
        payload = rsp.read()
        payload = decode_response(payload, mime_type)

        return create_resource(self, payload, request.url, mime_type=mime_type,
                               item_mime_type=item_content_type)

    def __repr__(self):
        return '<%s(url=%r, cookie_file=%r, agent=%r)>' % (
            self.__class__.__name__,
            self.url,
            self.server.cookie_file,
            self.server.agent)

########NEW FILE########
__FILENAME__ = utils
def parse_mimetype(mime_type):
    """Parse the mime type in to it's component parts."""
    types = mime_type.split(';')[0].split('/')

    ret_val = {
        'type': mime_type,
        'main_type': types[0],
        'sub_type': types[1]
    }

    sub_type = types[1].split('+')
    ret_val['vendor'] = ''
    if len(sub_type) == 1:
        ret_val['format'] = sub_type[0]
    else:
        ret_val['format'] = sub_type[1]
        ret_val['vendor'] = sub_type[0]

    vendor = ret_val['vendor'].split('.')
    if len(vendor) > 1:
        ret_val['resource'] = vendor[-1].replace('-', '_')
    else:
        ret_val['resource'] = ''

    return ret_val


def rem_mime_format(mime_type):
    """Strip the subtype from a mimetype, leaving vendor specific information.

    Removes the portion of the subtype after a +, or the entire
    subtype if no vendor specific type information is present.
    """
    if mime_type.rfind('+') != 0:
        return mime_type.rsplit('+', 1)[0]
    else:
        return mime_type.rsplit('/', 1)[0]

########NEW FILE########
__FILENAME__ = bazaar
import logging
import os
import re

from rbtools.clients import SCMClient, RepositoryInfo
from rbtools.clients.errors import TooManyRevisionsError
from rbtools.utils.checks import check_install
from rbtools.utils.process import execute


USING_PARENT_PREFIX = 'Using parent branch '


class BazaarClient(SCMClient):
    """
    Bazaar client wrapper that fetches repository information and generates
    compatible diffs.

    The :class:`RepositoryInfo` object reports whether the repository supports
    parent diffs (every branch with a parent supports them).
    """
    name = 'Bazaar'

    # Regular expression that matches the path to the current branch.
    #
    # For branches with shared repositories, Bazaar reports
    # "repository branch: /foo", but for standalone branches it reports
    # "branch root: /foo".
    BRANCH_REGEX = (
        r'\w*(repository branch|branch root|checkout root|checkout of branch):'
        r' (?P<branch_path>.+)$')

    # Revision separator (two ..s without escaping, and not followed by a /).
    # This is the same regex used in bzrlib/option.py:_parse_revision_spec.
    REVISION_SEPARATOR_REGEX = re.compile(r'\.\.(?![\\/])')

    def get_repository_info(self):
        """
        Find out information about the current Bazaar branch (if any) and
        return it.
        """
        if not check_install(['bzr', 'help']):
            logging.debug('Unable to execute "bzr help": skipping Bazaar')
            return None

        bzr_info = execute(["bzr", "info"], ignore_errors=True)

        if "ERROR: Not a branch:" in bzr_info:
            # This is not a branch:
            repository_info = None
        else:
            # This is a branch, let's get its attributes:
            branch_match = re.search(self.BRANCH_REGEX, bzr_info, re.MULTILINE)

            path = branch_match.group("branch_path")
            if path == ".":
                path = os.getcwd()

            repository_info = RepositoryInfo(
                path=path,
                base_path="/",    # Diffs are always relative to the root.
                supports_parent_diffs=True)

        return repository_info

    def parse_revision_spec(self, revisions=[]):
        """Parses the given revision spec.

        The 'revisions' argument is a list of revisions as specified by the
        user. Items in the list do not necessarily represent a single revision,
        since the user can use SCM-native syntaxes such as "r1..r2" or "r1:r2".
        SCMTool-specific overrides of this method are expected to deal with
        such syntaxes.

        This will return a dictionary with the following keys:
            'base':        A revision to use as the base of the resulting diff.
            'tip':         A revision to use as the tip of the resulting diff.
            'parent_base': (optional) The revision to use as the base of a
                           parent diff.

        These will be used to generate the diffs to upload to Review Board (or
        print). The diff for review will include the changes in (base, tip],
        and the parent diff (if necessary) will include (parent, base].

        If a single revision is passed in, this will return the parent of that
        revision for 'base' and the passed-in revision for 'tip'.

        If zero revisions are passed in, this will return the current HEAD as
        'tip', and the upstream branch as 'base', taking into account parent
        branches explicitly specified via --parent.
        """
        n_revs = len(revisions)
        result = {}

        if n_revs == 0:
            # No revisions were passed in--start with HEAD, and find the
            # submit branch automatically.
            result['tip'] = self._get_revno()
            result['base'] = self._get_revno('ancestor:')
        elif n_revs == 1 or n_revs == 2:
            # If there's a single argument, try splitting it on '..'
            if n_revs == 1:
                revisions = self.REVISION_SEPARATOR_REGEX.split(revisions[0])
                n_revs = len(revisions)

            if n_revs == 1:
                # Single revision. Extract the parent of that revision to use
                # as the base.
                result['base'] = self._get_revno('before:' + revisions[0])
                result['tip'] = self._get_revno(revisions[0])
            elif n_revs == 2:
                # Two revisions.
                result['base'] = self._get_revno(revisions[0])
                result['tip'] = self._get_revno(revisions[1])
            else:
                raise TooManyRevisionsError

            # XXX: I tried to automatically find the parent diff revision here,
            # but I really don't understand the difference between submit
            # branch, parent branch, bound branches, etc. If there's some way
            # to know what to diff against, we could use
            #     'bzr missing --mine-only --my-revision=(base) --line'
            # to see if we need a parent diff.
        else:
            raise TooManyRevisionsError

        if self.options.parent_branch:
            result['parent_base'] = result['base']
            result['base'] = self._get_revno(
                'ancestor:%s' % self.options.parent_branch)

        return result

    def _get_revno(self, revision_spec=None):
        command = ['bzr', 'revno']
        if revision_spec:
            command += ['-r', revision_spec]

        result = execute(command).strip().split('\n')

        if len(result) == 1:
            return 'revno:' + result[0]
        elif len(result) == 2 and result[0].startswith(USING_PARENT_PREFIX):
            branch = result[0][len(USING_PARENT_PREFIX):]
            return 'revno:%s:%s' % (result[1], branch)

    def diff(self, revisions, files=[], extra_args=[]):
        """Returns the diff for the given revision spec.

        If the revision spec is empty, this returns the diff of the current
        branch with respect to its parent. If a single revision is passed in,
        this returns the diff of the change introduced in that revision. If two
        revisions are passed in, this will do a diff between those two
        revisions.

        The summary and description are set if guessing is enabled.
        """
        diff = self._get_range_diff(revisions['base'], revisions['tip'], files)

        if 'parent_base' in revisions:
            parent_diff = self._get_range_diff(
                revisions['parent_base'], revisions['base'], files)
        else:
            parent_diff = None

        return {
            'diff': diff,
            'parent_diff': parent_diff,
        }

    def _get_range_diff(self, base, tip, files):
        """Return the diff between 'base' and 'tip'."""
        diff_cmd = ['bzr', 'diff', '-q', '-r',
                    '%s..%s' % (base, tip)] + files
        diff = execute(diff_cmd, ignore_errors=True)
        return diff or None

    def get_raw_commit_message(self, revisions):
        # The result is content in the form of:
        #
        # 2014-01-02  First Name  <email@address>
        #
        # <tab>line 1
        # <tab>line 2
        # <tab>...
        #
        # 2014-01-02  First Name  <email@address>
        #
        # ...
        log_cmd = ['bzr', 'log', '-r',
                   '%s..%s' % (revisions['base'], revisions['tip'])]

        # Find out how many commits there are, then log limiting to one fewer.
        # This is because diff treats the range as (r1, r2] while log treats
        # the lange as [r1, r2].
        lines = execute(log_cmd + ['--line'],
                        ignore_errors=True, split_lines=True)
        n_revs = len(lines) - 1

        lines = execute(log_cmd + ['--gnu-changelog', '-l', str(n_revs)],
                        ignore_errors=True, split_lines=True)

        message = []

        for line in lines:
            # We only care about lines that start with a tab (commit message
            # lines) or blank lines.
            if line.startswith('\t'):
                message.append(line[1:])
            elif not line.strip():
                message.append(line)

        return ''.join(message).strip()

########NEW FILE########
__FILENAME__ = clearcase
import logging
import os
import sys
from pkg_resources import parse_version

from rbtools.api.errors import APIError
from rbtools.clients import SCMClient, RepositoryInfo
from rbtools.clients.errors import InvalidRevisionSpecError
from rbtools.utils.checks import check_gnu_diff, check_install
from rbtools.utils.filesystem import make_tempfile
from rbtools.utils.process import die, execute

# This specific import is necessary to handle the paths for
# cygwin enabled machines.
if (sys.platform.startswith('win')
    or sys.platform.startswith('cygwin')):
    import ntpath as cpath
else:
    import posixpath as cpath


class ClearCaseClient(SCMClient):
    """
    A wrapper around the clearcase tool that fetches repository
    information and generates compatible diffs.
    This client assumes that cygwin is installed on windows.
    """
    name = 'ClearCase'
    viewtype = None

    REVISION_BRANCH_PREFIX = 'brtype:'
    REVISION_CHECKEDOUT_BASE = '--rbtools-checkedout-base'
    REVISION_CHECKEDOUT_CHANGESET = '--rbtools-checkedout-changeset'
    REVISION_FILES = '--rbtools-files'

    def __init__(self, **kwargs):
        super(ClearCaseClient, self).__init__(**kwargs)

    def get_repository_info(self):
        """Returns information on the Clear Case repository.

        This will first check if the cleartool command is installed and in the
        path, and that the current working directory is inside of the view.
        """
        if not check_install(['cleartool', 'help']):
            logging.debug('Unable to execute "cleartool help": skipping '
                          'ClearCase')
            return None

        viewname = execute(["cleartool", "pwv", "-short"]).strip()
        if viewname.startswith('** NONE'):
            return None

        # Now that we know it's ClearCase, make sure we have GNU diff
        # installed, and error out if we don't.
        check_gnu_diff()

        property_lines = execute(
            ["cleartool", "lsview", "-full", "-properties", "-cview"],
            split_lines=True)
        for line in property_lines:
            properties = line.split(' ')
            if properties[0] == 'Properties:':
                # Determine the view type and check if it's supported.
                #
                # Specifically check if webview was listed in properties
                # because webview types also list the 'snapshot'
                # entry in properties.
                if 'webview' in properties:
                    die("Webviews are not supported. You can use rbt commands"
                        " only in dynamic or snapshot views.")
                if 'dynamic' in properties:
                    self.viewtype = 'dynamic'
                else:
                    self.viewtype = 'snapshot'

                break

        # Find current VOB's tag
        vobstag = execute(["cleartool", "describe", "-short", "vob:."],
                          ignore_errors=True).strip()
        if "Error: " in vobstag:
            die("To generate diff run rbt inside vob.")

        root_path = execute(["cleartool", "pwv", "-root"],
                            ignore_errors=True).strip()
        if "Error: " in root_path:
            die("To generate diff run rbt inside view.")

        # From current working directory cut path to VOB.
        # VOB's tag contain backslash character before VOB's name.
        # I hope that first character of VOB's tag like '\new_proj'
        # won't be treat as new line character but two separate:
        # backslash and letter 'n'
        cwd = os.getcwd()
        base_path = cwd[:len(root_path) + len(vobstag)]

        return ClearCaseRepositoryInfo(path=base_path,
                                       base_path=base_path,
                                       vobstag=vobstag,
                                       supports_parent_diffs=False)

    def _determine_version(self, version_path):
        """Determine numeric version of revision.

        CHECKEDOUT is marked as infinity to be treated
        always as highest possible version of file.
        CHECKEDOUT, in ClearCase, is something like HEAD.
        """
        branch, number = cpath.split(version_path)
        if number == 'CHECKEDOUT':
            return float('inf')
        return int(number)

    def _construct_extended_path(self, path, version):
        """Combine extended_path from path and version.

        CHECKEDOUT must be removed becasue this one version
        doesn't exists in MVFS (ClearCase dynamic view file
        system). Only way to get content of checked out file
        is to use filename only."""
        if not version or version.endswith('CHECKEDOUT'):
            return path

        return "%s@@%s" % (path, version)

    def parse_revision_spec(self, revisions):
        """Parses the given revision spec.

        The 'revisions' argument is a list of revisions as specified by the
        user. Items in the list do not necessarily represent a single revision,
        since the user can use SCM-native syntaxes such as "r1..r2" or "r1:r2".
        SCMTool-specific overrides of this method are expected to deal with
        such syntaxes.

        This will return a dictionary with the following keys:
            'base':        A revision to use as the base of the resulting diff.
            'tip':         A revision to use as the tip of the resulting diff.

        These will be used to generate the diffs to upload to Review Board (or
        print).

        There are many different ways to generate diffs for clearcase, because
        there are so many different workflows. This method serves more as a way
        to validate the passed-in arguments than actually parsing them in the
        way that other clients do.
        """
        n_revs = len(revisions)

        if n_revs == 0:
            return {
                'base': self.REVISION_CHECKEDOUT_BASE,
                'tip': self.REVISION_CHECKEDOUT_CHANGESET,
            }
        elif n_revs == 1:
            if revisions[0].startswith(self.REVISION_BRANCH_PREFIX):
                return {
                    'base': self.REVISION_BRANCH_BASE,
                    'tip': revisions[0][len(self.REVISION_BRANCH_PREFIX):],
                }
            # TODO:
            # activity:activity[@pvob] => review changes in this UCM activity
            # lbtype:label1            => review changes between this label
            #                             and the working directory
            # stream:streamname[@pvob] => review changes in this UCM stream
            #                             (UCM "branch")
            # baseline:baseline[@pvob] => review changes between this baseline
            #                             and the working directory
        elif n_revs == 2:
            # TODO:
            # lbtype:label1 lbtype:label2 => review changes between these two
            #                                labels
            # baseline:baseline1[@pvob] baseline:baseline2[@pvob]
            #                             => review changes between these two
            #                                baselines
            pass

        pairs = []
        for r in revisions:
            p = r.split(':')
            if len(p) != 2:
                raise InvalidRevisionSpecError(
                    '"%s" is not a valid file@revision pair' % r)
            pairs.append(p)

        return {
            'base': self.REVISION_FILES,
            'tip': pairs,
        }

    def _sanitize_branch_changeset(self, changeset):
        """Return changeset containing non-binary, branched file versions.

        Changeset contain only first and last version of file made on branch.
        """
        changelist = {}

        for path, previous, current in changeset:
            version_number = self._determine_version(current)

            if path not in changelist:
                changelist[path] = {
                    'highest': version_number,
                    'current': current,
                    'previous': previous
                }

            if version_number == 0:
                # Previous version of 0 version on branch is base
                changelist[path]['previous'] = previous
            elif version_number > changelist[path]['highest']:
                changelist[path]['highest'] = version_number
                changelist[path]['current'] = current

        # Convert to list
        changeranges = []
        for path, version in changelist.iteritems():
            changeranges.append(
                (self._construct_extended_path(path, version['previous']),
                 self._construct_extended_path(path, version['current']))
            )

        return changeranges

    def _sanitize_checkedout_changeset(self, changeset):
        """Return changeset containing non-binary, checkdout file versions."""

        changeranges = []
        for path, previous, current in changeset:
            changeranges.append(
                (self._construct_extended_path(path, previous),
                 self._construct_extended_path(path, current))
            )

        return changeranges

    def _sanitize_version_0_file(self, file_revision):
        """Replace file version with Predecessor version when
        version is 0 except for /main/0."""

        # There is no predecessor for @@/main/0, so keep current revision.
        if file_revision.endswith("@@/main/0"):
            return file_revision

        if file_revision.endswith("/0"):
            logging.debug("Found file %s with version 0", file_revision)
            file_revision = execute(["cleartool",
                                     "describe",
                                     "-fmt", "%En@@%PSn",
                                     file_revision])
            logging.debug("Sanitized with predecessor, new file: %s",
                          file_revision)

        return file_revision

    def _sanitize_version_0_changeset(self, changeset):
        """Return changeset sanitized of its <branch>/0 version.

        Indeed this predecessor (equal to <branch>/0) should already be
        available from previous vob synchro in multi-site context.
        """

        sanitized_changeset = []
        for old_file, new_file in changeset:
            # This should not happen for new file but it is safer to sanitize
            # both file revisions.
            sanitized_changeset.append(
                (self._sanitize_version_0_file(old_file),
                 self._sanitize_version_0_file(new_file)))

        return sanitized_changeset

    def _directory_content(self, path):
        """Return directory content ready for saving to tempfile."""

        # Get the absolute path of each element located in path, but only
        # clearcase elements => -vob_only
        output = execute(["cleartool", "ls", "-short", "-nxname", "-vob_only",
                          path])
        lines = output.splitlines(True)

        content = []
        # The previous command returns absolute file paths but only file names
        # are required.
        for absolute_path in lines:
            short_path = os.path.basename(absolute_path.strip())
            content.append(short_path)

        return ''.join([
            '%s\n' % s
            for s in sorted(content)])

    def _construct_changeset(self, output):
        return [
            info.split('\t')
            for info in output.strip().split('\n')
        ]

    def _get_checkedout_changeset(self):
        """Return information about the checked out changeset.

        This function returns: kind of element, path to file,
        previews and current file version.
        """
        changeset = []
        # We ignore return code 1 in order to omit files that Clear Case can't
        # read.
        output = execute([
            "cleartool",
            "lscheckout",
            "-all",
            "-cview",
            "-me",
            "-fmt",
            r"%En\t%PVn\t%Vn\n"],
            extra_ignore_errors=(1,),
            with_errors=False)

        if output:
            changeset = self._construct_changeset(output)

        return self._sanitize_checkedout_changeset(changeset)

    def _get_branch_changeset(self, branch):
        """Returns information about the versions changed on a branch.

        This takes into account the changes on the branch owned by the
        current user in all vobs of the current view.
        """
        changeset = []

        # We ignore return code 1 in order to omit files that Clear Case can't
        # read.
        if sys.platform.startswith('win'):
            CLEARCASE_XPN = '%CLEARCASE_XPN%'
        else:
            CLEARCASE_XPN = '$CLEARCASE_XPN'

        output = execute(
            [
                "cleartool",
                "find",
                "-all",
                "-version",
                "brtype(%s)" % branch,
                "-exec",
                'cleartool descr -fmt "%%En\t%%PVn\t%%Vn\n" %s' % CLEARCASE_XPN
            ],
            extra_ignore_errors=(1,),
            with_errors=False)

        if output:
            changeset = self._construct_changeset(output)

        return self._sanitize_branch_changeset(changeset)

    def diff(self, revisions, files=[], extra_args=[]):
        if files:
            raise Exception(
                'The ClearCase backend does not currently support the '
                '-I/--include parameter. To diff for specific files, pass in '
                'file@revision1:file@revision2 pairs as arguments')

        if revisions['tip'] == self.REVISION_CHECKEDOUT_CHANGESET:
            changeset = self._get_checkedout_changeset()
            return self._do_diff(changeset)
        elif revisions['base'] == self.REVISION_BRANCH_BASE:
            changeset = self._get_branch_changeset(revisions['tip'])
            return self._do_diff(changeset)
        elif revisions['base'] == self.REVISION_FILES:
            files = revisions['tip']
            return self._do_diff(files)
        else:
            assert False

    def _diff_files(self, old_file, new_file):
        """Return unified diff for file.

        Most effective and reliable way is use gnu diff.
        """

        # In snapshot view, diff can't access history clearcase file version
        # so copy cc files to tempdir by 'cleartool get -to dest-pname pname',
        # and compare diff with the new temp ones.
        if self.viewtype == 'snapshot':
            # Create temporary file first.
            tmp_old_file = make_tempfile()
            tmp_new_file = make_tempfile()

            # Delete so cleartool can write to them.
            try:
                os.remove(tmp_old_file)
            except OSError:
                pass

            try:
                os.remove(tmp_new_file)
            except OSError:
                pass

            execute(["cleartool", "get", "-to", tmp_old_file, old_file])
            execute(["cleartool", "get", "-to", tmp_new_file, new_file])
            diff_cmd = ["diff", "-uN", tmp_old_file, tmp_new_file]
        else:
            diff_cmd = ["diff", "-uN", old_file, new_file]

        dl = execute(diff_cmd, extra_ignore_errors=(1, 2),
                     translate_newlines=False)

        # Replace temporary file name in diff with the one in snapshot view.
        if self.viewtype == "snapshot":
            dl = dl.replace(tmp_old_file, old_file)
            dl = dl.replace(tmp_new_file, new_file)

        # If the input file has ^M characters at end of line, lets ignore them.
        dl = dl.replace('\r\r\n', '\r\n')
        dl = dl.splitlines(True)

        # Special handling for the output of the diff tool on binary files:
        #     diff outputs "Files a and b differ"
        # and the code below expects the output to start with
        #     "Binary files "
        if (len(dl) == 1 and
            dl[0].startswith('Files %s and %s differ' % (old_file, new_file))):
            dl = ['Binary files %s and %s differ\n' % (old_file, new_file)]

        # We need oids of files to translate them to paths on reviewboard
        # repository.
        old_oid = execute(["cleartool", "describe", "-fmt", "%On", old_file])
        new_oid = execute(["cleartool", "describe", "-fmt", "%On", new_file])

        if dl == [] or dl[0].startswith("Binary files "):
            if dl == []:
                dl = ["File %s in your changeset is unmodified\n" % new_file]

            dl.insert(0, "==== %s %s ====\n" % (old_oid, new_oid))
            dl.append('\n')
        else:
            dl.insert(2, "==== %s %s ====\n" % (old_oid, new_oid))

        return dl

    def _diff_directories(self, old_dir, new_dir):
        """Return uniffied diff between two directories content.

        Function save two version's content of directory to temp
        files and treate them as casual diff between two files.
        """
        old_content = self._directory_content(old_dir)
        new_content = self._directory_content(new_dir)

        old_tmp = make_tempfile(content=old_content)
        new_tmp = make_tempfile(content=new_content)

        diff_cmd = ["diff", "-uN", old_tmp, new_tmp]
        dl = execute(diff_cmd,
                     extra_ignore_errors=(1, 2),
                     translate_newlines=False,
                     split_lines=True)

        # Replace temporary filenames with real directory names and add ids
        if dl:
            dl[0] = dl[0].replace(old_tmp, old_dir)
            dl[1] = dl[1].replace(new_tmp, new_dir)
            old_oid = execute(["cleartool", "describe", "-fmt", "%On",
                               old_dir])
            new_oid = execute(["cleartool", "describe", "-fmt", "%On",
                               new_dir])
            dl.insert(2, "==== %s %s ====\n" % (old_oid, new_oid))

        return dl

    def _do_diff(self, changeset):
        """Generates a unified diff for all files in the changeset."""
        # Sanitize all changesets of version 0 before processing
        changeset = self._sanitize_version_0_changeset(changeset)

        diff = []
        for old_file, new_file in changeset:
            dl = []

            # cpath.isdir does not work for snapshot views but this
            # information can be found using `cleartool describe`.
            if self.viewtype == 'snapshot':
                # ClearCase object path is file path + @@
                object_path = new_file.split('@@')[0] + '@@'
                output = execute(["cleartool", "describe", "-fmt", "%m",
                                  object_path])
                object_kind = output.strip()
                isdir = object_kind == 'directory element'
            else:
                isdir = cpath.isdir(new_file)

            if isdir:
                dl = self._diff_directories(old_file, new_file)
            elif cpath.exists(new_file) or self.viewtype == 'snapshot':
                dl = self._diff_files(old_file, new_file)
            else:
                logging.error("File %s does not exist or access is denied."
                              % new_file)
                continue

            if dl:
                diff.append(''.join(dl))

        return {
            'diff': ''.join(diff),
        }


class ClearCaseRepositoryInfo(RepositoryInfo):
    """
    A representation of a ClearCase source code repository. This version knows
    how to find a matching repository on the server even if the URLs differ.
    """

    def __init__(self, path, base_path, vobstag, supports_parent_diffs=False):
        RepositoryInfo.__init__(self, path, base_path,
                                supports_parent_diffs=supports_parent_diffs)
        self.vobstag = vobstag

    def find_server_repository_info(self, server):
        """
        The point of this function is to find a repository on the server that
        matches self, even if the paths aren't the same. (For example, if self
        uses an 'http' path, but the server uses a 'file' path for the same
        repository.) It does this by comparing VOB's name and uuid. If the
        repositories use the same path, you'll get back self, otherwise you'll
        get a different ClearCaseRepositoryInfo object (with a different path).
        """

        # Find VOB's family uuid based on VOB's tag
        uuid = self._get_vobs_uuid(self.vobstag)
        logging.debug("Repository's %s uuid is %r" % (self.vobstag, uuid))

        repositories = server.get_repositories()

        # To reduce HTTP requests (_get_repository_info call), we build an
        # ordered list of ClearCase repositories starting with the ones that
        # have a matching vobstag.
        repository_scan_order = []

        for repository in repositories:
            # Ignore non-ClearCase repositories
            if repository['tool'] != 'ClearCase':
                continue

            # Add repos where the vobstag matches at the beginning and others
            # at the end.
            if repository['name'] == self.vobstag:
                repository_scan_order.insert(0, repository)
            else:
                repository_scan_order.append(repository)

        # Now try to find a matching uuid
        for repository in repository_scan_order:
            repo_name = repository['name']
            try:
                info = self._get_repository_info(server, repository)
            except APIError, e:
                # If the current repository is not publicly accessible and the
                # current user has no explicit access to it, the server will
                # return error_code 101 and http_status 403.
                if not (e.error_code == 101 and e.http_status == 403):
                    # We can safely ignore this repository unless the VOB tag
                    # matches.
                    if repo_name == self.vobstag:
                        die('You do not have permission to access this '
                            'repository.')

                    continue
                else:
                    # Bubble up any other errors
                    raise e

            if not info or uuid != info['uuid']:
                continue

            path = info['repopath']
            logging.debug('Matching repository uuid:%s with path:%s',
                          uuid, path)
            return ClearCaseRepositoryInfo(path, path, uuid)

        # We didn't found uuid but if version is >= 1.5.3
        # we can try to use VOB's name hoping it is better
        # than current VOB's path.
        if parse_version(server.rb_version) >= parse_version('1.5.3'):
            self.path = cpath.split(self.vobstag)[1]

        # We didn't find a matching repository on the server.
        # We'll just return self and hope for the best.
        return self

    def _get_vobs_uuid(self, vobstag):
        """Return family uuid of VOB."""

        property_lines = execute(["cleartool", "lsvob", "-long", vobstag],
                                 split_lines=True)
        for line in property_lines:
            if line.startswith('Vob family uuid:'):
                return line.split(' ')[-1].rstrip()

    def _get_repository_info(self, server, repository):
        try:
            return server.get_repository_info(repository['id'])
        except APIError, e:
            # If the server couldn't fetch the repository info, it will return
            # code 210. Ignore those.
            # Other more serious errors should still be raised, though.
            if e.error_code == 210:
                return None

            raise e

########NEW FILE########
__FILENAME__ = cvs
import logging
import os
import socket

from rbtools.clients import SCMClient, RepositoryInfo
from rbtools.clients.errors import (InvalidRevisionSpecError,
                                    TooManyRevisionsError)
from rbtools.utils.checks import check_install
from rbtools.utils.process import execute


class CVSClient(SCMClient):
    """
    A wrapper around the cvs tool that fetches repository
    information and generates compatible diffs.
    """
    name = 'CVS'

    REVISION_WORKING_COPY = '--rbtools-working-copy'

    def __init__(self, **kwargs):
        super(CVSClient, self).__init__(**kwargs)

    def get_repository_info(self):
        if not check_install(['cvs']):
            logging.debug('Unable to execute "cvs": skipping CVS')
            return None

        cvsroot_path = os.path.join("CVS", "Root")

        if not os.path.exists(cvsroot_path):
            return None

        fp = open(cvsroot_path, "r")
        repository_path = fp.read().strip()
        fp.close()

        i = repository_path.find("@")
        if i != -1:
            repository_path = repository_path[i + 1:]

        i = repository_path.rfind(":")
        if i != -1:
            host = repository_path[:i]
            try:
                canon = socket.getfqdn(host)
                repository_path = repository_path.replace('%s:' % host,
                                                          '%s:' % canon)
            except socket.error, msg:
                logging.error("failed to get fqdn for %s, msg=%s"
                              % (host, msg))

        return RepositoryInfo(path=repository_path)

    def parse_revision_spec(self, revisions=[]):
        """Parses the given revision spec.

        The 'revisions' argument is a list of revisions as specified by the
        user. Items in the list do not necessarily represent a single revision,
        since the user can use SCM-native syntaxes such as "r1..r2" or "r1:r2".
        SCMTool-specific overrides of this method are expected to deal with
        such syntaxes.

        This will return a dictionary with the following keys:
            'base':        A revision to use as the base of the resulting diff.
            'tip':         A revision to use as the tip of the resulting diff.

        These will be used to generate the diffs to upload to Review Board (or
        print). The diff for review will include the changes in (base, tip].

        If a single revision is passed in, this will raise an exception,
        because CVS doesn't have a repository-wide concept of "revision", so
        selecting an individual "revision" doesn't make sense.

        With two revisions, this will treat those revisions as tags and do a
        diff between those tags.

        If zero revisions are passed in, this will return revisions relevant
        for the "current change". The exact definition of what "current" means
        is specific to each SCMTool backend, and documented in the
        implementation classes.

        The CVS SCMClient never fills in the 'parent_base' key. Users who are
        using other patch-stack tools who want to use parent diffs with CVS
        will have to generate their diffs by hand.

        Because `cvs diff` uses multiple arguments to define multiple tags,
        there's no single-argument/multiple-revision syntax available.
        """
        n_revs = len(revisions)

        if n_revs == 0:
            return {
                'base': 'BASE',
                'tip': self.REVISION_WORKING_COPY,
            }
        elif n_revs == 1:
            raise InvalidRevisionSpecError(
                'CVS does not support passing in a single revision.')
        elif n_revs == 2:
            return {
                'base': revisions[0],
                'tip': revisions[1],
            }
        else:
            raise TooManyRevisionsError

        return {
            'base': None,
            'tip': None,
        }

    def diff(self, revisions, files=[], extra_args=[]):
        """Get the diff for the given revisions.

        If revision_spec is empty, this will return the diff for the modified
        files in the working directory. If it's not empty and contains two
        revisions, this will do a diff between those revisions.
        """
        files = files or []

        # Diff returns "1" if differences were found.
        diff_cmd = ['cvs', 'diff', '-uN']

        base = revisions['base']
        tip = revisions['tip']
        if (not (base == 'BASE' and
                 tip == self.REVISION_WORKING_COPY)):
            diff_cmd.extend(['-r', base, '-r', tip])

        return {
            'diff': execute(diff_cmd + files, extra_ignore_errors=(1,)),
        }

########NEW FILE########
__FILENAME__ = errors
class OptionsCheckError(Exception):
    """
    An error that represents when command-line options were used
    inappropriately for the given SCMClient backend. The message in the
    exception is presented to the user.
    """
    pass


class InvalidRevisionSpecError(Exception):
    """An error for when the specified revisions are invalid."""
    pass


class TooManyRevisionsError(InvalidRevisionSpecError):
    """An error for when too many revisions were specified."""
    def __init__(self):
        super(TooManyRevisionsError, self).__init__(
            'Too many revisions specified')


class EmptyChangeError(Exception):
    def __init__(self):
        super(EmptyChangeError, self).__init(
            "Couldn't find any affected files for this change.")

########NEW FILE########
__FILENAME__ = git
import logging
import os
import re
import sys

from rbtools.clients import SCMClient, RepositoryInfo
from rbtools.clients.errors import (InvalidRevisionSpecError,
                                    TooManyRevisionsError)
from rbtools.clients.perforce import PerforceClient
from rbtools.clients.svn import SVNClient, SVNRepositoryInfo
from rbtools.utils.checks import check_install
from rbtools.utils.console import edit_text
from rbtools.utils.process import die, execute


class GitClient(SCMClient):
    """
    A wrapper around git that fetches repository information and generates
    compatible diffs. This will attempt to generate a diff suitable for the
    remote repository, whether git, SVN or Perforce.
    """
    name = 'Git'

    def __init__(self, **kwargs):
        super(GitClient, self).__init__(**kwargs)
        # Store the 'correct' way to invoke git, just plain old 'git' by
        # default.
        self.git = 'git'

    def parse_revision_spec(self, revisions=[]):
        """Parses the given revision spec.

        The 'revisions' argument is a list of revisions as specified by the
        user. Items in the list do not necessarily represent a single revision,
        since the user can use SCM-native syntaxes such as "r1..r2" or "r1:r2".
        SCMTool-specific overrides of this method are expected to deal with
        such syntaxes.

        This will return a dictionary with the following keys:
            'base':        A revision to use as the base of the resulting diff.
            'tip':         A revision to use as the tip of the resulting diff.
            'parent_base': (optional) The revision to use as the base of a
                           parent diff.
            'commit_id':   (optional) The ID of the single commit being posted,
                           if not using a range.

        These will be used to generate the diffs to upload to Review Board (or
        print). The diff for review will include the changes in (base, tip],
        and the parent diff (if necessary) will include (parent_base, base].

        If a single revision is passed in, this will return the parent of that
        revision for 'base' and the passed-in revision for 'tip'.

        If zero revisions are passed in, this will return the current HEAD as
        'tip', and the upstream branch as 'base', taking into account parent
        branches explicitly specified via --parent.
        """
        n_revs = len(revisions)
        result = {}

        if n_revs == 0:
            # No revisions were passed in--start with HEAD, and find the
            # tracking branch automatically.
            parent_branch = self.get_parent_branch()
            head_ref = self._rev_parse(self.get_head_ref())[0]
            merge_base = self._rev_parse(
                self._get_merge_base(head_ref, self.upstream_branch))[0]

            result = {
                'tip': head_ref,
                'commit_id': head_ref,
            }

            if parent_branch:
                result['base'] = self._rev_parse(parent_branch)[0]
                result['parent_base'] = merge_base
            else:
                result['base'] = merge_base

            # Since the user asked us to operate on HEAD, warn them about a
            # dirty working directory
            if self.has_pending_changes():
                logging.warning('Your working directory is not clean. Any '
                                'changes which have not been committed '
                                'to a branch will not be included in your '
                                'review request.')
        elif n_revs == 1 or n_revs == 2:
            # Let `git rev-parse` sort things out.
            parsed = self._rev_parse(revisions)

            n_parsed_revs = len(parsed)
            assert n_parsed_revs <= 3

            if n_parsed_revs == 1:
                # Single revision. Extract the parent of that revision to use
                # as the base.
                parent = self._rev_parse('%s^' % parsed[0])[0]
                result = {
                    'base': parent,
                    'tip': parsed[0],
                    'commit_id': parsed[0],
                }
            elif n_parsed_revs == 2:
                if parsed[1].startswith('^'):
                    # Passed in revisions were probably formatted as
                    # "base..tip". The rev-parse output includes all ancestors
                    # of the first part, and none of the ancestors of the
                    # second. Basically, the second part is the base (after
                    # stripping the ^ prefix) and the first is the tip.
                    result = {
                        'base': parsed[1][1:],
                        'tip': parsed[0],
                    }
                else:
                    # First revision is base, second is tip
                    result = {
                        'base': parsed[0],
                        'tip': parsed[1],
                    }
            elif n_parsed_revs == 3 and parsed[2].startswith('^'):
                # Revision spec is diff-since-merge. Find the merge-base of the
                # two revs to use as base.
                merge_base = execute([self.git, 'merge-base', parsed[0],
                                      parsed[1]]).strip()
                result = {
                    'base': merge_base,
                    'tip': parsed[0],
                }
            else:
                raise InvalidRevisionSpecError(
                    'Unexpected result while parsing revision spec')

            parent_base = self._get_merge_base(result['base'],
                                               self.upstream_branch)
            if parent_base != result['base']:
                result['parent_base'] = parent_base
        else:
            raise TooManyRevisionsError

        return result

    def get_repository_info(self):
        if not check_install(['git', '--help']):
            # CreateProcess (launched via subprocess, used by check_install)
            # does not automatically append .cmd for things it finds in PATH.
            # If we're on Windows, and this works, save it for further use.
            if (sys.platform.startswith('win') and
                check_install(['git.cmd', '--help'])):
                self.git = 'git.cmd'
            else:
                logging.debug('Unable to execute "git --help" or "git.cmd '
                              '--help": skipping Git')
                return None

        git_dir = execute([self.git, "rev-parse", "--git-dir"],
                          ignore_errors=True).rstrip("\n")

        if git_dir.startswith("fatal:") or not os.path.isdir(git_dir):
            return None

        # Sometimes core.bare is not set, and generates an error, so ignore
        # errors. Valid values are 'true' or '1'.
        bare = execute([self.git, 'config', 'core.bare'],
                       ignore_errors=True).strip()
        self.bare = bare in ('true', '1')

        # Running in directories other than the top level of
        # of a work-tree would result in broken diffs on the server
        if not self.bare:
            git_top = execute([self.git, "rev-parse", "--show-toplevel"],
                              ignore_errors=True).rstrip("\n")

            # Top level might not work on old git version se we use git dir
            # to find it.
            if (git_top.startswith('fatal:') or not os.path.isdir(git_dir)
                or git_top.startswith('cygdrive')):
                git_top = git_dir

            os.chdir(os.path.abspath(git_top))

        self.head_ref = execute([self.git, 'symbolic-ref', '-q',
                                 'HEAD'], ignore_errors=True).strip()

        # We know we have something we can work with. Let's find out
        # what it is. We'll try SVN first, but only if there's a .git/svn
        # directory. Otherwise, it may attempt to create one and scan
        # revisions, which can be slow. Also skip SVN detection if the git
        # repository was specified on command line.
        git_svn_dir = os.path.join(git_dir, 'svn')

        if (not getattr(self.options, 'repository_url', None) and
            os.path.isdir(git_svn_dir) and len(os.listdir(git_svn_dir)) > 0):
            data = execute([self.git, "svn", "info"], ignore_errors=True)

            m = re.search(r'^Repository Root: (.+)$', data, re.M)

            if m:
                path = m.group(1)
                m = re.search(r'^URL: (.+)$', data, re.M)

                if m:
                    base_path = m.group(1)[len(path):] or "/"
                    m = re.search(r'^Repository UUID: (.+)$', data, re.M)

                    if m:
                        uuid = m.group(1)
                        self.type = "svn"

                        # Get SVN tracking branch
                        if getattr(self.options, 'tracking', None):
                            self.upstream_branch = self.options.tracking
                        else:
                            data = execute([self.git, "svn", "rebase", "-n"],
                                           ignore_errors=True)
                            m = re.search(r'^Remote Branch:\s*(.+)$', data,
                                          re.M)

                            if m:
                                self.upstream_branch = m.group(1)
                            else:
                                sys.stderr.write('Failed to determine SVN '
                                                 'tracking branch. Defaulting'
                                                 'to "master"\n')
                                self.upstream_branch = 'master'

                        return SVNRepositoryInfo(path=path,
                                                 base_path=base_path,
                                                 uuid=uuid,
                                                 supports_parent_diffs=True)
            else:
                # Versions of git-svn before 1.5.4 don't (appear to) support
                # 'git svn info'.  If we fail because of an older git install,
                # here, figure out what version of git is installed and give
                # the user a hint about what to do next.
                version = execute([self.git, "svn", "--version"],
                                  ignore_errors=True)
                version_parts = re.search('version (\d+)\.(\d+)\.(\d+)',
                                          version)
                svn_remote = execute(
                    [self.git, "config", "--get", "svn-remote.svn.url"],
                    ignore_errors=True)

                if (version_parts and svn_remote and
                    not self.is_valid_version((int(version_parts.group(1)),
                                               int(version_parts.group(2)),
                                               int(version_parts.group(3))),
                                              (1, 5, 4))):
                    die("Your installation of git-svn must be upgraded to "
                        "version 1.5.4 or later")

        # Okay, maybe Perforce (git-p4).
        git_p4_ref = os.path.join(git_dir, 'refs', 'remotes', 'p4', 'master')
        if os.path.exists(git_p4_ref):
            data = execute([self.git, 'config', '--get', 'git-p4.port'],
                           ignore_errors=True)
            m = re.search(r'(.+)', data)
            if m:
                port = m.group(1)
            else:
                port = os.getenv('P4PORT')

            if port:
                self.type = 'perforce'
                self.upstream_branch = 'remotes/p4/master'
                return RepositoryInfo(path=port,
                                      base_path='',
                                      supports_parent_diffs=True)

        # Nope, it's git then.
        # Check for a tracking branch and determine merge-base
        self.upstream_branch = ''
        if self.head_ref:
            short_head = self._strip_heads_prefix(self.head_ref)
            merge = execute([self.git, 'config', '--get',
                             'branch.%s.merge' % short_head],
                            ignore_errors=True).strip()
            remote = execute([self.git, 'config', '--get',
                              'branch.%s.remote' % short_head],
                             ignore_errors=True).strip()

            merge = self._strip_heads_prefix(merge)

            if remote and remote != '.' and merge:
                self.upstream_branch = '%s/%s' % (remote, merge)

        url = None
        if getattr(self.options, 'repository_url', None):
            url = self.options.repository_url
            self.upstream_branch = self.get_origin(self.upstream_branch,
                                                   True)[0]
        else:
            self.upstream_branch, origin_url = \
                self.get_origin(self.upstream_branch, True)

            if not origin_url or origin_url.startswith("fatal:"):
                self.upstream_branch, origin_url = self.get_origin()

            url = origin_url.rstrip('/')

            # Central bare repositories don't have origin URLs.
            # We return git_dir instead and hope for the best.
            if not url:
                url = os.path.abspath(git_dir)

                # There is no remote, so skip this part of upstream_branch.
                self.upstream_branch = self.upstream_branch.split('/')[-1]

        if url:
            self.type = "git"
            return RepositoryInfo(path=url, base_path='',
                                  supports_parent_diffs=True)

        return None

    def _strip_heads_prefix(self, ref):
        """Strips prefix from ref name, if possible."""
        return re.sub(r'^refs/heads/', '', ref)

    def get_origin(self, default_upstream_branch=None, ignore_errors=False):
        """Get upstream remote origin from options or parameters.

        Returns a tuple: (upstream_branch, remote_url)
        """
        upstream_branch = (getattr(self.options, 'tracking', None) or
                           default_upstream_branch or
                           'origin/master')
        upstream_remote = upstream_branch.split('/')[0]
        origin_url = execute(
            [self.git, "config", "--get", "remote.%s.url" % upstream_remote],
            ignore_errors=True).rstrip("\n")
        return (upstream_branch, origin_url)

    def is_valid_version(self, actual, expected):
        """
        Takes two tuples, both in the form:
            (major_version, minor_version, micro_version)
        Returns true if the actual version is greater than or equal to
        the expected version, and false otherwise.
        """
        return ((actual[0] > expected[0]) or
                (actual[0] == expected[0] and actual[1] > expected[1]) or
                (actual[0] == expected[0] and actual[1] == expected[1] and
                 actual[2] >= expected[2]))

    def scan_for_server(self, repository_info):
        # Scan first for dot files, since it's faster and will cover the
        # user's $HOME/.reviewboardrc
        server_url = super(GitClient, self).scan_for_server(repository_info)

        if server_url:
            return server_url

        # TODO: Maybe support a server per remote later? Is that useful?
        url = execute([self.git, "config", "--get", "reviewboard.url"],
                      ignore_errors=True).strip()
        if url:
            return url

        if self.type == "svn":
            # Try using the reviewboard:url property on the SVN repo, if it
            # exists.
            prop = SVNClient().scan_for_server_property(repository_info)

            if prop:
                return prop
        elif self.type == 'perforce':
            prop = PerforceClient().scan_for_server(repository_info)

            if prop:
                return prop

        return None

    def get_raw_commit_message(self, revisions):
        """Extracts the commit message based on the provided revision range."""
        return execute(
            [self.git, 'log', '--reverse', '--pretty=format:%s%n%n%b',
             '^%s' % revisions['base'], revisions['tip']],
            ignore_errors=True).strip()

    def get_parent_branch(self):
        """Returns the parent branch."""
        if self.type == 'perforce':
            parent_branch = self.options.parent_branch or 'p4'
        else:
            parent_branch = self.options.parent_branch

        return parent_branch

    def get_head_ref(self):
        """Returns the HEAD reference."""
        head_ref = "HEAD"

        if self.head_ref:
            head_ref = self.head_ref

        return head_ref

    def _get_merge_base(self, rev1, rev2):
        """Returns the merge base."""
        return execute([self.git, "merge-base", rev1, rev2]).strip()

    def _rev_parse(self, revisions):
        """Runs `git rev-parse` and returns a list of revisions."""
        if not isinstance(revisions, list):
            revisions = [revisions]

        return execute([self.git, 'rev-parse'] + revisions).strip().split('\n')

    def diff(self, revisions, files=[], extra_args=[]):
        """Perform a diff using the given revisions.

        If no revisions are specified, this will do a diff of the contents of
        the current branch since the tracking branch (which defaults to
        'master'). If one revision is specified, this will get the diff of that
        specific change. If two revisions are specified, this will do a diff
        between those two revisions.

        If a parent branch is specified via the command-line options, or would
        make sense given the requested revisions and the tracking branch, this
        will also return a parent diff.
        """
        try:
            merge_base = revisions['parent_base']
        except KeyError:
            merge_base = revisions['base']

        diff_lines = self.make_diff(merge_base,
                                    revisions['base'],
                                    revisions['tip'],
                                    files)

        if 'parent_base' in revisions:
            parent_diff_lines = self.make_diff(merge_base,
                                               revisions['parent_base'],
                                               revisions['base'],
                                               files)
            base_commit_id = revisions['parent_base']
        else:
            parent_diff_lines = None
            base_commit_id = revisions['base']

        return {
            'diff': diff_lines,
            'parent_diff': parent_diff_lines,
            'commit_id': revisions.get('commit_id'),
            'base_commit_id': base_commit_id,
        }

    def make_diff(self, merge_base, base, tip, files):
        """Performs a diff on a particular branch range."""
        rev_range = "%s..%s" % (base, tip)

        if files:
            files = ['--'] + files

        if self.type in ('svn', 'perforce'):
            diff_cmd = [self.git, 'diff', '--no-color', '--no-prefix', '-r',
                        '-u', rev_range]
        elif self.type == "git":
            diff_cmd = [self.git, 'diff', '--no-color', '--full-index',
                        '--ignore-submodules', '--no-renames', rev_range]

            if (self.capabilities is not None and
                self.capabilities.has_capability('diffs', 'moved_files')):
                diff_cmd.append('-M')
        else:
            return None

        # By default, don't allow using external diff commands. This prevents
        # things from breaking horribly if someone configures a graphical diff
        # viewer like p4merge or kaleidoscope. This can be overridden by
        # setting GIT_USE_EXT_DIFF = True in ~/.reviewboardrc
        if self.user_config.get('GIT_USE_EXT_DIFF', False):
            diff_cmd.append('--no-ext-diff')

        diff_lines = execute(diff_cmd + files,
                             split_lines=True,
                             with_errors=False,
                             ignore_errors=True,
                             none_on_ignored_error=True)

        if self.type == 'svn':
            return self.make_svn_diff(merge_base, diff_lines)
        elif self.type == 'perforce':
            return self.make_perforce_diff(merge_base, diff_lines)
        else:
            return ''.join(diff_lines)

    def make_svn_diff(self, merge_base, diff_lines):
        """
        Formats the output of git diff such that it's in a form that
        svn diff would generate. This is needed so the SVNTool in Review
        Board can properly parse this diff.
        """
        rev = execute([self.git, "svn", "find-rev", merge_base]).strip()

        if not rev:
            return None

        diff_data = ""
        filename = ""
        newfile = False

        for line in diff_lines:
            if line.startswith("diff "):
                # Grab the filename and then filter this out.
                # This will be in the format of:
                #
                # diff --git a/path/to/file b/path/to/file
                info = line.split(" ")
                diff_data += "Index: %s\n" % info[2]
                diff_data += "=" * 67
                diff_data += "\n"
            elif line.startswith("index "):
                # Filter this out.
                pass
            elif line.strip() == "--- /dev/null":
                # New file
                newfile = True
            elif line.startswith("--- "):
                newfile = False
                diff_data += "--- %s\t(revision %s)\n" % \
                             (line[4:].strip(), rev)
            elif line.startswith("+++ "):
                filename = line[4:].strip()
                if newfile:
                    diff_data += "--- %s\t(revision 0)\n" % filename
                    diff_data += "+++ %s\t(revision 0)\n" % filename
                else:
                    # We already printed the "--- " line.
                    diff_data += "+++ %s\t(working copy)\n" % filename
            elif line.startswith("new file mode"):
                # Filter this out.
                pass
            elif line.startswith("Binary files "):
                # Add the following so that we know binary files were
                # added/changed.
                diff_data += "Cannot display: file marked as a binary type.\n"
                diff_data += "svn:mime-type = application/octet-stream\n"
            else:
                diff_data += line

        return diff_data

    def make_perforce_diff(self, merge_base, diff_lines):
        """Format the output of git diff to look more like perforce's."""
        diff_data = ''
        filename = ''
        p4rev = ''

        # Find which depot changelist we're based on
        log = execute([self.git, 'log', merge_base], ignore_errors=True)

        for line in log:
            m = re.search(r'[rd]epo.-paths = "(.+)": change = (\d+).*\]', log, re.M)

            if m:
                base_path = m.group(1).strip()
                p4rev = m.group(2).strip()
                break
            else:
                # We should really raise an error here, base_path is required
                pass

        for line in diff_lines:
            if line.startswith('diff '):
                # Grab the filename and then filter this out.
                # This will be in the format of:
                #    diff --git a/path/to/file b/path/to/file
                filename = line.split(' ')[2].strip()
            elif (line.startswith('index ') or
                  line.startswith('new file mode ')):
                # Filter this out
                pass
            elif line.startswith('--- '):
                data = execute(
                    ['p4', 'files', base_path + filename + '@' + p4rev],
                    ignore_errors=True)
                m = re.search(r'^%s%s#(\d+).*$' % (re.escape(base_path),
                                                   re.escape(filename)),
                              data, re.M)
                if m:
                    fileVersion = m.group(1).strip()
                else:
                    fileVersion = 1

                diff_data += '--- %s%s\t%s%s#%s\n' % (base_path, filename,
                                                      base_path, filename,
                                                      fileVersion)
            elif line.startswith('+++ '):
                # TODO: add a real timestamp
                diff_data += '+++ %s%s\t%s\n' % (base_path, filename,
                                                 'TIMESTAMP')
            else:
                diff_data += line

        return diff_data

    def has_pending_changes(self):
        """Checks if there are changes waiting to be committed.

        Returns True if the working directory has been modified or if changes
        have been staged in the index, otherwise returns False.
        """
        status = execute(['git', 'status', '--porcelain',
                          '--untracked-files=no'])
        return status != ''

    def apply_patch(self, patch_file, base_path=None, base_dir=None, p=None):
        """Apply the given patch to index.

        This will take the given patch file and apply it to the index,
        scheduling all changes for commit.
        """
        if p:
            cmd = ['git', 'apply', '--index', '-p', p, patch_file]
        else:
            cmd = ['git', 'apply', '--index', patch_file]

        self._execute(cmd)

    def create_commit(self, message, author, files=[], all_files=False):
        modified_message = edit_text(message)

        if all_files:
            execute(['git', 'add', '--all', ':/'])
        elif files:
            execute(['git', 'add'] + files)

        execute(['git', 'commit', '-m', modified_message,
                 '--author="%s <%s>"' % (author.fullname, author.email)])

    def get_current_branch(self):
        """Returns the name of the current branch."""
        return execute([self.git, "rev-parse", "--abbrev-ref", "HEAD"],
                       ignore_errors=True).strip()

########NEW FILE########
__FILENAME__ = mercurial
import logging
import os
import re
import uuid

from urlparse import urlsplit, urlunparse

from rbtools.clients import SCMClient, RepositoryInfo
from rbtools.clients.errors import (InvalidRevisionSpecError,
                                    TooManyRevisionsError)
from rbtools.clients.svn import SVNClient
from rbtools.utils.checks import check_install
from rbtools.utils.process import execute


class MercurialClient(SCMClient):
    """
    A wrapper around the hg Mercurial tool that fetches repository
    information and generates compatible diffs.
    """
    name = 'Mercurial'

    def __init__(self, **kwargs):
        super(MercurialClient, self).__init__(**kwargs)

        self.hgrc = {}
        self._type = 'hg'
        self._remote_path = ()
        self._initted = False
        self._hg_env = {
            'HGPLAIN': '1',
        }

        self._hgext_path = os.path.normpath(os.path.join(
            os.path.dirname(__file__),
            '..', 'helpers', 'hgext.py'))

        # `self._remote_path_candidates` is an ordered set of hgrc
        # paths that are checked if `tracking` option is not given
        # explicitly.  The first candidate found to exist will be used,
        # falling back to `default` (the last member.)
        self._remote_path_candidates = ['reviewboard', 'origin', 'parent',
                                        'default']

    @property
    def hidden_changesets_supported(self):
        """Whether the repository supports hidden changesets.

        Mercurial 1.9 and above support hidden changesets. These are changesets
        that have been hidden from regular repository view. They still exist
        and are accessible, but only if the --hidden command argument is
        specified.

        Since we may encounter hidden changesets (e.g. the user specifies
        hidden changesets as part of the revision spec), we need to be aware
        of hidden changesets.
        """
        if not hasattr(self, '_hidden_changesets_supported'):
            # The choice of command is arbitrary. parents for the initial
            # revision should be fast.
            result = execute(['hg', 'parents', '--hidden', '-r', '0'],
                             ignore_errors=True,
                             with_errors=False,
                             none_on_ignored_error=True)
            self._hidden_changesets_supported = result is not None

        return self._hidden_changesets_supported

    @property
    def hg_root(self):
        """The root of the working directory.

        This will return the root directory of the current repository. If the
        current working directory is not inside a mercurial repository, this
        returns None.
        """
        if not hasattr(self, '_hg_root'):
            root = execute(['hg', 'root'], env=self._hg_env,
                           ignore_errors=True)

            if not root.startswith('abort:'):
                self._hg_root = root.strip()
            else:
                self._hg_root = None

        return self._hg_root

    def _init(self):
        """Initialize the client."""
        if self._initted or not self.hg_root:
            return

        self._load_hgrc()

        svn_info = execute(["hg", "svn", "info"], ignore_errors=True)
        if (not svn_info.startswith('abort:') and
                not svn_info.startswith("hg: unknown command") and
                not svn_info.lower().startswith('not a child of')):
            self._type = 'svn'
            self._svn_info = svn_info
        else:
            self._type = 'hg'

            for candidate in self._remote_path_candidates:
                rc_key = 'paths.%s' % candidate

                if rc_key in self.hgrc:
                    self._remote_path = (candidate, self.hgrc[rc_key])
                    logging.debug('Using candidate path %r: %r' %
                                  self._remote_path)
                    break

        self._initted = True

    def get_repository_info(self):
        if not check_install(['hg', '--help']):
            logging.debug('Unable to execute "hg --help": skipping Mercurial')
            return None

        self._init()

        if not self.hg_root:
            # hg aborted => no mercurial repository here.
            return None

        if self._type == 'svn':
            return self._calculate_hgsubversion_repository_info(self._svn_info)
        else:
            path = self.hg_root
            base_path = '/'

            if self._remote_path:
                path = self._remote_path[1]
                base_path = ''

            return RepositoryInfo(path=path, base_path=base_path,
                                  supports_parent_diffs=True)

    def parse_revision_spec(self, revisions=[]):
        """Parses the given revision spec.

        The 'revisions' argument is a list of revisions as specified by the
        user. Items in the list do not necessarily represent a single revision,
        since the user can use SCM-native syntaxes such as "r1..r2" or "r1:r2".
        SCMTool-specific overrides of this method are expected to deal with
        such syntaxes.

        This will return a dictionary with the following keys:
            'base':        A revision to use as the base of the resulting diff.
            'tip':         A revision to use as the tip of the resulting diff.
            'parent_base': (optional) The revision to use as the base of a
                           parent diff.
            'commit_id':   (optional) The ID of the single commit being posted,
                           if not using a range.

        These will be used to generate the diffs to upload to Review Board (or
        print). The diff for review will include the changes in (base, tip],
        and the parent diff (if necessary) will include (parent, base].

        If zero revisions are passed in, this will return the outgoing changes
        from the parent of the working directory.

        If a single revision is passed in, this will return the parent of that
        revision for 'base' and the passed-in revision for 'tip'. This will
        result in generating a diff for the changeset specified.

        If two revisions are passed in, they will be used for the 'base'
        and 'tip' revisions, respectively.

        In all cases, a parent base will be calculated automatically from
        changesets not present on the remote.
        """
        self._init()

        n_revisions = len(revisions)

        if n_revisions == 1:
            # If there's a single revision, try splitting it based on hg's
            # revision range syntax (either :: or ..). If this splits, then
            # it's handled as two revisions below.
            revisions = re.split(r'\.\.|::', revisions[0])
            n_revisions = len(revisions)

        result = {}
        if n_revisions == 0:
            # No revisions: Find the outgoing changes. Only consider the
            # working copy revision and ancestors because that makes sense.
            # If a user wishes to include other changesets, they can run
            # `hg up` or specify explicit revisions as command arguments.
            if self._type == 'svn':
                result['base'] = self._get_parent_for_hgsubversion()
                result['tip'] = '.'
            else:
                # Ideally, generating a diff for outgoing changes would be as
                # simple as just running `hg outgoing --patch <remote>`, but
                # there are a couple problems with this. For one, the
                # server-side diff parser isn't equipped to filter out diff
                # headers such as "comparing with..." and
                # "changeset: <rev>:<hash>". Another problem is that the output
                # of `hg outgoing` potentially includes changesets across
                # multiple branches.
                #
                # In order to provide the most accurate comparison between
                # one's local clone and a given remote (something akin to git's
                # diff command syntax `git diff <treeish>..<treeish>`), we have
                # to do the following:
                #
                # - Get the name of the current branch
                # - Get a list of outgoing changesets, specifying a custom
                #   format
                # - Filter outgoing changesets by the current branch name
                # - Get the "top" and "bottom" outgoing changesets
                #
                # These changesets are then used as arguments to
                # `hg diff -r <rev> -r <rev>`.
                #
                # Future modifications may need to be made to account for odd
                # cases like having multiple diverged branches which share
                # partial history--or we can just punish developers for doing
                # such nonsense :)
                outgoing = \
                    self._get_bottom_and_top_outgoing_revs_for_remote(rev='.')
                if outgoing[0] is None or outgoing[1] is None:
                    raise InvalidRevisionSpecError(
                        'There are no outgoing changes')
                result['base'] = self._identify_revision(outgoing[0])
                result['tip'] = self._identify_revision(outgoing[1])
                result['commit_id'] = result['tip']

            if self.options.parent_branch:
                result['parent_base'] = result['base']
                result['base'] = self._identify_revision(
                    self.options.parent_branch)
        elif n_revisions == 1:
            # One revision: Use the given revision for tip, and find its parent
            # for base.
            result['tip'] = self._identify_revision(revisions[0])
            result['commit_id'] = result['tip']
            result['base'] = self._execute(
                ['hg', 'parents', '--hidden', '-r', result['tip'],
                 '--template', '{node|short}']).split()[0]
        elif n_revisions == 2:
            # Two revisions: Just use the given revisions
            result['base'] = self._identify_revision(revisions[0])
            result['tip'] = self._identify_revision(revisions[1])
        else:
            raise TooManyRevisionsError

        if 'base' not in result or 'tip' not in result:
            raise InvalidRevisionSpecError(
                '"%s" does not appear to be a valid revision spec' % revisions)

        if self._type == 'hg' and 'parent_base' not in result:
            # If there are missing changesets between base and the remote, we
            # need to generate a parent diff.
            outgoing = self._get_outgoing_changesets(self._get_remote_branch(),
                                                 rev=result['base'])

            logging.debug('%d outgoing changesets between remote and base.',
                          len(outgoing))

            if not outgoing:
                return result

            result['parent_base'] = self._execute(
                ['hg', 'parents', '--hidden', '-r', outgoing[0][1],
                 '--template', '{node|short}']).split()[0]
            logging.debug('Identified %s as parent base', result['parent_base'])

        return result

    def _identify_revision(self, revision):
        identify = self._execute(
            ['hg', 'identify', '-i', '--hidden', '-r', str(revision)],
            ignore_errors=True, none_on_ignored_error=True)

        if identify is None:
            raise InvalidRevisionSpecError(
                '"%s" does not appear to be a valid revision' % revision)
        else:
            return identify.split()[0]

    def _calculate_hgsubversion_repository_info(self, svn_info):
        def _info(r):
            m = re.search(r, svn_info, re.M)

            if m:
                return urlsplit(m.group(1))
            else:
                return None

        self._type = 'svn'

        root = _info(r'^Repository Root: (.+)$')
        url = _info(r'^URL: (.+)$')

        if not (root and url):
            return None

        scheme, netloc, path, _, _ = root
        root = urlunparse([scheme, root.netloc.split("@")[-1], path,
                           "", "", ""])
        base_path = url.path[len(path):]

        return RepositoryInfo(path=root, base_path=base_path,
                              supports_parent_diffs=True)


    def _load_hgrc(self):
        for line in execute(['hg', 'showconfig'], split_lines=True):
            line = line.split('=', 1)
            if len(line) == 2:
                key, value = line
            else:
                key = line[0]
                value = ''

            self.hgrc[key] = value.strip()

    def get_raw_commit_message(self, revisions):
        """
        Extracts all descriptions in the given revision range and concatenates
        them, most recent ones going first.
        """
        rev1 = revisions['base']
        rev2 = revisions['tip']

        delim = str(uuid.uuid1())
        descs = self._execute([
            'hg', 'log', '--hidden', '-r', '%s::%s' % (rev1, rev2),
            '--template', '{desc}%s' % delim], env=self._hg_env)
        # This initial element in the base changeset, which we don't
        # care about. The last element is always empty due to the string
        # ending with <delim>.
        descs = descs.split(delim)[1:-1]

        return '\n\n'.join([desc.strip() for desc in descs])

    def diff(self, revisions, files=[], extra_args=[]):
        """
        Performs a diff across all modified files in a Mercurial repository.
        """
        self._init()

        diff_cmd = ['hg', 'diff', '--hidden']

        if self._type == 'svn':
            diff_cmd.append('--svn')

        diff_cmd += files

        diff = self._execute(
            diff_cmd + ['-r', revisions['base'], '-r', revisions['tip']],
            env=self._hg_env)

        if 'parent_base' in revisions:
            base_commit_id = revisions['parent_base']
            parent_diff = self._execute(
                diff_cmd + ['-r', base_commit_id, '-r', revisions['base']],
                env=self._hg_env)
        else:
            base_commit_id = revisions['base']
            parent_diff = None

        return {
            'diff': diff,
            'parent_diff': parent_diff,
            'commit_id': revisions.get('commit_id'),
            'base_commit_id': base_commit_id,
        }

    def _get_parent_for_hgsubversion(self):
        """Returns the parent Subversion branch.

        Returns the parent branch defined in the command options if it exists,
        otherwise returns the parent Subversion branch of the current
        repository.
        """
        return (getattr(self.options, 'tracking', None) or
                execute(['hg', 'parent', '--svn', '--template',
                        '{node}\n']).strip())

    def _get_remote_branch(self):
        """Returns the remote branch assoicated with this repository.

        If the remote branch is not defined, the parent branch of the
        repository is returned.
        """
        remote = self._remote_path[0]
        tracking = getattr(self.options, 'tracking', None)

        if not remote and tracking:
            remote = tracking

        return remote

    def _get_current_branch(self):
        """Returns the current branch of this repository."""
        return execute(['hg', 'branch'], env=self._hg_env).strip()

    def _get_bottom_and_top_outgoing_revs_for_remote(self, rev=None):
        """Returns the bottom and top outgoing revisions.

        Returns the bottom and top outgoing revisions for the changesets
        between the current branch and the remote branch.
        """
        remote = self._get_remote_branch()
        current_branch = self._get_current_branch()

        outgoing = [o for o in self._get_outgoing_changesets(remote, rev=rev)
                    if current_branch == o[2]]

        if outgoing:
            top_rev, bottom_rev = \
                self._get_top_and_bottom_outgoing_revs(outgoing)
        else:
            top_rev = None
            bottom_rev = None

        return bottom_rev, top_rev

    def _get_outgoing_changesets(self, remote, rev=None):
        """
        Return the outgoing changesets between us and a remote.

        This will return a list of tuples of (rev, node, branch) for
        each outgoing changeset. The list will be sorted in revision order.

        If rev is specified, we will limit the changesets to ancestors of
        the specified revision. Otherwise, all changesets not in the remote
        will be returned.
        """

        outgoing_changesets = []
        args = ['hg', '-q', 'outgoing', '--template',
                "{rev}\\t{node|short}\\t{branch}\\n",
                remote]
        if rev:
            args.extend(['-r', rev])

        # We must handle the special case where there are no outgoing commits
        # as mercurial has a non-zero return value in this case.
        raw_outgoing = execute(args,
                               env=self._hg_env,
                               extra_ignore_errors=(1,))

        for line in raw_outgoing.splitlines():
            if not line:
                continue

            # Ignore warning messages that hg might put in, such as
            # "warning: certificate for foo can't be verified (Python too old)"
            if line.startswith('warning: '):
                continue

            rev, node, branch = [f.strip() for f in line.split('\t')]
            branch = branch or 'default'

            if not rev.isdigit():
                raise Exception('Unexpected output from hg: %s' % line)

            logging.debug('Found outgoing changeset %s:%s' % (rev, node))

            outgoing_changesets.append((int(rev), node, branch))

        return outgoing_changesets

    def _get_top_and_bottom_outgoing_revs(self, outgoing_changesets):
        revs = set(t[0] for t in outgoing_changesets)

        top_rev = max(revs)
        bottom_rev = min(revs)

        for rev, node, branch in reversed(outgoing_changesets):
            parents = execute(
                ["hg", "log", "-r", str(rev), "--template", "{parents}"],
                env=self._hg_env)
            parents = re.split(':[^\s]+\s*', parents)
            parents = [int(p) for p in parents if p != '']

            parents = [p for p in parents if p not in outgoing_changesets]

            if len(parents) > 0:
                bottom_rev = parents[0]
                break
            else:
                bottom_rev = rev - 1

        bottom_rev = max(0, bottom_rev)

        return top_rev, bottom_rev

    def scan_for_server(self, repository_info):
        # Scan first for dot files, since it's faster and will cover the
        # user's $HOME/.reviewboardrc
        server_url = \
            super(MercurialClient, self).scan_for_server(repository_info)

        if not server_url and self.hgrc.get('reviewboard.url'):
            server_url = self.hgrc.get('reviewboard.url').strip()

        if not server_url and self._type == "svn":
            # Try using the reviewboard:url property on the SVN repo, if it
            # exists.
            prop = SVNClient().scan_for_server_property(repository_info)

            if prop:
                return prop

        return server_url

    def _execute(self, cmd, *args, **kwargs):
        if not self.hidden_changesets_supported and '--hidden' in cmd:
            cmd = [p for p in cmd if p != '--hidden']

        # Add our extension which normalizes settings. This is the easiest
        # way to normalize settings since it doesn't require us to chase
        # a tail of diff-related config options.
        cmd.extend([
            '--config',
            'extensions.rbtoolsnormalize=%s' % self._hgext_path
        ])

        return execute(cmd, *args, **kwargs)

########NEW FILE########
__FILENAME__ = perforce
import logging
import marshal
import os
import re
import socket
import stat
import subprocess

from rbtools.clients import SCMClient, RepositoryInfo
from rbtools.clients.errors import (EmptyChangeError,
                                    InvalidRevisionSpecError,
                                    TooManyRevisionsError)
from rbtools.utils.checks import check_gnu_diff, check_install
from rbtools.utils.filesystem import make_tempfile
from rbtools.utils.process import die, execute


class P4Wrapper(object):
    """A wrapper around p4 commands.

    All calls out to p4 go through an instance of this class. It keeps a
    separation between all the standard SCMClient logic and any parsing
    and handling of p4 invocation and results.
    """
    KEYVAL_RE = re.compile('^([^:]+): (.+)$')
    COUNTERS_RE = re.compile('^([^ ]+) = (.+)$')

    def __init__(self, options):
        self.options = options

    def is_supported(self):
        return check_install(['p4', 'help'])

    def counters(self):
        lines = self.run_p4(['counters'], split_lines=True)
        return self._parse_keyval_lines(lines, self.COUNTERS_RE)

    def change(self, changenum, password=None):
        return self.run_p4(['change', '-o', str(changenum)],
                           password=password, ignore_errors=True,
                           none_on_ignored_error=True,
                           marshalled=True)

    def files(self, path):
        return self.run_p4(['files', path], marshalled=True)

    def filelog(self, path):
        return self.run_p4(['filelog', path], marshalled=True)

    def fstat(self, depot_path, fields=[]):
        args = ['fstat']

        if fields:
            args += ['-T', ','.join(fields)]

        args.append(depot_path)

        lines = self.run_p4(args, split_lines=True)
        stat_info = {}

        for line in lines:
            line = line.strip()

            if line.startswith('... '):
                parts = line.split(' ', 2)
                stat_info[parts[1]] = parts[2]

        return stat_info

    def info(self):
        lines = self.run_p4(['info'],
                            ignore_errors=True,
                            split_lines=True)

        return self._parse_keyval_lines(lines)

    def opened(self, changenum):
        return self.run_p4(['opened', '-c', str(changenum)],
                           marshalled=True)

    def print_file(self, depot_path, out_file=None):
        cmd = ['print']

        if out_file:
            cmd += ['-o', out_file]

        cmd += ['-q', depot_path]

        return self.run_p4(cmd)

    def where(self, depot_path):
        return self.run_p4(['where', depot_path], marshalled=True)

    def run_p4(self, p4_args, marshalled=False, password=None,
               ignore_errors=False, *args, **kwargs):
        cmd = ['p4']

        if marshalled:
            cmd += ['-G']

        if getattr(self.options, 'p4_client', None):
            cmd += ['-c', self.options.p4_client]

        if getattr(self.options, 'p4_port', None):
            cmd += ['-p', self.options.p4_port]

        if getattr(self.options, 'p4_passwd', None):
            cmd += ['-P', self.options.p4_passwd]

        cmd += p4_args

        if password is not None:
            cmd += ['-P', password]

        if marshalled:
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
            result = []
            has_error = False

            while 1:
                try:
                    data = marshal.load(p.stdout)
                except EOFError:
                    break
                else:
                    result.append(data)
                    if data.get('code', None) == 'error':
                        has_error = True

            rc = p.wait()

            if not ignore_errors and (rc or has_error):
                for record in result:
                    if 'data' in record:
                        print record['data']
                die('Failed to execute command: %s\n' % (cmd,))

            return result
        else:
            result = execute(cmd, ignore_errors=ignore_errors, *args, **kwargs)

        return result

    def _parse_keyval_lines(self, lines, regex=KEYVAL_RE):
        keyvals = {}

        for line in lines:
            m = regex.match(line)

            if m:
                key = m.groups()[0]
                value = m.groups()[1]
                keyvals[key] = value.strip()

        return keyvals


class PerforceClient(SCMClient):
    """
    A wrapper around the p4 Perforce tool that fetches repository information
    and generates compatible diffs.
    """
    name = 'Perforce'

    supports_diff_extra_args = True

    DATE_RE = re.compile(r'(\w+)\s+(\w+)\s+(\d+)\s+(\d\d:\d\d:\d\d)\s+'
                         '(\d\d\d\d)')
    ENCODED_COUNTER_URL_RE = re.compile('reviewboard.url\.(\S+)')

    REVISION_CURRENT_SYNC = '--rbtools-current-sync'
    REVISION_PENDING_CLN_PREFIX = '--rbtools-pending-cln:'

    def __init__(self, p4_class=P4Wrapper, **kwargs):
        super(PerforceClient, self).__init__(**kwargs)
        self.p4 = p4_class(self.options)

    def get_repository_info(self):
        if not self.p4.is_supported():
            logging.debug('Unable to execute "p4 help": skipping Perforce')
            return None

        p4_info = self.p4.info()

        # For the repository path, we first prefer p4 brokers, then the
        # upstream p4 server. If neither of those are found, just return None.
        repository_path = (p4_info.get('Broker address') or
                           p4_info.get('Server address'))

        if repository_path is None:
            return None

        client_root = p4_info.get('Client root')

        if client_root is None:
            return None

        norm_cwd = os.path.normcase(os.path.realpath(os.getcwd()) +
                                    os.path.sep)
        norm_client_root = os.path.normcase(os.path.realpath(client_root) +
                                            os.path.sep)

        # Don't accept the repository if the current directory is outside the
        # root of the Perforce client.
        if not norm_cwd.startswith(norm_client_root):
            return None

        try:
            parts = repository_path.split(':')
            hostname = None

            if len(parts) == 3 and parts[0] == 'ssl':
                hostname = parts[1]
                port = parts[2]
            elif len(parts) == 2:
                hostname, port = parts

            if not hostname:
                die('Path %s is not a valid Perforce P4PORT' % repository_path)

            info = socket.gethostbyaddr(hostname)

            # Build the list of repository paths we want to tr to look up.
            servers = [hostname]

            if info[0] != hostname:
                servers.append(info[0])

            # If aliases exist for hostname, create a list of alias:port
            # strings for repository_path.
            if info[1]:
                servers += info[1]

            repository_path = ["%s:%s" % (server, port)
                               for server in servers]

            # If there's only one repository path found, then we don't
            # need to do a more expensive lookup of all registered
            # paths. We can look up just this path directly.
            if len(repository_path) == 1:
                repository_path = repository_path[0]
        except (socket.gaierror, socket.herror):
            pass

        server_version = p4_info.get('Server version', None)

        if not server_version:
            return None

        m = re.search(r'[^ ]*/([0-9]+)\.([0-9]+)/[0-9]+ .*$',
                      server_version, re.M)
        if m:
            self.p4d_version = int(m.group(1)), int(m.group(2))
        else:
            # Gracefully bail if we don't get a match
            return None

        # Now that we know it's Perforce, make sure we have GNU diff
        # installed, and error out if we don't.
        check_gnu_diff()

        return RepositoryInfo(path=repository_path, supports_changesets=True)

    def parse_revision_spec(self, revisions=[]):
        """Parses the given revision spec.

        The 'revisions' argument is a list of revisions as specified by the
        user. Items in the list do not necessarily represent a single revision,
        since the user can use SCM-native syntaxes such as "r1..r2" or "r1:r2".
        SCMTool-specific overrides of this method are expected to deal with
        such syntaxes.

        This will return a dictionary with the following keys:
            'base':        A revision to use as the base of the resulting diff.
            'tip':         A revision to use as the tip of the resulting diff.

        These will be used to generate the diffs to upload to Review Board (or
        print). The diff for review will include the changes in (base, tip].

        If zero revisions are passed in, this will return the 'default'
        changelist.

        If a single revision is passed in, this will return the parent of that
        revision for 'base' and the passed-in revision for 'tip'. The result
        may have special internal revisions or prefixes based on whether the
        changeset is submitted, pending, or shelved.

        If two revisions are passed in, they need to both be submitted
        changesets.
        """
        n_revs = len(revisions)

        if n_revs == 0:
            return {
                'base': self.REVISION_CURRENT_SYNC,
                'tip': self.REVISION_PENDING_CLN_PREFIX + 'default',
            }
        elif n_revs == 1:
            # A single specified CLN can be any of submitted, pending, or
            # shelved. These are stored with special prefixes and/or names
            # because the way that we get the contents of the files changes
            # based on which of these is in effect.
            status = self._get_changelist_status(revisions[0])

            # Both pending and shelved changes are treated as "pending",
            # through the same code path. This is because the documentation for
            # 'p4 change' tells a filthy lie, saying that shelved changes will
            # have their status listed as shelved. In fact, when you shelve
            # changes, it sticks the data up on the server, but leaves your
            # working copy intact, and the change is still marked as pending.
            # Even after reverting the working copy, the change won't have its
            # status as "shelved". That said, there's perhaps a way that it
            # could (perhaps from other clients?), so it's still handled in
            # this conditional.
            #
            # The diff routine will first look for opened files in the client,
            # and if that fails, it will then do the diff against the shelved
            # copy.
            if status in ('pending', 'shelved'):
                return {
                    'base': self.REVISION_CURRENT_SYNC,
                    'tip': self.REVISION_PENDING_CLN_PREFIX + revisions[0],
                }
            elif status == 'submitted':
                try:
                    cln = int(revisions[0])

                    return {
                        'base': str(cln - 1),
                        'tip': str(cln),
                    }
                except ValueError:
                    raise InvalidRevisionSpecError(
                        '%s does not appear to be a valid changelist' %
                        revisions[0])
            else:
                raise InvalidRevisionSpecError(
                    '%s does not appear to be a valid changelist' %
                    revisions[0])
        elif n_revs == 2:
            result = {}

            # The base revision must be a submitted CLN
            status = self._get_changelist_status(revisions[0])
            if status == 'submitted':
                result['base'] = revisions[0]
            elif status in ('pending', 'shelved'):
                raise InvalidRevisionSpecError(
                    '%s cannot be used as the base CLN for a diff because '
                    'it is %s.' % (revisions[0], status))
            else:
                raise InvalidRevisionSpecError(
                    '%s does not appear to be a valid changelist' %
                    revisions[0])

            # Tip revision can be any of submitted, pending, or shelved CLNs
            status = self._get_changelist_status(revisions[1])
            if status == 'submitted':
                result['tip'] = revisions[1]
            elif status in ('pending', 'shelved'):
                raise InvalidRevisionSpecError(
                    '%s cannot be used for a revision range diff because it '
                    'is %s' % (revisions[1], status))
            else:
                raise InvalidRevisionSpecError(
                    '%s does not appear to be a valid changelist' %
                    revisions[1])

            return result
        else:
            raise TooManyRevisionsError

    def _get_changelist_status(self, changelist):
        if changelist == 'default':
            return 'pending'
        else:
            change = self.p4.change(changelist)
            if len(change) == 1 and 'Status' in change[0]:
                return change[0]['Status']

        return None

    def scan_for_server(self, repository_info):
        # Scan first for dot files, since it's faster and will cover the
        # user's $HOME/.reviewboardrc
        server_url = \
            super(PerforceClient, self).scan_for_server(repository_info)

        if server_url:
            return server_url

        return self.scan_for_server_counter(repository_info)

    def scan_for_server_counter(self, repository_info):
        """
        Checks the Perforce counters to see if the Review Board server's url
        is specified. Since Perforce only started supporting non-numeric
        counter values in server version 2008.1, we support both a normal
        counter 'reviewboard.url' with a string value and embedding the url in
        a counter name like 'reviewboard.url.http:||reviewboard.example.com'.
        Note that forward slashes aren't allowed in counter names, so
        pipe ('|') characters should be used. These should be safe because they
        should not be used unencoded in urls.
        """
        counters = self.p4.counters()

        # Try for a "reviewboard.url" counter first.
        url = counters.get('reviewboard.url', None)

        if url:
            return url

        # Next try for a counter of the form:
        # reviewboard_url.http:||reviewboard.example.com
        for key, value in counters.iteritems():
            m = self.ENCODED_COUNTER_URL_RE.match(key)

            if m:
                return m.group(1).replace('|', '/')

        return None

    def diff(self, revisions, files=[], extra_args=[]):
        """
        Goes through the hard work of generating a diff on Perforce in order
        to take into account adds/deletes and to provide the necessary
        revision information.
        """
        if not revisions:
            # The "path posting" is still interesting enough to keep around. If
            # the given arguments don't parse as valid changelists, fall back
            # on that behavior.
            return self._path_diff(extra_args)

        # Support both //depot/... paths and local filenames. For the moment,
        # this does *not* support any of perforce's traversal literals like ...
        depot_include_files = []
        local_include_files = []
        for filename in files:
            if filename.startswith('//'):
                depot_include_files.append(filename)
            else:
                # The way we determine files to include or not is via
                # 'p4 where', which gives us absolute paths.
                local_include_files.append(
                    os.path.realpath(os.path.abspath(filename)))

        base = revisions['base']
        tip = revisions['tip']

        cl_is_pending = tip.startswith(self.REVISION_PENDING_CLN_PREFIX)
        cl_is_shelved = False

        if not cl_is_pending:
            # Submitted changes are handled by a different method
            logging.info('Generating diff for range of submitted changes: %s '
                         'to %s',
                         base, tip)
            return self._compute_range_changes(
                base, tip, depot_include_files, local_include_files)

        # Strip off the prefix
        tip = tip[len(self.REVISION_PENDING_CLN_PREFIX):]

        # Try to get the files out of the working directory first. If that
        # doesn't work, look at shelved files.
        opened_files = self.p4.opened(tip)
        if not opened_files:
            opened_files = self.p4.files('//...@=%s' % tip)
            cl_is_shelved = True

        if not opened_files:
            raise EmptyChangeError

        if cl_is_shelved:
            logging.info('Generating diff for shelved changeset %s' % tip)
        else:
            logging.info('Generating diff for pending changeset %s' % tip)

        diff_lines = []

        action_mapping = {
            'edit': 'M',
            'integrate': 'M',
            'add': 'A',
            'branch': 'A',
            'delete': 'D',
        }

        # XXX: Theoretically, shelved files should handle moves just fine--you
        # can shelve and unshelve changes containing moves. Unfortunately,
        # there doesn't seem to be any way to match up the added and removed
        # files when the changeset is shelved, because none of the usual
        # methods (fstat, filelog) provide the source move information when the
        # changeset is shelved.
        if self._supports_moves() and not cl_is_shelved:
            action_mapping['move/add'] = 'MV-a'
            action_mapping['move/delete'] = 'MV'
        else:
            # The Review Board server doesn't support moved files for
            # perforce--create a diff that shows moved files as adds and
            # deletes.
            action_mapping['move/add'] = 'A'
            action_mapping['move/delete'] = 'D'

        for f in opened_files:
            depot_file = f['depotFile']
            local_file = self._depot_to_local(depot_file)
            new_depot_file = ''
            try:
                base_revision = int(f['rev'])
            except ValueError:
                # For actions like deletes, there won't be any "current
                # revision". Just pass through whatever was there before.
                base_revision = f['rev']
            action = f['action']

            if ((depot_include_files and
                 depot_file not in depot_include_files) or
                (local_include_files and
                 local_file not in local_include_files)):
                continue

            old_file = ''
            new_file = ''

            logging.debug('Processing %s of %s', action, depot_file)

            try:
                changetype_short = action_mapping[action]
            except KeyError:
                die('Unsupported action type "%s" for %s' % (action, depot_file))

            if changetype_short == 'M':
                try:
                    old_file, new_file = self._extract_edit_files(
                        depot_file, local_file, base_revision, tip,
                        cl_is_shelved, False)
                except ValueError, e:
                    logging.warning('Skipping file %s: %s', depot_file, e)
                    continue
            elif changetype_short == 'A':
                # Perforce has a charming quirk where the revision listed for
                # a file is '1' in both the first submitted revision, as well
                # as before it's added. On the Review Board side, when we parse
                # the diff, we'll check to see if that revision exists, but
                # that only works for pending changes. If the change is shelved
                # or submitted, revision 1 will exist, which causes the
                # displayed diff to contain revision 1 twice.
                #
                # Setting the revision in the diff file to be '0' will avoid
                # problems with patches that add files.
                base_revision = 0

                try:
                    old_file, new_file = self._extract_add_files(
                        depot_file, local_file, tip, cl_is_shelved,
                        cl_is_pending)
                except ValueError, e:
                    logging.warning('Skipping file %s: %s', depot_file, e)
                    continue

                if os.path.islink(new_file):
                    logging.warning('Skipping symlink %s', new_file)
                    continue
            elif changetype_short == 'D':
                try:
                    old_file, new_file = self._extract_delete_files(
                        depot_file, base_revision)
                except ValueError, e:
                    logging.warning('Skipping file %s#%s: %s', depot_file, e)
                    continue
            elif changetype_short == 'MV-a':
                # The server supports move information. We ignore this
                # particular entry, and handle the moves within the equivalent
                # 'move/delete' entry.
                continue
            elif changetype_short == 'MV':
                try:
                    old_file, new_file, new_depot_file = \
                        self._extract_move_files(
                            depot_file, tip, base_revision, cl_is_shelved)
                except ValueError, e:
                    logging.warning('Skipping file %s: %s', depot_file, e)
                    continue

            dl = self._do_diff(old_file, new_file, depot_file, base_revision,
                               new_depot_file, changetype_short,
                               ignore_unmodified=True)
            diff_lines += dl

        # For pending changesets, report the change number to the reviewboard
        # server when posting. This is used to extract the changeset
        # description server-side. Ideally we'd change this to remove the
        # server-side implementation and just implement --guess-summary and
        # --guess-description, but that would create a lot of unhappy users.
        if cl_is_pending and tip != 'default':
            changenum = str(tip)
        else:
            changenum = None

        return {
            'diff': ''.join(diff_lines),
            'changenum': changenum,
        }

    def _compute_range_changes(self, base, tip, depot_include_files,
                               local_include_files):
        """Compute the changes across files given a revision range.

        This will look at the history of all changes within the given range and
        compute the full set of changes contained therein. Just looking at the
        two trees isn't enough, since files may have moved around and we want
        to include that information.
        """
        # Start by looking at the filelog to get a history of all the changes
        # within the changeset range. This processing step is done because in
        # marshalled mode, the filelog doesn't sort its entries at all, and can
        # also include duplicate information, especially when files have moved
        # around.
        changesets = {}

        # We expect to generate a diff for (base, tip], but filelog gives us
        # [base, tip]. Increment the base to avoid this.
        real_base = str(int(base) + 1)

        for file_entry in self.p4.filelog('//...@%s,%s' % (real_base, tip)):
            cid = 0
            while True:
                change_key = 'change%d' % cid
                if change_key not in file_entry:
                    break

                action = file_entry['action%d' % cid]
                depot_file = file_entry['depotFile']

                try:
                    cln = int(file_entry[change_key])
                except ValueError:
                    logging.warning('Skipping file %s: unable to parse '
                                    'change number "%s"',
                                    depot_file, file_entry[change_key])
                    break

                if action not in ('edit', 'integrate', 'add', 'delete',
                                  'move/add', 'move/delete'):
                    raise Exception('Unsupported action type "%s" for %s' %
                                    (action, depot_file))

                if action == 'integrate':
                    action = 'edit'
                elif action == 'branch':
                    action = 'add'

                try:
                    rev_key = 'rev%d' % cid
                    rev = int(file_entry[rev_key])
                except ValueError:
                    logging.warning('Skipping file %s: unable to parse '
                                    'revision number "%s"',
                                    depot_file, file_entry[rev_key])
                    break

                change = {
                    'rev': rev,
                    'action': action,
                }

                if action == 'move/add':
                    change['oldFilename'] = file_entry['file0,%d' % cid]
                elif action == 'move/delete':
                    change['newFilename'] = file_entry['file1,%d' % cid]

                cid += 1

                changesets.setdefault(cln, {})[depot_file] = change

        # Now run through the changesets in order and compute a change journal
        # for each file.
        files = []
        for cln in sorted(changesets.keys()):
            changeset = changesets[cln]
            for depot_file, change in changeset.iteritems():
                action = change['action']

                # Moves will be handled in the 'move/delete' entry
                if action == 'move/add':
                    continue

                file_entry = None
                for f in files:
                    if f['depotFile'] == depot_file:
                        file_entry = f
                        break

                if file_entry is None:
                    file_entry = {
                        'initialDepotFile': depot_file,
                        'initialRev': change['rev'],
                        'newFile': action == 'add',
                        'rev': change['rev'],
                        'action': 'none',
                    }
                    files.append(file_entry)

                self._accumulate_range_change(file_entry, change)

        if not files:
            raise EmptyChangeError

        # Now generate the diff
        supports_moves = self._supports_moves()
        diff_lines = []
        for f in files:
            action = f['action']
            depot_file = f['depotFile']
            local_file = self._depot_to_local(depot_file)
            rev = f['rev']
            initial_depot_file = f['initialDepotFile']
            initial_rev = f['initialRev']

            if ((depot_include_files and
                 depot_file not in depot_include_files) or
                (local_include_files and
                 local_file not in local_include_files)):
                continue

            if action == 'add':
                try:
                    old_file, new_file = self._extract_add_files(
                        depot_file, local_file, rev, False, False)
                except ValueError, e:
                    logging.warning('Skipping file %s: %s', depot_file, e)
                    continue

                diff_lines += self._do_diff(
                    old_file, new_file, depot_file, 0, '', 'A',
                    ignore_unmodified=True)
            elif action == 'delete':
                try:
                    old_file, new_file = self._extract_delete_files(
                        initial_depot_file, initial_rev)
                except ValueError:
                    logging.warning('Skipping file %s: %s', depot_file, e)
                    continue

                diff_lines += self._do_diff(
                    old_file, new_file, initial_depot_file, initial_rev,
                    depot_file, 'D', ignore_unmodified=True)
            elif action == 'edit':
                try:
                    old_file, new_file = self._extract_edit_files(
                        depot_file, local_file, initial_rev, rev, False, True)
                except ValueError:
                    logging.warning('Skipping file %s: %s', depot_file, e)
                    continue

                diff_lines += self._do_diff(
                    old_file, new_file, initial_depot_file, initial_rev,
                    depot_file, 'M', ignore_unmodified=True)
            elif action == 'move':
                try:
                    old_file_a, new_file_a = self._extract_add_files(
                        depot_file, local_file, rev, False, False)
                    old_file_b, new_file_b = self._extract_delete_files(
                        initial_depot_file, initial_rev)
                except ValueError:
                    logging.warning('Skipping file %s: %s', depot_file, e)
                    continue

                if supports_moves:
                    # Show the change as a move
                    diff_lines += self._do_diff(
                        old_file_a, new_file_b, initial_depot_file,
                        initial_rev, depot_file, 'MV', ignore_unmodified=True)
                else:
                    # Show the change as add and delete
                    diff_lines += self._do_diff(
                        old_file_a, new_file_a, depot_file, 0, '', 'A',
                        ignore_unmodified=True)
                    diff_lines += self._do_diff(
                        old_file_b, new_file_b, initial_depot_file, initial_rev,
                        depot_file, 'D', ignore_unmodified=True)
            elif action == 'skip':
                continue
            else:
                # We should never get here. The results of
                # self._accumulate_range_change should never be anything other
                # than add, delete, move, or edit.
                assert False

        return {
            'diff': ''.join(diff_lines)
        }

    def _accumulate_range_change(self, file_entry, change):
        """Compute the effects of a given change on a given file"""
        old_action = file_entry['action']
        current_action = change['action']

        if old_action == 'none':
            # This is the first entry for this file.
            new_action = current_action
            file_entry['depotFile'] = file_entry['initialDepotFile']

            # If the first action was an edit, then the initial revision
            # (that we'll use to generate the diff) is n-1
            if current_action == 'edit':
                file_entry['initialRev'] -= 1
        elif current_action == 'add':
            # If we're adding a file that existed in the base changeset, it
            # means it was previously deleted and then added back. We
            # therefore want the operation to look like an edit. If it
            # didn't exist, then we added, deleted, and are now adding
            # again.
            if old_action == 'skip':
                new_action = 'add'
            else:
                new_action = 'edit'
        elif current_action == 'edit':
            # Edits don't affect the previous type of change
            # (edit+edit=edit, move+edit=move, add+edit=add).
            new_action = old_action
        elif current_action == 'delete':
            # If we're deleting a file which did not exist in the base
            # changeset, then we want to just skip it entirely (since it
            # means it's been added and then deleted). Otherwise, it's a
            # real delete.
            if file_entry['newFile']:
                new_action = 'skip'
            else:
                new_action = 'delete'
        elif current_action == 'move/delete':
            new_action = 'move'
            file_entry['depotFile'] = change['newFilename']

        file_entry['rev'] = change['rev']
        file_entry['action'] = new_action

    def _extract_edit_files(self, depot_file, local_file, rev_a, rev_b,
                            cl_is_shelved, cl_is_submitted):
        """Extract the 'old' and 'new' files for an edit operation.

        Returns a tuple of (old filename, new filename). This can raise a
        ValueError if the extraction fails.
        """
        # Get the old version out of perforce
        old_filename = make_tempfile()
        self._write_file('%s#%s' % (depot_file, rev_a), old_filename)

        if cl_is_shelved:
            new_filename = make_tempfile()
            self._write_file('%s@=%s' % (depot_file, rev_b), new_filename)
        elif cl_is_submitted:
            new_filename = make_tempfile()
            self._write_file('%s#%s' % (depot_file, rev_b), new_filename)
        else:
            # Just reference the file within the client view
            new_filename = local_file

        return old_filename, new_filename

    def _extract_add_files(self, depot_file, local_file, revision,
                           cl_is_shelved, cl_is_pending):
        """Extract the 'old' and 'new' files for an add operation.

        Returns a tuple of (old filename, new filename). This can raise a
        ValueError if the extraction fails.
        """
        # Make an empty tempfile for the old file
        old_filename = make_tempfile()

        if cl_is_shelved:
            new_filename = make_tempfile()
            self._write_file('%s@=%s' % (depot_file, revision), new_filename)
        elif cl_is_pending:
            # Just reference the file within the client view
            new_filename = local_file
        else:
            new_filename = make_tempfile()
            self._write_file('%s#%s' % (depot_file, revision), new_filename)

        return old_filename, new_filename

    def _extract_delete_files(self, depot_file, revision):
        """Extract the 'old' and 'new' files for a delete operation.

        Returns a tuple of (old filename, new filename). This can raise a
        ValueError if extraction fails.
        """
        # Get the old version out of perforce
        old_filename = make_tempfile()
        self._write_file('%s#%s' % (depot_file, revision), old_filename)

        # Make an empty tempfile for the new file
        new_filename = make_tempfile()

        return old_filename, new_filename

    def _extract_move_files(self, old_depot_file, tip, base_revision,
                            cl_is_shelved):
        """Extract the 'old' and 'new' files for a move operation.

        Returns a tuple of (old filename, new filename, new depot path). This
        can raise a ValueError if extraction fails.
        """
        # XXX: fstat *ought* to work, but perforce doesn't supply the movedFile
        # field in fstat (or apparently anywhere else) when a change is
        # shelved. For now, _diff_pending will avoid calling this method at all
        # for shelved changes, and instead treat them as deletes and adds.
        assert not cl_is_shelved

        # if cl_is_shelved:
        #     fstat_path = '%s@=%s' % (depot_file, tip)
        # else:
        fstat_path = old_depot_file

        stat_info = self.p4.fstat(fstat_path,
                                  ['clientFile', 'movedFile'])
        if 'clientFile' not in stat_info or 'movedFile' not in stat_info:
            raise ValueError('Unable to get moved file information')

        old_filename = make_tempfile()
        self._write_file('%s#%s' % (old_depot_file, base_revision),
                         old_filename)

        # if cl_is_shelved:
        #     fstat_path = '%s@=%s' % (stat_info['movedFile'], tip)
        # else:
        fstat_path = stat_info['movedFile']

        stat_info = self.p4.fstat(fstat_path,
                                  ['clientFile', 'depotFile'])
        if 'clientFile' not in stat_info or 'depotFile' not in stat_info:
            raise ValueError('Unable to get moved file information')

        # Grab the new depot path (to include in the diff index)
        new_depot_file = stat_info['depotFile']

        # Reference the new file directly in the client view
        new_filename = stat_info['clientFile']

        return old_filename, new_filename, new_depot_file

    def _path_diff(self, args):
        """
        Process a path-style diff. This allows people to post individual files
        in various ways.

        Multiple paths may be specified in `args`.  The path styles supported
        are:

        //path/to/file
        Upload file as a "new" file.

        //path/to/dir/...
        Upload all files as "new" files.

        //path/to/file[@#]rev
        Upload file from that rev as a "new" file.

        //path/to/file[@#]rev,[@#]rev
        Upload a diff between revs.

        //path/to/dir/...[@#]rev,[@#]rev
        Upload a diff of all files between revs in that directory.
        """
        r_revision_range = re.compile(r'^(?P<path>//[^@#]+)' +
                                      r'(?P<revision1>[#@][^,]+)?' +
                                      r'(?P<revision2>,[#@][^,]+)?$')

        empty_filename = make_tempfile()
        tmp_diff_from_filename = make_tempfile()
        tmp_diff_to_filename = make_tempfile()

        diff_lines = []

        for path in args:
            m = r_revision_range.match(path)

            if not m:
                die('Path %r does not match a valid Perforce path.' % (path,))
            revision1 = m.group('revision1')
            revision2 = m.group('revision2')
            first_rev_path = m.group('path')

            if revision1:
                first_rev_path += revision1
            records = self.p4.files(first_rev_path)

            # Make a map for convenience.
            files = {}

            # Records are:
            # 'rev': '1'
            # 'func': '...'
            # 'time': '1214418871'
            # 'action': 'edit'
            # 'type': 'ktext'
            # 'depotFile': '...'
            # 'change': '123456'
            for record in records:
                if record['action'] not in ('delete', 'move/delete'):
                    if revision2:
                        files[record['depotFile']] = [record, None]
                    else:
                        files[record['depotFile']] = [None, record]

            if revision2:
                # [1:] to skip the comma.
                second_rev_path = m.group('path') + revision2[1:]
                records = self.p4.files(second_rev_path)
                for record in records:
                    if record['action'] not in ('delete', 'move/delete'):
                        try:
                            m = files[record['depotFile']]
                            m[1] = record
                        except KeyError:
                            files[record['depotFile']] = [None, record]

            old_file = new_file = empty_filename
            changetype_short = None

            for depot_path, (first_record, second_record) in files.items():
                old_file = new_file = empty_filename
                if first_record is None:
                    new_path = '%s#%s' % (depot_path, second_record['rev'])
                    self._write_file(new_path, tmp_diff_to_filename)
                    new_file = tmp_diff_to_filename
                    changetype_short = 'A'
                    base_revision = 0
                elif second_record is None:
                    old_path = '%s#%s' % (depot_path, first_record['rev'])
                    self._write_file(old_path, tmp_diff_from_filename)
                    old_file = tmp_diff_from_filename
                    changetype_short = 'D'
                    base_revision = int(first_record['rev'])
                elif first_record['rev'] == second_record['rev']:
                    # We when we know the revisions are the same, we don't need
                    # to do any diffing. This speeds up large revision-range
                    # diffs quite a bit.
                    continue
                else:
                    old_path = '%s#%s' % (depot_path, first_record['rev'])
                    new_path = '%s#%s' % (depot_path, second_record['rev'])
                    self._write_file(old_path, tmp_diff_from_filename)
                    self._write_file(new_path, tmp_diff_to_filename)
                    new_file = tmp_diff_to_filename
                    old_file = tmp_diff_from_filename
                    changetype_short = 'M'
                    base_revision = int(first_record['rev'])

                # TODO: We're passing new_depot_file='' here just to make
                # things work like they did before the moved file change was
                # added (58ccae27). This section of code needs to be updated
                # to properly work with moved files.
                dl = self._do_diff(old_file, new_file, depot_path,
                                   base_revision, '', changetype_short,
                                   ignore_unmodified=True)
                diff_lines += dl

        os.unlink(empty_filename)
        os.unlink(tmp_diff_from_filename)
        os.unlink(tmp_diff_to_filename)

        return {
            'diff': ''.join(diff_lines),
        }

    def _do_diff(self, old_file, new_file, depot_file, base_revision,
                 new_depot_file, changetype_short, ignore_unmodified=False):
        """
        Do the work of producing a diff for Perforce.

        old_file - The absolute path to the "old" file.
        new_file - The absolute path to the "new" file.
        depot_file - The depot path in Perforce for this file.
        base_revision - The base perforce revision number of the old file as
            an integer.
        new_depot_file - Location of the new file. Only used for moved files.
        changetype_short - The change type as a short string.
        ignore_unmodified - If True, will return an empty list if the file
            is not changed.

        Returns a list of strings of diff lines.
        """
        if hasattr(os, 'uname') and os.uname()[0] == 'SunOS':
            diff_cmd = ["gdiff", "-urNp", old_file, new_file]
        else:
            diff_cmd = ["diff", "-urNp", old_file, new_file]

        # Diff returns "1" if differences were found.
        dl = execute(diff_cmd, extra_ignore_errors=(1, 2),
                     translate_newlines=False)

        # If the input file has ^M characters at end of line, lets ignore them.
        dl = dl.replace('\r\r\n', '\r\n')
        dl = dl.splitlines(True)

        cwd = os.getcwd()

        if depot_file.startswith(cwd):
            local_path = depot_file[len(cwd) + 1:]
        else:
            local_path = depot_file

        if changetype_short == 'MV':
            is_move = True

            if new_depot_file.startswith(cwd):
                new_local_path = new_depot_file[len(cwd) + 1:]
            else:
                new_local_path = new_depot_file
        else:
            is_move = False
            new_local_path = local_path

        # Special handling for the output of the diff tool on binary files:
        #     diff outputs "Files a and b differ"
        # and the code below expects the output to start with
        #     "Binary files "
        if (len(dl) == 1 and
            dl[0].startswith('Files %s and %s differ' %
                            (old_file, new_file))):
            dl = ['Binary files %s and %s differ\n' % (old_file, new_file)]

        if dl == [] or dl[0].startswith("Binary files "):
            if dl == [] and not is_move:
                if ignore_unmodified:
                    return []
                else:
                    print "Warning: %s in your changeset is unmodified" % \
                          local_path

            dl.insert(0, "==== %s#%s ==%s== %s ====\n" %
                      (depot_file, base_revision, changetype_short,
                       new_local_path))
            dl.append('\n')
        elif len(dl) > 1:
            m = re.search(r'(\d\d\d\d-\d\d-\d\d \d\d:\d\d:\d\d)', dl[1])
            if m:
                timestamp = m.group(1)
            else:
                # Thu Sep  3 11:24:48 2007
                m = self.DATE_RE.search(dl[1])
                if not m:
                    die("Unable to parse diff header: %s" % dl[1])

                month_map = {
                    "Jan": "01",
                    "Feb": "02",
                    "Mar": "03",
                    "Apr": "04",
                    "May": "05",
                    "Jun": "06",
                    "Jul": "07",
                    "Aug": "08",
                    "Sep": "09",
                    "Oct": "10",
                    "Nov": "11",
                    "Dec": "12",
                }
                month = month_map[m.group(2)]
                day = m.group(3)
                timestamp = m.group(4)
                year = m.group(5)

                timestamp = "%s-%s-%s %s" % (year, month, day, timestamp)

            dl[0] = "--- %s\t%s#%s\n" % (local_path, depot_file, base_revision)
            dl[1] = "+++ %s\t%s\n" % (new_local_path, timestamp)

            if is_move:
                dl.insert(0, 'Moved to: %s\n' % new_depot_file)
                dl.insert(0, 'Moved from: %s\n' % depot_file)

            # Not everybody has files that end in a newline (ugh). This ensures
            # that the resulting diff file isn't broken.
            if dl[-1][-1] != '\n':
                dl.append('\n')
        else:
            die("ERROR, no valid diffs: %s" % dl[0])

        return dl

    def _write_file(self, depot_path, tmpfile):
        """
        Grabs a file from Perforce and writes it to a temp file. p4 print sets
        the file readonly and that causes a later call to unlink fail. So we
        make the file read/write.
        """
        logging.debug('Writing "%s" to "%s"' % (depot_path, tmpfile))
        self.p4.print_file(depot_path, out_file=tmpfile)

        # The output of 'p4 print' will be a symlink if that's what version
        # control contains. There's a few reasons to skip these files...
        #
        # * Relative symlinks will likely be broken, causing an unexpected
        #   OSError.
        # * File that's symlinked to isn't necessarily in version control.
        # * Users expect that this will only process files under version
        #   control. If I can replace a file they opened with a symlink to
        #   private keys in '~/.ssh', then they'd probably be none too happy
        #   when rbt uses their credentials to publish its contents.

        if os.path.islink(tmpfile):
            raise ValueError("'%s' is a symlink" % depot_path)
        else:
            os.chmod(tmpfile, stat.S_IREAD | stat.S_IWRITE)

    def _depot_to_local(self, depot_path):
        """
        Given a path in the depot return the path on the local filesystem to
        the same file.  If there are multiple results, take only the last
        result from the where command.
        """
        where_output = self.p4.where(depot_path)

        try:
            return where_output[-1]['path']
        except:
            # XXX: This breaks on filenames with spaces.
            return where_output[-1]['data'].split(' ')[2].strip()

    def _supports_moves(self):
        return (self.capabilities and
                self.capabilities.has_capability('scmtools', 'perforce',
                                                 'moved_files'))

########NEW FILE########
__FILENAME__ = plastic
import logging
import os
import re

from rbtools.clients import SCMClient, RepositoryInfo
from rbtools.clients.errors import (InvalidRevisionSpecError,
                                    TooManyRevisionsError)
from rbtools.utils.checks import check_install
from rbtools.utils.filesystem import make_tempfile
from rbtools.utils.process import die, execute


class PlasticClient(SCMClient):
    """
    A wrapper around the cm Plastic tool that fetches repository
    information and generates compatible diffs
    """
    name = 'Plastic'

    REVISION_CHANGESET_PREFIX = 'cs:'

    def __init__(self, **kwargs):
        super(PlasticClient, self).__init__(**kwargs)

    def get_repository_info(self):
        if not check_install(['cm', 'version']):
            logging.debug('Unable to execute "cm version": skipping Plastic')
            return None

        # Get the workspace directory, so we can strip it from the diff output
        self.workspacedir = execute(["cm", "gwp", ".", "--format={1}"],
                                    split_lines=False,
                                    ignore_errors=True).strip()

        logging.debug("Workspace is %s" % self.workspacedir)

        # Get the repository that the current directory is from
        split = execute(["cm", "ls", self.workspacedir, "--format={8}"],
                        split_lines=True, ignore_errors=True)

        # remove blank lines
        split = filter(None, split)

        m = re.search(r'^rep:(.+)$', split[0], re.M)

        if not m:
            return None

        path = m.group(1)

        return RepositoryInfo(path,
                              supports_changesets=True,
                              supports_parent_diffs=False)

    def parse_revision_spec(self, revisions=[]):
        """Parses the given revision spec.

        The 'revisions' argument is a list of revisions as specified by the
        user. Items in the list do not necessarily represent a single revision,
        since the user can use SCM-native syntaxes such as "r1..r2" or "r1:r2".
        SCMTool-specific overrides of this method are expected to deal with
        such syntaxes.

        This will return a dictionary with the following keys:
            'base': Always None.
            'tip':  A revision string representing either a changeset or a
                    branch.

        These will be used to generate the diffs to upload to Review Board (or
        print). The Plastic implementation requires that one and only one
        revision is passed in. The diff for review will include the changes in
        the given changeset or branch.
        """
        n_revisions = len(revisions)

        if n_revisions == 0:
            raise InvalidRevisionSpecError(
                'Either a changeset or a branch must be specified')
        elif n_revisions == 1:
            return {
                'base': None,
                'tip': revisions[0],
            }
        else:
            raise TooManyRevisionsError

    def diff(self, revisions, files=[], extra_args=[]):
        """
        Performs a diff across all modified files in a Plastic workspace

        Parent diffs are not supported (the second value in the tuple).
        """
        # TODO: use 'files'
        changenum = None
        tip = revisions['tip']
        if tip.startswith(self.REVISION_CHANGESET_PREFIX):
            logging.debug('Doing a diff against changeset %s', tip)
            try:
                changenum = str(int(
                    tip[len(self.REVISION_CHANGESET_PREFIX):]))
            except ValueError:
                pass
        else:
            logging.debug('Doing a diff against branch %s', tip)
            if not getattr(self.options, 'branch', None):
                self.options.branch = tip

        diff_entries = execute(
            ['cm', 'diff', tip, '--format={status} {path} rev:revid:{revid} '
                                'rev:revid:{parentrevid} src:{srccmpath} '
                                'dst:{dstcmpath}{newline}'],
            split_lines=True)
        logging.debug('Got files: %s', diff_entries)

        diff = self._process_diffs(diff_entries)

        return {
            'diff': diff,
            'changenum': changenum,
        }

    def _process_diffs(self, my_diff_entries):
        # Diff generation based on perforce client
        diff_lines = []

        empty_filename = make_tempfile()
        tmp_diff_from_filename = make_tempfile()
        tmp_diff_to_filename = make_tempfile()

        for f in my_diff_entries:
            f = f.strip()

            if not f:
                continue

            m = re.search(r'(?P<type>[ACMD]) (?P<file>.*) '
                          r'(?P<revspec>rev:revid:[-\d]+) '
                          r'(?P<parentrevspec>rev:revid:[-\d]+) '
                          r'src:(?P<srcpath>.*) '
                          r'dst:(?P<dstpath>.*)$',
                          f)
            if not m:
                die("Could not parse 'cm log' response: %s" % f)

            changetype = m.group("type")
            filename = m.group("file")

            if changetype == "M":
                # Handle moved files as a delete followed by an add.
                # Clunky, but at least it works
                oldfilename = m.group("srcpath")
                oldspec = m.group("revspec")
                newfilename = m.group("dstpath")
                newspec = m.group("revspec")

                self._write_file(oldfilename, oldspec, tmp_diff_from_filename)
                dl = self._diff_files(tmp_diff_from_filename, empty_filename,
                                      oldfilename, "rev:revid:-1", oldspec,
                                      changetype)
                diff_lines += dl

                self._write_file(newfilename, newspec, tmp_diff_to_filename)
                dl = self._diff_files(empty_filename, tmp_diff_to_filename,
                                      newfilename, newspec, "rev:revid:-1",
                                      changetype)
                diff_lines += dl

            else:
                newrevspec = m.group("revspec")
                parentrevspec = m.group("parentrevspec")

                logging.debug("Type %s File %s Old %s New %s"
                              % (changetype, filename, parentrevspec,
                                 newrevspec))

                old_file = new_file = empty_filename

                if (changetype in ['A'] or
                    (changetype in ['C'] and parentrevspec == "rev:revid:-1")):
                    # There's only one content to show
                    self._write_file(filename, newrevspec, tmp_diff_to_filename)
                    new_file = tmp_diff_to_filename
                elif changetype in ['C']:
                    self._write_file(filename, parentrevspec,
                                     tmp_diff_from_filename)
                    old_file = tmp_diff_from_filename
                    self._write_file(filename, newrevspec, tmp_diff_to_filename)
                    new_file = tmp_diff_to_filename
                elif changetype in ['D']:
                    self._write_file(filename, parentrevspec,
                                     tmp_diff_from_filename)
                    old_file = tmp_diff_from_filename
                else:
                    die("Don't know how to handle change type '%s' for %s" %
                        (changetype, filename))

                dl = self._diff_files(old_file, new_file, filename,
                                      newrevspec, parentrevspec, changetype)
                diff_lines += dl

        os.unlink(empty_filename)
        os.unlink(tmp_diff_from_filename)
        os.unlink(tmp_diff_to_filename)

        return ''.join(diff_lines)

    def _diff_files(self, old_file, new_file, filename, newrevspec,
                    parentrevspec, changetype):
        """
        Do the work of producing a diff for Plastic (based on the Perforce one)

        old_file - The absolute path to the "old" file.
        new_file - The absolute path to the "new" file.
        filename - The file in the Plastic workspace
        newrevspec - The revid spec of the changed file
        parentrevspecspec - The revision spec of the "old" file
        changetype - The change type as a single character string

        Returns a list of strings of diff lines.
        """
        if filename.startswith(self.workspacedir):
            filename = filename[len(self.workspacedir):]

        diff_cmd = ["diff", "-urN", old_file, new_file]
        # Diff returns "1" if differences were found.
        dl = execute(diff_cmd, extra_ignore_errors=(1, 2),
                     translate_newlines = False)

        # If the input file has ^M characters at end of line, lets ignore them.
        dl = dl.replace('\r\r\n', '\r\n')
        dl = dl.splitlines(True)

        # Special handling for the output of the diff tool on binary files:
        #     diff outputs "Files a and b differ"
        # and the code below expects the output to start with
        #     "Binary files "
        if (len(dl) == 1 and
            dl[0].startswith('Files %s and %s differ' % (old_file, new_file))):
            dl = ['Binary files %s and %s differ\n' % (old_file, new_file)]

        if dl == [] or dl[0].startswith("Binary files "):
            if dl == []:
                return []

            dl.insert(0, "==== %s (%s) ==%s==\n" % (filename, newrevspec,
                                                    changetype))
            dl.append('\n')
        else:
            dl[0] = "--- %s\t%s\n" % (filename, parentrevspec)
            dl[1] = "+++ %s\t%s\n" % (filename, newrevspec)

            # Not everybody has files that end in a newline.  This ensures
            # that the resulting diff file isn't broken.
            if dl[-1][-1] != '\n':
                dl.append('\n')

        return dl

    def _write_file(self, filename, filespec, tmpfile):
        """ Grabs a file from Plastic and writes it to a temp file """
        logging.debug("Writing '%s' (rev %s) to '%s'"
                      % (filename, filespec, tmpfile))
        execute(["cm", "cat", filespec, "--file=" + tmpfile])

########NEW FILE########
__FILENAME__ = svn
import logging
import os
import re
import sys
import urllib
from xml.etree import ElementTree

from rbtools.api.errors import APIError
from rbtools.clients import SCMClient, RepositoryInfo
from rbtools.clients.errors import (InvalidRevisionSpecError,
                                    TooManyRevisionsError)
from rbtools.utils.checks import check_gnu_diff, check_install
from rbtools.utils.filesystem import walk_parents
from rbtools.utils.process import execute


class SVNClient(SCMClient):
    """
    A wrapper around the svn Subversion tool that fetches repository
    information and generates compatible diffs.
    """
    name = 'Subversion'

    # Match the diff control lines generated by 'svn diff'.
    DIFF_ORIG_FILE_LINE_RE = re.compile(r'^---\s+.*\s+\(.*\)')
    DIFF_NEW_FILE_LINE_RE = re.compile(r'^\+\+\+\s+.*\s+\(.*\)')
    DIFF_COMPLETE_REMOVAL_RE = re.compile(r'^@@ -1,\d+ \+0,0 @@$')

    REVISION_WORKING_COPY = '--rbtools-working-copy'
    REVISION_CHANGELIST_PREFIX = '--rbtools-changelist:'

    def __init__(self, **kwargs):
        super(SVNClient, self).__init__(**kwargs)

    def get_repository_info(self):
        if not check_install(['svn', 'help']):
            logging.debug('Unable to execute "svn help": skipping SVN')
            return None

        # Get the SVN repository path (either via a working copy or
        # a supplied URI)
        svn_info_params = ["svn", "info"]

        if getattr(self.options, 'repository_url', None):
            svn_info_params.append(self.options.repository_url)

        # Add --non-interactive so that this command will not hang
        #  when used  on a https repository path
        svn_info_params.append("--non-interactive")

        data = execute(svn_info_params, ignore_errors=True)

        m = re.search(r'^Repository Root: (.+)$', data, re.M)
        if not m:
            return None

        path = m.group(1)

        m = re.search(r'^URL: (.+)$', data, re.M)
        if not m:
            return None

        base_path = m.group(1)[len(path):] or "/"

        m = re.search(r'^Repository UUID: (.+)$', data, re.M)
        if not m:
            return None

        # Now that we know it's SVN, make sure we have GNU diff installed,
        # and error out if we don't.
        check_gnu_diff()

        return SVNRepositoryInfo(path, base_path, m.group(1))

    def parse_revision_spec(self, revisions=[]):
        """Parses the given revision spec.

        The 'revisions' argument is a list of revisions as specified by the
        user. Items in the list do not necessarily represent a single revision,
        since the user can use SCM-native syntaxes such as "r1..r2" or "r1:r2".
        SCMTool-specific overrides of this method are expected to deal with
        such syntaxes.

        This will return a dictionary with the following keys:
            'base':        A revision to use as the base of the resulting diff.
            'tip':         A revision to use as the tip of the resulting diff.

        These will be used to generate the diffs to upload to Review Board (or
        print). The diff for review will include the changes in (base, tip].

        If a single revision is passed in, this will return the parent of that
        revision for 'base' and the passed-in revision for 'tip'.

        If zero revisions are passed in, this will return the most recently
        checked-out revision for 'base' and a special string indicating the
        working copy for 'tip'.

        The SVN SCMClient never fills in the 'parent_base' key. Users who are
        using other patch-stack tools who want to use parent diffs with SVN
        will have to generate their diffs by hand.
        """
        n_revisions = len(revisions)

        if n_revisions == 1 and ':' in revisions[0]:
            revisions = revisions[0].split(':')
            n_revisions = len(revisions)

        if n_revisions == 0:
            # Most recent checked-out revision -- working copy

            # TODO: this should warn about mixed-revision working copies that
            # affect the list of files changed (see bug 2392).
            return {
                'base': 'BASE',
                'tip': self.REVISION_WORKING_COPY,
            }
        elif n_revisions == 1:
            # Either a numeric revision (n-1:n) or a changelist
            revision = revisions[0]
            try:
                revision = self._convert_symbolic_revision(revision)
                return {
                    'base': revision - 1,
                    'tip': revision,
                }
            except ValueError:
                # It's not a revision--let's try a changelist. This only makes
                # sense if we have a working copy.
                if not self.options.repository_url:
                    status = execute(['svn', 'status', '--cl', str(revision),
                                      '--ignore-externals', '--xml'])
                    cl = ElementTree.fromstring(status).find('changelist')
                    if cl is not None:
                        # TODO: this should warn about mixed-revision working
                        # copies that affect the list of files changed (see
                        # bug 2392).
                        return {
                            'base': 'BASE',
                            'tip': self.REVISION_CHANGELIST_PREFIX + revision
                        }

                raise InvalidRevisionSpecError(
                    '"%s" does not appear to be a valid revision or '
                    'changelist name' % revision)
        elif n_revisions == 2:
            # Diff between two numeric revisions
            try:
                return {
                    'base': self._convert_symbolic_revision(revisions[0]),
                    'tip': self._convert_symbolic_revision(revisions[1]),
                }
            except ValueError:
                raise InvalidRevisionSpecError(
                    'Could not parse specified revisions: %s' % revisions)
        else:
            raise TooManyRevisionsError

    def _convert_symbolic_revision(self, revision):
        command = ['svn', 'log', '-r', str(revision), '-l', '1', '--xml']
        if getattr(self.options, 'repository_url', None):
            command.append(self.options.repository_url)
        log = execute(command, ignore_errors=True, none_on_ignored_error=True)

        if log is not None:
            root = ElementTree.fromstring(log)
            logentry = root.find('logentry')
            if logentry is not None:
                return int(logentry.attrib['revision'])

        raise ValueError

    def scan_for_server(self, repository_info):
        # Scan first for dot files, since it's faster and will cover the
        # user's $HOME/.reviewboardrc
        server_url = super(SVNClient, self).scan_for_server(repository_info)
        if server_url:
            return server_url

        return self.scan_for_server_property(repository_info)

    def scan_for_server_property(self, repository_info):
        def get_url_prop(path):
            url = execute(["svn", "propget", "reviewboard:url", path],
                          with_errors=False).strip()
            return url or None

        for path in walk_parents(os.getcwd()):
            if not os.path.exists(os.path.join(path, ".svn")):
                break

            prop = get_url_prop(path)
            if prop:
                return prop

        return get_url_prop(repository_info.path)

    def diff(self, revisions, files=[], extra_args=[]):
        """
        Performs a diff in a Subversion repository.

        If the given revision spec is empty, this will do a diff of the
        modified files in the working directory. If the spec is a changelist,
        it will do a diff of the modified files in that changelist. If the spec
        is a single revision, it will show the changes in that revision. If the
        spec is two revisions, this will do a diff between the two revisions.

        SVN repositories do not support branches of branches in a way that
        makes parent diffs possible, so we never return a parent diff.
        """
        base = str(revisions['base'])
        tip = str(revisions['tip'])

        repository_info = self.get_repository_info()

        diff_cmd = ['svn', 'diff', '--diff-cmd=diff', '--notice-ancestry']
        changelist = None

        if tip == self.REVISION_WORKING_COPY:
            # Posting the working copy
            diff_cmd.extend(['-r', base])
        elif tip.startswith(self.REVISION_CHANGELIST_PREFIX):
            # Posting a changelist
            changelist = tip[len(self.REVISION_CHANGELIST_PREFIX):]
            diff_cmd.extend(['--changelist', changelist])
        else:
            # Diff between two separate revisions. Behavior depends on whether
            # or not there's a working copy
            if self.options.repository_url:
                # No working copy--create 'old' and 'new' URLs
                if len(files) == 1:
                    # If there's a single file or directory passed in, we use
                    # that as part of the URL instead of as a separate
                    # filename.
                    repository_info.set_base_path(files[0])
                    files = []

                new_url = (repository_info.path + repository_info.base_path +
                           '@' + tip)

                # When the source revision is '0', assume the user wants to
                # upload a diff containing all the files in 'base_path' as
                # new files. If the base path within the repository is added to
                # both the old and new URLs, `svn diff` will error out, since
                # the base_path didn't exist at revision 0. To avoid that
                # error, use the repository's root URL as the source for the
                # diff.
                if base == '0':
                    old_url = repository_info.path + '@' + base
                else:
                    old_url = (repository_info.path + repository_info.base_path +
                               '@' + base)

                diff_cmd.extend([old_url, new_url])
            else:
                # Working copy--do a normal range diff
                diff_cmd.extend(['-r', '%s:%s' % (base, tip)])

        diff_cmd.extend(files)

        if self.history_scheduled_with_commit(changelist):
            svn_show_copies_as_adds = getattr(
                self.options, 'svn_show_copies_as_adds', None)
            if svn_show_copies_as_adds is None:
                sys.stderr.write("One or more files in your changeset has "
                                 "history scheduled with commit. Please try "
                                 "again with '--svn-show-copies-as-adds=y/n"
                                 "'\n")
                sys.exit(1)
            else:
                if svn_show_copies_as_adds in 'Yy':
                    diff_cmd.append("--show-copies-as-adds")

        diff = execute(diff_cmd, split_lines=True)
        diff = self.handle_renames(diff)
        diff = self.convert_to_absolute_paths(diff, repository_info)

        return {
            'diff': ''.join(diff),
        }

    def history_scheduled_with_commit(self, changelist):
        """ Method to find if any file status has '+' in 4th column"""
        status_cmd = ['svn', 'status', '--ignore-externals']

        if changelist:
            status_cmd.extend(['--changelist', changelist])

        for p in execute(status_cmd, split_lines=True):
            if p[3] == '+':
                return True
        return False

    def find_copyfrom(self, path):
        """
        A helper function for handle_renames

        The output of 'svn info' reports the "Copied From" header when invoked
        on the exact path that was copied. If the current file was copied as a
        part of a parent or any further ancestor directory, 'svn info' will not
        report the origin. Thus it is needed to ascend from the path until
        either a copied path is found or there are no more path components to
        try.
        """
        def smart_join(p1, p2):
            if p2:
                return os.path.join(p1, p2)

            return p1

        path1 = path
        path2 = None

        while path1:
            info = self.svn_info(path1, ignore_errors=True) or {}
            url = info.get('Copied From URL', None)

            if url:
                root = info["Repository Root"]
                from_path1 = urllib.unquote(url[len(root):])
                return smart_join(from_path1, path2)

            if info.get('Schedule', None) != 'normal':
                # Not added as a part of the parent directory, bail out
                return None

            # Strip one component from path1 to path2
            path1, tmp = os.path.split(path1)

            if path1 == "" or path1 == "/":
                path1 = None
            else:
                path2 = smart_join(tmp, path2)

        return None

    def handle_renames(self, diff_content):
        """
        The output of svn diff is incorrect when the file in question came
        into being via svn mv/cp. Although the patch for these files are
        relative to its parent, the diff header doesn't reflect this.
        This function fixes the relevant section headers of the patch to
        portray this relationship.
        """

        # svn diff against a repository URL on two revisions appears to
        # handle moved files properly, so only adjust the diff file names
        # if they were created using a working copy.
        if self.options.repository_url:
            return diff_content

        result = []

        from_line = to_line = None
        for line in diff_content:
            if self.DIFF_ORIG_FILE_LINE_RE.match(line):
                from_line = line
                continue

            if self.DIFF_NEW_FILE_LINE_RE.match(line):
                to_line = line
                continue

            # This is where we decide how mangle the previous '--- '
            if from_line and to_line:
                # If the file is marked completely removed, bail out with
                # original diff. The reason for this is that 'svn diff
                # --notice-ancestry' generates two diffs for a replaced file:
                # one as a complete deletion, and one as a new addition.
                # If it was replaced with history, though, we need to preserve
                # the file name in the "deletion" part - or the patch won't
                # apply.
                if self.DIFF_COMPLETE_REMOVAL_RE.match(line):
                    result.append(from_line)
                    result.append(to_line)
                else:
                    to_file, _ = self.parse_filename_header(to_line[4:])
                    copied_from = self.find_copyfrom(to_file)
                    if copied_from is not None:
                        result.append(from_line.replace(to_file, copied_from))
                    else:
                        result.append(from_line)  # As is, no copy performed
                    result.append(to_line)
                from_line = to_line = None

            # We only mangle '---' lines. All others get added straight to
            # the output.
            result.append(line)

        return result

    def convert_to_absolute_paths(self, diff_content, repository_info):
        """
        Converts relative paths in a diff output to absolute paths.
        This handles paths that have been svn switched to other parts of the
        repository.
        """

        result = []

        for line in diff_content:
            front = None
            orig_line = line
            if (self.DIFF_NEW_FILE_LINE_RE.match(line)
                or self.DIFF_ORIG_FILE_LINE_RE.match(line)
                or line.startswith('Index: ')):
                front, line = line.split(" ", 1)

            if front:
                if line.startswith('/'):  # Already absolute
                    line = front + " " + line
                else:
                    # Filename and rest of line (usually the revision
                    # component)
                    file, rest = self.parse_filename_header(line)

                    # If working with a diff generated outside of a working
                    # copy, then file paths are already absolute, so just
                    # add initial slash.
                    if self.options.repository_url:
                        path = urllib.unquote(
                            "%s/%s" % (repository_info.base_path, file))
                    else:
                        info = self.svn_info(file, True)
                        if info is None:
                            result.append(orig_line)
                            continue
                        url = info["URL"]
                        root = info["Repository Root"]
                        path = urllib.unquote(url[len(root):])

                    line = front + " " + path + rest

            result.append(line)

        return result

    def svn_info(self, path, ignore_errors=False):
        """Return a dict which is the result of 'svn info' at a given path."""
        svninfo = {}

        # SVN's internal path recognizers think that any file path that
        # includes an '@' character will be path@rev, and skips everything that
        # comes after the '@'. This makes it hard to do operations on files
        # which include '@' in the name (such as image@2x.png).
        if '@' in path and not path[-1] == '@':
            path += '@'

        result = execute(["svn", "info", path],
                         split_lines=True,
                         ignore_errors=ignore_errors,
                         none_on_ignored_error=True)
        if result is None:
            return None

        for info in result:
            parts = info.strip().split(": ", 1)
            if len(parts) == 2:
                key, value = parts
                svninfo[key] = value

        return svninfo

    # Adapted from server code parser.py
    def parse_filename_header(self, s):
        parts = None
        if "\t" in s:
            # There's a \t separating the filename and info. This is the
            # best case scenario, since it allows for filenames with spaces
            # without much work. The info can also contain tabs after the
            # initial one; ignore those when splitting the string.
            parts = s.split("\t", 1)

        # There's spaces being used to separate the filename and info.
        # This is technically wrong, so all we can do is assume that
        # 1) the filename won't have multiple consecutive spaces, and
        # 2) there's at least 2 spaces separating the filename and info.
        if "  " in s:
            parts = re.split(r"  +", s)

        if parts:
            parts[1] = '\t' + parts[1]
            return parts

        # strip off ending newline, and return it as the second component
        return [s.split('\n')[0], '\n']


class SVNRepositoryInfo(RepositoryInfo):
    """
    A representation of a SVN source code repository. This version knows how to
    find a matching repository on the server even if the URLs differ.
    """
    def __init__(self, path, base_path, uuid, supports_parent_diffs=False):
        RepositoryInfo.__init__(self, path, base_path,
                                supports_parent_diffs=supports_parent_diffs)
        self.uuid = uuid

    def find_server_repository_info(self, server):
        """
        The point of this function is to find a repository on the server that
        matches self, even if the paths aren't the same. (For example, if self
        uses an 'http' path, but the server uses a 'file' path for the same
        repository.) It does this by comparing repository UUIDs. If the
        repositories use the same path, you'll get back self, otherwise you'll
        get a different SVNRepositoryInfo object (with a different path).
        """
        repositories = [
            repository
            for repository in server.get_repositories()
            if repository['tool'] == 'Subversion'
        ]

        # Do two paths. The first will be to try to find a matching entry
        # by path/mirror path. If we don't find anything, then the second will
        # be to find a matching UUID.
        for repository in repositories:
            if self.path in (repository['path'],
                             repository.get('mirror_path', '')):
                return self

        # We didn't find our locally matched repository, so scan based on UUID.
        for repository in repositories:
            info = self._get_repository_info(server, repository)

            if not info or self.uuid != info['uuid']:
                continue

            repos_base_path = info['url'][len(info['root_url']):]
            relpath = self._get_relative_path(self.base_path, repos_base_path)

            if relpath:
                return SVNRepositoryInfo(info['url'], relpath, self.uuid)

        # We didn't find a matching repository on the server. We'll just return
        # self and hope for the best. In reality, we'll likely fail, but we
        # did all we could really do.
        return self

    def _get_repository_info(self, server, repository):
        try:
            return server.get_repository_info(repository['id'])
        except APIError, e:
            # If the server couldn't fetch the repository info, it will return
            # code 210. Ignore those.
            # Other more serious errors should still be raised, though.
            if e.error_code == 210:
                return None

            raise e

    def _get_relative_path(self, path, root):
        pathdirs = self._split_on_slash(path)
        rootdirs = self._split_on_slash(root)

        # root is empty, so anything relative to that is itself
        if len(rootdirs) == 0:
            return path

        # If one of the directories doesn't match, then path is not relative
        # to root.
        if rootdirs != pathdirs[:len(rootdirs)]:
            return None

        # All the directories matched, so the relative path is whatever
        # directories are left over. The base_path can't be empty, though, so
        # if the paths are the same, return '/'
        if len(pathdirs) == len(rootdirs):
            return '/'
        else:
            return '/' + '/'.join(pathdirs[len(rootdirs):])

    def _split_on_slash(self, path):
        # Split on slashes, but ignore multiple slashes and throw away any
        # trailing slashes.
        split = re.split('/*', path)
        if split[-1] == '':
            split = split[0:-1]
        return split

########NEW FILE########
__FILENAME__ = tests
import os
import re
import sys
import time
from hashlib import md5
from random import randint
from tempfile import mktemp
from textwrap import dedent

from nose import SkipTest

from rbtools.api.capabilities import Capabilities
from rbtools.clients import RepositoryInfo
from rbtools.clients.bazaar import (
    BazaarClient,
    USING_PARENT_PREFIX as BZR_USING_PARENT_PREFIX)
from rbtools.clients.errors import InvalidRevisionSpecError
from rbtools.clients.git import GitClient
from rbtools.clients.mercurial import MercurialClient
from rbtools.clients.perforce import PerforceClient, P4Wrapper
from rbtools.clients.svn import SVNRepositoryInfo, SVNClient
from rbtools.tests import OptionsStub
from rbtools.utils.filesystem import load_config_files, make_tempfile
from rbtools.utils.process import execute
from rbtools.utils.testbase import RBTestBase


class SCMClientTests(RBTestBase):
    def setUp(self):
        super(SCMClientTests, self).setUp()

        self.options = OptionsStub()

        self.clients_dir = os.path.dirname(__file__)


class GitClientTests(SCMClientTests):
    TESTSERVER = "http://127.0.0.1:8080"

    def _run_git(self, command):
        return execute(['git'] + command, env=None, split_lines=False,
                       ignore_errors=False, extra_ignore_errors=(),
                       translate_newlines=True)

    def _git_add_file_commit(self, file, data, msg):
        """Add a file to a git repository with the content of data
        and commit with msg.
        """
        foo = open(file, 'w')
        foo.write(data)
        foo.close()
        self._run_git(['add', file])
        self._run_git(['commit', '-m', msg])

    def _git_get_head(self):
        return self._run_git(['rev-parse', 'HEAD']).strip()

    def setUp(self):
        super(GitClientTests, self).setUp()

        if not self.is_exe_in_path('git'):
            raise SkipTest('git not found in path')

        self.set_user_home(os.path.join(self.clients_dir, 'testdata', 'homedir'))
        self.git_dir = os.path.join(self.clients_dir, 'testdata', 'git-repo')

        self.clone_dir = self.chdir_tmp()
        self._run_git(['clone', self.git_dir, self.clone_dir])
        self.client = GitClient(options=self.options)

        self.user_config = {}
        self.configs = []
        self.client.user_config = self.user_config
        self.client.configs = self.configs
        self.options.parent_branch = None

    def test_get_repository_info_simple(self):
        """Testing GitClient get_repository_info, simple case"""
        ri = self.client.get_repository_info()
        self.assertTrue(isinstance(ri, RepositoryInfo))
        self.assertEqual(ri.base_path, '')
        self.assertEqual(ri.path.rstrip("/.git"), self.git_dir)
        self.assertTrue(ri.supports_parent_diffs)
        self.assertFalse(ri.supports_changesets)

    def test_scan_for_server_simple(self):
        """Testing GitClient scan_for_server, simple case"""
        ri = self.client.get_repository_info()

        server = self.client.scan_for_server(ri)
        self.assertTrue(server is None)

    def test_scan_for_server_reviewboardrc(self):
        "Testing GitClient scan_for_server, .reviewboardrc case"""
        rc = open(os.path.join(self.clone_dir, '.reviewboardrc'), 'w')
        rc.write('REVIEWBOARD_URL = "%s"' % self.TESTSERVER)
        rc.close()
        self.client.user_config, configs = load_config_files(self.clone_dir)

        ri = self.client.get_repository_info()
        server = self.client.scan_for_server(ri)
        self.assertEqual(server, self.TESTSERVER)

    def test_scan_for_server_property(self):
        """Testing GitClient scan_for_server using repo property"""
        self._run_git(['config', 'reviewboard.url', self.TESTSERVER])
        ri = self.client.get_repository_info()

        self.assertEqual(self.client.scan_for_server(ri), self.TESTSERVER)

    def test_diff_simple(self):
        """Testing GitClient simple diff case"""
        self.client.get_repository_info()
        base_commit_id = self._git_get_head()

        self._git_add_file_commit('foo.txt', FOO1, 'delete and modify stuff')
        commit_id = self._git_get_head()

        revisions = self.client.parse_revision_spec([])
        result = self.client.diff(revisions)
        self.assertTrue(isinstance(result, dict))
        self.assertEqual(len(result), 4)
        self.assertTrue('diff' in result)
        self.assertTrue('parent_diff' in result)
        self.assertTrue('base_commit_id' in result)
        self.assertTrue('commit_id' in result)
        self.assertEqual(md5(result['diff']).hexdigest(),
                         '69d4616cf985f6b10571036db744e2d8')
        self.assertEqual(result['parent_diff'], None)
        self.assertEqual(result['base_commit_id'], base_commit_id)
        self.assertEqual(result['commit_id'], commit_id)

    def test_diff_simple_multiple(self):
        """Testing GitClient simple diff with multiple commits case"""
        self.client.get_repository_info()

        base_commit_id = self._git_get_head()

        self._git_add_file_commit('foo.txt', FOO1, 'commit 1')
        self._git_add_file_commit('foo.txt', FOO2, 'commit 1')
        self._git_add_file_commit('foo.txt', FOO3, 'commit 1')
        commit_id = self._git_get_head()

        revisions = self.client.parse_revision_spec([])
        result = self.client.diff(revisions)
        self.assertTrue(isinstance(result, dict))
        self.assertEqual(len(result), 4)
        self.assertTrue('diff' in result)
        self.assertTrue('parent_diff' in result)
        self.assertTrue('base_commit_id' in result)
        self.assertTrue('commit_id' in result)
        self.assertEqual(md5(result['diff']).hexdigest(),
                         'c9a31264f773406edff57a8ed10d9acc')
        self.assertEqual(result['parent_diff'], None)
        self.assertEqual(result['base_commit_id'], base_commit_id)
        self.assertEqual(result['commit_id'], commit_id)

    def test_diff_branch_diverge(self):
        """Testing GitClient diff with divergent branches"""
        self._git_add_file_commit('foo.txt', FOO1, 'commit 1')
        self._run_git(['checkout', '-b', 'mybranch', '--track',
                      'origin/master'])
        base_commit_id = self._git_get_head()
        self._git_add_file_commit('foo.txt', FOO2, 'commit 2')
        commit_id = self._git_get_head()
        self.client.get_repository_info()

        revisions = self.client.parse_revision_spec([])
        result = self.client.diff(revisions)
        self.assertTrue(isinstance(result, dict))
        self.assertEqual(len(result), 4)
        self.assertTrue('diff' in result)
        self.assertTrue('parent_diff' in result)
        self.assertTrue('base_commit_id' in result)
        self.assertTrue('commit_id' in result)
        self.assertEqual(md5(result['diff']).hexdigest(),
                         'cfb79a46f7a35b07e21765608a7852f7')
        self.assertEqual(result['parent_diff'], None)
        self.assertEqual(result['base_commit_id'], base_commit_id)
        self.assertEqual(result['commit_id'], commit_id)

        self._run_git(['checkout', 'master'])
        self.client.get_repository_info()
        commit_id = self._git_get_head()

        revisions = self.client.parse_revision_spec([])
        result = self.client.diff(revisions)
        self.assertTrue(isinstance(result, dict))
        self.assertEqual(len(result), 4)
        self.assertTrue('diff' in result)
        self.assertTrue('parent_diff' in result)
        self.assertTrue('base_commit_id' in result)
        self.assertTrue('commit_id' in result)
        self.assertEqual(md5(result['diff']).hexdigest(),
                         '69d4616cf985f6b10571036db744e2d8')
        self.assertEqual(result['parent_diff'], None)
        self.assertEqual(result['base_commit_id'], base_commit_id)
        self.assertEqual(result['commit_id'], commit_id)

    def test_diff_tracking_no_origin(self):
        """Testing GitClient diff with a tracking branch, but no origin remote"""
        self._run_git(['remote', 'add', 'quux', self.git_dir])
        self._run_git(['fetch', 'quux'])
        self._run_git(['checkout', '-b', 'mybranch', '--track', 'quux/master'])

        base_commit_id = self._git_get_head()
        self._git_add_file_commit('foo.txt', FOO1, 'delete and modify stuff')
        commit_id = self._git_get_head()

        self.client.get_repository_info()

        revisions = self.client.parse_revision_spec([])
        result = self.client.diff(revisions)
        self.assertTrue(isinstance(result, dict))
        self.assertEqual(len(result), 4)
        self.assertTrue('diff' in result)
        self.assertTrue('parent_diff' in result)
        self.assertTrue('base_commit_id' in result)
        self.assertTrue('commit_id' in result)
        self.assertEqual(md5(result['diff']).hexdigest(),
                         '69d4616cf985f6b10571036db744e2d8')
        self.assertEqual(result['parent_diff'], None)
        self.assertEqual(result['base_commit_id'], base_commit_id)
        self.assertEqual(result['commit_id'], commit_id)

    def test_diff_local_tracking(self):
        """Testing GitClient diff with a local tracking branch"""
        base_commit_id = self._git_get_head()
        self._git_add_file_commit('foo.txt', FOO1, 'commit 1')

        self._run_git(['checkout', '-b', 'mybranch', '--track', 'master'])
        self._git_add_file_commit('foo.txt', FOO2, 'commit 2')
        commit_id = self._git_get_head()

        self.client.get_repository_info()

        revisions = self.client.parse_revision_spec([])
        result = self.client.diff(revisions)
        self.assertTrue(isinstance(result, dict))
        self.assertEqual(len(result), 4)
        self.assertTrue('diff' in result)
        self.assertTrue('parent_diff' in result)
        self.assertTrue('base_commit_id' in result)
        self.assertTrue('commit_id' in result)
        self.assertEqual(md5(result['diff']).hexdigest(),
                         'cfb79a46f7a35b07e21765608a7852f7')
        self.assertEqual(result['parent_diff'], None)
        self.assertEqual(result['base_commit_id'], base_commit_id)
        self.assertEqual(result['commit_id'], commit_id)

    def test_diff_tracking_override(self):
        """Testing GitClient diff with option override for tracking branch"""
        self.options.tracking = 'origin/master'

        self._run_git(['remote', 'add', 'bad', self.git_dir])
        self._run_git(['fetch', 'bad'])
        self._run_git(['checkout', '-b', 'mybranch', '--track', 'bad/master'])

        base_commit_id = self._git_get_head()

        self._git_add_file_commit('foo.txt', FOO1, 'commit 1')
        commit_id = self._git_get_head()

        self.client.get_repository_info()

        revisions = self.client.parse_revision_spec([])
        result = self.client.diff(revisions)
        self.assertTrue(isinstance(result, dict))
        self.assertEqual(len(result), 4)
        self.assertTrue('diff' in result)
        self.assertTrue('parent_diff' in result)
        self.assertTrue('base_commit_id' in result)
        self.assertTrue('commit_id' in result)
        self.assertEqual(md5(result['diff']).hexdigest(),
                         '69d4616cf985f6b10571036db744e2d8')
        self.assertEqual(result['parent_diff'], None)
        self.assertEqual(result['base_commit_id'], base_commit_id)
        self.assertEqual(result['commit_id'], commit_id)

    def test_diff_slash_tracking(self):
        """Testing GitClient diff with tracking branch that has slash in its name."""
        self._run_git(['fetch', 'origin'])
        self._run_git(['checkout', '-b', 'my/branch', '--track',
                       'origin/not-master'])
        base_commit_id = self._git_get_head()
        self._git_add_file_commit('foo.txt', FOO2, 'commit 2')
        commit_id = self._git_get_head()

        self.client.get_repository_info()

        revisions = self.client.parse_revision_spec([])
        result = self.client.diff(revisions)
        self.assertTrue(isinstance(result, dict))
        self.assertEqual(len(result), 4)
        self.assertTrue('diff' in result)
        self.assertTrue('parent_diff' in result)
        self.assertTrue('base_commit_id' in result)
        self.assertTrue('commit_id' in result)
        self.assertEqual(md5(result['diff']).hexdigest(),
                         'd2015ff5fd0297fd7f1210612f87b6b3')
        self.assertEqual(result['parent_diff'], None)
        self.assertEqual(result['base_commit_id'], base_commit_id)
        self.assertEqual(result['commit_id'], commit_id)

    def test_parse_revision_spec_no_args(self):
        """Testing GitClient.parse_revision_spec with no specified revisions"""
        base_commit_id = self._git_get_head()
        self._git_add_file_commit('foo.txt', FOO2, 'Commit 2')
        tip_commit_id = self._git_get_head()

        self.client.get_repository_info()

        revisions = self.client.parse_revision_spec()
        self.assertTrue(isinstance(revisions, dict))
        self.assertTrue('base' in revisions)
        self.assertTrue('tip' in revisions)
        self.assertTrue('parent_base' not in revisions)
        self.assertEqual(revisions['base'], base_commit_id)
        self.assertEqual(revisions['tip'], tip_commit_id)

    def test_parse_revision_spec_no_args_parent(self):
        """Testing GitClient.parse_revision_spec with no specified revisions and a parent diff"""
        parent_base_commit_id = self._git_get_head()

        self._run_git(['fetch', 'origin'])
        self._run_git(['checkout', '-b', 'parent-branch', '--track',
                       'origin/not-master'])

        base_commit_id = self._git_get_head()

        self._run_git(['checkout', '-b', 'topic-branch'])

        self._git_add_file_commit('foo.txt', FOO2, 'Commit 2')
        tip_commit_id = self._git_get_head()

        self.options.parent_branch = 'parent-branch'

        self.client.get_repository_info()

        revisions = self.client.parse_revision_spec()
        self.assertTrue(isinstance(revisions, dict))
        self.assertTrue('base' in revisions)
        self.assertTrue('tip' in revisions)
        self.assertTrue('parent_base' in revisions)
        self.assertEqual(revisions['parent_base'], parent_base_commit_id)
        self.assertEqual(revisions['base'], base_commit_id)
        self.assertEqual(revisions['tip'], tip_commit_id)

    def test_parse_revision_spec_one_arg(self):
        """Testing GitClient.parse_revision_spec with one specified revision"""
        base_commit_id = self._git_get_head()
        self._git_add_file_commit('foo.txt', FOO2, 'Commit 2')
        tip_commit_id = self._git_get_head()

        self.client.get_repository_info()

        revisions = self.client.parse_revision_spec([tip_commit_id])
        self.assertTrue(isinstance(revisions, dict))
        self.assertTrue('base' in revisions)
        self.assertTrue('tip' in revisions)
        self.assertTrue('parent_base' not in revisions)
        self.assertEqual(revisions['base'], base_commit_id)
        self.assertEqual(revisions['tip'], tip_commit_id)

    def test_parse_revision_spec_one_arg_parent(self):
        """Testing GitClient.parse_revision_spec with one specified revision and a parent diff"""
        parent_base_commit_id = self._git_get_head()
        self._git_add_file_commit('foo.txt', FOO2, 'Commit 2')
        base_commit_id = self._git_get_head()
        self._git_add_file_commit('foo.txt', FOO3, 'Commit 3')
        tip_commit_id = self._git_get_head()

        self.client.get_repository_info()

        revisions = self.client.parse_revision_spec([tip_commit_id])
        self.assertTrue(isinstance(revisions, dict))
        self.assertTrue('base' in revisions)
        self.assertTrue('tip' in revisions)
        self.assertTrue('parent_base' in revisions)
        self.assertEqual(revisions['parent_base'], parent_base_commit_id)
        self.assertEqual(revisions['base'], base_commit_id)
        self.assertEqual(revisions['tip'], tip_commit_id)

    def test_parse_revision_spec_two_args(self):
        """Testing GitClient.parse_revision_spec with two specified revisions"""
        base_commit_id = self._git_get_head()
        self._run_git(['checkout', '-b', 'topic-branch'])
        self._git_add_file_commit('foo.txt', FOO2, 'Commit 2')
        tip_commit_id = self._git_get_head()

        self.client.get_repository_info()

        revisions = self.client.parse_revision_spec(['master', 'topic-branch'])
        self.assertTrue(isinstance(revisions, dict))
        self.assertTrue('base' in revisions)
        self.assertTrue('tip' in revisions)
        self.assertTrue('parent_base' not in revisions)
        self.assertEqual(revisions['base'], base_commit_id)
        self.assertEqual(revisions['tip'], tip_commit_id)

    def test_parse_revision_spec_one_arg_two_revs(self):
        """Testing GitClient.parse_revision_spec with diff-since syntax"""
        base_commit_id = self._git_get_head()
        self._run_git(['checkout', '-b', 'topic-branch'])
        self._git_add_file_commit('foo.txt', FOO2, 'Commit 2')
        tip_commit_id = self._git_get_head()

        self.client.get_repository_info()

        revisions = self.client.parse_revision_spec(['master..topic-branch'])
        self.assertTrue(isinstance(revisions, dict))
        self.assertTrue('base' in revisions)
        self.assertTrue('tip' in revisions)
        self.assertTrue('parent_base' not in revisions)
        self.assertEqual(revisions['base'], base_commit_id)
        self.assertEqual(revisions['tip'], tip_commit_id)

    def test_parse_revision_spec_one_arg_since_merge(self):
        """Testing GitClient.parse_revision_spec with diff-since-merge syntax"""
        base_commit_id = self._git_get_head()
        self._run_git(['checkout', '-b', 'topic-branch'])
        self._git_add_file_commit('foo.txt', FOO2, 'Commit 2')
        tip_commit_id = self._git_get_head()

        self.client.get_repository_info()

        revisions = self.client.parse_revision_spec(['master...topic-branch'])
        self.assertTrue(isinstance(revisions, dict))
        self.assertTrue('base' in revisions)
        self.assertTrue('tip' in revisions)
        self.assertTrue('parent_base' not in revisions)
        self.assertEqual(revisions['base'], base_commit_id)
        self.assertEqual(revisions['tip'], tip_commit_id)


class MercurialTestBase(SCMClientTests):
    def setUp(self):
        super(MercurialTestBase, self).setUp()
        self._hg_env = {}

    def _run_hg(self, command, ignore_errors=False, extra_ignore_errors=()):
        # We're *not* doing `env = env or {}` here because
        # we want the caller to be able to *enable* reading
        # of user and system-level hgrc configuration.
        env = self._hg_env.copy()

        if not env:
            env = {
                'HGRCPATH': os.devnull,
                'HGPLAIN': '1',
            }

        return execute(['hg'] + command, env, split_lines=False,
                       ignore_errors=ignore_errors,
                       extra_ignore_errors=extra_ignore_errors,
                       translate_newlines=True)

    def _hg_add_file_commit(self, filename, data, msg, branch=None):
        outfile = open(filename, 'w')
        outfile.write(data)
        outfile.close()
        if branch:
            self._run_hg(['branch', branch])
        self._run_hg(['add', filename])
        self._run_hg(['commit', '-m', msg])


class MercurialClientTests(MercurialTestBase):
    TESTSERVER = 'http://127.0.0.1:8080'
    CLONE_HGRC = dedent("""
    [paths]
    default = %(hg_dir)s
    cloned = %(clone_dir)s

    [reviewboard]
    url = %(test_server)s

    [diff]
    git = true
    """).rstrip()

    def setUp(self):
        super(MercurialClientTests, self).setUp()
        if not self.is_exe_in_path('hg'):
            raise SkipTest('hg not found in path')

        self.hg_dir = os.path.join(self.clients_dir, 'testdata', 'hg-repo')
        self.clone_dir = self.chdir_tmp()

        self._run_hg(['clone', self.hg_dir, self.clone_dir])
        self.client = MercurialClient(options=self.options)

        clone_hgrc = open(self.clone_hgrc_path, 'wb')
        clone_hgrc.write(self.CLONE_HGRC % {
            'hg_dir': self.hg_dir,
            'clone_dir': self.clone_dir,
            'test_server': self.TESTSERVER,
        })
        clone_hgrc.close()

        self.user_config = {}
        self.configs = []
        self.client.user_config = self.user_config
        self.client.configs = self.configs
        self.options.parent_branch = None

    def _hg_get_tip(self):
        return self._run_hg(['identify']).split()[0]

    @property
    def clone_hgrc_path(self):
        return os.path.join(self.clone_dir, '.hg', 'hgrc')

    def test_get_repository_info_simple(self):
        """Testing MercurialClient get_repository_info, simple case"""
        ri = self.client.get_repository_info()

        self.assertTrue(isinstance(ri, RepositoryInfo))
        self.assertEqual('', ri.base_path)

        hgpath = ri.path

        if os.path.basename(hgpath) == '.hg':
            hgpath = os.path.dirname(hgpath)

        self.assertEqual(self.hg_dir, hgpath)
        self.assertTrue(ri.supports_parent_diffs)
        self.assertFalse(ri.supports_changesets)

    def test_scan_for_server_simple(self):
        """Testing MercurialClient scan_for_server, simple case"""
        os.rename(self.clone_hgrc_path,
                  os.path.join(self.clone_dir, '._disabled_hgrc'))

        self.client.hgrc = {}
        self.client._load_hgrc()
        ri = self.client.get_repository_info()

        server = self.client.scan_for_server(ri)
        self.assertTrue(server is None)

    def test_scan_for_server_when_present_in_hgrc(self):
        """Testing MercurialClient scan_for_server when present in hgrc"""
        ri = self.client.get_repository_info()

        server = self.client.scan_for_server(ri)
        self.assertEqual(self.TESTSERVER, server)

    def test_scan_for_server_reviewboardrc(self):
        """Testing MercurialClient scan_for_server when in .reviewboardrc"""
        rc = open(os.path.join(self.clone_dir, '.reviewboardrc'), 'w')
        rc.write('REVIEWBOARD_URL = "%s"' % self.TESTSERVER)
        rc.close()

        ri = self.client.get_repository_info()
        server = self.client.scan_for_server(ri)
        self.assertEqual(self.TESTSERVER, server)

    def test_diff_simple(self):
        """Testing MercurialClient diff, simple case"""
        self._hg_add_file_commit('foo.txt', FOO1, 'delete and modify stuff')

        revisions = self.client.parse_revision_spec([])
        result = self.client.diff(revisions)
        self.assertTrue(isinstance(result, dict))
        self.assertTrue('diff' in result)
        self.assertEqual(md5(result['diff']).hexdigest(),
                         '68c2bdccf52a4f0baddd0ac9f2ecb7d2')

    def test_diff_simple_multiple(self):
        """Testing MercurialClient diff with multiple commits"""
        self._hg_add_file_commit('foo.txt', FOO1, 'commit 1')
        self._hg_add_file_commit('foo.txt', FOO2, 'commit 2')
        self._hg_add_file_commit('foo.txt', FOO3, 'commit 3')

        revisions = self.client.parse_revision_spec([])
        result = self.client.diff(revisions)
        self.assertTrue(isinstance(result, dict))
        self.assertTrue('diff' in result)
        self.assertEqual(md5(result['diff']).hexdigest(),
                         '9c8796936646be5c7349973b0fceacbd')

    def test_diff_branch_diverge(self):
        """Testing MercurialClient diff with diverged branch"""
        self._hg_add_file_commit('foo.txt', FOO1, 'commit 1')

        self._run_hg(['branch', 'diverged'])
        self._hg_add_file_commit('foo.txt', FOO2, 'commit 2')

        revisions = self.client.parse_revision_spec([])
        result = self.client.diff(revisions)
        self.assertTrue(isinstance(result, dict))
        self.assertTrue('diff' in result)
        self.assertEqual(md5(result['diff']).hexdigest(),
                         '6b12723baab97f346aa938005bc4da4d')

        self._run_hg(['update', '-C', 'default'])

        revisions = self.client.parse_revision_spec([])
        result = self.client.diff(revisions)
        self.assertTrue(isinstance(result, dict))
        self.assertTrue('diff' in result)
        self.assertEqual(md5(result['diff']).hexdigest(),
                         '68c2bdccf52a4f0baddd0ac9f2ecb7d2')

    def test_diff_parent_diff_simple(self):
        """Testing MercurialClient parent diffs with a simple case"""
        self._hg_add_file_commit('foo.txt', FOO1, 'commit 1')
        self._hg_add_file_commit('foo.txt', FOO2, 'commit 2')
        self._hg_add_file_commit('foo.txt', FOO3, 'commit 3')

        revisions = self.client.parse_revision_spec(['2', '3'])
        result = self.client.diff(revisions)
        self.assertTrue(isinstance(result, dict))
        self.assertTrue('parent_diff' in result)
        self.assertEqual(md5(result['diff']).hexdigest(),
                         '7a897f68a9dc034fc1e42fe7a33bb808')
        self.assertEqual(md5(result['parent_diff']).hexdigest(),
                         '5cacbd79800a9145f982dcc0908b6068')

    def test_diff_parent_diff_branch_diverge(self):
        """Testing MercurialClient parent diffs with a diverged branch"""

        # This test is very similar to test_diff_parent_diff_simple except
        # we throw a branch into the mix.
        self._hg_add_file_commit('foo.txt', FOO1, 'commit 1')
        self._run_hg(['branch', 'diverged'])
        self._hg_add_file_commit('foo.txt', FOO2, 'commit 2')
        self._hg_add_file_commit('foo.txt', FOO3, 'commit 3')

        revisions = self.client.parse_revision_spec(['2', '3'])
        result = self.client.diff(revisions)
        self.assertTrue('parent_diff' in result)
        self.assertEqual(md5(result['diff']).hexdigest(),
                         '7a897f68a9dc034fc1e42fe7a33bb808')
        self.assertEqual(md5(result['parent_diff']).hexdigest(),
                         '5cacbd79800a9145f982dcc0908b6068')

    def test_diff_parent_diff_simple_with_arg(self):
        """Testing MercurialClient parent diffs with a diverged branch and --parent option"""
        # This test is very similar to test_diff_parent_diff_simple except
        # we use the --parent option to post without explicit revisions
        self._hg_add_file_commit('foo.txt', FOO1, 'commit 1')
        self._hg_add_file_commit('foo.txt', FOO2, 'commit 2')
        self._hg_add_file_commit('foo.txt', FOO3, 'commit 3')

        self.options.parent_branch = '2'

        revisions = self.client.parse_revision_spec([])
        result = self.client.diff(revisions)
        self.assertTrue(isinstance(result, dict))
        self.assertTrue('parent_diff' in result)
        self.assertEqual(md5(result['diff']).hexdigest(),
                         '7a897f68a9dc034fc1e42fe7a33bb808')
        self.assertEqual(md5(result['parent_diff']).hexdigest(),
                         '5cacbd79800a9145f982dcc0908b6068')

    def test_parse_revision_spec_no_args(self):
        """Testing MercurialClient.parse_revision_spec with no arguments"""
        base = self._hg_get_tip()
        self._hg_add_file_commit('foo.txt', FOO1, 'commit 1')
        self._hg_add_file_commit('foo.txt', FOO2, 'commit 2')
        tip = self._hg_get_tip()

        revisions = self.client.parse_revision_spec([])
        self.assertTrue(isinstance(revisions, dict))
        self.assertTrue('base' in revisions)
        self.assertTrue('tip' in revisions)
        self.assertTrue('parent_base' not in revisions)
        self.assertEqual(revisions['base'], base)
        self.assertEqual(revisions['tip'], tip)

    def test_parse_revision_spec_one_arg_periods(self):
        """Testing MercurialClient.parse_revision_spec with r1..r2 syntax"""
        base = self._hg_get_tip()
        self._hg_add_file_commit('foo.txt', FOO1, 'commit 1')
        tip = self._hg_get_tip()

        revisions = self.client.parse_revision_spec(['0..1'])
        self.assertTrue(isinstance(revisions, dict))
        self.assertTrue('base' in revisions)
        self.assertTrue('tip' in revisions)
        self.assertTrue('parent_base' not in revisions)
        self.assertEqual(revisions['base'], base)
        self.assertEqual(revisions['tip'], tip)

    def test_parse_revision_spec_one_arg_colons(self):
        """Testing MercurialClient.parse_revision_spec with r1::r2 syntax"""
        base = self._hg_get_tip()
        self._hg_add_file_commit('foo.txt', FOO1, 'commit 1')
        tip = self._hg_get_tip()

        revisions = self.client.parse_revision_spec(['0..1'])
        self.assertTrue(isinstance(revisions, dict))
        self.assertTrue('base' in revisions)
        self.assertTrue('tip' in revisions)
        self.assertTrue('parent_base' not in revisions)
        self.assertEqual(revisions['base'], base)
        self.assertEqual(revisions['tip'], tip)

    def test_parse_revision_spec_one_arg(self):
        """Testing MercurialClient.parse_revision_spec with one revision"""
        base = self._hg_get_tip()
        self._hg_add_file_commit('foo.txt', FOO1, 'commit 1')
        tip = self._hg_get_tip()
        self._hg_add_file_commit('foo.txt', FOO2, 'commit 2')

        revisions = self.client.parse_revision_spec(['1'])
        self.assertTrue(isinstance(revisions, dict))
        self.assertTrue('base' in revisions)
        self.assertTrue('tip' in revisions)
        self.assertTrue('parent_base' not in revisions)
        self.assertEqual(revisions['base'], base)
        self.assertEqual(revisions['tip'], tip)

    def test_parse_revision_spec_two_args(self):
        """Testing MercurialClient.parse_revision_spec with two revisions"""
        base = self._hg_get_tip()
        self._hg_add_file_commit('foo.txt', FOO1, 'commit 1')
        self._hg_add_file_commit('foo.txt', FOO2, 'commit 2')
        tip = self._hg_get_tip()

        revisions = self.client.parse_revision_spec(['0', '2'])
        self.assertTrue(isinstance(revisions, dict))
        self.assertTrue('base' in revisions)
        self.assertTrue('tip' in revisions)
        self.assertTrue('parent_base' not in revisions)
        self.assertEqual(revisions['base'], base)
        self.assertEqual(revisions['tip'], tip)

    def test_parse_revision_spec_parent_base(self):
        """Testing MercurialClient.parse_revision_spec with parent base"""
        start_base = self._hg_get_tip()
        self._hg_add_file_commit('foo.txt', FOO1, 'commit 1')
        commit1 = self._hg_get_tip()
        self._hg_add_file_commit('foo.txt', FOO2, 'commit 2')
        commit2 = self._hg_get_tip()
        self._hg_add_file_commit('foo.txt', FOO3, 'commit 3')
        commit3 = self._hg_get_tip()
        self._hg_add_file_commit('foo.txt', FOO4, 'commit 4')
        commit4 = self._hg_get_tip()
        self._hg_add_file_commit('foo.txt', FOO5, 'commit 5')

        self.assertEqual(self.client.parse_revision_spec(['1', '2']),
            dict(base=commit1, tip=commit2, parent_base=start_base))

        self.assertEqual(self.client.parse_revision_spec(['4']),
            dict(base=commit3, tip=commit4, parent_base=start_base,
                 commit_id=commit4))

        self.assertEqual(self.client.parse_revision_spec(['2', '4']),
            dict(base=commit2, tip=commit4, parent_base=start_base))

    def test_guess_summary_description_one(self):
        """Testing MercurialClient guess summary & description 1 commit."""
        self.options.guess_summary = True
        self.options.guess_description = True

        self._hg_add_file_commit('foo.txt', FOO1, 'commit 1')

        revisions = self.client.parse_revision_spec([])
        commit_message = self.client.get_commit_message(revisions)

        self.assertEquals(commit_message['summary'], 'commit 1')

    def test_guess_summary_description_two(self):
        """Testing MercurialClient guess summary & description 2 commits."""
        self.options.guess_summary = True
        self.options.guess_description = True

        self._hg_add_file_commit('foo.txt', FOO1, 'summary 1\n\nbody 1')
        self._hg_add_file_commit('foo.txt', FOO2, 'summary 2\n\nbody 2')

        revisions = self.client.parse_revision_spec([])
        commit_message = self.client.get_commit_message(revisions)

        self.assertEquals(commit_message['summary'], 'summary 1')
        self.assertEquals(commit_message['description'],
                          'body 1\n\nsummary 2\n\nbody 2')

    def test_guess_summary_description_three(self):
        """Testing MercurialClient guess summary & description 3 commits."""
        self.options.guess_summary = True
        self.options.guess_description = True

        self._hg_add_file_commit('foo.txt', FOO1, 'commit 1\n\ndesc1')
        self._hg_add_file_commit('foo.txt', FOO2, 'commit 2\n\ndesc2')
        self._hg_add_file_commit('foo.txt', FOO3, 'commit 3\n\ndesc3')

        revisions = self.client.parse_revision_spec([])
        commit_message = self.client.get_commit_message(revisions)

        self.assertEquals(commit_message['summary'], 'commit 1')
        self.assertEquals(commit_message['description'],
                          'desc1\n\ncommit 2\n\ndesc2\n\ncommit 3\n\ndesc3')

    def test_guess_summary_description_one_middle(self):
        """Testing MercurialClient guess summary & description middle commit
        commit."""
        self.options.guess_summary = True
        self.options.guess_description = True

        self._hg_add_file_commit('foo.txt', FOO1, 'commit 1\n\ndesc1')
        self._hg_add_file_commit('foo.txt', FOO2, 'commit 2\n\ndesc2')
        tip = self._hg_get_tip()
        self._hg_add_file_commit('foo.txt', FOO3, 'commit 3\n\ndesc3')

        revisions = self.client.parse_revision_spec([tip])
        commit_message = self.client.get_commit_message(revisions)

        self.assertEquals(commit_message['summary'], 'commit 2')
        self.assertEquals(commit_message['description'], 'desc2')


class MercurialSubversionClientTests(MercurialTestBase):
    TESTSERVER = "http://127.0.0.1:8080"

    def __init__(self, *args, **kwargs):
        self._tmpbase = ''
        self.clone_dir = ''
        self.svn_repo = ''
        self.svn_checkout = ''
        self.client = None
        self._svnserve_pid = 0
        self._max_svnserve_pid_tries = 12
        self._svnserve_port = os.environ.get('SVNSERVE_PORT')
        self._required_exes = ('svnadmin', 'svnserve', 'svn')
        MercurialTestBase.__init__(self, *args, **kwargs)

    def setUp(self):
        super(MercurialSubversionClientTests, self).setUp()
        self._hg_env = {'FOO': 'BAR'}

        # Make sure hgsubversion is enabled.
        #
        # This will modify the .hgrc in the temp home directory created
        # for these tests.
        #
        # The "hgsubversion =" tells Mercurial to check for hgsubversion
        # in the default PYTHONPATH.
        fp = open('%s/.hgrc' % os.environ['HOME'], 'w')
        fp.write('[extensions]\n')
        fp.write('hgsubversion =\n')
        fp.close()

        for exe in self._required_exes:
            if not self.is_exe_in_path(exe):
                raise SkipTest('missing svn stuff!  giving up!')

        if not self._has_hgsubversion():
            raise SkipTest('unable to use `hgsubversion` extension!  '
                           'giving up!')

        if not self._tmpbase:
            self._tmpbase = self.create_tmp_dir()

        self._create_svn_repo()
        self._fire_up_svnserve()
        self._fill_in_svn_repo()

        try:
            self._get_testing_clone()
        except (OSError, IOError):
            msg = 'could not clone from svn repo!  skipping...'
            raise SkipTest(msg), None, sys.exc_info()[2]

        self._spin_up_client()
        self._stub_in_config_and_options()

    def _has_hgsubversion(self):
        output = self._run_hg(['svn', '--help'],
                              ignore_errors=True, extra_ignore_errors=(255))

        return not re.search("unknown command ['\"]svn['\"]", output, re.I)

    def tearDown(self):
        super(MercurialSubversionClientTests, self).tearDown()

        os.kill(self._svnserve_pid, 9)

    def _svn_add_file_commit(self, filename, data, msg, add_file=True):
        outfile = open(filename, 'w')
        outfile.write(data)
        outfile.close()

        if add_file:
            execute(['svn', 'add', filename], ignore_errors=True)

        execute(['svn', 'commit', '-m', msg])

    def _create_svn_repo(self):
        self.svn_repo = os.path.join(self._tmpbase, 'svnrepo')
        execute(['svnadmin', 'create', self.svn_repo])

    def _fire_up_svnserve(self):
        if not self._svnserve_port:
            self._svnserve_port = str(randint(30000, 40000))

        pid_file = os.path.join(self._tmpbase, 'svnserve.pid')
        execute(['svnserve', '--pid-file', pid_file, '-d',
                 '--listen-port', self._svnserve_port, '-r', self._tmpbase])

        for i in range(0, self._max_svnserve_pid_tries):
            try:
                self._svnserve_pid = int(open(pid_file).read().strip())
                return

            except (IOError, OSError):
                time.sleep(0.25)

        # This will re-raise the last exception, which will be either
        # IOError or OSError if the above fails and this branch is reached
        raise

    def _fill_in_svn_repo(self):
        self.svn_checkout = os.path.join(self._tmpbase, 'checkout.svn')
        execute(['svn', 'checkout', 'file://%s' % self.svn_repo,
                 self.svn_checkout])
        os.chdir(self.svn_checkout)

        for subtree in ('trunk', 'branches', 'tags'):
            execute(['svn', 'mkdir', subtree])

        execute(['svn', 'commit', '-m', 'filling in T/b/t'])
        os.chdir(os.path.join(self.svn_checkout, 'trunk'))

        for i, data in enumerate([FOO, FOO1, FOO2]):
            self._svn_add_file_commit('foo.txt', data, 'foo commit %s' % i,
                                      add_file=(i == 0))

    def _get_testing_clone(self):
        self.clone_dir = os.path.join(self._tmpbase, 'checkout.hg')
        self._run_hg([
            'clone', 'svn://127.0.0.1:%s/svnrepo' % self._svnserve_port,
            self.clone_dir,
        ])

    def _spin_up_client(self):
        os.chdir(self.clone_dir)
        self.client = MercurialClient(options=self.options)

    def _stub_in_config_and_options(self):
        self.user_config = {}
        self.configs = []
        self.client.user_config = self.user_config
        self.client.configs = self.configs
        self.options.parent_branch = None

    def testGetRepositoryInfoSimple(self):
        """Testing MercurialClient (+svn) get_repository_info, simple case"""
        ri = self.client.get_repository_info()

        self.assertEqual('svn', self.client._type)
        self.assertEqual('/trunk', ri.base_path)
        self.assertEqual('svn://127.0.0.1:%s/svnrepo' % self._svnserve_port,
                         ri.path)

    def testCalculateRepositoryInfo(self):
        """
        Testing MercurialClient (+svn) _calculate_hgsubversion_repository_info properly determines repository and base paths.
        """
        info = (
            "URL: svn+ssh://testuser@svn.example.net/repo/trunk\n"
            "Repository Root: svn+ssh://testuser@svn.example.net/repo\n"
            "Repository UUID: bfddb570-5023-0410-9bc8-bc1659bf7c01\n"
            "Revision: 9999\n"
            "Node Kind: directory\n"
            "Last Changed Author: user\n"
            "Last Changed Rev: 9999\n"
            "Last Changed Date: 2012-09-05 18:04:28 +0000 (Wed, 05 Sep 2012)")

        repo_info = self.client._calculate_hgsubversion_repository_info(info)

        self.assertEqual(repo_info.path, "svn+ssh://svn.example.net/repo")
        self.assertEqual(repo_info.base_path, "/trunk")

    def testScanForServerSimple(self):
        """Testing MercurialClient (+svn) scan_for_server, simple case"""
        ri = self.client.get_repository_info()
        server = self.client.scan_for_server(ri)

        self.assertTrue(server is None)

    def testScanForServerReviewboardrc(self):
        """Testing MercurialClient (+svn) scan_for_server in .reviewboardrc"""
        rc_filename = os.path.join(self.clone_dir, '.reviewboardrc')
        rc = open(rc_filename, 'w')
        rc.write('REVIEWBOARD_URL = "%s"' % self.TESTSERVER)
        rc.close()
        self.client.user_config, configs = load_config_files(self.clone_dir)

        ri = self.client.get_repository_info()
        server = self.client.scan_for_server(ri)

        self.assertEqual(self.TESTSERVER, server)

    def testScanForServerProperty(self):
        """Testing MercurialClient (+svn) scan_for_server in svn property"""
        os.chdir(self.svn_checkout)
        execute(['svn', 'update'])
        execute(['svn', 'propset', 'reviewboard:url', self.TESTSERVER,
                 self.svn_checkout])
        execute(['svn', 'commit', '-m', 'adding reviewboard:url property'])

        os.chdir(self.clone_dir)
        self._run_hg(['pull'])
        self._run_hg(['update', '-C'])

        ri = self.client.get_repository_info()

        self.assertEqual(self.TESTSERVER, self.client.scan_for_server(ri))

    def testDiffSimple(self):
        """Testing MercurialClient (+svn) diff, simple case"""
        self.client.get_repository_info()

        self._hg_add_file_commit('foo.txt', FOO4, 'edit 4')

        revisions = self.client.parse_revision_spec([])
        result = self.client.diff(revisions)
        self.assertTrue(isinstance(result, dict))
        self.assertTrue('diff' in result)
        self.assertEqual(md5(result['diff']).hexdigest(),
                         '2eb0a5f2149232c43a1745d90949fcd5')
        self.assertEqual(result['parent_diff'], None)

    def testDiffSimpleMultiple(self):
        """Testing MercurialClient (+svn) diff with multiple commits"""
        self.client.get_repository_info()

        self._hg_add_file_commit('foo.txt', FOO4, 'edit 4')
        self._hg_add_file_commit('foo.txt', FOO5, 'edit 5')
        self._hg_add_file_commit('foo.txt', FOO6, 'edit 6')

        revisions = self.client.parse_revision_spec([])
        result = self.client.diff(revisions)
        self.assertTrue(isinstance(result, dict))
        self.assertTrue('diff' in result)
        self.assertEqual(md5(result['diff']).hexdigest(),
                         '3d007394de3831d61e477cbcfe60ece8')
        self.assertEqual(result['parent_diff'], None)

    def testDiffOfRevision(self):
        """Testing MercurialClient (+svn) diff specifying a revision."""
        self.client.get_repository_info()

        self._hg_add_file_commit('foo.txt', FOO4, 'edit 4', branch='b')
        self._hg_add_file_commit('foo.txt', FOO5, 'edit 5', branch='b')
        self._hg_add_file_commit('foo.txt', FOO6, 'edit 6', branch='b')
        self._hg_add_file_commit('foo.txt', FOO4, 'edit 7', branch='b')

        revisions = self.client.parse_revision_spec(['3'])
        result = self.client.diff(revisions)
        self.assertTrue(isinstance(result, dict))
        self.assertTrue('diff' in result)
        self.assertEqual(md5(result['diff']).hexdigest(),
                         '2eb0a5f2149232c43a1745d90949fcd5')
        self.assertEqual(result['parent_diff'], None)


class SVNClientTests(SCMClientTests):
    def setUp(self):
        super(SVNClientTests, self).setUp()

        if not self.is_exe_in_path('svn'):
            raise SkipTest('svn not found in path')

        self.svn_dir = os.path.join(self.clients_dir, 'testdata', 'svn-repo')
        self.clone_dir = self.chdir_tmp()
        self._run_svn(['co', 'file://' + self.svn_dir, 'svn-repo'])
        os.chdir(os.path.join(self.clone_dir, 'svn-repo'))

        self.client = SVNClient(options=self.options)

    def _run_svn(self, command):
        return execute(['svn'] + command, env=None, split_lines=False,
                       ignore_errors=False, extra_ignore_errors=(),
                       translate_newlines=True)


    def _svn_add_file(self, filename, data, changelist=None):
        """Add a file to the test repo."""
        is_new = not os.path.exists(filename)

        f = open(filename, 'w')
        f.write(data)
        f.close()
        if is_new:
            self._run_svn(['add', filename])

        if changelist:
            self._run_svn(['changelist', changelist, filename])

    def test_relative_paths(self):
        """Testing SVNRepositoryInfo._get_relative_path"""
        info = SVNRepositoryInfo('http://svn.example.com/svn/', '/', '')
        self.assertEqual(info._get_relative_path('/foo', '/bar'), None)
        self.assertEqual(info._get_relative_path('/', '/trunk/myproject'),
                         None)
        self.assertEqual(info._get_relative_path('/trunk/myproject', '/'),
                         '/trunk/myproject')
        self.assertEqual(
            info._get_relative_path('/trunk/myproject', ''),
            '/trunk/myproject')
        self.assertEqual(
            info._get_relative_path('/trunk/myproject', '/trunk'),
            '/myproject')
        self.assertEqual(
            info._get_relative_path('/trunk/myproject', '/trunk/myproject'),
            '/')

    def test_parse_revision_spec_no_args(self):
        """Testing SVNClient.parse_revision_spec with no specified revisions"""
        revisions = self.client.parse_revision_spec()
        self.assertTrue(isinstance(revisions, dict))
        self.assertTrue('base' in revisions)
        self.assertTrue('tip' in revisions)
        self.assertTrue('parent_base' not in revisions)
        self.assertEqual(revisions['base'], 'BASE')
        self.assertEqual(revisions['tip'], '--rbtools-working-copy')

    def test_parse_revision_spec_one_revision(self):
        """Testing SVNClient.parse_revision_spec with one specified numeric revision"""
        revisions = self.client.parse_revision_spec(['3'])
        self.assertTrue(isinstance(revisions, dict))
        self.assertTrue('base' in revisions)
        self.assertTrue('tip' in revisions)
        self.assertTrue('parent_base' not in revisions)
        self.assertEqual(revisions['base'], 2)
        self.assertEqual(revisions['tip'], 3)

    def test_parse_revision_spec_one_revision_changelist(self):
        """Testing SVNClient.parse_revision_spec with one specified changelist revision"""
        self._svn_add_file('foo.txt', FOO3, 'my-change')

        revisions = self.client.parse_revision_spec(['my-change'])
        self.assertTrue(isinstance(revisions, dict))
        self.assertTrue('base' in revisions)
        self.assertTrue('tip' in revisions)
        self.assertTrue('parent_base' not in revisions)
        self.assertEqual(revisions['base'], 'BASE')
        self.assertEqual(revisions['tip'],
                         SVNClient.REVISION_CHANGELIST_PREFIX + 'my-change')

    def test_parse_revision_spec_one_revision_nonexistant_changelist(self):
        """Testing SVNClient.parse_revision_spec with one specified invalid changelist revision"""
        self._svn_add_file('foo.txt', FOO3, 'my-change')

        self.assertRaises(
            InvalidRevisionSpecError,
            lambda: self.client.parse_revision_spec(['not-my-change']))

    def test_parse_revision_spec_one_arg_two_revisions(self):
        """Testing SVNClient.parse_revision_spec with R1:R2 syntax"""
        revisions = self.client.parse_revision_spec(['1:3'])
        self.assertTrue(isinstance(revisions, dict))
        self.assertTrue('base' in revisions)
        self.assertTrue('tip' in revisions)
        self.assertTrue('parent_base' not in revisions)
        self.assertEqual(revisions['base'], 1)
        self.assertEqual(revisions['tip'], 3)

    def test_parse_revision_spec_two_arguments(self):
        """Testing SVNClient.parse_revision_spec with two revisions"""
        revisions = self.client.parse_revision_spec(['1', '3'])
        self.assertTrue(isinstance(revisions, dict))
        self.assertTrue('base' in revisions)
        self.assertTrue('tip' in revisions)
        self.assertTrue('parent_base' not in revisions)
        self.assertEqual(revisions['base'], 1)
        self.assertEqual(revisions['tip'], 3)

    def test_parse_revision_spec_one_revision_url(self):
        """Testing SVNClient.parse_revision_spec with one revision and a repository URL"""
        self.options.repository_url = \
            'http://svn.apache.org/repos/asf/subversion/trunk'

        revisions = self.client.parse_revision_spec(['1549823'])
        self.assertTrue(isinstance(revisions, dict))
        self.assertTrue('base' in revisions)
        self.assertTrue('tip' in revisions)
        self.assertTrue('parent_base' not in revisions)
        self.assertEqual(revisions['base'], 1549822)
        self.assertEqual(revisions['tip'], 1549823)


    def test_parse_revision_spec_two_revisions_url(self):
        """Testing SVNClient.parse_revision_spec with R1:R2 syntax and a repository URL"""
        self.options.repository_url = \
            'http://svn.apache.org/repos/asf/subversion/trunk'

        revisions = self.client.parse_revision_spec(['1549823:1550211'])
        self.assertTrue(isinstance(revisions, dict))
        self.assertTrue('base' in revisions)
        self.assertTrue('tip' in revisions)
        self.assertTrue('parent_base' not in revisions)
        self.assertEqual(revisions['base'], 1549823)
        self.assertEqual(revisions['tip'], 1550211)


class P4WrapperTests(RBTestBase):
    def is_supported(self):
        return True

    def test_counters(self):
        """Testing P4Wrapper.counters"""
        class TestWrapper(P4Wrapper):
            def run_p4(self, cmd, *args, **kwargs):
                return [
                    'a = 1\n',
                    'b = 2\n',
                    'c = 3\n',
                ]

        p4 = TestWrapper(None)
        info = p4.counters()

        self.assertEqual(len(info), 3)
        self.assertEqual(info['a'], '1')
        self.assertEqual(info['b'], '2')
        self.assertEqual(info['c'], '3')

    def test_info(self):
        """Testing P4Wrapper.info"""
        class TestWrapper(P4Wrapper):
            def run_p4(self, cmd, *args, **kwargs):
                return [
                    'User name: myuser\n',
                    'Client name: myclient\n',
                    'Client host: myclient.example.com\n',
                    'Client root: /path/to/client\n',
                    'Server uptime: 111:43:38\n',
                ]

        p4 = TestWrapper(None)
        info = p4.info()

        self.assertEqual(len(info), 5)
        self.assertEqual(info['User name'], 'myuser')
        self.assertEqual(info['Client name'], 'myclient')
        self.assertEqual(info['Client host'], 'myclient.example.com')
        self.assertEqual(info['Client root'], '/path/to/client')
        self.assertEqual(info['Server uptime'], '111:43:38')


class PerforceClientTests(SCMClientTests):
    class P4DiffTestWrapper(P4Wrapper):
        def __init__(self, options):
            super(PerforceClientTests.P4DiffTestWrapper, self).__init__(options)

            self._timestamp = time.mktime(time.gmtime(0))

        def fstat(self, depot_path, fields=[]):
            assert depot_path in self.fstat_files

            fstat_info = self.fstat_files[depot_path]

            for field in fields:
                assert field in fstat_info

            return fstat_info

        def opened(self, changenum):
            return [info for info in self.repo_files
                    if info['change'] == changenum]

        def print_file(self, depot_path, out_file):
            for info in self.repo_files:
                if depot_path == '%s#%s' % (info['depotFile'], info['rev']):
                    fp = open(out_file, 'w')
                    fp.write(info['text'])
                    fp.close()
                    return
            assert False

        def where(self, depot_path):
            assert depot_path in self.where_files

            return [{
                'path': self.where_files[depot_path],
            }]

        def change(self, changenum):
            return [{
                'Change': str(changenum),
                'Date': '2013/01/02 22:33:44',
                'User': 'joe@example.com',
                'Status': 'pending',
                'Description': 'This is a test.\n',
            }]

        def run_p4(self, *args, **kwargs):
            assert False

    def test_scan_for_server_counter_with_reviewboard_url(self):
        """Testing PerforceClient.scan_for_server_counter with reviewboard.url"""
        RB_URL = 'http://reviewboard.example.com/'

        class TestWrapper(P4Wrapper):
            def counters(self):
                return {
                    'reviewboard.url': RB_URL,
                    'foo': 'bar',
                }

        client = PerforceClient(TestWrapper)
        url = client.scan_for_server_counter(None)

        self.assertEqual(url, RB_URL)

    def test_repository_info(self):
        """Testing PerforceClient.get_repository_info"""
        SERVER_PATH = 'perforce.example.com:1666'

        class TestWrapper(P4Wrapper):
            def is_supported(self):
                return True

            def info(self):
                return {
                    'Client root': os.getcwd(),
                    'Server address': SERVER_PATH,
                    'Server version': 'P4D/FREEBSD60X86_64/2012.2/525804 '
                                      '(2012/09/18)',
                }

        client = PerforceClient(TestWrapper)
        info = client.get_repository_info()

        self.assertNotEqual(info, None)
        self.assertEqual(info.path, SERVER_PATH)
        self.assertEqual(client.p4d_version, (2012, 2))

    def test_repository_info_outside_client_root(self):
        """Testing PerforceClient.get_repository_info outside client root"""
        SERVER_PATH = 'perforce.example.com:1666'

        class TestWrapper(P4Wrapper):
            def is_supported(self):
                return True

            def info(self):
                return {
                    'Client root': '/',
                    'Server address': SERVER_PATH,
                    'Server version': 'P4D/FREEBSD60X86_64/2012.2/525804 '
                                      '(2012/09/18)',
                }

        client = PerforceClient(TestWrapper)
        info = client.get_repository_info()

        self.assertEqual(info, None)

    def test_scan_for_server_counter_with_reviewboard_url_encoded(self):
        """Testing PerforceClient.scan_for_server_counter with encoded reviewboard.url.http:||"""
        URL_KEY = 'reviewboard.url.http:||reviewboard.example.com/'
        RB_URL = 'http://reviewboard.example.com/'

        class TestWrapper(P4Wrapper):
            def counters(self):
                return {
                    URL_KEY: '1',
                    'foo': 'bar',
                }

        client = PerforceClient(TestWrapper)
        url = client.scan_for_server_counter(None)

        self.assertEqual(url, RB_URL)

    def test_diff_with_changenum(self):
        """Testing PerforceClient.diff with changenums"""
        client = self._build_client()
        client.p4.repo_files = [
            {
                'depotFile': '//mydepot/test/README',
                'rev': '2',
                'action': 'edit',
                'change': '12345',
                'text': 'This is a test.\n',
            },
            {
                'depotFile': '//mydepot/test/README',
                'rev': '3',
                'action': 'edit',
                'change': '',
                'text': 'This is a mess.\n',
            },
            {
                'depotFile': '//mydepot/test/COPYING',
                'rev': '1',
                'action': 'add',
                'change': '12345',
                'text': 'Copyright 2013 Joe User.\n',
            },
            {
                'depotFile': '//mydepot/test/Makefile',
                'rev': '3',
                'action': 'delete',
                'change': '12345',
                'text': 'all: all\n',
            },
        ]

        readme_file = make_tempfile()
        copying_file = make_tempfile()
        makefile_file = make_tempfile()
        client.p4.print_file('//mydepot/test/README#3', readme_file)
        client.p4.print_file('//mydepot/test/COPYING#1', copying_file)

        client.p4.where_files = {
            '//mydepot/test/README': readme_file,
            '//mydepot/test/COPYING': copying_file,
            '//mydepot/test/Makefile': makefile_file,
        }

        revisions = client.parse_revision_spec(['12345'])
        diff = client.diff(revisions)
        self._compare_diff(diff, '07aa18ff67f9aa615fcda7ecddcb354e')

    def test_diff_with_moved_files_cap_on(self):
        """Testing PerforceClient.diff with moved files and capability on"""
        self._test_diff_with_moved_files(
            '5926515eaf4cf6d8257a52f7d9f0e530',
            caps={
                'scmtools': {
                    'perforce': {
                        'moved_files': True
                    }
                }
            })

    def test_diff_with_moved_files_cap_off(self):
        """Testing PerforceClient.diff with moved files and capability off"""
        self._test_diff_with_moved_files('20e5ab395e170dce1b062a796e6c2c13')

    def _test_diff_with_moved_files(self, expected_diff_hash, caps={}):
        client = self._build_client()
        client.capabilities = Capabilities(caps)
        client.p4.repo_files = [
            {
                'depotFile': '//mydepot/test/README',
                'rev': '2',
                'action': 'move/delete',
                'change': '12345',
                'text': 'This is a test.\n',
            },
            {
                'depotFile': '//mydepot/test/README-new',
                'rev': '1',
                'action': 'move/add',
                'change': '12345',
                'text': 'This is a mess.\n',
            },
            {
                'depotFile': '//mydepot/test/COPYING',
                'rev': '2',
                'action': 'move/delete',
                'change': '12345',
                'text': 'Copyright 2013 Joe User.\n',
            },
            {
                'depotFile': '//mydepot/test/COPYING-new',
                'rev': '1',
                'action': 'move/add',
                'change': '12345',
                'text': 'Copyright 2013 Joe User.\n',
            },
        ]

        readme_file = make_tempfile()
        copying_file = make_tempfile()
        readme_file_new = make_tempfile()
        copying_file_new = make_tempfile()
        client.p4.print_file('//mydepot/test/README#2', readme_file)
        client.p4.print_file('//mydepot/test/COPYING#2', copying_file)
        client.p4.print_file('//mydepot/test/README-new#1', readme_file_new)
        client.p4.print_file('//mydepot/test/COPYING-new#1', copying_file_new)

        client.p4.where_files = {
            '//mydepot/test/README': readme_file,
            '//mydepot/test/COPYING': copying_file,
            '//mydepot/test/README-new': readme_file_new,
            '//mydepot/test/COPYING-new': copying_file_new,
        }

        client.p4.fstat_files = {
            '//mydepot/test/README': {
                'clientFile': readme_file,
                'movedFile': '//mydepot/test/README-new',
            },
            '//mydepot/test/README-new': {
                'clientFile': readme_file_new,
                'depotFile': '//mydepot/test/README-new',
            },
            '//mydepot/test/COPYING': {
                'clientFile': copying_file,
                'movedFile': '//mydepot/test/COPYING-new',
            },
            '//mydepot/test/COPYING-new': {
                'clientFile': copying_file_new,
                'depotFile': '//mydepot/test/COPYING-new',
            },
        }

        revisions = client.parse_revision_spec(['12345'])
        diff = client.diff(revisions)
        self._compare_diff(diff, expected_diff_hash)

    def _build_client(self):
        self.options.p4_client = 'myclient'
        self.options.p4_port = 'perforce.example.com:1666'
        self.options.p4_passwd = ''
        client = PerforceClient(self.P4DiffTestWrapper, options=self.options)
        client.p4d_version = (2012, 2)
        return client

    def _compare_diff(self, diff_info, expected_diff_hash):
        self.assertTrue(isinstance(diff_info, dict))
        self.assertTrue('diff' in diff_info)
        self.assertTrue('changenum' in diff_info)

        diff_content = re.sub('\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}',
                              '1970-01-01 00:00:00',
                              diff_info['diff'])
        print diff_content
        self.assertEqual(md5(diff_content).hexdigest(), expected_diff_hash)

    def test_parse_revision_spec_no_args(self):
        """Testing PerforceClient.parse_revision_spec with no specified revisions"""
        client = self._build_client()

        revisions = client.parse_revision_spec()
        self.assertTrue(isinstance(revisions, dict))
        self.assertTrue('base' in revisions)
        self.assertTrue('tip' in revisions)
        self.assertEqual(
            revisions['base'], PerforceClient.REVISION_CURRENT_SYNC)
        self.assertEqual(
            revisions['tip'],
            PerforceClient.REVISION_PENDING_CLN_PREFIX + 'default')

    def test_parse_revision_spec_pending_cln(self):
        """Testing PerforceClient.parse_revision_spec with a pending changelist"""
        class TestWrapper(P4Wrapper):
            def change(self, changelist):
                return [{
                    'Change': '12345',
                    'Date': '2013/12/19 11:32:45',
                    'User': 'example',
                    'Status': 'pending',
                    'Description': 'My change description\n',
                }]
        client = PerforceClient(TestWrapper)

        revisions = client.parse_revision_spec(['12345'])
        self.assertTrue(isinstance(revisions, dict))
        self.assertTrue('base' in revisions)
        self.assertTrue('tip' in revisions)
        self.assertTrue('parent_base' not in revisions)
        self.assertEqual(
            revisions['base'], PerforceClient.REVISION_CURRENT_SYNC)
        self.assertEqual(
            revisions['tip'],
            PerforceClient.REVISION_PENDING_CLN_PREFIX + '12345')

    def test_parse_revision_spec_submitted_cln(self):
        """Testing PerforceClient.parse_revision_spec with a submitted changelist"""
        class TestWrapper(P4Wrapper):
            def change(self, changelist):
                return [{
                    'Change': '12345',
                    'Date': '2013/12/19 11:32:45',
                    'User': 'example',
                    'Status': 'submitted',
                    'Description': 'My change description\n',
                }]

        client = PerforceClient(TestWrapper)

        revisions = client.parse_revision_spec(['12345'])
        self.assertTrue(isinstance(revisions, dict))
        self.assertTrue('base' in revisions)
        self.assertTrue('tip' in revisions)
        self.assertTrue('parent_base' not in revisions)
        self.assertEqual(revisions['base'], '12344')
        self.assertEqual(revisions['tip'], '12345')

    def test_parse_revision_spec_shelved_cln(self):
        """Testing PerforceClient.parse_revision_spec with a shelved changelist"""
        class TestWrapper(P4Wrapper):
            def change(self, changelist):
                return [{
                    'Change': '12345',
                    'Date': '2013/12/19 11:32:45',
                    'User': 'example',
                    'Status': 'shelved',
                    'Description': 'My change description\n',
                }]
        client = PerforceClient(TestWrapper)

        revisions = client.parse_revision_spec(['12345'])
        self.assertTrue(isinstance(revisions, dict))
        self.assertTrue('base' in revisions)
        self.assertTrue('tip' in revisions)
        self.assertTrue('parent_base' not in revisions)
        self.assertEqual(
            revisions['base'], PerforceClient.REVISION_CURRENT_SYNC)
        self.assertEqual(
            revisions['tip'],
            PerforceClient.REVISION_PENDING_CLN_PREFIX + '12345')

    def test_parse_revision_spec_two_args(self):
        class TestWrapper(P4Wrapper):
            def change(self, changelist):
                change = {
                    'Change': str(changelist),
                    'Date': '2013/12/19 11:32:45',
                    'User': 'example',
                    'Description': 'My change description\n',
                }

                if changelist == '99' or changelist == '100':
                    change['Status'] = 'submitted'
                elif changelist == '101':
                    change['Status'] = 'pending'
                elif changelist == '102':
                    change['Status'] = 'shelved'
                else:
                    assert False

                return [change]

        client = PerforceClient(TestWrapper)

        revisions = client.parse_revision_spec(['99', '100'])
        self.assertTrue(isinstance(revisions, dict))
        self.assertTrue('base' in revisions)
        self.assertTrue('tip' in revisions)
        self.assertTrue('parent_base' not in revisions)
        self.assertEqual(revisions['base'], '99')
        self.assertEqual(revisions['tip'], '100')

        self.assertRaises(InvalidRevisionSpecError,
                          lambda: client.parse_revision_spec(['99', '101']))
        self.assertRaises(InvalidRevisionSpecError,
                          lambda: client.parse_revision_spec(['99', '102']))
        self.assertRaises(InvalidRevisionSpecError,
                          lambda: client.parse_revision_spec(['101', '100']))
        self.assertRaises(InvalidRevisionSpecError,
                          lambda: client.parse_revision_spec(['102', '100']))
        self.assertRaises(InvalidRevisionSpecError,
                          lambda: client.parse_revision_spec(['102', '10284']))


class BazaarClientTests(SCMClientTests):
    def setUp(self):
        super(BazaarClientTests, self).setUp()

        if not self.is_exe_in_path("bzr"):
            raise SkipTest("bzr not found in path")

        self.set_user_home(os.path.join(self.clients_dir, 'testdata', 'homedir'))

        self.orig_dir = os.getcwd()

        self.original_branch = self.chdir_tmp()
        self._run_bzr(["init", "."])
        self._bzr_add_file_commit("foo.txt", FOO, "initial commit")

        self.child_branch = mktemp()
        self._run_bzr(["branch", self.original_branch, self.child_branch])
        self.client = BazaarClient(options=self.options)
        os.chdir(self.orig_dir)

        self.user_config = {}
        self.configs = []
        self.client.user_config = self.user_config
        self.client.configs = self.configs
        self.options.parent_branch = None

    def _run_bzr(self, command, *args, **kwargs):
        return execute(['bzr'] + command, *args, **kwargs)

    def _bzr_add_file_commit(self, file, data, msg):
        """
        Add a file to a Bazaar repository with the content of data and commit
        with msg.
        """
        foo = open(file, "w")
        foo.write(data)
        foo.close()
        self._run_bzr(["add", file])
        self._run_bzr(["commit", "-m", msg, '--author', 'Test User'])

    def _bzr_get_revno(self, revision_spec=None):
        command = ['revno']
        if revision_spec:
            command += ['-r', revision_spec]

        result = self._run_bzr(command).strip().split('\n')

        if len(result) == 1:
            return 'revno:' + result[0]
        elif len(result) == 2 and result[0].startswith(BZR_USING_PARENT_PREFIX):
            branch = result[0][len(BZR_USING_PARENT_PREFIX):]
            return 'revno:%s:%s' % (result[1], branch)

    def _compare_diffs(self, filename, full_diff, expected_diff_digest):
        """
        Testing that the full_diff for ``filename`` matches the ``expected_diff``.
        """
        diff_lines = full_diff.splitlines()

        self.assertEqual("=== modified file %r" % filename, diff_lines[0])
        self.assertTrue(diff_lines[1].startswith("--- %s\t" % filename))
        self.assertTrue(diff_lines[2].startswith("+++ %s\t" % filename))

        diff_body = "\n".join(diff_lines[3:])
        self.assertEqual(md5(diff_body).hexdigest(), expected_diff_digest)

    def test_get_repository_info_original_branch(self):
        """Testing BazaarClient get_repository_info with original branch"""
        os.chdir(self.original_branch)
        ri = self.client.get_repository_info()

        self.assertTrue(isinstance(ri, RepositoryInfo))
        self.assertEqual(os.path.realpath(ri.path),
                         os.path.realpath(self.original_branch))
        self.assertTrue(ri.supports_parent_diffs)

        self.assertEqual(ri.base_path, "/")
        self.assertFalse(ri.supports_changesets)

    def test_get_repository_info_child_branch(self):
        """Testing BazaarClient get_repository_info with child branch"""
        os.chdir(self.child_branch)
        ri = self.client.get_repository_info()

        self.assertTrue(isinstance(ri, RepositoryInfo))
        self.assertEqual(os.path.realpath(ri.path),
                         os.path.realpath(self.child_branch))
        self.assertTrue(ri.supports_parent_diffs)

        self.assertEqual(ri.base_path, "/")
        self.assertFalse(ri.supports_changesets)

    def test_get_repository_info_no_branch(self):
        """Testing BazaarClient get_repository_info, no branch"""
        self.chdir_tmp()
        ri = self.client.get_repository_info()
        self.assertEqual(ri, None)

    def test_diff_simple(self):
        """Testing BazaarClient simple diff case"""
        os.chdir(self.child_branch)

        self._bzr_add_file_commit("foo.txt", FOO1, "delete and modify stuff")

        revisions = self.client.parse_revision_spec([])
        result = self.client.diff(revisions)
        self.assertTrue(isinstance(result, dict))
        self.assertTrue('diff' in result)

        self._compare_diffs('foo.txt', result['diff'],
                            'a6326b53933f8b255a4b840485d8e210')

    def test_diff_specific_files(self):
        """Testing BazaarClient diff with specific files"""
        os.chdir(self.child_branch)

        self._bzr_add_file_commit("foo.txt", FOO1, "delete and modify stuff")
        self._bzr_add_file_commit("bar.txt", "baz", "added bar")

        revisions = self.client.parse_revision_spec([])
        result = self.client.diff(revisions, ['foo.txt'])
        self.assertTrue(isinstance(result, dict))
        self.assertTrue('diff' in result)

        self._compare_diffs('foo.txt', result['diff'],
                            'a6326b53933f8b255a4b840485d8e210')

    def test_diff_simple_multiple(self):
        """Testing BazaarClient simple diff with multiple commits case"""
        os.chdir(self.child_branch)

        self._bzr_add_file_commit("foo.txt", FOO1, "commit 1")
        self._bzr_add_file_commit("foo.txt", FOO2, "commit 2")
        self._bzr_add_file_commit("foo.txt", FOO3, "commit 3")

        revisions = self.client.parse_revision_spec([])
        result = self.client.diff(revisions)
        self.assertTrue(isinstance(result, dict))
        self.assertTrue('diff' in result)

        self._compare_diffs('foo.txt', result['diff'],
                            '4109cc082dce22288c2f1baca9b107b6')

    def test_diff_parent(self):
        """Testing BazaarClient diff with changes only in the parent branch"""
        os.chdir(self.child_branch)
        self._bzr_add_file_commit("foo.txt", FOO1, "delete and modify stuff")

        grand_child_branch = mktemp()
        self._run_bzr(["branch", self.child_branch, grand_child_branch])
        os.chdir(grand_child_branch)

        revisions = self.client.parse_revision_spec([])
        result = self.client.diff(revisions)
        self.assertTrue(isinstance(result, dict))
        self.assertTrue('diff' in result)

        self.assertEqual(result['diff'], None)

    def test_diff_grand_parent(self):
        """Testing BazaarClient diff with changes between a 2nd level descendant"""
        os.chdir(self.child_branch)
        self._bzr_add_file_commit("foo.txt", FOO1, "delete and modify stuff")

        grand_child_branch = mktemp()
        self._run_bzr(["branch", self.child_branch, grand_child_branch])
        os.chdir(grand_child_branch)

        # Requesting the diff between the grand child branch and its grand
        # parent:
        self.options.parent_branch = self.original_branch

        revisions = self.client.parse_revision_spec([])
        result = self.client.diff(revisions)
        self.assertTrue(isinstance(result, dict))
        self.assertTrue('diff' in result)

        self._compare_diffs("foo.txt", result['diff'],
                            'a6326b53933f8b255a4b840485d8e210')

    def test_guessed_summary_and_description(self):
        """Testing BazaarClient guessing summary and description"""
        os.chdir(self.child_branch)

        self._bzr_add_file_commit("foo.txt", FOO1, "commit 1")
        self._bzr_add_file_commit("foo.txt", FOO2, "commit 2")
        self._bzr_add_file_commit("foo.txt", FOO3, "commit 3")

        self.options.guess_summary = True
        self.options.guess_description = True
        revisions = self.client.parse_revision_spec([])
        commit_message = self.client.get_commit_message(revisions)

        self.assertEquals("commit 3", commit_message['summary'])

        description = commit_message['description']
        self.assertTrue("commit 1" in description)
        self.assertTrue("commit 2" in description)
        self.assertFalse("commit 3" in description)

    def test_guessed_summary_and_description_in_grand_parent_branch(self):
        """
        Testing BazaarClient guessing summary and description for grand parent branch.
        """
        os.chdir(self.child_branch)

        self._bzr_add_file_commit("foo.txt", FOO1, "commit 1")
        self._bzr_add_file_commit("foo.txt", FOO2, "commit 2")
        self._bzr_add_file_commit("foo.txt", FOO3, "commit 3")

        self.options.guess_summary = True
        self.options.guess_description = True

        grand_child_branch = mktemp()
        self._run_bzr(["branch", self.child_branch, grand_child_branch])
        os.chdir(grand_child_branch)

        # Requesting the diff between the grand child branch and its grand
        # parent:
        self.options.parent_branch = self.original_branch

        revisions = self.client.parse_revision_spec([])
        commit_message = self.client.get_commit_message(revisions)

        self.assertEquals("commit 3", commit_message['summary'])

        description = commit_message['description']
        self.assertTrue("commit 1" in description)
        self.assertTrue("commit 2" in description)
        self.assertFalse("commit 3" in description)

    def test_guessed_summary_and_description_with_revision_range(self):
        """Testing BazaarClient guessing summary and description with a revision range."""
        os.chdir(self.child_branch)

        self._bzr_add_file_commit("foo.txt", FOO1, "commit 1")
        self._bzr_add_file_commit("foo.txt", FOO2, "commit 2")
        self._bzr_add_file_commit("foo.txt", FOO3, "commit 3")

        self.options.guess_summary = True
        self.options.guess_description = True
        revisions = self.client.parse_revision_spec(['2..3'])
        commit_message = self.client.get_commit_message(revisions)
        print commit_message

        self.assertEquals("commit 2", commit_message['summary'])
        self.assertEquals("commit 2", commit_message['description'])

    def test_parse_revision_spec_no_args(self):
        """Testing BazaarClient.parse_revision_spec with no specified revisions"""
        os.chdir(self.child_branch)

        base_commit_id = self._bzr_get_revno()
        self._bzr_add_file_commit("foo.txt", FOO1, "commit 1")
        tip_commit_id = self._bzr_get_revno()

        revisions = self.client.parse_revision_spec()
        self.assertTrue(isinstance(revisions, dict))
        self.assertTrue('base' in revisions)
        self.assertTrue('tip' in revisions)
        self.assertTrue('parent_base' not in revisions)
        self.assertEqual(revisions['base'], base_commit_id)
        self.assertEqual(revisions['tip'], tip_commit_id)

    def test_parse_revision_spec_one_arg(self):
        """Testing BazaarClient.parse_revision_spec with one specified revision"""
        os.chdir(self.child_branch)

        base_commit_id = self._bzr_get_revno()
        self._bzr_add_file_commit("foo.txt", FOO1, "commit 1")
        tip_commit_id = self._bzr_get_revno()

        revisions = self.client.parse_revision_spec([tip_commit_id])
        self.assertTrue(isinstance(revisions, dict))
        self.assertTrue('base' in revisions)
        self.assertTrue('tip' in revisions)
        self.assertTrue('parent_base' not in revisions)
        self.assertEqual(revisions['base'], base_commit_id)
        self.assertEqual(revisions['tip'], tip_commit_id)

    def test_parse_revision_spec_one_arg_parent(self):
        """Testing BazaarClient.parse_revision_spec with one specified revision and a parent diff"""
        os.chdir(self.original_branch)
        parent_base_commit_id = self._bzr_get_revno()

        grand_child_branch = mktemp()
        self._run_bzr(["branch", self.child_branch, grand_child_branch])
        os.chdir(grand_child_branch)

        base_commit_id = self._bzr_get_revno()
        self._bzr_add_file_commit("foo.txt", FOO2, "commit 2")
        tip_commit_id = self._bzr_get_revno()

        self.options.parent_branch = self.child_branch

        revisions = self.client.parse_revision_spec([tip_commit_id])
        self.assertTrue(isinstance(revisions, dict))
        self.assertTrue('parent_base' in revisions)
        self.assertTrue('base' in revisions)
        self.assertTrue('tip' in revisions)
        self.assertEqual(revisions['parent_base'], parent_base_commit_id)
        self.assertEqual(revisions['base'], base_commit_id)
        self.assertEqual(revisions['tip'], tip_commit_id)

    def test_parse_revision_spec_one_arg_split(self):
        """Testing BazaarClient.parse_revision_spec with R1..R2 syntax"""
        os.chdir(self.child_branch)

        self._bzr_add_file_commit("foo.txt", FOO1, "commit 1")
        base_commit_id = self._bzr_get_revno()
        self._bzr_add_file_commit("foo.txt", FOO2, "commit 2")
        tip_commit_id = self._bzr_get_revno()

        revisions = self.client.parse_revision_spec(
            ['%s..%s' % (base_commit_id, tip_commit_id)])
        self.assertTrue(isinstance(revisions, dict))
        self.assertTrue('parent_base' not in revisions)
        self.assertTrue('base' in revisions)
        self.assertTrue('tip' in revisions)
        self.assertEqual(revisions['base'], base_commit_id)
        self.assertEqual(revisions['tip'], tip_commit_id)

    def test_parse_revision_spec_two_args(self):
        """Testing BazaarClient.parse_revision_spec with two revisions"""
        os.chdir(self.child_branch)

        self._bzr_add_file_commit("foo.txt", FOO1, "commit 1")
        base_commit_id = self._bzr_get_revno()
        self._bzr_add_file_commit("foo.txt", FOO2, "commit 2")
        tip_commit_id = self._bzr_get_revno()

        revisions = self.client.parse_revision_spec(
            [base_commit_id, tip_commit_id])
        self.assertTrue(isinstance(revisions, dict))
        self.assertTrue('parent_base' not in revisions)
        self.assertTrue('base' in revisions)
        self.assertTrue('tip' in revisions)
        self.assertEqual(revisions['base'], base_commit_id)
        self.assertEqual(revisions['tip'], tip_commit_id)


FOO = """\
ARMA virumque cano, Troiae qui primus ab oris
Italiam, fato profugus, Laviniaque venit
litora, multum ille et terris iactatus et alto
vi superum saevae memorem Iunonis ob iram;
multa quoque et bello passus, dum conderet urbem,
inferretque deos Latio, genus unde Latinum,
Albanique patres, atque altae moenia Romae.
Musa, mihi causas memora, quo numine laeso,
quidve dolens, regina deum tot volvere casus
insignem pietate virum, tot adire labores
impulerit. Tantaene animis caelestibus irae?

"""

FOO1 = """\
ARMA virumque cano, Troiae qui primus ab oris
Italiam, fato profugus, Laviniaque venit
litora, multum ille et terris iactatus et alto
vi superum saevae memorem Iunonis ob iram;
multa quoque et bello passus, dum conderet urbem,
inferretque deos Latio, genus unde Latinum,
Albanique patres, atque altae moenia Romae.
Musa, mihi causas memora, quo numine laeso,

"""

FOO2 = """\
ARMA virumque cano, Troiae qui primus ab oris
ARMA virumque cano, Troiae qui primus ab oris
ARMA virumque cano, Troiae qui primus ab oris
Italiam, fato profugus, Laviniaque venit
litora, multum ille et terris iactatus et alto
vi superum saevae memorem Iunonis ob iram;
multa quoque et bello passus, dum conderet urbem,
inferretque deos Latio, genus unde Latinum,
Albanique patres, atque altae moenia Romae.
Musa, mihi causas memora, quo numine laeso,

"""

FOO3 = """\
ARMA virumque cano, Troiae qui primus ab oris
ARMA virumque cano, Troiae qui primus ab oris
Italiam, fato profugus, Laviniaque venit
litora, multum ille et terris iactatus et alto
vi superum saevae memorem Iunonis ob iram;
dum conderet urbem,
inferretque deos Latio, genus unde Latinum,
Albanique patres, atque altae moenia Romae.
Albanique patres, atque altae moenia Romae.
Musa, mihi causas memora, quo numine laeso,

"""

FOO4 = """\
Italiam, fato profugus, Laviniaque venit
litora, multum ille et terris iactatus et alto
vi superum saevae memorem Iunonis ob iram;
dum conderet urbem,





inferretque deos Latio, genus unde Latinum,
Albanique patres, atque altae moenia Romae.
Musa, mihi causas memora, quo numine laeso,

"""

FOO5 = """\
litora, multum ille et terris iactatus et alto
Italiam, fato profugus, Laviniaque venit
vi superum saevae memorem Iunonis ob iram;
dum conderet urbem,
Albanique patres, atque altae moenia Romae.
Albanique patres, atque altae moenia Romae.
Musa, mihi causas memora, quo numine laeso,
inferretque deos Latio, genus unde Latinum,

ARMA virumque cano, Troiae qui primus ab oris
ARMA virumque cano, Troiae qui primus ab oris
"""

FOO6 = """\
ARMA virumque cano, Troiae qui primus ab oris
ARMA virumque cano, Troiae qui primus ab oris
Italiam, fato profugus, Laviniaque venit
litora, multum ille et terris iactatus et alto
vi superum saevae memorem Iunonis ob iram;
dum conderet urbem, inferretque deos Latio, genus
unde Latinum, Albanique patres, atque altae
moenia Romae. Albanique patres, atque altae
moenia Romae. Musa, mihi causas memora, quo numine laeso,

"""

########NEW FILE########
__FILENAME__ = api_get
import re

try:
    import json
except ImportError:
    import simplejson as json

from rbtools.api.errors import APIError
from rbtools.commands import (Command,
                              CommandError,
                              CommandExit,
                              Option,
                              ParseError)


class APIGet(Command):
    name = 'api-get'
    author = 'The Review Board Project'
    description = 'Retrieve raw API resource payloads.'
    args = '<path> [-- [--<query-arg>=<value> ...]]'
    option_list = [
        Option("--pretty",
               action="store_true",
               dest="pretty_print",
               config_key="API_GET_PRETTY_PRINT",
               default=False,
               help="Pretty print output"),
        Command.server_options,
    ]

    def _dumps(self, payload):
        if self.options.pretty_print:
            return json.dumps(payload, sort_keys=True, indent=4)
        else:
            return json.dumps(payload)

    def main(self, path, *args):
        query_args = {}
        query_arg_re = re.compile('^--(?P<name>.*)=(?P<value>.*)$')

        for arg in args:
            m = query_arg_re.match(arg)

            if m:
                query_args[m.group('name')] = m.group('value')
            else:
                raise ParseError("Unexpected query argument %s" % arg)

        self.repository_info, self.tool = self.initialize_scm_tool()
        server_url = self.get_server_url(self.repository_info, self.tool)
        api_client, api_root = self.get_api(server_url)

        try:
            if path.startswith('http://') or path.startswith('https://'):
                resource = api_client.get_url(path, **query_args)
            else:
                resource = api_client.get_path(path, **query_args)
        except APIError, e:
            if e.rsp:
                print self._dumps(e.rsp)
                raise CommandExit(1)
            else:
                raise CommandError('Could not retrieve the requested '
                                   'resource: %s' % e)

        print self._dumps(resource.rsp)

########NEW FILE########
__FILENAME__ = attach
import os

from rbtools.api.errors import APIError
from rbtools.commands import Command, CommandError, Option


class Attach(Command):
    """Attach a file to a review request."""
    name = "attach"
    author = "The Review Board Project"
    args = "<review-request-id> <file>"
    option_list = [
        Option("--filename",
               dest="filename",
               default=None,
               help="custom filename for file attachment"),
        Option("--caption",
               dest="caption",
               default=None,
               help="caption for file attachment"),
        Command.server_options,
        Command.repository_options,
    ]

    def get_review_request(self, request_id, api_root):
        """Returns the review request resource for the given ID."""
        try:
            request = api_root.get_review_request(review_request_id=request_id)
        except APIError, e:
            raise CommandError("Error getting review request: %s" % e)

        return request

    def main(self, request_id, path_to_file):
        self.repository_info, self.tool = self.initialize_scm_tool(
            client_name=self.options.repository_type)
        server_url = self.get_server_url(self.repository_info, self.tool)
        api_client, api_root = self.get_api(server_url)

        request = self.get_review_request(request_id, api_root)

        try:
            f = open(path_to_file, 'r')
            content = f.read()
            f.close()
        except IOError:
            raise CommandError("%s is not a valid file." % path_to_file)

        # Check if the user specified a custom filename, otherwise
        # use the original filename.
        filename = self.options.filename or os.path.basename(path_to_file)

        try:
            request.get_file_attachments() \
                .upload_attachment(filename, content, self.options.caption)
        except APIError, e:
            raise CommandError("Error uploading file: %s" % e)

        print "Uploaded %s to review request %s." % (path_to_file, request_id)

########NEW FILE########
__FILENAME__ = close
from rbtools.api.errors import APIError
from rbtools.commands import Command, CommandError, Option


SUBMITTED = 'submitted'
DISCARDED = 'discarded'


class Close(Command):
    """Close a specific review request as discarded or submitted.

    By default, the command will change the status to submitted. The
    user can provide an optional description for this action.
    """
    name = "close"
    author = "The Review Board Project"
    args = "<review-request-id>"
    option_list = [
        Option("--close-type",
               dest="close_type",
               default=SUBMITTED,
               help="either submitted or discarded"),
        Option("--description",
               dest="description",
               default=None,
               help="optional description accompanied with change"),
        Command.server_options,
        Command.repository_options,
    ]

    def get_review_request(self, request_id, api_root):
        """Returns the review request resource for the given ID."""
        try:
            request = api_root.get_review_request(review_request_id=request_id)
        except APIError, e:
            raise CommandError("Error getting review request: %s" % e)

        return request

    def check_valid_type(self, close_type):
        """Check if the user specificed a proper type.

        Type must either be 'discarded' or 'submitted'. If the type
        is wrong, the command will stop and alert the user.
        """
        if close_type not in (SUBMITTED, DISCARDED):
            raise CommandError("%s is not valid type. Try '%s' or '%s'" % (
                self.options.close_type, SUBMITTED, DISCARDED))

    def main(self, request_id):
        """Run the command."""
        close_type = self.options.close_type
        self.check_valid_type(close_type)
        if self.options.server:
            # Bypass getting the scm_tool to discover the server since it was
            # specified with --server or in .reviewboardrc
            repository_info, tool = None, None
        else:
            repository_info, tool = self.initialize_scm_tool(
                client_name=self.options.repository_type)
        server_url = self.get_server_url(repository_info, tool)
        api_client, api_root = self.get_api(server_url)
        request = self.get_review_request(request_id, api_root)

        if request.status == close_type:
            raise CommandError("Review request #%s is already %s." % (
                request_id, close_type))

        if self.options.description:
            request = request.update(status=close_type,
                                     description=self.options.description)
        else:
            request = request.update(status=close_type)

        print "Review request #%s is set to %s." % (request_id, request.status)

########NEW FILE########
__FILENAME__ = diff
from rbtools.clients.errors import InvalidRevisionSpecError
from rbtools.commands import Command, CommandError, Option


class Diff(Command):
    """Prints a diff to the terminal."""
    name = "diff"
    author = "The Review Board Project"
    args = "[revisions]"
    option_list = [
        Command.server_options,
        Command.diff_options,
        Command.repository_options,
        Command.git_options,
        Command.perforce_options,
        Command.subversion_options,
    ]

    def main(self, *args):
        """Print the diff to terminal."""
        # The 'args' tuple must be made into a list for some of the
        # SCM Clients code. See comment in post.
        args = list(args)

        if self.options.revision_range:
            raise CommandError(
                'The --revision-range argument has been removed. To create a '
                'diff for one or more specific revisions, pass those '
                'revisions as arguments. For more information, see the '
                'RBTools 0.6 Release Notes.')

        if self.options.svn_changelist:
            raise CommandError(
                'The --svn-changelist argument has been removed. To use a '
                'Subversion changelist, pass the changelist name as an '
                'additional argument after the command.')

        repository_info, tool = self.initialize_scm_tool(
            client_name=self.options.repository_type)
        server_url = self.get_server_url(repository_info, tool)
        api_client, api_root = self.get_api(server_url)
        self.setup_tool(tool, api_root=api_root)

        try:
            revisions = tool.parse_revision_spec(args)
            extra_args = None
        except InvalidRevisionSpecError:
            if not tool.supports_diff_extra_args:
                raise

            revisions = None
            extra_args = args

        diff_info = tool.diff(
            revisions=revisions,
            files=self.options.include_files or [],
            extra_args=extra_args)

        diff = diff_info['diff']

        if diff:
            print diff

########NEW FILE########
__FILENAME__ = list_repo_types
from rbtools.clients import print_clients
from rbtools.commands import Command


class ListRepoTypes(Command):
    """List available repository types."""
    name = 'list-repo-types'
    author = 'The Review Board Project'
    description = 'Print a list of supported repository types.'

    def main(self, *args):
        print_clients(self.options)

########NEW FILE########
__FILENAME__ = main
import argparse
import os
import pkg_resources
import signal
import subprocess
import sys

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

from rbtools import get_version_string
from rbtools.commands import Option, RB_MAIN


GLOBAL_OPTIONS = [
    Option('-v', '--version',
           action='version',
           version='RBTools %s' % get_version_string()),
    Option('-h', '--help',
           action='store_true',
           dest='help',
           default=False),
    Option('command',
           nargs=argparse.REMAINDER,
           help='The RBTools command to execute, and any arguments. '
                '(See below)'),
]


def build_help_text(command_class):
    """Generate help text from a command class."""
    command = command_class()
    parser = command.create_parser({})

    return parser.format_help()


def help(args, parser):
    if args:
        # TODO: First check for static help text file before
        # generating it at run time.
        ep = pkg_resources.get_entry_info("rbtools", "rbtools_commands",
                                          args[0])

        if ep:
            help_text = build_help_text(ep.load())
            print help_text
            sys.exit(0)

        print "No help found for %s" % args[0]
        sys.exit(0)

    parser.print_help()

    # We cast to a set to de-dupe the list, since third-parties may
    # try to override commands by using the same name, and then cast
    # back to a list for easy sorting.
    entrypoints = pkg_resources.iter_entry_points('rbtools_commands')
    commands = list(set([entrypoint.name for entrypoint in entrypoints]))
    common_commands = ['post', 'patch', 'close', 'diff']

    print "\nThe most commonly used commands are:"
    for command in common_commands:
        print "  %s" % command

    print "\nOther commands:"
    for command in sorted(commands):
        if command not in common_commands:
            print "  %s" % command

    print ("See '%s help <command>' for more information "
           "on a specific command." % RB_MAIN)
    sys.exit(0)


def main():
    """Execute a command."""
    def exit_on_int(sig, frame):
        sys.exit(128 + sig)
    signal.signal(signal.SIGINT, exit_on_int)

    parser = argparse.ArgumentParser(
        prog=RB_MAIN,
        usage='%(prog)s [--version] <command> [options] [<args>]',
        add_help=False)

    for option in GLOBAL_OPTIONS:
        option.add_to(parser)

    opt = parser.parse_args()

    if not opt.command:
        help([], parser)

    command_name = opt.command[0]
    args = opt.command[1:]

    if command_name == "help":
        help(args, parser)
    elif opt.help or "--help" in args or '-h' in args:
        help(opt.command, parser)

    # Attempt to retrieve the command class from the entry points. We
    # first look in rbtools for the commands, and failing that, we look
    # for third-party commands.
    ep = pkg_resources.get_entry_info("rbtools", "rbtools_commands",
                                      command_name)

    if not ep:
        try:
            ep = pkg_resources.iter_entry_points('rbtools_commands',
                                                 command_name).next()
        except StopIteration:
            # There aren't any custom entry points defined.
            pass

    if ep:
        try:
            command = ep.load()()
        except ImportError:
            # TODO: It might be useful to actual have the strack
            # trace here, due to an import somewhere down the import
            # chain failing.
            sys.stderr.write("Could not load command entry point %s\n" %
                             ep.name)
            sys.exit(1)
        except Exception, e:
            sys.stderr.write("Unexpected error loading command %s: %s\n" %
                             (ep.name, e))
            sys.exit(1)

        command.run_from_argv([RB_MAIN, command_name] + args)
    else:
        # A command class could not be found, so try and execute
        # the "rb-<command>" on the system.
        args = ['%s-%s' % (RB_MAIN, command_name)] + args

        try:
            sys.exit(subprocess.call(args,
                                     stdin=sys.stdin,
                                     stdout=sys.stdout,
                                     stderr=sys.stderr,
                                     env=os.environ.copy()))
        except OSError:
            parser.error("'%s' is not a command" % command_name)


if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = patch
import re

from rbtools.api.errors import APIError
from rbtools.commands import Command, CommandError, Option
from rbtools.utils.filesystem import make_tempfile


# MARKDOWN_ESCAPED_CHARS comes from markdown.Markdown.ESCAPED_CHARS. We don't
# want to have a dependency on markdown for rbtools, so we just copy it into
# here.
MARKDOWN_ESCAPED_CHARS = ['\\', '`', '*', '_', '{', '}', '[', ']',
                          '(', ')', '>', '#', '+', '-', '.', '!']
MARKDOWN_SPECIAL_CHARS = re.escape(r''.join(MARKDOWN_ESCAPED_CHARS))
UNESCAPE_CHARS_RE = re.compile(r'\\([%s])' % MARKDOWN_SPECIAL_CHARS)


class Patch(Command):
    """Applies a specific patch from a RB server.

    The patch file indicated by the request id is downloaded from the
    server and then applied locally."""
    name = "patch"
    author = "The Review Board Project"
    args = "<review-request-id>"
    option_list = [
        Option("-c", "--commit",
               dest="commit",
               action="store_true",
               default=False,
               help="Commit using information fetched "
                    "from the review request (Git only)."),
        Option("--diff-revision",
               dest="diff_revision",
               default=None,
               help="revision id of diff to be used as patch"),
        Option("--px",
               dest="px",
               default=None,
               help="numerical pX argument for patch"),
        Option("--print",
               dest="patch_stdout",
               action="store_true",
               default=False,
               help="print patch to stdout instead of applying"),
        Command.server_options,
        Command.repository_options,
    ]

    def get_patch(self, request_id, api_root, diff_revision=None):
        """Return the diff as a string, the used diff revision and its basedir.

        If a diff revision is not specified, then this will look at the most
        recent diff.
        """
        try:
            diffs = api_root.get_diffs(review_request_id=request_id)
        except APIError, e:
            raise CommandError("Error getting diffs: %s" % e)

        # Use the latest diff if a diff revision was not given.
        # Since diff revisions start a 1, increment by one, and
        # never skip a number, the latest diff revisions number
        # should be equal to the number of diffs.
        if diff_revision is None:
            diff_revision = diffs.total_results

        try:
            diff = diffs.get_item(diff_revision)
            diff_body = diff.get_patch().data
            base_dir = getattr(diff, 'basedir', None) or ''
        except APIError:
            raise CommandError('The specified diff revision does not exist.')

        return diff_body, diff_revision, base_dir

    def apply_patch(self, repository_info, tool, request_id, diff_revision,
                    diff_file_path, base_dir):
        """Apply patch patch_file and display results to user."""
        print ("Patch is being applied from request %s with diff revision "
               " %s." % (request_id, diff_revision))
        tool.apply_patch(diff_file_path, repository_info.base_path,
                         base_dir, self.options.px)

    def _extract_commit_message(self, review_request):
        """Returns a commit message based on the review request.

        The commit message returned contains the Summary, Description, Bugs,
        and Testing Done fields from the review request, if available.
        """
        info = []

        summary = review_request.summary
        description = review_request.description
        testing_done = review_request.testing_done

        if not description.startswith(summary):
            info.append(summary)

        info.append(description)

        if testing_done:
            info.append('Testing Done:\n%s' % testing_done)

        if review_request.bugs_closed:
            info.append('Bugs closed: %s'
                        % ', '.join(review_request.bugs_closed))

        info.append('Reviewed at %s' % review_request.absolute_url)

        return '\n\n'.join(info)

    def main(self, request_id):
        """Run the command."""
        repository_info, tool = self.initialize_scm_tool(
            client_name=self.options.repository_type)
        server_url = self.get_server_url(repository_info, tool)
        api_client, api_root = self.get_api(server_url)

        # Get the patch, the used patch ID and base dir for the diff
        diff_body, diff_revision, base_dir = self.get_patch(
            request_id,
            api_root,
            self.options.diff_revision)

        if self.options.patch_stdout:
            print diff_body
        else:
            try:
                if tool.has_pending_changes():
                    message = 'Working directory is not clean.'

                    if not self.options.commit:
                        print 'Warning: %s' % message
                    else:
                        raise CommandError(message)
            except NotImplementedError:
                pass

            tmp_patch_file = make_tempfile(diff_body)
            self.apply_patch(repository_info, tool, request_id, diff_revision,
                             tmp_patch_file, base_dir)

            if self.options.commit:
                try:
                    review_request = api_root.get_review_request(
                        review_request_id=request_id,
                        force_text_type='plain')
                except APIError, e:
                    raise CommandError('Error getting review request %s: %s'
                                       % (request_id, e))

                message = self._extract_commit_message(review_request)
                author = review_request.get_submitter()

                try:
                    tool.create_commit(message, author)
                    print('Changes committed to current branch.')
                except NotImplementedError:
                    raise CommandError('--commit is not supported with %s'
                                       % tool.name)

########NEW FILE########
__FILENAME__ = post
import logging
import os
import re
import sys

from rbtools.api.errors import APIError
from rbtools.clients.errors import InvalidRevisionSpecError
from rbtools.commands import Command, CommandError, Option, OptionGroup
from rbtools.utils.console import confirm
from rbtools.utils.match_score import Score
from rbtools.utils.repository import get_repository_id
from rbtools.utils.users import get_user


class Post(Command):
    """Create and update review requests."""
    name = "post"
    author = "The Review Board Project"
    description = "Uploads diffs to create and update review requests."
    args = "[revisions]"

    GUESS_AUTO = 'auto'
    GUESS_YES = 'yes'
    GUESS_NO = 'no'
    GUESS_YES_INPUT_VALUES = (True, 'yes', 1, '1')
    GUESS_NO_INPUT_VALUES = (False, 'no', 0, '0')
    GUESS_CHOICES = (GUESS_AUTO, GUESS_YES, GUESS_NO)

    option_list = [
        OptionGroup(
            name='Posting Options',
            description='Controls the behavior of a post, including what '
                        'review request gets posted and how, and what '
                        'happens after it is posted.',
            option_list=[
                Option('-r', '--review-request-id',
                       dest='rid',
                       metavar='ID',
                       default=None,
                       help='Specifies the existing review request ID to '
                            'update.'),
                Option('-u', '--update',
                       dest='update',
                       action='store_true',
                       default=False,
                       help='Automatically determines the existing review '
                            'request to update.'),
                Option('-p', '--publish',
                       dest='publish',
                       action='store_true',
                       default=False,
                       config_key='PUBLISH',
                       help='Immediately publishes the review request after '
                            'posting.'),
                Option('-o', '--open',
                       dest='open_browser',
                       action='store_true',
                       config_key='OPEN_BROWSER',
                       default=False,
                       help='Opens a web browser to the review request '
                            'after posting.'),
                Option('--submit-as',
                       dest='submit_as',
                       metavar='USERNAME',
                       config_key='SUBMIT_AS',
                       default=None,
                       help='The user name to use as the author of the '
                            'review request, instead of the logged in user.'),
                Option('--change-only',
                       dest='change_only',
                       action='store_true',
                       default=False,
                       help='Updates fields from the change description, '
                            'but does not upload a new diff '
                            '(Perforce/Plastic only).'),
                Option('--diff-only',
                       dest='diff_only',
                       action='store_true',
                       default=False,
                       help='Uploads a new diff, but does not update '
                            'fields from the change description '
                            '(Perforce/Plastic only).'),
            ]
        ),
        Command.server_options,
        Command.repository_options,
        OptionGroup(
            name='Review Request Field Options',
            description='Options for setting the contents of fields in the '
                        'review request.',
            option_list=[
                Option('-g', '--guess-fields',
                       dest='guess_fields',
                       action='store',
                       config_key='GUESS_FIELDS',
                       nargs='?',
                       default=GUESS_AUTO,
                       const=GUESS_YES,
                       choices=GUESS_CHOICES,
                       help='Short-hand for --guess-summary '
                            '--guess-description.'),
                Option('--guess-summary',
                       dest='guess_summary',
                       action='store',
                       config_key='GUESS_SUMMARY',
                       nargs='?',
                       default=GUESS_AUTO,
                       const=GUESS_YES,
                       choices=GUESS_CHOICES,
                       help='Generates the Summary field based on the '
                            'commit messages (Bazaar/Git/Mercurial only).'),
                Option('--guess-description',
                       dest='guess_description',
                       action='store',
                       config_key='GUESS_DESCRIPTION',
                       nargs='?',
                       default=GUESS_AUTO,
                       const=GUESS_YES,
                       choices=GUESS_CHOICES,
                       help='Generates the Description field based on the '
                            'commit messages (Bazaar/Git/Mercurial only).'),
                Option('--change-description',
                       default=None,
                       help='A description of what changed in this update '
                            'of the review request. This is ignored for new '
                            'review requests.'),
                Option('--summary',
                       dest='summary',
                       default=None,
                       help='The new contents for the Summary field.'),
                Option('--description',
                       dest='description',
                       default=None,
                       help='The new contents for the Description field.'),
                Option('--description-file',
                       dest='description_file',
                       default=None,
                       metavar='FILENAME',
                       help='A text file containing the new contents for the '
                            'Description field.'),
                Option('--testing-done',
                       dest='testing_done',
                       default=None,
                       help='The new contents for the Testing Done field.'),
                Option('--testing-done-file',
                       dest='testing_file',
                       default=None,
                       metavar='FILENAME',
                       help='A text file containing the new contents for the '
                            'Testing Done field.'),
                Option('--branch',
                       dest='branch',
                       config_key='BRANCH',
                       default=None,
                       help='The branch the change will be committed on.'),
                Option('--bugs-closed',
                       dest='bugs_closed',
                       default=None,
                       help='The comma-separated list of bug IDs closed.'),
                Option('--target-groups',
                       dest='target_groups',
                       config_key='TARGET_GROUPS',
                       default=None,
                       help='The names of the groups that should perform the '
                            'review.'),
                Option('--target-people',
                       dest='target_people',
                       config_key='TARGET_PEOPLE',
                       default=None,
                       help='The usernames of the people who should perform '
                            'the review.'),
                Option('--depends-on',
                       dest='depends_on',
                       config_key='DEPENDS_ON',
                       default=None,
                       help='The new contents for the Depends On field.'),
                Option('--markdown',
                       dest='markdown',
                       action='store_true',
                       config_key='MARKDOWN',
                       default=False,
                       help='Specifies if the summary and description should '
                            'be interpreted as Markdown-formatted text '
                            '(Review Board 2.0+ only).'),
            ]
        ),
        Command.diff_options,
        Command.git_options,
        Command.perforce_options,
        Command.subversion_options,
    ]

    def post_process_options(self):
        # -g implies --guess-summary and --guess-description
        if self.options.guess_fields:
            self.options.guess_fields = self.normalize_guess_value(
                self.options.guess_fields, '--guess-fields')

            self.options.guess_summary = self.options.guess_fields
            self.options.guess_description = self.options.guess_fields

        if self.options.revision_range:
            raise CommandError(
                'The --revision-range argument has been removed. To post a '
                'diff for one or more specific revisions, pass those '
                'revisions as arguments. For more information, see the '
                'RBTools 0.6 Release Notes.')

        if self.options.svn_changelist:
            raise CommandError(
                'The --svn-changelist argument has been removed. To use a '
                'Subversion changelist, pass the changelist name as an '
                'additional argument after the command.')

        # Only one of --description and --description-file can be used
        if self.options.description and self.options.description_file:
            raise CommandError("The --description and --description-file "
                               "options are mutually exclusive.\n")

        # If --description-file is used, read that file
        if self.options.description_file:
            if os.path.exists(self.options.description_file):
                fp = open(self.options.description_file, "r")
                self.options.description = fp.read()
                fp.close()
            else:
                raise CommandError(
                    "The description file %s does not exist.\n" %
                    self.options.description_file)

        # Only one of --testing-done and --testing-done-file can be used
        if self.options.testing_done and self.options.testing_file:
            raise CommandError("The --testing-done and --testing-done-file "
                               "options are mutually exclusive.\n")

        # If --testing-done-file is used, read that file
        if self.options.testing_file:
            if os.path.exists(self.options.testing_file):
                fp = open(self.options.testing_file, "r")
                self.options.testing_done = fp.read()
                fp.close()
            else:
                raise CommandError("The testing file %s does not exist.\n" %
                                   self.options.testing_file)

        # If we have an explicitly specified summary, override
        # --guess-summary
        if self.options.summary:
            self.options.guess_summary = self.GUESS_NO
        else:
            self.options.guess_summary = self.normalize_guess_value(
                self.options.guess_summary, '--guess-summary')

        # If we have an explicitly specified description, override
        # --guess-description
        if self.options.description:
            self.options.guess_description = self.GUESS_NO
        else:
            self.options.guess_description = self.normalize_guess_value(
                self.options.guess_description, '--guess-description')

        # If we have an explicitly specified review request ID, override
        # --update
        if self.options.rid and self.options.update:
            self.options.update = False

    def normalize_guess_value(self, guess, arg_name):
        if guess in self.GUESS_YES_INPUT_VALUES:
            return self.GUESS_YES
        elif guess in self.GUESS_NO_INPUT_VALUES:
            return self.GUESS_NO
        elif guess == self.GUESS_AUTO:
            return guess
        else:
            raise CommandError('Invalid value "%s" for argument "%s"'
                               % (guess, arg_name))

    def get_repository_path(self, repository_info, api_root):
        """Get the repository path from the server.

        This will compare the paths returned by the SCM client
        with those one the server, and return the first match.
        """
        if isinstance(repository_info.path, list):
            repositories = api_root.get_repositories()

            try:
                while True:
                    for repo in repositories:
                        if repo['path'] in repository_info.path:
                            repository_info.path = repo['path']
                            raise StopIteration()

                    repositories = repositories.get_next()
            except StopIteration:
                pass

        if isinstance(repository_info.path, list):
            error_str = [
                'There was an error creating this review request.\n',
                '\n',
                'There was no matching repository path found on the server.\n',
                'Unknown repository paths found:\n',
            ]

            for foundpath in repository_info.path:
                error_str.append('\t%s\n' % foundpath)

            error_str += [
                'Ask the administrator to add one of these repositories\n',
                'to the Review Board server.\n',
            ]

            raise CommandError(''.join(error_str))

        return repository_info.path

    def get_draft_or_current_value(self, field_name, review_request):
        """Returns the draft or current field value from a review request.

        If a draft exists for the supplied review request, return the draft's
        field value for the supplied field name, otherwise return the review
        request's field value for the supplied field name.
        """
        if review_request.draft:
            fields = review_request.draft[0]
        else:
            fields = review_request

        return fields[field_name]

    def get_possible_matches(self, review_requests, summary, description,
                             limit=5):
        """Returns a sorted list of tuples of score and review request.

        Each review request is given a score based on the summary and
        description provided. The result is a sorted list of tuples containing
        the score and the corresponding review request, sorted by the highest
        scoring review request first.
        """
        candidates = []

        # Get all potential matches.
        try:
            while True:
                for review_request in review_requests:
                    summary_pair = (
                        self.get_draft_or_current_value(
                            'summary', review_request),
                        summary)
                    description_pair = (
                        self.get_draft_or_current_value(
                            'description', review_request),
                        description)
                    score = Score.get_match(summary_pair, description_pair)
                    candidates.append((score, review_request))

                review_requests = review_requests.get_next()
        except StopIteration:
            pass

        # Sort by summary and description on descending rank.
        sorted_candidates = sorted(
            candidates,
            key=lambda m: (m[0].summary_score, m[0].description_score),
            reverse=True
        )

        return sorted_candidates[:limit]

    def num_exact_matches(self, possible_matches):
        """Returns the number of exact matches in the possible match list."""
        count = 0

        for score, request in possible_matches:
            if score.is_exact_match():
                count += 1

        return count

    def guess_existing_review_request_id(self, repository_info, api_root,
                                         api_client):
        """Try to guess the existing review request ID if it is available.

        The existing review request is guessed by comparing the existing
        summary and description to the current post's summary and description,
        respectively. The current post's summary and description are guessed if
        they are not provided.

        If the summary and description exactly match those of an existing
        review request, the ID for which is immediately returned. Otherwise,
        the user is prompted to select from a list of potential matches,
        sorted by the highest ranked match first.
        """
        user = get_user(api_client, api_root, auth_required=True)
        repository_id = get_repository_id(
            repository_info, api_root, self.options.repository_name)

        try:
            # Get only pending requests by the current user for this
            # repository.
            review_requests = api_root.get_review_requests(
                repository=repository_id, from_user=user.username,
                status='pending', expand='draft')

            if not review_requests:
                raise CommandError('No existing review requests to update for '
                                   'user %s.'
                                   % user.username)
        except APIError, e:
            raise CommandError('Error getting review requests for user '
                               '%s: %s' % (user.username, e))

        summary = self.options.summary
        description = self.options.description

        if not summary or not description:
            try:
                commit_message = self.get_commit_message()

                if commit_message:
                    if not summary:
                        summary = commit_message['summary']

                    if not description:
                        description = commit_message['description']
            except NotImplementedError:
                raise CommandError('--summary and --description are required.')

        possible_matches = self.get_possible_matches(review_requests, summary,
                                                     description)
        exact_match_count = self.num_exact_matches(possible_matches)

        for score, review_request in possible_matches:
            # If the score is the only exact match, return the review request
            # ID without confirmation, otherwise prompt.
            if score.is_exact_match() and exact_match_count == 1:
                return review_request.id
            else:
                question = ("Update Review Request #%s: '%s'? "
                            % (review_request.id,
                               self.get_draft_or_current_value(
                                   'summary', review_request)))

                if confirm(question):
                    return review_request.id

        return None

    def post_request(self, repository_info, server_url, api_root,
                     review_request_id=None, changenum=None, diff_content=None,
                     parent_diff_content=None, commit_id=None,
                     base_commit_id=None,
                     submit_as=None, retries=3):
        """Creates or updates a review request, and uploads a diff.

        On success the review request id and url are returned.
        """
        supports_posting_commit_ids = \
            self.tool.capabilities.has_capability('review_requests',
                                                  'commit_ids')

        if review_request_id:
            # Retrieve the review request corresponding to the provided id.
            try:
                review_request = api_root.get_review_request(
                    review_request_id=review_request_id)
            except APIError, e:
                raise CommandError("Error getting review request %s: %s"
                                   % (review_request_id, e))

            if review_request.status == 'submitted':
                raise CommandError(
                    "Review request %s is marked as %s. In order to update "
                    "it, please reopen the review request and try again."
                    % (review_request_id, review_request.status))
        else:
            # No review_request_id, so we will create a new review request.
            try:
                repository = (
                    self.options.repository_url or
                    self.options.repository_name or
                    self.get_repository_path(repository_info, api_root))
                request_data = {
                    'repository': repository
                }

                if changenum:
                    request_data['changenum'] = changenum
                elif commit_id and supports_posting_commit_ids:
                    request_data['commit_id'] = commit_id

                if submit_as:
                    request_data['submit_as'] = submit_as

                review_request = api_root.get_review_requests().create(
                    **request_data)
            except APIError, e:
                if e.error_code == 204 and changenum:  # Change number in use.
                    rid = e.rsp['review_request']['id']
                    review_request = api_root.get_review_request(
                        review_request_id=rid)

                    if not self.options.diff_only:
                        review_request = review_request.update(
                            changenum=changenum)
                else:
                    raise CommandError("Error creating review request: %s" % e)

        if (not repository_info.supports_changesets or
            not self.options.change_only):
            try:
                diff_kwargs = {
                    'parent_diff': parent_diff_content,
                    'base_dir': (self.options.basedir or
                                 repository_info.base_path),
                }

                if (base_commit_id and
                    self.tool.capabilities.has_capability('diffs',
                                                          'base_commit_ids')):
                    # Both the Review Board server and SCMClient support
                    # base commit IDs, so pass that along when creating
                    # the diff.
                    diff_kwargs['base_commit_id'] = base_commit_id

                review_request.get_diffs().upload_diff(diff_content,
                                                       **diff_kwargs)
            except APIError, e:
                error_msg = [
                    'Error uploading diff\n\n',
                ]

                if e.error_code == 101 and e.http_status == 403:
                    error_msg.append(
                        'You do not have permissions to modify '
                        'this review request\n')
                elif e.error_code == 219:
                    error_msg.append(
                        'The generated diff file was empty. This '
                        'usually means no files were\n'
                        'modified in this change.\n')
                else:
                    error_msg.append(str(e) + '\n')

                error_msg.append(
                    'Your review request still exists, but the diff is '
                    'not attached.\n')

                error_msg.append('%s\n' % review_request.absolute_url)

                raise CommandError('\n'.join(error_msg))

        try:
            draft = review_request.get_draft()
        except APIError, e:
            raise CommandError("Error retrieving review request draft: %s" % e)

        # Update the review request draft fields based on options set
        # by the user, or configuration.
        update_fields = {}

        if self.options.target_groups:
            update_fields['target_groups'] = self.options.target_groups

        if self.options.target_people:
            update_fields['target_people'] = self.options.target_people

        if self.options.depends_on:
            update_fields['depends_on'] = self.options.depends_on

        if self.options.summary:
            update_fields['summary'] = self.options.summary

        if self.options.branch:
            update_fields['branch'] = self.options.branch

        if self.options.bugs_closed:
            # Append to the existing list of bugs.
            self.options.bugs_closed = self.options.bugs_closed.strip(", ")
            bug_set = (set(re.split("[, ]+", self.options.bugs_closed)) |
                       set(review_request.bugs_closed))
            self.options.bugs_closed = ",".join(bug_set)
            update_fields['bugs_closed'] = self.options.bugs_closed

        if self.options.description:
            update_fields['description'] = self.options.description

        if self.options.testing_done:
            update_fields['testing_done'] = self.options.testing_done

        if ((self.options.description or self.options.testing_done) and
            self.options.markdown and
            self.tool.capabilities.has_capability('text', 'markdown')):
            # The user specified that their Description/Testing Done are
            # valid Markdown, so tell the server so it won't escape the text.
            update_fields['text_type'] = 'markdown'

        if self.options.change_description:
            update_fields['changedescription'] = \
                self.options.change_description

        if self.options.publish:
            update_fields['public'] = True

        if supports_posting_commit_ids and commit_id != draft.commit_id:
            update_fields['commit_id'] = commit_id or ''

        if update_fields:
            try:
                draft = draft.update(**update_fields)
            except APIError, e:
                raise CommandError(
                    "Error updating review request draft: %s" % e)

        return review_request.id, review_request.absolute_url

    def get_revisions(self):
        """Returns the parsed revisions from the command line arguments.

        These revisions are used for diff generation and commit message
        extraction. They will be cached for future calls.
        """
        # Parse the provided revisions from the command line and generate
        # a spec or set of specialized extra arguments that the SCMClient
        # can use for diffing and commit lookups.
        if not hasattr(self, '_revisions'):
            try:
                self._revisions = self.tool.parse_revision_spec(self.cmd_args)
            except InvalidRevisionSpecError:
                if not self.tool.supports_diff_extra_args:
                    raise

                self._revisions = None

        return self._revisions

    def check_guess_fields(self):
        """Checks and handles field guesses for the review request.

        This will attempt to guess the values for the summary and
        description fields, based on the contents of the commit message
        at the provided revisions, if requested by the caller.

        If the backend doesn't support guessing, or if guessing isn't
        requested, or if explicit values were set in the options, nothing
        will be set for the fields.
        """
        is_new_review_request = (not self.options.rid and
                                 not self.options.update)

        guess_summary = (
            self.options.guess_summary == self.GUESS_YES or
            (self.options.guess_summary == self.GUESS_AUTO and
             is_new_review_request))
        guess_description = (
            self.options.guess_description == self.GUESS_YES or
            (self.options.guess_description == self.GUESS_AUTO and
             is_new_review_request))

        if guess_summary or guess_description:
            try:
                commit_message = self.get_commit_message()

                if commit_message:
                    if guess_summary:
                        self.options.summary = commit_message['summary']

                    if guess_description:
                        self.options.description = \
                            commit_message['description']
            except NotImplementedError:
                # The SCMClient doesn't support getting commit messages,
                # so we can't provide the guessed versions.
                pass

    def get_commit_message(self):
        """Returns the commit message for the parsed revisions.

        If the SCMClient supports getting a commit message, this will fetch
        and store the message for future lookups.

        This is used for guessing the summary and description fields, and
        updating exising review requests using -u.
        """
        if not hasattr(self, '_commit_message'):
            self._commit_message = \
                self.tool.get_commit_message(self.get_revisions())

        return self._commit_message

    def main(self, *args):
        """Create and update review requests."""
        # The 'args' tuple must be made into a list for some of the
        # SCM Clients code. The way arguments were structured in
        # post-review meant this was a list, and certain parts of
        # the code base try and concatenate args to the end of
        # other lists. Until the client code is restructured and
        # cleaned up we will satisfy the assumption here.
        self.cmd_args = list(args)

        self.post_process_options()
        origcwd = os.path.abspath(os.getcwd())
        repository_info, self.tool = self.initialize_scm_tool(
            client_name=self.options.repository_type)
        server_url = self.get_server_url(repository_info, self.tool)
        api_client, api_root = self.get_api(server_url)
        self.setup_tool(self.tool, api_root=api_root)

        if self.options.diff_filename:
            parent_diff = None
            base_commit_id = None
            commit_id = None

            if self.options.diff_filename == '-':
                diff = sys.stdin.read()
            else:
                try:
                    diff_path = os.path.join(origcwd,
                                             self.options.diff_filename)
                    fp = open(diff_path, 'r')
                    diff = fp.read()
                    fp.close()
                except IOError, e:
                    raise CommandError("Unable to open diff filename: %s" % e)
        else:
            revisions = self.get_revisions()

            if revisions:
                extra_args = None
            else:
                extra_args = self.cmd_args

            # Generate a diff against the revisions or arguments, filtering
            # by the requested files if provided.
            diff_info = self.tool.diff(
                revisions=revisions,
                files=self.options.include_files or [],
                extra_args=extra_args)

            diff = diff_info['diff']
            parent_diff = diff_info.get('parent_diff')
            base_commit_id = diff_info.get('base_commit_id')
            commit_id = diff_info.get('commit_id')

        if len(diff) == 0:
            raise CommandError("There don't seem to be any diffs!")

        if repository_info.supports_changesets and 'changenum' in diff_info:
            changenum = diff_info['changenum']
            commit_id = changenum
        else:
            changenum = None

        if not self.options.diff_filename:
            # If the user has requested to guess the summary or description,
            # get the commit message and override the summary and description
            # options.
            self.check_guess_fields()

        if self.options.update:
            self.options.rid = self.guess_existing_review_request_id(
                repository_info, api_root, api_client)

            if not self.options.rid:
                raise CommandError('Could not determine the existing review '
                                   'request to update.')

        # If only certain files within a commit are being submitted for review,
        # do not include the commit id. This prevents conflicts if mutliple
        # files from the same commit are posted for review separately.
        if self.options.include_files:
            commit_id = None

        request_id, review_url = self.post_request(
            repository_info,
            server_url,
            api_root,
            self.options.rid,
            changenum=changenum,
            diff_content=diff,
            parent_diff_content=parent_diff,
            commit_id=commit_id,
            base_commit_id=base_commit_id,
            submit_as=self.options.submit_as)

        diff_review_url = review_url + 'diff/'

        print "Review request #%s posted." % request_id
        print
        print review_url
        print diff_review_url

        # Load the review up in the browser if requested to.
        if self.options.open_browser:
            try:
                import webbrowser
                if 'open_new_tab' in dir(webbrowser):
                    # open_new_tab is only in python 2.5+
                    webbrowser.open_new_tab(review_url)
                elif 'open_new' in dir(webbrowser):
                    webbrowser.open_new(review_url)
                else:
                    os.system('start %s' % review_url)
            except:
                logging.error('Error opening review URL: %s' % review_url)

########NEW FILE########
__FILENAME__ = publish
from rbtools.api.errors import APIError
from rbtools.commands import Command, CommandError, Option


class Publish(Command):
    """Publish a specific review request from a draft."""
    name = "publish"
    author = "The Review Board Project"
    args = "<review-request-id>"
    option_list = [
        Command.server_options,
        Command.repository_options,
    ]

    def get_review_request(self, request_id, api_root):
        """Returns the review request resource for the given ID."""
        try:
            request = api_root.get_review_request(review_request_id=request_id)
        except APIError, e:
            raise CommandError("Error getting review request: %s" % e)

        return request

    def main(self, request_id):
        """Run the command."""
        repository_info, tool = self.initialize_scm_tool(
            client_name=self.options.repository_type)
        server_url = self.get_server_url(repository_info, tool)
        api_client, api_root = self.get_api(server_url)

        request = self.get_review_request(request_id, api_root)
        try:
            draft = request.get_draft()
            draft = draft.update(public=True)
        except APIError, e:
            raise CommandError("Error publishing review request (it may "
                               "already be published): %s" % e)

        print "Review request #%s is published." % (request_id)

########NEW FILE########
__FILENAME__ = status
import logging

from rbtools.commands import Command, Option
from rbtools.utils.repository import get_repository_id
from rbtools.utils.users import get_username


class Status(Command):
    """Display review requests for the current repository."""
    name = "status"
    author = "The Review Board Project"
    description = "Output a list of your pending review requests."
    args = ""
    option_list = [
        Option("--all",
               dest="all_repositories",
               action="store_true",
               default=False,
               help="Show review requests for all repositories instead "
                    "of the detected repository."),
        Command.server_options,
        Command.repository_options,
        Command.perforce_options,
    ]

    def output_request(self, request):
        print "   r/%s - %s" % (request.id, request.summary)

    def output_draft(self, request, draft):
        print " * r/%s - %s" % (request.id, draft.summary)

    def main(self):
        repository_info, tool = self.initialize_scm_tool(
            client_name=self.options.repository_type)
        server_url = self.get_server_url(repository_info, tool)
        api_client, api_root = self.get_api(server_url)
        self.setup_tool(tool, api_root=api_root)
        username = get_username(api_client, api_root, auth_required=True)

        query_args = {
            'from_user': username,
            'status': 'pending',
            'expand': 'draft',
        }

        if not self.options.all_repositories:
            repo_id = get_repository_id(
                repository_info,
                api_root,
                repository_name=self.options.repository_name)

            if repo_id:
                query_args['repository'] = repo_id
            else:
                logging.warning('The repository detected in the current '
                                'directory was not found on\n'
                                'the Review Board server. Displaying review '
                                'requests from all repositories.')

        requests = api_root.get_review_requests(**query_args)

        try:
            while True:
                for request in requests:
                    if request.draft:
                        self.output_draft(request, request.draft[0])
                    else:
                        self.output_request(request)

                requests = requests.get_next(**query_args)
        except StopIteration:
            pass

########NEW FILE########
__FILENAME__ = hgext
# This file provides a Mercurial extension that resets certain
# config options to provide consistent output.

# We use reposetup because the config is re-read for each repo, after
# uisetup() is called.
ALLOWED_PARAMS  = ['git', 'svn']

def reposetup(ui, repo):
    for section in ['diff']:
        for k, v in ui.configitems(section):
            # Setting value to None is effectively unsetting the value since
            # None is the stand-in value for "not set."
            if k not in ALLOWED_PARAMS:
                ui.setconfig(section, k, None)

########NEW FILE########
__FILENAME__ = common
import logging
import re
import subprocess

from rbtools.api.client import RBClient
from rbtools.api.errors import APIError, ServerInterfaceError


SUBMITTED = 'submitted'


class HookError(Exception):
    pass


def get_api(server_url, username, password):
    """Returns an RBClient instance and the associated root resource.

    Hooks should use this method to gain access to the API, instead of
    instantianting their own client.
    """
    api_client = RBClient(server_url, username=username, password=password)

    try:
        api_root = api_client.get_root()
    except ServerInterfaceError, e:
        raise HookError('Could not reach the Review Board server at %s: %s'
                        % (server_url, e))
    except APIError, e:
        raise HookError('Unexpected API Error: %s' % e)

    return api_client, api_root


def execute(command):
    """Executes the specified command and returns the stdout output."""
    process = subprocess.Popen(command, stdout=subprocess.PIPE)
    output = process.communicate()[0].strip()

    if process.returncode:
        logging.warning('Failed to execute command: %s', command)
        return None

    return output


def initialize_logging():
    """Sets up a log handler to format log messages.

    Warning, error, and critical messages will show the level name as a prefix,
    followed by the message.
    """
    root = logging.getLogger()

    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
    handler.setLevel(logging.WARNING)
    root.addHandler(handler)


def get_review_request_id(regex, commit_message):
    """Returns the review request ID referenced in the commit message.

    We assume there is at most one review request associated with each commit.
    If a matching review request cannot be found, we return 0.
    """
    match = regex.search(commit_message)
    return (match and int(match.group('id'))) or 0


def get_review_request(review_request_id, api_root):
    """Returns the review request resource for the given ID."""
    try:
        review_request = api_root.get_review_request(
            review_request_id=review_request_id)
    except APIError, e:
        raise HookError('Error getting review request: %s' % e)

    return review_request


def close_review_request(server_url, username, password, review_request_id,
                         description):
    """Closes the specified review request as submitted."""
    api_client, api_root = get_api(server_url, username, password)
    review_request = get_review_request(review_request_id, api_root)

    if review_request.status == SUBMITTED:
        logging.warning('Review request #%s is already %s.',
                        review_request_id, SUBMITTED)
        return

    if description:
        review_request = review_request.update(status=SUBMITTED,
                                               description=description)
    else:
        review_request = review_request.update(status=SUBMITTED)

    print('Review request #%s is set to %s.' %
          (review_request_id, review_request.status))


def get_review_request_approval(server_url, username, password,
                                review_request_id):
    """Returns the approval information for the given review request."""
    api_client, api_root = get_api(server_url, username, password)
    review_request = get_review_request(review_request_id, api_root)

    return review_request.approved, review_request.approval_failure

########NEW FILE########
__FILENAME__ = git
from collections import defaultdict
from copy import deepcopy

from rbtools.hooks.common import execute, get_review_request_id


def get_branch_name(ref_name):
    """Returns the branch name corresponding to the specified ref name."""
    branch_ref_prefix = 'refs/heads/'

    if ref_name.startswith(branch_ref_prefix):
        return ref_name[len(branch_ref_prefix):]


def get_commit_hashes(old_rev, new_rev):
    """Returns a list of abbreviated commit hashes from old_rev to new_rev."""
    git_command = ['git', 'rev-list', '--abbrev-commit', '--reverse', '%s..%s'
                   % (old_rev, new_rev)]
    return execute(git_command).split('\n')


def get_unique_commit_hashes(ref_name, new_rev):
    """Returns a list of abbreviated commit hashes unique to ref_name."""
    git_command = ['git', 'rev-list', new_rev, '--abbrev-commit', '--reverse',
                   '--not']
    git_command.extend(get_excluded_branches(ref_name))
    return execute(git_command).strip().split('\n')


def get_excluded_branches(ref_name):
    """Returns a list of all branches, excluding the specified branch."""
    git_command = ['git', 'for-each-ref', 'refs/heads/', '--format=%(refname)']
    all_branches = execute(git_command).strip().split('\n')
    return [branch.strip() for branch in all_branches if branch != ref_name]


def get_branches_containing_commit(commit_hash):
    """Returns a list of all branches containing the specified commit."""
    git_command = ['git', 'branch', '--contains', commit_hash]
    branches = execute(git_command).replace('*', '').split('\n')
    return [branch.strip() for branch in branches]


def get_commit_message(commit):
    """Returns the specified commit's commit message."""
    git_command = ['git', 'show', '-s', '--pretty=format:%B', commit]
    return execute(git_command).strip()


def get_review_id_to_commits_map(lines, regex):
    """Returns a dictionary, mapping a review request ID to a list of commits.

    The commits must be in the form: oldrev newrev refname (separated by
    newlines), as given by a Git pre-receive or post-receive hook.

    If a commit's commit message does not contain a review request ID, we append
    the commit to the key 0.
    """
    review_id_to_commits_map = defaultdict(list)

    # Store a list of new branches (which have an all-zero old_rev value)
    # created in this push to handle them specially.
    new_branches = []
    null_sha1 = '0' * 40

    for line in lines:
        old_rev, new_rev, ref_name = line.split()
        branch_name = get_branch_name(ref_name)

        if not branch_name or new_rev == null_sha1:
            continue

        if old_rev == null_sha1:
            new_branches.append(branch_name)
            commit_hashes = get_unique_commit_hashes(ref_name, new_rev)
        else:
            commit_hashes = get_commit_hashes(old_rev, new_rev)

        for commit_hash in commit_hashes:
            if commit_hash:
                commit_message = get_commit_message(commit_hash)
                review_request_id = get_review_request_id(regex, commit_message)

                commit = '%s (%s)' % (branch_name, commit_hash)
                review_id_to_commits_map[review_request_id].append(commit)

    # If there are new branches, check every commit in the dictionary
    # (corresponding to only old branches) to see if the new branches also
    # contain that commit.
    if new_branches:
        review_id_to_commits_map_copy = deepcopy(review_id_to_commits_map)

        for review_id, commit_list in review_id_to_commits_map_copy.iteritems():
            for commit in commit_list:
                commit_branch = commit[:commit.find('(') - 1]

                if commit_branch in new_branches:
                    continue

                commit_hash = commit[commit.find('(') + 1:-1]
                commit_branches = get_branches_containing_commit(commit_hash)

                for branch in set(new_branches).intersection(commit_branches):
                    new_commit = '%s (%s)' % (branch, commit_hash)
                    review_id_to_commits_map[review_id].append(new_commit)

    return review_id_to_commits_map

########NEW FILE########
__FILENAME__ = tests
class OptionsStub(object):
    def __init__(self):
        self.debug = True
        self.guess_summary = False
        self.guess_description = False
        self.tracking = None
        self.username = None
        self.password = None
        self.repository_url = None
        self.disable_proxy = False
        self.summary = None
        self.description = None

########NEW FILE########
__FILENAME__ = checks
import os
import subprocess
import sys

from rbtools.utils.process import die, execute


GNU_DIFF_WIN32_URL = 'http://gnuwin32.sourceforge.net/packages/diffutils.htm'


def check_install(command):
    """
    Try executing an external command and return a boolean indicating whether
    that command is installed or not.  The 'command' argument should be
    something that executes quickly, without hitting the network (for
    instance, 'svn help' or 'git --version').
    """
    try:
        subprocess.Popen(command,
                         stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
        return True
    except OSError:
        return False


def check_gnu_diff():
    """Checks if GNU diff is installed, and informs the user if it's not."""
    has_gnu_diff = False

    try:
        if hasattr(os, 'uname') and os.uname()[0] == 'SunOS':
            diff_cmd = 'gdiff'
        else:
            diff_cmd = 'diff'

        result = execute([diff_cmd, '--version'], ignore_errors=True)
        has_gnu_diff = 'GNU diffutils' in result
    except OSError:
        pass

    if not has_gnu_diff:
        sys.stderr.write('\n')
        sys.stderr.write('GNU diff is required in order to generate diffs. '
                         'Make sure it is installed\n')
        sys.stderr.write('and in the path.\n')
        sys.stderr.write('\n')

        if os.name == 'nt':
            sys.stderr.write('On Windows, you can install this from:\n')
            sys.stderr.write(GNU_DIFF_WIN32_URL)
            sys.stderr.write('\n')

        die()

########NEW FILE########
__FILENAME__ = console
import os
import subprocess
from distutils.util import strtobool

from rbtools.utils.filesystem import make_tempfile


def confirm(question):
    """Interactively prompt for a Yes/No answer.

    Accepted values (case-insensitive) depend on distutils.util.strtobool():
    'Yes' values: y, yes, t, true, on, 1
    'No' values: n, no , f, false, off, 0
    """
    while True:
        try:
            answer = raw_input("%s [Yes/No]: " % question).lower()
            return strtobool(answer)
        except ValueError:
            print '%s is not a valid answer.' % answer


def edit_text(content):
    """Allows a user to edit a block of text and returns the saved result.

    The environment's default text editor is used if available, otherwise
    vim is used.
    """
    tempfile = make_tempfile(content.encode('utf8'))
    editor = os.environ.get('EDITOR', 'vim')
    subprocess.call([editor, tempfile])
    f = open(tempfile)
    result = f.read()
    f.close()

    return result.decode('utf8')

########NEW FILE########
__FILENAME__ = filesystem
import os
import shutil
import tempfile

from rbtools.utils.process import die


CONFIG_FILE = '.reviewboardrc'

tempfiles = []
tempdirs = []
builtin = {}


def cleanup_tempfiles():
    for tmpfile in tempfiles:
        try:
            os.unlink(tmpfile)
        except:
            pass

    for tmpdir in tempdirs:
        shutil.rmtree(tmpdir, ignore_errors=True)


def get_config_value(configs, name, default=None):
    for c in configs:
        if name in c:
            return c[name]

    return default


def load_config_files(homepath):
    """Loads data from .reviewboardrc files."""
    def _load_config(path):
        config = {
            'TREES': {},
        }

        filename = os.path.join(path, CONFIG_FILE)

        if os.path.exists(filename):
            try:
                execfile(filename, config)
            except SyntaxError, e:
                die('Syntax error in config file: %s\n'
                    'Line %i offset %i\n' % (filename, e.lineno, e.offset))

            return dict((k, config[k])
                        for k in set(config.keys()) - set(builtin.keys()))

        return None

    configs = []

    for path in walk_parents(os.getcwd()):
        config = _load_config(path)

        if config:
            configs.append(config)

    user_config = _load_config(homepath)
    if user_config:
        configs.append(user_config)

    return user_config, configs


def make_tempfile(content=None):
    """
    Creates a temporary file and returns the path. The path is stored
    in an array for later cleanup.
    """
    fd, tmpfile = tempfile.mkstemp()

    if content:
        os.write(fd, content)

    os.close(fd)
    tempfiles.append(tmpfile)
    return tmpfile


def make_tempdir(parent=None):
    """Creates a temporary directory and returns the path.

    The path is stored in an array for later cleanup.
    """
    tmpdir = tempfile.mkdtemp(dir=parent)
    tempdirs.append(tmpdir)

    return tmpdir


def walk_parents(path):
    """
    Walks up the tree to the root directory.
    """
    while os.path.splitdrive(path)[1] != os.sep:
        yield path
        path = os.path.dirname(path)


def get_home_path():
    """Retrieve the homepath"""
    if 'APPDATA' in os.environ:
        return os.environ['APPDATA']
    elif 'HOME' in os.environ:
        return os.environ["HOME"]
    else:
        return ''


def get_config_paths():
    """Return the paths to each .reviewboardrc influencing the cwd.

    A list of paths to .reviewboardrc files will be returned, where
    each subsequent list entry should take precedence over the previous.
    i.e. configuration found in files further down the list will take
    precedence.
    """
    config_paths = []
    for path in walk_parents(os.getcwd()):
        filename = os.path.join(path, CONFIG_FILE)
        if os.path.exists(filename):
            config_paths.insert(0, filename)

    filename = os.path.join(get_home_path(), CONFIG_FILE)
    if os.path.exists(filename):
        config_paths.append(filename)

    return config_paths


def parse_config_file(filename):
    """Parse a .reviewboardrc file.

    Returns a dictionary containing the configuration from the file.

    The ``filename`` argument should contain a full path to a
    .reviewboardrc file.
    """
    config = {}
    try:
        execfile(filename, config)
    except SyntaxError, e:
        die('Syntax error in config file: %s\n'
            'Line %i offset %i\n' % (filename, e.lineno, e.offset))

    return dict((k, config[k])
                for k in set(config.keys()) - set(builtin.keys()))


def load_config():
    """Load configuration from .reviewboardrc files

    This will read all of the .reviewboardrc files influencing the
    cwd and return a dictionary containing the configuration.
    """
    config = {
        'TREES': {},
    }

    for filename in get_config_paths():
        config.update(parse_config_file(filename))

    return config


# This extracts a dictionary of the built-in globals in order to have a clean
# dictionary of settings, consisting of only what has been specified in the
# config file.
exec('True', builtin)

########NEW FILE########
__FILENAME__ = match_score
from difflib import SequenceMatcher


class Score(object):
    """Encapsulates ranking information for matching existing requests.

    This is currently used with 'rbt post -u' to match the new change with
    existing review requests. The 'get_match' method will return a new Score,
    and then multiple scores can be ranked against each other."""
    EXACT_MATCH_SCORE = 1.0

    def __init__(self, summary_score, description_score):
        self.summary_score = summary_score
        self.description_score = description_score

    def is_exact_match(self):
        return (self.summary_score == self.EXACT_MATCH_SCORE and
                self.description_score == self.EXACT_MATCH_SCORE)

    @staticmethod
    def get_match(summary_pair, description_pair):
        """Get a score based on a pair of summaries and a pair of descriptions.

        The scores for summary and description pairs are calculated
        independently using SequenceMatcher, and returned as part of a Score
        object.
        """
        if not summary_pair or not description_pair:
            return None

        summary_score = SequenceMatcher(
            None, summary_pair[0], summary_pair[1]).ratio()
        description_score = SequenceMatcher(
            None, description_pair[0], description_pair[1]).ratio()

        return Score(summary_score, description_score)

########NEW FILE########
__FILENAME__ = process
import logging
import os
import subprocess
import sys


def die(msg=None):
    """
    Cleanly exits the program with an error message. Erases all remaining
    temporary files.
    """
    from rbtools.utils.filesystem import cleanup_tempfiles

    cleanup_tempfiles()

    if msg:
        print msg

    sys.exit(1)


def execute(command,
            env=None,
            split_lines=False,
            ignore_errors=False,
            extra_ignore_errors=(),
            translate_newlines=True,
            with_errors=True,
            none_on_ignored_error=False):
    """
    Utility function to execute a command and return the output.
    """
    if isinstance(command, list):
        logging.debug('Running: ' + subprocess.list2cmdline(command))
    else:
        logging.debug('Running: ' + command)

    if env:
        env.update(os.environ)
    else:
        env = os.environ.copy()

    # TODO: This can break on systems that don't have the en_US locale
    # installed (which isn't very many). Ideally in this case, we could
    # put something in the config file, but that's not plumbed through to here.
    env['LC_ALL'] = 'en_US.UTF-8'
    env['LANGUAGE'] = 'en_US.UTF-8'

    if with_errors:
        errors_output = subprocess.STDOUT
    else:
        errors_output = subprocess.PIPE

    if sys.platform.startswith('win'):
        p = subprocess.Popen(command,
                             stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE,
                             stderr=errors_output,
                             shell=False,
                             universal_newlines=translate_newlines,
                             env=env)
    else:
        p = subprocess.Popen(command,
                             stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE,
                             stderr=errors_output,
                             shell=False,
                             close_fds=True,
                             universal_newlines=translate_newlines,
                             env=env)
    if split_lines:
        data = p.stdout.readlines()
    else:
        data = p.stdout.read()

    rc = p.wait()

    if rc and not ignore_errors and rc not in extra_ignore_errors:
        die('Failed to execute command: %s\n%s' % (command, data))
    elif rc:
        logging.debug('Command exited with rc %s: %s\n%s---'
                      % (rc, command, data))

    if rc and none_on_ignored_error:
        return None

    return data

########NEW FILE########
__FILENAME__ = repository
def get_repository_id(repository_info, api_root, repository_name=None):
    """Get the repository ID from the server.

    This will compare the paths returned by the SCM client
    with those on the server, and return the id of the first
    match.
    """
    detected_paths = repository_info.path

    if not isinstance(detected_paths, list):
        detected_paths = [detected_paths]

    repositories = api_root.get_repositories()

    try:
        while True:
            for repo in repositories:
                if (repo.path in detected_paths or
                    repo.mirror_path in detected_paths or
                    repo.name == repository_name):
                    return repo.id

            repositories = repositories.get_next()
    except StopIteration:
        return None

########NEW FILE########
__FILENAME__ = testbase
import os
import sys
import unittest
import uuid
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

from rbtools.utils.filesystem import cleanup_tempfiles, make_tempdir


class RBTestBase(unittest.TestCase):
    """Base class for RBTools tests.

    Its side effect in that it change home directory before test suit will
    run. This is because RBTools actively works with files and almost all
    tests employ file I/O operations."""
    def setUp(self):
        self._old_cwd = os.getcwd()
        self.set_user_home_tmp()

    def tearDown(self):
        os.chdir(self._old_cwd)
        cleanup_tempfiles()

    def create_tmp_dir(self):
        """Creates and returns a temporary directory."""
        return make_tempdir()

    def chdir_tmp(self, dir=None):
        """Changes current directory to a temporary directory."""
        dirname = make_tempdir(parent=dir)
        os.chdir(dirname)
        return dirname

    def gen_uuid(self):
        """Generates UUID value which can be useful where some unique value
        is required."""
        return str(uuid.uuid4())

    def get_user_home(self):
        """Returns current user's home directory."""
        return os.environ['HOME']

    def is_exe_in_path(sefl, name):
        """Checks whether an executable is in the user's search path.

        This expects a name without any system-specific executable extension.
        It will append the proper extension as necessary. For example,
        use "myapp" and not "myapp.exe".

        This will return True if the app is in the path, or False otherwise.

        Taken from djblets.util.filesystem to avoid an extra dependency
        """

        if sys.platform == 'win32' and not name.endswith('.exe'):
            name += ".exe"

        for dir in os.environ['PATH'].split(os.pathsep):
            if os.path.exists(os.path.join(dir, name)):
                return True

        return False

    def reset_cl_args(self, values=[]):
        """Replaces command-line arguments with new ones. Useful for testing
        program's command-line options."""
        sys.argv = values

    def set_user_home(self, path):
        """Set home directory of current user."""
        os.environ['HOME'] = path

    def set_user_home_tmp(self):
        """Set temporary directory as current user's home."""
        self.set_user_home(make_tempdir())

    def catch_output(self, func):
        stdout = sys.stdout
        outbuf = StringIO()
        sys.stdout = outbuf
        func()
        sys.stdout = stdout
        return outbuf.getvalue()

########NEW FILE########
__FILENAME__ = tests
"""Tests for rbtools.api units.

Any new modules created under rbtools/api should be tested here."""
import os
import re
import sys

from rbtools.utils import checks, filesystem, process
from rbtools.utils.testbase import RBTestBase


class UtilitiesTest(RBTestBase):
    def test_check_install(self):
        """Testing 'check_install' method."""
        self.assertTrue(checks.check_install([sys.executable, ' --version']))
        self.assertFalse(checks.check_install([self.gen_uuid()]))

    def test_make_tempfile(self):
        """Testing 'make_tempfile' method."""
        fname = filesystem.make_tempfile()

        self.assertTrue(os.path.isfile(fname))
        self.assertEqual(os.stat(fname).st_uid, os.geteuid())
        self.assertTrue(os.access(fname, os.R_OK | os.W_OK))

    def test_execute(self):
        """Testing 'execute' method."""
        self.assertTrue(re.match('.*?%d.%d.%d' % sys.version_info[:3],
                        process.execute([sys.executable, '-V'])))

    def test_die(self):
        """Testing 'die' method."""
        self.assertRaises(SystemExit, process.die)

########NEW FILE########
__FILENAME__ = users
import getpass
import logging
import sys

from rbtools.api.errors import AuthorizationError
from rbtools.commands import CommandError


def get_authenticated_session(api_client, api_root, auth_required=False):
    """Return an authenticated session.

    None will be returned if the user is not authenticated, unless the
    'auth_required' parameter is True, in which case the user will be prompted
    to login.
    """
    session = api_root.get_session()

    if not session.authenticated:
        if not auth_required:
            return None

        logging.warning('You are not authenticated with the Review Board '
                        'server at %s, please login.' % api_client.url)
        sys.stderr.write('Username: ')
        username = raw_input()
        password = getpass.getpass('Password: ')
        api_client.login(username, password)

        try:
            session = session.get_self()
        except AuthorizationError:
            raise CommandError('You are not authenticated.')

    return session


def get_user(api_client, api_root, auth_required=False):
    """Return the user resource for the current session."""
    session = get_authenticated_session(api_client, api_root, auth_required)

    if session:
        return session.get_user()


def get_username(api_client, api_root, auth_required=False):
    """Return the username for the current session."""
    session = get_authenticated_session(api_client, api_root, auth_required)

    if session:
        return session.links.user.title

########NEW FILE########
