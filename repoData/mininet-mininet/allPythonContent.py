__FILENAME__ = topo-2sw-2host
"""Custom topology example

Two directly connected switches plus a host for each switch:

   host --- switch --- switch --- host

Adding the 'topos' dict with a key/value pair to generate our newly defined
topology enables one to pass in '--topo=mytopo' from the command line.
"""

from mininet.topo import Topo

class MyTopo( Topo ):
    "Simple topology example."

    def __init__( self ):
        "Create custom topo."

        # Initialize topology
        Topo.__init__( self )

        # Add hosts and switches
        leftHost = self.addHost( 'h1' )
        rightHost = self.addHost( 'h2' )
        leftSwitch = self.addSwitch( 's3' )
        rightSwitch = self.addSwitch( 's4' )

        # Add links
        self.addLink( leftHost, leftSwitch )
        self.addLink( leftSwitch, rightSwitch )
        self.addLink( rightSwitch, rightHost )


topos = { 'mytopo': ( lambda: MyTopo() ) }

########NEW FILE########
__FILENAME__ = baresshd
#!/usr/bin/python

"This example doesn't use OpenFlow, but attempts to run sshd in a namespace."

import sys
from mininet.node import Host
from mininet.util import ensureRoot

ensureRoot()

print "*** Creating nodes"
h1 = Host( 'h1' )

root = Host( 'root', inNamespace=False )

print "*** Creating links"
h1.linkTo( root )

print h1

print "*** Configuring nodes"
h1.setIP( '10.0.0.1', 8 )
root.setIP( '10.0.0.2', 8 )

print "*** Creating banner file"
f = open( '/tmp/%s.banner' % h1.name, 'w' )
f.write( 'Welcome to %s at %s\n' % ( h1.name, h1.IP() ) )
f.close()

print "*** Running sshd"
cmd = '/usr/sbin/sshd -o UseDNS=no -u0 -o "Banner /tmp/%s.banner"' % h1.name
# add arguments from the command line
if len( sys.argv ) > 1:
    cmd += ' ' + ' '.join( sys.argv[ 1: ] )
h1.cmd( cmd )

print "*** You may now ssh into", h1.name, "at", h1.IP()

########NEW FILE########
__FILENAME__ = bind
#!/usr/bin/python

"""
bind.py: Bind mount prototype

This creates hosts with private directories as desired.
"""

from mininet.net import Mininet
from mininet.node import Host
from mininet.cli import CLI
from mininet.util import errFail, quietRun, errRun
from mininet.topo import SingleSwitchTopo
from mininet.log import setLogLevel, info, debug

from os.path import realpath
from functools import partial


# Utility functions for unmounting a tree

MNRUNDIR = realpath( '/var/run/mn' )

def mountPoints():
    "Return list of mounted file systems"
    mtab, _err, _ret = errFail( 'cat /proc/mounts' )
    lines = mtab.split( '\n' )
    mounts = []
    for line in lines:
        if not line:
            continue
        fields = line.split( ' ')
        mount = fields[ 1 ]
        mounts.append( mount )
    return mounts

def unmountAll( rootdir=MNRUNDIR ):
    "Unmount all mounts under a directory tree"
    rootdir = realpath( rootdir )
    # Find all mounts below rootdir
    # This is subtle because /foo is not
    # a parent of /foot
    dirslash = rootdir + '/'
    mounts = [ m for m in mountPoints()
              if m == dir or m.find( dirslash ) == 0 ]
    # Unmount them from bottom to top
    mounts.sort( reverse=True )
    for mount in mounts:
        debug( 'Unmounting', mount, '\n' )
        _out, err, code = errRun( 'umount', mount )
        if code != 0:
            info( '*** Warning: failed to umount', mount, '\n' )
            info( err )


class HostWithPrivateDirs( Host ):
    "Host with private directories"

    mnRunDir = MNRUNDIR

    def __init__(self, name, *args, **kwargs ):
        """privateDirs: list of private directories
           remounts: dirs to remount
           unmount: unmount dirs in cleanup? (True)
           Note: if unmount is False, you must call unmountAll()
           manually."""
        self.privateDirs = kwargs.pop( 'privateDirs', [] )
        self.remounts = kwargs.pop( 'remounts', [] )
        self.unmount = kwargs.pop( 'unmount', True )
        Host.__init__( self, name, *args, **kwargs )
        self.rundir = '%s/%s' % ( self.mnRunDir, name )
        self.root, self.private = None, None  # set in createBindMounts
        if self.privateDirs:
            self.privateDirs = [ realpath( d ) for d in self.privateDirs ]
            self.createBindMounts()
        # These should run in the namespace before we chroot,
        # in order to put the right entries in /etc/mtab
        # Eventually this will allow a local pid space
        # Now we chroot and cd to wherever we were before.
        pwd = self.cmd( 'pwd' ).strip()
        self.sendCmd( 'exec chroot', self.root, 'bash -ms mininet:'
                       + self.name )
        self.waiting = False
        self.cmd( 'cd', pwd )
        # In order for many utilities to work,
        # we need to remount /proc and /sys
        self.cmd( 'mount /proc' )
        self.cmd( 'mount /sys' )

    def mountPrivateDirs( self ):
        "Create and bind mount private dirs"
        for dir_ in self.privateDirs:
            privateDir = self.private + dir_
            errFail( 'mkdir -p ' + privateDir )
            mountPoint = self.root + dir_
            errFail( 'mount -B %s %s' %
                           ( privateDir, mountPoint) )

    def mountDirs( self, dirs ):
        "Mount a list of directories"
        for dir_ in dirs:
            mountpoint = self.root + dir_
            errFail( 'mount -B %s %s' %
                     ( dir_, mountpoint ) )

    @classmethod
    def findRemounts( cls, fstypes=None ):
        """Identify mount points in /proc/mounts to remount
           fstypes: file system types to match"""
        if fstypes is None:
            fstypes = [ 'nfs' ]
        dirs = quietRun( 'cat /proc/mounts' ).strip().split( '\n' )
        remounts = []
        for dir_ in dirs:
            line = dir_.split()
            mountpoint, fstype = line[ 1 ], line[ 2 ]
            # Don't re-remount directories!!!
            if mountpoint.find( cls.mnRunDir ) == 0:
                continue
            if fstype in fstypes:
                remounts.append( mountpoint )
        return remounts

    def createBindMounts( self ):
        """Create a chroot directory structure,
           with self.privateDirs as private dirs"""
        errFail( 'mkdir -p '+ self.rundir )
        unmountAll( self.rundir )
        # Create /root and /private directories
        self.root = self.rundir + '/root'
        self.private = self.rundir + '/private'
        errFail( 'mkdir -p ' + self.root )
        errFail( 'mkdir -p ' + self.private )
        # Recursively mount / in private doort
        # note we'll remount /sys and /proc later
        errFail( 'mount -B / ' + self.root )
        self.mountDirs( self.remounts )
        self.mountPrivateDirs()

    def unmountBindMounts( self ):
        "Unmount all of our bind mounts"
        unmountAll( self.rundir )

    def popen( self, *args, **kwargs ):
        "Popen with chroot support"
        chroot = kwargs.pop( 'chroot', True )
        mncmd = kwargs.get( 'mncmd',
                           [ 'mnexec', '-a', str( self.pid ) ] )
        if chroot:
            mncmd = [ 'chroot', self.root ] + mncmd
            kwargs[ 'mncmd' ] = mncmd
        return Host.popen( self, *args, **kwargs )

    def cleanup( self ):
        """Clean up, then unmount bind mounts
           unmount: actually unmount bind mounts?"""
        # Wait for process to actually terminate
        self.shell.wait()
        Host.cleanup( self )
        if self.unmount:
            self.unmountBindMounts()
            errFail( 'rmdir ' + self.root )


# Convenience aliases

findRemounts = HostWithPrivateDirs.findRemounts


# Sample usage

def testHostWithPrivateDirs():
    "Test bind mounts"
    topo = SingleSwitchTopo( 10 )
    remounts = findRemounts( fstypes=[ 'nfs' ] )
    privateDirs = [ '/var/log', '/var/run' ]
    host = partial( HostWithPrivateDirs, remounts=remounts,
                    privateDirs=privateDirs, unmount=False )
    net = Mininet( topo=topo, host=host )
    net.start()
    info( 'Private Directories:', privateDirs, '\n' )
    CLI( net )
    net.stop()
    # We do this all at once to save a bit of time
    info( 'Unmounting host bind mounts...\n' )
    unmountAll()


if __name__ == '__main__':
    unmountAll()
    setLogLevel( 'info' )
    testHostWithPrivateDirs()
    info( 'Done.\n')





########NEW FILE########
__FILENAME__ = consoles
#!/usr/bin/python

"""
consoles.py: bring up a bunch of miniature consoles on a virtual network

This demo shows how to monitor a set of nodes by using
Node's monitor() and Tkinter's createfilehandler().

We monitor nodes in a couple of ways:

- First, each individual node is monitored, and its output is added
  to its console window

- Second, each time a console window gets iperf output, it is parsed
  and accumulated. Once we have output for all consoles, a bar is
  added to the bandwidth graph.

The consoles also support limited interaction:

- Pressing "return" in a console will send a command to it

- Pressing the console's title button will open up an xterm

Bob Lantz, April 2010

"""

import re

from Tkinter import Frame, Button, Label, Text, Scrollbar, Canvas, Wm, READABLE

from mininet.log import setLogLevel
from mininet.topolib import TreeNet
from mininet.term import makeTerms, cleanUpScreens
from mininet.util import quietRun

class Console( Frame ):
    "A simple console on a host."

    def __init__( self, parent, net, node, height=10, width=32, title='Node' ):
        Frame.__init__( self, parent )

        self.net = net
        self.node = node
        self.prompt = node.name + '# '
        self.height, self.width, self.title = height, width, title

        # Initialize widget styles
        self.buttonStyle = { 'font': 'Monaco 7' }
        self.textStyle = {
            'font': 'Monaco 7',
            'bg': 'black',
            'fg': 'green',
            'width': self.width,
            'height': self.height,
            'relief': 'sunken',
            'insertbackground': 'green',
            'highlightcolor': 'green',
            'selectforeground': 'black',
            'selectbackground': 'green'
        }

        # Set up widgets
        self.text = self.makeWidgets( )
        self.bindEvents()
        self.sendCmd( 'export TERM=dumb' )

        self.outputHook = None

    def makeWidgets( self ):
        "Make a label, a text area, and a scroll bar."

        def newTerm( net=self.net, node=self.node, title=self.title ):
            "Pop up a new terminal window for a node."
            net.terms += makeTerms( [ node ], title )
        label = Button( self, text=self.node.name, command=newTerm,
                        **self.buttonStyle )
        label.pack( side='top', fill='x' )
        text = Text( self, wrap='word', **self.textStyle )
        ybar = Scrollbar( self, orient='vertical', width=7,
                          command=text.yview )
        text.configure( yscrollcommand=ybar.set )
        text.pack( side='left', expand=True, fill='both' )
        ybar.pack( side='right', fill='y' )
        return text

    def bindEvents( self ):
        "Bind keyboard and file events."
        # The text widget handles regular key presses, but we
        # use special handlers for the following:
        self.text.bind( '<Return>', self.handleReturn )
        self.text.bind( '<Control-c>', self.handleInt )
        self.text.bind( '<KeyPress>', self.handleKey )
        # This is not well-documented, but it is the correct
        # way to trigger a file event handler from Tk's
        # event loop!
        self.tk.createfilehandler( self.node.stdout, READABLE,
                                   self.handleReadable )

    # We're not a terminal (yet?), so we ignore the following
    # control characters other than [\b\n\r]
    ignoreChars = re.compile( r'[\x00-\x07\x09\x0b\x0c\x0e-\x1f]+' )

    def append( self, text ):
        "Append something to our text frame."
        text = self.ignoreChars.sub( '', text )
        self.text.insert( 'end', text )
        self.text.mark_set( 'insert', 'end' )
        self.text.see( 'insert' )
        outputHook = lambda x, y: True  # make pylint happier
        if self.outputHook:
            outputHook = self.outputHook
        outputHook( self, text )

    def handleKey( self, event ):
        "If it's an interactive command, send it to the node."
        char = event.char
        if self.node.waiting:
            self.node.write( char )

    def handleReturn( self, event ):
        "Handle a carriage return."
        cmd = self.text.get( 'insert linestart', 'insert lineend' )
        # Send it immediately, if "interactive" command
        if self.node.waiting:
            self.node.write( event.char )
            return
        # Otherwise send the whole line to the shell
        pos = cmd.find( self.prompt )
        if pos >= 0:
            cmd = cmd[ pos + len( self.prompt ): ]
        self.sendCmd( cmd )

    # Callback ignores event
    def handleInt( self, _event=None ):
        "Handle control-c."
        self.node.sendInt()

    def sendCmd( self, cmd ):
        "Send a command to our node."
        if not self.node.waiting:
            self.node.sendCmd( cmd )

    def handleReadable( self, _fds, timeoutms=None ):
        "Handle file readable event."
        data = self.node.monitor( timeoutms )
        self.append( data )
        if not self.node.waiting:
            # Print prompt
            self.append( self.prompt )

    def waiting( self ):
        "Are we waiting for output?"
        return self.node.waiting

    def waitOutput( self ):
        "Wait for any remaining output."
        while self.node.waiting:
            # A bit of a trade-off here...
            self.handleReadable( self, timeoutms=1000)
            self.update()

    def clear( self ):
        "Clear all of our text."
        self.text.delete( '1.0', 'end' )


class Graph( Frame ):

    "Graph that we can add bars to over time."

    def __init__( self, parent=None, bg = 'white', gheight=200, gwidth=500,
                  barwidth=10, ymax=3.5,):

        Frame.__init__( self, parent )

        self.bg = bg
        self.gheight = gheight
        self.gwidth = gwidth
        self.barwidth = barwidth
        self.ymax = float( ymax )
        self.xpos = 0

        # Create everything
        self.title, self.scale, self.graph = self.createWidgets()
        self.updateScrollRegions()
        self.yview( 'moveto', '1.0' )

    def createScale( self ):
        "Create a and return a new canvas with scale markers."
        height = float( self.gheight )
        width = 25
        ymax = self.ymax
        scale = Canvas( self, width=width, height=height,
                        background=self.bg )
        opts = { 'fill': 'red' }
        # Draw scale line
        scale.create_line( width - 1, height, width - 1, 0, **opts )
        # Draw ticks and numbers
        for y in range( 0, int( ymax + 1 ) ):
            ypos = height * (1 - float( y ) / ymax )
            scale.create_line( width, ypos, width - 10, ypos, **opts )
            scale.create_text( 10, ypos, text=str( y ), **opts )
        return scale

    def updateScrollRegions( self ):
        "Update graph and scale scroll regions."
        ofs = 20
        height = self.gheight + ofs
        self.graph.configure( scrollregion=( 0, -ofs,
                              self.xpos * self.barwidth, height ) )
        self.scale.configure( scrollregion=( 0, -ofs, 0, height ) )

    def yview( self, *args ):
        "Scroll both scale and graph."
        self.graph.yview( *args )
        self.scale.yview( *args )

    def createWidgets( self ):
        "Create initial widget set."

        # Objects
        title = Label( self, text='Bandwidth (Gb/s)', bg=self.bg )
        width = self.gwidth
        height = self.gheight
        scale = self.createScale()
        graph = Canvas( self, width=width, height=height, background=self.bg)
        xbar = Scrollbar( self, orient='horizontal', command=graph.xview )
        ybar = Scrollbar( self, orient='vertical', command=self.yview )
        graph.configure( xscrollcommand=xbar.set, yscrollcommand=ybar.set,
                         scrollregion=(0, 0, width, height ) )
        scale.configure( yscrollcommand=ybar.set )

        # Layout
        title.grid( row=0, columnspan=3, sticky='new')
        scale.grid( row=1, column=0, sticky='nsew' )
        graph.grid( row=1, column=1, sticky='nsew' )
        ybar.grid( row=1, column=2, sticky='ns' )
        xbar.grid( row=2, column=0, columnspan=2, sticky='ew' )
        self.rowconfigure( 1, weight=1 )
        self.columnconfigure( 1, weight=1 )
        return title, scale, graph

    def addBar( self, yval ):
        "Add a new bar to our graph."
        percent = yval / self.ymax
        c = self.graph
        x0 = self.xpos * self.barwidth
        x1 = x0 + self.barwidth
        y0 = self.gheight
        y1 = ( 1 - percent ) * self.gheight
        c.create_rectangle( x0, y0, x1, y1, fill='green' )
        self.xpos += 1
        self.updateScrollRegions()
        self.graph.xview( 'moveto', '1.0' )

    def clear( self ):
        "Clear graph contents."
        self.graph.delete( 'all' )
        self.xpos = 0

    def test( self ):
        "Add a bar for testing purposes."
        ms = 1000
        if self.xpos < 10:
            self.addBar( self.xpos / 10 * self.ymax  )
            self.after( ms, self.test )

    def setTitle( self, text ):
        "Set graph title"
        self.title.configure( text=text, font='Helvetica 9 bold' )


class ConsoleApp( Frame ):

    "Simple Tk consoles for Mininet."

    menuStyle = { 'font': 'Geneva 7 bold' }

    def __init__( self, net, parent=None, width=4 ):
        Frame.__init__( self, parent )
        self.top = self.winfo_toplevel()
        self.top.title( 'Mininet' )
        self.net = net
        self.menubar = self.createMenuBar()
        cframe = self.cframe = Frame( self )
        self.consoles = {}  # consoles themselves
        titles = {
            'hosts': 'Host',
            'switches': 'Switch',
            'controllers': 'Controller'
        }
        for name in titles:
            nodes = getattr( net, name )
            frame, consoles = self.createConsoles(
                cframe, nodes, width, titles[ name ] )
            self.consoles[ name ] = Object( frame=frame, consoles=consoles )
        self.selected = None
        self.select( 'hosts' )
        self.cframe.pack( expand=True, fill='both' )
        cleanUpScreens()
        # Close window gracefully
        Wm.wm_protocol( self.top, name='WM_DELETE_WINDOW', func=self.quit )

        # Initialize graph
        graph = Graph( cframe )
        self.consoles[ 'graph' ] = Object( frame=graph, consoles=[ graph ] )
        self.graph = graph
        self.graphVisible = False
        self.updates = 0
        self.hostCount = len( self.consoles[ 'hosts' ].consoles )
        self.bw = 0

        self.pack( expand=True, fill='both' )

    def updateGraph( self, _console, output ):
        "Update our graph."
        m = re.search( r'(\d+.?\d*) ([KMG]?bits)/sec', output )
        if not m:
            return
        val, units = float( m.group( 1 ) ), m.group( 2 )
        #convert to Gbps
        if units[0] == 'M':
            val *= 10 ** -3
        elif units[0] == 'K':
            val *= 10 ** -6
        elif units[0] == 'b':
            val *= 10 ** -9
        self.updates += 1
        self.bw +=  val
        if self.updates >= self.hostCount:
            self.graph.addBar( self.bw )
            self.bw = 0
            self.updates = 0

    def setOutputHook( self, fn=None, consoles=None ):
        "Register fn as output hook [on specific consoles.]"
        if consoles is None:
            consoles = self.consoles[ 'hosts' ].consoles
        for console in consoles:
            console.outputHook = fn

    def createConsoles( self, parent, nodes, width, title ):
        "Create a grid of consoles in a frame."
        f = Frame( parent )
        # Create consoles
        consoles = []
        index = 0
        for node in nodes:
            console = Console( f, self.net, node, title=title )
            consoles.append( console )
            row = index / width
            column = index % width
            console.grid( row=row, column=column, sticky='nsew' )
            index += 1
            f.rowconfigure( row, weight=1 )
            f.columnconfigure( column, weight=1 )
        return f, consoles

    def select( self, groupName ):
        "Select a group of consoles to display."
        if self.selected is not None:
            self.selected.frame.pack_forget()
        self.selected = self.consoles[ groupName ]
        self.selected.frame.pack( expand=True, fill='both' )

    def createMenuBar( self ):
        "Create and return a menu (really button) bar."
        f = Frame( self )
        buttons = [
            ( 'Hosts', lambda: self.select( 'hosts' ) ),
            ( 'Switches', lambda: self.select( 'switches' ) ),
            ( 'Controllers', lambda: self.select( 'controllers' ) ),
            ( 'Graph', lambda: self.select( 'graph' ) ),
            ( 'Ping', self.ping ),
            ( 'Iperf', self.iperf ),
            ( 'Interrupt', self.stop ),
            ( 'Clear', self.clear ),
            ( 'Quit', self.quit )
        ]
        for name, cmd in buttons:
            b = Button( f, text=name, command=cmd, **self.menuStyle )
            b.pack( side='left' )
        f.pack( padx=4, pady=4, fill='x' )
        return f

    def clear( self ):
        "Clear selection."
        for console in self.selected.consoles:
            console.clear()

    def waiting( self, consoles=None ):
        "Are any of our hosts waiting for output?"
        if consoles is None:
            consoles = self.consoles[ 'hosts' ].consoles
        for console in consoles:
            if console.waiting():
                return True
        return False

    def ping( self ):
        "Tell each host to ping the next one."
        consoles = self.consoles[ 'hosts' ].consoles
        if self.waiting( consoles ):
            return
        count = len( consoles )
        i = 0
        for console in consoles:
            i = ( i + 1 ) % count
            ip = consoles[ i ].node.IP()
            console.sendCmd( 'ping ' + ip )

    def iperf( self ):
        "Tell each host to iperf to the next one."
        consoles = self.consoles[ 'hosts' ].consoles
        if self.waiting( consoles ):
            return
        count = len( consoles )
        self.setOutputHook( self.updateGraph )
        for console in consoles:
            # Sometimes iperf -sD doesn't return,
            # so we run it in the background instead
            console.node.cmd( 'iperf -s &' )
        i = 0
        for console in consoles:
            i = ( i + 1 ) % count
            ip = consoles[ i ].node.IP()
            console.sendCmd( 'iperf -t 99999 -i 1 -c ' + ip )

    def stop( self, wait=True ):
        "Interrupt all hosts."
        consoles = self.consoles[ 'hosts' ].consoles
        for console in consoles:
            console.handleInt()
        if wait:
            for console in consoles:
                console.waitOutput()
        self.setOutputHook( None )
        # Shut down any iperfs that might still be running
        quietRun( 'killall -9 iperf' )

    def quit( self ):
        "Stop everything and quit."
        self.stop( wait=False)
        Frame.quit( self )


# Make it easier to construct and assign objects

def assign( obj, **kwargs ):
    "Set a bunch of fields in an object."
    obj.__dict__.update( kwargs )

class Object( object ):
    "Generic object you can stuff junk into."
    def __init__( self, **kwargs ):
        assign( self, **kwargs )


if __name__ == '__main__':
    setLogLevel( 'info' )
    network = TreeNet( depth=2, fanout=4 )
    network.start()
    app = ConsoleApp( network, width=4 )
    app.mainloop()
    network.stop()

########NEW FILE########
__FILENAME__ = controllers
#!/usr/bin/python

"""
Create a network where different switches are connected to
different controllers, by creating a custom Switch() subclass.
"""

from mininet.net import Mininet
from mininet.node import OVSSwitch, Controller, RemoteController
from mininet.topolib import TreeTopo
from mininet.log import setLogLevel
from mininet.cli import CLI

setLogLevel( 'info' )

# Two local and one "external" controller (which is actually c0)
# Ignore the warning message that the remote isn't (yet) running
c0 = Controller( 'c0', port=6633 )
c1 = Controller( 'c1', port=6634 )
c2 = RemoteController( 'c2', ip='127.0.0.1' )

cmap = { 's1': c0, 's2': c1, 's3': c2 }

class MultiSwitch( OVSSwitch ):
    "Custom Switch() subclass that connects to different controllers"
    def start( self, controllers ):
        return OVSSwitch.start( self, [ cmap[ self.name ] ] )

topo = TreeTopo( depth=2, fanout=2 )
net = Mininet( topo=topo, switch=MultiSwitch, build=False )
for c in [ c0, c1 ]:
    net.addController(c)
net.build()
net.start()
CLI( net )
net.stop()

########NEW FILE########
__FILENAME__ = controllers2
#!/usr/bin/python

"""
This example creates a multi-controller network from semi-scratch by
using the net.add*() API and manually starting the switches and controllers.

This is the "mid-level" API, which is an alternative to the "high-level"
Topo() API which supports parametrized topology classes.

Note that one could also create a custom switch class and pass it into
the Mininet() constructor.
"""

from mininet.net import Mininet
from mininet.node import Controller, OVSSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel

def multiControllerNet():
    "Create a network from semi-scratch with multiple controllers."

    net = Mininet( controller=Controller, switch=OVSSwitch )

    print "*** Creating (reference) controllers"
    c1 = net.addController( 'c1', port=6633 )
    c2 = net.addController( 'c2', port=6634 )

    print "*** Creating switches"
    s1 = net.addSwitch( 's1' )
    s2 = net.addSwitch( 's2' )

    print "*** Creating hosts"
    hosts1 = [ net.addHost( 'h%d' % n ) for n in 3, 4 ]
    hosts2 = [ net.addHost( 'h%d' % n ) for n in 5, 6 ]

    print "*** Creating links"
    for h in hosts1:
        net.addLink( s1, h )
    for h in hosts2:
        net.addLink( s2, h )
    net.addLink( s1, s2 )

    print "*** Starting network"
    net.build()
    c1.start()
    c2.start()
    s1.start( [ c1 ] )
    s2.start( [ c2 ] )

    print "*** Testing network"
    net.pingAll()

    print "*** Running CLI"
    CLI( net )

    print "*** Stopping network"
    net.stop()

if __name__ == '__main__':
    setLogLevel( 'info' )  # for CLI output
    multiControllerNet()

########NEW FILE########
__FILENAME__ = controlnet
#!/usr/bin/python

"""
controlnet.py: Mininet with a custom control network

We create two Mininet() networks, a control network
and a data network, running four DataControllers on the
control network to control the data network.

Since we're using UserSwitch on the data network,
it should correctly fail over to a backup controller.

We also use a Mininet Facade to talk to both the
control and data networks from a single CLI.
"""

from functools import partial

from mininet.net import Mininet
from mininet.node import Controller, UserSwitch
from mininet.cli import CLI
from mininet.topo import Topo
from mininet.topolib import TreeTopo
from mininet.log import setLogLevel, info

# Some minor hacks

class DataController( Controller ):
    """Data Network Controller.
       patched to avoid checkListening error"""
    def checkListening( self ):
        "Ignore spurious error"
        pass

class MininetFacade( object ):
    """Mininet object facade that allows a single CLI to
       talk to one or more networks"""
    
    def __init__( self, net, *args, **kwargs ):
        """Create MininetFacade object.
           net: Primary Mininet object
           args: unnamed networks passed as arguments
           kwargs: named networks passed as arguments"""
        self.net = net
        self.nets = [ net ] + list( args ) + kwargs.values()
        self.nameToNet = kwargs
        self.nameToNet['net'] = net

    def __getattr__( self, name ):
        "returns attribute from Primary Mininet object"
        return getattr( self.net, name )

    def __getitem__( self, key ):
        "returns primary/named networks or node from any net"
        #search kwargs for net named key
        if key in self.nameToNet:
            return self.nameToNet[ key ]
        #search each net for node named key
        for net in self.nets:
            if key in net:
                return net[ key ]

    def __iter__( self ):
        "Iterate through all nodes in all Mininet objects"
        for net in self.nets:
            for node in net:
                yield node

    def __len__( self ):
        "returns aggregate number of nodes in all nets"
        count = 0
        for net in self.nets:
            count += len(net)
        return count

    def __contains__( self, key ):
        "returns True if node is a member of any net"
        return key in self.keys()

    def keys( self ):
        "returns a list of all node names in all networks"
        return list( self )

    def values( self ):
        "returns a list of all nodes in all networks"
        return [ self[ key ] for key in self ]

    def items( self ):
        "returns (key,value) tuple list for every node in all networks"
        return zip( self.keys(), self.values() )

# A real control network!

class ControlNetwork( Topo ):
    "Control Network Topology"
    def __init__( self, n, dataController=DataController, **kwargs ):
        """n: number of data network controller nodes
           dataController: class for data network controllers"""
        Topo.__init__( self, **kwargs )
        # Connect everything to a single switch
        cs0 = self.addSwitch( 'cs0' )
        # Add hosts which will serve as data network controllers
        for i in range( 0, n ):
            c = self.addHost( 'c%s' % i, cls=dataController,
                              inNamespace=True )
            self.addLink( c, cs0 )
        # Connect switch to root namespace so that data network
        # switches will be able to talk to us
        root = self.addHost( 'root', inNamespace=False )
        self.addLink( root, cs0 )


# Make it Happen!!

def run():
    "Create control and data networks, and invoke the CLI"
    
    info( '* Creating Control Network\n' )
    ctopo = ControlNetwork( n=4, dataController=DataController )
    cnet = Mininet( topo=ctopo, ipBase='192.168.123.0/24', controller=None )
    info( '* Adding Control Network Controller\n')
    cnet.addController( 'cc0', controller=Controller )
    info( '* Starting Control Network\n')
    cnet.start()

    info( '* Creating Data Network\n' )
    topo = TreeTopo( depth=2, fanout=2 )
    # UserSwitch so we can easily test failover
    sw = partial( UserSwitch, opts='--inactivity-probe=1 --max-backoff=1' )
    net = Mininet( topo=topo, switch=sw, controller=None )
    info( '* Adding Controllers to Data Network\n' )
    for host in cnet.hosts:
        if isinstance(host, Controller):
            net.addController( host )
    info( '* Starting Data Network\n')
    net.start()

    mn = MininetFacade( net, cnet=cnet )

    CLI( mn )

    info( '* Stopping Data Network\n' )
    net.stop()

    info( '* Stopping Control Network\n' )
    cnet.stop()


if __name__ == '__main__':
    setLogLevel( 'info' )
    run()

########NEW FILE########
__FILENAME__ = cpu
#!/usr/bin/python

"""
cpu.py: test iperf bandwidth for varying cpu limits
"""

from mininet.net import Mininet
from mininet.node import CPULimitedHost
from mininet.topolib import TreeTopo
from mininet.util import custom
from mininet.log import setLogLevel, output

from time import sleep

def waitListening(client, server, port):
    "Wait until server is listening on port"
    if not client.cmd('which telnet'):
        raise Exception('Could not find telnet')
    cmd = ('sh -c "echo A | telnet -e A %s %s"' %
           (server.IP(), port))
    while 'Connected' not in client.cmd(cmd):
        output('waiting for', server,
               'to listen on port', port, '\n')
        sleep(.5)


def bwtest( cpuLimits, period_us=100000, seconds=5 ):
    """Example/test of link and CPU bandwidth limits
       cpu: cpu limit as fraction of overall CPU time"""

    topo = TreeTopo( depth=1, fanout=2 )

    results = {}

    for sched in 'rt', 'cfs':
        print '*** Testing with', sched, 'bandwidth limiting'
        for cpu in cpuLimits:
            host = custom( CPULimitedHost, sched=sched,
                           period_us=period_us,
                           cpu=cpu )
            net = Mininet( topo=topo, host=host )
            net.start()
            net.pingAll()
            hosts = [ net.getNodeByName( h ) for h in topo.hosts() ]
            client, server = hosts[ 0 ], hosts[ -1 ]
            server.cmd( 'iperf -s -p 5001 &' )
            waitListening( client, server, 5001 )
            result = client.cmd( 'iperf -yc -t %s -c %s' % (
                seconds, server.IP() ) ).split( ',' )
            bps = float( result[ -1 ] )
            server.cmdPrint( 'kill %iperf' )
            net.stop()
            updated = results.get( sched, [] )
            updated += [ ( cpu, bps ) ]
            results[ sched ] = updated

    return results


def dump( results ):
    "Dump results"

    fmt = '%s\t%s\t%s'

    print
    print fmt % ( 'sched', 'cpu', 'client MB/s' )
    print

    for sched in sorted( results.keys() ):
        entries = results[ sched ]
        for cpu, bps in entries:
            pct = '%.2f%%' % ( cpu * 100 )
            mbps = bps / 1e6
            print fmt % ( sched, pct, mbps )


if __name__ == '__main__':
    setLogLevel( 'info' )
    limits = [ .45, .4, .3, .2, .1 ]
    out = bwtest( limits )
    dump( out )

########NEW FILE########
__FILENAME__ = emptynet
#!/usr/bin/python

"""
This example shows how to create an empty Mininet object
(without a topology object) and add nodes to it manually.
"""

from mininet.net import Mininet
from mininet.node import Controller
from mininet.cli import CLI
from mininet.log import setLogLevel, info

def emptyNet():

    "Create an empty network and add nodes to it."

    net = Mininet( controller=Controller )

    info( '*** Adding controller\n' )
    net.addController( 'c0' )

    info( '*** Adding hosts\n' )
    h1 = net.addHost( 'h1', ip='10.0.0.1' )
    h2 = net.addHost( 'h2', ip='10.0.0.2' )

    info( '*** Adding switch\n' )
    s3 = net.addSwitch( 's3' )

    info( '*** Creating links\n' )
    net.addLink( h1, s3 )
    net.addLink( h2, s3 )

    info( '*** Starting network\n')
    net.start()

    info( '*** Running CLI\n' )
    CLI( net )

    info( '*** Stopping network' )
    net.stop()

if __name__ == '__main__':
    setLogLevel( 'info' )
    emptyNet()

########NEW FILE########
__FILENAME__ = hwintf
#!/usr/bin/python

"""
This example shows how to add an interface (for example a real
hardware interface) to a network after the network is created.
"""

import re, sys

from mininet.cli import CLI
from mininet.log import setLogLevel, info, error
from mininet.net import Mininet
from mininet.link import Intf
from mininet.topolib import TreeTopo
from mininet.util import quietRun

def checkIntf( intf ):
    "Make sure intf exists and is not configured."
    if ( ' %s:' % intf ) not in quietRun( 'ip link show' ):
        error( 'Error:', intf, 'does not exist!\n' )
        exit( 1 )
    ips = re.findall( r'\d+\.\d+\.\d+\.\d+', quietRun( 'ifconfig ' + intf ) )
    if ips:
        error( 'Error:', intf, 'has an IP address,'
               'and is probably in use!\n' )
        exit( 1 )

if __name__ == '__main__':
    setLogLevel( 'info' )

    # try to get hw intf from the command line; by default, use eth1
    intfName = sys.argv[ 1 ] if len( sys.argv ) > 1 else 'eth1'
    info( '*** Connecting to hw intf: %s' % intfName )

    info( '*** Checking', intfName, '\n' )
    checkIntf( intfName )

    info( '*** Creating network\n' )
    net = Mininet( topo=TreeTopo( depth=1, fanout=2 ) )

    switch = net.switches[ 0 ]
    info( '*** Adding hardware interface', intfName, 'to switch',
          switch.name, '\n' )
    _intf = Intf( intfName, node=switch )

    info( '*** Note: you may need to reconfigure the interfaces for '
          'the Mininet hosts:\n', net.hosts, '\n' )

    net.start()
    CLI( net )
    net.stop()

########NEW FILE########
__FILENAME__ = limit
#!/usr/bin/python

"""
limit.py: example of using link and CPU limits
"""

from mininet.net import Mininet
from mininet.link import TCIntf
from mininet.node import CPULimitedHost
from mininet.topolib import TreeTopo
from mininet.util import custom
from mininet.log import setLogLevel


def testLinkLimit( net, bw ):
    "Run bandwidth limit test"
    print '*** Testing network %.2f Mbps bandwidth limit' % bw
    net.iperf( )


def limit( bw=10, cpu=.1 ):
    """Example/test of link and CPU bandwidth limits
       bw: interface bandwidth limit in Mbps
       cpu: cpu limit as fraction of overall CPU time"""
    intf = custom( TCIntf, bw=bw )
    myTopo = TreeTopo( depth=1, fanout=2 )
    for sched in 'rt', 'cfs':
        print '*** Testing with', sched, 'bandwidth limiting'
        host = custom( CPULimitedHost, sched=sched, cpu=cpu )
        net = Mininet( topo=myTopo, intf=intf, host=host )
        net.start()
        testLinkLimit( net, bw=bw )
        net.runCpuLimitTest( cpu=cpu )
        net.stop()

def verySimpleLimit( bw=150 ):
    "Absurdly simple limiting test"
    intf = custom( TCIntf, bw=bw )
    net = Mininet( intf=intf )
    h1, h2 = net.addHost( 'h1' ), net.addHost( 'h2' )
    net.addLink( h1, h2 )
    net.start()
    net.pingAll()
    net.iperf()
    h1.cmdPrint( 'tc -s qdisc ls dev', h1.defaultIntf() )
    h2.cmdPrint( 'tc -d class show dev', h2.defaultIntf() )
    h1.cmdPrint( 'tc -s qdisc ls dev', h1.defaultIntf() )
    h2.cmdPrint( 'tc -d class show dev', h2.defaultIntf() )
    net.stop()

if __name__ == '__main__':
    setLogLevel( 'info' )
    limit()

########NEW FILE########
__FILENAME__ = linearbandwidth
#!/usr/bin/python

"""
Test bandwidth (using iperf) on linear networks of varying size,
using both kernel and user datapaths.

We construct a network of N hosts and N-1 switches, connected as follows:

h1 <-> s1 <-> s2 .. sN-1
       |       |    |
       h2      h3   hN

WARNING: by default, the reference controller only supports 16
switches, so this test WILL NOT WORK unless you have recompiled
your controller to support 100 switches (or more.)

In addition to testing the bandwidth across varying numbers
of switches, this example demonstrates:

- creating a custom topology, LinearTestTopo
- using the ping() and iperf() tests from Mininet()
- testing both the kernel and user switches

"""

from mininet.net import Mininet
from mininet.node import UserSwitch, OVSKernelSwitch
from mininet.topo import Topo
from mininet.log import lg
from mininet.util import irange

import sys
flush = sys.stdout.flush

class LinearTestTopo( Topo ):
    "Topology for a string of N hosts and N-1 switches."

    def __init__( self, N, **params ):

        # Initialize topology
        Topo.__init__( self, **params )

        # Create switches and hosts
        hosts = [ self.addHost( 'h%s' % h )
                  for h in irange( 1, N ) ]
        switches = [ self.addSwitch( 's%s' % s )
                     for s in irange( 1, N - 1 ) ]

        # Wire up switches
        last = None
        for switch in switches:
            if last:
                self.addLink( last, switch )
            last = switch

        # Wire up hosts
        self.addLink( hosts[ 0 ], switches[ 0 ] )
        for host, switch in zip( hosts[ 1: ], switches ):
            self.addLink( host, switch )


def linearBandwidthTest( lengths ):

    "Check bandwidth at various lengths along a switch chain."

    results = {}
    switchCount = max( lengths )
    hostCount = switchCount + 1

    switches = { 'reference user': UserSwitch,
                 'Open vSwitch kernel': OVSKernelSwitch }

    topo = LinearTestTopo( hostCount )

    for datapath in switches.keys():
        print "*** testing", datapath, "datapath"
        Switch = switches[ datapath ]
        results[ datapath ] = []
        net = Mininet( topo=topo, switch=Switch )
        net.start()
        print "*** testing basic connectivity"
        for n in lengths:
            net.ping( [ net.hosts[ 0 ], net.hosts[ n ] ] )
        print "*** testing bandwidth"
        for n in lengths:
            src, dst = net.hosts[ 0 ], net.hosts[ n ]
            print "testing", src.name, "<->", dst.name,
            bandwidth = net.iperf( [ src, dst ] )
            print bandwidth
            flush()
            results[ datapath ] += [ ( n, bandwidth ) ]
        net.stop()

    for datapath in switches.keys():
        print
        print "*** Linear network results for", datapath, "datapath:"
        print
        result = results[ datapath ]
        print "SwitchCount\tiperf Results"
        for switchCount, bandwidth in result:
            print switchCount, '\t\t',
            print bandwidth[ 0 ], 'server, ', bandwidth[ 1 ], 'client'
        print
    print

if __name__ == '__main__':
    lg.setLogLevel( 'info' )
    sizes = [ 1, 10, 20, 40, 60, 80, 100 ]
    print "*** Running linearBandwidthTest", sizes
    linearBandwidthTest( sizes  )

########NEW FILE########
__FILENAME__ = miniedit
#!/usr/bin/python

"""
MiniEdit: a simple network editor for Mininet

This is a simple demonstration of how one might build a
GUI application using Mininet as the network model.

Bob Lantz, April 2010
Gregory Gee, July 2013

Controller icon from http://semlabs.co.uk/
OpenFlow icon from https://www.opennetworking.org/
"""

MINIEDIT_VERSION = '2.1.0.8.1'

from optparse import OptionParser
from Tkinter import *
from tkMessageBox import showinfo, showerror, showwarning
from subprocess import call
import tkFont
import csv
import tkFileDialog
import tkSimpleDialog
import re
import json
from distutils.version import StrictVersion
import os
import sys

if 'PYTHONPATH' in os.environ:
    sys.path = os.environ[ 'PYTHONPATH' ].split( ':' ) + sys.path

# someday: from ttk import *

from mininet.log import info, error, debug, output, setLogLevel
from mininet.net import Mininet, VERSION
from mininet.util import ipStr, netParse, ipAdd, quietRun
from mininet.util import buildTopo
from mininet.term import makeTerm, cleanUpScreens
from mininet.node import Controller, RemoteController, NOX, OVSController
from mininet.node import CPULimitedHost, Host, Node
from mininet.node import OVSKernelSwitch, OVSSwitch, UserSwitch
from mininet.link import TCLink, Intf, Link
from mininet.cli import CLI
from mininet.moduledeps import moduleDeps, pathCheck
from mininet.topo import SingleSwitchTopo, LinearTopo, SingleSwitchReversedTopo
from mininet.topolib import TreeTopo

print 'MiniEdit running against MiniNet '+VERSION
MININET_VERSION = re.sub(r'[^\d\.]', '', VERSION)
if StrictVersion(MININET_VERSION) > StrictVersion('2.0'):
    from mininet.node import IVSSwitch

TOPODEF = 'none'
TOPOS = { 'minimal': lambda: SingleSwitchTopo( k=2 ),
          'linear': LinearTopo,
          'reversed': SingleSwitchReversedTopo,
          'single': SingleSwitchTopo,
          'none': None,
          'tree': TreeTopo }
CONTROLLERDEF = 'ref'
CONTROLLERS = { 'ref': Controller,
                'ovsc': OVSController,
                'nox': NOX,
                'remote': RemoteController,
                'none': lambda name: None }

class InbandController( RemoteController ):

    def checkListening( self ):
        "Overridden to do nothing."
        return

class CustomUserSwitch(UserSwitch):
    def __init__( self, name, dpopts='--no-slicing', **kwargs ):
        UserSwitch.__init__( self, name, **kwargs )
        self.switchIP = None

    def getSwitchIP(self):
        return self.switchIP

    def setSwitchIP(self, ip):
        self.switchIP = ip

    def start( self, controllers ):
        # Call superclass constructor
        UserSwitch.start( self, controllers )
        # Set Switch IP address
        if (self.switchIP is not None):
            if not self.inNamespace:
                self.cmd( 'ifconfig', self, self.switchIP )
            else:
                self.cmd( 'ifconfig lo', self.switchIP )

class LegacyRouter( Node ):

    def __init__( self, name, inNamespace=True, **params ):
        Node.__init__( self, name, inNamespace, **params )

    def config( self, **_params ):
        if self.intfs:
            self.setParam( _params, 'setIP', ip='0.0.0.0' )
        r = Node.config( self, **_params )
        self.cmd('sysctl -w net.ipv4.ip_forward=1')
        return r

class LegacySwitch(OVSSwitch):

    def __init__( self, name, **params ):
        OVSSwitch.__init__( self, name, failMode='standalone', **params )
        self.switchIP = None

class customOvs(OVSSwitch):

    def __init__( self, name, failMode='secure', datapath='kernel', **params ):
        OVSSwitch.__init__( self, name, failMode=failMode, datapath=datapath, **params )
        self.switchIP = None

    def getSwitchIP(self):
        return self.switchIP

    def setSwitchIP(self, ip):
        self.switchIP = ip

    def getOpenFlowVersion(self):
        return self.openFlowVersions

    def setOpenFlowVersion(self, versions):
        self.openFlowVersions = []
        if versions['ovsOf10'] == '1':
            self.openFlowVersions.append('OpenFlow10')
        if versions['ovsOf11'] == '1':
            self.openFlowVersions.append('OpenFlow11')
        if versions['ovsOf12'] == '1':
            self.openFlowVersions.append('OpenFlow12')
        if versions['ovsOf13'] == '1':
            self.openFlowVersions.append('OpenFlow13')

    def configureOpenFlowVersion(self):
        if not ( 'OpenFlow11' in self.openFlowVersions or
                 'OpenFlow12' in self.openFlowVersions or
                 'OpenFlow13' in self.openFlowVersions ):
            return

        protoList = ",".join(self.openFlowVersions)
        print 'Configuring OpenFlow to '+protoList
        self.cmd( 'ovs-vsctl -- set bridge', self, 'protocols='+protoList)

    def start( self, controllers ):
        # Call superclass constructor
        OVSSwitch.start( self, controllers )
        # Set OpenFlow Versions
        self.configureOpenFlowVersion()
        # Set Switch IP address
        if (self.switchIP is not None):
            self.cmd( 'ifconfig', self, self.switchIP )

class PrefsDialog(tkSimpleDialog.Dialog):

        def __init__(self, parent, title, prefDefaults):

            self.prefValues = prefDefaults

            tkSimpleDialog.Dialog.__init__(self, parent, title)

        def body(self, master):
            self.rootFrame = master
            self.leftfieldFrame = Frame(self.rootFrame, padx=5, pady=5)
            self.leftfieldFrame.grid(row=0, column=0, sticky='nswe', columnspan=2)
            self.rightfieldFrame = Frame(self.rootFrame, padx=5, pady=5)
            self.rightfieldFrame.grid(row=0, column=2, sticky='nswe', columnspan=2)


            # Field for Base IP
            Label(self.leftfieldFrame, text="IP Base:").grid(row=0, sticky=E)
            self.ipEntry = Entry(self.leftfieldFrame)
            self.ipEntry.grid(row=0, column=1)
            ipBase =  self.prefValues['ipBase']
            self.ipEntry.insert(0, ipBase)

            # Selection of terminal type
            Label(self.leftfieldFrame, text="Default Terminal:").grid(row=1, sticky=E)
            self.terminalVar = StringVar(self.leftfieldFrame)
            self.terminalOption = OptionMenu(self.leftfieldFrame, self.terminalVar, "xterm", "gterm")
            self.terminalOption.grid(row=1, column=1, sticky=W)
            terminalType = self.prefValues['terminalType']
            self.terminalVar.set(terminalType)

            # Field for CLI
            Label(self.leftfieldFrame, text="Start CLI:").grid(row=2, sticky=E)
            self.cliStart = IntVar()
            self.cliButton = Checkbutton(self.leftfieldFrame, variable=self.cliStart)
            self.cliButton.grid(row=2, column=1, sticky=W)
            if self.prefValues['startCLI'] == '0':
                self.cliButton.deselect()
            else:
                self.cliButton.select()

            # Selection of switch type
            Label(self.leftfieldFrame, text="Default Switch:").grid(row=3, sticky=E)
            self.switchType = StringVar(self.leftfieldFrame)
            self.switchTypeMenu = OptionMenu(self.leftfieldFrame, self.switchType, "Open vSwitch", "Indigo Virtual Switch", "Userspace Switch", "Userspace Switch inNamespace")
            self.switchTypeMenu.grid(row=3, column=1, sticky=W)
            switchTypePref = self.prefValues['switchType']
            if switchTypePref == 'ivs':
                self.switchType.set("Indigo Virtual Switch")
            elif switchTypePref == 'userns':
                self.switchType.set("Userspace Switch inNamespace")
            elif switchTypePref == 'user':
                self.switchType.set("Userspace Switch")
            else:
                self.switchType.set("Open vSwitch")


            # Fields for OVS OpenFlow version
            ovsFrame= LabelFrame(self.leftfieldFrame, text='Open vSwitch', padx=5, pady=5)
            ovsFrame.grid(row=4, column=0, columnspan=2, sticky=EW)
            Label(ovsFrame, text="OpenFlow 1.0:").grid(row=0, sticky=E)
            Label(ovsFrame, text="OpenFlow 1.1:").grid(row=1, sticky=E)
            Label(ovsFrame, text="OpenFlow 1.2:").grid(row=2, sticky=E)
            Label(ovsFrame, text="OpenFlow 1.3:").grid(row=3, sticky=E)

            self.ovsOf10 = IntVar()
            self.covsOf10 = Checkbutton(ovsFrame, variable=self.ovsOf10)
            self.covsOf10.grid(row=0, column=1, sticky=W)
            if self.prefValues['openFlowVersions']['ovsOf10'] == '0':
                self.covsOf10.deselect()
            else:
                self.covsOf10.select()

            self.ovsOf11 = IntVar()
            self.covsOf11 = Checkbutton(ovsFrame, variable=self.ovsOf11)
            self.covsOf11.grid(row=1, column=1, sticky=W)
            if self.prefValues['openFlowVersions']['ovsOf11'] == '0':
                self.covsOf11.deselect()
            else:
                self.covsOf11.select()

            self.ovsOf12 = IntVar()
            self.covsOf12 = Checkbutton(ovsFrame, variable=self.ovsOf12)
            self.covsOf12.grid(row=2, column=1, sticky=W)
            if self.prefValues['openFlowVersions']['ovsOf12'] == '0':
                self.covsOf12.deselect()
            else:
                self.covsOf12.select()

            self.ovsOf13 = IntVar()
            self.covsOf13 = Checkbutton(ovsFrame, variable=self.ovsOf13)
            self.covsOf13.grid(row=3, column=1, sticky=W)
            if self.prefValues['openFlowVersions']['ovsOf13'] == '0':
                self.covsOf13.deselect()
            else:
                self.covsOf13.select()

            # Field for DPCTL listen port
            Label(self.leftfieldFrame, text="dpctl port:").grid(row=5, sticky=E)
            self.dpctlEntry = Entry(self.leftfieldFrame)
            self.dpctlEntry.grid(row=5, column=1)
            if 'dpctl' in self.prefValues:
                self.dpctlEntry.insert(0, self.prefValues['dpctl'])

            # sFlow
            sflowValues = self.prefValues['sflow']
            self.sflowFrame= LabelFrame(self.rightfieldFrame, text='sFlow Profile for Open vSwitch', padx=5, pady=5)
            self.sflowFrame.grid(row=0, column=0, columnspan=2, sticky=EW)

            Label(self.sflowFrame, text="Target:").grid(row=0, sticky=E)
            self.sflowTarget = Entry(self.sflowFrame)
            self.sflowTarget.grid(row=0, column=1)
            self.sflowTarget.insert(0, sflowValues['sflowTarget'])

            Label(self.sflowFrame, text="Sampling:").grid(row=1, sticky=E)
            self.sflowSampling = Entry(self.sflowFrame)
            self.sflowSampling.grid(row=1, column=1)
            self.sflowSampling.insert(0, sflowValues['sflowSampling'])

            Label(self.sflowFrame, text="Header:").grid(row=2, sticky=E)
            self.sflowHeader = Entry(self.sflowFrame)
            self.sflowHeader.grid(row=2, column=1)
            self.sflowHeader.insert(0, sflowValues['sflowHeader'])

            Label(self.sflowFrame, text="Polling:").grid(row=3, sticky=E)
            self.sflowPolling = Entry(self.sflowFrame)
            self.sflowPolling.grid(row=3, column=1)
            self.sflowPolling.insert(0, sflowValues['sflowPolling'])

            # NetFlow
            nflowValues = self.prefValues['netflow']
            self.nFrame= LabelFrame(self.rightfieldFrame, text='NetFlow Profile for Open vSwitch', padx=5, pady=5)
            self.nFrame.grid(row=1, column=0, columnspan=2, sticky=EW)

            Label(self.nFrame, text="Target:").grid(row=0, sticky=E)
            self.nflowTarget = Entry(self.nFrame)
            self.nflowTarget.grid(row=0, column=1)
            self.nflowTarget.insert(0, nflowValues['nflowTarget'])

            Label(self.nFrame, text="Active Timeout:").grid(row=1, sticky=E)
            self.nflowTimeout = Entry(self.nFrame)
            self.nflowTimeout.grid(row=1, column=1)
            self.nflowTimeout.insert(0, nflowValues['nflowTimeout'])

            Label(self.nFrame, text="Add ID to Interface:").grid(row=2, sticky=E)
            self.nflowAddId = IntVar()
            self.nflowAddIdButton = Checkbutton(self.nFrame, variable=self.nflowAddId)
            self.nflowAddIdButton.grid(row=2, column=1, sticky=W)
            if nflowValues['nflowAddId'] == '0':
                self.nflowAddIdButton.deselect()
            else:
                self.nflowAddIdButton.select()

            # initial focus
            return self.ipEntry

        def apply(self):
            ipBase = self.ipEntry.get()
            terminalType = self.terminalVar.get()
            startCLI = str(self.cliStart.get())
            sw = self.switchType.get()
            dpctl = self.dpctlEntry.get()

            ovsOf10 = str(self.ovsOf10.get())
            ovsOf11 = str(self.ovsOf11.get())
            ovsOf12 = str(self.ovsOf12.get())
            ovsOf13 = str(self.ovsOf13.get())

            sflowValues = {'sflowTarget':self.sflowTarget.get(),
                           'sflowSampling':self.sflowSampling.get(),
                           'sflowHeader':self.sflowHeader.get(),
                           'sflowPolling':self.sflowPolling.get()}
            nflowvalues = {'nflowTarget':self.nflowTarget.get(),
                           'nflowTimeout':self.nflowTimeout.get(),
                           'nflowAddId':str(self.nflowAddId.get())}
            self.result = {'ipBase':ipBase,
                           'terminalType':terminalType,
                           'dpctl':dpctl,
                           'sflow':sflowValues,
                           'netflow':nflowvalues,
                           'startCLI':startCLI}
            if sw == 'Indigo Virtual Switch':
                self.result['switchType'] = 'ivs'
                if StrictVersion(MININET_VERSION) < StrictVersion('2.1'):
                    self.ovsOk = False
                    showerror(title="Error",
                              message='MiniNet version 2.1+ required. You have '+VERSION+'.')
            elif sw == 'Userspace Switch':
                self.result['switchType'] = 'user'
            elif sw == 'Userspace Switch inNamespace':
                self.result['switchType'] = 'userns'
            else:
                self.result['switchType'] = 'ovs'

            self.ovsOk = True
            if ovsOf11 == "1":
                ovsVer = self.getOvsVersion()
                if StrictVersion(ovsVer) < StrictVersion('2.0'):
                    self.ovsOk = False
                    showerror(title="Error",
                              message='Open vSwitch version 2.0+ required. You have '+ovsVer+'.')
            if ovsOf12 == "1" or ovsOf13 == "1":
                ovsVer = self.getOvsVersion()
                if StrictVersion(ovsVer) < StrictVersion('1.10'):
                    self.ovsOk = False
                    showerror(title="Error",
                              message='Open vSwitch version 1.10+ required. You have '+ovsVer+'.')

            if self.ovsOk:
                self.result['openFlowVersions']={'ovsOf10':ovsOf10,
                                                 'ovsOf11':ovsOf11,
                                                 'ovsOf12':ovsOf12,
                                                 'ovsOf13':ovsOf13}
            else:
                self.result = None

        def getOvsVersion(self):
            outp = quietRun("ovs-vsctl show")
            r = r'ovs_version: "(.*)"'
            m = re.search(r, outp)
            if m is None:
                print 'Version check failed'
                return None
            else:
                print 'Open vSwitch version is '+m.group(1)
                return m.group(1)


class CustomDialog(object):

        # TODO: Fix button placement and Title and window focus lock
        def __init__(self, master, title):
            self.top=Toplevel(master)

            self.bodyFrame = Frame(self.top)
            self.bodyFrame.grid(row=0, column=0, sticky='nswe')
            self.body(self.bodyFrame)

            #return self.b # initial focus
            buttonFrame = Frame(self.top, relief='ridge', bd=3, bg='lightgrey')
            buttonFrame.grid(row=1 , column=0, sticky='nswe')

            okButton = Button(buttonFrame, width=8, text='OK', relief='groove',
                       bd=4, command=self.okAction)
            okButton.grid(row=0, column=0, sticky=E)

            canlceButton = Button(buttonFrame, width=8, text='Cancel', relief='groove',
                        bd=4, command=self.cancelAction)
            canlceButton.grid(row=0, column=1, sticky=W)

        def body(self, master):
            self.rootFrame = master

        def apply(self):
            self.top.destroy()

        def cancelAction(self):
            self.top.destroy()

        def okAction(self):
            self.apply()
            self.top.destroy()

class HostDialog(CustomDialog):

        def __init__(self, master, title, prefDefaults):

            self.prefValues = prefDefaults
            self.result = None

            CustomDialog.__init__(self, master, title)

        def body(self, master):
            self.rootFrame = master
            self.leftfieldFrame = Frame(self.rootFrame)
            self.leftfieldFrame.grid(row=0, column=0, sticky='nswe', columnspan=2)
            self.rightfieldFrame = Frame(self.rootFrame)
            self.rightfieldFrame.grid(row=0, column=2, sticky='nswe', columnspan=2)

            # Field for Hostname
            Label(self.leftfieldFrame, text="Hostname:").grid(row=0, sticky=E)
            self.hostnameEntry = Entry(self.leftfieldFrame)
            self.hostnameEntry.grid(row=0, column=1)
            if 'hostname' in self.prefValues:
                self.hostnameEntry.insert(0, self.prefValues['hostname'])

            # Field for Switch IP
            Label(self.leftfieldFrame, text="IP Address:").grid(row=1, sticky=E)
            self.ipEntry = Entry(self.leftfieldFrame)
            self.ipEntry.grid(row=1, column=1)
            if 'ip' in self.prefValues:
                self.ipEntry.insert(0, self.prefValues['ip'])

            # Field for default route
            Label(self.leftfieldFrame, text="Default Route:").grid(row=2, sticky=E)
            self.routeEntry = Entry(self.leftfieldFrame)
            self.routeEntry.grid(row=2, column=1)
            if 'defaultRoute' in self.prefValues:
                self.routeEntry.insert(0, self.prefValues['defaultRoute'])

            # Field for CPU
            Label(self.rightfieldFrame, text="Amount CPU:").grid(row=0, sticky=E)
            self.cpuEntry = Entry(self.rightfieldFrame)
            self.cpuEntry.grid(row=0, column=1)
            if 'cpu' in self.prefValues:
                self.cpuEntry.insert(0, str(self.prefValues['cpu']))
            # Selection of Scheduler
            if 'sched' in self.prefValues:
                sched =  self.prefValues['sched']
            else:
                sched = 'host'
            self.schedVar = StringVar(self.rightfieldFrame)
            self.schedOption = OptionMenu(self.rightfieldFrame, self.schedVar, "host", "cfs", "rt")
            self.schedOption.grid(row=0, column=2, sticky=W)
            self.schedVar.set(sched)

            # Selection of Cores
            Label(self.rightfieldFrame, text="Cores:").grid(row=1, sticky=E)
            self.coreEntry = Entry(self.rightfieldFrame)
            self.coreEntry.grid(row=1, column=1)
            if 'cores' in self.prefValues:
                self.coreEntry.insert(1, self.prefValues['cores'])

            # External Interfaces
            self.externalInterfaces = 0
            Label(self.rootFrame, text="External Interface:").grid(row=1, column=0, sticky=E)
            self.b = Button( self.rootFrame, text='Add', command=self.addInterface)
            self.b.grid(row=1, column=1)

            self.interfaceFrame = VerticalScrolledTable(self.rootFrame, rows=0, columns=1, title='External Interfaces')
            self.interfaceFrame.grid(row=2, column=0, sticky='nswe', columnspan=2)
            self.tableFrame = self.interfaceFrame.interior
            self.tableFrame.addRow(value=['Interface Name'], readonly=True)

            # Add defined interfaces
            externalInterfaces = []
            if 'externalInterfaces' in self.prefValues:
                externalInterfaces = self.prefValues['externalInterfaces']

            for externalInterface in externalInterfaces:
                self.tableFrame.addRow(value=[externalInterface])

            # VLAN Interfaces
            self.vlanInterfaces = 0
            Label(self.rootFrame, text="VLAN Interface:").grid(row=1, column=2, sticky=E)
            self.vlanButton = Button( self.rootFrame, text='Add', command=self.addVlanInterface)
            self.vlanButton.grid(row=1, column=3)

            self.vlanFrame = VerticalScrolledTable(self.rootFrame, rows=0, columns=2, title='VLAN Interfaces')
            self.vlanFrame.grid(row=2, column=2, sticky='nswe', columnspan=2)
            self.vlanTableFrame = self.vlanFrame.interior
            self.vlanTableFrame.addRow(value=['IP Address','VLAN ID'], readonly=True)

            vlanInterfaces = []
            if 'vlanInterfaces' in self.prefValues:
                vlanInterfaces = self.prefValues['vlanInterfaces']
            for vlanInterface in vlanInterfaces:
                self.vlanTableFrame.addRow(value=vlanInterface)

        def addVlanInterface( self ):
            self.vlanTableFrame.addRow()

        def addInterface( self ):
            self.tableFrame.addRow()

        def apply(self):
            externalInterfaces = []
            for row in range(self.tableFrame.rows):
                if (len(self.tableFrame.get(row, 0)) > 0 and
                    row > 0):
                    externalInterfaces.append(self.tableFrame.get(row, 0))
            vlanInterfaces = []
            for row in range(self.vlanTableFrame.rows):
                if (len(self.vlanTableFrame.get(row, 0)) > 0 and
                    len(self.vlanTableFrame.get(row, 1)) > 0 and
                    row > 0):
                    vlanInterfaces.append([self.vlanTableFrame.get(row, 0), self.vlanTableFrame.get(row, 1)])

            results = {'cpu': self.cpuEntry.get(),
                       'cores':self.coreEntry.get(),
                       'sched':self.schedVar.get(),
                       'hostname':self.hostnameEntry.get(),
                       'ip':self.ipEntry.get(),
                       'defaultRoute':self.routeEntry.get(),
                       'externalInterfaces':externalInterfaces,
                       'vlanInterfaces':vlanInterfaces}
            self.result = results

class SwitchDialog(CustomDialog):

        def __init__(self, master, title, prefDefaults):

            self.prefValues = prefDefaults
            self.result = None
            CustomDialog.__init__(self, master, title)

        def body(self, master):
            self.rootFrame = master

            rowCount = 0
            externalInterfaces = []
            if 'externalInterfaces' in self.prefValues:
                externalInterfaces = self.prefValues['externalInterfaces']

            self.fieldFrame = Frame(self.rootFrame)
            self.fieldFrame.grid(row=0, column=0, sticky='nswe')

            # Field for Hostname
            Label(self.fieldFrame, text="Hostname:").grid(row=rowCount, sticky=E)
            self.hostnameEntry = Entry(self.fieldFrame)
            self.hostnameEntry.grid(row=rowCount, column=1)
            self.hostnameEntry.insert(0, self.prefValues['hostname'])
            rowCount+=1

            # Field for DPID
            Label(self.fieldFrame, text="DPID:").grid(row=rowCount, sticky=E)
            self.dpidEntry = Entry(self.fieldFrame)
            self.dpidEntry.grid(row=rowCount, column=1)
            if 'dpid' in self.prefValues:
                self.dpidEntry.insert(0, self.prefValues['dpid'])
            rowCount+=1

            # Field for Netflow
            Label(self.fieldFrame, text="Enable NetFlow:").grid(row=rowCount, sticky=E)
            self.nflow = IntVar()
            self.nflowButton = Checkbutton(self.fieldFrame, variable=self.nflow)
            self.nflowButton.grid(row=rowCount, column=1, sticky=W)
            if 'netflow' in self.prefValues:
                if self.prefValues['netflow'] == '0':
                    self.nflowButton.deselect()
                else:
                    self.nflowButton.select()
            else:
                self.nflowButton.deselect()
            rowCount+=1

            # Field for sflow
            Label(self.fieldFrame, text="Enable sFlow:").grid(row=rowCount, sticky=E)
            self.sflow = IntVar()
            self.sflowButton = Checkbutton(self.fieldFrame, variable=self.sflow)
            self.sflowButton.grid(row=rowCount, column=1, sticky=W)
            if 'sflow' in self.prefValues:
                if self.prefValues['sflow'] == '0':
                    self.sflowButton.deselect()
                else:
                    self.sflowButton.select()
            else:
                self.sflowButton.deselect()
            rowCount+=1

            # Selection of switch type
            Label(self.fieldFrame, text="Switch Type:").grid(row=rowCount, sticky=E)
            self.switchType = StringVar(self.fieldFrame)
            self.switchTypeMenu = OptionMenu(self.fieldFrame, self.switchType, "Default", "Open vSwitch", "Indigo Virtual Switch", "Userspace Switch", "Userspace Switch inNamespace")
            self.switchTypeMenu.grid(row=rowCount, column=1, sticky=W)
            if 'switchType' in self.prefValues:
                switchTypePref = self.prefValues['switchType']
                if switchTypePref == 'ivs':
                    self.switchType.set("Indigo Virtual Switch")
                elif switchTypePref == 'userns':
                    self.switchType.set("Userspace Switch inNamespace")
                elif switchTypePref == 'user':
                    self.switchType.set("Userspace Switch")
                elif switchTypePref == 'ovs':
                    self.switchType.set("Open vSwitch")
                else:
                    self.switchType.set("Default")
            else:
                self.switchType.set("Default")
            rowCount+=1

            # Field for Switch IP
            Label(self.fieldFrame, text="IP Address:").grid(row=rowCount, sticky=E)
            self.ipEntry = Entry(self.fieldFrame)
            self.ipEntry.grid(row=rowCount, column=1)
            if 'switchIP' in self.prefValues:
                self.ipEntry.insert(0, self.prefValues['switchIP'])
            rowCount+=1

            # Field for DPCTL port
            Label(self.fieldFrame, text="DPCTL port:").grid(row=rowCount, sticky=E)
            self.dpctlEntry = Entry(self.fieldFrame)
            self.dpctlEntry.grid(row=rowCount, column=1)
            if 'dpctl' in self.prefValues:
                self.dpctlEntry.insert(0, self.prefValues['dpctl'])
            rowCount+=1

            # External Interfaces
            Label(self.fieldFrame, text="External Interface:").grid(row=rowCount, sticky=E)
            self.b = Button( self.fieldFrame, text='Add', command=self.addInterface)
            self.b.grid(row=rowCount, column=1)

            self.interfaceFrame = VerticalScrolledTable(self.rootFrame, rows=0, columns=1, title='External Interfaces')
            self.interfaceFrame.grid(row=2, column=0, sticky='nswe')
            self.tableFrame = self.interfaceFrame.interior

            # Add defined interfaces
            for externalInterface in externalInterfaces:
                self.tableFrame.addRow(value=[externalInterface])
            rowCount+=1

        def addInterface( self ):
            self.tableFrame.addRow()

        def defaultDpid( self ,name):
            "Derive dpid from switch name, s1 -> 1"
            try:
                dpid = int( re.findall( r'\d+', name )[ 0 ] )
                dpid = hex( dpid )[ 2: ]
                return dpid
            except IndexError:
                return None
                #raise Exception( 'Unable to derive default datapath ID - '
                #                 'please either specify a dpid or use a '
                #                 'canonical switch name such as s23.' )

        def apply(self):
            externalInterfaces = []
            for row in range(self.tableFrame.rows):
                #print 'Interface is ' + self.tableFrame.get(row, 0)
                if (len(self.tableFrame.get(row, 0)) > 0):
                    externalInterfaces.append(self.tableFrame.get(row, 0))

            dpid = self.dpidEntry.get()
            if (self.defaultDpid(self.hostnameEntry.get()) is None
               and len(dpid) == 0):
                showerror(title="Error",
                              message= 'Unable to derive default datapath ID - '
                                 'please either specify a DPID or use a '
                                 'canonical switch name such as s23.' )

            
            results = {'externalInterfaces':externalInterfaces,
                       'hostname':self.hostnameEntry.get(),
                       'dpid':dpid,
                       'sflow':str(self.sflow.get()),
                       'netflow':str(self.nflow.get()),
                       'dpctl':self.dpctlEntry.get(),
                       'switchIP':self.ipEntry.get()}
            sw = self.switchType.get()
            if sw == 'Indigo Virtual Switch':
                results['switchType'] = 'ivs'
                if StrictVersion(MININET_VERSION) < StrictVersion('2.1'):
                    self.ovsOk = False
                    showerror(title="Error",
                              message='MiniNet version 2.1+ required. You have '+VERSION+'.')
            elif sw == 'Userspace Switch inNamespace':
                results['switchType'] = 'userns'
            elif sw == 'Userspace Switch':
                results['switchType'] = 'user'
            elif sw == 'Open vSwitch':
                results['switchType'] = 'ovs'
            else:
                results['switchType'] = 'default'
            self.result = results


class VerticalScrolledTable(LabelFrame):
    """A pure Tkinter scrollable frame that actually works!

    * Use the 'interior' attribute to place widgets inside the scrollable frame
    * Construct and pack/place/grid normally
    * This frame only allows vertical scrolling
    
    """
    def __init__(self, parent, rows=2, columns=2, title=None, *args, **kw):
        LabelFrame.__init__(self, parent, text=title, padx=5, pady=5, *args, **kw)            

        # create a canvas object and a vertical scrollbar for scrolling it
        vscrollbar = Scrollbar(self, orient=VERTICAL)
        vscrollbar.pack(fill=Y, side=RIGHT, expand=FALSE)
        canvas = Canvas(self, bd=0, highlightthickness=0,
                        yscrollcommand=vscrollbar.set)
        canvas.pack(side=LEFT, fill=BOTH, expand=TRUE)
        vscrollbar.config(command=canvas.yview)

        # reset the view
        canvas.xview_moveto(0)
        canvas.yview_moveto(0)

        # create a frame inside the canvas which will be scrolled with it
        self.interior = interior = TableFrame(canvas, rows=rows, columns=columns)
        interior_id = canvas.create_window(0, 0, window=interior,
                                           anchor=NW)

        # track changes to the canvas and frame width and sync them,
        # also updating the scrollbar
        def _configure_interior(event):
            # update the scrollbars to match the size of the inner frame
            size = (interior.winfo_reqwidth(), interior.winfo_reqheight())
            canvas.config(scrollregion="0 0 %s %s" % size)
            if interior.winfo_reqwidth() != canvas.winfo_width():
                # update the canvas's width to fit the inner frame
                canvas.config(width=interior.winfo_reqwidth())
        interior.bind('<Configure>', _configure_interior)

        def _configure_canvas(event):
            if interior.winfo_reqwidth() != canvas.winfo_width():
                # update the inner frame's width to fill the canvas
                canvas.itemconfigure(interior_id, width=canvas.winfo_width())
        canvas.bind('<Configure>', _configure_canvas)

        return

class TableFrame(Frame):
    def __init__(self, parent, rows=2, columns=2):

        Frame.__init__(self, parent, background="black")
        self._widgets = []
        self.rows = rows
        self.columns = columns
        for row in range(rows):
            current_row = []
            for column in range(columns):
                label = Entry(self, borderwidth=0)
                label.grid(row=row, column=column, sticky="wens", padx=1, pady=1)
                current_row.append(label)
            self._widgets.append(current_row)

    def set(self, row, column, value):
        widget = self._widgets[row][column]
        widget.insert(0, value)

    def get(self, row, column):
        widget = self._widgets[row][column]
        return widget.get()

    def addRow( self, value=None, readonly=False ):
        #print "Adding row " + str(self.rows +1)
        current_row = []
        for column in range(self.columns):
            label = Entry(self, borderwidth=0)
            label.grid(row=self.rows, column=column, sticky="wens", padx=1, pady=1)
            if value is not None:
                label.insert(0, value[column])
            if (readonly == True):
                label.configure(state='readonly')
            current_row.append(label)
        self._widgets.append(current_row)
        self.update_idletasks()
        self.rows += 1

class LinkDialog(tkSimpleDialog.Dialog):

        def __init__(self, parent, title, linkDefaults):

            self.linkValues = linkDefaults

            tkSimpleDialog.Dialog.__init__(self, parent, title)

        def body(self, master):

            self.var = StringVar(master)
            Label(master, text="Bandwidth:").grid(row=0, sticky=E)
            self.e1 = Entry(master)
            self.e1.grid(row=0, column=1)
            Label(master, text="Mbit").grid(row=0, column=2, sticky=W)
            if 'bw' in self.linkValues:
                self.e1.insert(0,str(self.linkValues['bw']))

            Label(master, text="Delay:").grid(row=1, sticky=E)
            self.e2 = Entry(master)
            self.e2.grid(row=1, column=1)
            if 'delay' in self.linkValues:
                self.e2.insert(0, self.linkValues['delay'])

            Label(master, text="Loss:").grid(row=2, sticky=E)
            self.e3 = Entry(master)
            self.e3.grid(row=2, column=1)
            Label(master, text="%").grid(row=2, column=2, sticky=W)
            if 'loss' in self.linkValues:
                self.e3.insert(0, str(self.linkValues['loss']))

            Label(master, text="Max Queue size:").grid(row=3, sticky=E)
            self.e4 = Entry(master)
            self.e4.grid(row=3, column=1)
            if 'max_queue_size' in self.linkValues:
                self.e4.insert(0, str(self.linkValues['max_queue_size']))

            Label(master, text="Jitter:").grid(row=4, sticky=E)
            self.e5 = Entry(master)
            self.e5.grid(row=4, column=1)
            if 'jitter' in self.linkValues:
                self.e5.insert(0, self.linkValues['jitter'])

            Label(master, text="Speedup:").grid(row=5, sticky=E)
            self.e6 = Entry(master)
            self.e6.grid(row=5, column=1)
            if 'speedup' in self.linkValues:
                self.e6.insert(0, str(self.linkValues['speedup']))

            return self.e1 # initial focus

        def apply(self):
            self.result = {}
            if (len(self.e1.get()) > 0):
                self.result['bw'] = int(self.e1.get())
            if (len(self.e2.get()) > 0):
                self.result['delay'] = self.e2.get()
            if (len(self.e3.get()) > 0):
                self.result['loss'] = int(self.e3.get())
            if (len(self.e4.get()) > 0):
                self.result['max_queue_size'] = int(self.e4.get())
            if (len(self.e5.get()) > 0):
                self.result['jitter'] = self.e5.get()
            if (len(self.e6.get()) > 0):
                self.result['speedup'] = int(self.e6.get())

class ControllerDialog(tkSimpleDialog.Dialog):

        def __init__(self, parent, title, ctrlrDefaults=None):

            if ctrlrDefaults:
                self.ctrlrValues = ctrlrDefaults

            tkSimpleDialog.Dialog.__init__(self, parent, title)

        def body(self, master):

            self.var = StringVar(master)

            rowCount=0
            # Field for Hostname
            Label(master, text="Name:").grid(row=rowCount, sticky=E)
            self.hostnameEntry = Entry(master)
            self.hostnameEntry.grid(row=rowCount, column=1)
            self.hostnameEntry.insert(0, self.ctrlrValues['hostname'])
            rowCount+=1

            # Field for Remove Controller Port
            Label(master, text="Controller Port:").grid(row=rowCount, sticky=E)
            self.e2 = Entry(master)
            self.e2.grid(row=rowCount, column=1)
            self.e2.insert(0, self.ctrlrValues['remotePort'])
            rowCount+=1

            # Field for Controller Type
            Label(master, text="Controller Type:").grid(row=rowCount, sticky=E)
            controllerType = self.ctrlrValues['controllerType']
            self.o1 = OptionMenu(master, self.var, "Remote Controller", "In-Band Controller", "OpenFlow Reference", "OVS Controller")
            self.o1.grid(row=rowCount, column=1, sticky=W)
            if controllerType == 'ref':
                self.var.set("OpenFlow Reference")
            elif controllerType == 'inband':
                self.var.set("In-Band Controller")
            elif controllerType == 'remote':
                self.var.set("Remote Controller")
            else:
                self.var.set("OVS Controller")
            rowCount+=1

            # Field for Remove Controller IP
            remoteFrame= LabelFrame(master, text='Remote/In-Band Controller', padx=5, pady=5)
            remoteFrame.grid(row=rowCount, column=0, columnspan=2, sticky=W)

            Label(remoteFrame, text="IP Address:").grid(row=0, sticky=E)
            self.e1 = Entry(remoteFrame)
            self.e1.grid(row=0, column=1)
            self.e1.insert(0, self.ctrlrValues['remoteIP'])
            rowCount+=1

            return self.hostnameEntry # initial focus

        def apply(self):
            hostname = self.hostnameEntry.get()
            controllerType = self.var.get()
            remoteIP = self.e1.get()
            controllerPort = int(self.e2.get())
            self.result = { 'hostname': hostname,
                            'remoteIP': remoteIP,
                            'remotePort': controllerPort}

            if controllerType == 'Remote Controller':
                self.result['controllerType'] = 'remote'
            elif controllerType == 'In-Band Controller':
                self.result['controllerType'] = 'inband'
            elif controllerType == 'OpenFlow Reference':
                self.result['controllerType'] = 'ref'
            else:
                self.result['controllerType'] = 'ovsc'

class ToolTip(object):

    def __init__(self, widget):
        self.widget = widget
        self.tipwindow = None
        self.id = None
        self.x = self.y = 0

    def showtip(self, text):
        "Display text in tooltip window"
        self.text = text
        if self.tipwindow or not self.text:
            return
        x, y, cx, cy = self.widget.bbox("insert")
        x = x + self.widget.winfo_rootx() + 27
        y = y + cy + self.widget.winfo_rooty() +27
        self.tipwindow = tw = Toplevel(self.widget)
        tw.wm_overrideredirect(1)
        tw.wm_geometry("+%d+%d" % (x, y))
        try:
            # For Mac OS
            tw.tk.call("::tk::unsupported::MacWindowStyle",
                       "style", tw._w,
                       "help", "noActivates")
        except TclError:
            pass
        label = Label(tw, text=self.text, justify=LEFT,
                      background="#ffffe0", relief=SOLID, borderwidth=1,
                      font=("tahoma", "8", "normal"))
        label.pack(ipadx=1)

    def hidetip(self):
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()

class MiniEdit( Frame ):

    "A simple network editor for Mininet."

    def __init__( self, parent=None, cheight=600, cwidth=1000 ):

        self.defaultIpBase='10.0.0.0/8'

        self.nflowDefaults = {'nflowTarget':'',
                              'nflowTimeout':'600',
                              'nflowAddId':'0'}
        self.sflowDefaults = {'sflowTarget':'',
                              'sflowSampling':'400',
                              'sflowHeader':'128',
                              'sflowPolling':'30'}

        self.appPrefs={
            "ipBase": self.defaultIpBase,
            "startCLI": "0",
            "terminalType": 'xterm',
            "switchType": 'ovs',
            "dpctl": '',
            'sflow':self.sflowDefaults,
            'netflow':self.nflowDefaults,
            'openFlowVersions':{'ovsOf10':'1',
                                'ovsOf11':'0',
                                'ovsOf12':'0',
                                'ovsOf13':'0'}

        }


        Frame.__init__( self, parent )
        self.action = None
        self.appName = 'MiniEdit'
        self.fixedFont = tkFont.Font ( family="DejaVu Sans Mono", size="14" )

        # Style
        self.font = ( 'Geneva', 9 )
        self.smallFont = ( 'Geneva', 7 )
        self.bg = 'white'

        # Title
        self.top = self.winfo_toplevel()
        self.top.title( self.appName )

        # Menu bar
        self.createMenubar()

        # Editing canvas
        self.cheight, self.cwidth = cheight, cwidth
        self.cframe, self.canvas = self.createCanvas()

        # Toolbar
        self.controllers = {}

        # Toolbar
        self.images = miniEditImages()
        self.buttons = {}
        self.active = None
        self.tools = ( 'Select', 'Host', 'Switch', 'LegacySwitch', 'LegacyRouter', 'NetLink', 'Controller' )
        self.customColors = { 'Switch': 'darkGreen', 'Host': 'blue' }
        self.toolbar = self.createToolbar()

        # Layout
        self.toolbar.grid( column=0, row=0, sticky='nsew')
        self.cframe.grid( column=1, row=0 )
        self.columnconfigure( 1, weight=1 )
        self.rowconfigure( 0, weight=1 )
        self.pack( expand=True, fill='both' )

        # About box
        self.aboutBox = None

        # Initialize node data
        self.nodeBindings = self.createNodeBindings()
        self.nodePrefixes = { 'LegacyRouter': 'r', 'LegacySwitch': 's', 'Switch': 's', 'Host': 'h' , 'Controller': 'c'}
        self.widgetToItem = {}
        self.itemToWidget = {}

        # Initialize link tool
        self.link = self.linkWidget = None

        # Selection support
        self.selection = None

        # Keyboard bindings
        self.bind( '<Control-q>', lambda event: self.quit() )
        self.bind( '<KeyPress-Delete>', self.deleteSelection )
        self.bind( '<KeyPress-BackSpace>', self.deleteSelection )
        self.focus()

        self.hostPopup = Menu(self.top, tearoff=0)
        self.hostPopup.add_command(label='Host Options', font=self.font)
        self.hostPopup.add_separator()
        self.hostPopup.add_command(label='Properties', font=self.font, command=self.hostDetails )

        self.hostRunPopup = Menu(self.top, tearoff=0)
        self.hostRunPopup.add_command(label='Host Options', font=self.font)
        self.hostRunPopup.add_separator()
        self.hostRunPopup.add_command(label='Terminal', font=self.font, command=self.xterm )

        self.legacyRouterRunPopup = Menu(self.top, tearoff=0)
        self.legacyRouterRunPopup.add_command(label='Router Options', font=self.font)
        self.legacyRouterRunPopup.add_separator()
        self.legacyRouterRunPopup.add_command(label='Terminal', font=self.font, command=self.xterm )

        self.switchPopup = Menu(self.top, tearoff=0)
        self.switchPopup.add_command(label='Switch Options', font=self.font)
        self.switchPopup.add_separator()
        self.switchPopup.add_command(label='Properties', font=self.font, command=self.switchDetails )

        self.switchRunPopup = Menu(self.top, tearoff=0)
        self.switchRunPopup.add_command(label='Switch Options', font=self.font)
        self.switchRunPopup.add_separator()
        self.switchRunPopup.add_command(label='List bridge details', font=self.font, command=self.listBridge )

        self.linkPopup = Menu(self.top, tearoff=0)
        self.linkPopup.add_command(label='Link Options', font=self.font)
        self.linkPopup.add_separator()
        self.linkPopup.add_command(label='Properties', font=self.font, command=self.linkDetails )

        self.linkRunPopup = Menu(self.top, tearoff=0)
        self.linkRunPopup.add_command(label='Link Options', font=self.font)
        self.linkRunPopup.add_separator()
        self.linkRunPopup.add_command(label='Link Up', font=self.font, command=self.linkUp )
        self.linkRunPopup.add_command(label='Link Down', font=self.font, command=self.linkDown )

        self.controllerPopup = Menu(self.top, tearoff=0)
        self.controllerPopup.add_command(label='Controller Options', font=self.font)
        self.controllerPopup.add_separator()
        self.controllerPopup.add_command(label='Properties', font=self.font, command=self.controllerDetails )


        # Event handling initalization
        self.linkx = self.linky = self.linkItem = None
        self.lastSelection = None

        # Model initialization
        self.links = {}
        self.hostOpts = {}
        self.switchOpts = {}
        self.hostCount = 0
        self.switchCount = 0
        self.controllerCount = 0
        self.net = None

        # Close window gracefully
        Wm.wm_protocol( self.top, name='WM_DELETE_WINDOW', func=self.quit )

    def quit( self ):
        "Stop our network, if any, then quit."
        self.stop()
        Frame.quit( self )

    def createMenubar( self ):
        "Create our menu bar."

        font = self.font

        mbar = Menu( self.top, font=font )
        self.top.configure( menu=mbar )


        fileMenu = Menu( mbar, tearoff=False )
        mbar.add_cascade( label="File", font=font, menu=fileMenu )
        fileMenu.add_command( label="New", font=font, command=self.newTopology )
        fileMenu.add_command( label="Open", font=font, command=self.loadTopology )
        fileMenu.add_command( label="Save", font=font, command=self.saveTopology )
        fileMenu.add_command( label="Export", font=font, command=self.exportTopology )
        fileMenu.add_separator()
        fileMenu.add_command( label='Quit', command=self.quit, font=font )

        editMenu = Menu( mbar, tearoff=False )
        mbar.add_cascade( label="Edit", font=font, menu=editMenu )
        editMenu.add_command( label="Cut", font=font,
                              command=lambda: self.deleteSelection( None ) )
        editMenu.add_command( label="Preferences", font=font, command=self.prefDetails)

        runMenu = Menu( mbar, tearoff=False )
        mbar.add_cascade( label="Run", font=font, menu=runMenu )
        runMenu.add_command( label="Run", font=font, command=self.doRun )
        runMenu.add_command( label="Stop", font=font, command=self.doStop )
        fileMenu.add_separator()
        runMenu.add_command( label='Show OVS Summary', font=font, command=self.ovsShow )
        runMenu.add_command( label='Root Terminal', font=font, command=self.rootTerminal )

        # Application menu
        appMenu = Menu( mbar, tearoff=False )
        mbar.add_cascade( label="Help", font=font, menu=appMenu )
        appMenu.add_command( label='About MiniEdit', command=self.about,
                             font=font)
    # Canvas

    def createCanvas( self ):
        "Create and return our scrolling canvas frame."
        f = Frame( self )

        canvas = Canvas( f, width=self.cwidth, height=self.cheight,
                         bg=self.bg )

        # Scroll bars
        xbar = Scrollbar( f, orient='horizontal', command=canvas.xview )
        ybar = Scrollbar( f, orient='vertical', command=canvas.yview )
        canvas.configure( xscrollcommand=xbar.set, yscrollcommand=ybar.set )

        # Resize box
        resize = Label( f, bg='white' )

        # Layout
        canvas.grid( row=0, column=1, sticky='nsew')
        ybar.grid( row=0, column=2, sticky='ns')
        xbar.grid( row=1, column=1, sticky='ew' )
        resize.grid( row=1, column=2, sticky='nsew' )

        # Resize behavior
        f.rowconfigure( 0, weight=1 )
        f.columnconfigure( 1, weight=1 )
        f.grid( row=0, column=0, sticky='nsew' )
        f.bind( '<Configure>', lambda event: self.updateScrollRegion() )

        # Mouse bindings
        canvas.bind( '<ButtonPress-1>', self.clickCanvas )
        canvas.bind( '<B1-Motion>', self.dragCanvas )
        canvas.bind( '<ButtonRelease-1>', self.releaseCanvas )

        return f, canvas

    def updateScrollRegion( self ):
        "Update canvas scroll region to hold everything."
        bbox = self.canvas.bbox( 'all' )
        if bbox is not None:
            self.canvas.configure( scrollregion=( 0, 0, bbox[ 2 ],
                                   bbox[ 3 ] ) )

    def canvasx( self, x_root ):
        "Convert root x coordinate to canvas coordinate."
        c = self.canvas
        return c.canvasx( x_root ) - c.winfo_rootx()

    def canvasy( self, y_root ):
        "Convert root y coordinate to canvas coordinate."
        c = self.canvas
        return c.canvasy( y_root ) - c.winfo_rooty()

    # Toolbar

    def activate( self, toolName ):
        "Activate a tool and press its button."
        # Adjust button appearance
        if self.active:
            self.buttons[ self.active ].configure( relief='raised' )
        self.buttons[ toolName ].configure( relief='sunken' )
        # Activate dynamic bindings
        self.active = toolName


    def createToolTip(self, widget, text):
        toolTip = ToolTip(widget)
        def enter(event):
            toolTip.showtip(text)
        def leave(event):
            toolTip.hidetip()
        widget.bind('<Enter>', enter)
        widget.bind('<Leave>', leave)

    def createToolbar( self ):
        "Create and return our toolbar frame."

        toolbar = Frame( self )

        # Tools
        for tool in self.tools:
            cmd = ( lambda t=tool: self.activate( t ) )
            b = Button( toolbar, text=tool, font=self.smallFont, command=cmd)
            if tool in self.images:
                b.config( height=35, image=self.images[ tool ] )
                self.createToolTip(b, str(tool))
                # b.config( compound='top' )
            b.pack( fill='x' )
            self.buttons[ tool ] = b
        self.activate( self.tools[ 0 ] )

        # Spacer
        Label( toolbar, text='' ).pack()

        # Commands
        for cmd, color in [ ( 'Stop', 'darkRed' ), ( 'Run', 'darkGreen' ) ]:
            doCmd = getattr( self, 'do' + cmd )
            b = Button( toolbar, text=cmd, font=self.smallFont,
                        fg=color, command=doCmd )
            b.pack( fill='x', side='bottom' )

        return toolbar

    def doRun( self ):
        "Run command."
        self.activate( 'Select' )
        for tool in self.tools:
            self.buttons[ tool ].config( state='disabled' )
        self.start()

    def doStop( self ):
        "Stop command."
        self.stop()
        for tool in self.tools:
            self.buttons[ tool ].config( state='normal' )

    def addNode( self, node, nodeNum, x, y, name=None):
        "Add a new node to our canvas."
        if 'Switch' == node:
            self.switchCount += 1
        if 'Host' == node:
            self.hostCount += 1
        if 'Controller' == node:
            self.controllerCount += 1
        if name is None:
            name = self.nodePrefixes[ node ] + nodeNum
        self.addNamedNode(node, name, x, y)

    def addNamedNode( self, node, name, x, y):
        "Add a new node to our canvas."
        c = self.canvas
        icon = self.nodeIcon( node, name )
        item = self.canvas.create_window( x, y, anchor='c', window=icon,
                                          tags=node )
        self.widgetToItem[ icon ] = item
        self.itemToWidget[ item ] = icon
        icon.links = {}

    def loadTopology( self ):
        "Load command."
        c = self.canvas

        myFormats = [
            ('Mininet Topology','*.mn'),
            ('All Files','*'),
        ]
        f = tkFileDialog.askopenfile(filetypes=myFormats, mode='rb')
        if f == None:
            return
        self.newTopology()
        loadedTopology = eval(f.read())

        # Load application preferences
        if 'application' in loadedTopology:
            self.appPrefs = dict(self.appPrefs.items() + loadedTopology['application'].items())
            if "ovsOf10" not in self.appPrefs["openFlowVersions"]:
                self.appPrefs["openFlowVersions"]["ovsOf10"] = '0'
            if "ovsOf11" not in self.appPrefs["openFlowVersions"]:
                self.appPrefs["openFlowVersions"]["ovsOf11"] = '0'
            if "ovsOf12" not in self.appPrefs["openFlowVersions"]:
                self.appPrefs["openFlowVersions"]["ovsOf12"] = '0'
            if "ovsOf13" not in self.appPrefs["openFlowVersions"]:
                self.appPrefs["openFlowVersions"]["ovsOf13"] = '0'
            if "sflow" not in self.appPrefs:
                self.appPrefs["sflow"] = self.sflowDefaults
            if "netflow" not in self.appPrefs:
                self.appPrefs["netflow"] = self.nflowDefaults

        # Load controllers
        if ('controllers' in loadedTopology):
            if (loadedTopology['version'] == '1'):
                # This is old location of controller info
                hostname = 'c0'
                self.controllers = {}
                self.controllers[hostname] = loadedTopology['controllers']['c0']
                self.controllers[hostname]['hostname'] = hostname
                self.addNode('Controller', 0, float(30), float(30), name=hostname)
                icon = self.findWidgetByName(hostname)
                icon.bind('<Button-3>', self.do_controllerPopup )
            else:
                controllers = loadedTopology['controllers']
                for controller in controllers:
                    hostname = controller['opts']['hostname']
                    x = controller['x']
                    y = controller['y']
                    self.addNode('Controller', 0, float(x), float(y), name=hostname)
                    self.controllers[hostname] = controller['opts']
                    icon = self.findWidgetByName(hostname)
                    icon.bind('<Button-3>', self.do_controllerPopup )


        # Load hosts
        hosts = loadedTopology['hosts']
        for host in hosts:
            nodeNum = host['number']
            hostname = 'h'+nodeNum
            if 'hostname' in host['opts']:
                hostname = host['opts']['hostname']
            else:
                host['opts']['hostname'] = hostname
            if 'nodeNum' not in host['opts']:
                host['opts']['nodeNum'] = int(nodeNum)
            x = host['x']
            y = host['y']
            self.addNode('Host', nodeNum, float(x), float(y), name=hostname)
            self.hostOpts[hostname] = host['opts']
            icon = self.findWidgetByName(hostname)
            icon.bind('<Button-3>', self.do_hostPopup )

        # Load switches
        switches = loadedTopology['switches']
        for switch in switches:
            nodeNum = switch['number']
            hostname = 's'+nodeNum
            if 'controllers' not in switch['opts']:
                switch['opts']['controllers'] = []
            if 'switchType' not in switch['opts']:
                switch['opts']['switchType'] = 'default'
            if 'hostname' in switch['opts']:
                hostname = switch['opts']['hostname']
            else:
                switch['opts']['hostname'] = hostname
            if 'nodeNum' not in switch['opts']:
                switch['opts']['nodeNum'] = int(nodeNum)
            x = switch['x']
            y = switch['y']
            if switch['opts']['switchType'] == "legacyRouter":
                self.addNode('LegacyRouter', nodeNum, float(x), float(y), name=hostname)
                icon = self.findWidgetByName(hostname)
                icon.bind('<Button-3>', self.do_legacyRouterPopup )
            elif switch['opts']['switchType'] == "legacySwitch":
                self.addNode('LegacySwitch', nodeNum, float(x), float(y), name=hostname)
                icon = self.findWidgetByName(hostname)
                icon.bind('<Button-3>', self.do_legacySwitchPopup )
            else:
                self.addNode('Switch', nodeNum, float(x), float(y), name=hostname)
                icon = self.findWidgetByName(hostname)
                icon.bind('<Button-3>', self.do_switchPopup )
            self.switchOpts[hostname] = switch['opts']

            # create links to controllers
            if (int(loadedTopology['version']) > 1):
                controllers = self.switchOpts[hostname]['controllers']
                for controller in controllers:
                    dest = self.findWidgetByName(controller)
                    dx, dy = self.canvas.coords( self.widgetToItem[ dest ] )
                    self.link = self.canvas.create_line(float(x),
                                                        float(y),
                                                        dx,
                                                        dy,
                                                        width=4,
                                                        fill='red',
                                                        dash=(6, 4, 2, 4),
                                                        tag='link' )
                    c.itemconfig(self.link, tags=c.gettags(self.link)+('control',))
                    self.addLink( icon, dest, linktype='control' )
                    self.createControlLinkBindings()
                    self.link = self.linkWidget = None
            else:
                dest = self.findWidgetByName('c0')
                dx, dy = self.canvas.coords( self.widgetToItem[ dest ] )
                self.link = self.canvas.create_line(float(x),
                                                    float(y),
                                                    dx,
                                                    dy,
                                                    width=4,
                                                    fill='red',
                                                    dash=(6, 4, 2, 4),
                                                    tag='link' )
                c.itemconfig(self.link, tags=c.gettags(self.link)+('control',))
                self.addLink( icon, dest, linktype='control' )
                self.createControlLinkBindings()
                self.link = self.linkWidget = None

        # Load links
        links = loadedTopology['links']
        for link in links:
            srcNode = link['src']
            src = self.findWidgetByName(srcNode)
            sx, sy = self.canvas.coords( self.widgetToItem[ src ] )

            destNode = link['dest']
            dest = self.findWidgetByName(destNode)
            dx, dy = self.canvas.coords( self.widgetToItem[ dest]  )

            self.link = self.canvas.create_line( sx, sy, dx, dy, width=4,
                                             fill='blue', tag='link' )
            c.itemconfig(self.link, tags=c.gettags(self.link)+('data',))
            self.addLink( src, dest, linkopts=link['opts'] )
            self.createDataLinkBindings()
            self.link = self.linkWidget = None

        f.close

    def findWidgetByName( self, name ):
        for widget in self.widgetToItem:
            if name ==  widget[ 'text' ]:
                return widget

    def newTopology( self ):
        "New command."
        for widget in self.widgetToItem.keys():
            self.deleteItem( self.widgetToItem[ widget ] )
        self.hostCount = 0
        self.switchCount = 0
        self.controllerCount = 0
        self.links = {}
        self.hostOpts = {}
        self.switchOpts = {}
        self.controllers = {}
        self.appPrefs["ipBase"]= self.defaultIpBase

    def saveTopology( self ):
        "Save command."
        myFormats = [
            ('Mininet Topology','*.mn'),
            ('All Files','*'),
        ]

        savingDictionary = {}
        fileName = tkFileDialog.asksaveasfilename(filetypes=myFormats ,title="Save the topology as...")
        if len(fileName ) > 0:
            # Save Application preferences
            savingDictionary['version'] = '2'

            # Save Switches and Hosts
            hostsToSave = []
            switchesToSave = []
            controllersToSave = []
            for widget in self.widgetToItem:
                name = widget[ 'text' ]
                tags = self.canvas.gettags( self.widgetToItem[ widget ] )
                x1, y1 = self.canvas.coords( self.widgetToItem[ widget ] )
                if 'Switch' in tags or 'LegacySwitch' in tags or 'LegacyRouter' in tags:
                    nodeNum = self.switchOpts[name]['nodeNum']
                    nodeToSave = {'number':str(nodeNum),
                                  'x':str(x1),
                                  'y':str(y1),
                                  'opts':self.switchOpts[name] }
                    switchesToSave.append(nodeToSave)
                elif 'Host' in tags:
                    nodeNum = self.hostOpts[name]['nodeNum']
                    nodeToSave = {'number':str(nodeNum),
                                  'x':str(x1),
                                  'y':str(y1),
                                  'opts':self.hostOpts[name] }
                    hostsToSave.append(nodeToSave)
                elif 'Controller' in tags:
                    nodeToSave = {'x':str(x1),
                                  'y':str(y1),
                                  'opts':self.controllers[name] }
                    controllersToSave.append(nodeToSave)
                else:
                    raise Exception( "Cannot create mystery node: " + name )
            savingDictionary['hosts'] = hostsToSave
            savingDictionary['switches'] = switchesToSave
            savingDictionary['controllers'] = controllersToSave

            # Save Links
            linksToSave = []
            for link in self.links.values():
                src = link['src']
                dst = link['dest']
                linkopts = link['linkOpts']

                srcName, dstName = src[ 'text' ], dst[ 'text' ]
                linkToSave = {'src':srcName,
                              'dest':dstName,
                              'opts':linkopts}
                if link['type'] == 'data':
                    linksToSave.append(linkToSave)
            savingDictionary['links'] = linksToSave

            # Save Application preferences
            savingDictionary['application'] = self.appPrefs

            try:
                f = open(fileName, 'wb')
                #f.write(str(savingDictionary))
                f.write(json.dumps(savingDictionary, sort_keys=True, indent=4, separators=(',', ': ')))
            except Exception as er:
                print er
            finally:
                f.close()

    def exportTopology( self ):
        "Export command."
        myFormats = [
            ('Mininet Custom Topology','*.py'),
            ('All Files','*'),
        ]

        fileName = tkFileDialog.asksaveasfilename(filetypes=myFormats ,title="Export the topology as...")
        if len(fileName ) > 0:
            #print "Now saving under %s" % fileName
            f = open(fileName, 'wb')

            f.write("#!/usr/bin/python\n")
            f.write("\n")
            f.write("from mininet.net import Mininet\n")
            f.write("from mininet.node import Controller, RemoteController, OVSController\n")
            f.write("from mininet.node import CPULimitedHost, Host, Node\n")
            f.write("from mininet.node import OVSKernelSwitch, UserSwitch\n")
            if StrictVersion(MININET_VERSION) > StrictVersion('2.0'):
                f.write("from mininet.node import IVSSwitch\n")
            f.write("from mininet.cli import CLI\n")
            f.write("from mininet.log import setLogLevel, info\n")
            f.write("from mininet.link import TCLink, Intf\n")

            inBandCtrl = False
            hasLegacySwitch = False
            for widget in self.widgetToItem:
                name = widget[ 'text' ]
                tags = self.canvas.gettags( self.widgetToItem[ widget ] )

                if 'Controller' in tags:
                    opts = self.controllers[name]
                    controllerType = opts['controllerType']
                    if controllerType == 'inband':
                        inBandCtrl = True

            if inBandCtrl == True:
                f.write("\n")
                f.write("class InbandController( RemoteController ):\n")
                f.write("\n")
                f.write("    def checkListening( self ):\n")
                f.write("        \"Overridden to do nothing.\"\n")
                f.write("        return\n")

            f.write("\n")
            f.write("def myNetwork():\n")
            f.write("\n")
            f.write("    net = Mininet( topo=None,\n")
            if len(self.appPrefs['dpctl']) > 0:
                f.write("                   listenPort="+self.appPrefs['dpctl']+",\n")
            f.write("                   build=False,\n")
            f.write("                   ipBase='"+self.appPrefs['ipBase']+"')\n")
            f.write("\n")
            f.write("    info( '*** Adding controller\\n' )\n")
            for widget in self.widgetToItem:
                name = widget[ 'text' ]
                tags = self.canvas.gettags( self.widgetToItem[ widget ] )
    
                if 'Controller' in tags:
                    opts = self.controllers[name]
                    controllerType = opts['controllerType']
                    controllerIP = opts['remoteIP']
                    controllerPort = opts['remotePort']

    
                    f.write("    "+name+"=net.addController(name='"+name+"',\n")
        
                    if controllerType == 'remote':
                        f.write("                      controller=RemoteController,\n")
                        f.write("                      ip='"+controllerIP+"',\n")
                    elif controllerType == 'inband':
                        f.write("                      controller=InbandController,\n")
                        f.write("                      ip='"+controllerIP+"',\n")
                    elif controllerType == 'ovsc':
                        f.write("                      controller=OVSController,\n")
                    else:
                        f.write("                      controller=Controller,\n")
        
                    f.write("                      port="+str(controllerPort)+")\n")
                    f.write("\n")

            # Save Switches and Hosts
            f.write("    info( '*** Add switches\\n')\n")
            for widget in self.widgetToItem:
                name = widget[ 'text' ]
                tags = self.canvas.gettags( self.widgetToItem[ widget ] )
                if 'LegacyRouter' in tags:
                    f.write("    "+name+" = net.addHost('"+name+"', cls=Node, ip='0.0.0.0')\n")
                    f.write("    "+name+".cmd('sysctl -w net.ipv4.ip_forward=1')\n")
                if 'LegacySwitch' in tags:
                    f.write("    "+name+" = net.addSwitch('"+name+"', cls=OVSKernelSwitch, failMode='standalone')\n")
                if 'Switch' in tags:
                    opts = self.switchOpts[name]
                    nodeNum = opts['nodeNum']
                    f.write("    "+name+" = net.addSwitch('"+name+"'")
                    if opts['switchType'] == 'default':
                        if self.appPrefs['switchType'] == 'ivs':
                            f.write(", cls=IVSSwitch")
                        elif self.appPrefs['switchType'] == 'user':
                            f.write(", cls=UserSwitch")
                        elif self.appPrefs['switchType'] == 'userns':
                            f.write(", cls=UserSwitch, inNamespace=True")
                        else:
                            f.write(", cls=OVSKernelSwitch")
                    elif opts['switchType'] == 'ivs':
                        f.write(", cls=IVSSwitch")
                    elif opts['switchType'] == 'user':
                        f.write(", cls=UserSwitch")
                    elif opts['switchType'] == 'userns':
                        f.write(", cls=UserSwitch, inNamespace=True")
                    else:
                        f.write(", cls=OVSKernelSwitch")
                    if 'dpctl' in opts:
                        f.write(", listenPort="+opts['dpctl'])
                    if 'dpid' in opts:
                        f.write(", dpid='"+opts['dpid']+"'")
                    f.write(")\n")
                    if ('externalInterfaces' in opts):
                        for extInterface in opts['externalInterfaces']:
                            f.write("    Intf( '"+extInterface+"', node="+name+" )\n")

            f.write("\n")
            f.write("    info( '*** Add hosts\\n')\n")
            for widget in self.widgetToItem:
                name = widget[ 'text' ]
                tags = self.canvas.gettags( self.widgetToItem[ widget ] )
                if 'Host' in tags:
                    opts = self.hostOpts[name]
                    ip = None
                    defaultRoute = None
                    if 'defaultRoute' in opts and len(opts['defaultRoute']) > 0:
                        defaultRoute = "'via "+opts['defaultRoute']+"'"
                    else:
                        defaultRoute = 'None'
                    if 'ip' in opts and len(opts['ip']) > 0:
                        ip = opts['ip']
                    else:
                        nodeNum = self.hostOpts[name]['nodeNum']
                        ipBaseNum, prefixLen = netParse( self.appPrefs['ipBase'] )
                        ip = ipAdd(i=nodeNum, prefixLen=prefixLen, ipBaseNum=ipBaseNum)

                    if 'cores' in opts or 'cpu' in opts:
                        f.write("    "+name+" = net.addHost('"+name+"', cls=CPULimitedHost, ip='"+ip+"', defaultRoute="+defaultRoute+")\n")
                        if 'cores' in opts:
                            f.write("    "+name+".setCPUs(cores='"+opts['cores']+"')\n")
                        if 'cpu' in opts:
                            f.write("    "+name+".setCPUFrac(f="+str(opts['cpu'])+", sched='"+opts['sched']+"')\n")
                    else:
                        f.write("    "+name+" = net.addHost('"+name+"', cls=Host, ip='"+ip+"', defaultRoute="+defaultRoute+")\n")
                    if ('externalInterfaces' in opts):
                        for extInterface in opts['externalInterfaces']:
                            f.write("    Intf( '"+extInterface+"', node="+name+" )\n")
            f.write("\n")

            # Save Links
            f.write("    info( '*** Add links\\n')\n")
            for key,linkDetail in self.links.iteritems():
              tags = self.canvas.gettags(key)
              if 'data' in tags:
                optsExist = False
                src = linkDetail['src']
                dst = linkDetail['dest']
                linkopts = linkDetail['linkOpts']
                srcName, dstName = src[ 'text' ], dst[ 'text' ]
                bw = ''
                delay = ''
                loss = ''
                max_queue_size = ''
                linkOpts = "{"
                if 'bw' in linkopts:
                    bw =  linkopts['bw']
                    linkOpts = linkOpts + "'bw':"+str(bw)
                    optsExist = True
                if 'delay' in linkopts:
                    delay =  linkopts['delay']
                    if optsExist:
                        linkOpts = linkOpts + ","
                    linkOpts = linkOpts + "'delay':'"+linkopts['delay']+"'"
                    optsExist = True
                if 'loss' in linkopts:
                    if optsExist:
                        linkOpts = linkOpts + ","
                    linkOpts = linkOpts + "'loss':"+str(linkopts['loss'])
                    optsExist = True
                if 'max_queue_size' in linkopts:
                    if optsExist:
                        linkOpts = linkOpts + ","
                    linkOpts = linkOpts + "'max_queue_size':"+str(linkopts['max_queue_size'])
                    optsExist = True
                if 'jitter' in linkopts:
                    if optsExist:
                        linkOpts = linkOpts + ","
                    linkOpts = linkOpts + "'jitter':'"+linkopts['jitter']+"'"
                    optsExist = True
                if 'speedup' in linkopts:
                    if optsExist:
                        linkOpts = linkOpts + ","
                    linkOpts = linkOpts + "'speedup':"+str(linkopts['speedup'])
                    optsExist = True

                linkOpts = linkOpts + "}"
                if optsExist:
                    f.write("    "+srcName+dstName+" = "+linkOpts+"\n")
                f.write("    net.addLink("+srcName+", "+dstName)
                if optsExist:
                    f.write(", link=TCLink , **"+srcName+dstName)
                f.write(")\n")

            f.write("\n")
            f.write("    info( '*** Starting network\\n')\n")
            f.write("    net.build()\n")

            f.write("    info( '*** Starting controllers\\n')\n")
            f.write("    for controller in net.controllers:\n")
            f.write("        controller.start()\n")
            f.write("\n")

            f.write("    info( '*** Starting switches\\n')\n")
            for widget in self.widgetToItem:
                name = widget[ 'text' ]
                tags = self.canvas.gettags( self.widgetToItem[ widget ] )
                if 'Switch' in tags or 'LegacySwitch' in tags:
                    opts = self.switchOpts[name]
                    ctrlList = ",".join(opts['controllers'])
                    f.write("    net.get('"+name+"').start(["+ctrlList+"])\n")

            f.write("\n")

            f.write("    info( '*** Configuring switches\\n')\n")
            for widget in self.widgetToItem:
                name = widget[ 'text' ]
                tags = self.canvas.gettags( self.widgetToItem[ widget ] )
                if 'Switch' in tags:
                    opts = self.switchOpts[name]
                    if opts['switchType'] == 'default':
                        if self.appPrefs['switchType'] == 'user':
                            if ('switchIP' in opts):
                                if (len(opts['switchIP'])>0):
                                    f.write("    "+name+".cmd('ifconfig "+name+" "+opts['switchIP']+"')\n")
                        elif self.appPrefs['switchType'] == 'userns':
                            if ('switchIP' in opts):
                                if (len(opts['switchIP'])>0):
                                    f.write("    "+name+".cmd('ifconfig lo "+opts['switchIP']+"')\n")
                        elif self.appPrefs['switchType'] == 'ovs':
                            if ('switchIP' in opts):
                                if (len(opts['switchIP'])>0):
                                    f.write("    "+name+".cmd('ifconfig "+name+" "+opts['switchIP']+"')\n")
                    elif opts['switchType'] == 'user':
                        if ('switchIP' in opts):
                            if (len(opts['switchIP'])>0):
                                f.write("    "+name+".cmd('ifconfig "+name+" "+opts['switchIP']+"')\n")
                    elif opts['switchType'] == 'userns':
                        if ('switchIP' in opts):
                            if (len(opts['switchIP'])>0):
                                f.write("    "+name+".cmd('ifconfig lo "+opts['switchIP']+"')\n")
                    elif opts['switchType'] == 'ovs':
                        if ('switchIP' in opts):
                            if (len(opts['switchIP'])>0):
                                f.write("    "+name+".cmd('ifconfig "+name+" "+opts['switchIP']+"')\n")
            for widget in self.widgetToItem:
                name = widget[ 'text' ]
                tags = self.canvas.gettags( self.widgetToItem[ widget ] )
                if 'Host' in tags:
                    opts = self.hostOpts[name]
                    # Attach vlan interfaces
                    if ('vlanInterfaces' in opts):
                        for vlanInterface in opts['vlanInterfaces']:
                            f.write("    "+name+".cmd('vconfig add "+name+"-eth0 "+vlanInterface[1]+"')\n")
                            f.write("    "+name+".cmd('ifconfig "+name+"-eth0."+vlanInterface[1]+" "+vlanInterface[0]+"')\n")


            f.write("\n")
            f.write("    CLI(net)\n")
            f.write("    net.stop()\n")
            f.write("\n")
            f.write("if __name__ == '__main__':\n")
            f.write("    setLogLevel( 'info' )\n")
            f.write("    myNetwork()\n")
            f.write("\n")


            f.close()


    # Generic canvas handler
    #
    # We could have used bindtags, as in nodeIcon, but
    # the dynamic approach used here
    # may actually require less code. In any case, it's an
    # interesting introspection-based alternative to bindtags.

    def canvasHandle( self, eventName, event ):
        "Generic canvas event handler"
        if self.active is None:
            return
        toolName = self.active
        handler = getattr( self, eventName + toolName, None )
        if handler is not None:
            handler( event )

    def clickCanvas( self, event ):
        "Canvas click handler."
        self.canvasHandle( 'click', event )

    def dragCanvas( self, event ):
        "Canvas drag handler."
        self.canvasHandle( 'drag', event )

    def releaseCanvas( self, event ):
        "Canvas mouse up handler."
        self.canvasHandle( 'release', event )

    # Currently the only items we can select directly are
    # links. Nodes are handled by bindings in the node icon.

    def findItem( self, x, y ):
        "Find items at a location in our canvas."
        items = self.canvas.find_overlapping( x, y, x, y )
        if len( items ) == 0:
            return None
        else:
            return items[ 0 ]

    # Canvas bindings for Select, Host, Switch and Link tools

    def clickSelect( self, event ):
        "Select an item."
        self.selectItem( self.findItem( event.x, event.y ) )

    def deleteItem( self, item ):
        "Delete an item."
        # Don't delete while network is running
        if self.buttons[ 'Select' ][ 'state' ] == 'disabled':
            return
        # Delete from model
        if item in self.links:
            self.deleteLink( item )
        if item in self.itemToWidget:
            self.deleteNode( item )
        # Delete from view
        self.canvas.delete( item )

    def deleteSelection( self, _event ):
        "Delete the selected item."
        if self.selection is not None:
            self.deleteItem( self.selection )
        self.selectItem( None )

    def nodeIcon( self, node, name ):
        "Create a new node icon."
        icon = Button( self.canvas, image=self.images[ node ],
                       text=name, compound='top' )
        # Unfortunately bindtags wants a tuple
        bindtags = [ str( self.nodeBindings ) ]
        bindtags += list( icon.bindtags() )
        icon.bindtags( tuple( bindtags ) )
        return icon

    def newNode( self, node, event ):
        "Add a new node to our canvas."
        c = self.canvas
        x, y = c.canvasx( event.x ), c.canvasy( event.y )
        name = self.nodePrefixes[ node ]
        if 'Switch' == node:
            self.switchCount += 1
            name = self.nodePrefixes[ node ] + str( self.switchCount )
            self.switchOpts[name] = {}
            self.switchOpts[name]['nodeNum']=self.switchCount
            self.switchOpts[name]['hostname']=name
            self.switchOpts[name]['switchType']='default'
            self.switchOpts[name]['controllers']=[]
        if 'LegacyRouter' == node:
            self.switchCount += 1
            name = self.nodePrefixes[ node ] + str( self.switchCount )
            self.switchOpts[name] = {}
            self.switchOpts[name]['nodeNum']=self.switchCount
            self.switchOpts[name]['hostname']=name
            self.switchOpts[name]['switchType']='legacyRouter'
        if 'LegacySwitch' == node:
            self.switchCount += 1
            name = self.nodePrefixes[ node ] + str( self.switchCount )
            self.switchOpts[name] = {}
            self.switchOpts[name]['nodeNum']=self.switchCount
            self.switchOpts[name]['hostname']=name
            self.switchOpts[name]['switchType']='legacySwitch'
            self.switchOpts[name]['controllers']=[]
        if 'Host' == node:
            self.hostCount += 1
            name = self.nodePrefixes[ node ] + str( self.hostCount )
            self.hostOpts[name] = {'sched':'host'}
            self.hostOpts[name]['nodeNum']=self.hostCount
            self.hostOpts[name]['hostname']=name
        if 'Controller' == node:
            name = self.nodePrefixes[ node ] + str( self.controllerCount )
            ctrlr = { 'controllerType': 'ref',
                      'hostname': name,
                      'remoteIP': '127.0.0.1',
                      'remotePort': 6633}
            self.controllers[name] = ctrlr
            # We want to start controller count at 0
            self.controllerCount += 1

        icon = self.nodeIcon( node, name )
        item = self.canvas.create_window( x, y, anchor='c', window=icon,
                                          tags=node )
        self.widgetToItem[ icon ] = item
        self.itemToWidget[ item ] = icon
        self.selectItem( item )
        icon.links = {}
        if 'Switch' == node:
            icon.bind('<Button-3>', self.do_switchPopup )
        if 'LegacyRouter' == node:
            icon.bind('<Button-3>', self.do_legacyRouterPopup )
        if 'LegacySwitch' == node:
            icon.bind('<Button-3>', self.do_legacySwitchPopup )
        if 'Host' == node:
            icon.bind('<Button-3>', self.do_hostPopup )
        if 'Controller' == node:
            icon.bind('<Button-3>', self.do_controllerPopup )

    def clickController( self, event ):
        "Add a new Controller to our canvas."
        self.newNode( 'Controller', event )

    def clickHost( self, event ):
        "Add a new host to our canvas."
        self.newNode( 'Host', event )

    def clickLegacyRouter( self, event ):
        "Add a new switch to our canvas."
        self.newNode( 'LegacyRouter', event )

    def clickLegacySwitch( self, event ):
        "Add a new switch to our canvas."
        self.newNode( 'LegacySwitch', event )

    def clickSwitch( self, event ):
        "Add a new switch to our canvas."
        self.newNode( 'Switch', event )

    def dragNetLink( self, event ):
        "Drag a link's endpoint to another node."
        if self.link is None:
            return
        # Since drag starts in widget, we use root coords
        x = self.canvasx( event.x_root )
        y = self.canvasy( event.y_root )
        c = self.canvas
        c.coords( self.link, self.linkx, self.linky, x, y )

    def releaseNetLink( self, _event ):
        "Give up on the current link."
        if self.link is not None:
            self.canvas.delete( self.link )
        self.linkWidget = self.linkItem = self.link = None

    # Generic node handlers

    def createNodeBindings( self ):
        "Create a set of bindings for nodes."
        bindings = {
            '<ButtonPress-1>': self.clickNode,
            '<B1-Motion>': self.dragNode,
            '<ButtonRelease-1>': self.releaseNode,
            '<Enter>': self.enterNode,
            '<Leave>': self.leaveNode
        }
        l = Label()  # lightweight-ish owner for bindings
        for event, binding in bindings.items():
            l.bind( event, binding )
        return l

    def selectItem( self, item ):
        "Select an item and remember old selection."
        self.lastSelection = self.selection
        self.selection = item

    def enterNode( self, event ):
        "Select node on entry."
        self.selectNode( event )

    def leaveNode( self, _event ):
        "Restore old selection on exit."
        self.selectItem( self.lastSelection )

    def clickNode( self, event ):
        "Node click handler."
        if self.active is 'NetLink':
            self.startLink( event )
        else:
            self.selectNode( event )
        return 'break'

    def dragNode( self, event ):
        "Node drag handler."
        if self.active is 'NetLink':
            self.dragNetLink( event )
        else:
            self.dragNodeAround( event )

    def releaseNode( self, event ):
        "Node release handler."
        if self.active is 'NetLink':
            self.finishLink( event )

    # Specific node handlers

    def selectNode( self, event ):
        "Select the node that was clicked on."
        item = self.widgetToItem.get( event.widget, None )
        self.selectItem( item )

    def dragNodeAround( self, event ):
        "Drag a node around on the canvas."
        c = self.canvas
        # Convert global to local coordinates;
        # Necessary since x, y are widget-relative
        x = self.canvasx( event.x_root )
        y = self.canvasy( event.y_root )
        w = event.widget
        # Adjust node position
        item = self.widgetToItem[ w ]
        c.coords( item, x, y )
        # Adjust link positions
        for dest in w.links:
            link = w.links[ dest ]
            item = self.widgetToItem[ dest ]
            x1, y1 = c.coords( item )
            c.coords( link, x, y, x1, y1 )
        self.updateScrollRegion()

    def createControlLinkBindings( self ):
        "Create a set of bindings for nodes."
        # Link bindings
        # Selection still needs a bit of work overall
        # Callbacks ignore event

        def select( _event, link=self.link ):
            "Select item on mouse entry."
            self.selectItem( link )

        def highlight( _event, link=self.link ):
            "Highlight item on mouse entry."
            self.selectItem( link )
            self.canvas.itemconfig( link, fill='green' )

        def unhighlight( _event, link=self.link ):
            "Unhighlight item on mouse exit."
            self.canvas.itemconfig( link, fill='red' )
            #self.selectItem( None )

        self.canvas.tag_bind( self.link, '<Enter>', highlight )
        self.canvas.tag_bind( self.link, '<Leave>', unhighlight )
        self.canvas.tag_bind( self.link, '<ButtonPress-1>', select )

    def createDataLinkBindings( self ):
        "Create a set of bindings for nodes."
        # Link bindings
        # Selection still needs a bit of work overall
        # Callbacks ignore event

        def select( _event, link=self.link ):
            "Select item on mouse entry."
            self.selectItem( link )

        def highlight( _event, link=self.link ):
            "Highlight item on mouse entry."
            self.selectItem( link )
            self.canvas.itemconfig( link, fill='green' )

        def unhighlight( _event, link=self.link ):
            "Unhighlight item on mouse exit."
            self.canvas.itemconfig( link, fill='blue' )
            #self.selectItem( None )

        self.canvas.tag_bind( self.link, '<Enter>', highlight )
        self.canvas.tag_bind( self.link, '<Leave>', unhighlight )
        self.canvas.tag_bind( self.link, '<ButtonPress-1>', select )
        self.canvas.tag_bind( self.link, '<Button-3>', self.do_linkPopup )


    def startLink( self, event ):
        "Start a new link."
        if event.widget not in self.widgetToItem:
            # Didn't click on a node
            return

        w = event.widget
        item = self.widgetToItem[ w ]
        x, y = self.canvas.coords( item )
        self.link = self.canvas.create_line( x, y, x, y, width=4,
                                             fill='blue', tag='link' )
        self.linkx, self.linky = x, y
        self.linkWidget = w
        self.linkItem = item


    def finishLink( self, event ):
        "Finish creating a link"
        if self.link is None:
            return
        source = self.linkWidget
        c = self.canvas
        # Since we dragged from the widget, use root coords
        x, y = self.canvasx( event.x_root ), self.canvasy( event.y_root )
        target = self.findItem( x, y )
        dest = self.itemToWidget.get( target, None )
        if ( source is None or dest is None or source == dest
                or dest in source.links or source in dest.links ):
            self.releaseNetLink( event )
            return
        # For now, don't allow hosts to be directly linked
        stags = self.canvas.gettags( self.widgetToItem[ source ] )
        dtags = self.canvas.gettags( target )
        if (('Host' in stags and 'Host' in dtags) or
           ('Controller' in dtags and 'LegacyRouter' in stags) or
           ('Controller' in stags and 'LegacyRouter' in dtags) or
           ('Controller' in dtags and 'LegacySwitch' in stags) or
           ('Controller' in stags and 'LegacySwitch' in dtags) or
           ('Controller' in dtags and 'Host' in stags) or
           ('Controller' in stags and 'Host' in dtags) or
           ('Controller' in stags and 'Controller' in dtags)):
            self.releaseNetLink( event )
            return

        # Set link type
        linkType='data'
        if 'Controller' in stags or 'Controller' in dtags:
            linkType='control'
            c.itemconfig(self.link, dash=(6, 4, 2, 4), fill='red')
            self.createControlLinkBindings()
        else:
            linkType='data'
            self.createDataLinkBindings()
        c.itemconfig(self.link, tags=c.gettags(self.link)+(linkType,))

        x, y = c.coords( target )
        c.coords( self.link, self.linkx, self.linky, x, y )
        self.addLink( source, dest, linktype=linkType )
        if linkType == 'control':
            controllerName = ''
            switchName = ''
            if 'Controller' in stags:
                controllerName = source[ 'text' ]
                switchName = dest[ 'text' ]
            else:
                controllerName = dest[ 'text' ]
                switchName = source[ 'text' ]

            self.switchOpts[switchName]['controllers'].append(controllerName)

        # We're done
        self.link = self.linkWidget = None

    # Menu handlers

    def about( self ):
        "Display about box."
        about = self.aboutBox
        if about is None:
            bg = 'white'
            about = Toplevel( bg='white' )
            about.title( 'About' )
            info = self.appName + ': a simple network editor for MiniNet'
            version = 'MiniEdit '+MINIEDIT_VERSION
            author = 'Originally by: Bob Lantz <rlantz@cs>, April 2010'
            enhancements = 'Enhancements by: Gregory Gee, Since July 2013'
            www = 'http://gregorygee.wordpress.com/category/miniedit/'
            line1 = Label( about, text=info, font='Helvetica 10 bold', bg=bg )
            line2 = Label( about, text=version, font='Helvetica 9', bg=bg )
            line3 = Label( about, text=author, font='Helvetica 9', bg=bg )
            line4 = Label( about, text=enhancements, font='Helvetica 9', bg=bg )
            line5 = Entry( about, font='Helvetica 9', bg=bg, width=len(www), justify=CENTER )
            line5.insert(0, www)
            line5.configure(state='readonly')
            line1.pack( padx=20, pady=10 )
            line2.pack(pady=10 )
            line3.pack(pady=10 )
            line4.pack(pady=10 )
            line5.pack(pady=10 )
            hide = ( lambda about=about: about.withdraw() )
            self.aboutBox = about
            # Hide on close rather than destroying window
            Wm.wm_protocol( about, name='WM_DELETE_WINDOW', func=hide )
        # Show (existing) window
        about.deiconify()

    def createToolImages( self ):
        "Create toolbar (and icon) images."

    def checkIntf( self, intf ):
        "Make sure intf exists and is not configured."
        if ( ' %s:' % intf ) not in quietRun( 'ip link show' ):
            showerror(title="Error",
                      message='External interface ' +intf + ' does not exist! Skipping.')
            return False
        ips = re.findall( r'\d+\.\d+\.\d+\.\d+', quietRun( 'ifconfig ' + intf ) )
        if ips:
            showerror(title="Error",
                      message= intf + ' has an IP address and is probably in use! Skipping.' )
            return False
        return True

    def hostDetails( self, _ignore=None ):
        if ( self.selection is None or
             self.net is not None or
             self.selection not in self.itemToWidget ):
            return
        widget = self.itemToWidget[ self.selection ]
        name = widget[ 'text' ]
        tags = self.canvas.gettags( self.selection )
        if 'Host' not in tags:
            return

        prefDefaults = self.hostOpts[name]
        hostBox = HostDialog(self, title='Host Details', prefDefaults=prefDefaults)
        self.master.wait_window(hostBox.top)
        if hostBox.result:
            newHostOpts = {'nodeNum':self.hostOpts[name]['nodeNum']}
            newHostOpts['sched'] = hostBox.result['sched']
            if len(hostBox.result['cpu']) > 0:
                newHostOpts['cpu'] = float(hostBox.result['cpu'])
            if len(hostBox.result['cores']) > 0:
                newHostOpts['cores'] = hostBox.result['cores']
            if len(hostBox.result['hostname']) > 0:
                newHostOpts['hostname'] = hostBox.result['hostname']
                name = hostBox.result['hostname']
                widget[ 'text' ] = name
            if len(hostBox.result['defaultRoute']) > 0:
                newHostOpts['defaultRoute'] = hostBox.result['defaultRoute']
            if len(hostBox.result['ip']) > 0:
                newHostOpts['ip'] = hostBox.result['ip']
            if len(hostBox.result['externalInterfaces']) > 0:
                newHostOpts['externalInterfaces'] = hostBox.result['externalInterfaces']
            if len(hostBox.result['vlanInterfaces']) > 0:
                newHostOpts['vlanInterfaces'] = hostBox.result['vlanInterfaces']
            self.hostOpts[name] = newHostOpts
            print 'New host details for ' + name + ' = ' + str(newHostOpts)

    def switchDetails( self, _ignore=None ):
        if ( self.selection is None or
             self.net is not None or
             self.selection not in self.itemToWidget ):
            return
        widget = self.itemToWidget[ self.selection ]
        name = widget[ 'text' ]
        tags = self.canvas.gettags( self.selection )
        if 'Switch' not in tags:
            return

        prefDefaults = self.switchOpts[name]
        switchBox = SwitchDialog(self, title='Switch Details', prefDefaults=prefDefaults)
        self.master.wait_window(switchBox.top)
        if switchBox.result:
            newSwitchOpts = {'nodeNum':self.switchOpts[name]['nodeNum']}
            newSwitchOpts['switchType'] = switchBox.result['switchType']
            newSwitchOpts['controllers'] = self.switchOpts[name]['controllers']
            if len(switchBox.result['dpctl']) > 0:
                newSwitchOpts['dpctl'] = switchBox.result['dpctl']
            if len(switchBox.result['dpid']) > 0:
                newSwitchOpts['dpid'] = switchBox.result['dpid']
            if len(switchBox.result['hostname']) > 0:
                newSwitchOpts['hostname'] = switchBox.result['hostname']
                name = switchBox.result['hostname']
                widget[ 'text' ] = name
            if len(switchBox.result['externalInterfaces']) > 0:
                newSwitchOpts['externalInterfaces'] = switchBox.result['externalInterfaces']
            newSwitchOpts['switchIP'] = switchBox.result['switchIP']
            newSwitchOpts['sflow'] = switchBox.result['sflow']
            newSwitchOpts['netflow'] = switchBox.result['netflow']
            self.switchOpts[name] = newSwitchOpts
            print 'New switch details for ' + name + ' = ' + str(newSwitchOpts)

    def linkUp( self ):
        if ( self.selection is None or
             self.net is None):
            return
        link = self.selection
        linkDetail =  self.links[link]
        src = linkDetail['src']
        dst = linkDetail['dest']
        srcName, dstName = src[ 'text' ], dst[ 'text' ]
        self.net.configLinkStatus(srcName, dstName, 'up')
        self.canvas.itemconfig(link, dash=())

    def linkDown( self ):
        if ( self.selection is None or
             self.net is None):
            return
        link = self.selection
        linkDetail =  self.links[link]
        src = linkDetail['src']
        dst = linkDetail['dest']
        srcName, dstName = src[ 'text' ], dst[ 'text' ]
        self.net.configLinkStatus(srcName, dstName, 'down')
        self.canvas.itemconfig(link, dash=(4, 4))

    def linkDetails( self, _ignore=None ):
        if ( self.selection is None or
             self.net is not None):
            return
        link = self.selection

        linkDetail =  self.links[link]
        src = linkDetail['src']
        dest = linkDetail['dest']
        linkopts = linkDetail['linkOpts']
        linkBox = LinkDialog(self, title='Link Details', linkDefaults=linkopts)
        if linkBox.result is not None:
            linkDetail['linkOpts'] = linkBox.result
            print 'New link details = ' + str(linkBox.result)

    def prefDetails( self ):
        prefDefaults = self.appPrefs
        prefBox = PrefsDialog(self, title='Preferences', prefDefaults=prefDefaults)
        print 'New Prefs = ' + str(prefBox.result)
        if prefBox.result:
            self.appPrefs = prefBox.result


    def controllerDetails( self ):
        if ( self.selection is None or
             self.net is not None or
             self.selection not in self.itemToWidget ):
            return
        widget = self.itemToWidget[ self.selection ]
        name = widget[ 'text' ]
        tags = self.canvas.gettags( self.selection )
        oldName = name
        if 'Controller' not in tags:
            return

        ctrlrBox = ControllerDialog(self, title='Controller Details', ctrlrDefaults=self.controllers[name])
        if ctrlrBox.result:
            #print 'Controller is ' + ctrlrBox.result[0]
            if len(ctrlrBox.result['hostname']) > 0:
                name = ctrlrBox.result['hostname']
                widget[ 'text' ] = name
            else:
                ctrlrBox.result['hostname'] = name
            self.controllers[name] = ctrlrBox.result
            print 'New controller details for ' + name + ' = ' + str(self.controllers[name])
            # Find references to controller and change name
            if oldName != name:
                for widget in self.widgetToItem:
                    switchName = widget[ 'text' ]
                    tags = self.canvas.gettags( self.widgetToItem[ widget ] )
                    if 'Switch' in tags:
                        switch = self.switchOpts[switchName]
                        if oldName in switch['controllers']:
                            switch['controllers'].remove(oldName)
                            switch['controllers'].append(name)


    def listBridge( self, _ignore=None ):
        if ( self.selection is None or
             self.net is None or
             self.selection not in self.itemToWidget ):
            return
        name = self.itemToWidget[ self.selection ][ 'text' ]
        tags = self.canvas.gettags( self.selection )

        if name not in self.net.nameToNode:
            return
        if 'Switch' in tags or 'LegacySwitch' in tags:
           call(["xterm -T 'Bridge Details' -sb -sl 2000 -e 'ovs-vsctl list bridge " + name + "; read -p \"Press Enter to close\"' &"], shell=True)

    def ovsShow( self, _ignore=None ):
        call(["xterm -T 'OVS Summary' -sb -sl 2000 -e 'ovs-vsctl show; read -p \"Press Enter to close\"' &"], shell=True)

    def rootTerminal( self, _ignore=None ):
        call(["xterm -T 'Root Terminal' -sb -sl 2000 &"], shell=True)

    # Model interface
    #
    # Ultimately we will either want to use a topo or
    # mininet object here, probably.

    def addLink( self, source, dest, linktype='data', linkopts={} ):
        "Add link to model."
        source.links[ dest ] = self.link
        dest.links[ source ] = self.link
        self.links[ self.link ] = {'type' :linktype,
                                   'src':source,
                                   'dest':dest,
                                   'linkOpts':linkopts}

    def deleteLink( self, link ):
        "Delete link from model."
        pair = self.links.get( link, None )
        if pair is not None:
            source=pair['src']
            dest=pair['dest']
            del source.links[ dest ]
            del dest.links[ source ]
            stags = self.canvas.gettags( self.widgetToItem[ source ] )
            dtags = self.canvas.gettags( self.widgetToItem[ dest ] )
            ltags = self.canvas.gettags( link )

            if 'control' in ltags:
                controllerName = ''
                switchName = ''
                if 'Controller' in stags:
                    controllerName = source[ 'text' ]
                    switchName = dest[ 'text' ]
                else:
                    controllerName = dest[ 'text' ]
                    switchName = source[ 'text' ]
    
                if controllerName in self.switchOpts[switchName]['controllers']:
                    self.switchOpts[switchName]['controllers'].remove(controllerName)


        if link is not None:
            del self.links[ link ]

    def deleteNode( self, item ):
        "Delete node (and its links) from model."

        widget = self.itemToWidget[ item ]
        tags = self.canvas.gettags(item)
        if 'Controller' in tags:
            # remove from switch controller lists
            for serachwidget in self.widgetToItem:
                name = serachwidget[ 'text' ]
                tags = self.canvas.gettags( self.widgetToItem[ serachwidget ] )
                if 'Switch' in tags:
                    if widget['text'] in self.switchOpts[name]['controllers']:
                        self.switchOpts[name]['controllers'].remove(widget['text'])
            
        for link in widget.links.values():
            # Delete from view and model
            self.deleteItem( link )
        del self.itemToWidget[ item ]
        del self.widgetToItem[ widget ]

    def buildNodes( self, net):
        # Make nodes
        print "Getting Hosts and Switches."
        for widget in self.widgetToItem:
            name = widget[ 'text' ]
            tags = self.canvas.gettags( self.widgetToItem[ widget ] )
            #print name+' has '+str(tags)

            if 'Switch' in tags:
                opts = self.switchOpts[name]

                # Create the correct switch class
                switchClass = customOvs
                switchParms={}
                if 'dpctl' in opts:
                    switchParms['listenPort']=int(opts['dpctl'])
                if 'dpid' in opts:
                    switchParms['dpid']=opts['dpid']
                if opts['switchType'] == 'default':
                    if self.appPrefs['switchType'] == 'ivs':
                        switchClass = IVSSwitch
                    elif self.appPrefs['switchType'] == 'user':
                        switchClass = CustomUserSwitch
                    elif self.appPrefs['switchType'] == 'userns':
                        switchParms['inNamespace'] = True
                        switchClass = CustomUserSwitch
                    else:
                        switchClass = customOvs
                elif opts['switchType'] == 'user':
                    switchClass = CustomUserSwitch
                elif opts['switchType'] == 'userns':
                    switchClass = CustomUserSwitch
                    switchParms['inNamespace'] = True
                elif opts['switchType'] == 'ivs':
                    switchClass = IVSSwitch
                else:
                    switchClass = customOvs
                newSwitch = net.addSwitch( name , cls=switchClass, **switchParms)
                if switchClass == CustomUserSwitch:
                    if ('switchIP' in opts):
                        if (len(opts['switchIP']) > 0):
                            newSwitch.setSwitchIP(opts['switchIP'])
                if switchClass == customOvs:
                    newSwitch.setOpenFlowVersion(self.appPrefs['openFlowVersions'])
                    if ('switchIP' in opts):
                        if (len(opts['switchIP']) > 0):
                            newSwitch.setSwitchIP(opts['switchIP'])

                # Attach external interfaces
                if ('externalInterfaces' in opts):
                    for extInterface in opts['externalInterfaces']:
                        if self.checkIntf(extInterface):
                           Intf( extInterface, node=newSwitch )

            elif 'LegacySwitch' in tags:
                newSwitch = net.addSwitch( name , cls=LegacySwitch)
            elif 'LegacyRouter' in tags:
                newSwitch = net.addHost( name , cls=LegacyRouter)
            elif 'Host' in tags:
                opts = self.hostOpts[name]
                ip = None
                defaultRoute = None
                if 'defaultRoute' in opts and len(opts['defaultRoute']) > 0:
                    defaultRoute = 'via '+opts['defaultRoute']
                if 'ip' in opts and len(opts['ip']) > 0:
                    ip = opts['ip']
                else:
                    nodeNum = self.hostOpts[name]['nodeNum']
                    ipBaseNum, prefixLen = netParse( self.appPrefs['ipBase'] )
                    ip = ipAdd(i=nodeNum, prefixLen=prefixLen, ipBaseNum=ipBaseNum)

                # Create the correct host class
                hostCls = Host
                if 'cores' in opts or 'cpu' in opts:
                    hostCls=CPULimitedHost
                newHost = net.addHost( name,
                                       cls=hostCls,
                                       ip=ip,
                                       defaultRoute=defaultRoute
                                      )

                # Set the CPULimitedHost specific options
                if 'cores' in opts:
                    newHost.setCPUs(cores = opts['cores'])
                if 'cpu' in opts:
                    newHost.setCPUFrac(f=opts['cpu'], sched=opts['sched'])

                # Attach external interfaces
                if ('externalInterfaces' in opts):
                    for extInterface in opts['externalInterfaces']:
                        if self.checkIntf(extInterface):
                           Intf( extInterface, node=newHost )
                if ('vlanInterfaces' in opts):
                    if len(opts['vlanInterfaces']) > 0:
                        print 'Checking that OS is VLAN prepared'
                        self.pathCheck('vconfig', moduleName='vlan package')
                        moduleDeps( add='8021q' )
            elif 'Controller' in tags:
                opts = self.controllers[name]

                # Get controller info from panel
                controllerType = opts['controllerType']

                # Make controller
                print 'Getting controller selection:'+controllerType
                controllerIP = opts['remoteIP']
                controllerPort = opts['remotePort']
                if controllerType == 'remote':
                    net.addController(name=name,
                                      controller=RemoteController,
                                      ip=controllerIP,
                                      port=controllerPort)
                elif controllerType == 'inband':
                    net.addController(name=name,
                                      controller=InbandController,
                                      ip=controllerIP,
                                      port=controllerPort)
                elif controllerType == 'ovsc':
                    net.addController(name=name,
                                      controller=OVSController,
                                      port=controllerPort)
                else:
                    net.addController(name=name,
                                      controller=Controller,
                                      port=controllerPort)

            else:
                raise Exception( "Cannot create mystery node: " + name )

    def pathCheck( self, *args, **kwargs ):
        "Make sure each program in *args can be found in $PATH."
        moduleName = kwargs.get( 'moduleName', 'it' )
        for arg in args:
            if not quietRun( 'which ' + arg ):
                showerror(title="Error",
                      message= 'Cannot find required executable %s.\n' % arg +
                       'Please make sure that %s is installed ' % moduleName +
                       'and available in your $PATH.' )

    def buildLinks( self, net):
        # Make links
        print "Getting Links."
        for key,link in self.links.iteritems():
            tags = self.canvas.gettags(key)
            if 'data' in tags:
                src=link['src']
                dst=link['dest']
                linkopts=link['linkOpts']
                srcName, dstName = src[ 'text' ], dst[ 'text' ]
                src, dst = net.nameToNode[ srcName ], net.nameToNode[ dstName ]
                if linkopts:
                    net.addLink(src, dst, cls=TCLink, **linkopts)
                else:
                    net.addLink(src, dst)
                self.canvas.itemconfig(key, dash=())


    def build( self ):
        print "Build network based on our topology."

        dpctl = None
        if len(self.appPrefs['dpctl']) > 0:
            dpctl = int(self.appPrefs['dpctl'])
        net = Mininet( topo=None,
                       listenPort=dpctl,
                       build=False,
                       ipBase=self.appPrefs['ipBase'] )

        self.buildNodes(net)
        self.buildLinks(net)

        # Build network (we have to do this separately at the moment )
        net.build()

        return net


    def postStartSetup( self ):

        # Setup host VLAN subinterfaces
        for widget in self.widgetToItem:
            name = widget[ 'text' ]
            tags = self.canvas.gettags( self.widgetToItem[ widget ] )
            if 'Host' in tags:
                opts = self.hostOpts[name]
                # Attach vlan interfaces
                if ('vlanInterfaces' in opts):
                    for vlanInterface in opts['vlanInterfaces']:
                        print 'adding vlan interface '+vlanInterface[1]
                        newHost = self.net.get(name)
                        newHost.cmdPrint('vconfig add '+name+'-eth0 '+vlanInterface[1])
                        newHost.cmdPrint('ifconfig '+name+'-eth0.'+vlanInterface[1]+' '+vlanInterface[0])

        # Configure NetFlow
        nflowValues = self.appPrefs['netflow']
        if len(nflowValues['nflowTarget']) > 0:
            nflowEnabled = False
            nflowSwitches = ''
            for widget in self.widgetToItem:
                name = widget[ 'text' ]
                tags = self.canvas.gettags( self.widgetToItem[ widget ] )
    
                if 'Switch' in tags:
                    opts = self.switchOpts[name]
                    if 'netflow' in opts:
                        if opts['netflow'] == '1':
                            print name+' has Netflow enabled'
                            nflowSwitches = nflowSwitches+' -- set Bridge '+name+' netflow=@MiniEditNF'
                            nflowEnabled=True
            if nflowEnabled:
                nflowCmd = 'ovs-vsctl -- --id=@MiniEditNF create NetFlow '+ 'target=\\\"'+nflowValues['nflowTarget']+'\\\" '+ 'active-timeout='+nflowValues['nflowTimeout']
                if nflowValues['nflowAddId'] == '1':
                    nflowCmd = nflowCmd + ' add_id_to_interface=true'
                else:
                    nflowCmd = nflowCmd + ' add_id_to_interface=false'
                print 'cmd = '+nflowCmd+nflowSwitches
                call(nflowCmd+nflowSwitches, shell=True)

            else:
                print 'No switches with Netflow'
        else:
            print 'No NetFlow targets specified.'

        # Configure sFlow
        sflowValues = self.appPrefs['sflow']
        if len(sflowValues['sflowTarget']) > 0:
            sflowEnabled = False
            sflowSwitches = ''
            for widget in self.widgetToItem:
                name = widget[ 'text' ]
                tags = self.canvas.gettags( self.widgetToItem[ widget ] )
    
                if 'Switch' in tags:
                    opts = self.switchOpts[name]
                    if 'sflow' in opts:
                        if opts['sflow'] == '1':
                            print name+' has sflow enabled'
                            sflowSwitches = sflowSwitches+' -- set Bridge '+name+' sflow=@MiniEditSF'
                            sflowEnabled=True
            if sflowEnabled:
                sflowCmd = 'ovs-vsctl -- --id=@MiniEditSF create sFlow '+ 'target=\\\"'+sflowValues['sflowTarget']+'\\\" '+ 'header='+sflowValues['sflowHeader']+' '+ 'sampling='+sflowValues['sflowSampling']+' '+ 'polling='+sflowValues['sflowPolling']
                print 'cmd = '+sflowCmd+sflowSwitches
                call(sflowCmd+sflowSwitches, shell=True)

            else:
                print 'No switches with sflow'
        else:
            print 'No sFlow targets specified.'

        ## NOTE: MAKE SURE THIS IS LAST THING CALLED
        # Start the CLI if enabled
        if self.appPrefs['startCLI'] == '1':
            info( "\n\n NOTE: PLEASE REMEMBER TO EXIT THE CLI BEFORE YOU PRESS THE STOP BUTTON. Not exiting will prevent MiniEdit from quitting and will prevent you from starting the network again during this sessoin.\n\n")
            CLI(self.net)

    def start( self ):
        "Start network."
        if self.net is None:
            self.net = self.build()

            # Since I am going to inject per switch controllers.
            # I can't call net.start().  I have to replicate what it
            # does and add the controller options.
            #self.net.start()
            info( '**** Starting %s controllers\n' % len( self.net.controllers ) )
            for controller in self.net.controllers:
                info( str(controller) + ' ')
                controller.start()
            info('\n')
            info( '**** Starting %s switches\n' % len( self.net.switches ) )
            #for switch in self.net.switches:
            #    info( switch.name + ' ')
            #    switch.start( self.net.controllers )
            for widget in self.widgetToItem:
                name = widget[ 'text' ]
                tags = self.canvas.gettags( self.widgetToItem[ widget ] )
                if 'Switch' in tags:
                    opts = self.switchOpts[name]
                    switchControllers = []
                    for ctrl in opts['controllers']:
                        switchControllers.append(self.net.get(ctrl))
                    info( name + ' ')
                    # Figure out what controllers will manage this switch
                    self.net.get(name).start( switchControllers )
                if 'LegacySwitch' in tags:
                    self.net.get(name).start( [] )
                    info( name + ' ')
            info('\n')

            self.postStartSetup()

    def stop( self ):
        "Stop network."
        if self.net is not None:
            self.net.stop()
        cleanUpScreens()
        self.net = None

    def do_linkPopup(self, event):
        # display the popup menu
        if ( self.net is None ):
            try:
                self.linkPopup.tk_popup(event.x_root, event.y_root, 0)
            finally:
                # make sure to release the grab (Tk 8.0a1 only)
                self.linkPopup.grab_release()
        else:
            try:
                self.linkRunPopup.tk_popup(event.x_root, event.y_root, 0)
            finally:
                # make sure to release the grab (Tk 8.0a1 only)
                self.linkRunPopup.grab_release()

    def do_controllerPopup(self, event):
        # display the popup menu
        if ( self.net is None ):
            try:
                self.controllerPopup.tk_popup(event.x_root, event.y_root, 0)
            finally:
                # make sure to release the grab (Tk 8.0a1 only)
                self.controllerPopup.grab_release()

    def do_legacyRouterPopup(self, event):
        # display the popup menu
        if ( self.net is not None ):
            try:
                self.legacyRouterRunPopup.tk_popup(event.x_root, event.y_root, 0)
            finally:
                # make sure to release the grab (Tk 8.0a1 only)
                self.legacyRouterRunPopup.grab_release()

    def do_hostPopup(self, event):
        # display the popup menu
        if ( self.net is None ):
            try:
                self.hostPopup.tk_popup(event.x_root, event.y_root, 0)
            finally:
                # make sure to release the grab (Tk 8.0a1 only)
                self.hostPopup.grab_release()
        else:
            try:
                self.hostRunPopup.tk_popup(event.x_root, event.y_root, 0)
            finally:
                # make sure to release the grab (Tk 8.0a1 only)
                self.hostRunPopup.grab_release()

    def do_legacySwitchPopup(self, event):
        # display the popup menu
        if ( self.net is not None ):
            try:
                self.switchRunPopup.tk_popup(event.x_root, event.y_root, 0)
            finally:
                # make sure to release the grab (Tk 8.0a1 only)
                self.switchRunPopup.grab_release()

    def do_switchPopup(self, event):
        # display the popup menu
        if ( self.net is None ):
            try:
                self.switchPopup.tk_popup(event.x_root, event.y_root, 0)
            finally:
                # make sure to release the grab (Tk 8.0a1 only)
                self.switchPopup.grab_release()
        else:
            try:
                self.switchRunPopup.tk_popup(event.x_root, event.y_root, 0)
            finally:
                # make sure to release the grab (Tk 8.0a1 only)
                self.switchRunPopup.grab_release()

    def xterm( self, _ignore=None ):
        "Make an xterm when a button is pressed."
        if ( self.selection is None or
             self.net is None or
             self.selection not in self.itemToWidget ):
            return
        name = self.itemToWidget[ self.selection ][ 'text' ]
        if name not in self.net.nameToNode:
            return
        term = makeTerm( self.net.nameToNode[ name ], 'Host', term=self.appPrefs['terminalType'] )
        if StrictVersion(MININET_VERSION) > StrictVersion('2.0'):
            self.net.terms += term
        else:
            self.net.terms.append(term)

    def iperf( self, _ignore=None ):
        "Make an xterm when a button is pressed."
        if ( self.selection is None or
             self.net is None or
             self.selection not in self.itemToWidget ):
            return
        name = self.itemToWidget[ self.selection ][ 'text' ]
        if name not in self.net.nameToNode:
            return
        self.net.nameToNode[ name ].cmd( 'iperf -s -p 5001 &' )

    """ BELOW HERE IS THE TOPOLOGY IMPORT CODE """

    def parseArgs( self ):
        """Parse command-line args and return options object.
           returns: opts parse options dict"""

        if '--custom' in sys.argv:
            index = sys.argv.index( '--custom' )
            if len( sys.argv ) > index + 1:
                filename = sys.argv[ index + 1 ]
                self.parseCustomFile( filename )
            else:
                raise Exception( 'Custom file name not found' )

        desc = ( "The %prog utility creates Mininet network from the\n"
                 "command line. It can create parametrized topologies,\n"
                 "invoke the Mininet CLI, and run tests." )

        usage = ( '%prog [options]\n'
                  '(type %prog -h for details)' )

        opts = OptionParser( description=desc, usage=usage )

        addDictOption( opts, TOPOS, TOPODEF, 'topo' )
        opts.add_option( '--custom', type='string', default=None,
                         help='read custom topo and node params from .py' +
                         'file' )

        self.options, self.args = opts.parse_args()
        # We don't accept extra arguments after the options
        if self.args:
            opts.print_help()
            exit()

    def setCustom( self, name, value ):
        "Set custom parameters for MininetRunner."
        if name in ( 'topos', 'switches', 'hosts', 'controllers' ):
            # Update dictionaries
            param = name.upper()
            globals()[ param ].update( value )
        elif name == 'validate':
            # Add custom validate function
            self.validate = value
        else:
            # Add or modify global variable or class
            globals()[ name ] = value

    def parseCustomFile( self, fileName ):
        "Parse custom file and add params before parsing cmd-line options."
        customs = {}
        if os.path.isfile( fileName ):
            execfile( fileName, customs, customs )
            for name, val in customs.iteritems():
                self.setCustom( name, val )
        else:
            raise Exception( 'could not find custom file: %s' % fileName )

    def importTopo( self ):
        print 'topo='+self.options.topo
        if self.options.topo == 'none':
            return
        self.newTopology()
        topo = buildTopo( TOPOS, self.options.topo )
        importNet = Mininet(topo=topo, build=False)
        importNet.build()

        c = self.canvas
        rowIncrement = 100
        currentY = 100

        # Add Controllers
        print 'controllers:'+str(len(importNet.controllers))
        for controller in importNet.controllers:
            name = controller.name
            x = self.controllerCount*100+100
            self.addNode('Controller', self.controllerCount,
                 float(x), float(currentY), name=name)
            icon = self.findWidgetByName(name)
            icon.bind('<Button-3>', self.do_controllerPopup )
            ctrlr = { 'controllerType': 'ref',
                      'hostname': name,
                      'remoteIP': controller.ip,
                      'remotePort': controller.port}
            self.controllers[name] = ctrlr



        currentY = currentY + rowIncrement

        # Add switches
        print 'switches:'+str(len(importNet.switches))
        columnCount = 0
        for switch in importNet.switches:
            name = switch.name
            self.switchOpts[name] = {}
            self.switchOpts[name]['nodeNum']=self.switchCount
            self.switchOpts[name]['hostname']=name
            self.switchOpts[name]['switchType']='default'
            self.switchOpts[name]['controllers']=[]

            x = columnCount*100+100
            self.addNode('Switch', self.switchCount,
                 float(x), float(currentY), name=name)
            icon = self.findWidgetByName(name)
            icon.bind('<Button-3>', self.do_switchPopup )
            # Now link to controllers
            for controller in importNet.controllers:
                self.switchOpts[name]['controllers'].append(controller.name)
                dest = self.findWidgetByName(controller.name)
                dx, dy = c.coords( self.widgetToItem[ dest ] )
                self.link = c.create_line(float(x),
                                          float(currentY),
                                          dx,
                                          dy,
                                          width=4,
                                          fill='red',
                                          dash=(6, 4, 2, 4),
                                          tag='link' )
                c.itemconfig(self.link, tags=c.gettags(self.link)+('control',))
                self.addLink( icon, dest, linktype='control' )
                self.createControlLinkBindings()
                self.link = self.linkWidget = None
            if columnCount == 9:
                columnCount = 0
                currentY = currentY + rowIncrement
            else:
                columnCount =columnCount+1


        currentY = currentY + rowIncrement
        # Add hosts
        print 'hosts:'+str(len(importNet.hosts))
        columnCount = 0
        for host in importNet.hosts:
            name = host.name
            self.hostOpts[name] = {'sched':'host'}
            self.hostOpts[name]['nodeNum']=self.hostCount
            self.hostOpts[name]['hostname']=name
            self.hostOpts[name]['ip']=host.IP()

            x = columnCount*100+100
            self.addNode('Host', self.hostCount,
                 float(x), float(currentY), name=name)
            icon = self.findWidgetByName(name)
            icon.bind('<Button-3>', self.do_hostPopup )
            if columnCount == 9:
                columnCount = 0
                currentY = currentY + rowIncrement
            else:
                columnCount =columnCount+1

        print 'links:'+str(len(topo.links()))
        #[('h1', 's3'), ('h2', 's4'), ('s3', 's4')]
        for link in topo.links():
            srcNode = link[0]
            src = self.findWidgetByName(srcNode)
            sx, sy = self.canvas.coords( self.widgetToItem[ src ] )

            destNode = link[1]
            dest = self.findWidgetByName(destNode)
            dx, dy = self.canvas.coords( self.widgetToItem[ dest]  )

            self.link = self.canvas.create_line( sx, sy, dx, dy, width=4,
                                             fill='blue', tag='link' )
            c.itemconfig(self.link, tags=c.gettags(self.link)+('data',))
            self.addLink( src, dest )
            self.createDataLinkBindings()
            self.link = self.linkWidget = None

        importNet.stop()

def miniEditImages():
    "Create and return images for MiniEdit."

    # Image data. Git will be unhappy. However, the alternative
    # is to keep track of separate binary files, which is also
    # unappealing.

    return {
        'Select': BitmapImage(
            file='/usr/include/X11/bitmaps/left_ptr' ),

        'Switch': PhotoImage( data=r"""
R0lGODlhLgAgAPcAAB2ZxGq61imex4zH3RWWwmK41tzd3vn9/jCiyfX7/Q6SwFay0gBlmtnZ2snJ
yr+2tAuMu6rY6D6kyfHx8XO/2Uqszjmly6DU5uXz+JLN4uz3+kSrzlKx0ZeZm2K21BuYw67a6QB9
r+Xl5rW2uHW61On1+UGpzbrf6xiXwny9166vsMLCwgBdlAmHt8TFxgBwpNTs9C2hyO7t7ZnR5L/B
w0yv0NXV1gBimKGjpABtoQBuoqKkpiaUvqWmqHbB2/j4+Pf39729vgB/sN7w9obH3hSMugCAsonJ
4M/q8wBglgB6rCCaxLO0tX7C2wBqniGMuABzpuPl5f3+/v39/fr6+r7i7vP6/ABonV621LLc6zWk
yrq6uq6wskGlyUaszp6gohmYw8HDxKaoqn3E3LGztWGuzcnLzKmrrOnp6gB1qCaex1q001ewz+Dg
4QB3qrCxstHS09LR0dHR0s7Oz8zNzsfIyQaJuQB0pozL4YzI3re4uAGFtYDG3hOUwb+/wQB5rOvr
6wB2qdju9TWfxgBpniOcxeLj48vn8dvc3VKuzwB2qp6fos/Q0aXV6D+jxwB7rsXHyLu8vb27vCSc
xSGZwxyZxH3A2RuUv0+uzz+ozCedxgCDtABnnABroKutr/7+/n2/2LTd6wBvo9bX2OLo6lGv0C6d
xS6avjmmzLTR2uzr6m651RuXw4jF3CqfxySaxSadyAuRv9bd4cPExRiMuDKjyUWevNPS0sXl8BeY
xKytr8G/wABypXvC23vD3O73+3vE3cvU2PH5+7S1t7q7vCGVwO/v8JfM3zymyyyZwrWys+Hy90Ki
xK6qqg+TwBKXxMvMzaWtsK7U4jemzLXEygBxpW++2aCho97Z18bP0/T09fX29vb19ViuzdDR0crf
51qz01y00ujo6Onq6hCDs2Gpw3i71CqWv3S71nO92M/h52m207bJ0AN6rPPz9Nrh5Nvo7K/b6oTI
37Td7ABqneHi4yScxo/M4RiWwRqVwcro8n3B2lGoylStzszMzAAAACH5BAEAAP8ALAAAAAAuACAA
Bwj/AP8JHEjw3wEkEY74WOjrQhUNBSNKnCjRSoYKCOwJcKWpEAACBFBRGEKxZMkDjRAg2OBlQyYL
WhDEcOWxDwofv0zqHIhhDYIFC2p4MYFMS62ZaiYVWlJJAYIqO00KMlEjABYOQokaRbp0CYBKffpE
iDpxSKYC1gqswToUmYVaCFyp6QrgwwcCscaSJZhgQYBeAdRyqFBhgwWkGyct8WoXRZ8Ph/YOxMOB
CIUAHsBxwGQBAII1YwpMI5Brcd0PKFA4Q2ZFMgYteZqkwxyu1KQNJzQc+CdFCrxypyqdRoEPX6x7
ki/n2TfbAxtNRHYTVCWpWTRbuRoX7yMgZ9QSFQa0/7LU/BXygjIWXVOBTR2sxp7BxGpENgKbY+PR
reqyIOKnOh0M445AjTjDCgrPSBNFKt9w8wMVU5g0Bg8kDAAKOutQAkNEQNBwDRAEeVEcAV6w84Ay
KowQSRhmzNGAASIAYow2IP6DySPk8ANKCv1wINE2cpjxCUEgOIOPAKicQMMbKnhyhhg97HDNF4vs
IEYkNkzwjwSP/PHIE2VIgIdEnxjAiBwNGIKGDKS8I0sw2VAzApNOQimGLlyMAIkDw2yhZTF/KKGE
lxCEMtEPBtDhACQurLDCLkFIsoUeZLyRpx8OmEGHN3AEcU0HkFAhUDFulDroJvOU5M44iDjgDTQO
1P/hzRw2IFJPGw3AAY0LI/SAwxc7jEKQI2mkEUipRoxp0g821AMIGlG0McockMzihx5c1LkDDmSg
UVAiafACRbGPVKDTFG3MYUYdLoThRxDE6DEMGUww8eQONGwTER9piFINFOPasaFJVIjTwC1xzOGP
A3HUKoIMDTwJR4QRgdBOJzq8UM0Lj5QihU5ZdGMOCSSYUwYzAwwkDhNtUKTBOZ10koMOoohihDwm
HZKPEDwb4fMe9An0g5Yl+SDKFTHnkMMLLQAjXUTxUCLEIyH0bIQAwuxVQhEMcEIIIUmHUEsWGCQg
xQEaIFGAHV0+QnUIIWwyg2T/3MPLDQwwcAUhTjiswYsQl1SAxQKmbBJCIMe6ISjVmXwsWQKJEJJE
3l1/TY8O4wZyh8ZQ3IF4qX9cggTdAmEwCAMs3IB311fsDfbMGv97BxSBQBAP6QMN0QUhLCSRhOp5
e923zDpk/EIaRdyO+0C/eHBHEiz0vjrrfMfciSKD4LJ8RBEk88IN0ff+O/CEVEPLGK1tH1ECM7Dx
RDWdcMLJFTpUQ44jfCyjvlShZNDE/0QAgT6ypr6AAAA7
            """),

        'LegacySwitch': PhotoImage( data=r"""
R0lGODlhMgAYAPcAAAEBAXmDjbe4uAE5cjF7xwFWq2Sa0S9biSlrrdTW1k2Ly02a5xUvSQFHjmep
6bfI2Q5SlQIYLwFfvj6M3Jaan8fHyDuFzwFp0Vah60uU3AEiRhFgrgFRogFr10N9uTFrpytHYQFM
mGWt9wIwX+bm5kaT4gtFgR1cnJPF9yt80CF0yAIMGHmp2c/P0AEoUb/P4Fei7qK4zgpLjgFkyQlf
t1mf5jKD1WWJrQ86ZwFAgBhYmVOa4MPV52uv8y+A0iR3ywFbtUyX5ECI0Q1UmwIcOUGQ3RBXoQI0
aRJbpr3BxVeJvQUJDafH5wIlS2aq7xBmv52lr7fH12el5Wml3097ph1ru7vM3HCz91Ke6lid40KQ
4GSQvgQGClFnfwVJjszMzVCX3hljrdPT1AFLlBRnutPf6yd5zjeI2QE9eRBdrBNVl+3v70mV4ydf
lwMVKwErVlul8AFChTGB1QE3bsTFxQImTVmAp0FjiUSM1k+b6QQvWQ1SlxMgLgFixEqU3xJhsgFT
pn2Xs5OluZ+1yz1Xb6HN+Td9wy1zuYClykV5r0x2oeDh4qmvt8LDwxhuxRlLfyRioo2124mft9bi
71mDr7fT79nl8Z2hpQs9b7vN4QMQIOPj5XOPrU2Jx32z6xtvwzeBywFFikFnjwcPFa29yxJjuFmP
xQFv3qGxwRc/Z8vb6wsRGBNqwqmpqTdvqQIbNQFPngMzZAEfP0mQ13mHlQFYsAFnznOXu2mPtQxj
vQ1Vn4Ot1+/x8my0/CJgnxNNh8DT5CdJaWyx+AELFWmt8QxPkxBZpwMFB015pgFduGCNuyx7zdnZ
2WKm6h1xyOPp8aW70QtPkUmM0LrCyr/FyztljwFPm0OJzwFny7/L1xFjswE/e12i50iR2VR8o2Gf
3xszS2eTvz2BxSlloQdJiwMHDzF3u7bJ3T2I1WCp8+Xt80FokQFJklef6mORw2ap7SJ1y77Q47nN
3wFfu1Kb5cXJyxdhrdDR0wlNkTSF11Oa4yp4yQEuW0WQ3QIDBQI7dSH5BAEAAAAALAAAAAAyABgA
Bwj/AAEIHDjKF6SDvhImPMHwhA6HOiLqUENRDYSLEIplxBcNHz4Z5GTI8BLKS5OBA1Ply2fDhxwf
PlLITGFmmRkzP+DlVKHCmU9nnz45csSqKKsn9gileZKrVC4aRFACOGZu5UobNuRohRkzhc2b+36o
qCaqrFmzZEV1ERBg3BOmMl5JZTBhwhm7ZyycYZnvJdeuNl21qkCHTiPDhxspTtKoQgUKCJ6wehMV
5QctWupeo6TkjOd8e1lmdQkTGbTTMaDFiDGINeskX6YhEicUiQa5A/kUKaFFwQ0oXzjZ8Tbcm3Hj
irwpMtTSgg9QMJf5WEZ9375AiED19ImpSQSUB4Kw/8HFSMyiRWJaqG/xhf2X91+oCbmq1e/MFD/2
EcApVkWVJhp8J9AqsywQxDfAbLJJPAy+kMkL8shjxTkUnhOJZ5+JVp8cKfhwxwdf4fQLgG4MFAwW
KOZRAxM81EAPPQvoE0QQfrDhx4399OMBMjz2yCMVivCoCAWXKLKMTPvoUYcsKwi0RCcwYCAlFjU0
A6OBM4pXAhsl8FYELYWFWZhiZCbRQgIC2AGTLy408coxAoEDx5wwtGPALTVg0E4NKC7gp4FsBKoA
Ki8U+oIVmVih6DnZPMBMAlGwIARWOLiggSYC+ZNIOulwY4AkSZCyxaikbqHMqaeaIp4+rAaxQxBg
2P+IozuRzvLZIS4syYVAfMAhwhSC1EPCGoskIIYY9yS7Hny75OFnEIAGyiVvWkjjRxF11fXIG3WU
KNA6wghDTCW88PKMJZOkm24Z7LarSjPtoIjFn1lKyyVmmBVhwRtvaDDMgFL0Eu4VhaiDwhXCXNFD
D8QQw7ATEDsBw8RSxotFHs7CKJ60XWrRBj91EOGPQCA48c7J7zTjSTPctOzynjVkkYU+O9S8Axg4
Z6BzBt30003Ps+AhNB5C4PCGC5gKJMMTZJBRytOl/CH1HxvQkMbVVxujtdZGGKGL17rsEfYQe+xR
zNnFcGQCv7LsKlAtp8R9Sgd0032BLXjPoPcMffTd3YcEgAMOxOBA1GJ4AYgXAMjiHDTgggveCgRI
3RfcnffefgcOeDKEG3444osDwgEspMNiTQhx5FoOShxcrrfff0uQjOycD+554qFzMHrpp4cwBju/
5+CmVNbArnntndeCO+O689777+w0IH0o1P/TRJMohRA4EJwn47nyiocOSOmkn/57COxE3wD11Mfh
fg45zCGyVF4Ufvvyze8ewv5jQK9++6FwXxzglwM0GPAfR8AeSo4gwAHCbxsQNCAa/kHBAVhwAHPI
4BE2eIRYeHAEIBwBP0Y4Qn41YWRSCQgAOw==
            """),

        'LegacyRouter': PhotoImage( data=r"""
R0lGODlhMgAYAPcAAAEBAXZ8gQNAgL29vQNctjl/xVSa4j1dfCF+3QFq1DmL3wJMmAMzZZW11dnZ
2SFrtyNdmTSO6gIZMUKa8gJVqEOHzR9Pf5W74wFjxgFx4jltn+np6Eyi+DuT6qKiohdtwwUPGWiq
6ymF4LHH3Rh11CV81kKT5AMoUA9dq1ap/mV0gxdXlytRdR1ptRNPjTt9vwNgvwJZsX+69gsXJQFH
jTtjizF0tvHx8VOm9z2V736Dhz2N3QM2acPZ70qe8gFo0HS19wVRnTiR6hMpP0eP1i6J5iNlqAtg
tktjfQFu3TNxryx4xAMTIzOE1XqAh1uf5SWC4AcfNy1XgQJny93n8a2trRh312Gt+VGm/AQIDTmB
yAF37QJasydzvxM/ayF3zhdLf8zLywFdu4i56gFlyi2J4yV/1w8wUo2/8j+X8D2Q5Eee9jeR7Uia
7DpeggFt2QNPm97e3jRong9bpziH2DuT7aipqQoVICmG45vI9R5720eT4Q1hs1er/yVVhwJJktPh
70tfdbHP7Xev5xs5V7W1sz9jhz11rUVZcQ9WoCVVhQk7cRdtwWuw9QYOFyFHbSBnr0dznxtWkS18
zKfP9wwcLAMHCwFFiS5UeqGtuRNNiwMfPS1hlQMtWRE5XzGM5yhxusLCwCljnwMdOFWh7cve8pG/
7Tlxp+Tr8g9bpXF3f0lheStrrYu13QEXLS1ppTV3uUuR1RMjNTF3vU2X4TZupwRSolNne4nB+T+L
2YGz4zJ/zYe99YGHjRdDcT95sx09XQldsgMLEwMrVc/X3yN3yQ1JhTRbggsdMQNfu9HPz6WlpW2t
7RctQ0GFyeHh4dvl8SBZklCb5kOO2kWR3Vmt/zdjkQIQHi90uvPz8wIVKBp42SV5zbfT7wtXpStV
fwFWrBVvyTt3swFz5kGBv2+1/QlbrVFjdQM7d1+j54i67UmX51qn9i1vsy+D2TuR5zddhQsjOR1t
u0GV6ghbsDVZf4+76RRisent8Xd9hQFBgwFNmwJLlcPDwwFr1z2T5yH5BAEAAAAALAAAAAAyABgA
Bwj/AAEIHEiQYJY7Qwg9UsTplRIbENuxEiXJgpcz8e5YKsixY8Essh7JcbbOBwcOa1JOmJAmTY4c
HeoIabJrCShI0XyB8YRso0eOjoAdWpciBZajJ1GuWcnSZY46Ed5N8hPATqEBoRB9gVJsxRlhPwHI
0kDkVywcRpGe9LF0adOnMpt8CxDnxg1o9lphKoEACoIvmlxxvHOKVg0n/Tzku2WoVoU2J1P6WNkS
rtwADuxCG/MOjwgRUEIjGG3FhaOBzaThiDSCil27G8Isc3LLjZwXsA6YYJmDjhTMmseoKQIFDx7R
oxHo2abnwygAlUj1mV6tWjlelEpRwfd6gzI7VeJQ/2vZoVaDUqigqftXpH0R46H9Kl++zUo4JnKq
9dGvv09RHFhcIUMe0NiFDyql0OJUHWywMc87TXRhhCRGiHAccvNZUR8JxpDTH38p9HEUFhxgMSAv
jbBjQge8PSXEC6uo0IsHA6gAAShmgCbffNtsQwIJifhRHX/TpUUiSijlUk8AqgQixSwdNBjCa7CF
oVggmEgCyRf01WcFCYvYUgB104k4YlK5HONEXXfpokYdMrXRAzMhmNINNNzB9p0T57AgyZckpKKP
GFNgw06ZWKR10jTw6MAmFWj4AJcQQkQQwSefvFeGCemMIQggeaJywSQ/wgHOAmJskQEfWqBlFBEH
1P/QaGY3QOpDZXA2+A6m7hl3IRQKGDCIAj6iwE8yGKC6xbJv8IHNHgACQQybN2QiTi5NwdlBpZdi
isd7vyanByOJ7CMGGRhgwE+qyy47DhnBPLDLEzLIAEQjBtChRmVPNWgpr+Be+Nc9icARww9TkIEu
DAsQ0O7DzGIQzD2QdDEJHTsIAROc3F7qWQncyHPPHN5QQAAG/vjzw8oKp8sPPxDH3O44/kwBQzLB
xBCMOTzzHEMMBMBARgJvZJBBEm/4k0ACKydMBgwYoKNNEjJXbTXE42Q9jtFIp8z0Dy1jQMA1AGzi
z9VoW7310V0znYDTGMQgwUDXLDBO2nhvoTXbbyRk/XXL+pxWkAT8UJ331WsbnbTSK8MggDZhCTOM
LQkcjvXeSPedAAw0nABWWARZIgEDfyTzxt15Z53BG1PEcEknrvgEelhZMDHKCTwI8EcQFHBBAAFc
gGPLHwLwcMIo12Qxu0ABAQA7
            """),

        'Controller': PhotoImage( data=r"""
            R0lGODlhMAAwAPcAAAEBAWfNAYWFhcfHx+3t6/f390lJUaWlpfPz8/Hx72lpaZGRke/v77m5uc0B
            AeHh4e/v7WNjY3t7e5eXlyMjI4mJidPT0+3t7f///09PT7Ozs/X19fHx8ZWTk8HBwX9/fwAAAAAA
            AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
            AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
            AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
            AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
            AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
            AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
            AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
            AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
            AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
            AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
            AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
            AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACH5BAEAAAAALAAAAAAwADAA
            Bwj/AAEIHEiwoMGDCBMqXMiwocOHECNKnEixosWLGAEIeMCxo8ePHwVkBGABg8mTKFOmtDByAIYN
            MGPCRCCzQIENNzEMGOkBAwIKQIMKpYCgKAIHCDB4GNkAA4OnUJ9++CDhQ1QGFzA0GKkBA4GvYMOK
            BYtBA1cNaNOqXcuWq8q3b81m7Cqzbk2bMMu6/Tl0qFEEAZLKxdj1KlSqVA3rnet1rOOwiwmznUzZ
            LdzLJgdfpIv3pmebN2Pm1GyRbocNp1PLNMDaAM3Im1/alQk4gO28pCt2RdCBt+/eRg8IP1AUdmmf
            f5MrL56bYlcOvaP7Xo6Ag3HdGDho3869u/YE1507t+3AgLz58ujPMwg/sTBUCAzgy49PH0LW5u0x
            XFiwvz////5dcJ9bjxVIAHsSdUXAAgs2yOCDDn6FYEQaFGDgYxNCpEFfHHKIX4IDhCjiiCSS+CGF
            FlCmogYpcnVABTDGKGOMAlRQYwUHnKjhAjX2aOOPN8LImgAL6PiQBhLMqCSNAThQgQRGOqRBBD1W
            aaOVAggnQARRNqRBBxmEKeaYZIrZQZcMKbDiigqM5OabcMYp55x01ilnQAA7
            """),

        'Host': PhotoImage( data=r"""
            R0lGODlhIAAYAPcAMf//////zP//mf//Zv//M///AP/M///MzP/M
            mf/MZv/MM//MAP+Z//+ZzP+Zmf+ZZv+ZM/+ZAP9m//9mzP9mmf9m
            Zv9mM/9mAP8z//8zzP8zmf8zZv8zM/8zAP8A//8AzP8Amf8AZv8A
            M/8AAMz//8z/zMz/mcz/Zsz/M8z/AMzM/8zMzMzMmczMZszMM8zM
            AMyZ/8yZzMyZmcyZZsyZM8yZAMxm/8xmzMxmmcxmZsxmM8xmAMwz
            /8wzzMwzmcwzZswzM8wzAMwA/8wAzMwAmcwAZswAM8wAAJn//5n/
            zJn/mZn/Zpn/M5n/AJnM/5nMzJnMmZnMZpnMM5nMAJmZ/5mZzJmZ
            mZmZZpmZM5mZAJlm/5lmzJlmmZlmZplmM5lmAJkz/5kzzJkzmZkz
            ZpkzM5kzAJkA/5kAzJkAmZkAZpkAM5kAAGb//2b/zGb/mWb/Zmb/
            M2b/AGbM/2bMzGbMmWbMZmbMM2bMAGaZ/2aZzGaZmWaZZmaZM2aZ
            AGZm/2ZmzGZmmWZmZmZmM2ZmAGYz/2YzzGYzmWYzZmYzM2YzAGYA
            /2YAzGYAmWYAZmYAM2YAADP//zP/zDP/mTP/ZjP/MzP/ADPM/zPM
            zDPMmTPMZjPMMzPMADOZ/zOZzDOZmTOZZjOZMzOZADNm/zNmzDNm
            mTNmZjNmMzNmADMz/zMzzDMzmTMzZjMzMzMzADMA/zMAzDMAmTMA
            ZjMAMzMAAAD//wD/zAD/mQD/ZgD/MwD/AADM/wDMzADMmQDMZgDM
            MwDMAACZ/wCZzACZmQCZZgCZMwCZAABm/wBmzABmmQBmZgBmMwBm
            AAAz/wAzzAAzmQAzZgAzMwAzAAAA/wAAzAAAmQAAZgAAM+4AAN0A
            ALsAAKoAAIgAAHcAAFUAAEQAACIAABEAAADuAADdAAC7AACqAACI
            AAB3AABVAABEAAAiAAARAAAA7gAA3QAAuwAAqgAAiAAAdwAAVQAA
            RAAAIgAAEe7u7t3d3bu7u6qqqoiIiHd3d1VVVURERCIiIhEREQAA
            ACH5BAEAAAAALAAAAAAgABgAAAiNAAH8G0iwoMGDCAcKTMiw4UBw
            BPXVm0ixosWLFvVBHFjPoUeC9Tb+6/jRY0iQ/8iVbHiS40CVKxG2
            HEkQZsyCM0mmvGkw50uePUV2tEnOZkyfQA8iTYpTKNOgKJ+C3AhO
            p9SWVaVOfWj1KdauTL9q5UgVbFKsEjGqXVtP40NwcBnCjXtw7tx/
            C8cSBBAQADs=
        """ ),

        'OldSwitch': PhotoImage( data=r"""
            R0lGODlhIAAYAPcAMf//////zP//mf//Zv//M///AP/M///MzP/M
            mf/MZv/MM//MAP+Z//+ZzP+Zmf+ZZv+ZM/+ZAP9m//9mzP9mmf9m
            Zv9mM/9mAP8z//8zzP8zmf8zZv8zM/8zAP8A//8AzP8Amf8AZv8A
            M/8AAMz//8z/zMz/mcz/Zsz/M8z/AMzM/8zMzMzMmczMZszMM8zM
            AMyZ/8yZzMyZmcyZZsyZM8yZAMxm/8xmzMxmmcxmZsxmM8xmAMwz
            /8wzzMwzmcwzZswzM8wzAMwA/8wAzMwAmcwAZswAM8wAAJn//5n/
            zJn/mZn/Zpn/M5n/AJnM/5nMzJnMmZnMZpnMM5nMAJmZ/5mZzJmZ
            mZmZZpmZM5mZAJlm/5lmzJlmmZlmZplmM5lmAJkz/5kzzJkzmZkz
            ZpkzM5kzAJkA/5kAzJkAmZkAZpkAM5kAAGb//2b/zGb/mWb/Zmb/
            M2b/AGbM/2bMzGbMmWbMZmbMM2bMAGaZ/2aZzGaZmWaZZmaZM2aZ
            AGZm/2ZmzGZmmWZmZmZmM2ZmAGYz/2YzzGYzmWYzZmYzM2YzAGYA
            /2YAzGYAmWYAZmYAM2YAADP//zP/zDP/mTP/ZjP/MzP/ADPM/zPM
            zDPMmTPMZjPMMzPMADOZ/zOZzDOZmTOZZjOZMzOZADNm/zNmzDNm
            mTNmZjNmMzNmADMz/zMzzDMzmTMzZjMzMzMzADMA/zMAzDMAmTMA
            ZjMAMzMAAAD//wD/zAD/mQD/ZgD/MwD/AADM/wDMzADMmQDMZgDM
            MwDMAACZ/wCZzACZmQCZZgCZMwCZAABm/wBmzABmmQBmZgBmMwBm
            AAAz/wAzzAAzmQAzZgAzMwAzAAAA/wAAzAAAmQAAZgAAM+4AAN0A
            ALsAAKoAAIgAAHcAAFUAAEQAACIAABEAAADuAADdAAC7AACqAACI
            AAB3AABVAABEAAAiAAARAAAA7gAA3QAAuwAAqgAAiAAAdwAAVQAA
            RAAAIgAAEe7u7t3d3bu7u6qqqoiIiHd3d1VVVURERCIiIhEREQAA
            ACH5BAEAAAAALAAAAAAgABgAAAhwAAEIHEiwoMGDCBMqXMiwocOH
            ECNKnEixosWB3zJq3Mixo0eNAL7xG0mypMmTKPl9Cznyn8uWL/m5
            /AeTpsyYI1eKlBnO5r+eLYHy9Ck0J8ubPmPOrMmUpM6UUKMa/Ui1
            6saLWLNq3cq1q9evYB0GBAA7
        """ ),

        'NetLink': PhotoImage( data=r"""
            R0lGODlhFgAWAPcAMf//////zP//mf//Zv//M///AP/M///MzP/M
            mf/MZv/MM//MAP+Z//+ZzP+Zmf+ZZv+ZM/+ZAP9m//9mzP9mmf9m
            Zv9mM/9mAP8z//8zzP8zmf8zZv8zM/8zAP8A//8AzP8Amf8AZv8A
            M/8AAMz//8z/zMz/mcz/Zsz/M8z/AMzM/8zMzMzMmczMZszMM8zM
            AMyZ/8yZzMyZmcyZZsyZM8yZAMxm/8xmzMxmmcxmZsxmM8xmAMwz
            /8wzzMwzmcwzZswzM8wzAMwA/8wAzMwAmcwAZswAM8wAAJn//5n/
            zJn/mZn/Zpn/M5n/AJnM/5nMzJnMmZnMZpnMM5nMAJmZ/5mZzJmZ
            mZmZZpmZM5mZAJlm/5lmzJlmmZlmZplmM5lmAJkz/5kzzJkzmZkz
            ZpkzM5kzAJkA/5kAzJkAmZkAZpkAM5kAAGb//2b/zGb/mWb/Zmb/
            M2b/AGbM/2bMzGbMmWbMZmbMM2bMAGaZ/2aZzGaZmWaZZmaZM2aZ
            AGZm/2ZmzGZmmWZmZmZmM2ZmAGYz/2YzzGYzmWYzZmYzM2YzAGYA
            /2YAzGYAmWYAZmYAM2YAADP//zP/zDP/mTP/ZjP/MzP/ADPM/zPM
            zDPMmTPMZjPMMzPMADOZ/zOZzDOZmTOZZjOZMzOZADNm/zNmzDNm
            mTNmZjNmMzNmADMz/zMzzDMzmTMzZjMzMzMzADMA/zMAzDMAmTMA
            ZjMAMzMAAAD//wD/zAD/mQD/ZgD/MwD/AADM/wDMzADMmQDMZgDM
            MwDMAACZ/wCZzACZmQCZZgCZMwCZAABm/wBmzABmmQBmZgBmMwBm
            AAAz/wAzzAAzmQAzZgAzMwAzAAAA/wAAzAAAmQAAZgAAM+4AAN0A
            ALsAAKoAAIgAAHcAAFUAAEQAACIAABEAAADuAADdAAC7AACqAACI
            AAB3AABVAABEAAAiAAARAAAA7gAA3QAAuwAAqgAAiAAAdwAAVQAA
            RAAAIgAAEe7u7t3d3bu7u6qqqoiIiHd3d1VVVURERCIiIhEREQAA
            ACH5BAEAAAAALAAAAAAWABYAAAhIAAEIHEiwoEGBrhIeXEgwoUKG
            Cx0+hGhQoiuKBy1irChxY0GNHgeCDAlgZEiTHlFuVImRJUWXEGEy
            lBmxI8mSNknm1Dnx5sCAADs=
        """ )
    }

def addDictOption( opts, choicesDict, default, name, helpStr=None ):
    """Convenience function to add choices dicts to OptionParser.
       opts: OptionParser instance
       choicesDict: dictionary of valid choices, must include default
       default: default choice key
       name: long option name
       help: string"""
    if default not in choicesDict:
        raise Exception( 'Invalid  default %s for choices dict: %s' %
                         ( default, name ) )
    if not helpStr:
        helpStr = ( '|'.join( sorted( choicesDict.keys() ) ) +
                    '[,param=value...]' )
    opts.add_option( '--' + name,
                     type='string',
                     default = default,
                     help = helpStr )

if __name__ == '__main__':
    setLogLevel( 'info' )
    app = MiniEdit()
    """ import topology if specified """
    app.parseArgs()
    app.importTopo()

    app.mainloop()

########NEW FILE########
__FILENAME__ = multiping
#!/usr/bin/python

"""
multiping.py: monitor multiple sets of hosts using ping

This demonstrates how one may send a simple shell script to
multiple hosts and monitor their output interactively for a period=
of time.
"""

from mininet.net import Mininet
from mininet.node import Node
from mininet.topo import SingleSwitchTopo
from mininet.log import setLogLevel

from select import poll, POLLIN
from time import time

def chunks( l, n ):
    "Divide list l into chunks of size n - thanks Stackoverflow"
    return [ l[ i: i + n ] for i in range( 0, len( l ), n ) ]

def startpings( host, targetips ):
    "Tell host to repeatedly ping targets"

    targetips = ' '.join( targetips )

    # Simple ping loop
    cmd = ( 'while true; do '
            ' for ip in %s; do ' % targetips +
            '  echo -n %s "->" $ip ' % host.IP() +
            '   `ping -c1 -w 1 $ip | grep packets` ;'
            '  sleep 1;'
            ' done; '
            'done &' )

    print ( '*** Host %s (%s) will be pinging ips: %s' %
            ( host.name, host.IP(), targetips ) )

    host.cmd( cmd )

def multiping( netsize, chunksize, seconds):
    "Ping subsets of size chunksize in net of size netsize"

    # Create network and identify subnets
    topo = SingleSwitchTopo( netsize )
    net = Mininet( topo=topo )
    net.start()
    hosts = net.hosts
    subnets = chunks( hosts, chunksize )

    # Create polling object
    fds = [ host.stdout.fileno() for host in hosts ]
    poller = poll()
    for fd in fds:
        poller.register( fd, POLLIN )

    # Start pings
    for subnet in subnets:
        ips = [ host.IP() for host in subnet ]
        #adding bogus to generate packet loss
        ips.append( '10.0.0.200' )
        for host in subnet:
            startpings( host, ips )

    # Monitor output
    endTime = time() + seconds
    while time() < endTime:
        readable = poller.poll(1000)
        for fd, _mask in readable:
            node = Node.outToNode[ fd ]
            print '%s:' % node.name, node.monitor().strip()

    # Stop pings
    for host in hosts:
        host.cmd( 'kill %while' )

    net.stop()


if __name__ == '__main__':
    setLogLevel( 'info' )
    multiping( netsize=20, chunksize=4, seconds=10 )

########NEW FILE########
__FILENAME__ = multipoll
#!/usr/bin/python

"""
Simple example of sending output to multiple files and
monitoring them
"""

from mininet.topo import SingleSwitchTopo
from mininet.net import Mininet
from mininet.log import setLogLevel

from time import time
from select import poll, POLLIN
from subprocess import Popen, PIPE

def monitorFiles( outfiles, seconds, timeoutms ):
    "Monitor set of files and return [(host, line)...]"
    devnull = open( '/dev/null', 'w' )
    tails, fdToFile, fdToHost = {}, {}, {}
    for h, outfile in outfiles.iteritems():
        tail = Popen( [ 'tail', '-f', outfile ],
                      stdout=PIPE, stderr=devnull )
        fd = tail.stdout.fileno()
        tails[ h ] = tail
        fdToFile[ fd ] = tail.stdout
        fdToHost[ fd ] = h
    # Prepare to poll output files
    readable = poll()
    for t in tails.values():
        readable.register( t.stdout.fileno(), POLLIN )
    # Run until a set number of seconds have elapsed
    endTime = time() + seconds
    while time() < endTime:
        fdlist = readable.poll(timeoutms)
        if fdlist:
            for fd, _flags in fdlist:
                f = fdToFile[ fd ]
                host = fdToHost[ fd ]
                # Wait for a line of output
                line = f.readline().strip()
                yield host, line
        else:
            # If we timed out, return nothing
            yield None, ''
    for t in tails.values():
        t.terminate()
    devnull.close()  # Not really necessary


def monitorTest( N=3, seconds=3 ):
    "Run pings and monitor multiple hosts"
    topo = SingleSwitchTopo( N )
    net = Mininet( topo )
    net.start()
    hosts = net.hosts
    print "Starting test..."
    server = hosts[ 0 ]
    outfiles, errfiles = {}, {}
    for h in hosts:
        # Create and/or erase output files
        outfiles[ h ] = '/tmp/%s.out' % h.name
        errfiles[ h ] = '/tmp/%s.err' % h.name
        h.cmd( 'echo >', outfiles[ h ] )
        h.cmd( 'echo >', errfiles[ h ] )
        # Start pings
        h.cmdPrint('ping', server.IP(),
                   '>', outfiles[ h ],
                   '2>', errfiles[ h ],
                   '&' )
    print "Monitoring output for", seconds, "seconds"
    for h, line in monitorFiles( outfiles, seconds, timeoutms=500 ):
        if h:
            print '%s: %s' % ( h.name, line )
    for h in hosts:
        h.cmd('kill %ping')
    net.stop()


if __name__ == '__main__':
    setLogLevel('info')
    monitorTest()

########NEW FILE########
__FILENAME__ = multitest
#!/usr/bin/python

"""
This example shows how to create a network and run multiple tests.
For a more complicated test example, see udpbwtest.py.
"""

from mininet.cli import CLI
from mininet.log import lg, info
from mininet.net import Mininet
from mininet.node import OVSKernelSwitch
from mininet.topolib import TreeTopo

def ifconfigTest( net ):
    "Run ifconfig on all hosts in net."
    hosts = net.hosts
    for host in hosts:
        info( host.cmd( 'ifconfig' ) )

if __name__ == '__main__':
    lg.setLogLevel( 'info' )
    info( "*** Initializing Mininet and kernel modules\n" )
    OVSKernelSwitch.setup()
    info( "*** Creating network\n" )
    network = Mininet( TreeTopo( depth=2, fanout=2 ), switch=OVSKernelSwitch )
    info( "*** Starting network\n" )
    network.start()
    info( "*** Running ping test\n" )
    network.pingAll()
    info( "*** Running ifconfig test\n" )
    ifconfigTest( network )
    info( "*** Starting CLI (type 'exit' to exit)\n" )
    CLI( network )
    info( "*** Stopping network\n" )
    network.stop()

########NEW FILE########
__FILENAME__ = nat
#!/usr/bin/python

"""
Example to create a Mininet topology and connect it to the internet via NAT
through eth0 on the host.

Glen Gibb, February 2011

(slight modifications by BL, 5/13)
"""

from mininet.cli import CLI
from mininet.log import lg
from mininet.node import Node
from mininet.topolib import TreeNet

#################################
def startNAT( root, inetIntf='eth0', subnet='10.0/8' ):
    """Start NAT/forwarding between Mininet and external network
    root: node to access iptables from
    inetIntf: interface for internet access
    subnet: Mininet subnet (default 10.0/8)="""

    # Identify the interface connecting to the mininet network
    localIntf =  root.defaultIntf()

    # Flush any currently active rules
    root.cmd( 'iptables -F' )
    root.cmd( 'iptables -t nat -F' )

    # Create default entries for unmatched traffic
    root.cmd( 'iptables -P INPUT ACCEPT' )
    root.cmd( 'iptables -P OUTPUT ACCEPT' )
    root.cmd( 'iptables -P FORWARD DROP' )

    # Configure NAT
    root.cmd( 'iptables -I FORWARD -i', localIntf, '-d', subnet, '-j DROP' )
    root.cmd( 'iptables -A FORWARD -i', localIntf, '-s', subnet, '-j ACCEPT' )
    root.cmd( 'iptables -A FORWARD -i', inetIntf, '-d', subnet, '-j ACCEPT' )
    root.cmd( 'iptables -t nat -A POSTROUTING -o ', inetIntf, '-j MASQUERADE' )

    # Instruct the kernel to perform forwarding
    root.cmd( 'sysctl net.ipv4.ip_forward=1' )

def stopNAT( root ):
    """Stop NAT/forwarding between Mininet and external network"""
    # Flush any currently active rules
    root.cmd( 'iptables -F' )
    root.cmd( 'iptables -t nat -F' )

    # Instruct the kernel to stop forwarding
    root.cmd( 'sysctl net.ipv4.ip_forward=0' )

def fixNetworkManager( root, intf ):
    """Prevent network-manager from messing with our interface,
       by specifying manual configuration in /etc/network/interfaces
       root: a node in the root namespace (for running commands)
       intf: interface name"""
    cfile = '/etc/network/interfaces'
    line = '\niface %s inet manual\n' % intf
    config = open( cfile ).read()
    if line not in config:
        print '*** Adding', line.strip(), 'to', cfile
        with open( cfile, 'a' ) as f:
            f.write( line )
        # Probably need to restart network-manager to be safe -
        # hopefully this won't disconnect you
        root.cmd( 'service network-manager restart' )

def connectToInternet( network, switch='s1', rootip='10.254', subnet='10.0/8'):
    """Connect the network to the internet
       switch: switch to connect to root namespace
       rootip: address for interface in root namespace
       subnet: Mininet subnet"""
    switch = network.get( switch )
    prefixLen = subnet.split( '/' )[ 1 ]

    # Create a node in root namespace
    root = Node( 'root', inNamespace=False )

    # Prevent network-manager from interfering with our interface
    fixNetworkManager( root, 'root-eth0' )

    # Create link between root NS and switch
    link = network.addLink( root, switch )
    link.intf1.setIP( rootip, prefixLen )

    # Start network that now includes link to root namespace
    network.start()

    # Start NAT and establish forwarding
    startNAT( root )

    # Establish routes from end hosts
    for host in network.hosts:
        host.cmd( 'ip route flush root 0/0' )
        host.cmd( 'route add -net', subnet, 'dev', host.defaultIntf() )
        host.cmd( 'route add default gw', rootip )

    return root

if __name__ == '__main__':
    lg.setLogLevel( 'info')
    net = TreeNet( depth=1, fanout=4 )
    # Configure and start NATted connectivity
    rootnode = connectToInternet( net )
    print "*** Hosts are running and should have internet connectivity"
    print "*** Type 'exit' or control-D to shut down network"
    CLI( net )
    # Shut down NAT
    stopNAT( rootnode )
    net.stop()

########NEW FILE########
__FILENAME__ = popen
#!/usr/bin/python

"""
This example monitors a number of hosts using host.popen() and
pmonitor()
"""

from mininet.net import Mininet
from mininet.node import CPULimitedHost
from mininet.topo import SingleSwitchTopo
from mininet.log import setLogLevel
from mininet.util import custom, pmonitor

def monitorhosts( hosts=5, sched='cfs' ):
    "Start a bunch of pings and monitor them using popen"
    mytopo = SingleSwitchTopo( hosts )
    cpu = .5 / hosts
    myhost = custom( CPULimitedHost, cpu=cpu, sched=sched )
    net = Mininet( topo=mytopo, host=myhost )
    net.start()
    # Start a bunch of pings
    popens = {}
    last = net.hosts[ -1 ]
    for host in net.hosts:
        popens[ host ] = host.popen( "ping -c5 %s" % last.IP() )
        last = host
    # Monitor them and print output
    for host, line in pmonitor( popens ):
        if host:
            print "<%s>: %s" % ( host.name, line.strip() )
    # Done
    net.stop()

if __name__ == '__main__':
    setLogLevel( 'info' )
    monitorhosts( hosts=5 )

########NEW FILE########
__FILENAME__ = popenpoll
#!/usr/bin/python

"Monitor multiple hosts using popen()/pmonitor()"

from mininet.net import Mininet
from mininet.topo import SingleSwitchTopo
from mininet.util import pmonitor
from time import time
from signal import SIGINT

def pmonitorTest( N=3, seconds=10 ):
    "Run pings and monitor multiple hosts using pmonitor"
    topo = SingleSwitchTopo( N )
    net = Mininet( topo )
    net.start()
    hosts = net.hosts
    print "Starting test..."
    server = hosts[ 0 ]
    popens = {}
    for h in hosts:
        popens[ h ] = h.popen('ping', server.IP() )
    print "Monitoring output for", seconds, "seconds"
    endTime = time() + seconds
    for h, line in pmonitor( popens, timeoutms=500 ):
        if h:
            print '<%s>: %s' % ( h.name, line ),
        if time() >= endTime:
            for p in popens.values():
                p.send_signal( SIGINT )
    net.stop()

if __name__ == '__main__':
    pmonitorTest()

########NEW FILE########
__FILENAME__ = scratchnet
#!/usr/bin/python

"""
Build a simple network from scratch, using mininet primitives.
This is more complicated than using the higher-level classes,
but it exposes the configuration details and allows customization.

For most tasks, the higher-level API will be preferable.
"""

from mininet.net import Mininet
from mininet.node import Node
from mininet.link import Link
from mininet.log import setLogLevel, info
from mininet.util import quietRun

from time import sleep

def scratchNet( cname='controller', cargs='-v ptcp:' ):
    "Create network from scratch using Open vSwitch."

    info( "*** Creating nodes\n" )
    controller = Node( 'c0', inNamespace=False )
    switch = Node( 's0', inNamespace=False )
    h0 = Node( 'h0' )
    h1 = Node( 'h1' )

    info( "*** Creating links\n" )
    Link( h0, switch )
    Link( h1, switch )

    info( "*** Configuring hosts\n" )
    h0.setIP( '192.168.123.1/24' )
    h1.setIP( '192.168.123.2/24' )
    info( str( h0 ) + '\n' )
    info( str( h1 ) + '\n' )

    info( "*** Starting network using Open vSwitch\n" )
    controller.cmd( cname + ' ' + cargs + '&' )
    switch.cmd( 'ovs-vsctl del-br dp0' )
    switch.cmd( 'ovs-vsctl add-br dp0' )
    for intf in switch.intfs.values():
        print switch.cmd( 'ovs-vsctl add-port dp0 %s' % intf )

    # Note: controller and switch are in root namespace, and we
    # can connect via loopback interface
    switch.cmd( 'ovs-vsctl set-controller dp0 tcp:127.0.0.1:6633' )

    info( '*** Waiting for switch to connect to controller' )
    while 'is_connected' not in quietRun( 'ovs-vsctl show' ):
        sleep( 1 )
        info( '.' )
    info( '\n' )

    info( "*** Running test\n" )
    h0.cmdPrint( 'ping -c1 ' + h1.IP() )

    info( "*** Stopping network\n" )
    controller.cmd( 'kill %' + cname )
    switch.cmd( 'ovs-vsctl del-br dp0' )
    switch.deleteIntfs()
    info( '\n' )

if __name__ == '__main__':
    setLogLevel( 'info' )
    info( '*** Scratch network demo (kernel datapath)\n' )
    Mininet.init()
    scratchNet()

########NEW FILE########
__FILENAME__ = scratchnetuser
#!/usr/bin/python

"""
Build a simple network from scratch, using mininet primitives.
This is more complicated than using the higher-level classes,
but it exposes the configuration details and allows customization.

For most tasks, the higher-level API will be preferable.

This version uses the user datapath and an explicit control network.
"""

from mininet.net import Mininet
from mininet.node import Node
from mininet.link import Link
from mininet.log import setLogLevel, info

def linkIntfs( node1, node2 ):
    "Create link from node1 to node2 and return intfs"
    link = Link( node1, node2 )
    return link.intf1, link.intf2

def scratchNetUser( cname='controller', cargs='ptcp:' ):
    "Create network from scratch using user switch."

    # It's not strictly necessary for the controller and switches
    # to be in separate namespaces. For performance, they probably
    # should be in the root namespace. However, it's interesting to
    # see how they could work even if they are in separate namespaces.

    info( '*** Creating Network\n' )
    controller = Node( 'c0' )
    switch = Node( 's0')
    h0 = Node( 'h0' )
    h1 = Node( 'h1' )
    cintf, sintf = linkIntfs( controller, switch )
    h0intf, sintf1 = linkIntfs( h0, switch )
    h1intf, sintf2 = linkIntfs( h1, switch )

    info( '*** Configuring control network\n' )
    controller.setIP( '10.0.123.1/24', intf=cintf )
    switch.setIP( '10.0.123.2/24', intf=sintf)

    info( '*** Configuring hosts\n' )
    h0.setIP( '192.168.123.1/24', intf=h0intf )
    h1.setIP( '192.168.123.2/24', intf=h1intf )

    info( '*** Network state:\n' )
    for node in controller, switch, h0, h1:
        info( str( node ) + '\n' )

    info( '*** Starting controller and user datapath\n' )
    controller.cmd( cname + ' ' + cargs + '&' )
    switch.cmd( 'ifconfig lo 127.0.0.1' )
    intfs = [ str( i ) for i in sintf1, sintf2 ]
    switch.cmd( 'ofdatapath -i ' + ','.join( intfs ) + ' ptcp: &' )
    switch.cmd( 'ofprotocol tcp:' + controller.IP() + ' tcp:localhost &' )

    info( '*** Running test\n' )
    h0.cmdPrint( 'ping -c1 ' + h1.IP() )

    info( '*** Stopping network\n' )
    controller.cmd( 'kill %' + cname )
    switch.cmd( 'kill %ofdatapath' )
    switch.cmd( 'kill %ofprotocol' )
    switch.deleteIntfs()
    info( '\n' )

if __name__ == '__main__':
    setLogLevel( 'info' )
    info( '*** Scratch network demo (user datapath)\n' )
    Mininet.init()
    scratchNetUser()

########NEW FILE########
__FILENAME__ = simpleperf
#!/usr/bin/python

"""
Simple example of setting network and CPU parameters

NOTE: link params limit BW, add latency, and loss.
There is a high chance that pings WILL fail and that
iperf will hang indefinitely if the TCP handshake fails
to complete.
"""

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import CPULimitedHost
from mininet.link import TCLink
from mininet.util import dumpNodeConnections
from mininet.log import setLogLevel

class SingleSwitchTopo(Topo):
    "Single switch connected to n hosts."
    def __init__(self, n=2, **opts):
        Topo.__init__(self, **opts)
        switch = self.addSwitch('s1')
        for h in range(n):
            # Each host gets 50%/n of system CPU
            host = self.addHost('h%s' % (h + 1),
                                cpu=.5 / n)
            # 10 Mbps, 5ms delay, 10% loss
            self.addLink(host, switch,
                         bw=10, delay='5ms', loss=10, use_htb=True)

def perfTest():
    "Create network and run simple performance test"
    topo = SingleSwitchTopo(n=4)
    net = Mininet(topo=topo,
                  host=CPULimitedHost, link=TCLink)
    net.start()
    print "Dumping host connections"
    dumpNodeConnections(net.hosts)
    print "Testing network connectivity"
    net.pingAll()
    print "Testing bandwidth between h1 and h4"
    h1, h4 = net.getNodeByName('h1', 'h4')
    net.iperf((h1, h4))
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    perfTest()

########NEW FILE########
__FILENAME__ = sshd
#!/usr/bin/python

"""
Create a network and start sshd(8) on each host.

While something like rshd(8) would be lighter and faster,
(and perfectly adequate on an in-machine network)
the advantage of running sshd is that scripts can work
unchanged on mininet and hardware.

In addition to providing ssh access to hosts, this example
demonstrates:

- creating a convenience function to construct networks
- connecting the host network to the root namespace
- running server processes (sshd in this case) on hosts
"""

import sys

from mininet.net import Mininet
from mininet.cli import CLI
from mininet.log import lg
from mininet.node import Node
from mininet.topolib import TreeTopo
from mininet.link import Link

def TreeNet( depth=1, fanout=2, **kwargs ):
    "Convenience function for creating tree networks."
    topo = TreeTopo( depth, fanout )
    return Mininet( topo, **kwargs )

def connectToRootNS( network, switch, ip, routes ):
    """Connect hosts to root namespace via switch. Starts network.
      network: Mininet() network object
      switch: switch to connect to root namespace
      ip: IP address for root namespace node
      routes: host networks to route to"""
    # Create a node in root namespace and link to switch 0
    root = Node( 'root', inNamespace=False )
    intf = Link( root, switch ).intf1
    root.setIP( ip, intf=intf )
    # Start network that now includes link to root namespace
    network.start()
    # Add routes from root ns to hosts
    for route in routes:
        root.cmd( 'route add -net ' + route + ' dev ' + str( intf ) )

def sshd( network, cmd='/usr/sbin/sshd', opts='-D',
          ip='10.123.123.1/32', routes=None, switch=None ):
    """Start a network, connect it to root ns, and run sshd on all hosts.
       ip: root-eth0 IP address in root namespace (10.123.123.1/32)
       routes: Mininet host networks to route to (10.0/24)
       switch: Mininet switch to connect to root namespace (s1)"""
    if not switch:
        switch = network[ 's1' ]  # switch to use
    if not routes:
        routes = [ '10.0.0.0/24' ]
    connectToRootNS( network, switch, ip, routes )
    for host in network.hosts:
        host.cmd( cmd + ' ' + opts + '&' )
    print
    print "*** Hosts are running sshd at the following addresses:"
    print
    for host in network.hosts:
        print host.name, host.IP()
    print
    print "*** Type 'exit' or control-D to shut down network"
    CLI( network )
    for host in network.hosts:
        host.cmd( 'kill %' + cmd )
    network.stop()

if __name__ == '__main__':
    lg.setLogLevel( 'info')
    net = TreeNet( depth=1, fanout=4 )
    # get sshd args from the command line or use default args
    # useDNS=no -u0 to avoid reverse DNS lookup timeout
    opts = ' '.join( sys.argv[ 1: ] ) if len( sys.argv ) > 1 else (
        '-D -o UseDNS=no -u0' )
    sshd( net, opts=opts )

########NEW FILE########
__FILENAME__ = runner
#!/usr/bin/env python

"""
Run all mininet.examples tests
 -v : verbose output
 -quick : skip tests that take more than ~30 seconds
"""

import unittest
import os
import sys
from mininet.util import ensureRoot
from mininet.clean import cleanup

def runTests( testDir, verbosity=1 ):
    "discover and run all tests in testDir"
    # ensure root and cleanup before starting tests
    ensureRoot()
    cleanup()
    # discover all tests in testDir
    testSuite = unittest.defaultTestLoader.discover( testDir )
    # run tests
    unittest.TextTestRunner( verbosity=verbosity ).run( testSuite )

if __name__ == '__main__':
    # get the directory containing example tests
    testDir = os.path.dirname( os.path.realpath( __file__ ) )
    verbosity = 2 if '-v' in sys.argv else 1
    runTests( testDir, verbosity )

########NEW FILE########
__FILENAME__ = test_baresshd
#!/usr/bin/env python

"""
Tests for baresshd.py
"""

import unittest
import pexpect
from time import sleep
from mininet.clean import cleanup, sh

class testBareSSHD( unittest.TestCase ):

    opts = [ '\(yes/no\)\?', 'Welcome to h1', 'refused', pexpect.EOF, pexpect.TIMEOUT ]

    def connected( self ):
        "Log into ssh server, check banner, then exit"
        p = pexpect.spawn( 'ssh 10.0.0.1 -i /tmp/ssh/test_rsa exit' )
        while True:
            index = p.expect( self.opts )
            if index == 0:
                p.sendline( 'yes' )
            elif index == 1:
                return True
            else:
                return False

    def setUp( self ):
        # verify that sshd is not running
        self.assertFalse( self.connected() )
        # create public key pair for testing
        sh( 'rm -rf /tmp/ssh' )
        sh( 'mkdir /tmp/ssh' )
        sh( "ssh-keygen -t rsa -P '' -f /tmp/ssh/test_rsa" )
        sh( 'cat /tmp/ssh/test_rsa.pub >> /tmp/ssh/authorized_keys' )
        # run example with custom sshd args
        cmd = ( 'python -m mininet.examples.baresshd '
                '-o AuthorizedKeysFile=/tmp/ssh/authorized_keys '
                '-o StrictModes=no' )
        sh( cmd )

    def testSSH( self ):
        "Simple test to verify that we can ssh into h1"
        result = False
        # try to connect up to 3 times; sshd can take a while to start
        for _ in range( 3 ):
            result = self.connected()
            if result:
                break
            else:
                sleep( 1 )
        self.assertTrue( result )

    def tearDown( self ):
        # kill the ssh process
        sh( "ps aux | grep 'ssh.*Banner' | awk '{ print $2 }' | xargs kill" )
        cleanup()
        # remove public key pair
        sh( 'rm -rf /tmp/ssh' )

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_bind
#!/usr/bin/env python

"""
Tests for bind.py
"""

import unittest
import pexpect

class testBind( unittest.TestCase ):

    prompt = 'mininet>'

    def setUp( self ):
        self.net = pexpect.spawn( 'python -m mininet.examples.bind' )
        self.net.expect( "Private Directories: \[([\w\s,'/]+)\]" )
        self.directories = []
        # parse directories from mn output
        for d in self.net.match.group(1).split(', '):
            self.directories.append( d.strip("'") )
        self.net.expect( self.prompt )
        self.assertTrue( len( self.directories ) > 0 )

    def testCreateFile( self ):
        "Create a file, a.txt, in the first private directory and verify"
        fileName = 'a.txt'
        directory = self.directories[ 0 ]
        path = directory + '/' + fileName
        self.net.sendline( 'h1 touch %s; ls %s' % ( path, directory ) )
        index = self.net.expect( [ fileName, self.prompt ] )
        self.assertTrue( index == 0 )
        self.net.expect( self.prompt )
        self.net.sendline( 'h1 rm %s' % path )
        self.net.expect( self.prompt )

    def testIsolation( self ):
        "Create a file in two hosts and verify that contents are different"
        fileName = 'b.txt'
        directory = self.directories[ 0 ]
        path = directory + '/' + fileName
        contents = { 'h1' : '1', 'h2' : '2' }
        # Verify file doesn't exist, then write private copy of file
        for host in contents:
            value = contents[ host ]
            self.net.sendline( '%s cat %s' % ( host, path ) )
            self.net.expect( 'No such file' )
            self.net.expect( self.prompt )
            self.net.sendline( '%s echo %s > %s' % ( host, value, path ) )
            self.net.expect( self.prompt )
        # Verify file contents
        for host in contents:
            value = contents[ host ]
            self.net.sendline( '%s cat %s' % ( host, path ) )
            self.net.expect( value )
            self.net.expect( self.prompt )
            self.net.sendline( '%s rm %s' % ( host, path ) )
            self.net.expect( self.prompt )

    # TODO: need more tests

    def tearDown( self ):
        self.net.sendline( 'exit' )
        self.net.wait()

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_controllers
#!/usr/bin/env python

"""
Tests for controllers.py and controllers2.py
"""

import unittest
import pexpect

class testControllers( unittest.TestCase ):

    prompt = 'mininet>'

    def connectedTest( self, name, cmap ):
        "Verify that switches are connected to the controller specified by cmap"
        p = pexpect.spawn( 'python -m %s' % name )
        p.expect( self.prompt )
        # but first a simple ping test
        p.sendline( 'pingall' )
        p.expect ( '(\d+)% dropped' )
        percent = int( p.match.group( 1 ) ) if p.match else -1
        self.assertEqual( percent, 0 )
        p.expect( self.prompt )
        # verify connected controller
        for switch in cmap:
            p.sendline( 'sh ovs-vsctl get-controller %s' % switch )
            p.expect( 'tcp:([\d.:]+)')
            actual = p.match.group(1)
            expected = cmap[ switch ]
            self.assertEqual( actual, expected )
        p.expect( self.prompt )
        p.sendline( 'exit' )
        p.wait()

    def testControllers( self ):
        c0 = '127.0.0.1:6633'
        c1 = '127.0.0.1:6634'
        cmap = { 's1': c0, 's2': c1, 's3': c0 }
        self.connectedTest( 'mininet.examples.controllers', cmap )

    def testControllers2( self ):
        c0 = '127.0.0.1:6633'
        c1 = '127.0.0.1:6634'
        cmap = { 's1': c0, 's2': c1 }
        self.connectedTest( 'mininet.examples.controllers2', cmap )

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_controlnet
#!/usr/bin/env python

"""
Test for controlnet.py
"""

import unittest
import pexpect

class testControlNet( unittest.TestCase ):

    prompt = 'mininet>'

    def testPingall( self ):
        "Simple pingall test that verifies 0% packet drop in data network"
        p = pexpect.spawn( 'python -m mininet.examples.controlnet' )
        p.expect( self.prompt )
        p.sendline( 'pingall' )
        p.expect ( '(\d+)% dropped' )
        percent = int( p.match.group( 1 ) ) if p.match else -1
        self.assertEqual( percent, 0 )
        p.expect( self.prompt )
        p.sendline( 'exit' )
        p.wait()

    def testFailover( self ):
        "Kill controllers and verify that switch, s1, fails over properly"
        count = 1
        p = pexpect.spawn( 'python -m mininet.examples.controlnet' )
        p.expect( self.prompt )
        lp = pexpect.spawn( 'tail -f /tmp/s1-ofp.log' )
        lp.expect( 'tcp:\d+\.\d+\.\d+\.(\d+):\d+: connected' )
        ip = int( lp.match.group( 1 ) )
        self.assertEqual( count, ip )
        count += 1
        for c in [ 'c0', 'c1' ]:
            p.sendline( '%s ifconfig %s-eth0 down' % ( c, c) )
            p.expect( self.prompt )
            lp.expect( 'tcp:\d+\.\d+\.\d+\.(\d+):\d+: connected' )
            ip = int( lp.match.group( 1 ) )
            self.assertEqual( count, ip )
            count += 1
        p.sendline( 'exit' )
        p.wait()

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_cpu
#!/usr/bin/env python

"""
Test for cpu.py
"""

import unittest
import pexpect
import sys

class testCPU( unittest.TestCase ):

    prompt = 'mininet>'

    @unittest.skipIf( '-quick' in sys.argv, 'long test' )
    def testCPU( self ):
        "Verify that CPU utilization is monotonically decreasing for each scheduler"
        p = pexpect.spawn( 'python -m mininet.examples.cpu' )
        opts = [ '([a-z]+)\t([\d\.]+)%\t([\d\.]+)', pexpect.EOF ]
        scheds = []
        while True:
            index = p.expect( opts, timeout=600 )
            if index == 0:
                sched = p.match.group( 1 ) 
                cpu = float( p.match.group( 2 ) )
                bw = float( p.match.group( 3 ) )
                if sched not in scheds:
                    scheds.append( sched )
                    previous_bw = 10 ** 4 # 10 GB/s
                self.assertTrue( bw < previous_bw )
                previous_bw = bw
            else:
                break

        self.assertTrue( len( scheds ) > 0 )

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_emptynet
#!/usr/bin/env python

"""
Test for emptynet.py
"""

import unittest
import pexpect

class testEmptyNet( unittest.TestCase ):

    prompt = 'mininet>'

    def testEmptyNet( self ):
        "Run simple CLI tests: pingall (verify 0% drop) and iperf (sanity)"
        p = pexpect.spawn( 'python -m mininet.examples.emptynet' )
        p.expect( self.prompt )
        # pingall test
        p.sendline( 'pingall' )
        p.expect ( '(\d+)% dropped' )
        percent = int( p.match.group( 1 ) ) if p.match else -1
        self.assertEqual( percent, 0 ) 
        p.expect( self.prompt )
        # iperf test
        p.sendline( 'iperf' )
        p.expect( "Results: \['[\d.]+ .bits/sec', '[\d.]+ .bits/sec'\]" )
        p.expect( self.prompt )
        p.sendline( 'exit' )
        p.wait()

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_hwintf
#!/usr/bin/env python

"""
Test for hwintf.py
"""

import unittest
import re

import pexpect

from mininet.log import setLogLevel
from mininet.node import Node
from mininet.link import Link


class testHwintf( unittest.TestCase ):

    prompt = 'mininet>'

    def setUp( self ):
        self.h3 = Node( 't0', ip='10.0.0.3/8' )
        self.n0 = Node( 't1', inNamespace=False )
        Link( self.h3, self.n0 )
        self.h3.configDefault()

    def testLocalPing( self ):
        "Verify connectivity between virtual hosts using pingall"
        p = pexpect.spawn( 'python -m mininet.examples.hwintf %s' % self.n0.intf() )
        p.expect( self.prompt )
        p.sendline( 'pingall' )
        p.expect ( '(\d+)% dropped' )
        percent = int( p.match.group( 1 ) ) if p.match else -1
        self.assertEqual( percent, 0 )
        p.expect( self.prompt )
        p.sendline( 'exit' )
        p.wait()

    def testExternalPing( self ):
        "Verify connnectivity between virtual host and virtual-physical 'external' host "
        p = pexpect.spawn( 'python -m mininet.examples.hwintf %s' % self.n0.intf() )
        p.expect( self.prompt )
        # test ping external to internal
        expectStr = '(\d+) packets transmitted, (\d+) received'
        m = re.search( expectStr, self.h3.cmd( 'ping -v -c 1 10.0.0.1' ) )
        tx = m.group( 1 )
        rx = m.group( 2 )
        self.assertEqual( tx, rx )
        # test ping internal to external
        p.sendline( 'h1 ping -c 1 10.0.0.3')
        p.expect( expectStr )
        tx = p.match.group( 1 )
        rx = p.match.group( 2 )
        self.assertEqual( tx, rx )
        p.expect( self.prompt )
        p.sendline( 'exit' )
        p.wait()

    def tearDown( self ):
        self.h3.terminate()
        self.n0.terminate()

if __name__ == '__main__':
    setLogLevel( 'warning' )
    unittest.main()

########NEW FILE########
__FILENAME__ = test_limit
#!/usr/bin/env python

"""
Test for limit.py
"""

import unittest
import pexpect
import sys

class testLimit( unittest.TestCase ):

    @unittest.skipIf( '-quick' in sys.argv, 'long test' )
    def testLimit( self ):
        "Verify that CPU limits are within a 2% tolerance of limit for each scheduler"
        p = pexpect.spawn( 'python -m mininet.examples.limit' )
        opts = [ '\*\*\* Testing network ([\d\.]+) Mbps', 
                 '\*\*\* Results: \[([\d\., ]+)\]', 
                 pexpect.EOF ]
        count = 0
        bw = 0
        tolerance = 2
        while True:
            index = p.expect( opts )
            if index == 0:
                bw = float( p.match.group( 1 ) )
                count += 1
            elif index == 1:
                results = p.match.group( 1 )
                for x in results.split( ',' ):
                    result = float( x )
                    self.assertTrue( result < bw + tolerance )
                    self.assertTrue( result > bw - tolerance )
            else:
                break

        self.assertTrue( count > 0 )

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_linearbandwidth
#!/usr/bin/env python

"""
Test for linearbandwidth.py
"""

import unittest
import pexpect
import sys

class testLinearBandwidth( unittest.TestCase ):

    @unittest.skipIf( '-quick' in sys.argv, 'long test' )
    def testLinearBandwidth( self ):
        "Verify that bandwidth is monotonically decreasing as # of hops increases"
        p = pexpect.spawn( 'python -m mininet.examples.linearbandwidth' )
        count = 0
        opts = [ '\*\*\* Linear network results', 
                 '(\d+)\s+([\d\.]+) (.bits)', 
                 pexpect.EOF ]
        while True:
            index = p.expect( opts, timeout=600 )
            if index == 0:
                previous_bw = 10 ** 10 # 10 Gbits
                count += 1
            elif index == 1:
                n = int( p.match.group( 1 ) )
                bw = float( p.match.group( 2 ) )
                unit = p.match.group( 3 )
                if unit[ 0 ] == 'K':
                    bw *= 10 ** 3
                elif unit[ 0 ] == 'M':
                    bw *= 10 ** 6
                elif unit[ 0 ] == 'G':
                    bw *= 10 ** 9
                self.assertTrue( bw < previous_bw )
                previous_bw = bw
            else:
                break

        self.assertTrue( count > 0 )

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_multiping
#!/usr/bin/env python

"""
Test for multiping.py
"""

import unittest
import pexpect
from collections import defaultdict

class testMultiPing( unittest.TestCase ):

    def testMultiPing( self ):
        """Verify that each target is pinged at least once, and 
           that pings to 'real' targets are successful and unknown targets fail"""
        p = pexpect.spawn( 'python -m mininet.examples.multiping' )
        opts = [ "Host (h\d+) \(([\d.]+)\) will be pinging ips: ([\d\. ]+)",
                 "(h\d+): ([\d.]+) -> ([\d.]+) \d packets transmitted, (\d) received",
                 pexpect.EOF ]
        pings = defaultdict( list )
        while True:
            index = p.expect( opts )
            if index == 0:
                name = p.match.group(1)
                ip = p.match.group(2)
                targets = p.match.group(3).split()
                pings[ name ] += targets
            elif index == 1:
                name = p.match.group(1)
                ip = p.match.group(2)
                target = p.match.group(3)
                received = int( p.match.group(4) )
                if target == '10.0.0.200':
                    self.assertEqual( received, 0 )
                else:
                    self.assertEqual( received, 1 )
                try:
                    pings[ name ].remove( target )
                except:
                    pass
            else:
                break
        self.assertTrue( len( pings ) > 0 )
        for t in pings.values():
            self.assertEqual( len( t ), 0 )

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_multipoll
#!/usr/bin/env python

"""
Test for multipoll.py
"""

import unittest
import pexpect

class testMultiPoll( unittest.TestCase ):

    def testMultiPoll( self ):
        "Verify that we receive one ping per second per host"
        p = pexpect.spawn( 'python -m mininet.examples.multipoll' )
        opts = [ "\*\*\* (h\d) :" ,
                 "(h\d+): \d+ bytes from",
                 "Monitoring output for (\d+) seconds",
                 pexpect.EOF ]
        pings = {}
        while True:
            index = p.expect( opts )
            if index == 0:
                name = p.match.group( 1 )
                pings[ name ] = 0
            elif index == 1:
                name = p.match.group( 1 )
                pings[ name ] += 1
            elif index == 2:
                seconds = int( p.match.group( 1 ) )
            else:
                break
        self.assertTrue( len( pings ) > 0 )
        # make sure we have received at least one ping per second
        for count in pings.values():
            self.assertTrue( count >= seconds )

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_multitest
#!/usr/bin/env python

"""
Test for multitest.py
"""

import unittest
import pexpect

class testMultiTest( unittest.TestCase ):

    prompt = 'mininet>'

    def testMultiTest( self ):
        "Verify pingall (0% dropped) and hX-eth0 interface for each host (ifconfig)"
        p = pexpect.spawn( 'python -m mininet.examples.multitest' )
        p.expect( '(\d+)% dropped' )
        dropped = int( p.match.group( 1 ) )
        self.assertEqual( dropped, 0 )
        ifCount = 0
        while True:
            index = p.expect( [ 'h\d-eth0', self.prompt ] )
            if index == 0:
                ifCount += 1
            elif index == 1:
                p.sendline( 'exit' )
                break
        p.wait()
        self.assertEqual( ifCount, 4 )

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_nat
#!/usr/bin/env python

"""
Test for nat.py
"""

import unittest
import pexpect
from mininet.util import quietRun

destIP = '8.8.8.8' # Google DNS

class testNAT( unittest.TestCase ):

    prompt = 'mininet>'

    @unittest.skipIf( '0 received' in quietRun( 'ping -c 1 %s' % destIP ), 
                      'Destination IP is not reachable' )
    def testNAT( self ):
        "Attempt to ping an IP on the Internet and verify 0% packet loss"
        p = pexpect.spawn( 'python -m mininet.examples.nat' )
        p.expect( self.prompt )
        p.sendline( 'h1 ping -c 1 %s' % destIP )
        p.expect ( '(\d+)% packet loss' )
        percent = int( p.match.group( 1 ) ) if p.match else -1
        p.expect( self.prompt )
        p.sendline( 'exit' )
        p.wait()
        self.assertEqual( percent, 0 )

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_popen
#!/usr/bin/env python

"""
Test for popen.py and popenpoll.py
"""

import unittest
import pexpect

class testPopen( unittest.TestCase ):

    def pingTest( self, name ):
        "Verify that there are no dropped packets for each host"
        p = pexpect.spawn( 'python -m %s' % name )
        opts = [ "<(h\d+)>: PING ",
                 "<(h\d+)>: (\d+) packets transmitted, (\d+) received",
                 pexpect.EOF ]
        pings = {}
        while True:
            index = p.expect( opts )
            if index == 0:
                name = p.match.group(1)
                pings[ name ] = 0
            elif index == 1:
                name = p.match.group(1)
                transmitted = p.match.group(2)
                received = p.match.group(3)
                # verify no dropped packets
                self.assertEqual( received, transmitted )
                pings[ name ] += 1
            else:
                break
        self.assertTrue( len(pings) > 0 )
        # verify that each host has gotten results
        for count in pings.values():
            self.assertEqual( count, 1 )

    def testPopen( self ):
        self.pingTest( 'mininet.examples.popen' )

    def testPopenPoll( self ):
        self.pingTest( 'mininet.examples.popenpoll' )

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_scratchnet
#!/usr/bin/env python

"""
Test for scratchnet.py
"""

import unittest
import pexpect

class testScratchNet( unittest.TestCase ):

    opts = [ "1 packets transmitted, 1 received, 0% packet loss", pexpect.EOF ]

    def pingTest( self, name ):
        "Verify that no ping packets were dropped"
        p = pexpect.spawn( 'python -m %s' % name )
        index = p.expect( self.opts )
        self.assertEqual( index, 0 )

    def testPingKernel( self ):
        self.pingTest( 'mininet.examples.scratchnet' )

    def testPingUser( self ):
        self.pingTest( 'mininet.examples.scratchnetuser' )

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_simpleperf
#!/usr/bin/env python

"""
Test for simpleperf.py
"""

import unittest
import pexpect
import re
import sys
from mininet.log import setLogLevel
from mininet.net import Mininet
from mininet.node import CPULimitedHost
from mininet.link import TCLink

from mininet.examples.simpleperf import SingleSwitchTopo

class testSimplePerf( unittest.TestCase ):

    @unittest.skipIf( '-quick' in sys.argv, 'long test' )
    def testE2E( self ):
        "Run the example and verify ping and iperf results"
        p = pexpect.spawn( 'python -m mininet.examples.simpleperf' )
        # check ping results
        p.expect( "Results: (\d+)% dropped", timeout=120 )
        loss = int( p.match.group( 1 ) )
        self.assertTrue( 0 < loss < 100 )
        # check iperf results
        p.expect( "Results: \['([\d\.]+) .bits/sec", timeout=480 )
        bw = float( p.match.group( 1 ) )
        self.assertTrue( bw > 0 )
        p.wait()

    def testTopo( self ):
        """Import SingleSwitchTopo from example and test connectivity between two hosts
           Note: this test may fail very rarely because it is non-deterministic
           i.e. links are configured with 10% packet loss, but if we get unlucky and 
           none or all of the packets are dropped, the test will fail"""
        topo = SingleSwitchTopo( n=4 )
        net = Mininet( topo=topo, host=CPULimitedHost, link=TCLink )
        net.start()
        h1, h4 = net.get( 'h1', 'h4' )
        # have h1 ping h4 ten times
        expectStr = '(\d+) packets transmitted, (\d+) received, (\d+)% packet loss'
        output = h1.cmd( 'ping -c 10 %s' % h4.IP() )
        m = re.search( expectStr, output )
        loss = int( m.group( 3 ) )
        net.stop()
        self.assertTrue( 0 < loss < 100 )

if __name__ == '__main__':
    setLogLevel( 'warning' )
    unittest.main()

########NEW FILE########
__FILENAME__ = test_sshd
#!/usr/bin/env python

"""
Test for sshd.py
"""

import unittest
import pexpect
from mininet.clean import sh

class testSSHD( unittest.TestCase ):

    opts = [ '\(yes/no\)\?', 'refused', 'Welcome|\$|#', pexpect.EOF, pexpect.TIMEOUT ]

    def connected( self, ip ):
        "Log into ssh server, check banner, then exit"
        # Note: this test will fail if "Welcome" is not in the sshd banner 
        # and '#'' or '$'' are not in the prompt
        p = pexpect.spawn( 'ssh -i /tmp/ssh/test_rsa %s' % ip, timeout=10 )
        while True:
            index = p.expect( self.opts )
            if index == 0:
                print p.match.group(0)
                p.sendline( 'yes' )
            elif index == 1:
                return False
            elif index == 2:
                p.sendline( 'exit' )
                p.wait()    
                return True
            else:
                return False

    def setUp( self ):
        # create public key pair for testing
        sh( 'rm -rf /tmp/ssh' )
        sh( 'mkdir /tmp/ssh' )
        sh( "ssh-keygen -t rsa -P '' -f /tmp/ssh/test_rsa" )
        sh( 'cat /tmp/ssh/test_rsa.pub >> /tmp/ssh/authorized_keys' )
        cmd = ( 'python -m mininet.examples.sshd -D '
                '-o AuthorizedKeysFile=/tmp/ssh/authorized_keys '
                '-o StrictModes=no -o UseDNS=no -u0' )
        # run example with custom sshd args
        self.net = pexpect.spawn( cmd )
        self.net.expect( 'mininet>' )

    def testSSH( self ):
        "Verify that we can ssh into all hosts (h1 to h4)"
        for h in range( 1, 5 ):
            self.assertTrue( self.connected( '10.0.0.%d' % h ) )

    def tearDown( self ):
        self.net.sendline( 'exit' )
        self.net.wait()
        # remove public key pair
        sh( 'rm -rf /tmp/ssh' )

if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = test_tree1024
#!/usr/bin/env python

"""
Test for tree1024.py
"""

import unittest
import pexpect
import sys

class testTree1024( unittest.TestCase ):

    prompt = 'mininet>'

    @unittest.skipIf( '-quick' in sys.argv, 'long test' )
    def testTree1024( self ):
        "Run the example and do a simple ping test from h1 to h1024"
        p = pexpect.spawn( 'python -m mininet.examples.tree1024' )
        p.expect( self.prompt, timeout=6000 ) # it takes awhile to set up
        p.sendline( 'h1 ping -c 1 h1024' )
        p.expect ( '(\d+)% packet loss' )
        percent = int( p.match.group( 1 ) ) if p.match else -1
        p.expect( self.prompt )
        p.sendline( 'exit' )
        p.wait()
        self.assertEqual( percent, 0 )

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_treeping64
#!/usr/bin/env python

"""
Test for treeping64.py
"""

import unittest
import pexpect
import sys

class testTreePing64( unittest.TestCase ):

    prompt = 'mininet>'

    @unittest.skipIf( '-quick' in sys.argv, 'long test' )
    def testTreePing64( self ):
        "Run the example and verify ping results"
        p = pexpect.spawn( 'python -m mininet.examples.treeping64' )
        p.expect( 'Tree network ping results:', timeout=6000 )
        count = 0
        while True:
            index = p.expect( [ '(\d+)% packet loss', pexpect.EOF ] )
            if index == 0:
                percent = int( p.match.group( 1 ) ) if p.match else -1
                self.assertEqual( percent, 0 )
                count += 1
            else:
                break
        self.assertTrue( count > 0 )

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = tree1024
#!/usr/bin/python

"""
Create a 1024-host network, and run the CLI on it.
If this fails because of kernel limits, you may have
to adjust them, e.g. by adding entries to /etc/sysctl.conf
and running sysctl -p. Check util/sysctl_addon.
"""

from mininet.cli import CLI
from mininet.log import setLogLevel
from mininet.node import OVSKernelSwitch
from mininet.topolib import TreeNet

if __name__ == '__main__':
    setLogLevel( 'info' )
    network = TreeNet( depth=2, fanout=32, switch=OVSKernelSwitch )
    network.run( CLI, network )

########NEW FILE########
__FILENAME__ = treeping64
#!/usr/bin/python

"Create a 64-node tree network, and test connectivity using ping."

from mininet.log import setLogLevel
from mininet.node import UserSwitch, OVSKernelSwitch  # , KernelSwitch
from mininet.topolib import TreeNet

def treePing64():
    "Run ping test on 64-node tree networks."

    results = {}
    switches = {  # 'reference kernel': KernelSwitch,
                  'reference user': UserSwitch,
                  'Open vSwitch kernel': OVSKernelSwitch }

    for name in switches:
        print "*** Testing", name, "datapath"
        switch = switches[ name ]
        network = TreeNet( depth=2, fanout=8, switch=switch )
        result = network.run( network.pingAll )
        results[ name ] = result

    print
    print "*** Tree network ping results:"
    for name in switches:
        print "%s: %d%% packet loss" % ( name, results[ name ] )
    print

if __name__ == '__main__':
    setLogLevel( 'info' )
    treePing64()

########NEW FILE########
__FILENAME__ = clean
"""
Mininet Cleanup
author: Bob Lantz (rlantz@cs.stanford.edu)

Unfortunately, Mininet and OpenFlow (and the Linux kernel)
don't always clean up properly after themselves. Until they do
(or until cleanup functionality is integrated into the Python
code), this script may be used to get rid of unwanted garbage.
It may also get rid of 'false positives', but hopefully
nothing irreplaceable!
"""

from subprocess import Popen, PIPE
import time

from mininet.log import info
from mininet.term import cleanUpScreens

def sh( cmd ):
    "Print a command and send it to the shell"
    info( cmd + '\n' )
    return Popen( [ '/bin/sh', '-c', cmd ], stdout=PIPE ).communicate()[ 0 ]

def cleanup():
    """Clean up junk which might be left over from old runs;
       do fast stuff before slow dp and link removal!"""

    info("*** Removing excess controllers/ofprotocols/ofdatapaths/pings/noxes"
         "\n")
    zombies = 'controller ofprotocol ofdatapath ping nox_core lt-nox_core '
    zombies += 'ovs-openflowd ovs-controller udpbwtest mnexec ivs'
    # Note: real zombie processes can't actually be killed, since they
    # are already (un)dead. Then again,
    # you can't connect to them either, so they're mostly harmless.
    # Send SIGTERM first to give processes a chance to shutdown cleanly.
    sh( 'killall ' + zombies + ' 2> /dev/null' )
    time.sleep(1)
    sh( 'killall -9 ' + zombies + ' 2> /dev/null' )

    # And kill off sudo mnexec
    sh( 'pkill -9 -f "sudo mnexec"')

    info( "*** Removing junk from /tmp\n" )
    sh( 'rm -f /tmp/vconn* /tmp/vlogs* /tmp/*.out /tmp/*.log' )

    info( "*** Removing old X11 tunnels\n" )
    cleanUpScreens()

    info( "*** Removing excess kernel datapaths\n" )
    dps = sh( "ps ax | egrep -o 'dp[0-9]+' | sed 's/dp/nl:/'" ).splitlines()
    for dp in dps:
        if dp:
            sh( 'dpctl deldp ' + dp )

    info( "***  Removing OVS datapaths" )
    dps = sh("ovs-vsctl --timeout=1 list-br").strip().splitlines()
    if dps:
        sh( "ovs-vsctl " + " -- ".join( "--if-exists del-br " + dp
                                       for dp in dps if dp ) )
    # And in case the above didn't work...
    dps = sh("ovs-vsctl --timeout=1 list-br").strip().splitlines()
    for dp in dps:
        sh( 'ovs-vsctl del-br ' + dp )

    info( "*** Removing all links of the pattern foo-ethX\n" )
    links = sh( "ip link show | "
                "egrep -o '([-_.[:alnum:]]+-eth[[:digit:]]+)'" ).splitlines()
    for link in links:
        if link:
            sh( "ip link del " + link )

    info( "*** Cleanup complete.\n" )

########NEW FILE########
__FILENAME__ = cli
"""
A simple command-line interface for Mininet.

The Mininet CLI provides a simple control console which
makes it easy to talk to nodes. For example, the command

mininet> h27 ifconfig

runs 'ifconfig' on host h27.

Having a single console rather than, for example, an xterm for each
node is particularly convenient for networks of any reasonable
size.

The CLI automatically substitutes IP addresses for node names,
so commands like

mininet> h2 ping h3

should work correctly and allow host h2 to ping host h3

Several useful commands are provided, including the ability to
list all nodes ('nodes'), to print out the network topology
('net') and to check connectivity ('pingall', 'pingpair')
and bandwidth ('iperf'.)
"""

from subprocess import call
from cmd import Cmd
from os import isatty
from select import poll, POLLIN
import sys
import time
import os
import atexit

from mininet.log import info, output, error
from mininet.term import makeTerms, runX11
from mininet.util import quietRun, isShellBuiltin, dumpNodeConnections

class CLI( Cmd ):
    "Simple command-line interface to talk to nodes."

    prompt = 'mininet> '

    def __init__( self, mininet, stdin=sys.stdin, script=None ):
        self.mn = mininet
        # Local variable bindings for py command
        self.locals = { 'net': mininet }
        # Attempt to handle input
        self.stdin = stdin
        self.inPoller = poll()
        self.inPoller.register( stdin )
        self.inputFile = script
        Cmd.__init__( self )
        info( '*** Starting CLI:\n' )

        # Setup history if readline is available
        try:
            import readline
        except ImportError:
            pass
        else:
            history_path = os.path.expanduser('~/.mininet_history')
            if os.path.isfile(history_path):
                readline.read_history_file(history_path)
            atexit.register(lambda: readline.write_history_file(history_path))

        if self.inputFile:
            self.do_source( self.inputFile )
            return
        while True:
            try:
                # Make sure no nodes are still waiting
                for node in self.mn.values():
                    while node.waiting:
                        node.sendInt()
                        node.monitor()
                if self.isatty():
                    quietRun( 'stty sane' )
                self.cmdloop()
                break
            except KeyboardInterrupt:
                output( '\nInterrupt\n' )

    def emptyline( self ):
        "Don't repeat last command when you hit return."
        pass

    def getLocals( self ):
        "Local variable bindings for py command"
        self.locals.update( self.mn )
        return self.locals

    # Disable pylint "Unused argument: 'arg's'" messages, as well as
    # "method could be a function" warning, since each CLI function
    # must have the same interface
    # pylint: disable-msg=R0201

    helpStr = (
        'You may also send a command to a node using:\n'
        '  <node> command {args}\n'
        'For example:\n'
        '  mininet> h1 ifconfig\n'
        '\n'
        'The interpreter automatically substitutes IP addresses\n'
        'for node names when a node is the first arg, so commands\n'
        'like\n'
        '  mininet> h2 ping h3\n'
        'should work.\n'
        '\n'
        'Some character-oriented interactive commands require\n'
        'noecho:\n'
        '  mininet> noecho h2 vi foo.py\n'
        'However, starting up an xterm/gterm is generally better:\n'
        '  mininet> xterm h2\n\n'
    )

    def do_help( self, line ):
        "Describe available CLI commands."
        Cmd.do_help( self, line )
        if line is '':
            output( self.helpStr )

    def do_nodes( self, _line ):
        "List all nodes."
        nodes = ' '.join( sorted( self.mn ) )
        output( 'available nodes are: \n%s\n' % nodes )

    def do_net( self, _line ):
        "List network connections."
        dumpNodeConnections( self.mn.values() )

    def do_sh( self, line ):
        "Run an external shell command"
        call( line, shell=True )

    # do_py() and do_px() need to catch any exception during eval()/exec()
    # pylint: disable-msg=W0703

    def do_py( self, line ):
        """Evaluate a Python expression.
           Node names may be used, e.g.: py h1.cmd('ls')"""
        try:
            result = eval( line, globals(), self.getLocals() )
            if not result:
                return
            elif isinstance( result, str ):
                output( result + '\n' )
            else:
                output( repr( result ) + '\n' )
        except Exception, e:
            output( str( e ) + '\n' )

    # We are in fact using the exec() pseudo-function
    # pylint: disable-msg=W0122

    def do_px( self, line ):
        """Execute a Python statement.
            Node names may be used, e.g.: px print h1.cmd('ls')"""
        try:
            exec( line, globals(), self.getLocals() )
        except Exception, e:
            output( str( e ) + '\n' )

    # pylint: enable-msg=W0703,W0122

    def do_pingall( self, line ):
        "Ping between all hosts."
        self.mn.pingAll( line )

    def do_pingpair( self, _line ):
        "Ping between first two hosts, useful for testing."
        self.mn.pingPair()

    def do_pingallfull( self, _line ):
        "Ping between all hosts, returns all ping results."
        self.mn.pingAllFull()

    def do_pingpairfull( self, _line ):
        "Ping between first two hosts, returns all ping results."
        self.mn.pingPairFull()

    def do_iperf( self, line ):
        "Simple iperf TCP test between two (optionally specified) hosts."
        args = line.split()
        if not args:
            self.mn.iperf()
        elif len(args) == 2:
            hosts = []
            err = False
            for arg in args:
                if arg not in self.mn:
                    err = True
                    error( "node '%s' not in network\n" % arg )
                else:
                    hosts.append( self.mn[ arg ] )
            if not err:
                self.mn.iperf( hosts )
        else:
            error( 'invalid number of args: iperf src dst\n' )

    def do_iperfudp( self, line ):
        "Simple iperf UDP test between two (optionally specified) hosts."
        args = line.split()
        if not args:
            self.mn.iperf( l4Type='UDP' )
        elif len(args) == 3:
            udpBw = args[ 0 ]
            hosts = []
            err = False
            for arg in args[ 1:3 ]:
                if arg not in self.mn:
                    err = True
                    error( "node '%s' not in network\n" % arg )
                else:
                    hosts.append( self.mn[ arg ] )
            if not err:
                self.mn.iperf( hosts, l4Type='UDP', udpBw=udpBw )
        else:
            error( 'invalid number of args: iperfudp bw src dst\n' +
                   'bw examples: 10M\n' )

    def do_intfs( self, _line ):
        "List interfaces."
        for node in self.mn.values():
            output( '%s: %s\n' %
                    ( node.name, ','.join( node.intfNames() ) ) )

    def do_dump( self, _line ):
        "Dump node info."
        for node in self.mn.values():
            output( '%s\n' % repr( node ) )

    def do_link( self, line ):
        "Bring link(s) between two nodes up or down."
        args = line.split()
        if len(args) != 3:
            error( 'invalid number of args: link end1 end2 [up down]\n' )
        elif args[ 2 ] not in [ 'up', 'down' ]:
            error( 'invalid type: link end1 end2 [up down]\n' )
        else:
            self.mn.configLinkStatus( *args )

    def do_xterm( self, line, term='xterm' ):
        "Spawn xterm(s) for the given node(s)."
        args = line.split()
        if not args:
            error( 'usage: %s node1 node2 ...\n' % term )
        else:
            for arg in args:
                if arg not in self.mn:
                    error( "node '%s' not in network\n" % arg )
                else:
                    node = self.mn[ arg ]
                    self.mn.terms += makeTerms( [ node ], term = term )

    def do_x( self, line ):
        """Create an X11 tunnel to the given node,
           optionally starting a client."""
        args = line.split()
        if not args:
            error( 'usage: x node [cmd args]...\n' )
        else:
            node = self.mn[ args[ 0 ] ]
            cmd = args[ 1: ]
            self.mn.terms += runX11( node, cmd )

    def do_gterm( self, line ):
        "Spawn gnome-terminal(s) for the given node(s)."
        self.do_xterm( line, term='gterm' )

    def do_exit( self, _line ):
        "Exit"
        return 'exited by user command'

    def do_quit( self, line ):
        "Exit"
        return self.do_exit( line )

    def do_EOF( self, line ):
        "Exit"
        output( '\n' )
        return self.do_exit( line )

    def isatty( self ):
        "Is our standard input a tty?"
        return isatty( self.stdin.fileno() )

    def do_noecho( self, line ):
        "Run an interactive command with echoing turned off."
        if self.isatty():
            quietRun( 'stty -echo' )
        self.default( line )
        if self.isatty():
            quietRun( 'stty echo' )

    def do_source( self, line ):
        "Read commands from an input file."
        args = line.split()
        if len(args) != 1:
            error( 'usage: source <file>\n' )
            return
        try:
            self.inputFile = open( args[ 0 ] )
            while True:
                line = self.inputFile.readline()
                if len( line ) > 0:
                    self.onecmd( line )
                else:
                    break
        except IOError:
            error( 'error reading file %s\n' % args[ 0 ] )
        self.inputFile.close()
        self.inputFile = None

    def do_dpctl( self, line ):
        "Run dpctl (or ovs-ofctl) command on all switches."
        args = line.split()
        if len(args) < 1:
            error( 'usage: dpctl command [arg1] [arg2] ...\n' )
            return
        for sw in self.mn.switches:
            output( '*** ' + sw.name + ' ' + ('-' * 72) + '\n' )
            output( sw.dpctl( *args ) )

    def do_time( self, line ):
        "Measure time taken for any command in Mininet."
        start = time.time()
        self.onecmd(line)
        elapsed = time.time() - start
        self.stdout.write("*** Elapsed time: %0.6f secs\n" % elapsed)

    def default( self, line ):
        """Called on an input line when the command prefix is not recognized.
        Overridden to run shell commands when a node is the first CLI argument.
        Past the first CLI argument, node names are automatically replaced with
        corresponding IP addrs."""

        first, args, line = self.parseline( line )

        if first in self.mn:
            if not args:
                print "*** Enter a command for node: %s <cmd>" % first
                return
            node = self.mn[ first ]
            rest = args.split( ' ' )
            # Substitute IP addresses for node names in command
            # If updateIP() returns None, then use node name
            rest = [ self.mn[ arg ].defaultIntf().updateIP() or arg
                     if arg in self.mn else arg
                     for arg in rest ]
            rest = ' '.join( rest )
            # Run cmd on node:
            builtin = isShellBuiltin( first )
            node.sendCmd( rest, printPid=( not builtin ) )
            self.waitForNode( node )
        else:
            error( '*** Unknown command: %s\n' % line )

    # pylint: enable-msg=R0201

    def waitForNode( self, node ):
        "Wait for a node to finish, and  print its output."
        # Pollers
        nodePoller = poll()
        nodePoller.register( node.stdout )
        bothPoller = poll()
        bothPoller.register( self.stdin, POLLIN )
        bothPoller.register( node.stdout, POLLIN )
        if self.isatty():
            # Buffer by character, so that interactive
            # commands sort of work
            quietRun( 'stty -icanon min 1' )
        while True:
            try:
                bothPoller.poll()
                # XXX BL: this doesn't quite do what we want.
                if False and self.inputFile:
                    key = self.inputFile.read( 1 )
                    if key is not '':
                        node.write(key)
                    else:
                        self.inputFile = None
                if isReadable( self.inPoller ):
                    key = self.stdin.read( 1 )
                    node.write( key )
                if isReadable( nodePoller ):
                    data = node.monitor()
                    output( data )
                if not node.waiting:
                    break
            except KeyboardInterrupt:
                node.sendInt()

# Helper functions

def isReadable( poller ):
    "Check whether a Poll object has a readable fd."
    for fdmask in poller.poll( 0 ):
        mask = fdmask[ 1 ]
        if mask & POLLIN:
            return True

########NEW FILE########
__FILENAME__ = link
"""
link.py: interface and link abstractions for mininet

It seems useful to bundle functionality for interfaces into a single
class.

Also it seems useful to enable the possibility of multiple flavors of
links, including:

- simple veth pairs
- tunneled links
- patchable links (which can be disconnected and reconnected via a patchbay)
- link simulators (e.g. wireless)

Basic division of labor:

  Nodes: know how to execute commands
  Intfs: know how to configure themselves
  Links: know how to connect nodes together

Intf: basic interface object that can configure itself
TCIntf: interface with bandwidth limiting and delay via tc

Link: basic link class for creating veth pairs
"""

from mininet.log import info, error, debug
from mininet.util import makeIntfPair, quietRun
import re

class Intf( object ):

    "Basic interface object that can configure itself."

    def __init__( self, name, node=None, port=None, link=None, **params ):
        """name: interface name (e.g. h1-eth0)
           node: owning node (where this intf most likely lives)
           link: parent link if we're part of a link
           other arguments are passed to config()"""
        self.node = node
        self.name = name
        self.link = link
        self.mac, self.ip, self.prefixLen = None, None, None
        # Add to node (and move ourselves if necessary )
        node.addIntf( self, port=port )
        # Save params for future reference
        self.params = params
        self.config( **params )

    def cmd( self, *args, **kwargs ):
        "Run a command in our owning node"
        return self.node.cmd( *args, **kwargs )

    def ifconfig( self, *args ):
        "Configure ourselves using ifconfig"
        return self.cmd( 'ifconfig', self.name, *args )

    def setIP( self, ipstr, prefixLen=None ):
        """Set our IP address"""
        # This is a sign that we should perhaps rethink our prefix
        # mechanism and/or the way we specify IP addresses
        if '/' in ipstr:
            self.ip, self.prefixLen = ipstr.split( '/' )
            return self.ifconfig( ipstr, 'up' )
        else:
            self.ip, self.prefixLen = ipstr, prefixLen
            return self.ifconfig( '%s/%s' % ( ipstr, prefixLen ) )

    def setMAC( self, macstr ):
        """Set the MAC address for an interface.
           macstr: MAC address as string"""
        self.mac = macstr
        return ( self.ifconfig( 'down' ) +
                 self.ifconfig( 'hw', 'ether', macstr ) +
                 self.ifconfig( 'up' ) )

    _ipMatchRegex = re.compile( r'\d+\.\d+\.\d+\.\d+' )
    _macMatchRegex = re.compile( r'..:..:..:..:..:..' )

    def updateIP( self ):
        "Return updated IP address based on ifconfig"
        ifconfig = self.ifconfig()
        ips = self._ipMatchRegex.findall( ifconfig )
        self.ip = ips[ 0 ] if ips else None
        return self.ip

    def updateMAC( self ):
        "Return updated MAC address based on ifconfig"
        ifconfig = self.ifconfig()
        macs = self._macMatchRegex.findall( ifconfig )
        self.mac = macs[ 0 ] if macs else None
        return self.mac

    def IP( self ):
        "Return IP address"
        return self.ip

    def MAC( self ):
        "Return MAC address"
        return self.mac

    def isUp( self, setUp=False ):
        "Return whether interface is up"
        if setUp:
            self.ifconfig( 'up' )
        return "UP" in self.ifconfig()

    def rename( self, newname ):
        "Rename interface"
        self.ifconfig( 'down' )
        result = self.cmd( 'ip link set', self.name, 'name', newname )
        self.name = newname
        self.ifconfig( 'up' )
        return result

    # The reason why we configure things in this way is so
    # That the parameters can be listed and documented in
    # the config method.
    # Dealing with subclasses and superclasses is slightly
    # annoying, but at least the information is there!

    def setParam( self, results, method, **param ):
        """Internal method: configure a *single* parameter
           results: dict of results to update
           method: config method name
           param: arg=value (ignore if value=None)
           value may also be list or dict"""
        name, value = param.items()[ 0 ]
        f = getattr( self, method, None )
        if not f or value is None:
            return
        if type( value ) is list:
            result = f( *value )
        elif type( value ) is dict:
            result = f( **value )
        else:
            result = f( value )
        results[ name ] = result
        return result

    def config( self, mac=None, ip=None, ifconfig=None,
                up=True, **_params ):
        """Configure Node according to (optional) parameters:
           mac: MAC address
           ip: IP address
           ifconfig: arbitrary interface configuration
           Subclasses should override this method and call
           the parent class's config(**params)"""
        # If we were overriding this method, we would call
        # the superclass config method here as follows:
        # r = Parent.config( **params )
        r = {}
        self.setParam( r, 'setMAC', mac=mac )
        self.setParam( r, 'setIP', ip=ip )
        self.setParam( r, 'isUp', up=up )
        self.setParam( r, 'ifconfig', ifconfig=ifconfig )
        self.updateIP()
        self.updateMAC()
        return r

    def delete( self ):
        "Delete interface"
        self.cmd( 'ip link del ' + self.name )
        if self.node.inNamespace:
            # Link may have been dumped into root NS
            quietRun( 'ip link del ' + self.name )

    def __repr__( self ):
        return '<%s %s>' % ( self.__class__.__name__, self.name )

    def __str__( self ):
        return self.name


class TCIntf( Intf ):
    """Interface customized by tc (traffic control) utility
       Allows specification of bandwidth limits (various methods)
       as well as delay, loss and max queue length"""

    def bwCmds( self, bw=None, speedup=0, use_hfsc=False, use_tbf=False,
                latency_ms=None, enable_ecn=False, enable_red=False ):
        "Return tc commands to set bandwidth"

        cmds, parent = [], ' root '

        if bw and ( bw < 0 or bw > 1000 ):
            error( 'Bandwidth', bw, 'is outside range 0..1000 Mbps\n' )

        elif bw is not None:
            # BL: this seems a bit brittle...
            if ( speedup > 0 and
                 self.node.name[0:1] == 's' ):
                bw = speedup
            # This may not be correct - we should look more closely
            # at the semantics of burst (and cburst) to make sure we
            # are specifying the correct sizes. For now I have used
            # the same settings we had in the mininet-hifi code.
            if use_hfsc:
                cmds += [ '%s qdisc add dev %s root handle 5:0 hfsc default 1',
                          '%s class add dev %s parent 5:0 classid 5:1 hfsc sc '
                          + 'rate %fMbit ul rate %fMbit' % ( bw, bw ) ]
            elif use_tbf:
                if latency_ms is None:
                    latency_ms = 15 * 8 / bw
                cmds += [ '%s qdisc add dev %s root handle 5: tbf ' +
                          'rate %fMbit burst 15000 latency %fms' %
                          ( bw, latency_ms ) ]
            else:
                cmds += [ '%s qdisc add dev %s root handle 5:0 htb default 1',
                          '%s class add dev %s parent 5:0 classid 5:1 htb ' +
                          'rate %fMbit burst 15k' % bw ]
            parent = ' parent 5:1 '

            # ECN or RED
            if enable_ecn:
                cmds += [ '%s qdisc add dev %s' + parent +
                          'handle 6: red limit 1000000 ' +
                          'min 30000 max 35000 avpkt 1500 ' +
                          'burst 20 ' +
                          'bandwidth %fmbit probability 1 ecn' % bw ]
                parent = ' parent 6: '
            elif enable_red:
                cmds += [ '%s qdisc add dev %s' + parent +
                          'handle 6: red limit 1000000 ' +
                          'min 30000 max 35000 avpkt 1500 ' +
                          'burst 20 ' +
                          'bandwidth %fmbit probability 1' % bw ]
                parent = ' parent 6: '
        return cmds, parent

    @staticmethod
    def delayCmds( parent, delay=None, jitter=None,
                   loss=None, max_queue_size=None ):
        "Internal method: return tc commands for delay and loss"
        cmds = []
        if delay and delay < 0:
            error( 'Negative delay', delay, '\n' )
        elif jitter and jitter < 0:
            error( 'Negative jitter', jitter, '\n' )
        elif loss and ( loss < 0 or loss > 100 ):
            error( 'Bad loss percentage', loss, '%%\n' )
        else:
            # Delay/jitter/loss/max queue size
            netemargs = '%s%s%s%s' % (
                'delay %s ' % delay if delay is not None else '',
                '%s ' % jitter if jitter is not None else '',
                'loss %d ' % loss if loss is not None else '',
                'limit %d' % max_queue_size if max_queue_size is not None
                else '' )
            if netemargs:
                cmds = [ '%s qdisc add dev %s ' + parent +
                         ' handle 10: netem ' +
                         netemargs ]
                parent = ' parent 10:1 '
        return cmds, parent

    def tc( self, cmd, tc='tc' ):
        "Execute tc command for our interface"
        c = cmd % (tc, self)  # Add in tc command and our name
        debug(" *** executing command: %s\n" % c)
        return self.cmd( c )

    def config( self, bw=None, delay=None, jitter=None, loss=None,
                disable_gro=True, speedup=0, use_hfsc=False, use_tbf=False,
                latency_ms=None, enable_ecn=False, enable_red=False,
                max_queue_size=None, **params ):
        "Configure the port and set its properties."

        result = Intf.config( self, **params)

        # Disable GRO
        if disable_gro:
            self.cmd( 'ethtool -K %s gro off' % self )

        # Optimization: return if nothing else to configure
        # Question: what happens if we want to reset things?
        if ( bw is None and not delay and not loss
             and max_queue_size is None ):
            return

        # Clear existing configuration
        cmds = [ '%s qdisc del dev %s root' ]

        # Bandwidth limits via various methods
        bwcmds, parent = self.bwCmds( bw=bw, speedup=speedup,
                                      use_hfsc=use_hfsc, use_tbf=use_tbf,
                                      latency_ms=latency_ms,
                                      enable_ecn=enable_ecn,
                                      enable_red=enable_red )
        cmds += bwcmds

        # Delay/jitter/loss/max_queue_size using netem
        delaycmds, parent = self.delayCmds( delay=delay, jitter=jitter,
                                loss=loss, max_queue_size=max_queue_size,
                                parent=parent )
        cmds += delaycmds

        # Ugly but functional: display configuration info
        stuff = ( ( [ '%.2fMbit' % bw ] if bw is not None else [] ) +
                  ( [ '%s delay' % delay ] if delay is not None else [] ) +
                  ( [ '%s jitter' % jitter ] if jitter is not None else [] ) +
                  ( ['%d%% loss' % loss ] if loss is not None else [] ) +
                  ( [ 'ECN' ] if enable_ecn else [ 'RED' ]
                    if enable_red else [] ) )
        info( '(' + ' '.join( stuff ) + ') ' )

        # Execute all the commands in our node
        debug("at map stage w/cmds: %s\n" % cmds)
        tcoutputs = [ self.tc(cmd) for cmd in cmds ]
        debug( "cmds:", cmds, '\n' )
        debug( "outputs:", tcoutputs, '\n' )
        result[ 'tcoutputs'] = tcoutputs
        result[ 'parent' ] = parent

        return result


class Link( object ):

    """A basic link is just a veth pair.
       Other types of links could be tunnels, link emulators, etc.."""

    def __init__( self, node1, node2, port1=None, port2=None,
                  intfName1=None, intfName2=None,
                  intf=Intf, cls1=None, cls2=None, params1=None,
                  params2=None ):
        """Create veth link to another node, making two new interfaces.
           node1: first node
           node2: second node
           port1: node1 port number (optional)
           port2: node2 port number (optional)
           intf: default interface class/constructor
           cls1, cls2: optional interface-specific constructors
           intfName1: node1 interface name (optional)
           intfName2: node2  interface name (optional)
           params1: parameters for interface 1
           params2: parameters for interface 2"""
        # This is a bit awkward; it seems that having everything in
        # params would be more orthogonal, but being able to specify
        # in-line arguments is more convenient!
        if port1 is None:
            port1 = node1.newPort()
        if port2 is None:
            port2 = node2.newPort()
        if not intfName1:
            intfName1 = self.intfName( node1, port1 )
        if not intfName2:
            intfName2 = self.intfName( node2, port2 )

        self.makeIntfPair( intfName1, intfName2 )

        if not cls1:
            cls1 = intf
        if not cls2:
            cls2 = intf
        if not params1:
            params1 = {}
        if not params2:
            params2 = {}

        intf1 = cls1( name=intfName1, node=node1, port=port1,
                      link=self, **params1  )
        intf2 = cls2( name=intfName2, node=node2, port=port2,
                      link=self, **params2 )

        # All we are is dust in the wind, and our two interfaces
        self.intf1, self.intf2 = intf1, intf2

    @classmethod
    def intfName( cls, node, n ):
        "Construct a canonical interface name node-ethN for interface n."
        return node.name + '-eth' + repr( n )

    @classmethod
    def makeIntfPair( cls, intf1, intf2 ):
        """Create pair of interfaces
           intf1: name of interface 1
           intf2: name of interface 2
           (override this class method [and possibly delete()]
           to change link type)"""
        makeIntfPair( intf1, intf2  )

    def delete( self ):
        "Delete this link"
        self.intf1.delete()
        self.intf2.delete()

    def __str__( self ):
        return '%s<->%s' % ( self.intf1, self.intf2 )

class TCLink( Link ):
    "Link with symmetric TC interfaces configured via opts"
    def __init__( self, node1, node2, port1=None, port2=None,
                  intfName1=None, intfName2=None, **params ):
        Link.__init__( self, node1, node2, port1=port1, port2=port2,
                       intfName1=intfName1, intfName2=intfName2,
                       cls1=TCIntf,
                       cls2=TCIntf,
                       params1=params,
                       params2=params)

########NEW FILE########
__FILENAME__ = log
"Logging functions for Mininet."

import logging
from logging import Logger
import types

# Create a new loglevel, 'CLI info', which enables a Mininet user to see only
# the output of the commands they execute, plus any errors or warnings.  This
# level is in between info and warning.  CLI info-level commands should not be
# printed during regression tests.
OUTPUT = 25

LEVELS = { 'debug': logging.DEBUG,
           'info': logging.INFO,
           'output': OUTPUT,
           'warning': logging.WARNING,
           'error': logging.ERROR,
           'critical': logging.CRITICAL }

# change this to logging.INFO to get printouts when running unit tests
LOGLEVELDEFAULT = OUTPUT

#default: '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOGMSGFORMAT = '%(message)s'


# Modified from python2.5/__init__.py
class StreamHandlerNoNewline( logging.StreamHandler ):
    """StreamHandler that doesn't print newlines by default.
       Since StreamHandler automatically adds newlines, define a mod to more
       easily support interactive mode when we want it, or errors-only logging
       for running unit tests."""

    def emit( self, record ):
        """Emit a record.
           If a formatter is specified, it is used to format the record.
           The record is then written to the stream with a trailing newline
           [ N.B. this may be removed depending on feedback ]. If exception
           information is present, it is formatted using
           traceback.printException and appended to the stream."""
        try:
            msg = self.format( record )
            fs = '%s'  # was '%s\n'
            if not hasattr( types, 'UnicodeType' ):  # if no unicode support...
                self.stream.write( fs % msg )
            else:
                try:
                    self.stream.write( fs % msg )
                except UnicodeError:
                    self.stream.write( fs % msg.encode( 'UTF-8' ) )
            self.flush()
        except ( KeyboardInterrupt, SystemExit ):
            raise
        except:
            self.handleError( record )


class Singleton( type ):
    """Singleton pattern from Wikipedia
       See http://en.wikipedia.org/wiki/Singleton_Pattern

       Intended to be used as a __metaclass_ param, as shown for the class
       below."""

    def __init__( cls, name, bases, dict_ ):
        super( Singleton, cls ).__init__( name, bases, dict_ )
        cls.instance = None

    def __call__( cls, *args, **kw ):
        if cls.instance is None:
            cls.instance = super( Singleton, cls ).__call__( *args, **kw )
            return cls.instance


class MininetLogger( Logger, object ):
    """Mininet-specific logger
       Enable each mininet .py file to with one import:

       from mininet.log import [lg, info, error]

       ...get a default logger that doesn't require one newline per logging
       call.

       Inherit from object to ensure that we have at least one new-style base
       class, and can then use the __metaclass__ directive, to prevent this
       error:

       TypeError: Error when calling the metaclass bases
       a new-style class can't have only classic bases

       If Python2.5/logging/__init__.py defined Filterer as a new-style class,
       via Filterer( object ): rather than Filterer, we wouldn't need this.

       Use singleton pattern to ensure only one logger is ever created."""

    __metaclass__ = Singleton

    def __init__( self ):

        Logger.__init__( self, "mininet" )

        # create console handler
        ch = StreamHandlerNoNewline()
        # create formatter
        formatter = logging.Formatter( LOGMSGFORMAT )
        # add formatter to ch
        ch.setFormatter( formatter )
        # add ch to lg
        self.addHandler( ch )

        self.setLogLevel()

    def setLogLevel( self, levelname=None ):
        """Setup loglevel.
           Convenience function to support lowercase names.
           levelName: level name from LEVELS"""
        level = LOGLEVELDEFAULT
        if levelname is not None:
            if levelname not in LEVELS:
                raise Exception( 'unknown levelname seen in setLogLevel' )
            else:
                level = LEVELS.get( levelname, level )

        self.setLevel( level )
        self.handlers[ 0 ].setLevel( level )

    # pylint: disable-msg=E0202
    # "An attribute inherited from mininet.log hide this method"
    # Not sure why this is occurring - this function definitely gets called.

    # See /usr/lib/python2.5/logging/__init__.py; modified from warning()
    def output( self, msg, *args, **kwargs ):
        """Log 'msg % args' with severity 'OUTPUT'.

           To pass exception information, use the keyword argument exc_info
           with a true value, e.g.

           logger.warning("Houston, we have a %s", "cli output", exc_info=1)
        """
        if self.manager.disable >= OUTPUT:
            return
        if self.isEnabledFor( OUTPUT ):
            self._log( OUTPUT, msg, args, kwargs )

    # pylint: enable-msg=E0202

lg = MininetLogger()

# Make things a bit more convenient by adding aliases
# (info, warn, error, debug) and allowing info( 'this', 'is', 'OK' )
# In the future we may wish to make things more efficient by only
# doing the join (and calling the function) unless the logging level
# is high enough.

def makeListCompatible( fn ):
    """Return a new function allowing fn( 'a 1 b' ) to be called as
       newfn( 'a', 1, 'b' )"""

    def newfn( *args ):
        "Generated function. Closure-ish."
        if len( args ) == 1:
            return fn( *args )
        args = ' '.join( [ str( arg ) for arg in args ] )
        return fn( args )

    # Fix newfn's name and docstring
    setattr( newfn, '__name__', fn.__name__ )
    setattr( newfn, '__doc__', fn.__doc__ )
    return newfn

info, output, warn, error, debug = (
    lg.info, lg.output, lg.warn, lg.error, lg.debug ) = [
        makeListCompatible( f ) for f in
            lg.info, lg.output, lg.warn, lg.error, lg.debug ]

setLogLevel = lg.setLogLevel

########NEW FILE########
__FILENAME__ = moduledeps
"Module dependency utility functions for Mininet."

from mininet.util import quietRun
from mininet.log import info, error, debug
from os import environ

def lsmod():
    "Return output of lsmod."
    return quietRun( 'lsmod' )

def rmmod( mod ):
    """Return output of lsmod.
       mod: module string"""
    return quietRun( [ 'rmmod', mod ] )

def modprobe( mod ):
    """Return output of modprobe
       mod: module string"""
    return quietRun( [ 'modprobe', mod ] )

OF_KMOD = 'ofdatapath'
OVS_KMOD = 'openvswitch_mod'  # Renamed 'openvswitch' in OVS 1.7+/Linux 3.5+
TUN = 'tun'

def moduleDeps( subtract=None, add=None ):
    """Handle module dependencies.
       subtract: string or list of module names to remove, if already loaded
       add: string or list of module names to add, if not already loaded"""
    subtract = subtract if subtract is not None else []
    add = add if add is not None else []
    if type( subtract ) is str:
        subtract = [ subtract ]
    if type( add ) is str:
        add = [ add ]
    for mod in subtract:
        if mod in lsmod():
            info( '*** Removing ' + mod + '\n' )
            rmmodOutput = rmmod( mod )
            if rmmodOutput:
                error( 'Error removing ' + mod + ': "%s">\n' % rmmodOutput )
                exit( 1 )
            if mod in lsmod():
                error( 'Failed to remove ' + mod + '; still there!\n' )
                exit( 1 )
    for mod in add:
        if mod not in lsmod():
            info( '*** Loading ' + mod + '\n' )
            modprobeOutput = modprobe( mod )
            if modprobeOutput:
                error( 'Error inserting ' + mod +
                       ' - is it installed and available via modprobe?\n' +
                       'Error was: "%s"\n' % modprobeOutput )
            if mod not in lsmod():
                error( 'Failed to insert ' + mod + ' - quitting.\n' )
                exit( 1 )
        else:
            debug( '*** ' + mod + ' already loaded\n' )


def pathCheck( *args, **kwargs ):
    "Make sure each program in *args can be found in $PATH."
    moduleName = kwargs.get( 'moduleName', 'it' )
    for arg in args:
        if not quietRun( 'which ' + arg ):
            error( 'Cannot find required executable %s.\n' % arg +
                   'Please make sure that %s is installed ' % moduleName +
                   'and available in your $PATH:\n(%s)\n' % environ[ 'PATH' ] )
            exit( 1 )

########NEW FILE########
__FILENAME__ = net
"""

    Mininet: A simple networking testbed for OpenFlow/SDN!

author: Bob Lantz (rlantz@cs.stanford.edu)
author: Brandon Heller (brandonh@stanford.edu)

Mininet creates scalable OpenFlow test networks by using
process-based virtualization and network namespaces.

Simulated hosts are created as processes in separate network
namespaces. This allows a complete OpenFlow network to be simulated on
top of a single Linux kernel.

Each host has:

A virtual console (pipes to a shell)
A virtual interfaces (half of a veth pair)
A parent shell (and possibly some child processes) in a namespace

Hosts have a network interface which is configured via ifconfig/ip
link/etc.

This version supports both the kernel and user space datapaths
from the OpenFlow reference implementation (openflowswitch.org)
as well as OpenVSwitch (openvswitch.org.)

In kernel datapath mode, the controller and switches are simply
processes in the root namespace.

Kernel OpenFlow datapaths are instantiated using dpctl(8), and are
attached to the one side of a veth pair; the other side resides in the
host namespace. In this mode, switch processes can simply connect to the
controller via the loopback interface.

In user datapath mode, the controller and switches can be full-service
nodes that live in their own network namespaces and have management
interfaces and IP addresses on a control network (e.g. 192.168.123.1,
currently routed although it could be bridged.)

In addition to a management interface, user mode switches also have
several switch interfaces, halves of veth pairs whose other halves
reside in the host nodes that the switches are connected to.

Consistent, straightforward naming is important in order to easily
identify hosts, switches and controllers, both from the CLI and
from program code. Interfaces are named to make it easy to identify
which interfaces belong to which node.

The basic naming scheme is as follows:

    Host nodes are named h1-hN
    Switch nodes are named s1-sN
    Controller nodes are named c0-cN
    Interfaces are named {nodename}-eth0 .. {nodename}-ethN

Note: If the network topology is created using mininet.topo, then
node numbers are unique among hosts and switches (e.g. we have
h1..hN and SN..SN+M) and also correspond to their default IP addresses
of 10.x.y.z/8 where x.y.z is the base-256 representation of N for
hN. This mapping allows easy determination of a node's IP
address from its name, e.g. h1 -> 10.0.0.1, h257 -> 10.0.1.1.

Note also that 10.0.0.1 can often be written as 10.1 for short, e.g.
"ping 10.1" is equivalent to "ping 10.0.0.1".

Currently we wrap the entire network in a 'mininet' object, which
constructs a simulated network based on a network topology created
using a topology object (e.g. LinearTopo) from mininet.topo or
mininet.topolib, and a Controller which the switches will connect
to. Several configuration options are provided for functions such as
automatically setting MAC addresses, populating the ARP table, or
even running a set of terminals to allow direct interaction with nodes.

After the network is created, it can be started using start(), and a
variety of useful tasks maybe performed, including basic connectivity
and bandwidth tests and running the mininet CLI.

Once the network is up and running, test code can easily get access
to host and switch objects which can then be used for arbitrary
experiments, typically involving running a series of commands on the
hosts.

After all desired tests or activities have been completed, the stop()
method may be called to shut down the network.

"""

import os
import re
import select
import signal
from time import sleep
from itertools import chain, groupby

from mininet.cli import CLI
from mininet.log import info, error, debug, output
from mininet.node import Host, OVSKernelSwitch, Controller
from mininet.link import Link, Intf
from mininet.util import quietRun, fixLimits, numCores, ensureRoot
from mininet.util import macColonHex, ipStr, ipParse, netParse, ipAdd
from mininet.term import cleanUpScreens, makeTerms

# Mininet version: should be consistent with README and LICENSE
VERSION = "2.1.0+"

class Mininet( object ):
    "Network emulation with hosts spawned in network namespaces."

    def __init__( self, topo=None, switch=OVSKernelSwitch, host=Host,
                  controller=Controller, link=Link, intf=Intf,
                  build=True, xterms=False, cleanup=False, ipBase='10.0.0.0/8',
                  inNamespace=False,
                  autoSetMacs=False, autoStaticArp=False, autoPinCpus=False,
                  listenPort=None ):
        """Create Mininet object.
           topo: Topo (topology) object or None
           switch: default Switch class
           host: default Host class/constructor
           controller: default Controller class/constructor
           link: default Link class/constructor
           intf: default Intf class/constructor
           ipBase: base IP address for hosts,
           build: build now from topo?
           xterms: if build now, spawn xterms?
           cleanup: if build now, cleanup before creating?
           inNamespace: spawn switches and controller in net namespaces?
           autoSetMacs: set MAC addrs automatically like IP addresses?
           autoStaticArp: set all-pairs static MAC addrs?
           autoPinCpus: pin hosts to (real) cores (requires CPULimitedHost)?
           listenPort: base listening port to open; will be incremented for
               each additional switch in the net if inNamespace=False"""
        self.topo = topo
        self.switch = switch
        self.host = host
        self.controller = controller
        self.link = link
        self.intf = intf
        self.ipBase = ipBase
        self.ipBaseNum, self.prefixLen = netParse( self.ipBase )
        self.nextIP = 1  # start for address allocation
        self.inNamespace = inNamespace
        self.xterms = xterms
        self.cleanup = cleanup
        self.autoSetMacs = autoSetMacs
        self.autoStaticArp = autoStaticArp
        self.autoPinCpus = autoPinCpus
        self.numCores = numCores()
        self.nextCore = 0  # next core for pinning hosts to CPUs
        self.listenPort = listenPort

        self.hosts = []
        self.switches = []
        self.controllers = []

        self.nameToNode = {}  # name to Node (Host/Switch) objects

        self.terms = []  # list of spawned xterm processes

        Mininet.init()  # Initialize Mininet if necessary

        self.built = False
        if topo and build:
            self.build()

    def addHost( self, name, cls=None, **params ):
        """Add host.
           name: name of host to add
           cls: custom host class/constructor (optional)
           params: parameters for host
           returns: added host"""
        # Default IP and MAC addresses
        defaults = { 'ip': ipAdd( self.nextIP,
                                  ipBaseNum=self.ipBaseNum,
                                  prefixLen=self.prefixLen ) +
                                  '/%s' % self.prefixLen }
        if self.autoSetMacs:
            defaults[ 'mac'] = macColonHex( self.nextIP )
        if self.autoPinCpus:
            defaults[ 'cores' ] = self.nextCore
            self.nextCore = ( self.nextCore + 1 ) % self.numCores
        self.nextIP += 1
        defaults.update( params )
        if not cls:
            cls = self.host
        h = cls( name, **defaults )
        self.hosts.append( h )
        self.nameToNode[ name ] = h
        return h

    def addSwitch( self, name, cls=None, **params ):
        """Add switch.
           name: name of switch to add
           cls: custom switch class/constructor (optional)
           returns: added switch
           side effect: increments listenPort ivar ."""
        defaults = { 'listenPort': self.listenPort,
                     'inNamespace': self.inNamespace }
        defaults.update( params )
        if not cls:
            cls = self.switch
        sw = cls( name, **defaults )
        if not self.inNamespace and self.listenPort:
            self.listenPort += 1
        self.switches.append( sw )
        self.nameToNode[ name ] = sw
        return sw

    def addController( self, name='c0', controller=None, **params ):
        """Add controller.
           controller: Controller class"""
        # Get controller class
        if not controller:
            controller = self.controller
        # Construct new controller if one is not given
        if isinstance(name, Controller):
            controller_new = name
            # Pylint thinks controller is a str()
            # pylint: disable=E1103
            name = controller_new.name
            # pylint: enable=E1103
        else:
            controller_new = controller( name, **params )
        # Add new controller to net
        if controller_new:  # allow controller-less setups
            self.controllers.append( controller_new )
            self.nameToNode[ name ] = controller_new
        return controller_new

    # BL: We now have four ways to look up nodes
    # This may (should?) be cleaned up in the future.
    def getNodeByName( self, *args ):
        "Return node(s) with given name(s)"
        if len( args ) == 1:
            return self.nameToNode[ args[ 0 ] ]
        return [ self.nameToNode[ n ] for n in args ]

    def get( self, *args ):
        "Convenience alias for getNodeByName"
        return self.getNodeByName( *args )

    # Even more convenient syntax for node lookup and iteration
    def __getitem__( self, key ):
        """net [ name ] operator: Return node(s) with given name(s)"""
        return self.nameToNode[ key ]

    def __iter__( self ):
        "return iterator over node names"
        for node in chain( self.hosts, self.switches, self.controllers ):
            yield node.name

    def __len__( self ):
        "returns number of nodes in net"
        return ( len( self.hosts ) + len( self.switches ) +
                 len( self.controllers ) )

    def __contains__( self, item ):
        "returns True if net contains named node"
        return item in self.nameToNode

    def keys( self ):
        "return a list of all node names or net's keys"
        return list( self )

    def values( self ):
        "return a list of all nodes or net's values"
        return [ self[name] for name in self ]

    def items( self ):
        "return (key,value) tuple list for every node in net"
        return zip( self.keys(), self.values() )

    def addLink( self, node1, node2, port1=None, port2=None,
                 cls=None, **params ):
        """"Add a link from node1 to node2
            node1: source node
            node2: dest node
            port1: source port
            port2: dest port
            returns: link object"""
        defaults = { 'port1': port1,
                     'port2': port2,
                     'intf': self.intf }
        defaults.update( params )
        if not cls:
            cls = self.link
        return cls( node1, node2, **defaults )

    def configHosts( self ):
        "Configure a set of hosts."
        for host in self.hosts:
            info( host.name + ' ' )
            intf = host.defaultIntf()
            if intf:
                host.configDefault()
            else:
                # Don't configure nonexistent intf
                host.configDefault( ip=None, mac=None )
            # You're low priority, dude!
            # BL: do we want to do this here or not?
            # May not make sense if we have CPU lmiting...
            # quietRun( 'renice +18 -p ' + repr( host.pid ) )
            # This may not be the right place to do this, but
            # it needs to be done somewhere.
            host.cmd( 'ifconfig lo up' )
        info( '\n' )

    def buildFromTopo( self, topo=None ):
        """Build mininet from a topology object
           At the end of this function, everything should be connected
           and up."""

        # Possibly we should clean up here and/or validate
        # the topo
        if self.cleanup:
            pass

        info( '*** Creating network\n' )

        if not self.controllers and self.controller:
            # Add a default controller
            info( '*** Adding controller\n' )
            classes = self.controller
            if type( classes ) is not list:
                classes = [ classes ]
            for i, cls in enumerate( classes ):
                self.addController( 'c%d' % i, cls )

        info( '*** Adding hosts:\n' )
        for hostName in topo.hosts():
            self.addHost( hostName, **topo.nodeInfo( hostName ) )
            info( hostName + ' ' )

        info( '\n*** Adding switches:\n' )
        for switchName in topo.switches():
            self.addSwitch( switchName, **topo.nodeInfo( switchName) )
            info( switchName + ' ' )

        info( '\n*** Adding links:\n' )
        for srcName, dstName in topo.links(sort=True):
            src, dst = self.nameToNode[ srcName ], self.nameToNode[ dstName ]
            params = topo.linkInfo( srcName, dstName )
            srcPort, dstPort = topo.port( srcName, dstName )
            self.addLink( src, dst, srcPort, dstPort, **params )
            info( '(%s, %s) ' % ( src.name, dst.name ) )

        info( '\n' )

    def configureControlNetwork( self ):
        "Control net config hook: override in subclass"
        raise Exception( 'configureControlNetwork: '
                         'should be overriden in subclass', self )

    def build( self ):
        "Build mininet."
        if self.topo:
            self.buildFromTopo( self.topo )
        if self.inNamespace:
            self.configureControlNetwork()
        info( '*** Configuring hosts\n' )
        self.configHosts()
        if self.xterms:
            self.startTerms()
        if self.autoStaticArp:
            self.staticArp()
        self.built = True

    def startTerms( self ):
        "Start a terminal for each node."
        if 'DISPLAY' not in os.environ:
            error( "Error starting terms: Cannot connect to display\n" )
            return
        info( "*** Running terms on %s\n" % os.environ[ 'DISPLAY' ] )
        cleanUpScreens()
        self.terms += makeTerms( self.controllers, 'controller' )
        self.terms += makeTerms( self.switches, 'switch' )
        self.terms += makeTerms( self.hosts, 'host' )

    def stopXterms( self ):
        "Kill each xterm."
        for term in self.terms:
            os.kill( term.pid, signal.SIGKILL )
        cleanUpScreens()

    def staticArp( self ):
        "Add all-pairs ARP entries to remove the need to handle broadcast."
        for src in self.hosts:
            for dst in self.hosts:
                if src != dst:
                    src.setARP( ip=dst.IP(), mac=dst.MAC() )

    def start( self ):
        "Start controller and switches."
        if not self.built:
            self.build()
        info( '*** Starting controller\n' )
        for controller in self.controllers:
            controller.start()
        info( '*** Starting %s switches\n' % len( self.switches ) )
        for switch in self.switches:
            info( switch.name + ' ')
            switch.start( self.controllers )
        info( '\n' )

    def stop( self ):
        "Stop the controller(s), switches and hosts"
        if self.terms:
            info( '*** Stopping %i terms\n' % len( self.terms ) )
            self.stopXterms()
        info( '*** Stopping %i switches\n' % len( self.switches ) )
        for swclass, switches in groupby( sorted( self.switches, key=type ), type ):
            if hasattr( swclass, 'batchShutdown' ):
                swclass.batchShutdown( switches )
        for switch in self.switches:
            info( switch.name + ' ' )
            switch.stop()
        info( '\n' )
        info( '*** Stopping %i hosts\n' % len( self.hosts ) )
        for host in self.hosts:
            info( host.name + ' ' )
            host.terminate()
        info( '\n' )
        info( '*** Stopping %i controllers\n' % len( self.controllers ) )
        for controller in self.controllers:
            info( controller.name + ' ' )
            controller.stop()
        info( '\n*** Done\n' )

    def run( self, test, *args, **kwargs ):
        "Perform a complete start/test/stop cycle."
        self.start()
        info( '*** Running test\n' )
        result = test( *args, **kwargs )
        self.stop()
        return result

    def monitor( self, hosts=None, timeoutms=-1 ):
        """Monitor a set of hosts (or all hosts by default),
           and return their output, a line at a time.
           hosts: (optional) set of hosts to monitor
           timeoutms: (optional) timeout value in ms
           returns: iterator which returns host, line"""
        if hosts is None:
            hosts = self.hosts
        poller = select.poll()
        Node = hosts[ 0 ]  # so we can call class method fdToNode
        for host in hosts:
            poller.register( host.stdout )
        while True:
            ready = poller.poll( timeoutms )
            for fd, event in ready:
                host = Node.fdToNode( fd )
                if event & select.POLLIN:
                    line = host.readline()
                    if line is not None:
                        yield host, line
            # Return if non-blocking
            if not ready and timeoutms >= 0:
                yield None, None

    # XXX These test methods should be moved out of this class.
    # Probably we should create a tests.py for them

    @staticmethod
    def _parsePing( pingOutput ):
        "Parse ping output and return packets sent, received."
        # Check for downed link
        if 'connect: Network is unreachable' in pingOutput:
            return 1, 0
        r = r'(\d+) packets transmitted, (\d+) received'
        m = re.search( r, pingOutput )
        if m is None:
            error( '*** Error: could not parse ping output: %s\n' %
                   pingOutput )
            return 1, 0
        sent, received = int( m.group( 1 ) ), int( m.group( 2 ) )
        return sent, received

    def ping( self, hosts=None, timeout=None ):
        """Ping between all specified hosts.
           hosts: list of hosts
           timeout: time to wait for a response, as string
           returns: ploss packet loss percentage"""
        # should we check if running?
        packets = 0
        lost = 0
        ploss = None
        if not hosts:
            hosts = self.hosts
            output( '*** Ping: testing ping reachability\n' )
        for node in hosts:
            output( '%s -> ' % node.name )
            for dest in hosts:
                if node != dest:
                    opts = ''
                    if timeout:
                        opts = '-W %s' % timeout
                    result = node.cmd( 'ping -c1 %s %s' % (opts, dest.IP()) )
                    sent, received = self._parsePing( result )
                    packets += sent
                    if received > sent:
                        error( '*** Error: received too many packets' )
                        error( '%s' % result )
                        node.cmdPrint( 'route' )
                        exit( 1 )
                    lost += sent - received
                    output( ( '%s ' % dest.name ) if received else 'X ' )
            output( '\n' )
        if packets > 0:
            ploss = 100.0 * lost / packets
            received = packets - lost
            output( "*** Results: %i%% dropped (%d/%d received)\n" %
                    ( ploss, received, packets ) )
        else:
            ploss = 0
            output( "*** Warning: No packets sent\n" )
        return ploss

    @staticmethod
    def _parsePingFull( pingOutput ):
        "Parse ping output and return all data."
        errorTuple = (1, 0, 0, 0, 0, 0)
        # Check for downed link
        r = r'[uU]nreachable'
        m = re.search( r, pingOutput )
        if m is not None:
            return errorTuple
        r = r'(\d+) packets transmitted, (\d+) received'
        m = re.search( r, pingOutput )
        if m is None:
            error( '*** Error: could not parse ping output: %s\n' %
                   pingOutput )
            return errorTuple
        sent, received = int( m.group( 1 ) ), int( m.group( 2 ) )
        r = r'rtt min/avg/max/mdev = '
        r += r'(\d+\.\d+)/(\d+\.\d+)/(\d+\.\d+)/(\d+\.\d+) ms'
        m = re.search( r, pingOutput )
        if m is None:
            error( '*** Error: could not parse ping output: %s\n' %
                   pingOutput )
            return errorTuple
        rttmin = float( m.group( 1 ) )
        rttavg = float( m.group( 2 ) )
        rttmax = float( m.group( 3 ) )
        rttdev = float( m.group( 4 ) )
        return sent, received, rttmin, rttavg, rttmax, rttdev

    def pingFull( self, hosts=None, timeout=None ):
        """Ping between all specified hosts and return all data.
           hosts: list of hosts
           timeout: time to wait for a response, as string
           returns: all ping data; see function body."""
        # should we check if running?
        # Each value is a tuple: (src, dsd, [all ping outputs])
        all_outputs = []
        if not hosts:
            hosts = self.hosts
            output( '*** Ping: testing ping reachability\n' )
        for node in hosts:
            output( '%s -> ' % node.name )
            for dest in hosts:
                if node != dest:
                    opts = ''
                    if timeout:
                        opts = '-W %s' % timeout
                    result = node.cmd( 'ping -c1 %s %s' % (opts, dest.IP()) )
                    outputs = self._parsePingFull( result )
                    sent, received, rttmin, rttavg, rttmax, rttdev = outputs
                    all_outputs.append( (node, dest, outputs) )
                    output( ( '%s ' % dest.name ) if received else 'X ' )
            output( '\n' )
        output( "*** Results: \n" )
        for outputs in all_outputs:
            src, dest, ping_outputs = outputs
            sent, received, rttmin, rttavg, rttmax, rttdev = ping_outputs
            output( " %s->%s: %s/%s, " % (src, dest, sent, received ) )
            output( "rtt min/avg/max/mdev %0.3f/%0.3f/%0.3f/%0.3f ms\n" %
                    (rttmin, rttavg, rttmax, rttdev) )
        return all_outputs

    def pingAll( self, timeout=None ):
        """Ping between all hosts.
           returns: ploss packet loss percentage"""
        return self.ping( timeout=timeout )

    def pingPair( self ):
        """Ping between first two hosts, useful for testing.
           returns: ploss packet loss percentage"""
        hosts = [ self.hosts[ 0 ], self.hosts[ 1 ] ]
        return self.ping( hosts=hosts )

    def pingAllFull( self ):
        """Ping between all hosts.
           returns: ploss packet loss percentage"""
        return self.pingFull()

    def pingPairFull( self ):
        """Ping between first two hosts, useful for testing.
           returns: ploss packet loss percentage"""
        hosts = [ self.hosts[ 0 ], self.hosts[ 1 ] ]
        return self.pingFull( hosts=hosts )

    @staticmethod
    def _parseIperf( iperfOutput ):
        """Parse iperf output and return bandwidth.
           iperfOutput: string
           returns: result string"""
        r = r'([\d\.]+ \w+/sec)'
        m = re.findall( r, iperfOutput )
        if m:
            return m[-1]
        else:
            # was: raise Exception(...)
            error( 'could not parse iperf output: ' + iperfOutput )
            return ''

    # XXX This should be cleaned up

    def iperf( self, hosts=None, l4Type='TCP', udpBw='10M' ):
        """Run iperf between two hosts.
           hosts: list of hosts; if None, uses opposite hosts
           l4Type: string, one of [ TCP, UDP ]
           returns: results two-element array of server and client speeds"""
        if not quietRun( 'which telnet' ):
            error( 'Cannot find telnet in $PATH - required for iperf test' )
            return
        if not hosts:
            hosts = [ self.hosts[ 0 ], self.hosts[ -1 ] ]
        else:
            assert len( hosts ) == 2
        client, server = hosts
        output( '*** Iperf: testing ' + l4Type + ' bandwidth between ' )
        output( "%s and %s\n" % ( client.name, server.name ) )
        server.cmd( 'killall -9 iperf' )
        iperfArgs = 'iperf '
        bwArgs = ''
        if l4Type == 'UDP':
            iperfArgs += '-u '
            bwArgs = '-b ' + udpBw + ' '
        elif l4Type != 'TCP':
            raise Exception( 'Unexpected l4 type: %s' % l4Type )
        server.sendCmd( iperfArgs + '-s', printPid=True )
        servout = ''
        while server.lastPid is None:
            servout += server.monitor()
        if l4Type == 'TCP':
            while 'Connected' not in client.cmd(
                    'sh -c "echo A | telnet -e A %s 5001"' % server.IP()):
                output('waiting for iperf to start up...')
                sleep(.5)
        cliout = client.cmd( iperfArgs + '-t 5 -c ' + server.IP() + ' ' +
                             bwArgs )
        debug( 'Client output: %s\n' % cliout )
        server.sendInt()
        servout += server.waitOutput()
        debug( 'Server output: %s\n' % servout )
        result = [ self._parseIperf( servout ), self._parseIperf( cliout ) ]
        if l4Type == 'UDP':
            result.insert( 0, udpBw )
        output( '*** Results: %s\n' % result )
        return result

    def runCpuLimitTest( self, cpu, duration=5 ):
        """run CPU limit test with 'while true' processes.
        cpu: desired CPU fraction of each host
        duration: test duration in seconds
        returns a single list of measured CPU fractions as floats.
        """
        pct = cpu * 100
        info('*** Testing CPU %.0f%% bandwidth limit\n' % pct)
        hosts = self.hosts
        for h in hosts:
            h.cmd( 'while true; do a=1; done &' )
        pids = [h.cmd( 'echo $!' ).strip() for h in hosts]
        pids_str = ",".join(["%s" % pid for pid in pids])
        cmd = 'ps -p %s -o pid,%%cpu,args' % pids_str
        # It's a shame that this is what pylint prefers
        outputs = []
        for _ in range( duration ):
            sleep( 1 )
            outputs.append( quietRun( cmd ).strip() )
        for h in hosts:
            h.cmd( 'kill %1' )
        cpu_fractions = []
        for test_output in outputs:
            # Split by line.  Ignore first line, which looks like this:
            # PID %CPU COMMAND\n
            for line in test_output.split('\n')[1:]:
                r = r'\d+\s*(\d+\.\d+)'
                m = re.search( r, line )
                if m is None:
                    error( '*** Error: could not extract CPU fraction: %s\n' %
                           line )
                    return None
                cpu_fractions.append( float( m.group( 1 ) ) )
        output( '*** Results: %s\n' % cpu_fractions )
        return cpu_fractions

    # BL: I think this can be rewritten now that we have
    # a real link class.
    def configLinkStatus( self, src, dst, status ):
        """Change status of src <-> dst links.
           src: node name
           dst: node name
           status: string {up, down}"""
        if src not in self.nameToNode:
            error( 'src not in network: %s\n' % src )
        elif dst not in self.nameToNode:
            error( 'dst not in network: %s\n' % dst )
        else:
            if type( src ) is str:
                src = self.nameToNode[ src ]
            if type( dst ) is str:
                dst = self.nameToNode[ dst ]
            connections = src.connectionsTo( dst )
            if len( connections ) == 0:
                error( 'src and dst not connected: %s %s\n' % ( src, dst) )
            for srcIntf, dstIntf in connections:
                result = srcIntf.ifconfig( status )
                if result:
                    error( 'link src status change failed: %s\n' % result )
                result = dstIntf.ifconfig( status )
                if result:
                    error( 'link dst status change failed: %s\n' % result )

    def interact( self ):
        "Start network and run our simple CLI."
        self.start()
        result = CLI( self )
        self.stop()
        return result

    inited = False

    @classmethod
    def init( cls ):
        "Initialize Mininet"
        if cls.inited:
            return
        ensureRoot()
        fixLimits()
        cls.inited = True


class MininetWithControlNet( Mininet ):

    """Control network support:

       Create an explicit control network. Currently this is only
       used/usable with the user datapath.

       Notes:

       1. If the controller and switches are in the same (e.g. root)
          namespace, they can just use the loopback connection.

       2. If we can get unix domain sockets to work, we can use them
          instead of an explicit control network.

       3. Instead of routing, we could bridge or use 'in-band' control.

       4. Even if we dispense with this in general, it could still be
          useful for people who wish to simulate a separate control
          network (since real networks may need one!)

       5. Basically nobody ever used this code, so it has been moved
          into its own class.

       6. Ultimately we may wish to extend this to allow us to create a
          control network which every node's control interface is
          attached to."""

    def configureControlNetwork( self ):
        "Configure control network."
        self.configureRoutedControlNetwork()

    # We still need to figure out the right way to pass
    # in the control network location.

    def configureRoutedControlNetwork( self, ip='192.168.123.1',
                                       prefixLen=16 ):
        """Configure a routed control network on controller and switches.
           For use with the user datapath only right now."""
        controller = self.controllers[ 0 ]
        info( controller.name + ' <->' )
        cip = ip
        snum = ipParse( ip )
        for switch in self.switches:
            info( ' ' + switch.name )
            link = self.link( switch, controller, port1=0 )
            sintf, cintf = link.intf1, link.intf2
            switch.controlIntf = sintf
            snum += 1
            while snum & 0xff in [ 0, 255 ]:
                snum += 1
            sip = ipStr( snum )
            cintf.setIP( cip, prefixLen )
            sintf.setIP( sip, prefixLen )
            controller.setHostRoute( sip, cintf )
            switch.setHostRoute( cip, sintf )
        info( '\n' )
        info( '*** Testing control network\n' )
        while not cintf.isUp():
            info( '*** Waiting for', cintf, 'to come up\n' )
            sleep( 1 )
        for switch in self.switches:
            while not sintf.isUp():
                info( '*** Waiting for', sintf, 'to come up\n' )
                sleep( 1 )
            if self.ping( hosts=[ switch, controller ] ) != 0:
                error( '*** Error: control network test failed\n' )
                exit( 1 )
        info( '\n' )

########NEW FILE########
__FILENAME__ = node
"""
Node objects for Mininet.

Nodes provide a simple abstraction for interacting with hosts, switches
and controllers. Local nodes are simply one or more processes on the local
machine.

Node: superclass for all (primarily local) network nodes.

Host: a virtual host. By default, a host is simply a shell; commands
    may be sent using Cmd (which waits for output), or using sendCmd(),
    which returns immediately, allowing subsequent monitoring using
    monitor(). Examples of how to run experiments using this
    functionality are provided in the examples/ directory.

CPULimitedHost: a virtual host whose CPU bandwidth is limited by
    RT or CFS bandwidth limiting.

Switch: superclass for switch nodes.

UserSwitch: a switch using the user-space switch from the OpenFlow
    reference implementation.

KernelSwitch: a switch using the kernel switch from the OpenFlow reference
    implementation.

OVSSwitch: a switch using the OpenVSwitch OpenFlow-compatible switch
    implementation (openvswitch.org).

Controller: superclass for OpenFlow controllers. The default controller
    is controller(8) from the reference implementation.

NOXController: a controller node using NOX (noxrepo.org).

RemoteController: a remote controller node, which may use any
    arbitrary OpenFlow-compatible controller, and which is not
    created or managed by mininet.

Future enhancements:

- Possibly make Node, Switch and Controller more abstract so that
  they can be used for both local and remote nodes

- Create proxy objects for remote nodes (Mininet: Cluster Edition)
"""

import os
import re
import signal
import select
from subprocess import Popen, PIPE, STDOUT
from operator import or_
from time import sleep

from mininet.log import info, error, warn, debug
from mininet.util import ( quietRun, errRun, errFail, moveIntf, isShellBuiltin,
                           numCores, retry, mountCgroups )
from mininet.moduledeps import moduleDeps, pathCheck, OVS_KMOD, OF_KMOD, TUN
from mininet.link import Link, Intf, TCIntf

class Node( object ):
    """A virtual network node is simply a shell in a network namespace.
       We communicate with it using pipes."""

    portBase = 0  # Nodes always start with eth0/port0, even in OF 1.0

    def __init__( self, name, inNamespace=True, **params ):
        """name: name of node
           inNamespace: in network namespace?
           params: Node parameters (see config() for details)"""

        # Make sure class actually works
        self.checkSetup()

        self.name = name
        self.inNamespace = inNamespace

        # Stash configuration parameters for future reference
        self.params = params

        self.intfs = {}  # dict of port numbers to interfaces
        self.ports = {}  # dict of interfaces to port numbers
                         # replace with Port objects, eventually ?
        self.nameToIntf = {}  # dict of interface names to Intfs

        # Make pylint happy
        ( self.shell, self.execed, self.pid, self.stdin, self.stdout,
            self.lastPid, self.lastCmd, self.pollOut ) = (
                None, None, None, None, None, None, None, None )
        self.waiting = False
        self.readbuf = ''

        # Start command interpreter shell
        self.startShell()

    # File descriptor to node mapping support
    # Class variables and methods

    inToNode = {}  # mapping of input fds to nodes
    outToNode = {}  # mapping of output fds to nodes

    @classmethod
    def fdToNode( cls, fd ):
        """Return node corresponding to given file descriptor.
           fd: file descriptor
           returns: node"""
        node = cls.outToNode.get( fd )
        return node or cls.inToNode.get( fd )

    # Command support via shell process in namespace

    def startShell( self ):
        "Start a shell process for running commands"
        if self.shell:
            error( "%s: shell is already running" )
            return
        # mnexec: (c)lose descriptors, (d)etach from tty,
        # (p)rint pid, and run in (n)amespace
        opts = '-cdp'
        if self.inNamespace:
            opts += 'n'
        # bash -m: enable job control
        # -s: pass $* to shell, and make process easy to find in ps
        cmd = [ 'mnexec', opts, 'bash', '-ms', 'mininet:' + self.name ]
        self.shell = Popen( cmd, stdin=PIPE, stdout=PIPE, stderr=STDOUT,
                            close_fds=True )
        self.stdin = self.shell.stdin
        self.stdout = self.shell.stdout
        self.pid = self.shell.pid
        self.pollOut = select.poll()
        self.pollOut.register( self.stdout )
        # Maintain mapping between file descriptors and nodes
        # This is useful for monitoring multiple nodes
        # using select.poll()
        self.outToNode[ self.stdout.fileno() ] = self
        self.inToNode[ self.stdin.fileno() ] = self
        self.execed = False
        self.lastCmd = None
        self.lastPid = None
        self.readbuf = ''
        self.waiting = False

    def cleanup( self ):
        "Help python collect its garbage."
        # Intfs may end up in root NS
        for intfName in self.intfNames():
            if self.name in intfName:
                quietRun( 'ip link del ' + intfName )
        self.shell = None

    # Subshell I/O, commands and control

    def read( self, maxbytes=1024 ):
        """Buffered read from node, non-blocking.
           maxbytes: maximum number of bytes to return"""
        count = len( self.readbuf )
        if count < maxbytes:
            data = os.read( self.stdout.fileno(), maxbytes - count )
            self.readbuf += data
        if maxbytes >= len( self.readbuf ):
            result = self.readbuf
            self.readbuf = ''
        else:
            result = self.readbuf[ :maxbytes ]
            self.readbuf = self.readbuf[ maxbytes: ]
        return result

    def readline( self ):
        """Buffered readline from node, non-blocking.
           returns: line (minus newline) or None"""
        self.readbuf += self.read( 1024 )
        if '\n' not in self.readbuf:
            return None
        pos = self.readbuf.find( '\n' )
        line = self.readbuf[ 0: pos ]
        self.readbuf = self.readbuf[ pos + 1: ]
        return line

    def write( self, data ):
        """Write data to node.
           data: string"""
        os.write( self.stdin.fileno(), data )

    def terminate( self ):
        "Send kill signal to Node and clean up after it."
        if self.shell:
            os.killpg( self.pid, signal.SIGKILL )
        self.cleanup()

    def stop( self ):
        "Stop node."
        self.terminate()

    def waitReadable( self, timeoutms=None ):
        """Wait until node's output is readable.
           timeoutms: timeout in ms or None to wait indefinitely."""
        if len( self.readbuf ) == 0:
            self.pollOut.poll( timeoutms )

    def sendCmd( self, *args, **kwargs ):
        """Send a command, followed by a command to echo a sentinel,
           and return without waiting for the command to complete.
           args: command and arguments, or string
           printPid: print command's PID?"""
        assert not self.waiting
        printPid = kwargs.get( 'printPid', True )
        # Allow sendCmd( [ list ] )
        if len( args ) == 1 and type( args[ 0 ] ) is list:
            cmd = args[ 0 ]
        # Allow sendCmd( cmd, arg1, arg2... )
        elif len( args ) > 0:
            cmd = args
        # Convert to string
        if not isinstance( cmd, str ):
            cmd = ' '.join( [ str( c ) for c in cmd ] )
        if not re.search( r'\w', cmd ):
            # Replace empty commands with something harmless
            cmd = 'echo -n'
        self.lastCmd = cmd
        printPid = printPid and not isShellBuiltin( cmd )
        if len( cmd ) > 0 and cmd[ -1 ] == '&':
            # print ^A{pid}\n{sentinel}
            cmd += ' printf "\\001%d\n\\177" $! \n'
        else:
            # print sentinel
            cmd += '; printf "\\177"'
            if printPid and not isShellBuiltin( cmd ):
                cmd = 'mnexec -p ' + cmd
        self.write( cmd + '\n' )
        self.lastPid = None
        self.waiting = True

    def sendInt( self, sig=signal.SIGINT ):
        "Interrupt running command."
        if self.lastPid:
            try:
                os.kill( self.lastPid, sig )
            except OSError:
                pass

    def monitor( self, timeoutms=None ):
        """Monitor and return the output of a command.
           Set self.waiting to False if command has completed.
           timeoutms: timeout in ms or None to wait indefinitely."""
        self.waitReadable( timeoutms )
        data = self.read( 1024 )
        # Look for PID
        marker = chr( 1 ) + r'\d+\n'
        if chr( 1 ) in data:
            markers = re.findall( marker, data )
            if markers:
                self.lastPid = int( markers[ 0 ][ 1: ] )
                data = re.sub( marker, '', data )
        # Look for sentinel/EOF
        if len( data ) > 0 and data[ -1 ] == chr( 127 ):
            self.waiting = False
            data = data[ :-1 ]
        elif chr( 127 ) in data:
            self.waiting = False
            data = data.replace( chr( 127 ), '' )
        return data

    def waitOutput( self, verbose=False ):
        """Wait for a command to complete.
           Completion is signaled by a sentinel character, ASCII(127)
           appearing in the output stream.  Wait for the sentinel and return
           the output, including trailing newline.
           verbose: print output interactively"""
        log = info if verbose else debug
        output = ''
        while self.waiting:
            data = self.monitor()
            output += data
            log( data )
        return output

    def cmd( self, *args, **kwargs ):
        """Send a command, wait for output, and return it.
           cmd: string"""
        verbose = kwargs.get( 'verbose', False )
        log = info if verbose else debug
        log( '*** %s : %s\n' % ( self.name, args ) )
        self.sendCmd( *args, **kwargs )
        return self.waitOutput( verbose )

    def cmdPrint( self, *args):
        """Call cmd and printing its output
           cmd: string"""
        return self.cmd( *args, **{ 'verbose': True } )

    def popen( self, *args, **kwargs ):
        """Return a Popen() object in our namespace
           args: Popen() args, single list, or string
           kwargs: Popen() keyword args"""
        defaults = { 'stdout': PIPE, 'stderr': PIPE,
                     'mncmd':
                     [ 'mnexec', '-da', str( self.pid ) ] }
        defaults.update( kwargs )
        if len( args ) == 1:
            if type( args[ 0 ] ) is list:
                # popen([cmd, arg1, arg2...])
                cmd = args[ 0 ]
            elif type( args[ 0 ] ) is str:
                # popen("cmd arg1 arg2...")
                cmd = args[ 0 ].split()
            else:
                raise Exception( 'popen() requires a string or list' )
        elif len( args ) > 0:
            # popen( cmd, arg1, arg2... )
            cmd = list( args )
        # Attach to our namespace  using mnexec -a
        mncmd = defaults[ 'mncmd' ]
        del defaults[ 'mncmd' ]
        cmd = mncmd + cmd
        # Shell requires a string, not a list!
        if defaults.get( 'shell', False ):
            cmd = ' '.join( cmd )
        return Popen( cmd, **defaults )

    def pexec( self, *args, **kwargs ):
        """Execute a command using popen
           returns: out, err, exitcode"""
        popen = self.popen( *args, **kwargs)
        out, err = popen.communicate()
        exitcode = popen.wait()
        return out, err, exitcode

    # Interface management, configuration, and routing

    # BL notes: This might be a bit redundant or over-complicated.
    # However, it does allow a bit of specialization, including
    # changing the canonical interface names. It's also tricky since
    # the real interfaces are created as veth pairs, so we can't
    # make a single interface at a time.

    def newPort( self ):
        "Return the next port number to allocate."
        if len( self.ports ) > 0:
            return max( self.ports.values() ) + 1
        return self.portBase

    def addIntf( self, intf, port=None ):
        """Add an interface.
           intf: interface
           port: port number (optional, typically OpenFlow port number)"""
        if port is None:
            port = self.newPort()
        self.intfs[ port ] = intf
        self.ports[ intf ] = port
        self.nameToIntf[ intf.name ] = intf
        debug( '\n' )
        debug( 'added intf %s:%d to node %s\n' % ( intf, port, self.name ) )
        if self.inNamespace:
            debug( 'moving', intf, 'into namespace for', self.name, '\n' )
            moveIntf( intf.name, self )

    def defaultIntf( self ):
        "Return interface for lowest port"
        ports = self.intfs.keys()
        if ports:
            return self.intfs[ min( ports ) ]
        else:
            warn( '*** defaultIntf: warning:', self.name,
                  'has no interfaces\n' )

    def intf( self, intf='' ):
        """Return our interface object with given string name,
           default intf if name is falsy (None, empty string, etc).
           or the input intf arg.

        Having this fcn return its arg for Intf objects makes it
        easier to construct functions with flexible input args for
        interfaces (those that accept both string names and Intf objects).
        """
        if not intf:
            return self.defaultIntf()
        elif type( intf ) is str:
            return self.nameToIntf[ intf ]
        else:
            return intf

    def connectionsTo( self, node):
        "Return [ intf1, intf2... ] for all intfs that connect self to node."
        # We could optimize this if it is important
        connections = []
        for intf in self.intfList():
            link = intf.link
            if link:
                node1, node2 = link.intf1.node, link.intf2.node
                if node1 == self and node2 == node:
                    connections += [ ( intf, link.intf2 ) ]
                elif node1 == node and node2 == self:
                    connections += [ ( intf, link.intf1 ) ]
        return connections

    def deleteIntfs( self, checkName=True ):
        """Delete all of our interfaces.
           checkName: only delete interfaces that contain our name"""
        # In theory the interfaces should go away after we shut down.
        # However, this takes time, so we're better off removing them
        # explicitly so that we won't get errors if we run before they
        # have been removed by the kernel. Unfortunately this is very slow,
        # at least with Linux kernels before 2.6.33
        for intf in self.intfs.values():
            # Protect against deleting hardware interfaces
            if ( self.name in intf.name ) or ( not checkName ):
                intf.delete()
                info( '.' )

    # Routing support

    def setARP( self, ip, mac ):
        """Add an ARP entry.
           ip: IP address as string
           mac: MAC address as string"""
        result = self.cmd( 'arp', '-s', ip, mac )
        return result

    def setHostRoute( self, ip, intf ):
        """Add route to host.
           ip: IP address as dotted decimal
           intf: string, interface name"""
        return self.cmd( 'route add -host', ip, 'dev', intf )

    def setDefaultRoute( self, intf=None ):
        """Set the default route to go through intf.
           intf: Intf or {dev <intfname> via <gw-ip> ...}"""
        # Note setParam won't call us if intf is none
        if type( intf ) is str and ' ' in intf:
            params = intf
        else:
            params = 'dev %s' % intf
        self.cmd( 'ip route del default' )
        return self.cmd( 'ip route add default', params )

    # Convenience and configuration methods

    def setMAC( self, mac, intf=None ):
        """Set the MAC address for an interface.
           intf: intf or intf name
           mac: MAC address as string"""
        return self.intf( intf ).setMAC( mac )

    def setIP( self, ip, prefixLen=8, intf=None ):
        """Set the IP address for an interface.
           intf: intf or intf name
           ip: IP address as a string
           prefixLen: prefix length, e.g. 8 for /8 or 16M addrs"""
        # This should probably be rethought
        if '/' not in ip:
            ip = '%s/%s' % ( ip, prefixLen )
        return self.intf( intf ).setIP( ip )

    def IP( self, intf=None ):
        "Return IP address of a node or specific interface."
        return self.intf( intf ).IP()

    def MAC( self, intf=None ):
        "Return MAC address of a node or specific interface."
        return self.intf( intf ).MAC()

    def intfIsUp( self, intf=None ):
        "Check if an interface is up."
        return self.intf( intf ).isUp()

    # The reason why we configure things in this way is so
    # That the parameters can be listed and documented in
    # the config method.
    # Dealing with subclasses and superclasses is slightly
    # annoying, but at least the information is there!

    def setParam( self, results, method, **param ):
        """Internal method: configure a *single* parameter
           results: dict of results to update
           method: config method name
           param: arg=value (ignore if value=None)
           value may also be list or dict"""
        name, value = param.items()[ 0 ]
        f = getattr( self, method, None )
        if not f or value is None:
            return
        if type( value ) is list:
            result = f( *value )
        elif type( value ) is dict:
            result = f( **value )
        else:
            result = f( value )
        results[ name ] = result
        return result

    def config( self, mac=None, ip=None,
                defaultRoute=None, lo='up', **_params ):
        """Configure Node according to (optional) parameters:
           mac: MAC address for default interface
           ip: IP address for default interface
           ifconfig: arbitrary interface configuration
           Subclasses should override this method and call
           the parent class's config(**params)"""
        # If we were overriding this method, we would call
        # the superclass config method here as follows:
        # r = Parent.config( **_params )
        r = {}
        self.setParam( r, 'setMAC', mac=mac )
        self.setParam( r, 'setIP', ip=ip )
        self.setParam( r, 'setDefaultRoute', defaultRoute=defaultRoute )
        # This should be examined
        self.cmd( 'ifconfig lo ' + lo )
        return r

    def configDefault( self, **moreParams ):
        "Configure with default parameters"
        self.params.update( moreParams )
        self.config( **self.params )

    # This is here for backward compatibility
    def linkTo( self, node, link=Link ):
        """(Deprecated) Link to another node
           replace with Link( node1, node2)"""
        return link( self, node )

    # Other methods

    def intfList( self ):
        "List of our interfaces sorted by port number"
        return [ self.intfs[ p ] for p in sorted( self.intfs.iterkeys() ) ]

    def intfNames( self ):
        "The names of our interfaces sorted by port number"
        return [ str( i ) for i in self.intfList() ]

    def __repr__( self ):
        "More informative string representation"
        intfs = ( ','.join( [ '%s:%s' % ( i.name, i.IP() )
                              for i in self.intfList() ] ) )
        return '<%s %s: %s pid=%s> ' % (
            self.__class__.__name__, self.name, intfs, self.pid )

    def __str__( self ):
        "Abbreviated string representation"
        return self.name

    # Automatic class setup support

    isSetup = False

    @classmethod
    def checkSetup( cls ):
        "Make sure our class and superclasses are set up"
        while cls and not getattr( cls, 'isSetup', True ):
            cls.setup()
            cls.isSetup = True
            # Make pylint happy
            cls = getattr( type( cls ), '__base__', None )

    @classmethod
    def setup( cls ):
        "Make sure our class dependencies are available"
        pathCheck( 'mnexec', 'ifconfig', moduleName='Mininet')


class Host( Node ):
    "A host is simply a Node"
    pass


class CPULimitedHost( Host ):

    "CPU limited host"

    def __init__( self, name, sched='cfs', **kwargs ):
        Host.__init__( self, name, **kwargs )
        # Initialize class if necessary
        if not CPULimitedHost.inited:
            CPULimitedHost.init()
        # Create a cgroup and move shell into it
        self.cgroup = 'cpu,cpuacct,cpuset:/' + self.name
        errFail( 'cgcreate -g ' + self.cgroup )
        # We don't add ourselves to a cpuset because you must
        # specify the cpu and memory placement first
        errFail( 'cgclassify -g cpu,cpuacct:/%s %s' % ( self.name, self.pid ) )
        # BL: Setting the correct period/quota is tricky, particularly
        # for RT. RT allows very small quotas, but the overhead
        # seems to be high. CFS has a mininimum quota of 1 ms, but
        # still does better with larger period values.
        self.period_us = kwargs.get( 'period_us', 100000 )
        self.sched = sched
        self.rtprio = 20

    def cgroupSet( self, param, value, resource='cpu' ):
        "Set a cgroup parameter and return its value"
        cmd = 'cgset -r %s.%s=%s /%s' % (
            resource, param, value, self.name )
        quietRun( cmd )
        nvalue = int( self.cgroupGet( param, resource ) )
        if nvalue != value:
            error( '*** error: cgroupSet: %s set to %s instead of %s\n'
                   % ( param, nvalue, value ) )
        return nvalue

    def cgroupGet( self, param, resource='cpu' ):
        "Return value of cgroup parameter"
        cmd = 'cgget -r %s.%s /%s' % (
            resource, param, self.name )
        return int( quietRun( cmd ).split()[ -1 ] )

    def cgroupDel( self ):
        "Clean up our cgroup"
        # info( '*** deleting cgroup', self.cgroup, '\n' )
        _out, _err, exitcode = errRun( 'cgdelete -r ' + self.cgroup )
        return exitcode != 0

    def popen( self, *args, **kwargs ):
        """Return a Popen() object in node's namespace
           args: Popen() args, single list, or string
           kwargs: Popen() keyword args"""
        # Tell mnexec to execute command in our cgroup
        mncmd = [ 'mnexec', '-da', str( self.pid ),
                  '-g', self.name ]
        if self.sched == 'rt':
            mncmd += [ '-r', str( self.rtprio ) ]
        return Host.popen( self, *args, mncmd=mncmd, **kwargs )

    def cleanup( self ):
        "Clean up Node, then clean up our cgroup"
        super( CPULimitedHost, self ).cleanup()
        retry( retries=3, delaySecs=1, fn=self.cgroupDel )

    def chrt( self ):
        "Set RT scheduling priority"
        quietRun( 'chrt -p %s %s' % ( self.rtprio, self.pid ) )
        result = quietRun( 'chrt -p %s' % self.pid )
        firstline = result.split( '\n' )[ 0 ]
        lastword = firstline.split( ' ' )[ -1 ]
        if lastword != 'SCHED_RR':
            error( '*** error: could not assign SCHED_RR to %s\n' % self.name )
        return lastword

    def rtInfo( self, f ):
        "Internal method: return parameters for RT bandwidth"
        pstr, qstr = 'rt_period_us', 'rt_runtime_us'
        # RT uses wall clock time for period and quota
        quota = int( self.period_us * f * numCores() )
        return pstr, qstr, self.period_us, quota

    def cfsInfo( self, f):
        "Internal method: return parameters for CFS bandwidth"
        pstr, qstr = 'cfs_period_us', 'cfs_quota_us'
        # CFS uses wall clock time for period and CPU time for quota.
        quota = int( self.period_us * f * numCores() )
        period = self.period_us
        if f > 0 and quota < 1000:
            debug( '(cfsInfo: increasing default period) ' )
            quota = 1000
            period = int( quota / f / numCores() )
        return pstr, qstr, period, quota

    # BL comment:
    # This may not be the right API,
    # since it doesn't specify CPU bandwidth in "absolute"
    # units the way link bandwidth is specified.
    # We should use MIPS or SPECINT or something instead.
    # Alternatively, we should change from system fraction
    # to CPU seconds per second, essentially assuming that
    # all CPUs are the same.

    def setCPUFrac( self, f=-1, sched=None):
        """Set overall CPU fraction for this host
           f: CPU bandwidth limit (fraction)
           sched: 'rt' or 'cfs'
           Note 'cfs' requires CONFIG_CFS_BANDWIDTH"""
        if not f:
            return
        if not sched:
            sched = self.sched
        if sched == 'rt':
            pstr, qstr, period, quota = self.rtInfo( f )
        elif sched == 'cfs':
            pstr, qstr, period, quota = self.cfsInfo( f )
        else:
            return
        if quota < 0:
            # Reset to unlimited
            quota = -1
        # Set cgroup's period and quota
        self.cgroupSet( pstr, period )
        self.cgroupSet( qstr, quota )
        if sched == 'rt':
            # Set RT priority if necessary
            self.chrt()
        info( '(%s %d/%dus) ' % ( sched, quota, period ) )

    def setCPUs( self, cores, mems=0 ):
        "Specify (real) cores that our cgroup can run on"
        if type( cores ) is list:
            cores = ','.join( [ str( c ) for c in cores ] )
        self.cgroupSet( resource='cpuset', param='cpus',
                        value=cores )
        # Memory placement is probably not relevant, but we
        # must specify it anyway
        self.cgroupSet( resource='cpuset', param='mems',
                        value=mems)
        # We have to do this here after we've specified
        # cpus and mems
        errFail( 'cgclassify -g cpuset:/%s %s' % (
                 self.name, self.pid ) )

    def config( self, cpu=None, cores=None, **params ):
        """cpu: desired overall system CPU fraction
           cores: (real) core(s) this host can run on
           params: parameters for Node.config()"""
        r = Node.config( self, **params )
        # Was considering cpu={'cpu': cpu , 'sched': sched}, but
        # that seems redundant
        self.setParam( r, 'setCPUFrac', cpu=cpu )
        self.setParam( r, 'setCPUs', cores=cores )
        return r

    inited = False

    @classmethod
    def init( cls ):
        "Initialization for CPULimitedHost class"
        mountCgroups()
        cls.inited = True


# Some important things to note:
#
# The "IP" address which setIP() assigns to the switch is not
# an "IP address for the switch" in the sense of IP routing.
# Rather, it is the IP address for the control interface,
# on the control network, and it is only relevant to the
# controller. If you are running in the root namespace
# (which is the only way to run OVS at the moment), the
# control interface is the loopback interface, and you
# normally never want to change its IP address!
#
# In general, you NEVER want to attempt to use Linux's
# network stack (i.e. ifconfig) to "assign" an IP address or
# MAC address to a switch data port. Instead, you "assign"
# the IP and MAC addresses in the controller by specifying
# packets that you want to receive or send. The "MAC" address
# reported by ifconfig for a switch data port is essentially
# meaningless. It is important to understand this if you
# want to create a functional router using OpenFlow.

class Switch( Node ):
    """A Switch is a Node that is running (or has execed?)
       an OpenFlow switch."""

    portBase = 1  # Switches start with port 1 in OpenFlow
    dpidLen = 16  # digits in dpid passed to switch

    def __init__( self, name, dpid=None, opts='', listenPort=None, **params):
        """dpid: dpid hex string (or None to derive from name, e.g. s1 -> 1)
           opts: additional switch options
           listenPort: port to listen on for dpctl connections"""
        Node.__init__( self, name, **params )
        self.dpid = self.defaultDpid( dpid )
        self.opts = opts
        self.listenPort = listenPort
        if not self.inNamespace:
            self.controlIntf = Intf( 'lo', self, port=0 )

    def defaultDpid( self, dpid=None ):
        "Return correctly formatted dpid from dpid or switch name (s1 -> 1)"
        if dpid:
            # Remove any colons and make sure it's a good hex number
            dpid = dpid.translate( None, ':' )
            assert len( dpid ) <= self.dpidLen and int( dpid, 16 ) >= 0
        else:
            # Use hex of the first number in the switch name
            nums = re.findall( r'\d+', self.name )
            if nums:
                dpid = hex( int( nums[ 0 ] ) )[ 2: ]
            else:
                raise Exception( 'Unable to derive default datapath ID - '
                                 'please either specify a dpid or use a '
                                 'canonical switch name such as s23.' )
        return '0' * ( self.dpidLen - len( dpid ) ) + dpid

    def defaultIntf( self ):
        "Return control interface"
        if self.controlIntf:
            return self.controlIntf
        else:
            return Node.defaultIntf( self )

    def sendCmd( self, *cmd, **kwargs ):
        """Send command to Node.
           cmd: string"""
        kwargs.setdefault( 'printPid', False )
        if not self.execed:
            return Node.sendCmd( self, *cmd, **kwargs )
        else:
            error( '*** Error: %s has execed and cannot accept commands' %
                   self.name )

    def connected( self ):
        "Is the switch connected to a controller? (override this method)"
        return False and self  # satisfy pylint

    def __repr__( self ):
        "More informative string representation"
        intfs = ( ','.join( [ '%s:%s' % ( i.name, i.IP() )
                              for i in self.intfList() ] ) )
        return '<%s %s: %s pid=%s> ' % (
            self.__class__.__name__, self.name, intfs, self.pid )

class UserSwitch( Switch ):
    "User-space switch."

    dpidLen = 12

    def __init__( self, name, dpopts='--no-slicing', **kwargs ):
        """Init.
           name: name for the switch
           dpopts: additional arguments to ofdatapath (--no-slicing)"""
        Switch.__init__( self, name, **kwargs )
        pathCheck( 'ofdatapath', 'ofprotocol',
                   moduleName='the OpenFlow reference user switch' +
                              '(openflow.org)' )
        if self.listenPort:
            self.opts += ' --listen=ptcp:%i ' % self.listenPort
        self.dpopts = dpopts

    @classmethod
    def setup( cls ):
        "Ensure any dependencies are loaded; if not, try to load them."
        if not os.path.exists( '/dev/net/tun' ):
            moduleDeps( add=TUN )

    def dpctl( self, *args ):
        "Run dpctl command"
        listenAddr = None
        if not self.listenPort:
            listenAddr = 'unix:/tmp/' + self.name
        else:
            listenAddr = 'tcp:127.0.0.1:%i' % self.listenPort
        return self.cmd( 'dpctl ' + ' '.join( args ) +
                         ' ' + listenAddr )

    def connected( self ):
        "Is the switch connected to a controller?"
        return 'remote.is-connected=true' in self.dpctl( 'status' )

    @staticmethod
    def TCReapply( intf ):
        """Unfortunately user switch and Mininet are fighting
           over tc queuing disciplines. To resolve the conflict,
           we re-create the user switch's configuration, but as a
           leaf of the TCIntf-created configuration."""
        if type( intf ) is TCIntf:
            ifspeed = 10000000000 # 10 Gbps
            minspeed = ifspeed * 0.001

            res = intf.config( **intf.params )

            if res is None: # link may not have TC parameters
                return

            # Re-add qdisc, root, and default classes user switch created, but
            # with new parent, as setup by Mininet's TCIntf
            parent = res['parent']
            intf.tc( "%s qdisc add dev %s " + parent +
                     " handle 1: htb default 0xfffe" )
            intf.tc( "%s class add dev %s classid 1:0xffff parent 1: htb rate "
                     + str(ifspeed) )
            intf.tc( "%s class add dev %s classid 1:0xfffe parent 1:0xffff " +
                     "htb rate " + str(minspeed) + " ceil " + str(ifspeed) )

    def start( self, controllers ):
        """Start OpenFlow reference user datapath.
           Log to /tmp/sN-{ofd,ofp}.log.
           controllers: list of controller objects"""
        # Add controllers
        clist = ','.join( [ 'tcp:%s:%d' % ( c.IP(), c.port )
                            for c in controllers ] )
        ofdlog = '/tmp/' + self.name + '-ofd.log'
        ofplog = '/tmp/' + self.name + '-ofp.log'
        self.cmd( 'ifconfig lo up' )
        intfs = [ str( i ) for i in self.intfList() if not i.IP() ]
        self.cmd( 'ofdatapath -i ' + ','.join( intfs ) +
                  ' punix:/tmp/' + self.name + ' -d %s ' % self.dpid +
                  self.dpopts +
                  ' 1> ' + ofdlog + ' 2> ' + ofdlog + ' &' )
        self.cmd( 'ofprotocol unix:/tmp/' + self.name +
                  ' ' + clist +
                  ' --fail=closed ' + self.opts +
                  ' 1> ' + ofplog + ' 2>' + ofplog + ' &' )
        if "no-slicing" not in self.dpopts:
            # Only TCReapply if slicing is enable
            sleep(1) # Allow ofdatapath to start before re-arranging qdisc's
            for intf in self.intfList():
                if not intf.IP():
                    self.TCReapply( intf )

    def stop( self ):
        "Stop OpenFlow reference user datapath."
        self.cmd( 'kill %ofdatapath' )
        self.cmd( 'kill %ofprotocol' )
        self.deleteIntfs()


class OVSLegacyKernelSwitch( Switch ):
    """Open VSwitch legacy kernel-space switch using ovs-openflowd.
       Currently only works in the root namespace."""

    def __init__( self, name, dp=None, **kwargs ):
        """Init.
           name: name for switch
           dp: netlink id (0, 1, 2, ...)
           defaultMAC: default MAC as unsigned int; random value if None"""
        Switch.__init__( self, name, **kwargs )
        self.dp = dp if dp else self.name
        self.intf = self.dp
        if self.inNamespace:
            error( "OVSKernelSwitch currently only works"
                   " in the root namespace.\n" )
            exit( 1 )

    @classmethod
    def setup( cls ):
        "Ensure any dependencies are loaded; if not, try to load them."
        pathCheck( 'ovs-dpctl', 'ovs-openflowd',
                   moduleName='Open vSwitch (openvswitch.org)')
        moduleDeps( subtract=OF_KMOD, add=OVS_KMOD )

    def start( self, controllers ):
        "Start up kernel datapath."
        ofplog = '/tmp/' + self.name + '-ofp.log'
        quietRun( 'ifconfig lo up' )
        # Delete local datapath if it exists;
        # then create a new one monitoring the given interfaces
        self.cmd( 'ovs-dpctl del-dp ' + self.dp )
        self.cmd( 'ovs-dpctl add-dp ' + self.dp )
        intfs = [ str( i ) for i in self.intfList() if not i.IP() ]
        self.cmd( 'ovs-dpctl', 'add-if', self.dp, ' '.join( intfs ) )
        # Run protocol daemon
        clist = ','.join( [ 'tcp:%s:%d' % ( c.IP(), c.port )
                            for c in controllers ] )
        self.cmd( 'ovs-openflowd ' + self.dp +
                  ' ' + clist +
                  ' --fail=secure ' + self.opts +
                  ' --datapath-id=' + self.dpid +
                  ' 1>' + ofplog + ' 2>' + ofplog + '&' )
        self.execed = False

    def stop( self ):
        "Terminate kernel datapath."
        quietRun( 'ovs-dpctl del-dp ' + self.dp )
        self.cmd( 'kill %ovs-openflowd' )
        self.deleteIntfs()


class OVSSwitch( Switch ):
    "Open vSwitch switch. Depends on ovs-vsctl."

    def __init__( self, name, failMode='secure', datapath='kernel',
                 inband=False, **params ):
        """Init.
           name: name for switch
           failMode: controller loss behavior (secure|open)
           datapath: userspace or kernel mode (kernel|user)
           inband: use in-band control (False)"""
        Switch.__init__( self, name, **params )
        self.failMode = failMode
        self.datapath = datapath
        self.inband = inband

    @classmethod
    def setup( cls ):
        "Make sure Open vSwitch is installed and working"
        pathCheck( 'ovs-vsctl',
                   moduleName='Open vSwitch (openvswitch.org)')
        # This should no longer be needed, and it breaks
        # with OVS 1.7 which has renamed the kernel module:
        #  moduleDeps( subtract=OF_KMOD, add=OVS_KMOD )
        out, err, exitcode = errRun( 'ovs-vsctl -t 1 show' )
        if exitcode:
            error( out + err +
                   'ovs-vsctl exited with code %d\n' % exitcode +
                   '*** Error connecting to ovs-db with ovs-vsctl\n'
                   'Make sure that Open vSwitch is installed, '
                   'that ovsdb-server is running, and that\n'
                   '"ovs-vsctl show" works correctly.\n'
                   'You may wish to try '
                   '"service openvswitch-switch start".\n' )
            exit( 1 )

    @classmethod
    def batchShutdown( cls, switches ):
        "Call ovs-vsctl del-br on all OVSSwitches in a list"
        quietRun( 'ovs-vsctl ' +
                  ' -- '.join( '--if-exists del-br %s' % s
                               for s in switches ) )

    def dpctl( self, *args ):
        "Run ovs-ofctl command"
        return self.cmd( 'ovs-ofctl', args[ 0 ], self, *args[ 1: ] )

    @staticmethod
    def TCReapply( intf ):
        """Unfortunately OVS and Mininet are fighting
           over tc queuing disciplines. As a quick hack/
           workaround, we clear OVS's and reapply our own."""
        if type( intf ) is TCIntf:
            intf.config( **intf.params )

    def attach( self, intf ):
        "Connect a data port"
        self.cmd( 'ovs-vsctl add-port', self, intf )
        self.cmd( 'ifconfig', intf, 'up' )
        self.TCReapply( intf )

    def detach( self, intf ):
        "Disconnect a data port"
        self.cmd( 'ovs-vsctl del-port', self, intf )

    def controllerUUIDs( self ):
        "Return ovsdb UUIDs for our controllers"
        uuids = []
        controllers = self.cmd( 'ovs-vsctl -- get Bridge', self,
                               'Controller' ).strip()
        if controllers.startswith( '[' ) and controllers.endswith( ']' ):
            controllers = controllers[ 1 : -1 ]
            uuids = [ c.strip() for c in controllers.split( ',' ) ]
        return uuids

    def connected( self ):
        "Are we connected to at least one of our controllers?"
        results = [ 'true' in self.cmd( 'ovs-vsctl -- get Controller',
                                         uuid, 'is_connected' )
                    for uuid in self.controllerUUIDs() ]
        return reduce( or_, results, False )

    def start( self, controllers ):
        "Start up a new OVS OpenFlow switch using ovs-vsctl"
        if self.inNamespace:
            raise Exception(
                'OVS kernel switch does not work in a namespace' )
        # We should probably call config instead, but this
        # requires some rethinking...
        self.cmd( 'ifconfig lo up' )
        # Annoyingly, --if-exists option seems not to work
        self.cmd( 'ovs-vsctl del-br', self )
        int( self.dpid, 16 ) # DPID must be a hex string
        # Interfaces and controllers
        intfs = ' '.join( '-- add-port %s %s ' % ( self, intf )
                         for intf in self.intfList() if not intf.IP() )
        clist = ' '.join( '%s:%s:%d' % ( c.protocol, c.IP(), c.port )
                         for c in controllers )
        if self.listenPort:
            clist += ' ptcp:%s' % self.listenPort
        # Construct big ovs-vsctl command
        cmd = ( 'ovs-vsctl add-br %s ' % self +
                '-- set Bridge %s ' % self +
                'other_config:datapath-id=%s ' % self.dpid +
                '-- set-fail-mode %s %s ' % ( self, self.failMode ) +
                intfs +
                '-- set-controller %s %s ' % (self, clist ) )
        if not self.inband:
            cmd += ( '-- set bridge %s '
                     'other-config:disable-in-band=true ' % self )
        if self.datapath == 'user':
            cmd +=  '-- set bridge %s datapath_type=netdev ' % self
        # Reconnect quickly to controllers (1s vs. 15s max_backoff)
        for uuid in self.controllerUUIDs():
            if uuid.count( '-' ) != 4:
                # Doesn't look like a UUID
                continue
            uuid = uuid.strip()
            cmd += '-- set Controller %smax_backoff=1000 ' % uuid
        # Do it!!
        self.cmd( cmd )
        for intf in self.intfList():
            self.TCReapply( intf )


    def stop( self ):
        "Terminate OVS switch."
        self.cmd( 'ovs-vsctl del-br', self )
        if self.datapath == 'user':
            self.cmd( 'ip link del', self )
        self.deleteIntfs()

OVSKernelSwitch = OVSSwitch


class IVSSwitch(Switch):
    """IVS virtual switch"""

    def __init__( self, name, verbose=True, **kwargs ):
        Switch.__init__( self, name, **kwargs )
        self.verbose = verbose

    @classmethod
    def setup( cls ):
        "Make sure IVS is installed"
        pathCheck( 'ivs-ctl', 'ivs',
                   moduleName="Indigo Virtual Switch (projectfloodlight.org)" )
        out, err, exitcode = errRun( 'ivs-ctl show' )
        if exitcode:
            error( out + err +
                   'ivs-ctl exited with code %d\n' % exitcode +
                   '*** The openvswitch kernel module might '
                   'not be loaded. Try modprobe openvswitch.\n' )
            exit( 1 )

    @classmethod
    def batchShutdown( cls, switches ):
        "Kill each IVS switch, to be waited on later in stop()"
        for switch in switches:
            switch.cmd( 'kill %ivs' )

    def start( self, controllers ):
        "Start up a new IVS switch"
        args = ['ivs']
        args.extend( ['--name', self.name] )
        args.extend( ['--dpid', self.dpid] )
        if self.verbose:
            args.extend( ['--verbose'] )
        for intf in self.intfs.values():
            if not intf.IP():
                args.extend( ['-i', intf.name] )
        for c in controllers:
            args.extend( ['-c', '%s:%d' % (c.IP(), c.port)] )
        if self.listenPort:
            args.extend( ['--listen', '127.0.0.1:%i' % self.listenPort] )
        args.append( self.opts )

        logfile = '/tmp/ivs.%s.log' % self.name

        self.cmd( 'ifconfig lo up' )
        self.cmd( ' '.join(args) + ' >' + logfile + ' 2>&1 </dev/null &' )

    def stop( self ):
        "Terminate IVS switch."
        self.cmd( 'kill %ivs' )
        self.cmd( 'wait' )
        self.deleteIntfs()

    def attach( self, intf ):
        "Connect a data port"
        self.cmd( 'ivs-ctl', 'add-port', '--datapath', self.name, intf )

    def detach( self, intf ):
        "Disconnect a data port"
        self.cmd( 'ivs-ctl', 'del-port', '--datapath', self.name, intf )

    def dpctl( self, *args ):
        "Run dpctl command"
        if not self.listenPort:
            return "can't run dpctl without passive listening port"
        return self.cmd( 'ovs-ofctl ' + ' '.join( args ) +
                         ' tcp:127.0.0.1:%i' % self.listenPort )


class Controller( Node ):
    """A Controller is a Node that is running (or has execed?) an
       OpenFlow controller."""

    def __init__( self, name, inNamespace=False, command='controller',
                  cargs='-v ptcp:%d', cdir=None, ip="127.0.0.1",
                  port=6633, protocol='tcp', **params ):
        self.command = command
        self.cargs = cargs
        self.cdir = cdir
        self.ip = ip
        self.port = port
        self.protocol = protocol
        Node.__init__( self, name, inNamespace=inNamespace,
                       ip=ip, **params  )
        self.cmd( 'ifconfig lo up' )  # Shouldn't be necessary
        self.checkListening()

    def checkListening( self ):
        "Make sure no controllers are running on our port"
        # Verify that Telnet is installed first:
        out, _err, returnCode = errRun( "which telnet" )
        if 'telnet' not in out or returnCode != 0:
            raise Exception( "Error running telnet to check for listening "
                             "controllers; please check that it is "
                             "installed." )
        listening = self.cmd( "echo A | telnet -e A %s %d" %
                              ( self.ip, self.port ) )
        if 'Connected' in listening:
            servers = self.cmd( 'netstat -natp' ).split( '\n' )
            pstr = ':%d ' % self.port
            clist = servers[ 0:1 ] + [ s for s in servers if pstr in s ]
            raise Exception( "Please shut down the controller which is"
                             " running on port %d:\n" % self.port +
                             '\n'.join( clist ) )

    def start( self ):
        """Start <controller> <args> on controller.
           Log to /tmp/cN.log"""
        pathCheck( self.command )
        cout = '/tmp/' + self.name + '.log'
        if self.cdir is not None:
            self.cmd( 'cd ' + self.cdir )
        self.cmd( self.command + ' ' + self.cargs % self.port +
                  ' 1>' + cout + ' 2>' + cout + '&' )
        self.execed = False

    def stop( self ):
        "Stop controller."
        self.cmd( 'kill %' + self.command )
        self.terminate()

    def IP( self, intf=None ):
        "Return IP address of the Controller"
        if self.intfs:
            ip = Node.IP( self, intf )
        else:
            ip = self.ip
        return ip

    def __repr__( self ):
        "More informative string representation"
        return '<%s %s: %s:%s pid=%s> ' % (
            self.__class__.__name__, self.name,
            self.IP(), self.port, self.pid )


class OVSController( Controller ):
    "Open vSwitch controller"
    def __init__( self, name, command='ovs-controller', **kwargs ):
        Controller.__init__( self, name, command=command, **kwargs )


class NOX( Controller ):
    "Controller to run a NOX application."

    def __init__( self, name, *noxArgs, **kwargs ):
        """Init.
           name: name to give controller
           noxArgs: arguments (strings) to pass to NOX"""
        if not noxArgs:
            warn( 'warning: no NOX modules specified; '
                  'running packetdump only\n' )
            noxArgs = [ 'packetdump' ]
        elif type( noxArgs ) not in ( list, tuple ):
            noxArgs = [ noxArgs ]

        if 'NOX_CORE_DIR' not in os.environ:
            exit( 'exiting; please set missing NOX_CORE_DIR env var' )
        noxCoreDir = os.environ[ 'NOX_CORE_DIR' ]

        Controller.__init__( self, name,
                             command=noxCoreDir + '/nox_core',
                             cargs='--libdir=/usr/local/lib -v -i ptcp:%s ' +
                             ' '.join( noxArgs ),
                             cdir=noxCoreDir,
                             **kwargs )


class RemoteController( Controller ):
    "Controller running outside of Mininet's control."

    def __init__( self, name, ip='127.0.0.1',
                  port=6633, **kwargs):
        """Init.
           name: name to give controller
           ip: the IP address where the remote controller is
           listening
           port: the port where the remote controller is listening"""
        Controller.__init__( self, name, ip=ip, port=port, **kwargs )

    def start( self ):
        "Overridden to do nothing."
        return

    def stop( self ):
        "Overridden to do nothing."
        return

    def checkListening( self ):
        "Warn if remote controller is not accessible"
        listening = self.cmd( "echo A | telnet -e A %s %d" %
                              ( self.ip, self.port ) )
        if 'Connected' not in listening:
            warn( "Unable to contact the remote controller"
                  " at %s:%d\n" % ( self.ip, self.port ) )


########NEW FILE########
__FILENAME__ = term
"""
Terminal creation and cleanup.
Utility functions to run a terminal (connected via socat(1)) on each host.

Requires socat(1) and xterm(1).
Optionally uses gnome-terminal.
"""

from os import environ

from mininet.log import error
from mininet.util import quietRun, errRun

def tunnelX11( node, display=None):
    """Create an X11 tunnel from node:6000 to the root host
       display: display on root host (optional)
       returns: node $DISPLAY, Popen object for tunnel"""
    if display is None and 'DISPLAY' in environ:
        display = environ[ 'DISPLAY' ]
    if display is None:
        error( "Error: Cannot connect to display\n" )
        return None, None
    host, screen = display.split( ':' )
    # Unix sockets should work
    if not host or host == 'unix':
        # GDM3 doesn't put credentials in .Xauthority,
        # so allow root to just connect
        quietRun( 'xhost +si:localuser:root' )
        return display, None
    else:
        # Create a tunnel for the TCP connection
        port = 6000 + int( float( screen ) )
        connection = r'TCP\:%s\:%s' % ( host, port )
        cmd = [ "socat", "TCP-LISTEN:%d,fork,reuseaddr" % port,
               "EXEC:'mnexec -a 1 socat STDIO %s'" % connection ]
    return 'localhost:' + screen, node.popen( cmd )

def makeTerm( node, title='Node', term='xterm', display=None ):
    """Create an X11 tunnel to the node and start up a terminal.
       node: Node object
       title: base title
       term: 'xterm' or 'gterm'
       returns: two Popen objects, tunnel and terminal"""
    title += ': ' + node.name
    if not node.inNamespace:
        title += ' (root)'
    cmds = {
        'xterm': [ 'xterm', '-title', title, '-display' ],
        'gterm': [ 'gnome-terminal', '--title', title, '--display' ]
    }
    if term not in cmds:
        error( 'invalid terminal type: %s' % term )
        return
    display, tunnel = tunnelX11( node, display )
    if display is None:
        return []
    term = node.popen( cmds[ term ] + [ display, '-e', 'env TERM=ansi bash'] )
    return [ tunnel, term ] if tunnel else [ term ]

def runX11( node, cmd ):
    "Run an X11 client on a node"
    _display, tunnel = tunnelX11( node )
    if _display is None:
        return []
    popen = node.popen( cmd )
    return [ tunnel, popen ]

def cleanUpScreens():
    "Remove moldy socat X11 tunnels."
    errRun( "pkill -9 -f mnexec.*socat" )

def makeTerms( nodes, title='Node', term='xterm' ):
    """Create terminals.
       nodes: list of Node objects
       title: base title for each
       returns: list of created tunnel/terminal processes"""
    terms = []
    for node in nodes:
        terms += makeTerm( node, title, term )
    return terms

########NEW FILE########
__FILENAME__ = runner
#!/usr/bin/env python

"""
Run all mininet core tests
 -v : verbose output
 -quick : skip tests that take more than ~30 seconds
"""

import unittest
import os
import sys
from mininet.util import ensureRoot
from mininet.clean import cleanup
from mininet.log import setLogLevel

def runTests( testDir, verbosity=1 ):
    "discover and run all tests in testDir"
    # ensure root and cleanup before starting tests
    ensureRoot()
    cleanup()
    # discover all tests in testDir
    testSuite = unittest.defaultTestLoader.discover( testDir )
    # run tests
    unittest.TextTestRunner( verbosity=verbosity ).run( testSuite )

if __name__ == '__main__':
    setLogLevel( 'warning' )
    # get the directory containing example tests
    testDir = os.path.dirname( os.path.realpath( __file__ ) )
    verbosity = 2 if '-v' in sys.argv else 1
    runTests( testDir, verbosity )

########NEW FILE########
__FILENAME__ = test_hifi
#!/usr/bin/env python

"""Package: mininet
   Test creation and pings for topologies with link and/or CPU options."""

import unittest
from functools import partial

from mininet.net import Mininet
from mininet.node import OVSSwitch, UserSwitch, IVSSwitch
from mininet.node import CPULimitedHost
from mininet.link import TCLink
from mininet.topo import Topo
from mininet.log import setLogLevel
from mininet.util import quietRun

# Number of hosts for each test
N = 2


class SingleSwitchOptionsTopo(Topo):
    "Single switch connected to n hosts."
    def __init__(self, n=2, hopts=None, lopts=None):
        if not hopts:
            hopts = {}
        if not lopts:
            lopts = {}
        Topo.__init__(self, hopts=hopts, lopts=lopts)
        switch = self.addSwitch('s1')
        for h in range(n):
            host = self.addHost('h%s' % (h + 1))
            self.addLink(host, switch)

# Tell pylint not to complain about calls to other class
# pylint: disable=E1101

class testOptionsTopoCommon( object ):
    """Verify ability to create networks with host and link options
       (common code)."""

    switchClass = None # overridden in subclasses

    def runOptionsTopoTest( self, n, hopts=None, lopts=None ):
        "Generic topology-with-options test runner."
        mn = Mininet( topo=SingleSwitchOptionsTopo( n=n, hopts=hopts,
                                                    lopts=lopts ),
                      host=CPULimitedHost, link=TCLink,
                      switch=self.switchClass )
        dropped = mn.run( mn.ping )
        self.assertEqual( dropped, 0 )

    def assertWithinTolerance(self, measured, expected, tolerance_frac):
        """Check that a given value is within a tolerance of expected
        tolerance_frac: less-than-1.0 value; 0.8 would yield 20% tolerance.
        """
        self.assertGreaterEqual( float(measured),
                                 float(expected) * tolerance_frac )

    def testCPULimits( self ):
        "Verify topology creation with CPU limits set for both schedulers."
        CPU_FRACTION = 0.1
        CPU_TOLERANCE = 0.8  # CPU fraction below which test should fail
        hopts = { 'cpu': CPU_FRACTION }
        #self.runOptionsTopoTest( N, hopts=hopts )

        mn = Mininet( SingleSwitchOptionsTopo( n=N, hopts=hopts ),
                      host=CPULimitedHost, switch=self.switchClass )
        mn.start()
        results = mn.runCpuLimitTest( cpu=CPU_FRACTION )
        mn.stop()
        for cpu in results:
            self.assertWithinTolerance( cpu, CPU_FRACTION, CPU_TOLERANCE )

    def testLinkBandwidth( self ):
        "Verify that link bandwidths are accurate within a bound."
        BW = 5  # Mbps
        BW_TOLERANCE = 0.8  # BW fraction below which test should fail
        # Verify ability to create limited-link topo first;
        lopts = { 'bw': BW, 'use_htb': True }
        # Also verify correctness of limit limitng within a bound.
        mn = Mininet( SingleSwitchOptionsTopo( n=N, lopts=lopts ),
                      link=TCLink, switch=self.switchClass )
        bw_strs = mn.run( mn.iperf )
        for bw_str in bw_strs:
            bw = float( bw_str.split(' ')[0] )
            self.assertWithinTolerance( bw, BW, BW_TOLERANCE )

    def testLinkDelay( self ):
        "Verify that link delays are accurate within a bound."
        DELAY_MS = 15
        DELAY_TOLERANCE = 0.8  # Delay fraction below which test should fail
        lopts = { 'delay': '%sms' % DELAY_MS, 'use_htb': True }
        mn = Mininet( SingleSwitchOptionsTopo( n=N, lopts=lopts ),
                      link=TCLink, switch=self.switchClass )
        ping_delays = mn.run( mn.pingFull )
        test_outputs = ping_delays[0]
        # Ignore unused variables below
        # pylint: disable-msg=W0612
        node, dest, ping_outputs = test_outputs
        sent, received, rttmin, rttavg, rttmax, rttdev = ping_outputs
        self.assertEqual( sent, received )
        # pylint: enable-msg=W0612
        for rttval in [rttmin, rttavg, rttmax]:
            # Multiply delay by 4 to cover there & back on two links
            self.assertWithinTolerance( rttval, DELAY_MS * 4.0,
                                        DELAY_TOLERANCE)

    def testLinkLoss( self ):
        "Verify that we see packet drops with a high configured loss rate."
        LOSS_PERCENT = 99
        REPS = 1
        lopts = { 'loss': LOSS_PERCENT, 'use_htb': True }
        mn = Mininet( topo=SingleSwitchOptionsTopo( n=N, lopts=lopts ),
                      host=CPULimitedHost, link=TCLink,
                      switch=self.switchClass )
        # Drops are probabilistic, but the chance of no dropped packets is
        # 1 in 100 million with 4 hops for a link w/99% loss.
        dropped_total = 0
        mn.start()
        for _ in range(REPS):
            dropped_total += mn.ping(timeout='1')
        mn.stop()
        self.assertGreater( dropped_total, 0 )

    def testMostOptions( self ):
        "Verify topology creation with most link options and CPU limits."
        lopts = { 'bw': 10, 'delay': '5ms', 'use_htb': True }
        hopts = { 'cpu': 0.5 / N }
        self.runOptionsTopoTest( N, hopts=hopts, lopts=lopts )

# pylint: enable=E1101

class testOptionsTopoOVSKernel( testOptionsTopoCommon, unittest.TestCase ):
    """Verify ability to create networks with host and link options
       (OVS kernel switch)."""
    switchClass = OVSSwitch

@unittest.skip( 'Skipping OVS user switch test for now' )
class testOptionsTopoOVSUser( testOptionsTopoCommon, unittest.TestCase ):
    """Verify ability to create networks with host and link options
       (OVS user switch)."""
    switchClass = partial( OVSSwitch, datapath='user' )

@unittest.skipUnless( quietRun( 'which ivs-ctl' ), 'IVS is not installed' )
class testOptionsTopoIVS( testOptionsTopoCommon, unittest.TestCase ):
    "Verify ability to create networks with host and link options (IVS)."
    switchClass = IVSSwitch

@unittest.skipUnless( quietRun( 'which ofprotocol' ),
                     'Reference user switch is not installed' )
class testOptionsTopoUserspace( testOptionsTopoCommon, unittest.TestCase ):
    "Verify ability to create networks with host and link options (UserSwitch)."
    switchClass = UserSwitch

if __name__ == '__main__':
    setLogLevel( 'warning' )
    unittest.main()

########NEW FILE########
__FILENAME__ = test_nets
#!/usr/bin/env python

"""Package: mininet
   Test creation and all-pairs ping for each included mininet topo type."""

import unittest
from functools import partial

from mininet.net import Mininet
from mininet.node import Host, Controller
from mininet.node import UserSwitch, OVSSwitch, IVSSwitch
from mininet.topo import SingleSwitchTopo, LinearTopo
from mininet.log import setLogLevel
from mininet.util import quietRun

# Tell pylint not to complain about calls to other class
# pylint: disable=E1101

class testSingleSwitchCommon( object ):
    "Test ping with single switch topology (common code)."

    switchClass = None # overridden in subclasses

    def testMinimal( self ):
        "Ping test on minimal topology"
        mn = Mininet( SingleSwitchTopo(), self.switchClass, Host, Controller )
        dropped = mn.run( mn.ping )
        self.assertEqual( dropped, 0 )

    def testSingle5( self ):
        "Ping test on 5-host single-switch topology"
        mn = Mininet( SingleSwitchTopo( k=5 ), self.switchClass, Host,
                      Controller )
        dropped = mn.run( mn.ping )
        self.assertEqual( dropped, 0 )

# pylint: enable=E1101

class testSingleSwitchOVSKernel( testSingleSwitchCommon, unittest.TestCase ):
    "Test ping with single switch topology (OVS kernel switch)."
    switchClass = OVSSwitch

class testSingleSwitchOVSUser( testSingleSwitchCommon, unittest.TestCase ):
    "Test ping with single switch topology (OVS user switch)."
    switchClass = partial( OVSSwitch, datapath='user' )

@unittest.skipUnless( quietRun( 'which ivs-ctl' ), 'IVS is not installed' )
class testSingleSwitchIVS( testSingleSwitchCommon, unittest.TestCase ):
    "Test ping with single switch topology (IVS switch)."
    switchClass = IVSSwitch

@unittest.skipUnless( quietRun( 'which ofprotocol' ),
                     'Reference user switch is not installed' )
class testSingleSwitchUserspace( testSingleSwitchCommon, unittest.TestCase ):
    "Test ping with single switch topology (Userspace switch)."
    switchClass = UserSwitch


# Tell pylint not to complain about calls to other class
# pylint: disable=E1101

class testLinearCommon( object ):
    "Test all-pairs ping with LinearNet (common code)."

    switchClass = None # overridden in subclasses

    def testLinear5( self ):
        "Ping test on a 5-switch topology"
        mn = Mininet( LinearTopo( k=5 ), self.switchClass, Host, Controller )
        dropped = mn.run( mn.ping )
        self.assertEqual( dropped, 0 )

# pylint: enable=E1101


class testLinearOVSKernel( testLinearCommon, unittest.TestCase ):
    "Test all-pairs ping with LinearNet (OVS kernel switch)."
    switchClass = OVSSwitch

class testLinearOVSUser( testLinearCommon, unittest.TestCase ):
    "Test all-pairs ping with LinearNet (OVS user switch)."
    switchClass = partial( OVSSwitch, datapath='user' )

@unittest.skipUnless( quietRun( 'which ivs-ctl' ), 'IVS is not installed' )
class testLinearIVS( testLinearCommon, unittest.TestCase ):
    "Test all-pairs ping with LinearNet (IVS switch)."
    switchClass = IVSSwitch

@unittest.skipUnless( quietRun( 'which ofprotocol' ),
                      'Reference user switch is not installed' )
class testLinearUserspace( testLinearCommon, unittest.TestCase ):
    "Test all-pairs ping with LinearNet (Userspace switch)."
    switchClass = UserSwitch


if __name__ == '__main__':
    setLogLevel( 'warning' )
    unittest.main()

########NEW FILE########
__FILENAME__ = test_walkthrough
#!/usr/bin/env python

"""
Tests for the Mininet Walkthrough

TODO: missing xterm test
"""

import unittest
import pexpect
import os
from mininet.util import quietRun

class testWalkthrough( unittest.TestCase ):

    prompt = 'mininet>'

    # PART 1
    def testHelp( self ):
        "Check the usage message"
        p = pexpect.spawn( 'mn -h' )
        index = p.expect( [ 'Usage: mn', pexpect.EOF ] )
        self.assertEqual( index, 0 )

    def testWireshark( self ):
        "Use tshark to test the of dissector"
        tshark = pexpect.spawn( 'tshark -i lo -R of' )
        tshark.expect( 'Capturing on lo' )
        mn = pexpect.spawn( 'mn --test pingall' )
        mn.expect( '0% dropped' )
        tshark.expect( 'OFP 74 Hello' )
        tshark.sendintr()

    def testBasic( self ):
        "Test basic CLI commands (help, nodes, net, dump)"
        p = pexpect.spawn( 'mn' )
        p.expect( self.prompt )
        # help command
        p.sendline( 'help' )
        index = p.expect( [ 'commands', self.prompt ] )
        self.assertEqual( index, 0, 'No output for "help" command')
        # nodes command
        p.sendline( 'nodes' )
        p.expect( '([chs]\d ?){4}' )
        nodes = p.match.group( 0 ).split()
        self.assertEqual( len( nodes ), 4, 'No nodes in "nodes" command')
        p.expect( self.prompt )
        # net command
        p.sendline( 'net' )
        expected = [ x for x in nodes ]
        while len( expected ) > 0:
            index = p.expect( expected )
            node = p.match.group( 0 )
            expected.remove( node )
            p.expect( '\n' )
        self.assertEqual( len( expected ), 0, '"nodes" and "net" differ')
        p.expect( self.prompt )
        # dump command
        p.sendline( 'dump' )
        expected = [ '<\w+ (%s)' % n for n in nodes ]
        actual = []
        for _ in nodes:
            index = p.expect( expected )
            node = p.match.group( 1 )
            actual.append( node )
            p.expect( '\n' )
        self.assertEqual( actual.sort(), nodes.sort(), '"nodes" and "dump" differ' ) 
        p.expect( self.prompt )
        p.sendline( 'exit' )
        p.wait()

    def testHostCommands( self ):
        "Test ifconfig and ps on h1 and s1"
        p = pexpect.spawn( 'mn' )
        p.expect( self.prompt )
        interfaces = [ 'h1-eth0', 's1-eth1', '[^-]eth0', 'lo', self.prompt ]
        # h1 ifconfig
        p.sendline( 'h1 ifconfig -a' )
        ifcount = 0
        while True:
            index = p.expect( interfaces )
            if index == 0 or index == 3:
                ifcount += 1
            elif index == 1:
                self.fail( 's1 interface displayed in "h1 ifconfig"' )
            elif index == 2:
                self.fail( 'eth0 displayed in "h1 ifconfig"' )
            else:
                break
        self.assertEqual( ifcount, 2, 'Missing interfaces on h1')
        # s1 ifconfig
        p.sendline( 's1 ifconfig -a' )
        ifcount = 0
        while True:
            index = p.expect( interfaces )
            if index == 0:
                self.fail( 'h1 interface displayed in "s1 ifconfig"' )
            elif index == 1 or index == 2 or index == 3:
                ifcount += 1
            else:
                break
        self.assertEqual( ifcount, 3, 'Missing interfaces on s1')
        # h1 ps
        p.sendline( 'h1 ps -a' )
        p.expect( self.prompt )
        h1Output = p.before
        # s1 ps
        p.sendline( 's1 ps -a' )
        p.expect( self.prompt )
        s1Output = p.before
        # strip command from ps output
        h1Output = h1Output.split( '\n', 1 )[ 1 ]
        s1Output = s1Output.split( '\n', 1 )[ 1 ]
        self.assertEqual( h1Output, s1Output, 'h1 and s1 "ps" output differs')
        p.sendline( 'exit' )
        p.wait()

    def testConnectivity( self ):
        "Test ping and pingall"
        p = pexpect.spawn( 'mn' )
        p.expect( self.prompt )
        p.sendline( 'h1 ping -c 1 h2' )
        p.expect( '1 packets transmitted, 1 received' )
        p.expect( self.prompt )
        p.sendline( 'pingall' )
        p.expect( '0% dropped' )
        p.expect( self.prompt )
        p.sendline( 'exit' )
        p.wait()

    def testSimpleHTTP( self ):
        "Start an HTTP server on h1 and wget from h2"
        p = pexpect.spawn( 'mn' )
        p.expect( self.prompt )
        p.sendline( 'h1 python -m SimpleHTTPServer 80 &' )
        p.expect( self.prompt )
        p.sendline( ' h2 wget -O - h1' )
        p.expect( '200 OK' )
        p.expect( self.prompt )
        p.sendline( 'h1 kill %python' )
        p.expect( self.prompt )
        p.sendline( 'exit' )
        p.wait()

    # PART 2
    def testRegressionRun( self ):
        "Test pingpair (0% drop) and iperf (bw > 0) regression tests"
        # test pingpair
        p = pexpect.spawn( 'mn --test pingpair' )
        p.expect( '0% dropped' )
        p.expect( pexpect.EOF )
        # test iperf
        p = pexpect.spawn( 'mn --test iperf' )
        p.expect( "Results: \['([\d\.]+) .bits/sec'," )
        bw = float( p.match.group( 1 ) )
        self.assertTrue( bw > 0 )
        p.expect( pexpect.EOF )

    def testTopoChange( self ):
        "Test pingall on single,3 and linear,4 topos"
        # testing single,3
        p = pexpect.spawn( 'mn --test pingall --topo single,3' )
        p.expect( '(\d+)/(\d+) received')
        received = int( p.match.group( 1 ) )
        sent = int( p.match.group( 2 ) )
        self.assertEqual( sent, 6, 'Wrong number of pings sent in single,3' )
        self.assertEqual( sent, received, 'Dropped packets in single,3')
        p.expect( pexpect.EOF )
        # testing linear,4
        p = pexpect.spawn( 'mn --test pingall --topo linear,4' )
        p.expect( '(\d+)/(\d+) received')
        received = int( p.match.group( 1 ) )
        sent = int( p.match.group( 2 ) )
        self.assertEqual( sent, 12, 'Wrong number of pings sent in linear,4' )
        self.assertEqual( sent, received, 'Dropped packets in linear,4')
        p.expect( pexpect.EOF )

    def testLinkChange( self ):
        "Test TCLink bw and delay"
        p = pexpect.spawn( 'mn --link tc,bw=10,delay=10ms' )
        # test bw
        p.expect( self.prompt )
        p.sendline( 'iperf' )
        p.expect( "Results: \['([\d\.]+) Mbits/sec'," )
        bw = float( p.match.group( 1 ) )
        self.assertTrue( bw < 10.1, 'Bandwidth > 10 Mb/s')
        self.assertTrue( bw > 9.0, 'Bandwidth < 9 Mb/s')
        p.expect( self.prompt )
        # test delay
        p.sendline( 'h1 ping -c 4 h2' )
        p.expect( 'rtt min/avg/max/mdev = ([\d\.]+)/([\d\.]+)/([\d\.]+)/([\d\.]+) ms' )
        delay = float( p.match.group( 2 ) )
        self.assertTrue( delay > 40, 'Delay < 40ms' )
        self.assertTrue( delay < 45, 'Delay > 40ms' )
        p.expect( self.prompt )
        p.sendline( 'exit' )
        p.wait()

    def testVerbosity( self ):
        "Test debug and output verbosity"
        # test output
        p = pexpect.spawn( 'mn -v output' )
        p.expect( self.prompt )
        self.assertEqual( len( p.before ), 0, 'Too much output for "output"' )
        p.sendline( 'exit' )
        p.wait()
        # test debug
        p = pexpect.spawn( 'mn -v debug --test none' )
        p.expect( pexpect.EOF )
        lines = p.before.split( '\n' )
        self.assertTrue( len( lines ) > 100, "Debug output is too short" )

    def testCustomTopo( self ):
        "Start Mininet using a custom topo, then run pingall"
        custom = os.path.dirname( os.path.realpath( __file__ ) )
        custom = os.path.join( custom, '../../custom/topo-2sw-2host.py' )
        custom = os.path.normpath( custom )
        p = pexpect.spawn( 'mn --custom %s --topo mytopo --test pingall' % custom )
        p.expect( '0% dropped' )
        p.expect( pexpect.EOF )

    def testStaticMAC( self ):
        "Verify that MACs are set to easy to read numbers"
        p = pexpect.spawn( 'mn --mac' )
        p.expect( self.prompt )
        for i in range( 1, 3 ):
            p.sendline( 'h%d ifconfig' % i )
            p.expect( 'HWaddr 00:00:00:00:00:0%d' % i )
            p.expect( self.prompt )

    def testSwitches( self ):
        "Run iperf test using user and ovsk switches"
        switches = [ 'user', 'ovsk' ]
        for sw in switches:
            p = pexpect.spawn( 'mn --switch %s --test iperf' % sw )
            p.expect( "Results: \['([\d\.]+) .bits/sec'," )
            bw = float( p.match.group( 1 ) )
            self.assertTrue( bw > 0 )
            p.expect( pexpect.EOF )

    def testBenchmark( self ):
        "Run benchmark and verify that it takes less than 2 seconds"
        p = pexpect.spawn( 'mn --test none' )
        p.expect( 'completed in ([\d\.]+) seconds' )
        time = float( p.match.group( 1 ) )
        self.assertTrue( time < 2, 'Benchmark takes more than 2 seconds' )

    def testOwnNamespace( self ):
        "Test running user switch in its own namespace"
        p = pexpect.spawn( 'mn --innamespace --switch user' )
        p.expect( self.prompt )
        interfaces = [ 'h1-eth0', 's1-eth1', '[^-]eth0', 'lo', self.prompt ]
        p.sendline( 's1 ifconfig -a' )
        ifcount = 0
        while True:
            index = p.expect( interfaces )
            if index == 1 or index == 3:
                ifcount += 1
            elif index == 0:
                self.fail( 'h1 interface displayed in "s1 ifconfig"' )
            elif index == 2:
                self.fail( 'eth0 displayed in "s1 ifconfig"' )
            else:
                break
        self.assertEqual( ifcount, 2, 'Missing interfaces on s1' )
        # verify that all hosts a reachable
        p.sendline( 'pingall' )
        p.expect( '(\d+)% dropped' )
        dropped = int( p.match.group( 1 ) )
        self.assertEqual( dropped, 0, 'pingall failed')
        p.expect( self.prompt )
        p.sendline( 'exit' )
        p.wait()

    # PART 3
    def testPythonInterpreter( self ):
        "Test py and px by checking IP for h1 and adding h3"
        p = pexpect.spawn( 'mn' )
        p.expect( self.prompt )
        # test host IP
        p.sendline( 'py h1.IP()' )
        p.expect( '10.0.0.1' )
        p.expect( self.prompt )
        # test adding host
        p.sendline( "px net.addHost('h3')" )
        p.expect( self.prompt )
        p.sendline( "px net.addLink(s1, h3)" )
        p.expect( self.prompt )
        p.sendline( 'net' )
        p.expect( 'h3' )
        p.expect( self.prompt )
        p.sendline( 'py h3.MAC()' )
        p.expect( '([a-f0-9]{2}:?){6}' )
        p.expect( self.prompt )
        p.sendline( 'exit' )
        p.wait()

    def testLink( self ):
        "Test link CLI command using ping"
        p = pexpect.spawn( 'mn' )
        p.expect( self.prompt )
        p.sendline( 'link s1 h1 down' )
        p.expect( self.prompt )
        p.sendline( 'h1 ping -c 1 h2' )
        p.expect( 'unreachable' )
        p.expect( self.prompt )
        p.sendline( 'link s1 h1 up' )
        p.expect( self.prompt )
        p.sendline( 'h1 ping -c 1 h2' )
        p.expect( '0% packet loss' )
        p.expect( self.prompt )
        p.sendline( 'exit' )
        p.wait()

    @unittest.skipUnless( os.path.exists( '/tmp/pox' ) or
                          '1 received' in quietRun( 'ping -c 1 github.com' ),
                          'Github is not reachable; cannot download Pox' )
    def testRemoteController( self ):
        "Test Mininet using Pox controller"
        if not os.path.exists( '/tmp/pox' ):
            p = pexpect.spawn( 'git clone https://github.com/noxrepo/pox.git /tmp/pox' )
            p.expect( pexpect.EOF )
        pox = pexpect.spawn( '/tmp/pox/pox.py forwarding.l2_learning' )
        net = pexpect.spawn( 'mn --controller=remote,ip=127.0.0.1,port=6633 --test pingall' )
        net.expect( '0% dropped' )
        net.expect( pexpect.EOF )
        pox.sendintr()
        pox.wait()

if __name__ == '__main__':
    unittest.main()
########NEW FILE########
__FILENAME__ = topo
#!/usr/bin/env python
'''@package topo

Network topology creation.

@author Brandon Heller (brandonh@stanford.edu)

This package includes code to represent network topologies.

A Topo object can be a topology database for NOX, can represent a physical
setup for testing, and can even be emulated with the Mininet package.
'''

from mininet.util import irange, natural, naturalSeq

class MultiGraph( object ):
    "Utility class to track nodes and edges - replaces networkx.Graph"

    def __init__( self ):
        self.data = {}

    def add_node( self, node ):
        "Add node to graph"
        self.data.setdefault( node, [] )

    def add_edge( self, src, dest ):
        "Add edge to graph"
        src, dest = sorted( ( src, dest ) )
        self.add_node( src )
        self.add_node( dest )
        self.data[ src ].append( dest )

    def nodes( self ):
        "Return list of graph nodes"
        return self.data.keys()

    def edges( self ):
        "Iterator: return graph edges"
        for src in self.data.keys():
            for dest in self.data[ src ]:
                yield ( src, dest )

    def __getitem__( self, node ):
        "Return link dict for the given node"
        return self.data[node]


class Topo(object):
    "Data center network representation for structured multi-trees."

    def __init__(self, hopts=None, sopts=None, lopts=None):
        """Topo object:
           hinfo: default host options
           sopts: default switch options
           lopts: default link options"""
        self.g = MultiGraph()
        self.node_info = {}
        self.link_info = {}  # (src, dst) tuples hash to EdgeInfo objects
        self.hopts = {} if hopts is None else hopts
        self.sopts = {} if sopts is None else sopts
        self.lopts = {} if lopts is None else lopts
        self.ports = {}  # ports[src][dst] is port on src that connects to dst

    def addNode(self, name, **opts):
        """Add Node to graph.
           name: name
           opts: node options
           returns: node name"""
        self.g.add_node(name)
        self.node_info[name] = opts
        return name

    def addHost(self, name, **opts):
        """Convenience method: Add host to graph.
           name: host name
           opts: host options
           returns: host name"""
        if not opts and self.hopts:
            opts = self.hopts
        return self.addNode(name, **opts)

    def addSwitch(self, name, **opts):
        """Convenience method: Add switch to graph.
           name: switch name
           opts: switch options
           returns: switch name"""
        if not opts and self.sopts:
            opts = self.sopts
        result = self.addNode(name, isSwitch=True, **opts)
        return result

    def addLink(self, node1, node2, port1=None, port2=None,
                **opts):
        """node1, node2: nodes to link together
           port1, port2: ports (optional)
           opts: link options (optional)
           returns: link info key"""
        if not opts and self.lopts:
            opts = self.lopts
        self.addPort(node1, node2, port1, port2)
        key = tuple(self.sorted([node1, node2]))
        self.link_info[key] = opts
        self.g.add_edge(*key)
        return key

    def addPort(self, src, dst, sport=None, dport=None):
        '''Generate port mapping for new edge.
        @param src source switch name
        @param dst destination switch name
        '''
        self.ports.setdefault(src, {})
        self.ports.setdefault(dst, {})
        # New port: number of outlinks + base
        src_base = 1 if self.isSwitch(src) else 0
        dst_base = 1 if self.isSwitch(dst) else 0
        if sport is None:
            sport = len(self.ports[src]) + src_base
        if dport is None:
            dport = len(self.ports[dst]) + dst_base
        self.ports[src][dst] = sport
        self.ports[dst][src] = dport

    def nodes(self, sort=True):
        "Return nodes in graph"
        if sort:
            return self.sorted( self.g.nodes() )
        else:
            return self.g.nodes()

    def isSwitch(self, n):
        '''Returns true if node is a switch.'''
        info = self.node_info[n]
        return info and info.get('isSwitch', False)

    def switches(self, sort=True):
        '''Return switches.
        sort: sort switches alphabetically
        @return dpids list of dpids
        '''
        return [n for n in self.nodes(sort) if self.isSwitch(n)]

    def hosts(self, sort=True):
        '''Return hosts.
        sort: sort hosts alphabetically
        @return dpids list of dpids
        '''
        return [n for n in self.nodes(sort) if not self.isSwitch(n)]

    def links(self, sort=True):
        '''Return links.
        sort: sort links alphabetically
        @return links list of name pairs
        '''
        if not sort:
            return self.g.edges()
        else:
            links = [tuple(self.sorted(e)) for e in self.g.edges()]
            return sorted( links, key=naturalSeq )

    def port(self, src, dst):
        '''Get port number.

        @param src source switch name
        @param dst destination switch name
        @return tuple (src_port, dst_port):
            src_port: port on source switch leading to the destination switch
            dst_port: port on destination switch leading to the source switch
        '''
        if src in self.ports and dst in self.ports[src]:
            assert dst in self.ports and src in self.ports[dst]
            return self.ports[src][dst], self.ports[dst][src]

    def linkInfo( self, src, dst ):
        "Return link metadata"
        src, dst = self.sorted([src, dst])
        return self.link_info[(src, dst)]

    def setlinkInfo( self, src, dst, info ):
        "Set link metadata"
        src, dst = self.sorted([src, dst])
        self.link_info[(src, dst)] = info

    def nodeInfo( self, name ):
        "Return metadata (dict) for node"
        info = self.node_info[ name ]
        return info if info is not None else {}

    def setNodeInfo( self, name, info ):
        "Set metadata (dict) for node"
        self.node_info[ name ] = info

    @staticmethod
    def sorted( items ):
        "Items sorted in natural (i.e. alphabetical) order"
        return sorted(items, key=natural)

class SingleSwitchTopo(Topo):
    '''Single switch connected to k hosts.'''

    def __init__(self, k=2, **opts):
        '''Init.

        @param k number of hosts
        @param enable_all enables all nodes and switches?
        '''
        super(SingleSwitchTopo, self).__init__(**opts)

        self.k = k

        switch = self.addSwitch('s1')
        for h in irange(1, k):
            host = self.addHost('h%s' % h)
            self.addLink(host, switch)


class SingleSwitchReversedTopo(Topo):
    '''Single switch connected to k hosts, with reversed ports.

    The lowest-numbered host is connected to the highest-numbered port.

    Useful to verify that Mininet properly handles custom port numberings.
    '''
    def __init__(self, k=2, **opts):
        '''Init.

        @param k number of hosts
        @param enable_all enables all nodes and switches?
        '''
        super(SingleSwitchReversedTopo, self).__init__(**opts)
        self.k = k
        switch = self.addSwitch('s1')
        for h in irange(1, k):
            host = self.addHost('h%s' % h)
            self.addLink(host, switch,
                         port1=0, port2=(k - h + 1))

class LinearTopo(Topo):
    "Linear topology of k switches, with n hosts per switch."

    def __init__(self, k=2, n=1, **opts):
        """Init.
           k: number of switches
           n: number of hosts per switch
           hconf: host configuration options
           lconf: link configuration options"""

        super(LinearTopo, self).__init__(**opts)

        self.k = k
        self.n = n

        if n == 1:
            genHostName = lambda i, j: 'h%s' % i
        else:
            genHostName = lambda i, j: 'h%ss%d' % (j, i)


        lastSwitch = None
        for i in irange(1, k):
            # Add switch
            switch = self.addSwitch('s%s' % i)
            # Add hosts to switch
            for j in irange(1, n):
                host = self.addHost(genHostName(i, j))
                self.addLink(host, switch)
            # Connect switch to previous
            if lastSwitch:
                self.addLink(switch, lastSwitch)
            lastSwitch = switch

########NEW FILE########
__FILENAME__ = topolib
"Library of potentially useful topologies for Mininet"

from mininet.topo import Topo
from mininet.net import Mininet

class TreeTopo( Topo ):
    "Topology for a tree network with a given depth and fanout."

    def __init__( self, depth=1, fanout=2 ):
        super( TreeTopo, self ).__init__()
        # Numbering:  h1..N, s1..M
        self.hostNum = 1
        self.switchNum = 1
        # Build topology
        self.addTree( depth, fanout )

    def addTree( self, depth, fanout ):
        """Add a subtree starting with node n.
           returns: last node added"""
        isSwitch = depth > 0
        if isSwitch:
            node = self.addSwitch( 's%s' % self.switchNum )
            self.switchNum += 1
            for _ in range( fanout ):
                child = self.addTree( depth - 1, fanout )
                self.addLink( node, child )
        else:
            node = self.addHost( 'h%s' % self.hostNum )
            self.hostNum += 1
        return node


def TreeNet( depth=1, fanout=2, **kwargs ):
    "Convenience function for creating tree networks."
    topo = TreeTopo( depth, fanout )
    return Mininet( topo, **kwargs )

########NEW FILE########
__FILENAME__ = util
"Utility functions for Mininet."

from mininet.log import output, info, error, warn, debug

from time import sleep
from resource import getrlimit, setrlimit, RLIMIT_NPROC, RLIMIT_NOFILE
from select import poll, POLLIN, POLLHUP
from subprocess import call, check_call, Popen, PIPE, STDOUT
import re
from fcntl import fcntl, F_GETFL, F_SETFL
from os import O_NONBLOCK
import os

# Command execution support

def run( cmd ):
    """Simple interface to subprocess.call()
       cmd: list of command params"""
    return call( cmd.split( ' ' ) )

def checkRun( cmd ):
    """Simple interface to subprocess.check_call()
       cmd: list of command params"""
    return check_call( cmd.split( ' ' ) )

# pylint doesn't understand explicit type checking
# pylint: disable-msg=E1103

def oldQuietRun( *cmd ):
    """Run a command, routing stderr to stdout, and return the output.
       cmd: list of command params"""
    if len( cmd ) == 1:
        cmd = cmd[ 0 ]
        if isinstance( cmd, str ):
            cmd = cmd.split( ' ' )
    popen = Popen( cmd, stdout=PIPE, stderr=STDOUT )
    # We can't use Popen.communicate() because it uses
    # select(), which can't handle
    # high file descriptor numbers! poll() can, however.
    out = ''
    readable = poll()
    readable.register( popen.stdout )
    while True:
        while readable.poll():
            data = popen.stdout.read( 1024 )
            if len( data ) == 0:
                break
            out += data
        popen.poll()
        if popen.returncode is not None:
            break
    return out


# This is a bit complicated, but it enables us to
# monitor command output as it is happening

def errRun( *cmd, **kwargs ):
    """Run a command and return stdout, stderr and return code
       cmd: string or list of command and args
       stderr: STDOUT to merge stderr with stdout
       shell: run command using shell
       echo: monitor output to console"""
    # Allow passing in a list or a string
    if len( cmd ) == 1:
        cmd = cmd[ 0 ]
        if isinstance( cmd, str ):
            cmd = cmd.split( ' ' )
    cmd = [ str( arg ) for arg in cmd ]
    # By default we separate stderr, don't run in a shell, and don't echo
    stderr = kwargs.get( 'stderr', PIPE )
    shell = kwargs.get( 'shell', False )
    echo = kwargs.get( 'echo', False )
    if echo:
        # cmd goes to stderr, output goes to stdout
        info( cmd, '\n' )
    popen = Popen( cmd, stdout=PIPE, stderr=stderr, shell=shell )
    # We use poll() because select() doesn't work with large fd numbers,
    # and thus communicate() doesn't work either
    out, err = '', ''
    poller = poll()
    poller.register( popen.stdout, POLLIN )
    fdtofile = { popen.stdout.fileno(): popen.stdout }
    outDone, errDone = False, True
    if popen.stderr:
        fdtofile[ popen.stderr.fileno() ] = popen.stderr
        poller.register( popen.stderr, POLLIN )
        errDone = False
    while not outDone or not errDone:
        readable = poller.poll()
        for fd, _event in readable:
            f = fdtofile[ fd ]
            data = f.read( 1024 )
            if echo:
                output( data )
            if f == popen.stdout:
                out += data
                if data == '':
                    outDone = True
            elif f == popen.stderr:
                err += data
                if data == '':
                    errDone = True
    returncode = popen.wait()
    return out, err, returncode

def errFail( *cmd, **kwargs ):
    "Run a command using errRun and raise exception on nonzero exit"
    out, err, ret = errRun( *cmd, **kwargs )
    if ret:
        raise Exception( "errFail: %s failed with return code %s: %s"
                         % ( cmd, ret, err ) )
    return out, err, ret

def quietRun( cmd, **kwargs ):
    "Run a command and return merged stdout and stderr"
    return errRun( cmd, stderr=STDOUT, **kwargs )[ 0 ]

# pylint: enable-msg=E1103
# pylint: disable-msg=E1101

def isShellBuiltin( cmd ):
    "Return True if cmd is a bash builtin."
    if isShellBuiltin.builtIns is None:
        isShellBuiltin.builtIns = quietRun( 'bash -c enable' )
    space = cmd.find( ' ' )
    if space > 0:
        cmd = cmd[ :space]
    return cmd in isShellBuiltin.builtIns

isShellBuiltin.builtIns = None

# pylint: enable-msg=E1101

# Interface management
#
# Interfaces are managed as strings which are simply the
# interface names, of the form 'nodeN-ethM'.
#
# To connect nodes, we create a pair of veth interfaces, and then place them
# in the pair of nodes that we want to communicate. We then update the node's
# list of interfaces and connectivity map.
#
# For the kernel datapath, switch interfaces
# live in the root namespace and thus do not have to be
# explicitly moved.

def makeIntfPair( intf1, intf2 ):
    """Make a veth pair connecting intf1 and intf2.
       intf1: string, interface
       intf2: string, interface
       returns: success boolean"""
    # Delete any old interfaces with the same names
    quietRun( 'ip link del ' + intf1 )
    quietRun( 'ip link del ' + intf2 )
    # Create new pair
    cmd = 'ip link add name ' + intf1 + ' type veth peer name ' + intf2
    cmdOutput = quietRun( cmd )
    if cmdOutput == '':
        return True
    else:
        error( "Error creating interface pair: %s " % cmdOutput )
        return False

def retry( retries, delaySecs, fn, *args, **keywords ):
    """Try something several times before giving up.
       n: number of times to retry
       delaySecs: wait this long between tries
       fn: function to call
       args: args to apply to function call"""
    tries = 0
    while not fn( *args, **keywords ) and tries < retries:
        sleep( delaySecs )
        tries += 1
    if tries >= retries:
        error( "*** gave up after %i retries\n" % tries )
        exit( 1 )

def moveIntfNoRetry( intf, dstNode, srcNode=None, printError=False ):
    """Move interface to node, without retrying.
       intf: string, interface
        dstNode: destination Node
        srcNode: source Node or None (default) for root ns
        printError: if true, print error"""
    intf = str( intf )
    cmd = 'ip link set %s netns %s' % ( intf, dstNode.pid )
    if srcNode:
        srcNode.cmd( cmd )
    else:
        quietRun( cmd )
    if ( ' %s:' % intf ) not in dstNode.cmd( 'ip link show', intf ):
        if printError:
            error( '*** Error: moveIntf: ' + intf +
                   ' not successfully moved to ' + dstNode.name + '\n' )
        return False
    return True

def moveIntf( intf, dstNode, srcNode=None, printError=False,
             retries=3, delaySecs=0.001 ):
    """Move interface to node, retrying on failure.
       intf: string, interface
       dstNode: destination Node
       srcNode: source Node or None (default) for root ns
       printError: if true, print error"""
    retry( retries, delaySecs, moveIntfNoRetry, intf, dstNode,
          srcNode=srcNode, printError=printError )

# Support for dumping network

def dumpNodeConnections( nodes ):
    "Dump connections to/from nodes."

    def dumpConnections( node ):
        "Helper function: dump connections to node"
        for intf in node.intfList():
            output( ' %s:' % intf )
            if intf.link:
                intfs = [ intf.link.intf1, intf.link.intf2 ]
                intfs.remove( intf )
                output( intfs[ 0 ] )
            else:
                output( ' ' )

    for node in nodes:
        output( node.name )
        dumpConnections( node )
        output( '\n' )

def dumpNetConnections( net ):
    "Dump connections in network"
    nodes = net.controllers + net.switches + net.hosts
    dumpNodeConnections( nodes )

# IP and Mac address formatting and parsing

def _colonHex( val, bytecount ):
    """Generate colon-hex string.
       val: input as unsigned int
       bytecount: number of bytes to convert
       returns: chStr colon-hex string"""
    pieces = []
    for i in range( bytecount - 1, -1, -1 ):
        piece = ( ( 0xff << ( i * 8 ) ) & val ) >> ( i * 8 )
        pieces.append( '%02x' % piece )
    chStr = ':'.join( pieces )
    return chStr

def macColonHex( mac ):
    """Generate MAC colon-hex string from unsigned int.
       mac: MAC address as unsigned int
       returns: macStr MAC colon-hex string"""
    return _colonHex( mac, 6 )

def ipStr( ip ):
    """Generate IP address string from an unsigned int.
       ip: unsigned int of form w << 24 | x << 16 | y << 8 | z
       returns: ip address string w.x.y.z"""
    w = ( ip >> 24 ) & 0xff
    x = ( ip >> 16 ) & 0xff
    y = ( ip >> 8 ) & 0xff
    z = ip & 0xff
    return "%i.%i.%i.%i" % ( w, x, y, z )

def ipNum( w, x, y, z ):
    """Generate unsigned int from components of IP address
       returns: w << 24 | x << 16 | y << 8 | z"""
    return ( w << 24 ) | ( x << 16 ) | ( y << 8 ) | z

def ipAdd( i, prefixLen=8, ipBaseNum=0x0a000000 ):
    """Return IP address string from ints
       i: int to be added to ipbase
       prefixLen: optional IP prefix length
       ipBaseNum: option base IP address as int
       returns IP address as string"""
    imax = 0xffffffff >> prefixLen
    assert i <= imax
    mask = 0xffffffff ^ imax
    ipnum = ( ipBaseNum & mask ) + i
    return ipStr( ipnum )

def ipParse( ip ):
    "Parse an IP address and return an unsigned int."
    args = [ int( arg ) for arg in ip.split( '.' ) ]
    return ipNum( *args )

def netParse( ipstr ):
    """Parse an IP network specification, returning
       address and prefix len as unsigned ints"""
    prefixLen = 0
    if '/' in ipstr:
        ip, pf = ipstr.split( '/' )
        prefixLen = int( pf )
    return ipParse( ip ), prefixLen

def checkInt( s ):
    "Check if input string is an int"
    try:
        int( s )
        return True
    except ValueError:
        return False

def checkFloat( s ):
    "Check if input string is a float"
    try:
        float( s )
        return True
    except ValueError:
        return False

def makeNumeric( s ):
    "Convert string to int or float if numeric."
    if checkInt( s ):
        return int( s )
    elif checkFloat( s ):
        return float( s )
    else:
        return s

# Popen support

def pmonitor(popens, timeoutms=500, readline=True,
             readmax=1024 ):
    """Monitor dict of hosts to popen objects
       a line at a time
       timeoutms: timeout for poll()
       readline: return single line of output
       yields: host, line/output (if any)
       terminates: when all EOFs received"""
    poller = poll()
    fdToHost = {}
    for host, popen in popens.iteritems():
        fd = popen.stdout.fileno()
        fdToHost[ fd ] = host
        poller.register( fd, POLLIN )
        if not readline:
            # Use non-blocking reads
            flags = fcntl( fd, F_GETFL )
            fcntl( fd, F_SETFL, flags | O_NONBLOCK )
    while popens:
        fds = poller.poll( timeoutms )
        if fds:
            for fd, event in fds:
                host = fdToHost[ fd ]
                popen = popens[ host ]
                if event & POLLIN:
                    if readline:
                        # Attempt to read a line of output
                        # This blocks until we receive a newline!
                        line = popen.stdout.readline()
                    else:
                        line = popen.stdout.read( readmax )
                    yield host, line
                # Check for EOF
                elif event & POLLHUP:
                    poller.unregister( fd )
                    del popens[ host ]
        else:
            yield None, ''

# Other stuff we use
def sysctlTestAndSet( name, limit ):
    "Helper function to set sysctl limits"
    #convert non-directory names into directory names
    if '/' not in name:
        name = '/proc/sys/' + name.replace( '.', '/' )
    #read limit
    with open( name, 'r' ) as readFile:
        oldLimit = readFile.readline()
        if type( limit ) is int:
            #compare integer limits before overriding
            if int( oldLimit ) < limit:
                with open( name, 'w' ) as writeFile:
                    writeFile.write( "%d" % limit )
        else:
            #overwrite non-integer limits
            with open( name, 'w' ) as writeFile:
                writeFile.write( limit )

def rlimitTestAndSet( name, limit ):
    "Helper function to set rlimits"
    soft, hard = getrlimit( name )
    if soft < limit:
        hardLimit = hard if limit < hard else limit
        setrlimit( name, ( limit, hardLimit ) )

def fixLimits():
    "Fix ridiculously small resource limits."
    debug( "*** Setting resource limits\n" )
    try:
        rlimitTestAndSet( RLIMIT_NPROC, 8192 )
        rlimitTestAndSet( RLIMIT_NOFILE, 16384 )
        #Increase open file limit
        sysctlTestAndSet( 'fs.file-max', 10000 )
        #Increase network buffer space
        sysctlTestAndSet( 'net.core.wmem_max', 16777216 )
        sysctlTestAndSet( 'net.core.rmem_max', 16777216 )
        sysctlTestAndSet( 'net.ipv4.tcp_rmem', '10240 87380 16777216' )
        sysctlTestAndSet( 'net.ipv4.tcp_wmem', '10240 87380 16777216' )
        sysctlTestAndSet( 'net.core.netdev_max_backlog', 5000 )
        #Increase arp cache size
        sysctlTestAndSet( 'net.ipv4.neigh.default.gc_thresh1', 4096 )
        sysctlTestAndSet( 'net.ipv4.neigh.default.gc_thresh2', 8192 )
        sysctlTestAndSet( 'net.ipv4.neigh.default.gc_thresh3', 16384 )
        #Increase routing table size
        sysctlTestAndSet( 'net.ipv4.route.max_size', 32768 )
        #Increase number of PTYs for nodes
        sysctlTestAndSet( 'kernel.pty.max', 20000 )
    except:
        warn( "*** Error setting resource limits. "
              "Mininet's performance may be affected.\n" )

def mountCgroups():
    "Make sure cgroups file system is mounted"
    mounts = quietRun( 'cat /proc/mounts' )
    cgdir = '/sys/fs/cgroup'
    csdir = cgdir + '/cpuset'
    if ('cgroup %s' % cgdir not in mounts and
            'cgroups %s' % cgdir not in mounts):
        raise Exception( "cgroups not mounted on " + cgdir )
    if 'cpuset %s' % csdir not in mounts:
        errRun( 'mkdir -p ' + csdir )
        errRun( 'mount -t cgroup -ocpuset cpuset ' + csdir )

def natural( text ):
    "To sort sanely/alphabetically: sorted( l, key=natural )"
    def num( s ):
        "Convert text segment to int if necessary"
        return int( s ) if s.isdigit() else s
    return [  num( s ) for s in re.split( r'(\d+)', text ) ]

def naturalSeq( t ):
    "Natural sort key function for sequences"
    return [ natural( x ) for x in t ]

def numCores():
    "Returns number of CPU cores based on /proc/cpuinfo"
    if hasattr( numCores, 'ncores' ):
        return numCores.ncores
    try:
        numCores.ncores = int( quietRun('grep -c processor /proc/cpuinfo') )
    except ValueError:
        return 0
    return numCores.ncores

def irange(start, end):
    """Inclusive range from start to end (vs. Python insanity.)
       irange(1,5) -> 1, 2, 3, 4, 5"""
    return range( start, end + 1 )

def custom( cls, **params ):
    "Returns customized constructor for class cls."
    # Note: we may wish to see if we can use functools.partial() here
    # and in customConstructor
    def customized( *args, **kwargs):
        "Customized constructor"
        kwargs = kwargs.copy()
        kwargs.update( params )
        return cls( *args, **kwargs )
    customized.__name__ = 'custom(%s,%s)' % ( cls, params )
    return customized

def splitArgs( argstr ):
    """Split argument string into usable python arguments
       argstr: argument string with format fn,arg2,kw1=arg3...
       returns: fn, args, kwargs"""
    split = argstr.split( ',' )
    fn = split[ 0 ]
    params = split[ 1: ]
    # Convert int and float args; removes the need for function
    # to be flexible with input arg formats.
    args = [ makeNumeric( s ) for s in params if '=' not in s ]
    kwargs = {}
    for s in [ p for p in params if '=' in p ]:
        key, val = s.split( '=', 1 )
        kwargs[ key ] = makeNumeric( val )
    return fn, args, kwargs

def customConstructor( constructors, argStr ):
    """Return custom constructor based on argStr
    The args and key/val pairs in argsStr will be automatically applied
    when the generated constructor is later used.
    """
    cname, newargs, kwargs = splitArgs( argStr )
    constructor = constructors.get( cname, None )

    if not constructor:
        raise Exception( "error: %s is unknown - please specify one of %s" %
                         ( cname, constructors.keys() ) )

    def customized( name, *args, **params ):
        "Customized constructor, useful for Node, Link, and other classes"
        params = params.copy()
        params.update( kwargs )
        if not newargs:
            return constructor( name, *args, **params )
        if args:
            warn( 'warning: %s replacing %s with %s\n' % (
                  constructor, args, newargs ) )
        return constructor( name, *newargs, **params )

    customized.__name__ = 'customConstructor(%s)' % argStr
    return customized

def buildTopo( topos, topoStr ):
    """Create topology from string with format (object, arg1, arg2,...).
    input topos is a dict of topo names to constructors, possibly w/args.
    """
    topo, args, kwargs = splitArgs( topoStr )
    if topo not in topos:
        raise Exception( 'Invalid topo name %s' % topo )
    return topos[ topo ]( *args, **kwargs )

def ensureRoot():
    """Ensure that we are running as root.

    Probably we should only sudo when needed as per Big Switch's patch.
    """
    if os.getuid() != 0:
        print "*** Mininet must run as root."
        exit( 1 )
    return

########NEW FILE########
__FILENAME__ = doxify
#!/usr/bin/python

"""
Convert simple documentation to epydoc/pydoctor-compatible markup
"""

from sys import stdin, stdout, argv
import os
from tempfile import mkstemp
from subprocess import call

import re

spaces = re.compile( r'\s+' )
singleLineExp = re.compile( r'\s+"([^"]+)"' )
commentStartExp = re.compile( r'\s+"""' )
commentEndExp = re.compile( r'"""$' )
returnExp = re.compile( r'\s+(returns:.*)' )
lastindent = ''


comment = False

def fixParam( line ):
    "Change foo: bar to @foo bar"
    result = re.sub( r'(\w+):', r'@param \1', line )
    result = re.sub( r'   @', r'@', result)
    return result

def fixReturns( line ):
    "Change returns: foo to @return foo"
    return re.sub( 'returns:', r'@returns', line )
    
def fixLine( line ):
    global comment
    match = spaces.match( line )
    if not match:
        return line
    else:
        indent = match.group(0)
    if singleLineExp.match( line ):
        return re.sub( '"', '"""', line )
    if commentStartExp.match( line ):
        comment = True
    if comment:
        line = fixReturns( line )
        line = fixParam( line )
    if commentEndExp.search( line ):
        comment = False
    return line


def test():
    "Test transformations"
    assert fixLine(' "foo"') == ' """foo"""'
    assert fixParam( 'foo: bar' ) == '@param foo bar'
    assert commentStartExp.match( '   """foo"""')

def funTest():
    testFun = (
    'def foo():\n'
    '   "Single line comment"\n'
    '   """This is a test"""\n'
    '      bar: int\n'
    '      baz: string\n'
    '      returns: junk"""\n'
    '   if True:\n'
    '       print "OK"\n'
    ).splitlines( True )

    fixLines( testFun )
    
def fixLines( lines, fid ):
    for line in lines:
        os.write( fid, fixLine( line ) )

if __name__ == '__main__':
    if False:
        funTest()
    infile = open( argv[1] )
    outfid, outname = mkstemp()
    fixLines( infile.readlines(), outfid )
    infile.close()
    os.close( outfid )
    call( [ 'doxypy', outname ] )



    

########NEW FILE########
__FILENAME__ = versioncheck
#!/usr/bin/python

from subprocess import check_output as co
from sys import exit

# Actually run bin/mn rather than importing via python path
version = 'Mininet ' + co( 'PYTHONPATH=. bin/mn --version', shell=True )
version = version.strip()

# Find all Mininet path references
lines = co( "grep -or 'Mininet \w\+\.\w\+\.\w\+[+]*' *", shell=True )

error = False

for line in lines.split( '\n' ):
    if line and 'Binary' not in line:
        fname, fversion = line.split( ':' )
        if version != fversion:
            print "%s: incorrect version '%s' (should be '%s')" % (
                fname, fversion, version )
            error = True

if error:
    exit( 1 )

########NEW FILE########
__FILENAME__ = build
#!/usr/bin/python

"""
build.py: build a Mininet VM

Basic idea:

    prepare
    -> create base install image if it's missing
        - download iso if it's missing
        - install from iso onto image

    build
    -> create cow disk for new VM, based on base image
    -> boot it in qemu/kvm with text /serial console
    -> install Mininet

    test
    -> sudo mn --test pingall
    -> make test

    release
    -> shut down VM
    -> shrink-wrap VM
    -> upload to storage

"""

import os
from os import stat, path
from stat import ST_MODE, ST_SIZE
from os.path import abspath
from sys import exit, stdout, argv, modules
import re
from glob import glob
from subprocess import check_output, call, Popen
from tempfile import mkdtemp, NamedTemporaryFile
from time import time, strftime, localtime
import argparse
from distutils.spawn import find_executable
import inspect

pexpect = None  # For code check - imported dynamically

# boot can be slooooow!!!! need to debug/optimize somehow
TIMEOUT=600

# Some configuration options
# Possibly change this to use the parsed arguments instead!

LogToConsole = False        # VM output to console rather than log file
SaveQCOW2 = False           # Save QCOW2 image rather than deleting it
NoKVM = False               # Don't use kvm and use emulation instead
Branch = None               # Branch to update and check out before testing
Zip = False                  # Archive .ovf and .vmdk into a .zip file

VMImageDir = os.environ[ 'HOME' ] + '/vm-images'

Prompt = '\$ '              # Shell prompt that pexpect will wait for

isoURLs = {
    'precise32server':
    'http://mirrors.kernel.org/ubuntu-releases/12.04/'
    'ubuntu-12.04.3-server-i386.iso',
    'precise64server':
    'http://mirrors.kernel.org/ubuntu-releases/12.04/'
    'ubuntu-12.04.3-server-amd64.iso',
    'quantal32server':
    'http://mirrors.kernel.org/ubuntu-releases/12.10/'
    'ubuntu-12.10-server-i386.iso',
    'quantal64server':
    'http://mirrors.kernel.org/ubuntu-releases/12.10/'
    'ubuntu-12.10-server-amd64.iso',
    'raring32server':
    'http://mirrors.kernel.org/ubuntu-releases/13.04/'
    'ubuntu-13.04-server-i386.iso',
    'raring64server':
    'http://mirrors.kernel.org/ubuntu-releases/13.04/'
    'ubuntu-13.04-server-amd64.iso',
    'saucy32server':
    'http://mirrors.kernel.org/ubuntu-releases/13.10/'
    'ubuntu-13.10-server-i386.iso',
    'saucy64server':
    'http://mirrors.kernel.org/ubuntu-releases/13.10/'
    'ubuntu-13.10-server-amd64.iso',
    'trusty32server':
    'http://mirrors.kernel.org/ubuntu-releases/14.04/'
    'ubuntu-14.04-server-i386.iso',
    'trusty64server':
    'http://mirrors.kernel.org/ubuntu-releases/14.04/'
    'ubuntu-14.04-server-amd64.iso',
}


def OSVersion( flavor ):
    "Return full OS version string for build flavor"
    urlbase = path.basename( isoURLs.get( flavor, 'unknown' ) )
    return path.splitext( urlbase )[ 0 ]

def OVFOSNameID( flavor ):
    "Return OVF-specified ( OS Name, ID ) for flavor"
    version = OSVersion( flavor )
    arch = archFor( flavor )
    if 'ubuntu' in version:
        map = { 'i386': ( 'Ubuntu', 93 ),
                'x86_64': ( 'Ubuntu 64-bit', 94 ) }
    else:
        map = { 'i386': ( 'Linux', 36 ),
                'x86_64': ( 'Linux 64-bit', 101 ) }
    osname, osid = map[ arch ]
    return osname, osid

LogStartTime = time()
LogFile = None

def log( *args, **kwargs ):
    """Simple log function: log( message along with local and elapsed time
       cr: False/0 for no CR"""
    cr = kwargs.get( 'cr', True )
    elapsed = time() - LogStartTime
    clocktime = strftime( '%H:%M:%S', localtime() )
    msg = ' '.join( str( arg ) for arg in args )
    output = '%s [ %.3f ] %s' % ( clocktime, elapsed, msg )
    if cr:
        print output
    else:
        print output,
    # Optionally mirror to LogFile
    if type( LogFile ) is file:
        if cr:
            output += '\n'
        LogFile.write( output )
        LogFile.flush()


def run( cmd, **kwargs ):
    "Convenient interface to check_output"
    log( '-', cmd )
    cmd = cmd.split()
    arg0 = cmd[ 0 ]
    if not find_executable( arg0 ):
        raise Exception( 'Cannot find executable "%s";' % arg0 +
                         'you might try %s --depend' % argv[ 0 ] )
    return check_output( cmd, **kwargs )


def srun( cmd, **kwargs ):
    "Run + sudo"
    return run( 'sudo ' + cmd, **kwargs )


# BL: we should probably have a "checkDepend()" which
# checks to make sure all dependencies are satisfied!

def depend():
    "Install package dependencies"
    log( '* Installing package dependencies' )
    run( 'sudo apt-get -y update' )
    run( 'sudo apt-get install -y'
         ' kvm cloud-utils genisoimage qemu-kvm qemu-utils'
         ' e2fsprogs dnsmasq'
         ' python-setuptools mtools zip' )
    run( 'sudo easy_install pexpect' )


def popen( cmd ):
    "Convenient interface to popen"
    log( cmd )
    cmd = cmd.split()
    return Popen( cmd )


def remove( fname ):
    "Remove a file, ignoring errors"
    try:
        os.remove( fname )
    except OSError:
        pass


def findiso( flavor ):
    "Find iso, fetching it if it's not there already"
    url = isoURLs[ flavor ]
    name = path.basename( url )
    iso = path.join( VMImageDir, name )
    if not path.exists( iso ) or ( stat( iso )[ ST_MODE ] & 0777 != 0444 ):
        log( '* Retrieving', url )
        run( 'curl -C - -o %s %s' % ( iso, url ) )
        if 'ISO' not in run( 'file ' + iso ):
            os.remove( iso )
            raise Exception( 'findiso: could not download iso from ' + url )
        # Write-protect iso, signaling it is complete
        log( '* Write-protecting iso', iso)
        os.chmod( iso, 0444 )
    log( '* Using iso', iso )
    return iso


def attachNBD( cow, flags='' ):
    """Attempt to attach a COW disk image and return its nbd device
        flags: additional flags for qemu-nbd (e.g. -r for readonly)"""
    # qemu-nbd requires an absolute path
    cow = abspath( cow )
    log( '* Checking for unused /dev/nbdX device ' )
    for i in range ( 0, 63 ):
        nbd = '/dev/nbd%d' % i
        # Check whether someone's already messing with that device
        if call( [ 'pgrep', '-f', nbd ] ) == 0:
            continue
        srun( 'modprobe nbd max-part=64' )
        srun( 'qemu-nbd %s -c %s %s' % ( flags, nbd, cow ) )
        print
        return nbd
    raise Exception( "Error: could not find unused /dev/nbdX device" )


def detachNBD( nbd ):
    "Detatch an nbd device"
    srun( 'qemu-nbd -d ' + nbd )


def extractKernel( image, flavor, imageDir=VMImageDir ):
    "Extract kernel and initrd from base image"
    kernel = path.join( imageDir, flavor + '-vmlinuz' )
    initrd = path.join( imageDir, flavor + '-initrd' )
    if path.exists( kernel ) and ( stat( image )[ ST_MODE ] & 0777 ) == 0444:
        # If kernel is there, then initrd should also be there
        return kernel, initrd
    log( '* Extracting kernel to', kernel )
    nbd = attachNBD( image, flags='-r' )
    print srun( 'partx ' + nbd )
    # Assume kernel is in partition 1/boot/vmlinuz*generic for now
    part = nbd + 'p1'
    mnt = mkdtemp()
    srun( 'mount -o ro %s %s' % ( part, mnt  ) )
    kernsrc = glob( '%s/boot/vmlinuz*generic' % mnt )[ 0 ]
    initrdsrc = glob( '%s/boot/initrd*generic' % mnt )[ 0 ]
    srun( 'cp %s %s' % ( initrdsrc, initrd ) )
    srun( 'chmod 0444 ' + initrd )
    srun( 'cp %s %s' % ( kernsrc, kernel ) )
    srun( 'chmod 0444 ' + kernel )
    srun( 'umount ' + mnt )
    run( 'rmdir ' + mnt )
    detachNBD( nbd )
    return kernel, initrd


def findBaseImage( flavor, size='8G' ):
    "Return base VM image and kernel, creating them if needed"
    image = path.join( VMImageDir, flavor + '-base.qcow2' )
    if path.exists( image ):
        # Detect race condition with multiple builds
        perms = stat( image )[ ST_MODE ] & 0777
        if perms != 0444:
            raise Exception( 'Error - %s is writable ' % image +
                            '; are multiple builds running?' )
    else:
        # We create VMImageDir here since we are called first
        run( 'mkdir -p %s' % VMImageDir )
        iso = findiso( flavor )
        log( '* Creating image file', image )
        run( 'qemu-img create -f qcow2 %s %s' % ( image, size ) )
        installUbuntu( iso, image )
        # Write-protect image, also signaling it is complete
        log( '* Write-protecting image', image)
        os.chmod( image, 0444 )
    kernel, initrd = extractKernel( image, flavor )
    log( '* Using base image', image, 'and kernel', kernel )
    return image, kernel, initrd


# Kickstart and Preseed files for Ubuntu/Debian installer
#
# Comments: this is really clunky and painful. If Ubuntu
# gets their act together and supports kickstart a bit better
# then we can get rid of preseed and even use this as a
# Fedora installer as well.
#
# Another annoying thing about Ubuntu is that it can't just
# install a normal system from the iso - it has to download
# junk from the internet, making this house of cards even
# more precarious.

KickstartText ="""
#Generated by Kickstart Configurator
#platform=x86

#System language
lang en_US
#Language modules to install
langsupport en_US
#System keyboard
keyboard us
#System mouse
mouse
#System timezone
timezone America/Los_Angeles
#Root password
rootpw --disabled
#Initial user
user mininet --fullname "mininet" --password "mininet"
#Use text mode install
text
#Install OS instead of upgrade
install
#Use CDROM installation media
cdrom
#System bootloader configuration
bootloader --location=mbr
#Clear the Master Boot Record
zerombr yes
#Partition clearing information
clearpart --all --initlabel
#Automatic partitioning
autopart
#System authorization infomation
auth  --useshadow  --enablemd5
#Firewall configuration
firewall --disabled
#Do not configure the X Window System
skipx
"""

# Tell the Ubuntu/Debian installer to stop asking stupid questions

PreseedText = """
d-i mirror/country string manual
d-i mirror/http/hostname string mirrors.kernel.org
d-i mirror/http/directory string /ubuntu
d-i mirror/http/proxy string
d-i partman/confirm_write_new_label boolean true
d-i partman/choose_partition select finish
d-i partman/confirm boolean true
d-i partman/confirm_nooverwrite boolean true
d-i user-setup/allow-password-weak boolean true
d-i finish-install/reboot_in_progress note
d-i debian-installer/exit/poweroff boolean true
"""

def makeKickstartFloppy():
    "Create and return kickstart floppy, kickstart, preseed"
    kickstart = 'ks.cfg'
    with open( kickstart, 'w' ) as f:
        f.write( KickstartText )
    preseed = 'ks.preseed'
    with open( preseed, 'w' ) as f:
        f.write( PreseedText )
    # Create floppy and copy files to it
    floppy = 'ksfloppy.img'
    run( 'qemu-img create %s 1440k' % floppy )
    run( 'mkfs -t msdos ' + floppy )
    run( 'mcopy -i %s %s ::/' % ( floppy, kickstart ) )
    run( 'mcopy -i %s %s ::/' % ( floppy, preseed ) )
    return floppy, kickstart, preseed


def archFor( filepath ):
    "Guess architecture for file path"
    name = path.basename( filepath )
    if 'amd64' in name or 'x86_64' in name:
        arch = 'x86_64'
    # Beware of version 64 of a 32-bit OS
    elif 'i386' in name or '32' in name or 'x86' in name:
        arch = 'i386'
    elif '64' in name:
        arch = 'x86_64'
    else:
        log( "Error: can't discern CPU for name", name )
        exit( 1 )
    return arch


def installUbuntu( iso, image, logfilename='install.log', memory=1024 ):
    "Install Ubuntu from iso onto image"
    kvm = 'qemu-system-' + archFor( iso )
    floppy, kickstart, preseed = makeKickstartFloppy()
    # Mount iso so we can use its kernel
    mnt = mkdtemp()
    srun( 'mount %s %s' % ( iso, mnt ) )
    kernel = path.join( mnt, 'install/vmlinuz' )
    initrd = path.join( mnt, 'install/initrd.gz' )
    if NoKVM:
        accel = 'tcg'
    else:
        accel = 'kvm'
    cmd = [ 'sudo', kvm,
           '-machine', 'accel=%s' % accel,
           '-nographic',
           '-netdev', 'user,id=mnbuild',
           '-device', 'virtio-net,netdev=mnbuild',
           '-m', str( memory ),
           '-k', 'en-us',
           '-fda', floppy,
           '-drive', 'file=%s,if=virtio' % image,
           '-cdrom', iso,
           '-kernel', kernel,
           '-initrd', initrd,
           '-append',
           ' ks=floppy:/' + kickstart +
           ' preseed/file=floppy://' + preseed +
           ' console=ttyS0' ]
    ubuntuStart = time()
    log( '* INSTALLING UBUNTU FROM', iso, 'ONTO', image )
    log( ' '.join( cmd ) )
    log( '* logging to', abspath( logfilename ) )
    params = {}
    if not LogToConsole:
        logfile = open( logfilename, 'w' )
        params = { 'stdout': logfile, 'stderr': logfile }
    vm = Popen( cmd, **params )
    log( '* Waiting for installation to complete')
    vm.wait()
    if not LogToConsole:
        logfile.close()
    elapsed = time() - ubuntuStart
    # Unmount iso and clean up
    srun( 'umount ' + mnt )
    run( 'rmdir ' + mnt )
    if vm.returncode != 0:
        raise Exception( 'Ubuntu installation returned error %d' %
                          vm.returncode )
    log( '* UBUNTU INSTALLATION COMPLETED FOR', image )
    log( '* Ubuntu installation completed in %.2f seconds' % elapsed )


def boot( cow, kernel, initrd, logfile, memory=1024 ):
    """Boot qemu/kvm with a COW disk and local/user data store
       cow: COW disk path
       kernel: kernel path
       logfile: log file for pexpect object
       memory: memory size in MB
       returns: pexpect object to qemu process"""
    # pexpect might not be installed until after depend() is called
    global pexpect
    import pexpect
    arch = archFor( kernel )
    log( '* Detected kernel architecture', arch )
    if NoKVM:
        accel = 'tcg'
    else:
        accel = 'kvm'
    cmd = [ 'sudo', 'qemu-system-' + arch,
            '-machine accel=%s' % accel,
            '-nographic',
            '-netdev user,id=mnbuild',
            '-device virtio-net,netdev=mnbuild',
            '-m %s' % memory,
            '-k en-us',
            '-kernel', kernel,
            '-initrd', initrd,
            '-drive file=%s,if=virtio' % cow,
            '-append "root=/dev/vda1 init=/sbin/init console=ttyS0" ' ]
    cmd = ' '.join( cmd )
    log( '* BOOTING VM FROM', cow )
    log( cmd )
    vm = pexpect.spawn( cmd, timeout=TIMEOUT, logfile=logfile )
    return vm


def login( vm ):
    "Log in to vm (pexpect object)"
    log( '* Waiting for login prompt' )
    vm.expect( 'login: ' )
    log( '* Logging in' )
    vm.sendline( 'mininet' )
    log( '* Waiting for password prompt' )
    vm.expect( 'Password: ' )
    log( '* Sending password' )
    vm.sendline( 'mininet' )
    log( '* Waiting for login...' )


def sanityTest( vm ):
    "Run Mininet sanity test (pingall) in vm"
    vm.sendline( 'sudo mn --test pingall' )
    if vm.expect( [ ' 0% dropped', pexpect.TIMEOUT ], timeout=45 ) == 0:
        log( '* Sanity check OK' )
    else:
        log( '* Sanity check FAILED' )
        log( '* Sanity check output:' )
        log( vm.before )


def coreTest( vm, prompt=Prompt ):
    "Run core tests (make test) in VM"
    log( '* Making sure cgroups are mounted' )
    vm.sendline( 'sudo service cgroup-lite restart' )
    vm.expect( prompt )
    vm.sendline( 'sudo cgroups-mount' )
    vm.expect( prompt )
    log( '* Running make test' )
    vm.sendline( 'cd ~/mininet; sudo make test' )
    # We should change "make test" to report the number of
    # successful and failed tests. For now, we have to
    # know the time for each test, which means that this
    # script will have to change as we add more tests.
    for test in range( 0, 2 ):
        if vm.expect( [ 'OK', 'FAILED', pexpect.TIMEOUT ], timeout=180 ) == 0:
            log( '* Test', test, 'OK' )
        else:
            log( '* Test', test, 'FAILED' )
            log( '* Test', test, 'output:' )
            log( vm.before )

def noneTest( vm ):
    "This test does nothing"
    vm.sendline( 'echo' )

def examplesquickTest( vm, prompt=Prompt ):
    "Quick test of mininet examples"
    vm.sendline( 'sudo apt-get install python-pexpect' )
    vm.expect( prompt )
    vm.sendline( 'sudo python ~/mininet/examples/test/runner.py -v -quick' )


def examplesfullTest( vm, prompt=Prompt ):
    "Full (slow) test of mininet examples"
    vm.sendline( 'sudo apt-get install python-pexpect' )
    vm.expect( prompt )
    vm.sendline( 'sudo python ~/mininet/examples/test/runner.py -v' )


def walkthroughTest( vm, prompt=Prompt ):
    "Test mininet walkthrough"
    vm.sendline( 'sudo apt-get install python-pexpect' )
    vm.expect( prompt )
    vm.sendline( 'sudo python ~/mininet/mininet/test/test_walkthrough.py -v' )


def checkOutBranch( vm, branch, prompt=Prompt ):
    # This is a bit subtle; it will check out an existing branch (e.g. master)
    # if it exists; otherwise it will create a detached branch.
    # The branch will be rebased to its parent on origin.
    # This probably doesn't matter since we're running on a COW disk
    # anyway.
    vm.sendline( 'cd ~/mininet; git fetch --all; git checkout '
                 + branch + '; git pull --rebase origin ' + branch )
    vm.expect( prompt )
    vm.sendline( 'sudo make install' )


def interact( vm, tests, pre='', post='', prompt=Prompt ):
    "Interact with vm, which is a pexpect object"
    login( vm )
    log( '* Waiting for login...' )
    vm.expect( prompt )
    log( '* Sending hostname command' )
    vm.sendline( 'hostname' )
    log( '* Waiting for output' )
    vm.expect( prompt )
    log( '* Fetching Mininet VM install script' )
    branch = Branch if Branch else 'master'
    vm.sendline( 'wget '
                 'https://raw.github.com/mininet/mininet/%s/util/vm/'
                 'install-mininet-vm.sh' % branch )
    vm.expect( prompt )
    log( '* Running VM install script' )
    installcmd = 'bash install-mininet-vm.sh'
    if Branch:
        installcmd += ' ' + Branch
    vm.sendline( installcmd )
    vm.expect ( 'password for mininet: ' )
    vm.sendline( 'mininet' )
    log( '* Waiting for script to complete... ' )
    # Gigantic timeout for now ;-(
    vm.expect( 'Done preparing Mininet', timeout=3600 )
    log( '* Completed successfully' )
    vm.expect( prompt )
    version = getMininetVersion( vm )
    vm.expect( prompt )
    log( '* Mininet version: ', version )
    log( '* Testing Mininet' )
    runTests( vm, tests=tests, pre=pre, post=post )
    # Ubuntu adds this because we install via a serial console,
    # but we want the VM to boot via the VM console. Otherwise
    # we get the message 'error: terminal "serial" not found'
    log( '* Disabling serial console' )
    vm.sendline( "sudo sed -i -e 's/^GRUB_TERMINAL=serial/#GRUB_TERMINAL=serial/' "
                "/etc/default/grub; sudo update-grub" )
    vm.expect( prompt )
    log( '* Shutting down' )
    vm.sendline( 'sync; sudo shutdown -h now' )
    log( '* Waiting for EOF/shutdown' )
    vm.read()
    log( '* Interaction complete' )
    return version


def cleanup():
    "Clean up leftover qemu-nbd processes and other junk"
    call( [ 'sudo', 'pkill', '-9', 'qemu-nbd' ] )


def convert( cow, basename ):
    """Convert a qcow2 disk to a vmdk and put it a new directory
       basename: base name for output vmdk file"""
    vmdk = basename + '.vmdk'
    log( '* Converting qcow2 to vmdk' )
    run( 'qemu-img convert -f qcow2 -O vmdk %s %s' % ( cow, vmdk ) )
    return vmdk


# Template for OVF - a very verbose format!
# In the best of all possible worlds, we might use an XML
# library to generate this, but a template is easier and
# possibly more concise!
# Warning: XML file cannot begin with a newline!

OVFTemplate = """<?xml version="1.0"?>
<Envelope ovf:version="1.0" xml:lang="en-US"
    xmlns="http://schemas.dmtf.org/ovf/envelope/1"
    xmlns:ovf="http://schemas.dmtf.org/ovf/envelope/1"
    xmlns:rasd="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData"
    xmlns:vssd="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_VirtualSystemSettingData"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
<References>
<File ovf:href="%(diskname)s" ovf:id="file1" ovf:size="%(filesize)d"/>
</References>
<DiskSection>
<Info>Virtual disk information</Info>
<Disk ovf:capacity="%(disksize)d" ovf:capacityAllocationUnits="byte"
    ovf:diskId="vmdisk1" ovf:fileRef="file1"
    ovf:format="http://www.vmware.com/interfaces/specifications/vmdk.html#streamOptimized"/>
</DiskSection>
<NetworkSection>
<Info>The list of logical networks</Info>
<Network ovf:name="nat">
<Description>The nat  network</Description>
</Network>
</NetworkSection>
<VirtualSystem ovf:id="Mininet-VM">
<Info>A Mininet Virtual Machine (%(name)s)</Info>
<Name>mininet-vm</Name>
<OperatingSystemSection ovf:id="%(osid)d">
<Info>The kind of installed guest operating system</Info>
<Description>%(osname)s</Description>
</OperatingSystemSection>
<VirtualHardwareSection>
<Info>Virtual hardware requirements</Info>
<Item>
<rasd:AllocationUnits>hertz * 10^6</rasd:AllocationUnits>
<rasd:Description>Number of Virtual CPUs</rasd:Description>
<rasd:ElementName>1 virtual CPU(s)</rasd:ElementName>
<rasd:InstanceID>1</rasd:InstanceID>
<rasd:ResourceType>3</rasd:ResourceType>
<rasd:VirtualQuantity>1</rasd:VirtualQuantity>
</Item>
<Item>
<rasd:AllocationUnits>byte * 2^20</rasd:AllocationUnits>
<rasd:Description>Memory Size</rasd:Description>
<rasd:ElementName>%(mem)dMB of memory</rasd:ElementName>
<rasd:InstanceID>2</rasd:InstanceID>
<rasd:ResourceType>4</rasd:ResourceType>
<rasd:VirtualQuantity>%(mem)d</rasd:VirtualQuantity>
</Item>
<Item>
<rasd:Address>0</rasd:Address>
<rasd:Caption>scsiController0</rasd:Caption>
<rasd:Description>SCSI Controller</rasd:Description>
<rasd:ElementName>scsiController0</rasd:ElementName>
<rasd:InstanceID>4</rasd:InstanceID>
<rasd:ResourceSubType>lsilogic</rasd:ResourceSubType>
<rasd:ResourceType>6</rasd:ResourceType>
</Item>
<Item>
<rasd:AddressOnParent>0</rasd:AddressOnParent>
<rasd:ElementName>disk1</rasd:ElementName>
<rasd:HostResource>ovf:/disk/vmdisk1</rasd:HostResource>
<rasd:InstanceID>11</rasd:InstanceID>
<rasd:Parent>4</rasd:Parent>
<rasd:ResourceType>17</rasd:ResourceType>
</Item>
<Item>
<rasd:AddressOnParent>2</rasd:AddressOnParent>
<rasd:AutomaticAllocation>true</rasd:AutomaticAllocation>
<rasd:Connection>nat</rasd:Connection>
<rasd:Description>E1000 ethernet adapter on nat</rasd:Description>
<rasd:ElementName>ethernet0</rasd:ElementName>
<rasd:InstanceID>12</rasd:InstanceID>
<rasd:ResourceSubType>E1000</rasd:ResourceSubType>
<rasd:ResourceType>10</rasd:ResourceType>
</Item>
<Item>
<rasd:Address>0</rasd:Address>
<rasd:Caption>usb</rasd:Caption>
<rasd:Description>USB Controller</rasd:Description>
<rasd:ElementName>usb</rasd:ElementName>
<rasd:InstanceID>9</rasd:InstanceID>
<rasd:ResourceType>23</rasd:ResourceType>
</Item>
</VirtualHardwareSection>
</VirtualSystem>
</Envelope>
"""


def generateOVF( name, osname, osid, diskname, disksize, mem=1024 ):
    """Generate (and return) OVF file "name.ovf"
       name: root name of OVF file to generate
       osname: OS name for OVF (Ubuntu | Ubuntu 64-bit)
       osid: OS ID for OVF (93 | 94 )
       diskname: name of disk file
       disksize: size of virtual disk in bytes
       mem: VM memory size in MB"""
    ovf = name + '.ovf'
    filesize = stat( diskname )[ ST_SIZE ]
    params = dict( osname=osname, osid=osid, diskname=diskname,
                   filesize=filesize, disksize=disksize, name=name,
                   mem=mem )
    xmltext = OVFTemplate % params
    with open( ovf, 'w+' ) as f:
        f.write( xmltext )
    return ovf


def qcow2size( qcow2 ):
    "Return virtual disk size (in bytes) of qcow2 image"
    output = check_output( [ 'file', qcow2 ] )
    assert 'QCOW' in output
    bytes = int( re.findall( '(\d+) bytes', output )[ 0 ] )
    return bytes


def build( flavor='raring32server', tests=None, pre='', post='', memory=1024 ):
    """Build a Mininet VM; return vmdk and vdisk size
       tests: tests to run
       pre: command line to run in VM before tests
       post: command line to run in VM after tests
       prompt: shell prompt (default '$ ')
       memory: memory size in MB"""
    global LogFile, Zip
    start = time()
    lstart = localtime()
    date = strftime( '%y%m%d-%H-%M-%S', lstart)
    ovfdate = strftime( '%y%m%d', lstart )
    dir = 'mn-%s-%s' % ( flavor, date )
    if Branch:
        dir = 'mn-%s-%s-%s' % ( Branch, flavor, date )
    try:
        os.mkdir( dir )
    except:
        raise Exception( "Failed to create build directory %s" % dir )
    os.chdir( dir )
    LogFile = open( 'build.log', 'w' )
    log( '* Logging to', abspath( LogFile.name ) )
    log( '* Created working directory', dir )
    image, kernel, initrd = findBaseImage( flavor )
    basename = 'mininet-' + flavor
    volume = basename + '.qcow2'
    run( 'qemu-img create -f qcow2 -b %s %s' % ( image, volume ) )
    log( '* VM image for', flavor, 'created as', volume )
    if LogToConsole:
        logfile = stdout
    else:
        logfile = open( flavor + '.log', 'w+' )
    log( '* Logging results to', abspath( logfile.name ) )
    vm = boot( volume, kernel, initrd, logfile, memory=memory )
    version = interact( vm, tests=tests, pre=pre, post=post )
    size = qcow2size( volume )
    arch = archFor( flavor )
    vmdk = convert( volume, basename='mininet-vm-' + arch )
    if not SaveQCOW2:
        log( '* Removing qcow2 volume', volume )
        os.remove( volume )
    log( '* Converted VM image stored as', abspath( vmdk ) )
    ovfname = 'mininet-%s-%s-%s' % ( version, ovfdate, OSVersion( flavor ) )
    osname, osid = OVFOSNameID( flavor )
    ovf = generateOVF( name=ovfname, osname=osname, osid=osid,
                       diskname=vmdk, disksize=size )
    log( '* Generated OVF descriptor file', ovf )
    if Zip:
        log( '* Generating .zip file' )
        run( 'zip %s-ovf.zip %s %s' % ( ovfname, ovf, vmdk ) )
    end = time()
    elapsed = end - start
    log( '* Results logged to', abspath( logfile.name ) )
    log( '* Completed in %.2f seconds' % elapsed )
    log( '* %s VM build DONE!!!!! :D' % flavor )
    os.chdir( '..' )


def runTests( vm, tests=None, pre='', post='', prompt=Prompt ):
    "Run tests (list) in vm (pexpect object)"
    if not tests:
        tests = []
    if pre:
        log( '* Running command', pre )
        vm.sendline( pre )
        vm.expect( prompt )
    testfns = testDict()
    if tests:
        log( '* Running tests' )
    for test in tests:
        if test not in testfns:
            raise Exception( 'Unknown test: ' + test )
        log( '* Running test', test )
        fn = testfns[ test ]
        fn( vm )
        vm.expect( prompt )
    if post:
        log( '* Running post-test command', post )
        vm.sendline( post )
        vm.expect( prompt )

def getMininetVersion( vm ):
    "Run mn to find Mininet version in VM"
    vm.sendline( '~/mininet/bin/mn --version' )
    # Eat command line echo, then read output line
    vm.readline()
    version = vm.readline().strip()
    return version


def bootAndRunTests( image, tests=None, pre='', post='', prompt=Prompt,
                     memory=1024, outputFile=None ):
    """Boot and test VM
       tests: list of tests to run
       pre: command line to run in VM before tests
       post: command line to run in VM after tests
       prompt: shell prompt (default '$ ')
       memory: VM memory size in MB"""
    bootTestStart = time()
    basename = path.basename( image )
    image = abspath( image )
    tmpdir = mkdtemp( prefix='test-' + basename )
    log( '* Using tmpdir', tmpdir )
    cow = path.join( tmpdir, basename + '.qcow2' )
    log( '* Creating COW disk', cow )
    run( 'qemu-img create -f qcow2 -b %s %s' % ( image, cow ) )
    log( '* Extracting kernel and initrd' )
    kernel, initrd = extractKernel( image, flavor=basename, imageDir=tmpdir )
    if LogToConsole:
        logfile = stdout
    else:
        logfile = NamedTemporaryFile( prefix=basename,
                                      suffix='.testlog', delete=False )
    log( '* Logging VM output to', logfile.name )
    vm = boot( cow=cow, kernel=kernel, initrd=initrd, logfile=logfile,
               memory=memory )
    login( vm )
    log( '* Waiting for prompt after login' )
    vm.expect( prompt )
    if Branch:
        checkOutBranch( vm, branch=Branch )
        vm.expect( prompt )
    runTests( vm, tests=tests, pre=pre, post=post )
    # runTests eats its last prompt, but maybe it shouldn't...
    log( '* Shutting down' )
    vm.sendline( 'sudo shutdown -h now ' )
    log( '* Waiting for shutdown' )
    vm.wait()
    if outputFile:
        log( '* Saving temporary image to %s' % outputFile )
        convert( cow, outputFile )
    log( '* Removing temporary dir', tmpdir )
    srun( 'rm -rf ' + tmpdir )
    elapsed = time() - bootTestStart
    log( '* Boot and test completed in %.2f seconds' % elapsed )


def buildFlavorString():
    "Return string listing valid build flavors"
    return 'valid build flavors: ( %s )' % ' '.join( sorted( isoURLs ) )


def testDict():
    "Return dict of tests in this module"
    suffix = 'Test'
    trim = len( suffix )
    fdict = dict( [ ( fname[ : -trim ], f ) for fname, f in
                    inspect.getmembers( modules[ __name__ ],
                                    inspect.isfunction )
                  if fname.endswith( suffix ) ] )
    return fdict


def testString():
    "Return string listing valid tests"
    return 'valid tests: ( %s )' % ' '.join( testDict().keys() )


def parseArgs():
    "Parse command line arguments and run"
    global LogToConsole, NoKVM, Branch, Zip, TIMEOUT
    parser = argparse.ArgumentParser( description='Mininet VM build script',
                                      epilog=buildFlavorString() + ' ' +
                                      testString() )
    parser.add_argument( '-v', '--verbose', action='store_true',
                        help='send VM output to console rather than log file' )
    parser.add_argument( '-d', '--depend', action='store_true',
                         help='install dependencies for this script' )
    parser.add_argument( '-l', '--list', action='store_true',
                         help='list valid build flavors and tests' )
    parser.add_argument( '-c', '--clean', action='store_true',
                         help='clean up leftover build junk (e.g. qemu-nbd)' )
    parser.add_argument( '-q', '--qcow2', action='store_true',
                         help='save qcow2 image rather than deleting it' )
    parser.add_argument( '-n', '--nokvm', action='store_true',
                         help="Don't use kvm - use tcg emulation instead" )
    parser.add_argument( '-m', '--memory', metavar='MB', type=int,
                        default=1024, help='VM memory size in MB' )
    parser.add_argument( '-i', '--image', metavar='image', default=[],
                         action='append',
                         help='Boot and test an existing VM image' )
    parser.add_argument( '-t', '--test', metavar='test', default=[],
                         action='append',
                         help='specify a test to run' )
    parser.add_argument( '-w', '--timeout', metavar='timeout', type=int,
                            default=0, help='set expect timeout' )
    parser.add_argument( '-r', '--run', metavar='cmd', default='',
                         help='specify a command line to run before tests' )
    parser.add_argument( '-p', '--post', metavar='cmd', default='',
                         help='specify a command line to run after tests' )
    parser.add_argument( '-b', '--branch', metavar='branch',
                         help='branch to install and/or check out and test' )
    parser.add_argument( 'flavor', nargs='*',
                         help='VM flavor(s) to build (e.g. raring32server)' )
    parser.add_argument( '-z', '--zip', action='store_true',
                         help='archive .ovf and .vmdk into .zip file' )
    parser.add_argument( '-o', '--out',
                         help='output file for test image (vmdk)' )
    args = parser.parse_args()
    if args.depend:
        depend()
    if args.list:
        print buildFlavorString()
    if args.clean:
        cleanup()
    if args.verbose:
        LogToConsole = True
    if args.nokvm:
        NoKVM = True
    if args.branch:
        Branch = args.branch
    if args.zip:
        Zip = True
    if args.timeout:
        TIMEOUT = args.timeout
    if not args.test and not args.run and not args.post:
        args.test = [ 'sanity', 'core' ]
    for flavor in args.flavor:
        if flavor not in isoURLs:
            print "Unknown build flavor:", flavor
            print buildFlavorString()
            break
        try:
            build( flavor, tests=args.test, pre=args.run, post=args.post,
                   memory=args.memory )
        except Exception as e:
            log( '* BUILD FAILED with exception: ', e )
            exit( 1 )
    for image in args.image:
        bootAndRunTests( image, tests=args.test, pre=args.run,
                         post=args.post, memory=args.memory,
                         outputFile=args.out )
    if not ( args.depend or args.list or args.clean or args.flavor
             or args.image ):
        parser.print_help()


if __name__ == '__main__':
    parseArgs()

########NEW FILE########
