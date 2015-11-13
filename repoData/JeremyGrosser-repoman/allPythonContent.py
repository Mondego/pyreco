__FILENAME__ = buildbot
from simplejson import dumps
from webob import Response
from pycurl import Curl

from subprocess import Popen, PIPE
from multiprocessing import Queue
from traceback import format_exc
from time import sleep
import logging
import tarfile
import os
import os.path
import urllib
import uuid
import sys
import os

from config import conf
from common import RequestHandler

class GitRepository(object):
    def __init__(self, path=None):
        self.path = path

    def _cmd(self, args, shell=False):
        try:
            os.chdir(self.path)
        except: pass
        logging.debug('cwd: %s    exec: %s' % (os.getcwd(), ' '.join(args)))
        p = Popen(args, stdout=PIPE, stderr=PIPE, shell=shell)
        ret = (p.communicate(), p.returncode)
        if ret[0][0]:
            logging.debug('\n'.join(ret[0]))
        return ret

    def _git(self, args):
        return self._cmd(['/usr/bin/git'] + args)

    def clone(self, gitpath):
        return self._git(['clone', gitpath, self.path])

    def checkout(self, ref):
        return self._git(['checkout', ref])

    def submodule_init(self):
        return self._git(['submodule', 'init'])

    def submodule_update(self):
        return self._git(['submodule', 'update'])

    def ls_remote(self, gitpath):
        output, retcode = self._git(['ls-remote', '--heads', '--tags', gitpath])
        stdout, stderr = output
        return [x.split('\t') for x in stdout.split('\n') if x]

    def show_ref(self):
        output, retcode = self._git(['show-ref', '--heads', '--tags'])
        stdout, stderr = output
        return [x.split(' ', 1) for x in stdout.split('\n') if x]

    def build(self, signkey, pbuilderrc, resultsdir):
        if 'refs/heads/upstream' in [x[1] for x in self.show_ref()]:
            cmd = ['/usr/bin/git-buildpackage', '--git-sign', '--git-cleaner="fakeroot debian/rules clean"', '--git-keyid="%s"' % signkey, '--git-builder="pdebuild --debsign-k %s --auto-debsign --configfile %s --debbuildopts "-i.git -I.git -sa" --buildresult %s' % (signkey, pbuilderrc, resultsdir)]
        else:
            cmd = ['/usr/bin/pdebuild', '--debsign-k', signkey, '--auto-debsign', '--debbuildopts', '-i.git -I.git -sa', '--configfile', pbuilderrc, '--buildresult', resultsdir]
        return self._cmd(cmd)

class PackageHandler(RequestHandler):
    def get(self, gitpath, gitrepo):
        gitpath = os.path.join(conf('buildbot.gitpath.%s' % gitpath), gitrepo)

        repo = GitRepository()
        refs = repo.ls_remote(gitpath)
        return Response(status=200, body=dumps(refs))

    def post(self, gitpath, gitrepo):
        if not 'ref' in self.request.params:
            return Response(status=400, body='Required parameter "ref" is missing. You must pass a git tag, branch, or commit ID to be built.\n')

        gitpath = os.path.join(conf('buildbot.gitpath.%s' % gitpath), gitrepo)
        ref = self.request.params['ref']
        cburl = self.request.params.get('cburl', None)
        submodules = self.request.params.get('submodules', None)

        buildid = uuid.uuid4().hex

        build_worker(gitpath, ref, buildid, cburl, submodules)
        return Response(status=200, body=buildid + '\n')

class RepoListHandler(RequestHandler):
    def get(self, gitpath):
        try:
            gitindex = conf('buildbot.gitindex.%s' % gitpath)
        except KeyError:
            return Response(status=404, body='Unknown git path')
        response = urllib.urlopen(gitindex)
        index = response.read()
        index = [x.strip('\r\n ').split(' ')[0].rsplit('.')[0] for x in index.split('\n') if x.strip('\r\n ')]
        return Response(status=200, body=dumps(index))

class TarballHandler(RequestHandler):
    def get(self, buildid):
        builddir = os.path.join(conf('buildbot.buildpath'), buildid)
        if not os.path.exists(builddir):
            return Response(status=404, body='The build ID does not exist.\n')

        tarpath = os.path.join(builddir, 'package.tar.gz')
        if not os.path.exists(tarpath):
            return Response(status=400, body='The build is not done yet.\n')
        else:
            fd = file(tarpath, 'rb')
            data = fd.read()
            fd.close()
            return Response(status=200, body=data, content_type='application/x-tar-gz')

class StatusHandler(RequestHandler):
    def get(self, buildid):
        builddir = os.path.join(conf('buildbot.buildpath'), buildid)
        if not os.path.exists(builddir):
            return Response(status=404, body='The build ID does not exist.\n')

        try:
            log = file('%s/build.log' % builddir, 'r').read()
        except:
            log = ''
        if not os.path.exists(builddir + '/package.tar.gz'):
            return Response(status=400, body='The build is not done yet.\n' + log)
        else:
            return Response(status=200, body='Build complete.\n' + log)

def buildlog(buildid, message):
    filename = os.path.join(conf('buildbot.buildpath'), '%s/build.log' % buildid)
    fd = file(filename, 'a+')
    fd.write(message + '\n')
    fd.close()
    logging.debug(message)

def build_thread(gitpath, ref, buildid, cburl=None, submodules=False):
    tmpdir = os.path.join(conf('buildbot.buildpath'), buildid)
    repo = GitRepository(tmpdir)

    output, retcode = repo.clone(gitpath)
    if retcode:
        buildlog(buildid, 'Unable to clone %s. %s\n' % (gitpath, '\n'.join(output)))
        return

    output, retcode = repo.checkout(ref)
    if retcode:
        buildlog(buildid, 'Unable to checkout %s. %s\n' % (ref, '\n'.join(output)))
        return

    if submodules:
        output, retcode = repo.submodule_init()
        buildlog(buildid, output[0])
        buildlog(buildid, output[1])
        output, retcode = repo.submodule_update()
        buildlog(buildid, output[0])
        buildlog(buildid, output[1])

    resultsdir = os.path.join(tmpdir, '.build_results')
    os.makedirs(resultsdir)
    output, retcode = repo.build(conf('buildbot.signkey'), conf('buildbot.pbuilderrc'), resultsdir)

    buildlog(buildid, output[0])
    buildlog(buildid, output[1])
    #logging.debug(output[0])
    #logging.debug(output[1])

    os.chdir(resultsdir)
    if not os.listdir(resultsdir) or retcode != 0:
        buildlog(buildid, 'Nothing in results directory. Giving up.')
        return

    tarpath = os.path.join(tmpdir, 'package.tar.gz')
    tar = tarfile.open(tarpath, 'w:gz')
    for name in os.listdir(resultsdir):
        tar.add(name)
    tar.close()

    buildlog(buildid, 'Build complete. Results in %s\n' % tarpath)
    data = file(tarpath, 'rb').read()
    buildlog(buildid, 'Built %i byte tarball' % len(data))

    if cburl:
        buildlog(buildid, 'Performing callback: %s' % cburl)
        req = Curl()
        req.setopt(req.POST, 1)
        req.setopt(req.URL, str(cburl))
        req.setopt(req.HTTPPOST, [('package', (req.FORM_FILE, str(tarpath)))])
        req.setopt(req.WRITEDATA, file('%s/build.log' % tmpdir, 'a+'))
        req.perform()
        req.close()


