__FILENAME__ = conf
# -*- coding: utf-8 -*-
# pylint: disable=C0103,W0622
'''
Sphinx documentation for salt-api
'''
import os
import sys

from sphinx.directives import TocTree

# pylint: disable=R0903
class Mock(object):
    '''
    Mock out specified imports

    This allows autodoc to do it's thing without having oodles of req'd
    installed libs. This doesn't work with ``import *`` imports.

    http://read-the-docs.readthedocs.org/en/latest/faq.html#i-get-import-errors-on-libraries-that-depend-on-c-modules
    '''
    def __init__(self, *args, **kwargs):
        pass

    def __call__(self, *args, **kwargs):
        return Mock()

    @classmethod
    def __getattr__(cls, name):
        if name in ('__file__', '__path__'):
            return '/dev/null'
        else:
            return Mock()
# pylint: enable=R0903

MOCK_MODULES = [
    # third-party libs (for netapi modules)
    'flask',
    'flask.globals',
    'flask.views',
    'werkzeug',
    'werkzeug.exceptions',
    'cheroot.ssllib',
    'cheroot.ssllib.ssl_builtin',

    'cheroot',
    'cheroot.wsgi',
    'cherrypy',
    'cherrypy.lib',
    'cherrypy.wsgiserver',
    'cherrypy.wsgiserver.ssl_builtin',

    'tornado',
    'tornado.concurrent',
    'tornado.gen',
    'tornado.httpserver',
    'tornado.ioloop',
    'tornado.web',

    'yaml',
    'zmq',

    # salt libs
    'salt',
    'salt.auth',
    'salt.client',
    'salt.exceptions',
    'salt.log',
    'salt.output',
    'salt.runner',
    'salt.utils',
    'salt.utils.event',
    'salt.wheel',
]

for mod_name in MOCK_MODULES:
    sys.modules[mod_name] = Mock()


# -- Add paths to PYTHONPATH ---------------------------------------------------

docs_basepath = os.path.abspath(os.path.dirname(__file__))
addtl_paths = (
    os.pardir, # salt-api itself (for autodoc/autohttp)
    '_ext', # custom Sphinx extensions
)

for path in addtl_paths:
    sys.path.insert(0, os.path.abspath(os.path.join(docs_basepath, path)))

from saltapi.version import __version__


on_rtd = os.environ.get('READTHEDOCS', None) == 'True'

# -- General configuration -----------------------------------------------------

project = 'salt-api'
copyright = '2012, Thomas S. Hatch'

version = __version__
release = version

master_doc = 'index'
templates_path = ['_templates']
exclude_patterns = ['_build']

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.intersphinx',
    'sphinxcontrib.httpdomain',
    'sphinxcontrib.autohttp.flask',
]

modindex_common_prefix = ['saltapi.']

autosummary_generate = True

intersphinx_mapping = {
    'salt': ('http://docs.saltstack.org/en/latest/', None),
}

### HTML options
html_theme = 'default'

html_title = None
html_short_title = 'salt-api'

html_static_path = ['_static']
html_logo = 'salt-vert.png'
html_favicon = 'favicon.ico'
html_use_smartypants = False

html_use_index = True
html_last_updated_fmt = '%b %d, %Y'
html_show_sourcelink = False
html_show_sphinx = True
html_show_copyright = True
#html_use_opensearch = ''


### Latex options
latex_documents = [
    ('index', 'salt-api.tex', 'salt-api Documentation', 'Thomas Hatch', 'manual'),
]

latex_logo = '_static/salt-vert.png'


### Manpage options
# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
authors = [
    'Thomas S. Hatch <thatch45@gmail.com> and many others, please see the Authors file',
]

man_pages = [
    ('ref/cli/salt-api', 'salt-api', 'salt-api', authors, 1),
    ('index', 'salt-api', 'salt-api Documentation', authors, 7),
]


### epub options
epub_title = 'salt-api Documentation'
epub_author = 'Thomas S. Hatch'
epub_publisher = epub_author
epub_copyright = '2012, Thomas S. Hatch'

epub_scheme = 'URL'
epub_identifier = 'http://saltstack.org/'

#epub_tocdepth = 3

###############################################################################

def _normalize_version(args):
    _, path = args
    return '.'.join([x.zfill(4) for x in (path.split('/')[-1].split('.'))])

class ReleasesTree(TocTree):
    option_spec = dict(TocTree.option_spec)

    def run(self):
        rst = super(ReleasesTree, self).run()
        entries = rst[0][0]['entries'][:]
        entries.sort(key=_normalize_version, reverse=True)
        rst[0][0]['entries'][:] = entries
        return rst

def setup(app):
    # Copy ReleasesTree directive from Salt for properly sorting release
    # numbers with glob
    app.add_directive('releasestree', ReleasesTree)
    # Copy crossref types from Salt for master/minion conf files
    app.add_crossref_type(directivename="conf_master", rolename="conf_master",
            indextemplate="pair: %s; conf/master")
    app.add_crossref_type(directivename="conf_minion", rolename="conf_minion",
            indextemplate="pair: %s; conf/minion")

########NEW FILE########
__FILENAME__ = cli
'''
CLI entry-point for salt-api
'''
# Import python libs
import sys
import logging

# Import salt libs
import salt.utils.verify
from salt.utils.parsers import (
    ConfigDirMixIn,
    DaemonMixIn,
    LogLevelMixIn,
    MergeConfigMixIn,
    OptionParser,
    OptionParserMeta,
    PidfileMixin)

# Import salt-api libs
import saltapi.client
import saltapi.config
import saltapi.version

log = logging.getLogger(__name__)


class SaltAPI(OptionParser, ConfigDirMixIn, LogLevelMixIn, PidfileMixin,
              DaemonMixIn, MergeConfigMixIn):
    '''
    The cli parser object used to fire up the salt api system.
    '''
    __metaclass__ = OptionParserMeta

    VERSION = saltapi.version.__version__

    # ConfigDirMixIn config filename attribute
    _config_filename_ = 'master'
    # LogLevelMixIn attributes
    _default_logging_logfile_ = '/var/log/salt/api'

    def setup_config(self):
        return saltapi.config.api_config(self.get_config_file_path())

    def run(self):
        '''
        Run the api
        '''
        self.parse_args()
        try:
            if self.config['verify_env']:
                logfile = self.config['log_file']
                if logfile is not None and not logfile.startswith('tcp://') \
                        and not logfile.startswith('udp://') \
                        and not logfile.startswith('file://'):
                    # Logfile is not using Syslog, verify
                    salt.utils.verify.verify_files(
                        [logfile], self.config['user']
                    )
        except OSError as err:
            log.error(err)
            sys.exit(err.errno)

        self.setup_logfile_logger()
        client = saltapi.client.SaltAPIClient(self.config)
        self.daemonize_if_required()
        self.set_pidfile()
        client.run()

########NEW FILE########
__FILENAME__ = client
'''
The main entry point for salt-api
'''
# Import python libs
import logging
import multiprocessing

# Import salt-api libs
import saltapi.loader

logger = logging.getLogger(__name__)

class SaltAPIClient(object):
    '''
    '''
    def __init__(self, opts):
        self.opts = opts

    def run(self):
        '''
        Load and start all available api modules
        '''
        netapi = saltapi.loader.netapi(self.opts)
        for fun in netapi:
            if fun.endswith('.start'):
                logger.info("Starting '{0}' api module".format(fun))
                multiprocessing.Process(target=netapi[fun]).start()

########NEW FILE########
__FILENAME__ = config
'''
Manage configuration files in salt-api
'''

# Import salt libs
import salt.config

DEFAULT_API_OPTS = {
    # ----- Salt master settings overridden by Salt-API --------------------->
    'pidfile': '/var/run/salt-api.pid',
    'logfile': '/var/log/salt/api',
    # <---- Salt master settings overridden by Salt-API ----------------------
}


def api_config(path):
    '''
    Read in the salt master config file and add additional configs that
    need to be stubbed out for salt-api
    '''
    # Let's grab a copy of salt's master default opts
    defaults = salt.config.DEFAULT_MASTER_OPTS
    # Let's override them with salt-api's required defaults
    defaults.update(DEFAULT_API_OPTS)

    return salt.config.master_config(path, defaults=defaults)

########NEW FILE########
__FILENAME__ = loader
'''
The salt api module loader interface
'''
# Import python libs
import os

# Import Salt libs
import salt.loader
import saltapi


def netapi(opts):
    '''
    Return the network api functions
    '''
    load = salt.loader._create_loader(
            opts,
            'netapi',
            'netapi',
            base_path=os.path.dirname(saltapi.__file__)
            )
    return load.gen_functions()

def runner(opts):
    '''
    Load the runners, this function bypasses the issue with the altered
    basepath
    '''
    load = salt.loader._create_loader(
            opts,
            'runners',
            'runner',
            ext_type_dirs='runner_dirs',
            base_path=os.path.dirname(salt.__file__)
            )
    return load.gen_functions()

