__FILENAME__ = debug
#!/usr/bin/env python3

import os
import sys

# None of this works on Windows atm
if sys.platform != 'win32':

    # Store config locally
    config_dir = os.path.abspath('./config')
    os.environ['XDG_CONFIG_HOME'] = config_dir

    # Migrate old debug_config
    old_config_dir = os.path.abspath('./debug_config')
    if os.path.exists(old_config_dir):
        os.rename(old_config_dir, config_dir)

    if not os.path.exists(config_dir):
        os.makedirs(config_dir)

    # Enable verbose logging and test mode
    if len(sys.argv) == 1:
        sys.argv.append('-tv')

from pithos import pithos

pithos.main()

########NEW FILE########
__FILENAME__ = AboutPithosDialog
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: nil; -*-
### BEGIN LICENSE
# Copyright (C) 2010-2012 Kevin Mehall <km@kevinmehall.net>
#This program is free software: you can redistribute it and/or modify it 
#under the terms of the GNU General Public License version 3, as published 
#by the Free Software Foundation.
#
#This program is distributed in the hope that it will be useful, but 
#WITHOUT ANY WARRANTY; without even the implied warranties of 
#MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR 
#PURPOSE.  See the GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License along 
#with this program.  If not, see <http://www.gnu.org/licenses/>.
### END LICENSE

from gi.repository import Gtk, GdkPixbuf

from .pithosconfig import get_ui_file, get_media_file
from .util import open_browser

class AboutPithosDialog(Gtk.AboutDialog):
    __gtype_name__ = "AboutPithosDialog"

    def __init__(self):
        """__init__ - This function is typically not called directly.
        Creation of a AboutPithosDialog requires redeading the associated ui
        file and parsing the ui definition extrenally, 
        and then calling AboutPithosDialog.finish_initializing().
    
        Use the convenience function NewAboutPithosDialog to create 
        NewAboutPithosDialog objects.
    
        """
        pass

    def finish_initializing(self, builder):
        """finish_initalizing should be called after parsing the ui definition
        and creating a AboutPithosDialog object with it in order to finish
        initializing the start of the new AboutPithosDialog instance.
    
        """
        #get a reference to the builder and set up the signals
        self.builder = builder
        self.builder.connect_signals(self)

        self.set_logo(GdkPixbuf.Pixbuf.new_from_file_at_scale(get_media_file('icon'), -1, 96, True))

        #code for other initialization actions should be added here

    def activate_link_cb(self, wid, uri):
        open_browser(uri)
        return True

def NewAboutPithosDialog():
    """NewAboutPithosDialog - returns a fully instantiated
    AboutPithosDialog object. Use this function rather than
    creating a AboutPithosDialog instance directly.
    
    """

    builder = Gtk.Builder()
    builder.add_from_file(get_ui_file('about'))    
    dialog = builder.get_object("about_pithos_dialog")
    dialog.finish_initializing(builder)
    return dialog

if __name__ == "__main__":
    dialog = NewAboutPithosDialog()
    dialog.show()
    Gtk.main()


########NEW FILE########
__FILENAME__ = dbus_service
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: nil; -*-
### BEGIN LICENSE
# Copyright (C) 2010 Kevin Mehall <km@kevinmehall.net>
#This program is free software: you can redistribute it and/or modify it 
#under the terms of the GNU General Public License version 3, as published 
#by the Free Software Foundation.
#
#This program is distributed in the hope that it will be useful, but 
#WITHOUT ANY WARRANTY; without even the implied warranties of 
#MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR 
#PURPOSE.  See the GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License along 
#with this program.  If not, see <http://www.gnu.org/licenses/>.
### END LICENSE

import dbus.service

DBUS_BUS = "net.kevinmehall.Pithos"
DBUS_OBJECT_PATH = "/net/kevinmehall/Pithos"

def song_to_dict(song):
    d = {}
    if song:
        for i in ['artist', 'title', 'album', 'songDetailURL']:
            d[i] = getattr(song, i)
    return d
  
class PithosDBusProxy(dbus.service.Object):
    def __init__(self, window):
        self.bus = dbus.SessionBus()
        bus_name = dbus.service.BusName(DBUS_BUS, bus=self.bus)
        dbus.service.Object.__init__(self, bus_name, DBUS_OBJECT_PATH)
        self.window = window
        self.window.connect("song-changed", self.songchange_handler)
        self.window.connect("play-state-changed", self.playstate_handler)
        
    def playstate_handler(self, window, state):
        self.PlayStateChanged(state)
        
    def songchange_handler(self, window, song):
        self.SongChanged(song_to_dict(song))
    
    @dbus.service.method(DBUS_BUS)
    def PlayPause(self):
        self.window.playpause_notify()
    
    @dbus.service.method(DBUS_BUS)
    def SkipSong(self):
        self.window.next_song()
    
    @dbus.service.method(DBUS_BUS)
    def LoveCurrentSong(self):
        self.window.love_song()
    
    @dbus.service.method(DBUS_BUS)
    def BanCurrentSong(self):
        self.window.ban_song()
    
    @dbus.service.method(DBUS_BUS)
    def TiredCurrentSong(self):
        self.window.tired_song()
        
    @dbus.service.method(DBUS_BUS)
    def Present(self):
        self.window.bring_to_top()
        
    @dbus.service.method(DBUS_BUS, out_signature='a{sv}')
    def GetCurrentSong(self):
        return song_to_dict(self.window.current_song)
        
    @dbus.service.method(DBUS_BUS, out_signature='b')
    def IsPlaying(self):
        return self.window.playing
        
    @dbus.service.signal(DBUS_BUS, signature='b')
    def PlayStateChanged(self, state):
        pass
        
    @dbus.service.signal(DBUS_BUS, signature='a{sv}')
    def SongChanged(self, songinfo):
        pass

########NEW FILE########
__FILENAME__ = gobject_worker
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: nil; -*-
### BEGIN LICENSE
# Copyright (C) 2010-2012 Kevin Mehall <km@kevinmehall.net>
#This program is free software: you can redistribute it and/or modify it 
#under the terms of the GNU General Public License version 3, as published 
#by the Free Software Foundation.
#
#This program is distributed in the hope that it will be useful, but 
#WITHOUT ANY WARRANTY; without even the implied warranties of 
#MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR 
#PURPOSE.  See the GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License along 
#with this program.  If not, see <http://www.gnu.org/licenses/>.
### END LICENSE

import logging
import threading
import queue
from gi.repository import GObject, GLib
import traceback
GObject.threads_init()

class GObjectWorker():
    def __init__(self):
        self.thread = threading.Thread(target=self._run)
        self.thread.daemon = True
        self.queue = queue.Queue()
        self.thread.start()
        
    def _run(self):
        while True:
            command, args, callback, errorback = self.queue.get()
            try:
                result = command(*args)
                if callback:
                    GLib.idle_add(callback, result)
            except Exception as e:
                e.traceback = traceback.format_exc()
                if errorback:
                    GLib.idle_add(errorback, e)
                
    def send(self, command, args=(), callback=None, errorback=None):
        if errorback is None: errorback = self._default_errorback
        self.queue.put((command, args, callback, errorback))
        
    def _default_errorback(self, error):
        logging.error("Unhandled exception in worker thread:\n{}".format(error.traceback))
        
if __name__ == '__main__':
    worker = GObjectWorker()
    import time
    from gi.repository import Gtk
    
    def test_cmd(a, b):
        logging.info("running...")
        time.sleep(5)
        logging.info("done")
        return a*b
        
    def test_cb(result):
        logging.info("got result {}".format(result))
        
    logging.info("sending")
    worker.send(test_cmd, (3,4), test_cb)
    worker.send(test_cmd, ((), ()), test_cb) #trigger exception in worker to test error handling
    
    Gtk.main()
        
                

########NEW FILE########
__FILENAME__ = mpris
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: nil; -*-
### BEGIN LICENSE
# Copyright (C) 2011 Rick Spencer <rick.spencer@canonical.com>
# Copyright (C) 2011-2012 Kevin Mehall <km@kevinmehall.net>
#This program is free software: you can redistribute it and/or modify it 
#under the terms of the GNU General Public License version 3, as published 
#by the Free Software Foundation.
#
#This program is distributed in the hope that it will be useful, but 
#WITHOUT ANY WARRANTY; without even the implied warranties of 
#MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR 
#PURPOSE.  See the GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License along 
#with this program.  If not, see <http://www.gnu.org/licenses/>.
### END LICENSE

import dbus
import dbus.service

class PithosMprisService(dbus.service.Object):
    MEDIA_PLAYER2_IFACE = 'org.mpris.MediaPlayer2'
    MEDIA_PLAYER2_PLAYER_IFACE = 'org.mpris.MediaPlayer2.Player'

    def __init__(self, window):
        """
        Creates a PithosSoundMenu object.

        Requires a dbus loop to be created before the gtk mainloop,
        typically by calling DBusGMainLoop(set_as_default=True).
        """

        bus_str = """org.mpris.MediaPlayer2.pithos"""
        bus_name = dbus.service.BusName(bus_str, bus=dbus.SessionBus())
        dbus.service.Object.__init__(self, bus_name, "/org/mpris/MediaPlayer2")
        self.window = window

        self.song_changed()
        
        self.window.connect("song-changed", self.songchange_handler)
        self.window.connect("play-state-changed", self.playstate_handler)
        
    def playstate_handler(self, window, state):
        if state:
            self.signal_playing()
        else:
            self.signal_paused()
        
    def songchange_handler(self, window, song):
        self.song_changed([song.artist], song.album, song.title, song.artRadio)
        self.signal_playing()

    def song_changed(self, artists = None, album = None, title = None, artUrl=''):
        """song_changed - sets the info for the current song.

        This method is not typically overriden. It should be called
        by implementations of this class when the player has changed
        songs.
            
        named arguments:
            artists - a list of strings representing the artists"
            album - a string for the name of the album
            title - a string for the title of the song

        """
        
        if artists is None:
            artists = ["Artist Unknown"]
        if album is None:
            album = "Album Unknown"
        if title is None:
            title = "Title Unknown"
        if artUrl is None:
            artUrl = ''
   
        self.__meta_data = dbus.Dictionary({"xesam:album":album,
                            "xesam:title":title,
                            "xesam:artist":artists,
                            "mpris:artUrl":artUrl,
                            }, "sv", variant_level=1)

    # Properties
    def _get_playback_status(self):
        """Current status "Playing", "Paused", or "Stopped"."""
        if not self.window.current_song:
            return "Stopped"
        if self.window.playing:
            return "Playing"
        else:
            return "Paused"

    def _get_metadata(self):
        """The info for the current song."""
        return self.__meta_data

    def _get_volume(self):
        return self.window.player.get_property("volume")

    def _get_position(self):
        return self.window.player.query_position(self.window.time_format, None)[0] / 1000

    @dbus.service.method(dbus.PROPERTIES_IFACE, in_signature='ss', out_signature='v')
    def Get(self, interface_name, property_name):
        try:
            return self.GetAll(interface_name)[property_name]
        except KeyError:
            raise dbus.exceptions.DBusException(
                interface_name, 'Property %s was not found.' %property_name)

    @dbus.service.method(dbus.PROPERTIES_IFACE, in_signature='ssv')
    def Set(self, interface_name, property_name, new_value):
        if interface_name == self.MEDIA_PLAYER2_IFACE:
            pass
        elif interface_name == self.MEDIA_PLAYER2_PLAYER_IFACE:
            pass # TODO: volume
        else:
            raise dbus.exceptions.DBusException(
                'org.mpris.MediaPlayer2.pithos',
                'This object does not implement the %s interface'
                % interface_name)

    @dbus.service.method(dbus.PROPERTIES_IFACE, in_signature='s', out_signature='a{sv}')
    def GetAll(self, interface_name):
        if interface_name == self.MEDIA_PLAYER2_IFACE:
            return {
                'CanQuit': True,
                'CanRaise': True,
                'HasTrackList': False,
                'Identity': 'Pithos',
                'DesktopEntry': 'pithos',
                'SupportedUriSchemes': [''],
                'SupportedMimeTypes': [''],
            }
        elif interface_name == self.MEDIA_PLAYER2_PLAYER_IFACE:
            return {
                'PlaybackStatus': self._get_playback_status(),
                'LoopStatus': "None",
                'Rate': dbus.Double(1.0),
                'Shuffle': False,
                'Metadata': dbus.Dictionary(self._get_metadata(), signature='sv'),
                'Volume': dbus.Double(self._get_volume()),
                'Position': dbus.Int64(self._get_position()),
                'MinimumRate': dbus.Double(1.0),
                'MaximumRate': dbus.Double(1.0),
                'CanGoNext': self.window.waiting_for_playlist is not True,
                'CanGoPrevious': False,
                'CanPlay': self.window.current_song is not None,
                'CanPause': self.window.current_song is not None,
                'CanSeek': False,
                'CanControl': True,
            }
        else:
            raise dbus.exceptions.DBusException(
                'org.mpris.MediaPlayer2.pithos',
                'This object does not implement the %s interface'
                % interface_name)

    @dbus.service.method(MEDIA_PLAYER2_IFACE)
    def Raise(self):
        """Bring the media player to the front when selected by the sound menu"""

        self.window.bring_to_top()

    @dbus.service.method(MEDIA_PLAYER2_IFACE)
    def Quit(self):
        """Exit the player"""

        self.window.quit()

    @dbus.service.method(MEDIA_PLAYER2_PLAYER_IFACE)
    def Previous(self):
        """Play prvious song, not implemented"""

        pass

    @dbus.service.method(MEDIA_PLAYER2_PLAYER_IFACE)
    def Next(self):
        """Play next song"""

        self.window.next_song()

    @dbus.service.method(MEDIA_PLAYER2_PLAYER_IFACE)
    def PlayPause(self):
        self.window.playpause()

    @dbus.service.method(MEDIA_PLAYER2_PLAYER_IFACE)
    def Play(self):
        self.window.play()

    @dbus.service.method(MEDIA_PLAYER2_PLAYER_IFACE)
    def Pause(self):
        self.window.pause()

    @dbus.service.method(MEDIA_PLAYER2_PLAYER_IFACE)
    def Stop(self):
        self.window.stop()

    def signal_playing(self):
        """signal_playing - Tell the Sound Menu that the player has
        started playing.
        """
       
        self.__playback_status = "Playing"
        d = dbus.Dictionary({"PlaybackStatus":self.__playback_status, "Metadata":self.__meta_data},
                                    "sv",variant_level=1)
        self.PropertiesChanged("org.mpris.MediaPlayer2.Player",d,[])

    def signal_paused(self):
        """signal_paused - Tell the Sound Menu that the player has
        been paused
        """

        self.__playback_status = "Paused"
        d = dbus.Dictionary({"PlaybackStatus":self.__playback_status},
                                    "sv",variant_level=1)
        self.PropertiesChanged("org.mpris.MediaPlayer2.Player",d,[])

    @dbus.service.signal(dbus.PROPERTIES_IFACE, signature='sa{sv}as')
    def PropertiesChanged(self, interface_name, changed_properties,
                          invalidated_properties):
        """PropertiesChanged

        A function necessary to implement dbus properties.

        Typically, this function is not overriden or called directly.

        """

        pass

########NEW FILE########
__FILENAME__ = blowfish
# Copyright (C) 2011 Versile AS
#
# This file is part of Versile Python Open Source Edition.
#
# Versile Python Open Source Edition is free software: you can
# redistribute it and/or modify it under the terms of the GNU Affero
# General Public License as published by the Free Software Foundation,
# either version 3 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see
# <http://www.gnu.org/licenses/>.
#
# Versile Python Open Source Edition implements Versile Platform which
# is a copyrighted specification that is not part of this software.
# Modification of the software is subject to Versile Platform licensing,
# see https://versile.com/ for details. Distribution of unmodified versions
# released by Versile AS is not subject to Versile Platform licensing.
#

"""Implementation of the Blowfish cipher.

This is an implementation of the `Blowfish
<http://www.schneier.com/blowfish.html>`__ cipher, which is in the
public domain. Stated on the web site:

    \"Everyone is welcome to download Blowfish and use it in their
    application. There are no rules about use, although I would
    appreciate being notified of any commercial applications using
    the product so that I can list them on this website.\"

The implementation in this module is a python conversion and
adaptation of Bruce Schneier's `C implementation
<http://www.schneier.com/blowfish-download.html>`__\ .

"""

import copy

class VCryptoException(Exception):
    """Exception for crypto operations."""
    def __init__(self, *args):
        super(VCryptoException, self).__init__(*args)

