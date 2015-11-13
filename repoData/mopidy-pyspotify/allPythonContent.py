__FILENAME__ = conf
# encoding: utf-8

"""pyspotify documentation build configuration file"""

from __future__ import unicode_literals

import os
import re
import sys
import types

try:
    # Python 3.3+
    from unittest import mock
except ImportError:
    # Python <3.3
    import mock


def get_version(filename):
    init_py = open(filename).read()
    metadata = dict(re.findall("__([a-z]+)__ = '([^']+)'", init_py))
    return metadata['version']


# -- Workarounds to have autodoc generate API docs ----------------------------

sys.path.insert(0, os.path.abspath('..'))


# Mock cffi module and cffi objects
cffi = mock.Mock()
cffi.__version__ = '0.8.1'
sys.modules['cffi'] = cffi
ffi = cffi.FFI.return_value
ffi.CData = bytes
lib = ffi.verify.return_value
lib.sp_error_message.return_value = b''
lib.sp_error_message.__name__ = str('sp_error_message')


# Add all libspotify constants to the lib mock
with open('sp-constants.csv') as fh:
    for line in fh.readlines():
        key, value = line.split(',', 1)
        setattr(lib, key, value)


# Unwrap decorated methods so Sphinx can inspect their signatures
import spotify
for mod_name, mod in vars(spotify).items():
    if not isinstance(mod, types.ModuleType) or mod_name in ('threading',):
        continue
    for class_name, cls in vars(mod).items():
        if not isinstance(cls, type):
            continue
        for method_name, method in vars(cls).items():
            if hasattr(method, '__wrapped__'):
                setattr(cls, method_name, method.__wrapped__)


# -- General configuration ----------------------------------------------------

needs_sphinx = '1.0'

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.extlinks',
    'sphinx.ext.intersphinx',
    'sphinx.ext.viewcode',
]

templates_path = ['_templates']
source_suffix = '.rst'
master_doc = 'index'

project = 'pyspotify'
copyright = '2013-2014, Stein Magnus Jodal and contributors'

release = get_version('../spotify/__init__.py')
version = '.'.join(release.split('.')[:2])

exclude_patterns = ['_build']

pygments_style = 'sphinx'

modindex_common_prefix = ['spotify.']

autodoc_default_flags = ['members', 'undoc-members', 'inherited-members']
autodoc_member_order = 'bysource'

intersphinx_mapping = {
    'python': ('http://docs.python.org/3', None),
    'pyalsaaudio': ('http://pyalsaaudio.sourceforge.net', None),
}


# -- Options for HTML output --------------------------------------------------

html_theme = 'default'
html_static_path = ['_static']

html_use_modindex = True
html_use_index = True
html_split_index = False
html_show_sourcelink = True

htmlhelp_basename = 'pyspotify'

# -- Options for extlink extension --------------------------------------------

extlinks = {
    'issue': ('https://github.com/mopidy/pyspotify/issues/%s', '#'),
}

########NEW FILE########
__FILENAME__ = cover
import spotify

# Assuming a spotify_appkey.key in the current dir:
session = spotify.Session()

# Assuming a previous login with remember_me=True and a proper logout:
session.relogin()

while session.connection.state != spotify.ConnectionState.LOGGED_IN:
    session.process_events()

album = session.get_album('spotify:album:4m2880jivSbbyEGAKfITCa').load()
cover = album.cover(spotify.ImageSize.LARGE).load()

open('/tmp/cover.jpg', 'wb').write(cover.data)
open('/tmp/cover.html', 'w').write('<img src="%s">' % cover.data_uri)

########NEW FILE########
__FILENAME__ = play_track
#!/usr/bin/env python

"""
This is an example of playing music from Spotify using pyspotify.

The example use the :class:`spotify.AlsaSink`, and will thus only work on
systems with an ALSA sound subsystem, which means most Linux systems.

You can either run this file directly without arguments to play a default
track::

    python play_track.py

Or, give the script a Spotify track URI to play::

    python play_track.py spotify:track:3iFjScPoAC21CT5cbAFZ7b
"""

from __future__ import unicode_literals

import sys
import threading

import spotify

if sys.argv[1:]:
    track_uri = sys.argv[1]
else:
    track_uri = 'spotify:track:6xZtSE6xaBxmRozKA0F6TA'

# Assuming a spotify_appkey.key in the current dir
session = spotify.Session()

# Process events in the background
loop = spotify.EventLoop(session)
loop.start()

# Connect an audio sink
audio = spotify.AlsaSink(session)

# Events for coordination
logged_in = threading.Event()
end_of_track = threading.Event()


def on_connection_state_updated(session):
    if session.connection.state is spotify.ConnectionState.LOGGED_IN:
        logged_in.set()


def on_end_of_track(self):
    end_of_track.set()


# Register event listeners
session.on(
    spotify.SessionEvent.CONNECTION_STATE_UPDATED, on_connection_state_updated)
session.on(spotify.SessionEvent.END_OF_TRACK, on_end_of_track)

# Assuming a previous login with remember_me=True and a proper logout
session.relogin()

logged_in.wait()

# Play a track
track = session.get_track(track_uri).load()
session.player.load(track)
session.player.play()

# Wait for playback to complete or Ctrl+C
try:
    while not end_of_track.wait(0.1):
        pass
except KeyboardInterrupt:
    pass

########NEW FILE########
__FILENAME__ = shell
#!/usr/bin/env python

"""
This is an example of a simple command line client for Spotify using pyspotify.

You can run this file directly::

    python shell.py

Then run the ``help`` command on the ``spotify>`` prompt to view all available
commands.
"""

from __future__ import unicode_literals

import cmd
import logging
import threading

import spotify


class Commander(cmd.Cmd):

    doc_header = 'Commands'
    prompt = 'spotify> '

    logger = logging.getLogger('shell.commander')

    def __init__(self):
        cmd.Cmd.__init__(self)

        self.logged_in = threading.Event()
        self.logged_out = threading.Event()
        self.logged_out.set()

        self.session = spotify.Session()
        self.session.on(
            spotify.SessionEvent.CONNECTION_STATE_UPDATED,
            self.on_connection_state_changed)
        self.session.on(
            spotify.SessionEvent.END_OF_TRACK, self.on_end_of_track)

        try:
            self.audio_driver = spotify.AlsaSink(self.session)
        except ImportError:
            self.logger.warning(
                'No audio sink found; audio playback unavailable.')

        self.event_loop = spotify.EventLoop(self.session)
        self.event_loop.start()

    def on_connection_state_changed(self, session):
        if session.connection.state is spotify.ConnectionState.LOGGED_IN:
            self.logged_in.set()
            self.logged_out.clear()
        elif session.connection.state is spotify.ConnectionState.LOGGED_OUT:
            self.logged_in.clear()
            self.logged_out.set()

    def on_end_of_track(self, session):
        self.session.player.play(False)

    def precmd(self, line):
        if line:
            self.logger.debug('New command: %s', line)
        return line

    def emptyline(self):
        pass

    def do_debug(self, line):
        "Show more logging output"
        print('Logging at DEBUG level')
        logger = logging.getLogger()
        logger.setLevel(logging.DEBUG)

    def do_info(self, line):
        "Show normal logging output"
        print('Logging at INFO level')
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)

    def do_warning(self, line):
        "Show less logging output"
        print('Logging at WARNING level')
        logger = logging.getLogger()
        logger.setLevel(logging.WARNING)

    def do_EOF(self, line):
        "Exit"
        if self.logged_in.is_set():
            print('Logging out...')
            self.session.logout()
            self.logged_out.wait()
        self.event_loop.stop()
        print('')
        return True

    def do_login(self, line):
        "login <username> <password>"
        username, password = line.split(' ', 1)
        self.session.login(username, password, remember_me=True)
        self.logged_in.wait()

    def do_relogin(self, line):
        "relogin -- login as the previous logged in user"
        try:
            self.session.relogin()
            self.logged_in.wait()
        except spotify.Error as e:
            self.logger.error(e)

    def do_forget_me(self, line):
        "forget_me -- forget the previous logged in user"
        self.session.forget_me()

    def do_logout(self, line):
        "logout"
        self.session.logout()
        self.logged_out.wait()

    def do_whoami(self, line):
        "whoami"
        if self.logged_in.is_set():
            self.logger.info(
                'I am %s aka %s. You can find me at %s',
                self.session.user.canonical_name,
                self.session.user.display_name,
                self.session.user.link)
        else:
            self.logger.info(
                'I am not logged in, but I may be %s',
                self.session.remembered_user)

    def do_play_uri(self, line):
        "play <spotify track uri>"
        if not self.logged_in.is_set():
            self.logger.warning('You must be logged in to play')
            return
        try:
            track = self.session.get_track(line)
            track.load()
        except (ValueError, spotify.Error) as e:
            self.logger.warning(e)
            return
        self.logger.info('Loading track into player')
        self.session.player.load(track)
        self.logger.info('Playing track')
        self.session.player.play()

    def do_pause(self):
        self.logger.info('Pausing track')
        self.session.player.play(False)

    def do_resume(self):
        self.logger.info('Resuming track')
        self.session.player.play()

    def do_stop(self):
        self.logger.info('Stopping track')
        self.session.player.play(False)
        self.session.player.unload()

    def do_seek(self, seconds):
        "seek <seconds>"
        if not self.logged_in.is_set():
            self.logger.warning('You must be logged in to play')
            return
        # TODO Check if playing
        self.session.player.seek(int(seconds) * 1000)

    def do_search(self, query):
        "search <query>"
        if not self.logged_in.is_set():
            self.logger.warning('You must be logged in to search')
            return
        try:
            result = self.session.search(query)
            result.load()
        except spotify.Error as e:
            self.logger.warning(e)
            return
        self.logger.info(
            '%d tracks, %d albums, %d artists, and %d playlists found.',
            result.track_total, result.album_total,
            result.artist_total, result.playlist_total)
        self.logger.info('Top tracks:')
        for track in result.tracks:
            self.logger.info(
                '[%s] %s - %s', track.link, track.artists[0].name, track.name)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    Commander().cmdloop()

########NEW FILE########
__FILENAME__ = album
from __future__ import unicode_literals

import logging
import threading

import spotify
from spotify import ffi, lib, serialized, utils


__all__ = [
    'Album',
    'AlbumBrowser',
    'AlbumType',
]

logger = logging.getLogger(__name__)


class Album(object):
    """A Spotify album.

    You can get an album from a track or an artist, or you can create an
    :class:`Album` yourself from a Spotify URI::

        >>> session = spotify.Session()
        # ...
        >>> album = session.get_album('spotify:album:6wXDbHLesy6zWqQawAa91d')
        >>> album.load().name
        u'Forward / Return'
    """

    def __init__(self, session, uri=None, sp_album=None, add_ref=True):
        assert uri or sp_album, 'uri or sp_album is required'

        self._session = session

        if uri is not None:
            album = spotify.Link(self._session, uri=uri).as_album()
            if album is None:
                raise ValueError(
                    'Failed to get album from Spotify URI: %r' % uri)
            sp_album = album._sp_album
            add_ref = True

        if add_ref:
            lib.sp_album_add_ref(sp_album)
        self._sp_album = ffi.gc(sp_album, lib.sp_album_release)

    def __repr__(self):
        return 'Album(%r)' % self.link.uri

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self._sp_album == other._sp_album
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self._sp_album)

    @property
    def is_loaded(self):
        """Whether the album's data is loaded."""
        return bool(lib.sp_album_is_loaded(self._sp_album))

    def load(self, timeout=None):
        """Block until the album's data is loaded.

        After ``timeout`` seconds with no results :exc:`~spotify.Timeout` is
        raised. If ``timeout`` is :class:`None` the default timeout is used.

        The method returns ``self`` to allow for chaining of calls.
        """
        return utils.load(self._session, self, timeout=timeout)

    @property
    def is_available(self):
        """Whether the album is available in the current region.

        Will always return :class:`None` if the album isn't loaded.
        """
        if not self.is_loaded:
            return None
        return bool(lib.sp_album_is_available(self._sp_album))

    @property
    @serialized
    def artist(self):
        """The artist of the album.

        Will always return :class:`None` if the album isn't loaded.
        """
        sp_artist = lib.sp_album_artist(self._sp_album)
        if sp_artist == ffi.NULL:
            return None
        return spotify.Artist(self._session, sp_artist=sp_artist, add_ref=True)

    @serialized
    def cover(self, image_size=None, callback=None):
        """The album's cover :class:`Image`.

        ``image_size`` is an :class:`ImageSize` value, by default
        :attr:`ImageSize.NORMAL`.

        If ``callback`` isn't :class:`None`, it is expected to be a callable
        that accepts a single argument, an :class:`Image` instance, when
        the image is done loading.

        Will always return :class:`None` if the album isn't loaded or the
        album has no cover.
        """
        if image_size is None:
            image_size = spotify.ImageSize.NORMAL
        cover_id = lib.sp_album_cover(self._sp_album, int(image_size))
        if cover_id == ffi.NULL:
            return None
        sp_image = lib.sp_image_create(self._session._sp_session, cover_id)
        return spotify.Image(
            self._session, sp_image=sp_image, add_ref=False, callback=callback)

    def cover_link(self, image_size=None):
        """A :class:`Link` to the album's cover.

        ``image_size`` is an :class:`ImageSize` value, by default
        :attr:`ImageSize.NORMAL`.

        This is equivalent with ``album.cover(image_size).link``, except that
        this method does not need to create the album cover image object to
        create a link to it.
        """
        if image_size is None:
            image_size = spotify.ImageSize.NORMAL
        sp_link = lib.sp_link_create_from_album_cover(
            self._sp_album, int(image_size))
        return spotify.Link(self._session, sp_link=sp_link, add_ref=False)

    @property
    @serialized
    def name(self):
        """The album's name.

        Will always return :class:`None` if the album isn't loaded.
        """
        name = utils.to_unicode(lib.sp_album_name(self._sp_album))
        return name if name else None

    @property
    def year(self):
        """The album's release year.

        Will always return :class:`None` if the album isn't loaded.
        """
        if not self.is_loaded:
            return None
        return lib.sp_album_year(self._sp_album)

    @property
    def type(self):
        """The album's :class:`AlbumType`.

        Will always return :class:`None` if the album isn't loaded.
        """
        if not self.is_loaded:
            return None
        return AlbumType(lib.sp_album_type(self._sp_album))

    @property
    def link(self):
        """A :class:`Link` to the album."""
        sp_link = lib.sp_link_create_from_album(self._sp_album)
        return spotify.Link(self._session, sp_link=sp_link, add_ref=False)

    def browse(self, callback=None):
        """Get an :class:`AlbumBrowser` for the album.

        If ``callback`` isn't :class:`None`, it is expected to be a callable
        that accepts a single argument, an :class:`AlbumBrowser` instance, when
        the browser is done loading.

        Can be created without the album being loaded.
        """
        return spotify.AlbumBrowser(
            self._session, album=self, callback=callback)


class AlbumBrowser(object):
    """An album browser for a Spotify album.

    You can get an album browser from any :class:`Album` instance by calling
    :meth:`Album.browse`::

        >>> session = spotify.Session()
        # ...
        >>> album = session.get_album('spotify:album:6wXDbHLesy6zWqQawAa91d')
        >>> browser = album.browse()
        >>> browser.load()
        >>> len(browser.tracks)
        7
    """

    def __init__(
            self, session, album=None, callback=None,
            sp_albumbrowse=None, add_ref=True):

        assert album or sp_albumbrowse, 'album or sp_albumbrowse is required'

        self._session = session
        self.loaded_event = threading.Event()

        if sp_albumbrowse is None:
            handle = ffi.new_handle((self._session, self, callback))
            self._session._callback_handles.add(handle)

            sp_albumbrowse = lib.sp_albumbrowse_create(
                self._session._sp_session, album._sp_album,
                _albumbrowse_complete_callback, handle)
            add_ref = False

        if add_ref:
            lib.sp_albumbrowse_add_ref(sp_albumbrowse)
        self._sp_albumbrowse = ffi.gc(
            sp_albumbrowse, lib.sp_albumbrowse_release)

    def __repr__(self):
        if self.is_loaded:
            return 'AlbumBrowser(%r)' % self.album.link.uri
        else:
            return 'AlbumBrowser(<not loaded>)'

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self._sp_albumbrowse == other._sp_albumbrowse
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self._sp_albumbrowse)

    loaded_event = None
    """:class:`threading.Event` that is set when the album browser is loaded.
    """

    @property
    def is_loaded(self):
        """Whether the album browser's data is loaded."""
        return bool(lib.sp_albumbrowse_is_loaded(self._sp_albumbrowse))

    def load(self, timeout=None):
        """Block until the album browser's data is loaded.

        After ``timeout`` seconds with no results :exc:`~spotify.Timeout` is
        raised. If ``timeout`` is :class:`None` the default timeout is used.

        The method returns ``self`` to allow for chaining of calls.
        """
        return utils.load(self._session, self, timeout=timeout)

    @property
    def error(self):
        """An :class:`ErrorType` associated with the album browser.

        Check to see if there was problems creating the album browser.
        """
        return spotify.ErrorType(
            lib.sp_albumbrowse_error(self._sp_albumbrowse))

    @property
    def backend_request_duration(self):
        """The time in ms that was spent waiting for the Spotify backend to
        create the album browser.

        Returns ``-1`` if the request was served from local cache. Returns
        :class:`None` if the album browser isn't loaded yet.
        """
        if not self.is_loaded:
            return None
        return lib.sp_albumbrowse_backend_request_duration(
            self._sp_albumbrowse)

    @property
    @serialized
    def album(self):
        """Get the :class:`Album` the browser is for.

        Will always return :class:`None` if the album isn't loaded.
        """
        sp_album = lib.sp_albumbrowse_album(self._sp_albumbrowse)
        if sp_album == ffi.NULL:
            return None
        return Album(self._session, sp_album=sp_album, add_ref=True)

    @property
    @serialized
    def artist(self):
        """The :class:`Artist` of the album.

        Will always return :class:`None` if the album isn't loaded.
        """
        sp_artist = lib.sp_albumbrowse_artist(self._sp_albumbrowse)
        if sp_artist == ffi.NULL:
            return None
        return spotify.Artist(self._session, sp_artist=sp_artist, add_ref=True)

    @property
    @serialized
    def copyrights(self):
        """The album's copyright strings.

        Will always return an empty list if the album browser isn't loaded.
        """
        if not self.is_loaded:
            return []

        @serialized
        def get_copyright(sp_albumbrowse, key):
            return utils.to_unicode(
                lib.sp_albumbrowse_copyright(sp_albumbrowse, key))

        return utils.Sequence(
            sp_obj=self._sp_albumbrowse,
            add_ref_func=lib.sp_albumbrowse_add_ref,
            release_func=lib.sp_albumbrowse_release,
            len_func=lib.sp_albumbrowse_num_copyrights,
            getitem_func=get_copyright)

    @property
    @serialized
    def tracks(self):
        """The album's tracks.

        Will always return an empty list if the album browser isn't loaded.
        """
        if not self.is_loaded:
            return []

        @serialized
        def get_track(sp_albumbrowse, key):
            return spotify.Track(
                self._session,
                sp_track=lib.sp_albumbrowse_track(sp_albumbrowse, key),
                add_ref=True)

        return utils.Sequence(
            sp_obj=self._sp_albumbrowse,
            add_ref_func=lib.sp_albumbrowse_add_ref,
            release_func=lib.sp_albumbrowse_release,
            len_func=lib.sp_albumbrowse_num_tracks,
            getitem_func=get_track)

    @property
    @serialized
    def review(self):
        """A review of the album.

        Will always return an empty string if the album browser isn't loaded.
        """
        return utils.to_unicode(
            lib.sp_albumbrowse_review(self._sp_albumbrowse))


@ffi.callback('void(sp_albumbrowse *, void *)')
@serialized
def _albumbrowse_complete_callback(sp_albumbrowse, handle):
    logger.debug('albumbrowse_complete_callback called')
    if handle == ffi.NULL:
        logger.warning(
            'albumbrowse_complete_callback called without userdata')
        return
    (session, album_browser, callback) = ffi.from_handle(handle)
    session._callback_handles.remove(handle)
    album_browser.loaded_event.set()
    if callback is not None:
        callback(album_browser)


@utils.make_enum('SP_ALBUMTYPE_')
class AlbumType(utils.IntEnum):
    pass

########NEW FILE########
__FILENAME__ = artist
from __future__ import unicode_literals

import logging
import threading

import spotify
from spotify import ffi, lib, serialized, utils


__all__ = [
    'Artist',
    'ArtistBrowser',
    'ArtistBrowserType',
]

logger = logging.getLogger(__name__)


class Artist(object):
    """A Spotify artist.

    You can get artists from tracks and albums, or you can create an
    :class:`Artist` yourself from a Spotify URI::

        >>> session = spotify.Session()
        # ...
        >>> artist = session.get_artist(
        ...     'spotify:artist:22xRIphSN7IkPVbErICu7s')
        >>> artist.load().name
        u'Rob Dougan'
    """

    def __init__(self, session, uri=None, sp_artist=None, add_ref=True):
        assert uri or sp_artist, 'uri or sp_artist is required'

        self._session = session

        if uri is not None:
            artist = spotify.Link(self._session, uri=uri).as_artist()
            if artist is None:
                raise ValueError(
                    'Failed to get artist from Spotify URI: %r' % uri)
            sp_artist = artist._sp_artist

        if add_ref:
            lib.sp_artist_add_ref(sp_artist)
        self._sp_artist = ffi.gc(sp_artist, lib.sp_artist_release)

    def __repr__(self):
        return 'Artist(%r)' % self.link.uri

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self._sp_artist == other._sp_artist
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self._sp_artist)

    @property
    @serialized
    def name(self):
        """The artist's name.

        Will always return :class:`None` if the artist isn't loaded.
        """
        name = utils.to_unicode(lib.sp_artist_name(self._sp_artist))
        return name if name else None

    @property
    def is_loaded(self):
        """Whether the artist's data is loaded."""
        return bool(lib.sp_artist_is_loaded(self._sp_artist))

    def load(self, timeout=None):
        """Block until the artist's data is loaded.

        After ``timeout`` seconds with no results :exc:`~spotify.Timeout` is
        raised. If ``timeout`` is :class:`None` the default timeout is used.

        The method returns ``self`` to allow for chaining of calls.
        """
        return utils.load(self._session, self, timeout=timeout)

    @serialized
    def portrait(self, image_size=None, callback=None):
        """The artist's portrait :class:`Image`.

        ``image_size`` is an :class:`ImageSize` value, by default
        :attr:`ImageSize.NORMAL`.

        If ``callback`` isn't :class:`None`, it is expected to be a callable
        that accepts a single argument, an :class:`Image` instance, when
        the image is done loading.

        Will always return :class:`None` if the artist isn't loaded or the
        artist has no portrait.
        """
        if image_size is None:
            image_size = spotify.ImageSize.NORMAL
        portrait_id = lib.sp_artist_portrait(self._sp_artist, int(image_size))
        if portrait_id == ffi.NULL:
            return None
        sp_image = lib.sp_image_create(
            self._session._sp_session, portrait_id)
        return spotify.Image(
            self._session, sp_image=sp_image, add_ref=False, callback=callback)

    def portrait_link(self, image_size=None):
        """A :class:`Link` to the artist's portrait.

        ``image_size`` is an :class:`ImageSize` value, by default
        :attr:`ImageSize.NORMAL`.

        This is equivalent with ``artist.portrait(image_size).link``, except
        that this method does not need to create the artist portrait image
        object to create a link to it.
        """
        if image_size is None:
            image_size = spotify.ImageSize.NORMAL
        sp_link = lib.sp_link_create_from_artist_portrait(
            self._sp_artist, int(image_size))
        return spotify.Link(self._session, sp_link=sp_link, add_ref=False)

    @property
    def link(self):
        """A :class:`Link` to the artist."""
        sp_link = lib.sp_link_create_from_artist(self._sp_artist)
        return spotify.Link(self._session, sp_link=sp_link, add_ref=False)

    def browse(self, type=None, callback=None):
        """Get an :class:`ArtistBrowser` for the artist.

        If ``type`` is :class:`None`, it defaults to
        :attr:`ArtistBrowserType.FULL`.

        If ``callback`` isn't :class:`None`, it is expected to be a callable
        that accepts a single argument, an :class:`ArtistBrowser` instance,
        when the browser is done loading.

        Can be created without the artist being loaded.
        """
        return spotify.ArtistBrowser(
            self._session, artist=self, type=type, callback=callback)


class ArtistBrowser(object):
    """An artist browser for a Spotify artist.

    You can get an artist browser from any :class:`Artist` instance by calling
    :meth:`Artist.browse`::

        >>> session = spotify.Session()
        # ...
        >>> artist = session.get_artist(
        ...     'spotify:artist:421vyBBkhgRAOz4cYPvrZJ')
        >>> browser = artist.browse()
        >>> browser.load()
        >>> len(browser.albums)
        7
    """

    def __init__(
            self, session, artist=None, type=None, callback=None,
            sp_artistbrowse=None, add_ref=True):

        assert artist or sp_artistbrowse, (
            'artist or sp_artistbrowse is required')

        self._session = session
        self.loaded_event = threading.Event()

        if sp_artistbrowse is None:
            if type is None:
                type = ArtistBrowserType.FULL

            handle = ffi.new_handle((self._session, self, callback))
            self._session._callback_handles.add(handle)

            sp_artistbrowse = lib.sp_artistbrowse_create(
                self._session._sp_session, artist._sp_artist,
                int(type), _artistbrowse_complete_callback, handle)
            add_ref = False

        if add_ref:
            lib.sp_artistbrowse_add_ref(sp_artistbrowse)
        self._sp_artistbrowse = ffi.gc(
            sp_artistbrowse, lib.sp_artistbrowse_release)

    loaded_event = None
    """:class:`threading.Event` that is set when the artist browser is loaded.
    """

    def __repr__(self):
        if self.is_loaded:
            return 'ArtistBrowser(%r)' % self.artist.link.uri
        else:
            return 'ArtistBrowser(<not loaded>)'

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self._sp_artistbrowse == other._sp_artistbrowse
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self._sp_artistbrowse)

    @property
    def is_loaded(self):
        """Whether the artist browser's data is loaded."""
        return bool(lib.sp_artistbrowse_is_loaded(self._sp_artistbrowse))

    def load(self, timeout=None):
        """Block until the artist browser's data is loaded.

        After ``timeout`` seconds with no results :exc:`~spotify.Timeout` is
        raised. If ``timeout`` is :class:`None` the default timeout is used.

        The method returns ``self`` to allow for chaining of calls.
        """
        return utils.load(self._session, self, timeout=timeout)

    @property
    def error(self):
        """An :class:`ErrorType` associated with the artist browser.

        Check to see if there was problems creating the artist browser.
        """
        return spotify.ErrorType(
            lib.sp_artistbrowse_error(self._sp_artistbrowse))

    @property
    def backend_request_duration(self):
        """The time in ms that was spent waiting for the Spotify backend to
        create the artist browser.

        Returns ``-1`` if the request was served from local cache. Returns
        :class:`None` if the artist browser isn't loaded yet.
        """
        if not self.is_loaded:
            return None
        return lib.sp_artistbrowse_backend_request_duration(
            self._sp_artistbrowse)

    @property
    @serialized
    def artist(self):
        """Get the :class:`Artist` the browser is for.

        Will always return :class:`None` if the artist browser isn't loaded.
        """
        sp_artist = lib.sp_artistbrowse_artist(self._sp_artistbrowse)
        if sp_artist == ffi.NULL:
            return None
        return Artist(self._session, sp_artist=sp_artist, add_ref=True)

    @serialized
    def portraits(self, callback=None):
        """The artist's portraits.

        Due to limitations in libspotify's API you can't specify the
        :class:`ImageSize` of these images.

        If ``callback`` isn't :class:`None`, it is expected to be a callable
        that accepts a single argument, an :class:`Image` instance, when
        the image is done loading. The callable will be called once for each
        portrait.

        Will always return an empty list if the artist browser isn't loaded.
        """
        if not self.is_loaded:
            return []

        @serialized
        def get_image(sp_artistbrowse, key):
            image_id = lib.sp_artistbrowse_portrait(sp_artistbrowse, key)
            sp_image = lib.sp_image_create(image_id)
            return spotify.Image(
                self._session, sp_image=sp_image, add_ref=False,
                callback=callback)

        return utils.Sequence(
            sp_obj=self._sp_artistbrowse,
            add_ref_func=lib.sp_artistbrowse_add_ref,
            release_func=lib.sp_artistbrowse_release,
            len_func=lib.sp_artistbrowse_num_portraits,
            getitem_func=get_image)

    @property
    @serialized
    def tracks(self):
        """The artist's tracks.

        Will be an empty list if the browser was created with a ``type`` of
        :attr:`ArtistBrowserType.NO_TRACKS` or
        :attr:`ArtistBrowserType.NO_ALBUMS`.

        Will always return an empty list if the artist browser isn't loaded.
        """
        if not self.is_loaded:
            return []

        @serialized
        def get_track(sp_artistbrowse, key):
            return spotify.Track(
                self._session,
                sp_track=lib.sp_artistbrowse_track(sp_artistbrowse, key),
                add_ref=True)

        return utils.Sequence(
            sp_obj=self._sp_artistbrowse,
            add_ref_func=lib.sp_artistbrowse_add_ref,
            release_func=lib.sp_artistbrowse_release,
            len_func=lib.sp_artistbrowse_num_tracks,
            getitem_func=get_track)

    @property
    @serialized
    def tophit_tracks(self):
        """The artist's top hit tracks.

        Will always return an empty list if the artist browser isn't loaded.
        """
        if not self.is_loaded:
            return []

        @serialized
        def get_track(sp_artistbrowse, key):
            return spotify.Track(
                self._session,
                sp_track=lib.sp_artistbrowse_tophit_track(
                    sp_artistbrowse, key),
                add_ref=True)

        return utils.Sequence(
            sp_obj=self._sp_artistbrowse,
            add_ref_func=lib.sp_artistbrowse_add_ref,
            release_func=lib.sp_artistbrowse_release,
            len_func=lib.sp_artistbrowse_num_tophit_tracks,
            getitem_func=get_track)

    @property
    @serialized
    def albums(self):
        """The artist's albums.

        Will be an empty list if the browser was created with a ``type`` of
        :attr:`ArtistBrowserType.NO_ALBUMS`.

        Will always return an empty list if the artist browser isn't loaded.
        """
        if not self.is_loaded:
            return []

        @serialized
        def get_album(sp_artistbrowse, key):
            return spotify.Album(
                self._session,
                sp_album=lib.sp_artistbrowse_album(sp_artistbrowse, key),
                add_ref=True)

        return utils.Sequence(
            sp_obj=self._sp_artistbrowse,
            add_ref_func=lib.sp_artistbrowse_add_ref,
            release_func=lib.sp_artistbrowse_release,
            len_func=lib.sp_artistbrowse_num_albums,
            getitem_func=get_album)

    @property
    @serialized
    def similar_artists(self):
        """The artist's similar artists.

        Will always return an empty list if the artist browser isn't loaded.
        """
        if not self.is_loaded:
            return []

        @serialized
        def get_artist(sp_artistbrowse, key):
            return spotify.Artist(
                self._session,
                sp_artist=lib.sp_artistbrowse_similar_artist(
                    sp_artistbrowse, key),
                add_ref=True)

        return utils.Sequence(
            sp_obj=self._sp_artistbrowse,
            add_ref_func=lib.sp_artistbrowse_add_ref,
            release_func=lib.sp_artistbrowse_release,
            len_func=lib.sp_artistbrowse_num_similar_artists,
            getitem_func=get_artist)

    @property
    @serialized
    def biography(self):
        """A biography of the artist.

        Will always return an empty string if the artist browser isn't loaded.
        """
        return utils.to_unicode(
            lib.sp_artistbrowse_biography(self._sp_artistbrowse))


@ffi.callback('void(sp_artistbrowse *, void *)')
@serialized
def _artistbrowse_complete_callback(sp_artistbrowse, handle):
    logger.debug('artistbrowse_complete_callback called')
    if handle == ffi.NULL:
        logger.warning(
            'artistbrowse_complete_callback called without userdata')
        return
    (session, artist_browser, callback) = ffi.from_handle(handle)
    session._callback_handles.remove(handle)
    artist_browser.loaded_event.set()
    if callback is not None:
        callback(artist_browser)


@utils.make_enum('SP_ARTISTBROWSE_')
class ArtistBrowserType(utils.IntEnum):
    pass

########NEW FILE########
__FILENAME__ = audio
from __future__ import unicode_literals

import collections

from spotify import utils


__all__ = [
    'AudioBufferStats',
    'AudioFormat',
    'Bitrate',
    'SampleType',
]


class AudioBufferStats(collections.namedtuple(
        'AudioBufferStats', ['samples', 'stutter'])):
    """Stats about the application's audio buffers."""
    pass


@utils.make_enum('SP_BITRATE_', 'BITRATE_')
class Bitrate(utils.IntEnum):
    pass


@utils.make_enum('SP_SAMPLETYPE_')
class SampleType(utils.IntEnum):
    pass


class AudioFormat(object):
    """A Spotify audio format object.

    You'll never need to create an instance of this class yourself, but you'll
    get :class:`AudioFormat` objects as the ``audio_format`` argument to the
    :attr:`~spotify.SessionCallbacks.music_delivery` callback.
    """

    def __init__(self, sp_audioformat):
        self._sp_audioformat = sp_audioformat

    @property
    def sample_type(self):
        """The :class:`SampleType`, currently always
        :attr:`SampleType.INT16_NATIVE_ENDIAN`."""
        return SampleType(self._sp_audioformat.sample_type)

    @property
    def sample_rate(self):
        """The sample rate, typically 44100 Hz."""
        return self._sp_audioformat.sample_rate

    @property
    def channels(self):
        """The number of audio channels, typically 2."""
        return self._sp_audioformat.channels

    def frame_size(self):
        """The byte size of a single frame of this format."""
        if self.sample_type == SampleType.INT16_NATIVE_ENDIAN:
            return 2 * self.channels
        else:
            raise ValueError('Unknown sample type: %d', self.sample_type)

########NEW FILE########
__FILENAME__ = config
from __future__ import unicode_literals

import spotify
from spotify import ffi, utils
from spotify.session import _SessionCallbacks

__all__ = [
    'Config',
]


class Config(object):
    """The session config.

    Create an instance and assign to its attributes to configure. Then use the
    config object to create a session::

        >>> config = spotify.Config()
        >>> config.user_agent = 'My awesome Spotify client'
        >>> # Etc ...
        >>> session = spotify.Session(config=config)
    """

    def __init__(self):
        self._sp_session_callbacks = _SessionCallbacks.get_struct()
        self._sp_session_config = ffi.new('sp_session_config *', {
            'callbacks': self._sp_session_callbacks,
        })

        # Defaults
        self.api_version = spotify.get_libspotify_api_version()
        self.cache_location = b'tmp'
        self.settings_location = b'tmp'
        self.user_agent = 'pyspotify %s' % spotify.__version__
        self.compress_playlists = False
        self.dont_save_metadata_for_playlists = False
        self.initially_unload_playlists = False

    @property
    def api_version(self):
        """The API version of the libspotify we're using.

        You should not need to change this. It defaults to the value provided
        by libspotify through :func:`spotify.get_libspotify_api_version`.
        """
        return self._sp_session_config.api_version

    @api_version.setter
    def api_version(self, value):
        self._sp_session_config.api_version = value

    @property
    def cache_location(self):
        """A location for libspotify to cache files.

        Defaults to ``tmp`` in the current working directory.

        Must be a bytestring. Cannot be shared with other Spotify apps. Can
        only be used by one session at the time. Optimally, you should use a
        lock file or similar to ensure this.
        """
        return utils.to_bytes_or_none(self._sp_session_config.cache_location)

    @cache_location.setter
    def cache_location(self, value):
        self._cache_location = utils.to_char_or_null(value)
        self._sp_session_config.cache_location = self._cache_location

    @property
    def settings_location(self):
        """A location for libspotify to save settings.

        Defaults to ``tmp`` in the current working directory.

        Must be a bytestring. Cannot be shared with other Spotify apps. Can
        only be used by one session at the time. Optimally, you should use a
        lock file or similar to ensure this.
        """
        return utils.to_bytes_or_none(
            self._sp_session_config.settings_location)

    @settings_location.setter
    def settings_location(self, value):
        self._settings_location = utils.to_char_or_null(value)
        self._sp_session_config.settings_location = self._settings_location

    @property
    def application_key(self):
        """Your libspotify application key.

        Must be a bytestring. Alternatively, you can call
        :meth:`load_application_key_file`, and pyspotify will correctly read
        the file into :attr:`application_key`.
        """
        return utils.to_bytes_or_none(
            ffi.cast('char *', self._sp_session_config.application_key))

    @application_key.setter
    def application_key(self, value):
        if value is None:
            size = 0
        else:
            size = len(value)
        assert size in (0, 321), (
            'Invalid application key; expected 321 bytes, got %d bytes' % size)

        self._application_key = utils.to_char_or_null(value)
        self._sp_session_config.application_key = ffi.cast(
            'void *', self._application_key)
        self._sp_session_config.application_key_size = size

    def load_application_key_file(self, filename=b'spotify_appkey.key'):
        """Load your libspotify application key file.

        If called without arguments, it tries to read ``spotify_appkey.key``
        from the current working directory.

        This is an alternative to setting :attr:`application_key` yourself. The
        file must be a binary key file, not the C code key file that can be
        compiled into an application.
        """
        with open(filename, 'rb') as fh:
            self.application_key = fh.read()

    @property
    def user_agent(self):
        """A string with the name of your client.

        Defaults to ``pyspotify 2.x.y``.
        """
        return utils.to_unicode_or_none(self._sp_session_config.user_agent)

    @user_agent.setter
    def user_agent(self, value):
        self._user_agent = utils.to_char_or_null(value)
        self._sp_session_config.user_agent = self._user_agent

    @property
    def compress_playlists(self):
        """Compress local copy of playlists, reduces disk space usage.

        Defaults to :class:`False`.
        """
        return bool(self._sp_session_config.compress_playlists)

    @compress_playlists.setter
    def compress_playlists(self, value):
        self._sp_session_config.compress_playlists = bool(value)

    @property
    def dont_save_metadata_for_playlists(self):
        """Don't save metadata for local copies of playlists.

        Defaults to :class:`False`.

        Reduces disk space usage at the expense of needing to request metadata
        from Spotify backend when loading list.
        """
        return bool(self._sp_session_config.dont_save_metadata_for_playlists)

    @dont_save_metadata_for_playlists.setter
    def dont_save_metadata_for_playlists(self, value):
        self._sp_session_config.dont_save_metadata_for_playlists = bool(value)

    @property
    def initially_unload_playlists(self):
        """Avoid loading playlists into RAM on startup.

        Defaults to :class:`False`.

        See :meth:`Playlist.in_ram` for more details.
        """
        return bool(self._sp_session_config.initially_unload_playlists)

    @initially_unload_playlists.setter
    def initially_unload_playlists(self, value):
        self._sp_session_config.initially_unload_playlists = bool(value)

    @property
    def device_id(self):
        """Device ID for offline synchronization and logging purposes.

        Defaults to :class:`None`.

        The Device ID must be unique to the particular device instance, i.e. no
        two units must supply the same Device ID. The Device ID must not change
        between sessions or power cycles. Good examples is the device's MAC
        address or unique serial number.
        """
        return utils.to_unicode_or_none(self._sp_session_config.device_id)

    @device_id.setter
    def device_id(self, value):
        self._device_id = utils.to_char_or_null(value)
        self._sp_session_config.device_id = self._device_id

    @property
    def proxy(self):
        """URL to the proxy server that should be used.

        Defaults to :class:`None`.

        The format is protocol://host:port where protocol is
        http/https/socks4/socks5.
        """
        return utils.to_unicode_or_none(self._sp_session_config.proxy)

    @proxy.setter
    def proxy(self, value):
        self._proxy = utils.to_char_or_null(value)
        self._sp_session_config.proxy = self._proxy

    @property
    def proxy_username(self):
        """Username to authenticate with proxy server.

        Defaults to :class:`None`.
        """
        return utils.to_unicode_or_none(self._sp_session_config.proxy_username)

    @proxy_username.setter
    def proxy_username(self, value):
        self._proxy_username = utils.to_char_or_null(value)
        self._sp_session_config.proxy_username = self._proxy_username

    @property
    def proxy_password(self):
        """Password to authenticate with proxy server.

        Defaults to :class:`None`.
        """
        return utils.to_unicode_or_none(self._sp_session_config.proxy_password)

    @proxy_password.setter
    def proxy_password(self, value):
        self._proxy_password = utils.to_char_or_null(value)
        self._sp_session_config.proxy_password = self._proxy_password

    @property
    def ca_certs_filename(self):
        """Path to a file containing the root CA certificates that HTTPS
        servers should be verified with.

        Defaults to :class:`None`. Must be a bytestring file path otherwise.

        This is not used for verifying Spotify's servers, but may be
        used for verifying third parties' HTTPS servers, like the Last.fm
        servers if you scrobbling the music you listen to through libspotify.

        libspotify for OS X use other means for communicating with HTTPS
        servers and ignores this configuration.

        The file must be a concatenation of all certificates in PEM format.
        Provided with libspotify is a sample PEM file in the ``examples/``
        dir. It is recommended that the application export a similar file
        from the local certificate store. On Linux systems, the certificate
        store is often found at :file:`/etc/ssl/certs/ca-certificates.crt` or
        :file:`/etc/ssl/certs/ca-bundle.crt`
        """
        ptr = self._get_ca_certs_filename_ptr()
        if ptr is not None:
            return utils.to_bytes_or_none(ptr[0])
        else:
            return None

    @ca_certs_filename.setter
    def ca_certs_filename(self, value):
        ptr = self._get_ca_certs_filename_ptr()
        if ptr is not None:
            self._ca_certs_filename = utils.to_char_or_null(value)
            ptr[0] = self._ca_certs_filename

    def _get_ca_certs_filename_ptr(self):
        # XXX This function does pointer arithmetic based on the assumption
        # that if the ca_certs_filename field exists in sp_session_config on
        # the current platform, it will reside between the proxy_password and
        # tracefile fields.
        #
        # If CFFI supported #ifdef we could make this exact
        # science by including ca_certs_filename field in the sp_session_config
        # struct only if the SP_WITH_CURL macro is defined, ref. the
        # sp_session_create example in the libspotify docs.
        proxy_password_ptr = spotify.ffi.addressof(
            self._sp_session_config, 'proxy_password')
        tracefile_ptr = spotify.ffi.addressof(
            self._sp_session_config, 'tracefile')
        if tracefile_ptr - proxy_password_ptr != 2:
            return None
        return proxy_password_ptr + 1

    @property
    def tracefile(self):
        """Path to API trace file.

        Defaults to :class:`None`. Must be a bytestring otherwise.
        """
        return utils.to_bytes_or_none(self._sp_session_config.tracefile)

    @tracefile.setter
    def tracefile(self, value):
        self._tracefile = utils.to_char_or_null(value)
        self._sp_session_config.tracefile = self._tracefile

########NEW FILE########
__FILENAME__ = connection
from __future__ import unicode_literals

import functools
import operator

import spotify
from spotify import lib, utils


__all__ = [
    'ConnectionRule',
    'ConnectionState',
    'ConnectionType',
]


class Connection(object):
    """Connection controller.

    You'll never need to create an instance of this class yourself. You'll find
    it ready to use as the :attr:`~Session.connection` attribute on the
    :class:`Session` instance.
    """

    def __init__(self, session):
        self._session = session

        # The following defaults are based on the libspotify documentation
        self._connection_type = spotify.ConnectionType.UNKNOWN
        self._allow_network = True
        self._allow_network_if_roaming = False
        self._allow_sync_over_wifi = True
        self._allow_sync_over_mobile = False

    @property
    def state(self):
        """The session's current :class:`ConnectionState`.

        The connection state involves two components, authentication and
        offline mode. The mapping is as follows

        - :attr:`~ConnectionState.LOGGED_OUT`: not authenticated, offline
        - :attr:`~ConnectionState.OFFLINE`: authenticated, offline
        - :attr:`~ConnectionState.LOGGED_IN`: authenticated, online
        - :attr:`~ConnectionState.DISCONNECTED`: authenticated, offline, was
          previously online

        Register listeners for the
        :attr:`spotify.SessionEvent.CONNECTION_STATE_UPDATED` event to be
        notified when the connection state changes.
        """
        return spotify.ConnectionState(
            lib.sp_session_connectionstate(self._session._sp_session))

    @property
    def type(self):
        """The session's :class:`ConnectionType`.

        Defaults to :attr:`ConnectionType.UNKNOWN`. Set to a
        :class:`ConnectionType` value to tell libspotify what type of
        connection you're using.

        This is used together with :attr:`~Connection.allow_network`,
        :attr:`~Connection.allow_network_if_roaming`,
        :attr:`~Connection.allow_sync_over_wifi`, and
        :attr:`~Connection.allow_sync_over_mobile` to control offline syncing
        and network usage.
        """
        return self._connection_type

    @type.setter
    def type(self, value):
        spotify.Error.maybe_raise(lib.sp_session_set_connection_type(
            self._session._sp_session, value))
        self._connection_type = value

    @property
    def allow_network(self):
        """Whether or not network access is allowed at all.

        Defaults to :class:`True`. Setting this to :class:`False` turns on
        offline mode.
        """
        return self._allow_network

    @allow_network.setter
    def allow_network(self, value):
        self._allow_network = value
        self._update_connection_rules()

    @property
    def allow_network_if_roaming(self):
        """Whether or not network access is allowed if :attr:`~Connection.type`
        is set to :attr:`ConnectionType.MOBILE_ROAMING`.

        Defaults to :class:`False`.
        """
        return self._allow_network_if_roaming

    @allow_network_if_roaming.setter
    def allow_network_if_roaming(self, value):
        self._allow_network_if_roaming = value
        self._update_connection_rules()

    @property
    def allow_sync_over_wifi(self):
        """Whether or not offline syncing is allowed when
        :attr:`~Connection.type` is set to :attr:`ConnectionType.WIFI`.

        Defaults to :class:`True`.
        """
        return self._allow_sync_over_wifi

    @allow_sync_over_wifi.setter
    def allow_sync_over_wifi(self, value):
        self._allow_sync_over_wifi = value
        self._update_connection_rules()

    @property
    def allow_sync_over_mobile(self):
        """Whether or not offline syncing is allowed when
        :attr:`~Connection.type` is set to :attr:`ConnectionType.MOBILE`, or
        :attr:`allow_network_if_roaming` is :class:`True` and
        :attr:`~Connection.type` is set to
        :attr:`ConnectionType.MOBILE_ROAMING`.

        Defaults to :class:`True`.
        """
        return self._allow_sync_over_mobile

    @allow_sync_over_mobile.setter
    def allow_sync_over_mobile(self, value):
        self._allow_sync_over_mobile = value
        self._update_connection_rules()

    def _update_connection_rules(self):
        rules = []
        if self._allow_network:
            rules.append(spotify.ConnectionRule.NETWORK)
        if self._allow_network_if_roaming:
            rules.append(spotify.ConnectionRule.NETWORK_IF_ROAMING)
        if self._allow_sync_over_wifi:
            rules.append(spotify.ConnectionRule.ALLOW_SYNC_OVER_WIFI)
        if self._allow_sync_over_mobile:
            rules.append(spotify.ConnectionRule.ALLOW_SYNC_OVER_MOBILE)
        rules = functools.reduce(operator.or_, rules, 0)
        spotify.Error.maybe_raise(lib.sp_session_set_connection_rules(
            self._session._sp_session, rules))


@utils.make_enum('SP_CONNECTION_RULE_')
class ConnectionRule(utils.IntEnum):
    pass


@utils.make_enum('SP_CONNECTION_STATE_')
class ConnectionState(utils.IntEnum):
    pass


@utils.make_enum('SP_CONNECTION_TYPE_')
class ConnectionType(utils.IntEnum):
    pass

########NEW FILE########
__FILENAME__ = error
from __future__ import unicode_literals

from spotify import lib, serialized, utils


__all__ = [
    'Error',
    'ErrorType',
    'LibError',
    'Timeout',
]


class Error(Exception):
    """A Spotify error.

    This is the superclass of all custom exceptions raised by pyspotify.
    """

    @classmethod
    def maybe_raise(cls, error_type, ignores=None):
        """Raise an :exc:`LibError` unless the ``error_type`` is
        :attr:`ErrorType.OK` or in the ``ignores`` list of error types.

        Internal method.
        """
        ignores = set(ignores or [])
        ignores.add(ErrorType.OK)
        if error_type not in ignores:
            raise LibError(error_type)


@utils.make_enum('SP_ERROR_')
class ErrorType(utils.IntEnum):
    pass


class LibError(Error):
    """A libspotify error.

    Where many libspotify functions return error codes that must be checked
    after each and every function call, pyspotify raises the
    :exc:`LibError` exception instead. This helps you to not accidentally
    swallow and hide errors when using pyspotify.
    """

    error_type = None
    """The :class:`ErrorType` of the error."""

    @serialized
    def __init__(self, error_type):
        self.error_type = error_type
        message = utils.to_unicode(lib.sp_error_message(error_type))
        super(Error, self).__init__(message)

    def __eq__(self, other):
        return self.error_type == getattr(other, 'error_type', None)

    def __ne__(self, other):
        return not self.__eq__(other)


for attr in dir(lib):
    if attr.startswith('SP_ERROR_'):
        name = attr.replace('SP_ERROR_', '')
        error_no = getattr(lib, attr)
        setattr(LibError, name, LibError(error_no))


class Timeout(Error):
    """Exception raised by an operation not completing within the given
    timeout."""

    def __init__(self, timeout):
        message = 'Operation did not complete in %.3fs' % timeout
        super(Timeout, self).__init__(message)

########NEW FILE########
__FILENAME__ = eventloop
from __future__ import unicode_literals

import logging
import threading

try:
    # Python 3
    import queue
except ImportError:
    # Python 2
    import Queue as queue

import spotify


__all__ = [
    'EventLoop',
]

logger = logging.getLogger(__name__)


class EventLoop(threading.Thread):
    """Event loop for automatically processing events from libspotify.

    The event loop is a :class:`~threading.Thread` that listens to
    :attr:`~spotify.SessionEvent.NOTIFY_MAIN_THREAD` events and calls
    :meth:`~spotify.Session.process_events` when needed.

    To use it, pass it your :class:`~spotify.Session` instance and call
    :meth:`start`::

        >>> session = spotify.Session()
        >>> event_loop = spotify.EventLoop(session)
        >>> event_loop.start()

    The event loop thread is a daemon thread, so it will not stop your
    application from exiting. If you wish to stop the event loop without
    stopping your entire application, call :meth:`stop`. You may call
    :meth:`~threading.Thread.join` to block until the event loop thread has
    finished, just like for any other thread.

    .. warning::

        If you use :class:`EventLoop` to process the libspotify events, any
        event listeners you've registered will be called from the event loop
        thread. pyspotify itself is thread safe, but you'll need to ensure that
        you have proper synchronization in your own application code, as always
        when working with threads.
    """

    daemon = True
    name = 'SpotifyEventLoop'

    def __init__(self, session):
        threading.Thread.__init__(self)

        self._session = session
        self._runnable = True
        self._queue = queue.Queue()

    def start(self):
        """Start the event loop."""
        self._session.on(
            spotify.SessionEvent.NOTIFY_MAIN_THREAD,
            self._on_notify_main_thread)
        threading.Thread.start(self)

    def stop(self):
        """Stop the event loop."""
        self._runnable = False
        self._session.off(
            spotify.SessionEvent.NOTIFY_MAIN_THREAD,
            self._on_notify_main_thread)

    def run(self):
        logger.debug('Spotify event loop started')
        timeout = self._session.process_events() / 1000.0
        while self._runnable:
            try:
                logger.debug('Waiting %.3fs for new events', timeout)
                self._queue.get(timeout=timeout)
            except queue.Empty:
                logger.debug('Timeout reached; processing events')
            else:
                logger.debug('Notification received; processing events')
            finally:
                timeout = self._session.process_events() / 1000.0
        logger.debug('Spotify event loop stopped')

    def _on_notify_main_thread(self, session):
        # WARNING: This event listener is called from an internal libspotify
        # thread. It must not block.
        try:
            self._queue.put_nowait(1)
        except queue.Full:
            logger.warning(
                'Event loop queue full; dropped notification event')

########NEW FILE########
__FILENAME__ = image
from __future__ import unicode_literals

import base64
import logging
import threading

import spotify
from spotify import ffi, lib, serialized, utils


__all__ = [
    'Image',
    'ImageFormat',
    'ImageSize',
]

logger = logging.getLogger(__name__)


class Image(object):
    """A Spotify image.

    You can get images from :meth:`Album.cover`, :meth:`Artist.portrait`, or
    you can create an :class:`Image` yourself from a Spotify URI::

        >>> session = spotify.Session()
        # ...
        >>> image = session.get_image(
        ...     'spotify:image:a0bdcbe11b5cd126968e519b5ed1050b0e8183d0')
        >>> image.load().data_uri[:50]
        u'data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEBLAEsAAD'

    If ``callback`` isn't :class:`None`, it is expected to be a callable
    that accepts a single argument, an :class:`Image` instance, when
    the image is done loading.
    """

    def __init__(
            self, session, uri=None, sp_image=None, add_ref=True,
            callback=None):

        assert uri or sp_image, 'uri or sp_image is required'

        self._session = session

        if uri is not None:
            image = spotify.Link(self._session, uri=uri).as_image()
            if image is None:
                raise ValueError(
                    'Failed to get image from Spotify URI: %r' % uri)
            sp_image = image._sp_image
            add_ref = True

        if add_ref:
            lib.sp_image_add_ref(sp_image)
        self._sp_image = ffi.gc(sp_image, lib.sp_image_release)

        self.loaded_event = threading.Event()

        handle = ffi.new_handle((self._session, self, callback))
        self._session._callback_handles.add(handle)
        spotify.Error.maybe_raise(lib.sp_image_add_load_callback(
            self._sp_image, _image_load_callback, handle))

    def __repr__(self):
        return 'Image(%r)' % self.link.uri

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self._sp_image == other._sp_image
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self._sp_image)

    loaded_event = None
    """:class:`threading.Event` that is set when the image is loaded."""

    @property
    def is_loaded(self):
        """Whether the image's data is loaded."""
        return bool(lib.sp_image_is_loaded(self._sp_image))

    @property
    def error(self):
        """An :class:`ErrorType` associated with the image.

        Check to see if there was problems loading the image.
        """
        return spotify.ErrorType(lib.sp_image_error(self._sp_image))

    def load(self, timeout=None):
        """Block until the image's data is loaded.

        After ``timeout`` seconds with no results :exc:`~spotify.Timeout` is
        raised. If ``timeout`` is :class:`None` the default timeout is used.

        The method returns ``self`` to allow for chaining of calls.
        """
        return utils.load(self._session, self, timeout=timeout)

    @property
    def format(self):
        """The :class:`ImageFormat` of the image.

        Will always return :class:`None` if the image isn't loaded.
        """
        if not self.is_loaded:
            return None
        return ImageFormat(lib.sp_image_format(self._sp_image))

    @property
    @serialized
    def data(self):
        """The raw image data as a bytestring.

        Will always return :class:`None` if the image isn't loaded.
        """
        if not self.is_loaded:
            return None
        data_size_ptr = ffi.new('size_t *')
        data = lib.sp_image_data(self._sp_image, data_size_ptr)
        buffer_ = ffi.buffer(data, data_size_ptr[0])
        data_bytes = buffer_[:]
        assert len(data_bytes) == data_size_ptr[0], '%r == %r' % (
            len(data_bytes), data_size_ptr[0])
        return data_bytes

    @property
    def data_uri(self):
        """The raw image data as a data: URI.

        Will always return :class:`None` if the image isn't loaded.
        """
        if not self.is_loaded:
            return None
        if self.format is not ImageFormat.JPEG:
            raise ValueError('Unknown image format: %r' % self.format)
        return 'data:image/jpeg;base64,%s' % (
            base64.b64encode(self.data).decode('ascii'))

    @property
    def link(self):
        """A :class:`Link` to the image."""
        return spotify.Link(
            self._session,
            sp_link=lib.sp_link_create_from_image(self._sp_image),
            add_ref=False)


@ffi.callback('void(sp_image *, void *)')
@serialized
def _image_load_callback(sp_image, handle):
    logger.debug('image_load_callback called')
    if handle == ffi.NULL:
        logger.warning('image_load_callback called without userdata')
        return
    (session, image, callback) = ffi.from_handle(handle)
    session._callback_handles.remove(handle)
    image.loaded_event.set()
    if callback is not None:
        callback(image)

    # Load callbacks are by nature only called once per image, so we clean up
    # and remove the load callback the first time it is called.
    lib.sp_image_remove_load_callback(sp_image, _image_load_callback, handle)


@utils.make_enum('SP_IMAGE_FORMAT_')
class ImageFormat(utils.IntEnum):
    pass


@utils.make_enum('SP_IMAGE_SIZE_')
class ImageSize(utils.IntEnum):
    pass

########NEW FILE########
__FILENAME__ = inbox
from __future__ import unicode_literals

import logging
import threading

import spotify
from spotify import ffi, lib, serialized, utils


__all__ = [
    'InboxPostResult',
]

logger = logging.getLogger(__name__)


class InboxPostResult(object):
    """The result object returned by :meth:`Session.inbox_post_tracks`."""

    @serialized
    def __init__(
            self, session, canonical_username=None, tracks=None, message='',
            callback=None, sp_inbox=None, add_ref=True):

        assert canonical_username and tracks or sp_inbox, \
            'canonical_username and tracks, or sp_inbox, is required'

        self._session = session
        self.loaded_event = threading.Event()

        if sp_inbox is None:
            canonical_username = utils.to_char(canonical_username)

            if isinstance(tracks, spotify.Track):
                tracks = [tracks]

            message = utils.to_char(message)

            handle = ffi.new_handle((self._session, self, callback))
            self._session._callback_handles.add(handle)

            sp_inbox = lib.sp_inbox_post_tracks(
                self._session._sp_session, canonical_username,
                [t._sp_track for t in tracks], len(tracks),
                message, _inboxpost_complete_callback, handle)
            add_ref = True

            if sp_inbox == ffi.NULL:
                raise spotify.Error('Inbox post request failed to initialize')

        if add_ref:
            lib.sp_inbox_add_ref(sp_inbox)
        self._sp_inbox = ffi.gc(sp_inbox, lib.sp_inbox_release)

    loaded_event = None
    """:class:`threading.Event` that is set when the inbox post result is
    loaded.
    """

    def __repr__(self):
        if not self.loaded_event.is_set():
            return 'InboxPostResult(<pending>)'
        else:
            return 'InboxPostResult(%s)' % self.error._name

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self._sp_inbox == other._sp_inbox
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self._sp_inbox)

    @property
    def error(self):
        """An :class:`ErrorType` associated with the inbox post result.

        Check to see if there was problems posting to the inbox.
        """
        return spotify.ErrorType(lib.sp_inbox_error(self._sp_inbox))


@ffi.callback('void(sp_inbox *, void *)')
@serialized
def _inboxpost_complete_callback(sp_inbox, handle):
    logger.debug('inboxpost_complete_callback called')
    if handle == ffi.NULL:
        logger.warning('inboxpost_complete_callback called without userdata')
        return
    (session, inbox_post_result, callback) = ffi.from_handle(handle)
    session._callback_handles.remove(handle)
    inbox_post_result.loaded_event.set()
    if callback is not None:
        callback(inbox_post_result)

########NEW FILE########
__FILENAME__ = link
from __future__ import unicode_literals

try:
    # Python 3
    from urllib.parse import urlparse  # noqa
except ImportError:
    # Python 2
    from urlparse import urlparse  # noqa

import spotify
from spotify import ffi, lib, serialized, utils

__all__ = [
    'Link',
    'LinkType',
]


class Link(object):
    """A Spotify object link.

    Call the :meth:`~Session.get_link` method on your :class:`Session` instance
    to get a :class:`Link` object from a Spotify URI.  You can also get links
    from the ``link`` attribute on most objects, e.g. :attr:`Track.link`.

    To get the URI from the link object you can use the :attr:`uri` attribute,
    or simply use the link as a string::

        >>> session = spotify.Session()
        # ...
        >>> link = session.get_link(
        ...     'spotify:track:2Foc5Q5nqNiosCNqttzHof')
        >>> link
        Link('spotify:track:2Foc5Q5nqNiosCNqttzHof')
        >>> link.uri
        'spotify:track:2Foc5Q5nqNiosCNqttzHof'
        >>> str(link)
        'spotify:track:2Foc5Q5nqNiosCNqttzHof'
        >>> link.type
        <LinkType.TRACK: 1>
        >>> track = link.as_track()
        >>> track.link
        Link('spotify:track:2Foc5Q5nqNiosCNqttzHof')
        >>> track.load().name
        u'Get Lucky'

    You can also get :class:`Link` objects from open.spotify.com and
    play.spotify.com URLs::

        >>> session.get_link(
        ...     'http://open.spotify.com/track/4wl1dK5dHGp3Ig51stvxb0')
        Link('spotify:track:4wl1dK5dHGp3Ig51stvxb0')
        >>> session.get_link(
        ...     'https://play.spotify.com/track/4wl1dK5dHGp3Ig51stvxb0'
        ...     '?play=true&utm_source=open.spotify.com&utm_medium=open')
        Link('spotify:track:4wl1dK5dHGp3Ig51stvxb0')
    """

    def __init__(self, session, uri=None, sp_link=None, add_ref=True):
        assert uri or sp_link, 'uri or sp_link is required'

        self._session = session

        if uri is not None:
            sp_link = lib.sp_link_create_from_string(
                utils.to_char(Link._normalize_uri(uri)))
            add_ref = False
            if sp_link == ffi.NULL:
                raise ValueError(
                    'Failed to get link from Spotify URI: %r' % uri)

        if add_ref:
            lib.sp_link_add_ref(sp_link)
        self._sp_link = ffi.gc(sp_link, lib.sp_link_release)

    @staticmethod
    def _normalize_uri(uri):
        if uri.startswith('spotify:'):
            return uri
        parsed = urlparse(uri)
        if parsed.netloc not in ('open.spotify.com', 'play.spotify.com'):
            return uri
        return 'spotify%s' % parsed.path.strip().replace('/', ':')

    def __repr__(self):
        return 'Link(%r)' % self.uri

    def __str__(self):
        return self.uri

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self._sp_link == other._sp_link
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self._sp_link)

    @property
    def uri(self):
        """The link's Spotify URI."""
        return utils.get_with_growing_buffer(
            lib.sp_link_as_string, self._sp_link)

    @property
    def url(self):
        """The link's HTTP URL."""
        return 'https://open.spotify.com%s' % (
            self.uri[len('spotify'):].replace(':', '/'))

    @property
    def type(self):
        """The link's :class:`LinkType`."""
        return LinkType(lib.sp_link_type(self._sp_link))

    @serialized
    def as_track(self):
        """Make a :class:`Track` from the link."""
        sp_track = lib.sp_link_as_track(self._sp_link)
        if sp_track == ffi.NULL:
            return None
        return spotify.Track(self._session, sp_track=sp_track, add_ref=True)

    def as_track_offset(self):
        """Get the track offset in milliseconds from the link."""
        offset = ffi.new('int *')
        sp_track = lib.sp_link_as_track_and_offset(self._sp_link, offset)
        if sp_track == ffi.NULL:
            return None
        return offset[0]

    @serialized
    def as_album(self):
        """Make an :class:`Album` from the link."""
        sp_album = lib.sp_link_as_album(self._sp_link)
        if sp_album == ffi.NULL:
            return None
        return spotify.Album(self._session, sp_album=sp_album, add_ref=True)

    @serialized
    def as_artist(self):
        """Make an :class:`Artist` from the link."""
        sp_artist = lib.sp_link_as_artist(self._sp_link)
        if sp_artist == ffi.NULL:
            return None
        return spotify.Artist(self._session, sp_artist=sp_artist, add_ref=True)

    def as_playlist(self):
        """Make a :class:`Playlist` from the link."""
        if self.type is not LinkType.PLAYLIST:
            return None
        sp_playlist = lib.sp_playlist_create(
            self._session._sp_session, self._sp_link)
        if sp_playlist == ffi.NULL:
            return None
        return spotify.Playlist._cached(
            self._session, sp_playlist, add_ref=False)

    @serialized
    def as_user(self):
        """Make an :class:`User` from the link."""
        sp_user = lib.sp_link_as_user(self._sp_link)
        if sp_user == ffi.NULL:
            return None
        return spotify.User(self._session, sp_user=sp_user, add_ref=True)

    def as_image(self, callback=None):
        """Make an :class:`Image` from the link.

        If ``callback`` isn't :class:`None`, it is expected to be a callable
        that accepts a single argument, an :class:`Image` instance, when
        the image is done loading.
        """
        if self.type is not LinkType.IMAGE:
            return None
        sp_image = lib.sp_image_create_from_link(
            self._session._sp_session, self._sp_link)
        if sp_image == ffi.NULL:
            return None
        return spotify.Image(
            self._session, sp_image=sp_image, add_ref=False, callback=callback)


@utils.make_enum('SP_LINKTYPE_')
class LinkType(utils.IntEnum):
    pass

########NEW FILE########
__FILENAME__ = offline
from __future__ import unicode_literals

import spotify
from spotify import ffi, lib


__all__ = [
    'OfflineSyncStatus',
]


class Offline(object):
    """Offline sync controller.

    You'll never need to create an instance of this class yourself. You'll find
    it ready to use as the :attr:`~Session.offline` attribute on the
    :class:`Session` instance.
    """

    def __init__(self, session):
        self._session = session

    @property
    def tracks_to_sync(self):
        """Total number of tracks that needs download before everything from
        all playlists that are marked for offline is fully synchronized.
        """
        return lib.sp_offline_tracks_to_sync(self._session._sp_session)

    @property
    def num_playlists(self):
        """Number of playlists that are marked for offline synchronization."""
        return lib.sp_offline_num_playlists(self._session._sp_session)

    @property
    def sync_status(self):
        """The :class:`OfflineSyncStatus` or :class:`None` if not syncing.

        The :attr:`~SessionEvent.OFFLINE_STATUS_UPDATED` event is emitted on
        the session object when this is updated.
        """
        sp_offline_sync_status = ffi.new('sp_offline_sync_status *')
        syncing = lib.sp_offline_sync_get_status(
            self._session._sp_session, sp_offline_sync_status)
        if syncing:
            return spotify.OfflineSyncStatus(sp_offline_sync_status)

    @property
    def time_left(self):
        """The number of seconds until the user has to get online and
        relogin."""
        return lib.sp_offline_time_left(self._session._sp_session)


class OfflineSyncStatus(object):
    """A Spotify offline sync status object.

    You'll never need to create an instance of this class yourself. You'll find
    it ready for use as the :attr:`~spotify.Offline.sync_status` attribute on
    the :attr:`~spotify.Session.offline` attribute on the
    :class:`~spotify.Session` instance.
    """

    def __init__(self, sp_offline_sync_status):
        self._sp_offline_sync_status = sp_offline_sync_status

    @property
    def queued_tracks(self):
        """Number of tracks left to sync in current sync operation."""
        return self._sp_offline_sync_status.queued_tracks

    @property
    def done_tracks(self):
        """Number of tracks marked for sync that existed on the device before
        the current sync operation."""
        return self._sp_offline_sync_status.done_tracks

    @property
    def copied_tracks(self):
        """Number of tracks copied during the current sync operation."""
        return self._sp_offline_sync_status.copied_tracks

    @property
    def willnotcopy_tracks(self):
        """Number of tracks marked for sync that will not be copied."""
        return self._sp_offline_sync_status.willnotcopy_tracks

    @property
    def error_tracks(self):
        """Number of tracks that failed syncing during the current sync
        operation."""
        return self._sp_offline_sync_status.error_tracks

    @property
    def syncing(self):
        """If sync operation is in progress."""
        return bool(self._sp_offline_sync_status.syncing)

########NEW FILE########
__FILENAME__ = player
from __future__ import unicode_literals

import spotify
from spotify import lib


class Player(object):
    """Playback controller.

    You'll never need to create an instance of this class yourself. You'll find
    it ready to use as the :attr:`~Session.player` attribute on the
    :class:`Session` instance.
    """

    def __init__(self, session):
        self._session = session

    def load(self, track):
        """Load :class:`Track` for playback."""
        spotify.Error.maybe_raise(lib.sp_session_player_load(
            self._session._sp_session, track._sp_track))

    def seek(self, offset):
        """Seek to the offset in ms in the currently loaded track."""
        spotify.Error.maybe_raise(
            lib.sp_session_player_seek(self._session._sp_session, offset))

    def play(self, play=True):
        """Play the currently loaded track.

        This will cause audio data to be passed to the
        :attr:`~SessionCallbacks.music_delivery` callback.

        If ``play`` is set to :class:`False`, playback will be paused.
        """
        spotify.Error.maybe_raise(lib.sp_session_player_play(
            self._session._sp_session, play))

    def pause(self):
        """Pause the currently loaded track.

        This is the same as calling :meth:`play` with :class:`False`.
        """
        self.play(False)

    def unload(self):
        """Stops the currently playing track."""
        spotify.Error.maybe_raise(
            lib.sp_session_player_unload(self._session._sp_session))

    def prefetch(self, track):
        """Prefetch a :class:`Track` for playback.

        This can be used to make libspotify download and cache a track before
        playing it.
        """
        spotify.Error.maybe_raise(lib.sp_session_player_prefetch(
            self._session._sp_session, track._sp_track))

########NEW FILE########
__FILENAME__ = playlist
from __future__ import unicode_literals

import collections
import logging

import spotify
from spotify import ffi, lib, serialized, utils


__all__ = [
    'Playlist',
    'PlaylistEvent',
    'PlaylistOfflineStatus',
]

logger = logging.getLogger(__name__)


class Playlist(utils.EventEmitter):
    """A Spotify playlist.

    You can get playlists from the :attr:`~Session.playlist_container`,
    :attr:`~Session.inbox`, :meth:`~Session.get_starred`,
    :meth:`~Session.search`, etc., or you can create a playlist yourself from a
    Spotify URI::

        >>> session = spotify.Session()
        # ...
        >>> playlist = session.get_playlist(
        ...     'spotify:user:fiat500c:playlist:54k50VZdvtnIPt4d8RBCmZ')
        >>> playlist.load().name
        u'500C feelgood playlist'
    """

    @classmethod
    @serialized
    def _cached(cls, session, sp_playlist, add_ref=True):
        """
        Get :class:`Playlist` instance for the given ``sp_playlist``. If
        it already exists, it is retrieved from cache.

        Internal method.
        """
        if sp_playlist in session._cache:
            return session._cache[sp_playlist]
        playlist = Playlist(session, sp_playlist=sp_playlist, add_ref=add_ref)
        session._cache[sp_playlist] = playlist
        return playlist

    def __init__(self, session, uri=None, sp_playlist=None, add_ref=True):
        super(Playlist, self).__init__()

        assert uri or sp_playlist, 'uri or sp_playlist is required'

        self._session = session

        if uri is not None:
            playlist = spotify.Link(self._session, uri).as_playlist()
            if playlist is None:
                raise spotify.Error(
                    'Failed to get playlist from Spotify URI: %r' % uri)
            sp_playlist = playlist._sp_playlist
            session._cache[sp_playlist] = self
            add_ref = True

        if add_ref:
            lib.sp_playlist_add_ref(sp_playlist)
        self._sp_playlist = ffi.gc(sp_playlist, lib.sp_playlist_release)

        self._sp_playlist_callbacks = _PlaylistCallbacks.get_struct()
        lib.sp_playlist_add_callbacks(
            self._sp_playlist, self._sp_playlist_callbacks, ffi.NULL)

        # Make sure we remove callbacks in __del__() using the same lib as we
        # added callbacks with.
        self._lib = lib

    def __del__(self):
        if not hasattr(self, '_lib'):
            return
        self._lib.sp_playlist_remove_callbacks(
            self._sp_playlist, self._sp_playlist_callbacks, ffi.NULL)

    def __repr__(self):
        if not self.is_loaded:
            return 'Playlist(<not loaded>)'
        try:
            return 'Playlist(%r)' % self.link.uri
        except spotify.Error as exc:
            return 'Playlist(<error: %s>)' % exc

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self._sp_playlist == other._sp_playlist
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self._sp_playlist)

    @property
    def is_loaded(self):
        """Whether the playlist's data is loaded."""
        return bool(lib.sp_playlist_is_loaded(self._sp_playlist))

    def load(self, timeout=None):
        """Block until the playlist's data is loaded.

        After ``timeout`` seconds with no results :exc:`~spotify.Timeout` is
        raised. If ``timeout`` is :class:`None` the default timeout is used.

        The method returns ``self`` to allow for chaining of calls.
        """
        return utils.load(self._session, self, timeout=timeout)

    @property
    @serialized
    def tracks(self):
        """The playlist's tracks.

        Will always return an empty list if the search isn't loaded.
        """
        if not self.is_loaded:
            return []

        return _Tracks(self._session, self)

    @property
    @serialized
    def tracks_with_metadata(self):
        """The playlist's tracks, with metadata specific to the playlist as a
        a list of :class:`~spotify.PlaylistTrack` objects.

        Will always return an empty list if the search isn't loaded.
        """
        if not self.is_loaded:
            return []

        return _PlaylistTracks(self._session, self)

    @property
    @serialized
    def name(self):
        """The playlist's name.

        Assigning to :attr:`name` will rename the playlist.

        Will always return :class:`None` if the track isn't loaded.
        """
        name = utils.to_unicode(lib.sp_playlist_name(self._sp_playlist))
        return name if name else None

    @name.setter
    def name(self, new_name):
        self.rename(new_name)

    def rename(self, new_name):
        """Rename the playlist."""
        spotify.Error.maybe_raise(
            lib.sp_playlist_rename(self._sp_playlist, utils.to_char(new_name)))

    @property
    @serialized
    def owner(self):
        """The :class:`User` object for the owner of the playlist."""
        return spotify.User(
            self._session,
            sp_user=lib.sp_playlist_owner(self._sp_playlist), add_ref=True)

    @property
    def collaborative(self):
        """Whether the playlist can be modified by all users or not.

        Set to :class:`True` or :class:`False` to change.
        """
        return bool(lib.sp_playlist_is_collaborative(self._sp_playlist))

    @collaborative.setter
    def collaborative(self, value):
        spotify.Error.maybe_raise(
            lib.sp_playlist_set_collaborative(self._sp_playlist, int(value)))

    def set_autolink_tracks(self, link=True):
        """If a playlist is autolinked, unplayable tracks will be made playable
        by linking them to other Spotify tracks, where possible."""
        spotify.Error.maybe_raise(
            lib.sp_playlist_set_autolink_tracks(self._sp_playlist, int(link)))

    @property
    @serialized
    def description(self):
        """The playlist's description.

        Will return :class:`None` if the description is unset.
        """
        description = lib.sp_playlist_get_description(self._sp_playlist)
        return utils.to_unicode_or_none(description)

    def image(self, callback=None):
        """The playlist's :class:`Image`.

        Due to limitations in libspotify's API you can't specify the
        :class:`ImageSize` of these images.

        If ``callback`` isn't :class:`None`, it is expected to be a callable
        that accepts a single argument, an :class:`Image` instance, when
        the image is done loading.

        Will always return :class:`None` if the playlist isn't loaded or the
        playlist has no image.
        """
        image_id = ffi.new('char[20]')
        has_image = bool(
            lib.sp_playlist_get_image(self._sp_playlist, image_id))
        if not has_image:
            return None
        sp_image = lib.sp_image_create(self._session._sp_session, image_id)
        return spotify.Image(
            self._session, sp_image=sp_image, add_ref=False, callback=callback)

    @property
    def has_pending_changes(self):
        """Check if the playlist has local changes that has not been
        acknowledged by the server yet.
        """
        return bool(lib.sp_playlist_has_pending_changes(self._sp_playlist))

    @serialized
    def add_tracks(self, tracks, index=None):
        """Add the given ``tracks`` to playlist at the given ``index``.

        ``tracks`` can either be a single :class:`~spotify.Track` or a list of
        :class:`~spotify.Track` objects. If ``index`` isn't specified, the
        tracks are added to the end of the playlist.
        """
        if isinstance(tracks, spotify.Track):
            tracks = [tracks]
        if index is None:
            index = len(self.tracks)
        spotify.Error.maybe_raise(lib.sp_playlist_add_tracks(
            self._sp_playlist, [t._sp_track for t in tracks], len(tracks),
            index, self._session._sp_session))

    def remove_tracks(self, indexes):
        """Remove the tracks at the given ``indexes`` from the playlist.

        ``indexes`` can be a single index or a list of indexes to remove.
        """
        if isinstance(indexes, int):
            indexes = [indexes]
        indexes = list(set(indexes))  # Remove duplicates
        spotify.Error.maybe_raise(lib.sp_playlist_remove_tracks(
            self._sp_playlist, indexes, len(indexes)))

    def reorder_tracks(self, tracks, new_index):
        """Move the given ``tracks`` to a ``new_index`` in the playlist.

        ``tracks`` can be a single :class:`~spotify.Track` or a list of
        :class:`~spotify.Track` objects.

        ``new_index`` must be equal to or lower than the current playlist
        length.
        """
        if isinstance(tracks, spotify.Track):
            tracks = [tracks]
        tracks = list(set(tracks))  # Remove duplicates
        spotify.Error.maybe_raise(lib.sp_playlist_reorder_tracks(
            self._sp_playlist, [t._sp_track for t in tracks], len(tracks),
            new_index))

    @property
    def num_subscribers(self):
        """The number of subscribers to the playlist.

        The number can be higher than the length of the :attr:`subscribers`
        collection, especially if the playlist got many subscribers.

        May be zero until you call :meth:`update_subscribers` and the
        :attr:`~PlaylistEvent.SUBSCRIBERS_CHANGED` event is emitted from the
        playlist.
        """
        return lib.sp_playlist_num_subscribers(self._sp_playlist)

    @property
    @serialized
    def subscribers(self):
        """The canonical usernames of up to 500 of the subscribers of the
        playlist.

        May be empty until you call :meth:`update_subscribers` and the
        :attr:`~PlaylistEvent.SUBSCRIBERS_CHANGED` event is emitted from the
        playlist.
        """
        sp_subscribers = ffi.gc(
            lib.sp_playlist_subscribers(self._sp_playlist),
            lib.sp_playlist_subscribers_free)
        # The ``subscribers`` field is ``char *[1]`` according to the struct,
        # so we must cast it to ``char **`` to be able to access more than the
        # first subscriber.
        subscribers = ffi.cast('char **', sp_subscribers.subscribers)
        usernames = []
        for i in range(sp_subscribers.count):
            usernames.append(utils.to_unicode(subscribers[i]))
        return usernames

    def update_subscribers(self):
        """Request an update of :attr:`num_subscribers` and the
        :attr:`subscribers` collection.

        The :attr:`~PlaylistEvent.SUBSCRIBERS_CHANGED` event is emitted from
        the playlist when the subscriber data has been updated.
        """
        spotify.Error.maybe_raise(lib.sp_playlist_update_subscribers(
            self._session._sp_session, self._sp_playlist))

    @property
    def is_in_ram(self):
        """Whether the playlist is in RAM, and not only on disk.

        A playlist must *currently be* in RAM for tracks to be available. A
        playlist must *have been* in RAM for other metadata to be available.

        By default, playlists are kept in RAM unless
        :attr:`~spotify.Config.initially_unload_playlists` is set to
        :class:`True` before creating the :class:`~spotify.Session`. If the
        playlists are initially unloaded, use :meth:`set_in_ram` to have a
        playlist loaded into RAM.
        """
        return bool(lib.sp_playlist_is_in_ram(
            self._session._sp_session, self._sp_playlist))

    def set_in_ram(self, in_ram=True):
        """Control whether or not to keep the playlist in RAM.

        See :attr:`is_in_ram` for further details.
        """
        spotify.Error.maybe_raise(lib.sp_playlist_set_in_ram(
            self._session._sp_session, self._sp_playlist, int(in_ram)))

    def set_offline_mode(self, offline=True):
        """Mark the playlist to be synchronized for offline playback.

        The playlist must be in the current user's playlist container.
        """
        spotify.Error.maybe_raise(lib.sp_playlist_set_offline_mode(
            self._session._sp_session, self._sp_playlist, int(offline)))

    @property
    def offline_status(self):
        """The playlist's :class:`PlaylistOfflineStatus`."""
        return PlaylistOfflineStatus(lib.sp_playlist_get_offline_status(
            self._session._sp_session, self._sp_playlist))

    @property
    def offline_download_completed(self):
        """The download progress for an offline playlist.

        A number in the range 0-100. Always :class:`None` if
        :attr:`offline_status` isn't :attr:`PlaylistOfflineStatus.DOWNLOADING`.
        """
        if self.offline_status != PlaylistOfflineStatus.DOWNLOADING:
            return None
        return int(lib.sp_playlist_get_offline_download_completed(
            self._session._sp_session, self._sp_playlist))

    @property
    def link(self):
        """A :class:`Link` to the playlist."""
        if not self.is_loaded:
            raise spotify.Error('The playlist must be loaded to create a link')
        sp_link = lib.sp_link_create_from_playlist(self._sp_playlist)
        if sp_link == ffi.NULL:
            if not self.is_in_ram:
                raise spotify.Error(
                    'The playlist must have been in RAM to create a link')
            # XXX Figure out why we can still get NULL here even if
            # the playlist is both loaded and in RAM.
            raise spotify.Error('Failed to get link from Spotify playlist')
        return spotify.Link(self._session, sp_link=sp_link, add_ref=False)

    @serialized
    def on(self, event, listener, *user_args):
        if self not in self._session._emitters:
            self._session._emitters.append(self)
        super(Playlist, self).on(event, listener, *user_args)
    on.__doc__ = utils.EventEmitter.on.__doc__

    @serialized
    def off(self, event=None, listener=None):
        super(Playlist, self).off(event, listener)
        if (self.num_listeners() == 0 and
                self in self._session._emitters):
            self._session._emitters.remove(self)
    off.__doc__ = utils.EventEmitter.off.__doc__


class PlaylistEvent(object):
    """Playlist events.

    Using :class:`Playlist` objects, you can register listener functions to be
    called when various events occurs in the playlist. This class enumerates
    the available events and the arguments your listener functions will be
    called with.

    Example usage::

        import spotify

        def tracks_added(playlist, tracks, index):
            print('Tracks added to playlist')

        session = spotify.Session()
        # Login, etc...

        playlist = session.playlist_container[0]
        playlist.on(spotify.PlaylistEvent.TRACKS_ADDED, tracks_added)

    All events will cause debug log statements to be emitted, even if no
    listeners are registered. Thus, there is no need to register listener
    functions just to log that they're called.
    """

    TRACKS_ADDED = 'tracks_added'
    """Called when one or more tracks have been added to the playlist.

    :param playlist: the playlist
    :type playlist: :class:`Playlist`
    :param tracks: the added tracks
    :type tracks: list of :class:`Track`
    :param index: the index in the playlist the tracks were added at
    :type index: int
    """

    TRACKS_REMOVED = 'tracks_removed'
    """Called when one or more tracks have been removed from the playlist.

    :param playlist: the playlist
    :type playlist: :class:`Playlist`
    :param indexes: indexes of the tracks that were removed
    :type indexes: list of ints
    """

    TRACKS_MOVED = 'tracks_moved'
    """Called when one or more tracks have been moved within a playlist.

    :param playlist: the playlist
    :type playlist: :class:`Playlist`
    :param old_indexes: old indexes of the tracks that were moved
    :type old_indexes: list of ints
    :param new_index: the new index in the playlist the tracks were moved to
    :type new_index: int
    """

    PLAYLIST_RENAMED = 'playlist_renamed'
    """Called when the playlist has been renamed.

    :param playlist: the playlist
    :type playlist: :class:`Playlist`
    """

    PLAYLIST_STATE_CHANGED = 'playlist_state_changed'
    """Called when the state changed for a playlist.

    There are three states that trigger this callback:

    - Collaboration for this playlist has been turned on or off. See
      :meth:`Playlist.is_collaborative`.
    - The playlist started having pending changes, or all pending changes have
      now been committed. See :attr:`Playlist.has_pending_changes`.
    - The playlist started loading, or finished loading. See
      :attr:`Playlist.is_loaded`.

    :param playlist: the playlist
    :type playlist: :class:`Playlist`
    """

    PLAYLIST_UPDATE_IN_PROGRESS = 'playlist_update_in_progress'
    """Called when a playlist is updating or is done updating.

    This is called before and after a series of changes are applied to the
    playlist. It allows e.g. the user interface to defer updating until the
    entire operation is complete.

    :param playlist: the playlist
    :type playlist: :class:`Playlist`
    :param done: if the update is completed
    :type done: bool
    """

    PLAYLIST_METADATA_UPDATED = 'playlist_metadata_updated'
    """Called when metadata for one or more tracks in the playlist have been
    updated.

    :param playlist: the playlist
    :type playlist: :class:`Playlist`
    """

    TRACK_CREATED_CHANGED = 'track_created_changed'
    """Called when the create time and/or creator for a playlist entry changes.

    :param playlist: the playlist
    :type playlist: :class:`Playlist`
    :param index: the index of the entry in the playlist that was changed
    :type index: int
    :param user: the user that created the playlist entry
    :type user: :class:`User`
    :param time: the time the entry was created, in seconds since Unix epoch
    :type time: int
    """

    TRACK_SEEN_CHANGED = 'track_seen_changed'
    """Called when the seen attribute of a playlist entry changes.

    :param playlist: the playlist
    :type playlist: :class:`Playlist`
    :param index: the index of the entry in the playlist that was changed
    :type index: int
    :param seen: whether the entry is seen or not
    :type seen: bool
    """

    DESCRIPTION_CHANGED = 'description_changed'
    """Called when the playlist description has changed.

    :param playlist: the playlist
    :type playlist: :class:`Playlist`
    :param description: the new description
    :type description: string
    """

    IMAGE_CHANGED = 'image_changed'
    """Called when the playlist image has changed.

    :param playlist: the playlist
    :type playlist: :class:`Playlist`
    :param image: the new image
    :type image: :class:`Image`
    """

    TRACK_MESSAGE_CHANGED = 'track_message_changed'
    """Called when the message attribute of a playlist entry changes.

    :param playlist: the playlist
    :type playlist: :class:`Playlist`
    :param index: the index of the entry in the playlist that was changed
    :type index: int
    :param message: the new message
    :type message: string
    """

    SUBSCRIBERS_CHANGED = 'subscribers_changed'
    """Called when playlist subscribers changes, either the count or the
    subscriber names.

    :param playlist: the playlist
    :type playlist: :class:`Playlist`
    """


class _PlaylistCallbacks(object):

    @classmethod
    def get_struct(cls):
        return ffi.new('sp_playlist_callbacks *', {
            'tracks_added': cls.tracks_added,
            'tracks_removed': cls.tracks_removed,
            'tracks_moved': cls.tracks_moved,
            'playlist_renamed': cls.playlist_renamed,
            'playlist_state_changed': cls.playlist_state_changed,
            'playlist_update_in_progress': cls.playlist_update_in_progress,
            'playlist_metadata_updated': cls.playlist_metadata_updated,
            'track_created_changed': cls.track_created_changed,
            'track_seen_changed': cls.track_seen_changed,
            'description_changed': cls.description_changed,
            'image_changed': cls.image_changed,
            'track_message_changed': cls.track_message_changed,
            'subscribers_changed': cls.subscribers_changed,
        })

    # XXX Avoid use of the spotify._session_instance global in the following
    # callbacks.

    @staticmethod
    @ffi.callback(
        'void(sp_playlist *playlist, sp_track **tracks, int num_tracks, '
        'int position, void *userdata)')
    def tracks_added(sp_playlist, sp_tracks, num_tracks, index, userdata):
        logger.debug('Tracks added to playlist')
        playlist = Playlist._cached(
            spotify._session_instance, sp_playlist, add_ref=True)
        tracks = [
            spotify.Track(
                spotify._session_instance, sp_track=sp_tracks[i], add_ref=True)
            for i in range(num_tracks)]
        playlist.emit(
            PlaylistEvent.TRACKS_ADDED, playlist, tracks, int(index))

    @staticmethod
    @ffi.callback(
        'void(sp_playlist *playlist, int *tracks, int num_tracks, '
        'void *userdata)')
    def tracks_removed(sp_playlist, tracks, num_tracks, userdata):
        logger.debug('Tracks removed from playlist')
        playlist = Playlist._cached(
            spotify._session_instance, sp_playlist, add_ref=True)
        tracks = [int(tracks[i]) for i in range(num_tracks)]
        playlist.emit(PlaylistEvent.TRACKS_REMOVED, playlist, tracks)

    @staticmethod
    @ffi.callback(
        'void(sp_playlist *playlist, int *tracks, int num_tracks, '
        'int position, void *userdata)')
    def tracks_moved(
            sp_playlist, old_indexes, num_tracks, new_index, userdata):
        logger.debug('Tracks moved within playlist')
        playlist = Playlist._cached(
            spotify._session_instance, sp_playlist, add_ref=True)
        old_indexes = [int(old_indexes[i]) for i in range(num_tracks)]
        playlist.emit(
            PlaylistEvent.TRACKS_MOVED, playlist, old_indexes, int(new_index))

    @staticmethod
    @ffi.callback('void(sp_playlist *playlist, void *userdata)')
    def playlist_renamed(sp_playlist, userdata):
        logger.debug('Playlist renamed')
        playlist = Playlist._cached(
            spotify._session_instance, sp_playlist, add_ref=True)
        playlist.emit(PlaylistEvent.PLAYLIST_RENAMED, playlist)

    @staticmethod
    @ffi.callback('void(sp_playlist *playlist, void *userdata)')
    def playlist_state_changed(sp_playlist, userdata):
        logger.debug('Playlist state changed')
        playlist = Playlist._cached(
            spotify._session_instance, sp_playlist, add_ref=True)
        playlist.emit(PlaylistEvent.PLAYLIST_STATE_CHANGED, playlist)

    @staticmethod
    @ffi.callback('void(sp_playlist *playlist, bool done, void *userdata)')
    def playlist_update_in_progress(sp_playlist, done, userdata):
        logger.debug('Playlist update in progress')
        playlist = Playlist._cached(
            spotify._session_instance, sp_playlist, add_ref=True)
        playlist.emit(
            PlaylistEvent.PLAYLIST_UPDATE_IN_PROGRESS, playlist, bool(done))

    @staticmethod
    @ffi.callback('void(sp_playlist *playlist, void *userdata)')
    def playlist_metadata_updated(sp_playlist, userdata):
        logger.debug('Playlist metadata updated')
        playlist = Playlist._cached(
            spotify._session_instance, sp_playlist, add_ref=True)
        playlist.emit(PlaylistEvent.PLAYLIST_METADATA_UPDATED, playlist)

    @staticmethod
    @ffi.callback(
        'void(sp_playlist *playlist, int position, sp_user *user, '
        'int when, void *userdata)')
    def track_created_changed(sp_playlist, index, sp_user, when, userdata):
        logger.debug('Playlist track created changed')
        playlist = Playlist._cached(
            spotify._session_instance, sp_playlist, add_ref=True)
        user = spotify.User(
            spotify._session_instance, sp_user=sp_user, add_ref=True)
        playlist.emit(
            PlaylistEvent.TRACK_CREATED_CHANGED,
            playlist, int(index), user, int(when))

    @staticmethod
    @ffi.callback(
        'void(sp_playlist *playlist, int position, bool seen, void *userdata)')
    def track_seen_changed(sp_playlist, index, seen, userdata):
        logger.debug('Playlist track seen changed')
        playlist = Playlist._cached(
            spotify._session_instance, sp_playlist, add_ref=True)
        playlist.emit(
            PlaylistEvent.TRACK_SEEN_CHANGED,
            playlist, int(index), bool(seen))

    @staticmethod
    @ffi.callback(
        'void(sp_playlist *playlist, char *desc, void *userdata)')
    def description_changed(sp_playlist, desc, userdata):
        logger.debug('Playlist description changed')
        playlist = Playlist._cached(
            spotify._session_instance, sp_playlist, add_ref=True)
        playlist.emit(
            PlaylistEvent.DESCRIPTION_CHANGED,
            playlist, utils.to_unicode(desc))

    @staticmethod
    @ffi.callback(
        'void(sp_playlist *playlist, byte *image, void *userdata)')
    def image_changed(sp_playlist, image_id, userdata):
        logger.debug('Playlist image changed')
        playlist = Playlist._cached(
            spotify._session_instance, sp_playlist, add_ref=True)
        sp_image = lib.sp_image_create(
            spotify._session_instance._sp_session, image_id)
        image = spotify.Image(
            spotify._session_instance, sp_image=sp_image, add_ref=False)
        playlist.emit(PlaylistEvent.IMAGE_CHANGED, playlist, image)

    @staticmethod
    @ffi.callback(
        'void(sp_playlist *playlist, int position, char *message, '
        'void *userdata)')
    def track_message_changed(sp_playlist, index, message, userdata):
        logger.debug('Playlist track message changed')
        playlist = Playlist._cached(
            spotify._session_instance, sp_playlist, add_ref=True)
        playlist.emit(
            PlaylistEvent.TRACK_MESSAGE_CHANGED,
            playlist, int(index), utils.to_unicode(message))

    @staticmethod
    @ffi.callback('void(sp_playlist *playlist, void *userdata)')
    def subscribers_changed(sp_playlist, userdata):
        logger.debug('Playlist subscribers changed')
        playlist = Playlist._cached(
            spotify._session_instance, sp_playlist, add_ref=True)
        playlist.emit(PlaylistEvent.SUBSCRIBERS_CHANGED, playlist)


@utils.make_enum('SP_PLAYLIST_OFFLINE_STATUS_')
class PlaylistOfflineStatus(utils.IntEnum):
    pass


class _Tracks(utils.Sequence, collections.MutableSequence):

    def __init__(self, session, playlist):
        self._session = session
        self._playlist = playlist
        return super(_Tracks, self).__init__(
            sp_obj=playlist._sp_playlist,
            add_ref_func=lib.sp_playlist_add_ref,
            release_func=lib.sp_playlist_release,
            len_func=lib.sp_playlist_num_tracks,
            getitem_func=self.get_track)

    @serialized
    def get_track(self, sp_playlist, key):
        return spotify.Track(
            self._session,
            sp_track=lib.sp_playlist_track(sp_playlist, key), add_ref=True)

    def __setitem__(self, key, value):
        # Required by collections.MutableSequence

        if not isinstance(key, (int, slice)):
            raise TypeError(
                'list indices must be int or slice, not %s' %
                key.__class__.__name__)
        if isinstance(key, slice):
            if not isinstance(value, collections.Iterable):
                raise TypeError('can only assign an iterable')
        if isinstance(key, int):
            if not 0 <= key < self.__len__():
                raise IndexError('list index out of range')
            key = slice(key, key + 1)
            value = [value]

        for i, val in enumerate(value, key.start):
            self._playlist.add_tracks(val, index=i)

        key = slice(key.start + len(value), key.stop + len(value), key.step)
        del self[key]

    def __delitem__(self, key):
        # Required by collections.MutableSequence

        if isinstance(key, slice):
            start, stop, step = key.indices(self.__len__())
            indexes = range(start, stop, step)
            for i in reversed(sorted(indexes)):
                self._playlist.remove_tracks(i)
            return
        if not isinstance(key, int):
            raise TypeError(
                'list indices must be int or slice, not %s' %
                key.__class__.__name__)
        if not 0 <= key < self.__len__():
            raise IndexError('list index out of range')
        self._playlist.remove_tracks(key)

    def insert(self, index, value):
        # Required by collections.MutableSequence

        self[index:index] = [value]


class _PlaylistTracks(_Tracks):

    @serialized
    def get_track(self, sp_playlist, key):
        return spotify.PlaylistTrack(self._session, sp_playlist, key)

########NEW FILE########
__FILENAME__ = playlist_container
from __future__ import unicode_literals

import collections
import logging
import pprint
import re

import spotify
from spotify import ffi, lib, serialized, utils


__all__ = [
    'PlaylistContainer',
    'PlaylistContainerEvent',
    'PlaylistFolder',
    'PlaylistType',
]

logger = logging.getLogger(__name__)


class PlaylistContainer(collections.MutableSequence, utils.EventEmitter):
    """A Spotify playlist container.

    The playlist container can be accessed as a regular Python collection to
    work with the playlists::

        >>> import spotify
        >>> session = spotify.Session()
        # Login, etc.
        >>> container = session.playlist_container
        >>> container.is_loaded
        False
        >>> container.load()
        [Playlist(u'spotify:user:jodal:playlist:6xkJysqhkj9uwufFbUb8sP'),
         Playlist(u'spotify:user:jodal:playlist:0agJjPcOhHnstLIQunJHxo'),
         PlaylistFolder(id=8027491506140518932L, name=u'Shared playlists',
            type=<PlaylistType.START_FOLDER: 1>),
         Playlist(u'spotify:user:p3.no:playlist:7DkMndS2KNVQuf2fOpMt10'),
         PlaylistFolder(id=8027491506140518932L, name=u'',
            type=<PlaylistType.END_FOLDER: 2>)]
        >>> container[0]
        Playlist(u'spotify:user:jodal:playlist:6xkJysqhkj9uwufFbUb8sP')

    As you can see, a playlist container can contain a mix of
    :class:`~spotify.Playlist` and :class:`~spotify.PlaylistFolder` objects.

    The container supports operations that changes the container as well.

    To add a playlist you can use :meth:`append` or :meth:`insert` with either
    the name of a new playlist or an existing playlist object. For example::

        >>> playlist = session.get_playlist(
        ...     'spotify:user:fiat500c:playlist:54k50VZdvtnIPt4d8RBCmZ')
        >>> container.insert(3, playlist)
        >>> container.append('New empty playlist')

    To remove a playlist or folder you can use :meth:`remove_playlist`, or::

        >>> del container[0]

    To replace an existing playlist or folder with a new empty playlist with
    the given name you can use :meth:`remove_playlist` and
    :meth:`add_new_playlist`, or::

        >>> container[0] = 'My other new empty playlist'

    To replace an existing playlist or folder with an existing playlist you can
    :use :meth:`remove_playlist` and :meth:`add_playlist`, or::

        >>> container[0] = playlist
    """

    @classmethod
    @serialized
    def _cached(cls, session, sp_playlistcontainer, add_ref=True):
        """
        Get :class:`PlaylistContainer` instance for the given
        ``sp_playlistcontainer``. If it already exists, it is retrieved from
        cache.

        Internal method.
        """
        if sp_playlistcontainer in session._cache:
            return session._cache[sp_playlistcontainer]
        playlist_container = PlaylistContainer(
            session,
            sp_playlistcontainer=sp_playlistcontainer, add_ref=add_ref)
        session._cache[sp_playlistcontainer] = playlist_container
        return playlist_container

    def __init__(self, session, sp_playlistcontainer, add_ref=True):
        super(PlaylistContainer, self).__init__()

        self._session = session

        if add_ref:
            lib.sp_playlistcontainer_add_ref(sp_playlistcontainer)
        self._sp_playlistcontainer = ffi.gc(
            sp_playlistcontainer, lib.sp_playlistcontainer_release)

        self._sp_playlistcontainer_callbacks = (
            _PlaylistContainerCallbacks.get_struct())
        lib.sp_playlistcontainer_add_callbacks(
            self._sp_playlistcontainer, self._sp_playlistcontainer_callbacks,
            ffi.NULL)

        # Make sure we remove callbacks in __del__() using the same lib as we
        # added callbacks with.
        self._lib = lib

    def __del__(self):
        if not hasattr(self, '_lib'):
            return
        self._lib.sp_playlistcontainer_remove_callbacks(
            self._sp_playlistcontainer, self._sp_playlistcontainer_callbacks,
            ffi.NULL)

    def __repr__(self):
        return 'PlaylistContainer(%s)' % pprint.pformat(list(self))

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self._sp_playlistcontainer == other._sp_playlistcontainer
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self._sp_playlistcontainer)

    @property
    def is_loaded(self):
        """Whether the playlist container's data is loaded."""
        return bool(lib.sp_playlistcontainer_is_loaded(
            self._sp_playlistcontainer))

    def load(self, timeout=None):
        """Block until the playlist container's data is loaded.

        After ``timeout`` seconds with no results :exc:`~spotify.Timeout` is
        raised. If ``timeout`` is :class:`None` the default timeout is used.

        The method returns ``self`` to allow for chaining of calls.
        """
        return utils.load(self._session, self, timeout=timeout)

    def __len__(self):
        # Required by collections.Sequence

        length = lib.sp_playlistcontainer_num_playlists(
            self._sp_playlistcontainer)
        if length == -1:
            return 0
        return length

    @serialized
    def __getitem__(self, key):
        # Required by collections.Sequence

        if isinstance(key, slice):
            return list(self).__getitem__(key)
        if not isinstance(key, int):
            raise TypeError(
                'list indices must be int or slice, not %s' %
                key.__class__.__name__)
        if key < 0:
            key += self.__len__()
        if not 0 <= key < self.__len__():
            raise IndexError('list index out of range')

        playlist_type = PlaylistType(lib.sp_playlistcontainer_playlist_type(
            self._sp_playlistcontainer, key))

        if playlist_type is PlaylistType.PLAYLIST:
            sp_playlist = lib.sp_playlistcontainer_playlist(
                self._sp_playlistcontainer, key)
            return spotify.Playlist._cached(
                self._session, sp_playlist, add_ref=True)
        elif playlist_type in (
                PlaylistType.START_FOLDER, PlaylistType.END_FOLDER):
            return PlaylistFolder(
                id=lib.sp_playlistcontainer_playlist_folder_id(
                    self._sp_playlistcontainer, key),
                name=utils.get_with_fixed_buffer(
                    100,
                    lib.sp_playlistcontainer_playlist_folder_name,
                    self._sp_playlistcontainer, key),
                type=playlist_type)
        else:
            raise spotify.Error('Unknown playlist type: %r' % playlist_type)

    def __setitem__(self, key, value):
        # Required by collections.MutableSequence

        if not isinstance(key, (int, slice)):
            raise TypeError(
                'list indices must be int or slice, not %s' %
                key.__class__.__name__)
        if isinstance(key, slice):
            if not isinstance(value, collections.Iterable):
                raise TypeError('can only assign an iterable')
        if isinstance(key, int):
            if not 0 <= key < self.__len__():
                raise IndexError('list index out of range')
            key = slice(key, key + 1)
            value = [value]

        # In case playlist creation fails, we create before we remove any
        # playlists.
        for i, val in enumerate(value, key.start):
            if isinstance(val, spotify.Playlist):
                self.add_playlist(val, index=i)
            else:
                self.add_new_playlist(val, index=i)

        # Adjust for the new playlist at index key.start.
        key = slice(key.start + len(value), key.stop + len(value), key.step)
        del self[key]

    def __delitem__(self, key):
        # Required by collections.MutableSequence

        if isinstance(key, slice):
            start, stop, step = key.indices(self.__len__())
            indexes = range(start, stop, step)
            for i in reversed(sorted(indexes)):
                self.remove_playlist(i)
            return
        if not isinstance(key, int):
            raise TypeError(
                'list indices must be int or slice, not %s' %
                key.__class__.__name__)
        if not 0 <= key < self.__len__():
            raise IndexError('list index out of range')
        self.remove_playlist(key)

    @serialized
    def add_new_playlist(self, name, index=None):
        """Add an empty playlist with ``name`` at the given ``index``.

        The playlist name must not be space-only or longer than 255 chars.

        If the ``index`` isn't specified, the new playlist is added at the end
        of the container.

        Returns the new playlist.
        """
        self._validate_name(name)
        sp_playlist = lib.sp_playlistcontainer_add_new_playlist(
            self._sp_playlistcontainer, utils.to_char(name))
        if sp_playlist == ffi.NULL:
            raise spotify.Error('Playlist creation failed')
        playlist = spotify.Playlist._cached(
            self._session, sp_playlist, add_ref=True)
        if index is not None:
            self.move_playlist(self.__len__() - 1, index)
        return playlist

    @serialized
    def add_playlist(self, playlist, index=None):
        """Add an existing ``playlist`` to the playlist container at the given
        ``index``.

        The playlist can either be a :class:`~spotify.Playlist`, or a
        :class:`~spotify.Link` linking to a playlist.

        If the ``index`` isn't specified, the playlist is added at the end of
        the container.

        Returns the added playlist, or :class:`None` if the playlist already
        existed in the container. If the playlist already exists, it will not
        be moved to the given ``index``.
        """
        if isinstance(playlist, spotify.Link):
            link = playlist
        elif isinstance(playlist, spotify.Playlist):
            link = playlist.link
        else:
            raise TypeError(
                'Argument must be Link or Playlist, got %s' % type(playlist))
        sp_playlist = lib.sp_playlistcontainer_add_playlist(
            self._sp_playlistcontainer, link._sp_link)
        if sp_playlist == ffi.NULL:
            return None
        playlist = spotify.Playlist._cached(
            self._session, sp_playlist, add_ref=True)
        if index is not None:
            self.move_playlist(self.__len__() - 1, index)
        return playlist

    def add_folder(self, name, index=None):
        """Add a playlist folder with ``name`` at the given ``index``.

        The playlist folder name must not be space-only or longer than 255
        chars.

        If the ``index`` isn't specified, the folder is added at the end of the
        container.
        """
        self._validate_name(name)
        if index is None:
            index = self.__len__()
        spotify.Error.maybe_raise(lib.sp_playlistcontainer_add_folder(
            self._sp_playlistcontainer, index, utils.to_char(name)))

    def _validate_name(self, name):
        if len(name) > 255:
            raise ValueError('Playlist name cannot be longer than 255 chars')
        if len(re.sub('\s+', '', name)) == 0:
            raise ValueError('Playlist name cannot be space-only')

    def remove_playlist(self, index, recursive=False):
        """Remove playlist at the given index from the container.

        If the item at the given ``index`` is the start or the end of a
        playlist folder, and the other end of the folder is found, it is also
        removed. The folder content is kept, but is moved one level up the
        folder hierarchy. If ``recursive`` is :class:`True`, the folder content
        is removed as well.

        Using ``del playlist_container[3]`` is equivalent to
        ``playlist_container.remove_playlist(3)``. Similarly, ``del
        playlist_container[0:2]`` is equivalent to calling this method with
        indexes ``1`` and ``0``.
        """
        item = self[index]
        if isinstance(item, PlaylistFolder):
            indexes = self._find_folder_indexes(self, item.id, recursive)
        else:
            indexes = [index]
        for i in reversed(sorted(indexes)):
            spotify.Error.maybe_raise(
                lib.sp_playlistcontainer_remove_playlist(
                    self._sp_playlistcontainer, i))

    @staticmethod
    def _find_folder_indexes(container, folder_id, recursive):
        indexes = []
        for i, item in enumerate(container):
            if isinstance(item, PlaylistFolder) and item.id == folder_id:
                indexes.append(i)
        assert len(indexes) <= 2, (
            'Found more than 2 items with the same playlist folder ID')
        if recursive and len(indexes) == 2:
            start, end = indexes
            indexes = list(range(start, end + 1))
        return indexes

    def move_playlist(self, from_index, to_index, dry_run=False):
        """Move playlist at ``from_index`` to ``to_index``.

        If ``dry_run`` is :class:`True` the move isn't actually done. It is
        only checked if the move is possible.
        """
        spotify.Error.maybe_raise(lib.sp_playlistcontainer_move_playlist(
            self._sp_playlistcontainer, from_index, to_index, int(dry_run)))

    @property
    @serialized
    def owner(self):
        """The :class:`User` object for the owner of the playlist container."""
        return spotify.User(
            self._session,
            sp_user=lib.sp_playlistcontainer_owner(self._sp_playlistcontainer),
            add_ref=True)

    def get_unseen_tracks(self, playlist):
        """Get a list of unseen tracks in the given ``playlist``.

        The list is a :class:`PlaylistUnseenTracks` instance.

        The tracks will remain "unseen" until :meth:`clear_unseen_tracks` is
        called on the playlist.
        """
        return spotify.PlaylistUnseenTracks(
            self._session, self._sp_playlistcontainer, playlist._sp_playlist)

    def clear_unseen_tracks(self, playlist):
        """Clears unseen tracks from the given ``playlist``."""
        result = lib.sp_playlistcontainer_clear_unseen_tracks(
            self._sp_playlistcontainer, playlist._sp_playlist)
        if result == -1:
            raise spotify.Error('Failed clearing unseen tracks')

    def insert(self, index, value):
        # Required by collections.MutableSequence

        self[index:index] = [value]

    @serialized
    def on(self, event, listener, *user_args):
        if self not in self._session._emitters:
            self._session._emitters.append(self)
        super(PlaylistContainer, self).on(event, listener, *user_args)
    on.__doc__ = utils.EventEmitter.on.__doc__

    @serialized
    def off(self, event=None, listener=None):
        super(PlaylistContainer, self).off(event, listener)
        if (self.num_listeners() == 0 and
                self in self._session._emitters):
            self._session._emitters.remove(self)
    off.__doc__ = utils.EventEmitter.off.__doc__


class PlaylistContainerEvent(object):
    """Playlist container events.

    Using :class:`PlaylistContainer` objects, you can register listener
    functions to be called when various events occurs in the playlist
    container. This class enumerates the available events and the arguments
    your listener functions will be called with.

    Example usage::

        import spotify

        def container_loaded(playlist_container):
            print('Playlist container loaded')

        session = spotify.Session()
        # Login, etc...

        session.playlist_container.on(
            spotify.PlaylistContainerEvent.CONTAINER_LOADED, container_loaded)

    All events will cause debug log statements to be emitted, even if no
    listeners are registered. Thus, there is no need to register listener
    functions just to log that they're called.
    """

    PLAYLIST_ADDED = 'playlist_added'
    """Called when a playlist is added to the container.

    :param playlist_container: the playlist container
    :type playlist_container: :class:`PlaylistContainer`
    :param playlist: the added playlist
    :type playlist: :class:`Playlist`
    :param index: the index the playlist was added at
    :type index: int
    """

    PLAYLIST_REMOVED = 'playlist_removed'
    """Called when a playlist is removed from the container.

    :param playlist_container: the playlist container
    :type playlist_container: :class:`PlaylistContainer`
    :param playlist: the removed playlist
    :type playlist: :class:`Playlist`
    :param index: the index the playlist was removed from
    :type index: int
    """

    PLAYLIST_MOVED = 'playlist_moved'
    """Called when a playlist is moved in the container.

    :param playlist_container: the playlist container
    :type playlist_container: :class:`PlaylistContainer`
    :param playlist: the moved playlist
    :type playlist: :class:`Playlist`
    :param old_index: the index the playlist was moved from
    :type old_index: int
    :param new_index: the index the playlist was moved to
    :type new_index: int
    """

    CONTAINER_LOADED = 'container_loaded'
    """Called when the playlist container is loaded.

    :param playlist_container: the playlist container
    :type playlist_container: :class:`PlaylistContainer`
    """


class _PlaylistContainerCallbacks(object):
    """Internal class."""

    @classmethod
    def get_struct(cls):
        return ffi.new('sp_playlistcontainer_callbacks *', {
            'playlist_added': cls.playlist_added,
            'playlist_removed': cls.playlist_removed,
            'playlist_moved': cls.playlist_moved,
            'container_loaded': cls.container_loaded,
        })

    # XXX Avoid use of the spotify._session_instance global in the following
    # callbacks.

    @staticmethod
    @ffi.callback(
        'void(sp_playlistcontainer *pc, sp_playlist *playlist, int position, '
        'void *userdata)')
    def playlist_added(sp_playlistcontainer, sp_playlist, index, userdata):
        logger.debug('Playlist added at index %d', index)
        playlist_container = PlaylistContainer._cached(
            spotify._session_instance, sp_playlistcontainer, add_ref=True)
        playlist = spotify.Playlist._cached(
            spotify._session_instance, sp_playlist, add_ref=True)
        playlist_container.emit(
            PlaylistContainerEvent.PLAYLIST_ADDED,
            playlist_container, playlist, index)

    @staticmethod
    @ffi.callback(
        'void(sp_playlistcontainer *pc, sp_playlist *playlist, int position, '
        'void *userdata)')
    def playlist_removed(
            sp_playlistcontainer, sp_playlist, index, userdata):
        logger.debug('Playlist removed at index %d', index)
        playlist_container = PlaylistContainer._cached(
            spotify._session_instance, sp_playlistcontainer, add_ref=True)
        playlist = spotify.Playlist._cached(
            spotify._session_instance, sp_playlist, add_ref=True)
        playlist_container.emit(
            PlaylistContainerEvent.PLAYLIST_REMOVED,
            playlist_container, playlist, index)

    @staticmethod
    @ffi.callback(
        'void(sp_playlistcontainer *pc, sp_playlist *playlist, int position, '
        'int new_position, void *userdata)')
    def playlist_moved(
            sp_playlistcontainer, sp_playlist, old_index, new_index,
            userdata):
        logger.debug(
            'Playlist moved from index %d to %d', old_index, new_index)
        playlist_container = PlaylistContainer._cached(
            spotify._session_instance, sp_playlistcontainer, add_ref=True)
        playlist = spotify.Playlist._cached(
            spotify._session_instance, sp_playlist, add_ref=True)
        playlist_container.emit(
            PlaylistContainerEvent.PLAYLIST_MOVED,
            playlist_container, playlist, old_index, new_index)

    @staticmethod
    @ffi.callback(
        'void(sp_playlistcontainer *pc, void *userdata)')
    def container_loaded(sp_playlistcontainer, userdata):
        logger.debug('Playlist container loaded')
        playlist_container = PlaylistContainer._cached(
            spotify._session_instance, sp_playlistcontainer, add_ref=True)
        playlist_container.emit(
            PlaylistContainerEvent.CONTAINER_LOADED, playlist_container)


class PlaylistFolder(collections.namedtuple(
        'PlaylistFolder', ['id', 'name', 'type'])):
    """An object marking the start or end of a playlist folder."""
    pass


@utils.make_enum('SP_PLAYLIST_TYPE_')
class PlaylistType(utils.IntEnum):
    pass

########NEW FILE########
__FILENAME__ = playlist_track
from __future__ import unicode_literals

import logging

import spotify
from spotify import ffi, lib, serialized, utils


__all__ = [
    'PlaylistTrack',
]

logger = logging.getLogger(__name__)


class PlaylistTrack(object):
    """A playlist track with metadata specific to the playlist.

    Use :attr:`~spotify.Playlist.tracks_with_metadata` to get a list of
    :class:`PlaylistTrack`.
    """

    def __init__(self, session, sp_playlist, index):
        self._session = session

        lib.sp_playlist_add_ref(sp_playlist)
        self._sp_playlist = ffi.gc(sp_playlist, lib.sp_playlist_release)

        self._index = index

    def __repr__(self):
        return 'PlaylistTrack(uri=%r, creator=%r, create_time=%d)' % (
            self.track.link.uri, self.creator, self.create_time)

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return (
                self._sp_playlist == other._sp_playlist and
                self._index == other._index)
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash((self._sp_playlist, self._index))

    @property
    @serialized
    def track(self):
        """The :class:`~spotify.Track`."""
        return spotify.Track(
            self._session,
            sp_track=lib.sp_playlist_track(self._sp_playlist, self._index),
            add_ref=True)

    @property
    def create_time(self):
        """When the track was added to the playlist, as seconds since Unix
        epoch.
        """
        return lib.sp_playlist_track_create_time(
            self._sp_playlist, self._index)

    @property
    @serialized
    def creator(self):
        """The :class:`~spotify.User` that added the track to the playlist."""
        return spotify.User(
            self._session,
            sp_user=lib.sp_playlist_track_creator(
                self._sp_playlist, self._index),
            add_ref=True)

    def is_seen(self):
        return bool(lib.sp_playlist_track_seen(self._sp_playlist, self._index))

    def set_seen(self, value):
        spotify.Error.maybe_raise(lib.sp_playlist_track_set_seen(
            self._sp_playlist, self._index, int(value)))

    seen = property(is_seen, set_seen)
    """Whether the track is marked as seen or not."""

    @property
    @serialized
    def message(self):
        """A message attached to the track. Typically used in the inbox."""
        message = lib.sp_playlist_track_message(self._sp_playlist, self._index)
        return utils.to_unicode_or_none(message)

########NEW FILE########
__FILENAME__ = playlist_unseen_tracks
from __future__ import unicode_literals

import collections
import logging
import pprint

import spotify
from spotify import ffi, lib, serialized


__all__ = [
    'PlaylistUnseenTracks',
]

logger = logging.getLogger(__name__)


class PlaylistUnseenTracks(collections.Sequence):
    """A list of unseen tracks in a playlist.

    The list may contain items that are :class:`None`.

    Returned by :meth:`PlaylistContainer.get_unseen_tracks`.
    """

    _BATCH_SIZE = 100

    @serialized
    def __init__(self, session, sp_playlistcontainer, sp_playlist):
        self._session = session

        lib.sp_playlistcontainer_add_ref(sp_playlistcontainer)
        self._sp_playlistcontainer = ffi.gc(
            sp_playlistcontainer, lib.sp_playlistcontainer_release)

        lib.sp_playlist_add_ref(sp_playlist)
        self._sp_playlist = ffi.gc(sp_playlist, lib.sp_playlist_release)

        self._num_tracks = 0
        self._sp_tracks_len = 0
        self._get_more_tracks()

    @serialized
    def _get_more_tracks(self):
        self._sp_tracks_len = min(
            self._num_tracks, self._sp_tracks_len + self._BATCH_SIZE)
        self._sp_tracks = ffi.new('sp_track *[]', self._sp_tracks_len)
        self._num_tracks = lib.sp_playlistcontainer_get_unseen_tracks(
            self._sp_playlistcontainer, self._sp_playlist,
            self._sp_tracks, self._sp_tracks_len)

        if self._num_tracks < 0:
            raise spotify.Error('Failed to get unseen tracks for playlist')

    def __len__(self):
        return self._num_tracks

    def __getitem__(self, key):
        if isinstance(key, slice):
            return list(self).__getitem__(key)
        if not isinstance(key, int):
            raise TypeError(
                'list indices must be int or slice, not %s' %
                key.__class__.__name__)
        if key < 0:
            key += self.__len__()
        if not 0 <= key < self.__len__():
            raise IndexError('list index out of range')
        while key >= self._sp_tracks_len:
            self._get_more_tracks()
        sp_track = self._sp_tracks[key]
        if sp_track == ffi.NULL:
            return None
        return spotify.Track(self._session, sp_track=sp_track, add_ref=True)

    def __repr__(self):
        return 'PlaylistUnseenTracks(%s)' % pprint.pformat(list(self))

########NEW FILE########
__FILENAME__ = search
from __future__ import unicode_literals

import logging
import threading

import spotify
from spotify import ffi, lib, serialized, utils


__all__ = [
    'Search',
    'SearchPlaylist',
    'SearchType',
]

logger = logging.getLogger(__name__)


class Search(object):
    """A Spotify search result.

    Call the :meth:`~Session.search` method on your :class:`Session` instance
    to do a search and get a :class:`Search` back.
    """

    def __init__(
            self, session, query='', callback=None,
            track_offset=0, track_count=20,
            album_offset=0, album_count=20,
            artist_offset=0, artist_count=20,
            playlist_offset=0, playlist_count=20,
            search_type=None,
            sp_search=None, add_ref=True):

        assert query or sp_search, 'query or sp_search is required'

        self._session = session
        self.callback = callback
        self.track_offset = track_offset
        self.track_count = track_count
        self.album_offset = album_offset
        self.album_count = album_count
        self.artist_offset = artist_offset
        self.artist_count = artist_count
        self.playlist_offset = playlist_offset
        self.playlist_count = playlist_count
        if search_type is None:
            search_type = SearchType.STANDARD
        self.search_type = search_type

        self.loaded_event = threading.Event()

        if sp_search is None:
            handle = ffi.new_handle((self._session, self, callback))
            self._session._callback_handles.add(handle)

            sp_search = lib.sp_search_create(
                self._session._sp_session, utils.to_char(query),
                track_offset, track_count,
                album_offset, album_count,
                artist_offset, artist_count,
                playlist_offset, playlist_count,
                int(search_type), _search_complete_callback, handle)
            add_ref = False

        if add_ref:
            lib.sp_search_add_ref(sp_search)
        self._sp_search = ffi.gc(sp_search, lib.sp_search_release)

    def __repr__(self):
        return 'Search(%r)' % self.link.uri

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self._sp_search == other._sp_search
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self._sp_search)

    loaded_event = None
    """:class:`threading.Event` that is set when the search is loaded."""

    @property
    def is_loaded(self):
        """Whether the search's data is loaded."""
        return bool(lib.sp_search_is_loaded(self._sp_search))

    @property
    def error(self):
        """An :class:`ErrorType` associated with the search.

        Check to see if there was problems loading the search.
        """
        return spotify.ErrorType(lib.sp_search_error(self._sp_search))

    def load(self, timeout=None):
        """Block until the search's data is loaded.

        After ``timeout`` seconds with no results :exc:`~spotify.Timeout` is
        raised. If ``timeout`` is :class:`None` the default timeout is used.

        The method returns ``self`` to allow for chaining of calls.
        """
        return utils.load(self._session, self, timeout=timeout)

    @property
    @serialized
    def query(self):
        """The search query.

        Will always return :class:`None` if the search isn't loaded.
        """
        spotify.Error.maybe_raise(self.error)
        query = utils.to_unicode(lib.sp_search_query(self._sp_search))
        return query if query else None

    @property
    @serialized
    def did_you_mean(self):
        """The search's "did you mean" query or :class:`None` if no such
        suggestion exists.

        Will always return :class:`None` if the search isn't loaded.
        """
        spotify.Error.maybe_raise(self.error)
        did_you_mean = utils.to_unicode(
            lib.sp_search_did_you_mean(self._sp_search))
        return did_you_mean if did_you_mean else None

    @property
    @serialized
    def tracks(self):
        """The tracks matching the search query.

        Will always return an empty list if the search isn't loaded.
        """
        spotify.Error.maybe_raise(
            self.error, ignores=[spotify.ErrorType.IS_LOADING])
        if not self.is_loaded:
            return []

        @serialized
        def get_track(sp_search, key):
            return spotify.Track(
                self._session,
                sp_track=lib.sp_search_track(sp_search, key),
                add_ref=True)

        return utils.Sequence(
            sp_obj=self._sp_search,
            add_ref_func=lib.sp_search_add_ref,
            release_func=lib.sp_search_release,
            len_func=lib.sp_search_num_tracks,
            getitem_func=get_track)

    @property
    def track_total(self):
        """The total number of tracks matching the search query.

        If the number is larger than the interval specified at search object
        creation, more search results are available. To fetch these, create a
        new search object with a new interval.
        """
        spotify.Error.maybe_raise(self.error)
        return lib.sp_search_total_tracks(self._sp_search)

    @property
    @serialized
    def albums(self):
        """The albums matching the search query.

        Will always return an empty list if the search isn't loaded.
        """
        spotify.Error.maybe_raise(
            self.error, ignores=[spotify.ErrorType.IS_LOADING])
        if not self.is_loaded:
            return []

        @serialized
        def get_album(sp_search, key):
            return spotify.Album(
                self._session,
                sp_album=lib.sp_search_album(sp_search, key),
                add_ref=True)

        return utils.Sequence(
            sp_obj=self._sp_search,
            add_ref_func=lib.sp_search_add_ref,
            release_func=lib.sp_search_release,
            len_func=lib.sp_search_num_albums,
            getitem_func=get_album)

    @property
    def album_total(self):
        """The total number of albums matching the search query.

        If the number is larger than the interval specified at search object
        creation, more search results are available. To fetch these, create a
        new search object with a new interval.
        """
        spotify.Error.maybe_raise(self.error)
        return lib.sp_search_total_albums(self._sp_search)

    @property
    @serialized
    def artists(self):
        """The artists matching the search query.

        Will always return an empty list if the search isn't loaded.
        """
        spotify.Error.maybe_raise(
            self.error, ignores=[spotify.ErrorType.IS_LOADING])
        if not self.is_loaded:
            return []

        @serialized
        def get_artist(sp_search, key):
            return spotify.Artist(
                self._session,
                sp_artist=lib.sp_search_artist(sp_search, key),
                add_ref=True)

        return utils.Sequence(
            sp_obj=self._sp_search,
            add_ref_func=lib.sp_search_add_ref,
            release_func=lib.sp_search_release,
            len_func=lib.sp_search_num_artists,
            getitem_func=get_artist)

    @property
    def artist_total(self):
        """The total number of artists matching the search query.

        If the number is larger than the interval specified at search object
        creation, more search results are available. To fetch these, create a
        new search object with a new interval.
        """
        spotify.Error.maybe_raise(self.error)
        return lib.sp_search_total_artists(self._sp_search)

    @property
    @serialized
    def playlists(self):
        """The playlists matching the search query as
        :class:`SearchPlaylist` objects containing the name, URI and
        image URI for matching playlists.

        Will always return an empty list if the search isn't loaded.
        """
        spotify.Error.maybe_raise(
            self.error, ignores=[spotify.ErrorType.IS_LOADING])
        if not self.is_loaded:
            return []

        @serialized
        def getitem(sp_search, key):
            return spotify.SearchPlaylist(
                self._session,
                name=utils.to_unicode(
                    lib.sp_search_playlist_name(self._sp_search, key)),
                uri=utils.to_unicode(
                    lib.sp_search_playlist_uri(self._sp_search, key)),
                image_uri=utils.to_unicode(
                    lib.sp_search_playlist_image_uri(self._sp_search, key)))

        return utils.Sequence(
            sp_obj=self._sp_search,
            add_ref_func=lib.sp_search_add_ref,
            release_func=lib.sp_search_release,
            len_func=lib.sp_search_num_playlists,
            getitem_func=getitem)

    @property
    def playlist_total(self):
        """The total number of playlists matching the search query.

        If the number is larger than the interval specified at search object
        creation, more search results are available. To fetch these, create a
        new search object with a new interval.
        """
        spotify.Error.maybe_raise(self.error)
        return lib.sp_search_total_playlists(self._sp_search)

    def more(
            self, callback=None,
            track_count=None, album_count=None, artist_count=None,
            playlist_count=None):
        """Get the next page of search results for the same query.

        If called without arguments, the ``callback`` and ``*_count`` arguments
        from the original search is reused. If anything other than
        :class:`None` is specified, the value is used instead.
        """
        callback = callback or self.callback
        track_offset = self.track_offset + self.track_count
        track_count = track_count or self.track_count
        album_offset = self.album_offset + self.album_count
        album_count = album_count or self.album_count
        artist_offset = self.artist_offset + self.artist_count
        artist_count = artist_count or self.artist_count
        playlist_offset = self.playlist_offset + self.playlist_count
        playlist_count = playlist_count or self.playlist_count

        return Search(
            self._session, query=self.query, callback=callback,
            track_offset=track_offset, track_count=track_count,
            album_offset=album_offset, album_count=album_count,
            artist_offset=artist_offset, artist_count=artist_count,
            playlist_offset=playlist_offset, playlist_count=playlist_count,
            search_type=self.search_type)

    @property
    def link(self):
        """A :class:`Link` to the search."""
        return spotify.Link(
            self._session,
            sp_link=lib.sp_link_create_from_search(self._sp_search),
            add_ref=False)


@ffi.callback('void(sp_search *, void *)')
@serialized
def _search_complete_callback(sp_search, handle):
    logger.debug('search_complete_callback called')
    if handle == ffi.NULL:
        logger.warning('search_complete_callback called without userdata')
        return
    (session, search_result, callback) = ffi.from_handle(handle)
    session._callback_handles.remove(handle)
    search_result.loaded_event.set()
    if callback is not None:
        callback(search_result)


class SearchPlaylist(object):
    """A playlist matching a search query."""

    name = None
    """The name of the playlist."""

    uri = None
    """The URI of the playlist."""

    image_uri = None
    """The URI of the playlist's image."""

    def __init__(self, session, name, uri, image_uri):
        self._session = session
        self.name = name
        self.uri = uri
        self.image_uri = image_uri

    def __repr__(self):
        return 'SearchPlaylist(name=%r, uri=%r)' % (self.name, self.uri)

    @property
    def playlist(self):
        """The :class:`~spotify.Playlist` object for this
        :class:`SearchPlaylist`."""
        return self._session.get_playlist(self.uri)

    @property
    def image(self):
        """The :class:`~spotify.Image` object for this
        :class:`SearchPlaylist`."""
        return self._session.get_image(self.image_uri)


@utils.make_enum('SP_SEARCH_')
class SearchType(utils.IntEnum):
    pass

########NEW FILE########
__FILENAME__ = session
from __future__ import unicode_literals

import logging
import weakref

import spotify
import spotify.connection
import spotify.player
import spotify.social
from spotify import ffi, lib, serialized, utils


__all__ = [
    'Session',
    'SessionEvent',
]

logger = logging.getLogger(__name__)


class Session(utils.EventEmitter):
    """The Spotify session.

    If no ``config`` is provided, the default config is used.

    The session object will emit a number of events. See :class:`SessionEvent`
    for a list of all available events and how to connect your own listener
    functions up to get called when the events happens.

    .. warning::

        You can only have one :class:`Session` instance per process. This is a
        libspotify limitation. If you create a second :class:`Session` instance
        in the same process pyspotify will raise a :exc:`RuntimeError` with the
        message "Session has already been initialized".

    :param config: the session config
    :type config: :class:`Config` or :class:`None`
    """

    @serialized
    def __init__(self, config=None):
        super(Session, self).__init__()

        if spotify._session_instance is not None:
            raise RuntimeError('Session has already been initialized')

        if config is not None:
            self.config = config
        else:
            self.config = spotify.Config()

        if self.config.application_key is None:
            self.config.load_application_key_file()

        sp_session_ptr = ffi.new('sp_session **')

        spotify.Error.maybe_raise(lib.sp_session_create(
            self.config._sp_session_config, sp_session_ptr))

        self._sp_session = ffi.gc(sp_session_ptr[0], lib.sp_session_release)

        self._cache = weakref.WeakValueDictionary()
        self._emitters = []
        self._callback_handles = set()

        self.connection = spotify.connection.Connection(self)
        self.offline = spotify.offline.Offline(self)
        self.player = spotify.player.Player(self)
        self.social = spotify.social.Social(self)
        spotify._session_instance = self

    _cache = None
    """A mapping from sp_* objects to their corresponding Python instances.

    The ``_cached`` helper contructors on wrapper objects use this cache for
    finding and returning existing alive wrapper objects for the sp_* object it
    is about to create a wrapper for.

    The cache *does not* keep objects alive. It's only a means for looking up
    the objects if they are kept alive somewhere else in the application.

    Internal attribute.
    """

    _emitters = None
    """A list of event emitters with attached listeners.

    When an event emitter has attached event listeners, we must keep the
    emitter alive for as long as the listeners are attached. This is achieved
    by adding them to this list.

    When creating wrapper objects around sp_* objects we must also return the
    existing wrapper objects instead of creating new ones so that the set of
    event listeners on the wrapper object can be modified. This is achieved
    with a combination of this list and the :attr:`_cache` mapping.

    Internal attribute.
    """

    _callback_handles = None
    """A set of handles returned by :meth:`spotify.ffi.new_handle`.

    These must be kept alive for the handle to remain valid until the callback
    arrives, even if the end user does not maintain a reference to the object
    the callback works on.

    Internal attribute.
    """

    config = None
    """A :class:`Config` instance with the current configuration.

    Once the session has been created, changing the attributes of this object
    will generally have no effect.
    """

    connection = None
    """An :class:`~spotify.connection.Connection` instance for controlling the
    connection to the Spotify servers."""

    offline = None
    """An :class:`~spotify.offline.Offline` instance for controlling offline
    sync."""

    player = None
    """A :class:`~spotify.player.Player` instance for controlling playback."""

    social = None
    """A :class:`~spotify.social.Social` instance for controlling social
    sharing."""

    def login(self, username, password=None, remember_me=False, blob=None):
        """Authenticate to Spotify's servers.

        You can login with one of two combinations:

        - ``username`` and ``password``
        - ``username`` and ``blob``

        To get the ``blob`` string, you must once log in with ``username`` and
        ``password``. You'll then get the ``blob`` string passed to the
        :attr:`~SessionCallbacks.credentials_blob_updated` callback.

        If you set ``remember_me`` to :class:`True`, you can later login to the
        same account without providing any ``username`` or credentials by
        calling :meth:`relogin`.
        """

        username = utils.to_char(username)

        if password is not None:
            password = utils.to_char(password)
            blob = ffi.NULL
        elif blob is not None:
            password = ffi.NULL
            blob = utils.to_char(blob)
        else:
            raise AttributeError('password or blob is required to login')

        spotify.Error.maybe_raise(lib.sp_session_login(
            self._sp_session, username, password, bool(remember_me), blob))

    def logout(self):
        """Log out the current user.

        If you logged in with the ``remember_me`` argument set to
        :class:`True`, you will also need to call :meth:`forget_me` to
        completely remove all credentials of the user that was logged in.
        """
        spotify.Error.maybe_raise(lib.sp_session_logout(self._sp_session))

    @property
    def remembered_user_name(self):
        """The username of the remembered user from a previous :meth:`login`
        call."""
        return utils.get_with_growing_buffer(
            lib.sp_session_remembered_user, self._sp_session)

    def relogin(self):
        """Relogin as the remembered user.

        To be able do this, you must previously have logged in with
        :meth:`login` with the ``remember_me`` argument set to :class:`True`.

        To check what user you'll be logged in as if you call this method, see
        :attr:`remembered_user_name`.
        """
        spotify.Error.maybe_raise(lib.sp_session_relogin(self._sp_session))

    def forget_me(self):
        """Forget the remembered user from a previous :meth:`login` call."""
        spotify.Error.maybe_raise(lib.sp_session_forget_me(self._sp_session))

    @property
    @serialized
    def user(self):
        """The logged in :class:`User`."""
        sp_user = lib.sp_session_user(self._sp_session)
        if sp_user == ffi.NULL:
            return None
        return spotify.User(self, sp_user=sp_user, add_ref=True)

    @property
    @serialized
    def user_name(self):
        """The username of the logged in user."""
        return utils.to_unicode(lib.sp_session_user_name(self._sp_session))

    @property
    @serialized
    def user_country(self):
        """The country of the currently logged in user.

        The :attr:`~SessionEvent.OFFLINE_STATUS_UPDATED` event is emitted on
        the session object when this changes.
        """
        return utils.to_country(lib.sp_session_user_country(self._sp_session))

    @property
    @serialized
    def playlist_container(self):
        """The :class:`PlaylistContainer` for the currently logged in user."""
        sp_playlistcontainer = lib.sp_session_playlistcontainer(
            self._sp_session)
        if sp_playlistcontainer == ffi.NULL:
            return None
        return spotify.PlaylistContainer._cached(
            self, sp_playlistcontainer, add_ref=True)

    @property
    def inbox(self):
        """The inbox :class:`Playlist` for the currently logged in user."""
        sp_playlist = lib.sp_session_inbox_create(self._sp_session)
        if sp_playlist == ffi.NULL:
            return None
        return spotify.Playlist._cached(
            self, sp_playlist=sp_playlist, add_ref=False)

    def set_cache_size(self, size):
        """Set maximum size in MB for libspotify's cache.

        If set to 0 (the default), up to 10% of the free disk space will be
        used."""
        spotify.Error.maybe_raise(lib.sp_session_set_cache_size(
            self._sp_session, size))

    def flush_caches(self):
        """Write all cached data to disk.

        libspotify does this regularly and on logout, so you should never need
        to call this method yourself.
        """
        spotify.Error.maybe_raise(
            lib.sp_session_flush_caches(self._sp_session))

    def preferred_bitrate(self, bitrate):
        """Set preferred :class:`Bitrate` for music streaming."""
        spotify.Error.maybe_raise(lib.sp_session_preferred_bitrate(
            self._sp_session, bitrate))

    def preferred_offline_bitrate(self, bitrate, allow_resync=False):
        """Set preferred :class:`Bitrate` for offline sync.

        If ``allow_resync`` is :class:`True` libspotify may resynchronize
        already synced tracks.
        """
        spotify.Error.maybe_raise(lib.sp_session_preferred_offline_bitrate(
            self._sp_session, bitrate, allow_resync))

    @property
    def volume_normalization(self):
        """Whether volume normalization is active or not.

        Set to :class:`True` or :class:`False` to change.
        """
        return bool(lib.sp_session_get_volume_normalization(self._sp_session))

    @volume_normalization.setter
    def volume_normalization(self, value):
        spotify.Error.maybe_raise(lib.sp_session_set_volume_normalization(
            self._sp_session, value))

    def process_events(self):
        """Process pending events in libspotify.

        This method must be called for most callbacks to be called. Without
        calling this method, you'll only get the callbacks that are called from
        internal libspotify threads. When the
        :attr:`~SessionEvent.NOTIFY_MAIN_THREAD` event is emitted (from an
        internal libspotify thread), it's your job to make sure this method is
        called (from the thread you use for accessing Spotify), so that further
        callbacks can be triggered (from the same thread).

        pyspotify provides an :class:`~spotify.EventLoop` that you can use for
        processing events when needed.
        """
        next_timeout = ffi.new('int *')

        spotify.Error.maybe_raise(lib.sp_session_process_events(
            self._sp_session, next_timeout))

        return next_timeout[0]

    def inbox_post_tracks(
            self, canonical_username, tracks, message, callback=None):
        """Post a ``message`` and one or more ``tracks`` to the inbox of the
        user with the given ``canonical_username``.

        ``tracks`` can be a single :class:`~spotify.Track` or a list of
        :class:`~spotify.Track` objects.

        Returns an :class:`InboxPostResult` that can be used to check if the
        request completed successfully.

        If callback isn't :class:`None`, it is called with an
        :class:`InboxPostResult` instance when the request has completed.
        """
        return spotify.InboxPostResult(
            self, canonical_username, tracks, message, callback)

    def get_starred(self, canonical_username=None):
        """Get the starred :class:`Playlist` for the user with
        ``canonical_username``.

        If ``canonical_username`` isn't specified, the starred playlist for
        the currently logged in user is returned.
        """
        if canonical_username is None:
            sp_playlist = lib.sp_session_starred_create(self._sp_session)
        else:
            sp_playlist = lib.sp_session_starred_for_user_create(
                self._sp_session, utils.to_bytes(canonical_username))
        if sp_playlist == ffi.NULL:
            return None
        return spotify.Playlist._cached(self, sp_playlist, add_ref=False)

    def get_published_playlists(self, canonical_username=None):
        """Get the :class:`PlaylistContainer` of published playlists for the
        user with ``canonical_username``.

        If ``canonical_username`` isn't specified, the published container for
        the currently logged in user is returned.
        """
        if canonical_username is None:
            canonical_username = ffi.NULL
        else:
            canonical_username = utils.to_bytes(canonical_username)
        sp_playlistcontainer = (
            lib.sp_session_publishedcontainer_for_user_create(
                self._sp_session, canonical_username))
        if sp_playlistcontainer == ffi.NULL:
            return None
        return spotify.PlaylistContainer._cached(
            self, sp_playlistcontainer, add_ref=False)

    def get_link(self, uri):
        """
        Get :class:`Link` from any Spotify URI.

        A link can be created from a string containing a Spotify URI on the
        form ``spotify:...``.

        Example::

            >>> session = spotify.Session()
            # ...
            >>> session.get_link(
            ...     'spotify:track:2Foc5Q5nqNiosCNqttzHof')
            Link('spotify:track:2Foc5Q5nqNiosCNqttzHof')
            >>> session.get_link(
            ...     'http://open.spotify.com/track/4wl1dK5dHGp3Ig51stvxb0')
            Link('spotify:track:4wl1dK5dHGp3Ig51stvxb0')
        """
        return spotify.Link(self, uri=uri)

    def get_track(self, uri):
        """
        Get :class:`Track` from a Spotify track URI.

        Example::

            >>> session = spotify.Session()
            # ...
            >>> track = session.get_track(
            ...     'spotify:track:2Foc5Q5nqNiosCNqttzHof')
            >>> track.load().name
            u'Get Lucky'
        """
        return spotify.Track(self, uri=uri)

    def get_local_track(
            self, artist=None, title=None, album=None, length=None):
        """
        Get :class:`Track` for a local track.

        Spotify's official clients supports adding your local music files to
        Spotify so they can be played in the Spotify client. These are not
        synced with Spotify's servers or between your devices and there is not
        trace of them in your Spotify user account. The exception is when you
        add one of these local tracks to a playlist or mark them as starred.
        This creates a "local track" which pyspotify also will be able to
        observe.

        "Local tracks" can be recognized in several ways:

        - The track's URI will be of the form
          ``spotify:local:ARTIST:ALBUM:TITLE:LENGTH_IN_SECONDS``. Any of the
          parts in all caps can be left out if there is no information
          available. That is, ``spotify:local::::`` is a valid local track URI.

        - :attr:`Link.type` will be :class:`LinkType.LOCALTRACK` for the
          track's link.

        - :attr:`Track.is_local` will be :class:`True` for the track.

        This method can be used to create local tracks that can be starred or
        added to playlists.

        ``artist`` may be an artist name. ``title`` may be a track name.
        ``album`` may be an album name. ``length`` may be a track length in
        milliseconds.

        Note that when creating a local track you provide the length in
        milliseconds, while the local track URI contains the length in seconds.
        """

        if artist is None:
            artist = ''
        if title is None:
            title = ''
        if album is None:
            album = ''
        if length is None:
            length = -1

        artist = utils.to_char(artist)
        title = utils.to_char(title)
        album = utils.to_char(album)
        sp_track = lib.sp_localtrack_create(artist, title, album, length)

        return spotify.Track(self, sp_track=sp_track, add_ref=False)

    def get_album(self, uri):
        """
        Get :class:`Album` from a Spotify album URI.

        Example::

            >>> session = spotify.Session()
            # ...
            >>> album = session.get_album(
            ...     'spotify:album:6wXDbHLesy6zWqQawAa91d')
            >>> album.load().name
            u'Forward / Return'
        """
        return spotify.Album(self, uri=uri)

    def get_artist(self, uri):
        """
        Get :class:`Artist` from a Spotify artist URI.

        Example::

            >>> session = spotify.Session()
            # ...
            >>> artist = session.get_artist(
            ...     'spotify:artist:22xRIphSN7IkPVbErICu7s')
            >>> artist.load().name
            u'Rob Dougan'
        """
        return spotify.Artist(self, uri=uri)

    def get_playlist(self, uri):
        """
        Get :class:`Playlist` from a Spotify playlist URI.

        Example::

            >>> session = spotify.Session()
            # ...
            >>> playlist = session.get_playlist(
            ...     'spotify:user:fiat500c:playlist:54k50VZdvtnIPt4d8RBCmZ')
            >>> playlist.load().name
            u'500C feelgood playlist'
        """
        return spotify.Playlist(self, uri=uri)

    def get_user(self, uri):
        """
        Get :class:`User` from a Spotify user URI.

        Example::

            >>> session = spotify.Session()
            # ...
            >>> user = session.get_user('spotify:user:jodal')
            >>> user.load().display_name
            u'jodal'
        """
        return spotify.User(self, uri=uri)

    def get_image(self, uri, callback=None):
        """
        Get :class:`Image` from a Spotify image URI.

        If ``callback`` isn't :class:`None`, it is expected to be a callable
        that accepts a single argument, an :class:`Image` instance, when
        the image is done loading.

        Example::

            >>> session = spotify.Session()
            # ...
            >>> image = session.get_image(
            ...     'spotify:image:a0bdcbe11b5cd126968e519b5ed1050b0e8183d0')
            >>> image.load().data_uri[:50]
            u'data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEBLAEsAAD'
        """
        return spotify.Image(self, uri=uri, callback=callback)

    def search(
            self, query, callback=None,
            track_offset=0, track_count=20,
            album_offset=0, album_count=20,
            artist_offset=0, artist_count=20,
            playlist_offset=0, playlist_count=20,
            search_type=None):
        """
        Search Spotify for tracks, albums, artists, and playlists matching
        ``query``.

        The ``query`` string can be free format, or use some prefixes like
        ``title:`` and ``artist:`` to limit what to match on. There is no
        official docs on the search query format, but there's a `Spotify blog
        post
        <https://www.spotify.com/blog/archives/2008/01/22/searching-spotify/>`_
        from 2008 with some examples.

        If ``callback`` isn't :class:`None`, it is expected to be a callable
        that accepts a single argument, a :class:`Search` instance, when
        the search completes.

        The ``*_offset`` and ``*_count`` arguments can be used to retrieve more
        search results. libspotify will currently not respect ``*_count``
        values higher than 200, though this may change at any time as the limit
        isn't documented in any official docs. If you want to retrieve more
        than 200 results, you'll have to search multiple times with different
        ``*_offset`` values. See the ``*_total`` attributes on the
        :class:`Search` to see how many results exists, and to figure out
        how many searches you'll need to make to retrieve everything.

        ``search_type`` is a :class:`SearchType` value. It defaults to
        :attr:`SearchType.STANDARD`.
        """
        return spotify.Search(
            self, query=query, callback=callback,
            track_offset=track_offset, track_count=track_count,
            album_offset=album_offset, album_count=album_count,
            artist_offset=artist_offset, artist_count=artist_count,
            playlist_offset=playlist_offset, playlist_count=playlist_count,
            search_type=search_type)

    def get_toplist(
            self, type=None, region=None, canonical_username=None,
            callback=None):
        """Get a Spotify toplist of artists, albums, or tracks that are the
        currently most popular worldwide or in a specific region.

        ``type`` is a :class:`ToplistType` instance that specifies the type of
        toplist to create.

        ``region`` is either a :class:`ToplistRegion` instance, or a 2-letter
        ISO 3166-1 country code as a unicode string, that specifies the
        geographical region to create a toplist for.

        If ``region`` is :attr:`ToplistRegion.USER` and ``canonical_username``
        isn't specified, the region of the current user will be used. If
        ``canonical_username`` is specified, the region of the specified user
        will be used instead.

        If ``callback`` isn't :class:`None`, it is expected to be a callable
        that accepts a single argument, a :class:`Toplist` instance, when the
        toplist request completes.

        Example::

            >>> import spotify
            >>> session = spotify.Session()
            # ...
            >>> toplist = session.get_toplist(
            ...     type=spotify.ToplistType.TRACKS, region='US')
            >>> toplist.load()
            >>> len(toplist.tracks)
            100
            >>> len(toplist.artists)
            0
            >>> toplist.tracks[0]
            Track(u'spotify:track:2dLLR6qlu5UJ5gk0dKz0h3')
        """
        return spotify.Toplist(
            self, type=type, region=region,
            canonical_username=canonical_username, callback=callback)


class SessionEvent(object):
    """Session events.

    Using the :class:`Session` object, you can register listener functions to
    be called when various session related events occurs. This class enumerates
    the available events and the arguments your listener functions will be
    called with.

    Example usage::

        import spotify

        def logged_in(session, error_type):
            if error_type is spotify.ErrorType.OK:
                print('Logged in as %s' % session.user)
            else:
                print('Login failed: %s' % error_type)

        session = spotify.Session()
        session.on(spotify.SessionEvent.LOGGED_IN, logged_in)
        session.login('alice', 's3cret')

    All events will cause debug log statements to be emitted, even if no
    listeners are registered. Thus, there is no need to register listener
    functions just to log that they're called.
    """

    LOGGED_IN = 'logged_in'
    """Called when login has completed.

    Note that even if login has succeeded, that does not mean that you're
    online yet as libspotify may have cached enough information to let you
    authenticate with Spotify while offline.

    This event should be used to get notified about login errors. To get
    notified about the authentication and connection state, refer to the
    :attr:`SessionEvent.CONNECTION_STATE_UPDATED` event.

    :param session: the current session
    :type session: :class:`Session`
    :param error_type: the login error type
    :type error_type: :class:`ErrorType`
    """

    LOGGED_OUT = 'logged_out'
    """Called when logout has completed or there is a permanent connection
    error.

    :param session: the current session
    :type session: :class:`Session`
    """

    METADATA_UPDATED = 'metadata_updated'
    """Called when some metadata has been updated.

    There is no way to know what metadata was updated, so you'll have to
    refresh all you metadata caches.

    :param session: the current session
    :type session: :class:`Session`
    """

    CONNECTION_ERROR = 'connection_error'
    """Called when there is a connection error and libspotify has problems
    reconnecting to the Spotify service.

    May be called repeatedly as long as the problem persists. Will be called
    with an :attr:`ErrorType.OK` error when the problem is resolved.

    :param session: the current session
    :type session: :class:`Session`
    :param error_type: the connection error type
    :type error_type: :class:`ErrorType`
    """

    MESSAGE_TO_USER = 'message_to_user'
    """Called when libspotify wants to show a message to the end user.

    :param session: the current session
    :type session: :class:`Session`
    :param data: the message
    :type data: text
    """

    NOTIFY_MAIN_THREAD = 'notify_main_thread'
    """Called when processing on the main thread is needed.

    When this is called, you should call :meth:`~Session.process_events` from
    your main thread. Failure to do so may cause request timeouts, or a lost
    connection.

    .. warning::

        This event is emitted from an internal libspotify thread. Thus, your
        event listener must not block, and must use proper synchronization
        around anything it does.

    :param session: the current session
    :type session: :class:`Session`
    """

    MUSIC_DELIVERY = 'music_delivery'
    """Called when there is decompressed audio data available.

    If the function returns a lower number of frames consumed than
    ``num_frames``, libspotify will retry delivery of the unconsumed frames in
    about 100ms. This can be used for rate limiting if libspotify is giving you
    audio data too fast.

    .. note::

        You can register at most one event listener for this event.

    .. warning::

        This event is emitted from an internal libspotify thread. Thus, your
        event listener must not block, and must use proper synchronization
        around anything it does.

    :param session: the current session
    :type session: :class:`Session`
    :param audio_format: the audio format
    :type audio_format: :class:`AudioFormat`
    :param frames: the audio frames
    :type frames: bytestring
    :param num_frames: the number of frames
    :type num_frames: int
    :returns: the number of frames consumed
    """

    PLAY_TOKEN_LOST = 'play_token_lost'
    """Music has been paused because an account only allows music to be played
    from one location simultaneously.

    When this event is emitted, you should pause playback.

    :param session: the current session
    :type session: :class:`Session`
    """

    LOG_MESSAGE = 'log_message'
    """Called when libspotify have something to log.

    Note that pyspotify logs this for you, so you'll probably never need to
    register a listener for this event.

    :param session: the current session
    :type session: :class:`Session`
    :param data: the message
    :type data: text
    """

    END_OF_TRACK = 'end_of_track'
    """Called when all audio data for the current track has been delivered.

    :param session: the current session
    :type session: :class:`Session`
    """

    STREAMING_ERROR = 'streaming_error'
    """Called when audio streaming cannot start or continue.

    :param session: the current session
    :type session: :class:`Session`
    :param error_type: the streaming error type
    :type error_type: :class:`ErrorType`
    """

    USER_INFO_UPDATED = 'user_info_updated'
    """Called when anything related to :class:`User` objects is updated.

    :param session: the current session
    :type session: :class:`Session`
    """

    START_PLAYBACK = 'start_playback'
    """Called when audio playback should start.

    You need to implement a listener for the :attr:`GET_AUDIO_BUFFER_STATS`
    event for the :attr:`START_PLAYBACK` event to be useful.

    .. warning::

        This event is emitted from an internal libspotify thread. Thus, your
        event listener must not block, and must use proper synchronization
        around anything it does.

    :param session: the current session
    :type session: :class:`Session`
    """

    STOP_PLAYBACK = 'stop_playback'
    """Called when audio playback should stop.

    You need to implement a listener for the :attr:`GET_AUDIO_BUFFER_STATS`
    event for the :attr:`STOP_PLAYBACK` event to be useful.

    .. warning::

        This event is emitted from an internal libspotify thread. Thus, your
        event listener must not block, and must use proper synchronization
        around anything it does.

    :param session: the current session
    :type session: :class:`Session`
    """

    GET_AUDIO_BUFFER_STATS = 'get_audio_buffer_stats'
    """Called to query the application about its audio buffer.

    .. note::

        You can register at most one event listener for this event.

    .. warning::

        This event is emitted from an internal libspotify thread. Thus, your
        event listener must not block, and must use proper synchronization
        around anything it does.

    :param session: the current session
    :type session: :class:`Session`
    :returns: an :class:`AudioBufferStats` instance
    """

    OFFLINE_STATUS_UPDATED = 'offline_status_updated'
    """Called when offline sync status is updated.

    :param session: the current session
    :type session: :class:`Session`
    """

    CREDENTIALS_BLOB_UPDATED = 'credentials_blob_updated'
    """Called when storable credentials have been updated, typically right
    after login.

    The ``blob`` argument can be stored and later passed to
    :meth:`~Session.login` to login without storing the user's password.

    :param session: the current session
    :type session: :class:`Session`
    :param blob: the authentication blob
    :type blob: bytestring
    """

    CONNECTION_STATE_UPDATED = 'connection_state_updated'
    """Called when the connection state is updated.

    The connection state includes login, logout, offline mode, etc.

    :param session: the current session
    :type session: :class:`Session`
    """

    SCROBBLE_ERROR = 'scrobble_error'
    """Called when there is a scrobble error event.

    :param session: the current session
    :type session: :class:`Session`
    :param error_type: the scrobble error type
    :type error_type: :class:`ErrorType`
    """

    PRIVATE_SESSION_MODE_CHANGED = 'private_session_mode_changed'
    """Called when there is a change in the private session mode.

    :param session: the current session
    :type session: :class:`Session`
    :param is_private: whether the session is private
    :type is_private: bool
    """


class _SessionCallbacks(object):
    """Internal class."""

    @classmethod
    def get_struct(cls):
        return ffi.new('sp_session_callbacks *', {
            'logged_in': cls.logged_in,
            'logged_out': cls.logged_out,
            'metadata_updated': cls.metadata_updated,
            'connection_error': cls.connection_error,
            'message_to_user': cls.message_to_user,
            'notify_main_thread': cls.notify_main_thread,
            'music_delivery': cls.music_delivery,
            'play_token_lost': cls.play_token_lost,
            'log_message': cls.log_message,
            'end_of_track': cls.end_of_track,
            'streaming_error': cls.streaming_error,
            'userinfo_updated': cls.user_info_updated,
            'start_playback': cls.start_playback,
            'stop_playback': cls.stop_playback,
            'get_audio_buffer_stats': cls.get_audio_buffer_stats,
            'offline_status_updated': cls.offline_status_updated,
            'credentials_blob_updated': cls.credentials_blob_updated,
            'connectionstate_updated': cls.connection_state_updated,
            'scrobble_error': cls.scrobble_error,
            'private_session_mode_changed': cls.private_session_mode_changed,
        })

    # XXX Avoid use of the spotify._session_instance global in the following
    # callbacks.

    @staticmethod
    @ffi.callback('void(sp_session *, sp_error)')
    def logged_in(sp_session, sp_error):
        if not spotify._session_instance:
            return
        if sp_error == spotify.ErrorType.OK:
            logger.info('Logged in')
        else:
            logger.error('Login error: %s', spotify.ErrorType(sp_error))
        spotify._session_instance.emit(
            SessionEvent.LOGGED_IN,
            spotify._session_instance, spotify.ErrorType(sp_error))

    @staticmethod
    @ffi.callback('void(sp_session *)')
    def logged_out(sp_session):
        if not spotify._session_instance:
            return
        logger.info('Logged out')
        spotify._session_instance.emit(
            SessionEvent.LOGGED_OUT, spotify._session_instance)

    @staticmethod
    @ffi.callback('void(sp_session *)')
    def metadata_updated(sp_session):
        if not spotify._session_instance:
            return
        logger.debug('Metadata updated')
        spotify._session_instance.emit(
            SessionEvent.METADATA_UPDATED, spotify._session_instance)

    @staticmethod
    @ffi.callback('void(sp_session *, sp_error)')
    def connection_error(sp_session, sp_error):
        if not spotify._session_instance:
            return
        error_type = spotify.ErrorType(sp_error)
        logger.error('Connection error: %s', error_type)
        spotify._session_instance.emit(
            SessionEvent.CONNECTION_ERROR,
            spotify._session_instance, error_type)

    @staticmethod
    @ffi.callback('void(sp_session *, const char *)')
    def message_to_user(sp_session, data):
        if not spotify._session_instance:
            return
        data = utils.to_unicode(data).strip()
        logger.debug('Message to user: %s', data)
        spotify._session_instance.emit(
            SessionEvent.MESSAGE_TO_USER, spotify._session_instance, data)

    @staticmethod
    @ffi.callback('void(sp_session *)')
    def notify_main_thread(sp_session):
        if not spotify._session_instance:
            return
        logger.debug('Notify main thread')
        spotify._session_instance.emit(
            SessionEvent.NOTIFY_MAIN_THREAD, spotify._session_instance)

    @staticmethod
    @ffi.callback(
        'int(sp_session *, const sp_audioformat *, const void *, int)')
    def music_delivery(sp_session, sp_audioformat, frames, num_frames):
        if not spotify._session_instance:
            return 0
        if spotify._session_instance.num_listeners(
                SessionEvent.MUSIC_DELIVERY) == 0:
            logger.debug('Music delivery, but no listener')
            return 0
        audio_format = spotify.AudioFormat(sp_audioformat)
        frames_buffer = ffi.buffer(
            frames, audio_format.frame_size() * num_frames)
        frames_bytes = frames_buffer[:]
        num_frames_consumed = spotify._session_instance.call(
            SessionEvent.MUSIC_DELIVERY,
            spotify._session_instance, audio_format, frames_bytes, num_frames)
        logger.debug(
            'Music delivery of %d frames, %d consumed', num_frames,
            num_frames_consumed)
        return num_frames_consumed

    @staticmethod
    @ffi.callback('void(sp_session *)')
    def play_token_lost(sp_session):
        if not spotify._session_instance:
            return
        logger.debug('Play token lost')
        spotify._session_instance.emit(
            SessionEvent.PLAY_TOKEN_LOST, spotify._session_instance)

    @staticmethod
    @ffi.callback('void(sp_session *, const char *)')
    def log_message(sp_session, data):
        if not spotify._session_instance:
            return
        data = utils.to_unicode(data).strip()
        logger.debug('libspotify log message: %s', data)
        spotify._session_instance.emit(
            SessionEvent.LOG_MESSAGE, spotify._session_instance, data)

    @staticmethod
    @ffi.callback('void(sp_session *)')
    def end_of_track(sp_session):
        if not spotify._session_instance:
            return
        logger.debug('End of track')
        spotify._session_instance.emit(
            SessionEvent.END_OF_TRACK, spotify._session_instance)

    @staticmethod
    @ffi.callback('void(sp_session *, sp_error)')
    def streaming_error(sp_session, sp_error):
        if not spotify._session_instance:
            return
        error_type = spotify.ErrorType(sp_error)
        logger.error('Streaming error: %s', error_type)
        spotify._session_instance.emit(
            SessionEvent.STREAMING_ERROR,
            spotify._session_instance, error_type)

    @staticmethod
    @ffi.callback('void(sp_session *)')
    def user_info_updated(sp_session):
        if not spotify._session_instance:
            return
        logger.debug('User info updated')
        spotify._session_instance.emit(
            SessionEvent.USER_INFO_UPDATED, spotify._session_instance)

    @staticmethod
    @ffi.callback('void(sp_session *)')
    def start_playback(sp_session):
        if not spotify._session_instance:
            return
        logger.debug('Start playback called')
        spotify._session_instance.emit(
            SessionEvent.START_PLAYBACK, spotify._session_instance)

    @staticmethod
    @ffi.callback('void(sp_session *)')
    def stop_playback(sp_session):
        if not spotify._session_instance:
            return
        logger.debug('Stop playback called')
        spotify._session_instance.emit(
            SessionEvent.STOP_PLAYBACK, spotify._session_instance)

    @staticmethod
    @ffi.callback('void(sp_session *, sp_audio_buffer_stats *)')
    def get_audio_buffer_stats(sp_session, sp_audio_buffer_stats):
        if not spotify._session_instance:
            return
        if spotify._session_instance.num_listeners(
                SessionEvent.GET_AUDIO_BUFFER_STATS) == 0:
            logger.debug('Audio buffer stats requested, but no listener')
            return
        logger.debug('Audio buffer stats requested')
        stats = spotify._session_instance.call(
            SessionEvent.GET_AUDIO_BUFFER_STATS, spotify._session_instance)
        sp_audio_buffer_stats.samples = stats.samples
        sp_audio_buffer_stats.stutter = stats.stutter

    @staticmethod
    @ffi.callback('void(sp_session *)')
    def offline_status_updated(sp_session):
        if not spotify._session_instance:
            return
        logger.debug('Offline status updated')
        spotify._session_instance.emit(
            SessionEvent.OFFLINE_STATUS_UPDATED, spotify._session_instance)

    @staticmethod
    @ffi.callback('void(sp_session *, const char *)')
    def credentials_blob_updated(sp_session, data):
        if not spotify._session_instance:
            return
        data = ffi.string(data)
        logger.debug('Credentials blob updated: %r', data)
        spotify._session_instance.emit(
            SessionEvent.CREDENTIALS_BLOB_UPDATED,
            spotify._session_instance, data)

    @staticmethod
    @ffi.callback('void(sp_session *)')
    def connection_state_updated(sp_session):
        if not spotify._session_instance:
            return
        logger.debug('Connection state updated')
        spotify._session_instance.emit(
            SessionEvent.CONNECTION_STATE_UPDATED,
            spotify._session_instance)

    @staticmethod
    @ffi.callback('void(sp_session *, sp_error)')
    def scrobble_error(sp_session, sp_error):
        if not spotify._session_instance:
            return
        error_type = spotify.ErrorType(sp_error)
        logger.error('Scrobble error: %s', error_type)
        spotify._session_instance.emit(
            SessionEvent.SCROBBLE_ERROR,
            spotify._session_instance, error_type)

    @staticmethod
    @ffi.callback('void(sp_session *, bool)')
    def private_session_mode_changed(sp_session, is_private):
        if not spotify._session_instance:
            return
        is_private = bool(is_private)
        status = 'private' if is_private else 'public'
        logger.error('Private session mode changed: %s', status)
        spotify._session_instance.emit(
            SessionEvent.PRIVATE_SESSION_MODE_CHANGED,
            spotify._session_instance, is_private)

########NEW FILE########
__FILENAME__ = sink
from __future__ import unicode_literals

import sys

import spotify

__all__ = [
    'AlsaSink',
    'PortAudioSink',
]


class Sink(object):
    def on(self):
        """Turn on the audio sink.

        This is done automatically when the sink is instantiated, so you'll
        only need to call this method if you ever call :meth:`off` and want to
        turn the sink back on.
        """
        assert self._session.num_listeners(
            spotify.SessionEvent.MUSIC_DELIVERY) == 0
        self._session.on(
            spotify.SessionEvent.MUSIC_DELIVERY, self._on_music_delivery)

    def off(self):
        """Turn off the audio sink.

        This disconnects the sink from the relevant session events.
        """
        self._session.off(
            spotify.SessionEvent.MUSIC_DELIVERY, self._on_music_delivery)
        assert self._session.num_listeners(
            spotify.SessionEvent.MUSIC_DELIVERY) == 0
        self._close()

    def _on_music_delivery(self, session, audio_format, frames, num_frames):
        # This method is called from an internal libspotify thread and must
        # not block in any way.
        raise NotImplementedError

    def _close(self):
        pass


class AlsaSink(Sink):
    """Audio sink for systems using ALSA, e.g. most Linux systems.

    This audio sink requires `pyalsaaudio
    <https://pypi.python.org/pypi/pyalsaaudio>`_. pyalsaaudio is probably
    packaged in your Linux distribution. For example, on Debian/Ubuntu you can
    install the package ``python-alsaaudio``.

    The ``card`` keyword argument is passed on to :class:`alsaaudio.PCM`.
    Please refer to the pyalsaaudio documentation for details.

    Example::

        >>> import spotify
        >>> session = spotify.Session()
        >>> audio = spotify.AlsaSink(session)
        >>> loop = spotify.EventLoop(session)
        >>> loop.start()
        # Login, etc...
        >>> track = session.get_track('spotify:track:3N2UhXZI4Gf64Ku3cCjz2g')
        >>> track.load()
        >>> session.player.load(track)
        >>> session.player.play()
        # Listen to music...

    .. warning::

        There is a known memory leak in pyalsaaudio 0.7 when used on Python
        3.x which makes :class:`AlsaSink` unfeasible for anything else than
        short demonstrations. This issue is not present on Python 2.7.

        For more details, see `pyspotify issue #127
        <https://github.com/mopidy/pyspotify/issues/127>`_ and `pyalsaaudio
        issue #16 <https://sourceforge.net/p/pyalsaaudio/bugs/16/>`_.
    """

    def __init__(self, session, card='default'):
        self._session = session
        self._card = card

        import alsaaudio  # Crash early if not available
        self._alsaaudio = alsaaudio
        self._device = None

        self.on()

    def _on_music_delivery(self, session, audio_format, frames, num_frames):
        assert (
            audio_format.sample_type == spotify.SampleType.INT16_NATIVE_ENDIAN)

        if self._device is None:
            self._device = self._alsaaudio.PCM(
                mode=self._alsaaudio.PCM_NONBLOCK, card=self._card)
            if sys.byteorder == 'little':
                self._device.setformat(self._alsaaudio.PCM_FORMAT_S16_LE)
            else:
                self._device.setformat(self._alsaaudio.PCM_FORMAT_S16_BE)
            self._device.setrate(audio_format.sample_rate)
            self._device.setchannels(audio_format.channels)
            self._device.setperiodsize(num_frames * audio_format.frame_size())

        return self._device.write(frames)

    def _close(self):
        if self._device is not None:
            self._device.close()
            self._device = None


class PortAudioSink(Sink):
    """Audio sink for `PortAudio <http://www.portaudio.com/>`_.

    PortAudio is available for many platforms, including Linux, OS X, and
    Windows.

    This audio sink requires `pyaudio <https://pypi.python.org/pypi/pyaudio>`_.
    pyaudio is probably packaged in your Linux distribution. For example, on
    Debian/Ubuntu you can install the package ``python-pyaudio`` or
    ``python3-pyaudio``.

    For an example, see the :class:`AlsaSink` example. Just replace
    ``AlsaSink`` with ``PortAudioSink``.
    """

    def __init__(self, session):
        self._session = session

        import pyaudio  # Crash early if not available
        self._pyaudio = pyaudio
        self._device = self._pyaudio.PyAudio()
        self._stream = None

        self.on()

    def _on_music_delivery(self, session, audio_format, frames, num_frames):
        assert (
            audio_format.sample_type == spotify.SampleType.INT16_NATIVE_ENDIAN)

        if self._stream is None:
            self._stream = self._device.open(
                format=self._pyaudio.paInt16, channels=audio_format.channels,
                rate=audio_format.sample_rate, output=True)

        # XXX write() is a blocking call. There are two non-blocking
        # alternatives:
        # 1) Only feed write() with the number of frames returned by
        # self._stream.get_write_available() on each call. This causes buffer
        # underruns every third or fourth write().
        # 2) Let pyaudio call a callback function when it needs data, but then
        # we need to introduce a thread safe buffer here which is filled when
        # libspotify got data and drained when pyaudio needs data.
        self._stream.write(frames, num_frames=num_frames)
        return num_frames

    def _close(self):
        if self._stream is not None:
            self._stream.close()
            self._stream = None

########NEW FILE########
__FILENAME__ = social
from __future__ import unicode_literals

import spotify
from spotify import ffi, lib, utils


__all__ = [
    'ScrobblingState',
    'SocialProvider',
]


class Social(object):
    """Social sharing controller.

    You'll never need to create an instance of this class yourself. You'll find
    it ready to use as the :attr:`~Session.social` attribute on the
    :class:`Session` instance.
    """

    def __init__(self, session):
        self._session = session

    @property
    def private_session(self):
        """Whether the session is private.

        Set to :class:`True` or :class:`False` to change.
        """
        return bool(
            lib.sp_session_is_private_session(self._session._sp_session))

    @private_session.setter
    def private_session(self, value):
        # XXX sp_session_set_private_session() segfaults unless we login and
        # call process_events() at least once before calling it. If we log out
        # again, calling the function still works without segfaults. This bug
        # has been reported to Spotify on IRC.
        if self._session.connection.state != spotify.ConnectionState.LOGGED_IN:
            raise RuntimeError(
                'private_session can only be set when the session is logged '
                'in. This is temporary workaround of a libspotify bug, '
                'causing the application to segfault otherwise.')
        spotify.Error.maybe_raise(lib.sp_session_set_private_session(
            self._session._sp_session, bool(value)))

    def is_scrobbling(self, social_provider):
        """Get the :class:`ScrobblingState` for the given
        ``social_provider``."""
        scrobbling_state = ffi.new('sp_scrobbling_state *')
        spotify.Error.maybe_raise(lib.sp_session_is_scrobbling(
            self._session._sp_session, social_provider, scrobbling_state))
        return spotify.ScrobblingState(scrobbling_state[0])

    def is_scrobbling_possible(self, social_provider):
        """Check if the scrobbling settings should be shown to the user."""
        out = ffi.new('bool *')
        spotify.Error.maybe_raise(lib.sp_session_is_scrobbling_possible(
            self._session._sp_session, social_provider, out))
        return bool(out[0])

    def set_scrobbling(self, social_provider, scrobbling_state):
        """Set the ``scrobbling_state`` for the given ``social_provider``."""
        spotify.Error.maybe_raise(lib.sp_session_set_scrobbling(
            self._session._sp_session, social_provider, scrobbling_state))

    def set_social_credentials(self, social_provider, username, password):
        """Set the user's credentials with a social provider.

        Currently this is only relevant for Last.fm. Call
        :meth:`set_scrobbling` to force an authentication attempt with the
        provider. If authentication fails a
        :attr:`~SessionEvent.SCROBBLE_ERROR` event will be emitted on the
        :class:`Session` object.
        """
        spotify.Error.maybe_raise(lib.sp_session_set_social_credentials(
            self._session._sp_session, social_provider,
            utils.to_char(username), utils.to_char(password)))


@utils.make_enum('SP_SCROBBLING_STATE_')
class ScrobblingState(utils.IntEnum):
    pass


@utils.make_enum('SP_SOCIAL_PROVIDER_')
class SocialProvider(utils.IntEnum):
    pass

########NEW FILE########
__FILENAME__ = toplist
from __future__ import unicode_literals

import logging
import threading

import spotify
from spotify import ffi, lib, serialized, utils


__all__ = [
    'Toplist',
    'ToplistRegion',
    'ToplistType',
]

logger = logging.getLogger(__name__)


class Toplist(object):
    """A Spotify toplist of artists, albums or tracks that are currently most
    popular worldwide or in a specific region.

    Call the :meth:`~Session.get_toplist` method on your :class:`Session`
    instance to get a :class:`Toplist` back.
    """

    type = None
    """A :class:`ToplistType` instance that specifies what kind of toplist this
    is: top artists, top albums, or top tracks.

    Changing this field has no effect on existing toplists.
    """

    region = None
    """Either a :class:`ToplistRegion` instance, or a 2-letter ISO 3166-1
    country code, that specifies the geographical region this toplist is for.

    Changing this field has no effect on existing toplists.
    """

    canonical_username = None
    """If :attr:`region` is :attr:`ToplistRegion.USER`, then this field
    specifies which user the toplist is for.

    Changing this field has no effect on existing toplists.
    """

    loaded_event = None
    """:class:`threading.Event` that is set when the toplist is loaded."""

    def __init__(
            self, session, type=None, region=None, canonical_username=None,
            callback=None, sp_toplistbrowse=None, add_ref=True):

        assert (type is not None and region is not None) or sp_toplistbrowse, \
            'type and region, or sp_toplistbrowse, is required'

        self._session = session
        self.type = type
        self.region = region
        self.canonical_username = canonical_username
        self.loaded_event = threading.Event()

        if sp_toplistbrowse is None:
            if isinstance(region, ToplistRegion):
                region = int(region)
            else:
                region = utils.to_country_code(region)

            handle = ffi.new_handle((self._session, self, callback))
            self._session._callback_handles.add(handle)

            sp_toplistbrowse = lib.sp_toplistbrowse_create(
                self._session._sp_session, int(type), region,
                utils.to_char_or_null(canonical_username),
                _toplistbrowse_complete_callback, handle)
            add_ref = False

        if add_ref:
            lib.sp_toplistbrowse_add_ref(sp_toplistbrowse)
        self._sp_toplistbrowse = ffi.gc(
            sp_toplistbrowse, lib.sp_toplistbrowse_release)

    def __repr__(self):
        return 'Toplist(type=%r, region=%r, canonical_username=%r)' % (
            self.type, self.region, self.canonical_username)

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self._sp_toplistbrowse == other._sp_toplistbrowse
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self._sp_toplistbrowse)

    @property
    def is_loaded(self):
        """Whether the toplist's data is loaded yet."""
        return bool(lib.sp_toplistbrowse_is_loaded(self._sp_toplistbrowse))

    def load(self, timeout=None):
        """Block until the user's data is loaded.

        After ``timeout`` seconds with no results :exc:`~spotify.Timeout` is
        raised. If ``timeout`` is :class:`None` the default timeout is used.

        The method returns ``self`` to allow for chaining of calls.
        """
        return utils.load(self._session, self, timeout=timeout)

    @property
    def error(self):
        """An :class:`ErrorType` associated with the toplist.

        Check to see if there was problems creating the toplist.
        """
        return spotify.ErrorType(
            lib.sp_toplistbrowse_error(self._sp_toplistbrowse))

    @property
    def backend_request_duration(self):
        """The time in ms that was spent waiting for the Spotify backend to
        create the toplist.

        Returns ``-1`` if the request was served from local cache. Returns
        :class:`None` if the toplist isn't loaded yet.
        """
        if not self.is_loaded:
            return None
        return lib.sp_toplistbrowse_backend_request_duration(
            self._sp_toplistbrowse)

    @property
    @serialized
    def tracks(self):
        """The tracks in the toplist.

        Will always return an empty list if the toplist isn't loaded.
        """
        spotify.Error.maybe_raise(self.error)
        if not self.is_loaded:
            return []

        @serialized
        def get_track(sp_toplistbrowse, key):
            return spotify.Track(
                self._session,
                sp_track=lib.sp_toplistbrowse_track(sp_toplistbrowse, key),
                add_ref=True)

        return utils.Sequence(
            sp_obj=self._sp_toplistbrowse,
            add_ref_func=lib.sp_toplistbrowse_add_ref,
            release_func=lib.sp_toplistbrowse_release,
            len_func=lib.sp_toplistbrowse_num_tracks,
            getitem_func=get_track)

    @property
    @serialized
    def albums(self):
        """The albums in the toplist.

        Will always return an empty list if the toplist isn't loaded.
        """
        spotify.Error.maybe_raise(self.error)
        if not self.is_loaded:
            return []

        @serialized
        def get_album(sp_toplistbrowse, key):
            return spotify.Album(
                self._session,
                sp_album=lib.sp_toplistbrowse_album(sp_toplistbrowse, key),
                add_ref=True)

        return utils.Sequence(
            sp_obj=self._sp_toplistbrowse,
            add_ref_func=lib.sp_toplistbrowse_add_ref,
            release_func=lib.sp_toplistbrowse_release,
            len_func=lib.sp_toplistbrowse_num_albums,
            getitem_func=get_album)

    @property
    @serialized
    def artists(self):
        """The artists in the toplist.

        Will always return an empty list if the toplist isn't loaded.
        """
        spotify.Error.maybe_raise(self.error)
        if not self.is_loaded:
            return []

        @serialized
        def get_artist(sp_toplistbrowse, key):
            return spotify.Artist(
                self._session,
                sp_artist=lib.sp_toplistbrowse_artist(sp_toplistbrowse, key),
                add_ref=True)

        return utils.Sequence(
            sp_obj=self._sp_toplistbrowse,
            add_ref_func=lib.sp_toplistbrowse_add_ref,
            release_func=lib.sp_toplistbrowse_release,
            len_func=lib.sp_toplistbrowse_num_artists,
            getitem_func=get_artist)


@ffi.callback('void(sp_toplistbrowse *, void *)')
@serialized
def _toplistbrowse_complete_callback(sp_toplistbrowse, handle):
    logger.debug('toplistbrowse_complete_callback called')
    if handle == ffi.NULL:
        logger.warning(
            'toplistbrowse_complete_callback called without userdata')
        return
    (session, toplist, callback) = ffi.from_handle(handle)
    session._callback_handles.remove(handle)
    toplist.loaded_event.set()
    if callback is not None:
        callback(toplist)


@utils.make_enum('SP_TOPLIST_REGION_')
class ToplistRegion(utils.IntEnum):
    pass


@utils.make_enum('SP_TOPLIST_TYPE_')
class ToplistType(utils.IntEnum):
    pass

########NEW FILE########
__FILENAME__ = track
from __future__ import unicode_literals

import spotify
from spotify import ffi, lib, serialized, utils


__all__ = [
    'Track',
    'TrackAvailability',
    'TrackOfflineStatus',
]


class Track(object):
    """A Spotify track.

    You can get tracks from playlists or albums, or you can create a
    :class:`Track` yourself from a Spotify URI::

        >>> session = spotify.Session()
        # ...
        >>> track = session.get_track('spotify:track:2Foc5Q5nqNiosCNqttzHof')
        >>> track.load().name
        u'Get Lucky'
    """

    def __init__(self, session, uri=None, sp_track=None, add_ref=True):
        assert uri or sp_track, 'uri or sp_track is required'

        self._session = session

        if uri is not None:
            track = spotify.Link(self._session, uri=uri).as_track()
            if track is None:
                raise ValueError(
                    'Failed to get track from Spotify URI: %r' % uri)
            sp_track = track._sp_track
            add_ref = True

        if add_ref:
            lib.sp_track_add_ref(sp_track)
        self._sp_track = ffi.gc(sp_track, lib.sp_track_release)

    def __repr__(self):
        return 'Track(%r)' % self.link.uri

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self._sp_track == other._sp_track
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self._sp_track)

    @property
    def is_loaded(self):
        """Whether the track's data is loaded."""
        return bool(lib.sp_track_is_loaded(self._sp_track))

    @property
    def error(self):
        """An :class:`ErrorType` associated with the track.

        Check to see if there was problems loading the track.
        """
        return spotify.ErrorType(lib.sp_track_error(self._sp_track))

    def load(self, timeout=None):
        """Block until the track's data is loaded.

        After ``timeout`` seconds with no results :exc:`~spotify.Timeout` is
        raised. If ``timeout`` is :class:`None` the default timeout is used.

        The method returns ``self`` to allow for chaining of calls.
        """
        return utils.load(self._session, self, timeout=timeout)

    @property
    def offline_status(self):
        """The :class:`TrackOfflineStatus` of the track.

        The :attr:`~SessionCallbacks.metadata_updated` callback is called when
        the offline status changes.

        Will always return :class:`None` if the track isn't loaded.
        """
        spotify.Error.maybe_raise(
            self.error, ignores=[spotify.ErrorType.IS_LOADING])
        if not self.is_loaded:
            return None
        return TrackOfflineStatus(
            lib.sp_track_offline_get_status(self._sp_track))

    @property
    def availability(self):
        """The :class:`TrackAvailability` of the track.

        Will always return :class:`None` if the track isn't loaded.
        """
        spotify.Error.maybe_raise(
            self.error, ignores=[spotify.ErrorType.IS_LOADING])
        if not self.is_loaded:
            return None
        return TrackAvailability(lib.sp_track_get_availability(
            self._session._sp_session, self._sp_track))

    @property
    def is_local(self):
        """Whether the track is a local track.

        Will always return :class:`None` if the track isn't loaded.
        """
        spotify.Error.maybe_raise(
            self.error, ignores=[spotify.ErrorType.IS_LOADING])
        if not self.is_loaded:
            return None
        return bool(lib.sp_track_is_local(
            self._session._sp_session, self._sp_track))

    @property
    def is_autolinked(self):
        """Whether the track is a autolinked to another track.

        Will always return :class:`None` if the track isn't loaded.

        See :attr:`playable`.
        """
        spotify.Error.maybe_raise(
            self.error, ignores=[spotify.ErrorType.IS_LOADING])
        if not self.is_loaded:
            return None
        return bool(lib.sp_track_is_autolinked(
            self._session._sp_session, self._sp_track))

    @property
    @serialized
    def playable(self):
        """The actual track that will be played when this track is played.

        Will always return :class:`None` if the track isn't loaded.

        See :attr:`is_autolinked`.
        """
        spotify.Error.maybe_raise(
            self.error, ignores=[spotify.ErrorType.IS_LOADING])
        if not self.is_loaded:
            return None
        return Track(
            self._session,
            sp_track=lib.sp_track_get_playable(
                self._session._sp_session, self._sp_track),
            add_ref=True)

    @property
    def is_placeholder(self):
        """Whether the track is a placeholder for a non-track object in the
        playlist.

        To convert to the real object::

            >>> session = spotify.Session()
            # ...
            >>> track = session.get_track(
            ...     'spotify:track:2Foc5Q5nqNiosCNqttzHof')
            >>> track.load()
            >>> track.is_placeholder
            True
            >>> track.link.type
            <LinkType.ARTIST: ...>
            >>> artist = track.link.as_artist()

        Will always return :class:`None` if the track isn't loaded.
        """
        spotify.Error.maybe_raise(
            self.error, ignores=[spotify.ErrorType.IS_LOADING])
        if not self.is_loaded:
            return None
        return bool(lib.sp_track_is_placeholder(self._sp_track))

    @property
    def starred(self):
        """Whether the track is starred by the current user.

        Set to :class:`True` or :class:`False` to change.

        Will always be :class:`None` if the track isn't loaded.
        """
        spotify.Error.maybe_raise(
            self.error, ignores=[spotify.ErrorType.IS_LOADING])
        if not self.is_loaded:
            return None
        return bool(lib.sp_track_is_starred(
            self._session._sp_session, self._sp_track))

    @starred.setter
    def starred(self, value):
        tracks = ffi.new('sp_track *[]', 1)
        tracks[0] = self._sp_track
        spotify.Error.maybe_raise(lib.sp_track_set_starred(
            self._session._sp_session, tracks, len(tracks),
            bool(value)))

    @property
    @serialized
    def artists(self):
        """The artists performing on the track.

        Will always return :class:`None` if the track isn't loaded.
        """
        spotify.Error.maybe_raise(
            self.error, ignores=[spotify.ErrorType.IS_LOADING])
        if not self.is_loaded:
            return []

        @serialized
        def get_artist(sp_track, key):
            return spotify.Artist(
                self._session,
                sp_artist=lib.sp_track_artist(sp_track, key),
                add_ref=True)

        return utils.Sequence(
            sp_obj=self._sp_track,
            add_ref_func=lib.sp_track_add_ref,
            release_func=lib.sp_track_release,
            len_func=lib.sp_track_num_artists,
            getitem_func=get_artist)

    @property
    @serialized
    def album(self):
        """The album of the track.

        Will always return :class:`None` if the track isn't loaded.
        """
        spotify.Error.maybe_raise(
            self.error, ignores=[spotify.ErrorType.IS_LOADING])
        if not self.is_loaded:
            return None
        sp_album = lib.sp_track_album(self._sp_track)
        return spotify.Album(self._session, sp_album=sp_album, add_ref=True)

    @property
    @serialized
    def name(self):
        """The track's name.

        Will always return :class:`None` if the track isn't loaded.
        """
        spotify.Error.maybe_raise(
            self.error, ignores=[spotify.ErrorType.IS_LOADING])
        if not self.is_loaded:
            return None
        return utils.to_unicode(lib.sp_track_name(self._sp_track))

    @property
    def duration(self):
        """The track's duration in milliseconds.

        Will always return :class:`None` if the track isn't loaded.
        """
        spotify.Error.maybe_raise(
            self.error, ignores=[spotify.ErrorType.IS_LOADING])
        if not self.is_loaded:
            return None
        return lib.sp_track_duration(self._sp_track)

    @property
    def popularity(self):
        """The track's popularity in the range 0-100, 0 if undefined.

        Will always return :class:`None` if the track isn't loaded.
        """
        spotify.Error.maybe_raise(
            self.error, ignores=[spotify.ErrorType.IS_LOADING])
        if not self.is_loaded:
            return None
        return lib.sp_track_popularity(self._sp_track)

    @property
    def disc(self):
        """The track's disc number. 1 or higher.

        Will always return :class:`None` if the track isn't part of an album or
        artist browser.
        """
        spotify.Error.maybe_raise(
            self.error, ignores=[spotify.ErrorType.IS_LOADING])
        if not self.is_loaded:
            return None
        return lib.sp_track_disc(self._sp_track)

    @property
    def index(self):
        """The track's index number. 1 or higher.

        Will always return :class:`None` if the track isn't part of an album or
        artist browser.
        """
        spotify.Error.maybe_raise(
            self.error, ignores=[spotify.ErrorType.IS_LOADING])
        if not self.is_loaded:
            return None
        return lib.sp_track_index(self._sp_track)

    @property
    def link(self):
        """A :class:`Link` to the track."""
        return self.link_with_offset(0)

    def link_with_offset(self, offset):
        """A :class:`Link` to the track with an ``offset`` in milliseconds into
        the track."""
        return spotify.Link(
            self._session,
            sp_link=lib.sp_link_create_from_track(self._sp_track, offset),
            add_ref=False)


@utils.make_enum('SP_TRACK_AVAILABILITY_')
class TrackAvailability(utils.IntEnum):
    pass


@utils.make_enum('SP_TRACK_OFFLINE_')
class TrackOfflineStatus(utils.IntEnum):
    pass

########NEW FILE########
__FILENAME__ = user
from __future__ import unicode_literals

import spotify
from spotify import ffi, lib, serialized, utils


__all__ = [
    'User',
]


class User(object):
    """A Spotify user.

    You can get users from the session, or you can create a :class:`User`
    yourself from a Spotify URI::

        >>> session = spotify.Session()
        # ...
        >>> user = session.get_user('spotify:user:jodal')
        >>> user.load().display_name
        u'jodal'
    """

    def __init__(self, session, uri=None, sp_user=None, add_ref=True):
        assert uri or sp_user, 'uri or sp_user is required'

        self._session = session

        if uri is not None:
            user = spotify.Link(self._session, uri=uri).as_user()
            if user is None:
                raise ValueError(
                    'Failed to get user from Spotify URI: %r' % uri)
            sp_user = user._sp_user
            add_ref = True

        if add_ref:
            lib.sp_user_add_ref(sp_user)
        self._sp_user = ffi.gc(sp_user, lib.sp_user_release)

    def __repr__(self):
        return 'User(%r)' % self.link.uri

    @property
    @serialized
    def canonical_name(self):
        """The user's canonical username."""
        return utils.to_unicode(lib.sp_user_canonical_name(self._sp_user))

    @property
    @serialized
    def display_name(self):
        """The user's displayable username."""
        return utils.to_unicode(lib.sp_user_display_name(self._sp_user))

    @property
    def is_loaded(self):
        """Whether the user's data is loaded yet."""
        return bool(lib.sp_user_is_loaded(self._sp_user))

    def load(self, timeout=None):
        """Block until the user's data is loaded.

        After ``timeout`` seconds with no results :exc:`~spotify.Timeout` is
        raised. If ``timeout`` is :class:`None` the default timeout is used.

        The method returns ``self`` to allow for chaining of calls.
        """
        return utils.load(self._session, self, timeout=timeout)

    @property
    def link(self):
        """A :class:`Link` to the user."""
        return spotify.Link(
            self._session,
            sp_link=lib.sp_link_create_from_user(self._sp_user), add_ref=False)

    @property
    def starred(self):
        """The :class:`Playlist` of tracks starred by the user."""
        return self._session.get_starred(self.canonical_name)

    @property
    def published_playlists(self):
        """The :class:`PlaylistContainer` of playlists published by the
        user."""
        return self._session.get_published_playlists(self.canonical_name)

########NEW FILE########
__FILENAME__ = utils
from __future__ import unicode_literals

import collections
import functools
import pprint
import sys
import time

import spotify
from spotify import ffi, lib, serialized


PY2 = sys.version_info[0] == 2

if PY2:  # pragma: no branch
    string_types = (basestring,)  # noqa
    text_type = unicode  # noqa
    binary_type = str
else:
    string_types = (str,)
    text_type = str
    binary_type = bytes


class EventEmitter(object):
    """Mixin for adding event emitter functionality to a class."""

    def __init__(self):
        self._listeners = collections.defaultdict(list)

    @serialized
    def on(self, event, listener, *user_args):
        """Register a ``listener`` to be called on ``event``.

        The listener will be called with any extra arguments passed to
        :meth:`emit` first, and then the extra arguments passed to :meth:`on`
        last.

        If the listener function returns :class:`False`, it is removed and will
        not be called the next time the ``event`` is emitted.
        """
        self._listeners[event].append(
            _Listener(callback=listener, user_args=user_args))

    @serialized
    def off(self, event=None, listener=None):
        """Remove a ``listener`` that was to be called on ``event``.

        If ``listener`` is :class:`None`, all listeners for the given ``event``
        will be removed.

        If ``event`` is :class:`None`, all listeners for all events on this
        object will be removed.
        """
        if event is None:
            events = self._listeners.keys()
        else:
            events = [event]
        for event in events:
            if listener is None:
                self._listeners[event] = []
            else:
                self._listeners[event] = [
                    l for l in self._listeners[event]
                    if l.callback != listener]

    def emit(self, event, *event_args):
        """Call the registered listeners for ``event``.

        The listeners will be called with any extra arguments passed to
        :meth:`emit` first, and then the extra arguments passed to :meth:`on`
        """
        listeners = self._listeners[event][:]
        for listener in listeners:
            args = list(event_args) + list(listener.user_args)
            result = listener.callback(*args)
            if result is False:
                self.off(event, listener.callback)

    def num_listeners(self, event=None):
        """Return the number of listeners for ``event``.

        Return the total number of listeners for all events on this object if
        ``event`` is :class:`None`.
        """
        if event is not None:
            return len(self._listeners[event])
        else:
            return sum(len(l) for l in self._listeners.values())

    def call(self, event, *event_args):
        """Call the single registered listener for ``event``.

        The listener will be called with any extra arguments passed to
        :meth:`call` first, and then the extra arguments passed to :meth:`on`

        Raises :exc:`AssertionError` if there is none or multiple listeners for
        ``event``. Returns the listener's return value on success.
        """
        # XXX It would be a lot better for debugging if this error was raised
        # when registering the second listener instead of when the event is
        # emitted.
        assert self.num_listeners(event) == 1, (
            'Expected exactly 1 event listener, found %d listeners' %
            self.num_listeners(event))
        listener = self._listeners[event][0]
        args = list(event_args) + list(listener.user_args)
        return listener.callback(*args)


class _Listener(collections.namedtuple(
        'Listener', ['callback', 'user_args'])):
    """An listener of events from an :class:`EventEmitter`"""


class IntEnum(int):
    """An enum type for values mapping to integers.

    Tries to stay as close as possible to the enum type specified in
    :pep:`435` and introduced in Python 3.4.
    """

    def __new__(cls, value):
        if not hasattr(cls, '_values'):
            cls._values = {}
        if value not in cls._values:
            cls._values[value] = int.__new__(cls, value)
        return cls._values[value]

    def __repr__(self):
        if hasattr(self, '_name'):
            return '<%s.%s: %d>' % (self.__class__.__name__, self._name, self)
        else:
            return '<Unknown %s: %d>' % (self.__class__.__name__, self)

    @classmethod
    def add(cls, name, value):
        """Add a name-value pair to the enumeration."""
        attr = cls(value)
        attr._name = name
        setattr(cls, name, attr)


def make_enum(lib_prefix, enum_prefix=''):
    """Class decorator for automatically adding enum values.

    The values are read directly from the :attr:`spotify.lib` CFFI wrapper
    around libspotify. All values starting with ``lib_prefix`` are added. The
    ``lib_prefix`` is stripped from the name. Optionally, ``enum_prefix`` can
    be specified to add a prefix to all the names.
    """

    def wrapper(cls):
        for attr in dir(lib):
            if attr.startswith(lib_prefix):
                name = attr.replace(lib_prefix, enum_prefix)
                cls.add(name, getattr(lib, attr))
        return cls
    return wrapper


def get_with_fixed_buffer(buffer_length, func, *args):
    """Get a unicode string from a C function that takes a fixed-size buffer.

    The C function ``func`` is called with any arguments given in ``args``, a
    buffer of the given ``buffer_length``, and ``buffer_length``.

    Returns the buffer's value decoded from UTF-8 to a unicode string.
    """
    func = functools.partial(func, *args)
    buffer_ = ffi.new('char[]', buffer_length)
    func(buffer_, buffer_length)
    return to_unicode(buffer_)


def get_with_growing_buffer(func, *args):
    """Get a unicode string from a C function that returns the buffer size
    needed to return the full string.

    The C function ``func`` is called with any arguments given in ``args``, a
    buffer of fixed size, and the buffer size. If the C function returns a
    size that is larger than the buffer already filled, the C function is
    called again with a buffer large enough to get the full string from the C
    function.

    Returns the buffer's value decoded from UTF-8 to a unicode string.
    """
    func = functools.partial(func, *args)
    actual_length = 10
    buffer_length = actual_length
    while actual_length >= buffer_length:
        buffer_length = actual_length + 1
        buffer_ = ffi.new('char[]', buffer_length)
        actual_length = func(buffer_, buffer_length)
    if actual_length == -1:
        return None
    return to_unicode(buffer_)


def _check_error(obj):
    error_type = getattr(obj, 'error', spotify.ErrorType.OK)
    spotify.Error.maybe_raise(
        error_type, ignores=[spotify.ErrorType.IS_LOADING])


def load(session, obj, timeout=None):
    """Block until the object's data is loaded.

    The ``obj`` must at least have the :attr:`is_loaded` attribute. If it also
    has an :meth:`error` method, it will be checked for errors to raise.

    After ``timeout`` seconds with no results :exc:`~spotify.Timeout` is
    raised.

    If unspecified, the ``timeout`` defaults to 10s. Any timeout is better than
    no timeout, since no timeout would cause programs to potentially hang
    forever without any information to help debug the issue.

    The method returns ``self`` to allow for chaining of calls.
    """
    _check_error(obj)
    if obj.is_loaded:
        return obj

    if session.connection.state is not spotify.ConnectionState.LOGGED_IN:
        raise RuntimeError(
            'Session must be logged in and online to load objects: %r'
            % session.connection.state)

    if timeout is None:
        timeout = 10
    deadline = time.time() + timeout

    while not obj.is_loaded:
        session.process_events()
        _check_error(obj)
        if obj.is_loaded:
            return obj
        if time.time() > deadline:
            raise spotify.Timeout(timeout)

        # Instead of sleeping for a very short time and making a tight loop
        # here, one might be tempted to sleep for the time returned by the
        # session.process_events() call above. If no event loop is running,
        # that could lead to very long waits (up to a minute or so) since no
        # one is doing anything on "notify_main_thread" session callbacks,
        # which is intended to interrupt the sleep interval prescribed by
        # session.process_events(). Thus, it is better to make this loop tight.
        time.sleep(0.001)

    _check_error(obj)
    return obj


class Sequence(collections.Sequence):
    """Helper class for making sequences from a length and getitem function.

    The ``sp_obj`` is assumed to already have gotten an extra reference through
    ``sp_*_add_ref`` and to be automatically released through ``sp_*_release``
    when the ``sp_obj`` object is GC-ed.
    """

    def __init__(
            self, sp_obj, add_ref_func, release_func, len_func, getitem_func):

        add_ref_func(sp_obj)
        self._sp_obj = ffi.gc(sp_obj, release_func)
        self._len_func = len_func
        self._getitem_func = getitem_func

    def __len__(self):
        return self._len_func(self._sp_obj)

    def __getitem__(self, key):
        if isinstance(key, slice):
            return list(self).__getitem__(key)
        if not isinstance(key, int):
            raise TypeError(
                'list indices must be int or slice, not %s' %
                key.__class__.__name__)
        if key < 0:
            key += self.__len__()
        if not 0 <= key < self.__len__():
            raise IndexError('list index out of range')
        return self._getitem_func(self._sp_obj, key)

    def __repr__(self):
        return '%s(%s)' % (
            self.__class__.__name__, pprint.pformat(list(self)))


def to_bytes(value):
    """Converts bytes, unicode, and C char arrays to bytes.

    Unicode strings are encoded to UTF-8.
    """
    if isinstance(value, text_type):
        return value.encode('utf-8')
    elif isinstance(value, ffi.CData):
        return ffi.string(value)
    elif isinstance(value, binary_type):
        return value
    else:
        raise ValueError('Value must be text, bytes, or char[]')


def to_bytes_or_none(value):
    """Converts C char arrays to bytes and C NULL values to None."""
    if value == ffi.NULL:
        return None
    elif isinstance(value, ffi.CData):
        return ffi.string(value)
    else:
        raise ValueError('Value must be char[] or NULL')


def to_unicode(value):
    """Converts bytes, unicode, and C char arrays to unicode strings.

    Bytes and C char arrays are decoded from UTF-8.
    """
    if isinstance(value, ffi.CData):
        return ffi.string(value).decode('utf-8')
    elif isinstance(value, binary_type):
        return value.decode('utf-8')
    elif isinstance(value, text_type):
        return value
    else:
        raise ValueError('Value must be text, bytes, or char[]')


def to_unicode_or_none(value):
    """Converts C char arrays to unicode and C NULL values to None.

    C char arrays are decoded from UTF-8.
    """
    if value == ffi.NULL:
        return None
    elif isinstance(value, ffi.CData):
        return ffi.string(value).decode('utf-8')
    else:
        raise ValueError('Value must be char[] or NULL')


def to_char(value):
    """Converts bytes, unicode, and C char arrays to C char arrays.  """
    return ffi.new('char[]', to_bytes(value))


def to_char_or_null(value):
    """Converts bytes, unicode, and C char arrays to C char arrays, and
    :class:`None` to C NULL values.
    """
    if value is None:
        return ffi.NULL
    else:
        return to_char(value)


def to_country(code):
    """Converts a numeric libspotify country code to an ISO 3166-1 two-letter
    country code in a unicode string."""
    return to_unicode(chr(code >> 8) + chr(code & 0xff))


def to_country_code(country):
    """Converts an ISO 3166-1 two-letter country code in a unicode string to a
    numeric libspotify country code.
    """
    country = to_unicode(country)
    if len(country) != 2:
        raise ValueError('Must be exactly two chars')
    first, second = (ord(char) for char in country)
    if (not (ord('A') <= first <= ord('Z')) or
            not (ord('A') <= second <= ord('Z'))):
        raise ValueError('Chars must be in range A-Z')
    return first << 8 | second

########NEW FILE########
__FILENAME__ = version
from __future__ import unicode_literals

from spotify import lib, utils


def get_libspotify_api_version():
    """Get the API compatibility level of the wrapped libspotify library.

    >>> import spotify
    >>> spotify.get_libspotify_api_version()
    12
    """
    return lib.SPOTIFY_API_VERSION


def get_libspotify_build_id():
    """Get the build ID of the wrapped libspotify library.

    >>> import spotify
    >>> spotify.get_libspotify_build_id()
    u'12.1.51.g86c92b43 Release Linux-x86_64 '
    """
    return utils.to_unicode(lib.sp_build_id())

########NEW FILE########
__FILENAME__ = tasks
import sys

from invoke import run, task


@task
def docs(watch=False, warn=False):
    if watch:
        return watcher(docs)
    run('make -C docs/ html', warn=warn)


@task
def test(coverage=False, watch=False, warn=False):
    if watch:
        return watcher(test, coverage=coverage)
    cmd = 'nosetests'
    if coverage:
        cmd += (
            ' --with-coverage --cover-package=spotify'
            ' --cover-branches --cover-html')
    run(cmd, pty=True, warn=warn)


@task
def preprocess_header():
    run(
        'cpp -nostdinc spotify/api.h | egrep -v "(^#)|(^$)" '
        '> spotify/api.processed.h || true')


@task
def update_authors():
    # Keep authors in the order of appearance and use awk to filter out dupes
    run("git log --format='- %aN <%aE>' --reverse | awk '!x[$0]++' > AUTHORS")


@task
def update_sp_constants():
    import spotify
    constants = [
        '%s,%s\n' % (attr, getattr(spotify.lib, attr))
        for attr in dir(spotify.lib)
        if attr.startswith('SP_')]
    with open('docs/sp-constants.csv', 'w+') as fh:
        fh.writelines(constants)


def watcher(task, *args, **kwargs):
    while True:
        run('clear')
        kwargs['warn'] = True
        task(*args, **kwargs)
        try:
            run(
                'inotifywait -q -e create -e modify -e delete '
                '--exclude ".*\.(pyc|sw.)" -r docs/ spotify/ tests/')
        except KeyboardInterrupt:
            sys.exit()

########NEW FILE########
__FILENAME__ = bug_122
import logging
import sys
import threading
import time

import spotify


if len(sys.argv) != 3:
    sys.exit('Usage: %s USERNAME PASSWORD' % sys.argv[0])

username, password = sys.argv[1], sys.argv[2]


def login(session, username, password):
    logged_in_event = threading.Event()

    def logged_in_listener(session, error_type):
        logged_in_event.set()

    session.on(spotify.SessionEvent.LOGGED_IN, logged_in_listener)
    session.login(username, password)

    if not logged_in_event.wait(10):
        raise RuntimeError('Login timed out')

    while session.connection.state != spotify.ConnectionState.LOGGED_IN:
        time.sleep(0.1)


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

session = spotify.Session()
loop = spotify.EventLoop(session)
loop.start()

login(session, username, password)

logger.debug('Getting playlist')
pl = session.get_playlist(
    'spotify:user:durden20:playlist:1chOHrXPCFcShCwB357MFX')
logger.debug('Got playlist %r %r', pl, pl._sp_playlist)
logger.debug('Loading playlist %r %r', pl, pl._sp_playlist)
pl.load()
logger.debug('Loaded playlist %r %r', pl, pl._sp_playlist)

print pl
print pl.tracks

########NEW FILE########
__FILENAME__ = bug_123
from __future__ import print_function

import argparse
import json
import logging
import sys
import threading
import time

import spotify


logger = logging.getLogger(__name__)


def make_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-u', '--username', action='store', required=True,
        help='Spotify username')
    parser.add_argument(
        '-p', '--password', action='store', required=True,
        help='Spotify password')
    parser.add_argument(
        '-v', '--verbose', action='store_true', help='Turn on debug logging')
    subparsers = parser.add_subparsers(
        dest='command', help='sub-command --help')

    subparsers.add_parser('info', help='Get account info')

    create_playlist_parser = subparsers.add_parser(
        'create-playlist', help='Create a new playlist')
    create_playlist_parser.add_argument(
        'name', action='store', help='Name of new playlist')

    add_track_parser = subparsers.add_parser(
        'add-track', help='Add track to playlist')
    add_track_parser.add_argument(
        'playlist', action='store', help='URI of playlist')
    add_track_parser.add_argument(
        'track', action='store', help='URI of track')

    return parser


def login(session, username, password):
    logged_in_event = threading.Event()

    def logged_in_listener(session, error_type):
        if error_type != spotify.ErrorType.OK:
            logger.error('Login failed: %r', error_type)
        logged_in_event.set()

    session.on(spotify.SessionEvent.LOGGED_IN, logged_in_listener)
    session.login(username, password)

    if not logged_in_event.wait(10):
        raise RuntimeError('Login timed out')
    logger.debug('Logged in as %r', session.user_name)

    while session.connection.state != spotify.ConnectionState.LOGGED_IN:
        logger.debug('Waiting for connection')
        time.sleep(0.1)


def logout(session):
    logged_out_event = threading.Event()

    def logged_out_listener(session):
        logged_out_event.set()

    session.on(spotify.SessionEvent.LOGGED_OUT, logged_out_listener)
    session.logout()

    if not logged_out_event.wait(10):
        raise RuntimeError('Logout timed out')


def create_playlist(session, playlist_name):
    playlist = session.playlist_container.add_new_playlist(playlist_name)

    return (playlist.name, playlist.link.uri)


def add_track(session, playlist_uri, track_uri):
    playlist = session.get_playlist(playlist_uri).load()
    track = session.get_track(track_uri).load()

    playlist.add_tracks(track)

    return playlist.link.uri, track.link.uri


def main(args):
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)

    session = spotify.Session()
    loop = spotify.EventLoop(session)
    loop.start()

    login(session, args.username, args.password)

    try:
        if args.command == 'info':
            session.playlist_container.load()
            result = {
                'success': True,
                'action': args.command,
                'response': {
                    'user_name': session.user_name,
                    'num_playlists': len(session.playlist_container),
                    'num_starred': len(session.starred.tracks),
                },
            }
        elif args.command == 'create-playlist':
            name, uri = create_playlist(session, args.name)
            result = {
                'success': True,
                'action': args.command,
                'response': {
                    'playlist_name': name,
                    'playlist_uri': uri,
                },
            }
        elif args.command == 'add-track':
            playlist_uri, track_uri = add_track(
                session, args.playlist, args.track)
            result = {
                'success': True,
                'action': args.command,
                'response': {
                    'playlist_uri': playlist_uri,
                    'track_uri': track_uri,
                },
            }
    except spotify.Error as error:
        logger.exception('%s failed', args.command)
        result = {
            'success': False,
            'action': args.command,
            'error': str(error),
        }

    # Proper logout ensures that all data is persisted properly
    logout(session)

    return result


if __name__ == '__main__':
    parser = make_parser()
    args = parser.parse_args()
    result = main(args)
    print(json.dumps(result, indent=2))
    sys.exit(not result['success'])

########NEW FILE########
__FILENAME__ = failing_link_to_playlist
# TODO This example should work, but fails to get the URIs of the playlists.

from __future__ import print_function

import logging
import time

import spotify

logging.basicConfig(level=logging.INFO)

# Assuming a spotify_appkey.key in the current dir:
session = spotify.Session()

# Assuming a previous login with remember_me=True and a proper logout:
session.relogin()

while session.connection.state != spotify.ConnectionState.LOGGED_IN:
    session.process_events()

user = session.get_user('spotify:user:p3.no').load()
user.published_playlists.load()

time.sleep(10)
session.process_events()

print('%d playlists found' % len(user.published_playlists))

for playlist in user.published_playlists:
    playlist.load()
    print('Loaded', playlist)

print(user.published_playlists)

session.logout()
session.process_events()

########NEW FILE########
__FILENAME__ = test_album
from __future__ import unicode_literals

import unittest

import spotify
from spotify import utils
import tests
from tests import mock


@mock.patch('spotify.album.lib', spec=spotify.lib)
class AlbumTest(unittest.TestCase):

    def setUp(self):
        self.session = tests.create_session_mock()

    def test_create_without_uri_or_sp_album_fails(self, lib_mock):
        with self.assertRaises(AssertionError):
            spotify.Album(self.session)

    @mock.patch('spotify.Link', spec=spotify.Link)
    def test_create_from_uri(self, link_mock, lib_mock):
        sp_album = spotify.ffi.cast('sp_album *', 42)
        link_instance_mock = link_mock.return_value
        link_instance_mock.as_album.return_value = spotify.Album(
            self.session, sp_album=sp_album)
        uri = 'spotify:album:foo'

        result = spotify.Album(self.session, uri=uri)

        link_mock.assert_called_with(self.session, uri=uri)
        link_instance_mock.as_album.assert_called_with()
        lib_mock.sp_album_add_ref.assert_called_with(sp_album)
        self.assertEqual(result._sp_album, sp_album)

    @mock.patch('spotify.Link', spec=spotify.Link)
    def test_create_from_uri_fail_raises_error(self, link_mock, lib_mock):
        link_instance_mock = link_mock.return_value
        link_instance_mock.as_album.return_value = None
        uri = 'spotify:album:foo'

        with self.assertRaises(ValueError):
            spotify.Album(self.session, uri=uri)

    def test_adds_ref_to_sp_album_when_created(self, lib_mock):
        sp_album = spotify.ffi.cast('sp_album *', 42)

        spotify.Album(self.session, sp_album=sp_album)

        lib_mock.sp_album_add_ref.assert_called_with(sp_album)

    def test_releases_sp_album_when_album_dies(self, lib_mock):
        sp_album = spotify.ffi.cast('sp_album *', 42)

        album = spotify.Album(self.session, sp_album=sp_album)
        album = None  # noqa
        tests.gc_collect()

        lib_mock.sp_album_release.assert_called_with(sp_album)

    @mock.patch('spotify.Link', spec=spotify.Link)
    def test_repr(self, link_mock, lib_mock):
        link_instance_mock = link_mock.return_value
        link_instance_mock.uri = 'foo'
        sp_album = spotify.ffi.cast('sp_album *', 42)
        album = spotify.Album(self.session, sp_album=sp_album)

        result = repr(album)

        self.assertEqual(result, 'Album(%r)' % 'foo')

    def test_eq(self, lib_mock):
        sp_album = spotify.ffi.cast('sp_album *', 42)
        album1 = spotify.Album(self.session, sp_album=sp_album)
        album2 = spotify.Album(self.session, sp_album=sp_album)

        self.assertTrue(album1 == album2)
        self.assertFalse(album1 == 'foo')

    def test_ne(self, lib_mock):
        sp_album = spotify.ffi.cast('sp_album *', 42)
        album1 = spotify.Album(self.session, sp_album=sp_album)
        album2 = spotify.Album(self.session, sp_album=sp_album)

        self.assertFalse(album1 != album2)

    def test_hash(self, lib_mock):
        sp_album = spotify.ffi.cast('sp_album *', 42)
        album1 = spotify.Album(self.session, sp_album=sp_album)
        album2 = spotify.Album(self.session, sp_album=sp_album)

        self.assertEqual(hash(album1), hash(album2))

    def test_is_loaded(self, lib_mock):
        lib_mock.sp_album_is_loaded.return_value = 1
        sp_album = spotify.ffi.cast('sp_album *', 42)
        album = spotify.Album(self.session, sp_album=sp_album)

        result = album.is_loaded

        lib_mock.sp_album_is_loaded.assert_called_once_with(sp_album)
        self.assertTrue(result)

    @mock.patch('spotify.utils.load')
    def test_load(self, load_mock, lib_mock):
        sp_album = spotify.ffi.cast('sp_album *', 42)
        album = spotify.Album(self.session, sp_album=sp_album)

        album.load(10)

        load_mock.assert_called_with(self.session, album, timeout=10)

    def test_is_available(self, lib_mock):
        lib_mock.sp_album_is_available.return_value = 1
        sp_album = spotify.ffi.cast('sp_album *', 42)
        album = spotify.Album(self.session, sp_album=sp_album)

        result = album.is_available

        lib_mock.sp_album_is_available.assert_called_once_with(sp_album)
        self.assertTrue(result)

    def test_is_available_is_none_if_unloaded(self, lib_mock):
        lib_mock.sp_album_is_loaded.return_value = 0
        sp_album = spotify.ffi.cast('sp_album *', 42)
        album = spotify.Album(self.session, sp_album=sp_album)

        result = album.is_available

        lib_mock.sp_album_is_loaded.assert_called_once_with(sp_album)
        self.assertIsNone(result)

    @mock.patch('spotify.artist.lib', spec=spotify.lib)
    def test_artist(self, artist_lib_mock, lib_mock):
        sp_artist = spotify.ffi.cast('sp_artist *', 43)
        lib_mock.sp_album_artist.return_value = sp_artist
        sp_album = spotify.ffi.cast('sp_album *', 42)
        album = spotify.Album(self.session, sp_album=sp_album)

        result = album.artist

        lib_mock.sp_album_artist.assert_called_with(sp_album)
        self.assertEqual(artist_lib_mock.sp_artist_add_ref.call_count, 1)
        self.assertIsInstance(result, spotify.Artist)
        self.assertEqual(result._sp_artist, sp_artist)

    @mock.patch('spotify.artist.lib', spec=spotify.lib)
    def test_artist_if_unloaded(self, artist_lib_mock, lib_mock):
        lib_mock.sp_album_artist.return_value = spotify.ffi.NULL
        sp_album = spotify.ffi.cast('sp_album *', 42)
        album = spotify.Album(self.session, sp_album=sp_album)

        result = album.artist

        lib_mock.sp_album_artist.assert_called_with(sp_album)
        self.assertIsNone(result)

    @mock.patch('spotify.Image', spec=spotify.Image)
    def test_cover(self, image_mock, lib_mock):
        sp_album = spotify.ffi.cast('sp_album *', 42)
        album = spotify.Album(self.session, sp_album=sp_album)
        sp_image_id = spotify.ffi.new('char[]', b'cover-id')
        lib_mock.sp_album_cover.return_value = sp_image_id
        sp_image = spotify.ffi.cast('sp_image *', 43)
        lib_mock.sp_image_create.return_value = sp_image
        image_mock.return_value = mock.sentinel.image
        image_size = spotify.ImageSize.SMALL
        callback = mock.Mock()

        result = album.cover(image_size, callback=callback)

        self.assertIs(result, mock.sentinel.image)
        lib_mock.sp_album_cover.assert_called_with(
            sp_album, int(image_size))
        lib_mock.sp_image_create.assert_called_with(
            self.session._sp_session, sp_image_id)

        # Since we *created* the sp_image, we already have a refcount of 1 and
        # shouldn't increase the refcount when wrapping this sp_image in an
        # Image object
        image_mock.assert_called_with(
            self.session, sp_image=sp_image, add_ref=False, callback=callback)

    @mock.patch('spotify.Image', spec=spotify.Image)
    def test_cover_defaults_to_normal_size(self, image_mock, lib_mock):
        sp_image_id = spotify.ffi.new('char[]', b'cover-id')
        lib_mock.sp_album_cover.return_value = sp_image_id
        sp_image = spotify.ffi.cast('sp_image *', 43)
        lib_mock.sp_image_create.return_value = sp_image
        sp_album = spotify.ffi.cast('sp_album *', 42)
        album = spotify.Album(self.session, sp_album=sp_album)

        album.cover()

        lib_mock.sp_album_cover.assert_called_with(
            sp_album, int(spotify.ImageSize.NORMAL))

    def test_cover_is_none_if_null(self, lib_mock):
        lib_mock.sp_album_cover.return_value = spotify.ffi.NULL
        sp_album = spotify.ffi.cast('sp_album *', 42)
        album = spotify.Album(self.session, sp_album=sp_album)

        result = album.cover()

        lib_mock.sp_album_cover.assert_called_with(
            sp_album, int(spotify.ImageSize.NORMAL))
        self.assertIsNone(result)

    @mock.patch('spotify.Link', spec=spotify.Link)
    def test_cover_link_creates_link_to_cover(self, link_mock, lib_mock):
        sp_album = spotify.ffi.cast('sp_album *', 42)
        album = spotify.Album(self.session, sp_album=sp_album)
        sp_link = spotify.ffi.cast('sp_link *', 43)
        lib_mock.sp_link_create_from_album_cover.return_value = sp_link
        link_mock.return_value = mock.sentinel.link
        image_size = spotify.ImageSize.SMALL

        result = album.cover_link(image_size)

        lib_mock.sp_link_create_from_album_cover.assert_called_once_with(
            sp_album, int(image_size))
        link_mock.assert_called_once_with(
            self.session, sp_link=sp_link, add_ref=False)
        self.assertEqual(result, mock.sentinel.link)

    @mock.patch('spotify.Link', spec=spotify.Link)
    def test_cover_link_defaults_to_normal_size(self, link_mock, lib_mock):
        sp_album = spotify.ffi.cast('sp_album *', 42)
        album = spotify.Album(self.session, sp_album=sp_album)
        sp_link = spotify.ffi.cast('sp_link *', 43)
        lib_mock.sp_link_create_from_album_cover.return_value = sp_link
        link_mock.return_value = mock.sentinel.link

        album.cover_link()

        lib_mock.sp_link_create_from_album_cover.assert_called_once_with(
            sp_album, int(spotify.ImageSize.NORMAL))

    def test_name(self, lib_mock):
        lib_mock.sp_album_name.return_value = spotify.ffi.new(
            'char[]', b'Foo Bar Baz')
        sp_album = spotify.ffi.cast('sp_album *', 42)
        album = spotify.Album(self.session, sp_album=sp_album)

        result = album.name

        lib_mock.sp_album_name.assert_called_once_with(sp_album)
        self.assertEqual(result, 'Foo Bar Baz')

    def test_name_is_none_if_unloaded(self, lib_mock):
        lib_mock.sp_album_name.return_value = spotify.ffi.new('char[]', b'')
        sp_album = spotify.ffi.cast('sp_album *', 42)
        album = spotify.Album(self.session, sp_album=sp_album)

        result = album.name

        lib_mock.sp_album_name.assert_called_once_with(sp_album)
        self.assertIsNone(result)

    def test_year(self, lib_mock):
        lib_mock.sp_album_year.return_value = 2013
        sp_album = spotify.ffi.cast('sp_album *', 42)
        album = spotify.Album(self.session, sp_album=sp_album)

        result = album.year

        lib_mock.sp_album_year.assert_called_once_with(sp_album)
        self.assertEqual(result, 2013)

    def test_year_is_none_if_unloaded(self, lib_mock):
        lib_mock.sp_album_is_loaded.return_value = 0
        sp_album = spotify.ffi.cast('sp_album *', 42)
        album = spotify.Album(self.session, sp_album=sp_album)

        result = album.year

        lib_mock.sp_album_is_loaded.assert_called_once_with(sp_album)
        self.assertIsNone(result)

    def test_type(self, lib_mock):
        lib_mock.sp_album_type.return_value = int(spotify.AlbumType.SINGLE)
        sp_album = spotify.ffi.cast('sp_album *', 42)
        album = spotify.Album(self.session, sp_album=sp_album)

        result = album.type

        lib_mock.sp_album_type.assert_called_once_with(sp_album)
        self.assertIs(result, spotify.AlbumType.SINGLE)

    def test_type_is_none_if_unloaded(self, lib_mock):
        lib_mock.sp_album_is_loaded.return_value = 0
        sp_album = spotify.ffi.cast('sp_album *', 42)
        album = spotify.Album(self.session, sp_album=sp_album)

        result = album.type

        lib_mock.sp_album_is_loaded.assert_called_once_with(sp_album)
        self.assertIsNone(result)

    @mock.patch('spotify.Link', spec=spotify.Link)
    def test_link_creates_link_to_album(self, link_mock, lib_mock):
        sp_album = spotify.ffi.cast('sp_album *', 42)
        album = spotify.Album(self.session, sp_album=sp_album)
        sp_link = spotify.ffi.cast('sp_link *', 43)
        lib_mock.sp_link_create_from_album.return_value = sp_link
        link_mock.return_value = mock.sentinel.link

        result = album.link

        link_mock.assert_called_once_with(
            self.session, sp_link=sp_link, add_ref=False)
        self.assertEqual(result, mock.sentinel.link)


@mock.patch('spotify.album.lib', spec=spotify.lib)
class AlbumBrowserTest(unittest.TestCase):

    def setUp(self):
        self.session = tests.create_session_mock()
        spotify._session_instance = self.session

    def tearDown(self):
        spotify._session_instance = None

    def test_create_without_album_or_sp_albumbrowse_fails(self, lib_mock):
        with self.assertRaises(AssertionError):
            spotify.AlbumBrowser(self.session)

    def test_create_from_album(self, lib_mock):
        sp_album = spotify.ffi.cast('sp_album *', 43)
        album = spotify.Album(self.session, sp_album=sp_album)
        sp_albumbrowse = spotify.ffi.cast('sp_albumbrowse *', 42)
        lib_mock.sp_albumbrowse_create.return_value = sp_albumbrowse

        result = album.browse()

        lib_mock.sp_albumbrowse_create.assert_called_with(
            self.session._sp_session, sp_album, mock.ANY, mock.ANY)
        self.assertIsInstance(result, spotify.AlbumBrowser)

        albumbrowse_complete_cb = (
            lib_mock.sp_albumbrowse_create.call_args[0][2])
        userdata = lib_mock.sp_albumbrowse_create.call_args[0][3]
        self.assertFalse(result.loaded_event.is_set())
        albumbrowse_complete_cb(sp_albumbrowse, userdata)
        self.assertTrue(result.loaded_event.is_set())

    def test_create_from_album_with_callback(self, lib_mock):
        sp_album = spotify.ffi.cast('sp_album *', 43)
        album = spotify.Album(self.session, sp_album=sp_album)
        sp_albumbrowse = spotify.ffi.cast('sp_albumbrowse *', 42)
        lib_mock.sp_albumbrowse_create.return_value = sp_albumbrowse
        callback = mock.Mock()

        result = album.browse(callback)

        lib_mock.sp_albumbrowse_create.assert_called_with(
            self.session._sp_session, sp_album, mock.ANY, mock.ANY)
        albumbrowse_complete_cb = (
            lib_mock.sp_albumbrowse_create.call_args[0][2])
        userdata = lib_mock.sp_albumbrowse_create.call_args[0][3]
        albumbrowse_complete_cb(sp_albumbrowse, userdata)

        result.loaded_event.wait(3)
        callback.assert_called_with(result)

    def test_browser_is_gone_before_callback_is_called(self, lib_mock):
        sp_album = spotify.ffi.cast('sp_album *', 43)
        album = spotify.Album(self.session, sp_album=sp_album)
        sp_albumbrowse = spotify.ffi.cast('sp_albumbrowse *', 42)
        lib_mock.sp_albumbrowse_create.return_value = sp_albumbrowse
        callback = mock.Mock()

        result = spotify.AlbumBrowser(
            self.session, album=album, callback=callback)
        loaded_event = result.loaded_event
        result = None  # noqa
        tests.gc_collect()

        # The mock keeps the handle/userdata alive, thus this test doesn't
        # really test that session._callback_handles keeps the handle alive.
        albumbrowse_complete_cb = (
            lib_mock.sp_albumbrowse_create.call_args[0][2])
        userdata = lib_mock.sp_albumbrowse_create.call_args[0][3]
        albumbrowse_complete_cb(sp_albumbrowse, userdata)

        loaded_event.wait(3)
        self.assertEqual(callback.call_count, 1)
        self.assertEqual(
            callback.call_args[0][0]._sp_albumbrowse, sp_albumbrowse)

    def test_adds_ref_to_sp_albumbrowse_when_created(self, lib_mock):
        session = tests.create_session_mock()
        sp_albumbrowse = spotify.ffi.cast('sp_albumbrowse *', 42)

        spotify.AlbumBrowser(session, sp_albumbrowse=sp_albumbrowse)

        lib_mock.sp_albumbrowse_add_ref.assert_called_with(sp_albumbrowse)

    def test_releases_sp_albumbrowse_when_album_dies(self, lib_mock):
        sp_albumbrowse = spotify.ffi.cast('sp_albumbrowse *', 42)

        browser = spotify.AlbumBrowser(
            self.session, sp_albumbrowse=sp_albumbrowse)
        browser = None  # noqa
        tests.gc_collect()

        lib_mock.sp_albumbrowse_release.assert_called_with(sp_albumbrowse)

    @mock.patch('spotify.Link', spec=spotify.Link)
    def test_repr(self, link_mock, lib_mock):
        sp_albumbrowse = spotify.ffi.cast('sp_albumbrowse *', 42)
        browser = spotify.AlbumBrowser(
            self.session, sp_albumbrowse=sp_albumbrowse)
        lib_mock.sp_albumbrowse_is_loaded.return_value = 1
        sp_album = spotify.ffi.cast('sp_album *', 43)
        lib_mock.sp_albumbrowse_album.return_value = sp_album
        link_instance_mock = link_mock.return_value
        link_instance_mock.uri = 'foo'

        result = repr(browser)

        self.assertEqual(result, 'AlbumBrowser(%r)' % 'foo')

    def test_repr_if_unloaded(self, lib_mock):
        sp_albumbrowse = spotify.ffi.cast('sp_albumbrowse *', 42)
        browser = spotify.AlbumBrowser(
            self.session, sp_albumbrowse=sp_albumbrowse)
        lib_mock.sp_albumbrowse_is_loaded.return_value = 0

        result = repr(browser)

        self.assertEqual(result, 'AlbumBrowser(<not loaded>)')

    def test_eq(self, lib_mock):
        sp_albumbrowse = spotify.ffi.cast('sp_albumbrowse *', 42)
        browser1 = spotify.AlbumBrowser(
            self.session, sp_albumbrowse=sp_albumbrowse)
        browser2 = spotify.AlbumBrowser(
            self.session, sp_albumbrowse=sp_albumbrowse)

        self.assertTrue(browser1 == browser2)
        self.assertFalse(browser1 == 'foo')

    def test_ne(self, lib_mock):
        sp_albumbrowse = spotify.ffi.cast('sp_albumbrowse *', 42)
        browser1 = spotify.AlbumBrowser(
            self.session, sp_albumbrowse=sp_albumbrowse)
        browser2 = spotify.AlbumBrowser(
            self.session, sp_albumbrowse=sp_albumbrowse)

        self.assertFalse(browser1 != browser2)

    def test_hash(self, lib_mock):
        sp_albumbrowse = spotify.ffi.cast('sp_albumbrowse *', 42)
        browser1 = spotify.AlbumBrowser(
            self.session, sp_albumbrowse=sp_albumbrowse)
        browser2 = spotify.AlbumBrowser(
            self.session, sp_albumbrowse=sp_albumbrowse)

        self.assertEqual(hash(browser1), hash(browser2))

    def test_is_loaded(self, lib_mock):
        lib_mock.sp_albumbrowse_is_loaded.return_value = 1
        sp_albumbrowse = spotify.ffi.cast('sp_albumbrowse *', 42)
        browser = spotify.AlbumBrowser(
            self.session, sp_albumbrowse=sp_albumbrowse)

        result = browser.is_loaded

        lib_mock.sp_albumbrowse_is_loaded.assert_called_once_with(
            sp_albumbrowse)
        self.assertTrue(result)

    @mock.patch('spotify.utils.load')
    def test_load(self, load_mock, lib_mock):
        sp_albumbrowse = spotify.ffi.cast('sp_albumbrowse *', 42)
        browser = spotify.AlbumBrowser(
            self.session, sp_albumbrowse=sp_albumbrowse)

        browser.load(10)

        load_mock.assert_called_with(self.session, browser, timeout=10)

    def test_error(self, lib_mock):
        lib_mock.sp_albumbrowse_error.return_value = int(
            spotify.ErrorType.OTHER_PERMANENT)
        sp_albumbrowse = spotify.ffi.cast('sp_albumbrowse *', 42)
        browser = spotify.AlbumBrowser(
            self.session, sp_albumbrowse=sp_albumbrowse)

        result = browser.error

        lib_mock.sp_albumbrowse_error.assert_called_once_with(sp_albumbrowse)
        self.assertIs(result, spotify.ErrorType.OTHER_PERMANENT)

    def test_backend_request_duration(self, lib_mock):
        lib_mock.sp_albumbrowse_backend_request_duration.return_value = 137
        sp_albumbrowse = spotify.ffi.cast('sp_albumbrowse *', 42)
        browser = spotify.AlbumBrowser(
            self.session, sp_albumbrowse=sp_albumbrowse)

        result = browser.backend_request_duration

        lib_mock.sp_albumbrowse_backend_request_duration.assert_called_with(
            sp_albumbrowse)
        self.assertEqual(result, 137)

    def test_backend_request_duration_when_not_loaded(self, lib_mock):
        lib_mock.sp_albumbrowse_is_loaded.return_value = 0
        sp_albumbrowse = spotify.ffi.cast('sp_albumbrowse *', 42)
        browser = spotify.AlbumBrowser(
            self.session, sp_albumbrowse=sp_albumbrowse)

        result = browser.backend_request_duration

        lib_mock.sp_albumbrowse_is_loaded.assert_called_with(sp_albumbrowse)
        self.assertEqual(
            lib_mock.sp_albumbrowse_backend_request_duration.call_count, 0)
        self.assertIsNone(result)

    def test_album(self, lib_mock):
        sp_albumbrowse = spotify.ffi.cast('sp_albumbrowse *', 42)
        browser = spotify.AlbumBrowser(
            self.session, sp_albumbrowse=sp_albumbrowse)
        sp_album = spotify.ffi.cast('sp_album *', 43)
        lib_mock.sp_albumbrowse_album.return_value = sp_album

        result = browser.album

        self.assertIsInstance(result, spotify.Album)
        self.assertEqual(result._sp_album, sp_album)

    def test_album_when_not_loaded(self, lib_mock):
        sp_albumbrowse = spotify.ffi.cast('sp_albumbrowse *', 42)
        browser = spotify.AlbumBrowser(
            self.session, sp_albumbrowse=sp_albumbrowse)
        lib_mock.sp_albumbrowse_album.return_value = spotify.ffi.NULL

        result = browser.album

        lib_mock.sp_albumbrowse_album.assert_called_with(sp_albumbrowse)
        self.assertIsNone(result)

    @mock.patch('spotify.artist.lib', spec=spotify.lib)
    def test_artist(self, artist_lib_mock, lib_mock):
        sp_albumbrowse = spotify.ffi.cast('sp_albumbrowse *', 42)
        browser = spotify.AlbumBrowser(
            self.session, sp_albumbrowse=sp_albumbrowse)
        sp_artist = spotify.ffi.cast('sp_artist *', 43)
        lib_mock.sp_albumbrowse_artist.return_value = sp_artist

        result = browser.artist

        self.assertIsInstance(result, spotify.Artist)
        self.assertEqual(result._sp_artist, sp_artist)

    def test_artist_when_not_loaded(self, lib_mock):
        sp_albumbrowse = spotify.ffi.cast('sp_albumbrowse *', 42)
        browser = spotify.AlbumBrowser(
            self.session, sp_albumbrowse=sp_albumbrowse)
        lib_mock.sp_albumbrowse_artist.return_value = spotify.ffi.NULL

        result = browser.artist

        lib_mock.sp_albumbrowse_artist.assert_called_with(sp_albumbrowse)
        self.assertIsNone(result)

    def test_copyrights(self, lib_mock):
        copyright = spotify.ffi.new('char[]', b'Apple Records 1973')
        lib_mock.sp_albumbrowse_num_copyrights.return_value = 1
        lib_mock.sp_albumbrowse_copyright.return_value = copyright
        sp_albumbrowse = spotify.ffi.cast('sp_albumbrowse *', 42)
        browser = spotify.AlbumBrowser(
            self.session, sp_albumbrowse=sp_albumbrowse)

        self.assertEqual(lib_mock.sp_albumbrowse_add_ref.call_count, 1)
        result = browser.copyrights
        self.assertEqual(lib_mock.sp_albumbrowse_add_ref.call_count, 2)

        self.assertEqual(len(result), 1)
        lib_mock.sp_albumbrowse_num_copyrights.assert_called_with(
            sp_albumbrowse)

        item = result[0]
        self.assertIsInstance(item, utils.text_type)
        self.assertEqual(item, 'Apple Records 1973')
        self.assertEqual(lib_mock.sp_albumbrowse_copyright.call_count, 1)
        lib_mock.sp_albumbrowse_copyright.assert_called_with(sp_albumbrowse, 0)

    def test_copyrights_if_no_copyrights(self, lib_mock):
        lib_mock.sp_albumbrowse_num_copyrights.return_value = 0
        sp_albumbrowse = spotify.ffi.cast('sp_albumbrowse *', 42)
        browser = spotify.AlbumBrowser(
            self.session, sp_albumbrowse=sp_albumbrowse)

        result = browser.copyrights

        self.assertEqual(len(result), 0)
        lib_mock.sp_albumbrowse_num_copyrights.assert_called_with(
            sp_albumbrowse)
        self.assertEqual(lib_mock.sp_albumbrowse_copyright.call_count, 0)

    def test_copyrights_if_unloaded(self, lib_mock):
        lib_mock.sp_albumbrowse_is_loaded.return_value = 0
        sp_albumbrowse = spotify.ffi.cast('sp_albumbrowse *', 42)
        browser = spotify.AlbumBrowser(
            self.session, sp_albumbrowse=sp_albumbrowse)

        result = browser.copyrights

        lib_mock.sp_albumbrowse_is_loaded.assert_called_with(sp_albumbrowse)
        self.assertEqual(len(result), 0)

    @mock.patch('spotify.track.lib', spec=spotify.lib)
    def test_tracks(self, track_lib_mock, lib_mock):
        sp_track = spotify.ffi.cast('sp_track *', 43)
        lib_mock.sp_albumbrowse_num_tracks.return_value = 1
        lib_mock.sp_albumbrowse_track.return_value = sp_track
        sp_albumbrowse = spotify.ffi.cast('sp_albumbrowse *', 42)
        browser = spotify.AlbumBrowser(
            self.session, sp_albumbrowse=sp_albumbrowse)

        self.assertEqual(lib_mock.sp_albumbrowse_add_ref.call_count, 1)
        result = browser.tracks
        self.assertEqual(lib_mock.sp_albumbrowse_add_ref.call_count, 2)

        self.assertEqual(len(result), 1)
        lib_mock.sp_albumbrowse_num_tracks.assert_called_with(sp_albumbrowse)

        item = result[0]
        self.assertIsInstance(item, spotify.Track)
        self.assertEqual(item._sp_track, sp_track)
        self.assertEqual(lib_mock.sp_albumbrowse_track.call_count, 1)
        lib_mock.sp_albumbrowse_track.assert_called_with(sp_albumbrowse, 0)
        track_lib_mock.sp_track_add_ref.assert_called_with(sp_track)

    def test_tracks_if_no_tracks(self, lib_mock):
        lib_mock.sp_albumbrowse_num_tracks.return_value = 0
        sp_albumbrowse = spotify.ffi.cast('sp_albumbrowse *', 42)
        browser = spotify.AlbumBrowser(
            self.session, sp_albumbrowse=sp_albumbrowse)

        result = browser.tracks

        self.assertEqual(len(result), 0)
        lib_mock.sp_albumbrowse_num_tracks.assert_called_with(sp_albumbrowse)
        self.assertEqual(lib_mock.sp_albumbrowse_track.call_count, 0)

    def test_tracks_if_unloaded(self, lib_mock):
        lib_mock.sp_albumbrowse_is_loaded.return_value = 0
        sp_albumbrowse = spotify.ffi.cast('sp_albumbrowse *', 42)
        browser = spotify.AlbumBrowser(
            self.session, sp_albumbrowse=sp_albumbrowse)

        result = browser.tracks

        lib_mock.sp_albumbrowse_is_loaded.assert_called_with(sp_albumbrowse)
        self.assertEqual(len(result), 0)

    def test_review(self, lib_mock):
        sp_albumbrowse = spotify.ffi.cast('sp_albumbrowse *', 42)
        browser = spotify.AlbumBrowser(
            self.session, sp_albumbrowse=sp_albumbrowse)
        review = spotify.ffi.new('char[]', b'A nice album')
        lib_mock.sp_albumbrowse_review.return_value = review

        result = browser.review

        self.assertIsInstance(result, utils.text_type)
        self.assertEqual(result, 'A nice album')


class AlbumTypeTest(unittest.TestCase):

    def test_has_constants(self):
        self.assertEqual(spotify.AlbumType.ALBUM, 0)
        self.assertEqual(spotify.AlbumType.SINGLE, 1)

########NEW FILE########
__FILENAME__ = test_artist
from __future__ import unicode_literals

import unittest

import spotify
from spotify import utils
import tests
from tests import mock


@mock.patch('spotify.artist.lib', spec=spotify.lib)
class ArtistTest(unittest.TestCase):

    def setUp(self):
        self.session = tests.create_session_mock()

    def test_create_without_uri_or_sp_artist_fails(self, lib_mock):
        with self.assertRaises(AssertionError):
            spotify.Artist(self.session)

    @mock.patch('spotify.Link', spec=spotify.Link)
    def test_create_from_uri(self, link_mock, lib_mock):
        sp_artist = spotify.ffi.cast('sp_artist *', 42)
        link_instance_mock = link_mock.return_value
        link_instance_mock.as_artist.return_value = spotify.Artist(
            self.session, sp_artist=sp_artist)
        lib_mock.sp_link_as_artist.return_value = sp_artist
        uri = 'spotify:artist:foo'

        result = spotify.Artist(self.session, uri=uri)

        link_mock.assert_called_with(self.session, uri=uri)
        link_instance_mock.as_artist.assert_called_with()
        lib_mock.sp_artist_add_ref.assert_called_with(sp_artist)
        self.assertEqual(result._sp_artist, sp_artist)

    @mock.patch('spotify.Link', spec=spotify.Link)
    def test_create_from_uri_fail_raises_error(self, link_mock, lib_mock):
        link_instance_mock = link_mock.return_value
        link_instance_mock.as_artist.return_value = None
        lib_mock.sp_link_as_artist.return_value = spotify.ffi.NULL
        uri = 'spotify:artist:foo'

        with self.assertRaises(ValueError):
            spotify.Artist(self.session, uri=uri)

    def test_adds_ref_to_sp_artist_when_created(self, lib_mock):
        sp_artist = spotify.ffi.cast('sp_artist *', 42)

        spotify.Artist(self.session, sp_artist=sp_artist)

        lib_mock.sp_artist_add_ref.assert_called_with(sp_artist)

    def test_releases_sp_artist_when_artist_dies(self, lib_mock):
        sp_artist = spotify.ffi.cast('sp_artist *', 42)

        artist = spotify.Artist(self.session, sp_artist=sp_artist)
        artist = None  # noqa
        tests.gc_collect()

        lib_mock.sp_artist_release.assert_called_with(sp_artist)

    @mock.patch('spotify.Link', spec=spotify.Link)
    def test_repr(self, link_mock, lib_mock):
        link_instance_mock = link_mock.return_value
        link_instance_mock.uri = 'foo'
        sp_artist = spotify.ffi.cast('sp_artist *', 42)
        artist = spotify.Artist(self.session, sp_artist=sp_artist)

        result = repr(artist)

        self.assertEqual(result, 'Artist(%r)' % 'foo')

    def test_eq(self, lib_mock):
        sp_artist = spotify.ffi.cast('sp_artist *', 42)
        artist1 = spotify.Artist(self.session, sp_artist=sp_artist)
        artist2 = spotify.Artist(self.session, sp_artist=sp_artist)

        self.assertTrue(artist1 == artist2)
        self.assertFalse(artist1 == 'foo')

    def test_ne(self, lib_mock):
        sp_artist = spotify.ffi.cast('sp_artist *', 42)
        artist1 = spotify.Artist(self.session, sp_artist=sp_artist)
        artist2 = spotify.Artist(self.session, sp_artist=sp_artist)

        self.assertFalse(artist1 != artist2)

    def test_hash(self, lib_mock):
        sp_artist = spotify.ffi.cast('sp_artist *', 42)
        artist1 = spotify.Artist(self.session, sp_artist=sp_artist)
        artist2 = spotify.Artist(self.session, sp_artist=sp_artist)

        self.assertEqual(hash(artist1), hash(artist2))

    def test_name(self, lib_mock):
        lib_mock.sp_artist_name.return_value = spotify.ffi.new(
            'char[]', b'Foo Bar Baz')
        sp_artist = spotify.ffi.cast('sp_artist *', 42)
        artist = spotify.Artist(self.session, sp_artist=sp_artist)

        result = artist.name

        lib_mock.sp_artist_name.assert_called_once_with(sp_artist)
        self.assertEqual(result, 'Foo Bar Baz')

    def test_name_is_none_if_unloaded(self, lib_mock):
        lib_mock.sp_artist_name.return_value = spotify.ffi.new('char[]', b'')
        sp_artist = spotify.ffi.cast('sp_artist *', 42)
        artist = spotify.Artist(self.session, sp_artist=sp_artist)

        result = artist.name

        lib_mock.sp_artist_name.assert_called_once_with(sp_artist)
        self.assertIsNone(result)

    def test_is_loaded(self, lib_mock):
        lib_mock.sp_artist_is_loaded.return_value = 1
        sp_artist = spotify.ffi.cast('sp_artist *', 42)
        artist = spotify.Artist(self.session, sp_artist=sp_artist)

        result = artist.is_loaded

        lib_mock.sp_artist_is_loaded.assert_called_once_with(sp_artist)
        self.assertTrue(result)

    @mock.patch('spotify.utils.load')
    def test_load(self, load_mock, lib_mock):
        sp_artist = spotify.ffi.cast('sp_artist *', 42)
        artist = spotify.Artist(self.session, sp_artist=sp_artist)

        artist.load(10)

        load_mock.assert_called_with(self.session, artist, timeout=10)

    @mock.patch('spotify.Image', spec=spotify.Image)
    def test_portrait(self, image_mock, lib_mock):
        sp_artist = spotify.ffi.cast('sp_artist *', 42)
        artist = spotify.Artist(self.session, sp_artist=sp_artist)
        sp_image_id = spotify.ffi.new('char[]', b'portrait-id')
        lib_mock.sp_artist_portrait.return_value = sp_image_id
        sp_image = spotify.ffi.cast('sp_image *', 43)
        lib_mock.sp_image_create.return_value = sp_image
        image_mock.return_value = mock.sentinel.image
        image_size = spotify.ImageSize.SMALL
        callback = mock.Mock()

        result = artist.portrait(image_size, callback=callback)

        self.assertIs(result, mock.sentinel.image)
        lib_mock.sp_artist_portrait.assert_called_with(
            sp_artist, int(image_size))
        lib_mock.sp_image_create.assert_called_with(
            self.session._sp_session, sp_image_id)

        # Since we *created* the sp_image, we already have a refcount of 1 and
        # shouldn't increase the refcount when wrapping this sp_image in an
        # Image object
        image_mock.assert_called_with(
            self.session, sp_image=sp_image, add_ref=False, callback=callback)

    @mock.patch('spotify.Image', spec=spotify.Image)
    def test_portrait_defaults_to_normal_size(self, image_mock, lib_mock):
        sp_image_id = spotify.ffi.new('char[]', b'portrait-id')
        lib_mock.sp_artist_portrait.return_value = sp_image_id
        sp_image = spotify.ffi.cast('sp_image *', 43)
        lib_mock.sp_image_create.return_value = sp_image
        sp_artist = spotify.ffi.cast('sp_artist *', 42)
        artist = spotify.Artist(self.session, sp_artist=sp_artist)

        artist.portrait()

        lib_mock.sp_artist_portrait.assert_called_with(
            sp_artist, int(spotify.ImageSize.NORMAL))

    def test_portrait_is_none_if_null(self, lib_mock):
        lib_mock.sp_artist_portrait.return_value = spotify.ffi.NULL
        sp_artist = spotify.ffi.cast('sp_artist *', 42)
        artist = spotify.Artist(self.session, sp_artist=sp_artist)

        result = artist.portrait()

        lib_mock.sp_artist_portrait.assert_called_with(
            sp_artist, int(spotify.ImageSize.NORMAL))
        self.assertIsNone(result)

    @mock.patch('spotify.Link', spec=spotify.Link)
    def test_portrait_link_creates_link_to_portrait(self, link_mock, lib_mock):
        sp_artist = spotify.ffi.cast('sp_artist *', 42)
        artist = spotify.Artist(self.session, sp_artist=sp_artist)
        sp_link = spotify.ffi.cast('sp_link *', 43)
        lib_mock.sp_link_create_from_artist_portrait.return_value = sp_link
        link_mock.return_value = mock.sentinel.link
        image_size = spotify.ImageSize.SMALL

        result = artist.portrait_link(image_size)

        lib_mock.sp_link_create_from_artist_portrait.assert_called_once_with(
            sp_artist, int(image_size))
        link_mock.assert_called_once_with(
            self.session, sp_link=sp_link, add_ref=False)
        self.assertEqual(result, mock.sentinel.link)

    @mock.patch('spotify.Link', spec=spotify.Link)
    def test_portrait_link_defaults_to_normal_size(self, link_mock, lib_mock):
        sp_artist = spotify.ffi.cast('sp_artist *', 42)
        artist = spotify.Artist(self.session, sp_artist=sp_artist)
        sp_link = spotify.ffi.cast('sp_link *', 43)
        lib_mock.sp_link_create_from_artist_portrait.return_value = sp_link
        link_mock.return_value = mock.sentinel.link

        artist.portrait_link()

        lib_mock.sp_link_create_from_artist_portrait.assert_called_once_with(
            sp_artist, int(spotify.ImageSize.NORMAL))

    @mock.patch('spotify.Link', spec=spotify.Link)
    def test_link_creates_link_to_artist(self, link_mock, lib_mock):
        sp_artist = spotify.ffi.cast('sp_artist *', 42)
        artist = spotify.Artist(self.session, sp_artist=sp_artist)
        sp_link = spotify.ffi.cast('sp_link *', 43)
        lib_mock.sp_link_create_from_artist.return_value = sp_link
        link_mock.return_value = mock.sentinel.link

        result = artist.link

        link_mock.assert_called_once_with(
            self.session, sp_link=sp_link, add_ref=False)
        self.assertEqual(result, mock.sentinel.link)


@mock.patch('spotify.artist.lib', spec=spotify.lib)
class ArtistBrowserTest(unittest.TestCase):

    def setUp(self):
        self.session = tests.create_session_mock()
        spotify._session_instance = self.session

    def tearDown(self):
        spotify._session_instance = None

    def test_create_without_artist_or_sp_artistbrowse_fails(self, lib_mock):
        with self.assertRaises(AssertionError):
            spotify.ArtistBrowser(self.session)

    def test_create_from_artist(self, lib_mock):
        sp_artist = spotify.ffi.cast('sp_artist *', 43)
        artist = spotify.Artist(self.session, sp_artist=sp_artist)
        sp_artistbrowse = spotify.ffi.cast('sp_artistbrowse *', 42)
        lib_mock.sp_artistbrowse_create.return_value = sp_artistbrowse

        result = artist.browse()

        lib_mock.sp_artistbrowse_create.assert_called_with(
            self.session._sp_session, sp_artist,
            int(spotify.ArtistBrowserType.FULL), mock.ANY, mock.ANY)
        self.assertIsInstance(result, spotify.ArtistBrowser)

        artistbrowse_complete_cb = (
            lib_mock.sp_artistbrowse_create.call_args[0][3])
        userdata = lib_mock.sp_artistbrowse_create.call_args[0][4]
        self.assertFalse(result.loaded_event.is_set())
        artistbrowse_complete_cb(sp_artistbrowse, userdata)
        self.assertTrue(result.loaded_event.is_set())

    def test_create_from_artist_with_type_and_callback(self, lib_mock):
        sp_artist = spotify.ffi.cast('sp_artist *', 43)
        artist = spotify.Artist(self.session, sp_artist=sp_artist)
        sp_artistbrowse = spotify.ffi.cast('sp_artistbrowse *', 42)
        lib_mock.sp_artistbrowse_create.return_value = sp_artistbrowse
        callback = mock.Mock()

        result = artist.browse(
            type=spotify.ArtistBrowserType.NO_TRACKS, callback=callback)

        lib_mock.sp_artistbrowse_create.assert_called_with(
            self.session._sp_session, sp_artist,
            int(spotify.ArtistBrowserType.NO_TRACKS), mock.ANY, mock.ANY)
        artistbrowse_complete_cb = (
            lib_mock.sp_artistbrowse_create.call_args[0][3])
        userdata = lib_mock.sp_artistbrowse_create.call_args[0][4]
        artistbrowse_complete_cb(sp_artistbrowse, userdata)

        result.loaded_event.wait(3)
        callback.assert_called_with(result)

    def test_browser_is_gone_before_callback_is_called(self, lib_mock):
        sp_artist = spotify.ffi.cast('sp_artist *', 43)
        artist = spotify.Artist(self.session, sp_artist=sp_artist)
        sp_artistbrowse = spotify.ffi.cast('sp_artistbrowse *', 42)
        lib_mock.sp_artistbrowse_create.return_value = sp_artistbrowse
        callback = mock.Mock()

        result = spotify.ArtistBrowser(
            self.session, artist=artist, callback=callback)
        loaded_event = result.loaded_event
        result = None  # noqa
        tests.gc_collect()

        # The mock keeps the handle/userdata alive, thus this test doesn't
        # really test that session._callback_handles keeps the handle alive.
        artistbrowse_complete_cb = (
            lib_mock.sp_artistbrowse_create.call_args[0][3])
        userdata = lib_mock.sp_artistbrowse_create.call_args[0][4]
        artistbrowse_complete_cb(sp_artistbrowse, userdata)

        loaded_event.wait(3)
        self.assertEqual(callback.call_count, 1)
        self.assertEqual(
            callback.call_args[0][0]._sp_artistbrowse, sp_artistbrowse)

    def test_adds_ref_to_sp_artistbrowse_when_created(self, lib_mock):
        sp_artistbrowse = spotify.ffi.cast('sp_artistbrowse *', 42)

        spotify.ArtistBrowser(self.session, sp_artistbrowse=sp_artistbrowse)

        lib_mock.sp_artistbrowse_add_ref.assert_called_with(sp_artistbrowse)

    def test_releases_sp_artistbrowse_when_artist_dies(self, lib_mock):
        sp_artistbrowse = spotify.ffi.cast('sp_artistbrowse *', 42)

        browser = spotify.ArtistBrowser(
            self.session, sp_artistbrowse=sp_artistbrowse)
        browser = None  # noqa
        tests.gc_collect()

        lib_mock.sp_artistbrowse_release.assert_called_with(sp_artistbrowse)

    @mock.patch('spotify.Link', spec=spotify.Link)
    def test_repr(self, link_mock, lib_mock):
        sp_artistbrowse = spotify.ffi.cast('sp_artistbrowse *', 42)
        browser = spotify.ArtistBrowser(
            self.session, sp_artistbrowse=sp_artistbrowse)
        lib_mock.sp_artistbrowse_is_loaded.return_value = 1
        sp_artist = spotify.ffi.cast('sp_artist *', 42)
        lib_mock.sp_artistbrowse_artist.return_value = sp_artist
        link_instance_mock = link_mock.return_value
        link_instance_mock.uri = 'foo'

        result = repr(browser)

        self.assertEqual(result, 'ArtistBrowser(%r)' % 'foo')

    def test_repr_if_unloaded(self, lib_mock):
        sp_artistbrowse = spotify.ffi.cast('sp_artistbrowse *', 42)
        browser = spotify.ArtistBrowser(
            self.session, sp_artistbrowse=sp_artistbrowse)
        lib_mock.sp_artistbrowse_is_loaded.return_value = 0

        result = repr(browser)

        self.assertEqual(result, 'ArtistBrowser(<not loaded>)')

    def test_eq(self, lib_mock):
        sp_artistbrowse = spotify.ffi.cast('sp_artistbrowse *', 42)
        browser1 = spotify.ArtistBrowser(
            self.session, sp_artistbrowse=sp_artistbrowse)
        browser2 = spotify.ArtistBrowser(
            self.session, sp_artistbrowse=sp_artistbrowse)

        self.assertTrue(browser1 == browser2)
        self.assertFalse(browser1 == 'foo')

    def test_ne(self, lib_mock):
        sp_artistbrowse = spotify.ffi.cast('sp_artistbrowse *', 42)
        browser1 = spotify.ArtistBrowser(
            self.session, sp_artistbrowse=sp_artistbrowse)
        browser2 = spotify.ArtistBrowser(
            self.session, sp_artistbrowse=sp_artistbrowse)

        self.assertFalse(browser1 != browser2)

    def test_hash(self, lib_mock):
        sp_artistbrowse = spotify.ffi.cast('sp_artistbrowse *', 42)
        browser1 = spotify.ArtistBrowser(
            self.session, sp_artistbrowse=sp_artistbrowse)
        browser2 = spotify.ArtistBrowser(
            self.session, sp_artistbrowse=sp_artistbrowse)

        self.assertEqual(hash(browser1), hash(browser2))

    def test_is_loaded(self, lib_mock):
        lib_mock.sp_artistbrowse_is_loaded.return_value = 1
        sp_artistbrowse = spotify.ffi.cast('sp_artistbrowse *', 42)
        browser = spotify.ArtistBrowser(
            self.session, sp_artistbrowse=sp_artistbrowse)

        result = browser.is_loaded

        lib_mock.sp_artistbrowse_is_loaded.assert_called_once_with(
            sp_artistbrowse)
        self.assertTrue(result)

    @mock.patch('spotify.utils.load')
    def test_load(self, load_mock, lib_mock):
        sp_artistbrowse = spotify.ffi.cast('sp_artistbrowse *', 42)
        browser = spotify.ArtistBrowser(
            self.session, sp_artistbrowse=sp_artistbrowse)

        browser.load(10)

        load_mock.assert_called_with(self.session, browser, timeout=10)

    def test_error(self, lib_mock):
        lib_mock.sp_artistbrowse_error.return_value = int(
            spotify.ErrorType.OTHER_PERMANENT)
        sp_artistbrowse = spotify.ffi.cast('sp_artistbrowse *', 42)
        browser = spotify.ArtistBrowser(
            self.session, sp_artistbrowse=sp_artistbrowse)

        result = browser.error

        lib_mock.sp_artistbrowse_error.assert_called_once_with(sp_artistbrowse)
        self.assertIs(result, spotify.ErrorType.OTHER_PERMANENT)

    def test_backend_request_duration(self, lib_mock):
        lib_mock.sp_artistbrowse_backend_request_duration.return_value = 137
        sp_artistbrowse = spotify.ffi.cast('sp_artistbrowse *', 42)
        browser = spotify.ArtistBrowser(
            self.session, sp_artistbrowse=sp_artistbrowse)

        result = browser.backend_request_duration

        lib_mock.sp_artistbrowse_backend_request_duration.assert_called_with(
            sp_artistbrowse)
        self.assertEqual(result, 137)

    def test_backend_request_duration_when_not_loaded(self, lib_mock):
        lib_mock.sp_artistbrowse_is_loaded.return_value = 0
        sp_artistbrowse = spotify.ffi.cast('sp_artistbrowse *', 42)
        browser = spotify.ArtistBrowser(
            self.session, sp_artistbrowse=sp_artistbrowse)

        result = browser.backend_request_duration

        lib_mock.sp_artistbrowse_is_loaded.assert_called_with(sp_artistbrowse)
        self.assertEqual(
            lib_mock.sp_artistbrowse_backend_request_duration.call_count, 0)
        self.assertIsNone(result)

    def test_artist(self, lib_mock):
        sp_artistbrowse = spotify.ffi.cast('sp_artistbrowse *', 42)
        browser = spotify.ArtistBrowser(
            self.session, sp_artistbrowse=sp_artistbrowse)
        sp_artist = spotify.ffi.cast('sp_artist *', 43)
        lib_mock.sp_artistbrowse_artist.return_value = sp_artist

        result = browser.artist

        self.assertIsInstance(result, spotify.Artist)
        self.assertEqual(result._sp_artist, sp_artist)

    def test_artist_when_not_loaded(self, lib_mock):
        sp_artistbrowse = spotify.ffi.cast('sp_artistbrowse *', 42)
        browser = spotify.ArtistBrowser(
            self.session, sp_artistbrowse=sp_artistbrowse)
        lib_mock.sp_artistbrowse_artist.return_value = spotify.ffi.NULL

        result = browser.artist

        lib_mock.sp_artistbrowse_artist.assert_called_with(sp_artistbrowse)
        self.assertIsNone(result)

    @mock.patch('spotify.Image', spec=spotify.Image)
    def test_portraits(self, image_mock, lib_mock):
        sp_artistbrowse = spotify.ffi.cast('sp_artistbrowse *', 42)
        browser = spotify.ArtistBrowser(
            self.session, sp_artistbrowse=sp_artistbrowse)
        lib_mock.sp_artistbrowse_num_portraits.return_value = 1
        image_id = spotify.ffi.new('char[]', b'image-id')
        lib_mock.sp_artistbrowse_portrait.return_value = image_id
        sp_image = spotify.ffi.cast('sp_image *', 43)
        lib_mock.sp_image_create.return_value = sp_image
        image_mock.return_value = mock.sentinel.image
        callback = mock.Mock()

        self.assertEqual(lib_mock.sp_artistbrowse_add_ref.call_count, 1)
        result = browser.portraits(callback=callback)
        self.assertEqual(lib_mock.sp_artistbrowse_add_ref.call_count, 2)

        self.assertEqual(len(result), 1)
        lib_mock.sp_artistbrowse_num_portraits.assert_called_with(
            sp_artistbrowse)

        item = result[0]
        self.assertIs(item, mock.sentinel.image)
        self.assertEqual(lib_mock.sp_artistbrowse_portrait.call_count, 1)
        lib_mock.sp_artistbrowse_portrait.assert_called_with(
            sp_artistbrowse, 0)

        # Since we *created* the sp_image, we already have a refcount of 1 and
        # shouldn't increase the refcount when wrapping this sp_image in an
        # Image object
        image_mock.assert_called_with(
            self.session, sp_image=sp_image, add_ref=False, callback=callback)

    def test_portraits_if_no_portraits(self, lib_mock):
        lib_mock.sp_artistbrowse_num_portraits.return_value = 0
        sp_artistbrowse = spotify.ffi.cast('sp_artistbrowse *', 42)
        browser = spotify.ArtistBrowser(
            self.session, sp_artistbrowse=sp_artistbrowse)

        result = browser.portraits()

        self.assertEqual(len(result), 0)
        lib_mock.sp_artistbrowse_num_portraits.assert_called_with(
            sp_artistbrowse)
        self.assertEqual(lib_mock.sp_artistbrowse_portrait.call_count, 0)

    def test_portraits_if_unloaded(self, lib_mock):
        lib_mock.sp_artistbrowse_is_loaded.return_value = 0
        sp_artistbrowse = spotify.ffi.cast('sp_artistbrowse *', 42)
        browser = spotify.ArtistBrowser(
            self.session, sp_artistbrowse=sp_artistbrowse)

        result = browser.portraits()

        lib_mock.sp_artistbrowse_is_loaded.assert_called_with(sp_artistbrowse)
        self.assertEqual(len(result), 0)

    @mock.patch('spotify.track.lib', spec=spotify.lib)
    def test_tracks(self, track_lib_mock, lib_mock):
        sp_track = spotify.ffi.cast('sp_track *', 43)
        lib_mock.sp_artistbrowse_num_tracks.return_value = 1
        lib_mock.sp_artistbrowse_track.return_value = sp_track
        sp_artistbrowse = spotify.ffi.cast('sp_artistbrowse *', 42)
        browser = spotify.ArtistBrowser(
            self.session, sp_artistbrowse=sp_artistbrowse)

        self.assertEqual(lib_mock.sp_artistbrowse_add_ref.call_count, 1)
        result = browser.tracks
        self.assertEqual(lib_mock.sp_artistbrowse_add_ref.call_count, 2)

        self.assertEqual(len(result), 1)
        lib_mock.sp_artistbrowse_num_tracks.assert_called_with(sp_artistbrowse)

        item = result[0]
        self.assertIsInstance(item, spotify.Track)
        self.assertEqual(item._sp_track, sp_track)
        self.assertEqual(lib_mock.sp_artistbrowse_track.call_count, 1)
        lib_mock.sp_artistbrowse_track.assert_called_with(sp_artistbrowse, 0)
        track_lib_mock.sp_track_add_ref.assert_called_with(sp_track)

    def test_tracks_if_no_tracks(self, lib_mock):
        lib_mock.sp_artistbrowse_num_tracks.return_value = 0
        sp_artistbrowse = spotify.ffi.cast('sp_artistbrowse *', 42)
        browser = spotify.ArtistBrowser(
            self.session, sp_artistbrowse=sp_artistbrowse)

        result = browser.tracks

        self.assertEqual(len(result), 0)
        lib_mock.sp_artistbrowse_num_tracks.assert_called_with(sp_artistbrowse)
        self.assertEqual(lib_mock.sp_artistbrowse_track.call_count, 0)

    def test_tracks_if_unloaded(self, lib_mock):
        lib_mock.sp_artistbrowse_is_loaded.return_value = 0
        sp_artistbrowse = spotify.ffi.cast('sp_artistbrowse *', 42)
        browser = spotify.ArtistBrowser(
            self.session, sp_artistbrowse=sp_artistbrowse)

        result = browser.tracks

        lib_mock.sp_artistbrowse_is_loaded.assert_called_with(sp_artistbrowse)
        self.assertEqual(len(result), 0)

    @mock.patch('spotify.track.lib', spec=spotify.lib)
    def test_tophit_tracks(self, track_lib_mock, lib_mock):
        sp_track = spotify.ffi.cast('sp_track *', 43)
        lib_mock.sp_artistbrowse_num_tophit_tracks.return_value = 1
        lib_mock.sp_artistbrowse_tophit_track.return_value = sp_track
        sp_artistbrowse = spotify.ffi.cast('sp_artistbrowse *', 42)
        browser = spotify.ArtistBrowser(
            self.session, sp_artistbrowse=sp_artistbrowse)

        self.assertEqual(lib_mock.sp_artistbrowse_add_ref.call_count, 1)
        result = browser.tophit_tracks
        self.assertEqual(lib_mock.sp_artistbrowse_add_ref.call_count, 2)

        self.assertEqual(len(result), 1)
        lib_mock.sp_artistbrowse_num_tophit_tracks.assert_called_with(
            sp_artistbrowse)

        item = result[0]
        self.assertIsInstance(item, spotify.Track)
        self.assertEqual(item._sp_track, sp_track)
        self.assertEqual(lib_mock.sp_artistbrowse_tophit_track.call_count, 1)
        lib_mock.sp_artistbrowse_tophit_track.assert_called_with(
            sp_artistbrowse, 0)
        track_lib_mock.sp_track_add_ref.assert_called_with(sp_track)

    def test_tophit_tracks_if_no_tracks(self, lib_mock):
        lib_mock.sp_artistbrowse_num_tophit_tracks.return_value = 0
        sp_artistbrowse = spotify.ffi.cast('sp_artistbrowse *', 42)
        browser = spotify.ArtistBrowser(
            self.session, sp_artistbrowse=sp_artistbrowse)

        result = browser.tophit_tracks

        self.assertEqual(len(result), 0)
        lib_mock.sp_artistbrowse_num_tophit_tracks.assert_called_with(
            sp_artistbrowse)
        self.assertEqual(lib_mock.sp_artistbrowse_track.call_count, 0)

    def test_tophit_tracks_if_unloaded(self, lib_mock):
        lib_mock.sp_artistbrowse_is_loaded.return_value = 0
        sp_artistbrowse = spotify.ffi.cast('sp_artistbrowse *', 42)
        browser = spotify.ArtistBrowser(
            self.session, sp_artistbrowse=sp_artistbrowse)

        result = browser.tophit_tracks

        lib_mock.sp_artistbrowse_is_loaded.assert_called_with(sp_artistbrowse)
        self.assertEqual(len(result), 0)

    @mock.patch('spotify.album.lib', spec=spotify.lib)
    def test_albums(self, album_lib_mock, lib_mock):
        sp_album = spotify.ffi.cast('sp_album *', 43)
        lib_mock.sp_artistbrowse_num_albums.return_value = 1
        lib_mock.sp_artistbrowse_album.return_value = sp_album
        sp_artistbrowse = spotify.ffi.cast('sp_artistbrowse *', 42)
        browser = spotify.ArtistBrowser(
            self.session, sp_artistbrowse=sp_artistbrowse)

        self.assertEqual(lib_mock.sp_artistbrowse_add_ref.call_count, 1)
        result = browser.albums
        self.assertEqual(lib_mock.sp_artistbrowse_add_ref.call_count, 2)

        self.assertEqual(len(result), 1)
        lib_mock.sp_artistbrowse_num_albums.assert_called_with(sp_artistbrowse)

        item = result[0]
        self.assertIsInstance(item, spotify.Album)
        self.assertEqual(item._sp_album, sp_album)
        self.assertEqual(lib_mock.sp_artistbrowse_album.call_count, 1)
        lib_mock.sp_artistbrowse_album.assert_called_with(sp_artistbrowse, 0)
        album_lib_mock.sp_album_add_ref.assert_called_with(sp_album)

    def test_albums_if_no_albums(self, lib_mock):
        lib_mock.sp_artistbrowse_num_albums.return_value = 0
        sp_artistbrowse = spotify.ffi.cast('sp_artistbrowse *', 42)
        browser = spotify.ArtistBrowser(
            self.session, sp_artistbrowse=sp_artistbrowse)

        result = browser.albums

        self.assertEqual(len(result), 0)
        lib_mock.sp_artistbrowse_num_albums.assert_called_with(sp_artistbrowse)
        self.assertEqual(lib_mock.sp_artistbrowse_album.call_count, 0)

    def test_albums_if_unloaded(self, lib_mock):
        lib_mock.sp_artistbrowse_is_loaded.return_value = 0
        sp_artistbrowse = spotify.ffi.cast('sp_artistbrowse *', 42)
        browser = spotify.ArtistBrowser(
            self.session, sp_artistbrowse=sp_artistbrowse)

        result = browser.albums

        lib_mock.sp_artistbrowse_is_loaded.assert_called_with(sp_artistbrowse)
        self.assertEqual(len(result), 0)

    def test_similar_artists(self, lib_mock):
        sp_artist = spotify.ffi.cast('sp_artist *', 43)
        lib_mock.sp_artistbrowse_num_similar_artists.return_value = 1
        lib_mock.sp_artistbrowse_similar_artist.return_value = sp_artist
        sp_artistbrowse = spotify.ffi.cast('sp_artistbrowse *', 42)
        browser = spotify.ArtistBrowser(
            self.session, sp_artistbrowse=sp_artistbrowse)

        self.assertEqual(lib_mock.sp_artistbrowse_add_ref.call_count, 1)
        result = browser.similar_artists
        self.assertEqual(lib_mock.sp_artistbrowse_add_ref.call_count, 2)

        self.assertEqual(len(result), 1)
        lib_mock.sp_artistbrowse_num_similar_artists.assert_called_with(
            sp_artistbrowse)

        item = result[0]
        self.assertIsInstance(item, spotify.Artist)
        self.assertEqual(item._sp_artist, sp_artist)
        self.assertEqual(
            lib_mock.sp_artistbrowse_similar_artist.call_count, 1)
        lib_mock.sp_artistbrowse_similar_artist.assert_called_with(
            sp_artistbrowse, 0)
        lib_mock.sp_artist_add_ref.assert_called_with(sp_artist)

    def test_similar_artists_if_no_artists(self, lib_mock):
        lib_mock.sp_artistbrowse_num_similar_artists.return_value = 0
        sp_artistbrowse = spotify.ffi.cast('sp_artistbrowse *', 42)
        browser = spotify.ArtistBrowser(
            self.session, sp_artistbrowse=sp_artistbrowse)

        result = browser.similar_artists

        self.assertEqual(len(result), 0)
        lib_mock.sp_artistbrowse_num_similar_artists.assert_called_with(
            sp_artistbrowse)
        self.assertEqual(lib_mock.sp_artistbrowse_similar_artist.call_count, 0)

    def test_similar_artists_if_unloaded(self, lib_mock):
        lib_mock.sp_artistbrowse_is_loaded.return_value = 0
        sp_artistbrowse = spotify.ffi.cast('sp_artistbrowse *', 42)
        browser = spotify.ArtistBrowser(
            self.session, sp_artistbrowse=sp_artistbrowse)

        result = browser.similar_artists

        lib_mock.sp_artistbrowse_is_loaded.assert_called_with(sp_artistbrowse)
        self.assertEqual(len(result), 0)

    def test_biography(self, lib_mock):
        sp_artistbrowse = spotify.ffi.cast('sp_artistbrowse *', 42)
        browser = spotify.ArtistBrowser(
            self.session, sp_artistbrowse=sp_artistbrowse)
        biography = spotify.ffi.new('char[]', b'Lived, played, and died')
        lib_mock.sp_artistbrowse_biography.return_value = biography

        result = browser.biography

        self.assertIsInstance(result, utils.text_type)
        self.assertEqual(result, 'Lived, played, and died')


class ArtistBrowserTypeTest(unittest.TestCase):

    def test_has_constants(self):
        self.assertEqual(spotify.ArtistBrowserType.FULL, 0)
        self.assertEqual(spotify.ArtistBrowserType.NO_TRACKS, 1)
        self.assertEqual(spotify.ArtistBrowserType.NO_ALBUMS, 2)

########NEW FILE########
__FILENAME__ = test_audio
from __future__ import unicode_literals

import unittest

import spotify


class AudioBufferStatsTest(unittest.TestCase):

    def test_samples(self):
        stats = spotify.AudioBufferStats(100, 5)

        self.assertEqual(stats.samples, 100)

    def test_stutter(self):
        stats = spotify.AudioBufferStats(100, 5)

        self.assertEqual(stats.stutter, 5)


class AudioFormatTest(unittest.TestCase):

    def setUp(self):
        self._sp_audioformat = spotify.ffi.new('sp_audioformat *')
        self._sp_audioformat.sample_type = (
            spotify.SampleType.INT16_NATIVE_ENDIAN)
        self._sp_audioformat.sample_rate = 44100
        self._sp_audioformat.channels = 2
        self.audio_format = spotify.AudioFormat(self._sp_audioformat)

    def test_sample_type(self):
        self.assertIs(
            self.audio_format.sample_type,
            spotify.SampleType.INT16_NATIVE_ENDIAN)

    def test_sample_rate(self):
        self.assertEqual(self.audio_format.sample_rate, 44100)

    def test_channels(self):
        self.assertEqual(self.audio_format.channels, 2)

    def test_frame_size(self):
        # INT16 means 16 bits aka 2 bytes per channel
        self._sp_audioformat.sample_type = (
            spotify.SampleType.INT16_NATIVE_ENDIAN)

        self._sp_audioformat.channels = 1
        self.assertEqual(self.audio_format.frame_size(), 2)

        self._sp_audioformat.channels = 2
        self.assertEqual(self.audio_format.frame_size(), 4)

    def test_frame_size_fails_if_sample_type_is_unknown(self):
        self._sp_audioformat.sample_type = 666

        with self.assertRaises(ValueError):
            self.audio_format.frame_size()


class BitrateTest(unittest.TestCase):

    def test_has_contants(self):
        self.assertEqual(spotify.Bitrate.BITRATE_96k, 2)
        self.assertEqual(spotify.Bitrate.BITRATE_160k, 0)
        self.assertEqual(spotify.Bitrate.BITRATE_320k, 1)


class SampleTypeTest(unittest.TestCase):

    def test_has_constants(self):
        self.assertEqual(spotify.SampleType.INT16_NATIVE_ENDIAN, 0)

########NEW FILE########
__FILENAME__ = test_config
# encoding: utf-8

from __future__ import unicode_literals

import platform
import tempfile
import unittest

import spotify
from tests import mock


class ConfigTest(unittest.TestCase):
    def setUp(self):
        self.config = spotify.Config()

    def test_api_version(self):
        self.config.api_version = 71

        self.assertEqual(self.config._sp_session_config.api_version, 71)
        self.assertEqual(self.config.api_version, 71)

    def test_api_version_defaults_to_current_lib_version(self):
        self.assertEqual(
            self.config.api_version, spotify.lib.SPOTIFY_API_VERSION)

    def test_cache_location(self):
        self.config.cache_location = b'/cache'

        self.assertEqual(
            spotify.ffi.string(self.config._sp_session_config.cache_location),
            b'/cache')
        self.assertEqual(self.config.cache_location, b'/cache')

    def test_cache_location_defaults_to_tmp_in_cwd(self):
        self.assertEqual(self.config.cache_location, b'tmp')

    def test_settings_location(self):
        self.config.settings_location = b'/settings'

        self.assertEqual(
            spotify.ffi.string(
                self.config._sp_session_config.settings_location),
            b'/settings')
        self.assertEqual(self.config.settings_location, b'/settings')

    def test_settings_location_defaults_to_tmp_in_cwd(self):
        self.assertEqual(self.config.settings_location, b'tmp')

    def test_application_key(self):
        self.config.application_key = b'\x02' * 321

        self.assertEqual(
            spotify.ffi.string(spotify.ffi.cast(
                'char *', self.config._sp_session_config.application_key)),
            b'\x02' * 321)
        self.assertEqual(self.config.application_key, b'\x02' * 321)

    def test_application_key_is_unknown(self):
        self.assertIsNone(self.config.application_key)

    def test_applicaton_key_size_is_zero_by_default(self):
        self.assertEqual(
            self.config._sp_session_config.application_key_size, 0)

    def test_application_key_size_is_calculated_correctly(self):
        self.config.application_key = b'\x01' * 321

        self.assertEqual(
            self.config._sp_session_config.application_key_size, 321)

    def test_application_key_can_be_reset_to_none(self):
        self.config.application_key = None

        self.assertIsNone(self.config.application_key)
        self.assertEqual(
            self.config._sp_session_config.application_key_size, 0)

    def test_application_key_fails_if_invalid_key(self):
        with self.assertRaises(AssertionError):
            self.config.application_key = 'way too short key'

    def test_load_application_key_file_can_load_key_from_file(self):
        self.config.application_key = None
        filename = tempfile.mkstemp()[1]
        with open(filename, 'wb') as f:
            f.write(b'\x03' * 321)

        self.config.load_application_key_file(filename)

        self.assertEqual(self.config.application_key, b'\x03' * 321)

    def test_load_application_key_file_defaults_to_a_file_in_cwd(self):
        open_mock = mock.mock_open(read_data='\x04' * 321)
        with mock.patch('spotify.config.open', open_mock, create=True) as m:
            self.config.load_application_key_file()

        m.assert_called_once_with(b'spotify_appkey.key', 'rb')
        self.assertEqual(self.config.application_key, b'\x04' * 321)

    def test_load_application_key_file_fails_if_no_key_found(self):
        with self.assertRaises(EnvironmentError):
            self.config.load_application_key_file(b'/nonexistant')

    def test_user_agent(self):
        self.config.user_agent = 'an agent'

        self.assertEqual(
            spotify.ffi.string(self.config._sp_session_config.user_agent),
            b'an agent')
        self.assertEqual(self.config.user_agent, 'an agent')

    def test_user_agent_defaults_to_pyspotify_with_version_number(self):
        self.assertEqual(
            self.config.user_agent, 'pyspotify %s' % spotify.__version__)

    def test_compress_playlists(self):
        self.config.compress_playlists = True

        self.assertEqual(self.config._sp_session_config.compress_playlists, 1)
        self.assertEqual(self.config.compress_playlists, True)

    def test_compress_playlists_defaults_to_false(self):
        self.assertFalse(self.config.compress_playlists)

    def test_dont_save_metadata_for_playlists(self):
        self.config.dont_save_metadata_for_playlists = True

        self.assertEqual(
            self.config._sp_session_config.dont_save_metadata_for_playlists, 1)
        self.assertEqual(self.config.dont_save_metadata_for_playlists, True)

    def test_dont_save_metadata_for_playlists_defaults_to_false(self):
        self.assertFalse(self.config.dont_save_metadata_for_playlists)

    def test_initially_unload_playlists(self):
        self.config.initially_unload_playlists = True

        self.assertEqual(
            self.config._sp_session_config.initially_unload_playlists, 1)
        self.assertEqual(self.config.initially_unload_playlists, True)

    def test_initially_unload_playlists_defaults_to_false(self):
        self.assertFalse(self.config.initially_unload_playlists)

    def test_device_id(self):
        self.config.device_id = '123abc'

        self.assertEqual(
            spotify.ffi.string(self.config._sp_session_config.device_id),
            b'123abc')
        self.assertEqual(self.config.device_id, '123abc')

    def test_device_id_defaults_to_none(self):
        self.assertIsNone(self.config.device_id)

    def test_proxy(self):
        self.config.proxy = '123abc'

        self.assertEqual(
            spotify.ffi.string(self.config._sp_session_config.proxy),
            b'123abc')
        self.assertEqual(self.config.proxy, '123abc')

    def test_proxy_defaults_to_none(self):
        self.assertIsNone(self.config.proxy)

    def test_proxy_username(self):
        self.config.proxy_username = '123abc'

        self.assertEqual(
            spotify.ffi.string(self.config._sp_session_config.proxy_username),
            b'123abc')
        self.assertEqual(self.config.proxy_username, '123abc')

    def test_proxy_username_defaults_to_none(self):
        self.assertIsNone(self.config.proxy_username)

    def test_proxy_password(self):
        self.config.proxy_password = '123abc'

        self.assertEqual(
            spotify.ffi.string(self.config._sp_session_config.proxy_password),
            b'123abc')
        self.assertEqual(self.config.proxy_password, '123abc')

    def test_proxy_password_defaults_to_none(self):
        self.assertIsNone(self.config.proxy_password)

    @unittest.skipIf(
        platform.system() == 'Darwin',
        'The struct field does not exist in libspotify for OS X')
    def test_ca_certs_filename(self):
        self.config.ca_certs_filename = b'ca.crt'

        self.assertEqual(
            spotify.ffi.string(
                self.config._get_ca_certs_filename_ptr()[0]),
            b'ca.crt')
        self.assertEqual(self.config.ca_certs_filename, b'ca.crt')

    @unittest.skipIf(
        platform.system() == 'Darwin',
        'The struct field does not exist in libspotify for OS X')
    def test_ca_certs_filename_defaults_to_none(self):
        self.assertIsNone(self.config.ca_certs_filename)

    @unittest.skipIf(
        platform.system() != 'Darwin',
        'Not supported on this operating system')
    def test_ca_certs_filename_is_a_noop_on_os_x(self):
        self.assertIsNone(self.config.ca_certs_filename)

        self.config.ca_certs_filename = b'ca.crt'

        self.assertIsNone(self.config.ca_certs_filename)

    def test_tracefile(self):
        self.config.tracefile = b'123abc'

        self.assertEqual(
            spotify.ffi.string(self.config._sp_session_config.tracefile),
            b'123abc')
        self.assertEqual(self.config.tracefile, b'123abc')

    def test_tracefile_defaults_to_none(self):
        self.assertIsNone(self.config.tracefile)

    def test_sp_session_config_has_unicode_encoded_as_utf8(self):
        self.config.device_id = 'æ device_id'
        self.config.proxy = 'æ proxy'
        self.config.proxy_username = 'æ proxy_username'
        self.config.proxy_password = 'æ proxy_password'
        # XXX Waiting for ca_certs_filename on OS X
        # self.config.ca_certs_filename = b'æ ca_certs_filename'.encode(
        #     'utf-8')
        self.config.tracefile = 'æ tracefile'.encode('utf-8')

        self.assertEqual(
            spotify.ffi.string(self.config._sp_session_config.device_id),
            b'\xc3\xa6 device_id')
        self.assertEqual(
            spotify.ffi.string(self.config._sp_session_config.proxy),
            b'\xc3\xa6 proxy')
        self.assertEqual(
            spotify.ffi.string(self.config._sp_session_config.proxy_username),
            b'\xc3\xa6 proxy_username')
        self.assertEqual(
            spotify.ffi.string(self.config._sp_session_config.proxy_password),
            b'\xc3\xa6 proxy_password')
        # XXX Waiting for ca_certs_filename on OS X
        # self.assertEqual(
        #     spotify.ffi.string(
        #         self.config.sp_session_config.ca_certs_filename),
        #     b'\xc3\xa6 ca_certs_filename')
        self.assertEqual(
            spotify.ffi.string(self.config._sp_session_config.tracefile),
            b'\xc3\xa6 tracefile')

########NEW FILE########
__FILENAME__ = test_connection
from __future__ import unicode_literals

import unittest

import spotify

import tests
from tests import mock


@mock.patch('spotify.connection.lib', spec=spotify.lib)
@mock.patch('spotify.session.lib', spec=spotify.lib)
class ConnectionTest(unittest.TestCase):

    def tearDown(self):
        spotify._session_instance = None

    def test_connection_state(self, session_lib_mock, lib_mock):
        lib_mock.sp_session_connectionstate.return_value = int(
            spotify.ConnectionState.LOGGED_OUT)
        session = tests.create_real_session(session_lib_mock)

        self.assertIs(
            session.connection.state, spotify.ConnectionState.LOGGED_OUT)

        lib_mock.sp_session_connectionstate.assert_called_once_with(
            session._sp_session)

    def test_connection_type_defaults_to_unknown(
            self, session_lib_mock, lib_mock):
        lib_mock.sp_session_set_connection_type.return_value = (
            spotify.ErrorType.OK)
        session = tests.create_real_session(session_lib_mock)

        result = session.connection.type

        self.assertIs(result, spotify.ConnectionType.UNKNOWN)
        self.assertEqual(lib_mock.sp_session_set_connection_type.call_count, 0)

    def test_set_connection_type(self, session_lib_mock, lib_mock):
        lib_mock.sp_session_set_connection_type.return_value = (
            spotify.ErrorType.OK)
        session = tests.create_real_session(session_lib_mock)

        session.connection.type = spotify.ConnectionType.MOBILE_ROAMING

        lib_mock.sp_session_set_connection_type.assert_called_with(
            session._sp_session, spotify.ConnectionType.MOBILE_ROAMING)

        result = session.connection.type

        self.assertIs(result, spotify.ConnectionType.MOBILE_ROAMING)

    def test_set_connection_type_fail_raises_error(
            self, session_lib_mock, lib_mock):
        lib_mock.sp_session_set_connection_type.return_value = (
            spotify.ErrorType.BAD_API_VERSION)
        session = tests.create_real_session(session_lib_mock)

        with self.assertRaises(spotify.Error):
            session.connection.type = spotify.ConnectionType.MOBILE_ROAMING

        result = session.connection.type

        self.assertIs(result, spotify.ConnectionType.UNKNOWN)

    def test_allow_network_defaults_to_true(self, session_lib_mock, lib_mock):
        session = tests.create_real_session(session_lib_mock)

        self.assertTrue(session.connection.allow_network)

    def test_set_allow_network(self, session_lib_mock, lib_mock):
        lib_mock.sp_session_set_connection_rules.return_value = (
            spotify.ErrorType.OK)
        session = tests.create_real_session(session_lib_mock)

        session.connection.allow_network = False

        self.assertFalse(session.connection.allow_network)
        lib_mock.sp_session_set_connection_rules.assert_called_with(
            session._sp_session,
            int(spotify.ConnectionRule.ALLOW_SYNC_OVER_WIFI))

    def test_allow_network_if_roaming_defaults_to_false(
            self, session_lib_mock, lib_mock):
        session = tests.create_real_session(session_lib_mock)

        self.assertFalse(session.connection.allow_network_if_roaming)

    def test_set_allow_network_if_roaming(self, session_lib_mock, lib_mock):
        lib_mock.sp_session_set_connection_rules.return_value = (
            spotify.ErrorType.OK)
        session = tests.create_real_session(session_lib_mock)

        session.connection.allow_network_if_roaming = True

        self.assertTrue(session.connection.allow_network_if_roaming)
        lib_mock.sp_session_set_connection_rules.assert_called_with(
            session._sp_session,
            spotify.ConnectionRule.NETWORK |
            spotify.ConnectionRule.NETWORK_IF_ROAMING |
            spotify.ConnectionRule.ALLOW_SYNC_OVER_WIFI)

    def test_allow_sync_over_wifi_defaults_to_true(
            self, session_lib_mock, lib_mock):
        session = tests.create_real_session(session_lib_mock)

        self.assertTrue(session.connection.allow_sync_over_wifi)

    def test_set_allow_sync_over_wifi(self, session_lib_mock, lib_mock):
        lib_mock.sp_session_set_connection_rules.return_value = (
            spotify.ErrorType.OK)
        session = tests.create_real_session(session_lib_mock)

        session.connection.allow_sync_over_wifi = False

        self.assertFalse(session.connection.allow_sync_over_wifi)
        lib_mock.sp_session_set_connection_rules.assert_called_with(
            session._sp_session,
            int(spotify.ConnectionRule.NETWORK))

    def test_allow_sync_over_mobile_defaults_to_false(
            self, session_lib_mock, lib_mock):
        session = tests.create_real_session(session_lib_mock)

        self.assertFalse(session.connection.allow_sync_over_mobile)

    def test_set_allow_sync_over_mobile(self, session_lib_mock, lib_mock):
        lib_mock.sp_session_set_connection_rules.return_value = (
            spotify.ErrorType.OK)
        session = tests.create_real_session(session_lib_mock)

        session.connection.allow_sync_over_mobile = True

        self.assertTrue(session.connection.allow_sync_over_mobile)
        lib_mock.sp_session_set_connection_rules.assert_called_with(
            session._sp_session,
            spotify.ConnectionRule.NETWORK |
            spotify.ConnectionRule.ALLOW_SYNC_OVER_WIFI |
            spotify.ConnectionRule.ALLOW_SYNC_OVER_MOBILE)

    def test_set_connection_rules_without_rules(
            self, session_lib_mock, lib_mock):
        lib_mock.sp_session_set_connection_rules.return_value = (
            spotify.ErrorType.OK)
        session = tests.create_real_session(session_lib_mock)

        session.connection.allow_network = False
        session.connection.allow_sync_over_wifi = False

        lib_mock.sp_session_set_connection_rules.assert_called_with(
            session._sp_session, 0)

    def test_set_connection_rules_fail_raises_error(
            self, session_lib_mock, lib_mock):
        lib_mock.sp_session_set_connection_rules.return_value = (
            spotify.ErrorType.BAD_API_VERSION)
        session = tests.create_real_session(session_lib_mock)

        with self.assertRaises(spotify.Error):
            session.connection.allow_network = False


class ConnectionRuleTest(unittest.TestCase):

    def test_has_constants(self):
        self.assertEqual(spotify.ConnectionRule.NETWORK, 1)
        self.assertEqual(spotify.ConnectionRule.ALLOW_SYNC_OVER_WIFI, 8)


class ConnectionStateTest(unittest.TestCase):

    def test_has_constants(self):
        self.assertEqual(spotify.ConnectionState.LOGGED_OUT, 0)


class ConnectionTypeTest(unittest.TestCase):

    def test_has_constants(self):
        self.assertEqual(spotify.ConnectionType.UNKNOWN, 0)

########NEW FILE########
__FILENAME__ = test_error
from __future__ import unicode_literals

import unittest

import spotify
from spotify import utils


class ErrorTest(unittest.TestCase):

    def test_error_is_an_exception(self):
        error = spotify.Error(0)
        self.assertIsInstance(error, Exception)

    def test_maybe_raise(self):
        with self.assertRaises(spotify.LibError):
            spotify.Error.maybe_raise(spotify.ErrorType.BAD_API_VERSION)

    def test_maybe_raise_does_not_raise_if_ok(self):
        spotify.Error.maybe_raise(spotify.ErrorType.OK)

    def test_maybe_raise_does_not_raise_if_error_is_ignored(self):
        spotify.Error.maybe_raise(
            spotify.ErrorType.BAD_API_VERSION,
            ignores=[spotify.ErrorType.BAD_API_VERSION])

    def test_maybe_raise_works_with_any_iterable(self):
        spotify.Error.maybe_raise(
            spotify.ErrorType.BAD_API_VERSION,
            ignores=(spotify.ErrorType.BAD_API_VERSION,))


class LibErrorTest(unittest.TestCase):

    def test_is_an_error(self):
        error = spotify.LibError(0)
        self.assertIsInstance(error, spotify.Error)

    def test_has_error_type(self):
        error = spotify.LibError(0)
        self.assertEqual(error.error_type, 0)

        error = spotify.LibError(1)
        self.assertEqual(error.error_type, 1)

    def test_is_equal_if_same_error_type(self):
        self.assertEqual(spotify.LibError(0), spotify.LibError(0))

    def test_is_not_equal_if_different_error_type(self):
        self.assertNotEqual(spotify.LibError(0), spotify.LibError(1))

    def test_error_has_useful_repr(self):
        error = spotify.LibError(0)
        self.assertIn('No error', repr(error))

    def test_error_has_useful_string_representation(self):
        error = spotify.LibError(0)
        self.assertEqual('%s' % error, 'No error')
        self.assertIsInstance('%s' % error, utils.text_type)

        error = spotify.LibError(1)
        self.assertEqual('%s' % error, 'Invalid library version')

    def test_has_error_constants(self):
        self.assertEqual(
            spotify.LibError.OK, spotify.LibError(spotify.ErrorType.OK))
        self.assertEqual(
            spotify.LibError.BAD_API_VERSION,
            spotify.LibError(spotify.ErrorType.BAD_API_VERSION))


class ErrorTypeTest(unittest.TestCase):

    def test_has_error_type_constants(self):
        self.assertEqual(spotify.ErrorType.OK, 0)
        self.assertEqual(spotify.ErrorType.BAD_API_VERSION, 1)


class TimeoutTest(unittest.TestCase):

    def test_is_an_error(self):
        error = spotify.Timeout(0.5)
        self.assertIsInstance(error, spotify.Error)

    def test_has_useful_repr(self):
        error = spotify.Timeout(0.5)
        self.assertIn('Operation did not complete in 0.500s', repr(error))

    def test_has_useful_string_representation(self):
        error = spotify.Timeout(0.5)
        self.assertEqual('%s' % error, 'Operation did not complete in 0.500s')
        self.assertIsInstance('%s' % error, utils.text_type)

########NEW FILE########
__FILENAME__ = test_eventloop
from __future__ import unicode_literals

import time
import unittest

try:
    # Python 3
    import queue
except ImportError:
    # Python 2
    import Queue as queue

import spotify
from tests import mock


class EventLoopTest(unittest.TestCase):

    def setUp(self):
        self.timeout = 0.1
        self.session = mock.Mock(spec=spotify.Session)
        self.session.process_events.return_value = int(self.timeout * 1000)
        self.loop = spotify.EventLoop(self.session)

    def tearDown(self):
        self.loop.stop()
        while self.loop.is_alive():
            self.loop.join(1)

    def test_is_a_daemon_thread(self):
        self.assertTrue(self.loop.daemon)

    def test_has_a_descriptive_thread_name(self):
        self.assertEqual(self.loop.name, 'SpotifyEventLoop')

    def test_can_be_started_and_stopped_and_joined(self):
        self.assertFalse(self.loop.is_alive())

        self.loop.start()
        self.assertTrue(self.loop.is_alive())

        self.loop.stop()
        self.loop.join(1)
        self.assertFalse(self.loop.is_alive())

    def test_start_registers_notify_main_thread_listener(self):
        self.loop.start()

        self.session.on.assert_called_once_with(
            spotify.SessionEvent.NOTIFY_MAIN_THREAD,
            self.loop._on_notify_main_thread)

    def test_stop_unregisters_notify_main_thread_listener(self):
        self.loop.stop()

        self.session.off.assert_called_once_with(
            spotify.SessionEvent.NOTIFY_MAIN_THREAD,
            self.loop._on_notify_main_thread)

    def test_run_immediately_process_events(self):
        self.loop._runnable = False  # Short circuit run()
        self.loop.run()

        self.session.process_events.assert_called_once_with()

    def test_processes_events_if_no_notify_main_thread_before_timeout(self):
        self.loop._queue = mock.Mock(spec=queue.Queue)
        self.loop._queue.get = lambda timeout: time.sleep(timeout)
        self.loop.start()

        time.sleep(0.25)
        self.loop.stop()
        self.assertGreaterEqual(self.session.process_events.call_count, 3)

    def test_puts_on_queue_on_notify_main_thread(self):
        self.loop._queue = mock.Mock(spec=queue.Queue)

        self.loop._on_notify_main_thread(self.session)

        self.loop._queue.put_nowait.assert_called_once_with(mock.ANY)

    def test_on_notify_main_thread_fails_nicely_if_queue_is_full(self):
        self.loop._queue = mock.Mock(spec=queue.Queue)
        self.loop._queue.put_nowait.side_effect = queue.Full

        self.loop._on_notify_main_thread(self.session)

        self.loop._queue.put_nowait.assert_called_once_with(mock.ANY)

########NEW FILE########
__FILENAME__ = test_image
from __future__ import unicode_literals

import unittest

import spotify
import tests
from tests import mock


@mock.patch('spotify.image.lib', spec=spotify.lib)
class ImageTest(unittest.TestCase):

    def setUp(self):
        self.session = tests.create_session_mock()
        spotify._session_instance = self.session

    def tearDown(self):
        spotify._session_instance = None

    def test_create_without_uri_or_sp_image_fails(self, lib_mock):
        with self.assertRaises(AssertionError):
            spotify.Image(self.session)

    @mock.patch('spotify.Link', spec=spotify.Link)
    def test_create_from_uri(self, link_mock, lib_mock):
        lib_mock.sp_image_add_load_callback.return_value = int(
            spotify.ErrorType.OK)
        sp_image = spotify.ffi.cast('sp_image *', 42)
        link_instance_mock = link_mock.return_value
        link_instance_mock.as_image.return_value = spotify.Image(
            self.session, sp_image=sp_image)
        lib_mock.sp_image_create_from_link.return_value = sp_image
        uri = 'spotify:image:foo'

        result = spotify.Image(self.session, uri=uri)

        link_mock.assert_called_with(self.session, uri=uri)
        link_instance_mock.as_image.assert_called_with()
        lib_mock.sp_image_add_ref.assert_called_with(sp_image)
        self.assertEqual(result._sp_image, sp_image)

    @mock.patch('spotify.Link', spec=spotify.Link)
    def test_create_from_uri_fail_raises_error(self, link_mock, lib_mock):
        link_instance_mock = link_mock.return_value
        link_instance_mock.as_image.return_value = None
        uri = 'spotify:image:foo'

        with self.assertRaises(ValueError):
            spotify.Image(self.session, uri=uri)

    def test_adds_ref_to_sp_image_when_created(self, lib_mock):
        lib_mock.sp_image_add_load_callback.return_value = int(
            spotify.ErrorType.OK)
        sp_image = spotify.ffi.cast('sp_image *', 42)

        spotify.Image(self.session, sp_image=sp_image)

        lib_mock.sp_image_add_ref.assert_called_with(sp_image)

    def test_releases_sp_image_when_image_dies(self, lib_mock):
        lib_mock.sp_image_add_load_callback.return_value = int(
            spotify.ErrorType.OK)
        sp_image = spotify.ffi.cast('sp_image *', 42)

        image = spotify.Image(self.session, sp_image=sp_image)
        image = None  # noqa
        tests.gc_collect()

        lib_mock.sp_image_release.assert_called_with(sp_image)

    @mock.patch('spotify.Link', spec=spotify.Link)
    def test_repr(self, link_mock, lib_mock):
        link_instance_mock = link_mock.return_value
        link_instance_mock.uri = 'foo'
        lib_mock.sp_image_add_load_callback.return_value = int(
            spotify.ErrorType.OK)
        sp_image = spotify.ffi.cast('sp_image *', 42)
        image = spotify.Image(self.session, sp_image=sp_image)

        result = repr(image)

        self.assertEqual(result, 'Image(%r)' % 'foo')

    def test_eq(self, lib_mock):
        lib_mock.sp_image_add_load_callback.return_value = int(
            spotify.ErrorType.OK)
        sp_image = spotify.ffi.cast('sp_image *', 42)
        image1 = spotify.Image(self.session, sp_image=sp_image)
        image2 = spotify.Image(self.session, sp_image=sp_image)

        self.assertTrue(image1 == image2)
        self.assertFalse(image1 == 'foo')

    def test_ne(self, lib_mock):
        lib_mock.sp_image_add_load_callback.return_value = int(
            spotify.ErrorType.OK)
        sp_image = spotify.ffi.cast('sp_image *', 42)
        image1 = spotify.Image(self.session, sp_image=sp_image)
        image2 = spotify.Image(self.session, sp_image=sp_image)

        self.assertFalse(image1 != image2)

    def test_hash(self, lib_mock):
        lib_mock.sp_image_add_load_callback.return_value = int(
            spotify.ErrorType.OK)
        sp_image = spotify.ffi.cast('sp_image *', 42)
        image1 = spotify.Image(self.session, sp_image=sp_image)
        image2 = spotify.Image(self.session, sp_image=sp_image)

        self.assertEqual(hash(image1), hash(image2))

    def test_loaded_event_is_unset_by_default(self, lib_mock):
        lib_mock.sp_image_add_load_callback.return_value = int(
            spotify.ErrorType.OK)
        sp_image = spotify.ffi.cast('sp_image *', 42)
        image = spotify.Image(self.session, sp_image=sp_image)

        self.assertFalse(image.loaded_event.is_set())

    def test_create_with_callback(self, lib_mock):
        lib_mock.sp_image_add_load_callback.return_value = int(
            spotify.ErrorType.OK)
        lib_mock.sp_image_remove_load_callback.return_value = int(
            spotify.ErrorType.OK)
        sp_image = spotify.ffi.cast('sp_image *', 42)
        lib_mock.sp_image_create.return_value = sp_image
        callback = mock.Mock()

        # Add callback
        image = spotify.Image(
            self.session, sp_image=sp_image, callback=callback)

        lib_mock.sp_image_add_load_callback.assert_called_with(
            sp_image, mock.ANY, mock.ANY)
        image_load_cb = lib_mock.sp_image_add_load_callback.call_args[0][1]
        callback_handle = lib_mock.sp_image_add_load_callback.call_args[0][2]

        # Call calls callback, sets event, and removes callback registration
        self.assertEqual(callback.call_count, 0)
        self.assertEqual(lib_mock.sp_image_remove_load_callback.call_count, 0)
        self.assertFalse(image.loaded_event.is_set())
        image_load_cb(sp_image, callback_handle)
        callback.assert_called_once_with(image)
        lib_mock.sp_image_remove_load_callback.assert_called_with(
            sp_image, image_load_cb, callback_handle)
        self.assertTrue(image.loaded_event.is_set())

    def test_create_with_callback_and_throw_away_image_and_call_load_callback(
            self, lib_mock):

        lib_mock.sp_image_add_load_callback.return_value = int(
            spotify.ErrorType.OK)
        lib_mock.sp_image_remove_load_callback.return_value = int(
            spotify.ErrorType.OK)
        sp_image = spotify.ffi.cast('sp_image *', 42)
        lib_mock.sp_image_create.return_value = sp_image
        callback = mock.Mock()

        # Add callback
        image = spotify.Image(
            self.session, sp_image=sp_image, callback=callback)
        loaded_event = image.loaded_event

        # Throw away reference to 'image'
        image = None  # noqa
        tests.gc_collect()

        # The mock keeps the handle/userdata alive, thus this test doesn't
        # really test that session._callback_handles keeps the handle alive.

        # Call callback
        image_load_cb = lib_mock.sp_image_add_load_callback.call_args[0][1]
        callback_handle = lib_mock.sp_image_add_load_callback.call_args[0][2]
        image_load_cb(sp_image, callback_handle)

        loaded_event.wait(3)
        self.assertEqual(callback.call_count, 1)
        self.assertEqual(callback.call_args[0][0]._sp_image, sp_image)

    def test_create_with_callback_fails_if_error_adding_callback(
            self, lib_mock):

        lib_mock.sp_image_add_load_callback.return_value = int(
            spotify.ErrorType.BAD_API_VERSION)
        sp_image = spotify.ffi.cast('sp_image *', 42)
        callback = mock.Mock()

        with self.assertRaises(spotify.Error):
            spotify.Image(self.session, sp_image=sp_image, callback=callback)

    def test_is_loaded(self, lib_mock):
        lib_mock.sp_image_is_loaded.return_value = 1
        lib_mock.sp_image_add_load_callback.return_value = int(
            spotify.ErrorType.OK)
        sp_image = spotify.ffi.cast('sp_image *', 42)
        image = spotify.Image(self.session, sp_image=sp_image)

        result = image.is_loaded

        lib_mock.sp_image_is_loaded.assert_called_once_with(sp_image)
        self.assertTrue(result)

    def test_error(self, lib_mock):
        lib_mock.sp_image_error.return_value = int(
            spotify.ErrorType.IS_LOADING)
        lib_mock.sp_image_add_load_callback.return_value = int(
            spotify.ErrorType.OK)
        sp_image = spotify.ffi.cast('sp_image *', 42)
        image = spotify.Image(self.session, sp_image=sp_image)

        result = image.error

        lib_mock.sp_image_error.assert_called_once_with(sp_image)
        self.assertIs(result, spotify.ErrorType.IS_LOADING)

    @mock.patch('spotify.utils.load')
    def test_load(self, load_mock, lib_mock):
        lib_mock.sp_image_add_load_callback.return_value = int(
            spotify.ErrorType.OK)
        sp_image = spotify.ffi.cast('sp_image *', 42)
        image = spotify.Image(self.session, sp_image=sp_image)

        image.load(10)

        load_mock.assert_called_with(self.session, image, timeout=10)

    def test_format(self, lib_mock):
        lib_mock.sp_image_is_loaded.return_value = 1
        lib_mock.sp_image_format.return_value = int(spotify.ImageFormat.JPEG)
        lib_mock.sp_image_add_load_callback.return_value = int(
            spotify.ErrorType.OK)
        sp_image = spotify.ffi.cast('sp_image *', 42)
        image = spotify.Image(self.session, sp_image=sp_image)

        result = image.format

        lib_mock.sp_image_format.assert_called_with(sp_image)
        self.assertIs(result, spotify.ImageFormat.JPEG)

    def test_format_is_none_if_unloaded(self, lib_mock):
        lib_mock.sp_image_is_loaded.return_value = 0
        lib_mock.sp_image_add_load_callback.return_value = int(
            spotify.ErrorType.OK)
        sp_image = spotify.ffi.cast('sp_image *', 42)
        image = spotify.Image(self.session, sp_image=sp_image)

        result = image.format

        lib_mock.sp_image_is_loaded.assert_called_with(sp_image)
        self.assertIsNone(result)

    def test_data(self, lib_mock):
        lib_mock.sp_image_is_loaded.return_value = 1

        size = 20
        data = spotify.ffi.new('char[]', size)
        data[0:3] = [b'a', b'b', b'c']

        def func(sp_image_ptr, data_size_ptr):
            data_size_ptr[0] = size
            return spotify.ffi.cast('void *', data)

        lib_mock.sp_image_data.side_effect = func
        lib_mock.sp_image_add_load_callback.return_value = int(
            spotify.ErrorType.OK)
        sp_image = spotify.ffi.cast('sp_image *', 42)
        image = spotify.Image(self.session, sp_image=sp_image)

        result = image.data

        lib_mock.sp_image_data.assert_called_with(sp_image, mock.ANY)
        self.assertEqual(result[:5], b'abc\x00\x00')

    def test_data_is_none_if_unloaded(self, lib_mock):
        lib_mock.sp_image_is_loaded.return_value = 0
        lib_mock.sp_image_add_load_callback.return_value = int(
            spotify.ErrorType.OK)
        sp_image = spotify.ffi.cast('sp_image *', 42)
        image = spotify.Image(self.session, sp_image=sp_image)

        result = image.data

        lib_mock.sp_image_is_loaded.assert_called_with(sp_image)
        self.assertIsNone(result)

    def test_data_uri(self, lib_mock):
        lib_mock.sp_image_format.return_value = int(spotify.ImageFormat.JPEG)
        lib_mock.sp_image_add_load_callback.return_value = int(
            spotify.ErrorType.OK)
        sp_image = spotify.ffi.cast('sp_image *', 42)

        prop_mock = mock.PropertyMock()
        with mock.patch.object(spotify.Image, 'data', prop_mock):
            image = spotify.Image(self.session, sp_image=sp_image)
            prop_mock.return_value = b'01234\x006789'

            result = image.data_uri

        self.assertEqual(result, 'data:image/jpeg;base64,MDEyMzQANjc4OQ==')

    def test_data_uri_is_none_if_unloaded(self, lib_mock):
        lib_mock.sp_image_is_loaded.return_value = 0
        lib_mock.sp_image_add_load_callback.return_value = int(
            spotify.ErrorType.OK)
        sp_image = spotify.ffi.cast('sp_image *', 42)
        image = spotify.Image(self.session, sp_image=sp_image)

        result = image.data_uri

        self.assertIsNone(result)

    def test_data_uri_fails_if_unknown_image_format(self, lib_mock):
        lib_mock.sp_image_add_load_callback.return_value = int(
            spotify.ErrorType.OK)
        sp_image = spotify.ffi.cast('sp_image *', 42)
        image = spotify.Image(self.session, sp_image=sp_image)
        image.__dict__['format'] = mock.Mock(
            return_value=spotify.ImageFormat.UNKNOWN)
        image.__dict__['data'] = mock.Mock(return_value=b'01234\x006789')

        with self.assertRaises(ValueError):
            image.data_uri

    @mock.patch('spotify.Link', spec=spotify.Link)
    def test_link_creates_link_to_image(self, link_mock, lib_mock):
        lib_mock.sp_image_add_load_callback.return_value = int(
            spotify.ErrorType.OK)
        sp_image = spotify.ffi.cast('sp_image *', 42)
        image = spotify.Image(self.session, sp_image=sp_image)
        sp_link = spotify.ffi.cast('sp_link *', 43)
        lib_mock.sp_link_create_from_image.return_value = sp_link
        link_mock.return_value = mock.sentinel.link

        result = image.link

        link_mock.assert_called_once_with(
            self.session, sp_link=sp_link, add_ref=False)
        self.assertEqual(result, mock.sentinel.link)


class ImageFormatTest(unittest.TestCase):

    def test_has_constants(self):
        self.assertEqual(spotify.ImageFormat.UNKNOWN, -1)
        self.assertEqual(spotify.ImageFormat.JPEG, 0)


class ImageSizeTest(unittest.TestCase):

    def test_has_size_constants(self):
        self.assertEqual(spotify.ImageSize.NORMAL, 0)
        self.assertEqual(spotify.ImageSize.SMALL, 1)
        self.assertEqual(spotify.ImageSize.LARGE, 2)

########NEW FILE########
__FILENAME__ = test_inbox
# encoding: utf-8

from __future__ import unicode_literals

import unittest

import spotify
import tests
from tests import mock


@mock.patch('spotify.inbox.lib', spec=spotify.lib)
class InboxPostResultTest(unittest.TestCase):

    def setUp(self):
        self.session = tests.create_session_mock()
        spotify._session_instance = self.session

    def tearDown(self):
        spotify._session_instance = None

    def test_create_without_user_and_tracks_or_sp_inbox_fails(self, lib_mock):
        with self.assertRaises(AssertionError):
            spotify.InboxPostResult(self.session)

    def test_adds_ref_to_sp_inbox_when_created(self, lib_mock):
        sp_inbox = spotify.ffi.cast('sp_inbox *', 42)

        spotify.InboxPostResult(self.session, sp_inbox=sp_inbox)

        lib_mock.sp_inbox_add_ref.assert_called_with(sp_inbox)

    def test_releases_sp_inbox_when_result_dies(self, lib_mock):
        sp_inbox = spotify.ffi.cast('sp_inbox *', 42)

        inbox_post_result = spotify.InboxPostResult(
            self.session, sp_inbox=sp_inbox)
        inbox_post_result = None  # noqa
        tests.gc_collect()

        lib_mock.sp_inbox_release.assert_called_with(sp_inbox)

    @mock.patch('spotify.track.lib', spec=spotify.lib)
    def test_inbox_post_tracks(self, track_lib_mock, lib_mock):
        sp_track1 = spotify.ffi.cast('sp_track *', 43)
        track1 = spotify.Track(self.session, sp_track=sp_track1)
        sp_track2 = spotify.ffi.cast('sp_track *', 44)
        track2 = spotify.Track(self.session, sp_track=sp_track2)
        sp_inbox = spotify.ffi.cast('sp_inbox *', 42)
        lib_mock.sp_inbox_post_tracks.return_value = sp_inbox

        result = spotify.InboxPostResult(
            self.session, 'alice', [track1, track2], '♥')

        lib_mock.sp_inbox_post_tracks.assert_called_with(
            self.session._sp_session, mock.ANY, mock.ANY, 2, mock.ANY,
            mock.ANY, mock.ANY)
        self.assertEqual(
            spotify.ffi.string(lib_mock.sp_inbox_post_tracks.call_args[0][1]),
            b'alice')
        self.assertIn(
            sp_track1, lib_mock.sp_inbox_post_tracks.call_args[0][2])
        self.assertIn(
            sp_track2, lib_mock.sp_inbox_post_tracks.call_args[0][2])
        self.assertEqual(
            spotify.ffi.string(lib_mock.sp_inbox_post_tracks.call_args[0][4]),
            b'\xe2\x99\xa5')
        self.assertIsInstance(result, spotify.InboxPostResult)
        self.assertEqual(result._sp_inbox, sp_inbox)

        self.assertFalse(result.loaded_event.is_set())
        inboxpost_complete_cb = lib_mock.sp_inbox_post_tracks.call_args[0][5]
        userdata = lib_mock.sp_inbox_post_tracks.call_args[0][6]
        inboxpost_complete_cb(sp_inbox, userdata)
        self.assertTrue(result.loaded_event.wait(3))

    @mock.patch('spotify.track.lib', spec=spotify.lib)
    def test_inbox_post_with_single_track(self, track_lib_mock, lib_mock):
        sp_track1 = spotify.ffi.cast('sp_track *', 43)
        track1 = spotify.Track(self.session, sp_track=sp_track1)
        sp_inbox = spotify.ffi.cast('sp_inbox *', 42)
        lib_mock.sp_inbox_post_tracks.return_value = sp_inbox

        result = spotify.InboxPostResult(
            self.session, 'alice', track1, 'Enjoy!')

        lib_mock.sp_inbox_post_tracks.assert_called_with(
            self.session._sp_session, mock.ANY, mock.ANY, 1, mock.ANY,
            mock.ANY, mock.ANY)
        self.assertIn(
            sp_track1, lib_mock.sp_inbox_post_tracks.call_args[0][2])
        self.assertIsInstance(result, spotify.InboxPostResult)
        self.assertEqual(result._sp_inbox, sp_inbox)

    @mock.patch('spotify.track.lib', spec=spotify.lib)
    def test_inbox_post_with_callback(self, track_lib_mock, lib_mock):
        sp_track1 = spotify.ffi.cast('sp_track *', 43)
        track1 = spotify.Track(self.session, sp_track=sp_track1)
        sp_track2 = spotify.ffi.cast('sp_track *', 44)
        track2 = spotify.Track(self.session, sp_track=sp_track2)
        sp_inbox = spotify.ffi.cast('sp_inbox *', 42)
        lib_mock.sp_inbox_post_tracks.return_value = sp_inbox
        callback = mock.Mock()

        result = spotify.InboxPostResult(
            self.session, 'alice', [track1, track2], callback=callback)

        inboxpost_complete_cb = lib_mock.sp_inbox_post_tracks.call_args[0][5]
        userdata = lib_mock.sp_inbox_post_tracks.call_args[0][6]
        inboxpost_complete_cb(sp_inbox, userdata)

        result.loaded_event.wait(3)
        callback.assert_called_with(result)

    @mock.patch('spotify.track.lib', spec=spotify.lib)
    def test_inbox_post_where_result_is_gone_before_callback_is_called(
            self, track_lib_mock, lib_mock):

        sp_track1 = spotify.ffi.cast('sp_track *', 43)
        track1 = spotify.Track(self.session, sp_track=sp_track1)
        sp_track2 = spotify.ffi.cast('sp_track *', 44)
        track2 = spotify.Track(self.session, sp_track=sp_track2)
        sp_inbox = spotify.ffi.cast('sp_inbox *', 42)
        lib_mock.sp_inbox_post_tracks.return_value = sp_inbox
        callback = mock.Mock()

        result = spotify.InboxPostResult(
            self.session, 'alice', [track1, track2], callback=callback)
        loaded_event = result.loaded_event
        result = None  # noqa
        tests.gc_collect()

        # The mock keeps the handle/userdata alive, thus this test doesn't
        # really test that session._callback_handles keeps the handle alive.
        inboxpost_complete_cb = lib_mock.sp_inbox_post_tracks.call_args[0][5]
        userdata = lib_mock.sp_inbox_post_tracks.call_args[0][6]
        inboxpost_complete_cb(sp_inbox, userdata)

        loaded_event.wait(3)
        self.assertEqual(callback.call_count, 1)
        self.assertEqual(callback.call_args[0][0]._sp_inbox, sp_inbox)

    @mock.patch('spotify.track.lib', spec=spotify.lib)
    def test_fail_to_init_raises_error(self, track_lib_mock, lib_mock):
        sp_track1 = spotify.ffi.cast('sp_track *', 43)
        track1 = spotify.Track(self.session, sp_track=sp_track1)
        sp_track2 = spotify.ffi.cast('sp_track *', 44)
        track2 = spotify.Track(self.session, sp_track=sp_track2)
        lib_mock.sp_inbox_post_tracks.return_value = spotify.ffi.NULL

        with self.assertRaises(spotify.Error):
            spotify.InboxPostResult(
                self.session, 'alice', [track1, track2], 'Enjoy!')

    def test_repr(self, lib_mock):
        sp_inbox = spotify.ffi.cast('sp_inbox *', 42)
        inbox_post_result = spotify.InboxPostResult(
            self.session, sp_inbox=sp_inbox)

        self.assertEqual(repr(inbox_post_result), 'InboxPostResult(<pending>)')

        inbox_post_result.loaded_event.set()
        lib_mock.sp_inbox_error.return_value = int(
            spotify.ErrorType.INBOX_IS_FULL)

        self.assertEqual(
            repr(inbox_post_result), 'InboxPostResult(INBOX_IS_FULL)')

        lib_mock.sp_inbox_error.return_value = int(spotify.ErrorType.OK)

        self.assertEqual(repr(inbox_post_result), 'InboxPostResult(OK)')

    def test_eq(self, lib_mock):
        sp_inbox = spotify.ffi.cast('sp_inbox *', 42)
        inbox1 = spotify.InboxPostResult(self.session, sp_inbox=sp_inbox)
        inbox2 = spotify.InboxPostResult(self.session, sp_inbox=sp_inbox)

        self.assertTrue(inbox1 == inbox2)
        self.assertFalse(inbox1 == 'foo')

    def test_ne(self, lib_mock):
        sp_inbox = spotify.ffi.cast('sp_inbox *', 42)
        inbox1 = spotify.InboxPostResult(self.session, sp_inbox=sp_inbox)
        inbox2 = spotify.InboxPostResult(self.session, sp_inbox=sp_inbox)

        self.assertFalse(inbox1 != inbox2)

    def test_hash(self, lib_mock):
        sp_inbox = spotify.ffi.cast('sp_inbox *', 42)
        inbox1 = spotify.InboxPostResult(self.session, sp_inbox=sp_inbox)
        inbox2 = spotify.InboxPostResult(self.session, sp_inbox=sp_inbox)

        self.assertEqual(hash(inbox1), hash(inbox2))

    def test_error(self, lib_mock):
        lib_mock.sp_inbox_error.return_value = int(
            spotify.ErrorType.INBOX_IS_FULL)
        sp_inbox = spotify.ffi.cast('sp_inbox *', 42)
        inbox_post_result = spotify.InboxPostResult(
            self.session, sp_inbox=sp_inbox)

        result = inbox_post_result.error

        lib_mock.sp_inbox_error.assert_called_once_with(sp_inbox)
        self.assertIs(result, spotify.ErrorType.INBOX_IS_FULL)

########NEW FILE########
__FILENAME__ = test_lib
from __future__ import unicode_literals

import unittest

import spotify


class LibTest(unittest.TestCase):
    def test_sp_error_message(self):
        self.assertEqual(
            spotify.ffi.string(spotify.lib.sp_error_message(0)),
            b'No error')

    def test_SPOTIFY_API_VERSION_macro(self):
        self.assertEqual(spotify.lib.SPOTIFY_API_VERSION, 12)

########NEW FILE########
__FILENAME__ = test_link
from __future__ import unicode_literals

import unittest

import spotify
import tests
from tests import mock


@mock.patch('spotify.link.lib', spec=spotify.lib)
class LinkTest(unittest.TestCase):

    def setUp(self):
        self.session = tests.create_session_mock()

    def test_create_without_uri_or_obj_or_sp_link_fails(self, lib_mock):
        with self.assertRaises(AssertionError):
            spotify.Link(self.session)

    def test_create_from_sp_link(self, lib_mock):
        sp_link = spotify.ffi.cast('sp_link *', 42)

        result = spotify.Link(self.session, sp_link=sp_link)

        self.assertEqual(result._sp_link, sp_link)

    def test_create_from_uri(self, lib_mock):
        sp_link = spotify.ffi.cast('sp_link *', 42)
        lib_mock.sp_link_create_from_string.return_value = sp_link

        spotify.Link(self.session, 'spotify:track:foo')

        lib_mock.sp_link_create_from_string.assert_called_once_with(
            mock.ANY)
        self.assertEqual(
            spotify.ffi.string(
                lib_mock.sp_link_create_from_string.call_args[0][0]),
            b'spotify:track:foo')
        self.assertEqual(lib_mock.sp_link_add_ref.call_count, 0)

    def test_create_from_open_spotify_com_url(self, lib_mock):
        sp_link = spotify.ffi.cast('sp_link *', 42)
        lib_mock.sp_link_create_from_string.return_value = sp_link

        spotify.Link(
            self.session,
            'http://open.spotify.com/track/bar ')

        lib_mock.sp_link_create_from_string.assert_called_once_with(
            mock.ANY)
        self.assertEqual(
            spotify.ffi.string(
                lib_mock.sp_link_create_from_string.call_args[0][0]),
            b'spotify:track:bar')

    def test_create_from_play_spotify_com_url(self, lib_mock):
        sp_link = spotify.ffi.cast('sp_link *', 42)
        lib_mock.sp_link_create_from_string.return_value = sp_link

        spotify.Link(
            self.session,
            'https://play.spotify.com/track/bar?gurba=123')

        lib_mock.sp_link_create_from_string.assert_called_once_with(
            mock.ANY)
        self.assertEqual(
            spotify.ffi.string(
                lib_mock.sp_link_create_from_string.call_args[0][0]),
            b'spotify:track:bar')

    def test_raises_error_if_string_isnt_parseable(self, lib_mock):
        lib_mock.sp_link_create_from_string.return_value = spotify.ffi.NULL

        with self.assertRaises(ValueError):
            spotify.Link(self.session, 'invalid link string')

    def test_releases_sp_link_when_link_dies(self, lib_mock):
        sp_link = spotify.ffi.cast('sp_link *', 42)
        lib_mock.sp_link_create_from_string.return_value = sp_link

        link = spotify.Link(self.session, 'spotify:track:foo')
        link = None  # noqa
        tests.gc_collect()

        lib_mock.sp_link_release.assert_called_with(sp_link)

    def test_repr(self, lib_mock):
        sp_link = spotify.ffi.cast('sp_link *', 42)
        lib_mock.sp_link_create_from_string.return_value = sp_link
        string = 'foo'

        lib_mock.sp_link_as_string.side_effect = tests.buffer_writer(string)
        link = spotify.Link(self.session, string)

        result = repr(link)

        self.assertEqual(result, 'Link(%r)' % string)

    def test_str(self, lib_mock):
        sp_link = spotify.ffi.cast('sp_link *', 42)
        lib_mock.sp_link_create_from_string.return_value = sp_link
        string = 'foo'

        lib_mock.sp_link_as_string.side_effect = tests.buffer_writer(string)
        link = spotify.Link(self.session, string)

        self.assertEqual(str(link), link.uri)

    def test_eq(self, lib_mock):
        sp_link = spotify.ffi.cast('sp_link *', 42)
        link1 = spotify.Link(self.session, sp_link=sp_link)
        link2 = spotify.Link(self.session, sp_link=sp_link)

        self.assertTrue(link1 == link2)
        self.assertFalse(link1 == 'foo')

    def test_ne(self, lib_mock):
        sp_link = spotify.ffi.cast('sp_link *', 42)
        link1 = spotify.Link(self.session, sp_link=sp_link)
        link2 = spotify.Link(self.session, sp_link=sp_link)

        self.assertFalse(link1 != link2)

    def test_hash(self, lib_mock):
        sp_link = spotify.ffi.cast('sp_link *', 42)
        link1 = spotify.Link(self.session, sp_link=sp_link)
        link2 = spotify.Link(self.session, sp_link=sp_link)

        self.assertEqual(hash(link1), hash(link2))

    def test_uri_grows_buffer_to_fit_link(self, lib_mock):
        sp_link = spotify.ffi.cast('sp_link *', 42)
        lib_mock.sp_link_create_from_string.return_value = sp_link
        string = 'foo' * 100

        lib_mock.sp_link_as_string.side_effect = tests.buffer_writer(string)
        link = spotify.Link(self.session, string)

        result = link.uri

        lib_mock.sp_link_as_string.assert_called_with(
            sp_link, mock.ANY, mock.ANY)
        self.assertEqual(result, string)

    def test_url_expands_uri_to_http_url(self, lib_mock):
        sp_link = spotify.ffi.cast('sp_link *', 42)
        lib_mock.sp_link_create_from_string.return_value = sp_link
        string = 'spotify:track:foo'
        lib_mock.sp_link_as_string.side_effect = tests.buffer_writer(string)
        link = spotify.Link(self.session, string)

        result = link.url

        self.assertEqual(result, 'https://open.spotify.com/track/foo')

    def test_type(self, lib_mock):
        sp_link = spotify.ffi.cast('sp_link *', 42)
        lib_mock.sp_link_create_from_string.return_value = sp_link
        lib_mock.sp_link_type.return_value = 1
        link = spotify.Link(self.session, 'spotify:track:foo')

        self.assertIs(link.type, spotify.LinkType.TRACK)

        lib_mock.sp_link_type.assert_called_once_with(sp_link)

    @mock.patch('spotify.track.lib', spec=spotify.lib)
    def test_as_track(self, track_lib_mock, lib_mock):
        sp_link = spotify.ffi.cast('sp_link *', 42)
        lib_mock.sp_link_create_from_string.return_value = sp_link
        sp_track = spotify.ffi.cast('sp_track *', 43)
        lib_mock.sp_link_as_track.return_value = sp_track

        link = spotify.Link(self.session, 'spotify:track:foo')
        self.assertEqual(link.as_track()._sp_track, sp_track)

        lib_mock.sp_link_as_track.assert_called_once_with(sp_link)

    @mock.patch('spotify.track.lib', spec=spotify.lib)
    def test_as_track_if_not_a_track(self, track_lib_mock, lib_mock):
        sp_link = spotify.ffi.cast('sp_link *', 42)
        lib_mock.sp_link_create_from_string.return_value = sp_link
        lib_mock.sp_link_as_track.return_value = spotify.ffi.NULL

        link = spotify.Link(self.session, 'spotify:track:foo')
        self.assertIsNone(link.as_track())

        lib_mock.sp_link_as_track.assert_called_once_with(sp_link)

    @mock.patch('spotify.track.lib', spec=spotify.lib)
    def test_as_track_with_offset(self, track_lib_mock, lib_mock):
        sp_link = spotify.ffi.cast('sp_link *', 42)
        lib_mock.sp_link_create_from_string.return_value = sp_link
        sp_track = spotify.ffi.cast('sp_track *', 43)

        def func(sp_link, offset_ptr):
            offset_ptr[0] = 90
            return sp_track

        lib_mock.sp_link_as_track_and_offset.side_effect = func

        link = spotify.Link(self.session, 'spotify:track:foo')
        offset = link.as_track_offset()

        self.assertEqual(offset, 90)
        lib_mock.sp_link_as_track_and_offset.assert_called_once_with(
            sp_link, mock.ANY)

    @mock.patch('spotify.track.lib', spec=spotify.lib)
    def test_as_track_with_offset_if_not_a_track(
            self, track_lib_mock, lib_mock):
        sp_link = spotify.ffi.cast('sp_link *', 42)
        lib_mock.sp_link_create_from_string.return_value = sp_link
        lib_mock.sp_link_as_track_and_offset.return_value = spotify.ffi.NULL

        link = spotify.Link(self.session, 'spotify:track:foo')
        offset = link.as_track_offset()

        self.assertIsNone(offset)
        lib_mock.sp_link_as_track_and_offset.assert_called_once_with(
            sp_link, mock.ANY)

    @mock.patch('spotify.album.lib', spec=spotify.lib)
    def test_as_album(self, album_lib_mock, lib_mock):
        sp_link = spotify.ffi.cast('sp_link *', 42)
        lib_mock.sp_link_create_from_string.return_value = sp_link
        sp_album = spotify.ffi.cast('sp_album *', 43)
        lib_mock.sp_link_as_album.return_value = sp_album

        link = spotify.Link(self.session, 'spotify:album:foo')
        self.assertEqual(link.as_album()._sp_album, sp_album)

        lib_mock.sp_link_as_album.assert_called_once_with(sp_link)

    @mock.patch('spotify.album.lib', spec=spotify.lib)
    def test_as_album_if_not_an_album(self, album_lib_mock, lib_mock):
        sp_link = spotify.ffi.cast('sp_link *', 42)
        lib_mock.sp_link_create_from_string.return_value = sp_link
        lib_mock.sp_link_as_album.return_value = spotify.ffi.NULL

        link = spotify.Link(self.session, 'spotify:album:foo')
        self.assertIsNone(link.as_album())

        lib_mock.sp_link_as_album.assert_called_once_with(sp_link)

    @mock.patch('spotify.artist.lib', spec=spotify.lib)
    def test_as_artist(self, artist_lib_mock, lib_mock):
        sp_link = spotify.ffi.cast('sp_link *', 42)
        lib_mock.sp_link_create_from_string.return_value = sp_link
        sp_artist = spotify.ffi.cast('sp_artist *', 43)
        lib_mock.sp_link_as_artist.return_value = sp_artist

        link = spotify.Link(self.session, 'spotify:artist:foo')
        self.assertEqual(link.as_artist()._sp_artist, sp_artist)

        lib_mock.sp_link_as_artist.assert_called_once_with(sp_link)

    @mock.patch('spotify.artist.lib', spec=spotify.lib)
    def test_as_artist_if_not_an_artist(self, artist_lib_mock, lib_mock):
        sp_link = spotify.ffi.cast('sp_link *', 42)
        lib_mock.sp_link_create_from_string.return_value = sp_link
        lib_mock.sp_link_as_artist.return_value = spotify.ffi.NULL

        link = spotify.Link(self.session, 'spotify:artist:foo')
        self.assertIsNone(link.as_artist())

        lib_mock.sp_link_as_artist.assert_called_once_with(sp_link)

    @mock.patch('spotify.playlist.lib', spec=spotify.lib)
    def test_as_playlist(self, playlist_lib_mock, lib_mock):
        sp_link = spotify.ffi.cast('sp_link *', 42)
        lib_mock.sp_link_create_from_string.return_value = sp_link
        lib_mock.sp_link_type.return_value = spotify.LinkType.PLAYLIST
        sp_playlist = spotify.ffi.cast('sp_playlist *', 43)
        lib_mock.sp_playlist_create.return_value = sp_playlist

        link = spotify.Link(self.session, 'spotify:playlist:foo')
        self.assertEqual(link.as_playlist()._sp_playlist, sp_playlist)

        lib_mock.sp_playlist_create.assert_called_once_with(
            self.session._sp_session, sp_link)

        # Since we *created* the sp_playlist, we already have a refcount of 1
        # and shouldn't increase the refcount when wrapping this sp_playlist in
        # an Playlist object
        self.assertEqual(playlist_lib_mock.sp_playlist_add_ref.call_count, 0)

    @mock.patch('spotify.playlist.lib', spec=spotify.lib)
    def test_as_playlist_if_not_a_playlist(self, playlist_lib_mock, lib_mock):
        sp_link = spotify.ffi.cast('sp_link *', 42)
        lib_mock.sp_link_create_from_string.return_value = sp_link
        lib_mock.sp_link_type.return_value = spotify.LinkType.ARTIST

        link = spotify.Link(self.session, 'spotify:playlist:foo')
        self.assertIsNone(link.as_playlist())

        self.assertEqual(lib_mock.sp_playlist_create.call_count, 0)

    @mock.patch('spotify.user.lib', spec=spotify.lib)
    def test_as_user(self, user_lib_mock, lib_mock):
        sp_link = spotify.ffi.cast('sp_link *', 42)
        lib_mock.sp_link_create_from_string.return_value = sp_link
        sp_user = spotify.ffi.cast('sp_user *', 43)
        lib_mock.sp_link_as_user.return_value = sp_user

        link = spotify.Link(self.session, 'spotify:user:foo')
        self.assertEqual(link.as_user()._sp_user, sp_user)

        lib_mock.sp_link_as_user.assert_called_once_with(sp_link)

    @mock.patch('spotify.user.lib', spec=spotify.lib)
    def test_as_user_if_not_a_user(self, user_lib_mock, lib_mock):
        sp_link = spotify.ffi.cast('sp_link *', 42)
        lib_mock.sp_link_create_from_string.return_value = sp_link
        lib_mock.sp_link_as_user.return_value = spotify.ffi.NULL

        link = spotify.Link(self.session, 'spotify:user:foo')
        self.assertIsNone(link.as_user())

        lib_mock.sp_link_as_user.assert_called_once_with(sp_link)

    @mock.patch('spotify.Image', spec=spotify.Image)
    def test_as_image(self, image_mock, lib_mock):
        sp_link = spotify.ffi.cast('sp_link *', 42)
        lib_mock.sp_link_create_from_string.return_value = sp_link
        lib_mock.sp_link_type.return_value = spotify.LinkType.IMAGE
        sp_image = spotify.ffi.cast('sp_image *', 43)
        lib_mock.sp_image_create_from_link.return_value = sp_image
        image_mock.return_value = mock.sentinel.image
        callback = mock.Mock()

        link = spotify.Link(self.session, 'spotify:image:foo')
        result = link.as_image(callback=callback)

        self.assertIs(result, mock.sentinel.image)
        lib_mock.sp_image_create_from_link.assert_called_once_with(
            self.session._sp_session, sp_link)

        # Since we *created* the sp_image, we already have a refcount of 1 and
        # shouldn't increase the refcount when wrapping this sp_image in an
        # Image object
        image_mock.assert_called_with(
            self.session, sp_image=sp_image, add_ref=False, callback=callback)

    def test_as_image_if_not_a_image(self, lib_mock):
        sp_link = spotify.ffi.cast('sp_link *', 42)
        lib_mock.sp_link_create_from_string.return_value = sp_link
        lib_mock.sp_link_type.return_value = spotify.LinkType.ARTIST

        link = spotify.Link(self.session, 'spotify:image:foo')
        result = link.as_image()

        self.assertIsNone(result)
        self.assertEqual(lib_mock.sp_image_create_from_link.call_count, 0)


class LinkTypeTest(unittest.TestCase):

    def test_has_link_type_constants(self):
        self.assertEqual(spotify.LinkType.INVALID, 0)
        self.assertEqual(spotify.LinkType.TRACK, 1)
        self.assertEqual(spotify.LinkType.ALBUM, 2)

########NEW FILE########
__FILENAME__ = test_loadable
from __future__ import unicode_literals

import unittest
import time

import spotify
from spotify.utils import load
import tests
from tests import mock


class Foo(object):

    def __init__(self, session):
        self._session = session

    @property
    def is_loaded(self):
        return True

    def load(self, timeout=None):
        return load(self._session, self, timeout=timeout)


class FooWithError(Foo):
    @property
    def error(self):
        return spotify.Error(spotify.Error.OK)


@mock.patch('spotify.utils.time')
@mock.patch.object(Foo, 'is_loaded', new_callable=mock.PropertyMock)
class LoadableTest(unittest.TestCase):

    def setUp(self):
        self.session = tests.create_session_mock()
        self.session.connection.state = spotify.ConnectionState.LOGGED_IN

    def test_load_raises_error_if_not_logged_in(
            self, is_loaded_mock, time_mock):
        is_loaded_mock.return_value = False
        self.session.connection.state = spotify.ConnectionState.LOGGED_OUT
        foo = Foo(self.session)

        with self.assertRaises(RuntimeError):
            foo.load()

    def test_load_raises_error_if_offline(
            self, is_loaded_mock, time_mock):
        is_loaded_mock.return_value = False
        self.session.connection.state = spotify.ConnectionState.OFFLINE
        foo = Foo(self.session)

        with self.assertRaises(RuntimeError):
            foo.load()

    def test_load_returns_immediately_if_offline_but_already_loaded(
            self, is_loaded_mock, time_mock):
        is_loaded_mock.return_value = True
        self.session.connection.state = spotify.ConnectionState.OFFLINE
        foo = Foo(self.session)

        result = foo.load()

        self.assertEqual(result, foo)
        self.assertEqual(self.session.process_events.call_count, 0)

    def test_load_raises_error_when_timeout_is_reached(
            self, is_loaded_mock, time_mock):
        is_loaded_mock.return_value = False
        time_mock.time.side_effect = time.time
        foo = Foo(self.session)

        with self.assertRaises(spotify.Timeout):
            foo.load(timeout=0)

    def test_load_processes_events_until_loaded(
            self, is_loaded_mock, time_mock):
        is_loaded_mock.side_effect = [False, False, False, False, False, True]
        time_mock.time.side_effect = time.time

        foo = Foo(self.session)
        foo.load()

        self.assertEqual(self.session.process_events.call_count, 2)
        self.assertEqual(time_mock.sleep.call_count, 2)

    @mock.patch.object(FooWithError, 'error', new_callable=mock.PropertyMock)
    def test_load_raises_exception_on_error(
            self, error_mock, is_loaded_mock, time_mock):
        error_mock.side_effect = [
            spotify.ErrorType.IS_LOADING, spotify.ErrorType.OTHER_PERMANENT]
        is_loaded_mock.side_effect = [False, False, True]

        foo = FooWithError(self.session)

        with self.assertRaises(spotify.Error):
            foo.load()

        self.assertEqual(self.session.process_events.call_count, 1)
        self.assertEqual(time_mock.sleep.call_count, 0)

    def test_load_raises_exception_on_error_even_if_already_loaded(
            self, is_loaded_mock, time_mock):
        is_loaded_mock.return_value = True

        foo = Foo(self.session)
        foo.error = spotify.ErrorType.OTHER_PERMANENT

        with self.assertRaises(spotify.Error):
            foo.load()

    def test_load_does_not_abort_on_is_loading_error(
            self, is_loaded_mock, time_mock):
        is_loaded_mock.side_effect = [False, False, False, False, False, True]
        time_mock.time.side_effect = time.time

        foo = Foo(self.session)
        foo.error = spotify.ErrorType.IS_LOADING
        foo.load()

        self.assertEqual(self.session.process_events.call_count, 2)
        self.assertEqual(time_mock.sleep.call_count, 2)

    def test_load_returns_self(self, is_loaded_mock, time_mock):
        is_loaded_mock.return_value = True

        foo = Foo(self.session)
        result = foo.load()

        self.assertEqual(result, foo)

########NEW FILE########
__FILENAME__ = test_offline
from __future__ import unicode_literals

import unittest

import spotify

import tests
from tests import mock


@mock.patch('spotify.offline.lib', spec=spotify.lib)
@mock.patch('spotify.session.lib', spec=spotify.lib)
class OfflineTest(unittest.TestCase):

    def tearDown(self):
        spotify._session_instance = None

    def test_offline_tracks_to_sync(self, session_lib_mock, lib_mock):
        lib_mock.sp_offline_tracks_to_sync.return_value = 17
        session = tests.create_real_session(session_lib_mock)

        result = session.offline.tracks_to_sync

        lib_mock.sp_offline_tracks_to_sync.assert_called_with(
            session._sp_session)
        self.assertEqual(result, 17)

    def test_offline_num_playlists(self, session_lib_mock, lib_mock):
        lib_mock.sp_offline_num_playlists.return_value = 5
        session = tests.create_real_session(session_lib_mock)

        result = session.offline.num_playlists

        lib_mock.sp_offline_num_playlists.assert_called_with(
            session._sp_session)
        self.assertEqual(result, 5)

    def test_offline_sync_status(self, session_lib_mock, lib_mock):
        def func(sp_session_ptr, sp_offline_sync_status):
            sp_offline_sync_status.queued_tracks = 3
            return 1

        lib_mock.sp_offline_sync_get_status.side_effect = func
        session = tests.create_real_session(session_lib_mock)

        result = session.offline.sync_status

        lib_mock.sp_offline_sync_get_status.assert_called_with(
            session._sp_session, mock.ANY)
        self.assertIsInstance(result, spotify.OfflineSyncStatus)
        self.assertEqual(result.queued_tracks, 3)

    def test_offline_sync_status_when_not_syncing(
            self, session_lib_mock, lib_mock):
        lib_mock.sp_offline_sync_get_status.return_value = 0
        session = tests.create_real_session(session_lib_mock)

        result = session.offline.sync_status

        lib_mock.sp_offline_sync_get_status.assert_called_with(
            session._sp_session, mock.ANY)
        self.assertIsNone(result)

    def test_offline_time_left(self, session_lib_mock, lib_mock):
        lib_mock.sp_offline_time_left.return_value = 3600
        session = tests.create_real_session(session_lib_mock)

        result = session.offline.time_left

        lib_mock.sp_offline_time_left.assert_called_with(session._sp_session)
        self.assertEqual(result, 3600)


class OfflineSyncStatusTest(unittest.TestCase):

    def setUp(self):
        self._sp_offline_sync_status = spotify.ffi.new(
            'sp_offline_sync_status *')
        self._sp_offline_sync_status.queued_tracks = 5
        self._sp_offline_sync_status.done_tracks = 16
        self._sp_offline_sync_status.copied_tracks = 27
        self._sp_offline_sync_status.willnotcopy_tracks = 2
        self._sp_offline_sync_status.error_tracks = 3
        self._sp_offline_sync_status.syncing = True

        self.offline_sync_status = spotify.OfflineSyncStatus(
            self._sp_offline_sync_status)

    def test_queued_tracks(self):
        self.assertEqual(self.offline_sync_status.queued_tracks, 5)

    def test_done_tracks(self):
        self.assertEqual(self.offline_sync_status.done_tracks, 16)

    def test_copied_tracks(self):
        self.assertEqual(self.offline_sync_status.copied_tracks, 27)

    def test_willnotcopy_tracks(self):
        self.assertEqual(self.offline_sync_status.willnotcopy_tracks, 2)

    def test_error_tracks(self):
        self.assertEqual(self.offline_sync_status.error_tracks, 3)

    def test_syncing(self):
        self.assertTrue(self.offline_sync_status.syncing)

########NEW FILE########
__FILENAME__ = test_player
from __future__ import unicode_literals

import unittest

import spotify

import tests
from tests import mock


@mock.patch('spotify.player.lib', spec=spotify.lib)
@mock.patch('spotify.session.lib', spec=spotify.lib)
class PlayerTest(unittest.TestCase):

    def tearDown(self):
        spotify._session_instance = None

    @mock.patch('spotify.track.lib', spec=spotify.lib)
    def test_player_load(self, track_lib_mock, session_lib_mock, lib_mock):
        lib_mock.sp_session_player_load.return_value = spotify.ErrorType.OK
        session = tests.create_real_session(session_lib_mock)
        sp_track = spotify.ffi.cast('sp_track *', 42)
        track = spotify.Track(session, sp_track=sp_track)

        session.player.load(track)

        lib_mock.sp_session_player_load.assert_called_once_with(
            session._sp_session, sp_track)

    @mock.patch('spotify.track.lib', spec=spotify.lib)
    def test_player_load_fail_raises_error(
            self, track_lib_mock, session_lib_mock, lib_mock):
        lib_mock.sp_session_player_load.return_value = (
            spotify.ErrorType.TRACK_NOT_PLAYABLE)
        session = tests.create_real_session(session_lib_mock)
        sp_track = spotify.ffi.cast('sp_track *', 42)
        track = spotify.Track(session, sp_track=sp_track)

        with self.assertRaises(spotify.Error):
            session.player.load(track)

    def test_player_seek(self, session_lib_mock, lib_mock):
        lib_mock.sp_session_player_seek.return_value = spotify.ErrorType.OK
        session = tests.create_real_session(session_lib_mock)

        session.player.seek(45000)

        lib_mock.sp_session_player_seek.assert_called_once_with(
            session._sp_session, 45000)

    def test_player_seek_fail_raises_error(self, session_lib_mock, lib_mock):
        lib_mock.sp_session_player_seek.return_value = (
            spotify.ErrorType.BAD_API_VERSION)
        session = tests.create_real_session(session_lib_mock)

        with self.assertRaises(spotify.Error):
            session.player.seek(45000)

    def test_player_play(self, session_lib_mock, lib_mock):
        lib_mock.sp_session_player_play.return_value = spotify.ErrorType.OK
        session = tests.create_real_session(session_lib_mock)

        session.player.play(True)

        lib_mock.sp_session_player_play.assert_called_once_with(
            session._sp_session, 1)

    def test_player_play_with_false_to_pause(self, session_lib_mock, lib_mock):
        lib_mock.sp_session_player_play.return_value = spotify.ErrorType.OK
        session = tests.create_real_session(session_lib_mock)

        session.player.play(False)

        lib_mock.sp_session_player_play.assert_called_once_with(
            session._sp_session, 0)

    def test_player_play_fail_raises_error(self, session_lib_mock, lib_mock):
        lib_mock.sp_session_player_play.return_value = (
            spotify.ErrorType.BAD_API_VERSION)
        session = tests.create_real_session(session_lib_mock)

        with self.assertRaises(spotify.Error):
            session.player.play(True)

    def test_player_pause(self, session_lib_mock, lib_mock):
        lib_mock.sp_session_player_play.return_value = spotify.ErrorType.OK
        session = tests.create_real_session(session_lib_mock)

        session.player.pause()

        lib_mock.sp_session_player_play.assert_called_once_with(
            session._sp_session, 0)

    def test_player_unload(self, session_lib_mock, lib_mock):
        lib_mock.sp_session_player_unload.return_value = spotify.ErrorType.OK
        session = tests.create_real_session(session_lib_mock)

        session.player.unload()

        lib_mock.sp_session_player_unload.assert_called_once_with(
            session._sp_session)

    def test_player_unload_fail_raises_error(self, session_lib_mock, lib_mock):
        lib_mock.sp_session_player_unload.return_value = (
            spotify.ErrorType.BAD_API_VERSION)
        session = tests.create_real_session(session_lib_mock)

        with self.assertRaises(spotify.Error):
            session.player.unload()

    @mock.patch('spotify.track.lib', spec=spotify.lib)
    def test_player_prefetch(self, track_lib_mock, session_lib_mock, lib_mock):
        lib_mock.sp_session_player_prefetch.return_value = spotify.ErrorType.OK
        session = tests.create_real_session(session_lib_mock)
        sp_track = spotify.ffi.cast('sp_track *', 42)
        track = spotify.Track(session, sp_track=sp_track)

        session.player.prefetch(track)

        lib_mock.sp_session_player_prefetch.assert_called_once_with(
            session._sp_session, sp_track)

    @mock.patch('spotify.track.lib', spec=spotify.lib)
    def test_player_prefetch_fail_raises_error(
            self, track_lib_mock, session_lib_mock, lib_mock):
        lib_mock.sp_session_player_prefetch.return_value = (
            spotify.ErrorType.NO_CACHE)
        session = tests.create_real_session(session_lib_mock)
        sp_track = spotify.ffi.cast('sp_track *', 42)
        track = spotify.Track(session, sp_track=sp_track)

        with self.assertRaises(spotify.Error):
            session.player.prefetch(track)

########NEW FILE########
__FILENAME__ = test_playlist
# encoding: utf-8

from __future__ import unicode_literals

import collections
import unittest

import spotify
from spotify.playlist import _PlaylistCallbacks
import tests
from tests import mock


@mock.patch('spotify.playlist.lib', spec=spotify.lib)
class PlaylistTest(unittest.TestCase):

    def setUp(self):
        self.session = tests.create_session_mock()

    def test_create_without_uri_or_sp_playlist_fails(self, lib_mock):
        with self.assertRaises(AssertionError):
            spotify.Playlist(self.session)

    @mock.patch('spotify.Link', spec=spotify.Link)
    def test_create_from_uri(self, link_mock, lib_mock):
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        link_instance_mock = link_mock.return_value
        link_instance_mock.as_playlist.return_value = spotify.Playlist(
            self.session, sp_playlist=sp_playlist)
        uri = 'spotify:playlist:foo'

        result = spotify.Playlist(self.session, uri=uri)

        link_mock.assert_called_with(self.session, uri)
        link_instance_mock.as_playlist.assert_called_with()
        lib_mock.sp_playlist_add_ref.assert_called_with(sp_playlist)
        self.assertEqual(result._sp_playlist, sp_playlist)

    @mock.patch('spotify.Link', spec=spotify.Link)
    def test_create_from_uri_is_cached(self, link_mock, lib_mock):
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        link_instance_mock = link_mock.return_value
        link_instance_mock.as_playlist.return_value = spotify.Playlist(
            self.session, sp_playlist=sp_playlist)
        uri = 'spotify:playlist:foo'

        result = spotify.Playlist(self.session, uri=uri)

        self.assertEqual(self.session._cache[sp_playlist], result)

    @mock.patch('spotify.Link', spec=spotify.Link)
    def test_create_from_uri_fail_raises_error(self, link_mock, lib_mock):
        link_instance_mock = link_mock.return_value
        link_instance_mock.as_playlist.return_value = None
        uri = 'spotify:playlist:foo'

        with self.assertRaises(spotify.Error):
            spotify.Playlist(self.session, uri=uri)

    def test_life_cycle(self, lib_mock):
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)

        playlist = spotify.Playlist(self.session, sp_playlist=sp_playlist)
        sp_playlist = playlist._sp_playlist

        lib_mock.sp_playlist_add_ref.assert_called_with(sp_playlist)
        lib_mock.sp_playlist_add_callbacks.assert_called_with(
            sp_playlist, mock.ANY, mock.ANY)

        playlist = None  # noqa
        tests.gc_collect()

        lib_mock.sp_playlist_remove_callbacks.assert_called_with(
            sp_playlist, mock.ANY, mock.ANY)
        # FIXME Won't be called because lib_mock has references to the
        # sp_playlist object, and it thus won't be GC-ed.
        # lib_mock.sp_playlist_release.assert_called_with(sp_playlist)

    def test_cached_playlist(self, lib_mock):
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)

        result1 = spotify.Playlist._cached(self.session, sp_playlist)
        result2 = spotify.Playlist._cached(self.session, sp_playlist)

        self.assertIsInstance(result1, spotify.Playlist)
        self.assertIs(result1, result2)

    @mock.patch('spotify.Link', spec=spotify.Link)
    def test_repr(self, link_mock, lib_mock):
        lib_mock.sp_playlist_is_loaded.return_value = 1
        link_instance_mock = link_mock.return_value
        link_instance_mock.uri = 'foo'
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist = spotify.Playlist(self.session, sp_playlist=sp_playlist)

        result = repr(playlist)

        self.assertEqual(result, 'Playlist(%r)' % 'foo')

    @mock.patch('spotify.Link', spec=spotify.Link)
    def test_repr_if_unloaded(self, link_mock, lib_mock):
        lib_mock.sp_playlist_is_loaded.return_value = 0
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist = spotify.Playlist(self.session, sp_playlist=sp_playlist)

        result = repr(playlist)

        self.assertEqual(result, 'Playlist(<not loaded>)')

    @mock.patch('spotify.Link', spec=spotify.Link)
    def test_repr_if_link_creation_fails(self, link_mock, lib_mock):
        lib_mock.sp_playlist_is_loaded.return_value = 1
        link_mock.side_effect = spotify.Error('error message')
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist = spotify.Playlist(self.session, sp_playlist=sp_playlist)

        result = repr(playlist)

        self.assertEqual(result, 'Playlist(<error: error message>)')

    def test_eq(self, lib_mock):
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist1 = spotify.Playlist(self.session, sp_playlist=sp_playlist)
        playlist2 = spotify.Playlist(self.session, sp_playlist=sp_playlist)

        self.assertTrue(playlist1 == playlist2)
        self.assertFalse(playlist1 == 'foo')

    def test_ne(self, lib_mock):
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist1 = spotify.Playlist(self.session, sp_playlist=sp_playlist)
        playlist2 = spotify.Playlist(self.session, sp_playlist=sp_playlist)

        self.assertFalse(playlist1 != playlist2)

    def test_hash(self, lib_mock):
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist1 = spotify.Playlist(self.session, sp_playlist=sp_playlist)
        playlist2 = spotify.Playlist(self.session, sp_playlist=sp_playlist)

        self.assertEqual(hash(playlist1), hash(playlist2))

    def test_is_loaded(self, lib_mock):
        lib_mock.sp_playlist_is_loaded.return_value = 1
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist = spotify.Playlist(self.session, sp_playlist=sp_playlist)

        result = playlist.is_loaded

        lib_mock.sp_playlist_is_loaded.assert_called_once_with(sp_playlist)
        self.assertTrue(result)

    @mock.patch('spotify.utils.load')
    def test_load(self, load_mock, lib_mock):
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist = spotify.Playlist(self.session, sp_playlist=sp_playlist)

        playlist.load(10)

        load_mock.assert_called_with(self.session, playlist, timeout=10)

    @mock.patch('spotify.track.lib', spec=spotify.lib)
    def test_tracks(self, track_lib_mock, lib_mock):
        sp_track = spotify.ffi.cast('sp_track *', 43)
        lib_mock.sp_playlist_num_tracks.return_value = 1
        lib_mock.sp_playlist_track.return_value = sp_track
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist = spotify.Playlist(self.session, sp_playlist=sp_playlist)

        self.assertEqual(lib_mock.sp_playlist_add_ref.call_count, 1)
        result = playlist.tracks
        self.assertEqual(lib_mock.sp_playlist_add_ref.call_count, 2)

        self.assertEqual(len(result), 1)
        lib_mock.sp_playlist_num_tracks.assert_called_with(sp_playlist)

        item = result[0]
        self.assertIsInstance(item, spotify.Track)
        self.assertEqual(item._sp_track, sp_track)
        self.assertEqual(lib_mock.sp_playlist_track.call_count, 1)
        lib_mock.sp_playlist_track.assert_called_with(sp_playlist, 0)
        track_lib_mock.sp_track_add_ref.assert_called_with(sp_track)

    def test_tracks_if_no_tracks(self, lib_mock):
        lib_mock.sp_playlist_num_tracks.return_value = 0
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist = spotify.Playlist(self.session, sp_playlist=sp_playlist)

        result = playlist.tracks

        self.assertEqual(len(result), 0)
        lib_mock.sp_playlist_num_tracks.assert_called_with(sp_playlist)
        self.assertEqual(lib_mock.sp_playlist_track.call_count, 0)

    def test_tracks_if_unloaded(self, lib_mock):
        lib_mock.sp_playlist_is_loaded.return_value = 0
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist = spotify.Playlist(self.session, sp_playlist=sp_playlist)

        result = playlist.tracks

        lib_mock.sp_playlist_is_loaded.assert_called_with(sp_playlist)
        self.assertEqual(len(result), 0)

    def test_tracks_is_a_mutable_sequence(self, lib_mock):
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist = spotify.Playlist(self.session, sp_playlist=sp_playlist)

        self.assertIsInstance(playlist.tracks, collections.MutableSequence)

    def test_tracks_setitem(self, lib_mock):
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist = spotify.Playlist(self.session, sp_playlist=sp_playlist)
        tracks = playlist.tracks
        tracks.__len__ = mock.Mock(return_value=5)
        playlist.remove_tracks = mock.Mock()
        playlist.add_tracks = mock.Mock()

        tracks[0] = mock.sentinel.track

        playlist.add_tracks.assert_called_with(mock.sentinel.track, index=0)
        playlist.remove_tracks.assert_called_with(1)

    def test_tracks_setitem_with_slice(self, lib_mock):
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist = spotify.Playlist(self.session, sp_playlist=sp_playlist)
        tracks = playlist.tracks
        tracks.__len__ = mock.Mock(return_value=5)
        playlist.remove_tracks = mock.Mock()
        playlist.add_tracks = mock.Mock()

        tracks[0:2] = [mock.sentinel.track1, mock.sentinel.track2]

        playlist.add_tracks.assert_has_calls([
            mock.call(mock.sentinel.track1, index=0),
            mock.call(mock.sentinel.track2, index=1),
        ], any_order=False)
        playlist.remove_tracks.assert_has_calls([
            mock.call(3),
            mock.call(2),
        ], any_order=False)

    def test_tracks_setittem_with_slice_and_noniterable_value_fails(
            self, lib_mock):
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist = spotify.Playlist(self.session, sp_playlist=sp_playlist)
        tracks = playlist.tracks
        tracks.__len__ = mock.Mock(return_value=5)

        with self.assertRaises(TypeError):
            tracks[0:2] = mock.sentinel.track

    def test_tracks_setitem_raises_index_error_on_negative_index(
            self, lib_mock):
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist = spotify.Playlist(self.session, sp_playlist=sp_playlist)
        tracks = playlist.tracks
        tracks.__len__ = mock.Mock(return_value=5)

        with self.assertRaises(IndexError):
            tracks[-1] = None

    def test_tracks_setitem_raises_index_error_on_too_high_index(
            self, lib_mock):
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist = spotify.Playlist(self.session, sp_playlist=sp_playlist)
        tracks = playlist.tracks
        tracks.__len__ = mock.Mock(return_value=1)

        with self.assertRaises(IndexError):
            tracks[1] = None

    def test_tracks_setitem_raises_type_error_on_non_integral_index(
            self, lib_mock):
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist = spotify.Playlist(self.session, sp_playlist=sp_playlist)
        tracks = playlist.tracks
        tracks.__len__ = mock.Mock(return_value=1)

        with self.assertRaises(TypeError):
            tracks['abc'] = None

    def test_tracks_delitem(self, lib_mock):
        lib_mock.sp_playlist_remove_tracks.return_value = int(
            spotify.ErrorType.OK)
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist = spotify.Playlist(self.session, sp_playlist=sp_playlist)
        tracks = playlist.tracks
        tracks.__len__ = mock.Mock(return_value=4)

        del tracks[3]

        lib_mock.sp_playlist_remove_tracks.assert_called_with(
            sp_playlist, [3], 1)

    def test_tracks_delitem_with_slice(self, lib_mock):
        lib_mock.sp_playlist_remove_tracks.return_value = int(
            spotify.ErrorType.OK)
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist = spotify.Playlist(self.session, sp_playlist=sp_playlist)
        tracks = playlist.tracks
        tracks.__len__ = mock.Mock(return_value=3)

        del tracks[0:2]

        # Delete items in reverse order, so the indexes doesn't change
        lib_mock.sp_playlist_remove_tracks.assert_has_calls([
            mock.call(sp_playlist, [1], 1),
            mock.call(sp_playlist, [0], 1),
        ], any_order=False)

    def test_tracks_delitem_raises_index_error_on_negative_index(
            self, lib_mock):
        lib_mock.sp_playlist_remove_tracks.return_value = int(
            spotify.ErrorType.OK)
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist = spotify.Playlist(self.session, sp_playlist=sp_playlist)
        tracks = playlist.tracks
        tracks.__len__ = mock.Mock(return_value=1)

        with self.assertRaises(IndexError):
            del tracks[-1]

    def test_tracks_delitem_raises_index_error_on_too_high_index(
            self, lib_mock):
        lib_mock.sp_playlist_remove_tracks.return_value = int(
            spotify.ErrorType.OK)
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist = spotify.Playlist(self.session, sp_playlist=sp_playlist)
        tracks = playlist.tracks
        tracks.__len__ = mock.Mock(return_value=1)

        with self.assertRaises(IndexError):
            del tracks[1]

    def test_tracks_delitem_raises_type_error_on_non_integral_index(
            self, lib_mock):
        lib_mock.sp_playlist_remove_tracks.return_value = int(
            spotify.ErrorType.OK)
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist = spotify.Playlist(self.session, sp_playlist=sp_playlist)
        tracks = playlist.tracks
        tracks.__len__ = mock.Mock(return_value=1)

        with self.assertRaises(TypeError):
            del tracks['abc']

    def test_tracks_insert(self, lib_mock):
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist = spotify.Playlist(self.session, sp_playlist=sp_playlist)
        tracks = playlist.tracks
        tracks.__len__ = mock.Mock(return_value=5)
        playlist.add_tracks = mock.Mock()

        tracks.insert(3, mock.sentinel.track)

        playlist.add_tracks.assert_called_with(
            mock.sentinel.track, index=3)

    @mock.patch('spotify.playlist_track.lib', spec=spotify.lib)
    def test_tracks_with_metadata(self, playlist_track_lib_mock, lib_mock):
        lib_mock.sp_playlist_num_tracks.return_value = 1
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist = spotify.Playlist(self.session, sp_playlist=sp_playlist)

        # Created a Playlist with a ref to sp_playlist
        self.assertEqual(lib_mock.sp_playlist_add_ref.call_count, 1)
        self.assertEqual(
            playlist_track_lib_mock.sp_playlist_add_ref.call_count, 0)

        result = playlist.tracks_with_metadata

        # Created a Sequence with a ref to sp_playlist
        self.assertEqual(lib_mock.sp_playlist_add_ref.call_count, 2)
        self.assertEqual(
            playlist_track_lib_mock.sp_playlist_add_ref.call_count, 0)

        self.assertEqual(len(result), 1)
        lib_mock.sp_playlist_num_tracks.assert_called_with(sp_playlist)

        item = result[0]
        self.assertIsInstance(item, spotify.PlaylistTrack)

        # Created a PlaylistTrack with a ref to sp_playlist
        self.assertEqual(lib_mock.sp_playlist_add_ref.call_count, 2)
        self.assertEqual(
            playlist_track_lib_mock.sp_playlist_add_ref.call_count, 1)

    def test_tracks_with_metadata_if_no_tracks(self, lib_mock):
        lib_mock.sp_playlist_num_tracks.return_value = 0
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist = spotify.Playlist(self.session, sp_playlist=sp_playlist)

        result = playlist.tracks_with_metadata

        self.assertEqual(len(result), 0)
        lib_mock.sp_playlist_num_tracks.assert_called_with(sp_playlist)
        self.assertEqual(lib_mock.sp_playlist_track.call_count, 0)

    def test_tracks_with_metadata_if_unloaded(self, lib_mock):
        lib_mock.sp_playlist_is_loaded.return_value = 0
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist = spotify.Playlist(self.session, sp_playlist=sp_playlist)

        result = playlist.tracks_with_metadata

        lib_mock.sp_playlist_is_loaded.assert_called_with(sp_playlist)
        self.assertEqual(len(result), 0)

    def test_name(self, lib_mock):
        lib_mock.sp_playlist_name.return_value = spotify.ffi.new(
            'char[]', b'Foo Bar Baz')
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist = spotify.Playlist(self.session, sp_playlist=sp_playlist)

        result = playlist.name

        lib_mock.sp_playlist_name.assert_called_once_with(sp_playlist)
        self.assertEqual(result, 'Foo Bar Baz')

    def test_name_is_none_if_unloaded(self, lib_mock):
        lib_mock.sp_playlist_name.return_value = spotify.ffi.new('char[]', b'')
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist = spotify.Playlist(self.session, sp_playlist=sp_playlist)

        result = playlist.name

        lib_mock.sp_playlist_name.assert_called_once_with(sp_playlist)
        self.assertIsNone(result)

    def test_rename(self, lib_mock):
        lib_mock.sp_playlist_rename.return_value = int(spotify.ErrorType.OK)
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist = spotify.Playlist(self.session, sp_playlist=sp_playlist)

        playlist.rename('Quux')

        lib_mock.sp_playlist_rename.assert_called_with(sp_playlist, mock.ANY)
        self.assertEqual(
            spotify.ffi.string(lib_mock.sp_playlist_rename.call_args[0][1]),
            b'Quux')

    def test_rename_fails_if_error(self, lib_mock):
        lib_mock.sp_playlist_rename.return_value = int(
            spotify.ErrorType.BAD_API_VERSION)
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist = spotify.Playlist(self.session, sp_playlist=sp_playlist)

        with self.assertRaises(spotify.Error):
            playlist.rename('Quux')

    def test_name_setter(self, lib_mock):
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist = spotify.Playlist(self.session, sp_playlist=sp_playlist)
        playlist.rename = mock.Mock()

        playlist.name = 'Quux'

        playlist.rename.assert_called_with('Quux')

    @mock.patch('spotify.user.lib', spec=spotify.lib)
    def test_owner(self, user_lib_mock, lib_mock):
        sp_user = spotify.ffi.cast('sp_user *', 43)
        lib_mock.sp_playlist_owner.return_value = sp_user
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist = spotify.Playlist(self.session, sp_playlist=sp_playlist)

        result = playlist.owner

        lib_mock.sp_playlist_owner.assert_called_with(sp_playlist)
        self.assertIsInstance(result, spotify.User)
        self.assertEqual(result._sp_user, sp_user)
        user_lib_mock.sp_user_add_ref.assert_called_with(sp_user)

    def test_is_collaborative(self, lib_mock):
        lib_mock.sp_playlist_is_collaborative.return_value = 1
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist = spotify.Playlist(self.session, sp_playlist=sp_playlist)

        result = playlist.collaborative

        lib_mock.sp_playlist_is_collaborative.assert_called_with(sp_playlist)
        self.assertTrue(result)

    def test_set_collaborative(self, lib_mock):
        lib_mock.sp_playlist_set_collaborative.return_value = int(
            spotify.ErrorType.OK)
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist = spotify.Playlist(self.session, sp_playlist=sp_playlist)

        playlist.collaborative = False

        lib_mock.sp_playlist_set_collaborative.assert_called_with(
            sp_playlist, 0)

    def test_set_collaborative_fails_if_error(self, lib_mock):
        lib_mock.sp_playlist_set_collaborative.return_value = int(
            spotify.ErrorType.BAD_API_VERSION)
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist = spotify.Playlist(self.session, sp_playlist=sp_playlist)

        with self.assertRaises(spotify.Error):
            playlist.collaborative = False

    def test_set_autolink_tracks(self, lib_mock):
        lib_mock.sp_playlist_set_autolink_tracks.return_value = int(
            spotify.ErrorType.OK)
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist = spotify.Playlist(self.session, sp_playlist=sp_playlist)

        playlist.set_autolink_tracks(True)

        lib_mock.sp_playlist_set_autolink_tracks.assert_called_with(
            sp_playlist, 1)

    def test_set_autolink_tracks_fails_if_error(self, lib_mock):
        lib_mock.sp_playlist_set_autolink_tracks.return_value = int(
            spotify.ErrorType.BAD_API_VERSION)
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist = spotify.Playlist(self.session, sp_playlist=sp_playlist)

        with self.assertRaises(spotify.Error):
            playlist.set_autolink_tracks(True)

    def test_description(self, lib_mock):
        lib_mock.sp_playlist_get_description.return_value = spotify.ffi.new(
            'char[]', b'Lorem ipsum')
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist = spotify.Playlist(self.session, sp_playlist=sp_playlist)

        result = playlist.description

        lib_mock.sp_playlist_get_description.assert_called_with(sp_playlist)
        self.assertEqual(result, 'Lorem ipsum')

    def test_description_is_none_if_unset(self, lib_mock):
        lib_mock.sp_playlist_get_description.return_value = spotify.ffi.NULL
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist = spotify.Playlist(self.session, sp_playlist=sp_playlist)

        result = playlist.description

        lib_mock.sp_playlist_get_description.assert_called_with(sp_playlist)
        self.assertIsNone(result)

    @mock.patch('spotify.Image', spec=spotify.Image)
    def test_image(self, image_mock, lib_mock):
        image_id = b'image-id'

        def func(sp_playlist, sp_image_id):
            buf = spotify.ffi.buffer(sp_image_id)
            buf[:len(image_id)] = image_id
            return 1

        lib_mock.sp_playlist_get_image.side_effect = func
        sp_image = spotify.ffi.cast('sp_image *', 43)
        lib_mock.sp_image_create.return_value = sp_image
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist = spotify.Playlist(self.session, sp_playlist=sp_playlist)
        image_mock.return_value = mock.sentinel.image
        callback = mock.Mock()

        result = playlist.image(callback=callback)

        self.assertIs(result, mock.sentinel.image)
        lib_mock.sp_playlist_get_image.assert_called_with(
            sp_playlist, mock.ANY)
        lib_mock.sp_image_create.assert_called_with(
            self.session._sp_session, mock.ANY)
        self.assertEqual(
            spotify.ffi.string(lib_mock.sp_image_create.call_args[0][1]),
            b'image-id')

        # Since we *created* the sp_image, we already have a refcount of 1 and
        # shouldn't increase the refcount when wrapping this sp_image in an
        # Image object
        image_mock.assert_called_with(
            self.session, sp_image=sp_image, add_ref=False, callback=callback)

    def test_image_is_none_if_no_image(self, lib_mock):
        lib_mock.sp_playlist_get_image.return_value = 0
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist = spotify.Playlist(self.session, sp_playlist=sp_playlist)

        result = playlist.image()

        lib_mock.sp_playlist_get_image.assert_called_with(
            sp_playlist, mock.ANY)
        self.assertIsNone(result)

    def test_has_pending_changes(self, lib_mock):
        lib_mock.sp_playlist_has_pending_changes.return_value = 1
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist = spotify.Playlist(self.session, sp_playlist=sp_playlist)

        result = playlist.has_pending_changes

        lib_mock.sp_playlist_has_pending_changes.assert_called_with(
            sp_playlist)
        self.assertTrue(result)

    @mock.patch('spotify.track.lib', spec=spotify.lib)
    def test_add_tracks(self, track_lib_mock, lib_mock):
        lib_mock.sp_playlist_add_tracks.return_value = int(
            spotify.ErrorType.OK)
        sp_track1 = spotify.ffi.new('int * ')
        track1 = spotify.Track(self.session, sp_track=sp_track1)
        sp_track2 = spotify.ffi.new('int * ')
        track2 = spotify.Track(self.session, sp_track=sp_track2)
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist = spotify.Playlist(self.session, sp_playlist=sp_playlist)

        playlist.add_tracks([track1, track2], index=4)

        lib_mock.sp_playlist_add_tracks.assert_called_with(
            sp_playlist, [sp_track1, sp_track2], 2, 4,
            self.session._sp_session)

    @mock.patch('spotify.track.lib', spec=spotify.lib)
    def test_add_tracks_without_index(self, track_lib_mock, lib_mock):
        lib_mock.sp_playlist_add_tracks.return_value = int(
            spotify.ErrorType.OK)
        lib_mock.sp_playlist_num_tracks.return_value = 10
        sp_track1 = spotify.ffi.new('int * ')
        track1 = spotify.Track(self.session, sp_track=sp_track1)
        sp_track2 = spotify.ffi.new('int * ')
        track2 = spotify.Track(self.session, sp_track=sp_track2)
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist = spotify.Playlist(self.session, sp_playlist=sp_playlist)

        playlist.add_tracks([track1, track2])

        lib_mock.sp_playlist_add_tracks.assert_called_with(
            sp_playlist, [sp_track1, sp_track2], 2, 10,
            self.session._sp_session)

    @mock.patch('spotify.track.lib', spec=spotify.lib)
    def test_add_tracks_with_a_single_track(self, track_lib_mock, lib_mock):
        lib_mock.sp_playlist_add_tracks.return_value = int(
            spotify.ErrorType.OK)
        sp_track = spotify.ffi.new('int * ')
        track = spotify.Track(self.session, sp_track=sp_track)
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist = spotify.Playlist(self.session, sp_playlist=sp_playlist)

        playlist.add_tracks(track, index=7)

        lib_mock.sp_playlist_add_tracks.assert_called_with(
            sp_playlist, [sp_track], 1, 7, self.session._sp_session)

    def test_add_tracks_fails_if_error(self, lib_mock):
        lib_mock.sp_playlist_add_tracks.return_value = int(
            spotify.ErrorType.PERMISSION_DENIED)
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist = spotify.Playlist(self.session, sp_playlist=sp_playlist)

        with self.assertRaises(spotify.Error):
            playlist.add_tracks([])

    @mock.patch('spotify.track.lib', spec=spotify.lib)
    def test_remove_tracks(self, track_lib_mock, lib_mock):
        lib_mock.sp_playlist_remove_tracks.return_value = int(
            spotify.ErrorType.OK)
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist = spotify.Playlist(self.session, sp_playlist=sp_playlist)
        index1 = 13
        index2 = 17

        playlist.remove_tracks([index1, index2])

        lib_mock.sp_playlist_remove_tracks.assert_called_with(
            sp_playlist, mock.ANY, 2)
        self.assertIn(
            index1, lib_mock.sp_playlist_remove_tracks.call_args[0][1])
        self.assertIn(
            index2, lib_mock.sp_playlist_remove_tracks.call_args[0][1])

    @mock.patch('spotify.track.lib', spec=spotify.lib)
    def test_remove_tracks_with_a_single_track(self, track_lib_mock, lib_mock):
        lib_mock.sp_playlist_remove_tracks.return_value = int(
            spotify.ErrorType.OK)
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist = spotify.Playlist(self.session, sp_playlist=sp_playlist)
        index = 17

        playlist.remove_tracks(index)

        lib_mock.sp_playlist_remove_tracks.assert_called_with(
            sp_playlist, [index], 1)

    @mock.patch('spotify.track.lib', spec=spotify.lib)
    def test_remove_tracks_with_duplicates(self, track_lib_mock, lib_mock):
        lib_mock.sp_playlist_remove_tracks.return_value = int(
            spotify.ErrorType.OK)
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist = spotify.Playlist(self.session, sp_playlist=sp_playlist)
        index = 17

        playlist.remove_tracks([index, index])

        lib_mock.sp_playlist_remove_tracks.assert_called_with(
            sp_playlist, [index], 1)

    @mock.patch('spotify.track.lib', spec=spotify.lib)
    def test_remove_tracks_fails_if_error(self, track_lib_mock, lib_mock):
        lib_mock.sp_playlist_remove_tracks.return_value = int(
            spotify.ErrorType.PERMISSION_DENIED)
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist = spotify.Playlist(self.session, sp_playlist=sp_playlist)
        index = 17

        with self.assertRaises(spotify.Error):
            playlist.remove_tracks(index)

    @mock.patch('spotify.track.lib', spec=spotify.lib)
    def test_reorder_tracks(self, track_lib_mock, lib_mock):
        lib_mock.sp_playlist_reorder_tracks.return_value = int(
            spotify.ErrorType.OK)
        sp_track1 = spotify.ffi.cast('sp_track *', 43)
        track1 = spotify.Track(self.session, sp_track=sp_track1)
        sp_track2 = spotify.ffi.cast('sp_track *', 44)
        track2 = spotify.Track(self.session, sp_track=sp_track2)
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist = spotify.Playlist(self.session, sp_playlist=sp_playlist)

        playlist.reorder_tracks([track1, track2], 17)

        lib_mock.sp_playlist_reorder_tracks.assert_called_with(
            sp_playlist, mock.ANY, 2, 17)
        self.assertIn(
            sp_track1, lib_mock.sp_playlist_reorder_tracks.call_args[0][1])
        self.assertIn(
            sp_track2, lib_mock.sp_playlist_reorder_tracks.call_args[0][1])

    @mock.patch('spotify.track.lib', spec=spotify.lib)
    def test_reorder_tracks_with_a_single_track(
            self, track_lib_mock, lib_mock):
        lib_mock.sp_playlist_reorder_tracks.return_value = int(
            spotify.ErrorType.OK)
        sp_track = spotify.ffi.cast('sp_track *', 43)
        track = spotify.Track(self.session, sp_track=sp_track)
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist = spotify.Playlist(self.session, sp_playlist=sp_playlist)

        playlist.reorder_tracks(track, 17)

        lib_mock.sp_playlist_reorder_tracks.assert_called_with(
            sp_playlist, [sp_track], 1, 17)

    @mock.patch('spotify.track.lib', spec=spotify.lib)
    def test_reorder_tracks_with_duplicates(self, track_lib_mock, lib_mock):
        lib_mock.sp_playlist_reorder_tracks.return_value = int(
            spotify.ErrorType.OK)
        sp_track = spotify.ffi.cast('sp_track *', 43)
        track = spotify.Track(self.session, sp_track=sp_track)
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist = spotify.Playlist(self.session, sp_playlist=sp_playlist)

        playlist.reorder_tracks([track, track], 17)

        lib_mock.sp_playlist_reorder_tracks.assert_called_with(
            sp_playlist, [sp_track], 1, 17)

    @mock.patch('spotify.track.lib', spec=spotify.lib)
    def test_reorder_tracks_fails_if_error(self, track_lib_mock, lib_mock):
        lib_mock.sp_playlist_reorder_tracks.return_value = int(
            spotify.ErrorType.PERMISSION_DENIED)
        sp_track = spotify.ffi.cast('sp_track *', 43)
        track = spotify.Track(self.session, sp_track=sp_track)
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist = spotify.Playlist(self.session, sp_playlist=sp_playlist)

        with self.assertRaises(spotify.Error):
            playlist.reorder_tracks(track, 17)

    def test_num_subscribers(self, lib_mock):
        lib_mock.sp_playlist_num_subscribers.return_value = 7
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist = spotify.Playlist(self.session, sp_playlist=sp_playlist)

        result = playlist.num_subscribers

        lib_mock.sp_playlist_num_subscribers.assert_called_with(sp_playlist)
        self.assertEqual(result, 7)

    def test_subscribers(self, lib_mock):
        sp_subscribers = spotify.ffi.new('sp_subscribers *')
        sp_subscribers.count = 1
        user_alice = spotify.ffi.new('char[]', b'alice')
        sp_subscribers.subscribers = [user_alice]
        lib_mock.sp_playlist_subscribers.return_value = sp_subscribers
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist = spotify.Playlist(self.session, sp_playlist=sp_playlist)

        result = playlist.subscribers

        lib_mock.sp_playlist_subscribers.assert_called_with(sp_playlist)
        tests.gc_collect()
        lib_mock.sp_playlist_subscribers_free.assert_called_with(
            sp_subscribers)
        self.assertEqual(result, ['alice'])

    def test_update_subscribers(self, lib_mock):
        lib_mock.sp_playlist_update_subscribers.return_value = int(
            spotify.ErrorType.OK)
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist = spotify.Playlist(self.session, sp_playlist=sp_playlist)

        playlist.update_subscribers()

        lib_mock.sp_playlist_update_subscribers.assert_called_with(
            self.session._sp_session, sp_playlist)

    def test_update_subscribers_fails_if_error(self, lib_mock):
        lib_mock.sp_playlist_update_subscribers.return_value = int(
            spotify.ErrorType.BAD_API_VERSION)
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist = spotify.Playlist(self.session, sp_playlist=sp_playlist)

        with self.assertRaises(spotify.Error):
            playlist.update_subscribers()

    def test_is_in_ram(self, lib_mock):
        lib_mock.sp_playlist_is_in_ram.return_value = 1
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist = spotify.Playlist(self.session, sp_playlist=sp_playlist)

        result = playlist.is_in_ram

        lib_mock.sp_playlist_is_in_ram.assert_called_with(
            self.session._sp_session, sp_playlist)
        self.assertTrue(result)

    def test_set_in_ram(self, lib_mock):
        lib_mock.sp_playlist_set_in_ram.return_value = int(
            spotify.ErrorType.OK)
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist = spotify.Playlist(self.session, sp_playlist=sp_playlist)

        playlist.set_in_ram(False)

        lib_mock.sp_playlist_set_in_ram.assert_called_with(
            self.session._sp_session, sp_playlist, 0)

    def test_set_in_ram_fails_if_error(self, lib_mock):
        lib_mock.sp_playlist_set_in_ram.return_value = int(
            spotify.ErrorType.BAD_API_VERSION)
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist = spotify.Playlist(self.session, sp_playlist=sp_playlist)

        with self.assertRaises(spotify.Error):
            playlist.set_in_ram(False)

    def test_set_offline_mode(self, lib_mock):
        lib_mock.sp_playlist_set_offline_mode.return_value = int(
            spotify.ErrorType.OK)
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist = spotify.Playlist(self.session, sp_playlist=sp_playlist)

        playlist.set_offline_mode(False)

        lib_mock.sp_playlist_set_offline_mode.assert_called_with(
            self.session._sp_session, sp_playlist, 0)

    def test_set_offline_mode_fails_if_error(self, lib_mock):
        lib_mock.sp_playlist_set_offline_mode.return_value = int(
            spotify.ErrorType.BAD_API_VERSION)
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist = spotify.Playlist(self.session, sp_playlist=sp_playlist)

        with self.assertRaises(spotify.Error):
            playlist.set_offline_mode(False)

    def test_offline_status(self, lib_mock):
        lib_mock.sp_playlist_get_offline_status.return_value = 2
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist = spotify.Playlist(self.session, sp_playlist=sp_playlist)

        result = playlist.offline_status

        lib_mock.sp_playlist_get_offline_status.assert_called_with(
            self.session._sp_session, sp_playlist)
        self.assertIs(result, spotify.PlaylistOfflineStatus.DOWNLOADING)

    def test_offline_download_completed(self, lib_mock):
        lib_mock.sp_playlist_get_offline_status.return_value = 2
        lib_mock.sp_playlist_get_offline_download_completed.return_value = 73
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist = spotify.Playlist(self.session, sp_playlist=sp_playlist)

        result = playlist.offline_download_completed

        lib_mock.sp_playlist_get_offline_download_completed.assert_called_with(
            self.session._sp_session, sp_playlist)
        self.assertEqual(result, 73)

    def test_offline_download_completed_when_not_downloading(self, lib_mock):
        lib_mock.sp_playlist_get_offline_status.return_value = 0
        lib_mock.sp_playlist_get_offline_download_completed.return_value = 0
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist = spotify.Playlist(self.session, sp_playlist=sp_playlist)

        result = playlist.offline_download_completed

        self.assertEqual(
            lib_mock.sp_playlist_get_offline_download_completed.call_count, 0)
        self.assertIsNone(result)

    @mock.patch('spotify.Link', spec=spotify.Link)
    def test_link_creates_link_to_playlist(self, link_mock, lib_mock):
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist = spotify.Playlist(self.session, sp_playlist=sp_playlist)
        sp_link = spotify.ffi.cast('sp_link *', 43)
        lib_mock.sp_link_create_from_playlist.return_value = sp_link
        link_mock.return_value = mock.sentinel.link

        result = playlist.link

        link_mock.assert_called_once_with(
            self.session, sp_link=sp_link, add_ref=False)
        self.assertEqual(result, mock.sentinel.link)

    @mock.patch('spotify.Link', spec=spotify.Link)
    def test_link_fails_if_playlist_not_loaded(
            self, lik_mock, lib_mock):
        lib_mock.sp_playlist_is_loaded.return_value = 0
        lib_mock.sp_link_create_from_playlist.return_value = spotify.ffi.NULL
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist = spotify.Playlist(self.session, sp_playlist=sp_playlist)

        with self.assertRaises(spotify.Error):
            playlist.link

        # Condition is checked before link creation is tried
        self.assertEqual(lib_mock.sp_link_create_from_playlist.call_count, 0)

    @mock.patch('spotify.Link', spec=spotify.Link)
    def test_link_may_fail_if_playlist_has_not_been_in_ram(
            self, link_mock, lib_mock):
        lib_mock.sp_playlist_is_loaded.return_value = 1
        lib_mock.sp_link_create_from_playlist.return_value = spotify.ffi.NULL
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist = spotify.Playlist(self.session, sp_playlist=sp_playlist)

        with self.assertRaises(spotify.Error):
            playlist.link

        # Condition is checked only if link creation returns NULL
        lib_mock.sp_link_create_from_playlist.assert_called_with(sp_playlist)
        lib_mock.sp_playlist_is_in_ram.assert_called_with(
            self.session._sp_session, sp_playlist)

    def test_first_on_call_adds_ref_to_obj_on_session(self, lib_mock):
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist = spotify.Playlist(self.session, sp_playlist=sp_playlist)

        playlist.on(spotify.PlaylistEvent.TRACKS_ADDED, lambda *args: None)

        self.assertIn(playlist, self.session._emitters)

    def test_last_off_call_removes_ref_to_obj_from_session(self, lib_mock):
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist = spotify.Playlist(self.session, sp_playlist=sp_playlist)

        playlist.on(spotify.PlaylistEvent.TRACKS_ADDED, lambda *args: None)
        playlist.off(spotify.PlaylistEvent.TRACKS_ADDED)

        self.assertNotIn(playlist, self.session._emitters)

    def test_other_off_calls_keeps_ref_to_obj_on_session(self, lib_mock):
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist = spotify.Playlist(self.session, sp_playlist=sp_playlist)

        playlist.on(spotify.PlaylistEvent.TRACKS_ADDED, lambda *args: None)
        playlist.on(spotify.PlaylistEvent.TRACKS_MOVED, lambda *args: None)
        playlist.off(spotify.PlaylistEvent.TRACKS_ADDED)

        self.assertIn(playlist, self.session._emitters)

        playlist.off(spotify.PlaylistEvent.TRACKS_MOVED)

        self.assertNotIn(playlist, self.session._emitters)


@mock.patch('spotify.playlist.lib', spec=spotify.lib)
class PlaylistCallbacksTest(unittest.TestCase):

    def setUp(self):
        self.session = tests.create_session_mock()
        spotify._session_instance = self.session

    def tearDown(self):
        spotify._session_instance = None

    @mock.patch('spotify.track.lib', spec=spotify.lib)
    def test_tracks_added_callback(self, track_lib_mock, lib_mock):
        callback = mock.Mock()
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist = spotify.Playlist._cached(
            self.session, sp_playlist=sp_playlist)
        playlist.on(spotify.PlaylistEvent.TRACKS_ADDED, callback)
        sp_tracks = [
            spotify.ffi.cast('sp_track *', 43),
            spotify.ffi.cast('sp_track *', 44),
            spotify.ffi.cast('sp_track *', 45),
        ]
        index = 7

        _PlaylistCallbacks.tracks_added(
            sp_playlist, sp_tracks, len(sp_tracks), index, spotify.ffi.NULL)

        callback.assert_called_once_with(playlist, mock.ANY, index)
        tracks = callback.call_args[0][1]
        self.assertEqual(len(tracks), len(sp_tracks))
        self.assertIsInstance(tracks[0], spotify.Track)
        self.assertEqual(tracks[0]._sp_track, sp_tracks[0])
        track_lib_mock.sp_track_add_ref.assert_has_calls([
            mock.call(sp_tracks[0]),
            mock.call(sp_tracks[1]),
            mock.call(sp_tracks[2]),
        ])

    def test_tracks_removed_callback(self, lib_mock):
        callback = mock.Mock()
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist = spotify.Playlist._cached(
            self.session, sp_playlist=sp_playlist)
        playlist.on(spotify.PlaylistEvent.TRACKS_REMOVED, callback)
        track_numbers = [43, 44, 45]

        _PlaylistCallbacks.tracks_removed(
            sp_playlist, track_numbers, len(track_numbers), spotify.ffi.NULL)

        callback.assert_called_once_with(playlist, mock.ANY)
        tracks = callback.call_args[0][1]
        self.assertEqual(len(tracks), len(track_numbers))
        self.assertEqual(tracks[0], 43)

    def test_tracks_moved_callback(self, lib_mock):
        callback = mock.Mock()
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist = spotify.Playlist._cached(
            self.session, sp_playlist=sp_playlist)
        playlist.on(spotify.PlaylistEvent.TRACKS_MOVED, callback)
        track_numbers = [43, 44, 45]
        index = 7

        _PlaylistCallbacks.tracks_moved(
            sp_playlist, track_numbers, len(track_numbers), index,
            spotify.ffi.NULL)

        callback.assert_called_once_with(playlist, mock.ANY, index)
        tracks = callback.call_args[0][1]
        self.assertEqual(len(tracks), len(track_numbers))
        self.assertEqual(tracks[0], 43)

    def test_playlist_renamed_callback(self, lib_mock):
        callback = mock.Mock()
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist = spotify.Playlist._cached(
            self.session, sp_playlist=sp_playlist)
        playlist.on(spotify.PlaylistEvent.PLAYLIST_RENAMED, callback)

        _PlaylistCallbacks.playlist_renamed(sp_playlist, spotify.ffi.NULL)

        callback.assert_called_once_with(playlist)

    def test_playlist_state_changed_callback(self, lib_mock):
        callback = mock.Mock()
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist = spotify.Playlist._cached(
            self.session, sp_playlist=sp_playlist)
        playlist.on(spotify.PlaylistEvent.PLAYLIST_STATE_CHANGED, callback)

        _PlaylistCallbacks.playlist_state_changed(
            sp_playlist, spotify.ffi.NULL)

        callback.assert_called_once_with(playlist)

    def test_playlist_update_in_progress_callback(self, lib_mock):
        callback = mock.Mock()
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist = spotify.Playlist._cached(
            self.session, sp_playlist=sp_playlist)
        playlist.on(
            spotify.PlaylistEvent.PLAYLIST_UPDATE_IN_PROGRESS, callback)
        done = True

        _PlaylistCallbacks.playlist_update_in_progress(
            sp_playlist, int(done), spotify.ffi.NULL)

        callback.assert_called_once_with(playlist, done)

    def test_playlist_metadata_updated_callback(self, lib_mock):
        callback = mock.Mock()
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist = spotify.Playlist._cached(
            self.session, sp_playlist=sp_playlist)
        playlist.on(spotify.PlaylistEvent.PLAYLIST_METADATA_UPDATED, callback)

        _PlaylistCallbacks.playlist_metadata_updated(
            sp_playlist, spotify.ffi.NULL)

        callback.assert_called_once_with(playlist)

    @mock.patch('spotify.user.lib', spec=spotify.lib)
    def test_track_created_changed_callback(self, user_lib_mock, lib_mock):
        callback = mock.Mock()
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist = spotify.Playlist._cached(
            self.session, sp_playlist=sp_playlist)
        playlist.on(spotify.PlaylistEvent.TRACK_CREATED_CHANGED, callback)
        index = 7
        sp_user = spotify.ffi.cast('sp_user *', 43)
        time = 123456789

        _PlaylistCallbacks.track_created_changed(
            sp_playlist, index, sp_user, time, spotify.ffi.NULL)

        callback.assert_called_once_with(playlist, index, mock.ANY, time)
        user = callback.call_args[0][2]
        self.assertIsInstance(user, spotify.User)
        self.assertEqual(user._sp_user, sp_user)
        user_lib_mock.sp_user_add_ref.assert_called_with(sp_user)

    def test_track_seen_changed_callback(self, lib_mock):
        callback = mock.Mock()
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist = spotify.Playlist._cached(
            self.session, sp_playlist=sp_playlist)
        playlist.on(spotify.PlaylistEvent.TRACK_SEEN_CHANGED, callback)
        index = 7
        seen = True

        _PlaylistCallbacks.track_seen_changed(
            sp_playlist, index, int(seen), spotify.ffi.NULL)

        callback.assert_called_once_with(playlist, index, seen)

    def test_description_changed_callback(self, lib_mock):
        callback = mock.Mock()
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist = spotify.Playlist._cached(
            self.session, sp_playlist=sp_playlist)
        playlist.on(spotify.PlaylistEvent.DESCRIPTION_CHANGED, callback)
        description = 'foo bar æøå'
        desc = spotify.ffi.new('char[]', description.encode('utf-8'))

        _PlaylistCallbacks.description_changed(
            sp_playlist, desc, spotify.ffi.NULL)

        callback.assert_called_once_with(playlist, description)

    @mock.patch('spotify.image.lib', spec=spotify.lib)
    def test_image_changed_callback(self, image_lib_mock, lib_mock):
        callback = mock.Mock()
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist = spotify.Playlist._cached(
            self.session, sp_playlist=sp_playlist)
        playlist.on(spotify.PlaylistEvent.IMAGE_CHANGED, callback)
        image_id = spotify.ffi.new('char[]', b'image-id')
        sp_image = spotify.ffi.cast('sp_image *', 43)
        lib_mock.sp_image_create.return_value = sp_image
        image_lib_mock.sp_image_add_load_callback.return_value = int(
            spotify.ErrorType.OK)

        _PlaylistCallbacks.image_changed(
            sp_playlist, image_id, spotify.ffi.NULL)

        callback.assert_called_once_with(playlist, mock.ANY)
        image = callback.call_args[0][1]
        self.assertIsInstance(image, spotify.Image)
        self.assertEqual(image._sp_image, sp_image)
        lib_mock.sp_image_create.assert_called_once_with(
            self.session._sp_session, image_id)
        self.assertEqual(image_lib_mock.sp_image_add_ref.call_count, 0)

    def test_track_message_changed_callback(self, lib_mock):
        callback = mock.Mock()
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist = spotify.Playlist._cached(
            self.session, sp_playlist=sp_playlist)
        playlist.on(spotify.PlaylistEvent.TRACK_MESSAGE_CHANGED, callback)
        index = 7
        message = 'foo bar æøå'
        msg = spotify.ffi.new('char[]', message.encode('utf-8'))

        _PlaylistCallbacks.track_message_changed(
            sp_playlist, index, msg, spotify.ffi.NULL)

        callback.assert_called_once_with(playlist, index, message)

    def test_subscribers_changed_callback(self, lib_mock):
        callback = mock.Mock()
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist = spotify.Playlist._cached(
            self.session, sp_playlist=sp_playlist)
        playlist.on(spotify.PlaylistEvent.SUBSCRIBERS_CHANGED, callback)

        _PlaylistCallbacks.subscribers_changed(sp_playlist, spotify.ffi.NULL)

        callback.assert_called_once_with(playlist)


class PlaylistOfflineStatusTest(unittest.TestCase):

    def test_has_constants(self):
        self.assertEqual(spotify.PlaylistOfflineStatus.NO, 0)
        self.assertEqual(spotify.PlaylistOfflineStatus.DOWNLOADING, 2)

########NEW FILE########
__FILENAME__ = test_playlist_container
from __future__ import unicode_literals

import collections
import unittest

import spotify
from spotify.playlist_container import _PlaylistContainerCallbacks
import tests
from tests import mock


@mock.patch('spotify.playlist_container.lib', spec=spotify.lib)
class PlaylistContainerTest(unittest.TestCase):

    def setUp(self):
        self.session = tests.create_session_mock()
        spotify._session_instance = self.session

    def tearDown(self):
        spotify._session_instance = None

    def test_life_cycle(self, lib_mock):
        sp_playlistcontainer = spotify.ffi.cast('sp_playlistcontainer *', 42)

        playlist_container = spotify.PlaylistContainer(
            self.session, sp_playlistcontainer)

        lib_mock.sp_playlistcontainer_add_ref.assert_called_with(
            sp_playlistcontainer)
        lib_mock.sp_playlistcontainer_add_callbacks.assert_called_with(
            sp_playlistcontainer, mock.ANY, mock.ANY)

        playlist_container = None  # noqa
        tests.gc_collect()

        lib_mock.sp_playlistcontainer_remove_callbacks.assert_called_with(
            sp_playlistcontainer, mock.ANY, mock.ANY)
        # FIXME Won't be called because lib_mock has references to the
        # sp_playlistcontainer object, and it thus won't be GC-ed.
        # lib_mock.sp_playlistcontainer_release.assert_called_with(
        #     sp_playlistcontainer)

    def test_cached_container(self, lib_mock):
        sp_playlistcontainer = spotify.ffi.cast('sp_playlistcontainer *', 42)

        result1 = spotify.PlaylistContainer._cached(
            self.session, sp_playlistcontainer)
        result2 = spotify.PlaylistContainer._cached(
            self.session, sp_playlistcontainer)

        self.assertIsInstance(result1, spotify.PlaylistContainer)
        self.assertIs(result1, result2)

    @mock.patch('spotify.User', spec=spotify.User)
    @mock.patch('spotify.Link', spec=spotify.Link)
    def test_repr(self, link_mock, user_mock, lib_mock):
        link_instance_mock = link_mock.return_value
        link_instance_mock.uri = 'foo'
        user_instance_mock = user_mock.return_value
        user_instance_mock.link = link_instance_mock
        lib_mock.sp_playlistcontainer_num_playlists.return_value = 0
        sp_playlistcontainer = spotify.ffi.cast('sp_playlistcontainer *', 42)
        playlist_container = spotify.PlaylistContainer(
            self.session, sp_playlistcontainer=sp_playlistcontainer)

        result = repr(playlist_container)

        self.assertEqual(result, 'PlaylistContainer([])')

    def test_eq(self, lib_mock):
        sp_playlistcontainer = spotify.ffi.cast('sp_playlistcontainer *', 42)
        playlist_container1 = spotify.PlaylistContainer(
            self.session, sp_playlistcontainer=sp_playlistcontainer)
        playlist_container2 = spotify.PlaylistContainer(
            self.session, sp_playlistcontainer=sp_playlistcontainer)

        self.assertTrue(playlist_container1 == playlist_container2)
        self.assertFalse(playlist_container1 == 'foo')

    def test_ne(self, lib_mock):
        sp_playlistcontainer = spotify.ffi.cast('sp_playlistcontainer *', 42)
        playlist_container1 = spotify.PlaylistContainer(
            self.session, sp_playlistcontainer=sp_playlistcontainer)
        playlist_container2 = spotify.PlaylistContainer(
            self.session, sp_playlistcontainer=sp_playlistcontainer)

        self.assertFalse(playlist_container1 != playlist_container2)

    def test_hash(self, lib_mock):
        sp_playlistcontainer = spotify.ffi.cast('sp_playlistcontainer *', 42)
        playlist_container1 = spotify.PlaylistContainer(
            self.session, sp_playlistcontainer=sp_playlistcontainer)
        playlist_container2 = spotify.PlaylistContainer(
            self.session, sp_playlistcontainer=sp_playlistcontainer)

        self.assertEqual(hash(playlist_container1), hash(playlist_container2))

    def test_is_loaded(self, lib_mock):
        lib_mock.sp_playlistcontainer_is_loaded.return_value = 1
        sp_playlistcontainer = spotify.ffi.cast('sp_playlistcontainer *', 42)
        playlist_container = spotify.PlaylistContainer(
            self.session, sp_playlistcontainer=sp_playlistcontainer)

        result = playlist_container.is_loaded

        lib_mock.sp_playlistcontainer_is_loaded.assert_called_once_with(
            sp_playlistcontainer)
        self.assertTrue(result)

    @mock.patch('spotify.utils.load')
    def test_load(self, load_mock, lib_mock):
        sp_playlistcontainer = spotify.ffi.cast('sp_playlistcontainer *', 42)
        playlist_container = spotify.PlaylistContainer(
            self.session, sp_playlistcontainer=sp_playlistcontainer)

        playlist_container.load(10)

        load_mock.assert_called_with(
            self.session, playlist_container, timeout=10)

    def test_len(self, lib_mock):
        lib_mock.sp_playlistcontainer_num_playlists.return_value = 8
        sp_playlistcontainer = spotify.ffi.cast('sp_playlistcontainer *', 42)
        playlist_container = spotify.PlaylistContainer(
            self.session, sp_playlistcontainer=sp_playlistcontainer)

        result = len(playlist_container)

        lib_mock.sp_playlistcontainer_num_playlists.assert_called_with(
            sp_playlistcontainer)
        self.assertEqual(result, 8)

    def test_len_if_undefined(self, lib_mock):
        lib_mock.sp_playlistcontainer_num_playlists.return_value = -1
        sp_playlistcontainer = spotify.ffi.cast('sp_playlistcontainer *', 42)
        playlist_container = spotify.PlaylistContainer(
            self.session, sp_playlistcontainer=sp_playlistcontainer)

        result = len(playlist_container)

        lib_mock.sp_playlistcontainer_num_playlists.assert_called_with(
            sp_playlistcontainer)
        self.assertEqual(result, 0)

    @mock.patch('spotify.playlist.lib', lib=spotify.lib)
    def test_getitem(self, playlist_lib_mock, lib_mock):
        lib_mock.sp_playlistcontainer_num_playlists.return_value = 1
        sp_playlist = spotify.ffi.cast('sp_playlist *', 43)
        lib_mock.sp_playlistcontainer_playlist_type.return_value = int(
            spotify.PlaylistType.PLAYLIST)
        lib_mock.sp_playlistcontainer_playlist.return_value = sp_playlist
        sp_playlistcontainer = spotify.ffi.cast('sp_playlistcontainer *', 42)
        playlist_container = spotify.PlaylistContainer(
            self.session, sp_playlistcontainer=sp_playlistcontainer)

        result = playlist_container[0]

        lib_mock.sp_playlistcontainer_playlist.assert_called_with(
            sp_playlistcontainer, 0)
        playlist_lib_mock.sp_playlist_add_ref.assert_called_with(sp_playlist)
        self.assertIsInstance(result, spotify.Playlist)
        self.assertEqual(result._sp_playlist, sp_playlist)

    @mock.patch('spotify.playlist.lib', lib=spotify.lib)
    def test_getitem_with_negative_index(self, playlist_lib_mock, lib_mock):
        lib_mock.sp_playlistcontainer_num_playlists.return_value = 1
        sp_playlist = spotify.ffi.cast('sp_playlist *', 43)
        lib_mock.sp_playlistcontainer_playlist_type.return_value = int(
            spotify.PlaylistType.PLAYLIST)
        lib_mock.sp_playlistcontainer_playlist.return_value = sp_playlist
        sp_playlistcontainer = spotify.ffi.cast('sp_playlistcontainer *', 42)
        playlist_container = spotify.PlaylistContainer(
            self.session, sp_playlistcontainer=sp_playlistcontainer)

        result = playlist_container[-1]

        lib_mock.sp_playlistcontainer_playlist.assert_called_with(
            sp_playlistcontainer, 0)
        playlist_lib_mock.sp_playlist_add_ref.assert_called_with(sp_playlist)
        self.assertIsInstance(result, spotify.Playlist)
        self.assertEqual(result._sp_playlist, sp_playlist)

    @mock.patch('spotify.playlist.lib', lib=spotify.lib)
    def test_getitem_with_slice(self, playlist_lib_mock, lib_mock):
        lib_mock.sp_playlistcontainer_num_playlists.return_value = 3
        lib_mock.sp_playlistcontainer_playlist_type.side_effect = [
            int(spotify.PlaylistType.PLAYLIST),
            int(spotify.PlaylistType.PLAYLIST),
            int(spotify.PlaylistType.PLAYLIST)]
        sp_playlist1 = spotify.ffi.cast('sp_playlist *', 43)
        sp_playlist2 = spotify.ffi.cast('sp_playlist *', 44)
        sp_playlist3 = spotify.ffi.cast('sp_playlist *', 45)
        lib_mock.sp_playlistcontainer_playlist.side_effect = [
            sp_playlist1, sp_playlist2, sp_playlist3
        ]
        sp_playlistcontainer = spotify.ffi.cast('sp_playlistcontainer *', 42)
        playlist_container = spotify.PlaylistContainer(
            self.session, sp_playlistcontainer=sp_playlistcontainer)

        result = playlist_container[0:2]

        # Entire collection of length 3 is created as a list
        self.assertEqual(lib_mock.sp_playlistcontainer_playlist.call_count, 3)
        self.assertEqual(playlist_lib_mock.sp_playlist_add_ref.call_count, 3)

        # Only a subslice of length 2 is returned
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]._sp_playlist, sp_playlist1)
        self.assertEqual(result[1]._sp_playlist, sp_playlist2)

    @mock.patch('spotify.playlist.lib', lib=spotify.lib)
    def test_getitem_with_folder(self, playlist_lib_mock, lib_mock):
        folder_name = 'foobar'

        lib_mock.sp_playlistcontainer_num_playlists.return_value = 3
        lib_mock.sp_playlistcontainer_playlist_type.side_effect = [
            int(spotify.PlaylistType.START_FOLDER),
            int(spotify.PlaylistType.PLAYLIST),
            int(spotify.PlaylistType.END_FOLDER)]
        sp_playlist = spotify.ffi.cast('sp_playlist *', 43)
        lib_mock.sp_playlistcontainer_playlist.return_value = sp_playlist
        lib_mock.sp_playlistcontainer_playlist_folder_id.side_effect = [
            1001, 1002]
        lib_mock.sp_playlistcontainer_playlist_folder_name.side_effect = (
            tests.buffer_writer(folder_name))
        sp_playlistcontainer = spotify.ffi.cast('sp_playlistcontainer *', 42)
        playlist_container = spotify.PlaylistContainer(
            self.session, sp_playlistcontainer=sp_playlistcontainer)

        result = playlist_container[0]

        lib_mock.sp_playlistcontainer_playlist_type.assert_called_with(
            sp_playlistcontainer, 0)
        lib_mock.sp_playlistcontainer_playlist_folder_id.assert_called_with(
            sp_playlistcontainer, 0)
        self.assertIsInstance(result, spotify.PlaylistFolder)
        self.assertEqual(result.id, 1001)
        self.assertEqual(result.name, 'foobar')
        self.assertEqual(result.type, spotify.PlaylistType.START_FOLDER)

        result = playlist_container[1]

        lib_mock.sp_playlistcontainer_playlist_type.assert_called_with(
            sp_playlistcontainer, 1)
        lib_mock.sp_playlistcontainer_playlist.assert_called_with(
            sp_playlistcontainer, 1)
        playlist_lib_mock.sp_playlist_add_ref.assert_called_with(sp_playlist)
        self.assertIsInstance(result, spotify.Playlist)
        self.assertEqual(result._sp_playlist, sp_playlist)

        result = playlist_container[2]

        lib_mock.sp_playlistcontainer_playlist_type.assert_called_with(
            sp_playlistcontainer, 2)
        lib_mock.sp_playlistcontainer_playlist_folder_id.assert_called_with(
            sp_playlistcontainer, 2)
        self.assertIsInstance(result, spotify.PlaylistFolder)
        self.assertEqual(result.id, 1002)
        # self.assertEqual(result.name, '')  # Needs better mock impl
        self.assertEqual(result.type, spotify.PlaylistType.END_FOLDER)

    def test_getitem_raises_error_on_unknown_playlist_type(self, lib_mock):
        lib_mock.sp_playlistcontainer_num_playlists.return_value = 1
        lib_mock.sp_playlistcontainer_playlist_type.return_value = int(
            spotify.PlaylistType.PLACEHOLDER)
        sp_playlistcontainer = spotify.ffi.cast('sp_playlistcontainer *', 42)
        playlist_container = spotify.PlaylistContainer(
            self.session, sp_playlistcontainer=sp_playlistcontainer)

        with self.assertRaises(spotify.Error):
            playlist_container[0]

    def test_getitem_raises_index_error_on_too_low_index(self, lib_mock):
        lib_mock.sp_playlistcontainer_num_playlists.return_value = 1
        sp_playlist = spotify.ffi.cast('sp_playlist *', 43)
        lib_mock.sp_playlistcontainer_playlist.return_value = sp_playlist
        sp_playlistcontainer = spotify.ffi.cast('sp_playlistcontainer *', 42)
        playlist_container = spotify.PlaylistContainer(
            self.session, sp_playlistcontainer=sp_playlistcontainer)

        with self.assertRaises(IndexError):
            playlist_container[-3]

    def test_getitem_raises_index_error_on_too_high_index(self, lib_mock):
        lib_mock.sp_playlistcontainer_num_playlists.return_value = 1
        sp_playlist = spotify.ffi.cast('sp_playlist *', 43)
        lib_mock.sp_playlistcontainer_playlist.return_value = sp_playlist
        sp_playlistcontainer = spotify.ffi.cast('sp_playlistcontainer *', 42)
        playlist_container = spotify.PlaylistContainer(
            self.session, sp_playlistcontainer=sp_playlistcontainer)

        with self.assertRaises(IndexError):
            playlist_container[1]

    def test_getitem_raises_type_error_on_non_integral_index(self, lib_mock):
        lib_mock.sp_playlistcontainer_num_playlists.return_value = 1
        sp_playlist = spotify.ffi.cast('sp_playlist *', 43)
        lib_mock.sp_playlistcontainer_playlist.return_value = sp_playlist
        sp_playlistcontainer = spotify.ffi.cast('sp_playlistcontainer *', 42)
        playlist_container = spotify.PlaylistContainer(
            self.session, sp_playlistcontainer=sp_playlistcontainer)

        with self.assertRaises(TypeError):
            playlist_container['abc']

    def test_setitem_with_playlist_name(self, lib_mock):
        sp_playlistcontainer = spotify.ffi.cast('sp_playlistcontainer *', 42)
        playlist_container = spotify.PlaylistContainer(
            self.session, sp_playlistcontainer=sp_playlistcontainer)
        playlist_container.__len__ = mock.Mock(return_value=5)
        playlist_container.remove_playlist = mock.Mock()
        playlist_container.add_new_playlist = mock.Mock()

        playlist_container[0] = 'New playlist'

        playlist_container.add_new_playlist.assert_called_with(
            'New playlist', index=0)
        playlist_container.remove_playlist.assert_called_with(1)

    @mock.patch('spotify.playlist.lib', lib=spotify.lib)
    def test_setitem_with_existing_playlist(self, playlist_lib_mock, lib_mock):
        sp_playlist = spotify.ffi.cast('sp_playlist *', 43)
        playlist = spotify.Playlist(self.session, sp_playlist=sp_playlist)
        sp_playlistcontainer = spotify.ffi.cast('sp_playlistcontainer *', 42)
        playlist_container = spotify.PlaylistContainer(
            self.session, sp_playlistcontainer=sp_playlistcontainer)
        playlist_container.__len__ = mock.Mock(return_value=5)
        playlist_container.remove_playlist = mock.Mock()
        playlist_container.add_playlist = mock.Mock()

        playlist_container[0] = playlist

        playlist_container.add_playlist.assert_called_with(playlist, index=0)
        playlist_container.remove_playlist.assert_called_with(1)

    @mock.patch('spotify.playlist.lib', lib=spotify.lib)
    def test_setitem_with_slice(self, playlist_lib_mock, lib_mock):
        sp_playlist = spotify.ffi.cast('sp_playlist *', 43)
        playlist = spotify.Playlist(self.session, sp_playlist=sp_playlist)
        sp_playlistcontainer = spotify.ffi.cast('sp_playlistcontainer *', 42)
        playlist_container = spotify.PlaylistContainer(
            self.session, sp_playlistcontainer=sp_playlistcontainer)
        playlist_container.__len__ = mock.Mock(return_value=5)
        playlist_container.remove_playlist = mock.Mock()
        playlist_container.add_new_playlist = mock.Mock()
        playlist_container.add_playlist = mock.Mock()

        playlist_container[0:2] = ['New playlist', playlist]

        playlist_container.add_new_playlist.assert_called_with(
            'New playlist', index=0)
        playlist_container.add_playlist.assert_called_with(playlist, index=1)
        playlist_container.remove_playlist.assert_has_calls(
            [mock.call(3), mock.call(2)], any_order=False)

    @mock.patch('spotify.playlist.lib', lib=spotify.lib)
    def test_setittem_with_slice_and_noniterable_value_fails(
            self, playlist_lib_mock, lib_mock):

        sp_playlist = spotify.ffi.cast('sp_playlist *', 43)
        playlist = spotify.Playlist(self.session, sp_playlist=sp_playlist)
        sp_playlistcontainer = spotify.ffi.cast('sp_playlistcontainer *', 42)
        playlist_container = spotify.PlaylistContainer(
            self.session, sp_playlistcontainer=sp_playlistcontainer)
        playlist_container.__len__ = mock.Mock(return_value=3)
        playlist_container.remove_playlist = mock.Mock()
        playlist_container.add_new_playlist = mock.Mock()

        with self.assertRaises(TypeError):
            playlist_container[0:2] = playlist

    def test_setitem_raises_error_on_unknown_playlist_type(self, lib_mock):
        sp_playlistcontainer = spotify.ffi.cast('sp_playlistcontainer *', 42)
        playlist_container = spotify.PlaylistContainer(
            self.session, sp_playlistcontainer=sp_playlistcontainer)
        playlist_container.__len__ = mock.Mock(return_value=1)
        playlist_container.remove_playlist = mock.Mock()
        playlist_container.add_new_playlist = mock.Mock(side_effect=ValueError)

        with self.assertRaises(ValueError):
            playlist_container[0] = False

        playlist_container.add_new_playlist.assert_called_with(False, index=0)
        self.assertEqual(playlist_container.remove_playlist.call_count, 0)

    def test_setitem_raises_index_error_on_negative_index(self, lib_mock):
        sp_playlistcontainer = spotify.ffi.cast('sp_playlistcontainer *', 42)
        playlist_container = spotify.PlaylistContainer(
            self.session, sp_playlistcontainer=sp_playlistcontainer)
        playlist_container.__len__ = mock.Mock(return_value=1)

        with self.assertRaises(IndexError):
            playlist_container[-1] = None

    def test_setitem_raises_index_error_on_too_high_index(self, lib_mock):
        sp_playlistcontainer = spotify.ffi.cast('sp_playlistcontainer *', 42)
        playlist_container = spotify.PlaylistContainer(
            self.session, sp_playlistcontainer=sp_playlistcontainer)
        playlist_container.__len__ = mock.Mock(return_value=1)

        with self.assertRaises(IndexError):
            playlist_container[1] = None

    def test_setitem_raises_type_error_on_non_integral_index(self, lib_mock):
        sp_playlistcontainer = spotify.ffi.cast('sp_playlistcontainer *', 42)
        playlist_container = spotify.PlaylistContainer(
            self.session, sp_playlistcontainer=sp_playlistcontainer)
        playlist_container.__len__ = mock.Mock(return_value=1)

        with self.assertRaises(TypeError):
            playlist_container['abc'] = None

    def test_delitem(self, lib_mock):
        sp_playlistcontainer = spotify.ffi.cast('sp_playlistcontainer *', 42)
        playlist_container = spotify.PlaylistContainer(
            self.session, sp_playlistcontainer=sp_playlistcontainer)
        playlist_container.__len__ = mock.Mock(return_value=1)
        playlist_container.remove_playlist = mock.Mock()

        del playlist_container[0]

        playlist_container.remove_playlist.assert_called_with(0)

    def test_delitem_with_slice(self, lib_mock):
        sp_playlistcontainer = spotify.ffi.cast('sp_playlistcontainer *', 42)
        playlist_container = spotify.PlaylistContainer(
            self.session, sp_playlistcontainer=sp_playlistcontainer)
        playlist_container.__len__ = mock.Mock(return_value=3)
        playlist_container.remove_playlist = mock.Mock()

        del playlist_container[0:2]

        # Delete items in reverse order, so the indexes doesn't change
        playlist_container.remove_playlist.assert_has_calls(
            [mock.call(1), mock.call(0)], any_order=False)

    def test_delitem_raises_index_error_on_negative_index(self, lib_mock):
        sp_playlistcontainer = spotify.ffi.cast('sp_playlistcontainer *', 42)
        playlist_container = spotify.PlaylistContainer(
            self.session, sp_playlistcontainer=sp_playlistcontainer)
        playlist_container.__len__ = mock.Mock(return_value=1)

        with self.assertRaises(IndexError):
            del playlist_container[-1]

    def test_delitem_raises_index_error_on_too_high_index(self, lib_mock):
        sp_playlistcontainer = spotify.ffi.cast('sp_playlistcontainer *', 42)
        playlist_container = spotify.PlaylistContainer(
            self.session, sp_playlistcontainer=sp_playlistcontainer)
        playlist_container.__len__ = mock.Mock(return_value=1)

        with self.assertRaises(IndexError):
            del playlist_container[1]

    def test_delitem_raises_type_error_on_non_integral_index(self, lib_mock):
        sp_playlistcontainer = spotify.ffi.cast('sp_playlistcontainer *', 42)
        playlist_container = spotify.PlaylistContainer(
            self.session, sp_playlistcontainer=sp_playlistcontainer)
        playlist_container.__len__ = mock.Mock(return_value=1)

        with self.assertRaises(TypeError):
            del playlist_container['abc']

    def test_insert_with_playlist_name(self, lib_mock):
        sp_playlistcontainer = spotify.ffi.cast('sp_playlistcontainer *', 42)
        playlist_container = spotify.PlaylistContainer(
            self.session, sp_playlistcontainer=sp_playlistcontainer)
        playlist_container.__len__ = mock.Mock(return_value=5)
        playlist_container.remove_playlist = mock.Mock()
        playlist_container.add_new_playlist = mock.Mock()

        playlist_container.insert(3, 'New playlist')

        playlist_container.add_new_playlist.assert_called_with(
            'New playlist', index=3)

    @mock.patch('spotify.playlist.lib', spec=spotify.lib)
    def test_insert_with_existing_playlist(self, playlist_lib_mock, lib_mock):
        sp_playlist = spotify.ffi.cast('sp_playlist *', 43)
        playlist = spotify.Playlist(self.session, sp_playlist=sp_playlist)
        sp_playlistcontainer = spotify.ffi.cast('sp_playlistcontainer *', 42)
        playlist_container = spotify.PlaylistContainer(
            self.session, sp_playlistcontainer=sp_playlistcontainer)
        playlist_container.__len__ = mock.Mock(return_value=5)
        playlist_container.remove_playlist = mock.Mock()
        playlist_container.add_playlist = mock.Mock()

        playlist_container.insert(3, playlist)

        playlist_container.add_playlist.assert_called_with(playlist, index=3)

    def test_is_a_sequence(self, lib_mock):
        sp_playlistcontainer = spotify.ffi.cast('sp_playlistcontainer *', 42)
        playlist_container = spotify.PlaylistContainer(
            self.session, sp_playlistcontainer=sp_playlistcontainer)

        self.assertIsInstance(playlist_container, collections.Sequence)

    def test_is_a_mutable_sequence(self, lib_mock):
        sp_playlistcontainer = spotify.ffi.cast('sp_playlistcontainer *', 42)
        playlist_container = spotify.PlaylistContainer(
            self.session, sp_playlistcontainer=sp_playlistcontainer)

        self.assertIsInstance(playlist_container, collections.MutableSequence)

    @mock.patch('spotify.playlist.lib', lib=spotify.lib)
    def test_add_new_playlist_to_end_of_container(
            self, playlist_lib_mock, lib_mock):

        sp_playlistcontainer = spotify.ffi.cast('sp_playlistcontainer *', 42)
        playlist_container = spotify.PlaylistContainer(
            self.session, sp_playlistcontainer=sp_playlistcontainer)
        sp_playlist = spotify.ffi.cast('sp_playlist *', 43)
        lib_mock.sp_playlistcontainer_add_new_playlist.return_value = (
            sp_playlist)

        result = playlist_container.add_new_playlist('foo bar')

        lib_mock.sp_playlistcontainer_add_new_playlist.assert_called_with(
            sp_playlistcontainer, mock.ANY)
        self.assertEqual(
            spotify.ffi.string(
                lib_mock.sp_playlistcontainer_add_new_playlist
                .call_args[0][1]),
            b'foo bar')
        self.assertIsInstance(result, spotify.Playlist)
        self.assertEqual(result._sp_playlist, sp_playlist)
        playlist_lib_mock.sp_playlist_add_ref.assert_called_with(sp_playlist)
        self.assertEqual(
            lib_mock.sp_playlistcontainer_move_playlist.call_count, 0)

    @mock.patch('spotify.playlist.lib', lib=spotify.lib)
    def test_add_new_playlist_at_given_index(
            self, playlist_lib_mock, lib_mock):

        sp_playlistcontainer = spotify.ffi.cast('sp_playlistcontainer *', 42)
        playlist_container = spotify.PlaylistContainer(
            self.session, sp_playlistcontainer=sp_playlistcontainer)
        sp_playlist = spotify.ffi.cast('sp_playlist *', 43)
        lib_mock.sp_playlistcontainer_add_new_playlist.return_value = (
            sp_playlist)
        lib_mock.sp_playlistcontainer_num_playlists.return_value = 100
        lib_mock.sp_playlistcontainer_move_playlist.return_value = int(
            spotify.ErrorType.OK)

        result = playlist_container.add_new_playlist('foo bar', index=7)

        lib_mock.sp_playlistcontainer_add_new_playlist.assert_called_with(
            sp_playlistcontainer, mock.ANY)
        self.assertEqual(
            spotify.ffi.string(
                lib_mock.sp_playlistcontainer_add_new_playlist
                .call_args[0][1]),
            b'foo bar')
        self.assertIsInstance(result, spotify.Playlist)
        self.assertEqual(result._sp_playlist, sp_playlist)
        playlist_lib_mock.sp_playlist_add_ref.assert_called_with(sp_playlist)
        lib_mock.sp_playlistcontainer_move_playlist.assert_called_with(
            sp_playlistcontainer, 99, 7, 0)

    def test_add_new_playlist_fails_if_name_is_space_only(self, lib_mock):
        sp_playlistcontainer = spotify.ffi.cast('sp_playlistcontainer *', 42)
        playlist_container = spotify.PlaylistContainer(
            self.session, sp_playlistcontainer=sp_playlistcontainer)

        with self.assertRaises(ValueError):
            playlist_container.add_new_playlist('   ')

        # Spotify seems to accept e.g. tab-only names, but it doesn't make any
        # sense to allow it, so we disallow names with all combinations of just
        # whitespace.
        with self.assertRaises(ValueError):
            playlist_container.add_new_playlist('\t\t')
        with self.assertRaises(ValueError):
            playlist_container.add_new_playlist('\r\r')
        with self.assertRaises(ValueError):
            playlist_container.add_new_playlist('\n\n')
        with self.assertRaises(ValueError):
            playlist_container.add_new_playlist(' \t\r\n')

    def test_add_new_playlist_fails_if_name_is_too_long(self, lib_mock):
        sp_playlistcontainer = spotify.ffi.cast('sp_playlistcontainer *', 42)
        playlist_container = spotify.PlaylistContainer(
            self.session, sp_playlistcontainer=sp_playlistcontainer)

        with self.assertRaises(ValueError):
            playlist_container.add_new_playlist('x' * 300)

    def test_add_new_playlist_fails_if_operation_fails(self, lib_mock):
        lib_mock.sp_playlistcontainer_add_new_playlist.return_value = (
            spotify.ffi.NULL)
        sp_playlistcontainer = spotify.ffi.cast('sp_playlistcontainer *', 42)
        playlist_container = spotify.PlaylistContainer(
            self.session, sp_playlistcontainer=sp_playlistcontainer)

        with self.assertRaises(spotify.Error):
            playlist_container.add_new_playlist('foo bar')

    @mock.patch('spotify.link.lib', lib=spotify.lib)
    @mock.patch('spotify.playlist.lib', lib=spotify.lib)
    def test_add_playlist_from_link(
            self, playlist_lib_mock, link_lib_mock, lib_mock):
        sp_link = spotify.ffi.cast('sp_link *', 43)
        link = spotify.Link(self.session, sp_link=sp_link, add_ref=False)
        sp_playlist = spotify.ffi.cast('sp_playlist *', 44)
        lib_mock.sp_playlistcontainer_add_playlist.return_value = sp_playlist
        sp_playlistcontainer = spotify.ffi.cast('sp_playlistcontainer *', 42)
        playlist_container = spotify.PlaylistContainer(
            self.session, sp_playlistcontainer=sp_playlistcontainer)

        result = playlist_container.add_playlist(link)

        lib_mock.sp_playlistcontainer_add_playlist.assert_called_with(
            sp_playlistcontainer, sp_link)
        self.assertIsInstance(result, spotify.Playlist)
        self.assertEqual(result._sp_playlist, sp_playlist)
        playlist_lib_mock.sp_playlist_add_ref.assert_called_with(sp_playlist)
        self.assertEqual(
            lib_mock.sp_playlistcontainer_move_playlist.call_count, 0)

    @mock.patch('spotify.link.lib', lib=spotify.lib)
    @mock.patch('spotify.playlist.lib', lib=spotify.lib)
    def test_add_playlist_from_playlist(
            self, playlist_lib_mock, link_lib_mock, lib_mock):
        sp_link = spotify.ffi.cast('sp_link *', 43)
        link = spotify.Link(self.session, sp_link=sp_link, add_ref=False)
        existing_playlist = mock.Mock(spec=spotify.Playlist)
        existing_playlist.link = link
        added_sp_playlist = spotify.ffi.cast('sp_playlist *', 44)
        lib_mock.sp_playlistcontainer_add_playlist.return_value = (
            added_sp_playlist)
        sp_playlistcontainer = spotify.ffi.cast('sp_playlistcontainer *', 42)
        playlist_container = spotify.PlaylistContainer(
            self.session, sp_playlistcontainer=sp_playlistcontainer)

        result = playlist_container.add_playlist(existing_playlist)

        lib_mock.sp_playlistcontainer_add_playlist.assert_called_with(
            sp_playlistcontainer, sp_link)
        self.assertIsInstance(result, spotify.Playlist)
        self.assertEqual(result._sp_playlist, added_sp_playlist)
        playlist_lib_mock.sp_playlist_add_ref.assert_called_with(
            added_sp_playlist)
        self.assertEqual(
            lib_mock.sp_playlistcontainer_move_playlist.call_count, 0)

    @mock.patch('spotify.link.lib', lib=spotify.lib)
    @mock.patch('spotify.playlist.lib', lib=spotify.lib)
    def test_add_playlist_at_given_index(
            self, playlist_lib_mock, link_lib_mock, lib_mock):
        sp_link = spotify.ffi.cast('sp_link *', 43)
        link = spotify.Link(self.session, sp_link=sp_link, add_ref=False)
        sp_playlist = spotify.ffi.cast('sp_playlist *', 44)
        lib_mock.sp_playlistcontainer_add_playlist.return_value = sp_playlist
        sp_playlistcontainer = spotify.ffi.cast('sp_playlistcontainer *', 42)
        playlist_container = spotify.PlaylistContainer(
            self.session, sp_playlistcontainer=sp_playlistcontainer)
        lib_mock.sp_playlistcontainer_num_playlists.return_value = 100
        lib_mock.sp_playlistcontainer_move_playlist.return_value = int(
            spotify.ErrorType.OK)

        result = playlist_container.add_playlist(link, index=7)

        lib_mock.sp_playlistcontainer_add_playlist.assert_called_with(
            sp_playlistcontainer, sp_link)
        self.assertIsInstance(result, spotify.Playlist)
        self.assertEqual(result._sp_playlist, sp_playlist)
        playlist_lib_mock.sp_playlist_add_ref.assert_called_with(sp_playlist)
        lib_mock.sp_playlistcontainer_move_playlist.assert_called_with(
            sp_playlistcontainer, 99, 7, 0)

    @mock.patch('spotify.link.lib', lib=spotify.lib)
    def test_add_playlist_already_in_the_container(
            self, link_lib_mock, lib_mock):
        sp_link = spotify.ffi.cast('sp_link *', 43)
        link = spotify.Link(self.session, sp_link=sp_link, add_ref=False)
        lib_mock.sp_playlistcontainer_add_playlist.return_value = (
            spotify.ffi.NULL)
        sp_playlistcontainer = spotify.ffi.cast('sp_playlistcontainer *', 42)
        playlist_container = spotify.PlaylistContainer(
            self.session, sp_playlistcontainer=sp_playlistcontainer)

        result = playlist_container.add_playlist(link)

        lib_mock.sp_playlistcontainer_add_playlist.assert_called_with(
            sp_playlistcontainer, sp_link)
        self.assertIsNone(result)
        self.assertEqual(
            lib_mock.sp_playlistcontainer_move_playlist.call_count, 0)

    def test_add_playlist_from_unknown_type_fails(self, lib_mock):
        sp_playlistcontainer = spotify.ffi.cast('sp_playlistcontainer *', 42)
        playlist_container = spotify.PlaylistContainer(
            self.session, sp_playlistcontainer=sp_playlistcontainer)

        with self.assertRaises(TypeError):
            playlist_container.add_playlist(None)

    def test_add_folder(self, lib_mock):
        lib_mock.sp_playlistcontainer_add_folder.return_value = int(
            spotify.ErrorType.OK)
        sp_playlistcontainer = spotify.ffi.cast('sp_playlistcontainer *', 42)
        playlist_container = spotify.PlaylistContainer(
            self.session, sp_playlistcontainer=sp_playlistcontainer)

        playlist_container.add_folder('foo bar', index=3)

        lib_mock.sp_playlistcontainer_add_folder.assert_called_with(
            sp_playlistcontainer, 3, mock.ANY)
        self.assertEqual(
            spotify.ffi.string(
                lib_mock.sp_playlistcontainer_add_folder.call_args[0][2]),
            b'foo bar')

    def test_add_folder_without_index_adds_to_end(self, lib_mock):
        lib_mock.sp_playlistcontainer_num_playlists.return_value = 7
        lib_mock.sp_playlistcontainer_add_folder.return_value = int(
            spotify.ErrorType.OK)
        sp_playlistcontainer = spotify.ffi.cast('sp_playlistcontainer *', 42)
        playlist_container = spotify.PlaylistContainer(
            self.session, sp_playlistcontainer=sp_playlistcontainer)

        playlist_container.add_folder('foo bar')

        lib_mock.sp_playlistcontainer_add_folder.assert_called_with(
            sp_playlistcontainer, 7, mock.ANY)
        self.assertEqual(
            spotify.ffi.string(
                lib_mock.sp_playlistcontainer_add_folder.call_args[0][2]),
            b'foo bar')

    def test_add_folder_out_of_range_fails(self, lib_mock):
        lib_mock.sp_playlistcontainer_add_folder.return_value = int(
            spotify.ErrorType.INDEX_OUT_OF_RANGE)

        sp_playlistcontainer = spotify.ffi.cast('sp_playlistcontainer *', 42)
        playlist_container = spotify.PlaylistContainer(
            self.session, sp_playlistcontainer=sp_playlistcontainer)

        with self.assertRaises(spotify.Error):
            playlist_container.add_folder('foo bar', index=3)

    def test_add_folder_fails_if_name_is_space_only(self, lib_mock):
        sp_playlistcontainer = spotify.ffi.cast('sp_playlistcontainer *', 42)
        playlist_container = spotify.PlaylistContainer(
            self.session, sp_playlistcontainer=sp_playlistcontainer)

        with self.assertRaises(ValueError):
            playlist_container.add_folder('   ')

        # Spotify seems to accept e.g. tab-only names, but it doesn't make any
        # sense to allow it, so we disallow names with all combinations of just
        # whitespace.
        with self.assertRaises(ValueError):
            playlist_container.add_folder('\t\t')
        with self.assertRaises(ValueError):
            playlist_container.add_folder('\r\r')
        with self.assertRaises(ValueError):
            playlist_container.add_folder('\n\n')
        with self.assertRaises(ValueError):
            playlist_container.add_folder(' \t\r\n')

    def test_add_folder_fails_if_name_is_too_long(self, lib_mock):
        sp_playlistcontainer = spotify.ffi.cast('sp_playlistcontainer *', 42)
        playlist_container = spotify.PlaylistContainer(
            self.session, sp_playlistcontainer=sp_playlistcontainer)

        with self.assertRaises(ValueError):
            playlist_container.add_folder('x' * 300)

    @mock.patch('spotify.playlist.lib', lib=spotify.lib)
    def test_remove_playlist(self, playlist_lib_mock, lib_mock):
        sp_playlistcontainer = spotify.ffi.cast('sp_playlistcontainer *', 42)
        playlist_container = spotify.PlaylistContainer(
            self.session, sp_playlistcontainer=sp_playlistcontainer)
        lib_mock.sp_playlistcontainer_num_playlists.return_value = 9
        sp_playlist = spotify.ffi.cast('sp_playlist *', 43)
        lib_mock.sp_playlistcontainer_playlist.return_value = sp_playlist
        lib_mock.sp_playlistcontainer_playlist_type.return_value = int(
            spotify.PlaylistType.PLAYLIST)
        lib_mock.sp_playlistcontainer_remove_playlist.return_value = int(
            spotify.ErrorType.OK)

        playlist_container.remove_playlist(5)

        lib_mock.sp_playlistcontainer_remove_playlist.assert_called_with(
            sp_playlistcontainer, 5)

    @mock.patch('spotify.playlist.lib', lib=spotify.lib)
    def test_remove_playlist_out_of_range_fails(
            self, playlist_lib_mock, lib_mock):

        sp_playlistcontainer = spotify.ffi.cast('sp_playlistcontainer *', 42)
        playlist_container = spotify.PlaylistContainer(
            self.session, sp_playlistcontainer=sp_playlistcontainer)
        lib_mock.sp_playlistcontainer_num_playlists.return_value = 9
        sp_playlist = spotify.ffi.cast('sp_playlist *', 43)
        lib_mock.sp_playlistcontainer_playlist.return_value = sp_playlist
        lib_mock.sp_playlistcontainer_playlist_type.return_value = int(
            spotify.PlaylistType.PLAYLIST)
        lib_mock.sp_playlistcontainer_remove_playlist.return_value = int(
            spotify.ErrorType.INDEX_OUT_OF_RANGE)

        with self.assertRaises(spotify.Error):
            playlist_container.remove_playlist(3)

    def test_remove_start_folder_removes_end_folder_too(self, lib_mock):
        sp_playlistcontainer = spotify.ffi.cast('sp_playlistcontainer *', 42)
        playlist_container = spotify.PlaylistContainer(
            self.session, sp_playlistcontainer=sp_playlistcontainer)
        lib_mock.sp_playlistcontainer_num_playlists.return_value = 3
        sp_playlist = spotify.ffi.cast('sp_playlist *', 43)
        lib_mock.sp_playlistcontainer_playlist.return_value = sp_playlist
        lib_mock.sp_playlistcontainer_playlist_type.side_effect = [
            int(spotify.PlaylistType.START_FOLDER),
            int(spotify.PlaylistType.PLAYLIST),
            int(spotify.PlaylistType.END_FOLDER),
        ]
        lib_mock.sp_playlistcontainer_playlist_folder_id.side_effect = [
            173, 173]
        playlist_container._find_folder_indexes = lambda *a: [0, 2]
        lib_mock.sp_playlistcontainer_remove_playlist.return_value = int(
            spotify.ErrorType.OK)

        playlist_container.remove_playlist(0)

        lib_mock.sp_playlistcontainer_playlist_type.assert_called_with(
            sp_playlistcontainer, 0)
        lib_mock.sp_playlistcontainer_playlist_folder_id.assert_called_with(
            sp_playlistcontainer, 0)
        lib_mock.sp_playlistcontainer_remove_playlist.assert_has_calls([
            mock.call(sp_playlistcontainer, 2),
            mock.call(sp_playlistcontainer, 0),
        ], any_order=False)

    def test_remove_end_folder_removes_start_folder_too(self, lib_mock):
        sp_playlistcontainer = spotify.ffi.cast('sp_playlistcontainer *', 42)
        playlist_container = spotify.PlaylistContainer(
            self.session, sp_playlistcontainer=sp_playlistcontainer)
        lib_mock.sp_playlistcontainer_num_playlists.return_value = 3
        sp_playlist = spotify.ffi.cast('sp_playlist *', 43)
        lib_mock.sp_playlistcontainer_playlist.return_value = sp_playlist
        lib_mock.sp_playlistcontainer_playlist_type.side_effect = [
            int(spotify.PlaylistType.START_FOLDER),
            int(spotify.PlaylistType.PLAYLIST),
            int(spotify.PlaylistType.END_FOLDER),
        ]
        lib_mock.sp_playlistcontainer_playlist_folder_id.side_effect = [
            173, 173]
        playlist_container._find_folder_indexes = lambda *a: [0, 2]
        lib_mock.sp_playlistcontainer_remove_playlist.return_value = int(
            spotify.ErrorType.OK)

        playlist_container.remove_playlist(2)

        lib_mock.sp_playlistcontainer_playlist_type.assert_called_with(
            sp_playlistcontainer, 2)
        lib_mock.sp_playlistcontainer_playlist_folder_id.assert_called_with(
            sp_playlistcontainer, 2)
        lib_mock.sp_playlistcontainer_remove_playlist.assert_has_calls([
            mock.call(sp_playlistcontainer, 2),
            mock.call(sp_playlistcontainer, 0),
        ], any_order=False)

    def test_remove_folder_with_everything_in_it(self, lib_mock):
        sp_playlistcontainer = spotify.ffi.cast('sp_playlistcontainer *', 42)
        playlist_container = spotify.PlaylistContainer(
            self.session, sp_playlistcontainer=sp_playlistcontainer)
        lib_mock.sp_playlistcontainer_num_playlists.return_value = 3
        sp_playlist = spotify.ffi.cast('sp_playlist *', 43)
        lib_mock.sp_playlistcontainer_playlist.return_value = sp_playlist
        lib_mock.sp_playlistcontainer_playlist_type.side_effect = [
            int(spotify.PlaylistType.START_FOLDER),
            int(spotify.PlaylistType.PLAYLIST),
            int(spotify.PlaylistType.END_FOLDER),
        ]
        lib_mock.sp_playlistcontainer_playlist_folder_id.side_effect = [
            173, 173]
        playlist_container._find_folder_indexes = lambda *a: [0, 1, 2]
        lib_mock.sp_playlistcontainer_remove_playlist.return_value = int(
            spotify.ErrorType.OK)

        playlist_container.remove_playlist(0, recursive=True)

        lib_mock.sp_playlistcontainer_playlist_type.assert_called_with(
            sp_playlistcontainer, 0)
        lib_mock.sp_playlistcontainer_playlist_folder_id.assert_called_with(
            sp_playlistcontainer, 0)
        lib_mock.sp_playlistcontainer_remove_playlist.assert_has_calls([
            mock.call(sp_playlistcontainer, 2),
            mock.call(sp_playlistcontainer, 1),
            mock.call(sp_playlistcontainer, 0),
        ], any_order=False)

    @mock.patch('spotify.playlist.lib', spec=spotify.lib)
    def test_find_folder_indexes(self, playlist_lib_mock, lib_mock):
        sp_playlist = spotify.ffi.cast('sp_playlist *', 43)
        playlist = spotify.Playlist(self.session, sp_playlist=sp_playlist)
        playlists = [
            spotify.PlaylistFolder(
                173, 'foo', spotify.PlaylistType.START_FOLDER),
            playlist,
            spotify.PlaylistFolder(
                173, '', spotify.PlaylistType.END_FOLDER),
        ]

        result = spotify.PlaylistContainer._find_folder_indexes(
            playlists, 173, recursive=False)

        self.assertEqual(result, [0, 2])

    @mock.patch('spotify.playlist.lib', spec=spotify.lib)
    def test_find_folder_indexes_with_unknown_id(
            self, playlist_lib_mock, lib_mock):

        sp_playlist = spotify.ffi.cast('sp_playlist *', 43)
        playlist = spotify.Playlist(self.session, sp_playlist=sp_playlist)
        playlists = [
            spotify.PlaylistFolder(
                173, 'foo', spotify.PlaylistType.START_FOLDER),
            playlist,
            spotify.PlaylistFolder(
                173, '', spotify.PlaylistType.END_FOLDER),
        ]

        result = spotify.PlaylistContainer._find_folder_indexes(
            playlists, 174, recursive=False)

        self.assertEqual(result, [])

    @mock.patch('spotify.playlist.lib', spec=spotify.lib)
    def test_find_folder_indexes_recursive(self, playlist_lib_mock, lib_mock):
        sp_playlist = spotify.ffi.cast('sp_playlist *', 43)
        playlist = spotify.Playlist(self.session, sp_playlist=sp_playlist)
        playlists = [
            spotify.PlaylistFolder(
                173, 'foo', spotify.PlaylistType.START_FOLDER),
            playlist,
            spotify.PlaylistFolder(
                173, '', spotify.PlaylistType.END_FOLDER),
        ]

        result = spotify.PlaylistContainer._find_folder_indexes(
            playlists, 173, recursive=True)

        self.assertEqual(result, [0, 1, 2])

    @mock.patch('spotify.playlist.lib', spec=spotify.lib)
    def test_find_folder_indexes_without_end(
            self, playlist_lib_mock, lib_mock):

        sp_playlist = spotify.ffi.cast('sp_playlist *', 43)
        playlist = spotify.Playlist(self.session, sp_playlist=sp_playlist)
        playlists = [
            spotify.PlaylistFolder(
                173, 'foo', spotify.PlaylistType.START_FOLDER),
            playlist,
        ]

        result = spotify.PlaylistContainer._find_folder_indexes(
            playlists, 173, recursive=True)

        self.assertEqual(result, [0])

    @mock.patch('spotify.playlist.lib', spec=spotify.lib)
    def test_find_folder_indexes_without_start(
            self, playlist_lib_mock, lib_mock):

        sp_playlist = spotify.ffi.cast('sp_playlist *', 43)
        playlist = spotify.Playlist(self.session, sp_playlist=sp_playlist)
        playlists = [
            playlist,
            spotify.PlaylistFolder(
                173, '', spotify.PlaylistType.END_FOLDER),
        ]

        result = spotify.PlaylistContainer._find_folder_indexes(
            playlists, 173, recursive=True)

        self.assertEqual(result, [1])

    def test_move_playlist(self, lib_mock):
        lib_mock.sp_playlistcontainer_move_playlist.return_value = int(
            spotify.ErrorType.OK)
        sp_playlistcontainer = spotify.ffi.cast('sp_playlistcontainer *', 42)
        playlist_container = spotify.PlaylistContainer(
            self.session, sp_playlistcontainer=sp_playlistcontainer)

        playlist_container.move_playlist(5, 7)

        lib_mock.sp_playlistcontainer_move_playlist.assert_called_with(
            sp_playlistcontainer, 5, 7, 0)

    def test_move_playlist_dry_run(self, lib_mock):
        lib_mock.sp_playlistcontainer_move_playlist.return_value = int(
            spotify.ErrorType.OK)
        sp_playlistcontainer = spotify.ffi.cast('sp_playlistcontainer *', 42)
        playlist_container = spotify.PlaylistContainer(
            self.session, sp_playlistcontainer=sp_playlistcontainer)

        playlist_container.move_playlist(5, 7, dry_run=True)

        lib_mock.sp_playlistcontainer_move_playlist.assert_called_with(
            sp_playlistcontainer, 5, 7, 1)

    def test_move_playlist_out_of_range_fails(self, lib_mock):
        lib_mock.sp_playlistcontainer_move_playlist.return_value = int(
            spotify.ErrorType.INDEX_OUT_OF_RANGE)
        sp_playlistcontainer = spotify.ffi.cast('sp_playlistcontainer *', 42)
        playlist_container = spotify.PlaylistContainer(
            self.session, sp_playlistcontainer=sp_playlistcontainer)

        with self.assertRaises(spotify.Error):
            playlist_container.move_playlist(5, 7)

    @mock.patch('spotify.User', spec=spotify.User)
    def test_owner(self, user_mock, lib_mock):
        user_mock.return_value = mock.sentinel.user
        sp_user = spotify.ffi.cast('sp_user *', 43)
        lib_mock.sp_playlistcontainer_owner.return_value = sp_user
        sp_playlistcontainer = spotify.ffi.cast('sp_playlistcontainer *', 42)
        playlist_container = spotify.PlaylistContainer(
            self.session, sp_playlistcontainer=sp_playlistcontainer)

        result = playlist_container.owner

        lib_mock.sp_playlistcontainer_owner.assert_called_with(
            sp_playlistcontainer)
        user_mock.assert_called_with(
            self.session, sp_user=sp_user, add_ref=True)
        self.assertEqual(result, mock.sentinel.user)

    @mock.patch('spotify.playlist.lib', spec=spotify.lib)
    @mock.patch('spotify.playlist_unseen_tracks.lib', spec=spotify.lib)
    def test_get_unseen_tracks(
            self, unseen_lib_mock, playlist_lib_mock, lib_mock):

        sp_playlistcontainer = spotify.ffi.cast('sp_playlistcontainer *', 42)
        playlist_container = spotify.PlaylistContainer(
            self.session, sp_playlistcontainer=sp_playlistcontainer)
        sp_playlist = spotify.ffi.cast('sp_playlist *', 43)
        playlist = spotify.Playlist(self.session, sp_playlist=sp_playlist)
        unseen_lib_mock.sp_playlistcontainer_get_unseen_tracks.return_value = 0

        result = playlist_container.get_unseen_tracks(playlist)

        self.assertIsInstance(result, spotify.PlaylistUnseenTracks)
        self.assertEqual(len(result), 0)

    @mock.patch('spotify.playlist.lib', spec=spotify.lib)
    def test_clear_unseen_tracks(self, playlist_lib_mock, lib_mock):
        sp_playlistcontainer = spotify.ffi.cast('sp_playlistcontainer *', 42)
        playlist_container = spotify.PlaylistContainer(
            self.session, sp_playlistcontainer=sp_playlistcontainer)
        sp_playlist = spotify.ffi.cast('sp_playlist *', 43)
        playlist = spotify.Playlist(self.session, sp_playlist=sp_playlist)
        lib_mock.sp_playlistcontainer_clear_unseen_tracks.return_value = 0

        playlist_container.clear_unseen_tracks(playlist)

        lib_mock.sp_playlistcontainer_clear_unseen_tracks.assert_called_with(
            sp_playlistcontainer, sp_playlist)

    @mock.patch('spotify.playlist.lib', spec=spotify.lib)
    def test_clear_unseen_tracks_raises_error_on_failure(
            self, playlist_lib_mock, lib_mock):

        sp_playlistcontainer = spotify.ffi.cast('sp_playlistcontainer *', 42)
        playlist_container = spotify.PlaylistContainer(
            self.session, sp_playlistcontainer=sp_playlistcontainer)
        sp_playlist = spotify.ffi.cast('sp_playlist *', 43)
        playlist = spotify.Playlist(self.session, sp_playlist=sp_playlist)
        lib_mock.sp_playlistcontainer_clear_unseen_tracks.return_value = -1

        with self.assertRaises(spotify.Error):
            playlist_container.clear_unseen_tracks(playlist)

    def test_first_on_call_adds_obj_emitters_list(self, lib_mock):
        sp_playlistcontainer = spotify.ffi.cast('sp_playlistcontainer *', 42)
        playlist_container = spotify.PlaylistContainer(
            self.session, sp_playlistcontainer=sp_playlistcontainer)

        playlist_container.on(
            spotify.PlaylistContainerEvent.PLAYLIST_ADDED, lambda *args: None)

        self.assertIn(playlist_container, self.session._emitters)

        playlist_container.off()

    def test_last_off_call_removes_obj_from_emitters_list(self, lib_mock):
        sp_playlistcontainer = spotify.ffi.cast('sp_playlistcontainer *', 42)
        playlist_container = spotify.PlaylistContainer(
            self.session, sp_playlistcontainer=sp_playlistcontainer)

        playlist_container.on(
            spotify.PlaylistContainerEvent.PLAYLIST_ADDED, lambda *args: None)
        playlist_container.off(
            spotify.PlaylistContainerEvent.PLAYLIST_ADDED)

        self.assertNotIn(playlist_container, self.session._emitters)

    def test_other_off_calls_keeps_obj_in_emitters_list(self, lib_mock):
        sp_playlistcontainer = spotify.ffi.cast('sp_playlistcontainer *', 42)
        playlist_container = spotify.PlaylistContainer(
            self.session, sp_playlistcontainer=sp_playlistcontainer)

        playlist_container.on(
            spotify.PlaylistContainerEvent.PLAYLIST_ADDED, lambda *args: None)
        playlist_container.on(
            spotify.PlaylistContainerEvent.PLAYLIST_MOVED, lambda *args: None)
        playlist_container.off(
            spotify.PlaylistContainerEvent.PLAYLIST_ADDED)

        self.assertIn(playlist_container, self.session._emitters)

        playlist_container.off(
            spotify.PlaylistContainerEvent.PLAYLIST_MOVED)

        self.assertNotIn(playlist_container, self.session._emitters)


@mock.patch('spotify.playlist_container.lib', spec=spotify.lib)
class PlaylistContainerCallbacksTest(unittest.TestCase):

    def setUp(self):
        self.session = tests.create_session_mock()
        spotify._session_instance = self.session

    def tearDown(self):
        spotify._session_instance = None

    @mock.patch('spotify.playlist.lib', spec=spotify.lib)
    def test_playlist_added_callback(self, playlist_lib_mock, lib_mock):
        callback = mock.Mock()
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        sp_playlistcontainer = spotify.ffi.cast('sp_playlistcontainer *', 43)
        playlist_container = spotify.PlaylistContainer._cached(
            self.session, sp_playlistcontainer=sp_playlistcontainer)
        playlist_container.on(
            spotify.PlaylistContainerEvent.PLAYLIST_ADDED, callback)

        _PlaylistContainerCallbacks.playlist_added(
            sp_playlistcontainer, sp_playlist, 7, spotify.ffi.NULL)

        callback.assert_called_once_with(playlist_container, mock.ANY, 7)
        playlist = callback.call_args[0][1]
        self.assertIsInstance(playlist, spotify.Playlist)
        self.assertEqual(playlist._sp_playlist, sp_playlist)

    @mock.patch('spotify.playlist.lib', spec=spotify.lib)
    def test_playlist_removed_callback(self, playlist_lib_mock, lib_mock):
        callback = mock.Mock()
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        sp_playlistcontainer = spotify.ffi.cast('sp_playlistcontainer *', 43)
        playlist_container = spotify.PlaylistContainer._cached(
            self.session, sp_playlistcontainer=sp_playlistcontainer)
        playlist_container.on(
            spotify.PlaylistContainerEvent.PLAYLIST_REMOVED, callback)

        _PlaylistContainerCallbacks.playlist_removed(
            sp_playlistcontainer, sp_playlist, 7, spotify.ffi.NULL)

        callback.assert_called_once_with(playlist_container, mock.ANY, 7)
        playlist = callback.call_args[0][1]
        self.assertIsInstance(playlist, spotify.Playlist)
        self.assertEqual(playlist._sp_playlist, sp_playlist)

    @mock.patch('spotify.playlist.lib', spec=spotify.lib)
    def test_playlist_moved_callback(self, playlist_lib_mock, lib_mock):
        callback = mock.Mock()
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        sp_playlistcontainer = spotify.ffi.cast('sp_playlistcontainer *', 43)
        playlist_container = spotify.PlaylistContainer._cached(
            self.session, sp_playlistcontainer=sp_playlistcontainer)
        playlist_container.on(
            spotify.PlaylistContainerEvent.PLAYLIST_MOVED, callback)

        _PlaylistContainerCallbacks.playlist_moved(
            sp_playlistcontainer, sp_playlist, 7, 13, spotify.ffi.NULL)

        callback.assert_called_once_with(playlist_container, mock.ANY, 7, 13)
        playlist = callback.call_args[0][1]
        self.assertIsInstance(playlist, spotify.Playlist)
        self.assertEqual(playlist._sp_playlist, sp_playlist)

    def test_container_loaded_callback(self, lib_mock):
        callback = mock.Mock()
        sp_playlistcontainer = spotify.ffi.cast('sp_playlistcontainer *', 43)
        playlist_container = spotify.PlaylistContainer._cached(
            self.session, sp_playlistcontainer=sp_playlistcontainer)
        playlist_container.on(
            spotify.PlaylistContainerEvent.CONTAINER_LOADED, callback)

        _PlaylistContainerCallbacks.container_loaded(
            sp_playlistcontainer, spotify.ffi.NULL)

        callback.assert_called_once_with(playlist_container)


class PlaylistFolderTest(unittest.TestCase):

    def test_id(self):
        folder = spotify.PlaylistFolder(
            id=123, name='foo', type=spotify.PlaylistType.START_FOLDER)

        self.assertEqual(folder.id, 123)

    def test_image(self):
        folder = spotify.PlaylistFolder(
            id=123, name='foo', type=spotify.PlaylistType.START_FOLDER)

        self.assertEqual(folder.name, 'foo')

    def test_type(self):
        folder = spotify.PlaylistFolder(
            id=123, name='foo', type=spotify.PlaylistType.START_FOLDER)

        self.assertEqual(folder.type, spotify.PlaylistType.START_FOLDER)


class PlaylistTypeTest(unittest.TestCase):

    def test_has_constants(self):
        self.assertEqual(spotify.PlaylistType.PLAYLIST, 0)
        self.assertEqual(spotify.PlaylistType.START_FOLDER, 1)
        self.assertEqual(spotify.PlaylistType.END_FOLDER, 2)

########NEW FILE########
__FILENAME__ = test_playlist_track
from __future__ import unicode_literals

import unittest

import spotify
import tests
from tests import mock


@mock.patch('spotify.playlist_track.lib', spec=spotify.lib)
class PlaylistTrackTest(unittest.TestCase):

    def setUp(self):
        self.session = tests.create_session_mock()

    @mock.patch('spotify.track.lib', spec=spotify.lib)
    def test_track(self, track_lib_mock, lib_mock):
        sp_track = spotify.ffi.cast('sp_track *', 43)
        lib_mock.sp_playlist_track.return_value = sp_track
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist_track = spotify.PlaylistTrack(self.session, sp_playlist, 0)

        result = playlist_track.track

        lib_mock.sp_playlist_track.assert_called_with(sp_playlist, 0)
        track_lib_mock.sp_track_add_ref.assert_called_with(sp_track)
        self.assertIsInstance(result, spotify.Track)
        self.assertEqual(result._sp_track, sp_track)

    @mock.patch('spotify.Track', spec=spotify.Track)
    @mock.patch('spotify.User', spec=spotify.User)
    def test_repr(self, user_mock, track_mock, lib_mock):
        sp_track = spotify.ffi.cast('sp_track *', 43)
        lib_mock.sp_playlist_track.return_value = sp_track
        track_instance_mock = track_mock.return_value
        track_instance_mock.link.uri = 'foo'

        lib_mock.sp_playlist_track_create_time.return_value = 1234567890

        sp_user = spotify.ffi.cast('sp_user *', 44)
        lib_mock.sp_playlist_track_creator.return_value = sp_user
        user_mock.return_value = 'alice-user-object'

        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist_track = spotify.PlaylistTrack(self.session, sp_playlist, 0)

        result = repr(playlist_track)

        self.assertEqual(
            result,
            'PlaylistTrack(uri=%r, creator=%r, create_time=%d)' % (
                'foo', 'alice-user-object', 1234567890))

    def test_eq(self, lib_mock):
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        track1 = spotify.PlaylistTrack(self.session, sp_playlist, 0)
        track2 = spotify.PlaylistTrack(self.session, sp_playlist, 0)

        self.assertTrue(track1 == track2)
        self.assertFalse(track1 == 'foo')

    def test_ne(self, lib_mock):
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        track1 = spotify.PlaylistTrack(self.session, sp_playlist, 0)
        track2 = spotify.PlaylistTrack(self.session, sp_playlist, 0)
        track3 = spotify.PlaylistTrack(self.session, sp_playlist, 1)

        self.assertFalse(track1 != track2)
        self.assertTrue(track1 != track3)

    def test_hash(self, lib_mock):
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        track1 = spotify.PlaylistTrack(self.session, sp_playlist, 0)
        track2 = spotify.PlaylistTrack(self.session, sp_playlist, 0)
        track3 = spotify.PlaylistTrack(self.session, sp_playlist, 1)

        self.assertEqual(hash(track1), hash(track2))
        self.assertNotEqual(hash(track1), hash(track3))

    def test_create_time(self, lib_mock):
        lib_mock.sp_playlist_track_create_time.return_value = 1234567890
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist_track = spotify.PlaylistTrack(self.session, sp_playlist, 0)

        result = playlist_track.create_time

        lib_mock.sp_playlist_track_create_time.assert_called_with(
            sp_playlist, 0)
        self.assertEqual(result, 1234567890)

    @mock.patch('spotify.user.lib', spec=spotify.lib)
    def test_creator(self, user_lib_mock, lib_mock):
        sp_user = spotify.ffi.cast('sp_user *', 43)
        lib_mock.sp_playlist_track_creator.return_value = sp_user
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist_track = spotify.PlaylistTrack(self.session, sp_playlist, 0)

        result = playlist_track.creator

        lib_mock.sp_playlist_track_creator.assert_called_with(sp_playlist, 0)
        user_lib_mock.sp_user_add_ref.assert_called_with(sp_user)
        self.assertIsInstance(result, spotify.User)
        self.assertEqual(result._sp_user, sp_user)

    def test_is_seen(self, lib_mock):
        lib_mock.sp_playlist_track_seen.return_value = 0
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist_track = spotify.PlaylistTrack(self.session, sp_playlist, 0)

        result = playlist_track.seen

        lib_mock.sp_playlist_track_seen.assert_called_with(sp_playlist, 0)
        self.assertEqual(result, False)

    def test_set_seen(self, lib_mock):
        lib_mock.sp_playlist_track_set_seen.return_value = int(
            spotify.ErrorType.OK)
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist_track = spotify.PlaylistTrack(self.session, sp_playlist, 0)

        playlist_track.seen = True

        lib_mock.sp_playlist_track_set_seen.assert_called_with(
            sp_playlist, 0, 1)

    def test_set_seen_fails_if_error(self, lib_mock):
        lib_mock.sp_playlist_track_set_seen.return_value = int(
            spotify.ErrorType.BAD_API_VERSION)
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist_track = spotify.PlaylistTrack(self.session, sp_playlist, 0)

        with self.assertRaises(spotify.Error):
            playlist_track.seen = True

    def test_message(self, lib_mock):
        lib_mock.sp_playlist_track_message.return_value = spotify.ffi.new(
            'char[]', b'foo bar')
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist_track = spotify.PlaylistTrack(self.session, sp_playlist, 0)

        result = playlist_track.message

        lib_mock.sp_playlist_track_message.assert_called_with(sp_playlist, 0)
        self.assertEqual(result, 'foo bar')

    def test_message_is_none_when_null(self, lib_mock):
        lib_mock.sp_playlist_track_message.return_value = spotify.ffi.NULL
        sp_playlist = spotify.ffi.cast('sp_playlist *', 42)
        playlist_track = spotify.PlaylistTrack(self.session, sp_playlist, 0)

        result = playlist_track.message

        lib_mock.sp_playlist_track_message.assert_called_with(sp_playlist, 0)
        self.assertIsNone(result)

########NEW FILE########
__FILENAME__ = test_playlist_unseen_tracks
from __future__ import unicode_literals

import unittest

import spotify
import tests
from tests import mock


@mock.patch('spotify.playlist_unseen_tracks.lib', spec=spotify.lib)
class PlaylistUnseenTracksTest(unittest.TestCase):

    # TODO Test that the collection releases sp_playlistcontainer and
    # sp_playlist when no longer referenced.

    def setUp(self):
        self.session = tests.create_session_mock()

    @mock.patch('spotify.track.lib', spec=spotify.lib)
    def test_normal_usage(self, track_lib_mock, lib_mock):
        sp_playlistcontainer = spotify.ffi.cast('sp_playlistcontainer *', 42)
        sp_playlist = spotify.ffi.cast('sp_playlist *', 43)

        total_num_tracks = 3
        sp_tracks = [
            spotify.ffi.cast('sp_track *', 44 + i)
            for i in range(total_num_tracks)]

        def func(sp_pc, sp_p, sp_t, num_t):
            for i in range(min(total_num_tracks, num_t)):
                sp_t[i] = sp_tracks[i]
            return total_num_tracks

        lib_mock.sp_playlistcontainer_get_unseen_tracks.side_effect = func

        tracks = spotify.PlaylistUnseenTracks(
            self.session, sp_playlistcontainer, sp_playlist)

        # Collection keeps references to container and playlist:
        lib_mock.sp_playlistcontainer_add_ref.assert_called_with(
            sp_playlistcontainer)
        lib_mock.sp_playlist_add_ref.assert_called_with(sp_playlist)

        # Getting collection and length causes no tracks to be retrieved:
        self.assertEqual(len(tracks), total_num_tracks)
        self.assertEqual(
            lib_mock.sp_playlistcontainer_get_unseen_tracks.call_count, 1)
        lib_mock.sp_playlistcontainer_get_unseen_tracks.assert_called_with(
            sp_playlistcontainer, sp_playlist, mock.ANY, 0)

        # Getting items causes more tracks to be retrieved:
        track0 = tracks[0]
        self.assertEqual(
            lib_mock.sp_playlistcontainer_get_unseen_tracks.call_count, 2)
        lib_mock.sp_playlistcontainer_get_unseen_tracks.assert_called_with(
            sp_playlistcontainer, sp_playlist, mock.ANY, total_num_tracks)
        self.assertIsInstance(track0, spotify.Track)
        self.assertEqual(track0._sp_track, sp_tracks[0])

        # Getting alrady retrieved tracks causes no new retrieval:
        track1 = tracks[1]
        self.assertEqual(
            lib_mock.sp_playlistcontainer_get_unseen_tracks.call_count, 2)
        self.assertIsInstance(track1, spotify.Track)
        self.assertEqual(track1._sp_track, sp_tracks[1])

        # Getting item with negative index
        track2 = tracks[-3]
        self.assertEqual(track2._sp_track, track0._sp_track)
        self.assertEqual(
            lib_mock.sp_playlistcontainer_get_unseen_tracks.call_count, 2)

    def test_raises_error_on_failure(self, lib_mock):
        sp_playlistcontainer = spotify.ffi.cast('sp_playlistcontainer *', 42)
        sp_playlist = spotify.ffi.cast('sp_playlist *', 43)
        lib_mock.sp_playlistcontainer_get_unseen_tracks.return_value = -3

        with self.assertRaises(spotify.Error):
            spotify.PlaylistUnseenTracks(
                self.session, sp_playlistcontainer, sp_playlist)

    @mock.patch('spotify.track.lib', spec=spotify.lib)
    def test_getitem_with_slice(self, track_lib_mock, lib_mock):
        sp_playlistcontainer = spotify.ffi.cast('sp_playlistcontainer *', 42)
        sp_playlist = spotify.ffi.cast('sp_playlist *', 43)

        total_num_tracks = 3
        sp_tracks = [
            spotify.ffi.cast('sp_track *', 44 + i)
            for i in range(total_num_tracks)]

        def func(sp_pc, sp_p, sp_t, num_t):
            for i in range(min(total_num_tracks, num_t)):
                sp_t[i] = sp_tracks[i]
            return total_num_tracks

        lib_mock.sp_playlistcontainer_get_unseen_tracks.side_effect = func

        tracks = spotify.PlaylistUnseenTracks(
            self.session, sp_playlistcontainer, sp_playlist)

        result = tracks[0:2]

        # Only a subslice of length 2 is returned
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        self.assertIsInstance(result[0], spotify.Track)
        self.assertEqual(result[0]._sp_track, sp_tracks[0])
        self.assertIsInstance(result[1], spotify.Track)
        self.assertEqual(result[1]._sp_track, sp_tracks[1])

    def test_getitem_raises_index_error_on_too_low_index(self, lib_mock):
        sp_playlistcontainer = spotify.ffi.cast('sp_playlistcontainer *', 42)
        sp_playlist = spotify.ffi.cast('sp_playlist *', 43)
        lib_mock.sp_playlistcontainer_get_unseen_tracks.return_value = 0
        tracks = spotify.PlaylistUnseenTracks(
            self.session, sp_playlistcontainer, sp_playlist)

        with self.assertRaises(IndexError) as ctx:
            tracks[-1]

        self.assertEqual(str(ctx.exception), 'list index out of range')

    def test_getitem_raises_index_error_on_too_high_index(self, lib_mock):
        sp_playlistcontainer = spotify.ffi.cast('sp_playlistcontainer *', 42)
        sp_playlist = spotify.ffi.cast('sp_playlist *', 43)
        lib_mock.sp_playlistcontainer_get_unseen_tracks.return_value = 0
        tracks = spotify.PlaylistUnseenTracks(
            self.session, sp_playlistcontainer, sp_playlist)

        with self.assertRaises(IndexError) as ctx:
            tracks[1]

        self.assertEqual(str(ctx.exception), 'list index out of range')

    def test_getitem_raises_type_error_on_non_integral_index(self, lib_mock):
        sp_playlistcontainer = spotify.ffi.cast('sp_playlistcontainer *', 42)
        sp_playlist = spotify.ffi.cast('sp_playlist *', 43)
        lib_mock.sp_playlistcontainer_get_unseen_tracks.return_value = 0
        tracks = spotify.PlaylistUnseenTracks(
            self.session, sp_playlistcontainer, sp_playlist)

        with self.assertRaises(TypeError):
            tracks['abc']

    def test_repr(self, lib_mock):
        sp_playlistcontainer = spotify.ffi.cast('sp_playlistcontainer *', 42)
        sp_playlist = spotify.ffi.cast('sp_playlist *', 43)
        lib_mock.sp_playlistcontainer_get_unseen_tracks.return_value = 0
        tracks = spotify.PlaylistUnseenTracks(
            self.session, sp_playlistcontainer, sp_playlist)

        self.assertEqual(repr(tracks), 'PlaylistUnseenTracks([])')

########NEW FILE########
__FILENAME__ = test_search
from __future__ import unicode_literals

import unittest

import spotify
import tests
from tests import mock


@mock.patch('spotify.search.lib', spec=spotify.lib)
class SearchTest(unittest.TestCase):

    def setUp(self):
        self.session = tests.create_session_mock()
        spotify._session_instance = self.session

    def tearDown(self):
        spotify._session_instance = None

    def assert_fails_if_error(self, lib_mock, func):
        lib_mock.sp_search_error.return_value = (
            spotify.ErrorType.BAD_API_VERSION)
        sp_search = spotify.ffi.cast('sp_search *', 42)
        search = spotify.Search(self.session, sp_search=sp_search)

        with self.assertRaises(spotify.Error):
            func(search)

    def test_create_without_query_or_sp_search_fails(self, lib_mock):
        with self.assertRaises(AssertionError):
            spotify.Search(self.session)

    def test_search(self, lib_mock):
        sp_search = spotify.ffi.cast('sp_search *', 42)
        lib_mock.sp_search_create.return_value = sp_search

        result = spotify.Search(self.session, query='alice')

        lib_mock.sp_search_create.assert_called_with(
            self.session._sp_session, mock.ANY,
            0, 20, 0, 20, 0, 20, 0, 20,
            int(spotify.SearchType.STANDARD), mock.ANY, mock.ANY)
        self.assertEqual(
            spotify.ffi.string(lib_mock.sp_search_create.call_args[0][1]),
            b'alice')
        self.assertEqual(lib_mock.sp_search_add_ref.call_count, 0)
        self.assertIsInstance(result, spotify.Search)

        self.assertFalse(result.loaded_event.is_set())
        search_complete_cb = lib_mock.sp_search_create.call_args[0][11]
        userdata = lib_mock.sp_search_create.call_args[0][12]
        search_complete_cb(sp_search, userdata)
        self.assertTrue(result.loaded_event.wait(3))

    def test_search_with_callback(self, lib_mock):
        sp_search = spotify.ffi.cast('sp_search *', 42)
        lib_mock.sp_search_create.return_value = sp_search
        callback = mock.Mock()

        result = spotify.Search(self.session, query='alice', callback=callback)

        search_complete_cb = lib_mock.sp_search_create.call_args[0][11]
        userdata = lib_mock.sp_search_create.call_args[0][12]
        search_complete_cb(sp_search, userdata)

        result.loaded_event.wait(3)
        callback.assert_called_with(result)

    def test_search_where_result_is_gone_before_callback_is_called(
            self, lib_mock):

        sp_search = spotify.ffi.cast('sp_search *', 42)
        lib_mock.sp_search_create.return_value = sp_search
        callback = mock.Mock()

        result = spotify.Search(self.session, query='alice', callback=callback)
        loaded_event = result.loaded_event
        result = None  # noqa
        tests.gc_collect()

        # The mock keeps the handle/userdata alive, thus this test doesn't
        # really test that session._callback_handles keeps the handle alive.
        search_complete_cb = lib_mock.sp_search_create.call_args[0][11]
        userdata = lib_mock.sp_search_create.call_args[0][12]
        search_complete_cb(sp_search, userdata)

        loaded_event.wait(3)
        self.assertEqual(callback.call_count, 1)
        self.assertEqual(callback.call_args[0][0]._sp_search, sp_search)

    def test_adds_ref_to_sp_search_when_created(self, lib_mock):
        sp_search = spotify.ffi.cast('sp_search *', 42)

        spotify.Search(self.session, sp_search=sp_search)

        lib_mock.sp_search_add_ref.assert_called_with(sp_search)

    def test_releases_sp_search_when_search_dies(self, lib_mock):
        sp_search = spotify.ffi.cast('sp_search *', 42)

        search = spotify.Search(self.session, sp_search=sp_search)
        search = None  # noqa
        tests.gc_collect()

        lib_mock.sp_search_release.assert_called_with(sp_search)

    def test_loaded_event_is_unset_by_default(self, lib_mock):
        sp_search = spotify.ffi.cast('sp_search *', 42)
        search = spotify.Search(self.session, sp_search=sp_search)

        self.assertFalse(search.loaded_event.is_set())

    @mock.patch('spotify.Link', spec=spotify.Link)
    def test_repr(self, link_mock, lib_mock):
        link_instance_mock = link_mock.return_value
        link_instance_mock.uri = 'foo'
        sp_search = spotify.ffi.cast('sp_search *', 42)
        search = spotify.Search(self.session, sp_search=sp_search)

        result = repr(search)

        self.assertEqual(result, 'Search(%r)' % 'foo')

    def test_eq(self, lib_mock):
        sp_search = spotify.ffi.cast('sp_search *', 42)
        search1 = spotify.Search(self.session, sp_search=sp_search)
        search2 = spotify.Search(self.session, sp_search=sp_search)

        self.assertTrue(search1 == search2)
        self.assertFalse(search1 == 'foo')

    def test_ne(self, lib_mock):
        sp_search = spotify.ffi.cast('sp_search *', 42)
        search1 = spotify.Search(self.session, sp_search=sp_search)
        search2 = spotify.Search(self.session, sp_search=sp_search)

        self.assertFalse(search1 != search2)

    def test_hash(self, lib_mock):
        sp_search = spotify.ffi.cast('sp_search *', 42)
        search1 = spotify.Search(self.session, sp_search=sp_search)
        search2 = spotify.Search(self.session, sp_search=sp_search)

        self.assertEqual(hash(search1), hash(search2))

    def test_is_loaded(self, lib_mock):
        lib_mock.sp_search_is_loaded.return_value = 1
        sp_search = spotify.ffi.cast('sp_search *', 42)
        search = spotify.Search(self.session, sp_search=sp_search)

        result = search.is_loaded

        lib_mock.sp_search_is_loaded.assert_called_once_with(sp_search)
        self.assertTrue(result)

    def test_error(self, lib_mock):
        lib_mock.sp_search_error.return_value = int(
            spotify.ErrorType.IS_LOADING)
        sp_search = spotify.ffi.cast('sp_search *', 42)
        search = spotify.Search(self.session, sp_search=sp_search)

        result = search.error

        lib_mock.sp_search_error.assert_called_once_with(sp_search)
        self.assertIs(result, spotify.ErrorType.IS_LOADING)

    @mock.patch('spotify.utils.load')
    def test_load(self, load_mock, lib_mock):
        sp_search = spotify.ffi.cast('sp_search *', 42)
        search = spotify.Search(self.session, sp_search=sp_search)

        search.load(10)

        load_mock.assert_called_with(self.session, search, timeout=10)

    @mock.patch('spotify.track.lib', spec=spotify.lib)
    def test_tracks(self, track_lib_mock, lib_mock):
        lib_mock.sp_search_error.return_value = spotify.ErrorType.OK
        sp_track = spotify.ffi.cast('sp_track *', 43)
        lib_mock.sp_search_num_tracks.return_value = 1
        lib_mock.sp_search_track.return_value = sp_track
        sp_search = spotify.ffi.cast('sp_search *', 42)
        search = spotify.Search(self.session, sp_search=sp_search)

        self.assertEqual(lib_mock.sp_search_add_ref.call_count, 1)
        result = search.tracks
        self.assertEqual(lib_mock.sp_search_add_ref.call_count, 2)

        self.assertEqual(len(result), 1)
        lib_mock.sp_search_num_tracks.assert_called_with(sp_search)

        item = result[0]
        self.assertIsInstance(item, spotify.Track)
        self.assertEqual(item._sp_track, sp_track)
        self.assertEqual(lib_mock.sp_search_track.call_count, 1)
        lib_mock.sp_search_track.assert_called_with(sp_search, 0)
        track_lib_mock.sp_track_add_ref.assert_called_with(sp_track)

    def test_tracks_if_no_tracks(self, lib_mock):
        lib_mock.sp_search_error.return_value = spotify.ErrorType.OK
        lib_mock.sp_search_num_tracks.return_value = 0
        sp_search = spotify.ffi.cast('sp_search *', 42)
        search = spotify.Search(self.session, sp_search=sp_search)

        result = search.tracks

        self.assertEqual(len(result), 0)
        lib_mock.sp_search_num_tracks.assert_called_with(sp_search)
        self.assertEqual(lib_mock.sp_search_track.call_count, 0)

    def test_tracks_if_unloaded(self, lib_mock):
        lib_mock.sp_search_error.return_value = spotify.ErrorType.IS_LOADING
        lib_mock.sp_search_is_loaded.return_value = 0
        sp_search = spotify.ffi.cast('sp_search *', 42)
        search = spotify.Search(self.session, sp_search=sp_search)

        result = search.tracks

        lib_mock.sp_search_is_loaded.assert_called_with(sp_search)
        self.assertEqual(len(result), 0)

    def test_tracks_fails_if_error(self, lib_mock):
        self.assert_fails_if_error(lib_mock, lambda s: s.tracks)

    @mock.patch('spotify.album.lib', spec=spotify.lib)
    def test_albums(self, album_lib_mock, lib_mock):
        lib_mock.sp_search_error.return_value = spotify.ErrorType.OK
        sp_album = spotify.ffi.cast('sp_album *', 43)
        lib_mock.sp_search_num_albums.return_value = 1
        lib_mock.sp_search_album.return_value = sp_album
        sp_search = spotify.ffi.cast('sp_search *', 42)
        search = spotify.Search(self.session, sp_search=sp_search)

        self.assertEqual(lib_mock.sp_search_add_ref.call_count, 1)
        result = search.albums
        self.assertEqual(lib_mock.sp_search_add_ref.call_count, 2)

        self.assertEqual(len(result), 1)
        lib_mock.sp_search_num_albums.assert_called_with(sp_search)

        item = result[0]
        self.assertIsInstance(item, spotify.Album)
        self.assertEqual(item._sp_album, sp_album)
        self.assertEqual(lib_mock.sp_search_album.call_count, 1)
        lib_mock.sp_search_album.assert_called_with(sp_search, 0)
        album_lib_mock.sp_album_add_ref.assert_called_with(sp_album)

    def test_albums_if_no_albums(self, lib_mock):
        lib_mock.sp_search_error.return_value = spotify.ErrorType.OK
        lib_mock.sp_search_num_albums.return_value = 0
        sp_search = spotify.ffi.cast('sp_search *', 42)
        search = spotify.Search(self.session, sp_search=sp_search)

        result = search.albums

        self.assertEqual(len(result), 0)
        lib_mock.sp_search_num_albums.assert_called_with(sp_search)
        self.assertEqual(lib_mock.sp_search_album.call_count, 0)

    def test_albums_if_unloaded(self, lib_mock):
        lib_mock.sp_search_error.return_value = spotify.ErrorType.IS_LOADING
        lib_mock.sp_search_is_loaded.return_value = 0
        sp_search = spotify.ffi.cast('sp_search *', 42)
        search = spotify.Search(self.session, sp_search=sp_search)

        result = search.albums

        lib_mock.sp_search_is_loaded.assert_called_with(sp_search)
        self.assertEqual(len(result), 0)

    def test_albums_fails_if_error(self, lib_mock):
        self.assert_fails_if_error(lib_mock, lambda s: s.albums)

    @mock.patch('spotify.artist.lib', spec=spotify.lib)
    def test_artists(self, artist_lib_mock, lib_mock):
        lib_mock.sp_search_error.return_value = spotify.ErrorType.OK
        sp_artist = spotify.ffi.cast('sp_artist *', 43)
        lib_mock.sp_search_num_artists.return_value = 1
        lib_mock.sp_search_artist.return_value = sp_artist
        sp_search = spotify.ffi.cast('sp_search *', 42)
        search = spotify.Search(self.session, sp_search=sp_search)

        self.assertEqual(lib_mock.sp_search_add_ref.call_count, 1)
        result = search.artists
        self.assertEqual(lib_mock.sp_search_add_ref.call_count, 2)

        self.assertEqual(len(result), 1)
        lib_mock.sp_search_num_artists.assert_called_with(sp_search)

        item = result[0]
        self.assertIsInstance(item, spotify.Artist)
        self.assertEqual(item._sp_artist, sp_artist)
        self.assertEqual(lib_mock.sp_search_artist.call_count, 1)
        lib_mock.sp_search_artist.assert_called_with(sp_search, 0)
        artist_lib_mock.sp_artist_add_ref.assert_called_with(sp_artist)

    def test_artists_if_no_artists(self, lib_mock):
        lib_mock.sp_search_error.return_value = spotify.ErrorType.OK
        lib_mock.sp_search_num_artists.return_value = 0
        sp_search = spotify.ffi.cast('sp_search *', 42)
        search = spotify.Search(self.session, sp_search=sp_search)

        result = search.artists

        self.assertEqual(len(result), 0)
        lib_mock.sp_search_num_artists.assert_called_with(sp_search)
        self.assertEqual(lib_mock.sp_search_artist.call_count, 0)

    def test_artists_if_unloaded(self, lib_mock):
        lib_mock.sp_search_error.return_value = spotify.ErrorType.IS_LOADING
        lib_mock.sp_search_is_loaded.return_value = 0
        sp_search = spotify.ffi.cast('sp_search *', 42)
        search = spotify.Search(self.session, sp_search=sp_search)

        result = search.artists

        lib_mock.sp_search_is_loaded.assert_called_with(sp_search)
        self.assertEqual(len(result), 0)

    def test_artists_fails_if_error(self, lib_mock):
        self.assert_fails_if_error(lib_mock, lambda s: s.artists)

    @mock.patch('spotify.playlist.lib', spec=spotify.lib)
    def test_playlists(self, playlist_lib_mock, lib_mock):
        lib_mock.sp_search_error.return_value = spotify.ErrorType.OK
        lib_mock.sp_search_num_playlists.return_value = 1
        lib_mock.sp_search_playlist_name.return_value = spotify.ffi.new(
            'char[]', b'The Party List')
        lib_mock.sp_search_playlist_uri.return_value = spotify.ffi.new(
            'char[]', b'spotify:playlist:foo')
        lib_mock.sp_search_playlist_image_uri.return_value = spotify.ffi.new(
            'char[]', b'spotify:image:foo')
        sp_search = spotify.ffi.cast('sp_search *', 42)
        search = spotify.Search(self.session, sp_search=sp_search)

        self.assertEqual(lib_mock.sp_search_add_ref.call_count, 1)
        result = search.playlists
        self.assertEqual(lib_mock.sp_search_add_ref.call_count, 2)

        self.assertEqual(len(result), 1)
        lib_mock.sp_search_num_playlists.assert_called_with(sp_search)

        item = result[0]
        self.assertIsInstance(item, spotify.SearchPlaylist)
        self.assertEqual(item.name, 'The Party List')
        self.assertEqual(item.uri, 'spotify:playlist:foo')
        self.assertEqual(item.image_uri, 'spotify:image:foo')
        self.assertEqual(lib_mock.sp_search_playlist_name.call_count, 1)
        lib_mock.sp_search_playlist_name.assert_called_with(sp_search, 0)
        self.assertEqual(lib_mock.sp_search_playlist_uri.call_count, 1)
        lib_mock.sp_search_playlist_uri.assert_called_with(sp_search, 0)
        self.assertEqual(lib_mock.sp_search_playlist_image_uri.call_count, 1)
        lib_mock.sp_search_playlist_image_uri.assert_called_with(sp_search, 0)

    def test_playlists_if_no_playlists(self, lib_mock):
        lib_mock.sp_search_error.return_value = spotify.ErrorType.OK
        lib_mock.sp_search_num_playlists.return_value = 0
        sp_search = spotify.ffi.cast('sp_search *', 42)
        search = spotify.Search(self.session, sp_search=sp_search)

        result = search.playlists

        self.assertEqual(len(result), 0)
        lib_mock.sp_search_num_playlists.assert_called_with(sp_search)
        self.assertEqual(lib_mock.sp_search_playlist.call_count, 0)

    def test_playlists_if_unloaded(self, lib_mock):
        lib_mock.sp_search_error.return_value = spotify.ErrorType.IS_LOADING
        lib_mock.sp_search_is_loaded.return_value = 0
        sp_search = spotify.ffi.cast('sp_search *', 42)
        search = spotify.Search(self.session, sp_search=sp_search)

        result = search.playlists

        lib_mock.sp_search_is_loaded.assert_called_with(sp_search)
        self.assertEqual(len(result), 0)

    def test_playlists_fails_if_error(self, lib_mock):
        self.assert_fails_if_error(lib_mock, lambda s: s.playlists)

    def test_query(self, lib_mock):
        lib_mock.sp_search_error.return_value = spotify.ErrorType.OK
        lib_mock.sp_search_query.return_value = spotify.ffi.new(
            'char[]', b'Foo Bar Baz')
        sp_search = spotify.ffi.cast('sp_search *', 42)
        search = spotify.Search(self.session, sp_search=sp_search)

        result = search.query

        lib_mock.sp_search_query.assert_called_once_with(sp_search)
        self.assertEqual(result, 'Foo Bar Baz')

    def test_query_is_none_if_empty(self, lib_mock):
        lib_mock.sp_search_error.return_value = spotify.ErrorType.OK
        lib_mock.sp_search_query.return_value = spotify.ffi.new('char[]', b'')
        sp_search = spotify.ffi.cast('sp_search *', 42)
        search = spotify.Search(self.session, sp_search=sp_search)

        result = search.query

        lib_mock.sp_search_query.assert_called_once_with(sp_search)
        self.assertIsNone(result)

    def test_query_fails_if_error(self, lib_mock):
        self.assert_fails_if_error(lib_mock, lambda s: s.query)

    def test_did_you_mean(self, lib_mock):
        lib_mock.sp_search_error.return_value = spotify.ErrorType.OK
        lib_mock.sp_search_did_you_mean.return_value = spotify.ffi.new(
            'char[]', b'Foo Bar Baz')
        sp_search = spotify.ffi.cast('sp_search *', 42)
        search = spotify.Search(self.session, sp_search=sp_search)

        result = search.did_you_mean

        lib_mock.sp_search_did_you_mean.assert_called_once_with(sp_search)
        self.assertEqual(result, 'Foo Bar Baz')

    def test_did_you_mean_is_none_if_empty(self, lib_mock):
        lib_mock.sp_search_error.return_value = spotify.ErrorType.OK
        lib_mock.sp_search_did_you_mean.return_value = spotify.ffi.new(
            'char[]', b'')
        sp_search = spotify.ffi.cast('sp_search *', 42)
        search = spotify.Search(self.session, sp_search=sp_search)

        result = search.did_you_mean

        lib_mock.sp_search_did_you_mean.assert_called_once_with(sp_search)
        self.assertIsNone(result)

    def test_did_you_mean_fails_if_error(self, lib_mock):
        self.assert_fails_if_error(lib_mock, lambda s: s.did_you_mean)

    def test_track_total(self, lib_mock):
        lib_mock.sp_search_error.return_value = spotify.ErrorType.OK
        lib_mock.sp_search_total_tracks.return_value = 75
        sp_search = spotify.ffi.cast('sp_search *', 42)
        search = spotify.Search(self.session, sp_search=sp_search)

        result = search.track_total

        lib_mock.sp_search_total_tracks.assert_called_with(sp_search)
        self.assertEqual(result, 75)

    def test_track_total_fails_if_error(self, lib_mock):
        self.assert_fails_if_error(lib_mock, lambda s: s.track_total)

    def test_album_total(self, lib_mock):
        lib_mock.sp_search_error.return_value = spotify.ErrorType.OK
        lib_mock.sp_search_total_albums.return_value = 75
        sp_search = spotify.ffi.cast('sp_search *', 42)
        search = spotify.Search(self.session, sp_search=sp_search)

        result = search.album_total

        lib_mock.sp_search_total_albums.assert_called_with(sp_search)
        self.assertEqual(result, 75)

    def test_album_total_fails_if_error(self, lib_mock):
        self.assert_fails_if_error(lib_mock, lambda s: s.album_total)

    def test_artist_total(self, lib_mock):
        lib_mock.sp_search_error.return_value = spotify.ErrorType.OK
        lib_mock.sp_search_total_artists.return_value = 75
        sp_search = spotify.ffi.cast('sp_search *', 42)
        search = spotify.Search(self.session, sp_search=sp_search)

        result = search.artist_total

        lib_mock.sp_search_total_artists.assert_called_with(sp_search)
        self.assertEqual(result, 75)

    def test_artist_total_fails_if_error(self, lib_mock):
        self.assert_fails_if_error(lib_mock, lambda s: s.artist_total)

    def test_playlist_total(self, lib_mock):
        lib_mock.sp_search_error.return_value = spotify.ErrorType.OK
        lib_mock.sp_search_total_playlists.return_value = 75
        sp_search = spotify.ffi.cast('sp_search *', 42)
        search = spotify.Search(self.session, sp_search=sp_search)

        result = search.playlist_total

        lib_mock.sp_search_total_playlists.assert_called_with(sp_search)
        self.assertEqual(result, 75)

    def test_playlist_total_fails_if_error(self, lib_mock):
        self.assert_fails_if_error(lib_mock, lambda s: s.playlist_total)

    def test_search_type_defaults_to_standard(self, lib_mock):
        sp_search = spotify.ffi.cast('sp_search *', 42)
        search = spotify.Search(self.session, sp_search=sp_search)

        result = search.search_type

        self.assertEqual(result, spotify.SearchType.STANDARD)

    def test_more(self, lib_mock):
        sp_search1 = spotify.ffi.cast('sp_search *', 42)
        sp_search2 = spotify.ffi.cast('sp_search *', 43)
        lib_mock.sp_search_create.side_effect = [sp_search1, sp_search2]
        lib_mock.sp_search_error.return_value = spotify.ErrorType.OK
        lib_mock.sp_search_query.return_value = spotify.ffi.new(
            'char[]', b'alice')

        result = spotify.Search(self.session, query='alice')

        lib_mock.sp_search_create.assert_called_with(
            self.session._sp_session, mock.ANY,
            0, 20, 0, 20, 0, 20, 0, 20,
            int(spotify.SearchType.STANDARD), mock.ANY, mock.ANY)
        self.assertEqual(
            spotify.ffi.string(lib_mock.sp_search_create.call_args[0][1]),
            b'alice')
        self.assertEqual(lib_mock.sp_search_add_ref.call_count, 0)
        self.assertIsInstance(result, spotify.Search)
        self.assertEqual(result._sp_search, sp_search1)

        result = result.more(
            track_count=30, album_count=30, artist_count=30, playlist_count=30)

        lib_mock.sp_search_create.assert_called_with(
            self.session._sp_session, mock.ANY,
            20, 30, 20, 30, 20, 30, 20, 30,
            int(spotify.SearchType.STANDARD), mock.ANY, mock.ANY)
        self.assertEqual(
            spotify.ffi.string(lib_mock.sp_search_create.call_args[0][1]),
            b'alice')
        self.assertEqual(lib_mock.sp_search_add_ref.call_count, 0)
        self.assertIsInstance(result, spotify.Search)
        self.assertEqual(result._sp_search, sp_search2)

    @mock.patch('spotify.Link', spec=spotify.Link)
    def test_link_creates_link_to_search(self, link_mock, lib_mock):
        sp_search = spotify.ffi.cast('sp_search *', 42)
        search = spotify.Search(self.session, sp_search=sp_search)
        sp_link = spotify.ffi.cast('sp_link *', 43)
        lib_mock.sp_link_create_from_search.return_value = sp_link
        link_mock.return_value = mock.sentinel.link

        result = search.link

        link_mock.assert_called_once_with(
            self.session, sp_link=sp_link, add_ref=False)
        self.assertEqual(result, mock.sentinel.link)


class SearchPlaylistTest(unittest.TestCase):

    def setUp(self):
        self.session = tests.create_session_mock()

    def test_attributes(self):
        pl = spotify.SearchPlaylist(
            self.session, name='foo', uri='uri:foo', image_uri='image:foo')

        self.assertEqual(pl.name, 'foo')
        self.assertEqual(pl.uri, 'uri:foo')
        self.assertEqual(pl.image_uri, 'image:foo')

    def test_repr(self):
        pl = spotify.SearchPlaylist(
            self.session, name='foo', uri='uri:foo', image_uri='image:foo')

        result = repr(pl)

        self.assertEqual(
            result, 'SearchPlaylist(name=%r, uri=%r)' % ('foo', 'uri:foo'))

    def test_playlist(self):
        self.session.get_playlist.return_value = mock.sentinel.playlist
        pl = spotify.SearchPlaylist(
            self.session, name='foo', uri='uri:foo', image_uri='image:foo')

        result = pl.playlist

        self.assertEqual(result, mock.sentinel.playlist)
        self.session.get_playlist.assert_called_with(pl.uri)

    def test_image(self):
        self.session.get_image.return_value = mock.sentinel.image
        pl = spotify.SearchPlaylist(
            self.session, name='foo', uri='uri:foo', image_uri='image:foo')

        result = pl.image

        self.assertEqual(result, mock.sentinel.image)
        self.session.get_image.assert_called_with(pl.image_uri)


class SearchTypeTest(unittest.TestCase):

    def test_has_constants(self):
        self.assertEqual(spotify.SearchType.STANDARD, 0)
        self.assertEqual(spotify.SearchType.SUGGEST, 1)

########NEW FILE########
__FILENAME__ = test_session
# encoding: utf-8

from __future__ import unicode_literals

import unittest

import spotify
from spotify.session import _SessionCallbacks

import tests
from tests import mock


@mock.patch('spotify.session.lib', spec=spotify.lib)
class SessionTest(unittest.TestCase):

    def tearDown(self):
        spotify._session_instance = None

    def test_raises_error_if_a_session_already_exists(self, lib_mock):
        tests.create_real_session(lib_mock)

        with self.assertRaises(RuntimeError):
            tests.create_real_session(lib_mock)

    @mock.patch('spotify.Config')
    def test_creates_config_if_none_provided(self, config_cls_mock, lib_mock):
        lib_mock.sp_session_create.return_value = spotify.ErrorType.OK

        session = spotify.Session()

        config_cls_mock.assert_called_once_with()
        self.assertEqual(session.config, config_cls_mock.return_value)

    @mock.patch('spotify.Config')
    def test_tries_to_load_application_key_if_none_provided(
            self, config_cls_mock, lib_mock):
        lib_mock.sp_session_create.return_value = spotify.ErrorType.OK
        config_mock = config_cls_mock.return_value
        config_mock.application_key = None

        spotify.Session()

        config_mock.load_application_key_file.assert_called_once_with()

    def test_raises_error_if_not_ok(self, lib_mock):
        lib_mock.sp_session_create.return_value = (
            spotify.ErrorType.BAD_API_VERSION)
        config = spotify.Config()
        config.application_key = b'\x01' * 321

        with self.assertRaises(spotify.Error):
            spotify.Session(config=config)

    def test_releases_sp_session_when_session_dies(self, lib_mock):
        sp_session = spotify.ffi.NULL

        def func(sp_session_config, sp_session_ptr):
            sp_session_ptr[0] = sp_session
            return spotify.ErrorType.OK

        lib_mock.sp_session_create.side_effect = func
        config = spotify.Config()
        config.application_key = b'\x01' * 321

        session = spotify.Session(config=config)
        session = None  # noqa
        spotify._session_instance = None
        tests.gc_collect()

        lib_mock.sp_session_release.assert_called_with(sp_session)

    def test_login_raises_error_if_no_password_and_no_blob(self, lib_mock):
        lib_mock.sp_session_login.return_value = spotify.ErrorType.OK
        session = tests.create_real_session(lib_mock)

        with self.assertRaises(AttributeError):
            session.login('alice')

    def test_login_with_password(self, lib_mock):
        lib_mock.sp_session_login.return_value = spotify.ErrorType.OK
        session = tests.create_real_session(lib_mock)

        session.login('alice', 'secret')

        lib_mock.sp_session_login.assert_called_once_with(
            session._sp_session, mock.ANY, mock.ANY,
            False, spotify.ffi.NULL)
        self.assertEqual(
            spotify.ffi.string(lib_mock.sp_session_login.call_args[0][1]),
            b'alice')
        self.assertEqual(
            spotify.ffi.string(lib_mock.sp_session_login.call_args[0][2]),
            b'secret')

    def test_login_with_blob(self, lib_mock):
        lib_mock.sp_session_login.return_value = spotify.ErrorType.OK
        session = tests.create_real_session(lib_mock)

        session.login('alice', blob='secret blob')

        lib_mock.sp_session_login.assert_called_once_with(
            session._sp_session, mock.ANY, spotify.ffi.NULL,
            False, mock.ANY)
        self.assertEqual(
            spotify.ffi.string(lib_mock.sp_session_login.call_args[0][1]),
            b'alice')
        self.assertEqual(
            spotify.ffi.string(lib_mock.sp_session_login.call_args[0][4]),
            b'secret blob')

    def test_login_with_remember_me_flag(self, lib_mock):
        lib_mock.sp_session_login.return_value = spotify.ErrorType.OK
        session = tests.create_real_session(lib_mock)

        session.login('alice', 'secret', remember_me='anything truish')

        lib_mock.sp_session_login.assert_called_once_with(
            session._sp_session, mock.ANY, mock.ANY,
            True, spotify.ffi.NULL)

    def test_login_fail_raises_error(self, lib_mock):
        lib_mock.sp_session_login.return_value = spotify.ErrorType.NO_SUCH_USER
        session = tests.create_real_session(lib_mock)

        with self.assertRaises(spotify.Error):
            session.login('alice', 'secret')

    def test_logout(self, lib_mock):
        lib_mock.sp_session_logout.return_value = spotify.ErrorType.OK
        session = tests.create_real_session(lib_mock)

        session.logout()

        lib_mock.sp_session_logout.assert_called_once_with(session._sp_session)

    def test_logout_fail_raises_error(self, lib_mock):
        lib_mock.sp_session_login.return_value = (
            spotify.ErrorType.BAD_API_VERSION)
        session = tests.create_real_session(lib_mock)

        with self.assertRaises(spotify.Error):
            session.logout()

    def test_remembered_user_name_grows_buffer_to_fit_username(self, lib_mock):
        username = 'alice' * 100

        lib_mock.sp_session_remembered_user.side_effect = (
            tests.buffer_writer(username))
        session = tests.create_real_session(lib_mock)

        result = session.remembered_user_name

        lib_mock.sp_session_remembered_user.assert_called_with(
            session._sp_session, mock.ANY, mock.ANY)
        self.assertEqual(result, username)

    def test_remembered_user_name_is_none_if_not_remembered(self, lib_mock):
        lib_mock.sp_session_remembered_user.return_value = -1
        session = tests.create_real_session(lib_mock)

        result = session.remembered_user_name

        lib_mock.sp_session_remembered_user.assert_called_with(
            session._sp_session, mock.ANY, mock.ANY)
        self.assertIsNone(result)

    def test_relogin(self, lib_mock):
        lib_mock.sp_session_relogin.return_value = spotify.ErrorType.OK
        session = tests.create_real_session(lib_mock)

        session.relogin()

        lib_mock.sp_session_relogin.assert_called_once_with(
            session._sp_session)

    def test_relogin_fail_raises_error(self, lib_mock):
        lib_mock.sp_session_relogin.return_value = (
            spotify.ErrorType.NO_CREDENTIALS)
        session = tests.create_real_session(lib_mock)

        with self.assertRaises(spotify.Error):
            session.relogin()

    def test_forget_me(self, lib_mock):
        lib_mock.sp_session_forget_me.return_value = spotify.ErrorType.OK
        session = tests.create_real_session(lib_mock)

        session.forget_me()

        lib_mock.sp_session_forget_me.assert_called_with(session._sp_session)

    def test_forget_me_fail_raises_error(self, lib_mock):
        lib_mock.sp_session_forget_me.return_value = (
            spotify.ErrorType.BAD_API_VERSION)
        session = tests.create_real_session(lib_mock)

        with self.assertRaises(spotify.Error):
            session.forget_me()

    @mock.patch('spotify.user.lib', spec=spotify.lib)
    def test_user(self, user_lib_mock, lib_mock):
        lib_mock.sp_session_user.return_value = (
            spotify.ffi.cast('sp_user *', 42))
        session = tests.create_real_session(lib_mock)

        result = session.user

        lib_mock.sp_session_user.assert_called_with(session._sp_session)
        self.assertIsInstance(result, spotify.User)

    def test_user_if_not_logged_in(self, lib_mock):
        lib_mock.sp_session_user.return_value = spotify.ffi.NULL
        session = tests.create_real_session(lib_mock)

        result = session.user

        lib_mock.sp_session_user.assert_called_with(session._sp_session)
        self.assertIsNone(result)

    def test_user_name(self, lib_mock):
        lib_mock.sp_session_user_name.return_value = spotify.ffi.new(
            'char[]', b'alice')
        session = tests.create_real_session(lib_mock)

        result = session.user_name

        lib_mock.sp_session_user_name.assert_called_with(session._sp_session)
        self.assertEqual(result, 'alice')

    def test_user_country(self, lib_mock):
        lib_mock.sp_session_user_country.return_value = (
            ord('S') << 8 | ord('E'))
        session = tests.create_real_session(lib_mock)

        result = session.user_country

        lib_mock.sp_session_user_country.assert_called_with(
            session._sp_session)
        self.assertEqual(result, 'SE')

    @mock.patch('spotify.playlist_container.lib', spec=spotify.lib)
    def test_playlist_container(self, playlist_lib_mock, lib_mock):
        lib_mock.sp_session_playlistcontainer.return_value = (
            spotify.ffi.cast('sp_playlistcontainer *', 42))
        session = tests.create_real_session(lib_mock)

        result = session.playlist_container

        lib_mock.sp_session_playlistcontainer.assert_called_with(
            session._sp_session)
        self.assertIsInstance(result, spotify.PlaylistContainer)

    @mock.patch('spotify.playlist_container.lib', spec=spotify.lib)
    def test_playlist_container_if_already_listened_to(
            self, playlist_lib_mock, lib_mock):
        lib_mock.sp_session_playlistcontainer.return_value = (
            spotify.ffi.cast('sp_playlistcontainer *', 42))
        session = tests.create_real_session(lib_mock)

        result1 = session.playlist_container
        result1.on(
            spotify.PlaylistContainerEvent.PLAYLIST_ADDED, lambda *args: None)
        result2 = session.playlist_container

        result1.off()

        self.assertIsInstance(result1, spotify.PlaylistContainer)
        self.assertIs(result1, result2)

    def test_playlist_container_if_not_logged_in(self, lib_mock):
        lib_mock.sp_session_playlistcontainer.return_value = spotify.ffi.NULL
        session = tests.create_real_session(lib_mock)

        result = session.playlist_container

        lib_mock.sp_session_playlistcontainer.assert_called_with(
            session._sp_session)
        self.assertIsNone(result)

    @mock.patch('spotify.playlist.lib', spec=spotify.lib)
    def test_inbox(self, playlist_lib_mock, lib_mock):
        lib_mock.sp_session_inbox_create.return_value = (
            spotify.ffi.cast('sp_playlist *', 42))
        session = tests.create_real_session(lib_mock)

        result = session.inbox

        lib_mock.sp_session_inbox_create.assert_called_with(
            session._sp_session)
        self.assertIsInstance(result, spotify.Playlist)

        # Since we *created* the sp_playlist, we already have a refcount of 1
        # and shouldn't increase the refcount when wrapping this sp_playlist in
        # a Playlist object
        self.assertEqual(playlist_lib_mock.sp_playlist_add_ref.call_count, 0)

    def test_inbox_if_not_logged_in(self, lib_mock):
        lib_mock.sp_session_inbox_create.return_value = spotify.ffi.NULL
        session = tests.create_real_session(lib_mock)

        result = session.inbox

        lib_mock.sp_session_inbox_create.assert_called_with(
            session._sp_session)
        self.assertIsNone(result)

    def test_set_cache_size(self, lib_mock):
        lib_mock.sp_session_set_cache_size.return_value = spotify.ErrorType.OK
        session = tests.create_real_session(lib_mock)

        session.set_cache_size(100)

        lib_mock.sp_session_set_cache_size.assert_called_once_with(
            session._sp_session, 100)

    def test_set_cache_size_fail_raises_error(self, lib_mock):
        lib_mock.sp_session_set_cache_size.return_value = (
            spotify.ErrorType.BAD_API_VERSION)
        session = tests.create_real_session(lib_mock)

        with self.assertRaises(spotify.Error):
            session.set_cache_size(100)

    def test_flush_caches(self, lib_mock):
        lib_mock.sp_session_flush_caches.return_value = spotify.ErrorType.OK
        session = tests.create_real_session(lib_mock)

        session.flush_caches()

        lib_mock.sp_session_flush_caches.assert_called_once_with(
            session._sp_session)

    def test_flush_caches_fail_raises_error(self, lib_mock):
        lib_mock.sp_session_flush_caches.return_value = (
            spotify.ErrorType.BAD_API_VERSION)
        session = tests.create_real_session(lib_mock)

        with self.assertRaises(spotify.Error):
            session.flush_caches()

    def test_preferred_bitrate(self, lib_mock):
        lib_mock.sp_session_preferred_bitrate.return_value = (
            spotify.ErrorType.OK)
        session = tests.create_real_session(lib_mock)

        session.preferred_bitrate(spotify.Bitrate.BITRATE_320k)

        lib_mock.sp_session_preferred_bitrate.assert_called_with(
            session._sp_session, spotify.Bitrate.BITRATE_320k)

    def test_preferred_bitrate_fail_raises_error(self, lib_mock):
        lib_mock.sp_session_preferred_bitrate.return_value = (
            spotify.ErrorType.INVALID_ARGUMENT)
        session = tests.create_real_session(lib_mock)

        with self.assertRaises(spotify.Error):
            session.preferred_bitrate(17)

    def test_preferred_offline_bitrate(self, lib_mock):
        lib_mock.sp_session_preferred_offline_bitrate.return_value = (
            spotify.ErrorType.OK)
        session = tests.create_real_session(lib_mock)

        session.preferred_offline_bitrate(spotify.Bitrate.BITRATE_320k)

        lib_mock.sp_session_preferred_offline_bitrate.assert_called_with(
            session._sp_session, spotify.Bitrate.BITRATE_320k, 0)

    def test_preferred_offline_bitrate_with_allow_resync(self, lib_mock):
        lib_mock.sp_session_preferred_offline_bitrate.return_value = (
            spotify.ErrorType.OK)
        session = tests.create_real_session(lib_mock)

        session.preferred_offline_bitrate(
            spotify.Bitrate.BITRATE_320k, allow_resync=True)

        lib_mock.sp_session_preferred_offline_bitrate.assert_called_with(
            session._sp_session, spotify.Bitrate.BITRATE_320k, 1)

    def test_preferred_offline_bitrate_fail_raises_error(self, lib_mock):
        lib_mock.sp_session_preferred_offline_bitrate.return_value = (
            spotify.ErrorType.INVALID_ARGUMENT)
        session = tests.create_real_session(lib_mock)

        with self.assertRaises(spotify.Error):
            session.preferred_offline_bitrate(17)

    def test_get_volume_normalization(self, lib_mock):
        lib_mock.sp_session_get_volume_normalization.return_value = 0
        session = tests.create_real_session(lib_mock)

        result = session.volume_normalization

        lib_mock.sp_session_get_volume_normalization.assert_called_with(
            session._sp_session)
        self.assertFalse(result)

    def test_set_volume_normalization(self, lib_mock):
        lib_mock.sp_session_set_volume_normalization.return_value = (
            spotify.ErrorType.OK)
        session = tests.create_real_session(lib_mock)

        session.volume_normalization = True

        lib_mock.sp_session_set_volume_normalization.assert_called_with(
            session._sp_session, 1)

    def test_set_volume_normalization_fail_raises_error(self, lib_mock):
        lib_mock.sp_session_set_volume_normalization.return_value = (
            spotify.ErrorType.BAD_API_VERSION)
        session = tests.create_real_session(lib_mock)

        with self.assertRaises(spotify.Error):
            session.volume_normalization = True

    def test_process_events_returns_ms_to_next_timeout(self, lib_mock):
        def func(sp_session, int_ptr):
            int_ptr[0] = 5500
            return spotify.ErrorType.OK

        lib_mock.sp_session_process_events.side_effect = func

        session = tests.create_real_session(lib_mock)

        timeout = session.process_events()

        self.assertEqual(timeout, 5500)

    def test_process_events_fail_raises_error(self, lib_mock):
        lib_mock.sp_session_process_events.return_value = (
            spotify.ErrorType.BAD_API_VERSION)
        session = tests.create_real_session(lib_mock)

        with self.assertRaises(spotify.Error):
            session.process_events()

    @mock.patch('spotify.InboxPostResult', spec=spotify.InboxPostResult)
    def test_inbox_post_tracks(self, inbox_mock, lib_mock):
        session = tests.create_real_session(lib_mock)
        inbox_instance_mock = inbox_mock.return_value

        result = session.inbox_post_tracks(
            mock.sentinel.username, mock.sentinel.tracks,
            mock.sentinel.message, mock.sentinel.callback)

        inbox_mock.assert_called_with(
            session, mock.sentinel.username, mock.sentinel.tracks,
            mock.sentinel.message, mock.sentinel.callback)
        self.assertEqual(result, inbox_instance_mock)

    @mock.patch('spotify.playlist.lib', spec=spotify.lib)
    def test_get_starred(self, playlist_lib_mock, lib_mock):
        lib_mock.sp_session_starred_for_user_create.return_value = (
            spotify.ffi.cast('sp_playlist *', 42))
        session = tests.create_real_session(lib_mock)

        result = session.get_starred('alice')

        lib_mock.sp_session_starred_for_user_create.assert_called_with(
            session._sp_session, b'alice')
        self.assertIsInstance(result, spotify.Playlist)

        # Since we *created* the sp_playlist, we already have a refcount of 1
        # and shouldn't increase the refcount when wrapping this sp_playlist in
        # a Playlist object
        self.assertEqual(playlist_lib_mock.sp_playlist_add_ref.call_count, 0)

    @mock.patch('spotify.playlist.lib', spec=spotify.lib)
    def test_get_starred_for_current_user(self, playlist_lib_mock, lib_mock):
        lib_mock.sp_session_starred_create.return_value = (
            spotify.ffi.cast('sp_playlist *', 42))
        session = tests.create_real_session(lib_mock)

        result = session.get_starred()

        lib_mock.sp_session_starred_create.assert_called_with(
            session._sp_session)
        self.assertIsInstance(result, spotify.Playlist)

        # Since we *created* the sp_playlist, we already have a refcount of 1
        # and shouldn't increase the refcount when wrapping this sp_playlist in
        # a Playlist object
        self.assertEqual(playlist_lib_mock.sp_playlist_add_ref.call_count, 0)

    def test_get_starred_if_not_logged_in(self, lib_mock):
        lib_mock.sp_session_starred_for_user_create.return_value = (
            spotify.ffi.NULL)
        session = tests.create_real_session(lib_mock)

        result = session.get_starred('alice')

        lib_mock.sp_session_starred_for_user_create.assert_called_with(
            session._sp_session, b'alice')
        self.assertIsNone(result)

    @mock.patch('spotify.playlist_container.lib', spec=spotify.lib)
    def test_get_published_playlists(self, playlist_lib_mock, lib_mock):
        func_mock = lib_mock.sp_session_publishedcontainer_for_user_create
        func_mock.return_value = spotify.ffi.cast('sp_playlistcontainer *', 42)
        session = tests.create_real_session(lib_mock)

        result = session.get_published_playlists('alice')

        func_mock.assert_called_with(session._sp_session, b'alice')
        self.assertIsInstance(result, spotify.PlaylistContainer)

        # Since we *created* the sp_playlistcontainer, we already have a
        # refcount of 1 and shouldn't increase the refcount when wrapping this
        # sp_playlistcontainer in a PlaylistContainer object
        self.assertEqual(
            playlist_lib_mock.sp_playlistcontainer_add_ref.call_count, 0)

    @mock.patch('spotify.playlist_container.lib', spec=spotify.lib)
    def test_get_published_playlists_for_current_user(
            self, playlist_lib_mock, lib_mock):
        func_mock = lib_mock.sp_session_publishedcontainer_for_user_create
        func_mock.return_value = spotify.ffi.cast('sp_playlistcontainer *', 42)
        session = tests.create_real_session(lib_mock)

        result = session.get_published_playlists()

        func_mock.assert_called_with(session._sp_session, spotify.ffi.NULL)
        self.assertIsInstance(result, spotify.PlaylistContainer)

    def test_get_published_playlists_if_not_logged_in(self, lib_mock):
        func_mock = lib_mock.sp_session_publishedcontainer_for_user_create
        func_mock.return_value = spotify.ffi.NULL
        session = tests.create_real_session(lib_mock)

        result = session.get_published_playlists('alice')

        func_mock.assert_called_with(session._sp_session, b'alice')
        self.assertIsNone(result)

    @mock.patch('spotify.Link')
    def test_get_link(self, link_mock, lib_mock):
        session = tests.create_real_session(lib_mock)
        link_mock.return_value = mock.sentinel.link

        result = session.get_link('spotify:any:foo')

        self.assertIs(result, mock.sentinel.link)
        link_mock.assert_called_with(session, uri='spotify:any:foo')

    @mock.patch('spotify.Track')
    def test_get_track(self, track_mock, lib_mock):
        session = tests.create_real_session(lib_mock)
        track_mock.return_value = mock.sentinel.track

        result = session.get_track('spotify:track:foo')

        self.assertIs(result, mock.sentinel.track)
        track_mock.assert_called_with(session, uri='spotify:track:foo')

    @mock.patch('spotify.Track')
    def test_get_local_track(self, track_mock, lib_mock):
        session = tests.create_real_session(lib_mock)
        sp_track = spotify.ffi.cast('sp_track *', 42)
        lib_mock.sp_localtrack_create.return_value = sp_track
        track_mock.return_value = mock.sentinel.track

        track = session.get_local_track(
            artist='foo', title='bar', album='baz', length=210000)

        self.assertEqual(track, mock.sentinel.track)
        lib_mock.sp_localtrack_create.assert_called_once_with(
            mock.ANY, mock.ANY, mock.ANY, 210000)
        self.assertEqual(
            spotify.ffi.string(lib_mock.sp_localtrack_create.call_args[0][0]),
            b'foo')
        self.assertEqual(
            spotify.ffi.string(lib_mock.sp_localtrack_create.call_args[0][1]),
            b'bar')
        self.assertEqual(
            spotify.ffi.string(lib_mock.sp_localtrack_create.call_args[0][2]),
            b'baz')
        self.assertEqual(
            lib_mock.sp_localtrack_create.call_args[0][3], 210000)

        # Since we *created* the sp_track, we already have a refcount of 1 and
        # shouldn't increase the refcount when wrapping this sp_track in a
        # Track object
        track_mock.assert_called_with(
            session, sp_track=sp_track, add_ref=False)

    @mock.patch('spotify.Track')
    def test_get_local_track_with_defaults(self, track_mock, lib_mock):
        session = tests.create_real_session(lib_mock)
        sp_track = spotify.ffi.cast('sp_track *', 42)
        lib_mock.sp_localtrack_create.return_value = sp_track
        track_mock.return_value = mock.sentinel.track

        track = session.get_local_track()

        self.assertEqual(track, mock.sentinel.track)
        lib_mock.sp_localtrack_create.assert_called_once_with(
            mock.ANY, mock.ANY, mock.ANY, -1)
        self.assertEqual(
            spotify.ffi.string(lib_mock.sp_localtrack_create.call_args[0][0]),
            b'')
        self.assertEqual(
            spotify.ffi.string(lib_mock.sp_localtrack_create.call_args[0][1]),
            b'')
        self.assertEqual(
            spotify.ffi.string(lib_mock.sp_localtrack_create.call_args[0][2]),
            b'')
        self.assertEqual(
            lib_mock.sp_localtrack_create.call_args[0][3], -1)

        # Since we *created* the sp_track, we already have a refcount of 1 and
        # shouldn't increase the refcount when wrapping this sp_track in a
        # Track object
        track_mock.assert_called_with(
            session, sp_track=sp_track, add_ref=False)

    @mock.patch('spotify.Album')
    def test_get_album(self, album_mock, lib_mock):
        session = tests.create_real_session(lib_mock)
        album_mock.return_value = mock.sentinel.album

        result = session.get_album('spotify:album:foo')

        self.assertIs(result, mock.sentinel.album)
        album_mock.assert_called_with(session, uri='spotify:album:foo')

    @mock.patch('spotify.Artist')
    def test_get_artist(self, artist_mock, lib_mock):
        session = tests.create_real_session(lib_mock)
        artist_mock.return_value = mock.sentinel.artist

        result = session.get_artist('spotify:artist:foo')

        self.assertIs(result, mock.sentinel.artist)
        artist_mock.assert_called_with(session, uri='spotify:artist:foo')

    @mock.patch('spotify.Playlist')
    def test_get_playlist(self, playlist_mock, lib_mock):
        session = tests.create_real_session(lib_mock)
        playlist_mock.return_value = mock.sentinel.playlist

        result = session.get_playlist('spotify:playlist:foo')

        self.assertIs(result, mock.sentinel.playlist)
        playlist_mock.assert_called_with(session, uri='spotify:playlist:foo')

    @mock.patch('spotify.User')
    def test_get_user(self, user_mock, lib_mock):
        session = tests.create_real_session(lib_mock)
        user_mock.return_value = mock.sentinel.user

        result = session.get_user('spotify:user:foo')

        self.assertIs(result, mock.sentinel.user)
        user_mock.assert_called_with(session, uri='spotify:user:foo')

    @mock.patch('spotify.Image')
    def test_get_image(self, image_mock, lib_mock):
        session = tests.create_real_session(lib_mock)
        callback = mock.Mock()
        image_mock.return_value = mock.sentinel.image

        result = session.get_image('spotify:image:foo', callback=callback)

        self.assertIs(result, mock.sentinel.image)
        image_mock.assert_called_with(
            session, uri='spotify:image:foo', callback=callback)

    @mock.patch('spotify.Search')
    def test_search(self, search_mock, lib_mock):
        session = tests.create_real_session(lib_mock)
        search_mock.return_value = mock.sentinel.search

        result = session.search('alice')

        self.assertIs(result, mock.sentinel.search)
        search_mock.assert_called_with(
            session, query='alice', callback=None,
            track_offset=0, track_count=20,
            album_offset=0, album_count=20,
            artist_offset=0, artist_count=20,
            playlist_offset=0, playlist_count=20,
            search_type=None)

    @mock.patch('spotify.Toplist')
    def test_toplist(self, toplist_mock, lib_mock):
        session = tests.create_real_session(lib_mock)
        toplist_mock.return_value = mock.sentinel.toplist

        result = session.get_toplist(
            type=spotify.ToplistType.TRACKS, region='NO')

        self.assertIs(result, mock.sentinel.toplist)
        toplist_mock.assert_called_with(
            session, type=spotify.ToplistType.TRACKS, region='NO',
            canonical_username=None, callback=None)


@mock.patch('spotify.session.lib', spec=spotify.lib)
class SessionCallbacksTest(unittest.TestCase):

    def tearDown(self):
        spotify._session_instance = None

    def test_logged_in_callback(self, lib_mock):
        callback = mock.Mock()
        session = tests.create_real_session(lib_mock)
        session.on(spotify.SessionEvent.LOGGED_IN, callback)

        _SessionCallbacks.logged_in(
            session._sp_session, int(spotify.ErrorType.BAD_API_VERSION))

        callback.assert_called_once_with(
            session, spotify.ErrorType.BAD_API_VERSION)

    def test_logged_out_callback(self, lib_mock):
        callback = mock.Mock()
        session = tests.create_real_session(lib_mock)
        session.on(spotify.SessionEvent.LOGGED_OUT, callback)

        _SessionCallbacks.logged_out(session._sp_session)

        callback.assert_called_once_with(session)

    def test_metadata_updated_callback(self, lib_mock):
        callback = mock.Mock()
        session = tests.create_real_session(lib_mock)
        session.on(spotify.SessionEvent.METADATA_UPDATED, callback)

        _SessionCallbacks.metadata_updated(session._sp_session)

        callback.assert_called_once_with(session)

    def test_connection_error_callback(self, lib_mock):
        callback = mock.Mock()
        session = tests.create_real_session(lib_mock)
        session.on(spotify.SessionEvent.CONNECTION_ERROR, callback)

        _SessionCallbacks.connection_error(
            session._sp_session, int(spotify.ErrorType.OK))

        callback.assert_called_once_with(session, spotify.ErrorType.OK)

    def test_message_to_user_callback(self, lib_mock):
        callback = mock.Mock()
        session = tests.create_real_session(lib_mock)
        session.on(spotify.SessionEvent.MESSAGE_TO_USER, callback)
        data = spotify.ffi.new('char[]', b'a log message\n')

        _SessionCallbacks.message_to_user(session._sp_session, data)

        callback.assert_called_once_with(session, 'a log message')

    def test_notify_main_thread_callback(self, lib_mock):
        callback = mock.Mock()
        session = tests.create_real_session(lib_mock)
        session.on(spotify.SessionEvent.NOTIFY_MAIN_THREAD, callback)

        _SessionCallbacks.notify_main_thread(session._sp_session)

        callback.assert_called_once_with(session)

    def test_music_delivery_callback(self, lib_mock):
        sp_audioformat = spotify.ffi.new('sp_audioformat *')
        sp_audioformat.channels = 2
        audio_format = spotify.AudioFormat(sp_audioformat)

        num_frames = 10
        frames_size = audio_format.frame_size() * num_frames
        frames = spotify.ffi.new('char[]', frames_size)
        frames[0:3] = [b'a', b'b', b'c']
        frames_void_ptr = spotify.ffi.cast('void *', frames)

        callback = mock.Mock()
        callback.return_value = num_frames
        session = tests.create_real_session(lib_mock)
        session.on('music_delivery', callback)

        result = _SessionCallbacks.music_delivery(
            session._sp_session, sp_audioformat, frames_void_ptr, num_frames)

        callback.assert_called_once_with(
            session, mock.ANY, mock.ANY, num_frames)
        self.assertEqual(
            callback.call_args[0][1]._sp_audioformat, sp_audioformat)
        self.assertEqual(callback.call_args[0][2][:5], b'abc\x00\x00')
        self.assertEqual(result, num_frames)

    def test_music_delivery_without_callback_does_not_consume(self, lib_mock):
        session = tests.create_real_session(lib_mock)

        sp_audioformat = spotify.ffi.new('sp_audioformat *')
        num_frames = 10
        frames = spotify.ffi.new('char[]', 0)
        frames_void_ptr = spotify.ffi.cast('void *', frames)

        result = _SessionCallbacks.music_delivery(
            session._sp_session, sp_audioformat, frames_void_ptr, num_frames)

        self.assertEqual(result, 0)

    def test_play_token_lost_callback(self, lib_mock):
        callback = mock.Mock()
        session = tests.create_real_session(lib_mock)
        session.on(spotify.SessionEvent.PLAY_TOKEN_LOST, callback)

        _SessionCallbacks.play_token_lost(session._sp_session)

        callback.assert_called_once_with(session)

    def test_log_message_callback(self, lib_mock):
        callback = mock.Mock()
        session = tests.create_real_session(lib_mock)
        session.on(spotify.SessionEvent.LOG_MESSAGE, callback)
        data = spotify.ffi.new('char[]', b'a log message\n')

        _SessionCallbacks.log_message(session._sp_session, data)

        callback.assert_called_once_with(session, 'a log message')

    def test_end_of_track_callback(self, lib_mock):
        callback = mock.Mock()
        session = tests.create_real_session(lib_mock)
        session.on(spotify.SessionEvent.END_OF_TRACK, callback)

        _SessionCallbacks.end_of_track(session._sp_session)

        callback.assert_called_once_with(session)

    def test_streaming_error_callback(self, lib_mock):
        callback = mock.Mock()
        session = tests.create_real_session(lib_mock)
        session.on(spotify.SessionEvent.STREAMING_ERROR, callback)

        _SessionCallbacks.streaming_error(
            session._sp_session, int(spotify.ErrorType.NO_STREAM_AVAILABLE))

        callback.assert_called_once_with(
            session, spotify.ErrorType.NO_STREAM_AVAILABLE)

    def test_user_info_updated_callback(self, lib_mock):
        callback = mock.Mock()
        session = tests.create_real_session(lib_mock)
        session.on(spotify.SessionEvent.USER_INFO_UPDATED, callback)

        _SessionCallbacks.user_info_updated(session._sp_session)

        callback.assert_called_once_with(session)

    def test_start_playback_callback(self, lib_mock):
        callback = mock.Mock()
        session = tests.create_real_session(lib_mock)
        session.on(spotify.SessionEvent.START_PLAYBACK, callback)

        _SessionCallbacks.start_playback(session._sp_session)

        callback.assert_called_once_with(session)

    def test_stop_playback_callback(self, lib_mock):
        callback = mock.Mock()
        session = tests.create_real_session(lib_mock)
        session.on(spotify.SessionEvent.STOP_PLAYBACK, callback)

        _SessionCallbacks.stop_playback(session._sp_session)

        callback.assert_called_once_with(session)

    def test_get_audio_buffer_stats_callback(self, lib_mock):
        callback = mock.Mock()
        callback.return_value = spotify.AudioBufferStats(100, 5)
        session = tests.create_real_session(lib_mock)
        session.on(spotify.SessionEvent.GET_AUDIO_BUFFER_STATS, callback)
        sp_audio_buffer_stats = spotify.ffi.new('sp_audio_buffer_stats *')

        _SessionCallbacks.get_audio_buffer_stats(
            session._sp_session, sp_audio_buffer_stats)

        callback.assert_called_once_with(session)
        self.assertEqual(sp_audio_buffer_stats.samples, 100)
        self.assertEqual(sp_audio_buffer_stats.stutter, 5)

    def test_offline_status_updated_callback(self, lib_mock):
        callback = mock.Mock()
        session = tests.create_real_session(lib_mock)
        session.on(spotify.SessionEvent.OFFLINE_STATUS_UPDATED, callback)

        _SessionCallbacks.offline_status_updated(session._sp_session)

        callback.assert_called_once_with(session)

    def test_credentials_blob_updated_callback(self, lib_mock):
        callback = mock.Mock()
        session = tests.create_real_session(lib_mock)
        session.on(spotify.SessionEvent.CREDENTIALS_BLOB_UPDATED, callback)
        data = spotify.ffi.new('char[]', b'a credentials blob')

        _SessionCallbacks.credentials_blob_updated(
            session._sp_session, data)

        callback.assert_called_once_with(session, b'a credentials blob')

    def test_connection_state_updated_callback(self, lib_mock):
        callback = mock.Mock()
        session = tests.create_real_session(lib_mock)
        session.on(spotify.SessionEvent.CONNECTION_STATE_UPDATED, callback)

        _SessionCallbacks.connection_state_updated(session._sp_session)

        callback.assert_called_once_with(session)

    def test_scrobble_error_callback(self, lib_mock):
        callback = mock.Mock()
        session = tests.create_real_session(lib_mock)
        session.on(spotify.SessionEvent.SCROBBLE_ERROR, callback)

        _SessionCallbacks.scrobble_error(
            session._sp_session, int(spotify.ErrorType.LASTFM_AUTH_ERROR))

        callback.assert_called_once_with(
            session, spotify.ErrorType.LASTFM_AUTH_ERROR)

    def test_private_session_mode_changed_callback(self, lib_mock):
        callback = mock.Mock()
        session = tests.create_real_session(lib_mock)
        session.on(spotify.SessionEvent.PRIVATE_SESSION_MODE_CHANGED, callback)

        _SessionCallbacks.private_session_mode_changed(
            session._sp_session, 1)

        callback.assert_called_once_with(session, True)

########NEW FILE########
__FILENAME__ = test_sink
from __future__ import unicode_literals

import unittest

import spotify
from tests import mock


class BaseSinkTest(object):

    def test_init_connects_to_music_delivery_event(self):
        self.session.on.assert_called_with(
            spotify.SessionEvent.MUSIC_DELIVERY, self.sink._on_music_delivery)

    def test_off_disconnects_from_music_delivery_event(self):
        self.assertEqual(self.session.off.call_count, 0)

        self.sink.off()

        self.session.off.assert_called_with(
            spotify.SessionEvent.MUSIC_DELIVERY, mock.ANY)

    def test_on_connects_to_music_delivery_event(self):
        self.assertEqual(self.session.on.call_count, 1)

        self.sink.off()
        self.sink.on()

        self.assertEqual(self.session.on.call_count, 2)


class AlsaSinkTest(unittest.TestCase, BaseSinkTest):

    def setUp(self):
        self.session = mock.Mock()
        self.session.num_listeners.return_value = 0
        self.alsaaudio = mock.Mock()
        with mock.patch.dict('sys.modules', {'alsaaudio': self.alsaaudio}):
            self.sink = spotify.AlsaSink(self.session)

    def test_off_closes_audio_device(self):
        device_mock = mock.Mock()
        self.sink._device = device_mock

        self.sink.off()

        device_mock.close.assert_called_with()
        self.assertIsNone(self.sink._device)

    def test_music_delivery_creates_device_if_needed(self):
        device = mock.Mock()
        self.alsaaudio.PCM.return_value = device
        audio_format = mock.Mock()
        audio_format.frame_size.return_value = 4
        audio_format.sample_type = spotify.SampleType.INT16_NATIVE_ENDIAN
        num_frames = 2048

        self.sink._on_music_delivery(
            mock.sentinel.session, audio_format, mock.sentinel.frames,
            num_frames)

        self.alsaaudio.PCM.assert_called_with(
            mode=self.alsaaudio.PCM_NONBLOCK, card='default')
        device.setformat.assert_called_with(mock.ANY)
        device.setrate.assert_called_with(audio_format.sample_rate)
        device.setchannels.assert_called_with(audio_format.channels)
        device.setperiodsize.assert_called_with(2048 * 4)

    def test_sets_little_endian_format_if_little_endian_system(self):
        device = mock.Mock()
        self.alsaaudio.PCM.return_value = device
        audio_format = mock.Mock()
        audio_format.frame_size.return_value = 4
        audio_format.sample_type = spotify.SampleType.INT16_NATIVE_ENDIAN
        num_frames = 2048

        with mock.patch('spotify.sink.sys') as sys_mock:
            sys_mock.byteorder = 'little'

            self.sink._on_music_delivery(
                mock.sentinel.session, audio_format, mock.sentinel.frames,
                num_frames)

        device.setformat.assert_called_with(self.alsaaudio.PCM_FORMAT_S16_LE)

    def test_sets_big_endian_format_if_big_endian_system(self):
        device = mock.Mock()
        self.alsaaudio.PCM.return_value = device
        audio_format = mock.Mock()
        audio_format.frame_size.return_value = 4
        audio_format.sample_type = spotify.SampleType.INT16_NATIVE_ENDIAN
        num_frames = 2048

        with mock.patch('spotify.sink.sys') as sys_mock:
            sys_mock.byteorder = 'big'

            self.sink._on_music_delivery(
                mock.sentinel.session, audio_format, mock.sentinel.frames,
                num_frames)

        device.setformat.assert_called_with(self.alsaaudio.PCM_FORMAT_S16_BE)

    def test_music_delivery_writes_frames_to_stream(self):
        self.sink._device = mock.Mock()
        audio_format = mock.Mock()
        audio_format.sample_type = spotify.SampleType.INT16_NATIVE_ENDIAN

        num_consumed_frames = self.sink._on_music_delivery(
            mock.sentinel.session, audio_format, mock.sentinel.frames,
            mock.sentinel.num_frames)

        self.sink._device.write.assert_called_with(mock.sentinel.frames)
        self.assertEqual(
            num_consumed_frames, self.sink._device.write.return_value)


class PortAudioSinkTest(unittest.TestCase, BaseSinkTest):

    def setUp(self):
        self.session = mock.Mock()
        self.session.num_listeners.return_value = 0
        self.pyaudio = mock.Mock()
        with mock.patch.dict('sys.modules', {'pyaudio': self.pyaudio}):
            self.sink = spotify.PortAudioSink(self.session)

    def test_init_creates_device(self):
        self.pyaudio.PyAudio.assert_called_with()
        self.assertEqual(self.sink._device, self.pyaudio.PyAudio.return_value)

    def test_off_closes_audio_stream(self):
        stream_mock = mock.Mock()
        self.sink._stream = stream_mock

        self.sink.off()

        stream_mock.close.assert_called_with()
        self.assertIsNone(self.sink._stream)

    def test_music_delivery_creates_stream_if_needed(self):
        audio_format = mock.Mock()
        audio_format.sample_type = spotify.SampleType.INT16_NATIVE_ENDIAN

        self.sink._on_music_delivery(
            mock.sentinel.session, audio_format, mock.sentinel.frames,
            mock.sentinel.num_frames)

        self.sink._device.open.assert_called_with(
            format=self.pyaudio.paInt16, channels=audio_format.channels,
            rate=audio_format.sample_rate, output=True)
        self.assertEqual(
            self.sink._stream, self.sink._device.open.return_value)

    def test_music_delivery_writes_frames_to_stream(self):
        self.sink._stream = mock.Mock()
        audio_format = mock.Mock()
        audio_format.sample_type = spotify.SampleType.INT16_NATIVE_ENDIAN

        num_consumed_frames = self.sink._on_music_delivery(
            mock.sentinel.session, audio_format, mock.sentinel.frames,
            mock.sentinel.num_frames)

        self.sink._stream.write.assert_called_with(
            mock.sentinel.frames, num_frames=mock.sentinel.num_frames)
        self.assertEqual(num_consumed_frames, mock.sentinel.num_frames)

########NEW FILE########
__FILENAME__ = test_social
from __future__ import unicode_literals

import unittest

import spotify

import tests
from tests import mock


@mock.patch('spotify.social.lib', spec=spotify.lib)
@mock.patch('spotify.session.lib', spec=spotify.lib)
class SocialTest(unittest.TestCase):

    def tearDown(self):
        spotify._session_instance = None

    def test_is_private_session(self, session_lib_mock, lib_mock):
        lib_mock.sp_session_is_private_session.return_value = 0
        session = tests.create_real_session(session_lib_mock)

        result = session.social.private_session

        lib_mock.sp_session_is_private_session.assert_called_with(
            session._sp_session)
        self.assertFalse(result)

    @mock.patch('spotify.connection.lib', spec=spotify.lib)
    def test_set_private_session(
            self, conn_lib_mock, session_lib_mock, lib_mock):
        lib_mock.sp_session_set_private_session.return_value = (
            spotify.ErrorType.OK)
        session = tests.create_real_session(session_lib_mock)

        session.social.private_session = True

        lib_mock.sp_session_set_private_session.assert_called_with(
            session._sp_session, 1)

    @mock.patch('spotify.connection.lib', spec=spotify.lib)
    def test_set_private_session_fail_raises_error(
            self, conn_lib_mock, session_lib_mock, lib_mock):
        lib_mock.sp_session_set_private_session.return_value = (
            spotify.ErrorType.BAD_API_VERSION)
        session = tests.create_real_session(session_lib_mock)

        with self.assertRaises(spotify.Error):
            session.social.private_session = True

    def test_is_scrobbling(self, session_lib_mock, lib_mock):

        def func(sp_session_ptr, sp_social_provider, sp_scrobbling_state_ptr):
            sp_scrobbling_state_ptr[0] = (
                spotify.ScrobblingState.USE_GLOBAL_SETTING)
            return spotify.ErrorType.OK

        lib_mock.sp_session_is_scrobbling.side_effect = func
        session = tests.create_real_session(session_lib_mock)

        result = session.social.is_scrobbling(spotify.SocialProvider.SPOTIFY)

        lib_mock.sp_session_is_scrobbling.assert_called_with(
            session._sp_session, spotify.SocialProvider.SPOTIFY, mock.ANY)
        self.assertIs(result, spotify.ScrobblingState.USE_GLOBAL_SETTING)

    def test_is_scrobbling_fail_raises_error(self, session_lib_mock, lib_mock):
        lib_mock.sp_session_is_scrobbling.return_value = (
            spotify.ErrorType.BAD_API_VERSION)
        session = tests.create_real_session(session_lib_mock)

        with self.assertRaises(spotify.Error):
            session.social.is_scrobbling(spotify.SocialProvider.SPOTIFY)

    def test_set_scrobbling(self, session_lib_mock, lib_mock):
        lib_mock.sp_session_set_scrobbling.return_value = spotify.ErrorType.OK
        session = tests.create_real_session(session_lib_mock)

        session.social.set_scrobbling(
            spotify.SocialProvider.SPOTIFY,
            spotify.ScrobblingState.USE_GLOBAL_SETTING)

        lib_mock.sp_session_set_scrobbling.assert_called_with(
            session._sp_session,
            spotify.SocialProvider.SPOTIFY,
            spotify.ScrobblingState.USE_GLOBAL_SETTING)

    def test_set_scrobbling_fail_raises_error(
            self, session_lib_mock, lib_mock):
        lib_mock.sp_session_set_scrobbling.return_value = (
            spotify.ErrorType.BAD_API_VERSION)
        session = tests.create_real_session(session_lib_mock)

        with self.assertRaises(spotify.Error):
            session.social.set_scrobbling(
                spotify.SocialProvider.SPOTIFY,
                spotify.ScrobblingState.USE_GLOBAL_SETTING)

    def test_is_scrobbling_possible(self, session_lib_mock, lib_mock):

        def func(sp_session_ptr, sp_social_provider, out_ptr):
            out_ptr[0] = 1
            return spotify.ErrorType.OK

        lib_mock.sp_session_is_scrobbling_possible.side_effect = func
        session = tests.create_real_session(session_lib_mock)

        result = session.social.is_scrobbling_possible(
            spotify.SocialProvider.FACEBOOK)

        lib_mock.sp_session_is_scrobbling_possible.assert_called_with(
            session._sp_session, spotify.SocialProvider.FACEBOOK, mock.ANY)
        self.assertTrue(result)

    def test_is_scrobbling_possible_fail_raises_error(
            self, session_lib_mock, lib_mock):
        lib_mock.sp_session_is_scrobbling_possible.return_value = (
            spotify.ErrorType.BAD_API_VERSION)
        session = tests.create_real_session(session_lib_mock)

        with self.assertRaises(spotify.Error):
            session.social.is_scrobbling_possible(
                spotify.SocialProvider.FACEBOOK)

    def test_set_social_credentials(self, session_lib_mock, lib_mock):
        lib_mock.sp_session_set_social_credentials.return_value = (
            spotify.ErrorType.OK)
        session = tests.create_real_session(session_lib_mock)

        session.social.set_social_credentials(
            spotify.SocialProvider.LASTFM, 'alice', 'secret')

        lib_mock.sp_session_set_social_credentials.assert_called_once_with(
            session._sp_session, spotify.SocialProvider.LASTFM,
            mock.ANY, mock.ANY)
        self.assertEqual(
            spotify.ffi.string(
                lib_mock.sp_session_set_social_credentials.call_args[0][2]),
            b'alice')
        self.assertEqual(
            spotify.ffi.string(
                lib_mock.sp_session_set_social_credentials.call_args[0][3]),
            b'secret')

    def test_set_social_credentials_fail_raises_error(
            self, session_lib_mock, lib_mock):
        lib_mock.sp_session_login.return_value = (
            spotify.ErrorType.BAD_API_VERSION)
        session = tests.create_real_session(session_lib_mock)

        with self.assertRaises(spotify.Error):
            session.social.set_social_credentials(
                spotify.SocialProvider.LASTFM, 'alice', 'secret')


class ScrobblingStateTest(unittest.TestCase):

    def test_has_constants(self):
        self.assertEqual(spotify.ScrobblingState.USE_GLOBAL_SETTING, 0)
        self.assertEqual(spotify.ScrobblingState.LOCAL_ENABLED, 1)


class SocialProviderTest(unittest.TestCase):

    def test_has_constants(self):
        self.assertEqual(spotify.SocialProvider.SPOTIFY, 0)
        self.assertEqual(spotify.SocialProvider.FACEBOOK, 1)

########NEW FILE########
__FILENAME__ = test_toplist
from __future__ import unicode_literals

import unittest

import spotify
import tests
from tests import mock


@mock.patch('spotify.toplist.lib', spec=spotify.lib)
class ToplistTest(unittest.TestCase):

    def setUp(self):
        self.session = tests.create_session_mock()
        spotify._session_instance = self.session

    def tearDown(self):
        spotify._session_instance = None

    def assert_fails_if_error(self, lib_mock, func):
        lib_mock.sp_toplistbrowse_error.return_value = (
            spotify.ErrorType.BAD_API_VERSION)
        sp_toplistbrowse = spotify.ffi.cast('sp_toplistbrowse *', 42)
        toplist = spotify.Toplist(
            self.session, sp_toplistbrowse=sp_toplistbrowse)

        with self.assertRaises(spotify.Error):
            func(toplist)

    def test_create_without_type_or_region_or_sp_toplistbrowse_fails(
            self, lib_mock):
        with self.assertRaises(AssertionError):
            spotify.Toplist(self.session)

    def test_create_from_type_and_current_user_region(self, lib_mock):
        sp_toplistbrowse = spotify.ffi.cast('sp_toplistbrowse *', 42)
        lib_mock.sp_toplistbrowse_create.return_value = sp_toplistbrowse

        result = spotify.Toplist(
            self.session, type=spotify.ToplistType.TRACKS,
            region=spotify.ToplistRegion.USER)

        lib_mock.sp_toplistbrowse_create.assert_called_with(
            self.session._sp_session, int(spotify.ToplistType.TRACKS),
            int(spotify.ToplistRegion.USER), spotify.ffi.NULL,
            mock.ANY, mock.ANY)
        self.assertEqual(lib_mock.sp_toplistbrowse_add_ref.call_count, 0)
        self.assertEqual(result._sp_toplistbrowse, sp_toplistbrowse)

    def test_create_from_type_and_specific_user_region(self, lib_mock):
        sp_toplistbrowse = spotify.ffi.cast('sp_toplistbrowse *', 42)
        lib_mock.sp_toplistbrowse_create.return_value = sp_toplistbrowse

        spotify.Toplist(
            self.session, type=spotify.ToplistType.TRACKS,
            region=spotify.ToplistRegion.USER, canonical_username='alice')

        lib_mock.sp_toplistbrowse_create.assert_called_with(
            self.session._sp_session, int(spotify.ToplistType.TRACKS),
            int(spotify.ToplistRegion.USER), mock.ANY, mock.ANY, mock.ANY)
        self.assertEqual(
            spotify.ffi.string(
                lib_mock.sp_toplistbrowse_create.call_args[0][3]),
            b'alice')

    def test_create_from_type_and_country(self, lib_mock):
        sp_toplistbrowse = spotify.ffi.cast('sp_toplistbrowse *', 42)
        lib_mock.sp_toplistbrowse_create.return_value = sp_toplistbrowse

        spotify.Toplist(
            self.session, type=spotify.ToplistType.TRACKS, region='NO')

        lib_mock.sp_toplistbrowse_create.assert_called_with(
            self.session._sp_session, int(spotify.ToplistType.TRACKS),
            20047, spotify.ffi.NULL, mock.ANY, mock.ANY)

    def test_create_with_callback(self, lib_mock):
        sp_toplistbrowse = spotify.ffi.cast('sp_toplistbrowse *', 42)
        lib_mock.sp_toplistbrowse_create.return_value = sp_toplistbrowse
        callback = mock.Mock()

        result = spotify.Toplist(
            self.session, type=spotify.ToplistType.TRACKS,
            region=spotify.ToplistRegion.USER, callback=callback)

        toplistbrowse_complete_cb = (
            lib_mock.sp_toplistbrowse_create.call_args[0][4])
        userdata = lib_mock.sp_toplistbrowse_create.call_args[0][5]
        toplistbrowse_complete_cb(sp_toplistbrowse, userdata)

        result.loaded_event.wait(3)
        callback.assert_called_with(result)

    def test_toplist_is_gone_before_callback_is_called(self, lib_mock):
        sp_toplistbrowse = spotify.ffi.cast('sp_toplistbrowse *', 42)
        lib_mock.sp_toplistbrowse_create.return_value = sp_toplistbrowse
        callback = mock.Mock()

        result = spotify.Toplist(
            self.session, type=spotify.ToplistType.TRACKS,
            region=spotify.ToplistRegion.USER, callback=callback)
        loaded_event = result.loaded_event
        result = None  # noqa
        tests.gc_collect()

        # The mock keeps the handle/userdata alive, thus this test doesn't
        # really test that session._callback_handles keeps the handle alive.
        toplistbrowse_complete_cb = (
            lib_mock.sp_toplistbrowse_create.call_args[0][4])
        userdata = lib_mock.sp_toplistbrowse_create.call_args[0][5]
        toplistbrowse_complete_cb(sp_toplistbrowse, userdata)

        loaded_event.wait(3)
        self.assertEqual(callback.call_count, 1)
        self.assertEqual(
            callback.call_args[0][0]._sp_toplistbrowse, sp_toplistbrowse)

    def test_adds_ref_to_sp_toplistbrowse_when_created(self, lib_mock):
        sp_toplistbrowse = spotify.ffi.cast('sp_toplistbrowse *', 42)

        spotify.Toplist(self.session, sp_toplistbrowse=sp_toplistbrowse)

        lib_mock.sp_toplistbrowse_add_ref.assert_called_once_with(
            sp_toplistbrowse)

    def test_releases_sp_toplistbrowse_when_toplist_dies(self, lib_mock):
        sp_toplistbrowse = spotify.ffi.cast('sp_toplistbrowse *', 42)

        toplist = spotify.Toplist(
            self.session, sp_toplistbrowse=sp_toplistbrowse)
        toplist = None  # noqa
        tests.gc_collect()

        lib_mock.sp_toplistbrowse_release.assert_called_with(sp_toplistbrowse)

    def test_repr(self, lib_mock):
        sp_toplistbrowse = spotify.ffi.cast('sp_toplistbrowse *', 42)
        lib_mock.sp_toplistbrowse_create.return_value = sp_toplistbrowse
        toplist = spotify.Toplist(
            self.session, type=spotify.ToplistType.TRACKS, region='NO')

        result = repr(toplist)

        self.assertEqual(
            result,
            "Toplist(type=<ToplistType.TRACKS: 2>, region=%r, "
            "canonical_username=None)" % 'NO')

    def test_eq(self, lib_mock):
        sp_toplistbrowse = spotify.ffi.cast('sp_toplistbrowse *', 42)
        toplist1 = spotify.Toplist(
            self.session, sp_toplistbrowse=sp_toplistbrowse)
        toplist2 = spotify.Toplist(
            self.session, sp_toplistbrowse=sp_toplistbrowse)

        self.assertTrue(toplist1 == toplist2)
        self.assertFalse(toplist1 == 'foo')

    def test_ne(self, lib_mock):
        sp_toplistbrowse = spotify.ffi.cast('sp_toplistbrowse *', 42)
        toplist1 = spotify.Toplist(
            self.session, sp_toplistbrowse=sp_toplistbrowse)
        toplist2 = spotify.Toplist(
            self.session, sp_toplistbrowse=sp_toplistbrowse)

        self.assertFalse(toplist1 != toplist2)

    def test_hash(self, lib_mock):
        sp_toplistbrowse = spotify.ffi.cast('sp_toplistbrowse *', 42)
        toplist1 = spotify.Toplist(
            self.session, sp_toplistbrowse=sp_toplistbrowse)
        toplist2 = spotify.Toplist(
            self.session, sp_toplistbrowse=sp_toplistbrowse)

        self.assertEqual(hash(toplist1), hash(toplist2))

    def test_is_loaded(self, lib_mock):
        lib_mock.sp_toplistbrowse_is_loaded.return_value = 1
        sp_toplistbrowse = spotify.ffi.cast('sp_toplistbrowse *', 42)
        toplist = spotify.Toplist(
            self.session, sp_toplistbrowse=sp_toplistbrowse)

        result = toplist.is_loaded

        lib_mock.sp_toplistbrowse_is_loaded.assert_called_once_with(
            sp_toplistbrowse)
        self.assertTrue(result)

    @mock.patch('spotify.utils.load')
    def test_load(self, load_mock, lib_mock):
        sp_toplistbrowse = spotify.ffi.cast('sp_toplistbrowse *', 42)
        toplist = spotify.Toplist(
            self.session, sp_toplistbrowse=sp_toplistbrowse)

        toplist.load(10)

        load_mock.assert_called_with(self.session, toplist, timeout=10)

    def test_error(self, lib_mock):
        lib_mock.sp_toplistbrowse_error.return_value = int(
            spotify.ErrorType.OTHER_PERMANENT)
        sp_toplistbrowse = spotify.ffi.cast('sp_toplistbrowse *', 42)
        toplist = spotify.Toplist(
            self.session, sp_toplistbrowse=sp_toplistbrowse)

        result = toplist.error

        lib_mock.sp_toplistbrowse_error.assert_called_once_with(
            sp_toplistbrowse)
        self.assertIs(result, spotify.ErrorType.OTHER_PERMANENT)

    def test_backend_request_duration(self, lib_mock):
        lib_mock.sp_toplistbrowse_backend_request_duration.return_value = 137
        sp_toplistbrowse = spotify.ffi.cast('sp_toplistbrowse *', 42)
        toplist = spotify.Toplist(
            self.session, sp_toplistbrowse=sp_toplistbrowse)

        result = toplist.backend_request_duration

        lib_mock.sp_toplistbrowse_backend_request_duration.assert_called_with(
            sp_toplistbrowse)
        self.assertEqual(result, 137)

    def test_backend_request_duration_when_not_loaded(self, lib_mock):
        lib_mock.sp_toplistbrowse_is_loaded.return_value = 0
        sp_toplistbrowse = spotify.ffi.cast('sp_toplistbrowse *', 42)
        toplist = spotify.Toplist(
            self.session, sp_toplistbrowse=sp_toplistbrowse)

        result = toplist.backend_request_duration

        lib_mock.sp_toplistbrowse_is_loaded.assert_called_with(
            sp_toplistbrowse)
        self.assertEqual(
            lib_mock.sp_toplistbrowse_backend_request_duration.call_count, 0)
        self.assertIsNone(result)

    @mock.patch('spotify.track.lib', spec=spotify.lib)
    def test_tracks(self, track_lib_mock, lib_mock):
        lib_mock.sp_toplistbrowse_error.return_value = spotify.ErrorType.OK
        sp_track = spotify.ffi.cast('sp_track *', 43)
        lib_mock.sp_toplistbrowse_num_tracks.return_value = 1
        lib_mock.sp_toplistbrowse_track.return_value = sp_track
        sp_toplistbrowse = spotify.ffi.cast('sp_toplistbrowse *', 42)
        toplist = spotify.Toplist(
            self.session, sp_toplistbrowse=sp_toplistbrowse)

        self.assertEqual(lib_mock.sp_toplistbrowse_add_ref.call_count, 1)
        result = toplist.tracks
        self.assertEqual(lib_mock.sp_toplistbrowse_add_ref.call_count, 2)

        self.assertEqual(len(result), 1)
        lib_mock.sp_toplistbrowse_num_tracks.assert_called_with(
            sp_toplistbrowse)

        item = result[0]
        self.assertIsInstance(item, spotify.Track)
        self.assertEqual(item._sp_track, sp_track)
        self.assertEqual(lib_mock.sp_toplistbrowse_track.call_count, 1)
        lib_mock.sp_toplistbrowse_track.assert_called_with(sp_toplistbrowse, 0)
        track_lib_mock.sp_track_add_ref.assert_called_with(sp_track)

    def test_tracks_if_no_tracks(self, lib_mock):
        lib_mock.sp_toplistbrowse_error.return_value = spotify.ErrorType.OK
        lib_mock.sp_toplistbrowse_num_tracks.return_value = 0
        sp_toplistbrowse = spotify.ffi.cast('sp_toplistbrowse *', 42)
        toplist = spotify.Toplist(
            self.session, sp_toplistbrowse=sp_toplistbrowse)

        result = toplist.tracks

        self.assertEqual(len(result), 0)
        lib_mock.sp_toplistbrowse_num_tracks.assert_called_with(
            sp_toplistbrowse)
        self.assertEqual(lib_mock.sp_toplistbrowse_track.call_count, 0)

    def test_tracks_if_unloaded(self, lib_mock):
        lib_mock.sp_toplistbrowse_error.return_value = spotify.ErrorType.OK
        lib_mock.sp_toplistbrowse_is_loaded.return_value = 0
        sp_toplistbrowse = spotify.ffi.cast('sp_toplistbrowse *', 42)
        toplist = spotify.Toplist(
            self.session, sp_toplistbrowse=sp_toplistbrowse)

        result = toplist.tracks

        lib_mock.sp_toplistbrowse_is_loaded.assert_called_with(
            sp_toplistbrowse)
        self.assertEqual(len(result), 0)

    def test_tracks_fails_if_error(self, lib_mock):
        self.assert_fails_if_error(lib_mock, lambda s: s.tracks)

    @mock.patch('spotify.album.lib', spec=spotify.lib)
    def test_albums(self, album_lib_mock, lib_mock):
        lib_mock.sp_toplistbrowse_error.return_value = spotify.ErrorType.OK
        sp_album = spotify.ffi.cast('sp_album *', 43)
        lib_mock.sp_toplistbrowse_num_albums.return_value = 1
        lib_mock.sp_toplistbrowse_album.return_value = sp_album
        sp_toplistbrowse = spotify.ffi.cast('sp_toplistbrowse *', 42)
        toplist = spotify.Toplist(
            self.session, sp_toplistbrowse=sp_toplistbrowse)

        self.assertEqual(lib_mock.sp_toplistbrowse_add_ref.call_count, 1)
        result = toplist.albums
        self.assertEqual(lib_mock.sp_toplistbrowse_add_ref.call_count, 2)

        self.assertEqual(len(result), 1)
        lib_mock.sp_toplistbrowse_num_albums.assert_called_with(
            sp_toplistbrowse)

        item = result[0]
        self.assertIsInstance(item, spotify.Album)
        self.assertEqual(item._sp_album, sp_album)
        self.assertEqual(lib_mock.sp_toplistbrowse_album.call_count, 1)
        lib_mock.sp_toplistbrowse_album.assert_called_with(sp_toplistbrowse, 0)
        album_lib_mock.sp_album_add_ref.assert_called_with(sp_album)

    def test_albums_if_no_albums(self, lib_mock):
        lib_mock.sp_toplistbrowse_error.return_value = spotify.ErrorType.OK
        lib_mock.sp_toplistbrowse_num_albums.return_value = 0
        sp_toplistbrowse = spotify.ffi.cast('sp_toplistbrowse *', 42)
        toplist = spotify.Toplist(
            self.session, sp_toplistbrowse=sp_toplistbrowse)

        result = toplist.albums

        self.assertEqual(len(result), 0)
        lib_mock.sp_toplistbrowse_num_albums.assert_called_with(
            sp_toplistbrowse)
        self.assertEqual(lib_mock.sp_toplistbrowse_album.call_count, 0)

    def test_albums_if_unloaded(self, lib_mock):
        lib_mock.sp_toplistbrowse_error.return_value = spotify.ErrorType.OK
        lib_mock.sp_toplistbrowse_is_loaded.return_value = 0
        sp_toplistbrowse = spotify.ffi.cast('sp_toplistbrowse *', 42)
        toplist = spotify.Toplist(
            self.session, sp_toplistbrowse=sp_toplistbrowse)

        result = toplist.albums

        lib_mock.sp_toplistbrowse_is_loaded.assert_called_with(
            sp_toplistbrowse)
        self.assertEqual(len(result), 0)

    def test_albums_fails_if_error(self, lib_mock):
        self.assert_fails_if_error(lib_mock, lambda s: s.albums)

    @mock.patch('spotify.artist.lib', spec=spotify.lib)
    def test_artists(self, artist_lib_mock, lib_mock):
        lib_mock.sp_toplistbrowse_error.return_value = spotify.ErrorType.OK
        sp_artist = spotify.ffi.cast('sp_artist *', 43)
        lib_mock.sp_toplistbrowse_num_artists.return_value = 1
        lib_mock.sp_toplistbrowse_artist.return_value = sp_artist
        sp_toplistbrowse = spotify.ffi.cast('sp_toplistbrowse *', 42)
        toplist = spotify.Toplist(
            self.session, sp_toplistbrowse=sp_toplistbrowse)

        self.assertEqual(lib_mock.sp_toplistbrowse_add_ref.call_count, 1)
        result = toplist.artists
        self.assertEqual(lib_mock.sp_toplistbrowse_add_ref.call_count, 2)

        self.assertEqual(len(result), 1)
        lib_mock.sp_toplistbrowse_num_artists.assert_called_with(
            sp_toplistbrowse)

        item = result[0]
        self.assertIsInstance(item, spotify.Artist)
        self.assertEqual(item._sp_artist, sp_artist)
        self.assertEqual(lib_mock.sp_toplistbrowse_artist.call_count, 1)
        lib_mock.sp_toplistbrowse_artist.assert_called_with(
            sp_toplistbrowse, 0)
        artist_lib_mock.sp_artist_add_ref.assert_called_with(sp_artist)

    def test_artists_if_no_artists(self, lib_mock):
        lib_mock.sp_toplistbrowse_error.return_value = spotify.ErrorType.OK
        lib_mock.sp_toplistbrowse_num_artists.return_value = 0
        sp_toplistbrowse = spotify.ffi.cast('sp_toplistbrowse *', 42)
        toplist = spotify.Toplist(
            self.session, sp_toplistbrowse=sp_toplistbrowse)

        result = toplist.artists

        self.assertEqual(len(result), 0)
        lib_mock.sp_toplistbrowse_num_artists.assert_called_with(
            sp_toplistbrowse)
        self.assertEqual(lib_mock.sp_toplistbrowse_artist.call_count, 0)

    def test_artists_if_unloaded(self, lib_mock):
        lib_mock.sp_toplistbrowse_error.return_value = spotify.ErrorType.OK
        lib_mock.sp_toplistbrowse_is_loaded.return_value = 0
        sp_toplistbrowse = spotify.ffi.cast('sp_toplistbrowse *', 42)
        toplist = spotify.Toplist(
            self.session, sp_toplistbrowse=sp_toplistbrowse)

        result = toplist.artists

        lib_mock.sp_toplistbrowse_is_loaded.assert_called_with(
            sp_toplistbrowse)
        self.assertEqual(len(result), 0)

    def test_artists_fails_if_error(self, lib_mock):
        self.assert_fails_if_error(lib_mock, lambda s: s.artists)


class ToplistRegionTest(unittest.TestCase):

    def test_has_toplist_region_constants(self):
        self.assertEqual(spotify.ToplistRegion.EVERYWHERE, 0)
        self.assertEqual(spotify.ToplistRegion.USER, 1)


class ToplistTypeTest(unittest.TestCase):

    def test_has_toplist_type_constants(self):
        self.assertEqual(spotify.ToplistType.ARTISTS, 0)
        self.assertEqual(spotify.ToplistType.ALBUMS, 1)
        self.assertEqual(spotify.ToplistType.TRACKS, 2)

########NEW FILE########
__FILENAME__ = test_track
from __future__ import unicode_literals

import unittest

import spotify
import tests
from tests import mock


@mock.patch('spotify.track.lib', spec=spotify.lib)
class TrackTest(unittest.TestCase):

    def setUp(self):
        self.session = tests.create_session_mock()

    def assert_fails_if_error(self, lib_mock, func):
        lib_mock.sp_track_error.return_value = (
            spotify.ErrorType.BAD_API_VERSION)
        sp_track = spotify.ffi.cast('sp_track *', 42)
        track = spotify.Track(self.session, sp_track=sp_track)

        with self.assertRaises(spotify.Error):
            func(track)

    def test_create_without_uri_or_sp_track_fails(self, lib_mock):
        with self.assertRaises(AssertionError):
            spotify.Track(self.session)

    @mock.patch('spotify.Link', spec=spotify.Link)
    def test_create_from_uri(self, link_mock, lib_mock):
        sp_track = spotify.ffi.cast('sp_track *', 42)
        link_instance_mock = link_mock.return_value
        link_instance_mock.as_track.return_value = spotify.Track(
            self.session, sp_track=sp_track)
        uri = 'spotify:track:foo'

        result = spotify.Track(self.session, uri=uri)

        link_mock.assert_called_with(self.session, uri=uri)
        link_instance_mock.as_track.assert_called_with()
        lib_mock.sp_track_add_ref.assert_called_with(sp_track)
        self.assertEqual(result._sp_track, sp_track)

    @mock.patch('spotify.Link', spec=spotify.Link)
    def test_create_from_uri_fail_raises_error(self, link_mock, lib_mock):
        link_instance_mock = link_mock.return_value
        link_instance_mock.as_track.return_value = None
        uri = 'spotify:track:foo'

        with self.assertRaises(ValueError):
            spotify.Track(self.session, uri=uri)

    def test_adds_ref_to_sp_track_when_created(self, lib_mock):
        sp_track = spotify.ffi.cast('sp_track *', 42)

        spotify.Track(self.session, sp_track=sp_track)

        lib_mock.sp_track_add_ref.assert_called_with(sp_track)

    def test_releases_sp_track_when_track_dies(self, lib_mock):
        sp_track = spotify.ffi.cast('sp_track *', 42)

        track = spotify.Track(self.session, sp_track=sp_track)
        track = None  # noqa
        tests.gc_collect()

        lib_mock.sp_track_release.assert_called_with(sp_track)

    @mock.patch('spotify.Link', spec=spotify.Link)
    def test_repr(self, link_mock, lib_mock):
        link_instance_mock = link_mock.return_value
        link_instance_mock.uri = 'foo'
        sp_track = spotify.ffi.cast('sp_track *', 42)
        track = spotify.Track(self.session, sp_track=sp_track)

        result = repr(track)

        self.assertEqual(result, 'Track(%r)' % 'foo')

    def test_eq(self, lib_mock):
        sp_track = spotify.ffi.cast('sp_track *', 42)
        track1 = spotify.Track(self.session, sp_track=sp_track)
        track2 = spotify.Track(self.session, sp_track=sp_track)

        self.assertTrue(track1 == track2)
        self.assertFalse(track1 == 'foo')

    def test_ne(self, lib_mock):
        sp_track = spotify.ffi.cast('sp_track *', 42)
        track1 = spotify.Track(self.session, sp_track=sp_track)
        track2 = spotify.Track(self.session, sp_track=sp_track)

        self.assertFalse(track1 != track2)

    def test_hash(self, lib_mock):
        sp_track = spotify.ffi.cast('sp_track *', 42)
        track1 = spotify.Track(self.session, sp_track=sp_track)
        track2 = spotify.Track(self.session, sp_track=sp_track)

        self.assertEqual(hash(track1), hash(track2))

    def test_is_loaded(self, lib_mock):
        lib_mock.sp_track_is_loaded.return_value = 1
        sp_track = spotify.ffi.cast('sp_track *', 42)
        track = spotify.Track(self.session, sp_track=sp_track)

        result = track.is_loaded

        lib_mock.sp_track_is_loaded.assert_called_once_with(sp_track)
        self.assertTrue(result)

    def test_error(self, lib_mock):
        lib_mock.sp_track_error.return_value = int(
            spotify.ErrorType.IS_LOADING)
        sp_track = spotify.ffi.cast('sp_track *', 42)
        track = spotify.Track(self.session, sp_track=sp_track)

        result = track.error

        lib_mock.sp_track_error.assert_called_once_with(sp_track)
        self.assertIs(result, spotify.ErrorType.IS_LOADING)

    @mock.patch('spotify.utils.load')
    def test_load(self, load_mock, lib_mock):
        sp_track = spotify.ffi.cast('sp_track *', 42)
        track = spotify.Track(self.session, sp_track=sp_track)

        track.load(10)

        load_mock.assert_called_with(self.session, track, timeout=10)

    def test_offline_status(self, lib_mock):
        lib_mock.sp_track_error.return_value = spotify.ErrorType.OK
        lib_mock.sp_track_offline_get_status.return_value = 2
        sp_track = spotify.ffi.cast('sp_track *', 42)
        track = spotify.Track(self.session, sp_track=sp_track)

        result = track.offline_status

        lib_mock.sp_track_offline_get_status.assert_called_with(sp_track)
        self.assertIs(result, spotify.TrackOfflineStatus.DOWNLOADING)

    def test_offline_status_is_none_if_unloaded(self, lib_mock):
        lib_mock.sp_track_error.return_value = spotify.ErrorType.IS_LOADING
        lib_mock.sp_track_is_loaded.return_value = 0
        sp_track = spotify.ffi.cast('sp_track *', 42)
        track = spotify.Track(self.session, sp_track=sp_track)

        result = track.offline_status

        lib_mock.sp_track_is_loaded.assert_called_with(sp_track)
        self.assertIsNone(result)

    def test_offline_status_fails_if_error(self, lib_mock):
        lib_mock.sp_track_error.return_value = (
            spotify.ErrorType.BAD_API_VERSION)
        lib_mock.sp_track_offline_get_status.return_value = 2
        sp_track = spotify.ffi.cast('sp_track *', 42)
        track = spotify.Track(self.session, sp_track=sp_track)

        with self.assertRaises(spotify.Error):
            track.offline_status

    def test_availability(self, lib_mock):
        lib_mock.sp_track_error.return_value = spotify.ErrorType.OK
        lib_mock.sp_track_get_availability.return_value = 1
        sp_track = spotify.ffi.cast('sp_track *', 42)
        track = spotify.Track(self.session, sp_track=sp_track)

        result = track.availability

        lib_mock.sp_track_get_availability.assert_called_with(
            self.session._sp_session, sp_track)
        self.assertIs(result, spotify.TrackAvailability.AVAILABLE)

    def test_availability_is_none_if_unloaded(self, lib_mock):
        lib_mock.sp_track_error.return_value = spotify.ErrorType.IS_LOADING
        lib_mock.sp_track_is_loaded.return_value = 0
        sp_track = spotify.ffi.cast('sp_track *', 42)
        track = spotify.Track(self.session, sp_track=sp_track)

        result = track.availability

        lib_mock.sp_track_is_loaded.assert_called_with(sp_track)
        self.assertIsNone(result)

    def test_availability_fails_if_error(self, lib_mock):
        self.assert_fails_if_error(lib_mock, lambda t: t.availability)

    def test_is_local(self, lib_mock):
        lib_mock.sp_track_error.return_value = spotify.ErrorType.OK
        lib_mock.sp_track_is_local.return_value = 1
        sp_track = spotify.ffi.cast('sp_track *', 42)
        track = spotify.Track(self.session, sp_track=sp_track)

        result = track.is_local

        lib_mock.sp_track_is_local.assert_called_with(
            self.session._sp_session, sp_track)
        self.assertTrue(result)

    def test_is_local_is_none_if_unloaded(self, lib_mock):
        lib_mock.sp_track_error.return_value = spotify.ErrorType.IS_LOADING
        lib_mock.sp_track_is_loaded.return_value = 0
        sp_track = spotify.ffi.cast('sp_track *', 42)
        track = spotify.Track(self.session, sp_track=sp_track)

        result = track.is_local

        lib_mock.sp_track_is_loaded.assert_called_with(sp_track)
        self.assertIsNone(result)

    def test_is_local_fails_if_error(self, lib_mock):
        self.assert_fails_if_error(lib_mock, lambda t: t.is_local)

    def test_is_autolinked(self, lib_mock):
        lib_mock.sp_track_error.return_value = spotify.ErrorType.OK
        lib_mock.sp_track_is_autolinked.return_value = 1
        sp_track = spotify.ffi.cast('sp_track *', 42)
        track = spotify.Track(self.session, sp_track=sp_track)

        result = track.is_autolinked

        lib_mock.sp_track_is_autolinked.assert_called_with(
            self.session._sp_session, sp_track)
        self.assertTrue(result)

    def test_is_autolinked_is_none_if_unloaded(self, lib_mock):
        lib_mock.sp_track_error.return_value = spotify.ErrorType.IS_LOADING
        lib_mock.sp_track_is_loaded.return_value = 0
        sp_track = spotify.ffi.cast('sp_track *', 42)
        track = spotify.Track(self.session, sp_track=sp_track)

        result = track.is_autolinked

        lib_mock.sp_track_is_loaded.assert_called_with(sp_track)
        self.assertIsNone(result)

    def test_is_autolinked_fails_if_error(self, lib_mock):
        self.assert_fails_if_error(lib_mock, lambda t: t.is_autolinked)

    def test_playable(self, lib_mock):
        lib_mock.sp_track_error.return_value = spotify.ErrorType.OK
        sp_track_playable = spotify.ffi.cast('sp_track *', 43)
        lib_mock.sp_track_get_playable.return_value = sp_track_playable
        sp_track = spotify.ffi.cast('sp_track *', 42)
        track = spotify.Track(self.session, sp_track=sp_track)

        result = track.playable

        lib_mock.sp_track_get_playable.assert_called_with(
            self.session._sp_session, sp_track)
        lib_mock.sp_track_add_ref.assert_called_with(sp_track_playable)
        self.assertIsInstance(result, spotify.Track)
        self.assertEqual(result._sp_track, sp_track_playable)

    def test_playable_is_none_if_unloaded(self, lib_mock):
        lib_mock.sp_track_error.return_value = spotify.ErrorType.IS_LOADING
        lib_mock.sp_track_is_loaded.return_value = 0
        sp_track = spotify.ffi.cast('sp_track *', 42)
        track = spotify.Track(self.session, sp_track=sp_track)

        result = track.playable

        lib_mock.sp_track_is_loaded.assert_called_with(sp_track)
        self.assertIsNone(result)

    def test_playable_fails_if_error(self, lib_mock):
        self.assert_fails_if_error(lib_mock, lambda t: t.playable)

    def test_is_placeholder(self, lib_mock):
        lib_mock.sp_track_error.return_value = spotify.ErrorType.OK
        lib_mock.sp_track_is_placeholder.return_value = 1
        sp_track = spotify.ffi.cast('sp_track *', 42)
        track = spotify.Track(self.session, sp_track=sp_track)

        result = track.is_placeholder

        lib_mock.sp_track_is_placeholder.assert_called_with(sp_track)
        self.assertTrue(result)

    def test_is_placeholder_is_none_if_unloaded(self, lib_mock):
        lib_mock.sp_track_error.return_value = spotify.ErrorType.IS_LOADING
        lib_mock.sp_track_is_loaded.return_value = 0
        sp_track = spotify.ffi.cast('sp_track *', 42)
        track = spotify.Track(self.session, sp_track=sp_track)

        result = track.is_placeholder

        lib_mock.sp_track_is_loaded.assert_called_with(sp_track)
        self.assertIsNone(result)

    def test_is_placeholder_fails_if_error(self, lib_mock):
        self.assert_fails_if_error(lib_mock, lambda t: t.is_placeholder)

    def test_is_starred(self, lib_mock):
        lib_mock.sp_track_error.return_value = spotify.ErrorType.OK
        lib_mock.sp_track_is_starred.return_value = 1
        sp_track = spotify.ffi.cast('sp_track *', 42)
        track = spotify.Track(self.session, sp_track=sp_track)

        result = track.starred

        lib_mock.sp_track_is_starred.assert_called_with(
            self.session._sp_session, sp_track)
        self.assertTrue(result)

    def test_is_starred_is_none_if_unloaded(self, lib_mock):
        lib_mock.sp_track_error.return_value = spotify.ErrorType.IS_LOADING
        lib_mock.sp_track_is_loaded.return_value = 0
        sp_track = spotify.ffi.cast('sp_track *', 42)
        track = spotify.Track(self.session, sp_track=sp_track)

        result = track.starred

        lib_mock.sp_track_is_loaded.assert_called_with(sp_track)
        self.assertIsNone(result)

    def test_is_starred_fails_if_error(self, lib_mock):
        self.assert_fails_if_error(lib_mock, lambda t: t.starred)

    def test_set_starred(self, lib_mock):
        lib_mock.sp_track_set_starred.return_value = spotify.ErrorType.OK
        sp_track = spotify.ffi.cast('sp_track *', 42)
        track = spotify.Track(self.session, sp_track=sp_track)

        track.starred = True

        lib_mock.sp_track_set_starred.assert_called_with(
            self.session._sp_session, mock.ANY, 1, 1)

    def test_set_starred_fails_if_error(self, lib_mock):
        tests.create_session_mock()
        lib_mock.sp_track_set_starred.return_value = (
            spotify.ErrorType.BAD_API_VERSION)
        sp_track = spotify.ffi.cast('sp_track *', 42)
        track = spotify.Track(self.session, sp_track=sp_track)

        with self.assertRaises(spotify.Error):
            track.starred = True

    @mock.patch('spotify.artist.lib', spec=spotify.lib)
    def test_artists(self, artist_lib_mock, lib_mock):
        lib_mock.sp_track_error.return_value = spotify.ErrorType.OK
        sp_artist = spotify.ffi.cast('sp_artist *', 43)
        lib_mock.sp_track_num_artists.return_value = 1
        lib_mock.sp_track_artist.return_value = sp_artist
        sp_track = spotify.ffi.cast('sp_track *', 42)
        track = spotify.Track(self.session, sp_track=sp_track)

        result = track.artists

        self.assertEqual(len(result), 1)
        lib_mock.sp_track_num_artists.assert_called_with(sp_track)

        item = result[0]
        self.assertIsInstance(item, spotify.Artist)
        self.assertEqual(item._sp_artist, sp_artist)
        self.assertEqual(lib_mock.sp_track_artist.call_count, 1)
        lib_mock.sp_track_artist.assert_called_with(sp_track, 0)
        artist_lib_mock.sp_artist_add_ref.assert_called_with(sp_artist)

    def test_artists_if_no_artists(self, lib_mock):
        lib_mock.sp_track_error.return_value = spotify.ErrorType.OK
        lib_mock.sp_track_num_artists.return_value = 0
        sp_track = spotify.ffi.cast('sp_track *', 42)
        track = spotify.Track(self.session, sp_track=sp_track)

        result = track.artists

        self.assertEqual(len(result), 0)
        lib_mock.sp_track_num_artists.assert_called_with(sp_track)
        self.assertEqual(lib_mock.sp_track_artist.call_count, 0)

    def test_artists_if_unloaded(self, lib_mock):
        lib_mock.sp_track_error.return_value = spotify.ErrorType.IS_LOADING
        lib_mock.sp_track_is_loaded.return_value = 0
        sp_track = spotify.ffi.cast('sp_track *', 42)
        track = spotify.Track(self.session, sp_track=sp_track)

        result = track.artists

        lib_mock.sp_track_is_loaded.assert_called_with(sp_track)
        self.assertEqual(len(result), 0)

    def test_artists_fails_if_error(self, lib_mock):
        self.assert_fails_if_error(lib_mock, lambda t: t.artists)

    @mock.patch('spotify.album.lib', spec=spotify.lib)
    def test_album(self, album_lib_mock, lib_mock):
        lib_mock.sp_track_error.return_value = spotify.ErrorType.OK
        sp_album = spotify.ffi.cast('sp_album *', 43)
        lib_mock.sp_track_album.return_value = sp_album
        sp_track = spotify.ffi.cast('sp_track *', 42)
        track = spotify.Track(self.session, sp_track=sp_track)

        result = track.album

        lib_mock.sp_track_album.assert_called_with(sp_track)
        self.assertEqual(album_lib_mock.sp_album_add_ref.call_count, 1)
        self.assertIsInstance(result, spotify.Album)
        self.assertEqual(result._sp_album, sp_album)

    @mock.patch('spotify.album.lib', spec=spotify.lib)
    def test_album_if_unloaded(self, album_lib_mock, lib_mock):
        lib_mock.sp_track_error.return_value = spotify.ErrorType.IS_LOADING
        lib_mock.sp_track_is_loaded.return_value = 0
        sp_track = spotify.ffi.cast('sp_track *', 42)
        track = spotify.Track(self.session, sp_track=sp_track)

        result = track.album

        self.assertEqual(lib_mock.sp_track_album.call_count, 0)
        self.assertIsNone(result)

    def test_album_fails_if_error(self, lib_mock):
        self.assert_fails_if_error(lib_mock, lambda t: t.album)

    def test_name(self, lib_mock):
        lib_mock.sp_track_error.return_value = spotify.ErrorType.OK
        lib_mock.sp_track_name.return_value = spotify.ffi.new(
            'char[]', b'Foo Bar Baz')
        sp_track = spotify.ffi.cast('sp_track *', 42)
        track = spotify.Track(self.session, sp_track=sp_track)

        result = track.name

        lib_mock.sp_track_name.assert_called_once_with(sp_track)
        self.assertEqual(result, 'Foo Bar Baz')

    def test_name_is_none_if_unloaded(self, lib_mock):
        lib_mock.sp_track_error.return_value = spotify.ErrorType.IS_LOADING
        lib_mock.sp_track_is_loaded.return_value = 0
        lib_mock.sp_track_name.return_value = spotify.ffi.new('char[]', b'')
        sp_track = spotify.ffi.cast('sp_track *', 42)
        track = spotify.Track(self.session, sp_track=sp_track)

        result = track.name

        self.assertEqual(lib_mock.sp_track_name.call_count, 0)
        self.assertIsNone(result)

    def test_name_fails_if_error(self, lib_mock):
        self.assert_fails_if_error(lib_mock, lambda t: t.name)

    def test_duration(self, lib_mock):
        lib_mock.sp_track_error.return_value = spotify.ErrorType.OK
        lib_mock.sp_track_duration.return_value = 60000
        sp_track = spotify.ffi.cast('sp_track *', 42)
        track = spotify.Track(self.session, sp_track=sp_track)

        result = track.duration

        lib_mock.sp_track_duration.assert_called_with(sp_track)
        self.assertEqual(result, 60000)

    def test_duration_is_none_if_unloaded(self, lib_mock):
        lib_mock.sp_track_error.return_value = spotify.ErrorType.IS_LOADING
        lib_mock.sp_track_is_loaded.return_value = 0
        sp_track = spotify.ffi.cast('sp_track *', 42)
        track = spotify.Track(self.session, sp_track=sp_track)

        result = track.duration

        self.assertEqual(lib_mock.sp_track_duration.call_count, 0)
        self.assertIsNone(result)

    def test_duration_fails_if_error(self, lib_mock):
        self.assert_fails_if_error(lib_mock, lambda t: t.duration)

    def test_popularity(self, lib_mock):
        lib_mock.sp_track_error.return_value = spotify.ErrorType.OK
        lib_mock.sp_track_popularity.return_value = 90
        sp_track = spotify.ffi.cast('sp_track *', 42)
        track = spotify.Track(self.session, sp_track=sp_track)

        result = track.popularity

        lib_mock.sp_track_popularity.assert_called_with(sp_track)
        self.assertEqual(result, 90)

    def test_popularity_is_none_if_unloaded(self, lib_mock):
        lib_mock.sp_track_error.return_value = spotify.ErrorType.IS_LOADING
        lib_mock.sp_track_is_loaded.return_value = 0
        sp_track = spotify.ffi.cast('sp_track *', 42)
        track = spotify.Track(self.session, sp_track=sp_track)

        result = track.popularity

        self.assertEqual(lib_mock.sp_track_popularity.call_count, 0)
        self.assertIsNone(result)

    def test_popularity_fails_if_error(self, lib_mock):
        self.assert_fails_if_error(lib_mock, lambda t: t.popularity)

    def test_disc(self, lib_mock):
        lib_mock.sp_track_error.return_value = spotify.ErrorType.OK
        lib_mock.sp_track_disc.return_value = 2
        sp_track = spotify.ffi.cast('sp_track *', 42)
        track = spotify.Track(self.session, sp_track=sp_track)

        result = track.disc

        lib_mock.sp_track_disc.assert_called_with(sp_track)
        self.assertEqual(result, 2)

    def test_disc_is_none_if_unloaded(self, lib_mock):
        lib_mock.sp_track_error.return_value = spotify.ErrorType.IS_LOADING
        lib_mock.sp_track_is_loaded.return_value = 0
        sp_track = spotify.ffi.cast('sp_track *', 42)
        track = spotify.Track(self.session, sp_track=sp_track)

        result = track.disc

        self.assertEqual(lib_mock.sp_track_disc.call_count, 0)
        self.assertIsNone(result)

    def test_disc_fails_if_error(self, lib_mock):
        self.assert_fails_if_error(lib_mock, lambda t: t.disc)

    def test_index(self, lib_mock):
        lib_mock.sp_track_error.return_value = spotify.ErrorType.OK
        lib_mock.sp_track_index.return_value = 7
        sp_track = spotify.ffi.cast('sp_track *', 42)
        track = spotify.Track(self.session, sp_track=sp_track)

        result = track.index

        lib_mock.sp_track_index.assert_called_with(sp_track)
        self.assertEqual(result, 7)

    def test_index_is_none_if_unloaded(self, lib_mock):
        lib_mock.sp_track_error.return_value = spotify.ErrorType.IS_LOADING
        lib_mock.sp_track_is_loaded.return_value = 0
        sp_track = spotify.ffi.cast('sp_track *', 42)
        track = spotify.Track(self.session, sp_track=sp_track)

        result = track.index

        self.assertEqual(lib_mock.sp_track_index.call_count, 0)
        self.assertIsNone(result)

    def test_index_fails_if_error(self, lib_mock):
        self.assert_fails_if_error(lib_mock, lambda t: t.index)

    @mock.patch('spotify.Link', spec=spotify.Link)
    def test_link_creates_link_to_track(self, link_mock, lib_mock):
        sp_track = spotify.ffi.cast('sp_track *', 42)
        track = spotify.Track(self.session, sp_track=sp_track)
        sp_link = spotify.ffi.cast('sp_link *', 43)
        lib_mock.sp_link_create_from_track.return_value = sp_link
        link_mock.return_value = mock.sentinel.link

        result = track.link

        lib_mock.sp_link_create_from_track.asssert_called_once_with(
            sp_track, 0)
        link_mock.assert_called_once_with(
            self.session, sp_link=sp_link, add_ref=False)
        self.assertEqual(result, mock.sentinel.link)

    @mock.patch('spotify.Link', spec=spotify.Link)
    def test_link_with_offset(self, link_mock, lib_mock):
        sp_track = spotify.ffi.cast('sp_track *', 42)
        track = spotify.Track(self.session, sp_track=sp_track)
        sp_link = spotify.ffi.cast('sp_link *', 43)
        lib_mock.sp_link_create_from_track.return_value = sp_link
        link_mock.return_value = mock.sentinel.link

        result = track.link_with_offset(90)

        lib_mock.sp_link_create_from_track.asssert_called_once_with(
            sp_track, 90)
        link_mock.assert_called_once_with(
            self.session, sp_link=sp_link, add_ref=False)
        self.assertEqual(result, mock.sentinel.link)


class TrackAvailability(unittest.TestCase):

    def test_has_constants(self):
        self.assertEqual(spotify.TrackAvailability.UNAVAILABLE, 0)
        self.assertEqual(spotify.TrackAvailability.AVAILABLE, 1)


class TrackOfflineStatusTest(unittest.TestCase):

    def test_has_constants(self):
        self.assertEqual(spotify.TrackOfflineStatus.NO, 0)
        self.assertEqual(spotify.TrackOfflineStatus.DOWNLOADING, 2)

########NEW FILE########
__FILENAME__ = test_user
from __future__ import unicode_literals

import unittest

import spotify
import tests
from tests import mock


@mock.patch('spotify.user.lib', spec=spotify.lib)
class UserTest(unittest.TestCase):

    def setUp(self):
        self.session = tests.create_session_mock()

    def test_create_without_uri_or_sp_user_fails(self, lib_mock):
        with self.assertRaises(AssertionError):
            spotify.User(self.session)

    @mock.patch('spotify.Link', spec=spotify.Link)
    def test_create_from_uri(self, link_mock, lib_mock):
        sp_user = spotify.ffi.cast('sp_user *', 42)
        link_instance_mock = link_mock.return_value
        link_instance_mock.as_user.return_value = spotify.User(
            self.session, sp_user=sp_user)
        uri = 'spotify:user:foo'

        result = spotify.User(self.session, uri=uri)

        link_mock.assert_called_with(self.session, uri=uri)
        link_instance_mock.as_user.assert_called_with()
        lib_mock.sp_user_add_ref.assert_called_with(sp_user)
        self.assertEqual(result._sp_user, sp_user)

    @mock.patch('spotify.Link', spec=spotify.Link)
    def test_create_from_uri_fail_raises_error(self, link_mock, lib_mock):
        link_instance_mock = link_mock.return_value
        link_instance_mock.as_user.return_value = None
        uri = 'spotify:user:foo'

        with self.assertRaises(ValueError):
            spotify.User(self.session, uri=uri)

    def test_adds_ref_to_sp_user_when_created(self, lib_mock):
        sp_user = spotify.ffi.cast('sp_user *', 42)

        spotify.User(self.session, sp_user=sp_user)

        lib_mock.sp_user_add_ref.assert_called_once_with(sp_user)

    def test_releases_sp_user_when_user_dies(self, lib_mock):
        sp_user = spotify.ffi.cast('sp_user *', 42)

        user = spotify.User(self.session, sp_user=sp_user)
        user = None  # noqa
        tests.gc_collect()

        lib_mock.sp_user_release.assert_called_with(sp_user)

    @mock.patch('spotify.Link', spec=spotify.Link)
    def test_repr(self, link_mock, lib_mock):
        link_instance_mock = link_mock.return_value
        link_instance_mock.uri = 'foo'
        sp_user = spotify.ffi.cast('sp_user *', 42)
        user = spotify.User(self.session, sp_user=sp_user)

        result = repr(user)

        self.assertEqual(result, 'User(%r)' % 'foo')

    def test_canonical_name(self, lib_mock):
        lib_mock.sp_user_canonical_name.return_value = spotify.ffi.new(
            'char[]', b'alicefoobar')
        sp_user = spotify.ffi.cast('sp_user *', 42)
        user = spotify.User(self.session, sp_user=sp_user)

        result = user.canonical_name

        lib_mock.sp_user_canonical_name.assert_called_once_with(sp_user)
        self.assertEqual(result, 'alicefoobar')

    def test_display_name(self, lib_mock):
        lib_mock.sp_user_display_name.return_value = spotify.ffi.new(
            'char[]', b'Alice Foobar')
        sp_user = spotify.ffi.cast('sp_user *', 42)
        user = spotify.User(self.session, sp_user=sp_user)

        result = user.display_name

        lib_mock.sp_user_display_name.assert_called_once_with(sp_user)
        self.assertEqual(result, 'Alice Foobar')

    def test_is_loaded(self, lib_mock):
        lib_mock.sp_user_is_loaded.return_value = 1
        sp_user = spotify.ffi.cast('sp_user *', 42)
        user = spotify.User(self.session, sp_user=sp_user)

        result = user.is_loaded

        lib_mock.sp_user_is_loaded.assert_called_once_with(sp_user)
        self.assertTrue(result)

    @mock.patch('spotify.utils.load')
    def test_load(self, load_mock, lib_mock):
        sp_user = spotify.ffi.cast('sp_user *', 42)
        user = spotify.User(self.session, sp_user=sp_user)

        user.load(10)

        load_mock.assert_called_with(self.session, user, timeout=10)

    @mock.patch('spotify.Link', spec=spotify.Link)
    def test_link_creates_link_to_user(self, link_mock, lib_mock):
        sp_user = spotify.ffi.cast('sp_user *', 42)
        user = spotify.User(self.session, sp_user=sp_user)
        sp_link = spotify.ffi.cast('sp_link *', 43)
        lib_mock.sp_link_create_from_user.return_value = sp_link
        link_mock.return_value = mock.sentinel.link

        result = user.link

        link_mock.assert_called_once_with(
            self.session, sp_link=sp_link, add_ref=False)
        self.assertEqual(result, mock.sentinel.link)

    def test_starred(self, lib_mock):
        self.session.get_starred.return_value = mock.sentinel.playlist
        lib_mock.sp_user_canonical_name.return_value = spotify.ffi.new(
            'char[]', b'alice')
        sp_user = spotify.ffi.cast('sp_user *', 42)
        user = spotify.User(self.session, sp_user=sp_user)

        result = user.starred

        self.session.get_starred.assert_called_with('alice')
        self.assertEqual(result, mock.sentinel.playlist)

    def test_published_playlists(self, lib_mock):
        self.session.get_published_playlists.return_value = (
            mock.sentinel.playlist_container)
        lib_mock.sp_user_canonical_name.return_value = spotify.ffi.new(
            'char[]', b'alice')
        sp_user = spotify.ffi.cast('sp_user *', 42)
        user = spotify.User(self.session, sp_user=sp_user)

        result = user.published_playlists

        self.session.get_published_playlists.assert_called_with('alice')
        self.assertEqual(result, mock.sentinel.playlist_container)

########NEW FILE########
__FILENAME__ = test_utils
# encoding: utf-8

from __future__ import unicode_literals

import unittest

import spotify
from spotify import utils
import tests
from tests import mock


class EventEmitterTest(unittest.TestCase):

    def test_listener_receives_event_args(self):
        listener_mock = mock.Mock()
        emitter = utils.EventEmitter()
        emitter.on('some_event', listener_mock)

        emitter.emit('some_event', 'abc', 'def')

        listener_mock.assert_called_with('abc', 'def')

    def test_listener_receives_both_user_and_event_args(self):
        listener_mock = mock.Mock()
        emitter = utils.EventEmitter()

        emitter.on('some_event', listener_mock, 1, 2, 3)
        emitter.emit('some_event', 'abc')

        listener_mock.assert_called_with('abc', 1, 2, 3)

    def test_multiple_listeners_for_same_event(self):
        listener_mock1 = mock.Mock()
        listener_mock2 = mock.Mock()
        emitter = utils.EventEmitter()

        emitter.on('some_event', listener_mock1, 1, 2, 3)
        emitter.on('some_event', listener_mock2, 4, 5)
        emitter.emit('some_event', 'abc')

        listener_mock1.assert_called_with('abc', 1, 2, 3)
        listener_mock2.assert_called_with('abc', 4, 5)

    def test_removing_a_listener(self):
        listener_mock1 = mock.Mock()
        listener_mock2 = mock.Mock()
        emitter = utils.EventEmitter()

        emitter.on('some_event', listener_mock1, 123)
        emitter.on('some_event', listener_mock1, 456)
        emitter.on('some_event', listener_mock2, 78)
        emitter.off('some_event', listener_mock1)
        emitter.emit('some_event')

        self.assertEqual(listener_mock1.call_count, 0)
        listener_mock2.assert_called_with(78)

    def test_removing_all_listeners_for_an_event(self):
        listener_mock1 = mock.Mock()
        listener_mock2 = mock.Mock()
        emitter = utils.EventEmitter()

        emitter.on('some_event', listener_mock1)
        emitter.on('some_event', listener_mock2)
        emitter.off('some_event')
        emitter.emit('some_event')

        self.assertEqual(listener_mock1.call_count, 0)
        self.assertEqual(listener_mock2.call_count, 0)

    def test_removing_all_listeners_for_all_events(self):
        listener_mock1 = mock.Mock()
        listener_mock2 = mock.Mock()
        emitter = utils.EventEmitter()

        emitter.on('some_event', listener_mock1)
        emitter.on('another_event', listener_mock2)
        emitter.off()
        emitter.emit('some_event')
        emitter.emit('another_event')

        self.assertEqual(listener_mock1.call_count, 0)
        self.assertEqual(listener_mock2.call_count, 0)

    def test_listener_returning_false_is_removed(self):
        listener_mock1 = mock.Mock(return_value=False)
        listener_mock2 = mock.Mock()
        emitter = utils.EventEmitter()

        emitter.on('some_event', listener_mock1)
        emitter.on('some_event', listener_mock2)
        emitter.emit('some_event')
        emitter.emit('some_event')

        self.assertEqual(listener_mock1.call_count, 1)
        self.assertEqual(listener_mock2.call_count, 2)

    def test_num_listeners_returns_total_number_of_listeners(self):
        listener_mock1 = mock.Mock()
        listener_mock2 = mock.Mock()
        emitter = utils.EventEmitter()

        self.assertEqual(emitter.num_listeners(), 0)

        emitter.on('some_event', listener_mock1)
        self.assertEqual(emitter.num_listeners(), 1)

        emitter.on('another_event', listener_mock1)
        emitter.on('another_event', listener_mock2)
        self.assertEqual(emitter.num_listeners(), 3)

    def test_num_listeners_returns_number_of_listeners_for_event(self):
        listener_mock1 = mock.Mock()
        listener_mock2 = mock.Mock()
        emitter = utils.EventEmitter()

        self.assertEqual(emitter.num_listeners('unknown_event'), 0)

        emitter.on('some_event', listener_mock1)
        self.assertEqual(emitter.num_listeners('some_event'), 1)

        emitter.on('another_event', listener_mock1)
        emitter.on('another_event', listener_mock2)
        self.assertEqual(emitter.num_listeners('another_event'), 2)

    def test_call_fails_if_zero_listeners_for_event(self):
        emitter = utils.EventEmitter()

        with self.assertRaises(AssertionError):
            emitter.call('some_event')

    def test_call_fails_if_multiple_listeners_for_event(self):
        listener_mock1 = mock.Mock()
        listener_mock2 = mock.Mock()
        emitter = utils.EventEmitter()

        emitter.on('some_event', listener_mock1)
        emitter.on('some_event', listener_mock2)

        with self.assertRaises(AssertionError):
            emitter.call('some_event')

    def test_call_calls_and_returns_result_of_a_single_listener(self):
        listener_mock = mock.Mock()
        emitter = utils.EventEmitter()

        emitter.on('some_event', listener_mock, 1, 2, 3)
        result = emitter.call('some_event', 'abc')

        listener_mock.assert_called_with('abc', 1, 2, 3)
        self.assertEqual(result, listener_mock.return_value)


class IntEnumTest(unittest.TestCase):

    def setUp(self):
        class Foo(utils.IntEnum):
            pass

        self.Foo = Foo

        self.Foo.add('bar', 1)
        self.Foo.add('baz', 2)

    def test_has_pretty_repr(self):
        self.assertEqual(repr(self.Foo.bar), '<Foo.bar: 1>')
        self.assertEqual(repr(self.Foo.baz), '<Foo.baz: 2>')

    def test_is_equal_to_the_int_value(self):
        self.assertEqual(self.Foo.bar, 1)
        self.assertEqual(self.Foo.baz, 2)

    def test_two_instances_with_same_value_is_identical(self):
        self.assertIs(self.Foo(1), self.Foo.bar)
        self.assertIs(self.Foo(2), self.Foo.baz)
        self.assertIsNot(self.Foo(2), self.Foo.bar)
        self.assertIsNot(self.Foo(1), self.Foo.baz)


@mock.patch('spotify.search.lib', spec=spotify.lib)
class SequenceTest(unittest.TestCase):

    def test_adds_ref_to_sp_obj_when_created(self, lib_mock):
        sp_search = spotify.ffi.cast('sp_search *', 42)
        utils.Sequence(
            sp_obj=sp_search,
            add_ref_func=lib_mock.sp_search_add_ref,
            release_func=lib_mock.sp_search_release,
            len_func=None,
            getitem_func=None)

        self.assertEqual(lib_mock.sp_search_add_ref.call_count, 1)

    def test_releases_sp_obj_when_sequence_dies(self, lib_mock):
        sp_search = spotify.ffi.cast('sp_search *', 42)
        seq = utils.Sequence(
            sp_obj=sp_search,
            add_ref_func=lib_mock.sp_search_add_ref,
            release_func=lib_mock.sp_search_release,
            len_func=None,
            getitem_func=None)

        seq = None  # noqa
        tests.gc_collect()

        self.assertEqual(lib_mock.sp_search_release.call_count, 1)

    def test_len_calls_len_func(self, lib_mock):
        sp_search = spotify.ffi.cast('sp_search *', 42)
        len_func = mock.Mock()
        len_func.return_value = 0
        seq = utils.Sequence(
            sp_obj=sp_search,
            add_ref_func=lib_mock.sp_search_add_ref,
            release_func=lib_mock.sp_search_release,
            len_func=len_func,
            getitem_func=None)

        result = len(seq)

        self.assertEqual(result, 0)
        len_func.assert_called_with(sp_search)

    def test_getitem_calls_getitem_func(self, lib_mock):
        sp_search = spotify.ffi.cast('sp_search *', 42)
        getitem_func = mock.Mock()
        getitem_func.return_value = mock.sentinel.item_one
        seq = utils.Sequence(
            sp_obj=sp_search,
            add_ref_func=lib_mock.sp_search_add_ref,
            release_func=lib_mock.sp_search_release,
            len_func=lambda x: 1,
            getitem_func=getitem_func)

        result = seq[0]

        self.assertEqual(result, mock.sentinel.item_one)
        getitem_func.assert_called_with(sp_search, 0)

    def test_getitem_with_negative_index(self, lib_mock):
        sp_search = spotify.ffi.cast('sp_search *', 42)
        getitem_func = mock.Mock()
        getitem_func.return_value = mock.sentinel.item_one
        seq = utils.Sequence(
            sp_obj=sp_search,
            add_ref_func=lib_mock.sp_search_add_ref,
            release_func=lib_mock.sp_search_release,
            len_func=lambda x: 1,
            getitem_func=getitem_func)

        result = seq[-1]

        self.assertEqual(result, mock.sentinel.item_one)
        getitem_func.assert_called_with(sp_search, 0)

    def test_getitem_with_slice(self, lib_mock):
        sp_search = spotify.ffi.cast('sp_search *', 42)
        getitem_func = mock.Mock()
        getitem_func.side_effect = [
            mock.sentinel.item_one,
            mock.sentinel.item_two,
            mock.sentinel.item_three,
        ]
        seq = utils.Sequence(
            sp_obj=sp_search,
            add_ref_func=lib_mock.sp_search_add_ref,
            release_func=lib_mock.sp_search_release,
            len_func=lambda x: 3,
            getitem_func=getitem_func)

        result = seq[0:2]

        # Entire collection of length 3 is created as a list
        self.assertEqual(getitem_func.call_count, 3)

        # Only a subslice of length 2 is returned
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], mock.sentinel.item_one)
        self.assertEqual(result[1], mock.sentinel.item_two)

    def test_getitem_raises_index_error_on_too_low_index(self, lib_mock):
        sp_search = spotify.ffi.cast('sp_search *', 42)
        seq = utils.Sequence(
            sp_obj=sp_search,
            add_ref_func=lib_mock.sp_search_add_ref,
            release_func=lib_mock.sp_search_release,
            len_func=lambda x: 1,
            getitem_func=None)

        with self.assertRaises(IndexError):
            seq[-3]

    def test_getitem_raises_index_error_on_too_high_index(self, lib_mock):
        sp_search = spotify.ffi.cast('sp_search *', 42)
        seq = utils.Sequence(
            sp_obj=sp_search,
            add_ref_func=lib_mock.sp_search_add_ref,
            release_func=lib_mock.sp_search_release,
            len_func=lambda x: 1,
            getitem_func=None)

        with self.assertRaises(IndexError):
            seq[1]

    def test_getitem_raises_type_error_on_non_integral_index(self, lib_mock):
        sp_search = spotify.ffi.cast('sp_search *', 42)
        seq = utils.Sequence(
            sp_obj=sp_search,
            add_ref_func=lib_mock.sp_search_add_ref,
            release_func=lib_mock.sp_search_release,
            len_func=lambda x: 1,
            getitem_func=None)

        with self.assertRaises(TypeError):
            seq['abc']

    def test_repr(self, lib_mock):
        sp_search = spotify.ffi.cast('sp_search *', 42)
        seq = utils.Sequence(
            sp_obj=sp_search,
            add_ref_func=lib_mock.sp_search_add_ref,
            release_func=lib_mock.sp_search_release,
            len_func=lambda x: 1,
            getitem_func=lambda s, i: 123)

        result = repr(seq)

        self.assertEqual(result, 'Sequence([123])')


class ToBytesTest(unittest.TestCase):

    def test_unicode_to_bytes_is_encoded_as_utf8(self):
        self.assertEqual(utils.to_bytes('æøå'), 'æøå'.encode('utf-8'))

    def test_bytes_to_bytes_is_passed_through(self):
        self.assertEqual(
            utils.to_bytes('æøå'.encode('utf-8')), 'æøå'.encode('utf-8'))

    def test_cdata_to_bytes_is_unwrapped(self):
        cdata = spotify.ffi.new('char[]', 'æøå'.encode('utf-8'))
        self.assertEqual(utils.to_bytes(cdata), 'æøå'.encode('utf-8'))

    def test_anything_else_to_bytes_fails(self):
        with self.assertRaises(ValueError):
            utils.to_bytes([])

        with self.assertRaises(ValueError):
            utils.to_bytes(123)


class ToBytesOrNoneTest(unittest.TestCase):

    def test_null_becomes_none(self):
        self.assertEqual(utils.to_bytes_or_none(spotify.ffi.NULL), None)

    def test_char_becomes_bytes(self):
        result = utils.to_bytes_or_none(spotify.ffi.new('char[]', b'abc'))

        self.assertEqual(result, b'abc')

    def test_anything_else_fails(self):
        with self.assertRaises(ValueError):
            utils.to_bytes_or_none(b'abc')


class ToUnicodeTest(unittest.TestCase):

    def test_unicode_to_unicode_is_passed_through(self):
        self.assertEqual(utils.to_unicode('æøå'), 'æøå')

    def test_bytes_to_unicode_is_decoded_as_utf8(self):
        self.assertEqual(utils.to_unicode('æøå'.encode('utf-8')), 'æøå')

    def test_cdata_to_unicode_is_unwrapped_and_decoded_as_utf8(self):
        cdata = spotify.ffi.new('char[]', 'æøå'.encode('utf-8'))
        self.assertEqual(utils.to_unicode(cdata), 'æøå')

    def test_anything_else_to_unicode_fails(self):
        with self.assertRaises(ValueError):
            utils.to_unicode([])

        with self.assertRaises(ValueError):
            utils.to_unicode(123)


class ToUnicodeOrNoneTest(unittest.TestCase):

    def test_null_becomes_none(self):
        self.assertEqual(utils.to_unicode_or_none(spotify.ffi.NULL), None)

    def test_char_becomes_bytes(self):
        result = utils.to_unicode_or_none(
            spotify.ffi.new('char[]', 'æøå'.encode('utf-8')))

        self.assertEqual(result, 'æøå')

    def test_anything_else_fails(self):
        with self.assertRaises(ValueError):
            utils.to_unicode_or_none('æøå')


class ToCharTest(unittest.TestCase):

    def test_bytes_becomes_char(self):
        result = utils.to_char(b'abc')

        self.assertIsInstance(result, spotify.ffi.CData)
        self.assertEqual(spotify.ffi.string(result), b'abc')

    def test_unicode_becomes_char(self):
        result = utils.to_char('æøå')

        self.assertIsInstance(result, spotify.ffi.CData)
        self.assertEqual(spotify.ffi.string(result).decode('utf-8'), 'æøå')

    def test_anything_else_fails(self):
        with self.assertRaises(ValueError):
            utils.to_char(None)

        with self.assertRaises(ValueError):
            utils.to_char(123)


class ToCharOrNullTest(unittest.TestCase):

    def test_none_becomes_null(self):
        self.assertEqual(utils.to_char_or_null(None), spotify.ffi.NULL)

    def test_bytes_becomes_char(self):
        result = utils.to_char_or_null(b'abc')

        self.assertIsInstance(result, spotify.ffi.CData)
        self.assertEqual(spotify.ffi.string(result), b'abc')

    def test_unicode_becomes_char(self):
        result = utils.to_char_or_null('æøå')

        self.assertIsInstance(result, spotify.ffi.CData)
        self.assertEqual(spotify.ffi.string(result).decode('utf-8'), 'æøå')

    def test_anything_else_fails(self):
        with self.assertRaises(ValueError):
            utils.to_char_or_null(123)


class ToCountryCodeTest(unittest.TestCase):

    def test_unicode_to_country_code(self):
        self.assertEqual(utils.to_country_code('NO'), 20047)
        self.assertEqual(utils.to_country_code('SE'), 21317)

    def test_bytes_to_country_code(self):
        self.assertEqual(utils.to_country_code(b'NO'), 20047)
        self.assertEqual(utils.to_country_code(b'SE'), 21317)

    def test_fails_if_not_exactly_two_chars(self):
        with self.assertRaises(ValueError):
            utils.to_country_code('NOR')

    def test_fails_if_not_in_uppercase(self):
        with self.assertRaises(ValueError):
            utils.to_country_code('no')


class ToCountryTest(unittest.TestCase):

    def test_to_country(self):
        self.assertEqual(utils.to_country(20047), 'NO')
        self.assertEqual(utils.to_country(21317), 'SE')

########NEW FILE########
__FILENAME__ = test_version
# encoding: utf-8

from __future__ import unicode_literals

from distutils.version import StrictVersion as SV
import unittest

import spotify

from tests import mock


class VersionTest(unittest.TestCase):

    def test_version_is_a_valid_pep_386_strict_version(self):
        SV(spotify.__version__)

    def test_version_is_grater_than_all_1_x_versions(self):
        self.assertLess(SV('1.999'), SV(spotify.__version__))


@mock.patch('spotify.version.lib', spec=spotify.lib)
class LibspotifyVersionTest(unittest.TestCase):

    def test_libspotify_api_version(self, lib_mock):
        lib_mock.SPOTIFY_API_VERSION = 73

        result = spotify.get_libspotify_api_version()

        self.assertEqual(result, 73)

    def test_libspotify_build_id(self, lib_mock):
        build_id = spotify.ffi.new(
            'char []', '12.1.51.foobaræøå'.encode('utf-8'))
        lib_mock.sp_build_id.return_value = build_id

        result = spotify.get_libspotify_build_id()

        self.assertEqual(result, '12.1.51.foobaræøå')

########NEW FILE########
