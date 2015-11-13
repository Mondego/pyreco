__FILENAME__ = background
# Copyright (c) 2013 Ondrej Kipila <ok100 at openmailbox dot org>
# This work is free. You can redistribute it and/or modify it under the
# terms of the Do What The Fuck You Want To Public License, Version 2,
# as published by Sam Hocevar. See the COPYING file for more details.

"""Classes for normal and Tmux backgrounds."""


import os
import sys
from io import BytesIO

from PIL import Image

import lyvi
from lyvi.utils import check_output


# Get the terminal background color from the 'xrdb' command
for line in check_output('xrdb -query').splitlines():
    if 'background' in line:
        BG_COLOR = line.split(':')[1].strip()
        break
else:
    BG_COLOR = '#FFFFFF'


def pil_image(image):
    """Return the initialized Image class.

    Keyword arguments:
    image -- bytes or Image instance
    """
    if isinstance(image, bytes):
        buf = BytesIO(image)
        return Image.open(buf)
    return image


def blend(image, opacity):
    """Return the image blended with terminal background color.

    Keyword arguments:
    image -- image to blend
    opacity -- opacity of the background color layer
    """
    image = pil_image(image)
    layer = Image.new(image.mode, image.size, BG_COLOR)
    return Image.blend(image, layer, 1 - opacity)


def paste(root, image_to_paste, x, y):
    """Return root image with pasted image.

    Keyword arguments:
    root -- root image
    image_to_paste -- image to paste
    x -- top-left x coordinates of the image to paste
    y -- top-left y coordinates of the image to paste
    """
    root = pil_image(root)
    image_to_paste = pil_image(image_to_paste)
    root.paste(image_to_paste, (x, y))
    return root


def resize(image, x, y):
    """Return the resized image.

    Keyword argumants:
    image -- image to resize
    x -- new x resolution in px
    y -- new y resolution in px
    """
    image = pil_image(image)
    image.thumbnail((x, y), Image.ANTIALIAS)
    return image


class Background:
    ESCAPE_STR_BEG = "\033]20;"
    ESCAPE_STR_END = ";100x100+50+50:op=keep-aspect\a"

    def __init__(self):
        """Initialize the class."""
        self.FILE = os.path.join(lyvi.TEMP, 'lyvi-%s.jpg' % lyvi.PID)
        self.type = lyvi.config['bg_type']
        self.opacity = lyvi.config['bg_opacity']

    def toggle_type(self):
        """Toggle background type."""
        self.type = 'cover' if self.type == 'backdrops' else 'backdrops'
        self.update()

    def _make(self, clean=False):
        """Save the background to a temporary file.

        Keyword arguments:
        clean -- whether the background should be unset
        """
        if (((self.type == 'backdrops' and lyvi.md.backdrops and lyvi.md.artist)
                or (self.type == 'cover' and lyvi.md.cover and lyvi.md.album))
                and not clean):
            image = blend(getattr(lyvi.md, self.type), self.opacity)
        else:
            image = Image.new('RGB', (100, 100), BG_COLOR)
        image.save(self.FILE)

    def _set(self):
        """Set the image file as a terminal background."""
        sys.stdout.write(self.ESCAPE_STR_BEG + self.FILE + self.ESCAPE_STR_END)

    def update(self, clean=False):
        """Update the background.

        Keyword arguments:
        clean -- whether the background should be unset
        """
        self._make(clean=clean)
        self._set()

    def cleanup(self):
        """Unset the background and delete the image file."""
        self.update(clean=True)
        os.remove(self.FILE)


class Tmux:
    """A class which represents Tmux layout and dimensions.

    Properties:
    layout -- a list containing Pane instances representing all tmux panes
    width -- window width in px
    height -- window height in px
    cell -- Cell instance representing a terminal cell
    """
    class Cell:
        """Class used as a placeholder for terminal cell properties.

        Properties:
        w -- cell width in px
        h -- cell height in px
        """
        pass

    class Pane:
        """Class used as a placeholder for pane properties.

        Properties:
        active -- whether the pane is active
        x -- horizontal pane offset from the top left corner of the terminal in cells
        y -- vertical pane offset from the top left corner of the terminal in cells
        w -- pane width in cells
        h -- pane height in cells
        """
        pass

    def __init__(self):
        """Initialize the class and update the class properties."""
        self.cell = self.Cell()
        self.update()

    def _get_layout(self):
        """Return a list containing Pane instances representing all tmux panes."""
        display = check_output('tmux display -p \'#{window_layout}\'')
        for delim in '[]{}':
            display = display.replace(delim, ',')
        layout = [self.Pane()]
        layout[0].w, layout[0].h = (int(a) for a in display.split(',')[1].split('x'))
        display = display.split(',', 1)[1]
        chunks = display.split(',')
        for i in range(0, len(chunks) - 1):
            if 'x' in chunks[i] and 'x' not in chunks[i + 3]:
                layout.append(self.Pane())
                layout[-1].w, layout[-1].h = (int(a) for a in chunks[i].split('x'))
                layout[-1].x = int(chunks[i + 1])
                layout[-1].y = int(chunks[i + 2])
        lsp = check_output('tmux lsp').splitlines()
        for chunk in lsp:
            layout[lsp.index(chunk) + 1].active = 'active' in chunk
        return layout

    def _get_size_px(self):
        """Return a tuple (width, height) with the tmux window dimensions in px."""
        while(True):
            # Use xwininfo command to get the window dimensions
            info = check_output('xwininfo -name ' + lyvi.config['bg_tmux_window_title'])
            try:
                width = int(info.split('Width: ')[1].split('\n')[0])
                height = int(info.split('Height: ')[1].split('\n')[0])
            except IndexError:
                continue
            else:
                return width, height

    def update(self):
        """Set class properties to the actual values."""
        self.layout = self._get_layout()
        self.width, self.height = self._get_size_px()
        self.cell.w = round(self.width / self.layout[0].w)
        self.cell.h = round(self.height / self.layout[0].h)