class Blowfish(object):
    """Blowfish cipher.

    When initialized the object can encrypt and decrypt blocks of
    data with the :meth:`encrypt` and :meth:`decrypt` methods.

    :param key: cipher key
    :type  key: bytes

    Key length must be between 1 byte and 56 bytes (448 bits).


    """
    def __init__(self, key):
        if not isinstance(key, bytes):
            raise VCryptoException('Key must be a bytes object')
        elif len(key) > 56:
            raise VCryptoException('Max key length is 448 bits (56 bytes)')

        P, S = copy.deepcopy(_P_INIT), copy.deepcopy(_S_INIT)
        self.__P, self.__S = P, S

        keylen = len(key)
        j = 0
        for i in range(len(P)):
            data = 0
            for k in range(4):
                data = ((data << 8) & 0xffffffff) | key[j]
                j += 1
                if j >= keylen:
                    j = 0
            P[i] ^= data

        data = 8*b'\x00'
        for i in range(0, len(P), 2):
            data = self.encrypt(data)
            P[i] = ((data[0] << 24) + (data[1] << 16) +
                    (data[2] << 8 ) + data[3])
            P[i+1] = ((data[4] << 24) + (data[5] << 16) +
                      (data[6] << 8 ) + data[7])

        for i in range(4):
            for j in range(0, 256, 2):
                data = self.encrypt(data)
                S[i][j] = ((data[0] << 24) + (data[1] << 16) +
                           (data[2] << 8 ) + data[3])
                S[i][j+1] = ((data[4] << 24) +
                             (data[5] << 16) +
                             (data[6] << 8 ) + data[7])

    def __feistel(self, x):
        S = self.__S
        d = x & 0xff
        x >>= 8
        c = x & 0xff
        x >>= 8
        b = x & 0xff
        x >>= 8
        a = x & 0xff
        y = (S[0][a] + S[1][b]) & 0xffffffff
        y ^= S[2][c]
        y = (y + S[3][d]) & 0xffffffff
        return y

    def encrypt(self, data):
        """Encipher plaintext and return result.

        :param data:  plaintext to encrypt (8 bytes)
        :type  data:  bytes
        :returns:     encrypted data (8 bytes)
        :rtype:       bytes

        The data must align with 8-byte blocksize.

        .. note::

            Enciphering is performed without any kind of chaining, and
            the same plaintext will always return the same encrypted
            block of data. In order to use securely as a cipher, it is
            normally required that the cipher is combined with
            chaining techniques.

        """
        len_data = len(data)
        if len_data % 8:
            raise VCryptoException('Data not aligned with 8-byte blocksize')
        if len_data == 8:
            return self._encrypt_block(data)
        else:
            result = []
            start = 0
            while start < len_data:
                end = start + 8
                block = data[start:end]
                result.append(self._encrypt_block(block))
                start += 8
            return b''.join(result)

    def _encrypt_block(self, block):
        if not isinstance(block, bytes) or len(block) != 8:
            raise VCryptoException('Data block must be bytes of len 8')
        b_l = ((block[0] << 24) + (block[1] << 16) +
               (block[2] << 8 ) + block[3])
        b_r = ((block[4] << 24) + (block[5] << 16) +
               (block[6] << 8 ) + block[7])
        P, S = self.__P, self.__S

        for i in range(16):
            b_l ^= P[i]
            b_r ^= self.__feistel(b_l)
            b_l, b_r = b_r, b_l
        b_l, b_r = b_r, b_l
        b_r ^= P[16]
        b_l ^= P[17]

        bval = [(b_l >> 24), (b_l >> 16), (b_l >> 8), b_l,
                (b_r >> 24), (b_r >> 16), (b_r >> 8), b_r]

        return bytes([b & 0xff for b in bval])

    def decrypt(self, data):
        """Decipher encrypted data and return decrypted plaintext.

        :param data:  encrypted data (8 bytes)
        :type  data:  bytes
        :returns:     decrypted plaintext (8 bytes)
        :rtype:       bytes

        The block of encrypted data must be a multiple of 8 bytes.

        """
        len_data = len(data)
        if len_data % 8:
            raise VCryptoException('Data not aligned with 8-byte blocksize')
        if len_data == 8:
            return self._decrypt_block(data)
        else:
            result = []
            start = 0
            while start < len_data:
                end = start + 8
                block = data[start:end]
                result.append(self._decrypt_block(block))
                start += 8
            return b''.join(result)

    def _decrypt_block(self, block):
        if not isinstance(block, bytes) or len(block) != 8:
            raise VCryptoException('Data block must be bytes of len 8')
        b_l = ((block[0] << 24) + (block[1] << 16) +
               (block[2] << 8 ) + block[3])
        b_r = ((block[4] << 24) + (block[5] << 16) +
               (block[6] << 8 ) + block[7])
        P, S = self.__P, self.__S

        for i in range(17, 1, -1):
            b_l ^= P[i]
            b_r ^= self.__feistel(b_l)
            b_l, b_r = b_r, b_l
        b_l, b_r = b_r, b_l
        b_r ^= P[1]
        b_l ^= P[0]

        bval = [(b_l >> 24), (b_l >> 16), (b_l >> 8), b_l,
                (b_r >> 24), (b_r >> 16), (b_r >> 8), b_r]

        return bytes([b & 0xff for b in bval])

# These are the standard initialization valies of P and S blocks for the
# cipher. The constants are internal to this module and should not be accessed
# directly or modified by outside code.

_P_INIT = [0x243f6a88,0x85a308d3,0x13198a2e,0x03707344,0xa4093822,0x299f31d0,
           0x082efa98,0xec4e6c89,0x452821e6,0x38d01377,0xbe5466cf,0x34e90c6c,
           0xc0ac29b7,0xc97c50dd,0x3f84d5b5,0xb5470917,0x9216d5d9,0x8979fb1b]

_S_INIT = [[0xd1310ba6,0x98dfb5ac,0x2ffd72db,0xd01adfb7,0xb8e1afed,0x6a267e96,
            0xba7c9045,0xf12c7f99,0x24a19947,0xb3916cf7,0x0801f2e2,0x858efc16,
            0x636920d8,0x71574e69,0xa458fea3,0xf4933d7e,0x0d95748f,0x728eb658,
            0x718bcd58,0x82154aee,0x7b54a41d,0xc25a59b5,0x9c30d539,0x2af26013,
            0xc5d1b023,0x286085f0,0xca417918,0xb8db38ef,0x8e79dcb0,0x603a180e,
            0x6c9e0e8b,0xb01e8a3e,0xd71577c1,0xbd314b27,0x78af2fda,0x55605c60,
            0xe65525f3,0xaa55ab94,0x57489862,0x63e81440,0x55ca396a,0x2aab10b6,
            0xb4cc5c34,0x1141e8ce,0xa15486af,0x7c72e993,0xb3ee1411,0x636fbc2a,
            0x2ba9c55d,0x741831f6,0xce5c3e16,0x9b87931e,0xafd6ba33,0x6c24cf5c,
            0x7a325381,0x28958677,0x3b8f4898,0x6b4bb9af,0xc4bfe81b,0x66282193,
            0x61d809cc,0xfb21a991,0x487cac60,0x5dec8032,0xef845d5d,0xe98575b1,
            0xdc262302,0xeb651b88,0x23893e81,0xd396acc5,0x0f6d6ff3,0x83f44239,
            0x2e0b4482,0xa4842004,0x69c8f04a,0x9e1f9b5e,0x21c66842,0xf6e96c9a,
            0x670c9c61,0xabd388f0,0x6a51a0d2,0xd8542f68,0x960fa728,0xab5133a3,
            0x6eef0b6c,0x137a3be4,0xba3bf050,0x7efb2a98,0xa1f1651d,0x39af0176,
            0x66ca593e,0x82430e88,0x8cee8619,0x456f9fb4,0x7d84a5c3,0x3b8b5ebe,
            0xe06f75d8,0x85c12073,0x401a449f,0x56c16aa6,0x4ed3aa62,0x363f7706,
            0x1bfedf72,0x429b023d,0x37d0d724,0xd00a1248,0xdb0fead3,0x49f1c09b,
            0x075372c9,0x80991b7b,0x25d479d8,0xf6e8def7,0xe3fe501a,0xb6794c3b,
            0x976ce0bd,0x04c006ba,0xc1a94fb6,0x409f60c4,0x5e5c9ec2,0x196a2463,
            0x68fb6faf,0x3e6c53b5,0x1339b2eb,0x3b52ec6f,0x6dfc511f,0x9b30952c,
            0xcc814544,0xaf5ebd09,0xbee3d004,0xde334afd,0x660f2807,0x192e4bb3,
            0xc0cba857,0x45c8740f,0xd20b5f39,0xb9d3fbdb,0x5579c0bd,0x1a60320a,
            0xd6a100c6,0x402c7279,0x679f25fe,0xfb1fa3cc,0x8ea5e9f8,0xdb3222f8,
            0x3c7516df,0xfd616b15,0x2f501ec8,0xad0552ab,0x323db5fa,0xfd238760,
            0x53317b48,0x3e00df82,0x9e5c57bb,0xca6f8ca0,0x1a87562e,0xdf1769db,
            0xd542a8f6,0x287effc3,0xac6732c6,0x8c4f5573,0x695b27b0,0xbbca58c8,
            0xe1ffa35d,0xb8f011a0,0x10fa3d98,0xfd2183b8,0x4afcb56c,0x2dd1d35b,
            0x9a53e479,0xb6f84565,0xd28e49bc,0x4bfb9790,0xe1ddf2da,0xa4cb7e33,
            0x62fb1341,0xcee4c6e8,0xef20cada,0x36774c01,0xd07e9efe,0x2bf11fb4,
            0x95dbda4d,0xae909198,0xeaad8e71,0x6b93d5a0,0xd08ed1d0,0xafc725e0,
            0x8e3c5b2f,0x8e7594b7,0x8ff6e2fb,0xf2122b64,0x8888b812,0x900df01c,
            0x4fad5ea0,0x688fc31c,0xd1cff191,0xb3a8c1ad,0x2f2f2218,0xbe0e1777,
            0xea752dfe,0x8b021fa1,0xe5a0cc0f,0xb56f74e8,0x18acf3d6,0xce89e299,
            0xb4a84fe0,0xfd13e0b7,0x7cc43b81,0xd2ada8d9,0x165fa266,0x80957705,
            0x93cc7314,0x211a1477,0xe6ad2065,0x77b5fa86,0xc75442f5,0xfb9d35cf,
            0xebcdaf0c,0x7b3e89a0,0xd6411bd3,0xae1e7e49,0x00250e2d,0x2071b35e,
            0x226800bb,0x57b8e0af,0x2464369b,0xf009b91e,0x5563911d,0x59dfa6aa,
            0x78c14389,0xd95a537f,0x207d5ba2,0x02e5b9c5,0x83260376,0x6295cfa9,
            0x11c81968,0x4e734a41,0xb3472dca,0x7b14a94a,0x1b510052,0x9a532915,
            0xd60f573f,0xbc9bc6e4,0x2b60a476,0x81e67400,0x08ba6fb5,0x571be91f,
            0xf296ec6b,0x2a0dd915,0xb6636521,0xe7b9f9b6,0xff34052e,0xc5855664,
            0x53b02d5d,0xa99f8fa1,0x08ba4799,0x6e85076a],
           [0x4b7a70e9,0xb5b32944,0xdb75092e,0xc4192623,0xad6ea6b0,0x49a7df7d,
            0x9cee60b8,0x8fedb266,0xecaa8c71,0x699a17ff,0x5664526c,0xc2b19ee1,
            0x193602a5,0x75094c29,0xa0591340,0xe4183a3e,0x3f54989a,0x5b429d65,
            0x6b8fe4d6,0x99f73fd6,0xa1d29c07,0xefe830f5,0x4d2d38e6,0xf0255dc1,
            0x4cdd2086,0x8470eb26,0x6382e9c6,0x021ecc5e,0x09686b3f,0x3ebaefc9,
            0x3c971814,0x6b6a70a1,0x687f3584,0x52a0e286,0xb79c5305,0xaa500737,
            0x3e07841c,0x7fdeae5c,0x8e7d44ec,0x5716f2b8,0xb03ada37,0xf0500c0d,
            0xf01c1f04,0x0200b3ff,0xae0cf51a,0x3cb574b2,0x25837a58,0xdc0921bd,
            0xd19113f9,0x7ca92ff6,0x94324773,0x22f54701,0x3ae5e581,0x37c2dadc,
            0xc8b57634,0x9af3dda7,0xa9446146,0x0fd0030e,0xecc8c73e,0xa4751e41,
            0xe238cd99,0x3bea0e2f,0x3280bba1,0x183eb331,0x4e548b38,0x4f6db908,
            0x6f420d03,0xf60a04bf,0x2cb81290,0x24977c79,0x5679b072,0xbcaf89af,
            0xde9a771f,0xd9930810,0xb38bae12,0xdccf3f2e,0x5512721f,0x2e6b7124,
            0x501adde6,0x9f84cd87,0x7a584718,0x7408da17,0xbc9f9abc,0xe94b7d8c,
            0xec7aec3a,0xdb851dfa,0x63094366,0xc464c3d2,0xef1c1847,0x3215d908,
            0xdd433b37,0x24c2ba16,0x12a14d43,0x2a65c451,0x50940002,0x133ae4dd,
            0x71dff89e,0x10314e55,0x81ac77d6,0x5f11199b,0x043556f1,0xd7a3c76b,
            0x3c11183b,0x5924a509,0xf28fe6ed,0x97f1fbfa,0x9ebabf2c,0x1e153c6e,
            0x86e34570,0xeae96fb1,0x860e5e0a,0x5a3e2ab3,0x771fe71c,0x4e3d06fa,
            0x2965dcb9,0x99e71d0f,0x803e89d6,0x5266c825,0x2e4cc978,0x9c10b36a,
            0xc6150eba,0x94e2ea78,0xa5fc3c53,0x1e0a2df4,0xf2f74ea7,0x361d2b3d,
            0x1939260f,0x19c27960,0x5223a708,0xf71312b6,0xebadfe6e,0xeac31f66,
            0xe3bc4595,0xa67bc883,0xb17f37d1,0x018cff28,0xc332ddef,0xbe6c5aa5,
            0x65582185,0x68ab9802,0xeecea50f,0xdb2f953b,0x2aef7dad,0x5b6e2f84,
            0x1521b628,0x29076170,0xecdd4775,0x619f1510,0x13cca830,0xeb61bd96,
            0x0334fe1e,0xaa0363cf,0xb5735c90,0x4c70a239,0xd59e9e0b,0xcbaade14,
            0xeecc86bc,0x60622ca7,0x9cab5cab,0xb2f3846e,0x648b1eaf,0x19bdf0ca,
            0xa02369b9,0x655abb50,0x40685a32,0x3c2ab4b3,0x319ee9d5,0xc021b8f7,
            0x9b540b19,0x875fa099,0x95f7997e,0x623d7da8,0xf837889a,0x97e32d77,
            0x11ed935f,0x16681281,0x0e358829,0xc7e61fd6,0x96dedfa1,0x7858ba99,
            0x57f584a5,0x1b227263,0x9b83c3ff,0x1ac24696,0xcdb30aeb,0x532e3054,
            0x8fd948e4,0x6dbc3128,0x58ebf2ef,0x34c6ffea,0xfe28ed61,0xee7c3c73,
            0x5d4a14d9,0xe864b7e3,0x42105d14,0x203e13e0,0x45eee2b6,0xa3aaabea,
            0xdb6c4f15,0xfacb4fd0,0xc742f442,0xef6abbb5,0x654f3b1d,0x41cd2105,
            0xd81e799e,0x86854dc7,0xe44b476a,0x3d816250,0xcf62a1f2,0x5b8d2646,
            0xfc8883a0,0xc1c7b6a3,0x7f1524c3,0x69cb7492,0x47848a0b,0x5692b285,
            0x095bbf00,0xad19489d,0x1462b174,0x23820e00,0x58428d2a,0x0c55f5ea,
            0x1dadf43e,0x233f7061,0x3372f092,0x8d937e41,0xd65fecf1,0x6c223bdb,
            0x7cde3759,0xcbee7460,0x4085f2a7,0xce77326e,0xa6078084,0x19f8509e,
            0xe8efd855,0x61d99735,0xa969a7aa,0xc50c06c2,0x5a04abfc,0x800bcadc,
            0x9e447a2e,0xc3453484,0xfdd56705,0x0e1e9ec9,0xdb73dbd3,0x105588cd,
            0x675fda79,0xe3674340,0xc5c43465,0x713e38d8,0x3d28f89e,0xf16dff20,
            0x153e21e7,0x8fb03d4a,0xe6e39f2b,0xdb83adf7],
           [0xe93d5a68,0x948140f7,0xf64c261c,0x94692934,0x411520f7,0x7602d4f7,
            0xbcf46b2e,0xd4a20068,0xd4082471,0x3320f46a,0x43b7d4b7,0x500061af,
            0x1e39f62e,0x97244546,0x14214f74,0xbf8b8840,0x4d95fc1d,0x96b591af,
            0x70f4ddd3,0x66a02f45,0xbfbc09ec,0x03bd9785,0x7fac6dd0,0x31cb8504,
            0x96eb27b3,0x55fd3941,0xda2547e6,0xabca0a9a,0x28507825,0x530429f4,
            0x0a2c86da,0xe9b66dfb,0x68dc1462,0xd7486900,0x680ec0a4,0x27a18dee,
            0x4f3ffea2,0xe887ad8c,0xb58ce006,0x7af4d6b6,0xaace1e7c,0xd3375fec,
            0xce78a399,0x406b2a42,0x20fe9e35,0xd9f385b9,0xee39d7ab,0x3b124e8b,
            0x1dc9faf7,0x4b6d1856,0x26a36631,0xeae397b2,0x3a6efa74,0xdd5b4332,
            0x6841e7f7,0xca7820fb,0xfb0af54e,0xd8feb397,0x454056ac,0xba489527,
            0x55533a3a,0x20838d87,0xfe6ba9b7,0xd096954b,0x55a867bc,0xa1159a58,
            0xcca92963,0x99e1db33,0xa62a4a56,0x3f3125f9,0x5ef47e1c,0x9029317c,
            0xfdf8e802,0x04272f70,0x80bb155c,0x05282ce3,0x95c11548,0xe4c66d22,
            0x48c1133f,0xc70f86dc,0x07f9c9ee,0x41041f0f,0x404779a4,0x5d886e17,
            0x325f51eb,0xd59bc0d1,0xf2bcc18f,0x41113564,0x257b7834,0x602a9c60,
            0xdff8e8a3,0x1f636c1b,0x0e12b4c2,0x02e1329e,0xaf664fd1,0xcad18115,
            0x6b2395e0,0x333e92e1,0x3b240b62,0xeebeb922,0x85b2a20e,0xe6ba0d99,
            0xde720c8c,0x2da2f728,0xd0127845,0x95b794fd,0x647d0862,0xe7ccf5f0,
            0x5449a36f,0x877d48fa,0xc39dfd27,0xf33e8d1e,0x0a476341,0x992eff74,
            0x3a6f6eab,0xf4f8fd37,0xa812dc60,0xa1ebddf8,0x991be14c,0xdb6e6b0d,
            0xc67b5510,0x6d672c37,0x2765d43b,0xdcd0e804,0xf1290dc7,0xcc00ffa3,
            0xb5390f92,0x690fed0b,0x667b9ffb,0xcedb7d9c,0xa091cf0b,0xd9155ea3,
            0xbb132f88,0x515bad24,0x7b9479bf,0x763bd6eb,0x37392eb3,0xcc115979,
            0x8026e297,0xf42e312d,0x6842ada7,0xc66a2b3b,0x12754ccc,0x782ef11c,
            0x6a124237,0xb79251e7,0x06a1bbe6,0x4bfb6350,0x1a6b1018,0x11caedfa,
            0x3d25bdd8,0xe2e1c3c9,0x44421659,0x0a121386,0xd90cec6e,0xd5abea2a,
            0x64af674e,0xda86a85f,0xbebfe988,0x64e4c3fe,0x9dbc8057,0xf0f7c086,
            0x60787bf8,0x6003604d,0xd1fd8346,0xf6381fb0,0x7745ae04,0xd736fccc,
            0x83426b33,0xf01eab71,0xb0804187,0x3c005e5f,0x77a057be,0xbde8ae24,
            0x55464299,0xbf582e61,0x4e58f48f,0xf2ddfda2,0xf474ef38,0x8789bdc2,
            0x5366f9c3,0xc8b38e74,0xb475f255,0x46fcd9b9,0x7aeb2661,0x8b1ddf84,
            0x846a0e79,0x915f95e2,0x466e598e,0x20b45770,0x8cd55591,0xc902de4c,
            0xb90bace1,0xbb8205d0,0x11a86248,0x7574a99e,0xb77f19b6,0xe0a9dc09,
            0x662d09a1,0xc4324633,0xe85a1f02,0x09f0be8c,0x4a99a025,0x1d6efe10,
            0x1ab93d1d,0x0ba5a4df,0xa186f20f,0x2868f169,0xdcb7da83,0x573906fe,
            0xa1e2ce9b,0x4fcd7f52,0x50115e01,0xa70683fa,0xa002b5c4,0x0de6d027,
            0x9af88c27,0x773f8641,0xc3604c06,0x61a806b5,0xf0177a28,0xc0f586e0,
            0x006058aa,0x30dc7d62,0x11e69ed7,0x2338ea63,0x53c2dd94,0xc2c21634,
            0xbbcbee56,0x90bcb6de,0xebfc7da1,0xce591d76,0x6f05e409,0x4b7c0188,
            0x39720a3d,0x7c927c24,0x86e3725f,0x724d9db9,0x1ac15bb4,0xd39eb8fc,
            0xed545578,0x08fca5b5,0xd83d7cd3,0x4dad0fc4,0x1e50ef5e,0xb161e6f8,
            0xa28514d9,0x6c51133c,0x6fd5c7e7,0x56e14ec4,0x362abfce,0xddc6c837,
            0xd79a3234,0x92638212,0x670efa8e,0x406000e0],
           [0x3a39ce37,0xd3faf5cf,0xabc27737,0x5ac52d1b,0x5cb0679e,0x4fa33742,
            0xd3822740,0x99bc9bbe,0xd5118e9d,0xbf0f7315,0xd62d1c7e,0xc700c47b,
            0xb78c1b6b,0x21a19045,0xb26eb1be,0x6a366eb4,0x5748ab2f,0xbc946e79,
            0xc6a376d2,0x6549c2c8,0x530ff8ee,0x468dde7d,0xd5730a1d,0x4cd04dc6,
            0x2939bbdb,0xa9ba4650,0xac9526e8,0xbe5ee304,0xa1fad5f0,0x6a2d519a,
            0x63ef8ce2,0x9a86ee22,0xc089c2b8,0x43242ef6,0xa51e03aa,0x9cf2d0a4,
            0x83c061ba,0x9be96a4d,0x8fe51550,0xba645bd6,0x2826a2f9,0xa73a3ae1,
            0x4ba99586,0xef5562e9,0xc72fefd3,0xf752f7da,0x3f046f69,0x77fa0a59,
            0x80e4a915,0x87b08601,0x9b09e6ad,0x3b3ee593,0xe990fd5a,0x9e34d797,
            0x2cf0b7d9,0x022b8b51,0x96d5ac3a,0x017da67d,0xd1cf3ed6,0x7c7d2d28,
            0x1f9f25cf,0xadf2b89b,0x5ad6b472,0x5a88f54c,0xe029ac71,0xe019a5e6,
            0x47b0acfd,0xed93fa9b,0xe8d3c48d,0x283b57cc,0xf8d56629,0x79132e28,
            0x785f0191,0xed756055,0xf7960e44,0xe3d35e8c,0x15056dd4,0x88f46dba,
            0x03a16125,0x0564f0bd,0xc3eb9e15,0x3c9057a2,0x97271aec,0xa93a072a,
            0x1b3f6d9b,0x1e6321f5,0xf59c66fb,0x26dcf319,0x7533d928,0xb155fdf5,
            0x03563482,0x8aba3cbb,0x28517711,0xc20ad9f8,0xabcc5167,0xccad925f,
            0x4de81751,0x3830dc8e,0x379d5862,0x9320f991,0xea7a90c2,0xfb3e7bce,
            0x5121ce64,0x774fbe32,0xa8b6e37e,0xc3293d46,0x48de5369,0x6413e680,
            0xa2ae0810,0xdd6db224,0x69852dfd,0x09072166,0xb39a460a,0x6445c0dd,
            0x586cdecf,0x1c20c8ae,0x5bbef7dd,0x1b588d40,0xccd2017f,0x6bb4e3bb,
            0xdda26a7e,0x3a59ff45,0x3e350a44,0xbcb4cdd5,0x72eacea8,0xfa6484bb,
            0x8d6612ae,0xbf3c6f47,0xd29be463,0x542f5d9e,0xaec2771b,0xf64e6370,
            0x740e0d8d,0xe75b1357,0xf8721671,0xaf537d5d,0x4040cb08,0x4eb4e2cc,
            0x34d2466a,0x0115af84,0xe1b00428,0x95983a1d,0x06b89fb4,0xce6ea048,
            0x6f3f3b82,0x3520ab82,0x011a1d4b,0x277227f8,0x611560b1,0xe7933fdc,
            0xbb3a792b,0x344525bd,0xa08839e1,0x51ce794b,0x2f32c9b7,0xa01fbac9,
            0xe01cc87e,0xbcc7d1f6,0xcf0111c3,0xa1e8aac7,0x1a908749,0xd44fbd9a,
            0xd0dadecb,0xd50ada38,0x0339c32a,0xc6913667,0x8df9317c,0xe0b12b4f,
            0xf79e59b7,0x43f5bb3a,0xf2d519ff,0x27d9459c,0xbf97222c,0x15e6fc2a,
            0x0f91fc71,0x9b941525,0xfae59361,0xceb69ceb,0xc2a86459,0x12baa8d1,
            0xb6c1075e,0xe3056a0c,0x10d25065,0xcb03a442,0xe0ec6e0e,0x1698db3b,
            0x4c98a0be,0x3278e964,0x9f1f9532,0xe0d392df,0xd3a0342b,0x8971f21e,
            0x1b0a7441,0x4ba3348c,0xc5be7120,0xc37632d8,0xdf359f8d,0x9b992f2e,
            0xe60b6f47,0x0fe3f11d,0xe54cda54,0x1edad891,0xce6279cf,0xcd3e7e6f,
            0x1618b166,0xfd2c1d05,0x848fd2c5,0xf6fb2299,0xf523f357,0xa6327623,
            0x93a83531,0x56cccd02,0xacf08162,0x5a75ebb5,0x6e163697,0x88d273cc,
            0xde966292,0x81b949d0,0x4c50901b,0x71c65614,0xe6c6c7bd,0x327a140a,
            0x45e1d006,0xc3f27b9a,0xc9aa53fd,0x62a80f00,0xbb25bfe2,0x35bdd2f6,
            0x71126905,0xb2040222,0xb6cbcf7c,0xcd769c2b,0x53113ec0,0x1640e3d3,
            0x38abbd60,0x2547adf0,0xba38209c,0xf746ce76,0x77afa1c5,0x20756060,
            0x85cbfe4e,0x8ae88dd8,0x7aaaf9b0,0x4cf9aa7e,0x1948c25c,0x02fb8a8c,
            0x01c36ae4,0xd6ebe1f9,0x90d4f869,0xa65cdea0,0x3f09252d,0xc208e69f,
            0xb74e6132,0xce77e25b,0x578fdfe3,0x3ac372e6]
           ]