def build_worker(gitpath, ref, buildid, cburl, submodules):
    if os.fork() == 0:
        build_thread(gitpath, ref, buildid, cburl, submodules)

########NEW FILE########
__FILENAME__ = client
# -*- coding: utf-8 -*-
#
# © 2010 SimpleGeo, Inc. All rights reserved.
# Author: Ian Eure <ian@simplegeo.com>
#

"""A command-line tool for interacting with repoman."""

from __future__ import with_statement
import sys
import time
import logging
import os.path
import tarfile
from textwrap import fill, dedent
from optparse import OptionParser
from itertools import imap, takewhile
from functools import wraps
from urllib import urlencode

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

import simplejson as json
from httplib2 import Http
from poster.encode import multipart_encode, MultipartParam

API_URL = os.getenv("REPOMAN_API_URL", "")


class ArgumentError(Exception):

    """Raised when invalid arguments are provided to a command."""


def format_dict(pkg):
    """Return a string containing a nicely formatted dict."""
    width = max(imap(len, pkg.iterkeys()))
    pkg['Description'] = fill(pkg['Description'], 79,
                              subsequent_indent=" " * (width + 2))

    return "\n".join("%*s: %s" % (width, field, val)
                     for (field, val) in pkg.iteritems())


def explode_slashes(func):
    """Explode slashes in args."""

    @wraps(func)
    def __inner__(*args, **kwargs):
        new_args = []
        for arg in args:
            if isinstance(arg, str):
                new_args.extend(arg.split("/"))
            else:
                new_args.append(arg)

        return func(*new_args, **kwargs)

    return __inner__


def get_commands():
    """Return a list of commands and their descriptions."""
    out = ["%prog [OPTIONS] COMMAND [ARGS]", "", "Commands:"]

    width = max(imap(len, (name[4:] for name in globals()
                           if name.startswith('cmd_'))))

    for name in globals():
        item = globals()[name]
        if name.startswith('cmd_') and callable(item):
            try:
                doc = item.__doc__.split("\n")[0]
            except AttributeError:
                doc = ""

            out.append("  %*s - %s" % (width, name[4:], doc))

    return "\n".join(out)


def get_parser():
    """Return an optionparser instance."""
    parser = OptionParser(get_commands())
    parser.add_option("-a", "--api", help="Base URL of the Repoman API.",
                      default=API_URL)
    parser.add_option("-d", "--debug", action="store_true",
                      help="Debug reqests & responses.")
    return parser


def request_internal(endpoint="", sub="repository", **kwargs):
    """Perform a request."""
    return Http().request(
        "%s/%s/%s" % (API_URL, sub, endpoint), **kwargs)


def request(endpoint="", sub="repository", **kwargs):
    """Perform a request."""
    (response, content) = request_internal(endpoint, sub, **kwargs)

    if response.status >= 500:
        raise Exception(content)

    try:
        return json.loads(content)
    except json.decoder.JSONDecodeError:
        return content or ""


def cmd_help(cmd=None):
    """Show command help."""
    if not cmd:
        return get_commands()
    return dedent(globals()['cmd_%s' % cmd].__doc__)


def _parse_changes(contents):
    """Return a tuple of (source_pkg, (changed_files)) from a .changes file."""
    return (
        contents.split("Source:")[1].strip().split("\n")[0],
        tuple(line.split(" ")[-1] for line in
              takewhile(lambda line: line.startswith(" "),
                        (contents.split("Files:")[1].split("\n"))[1:])))


def create_pack(changefile):
    """Return a tuple of (filename, StringIO)."""
    output = StringIO()

    change_dir = os.path.dirname(changefile) or "."
    with open(changefile, 'r') as change:
        (source_pkg, pkg_files) = _parse_changes(change.read())

    dsc_file = [file_ for file_ in pkg_files if file_.endswith(".dsc")]
    if dsc_file:
        with open("%s/%s" % (change_dir, dsc_file[0]), 'r') as dscfile:
            pkg_files += _parse_changes(dscfile.read())[1]

    tarball = tarfile.open("%s.tar.gz" % source_pkg, 'w:gz',
                           fileobj=output)

    base_dir = os.path.dirname(changefile) or "."
    tarball.add(changefile, os.path.basename(changefile))
    for pkg_file in set(pkg_files):
        tarball.add("%s/%s" % (base_dir, pkg_file), pkg_file)


    tarball.close()

    return (tarball.name, output)


def cmd_pack(*changefiles):
    """Create a packfile for uploading.

    pack FILE1 [FILE2 ... FILEN]
    """
    for changefile in changefiles:
        (name, contents) = create_pack(changefile)
        with open(name, 'w') as pack:
            pack.write(contents.getvalue())


def cmd_upload(dist, *pack_files):
    """Upload a package to the repo.

    upload DISTRIBUTION FILE1 [FILE2 ... FILEN]
    """

    if not pack_files:
        raise ArgumentError("No packfiles specified.")

    buf = ""
    for file_ in pack_files:
        print file_
        sys.stdout.flush()
        if file_.endswith(".changes"):
            (file_, pack) = create_pack(file_)
        else:
            pack = open(file_, 'r')

        print "Uploading %s" % file_
        try:
            (data, headers) = multipart_encode(
                (MultipartParam('package', filename=file_, fileobj=pack),))

            output = request(
                dist, method="POST", body="".join(data),
                headers=dict((key, str(val))
                             for (key, val) in headers.iteritems()))

            if isinstance(output, str):
                buf += "While uploading %s: %s" % (file_, output)
                continue

            try:
                buf += "\n\n".join(format_dict(pkg[0]) for pkg in output)
            except IndexError:
                buf += "While uploading %s: %s" % (file_, output)
                continue
        finally:
            pack.close()

    return buf


@explode_slashes
def cmd_promote(dist, package, *dest_dists):
    """Promote a package to another distribution.

    promote SOURCE_DIST/PACKAGE DEST_DIST [DEST_DIST2...DEST_DISTN]
    """
    for dest in dest_dists:
        request("%s/%s/copy?dstdist=%s" % (dist, package, dest),
                method="POST")
    return ""


@explode_slashes
def cmd_show(*path):
    """List known distributions or packages.

    List available distributions:
    show

    List packages in DISTRIBUTION:
    show DISTRIBUTION

    Show package details:
    show DISTRIBUTION/PACKAGE
    """
    output = request("/".join(path))
    if len(path) < 2:
        return "\n".join(sorted(output))

    return "\n\n".join(format_dict(pkg) for pkg in output)


@explode_slashes
def cmd_rm(dist, pkg):
    """Remove a package from a distribution.

    rm DIST/PACKAGE
    """
    request("%s/%s" % (dist, pkg), method="DELETE")


def _build(path, ref="origin/master"):
    """Perform a build."""
    return request(
        path, sub="buildbot", method="POST", body=urlencode({'ref': ref}),
        headers={'Content-Type': 'application/x-www-form-urlencoded'})