class TmuxBackground(Background):
    ESCAPE_STR_BEG = "\033Ptmux;\033\033]20;"
    ESCAPE_STR_END = ";100x100+50+50:op=keep-aspect\a\033\\\\"

    def __init__(self):
        """Initialize the class."""
        super().__init__()
        self._tmux = Tmux()

    def _make(self, clean=False):
        self._tmux.update()
        image = Image.new('RGB', (self._tmux.width, self._tmux.height), BG_COLOR)
        if not clean:
            cover = {
                'image': lyvi.md.cover,
                'pane': self._tmux.layout[lyvi.config['bg_tmux_cover_pane'] + 1],
                'underlying': lyvi.config['bg_tmux_cover_underlying']
            }
            backdrops = {
                'image': lyvi.md.backdrops,
                'pane': self._tmux.layout[lyvi.config['bg_tmux_backdrops_pane'] + 1],
                'underlying': lyvi.config['bg_tmux_backdrops_underlying']
            }
            if lyvi.config['bg_tmux_backdrops_pane'] == lyvi.config['bg_tmux_cover_pane']:
                to_paste = [cover if self.type == 'cover' else backdrops]
            else:
                to_paste = [cover, backdrops]
            for t in (t for t in to_paste if t['image']):
                t['image'] = resize(t['image'], t['pane'].w * self._tmux.cell.w,
                                                t['pane'].h * self._tmux.cell.h)
                if t['underlying']:
                    t['image'] = blend(t['image'], self.opacity)
                x1 = t['pane'].x * self._tmux.cell.w
                y1 = t['pane'].y * self._tmux.cell.h
                x2 = (t['pane'].x + t['pane'].w) * self._tmux.cell.w
                y2 = (t['pane'].y + t['pane'].h) * self._tmux.cell.h
                x = round(x1 + (x2 - x1) / 2 - t['image'].size[0] / 2)
                y = round(y1 + (y2 - y1) / 2 - t['image'].size[1] / 2)
                image = paste(image, t['image'], x, y)
        image.save(self.FILE)

########NEW FILE########
__FILENAME__ = config_defaults
# Copyright (c) 2013 Ondrej Kipila <ok100 at openmailbox dot org>
# This work is free. You can redistribute it and/or modify it under the
# terms of the Do What The Fuck You Want To Public License, Version 2,
# as published by Sam Hocevar. See the COPYING file for more details.

"""Default configuration options."""


import os


defaults = {
# Enable autoscroll.
# Type: bool
# Default value: False
'autoscroll': False,

# Enable background. Currently, the background is supported only in urxvt.
# Type: bool
# Default value: False
'bg': False,

# Background opacity.
# Type: float
# Default value: 0.15
'bg_opacity': 0.15,

# A tmux pane where the backdrops are displayed. Panes are numbered from 0.
# To enable tmux support, this option must be set.
# Type: int
# Default value: None
'bg_tmux_backdrops_pane': None,

# Set to True if Lyvi is running in the same pane where backdrops are displayed.
# Type: bool
# Default value: False
'bg_tmux_backdrops_underlying': False,

# A tmux pane where the covers are displayed. Panes are numbered from 0.
# To enable tmux support, this option must be set.
# Type: int
# Default value: None
'bg_tmux_cover_pane': None,

# Set to True if Lyvi is running in the same pane where covers are displayed.
# Type: bool
# Default value: False
'bg_tmux_cover_underlying': False,

# A title of the terminal window running tmux.
# To enable tmux support, this option must be set.
# Type: str
# Default value: None
'bg_tmux_window_title': None,

# Default background type.
# Type: 'cover', 'backdrops'
# Default value: 'cover'
'bg_type': 'cover',

# Try to find player specified with this option first.
# Type: str
# Default value: None
'default_player': None,

# Default view.
# Type: 'lyrics', 'artistbio', 'guitartabs'
# Default value: 'lyrics'
'default_view': 'lyrics',

# Background color of the header.
# Type: str
# Default value: 'default'
'header_bg': 'default',

# Foreground color of the header.
# Type: str
# Default value: 'white'
'header_fg': 'white',

# 'Quit' key.
# Type: str
# Default value: 'q'
'key_quit': 'q',

# 'Reload background' key.
# Type: str
# Default value: 'R'
'key_reload_bg': 'R',

# 'Reload current view' key.
# Type: str
# Default value: 'r'
'key_reload_view': 'r',

# 'Toggle background type' key.
# Type: str
# Default value: 's'
'key_toggle_bg_type': 's',

# 'Toggle view' key.
# Type: str
# Default value: 'a'
'key_toggle_views': 'a',

# 'Toggle UI' key.
# Type: str
# Default value: 'h'
'key_toggle_ui': 'h',

# Path to the mpd configuration file.
# Type: str
# Default value: '~/.mpdconf' or '/etc/mpd.conf'
'mpd_config_file': os.path.join(os.environ['HOME'], '.mpdconf')
    if os.path.exists(os.path.join(os.environ['HOME'], '.mpdconf')) else '/etc/mpd.conf',

# Mpd host.
# Type: str
# Default value: same as MPD_HOST environment variable or 'localhost'
'mpd_host': os.environ['MPD_HOST'] if 'MPD_HOST' in os.environ else 'localhost',

# Mpd port.
# Type: int
# Default value: same as MPD_PORT environment variable or 6600
'mpd_port': os.environ['MPD_PORT'] if 'MPD_PORT' in os.environ else 6600,

# Path to the mplayer configuration directory.
# Type: str
# Default value: '~/.mplayer'
'mplayer_config_dir': os.path.join(os.environ['HOME'], '.mplayer'),

# Path to the saved cover.
# Type: str
# Default value: None
'save_cover': None,

# Path to the saved lyrics.
# Type: str
# Default value: None
'save_lyrics': None,

# Background color of the statusbar.
# Type: str
# Default value: 'default'
'statusbar_bg': 'default',

# Foreground color of the statusbar.
# Type: str
# Default value: 'default'
'statusbar_fg': 'default',

# Background color of the text.
# Type: str
# Default value: 'default'
'text_bg': 'default',

# Foreground color of the text.
# Type: str
# Default value: 'default'
'text_fg': 'default',

# Hide UI by default.
# Type: bool
# Default value: False
'ui_hidden': False,
}