########NEW FILE########
__FILENAME__ = data
client_keys = {
    'android-generic':{
        'deviceModel': 'android-generic',
        'username': 'android',
        'password': 'AC7IBG09A3DTSYM4R41UJWL07VLN8JI7',
        'rpcUrl': '://tuner.pandora.com/services/json/?',
        'encryptKey': '6#26FRL$ZWD',
        'decryptKey': 'R=U!LH$O2B#',
        'version' : '5',
    },
    'pandora-one':{
        'deviceModel': 'D01',
        'username': 'pandora one',
        'password': 'TVCKIBGS9AO9TSYLNNFUML0743LH82D',
        'rpcUrl': '://internal-tuner.pandora.com/services/json/?',
        'encryptKey': '2%3WCL*JU$MP]4',
        'decryptKey': 'U#IO$RZPAB%VX2',
        'version' : '5',
    }
}
default_client_id = "android-generic"
default_one_client_id = "pandora-one"

# See http://pan-do-ra-api.wikia.com/wiki/Json/5/station.getPlaylist
valid_audio_formats = [
    ('highQuality', 'High'),
    ('mediumQuality', 'Medium'),
    ('lowQuality', 'Low'),
]
default_audio_quality = 'mediumQuality'

########NEW FILE########
__FILENAME__ = fake
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: nil; -*-
### BEGIN LICENSE
# Copyright (C) 2010 Kevin Mehall <km@kevinmehall.net>
#This program is free software: you can redistribute it and/or modify it 
#under the terms of the GNU General Public License version 3, as published 
#by the Free Software Foundation.
#
#This program is distributed in the hope that it will be useful, but 
#WITHOUT ANY WARRANTY; without even the implied warranties of 
#MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR 
#PURPOSE.  See the GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License along 
#with this program.  If not, see <http://www.gnu.org/licenses/>.
### END LICENSE

from pithos.pandora.pandora import *
from gi.repository import Gtk
import logging

TEST_FILE = "http://pithos.github.io/testfile.aac"

class FakePandora(Pandora):
    def __init__(self):
        super(FakePandora, self).__init__()
        self.counter = 0
        self.show_fail_window()
        logging.info("Using test mode")
    
    def count(self):
        self.counter +=1
        return self.counter
        
    def show_fail_window(self):
        self.window = Gtk.Window()
        self.window.set_size_request(200, 100)
        self.window.set_title("Pithos failure tester")
        self.window.set_opacity(0.7)
        self.auth_check = Gtk.CheckButton.new_with_label("Authenticated")
        self.time_check = Gtk.CheckButton.new_with_label("Be really slow")
        vbox = Gtk.VBox()
        self.window.add(vbox)
        vbox.pack_start(self.auth_check, True, True, 0)
        vbox.pack_start(self.time_check, True, True, 0)
        self.window.show_all()

    def maybe_fail(self):
        if self.time_check.get_active():
            logging.info("fake: Going to sleep for 10s")
            time.sleep(10)
        if not self.auth_check.get_active():
            logging.info("fake: We're deauthenticated...")
            raise PandoraAuthTokenInvalid("Auth token invalid", "AUTH_INVALID_TOKEN")

    def set_authenticated(self):
        self.auth_check.set_active(True)

    def json_call(self, method, args={}, https=False, blowfish=True):
        time.sleep(1)
        self.maybe_fail()

        if method == 'user.getStationList':
            return {'stations': [
                {'stationId':'987', 'stationToken':'345434', 'isShared':False, 'isQuickMix':False, 'stationName':"Test Station 1"},
                {'stationId':'321', 'stationToken':'453544', 'isShared':False, 'isQuickMix':True, 'stationName':"Fake's QuickMix",
                    'quickMixStationIds':['987', '343']},
                {'stationId':'432', 'stationToken':'345485', 'isShared':False, 'isQuickMix':False, 'stationName':"Test Station 2"},
                {'stationId':'254', 'stationToken':'345415', 'isShared':False, 'isQuickMix':False, 'stationName':"Test Station 4 - Out of Order"},
                {'stationId':'343', 'stationToken':'345435', 'isShared':False, 'isQuickMix':False, 'stationName':"Test Station 3"},
            ]}
        elif method == 'station.getPlaylist':
            stationId = self.get_station_by_token(args['stationToken']).id
            return {'items': [self.makeFakeSong(stationId) for i in range(4)]}
        elif method == 'music.search':
            return {'artists': [
                        {'score':90, 'musicToken':'988', 'artistName':"artistName"},
                    ],
                    'songs':[
                        {'score':80, 'musicToken':'238', 'songName':"SongName", 'artistName':"ArtistName"},
                    ],
                   }
        elif method == 'station.createStation':
            return {'stationId':'999', 'stationToken':'345433', 'isShared':False, 'isQuickMix':False, 'stationName':"Added Station"}
        elif method == 'station.addFeedback':
            return {'feedbackId': '1234'}
        elif method in ('user.setQuickMix',
                        'station.deleteFeedback',
                        'station.transformSharedStation',
                        'station.renameStation',
                        'station.deleteStation',
                        'user.sleepSong',
                        'bookmark.addSongBookmark',
                        'bookmark.addArtistBookmark',
                     ):
            return 1
        else:
            logging.error("Invalid method %s" % method)

    def connect(self, client, user, password):
        self.set_authenticated()
        self.get_stations()

    def get_station_by_token(self, token):
        for i in self.stations:
            if i.idToken == token:
                return i

    def makeFakeSong(self, stationId):
        c = self.count()
        audio_url = TEST_FILE + '?val='+'0'*48
        return {
            'albumName':"AlbumName",
            'artistName':"ArtistName",
            'audioUrlMap': {
                'highQuality': {
                    'audioUrl': audio_url
                },
                'mediumQuality': {
                    'audioUrl': audio_url
                },
                'lowQuality': {
                    'audioUrl': audio_url
                },
            },
            'trackGain':0,
            'trackToken':'5908540384',
            'songRating': 1 if c%3 == 0 else 0,
            'stationId': stationId,
            'songName': 'Test song %i'%c,
            'songDetailUrl': 'http://pithos.github.io/',
            'albumDetailUrl':'http://pithos.github.io/',
            'albumArtUrl':'http://pithos.github.io/img/pithos_logo.png',
            'songExplorerUrl':'http://pithos.github.io/test-song.xml',
        }


########NEW FILE########
__FILENAME__ = pandora
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: nil; -*-
### BEGIN LICENSE
# Copyright (C) 2010 Kevin Mehall <km@kevinmehall.net>
# Copyright (C) 2012 Christopher Eby <kreed@kreed.org>
#This program is free software: you can redistribute it and/or modify it
#under the terms of the GNU General Public License version 3, as published
#by the Free Software Foundation.
#
#This program is distributed in the hope that it will be useful, but
#WITHOUT ANY WARRANTY; without even the implied warranties of
#MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR
#PURPOSE.  See the GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License along
#with this program.  If not, see <http://www.gnu.org/licenses/>.
### END LICENSE

from .blowfish import Blowfish
# from Crypto.Cipher import Blowfish
from xml.dom import minidom
import re
import json
import logging
import time
import urllib.request, urllib.parse, urllib.error
import codecs

# This is an implementation of the Pandora JSON API using Android partner
# credentials.
# See http://pan-do-ra-api.wikia.com/wiki/Json/5 for API documentation.

HTTP_TIMEOUT = 30
USER_AGENT = 'pithos'

RATE_BAN = 'ban'
RATE_LOVE = 'love'
RATE_NONE = None

API_ERROR_API_VERSION_NOT_SUPPORTED = 11
API_ERROR_COUNTRY_NOT_SUPPORTED = 12
API_ERROR_INSUFFICIENT_CONNECTIVITY = 13
API_ERROR_READ_ONLY_MODE = 1000
API_ERROR_INVALID_AUTH_TOKEN = 1001
API_ERROR_INVALID_LOGIN = 1002
API_ERROR_LISTENER_NOT_AUTHORIZED = 1003
API_ERROR_PARTNER_NOT_AUTHORIZED = 1010
API_ERROR_PLAYLIST_EXCEEDED = 1039

PLAYLIST_VALIDITY_TIME = 60*60*3

NAME_COMPARE_REGEX = re.compile(r'[^A-Za-z0-9]')

class PandoraError(IOError):
    def __init__(self, message, status=None, submsg=None):
        self.status = status
        self.message = message
        self.submsg = submsg

class PandoraAuthTokenInvalid(PandoraError): pass
class PandoraNetError(PandoraError): pass
class PandoraAPIVersionError(PandoraError): pass
class PandoraTimeout(PandoraNetError): pass

def pad(s, l):
    return s + b'\0' * (l - len(s))

