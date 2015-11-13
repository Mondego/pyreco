__FILENAME__ = bootstrap
##############################################################################
#
# Copyright (c) 2006 Zope Foundation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Bootstrap a buildout-based project

Simply run this script in a directory containing a buildout.cfg.
The script accepts buildout command-line options, so you can
use the -c option to specify an alternate configuration file.
"""

import os, shutil, sys, tempfile, urllib, urllib2, subprocess
from optparse import OptionParser

if sys.platform == 'win32':
    def quote(c):
        if ' ' in c:
            return '"%s"' % c  # work around spawn lamosity on windows
        else:
            return c
else:
    quote = str

# See zc.buildout.easy_install._has_broken_dash_S for motivation and comments.
stdout, stderr = subprocess.Popen(
    [sys.executable, '-Sc',
     'try:\n'
     '    import ConfigParser\n'
     'except ImportError:\n'
     '    print 1\n'
     'else:\n'
     '    print 0\n'],
    stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
has_broken_dash_S = bool(int(stdout.strip()))

# In order to be more robust in the face of system Pythons, we want to
# run without site-packages loaded.  This is somewhat tricky, in
# particular because Python 2.6's distutils imports site, so starting
# with the -S flag is not sufficient.  However, we'll start with that:
if not has_broken_dash_S and 'site' in sys.modules:
    # We will restart with python -S.
    args = sys.argv[:]
    args[0:0] = [sys.executable, '-S']
    args = map(quote, args)
    os.execv(sys.executable, args)
# Now we are running with -S.  We'll get the clean sys.path, import site
# because distutils will do it later, and then reset the path and clean
# out any namespace packages from site-packages that might have been
# loaded by .pth files.
clean_path = sys.path[:]
import site  # imported because of its side effects
sys.path[:] = clean_path
for k, v in sys.modules.items():
    if k in ('setuptools', 'pkg_resources') or (
        hasattr(v, '__path__') and
        len(v.__path__) == 1 and
        not os.path.exists(os.path.join(v.__path__[0], '__init__.py'))):
        # This is a namespace package.  Remove it.
        sys.modules.pop(k)

is_jython = sys.platform.startswith('java')

setuptools_source = 'http://peak.telecommunity.com/dist/ez_setup.py'
distribute_source = 'http://python-distribute.org/distribute_setup.py'


# parsing arguments
def normalize_to_url(option, opt_str, value, parser):
    if value:
        if '://' not in value:  # It doesn't smell like a URL.
            value = 'file://%s' % (
                urllib.pathname2url(
                    os.path.abspath(os.path.expanduser(value))),)
        if opt_str == '--download-base' and not value.endswith('/'):
            # Download base needs a trailing slash to make the world happy.
            value += '/'
    else:
        value = None
    name = opt_str[2:].replace('-', '_')
    setattr(parser.values, name, value)

usage = '''\
[DESIRED PYTHON FOR BUILDOUT] bootstrap.py [options]

Bootstraps a buildout-based project.

Simply run this script in a directory containing a buildout.cfg, using the
Python that you want bin/buildout to use.

Note that by using --setup-source and --download-base to point to
local resources, you can keep this script from going over the network.
'''

parser = OptionParser(usage=usage)
parser.add_option("-v", "--version", dest="version",
                          help="use a specific zc.buildout version")
parser.add_option("-d", "--distribute",
                   action="store_true", dest="use_distribute", default=False,
                   help="Use Distribute rather than Setuptools.")
parser.add_option("--setup-source", action="callback", dest="setup_source",
                  callback=normalize_to_url, nargs=1, type="string",
                  help=("Specify a URL or file location for the setup file. "
                        "If you use Setuptools, this will default to " +
                        setuptools_source + "; if you use Distribute, this "
                        "will default to " + distribute_source + "."))
parser.add_option("--download-base", action="callback", dest="download_base",
                  callback=normalize_to_url, nargs=1, type="string",
                  help=("Specify a URL or directory for downloading "
                        "zc.buildout and either Setuptools or Distribute. "
                        "Defaults to PyPI."))
parser.add_option("--eggs",
                  help=("Specify a directory for storing eggs.  Defaults to "
                        "a temporary directory that is deleted when the "
                        "bootstrap script completes."))
parser.add_option("-t", "--accept-buildout-test-releases",
                  dest='accept_buildout_test_releases',
                  action="store_true", default=False,
                  help=("Normally, if you do not specify a --version, the "
                        "bootstrap script and buildout gets the newest "
                        "*final* versions of zc.buildout and its recipes and "
                        "extensions for you.  If you use this flag, "
                        "bootstrap and buildout will get the newest releases "
                        "even if they are alphas or betas."))
parser.add_option("-c", None, action="store", dest="config_file",
                   help=("Specify the path to the buildout configuration "
                         "file to be used."))

options, args = parser.parse_args()

# if -c was provided, we push it back into args for buildout's main function
if options.config_file is not None:
    args += ['-c', options.config_file]

if options.eggs:
    eggs_dir = os.path.abspath(os.path.expanduser(options.eggs))
else:
    eggs_dir = tempfile.mkdtemp()

if options.setup_source is None:
    if options.use_distribute:
        options.setup_source = distribute_source
    else:
        options.setup_source = setuptools_source

if options.accept_buildout_test_releases:
    args.append('buildout:accept-buildout-test-releases=true')
args.append('bootstrap')

try:
    import pkg_resources
    import setuptools  # A flag.  Sometimes pkg_resources is installed alone.
    if not hasattr(pkg_resources, '_distribute'):
        raise ImportError
except ImportError:
    ez_code = urllib2.urlopen(
        options.setup_source).read().replace('\r\n', '\n')
    ez = {}
    exec ez_code in ez
    setup_args = dict(to_dir=eggs_dir, download_delay=0)
    if options.download_base:
        setup_args['download_base'] = options.download_base
    if options.use_distribute:
        setup_args['no_fake'] = True
    ez['use_setuptools'](**setup_args)
    if 'pkg_resources' in sys.modules:
        reload(sys.modules['pkg_resources'])
    import pkg_resources
    # This does not (always?) update the default working set.  We will
    # do it.
    for path in sys.path:
        if path not in pkg_resources.working_set.entries:
            pkg_resources.working_set.add_entry(path)

cmd = [quote(sys.executable),
       '-c',
       quote('from setuptools.command.easy_install import main; main()'),
       '-mqNxd',
       quote(eggs_dir)]

if not has_broken_dash_S:
    cmd.insert(1, '-S')

find_links = options.download_base
if not find_links:
    find_links = os.environ.get('bootstrap-testing-find-links')
if find_links:
    cmd.extend(['-f', quote(find_links)])

if options.use_distribute:
    setup_requirement = 'distribute'
else:
    setup_requirement = 'setuptools'
ws = pkg_resources.working_set
setup_requirement_path = ws.find(
    pkg_resources.Requirement.parse(setup_requirement)).location
env = dict(
    os.environ,
    PYTHONPATH=setup_requirement_path)

requirement = 'zc.buildout'
version = options.version
if version is None and not options.accept_buildout_test_releases:
    # Figure out the most recent final version of zc.buildout.
    import setuptools.package_index
    _final_parts = '*final-', '*final'

    def _final_version(parsed_version):
        for part in parsed_version:
            if (part[:1] == '*') and (part not in _final_parts):
                return False
        return True
    index = setuptools.package_index.PackageIndex(
        search_path=[setup_requirement_path])
    if find_links:
        index.add_find_links((find_links,))
    req = pkg_resources.Requirement.parse(requirement)
    if index.obtain(req) is not None:
        best = []
        bestv = None
        for dist in index[req.project_name]:
            distv = dist.parsed_version
            if _final_version(distv):
                if bestv is None or distv > bestv:
                    best = [dist]
                    bestv = distv
                elif distv == bestv:
                    best.append(dist)
        if best:
            best.sort()
            version = best[-1].version
if version:
    requirement = '=='.join((requirement, version))
cmd.append(requirement)

if is_jython:
    import subprocess
    exitcode = subprocess.Popen(cmd, env=env).wait()
else:  # Windows prefers this, apparently; otherwise we would prefer subprocess
    exitcode = os.spawnle(*([os.P_WAIT, sys.executable] + cmd + [env]))
if exitcode != 0:
    sys.stdout.flush()
    sys.stderr.flush()
    print ("An error occurred when trying to install zc.buildout. "
           "Look above this message for any errors that "
           "were output by easy_install.")
    sys.exit(exitcode)

ws.add_entry(eggs_dir)
ws.require(requirement)
import zc.buildout.buildout
zc.buildout.buildout.main(args)
if not options.eggs:  # clean up temporary egg directory
    shutil.rmtree(eggs_dir)

########NEW FILE########
__FILENAME__ = cors
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
import fnmatch
import functools


CORS_PARAMETERS = ('cors_headers', 'cors_enabled', 'cors_origins',
                   'cors_credentials', 'cors_max_age',
                   'cors_expose_all_headers')


def get_cors_preflight_view(service):
    """Return a view for the OPTION method.

    Checks that the User-Agent is authorized to do a request to the server, and
    to this particular service, and add the various checks that are specified
    in http://www.w3.org/TR/cors/#resource-processing-model.
    """

    def _preflight_view(request):
        response = request.response
        origin = request.headers.get('Origin')
        supported_headers = service.cors_supported_headers

        if not origin:
            request.errors.add('header', 'Origin',
                               'this header is mandatory')

        requested_method = request.headers.get('Access-Control-Request-Method')
        if not requested_method:
            request.errors.add('header', 'Access-Control-Request-Method',
                               'this header is mandatory')

        if not (requested_method and origin):
            return

        requested_headers = (
            request.headers.get('Access-Control-Request-Headers', ()))

        if requested_headers:
            requested_headers = map(str.strip, requested_headers.split(', '))

        if requested_method not in service.cors_supported_methods:
            request.errors.add('header', 'Access-Control-Request-Method',
                               'Method not allowed')

        if not service.cors_expose_all_headers:
            for h in requested_headers:
                if not h.lower() in [s.lower() for s in supported_headers]:
                    request.errors.add(
                        'header',
                        'Access-Control-Request-Headers',
                        'Header "%s" not allowed' % h)

        supported_headers = set(supported_headers) | set(requested_headers)

        response.headers['Access-Control-Allow-Headers'] = (
                ','.join(supported_headers))

        response.headers['Access-Control-Allow-Methods'] = (
            ','.join(service.cors_supported_methods))

        max_age = service.cors_max_age_for(requested_method)
        if max_age is not None:
            response.headers['Access-Control-Max-Age'] = str(max_age)

        return ''
    return _preflight_view


def _get_method(request):
    """Return what's supposed to be the method for CORS operations.
    (e.g if the verb is options, look at the A-C-Request-Method header,
    otherwise return the HTTP verb).
    """
    if request.method == 'OPTIONS':
        method = request.headers.get('Access-Control-Request-Method',
                                     request.method)
    else:
        method = request.method
    return method


def ensure_origin(service, request, response=None):
    """Ensure that the origin header is set and allowed."""
    response = response or request.response

    # Don't check this twice.
    if not request.info.get('cors_checked', False):
        method = _get_method(request)

        origin = request.headers.get('Origin')
        if origin:
            if not any([fnmatch.fnmatchcase(origin, o)
                        for o in service.cors_origins_for(method)]):
                request.errors.add('header', 'Origin',
                                   '%s not allowed' % origin)
            else:
                if any([o == "*" for o in service.cors_origins_for(method)]):
                    response.headers['Access-Control-Allow-Origin'] = '*'
                else:
                    response.headers['Access-Control-Allow-Origin'] = origin
        request.info['cors_checked'] = True
    return response


def get_cors_validator(service):
    return functools.partial(ensure_origin, service)


def apply_cors_post_request(service, request, response):
    """Handles CORS-related post-request things.

    Add some response headers, such as the Expose-Headers and the
    Allow-Credentials ones.
    """
    response = ensure_origin(service, request, response)
    method = _get_method(request)

    if (service.cors_support_credentials(method) and
            not 'Access-Control-Allow-Credentials' in response.headers):
        response.headers['Access-Control-Allow-Credentials'] = 'true'

    if request.method is not 'OPTIONS':
        # Which headers are exposed?
        supported_headers = service.cors_supported_headers
        if supported_headers:
            response.headers['Access-Control-Expose-Headers'] = (
                    ', '.join(supported_headers))

    return response

########NEW FILE########
__FILENAME__ = errors
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
import simplejson as json


class Errors(list):
    """Holds Request errors
    """
    def __init__(self, request=None, status=400):
        self.request = request
        self.status = status
        super(Errors, self).__init__()

    def add(self, location, name=None, description=None, **kw):
        """Registers a new error."""
        self.append(dict(
            location=location,
            name=name,
            description=description, **kw))

    @classmethod
    def from_json(cls, string):
        """Transforms a json string into an `Errors` instance"""
        obj = json.loads(string)
        return Errors.from_list(obj.get('errors', []))

    @classmethod
    def from_list(cls, obj):
        """Transforms a python list into an `Errors` instance"""
        errors = Errors()
        for error in obj:
            errors.add(**error)
        return errors

########NEW FILE########
__FILENAME__ = sphinxext
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# Contributors: Vincent Fretin
"""
Sphinx extension that is able to convert a service into a documentation.
"""
import sys
from importlib import import_module

from cornice.util import to_list, is_string, PY3
from cornice.service import get_services, clear_services

import docutils
from docutils import nodes, core
from docutils.parsers.rst import Directive, directives
from docutils.writers.html4css1 import Writer, HTMLTranslator
from sphinx.util.docfields import DocFieldTransformer

MODULES = {}

def convert_to_list(argument):
    """Convert a comma separated list into a list of python values"""
    if argument is None:
        return []
    else:
        return [i.strip() for i in argument.split(',')]


def convert_to_list_required(argument):
    if argument is None:
        raise ValueError('argument required but none supplied')
    return convert_to_list(argument)


class ServiceDirective(Directive):
    """ Service directive.

    Injects sections in the documentation about the services registered in the
    given module.

    Usage, in a sphinx documentation::

        .. cornice-autodoc::
            :modules: your.module
            :services: name1, name2
            :service: name1 # no need to specify both services and service.
            :ignore: a comma separated list of services names to ignore

    """
    has_content = True
    option_spec = {'modules': convert_to_list_required,
                   'service': directives.unchanged,
                   'services': convert_to_list,
                   'ignore': convert_to_list}
    domain = 'cornice'
    doc_field_types = []

    def __init__(self, *args, **kwargs):
        super(ServiceDirective, self).__init__(*args, **kwargs)
        self.env = self.state.document.settings.env

    def run(self):
        # clear the SERVICES variable, which will allow to use this directive multiple times
        clear_services()

        # import the modules, which will populate the SERVICES variable.
        for module in self.options.get('modules'):
            if MODULES.has_key(module):
                reload(MODULES[module])
            else:
                MODULES[module] = import_module(module)

        names = self.options.get('services', [])

        service = self.options.get('service')
        if service is not None:
            names.append(service)

        # filter the services according to the options we got
        services = get_services(names=names or None,
                                exclude=self.options.get('exclude'))

        return [self._render_service(s) for s in services]

    def _render_service(self, service):
        service_id = "service-%d" % self.env.new_serialno('service')
        service_node = nodes.section(ids=[service_id])

        title = '%s service at %s' % (service.name.title(), service.path)
        service_node += nodes.title(text=title)

        if service.description is not None:
            service_node += rst2node(trim(service.description))

        for method, view, args in service.definitions:
            if method == 'HEAD':
                #Skip head - this is essentially duplicating the get docs.
                continue
            method_id = '%s-%s' % (service_id, method)
            method_node = nodes.section(ids=[method_id])
            method_node += nodes.title(text=method)

            if is_string(view):
                if 'klass' in args:
                    ob = args['klass']
                    view_ = getattr(ob, view.lower())
                    docstring = trim(view_.__doc__ or "") + '\n'
            else:
                docstring = trim(view.__doc__ or "") + '\n'

            if 'schema' in args:
                schema = args['schema']

                attrs_node = nodes.inline()
                for location in ('header', 'querystring', 'body'):
                    attributes = schema.get_attributes(location=location)
                    if attributes:
                        attrs_node += nodes.inline(
                                text='values in the %s' % location)
                        location_attrs = nodes.bullet_list()

                        for attr in attributes:
                            temp = nodes.list_item()
                            desc = "%s : " % attr.name

                            # Get attribute data-type
                            if hasattr(attr, 'type'):
                                attr_type = attr.type
                            elif hasattr(attr, 'typ'):
                                attr_type = attr.typ.__class__.__name__

                            desc += " %s, " % attr_type

                            if attr.required:
                                desc += "required "
                            else:
                                desc += "optional "

                            temp += nodes.inline(text=desc)
                            location_attrs += temp

                        attrs_node += location_attrs
                method_node += attrs_node

            for validator in args.get('validators', ()):
                if validator.__doc__ is not None:
                    docstring += trim(validator.__doc__)

            if 'accept' in args:
                accept = to_list(args['accept'])

                if callable(accept):
                    if accept.__doc__ is not None:
                        docstring += accept.__doc__.strip()
                else:
                    accept_node = nodes.strong(text='Accepted content types:')
                    node_accept_list = nodes.bullet_list()
                    accept_node += node_accept_list

                    for item in accept:
                        temp = nodes.list_item()
                        temp += nodes.inline(text=item)
                        node_accept_list += temp

                    method_node += accept_node

            node = rst2node(docstring)
            DocFieldTransformer(self).transform_all(node)
            if node is not None:
                method_node += node

            renderer = args['renderer']
            if renderer == 'simplejson':
                renderer = 'json'

            response = nodes.paragraph()

            response += nodes.strong(text='Response: %s' % renderer)
            method_node += response

            service_node += method_node

        return service_node


# Utils


def trim(docstring):
    """
    Remove the tabs to spaces, and remove the extra spaces / tabs that are in
    front of the text in docstrings.

    Implementation taken from http://www.python.org/dev/peps/pep-0257/
    """
    if not docstring:
        return ''
    # Convert tabs to spaces (following the normal Python rules)
    # and split into a list of lines:
    lines = docstring.expandtabs().splitlines()
    # Determine minimum indentation (first line doesn't count):
    indent = sys.maxsize
    for line in lines[1:]:
        stripped = line.lstrip()
        if stripped:
            indent = min(indent, len(line) - len(stripped))
    # Remove indentation (first line is special):
    trimmed = [lines[0].strip()]
    if indent < sys.maxsize:
        for line in lines[1:]:
            trimmed.append(line[indent:].rstrip())
    # Strip off trailing and leading blank lines:
    while trimmed and not trimmed[-1]:
        trimmed.pop()
    while trimmed and not trimmed[0]:
        trimmed.pop(0)
    # Return a single string:
    res = '\n'.join(trimmed)
    if not PY3 and not isinstance(res, unicode):
        res = res.decode('utf8')
    return res


class _HTMLFragmentTranslator(HTMLTranslator):
    def __init__(self, document):
        HTMLTranslator.__init__(self, document)
        self.head_prefix = ['', '', '', '', '']
        self.body_prefix = []
        self.body_suffix = []
        self.stylesheet = []

    def astext(self):
        return ''.join(self.body)


class _FragmentWriter(Writer):
    translator_class = _HTMLFragmentTranslator

    def apply_template(self):
        subs = self.interpolation_dict()
        return subs['body']


def rst2html(data):
    """Converts a reStructuredText into its HTML
    """
    if not data:
        return ''
    return core.publish_string(data, writer=_FragmentWriter())


class Env(object):
    temp_data = {}
    docname = ''


def rst2node(data):
    """Converts a reStructuredText into its node
    """
    if not data:
        return
    parser = docutils.parsers.rst.Parser()
    document = docutils.utils.new_document('<>')
    document.settings = docutils.frontend.OptionParser().get_default_values()
    document.settings.tab_width = 4
    document.settings.pep_references = False
    document.settings.rfc_references = False
    document.settings.env = Env()
    parser.parse(data, document)
    if len(document.children) == 1:
        return document.children[0]
    else:
        par = docutils.nodes.paragraph()
        for child in document.children:
            par += child
        return par


def setup(app):
    """Hook the directives when Sphinx ask for it."""
    app.add_directive('services', ServiceDirective)  # deprecated
    app.add_directive('cornice-autodoc', ServiceDirective)

########NEW FILE########
__FILENAME__ = spore
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
import re


URL_PLACEHOLDER = re.compile(r'\{([a-zA-Z0-9_-]*)\}')


def generate_spore_description(services, name, base_url, version, **kwargs):
    """Utility to turn cornice web services into a SPORE-readable file.

    See https://github.com/SPORE/specifications for more information on SPORE.
    """
    spore_doc = dict(
        name=name,
        base_url=base_url,
        version=version,
        expected_status=[200, ],
        methods={},
        **kwargs)

    for service in services:
        # the :foobar syntax should be removed.
        # see https://github.com/SPORE/specifications/issues/5
        service_path = URL_PLACEHOLDER.sub(':\g<1>', service.path)

        # get the list of placeholders
        service_params = URL_PLACEHOLDER.findall(service.path)

        for method, view, args in service.definitions:
            format_name = args['renderer']
            if 'json' in format_name:
                format_name = 'json'

            view_info = {
                'path': service_path,
                'method': method,
                'formats': [format_name]
            }
            if service_params:
                view_info['required_params'] = service_params

            if getattr(view, '__doc__'):
                view_info['description'] = view.__doc__

            # we have the values, but we need to merge this with
            # possible previous values for this method.
            method_name = '{method}_{service}'.format(
                    method=method.lower(), service=service.name.lower())
            spore_doc['methods'][method_name] = view_info

    return spore_doc

########NEW FILE########
__FILENAME__ = pyramidhook
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
import functools
import copy
import itertools

from pyramid.httpexceptions import (HTTPMethodNotAllowed, HTTPNotAcceptable,
                                    HTTPUnsupportedMediaType, HTTPException)
from pyramid.exceptions import PredicateMismatch

from cornice.service import decorate_view
from cornice.errors import Errors
from cornice.util import (
    is_string, to_list, match_accept_header, match_content_type_header,
    content_type_matches,
)
from cornice.cors import (
    get_cors_validator,
    get_cors_preflight_view,
    apply_cors_post_request,
    CORS_PARAMETERS
)


def make_route_factory(acl_factory):
    class ACLResource(object):
        def __init__(self, request):
            self.request = request
            self.__acl__ = acl_factory(request)

    return ACLResource


def get_fallback_view(service):
    """Fallback view for a given service, called when nothing else matches.

    This method provides the view logic to be executed when the request
    does not match any explicitly-defined view.  Its main responsibility
    is to produce an accurate error response, such as HTTPMethodNotAllowed,
    HTTPNotAcceptable or HTTPUnsupportedMediaType.
    """

    def _fallback_view(request):
        # Maybe we failed to match any definitions for the request method?
        if request.method not in service.defined_methods:
            response = HTTPMethodNotAllowed()
            response.allow = service.defined_methods
            raise response
        # Maybe we failed to match an acceptable content-type?
        # First search all the definitions to find the acceptable types.
        # XXX: precalculate this like the defined_methods list?
        acceptable = []
        supported_contenttypes = []
        for method, _, args in service.definitions:
            if method != request.method:
                continue

            if 'accept' in args:
                acceptable.extend(
                        service.get_acceptable(method, filter_callables=True))
                acceptable.extend(
                        request.info.get('acceptable', []))
                acceptable = list(set(acceptable))

                # Now check if that was actually the source of the problem.
                if not request.accept.best_match(acceptable):
                    request.errors.add(
                        'header', 'Accept',
                        'Accept header should be one of {0}'.format(
                            acceptable).encode('ascii'))
                    request.errors.status = HTTPNotAcceptable.code
                    error = service.error_handler(request.errors)
                    raise error

            if 'content_type' in args:
                supported_contenttypes.extend(
                        service.get_contenttypes(method,
                                                 filter_callables=True))
                supported_contenttypes.extend(
                        request.info.get('supported_contenttypes', []))
                supported_contenttypes = list(set(supported_contenttypes))

                # Now check if that was actually the source of the problem.
                if not content_type_matches(request, supported_contenttypes):
                    request.errors.add(
                        'header', 'Content-Type',
                        'Content-Type header should be one of {0}'.format(
                            supported_contenttypes).encode('ascii'))
                    request.errors.status = HTTPUnsupportedMediaType.code
                    error = service.error_handler(request.errors)
                    raise error

        # In the absence of further information about what went wrong,
        # let upstream deal with the mismatch.
        raise PredicateMismatch(service.name)
    return _fallback_view


def apply_filters(request, response):
    if request.matched_route is not None:
        # do some sanity checking on the response using filters
        services = request.registry.cornice_services
        pattern = request.matched_route.pattern
        service = services.get(pattern, None)
        if service is not None:
            kwargs, ob = getattr(request, "cornice_args", ({}, None))
            for _filter in kwargs.get('filters', []):
                if is_string(_filter) and ob is not None:
                    _filter = getattr(ob, _filter)
                try:
                    response = _filter(response, request)
                except TypeError:
                    response = _filter(response)
            if service.cors_enabled:
                apply_cors_post_request(service, request, response)

    return response


def handle_exceptions(exc, request):
    # At this stage, the checks done by the validators had been removed because
    # a new response started (the exception), so we need to do that again.
    if not isinstance(exc, HTTPException):
        raise
    request.info['cors_checked'] = False
    return apply_filters(request, exc)


def wrap_request(event):
    """Adds a "validated" dict, a custom "errors" object and an "info" dict to
    the request object if they don't already exists
    """
    request = event.request
    request.add_response_callback(apply_filters)

    if not hasattr(request, 'validated'):
        setattr(request, 'validated', {})

    if not hasattr(request, 'errors'):
        setattr(request, 'errors', Errors(request))

    if not hasattr(request, 'info'):
        setattr(request, 'info', {})


def register_service_views(config, service):
    """Register the routes of the given service into the pyramid router.

    :param config: the pyramid configuration object that will be populated.
    :param service: the service object containing the definitions
    """
    services = config.registry.cornice_services
    prefix = config.route_prefix or ''
    services[prefix + service.path] = service

    # keep track of the registered routes
    registered_routes = []

    # before doing anything else, register a view for the OPTIONS method
    # if we need to
    if service.cors_enabled and 'OPTIONS' not in service.defined_methods:
        service.add_view('options', view=get_cors_preflight_view(service))

    # register the fallback view, which takes care of returning good error
    # messages to the user-agent
    cors_validator = get_cors_validator(service)

    # Cornice-specific arguments that pyramid does not know about
    cornice_parameters = ('filters', 'validators', 'schema', 'klass',
                          'error_handler', 'deserializer') + CORS_PARAMETERS

    for method, view, args in service.definitions:

        args = copy.copy(args)  # make a copy of the dict to not modify it
        # Deepcopy only the params we're possibly passing on to pyramid
        # (Some of those in cornice_parameters, e.g. ``schema``, may contain
        # unpickleable values.)
        for item in args:
            if item not in cornice_parameters:
                args[item] = copy.deepcopy(args[item])

        args['request_method'] = method

        if service.cors_enabled:
            args['validators'].insert(0, cors_validator)

        decorated_view = decorate_view(view, dict(args), method)

        for item in cornice_parameters:
            if item in args:
                del args[item]

        # if acl is present, then convert it to a "factory"
        if 'acl' in args:
            args["factory"] = make_route_factory(args.pop('acl'))

        # 1. register route
        route_args = {}
        if 'factory' in args:
            route_args['factory'] = args.pop('factory')

        if 'traverse' in args:
            route_args['traverse'] = args.pop('traverse')

        # register the route name with the path if it's not already done
        if service.path not in registered_routes:
            config.add_route(service.name, service.path, **route_args)
            config.add_view(view=get_fallback_view(service),
                            route_name=service.name)
            registered_routes.append(service.path)
            config.commit()

        # 2. register view(s)
        # pop and compute predicates which get passed through to Pyramid 1:1

        predicate_definitions = _pop_complex_predicates(args)

        if predicate_definitions:
            for predicate_list in predicate_definitions:
                args = dict(args)  # make a copy of the dict to not modify it

                # prepare view args by evaluating complex predicates
                _mungle_view_args(args, predicate_list)

                # We register the same view multiple times with different
                # accept / content_type / custom_predicates arguments
                config.add_view(view=decorated_view, route_name=service.name,
                            **args)

        else:
            # it is a simple view, we don't need to loop on the definitions
            # and just add it one time.
            config.add_view(view=decorated_view, route_name=service.name,
                            **args)

        config.commit()


def _pop_complex_predicates(args):
    """
    Compute the cartesian product of "accept" and "content_type"
    fields to establish all possible predicate combinations.

    .. seealso::

        https://github.com/mozilla-services/cornice/pull/91#discussion_r3441384
    """

    # pop and prepare individual predicate lists
    accept_list = _pop_predicate_definition(args, 'accept')
    content_type_list = _pop_predicate_definition(args, 'content_type')

    # compute cartesian product of prepared lists, additionally
    # remove empty elements of input and output lists
    product_input = filter(None, [accept_list, content_type_list])

    # In Python 3, the filter() function returns an iterator, not a list.
    # http://getpython3.com/diveintopython3/porting-code-to-python-3-with-2to3.html#filter
    predicate_product = list(filter(None, itertools.product(*product_input)))

    return predicate_product


def _pop_predicate_definition(args, kind):
    """
    Build a dictionary enriched by "kind" of predicate definition list.
    This is required for evaluation in ``_mungle_view_args``.
    """
    values = to_list(args.pop(kind, ()))
    # In much the same way as filter(), the map() function [in Python 3] now
    # returns an iterator. (In Python 2, it returned a list.)
    # http://getpython3.com/diveintopython3/porting-code-to-python-3-with-2to3.html#map
    values = list(map(lambda value: {'kind': kind, 'value': value}, values))
    return values


def _mungle_view_args(args, predicate_list):
    """
    Prepare view args by evaluating complex predicates
    which get passed through to Pyramid 1:1.
    Also resolve predicate definitions passed as callables.

    .. seealso::

        https://github.com/mozilla-services/cornice/pull/91#discussion_r3441384
    """

    # map kind of argument value to function for resolving callables
    callable_map = {
        'accept': match_accept_header,
        'content_type': match_content_type_header,
    }

    # iterate and resolve all predicates
    for predicate_entry in predicate_list:

        kind = predicate_entry['kind']
        value = predicate_entry['value']

        # we need to build a custom predicate if argument value is a callable
        predicates = args.get('custom_predicates', [])
        if callable(value):
            func = callable_map.get(kind)
            if func:
                predicate_checker = functools.partial(func, value)
                predicates.append(predicate_checker)
                args['custom_predicates'] = predicates
            else:
                raise ValueError('No function defined for ' +
                    'handling callables for field "{0}"'.format(kind))
        else:
            # otherwise argument value is just a scalar
            args[kind] = value


def add_deserializer(config, content_type, deserializer):
    registry = config.registry

    def callback():
        if not hasattr(registry, 'cornice_deserializers'):
            registry.cornice_deserializers = {}
        registry.cornice_deserializers[content_type] = deserializer

    config.action(content_type, callable=callback)

########NEW FILE########
__FILENAME__ = resource
# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
from cornice import Service
try:
    import venusian
    VENUSIAN = True
except ImportError:
    VENUSIAN = False


def resource(depth=1, **kw):
    """Class decorator to declare resources.

    All the methods of this class named by the name of HTTP resources
    will be used as such. You can also prefix them by "collection_" and they
    will be treated as HTTP methods for the given collection path
    (collection_path), if any.

    Here is an example::

        @resource(collection_path='/users', path='/users/{id}')
    """
    def wrapper(klass):
        services = {}

        if 'collection_path' in kw:
            prefixes = ('collection_', '')
        else:
            prefixes = ('',)

        for prefix in prefixes:

            # get clean view arguments
            service_args = {}
            for k in list(kw):
                if k.startswith('collection_'):
                    if prefix == 'collection_':
                        service_args[k[len(prefix):]] = kw[k]
                elif k not in service_args:
                    service_args[k] = kw[k]

            # create service
            service_name = (service_args.pop('name', None)
                            or klass.__name__.lower())
            service_name = prefix + service_name
            service = services[service_name] = Service(name=service_name,
                                                       depth=2, **service_args)

            # initialize views
            for verb in ('get', 'post', 'put', 'delete', 'options', 'patch'):

                view_attr = prefix + verb
                meth = getattr(klass, view_attr, None)

                if meth is not None:
                    # if the method has a __views__ arguments, then it had
                    # been decorated by a @view decorator. get back the name of
                    # the decorated method so we can register it properly
                    views = getattr(meth, '__views__', [])
                    if views:
                        for view_args in views:
                            service.add_view(verb, view_attr, klass=klass,
                                              **view_args)
                    else:
                        service.add_view(verb, view_attr, klass=klass)

        setattr(klass, '_services', services)

        if VENUSIAN:
            def callback(context, name, ob):
                # get the callbacks registred by the inner services
                # and call them from here when the @resource classes are being
                # scanned by venusian.
                for service in services.values():
                    config = context.config.with_package(info.module)
                    config.add_cornice_service(service)

            info = venusian.attach(klass, callback, category='pyramid', depth=depth)
        return klass
    return wrapper


def view(**kw):
    """Method decorator to store view arguments when defining a resource with
    the @resource class decorator
    """
    def wrapper(func):
        # store view argument to use them later in @resource
        views = getattr(func, '__views__', None)
        if views is None:
            views = []
            setattr(func, '__views__', views)
        views.append(kw)
        return func
    return wrapper

########NEW FILE########
__FILENAME__ = schemas
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
from pyramid.path import DottedNameResolver
import webob.multidict
from cornice.util import to_list, extract_request_data


class CorniceSchema(object):
    """Defines a cornice schema"""

    def __init__(self, _colander_schema):
        self._colander_schema = _colander_schema
        self._colander_schema_runtime = None

    @property
    def colander_schema(self):
        if not self._colander_schema_runtime:
            schema = self._colander_schema
            schema = DottedNameResolver(__name__).maybe_resolve(schema)
            if callable(schema):
                schema = schema()
            self._colander_schema_runtime = schema
        return self._colander_schema_runtime

    def bind_attributes(self, request=None):
        schema = self.colander_schema
        if request:
            schema = schema.bind(request=request)
        return schema.children

    def get_attributes(self, location=("body", "header", "querystring"),
                       required=(True, False),
                       request=None):
        """Return a list of attributes that match the given criteria.

        By default, if nothing is specified, it will return all the attributes,
        without filtering anything.
        """
        attributes = self.bind_attributes(request)

        def _filter(attr):
            if not hasattr(attr, "location"):
                valid_location = 'body' in location
            else:
                valid_location = attr.location in to_list(location)
            return valid_location and attr.required in to_list(required)

        return list(filter(_filter, attributes))

    def as_dict(self):
        """returns a dict containing keys for the different attributes, and
        for each of them, a dict containing information about them::

            >>> schema.as_dict()
            {'foo': {'type': 'string',
                     'location': 'body',
                     'description': 'yeah',
                     'required': True},
             'bar': {'type': 'string',
                     'location': 'body',
                     'description': 'yeah',
                     'required': True}
             # ...
             }
        """
        attributes = self.bind_attributes()
        schema = {}
        for attr in attributes:
            schema[attr.name] = {
                'type': getattr(attr, 'type', attr.typ),
                'name': attr.name,
                'description': getattr(attr, 'description', ''),
                'required': getattr(attr, 'required', False),
            }

        return schema

    def unflatten(self, data):
        return self.colander_schema.unflatten(data)

    def flatten(self, data):
        return self.colander_schema.flatten(data)

    @classmethod
    def from_colander(klass, colander_schema):
        return CorniceSchema(colander_schema)


def validate_colander_schema(schema, request):
    """Validates that the request is conform to the given schema"""
    from colander import Invalid, Sequence, drop

    def _validate_fields(location, data):
        if location == 'body':
            try:
                original = data
                data = webob.multidict.MultiDict(schema.unflatten(data))
                data.update(original)
            except KeyError:
                pass

        for attr in schema.get_attributes(location=location,
                                          request=request):
            if attr.required and not attr.name in data:
                # missing
                request.errors.add(location, attr.name,
                                   "%s is missing" % attr.name)
            else:
                try:
                    if not attr.name in data:
                        deserialized = attr.deserialize()
                    else:
                        if (location == 'querystring' and
                                isinstance(attr.typ, Sequence)):
                            serialized = data.getall(attr.name)
                        else:
                            serialized = data[attr.name]
                        deserialized = attr.deserialize(serialized)
                except Invalid as e:
                    # the struct is invalid
                    try:
                        request.errors.add(location, attr.name,
                                           e.asdict()[attr.name])
                    except KeyError:
                        for k, v in e.asdict().items():
                            if k.startswith(attr.name):
                                request.errors.add(location, k, v)
                else:
                    if deserialized is not drop:
                        request.validated[attr.name] = deserialized

    qs, headers, body, path = extract_request_data(request)

    _validate_fields('path', path)
    _validate_fields('header', headers)
    _validate_fields('body', body)
    _validate_fields('querystring', qs)

    # validate unknown
    if schema.colander_schema.typ.unknown == 'raise':
        attrs = schema.get_attributes(location=('body', 'querystring'),
                                      request=request)
        params = list(qs.keys()) + list(body.keys())
        msg = '%s is not allowed'
        for param in set(params) - set([attr.name for attr in attrs]):
            request.errors.add('body' if param in body else 'querystring',
                               param, msg % param)

########NEW FILE########
__FILENAME__ = service
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
import functools
import warnings

from cornice.validators import (
    DEFAULT_VALIDATORS,
    DEFAULT_FILTERS,
)
from cornice.schemas import CorniceSchema, validate_colander_schema
from cornice.util import is_string, to_list, json_error

try:
    import venusian
    VENUSIAN = True
except ImportError:
    VENUSIAN = False

SERVICES = []


def clear_services():
    SERVICES[:] = []


def get_services(names=None, exclude=None):

    def _keep(service):
        if exclude is not None and service.name in exclude:
            # excluded !
            return False

        # in white list or no white list provided
        return names is None or service.name in names

    return [service for service in SERVICES if _keep(service)]


class Service(object):
    """Contains a service definition (in the definition attribute).

    A service is composed of a path and many potential methods, associated
    with context.

    All the class attributes defined in this class or in childs are considered
    default values.

    :param name:
        The name of the service. Should be unique among all the services.

    :param path:
        The path the service is available at. Should also be unique.

    :param renderer:
        The renderer that should be used by this service. Default value is
        'simplejson'.

    :param description:
        The description of what the webservice does. This is primarily intended
        for documentation purposes.

    :param validators:
        A list of callables to pass the request into before passing it to the
        associated view.

    :param filters:
        A list of callables to pass the response into before returning it to
        the client.

    :param accept:
        A list of ``Accept`` header values accepted for this service
        (or method if overwritten when defining a method).
        It can also be a callable, in which case the values will be
        discovered at runtime. If a callable is passed, it should be able
        to take the request as a first argument.

    :param content_type:
        A list of ``Content-Type`` header values accepted for this service
        (or method if overwritten when defining a method).
        It can also be a callable, in which case the values will be
        discovered at runtime. If a callable is passed, it should be able
        to take the request as a first argument.

    :param factory:
        A factory returning callables which return boolean values.  The
        callables take the request as their first argument and return boolean
        values.  This param is exclusive with the 'acl' one.

    :param acl:
        A callable defining the ACL (returns true or false, function of the
        given request). Exclusive with the 'factory' option.

    :param klass:
        The class to use when resolving views (if they are not callables)

    :param error_handler:
        A callable which is used to render responses following validation
        failures.  Defaults to 'json_error'.

    :param traverse:
        A traversal pattern that will be passed on route declaration and that
        will be used as the traversal path.

    There is also a number of parameters that are related to the support of
    CORS (Cross Origin Resource Sharing). You can read the CORS specification
    at http://www.w3.org/TR/cors/

    :param cors_enabled:
        To use if you especially want to disable CORS support for a particular
        service / method.

    :param cors_origins:
        The list of origins for CORS. You can use wildcards here if needed,
        e.g. ('list', 'of', '*.domain').

    :param cors_headers:
        The list of headers supported for the services.

    :param cors_credentials:
        Should the client send credential information (False by default).

    :param cors_max_age:
         Indicates how long the results of a preflight request can be cached in
         a preflight result cache.

    :param cors_expose_all_headers:
        If set to True, all the headers will be exposed and considered valid
        ones (Default: True). If set to False, all the headers need be
        explicitely mentionned with the cors_headers parameter.

    :param cors_policy:
        It may be easier to have an external object containing all the policy
        information related to CORS, e.g::

            >>> cors_policy = {'origins': ('*',), 'max_age': 42,
            ...                'credentials': True}

        You can pass a dict here and all the values will be
        unpacked and considered rather than the parameters starting by `cors_`
        here.

    See
    http://readthedocs.org/docs/pyramid/en/1.0-branch/glossary.html#term-acl
    for more information about ACLs.

    Service cornice instances also have methods :meth:`~get`, :meth:`~post`,
    :meth:`~put`, :meth:`~options` and :meth:`~delete` are decorators that can
    be used to decorate views.
    """
    renderer = 'simplejson'
    default_validators = DEFAULT_VALIDATORS
    default_filters = DEFAULT_FILTERS

    mandatory_arguments = ('renderer',)
    list_arguments = ('validators', 'filters', 'cors_headers', 'cors_origins')

    def __repr__(self):
        return u'<Service %s at %s>' % (self.name, self.path)

    def __init__(self, name, path, description=None, cors_policy=None, depth=1,
                 **kw):
        self.name = name
        self.path = path
        self.description = description
        self.cors_expose_all_headers = True
        self._schemas = {}
        self._cors_enabled = None

        if cors_policy:
            for key, value in cors_policy.items():
                kw.setdefault('cors_' + key, value)

        for key in self.list_arguments:
            # default_{validators,filters} and {filters,validators} doesn't
            # have to be mutables, so we need to create a new list from them
            extra = to_list(kw.get(key, []))
            kw[key] = []
            kw[key].extend(getattr(self, 'default_%s' % key, []))
            kw[key].extend(extra)

        self.arguments = self.get_arguments(kw)
        for key, value in self.arguments.items():
            # avoid squashing Service.decorator if ``decorator``
            # argument is used to specify a default pyramid view
            # decorator
            if key != 'decorator':
                setattr(self, key, value)

        if hasattr(self, 'factory') and hasattr(self, 'acl'):
            raise KeyError("Cannot specify both 'acl' and 'factory'")

        # instanciate some variables we use to keep track of what's defined for
        # this service.
        self.defined_methods = []
        self.definitions = []

        # add this service to the list of available services
        SERVICES.append(self)

        # register aliases for the decorators
        for verb in ('GET', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'PATCH'):
            setattr(self, verb.lower(),
                    functools.partial(self.decorator, verb))

        if VENUSIAN:
            # this callback will be called when config.scan (from pyramid) will
            # be triggered.
            def callback(context, name, ob):
                config = context.config.with_package(info.module)
                config.add_cornice_service(self)

            info = venusian.attach(self, callback, category='pyramid',
                                   depth=depth)

    def get_arguments(self, conf=None):
        """Return a dictionnary of arguments. Takes arguments from the :param
        conf: param and merges it with the arguments passed in the constructor.

        :param conf: the dictionnary to use.
        """
        if conf is None:
            conf = {}

        arguments = {}
        for arg in self.mandatory_arguments:
            # get the value from the passed conf, then from the instance, then
            # from the default class settings.
            arguments[arg] = conf.pop(arg, getattr(self, arg, None))

        for arg in self.list_arguments:
            # rather than overwriting, extend the defined lists if any.
            # take care of re-creating the lists before appening items to them,
            # to avoid modifications to the already existing ones
            value = list(getattr(self, arg, []))
            if arg in conf:
                value.extend(to_list(conf.pop(arg)))
            arguments[arg] = value

        # schema validation handling
        if 'schema' in conf:
            arguments['schema'] = (
                CorniceSchema.from_colander(conf.pop('schema')))

        # Allow custom error handler
        arguments['error_handler'] = conf.pop('error_handler',
                                              getattr(self, 'error_handler',
                                                      json_error))

        # exclude some validators or filters
        if 'exclude' in conf:
            for item in to_list(conf.pop('exclude')):
                for container in arguments['validators'], arguments['filters']:
                    if item in container:
                        container.remove(item)

        # also include the other key,value pair we don't know anything about
        arguments.update(conf)

        # if some keys have been defined service-wide, then we need to add
        # them to the returned dict.
        if hasattr(self, 'arguments'):
            for key, value in self.arguments.items():
                if key not in arguments:
                    arguments[key] = value

        return arguments

    def add_view(self, method, view, **kwargs):
        """Add a view to a method and arguments.

        All the :class:`Service` keyword params except `name` and `path`
        can be overwritten here. Additionally,
        :meth:`~cornice.service.Service.api` has following keyword params:

        :param method: The request method. Should be one of GET, POST, PUT,
                       DELETE, OPTIONS, TRACE or CONNECT.
        :param view: the view to hook to
        :param **kwargs: additional configuration for this view
        """
        method = method.upper()
        if 'schema' in kwargs:
            # this is deprecated and unusable because multiple schema
            # definitions for the same method will overwrite each other.
            # still here for legacy reasons: you'll get a warning if you try to
            # use it.
            self._schemas[method] = kwargs['schema']

        args = self.get_arguments(kwargs)
        if hasattr(self, 'get_view_wrapper'):
            view = self.get_view_wrapper(kwargs)(view)
        self.definitions.append((method, view, args))

        # keep track of the defined methods for the service
        if method not in self.defined_methods:
            self.defined_methods.append(method)

        # auto-define a HEAD method if we have a definition for GET.
        if method == 'GET':
            self.definitions.append(('HEAD', view, args))
            if 'HEAD' not in self.defined_methods:
                self.defined_methods.append('HEAD')

    def decorator(self, method, **kwargs):
        """Add the ability to define methods using python's decorators
        syntax.

        For instance, it is possible to do this with this method::

            service = Service("blah", "/blah")
            @service.decorator("get", accept="application/json")
            def my_view(request):
                pass
        """
        def wrapper(view):
            self.add_view(method, view, **kwargs)
            return view
        return wrapper

    def filter_argumentlist(self, method, argname, filter_callables=False):
        """
        Helper method to ``get_acceptable`` and ``get_contenttypes``. DRY.
        """
        result = []
        for meth, view, args in self.definitions:
            if meth.upper() == method.upper():
                result_tmp = to_list(args.get(argname))
                if filter_callables:
                    result_tmp = [a for a in result_tmp if not callable(a)]
                result.extend(result_tmp)
        return result

    def get_acceptable(self, method, filter_callables=False):
        """return a list of acceptable egress content-type headers that were
        defined for this service.

        :param method: the method to get the acceptable egress content-types
                       for.
        :param filter_callables: it is possible to give acceptable
                                 content-types dynamically, with callables.
                                 This toggles filtering the callables (default:
                                 False)
        """
        return self.filter_argumentlist(method, 'accept', filter_callables)

    def get_contenttypes(self, method, filter_callables=False):
        """return a list of supported ingress content-type headers that were
        defined for this service.

        :param method: the method to get the supported ingress content-types
                       for.
        :param filter_callables: it is possible to give supported
                                 content-types dynamically, with callables.
                                 This toggles filtering the callables (default:
                                 False)
        """
        return self.filter_argumentlist(method, 'content_type',
                                        filter_callables)

    def get_validators(self, method):
        """return a list of validators for the given method.

        :param method: the method to get the validators for.
        """
        validators = []
        for meth, view, args in self.definitions:
            if meth.upper() == method.upper() and 'validators' in args:
                for validator in args['validators']:
                    if validator not in validators:
                        validators.append(validator)
        return validators

    def schemas_for(self, method):
        """Returns a list of schemas defined for a given HTTP method.

        A tuple is returned, containing the schema and the arguments relative
        to it.
        """
        schemas = []
        for meth, view, args in self.definitions:
            if meth.upper() == method.upper() and 'schema' in args:
                schemas.append((args['schema'], args))
        return schemas

    @property
    def schemas(self):
        """Here for backward compatibility with the old API."""
        msg = "'Service.schemas' is deprecated. Use 'Service.definitions' "\
              "instead."
        warnings.warn(msg, DeprecationWarning)
        return self._schemas

    @property
    def cors_enabled(self):
        if self._cors_enabled is False:
            return False

        return bool(self.cors_origins or self._cors_enabled)

    @cors_enabled.setter
    def cors_enabled(self, value):
        self._cors_enabled = value

    @property
    def cors_supported_headers(self):
        """Return an iterable of supported headers for this service.

        The supported headers are defined by the :param headers: argument
        that is passed to services or methods, at definition time.
        """
        headers = set()
        for _, _, args in self.definitions:
            if args.get('cors_enabled', True):
                headers |= set(args.get('cors_headers', ()))
        return headers

    @property
    def cors_supported_methods(self):
        """Return an iterable of methods supported by CORS"""
        methods = []
        for meth, _, args in self.definitions:
            if args.get('cors_enabled', True) and meth not in methods:
                methods.append(meth)
        return methods

    @property
    def cors_supported_origins(self):
        origins = set(getattr(self, 'cors_origins', ()))
        for _, _, args in self.definitions:
            origins |= set(args.get('cors_origins', ()))
        return origins

    def cors_origins_for(self, method):
        """Return the list of origins supported for a given HTTP method"""
        origins = set()
        for meth, view, args in self.definitions:
            if meth.upper() == method.upper():
                origins |= set(args.get('cors_origins', ()))

        if not origins:
            origins = self.cors_origins
        return origins

    def cors_support_credentials(self, method=None):
        """Returns if the given method support credentials.

        :param method:
            The method to check the credentials support for
        """
        for meth, view, args in self.definitions:
            if meth.upper() == method.upper():
                return args.get('cors_credentials', False)

        if getattr(self, 'cors_credentials', False):
            return self.cors_credentials
        return False

    def cors_max_age_for(self, method=None):
        for meth, view, args in self.definitions:
            if meth.upper() == method.upper():
                return args.get('cors_max_age', False)

        return getattr(self, 'cors_max_age', None)


def decorate_view(view, args, method):
    """Decorate a given view with cornice niceties.

    This function returns a function with the same signature than the one
    you give as :param view:

    :param view: the view to decorate
    :param args: the args to use for the decoration
    :param method: the HTTP method
    """
    def wrapper(request):
        # if the args contain a klass argument then use it to resolve the view
        # location (if the view argument isn't a callable)
        ob = None
        view_ = view
        if 'klass' in args and not callable(view):
            params = dict(request=request)
            if 'factory' in args and 'acl' not in args:
                params['context'] = request.context
            ob = args['klass'](**params)
            if is_string(view):
                view_ = getattr(ob, view.lower())

        # set data deserializer
        if 'deserializer' in args:
            request.deserializer = args['deserializer']

        # do schema validation
        if 'schema' in args:
            validate_colander_schema(args['schema'], request)
        elif hasattr(ob, 'schema'):
            validate_colander_schema(ob.schema, request)

        # the validators can either be a list of callables or contain some
        # non-callable values. In which case we want to resolve them using the
        # object if any
        validators = args.get('validators', ())
        for validator in validators:
            if is_string(validator) and ob is not None:
                validator = getattr(ob, validator)
            validator(request)

        # only call the view if we don't have validation errors
        if len(request.errors) == 0:
            # if we have an object, the request had already been passed to it
            if ob:
                response = view_()
            else:
                response = view_(request)

        # check for errors and return them if any
        if len(request.errors) > 0:
            # We already checked for CORS, but since the response is created
            # again, we want to do that again before returning the response.
            request.info['cors_checked'] = False
            return args['error_handler'](request.errors)

        # We can't apply filters at this level, since "response" may not have
        # been rendered into a proper Response object yet.  Instead, give the
        # request a reference to its api_kwargs so that a tween can apply them.
        # We also pass the object we created (if any) so we can use it to find
        # the filters that are in fact methods.
        request.cornice_args = (args, ob)
        return response

    # return the wrapper, not the function, keep the same signature
    functools.wraps(wrapper)
    return wrapper

########NEW FILE########
__FILENAME__ = test_sphinxext
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
from cornice.tests.support import TestCase
from cornice.ext.sphinxext import rst2html


class TestUtil(TestCase):

    def test_rendering(self):
        text = '**simple render**'
        res = rst2html(text)
        self.assertEqual(res, b'<p><strong>simple render</strong></p>')
        self.assertEqual(rst2html(''), '')

########NEW FILE########
__FILENAME__ = test_spore
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
import os
import json
from rxjson import Rx
from cornice.tests.support import TestCase
from cornice.service import Service, get_services
from cornice.ext.spore import generate_spore_description

HERE = os.path.dirname(os.path.abspath(__file__))


class TestSporeGeneration(TestCase):

    def _define_coffee_methods(self, service):
        @service.get()
        def get_coffee(request):
            pass

    def test_generate_spore_description(self):

        coffees = Service(name='Coffees', path='/coffee')
        coffee = Service(name='coffee', path='/coffee/{bar}/{id}')

        @coffees.post()
        def post_coffees(request):
            """Post information about the coffee"""
            return "ok"

        self._define_coffee_methods(coffee)
        self._define_coffee_methods(coffees)

        services = get_services(names=('coffee', 'Coffees'))
        spore = generate_spore_description(
                services, name="oh yeah",
                base_url="http://localhost/", version="1.0")

        # basic fields
        self.assertEqual(spore['name'], "oh yeah")
        self.assertEqual(spore['base_url'], "http://localhost/")
        self.assertEqual(spore['version'], "1.0")

        # methods
        methods = spore['methods']
        self.assertIn('get_coffees', methods)
        self.assertDictEqual(methods['get_coffees'], {
            'path': '/coffee',
            'method': 'GET',
            'formats': ['json'],
            })

        self.assertIn('post_coffees', methods)
        self.assertDictEqual(methods['post_coffees'], {
            'path': '/coffee',
            'method': 'POST',
            'formats': ['json'],
            'description': post_coffees.__doc__
            })

        self.assertIn('get_coffee', methods)
        self.assertDictEqual(methods['get_coffee'], {
            'path': '/coffee/:bar/:id',
            'method': 'GET',
            'formats': ['json'],
            'required_params': ['bar', 'id']
            })

    def test_rxjson_spore(self):
        rx = Rx.Factory({'register_core_types': True})

        coffees = Service(name='Coffees', path='/coffee')
        coffee = Service(name='coffee', path='/coffee/{bar}/{id}')

        self._define_coffee_methods(coffee)
        self._define_coffee_methods(coffees)

        services = get_services(names=('coffee', 'Coffees'))
        spore = generate_spore_description(
                services, name="oh yeah",
                base_url="http://localhost/", version="1.0")

        with open(os.path.join(HERE, 'spore_validation.rx')) as f:
            spore_json_schema = json.loads(f.read())
            spore_schema = rx.make_schema(spore_json_schema)
            self.assertTrue(spore_schema.check(spore))

########NEW FILE########
__FILENAME__ = schema

try:
    from colander import MappingSchema, SchemaNode, String
    COLANDER = True
except ImportError:
    COLANDER = False

if COLANDER:

    class AccountSchema(MappingSchema):
        nickname = SchemaNode(String(), location='body', type='str')
        city = SchemaNode(String(), location='body', type='str')

########NEW FILE########
__FILENAME__ = support
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
import logging
import logging.handlers
import weakref

try:
    from unittest2 import TestCase
except ImportError:
    # Maybe we're running in python2.7?
    from unittest import TestCase  # NOQA

from webob.dec import wsgify
from webob import exc
from pyramid.httpexceptions import HTTPException
from pyramid import testing


logger = logging.getLogger('cornice')


class DummyContext(object):

    def __repr__(self):
        return 'context!'


class DummyRequest(testing.DummyRequest):
    errors = []
    def __init__(self, *args, **kwargs):
        super(DummyRequest, self).__init__(*args, **kwargs)
        self.context = DummyContext()


def dummy_factory(request):
    return DummyContext()


# stolen from the packaging stdlib testsuite tools


class _TestHandler(logging.handlers.BufferingHandler):
    # stolen and adapted from test.support

    def __init__(self):
        logging.handlers.BufferingHandler.__init__(self, 0)
        self.setLevel(logging.DEBUG)

    def shouldFlush(self):
        return False

    def emit(self, record):
        self.buffer.append(record)


class LoggingCatcher(object):
    """TestCase-compatible mixin to receive logging calls.

    Upon setUp, instances of this classes get a BufferingHandler that's
    configured to record all messages logged to the 'cornice' logger
    """

    def setUp(self):
        super(LoggingCatcher, self).setUp()
        self.loghandler = handler = _TestHandler()
        self._old_level = logger.level
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)  # we want all messages

    def tearDown(self):
        handler = self.loghandler
        # All this is necessary to properly shut down the logging system and
        # avoid a regrtest complaint.  Thanks to Vinay Sajip for the help.
        handler.close()
        logger.removeHandler(handler)
        for ref in weakref.getweakrefs(handler):
            logging._removeHandlerRef(ref)
        del self.loghandler
        logger.setLevel(self._old_level)
        super(LoggingCatcher, self).tearDown()

    def get_logs(self, level=logging.WARNING, flush=True):
        """Return all log messages with given level.

        *level* defaults to logging.WARNING.

        For log calls with arguments (i.e.  logger.info('bla bla %r', arg)),
        the messages will be formatted before being returned (e.g. "bla bla
        'thing'").

        Returns a list.  Automatically flushes the loghandler after being
        called, unless *flush* is False (this is useful to get e.g. all
        warnings then all info messages).
        """
        messages = [log.getMessage() for log in self.loghandler.buffer
                    if log.levelno == level]
        if flush:
            self.loghandler.flush()
        return messages


class CatchErrors(object):
    def __init__(self, app):
        self.app = app
        if hasattr(app, 'registry'):
            self.registry = app.registry

    @wsgify
    def __call__(self, request):
        try:
            return request.get_response(self.app)
        except (exc.HTTPException, HTTPException) as e:
            return e

########NEW FILE########
__FILENAME__ = test_cors
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
from pyramid import testing
from pyramid.exceptions import NotFound
from pyramid.response import Response

from webtest import TestApp

from cornice.service import Service
from cornice.tests.support import TestCase, CatchErrors


squirel = Service(path='/squirel', name='squirel', cors_origins=('foobar',))
spam = Service(path='/spam', name='spam', cors_origins=('*',))
eggs = Service(path='/eggs', name='egg', cors_origins=('*',),
               cors_expose_all_headers=False)
bacon = Service(path='/bacon/{type}', name='bacon', cors_origins=('*',))


class Klass(object):
    """
    Class implementation of a service
    """
    def __init__(self, request):
        self.request = request

    def post(self):
        return "moar squirels (take care)"

cors_policy = {'origins': ('*',), 'enabled': True}

cors_klass = Service(name='cors_klass',
                     path='/cors_klass',
                     klass=Klass,
                     cors_policy=cors_policy)
cors_klass.add_view('post', 'post')


@squirel.get(cors_origins=('notmyidea.org',))
def get_squirel(request):
    return "squirels"


@squirel.post(cors_enabled=False, cors_headers=('X-Another-Header'))
def post_squirel(request):
    return "moar squirels (take care)"


@squirel.put(cors_headers=('X-My-Header',))
def put_squirel(request):
    return "squirels!"


@spam.get(cors_credentials=True, cors_headers=('X-My-Header'),
          cors_max_age=42)
def gimme_some_spam_please(request):
    return 'spam'


@spam.post()
def moar_spam(request):
    return 'moar spam'


def is_bacon_good(request):
    if not request.matchdict['type'].endswith('good'):
        request.errors.add('querystring', 'type', 'should be better!')


@bacon.get(validators=is_bacon_good)
def get_some_bacon(request):
    # Okay, you there. Bear in mind, the only kind of bacon existing is 'good'.
    if request.matchdict['type'] != 'good':
        raise NotFound(detail='Not. Found.')
    return "yay"

from pyramid.view import view_config


@view_config(route_name='noservice')
def noservice(request):
    return Response('No Service here.')


class TestCORS(TestCase):

    def setUp(self):
        self.config = testing.setUp()
        self.config.include("cornice")
        self.config.add_route('noservice', '/noservice')

        self.config.scan("cornice.tests.test_cors")
        self.app = TestApp(CatchErrors(self.config.make_wsgi_app()))

        def tearDown(self):
            testing.tearDown()

    def test_preflight_cors_klass_post(self):
        resp = self.app.options('/cors_klass',
                                status=200,
                                headers={
                                    'Origin': 'lolnet.org',
                                    'Access-Control-Request-Method': 'POST'})
        self.assertEqual('POST,OPTIONS', dict(resp.headers)['Access-Control-Allow-Methods'])

    def test_preflight_cors_klass_put(self):
        resp = self.app.options('/cors_klass',
                                status=400,
                                headers={
                                    'Origin': 'lolnet.org',
                                    'Access-Control-Request-Method': 'PUT'})

    def test_preflight_missing_headers(self):
        # we should have an OPTION method defined.
        # If we just try to reach it, without using correct headers:
        # "Access-Control-Request-Method"or without the "Origin" header,
        # we should get a 400.
        resp = self.app.options('/squirel', status=400)
        self.assertEqual(len(resp.json['errors']), 2)

    def test_preflight_missing_origin(self):

        resp = self.app.options(
            '/squirel',
            headers={'Access-Control-Request-Method': 'GET'},
            status=400)
        self.assertEqual(len(resp.json['errors']), 1)

    def test_preflight_missing_request_method(self):

        resp = self.app.options(
            '/squirel',
            headers={'Origin': 'foobar.org'},
            status=400)

        self.assertEqual(len(resp.json['errors']), 1)

    def test_preflight_incorrect_origin(self):
        # we put "lolnet.org" where only "notmyidea.org" is authorized
        resp = self.app.options(
            '/squirel',
            headers={'Origin': 'lolnet.org',
                     'Access-Control-Request-Method': 'GET'},
            status=400)
        self.assertEqual(len(resp.json['errors']), 1)

    def test_preflight_correct_origin(self):
        resp = self.app.options(
            '/squirel',
            headers={'Origin': 'notmyidea.org',
                     'Access-Control-Request-Method': 'GET'})
        self.assertEqual(
            resp.headers['Access-Control-Allow-Origin'],
            'notmyidea.org')

        allowed_methods = (resp.headers['Access-Control-Allow-Methods']
                           .split(','))

        self.assertNotIn('POST', allowed_methods)
        self.assertIn('GET', allowed_methods)
        self.assertIn('PUT', allowed_methods)
        self.assertIn('HEAD', allowed_methods)

        allowed_headers = (resp.headers['Access-Control-Allow-Headers']
                           .split(','))

        self.assertIn('X-My-Header', allowed_headers)
        self.assertNotIn('X-Another-Header', allowed_headers)

    def test_preflight_deactivated_method(self):
        self.app.options('/squirel',
            headers={'Origin': 'notmyidea.org',
                     'Access-Control-Request-Method': 'POST'},
            status=400)

    def test_preflight_origin_not_allowed_for_method(self):
        self.app.options('/squirel',
            headers={'Origin': 'notmyidea.org',
                     'Access-Control-Request-Method': 'PUT'},
            status=400)

    def test_preflight_credentials_are_supported(self):
        resp = self.app.options('/spam',
            headers={'Origin': 'notmyidea.org',
                     'Access-Control-Request-Method': 'GET'})

        self.assertIn('Access-Control-Allow-Credentials', resp.headers)
        self.assertEqual(resp.headers['Access-Control-Allow-Credentials'],
                          'true')

    def test_preflight_credentials_header_not_included_when_not_needed(self):
        resp = self.app.options('/spam',
            headers={'Origin': 'notmyidea.org',
                     'Access-Control-Request-Method': 'POST'})

        self.assertNotIn('Access-Control-Allow-Credentials', resp.headers)

    def test_preflight_contains_max_age(self):
        resp = self.app.options('/spam',
                headers={'Origin': 'notmyidea.org',
                         'Access-Control-Request-Method': 'GET'})

        self.assertIn('Access-Control-Max-Age', resp.headers)
        self.assertEqual(resp.headers['Access-Control-Max-Age'], '42')

    def test_resp_dont_include_allow_origin(self):
        resp = self.app.get('/squirel')  # omit the Origin header
        self.assertNotIn('Access-Control-Allow-Origin', resp.headers)
        self.assertEqual(resp.json, 'squirels')

    def test_resp_allow_origin_wildcard(self):
        resp = self.app.options(
            '/cors_klass',
            status=200,
            headers={
                'Origin': 'lolnet.org',
                'Access-Control-Request-Method': 'POST'})
        self.assertEqual(resp.headers['Access-Control-Allow-Origin'], '*')

    def test_responses_include_an_allow_origin_header(self):
        resp = self.app.get('/squirel', headers={'Origin': 'notmyidea.org'})
        self.assertIn('Access-Control-Allow-Origin', resp.headers)
        self.assertEqual(resp.headers['Access-Control-Allow-Origin'],
                          'notmyidea.org')

    def test_credentials_are_included(self):
        resp = self.app.get('/spam', headers={'Origin': 'notmyidea.org'})
        self.assertIn('Access-Control-Allow-Credentials', resp.headers)
        self.assertEqual(resp.headers['Access-Control-Allow-Credentials'],
                          'true')

    def test_headers_are_exposed(self):
        resp = self.app.get('/squirel', headers={'Origin': 'notmyidea.org'})
        self.assertIn('Access-Control-Expose-Headers', resp.headers)

        headers = resp.headers['Access-Control-Expose-Headers'].split(',')
        self.assertIn('X-My-Header', headers)

    def test_preflight_request_headers_are_included(self):
        resp = self.app.options('/squirel',
            headers={'Origin': 'notmyidea.org',
                     'Access-Control-Request-Method': 'GET',
                     'Access-Control-Request-Headers': 'foo,    bar,baz  '})
        # The specification says we can have any number of LWS (Linear white
        # spaces) in the values and that it should be removed.

        # per default, they should be authorized, and returned in the list of
        # authorized headers
        headers = resp.headers['Access-Control-Allow-Headers'].split(',')
        self.assertIn('foo', headers)
        self.assertIn('bar', headers)
        self.assertIn('baz', headers)

    def test_preflight_request_headers_isnt_too_permissive(self):
        self.app.options('/eggs',
            headers={'Origin': 'notmyidea.org',
                     'Access-Control-Request-Method': 'GET',
                     'Access-Control-Request-Headers': 'foo,bar,baz'},
            status=400)

    def test_preflight_headers_arent_case_sensitive(self):
        self.app.options('/spam', headers={
            'Origin': 'notmyidea.org',
            'Access-Control-Request-Method': 'GET',
            'Access-Control-Request-Headers': 'x-my-header', })

    def test_400_returns_CORS_headers(self):
        resp = self.app.get('/bacon/not', status=400,
                            headers={'Origin': 'notmyidea.org'})
        self.assertIn('Access-Control-Allow-Origin', resp.headers)

    def test_404_returns_CORS_headers(self):
        resp = self.app.get('/bacon/notgood', status=404,
                            headers={'Origin': 'notmyidea.org'})
        self.assertIn('Access-Control-Allow-Origin', resp.headers)

    def test_existing_non_service_route(self):
        resp = self.app.get('/noservice', status=200,
                            headers={'Origin': 'notmyidea.org'})
        self.assertEqual(resp.body, b'No Service here.')

########NEW FILE########
__FILENAME__ = test_init
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
from pyramid import testing
from webtest import TestApp
import mock

from cornice.tests.support import TestCase, CatchErrors


class TestCorniceSetup(TestCase):

    def setUp(self):
        self._apply_called = False

        def _apply(request, response):
            self._apply_called = True
            return response

        self._apply = _apply
        self.config = testing.setUp()

    def _get_app(self):
        self.config.include('cornice')
        self.config.scan("cornice.tests.test_init")
        return TestApp(CatchErrors(self.config.make_wsgi_app()))

    def test_exception_handling_is_included_by_default(self):
        app = self._get_app()
        with mock.patch('cornice.pyramidhook.apply_filters', self._apply):
            app.post('/foo', status=404)
            self.assertTrue(self._apply_called)

    def test_exception_handling_can_be_disabled(self):
        self.config.add_settings(handle_exceptions=False)
        app = self._get_app()
        with mock.patch('cornice.pyramidhook.apply_filters', self._apply):
            app.post('/foo', status=404)
            self.assertFalse(self._apply_called)

########NEW FILE########
__FILENAME__ = test_pyramidhook
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
from cornice.tests.support import TestCase

from pyramid import testing
from pyramid.httpexceptions import HTTPNotFound
from pyramid.response import Response
from pyramid.security import Allow
import colander

from webtest import TestApp

from cornice import Service
from cornice.tests.support import CatchErrors
from cornice.tests.support import dummy_factory

from cornice.pyramidhook import register_service_views

from mock import MagicMock

service = Service(name="service", path="/service")


@service.get()
def return_404(request):
    raise HTTPNotFound()


def my_acl(request):
    return [(Allow, 'bob', 'write')]


@service.delete(acl=my_acl)
def return_yay(request):
    return "yay"


class TemperatureCooler(object):
    def __init__(self, request, context=None):
        self.request = request
        self.context = context

    def get_fresh_air(self):
        resp = Response()
        resp.text = u'air with ' + repr(self.context)
        return resp

    def make_it_fresh(self, response):
        response.text = u'fresh ' + response.text
        return response

    def check_temperature(self, request):
        if not 'X-Temperature' in request.headers:
            request.errors.add('header', 'X-Temperature')

tc = Service(name="TemperatureCooler", path="/fresh-air",
             klass=TemperatureCooler, factory=dummy_factory)
tc.add_view("GET", "get_fresh_air", filters=('make_it_fresh',),
            validators=('check_temperature',))


class TestService(TestCase):

    def setUp(self):
        self.config = testing.setUp()
        self.config.include("cornice")
        self.config.scan("cornice.tests.test_service")
        self.config.scan("cornice.tests.test_pyramidhook")
        self.app = TestApp(CatchErrors(self.config.make_wsgi_app()))

    def tearDown(self):
        testing.tearDown()

    def test_404(self):
        # a get on a resource that explicitely return a 404 should return
        # 404
        self.app.get("/service", status=404)

    def test_405(self):
        # calling a unknown verb on an existing resource should return a 405
        self.app.post("/service", status=405)

    def test_acl_support(self):
        self.app.delete('/service')

    def test_class_support(self):
        self.app.get('/fresh-air', status=400)
        resp = self.app.get('/fresh-air', headers={'X-Temperature': '50'})
        self.assertEqual(resp.body, b'fresh air with context!')


class WrapperService(Service):
    def get_view_wrapper(self, kw):
        def upper_wrapper(func):
            def upperizer(*args, **kwargs):
                result = func(*args, **kwargs)
                return result.upper()
            return upperizer
        return upper_wrapper


wrapper_service = WrapperService(name='wrapperservice', path='/wrapperservice')


@wrapper_service.get()
def return_foo(request):
    return 'foo'


class TestServiceWithWrapper(TestCase):
    def setUp(self):
        self.config = testing.setUp()
        self.config.include("cornice")
        self.config.scan("cornice.tests.test_pyramidhook")
        self.app = TestApp(CatchErrors(self.config.make_wsgi_app()))

    def tearDown(self):
        testing.tearDown()

    def test_wrapped(self):
        result = self.app.get('/wrapperservice')
        self.assertEqual(result.json, 'FOO')


test_service = Service(name="jardinet", path="/jardinet", traverse="/jardinet")
test_service.add_view('GET', lambda _:_)


class TestRouteWithTraverse(TestCase):

    def test_route_construction(self):
        config = MagicMock()
        config.add_route = MagicMock()

        register_service_views(config, test_service)
        self.assertTrue(
                ('traverse', '/jardinet'),
                config.add_route.called_args,
            )

    def test_route_with_prefix(self):
        config = testing.setUp(settings={})
        config.add_route = MagicMock()
        config.route_prefix = '/prefix'
        config.registry.cornice_services = {}
        config.add_directive('add_cornice_service', register_service_views)
        config.scan("cornice.tests.test_pyramidhook")

        services = config.registry.cornice_services
        self.assertTrue('/prefix/wrapperservice' in services)


class NonpickableSchema(colander.Schema):
    # Compiled regexs are, apparently, non-pickleable
    s = colander.SchemaNode(colander.String(), validator=colander.Regex('.'))


class TestServiceWithNonpickleableSchema(TestCase):
    def setUp(self):
        self.config = testing.setUp()
        self.config.registry.cornice_services = {}

    def tearDown(self):
        testing.tearDown()

    def test(self):
        service = Service(name="test", path="/", schema=NonpickableSchema())
        service.add_view('GET', lambda _:_)
        register_service_views(self.config, service)

########NEW FILE########
__FILENAME__ = test_resource
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
import json

from pyramid import testing
from webtest import TestApp

from cornice.resource import resource
from cornice.resource import view
from cornice.schemas import CorniceSchema
from cornice.tests import validationapp
from cornice.tests.support import TestCase, CatchErrors
from cornice.tests.support import dummy_factory


USERS = {1: {'name': 'gawel'}, 2: {'name': 'tarek'}}


@resource(collection_path='/users', path='/users/{id}',
          name='user_service', factory=dummy_factory)
class User(object):

    def __init__(self, request, context=None):
        self.request = request
        self.context = context

    def collection_get(self):
        return {'users': list(USERS.keys())}

    @view(renderer='jsonp')
    @view(renderer='json')
    def get(self):
        return USERS.get(int(self.request.matchdict['id']))

    @view(renderer='json', accept='text/json')
    #@view(renderer='jsonp', accept='application/json')
    def collection_post(self):
        return {'test': 'yeah'}

    def patch(self):
        return {'test': 'yeah'}

    def collection_patch(self):
        return {'test': 'yeah'}

    def put(self):
        return dict(type=repr(self.context))


class TestResource(TestCase):

    def setUp(self):
        from pyramid.renderers import JSONP
        self.config = testing.setUp()
        self.config.add_renderer('jsonp', JSONP(param_name='callback'))
        self.config.include("cornice")
        self.config.scan("cornice.tests.test_resource")
        self.app = TestApp(CatchErrors(self.config.make_wsgi_app()))

    def tearDown(self):
        testing.tearDown()

    def test_basic_resource(self):
        from pkg_resources import parse_version, get_distribution
        current_version = parse_version(get_distribution('pyramid').version)

        self.assertEqual(self.app.get("/users").json, {'users': [1, 2]})

        self.assertEqual(self.app.get("/users/1").json, {'name': 'gawel'})

        resp = self.app.get("/users/1?callback=test")

        if current_version < parse_version('1.5a4'):
            self.assertEqual(resp.body, b'test({"name": "gawel"})', resp.body)
        else:
            self.assertEqual(resp.body, b'test({"name": "gawel"});', resp.body)

    def test_accept_headers(self):
        # the accept headers should work even in case they're specified in a
        # resource method
        self.assertEqual(
            self.app.post("/users", headers={'Accept': 'text/json'},
                          params=json.dumps({'test': 'yeah'})).json,
            {'test': 'yeah'})

    def patch(self, *args, **kwargs):
        return self.app._gen_request('PATCH', *args, **kwargs)

    def test_head_and_patch(self):
        self.app.head("/users")
        self.app.head("/users/1")

        self.assertEqual(
            self.patch("/users").json,
            {'test': 'yeah'})

        self.assertEqual(
            self.patch("/users/1").json,
            {'test': 'yeah'})

    def test_context_factory(self):
        self.assertEqual(self.app.put('/users/1').json, {'type': 'context!'})

    def test_explicit_collection_service_name(self):
        route_url = testing.DummyRequest().route_url
        self.assert_(route_url('collection_user_service'))  # service must exist

    def test_explicit_service_name(self):
        route_url = testing.DummyRequest().route_url
        self.assert_(route_url('user_service', id=42))  # service must exist

    if validationapp.COLANDER:
        def test_schema_on_resource(self):
            User.schema = CorniceSchema.from_colander(
                    validationapp.FooBarSchema)
            result = self.patch("/users/1", status=400).json
            self.assertEquals(
                [(e['name'], e['description']) for e in result['errors']], [
                    ('foo', 'foo is missing'),
                    ('bar', 'bar is missing'),
                    ('yeah', 'yeah is missing'),
                ])


class NonAutocommittingConfigurationTestResource(TestCase):
    """
    Test that we don't fail Pyramid's conflict detection when using a manually-
    committing :class:`pyramid.config.Configurator` instance.
    """

    def setUp(self):
        from pyramid.renderers import JSONP
        self.config = testing.setUp(autocommit=False)
        self.config.add_renderer('jsonp', JSONP(param_name='callback'))
        self.config.include("cornice")
        self.config.scan("cornice.tests.test_resource")
        self.app = TestApp(CatchErrors(self.config.make_wsgi_app()))

    def tearDown(self):
        testing.tearDown()

    def test_get(self):
        self.app.get('/users/1')

########NEW FILE########
__FILENAME__ = test_schemas
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
from cornice.errors import Errors
from cornice.tests.support import TestCase
from cornice.schemas import CorniceSchema, validate_colander_schema
from cornice.util import extract_json_data

try:
    from colander import (
        deferred,
        Mapping,
        MappingSchema,
        SchemaNode,
        String,
        Int,
        OneOf,
        drop
    )
    COLANDER = True
except ImportError:
    COLANDER = False

if COLANDER:

    @deferred
    def deferred_validator(node, kw):
        """
        This is a deferred validator that changes its own behavior based on
        request object being passed, thus allowing for validation of fields
        depending on other field values.

        This example shows how to validate a body field based on a dummy
        header value, using OneOf validator with different choices
        """
        request = kw['request']
        if request['x-foo'] == 'version_a':
            return OneOf(['a', 'b'])
        else:
            return OneOf(['c', 'd'])

    class TestingSchema(MappingSchema):
        foo = SchemaNode(String(), type='str')
        bar = SchemaNode(String(), type='str', location="body")
        baz = SchemaNode(String(), type='str', location="querystring")

    class InheritedSchema(TestingSchema):
        foo = SchemaNode(Int(), missing=1)

    class ToBoundSchema(TestingSchema):
        foo = SchemaNode(Int(), missing=1)
        bazinga = SchemaNode(String(), type='str', location="body",
                             validator=deferred_validator)

    class DropSchema(MappingSchema):
        foo = SchemaNode(String(), type='str', missing=drop)
        bar = SchemaNode(String(), type='str')

    class StrictMappingSchema(MappingSchema):
        @staticmethod
        def schema_type():
            return MappingSchema.schema_type(unknown='raise')

    class StrictSchema(StrictMappingSchema):
        foo = SchemaNode(String(), type='str', location="body", missing=drop)
        bar = SchemaNode(String(), type='str', location="body")

    imperative_schema = SchemaNode(Mapping())
    imperative_schema.add(SchemaNode(String(), name='foo', type='str'))
    imperative_schema.add(SchemaNode(String(), name='bar', type='str',
                          location="body"))
    imperative_schema.add(SchemaNode(String(), name='baz', type='str',
                          location="querystring"))

    class TestingSchemaWithHeader(MappingSchema):
        foo = SchemaNode(String(), type='str')
        bar = SchemaNode(String(), type='str', location="body")
        baz = SchemaNode(String(), type='str', location="querystring")
        qux = SchemaNode(String(), type='str', location="header")

    class MockRequest(object):
        def __init__(self, body):
            self.content_type = 'application/json'
            self.headers = {}
            self.matchdict = {}
            self.body = body
            self.GET = {}
            self.POST = {}
            self.validated = {}
            class MockRegistry(object):
                def __init__(self):
                    self.cornice_deserializers = {
                        'application/json': extract_json_data}
            self.registry = MockRegistry()

    class TestSchemas(TestCase):

        def test_colander_integration(self):
            # not specifying body should act the same way as specifying it
            schema = CorniceSchema.from_colander(TestingSchema)
            body_fields = schema.get_attributes(location="body")
            qs_fields = schema.get_attributes(location="querystring")

            self.assertEqual(len(body_fields), 2)
            self.assertEqual(len(qs_fields), 1)

        def test_colander_integration_with_header(self):
            schema = CorniceSchema.from_colander(TestingSchemaWithHeader)
            all_fields = schema.get_attributes()
            body_fields = schema.get_attributes(location="body")
            qs_fields = schema.get_attributes(location="querystring")
            header_fields = schema.get_attributes(location="header")

            self.assertEqual(len(all_fields), 4)
            self.assertEqual(len(body_fields), 2)
            self.assertEqual(len(qs_fields), 1)
            self.assertEqual(len(header_fields), 1)

        def test_colander_inheritance(self):
            """
            support inheritance of colander.Schema
            introduced in colander 0.9.9

            attributes of base-classes with the same name than
            subclass-attributes get overwritten.
            """
            base_schema = CorniceSchema.from_colander(TestingSchema)
            inherited_schema = CorniceSchema.from_colander(InheritedSchema)

            self.assertEqual(len(base_schema.get_attributes()),
                              len(inherited_schema.get_attributes()))

            foo_filter = lambda x: x.name == "foo"
            base_foo = list(filter(foo_filter,
                                   base_schema.get_attributes()))[0]
            inherited_foo = list(filter(foo_filter,
                                        inherited_schema.get_attributes()))[0]
            self.assertTrue(base_foo.required)
            self.assertFalse(inherited_foo.required)

        def test_colander_bound_schemas(self):
            dummy_request = {'x-foo': 'version_a'}
            a_schema = CorniceSchema.from_colander(ToBoundSchema)
            field = a_schema.get_attributes(request=dummy_request)[3]
            self.assertEqual(field.validator.choices, ['a', 'b'])

            other_dummy_request = {'x-foo': 'bazinga!'}
            b_schema = CorniceSchema.from_colander(ToBoundSchema)
            field = b_schema.get_attributes(request=other_dummy_request)[3]
            self.assertEqual(field.validator.choices, ['c', 'd'])

        def test_colander_bound_schema_rebinds_to_new_request(self):
            dummy_request = {'x-foo': 'version_a'}
            the_schema = CorniceSchema.from_colander(ToBoundSchema)
            field = the_schema.get_attributes(request=dummy_request)[3]
            self.assertEqual(field.validator.choices, ['a', 'b'])

            other_dummy_request = {'x-foo': 'bazinga!'}
            field = the_schema.get_attributes(request=other_dummy_request)[3]
            self.assertEqual(field.validator.choices, ['c', 'd'])

        def test_imperative_colander_schema(self):
            # not specifying body should act the same way as specifying it
            schema = CorniceSchema.from_colander(imperative_schema)
            body_fields = schema.get_attributes(location="body")
            qs_fields = schema.get_attributes(location="querystring")

            self.assertEqual(len(body_fields), 2)
            self.assertEqual(len(qs_fields), 1)

        def test_colander_schema_using_drop(self):
            """
            remove fields from validated data if they deserialize to colander's
            `drop` object.
            """
            schema = CorniceSchema.from_colander(DropSchema)

            dummy_request = MockRequest('{"bar": "required_data"}')
            setattr(dummy_request, 'errors', Errors(dummy_request))
            validate_colander_schema(schema, dummy_request)

            self.assertNotIn('foo', dummy_request.validated)
            self.assertIn('bar', dummy_request.validated)

        def test_colander_strict_schema(self):
            schema = CorniceSchema.from_colander(StrictSchema)

            dummy_request = MockRequest('''{"bar": "required_data",
                                            "foo": "optional_data",
                                            "other": "not_wanted_data"}''')

            setattr(dummy_request, 'errors', Errors(dummy_request))
            validate_colander_schema(schema, dummy_request)

            errors = dummy_request.errors
            self.assertEqual(len(errors), 1)
            self.assertEqual(errors[0], {'description': 'other is not allowed',
                                         'location': 'body',
                                         'name': 'other'})
            self.assertIn('foo', dummy_request.validated)
            self.assertIn('bar', dummy_request.validated)

        def test_colander_schema_using_dotted_names(self):
            """
            Schema could be passed as string in view
            """
            schema = CorniceSchema.from_colander(
                'cornice.tests.schema.AccountSchema')

            dummy_request = MockRequest('{"nickname": "john"}')
            setattr(dummy_request, 'errors', Errors(dummy_request))
            validate_colander_schema(schema, dummy_request)

            self.assertIn('nickname', dummy_request.validated)
            self.assertNotIn('city', dummy_request.validated)
########NEW FILE########
__FILENAME__ = test_service
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
from cornice.service import (Service, get_services, clear_services,
                             decorate_view)
from cornice.tests import validationapp
from cornice.tests.support import TestCase, DummyRequest, DummyContext

_validator = lambda req: True
_validator2 = lambda req: True
_stub = lambda req: None


from cornice.resource import resource


@resource(collection_path='/pets', path='/pets/{id}')
class DummyAPI(object):
    last_request = None
    last_context = None
    def __init__(self, request, context=None):
        DummyAPI.last_request = request
        DummyAPI.last_context = context

    def collection_get(self):
        return ['douggy', 'rusty']


class TestService(TestCase):

    def tearDown(self):
        clear_services()

    def test_service_instanciation(self):
        service = Service("coconuts", "/migrate")
        self.assertEqual(service.name, "coconuts")
        self.assertEqual(service.path, "/migrate")
        self.assertEqual(service.renderer, Service.renderer)

        service = Service("coconuts", "/migrate", renderer="html")
        self.assertEqual(service.renderer, "html")

        # test that lists are also set
        validators = [lambda x: True, ]
        service = Service("coconuts", "/migrate", validators=validators)
        self.assertEqual(service.validators, validators)

    def test_get_arguments(self):
        service = Service("coconuts", "/migrate")
        # not specifying anything, we should get the default values
        args = service.get_arguments({})
        for arg in Service.mandatory_arguments:
            self.assertEqual(args[arg], getattr(Service, arg, None))

        # calling this method on a configured service should use the values
        # passed at instanciation time as default values
        service = Service("coconuts", "/migrate", renderer="html")
        args = service.get_arguments({})
        self.assertEqual(args['renderer'], 'html')

        # if we specify another renderer for this service, despite the fact
        # that one is already set in the instance, this one should be used
        args = service.get_arguments({'renderer': 'foobar'})
        self.assertEqual(args['renderer'], 'foobar')

        # test that list elements are not overwritten
        # define a validator for the needs of the test

        service = Service("vaches", "/fetchez", validators=(_validator,))
        self.assertEqual(len(service.validators), 1)
        args = service.get_arguments({'validators': (_validator2,)})

        # the list of validators didn't changed
        self.assertEqual(len(service.validators), 1)

        # but the one returned contains 2 validators
        self.assertEqual(len(args['validators']), 2)

        # test that exclude effectively removes the items from the list of
        # validators / filters it returns, without removing it from the ones
        # registered for the service.
        service = Service("open bar", "/bar", validators=(_validator,
                                                          _validator2))
        self.assertEqual(service.validators, [_validator, _validator2])

        args = service.get_arguments({"exclude": _validator2})
        self.assertEqual(args['validators'], [_validator])

        # defining some non-mandatory arguments in a service should make
        # them available on further calls to get_arguments.

        service = Service("vaches", "/fetchez", foobar="baz")
        self.assertIn("foobar", service.arguments)
        self.assertIn("foobar", service.get_arguments())

    def test_view_registration(self):
        # registering a new view should make it available in the list.
        # The methods list is populated
        service = Service("color", "/favorite-color")

        def view(request):
            pass
        service.add_view("post", view, validators=(_validator,))
        self.assertEqual(len(service.definitions), 1)
        method, _view, _ = service.definitions[0]

        # the view had been registered. we also test here that the method had
        # been inserted capitalized (POST instead of post)
        self.assertEqual(("POST", view), (method, _view))

    def test_error_handler(self):
        error_handler = object()
        service = Service("color", "/favorite-color",
                          error_handler=error_handler)

        @service.get()
        def get_favorite_color(request):
            return "blue, hmm, red, hmm, aaaaaaaah"

        method, view, args = service.definitions[0]
        self.assertIs(args['error_handler'], error_handler)

    def test_decorators(self):
        service = Service("color", "/favorite-color")

        @service.get()
        def get_favorite_color(request):
            return "blue, hmm, red, hmm, aaaaaaaah"

        self.assertEqual(2, len(service.definitions))
        method, view, _ = service.definitions[0]
        self.assertEqual(("GET", get_favorite_color), (method, view))
        method, view, _ = service.definitions[1]
        self.assertEqual(("HEAD", get_favorite_color), (method, view))

        @service.post(accept='text/plain', renderer='plain')
        @service.post(accept='application/json')
        def post_favorite_color(request):
            pass

        # using multiple decorators on a resource should register them all in
        # as many different definitions in the service
        self.assertEqual(4, len(service.definitions))

        @service.patch()
        def patch_favorite_color(request):
            return ""

        method, view, _ = service.definitions[4]
        self.assertEqual("PATCH", method)

    def test_get_acceptable(self):
        # defining a service with different "accept" headers, we should be able
        # to retrieve this information easily
        service = Service("color", "/favorite-color")
        service.add_view("GET", lambda x: "blue", accept="text/plain")
        self.assertEqual(service.get_acceptable("GET"), ['text/plain'])

        service.add_view("GET", lambda x: "blue", accept="application/json")
        self.assertEqual(service.get_acceptable("GET"),
                          ['text/plain', 'application/json'])

        # adding a view for the POST method should not break everything :-)
        service.add_view("POST", lambda x: "ok", accept=('foo/bar'))
        self.assertEqual(service.get_acceptable("GET"),
                          ['text/plain', 'application/json'])
        # and of course the list of accepted egress content-types should be
        # available for the "POST" as well.
        self.assertEqual(service.get_acceptable("POST"),
                          ['foo/bar'])

        # it is possible to give acceptable egress content-types dynamically at
        # run-time. You don't always want to have the callables when retrieving
        # all the acceptable content-types
        service.add_view("POST", lambda x: "ok", accept=lambda r: "text/json")
        self.assertEqual(len(service.get_acceptable("POST")), 2)
        self.assertEqual(len(service.get_acceptable("POST", True)), 1)

    def test_get_contenttypes(self):
        # defining a service with different "content_type" headers, we should
        # be able to retrieve this information easily
        service = Service("color", "/favorite-color")
        service.add_view("GET", lambda x: "blue", content_type="text/plain")
        self.assertEquals(service.get_contenttypes("GET"), ['text/plain'])

        service.add_view("GET", lambda x: "blue",
                         content_type="application/json")
        self.assertEquals(service.get_contenttypes("GET"),
                          ['text/plain', 'application/json'])

        # adding a view for the POST method should not break everything :-)
        service.add_view("POST", lambda x: "ok", content_type=('foo/bar'))
        self.assertEquals(service.get_contenttypes("GET"),
                          ['text/plain', 'application/json'])
        # and of course the list of supported ingress content-types should be
        # available for the "POST" as well.
        self.assertEquals(service.get_contenttypes("POST"),
                          ['foo/bar'])

        # it is possible to give supported ingress content-types dynamically at
        # run-time. You don't always want to have the callables when retrieving
        # all the supported content-types
        service.add_view("POST", lambda x: "ok",
                         content_type=lambda r: "text/json")
        self.assertEquals(len(service.get_contenttypes("POST")), 2)
        self.assertEquals(len(service.get_contenttypes("POST", True)), 1)

    def test_get_validators(self):
        # defining different validators for the same services, even with
        # different calls to add_view should make them available in the
        # get_validators method

        def validator(request):
            """Super validator"""
            pass

        def validator2(request):
            pass

        service = Service('/color', '/favorite-color')
        service.add_view('GET', lambda x: 'ok',
                         validators=(validator, validator))
        service.add_view('GET', lambda x: 'ok', validators=(validator2))
        self.assertEqual(service.get_validators('GET'),
                          [validator, validator2])

    if validationapp.COLANDER:
        def test_schemas_for(self):
            schema = validationapp.FooBarSchema
            service = Service("color", "/favorite-color")
            service.add_view("GET", lambda x: "red", schema=schema)
            self.assertEqual(len(service.schemas_for("GET")), 1)
            service.add_view("GET", lambda x: "red", validators=_validator,
                             schema=schema)
            self.assertEqual(len(service.schemas_for("GET")), 2)

    def test_class_parameters(self):
        # when passing a "klass" argument, it gets registered. It also tests
        # that the view argument can be a string and not a callable.
        class TemperatureCooler(object):
            def get_fresh_air(self):
                pass
        service = Service("TemperatureCooler", "/freshair",
                          klass=TemperatureCooler)
        service.add_view("get", "get_fresh_air")

        self.assertEqual(len(service.definitions), 2)

        method, view, args = service.definitions[0]
        self.assertEqual(view, "get_fresh_air")
        self.assertEqual(args["klass"], TemperatureCooler)

    def test_get_services(self):
        self.assertEqual([], get_services())
        foobar = Service("Foobar", "/foobar")
        self.assertIn(foobar, get_services())

        barbaz = Service("Barbaz", "/barbaz")
        self.assertIn(barbaz, get_services())

        self.assertEqual([barbaz, ], get_services(exclude=['Foobar', ]))
        self.assertEqual([foobar, ], get_services(names=['Foobar', ]))
        self.assertEqual([foobar, barbaz],
                          get_services(names=['Foobar', 'Barbaz']))

    def test_default_validators(self):

        old_validators = Service.default_validators
        old_filters = Service.default_filters
        try:
            def custom_validator(request):
                pass

            def custom_filter(request):
                pass

            def freshair(request):
                pass

            # the default validators should be used when registering a service
            Service.default_validators = [custom_validator, ]
            Service.default_filters = [custom_filter, ]
            service = Service("TemperatureCooler", "/freshair")
            service.add_view("GET", freshair)
            method, view, args = service.definitions[0]

            self.assertIn(custom_validator, args['validators'])
            self.assertIn(custom_filter, args['filters'])

            # defining a service with additional filters / validators should
            # work as well
            def another_validator(request):
                pass

            def another_filter(request):
                pass

            def groove_em_all(request):
                pass

            service2 = Service('FunkyGroovy', '/funky-groovy',
                               validators=[another_validator],
                               filters=[another_filter])

            service2.add_view("GET", groove_em_all)
            method, view, args = service2.definitions[0]

            self.assertIn(custom_validator, args['validators'])
            self.assertIn(another_validator, args['validators'])
            self.assertIn(custom_filter, args['filters'])
            self.assertIn(another_filter, args['filters'])
        finally:
            Service.default_validators = old_validators
            Service.default_filters = old_filters

    def test_cors_support(self):
        self.assertFalse(
            Service(name='foo', path='/foo').cors_enabled)

        self.assertTrue(
            Service(name='foo', path='/foo', cors_enabled=True)
            .cors_enabled)

        self.assertFalse(
            Service(name='foo', path='/foo', cors_enabled=False)
            .cors_enabled)

        self.assertTrue(
            Service(name='foo', path='/foo', cors_origins=('*',))
            .cors_enabled)

        self.assertFalse(
            Service(name='foo', path='/foo',
                    cors_origins=('*'), cors_enabled=False)
            .cors_enabled)

    def test_cors_headers_for_service_instanciation(self):
        # When definining services, it's possible to add headers. This tests
        # it is possible to list all the headers supported by a service.
        service = Service('coconuts', '/migrate',
                          cors_headers=('X-Header-Coconut'))
        self.assertNotIn('X-Header-Coconut', service.cors_supported_headers)

        service.add_view('POST', _stub)
        self.assertIn('X-Header-Coconut', service.cors_supported_headers)

    def test_cors_headers_for_view_definition(self):
        # defining headers in the view should work.
        service = Service('coconuts', '/migrate')
        service.add_view('POST', _stub, cors_headers=('X-Header-Foobar'))
        self.assertIn('X-Header-Foobar', service.cors_supported_headers)

    def test_cors_headers_extension(self):
        # definining headers in the service and in the view
        service = Service('coconuts', '/migrate',
                          cors_headers=('X-Header-Foobar'))
        service.add_view('POST', _stub, cors_headers=('X-Header-Barbaz'))
        self.assertIn('X-Header-Foobar', service.cors_supported_headers)
        self.assertIn('X-Header-Barbaz', service.cors_supported_headers)

        # check that adding the same header twice doesn't make bad things
        # happen
        service.add_view('POST', _stub, cors_headers=('X-Header-Foobar'),)
        self.assertEqual(len(service.cors_supported_headers), 2)

        # check that adding a header on a cors disabled method doesn't
        # change anything
        service.add_view('put', _stub,
                         cors_headers=('X-Another-Header',),
                         cors_enabled=False)

        self.assertFalse('X-Another-Header' in service.cors_supported_headers)

    def test_cors_supported_methods(self):
        foo = Service(name='foo', path='/foo', cors_enabled=True)
        foo.add_view('GET', _stub)
        self.assertIn('GET', foo.cors_supported_methods)

        foo.add_view('POST', _stub)
        self.assertIn('POST', foo.cors_supported_methods)

    def test_disabling_cors_for_one_method(self):
        foo = Service(name='foo', path='/foo', cors_enabled=True)
        foo.add_view('GET', _stub)
        self.assertIn('GET', foo.cors_supported_methods)

        foo.add_view('POST', _stub, cors_enabled=False)
        self.assertIn('GET', foo.cors_supported_methods)
        self.assertFalse('POST' in foo.cors_supported_methods)

    def test_cors_supported_origins(self):
        foo = Service(
            name='foo', path='/foo', cors_origins=('mozilla.org',))

        foo.add_view('GET', _stub,
                     cors_origins=('notmyidea.org', 'lolnet.org'))

        self.assertIn('mozilla.org', foo.cors_supported_origins)
        self.assertIn('notmyidea.org', foo.cors_supported_origins)
        self.assertIn('lolnet.org', foo.cors_supported_origins)

    def test_per_method_supported_origins(self):
        foo = Service(
            name='foo', path='/foo', cors_origins=('mozilla.org',))
        foo.add_view('GET', _stub, cors_origins=('lolnet.org',))

        self.assertTrue('mozilla.org' in foo.cors_origins_for('GET'))
        self.assertTrue('lolnet.org' in foo.cors_origins_for('GET'))

        foo.add_view('POST', _stub)
        self.assertFalse('lolnet.org' in foo.cors_origins_for('POST'))

    def test_credential_support_can_be_enabled(self):
        foo = Service(name='foo', path='/foo', cors_credentials=True)
        self.assertTrue(foo.cors_support_credentials())

    def test_credential_support_is_disabled_by_default(self):
        foo = Service(name='foo', path='/foo')
        self.assertFalse(foo.cors_support_credentials())

    def test_per_method_credential_support(self):
        foo = Service(name='foo', path='/foo')
        foo.add_view('GET', _stub, cors_credentials=True)
        foo.add_view('POST', _stub)
        self.assertTrue(foo.cors_support_credentials('GET'))
        self.assertFalse(foo.cors_support_credentials('POST'))

    def test_method_takes_precendence_for_credential_support(self):
        foo = Service(name='foo', path='/foo', cors_credentials=True)
        foo.add_view('GET', _stub, cors_credentials=False)
        self.assertFalse(foo.cors_support_credentials('GET'))

    def test_max_age_can_be_defined(self):
        foo = Service(name='foo', path='/foo', cors_max_age=42)
        self.assertEqual(foo.cors_max_age_for(), 42)

    def test_max_age_can_be_different_dependeing_methods(self):
        foo = Service(name='foo', path='/foo', cors_max_age=42)
        foo.add_view('GET', _stub)
        foo.add_view('POST', _stub, cors_max_age=32)
        foo.add_view('PUT', _stub, cors_max_age=7)

        self.assertEqual(foo.cors_max_age_for('GET'), 42)
        self.assertEqual(foo.cors_max_age_for('POST'), 32)
        self.assertEqual(foo.cors_max_age_for('PUT'), 7)

    def test_cors_policy(self):
        policy = {'origins': ('foo', 'bar', 'baz')}
        foo = Service(name='foo', path='/foo', cors_policy=policy)
        self.assertTrue('foo' in foo.cors_supported_origins)
        self.assertTrue('bar' in foo.cors_supported_origins)
        self.assertTrue('baz' in foo.cors_supported_origins)

    def test_cors_policy_can_be_overwritten(self):
        policy = {'origins': ('foo', 'bar', 'baz')}
        foo = Service(name='foo', path='/foo', cors_origins=(),
                      cors_policy=policy)
        self.assertEqual(len(foo.cors_supported_origins), 0)

    def test_can_specify_a_view_decorator(self):
        def dummy_decorator(view):
            return view
        service = Service("coconuts", "/migrate", decorator=dummy_decorator)
        args = service.get_arguments({})
        self.assertEqual(args['decorator'], dummy_decorator)

        # make sure Service.decorator() still works
        @service.decorator('put')
        def dummy_view(request):
            return "data"
        self.assertTrue(any(view is dummy_view
                            for method, view, args in service.definitions))

    def test_decorate_view_factory(self):

        args = {'factory': u'TheFactoryMethodCalledByPyramid',
                'klass': DummyAPI}

        decorated_view = decorate_view('collection_get', args, 'GET')
        dummy_request = DummyRequest()
        ret = decorated_view(dummy_request)
        self.assertEqual(ret, ['douggy', 'rusty'])
        self.assertEqual(dummy_request, DummyAPI.last_request)
        self.assertEqual(dummy_request.context, DummyAPI.last_context)

    def test_decorate_view_acl(self):

        args = {'acl': 'dummy_permission',
                'klass': DummyAPI}

        decorated_view = decorate_view('collection_get', args, 'GET')
        dummy_request = DummyRequest()
        ret = decorated_view(dummy_request)
        self.assertEqual(ret, ['douggy', 'rusty'])
        self.assertEqual(dummy_request, DummyAPI.last_request)
        self.assertIsNone(DummyAPI.last_context)

########NEW FILE########
__FILENAME__ = test_service_definition
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

from pyramid import testing
from webtest import TestApp

from cornice import Service
from cornice.tests.support import TestCase, CatchErrors


service1 = Service(name="service1", path="/service1")
service2 = Service(name="service2", path="/service2")


@service1.get()
def get1(request):
    return {"test": "succeeded"}


@service1.post()
def post1(request):
    return {"body": request.body}


@service2.get(accept="text/html")
@service2.post(accept="audio/ogg")
def get2_or_post2(request):
    return {"test": "succeeded"}


class TestServiceDefinition(TestCase):

    def setUp(self):
        self.config = testing.setUp()
        self.config.include("cornice")
        self.config.scan("cornice.tests.test_service_definition")
        self.app = TestApp(CatchErrors(self.config.make_wsgi_app()))

    def tearDown(self):
        testing.tearDown()

    def test_basic_service_operation(self):

        self.app.get("/unknown", status=404)
        self.assertEqual(
            self.app.get("/service1").json,
            {'test': "succeeded"})

        self.assertEqual(
            self.app.post("/service1", params="BODY").json,
            {'body': 'BODY'})

    def test_loading_into_multiple_configurators(self):
        # When initializing a second configurator, it shouldn't interfere
        # with the one already in place.
        config2 = testing.setUp()
        config2.include("cornice")
        config2.scan("cornice.tests.test_service_definition")

        # Calling the new configurator works as expected.
        app = TestApp(CatchErrors(config2.make_wsgi_app()))
        self.assertEqual(
            app.get("/service1").json,
            {'test': 'succeeded'})

        # Calling the old configurator works as expected.
        self.assertEqual(
            self.app.get("/service1").json,
            {'test': 'succeeded'})

    def test_stacking_api_decorators(self):
        # Stacking multiple @api calls on a single function should
        # register it multiple times, just like @view_config does.
        resp = self.app.get("/service2", headers={'Accept': 'text/html'})
        self.assertEqual(resp.json, {'test': 'succeeded'})

        resp = self.app.post("/service2", headers={'Accept': 'audio/ogg'})
        self.assertEqual(resp.json, {'test': 'succeeded'})

########NEW FILE########
__FILENAME__ = test_service_description
# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
import warnings

from pyramid import testing
from webtest import TestApp

from cornice.schemas import CorniceSchema
from cornice.tests.validationapp import COLANDER
from cornice.tests.support import TestCase, CatchErrors
from cornice.service import Service

if COLANDER:
    from cornice.tests.validationapp import FooBarSchema
    from colander import (MappingSchema, SchemaNode, String, SequenceSchema,
                          Length)

    class SchemaFromQuerystring(MappingSchema):
        yeah = SchemaNode(String(), location="querystring", type='str')

    class SchemaFromHeader(MappingSchema):
        x_qux = SchemaNode(String(), location="header", type='str',
                           name="X-Qux")

    class ModelField(MappingSchema):
        name = SchemaNode(String())
        description = SchemaNode(String())

    class ModelFields(SequenceSchema):
        field = ModelField()

    class ModelDefinition(MappingSchema):
        title = SchemaNode(String(), location="body")
        fields = ModelFields(validator=Length(min=1), location="body")

    nested_service = Service(name='nested', path='/nested')

    @nested_service.post(schema=ModelDefinition)
    def get_nested(request):
        return "yay"

    foobar = Service(name="foobar", path="/foobar")

    @foobar.post(schema=FooBarSchema)
    def foobar_post(request):
        return {"test": "succeeded", 'baz': request.validated['baz']}

    @foobar.get(schema=SchemaFromQuerystring)
    def foobar_get(request):
        return {"test": "succeeded"}

    @foobar.delete(schema=SchemaFromHeader)
    def foobar_delete(request):
        return {"test": "succeeded"}

    class TestServiceDescription(TestCase):

        def setUp(self):
            self.config = testing.setUp()
            self.config.include("cornice")
            self.config.scan("cornice.tests.test_service_description")
            self.app = TestApp(CatchErrors(self.config.make_wsgi_app()))

        def tearDown(self):
            testing.tearDown()

        def test_get_from_colander(self):
            schema = CorniceSchema.from_colander(FooBarSchema)
            attrs = schema.as_dict()
            self.assertEqual(len(attrs), 6)

        def test_description_attached(self):
            # foobar should contain a schema argument containing the cornice
            # schema object, so it can be introspected if needed
            # accessing Service.schemas emits a warning
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                self.assertTrue('POST' in foobar.schemas)
                self.assertEqual(len(w), 1)

        def test_schema_validation(self):
            # using a colander schema for the service should automatically
            # validate the request calls. Let's make some of them here.
            resp = self.app.post('/foobar', status=400)
            self.assertEqual(resp.json['status'], 'error')

            errors = resp.json['errors']
            # we should at have 1 missing value in the QS...
            self.assertEqual(1, len([e for e in errors
                                    if e['location'] == "querystring"]))

            # ... and 2 in the body (a json error as well)
            self.assertEqual(2, len([e for e in errors
                                    if e['location'] == "body"]))

            # let's do the same request, but with information in the
            # querystring
            resp = self.app.post('/foobar?yeah=test', status=400)

            # we should have no missing value in the QS
            self.assertEqual(0, len([e for e in resp.json['errors']
                                    if e['location'] == "querystring"]))

            # and if we add the required values in the body of the post,
            # then we should be good
            data = {'foo': 'yeah', 'bar': 'open'}
            resp = self.app.post_json('/foobar?yeah=test',
                                      params=data, status=200)

            self.assertEqual(resp.json, {u'baz': None, "test": "succeeded"})

        def test_schema_validation2(self):
            resp = self.app.get('/foobar?yeah=test', status=200)
            self.assertEqual(resp.json, {"test": "succeeded"})

        def test_bar_validator(self):
            # test validator on bar attribute
            data = {'foo': 'yeah', 'bar': 'closed'}
            resp = self.app.post_json('/foobar?yeah=test', params=data,
                                      status=400)

            self.assertEqual(resp.json, {
                u'errors': [{u'description': u'The bar is not open.',
                             u'location': u'body',
                             u'name': u'bar'}],
                u'status': u'error'})

        def test_foo_required(self):
            # test required attribute
            data = {'bar': 'open'}
            resp = self.app.post_json('/foobar?yeah=test', params=data,
                                      status=400)

            self.assertEqual(resp.json, {
                u'errors': [{u'description': u'foo is missing',
                             u'location': u'body',
                             u'name': u'foo'}],
                u'status': u'error'})

        def test_default_baz_value(self):
            # test required attribute
            data = {'foo': 'yeah', 'bar': 'open'}
            resp = self.app.post_json('/foobar?yeah=test', params=data,
                                      status=200)

            self.assertEqual(resp.json, {u'baz': None, "test": "succeeded"})

        def test_ipsum_error_message(self):
            # test required attribute
            data = {'foo': 'yeah', 'bar': 'open', 'ipsum': 5}
            resp = self.app.post_json('/foobar?yeah=test',
                                      params=data,
                                      status=400)

            self.assertEqual(resp.json, {
                u'errors': [
                    {u'description': u'5 is greater than maximum value 3',
                     u'location': u'body',
                     u'name': u'ipsum'}],
                u'status': u'error'})

        def test_integers_fail(self):
            # test required attribute
            data = {'foo': 'yeah', 'bar': 'open', 'ipsum': 2,
                    'integers': ('a', '2')}
            resp = self.app.post_json('/foobar?yeah=test', data,
                                      status=400)

            self.assertEqual(resp.json, {
                u'errors': [
                    {u'description': u'"a" is not a number',
                     u'location': u'body',
                     u'name': u'integers.0'}],
                u'status': u'error'})

        def test_integers_ok(self):
            # test required attribute
            data = {'foo': 'yeah', 'bar': 'open', 'ipsum': 2,
                    'integers': ('1', '2')}
            self.app.post_json('/foobar?yeah=test', params=data,
                               status=200)

        def test_nested_schemas(self):

            data = {"title": "Mushroom",
                    "fields": [{"name": "genre", "description": "Genre"}]}

            nested_data = {"title": "Mushroom",
                           "fields": [{"schmil": "Blick"}]}

            self.app.post_json('/nested', params=data, status=200)
            self.app.post_json('/nested', params=nested_data,
                               status=400)

        def test_nested_schemas_with_flattened_values(self):

            data = {"title": "Mushroom",
                    "fields.0.name": "genre",
                    "fields.0.description": "Genre"}

            resp = self.app.post('/nested', params=data, status=200)

        def test_qux_header(self):
            resp = self.app.delete('/foobar', status=400)
            self.assertEqual(resp.json, {
                u'errors': [
                    {u'description': u'X-Qux is missing',
                     u'location': u'header',
                     u'name': u'X-Qux'}],
                u'status': u'error'})

            self.app.delete('/foobar', headers={'X-Qux': 'Hotzenplotz'},
                            status=200)

########NEW FILE########
__FILENAME__ = test_validation
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
from pyramid.config import Configurator
import simplejson as json

from webtest import TestApp
from pyramid.response import Response

from cornice.errors import Errors
from cornice.tests.validationapp import main, includeme, dummy_deserializer
from cornice.tests.support import LoggingCatcher, TestCase, CatchErrors
from cornice.validators import filter_json_xsrf


class TestServiceDefinition(LoggingCatcher, TestCase):

    def test_validation(self):
        app = TestApp(main({}))
        app.get('/service', status=400)

        response = app.post('/service', params='buh', status=400)
        self.assertTrue(b'Not a json body' in response.body)

        response = app.post('/service', params=json.dumps('buh'))

        expected = json.dumps({'body': '"buh"'}).encode('ascii')
        self.assertEqual(response.body, expected)

        app.get('/service?paid=yup')

        # valid = foo is one
        response = app.get('/service?foo=1&paid=yup')
        self.assertEqual(response.json['foo'], 1)

        # invalid value for foo
        response = app.get('/service?foo=buh&paid=yup', status=400)

        # check that json is returned
        errors = Errors.from_json(response.body)
        self.assertEqual(len(errors), 1)

    def test_validation_hooked_error_response(self):
        app = TestApp(main({}))

        response = app.post('/service4', status=400)
        self.assertTrue(b'<errors>' in response.body)

    def test_accept(self):
        # tests that the accept headers are handled the proper way
        app = TestApp(main({}))

        # requesting the wrong accept header should return a 406 ...
        response = app.get('/service2', headers={'Accept': 'audio/*'},
                           status=406)

        # ... with the list of accepted content-types
        error_location = response.json['errors'][0]['location']
        error_name = response.json['errors'][0]['name']
        error_description = response.json['errors'][0]['description']
        self.assertEquals('header', error_location)
        self.assertEquals('Accept', error_name)
        self.assertTrue('application/json' in error_description)
        self.assertTrue('text/json' in error_description)
        self.assertTrue('text/plain' in error_description)

        # requesting a supported type should give an appropriate response type
        response = app.get('/service2', headers={'Accept': 'application/*'})
        self.assertEqual(response.content_type, "application/json")

        response = app.get('/service2', headers={'Accept': 'text/plain'})
        self.assertEqual(response.content_type, "text/plain")

        # it should also work with multiple Accept headers
        response = app.get('/service2', headers={
            'Accept': 'audio/*, application/*'
        })
        self.assertEqual(response.content_type, "application/json")

        # and requested preference order should be respected
        headers = {'Accept': 'application/json; q=1.0, text/plain; q=0.9'}
        response = app.get('/service2', headers=headers)
        self.assertEqual(response.content_type, "application/json")

        headers = {'Accept': 'application/json; q=0.9, text/plain; q=1.0'}
        response = app.get('/service2', headers=headers)
        self.assertEqual(response.content_type, "text/plain")

        # test that using a callable to define what's accepted works as well
        response = app.get('/service3', headers={'Accept': 'audio/*'},
                           status=406)
        error_description = response.json['errors'][0]['description']
        self.assertTrue('text/json' in error_description)

        response = app.get('/service3', headers={'Accept': 'text/*'})
        self.assertEqual(response.content_type, "text/json")

        # if we are not asking for a particular content-type,
        # we should get one of the two types that the service supports.
        response = app.get('/service2')
        self.assertTrue(response.content_type
                        in ("application/json", "text/plain"))

    def test_accept_issue_113_text_star(self):
        app = TestApp(main({}))

        response = app.get('/service3', headers={'Accept': 'text/*'})
        self.assertEqual(response.content_type, "text/json")

    def test_accept_issue_113_text_application_star(self):
        app = TestApp(main({}))

        response = app.get('/service3', headers={'Accept': 'application/*'})
        self.assertEqual(response.content_type, "application/json")

    def test_accept_issue_113_text_application_json(self):
        app = TestApp(main({}))

        response = app.get('/service3', headers={'Accept': 'application/json'})
        self.assertEqual(response.content_type, "application/json")

    def test_accept_issue_113_text_html_not_acceptable(self):
        app = TestApp(main({}))

        # requesting an unsupported content type should return a HTTP 406 (Not
        # Acceptable)
        app.get('/service3', headers={'Accept': 'text/html'}, status=406)

    def test_accept_issue_113_audio_or_text(self):
        app = TestApp(main({}))

        response = app.get('/service2', headers={
            'Accept': 'audio/mp4; q=0.9, text/plain; q=0.5'
        })
        self.assertEqual(response.content_type, "text/plain")

        # if we are not asking for a particular content-type,
        # we should get one of the two types that the service supports.
        response = app.get('/service2')
        self.assertTrue(response.content_type
                        in ("application/json", "text/plain"))

    def test_filters(self):
        app = TestApp(main({}))

        # filters can be applied to all the methods of a service
        self.assertTrue(b"filtered response" in app.get('/filtered').body)
        self.assertTrue(b"unfiltered" in app.post('/filtered').body)

    def test_json_xsrf_vulnerable_values_warning(self):
        vulnerable_values = [
            '["value1", "value2"]',  # json array
            '  \n ["value1", "value2"] ',  # may include whitespace
            '"value"',  # strings may contain nasty characters in UTF-7
        ]
        # a view returning a vulnerable json response should issue a warning
        for value in vulnerable_values:
            response = Response(value)
            response.status = 200
            response.content_type = 'application/json'
            filter_json_xsrf(response)
            assert len(self.get_logs()) == 1, "Expected warning: %s" % value

    def test_json_xsrf_safe_values_no_warning(self):
        safe_values = [
            '{"value1": "value2"}',  # json object
            '  \n {"value1": "value2"} ',  # may include whitespace
            'true', 'false', 'null',  # primitives
            '123', '-123', '0.123',  # numbers
        ]
        # a view returning safe json response should not issue a warning
        for value in safe_values:
            response = Response(value)
            response.status = 200
            response.content_type = 'application/json'
            filter_json_xsrf(response)
            assert len(self.get_logs()) == 0, "Unexpected warning: %s" % value

    def test_multiple_querystrings(self):
        app = TestApp(main({}))

        # it is possible to have more than one value with the same name in the
        # querystring
        self.assertEquals(b'{"field": ["5"]}', app.get('/foobaz?field=5').body)
        self.assertEquals(b'{"field": ["5", "2"]}',
                          app.get('/foobaz?field=5&field=2').body)

    def test_email_field(self):
        app = TestApp(main({}))
        content = {'email': 'alexis@notmyidea.org'}
        app.post_json('/newsletter', params=content)

    def test_content_type_missing(self):
        # test that a Content-Type request headers is present
        app = TestApp(main({}))

        # requesting without a Content-Type header should return a 415 ...
        request = app.RequestClass.blank('/service5', method='POST')
        response = app.do_request(request, 415, True)

        # ... with an appropriate json error structure
        error_location = response.json['errors'][0]['location']
        error_name = response.json['errors'][0]['name']
        error_description = response.json['errors'][0]['description']
        self.assertEqual('header', error_location)
        self.assertEqual('Content-Type', error_name)
        self.assertTrue('application/json' in error_description)

    def test_content_type_wrong_single(self):
        # tests that the Content-Type request header satisfies the requirement
        app = TestApp(main({}))

        # requesting the wrong Content-Type header should return a 415 ...
        response = app.post('/service5',
                            headers={'Content-Type': 'text/plain'},
                            status=415)

        # ... with an appropriate json error structure
        error_description = response.json['errors'][0]['description']
        self.assertTrue('application/json' in error_description)

    def test_content_type_wrong_multiple(self):
        # tests that the Content-Type request header satisfies the requirement
        app = TestApp(main({}))

        # requesting the wrong Content-Type header should return a 415 ...
        response = app.put('/service5',
                           headers={'Content-Type': 'text/xml'},
                           status=415)

        # ... with an appropriate json error structure
        error_description = response.json['errors'][0]['description']
        self.assertTrue('text/plain' in error_description)
        self.assertTrue('application/json' in error_description)

    def test_content_type_correct(self):
        # tests that the Content-Type request header satisfies the requirement
        app = TestApp(main({}))

        # requesting with one of the allowed Content-Type headers should work,
        # even when having a charset parameter as suffix
        response = app.put('/service5', headers={
            'Content-Type': 'text/plain; charset=utf-8'
        })
        self.assertEqual(response.json, "some response")

    def test_content_type_on_get(self):
        # test that a Content-Type request header is not
        # checked on GET requests, they don't usually have a body
        app = TestApp(main({}))
        response = app.get('/service5')
        self.assertEqual(response.json, "some response")

    def test_content_type_with_callable(self):
        # test that using a callable for content_type works as well
        app = TestApp(main({}))
        response = app.post('/service6', headers={'Content-Type': 'audio/*'},
                            status=415)
        error_description = response.json['errors'][0]['description']
        self.assertTrue('text/xml' in error_description)
        self.assertTrue('application/json' in error_description)

        app.post('/service6', headers={'Content-Type': 'text/xml'})

    def test_accept_and_content_type(self):
        # tests that giving both Accept and Content-Type
        # request headers satisfy the requirement
        app = TestApp(main({}))

        # POST endpoint just has one accept and content_type definition
        response = app.post('/service7', headers={
            'Accept': 'text/xml, application/json',
            'Content-Type': 'application/json; charset=utf-8'
        })
        self.assertEqual(response.json, "some response")

        response = app.post(
            '/service7',
            headers={
                'Accept': 'text/plain, application/json',
                'Content-Type': 'application/json; charset=utf-8'
            },
            status=406)

        response = app.post(
            '/service7',
            headers={
                'Accept': 'text/xml, application/json',
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            status=415)

        # PUT endpoint has a list of accept and content_type definitions
        response = app.put('/service7', headers={
            'Accept': 'text/xml, application/json',
            'Content-Type': 'application/json; charset=utf-8'
        })
        self.assertEqual(response.json, "some response")

        response = app.put(
            '/service7',
            headers={
                'Accept': 'audio/*',
                'Content-Type': 'application/json; charset=utf-8'
            },
            status=406)

        response = app.put(
            '/service7',
            headers={
                'Accept': 'text/xml, application/json',
                'Content-Type': 'application/x-www-form-urlencoded'
            }, status=415)


class TestRequestDataExtractors(LoggingCatcher, TestCase):

    def make_ordinary_app(self):
        return TestApp(main({}))

    def make_app_with_deserializer(self, deserializer):
        config = Configurator(settings={})
        config.include(includeme)
        config.add_cornice_deserializer('text/dummy', deserializer)
        return TestApp(CatchErrors(config.make_wsgi_app()))

    def test_valid_json(self):
        app = self.make_ordinary_app()
        response = app.post_json('/foobar?yeah=test', {
            'foo': 'hello',
            'bar': 'open',
            'yeah': 'man',
        })
        self.assertEqual(response.json['test'], 'succeeded')

    def test_invalid_json(self):
        app = self.make_ordinary_app()
        response = app.post('/foobar?yeah=test',
                            "invalid json input",
                            headers={'content-type': 'application/json'},
                            status=400)
        self.assertEqual(response.json['status'], 'error')
        error_description = response.json['errors'][0]['description']
        self.assertIn('Invalid JSON', error_description)


    def test_www_form_urlencoded(self):
        app = self.make_ordinary_app()
        response = app.post('/foobar?yeah=test', {
            'foo': 'hello',
            'bar': 'open',
            'yeah': 'man',
        })
        self.assertEqual(response.json['test'], 'succeeded')

    def test_deserializer_from_global_config(self):
        app = self.make_app_with_deserializer(dummy_deserializer)
        response = app.post('/foobar?yeah=test', "hello,open,yeah",
                            headers={'content-type': 'text/dummy'})
        self.assertEqual(response.json['test'], 'succeeded')

    def test_deserializer_from_view_config(self):
        app = self.make_ordinary_app()
        response = app.post('/custom_deserializer?yeah=test',
                            "hello,open,yeah",
                            headers={'content-type': 'text/dummy'})
        self.assertEqual(response.json['test'], 'succeeded')

    def test_view_config_has_priority_over_global_config(self):
        low_priority_deserializer = lambda request: "we don't want this"
        app = self.make_app_with_deserializer(low_priority_deserializer)
        response = app.post('/custom_deserializer?yeah=test',
                            "hello,open,yeah",
                            headers={'content-type': 'text/dummy'})
        self.assertEqual(response.json['test'], 'succeeded')

########NEW FILE########
__FILENAME__ = validationapp
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
from pyramid.config import Configurator
from pyramid.httpexceptions import HTTPBadRequest

from cornice import Service
from cornice.tests.support import CatchErrors
import json


service = Service(name="service", path="/service")


def has_payed(request):
    if not 'paid' in request.GET:
        request.errors.add('body', 'paid', 'You must pay!')


def foo_int(request):
    if 'foo' not in request.GET:
        return
    try:
        request.validated['foo'] = int(request.GET['foo'])
    except ValueError:
        request.errors.add('url', 'foo', 'Not an int')


@service.get(validators=(has_payed, foo_int))
def get1(request):
    res = {"test": "succeeded"}
    try:
        res['foo'] = request.validated['foo']
    except KeyError:
        pass

    return res


def _json(request):
    """The request body should be a JSON object."""
    try:
        request.validated['json'] = json.loads(request.body.decode('utf-8'))
    except ValueError:
        request.errors.add('body', 'json', 'Not a json body')


@service.post(validators=_json)
def post1(request):
    return {"body": request.body}


service2 = Service(name="service2", path="/service2")


@service2.get(accept=("application/json", "text/json"))
@service2.get(accept=("text/plain"), renderer="string")
def get2(request):
    return {"body": "yay!"}


service3 = Service(name="service3", path="/service3")


def _accept(request):
    return ('application/json', 'text/json')


@service3.get(accept=_accept)
def get3(request):
    return {"body": "yay!"}


def _filter(response):
    response.body = b"filtered response"
    return response

service4 = Service(name="service4", path="/service4")


def fail(request):
    request.errors.add('body', 'xml', 'Not XML')


def xml_error(errors):
    lines = ['<errors>']
    for error in errors:
        lines.append('<error>'
                     '<location>%(location)s</location>'
                     '<type>%(name)s</type>'
                     '<message>%(description)s</message>'
                     '</error>' % error)
    lines.append('</errors>')
    return HTTPBadRequest(body=''.join(lines))


@service4.post(validators=fail, error_handler=xml_error)
def post4(request):
    raise ValueError("Shouldn't get here")

# test filtered services
filtered_service = Service(name="filtered", path="/filtered", filters=_filter)


@filtered_service.get()
@filtered_service.post(exclude=_filter)
def get4(request):
    return "unfiltered"  # should be overwritten on GET

# test the "content_type" parameter (scalar)
service5 = Service(name="service5", path="/service5")


@service5.get()
@service5.post(content_type='application/json')
@service5.put(content_type=('text/plain', 'application/json'))
def post5(request):
    return "some response"

# test the "content_type" parameter (callable)
service6 = Service(name="service6", path="/service6")


def _content_type(request):
    return ('text/xml', 'application/json')


@service6.post(content_type=_content_type)
def post6(request):
    return {"body": "yay!"}

# test a mix of "accept" and "content_type" parameters
service7 = Service(name="service7", path="/service7")


@service7.post(accept='text/xml', content_type='application/json')
@service7.put(accept=('text/xml', 'text/plain'),
              content_type=('application/json', 'text/xml'))
def post7(request):
    return "some response"


try:
    from colander import (
        Invalid,
        MappingSchema,
        SequenceSchema,
        SchemaNode,
        String,
        Integer,
        Range,
        Email
    )
    COLANDER = True
except ImportError:
    COLANDER = False

if COLANDER:
    def validate_bar(node, value):
        if value != 'open':
            raise Invalid(node, "The bar is not open.")

    class Integers(SequenceSchema):
        integer = SchemaNode(Integer(), type='int')

    class FooBarSchema(MappingSchema):
        # foo and bar are required, baz is optional
        foo = SchemaNode(String(), type='str')
        bar = SchemaNode(String(), type='str', validator=validate_bar)
        baz = SchemaNode(String(), type='str', missing=None)
        yeah = SchemaNode(String(), location="querystring", type='str')
        ipsum = SchemaNode(Integer(), type='int', missing=1,
                           validator=Range(0, 3))
        integers = Integers(location="body", type='list', missing=())

    foobar = Service(name="foobar", path="/foobar")
    foobaz = Service(name="foobaz", path="/foobaz")

    @foobar.post(schema=FooBarSchema)
    def foobar_post(request):
        return {"test": "succeeded"}

    custom_deserializer_service = Service(name="custom_deserializer_service",
                                          path="/custom_deserializer")

    def dummy_deserializer(request):
        values = request.body.decode().split(',')
        return dict(zip(['foo', 'bar', 'yeah'], values))

    @custom_deserializer_service.post(schema=FooBarSchema,
                                      deserializer=dummy_deserializer)
    def custom_deserializer_service_post(request):
        return {"test": "succeeded"}

    class StringSequence(SequenceSchema):
        _ = SchemaNode(String())

    class ListQuerystringSequence(MappingSchema):
        field = StringSequence(location="querystring")

    @foobaz.get(schema=ListQuerystringSequence)
    def foobaz_get(request):
        return {"field": request.validated['field']}

    class NewsletterSchema(MappingSchema):
        email = SchemaNode(String(), validator=Email())

    email_service = Service(name='newsletter', path='/newsletter')

    @email_service.post(schema=NewsletterSchema)
    def newsletter(request):
        return "ohyeah"


def includeme(config):
    config.include("cornice")
    config.scan("cornice.tests.validationapp")


def main(global_config, **settings):
    config = Configurator(settings={})
    config.include(includeme)
    return CatchErrors(config.make_wsgi_app())

########NEW FILE########
__FILENAME__ = util
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
import sys

import simplejson as json

from pyramid import httpexceptions as exc
from pyramid.response import Response


__all__ = ['json_renderer', 'to_list', 'json_error', 'match_accept_header',
           'extract_request_data']


PY3 = sys.version_info[0] == 3

if PY3:
    string_types = str,
else:
    string_types = basestring,


def is_string(s):
    return isinstance(s, string_types)


def json_renderer(helper):
    return _JsonRenderer()


class _JsonRenderer(object):
    def __call__(self, data, context):
        acceptable = ('application/json', 'text/json', 'text/plain')
        response = context['request'].response
        content_type = (context['request'].accept.best_match(acceptable)
                        or acceptable[0])
        response.content_type = content_type
        return json.dumps(data, use_decimal=True)


def to_list(obj):
    """Convert an object to a list if it is not already one"""
    if not isinstance(obj, (list, tuple)):
        obj = [obj, ]
    return obj


class _JSONError(exc.HTTPError):
    def __init__(self, errors, status=400):
        body = {'status': 'error', 'errors': errors}
        Response.__init__(self, json.dumps(body, use_decimal=True))
        self.status = status
        self.content_type = 'application/json'


def json_error(errors):
    """Returns an HTTPError with the given status and message.

    The HTTP error content type is "application/json"
    """
    return _JSONError(errors, errors.status)


def match_accept_header(func, context, request):
    """
    Return True if the request matches the values returned by the given :param:
    func callable.

    :param func:
        The callable returning the list of acceptable content-types,
        given a request. It should accept a "request" argument.
    """
    acceptable = func(request)
    # attach the accepted egress content types to the request
    request.info['acceptable'] = acceptable
    return request.accept.best_match(acceptable) is not None


def match_content_type_header(func, context, request):
    supported_contenttypes = func(request)
    # attach the accepted ingress content types to the request
    request.info['supported_contenttypes'] = supported_contenttypes
    return content_type_matches(request, supported_contenttypes)


def extract_json_data(request):
    if request.body:
        try:
            body = json.loads(request.body)
            return body
        except ValueError as e:
            request.errors.add(
                'body', None,
                "Invalid JSON request body: %s" % e)
            return {}
    else:
        return {}


def extract_form_urlencoded_data(request):
    return request.POST


def extract_request_data(request):
    """extract the different parts of the data from the request, and return
    them as a tuple of (querystring, headers, body, path)
    """
    body = {}
    content_type = getattr(request, 'content_type', None)
    registry = request.registry
    if hasattr(request, 'deserializer'):
        body = request.deserializer(request)
    elif (hasattr(registry, 'cornice_deserializers')
          and content_type in registry.cornice_deserializers):
        deserializer = registry.cornice_deserializers[content_type]
        body = deserializer(request)
    # otherwise, don't block but it will be an empty body, decode
    # on your own

    return request.GET, request.headers, body, request.matchdict


def content_type_matches(request, content_types):
    """
    Check whether ``request.content_type``
    matches given list of content types.
    """
    return request.content_type in content_types


class ContentTypePredicate(object):
    """
    Pyramid predicate for matching against ``Content-Type`` request header.
    Should live in ``pyramid.config.predicates``.

    .. seealso::

        http://docs.pylonsproject.org/projects/pyramid/en/latest/narr/hooks.html#view-and-route-predicates
    """
    def __init__(self, val, config):
        self.val = val

    def text(self):
        return 'content_type = %s' % (self.val,)

    phash = text

    def __call__(self, context, request):
        return request.content_type == self.val

########NEW FILE########
__FILENAME__ = validators
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
import re

# Strings and arrays are potentially exploitable
safe_json_re = re.compile(r'\s*[\{tfn\-0-9]'.encode('ascii'), re.MULTILINE)


def filter_json_xsrf(response):
    """drops a warning if a service returns potentially exploitable json
    """
    if hasattr(response, 'content_type') and response.content_type in ('application/json', 'text/json'):
        if safe_json_re.match(response.body) is None:
            from cornice import logger
            logger.warn("returning a json string or array is a potential "
                "security hole, please ensure you really want to do this.")
    return response


DEFAULT_VALIDATORS = []
DEFAULT_FILTERS = [filter_json_xsrf, ]

########NEW FILE########
__FILENAME__ = conf
# flake8: noqa
# -*- coding: utf-8 -*-
import sys, os
try:
    import mozilla_sphinx_theme
except ImportError:
    print("please install the 'mozilla-sphinx-theme' distribution")

sys.path.insert(0, os.path.abspath("../.."))  # include cornice from the source
extensions = ['cornice.ext.sphinxext', 'sphinx.ext.autodoc']

templates_path = ['_templates']
source_suffix = '.rst'
master_doc = 'index'
project = u'Cornice'
copyright = u'2011, Mozilla Services'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.17'
# The full version, including alpha/beta/rc tags.
release = '0.17'

exclude_patterns = []

html_theme_path = [os.path.dirname(mozilla_sphinx_theme.__file__)]

html_theme = 'mozilla'
html_static_path = ['_static']
htmlhelp_basename = 'Cornicedoc'

latex_documents = [
  ('index', 'Cornice.tex', u'Cornice Documentation',
   u'Mozilla Services', 'manual'),
]

man_pages = [
    ('index', 'cornice', u'Cornice Documentation',
     [u'Mozilla Services'], 1)
]

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Messaging documentation build configuration file, created by
# sphinx-quickstart on Tue Dec 20 22:33:26 2011.
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
import cornice
sys.path.insert(0, os.path.abspath(cornice.__file__))
extensions = ['cornice.sphinxext']


# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Messaging'
copyright = u'2011, Tarek'

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
htmlhelp_basename = 'Messagingdoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'Messaging.tex', u'Messaging Documentation',
   u'Tarek', 'manual'),
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

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'messaging', u'Messaging Documentation',
     [u'Tarek'], 1)
]

########NEW FILE########
__FILENAME__ = client
import threading
import urllib2
import json
import time
import curses


_SERVER = 'http://localhost:6543'


def post(message, token):
    headers = {'X-Messaging-Token': token}
    req = urllib2.Request(_SERVER, headers=headers)
    req.get_method = lambda: 'POST'
    message = {'text': message}
    req.add_data(json.dumps(message))
    urllib2.urlopen(req)


def register(name):
    url = _SERVER + '/users'
    req = urllib2.Request(url)
    req.add_data(name)
    try:
        res = urllib2.urlopen(req)
    except urllib2.HTTPError:
        return False

    if res.getcode() != 200:
        return False

    return json.loads(res.read())['token']


class UpdateThread(threading.Thread):
    def __init__(self, server, token, scr):
        threading.Thread.__init__(self)
        self.server = server
        self.token = token
        self.updating = False
        self.pause = 1
        self.scr = scr

    def run(self):
        self.updating = True
        headers = {'X-Messaging-Token': self.token}
        req = urllib2.Request(self.server, headers=headers)

        while self.updating:
            res = urllib2.urlopen(req)
            result = json.loads(res.read())
            if result == []:
                continue

            y, x = self.scr.getyx()
            for index, line in enumerate(reversed(result)):
                self.scr.addstr(index + 2, 0,
                        '%s> %s' % (line['user'], line['text']))
            self.scr.move(y, x)
            self.scr.addstr(y, x, '')
            self.scr.refresh()
            time.sleep(self.pause)

    def stop(self):
        self.updating = False
        self.join()


def get_str(y, x, screen, msg):
    screen.addstr(y, x,  msg)
    str = []
    while True:
        cchar = screen.getch()
        if cchar == 10:
            return ''.join(str)
        str.append(chr(cchar))


def shell():
    stdscr = curses.initscr()
    stdscr.addstr(0, 0, "Welcome (type 'exit' to exit)")
    token = None

    while token is None:
        name = get_str(1, 0, stdscr, 'Select a name : ')
        token = register(name)
        if token is None:
            print('That name is taken')

    update = UpdateThread(_SERVER, token, stdscr)
    update.start()
    while True:
        try:
            msg = get_str(10, 0, stdscr, '> ')
            if msg == 'exit':
                break
            else:
                post(msg, token)

            stdscr.addstr(10, 0, ' ' * 100)
        except KeyboardInterrupt:
            update.stop()

    curses.endwin()

if __name__ == '__main__':
    shell()

########NEW FILE########
__FILENAME__ = views
""" Cornice services.
"""
import os
import binascii
import json

from webob import Response, exc
from cornice import Service


users = Service(name='users', path='/users', description="Users")
messages = Service(name='messages', path='/', description="Messages")


_USERS = {}
_MESSAGES = []


#
# Helpers
#
def _create_token():
    return binascii.b2a_hex(os.urandom(20))


class _401(exc.HTTPError):
    def __init__(self, msg='Unauthorized'):
        body = {'status': 401, 'message': msg}
        Response.__init__(self, json.dumps(body))
        self.status = 401
        self.content_type = 'application/json'


def valid_token(request):
    header = 'X-Messaging-Token'
    token = request.headers.get(header)
    if token is None:
        raise _401()

    token = token.split('-')
    if len(token) != 2:
        raise _401()

    user, token = token

    valid = user in _USERS and _USERS[user] == token
    if not valid:
        raise _401()

    request.validated['user'] = user


def unique(request):
    name = request.body
    if name in _USERS:
        request.errors.add('url', 'name', 'This user exists!')
    else:
        user = {'name': name, 'token': _create_token()}
        request.validated['user'] = user

#
# Services
#

#
# User Management
#


@users.get(validators=valid_token)
def get_users(request):
    """Returns a list of all users."""
    return {'users': _USERS.keys()}


@users.post(validators=unique)
def create_user(request):
    """Adds a new user."""
    user = request.validated['user']
    _USERS[user['name']] = user['token']
    return {'token': '%s-%s' % (user['name'], user['token'])}


@users.delete(validators=valid_token)
def del_user(request):
    """Removes the user."""
    name = request.validated['user']
    del _USERS[name]
    return {'Goodbye': name}

#
# Messages management
#


def valid_message(request):
    try:
        message = json.loads(request.body)
    except ValueError:
        request.errors.add('body', 'message', 'Not valid JSON')
        return

    # make sure we have the fields we want
    if 'text' not in message:
        request.errors.add('body', 'text', 'Missing text')
        return

    if 'color' in message and message['color'] not in ('red', 'black'):
        request.errors.add('body', 'color', 'only red and black supported')
    elif 'color' not in message:
        message['color'] = 'black'

    message['user'] = request.validated['user']
    request.validated['message'] = message


@messages.get()
def get_messages(request):
    """Returns the 5 latest messages"""
    return _MESSAGES[:5]


@messages.post(validators=(valid_token, valid_message))
def post_message(request):
    """Adds a message"""
    _MESSAGES.insert(0, request.validated['message'])
    return {'status': 'added'}

########NEW FILE########