def _wait(build_id, poll_interval=1):
    """Wait until a build is complete."""
    resp = "not done"
    while "not done" in resp:
        time.sleep(poll_interval)
        resp = request("status/%s" % build_id, sub="buildbot")
        print ".",
        sys.stdout.flush()


def cmd_build(path, ref="origin/master"):
    """Build a package synchronously.

    This command works the same as build_async, except it doesn't
    return until the build is complete.
    """

    build_id = _build(path, ref)
    print "Building %s:%s, ID %s" % (path, ref, build_id)
    _wait(build_id)


def cmd_build_async(path, ref="origin/master"):
    """Build a package asynchronously.

    This will print a build identifier and return immediately; the
    package will build in the background.

    build REPO_PATH [REF]

    Example:

    build github.com/synack/repoman refs/tags/release-1.4.6-1
    """
    build_id = request(
        path, sub="buildbot", method="POST", body=urlencode({'ref': ref}),
        headers={'Content-Type': 'application/x-www-form-urlencoded'})
    return "Building %s:%s, ID %s" % (path, ref, build_id)


def cmd_status(build_id):
    """Return status of a build.

    status BUILD_ID
    """
    return request("status/%s" % build_id, sub="buildbot")


def cmd_wait(build_id):
    """Block until a build is complete.

    wait BUILD_ID
    """
    _wait(build_id)


def cmd_get(build_id):
    """Get the result of a build.

    get BUILD_ID
    """
    (resp, content) = request_internal("tarball/%s" % build_id, sub="buildbot")
    if resp.status != 200:
        return content

    with open('%s.tar' % build_id, 'w') as tarball:
        tarball.write(content)


def cmd_refs(repo):
    """Show refs we can build in a repo.

    refs github/synack/repoman
    """

    return "\n".join("%s %s" % tuple(pair)
                     for pair in request(repo, sub="buildbot"))


def cmd_policy(package):
    """Return available versions of a package in all dists.

    policy PACKAGE
    """
    dists = request()

    out = []
    width = max(imap(len, dists))
    for dist in sorted(dists):
        try:
            for version in request("%s/%s" % (dist, package)):
                out.append("%*s: %s (%s)" % (width, dist, version['Version'],
                                             version['Architecture']))
        except:
            pass
    return "\n".join(out)


def main():
    """The main entrypoint for the repoman CLI."""
    parser = get_parser()

    (opts, args) = parser.parse_args()

    if not args:
        parser.print_help()
        sys.exit(-1)

    globals()['API_URL'] = opts.api

    if opts.debug:
        logging.basicConfig(level=logging.DEBUG)

    func = 'cmd_%s' % args[0]
    if func not in globals():
        print "No such command: %s" % args[0]
        sys.exit(-1)

    try:
        output = globals()[func](*args[1:])

        if output:
            print output
    except (TypeError, ArgumentError), ex:
        print "Error: %s\n" % ex
        print cmd_help(args[0])
    except ValueError, ex:
        print ex
        if ex.args and 'argument' in ex.args[0]:
            print "Invalid argument:"
            print cmd_help(args[0])
        else:
            raise

########NEW FILE########
__FILENAME__ = common
# -*- coding: utf-8 -*-
#
# © 2010 SimpleGeo, Inc. All rights reserved.
# Author: Ian Eure <ian@simplegeo.com>
#

import wsgiref.simple_server as wsgi_server
from repoman.config import conf
import os.path
from webob import Response

class RequestHandler(object):
    def __init__(self, app, request):
        self.app = app
        self.request = request


class StaticHandler(RequestHandler):
    def get(self, path):
        if path.strip('/') == '':
            path = 'index.html'
        root = conf('server.static_path')
        path = os.path.join(root, path)
        if not path.startswith(root):
            return Response(status=400, body='400 Bad Request')
        else:
            return Response(status=200, body=file(path, 'rb').read())


class WSGIRequestHandler(wsgi_server.WSGIRequestHandler):

    def address_string(self):
        return self.client_address[0]

########NEW FILE########
__FILENAME__ = config
import logging
import logging.config

import os.path
import sys

try:
    import json
except ImportError:
    import simplejson as json

config = None

def set_log_conf(logging_conf):
    logging.config.fileConfig(logging_conf)

def set_web_conf(web_conf):
    """"""
    global config  # lulz
    if os.path.exists(web_conf):
        config = json.load(file(web_conf, 'r'))

    if not config:
        logging.critical('Unable to load config file. Exiting.')
        sys.exit(0)

def conf(key):
    if config is None:
        logging.critical('Config not loaded. Exiting.')
        sys.exit(0)

    obj = config
    for k in key.split('.'):
        obj = obj[k]
    return obj

########NEW FILE########
__FILENAME__ = gnupg
""" A wrapper for the 'gpg' command::

Portions of this module are derived from A.M. Kuchling's well-designed
GPG.py, using Richard Jones' updated version 1.3, which can be found
in the pycrypto CVS repository on Sourceforge:

http://pycrypto.cvs.sourceforge.net/viewvc/pycrypto/gpg/GPG.py

This module is *not* forward-compatible with amk's; some of the
old interface has changed.  For instance, since I've added decrypt
functionality, I elected to initialize with a 'gnupghome' argument
instead of 'keyring', so that gpg can find both the public and secret
keyrings.  I've also altered some of the returned objects in order for
the caller to not have to know as much about the internals of the
result classes.

While the rest of ISconf is released under the GPL, I am releasing
this single file under the same terms that A.M. Kuchling used for
pycrypto.

Steve Traugott, stevegt@terraluna.org
Thu Jun 23 21:27:20 PDT 2005

This version of the module has been modified from Steve Traugott's version
(see http://trac.t7a.org/isconf/browser/trunk/lib/python/isconf/GPG.py) by
Vinay Sajip to make use of the subprocess module (Steve's version uses os.fork()
and so does not work on Windows). Renamed to gnupg.py to avoid confusion with
the previous versions.

Modifications Copyright (C) 2008-2009 Vinay Sajip. All rights reserved.

A unittest harness (test_gnupg.py) has also been added.
"""
import locale

__author__ = "Vinay Sajip"
__date__  = "$07-Aug-2009 10:36:12$"

try:
    from io import StringIO
    from io import TextIOWrapper
    from io import BufferedReader
    from io import BufferedWriter
except ImportError:
    from cStringIO import StringIO
    class BufferedReader: pass
    class BufferedWriter: pass

import locale
import logging
import os
import socket
from subprocess import Popen
from subprocess import PIPE
import threading

try:
    import logging.NullHandler as NullHandler
except:
    class NullHandler(logging.Handler):
        def emit(self, record):
            pass

logger = logging.getLogger(__name__)
if not logger.handlers:
    logger.addHandler(NullHandler())

def _copy_data(instream, outstream):
    # Copy one stream to another
    while True:
        data = instream.read(1024)
        if data == "":
            break
        logger.debug("sending chunk: %r" % data)
        outstream.write(data)
    outstream.close()

def _write_passphrase(stream, passphrase):
    stream.write(passphrase + "\n")
    logger.debug("Wrote passphrase")

def _is_sequence(instance):
    return isinstance(instance,list) or isinstance(instance,tuple)