class Pandora(object):
    def __init__(self):
        self.opener = urllib.request.build_opener()
        pass

    def pandora_encrypt(self, s):
        return b''.join([codecs.encode(self.blowfish_encode.encrypt(pad(s[i:i+8], 8)), 'hex_codec') for i in range(0, len(s), 8)])

    def pandora_decrypt(self, s):
        return b''.join([self.blowfish_decode.decrypt(pad(codecs.decode(s[i:i+16], 'hex_codec'), 8)) for i in range(0, len(s), 16)]).rstrip(b'\x08')

    def json_call(self, method, args={}, https=False, blowfish=True):
        url_arg_strings = []
        if self.partnerId:
            url_arg_strings.append('partner_id=%s'%self.partnerId)
        if self.userId:
            url_arg_strings.append('user_id=%s'%self.userId)
        if self.userAuthToken:
            url_arg_strings.append('auth_token=%s'%urllib.parse.quote_plus(self.userAuthToken))
        elif self.partnerAuthToken:
            url_arg_strings.append('auth_token=%s'%urllib.parse.quote_plus(self.partnerAuthToken))

        url_arg_strings.append('method=%s'%method)
        protocol = 'https' if https else 'http'
        url = protocol + self.rpcUrl + '&'.join(url_arg_strings)

        if self.time_offset:
            args['syncTime'] = int(time.time()+self.time_offset)
        if self.userAuthToken:
            args['userAuthToken'] = self.userAuthToken
        elif self.partnerAuthToken:
            args['partnerAuthToken'] = self.partnerAuthToken
        data = json.dumps(args).encode('utf-8')

        logging.debug(url)
        logging.debug(data)

        if blowfish:
            data = self.pandora_encrypt(data)

        try:
            req = urllib.request.Request(url, data, {'User-agent': USER_AGENT, 'Content-type': 'text/plain'})
            response = self.opener.open(req, timeout=HTTP_TIMEOUT)
            text = response.read().decode('utf-8')
        except urllib.error.HTTPError as e:
            logging.error("HTTP error: %s", e)
            raise PandoraNetError(str(e))
        except urllib.error.URLError as e:
            logging.error("Network error: %s", e)
            if e.reason.strerror == 'timed out':
                raise PandoraTimeout("Network error", submsg="Timeout")
            else:
                raise PandoraNetError("Network error", submsg=e.reason.strerror)

        logging.debug(text)

        tree = json.loads(text)

        if tree['stat'] == 'fail':
            code = tree['code']
            msg = tree['message']
            logging.error('fault code: ' + str(code) + ' message: ' + msg)

            if code == API_ERROR_INVALID_AUTH_TOKEN:
                raise PandoraAuthTokenInvalid(msg)
            elif code == API_ERROR_COUNTRY_NOT_SUPPORTED:
                 raise PandoraError("Pandora not available", code,
                    submsg="Pandora is not available outside the United States.")
            elif code == API_ERROR_API_VERSION_NOT_SUPPORTED:
                raise PandoraAPIVersionError(msg)
            elif code == API_ERROR_INSUFFICIENT_CONNECTIVITY:
                raise PandoraError("Out of sync", code,
                    submsg="Correct your system's clock. If the problem persists, a Pithos update may be required")
            elif code == API_ERROR_READ_ONLY_MODE:
                raise PandoraError("Pandora maintenance", code,
                    submsg="Pandora is in read-only mode as it is performing maintenance. Try again later.")
            elif code == API_ERROR_INVALID_LOGIN:
                raise PandoraError("Login Error", code, submsg="Invalid username or password")
            elif code == API_ERROR_LISTENER_NOT_AUTHORIZED:
                raise PandoraError("Pandora Error", code,
                    submsg="A Pandora One account is required to access this feature. Uncheck 'Pandora One' in Settings.")
            elif code == API_ERROR_PARTNER_NOT_AUTHORIZED:
                raise PandoraError("Login Error", code,
                    submsg="Invalid Pandora partner keys. A Pithos update may be required.")
            elif code == API_ERROR_PLAYLIST_EXCEEDED:
                raise PandoraError("Playlist Error", code,
                    submsg="You have requested too many playlists. Try again later.")
            else:
                raise PandoraError("Pandora returned an error", code, "%s (code %d)"%(msg, code))

        if 'result' in tree:
            return tree['result']

    def set_audio_quality(self, fmt):
        self.audio_quality = fmt

    def set_url_opener(self, opener):
        self.opener = opener

    def connect(self, client, user, password):
        self.partnerId = self.userId = self.partnerAuthToken = None
        self.userAuthToken = self.time_offset = None

        self.rpcUrl = client['rpcUrl']
        self.blowfish_encode = Blowfish(client['encryptKey'].encode('utf-8'))
        self.blowfish_decode = Blowfish(client['decryptKey'].encode('utf-8'))

        partner = self.json_call('auth.partnerLogin', {
            'deviceModel': client['deviceModel'],
            'username': client['username'], # partner username
            'password': client['password'], # partner password
            'version': client['version']
            },https=True, blowfish=False)

        self.partnerId = partner['partnerId']
        self.partnerAuthToken = partner['partnerAuthToken']

        pandora_time = int(self.pandora_decrypt(partner['syncTime'].encode('utf-8'))[4:14])
        self.time_offset = pandora_time - time.time()
        logging.info("Time offset is %s", self.time_offset)

        user = self.json_call('auth.userLogin', {'username': user, 'password': password, 'loginType': 'user'}, https=True)
        self.userId = user['userId']
        self.userAuthToken = user['userAuthToken']

        self.get_stations(self)

    def get_stations(self, *ignore):
        stations = self.json_call('user.getStationList')['stations']
        self.quickMixStationIds = None
        self.stations = [Station(self, i) for i in stations]

        if self.quickMixStationIds:
            for i in self.stations:
                if i.id in self.quickMixStationIds:
                    i.useQuickMix = True

    def save_quick_mix(self):
        stationIds = []
        for i in self.stations:
            if i.useQuickMix:
                stationIds.append(i.id)
        self.json_call('user.setQuickMix', {'quickMixStationIds': stationIds})

    def search(self, query):
        results = self.json_call('music.search', {'searchText': query})

        l =  [SearchResult('artist', i) for i in results['artists']]
        l += [SearchResult('song',   i) for i in results['songs']]
        l.sort(key=lambda i: i.score, reverse=True)

        return l

    def add_station_by_music_id(self, musicid):
        d = self.json_call('station.createStation', {'musicToken': musicid})
        station = Station(self, d)
        self.stations.append(station)
        return station

    def get_station_by_id(self, id):
        for i in self.stations:
            if i.id == id:
                return i

    def add_feedback(self, trackToken, rating):
        logging.info("pandora: addFeedback")
        rating_bool = True if rating == RATE_LOVE else False
        feedback = self.json_call('station.addFeedback', {'trackToken': trackToken, 'isPositive': rating_bool})
        return feedback['feedbackId']

    def delete_feedback(self, stationToken, feedbackId):
        self.json_call('station.deleteFeedback', {'feedbackId': feedbackId, 'stationToken': stationToken})

class Station(object):
    def __init__(self, pandora, d):
        self.pandora = pandora

        self.id = d['stationId']
        self.idToken = d['stationToken']
        self.isCreator = not d['isShared']
        self.isQuickMix = d['isQuickMix']
        self.name = d['stationName']
        self.useQuickMix = False

        if self.isQuickMix:
            self.pandora.quickMixStationIds = d.get('quickMixStationIds', [])

    def transformIfShared(self):
        if not self.isCreator:
            logging.info("pandora: transforming station")
            self.pandora.json_call('station.transformSharedStation', {'stationToken': self.idToken})
            self.isCreator = True

    def get_playlist(self):
        logging.info("pandora: Get Playlist")
        playlist = self.pandora.json_call('station.getPlaylist', {'stationToken': self.idToken}, https=True)
        songs = []
        for i in playlist['items']:
            if 'songName' in i: # check for ads
                songs.append(Song(self.pandora, i))
        return songs

    @property
    def info_url(self):
        return 'http://www.pandora.com/stations/'+self.idToken

    def rename(self, new_name):
        if new_name != self.name:
            self.transformIfShared()
            logging.info("pandora: Renaming station")
            self.pandora.json_call('station.renameStation', {'stationToken': self.idToken, 'stationName': new_name})
            self.name = new_name

    def delete(self):
        logging.info("pandora: Deleting Station")
        self.pandora.json_call('station.deleteStation', {'stationToken': self.idToken})

class Song(object):
    def __init__(self, pandora, d):
        self.pandora = pandora

        self.album = d['albumName']
        self.artist = d['artistName']
        self.audioUrlMap = d['audioUrlMap']
        self.trackToken = d['trackToken']
        self.rating = RATE_LOVE if d['songRating'] == 1 else RATE_NONE # banned songs won't play, so we don't care about them
        self.stationId = d['stationId']
        self.songName = d['songName']
        self.songDetailURL = d['songDetailUrl']
        self.songExplorerUrl = d['songExplorerUrl']
        self.artRadio = d['albumArtUrl']

        self.bitrate = None
        self.is_ad = None  # None = we haven't checked, otherwise True/False
        self.tired=False
        self.message=''
        self.start_time = None
        self.finished = False
        self.playlist_time = time.time()
        self.feedbackId = None

    @property
    def title(self):
        if not hasattr(self, '_title'):
            # the actual name of the track, minus any special characters (except dashes) is stored
            # as the last part of the songExplorerUrl, before the args.
            explorer_name = self.songExplorerUrl.split('?')[0].split('/')[-1]
            clean_expl_name = NAME_COMPARE_REGEX.sub('', explorer_name).lower()
            clean_name = NAME_COMPARE_REGEX.sub('', self.songName).lower()

            if clean_name == clean_expl_name:
                self._title = self.songName
            else:
                try:
                    xml_data = urllib.urlopen(self.songExplorerUrl)
                    dom = minidom.parseString(xml_data.read())
                    attr_value = dom.getElementsByTagName('songExplorer')[0].attributes['songTitle'].value

                    # Pandora stores their titles for film scores and the like as 'Score name: song name'
                    self._title = attr_value.replace('{0}: '.format(self.songName), '', 1)
                except:
                    self._title = self.songName
        return self._title

    @property
    def audioUrl(self):
        quality = self.pandora.audio_quality
        try:
            q = self.audioUrlMap[quality]
            logging.info("Using audio quality %s: %s %s", quality, q['bitrate'], q['encoding'])
            return q['audioUrl']
        except KeyError:
            logging.warn("Unable to use audio format %s. Using %s",
                           quality, list(self.audioUrlMap.keys())[0])
            return list(self.audioUrlMap.values())[0]['audioUrl']

    @property
    def station(self):
        return self.pandora.get_station_by_id(self.stationId)

    def rate(self, rating):
        if self.rating != rating:
            self.station.transformIfShared()
            if rating == RATE_NONE:
                if not self.feedbackId:
                    # We need a feedbackId, get one by re-rating the song. We
                    # could also get one by calling station.getStation, but
                    # that requires transferring a lot of data (all feedback,
                    # seeds, etc for the station).
                    opposite = RATE_BAN if self.rating == RATE_LOVE else RATE_LOVE
                    self.feedbackId = self.pandora.add_feedback(self.trackToken, opposite)
                self.pandora.delete_feedback(self.station.idToken, self.feedbackId)
            else:
                self.feedbackId = self.pandora.add_feedback(self.trackToken, rating)
            self.rating = rating

    def set_tired(self):
        if not self.tired:
            self.pandora.json_call('user.sleepSong', {'trackToken': self.trackToken})
            self.tired = True

    def bookmark(self):
        self.pandora.json_call('bookmark.addSongBookmark', {'trackToken': self.trackToken})

    def bookmark_artist(self):
        self.pandora.json_call('bookmark.addArtistBookmark', {'trackToken': self.trackToken})

    @property
    def rating_str(self):
        return self.rating

    def is_still_valid(self):
        return (time.time() - self.playlist_time) < PLAYLIST_VALIDITY_TIME


class SearchResult(object):
    def __init__(self, resultType, d):
        self.resultType = resultType
        self.score = d['score']
        self.musicId = d['musicToken']

        if resultType == 'song':
            self.title = d['songName']
            self.artist = d['artistName']
        elif resultType == 'artist':
            self.name = d['artistName']


########NEW FILE########
__FILENAME__ = pithos
#!/usr/bin/env python
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: nil; -*-
### BEGIN LICENSE
# Copyright (C) 2010-2012 Kevin Mehall <km@kevinmehall.net>
#This program is free software: you can redistribute it and/or modify it
#under the terms of the GNU General Public License version 3, as published
#by the Free Software Foundation.
#
#This program is distributed in the hope that it will be useful, but
#WITHOUT ANY WARRANTY; without even the implied warranties of
#MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR
#PURPOSE.  See the GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License along
#with this program.  If not, see <http://www.gnu.org/licenses/>.
### END LICENSE

import sys
import re
import os, time
import logging, argparse
import signal

import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GObject, Gtk, Gdk, Pango, GdkPixbuf, Gio, GLib
import contextlib
import html
import math
import urllib.request, urllib.error, urllib.parse
import json
if sys.platform != 'win32':
    from dbus.mainloop.glib import DBusGMainLoop
    DBusGMainLoop(set_as_default=True)

# Check if we are working in the source tree or from the installed
# package and mangle the python path accordingly
realPath = os.path.realpath(sys.argv[0])  # If this file is run from a symlink, it needs to follow the symlink
if os.path.dirname(realPath) != ".":
    if realPath[0] == "/":
        fullPath = os.path.dirname(realPath)
    else:
        fullPath = os.getcwd() + "/" + os.path.dirname(realPath)
else:
    fullPath = os.getcwd()
sys.path.insert(0, os.path.dirname(fullPath))

from . import AboutPithosDialog, PreferencesPithosDialog, StationsDialog
from .util import parse_proxy, open_browser
from .pithosconfig import get_ui_file, get_media_file, VERSION
from .gobject_worker import GObjectWorker
from .plugin import load_plugins
if sys.platform != 'win32':
    from .dbus_service import PithosDBusProxy
    from .mpris import PithosMprisService
from .pandora import *
from .pandora.data import *

pacparser_imported = False
try:
    import pacparser
    pacparser_imported = True
except ImportError:
    pass

def buttonMenu(button, menu):
    def cb(button):
        allocation = button.get_allocation()
        x, y = button.get_window().get_origin()[1:]
        x += allocation.x
        y += allocation.y + allocation.height
        menu.popup(None, None, (lambda *ignore: (x, y, True)), None, 1, Gtk.get_current_event_time())

    button.connect('clicked', cb)

ALBUM_ART_SIZE = 96
ALBUM_ART_X_PAD = 6

class CellRendererAlbumArt(Gtk.CellRenderer):
    def __init__(self):
        GObject.GObject.__init__(self)
        self.icon = None
        self.pixbuf = None
        self.rate_bg = GdkPixbuf.Pixbuf.new_from_file(get_media_file('rate'))

    __gproperties__ = {
        'icon': (str, 'icon', 'icon', '', GObject.PARAM_READWRITE),
        'pixbuf': (GdkPixbuf.Pixbuf, 'pixmap', 'pixmap',  GObject.PARAM_READWRITE)
    }

    def do_set_property(self, pspec, value):
        setattr(self, pspec.name, value)
    def do_get_property(self, pspec):
        return getattr(self, pspec.name)
    def do_get_size(self, widget, cell_area):
        return (0, 0, ALBUM_ART_SIZE + ALBUM_ART_X_PAD, ALBUM_ART_SIZE)
    def do_render(self, ctx, widget, background_area, cell_area, flags):
        if self.pixbuf:
            Gdk.cairo_set_source_pixbuf(ctx, self.pixbuf, cell_area.x, cell_area.y)
            ctx.paint()
        if self.icon:
            x = cell_area.x+(cell_area.width-self.rate_bg.get_width()) - ALBUM_ART_X_PAD # right
            y = cell_area.y+(cell_area.height-self.rate_bg.get_height()) # bottom
            Gdk.cairo_set_source_pixbuf(ctx, self.rate_bg, x, y)
            ctx.paint()

            icon = widget.get_style_context().lookup_icon_set(self.icon)
            pixbuf = icon.render_icon_pixbuf(widget.get_style_context(), Gtk.IconSize.MENU)
            x = cell_area.x+(cell_area.width-pixbuf.get_width())-5 - ALBUM_ART_X_PAD # right
            y = cell_area.y+(cell_area.height-pixbuf.get_height())-5 # bottom
            Gdk.cairo_set_source_pixbuf(ctx, pixbuf, x, y)
            ctx.paint()

def get_album_art(url, *extra):
    try:
        with urllib.request.urlopen(url) as f:
            image = f.read()
    except urllib.error.HTTPError:
        logging.warn('Invalid image url received')
        return (None,) + extra

    with contextlib.closing(GdkPixbuf.PixbufLoader()) as loader:
        loader.set_size(ALBUM_ART_SIZE, ALBUM_ART_SIZE)
        loader.write(image)
        return (loader.get_pixbuf(),) + extra