########NEW FILE########
__FILENAME__ = app
'''
A REST API for Salt
===================

.. py:currentmodule:: saltapi.netapi.rest_cherrypy.app

:depends:   - CherryPy Python module
:configuration: All authentication is done through Salt's :ref:`external auth
    <acl-eauth>` system. Be sure that it is enabled and the user you are
    authenticating as has permissions for all the functions you will be
    running.

    Example production configuration block; add to the Salt master config file:

    .. code-block:: yaml

        rest_cherrypy:
          port: 8000
          ssl_crt: /etc/pki/tls/certs/localhost.crt
          ssl_key: /etc/pki/tls/certs/localhost.key

    The REST interface strongly recommends a secure HTTPS connection since Salt
    authentication credentials will be sent over the wire. If you don't already
    have a certificate and don't wish to buy one, you can generate a
    self-signed certificate using the
    :py:func:`~salt.modules.tls.create_self_signed_cert` function in Salt (note
    the dependencies for this module):

    .. code-block:: bash

        % salt-call tls.create_self_signed_cert

    All available configuration options are detailed below. These settings
    configure the CherryPy HTTP server and do not apply when using an external
    server such as Apache or Nginx.

    port
        **Required**

        The port for the webserver to listen on.
    host : ``0.0.0.0``
        The socket interface for the HTTP server to listen on.

        .. versionadded:: 0.8.2
    debug : ``False``
        Starts the web server in development mode. It will reload itself when
        the underlying code is changed and will output more debugging info.
    ssl_crt
        The path to a SSL certificate. (See below)
    ssl_key
        The path to the private key for your SSL certificate. (See below)
    disable_ssl
        A flag to disable SSL. Warning: your Salt authentication credentials
        will be sent in the clear!

        .. versionadded:: 0.8.3
    webhook_disable_auth : False
        The :py:class:`Webhook` URL requires authentication by default but
        external services cannot always be configured to send authentication.
        See the Webhook documentation for suggestions on securing this
        interface.

        .. versionadded:: 0.8.4.1
    webhook_url : /hook
        Configure the URL endpoint for the :py:class:`Webhook` entry point.

        .. versionadded:: 0.8.4.1
    thread_pool : ``100``
        The number of worker threads to start up in the pool.

        .. versionchanged:: 0.8.4
            Previous versions defaulted to a pool of ``10``
    socket_queue_size : ``30``
        Specify the maximum number of HTTP connections to queue.

        .. versionchanged:: 0.8.4
            Previous versions defaulted to ``5`` connections.
    max_request_body_size : ``1048576``
        .. versionchanged:: 0.8.4
            Previous versions defaulted to ``104857600`` for the size of the
            request body
    collect_stats : False
        Collect and report statistics about the CherryPy server

        .. versionadded:: 0.8.4

        Reports are available via the :py:class:`Stats` URL.
    static
        A filesystem path to static HTML/JavaScript/CSS/image assets.
    static_path : ``/static``
        The URL prefix to use when serving static assets out of the directory
        specified in the ``static`` setting.

        .. versionadded:: 0.8.2
    app
        A filesystem path to an HTML file that will be served as a static file.
        This is useful for bootstrapping a single-page JavaScript app.

        .. versionadded:: 0.8.2
    app_path : ``/app``
        The URL prefix to use for serving the HTML file specified in the ``app``
        setting. This should be a simple name containing no slashes.

        Any path information after the specified path is ignored; this is
        useful for apps that utilize the HTML5 history API.

        .. versionadded:: 0.8.2
    root_prefix : ``/``
        A URL path to the main entry point for the application. This is useful
        for serving multiple applications from the same URL.

        .. versionadded:: 0.8.4

Authentication
--------------

Authentication is performed by passing a session token with each request. The
token may be sent either via a custom header named :mailheader:`X-Auth-Token`
or sent inside a cookie. (The result is the same but browsers and some HTTP
clients handle cookies automatically and transparently so it is a convenience.)

Token are generated via the :py:class:`Login` URL.

.. seealso:: You can bypass the session handling via the :py:class:`Run` URL.

Usage
-----

You access a running Salt master via this module by sending HTTP requests to
the URLs detailed below.

.. admonition:: Content negotiation

    This REST interface is flexible in what data formats it will accept as well
    as what formats it will return (e.g., JSON, YAML, x-www-form-urlencoded).

    * Specify the format of data you are sending in a request by including the
      :mailheader:`Content-Type` header.
    * Specify your desired output format for the response with the
      :mailheader:`Accept` header.

This REST interface expects data sent in :http:method:`post` and
:http:method:`put` requests  to be in the format of a list of lowstate
dictionaries. This allows you to specify multiple commands in a single request.

.. glossary::

    lowstate
        A dictionary containing various keys that instruct Salt which command
        to run, where that command lives, any parameters for that command, any
        authentication credentials, what returner to use, etc.

        Salt uses the lowstate data format internally in many places to pass
        command data between functions. Salt also uses lowstate for the
        :ref:`LocalClient() <python-api>` Python API interface.

For example (in JSON format)::

    [{
        'client': 'local',
        'tgt': '*',
        'fun': 'test.fib',
        'arg': ['10'],
    }]

.. admonition:: x-www-form-urlencoded

    This REST interface accepts data in the x-www-form-urlencoded format. This
    is the format used by HTML forms, the default format used by
    :command:`curl`, the default format used by many JavaScript AJAX libraries
    (such as jQuery), etc. This format will be converted to the
    :term:`lowstate` format as best as possible with the caveats below. It is
    always preferable to format data in the lowstate format directly in a more
    capable format such as JSON or YAML.

    * Only a single command may be sent in this format per HTTP request.
    * Multiple ``arg`` params will be sent as a single list of params.

      Note, some popular frameworks and languages (notably jQuery, PHP, and
      Ruby on Rails) will automatically append empty brackets onto repeated
      parameters. E.g., arg=one, arg=two will be sent as arg[]=one, arg[]=two.
      Again, it is preferable to send lowstate via JSON or YAML directly by
      specifying the :mailheader:`Content-Type` header in the request.

URL reference
-------------

The main entry point is the :py:class:`root URL (/) <LowDataAdapter>` and all
functionality is available at that URL. The other URLs are largely convenience
URLs that wrap that main entry point with shorthand or specialized
functionality.

'''
# We need a custom pylintrc here...
# pylint: disable=W0212,E1101,C0103,R0201,W0221,W0613

# Import Python libs
import collections
import itertools
import functools
import logging
import json

# Import third-party libs
import cherrypy
from cherrypy.lib import cpstats
import yaml

# Import Salt libs
import salt
import salt.auth
import salt.utils.event

# Import salt-api libs
import saltapi

logger = logging.getLogger(__name__)


def salt_token_tool():
    '''
    If the custom authentication header is supplied, put it in the cookie dict
    so the rest of the session-based auth works as intended
    '''
    x_auth = cherrypy.request.headers.get('X-Auth-Token', None)

    # X-Auth-Token header trumps session cookie
    if x_auth:
        cherrypy.request.cookie['session_id'] = x_auth

def salt_ip_verify_tool():
    '''
    If there is a list of restricted IPs, verify current
    client is coming from one of those IPs.
    '''
    # This is overly cumbersome and crude,
    # But, it's also safe... ish...
    salt_config = cherrypy.config.get('saltopts', None)
    if salt_config:
        cherrypy_conf = salt_config.get('rest_cherrypy', None)
        if cherrypy_conf:
            auth_ip_list = cherrypy_conf.get('authorized_ips', None)
            if auth_ip_list:
                logger.debug("Found IP list: {0}".format(auth_ip_list))
                rem_ip = cherrypy.request.headers.get('Remote-Addr', None)
                logger.debug("Request from IP: {0}".format(rem_ip))
                if not rem_ip in auth_ip_list:
                    logger.error("Blocked IP: {0}".format(rem_ip))
                    cherrypy.response.status = 403
                    return {
                        'status': cherrypy.response.status,
                        'return': "Bad IP",
                    }
    request = cherrypy.serving.request
    cherrypy.response.headers['Access-Control-Allow-Origin'] = '*'


def salt_auth_tool():
    '''
    Redirect all unauthenticated requests to the login page
    '''
    # Redirect to the login page if the session hasn't been authed
    if not cherrypy.session.has_key('token'):
        raise cherrypy.InternalRedirect('/login')

    # Session is authenticated; inform caches
    cherrypy.response.headers['Cache-Control'] = 'private'

# Be conservative in what you send
# Maps Content-Type to serialization functions; this is a tuple of tuples to
# preserve order of preference.
ct_out_map = (
    ('application/json', json.dumps),
    ('application/x-yaml', functools.partial(
        yaml.safe_dump, default_flow_style=False)),
)

def hypermedia_handler(*args, **kwargs):
    '''
    Determine the best output format based on the Accept header, execute the
    regular handler, and transform the output to the request content type (even
    if it's an error).

    :param args: Pass args through to the main handler
    :param kwargs: Pass kwargs through to the main handler
    '''
    # Execute the real handler. Handle or pass-through any errors we know how
    # to handle (auth & HTTP errors). Reformat any errors we don't know how to
    # handle as a data structure.
    try:
        cherrypy.response.processors = dict(ct_out_map) # handlers may modify this
        ret = cherrypy.serving.request._hypermedia_inner_handler(*args, **kwargs)
    except salt.exceptions.EauthAuthenticationError:
        raise cherrypy.InternalRedirect('/login')
    except cherrypy.CherryPyException:
        raise
    except Exception as exc:
        import traceback

        logger.debug("Error while processing request for: %s",
                cherrypy.request.path_info,
                exc_info=True)

        cherrypy.response.status = 500

        ret = {
            'status': cherrypy.response.status,
            'return': '{0}'.format(traceback.format_exc(exc))
                    if cherrypy.config['debug']
                    else "An unexpected error occurred"}

    # Raises 406 if requested content-type is not supported
    best = cherrypy.lib.cptools.accept([i for (i, _) in ct_out_map])

    # Transform the output from the handler into the requested output format
    cherrypy.response.headers['Content-Type'] = best
    out = cherrypy.response.processors[best]
    return out(ret)


def hypermedia_out():
    '''
    Determine the best handler for the requested content type

    Wrap the normal handler and transform the output from that handler into the
    requested content type
    '''
    request = cherrypy.serving.request
    request._hypermedia_inner_handler = request.handler
    request.handler = hypermedia_handler

    cherrypy.response.headers['Access-Control-Allow-Origin'] = '*'


@functools.wraps
def process_request_body(fn):
    '''
    A decorator to skip a processor function if process_request_body is False
    '''
    def wrapped(*args, **kwargs):
        if cherrypy.request.process_request_body != False:
            fn(*args, **kwargs)
    return wrapped


def urlencoded_processor(entity):
    '''
    Accept x-www-form-urlencoded data (run through CherryPy's formatter)
    and reformat it into a Low State data structure.

    Since we can't easily represent complicated data structures with
    key-value pairs, any more complicated requirements (e.g. compound
    commands) must instead be delivered via JSON or YAML.

    For example::

        curl -si localhost:8000 -d client=local -d tgt='*' \\
                -d fun='test.kwarg' -d arg='one=1' -d arg='two=2'

    :param entity: raw POST data
    '''
    # First call out to CherryPy's default processor
    cherrypy._cpreqbody.process_urlencoded(entity)
    cherrypy.serving.request.unserialized_data = entity.params


@process_request_body
def json_processor(entity):
    '''
    Unserialize raw POST data in JSON format to a Python data structure.

    :param entity: raw POST data
    '''
    body = entity.fp.read()
    try:
        cherrypy.serving.request.unserialized_data = json.loads(body)
    except ValueError:
        raise cherrypy.HTTPError(400, 'Invalid JSON document')


@process_request_body
def yaml_processor(entity):
    '''
    Unserialize raw POST data in YAML format to a Python data structure.

    :param entity: raw POST data
    '''
    body = entity.fp.read()
    try:
        cherrypy.serving.request.unserialized_data = yaml.safe_load(body)
    except ValueError:
        raise cherrypy.HTTPError(400, 'Invalid YAML document')


@process_request_body
def text_processor(entity):
    '''
    Attempt to unserialize plain text as JSON

    Some large services still send JSON with a text/plain Content-Type. Those
    services are bad and should feel bad.

    :param entity: raw POST data
    '''
    body = entity.fp.read()
    try:
        cherrypy.serving.request.unserialized_data = json.loads(body)
    except ValueError:
        cherrypy.serving.request.unserialized_data = body


def hypermedia_in():
    '''
    Unserialize POST/PUT data of a specified Content-Type.

    The following custom processors all are intended to format Low State data
    and will place that data structure into the request object.

    :raises HTTPError: if the request contains a Content-Type that we do not
        have a processor for
    '''
    # Be liberal in what you accept
    ct_in_map = {
        'application/x-www-form-urlencoded': urlencoded_processor,
        'application/json': json_processor,
        'application/x-yaml': yaml_processor,
        'text/yaml': yaml_processor,
        'text/plain': text_processor,
    }

    # Do not process the body for POST requests that have specified no content
    # or have not specified Content-Length
    if (cherrypy.request.method.upper() == 'POST'
            and cherrypy.request.headers.get('Content-Length', '0') == '0'):
        cherrypy.request.process_request_body = False

    cherrypy.request.body.processors.clear()
    cherrypy.request.body.default_proc = cherrypy.HTTPError(
            406, 'Content type not supported')
    cherrypy.request.body.processors = ct_in_map


def lowdata_fmt():
    '''
    Validate and format lowdata from incoming unserialized request data

    This tool requires that the hypermedia_in tool has already been run.
    '''
    if cherrypy.request.method.upper() != 'POST':
        return

    # TODO: call lowdata validation routines from here

    data = cherrypy.request.unserialized_data

    if cherrypy.request.headers['Content-Type'] == 'application/x-www-form-urlencoded':
        # Make the 'arg' param a list if not already
        if 'arg' in data and not isinstance(data['arg'], list):
            data['arg'] = [data['arg']]

        # Finally, make a Low State and put it in request
        cherrypy.request.lowstate = [data]
    else:
        cherrypy.serving.request.lowstate = data


cherrypy.tools.salt_token = cherrypy.Tool('on_start_resource',
        salt_token_tool, priority=55)