class GPG(object):
    "Encapsulate access to the gpg executable"
    def __init__(self, gpgbinary='gpg', gnupghome=None, verbose=False):
        """Initialize a GPG process wrapper.  Options are:

        gpgbinary -- full pathname for GPG binary.

        gnupghome -- full pathname to where we can find the public and
        private keyrings.  Default is whatever gpg defaults to.

        >>> gpg = GPG(gnupghome="/tmp/pygpgtest")

        """
        self.gpgbinary = gpgbinary
        self.gnupghome = gnupghome
        self.verbose = verbose
        if gnupghome and not os.path.isdir(self.gnupghome):
            os.makedirs(self.gnupghome,0x1C0)
        p = self._open_subprocess(["--version"])
        result = Verify() # any result will do for this
        self._collect_output(p, result)
        if p.returncode != 0:
            raise ValueError("Error invoking gpg: %s: %s" % (p.returncode,
                                                             result.stderr))

    def _open_subprocess(self, args, passphrase=False):
        # Internal method: open a pipe to a GPG subprocess and return
        # the file objects for communicating with it.
        cmd = [self.gpgbinary, '--status-fd 2 --no-tty']
        if self.gnupghome:
            cmd.append('--homedir "%s" ' % self.gnupghome)
        if passphrase:
            cmd.append('--passphrase-fd 0')

        cmd.extend(args)
        cmd = ' '.join(cmd)
        if self.verbose:
            print(cmd)
        logger.debug("%s", cmd)
        return Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=PIPE)

    def _read_response(self, stream, result):
        # Internal method: reads all the output from GPG, taking notice
        # only of lines that begin with the magic [GNUPG:] prefix.
        #
        # Calls methods on the response object for each valid token found,
        # with the arg being the remainder of the status line.
        lines = []
        while True:
            line = stream.readline()
            lines.append(line)
            if self.verbose:
                print(line)
            logger.debug("%s", line.rstrip())
            if line == "": break
            line = line.rstrip()
            if line[0:9] == '[GNUPG:] ':
                # Chop off the prefix
                line = line[9:]
                L = line.split(None, 1)
                keyword = L[0]
                if len(L) > 1:
                    value = L[1]
                else:
                    value = ""
                result.handle_status(keyword, value)
        result.stderr = ''.join(lines)

    def _read_data(self, stream, result):
        # Read the contents of the file from GPG's stdout
        chunks = []
        while True:
            data = stream.read(1024)
            if data == "":
                break
            logger.debug("chunk: %s" % data)
            chunks.append(data)
        result.data = ''.join(chunks)

    def _collect_output(self, process, result):
        """
        Drain the subprocesses output streams, writing the collected output
        to the result.
        """
        stderr = process.stderr
        if isinstance(stderr, BufferedReader):
            stderr = TextIOWrapper(stderr)
        rr = threading.Thread(target=self._read_response, args=(stderr, result))
        rr.setDaemon(True)
        rr.start()

        stdout = process.stdout
        if isinstance(stdout, BufferedReader):
            stdout = TextIOWrapper(stdout)
        dr = threading.Thread(target=self._read_data, args=(stdout, result))
        dr.setDaemon(True)
        dr.start()

        dr.join()
        rr.join()
        process.wait()

    def _handle_io(self, args, file, result, passphrase=None):
        "Handle a call to GPG - pass input data, collect output data"
        # Handle a basic data call - pass data to GPG, handle the output
        # including status information. Garbage In, Garbage Out :)
        p = self._open_subprocess(args, passphrase is not None)
        stdin = p.stdin
        if isinstance(stdin, BufferedWriter):
            stdin = TextIOWrapper(stdin, locale.getpreferredencoding())
        if passphrase:
            _write_passphrase(stdin, passphrase)
        _copy_data(file, stdin)
        self._collect_output(p, result)
        return result

    #
    # SIGNATURE METHODS
    #
    def sign(self, message, **kwargs):
        """sign message"""
        return self.sign_file(StringIO(message), **kwargs)

    def sign_file(self, file, keyid=None, passphrase=None, outputfile=None):
        """sign file"""
        args = []
        if keyid:
            args.append("-u %s" % keyid)
        args.append("-abs")
        if outputfile:
            args.append('-o %s' % outputfile)

        result = Sign()
        #We could use _handle_io here except for the fact that if the
        #passphrase is bad, gpg bails and you can't write the message.
        #self._handle_io(args, StringIO(message), result, passphrase=passphrase)
        p = self._open_subprocess(args, passphrase is not None)
        try:
            stdin = p.stdin
            if isinstance(stdin, BufferedWriter):
                stdin = TextIOWrapper(stdin)
            if passphrase:
                _write_passphrase(stdin, passphrase)
            _copy_data(file, stdin)
        except IOError:
            logging.exception("error writing message")
        self._collect_output(p, result)
        return result

    def verify(self, data):
        """Verify the signature on the contents of the string 'data'

        >>> gpg = GPG(gnupghome="/tmp/pygpgtest")
        >>> input = gpg.gen_key_input(Passphrase='foo')
        >>> key = gpg.gen_key(input)
        >>> assert key
        >>> sig = gpg.sign('hello',keyid=key.fingerprint,passphrase='bar')
        >>> assert not sig
        >>> sig = gpg.sign('hello',keyid=key.fingerprint,passphrase='foo')
        >>> assert sig
        >>> verify = gpg.verify(str(sig))
        >>> assert verify

        """
        return self.verify_file(StringIO(data))

    def verify_file(self, file):
        "Verify the signature on the contents of the file-like object 'file'"
        result = Verify()
        self._handle_io([], file, result)
        return result

    #
    # KEY MANAGEMENT
    #

    def import_keys(self, key_data):
        """ import the key_data into our keyring

        >>> import shutil
        >>> shutil.rmtree("/tmp/pygpgtest")
        >>> gpg = GPG(gnupghome="/tmp/pygpgtest")
        >>> input = gpg.gen_key_input()
        >>> result = gpg.gen_key(input)
        >>> print1 = result.fingerprint
        >>> result = gpg.gen_key(input)
        >>> print2 = result.fingerprint
        >>> pubkey1 = gpg.export_keys(print1)
        >>> seckey1 = gpg.export_keys(print1,secret=True)
        >>> seckeys = gpg.list_keys(secret=True)
        >>> pubkeys = gpg.list_keys()
        >>> assert print1 in seckeys.fingerprints
        >>> assert print1 in pubkeys.fingerprints
        >>> str(gpg.delete_keys(print1))
        'Must delete secret key first'
        >>> str(gpg.delete_keys(print1,secret=True))
        'ok'
        >>> str(gpg.delete_keys(print1))
        'ok'
        >>> str(gpg.delete_keys("nosuchkey"))
        'No such key'
        >>> seckeys = gpg.list_keys(secret=True)
        >>> pubkeys = gpg.list_keys()
        >>> assert not print1 in seckeys.fingerprints
        >>> assert not print1 in pubkeys.fingerprints
        >>> result = gpg.import_keys('foo')
        >>> assert not result
        >>> result = gpg.import_keys(pubkey1)
        >>> pubkeys = gpg.list_keys()
        >>> seckeys = gpg.list_keys(secret=True)
        >>> assert not print1 in seckeys.fingerprints
        >>> assert print1 in pubkeys.fingerprints
        >>> result = gpg.import_keys(seckey1)
        >>> assert result
        >>> seckeys = gpg.list_keys(secret=True)
        >>> pubkeys = gpg.list_keys()
        >>> assert print1 in seckeys.fingerprints
        >>> assert print1 in pubkeys.fingerprints
        >>> assert print2 in pubkeys.fingerprints

        """
        result = ImportResult()
        self._handle_io(['--import'], StringIO(key_data), result)
        return result

    def delete_keys(self, fingerprints, secret=False):
        which='key'
        if secret:
            which='secret-key'
        if _is_sequence(fingerprints):
            fingerprints = ' '.join(fingerprints)
        args = ["--batch --delete-%s %s" % (which, fingerprints)]
        result = DeleteResult()
        p = self._open_subprocess(args)
        self._collect_output(p, result)
        return result

    def export_keys(self, keyids, secret=False):
        "export the indicated keys. 'keyid' is anything gpg accepts"
        which=''
        if secret:
            which='-secret-key'
        if _is_sequence(keyids):
            keyids = ' '.join(keyids)
        args = ["--armor --export%s %s" % (which, keyids)]
        p = self._open_subprocess(args)
        # gpg --export produces no status-fd output; stdout will be
        # empty in case of failure
        #stdout, stderr = p.communicate()
        result = DeleteResult() # any result will do
        self._collect_output(p, result)
        return result.data

    def list_keys(self, secret=False):
        """ list the keys currently in the keyring

        >>> import shutil
        >>> shutil.rmtree("/tmp/pygpgtest")
        >>> gpg = GPG(gnupghome="/tmp/pygpgtest")
        >>> input = gpg.gen_key_input()
        >>> result = gpg.gen_key(input)
        >>> print1 = result.fingerprint
        >>> result = gpg.gen_key(input)
        >>> print2 = result.fingerprint
        >>> pubkeys = gpg.list_keys()
        >>> assert print1 in pubkeys.fingerprints
        >>> assert print2 in pubkeys.fingerprints

        """

        which='keys'
        if secret:
            which='secret-keys'
        args = "--list-%s --fixed-list-mode --fingerprint --with-colons" % (which)
        args = [args]
        p = self._open_subprocess(args)

        # there might be some status thingumy here I should handle... (amk)
        # ...nope, unless you care about expired sigs or keys (stevegt)

        # Get the response information
        result = ListKeys()
        self._collect_output(p, result)
        stdout = StringIO(result.data)
        valid_keywords = 'pub uid sec fpr'.split()
        while True:
            line = stdout.readline()
            if self.verbose:
                print(line)
            logger.debug("%s", line.rstrip())
            if not line:
                break
            L = line.strip().split(':')
            if not L:
                continue
            keyword = L[0]
            if keyword in valid_keywords:
                getattr(result, keyword)(L)
        return result

    def gen_key(self, input):
        """Generate a key; you might use gen_key_input() to create the
        control input.

        >>> gpg = GPG(gnupghome="/tmp/pygpgtest")
        >>> input = gpg.gen_key_input()
        >>> result = gpg.gen_key(input)
        >>> assert result
        >>> result = gpg.gen_key('foo')
        >>> assert not result

        """
        args = ["--gen-key --batch"]
        result = GenKey()
        file = StringIO(input)
        self._handle_io(args, file, result)
        return result

    def gen_key_input(self, **kwargs):
        """
        Generate --gen-key input per gpg doc/DETAILS
        """
        parms = {}
        for key, val in list(kwargs.items()):
            key = key.replace('_','-').title()
            parms[key] = val
        parms.setdefault('Key-Type','RSA')
        parms.setdefault('Key-Length',1024)
        parms.setdefault('Name-Real', "Autogenerated Key")
        parms.setdefault('Name-Comment', "Generated by gnupg.py")
        try:
            logname = os.environ['LOGNAME']
        except KeyError:
            logname = os.environ['USERNAME']
        hostname = socket.gethostname()
        parms.setdefault('Name-Email', "%s@%s" % (logname.replace(' ', '_'),
                                                  hostname))
        out = "Key-Type: %s\n" % parms.pop('Key-Type')
        for key, val in list(parms.items()):
            out += "%s: %s\n" % (key, val)
        out += "%commit\n"
        return out

        # Key-Type: RSA
        # Key-Length: 1024
        # Name-Real: ISdlink Server on %s
        # Name-Comment: Created by %s
        # Name-Email: isdlink@%s
        # Expire-Date: 0
        # %commit
        #
        #
        # Key-Type: DSA
        # Key-Length: 1024
        # Subkey-Type: ELG-E
        # Subkey-Length: 1024
        # Name-Real: Joe Tester
        # Name-Comment: with stupid passphrase
        # Name-Email: joe@foo.bar
        # Expire-Date: 0
        # Passphrase: abc
        # %pubring foo.pub
        # %secring foo.sec
        # %commit

    #
    # ENCRYPTION
    #
    def encrypt_file(self, file, recipients, sign=None,
            always_trust=False, passphrase=None):
        "Encrypt the message read from the file-like object 'file'"
        args = ['--encrypt --armor']
        if not _is_sequence(recipients):
            recipients = (recipients,)
        for recipient in recipients:
            args.append('--recipient %s' % recipient)
        if sign:
            args.append("--sign --default-key %s" % sign)
        if always_trust:
            args.append("--always-trust")
        result = Crypt()
        self._handle_io(args, file, result, passphrase=passphrase)
        return result

    def encrypt(self, data, recipients, **kwargs):
        """Encrypt the message contained in the string 'data'

        >>> import shutil
        >>> if os.path.exists("/tmp/pygpgtest"):
        ...     shutil.rmtree("/tmp/pygpgtest")
        >>> gpg = GPG(gnupghome="/tmp/pygpgtest")
        >>> input = gpg.gen_key_input(passphrase='foo')
        >>> result = gpg.gen_key(input)
        >>> print1 = result.fingerprint
        >>> input = gpg.gen_key_input()
        >>> result = gpg.gen_key(input)
        >>> print2 = result.fingerprint
        >>> result = gpg.encrypt("hello",print2)
        >>> message = str(result)
        >>> assert message != 'hello'
        >>> result = gpg.decrypt(message)
        >>> assert result
        >>> str(result)
        'hello'
        >>> result = gpg.encrypt("hello again",print1)
        >>> message = str(result)
        >>> result = gpg.decrypt(message)
        >>> result.status
        'need passphrase'
        >>> result = gpg.decrypt(message,passphrase='bar')
        >>> result.status
        'decryption failed'
        >>> assert not result
        >>> result = gpg.decrypt(message,passphrase='foo')
        >>> result.status
        'decryption ok'
        >>> str(result)
        'hello again'
        >>> result = gpg.encrypt("signed hello",print2,sign=print1)
        >>> result.status
        'need passphrase'
        >>> result = gpg.encrypt("signed hello",print2,sign=print1,passphrase='foo')
        >>> result.status
        'encryption ok'
        >>> message = str(result)
        >>> result = gpg.decrypt(message)
        >>> result.status
        'decryption ok'
        >>> assert result.fingerprint == print1

        """
        return self.encrypt_file(StringIO(data), recipients, **kwargs)

    def decrypt(self, message, **kwargs):
        return self.decrypt_file(StringIO(message), **kwargs)

    def decrypt_file(self, file, always_trust=False, passphrase=None):
        args = ["--decrypt"]
        if always_trust:
            args.append("--always-trust")
        result = Crypt()
        self._handle_io(args, file, result, passphrase)
        return result

