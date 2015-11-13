__FILENAME__ = cli
"""
This module contains the command line interface for snakeviz.

"""

import optparse
import os
import sys
import threading
import webbrowser


def main(argv=sys.argv[1:]):
    parser = optparse.OptionParser(
        usage='%prog [options] filename'
    )
    parser.add_option('-H', '--hostname', metavar='ADDR', default='127.0.0.1',
                      help='hostname to bind to (default: 127.0.0.1')

    # TODO: Make this help text actually true
    parser.add_option('-p', '--port', type='int', metavar='PORT', default=8080,
                      help='port to bind to; if this port is already in use a'
                           'free port will be selected automatically '
                           '(default: %default)')

    parser.add_option('-b', '--browser', metavar='PATH',
                      help="path to the web browser executable to use to open "
                           "the visualization; uses the same default as "
                           "Python's webbrowser module, which can also be "
                           "overridden with the BROWSER environment variable")

    options, args = parser.parse_args(argv)

    if len(args) != 1:
        parser.error('please provide the path to a profiler output file to '
                     'open')

    filename = os.path.abspath(args[0])
    if not os.path.exists(filename):
        parser.error('the file %s does not exist' % filename)

    try:
        open(filename)
    except IOError, e:
        parser.error('the file %s could not be opened: %s'
                     % (filename, str(e)))

    hostname = options.hostname
    port = options.port

    if not 0 <= port <= 65535:
        parser.error('invalid port number %d: use a port between 0 and 65535'
                     % port)

    try:
        browser = webbrowser.get(options.browser)
    except webbrowser.Error as e:
        parser.error('no web browser found: %s' % e)

    # Go ahead and import the tornado app and start it; we do an inline import
    # here to avoid the extra overhead when just running the cli for --help and
    # the like
    from .main import app
    import tornado.ioloop

    app.listen(port, address=hostname)
    app.settings['single_user_mode'] = True

    print ('snakeviz web server started on %s:%d; enter Ctrl-C to exit' %
           (hostname, port))

    # Launce the browser in a separate thread to avoid blocking the ioloop from
    # starting

    import platform
    if platform.system() == 'Windows':
        filename = '/' + filename

    bt = lambda: browser.open('http://%s:%d/viz/file%s' %
                              (hostname, port, filename), new=2)
    threading.Thread(target=bt).start()

    try:
        tornado.ioloop.IOLoop.instance().start()
    except KeyboardInterrupt:
        # TODO: Cheap KeyboardInterrupt handler for now; iPython has some nicer
        # stuff for handling SIGINT and SIGTERM that might be worth borrowing
        tornado.ioloop.IOLoop.instance().stop()
        print ('\nBye!')

    return 0

########NEW FILE########
__FILENAME__ = handler
"""
This module contains a Handler base class with a conveience method
for rendering templates with Jinja2. The Jinja2 environment
configuration is also here.

"""

import tornado.web
import jinja2
import os


template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir),
                               autoescape=True)


class Handler(tornado.web.RequestHandler):
    """
    This is the base class for other handlers throughout snakeviz.
    It overrides tornado's `render` method with one that uses Jinja2.

    """
    def render_template(self, template, **params):
        t = jinja_env.get_template(template)
        return t.render(params)

    def render(self, template, **params):
        self.write(self.render_template(template, **params))

########NEW FILE########
__FILENAME__ = ipymagic
import subprocess
import tempfile
import time

__all__ = ['load_ipython_extension']


def snakeviz_magic(line, cell=None):
    """
    Profile code and display the profile in Snakeviz.
    Works as a line or cell magic.

    """
    # get location for saved profile
    filename = tempfile.NamedTemporaryFile().name

    # call signature for prun
    line = '-q -D ' + filename + ' ' + line

    # generate the stats file using IPython's prun magic
    ip = get_ipython()

    if cell:
        ip.run_cell_magic('prun', line, cell)
    else:
        ip.run_line_magic('prun', line)

    # start up a Snakeviz server
    sv = subprocess.Popen(['snakeviz', filename])

    # give time for the Snakeviz page to load then shut down the server
    time.sleep(20)
    sv.terminate()


