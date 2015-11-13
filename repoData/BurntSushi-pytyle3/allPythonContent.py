__FILENAME__ = config
# A list of windows to ignore... 
# will search both the class and role of the WM_CLASS property
# case-insensitive
ignore = ['gmrun', 'qjackctl', 'viewnior', 'gnome-screenshot', 'mplayer', 'file-roller']

# If this list is non-empty, only windows in the list will be tiled.
# The matching algorithm is precisely the same as for 'ignore'.
tile_only = []

# Whether to enable tiling on startup
tile_on_startup = False

# Whether tiled windows are below others
tiles_below = True

# Whether new windows should tile or float by default (default is False)
floats_default = False

# Whether tiled windows should have their decorations removed
remove_decorations = False

# How much to increment the master area proportion size
proportion_change = 0.05

# If you have panels that don't set struts (*ahem* JWM's panel), then
# setting a margin is the only way to force pytyle not to cover your panels.
# IMPORTANT NOTE: If you set *any* margin, pytyle3 will automatically skip
# all strut auto-detection. So your margins should account for all panels, even
# if the others set struts.
# The format here is to have one set of margins for each active physical
# head. They should be in the following order: Left to right, top to bottom.
# Make sure to set 'use_margins' to True!
use_margins = False
margins = [ {'top': 0, 'bottom': 1, 'left': 0, 'right': 0} ]

# Leave some empty space between windows
gap = 0

# Whether to send any debug information to stdout
debug = False


########NEW FILE########
__FILENAME__ = keybind
# This is a python script. Pay attention to the syntax and indentation
import state
import tile

bindings = {
# You can use Control and Shift. Alt is Mod1, Super is Mod4.

#Available commands :
# tile: start tiling
# untile: stop tiling and move the windows back to their original position
# cycle: switch between horizontal and vertical tiling

# increase_master: increase the space allocated to master windows
# decrease_master: increase the space allocated to slave windows
# add_master: send a window from the slave group to the master group
# remove_master: send a window from the master group to the slave group

# prev_client: Focus the previous window
# next_client: Focus the next window
# focus_master: Focus the master window

# switch_prev_client: switch active window with previous
# switch_next_client: switch active window with next
# rotate: shift all windows' positions (clockwise)
# make_master: send active window to the master position

	'Control-Mod1-v': tile.cmd('tile'),
    'Control-Mod1-BackSpace': tile.cmd('untile'),
    'Control-Mod1-s': tile.cmd('decrease_master'),
    'Control-Mod1-r': tile.cmd('increase_master'),
    'Control-Mod1-g': tile.cmd('remove_master'),
    'Control-Mod1-d': tile.cmd('add_master'),
	'Control-Mod1-c': tile.cmd('rotate'),
    'Control-Mod1-h': tile.cmd('cycle'),
    'Control-Mod1-f': tile.cmd('toggle_float'),

# quit pytyle
    'Control-Mod1-q': state.quit,
}


########NEW FILE########
__FILENAME__ = client
import time

import xcb.xproto

import xpybutil
import xpybutil.event as event
import xpybutil.ewmh as ewmh
import xpybutil.motif as motif
import xpybutil.icccm as icccm
import xpybutil.rect as rect
import xpybutil.util as util
import xpybutil.window as window

from debug import debug

import config
import state
import tile

clients = {}
ignore = [] # Some clients are never gunna make it...