class Verify(object):
    "Handle status messages for --verify"

    def __init__(self):
        self.valid = False
        self.fingerprint = self.creation_date = self.timestamp = None
        self.signature_id = self.key_id = None
        self.username = None

    def __nonzero__(self):
        return self.valid

    __bool__ = __nonzero__

    def handle_status(self, key, value):
        if key in ("TRUST_UNDEFINED", "TRUST_NEVER", "TRUST_MARGINAL",
                   "TRUST_FULLY", "TRUST_ULTIMATE"):
            pass
        elif key in ("PLAINTEXT", "PLAINTEXT_LENGTH"):
            pass
        elif key == "BADSIG":
            self.valid = False
            self.key_id, self.username = value.split(None, 1)
        elif key == "GOODSIG":
            self.valid = True
            self.key_id, self.username = value.split(None, 1)
        elif key == "VALIDSIG":
            (self.fingerprint,
             self.creation_date,
             self.sig_timestamp,
             self.expire_timestamp) = value.split()[:4]
        elif key == "SIG_ID":
            (self.signature_id,
             self.creation_date, self.timestamp) = value.split()
        else:
            raise ValueError("Unknown status message: %r" % key)

class ImportResult(object):
    "Handle status messages for --import"

    counts = '''count no_user_id imported imported_rsa unchanged
            n_uids n_subk n_sigs n_revoc sec_read sec_imported
            sec_dups not_imported'''.split()
    def __init__(self):
        self.imported = []
        self.results = []
        self.fingerprints = []
        for result in self.counts:
            setattr(self, result, None)

    def __nonzero__(self):
        if self.not_imported: return False
        if not self.fingerprints: return False
        return True

    __bool__ = __nonzero__

    ok_reason = {
        '0': 'Not actually changed',
        '1': 'Entirely new key',
        '2': 'New user IDs',
        '4': 'New signatures',
        '8': 'New subkeys',
        '16': 'Contains private key',
    }

    problem_reason = {
        '0': 'No specific reason given',
        '1': 'Invalid Certificate',
        '2': 'Issuer Certificate missing',
        '3': 'Certificate Chain too long',
        '4': 'Error storing certificate',
    }

    def handle_status(self, key, value):
        if key == "IMPORTED":
            # this duplicates info we already see in import_ok & import_problem
            pass
        elif key == "NODATA":
            self.results.append({'fingerprint': None,
                'problem': '0', 'text': 'No valid data found'})
        elif key == "IMPORT_OK":
            reason, fingerprint = value.split()
            reasons = []
            for code, text in list(self.ok_reason.items()):
                if int(reason) | int(code) == int(reason):
                    reasons.append(text)
            reasontext = '\n'.join(reasons) + "\n"
            self.results.append({'fingerprint': fingerprint,
                'ok': reason, 'text': reasontext})
            self.fingerprints.append(fingerprint)
        elif key == "IMPORT_PROBLEM":
            try:
                reason, fingerprint = value.split()
            except:
                reason = value
                fingerprint = '<unknown>'
            self.results.append({'fingerprint': fingerprint,
                'problem': reason, 'text': self.problem_reason[reason]})
        elif key == "IMPORT_RES":
            import_res = value.split()
            for i in range(len(self.counts)):
                setattr(self, self.counts[i], int(import_res[i]))
        else:
            raise ValueError("Unknown status message: %r" % key)

    def summary(self):
        l = []
        l.append('%d imported'%self.imported)
        if self.not_imported:
            l.append('%d not imported'%self.not_imported)
        return ', '.join(l)