class PithosWindow(Gtk.ApplicationWindow):
    __gtype_name__ = "PithosWindow"
    __gsignals__ = {
        "song-changed": (GObject.SignalFlags.RUN_FIRST, None, (GObject.TYPE_PYOBJECT,)),
        "song-ended": (GObject.SignalFlags.RUN_FIRST, None, (GObject.TYPE_PYOBJECT,)),
        "song-rating-changed": (GObject.SignalFlags.RUN_FIRST, None, (GObject.TYPE_PYOBJECT,)),
        "play-state-changed": (GObject.SignalFlags.RUN_FIRST, None, (GObject.TYPE_BOOLEAN,)),
        "user-changed-play-state": (GObject.SignalFlags.RUN_FIRST, None, (GObject.TYPE_BOOLEAN,)),
    }

    def __init__(self):
        """__init__ - This function is typically not called directly.
        Creation a PithosWindow requires redeading the associated ui
        file and parsing the ui definition extrenally,
        and then calling PithosWindow.finish_initializing().

        Use the convenience function NewPithosWindow to create
        PithosWindow object.

        """
        pass

    def finish_initializing(self, builder, cmdopts):
        """finish_initalizing should be called after parsing the ui definition
        and creating a PithosWindow object with it in order to finish
        initializing the start of the new PithosWindow instance.

        """
        signal.signal(signal.SIGINT, signal.SIG_DFL)

        self.cmdopts = cmdopts

        #get a reference to the builder and set up the signals
        self.builder = builder
        self.builder.connect_signals(self)

        self.prefs_dlg = PreferencesPithosDialog.NewPreferencesPithosDialog()
        self.prefs_dlg.set_transient_for(self)
        self.preferences = self.prefs_dlg.get_preferences()

        if self.prefs_dlg.fix_perms():
            # Changes were made, save new config variable
            self.prefs_dlg.save()

        self.init_core()
        self.init_ui()

        self.plugins = {}
        load_plugins(self)

        if sys.platform != 'win32':
            self.dbus_service = PithosDBusProxy(self)
            self.mpris = PithosMprisService(self)

        if not self.preferences['username']:
            self.show_preferences(is_startup=True)

        self.pandora = make_pandora(self.cmdopts.test)
        self.set_proxy()
        self.set_audio_quality()
        self.pandora_connect()

    def init_core(self):
        #                                Song object            display text  icon  album art
        self.songs_model = Gtk.ListStore(GObject.TYPE_PYOBJECT, str,          str,  GdkPixbuf.Pixbuf)
        #                                   Station object         station name
        self.stations_model = Gtk.ListStore(GObject.TYPE_PYOBJECT, str)

        Gst.init(None)
        self.player = Gst.ElementFactory.make("playbin", "player");
        self.player.props.flags |= (1 << 7) # enable progressive download (GST_PLAY_FLAG_DOWNLOAD)
        bus = self.player.get_bus()
        bus.add_signal_watch()
        bus.connect("message::eos", self.on_gst_eos)
        bus.connect("message::buffering", self.on_gst_buffering)
        bus.connect("message::error", self.on_gst_error)
        bus.connect("message::tag", self.on_gst_tag)
        self.player.connect("notify::volume", self.on_gst_volume)
        self.player.connect("notify::source", self.on_gst_source)
        self.time_format = Gst.Format.TIME

        self.stations_dlg = None

        self.playing = False
        self.current_song_index = None
        self.current_station = None
        self.current_station_id = self.preferences.get('last_station_id')

        self.buffer_percent = 100
        self.auto_retrying_auth = False
        self.have_stations = False
        self.playcount = 0
        self.gstreamer_errorcount_1 = 0
        self.gstreamer_errorcount_2 = 0
        self.gstreamer_error = ''
        self.waiting_for_playlist = False
        self.start_new_playlist = False

        self.worker = GObjectWorker()
        self.art_worker = GObjectWorker()

        aa = GdkPixbuf.Pixbuf.new_from_file(get_media_file('album'))

        self.default_album_art = aa.scale_simple(ALBUM_ART_SIZE, ALBUM_ART_SIZE, GdkPixbuf.InterpType.BILINEAR)

    def init_ui(self):
        GLib.set_application_name("Pithos")
        Gtk.Window.set_default_icon_name('pithos')
        os.environ['PULSE_PROP_media.role'] = 'music'

        self.playpause_image = self.builder.get_object('playpause_image')

        self.volume = self.builder.get_object('volume')
        self.volume.set_relief(Gtk.ReliefStyle.NORMAL)  # It ignores glade...
        self.volume.set_property("value", math.pow(float(self.preferences['volume']), 1.0/3.0))

        self.statusbar = self.builder.get_object('statusbar1')

        self.song_menu = self.builder.get_object('song_menu')
        self.song_menu_love = self.builder.get_object('menuitem_love')
        self.song_menu_unlove = self.builder.get_object('menuitem_unlove')
        self.song_menu_ban = self.builder.get_object('menuitem_ban')
        self.song_menu_unban = self.builder.get_object('menuitem_unban')

        self.songs_treeview = self.builder.get_object('songs_treeview')
        self.songs_treeview.set_model(self.songs_model)

        title_col   = Gtk.TreeViewColumn()

        def bgcolor_data_func(column, cell, model, iter, data=None):
            if model.get_value(iter, 0) is self.current_song:
                bgcolor = column.get_tree_view().get_style_context().get_background_color(Gtk.StateFlags.ACTIVE)
            else:
                bgcolor = column.get_tree_view().get_style_context().get_background_color(Gtk.StateFlags.NORMAL)
            cell.set_property("cell-background-rgba", bgcolor)

        render_icon = CellRendererAlbumArt()
        title_col.pack_start(render_icon, False)
        title_col.add_attribute(render_icon, "icon", 2)
        title_col.add_attribute(render_icon, "pixbuf", 3)
        title_col.set_cell_data_func(render_icon, bgcolor_data_func)

        render_text = Gtk.CellRendererText()
        render_text.props.ellipsize = Pango.EllipsizeMode.END
        title_col.pack_start(render_text, True)
        title_col.add_attribute(render_text, "markup", 1)
        title_col.set_cell_data_func(render_text, bgcolor_data_func)

        self.songs_treeview.append_column(title_col)

        self.songs_treeview.connect('button_press_event', self.on_treeview_button_press_event)

        self.stations_combo = self.builder.get_object('stations')
        self.stations_combo.set_model(self.stations_model)
        render_text = Gtk.CellRendererText()
        self.stations_combo.pack_start(render_text, True)
        self.stations_combo.add_attribute(render_text, "text", 1)
        self.stations_combo.set_row_separator_func(lambda model, iter, data=None: model.get_value(iter, 0) is None, None)

    def worker_run(self, fn, args=(), callback=None, message=None, context='net'):
        if context and message:
            self.statusbar.push(self.statusbar.get_context_id(context), message)

        if isinstance(fn,str):
            fn = getattr(self.pandora, fn)

        def cb(v):
            if context: self.statusbar.pop(self.statusbar.get_context_id(context))
            if callback: callback(v)

        def eb(e):
            if context and message:
                self.statusbar.pop(self.statusbar.get_context_id(context))

            def retry_cb():
                self.auto_retrying_auth = False
                if fn is not self.pandora.connect:
                    self.worker_run(fn, args, callback, message, context)

            if isinstance(e, PandoraAuthTokenInvalid) and not self.auto_retrying_auth:
                self.auto_retrying_auth = True
                logging.info("Automatic reconnect after invalid auth token")
                self.pandora_connect("Reconnecting...", retry_cb)
            elif isinstance(e, PandoraAPIVersionError):
                self.api_update_dialog()
            elif isinstance(e, PandoraError):
                self.error_dialog(e.message, retry_cb, submsg=e.submsg)
            else:
                logging.warn(e.traceback)

        self.worker.send(fn, args, cb, eb)

    def get_proxy(self):
        """ Get HTTP proxy, first trying preferences then system proxy """

        if self.preferences['proxy']:
            return self.preferences['proxy']

        system_proxies = urllib.request.getproxies()
        if 'http' in system_proxies:
            return system_proxies['http']

        return None

    def set_proxy(self):
        # proxy preference is used for all Pithos HTTP traffic
        # control proxy preference is used only for Pandora traffic and
        # overrides proxy
        #
        # If neither option is set, urllib2.build_opener uses urllib.getproxies()
        # by default

        handlers = []
        global_proxy = self.preferences['proxy']
        if global_proxy:
            handlers.append(urllib.request.ProxyHandler({'http': global_proxy, 'https': global_proxy}))
        global_opener = urllib.request.build_opener(*handlers)
        urllib.request.install_opener(global_opener)

        control_opener = global_opener
        control_proxy = self.preferences['control_proxy']
        control_proxy_pac = self.preferences['control_proxy_pac']

        if control_proxy:
            control_opener = urllib.request.build_opener(urllib.request.ProxyHandler({'http': control_proxy, 'https': control_proxy}))

        elif control_proxy_pac and pacparser_imported:
            pacparser.init()
            pacparser.parse_pac_string(urllib.request.urlopen(control_proxy_pac).read())
            proxies = pacparser.find_proxy("http://pandora.com", "pandora.com").split(";")
            for proxy in proxies:
                match = re.search("PROXY (.*)", proxy)
                if match:
                    control_proxy = match.group(1)
                    break
        elif control_proxy_pac and not pacparser_imported:
            logging.warn("Disabled proxy auto-config support because python-pacparser module was not found.")

        self.worker_run('set_url_opener', (control_opener,))

    def set_audio_quality(self):
        self.worker_run('set_audio_quality', (self.preferences['audio_quality'],))

    def pandora_connect(self, message="Logging in...", callback=None):
        if self.preferences['pandora_one']:
            client = client_keys[default_one_client_id]
        else:
            client = client_keys[default_client_id]

        # Allow user to override client settings
        force_client = self.preferences['force_client']
        if force_client in client_keys:
            client = client_keys[force_client]
        elif force_client and force_client[0] == '{':
            try:
                client = json.loads(force_client)
            except:
                logging.error("Could not parse force_client json")

        args = (
            client,
            self.preferences['username'],
            self.preferences['password'],
        )

        def pandora_ready(*ignore):
            logging.info("Pandora connected")
            self.process_stations(self)
            if callback:
                callback()

        self.worker_run('connect', args, pandora_ready, message, 'login')

    def process_stations(self, *ignore):
        self.stations_model.clear()
        self.current_station = None
        selected = None

        for i in self.pandora.stations:
            if i.isQuickMix and i.isCreator:
                self.stations_model.append((i, "QuickMix"))
        self.stations_model.append((None, 'sep'))
        for i in self.pandora.stations:
            if not (i.isQuickMix and i.isCreator):
                self.stations_model.append((i, i.name))
            if i.id == self.current_station_id:
                logging.info("Restoring saved station: id = %s"%(i.id))
                selected = i
        if not selected:
            selected=self.stations_model[0][0]
        self.station_changed(selected, reconnecting = self.have_stations)
        self.have_stations = True

    @property
    def current_song(self):
        if self.current_song_index is not None:
            return self.songs_model[self.current_song_index][0]

    def start_song(self, song_index):
        songs_remaining = len(self.songs_model) - song_index

        if songs_remaining <= 0:
            # We don't have this song yet. Get a new playlist.
            return self.get_playlist(start = True)
        elif songs_remaining == 1:
            # Preload next playlist so there's no delay
            self.get_playlist()

        prev = self.current_song

        self.stop()
        self.current_song_index = song_index

        if prev:
            self.update_song_row(prev)

        if not self.current_song.is_still_valid():
            self.current_song.message = "Playlist expired"
            self.update_song_row()
            return self.next_song()

        if self.current_song.tired or self.current_song.rating == RATE_BAN:
            return self.next_song()

        logging.info("Starting song: index = %i"%(song_index))
        self.buffer_percent = 0
        self.song_started = False
        self.player.set_property("uri", self.current_song.audioUrl)
        self.play()
        self.playcount += 1

        self.current_song.start_time = time.time()

        self.songs_treeview.scroll_to_cell(song_index, use_align=True, row_align = 1.0)
        self.songs_treeview.set_cursor(song_index, None, 0)
        self.set_title("Pithos - %s by %s" % (self.current_song.title, self.current_song.artist))

        self.emit('song-changed', self.current_song)

    def next_song(self, *ignore):
        self.start_song(self.current_song_index + 1)

    def user_play(self, *ignore):
        self.play()
        self.song_started = True
        self.emit('user-changed-play-state', True)

    def play(self):
        if not self.playing:
            self.playing = True
        self.player.set_state(Gst.State.PLAYING)
        GLib.timeout_add_seconds(1, self.update_song_row)
        self.playpause_image.set_from_icon_name('media-playback-pause-symbolic', Gtk.IconSize.SMALL_TOOLBAR)
        self.update_song_row()
        self.emit('play-state-changed', True)

    def user_pause(self, *ignore):
        self.pause()
        self.emit('user-changed-play-state', False)

    def pause(self):
        self.playing = False
        self.player.set_state(Gst.State.PAUSED)
        self.playpause_image.set_from_icon_name('media-playback-start-symbolic', Gtk.IconSize.SMALL_TOOLBAR)
        self.update_song_row()
        self.emit('play-state-changed', False)


    def stop(self):
        prev = self.current_song
        if prev and prev.start_time:
            prev.finished = True
            dur_stat, dur = self.player.query_duration(self.time_format)
            prev.duration = dur//1000000000 if dur_stat else None
            pos_stat, pos = self.player.query_position(self.time_format)
            prev.position = pos//1000000000 if pos_stat else None
            self.emit("song-ended", prev)

        self.playing = False
        self.player.set_state(Gst.State.NULL)
        self.emit('play-state-changed', False)

    def user_playpause(self, *ignore):
        self.playpause_notify()
        
    def playpause(self, *ignore):
        logging.info("playpause")
        if self.playing:
            self.pause()
        else:
            self.play()

    def playpause_notify(self, *ignore):
        if self.playing:
            self.user_pause()
        else:
            self.user_play()

    def get_playlist(self, start = False):
        self.start_new_playlist = self.start_new_playlist or start
        if self.waiting_for_playlist: return

        if self.gstreamer_errorcount_1 >= self.playcount and self.gstreamer_errorcount_2 >=1:
            logging.warn("Too many gstreamer errors. Not retrying")
            self.waiting_for_playlist = 1
            self.error_dialog(self.gstreamer_error, self.get_playlist)
            return

        def art_callback(t):
            pixbuf, song, index = t
            if index<len(self.songs_model) and self.songs_model[index][0] is song: # in case the playlist has been reset
                logging.info("Downloaded album art for %i"%song.index)
                song.art_pixbuf = pixbuf
                self.songs_model[index][3]=pixbuf
                self.update_song_row(song)

        def callback(l):
            start_index = len(self.songs_model)
            for i in l:
                i.index = len(self.songs_model)
                self.songs_model.append((i, '', '', self.default_album_art))
                self.update_song_row(i)

                i.art_pixbuf = None
                if i.artRadio:
                    self.art_worker.send(get_album_art, (i.artRadio, i, i.index), art_callback)

            self.statusbar.pop(self.statusbar.get_context_id('net'))
            if self.start_new_playlist:
                self.start_song(start_index)

            self.gstreamer_errorcount_2 = self.gstreamer_errorcount_1
            self.gstreamer_errorcount_1 = 0
            self.playcount = 0
            self.waiting_for_playlist = False
            self.start_new_playlist = False

        self.waiting_for_playlist = True
        self.worker_run(self.current_station.get_playlist, (), callback, "Getting songs...")

    def error_dialog(self, message, retry_cb, submsg=None):
        dialog = self.builder.get_object("error_dialog")

        dialog.props.text = message
        dialog.props.secondary_text = submsg
        dialog.set_default_response(3)

        response = dialog.run()
        dialog.hide()

        if response == 2:
            self.gstreamer_errorcount_2 = 0
            logging.info("Manual retry")
            return retry_cb()
        elif response == 3:
            self.show_preferences()

    def fatal_error_dialog(self, message, submsg):
        dialog = self.builder.get_object("fatal_error_dialog")
        dialog.props.text = message
        dialog.props.secondary_text = submsg
        dialog.set_default_response(1)

        response = dialog.run()
        dialog.hide()

        self.quit()

    def api_update_dialog(self):
        dialog = self.builder.get_object("api_update_dialog")
        dialog.set_default_response(0)
        response = dialog.run()
        if response:
            open_browser("http://pithos.github.io/itbroke?utm_source=pithos&utm_medium=app&utm_campaign=%s"%VERSION)
        self.quit()

    def station_index(self, station):
        return [i[0] for i in self.stations_model].index(station)

    def station_changed(self, station, reconnecting=False):
        if station is self.current_station: return
        self.waiting_for_playlist = False
        if not reconnecting:
            self.stop()
            self.current_song_index = None
            self.songs_model.clear()
        logging.info("Selecting station %s; total = %i" % (station.id, len(self.stations_model)))
        self.current_station_id = station.id
        self.current_station = station
        if not reconnecting:
            self.get_playlist(start = True)
        self.stations_combo.set_active(self.station_index(station))

    def on_gst_eos(self, bus, message):
        logging.info("EOS")
        self.next_song()

    def on_gst_error(self, bus, message):
        err, debug = message.parse_error()
        logging.error("Gstreamer error: %s, %s, %s" % (err, debug, err.code))
        if self.current_song:
            self.current_song.message = "Error: "+str(err)

        #if err.code is int(Gst.CORE_ERROR_MISSING_PLUGIN):
        #    self.fatal_error_dialog("Missing codec", submsg="GStreamer is missing a plugin")
        #    return

        self.gstreamer_error = str(err)
        self.gstreamer_errorcount_1 += 1
        self.next_song()

    def gst_tag_handler(self, tag_info):
        def handler(_x, tag, _y):
            # An exhaustive list of tags is available at 
            # https://developer.gnome.org/gstreamer/stable/gstreamer-GstTagList.html
            # but Pandora seems to only use those
            if tag == 'datetime':
                _, datetime = tag_info.get_date_time(tag)
                value = datetime.to_iso8601_string()
            elif tag in ('container-format', 'audio-codec'):
                _, value = tag_info.get_string(tag)
            elif tag in ('bitrate', 'maximum-bitrate', 'minimum-bitrate'):
                _, value = tag_info.get_uint(tag)
            else:
                value = 'Don\'t know the type of this'

            logging.debug('Found tag "%s" in stream: "%s" (type: %s)' % (tag, value, type(value)))

            if tag == 'audio-codec':
                # At that point we should have duration information, check for ads
                self.check_if_song_is_ad()

            if tag == 'bitrate':
                self.current_song.bitrate = value
                self.update_song_row()

        return handler

    def check_if_song_is_ad(self):
        if self.current_song.is_ad is None:
            dur_stat, dur_int = self.player.query_duration(self.time_format)

            if not dur_stat:
                logging.warning('dur_stat is False. The assumption that duration is available once the audio-codec messages feeds is bad.')
            else:
                dur_int /= 1e9

                if dur_int < 45.0:  # Less than 45 seconds we assume it's an ad
                    logging.info('Ad detected!')
                    self.current_song.is_ad = True
                    self.update_song_row()
                else:
                    logging.info('Not an Ad..')
                    self.current_song.is_ad = False

    def on_gst_tag(self, bus, message):
        tag_info = message.parse_tag()
        tag_handler = self.gst_tag_handler(tag_info)
        tag_info.foreach(tag_handler, None)

    def on_gst_buffering(self, bus, message):
        # per GST documentation:
        # Note that applications should keep/set the pipeline in the PAUSED state when a BUFFERING
        # message is received with a buffer percent value < 100 and set the pipeline back to PLAYING
        # state when a BUFFERING message with a value of 100 percent is received.
        
        # 100% doesn't mean the entire song is downloaded, but it does mean that it's safe to play.
        # trying to play before 100% will cause stuttering.
        percent = message.parse_buffering()
        self.buffer_percent = percent
        if percent < 100:
            self.player.set_state(Gst.State.PAUSED)
        else:
            if self.playing:
                self.play()
                self.song_started = True
        self.update_song_row()
        logging.debug("Buffering (%i%%)"%self.buffer_percent)

    def set_volume_cb(self, volume):
        # Convert to the cubic scale that the volume slider uses
        scaled_volume = math.pow(volume, 1.0/3.0)
        self.volume.handler_block_by_func(self.on_volume_change_event)
        self.volume.set_property("value", scaled_volume)
        self.volume.handler_unblock_by_func(self.on_volume_change_event)
        self.preferences['volume'] = volume

    def on_gst_volume(self, player, volumespec):
        vol = self.player.get_property('volume')
        GLib.idle_add(self.set_volume_cb, vol)

    def on_gst_source(self, player, params):
        """ Setup httpsoupsrc to match Pithos proxy settings """
        soup = player.props.source.props
        proxy = self.get_proxy()
        if proxy and hasattr(soup, 'proxy'):
            scheme, user, password, hostport = parse_proxy(proxy)
            soup.proxy = hostport
            soup.proxy_id = user
            soup.proxy_pw = password

    def song_text(self, song):
        title = html.escape(song.title)
        artist = html.escape(song.artist)
        album = html.escape(song.album)
        msg = []
        if song is self.current_song:
            dur_stat, dur_int = self.player.query_duration(self.time_format)
            pos_stat, pos_int = self.player.query_position(self.time_format)
            if not self.song_started:
                pos_int = 0
            if not song.bitrate is None:
                msg.append("%0dkbit/s" % (song.bitrate / 1000))
            if dur_stat and pos_stat:
                dur_str = self.format_time(dur_int)
                pos_str = self.format_time(pos_int)
                msg.append("%s / %s" %(pos_str, dur_str))
                if not self.playing:
                    msg.append("Paused")
            if self.buffer_percent < 100:
                msg.append("Buffering (%i%%)"%self.buffer_percent)
        if song.message:
            msg.append(song.message)
        msg = " - ".join(msg)
        if not msg:
            msg = " "

        if song.is_ad:
            description = "<b><big>Commercial Advertisement</big></b>\n<b>Pandora</b>"
        else:
            description = "<b><big>%s</big></b>\nby <b>%s</b>\n<small>from <i>%s</i></small>" % (title, artist, album)

        return "%s\n<small>%s</small>" % (description, msg)

    def song_icon(self, song):
        if song.tired:
            return Gtk.STOCK_JUMP_TO
        if song.rating == RATE_LOVE:
            return Gtk.STOCK_ABOUT
        if song.rating == RATE_BAN:
            return Gtk.STOCK_CANCEL

    def update_song_row(self, song = None):
        if song is None:
            song = self.current_song
        if song:
            self.songs_model[song.index][1] = self.song_text(song)
            self.songs_model[song.index][2] = self.song_icon(song) or ""
        return self.playing

    def stations_combo_changed(self, widget):
        index = widget.get_active()
        if index>=0:
            self.station_changed(self.stations_model[index][0])

    def format_time(self, time_int):
        time_int = time_int // 1000000000
        s = time_int % 60
        time_int //= 60
        m = time_int % 60
        time_int //= 60
        h = time_int

        if h:
            return "%i:%02i:%02i"%(h,m,s)
        else:
            return "%i:%02i"%(m,s)

    def selected_song(self):
        sel = self.songs_treeview.get_selection().get_selected()
        if sel:
            return self.songs_treeview.get_model().get_value(sel[1], 0)

    def love_song(self, song=None):
        song = song or self.current_song
        def callback(l):
            self.update_song_row(song)
            self.emit('song-rating-changed', song)
        self.worker_run(song.rate, (RATE_LOVE,), callback, "Loving song...")


    def ban_song(self, song=None):
        song = song or self.current_song
        def callback(l):
            self.update_song_row(song)
            self.emit('song-rating-changed', song)
        self.worker_run(song.rate, (RATE_BAN,), callback, "Banning song...")
        if song is self.current_song:
            self.next_song()

    def unrate_song(self, song=None):
        song = song or self.current_song
        def callback(l):
            self.update_song_row(song)
            self.emit('song-rating-changed', song)
        self.worker_run(song.rate, (RATE_NONE,), callback, "Removing song rating...")

    def tired_song(self, song=None):
        song = song or self.current_song
        def callback(l):
            self.update_song_row(song)
            self.emit('song-rating-changed', song)
        self.worker_run(song.set_tired, (), callback, "Putting song on shelf...")
        if song is self.current_song:
            self.next_song()

    def bookmark_song(self, song=None):
        song = song or self.current_song
        self.worker_run(song.bookmark, (), None, "Bookmarking...")

    def bookmark_song_artist(self, song=None):
        song = song or self.current_song
        self.worker_run(song.bookmark_artist, (), None, "Bookmarking...")

    def on_menuitem_love(self, widget):
        self.love_song(self.selected_song())

    def on_menuitem_ban(self, widget):
        self.ban_song(self.selected_song())

    def on_menuitem_unrate(self, widget):
        self.unrate_song(self.selected_song())

    def on_menuitem_tired(self, widget):
        self.tired_song(self.selected_song())

    def on_menuitem_info(self, widget):
        song = self.selected_song()
        open_browser(song.songDetailURL)

    def on_menuitem_bookmark_song(self, widget):
        self.bookmark_song(self.selected_song())

    def on_menuitem_bookmark_artist(self, widget):
        self.bookmark_song_artist(self.selected_song())

    def on_treeview_button_press_event(self, treeview, event):
        x = int(event.x)
        y = int(event.y)
        time = event.time
        pthinfo = treeview.get_path_at_pos(x, y)
        if pthinfo is not None:
            path, col, cellx, celly = pthinfo
            treeview.grab_focus()
            treeview.set_cursor( path, col, 0)

            if event.button == 3:
                rating = self.selected_song().rating
                self.song_menu_love.set_property("visible", rating != RATE_LOVE);
                self.song_menu_unlove.set_property("visible", rating == RATE_LOVE);
                self.song_menu_ban.set_property("visible", rating != RATE_BAN);
                self.song_menu_unban.set_property("visible", rating == RATE_BAN);

                self.song_menu.popup( None, None, None, None, event.button, time)
                return True

            if event.button == 1 and event.type == Gdk.EventType._2BUTTON_PRESS:
                logging.info("Double clicked on song %s", self.selected_song().index)
                if self.selected_song().index <= self.current_song_index:
                    return False
                self.start_song(self.selected_song().index)

    def set_player_volume(self, value):
        logging.info('%.3f' % value)
        # Use a cubic scale for volume. This matches what PulseAudio uses.
        volume = math.pow(value, 3)
        self.player.set_property("volume", volume)
        self.preferences['volume'] = volume

    def adjust_volume(self, amount):
        old_volume = self.volume.get_property("value")
        new_volume = max(0.0, min(1.0, old_volume + 0.02 * amount))

        if new_volume != old_volume:
            self.volume.set_property("value", new_volume)

    def on_volume_change_event(self, volumebutton, value):
        self.set_player_volume(value)

    def station_properties(self, *ignore):
        open_browser(self.current_station.info_url)

    def show_about(self):
        """about - display the about box for pithos """
        about = AboutPithosDialog.NewAboutPithosDialog()
        about.set_transient_for(self)
        about.set_version(VERSION)
        response = about.run()
        about.destroy()

    def show_preferences(self, is_startup=False):
        """preferences - display the preferences window for pithos """
        if is_startup:
            self.prefs_dlg.set_type_hint(Gdk.WindowTypeHint.NORMAL)

        old_prefs = dict(self.preferences)
        response = self.prefs_dlg.run()
        self.prefs_dlg.hide()

        if response == Gtk.ResponseType.OK:
            self.preferences = self.prefs_dlg.get_preferences()
            if not is_startup:
                if (   self.preferences['proxy'] != old_prefs['proxy']
                    or self.preferences['control_proxy'] != old_prefs['control_proxy']):
                    self.set_proxy()
                if self.preferences['audio_quality'] != old_prefs['audio_quality']:
                    self.set_audio_quality()
                if (   self.preferences['username'] != old_prefs['username']
                    or self.preferences['password'] != old_prefs['password']
                    or self.preferences['pandora_one'] != old_prefs['pandora_one']):
                        self.pandora_connect()
            else:
                self.prefs_dlg.set_type_hint(Gdk.WindowTypeHint.DIALOG)
            load_plugins(self)

    def show_stations(self):
        if self.stations_dlg:
            self.stations_dlg.present()
        else:
            self.stations_dlg = StationsDialog.NewStationsDialog(self)
            self.stations_dlg.set_transient_for(self)
            self.stations_dlg.show_all()

    def refresh_stations(self, *ignore):
        self.worker_run(self.pandora.get_stations, (), self.process_stations, "Refreshing stations...")

    def bring_to_top(self, *ignore):
        self.show()
        self.present()

    def on_kb_playpause(self, widget=None, data=None):
        if not isinstance(widget.get_focus(), Gtk.Button) and data.keyval == 32:
            self.playpause()
            return True

    def quit(self, widget=None, data=None):
        """quit - signal handler for closing the PithosWindow"""
        self.destroy()

    def on_destroy(self, widget, data=None):
        """on_destroy - called when the PithosWindow is close. """
        self.stop()
        self.preferences['last_station_id'] = self.current_station_id
        self.prefs_dlg.save()
        self.quit()