class Client(object):
    def __init__(self, wid):
        self.wid = wid

        self.name = ewmh.get_wm_name(self.wid).reply() or 'N/A'
        debug('Connecting to %s' % self)

        window.listen(self.wid, 'PropertyChange', 'FocusChange')
        event.connect('PropertyNotify', self.wid, self.cb_property_notify)
        event.connect('FocusIn', self.wid, self.cb_focus_in)
        event.connect('FocusOut', self.wid, self.cb_focus_out)

        # This connects to the parent window (decorations)
        # We get all resize AND move events... might be too much
        self.parentid = window.get_parent_window(self.wid)
        window.listen(self.parentid, 'StructureNotify')
        event.connect('ConfigureNotify', self.parentid, 
                      self.cb_configure_notify)

        # A window should only be floating if that is default
        self.floating = config.floats_default

        # Not currently in a "moving" state
        self.moving = False

        # Load some data
        self.desk = ewmh.get_wm_desktop(self.wid).reply()

        # Add it to this desktop's tilers
        tile.update_client_add(self)

        # First cut at saving client geometry
        self.save()

    def remove(self):
        tile.update_client_removal(self)
        debug('Disconnecting from %s' % self)
        event.disconnect('ConfigureNotify', self.parentid)
        event.disconnect('PropertyNotify', self.wid)
        event.disconnect('FocusIn', self.wid)
        event.disconnect('FocusOut', self.wid)

    def activate(self):
        ewmh.request_active_window_checked(self.wid, source=1).check()

    def unmaximize(self):
        vatom = util.get_atom('_NET_WM_STATE_MAXIMIZED_VERT')
        hatom = util.get_atom('_NET_WM_STATE_MAXIMIZED_HORZ')
        ewmh.request_wm_state_checked(self.wid, 0, vatom, hatom).check()

    def save(self):
        self.saved_geom = window.get_geometry(self.wid)
        self.saved_state = ewmh.get_wm_state(self.wid).reply()

    def restore(self):
        debug('Restoring %s' % self)
        if config.remove_decorations:
            motif.set_hints_checked(self.wid,2,decoration=1).check()
        if config.tiles_below:
            ewmh.request_wm_state_checked(self.wid,0,util.get_atom('_NET_WM_STATE_BELOW')).check()
        if self.saved_state:
            fullymaxed = False
            vatom = util.get_atom('_NET_WM_STATE_MAXIMIZED_VERT')
            hatom = util.get_atom('_NET_WM_STATE_MAXIMIZED_HORZ')

            if vatom in self.saved_state and hatom in self.saved_state:
                fullymaxed = True
                ewmh.request_wm_state_checked(self.wid, 1, vatom, hatom).check()
            elif vatom in self.saved_state:
                ewmh.request_wm_state_checked(self.wid, 1, vatom).check()
            elif hatom in self.saved_state:
                ewmh.request_wm_state_checked(self.wid, 1, hatom).check()

            # No need to continue if we've fully maximized the window
            if fullymaxed:
                return
            
        mnow = rect.get_monitor_area(window.get_geometry(self.wid),
                                     state.monitors)
        mold = rect.get_monitor_area(self.saved_geom, state.monitors)

        x, y, w, h = self.saved_geom

        # What if the client is on a monitor different than what it was before?
        # Use the same algorithm in Openbox to convert one monitor's 
        # coordinates to another.
        if mnow != mold:
            nowx, nowy, noww, nowh = mnow
            oldx, oldy, oldw, oldh = mold

            xrat, yrat = float(noww) / float(oldw), float(nowh) / float(oldh)

            x = nowx + (x - oldx) * xrat
            y = nowy + (y - oldy) * yrat
            w *= xrat
            h *= yrat

        window.moveresize(self.wid, x, y, w, h)

    def moveresize(self, x=None, y=None, w=None, h=None):
        # Ignore this if the user is moving the window...
        if self.moving:
            print 'Sorry but %s is moving...' % self
            return

        try:
            window.moveresize(self.wid, x, y, w, h)
        except:
            pass

    def is_button_pressed(self):
        try:
            pointer = xpybutil.conn.core.QueryPointer(self.wid).reply()
            if pointer is None:
                return False

            if (xcb.xproto.KeyButMask.Button1 & pointer.mask or
                xcb.xproto.KeyButMask.Button3 & pointer.mask):
                return True
        except xcb.xproto.BadWindow:
            pass

        return False

    def cb_focus_in(self, e):
        if self.moving and e.mode == xcb.xproto.NotifyMode.Ungrab:
            state.GRAB = None
            self.moving = False
            tile.update_client_moved(self)

    def cb_focus_out(self, e):
        if e.mode == xcb.xproto.NotifyMode.Grab:
            state.GRAB = self

    def cb_configure_notify(self, e):
        if state.GRAB is self and self.is_button_pressed():
            self.moving = True

    def cb_property_notify(self, e):
        aname = util.get_atom_name(e.atom)

        try:
            if aname == '_NET_WM_DESKTOP':
                if should_ignore(self.wid):
                    untrack_client(self.wid)
                    return

                olddesk = self.desk
                self.desk = ewmh.get_wm_desktop(self.wid).reply()

                if self.desk is not None and self.desk != olddesk:
                    tile.update_client_desktop(self, olddesk)
                else:
                    self.desk = olddesk
            elif aname == '_NET_WM_STATE':
                if should_ignore(self.wid):
                    untrack_client(self.wid)
                    return
        except xcb.xproto.BadWindow:
            pass # S'ok...

    def __str__(self):
        return '{%s (%d)}' % (self.name[0:30], self.wid)