class ListKeys(list):
    ''' Handle status messages for --list-keys.

        Handle pub and uid (relating the latter to the former).

        Don't care about (info from src/DETAILS):

        crt = X.509 certificate
        crs = X.509 certificate and private key available
        sub = subkey (secondary key)
        ssb = secret subkey (secondary key)
        uat = user attribute (same as user id except for field 10).
        sig = signature
        rev = revocation signature
        pkd = public key data (special field format, see below)
        grp = reserved for gpgsm
        rvk = revocation key
    '''
    def __init__(self):
        self.curkey = None
        self.fingerprints = []

    def key(self, args):
        vars = ("""
            type trust length algo keyid date expires dummy ownertrust uid
        """).split()
        self.curkey = {}
        for i in range(len(vars)):
            self.curkey[vars[i]] = args[i]
        self.curkey['uids'] = [self.curkey['uid']]
        del self.curkey['uid']
        self.append(self.curkey)

    pub = sec = key

    def fpr(self, args):
        self.curkey['fingerprint'] = args[9]
        self.fingerprints.append(args[9])

    def uid(self, args):
        self.curkey['uids'].append(args[9])

    def handle_status(self, key, value):
        pass

class Crypt(Verify):
    "Handle status messages for --encrypt and --decrypt"
    def __init__(self):
        Verify.__init__(self)
        self.data = ''
        self.ok = False
        self.status = ''

    def __nonzero__(self):
        if self.ok: return True
        return False

    __bool__ = __nonzero__

    def __str__(self):
        return self.data

    def handle_status(self, key, value):
        if key in ("ENC_TO", "USERID_HINT", "GOODMDC", "END_DECRYPTION",
                   "BEGIN_SIGNING", "NO_SECKEY"):
            pass
        elif key in ("NEED_PASSPHRASE", "BAD_PASSPHRASE", "GOOD_PASSPHRASE",
                     "DECRYPTION_FAILED"):
            self.status = key.replace("_", " ").lower()
        elif key == "BEGIN_DECRYPTION":
            self.status = 'decryption incomplete'
        elif key == "BEGIN_ENCRYPTION":
            self.status = 'encryption incomplete'
        elif key == "DECRYPTION_OKAY":
            self.status = 'decryption ok'
            self.ok = True
        elif key == "END_ENCRYPTION":
            self.status = 'encryption ok'
            self.ok = True
        elif key == "INV_RECP":
            self.status = 'invalid recipient'
        elif key == "KEYEXPIRED":
            self.status = 'key expired'
        elif key == "SIG_CREATED":
            self.status = 'sig created'
        elif key == "SIGEXPIRED":
            self.status = 'sig expired'
        else:
            Verify.handle_status(self, key, value)

class GenKey(object):
    "Handle status messages for --gen-key"
    def __init__(self):
        self.type = None
        self.fingerprint = None

    def __nonzero__(self):
        if self.fingerprint: return True
        return False

    __bool__ = __nonzero__

    def __str__(self):
        return self.fingerprint or ''

    def handle_status(self, key, value):
        if key in ("PROGRESS", "GOOD_PASSPHRASE", "NODATA"):
            pass
        elif key == "KEY_CREATED":
            (self.type,self.fingerprint) = value.split()
        else:
            raise ValueError("Unknown status message: %r" % key)