cherrypy.tools.salt_auth = cherrypy.Tool('before_request_body',
        salt_auth_tool, priority=60)
cherrypy.tools.hypermedia_in = cherrypy.Tool('before_request_body',
        hypermedia_in)
cherrypy.tools.lowdata_fmt = cherrypy.Tool('before_handler',
        lowdata_fmt, priority=40)
cherrypy.tools.hypermedia_out = cherrypy.Tool('before_handler',
        hypermedia_out)
cherrypy.tools.salt_ip_verify = cherrypy.Tool('before_handler',
        salt_ip_verify_tool)


###############################################################################


class LowDataAdapter(object):
    '''
    The primary entry point to the REST API. All functionality is available
    through this URL. The other available URLs provide convenience wrappers
    around this URL.
    '''
    exposed = True

    _cp_config = {
        'tools.sessions.on': True,
        'tools.sessions.timeout': 60 * 10, # 10 hours

        # 'tools.autovary.on': True,

        'tools.hypermedia_out.on': True,
        'tools.hypermedia_in.on': True,
        'tools.lowdata_fmt.on': True,
        'tools.salt_ip_verify.on': True,
    }

    def __init__(self):
        self.opts = cherrypy.config['saltopts']
        self.api = saltapi.APIClient(self.opts)

    def exec_lowstate(self, client=None, token=None):
        '''
        Pull a Low State data structure from request and execute the low-data
        chunks through Salt. The low-data chunks will be updated to include the
        authorization token for the current session.
        '''
        lowstate = cherrypy.request.lowstate

        # Release the session lock before executing any potentially
        # long-running Salt commands. This allows different threads to execute
        # Salt commands concurrently without blocking.
        cherrypy.session.release_lock()

        # if the lowstate loaded isn't a list, lets notify the client
        if type(lowstate) != list:
            raise cherrypy.HTTPError(400, 'Lowstates must be a list')

        # Make any requested additions or modifications to each lowstate, then
        # execute each one and yield the result.
        for chunk in lowstate:
            if token:
                chunk['token'] = token

            if client:
                chunk['client'] = client

            # Make any 'arg' params a list if not already.
            # This is largely to fix a deficiency in the urlencoded format.
            if 'arg' in chunk and not isinstance(chunk['arg'], list):
                chunk['arg'] = [chunk['arg']]

            ret = self.api.run(chunk)

            # Sometimes Salt gives us a return and sometimes an iterator
            if isinstance(ret, collections.Iterator):
                for i in ret:
                    yield i
            else:
                yield ret

    def GET(self):
        '''
        .. http:get:: /

            An explanation of the API with links of where to go next.

            **Example request**::

                % curl -i localhost:8000

            .. code-block:: http

                GET / HTTP/1.1
                Host: localhost:8000
                Accept: application/json

            **Example response**:

            .. code-block:: http

                HTTP/1.1 200 OK
                Content-Type: application/json

        :status 200: success
        :status 401: authentication required
        :status 406: requested Content-Type not available
        '''
        import inspect

        # Grab all available client interfaces
        clients = [name for name, _ in inspect.getmembers(saltapi.APIClient,
            predicate=inspect.ismethod) if not name.startswith('__')]
        clients.remove('run') # run method calls client interfaces

        return {
            'return': "Welcome",
            'clients': clients,
        }

    @cherrypy.tools.salt_token()
    @cherrypy.tools.salt_auth()
    def POST(self, **kwargs):
        '''
        The primary execution interface for the rest of the API

        .. http:post:: /

            **Example request**::

                % curl -si https://localhost:8000 \\
                        -H "Accept: application/x-yaml" \\
                        -H "X-Auth-Token: d40d1e1e" \\
                        -d client=local \\
                        -d tgt='*' \\
                        -d fun='test.ping' \\
                        -d arg

            .. code-block:: http

                POST / HTTP/1.1
                Host: localhost:8000
                Accept: application/x-yaml
                X-Auth-Token: d40d1e1e
                Content-Length: 36
                Content-Type: application/x-www-form-urlencoded

                fun=test.ping&arg&client=local&tgt=*

            **Example response**:

            .. code-block:: http

                HTTP/1.1 200 OK
                Content-Length: 200
                Allow: GET, HEAD, POST
                Content-Type: application/x-yaml

                return:
                - ms-0: true
                  ms-1: true
                  ms-2: true
                  ms-3: true
                  ms-4: true

        :form lowstate: A list of :term:`lowstate` data appropriate for the
            :ref:`client <client-apis>` interface you are calling.

            Lowstate may be supplied in any supported format by specifying the
            :mailheader:`Content-Type` header in the request. Supported formats
            are listed in the :mailheader:`Alternates` response header.
        :status 200: success
        :status 401: authentication required
        :status 406: requested Content-Type not available
        '''
        return {
            'return': list(self.exec_lowstate(
                token=cherrypy.session.get('token')))
        }


class Minions(LowDataAdapter):
    _cp_config = dict(LowDataAdapter._cp_config, **{
        'tools.salt_token.on': True,
        'tools.salt_auth.on': True,
    })

    def GET(self, mid=None):
        '''
        A convenience URL for getting lists of minions or getting minion
        details

        .. http:get:: /minions/(mid)

            Get grains, modules, functions, and inline function documentation
            for all minions or a single minion

            **Example request**::

                % curl -i localhost:8000/minions/ms-3

            .. code-block:: http

                GET /minions/ms-3 HTTP/1.1
                Host: localhost:8000
                Accept: application/x-yaml

            **Example response**:

            .. code-block:: http

                HTTP/1.1 200 OK
                Content-Length: 129005
                Content-Type: application/x-yaml

                return:
                - ms-3:
                    grains.items:
                      ...

        :param mid: (optional) a minion id
        :status 200: success
        :status 401: authentication required
        :status 406: requested Content-Type not available
        '''
        cherrypy.request.lowstate = [{
            'client': 'local', 'tgt': mid or '*', 'fun': 'grains.items',
        }]
        return {
            'return': list(self.exec_lowstate(
                token=cherrypy.session.get('token'))),
        }

    def POST(self, **kwargs):
        '''
        Start an execution command and immediately return the job id

        .. http:post:: /minions

            You must pass low-data in the request body either from an HTML form
            or as JSON or YAML. The ``client`` option is pre-set to
            ``local_async``.

            **Example request**::

                % curl -sSi localhost:8000/minions \\
                    -H "Accept: application/x-yaml" \\
                    -d tgt='*' \\
                    -d fun='status.diskusage'

            .. code-block:: http

                POST /minions HTTP/1.1
                Host: localhost:8000
                Accept: application/x-yaml
                Content-Length: 26
                Content-Type: application/x-www-form-urlencoded

                tgt=*&fun=status.diskusage

            **Example response**:

            .. code-block:: http

                HTTP/1.1 202 Accepted
                Content-Length: 86
                Content-Type: application/x-yaml

                return:
                - jid: '20130603122505459265'
                  minions: [ms-4, ms-3, ms-2, ms-1, ms-0]
                _links:
                  jobs:
                  - href: /jobs/20130603122505459265

        :form lowstate: lowstate data for the
            :py:mod:`~salt.client.LocalClient`; the ``client`` parameter will
            be set to ``local_async``

            Lowstate may be supplied in any supported format by specifying the
            :mailheader:`Content-Type` header in the request. Supported formats
            are listed in the :mailheader:`Alternates` response header.
        :status 202: success
        :status 401: authentication required
        :status 406: requested :mailheader:`Content-Type` not available
        '''
        job_data = list(self.exec_lowstate(client='local_async',
            token=cherrypy.session.get('token')))

        cherrypy.response.status = 202
        return {
            'return': job_data,
            '_links': {
                'jobs': [{'href': '/jobs/{0}'.format(i['jid'])}
                    for i in job_data if i],
            },
        }


class Jobs(LowDataAdapter):
    _cp_config = dict(LowDataAdapter._cp_config, **{
        'tools.salt_token.on': True,
        'tools.salt_auth.on': True,
    })

    def GET(self, jid=None):
        '''
        A convenience URL for getting lists of previously run jobs or getting
        the return from a single job

        .. http:get:: /jobs/(jid)

            Get grains, modules, functions, and inline function documentation
            for all minions or a single minion

            **Example request**::

                % curl -i localhost:8000/jobs

            .. code-block:: http

                GET /jobs HTTP/1.1
                Host: localhost:8000
                Accept: application/x-yaml

            **Example response**:

            .. code-block:: http

                HTTP/1.1 200 OK
                Content-Length: 165
                Content-Type: application/x-yaml

                return:
                - '20121130104633606931':
                    Arguments:
                    - '3'
                    Function: test.fib
                    Start Time: 2012, Nov 30 10:46:33.606931
                    Target: jerry
                    Target-type: glob

            **Example request**::

                % curl -i localhost:8000/jobs/20121130104633606931

            .. code-block:: http

                GET /jobs/20121130104633606931 HTTP/1.1
                Host: localhost:8000
                Accept: application/x-yaml

            **Example response**:

            .. code-block:: http

                HTTP/1.1 200 OK
                Content-Length: 73
                Content-Type: application/x-yaml

                info:
                - Arguments:
                  - '3'
                  Function: test.fib
                  Minions:
                  - jerry
                  Start Time: 2012, Nov 30 10:46:33.606931
                  Target: '*'
                  Target-type: glob
                  User: saltdev
                  jid: '20121130104633606931'
                return:
                - jerry:
                  - - 0
                    - 1
                    - 1
                    - 2
                  - 6.9141387939453125e-06

        :param mid: (optional) a minion id
        :status 200: success
        :status 401: authentication required
        :status 406: requested Content-Type not available
        '''
        lowstate = [{
            'client': 'runner',
            'fun': 'jobs.lookup_jid' if jid else 'jobs.list_jobs',
            'jid': jid,
        }]

        if jid:
            lowstate.append({
                'client': 'runner',
                'fun': 'jobs.list_job',
                'jid': jid,
            })

        cherrypy.request.lowstate = lowstate
        job_ret_info = list(self.exec_lowstate(
            token=cherrypy.session.get('token')))

        ret = {}
        if jid:
            job_ret, job_info = job_ret_info
            ret['info'] = [job_info]
        else:
            job_ret = job_ret_info[0]

        ret['return'] = [job_ret]
        return ret