def update_clients():
    client_list = ewmh.get_client_list_stacking().reply()
    client_list = list(reversed(client_list))
    for c in client_list:
        if c not in clients:
            track_client(c)
    for c in clients.keys():
        if c not in client_list:
            untrack_client(c)

def track_client(client):
    assert client not in clients

    try:
        if not should_ignore(client):
            if state.PYTYLE_STATE == 'running':
                # This is truly unfortunate and only seems to be necessary when
                # a client comes back from an iconified state. This causes a 
                # slight lag when a new window is mapped, though.
                time.sleep(0.2)

            clients[client] = Client(client)
    except xcb.xproto.BadWindow:
        debug('Window %s was destroyed before we could finish inspecting it. '
              'Untracking it...' % client)
        untrack_client(client)

def untrack_client(client):
    if client not in clients:
        return

    c = clients[client]
    del clients[client]
    c.remove()

def should_ignore(client):
    # Don't waste time on clients we'll never possibly tile
    if client in ignore:
        return True

    nm = ewmh.get_wm_name(client).reply()

    wm_class = icccm.get_wm_class(client).reply()
    if wm_class is not None:
        try:
            inst, cls = wm_class
            matchNames = set([inst.lower(), cls.lower()])

            if matchNames.intersection(config.ignore):
                debug('Ignoring %s because it is in the ignore list' % nm)
                return True

            if hasattr(config, 'tile_only') and config.tile_only:
              if not matchNames.intersection(config.tile_only):
                debug('Ignoring %s because it is not in the tile_only '
                      'list' % nm)
                return True
        except ValueError:
            pass

    if icccm.get_wm_transient_for(client).reply() is not None:
        debug('Ignoring %s because it is transient' % nm)
        ignore.append(client)
        return True

    wtype = ewmh.get_wm_window_type(client).reply()
    if wtype:
        for atom in wtype:
            aname = util.get_atom_name(atom)

            if aname in ('_NET_WM_WINDOW_TYPE_DESKTOP',
                         '_NET_WM_WINDOW_TYPE_DOCK',
                         '_NET_WM_WINDOW_TYPE_TOOLBAR',
                         '_NET_WM_WINDOW_TYPE_MENU',
                         '_NET_WM_WINDOW_TYPE_UTILITY',
                         '_NET_WM_WINDOW_TYPE_SPLASH',
                         '_NET_WM_WINDOW_TYPE_DIALOG',
                         '_NET_WM_WINDOW_TYPE_DROPDOWN_MENU',
                         '_NET_WM_WINDOW_TYPE_POPUP_MENU',
                         '_NET_WM_WINDOW_TYPE_TOOLTIP',
                         '_NET_WM_WINDOW_TYPE_NOTIFICATION',
                         '_NET_WM_WINDOW_TYPE_COMBO', 
                         '_NET_WM_WINDOW_TYPE_DND'):
                debug('Ignoring %s because it has type %s' % (nm, aname))
                ignore.append(client)
                return True

    wstate = ewmh.get_wm_state(client).reply()
    if wstate is None:
        debug('Ignoring %s because it does not have a state' % nm)
        return True

    for atom in wstate:
        aname = util.get_atom_name(atom)

        # For now, while I decide how to handle these guys
        if aname == '_NET_WM_STATE_STICKY':
            debug('Ignoring %s because it is sticky and they are weird' % nm)
            return True
        if aname in ('_NET_WM_STATE_SHADED', '_NET_WM_STATE_HIDDEN',
                     '_NET_WM_STATE_FULLSCREEN', '_NET_WM_STATE_MODAL'):
            debug('Ignoring %s because it has state %s' % (nm, aname))
            return True

    d = ewmh.get_wm_desktop(client).reply()
    if d == 0xffffffff:
        debug('Ignoring %s because it\'s on all desktops' \
              '(not implemented)' % nm)
        return True

    return False