def load_ipython_extension(ipython):
    ipython.register_magic_function(snakeviz_magic, magic_kind='line_cell',
                                    magic_name='snakeviz')

########NEW FILE########
__FILENAME__ = main
#!/usr/bin/env python

import os.path

import tornado.ioloop
import tornado.web

settings = {
    'static_path': os.path.join(os.path.dirname(__file__), 'static'),
    'debug': True,
    'single_user_mode': True
}

# set of handlers for online mode
# handlers = [(r'/', 'snakeviz.upload.UploadHandler'),
#             (r'/json/(.*)\.json', 'snakeviz.upload.JSONHandler'),
#             (r'/viz/(.*)', 'snakeviz.viz.VizHandler')]

# set of handlers for offline, single user mode
handlers = [(r'/json/file/(.*)\.json', 'snakeviz.upload.JSONHandler'),
            (r'/viz/file/(.*)', 'snakeviz.viz.VizHandler')]

app = tornado.web.Application(handlers, **settings)

if __name__ == '__main__':
    app.listen(8080)
    tornado.ioloop.IOLoop.instance().start()

########NEW FILE########
__FILENAME__ = pstatsloader
"""Module to load cProfile/profile records as a tree of records"""
import pstats, os, logging
log = logging.getLogger(__name__)
#log.setLevel( logging.DEBUG )
from gettext import gettext as _

TREE_CALLS, TREE_FILES = range( 2 )

class PStatsLoader( object ):
    """Load profiler statistic from """
    def __init__( self, *filenames ):
        self.filename = filenames
        self.rows = {}
        self.stats = pstats.Stats( *filenames )
        self.tree = self.load( self.stats.stats )
        self.location_rows = {}
        self.location_tree = l = self.load_location( )
    def load( self, stats ):
        """Build a squaremap-compatible model from a pstats class"""
        rows = self.rows
        for func, raw in stats.iteritems():
            try:
                rows[func] = row = PStatRow( func,raw )
            except ValueError, err:
                log.info( 'Null row: %s', func )
        for row in rows.itervalues():
            row.weave( rows )
        return self.find_root( rows )

    def find_root( self, rows ):
        """Attempt to find/create a reasonable root node from list/set of rows

        rows -- key: PStatRow mapping

        TODO: still need more robustness here, particularly in the case of
        threaded programs.  Should be tracing back each row to root, breaking
        cycles by sorting on cummulative time, and then collecting the traced
        roots (or, if they are all on the same root, use that).
        """
        maxes = sorted( rows.values(), key = lambda x: x.cummulative )
        if not maxes:
            raise RuntimeError( """Null results!""" )
        root = maxes[-1]
        roots = [root]
        for key,value in rows.items():
            if not value.parents:
                log.debug( 'Found node root: %s', value )
                if value not in roots:
                    roots.append( value )
        if len(roots) > 1:
            root = PStatGroup(
                directory='*',
                filename='*',
                name=_("<profiling run>"),
                children= roots,
            )
            root.finalize()
            self.rows[ root.key ] = root
        return root
    def load_location( self ):
        """Build a squaremap-compatible model for location-based hierarchy"""
        directories = {}
        files = {}
        root = PStatLocation( '/', 'PYTHONPATH' )
        self.location_rows = self.rows.copy()
        for child in self.rows.values():
            current = directories.get( child.directory )
            directory, filename = child.directory, child.filename
            if current is None:
                if directory == '':
                    current = root
                else:
                    current = PStatLocation( directory, '' )
                    self.location_rows[ current.key ] = current
                directories[ directory ] = current
            if filename == '~':
                filename = '<built-in>'
            file_current = files.get( (directory,filename) )
            if file_current is None:
                file_current = PStatLocation( directory, filename )
                self.location_rows[ file_current.key ] = file_current
                files[ (directory,filename) ] = file_current
                current.children.append( file_current )
            file_current.children.append( child )
        # now link the directories...
        for key,value in directories.items():
            if value is root:
                continue
            found = False
            while key:
                new_key,rest = os.path.split( key )
                if new_key == key:
                    break
                key = new_key
                parent = directories.get( key )
                if parent:
                    if value is not parent:
                        parent.children.append( value )
                        found = True
                        break
            if not found:
                root.children.append( value )
        # lastly, finalize all of the directory records...
        root.finalize()
        return root