class Login(LowDataAdapter):
    '''
    All interactions with this REST API must be authenticated. Authentication
    is performed through Salt's eauth system. You must set the eauth backend
    and allowed users by editing the :conf_master:`external_auth` section in
    your master config.

    Authentication credentials are passed to the REST API via a session id in
    one of two ways:

    If the request is initiated from a browser it must pass a session id via a
    cookie and that session must be valid and active.

    If the request is initiated programmatically, the request must contain a
    :mailheader:`X-Auth-Token` header with valid and active session id.
    '''

    def __init__(self, *args, **kwargs):
        super(Login, self).__init__(*args, **kwargs)

        self.auth = salt.auth.Resolver(self.opts)

    def GET(self):
        '''
        Present the login interface

        .. http:get:: /login

            An explanation of how to log in.

            **Example request**::

                % curl -i localhost:8000/login

            .. code-block:: http

                GET /login HTTP/1.1
                Host: localhost:8000
                Accept: text/html

            **Example response**:

            .. code-block:: http

                HTTP/1.1 200 OK
                Content-Type: text/html

        :status 401: authentication required
        :status 406: requested Content-Type not available
        '''
        cherrypy.response.headers['WWW-Authenticate'] = 'Session'

        return {
            'status': cherrypy.response.status,
            'return': "Please log in",
        }

    def POST(self, **kwargs):
        '''
        Authenticate against Salt's eauth system

        .. versionchanged:: 0.8.0
            No longer returns a 302 redirect on success.

        .. versionchanged:: 0.8.1
            Returns 401 on authentication failure

        .. http:post:: /login

            **Example request**::

                % curl -si localhost:8000/login \\
                        -H "Accept: application/json" \\
                        -d username='saltuser' \\
                        -d password='saltpass' \\
                        -d eauth='pam'

            .. code-block:: http

                POST / HTTP/1.1
                Host: localhost:8000
                Content-Length: 42
                Content-Type: application/x-www-form-urlencoded
                Accept: application/json

                username=saltuser&password=saltpass&eauth=pam

            **Example response**:

            .. code-block:: http

                HTTP/1.1 200 OK
                Content-Type: application/json
                Content-Length: 206
                X-Auth-Token: 6d1b722e
                Set-Cookie: session_id=6d1b722e; expires=Sat, 17 Nov 2012 03:23:52 GMT; Path=/

                {"return": {
                    "token": "6d1b722e",
                    "start": 1363805943.776223,
                    "expire": 1363849143.776224,
                    "user": "saltuser",
                    "eauth": "pam",
                    "perms": [
                        "grains.*",
                        "status.*",
                        "sys.*",
                        "test.*"
                    ]
                }}

        :form eauth: the eauth backend configured in your master config
        :form username: username
        :form password: password
        :status 200: success
        :status 401: could not authenticate using provided credentials
        :status 406: requested Content-Type not available
        '''
        # the urlencoded_processor will wrap this in a list
        if isinstance(cherrypy.serving.request.lowstate, list):
            creds = cherrypy.serving.request.lowstate[0]
        else:
            creds = cherrypy.serving.request.lowstate

        token = self.auth.mk_token(creds)
        if not 'token' in token:
            raise cherrypy.HTTPError(401,
                    'Could not authenticate using provided credentials')

        cherrypy.response.headers['X-Auth-Token'] = cherrypy.session.id
        cherrypy.session['token'] = token['token']
        cherrypy.session['timeout'] = (token['expire'] - token['start']) / 60

        # Grab eauth config for the current backend for the current user
        try:
            perms = self.opts['external_auth'][token['eauth']][token['name']]
        except (AttributeError, IndexError):
            logger.debug("Configuration for external_auth malformed for "\
                "eauth '{0}', and user '{1}'."
                .format(token.get('eauth'), token.get('name')), exc_info=True)
            raise cherrypy.HTTPError(500,
                'Configuration for external_auth could not be read.')

        return {'return': [{
            'token': cherrypy.session.id,
            'expire': token['expire'],
            'start': token['start'],
            'user': token['name'],
            'eauth': token['eauth'],
            'perms': perms,
        }]}


class Logout(LowDataAdapter):
    _cp_config = dict(LowDataAdapter._cp_config, **{
        'tools.salt_token.on': True,
        'tools.salt_auth.on': True,
    })

    def POST(self):
        '''
        Destroy the currently active session and expire the session cookie

        .. versionadded:: 0.8.0
        '''
        cherrypy.lib.sessions.expire() # set client-side to expire
        cherrypy.session.regenerate() # replace server-side with new

        return {'return': "Your token has been cleared"}


class Run(LowDataAdapter):
    _cp_config = dict(LowDataAdapter._cp_config, **{
        'tools.sessions.on': False,
    })

    def POST(self, **kwargs):
        '''
        Run commands bypassing the normal session handling

        .. versionadded:: 0.8.0

        .. http:post:: /run

            This entry point is primarily for "one-off" commands. Each request
            must pass full Salt authentication credentials. Otherwise this URL
            is identical to the root (``/``) execution URL.

            **Example request**::

                % curl -sS localhost:8000/run \\
                    -H 'Accept: application/x-yaml' \\
                    -d client='local' \\
                    -d tgt='*' \\
                    -d fun='test.ping' \\
                    -d username='saltdev' \\
                    -d password='saltdev' \\
                    -d eauth='pam'

            .. code-block:: http

                POST /run HTTP/1.1
                Host: localhost:8000
                Accept: application/x-yaml
                Content-Length: 75
                Content-Type: application/x-www-form-urlencoded

                client=local&tgt=*&fun=test.ping&username=saltdev&password=saltdev&eauth=pam

            **Example response**:

            .. code-block:: http

                HTTP/1.1 200 OK
                Content-Length: 73
                Content-Type: application/x-yaml

                return:
                - ms-0: true
                  ms-1: true
                  ms-2: true
                  ms-3: true
                  ms-4: true

        :form lowstate: A list of :term:`lowstate` data appropriate for the
            :ref:`client <client-apis>` specified client interface. Full
            external authentication credentials must be included.
        :status 200: success
        :status 401: authentication failed
        :status 406: requested Content-Type not available
        '''
        return {
            'return': list(self.exec_lowstate()),
        }


class Events(object):
    '''
    The event bus on the Salt master exposes a large variety of things, notably
    when executions are started on the master and also when minions ultimately
    return their results. This URL provides a real-time window into a running
    Salt infrastructure.
    '''
    exposed = True

    _cp_config = dict(LowDataAdapter._cp_config, **{
        'response.stream': True,
        'tools.encode.encoding': 'utf-8',

        # Auth handled manually below
        'tools.salt_token.on': True,
        'tools.salt_auth.on': False,

        'tools.hypermedia_in.on': False,
        'tools.hypermedia_out.on': False,
    })

    def __init__(self):
        self.opts = cherrypy.config['saltopts']
        self.auth = salt.auth.LoadAuth(self.opts)

    def GET(self, token=None):
        '''
        Return an HTTP stream of the Salt master event bus; this stream is
        formatted per the Server Sent Events (SSE) spec

        .. versionadded:: 0.8.3

        Browser clients currently lack Cross-origin resource sharing (CORS)
        support for the ``EventSource()`` API. Cross-domain requests from a
        browser may instead pass the :mailheader:`X-Auth-Token` value as an URL
        parameter::

            % curl -NsS localhost:8000/events/6d1b722e

        .. http:get:: /events

            **Example request**::

                % curl -NsS localhost:8000/events

            .. code-block:: http

                GET /events HTTP/1.1
                Host: localhost:8000

            **Example response**:

            .. code-block:: http

                HTTP/1.1 200 OK
                Connection: keep-alive
                Cache-Control: no-cache
                Content-Type: text/event-stream;charset=utf-8

                retry: 400
                data: {'tag': '', 'data': {'minions': ['ms-4', 'ms-3', 'ms-2', 'ms-1', 'ms-0']}}

                data: {'tag': '20130802115730568475', 'data': {'jid': '20130802115730568475', 'return': True, 'retcode': 0, 'success': True, 'cmd': '_return', 'fun': 'test.ping', 'id': 'ms-1'}}

        The event stream can be easily consumed via JavaScript:

        .. code-block:: javascript

            # Note, you must be authenticated!
            var source = new EventSource('/events');
            source.onopen = function() { console.debug('opening') };
            source.onerror = function(e) { console.debug('error!', e) };
            source.onmessage = function(e) { console.debug(e.data) };

        It is also possible to consume the stream via the shell.

        Records are separated by blank lines; the ``data:`` and ``tag:``
        prefixes will need to be removed manually before attempting to
        unserialize the JSON.

        curl's ``-N`` flag turns off input buffering which is required to
        process the stream incrementally.

        Here is a basic example of printing each event as it comes in:

        .. code-block:: bash

            % curl -NsS localhost:8000/events |\\
                    while IFS= read -r line ; do
                        echo $line
                    done

        Here is an example of using awk to filter events based on tag:

        .. code-block:: bash

            % curl -NsS localhost:8000/events |\\
                    awk '
                        BEGIN { RS=""; FS="\\n" }
                        $1 ~ /^tag: salt\/job\/[0-9]+\/new$/ { print $0 }
                    '
            tag: salt/job/20140112010149808995/new
            data: {"tag": "salt/job/20140112010149808995/new", "data": {"tgt_type": "glob", "jid": "20140112010149808995", "tgt": "jerry", "_stamp": "2014-01-12_01:01:49.809617", "user": "shouse", "arg": [], "fun": "test.ping", "minions": ["jerry"]}}
            tag: 20140112010149808995
            data: {"tag": "20140112010149808995", "data": {"fun_args": [], "jid": "20140112010149808995", "return": true, "retcode": 0, "success": true, "cmd": "_return", "_stamp": "2014-01-12_01:01:49.819316", "fun": "test.ping", "id": "jerry"}}

        :status 200: success
        :status 401: could not authenticate using provided credentials
        '''
        # Pulling the session token from an URL param is a workaround for
        # browsers not supporting CORS in the EventSource API.
        if token:
            orig_sesion, _ = cherrypy.session.cache.get(token, ({}, None))
            salt_token = orig_sesion.get('token')
        else:
            salt_token = cherrypy.session.get('token')

        # Manually verify the token
        if not salt_token or not self.auth.get_tok(salt_token):
            raise cherrypy.InternalRedirect('/login')

        # Release the session lock before starting the long-running response
        cherrypy.session.release_lock()

        cherrypy.response.headers['Content-Type'] = 'text/event-stream'
        cherrypy.response.headers['Cache-Control'] = 'no-cache'
        cherrypy.response.headers['Connection'] = 'keep-alive'

        def listen():
            event = salt.utils.event.SaltEvent('master', self.opts['sock_dir'])
            stream = event.iter_events(full=True)

            yield u'retry: {0}\n'.format(400)

            while True:
                data = stream.next()
                yield u'tag: {0}\n'.format(data.get('tag', ''))
                yield u'data: {0}\n\n'.format(json.dumps(data))

        return listen()