def cb_property_notify(e):
    aname = util.get_atom_name(e.atom)

    if aname == '_NET_CLIENT_LIST_STACKING':
        update_clients()

event.connect('PropertyNotify', xpybutil.root, cb_property_notify)


########NEW FILE########
__FILENAME__ = config
import os
import os.path
import sys

xdg = os.getenv('XDG_CONFIG_HOME') or os.path.join(os.getenv('HOME'), '.config')
conffile = os.path.join(xdg, 'pytyle3', 'config.py')

if not os.access(conffile, os.R_OK):
    conffile = os.path.join('/', 'etc', 'xdg', 'pytyle3', 'config.py')
    if not os.access(conffile, os.R_OK):
        print >> sys.stderr, 'UNRECOVERABLE ERROR: ' \
                             'No configuration file found at %s' % conffile
        sys.exit(1)

execfile(conffile)


########NEW FILE########
__FILENAME__ = debug
import sys

import config

def debug(s):
    if not config.debug:
        return
    print s
    sys.stdout.flush()


########NEW FILE########
__FILENAME__ = keybind
import os
import os.path
import sys

# from xpybutil import conn, root 
# import xpybutil.event as event 
import xpybutil.keybind as keybind

bindings = None

#####################
# Get key bindings
xdg = os.getenv('XDG_CONFIG_HOME') or os.path.join(os.getenv('HOME'), '.config')
conffile = os.path.join(xdg, 'pytyle3', 'keybind.py')

if not os.access(conffile, os.R_OK):
    conffile = os.path.join('/', 'etc', 'xdg', 'pytyle3', 'keybind.py')
    if not os.access(conffile, os.R_OK):
        print >> sys.stderr, 'UNRECOVERABLE ERROR: ' \
                             'No configuration file found at %s' % conffile
        sys.exit(1)

execfile(conffile)
#####################

assert bindings is not None

for key_string, fun in bindings.iteritems():
    if not keybind.bind_global_key('KeyPress', key_string, fun):
        print >> sys.stderr, 'Could not bind %s' % key_string


########NEW FILE########
__FILENAME__ = layout_vert_horz
import xpybutil

from pt3.debug import debug

import pt3.config as config
import pt3.client as client
import pt3.state as state
from pt3.layouts import Layout

import store