########NEW FILE########
__FILENAME__ = metadata
# Copyright (c) 2013 Ondrej Kipila <ok100 at openmailbox dot org>
# This work is free. You can redistribute it and/or modify it under the
# terms of the Do What The Fuck You Want To Public License, Version 2,
# as published by Sam Hocevar. See the COPYING file for more details.

"""Metadata-related code."""


import os
from threading import Lock

import plyr

import lyvi


class Metadata:
    """A class which holds metadata for the currently playing song."""
    artist = None
    album = None
    title = None
    file = None
    _lyrics = None
    _artistbio = None
    _guitartabs = None
    _backdrops = None
    _cover = None

    @property
    def lyrics(self):
        return self._lyrics

    @lyrics.setter
    def lyrics(self, value):
        """Update ui and save the lyrics."""
        self._lyrics = value
        lyvi.ui.update()
        if lyvi.ui.autoscroll:
            lyvi.ui.autoscroll.reset()
        if lyvi.config['save_lyrics']:
            self.save('lyrics', lyvi.config['save_lyrics_filename'])

    @property
    def artistbio(self):
        return self._artistbio

    @artistbio.setter
    def artistbio(self, value):
        """Update UI."""
        self._artistbio = value
        lyvi.ui.update()

    @property
    def guitartabs(self):
        return self._guitartabs

    @guitartabs.setter
    def guitartabs(self, value):
        """Update UI."""
        self._guitartabs = value
        lyvi.ui.update()

    @property
    def backdrops(self):
        return self._backdrops

    @backdrops.setter
    def backdrops(self, value):
        """Update background."""
        self._backdrops = value
        if lyvi.bg:
            lyvi.bg.update()

    @property
    def cover(self):
        return self._cover

    @cover.setter
    def cover(self, value):
        """Update background and save the cover."""
        self._cover = value
        if lyvi.bg:
            lyvi.bg.update()
        if lyvi.config['save_cover']:
            self.save('cover', lyvi.config['save_cover_filename'])

    def __init__(self):
        """Initialize the class."""
        cache_dir = os.path.join(os.environ['HOME'], '.local/share/lyvi')
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
        self.cache = plyr.Database(cache_dir)
        self.lock = Lock()

    def set_tags(self):
        """Set all tag properties to the actual values."""
        self.artist = lyvi.player.artist
        self.title = lyvi.player.title
        self.album = lyvi.player.album
        self.file = lyvi.player.file

    def reset_tags(self):
        """Set all tag and metadata properties to None."""
        self.artist = self.title = self.album = self.file = None
        self.lyrics = self.artistbio = self.guitartabs = None
        self.backdrops = self.cover = None

    def delete(self, type, artist, title, album):
        """Delete metadata from the cache.

        Keyword arguments:
        type -- type of the metadata
        artist -- artist tag
        title -- title tag
        album -- album tag
        """
        if artist and title and album:
            self.cache.delete(plyr.Query(get_type=type, artist=artist, title=title, album=album))

    def save(self, type, filename):
        """Save the given metadata type.

        Keyword arguments:
        type -- type of the metadata
        filename -- path to the file metadata will be saved to

        Some special substrings can be used in the filename:
        <filename> -- name of the current song without extension
        <songdir> -- directory containing the current song
        <artist> -- artist of the current song
        <title> -- title of the current song
        <album> -- album of the current song
        """
        data = getattr(self, type)
        if self.file and data and data != 'Searching...':
            replace = {
                '<filename>': os.path.splitext(os.path.basename(self.file))[0],
                '<songdir>': os.path.dirname(self.file),
                '<artist>': self.artist,
                '<title>': self.title,
                '<album>': self.album
            }
            file = filename
            for k in replace:
                file = file.replace(k, replace[k])
            if not os.path.exists(os.path.dirname(file)):
                os.makedirs(os.path.dirname(file))
            if not os.path.exists(file):
                mode = 'wb' if isinstance(data, bytes) else 'w'
                with open(file, mode) as f:
                    f.write(data)

    def _query(self, type, normalize=True):
        """Return the list containing results from the glyr.Query,
        or None if some tags are missing.

        Keyword arguments:
        type -- type of the metadata
        normalize -- whether the search strings should be normalized by glyr
        """
        try:
            query = plyr.Query(get_type=type, artist=self.artist, title=self.title, album=self.album)
        except AttributeError:
            # Missing tags?
            return None
        else:
            query.useragent = lyvi.USERAGENT
            query.database = self.cache
            if not normalize:
                query.normalize = ('none', 'artist', 'album', 'title')
            return query.commit()

    def get(self, type):
        """Download and set the metadata for the given property.

        Keyword arguments:
        type -- type of the metadata
        """
        artist = self.artist
        title = self.title
        if lyvi.ui.view == type:
            lyvi.ui.home()
        if type in ('lyrics', 'artistbio', 'guitartabs'):
            setattr(self, type, 'Searching...')
        elif type in ('backdrops', 'cover'):
            setattr(self, type, None)
        items = self._query(type, normalize=False) or self._query(type)
        data = None
        if items:
            if type in ('backdrops', 'cover'):
                data = items[0].data
            else:
                data = items[0].data.decode()
        with self.lock:
            if artist == self.artist and title == self.title:
                setattr(self, type, data)

########NEW FILE########
__FILENAME__ = cmus
# Copyright (c) 2013 Ondrej Kipila <ok100 at openmailbox dot org>
# This work is free. You can redistribute it and/or modify it under the
# terms of the Do What The Fuck You Want To Public License, Version 2,
# as published by Sam Hocevar. See the COPYING file for more details.

"""Cmus plugin for Lyvi."""


import os
import subprocess

from lyvi.players import Player
from lyvi.utils import check_output