class Webhook(object):
    '''
    A generic web hook entry point that fires an event on Salt's event bus

    External services can POST data to this URL to trigger an event in Salt.
    For example, Amazon SNS, Jenkins-CI or Travis-CI, or GitHub web hooks.

    .. note:: Be mindful of security

        Salt's Reactor can run any code. A Reactor SLS that responds to a hook
        event is responsible for validating that the event came from a trusted
        source and contains valid data.

        **This is a generic interface and securing it is up to you!**

        This URL requires authentication however not all external services can
        be configured to authenticate. For this reason authentication can be
        selectively disabled for this URL. Follow best practices -- always use
        SSL, pass a secret key, configure the firewall to only allow traffic
        from a known source, etc.

    The event data is taken from the request body. The
    :mailheader:`Content-Type` header is respected for the payload.

    The event tag is prefixed with ``salt/netapi/hook`` and the URL path is
    appended to the end. For example, a ``POST`` request sent to
    ``/hook/mycompany/myapp/mydata`` will produce a Salt event with the tag
    ``salt/netapi/hook/mycompany/myapp/mydata``. See the :ref:`Salt Reactor
    <reactor>` documentation for how to react to events with various tags.

    The following is an example ``.travis.yml`` file to send notifications to
    Salt of successful test runs:

    .. code-block:: yaml

        language: python
        script: python -m unittest tests
        after_success:
            - 'curl -sS http://saltapi-url.example.com:8000/hook/travis/build/success -d branch="${TRAVIS_BRANCH}" -d commit="${TRAVIS_COMMIT}"'

    '''
    exposed = True
    tag_base = ['salt', 'netapi', 'hook']

    _cp_config = dict(LowDataAdapter._cp_config, **{
        # Don't do any lowdata processing on the POST data
        'tools.lowdata_fmt.on': True,

        # Auth can be overridden in __init__().
        'tools.salt_token.on': True,
        'tools.salt_auth.on': True,
    })

    def __init__(self):
        self.opts = cherrypy.config['saltopts']
        self.event = salt.utils.event.SaltEvent('master',
                self.opts.get('sock_dir', ''))

        if cherrypy.config['apiopts'].get('webhook_disable_auth'):
            self._cp_config['tools.salt_token.on'] = False
            self._cp_config['tools.salt_auth.on'] = False

    def POST(self, *args, **kwargs):
        '''
        Fire an event in Salt with a custom event tag and data

        .. versionadded:: 0.8.4

        .. http:post:: /hook

            **Example request**::

                % curl -sS localhost:8000/hook -d foo='Foo!' -d bar='Bar!'

            .. code-block:: http

                POST /hook HTTP/1.1
                Host: localhost:8000
                Content-Length: 16
                Content-Type: application/x-www-form-urlencoded

                foo=Foo&bar=Bar!

            **Example response**:

            .. code-block:: http

                HTTP/1.1 200 OK
                Content-Length: 14
                Content-Type: application/json

                {"success": true}

        As a practical example, an internal continuous-integration build
        server could send an HTTP POST request to the URL
        ``http://localhost:8000/hook/mycompany/build/success`` which contains
        the result of a build and the SHA of the version that was built as
        JSON. That would then produce the following event in Salt that could be
        used to kick off a deployment via Salt's Reactor::

            Event fired at Fri Feb 14 17:40:11 2014
            *************************
            Tag: salt/netapi/hook/mycompany/build/success
            Data:
            {'_stamp': '2014-02-14_17:40:11.440996',
                'headers': {
                    'X-My-Secret-Key': 'F0fAgoQjIT@W',
                    'Content-Length': '37',
                    'Content-Type': 'application/json',
                    'Host': 'localhost:8000',
                    'Remote-Addr': '127.0.0.1'},
                'post': {'revision': 'aa22a3c4b2e7', 'result': True}}

        Salt's Reactor could listen for the event:

        .. code-block:: yaml

            reactor:
              - 'salt/netapi/hook/mycompany/build/*':
                - /srv/reactor/react_ci_builds.sls

        And finally deploy the new build:

        .. code-block:: yaml

            {% set secret_key = data.get('headers', {}).get('X-My-Secret-Key') %}
            {% set build = data.get('post', {}) %}

            {% if secret_key == 'F0fAgoQjIT@W' and build.result == True %}
            deploy_my_app:
              cmd.state.sls:
                - tgt: 'application*'
                - arg:
                  - myapp.deploy
                - kwarg:
                    pillar:
                      revision: {{ revision }}
            {% endif %}

        :status 200: success
        :status 406: requested Content-Type not available
        :status 413: request body is too large
        '''
        tag = '/'.join(itertools.chain(self.tag_base, args))
        data = cherrypy.serving.request.unserialized_data
        headers = dict(cherrypy.request.headers)

        ret = self.event.fire_event({
            'post': data,
            'headers': headers,
        }, tag)
        return {'success': ret}


class Stats(object):
    '''
    Expose statistics on the running CherryPy server
    '''
    exposed = True

    _cp_config = dict(LowDataAdapter._cp_config, **{
        'tools.salt_token.on': True,
        'tools.salt_auth.on': True,
    })

    def GET(self):
        '''
        Return a dump of statistics collected from the CherryPy server

        :status 200: success
        :status 406: requested Content-Type not available
        '''
        if hasattr(logging, 'statistics'):
            return cpstats.extrapolate_statistics(logging.statistics)

        return {}


class App(object):
    exposed = True
    def GET(self, *args):
        apiopts = cherrypy.config['apiopts']
        return cherrypy.lib.static.serve_file(apiopts['app'])


class API(object):
    '''
    Collect configuration and URL map for building the CherryPy app
    '''
    url_map = {
        'index': LowDataAdapter,
        'login': Login,
        'logout': Logout,
        'minions': Minions,
        'run': Run,
        'jobs': Jobs,
        'events': Events,
        'stats': Stats,
    }

    def __init__(self):
        self.opts = cherrypy.config['saltopts']
        self.apiopts = cherrypy.config['apiopts']

        for url, cls in self.url_map.items():
            setattr(self, url, cls())

        # Allow the Webhook URL to be overridden from the conf.
        setattr(self, self.apiopts.get('webhook_url', 'hook').lstrip('/'), Webhook())

        if 'app' in self.apiopts:
            setattr(self, self.apiopts.get('app_path', 'app').lstrip('/'), App())

    def get_conf(self):
        '''
        Combine the CherryPy configuration with the rest_cherrypy config values
        pulled from the master config and return the CherryPy configuration
        '''
        conf = {
            'global': {
                'server.socket_host': self.apiopts.get('host', '0.0.0.0'),
                'server.socket_port': self.apiopts.get('port', 8000),
                'server.thread_pool': self.apiopts.get('thread_pool', 100),
                'server.socket_queue_size': self.apiopts.get('queue_size', 30),
                'max_request_body_size': self.apiopts.get('max_request_body_size', 1048576),
                'debug': self.apiopts.get('debug', False),
            },
            '/': {
                'request.dispatch': cherrypy.dispatch.MethodDispatcher(),

                'tools.trailing_slash.on': True,
                'tools.gzip.on': True,

                'tools.cpstats.on': self.apiopts.get('collect_stats', False),
            },
        }

        if self.apiopts.get('debug', False) == False:
            conf['global']['environment'] = 'production'

        # Serve static media if the directory has been set in the configuration
        if 'static' in self.apiopts:
            conf[self.apiopts.get('static_path', '/static')] = {
                'tools.staticdir.on': True,
                'tools.staticdir.dir': self.apiopts['static'],
            }

        # Add to global config
        cherrypy.config.update(conf['global'])

        return conf


def get_app(opts):
    '''
    Returns a WSGI app and a configuration dictionary
    '''
    apiopts = opts.get(__name__.rsplit('.', 2)[-2], {}) # rest_cherrypy opts

    # Add Salt and salt-api config options to the main CherryPy config dict
    cherrypy.config['saltopts'] = opts
    cherrypy.config['apiopts'] = apiopts

    root = API() # cherrypy app
    cpyopts = root.get_conf() # cherrypy app opts

    return root, apiopts, cpyopts

########NEW FILE########
__FILENAME__ = wsgi
#!/usr/bin/env python
'''
Deployment
==========

The ``rest_cherrypy`` netapi module is a standard Python WSGI app. It can be
deployed one of two ways.

:program:`salt-api` using the CherryPy server
---------------------------------------------

The default configuration is to run this module using :program:`salt-api` to
start the Python-based CherryPy server. This server is lightweight,
multi-threaded, encrypted with SSL, and should be considered production-ready.

Using a WSGI-compliant web server
---------------------------------

This module may be deplayed on any WSGI-compliant server such as Apache with
mod_wsgi or Nginx with FastCGI, to name just two (there are many).

Note, external WSGI servers handle URLs, paths, and SSL certs directly. The
``rest_cherrypy`` configuration options are ignored and the ``salt-api`` daemon
does not need to be running at all. Remember Salt authentication credentials
are sent in the clear unless SSL is being enforced!

An example Apache virtual host configuration::

    <VirtualHost *:80>
        ServerName example.com
        ServerAlias *.example.com

        ServerAdmin webmaster@example.com

        LogLevel warn
        ErrorLog /var/www/example.com/logs/error.log
        CustomLog /var/www/example.com/logs/access.log combined

        DocumentRoot /var/www/example.com/htdocs

        WSGIScriptAlias / /path/to/saltapi/netapi/rest_cherrypy/wsgi.py
    </VirtualHost>

'''
# pylint: disable=C0103

import os

import cherrypy

def bootstrap_app():
    '''
    Grab the opts dict of the master config by trying to import Salt
    '''
    from saltapi.netapi.rest_cherrypy import app
    import salt.config

    __opts__ = salt.config.client_config(
            os.environ.get('SALT_MASTER_CONFIG', '/etc/salt/master'))
    return app.get_app(__opts__)


def get_application(*args):
    '''
    Returns a WSGI application function. If you supply the WSGI app and config
    it will use that, otherwise it will try to obtain them from a local Salt
    installation
    '''
    opts_tuple = args

    def wsgi_app(environ, start_response):
        root, _, conf = opts_tuple or bootstrap_app()
        cherrypy.config.update({'environment': 'embedded'})

        cherrypy.tree.mount(root, '/', conf)
        return cherrypy.tree(environ, start_response)

    return wsgi_app

application = get_application()

########NEW FILE########
__FILENAME__ = saltnado
'''

curl localhost:8888/login -d client=local -d username=username -d password=password -d eauth=pam

for testing
curl -H 'X-Auth-Token: 89010c15bcbc8e4fc4ce4605b6699165' localhost:8888 -d client=local -d tgt='*' -d fun='test.ping'

# not working.... but in siege 3.0.1 and posts..
siege -c 1 -n 1 "http://127.0.0.1:8888 POST client=local&tgt=*&fun=test.ping"

# this works
ab -c 50 -n 100 -p body -T 'application/x-www-form-urlencoded' http://localhost:8888/

{"return": [{"perms": ["*.*"], "start": 1396151398.373983, "token": "cb86b805e8915c84bceb0d466026caab", "expire": 1396194598.373983, "user": "jacksontj", "eauth": "pam"}]}[jacksontj@Thomas-PC netapi]$



'''

import logging
from copy import copy

import time

import sys

import tornado.httpserver
import tornado.ioloop
import tornado.web
import tornado.gen
from tornado.concurrent import Future

from collections import defaultdict

import math
import functools
import json
import yaml
import zmq
import fnmatch

# salt imports
import salt.utils
import salt.utils.event
from salt.utils.event import tagify
import salt.client
import salt.runner
import salt.auth

'''
The clients rest_cherrypi supports. We want to mimic the interface, but not
    necessarily use the same API under the hood
# all of these require coordinating minion stuff
 - "local" (done)
 - "local_async" (done)
 - "local_batch" (done)

# master side
 - "runner" (done)
 - "wheel" (need async api...)
'''


# TODO: refreshing clients using cachedict
saltclients = {'local': salt.client.LocalClient().run_job,
               # not the actual client we'll use.. but its what we'll use to get args
               'local_batch': salt.client.LocalClient().cmd_batch,
               'local_async': salt.client.LocalClient().run_job,
               'runner': salt.runner.RunnerClient(salt.config.master_config('/etc/salt/master')).async,
               }


AUTH_TOKEN_HEADER = 'X-Auth-Token'
AUTH_COOKIE_NAME = 'session_id'


class TimeoutException(Exception):
    pass


class Any(Future):
    '''
    Future that wraps other futures to "block" until one is done
    '''
    def __init__(self, futures):
        super(Any, self).__init__()
        for future in futures:
            future.add_done_callback(self.done_callback)

    def done_callback(self, future):
        self.set_result(future)