class OrientLayout(Layout):
    # Start implementing abstract methods
    def __init__(self, desk):
        super(OrientLayout, self).__init__(desk)
        self.store = store.Store()
        self.proportion = 0.5

    def add(self, c):
        debug('%s being added to %s' % (c, self))
        self.store.add(c)

        if self.tiling:
            self.tile()

    def remove(self, c):
        debug('%s being removed from %s' % (c, self))
        self.store.remove(c)

        if self.tiling:
            self.tile()

    def untile(self):
        debug('Untiling %s' % (self))
        for c in self.store.masters + self.store.slaves:
			c.restore()

        self.tiling = False
        xpybutil.conn.flush()

    def next_client(self):
        nxt = self._get_next()
        if nxt:
            nxt.activate()

    def switch_next_client(self):
        assert self.tiling

        awin = self._get_focused()
        nxt = self._get_next()
        if None not in (awin, nxt):
            self.store.switch(awin, nxt)
            self.tile()

    def prev_client(self):
        prv = self._get_prev()
        if prv:
            prv.activate()

    def switch_prev_client(self):
        assert self.tiling

        awin = self._get_focused()
        prv = self._get_prev()
        if None not in (awin, prv):
            self.store.switch(awin, prv)
            self.tile()
            
    def rotate(self):
		assert self.tiling
		
		self.store.slaves.insert(0,self.store.masters.pop(0)) # move the first master to slave
		self.store.masters.append(self.store.slaves.pop(-1)) # move the last slave to master
		self.tile()

    def clients(self):
        return self.store.masters + self.store.slaves

    # End abstract methods; begin OrientLayout specific methods

    def decrease_master(self):
        self.proportion = max(0.0, self.proportion - config.proportion_change)
        self.tile()

    def increase_master(self):
        self.proportion = min(1.0, self.proportion + config.proportion_change)
        self.tile()

    def add_master(self):
        assert self.tiling

        self.store.inc_masters(self._get_focused())
        self.tile()

    def remove_master(self):
        assert self.tiling

        self.store.dec_masters(self._get_focused())
        self.tile()

    def make_master(self):
        assert self.tiling

        if not self.store.masters: # no masters right now, so don't add any!
            return

        awin = self._get_focused()
        if awin is None:
            return

        self.store.switch(self.store.masters[0], awin)
        self.tile()

    def focus_master(self):
        assert self.tiling

        if not self.store.masters:
            return

        self.store.masters[0].activate()

    def toggle_float(self):
        assert self.tiling

        self.store.toggle_float(self._get_focused())
        self.tile()
    
    # Begin private methods that should not be called by the user directly

    def _get_focused(self):
        
        if type(state.activewin) == list:
            state.activewin = state.activewin[0]
        
        if state.activewin not in client.clients:
            return None

        awin = client.clients[state.activewin]
        if awin not in self.store.masters + self.store.slaves + self.store.floats:
            return None

        return awin

    def _get_next(self):
        ms, ss = self.store.masters, self.store.slaves
        awin = self._get_focused()
        if awin is None:
            return None

        nxt = None
        try:
            i = ms.index(awin)
            if i == 0:
                nxt = ss[0] if ss else ms[-1]
            else:
                nxt = ms[i - 1]
        except ValueError:
            i = ss.index(awin)
            if i == len(ss) - 1:
                nxt = ms[-1] if ms else ss[0]
            else:
                nxt = ss[i + 1]

        return nxt

    def _get_prev(self):
        ms, ss = self.store.masters, self.store.slaves
        awin = self._get_focused()
        if awin is None:
            return None

        prv = None
        try:
            i = ms.index(awin)
            if i == len(ms) - 1:
                prv = ss[-1] if ss else ms[0]
            else:
                prv = ms[i + 1]
        except ValueError:
            i = ss.index(awin)
            if i == 0:
                prv = ms[0] if ms else ss[-1]
            else:
                prv = ss[i - 1]

        return prv

class VerticalLayout(OrientLayout):
    def tile(self, save=True):
        if not super(VerticalLayout, self).tile(save):
            return

        wx, wy, ww, wh = self.get_workarea()
        msize = len(self.store.masters)
        ssize = len(self.store.slaves)

        if not msize and not ssize:
            return

        mx = wx # left limit
        mw = int(ww * self.proportion) # width of the master
        sx = mx + mw
        sw = ww - mw
        g = config.gap # Gap between windows

        if mw <= 0 or mw > ww or sw <= 0 or sw > ww:
            return
		
#Masters
        if msize:
            mh = (wh - (msize + 1) * g) / msize # Height of each window
            mw = ww if not ssize else mw
            for i, c in enumerate(self.store.masters): # i is the number of the window in the list
                c.moveresize(x=mx + g, y= g + wy + i * (mh + g), w=mw - 2 * g, h=mh)