class BaseStat( object ):
    def recursive_distinct( self, already_done=None, attribute='children' ):
        if already_done is None:
            already_done = {}
        for child in getattr(self,attribute,()):
            if not already_done.has_key( child ):
                already_done[child] = True
                yield child
                for descendent in child.recursive_distinct( already_done=already_done, attribute=attribute ):
                    yield descendent

    def descendants( self ):
        return list( self.recursive_distinct( attribute='children' ))
    def ancestors( self ):
        return list( self.recursive_distinct( attribute='parents' ))

class PStatRow( BaseStat ):
    """Simulates a HotShot profiler record using PStats module"""
    def __init__( self, key, raw ):
        self.children = []
        self.parents = []
        file,line,func = self.key = key
        try:
            dirname,basename = os.path.dirname(file),os.path.basename(file)
        except ValueError, err:
            dirname = ''
            basename = file
        nc, cc, tt, ct, callers = raw
        if nc == cc == tt == ct == 0:
            raise ValueError( 'Null stats row' )
        (
            self.calls, self.recursive, self.local, self.localPer,
            self.cummulative, self.cummulativePer, self.directory,
            self.filename, self.name, self.lineno
        ) = (
            nc,
            cc,
            tt,
            tt/(cc or 0.00000000000001),
            ct,
            ct/(nc or 0.00000000000001),
            dirname,
            basename,
            func,
            line,
        )
        self.callers = callers
    def __repr__( self ):
        return 'PStatRow( %r,%r,%r,%r, %s )'%(self.directory, self.filename, self.lineno, self.name, len(self.children))
    def add_child( self, child ):
        self.children.append( child )

    def weave( self, rows ):
        for caller,data in self.callers.iteritems():
            # data is (cc,nc,tt,ct)
            parent = rows.get( caller )
            if parent:
                self.parents.append( parent )
                parent.children.append( self )
    def child_cumulative_time( self, child ):
        total = self.cummulative
        if total:
            try:
                (cc,nc,tt,ct) = child.callers[ self.key ]
            except TypeError, err:
                ct = child.callers[ self.key ]
            return float(ct)/total
        return 0



class PStatGroup( BaseStat ):
    """A node/record that holds a group of children but isn't a raw-record based group"""
    # if LOCAL_ONLY then only take the raw-record's local values, not cummulative values
    LOCAL_ONLY = False
    def __init__( self, directory='', filename='', name='', children=None, local_children=None, tree=TREE_CALLS ):
        self.directory = directory
        self.filename = filename
        self.name = ''
        self.key = (directory,filename,name)
        self.children = children or []
        self.parents = []
        self.local_children = local_children or []
        self.tree = tree
    def __repr__( self ):
        return '%s( %r,%r,%s )'%(self.__class__.__name__,self.directory, self.filename, self.name)
    def finalize( self, already_done=None ):
        """Finalize our values (recursively) taken from our children"""
        if already_done is None:
            already_done = {}
        if already_done.has_key( self ):
            return True
        already_done[self] = True
        self.filter_children()
        children = self.children
        for child in children:
            if hasattr( child, 'finalize' ):
                child.finalize( already_done)
            child.parents.append( self )
        self.calculate_totals( self.children, self.local_children )
    def filter_children( self ):
        """Filter our children into regular and local children sets (if appropriate)"""
    def calculate_totals( self, children, local_children=None ):
        """Calculate our cummulative totals from children and/or local children"""
        for field,local_field in (('recursive','calls'),('cummulative','local')):
            values = []
            for child in children:
                if isinstance( child, PStatGroup ) or not self.LOCAL_ONLY:
                    values.append( getattr( child, field, 0 ) )
                elif isinstance( child, PStatRow ) and self.LOCAL_ONLY:
                    values.append( getattr( child, local_field, 0 ) )
            value = sum( values )
            setattr( self, field, value )
        if self.recursive:
            self.cummulativePer = self.cummulative/float(self.recursive)
        else:
            self.recursive = 0
        if local_children:
            for field in ('local','calls'):
                value = sum([ getattr( child, field, 0 ) for child in children] )
                setattr( self, field, value )
            if self.calls:
                self.localPer = self.local / self.calls
        else:
            self.local = 0
            self.calls = 0
            self.localPer = 0