def NewPithosWindow(app, options):
    """NewPithosWindow - returns a fully instantiated
    PithosWindow object. Use this function rather than
    creating a PithosWindow directly.
    """

    builder = Gtk.Builder()
    builder.add_from_file(get_ui_file('main'))
    window = builder.get_object("pithos_window")
    window.set_application(app)
    window.finish_initializing(builder, options)
    return window

class PithosApplication(Gtk.Application):
    def __init__(self):
        # Use org.gnome to avoid conflict with existing dbus interface net.kevinmehall
        Gtk.Application.__init__(self, application_id='org.gnome.pithos',
                                flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE)
        self.window = None
        self.options = None

    def do_startup(self):
        Gtk.Application.do_startup(self)

        # Setup appmenu
        builder = Gtk.Builder()
        builder.add_from_file(get_ui_file('menu'))
        menu = builder.get_object("app-menu")
        self.set_app_menu(menu)

        action = Gio.SimpleAction.new("stations", None)
        action.connect("activate", self.stations_cb)
        self.add_action(action)

        action = Gio.SimpleAction.new("preferences", None)
        action.connect("activate", self.prefs_cb)
        self.add_action(action)

        action = Gio.SimpleAction.new("about", None)
        action.connect("activate", self.about_cb)
        self.add_action(action)

        action = Gio.SimpleAction.new("quit", None)
        action.connect("activate", self.quit_cb)
        self.add_action(action)

    # FIXME: do_local_command_line() segfaults?
    def do_command_line(self, args):
        Gtk.Application.do_command_line(self, args)

        parser = argparse.ArgumentParser()
        parser.add_argument("-v", "--verbose", action="count", default=0, dest="verbose", help="Show debug messages")
        parser.add_argument("-t", "--test", action="store_true", dest="test", help="Use a mock web interface instead of connecting to the real Pandora server")
        self.options = parser.parse_args(args.get_arguments()[1:])

        # First, get rid of existing logging handlers due to call in header as per
        # http://stackoverflow.com/questions/1943747/python-logging-before-you-run-logging-basicconfig
        logging.root.handlers = []

        #set the logging level to show debug messages
        if self.options.verbose > 1:
            log_level = logging.DEBUG
        elif self.options.verbose == 1:
            log_level = logging.INFO
        else:
            log_level = logging.WARN

        logging.basicConfig(level=log_level, format='%(levelname)s - %(module)s:%(funcName)s:%(lineno)d - %(message)s')

        self.do_activate()

        return 0

    def do_activate(self):
        if not self.window:
            logging.info("Pithos %s" %VERSION)
            self.window = NewPithosWindow(self, self.options)

        self.window.present()

    def do_shutdown(self):
        Gtk.Application.do_shutdown(self)
        self.quit()

    def stations_cb(self, action, param):
        self.window.show_stations()

    def prefs_cb(self, action, param):
        self.window.show_preferences()

    def about_cb(self, action, param):
        self.window.show_about()

    def quit_cb(self, action, param):
        self.quit()

def main():
    app = PithosApplication()
    exit_status = app.run(sys.argv)
    sys.exit(exit_status)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = pithosconfig
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: nil; -*-
### BEGIN LICENSE
# Copyright (C) 2010-2012 Kevin Mehall <km@kevinmehall.net>
#This program is free software: you can redistribute it and/or modify it
#under the terms of the GNU General Public License version 3, as published
#by the Free Software Foundation.
#
#This program is distributed in the hope that it will be useful, but
#WITHOUT ANY WARRANTY; without even the implied warranties of
#MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR
#PURPOSE.  See the GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License along
#with this program.  If not, see <http://www.gnu.org/licenses/>.
### END LICENSE

# where your project will head for your data (for instance, images and ui files)
# by default, this is data, relative your trunk layout
__pithos_data_directory__ = 'data/'
__license__ = 'GPL-3'

VERSION = '1.0.0'

import os

class project_path_not_found(Exception):
    pass

ui_files = {
    'about': 'AboutPithosDialog.ui',
    'preferences': 'PreferencesPithosDialog.ui',
    'search': 'SearchDialog.ui',
    'stations': 'StationsDialog.ui',
    'main': 'PithosWindow.ui',
    'menu': 'app_menu.ui'
}

media_files = {
    'icon': 'icon.svg',
    'rate': 'rate_bg.png',
    'album': 'album_default.png'
}

def get_media_file(name):
    media = os.path.join(getdatapath(), 'media', media_files[name])
    if not os.path.exists(media):
        media = None
        
    return media

def get_ui_file(name):
    ui_filename = os.path.join(getdatapath(), 'ui', ui_files[name])
    if not os.path.exists(ui_filename):
        ui_filename = None
        
    return ui_filename

def get_data_file(*path_segments):
    """Get the full path to a data file.

    Returns the path to a file underneath the data directory (as defined by
    `get_data_path`). Equivalent to os.path.join(get_data_path(),
    *path_segments).
    """
    return os.path.join(getdatapath(), *path_segments)

def getdatapath():
    """Retrieve pithos data path

    This path is by default <pithos_lib_path>/../data/ in trunk
    and /usr/share/pithos in an installed version but this path
    is specified at installation time.
    """

    # get pathname absolute or relative
    if __pithos_data_directory__.startswith('/'):
        pathname = __pithos_data_directory__
    else:
        pathname = os.path.dirname(__file__) + '/' + __pithos_data_directory__

    abs_data_path = os.path.abspath(pathname)
    if os.path.exists(abs_data_path):
        return abs_data_path
    else:
        raise project_path_not_found

if __name__=='__main__':
    print(VERSION)

########NEW FILE########
__FILENAME__ = plugin
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: nil; -*-
### BEGIN LICENSE
# Copyright (C) 2010-2012 Kevin Mehall <km@kevinmehall.net>
#This program is free software: you can redistribute it and/or modify it 
#under the terms of the GNU General Public License version 3, as published 
#by the Free Software Foundation.
#
#This program is distributed in the hope that it will be useful, but 
#WITHOUT ANY WARRANTY; without even the implied warranties of 
#MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR 
#PURPOSE.  See the GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License along 
#with this program.  If not, see <http://www.gnu.org/licenses/>.
### END LICENSE

import logging
import glob
import os

class PithosPlugin(object):
    _PITHOS_PLUGIN = True # used to find the plugin class in a module
    preference = None
    def __init__(self, name, window):
        self.name = name
        self.window = window
        self.prepared = False
        self.enabled = False
        
    def enable(self):
        if not self.prepared:
            self.error = self.on_prepare()
            self.prepared = True
        if not self.error and not self.enabled:
            logging.info("Enabling module %s"%(self.name))
            self.on_enable()
            self.enabled = True
            
    def disable(self):
        if self.enabled:
            logging.info("Disabling module %s"%(self.name))
            self.on_disable()
            self.enabled = False
        
    def on_prepare(self):
        pass
        
    def on_enable(self):
        pass
        
    def on_disable(self):
        pass

class ErrorPlugin(PithosPlugin):
    def __init__(self, name, error):
        logging.error("Error loading plugin %s: %s"%(name, error))
        self.prepared = True
        self.error = error
        self.name = name
        self.enabled = False
        
def load_plugin(name, window):
    try:
        module = __import__('pithos.plugins.'+name)
        module = getattr(module.plugins, name)
        
    except ImportError as e:
        return ErrorPlugin(name, e.message)
        
    # find the class object for the actual plugin
    for key, item in module.__dict__.items():
        if hasattr(item, '_PITHOS_PLUGIN') and key != "PithosPlugin":
            plugin_class = item
            break
    else:
        return ErrorPlugin(name, "Could not find module class")
        
    return plugin_class(name, window)

def load_plugins(window):
    plugins = window.plugins
    prefs = window.preferences
    
    plugins_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "plugins")
    discovered_plugins = [ fname.replace(".py", "") for fname in glob.glob1(plugins_dir, "*.py") if not fname.startswith("__") ]
    
    for name in discovered_plugins:
        if not name in plugins:
            plugin = plugins[name] = load_plugin(name, window)
        else:
            plugin = plugins[name]

        if plugin.preference and prefs.get(plugin.preference, False):
            plugin.enable()
        else:
            plugin.disable()
        

########NEW FILE########
__FILENAME__ = mediakeys
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: nil; -*-
### BEGIN LICENSE
# Copyright (C) 2010-2012 Kevin Mehall <km@kevinmehall.net>
#This program is free software: you can redistribute it and/or modify it 
#under the terms of the GNU General Public License version 3, as published 
#by the Free Software Foundation.
#
#This program is distributed in the hope that it will be useful, but 
#WITHOUT ANY WARRANTY; without even the implied warranties of 
#MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR 
#PURPOSE.  See the GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License along 
#with this program.  If not, see <http://www.gnu.org/licenses/>.
### END LICENSE

from pithos.plugin import PithosPlugin
import sys
import logging

APP_ID = 'Pithos'

class MediaKeyPlugin(PithosPlugin):
    preference = 'enable_mediakeys'
    
    def bind_dbus(self):
        try:
            import dbus
        except ImportError:
            return False
        try:
            bus = dbus.Bus(dbus.Bus.TYPE_SESSION)
            mk = bus.get_object("org.gnome.SettingsDaemon","/org/gnome/SettingsDaemon/MediaKeys")
            mk.GrabMediaPlayerKeys(APP_ID, 0, dbus_interface='org.gnome.SettingsDaemon.MediaKeys')
            mk.connect_to_signal("MediaPlayerKeyPressed", self.mediakey_pressed)
            logging.info("Bound media keys with DBUS")
            self.method = 'dbus'
            return True
        except dbus.DBusException:
            return False
            
    def mediakey_pressed(self, app, action):
       if app == APP_ID:
            if action == 'Play':
                self.window.playpause_notify()
            elif action == 'Next':
                self.window.next_song()
            elif action == 'Stop':
                self.window.user_pause()
            elif action == 'Previous':
                self.window.bring_to_top()
            
    def bind_keybinder(self):
        try:
            import gi
            gi.require_version('Keybinder', '3.0')
            # Gdk needed for Keybinder
            from gi.repository import Keybinder, Gdk
            Keybinder.init()
        except:
            return False
        
        Keybinder.bind('XF86AudioPlay', self.window.playpause, None)
        Keybinder.bind('XF86AudioStop', self.window.user_pause, None)
        Keybinder.bind('XF86AudioNext', self.window.next_song, None)
        Keybinder.bind('XF86AudioPrev', self.window.bring_to_top, None)
        
        logging.info("Bound media keys with keybinder")
        self.method = 'keybinder'
        return True

    def kbevent(self, event):
        if event.KeyID == 179 or event.Key == 'Media_Play_Pause':
            self.window.playpause_notify()
        if event.KeyID == 176 or event.Key == 'Media_Next_Track':
            self.window.next_song()
        return True

    def bind_win32(self):
        try:
            import pyHook
        except ImportError:
            logging.warning('Please install PyHook: http://www.lfd.uci.edu/~gohlke/pythonlibs/#pyhook')
            return False
        self.hookman = pyHook.HookManager()
        self.hookman.KeyDown = self.kbevent
        self.hookman.HookKeyboard()
        return True
        
    def on_enable(self):
        if sys.platform == 'win32':
            self.bind_win32() or logging.error("Could not bind media keys")
        else:
            self.bind_dbus() or self.bind_keybinder() or logging.error("Could not bind media keys")
        
    def on_disable(self):
        logging.error("Not implemented: Can't disable media keys")

########NEW FILE########
__FILENAME__ = notification_icon
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: nil; -*-
### BEGIN LICENSE
# Copyright (C) 2010-2012 Kevin Mehall <km@kevinmehall.net>
#This program is free software: you can redistribute it and/or modify it 
#under the terms of the GNU General Public License version 3, as published 
#by the Free Software Foundation.
#
#This program is distributed in the hope that it will be useful, but 
#WITHOUT ANY WARRANTY; without even the implied warranties of 
#MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR 
#PURPOSE.  See the GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License along 
#with this program.  If not, see <http://www.gnu.org/licenses/>.
### END LICENSE

import os
from gi.repository import Gtk
from pithos.pithosconfig import get_data_file
from pithos.plugin import PithosPlugin

# Use appindicator if on Unity and installed
try:
    if os.environ['XDG_CURRENT_DESKTOP'] == 'Unity':
        from gi.repository import AppIndicator3 as AppIndicator
        indicator_capable = True
    else:
        indicator_capable = False
except:
    indicator_capable = False