# Slaves
        if ssize:
            sh = (wh - (ssize + 1) * g)/ ssize # Height of each window
            if not msize:
                sx, sw = wx, ww
            for i, c in enumerate(self.store.slaves):
                c.moveresize(x=sx, y= g + wy + i * (sh + g), w=sw - g, h=sh)

        xpybutil.conn.flush()

class HorizontalLayout(OrientLayout):
    def tile(self, save=True):
        if not super(HorizontalLayout, self).tile(save):
            return

        wx, wy, ww, wh = self.get_workarea()
        msize = len(self.store.masters)
        ssize = len(self.store.slaves)

        if not msize and not ssize:
            return

        my = wy
        mh = int(wh * self.proportion)
        sy = my + mh
        sh = wh - mh
        g = config.gap # Gap between windows

        if mh <= 0 or mh > wh or sh <= 0 or sh > wh:
            return

# Masters
        if msize:
            #mw = ww / msize
            mw = (ww - (msize + 1) * g) / msize # Height of each window
            mh = wh if not ssize else mh
            for i, c in enumerate(self.store.masters):
                c.moveresize(x=g + wx + i * (g + mw), y=my + g, w=mw, h=mh - 2 * g)

#Slaves
        if ssize:
            #sw = ww / ssize
            sw = (ww - (ssize + 1) * g) / ssize # Height of each window
            if not msize:
                sy, sh = wy, wh
            for i, c in enumerate(self.store.slaves):
                c.moveresize(x= g + wx + i * (g + sw), y=sy, w=sw, h=sh - g)

        xpybutil.conn.flush()


########NEW FILE########
__FILENAME__ = store
import pt3.config as config
import xpybutil.ewmh as ewmh
import xpybutil.util as util
import xpybutil.motif as motif

class Store(object):
    def __init__(self):
        self.masters, self.slaves, self.floats = [], [], []
        self.mcnt = 1 # Number of masters allowed

    def add(self, c, above=None):
        if c.floating:
            if config.remove_decorations:
                motif.set_hints_checked(c.wid,2,decoration=1).check() # add decorations
            if config.tiles_below:
                ewmh.request_wm_state_checked(c.wid,0,util.get_atom('_NET_WM_STATE_BELOW')).check()
            self.floats.append(c)
        else:
            if config.remove_decorations:
                motif.set_hints_checked(c.wid,2,decoration=2).check() #remove decorations
            if config.tiles_below:
                ewmh.request_wm_state_checked(c.wid,1,util.get_atom('_NET_WM_STATE_BELOW')).check()
            if len(self.masters) < self.mcnt:
                if c in self.slaves:
                    self.slaves.remove(c)
                self.masters.append(c)
            elif c not in self.slaves:
                self.slaves.append(c)

    def remove(self, c):
        if c in self.floats:
            self.floats.remove(c)
        else:
            if c in self.masters:
                self.masters.remove(c)
                if len(self.masters) < self.mcnt and self.slaves:
                    self.masters.append(self.slaves.pop(0))
            elif c in self.slaves:
                self.slaves.remove(c)

    def reset(self):
        self.__init__()

    def inc_masters(self, current=None):
        self.mcnt = min(self.mcnt + 1, len(self))
        if len(self.masters) < self.mcnt and self.slaves:
            try:
                newmast = self.slaves.index(current)
            except ValueError:
                newmast = 0
            self.masters.append(self.slaves.pop(newmast))

    def dec_masters(self, current=None):
        self.mcnt = max(self.mcnt - 1, 0)
        if len(self.masters) > self.mcnt:
            try:
                newslav = self.masters.index(current)
            except ValueError:
                newslav = -1
            self.slaves.append(self.masters.pop(newslav))

    def switch(self, c1, c2):
        ms, ss = self.masters, self.slaves # alias
        if c1 in ms and c2 in ms:
            i1, i2 = ms.index(c1), ms.index(c2)
            ms[i1], ms[i2] = ms[i2], ms[i1]
        elif c1 in self.slaves and c2 in self.slaves:
            i1, i2 = ss.index(c1), ss.index(c2)
            ss[i1], ss[i2] = ss[i2], ss[i1]
        elif c1 in ms: # and c2 in self.slaves
            i1, i2 = ms.index(c1), ss.index(c2)
            ms[i1], ss[i2] = ss[i2], ms[i1]
        else: # c1 in ss and c2 in ms
            i1, i2 = ss.index(c1), ms.index(c2)
            ss[i1], ms[i2] = ms[i2], ss[i1]

    def toggle_float(self, c):
        self.remove(c)
        c.floating = not c.floating
        self.add(c)

    def __len__(self):
        return len(self.masters) + len(self.slaves)

    def __str__(self):
        s = ['Masters: %s' % [str(c) for c in self.masters],
             'Slaves: %s' % [str(c) for c in self.slaves]]
        return '\n'.join(s)