class DeleteResult(object):
    "Handle status messages for --delete-key and --delete-secret-key"
    def __init__(self):
        self.status = 'ok'

    def __str__(self):
        return self.status

    problem_reason = {
        '1': 'No such key',
        '2': 'Must delete secret key first',
        '3': 'Ambigious specification',
    }

    def handle_status(self, key, value):
        if key == "DELETE_PROBLEM":
            self.status = self.problem_reason.get(value,
                                                  "Unknown error: %r" % value)
        else:
            raise ValueError("Unknown status message: %r" % key)

class Sign(object):
    "Handle status messages for --sign"
    def __init__(self):
        self.type = None
        self.fingerprint = None

    def __nonzero__(self):
        if self.fingerprint: return True
        return False

    __bool__ = __nonzero__

    def __str__(self):
        return self.data or ''
    
    def handle_status(self, key, value):
        if key in ("USERID_HINT", "NEED_PASSPHRASE", "BAD_PASSPHRASE",
                   "GOOD_PASSPHRASE", "BEGIN_SIGNING"):
            pass
        elif key == "SIG_CREATED":
            (self.type,
             algo, hashalgo, cls,
             self.timestamp, self.fingerprint
             ) = value.split()
        else:
            raise ValueError("Unknown status message: %r" % key)

########NEW FILE########
__FILENAME__ = repository
from simplejson import dumps, loads
from gnupg import GPG
from webob import Response
from common import RequestHandler

from subprocess import Popen, PIPE
import logging
import os.path
import os

import tarfile
import uuid

from config import conf

try:
    import json
except ImportError:
    import simplejson as json

def unique(lst):
    s = {}
    [s.__setitem__(repr(p), p) for p in lst]
    return s.values()

class Repository(object):
    def __init__(self, path):
        self.path = path

    def _reprepro(self, args):
        os.chdir(self.path)
        p = Popen(['/usr/bin/reprepro', '-Vb.'] + args.split(' '), stdout=PIPE, stderr=PIPE)
        return (p.communicate(), p.returncode)

    def get_dists(self):
        results = []
        distdir = os.path.join(self.path, 'dists')
        for dist in os.listdir(distdir):
            distpath = os.path.join(distdir, dist)
            if os.path.islink(distpath) or not os.path.isdir(distpath):
                continue
            results.append(dist)
        return results

    def create_dist(self, distinfo):
        if distinfo['Codename'] in self.get_dists():
            raise ValueError('Cannot create distribution %s, it already exists' % label)

        dist = ['%s: %s' % (k, v) for k, v in distinfo.items() if k and v]
        dist.insert(0, '')
        dist = '\n'.join(dist)

        fd = file(os.path.join(self.path, 'conf/distributions'), 'a')
        fd.write(dist)
        fd.close()

        self._reprepro('export')

    def get_packages(self, dist):
        # This code is evil and ugly... Don't stare at it for too long
        results = {}
        distdir = os.path.join(self.path, 'dists/%s' % dist)
        for dirpath, dirnames, filenames in os.walk(distdir):
            for name in filenames:
                if name != 'Packages': continue
                path = os.path.join(dirpath, name)
                packages = file(path, 'r').read()
                packages = packages.split('\n\n')
                for pkg in packages:
                    fields = []
                    for field in pkg.split('\n'):
                        if not field: continue
                        if field[0].isalpha():
                            fields.append(field.split(': ', 1))
                        else:
                            fields[-1][1] += field
                    if not fields: continue
                    pkg = dict(fields)
                    pkgname = pkg['Package']
                    if not pkgname in results:
                        results[pkgname] = []
                    results[pkgname].append(pkg)
        return results

    def get_package(self, dist, package):
        p = self.get_packages(dist)
        return unique(p.get(package, []))

    def sign(self, dist):
        self._reprepro('export %s' % dist)

        gpg = GPG(gnupghome=conf('repository.gpghome'))
        filename = os.path.join(self.path, 'dists/%s/Release' % dist)
        detach_file = filename + '.gpg'
        try:
            os.unlink(detach_file)
        except: pass
        result = gpg.sign_file(file(filename, 'r'), keyid=conf('repository.signkey'), outputfile=detach_file)

    def copy_package(self, srcdist, dstdist, package):
        self._reprepro('copy %s %s %s' % (dstdist, srcdist, package))
        self.sign(dstdist)

    def add_package(self, dist, changes):
        result = self._reprepro('-Pnormal --ignore=wrongdistribution include %s %s' % (dist, changes))
        self.sign(dist)
        return result

    def remove_package(self, dist, package):
        output, retcode = self._reprepro('remove %s %s' % (dist, package))
        self.sign(dist)
        return output[1]

class RepoHandler(RequestHandler):
    def get(self):
        repo = Repository(conf('repository.path'))
        return Response(body=dumps(repo.get_dists()))

    def post(self):
        repo = Repository(conf('repository.path'))
        dist = {
            'Version': '5.0',
            'Architectures': 'amd64 source any',
            'Components': 'main contrib non-free',
            'Description': 'Default package repository',
        }
        dist.update(json.loads(self.request.body))
        for field in ['Origin', 'Label', 'Suite', 'Codename']:
            if not field in dist:
                return Response(status=400, body='Required field %s is missing.' % field)
        repo.create_dist(dist)

class DistHandler(RequestHandler):
    def get(self, dist=None, action=None):
        repo = Repository(conf('repository.path'))
        return Response(body=dumps(repo.get_packages(dist).keys()))

    def post(self, dist):
        repo = Repository(conf('repository.path'))
        response = None

        basedir = '/tmp/repoman.upload/%s' % uuid.uuid4().hex
        os.makedirs(basedir)
        os.chdir(basedir)

        field = self.request.params['package']

        name = os.path.basename(field.filename)
        if not name.endswith('tar.gz') and not name.endswith('tar.bz2'):
            return Response(status=400, body='Packages must be uploaded as .tar.gz or tar.bz2 files containing .changes, .dsc, and .deb files')

        fd = file(name, 'wb')
        fd.write(field.value)
        fd.close()

        tf = tarfile.open(name, 'r|*')
        tf.extractall()
        changesfile = [x for x in os.listdir(basedir) if x.endswith('.changes')]
        if not changesfile:
            return Response(status=400, body='Tarball does not contain a .changes file')

        packages = []
        for changes in changesfile:
            changes = os.path.join(basedir, changes)
            stderr, stdout = repo.add_package(dist, changes)[0]
            if stdout:
                logging.debug('add_package: %s' % stdout)
            if stderr:
                logging.warning('add_package: %s' % stderr)
            for p in [x.split(': ', 1)[1].rstrip('\r\n').split(' ') for x in file(changes, 'r').readlines() if x.startswith('Binary: ')]:
                for bin in p:
                    pkg = repo.get_package(dist, bin)
                    packages.append(pkg)
        response = Response(status=200, body=dumps(packages))

        for dirpath, dirnames, filenames in os.walk(basedir):
            for filename in filenames:
                filename = os.path.join(dirpath, filename)
                os.remove(filename)
        os.rmdir(basedir)
        
        if not response:
            response = Response(status=500)
        return response