class EventListener():
    def __init__(self, mod_opts, opts):
        self.mod_opts = mod_opts
        self.opts = opts
        self.event = salt.utils.event.MasterEvent(opts['sock_dir'])

        # tag -> list of futures
        self.tag_map = defaultdict(list)

        # request_obj -> list of (tag, future)
        self.request_map = defaultdict(list)

    def clean_timeout_futures(self, request):
        '''
        Remove all futures that were waiting for request `request` since it is done waiting
        '''
        if request not in self.request_map:
            return
        for tag, future in self.request_map[request]:
            # TODO: log, this shouldn't happen...
            if tag not in self.tag_map:
                continue
            # mark the future done
            future.set_exception(TimeoutException())
            self.tag_map[tag].remove(future)

            # if that was the last of them, remove the key all together
            if len(self.tag_map[tag]) == 0:
                del self.tag_map[tag]

    def get_event(self, request,
                        tag='',
                        callback=None):
        '''
        Get an event (async of course) return a future that will get it later
        '''
        future = Future()
        if callback is not None:
            def handle_future(future):
                response = future.result()
                self.io_loop.add_callback(callback, response)
            future.add_done_callback(handle_future)
        # add this tag and future to the callbacks
        self.tag_map[tag].append(future)
        self.request_map[request].append((tag, future))

        return future

    def iter_events(self):
        '''
        Iterate over all events that could happen
        '''
        try:
            data = self.event.get_event_noblock()
            # see if we have any futures that need this info:
            for tag_prefix, futures in self.tag_map.items():
                if data['tag'].startswith(tag_prefix):
                    for future in futures:
                        if future.done():
                            continue
                        future.set_result(data)
                    del self.tag_map[tag_prefix]

            # call yourself back!
            tornado.ioloop.IOLoop.instance().add_callback(self.iter_events)

        except zmq.ZMQError as e:
            # TODO: not sure what other errors we can get...
            if e.errno != zmq.EAGAIN:
                raise Exception()
            # add callback in the future (to avoid spinning)
            # TODO: configurable timeout
            tornado.ioloop.IOLoop.instance().add_timeout(time.time() + 0.1, self.iter_events)
        except:
            logging.critical('Uncaught exception in the event_listener: {0}'.format(sys.exc_info()))
            # TODO: configurable timeout
            tornado.ioloop.IOLoop.instance().add_timeout(time.time() + 0.1, self.iter_events)


# TODO: move to a utils function within salt-- the batching stuff is a bit tied together
def get_batch_size(batch, num_minions):
    '''
    Return the batch size that you should have
    '''
    # figure out how many we can keep in flight
    partition = lambda x: float(x) / 100.0 * num_minions
    try:
        if '%' in batch:
            res = partition(float(batch.strip('%')))
            if res < 1:
                return int(math.ceil(res))
            else:
                return int(res)
        else:
            return int(batch)
    except ValueError:
        print(('Invalid batch data sent: {0}\nData must be in the form'
               'of %10, 10% or 3').format(batch))


class BaseSaltAPIHandler(tornado.web.RequestHandler):
    ct_out_map = (
        ('application/json', json.dumps),
        ('application/x-yaml', functools.partial(
            yaml.safe_dump, default_flow_style=False)),
    )

    def _verify_client(self, client):
        '''
        Verify that the client is in fact one we have
        '''
        if client not in saltclients:
            self.set_status(400)
            self.write('We don\'t serve your kind here')
            self.finish()

    @property
    def token(self):
        '''
        The token used for the request
        '''
        # find the token (cookie or headers)
        if AUTH_TOKEN_HEADER in self.request.headers:
            return self.request.headers[AUTH_TOKEN_HEADER]
        else:
            return self.get_cookie(AUTH_COOKIE_NAME)

    def _verify_auth(self):
        '''
        Boolean wether the request is auth'd
        '''

        return self.token and bool(self.application.auth.get_tok(self.token))

    def prepare(self):
        '''
        Run before get/posts etc. Pre-flight checks:
            - verify that we can speak back to them (compatible accept header)
        '''
        # verify the content type
        found = False
        for content_type, dumper in self.ct_out_map:
            if fnmatch.fnmatch(content_type, self.request.headers['Accept']):
                found = True
                break

        # better return message?
        if not found:
            self.send_error(406)

        self.content_type = content_type
        self.dumper = dumper

        # do the common parts
        self.start = time.time()
        self.connected = True

        self.lowstate = self._get_lowstate()

    def timeout_futures(self):
        '''
        timeout a session
        '''
        # TODO: set a header or something??? so we know it was a timeout
        self.application.event_listener.clean_timeout_futures(self)

    def on_finish(self):
        '''
        When the job has been done, lets cleanup
        '''
        # timeout all the futures
        self.timeout_futures()

    def on_connection_close(self):
        '''
        If the client disconnects, lets close out
        '''
        self.finish()

    def serialize(self, data):
        '''
        Serlialize the output based on the Accept header
        '''
        self.set_header('Content-Type', self.content_type)

        return self.dumper(data)

    def _form_loader(self, _):
        '''
        function to get the data from the urlencoded forms
        ignore the data passed in and just get the args from wherever they are
        '''
        data = {}
        for key, val in self.request.arguments.iteritems():
            if len(val) == 1:
                data[key] = val[0]
            else:
                data[key] = val
        return data

    def deserialize(self, data):
        '''
        Deserialize the data based on request content type headers
        '''
        ct_in_map = {
            'application/x-www-form-urlencoded': self._form_loader,
            'application/json': json.loads,
            'application/x-yaml': functools.partial(
                yaml.safe_load, default_flow_style=False),
            'text/yaml': functools.partial(
                yaml.safe_load, default_flow_style=False),
            # because people are terrible and dont mean what they say
            'text/plain': json.loads
        }

        try:
            if self.request.headers['Content-Type'] not in ct_in_map:
                self.send_error(406)
            return ct_in_map[self.request.headers['Content-Type']](data)
        except KeyError:
            return []

    def _get_lowstate(self):
        '''
        Format the incoming data into a lowstate object
        '''
        data = self.deserialize(self.request.body)
        self.raw_data = copy(data)

        if self.request.headers.get('Content-Type') == 'application/x-www-form-urlencoded':
            if 'arg' in data and not isinstance(data['arg'], list):
                data['arg'] = [data['arg']]
            lowstate = [data]
        else:
            lowstate = data
        return lowstate


class SaltAuthHandler(BaseSaltAPIHandler):
    '''
    Handler for login resquests
    '''
    def get(self):
        '''
        We don't allow gets on the login path, so lets send back a nice message
        '''
        self.set_status(401)
        self.set_header('WWW-Authenticate', 'Session')

        ret = {'status': '401 Unauthorized',
               'return': 'Please log in'}

        self.write(self.serialize(ret))
        self.finish()

    # TODO: make async? Underlying library isn't... and we ARE making disk calls :(
    def post(self):
        '''
        Authenticate against Salt's eauth system
        {"return": {"start": 1395507384.320007, "token": "6ff4cd2b770ada48713afc629cd3178c", "expire": 1395550584.320007, "name": "jacksontj", "eauth": "pam"}}
        {"return": [{"perms": ["*.*"], "start": 1395507675.396021, "token": "dea8274dc359fee86357d9d0263ec93c0498888e", "expire": 1395550875.396021, "user": "jacksontj", "eauth": "pam"}]}
        '''
        creds = {'username': self.get_arguments('username')[0],
                 'password': self.get_arguments('password')[0],
                 'eauth': self.get_arguments('eauth')[0],
                 }

        token = self.application.auth.mk_token(creds)
        if not 'token' in token:
            # TODO: nicer error message
            # 'Could not authenticate using provided credentials')
            self.send_error(401)
            # return since we don't want to execute any more
            return

        # Grab eauth config for the current backend for the current user
        try:
            perms = self.application.opts['external_auth'][token['eauth']][token['name']]
        except (AttributeError, IndexError):
            logging.debug("Configuration for external_auth malformed for "
                         "eauth '{0}', and user '{1}'."
                         .format(token.get('eauth'), token.get('name')), exc_info=True)
            # TODO better error -- 'Configuration for external_auth could not be read.'
            self.send_error(500)

        ret = {'return': [{
            'token': token['token'],
            'expire': token['expire'],
            'start': token['start'],
            'user': token['name'],
            'eauth': token['eauth'],
            'perms': perms,
            }]}

        self.write(self.serialize(ret))
        self.finish()


class SaltAPIHandler(BaseSaltAPIHandler):
    '''
    Main API handler for base "/"
    '''
    def get(self):
        '''
        return data about what clients you have
        '''
        ret = {"clients": saltclients.keys(),
               "return": "Welcome"}
        self.write(self.serialize(ret))
        self.finish()

    @tornado.web.asynchronous
    def post(self):
        '''
        This function takes in all the args for dispatching requests
            **Example request**::

            % curl -si https://localhost:8000 \\
                    -H "Accept: application/x-yaml" \\
                    -H "X-Auth-Token: d40d1e1e" \\
                    -d client=local \\
                    -d tgt='*' \\
                    -d fun='test.sleep' \\
                    -d arg=1
        '''
        # if you aren't authenticated, redirect to login
        if not self._verify_auth():
            self.redirect('/login')
            return

        client = self.get_arguments('client')[0]
        self._verify_client(client)
        self.disbatch(client)

    def disbatch(self, client):
        '''
        Disbatch a lowstate job to the appropriate client
        '''
        self.client = client

        for low in self.lowstate:
            if (not self._verify_auth() or 'eauth' in low):
                # TODO: better error?
                self.set_status(401)
                self.finish()
                return
        # disbatch to the correct handler
        try:
            getattr(self, '_disbatch_{0}'.format(self.client))()
        except AttributeError:
            # TODO set the right status... this means we didn't implement it...
            self.set_status(500)
            self.finish()

    @tornado.gen.coroutine
    def _disbatch_local_batch(self):
        '''
        Disbatch local client batched commands
        '''
        self.ret = []

        for chunk in self.lowstate:
            f_call = salt.utils.format_call(saltclients['local_batch'], chunk)

            timeout = float(chunk.get('timeout', self.application.opts['timeout']))
            # set the timeout
            timeout_obj = tornado.ioloop.IOLoop.instance().add_timeout(time.time() + timeout, self.timeout_futures)

            # ping all the minions (to see who we have to talk to)
            # TODO: actually ping them all? this just gets the pub data
            minions = saltclients['local'](chunk['tgt'],
                                           'test.ping',
                                           [],
                                           expr_form=f_call['kwargs']['expr_form'])['minions']

            chunk_ret = {}
            maxflight = get_batch_size(f_call['kwargs']['batch'], len(minions))
            inflight_futures = []
            # do this batch
            while len(minions) > 0:
                # if you have more to go, lets disbatch jobs
                while len(inflight_futures) < maxflight:
                    minion_id = minions.pop(0)
                    f_call['args'][0] = minion_id
                    # TODO: list??
                    f_call['kwargs']['expr_form'] = 'glob'
                    pub_data = saltclients['local'](*f_call.get('args', ()), **f_call.get('kwargs', {}))
                    print pub_data
                    tag = tagify([pub_data['jid'], 'ret', minion_id], 'job')
                    future = self.application.event_listener.get_event(self, tag=tag)
                    inflight_futures.append(future)

                # wait until someone is done
                finished_future = yield Any(inflight_futures)
                try:
                    event = finished_future.result()
                except TimeoutException:
                    break
                print event
                chunk_ret[event['data']['id']] = event['data']['return']
                inflight_futures.remove(finished_future)

            self.ret.append(chunk_ret)

            # if we finish in time, cancel the timeout
            tornado.ioloop.IOLoop.instance().remove_timeout(timeout_obj)

        self.write(self.serialize({'return': self.ret}))
        self.finish()

    @tornado.gen.coroutine
    def _disbatch_local(self):
        '''
        Disbatch local client commands
        '''
        self.ret = []

        for chunk in self.lowstate:
            timeout = float(chunk.get('timeout', self.application.opts['timeout']))
            # set the timeout
            tornado.ioloop.IOLoop.instance().add_timeout(time.time() + timeout, self.timeout_futures)
            timeout_obj = tornado.ioloop.IOLoop.instance().add_timeout(time.time() + timeout, self.timeout_futures)

            # TODO: not sure why.... we already verify auth, probably for ACLs
            # require token or eauth
            chunk['token'] = self.token

            chunk_ret = {}

            f_call = salt.utils.format_call(saltclients[self.client], chunk)
            # fire a job off
            pub_data = saltclients[self.client](*f_call.get('args', ()), **f_call.get('kwargs', {}))

            # get the tag that we are looking for
            tag = tagify([pub_data['jid'], 'ret'], 'job')

            minions_remaining = pub_data['minions']

            # while we are waiting on all the mininons
            while len(minions_remaining) > 0:
                try:
                    event = yield self.application.event_listener.get_event(self, tag=tag)
                    chunk_ret[event['data']['id']] = event['data']['return']
                    minions_remaining.remove(event['data']['id'])
                # if you hit a timeout, just stop waiting ;)
                except TimeoutException:
                    break
            self.ret.append(chunk_ret)

            # if we finish in time, cancel the timeout
            tornado.ioloop.IOLoop.instance().remove_timeout(timeout_obj)

        self.write(self.serialize({'return': self.ret}))
        self.finish()

    def _disbatch_local_async(self):
        '''
        Disbatch local client_async commands
        '''
        ret = []
        for chunk in self.lowstate:
            f_call = salt.utils.format_call(saltclients[self.client], chunk)
            # fire a job off
            pub_data = saltclients[self.client](*f_call.get('args', ()), **f_call.get('kwargs', {}))
            ret.append(pub_data)

        self.write(self.serialize({'return': ret}))
        self.finish()

    @tornado.gen.coroutine
    def _disbatch_runner(self):
        '''
        Disbatch runner client commands
        '''
        self.ret = []
        for chunk in self.lowstate:
            timeout = float(chunk.get('timeout', self.application.opts['timeout']))
            # set the timeout
            tornado.ioloop.IOLoop.instance().add_timeout(time.time() + timeout, self.timeout_futures)
            timeout_obj = tornado.ioloop.IOLoop.instance().add_timeout(time.time() + timeout, self.timeout_futures)

            f_call = {'args': [chunk['fun'], chunk]}
            pub_data = saltclients[self.client](chunk['fun'], chunk)
            tag = pub_data['tag'] + '/ret'
            try:
                event = yield self.application.event_listener.get_event(self, tag=tag)
                # only return the return data
                self.ret.append(event['data']['return'])

                # if we finish in time, cancel the timeout
                tornado.ioloop.IOLoop.instance().remove_timeout(timeout_obj)
            except TimeoutException:
                break

        self.write(self.serialize({'return': self.ret}))
        self.finish()