########NEW FILE########
__FILENAME__ = state
import sys
import time

import xpybutil
import xpybutil.event as event
import xpybutil.ewmh as ewmh
import xpybutil.rect as rect
import xpybutil.util as util
import xpybutil.window as window
import xpybutil.xinerama as xinerama

import config

PYTYLE_STATE = 'startup'
GRAB = None

_wmrunning = False

wm = 'N/A'
utilwm = window.WindowManagers.Unknown
while not _wmrunning:
    w = ewmh.get_supporting_wm_check(xpybutil.root).reply()
    if w:
        childw = ewmh.get_supporting_wm_check(w).reply()
        if childw == w:
            _wmrunning = True
            wm = ewmh.get_wm_name(childw).reply()
            if wm.lower() == 'openbox':
                utilwm = window.WindowManagers.Openbox
            elif wm.lower() == 'kwin':
                utilwm = window.WindowManagers.KWin

            print '%s window manager is running...' % wm
            sys.stdout.flush()

    if not _wmrunning:
        time.sleep(1)

root_geom = ewmh.get_desktop_geometry().reply()
monitors = xinerama.get_monitors()
phys_monitors = xinerama.get_physical_mapping(monitors)
desk_num = ewmh.get_number_of_desktops().reply()
activewin = ewmh.get_active_window().reply()
desktop = ewmh.get_current_desktop().reply()
visibles = ewmh.get_visible_desktops().reply() or [desktop]
stacking = ewmh.get_client_list_stacking().reply()
workarea = []

def quit():
    print 'Exiting...'
    import tile
    for tiler in tile.tilers:
        tile.get_active_tiler(tiler)[0].untile()
    sys.exit(0)

def update_workarea():
    '''
    We update the current workarea either by autodetecting struts, or by
    using margins specified in the config file. Never both, though.
    '''
    global workarea

    if hasattr(config, 'use_margins') and config.use_margins:
        workarea = monitors[:]
        for physm, margins in enumerate(config.margins):
            i = phys_monitors[physm]
            mx, my, mw, mh = workarea[i]
            workarea[i] = (mx + margins['left'], my + margins['top'],
                           mw - (margins['left'] + margins['right']),
                           mh - (margins['top'] + margins['bottom']))
    else:
        workarea = rect.monitor_rects(monitors)

def cb_property_notify(e):
    global activewin, desk_num, desktop, monitors, phys_monitors, root_geom, \
           stacking, visibles, workarea

    aname = util.get_atom_name(e.atom)
    if aname == '_NET_DESKTOP_GEOMETRY':
        root_geom = ewmh.get_desktop_geometry().reply()
        monitors = xinerama.get_monitors()
        phys_monitors = xinerama.get_physical_mapping(monitors)
    elif aname == '_NET_ACTIVE_WINDOW':
        activewin = ewmh.get_active_window().reply()
    elif aname == '_NET_CURRENT_DESKTOP':
        desktop = ewmh.get_current_desktop().reply()
        if visibles is None or len(visibles) == 1:
            visibles = [desktop]
    elif aname == '_NET_VISIBLE_DESKTOPS':
        visibles = ewmh.get_visible_desktops().reply()
    elif aname == '_NET_NUMBER_OF_DESKTOPS':
        desk_num = ewmh.get_number_of_desktops().reply()
    elif aname == '_NET_CLIENT_LIST_STACKING':
        stacking = ewmh.get_client_list_stacking().reply()
    elif aname == '_NET_WORKAREA':
        update_workarea()