class PStatLocation( PStatGroup ):
    """A row that represents a hierarchic structure other than call-patterns

    This is used to create a file-based hierarchy for the views

    Children with the name <module> are our "empty" space,
    our totals are otherwise just the sum of our children.
    """
    LOCAL_ONLY = True
    def __init__( self, directory, filename, tree=TREE_FILES):
        super( PStatLocation, self ).__init__( directory=directory, filename=filename, name='package', tree=tree )
    def filter_children( self ):
        """Filter our children into regular and local children sets"""
        real_children = []
        for child in self.children:
            if child.name == '<module>':
                self.local_children.append( child )
            else:
                real_children.append( child )
        self.children = real_children



if __name__ == "__main__":
    import sys
    p = PStatsLoader( sys.argv[1] )
    assert p.tree
    print p.tree

########NEW FILE########
__FILENAME__ = upload
"""
This module contains the handlers for the upload page and the JSON
request URL. In the standalone, command line version the upload handler
is not used.

"""

import pstats
import json
import tempfile
import os
import multiprocessing as mp
import platform

from tornado import ioloop
from tornado.web import asynchronous

from . import pstatsloader
from . import handler


def storage_name(filename):
    """
    Prepend the temporary file directory to the input `filename`.

    Parameters
    ----------
    filename : str
        Any name to give a file.

    Returns
    -------
    tempname : str
        `filename` with temporary file directory prepended.

    """
    if len(filename) == 0:
        raise ValueError('filename must length greater than 0.')

    return os.path.join(tempfile.gettempdir(), filename)


class UploadHandler(handler.Handler):
    """
    Handler for a profile upload page. Not used in the command line
    version.

    """
    def get(self):
        self.render('upload.html')

    def post(self):
        filename = self.request.files['profile'][0]['filename']
        sfilename = storage_name(filename)

        # save the stats info to a file so it can be loaded by pstats
        with open(sfilename, 'wb') as f:
            f.write(self.request.files['profile'][0]['body'])

        # test whether this can be opened with pstats
        try:
            pstats.Stats(sfilename)

        except:
            os.remove(sfilename)
            error = 'There was an error parsing {0} with pstats.'
            error = error.format(filename)
            self.render('upload.html', error=error)

        else:
            self.redirect('viz/' + filename)