class Player(Player):
    @classmethod
    def running(self):
        try:
            return subprocess.call(['cmus-remote', '-C']) == 0
        except OSError:
            return False

    def get_status(self):
        data = {'artist': None, 'album': None, 'title': None, 'file': None, 'length': None}

        for line in check_output('cmus-remote -Q').splitlines():
            if line.startswith('status '):
                data['state'] = line.split()[1].replace('playing', 'play')
                for x, y in (('playing', 'play'), ('paused', 'pause'), ('stopped', 'stop')):
                    data['state'] = data['state'].replace(x, y)
            elif line.startswith('tag artist '):
                data['artist'] = line.split(maxsplit=2)[2]
            elif line.startswith('tag album '):
                data['album'] = line.split(maxsplit=2)[2]
            elif line.startswith('tag title '):
                data['title'] = line.split(maxsplit=2)[2]
            elif line.startswith('file '):
                data['file'] = line.split(maxsplit=1)[1]
            elif line.startswith('duration '):
                data['length'] = int(line.split(maxsplit=1)[1])

        for k in data:
            setattr(self, k, data[k])

    def send_command(self, command):
        cmd = {
            'play': 'cmus-remote -p',
            'pause': 'cmus-remote -u',
            'next': 'cmus-remote -n',
            'prev': 'cmus-remote -r',
            'stop': 'cmus-remote -s',
            'volup': 'cmus-remote -v +5',
            'voldn': 'cmus-remote -v -5',
        }.get(command)

        if cmd:
            os.system(cmd)
            return True

########NEW FILE########
__FILENAME__ = moc
# Copyright (c) 2013 Ondrej Kipila <ok100 at openmailbox dot org>
# This work is free. You can redistribute it and/or modify it under the
# terms of the Do What The Fuck You Want To Public License, Version 2,
# as published by Sam Hocevar. See the COPYING file for more details.

"""MOC plugin for Lyvi."""


import os

from lyvi.players import Player
from lyvi.utils import check_output


class Player(Player):
    @classmethod
    def running(self):
        return os.path.exists(os.path.join(os.environ['HOME'], '.moc/pid'))

    def get_info_value(self, info_line):
        """Extract 'A value' from line 'ValueName: A value'."""
        try:
            return info_line.split(maxsplit=1)[1]
        except IndexError:
            # Empty value.
            return None

    def get_status(self):
        data = {'artist': None, 'album': None, 'title': None, 'file': None, 'length': None}

        for line in check_output('mocp -i').splitlines():
            info_value = self.get_info_value(line)
            if line.startswith('State: '):
                data['state'] = info_value.lower()
            elif line.startswith('Artist: '):
                data['artist'] = info_value or ''
            elif line.startswith('Album: '):
                data['album'] = info_value or ''
            elif line.startswith('SongTitle: '):
                data['title'] = info_value or ''
            elif line.startswith('File: '):
                data['file'] = info_value
            elif line.startswith('TotalSec: '):
                data['length'] = int(info_value)

        for k in data:
            setattr(self, k, data[k])

    def send_command(self, command):
        cmd = {
            'play': 'mocp -U',
            'pause': 'mocp -P',
            'next': 'mocp -f',
            'prev': 'mocp -r',
            'stop': 'mocp -s',
            'volup': 'mocp --volume +5',
            'voldn': 'mocp --volume -5',
        }.get(command)

        if cmd:
            os.system(cmd)
            return True

########NEW FILE########
__FILENAME__ = mpd
# Copyright (c) 2013 Ondrej Kipila <ok100 at openmailbox dot org>
# This work is free. You can redistribute it and/or modify it under the
# terms of the Do What The Fuck You Want To Public License, Version 2,
# as published by Sam Hocevar. See the COPYING file for more details.

"""MPD plugin for Lyvi."""


import os
from telnetlib import Telnet

import lyvi
from lyvi.players import Player
from lyvi.utils import running


class Player(Player):
    @classmethod
    def running(self):
        try:
            Telnet(lyvi.config['mpd_host'], lyvi.config['mpd_port']).close()
            return True
        except OSError:
            return False

    def __init__(self):
        """Get a path to the music directory and initialize the telnet connection."""
        self.music_dir = None
        if os.path.exists(lyvi.config['mpd_config_file']):
            for line in open(lyvi.config['mpd_config_file']):
                if line.strip().startswith('music_directory'):
                    self.music_dir = line.split('"')[1]
        self.telnet = Telnet(lyvi.config['mpd_host'], lyvi.config['mpd_port'])
        self.telnet.read_until(b'\n')

    def get_status(self):
        data = {'artist': None, 'album': None, 'title': None, 'file': None, 'length': None}

        self.telnet.write(b'status\n')
        response = self.telnet.read_until(b'OK').decode()
        self.telnet.write(b'currentsong\n')
        response += self.telnet.read_until(b'OK').decode()
        t = {
            'state: ': 'state',
            'Artist: ': 'artist',
            'Title: ': 'title',
            'Album: ': 'album',
            'file: ': 'file',
            'time: ': 'length',
        }
        for line in response.splitlines():
            for k in t:
                if line.startswith(k):
                    data[t[k]] = line.split(k, 1)[1]
                    break
        data['file'] = os.path.join(self.music_dir, data['file']) if data['file'] and self.music_dir else None
        data['length'] = int(data['length'].split(':')[1]) if data['length'] else None

        for k in data:
            setattr(self, k, data[k])

    def send_command(self, command):
        cmd = {
            'play': b'play\n',
            'pause': b'pause\n',
            'next': b'next\n',
            'prev': b'previous\n',
            'stop': b'stop\n',
        }.get(command)

        if cmd:
            self.telnet.write(cmd)
            return True
    
    def cleanup(self):
        self.telnet.close()

########NEW FILE########
__FILENAME__ = mpg123
# Copyright (c) 2013 Ondrej Kipila <ok100 at openmailbox dot org>
# This work is free. You can redistribute it and/or modify it under the
# terms of the Do What The Fuck You Want To Public License, Version 2,
# as published by Sam Hocevar. See the COPYING file for more details.