class PithosNotificationIcon(PithosPlugin):    
    preference = 'show_icon'
            
    def on_prepare(self):
        if indicator_capable:
            self.ind = AppIndicator.Indicator.new_with_path("pithos-tray-icon", \
                                  "pithos-tray-icon", \
                                   AppIndicator.IndicatorCategory.APPLICATION_STATUS, \
                                   get_data_file('media'))
    
    def on_enable(self):
        self.visible = True
        self.delete_callback_handle = self.window.connect("delete-event", self.toggle_visible)
        self.state_callback_handle = self.window.connect("play-state-changed", self.play_state_changed)
        self.song_callback_handle = self.window.connect("song-changed", self.song_changed)
        
        if indicator_capable:
            self.ind.set_status(AppIndicator.IndicatorStatus.ACTIVE)
        else:
            icon_info = Gtk.IconTheme.lookup_icon (Gtk.IconTheme.get_default(), 'pithos-tray-icon', 48, 0)
            if icon_info and Gtk.IconInfo.get_filename (icon_info):
                filename = Gtk.IconInfo.get_filename (icon_info)
            else:
                filename = get_data_file('media', 'pithos-tray-icon.png')

            self.statusicon = Gtk.StatusIcon.new ()
            self.statusicon.set_from_file (filename)
            self.statusicon.connect('activate', self.toggle_visible)
        
        self.build_context_menu()

    def scroll(self, steps):
        if indicator_capable:
            direction = steps.value_nick
        else:
            direction = steps.direction.value_nick

        if direction == 'down':
            self.window.adjust_volume(-1)
        elif direction == 'up':
            self.window.adjust_volume(+1)

    def build_context_menu(self):
        menu = Gtk.Menu()
        
        def button(text, action, icon=None):
            if icon == 'check':
                item = Gtk.CheckMenuItem(text)
                item.set_active(True)
            elif icon:
                item = Gtk.ImageMenuItem(text)
                item.set_image(Gtk.Image.new_from_stock(icon, Gtk.IconSize.MENU))
            else:
                item = Gtk.MenuItem(text)
            item.connect('activate', action) 
            item.show()
            menu.append(item)
            return item
        
        if indicator_capable:
            # We have to add another entry for show / hide Pithos window
            self.visible_check = button("Show Pithos", self._toggle_visible, 'check')
        
        self.playpausebtn = button("Pause", self.window.playpause, Gtk.STOCK_MEDIA_PAUSE)
        button("Skip",  self.window.next_song,                     Gtk.STOCK_MEDIA_NEXT)
        button("Love",  (lambda *i: self.window.love_song()),      Gtk.STOCK_ABOUT)
        button("Ban",   (lambda *i: self.window.ban_song()),       Gtk.STOCK_CANCEL)
        button("Tired", (lambda *i: self.window.tired_song()),     Gtk.STOCK_JUMP_TO)
        button("Quit",  self.window.quit,                          Gtk.STOCK_QUIT )

        # connect our new menu to the statusicon or the appindicator
        if indicator_capable:
            self.ind.set_menu(menu)
            # Disabled because of https://bugs.launchpad.net/variety/+bug/1071598
            #self.ind.connect('scroll-event', lambda _x, _y, steps: self.scroll(steps))
        else:
            self.statusicon.connect('popup-menu', self.context_menu, menu)
            self.statusicon.connect('scroll-event', lambda _, steps: self.scroll(steps))

        self.menu = menu


    def play_state_changed(self, window, playing):
        """ play or pause and rotate the text """
        
        button = self.playpausebtn
        if not playing:
            button.set_label("Play")
            button.set_image(Gtk.Image.new_from_stock(Gtk.STOCK_MEDIA_PLAY, Gtk.IconSize.MENU))

        else:
            button.set_label("Pause")
            button.set_image(Gtk.Image.new_from_stock(Gtk.STOCK_MEDIA_PAUSE, Gtk.IconSize.MENU))
            
        if indicator_capable: # menu needs to be reset to get updated icon
            self.ind.set_menu(self.menu)

    def song_changed(self, window, song):
        if not indicator_capable:
            self.statusicon.set_tooltip_text("%s by %s"%(song.title, song.artist))
        
    def _toggle_visible(self, *args):
        if self.visible:
            self.window.hide()
        else:
            self.window.bring_to_top()
        
        self.visible = not self.visible
        
    def toggle_visible(self, *args):
        if hasattr(self, 'visible_check'):
            self.visible_check.set_active(not self.visible)
        else:
            self._toggle_visible()
        
        return True

    def context_menu(self, widget, button, time, data=None): 
       if button == 3: 
           if data: 
               data.show_all() 
               data.popup(None, None, None, None, 3, time)
    
    def on_disable(self):
        if indicator_capable:
            self.ind.set_status(AppIndicator.IndicatorStatus.PASSIVE)
        else:
            self.statusicon.set_visible(False)
            
        self.window.disconnect(self.delete_callback_handle)
        self.window.disconnect(self.state_callback_handle)
        self.window.disconnect(self.song_callback_handle)
        
        # Pithos window needs to be reconnected to on_destro()
        self.window.connect('delete-event',self.window.on_destroy)


########NEW FILE########
__FILENAME__ = notify
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: nil; -*-
### BEGIN LICENSE
# Copyright (C) 2010-2012 Kevin Mehall <km@kevinmehall.net>
#This program is free software: you can redistribute it and/or modify it 
#under the terms of the GNU General Public License version 3, as published 
#by the Free Software Foundation.
#
#This program is distributed in the hope that it will be useful, but 
#WITHOUT ANY WARRANTY; without even the implied warranties of 
#MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR 
#PURPOSE.  See the GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License along 
#with this program.  If not, see <http://www.gnu.org/licenses/>.
### END LICENSE

import logging
import html
from pithos.plugin import PithosPlugin
from pithos.pithosconfig import get_data_file
from gi.repository import (GLib, Gtk)

class NotifyPlugin(PithosPlugin):
    preference = 'notify'

    has_notify = False
    supports_actions = False

    def on_prepare(self):
        try:
            from gi.repository import Notify
            self.has_notify = True
        except ImportError:
            logging.warning ("libnotify not found.")
            return

        # Work-around Ubuntu's incompatible workaround for Gnome's API breaking mistake.
        # https://bugzilla.gnome.org/show_bug.cgi?id=702390
        old_add_action = Notify.Notification.add_action
        def new_add_action(*args):
            try:
                old_add_action(*args)
            except TypeError:
                old_add_action(*(args + (None,)))
        Notify.Notification.add_action = new_add_action

        Notify.init('Pithos')
        self.notification = Notify.Notification()
        self.notification.set_category('x-gnome.music')
        self.notification.set_hint_string('desktop-icon', 'pithos')

        caps = Notify.get_server_caps()
        if 'actions' in caps:
            logging.info('Notify supports actions')
            self.supports_actions = True

        if 'action-icons' in caps:
            self.notification.set_hint('action-icons', GLib.Variant.new_boolean(True))

        # TODO: On gnome this can replace the tray icon, just need to add love/hate buttons
        #if 'persistence' in caps:
        #    self.notification.set_hint('resident', GLib.Variant.new_boolean(True))

    def on_enable(self):
        if self.has_notify:
            self.song_callback_handle = self.window.connect("song-changed", self.song_changed)
            self.state_changed_handle = self.window.connect("user-changed-play-state", self.playstate_changed)

    def set_actions(self, playing=True):
        self.notification.clear_actions()

        pause_action = 'media-playback-pause'
        play_action = 'media-playback-start'
        skip_action = 'media-skip-forward'

        if Gtk.Widget.get_default_direction() == Gtk.TextDirection.RTL:
            play_action += '-rtl'
            skip_action += '-rtl'

        if playing:
            self.notification.add_action(pause_action, 'Pause',
                                         self.notification_playpause_cb, None)
        else:
            self.notification.add_action(play_action, 'Play',
                                         self.notification_playpause_cb, None)

        self.notification.add_action(skip_action, 'Skip',
                                     self.notification_skip_cb, None)

    def set_notification(self, song, playing=True):
        if self.supports_actions:
            self.set_actions(playing)

        if song.art_pixbuf:
            self.notification.set_image_from_pixbuf(song.art_pixbuf)
        else:
            self.notification.set_hint('image-data', None)

        msg = html.escape('by {} from {}'.format(song.artist, song.album))
        self.notification.update(song.title, msg, 'audio-x-generic')
        self.notification.show()

    def notification_playpause_cb(self, notification, action, data, ignore=None):
        self.window.playpause_notify()

    def notification_skip_cb(self, notification, action, data, ignore=None):
        self.window.next_song()

    def song_changed(self, window,  song):
        if not self.window.is_active():
            GLib.idle_add(self.set_notification, window.current_song)

    def playstate_changed(self, window, state):
        if not self.window.is_active():
            GLib.idle_add(self.set_notification, window.current_song, state)

    def on_disable(self):
        if self.has_notify:
            self.window.disconnect(self.song_callback_handle)
            self.window.disconnect(self.state_changed_handle)

########NEW FILE########
__FILENAME__ = screensaver_pause
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: nil; -*-
### BEGIN LICENSE
# Copyright (C) 2010-2012 Kevin Mehall <km@kevinmehall.net>
#This program is free software: you can redistribute it and/or modify it 
#under the terms of the GNU General Public License version 3, as published 
#by the Free Software Foundation.
#
#This program is distributed in the hope that it will be useful, but 
#WITHOUT ANY WARRANTY; without even the implied warranties of 
#MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR 
#PURPOSE.  See the GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License along 
#with this program.  If not, see <http://www.gnu.org/licenses/>.
### END LICENSE

from pithos.plugin import PithosPlugin
import logging


class ScreenSaverPausePlugin(PithosPlugin):
    preference = 'enable_screensaverpause'

    session_bus = None
    
    def bind_session_bus(self):
        try:
            import dbus
        except ImportError:
            return False

        try:
            self.session_bus = dbus.SessionBus()
            return True
        except dbus.DBusException:
            return False
        
    def on_enable(self):
        if not self.bind_session_bus():
            logging.error("Could not bind session bus")
            return
        self.connect_events() or logging.error("Could not connect events")

    def on_disable(self):
        if self.session_bus:
            self.disconnect_events()

        self.session_bus = None

    def connect_events(self):
        try:
            self.session_bus.add_signal_receiver(self.playPause, 'ActiveChanged', 'org.gnome.ScreenSaver')
            self.session_bus.add_signal_receiver(self.playPause, 'ActiveChanged', 'org.cinnamon.ScreenSaver')
            self.session_bus.add_signal_receiver(self.playPause, 'ActiveChanged', 'org.freedesktop.ScreenSaver')
            return True
        except dbus.DBusException:
            logging.info("Enable failed")
            return False

    def disconnect_events(self):
        try:
            self.session_bus.remove_signal_receiver(self.playPause, 'ActiveChanged', 'org.gnome.ScreenSaver')
            self.session_bus.remove_signal_receiver(self.playPause, 'ActiveChanged', 'org.cinnamon.ScreenSaver')
            self.session_bus.remove_signal_receiver(self.playPause, 'ActiveChanged', 'org.freedesktop.ScreenSaver')
            return True
        except dbus.DBusException:
            return False
            
    
    def playPause(self,state):
        if not state:
            if self.wasplaying:
                self.window.user_play()
        else:
            self.wasplaying = self.window.playing
            self.window.pause()

########NEW FILE########
__FILENAME__ = scrobble
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: nil; -*-
### BEGIN LICENSE
# Copyright (C) 2010-2012 Kevin Mehall <km@kevinmehall.net>
#This program is free software: you can redistribute it and/or modify it 
#under the terms of the GNU General Public License version 3, as published 
#by the Free Software Foundation.
#
#This program is distributed in the hope that it will be useful, but 
#WITHOUT ANY WARRANTY; without even the implied warranties of 
#MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR 
#PURPOSE.  See the GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License along 
#with this program.  If not, see <http://www.gnu.org/licenses/>.
### END LICENSE

import pylast
import logging
from pithos.gobject_worker import GObjectWorker
from pithos.plugin import PithosPlugin
from pithos.util import open_browser

#getting an API account: http://www.last.fm/api/account
API_KEY = '997f635176130d5d6fe3a7387de601a8'
API_SECRET = '3243b876f6bf880b923a3c9fb955720c'

#client id, client version info: http://www.last.fm/api/submissions#1.1
CLIENT_ID = 'pth'
CLIENT_VERSION = '1.0'

_worker = None
def get_worker():
    # so it can be shared between the plugin and the authorizer
    global _worker
    if not _worker:
        _worker = GObjectWorker()
    return _worker

class LastfmPlugin(PithosPlugin):
    preference='lastfm_key'
    
    def on_prepare(self):
        self.worker = get_worker()

    def on_enable(self):
        self.connect(self.window.preferences['lastfm_key'])
        self.song_ended_handle = self.window.connect('song-ended', self.song_ended)
        self.song_changed_handle = self.window.connect('song-changed', self.song_changed)
        
    def on_disable(self):
        self.window.disconnect(self.song_ended_handle)
        self.window.disconnect(self.song_rating_changed_handle)
        self.window.disconnect(self.song_changed_handle)
        
    def song_ended(self, window, song):
        self.scrobble(song)
        
    def connect(self, session_key):
        self.network = pylast.get_lastfm_network(
            api_key=API_KEY, api_secret=API_SECRET,
            session_key = session_key
        )
        self.scrobbler = self.network.get_scrobbler(CLIENT_ID, CLIENT_VERSION)
     
    def song_changed(self, window, song):
        self.worker.send(self.scrobbler.report_now_playing, (song.artist, song.title, song.album))
        
    def send_rating(self, song, rating):
        if song.rating:
            track = self.network.get_track(song.artist, song.title)
            if rating == 'love':
                self.worker.send(track.love)
            elif rating == 'ban':
                self.worker.send(track.ban)
            logging.info("Sending song rating to last.fm")

    def scrobble(self, song):
        if song.duration > 30 and (song.position > 240 or song.position > song.duration/2):
            logging.info("Scrobbling song")
            mode = pylast.SCROBBLE_MODE_PLAYED
            source = pylast.SCROBBLE_SOURCE_PERSONALIZED_BROADCAST
            self.worker.send(self.scrobbler.scrobble, (song.artist, song.title, int(song.start_time), source, mode, song.duration, song.album))            


class LastFmAuth:
    def __init__(self, d,  prefname, button):
        self.button = button
        self.dict = d
        self.prefname = prefname
        
        self.auth_url= False
        self.set_button_text()
        self.button.connect('clicked', self.clicked)
    
    @property
    def enabled(self):
        return self.dict[self.prefname]
    
    def setkey(self, key):
        self.dict[self.prefname] = key
        self.set_button_text()
        
    def set_button_text(self):
        self.button.set_sensitive(True)
        if self.auth_url:
            self.button.set_label("Click once authorized on web site")
        elif self.enabled:
            self.button.set_label("Disable")
        else:
            self.button.set_label("Authorize")
            
    def clicked(self, *ignore):
        if self.auth_url:
            def err(e):
                logging.error(e)
                self.set_button_text()

            get_worker().send(self.sg.get_web_auth_session_key, (self.auth_url,), self.setkey, err) 
            self.button.set_label("Checking...")
            self.button.set_sensitive(False)
            self.auth_url = False
                
        elif self.enabled:
            self.setkey(False)
        else:
            self.network = pylast.get_lastfm_network(api_key=API_KEY, api_secret=API_SECRET)
            self.sg = pylast.SessionKeyGenerator(self.network)
            
            def callback(url):
                self.auth_url = url
                self.set_button_text()
                open_browser(self.auth_url)
            
            get_worker().send(self.sg.get_web_auth_url, (), callback)
            self.button.set_label("Connecting...")
            self.button.set_sensitive(False)
            
            
            
        

########NEW FILE########
__FILENAME__ = PreferencesPithosDialog
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: nil; -*-
### BEGIN LICENSE
# Copyright (C) 2010 Kevin Mehall <km@kevinmehall.net>
#This program is free software: you can redistribute it and/or modify it
#under the terms of the GNU General Public License version 3, as published
#by the Free Software Foundation.
#
#This program is distributed in the hope that it will be useful, but
#WITHOUT ANY WARRANTY; without even the implied warranties of
#MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR
#PURPOSE.  See the GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License along
#with this program.  If not, see <http://www.gnu.org/licenses/>.
### END LICENSE

import sys
import os
import stat
import logging

from gi.repository import Gtk
from gi.repository import GObject
from gi.repository import GLib

from .pithosconfig import get_ui_file
from .pandora.data import *
from .plugins.scrobble import LastFmAuth

pacparser_imported = False
try:
    import pacparser
    pacparser_imported = True
except ImportError:
    logging.info("Could not import python-pacparser.")

config_home = GLib.get_user_config_dir()
configfilename = os.path.join(config_home, 'pithos.ini')