class JSONHandler(handler.Handler):
    """
    Handler for requesting the JSON representation of a profile.
    """

    _timer = None
    _pool = None
    _timeout = None
    _result = None

    @asynchronous
    def get(self, prof_name):
        if self.request.path.startswith('/json/file/'):
            if self.settings['single_user_mode']:
                if prof_name[0] != '/' and platform.system() != 'Windows':
                    prof_name = '/' + prof_name
                filename = os.path.abspath(prof_name)
            else:
                self.send_error(status_code=404)
        else:
            filename = storage_name(prof_name)

        self._pool = mp.Pool(1, maxtasksperchild=1)
        self._result = self._pool.apply_async(prof_to_json, (filename,))

        # TODO: Make the timeout parameters configurable
        self._timeout = 10  # in seconds
        self._period = 0.1  # in seconds
        self._timer = ioloop.PeriodicCallback(self._result_callback,
                                              self._period * 1000,
                                              ioloop.IOLoop.instance())
        self._timer.start()

    def _result_callback(self):
        try:
            content = self._result.get(0)
            self._finish_request(content)
        except mp.TimeoutError:
            self._timeout -= self._period
            if self._timeout < 0:
                self._finish_request('')

    def _finish_request(self, content):
        self._timer.stop()
        self._pool.terminate()
        self._pool.close()
        if content:
            self.set_header('Content-Type', 'application/json; charset=UTF-8')
        self.write(content)
        self.finish()


def prof_to_json(prof_name):
    """
    Convert profiles stats in a `pstats` compatible file to a JSON string.

    Parameters
    ----------
    prof_name : str
        Path to to a `pstats` compatible profile.

    Returns
    -------
    json_stats : str
        Profile as a JSON string.

    """
    loader = pstatsloader.PStatsLoader(prof_name)

    d = _stats_to_tree_dict(loader.tree.children[0])

    return json.dumps(d, indent=1)


def _stats_to_tree_dict(node, parent=None, parent_size=None,
                        recursive_seen=None):
    """
    `_stats_to_tree_dict` is a specialized function for converting
    a `pstatsloader.PStatsLoader` profile representation into a tree
    of nested dictionaries by recursively calling itself.
    It is primarily meant to be called from `prof_to_json`.

    Parameters
    ----------
    node : `pstatsloader.PStatsRow` or `pstatsloader.PStatGroup`
        One node of the call tree.
    parent : `pstatsloader.PStatsRow` or `pstatsloader.PStatGroup`
        Parent of `node`. Optional for the root node.
    parent_size : float
        Calculated size of `parent`. Optional for the root node.
    recursive_seen : set
        Set of nodes that are direct ancestors of `node`.
        This is used to prevent `_stats_to_tree_dict` from ending up in
        infinite loops when it encounters recursion.
        Optional for the root node.

    Returns
    -------
    tree_dict : dict
        Tree of nested dictionaries representing the profile call tree.

    """
    # recursive_seen prevents us from repeatedly traversing
    # recursive structures. only want to show the first set.
    if recursive_seen is None:
        recursive_seen = set()

    d = {}

    d['name'] = node.name
    d['filename'] = node.filename
    d['directory'] = node.directory

    if isinstance(node, pstatsloader.PStatRow):
        d['calls'] = node.calls
        d['recursive'] = node.recursive
        d['local'] = node.local
        d['localPer'] = node.localPer
        d['cumulative'] = node.cummulative
        d['cumulativePer'] = node.cummulativePer
        d['line_number'] = node.lineno

        recursive_seen.add(node)

    if parent:
        # figure out the size of this node. This is an arbitrary value
        # but it's important that the child size is no larger
        # than the parent size.
        if isinstance(parent, pstatsloader.PStatGroup):
            if parent.cummulative:
                d['size'] = node.cummulative / parent.cummulative * parent_size
            else:
                # this is a catch-all when it's not possible
                # to calculate a size. hopefully this doesn't come
                # up too often.
                d['size'] = 0
        else:
            d['size'] = parent.child_cumulative_time(node) * parent_size
    else:
        # default size for the root node
        d['size'] = 1000

    if node.children:
        d['children'] = []
        for child in node.children:
            if child not in recursive_seen:
                child_dict = _stats_to_tree_dict(child, node, d['size'],
                                                 recursive_seen)
                d['children'].append(child_dict)

        if d['children']:
            # make a "child" that represents the internal time of this function
            children_sum = sum(c['size'] for c in d['children'])

            if children_sum > d['size']:
                for child in d['children']:
                    child['size'] = child['size'] / children_sum * d['size']

            elif children_sum < d['size']:

                d_internal = {'name': node.name,
                              'filename': node.filename,
                              'directory': node.directory,
                              'size': d['size'] - children_sum}

                if isinstance(node, pstatsloader.PStatRow):
                    d_internal['calls'] = node.calls
                    d_internal['recursive'] = node.recursive
                    d_internal['local'] = node.local
                    d_internal['localPer'] = node.localPer
                    d_internal['cumulative'] = node.cummulative
                    d_internal['cumulativePer'] = node.cummulativePer
                    d_internal['line_number'] = node.lineno

                d['children'].append(d_internal)
        else:
            # there were no non-recursive children so get rid of the
            # children list.
            del d['children']

    if node in recursive_seen:
        # remove this node from the set so it doesn't interfere if this
        # node shows up again in another part of the call tree.
        recursive_seen.remove(node)

    return d