class PackageHandler(RequestHandler):
    def get(self, dist, package):
        repo = Repository(conf('repository.path'))

        if dist and package:
            pkg = repo.get_package(dist, package)
            if not pkg:
                return Response(status=404, body=dumps([]))

            return Response(status=200, body=dumps(pkg))

        if dist and not package:
            result = repo.get_packages(dist).keys()
            if not result:
                return Response(status=404, body=dumps([]))
            return Response(status=200, body=dumps(result))

        if not dist:
            result = repo.get_dists()
            if not result:
                return Response(status=404, body=dumps([]))
            return Response(status=200, body=dumps(result))

    def post(self, dist=None, package=None, action=None):
        repo = Repository(conf('repository.path'))
        if not dist or not package or not action:
            return Response(status=405)

        if action == 'copy':
            if not 'dstdist' in self.request.params:
                return Response(status=400, body='A required parameter, dstdist is missing')
            repo.copy_package(dist, self.request.params['dstdist'], package)
            return Response(status=200)

    def delete(self, dist=None, package=None, action=None):
        repo = Repository(conf('repository.path'))
        if action:
            return Response(status=405, body='You cannot delete an action')
        if not dist or not package:
            return Response(status=400, body='You must specify a dist and package to delete from it')

        result = repo.remove_package(dist, package)
        if result:
            return Response(status=404, body=result)
        return Response(status=200)

########NEW FILE########
__FILENAME__ = server
#!/usr/bin/env python

import sys
import daemon

from optparse import OptionParser

from repoman.config import conf, set_log_conf, set_web_conf
from repoman.wsgi import get_server
from repoman import repository
from repoman import buildbot


def get_context():
    context = {'working_directory': '.',
               'detach_process': False}
    if conf('server.daemonize'):
        log_file = open(conf('server.daemon_log'), 'w+')
        context.update(detach_process=True,
                       stdout=log_file,
                       stderr=log_file)
    else:
        context.update(files_preserve=[sys.stdout, sys.stderr],
                       stdout=sys.stdout,
                       stderr=sys.stderr)

    return daemon.DaemonContext(**context)

def main():
    parser = OptionParser()
    parser.add_option("-l", "--logging-config", help="Logging config file", default="/etc/repoman/logging.conf")
    parser.add_option("-w", "--web-config", help="Web config file", default="/etc/repoman/web.conf")
    (options, args) = parser.parse_args()
    set_log_conf(options.logging_config)
    set_web_conf(options.web_config)
    with get_context():
        get_server().serve_forever()



########NEW FILE########
__FILENAME__ = test_client
# -*- coding: utf-8 -*-
#
# © 2010 SimpleGeo, Inc. All rights reserved.
# Author: Ian Eure <ian@simplegeo.com>
#

"""Unit tests for the repoman client."""

import os
import repoman.client as client


def check_parsing(changefile, expected):
    """Verify that parsing succeds with problematic .changes files."""
    with open("%s/changefiles/%s" % (os.path.dirname(__file__), changefile),
                                     'r') as change:
        changes = change.read()
        parsed = client._parse_changes(changes)
        assert len(parsed) == 2
        assert set(parsed[1]) == set(expected), \
            "Incorrect result: %r" % \
            set(parsed[1]).symmetric_difference(set(expected))

        for file_ in parsed[1]:
            assert file_ in expected


def test_parsing():
    expected = ("puppet_0.25.5-sg1.dsc",
                "puppet_0.25.5.orig.tar.gz",
                "puppet_0.25.5-sg1.debian.tar.gz",
                "puppet_0.25.5-sg1_all.deb",
                "puppetmaster_0.25.5-sg1_all.deb",
                "puppet-common_0.25.5-sg1_all.deb",
                "vim-puppet_0.25.5-sg1_all.deb",
                "puppet-el_0.25.5-sg1_all.deb",
                "puppet-testsuite_0.25.5-sg1_all.deb")

    fixture_dir = os.path.dirname(__file__) + '/changefiles/'
    for change in (os.listdir(fixture_dir)):
        yield (check_parsing, change, expected)


def test_explode_slashes():
    unexploded = ['foo/bar', 'baz']
    expected = ('foo', 'bar', 'baz')
    func = lambda foo, bar, baz: (foo, bar, baz)
    exploded = client.explode_slashes(func)(*unexploded)
    assert exploded == expected, \
        "Expected %r, got %r" % (expected, exploded)


def test_bad_docs():
    """Make sure help works even if docblocks are missing."""
    client.cmd_fake = lambda: None
    help_str = client.get_commands()
    assert "fake" in help_str


def test_help_commands():
    """Make sure help with no args shows commands."""
    assert client.cmd_help() == client.get_commands()


def check_decorated_function_docs(name):
    assert getattr(getattr(client, 'cmd_%s' % name), '__doc__')


def test_decorated_function_docs():
    """Make sure decorated functions retain their documentation."""
    for func in ('rm', 'show', 'promote'):
        yield (check_decorated_function_docs, func)

########NEW FILE########
__FILENAME__ = wsgi
from webob import Request, Response
import httplib
import os.path
import re
from wsgiref.simple_server import make_server

from config import conf

import buildbot
import repository
from common import StaticHandler, WSGIRequestHandler


class Application(object):
    def __init__(self, extra_urls=None):
        extra_urls = extra_urls or []
        self.handlers = [(re.compile(pattern), handler)
                         for pattern, handler in DEFAULT_URLS + extra_urls]

    def __call__(self, environ, start_response):
        request = Request(environ)
        response = None

        for pattern, handler in self.handlers:
            match = pattern.match(request.path_info)
            if not match: continue
            handler = handler(self, request)
            if hasattr(handler, request.method.lower()):
                f = getattr(handler, request.method.lower())
                response = f(**match.groupdict())
            else:
                response = Response(status=501)
            break

        if not response:
            response = Response(status=404)

        return response(environ, start_response)


def get_server():
    return make_server(conf('server.bind_address'),
                         conf('server.bind_port'), Application(),
                         handler_class=WSGIRequestHandler)


DEFAULT_URLS = [
    ('^/repository/(?P<dist>[-\w]+)/(?P<package>[a-z0-9][a-z0-9+-.]+)/(?P<action>\w+)/*$',
     repository.PackageHandler),
    ('^/repository/(?P<dist>[-\w]+)/(?P<package>[a-z0-9][a-z0-9+-.]+)/*$',
     repository.PackageHandler),
    ('^/repository/(?P<dist>[-\w]+)/*$',
     repository.DistHandler),
    ('^/repository/*$',
     repository.RepoHandler),
    ('^/buildbot/status/(?P<buildid>[a-z0-9]{32})/*$',
     buildbot.StatusHandler),
    ('^/buildbot/tarball/(?P<buildid>[a-z0-9]{32})/*$',
     buildbot.TarballHandler),
    ('^/buildbot/(?P<gitpath>[a-z]+)/(?P<gitrepo>.+)/*$',
     buildbot.PackageHandler),
    ('^/buildbot/(?P<gitpath>[a-z]+)/*$',
     buildbot.RepoListHandler),
    ('^/(?P<path>.*)/*$',
     StaticHandler),
    ]

########NEW FILE########