class PreferencesPithosDialog(Gtk.Dialog):
    __gtype_name__ = "PreferencesPithosDialog"
    prefernces = {}

    def __init__(self):
        """__init__ - This function is typically not called directly.
        Creation of a PreferencesPithosDialog requires reading the associated ui
        file and parsing the ui definition extrenally,
        and then calling PreferencesPithosDialog.finish_initializing().

        Use the convenience function NewPreferencesPithosDialog to create
        NewAboutPithosDialog objects.
        """

        pass

    def finish_initializing(self, builder):
        """finish_initalizing should be called after parsing the ui definition
        and creating a AboutPithosDialog object with it in order to finish
        initializing the start of the new AboutPithosDialog instance.
        """

        # get a reference to the builder and set up the signals
        self.builder = builder
        self.builder.connect_signals(self)

        # initialize the "Audio Quality" combobox backing list
        audio_quality_combo = self.builder.get_object('prefs_audio_quality')
        fmt_store = Gtk.ListStore(GObject.TYPE_STRING, GObject.TYPE_STRING)
        for audio_quality in valid_audio_formats:
            fmt_store.append(audio_quality)
        audio_quality_combo.set_model(fmt_store)
        render_text = Gtk.CellRendererText()
        audio_quality_combo.pack_start(render_text, True)
        audio_quality_combo.add_attribute(render_text, "text", 1)

        self.__load_preferences()


    def get_preferences(self):
        """get_preferences  - returns a dictionary object that contains
        preferences for pithos.
        """
        return self.__preferences

    def __load_preferences(self):
        #default preferences that will be overwritten if some are saved
        self.__preferences = {
            "username":'',
            "password":'',
            "notify":True,
            "last_station_id":None,
            "proxy":'',
            "control_proxy":'',
            "control_proxy_pac":'',
            "show_icon": False,
            "lastfm_key": False,
            "enable_mediakeys":True,
            "enable_screensaverpause":False,
            "volume": 1.0,
            # If set, allow insecure permissions. Implements CVE-2011-1500
            "unsafe_permissions": False,
            "audio_quality": default_audio_quality,
            "pandora_one": False,
            "force_client": None,
        }

        try:
            f = open(configfilename)
        except IOError:
            f = []

        for line in f:
            sep = line.find('=')
            key = line[:sep]
            val = line[sep+1:].strip()
            if val == 'None': val=None
            elif val == 'False': val=False
            elif val == 'True': val=True
            self.__preferences[key]=val

        if 'audio_format' in self.__preferences:
            # Pithos <= 0.3.17, replaced by audio_quality
            del self.__preferences['audio_format']

        if not pacparser_imported and self.__preferences['control_proxy_pac'] != '':
            self.__preferences['control_proxy_pac'] = ''

        self.setup_fields()

    def fix_perms(self):
        """Apply new file permission rules, fixing CVE-2011-1500.
        If the file is 0644 and if "unsafe_permissions" is not True,
           chmod 0600
        If the file is world-readable (but not exactly 0644) and if
        "unsafe_permissions" is not True:
           chmod o-rw
        """
        def complain_unsafe():
            # Display this message iff permissions are unsafe, which is why
            #   we don't just check once and be done with it.
            logging.warning("Ignoring potentially unsafe permissions due to user override.")

        changed = False

        if os.path.exists(configfilename):
            # We've already written the file, get current permissions
            config_perms = stat.S_IMODE(os.stat(configfilename).st_mode)
            if config_perms == (stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH):
                if self.__preferences["unsafe_permissions"]:
                    return complain_unsafe()
                # File is 0644, set to 0600
                logging.warning("Removing world- and group-readable permissions, to fix CVE-2011-1500 in older software versions. To force, set unsafe_permissions to True in pithos.ini.")
                os.chmod(configfilename, stat.S_IRUSR | stat.S_IWUSR)
                changed = True

            elif config_perms & stat.S_IROTH:
                if self.__preferences["unsafe_permissions"]:
                    return complain_unsafe()
                # File is o+r,
                logging.warning("Removing world-readable permissions, configuration should not be globally readable. To force, set unsafe_permissions to True in pithos.ini.")
                config_perms ^= stat.S_IROTH
                os.chmod(configfilename, config_perms)
                changed = True

            if config_perms & stat.S_IWOTH:
                if self.__preferences["unsafe_permissions"]:
                    return complain_unsafe()
                logging.warning("Removing world-writable permissions, configuration should not be globally writable. To force, set unsafe_permissions to True in pithos.ini.")
                config_perms ^= stat.S_IWOTH
                os.chmod(configfilename, config_perms)
                changed = True

        return changed

    def save(self):
        existed = os.path.exists(configfilename)
        f = open(configfilename, 'w')

        if not existed:
            # make the file owner-readable and writable only
            os.fchmod(f.fileno(), (stat.S_IRUSR | stat.S_IWUSR))

        for key in self.__preferences:
            f.write('%s=%s\n'%(key, self.__preferences[key]))
        f.close()

    def setup_fields(self):
        self.builder.get_object('prefs_username').set_text(self.__preferences["username"])
        self.builder.get_object('prefs_password').set_text(self.__preferences["password"])
        self.builder.get_object('checkbutton_pandora_one').set_active(self.__preferences["pandora_one"])
        self.builder.get_object('prefs_proxy').set_text(self.__preferences["proxy"])
        self.builder.get_object('prefs_control_proxy').set_text(self.__preferences["control_proxy"])
        self.builder.get_object('prefs_control_proxy_pac').set_text(self.__preferences["control_proxy_pac"])
        if not pacparser_imported:
            self.builder.get_object('prefs_control_proxy_pac').set_sensitive(False)
            self.builder.get_object('prefs_control_proxy_pac').set_tooltip_text("Please install python-pacparser")

        audio_quality_combo = self.builder.get_object('prefs_audio_quality')
        for row in audio_quality_combo.get_model():
            if row[0] == self.__preferences["audio_quality"]:
                audio_quality_combo.set_active_iter(row.iter)
                break

        self.builder.get_object('checkbutton_notify').set_active(self.__preferences["notify"])
        self.builder.get_object('checkbutton_screensaverpause').set_active(self.__preferences["enable_screensaverpause"])
        self.builder.get_object('checkbutton_icon').set_active(self.__preferences["show_icon"])

        self.lastfm_auth = LastFmAuth(self.__preferences, "lastfm_key", self.builder.get_object('lastfm_btn'))

    def ok(self, widget, data=None):
        """ok - The user has elected to save the changes.
        Called before the dialog returns Gtk.RESONSE_OK from run().
        """

        self.__preferences["username"] = self.builder.get_object('prefs_username').get_text()
        self.__preferences["password"] = self.builder.get_object('prefs_password').get_text()
        self.__preferences["pandora_one"] = self.builder.get_object('checkbutton_pandora_one').get_active()
        self.__preferences["proxy"] = self.builder.get_object('prefs_proxy').get_text()
        self.__preferences["control_proxy"] = self.builder.get_object('prefs_control_proxy').get_text()
        self.__preferences["control_proxy_pac"] = self.builder.get_object('prefs_control_proxy_pac').get_text()
        self.__preferences["notify"] = self.builder.get_object('checkbutton_notify').get_active()
        self.__preferences["enable_screensaverpause"] = self.builder.get_object('checkbutton_screensaverpause').get_active()
        self.__preferences["show_icon"] = self.builder.get_object('checkbutton_icon').get_active()

        audio_quality = self.builder.get_object('prefs_audio_quality')
        active_idx = audio_quality.get_active()
        if active_idx != -1: # ignore unknown format
            self.__preferences["audio_quality"] = audio_quality.get_model()[active_idx][0]

        self.save()

    def cancel(self, widget, data=None):
        """cancel - The user has elected cancel changes.
        Called before the dialog returns Gtk.ResponseType.CANCEL for run()
        """

        self.setup_fields() # restore fields to previous values
        pass


def NewPreferencesPithosDialog():
    """NewPreferencesPithosDialog - returns a fully instantiated
    PreferencesPithosDialog object. Use this function rather than
    creating a PreferencesPithosDialog instance directly.
    """

    builder = Gtk.Builder()
    builder.add_from_file(get_ui_file('preferences'))
    dialog = builder.get_object("preferences_pithos_dialog")
    dialog.finish_initializing(builder)
    return dialog

if __name__ == "__main__":
    dialog = NewPreferencesPithosDialog()
    dialog.show()
    Gtk.main()

########NEW FILE########
__FILENAME__ = SearchDialog
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: nil; -*-
### BEGIN LICENSE
# Copyright (C) 2010-2012 Kevin Mehall <km@kevinmehall.net>
#This program is free software: you can redistribute it and/or modify it 
#under the terms of the GNU General Public License version 3, as published 
#by the Free Software Foundation.
#
#This program is distributed in the hope that it will be useful, but 
#WITHOUT ANY WARRANTY; without even the implied warranties of 
#MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR 
#PURPOSE.  See the GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License along 
#with this program.  If not, see <http://www.gnu.org/licenses/>.
### END LICENSE

import sys
import os
import html
from gi.repository import Gtk
from gi.repository import GObject

from .pithosconfig import get_ui_file

class SearchDialog(Gtk.Dialog):
    __gtype_name__ = "SearchDialog"

    def __init__(self):
        """__init__ - This function is typically not called directly.
        Creation of a SearchDialog requires redeading the associated ui
        file and parsing the ui definition extrenally, 
        and then calling SearchDialog.finish_initializing().
    
        Use the convenience function NewSearchDialog to create 
        a SearchDialog object.
    
        """
        pass

    def finish_initializing(self, builder, worker_run):
        """finish_initalizing should be called after parsing the ui definition
        and creating a SearchDialog object with it in order to finish
        initializing the start of the new SearchDialog instance.
    
        """
        #get a reference to the builder and set up the signals
        self.builder = builder
        self.builder.connect_signals(self)
        
        self.entry = self.builder.get_object('entry')
        self.treeview = self.builder.get_object('treeview')
        self.okbtn = self.builder.get_object('okbtn')
        self.searchbtn = self.builder.get_object('searchbtn')
        self.model = Gtk.ListStore(GObject.TYPE_PYOBJECT, str)
        self.treeview.set_model(self.model)
        
        self.worker_run = worker_run
        
        self.result = None


    def ok(self, widget, data=None):
        """ok - The user has elected to save the changes.
        Called before the dialog returns Gtk.RESONSE_OK from run().

        """
        

    def cancel(self, widget, data=None):
        """cancel - The user has elected cancel changes.
        Called before the dialog returns Gtk.ResponseType.CANCEL for run()

        """         
        pass
        
    def search_clicked(self, widget):
        self.search(self.entry.get_text())
        
    def search(self, query):
        if not query: return
        def callback(results):
            self.model.clear()
            for i in results:
                if i.resultType is 'song':
                    mk = "<b>%s</b> by %s"%(html.escape(i.title), html.escape(i.artist))
                elif i.resultType is 'artist':
                    mk = "<b>%s</b> (artist)"%(html.escape(i.name))
                self.model.append((i, mk))
            self.treeview.show()
            self.searchbtn.set_sensitive(True)
            self.searchbtn.set_label("Search")
        self.worker_run('search', (query,), callback, "Searching...")
        self.searchbtn.set_sensitive(False)
        self.searchbtn.set_label("Searching...")
        
    def get_selected(self):
        sel = self.treeview.get_selection().get_selected()
        if sel[1]:
            return self.treeview.get_model().get_value(sel[1], 0)
            
    def cursor_changed(self, *ignore):
        self.result = self.get_selected()
        self.okbtn.set_sensitive(not not self.result)
        

def NewSearchDialog(worker_run):
    """NewSearchDialog - returns a fully instantiated
    dialog-camel_case_nameDialog object. Use this function rather than
    creating SearchDialog instance directly.
    
    """

    builder = Gtk.Builder()
    builder.add_from_file(get_ui_file('search'))    
    dialog = builder.get_object("search_dialog")
    dialog.finish_initializing(builder, worker_run)
    return dialog

if __name__ == "__main__":
    dialog = NewSearchDialog()
    dialog.show()
    Gtk.main()


########NEW FILE########
__FILENAME__ = StationsDialog
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: nil; -*-
### BEGIN LICENSE
# Copyright (C) 2010-2012 Kevin Mehall <km@kevinmehall.net>
#This program is free software: you can redistribute it and/or modify it 
#under the terms of the GNU General Public License version 3, as published 
#by the Free Software Foundation.
#
#This program is distributed in the hope that it will be useful, but 
#WITHOUT ANY WARRANTY; without even the implied warranties of 
#MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR 
#PURPOSE.  See the GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License along 
#with this program.  If not, see <http://www.gnu.org/licenses/>.
### END LICENSE

import sys
import os
from gi.repository import Gtk
import logging

from .pithosconfig import get_ui_file
from .util import open_browser
from . import SearchDialog

class StationsDialog(Gtk.Dialog):
    __gtype_name__ = "StationsDialog"

    def __init__(self):
        """__init__ - This function is typically not called directly.
        Creation of a StationsDialog requires redeading the associated ui
        file and parsing the ui definition extrenally, 
        and then calling StationsDialog.finish_initializing().
    
        Use the convenience function NewStationsDialog to create 
        a StationsDialog object.
    
        """
        pass

    def finish_initializing(self, builder, pithos):
        """finish_initalizing should be called after parsing the ui definition
        and creating a StationsDialog object with it in order to finish
        initializing the start of the new StationsDialog instance.
    
        """
        #get a reference to the builder and set up the signals
        self.builder = builder
        self.builder.connect_signals(self)
        
        self.pithos = pithos
        self.model = pithos.stations_model
        self.worker_run = pithos.worker_run
        self.quickmix_changed = False
        self.searchDialog = None
        
        self.modelfilter = self.model.filter_new()
        self.modelfilter.set_visible_func(lambda m, i, d: m.get_value(i, 0) and not  m.get_value(i, 0).isQuickMix)

        self.modelsortable = Gtk.TreeModelSort.sort_new_with_model(self.modelfilter)
        """
        @todo Leaving it as sorting by date added by default. 
        Probably should make a radio select in the window or an option in program options for user preference
        """
#        self.modelsortable.set_sort_column_id(1, Gtk.SortType.ASCENDING)
        
        self.treeview = self.builder.get_object("treeview")
        self.treeview.set_model(self.modelsortable)
        self.treeview.connect('button_press_event', self.on_treeview_button_press_event)
        
        name_col   = Gtk.TreeViewColumn()
        name_col.set_title("Name")
        render_text = Gtk.CellRendererText()
        render_text.set_property('editable', True)
        render_text.connect("edited", self.station_renamed)
        name_col.pack_start(render_text, True)
        name_col.add_attribute(render_text, "text", 1)
        name_col.set_expand(True)
        name_col.set_sort_column_id(1)
        self.treeview.append_column(name_col)
        
        qm_col   = Gtk.TreeViewColumn()
        qm_col.set_title("In QuickMix")
        render_toggle = Gtk.CellRendererToggle()
        qm_col.pack_start(render_toggle, True)
        def qm_datafunc(column, cell, model, iter, data=None):
            if model.get_value(iter,0).useQuickMix:
                cell.set_active(True)
            else:
                cell.set_active(False)
        qm_col.set_cell_data_func(render_toggle, qm_datafunc)
        render_toggle.connect("toggled", self.qm_toggled)
        self.treeview.append_column(qm_col)
        
        self.station_menu = builder.get_object("station_menu")
        
    def qm_toggled(self, renderer, path):
        station = self.modelfilter[path][0]
        station.useQuickMix = not station.useQuickMix
        self.quickmix_changed = True
        
    def station_renamed(self, cellrenderertext, path, new_text):
        station = self.modelfilter[path][0]
        self.worker_run(station.rename, (new_text,), context='net', message="Renaming Station...")
        self.model[self.modelfilter.convert_path_to_child_path(Gtk.TreePath(path))][1] = new_text
        
    def selected_station(self):
        sel = self.treeview.get_selection().get_selected()
        if sel:
            return self.treeview.get_model().get_value(sel[1], 0)
           
    def on_treeview_button_press_event(self, treeview, event):
        if event.button == 3:
            x = int(event.x)
            y = int(event.y)
            time = event.time
            pthinfo = treeview.get_path_at_pos(x, y)
            if pthinfo is not None:
                path, col, cellx, celly = pthinfo
                treeview.grab_focus()
                treeview.set_cursor( path, col, 0)
                self.station_menu.popup(None, None, None, None, event.button, time)
            return True
            
    def on_menuitem_listen(self, widget):
        station = self.selected_station()
        self.pithos.station_changed(station)
        self.hide()
        
    def on_menuitem_info(self, widget):
        open_browser(self.selected_station().info_url)
        
    def on_menuitem_rename(self, widget):
        sel = self.treeview.get_selection().get_selected()
        path = self.treeview.get_model().get_path(sel[1])
        self.treeview.set_cursor(path, self.treeview.get_column(0) ,True)
        
    def on_menuitem_delete(self, widget):
        station = self.selected_station()
        
        dialog = self.builder.get_object("delete_confirm_dialog")
        dialog.set_property("text", "Are you sure you want to delete the station \"%s\"?"%(station.name))
        response = dialog.run()
        dialog.hide()
        
        if response:
            self.worker_run(station.delete, context='net', message="Deleting Station...")
            del self.pithos.stations_model[self.pithos.station_index(station)]
            if self.pithos.current_station is station:
                self.pithos.station_changed(self.model[0][0])
                
    def add_station(self, widget):
        if self.searchDialog:
            self.searchDialog.present()
        else:
            self.searchDialog = SearchDialog.NewSearchDialog(self.worker_run)
            self.searchDialog.set_transient_for(self)
            self.searchDialog.show_all()
            self.searchDialog.connect("response", self.add_station_cb)
            
    def refresh_stations(self, widget):
        self.pithos.refresh_stations(self.pithos)
        
    def add_station_cb(self, dialog, response):
        logging.info("in add_station_cb {} {}".format(dialog.result, response))
        if response == 1:
            self.worker_run("add_station_by_music_id", (dialog.result.musicId,), self.station_added, "Creating station...")
        dialog.hide()
        dialog.destroy()
        self.searchDialog = None
        
    def station_added(self, station):
        logging.debug("1 "+ repr(station))
        it = self.model.insert_after(self.model.get_iter(1), (station, station.name))
        logging.debug("2 "+ repr(it))
        self.pithos.station_changed(station)
        logging.debug("3 ")
        self.modelfilter.refilter()
        logging.debug("4")
        self.treeview.set_cursor(0)
        logging.debug("5 ")
        
    def add_genre_station(self, widget):
        """
        This is just a stub for the non-completed buttn
        """
        
    def on_close(self, widget, data=None):
        self.hide()
        
        if self.quickmix_changed:
            self.worker_run("save_quick_mix",  message="Saving QuickMix...")
            self.quickmix_changed = False
        
        logging.info("closed dialog")
        return True

def NewStationsDialog(pithos):
    """NewStationsDialog - returns a fully instantiated
    Dialog object. Use this function rather than
    creating StationsDialog instance directly.
    
    """

    builder = Gtk.Builder()
    builder.add_from_file(get_ui_file('stations'))    
    dialog = builder.get_object("stations_dialog")
    dialog.finish_initializing(builder, pithos)
    return dialog

if __name__ == "__main__":
    dialog = NewStationsDialog()
    dialog.show()
    Gtk.main()


########NEW FILE########
__FILENAME__ = util
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: nil; -*-
### BEGIN LICENSE
# Copyright (C) 2010-2012 Kevin Mehall <km@kevinmehall.net>
#This program is free software: you can redistribute it and/or modify it 
#under the terms of the GNU General Public License version 3, as published 
#by the Free Software Foundation.
#
#This program is distributed in the hope that it will be useful, but 
#WITHOUT ANY WARRANTY; without even the implied warranties of 
#MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR 
#PURPOSE.  See the GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License along 
#with this program.  If not, see <http://www.gnu.org/licenses/>.
### END LICENSE

import logging
import webbrowser
from urllib.parse import splittype, splituser, splitpasswd

def parse_proxy(proxy):
    """ _parse_proxy from urllib """
    scheme, r_scheme = splittype(proxy)
    if not r_scheme.startswith("/"):
        # authority
        scheme = None
        authority = proxy
    else:
        # URL
        if not r_scheme.startswith("//"):
            raise ValueError("proxy URL with no authority: %r" % proxy)
        # We have an authority, so for RFC 3986-compliant URLs (by ss 3.
        # and 3.3.), path is empty or starts with '/'
        end = r_scheme.find("/", 2)
        if end == -1:
            end = None
        authority = r_scheme[2:end]
    userinfo, hostport = splituser(authority)
    if userinfo is not None:
        user, password = splitpasswd(userinfo)
    else:
        user = password = None
    return scheme, user, password, hostport

def open_browser(url):
    logging.info("Opening URL {}".format(url))
    webbrowser.open(url)
    if isinstance(webbrowser.get(), webbrowser.BackgroundBrowser):
        try:
            os.wait() # workaround for http://bugs.python.org/issue5993
        except:
            pass

########NEW FILE########