class MinionSaltAPIHandler(SaltAPIHandler):
    '''
    Handler for /minion requests
    '''
    @tornado.web.asynchronous
    def get(self, mid):
        # if you aren't authenticated, redirect to login
        if not self._verify_auth():
            self.redirect('/login')
            return

        #'client': 'local', 'tgt': mid or '*', 'fun': 'grains.items',
        self.lowstate = [{
            'client': 'local', 'tgt': mid or '*', 'fun': 'grains.items',
        }]
        self.disbatch('local')

    @tornado.web.asynchronous
    def post(self):
        '''
        local_async post endpoint
        '''
        # if you aren't authenticated, redirect to login
        if not self._verify_auth():
            self.redirect('/login')
            return

        self.disbatch('local_async')


class JobsSaltAPIHandler(SaltAPIHandler):
    '''
    Handler for /minion requests
    '''
    @tornado.web.asynchronous
    def get(self, jid=None):
        # if you aren't authenticated, redirect to login
        if not self._verify_auth():
            self.redirect('/login')
            return

        self.lowstate = [{
            'fun': 'jobs.lookup_jid' if jid else 'jobs.list_jobs',
            'jid': jid,
        }]

        if jid:
            self.lowstate.append({
                'fun': 'jobs.list_job',
                'jid': jid,
            })

        self.disbatch('runner')


class RunSaltAPIHandler(SaltAPIHandler):
    '''
    Handler for /run requests
    '''
    @tornado.web.asynchronous
    def post(self):
        client = self.get_arguments('client')[0]
        self._verify_client(client)
        self.disbatch(client)


class EventsSaltAPIHandler(SaltAPIHandler):
    '''
    Handler for /events requests
    '''
    @tornado.gen.coroutine
    def get(self):
        # if you aren't authenticated, redirect to login
        if not self._verify_auth():
            self.redirect('/login')
            return
        # set the streaming headers
        self.set_header('Content-Type', 'text/event-stream')
        self.set_header('Cache-Control', 'no-cache')
        self.set_header('Connection', 'keep-alive')

        self.write(u'retry: {0}\n'.format(400))
        self.flush()

        while True:
            try:
                event = yield self.application.event_listener.get_event(self)
                self.write(u'tag: {0}\n'.format(event.get('tag', '')))
                self.write(u'data: {0}\n\n'.format(json.dumps(event)))
                self.flush()
            except TimeoutException:
                break

        self.finish()


class WebhookSaltAPIHandler(SaltAPIHandler):
    '''
    Handler for /run requests
    '''
    def post(self, tag_suffix=None):
        if not self._verify_auth():
            self.redirect('/login')
            return

        # if you have the tag, prefix
        tag = 'salt/netapi/hook'
        if tag_suffix:
            tag += tag_suffix

        # TODO: consolidate??
        self.event = salt.utils.event.MasterEvent(self.application.opts['sock_dir'])

        ret = self.event.fire_event({
            'post': self.raw_data,
            'headers': self.request.headers,
        }, tag)

        self.write(self.serialize({'success': ret}))

########NEW FILE########
__FILENAME__ = rest_wsgi
'''
A minimalist REST API for Salt
==============================

This ``rest_wsgi`` module provides a no-frills REST interface to a running Salt
master. There are no dependencies.

Please read this introductory section in entirety before deploying this module.

:configuration: All authentication is done through Salt's :ref:`external auth
    <acl-eauth>` system. Be sure that it is enabled and the user you are
    authenticating as has permissions for all the functions you will be
    running.

    The configuration options for this module resides in the Salt master config
    file. All available options are detailed below.

    port
        **Required**

        The port for the webserver to listen on.

    Example configuration:

    .. code-block:: yaml

        rest_wsgi:
          port: 8001

This API is not very "RESTful"; please note the following:

* All requests must be sent to the root URL (``/``).
* All requests must be sent as a POST request with JSON content in the request
  body.
* All responses are in JSON.

.. seealso:: :py:mod:`rest_cherrypy <saltapi.netapi.rest_cherrypy.app>`

    The :py:mod:`rest_cherrypy <saltapi.netapi.rest_cherrypy.app>` module is
    more full-featured, production-ready, and has builtin security features.

Deployment
==========

The ``rest_wsgi`` netapi module is a standard Python WSGI app. It can be
deployed one of two ways.

:program:`salt-api` using a development-only server
---------------------------------------------------

If run directly via salt-api it uses the `wsgiref.simple_server()`__ that ships
in the Python standard library. This is a single-threaded server that is
intended for testing and development. This server does **not** use encryption;
please note that raw Salt authentication credentials must be sent with every
HTTP request.

**Running this module via salt-api is not recommended for most use!**

.. __: http://docs.python.org/2/library/wsgiref.html#module-wsgiref.simple_server

Using a WSGI-compliant web server
---------------------------------

This module may be run via any WSGI-compliant production server such as Apache
with mod_wsgi or Nginx with FastCGI.

It is highly recommended that this app be used with a server that supports
HTTPS encryption since raw Salt authentication credentials must be sent with
every request. Any apps that access Salt through this interface will need to
manually manage authentication credentials (either username and password or a
Salt token). Tread carefully.

Usage examples
==============

.. http:post:: /

    **Example request** for a basic ``test.ping``::

        % curl -sS -i \\
                -H 'Content-Type: application/json' \\
                -d '[{"eauth":"pam","username":"saltdev","password":"saltdev","client":"local","tgt":"*","fun":"test.ping"}]' localhost:8001

    **Example response**:

    .. code-block:: http

        HTTP/1.0 200 OK
        Content-Length: 89
        Content-Type: application/json

        {"return": [{"ms--4": true, "ms--3": true, "ms--2": true, "ms--1": true, "ms--0": true}]}

    **Example request** for an asyncronous ``test.ping``::

        % curl -sS -i \\
                -H 'Content-Type: application/json' \\
                -d '[{"eauth":"pam","username":"saltdev","password":"saltdev","client":"local_async","tgt":"*","fun":"test.ping"}]' localhost:8001

    **Example response**:

    .. code-block:: http

        HTTP/1.0 200 OK
        Content-Length: 103
        Content-Type: application/json

        {"return": [{"jid": "20130412192112593739", "minions": ["ms--4", "ms--3", "ms--2", "ms--1", "ms--0"]}]}

    **Example request** for looking up a job ID::

        % curl -sS -i \\
                -H 'Content-Type: application/json' \\
                -d '[{"eauth":"pam","username":"saltdev","password":"saltdev","client":"runner","fun":"jobs.lookup_jid","jid":"20130412192112593739"}]' localhost:8001

    **Example response**:

    .. code-block:: http

        HTTP/1.0 200 OK
        Content-Length: 89
        Content-Type: application/json

        {"return": [{"ms--4": true, "ms--3": true, "ms--2": true, "ms--1": true, "ms--0": true}]}

:form lowstate: A list of :term:`lowstate` data appropriate for the
    :ref:`client <client-apis>` interface you are calling.
:status 200: success
:status 401: authentication required

'''
import errno
import json
import logging
import os

# Import salt libs
import salt
import saltapi

# HTTP response codes to response headers map
H = {
    200: '200 OK',
    400: '400 BAD REQUEST',
    401: '401 UNAUTHORIZED',
    404: '404 NOT FOUND',
    405: '405 METHOD NOT ALLOWED',
    406: '406 NOT ACCEPTABLE',
    500: '500 INTERNAL SERVER ERROR',
}

__virtualname__ = 'rest_wsgi'

logger = logging.getLogger(__virtualname__)

def __virtual__():
    mod_opts = __opts__.get(__virtualname__, {})

    if 'port' in mod_opts:
        return __virtualname__

    return False

class HTTPError(Exception):
    '''
    A custom exception that can take action based on an HTTP error code
    '''
    def __init__(self, code, message):
        self.code = code
        Exception.__init__(self, '{0}: {1}'.format(code, message))

def mkdir_p(path):
    '''
    mkdir -p
    http://stackoverflow.com/a/600612/127816
    '''
    try:
        os.makedirs(path)
    except OSError as exc: # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else: raise

def read_body(environ):
    '''
    Pull the body from the request and return it
    '''
    length = environ.get('CONTENT_LENGTH', '0')
    length = 0 if length == '' else int(length)

    return environ['wsgi.input'].read(length)

def get_json(environ):
    '''
    Return the request body as JSON
    '''
    content_type = environ.get('CONTENT_TYPE', '')
    if content_type != 'application/json':
        raise HTTPError(406, 'JSON required')

    try:
        return json.loads(read_body(environ))
    except ValueError as exc:
        raise HTTPError(400, exc)

def get_headers(data, extra_headers=None):
    '''
    Takes the response data as well as any additional headers and returns a
    tuple of tuples of headers suitable for passing to start_response()
    '''
    response_headers = {
        'Content-Length': str(len(data)),
    }

    if extra_headers:
        response_headers.update(extra_headers)

    return response_headers.items()

def run_chunk(environ, lowstate):
    '''
    Expects a list of lowstate dictionaries that are executed and returned in
    order
    '''
    client = environ['SALT_APIClient']

    for chunk in lowstate:
        yield client.run(chunk)

def dispatch(environ):
    '''
    Do any path/method dispatching here and return a JSON-serializable data
    structure appropriate for the response
    '''
    method = environ['REQUEST_METHOD'].upper()

    if method == 'GET':
        return ("They found me. I don't know how, but they found me. "
                "Run for it, Marty!")
    elif method == 'POST':
        data = get_json(environ)
        return run_chunk(environ, data)
    else:
        raise HTTPError(405, 'Method Not Allowed')