"""Mpg123 plugin for Lyvi."""


import os

import lyvi
from lyvi.players import Player
from lyvi.utils import running

class Player(Player):
    LOG_FILE = os.path.join(lyvi.TEMP, 'mpg123.log')

    @classmethod
    def running(self):
        return running('mpg123') and os.path.exists(self.LOG_FILE)

    def get_status(self):
        data = {'artist': None, 'album': None, 'title': None, 'file': None, 'state': 'play', 'length': None}

        with open(self.LOG_FILE) as f:
            for line in f.read().splitlines():
                if 'Title:' and 'Artist:' in line:
                    data['title'], data['artist'] = (
                        x.strip() for x in line.split('Title: ')[1].split('Artist: ')
                    )
                elif 'Album: ' in line:
                    data['album'] = line.split('Album: ')[1].strip()

        for k in data:
            setattr(self, k, data[k])

########NEW FILE########
__FILENAME__ = mplayer
# Copyright (c) 2013 Ondrej Kipila <ok100 at openmailbox dot org>
# This work is free. You can redistribute it and/or modify it under the
# terms of the Do What The Fuck You Want To Public License, Version 2,
# as published by Sam Hocevar. See the COPYING file for more details.

"""MPlayer/mpv plugin for Lyvi."""


import os

import lyvi
from lyvi.players import Player
from lyvi.utils import process_fifo, running


class Player(Player):
    LOG_FILE = os.path.join(lyvi.config['mplayer_config_dir'], 'log')
    FIFO = os.path.join(lyvi.config['mplayer_config_dir'], 'fifo')
    ID = {
        'ID_CLIP_INFO_VALUE0=': 'title',
        'ID_CLIP_INFO_VALUE1=': 'artist',
        'ID_CLIP_INFO_VALUE3=': 'album',
        'ID_FILENAME=': 'file',
        'ID_LENGTH=': 'length',
    }

    @classmethod
    def running(self):
        return (running('mplayer') or running('mpv')) and os.path.exists(self.LOG_FILE)

    def get_status(self):
        data = {'artist': None, 'album': None, 'title': None, 'file': None, 'state': 'play', 'length': None}

        with open(self.LOG_FILE) as f:
            for line in f.read().splitlines():
                for i in self.ID:
                    if i in line:
                        data[self.ID[i]] = line.split(i)[1]

        if data['length']:
            data['length'] = int(data['length'].split('.')[0])

        for k in data:
            setattr(self, k, data[k])

    def send_command(self, command):
        if not os.path.exists(self.FIFO):
            return

        cmd = {
            'play': 'pause',
            'pause': 'pause',
            'next': 'pt_step 1',
            'prev': 'pt_step -1',
            'stop': 'stop',
            'volup': 'volume +5',
            'voldn': 'volume -5',
        }.get(command)

        if cmd:
            process_fifo(self.FIFO, cmd)
            return True

########NEW FILE########
__FILENAME__ = mpris
# Copyright (c) 2013 Ondrej Kipila <ok100 at openmailbox dot org>
# This work is free. You can redistribute it and/or modify it under the
# terms of the Do What The Fuck You Want To Public License, Version 2,
# as published by Sam Hocevar. See the COPYING file for more details.

"""MPRIS plugin for Lyvi."""


import dbus
import dbus.exceptions
import dbus.glib
import dbus.mainloop.glib
from gi.repository import GObject

from lyvi.players import Player
from lyvi.utils import thread


# Initialize the DBus loop, required to enable asynchronous dbus calls
dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
GObject.threads_init()
dbus.glib.init_threads()
loop = GObject.MainLoop()
thread(loop.run)


def find():
    """Return the initialized mpris.Player class, otherwise
    return None if no player was found."""
    try:
        for name in dbus.SessionBus().list_names():
            if name.startswith('org.mpris.MediaPlayer2.'):
                return Player(name[len('org.mpris.MediaPlayer2.'):])
    except dbus.exceptions.DBusException:
        pass
    return None


def running(playername):
    """Return True if a MPRIS player with the given name is running.
    
    Keyword arguments:
    playername -- mpris player name
    """
    try:
        bus = dbus.SessionBus()
        bus.get_object('org.mpris.MediaPlayer2.%s' % playername, '/org/mpris/MediaPlayer2')
        return True
    except dbus.exceptions.DBusException:
        return False