########NEW FILE########
__FILENAME__ = viz
"""
This module contains the handler and supporting functions for the primary
visualization page.

"""

import os
import platform
from collections import namedtuple

from . import pstatsloader
from . import handler
from . import upload


# a structure to represent all of the profile data on a particular function
# the viz.html template is expecting a list of these so it can build its
# stats table.
StatsRow = namedtuple('StatsRow', ['calls_value', 'calls_str',
                                   'tottime', 'tottime_str',
                                   'tottime_percall', 'tottime_percall_str',
                                   'cumtime', 'cumtime_str',
                                   'cumtime_percall', 'cumtime_percall_str',
                                   'file_line_func'])


def stats_rows(filename):
    """
    Build a list of StatsRow objects that will be used to make the
    profile stats table beneath the profile visualization.

    Parameters
    ----------
    filename : str
        Name of profiling output as made by Python's built-in profilers.

    """
    time_fmt = '{0:>12.6g}'

    loader = pstatsloader.PStatsLoader(filename)

    rows = []

    for r in loader.rows.itervalues():
        if isinstance(r, pstatsloader.PStatRow):
            calls_value = r.recursive
            if r.recursive > r.calls:
                calls_str = '{0}/{1}'.format(r.recursive, r.calls)
            else:
                calls_str = str(r.calls)
            tottime = r.local
            tottime_str = time_fmt.format(tottime)
            tottime_percall = r.localPer
            tottime_percall_str = time_fmt.format(tottime_percall)
            cumtime = r.cummulative
            cumtime_str = time_fmt.format(cumtime)
            cumtime_percall = r.cummulativePer
            cumtime_percall_str = time_fmt.format(cumtime_percall)
            file_line_func = '{0}:{1}({2})'.format(r.filename,
                                                   r.lineno,
                                                   r.name)
            rows.append(StatsRow(calls_value, calls_str,
                                 tottime, tottime_str,
                                 tottime_percall, tottime_percall_str,
                                 cumtime, cumtime_str,
                                 cumtime_percall, cumtime_percall_str,
                                 file_line_func))

    return rows


class VizHandler(handler.Handler):
    """
    Handler for the main visualization page. Renders viz.html.

    """
    def get(self, profile_name):
        if self.request.path.startswith('/viz/file/'):
            if self.settings['single_user_mode']:
                # Allow opening arbitrary files by full filesystem path
                # WARNING!!! Obviously this must be disabled by default
                # TODO: Some modicum of error handling here as well...

                json_path = '/json/file/%s.json' % profile_name

                if profile_name[0] != '/' and platform.system() != 'Windows':
                    profile_name = '/' + profile_name
                filename = os.path.abspath(profile_name)
            else:
                # TODO: Raise a 404 error here
                pass
        else:
            filename = upload.storage_name(profile_name)
            json_path = '/json/%s.json' % filename

        rows = stats_rows(filename)

        self.render('viz.html', profile_name=profile_name, json_path=json_path,
                    stats_rows=rows)

########NEW FILE########