window.listen(xpybutil.root, 'PropertyChange')
event.connect('PropertyNotify', xpybutil.root, cb_property_notify)

update_workarea()


########NEW FILE########
__FILENAME__ = tile
import xpybutil
import xpybutil.event as event
import xpybutil.util as util

from debug import debug

import state
from layouts import layouts

try:
    from config import tile_on_startup
except ImportError:
    tile_on_startup = False

tilers = {}

def debug_state():
    debug('-' * 45)
    for d in tilers:
        if d not in state.visibles:
            continue
        tiler, _ = get_active_tiler(d)
        debug(tiler)
        debug(tiler.store)
        debug('-' * 45)

def cmd(action):
    def _cmd():
        if state.desktop not in tilers:
            return

        tiler, _ = get_active_tiler(state.desktop)

        if action == 'tile':
            tiler.tile()
        elif tiler.tiling:
            if action == 'cycle':
                cycle_current_tiler()
            else:
                getattr(tiler, action)()

    return _cmd

def cycle_current_tiler():
    assert state.desktop in tilers

    tiler, i = get_active_tiler(state.desktop)
    newtiler = tilers[state.desktop][(i + 1) % len(tilers[state.desktop])]

    tiler.active = False
    tiler.tiling = False
    newtiler.active = True

    debug('Switching tiler from %s to %s on desktop %d' % (
           tiler.__class__.__name__, newtiler.__class__.__name__, 
           state.desktop))

    newtiler.tile(save=False)

def get_active_tiler(desk):
    assert desk in tilers

    for i, tiler in enumerate(tilers[desk]):
        if tiler.active:
            return tiler, i

def update_client_moved(c):
    assert c.desk in tilers

    tiler, _ = get_active_tiler(c.desk)
    if tiler.tiling:
        tiler.tile()

def update_client_desktop(c, olddesk):
    assert c.desk in tilers

    if olddesk in tilers:
        for tiler in tilers[olddesk]:
            tiler.remove(c)

    for tiler in tilers[c.desk]:
        tiler.add(c)

def update_client_add(c):
    assert c.desk in tilers
    
    for tiler in tilers[c.desk]:
        tiler.add(c)

def update_client_removal(c):
    assert c.desk in tilers

    for tiler in tilers[c.desk]:
        tiler.remove(c)

def update_tilers():
    for d in xrange(state.desk_num):
        if d not in tilers:
            debug('Adding tilers to desktop %d' % d)
            tilers[d] = []
            for lay in layouts:
                t = lay(d)
                tilers[d].append(t)
            tilers[d][0].active = True
            if tile_on_startup:
                tilers[d][0].tiling = True
                tilers[d][0].tile()
    for d in tilers.keys():
        if d >= state.desk_num:
            debug('Removing tilers from desktop %d' % d)
            del tilers[d]

def cb_property_notify(e):
    aname = util.get_atom_name(e.atom)

    if aname == '_NET_NUMBER_OF_DESKTOPS':
        update_tilers()
    elif aname == '_NET_CURRENT_DESKTOP':
        if len(state.visibles) == 1:
            tiler, _ = get_active_tiler(state.desktop)
            if tiler.tiling:
                tiler.tile()
    elif aname == '_NET_VISIBLE_DESKTOPS':
        for d in state.visibles:
            tiler, _ = get_active_tiler(d)
            if tiler.tiling:
                tiler.tile()

event.connect('PropertyNotify', xpybutil.root, cb_property_notify)


########NEW FILE########