class Player(Player):
    """Class which supports all players that implement the MPRIS Interface."""
    def running(self):
        return running(self.playername)

    def __init__(self, playername):
        """Initialize the player.

        Keyword arguments:
        playername -- mpris player name
        """
        self.playername = playername

        # Player status cache
        self.playerstatus = {}

        # Store the interface in this object, so it does not have to reinitialized each second
        # in the main loop
        bus = dbus.SessionBus()
        playerobject = bus.get_object('org.mpris.MediaPlayer2.' + self.playername,
                '/org/mpris/MediaPlayer2')
        self.mprisplayer = dbus.Interface(playerobject, 'org.mpris.MediaPlayer2.Player')
        self.mprisprops = dbus.Interface(playerobject, 'org.freedesktop.DBus.Properties')
        self.mprisprops.connect_to_signal("PropertiesChanged", self.loaddata)
        self.loaddata()

    def loaddata(self, *args, **kwargs):
        """Retrieve the player status over DBUS.

        Arguments are ignored, but *args and **kwargs enable support the dbus callback.
        """
        self.playerstatus = self.mprisprops.GetAll('org.mpris.MediaPlayer2.Player')

    def get_status(self):
        data = {'artist': None, 'album': None, 'title': None, 'file': None, 'length': None}

        data['state'] = (self.playerstatus['PlaybackStatus']
                .replace('Stopped', 'stop')
                .replace('Playing', 'play')
                .replace('Paused', 'pause'))
        try:
            data['length'] = round(int(self.playerstatus['Metadata']['mpris:length']) / 1000000)
        except KeyError:
            pass
        try:
            data['artist'] = self.playerstatus['Metadata']['xesam:artist'][0]
        except KeyError:
            pass
        try:
            title = self.playerstatus['Metadata']['xesam:title']
            # According to MPRIS/Xesam, title is a String, but some players seem return an array
            data['title'] = title[0] if isinstance(title, dbus.Array) else title
        except KeyError:
            pass
        try:
            data['album'] = self.playerstatus['Metadata']['xesam:album']
        except KeyError:
            pass
        try:
            data['file'] = self.playerstatus['Metadata']['xesam:url'].split('file://')[1]
        except (KeyError, IndexError):
            pass

        for k in data:
            setattr(self, k, data[k])

    def send_command(self, command):
        if command == 'volup':
            volume = self.playerstatus['Volume'] + 0.1
            self.mprisprops.Set('org.mpris.MediaPlayer2.Player', 'Volume', min(volume, 1.0))
            return True
        if command == 'voldn':
            volume = self.playerstatus['Volume'] - 0.1
            self.mprisprops.Set('org.mpris.MediaPlayer2.Player', 'Volume', max(volume, 0.0))
            return True

        cmd = {
            'play': self.mprisplayer.PlayPause,
            'pause': self.mprisplayer.Pause,
            'next': self.mprisplayer.Next,
            'prev': self.mprisplayer.Previous,
            'stop': self.mprisplayer.Stop,
        }.get(command)
        
        if cmd:
            try:
                cmd()
            except dbus.DBusException:
                # Some players (rhythmbox) raises DBusException when attempt to
                # use "next"/"prev" command on first/last item of the playlist
                pass
            return True

########NEW FILE########
__FILENAME__ = pianobar
# Copyright (c) 2013 Ondrej Kipila <ok100 at openmailbox dot org>
# This work is free. You can redistribute it and/or modify it under the
# terms of the Do What The Fuck You Want To Public License, Version 2,
# as published by Sam Hocevar. See the COPYING file for more details.

"""Pianobar plugin for Lyvi."""


import os

from lyvi.players import Player
from lyvi.utils import process_fifo, running


class Player(Player):
    CONFIG_FILE = os.path.join(os.environ['HOME'], '.config/pianobar/config')
    NOWPLAYING_FILE = os.path.join(os.environ['HOME'], '.config/pianobar/nowplaying')
    FIFO = os.path.join(os.environ['HOME'], '.config/pianobar/ctl')
    # Default control keys
    config = {
        'act_songpausetoggle': 'p',
        'act_songnext': 'n',
        'act_volup': ')',
        'act_voldown': '(',
    }

    @classmethod
    def running(self):
        return running('pianobar') and os.path.exists(self.NOWPLAYING_FILE)

    def __init__(self):
        """Get the actual control keys from the pianobar configuration file
        so we can send the right commands to the fifo."""
        with open(self.CONFIG_FILE) as f:
            for line in f.read().splitlines():
                if not line.strip().startswith('#') and line.split('=')[0].strip() in self.config:
                    self.config[line.split('=')[0].strip()] = line.split('=')[1].strip()

    def get_status(self):
        data = {'artist': None, 'album': None, 'title': None, 'file': None, 'state': 'play'}

        with open(self.NOWPLAYING_FILE) as f:
            data['artist'], data['title'], data['album'] = f.read().split('|')

        for k in data:
            setattr(self, k, data[k])

    def send_command(self, command):
        if not os.path.exists(self.FIFO):
            return

        cmd = {
            'play': 'act_songpausetoggle',
            'pause': 'act_songpausetoggle',
            'next': 'act_songnext',
            'volup': 'act_volup',
            'voldn': 'act_voldown',
        }.get(command)

        if cmd:
            process_fifo(self.FIFO, self.config[cmd])
            return True

########NEW FILE########
__FILENAME__ = shell-fm
# Copyright (c) 2013 Ondrej Kipila <ok100 at openmailbox dot org>
# This work is free. You can redistribute it and/or modify it under the
# terms of the Do What The Fuck You Want To Public License, Version 2,
# as published by Sam Hocevar. See the COPYING file for more details.

"""Shell-fm plugin for Lyvi."""


import os

from lyvi.players import Player
from lyvi.utils import process_socket, running


class Player(Player):
    NOWPLAYING_FILE = os.path.join(os.environ['HOME'], '.shell-fm/nowplaying')
    SOCKET = os.path.join(os.environ['HOME'], '.shell-fm/socket')

    @classmethod
    def running(self):
        return running('shell-fm') and os.path.exists(self.NOWPLAYING_FILE)

    def get_status(self):
        data = {'artist': None, 'album': None, 'title': None, 'file': None, 'state': 'stop'}

        with open(self.NOWPLAYING_FILE) as f:
            data['artist'], data['title'], data['album'], data['state'] = f.read().split('|')
        for x, y in (
            ('PLAYING', 'play'),
            ('PAUSED', 'pause'),
            ('STOPPED', 'stop')
        ):
            data['state'] = data['state'].replace(x, y)

        for k in data:
            setattr(self, k, data[k])

    def send_command(self, command):
        if not os.path.exists(self.SOCKET):
            return

        cmd = {
            'pause': 'pause',
            'next': 'skip',
            'stop': 'stop',
            'volup': 'volume +5',
            'voldn': 'volume -5',
        }.get(command)

        if cmd:
            process_socket(self.SOCKET, cmd)
            return True

########NEW FILE########
__FILENAME__ = xmms2
# Copyright (c) 2013 Ondrej Kipila <ok100 at openmailbox dot org>
# This work is free. You can redistribute it and/or modify it under the
# terms of the Do What The Fuck You Want To Public License, Version 2,
# as published by Sam Hocevar. See the COPYING file for more details.

"""Xmms2 plugin for Lyvi."""


import os
from urllib.parse import unquote_plus

from lyvi.players import Player
from lyvi.utils import running, check_output