def saltenviron(environ):
    '''
    Make Salt's opts dict and the APIClient available in the WSGI environ
    '''
    if not '__opts__' in locals():
        import salt.config
        __opts__ = salt.config.client_config(
                os.environ.get('SALT_MASTER_CONFIG', '/etc/salt/master'))

    environ['SALT_OPTS'] = __opts__
    environ['SALT_APIClient'] = saltapi.APIClient(__opts__)

def application(environ, start_response):
    '''
    Process the request and return a JSON response. Catch errors and return the
    appropriate HTTP code.
    '''
    # Instantiate APIClient once for the whole app
    saltenviron(environ)

    # Call the dispatcher
    try:
        resp = list(dispatch(environ))
        code = 200
    except HTTPError as exc:
        code = exc.code
        resp = str(exc)
    except salt.exceptions.EauthAuthenticationError as exc:
        code = 401
        resp = str(exc)
    except Exception as exc:
        code = 500
        resp = str(exc)

    # Convert the response to JSON
    try:
        ret = json.dumps({'return': resp})
    except TypeError as exc:
        code = 500
        ret = str(exc)

    # Return the response
    start_response(H[code], get_headers(ret, {
        'Content-Type': 'application/json',
    }))
    return (ret,)

def get_opts():
    '''
    Return the Salt master config as __opts__
    '''
    import salt.config

    return salt.config.client_config(
            os.environ.get('SALT_MASTER_CONFIG', '/etc/salt/master'))

def start():
    '''
    Start simple_server()
    '''
    from wsgiref.simple_server import make_server

    # When started outside of salt-api __opts__ will not be injected
    if not '__opts__' in globals():
        globals()['__opts__'] = get_opts()

        if __virtual__() == False:
            raise SystemExit(1)

    mod_opts = __opts__.get(__virtualname__, {})

    # pylint: disable-msg=C0103
    httpd = make_server('localhost', mod_opts['port'], application)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        raise SystemExit(0)

if __name__ == '__main__':
    start()

########NEW FILE########
__FILENAME__ = version
__version_info__ = (0, 8, 4)
__version__ = '.'.join(map(str, __version_info__))

# If we can get a version from Git use that instead, otherwise carry on
try:
    import subprocess
    from salt.utils import which

    git = which('git')
    if git:
        p = subprocess.Popen([git, 'describe'],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True)
        out, err = p.communicate()
        if out:
            __version__ = '{0}'.format(out.strip().lstrip('v'))
            __version_info__ = tuple(__version__.split('-', 1)[0].split('.'))
except Exception:
    pass

if __name__ == '__main__':
    print(__version__)

########NEW FILE########
__FILENAME__ = test_app
# coding: utf-8
import cgi
import json
import urllib

import cherrypy
import yaml

from tests.utils import BaseRestCherryPyTest

class TestAuth(BaseRestCherryPyTest):
    def test_get_root_noauth(self):
        '''
        GET requests to the root URL should not require auth
        '''
        request, response = self.request('/')
        self.assertEqual(response.status, '200 OK')

    def test_post_root_auth(self):
        '''
        POST requests to the root URL redirect to login
        '''
        self.assertRaisesRegexp(cherrypy.InternalRedirect, '\/login',
                self.request, '/', method='POST', data={})

    def test_login_noauth(self):
        '''
        GET requests to the login URL should not require auth
        '''
        request, response = self.request('/login')
        self.assertEqual(response.status, '200 OK')

    def test_webhook_auth(self):
        '''
        Requests to the webhook URL require auth by default
        '''
        self.assertRaisesRegexp(cherrypy.InternalRedirect, '\/login',
                self.request, '/hook', method='POST', data={})

class TestLogin(BaseRestCherryPyTest):
    auth_creds = (
            ('username', 'saltdev'),
            ('password', 'saltdev'),
            ('eauth', 'auto'))

    def test_good_login(self):
        '''
        Test logging in
        '''
        # Mock mk_token for a positive return
        self.Resolver.return_value.mk_token.return_value = {
            'token': '6d1b722e',
            'start': 1363805943.776223,
            'expire': 1363849143.776224,
            'name': 'saltdev',
            'eauth': 'auto',
        }

        body = urllib.urlencode(self.auth_creds)
        request, response = self.request('/login', method='POST', body=body,
            headers={
                'content-type': 'application/x-www-form-urlencoded'
        })
        self.assertEqual(response.status, '200 OK')

    def test_bad_login(self):
        '''
        Test logging in
        '''
        # Mock mk_token for a negative return
        self.Resolver.return_value.mk_token.return_value = {}

        body = urllib.urlencode({'totally': 'invalid_creds'})
        request, response = self.request('/login', method='POST', body=body,
            headers={
                'content-type': 'application/x-www-form-urlencoded'
        })
        self.assertEqual(response.status, '401 Unauthorized')

class TestWebhookDisableAuth(BaseRestCherryPyTest):
    __opts__ = {
        'rest_cherrypy': {
            'port': 8000,
            'debug': True,
            'webhook_disable_auth': True,
        },
    }

    def test_webhook_noauth(self):
        '''
        Auth can be disabled for requests to the webhook URL
        '''
        body = urllib.urlencode({'foo': 'Foo!'})
        request, response = self.request('/hook', method='POST', body=body,
            headers={
                'content-type': 'application/x-www-form-urlencoded'
        })
        self.assertEqual(response.status, '200 OK')

########NEW FILE########
__FILENAME__ = test_tools
# coding: utf-8
import json
import urllib

import cherrypy
import yaml

from saltapi.netapi.rest_cherrypy import app

from tests.utils import BaseRestCherryPyTest, BaseToolsTest

class TestOutFormats(BaseToolsTest):
    _cp_config = {
        'tools.hypermedia_out.on': True,
    }

    def test_default_accept(self):
        request, response = self.request('/')
        self.assertEqual(response.headers['Content-type'], 'application/json')

    def test_unsupported_accept(self):
        request, response = self.request('/', headers=(
            ('Accept', 'application/ms-word'),
        ))
        self.assertEqual(response.status, '406 Not Acceptable')

    def test_json_out(self):
        request, response = self.request('/', headers=(
            ('Accept', 'application/json'),
        ))
        self.assertEqual(response.headers['Content-type'], 'application/json')

    def test_yaml_out(self):
        request, response = self.request('/', headers=(
            ('Accept', 'application/x-yaml'),
        ))
        self.assertEqual(response.headers['Content-type'], 'application/x-yaml')

class TestInFormats(BaseToolsTest):
    _cp_config = {
        'tools.hypermedia_in.on': True,
    }

    def test_urlencoded_ctype(self):
        data = {'valid': 'stuff'}
        request, response = self.request('/', method='POST',
            body=urllib.urlencode(data), headers=(
                ('Content-type', 'application/x-www-form-urlencoded'),
        ))
        self.assertEqual(response.status, '200 OK')
        self.assertDictEqual(request.unserialized_data, data)

    def test_json_ctype(self):
        data = {'valid': 'stuff'}
        request, response = self.request('/', method='POST',
            body=json.dumps(data), headers=(
                ('Content-type', 'application/json'),
        ))
        self.assertEqual(response.status, '200 OK')
        self.assertDictEqual(request.unserialized_data, data)

    def test_json_as_text_out(self):
        '''
        Some service send JSON as text/plain for compatibility purposes
        '''
        data = {'valid': 'stuff'}
        request, response = self.request('/', method='POST',
            body=json.dumps(data), headers=(
                ('Content-type', 'text/plain'),
        ))
        self.assertEqual(response.status, '200 OK')
        self.assertDictEqual(request.unserialized_data, data)

    def test_yaml_ctype(self):
        data = {'valid': 'stuff'}
        request, response = self.request('/', method='POST',
            body=yaml.dump(data), headers=(
                ('Content-type', 'application/x-yaml'),
        ))
        self.assertEqual(response.status, '200 OK')
        self.assertDictEqual(request.unserialized_data, data)

########NEW FILE########
__FILENAME__ = cptestcase
# -*- coding: utf-8 -*-
# Copyright (c) 2011-2012, Sylvain Hellegouarch
# All rights reserved.

# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:

#      * Redistributions of source code must retain the above copyright notice,
#        this list of conditions and the following disclaimer.
#      * Redistributions in binary form must reproduce the above copyright notice,
#        this list of conditions and the following disclaimer in the documentation
#        and/or other materials provided with the distribution.
#      * Neither the name of Sylvain Hellegouarch nor the names of his contributors
#        may be used to endorse or promote products derived from this software
#        without specific prior written permission.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# Modified from the original. See the Git history of this file for details.
# https://bitbucket.org/Lawouach/cherrypy-recipes/src/50aff88dc4e24206518ec32e1c32af043f2729da/testing/unit/serverless/cptestcase.py

from StringIO import StringIO
import unittest
import urllib

import cherrypy

# Not strictly speaking mandatory but just makes sense
cherrypy.config.update({'environment': "test_suite"})

# This is mandatory so that the HTTP server isn't started
# if you need to actually start (why would you?), simply
# subscribe it back.
cherrypy.server.unsubscribe()

# simulate fake socket address... they are irrelevant in our context
local = cherrypy.lib.httputil.Host('127.0.0.1', 50000, "")
remote = cherrypy.lib.httputil.Host('127.0.0.1', 50001, "")

__all__ = ['BaseCherryPyTestCase']

class BaseCherryPyTestCase(unittest.TestCase):
    def request(self, path='/', method='GET', app_path='', scheme='http',
                proto='HTTP/1.1', body=None, qs=None, headers=None, **kwargs):
        """
        CherryPy does not have a facility for serverless unit testing.
        However this recipe demonstrates a way of doing it by
        calling its internal API to simulate an incoming request.
        This will exercise the whole stack from there.

        Remember a couple of things:

        * CherryPy is multithreaded. The response you will get
          from this method is a thread-data object attached to
          the current thread. Unless you use many threads from
          within a unit test, you can mostly forget
          about the thread data aspect of the response.

        * Responses are dispatched to a mounted application's
          page handler, if found. This is the reason why you
          must indicate which app you are targetting with
          this request by specifying its mount point.

        You can simulate various request settings by setting
        the `headers` parameter to a dictionary of headers,
        the request's `scheme` or `protocol`.

        .. seealso: http://docs.cherrypy.org/stable/refman/_cprequest.html#cherrypy._cprequest.Response
        """
        # This is a required header when running HTTP/1.1
        h = {'Host': '127.0.0.1'}

        # if we had some data passed as the request entity
        # let's make sure we have the content-length set
        fd = None
        if body is not None:
            h['content-length'] = '%d' % len(body)
            fd = StringIO(body)

        if headers is not None:
            h.update(headers)

        # Get our application and run the request against it
        app = cherrypy.tree.apps.get(app_path)
        if not app:
            # XXX: perhaps not the best exception to raise?
            raise AssertionError("No application mounted at '%s'" % app_path)

        # Cleanup any previous returned response
        # between calls to this method
        app.release_serving()

        # Let's fake the local and remote addresses
        request, response = app.get_serving(local, remote, scheme, proto)
        try:
            h = [(k, v) for k, v in h.iteritems()]
            response = request.run(method, path, qs, proto, h, fd)
        finally:
            if fd:
                fd.close()
                fd = None

        if response.output_status.startswith('500'):
            print response.body
            raise AssertionError("Unexpected error")

        # collapse the response into a bytestring
        response.collapse_body()
        return request, response

########NEW FILE########