class Player(Player):
    @classmethod
    def running(self):
        return running('xmms2d')

    def get_status(self):
        data = {'artist': None, 'album': None, 'title': None, 'file': None, 'state': 'play', 'length': None}
        try:
            data['state'], data['artist'], data['album'], data['title'], data['file'], data['length'] = \
                    check_output('xmms2 current -f \'${playback_status}|${artist}|${album}|${title}|${url}|${duration}\'').split('|')
        except ValueError:
            return

        for x, y in (('Playing', 'play'), ('Paused', 'pause'), ('Stopped', 'stop')):
            data['state'] = data['state'].replace(x, y)

        # unquote_plus replaces % not as plus signs but as spaces (url decode)
        data['file'] = unquote_plus(data['file']).strip()
        for x, y in (('\'', ''), ('file://', '')):
            data['file'] = data['file'].replace(x, y)

        try:
            data['length'] = int(data['length'].split(':')[0]) * 60 + int(data['length'].split(':')[1])
        except ValueError:
            data['length'] = None

        for k in data:
            setattr(self, k, data[k])

    def send_command(self, command):
        cmd = {
            'play': 'xmms2 play',
            'pause': 'xmms2 pause',
            'next': 'xmms2 jump +1',
            'prev': 'xmms2 jump -1',
            'stop': 'xmms2 stop',
            'volup': 'xmms2 server volume +5',
            'voldn': 'xmms2 server volume -5',
        }.get(command)

        if cmd:
            os.system(cmd)
            return True

########NEW FILE########
__FILENAME__ = tui
# Copyright (c) 2013 Ondrej Kipila <ok100 at openmailbox dot org>
# This work is free. You can redistribute it and/or modify it under the
# terms of the Do What The Fuck You Want To Public License, Version 2,
# as published by Sam Hocevar. See the COPYING file for more details.

"""Curses user interface."""


from math import ceil
from time import sleep
from threading import Thread, Event

import urwid

import lyvi


class VimListBox(urwid.ListBox):
    """A ListBox subclass which provides vim-like and mouse scrolling.

    Additional properties:
    size -- a tuple (width, height) of the listbox dimensions
    total_lines -- total number of lines
    pos -- a string containing vim-like scroll position indicator

    Additional signals:
    changed -- emited when the listbox content changes
    """
    signals = ['changed']

    def mouse_event(self, size, event, button, col, row, focus):
        """Overrides ListBox.mouse_event method.

        Implements mouse scrolling.
        """
        if event == 'mouse press':
            if button == 4:
                for _ in range(3):
                    self.keypress(size, 'up')
                return True
            if button == 5:
                for _ in range(3):
                    self.keypress(size, 'down')
                return True
        return self.__super.mouse_event(size, event, button, col, row, focus)

    def keypress(self, size, key):
        """Overrides ListBox.keypress method.

        Implements vim-like scrolling.
        """
        if key == 'j':
            self.keypress(size, 'down')
            return True
        if key == 'k':
            self.keypress(size, 'up')
            return True
        if key == 'g':
            self.set_focus(0)
            return True
        if key == 'G':
            self.set_focus(len(self.body) - 1)
            self.set_focus_valign('bottom')
            return True
        return self.__super.keypress(size, key)

    def calculate_visible(self, size, focus=False):
        """Overrides ListBox.calculate_visible method.

        Calculates the scroll position (like in vim).
        """
        self.size = size
        width, height = size
        middle, top, bottom = self.__super.calculate_visible(self.size, focus)
        fpos = self.body.index(top[1][-1][0]) if top[1] else self.focus_position
        top_line = sum([self.body[n].rows((width,)) for n in range(0, fpos)]) + top[0]
        self.total_lines = sum([widget.rows((width,)) for widget in self.body])
        if self.total_lines <= height:
            self.pos = 'All'
        elif top_line == 0:
            self.pos = 'Top'
        elif top_line + height == self.total_lines:
            self.pos = 'Bot'
        else:
            self.pos = '%d%%' % round(top_line * 100 / (self.total_lines - height))
        self._emit('changed')
        return middle, top, bottom


class Autoscroll(Thread):
    """A Thread subclass that implements autoscroll timer."""
    def __init__(self, widget):
        """Initialize the class."""
        super().__init__()
        self.daemon = True
        self.widget = widget
        self.event = Event()

    def _can_scroll(self):
        """Return True if we can autoscroll."""
        return (lyvi.player.length and lyvi.player.state == 'play' and lyvi.ui.view == 'lyrics'
                and not lyvi.ui.hidden and self.widget.pos not in ('All', 'Bot'))

    def run(self):
        """Start the timer."""
        while True:
            if self._can_scroll():
                time = ceil(lyvi.player.length / (self.widget.total_lines - self.widget.size[1]))
                reset = False
                for _ in range(time):
                    if self.event.wait(1):
                        reset = True
                        self.event.clear()
                        break
                if not reset and self._can_scroll():
                    self.widget.keypress(self.widget.size, 'down')
            else:
                sleep(1)

    def reset(self):
        """Reset the timer."""
        self.event.set()


class Ui:
    """Main UI class.
    
    Attributes:
    view -- current view
    hidden -- whether the UI is hidden
    quit -- stop the mainloop if this flag is set to True
    """
    view = lyvi.config['default_view']
    hidden = lyvi.config['ui_hidden']
    _header = ''
    _text = ''
    quit = False

    @property
    def header(self):
        """Header text."""
        return self._header

    @header.setter
    def header(self, value):
        self._header = value
        if not self.hidden:
            self.head.set_text(('header', self.header))
            self._refresh()

    @property
    def text(self):
        """The main text."""
        return self._text

    @text.setter
    def text(self, value):
        self._text = value
        if not self.hidden:
            self.content[:] = [self.head, urwid.Divider()] + \
                    [urwid.Text(('content', line)) for line in self.text.splitlines()]
            self._refresh()

    def init(self):
        """Initialize the class."""
        palette = [
            ('header', lyvi.config['header_fg'], lyvi.config['header_bg']),
            ('content', lyvi.config['text_fg'], lyvi.config['text_bg']),
            ('statusbar', lyvi.config['statusbar_fg'], lyvi.config['statusbar_bg']),
        ]

        self.head = urwid.Text(('header', ''))
        self.statusbar = urwid.AttrMap(urwid.Text('', align='right'), 'statusbar')
        self.content = urwid.SimpleListWalker([urwid.Text(('content', ''))])
        self.listbox = VimListBox(self.content)
        self.frame = urwid.Frame(urwid.Padding(self.listbox, left=1, right=1), footer=self.statusbar)
        self.loop = urwid.MainLoop(self.frame, palette, unhandled_input=self.input)
        self.autoscroll = Autoscroll(self.listbox) if lyvi.config['autoscroll'] else None

        if self.autoscroll:
            self.autoscroll.start()
        urwid.connect_signal(self.listbox, 'changed', self.update_statusbar)
        self._set_alarm()

    def update(self):
        """Update the listbox content."""
        if lyvi.player.state == 'stop':
            self.header = 'N/A' if self.view == 'artistbio' else 'N/A - N/A'
            self.text = 'Not playing'
        elif self.view == 'lyrics':
            self.header = '%s - %s' % (lyvi.md.artist or 'N/A', lyvi.md.title or 'N/A')
            self.text = lyvi.md.lyrics or 'No lyrics found'
        elif self.view == 'artistbio':
            self.header = lyvi.md.artist or 'N/A'
            self.text = lyvi.md.artistbio or 'No artist info found'
        elif self.view == 'guitartabs':
            self.header = '%s - %s' % (lyvi.md.artist or 'N/A', lyvi.md.title or 'N/A')
            self.text = lyvi.md.guitartabs or 'No guitar tabs found'

    def home(self):
        """Scroll to the top of the current view."""
        self.listbox.set_focus(0)
        self._refresh()

    def update_statusbar(self, _=None):
        """Update the statusbar.

        Arguments are ignored, but enable support for urwid signal callback.
        """
        if not self.hidden:
            text = urwid.Text(self.view + self.listbox.pos.rjust(10), align='right')
            wrap = urwid.AttrWrap(text, 'statusbar')
            self.frame.set_footer(wrap)

    def toggle_views(self):
        """Toggle between views."""
        if not self.hidden:
            views = ['lyrics', 'artistbio', 'guitartabs']
            n = views.index(self.view)
            self.view = views[n + 1] if n < len(views) - 1 else views[0]
            self.home()
            self.update()

    def toggle_visibility(self):
        """Toggle UI visibility."""
        if lyvi.bg:
            if not self.hidden:
                self.header = ''
                self.text = ''
                self.frame.set_footer(urwid.AttrWrap(urwid.Text(''), 'statusbar'))
                lyvi.bg.opacity = 1.0
                lyvi.bg.update()
                self.hidden = True
            else:
                self.hidden = False
                lyvi.bg.opacity = lyvi.config['bg_opacity']
                lyvi.bg.update()
                self.update()

    def reload(self, type):
        """Reload metadata for current view."""
        from lyvi.utils import thread
        import lyvi.metadata
        lyvi.md.delete(type, lyvi.md.artist, lyvi.md.title, lyvi.md.album)
        thread(lyvi.md.get, (type,))

    def input(self, key):
        """Process input not handled by any widget."""
        if key == lyvi.config['key_quit']:
            lyvi.exit()
        elif key == lyvi.config['key_toggle_views']:
            self.toggle_views()
        elif key == lyvi.config['key_reload_view']:
            self.reload(self.view)
        elif key == lyvi.config['key_reload_bg'] and lyvi.bg:
            self.reload(lyvi.bg.type)
        elif key == lyvi.config['key_toggle_bg_type'] and lyvi.bg:
            lyvi.bg.toggle_type()
        elif key == lyvi.config['key_toggle_ui']:
            self.toggle_visibility()

    def mainloop(self):
        """Start the mainloop."""
        self.loop.run()

    def _set_alarm(self):
        """Set the alarm for _check_exit."""
        self.loop.event_loop.alarm(0.5, self._check_exit)

    def _check_exit(self):
        """Stop the mainloop if the quit property is True."""
        self._set_alarm()
        if self.quit:
            raise urwid.ExitMainLoop()

    def _refresh(self):
        """Redraw the screen."""
        self.loop.draw_screen()

########NEW FILE########
__FILENAME__ = utils
# Copyright (c) 2013 Ondrej Kipila <ok100 at openmailbox dot org>
# This work is free. You can redistribute it and/or modify it under the
# terms of the Do What The Fuck You Want To Public License, Version 2,
# as published by Sam Hocevar. See the COPYING file for more details.

"""Common functions used across the whole package."""


import socket
import subprocess as sp
from threading import Thread

from psutil import process_iter


def check_output(command):
    """Return an output of the given command."""
    try:
        return sp.check_output(command, shell=True, stderr=sp.DEVNULL).decode()
    except sp.CalledProcessError:
        return ''


def process_fifo(file, command):
    """Send a command to the given fifo.

    Keyword arguments:
    file -- the path to the fifo file
    command -- the command without newline character at the end
    """
    with open(file, 'w') as f:
        f.write(command + '\n')


def process_socket(sock, command):
    """Send a command to the given socket.

    Keyword arguments:
    file -- the path to the socket
    command -- the command without newline character at the end
    """
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        s.connect(sock)
        s.send((command + '\n').encode())


def running(process_name):
    """Return True if the given process is running, otherwise return False.

    Keyword arguments:
    process_name -- the name of the process
    """
    for p in process_iter():
        if p.name == process_name:
            return True
    return False


def thread(target, args=()):
    """Run the given callable object in a new daemon thread.

    Keyword arguments:
    target -- the target object
    args -- a tuple of arguments to be passed to the target object
    """
    worker = Thread(target=target, args=args)
    worker.daemon = True
    worker.start()

########NEW FILE########
__FILENAME__ = lyvi
#!/usr/bin/env python

import lyvi


lyvi.main()

########NEW FILE########
