__FILENAME__ = conf
# encoding: utf-8

"""Mopidy documentation build configuration file"""

from __future__ import unicode_literals

import os
import sys


# -- Workarounds to have autodoc generate API docs ----------------------------

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/../'))


class Mock(object):
    def __init__(self, *args, **kwargs):
        pass

    def __call__(self, *args, **kwargs):
        return Mock()

    def __or__(self, other):
        return Mock()

    @classmethod
    def __getattr__(self, name):
        if name in ('__file__', '__path__'):
            return '/dev/null'
        elif name == 'get_system_config_dirs':
            # glib.get_system_config_dirs()
            return tuple
        elif name == 'get_user_config_dir':
            # glib.get_user_config_dir()
            return str
        elif (name[0] == name[0].upper()
                # gst.interfaces.MIXER_TRACK_*
                and not name.startswith('MIXER_TRACK_')
                # gst.PadTemplate
                and not name.startswith('PadTemplate')
                # dbus.String()
                and not name == 'String'):
            return type(name, (), {})
        else:
            return Mock()

MOCK_MODULES = [
    'cherrypy',
    'dbus',
    'dbus.mainloop',
    'dbus.mainloop.glib',
    'dbus.service',
    'glib',
    'gobject',
    'gst',
    'pygst',
    'pykka',
    'pykka.actor',
    'pykka.future',
    'pykka.registry',
    'pylast',
    'ws4py',
    'ws4py.messaging',
    'ws4py.server',
    'ws4py.server.cherrypyserver',
    'ws4py.websocket',
]
for mod_name in MOCK_MODULES:
    sys.modules[mod_name] = Mock()


# -- Custom Sphinx object types -----------------------------------------------

def setup(app):
    from sphinx.ext.autodoc import cut_lines
    app.connect(b'autodoc-process-docstring', cut_lines(4, what=['module']))
    app.add_object_type(
        b'confval', 'confval',
        objname='configuration value',
        indextemplate='pair: %s; configuration value')


# -- General configuration ----------------------------------------------------

needs_sphinx = '1.0'

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.extlinks',
    'sphinx.ext.graphviz',
    'sphinx.ext.intersphinx',
    'sphinx.ext.viewcode',
]

templates_path = ['_templates']
source_suffix = '.rst'
master_doc = 'index'

project = 'Mopidy'
copyright = '2009-2014, Stein Magnus Jodal and contributors'

from mopidy.utils.versioning import get_version
release = get_version()
version = '.'.join(release.split('.')[:2])

exclude_trees = ['_build']

pygments_style = 'sphinx'

modindex_common_prefix = ['mopidy.']


# -- Options for HTML output --------------------------------------------------

html_theme = 'default'
html_theme_path = ['_themes']
html_static_path = ['_static']

html_use_modindex = True
html_use_index = True
html_split_index = False
html_show_sourcelink = True

htmlhelp_basename = 'Mopidy'


# -- Options for LaTeX output -------------------------------------------------

latex_documents = [
    (
        'index',
        'Mopidy.tex',
        'Mopidy Documentation',
        'Stein Magnus Jodal and contributors',
        'manual'
    ),
]


# -- Options for manpages output ----------------------------------------------

man_pages = [
    (
        'commands/mopidy',
        'mopidy',
        'music server',
        '',
        '1'
    ),
]


# -- Options for extlink extension --------------------------------------------

extlinks = {
    'issue': ('https://github.com/mopidy/mopidy/issues/%s', '#'),
    'commit': ('https://github.com/mopidy/mopidy/commit/%s', 'commit '),
    'mpris': (
        'https://github.com/mopidy/mopidy-mpris/issues/%s', 'mopidy-mpris#'),
}


# -- Options for intersphinx extension ----------------------------------------

intersphinx_mapping = {
    'python': ('http://docs.python.org/2', None),
    'pykka': ('http://www.pykka.org/en/latest/', None),
    'tornado': ('http://www.tornadoweb.org/en/stable/', None),
}

########NEW FILE########
__FILENAME__ = fabfile
from fabric.api import execute, local, settings, task


@task
def docs():
    local('make -C docs/ html')


@task
def autodocs():
    auto(docs)


@task
def test(path=None):
    path = path or 'tests/'
    local('nosetests ' + path)


@task
def autotest(path=None):
    auto(test, path=path)


@task
def coverage(path=None):
    path = path or 'tests/'
    local(
        'nosetests --with-coverage --cover-package=mopidy '
        '--cover-branches --cover-html ' + path)


@task
def autocoverage(path=None):
    auto(coverage, path=path)


@task
def lint(path=None):
    path = path or '.'
    local('flake8 $(find %s -iname "*.py")' % path)


@task
def autolint(path=None):
    auto(lint, path=path)


def auto(task, *args, **kwargs):
    while True:
        local('clear')
        with settings(warn_only=True):
            execute(task, *args, **kwargs)
        local(
            'inotifywait -q -e create -e modify -e delete '
            '--exclude ".*\.(pyc|sw.)" -r docs/ mopidy/ tests/')


@task
def update_authors():
    # Keep authors in the order of appearance and use awk to filter out dupes
    local(
        "git log --format='- %aN <%aE>' --reverse | awk '!x[$0]++' > AUTHORS")

########NEW FILE########
__FILENAME__ = actor
from __future__ import unicode_literals

import logging

import gobject

import pygst
pygst.require('0.10')
import gst  # noqa

import pykka

from mopidy.audio import mixers, playlists, utils
from mopidy.audio.constants import PlaybackState
from mopidy.audio.listener import AudioListener
from mopidy.utils import process


logger = logging.getLogger(__name__)

mixers.register_mixers()

playlists.register_typefinders()
playlists.register_elements()


MB = 1 << 20

# GST_PLAY_FLAG_VIDEO (1<<0)
# GST_PLAY_FLAG_AUDIO (1<<1)
# GST_PLAY_FLAG_TEXT (1<<2)
# GST_PLAY_FLAG_VIS (1<<3)
# GST_PLAY_FLAG_SOFT_VOLUME (1<<4)
# GST_PLAY_FLAG_NATIVE_AUDIO (1<<5)
# GST_PLAY_FLAG_NATIVE_VIDEO (1<<6)
# GST_PLAY_FLAG_DOWNLOAD (1<<7)
# GST_PLAY_FLAG_BUFFERING (1<<8)
# GST_PLAY_FLAG_DEINTERLACE (1<<9)
# GST_PLAY_FLAG_SOFT_COLORBALANCE (1<<10)

# Default flags to use for playbin: AUDIO, SOFT_VOLUME, DOWNLOAD
PLAYBIN_FLAGS = (1 << 1) | (1 << 4) | (1 << 7)
PLAYBIN_VIS_FLAGS = PLAYBIN_FLAGS | (1 << 3)


class Audio(pykka.ThreadingActor):
    """
    Audio output through `GStreamer <http://gstreamer.freedesktop.org/>`_.
    """

    #: The GStreamer state mapped to :class:`mopidy.audio.PlaybackState`
    state = PlaybackState.STOPPED
    _target_state = gst.STATE_NULL

    def __init__(self, config):
        super(Audio, self).__init__()

        self._config = config

        self._playbin = None
        self._signal_ids = {}  # {(element, event): signal_id}

        self._mixer = None
        self._mixer_track = None
        self._mixer_scale = None
        self._software_mixing = False
        self._volume_set = None

        self._appsrc = None
        self._appsrc_caps = None
        self._appsrc_need_data_callback = None
        self._appsrc_enough_data_callback = None
        self._appsrc_seek_data_callback = None

    def on_start(self):
        try:
            self._setup_playbin()
            self._setup_output()
            self._setup_visualizer()
            self._setup_mixer()
            self._setup_message_processor()
        except gobject.GError as ex:
            logger.exception(ex)
            process.exit_process()

    def on_stop(self):
        self._teardown_message_processor()
        self._teardown_mixer()
        self._teardown_playbin()

    def _connect(self, element, event, *args):
        """Helper to keep track of signal ids based on element+event"""
        self._signal_ids[(element, event)] = element.connect(event, *args)

    def _disconnect(self, element, event):
        """Helper to disconnect signals created with _connect helper."""
        signal_id = self._signal_ids.pop((element, event), None)
        if signal_id is not None:
            element.disconnect(signal_id)

    def _setup_playbin(self):
        playbin = gst.element_factory_make('playbin2')
        playbin.set_property('flags', PLAYBIN_FLAGS)

        playbin.set_property('buffer-size', 2*1024*1024)
        playbin.set_property('buffer-duration', 2*gst.SECOND)

        self._connect(playbin, 'about-to-finish', self._on_about_to_finish)
        self._connect(playbin, 'notify::source', self._on_new_source)
        self._connect(playbin, 'source-setup', self._on_source_setup)

        self._playbin = playbin

    def _on_about_to_finish(self, element):
        source, self._appsrc = self._appsrc, None
        if source is None:
            return
        self._appsrc_caps = None

        self._disconnect(source, 'need-data')
        self._disconnect(source, 'enough-data')
        self._disconnect(source, 'seek-data')

    def _on_new_source(self, element, pad):
        uri = element.get_property('uri')
        if not uri or not uri.startswith('appsrc://'):
            return

        source = element.get_property('source')
        source.set_property('caps', self._appsrc_caps)
        source.set_property('format', b'time')
        source.set_property('stream-type', b'seekable')
        source.set_property('max-bytes', 1 * MB)
        source.set_property('min-percent', 50)

        self._connect(source, 'need-data', self._appsrc_on_need_data)
        self._connect(source, 'enough-data', self._appsrc_on_enough_data)
        self._connect(source, 'seek-data', self._appsrc_on_seek_data)

        self._appsrc = source

    def _on_source_setup(self, element, source):
        scheme = 'http'
        hostname = self._config['proxy']['hostname']
        port = 80

        if hasattr(source.props, 'proxy') and hostname:
            if self._config['proxy']['port']:
                port = self._config['proxy']['port']
            if self._config['proxy']['scheme']:
                scheme = self._config['proxy']['scheme']

            proxy = "%s://%s:%d" % (scheme, hostname, port)
            source.set_property('proxy', proxy)
            source.set_property('proxy-id', self._config['proxy']['username'])
            source.set_property('proxy-pw', self._config['proxy']['password'])

    def _appsrc_on_need_data(self, appsrc, gst_length_hint):
        length_hint = utils.clocktime_to_millisecond(gst_length_hint)
        if self._appsrc_need_data_callback is not None:
            self._appsrc_need_data_callback(length_hint)
        return True

    def _appsrc_on_enough_data(self, appsrc):
        if self._appsrc_enough_data_callback is not None:
            self._appsrc_enough_data_callback()
        return True

    def _appsrc_on_seek_data(self, appsrc, gst_position):
        position = utils.clocktime_to_millisecond(gst_position)
        if self._appsrc_seek_data_callback is not None:
            self._appsrc_seek_data_callback(position)
        return True

    def _teardown_playbin(self):
        self._disconnect(self._playbin, 'about-to-finish')
        self._disconnect(self._playbin, 'notify::source')
        self._disconnect(self._playbin, 'source-setup')
        self._playbin.set_state(gst.STATE_NULL)

    def _setup_output(self):
        output_desc = self._config['audio']['output']
        try:
            output = gst.parse_bin_from_description(
                output_desc, ghost_unconnected_pads=True)
            self._playbin.set_property('audio-sink', output)
            logger.info('Audio output set to "%s"', output_desc)
        except gobject.GError as ex:
            logger.error(
                'Failed to create audio output "%s": %s', output_desc, ex)
            process.exit_process()

    def _setup_visualizer(self):
        visualizer_element = self._config['audio']['visualizer']
        if not visualizer_element:
            return
        try:
            visualizer = gst.element_factory_make(visualizer_element)
            self._playbin.set_property('vis-plugin', visualizer)
            self._playbin.set_property('flags', PLAYBIN_VIS_FLAGS)
            logger.info('Audio visualizer set to "%s"', visualizer_element)
        except gobject.GError as ex:
            logger.error(
                'Failed to create audio visualizer "%s": %s',
                visualizer_element, ex)

    def _setup_mixer(self):
        mixer_desc = self._config['audio']['mixer']
        track_desc = self._config['audio']['mixer_track']
        volume = self._config['audio']['mixer_volume']

        if mixer_desc is None:
            logger.info('Not setting up audio mixer')
            return

        if mixer_desc == 'software':
            self._software_mixing = True
            logger.info('Audio mixer is using software mixing')
            if volume is not None:
                self.set_volume(volume)
                logger.info('Audio mixer volume set to %d', volume)
            return

        try:
            mixerbin = gst.parse_bin_from_description(
                mixer_desc, ghost_unconnected_pads=False)
        except gobject.GError as ex:
            logger.warning(
                'Failed to create audio mixer "%s": %s', mixer_desc, ex)
            return

        # We assume that the bin will contain a single mixer.
        mixer = mixerbin.get_by_interface(b'GstMixer')
        if not mixer:
            logger.warning(
                'Did not find any audio mixers in "%s"', mixer_desc)
            return

        if mixerbin.set_state(gst.STATE_READY) != gst.STATE_CHANGE_SUCCESS:
            logger.warning(
                'Setting audio mixer "%s" to READY failed', mixer_desc)
            return

        track = self._select_mixer_track(mixer, track_desc)
        if not track:
            logger.warning('Could not find usable audio mixer track')
            return

        self._mixer = mixer
        self._mixer_track = track
        self._mixer_scale = (
            self._mixer_track.min_volume, self._mixer_track.max_volume)

        logger.info(
            'Audio mixer set to "%s" using track "%s"',
            str(mixer.get_factory().get_name()).decode('utf-8'),
            str(track.label).decode('utf-8'))

        if volume is not None:
            self.set_volume(volume)
            logger.info('Audio mixer volume set to %d', volume)

    def _select_mixer_track(self, mixer, track_label):
        # Ignore tracks without volumes, then look for track with
        # label equal to the audio/mixer_track config value, otherwise fallback
        # to first usable track hoping the mixer gave them to us in a sensible
        # order.

        usable_tracks = []
        for track in mixer.list_tracks():
            if not mixer.get_volume(track):
                continue

            if track_label and track.label == track_label:
                return track
            elif track.flags & (gst.interfaces.MIXER_TRACK_MASTER |
                                gst.interfaces.MIXER_TRACK_OUTPUT):
                usable_tracks.append(track)

        if usable_tracks:
            return usable_tracks[0]

    def _teardown_mixer(self):
        if self._mixer is not None:
            self._mixer.set_state(gst.STATE_NULL)

    def _setup_message_processor(self):
        bus = self._playbin.get_bus()
        bus.add_signal_watch()
        self._connect(bus, 'message', self._on_message)

    def _teardown_message_processor(self):
        bus = self._playbin.get_bus()
        self._disconnect(bus, 'message')
        bus.remove_signal_watch()

    def _on_message(self, bus, message):
        if (message.type == gst.MESSAGE_STATE_CHANGED
                and message.src == self._playbin):
            old_state, new_state, pending_state = message.parse_state_changed()
            self._on_playbin_state_changed(old_state, new_state, pending_state)
        elif message.type == gst.MESSAGE_BUFFERING:
            percent = message.parse_buffering()
            if percent < 10:
                self._playbin.set_state(gst.STATE_PAUSED)
            if percent == 100 and self._target_state == gst.STATE_PLAYING:
                self._playbin.set_state(gst.STATE_PLAYING)
            logger.debug('Buffer %d%% full', percent)
        elif message.type == gst.MESSAGE_EOS:
            self._on_end_of_stream()
        elif message.type == gst.MESSAGE_ERROR:
            error, debug = message.parse_error()
            logger.error(
                '%s Debug message: %s',
                str(error).decode('utf-8'), debug.decode('utf-8') or 'None')
            self.stop_playback()
        elif message.type == gst.MESSAGE_WARNING:
            error, debug = message.parse_warning()
            logger.warning(
                '%s Debug message: %s',
                str(error).decode('utf-8'), debug.decode('utf-8') or 'None')

    def _on_playbin_state_changed(self, old_state, new_state, pending_state):
        if new_state == gst.STATE_READY and pending_state == gst.STATE_NULL:
            # XXX: We're not called on the last state change when going down to
            # NULL, so we rewrite the second to last call to get the expected
            # behavior.
            new_state = gst.STATE_NULL
            pending_state = gst.STATE_VOID_PENDING

        if pending_state != gst.STATE_VOID_PENDING:
            return  # Ignore intermediate state changes

        if new_state == gst.STATE_READY:
            return  # Ignore READY state as it's GStreamer specific

        if new_state == gst.STATE_PLAYING:
            new_state = PlaybackState.PLAYING
        elif new_state == gst.STATE_PAUSED:
            new_state = PlaybackState.PAUSED
        elif new_state == gst.STATE_NULL:
            new_state = PlaybackState.STOPPED

        old_state, self.state = self.state, new_state

        logger.debug(
            'Triggering event: state_changed(old_state=%s, new_state=%s)',
            old_state, new_state)
        AudioListener.send(
            'state_changed', old_state=old_state, new_state=new_state)

    def _on_end_of_stream(self):
        logger.debug('Triggering reached_end_of_stream event')
        AudioListener.send('reached_end_of_stream')

    def set_uri(self, uri):
        """
        Set URI of audio to be played.

        You *MUST* call :meth:`prepare_change` before calling this method.

        :param uri: the URI to play
        :type uri: string
        """
        self._playbin.set_property('uri', uri)

    def set_appsrc(
            self, caps, need_data=None, enough_data=None, seek_data=None):
        """
        Switch to using appsrc for getting audio to be played.

        You *MUST* call :meth:`prepare_change` before calling this method.

        :param caps: GStreamer caps string describing the audio format to
            expect
        :type caps: string
        :param need_data: callback for when appsrc needs data
        :type need_data: callable which takes data length hint in ms
        :param enough_data: callback for when appsrc has enough data
        :type enough_data: callable
        :param seek_data: callback for when data from a new position is needed
            to continue playback
        :type seek_data: callable which takes time position in ms
        """
        if isinstance(caps, unicode):
            caps = caps.encode('utf-8')
        self._appsrc_caps = gst.Caps(caps)
        self._appsrc_need_data_callback = need_data
        self._appsrc_enough_data_callback = enough_data
        self._appsrc_seek_data_callback = seek_data
        self._playbin.set_property('uri', 'appsrc://')

    def emit_data(self, buffer_):
        """
        Call this to deliver raw audio data to be played.

        Note that the uri must be set to ``appsrc://`` for this to work.

        Returns true if data was delivered.

        :param buffer_: buffer to pass to appsrc
        :type buffer_: :class:`gst.Buffer`
        :rtype: boolean
        """
        if not self._appsrc:
            return False
        return self._appsrc.emit('push-buffer', buffer_) == gst.FLOW_OK

    def emit_end_of_stream(self):
        """
        Put an end-of-stream token on the playbin. This is typically used in
        combination with :meth:`emit_data`.

        We will get a GStreamer message when the stream playback reaches the
        token, and can then do any end-of-stream related tasks.
        """
        self._playbin.get_property('source').emit('end-of-stream')

    def get_position(self):
        """
        Get position in milliseconds.

        :rtype: int
        """
        try:
            gst_position = self._playbin.query_position(gst.FORMAT_TIME)[0]
            return utils.clocktime_to_millisecond(gst_position)
        except gst.QueryError:
            logger.debug('Position query failed')
            return 0

    def set_position(self, position):
        """
        Set position in milliseconds.

        :param position: the position in milliseconds
        :type position: int
        :rtype: :class:`True` if successful, else :class:`False`
        """
        gst_position = utils.millisecond_to_clocktime(position)
        return self._playbin.seek_simple(
            gst.Format(gst.FORMAT_TIME), gst.SEEK_FLAG_FLUSH, gst_position)

    def start_playback(self):
        """
        Notify GStreamer that it should start playback.

        :rtype: :class:`True` if successfull, else :class:`False`
        """
        return self._set_state(gst.STATE_PLAYING)

    def pause_playback(self):
        """
        Notify GStreamer that it should pause playback.

        :rtype: :class:`True` if successfull, else :class:`False`
        """
        return self._set_state(gst.STATE_PAUSED)

    def prepare_change(self):
        """
        Notify GStreamer that we are about to change state of playback.

        This function *MUST* be called before changing URIs or doing
        changes like updating data that is being pushed. The reason for this
        is that GStreamer will reset all its state when it changes to
        :attr:`gst.STATE_READY`.
        """
        return self._set_state(gst.STATE_READY)

    def stop_playback(self):
        """
        Notify GStreamer that is should stop playback.

        :rtype: :class:`True` if successfull, else :class:`False`
        """
        return self._set_state(gst.STATE_NULL)

    def _set_state(self, state):
        """
        Internal method for setting the raw GStreamer state.

        .. digraph:: gst_state_transitions

            graph [rankdir="LR"];
            node [fontsize=10];

            "NULL" -> "READY"
            "PAUSED" -> "PLAYING"
            "PAUSED" -> "READY"
            "PLAYING" -> "PAUSED"
            "READY" -> "NULL"
            "READY" -> "PAUSED"

        :param state: State to set playbin to. One of: `gst.STATE_NULL`,
            `gst.STATE_READY`, `gst.STATE_PAUSED` and `gst.STATE_PLAYING`.
        :type state: :class:`gst.State`
        :rtype: :class:`True` if successfull, else :class:`False`
        """
        self._target_state = state
        result = self._playbin.set_state(state)
        if result == gst.STATE_CHANGE_FAILURE:
            logger.warning(
                'Setting GStreamer state to %s failed', state.value_name)
            return False
        elif result == gst.STATE_CHANGE_ASYNC:
            logger.debug(
                'Setting GStreamer state to %s is async', state.value_name)
            return True
        else:
            logger.debug(
                'Setting GStreamer state to %s is OK', state.value_name)
            return True

    def get_volume(self):
        """
        Get volume level of the installed mixer.

        Example values:

        0:
            Muted.
        100:
            Max volume for given system.
        :class:`None`:
            No mixer present, so the volume is unknown.

        :rtype: int in range [0..100] or :class:`None`
        """
        if self._software_mixing:
            return int(round(self._playbin.get_property('volume') * 100))

        if self._mixer is None:
            return None

        volumes = self._mixer.get_volume(self._mixer_track)
        avg_volume = float(sum(volumes)) / len(volumes)

        internal_scale = (0, 100)

        if self._volume_set is not None:
            volume_set_on_mixer_scale = self._rescale(
                self._volume_set, old=internal_scale, new=self._mixer_scale)
        else:
            volume_set_on_mixer_scale = None

        if volume_set_on_mixer_scale == avg_volume:
            return self._volume_set
        else:
            return self._rescale(
                avg_volume, old=self._mixer_scale, new=internal_scale)

    def set_volume(self, volume):
        """
        Set volume level of the installed mixer.

        :param volume: the volume in the range [0..100]
        :type volume: int
        :rtype: :class:`True` if successful, else :class:`False`
        """
        if self._software_mixing:
            self._playbin.set_property('volume', volume / 100.0)
            return True

        if self._mixer is None:
            return False

        self._volume_set = volume

        internal_scale = (0, 100)

        volume = self._rescale(
            volume, old=internal_scale, new=self._mixer_scale)

        volumes = (volume,) * self._mixer_track.num_channels
        self._mixer.set_volume(self._mixer_track, volumes)

        return self._mixer.get_volume(self._mixer_track) == volumes

    def _rescale(self, value, old=None, new=None):
        """Convert value between scales."""
        new_min, new_max = new
        old_min, old_max = old
        if old_min == old_max:
            return old_max
        scaling = float(new_max - new_min) / (old_max - old_min)
        return int(round(scaling * (value - old_min) + new_min))

    def get_mute(self):
        """
        Get mute status of the installed mixer.

        :rtype: :class:`True` if muted, :class:`False` if unmuted,
          :class:`None` if no mixer is installed.
        """
        if self._software_mixing:
            return self._playbin.get_property('mute')

        if self._mixer_track is None:
            return None

        return bool(self._mixer_track.flags & gst.interfaces.MIXER_TRACK_MUTE)

    def set_mute(self, mute):
        """
        Mute or unmute of the installed mixer.

        :param mute: Wether to mute the mixer or not.
        :type mute: bool
        :rtype: :class:`True` if successful, else :class:`False`
        """
        if self._software_mixing:
            return self._playbin.set_property('mute', bool(mute))

        if self._mixer_track is None:
            return False

        return self._mixer.set_mute(self._mixer_track, bool(mute))

    def set_metadata(self, track):
        """
        Set track metadata for currently playing song.

        Only needs to be called by sources such as `appsrc` which do not
        already inject tags in playbin, e.g. when using :meth:`emit_data` to
        deliver raw audio data to GStreamer.

        :param track: the current track
        :type track: :class:`mopidy.models.Track`
        """
        taglist = gst.TagList()
        artists = [a for a in (track.artists or []) if a.name]

        # Default to blank data to trick shoutcast into clearing any previous
        # values it might have.
        taglist[gst.TAG_ARTIST] = ' '
        taglist[gst.TAG_TITLE] = ' '
        taglist[gst.TAG_ALBUM] = ' '

        if artists:
            taglist[gst.TAG_ARTIST] = ', '.join([a.name for a in artists])

        if track.name:
            taglist[gst.TAG_TITLE] = track.name

        if track.album and track.album.name:
            taglist[gst.TAG_ALBUM] = track.album.name

        event = gst.event_new_tag(taglist)
        self._playbin.send_event(event)

########NEW FILE########
__FILENAME__ = constants
from __future__ import unicode_literals


class PlaybackState(object):
    """
    Enum of playback states.
    """

    #: Constant representing the paused state.
    PAUSED = 'paused'

    #: Constant representing the playing state.
    PLAYING = 'playing'

    #: Constant representing the stopped state.
    STOPPED = 'stopped'

########NEW FILE########
__FILENAME__ = dummy
"""A dummy audio actor for use in tests.

This class implements the audio API in the simplest way possible. It is used in
tests of the core and backends.
"""

from __future__ import unicode_literals

import pykka

from .constants import PlaybackState
from .listener import AudioListener


class DummyAudio(pykka.ThreadingActor):
    def __init__(self):
        super(DummyAudio, self).__init__()
        self.state = PlaybackState.STOPPED
        self._position = 0

    def set_on_end_of_track(self, callback):
        pass

    def set_uri(self, uri):
        pass

    def set_appsrc(self, *args, **kwargs):
        pass

    def emit_data(self, buffer_):
        pass

    def emit_end_of_stream(self):
        pass

    def get_position(self):
        return self._position

    def set_position(self, position):
        self._position = position
        return True

    def start_playback(self):
        return self._change_state(PlaybackState.PLAYING)

    def pause_playback(self):
        return self._change_state(PlaybackState.PAUSED)

    def prepare_change(self):
        return True

    def stop_playback(self):
        return self._change_state(PlaybackState.STOPPED)

    def get_volume(self):
        return 0

    def set_volume(self, volume):
        pass

    def set_metadata(self, track):
        pass

    def _change_state(self, new_state):
        old_state, self.state = self.state, new_state
        AudioListener.send(
            'state_changed', old_state=old_state, new_state=new_state)
        return True

########NEW FILE########
__FILENAME__ = listener
from __future__ import unicode_literals

from mopidy import listener


class AudioListener(listener.Listener):
    """
    Marker interface for recipients of events sent by the audio actor.

    Any Pykka actor that mixes in this class will receive calls to the methods
    defined here when the corresponding events happen in the core actor. This
    interface is used both for looking up what actors to notify of the events,
    and for providing default implementations for those listeners that are not
    interested in all events.
    """

    @staticmethod
    def send(event, **kwargs):
        """Helper to allow calling of audio listener events"""
        listener.send_async(AudioListener, event, **kwargs)

    def reached_end_of_stream(self):
        """
        Called whenever the end of the audio stream is reached.

        *MAY* be implemented by actor.
        """
        pass

    def state_changed(self, old_state, new_state):
        """
        Called after the playback state have changed.

        Will be called for both immediate and async state changes in GStreamer.

        *MAY* be implemented by actor.

        :param old_state: the state before the change
        :type old_state: string from :class:`mopidy.core.PlaybackState` field
        :param new_state: the state after the change
        :type new_state: string from :class:`mopidy.core.PlaybackState` field
        """
        pass

########NEW FILE########
__FILENAME__ = auto
"""Mixer element that automatically selects the real mixer to use.

Set the :confval:`audio/mixer` config value to ``autoaudiomixer`` to use this
mixer.
"""

from __future__ import unicode_literals

import logging

import pygst
pygst.require('0.10')
import gst  # noqa


logger = logging.getLogger(__name__)


# TODO: we might want to add some ranking to the mixers we know about?
class AutoAudioMixer(gst.Bin):
    __gstdetails__ = (
        'AutoAudioMixer',
        'Mixer',
        'Element automatically selects a mixer.',
        'Mopidy')

    def __init__(self):
        gst.Bin.__init__(self)
        mixer = self._find_mixer()
        if mixer:
            self.add(mixer)
            logger.debug('AutoAudioMixer chose: %s', mixer.get_name())
        else:
            logger.debug('AutoAudioMixer did not find any usable mixers')

    def _find_mixer(self):
        registry = gst.registry_get_default()

        factories = registry.get_feature_list(gst.TYPE_ELEMENT_FACTORY)
        factories.sort(key=lambda f: (-f.get_rank(), f.get_name()))

        for factory in factories:
            # Avoid sink/srcs that implement mixing.
            if factory.get_klass() != 'Generic/Audio':
                continue
            # Avoid anything that doesn't implement mixing.
            elif not factory.has_interface('GstMixer'):
                continue

            if self._test_mixer(factory):
                return factory.create()

        return None

    def _test_mixer(self, factory):
        element = factory.create()
        if not element:
            return False

        try:
            result = element.set_state(gst.STATE_READY)
            if result != gst.STATE_CHANGE_SUCCESS:
                return False

            # Trust that the default device is sane and just check tracks.
            return self._test_tracks(element)
        finally:
            element.set_state(gst.STATE_NULL)

    def _test_tracks(self, element):
        # Only allow elements that have a least one output track.
        flags = gst.interfaces.MIXER_TRACK_OUTPUT

        for track in element.list_tracks():
            if track.flags & flags:
                return True
        return False

########NEW FILE########
__FILENAME__ = fake
"""Fake mixer for use in tests.

Set the :confval:`audio/mixer:` config value to ``fakemixer`` to use this
mixer.
"""

from __future__ import unicode_literals

import gobject

import pygst
pygst.require('0.10')
import gst  # noqa

from mopidy.audio.mixers import utils


class FakeMixer(gst.Element, gst.ImplementsInterface, gst.interfaces.Mixer):
    __gstdetails__ = (
        'FakeMixer',
        'Mixer',
        'Fake mixer for use in tests.',
        'Mopidy')

    track_label = gobject.property(type=str, default='Master')
    track_initial_volume = gobject.property(type=int, default=0)
    track_min_volume = gobject.property(type=int, default=0)
    track_max_volume = gobject.property(type=int, default=100)
    track_num_channels = gobject.property(type=int, default=2)
    track_flags = gobject.property(type=int, default=(
        gst.interfaces.MIXER_TRACK_MASTER | gst.interfaces.MIXER_TRACK_OUTPUT))

    def list_tracks(self):
        track = utils.create_track(
            self.track_label,
            self.track_initial_volume,
            self.track_min_volume,
            self.track_max_volume,
            self.track_num_channels,
            self.track_flags)
        return [track]

    def get_volume(self, track):
        return track.volumes

    def set_volume(self, track, volumes):
        track.volumes = volumes

    def set_record(self, track, record):
        pass

########NEW FILE########
__FILENAME__ = utils
from __future__ import unicode_literals

import gobject

import pygst
pygst.require('0.10')
import gst  # noqa


def create_track(label, initial_volume, min_volume, max_volume,
                 num_channels, flags):

    class Track(gst.interfaces.MixerTrack):
        def __init__(self):
            super(Track, self).__init__()
            self.volumes = (initial_volume,) * self.num_channels

        @gobject.property
        def label(self):
            return label

        @gobject.property
        def min_volume(self):
            return min_volume

        @gobject.property
        def max_volume(self):
            return max_volume

        @gobject.property
        def num_channels(self):
            return num_channels

        @gobject.property
        def flags(self):
            return flags

    return Track()

########NEW FILE########
__FILENAME__ = playlists
from __future__ import unicode_literals

import ConfigParser as configparser
import io

import gobject

import pygst
pygst.require('0.10')
import gst  # noqa

try:
    import xml.etree.cElementTree as elementtree
except ImportError:
    import xml.etree.ElementTree as elementtree


# TODO: make detect_FOO_header reusable in general mopidy code.
# i.e. give it just a "peek" like function.
def detect_m3u_header(typefind):
    return typefind.peek(0, 8) == b'#EXTM3U\n'


def detect_pls_header(typefind):
    return typefind.peek(0, 11).lower() == b'[playlist]\n'


def detect_xspf_header(typefind):
    data = typefind.peek(0, 150)
    if b'xspf' not in data:
        return False

    try:
        data = io.BytesIO(data)
        for event, element in elementtree.iterparse(data, events=(b'start',)):
            return element.tag.lower() == '{http://xspf.org/ns/0/}playlist'
    except elementtree.ParseError:
        pass
    return False


def detect_asx_header(typefind):
    data = typefind.peek(0, 50)
    if b'asx' not in data:
        return False

    try:
        data = io.BytesIO(data)
        for event, element in elementtree.iterparse(data, events=(b'start',)):
            return element.tag.lower() == 'asx'
    except elementtree.ParseError:
        pass
    return False


def parse_m3u(data):
    # TODO: convert non URIs to file URIs.
    found_header = False
    for line in data.readlines():
        if found_header or line.startswith('#EXTM3U'):
            found_header = True
        else:
            continue
        if not line.startswith('#') and line.strip():
            yield line.strip()


def parse_pls(data):
    # TODO: convert non URIs to file URIs.
    try:
        cp = configparser.RawConfigParser()
        cp.readfp(data)
    except configparser.Error:
        return

    for section in cp.sections():
        if section.lower() != 'playlist':
            continue
        for i in xrange(cp.getint(section, 'numberofentries')):
            yield cp.get(section, 'file%d' % (i+1))


def parse_xspf(data):
    try:
        for event, element in elementtree.iterparse(data):
            element.tag = element.tag.lower()  # normalize
    except elementtree.ParseError:
        return

    ns = 'http://xspf.org/ns/0/'
    for track in element.iterfind('{%s}tracklist/{%s}track' % (ns, ns)):
        yield track.findtext('{%s}location' % ns)


def parse_asx(data):
    try:
        for event, element in elementtree.iterparse(data):
            element.tag = element.tag.lower()  # normalize
    except elementtree.ParseError:
        return

    for ref in element.findall('entry/ref'):
        yield ref.get('href', '').strip()


def parse_urilist(data):
    for line in data.readlines():
        if not line.startswith('#') and gst.uri_is_valid(line.strip()):
            yield line


def playlist_typefinder(typefind, func, caps):
    if func(typefind):
        typefind.suggest(gst.TYPE_FIND_MAXIMUM, caps)


def register_typefind(mimetype, func, extensions):
    caps = gst.caps_from_string(mimetype)
    gst.type_find_register(mimetype, gst.RANK_PRIMARY, playlist_typefinder,
                           extensions, caps, func, caps)


def register_typefinders():
    register_typefind('audio/x-mpegurl', detect_m3u_header, [b'm3u', b'm3u8'])
    register_typefind('audio/x-scpls', detect_pls_header, [b'pls'])
    register_typefind('application/xspf+xml', detect_xspf_header, [b'xspf'])
    # NOTE: seems we can't use video/x-ms-asf which is the correct mime for asx
    # as it is shared with asf for streaming videos :/
    register_typefind('audio/x-ms-asx', detect_asx_header, [b'asx'])


class BasePlaylistElement(gst.Bin):
    """Base class for creating GStreamer elements for playlist support.

    This element performs the following steps:

    1. Initializes src and sink pads for the element.
    2. Collects data from the sink until EOS is reached.
    3. Passes the collected data to :meth:`convert` to get a list of URIs.
    4. Passes the list of URIs to :meth:`handle`, default handling is to pass
       the URIs to the src element as a uri-list.
    5. If handle returned true, the EOS consumed and nothing more happens, if
       it is not consumed it flows on to the next element downstream, which is
       likely our uri-list consumer which needs the EOS to know we are done
       sending URIs.
    """

    sinkpad_template = None
    """GStreamer pad template to use for sink, must be overriden."""

    srcpad_template = None
    """GStreamer pad template to use for src, must be overriden."""

    ghost_srcpad = False
    """Indicates if src pad should be ghosted or not."""

    def __init__(self):
        """Sets up src and sink pads plus behaviour."""
        super(BasePlaylistElement, self).__init__()
        self._data = io.BytesIO()
        self._done = False

        self.sinkpad = gst.Pad(self.sinkpad_template)
        self.sinkpad.set_chain_function(self._chain)
        self.sinkpad.set_event_function(self._event)
        self.add_pad(self.sinkpad)

        if self.ghost_srcpad:
            self.srcpad = gst.ghost_pad_new_notarget('src', gst.PAD_SRC)
        else:
            self.srcpad = gst.Pad(self.srcpad_template)
        self.add_pad(self.srcpad)

    def convert(self, data):
        """Convert the data we have colleted to URIs.

        :param data: collected data buffer
        :type data: :class:`io.BytesIO`
        :returns: iterable or generator of URIs
        """
        raise NotImplementedError

    def handle(self, uris):
        """Do something useful with the URIs.

        :param uris: list of URIs
        :type uris: :type:`list`
        :returns: boolean indicating if EOS should be consumed
        """
        # TODO: handle unicode uris which we can get out of elementtree
        self.srcpad.push(gst.Buffer('\n'.join(uris)))
        return False

    def _chain(self, pad, buf):
        if not self._done:
            self._data.write(buf.data)
            return gst.FLOW_OK
        return gst.FLOW_EOS

    def _event(self, pad, event):
        if event.type == gst.EVENT_NEWSEGMENT:
            return True

        if event.type == gst.EVENT_EOS:
            self._done = True
            self._data.seek(0)
            if self.handle(list(self.convert(self._data))):
                return True

        # Ensure we handle remaining events in a sane way.
        return pad.event_default(event)


class M3uDecoder(BasePlaylistElement):
    __gstdetails__ = ('M3U Decoder',
                      'Decoder',
                      'Convert .m3u to text/uri-list',
                      'Mopidy')

    sinkpad_template = gst.PadTemplate(
        'sink', gst.PAD_SINK, gst.PAD_ALWAYS,
        gst.caps_from_string('audio/x-mpegurl'))

    srcpad_template = gst.PadTemplate(
        'src', gst.PAD_SRC, gst.PAD_ALWAYS,
        gst.caps_from_string('text/uri-list'))

    __gsttemplates__ = (sinkpad_template, srcpad_template)

    def convert(self, data):
        return parse_m3u(data)


class PlsDecoder(BasePlaylistElement):
    __gstdetails__ = ('PLS Decoder',
                      'Decoder',
                      'Convert .pls to text/uri-list',
                      'Mopidy')

    sinkpad_template = gst.PadTemplate(
        'sink', gst.PAD_SINK, gst.PAD_ALWAYS,
        gst.caps_from_string('audio/x-scpls'))

    srcpad_template = gst.PadTemplate(
        'src', gst.PAD_SRC, gst.PAD_ALWAYS,
        gst.caps_from_string('text/uri-list'))

    __gsttemplates__ = (sinkpad_template, srcpad_template)

    def convert(self, data):
        return parse_pls(data)


class XspfDecoder(BasePlaylistElement):
    __gstdetails__ = ('XSPF Decoder',
                      'Decoder',
                      'Convert .pls to text/uri-list',
                      'Mopidy')

    sinkpad_template = gst.PadTemplate(
        'sink', gst.PAD_SINK, gst.PAD_ALWAYS,
        gst.caps_from_string('application/xspf+xml'))

    srcpad_template = gst.PadTemplate(
        'src', gst.PAD_SRC, gst.PAD_ALWAYS,
        gst.caps_from_string('text/uri-list'))

    __gsttemplates__ = (sinkpad_template, srcpad_template)

    def convert(self, data):
        return parse_xspf(data)


class AsxDecoder(BasePlaylistElement):
    __gstdetails__ = ('ASX Decoder',
                      'Decoder',
                      'Convert .asx to text/uri-list',
                      'Mopidy')

    sinkpad_template = gst.PadTemplate(
        'sink', gst.PAD_SINK, gst.PAD_ALWAYS,
        gst.caps_from_string('audio/x-ms-asx'))

    srcpad_template = gst.PadTemplate(
        'src', gst.PAD_SRC, gst.PAD_ALWAYS,
        gst.caps_from_string('text/uri-list'))

    __gsttemplates__ = (sinkpad_template, srcpad_template)

    def convert(self, data):
        return parse_asx(data)


class UriListElement(BasePlaylistElement):
    __gstdetails__ = ('URIListDemuxer',
                      'Demuxer',
                      'Convert a text/uri-list to a stream',
                      'Mopidy')

    sinkpad_template = gst.PadTemplate(
        'sink', gst.PAD_SINK, gst.PAD_ALWAYS,
        gst.caps_from_string('text/uri-list'))

    srcpad_template = gst.PadTemplate(
        'src', gst.PAD_SRC, gst.PAD_ALWAYS,
        gst.caps_new_any())

    ghost_srcpad = True  # We need to hook this up to our internal decodebin

    __gsttemplates__ = (sinkpad_template, srcpad_template)

    def __init__(self):
        super(UriListElement, self).__init__()
        self.uridecodebin = gst.element_factory_make('uridecodebin')
        self.uridecodebin.connect('pad-added', self.pad_added)
        # Limit to anycaps so we get a single stream out, letting other
        # elements downstream figure out actual muxing
        self.uridecodebin.set_property('caps', gst.caps_new_any())

    def pad_added(self, src, pad):
        self.srcpad.set_target(pad)
        pad.add_event_probe(self.pad_event)

    def pad_event(self, pad, event):
        if event.has_name('urilist-played'):
            error = gst.GError(gst.RESOURCE_ERROR, gst.RESOURCE_ERROR_FAILED,
                               b'Nested playlists not supported.')
            message = b'Playlists pointing to other playlists is not supported'
            self.post_message(gst.message_new_error(self, error, message))
        return 1  # GST_PAD_PROBE_OK

    def handle(self, uris):
        struct = gst.Structure('urilist-played')
        event = gst.event_new_custom(gst.EVENT_CUSTOM_UPSTREAM, struct)
        self.sinkpad.push_event(event)

        # TODO: hookup about to finish and errors to rest of URIs so we
        # round robin, only giving up once all have been tried.
        # TODO: uris could be empty.
        self.add(self.uridecodebin)
        self.uridecodebin.set_state(gst.STATE_READY)
        self.uridecodebin.set_property('uri', uris[0])
        self.uridecodebin.sync_state_with_parent()
        return True  # Make sure we consume the EOS that triggered us.

    def convert(self, data):
        return parse_urilist(data)


class IcySrc(gst.Bin, gst.URIHandler):
    __gstdetails__ = ('IcySrc',
                      'Src',
                      'HTTP src wrapper for icy:// support.',
                      'Mopidy')

    srcpad_template = gst.PadTemplate(
        'src', gst.PAD_SRC, gst.PAD_ALWAYS,
        gst.caps_new_any())

    __gsttemplates__ = (srcpad_template,)

    def __init__(self):
        super(IcySrc, self).__init__()
        self._httpsrc = gst.element_make_from_uri(gst.URI_SRC, 'http://')
        try:
            self._httpsrc.set_property('iradio-mode', True)
        except TypeError:
            pass
        self.add(self._httpsrc)

        self._srcpad = gst.GhostPad('src', self._httpsrc.get_pad('src'))
        self.add_pad(self._srcpad)

    @classmethod
    def do_get_type_full(cls):
        return gst.URI_SRC

    @classmethod
    def do_get_protocols_full(cls):
        return [b'icy', b'icyx']

    def do_set_uri(self, uri):
        if uri.startswith('icy://'):
            return self._httpsrc.set_uri(b'http://' + uri[len('icy://'):])
        elif uri.startswith('icyx://'):
            return self._httpsrc.set_uri(b'https://' + uri[len('icyx://'):])
        else:
            return False

    def do_get_uri(self):
        uri = self._httpsrc.get_uri()
        if uri.startswith('http://'):
            return b'icy://' + uri[len('http://'):]
        else:
            return b'icyx://' + uri[len('https://'):]


def register_element(element_class):
    gobject.type_register(element_class)
    gst.element_register(
        element_class, element_class.__name__.lower(), gst.RANK_MARGINAL)


def register_elements():
    register_element(M3uDecoder)
    register_element(PlsDecoder)
    register_element(XspfDecoder)
    register_element(AsxDecoder)
    register_element(UriListElement)

    # Only register icy if gst install can't handle it on it's own.
    if not gst.element_make_from_uri(gst.URI_SRC, 'icy://'):
        register_element(IcySrc)

########NEW FILE########
__FILENAME__ = scan
from __future__ import unicode_literals

import datetime
import os
import time

import pygst
pygst.require('0.10')
import gst  # noqa

from mopidy import exceptions
from mopidy.models import Album, Artist, Track
from mopidy.utils import encoding, path


class Scanner(object):
    """
    Helper to get tags and other relevant info from URIs.

    :param timeout: timeout for scanning a URI in ms
    :type event: int
    :param min_duration: minimum duration of scanned URI in ms, -1 for all.
    :type event: int
    """

    def __init__(self, timeout=1000, min_duration=100):
        self._timeout_ms = timeout
        self._min_duration_ms = min_duration

        sink = gst.element_factory_make('fakesink')

        audio_caps = gst.Caps(b'audio/x-raw-int; audio/x-raw-float')
        pad_added = lambda src, pad: pad.link(sink.get_pad('sink'))

        self._uribin = gst.element_factory_make('uridecodebin')
        self._uribin.set_property('caps', audio_caps)
        self._uribin.connect('pad-added', pad_added)

        self._pipe = gst.element_factory_make('pipeline')
        self._pipe.add(self._uribin)
        self._pipe.add(sink)

        self._bus = self._pipe.get_bus()
        self._bus.set_flushing(True)

    def scan(self, uri):
        """
        Scan the given uri collecting relevant metadata.

        :param uri: URI of the resource to scan.
        :type event: string
        :return: Dictionary of tags, duration, mtime and uri information.
        """
        try:
            self._setup(uri)
            tags = self._collect()  # Ensure collect before queries.
            data = {'uri': uri, 'tags': tags,
                    'mtime': self._query_mtime(uri),
                    'duration': self._query_duration()}
        finally:
            self._reset()

        if self._min_duration_ms is None:
            return data
        elif data['duration'] >= self._min_duration_ms * gst.MSECOND:
            return data

        raise exceptions.ScannerError('Rejecting file with less than %dms '
                                      'audio data.' % self._min_duration_ms)

    def _setup(self, uri):
        """Primes the pipeline for collection."""
        self._pipe.set_state(gst.STATE_READY)
        self._uribin.set_property(b'uri', uri)
        self._bus.set_flushing(False)
        result = self._pipe.set_state(gst.STATE_PAUSED)
        if result == gst.STATE_CHANGE_NO_PREROLL:
            # Live sources don't pre-roll, so set to playing to get data.
            self._pipe.set_state(gst.STATE_PLAYING)

    def _collect(self):
        """Polls for messages to collect data."""
        start = time.time()
        timeout_s = self._timeout_ms / float(1000)
        tags = {}

        while time.time() - start < timeout_s:
            if not self._bus.have_pending():
                continue
            message = self._bus.pop()

            if message.type == gst.MESSAGE_ERROR:
                raise exceptions.ScannerError(
                    encoding.locale_decode(message.parse_error()[0]))
            elif message.type == gst.MESSAGE_EOS:
                return tags
            elif message.type == gst.MESSAGE_ASYNC_DONE:
                if message.src == self._pipe:
                    return tags
            elif message.type == gst.MESSAGE_TAG:
                # Taglists are not really dicts, hence the lack of .items() and
                # explicit .keys. We only keep the last tag for each key, as we
                # assume this is the best, some formats will produce multiple
                # taglists. Lastly we force everything to lists for conformity.
                taglist = message.parse_tag()
                for key in taglist.keys():
                    value = taglist[key]
                    if not isinstance(value, list):
                        value = [value]
                    tags[key] = value

        raise exceptions.ScannerError('Timeout after %dms' % self._timeout_ms)

    def _reset(self):
        """Ensures we cleanup child elements and flush the bus."""
        self._bus.set_flushing(True)
        self._pipe.set_state(gst.STATE_NULL)

    def _query_duration(self):
        try:
            return self._pipe.query_duration(gst.FORMAT_TIME, None)[0]
        except gst.QueryError:
            return None

    def _query_mtime(self, uri):
        if not uri.startswith('file:'):
            return None
        return os.path.getmtime(path.uri_to_path(uri))


def _artists(tags, artist_name, artist_id=None):
    # Name missing, don't set artist
    if not tags.get(artist_name):
        return None
    # One artist name and id, provide artist with id.
    if len(tags[artist_name]) == 1 and artist_id in tags:
        return [Artist(name=tags[artist_name][0],
                       musicbrainz_id=tags[artist_id][0])]
    # Multiple artist, provide artists without id.
    return [Artist(name=name) for name in tags[artist_name]]


def _date(tags):
    if not tags.get(gst.TAG_DATE):
        return None
    try:
        date = tags[gst.TAG_DATE][0]
        return datetime.date(date.year, date.month, date.day).isoformat()
    except ValueError:
        return None


def audio_data_to_track(data):
    """Convert taglist data + our extras to a track."""
    tags = data['tags']
    album_kwargs = {}
    track_kwargs = {}

    track_kwargs['composers'] = _artists(tags, gst.TAG_COMPOSER)
    track_kwargs['performers'] = _artists(tags, gst.TAG_PERFORMER)
    track_kwargs['artists'] = _artists(
        tags, gst.TAG_ARTIST, 'musicbrainz-artistid')
    album_kwargs['artists'] = _artists(
        tags, gst.TAG_ALBUM_ARTIST, 'musicbrainz-albumartistid')

    track_kwargs['genre'] = '; '.join(tags.get(gst.TAG_GENRE, []))
    track_kwargs['name'] = '; '.join(tags.get(gst.TAG_TITLE, []))
    if not track_kwargs['name']:
        track_kwargs['name'] = '; '.join(tags.get(gst.TAG_ORGANIZATION, []))

    track_kwargs['comment'] = '; '.join(tags.get('comment', []))
    if not track_kwargs['comment']:
        track_kwargs['comment'] = '; '.join(tags.get(gst.TAG_LOCATION, []))
    if not track_kwargs['comment']:
        track_kwargs['comment'] = '; '.join(tags.get(gst.TAG_COPYRIGHT, []))

    track_kwargs['track_no'] = tags.get(gst.TAG_TRACK_NUMBER, [None])[0]
    track_kwargs['disc_no'] = tags.get(gst.TAG_ALBUM_VOLUME_NUMBER, [None])[0]
    track_kwargs['bitrate'] = tags.get(gst.TAG_BITRATE, [None])[0]
    track_kwargs['musicbrainz_id'] = tags.get('musicbrainz-trackid', [None])[0]

    album_kwargs['name'] = tags.get(gst.TAG_ALBUM, [None])[0]
    album_kwargs['num_tracks'] = tags.get(gst.TAG_TRACK_COUNT, [None])[0]
    album_kwargs['num_discs'] = tags.get(gst.TAG_ALBUM_VOLUME_COUNT, [None])[0]
    album_kwargs['musicbrainz_id'] = tags.get('musicbrainz-albumid', [None])[0]

    track_kwargs['date'] = _date(tags)
    track_kwargs['last_modified'] = int(data.get('mtime') or 0)
    track_kwargs['length'] = (data.get(gst.TAG_DURATION) or 0) // gst.MSECOND

    # Clear out any empty values we found
    track_kwargs = {k: v for k, v in track_kwargs.items() if v}
    album_kwargs = {k: v for k, v in album_kwargs.items() if v}

    track_kwargs['uri'] = data['uri']
    track_kwargs['album'] = Album(**album_kwargs)
    return Track(**track_kwargs)

########NEW FILE########
__FILENAME__ = utils
from __future__ import unicode_literals

import pygst
pygst.require('0.10')
import gst  # noqa


def calculate_duration(num_samples, sample_rate):
    """Determine duration of samples using GStreamer helper for precise
    math."""
    return gst.util_uint64_scale(num_samples, gst.SECOND, sample_rate)


def create_buffer(data, capabilites=None, timestamp=None, duration=None):
    """Create a new GStreamer buffer based on provided data.

    Mainly intended to keep gst imports out of non-audio modules.
    """
    buffer_ = gst.Buffer(data)
    if capabilites:
        if isinstance(capabilites, basestring):
            capabilites = gst.caps_from_string(capabilites)
        buffer_.set_caps(capabilites)
    if timestamp:
        buffer_.timestamp = timestamp
    if duration:
        buffer_.duration = duration
    return buffer_


def millisecond_to_clocktime(value):
    """Convert a millisecond time to internal GStreamer time."""
    return value * gst.MSECOND


def clocktime_to_millisecond(value):
    """Convert an internal GStreamer time to millisecond time."""
    return value // gst.MSECOND


def supported_uri_schemes(uri_schemes):
    """Determine which URIs we can actually support from provided whitelist.

    :param uri_schemes: list/set of URIs to check support for.
    :type uri_schemes: list or set or URI schemes as strings.
    :rtype: set of URI schemes we can support via this GStreamer install.
    """
    supported_schemes = set()
    registry = gst.registry_get_default()

    for factory in registry.get_feature_list(gst.TYPE_ELEMENT_FACTORY):
        for uri in factory.get_uri_protocols():
            if uri in uri_schemes:
                supported_schemes.add(uri)

    return supported_schemes

########NEW FILE########
__FILENAME__ = dummy
"""A dummy backend for use in tests.

This backend implements the backend API in the simplest way possible.  It is
used in tests of the frontends.
"""

from __future__ import unicode_literals

import pykka

from mopidy import backend
from mopidy.models import Playlist, Ref, SearchResult


def create_dummy_backend_proxy(config=None, audio=None):
    return DummyBackend.start(config=config, audio=audio).proxy()


class DummyBackend(pykka.ThreadingActor, backend.Backend):
    def __init__(self, config, audio):
        super(DummyBackend, self).__init__()

        self.library = DummyLibraryProvider(backend=self)
        self.playback = DummyPlaybackProvider(audio=audio, backend=self)
        self.playlists = DummyPlaylistsProvider(backend=self)

        self.uri_schemes = ['dummy']


class DummyLibraryProvider(backend.LibraryProvider):
    root_directory = Ref.directory(uri='dummy:/', name='dummy')

    def __init__(self, *args, **kwargs):
        super(DummyLibraryProvider, self).__init__(*args, **kwargs)
        self.dummy_library = []
        self.dummy_browse_result = {}
        self.dummy_find_exact_result = SearchResult()
        self.dummy_search_result = SearchResult()

    def browse(self, path):
        return self.dummy_browse_result.get(path, [])

    def find_exact(self, **query):
        return self.dummy_find_exact_result

    def lookup(self, uri):
        return filter(lambda t: uri == t.uri, self.dummy_library)

    def refresh(self, uri=None):
        pass

    def search(self, **query):
        return self.dummy_search_result


class DummyPlaybackProvider(backend.PlaybackProvider):
    def __init__(self, *args, **kwargs):
        super(DummyPlaybackProvider, self).__init__(*args, **kwargs)
        self._time_position = 0

    def pause(self):
        return True

    def play(self, track):
        """Pass a track with URI 'dummy:error' to force failure"""
        self._time_position = 0
        return track.uri != 'dummy:error'

    def resume(self):
        return True

    def seek(self, time_position):
        self._time_position = time_position
        return True

    def stop(self):
        return True

    def get_time_position(self):
        return self._time_position


class DummyPlaylistsProvider(backend.PlaylistsProvider):
    def create(self, name):
        playlist = Playlist(name=name, uri='dummy:%s' % name)
        self._playlists.append(playlist)
        return playlist

    def delete(self, uri):
        playlist = self.lookup(uri)
        if playlist:
            self._playlists.remove(playlist)

    def lookup(self, uri):
        for playlist in self._playlists:
            if playlist.uri == uri:
                return playlist

    def refresh(self):
        pass

    def save(self, playlist):
        old_playlist = self.lookup(playlist.uri)

        if old_playlist is not None:
            index = self._playlists.index(old_playlist)
            self._playlists[index] = playlist
        else:
            self._playlists.append(playlist)

        return playlist

########NEW FILE########
__FILENAME__ = commands
from __future__ import print_function, unicode_literals

import argparse
import collections
import logging
import os
import sys

import glib

import gobject

from mopidy import config as config_lib
from mopidy.audio import Audio
from mopidy.core import Core
from mopidy.utils import deps, process, versioning

logger = logging.getLogger(__name__)

_default_config = []
for base in glib.get_system_config_dirs() + (glib.get_user_config_dir(),):
    _default_config.append(os.path.join(base, b'mopidy', b'mopidy.conf'))
DEFAULT_CONFIG = b':'.join(_default_config)


def config_files_type(value):
    return value.split(b':')


def config_override_type(value):
    try:
        section, remainder = value.split(b'/', 1)
        key, value = remainder.split(b'=', 1)
        return (section.strip(), key.strip(), value.strip())
    except ValueError:
        raise argparse.ArgumentTypeError(
            '%s must have the format section/key=value' % value)


class _ParserError(Exception):
    pass


class _HelpError(Exception):
    pass


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        raise _ParserError(message)


class _HelpAction(argparse.Action):
    def __init__(self, option_strings, dest=None, help=None):
        super(_HelpAction, self).__init__(
            option_strings=option_strings,
            dest=dest or argparse.SUPPRESS,
            default=argparse.SUPPRESS,
            nargs=0,
            help=help)

    def __call__(self, parser, namespace, values, option_string=None):
        raise _HelpError()


class Command(object):
    """Command parser and runner for building trees of commands.

    This class provides a wraper around :class:`argparse.ArgumentParser`
    for handling this type of command line application in a better way than
    argprases own sub-parser handling.
    """

    help = None
    #: Help text to display in help output.

    def __init__(self):
        self._children = collections.OrderedDict()
        self._arguments = []
        self._overrides = {}

    def _build(self):
        actions = []
        parser = _ArgumentParser(add_help=False)
        parser.register('action', 'help', _HelpAction)

        for args, kwargs in self._arguments:
            actions.append(parser.add_argument(*args, **kwargs))

        parser.add_argument('_args', nargs=argparse.REMAINDER,
                            help=argparse.SUPPRESS)
        return parser, actions

    def add_child(self, name, command):
        """Add a child parser to consider using.

        :param name: name to use for the sub-command that is being added.
        :type name: string
        """
        self._children[name] = command

    def add_argument(self, *args, **kwargs):
        """Add am argument to the parser.

        This method takes all the same arguments as the
        :class:`argparse.ArgumentParser` version of this method.
        """
        self._arguments.append((args, kwargs))

    def set(self, **kwargs):
        """Override a value in the finaly result of parsing."""
        self._overrides.update(kwargs)

    def exit(self, status_code=0, message=None, usage=None):
        """Optionally print a message and exit."""
        print('\n\n'.join(m for m in (usage, message) if m))
        sys.exit(status_code)

    def format_usage(self, prog=None):
        """Format usage for current parser."""
        actions = self._build()[1]
        prog = prog or os.path.basename(sys.argv[0])
        return self._usage(actions, prog) + '\n'

    def _usage(self, actions, prog):
        formatter = argparse.HelpFormatter(prog)
        formatter.add_usage(None, actions, [])
        return formatter.format_help().strip()

    def format_help(self, prog=None):
        """Format help for current parser and children."""
        actions = self._build()[1]
        prog = prog or os.path.basename(sys.argv[0])

        formatter = argparse.HelpFormatter(prog)
        formatter.add_usage(None, actions, [])

        if self.help:
            formatter.add_text(self.help)

        if actions:
            formatter.add_text('OPTIONS:')
            formatter.start_section(None)
            formatter.add_arguments(actions)
            formatter.end_section()

        subhelp = []
        for name, child in self._children.items():
            child._subhelp(name, subhelp)

        if subhelp:
            formatter.add_text('COMMANDS:')
            subhelp.insert(0, '')

        return formatter.format_help() + '\n'.join(subhelp)

    def _subhelp(self, name, result):
        actions = self._build()[1]

        if self.help or actions:
            formatter = argparse.HelpFormatter(name)
            formatter.add_usage(None, actions, [], '')
            formatter.start_section(None)
            formatter.add_text(self.help)
            formatter.start_section(None)
            formatter.add_arguments(actions)
            formatter.end_section()
            formatter.end_section()
            result.append(formatter.format_help())

        for childname, child in self._children.items():
            child._subhelp(' '.join((name, childname)), result)

    def parse(self, args, prog=None):
        """Parse command line arguments.

        Will recursively parse commands until a final parser is found or an
        error occurs. In the case of errors we will print a message and exit.
        Otherwise, any overrides are applied and the current parser stored
        in the command attribute of the return value.

        :param args: list of arguments to parse
        :type args: list of strings
        :param prog: name to use for program
        :type prog: string
        :rtype: :class:`argparse.Namespace`
        """
        prog = prog or os.path.basename(sys.argv[0])
        try:
            return self._parse(
                args, argparse.Namespace(), self._overrides.copy(), prog)
        except _HelpError:
            self.exit(0, self.format_help(prog))

    def _parse(self, args, namespace, overrides, prog):
        overrides.update(self._overrides)
        parser, actions = self._build()

        try:
            result = parser.parse_args(args, namespace)
        except _ParserError as e:
            self.exit(1, e.message, self._usage(actions, prog))

        if not result._args:
            for attr, value in overrides.items():
                setattr(result, attr, value)
            delattr(result, '_args')
            result.command = self
            return result

        child = result._args.pop(0)
        if child not in self._children:
            usage = self._usage(actions, prog)
            self.exit(1, 'unrecognized command: %s' % child, usage)

        return self._children[child]._parse(
            result._args, result, overrides, ' '.join([prog, child]))

    def run(self, *args, **kwargs):
        """Run the command.

        Must be implemented by sub-classes that are not simply and intermediate
        in the command namespace.
        """
        raise NotImplementedError


class RootCommand(Command):
    def __init__(self):
        super(RootCommand, self).__init__()
        self.set(base_verbosity_level=0)
        self.add_argument(
            '-h', '--help',
            action='help', help='Show this message and exit')
        self.add_argument(
            '--version', action='version',
            version='Mopidy %s' % versioning.get_version())
        self.add_argument(
            '-q', '--quiet',
            action='store_const', const=-1, dest='verbosity_level',
            help='less output (warning level)')
        self.add_argument(
            '-v', '--verbose',
            action='count', dest='verbosity_level', default=0,
            help='more output (repeat up to 3 times for even more)')
        self.add_argument(
            '--save-debug-log',
            action='store_true', dest='save_debug_log',
            help='save debug log to "./mopidy.log"')
        self.add_argument(
            '--config',
            action='store', dest='config_files', type=config_files_type,
            default=DEFAULT_CONFIG, metavar='FILES',
            help='config files to use, colon seperated, later files override')
        self.add_argument(
            '-o', '--option',
            action='append', dest='config_overrides',
            type=config_override_type, metavar='OPTIONS',
            help='`section/key=value` values to override config options')

    def run(self, args, config):
        loop = gobject.MainLoop()

        backend_classes = args.registry['backend']
        frontend_classes = args.registry['frontend']

        try:
            audio = self.start_audio(config)
            backends = self.start_backends(config, backend_classes, audio)
            core = self.start_core(audio, backends)
            self.start_frontends(config, frontend_classes, core)
            loop.run()
        except KeyboardInterrupt:
            logger.info('Interrupted. Exiting...')
            return
        finally:
            loop.quit()
            self.stop_frontends(frontend_classes)
            self.stop_core()
            self.stop_backends(backend_classes)
            self.stop_audio()
            process.stop_remaining_actors()

    def start_audio(self, config):
        logger.info('Starting Mopidy audio')
        return Audio.start(config=config).proxy()

    def start_backends(self, config, backend_classes, audio):
        logger.info(
            'Starting Mopidy backends: %s',
            ', '.join(b.__name__ for b in backend_classes) or 'none')

        backends = []
        for backend_class in backend_classes:
            backend = backend_class.start(config=config, audio=audio).proxy()
            backends.append(backend)

        return backends

    def start_core(self, audio, backends):
        logger.info('Starting Mopidy core')
        return Core.start(audio=audio, backends=backends).proxy()

    def start_frontends(self, config, frontend_classes, core):
        logger.info(
            'Starting Mopidy frontends: %s',
            ', '.join(f.__name__ for f in frontend_classes) or 'none')

        for frontend_class in frontend_classes:
            frontend_class.start(config=config, core=core)

    def stop_frontends(self, frontend_classes):
        logger.info('Stopping Mopidy frontends')
        for frontend_class in frontend_classes:
            process.stop_actors_by_class(frontend_class)

    def stop_core(self):
        logger.info('Stopping Mopidy core')
        process.stop_actors_by_class(Core)

    def stop_backends(self, backend_classes):
        logger.info('Stopping Mopidy backends')
        for backend_class in backend_classes:
            process.stop_actors_by_class(backend_class)

    def stop_audio(self):
        logger.info('Stopping Mopidy audio')
        process.stop_actors_by_class(Audio)


class ConfigCommand(Command):
    help = 'Show currently active configuration.'

    def __init__(self):
        super(ConfigCommand, self).__init__()
        self.set(base_verbosity_level=-1)

    def run(self, config, errors, extensions):
        print(config_lib.format(config, extensions, errors))
        return 0


class DepsCommand(Command):
    help = 'Show dependencies and debug information.'

    def __init__(self):
        super(DepsCommand, self).__init__()
        self.set(base_verbosity_level=-1)

    def run(self):
        print(deps.format_dependency_list())
        return 0

########NEW FILE########
__FILENAME__ = keyring
from __future__ import unicode_literals

import logging

logger = logging.getLogger(__name__)

try:
    import dbus
except ImportError:
    dbus = None


# XXX: Hack to workaround introspection bug caused by gnome-keyring, should be
# fixed by version 3.5 per:
# https://git.gnome.org/browse/gnome-keyring/commit/?id=5dccbe88eb94eea9934e2b7
if dbus:
    EMPTY_STRING = dbus.String('', variant_level=1)
else:
    EMPTY_STRING = ''


FETCH_ERROR = (
    'Fetching passwords from your keyring failed. Any passwords '
    'stored in the keyring will not be available.')


def fetch():
    if not dbus:
        logger.debug('%s (dbus not installed)', FETCH_ERROR)
        return []

    try:
        bus = dbus.SessionBus()
    except dbus.exceptions.DBusException as e:
        logger.debug('%s (%s)', FETCH_ERROR, e)
        return []

    if not bus.name_has_owner('org.freedesktop.secrets'):
        logger.debug(
            '%s (org.freedesktop.secrets service not running)', FETCH_ERROR)
        return []

    service = _service(bus)
    session = service.OpenSession('plain', EMPTY_STRING)[1]
    items, locked = service.SearchItems({'service': 'mopidy'})

    if not locked and not items:
        return []

    if locked:
        # There is a chance we can unlock without prompting the users...
        items, prompt = service.Unlock(locked)
        if prompt != '/':
            _prompt(bus, prompt).Dismiss()
            logger.debug('%s (Keyring is locked)', FETCH_ERROR)
            return []

    result = []
    secrets = service.GetSecrets(items, session, byte_arrays=True)
    for item_path, values in secrets.iteritems():
        session_path, parameters, value, content_type = values
        attrs = _item_attributes(bus, item_path)
        result.append((attrs['section'], attrs['key'], bytes(value)))
    return result


def set(section, key, value):
    """Store a secret config value for a given section/key.

    Indicates if storage failed or succeeded.
    """
    if not dbus:
        logger.debug('Saving %s/%s to keyring failed. (dbus not installed)',
                     section, key)
        return False

    try:
        bus = dbus.SessionBus()
    except dbus.exceptions.DBusException as e:
        logger.debug('Saving %s/%s to keyring failed. (%s)', section, key, e)
        return False

    if not bus.name_has_owner('org.freedesktop.secrets'):
        logger.debug(
            'Saving %s/%s to keyring failed. '
            '(org.freedesktop.secrets service not running)',
            section, key)
        return False

    service = _service(bus)
    collection = _collection(bus)
    if not collection:
        return False

    if isinstance(value, unicode):
        value = value.encode('utf-8')

    session = service.OpenSession('plain', EMPTY_STRING)[1]
    secret = dbus.Struct((session, '', dbus.ByteArray(value),
                          'plain/text; charset=utf8'))
    label = 'mopidy: %s/%s' % (section, key)
    attributes = {'service': 'mopidy', 'section': section, 'key': key}
    properties = {'org.freedesktop.Secret.Item.Label': label,
                  'org.freedesktop.Secret.Item.Attributes': attributes}

    try:
        item, prompt = collection.CreateItem(properties, secret, True)
    except dbus.exceptions.DBusException as e:
        # TODO: catch IsLocked errors etc.
        logger.debug('Saving %s/%s to keyring failed. (%s)', section, key, e)
        return False

    if prompt == '/':
        return True

    _prompt(bus, prompt).Dismiss()
    logger.debug('Saving secret %s/%s failed. (Keyring is locked)',
                 section, key)
    return False


def _service(bus):
    return _interface(bus, '/org/freedesktop/secrets',
                      'org.freedesktop.Secret.Service')


# NOTE: depending on versions and setup 'default' might not exists, so try and
# use it but fall back to the 'login' collection, and finally the 'session' one
# if all else fails. We should probably create a keyring/collection setting
# that allows users to set this so they have control over where their secrets
# get stored.
def _collection(bus):
    for name in 'aliases/default', 'collection/login', 'collection/session':
        path = '/org/freedesktop/secrets/' + name
        if _collection_exists(bus, path):
            break
    else:
        return None
    return _interface(bus, path, 'org.freedesktop.Secret.Collection')


# NOTE: Hack to probe if a given collection actually exists. Needed to work
# around an introspection bug in setting passwords for non-existant aliases.
def _collection_exists(bus, path):
    try:
        item = _interface(bus, path, 'org.freedesktop.DBus.Properties')
        item.Get('org.freedesktop.Secret.Collection', 'Label')
        return True
    except dbus.exceptions.DBusException:
        return False


# NOTE: We could call prompt.Prompt('') to unlock the keyring when it is not
# '/', but we would then also have to arrange to setup signals to wait until
# this has been completed. So for now we just dismiss the prompt and expect
# keyrings to be unlocked.
def _prompt(bus, path):
    return _interface(bus, path, 'Prompt')


def _item_attributes(bus, path):
    item = _interface(bus, path, 'org.freedesktop.DBus.Properties')
    result = item.Get('org.freedesktop.Secret.Item', 'Attributes')
    return dict((bytes(k), bytes(v)) for k, v in result.iteritems())


def _interface(bus, path, interface):
    obj = bus.get_object('org.freedesktop.secrets', path)
    return dbus.Interface(obj, interface)

########NEW FILE########
__FILENAME__ = schemas
from __future__ import unicode_literals

import collections

from mopidy.config import types


def _did_you_mean(name, choices):
    """Suggest most likely setting based on levenshtein."""
    if not choices:
        return None

    name = name.lower()
    candidates = [(_levenshtein(name, c), c) for c in choices]
    candidates.sort()

    if candidates[0][0] <= 3:
        return candidates[0][1]
    return None


def _levenshtein(a, b):
    """Calculates the Levenshtein distance between a and b."""
    n, m = len(a), len(b)
    if n > m:
        return _levenshtein(b, a)

    current = xrange(n + 1)
    for i in xrange(1, m + 1):
        previous, current = current, [i] + [0] * n
        for j in xrange(1, n + 1):
            add, delete = previous[j] + 1, current[j - 1] + 1
            change = previous[j - 1]
            if a[j - 1] != b[i - 1]:
                change += 1
            current[j] = min(add, delete, change)
    return current[n]


class ConfigSchema(collections.OrderedDict):
    """Logical group of config values that correspond to a config section.

    Schemas are set up by assigning config keys with config values to
    instances. Once setup :meth:`deserialize` can be called with a dict of
    values to process. For convienience we also support :meth:`format` method
    that can used for converting the values to a dict that can be printed and
    :meth:`serialize` for converting the values to a form suitable for
    persistence.
    """
    def __init__(self, name):
        super(ConfigSchema, self).__init__()
        self.name = name

    def deserialize(self, values):
        """Validates the given ``values`` using the config schema.

        Returns a tuple with cleaned values and errors.
        """
        errors = {}
        result = {}

        for key, value in values.items():
            try:
                result[key] = self[key].deserialize(value)
            except KeyError:  # not in our schema
                errors[key] = 'unknown config key.'
                suggestion = _did_you_mean(key, self.keys())
                if suggestion:
                    errors[key] += ' Did you mean %s?' % suggestion
            except ValueError as e:  # deserialization failed
                result[key] = None
                errors[key] = str(e)

        for key in self.keys():
            if isinstance(self[key], types.Deprecated):
                result.pop(key, None)
            elif key not in result and key not in errors:
                result[key] = None
                errors[key] = 'config key not found.'

        return result, errors

    def serialize(self, values, display=False):
        """Converts the given ``values`` to a format suitable for persistence.

        If ``display`` is :class:`True` secret config values, like passwords,
        will be masked out.

        Returns a dict of config keys and values."""
        result = collections.OrderedDict()
        for key in self.keys():
            if key in values:
                result[key] = self[key].serialize(values[key], display)
        return result


class LogLevelConfigSchema(object):
    """Special cased schema for handling a config section with loglevels.

    Expects the config keys to be logger names and the values to be log levels
    as understood by the :class:`LogLevel` config value. Does not sub-class
    :class:`ConfigSchema`, but implements the same serialize/deserialize
    interface.
    """
    def __init__(self, name):
        self.name = name
        self._config_value = types.LogLevel()

    def deserialize(self, values):
        errors = {}
        result = {}

        for key, value in values.items():
            try:
                result[key] = self._config_value.deserialize(value)
            except ValueError as e:  # deserialization failed
                result[key] = None
                errors[key] = str(e)
        return result, errors

    def serialize(self, values, display=False):
        result = collections.OrderedDict()
        for key in sorted(values.keys()):
            result[key] = self._config_value.serialize(values[key], display)
        return result

########NEW FILE########
__FILENAME__ = types
from __future__ import unicode_literals

import logging
import re
import socket

from mopidy.config import validators
from mopidy.utils import path


def decode(value):
    if isinstance(value, unicode):
        return value
    # TODO: only unescape \n \t and \\?
    return value.decode('string-escape').decode('utf-8')


def encode(value):
    if not isinstance(value, unicode):
        return value
    for char in ('\\', '\n', '\t'):  # TODO: more escapes?
        value = value.replace(char, char.encode('unicode-escape'))
    return value.encode('utf-8')


class ExpandedPath(bytes):
    def __new__(self, original, expanded):
        return super(ExpandedPath, self).__new__(self, expanded)

    def __init__(self, original, expanded):
        self.original = original


class DeprecatedValue(object):
    pass


class ConfigValue(object):
    """Represents a config key's value and how to handle it.

    Normally you will only be interacting with sub-classes for config values
    that encode either deserialization behavior and/or validation.

    Each config value should be used for the following actions:

    1. Deserializing from a raw string and validating, raising ValueError on
       failure.
    2. Serializing a value back to a string that can be stored in a config.
    3. Formatting a value to a printable form (useful for masking secrets).

    :class:`None` values should not be deserialized, serialized or formatted,
    the code interacting with the config should simply skip None config values.
    """

    def deserialize(self, value):
        """Cast raw string to appropriate type."""
        return value

    def serialize(self, value, display=False):
        """Convert value back to string for saving."""
        if value is None:
            return b''
        return bytes(value)


class Deprecated(ConfigValue):
    """Deprecated value

    Used for ignoring old config values that are no longer in use, but should
    not cause the config parser to crash.
    """

    def deserialize(self, value):
        return DeprecatedValue()

    def serialize(self, value, display=False):
        return DeprecatedValue()


class String(ConfigValue):
    """String value.

    Is decoded as utf-8 and \\n \\t escapes should work and be preserved.
    """
    def __init__(self, optional=False, choices=None):
        self._required = not optional
        self._choices = choices

    def deserialize(self, value):
        value = decode(value).strip()
        validators.validate_required(value, self._required)
        if not value:
            return None
        validators.validate_choice(value, self._choices)
        return value

    def serialize(self, value, display=False):
        if value is None:
            return b''
        return encode(value)


class Secret(String):
    """Secret string value.

    Is decoded as utf-8 and \\n \\t escapes should work and be preserved.

    Should be used for passwords, auth tokens etc. Will mask value when being
    displayed.
    """
    def __init__(self, optional=False, choices=None):
        self._required = not optional
        self._choices = None  # Choices doesn't make sense for secrets

    def serialize(self, value, display=False):
        if value is not None and display:
            return b'********'
        return super(Secret, self).serialize(value, display)


class Integer(ConfigValue):
    """Integer value."""

    def __init__(
            self, minimum=None, maximum=None, choices=None, optional=False):
        self._required = not optional
        self._minimum = minimum
        self._maximum = maximum
        self._choices = choices

    def deserialize(self, value):
        validators.validate_required(value, self._required)
        if not value:
            return None
        value = int(value)
        validators.validate_choice(value, self._choices)
        validators.validate_minimum(value, self._minimum)
        validators.validate_maximum(value, self._maximum)
        return value


class Boolean(ConfigValue):
    """Boolean value.

    Accepts ``1``, ``yes``, ``true``, and ``on`` with any casing as
    :class:`True`.

    Accepts ``0``, ``no``, ``false``, and ``off`` with any casing as
    :class:`False`.
    """
    true_values = ('1', 'yes', 'true', 'on')
    false_values = ('0', 'no', 'false', 'off')

    def deserialize(self, value):
        if value.lower() in self.true_values:
            return True
        elif value.lower() in self.false_values:
            return False
        raise ValueError('invalid value for boolean: %r' % value)

    def serialize(self, value, display=False):
        if value:
            return b'true'
        else:
            return b'false'


class List(ConfigValue):
    """List value.

    Supports elements split by commas or newlines. Newlines take presedence and
    empty list items will be filtered out.
    """
    def __init__(self, optional=False):
        self._required = not optional

    def deserialize(self, value):
        if b'\n' in value:
            values = re.split(r'\s*\n\s*', value)
        else:
            values = re.split(r'\s*,\s*', value)
        values = (decode(v).strip() for v in values)
        values = filter(None, values)
        validators.validate_required(values, self._required)
        return tuple(values)

    def serialize(self, value, display=False):
        return b'\n  ' + b'\n  '.join(encode(v) for v in value if v)


class LogLevel(ConfigValue):
    """Log level value.

    Expects one of ``critical``, ``error``, ``warning``, ``info``, ``debug``
    with any casing.
    """
    levels = {
        b'critical': logging.CRITICAL,
        b'error': logging.ERROR,
        b'warning': logging.WARNING,
        b'info': logging.INFO,
        b'debug': logging.DEBUG,
    }

    def deserialize(self, value):
        validators.validate_choice(value.lower(), self.levels.keys())
        return self.levels.get(value.lower())

    def serialize(self, value, display=False):
        lookup = dict((v, k) for k, v in self.levels.items())
        if value in lookup:
            return lookup[value]
        return b''


class Hostname(ConfigValue):
    """Network hostname value."""

    def __init__(self, optional=False):
        self._required = not optional

    def deserialize(self, value, display=False):
        validators.validate_required(value, self._required)
        if not value.strip():
            return None
        try:
            socket.getaddrinfo(value, None)
        except socket.error:
            raise ValueError('must be a resolveable hostname or valid IP')
        return value


class Port(Integer):
    """Network port value.

    Expects integer in the range 0-65535, zero tells the kernel to simply
    allocate a port for us.
    """
    # TODO: consider probing if port is free or not?
    def __init__(self, choices=None, optional=False):
        super(Port, self).__init__(
            minimum=0, maximum=2 ** 16 - 1, choices=choices, optional=optional)


class Path(ConfigValue):
    """File system path

    The following expansions of the path will be done:

    - ``~`` to the current user's home directory

    - ``$XDG_CACHE_DIR`` according to the XDG spec

    - ``$XDG_CONFIG_DIR`` according to the XDG spec

    - ``$XDG_DATA_DIR`` according to the XDG spec

    - ``$XDG_MUSIC_DIR`` according to the XDG spec
    """
    def __init__(self, optional=False):
        self._required = not optional

    def deserialize(self, value):
        value = value.strip()
        expanded = path.expand_path(value)
        validators.validate_required(value, self._required)
        validators.validate_required(expanded, self._required)
        if not value or expanded is None:
            return None
        return ExpandedPath(value, expanded)

    def serialize(self, value, display=False):
        if isinstance(value, unicode):
            raise ValueError('paths should always be bytes')
        if isinstance(value, ExpandedPath):
            return value.original
        return value

########NEW FILE########
__FILENAME__ = validators
from __future__ import unicode_literals

# TODO: add validate regexp?


def validate_required(value, required):
    """Validate that ``value`` is set if ``required``

    Normally called in :meth:`~mopidy.config.types.ConfigValue.deserialize` on
    the raw string, _not_ the converted value.
    """
    if required and not value:
        raise ValueError('must be set.')


def validate_choice(value, choices):
    """Validate that ``value`` is one of the ``choices``

    Normally called in :meth:`~mopidy.config.types.ConfigValue.deserialize`.
    """
    if choices is not None and value not in choices:
        names = ', '.join(repr(c) for c in choices)
        raise ValueError('must be one of %s, not %s.' % (names, value))


def validate_minimum(value, minimum):
    """Validate that ``value`` is at least ``minimum``

    Normally called in :meth:`~mopidy.config.types.ConfigValue.deserialize`.
    """
    if minimum is not None and value < minimum:
        raise ValueError('%r must be larger than %r.' % (value, minimum))


def validate_maximum(value, maximum):
    """Validate that ``value`` is at most ``maximum``

    Normally called in :meth:`~mopidy.config.types.ConfigValue.deserialize`.
    """
    if maximum is not None and value > maximum:
        raise ValueError('%r must be smaller than %r.' % (value, maximum))

########NEW FILE########
__FILENAME__ = actor
from __future__ import unicode_literals

import collections
import itertools

import pykka

from mopidy import audio, backend
from mopidy.audio import PlaybackState
from mopidy.core.library import LibraryController
from mopidy.core.listener import CoreListener
from mopidy.core.playback import PlaybackController
from mopidy.core.playlists import PlaylistsController
from mopidy.core.tracklist import TracklistController
from mopidy.utils import versioning


class Core(pykka.ThreadingActor, audio.AudioListener, backend.BackendListener):
    library = None
    """The library controller. An instance of
    :class:`mopidy.core.LibraryController`."""

    playback = None
    """The playback controller. An instance of
    :class:`mopidy.core.PlaybackController`."""

    playlists = None
    """The playlists controller. An instance of
    :class:`mopidy.core.PlaylistsController`."""

    tracklist = None
    """The tracklist controller. An instance of
    :class:`mopidy.core.TracklistController`."""

    def __init__(self, audio=None, backends=None):
        super(Core, self).__init__()

        self.backends = Backends(backends)

        self.library = LibraryController(backends=self.backends, core=self)

        self.playback = PlaybackController(
            audio=audio, backends=self.backends, core=self)

        self.playlists = PlaylistsController(
            backends=self.backends, core=self)

        self.tracklist = TracklistController(core=self)

    def get_uri_schemes(self):
        futures = [b.uri_schemes for b in self.backends]
        results = pykka.get_all(futures)
        uri_schemes = itertools.chain(*results)
        return sorted(uri_schemes)

    uri_schemes = property(get_uri_schemes)
    """List of URI schemes we can handle"""

    def get_version(self):
        return versioning.get_version()

    version = property(get_version)
    """Version of the Mopidy core API"""

    def reached_end_of_stream(self):
        self.playback.on_end_of_track()

    def state_changed(self, old_state, new_state):
        # XXX: This is a temporary fix for issue #232 while we wait for a more
        # permanent solution with the implementation of issue #234. When the
        # Spotify play token is lost, the Spotify backend pauses audio
        # playback, but mopidy.core doesn't know this, so we need to update
        # mopidy.core's state to match the actual state in mopidy.audio. If we
        # don't do this, clients will think that we're still playing.
        if (new_state == PlaybackState.PAUSED
                and self.playback.state != PlaybackState.PAUSED):
            self.playback.state = new_state
            self.playback._trigger_track_playback_paused()

    def playlists_loaded(self):
        # Forward event from backend to frontends
        CoreListener.send('playlists_loaded')


class Backends(list):
    def __init__(self, backends):
        super(Backends, self).__init__(backends)

        self.with_library = collections.OrderedDict()
        self.with_library_browse = collections.OrderedDict()
        self.with_playback = collections.OrderedDict()
        self.with_playlists = collections.OrderedDict()

        backends_by_scheme = {}
        name = lambda b: b.actor_ref.actor_class.__name__

        for b in backends:
            has_library = b.has_library().get()
            has_library_browse = b.has_library_browse().get()
            has_playback = b.has_playback().get()
            has_playlists = b.has_playlists().get()

            for scheme in b.uri_schemes.get():
                assert scheme not in backends_by_scheme, (
                    'Cannot add URI scheme %s for %s, '
                    'it is already handled by %s'
                ) % (scheme, name(b), name(backends_by_scheme[scheme]))
                backends_by_scheme[scheme] = b

                if has_library:
                    self.with_library[scheme] = b
                if has_library_browse:
                    self.with_library_browse[scheme] = b
                if has_playback:
                    self.with_playback[scheme] = b
                if has_playlists:
                    self.with_playlists[scheme] = b

########NEW FILE########
__FILENAME__ = library
from __future__ import unicode_literals

import collections
import urlparse

import pykka


class LibraryController(object):
    pykka_traversable = True

    def __init__(self, backends, core):
        self.backends = backends
        self.core = core

    def _get_backend(self, uri):
        uri_scheme = urlparse.urlparse(uri).scheme
        return self.backends.with_library.get(uri_scheme, None)

    def _get_backends_to_uris(self, uris):
        if uris:
            backends_to_uris = collections.defaultdict(list)
            for uri in uris:
                backend = self._get_backend(uri)
                if backend is not None:
                    backends_to_uris[backend].append(uri)
        else:
            backends_to_uris = dict([
                (b, None) for b in self.backends.with_library.values()])
        return backends_to_uris

    def browse(self, uri):
        """
        Browse directories and tracks at the given ``uri``.

        ``uri`` is a string which represents some directory belonging to a
        backend. To get the intial root directories for backends pass None as
        the URI.

        Returns a list of :class:`mopidy.models.Ref` objects for the
        directories and tracks at the given ``uri``.

        The :class:`~mopidy.models.Ref` objects representing tracks keep the
        track's original URI. A matching pair of objects can look like this::

            Track(uri='dummy:/foo.mp3', name='foo', artists=..., album=...)
            Ref.track(uri='dummy:/foo.mp3', name='foo')

        The :class:`~mopidy.models.Ref` objects representing directories have
        backend specific URIs. These are opaque values, so no one but the
        backend that created them should try and derive any meaning from them.
        The only valid exception to this is checking the scheme, as it is used
        to route browse requests to the correct backend.

        For example, the dummy library's ``/bar`` directory could be returned
        like this::

            Ref.directory(uri='dummy:directory:/bar', name='bar')

        :param string uri: URI to browse
        :rtype: list of :class:`mopidy.models.Ref`
        """
        if uri is None:
            backends = self.backends.with_library_browse.values()
            return [b.library.root_directory.get() for b in backends]

        scheme = urlparse.urlparse(uri).scheme
        backend = self.backends.with_library_browse.get(scheme)
        if not backend:
            return []
        return backend.library.browse(uri).get()

    def find_exact(self, query=None, uris=None, **kwargs):
        """
        Search the library for tracks where ``field`` is ``values``.

        If the query is empty, and the backend can support it, all available
        tracks are returned.

        If ``uris`` is given, the search is limited to results from within the
        URI roots. For example passing ``uris=['file:']`` will limit the search
        to the local backend.

        Examples::

            # Returns results matching 'a' from any backend
            find_exact({'any': ['a']})
            find_exact(any=['a'])

            # Returns results matching artist 'xyz' from any backend
            find_exact({'artist': ['xyz']})
            find_exact(artist=['xyz'])

            # Returns results matching 'a' and 'b' and artist 'xyz' from any
            # backend
            find_exact({'any': ['a', 'b'], 'artist': ['xyz']})
            find_exact(any=['a', 'b'], artist=['xyz'])

            # Returns results matching 'a' if within the given URI roots
            # "file:///media/music" and "spotify:"
            find_exact(
                {'any': ['a']}, uris=['file:///media/music', 'spotify:'])
            find_exact(any=['a'], uris=['file:///media/music', 'spotify:'])

        :param query: one or more queries to search for
        :type query: dict
        :param uris: zero or more URI roots to limit the search to
        :type uris: list of strings or :class:`None`
        :rtype: list of :class:`mopidy.models.SearchResult`
        """
        query = query or kwargs
        futures = [
            backend.library.find_exact(query=query, uris=backend_uris)
            for (backend, backend_uris)
            in self._get_backends_to_uris(uris).items()]
        return [result for result in pykka.get_all(futures) if result]

    def lookup(self, uri):
        """
        Lookup the given URI.

        If the URI expands to multiple tracks, the returned list will contain
        them all.

        :param uri: track URI
        :type uri: string
        :rtype: list of :class:`mopidy.models.Track`
        """
        backend = self._get_backend(uri)
        if backend:
            return backend.library.lookup(uri).get()
        else:
            return []

    def refresh(self, uri=None):
        """
        Refresh library. Limit to URI and below if an URI is given.

        :param uri: directory or track URI
        :type uri: string
        """
        if uri is not None:
            backend = self._get_backend(uri)
            if backend:
                backend.library.refresh(uri).get()
        else:
            futures = [b.library.refresh(uri)
                       for b in self.backends.with_library.values()]
            pykka.get_all(futures)

    def search(self, query=None, uris=None, **kwargs):
        """
        Search the library for tracks where ``field`` contains ``values``.

        If the query is empty, and the backend can support it, all available
        tracks are returned.

        If ``uris`` is given, the search is limited to results from within the
        URI roots. For example passing ``uris=['file:']`` will limit the search
        to the local backend.

        Examples::

            # Returns results matching 'a' in any backend
            search({'any': ['a']})
            search(any=['a'])

            # Returns results matching artist 'xyz' in any backend
            search({'artist': ['xyz']})
            search(artist=['xyz'])

            # Returns results matching 'a' and 'b' and artist 'xyz' in any
            # backend
            search({'any': ['a', 'b'], 'artist': ['xyz']})
            search(any=['a', 'b'], artist=['xyz'])

            # Returns results matching 'a' if within the given URI roots
            # "file:///media/music" and "spotify:"
            search({'any': ['a']}, uris=['file:///media/music', 'spotify:'])
            search(any=['a'], uris=['file:///media/music', 'spotify:'])

        :param query: one or more queries to search for
        :type query: dict
        :param uris: zero or more URI roots to limit the search to
        :type uris: list of strings or :class:`None`
        :rtype: list of :class:`mopidy.models.SearchResult`
        """
        query = query or kwargs
        futures = [
            backend.library.search(query=query, uris=backend_uris)
            for (backend, backend_uris)
            in self._get_backends_to_uris(uris).items()]
        return [result for result in pykka.get_all(futures) if result]

########NEW FILE########
__FILENAME__ = listener
from __future__ import unicode_literals

from mopidy import listener


class CoreListener(listener.Listener):
    """
    Marker interface for recipients of events sent by the core actor.

    Any Pykka actor that mixes in this class will receive calls to the methods
    defined here when the corresponding events happen in the core actor. This
    interface is used both for looking up what actors to notify of the events,
    and for providing default implementations for those listeners that are not
    interested in all events.
    """

    @staticmethod
    def send(event, **kwargs):
        """Helper to allow calling of core listener events"""
        listener.send_async(CoreListener, event, **kwargs)

    def on_event(self, event, **kwargs):
        """
        Called on all events.

        *MAY* be implemented by actor. By default, this method forwards the
        event to the specific event methods.

        :param event: the event name
        :type event: string
        :param kwargs: any other arguments to the specific event handlers
        """
        getattr(self, event)(**kwargs)

    def track_playback_paused(self, tl_track, time_position):
        """
        Called whenever track playback is paused.

        *MAY* be implemented by actor.

        :param tl_track: the track that was playing when playback paused
        :type tl_track: :class:`mopidy.models.TlTrack`
        :param time_position: the time position in milliseconds
        :type time_position: int
        """
        pass

    def track_playback_resumed(self, tl_track, time_position):
        """
        Called whenever track playback is resumed.

        *MAY* be implemented by actor.

        :param tl_track: the track that was playing when playback resumed
        :type tl_track: :class:`mopidy.models.TlTrack`
        :param time_position: the time position in milliseconds
        :type time_position: int
        """
        pass

    def track_playback_started(self, tl_track):
        """
        Called whenever a new track starts playing.

        *MAY* be implemented by actor.

        :param tl_track: the track that just started playing
        :type tl_track: :class:`mopidy.models.TlTrack`
        """
        pass

    def track_playback_ended(self, tl_track, time_position):
        """
        Called whenever playback of a track ends.

        *MAY* be implemented by actor.

        :param tl_track: the track that was played before playback stopped
        :type tl_track: :class:`mopidy.models.TlTrack`
        :param time_position: the time position in milliseconds
        :type time_position: int
        """
        pass

    def playback_state_changed(self, old_state, new_state):
        """
        Called whenever playback state is changed.

        *MAY* be implemented by actor.

        :param old_state: the state before the change
        :type old_state: string from :class:`mopidy.core.PlaybackState` field
        :param new_state: the state after the change
        :type new_state: string from :class:`mopidy.core.PlaybackState` field
        """
        pass

    def tracklist_changed(self):
        """
        Called whenever the tracklist is changed.

        *MAY* be implemented by actor.
        """
        pass

    def playlists_loaded(self):
        """
        Called when playlists are loaded or refreshed.

        *MAY* be implemented by actor.
        """
        pass

    def playlist_changed(self, playlist):
        """
        Called whenever a playlist is changed.

        *MAY* be implemented by actor.

        :param playlist: the changed playlist
        :type playlist: :class:`mopidy.models.Playlist`
        """
        pass

    def options_changed(self):
        """
        Called whenever an option is changed.

        *MAY* be implemented by actor.
        """
        pass

    def volume_changed(self, volume):
        """
        Called whenever the volume is changed.

        *MAY* be implemented by actor.

        :param volume: the new volume in the range [0..100]
        :type volume: int
        """
        pass

    def mute_changed(self, mute):
        """
        Called whenever the mute state is changed.

        *MAY* be implemented by actor.

        :param mute: the new mute state
        :type mute: boolean
        """
        pass

    def seeked(self, time_position):
        """
        Called whenever the time position changes by an unexpected amount, e.g.
        at seek to a new time position.

        *MAY* be implemented by actor.

        :param time_position: the position that was seeked to in milliseconds
        :type time_position: int
        """
        pass

########NEW FILE########
__FILENAME__ = playback
from __future__ import unicode_literals

import logging
import urlparse

from mopidy.audio import PlaybackState
from mopidy.core import listener


logger = logging.getLogger(__name__)


class PlaybackController(object):
    pykka_traversable = True

    def __init__(self, audio, backends, core):
        self.audio = audio
        self.backends = backends
        self.core = core

        self._state = PlaybackState.STOPPED
        self._volume = None
        self._mute = False

    def _get_backend(self):
        if self.current_tl_track is None:
            return None
        uri = self.current_tl_track.track.uri
        uri_scheme = urlparse.urlparse(uri).scheme
        return self.backends.with_playback.get(uri_scheme, None)

    # Properties

    def get_current_tl_track(self):
        return self.current_tl_track

    current_tl_track = None
    """
    The currently playing or selected :class:`mopidy.models.TlTrack`, or
    :class:`None`.
    """

    def get_current_track(self):
        return self.current_tl_track and self.current_tl_track.track

    current_track = property(get_current_track)
    """
    The currently playing or selected :class:`mopidy.models.Track`.

    Read-only. Extracted from :attr:`current_tl_track` for convenience.
    """

    def get_state(self):
        return self._state

    def set_state(self, new_state):
        (old_state, self._state) = (self.state, new_state)
        logger.debug('Changing state: %s -> %s', old_state, new_state)

        self._trigger_playback_state_changed(old_state, new_state)

    state = property(get_state, set_state)
    """
    The playback state. Must be :attr:`PLAYING`, :attr:`PAUSED`, or
    :attr:`STOPPED`.

    Possible states and transitions:

    .. digraph:: state_transitions

        "STOPPED" -> "PLAYING" [ label="play" ]
        "STOPPED" -> "PAUSED" [ label="pause" ]
        "PLAYING" -> "STOPPED" [ label="stop" ]
        "PLAYING" -> "PAUSED" [ label="pause" ]
        "PLAYING" -> "PLAYING" [ label="play" ]
        "PAUSED" -> "PLAYING" [ label="resume" ]
        "PAUSED" -> "STOPPED" [ label="stop" ]
    """

    def get_time_position(self):
        backend = self._get_backend()
        if backend:
            return backend.playback.get_time_position().get()
        else:
            return 0

    time_position = property(get_time_position)
    """Time position in milliseconds."""

    def get_volume(self):
        if self.audio:
            return self.audio.get_volume().get()
        else:
            # For testing
            return self._volume

    def set_volume(self, volume):
        if self.audio:
            self.audio.set_volume(volume)
        else:
            # For testing
            self._volume = volume

        self._trigger_volume_changed(volume)

    volume = property(get_volume, set_volume)
    """Volume as int in range [0..100] or :class:`None`"""

    def get_mute(self):
        if self.audio:
            return self.audio.get_mute().get()
        else:
            # For testing
            return self._mute

    def set_mute(self, value):
        value = bool(value)
        if self.audio:
            self.audio.set_mute(value)
        else:
            # For testing
            self._mute = value

        self._trigger_mute_changed(value)

    mute = property(get_mute, set_mute)
    """Mute state as a :class:`True` if muted, :class:`False` otherwise"""

    # Methods

    def change_track(self, tl_track, on_error_step=1):
        """
        Change to the given track, keeping the current playback state.

        :param tl_track: track to change to
        :type tl_track: :class:`mopidy.models.TlTrack` or :class:`None`
        :param on_error_step: direction to step at play error, 1 for next
            track (default), -1 for previous track
        :type on_error_step: int, -1 or 1
        """
        old_state = self.state
        self.stop()
        self.current_tl_track = tl_track
        if old_state == PlaybackState.PLAYING:
            self.play(on_error_step=on_error_step)
        elif old_state == PlaybackState.PAUSED:
            self.pause()

    def on_end_of_track(self):
        """
        Tell the playback controller that end of track is reached.

        Used by event handler in :class:`mopidy.core.Core`.
        """
        if self.state == PlaybackState.STOPPED:
            return

        original_tl_track = self.current_tl_track
        next_tl_track = self.core.tracklist.eot_track(original_tl_track)

        if next_tl_track:
            self.change_track(next_tl_track)
        else:
            self.stop(clear_current_track=True)

        self.core.tracklist.mark_played(original_tl_track)

    def on_tracklist_change(self):
        """
        Tell the playback controller that the current playlist has changed.

        Used by :class:`mopidy.core.TracklistController`.
        """
        if self.current_tl_track not in self.core.tracklist.tl_tracks:
            self.stop(clear_current_track=True)

    def next(self):
        """
        Change to the next track.

        The current playback state will be kept. If it was playing, playing
        will continue. If it was paused, it will still be paused, etc.
        """
        tl_track = self.core.tracklist.next_track(self.current_tl_track)
        if tl_track:
            self.change_track(tl_track)
        else:
            self.stop(clear_current_track=True)

    def pause(self):
        """Pause playback."""
        backend = self._get_backend()
        if not backend or backend.playback.pause().get():
            self.state = PlaybackState.PAUSED
            self._trigger_track_playback_paused()

    def play(self, tl_track=None, on_error_step=1):
        """
        Play the given track, or if the given track is :class:`None`, play the
        currently active track.

        :param tl_track: track to play
        :type tl_track: :class:`mopidy.models.TlTrack` or :class:`None`
        :param on_error_step: direction to step at play error, 1 for next
            track (default), -1 for previous track
        :type on_error_step: int, -1 or 1
        """

        assert on_error_step in (-1, 1)

        if tl_track is None:
            if self.state == PlaybackState.PAUSED:
                return self.resume()

            if self.current_tl_track is not None:
                tl_track = self.current_tl_track
            else:
                if on_error_step == 1:
                    tl_track = self.core.tracklist.next_track(tl_track)
                elif on_error_step == -1:
                    tl_track = self.core.tracklist.previous_track(tl_track)

            if tl_track is None:
                return

        assert tl_track in self.core.tracklist.tl_tracks

        if self.state == PlaybackState.PLAYING:
            self.stop()

        self.current_tl_track = tl_track
        self.state = PlaybackState.PLAYING
        backend = self._get_backend()
        success = backend and backend.playback.play(tl_track.track).get()

        if success:
            self.core.tracklist.mark_playing(tl_track)
            self._trigger_track_playback_started()
        else:
            self.core.tracklist.mark_unplayable(tl_track)
            if on_error_step == 1:
                # TODO: can cause an endless loop for single track repeat.
                self.next()
            elif on_error_step == -1:
                self.previous()

    def previous(self):
        """
        Change to the previous track.

        The current playback state will be kept. If it was playing, playing
        will continue. If it was paused, it will still be paused, etc.
        """
        tl_track = self.current_tl_track
        self.change_track(
            self.core.tracklist.previous_track(tl_track), on_error_step=-1)

    def resume(self):
        """If paused, resume playing the current track."""
        if self.state != PlaybackState.PAUSED:
            return
        backend = self._get_backend()
        if backend and backend.playback.resume().get():
            self.state = PlaybackState.PLAYING
            self._trigger_track_playback_resumed()

    def seek(self, time_position):
        """
        Seeks to time position given in milliseconds.

        :param time_position: time position in milliseconds
        :type time_position: int
        :rtype: :class:`True` if successful, else :class:`False`
        """
        if not self.core.tracklist.tracks:
            return False

        if self.state == PlaybackState.STOPPED:
            self.play()
        elif self.state == PlaybackState.PAUSED:
            self.resume()

        if time_position < 0:
            time_position = 0
        elif time_position > self.current_track.length:
            self.next()
            return True

        backend = self._get_backend()
        if not backend:
            return False

        success = backend.playback.seek(time_position).get()
        if success:
            self._trigger_seeked(time_position)
        return success

    def stop(self, clear_current_track=False):
        """
        Stop playing.

        :param clear_current_track: whether to clear the current track _after_
            stopping
        :type clear_current_track: boolean
        """
        if self.state != PlaybackState.STOPPED:
            backend = self._get_backend()
            time_position_before_stop = self.time_position
            if not backend or backend.playback.stop().get():
                self.state = PlaybackState.STOPPED
                self._trigger_track_playback_ended(time_position_before_stop)
        if clear_current_track:
            self.current_tl_track = None

    def _trigger_track_playback_paused(self):
        logger.debug('Triggering track playback paused event')
        if self.current_track is None:
            return
        listener.CoreListener.send(
            'track_playback_paused',
            tl_track=self.current_tl_track, time_position=self.time_position)

    def _trigger_track_playback_resumed(self):
        logger.debug('Triggering track playback resumed event')
        if self.current_track is None:
            return
        listener.CoreListener.send(
            'track_playback_resumed',
            tl_track=self.current_tl_track, time_position=self.time_position)

    def _trigger_track_playback_started(self):
        logger.debug('Triggering track playback started event')
        if self.current_tl_track is None:
            return
        listener.CoreListener.send(
            'track_playback_started',
            tl_track=self.current_tl_track)

    def _trigger_track_playback_ended(self, time_position_before_stop):
        logger.debug('Triggering track playback ended event')
        if self.current_tl_track is None:
            return
        listener.CoreListener.send(
            'track_playback_ended',
            tl_track=self.current_tl_track,
            time_position=time_position_before_stop)

    def _trigger_playback_state_changed(self, old_state, new_state):
        logger.debug('Triggering playback state change event')
        listener.CoreListener.send(
            'playback_state_changed',
            old_state=old_state, new_state=new_state)

    def _trigger_volume_changed(self, volume):
        logger.debug('Triggering volume changed event')
        listener.CoreListener.send('volume_changed', volume=volume)

    def _trigger_mute_changed(self, mute):
        logger.debug('Triggering mute changed event')
        listener.CoreListener.send('mute_changed', mute=mute)

    def _trigger_seeked(self, time_position):
        logger.debug('Triggering seeked event')
        listener.CoreListener.send('seeked', time_position=time_position)

########NEW FILE########
__FILENAME__ = playlists
from __future__ import unicode_literals

import itertools
import urlparse

import pykka

from . import listener


class PlaylistsController(object):
    pykka_traversable = True

    def __init__(self, backends, core):
        self.backends = backends
        self.core = core

    def get_playlists(self, include_tracks=True):
        futures = [b.playlists.playlists
                   for b in self.backends.with_playlists.values()]
        results = pykka.get_all(futures)
        playlists = list(itertools.chain(*results))
        if not include_tracks:
            playlists = [p.copy(tracks=[]) for p in playlists]
        return playlists

    playlists = property(get_playlists)
    """
    The available playlists.

    Read-only. List of :class:`mopidy.models.Playlist`.
    """

    def create(self, name, uri_scheme=None):
        """
        Create a new playlist.

        If ``uri_scheme`` matches an URI scheme handled by a current backend,
        that backend is asked to create the playlist. If ``uri_scheme`` is
        :class:`None` or doesn't match a current backend, the first backend is
        asked to create the playlist.

        All new playlists should be created by calling this method, and **not**
        by creating new instances of :class:`mopidy.models.Playlist`.

        :param name: name of the new playlist
        :type name: string
        :param uri_scheme: use the backend matching the URI scheme
        :type uri_scheme: string
        :rtype: :class:`mopidy.models.Playlist`
        """
        if uri_scheme in self.backends.with_playlists:
            backend = self.backends.with_playlists[uri_scheme]
        else:
            # TODO: this fallback looks suspicious
            backend = self.backends.with_playlists.values()[0]
        playlist = backend.playlists.create(name).get()
        listener.CoreListener.send('playlist_changed', playlist=playlist)
        return playlist

    def delete(self, uri):
        """
        Delete playlist identified by the URI.

        If the URI doesn't match the URI schemes handled by the current
        backends, nothing happens.

        :param uri: URI of the playlist to delete
        :type uri: string
        """
        uri_scheme = urlparse.urlparse(uri).scheme
        backend = self.backends.with_playlists.get(uri_scheme, None)
        if backend:
            backend.playlists.delete(uri).get()

    def filter(self, criteria=None, **kwargs):
        """
        Filter playlists by the given criterias.

        Examples::

            # Returns track with name 'a'
            filter({'name': 'a'})
            filter(name='a')

            # Returns track with URI 'xyz'
            filter({'uri': 'xyz'})
            filter(uri='xyz')

            # Returns track with name 'a' and URI 'xyz'
            filter({'name': 'a', 'uri': 'xyz'})
            filter(name='a', uri='xyz')

        :param criteria: one or more criteria to match by
        :type criteria: dict
        :rtype: list of :class:`mopidy.models.Playlist`
        """
        criteria = criteria or kwargs
        matches = self.playlists
        for (key, value) in criteria.iteritems():
            matches = filter(lambda p: getattr(p, key) == value, matches)
        return matches

    def lookup(self, uri):
        """
        Lookup playlist with given URI in both the set of playlists and in any
        other playlist sources. Returns :class:`None` if not found.

        :param uri: playlist URI
        :type uri: string
        :rtype: :class:`mopidy.models.Playlist` or :class:`None`
        """
        uri_scheme = urlparse.urlparse(uri).scheme
        backend = self.backends.with_playlists.get(uri_scheme, None)
        if backend:
            return backend.playlists.lookup(uri).get()
        else:
            return None

    def refresh(self, uri_scheme=None):
        """
        Refresh the playlists in :attr:`playlists`.

        If ``uri_scheme`` is :class:`None`, all backends are asked to refresh.
        If ``uri_scheme`` is an URI scheme handled by a backend, only that
        backend is asked to refresh. If ``uri_scheme`` doesn't match any
        current backend, nothing happens.

        :param uri_scheme: limit to the backend matching the URI scheme
        :type uri_scheme: string
        """
        if uri_scheme is None:
            futures = [b.playlists.refresh()
                       for b in self.backends.with_playlists.values()]
            pykka.get_all(futures)
            listener.CoreListener.send('playlists_loaded')
        else:
            backend = self.backends.with_playlists.get(uri_scheme, None)
            if backend:
                backend.playlists.refresh().get()
                listener.CoreListener.send('playlists_loaded')

    def save(self, playlist):
        """
        Save the playlist.

        For a playlist to be saveable, it must have the ``uri`` attribute set.
        You should not set the ``uri`` atribute yourself, but use playlist
        objects returned by :meth:`create` or retrieved from :attr:`playlists`,
        which will always give you saveable playlists.

        The method returns the saved playlist. The return playlist may differ
        from the saved playlist. E.g. if the playlist name was changed, the
        returned playlist may have a different URI. The caller of this method
        should throw away the playlist sent to this method, and use the
        returned playlist instead.

        If the playlist's URI isn't set or doesn't match the URI scheme of a
        current backend, nothing is done and :class:`None` is returned.

        :param playlist: the playlist
        :type playlist: :class:`mopidy.models.Playlist`
        :rtype: :class:`mopidy.models.Playlist` or :class:`None`
        """
        if playlist.uri is None:
            return
        uri_scheme = urlparse.urlparse(playlist.uri).scheme
        backend = self.backends.with_playlists.get(uri_scheme, None)
        if backend:
            playlist = backend.playlists.save(playlist).get()
            listener.CoreListener.send('playlist_changed', playlist=playlist)
            return playlist

########NEW FILE########
__FILENAME__ = tracklist
from __future__ import unicode_literals

import collections
import logging
import random

from mopidy.core import listener
from mopidy.models import TlTrack


logger = logging.getLogger(__name__)


class TracklistController(object):
    pykka_traversable = True

    def __init__(self, core):
        self.core = core
        self._next_tlid = 0
        self._tl_tracks = []
        self._version = 0

        self._shuffled = []

    # Properties

    def get_tl_tracks(self):
        return self._tl_tracks[:]

    tl_tracks = property(get_tl_tracks)
    """
    List of :class:`mopidy.models.TlTrack`.

    Read-only.
    """

    def get_tracks(self):
        return [tl_track.track for tl_track in self._tl_tracks]

    tracks = property(get_tracks)
    """
    List of :class:`mopidy.models.Track` in the tracklist.

    Read-only.
    """

    def get_length(self):
        return len(self._tl_tracks)

    length = property(get_length)
    """Length of the tracklist."""

    def get_version(self):
        return self._version

    def _increase_version(self):
        self._version += 1
        self.core.playback.on_tracklist_change()
        self._trigger_tracklist_changed()

    version = property(get_version)
    """
    The tracklist version.

    Read-only. Integer which is increased every time the tracklist is changed.
    Is not reset before Mopidy is restarted.
    """

    def get_consume(self):
        return getattr(self, '_consume', False)

    def set_consume(self, value):
        if self.get_consume() != value:
            self._trigger_options_changed()
        return setattr(self, '_consume', value)

    consume = property(get_consume, set_consume)
    """
    :class:`True`
        Tracks are removed from the playlist when they have been played.
    :class:`False`
        Tracks are not removed from the playlist.
    """

    def get_random(self):
        return getattr(self, '_random', False)

    def set_random(self, value):
        if self.get_random() != value:
            self._trigger_options_changed()
        if value:
            self._shuffled = self.tl_tracks
            random.shuffle(self._shuffled)
        return setattr(self, '_random', value)

    random = property(get_random, set_random)
    """
    :class:`True`
        Tracks are selected at random from the playlist.
    :class:`False`
        Tracks are played in the order of the playlist.
    """

    def get_repeat(self):
        return getattr(self, '_repeat', False)

    def set_repeat(self, value):
        if self.get_repeat() != value:
            self._trigger_options_changed()
        return setattr(self, '_repeat', value)

    repeat = property(get_repeat, set_repeat)
    """
    :class:`True`
        The current playlist is played repeatedly. To repeat a single track,
        select both :attr:`repeat` and :attr:`single`.
    :class:`False`
        The current playlist is played once.
    """

    def get_single(self):
        return getattr(self, '_single', False)

    def set_single(self, value):
        if self.get_single() != value:
            self._trigger_options_changed()
        return setattr(self, '_single', value)

    single = property(get_single, set_single)
    """
    :class:`True`
        Playback is stopped after current song, unless in :attr:`repeat`
        mode.
    :class:`False`
        Playback continues after current song.
    """

    # Methods

    def index(self, tl_track):
        """
        The position of the given track in the tracklist.

        :param tl_track: the track to find the index of
        :type tl_track: :class:`mopidy.models.TlTrack`
        :rtype: :class:`int` or :class:`None`
        """
        try:
            return self._tl_tracks.index(tl_track)
        except ValueError:
            return None

    def eot_track(self, tl_track):
        """
        The track that will be played after the given track.

        Not necessarily the same track as :meth:`next_track`.

        :param tl_track: the reference track
        :type tl_track: :class:`mopidy.models.TlTrack` or :class:`None`
        :rtype: :class:`mopidy.models.TlTrack` or :class:`None`
        """
        if self.single and self.repeat:
            return tl_track
        elif self.single:
            return None

        # Current difference between next and EOT handling is that EOT needs to
        # handle "single", with that out of the way the rest of the logic is
        # shared.
        return self.next_track(tl_track)

    def next_track(self, tl_track):
        """
        The track that will be played if calling
        :meth:`mopidy.core.PlaybackController.next()`.

        For normal playback this is the next track in the playlist. If repeat
        is enabled the next track can loop around the playlist. When random is
        enabled this should be a random track, all tracks should be played once
        before the list repeats.

        :param tl_track: the reference track
        :type tl_track: :class:`mopidy.models.TlTrack` or :class:`None`
        :rtype: :class:`mopidy.models.TlTrack` or :class:`None`
        """

        if not self.tl_tracks:
            return None

        if self.random and not self._shuffled:
            if self.repeat or not tl_track:
                logger.debug('Shuffling tracks')
                self._shuffled = self.tl_tracks
                random.shuffle(self._shuffled)

        if self.random:
            try:
                return self._shuffled[0]
            except IndexError:
                return None

        if tl_track is None:
            return self.tl_tracks[0]

        next_index = self.index(tl_track) + 1
        if self.repeat:
            next_index %= len(self.tl_tracks)

        try:
            return self.tl_tracks[next_index]
        except IndexError:
            return None

    def previous_track(self, tl_track):
        """
        Returns the track that will be played if calling
        :meth:`mopidy.core.PlaybackController.previous()`.

        For normal playback this is the previous track in the playlist. If
        random and/or consume is enabled it should return the current track
        instead.

        :param tl_track: the reference track
        :type tl_track: :class:`mopidy.models.TlTrack` or :class:`None`
        :rtype: :class:`mopidy.models.TlTrack` or :class:`None`
        """
        if self.repeat or self.consume or self.random:
            return tl_track

        position = self.index(tl_track)

        if position in (None, 0):
            return None

        return self.tl_tracks[position - 1]

    def add(self, tracks=None, at_position=None, uri=None):
        """
        Add the track or list of tracks to the tracklist.

        If ``uri`` is given instead of ``tracks``, the URI is looked up in the
        library and the resulting tracks are added to the tracklist.

        If ``at_position`` is given, the tracks placed at the given position in
        the tracklist. If ``at_position`` is not given, the tracks are appended
        to the end of the tracklist.

        Triggers the :meth:`mopidy.core.CoreListener.tracklist_changed` event.

        :param tracks: tracks to add
        :type tracks: list of :class:`mopidy.models.Track`
        :param at_position: position in tracklist to add track
        :type at_position: int or :class:`None`
        :param uri: URI for tracks to add
        :type uri: string
        :rtype: list of :class:`mopidy.models.TlTrack`
        """
        assert tracks is not None or uri is not None, \
            'tracks or uri must be provided'

        if tracks is None and uri is not None:
            tracks = self.core.library.lookup(uri)

        tl_tracks = []

        for track in tracks:
            tl_track = TlTrack(self._next_tlid, track)
            self._next_tlid += 1
            if at_position is not None:
                self._tl_tracks.insert(at_position, tl_track)
                at_position += 1
            else:
                self._tl_tracks.append(tl_track)
            tl_tracks.append(tl_track)

        if tl_tracks:
            self._increase_version()

        return tl_tracks

    def clear(self):
        """
        Clear the tracklist.

        Triggers the :meth:`mopidy.core.CoreListener.tracklist_changed` event.
        """
        self._tl_tracks = []
        self._increase_version()

    def filter(self, criteria=None, **kwargs):
        """
        Filter the tracklist by the given criterias.

        A criteria consists of a model field to check and a list of values to
        compare it against. If the model field matches one of the values, it
        may be returned.

        Only tracks that matches all the given criterias are returned.

        Examples::

            # Returns tracks with TLIDs 1, 2, 3, or 4 (tracklist ID)
            filter({'tlid': [1, 2, 3, 4]})
            filter(tlid=[1, 2, 3, 4])

            # Returns track with IDs 1, 5, or 7
            filter({'id': [1, 5, 7]})
            filter(id=[1, 5, 7])

            # Returns track with URIs 'xyz' or 'abc'
            filter({'uri': ['xyz', 'abc']})
            filter(uri=['xyz', 'abc'])

            # Returns tracks with ID 1 and URI 'xyz'
            filter({'id': [1], 'uri': ['xyz']})
            filter(id=[1], uri=['xyz'])

            # Returns track with a matching ID (1, 3 or 6) and a matching URI
            # ('xyz' or 'abc')
            filter({'id': [1, 3, 6], 'uri': ['xyz', 'abc']})
            filter(id=[1, 3, 6], uri=['xyz', 'abc'])

        :param criteria: on or more criteria to match by
        :type criteria: dict, of (string, list) pairs
        :rtype: list of :class:`mopidy.models.TlTrack`
        """
        criteria = criteria or kwargs
        matches = self._tl_tracks
        for (key, values) in criteria.iteritems():
            if (not isinstance(values, collections.Iterable)
                    or isinstance(values, basestring)):
                # Fail hard if anyone is using the <0.17 calling style
                raise ValueError('Filter values must be iterable: %r' % values)
            if key == 'tlid':
                matches = filter(lambda ct: ct.tlid in values, matches)
            else:
                matches = filter(
                    lambda ct: getattr(ct.track, key) in values, matches)
        return matches

    def move(self, start, end, to_position):
        """
        Move the tracks in the slice ``[start:end]`` to ``to_position``.

        Triggers the :meth:`mopidy.core.CoreListener.tracklist_changed` event.

        :param start: position of first track to move
        :type start: int
        :param end: position after last track to move
        :type end: int
        :param to_position: new position for the tracks
        :type to_position: int
        """
        if start == end:
            end += 1

        tl_tracks = self._tl_tracks

        assert start < end, 'start must be smaller than end'
        assert start >= 0, 'start must be at least zero'
        assert end <= len(tl_tracks), \
            'end can not be larger than tracklist length'
        assert to_position >= 0, 'to_position must be at least zero'
        assert to_position <= len(tl_tracks), \
            'to_position can not be larger than tracklist length'

        new_tl_tracks = tl_tracks[:start] + tl_tracks[end:]
        for tl_track in tl_tracks[start:end]:
            new_tl_tracks.insert(to_position, tl_track)
            to_position += 1
        self._tl_tracks = new_tl_tracks
        self._increase_version()

    def remove(self, criteria=None, **kwargs):
        """
        Remove the matching tracks from the tracklist.

        Uses :meth:`filter()` to lookup the tracks to remove.

        Triggers the :meth:`mopidy.core.CoreListener.tracklist_changed` event.

        :param criteria: on or more criteria to match by
        :type criteria: dict
        :rtype: list of :class:`mopidy.models.TlTrack` that was removed
        """
        tl_tracks = self.filter(criteria, **kwargs)
        for tl_track in tl_tracks:
            position = self._tl_tracks.index(tl_track)
            del self._tl_tracks[position]
        self._increase_version()
        return tl_tracks

    def shuffle(self, start=None, end=None):
        """
        Shuffles the entire tracklist. If ``start`` and ``end`` is given only
        shuffles the slice ``[start:end]``.

        Triggers the :meth:`mopidy.core.CoreListener.tracklist_changed` event.

        :param start: position of first track to shuffle
        :type start: int or :class:`None`
        :param end: position after last track to shuffle
        :type end: int or :class:`None`
        """
        tl_tracks = self._tl_tracks

        if start is not None and end is not None:
            assert start < end, 'start must be smaller than end'

        if start is not None:
            assert start >= 0, 'start must be at least zero'

        if end is not None:
            assert end <= len(tl_tracks), 'end can not be larger than ' + \
                'tracklist length'

        before = tl_tracks[:start or 0]
        shuffled = tl_tracks[start:end]
        after = tl_tracks[end or len(tl_tracks):]
        random.shuffle(shuffled)
        self._tl_tracks = before + shuffled + after
        self._increase_version()

    def slice(self, start, end):
        """
        Returns a slice of the tracklist, limited by the given start and end
        positions.

        :param start: position of first track to include in slice
        :type start: int
        :param end: position after last track to include in slice
        :type end: int
        :rtype: :class:`mopidy.models.TlTrack`
        """
        return self._tl_tracks[start:end]

    def mark_playing(self, tl_track):
        """Private method used by :class:`mopidy.core.PlaybackController`."""
        if self.random and tl_track in self._shuffled:
            self._shuffled.remove(tl_track)

    def mark_unplayable(self, tl_track):
        """Private method used by :class:`mopidy.core.PlaybackController`."""
        logger.warning('Track is not playable: %s', tl_track.track.uri)
        if self.random and tl_track in self._shuffled:
            self._shuffled.remove(tl_track)

    def mark_played(self, tl_track):
        """Private method used by :class:`mopidy.core.PlaybackController`."""
        if not self.consume:
            return False
        self.remove(tlid=[tl_track.tlid])
        return True

    def _trigger_tracklist_changed(self):
        if self.random:
            self._shuffled = self.tl_tracks
            random.shuffle(self._shuffled)
        else:
            self._shuffled = []

        logger.debug('Triggering event: tracklist_changed()')
        listener.CoreListener.send('tracklist_changed')

    def _trigger_options_changed(self):
        logger.debug('Triggering options changed event')
        listener.CoreListener.send('options_changed')

########NEW FILE########
__FILENAME__ = exceptions
from __future__ import unicode_literals


class MopidyException(Exception):
    def __init__(self, message, *args, **kwargs):
        super(MopidyException, self).__init__(message, *args, **kwargs)
        self._message = message

    @property
    def message(self):
        """Reimplement message field that was deprecated in Python 2.6"""
        return self._message

    @message.setter  # noqa
    def message(self, message):
        self._message = message


class ExtensionError(MopidyException):
    pass


class ScannerError(MopidyException):
    pass

########NEW FILE########
__FILENAME__ = ext
from __future__ import unicode_literals

import collections
import logging

import pkg_resources

from mopidy import config as config_lib, exceptions


logger = logging.getLogger(__name__)


class Extension(object):
    """Base class for Mopidy extensions"""

    dist_name = None
    """The extension's distribution name, as registered on PyPI

    Example: ``Mopidy-Soundspot``
    """

    ext_name = None
    """The extension's short name, as used in setup.py and as config section
    name

    Example: ``soundspot``
    """

    version = None
    """The extension's version

    Should match the :attr:`__version__` attribute on the extension's main
    Python module and the version registered on PyPI.
    """

    def get_default_config(self):
        """The extension's default config as a bytestring

        :returns: bytes or unicode
        """
        raise NotImplementedError(
            'Add at least a config section with "enabled = true"')

    def get_config_schema(self):
        """The extension's config validation schema

        :returns: :class:`~mopidy.config.schema.ExtensionConfigSchema`
        """
        schema = config_lib.ConfigSchema(self.ext_name)
        schema['enabled'] = config_lib.Boolean()
        return schema

    def get_command(self):
        """Command to expose to command line users running mopidy.

        :returns:
          Instance of a :class:`~mopidy.commands.Command` class.
        """
        pass

    def validate_environment(self):
        """Checks if the extension can run in the current environment

        For example, this method can be used to check if all dependencies that
        are needed are installed. If a problem is found, raise
        :exc:`~mopidy.exceptions.ExtensionError` with a message explaining the
        issue.

        :raises: :exc:`~mopidy.exceptions.ExtensionError`
        :returns: :class:`None`
        """
        pass

    def setup(self, registry):
        """
        Register the extension's components in the extension :class:`Registry`.

        For example, to register a backend::

            def setup(self, registry):
                from .backend import SoundspotBackend
                registry.add('backend', SoundspotBackend)

        See :class:`Registry` for a list of registry keys with a special
        meaning. Mopidy will instantiate and start any classes registered under
        the ``frontend`` and ``backend`` registry keys.

        This method can also be used for other setup tasks not involving the
        extension registry. For example, to register custom GStreamer
        elements::

            def setup(self, registry):
                from .mixer import SoundspotMixer
                gobject.type_register(SoundspotMixer)
                gst.element_register(
                    SoundspotMixer, 'soundspotmixer', gst.RANK_MARGINAL)

        :param registry: the extension registry
        :type registry: :class:`Registry`
        """
        pass


class Registry(collections.Mapping):
    """Registry of components provided by Mopidy extensions.

    Passed to the :meth:`~Extension.setup` method of all extensions. The
    registry can be used like a dict of string keys and lists.

    Some keys have a special meaning, including, but not limited to:

    - ``backend`` is used for Mopidy backend classes.
    - ``frontend`` is used for Mopidy frontend classes.
    - ``local:library`` is used for Mopidy-Local libraries.

    Extensions can use the registry for allow other to extend the extension
    itself. For example the ``Mopidy-Local`` use the ``local:library`` key to
    allow other extensions to register library providers for ``Mopidy-Local``
    to use. Extensions should namespace custom keys with the extension's
    :attr:`~Extension.ext_name`, e.g. ``local:foo`` or ``http:bar``.
    """

    def __init__(self):
        self._registry = {}

    def add(self, name, cls):
        """Add a component to the registry.

        Multiple classes can be registered to the same name.
        """
        self._registry.setdefault(name, []).append(cls)

    def __getitem__(self, name):
        return self._registry.setdefault(name, [])

    def __iter__(self):
        return iter(self._registry)

    def __len__(self):
        return len(self._registry)


def load_extensions():
    """Find all installed extensions.

    :returns: list of installed extensions
    """

    installed_extensions = []

    for entry_point in pkg_resources.iter_entry_points('mopidy.ext'):
        logger.debug('Loading entry point: %s', entry_point)
        extension_class = entry_point.load(require=False)
        extension = extension_class()
        extension.entry_point = entry_point
        installed_extensions.append(extension)
        logger.debug(
            'Loaded extension: %s %s', extension.dist_name, extension.version)

    names = (e.ext_name for e in installed_extensions)
    logger.debug('Discovered extensions: %s', ', '.join(names))
    return installed_extensions


def validate_extension(extension):
    """Verify extension's dependencies and environment.

    :param extensions: an extension to check
    :returns: if extension should be run
    """

    logger.debug('Validating extension: %s', extension.ext_name)

    if extension.ext_name != extension.entry_point.name:
        logger.warning(
            'Disabled extension %(ep)s: entry point name (%(ep)s) '
            'does not match extension name (%(ext)s)',
            {'ep': extension.entry_point.name, 'ext': extension.ext_name})
        return False

    try:
        extension.entry_point.require()
    except pkg_resources.DistributionNotFound as ex:
        logger.info(
            'Disabled extension %s: Dependency %s not found',
            extension.ext_name, ex)
        return False
    except pkg_resources.VersionConflict as ex:
        found, required = ex.args
        logger.info(
            'Disabled extension %s: %s required, but found %s at %s',
            extension.ext_name, required, found, found.location)
        return False

    try:
        extension.validate_environment()
    except exceptions.ExtensionError as ex:
        logger.info(
            'Disabled extension %s: %s', extension.ext_name, ex.message)
        return False

    return True

########NEW FILE########
__FILENAME__ = actor
from __future__ import unicode_literals

import json
import logging
import os
import threading

import pykka

import tornado.ioloop
import tornado.web
import tornado.websocket

from mopidy import models, zeroconf
from mopidy.core import CoreListener
from mopidy.http import handlers


logger = logging.getLogger(__name__)


class HttpFrontend(pykka.ThreadingActor, CoreListener):
    routers = []

    def __init__(self, config, core):
        super(HttpFrontend, self).__init__()
        self.config = config
        self.core = core

        self.hostname = config['http']['hostname']
        self.port = config['http']['port']
        self.zeroconf_name = config['http']['zeroconf']
        self.zeroconf_service = None
        self.app = None

    def on_start(self):
        threading.Thread(target=self._startup).start()
        self._publish_zeroconf()

    def on_stop(self):
        self._unpublish_zeroconf()
        tornado.ioloop.IOLoop.instance().add_callback(self._shutdown)

    def _startup(self):
        logger.debug('Starting HTTP server')
        self.app = tornado.web.Application(self._get_request_handlers())
        self.app.listen(self.port, self.hostname)
        logger.info(
            'HTTP server running at http://%s:%s', self.hostname, self.port)
        tornado.ioloop.IOLoop.instance().start()

    def _shutdown(self):
        logger.debug('Stopping HTTP server')
        tornado.ioloop.IOLoop.instance().stop()
        logger.debug('Stopped HTTP server')

    def on_event(self, name, **data):
        event = data
        event['event'] = name
        message = json.dumps(event, cls=models.ModelJSONEncoder)
        handlers.WebSocketHandler.broadcast(message)

    def _get_request_handlers(self):
        request_handlers = []

        request_handlers.extend(self._get_extension_request_handlers())

        # Either default Mopidy or user defined path to files
        static_dir = self.config['http']['static_dir']
        data_dir = os.path.join(os.path.dirname(__file__), 'data')
        root_handler = (r'/(.*)', handlers.StaticFileHandler, {
            'path': static_dir if static_dir else data_dir,
            'default_filename': 'index.html'
        })
        request_handlers.append(root_handler)

        logger.debug(
            'HTTP routes from extensions: %s',
            list((l[0], l[1]) for l in request_handlers))
        return request_handlers

    def _get_extension_request_handlers(self):
        result = []
        for router_class in self.routers:
            router = router_class(self.config, self.core)
            request_handlers = router.get_request_handlers()
            for handler in request_handlers:
                handler = list(handler)
                handler[0] = '/%s%s' % (router.name, handler[0])
                result.append(tuple(handler))
            logger.info('Loaded HTTP extension: %s', router_class.__name__)
        return result

    def _publish_zeroconf(self):
        if not self.zeroconf_name:
            return

        self.zeroconf_http_service = zeroconf.Zeroconf(
            stype='_http._tcp', name=self.zeroconf_name,
            host=self.hostname, port=self.port)

        if self.zeroconf_http_service.publish():
            logger.debug(
                'Registered HTTP with Zeroconf as "%s"',
                self.zeroconf_http_service.name)
        else:
            logger.debug('Registering HTTP with Zeroconf failed.')

        self.zeroconf_mopidy_http_service = zeroconf.Zeroconf(
            stype='_mopidy-http._tcp', name=self.zeroconf_name,
            host=self.hostname, port=self.port)

        if self.zeroconf_mopidy_http_service.publish():
            logger.debug(
                'Registered Mopidy-HTTP with Zeroconf as "%s"',
                self.zeroconf_mopidy_http_service.name)
        else:
            logger.debug('Registering Mopidy-HTTP with Zeroconf failed.')

    def _unpublish_zeroconf(self):
        if self.zeroconf_http_service:
            self.zeroconf_http_service.unpublish()

        if self.zeroconf_mopidy_http_service:
            self.zeroconf_mopidy_http_service.unpublish()

########NEW FILE########
__FILENAME__ = handlers
from __future__ import unicode_literals

import logging
import os

import tornado.escape
import tornado.web
import tornado.websocket

import mopidy
from mopidy import core, http, models
from mopidy.utils import jsonrpc


logger = logging.getLogger(__name__)


class MopidyHttpRouter(http.Router):
    name = 'mopidy'

    def get_request_handlers(self):
        data_dir = os.path.join(os.path.dirname(__file__), 'data')
        return [
            (r'/ws/?', WebSocketHandler, {'core': self.core}),
            (r'/rpc', JsonRpcHandler, {'core': self.core}),
            (r'/(.*)', StaticFileHandler, {
                'path': data_dir, 'default_filename': 'mopidy.html'
            }),
        ]


def make_jsonrpc_wrapper(core_actor):
    inspector = jsonrpc.JsonRpcInspector(
        objects={
            'core.get_uri_schemes': core.Core.get_uri_schemes,
            'core.get_version': core.Core.get_version,
            'core.library': core.LibraryController,
            'core.playback': core.PlaybackController,
            'core.playlists': core.PlaylistsController,
            'core.tracklist': core.TracklistController,
        })
    return jsonrpc.JsonRpcWrapper(
        objects={
            'core.describe': inspector.describe,
            'core.get_uri_schemes': core_actor.get_uri_schemes,
            'core.get_version': core_actor.get_version,
            'core.library': core_actor.library,
            'core.playback': core_actor.playback,
            'core.playlists': core_actor.playlists,
            'core.tracklist': core_actor.tracklist,
        },
        decoders=[models.model_json_decoder],
        encoders=[models.ModelJSONEncoder]
    )


class WebSocketHandler(tornado.websocket.WebSocketHandler):

    # XXX This set is shared by all WebSocketHandler objects. This isn't
    # optimal, but there's currently no use case for having more than one of
    # these anyway.
    clients = set()

    @classmethod
    def broadcast(cls, msg):
        for client in cls.clients:
            client.write_message(msg)

    def initialize(self, core):
        self.jsonrpc = make_jsonrpc_wrapper(core)

    def open(self):
        self.set_nodelay(True)
        self.clients.add(self)
        logger.debug(
            'New WebSocket connection from %s', self.request.remote_ip)

    def on_close(self):
        self.clients.discard(self)
        logger.debug(
            'Closed WebSocket connection from %s',
            self.request.remote_ip)

    def on_message(self, message):
        if not message:
            return

        logger.debug(
            'Received WebSocket message from %s: %r',
            self.request.remote_ip, message)

        try:
            response = self.jsonrpc.handle_json(
                tornado.escape.native_str(message))
            if response and self.write_message(response):
                logger.debug(
                    'Sent WebSocket message to %s: %r',
                    self.request.remote_ip, response)
        except Exception as e:
            logger.error('WebSocket request error:', e)
            self.close()


class JsonRpcHandler(tornado.web.RequestHandler):
    def initialize(self, core):
        self.jsonrpc = make_jsonrpc_wrapper(core)

    def head(self):
        self.set_extra_headers()
        self.finish()

    def post(self):
        data = self.request.body
        if not data:
            return

        logger.debug(
            'Received RPC message from %s: %r', self.request.remote_ip, data)

        try:
            self.set_extra_headers()
            response = self.jsonrpc.handle_json(
                tornado.escape.native_str(data))
            if response and self.write(response):
                logger.debug(
                    'Sent RPC message to %s: %r',
                    self.request.remote_ip, response)
        except Exception as e:
            logger.error('HTTP JSON-RPC request error:', e)
            self.write_error(500)

    def set_extra_headers(self):
        self.set_header('Accept', 'application/json')
        self.set_header('Cache-Control', 'no-cache')
        self.set_header(
            'X-Mopidy-Version', mopidy.__version__.encode('utf-8'))
        self.set_header('Content-Type', 'application/json; utf-8')


class StaticFileHandler(tornado.web.StaticFileHandler):
    def set_extra_headers(self, path):
        self.set_header('Cache-Control', 'no-cache')
        self.set_header(
            'X-Mopidy-Version', mopidy.__version__.encode('utf-8'))

########NEW FILE########
__FILENAME__ = listener
from __future__ import unicode_literals

import logging

import gobject

import pykka

logger = logging.getLogger(__name__)


def send_async(cls, event, **kwargs):
    gobject.idle_add(lambda: send(cls, event, **kwargs))


def send(cls, event, **kwargs):
    listeners = pykka.ActorRegistry.get_by_class(cls)
    logger.debug('Sending %s to %s: %s', event, cls.__name__, kwargs)
    for listener in listeners:
        listener.proxy().on_event(event, **kwargs)


class Listener(object):
    def on_event(self, event, **kwargs):
        """
        Called on all events.

        *MAY* be implemented by actor. By default, this method forwards the
        event to the specific event methods.

        :param event: the event name
        :type event: string
        :param kwargs: any other arguments to the specific event handlers
        """
        getattr(self, event)(**kwargs)

########NEW FILE########
__FILENAME__ = actor
from __future__ import unicode_literals

import logging

import pykka

from mopidy import backend
from mopidy.local import storage
from mopidy.local.library import LocalLibraryProvider
from mopidy.local.playback import LocalPlaybackProvider
from mopidy.local.playlists import LocalPlaylistsProvider


logger = logging.getLogger(__name__)


class LocalBackend(pykka.ThreadingActor, backend.Backend):
    uri_schemes = ['local']
    libraries = []

    def __init__(self, config, audio):
        super(LocalBackend, self).__init__()

        self.config = config

        storage.check_dirs_and_files(config)

        libraries = dict((l.name, l) for l in self.libraries)
        library_name = config['local']['library']

        if library_name in libraries:
            library = libraries[library_name](config)
            logger.debug('Using %s as the local library', library_name)
        else:
            library = None
            logger.warning('Local library %s not found', library_name)

        self.playback = LocalPlaybackProvider(audio=audio, backend=self)
        self.playlists = LocalPlaylistsProvider(backend=self)
        self.library = LocalLibraryProvider(backend=self, library=library)

########NEW FILE########
__FILENAME__ = commands
from __future__ import print_function, unicode_literals

import logging
import os
import time

from mopidy import commands, exceptions
from mopidy.audio import scan
from mopidy.local import translator
from mopidy.utils import path


logger = logging.getLogger(__name__)


def _get_library(args, config):
    libraries = dict((l.name, l) for l in args.registry['local:library'])
    library_name = config['local']['library']

    if library_name not in libraries:
        logger.warning('Local library %s not found', library_name)
        return 1

    logger.debug('Using %s as the local library', library_name)
    return libraries[library_name](config)


class LocalCommand(commands.Command):
    def __init__(self):
        super(LocalCommand, self).__init__()
        self.add_child('scan', ScanCommand())
        self.add_child('clear', ClearCommand())


class ClearCommand(commands.Command):
    help = 'Clear local media files from the local library.'

    def run(self, args, config):
        library = _get_library(args, config)
        prompt = '\nAre you sure you want to clear the library? [y/N] '

        if raw_input(prompt).lower() != 'y':
            print('Clearing library aborted.')
            return 0

        if library.clear():
            print('Library successfully cleared.')
            return 0

        print('Unable to clear library.')
        return 1


class ScanCommand(commands.Command):
    help = 'Scan local media files and populate the local library.'

    def __init__(self):
        super(ScanCommand, self).__init__()
        self.add_argument('--limit',
                          action='store', type=int, dest='limit', default=None,
                          help='Maxmimum number of tracks to scan')

    def run(self, args, config):
        media_dir = config['local']['media_dir']
        scan_timeout = config['local']['scan_timeout']
        flush_threshold = config['local']['scan_flush_threshold']
        excluded_file_extensions = config['local']['excluded_file_extensions']
        excluded_file_extensions = tuple(
            bytes(file_ext.lower()) for file_ext in excluded_file_extensions)

        library = _get_library(args, config)

        uris_in_library = set()
        uris_to_update = set()
        uris_to_remove = set()

        file_mtimes = path.find_mtimes(media_dir)
        logger.info('Found %d files in media_dir.', len(file_mtimes))

        num_tracks = library.load()
        logger.info('Checking %d tracks from library.', num_tracks)

        for track in library.begin():
            abspath = translator.local_track_uri_to_path(track.uri, media_dir)
            mtime = file_mtimes.pop(abspath, None)
            if mtime is None:
                logger.debug('Missing file %s', track.uri)
                uris_to_remove.add(track.uri)
            elif mtime > track.last_modified:
                uris_in_library.add(track.uri)

        logger.info('Removing %d missing tracks.', len(uris_to_remove))
        for uri in uris_to_remove:
            library.remove(uri)

        for abspath in file_mtimes:
            relpath = os.path.relpath(abspath, media_dir)
            uri = translator.path_to_local_track_uri(relpath)

            if relpath.lower().endswith(excluded_file_extensions):
                logger.debug('Skipped %s: File extension excluded.', uri)
                continue

            uris_to_update.add(uri)

        logger.info(
            'Found %d tracks which need to be updated.', len(uris_to_update))
        logger.info('Scanning...')

        uris_to_update = sorted(uris_to_update, key=lambda v: v.lower())
        uris_to_update = uris_to_update[:args.limit]

        scanner = scan.Scanner(scan_timeout)
        progress = _Progress(flush_threshold, len(uris_to_update))

        for uri in uris_to_update:
            try:
                relpath = translator.local_track_uri_to_path(uri, media_dir)
                file_uri = path.path_to_uri(os.path.join(media_dir, relpath))
                data = scanner.scan(file_uri)
                track = scan.audio_data_to_track(data).copy(uri=uri)
                library.add(track)
                logger.debug('Added %s', track.uri)
            except exceptions.ScannerError as error:
                logger.warning('Failed %s: %s', uri, error)

            if progress.increment():
                progress.log()
                if library.flush():
                    logger.debug('Progress flushed.')

        progress.log()
        library.close()
        logger.info('Done scanning.')
        return 0


class _Progress(object):
    def __init__(self, batch_size, total):
        self.count = 0
        self.batch_size = batch_size
        self.total = total
        self.start = time.time()

    def increment(self):
        self.count += 1
        return self.batch_size and self.count % self.batch_size == 0

    def log(self):
        duration = time.time() - self.start
        if self.count >= self.total or not self.count:
            logger.info('Scanned %d of %d files in %ds.',
                        self.count, self.total, duration)
        else:
            remainder = duration / self.count * (self.total - self.count)
            logger.info('Scanned %d of %d files in %ds, ~%ds left.',
                        self.count, self.total, duration, remainder)

########NEW FILE########
__FILENAME__ = json
from __future__ import absolute_import, unicode_literals

import collections
import gzip
import json
import logging
import os
import re
import sys
import tempfile
import time

import mopidy
from mopidy import local, models
from mopidy.local import search, storage, translator
from mopidy.utils import encoding

logger = logging.getLogger(__name__)


# TODO: move to load and dump in models?
def load_library(json_file):
    try:
        with gzip.open(json_file, 'rb') as fp:
            return json.load(fp, object_hook=models.model_json_decoder)
    except (IOError, ValueError) as error:
        logger.warning(
            'Loading JSON local library failed: %s',
            encoding.locale_decode(error))
        return {}


def write_library(json_file, data):
    data['version'] = mopidy.__version__
    directory, basename = os.path.split(json_file)

    # TODO: cleanup directory/basename.* files.
    tmp = tempfile.NamedTemporaryFile(
        prefix=basename + '.', dir=directory, delete=False)

    try:
        with gzip.GzipFile(fileobj=tmp, mode='wb') as fp:
            json.dump(data, fp, cls=models.ModelJSONEncoder,
                      indent=2, separators=(',', ': '))
        os.rename(tmp.name, json_file)
    finally:
        if os.path.exists(tmp.name):
            os.remove(tmp.name)


class _BrowseCache(object):
    encoding = sys.getfilesystemencoding()
    splitpath_re = re.compile(r'([^/]+)')

    def __init__(self, uris):
        # TODO: local.ROOT_DIRECTORY_URI
        self._cache = {'local:directory': collections.OrderedDict()}

        for track_uri in uris:
            path = translator.local_track_uri_to_path(track_uri, b'/')
            parts = self.splitpath_re.findall(
                path.decode(self.encoding, 'replace'))
            track_ref = models.Ref.track(uri=track_uri, name=parts.pop())

            # Look for our parents backwards as this is faster than having to
            # do a complete search for each add.
            parent_uri = None
            child = None
            for i in reversed(range(len(parts))):
                directory = '/'.join(parts[:i+1])
                uri = translator.path_to_local_directory_uri(directory)

                # First dir we process is our parent
                if not parent_uri:
                    parent_uri = uri

                # We found ourselves and we exist, done.
                if uri in self._cache:
                    if child:
                        self._cache[uri][child.uri] = child
                    break

                # Initialize ourselves, store child if present, and add
                # ourselves as child for next loop.
                self._cache[uri] = collections.OrderedDict()
                if child:
                    self._cache[uri][child.uri] = child
                child = models.Ref.directory(uri=uri, name=parts[i])
            else:
                # Loop completed, so final child needs to be added to root.
                if child:
                    self._cache['local:directory'][child.uri] = child
                # If no parent was set we belong in the root.
                if not parent_uri:
                    parent_uri = 'local:directory'

            self._cache[parent_uri][track_uri] = track_ref

    def lookup(self, uri):
        return self._cache.get(uri, {}).values()


# TODO: make this available to other code?
class DebugTimer(object):
    def __init__(self, msg):
        self.msg = msg
        self.start = None

    def __enter__(self):
        self.start = time.time()

    def __exit__(self, exc_type, exc_value, traceback):
        duration = (time.time() - self.start) * 1000
        logger.debug('%s: %dms', self.msg, duration)


class JsonLibrary(local.Library):
    name = 'json'

    def __init__(self, config):
        self._tracks = {}
        self._browse_cache = None
        self._media_dir = config['local']['media_dir']
        self._json_file = os.path.join(
            config['local']['data_dir'], b'library.json.gz')

        storage.check_dirs_and_files(config)

    def browse(self, uri):
        if not self._browse_cache:
            return []
        return self._browse_cache.lookup(uri)

    def load(self):
        logger.debug('Loading library: %s', self._json_file)
        with DebugTimer('Loading tracks'):
            library = load_library(self._json_file)
            self._tracks = dict((t.uri, t) for t in library.get('tracks', []))
        with DebugTimer('Building browse cache'):
            self._browse_cache = _BrowseCache(sorted(self._tracks.keys()))
        return len(self._tracks)

    def lookup(self, uri):
        try:
            return self._tracks[uri]
        except KeyError:
            return None

    def search(self, query=None, limit=100, offset=0, uris=None, exact=False):
        tracks = self._tracks.values()
        # TODO: pass limit and offset into search helpers
        if exact:
            return search.find_exact(tracks, query=query, uris=uris)
        else:
            return search.search(tracks, query=query, uris=uris)

    def begin(self):
        return self._tracks.itervalues()

    def add(self, track):
        self._tracks[track.uri] = track

    def remove(self, uri):
        self._tracks.pop(uri, None)

    def close(self):
        write_library(self._json_file, {'tracks': self._tracks.values()})

    def clear(self):
        try:
            os.remove(self._json_file)
            return True
        except OSError:
            return False

########NEW FILE########
__FILENAME__ = library
from __future__ import unicode_literals

import logging

from mopidy import backend, models

logger = logging.getLogger(__name__)


class LocalLibraryProvider(backend.LibraryProvider):
    """Proxy library that delegates work to our active local library."""

    root_directory = models.Ref.directory(uri=b'local:directory',
                                          name='Local media')

    def __init__(self, backend, library):
        super(LocalLibraryProvider, self).__init__(backend)
        self._library = library
        self.refresh()

    def browse(self, path):
        if not self._library:
            return []
        return self._library.browse(path)

    def refresh(self, uri=None):
        if not self._library:
            return 0
        num_tracks = self._library.load()
        logger.info('Loaded %d local tracks using %s',
                    num_tracks, self._library.name)

    def lookup(self, uri):
        if not self._library:
            return []
        track = self._library.lookup(uri)
        if track is None:
            logger.debug('Failed to lookup %r', uri)
            return []
        return [track]

    def find_exact(self, query=None, uris=None):
        if not self._library:
            return None
        return self._library.search(query=query, uris=uris, exact=True)

    def search(self, query=None, uris=None):
        if not self._library:
            return None
        return self._library.search(query=query, uris=uris, exact=False)

########NEW FILE########
__FILENAME__ = playback
from __future__ import unicode_literals

import logging

from mopidy import backend
from mopidy.local import translator


logger = logging.getLogger(__name__)


class LocalPlaybackProvider(backend.PlaybackProvider):
    def change_track(self, track):
        track = track.copy(uri=translator.local_track_uri_to_file_uri(
            track.uri, self.backend.config['local']['media_dir']))
        return super(LocalPlaybackProvider, self).change_track(track)

########NEW FILE########
__FILENAME__ = playlists
from __future__ import unicode_literals

import glob
import logging
import os
import shutil

from mopidy import backend
from mopidy.models import Playlist
from mopidy.utils import formatting, path

from .translator import parse_m3u


logger = logging.getLogger(__name__)


class LocalPlaylistsProvider(backend.PlaylistsProvider):
    def __init__(self, *args, **kwargs):
        super(LocalPlaylistsProvider, self).__init__(*args, **kwargs)
        self._media_dir = self.backend.config['local']['media_dir']
        self._playlists_dir = self.backend.config['local']['playlists_dir']
        self.refresh()

    def create(self, name):
        name = formatting.slugify(name)
        uri = 'local:playlist:%s.m3u' % name
        playlist = Playlist(uri=uri, name=name)
        return self.save(playlist)

    def delete(self, uri):
        playlist = self.lookup(uri)
        if not playlist:
            return

        self._playlists.remove(playlist)
        self._delete_m3u(playlist.uri)

    def lookup(self, uri):
        # TODO: store as {uri: playlist}?
        for playlist in self._playlists:
            if playlist.uri == uri:
                return playlist

    def refresh(self):
        playlists = []

        for m3u in glob.glob(os.path.join(self._playlists_dir, '*.m3u')):
            name = os.path.splitext(os.path.basename(m3u))[0]
            uri = 'local:playlist:%s' % name

            tracks = []
            for track in parse_m3u(m3u, self._media_dir):
                tracks.append(track)

            playlist = Playlist(uri=uri, name=name, tracks=tracks)
            playlists.append(playlist)

        self.playlists = playlists
        # TODO: send what scheme we loaded them for?
        backend.BackendListener.send('playlists_loaded')

        logger.info(
            'Loaded %d local playlists from %s',
            len(playlists), self._playlists_dir)

    def save(self, playlist):
        assert playlist.uri, 'Cannot save playlist without URI'

        old_playlist = self.lookup(playlist.uri)

        if old_playlist and playlist.name != old_playlist.name:
            playlist = playlist.copy(name=formatting.slugify(playlist.name))
            playlist = self._rename_m3u(playlist)

        self._save_m3u(playlist)

        if old_playlist is not None:
            index = self._playlists.index(old_playlist)
            self._playlists[index] = playlist
        else:
            self._playlists.append(playlist)

        return playlist

    def _m3u_uri_to_path(self, uri):
        # TODO: create uri handling helpers for local uri types.
        file_path = path.uri_to_path(uri).split(':', 1)[1]
        file_path = os.path.join(self._playlists_dir, file_path)
        path.check_file_path_is_inside_base_dir(file_path, self._playlists_dir)
        return file_path

    def _write_m3u_extinf(self, file_handle, track):
        title = track.name.encode('latin-1', 'replace')
        runtime = track.length / 1000 if track.length else -1
        file_handle.write('#EXTINF:' + str(runtime) + ',' + title + '\n')

    def _save_m3u(self, playlist):
        file_path = self._m3u_uri_to_path(playlist.uri)
        extended = any(track.name for track in playlist.tracks)
        with open(file_path, 'w') as file_handle:
            if extended:
                file_handle.write('#EXTM3U\n')
            for track in playlist.tracks:
                if extended and track.name:
                    self._write_m3u_extinf(file_handle, track)
                file_handle.write(track.uri + '\n')

    def _delete_m3u(self, uri):
        file_path = self._m3u_uri_to_path(uri)
        if os.path.exists(file_path):
            os.remove(file_path)

    def _rename_m3u(self, playlist):
        dst_name = formatting.slugify(playlist.name)
        dst_uri = 'local:playlist:%s.m3u' % dst_name

        src_file_path = self._m3u_uri_to_path(playlist.uri)
        dst_file_path = self._m3u_uri_to_path(dst_uri)

        shutil.move(src_file_path, dst_file_path)
        return playlist.copy(uri=dst_uri)

########NEW FILE########
__FILENAME__ = search
from __future__ import unicode_literals

from mopidy.models import Album, SearchResult


def find_exact(tracks, query=None, uris=None):
    # TODO Only return results within URI roots given by ``uris``

    if query is None:
        query = {}

    _validate_query(query)

    for (field, values) in query.iteritems():
        if not hasattr(values, '__iter__'):
            values = [values]
        # FIXME this is bound to be slow for large libraries
        for value in values:
            if field == 'track_no':
                q = _convert_to_int(value)
            else:
                q = value.strip()

            uri_filter = lambda t: q == t.uri
            track_name_filter = lambda t: q == t.name
            album_filter = lambda t: q == getattr(t, 'album', Album()).name
            artist_filter = lambda t: filter(
                lambda a: q == a.name, t.artists)
            albumartist_filter = lambda t: any([
                q == a.name
                for a in getattr(t.album, 'artists', [])])
            composer_filter = lambda t: any([
                q == a.name
                for a in getattr(t, 'composers', [])])
            performer_filter = lambda t: any([
                q == a.name
                for a in getattr(t, 'performers', [])])
            track_no_filter = lambda t: q == t.track_no
            genre_filter = lambda t: t.genre and q == t.genre
            date_filter = lambda t: q == t.date
            comment_filter = lambda t: q == t.comment
            any_filter = lambda t: (
                uri_filter(t) or
                track_name_filter(t) or
                album_filter(t) or
                artist_filter(t) or
                albumartist_filter(t) or
                composer_filter(t) or
                performer_filter(t) or
                track_no_filter(t) or
                genre_filter(t) or
                date_filter(t) or
                comment_filter(t))

            if field == 'uri':
                tracks = filter(uri_filter, tracks)
            elif field == 'track_name':
                tracks = filter(track_name_filter, tracks)
            elif field == 'album':
                tracks = filter(album_filter, tracks)
            elif field == 'artist':
                tracks = filter(artist_filter, tracks)
            elif field == 'albumartist':
                tracks = filter(albumartist_filter, tracks)
            elif field == 'composer':
                tracks = filter(composer_filter, tracks)
            elif field == 'performer':
                tracks = filter(performer_filter, tracks)
            elif field == 'track_no':
                tracks = filter(track_no_filter, tracks)
            elif field == 'genre':
                tracks = filter(genre_filter, tracks)
            elif field == 'date':
                tracks = filter(date_filter, tracks)
            elif field == 'comment':
                tracks = filter(comment_filter, tracks)
            elif field == 'any':
                tracks = filter(any_filter, tracks)
            else:
                raise LookupError('Invalid lookup field: %s' % field)

    # TODO: add local:search:<query>
    return SearchResult(uri='local:search', tracks=tracks)


def search(tracks, query=None, uris=None):
    # TODO Only return results within URI roots given by ``uris``

    if query is None:
        query = {}

    _validate_query(query)

    for (field, values) in query.iteritems():
        if not hasattr(values, '__iter__'):
            values = [values]
        # FIXME this is bound to be slow for large libraries
        for value in values:
            if field == 'track_no':
                q = _convert_to_int(value)
            else:
                q = value.strip().lower()

            uri_filter = lambda t: bool(t.uri and q in t.uri.lower())
            track_name_filter = lambda t: bool(t.name and q in t.name.lower())
            album_filter = lambda t: bool(
                t.album and t.album.name and q in t.album.name.lower())
            artist_filter = lambda t: bool(filter(
                lambda a: bool(a.name and q in a.name.lower()), t.artists))
            albumartist_filter = lambda t: any([
                a.name and q in a.name.lower()
                for a in getattr(t.album, 'artists', [])])
            composer_filter = lambda t: any([
                a.name and q in a.name.lower()
                for a in getattr(t, 'composers', [])])
            performer_filter = lambda t: any([
                a.name and q in a.name.lower()
                for a in getattr(t, 'performers', [])])
            track_no_filter = lambda t: q == t.track_no
            genre_filter = lambda t: bool(t.genre and q in t.genre.lower())
            date_filter = lambda t: bool(t.date and t.date.startswith(q))
            comment_filter = lambda t: bool(
                t.comment and q in t.comment.lower())
            any_filter = lambda t: (
                uri_filter(t) or
                track_name_filter(t) or
                album_filter(t) or
                artist_filter(t) or
                albumartist_filter(t) or
                composer_filter(t) or
                performer_filter(t) or
                track_no_filter(t) or
                genre_filter(t) or
                date_filter(t) or
                comment_filter(t))

            if field == 'uri':
                tracks = filter(uri_filter, tracks)
            elif field == 'track_name':
                tracks = filter(track_name_filter, tracks)
            elif field == 'album':
                tracks = filter(album_filter, tracks)
            elif field == 'artist':
                tracks = filter(artist_filter, tracks)
            elif field == 'albumartist':
                tracks = filter(albumartist_filter, tracks)
            elif field == 'composer':
                tracks = filter(composer_filter, tracks)
            elif field == 'performer':
                tracks = filter(performer_filter, tracks)
            elif field == 'track_no':
                tracks = filter(track_no_filter, tracks)
            elif field == 'genre':
                tracks = filter(genre_filter, tracks)
            elif field == 'date':
                tracks = filter(date_filter, tracks)
            elif field == 'comment':
                tracks = filter(comment_filter, tracks)
            elif field == 'any':
                tracks = filter(any_filter, tracks)
            else:
                raise LookupError('Invalid lookup field: %s' % field)
    # TODO: add local:search:<query>
    return SearchResult(uri='local:search', tracks=tracks)


def _validate_query(query):
    for (_, values) in query.iteritems():
        if not values:
            raise LookupError('Missing query')
        for value in values:
            if not value:
                raise LookupError('Missing query')


def _convert_to_int(string):
    try:
        return int(string)
    except ValueError:
        return object()

########NEW FILE########
__FILENAME__ = storage
from __future__ import unicode_literals

import logging
import os

from mopidy.utils import encoding, path

logger = logging.getLogger(__name__)


def check_dirs_and_files(config):
    if not os.path.isdir(config['local']['media_dir']):
        logger.warning(
            'Local media dir %s does not exist.' %
            config['local']['media_dir'])

    try:
        path.get_or_create_dir(config['local']['data_dir'])
    except EnvironmentError as error:
        logger.warning(
            'Could not create local data dir: %s',
            encoding.locale_decode(error))

    # TODO: replace with data dir?
    try:
        path.get_or_create_dir(config['local']['playlists_dir'])
    except EnvironmentError as error:
        logger.warning(
            'Could not create local playlists dir: %s',
            encoding.locale_decode(error))

########NEW FILE########
__FILENAME__ = translator
from __future__ import unicode_literals

import logging
import os
import re
import urllib
import urlparse

from mopidy.models import Track
from mopidy.utils.encoding import locale_decode
from mopidy.utils.path import path_to_uri, uri_to_path


M3U_EXTINF_RE = re.compile(r'#EXTINF:(-1|\d+),(.*)')

logger = logging.getLogger(__name__)


def local_track_uri_to_file_uri(uri, media_dir):
    return path_to_uri(local_track_uri_to_path(uri, media_dir))


def local_track_uri_to_path(uri, media_dir):
    if not uri.startswith('local:track:'):
        raise ValueError('Invalid URI.')
    file_path = uri_to_path(uri).split(b':', 1)[1]
    return os.path.join(media_dir, file_path)


def path_to_local_track_uri(relpath):
    """Convert path releative to media_dir to local track URI."""
    if isinstance(relpath, unicode):
        relpath = relpath.encode('utf-8')
    return b'local:track:%s' % urllib.quote(relpath)


def path_to_local_directory_uri(relpath):
    """Convert path relative to :confval:`local/media_dir` directory URI."""
    if isinstance(relpath, unicode):
        relpath = relpath.encode('utf-8')
    return b'local:directory:%s' % urllib.quote(relpath)


def m3u_extinf_to_track(line):
    """Convert extended M3U directive to track template."""
    m = M3U_EXTINF_RE.match(line)
    if not m:
        logger.warning('Invalid extended M3U directive: %s', line)
        return Track()
    (runtime, title) = m.groups()
    if int(runtime) > 0:
        return Track(name=title, length=1000*int(runtime))
    else:
        return Track(name=title)


def parse_m3u(file_path, media_dir):
    r"""
    Convert M3U file list to list of tracks

    Example M3U data::

        # This is a comment
        Alternative\Band - Song.mp3
        Classical\Other Band - New Song.mp3
        Stuff.mp3
        D:\More Music\Foo.mp3
        http://www.example.com:8000/Listen.pls
        http://www.example.com/~user/Mine.mp3

    Example extended M3U data::

        #EXTM3U
        #EXTINF:123, Sample artist - Sample title
        Sample.mp3
        #EXTINF:321,Example Artist - Example title
        Greatest Hits\Example.ogg
        #EXTINF:-1,Radio XMP
        http://mp3stream.example.com:8000/

    - Relative paths of songs should be with respect to location of M3U.
    - Paths are normally platform specific.
    - Lines starting with # are ignored, except for extended M3U directives.
    - Track.name and Track.length are set from extended M3U directives.
    - m3u files are latin-1.
    """
    # TODO: uris as bytes
    tracks = []
    try:
        with open(file_path) as m3u:
            contents = m3u.readlines()
    except IOError as error:
        logger.warning('Couldn\'t open m3u: %s', locale_decode(error))
        return tracks

    if not contents:
        return tracks

    extended = contents[0].decode('latin1').startswith('#EXTM3U')

    track = Track()
    for line in contents:
        line = line.strip().decode('latin1')

        if line.startswith('#'):
            if extended and line.startswith('#EXTINF'):
                track = m3u_extinf_to_track(line)
            continue

        if urlparse.urlsplit(line).scheme:
            tracks.append(track.copy(uri=line))
        elif os.path.normpath(line) == os.path.abspath(line):
            path = path_to_uri(line)
            tracks.append(track.copy(uri=path))
        else:
            path = path_to_uri(os.path.join(media_dir, line))
            tracks.append(track.copy(uri=path))

        track = Track()
    return tracks

########NEW FILE########
__FILENAME__ = models
from __future__ import unicode_literals

import json


class ImmutableObject(object):
    """
    Superclass for immutable objects whose fields can only be modified via the
    constructor.

    :param kwargs: kwargs to set as fields on the object
    :type kwargs: any
    """

    def __init__(self, *args, **kwargs):
        for key, value in kwargs.items():
            if not hasattr(self, key) or callable(getattr(self, key)):
                raise TypeError(
                    '__init__() got an unexpected keyword argument "%s"' %
                    key)
            self.__dict__[key] = value

    def __setattr__(self, name, value):
        if name.startswith('_'):
            return super(ImmutableObject, self).__setattr__(name, value)
        raise AttributeError('Object is immutable.')

    def __repr__(self):
        kwarg_pairs = []
        for (key, value) in sorted(self.__dict__.items()):
            if isinstance(value, (frozenset, tuple)):
                value = list(value)
            kwarg_pairs.append('%s=%s' % (key, repr(value)))
        return '%(classname)s(%(kwargs)s)' % {
            'classname': self.__class__.__name__,
            'kwargs': ', '.join(kwarg_pairs),
        }

    def __hash__(self):
        hash_sum = 0
        for key, value in self.__dict__.items():
            hash_sum += hash(key) + hash(value)
        return hash_sum

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False

        return self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not self.__eq__(other)

    def copy(self, **values):
        """
        Copy the model with ``field`` updated to new value.

        Examples::

            # Returns a track with a new name
            Track(name='foo').copy(name='bar')
            # Return an album with a new number of tracks
            Album(num_tracks=2).copy(num_tracks=5)

        :param values: the model fields to modify
        :type values: dict
        :rtype: new instance of the model being copied
        """
        data = {}
        for key in self.__dict__.keys():
            public_key = key.lstrip('_')
            value = values.pop(public_key, self.__dict__[key])
            if value is not None:
                data[public_key] = value
        for key in values.keys():
            if hasattr(self, key):
                value = values.pop(key)
                if value is not None:
                    data[key] = value
        if values:
            raise TypeError(
                'copy() got an unexpected keyword argument "%s"' % key)
        return self.__class__(**data)

    def serialize(self):
        data = {}
        data['__model__'] = self.__class__.__name__
        for key in self.__dict__.keys():
            public_key = key.lstrip('_')
            value = self.__dict__[key]
            if isinstance(value, (set, frozenset, list, tuple)):
                value = [
                    v.serialize() if isinstance(v, ImmutableObject) else v
                    for v in value]
            elif isinstance(value, ImmutableObject):
                value = value.serialize()
            if not (isinstance(value, list) and len(value) == 0):
                data[public_key] = value
        return data


class ModelJSONEncoder(json.JSONEncoder):
    """
    Automatically serialize Mopidy models to JSON.

    Usage::

        >>> import json
        >>> json.dumps({'a_track': Track(name='name')}, cls=ModelJSONEncoder)
        '{"a_track": {"__model__": "Track", "name": "name"}}'

    """
    def default(self, obj):
        if isinstance(obj, ImmutableObject):
            return obj.serialize()
        return json.JSONEncoder.default(self, obj)


def model_json_decoder(dct):
    """
    Automatically deserialize Mopidy models from JSON.

    Usage::

        >>> import json
        >>> json.loads(
        ...     '{"a_track": {"__model__": "Track", "name": "name"}}',
        ...     object_hook=model_json_decoder)
        {u'a_track': Track(artists=[], name=u'name')}

    """
    if '__model__' in dct:
        model_name = dct.pop('__model__')
        cls = globals().get(model_name, None)
        if issubclass(cls, ImmutableObject):
            kwargs = {}
            for key, value in dct.items():
                kwargs[key] = value
            return cls(**kwargs)
    return dct


class Ref(ImmutableObject):
    """
    Model to represent URI references with a human friendly name and type
    attached. This is intended for use a lightweight object "free" of metadata
    that can be passed around instead of using full blown models.

    :param uri: object URI
    :type uri: string
    :param name: object name
    :type name: string
    :param type: object type
    :type name: string
    """

    #: The object URI. Read-only.
    uri = None

    #: The object name. Read-only.
    name = None

    #: The object type, e.g. "artist", "album", "track", "playlist",
    #: "directory". Read-only.
    type = None

    #: Constant used for comparison with the :attr:`type` field.
    ALBUM = 'album'

    #: Constant used for comparison with the :attr:`type` field.
    ARTIST = 'artist'

    #: Constant used for comparison with the :attr:`type` field.
    DIRECTORY = 'directory'

    #: Constant used for comparison with the :attr:`type` field.
    PLAYLIST = 'playlist'

    #: Constant used for comparison with the :attr:`type` field.
    TRACK = 'track'

    @classmethod
    def album(cls, **kwargs):
        """Create a :class:`Ref` with ``type`` :attr:`ALBUM`."""
        kwargs['type'] = Ref.ALBUM
        return cls(**kwargs)

    @classmethod
    def artist(cls, **kwargs):
        """Create a :class:`Ref` with ``type`` :attr:`ARTIST`."""
        kwargs['type'] = Ref.ARTIST
        return cls(**kwargs)

    @classmethod
    def directory(cls, **kwargs):
        """Create a :class:`Ref` with ``type`` :attr:`DIRECTORY`."""
        kwargs['type'] = Ref.DIRECTORY
        return cls(**kwargs)

    @classmethod
    def playlist(cls, **kwargs):
        """Create a :class:`Ref` with ``type`` :attr:`PLAYLIST`."""
        kwargs['type'] = Ref.PLAYLIST
        return cls(**kwargs)

    @classmethod
    def track(cls, **kwargs):
        """Create a :class:`Ref` with ``type`` :attr:`TRACK`."""
        kwargs['type'] = Ref.TRACK
        return cls(**kwargs)


class Artist(ImmutableObject):
    """
    :param uri: artist URI
    :type uri: string
    :param name: artist name
    :type name: string
    :param musicbrainz_id: MusicBrainz ID
    :type musicbrainz_id: string
    """

    #: The artist URI. Read-only.
    uri = None

    #: The artist name. Read-only.
    name = None

    #: The MusicBrainz ID of the artist. Read-only.
    musicbrainz_id = None


class Album(ImmutableObject):
    """
    :param uri: album URI
    :type uri: string
    :param name: album name
    :type name: string
    :param artists: album artists
    :type artists: list of :class:`Artist`
    :param num_tracks: number of tracks in album
    :type num_tracks: integer
    :param num_discs: number of discs in album
    :type num_discs: integer or :class:`None` if unknown
    :param date: album release date (YYYY or YYYY-MM-DD)
    :type date: string
    :param musicbrainz_id: MusicBrainz ID
    :type musicbrainz_id: string
    :param images: album image URIs
    :type images: list of strings
    """

    #: The album URI. Read-only.
    uri = None

    #: The album name. Read-only.
    name = None

    #: A set of album artists. Read-only.
    artists = frozenset()

    #: The number of tracks in the album. Read-only.
    num_tracks = 0

    #: The number of discs in the album. Read-only.
    num_discs = None

    #: The album release date. Read-only.
    date = None

    #: The MusicBrainz ID of the album. Read-only.
    musicbrainz_id = None

    #: The album image URIs. Read-only.
    images = frozenset()
    # XXX If we want to keep the order of images we shouldn't use frozenset()
    # as it doesn't preserve order. I'm deferring this issue until we got
    # actual usage of this field with more than one image.

    def __init__(self, *args, **kwargs):
        self.__dict__['artists'] = frozenset(kwargs.pop('artists', None) or [])
        self.__dict__['images'] = frozenset(kwargs.pop('images', None) or [])
        super(Album, self).__init__(*args, **kwargs)


class Track(ImmutableObject):
    """
    :param uri: track URI
    :type uri: string
    :param name: track name
    :type name: string
    :param artists: track artists
    :type artists: list of :class:`Artist`
    :param album: track album
    :type album: :class:`Album`
    :param composers: track composers
    :type composers: string
    :param performers: track performers
    :type performers: string
    :param genre: track genre
    :type genre: string
    :param track_no: track number in album
    :type track_no: integer
    :param disc_no: disc number in album
    :type disc_no: integer or :class:`None` if unknown
    :param date: track release date (YYYY or YYYY-MM-DD)
    :type date: string
    :param length: track length in milliseconds
    :type length: integer
    :param bitrate: bitrate in kbit/s
    :type bitrate: integer
    :param comment: track comment
    :type comment: string
    :param musicbrainz_id: MusicBrainz ID
    :type musicbrainz_id: string
    :param last_modified: Represents last modification time
    :type last_modified: integer
    """

    #: The track URI. Read-only.
    uri = None

    #: The track name. Read-only.
    name = None

    #: A set of track artists. Read-only.
    artists = frozenset()

    #: The track :class:`Album`. Read-only.
    album = None

    #: A set of track composers. Read-only.
    composers = frozenset()

    #: A set of track performers`. Read-only.
    performers = frozenset()

    #: The track genre. Read-only.
    genre = None

    #: The track number in the album. Read-only.
    track_no = 0

    #: The disc number in the album. Read-only.
    disc_no = None

    #: The track release date. Read-only.
    date = None

    #: The track length in milliseconds. Read-only.
    length = None

    #: The track's bitrate in kbit/s. Read-only.
    bitrate = None

    #: The track comment. Read-only.
    comment = None

    #: The MusicBrainz ID of the track. Read-only.
    musicbrainz_id = None

    #: Integer representing when the track was last modified, exact meaning
    #: depends on source of track. For local files this is the mtime, for other
    #: backends it could be a timestamp or simply a version counter.
    last_modified = 0

    def __init__(self, *args, **kwargs):
        get = lambda key: frozenset(kwargs.pop(key, None) or [])
        self.__dict__['artists'] = get('artists')
        self.__dict__['composers'] = get('composers')
        self.__dict__['performers'] = get('performers')
        super(Track, self).__init__(*args, **kwargs)


class TlTrack(ImmutableObject):
    """
    A tracklist track. Wraps a regular track and it's tracklist ID.

    The use of :class:`TlTrack` allows the same track to appear multiple times
    in the tracklist.

    This class also accepts it's parameters as positional arguments. Both
    arguments must be provided, and they must appear in the order they are
    listed here.

    This class also supports iteration, so your extract its values like this::

        (tlid, track) = tl_track

    :param tlid: tracklist ID
    :type tlid: int
    :param track: the track
    :type track: :class:`Track`
    """

    #: The tracklist ID. Read-only.
    tlid = None

    #: The track. Read-only.
    track = None

    def __init__(self, *args, **kwargs):
        if len(args) == 2 and len(kwargs) == 0:
            kwargs['tlid'] = args[0]
            kwargs['track'] = args[1]
            args = []
        super(TlTrack, self).__init__(*args, **kwargs)

    def __iter__(self):
        return iter([self.tlid, self.track])


class Playlist(ImmutableObject):
    """
    :param uri: playlist URI
    :type uri: string
    :param name: playlist name
    :type name: string
    :param tracks: playlist's tracks
    :type tracks: list of :class:`Track` elements
    :param last_modified:
        playlist's modification time in milliseconds since Unix epoch
    :type last_modified: int
    """

    #: The playlist URI. Read-only.
    uri = None

    #: The playlist name. Read-only.
    name = None

    #: The playlist's tracks. Read-only.
    tracks = tuple()

    #: The playlist modification time in milliseconds since Unix epoch.
    #: Read-only.
    #:
    #: Integer, or :class:`None` if unknown.
    last_modified = None

    def __init__(self, *args, **kwargs):
        self.__dict__['tracks'] = tuple(kwargs.pop('tracks', None) or [])
        super(Playlist, self).__init__(*args, **kwargs)

    # TODO: def insert(self, pos, track): ... ?

    @property
    def length(self):
        """The number of tracks in the playlist. Read-only."""
        return len(self.tracks)


class SearchResult(ImmutableObject):
    """
    :param uri: search result URI
    :type uri: string
    :param tracks: matching tracks
    :type tracks: list of :class:`Track` elements
    :param artists: matching artists
    :type artists: list of :class:`Artist` elements
    :param albums: matching albums
    :type albums: list of :class:`Album` elements
    """

    # The search result URI. Read-only.
    uri = None

    # The tracks matching the search query. Read-only.
    tracks = tuple()

    # The artists matching the search query. Read-only.
    artists = tuple()

    # The albums matching the search query. Read-only.
    albums = tuple()

    def __init__(self, *args, **kwargs):
        self.__dict__['tracks'] = tuple(kwargs.pop('tracks', None) or [])
        self.__dict__['artists'] = tuple(kwargs.pop('artists', None) or [])
        self.__dict__['albums'] = tuple(kwargs.pop('albums', None) or [])
        super(SearchResult, self).__init__(*args, **kwargs)

########NEW FILE########
__FILENAME__ = actor
from __future__ import unicode_literals

import logging
import sys

import pykka

from mopidy import zeroconf
from mopidy.core import CoreListener
from mopidy.mpd import session
from mopidy.utils import encoding, network, process

logger = logging.getLogger(__name__)


class MpdFrontend(pykka.ThreadingActor, CoreListener):
    def __init__(self, config, core):
        super(MpdFrontend, self).__init__()

        hostname = network.format_hostname(config['mpd']['hostname'])
        self.hostname = hostname
        self.port = config['mpd']['port']
        self.zeroconf_name = config['mpd']['zeroconf']
        self.zeroconf_service = None

        try:
            network.Server(
                self.hostname, self.port,
                protocol=session.MpdSession,
                protocol_kwargs={
                    'config': config,
                    'core': core,
                },
                max_connections=config['mpd']['max_connections'],
                timeout=config['mpd']['connection_timeout'])
        except IOError as error:
            logger.error(
                'MPD server startup failed: %s',
                encoding.locale_decode(error))
            sys.exit(1)

        logger.info('MPD server running at [%s]:%s', self.hostname, self.port)

    def on_start(self):
        if self.zeroconf_name:
            self.zeroconf_service = zeroconf.Zeroconf(
                stype='_mpd._tcp', name=self.zeroconf_name,
                host=self.hostname, port=self.port)

            if self.zeroconf_service.publish():
                logger.debug(
                    'Registered MPD with Zeroconf as "%s"',
                    self.zeroconf_service.name)
            else:
                logger.debug('Registering MPD with Zeroconf failed.')

    def on_stop(self):
        if self.zeroconf_service:
            self.zeroconf_service.unpublish()

        process.stop_actors_by_class(session.MpdSession)

    def send_idle(self, subsystem):
        listeners = pykka.ActorRegistry.get_by_class(session.MpdSession)
        for listener in listeners:
            getattr(listener.proxy(), 'on_idle')(subsystem)

    def playback_state_changed(self, old_state, new_state):
        self.send_idle('player')

    def tracklist_changed(self):
        self.send_idle('playlist')

    def options_changed(self):
        self.send_idle('options')

    def volume_changed(self, volume):
        self.send_idle('mixer')

    def mute_changed(self, mute):
        self.send_idle('output')

########NEW FILE########
__FILENAME__ = dispatcher
from __future__ import unicode_literals

import logging
import re

import pykka

from mopidy.mpd import exceptions, protocol, tokenize

logger = logging.getLogger(__name__)

protocol.load_protocol_modules()


class MpdDispatcher(object):
    """
    The MPD session feeds the MPD dispatcher with requests. The dispatcher
    finds the correct handler, processes the request and sends the response
    back to the MPD session.
    """

    _noidle = re.compile(r'^noidle$')

    def __init__(self, session=None, config=None, core=None):
        self.config = config
        self.authenticated = False
        self.command_list_receiving = False
        self.command_list_ok = False
        self.command_list = []
        self.command_list_index = None
        self.context = MpdContext(
            self, session=session, config=config, core=core)

    def handle_request(self, request, current_command_list_index=None):
        """Dispatch incoming requests to the correct handler."""
        self.command_list_index = current_command_list_index
        response = []
        filter_chain = [
            self._catch_mpd_ack_errors_filter,
            self._authenticate_filter,
            self._command_list_filter,
            self._idle_filter,
            self._add_ok_filter,
            self._call_handler_filter,
        ]
        return self._call_next_filter(request, response, filter_chain)

    def handle_idle(self, subsystem):
        self.context.events.add(subsystem)

        subsystems = self.context.subscriptions.intersection(
            self.context.events)
        if not subsystems:
            return

        response = []
        for subsystem in subsystems:
            response.append('changed: %s' % subsystem)
        response.append('OK')
        self.context.subscriptions = set()
        self.context.events = set()
        self.context.session.send_lines(response)

    def _call_next_filter(self, request, response, filter_chain):
        if filter_chain:
            next_filter = filter_chain.pop(0)
            return next_filter(request, response, filter_chain)
        else:
            return response

    # Filter: catch MPD ACK errors

    def _catch_mpd_ack_errors_filter(self, request, response, filter_chain):
        try:
            return self._call_next_filter(request, response, filter_chain)
        except exceptions.MpdAckError as mpd_ack_error:
            if self.command_list_index is not None:
                mpd_ack_error.index = self.command_list_index
            return [mpd_ack_error.get_mpd_ack()]

    # Filter: authenticate

    def _authenticate_filter(self, request, response, filter_chain):
        if self.authenticated:
            return self._call_next_filter(request, response, filter_chain)
        elif self.config['mpd']['password'] is None:
            self.authenticated = True
            return self._call_next_filter(request, response, filter_chain)
        else:
            command_name = request.split(' ')[0]
            command = protocol.commands.handlers.get(command_name)
            if command and not command.auth_required:
                return self._call_next_filter(request, response, filter_chain)
            else:
                raise exceptions.MpdPermissionError(command=command_name)

    # Filter: command list

    def _command_list_filter(self, request, response, filter_chain):
        if self._is_receiving_command_list(request):
            self.command_list.append(request)
            return []
        else:
            response = self._call_next_filter(request, response, filter_chain)
            if (self._is_receiving_command_list(request) or
                    self._is_processing_command_list(request)):
                if response and response[-1] == 'OK':
                    response = response[:-1]
            return response

    def _is_receiving_command_list(self, request):
        return (
            self.command_list_receiving and request != 'command_list_end')

    def _is_processing_command_list(self, request):
        return (
            self.command_list_index is not None and
            request != 'command_list_end')

    # Filter: idle

    def _idle_filter(self, request, response, filter_chain):
        if self._is_currently_idle() and not self._noidle.match(request):
            logger.debug(
                'Client sent us %s, only %s is allowed while in '
                'the idle state', repr(request), repr('noidle'))
            self.context.session.close()
            return []

        if not self._is_currently_idle() and self._noidle.match(request):
            return []  # noidle was called before idle

        response = self._call_next_filter(request, response, filter_chain)

        if self._is_currently_idle():
            return []
        else:
            return response

    def _is_currently_idle(self):
        return bool(self.context.subscriptions)

    # Filter: add OK

    def _add_ok_filter(self, request, response, filter_chain):
        response = self._call_next_filter(request, response, filter_chain)
        if not self._has_error(response):
            response.append('OK')
        return response

    def _has_error(self, response):
        return response and response[-1].startswith('ACK')

    # Filter: call handler

    def _call_handler_filter(self, request, response, filter_chain):
        try:
            response = self._format_response(self._call_handler(request))
            return self._call_next_filter(request, response, filter_chain)
        except pykka.ActorDeadError as e:
            logger.warning('Tried to communicate with dead actor.')
            raise exceptions.MpdSystemError(e)

    def _call_handler(self, request):
        tokens = tokenize.split(request)
        try:
            return protocol.commands.call(tokens, context=self.context)
        except exceptions.MpdAckError as exc:
            if exc.command is None:
                exc.command = tokens[0]
            raise
        except LookupError:
            raise exceptions.MpdUnknownCommand(command=tokens[0])

    def _format_response(self, response):
        formatted_response = []
        for element in self._listify_result(response):
            formatted_response.extend(self._format_lines(element))
        return formatted_response

    def _listify_result(self, result):
        if result is None:
            return []
        if isinstance(result, set):
            return self._flatten(list(result))
        if not isinstance(result, list):
            return [result]
        return self._flatten(result)

    def _flatten(self, the_list):
        result = []
        for element in the_list:
            if isinstance(element, list):
                result.extend(self._flatten(element))
            else:
                result.append(element)
        return result

    def _format_lines(self, line):
        if isinstance(line, dict):
            return ['%s: %s' % (key, value) for (key, value) in line.items()]
        if isinstance(line, tuple):
            (key, value) = line
            return ['%s: %s' % (key, value)]
        return [line]


class MpdContext(object):
    """
    This object is passed as the first argument to all MPD command handlers to
    give the command handlers access to important parts of Mopidy.
    """

    #: The current :class:`MpdDispatcher`.
    dispatcher = None

    #: The current :class:`mopidy.mpd.MpdSession`.
    session = None

    #: The MPD password
    password = None

    #: The Mopidy core API. An instance of :class:`mopidy.core.Core`.
    core = None

    #: The active subsystems that have pending events.
    events = None

    #: The subsytems that we want to be notified about in idle mode.
    subscriptions = None

    _invalid_playlist_chars = re.compile(r'[\n\r/]')

    def __init__(self, dispatcher, session=None, config=None, core=None):
        self.dispatcher = dispatcher
        self.session = session
        if config is not None:
            self.password = config['mpd']['password']
        self.core = core
        self.events = set()
        self.subscriptions = set()
        self._playlist_uri_from_name = {}
        self._playlist_name_from_uri = {}
        self.refresh_playlists_mapping()

    def create_unique_name(self, playlist_name):
        stripped_name = self._invalid_playlist_chars.sub(' ', playlist_name)
        name = stripped_name
        i = 2
        while name in self._playlist_uri_from_name:
            name = '%s [%d]' % (stripped_name, i)
            i += 1
        return name

    def refresh_playlists_mapping(self):
        """
        Maintain map between playlists and unique playlist names to be used by
        MPD
        """
        if self.core is not None:
            self._playlist_uri_from_name.clear()
            self._playlist_name_from_uri.clear()
            for playlist in self.core.playlists.playlists.get():
                if not playlist.name:
                    continue
                # TODO: add scheme to name perhaps 'foo (spotify)' etc.
                name = self.create_unique_name(playlist.name)
                self._playlist_uri_from_name[name] = playlist.uri
                self._playlist_name_from_uri[playlist.uri] = name

    def lookup_playlist_from_name(self, name):
        """
        Helper function to retrieve a playlist from its unique MPD name.
        """
        if not self._playlist_uri_from_name:
            self.refresh_playlists_mapping()
        if name not in self._playlist_uri_from_name:
            return None
        uri = self._playlist_uri_from_name[name]
        return self.core.playlists.lookup(uri).get()

    def lookup_playlist_name_from_uri(self, uri):
        """
        Helper function to retrieve the unique MPD playlist name from its uri.
        """
        if uri not in self._playlist_name_from_uri:
            self.refresh_playlists_mapping()
        return self._playlist_name_from_uri[uri]

    def browse(self, path, recursive=True, lookup=True):
        # TODO: consider caching lookups for less work mapping path->uri
        path_parts = re.findall(r'[^/]+', path or '')
        root_path = '/'.join([''] + path_parts)
        uri = None

        for part in path_parts:
            for ref in self.core.library.browse(uri).get():
                if ref.type == ref.DIRECTORY and ref.name == part:
                    uri = ref.uri
                    break
            else:
                raise exceptions.MpdNoExistError('Not found')

        if recursive:
            yield (root_path, None)

        path_and_futures = [(root_path, self.core.library.browse(uri))]
        while path_and_futures:
            base_path, future = path_and_futures.pop()
            for ref in future.get():
                path = '/'.join([base_path, ref.name.replace('/', '')])
                if ref.type == ref.DIRECTORY:
                    yield (path, None)
                    if recursive:
                        path_and_futures.append(
                            (path, self.core.library.browse(ref.uri)))
                elif ref.type == ref.TRACK:
                    if lookup:
                        yield (path, self.core.library.lookup(ref.uri))
                    else:
                        yield (path, ref)

########NEW FILE########
__FILENAME__ = exceptions
from __future__ import unicode_literals

from mopidy.exceptions import MopidyException


class MpdAckError(MopidyException):
    """See fields on this class for available MPD error codes"""

    ACK_ERROR_NOT_LIST = 1
    ACK_ERROR_ARG = 2
    ACK_ERROR_PASSWORD = 3
    ACK_ERROR_PERMISSION = 4
    ACK_ERROR_UNKNOWN = 5
    ACK_ERROR_NO_EXIST = 50
    ACK_ERROR_PLAYLIST_MAX = 51
    ACK_ERROR_SYSTEM = 52
    ACK_ERROR_PLAYLIST_LOAD = 53
    ACK_ERROR_UPDATE_ALREADY = 54
    ACK_ERROR_PLAYER_SYNC = 55
    ACK_ERROR_EXIST = 56

    error_code = 0

    def __init__(self, message='', index=0, command=None):
        super(MpdAckError, self).__init__(message, index, command)
        self.message = message
        self.index = index
        self.command = command

    def get_mpd_ack(self):
        """
        MPD error code format::

            ACK [%(error_code)i@%(index)i] {%(command)s} description
        """
        return 'ACK [%i@%i] {%s} %s' % (
            self.__class__.error_code, self.index, self.command, self.message)


class MpdArgError(MpdAckError):
    error_code = MpdAckError.ACK_ERROR_ARG


class MpdPasswordError(MpdAckError):
    error_code = MpdAckError.ACK_ERROR_PASSWORD


class MpdPermissionError(MpdAckError):
    error_code = MpdAckError.ACK_ERROR_PERMISSION

    def __init__(self, *args, **kwargs):
        super(MpdPermissionError, self).__init__(*args, **kwargs)
        assert self.command is not None, 'command must be given explicitly'
        self.message = 'you don\'t have permission for "%s"' % self.command


class MpdUnknownError(MpdAckError):
    error_code = MpdAckError.ACK_ERROR_UNKNOWN


class MpdUnknownCommand(MpdUnknownError):
    def __init__(self, *args, **kwargs):
        super(MpdUnknownCommand, self).__init__(*args, **kwargs)
        assert self.command is not None, 'command must be given explicitly'
        self.message = 'unknown command "%s"' % self.command
        self.command = ''


class MpdNoCommand(MpdUnknownCommand):
    def __init__(self, *args, **kwargs):
        kwargs['command'] = ''
        super(MpdNoCommand, self).__init__(*args, **kwargs)
        self.message = 'No command given'


class MpdNoExistError(MpdAckError):
    error_code = MpdAckError.ACK_ERROR_NO_EXIST


class MpdSystemError(MpdAckError):
    error_code = MpdAckError.ACK_ERROR_SYSTEM


class MpdNotImplemented(MpdAckError):
    error_code = 0

    def __init__(self, *args, **kwargs):
        super(MpdNotImplemented, self).__init__(*args, **kwargs)
        self.message = 'Not implemented'

########NEW FILE########
__FILENAME__ = audio_output
from __future__ import unicode_literals

from mopidy.mpd import exceptions, protocol


@protocol.commands.add('disableoutput', outputid=protocol.UINT)
def disableoutput(context, outputid):
    """
    *musicpd.org, audio output section:*

        ``disableoutput``

        Turns an output off.
    """
    if outputid == 0:
        context.core.playback.set_mute(False)
    else:
        raise exceptions.MpdNoExistError('No such audio output')


@protocol.commands.add('enableoutput', outputid=protocol.UINT)
def enableoutput(context, outputid):
    """
    *musicpd.org, audio output section:*

        ``enableoutput``

        Turns an output on.
    """
    if outputid == 0:
        context.core.playback.set_mute(True)
    else:
        raise exceptions.MpdNoExistError('No such audio output')


# TODO: implement and test
# @protocol.commands.add('toggleoutput', outputid=protocol.UINT)
def toggleoutput(context, outputid):
    """
    *musicpd.org, audio output section:*

        ``toggleoutput {ID}``

        Turns an output on or off, depending on the current state.
    """
    pass


@protocol.commands.add('outputs')
def outputs(context):
    """
    *musicpd.org, audio output section:*

        ``outputs``

        Shows information about all outputs.
    """
    muted = 1 if context.core.playback.get_mute().get() else 0
    return [
        ('outputid', 0),
        ('outputname', 'Mute'),
        ('outputenabled', muted),
    ]

########NEW FILE########
__FILENAME__ = channels
from __future__ import unicode_literals

from mopidy.mpd import exceptions, protocol


@protocol.commands.add('subscribe')
def subscribe(context, channel):
    """
    *musicpd.org, client to client section:*

        ``subscribe {NAME}``

        Subscribe to a channel. The channel is created if it does not exist
        already. The name may consist of alphanumeric ASCII characters plus
        underscore, dash, dot and colon.
    """
    # TODO: match channel against [A-Za-z0-9:._-]+
    raise exceptions.MpdNotImplemented  # TODO


@protocol.commands.add('unsubscribe')
def unsubscribe(context, channel):
    """
    *musicpd.org, client to client section:*

        ``unsubscribe {NAME}``

        Unsubscribe from a channel.
    """
    # TODO: match channel against [A-Za-z0-9:._-]+
    raise exceptions.MpdNotImplemented  # TODO


@protocol.commands.add('channels')
def channels(context):
    """
    *musicpd.org, client to client section:*

        ``channels``

        Obtain a list of all channels. The response is a list of "channel:"
        lines.
    """
    raise exceptions.MpdNotImplemented  # TODO


@protocol.commands.add('readmessages')
def readmessages(context):
    """
    *musicpd.org, client to client section:*

        ``readmessages``

        Reads messages for this client. The response is a list of "channel:"
        and "message:" lines.
    """
    raise exceptions.MpdNotImplemented  # TODO


@protocol.commands.add('sendmessage')
def sendmessage(context, channel, text):
    """
    *musicpd.org, client to client section:*

        ``sendmessage {CHANNEL} {TEXT}``

        Send a message to the specified channel.
    """
    # TODO: match channel against [A-Za-z0-9:._-]+
    raise exceptions.MpdNotImplemented  # TODO

########NEW FILE########
__FILENAME__ = command_list
from __future__ import unicode_literals

from mopidy.mpd import exceptions, protocol


@protocol.commands.add('command_list_begin', list_command=False)
def command_list_begin(context):
    """
    *musicpd.org, command list section:*

        To facilitate faster adding of files etc. you can pass a list of
        commands all at once using a command list. The command list begins
        with ``command_list_begin`` or ``command_list_ok_begin`` and ends
        with ``command_list_end``.

        It does not execute any commands until the list has ended. The
        return value is whatever the return for a list of commands is. On
        success for all commands, ``OK`` is returned. If a command fails,
        no more commands are executed and the appropriate ``ACK`` error is
        returned. If ``command_list_ok_begin`` is used, ``list_OK`` is
        returned for each successful command executed in the command list.
    """
    context.dispatcher.command_list_receiving = True
    context.dispatcher.command_list_ok = False
    context.dispatcher.command_list = []


@protocol.commands.add('command_list_end', list_command=False)
def command_list_end(context):
    """See :meth:`command_list_begin()`."""
    # TODO: batch consecutive add commands
    if not context.dispatcher.command_list_receiving:
        raise exceptions.MpdUnknownCommand(command='command_list_end')
    context.dispatcher.command_list_receiving = False
    (command_list, context.dispatcher.command_list) = (
        context.dispatcher.command_list, [])
    (command_list_ok, context.dispatcher.command_list_ok) = (
        context.dispatcher.command_list_ok, False)
    command_list_response = []
    for index, command in enumerate(command_list):
        response = context.dispatcher.handle_request(
            command, current_command_list_index=index)
        command_list_response.extend(response)
        if (command_list_response and
                command_list_response[-1].startswith('ACK')):
            return command_list_response
        if command_list_ok:
            command_list_response.append('list_OK')
    return command_list_response


@protocol.commands.add('command_list_ok_begin', list_command=False)
def command_list_ok_begin(context):
    """See :meth:`command_list_begin()`."""
    context.dispatcher.command_list_receiving = True
    context.dispatcher.command_list_ok = True
    context.dispatcher.command_list = []

########NEW FILE########
__FILENAME__ = connection
from __future__ import unicode_literals

from mopidy.mpd import exceptions, protocol


@protocol.commands.add('close', auth_required=False)
def close(context):
    """
    *musicpd.org, connection section:*

        ``close``

        Closes the connection to MPD.
    """
    context.session.close()


@protocol.commands.add('kill', list_command=False)
def kill(context):
    """
    *musicpd.org, connection section:*

        ``kill``

        Kills MPD.
    """
    raise exceptions.MpdPermissionError(command='kill')


@protocol.commands.add('password', auth_required=False)
def password(context, password):
    """
    *musicpd.org, connection section:*

        ``password {PASSWORD}``

        This is used for authentication with the server. ``PASSWORD`` is
        simply the plaintext password.
    """
    if password == context.password:
        context.dispatcher.authenticated = True
    else:
        raise exceptions.MpdPasswordError('incorrect password')


@protocol.commands.add('ping', auth_required=False)
def ping(context):
    """
    *musicpd.org, connection section:*

        ``ping``

        Does nothing but return ``OK``.
    """
    pass

########NEW FILE########
__FILENAME__ = current_playlist
from __future__ import unicode_literals

import warnings

from mopidy.mpd import exceptions, protocol, translator


@protocol.commands.add('add')
def add(context, uri):
    """
    *musicpd.org, current playlist section:*

        ``add {URI}``

        Adds the file ``URI`` to the playlist (directories add recursively).
        ``URI`` can also be a single file.

    *Clarifications:*

    - ``add ""`` should add all tracks in the library to the current playlist.
    """
    if not uri.strip('/'):
        return

    if context.core.tracklist.add(uri=uri).get():
        return

    try:
        tracks = []
        for path, lookup_future in context.browse(uri):
            if lookup_future:
                tracks.extend(lookup_future.get())
    except exceptions.MpdNoExistError as e:
        e.message = 'directory or file not found'
        raise

    if not tracks:
        raise exceptions.MpdNoExistError('directory or file not found')
    context.core.tracklist.add(tracks=tracks)


@protocol.commands.add('addid', songpos=protocol.UINT)
def addid(context, uri, songpos=None):
    """
    *musicpd.org, current playlist section:*

        ``addid {URI} [POSITION]``

        Adds a song to the playlist (non-recursive) and returns the song id.

        ``URI`` is always a single file or URL. For example::

            addid "foo.mp3"
            Id: 999
            OK

    *Clarifications:*

    - ``addid ""`` should return an error.
    """
    if not uri:
        raise exceptions.MpdNoExistError('No such song')
    if songpos is not None and songpos > context.core.tracklist.length.get():
        raise exceptions.MpdArgError('Bad song index')
    tl_tracks = context.core.tracklist.add(uri=uri, at_position=songpos).get()
    if not tl_tracks:
        raise exceptions.MpdNoExistError('No such song')
    return ('Id', tl_tracks[0].tlid)


@protocol.commands.add('delete', position=protocol.RANGE)
def delete(context, position):
    """
    *musicpd.org, current playlist section:*

        ``delete [{POS} | {START:END}]``

        Deletes a song from the playlist.
    """
    start = position.start
    end = position.stop
    if end is None:
        end = context.core.tracklist.length.get()
    tl_tracks = context.core.tracklist.slice(start, end).get()
    if not tl_tracks:
        raise exceptions.MpdArgError('Bad song index', command='delete')
    for (tlid, _) in tl_tracks:
        context.core.tracklist.remove(tlid=[tlid])


@protocol.commands.add('deleteid', tlid=protocol.UINT)
def deleteid(context, tlid):
    """
    *musicpd.org, current playlist section:*

        ``deleteid {SONGID}``

        Deletes the song ``SONGID`` from the playlist
    """
    tl_tracks = context.core.tracklist.remove(tlid=[tlid]).get()
    if not tl_tracks:
        raise exceptions.MpdNoExistError('No such song')


@protocol.commands.add('clear')
def clear(context):
    """
    *musicpd.org, current playlist section:*

        ``clear``

        Clears the current playlist.
    """
    context.core.tracklist.clear()


@protocol.commands.add('move', position=protocol.RANGE, to=protocol.UINT)
def move_range(context, position, to):
    """
    *musicpd.org, current playlist section:*

        ``move [{FROM} | {START:END}] {TO}``

        Moves the song at ``FROM`` or range of songs at ``START:END`` to
        ``TO`` in the playlist.
    """
    start = position.start
    end = position.stop
    if end is None:
        end = context.core.tracklist.length.get()
    context.core.tracklist.move(start, end, to)


@protocol.commands.add('moveid', tlid=protocol.UINT, to=protocol.UINT)
def moveid(context, tlid, to):
    """
    *musicpd.org, current playlist section:*

        ``moveid {FROM} {TO}``

        Moves the song with ``FROM`` (songid) to ``TO`` (playlist index) in
        the playlist. If ``TO`` is negative, it is relative to the current
        song in the playlist (if there is one).
    """
    tl_tracks = context.core.tracklist.filter(tlid=[tlid]).get()
    if not tl_tracks:
        raise exceptions.MpdNoExistError('No such song')
    position = context.core.tracklist.index(tl_tracks[0]).get()
    context.core.tracklist.move(position, position + 1, to)


@protocol.commands.add('playlist')
def playlist(context):
    """
    *musicpd.org, current playlist section:*

        ``playlist``

        Displays the current playlist.

        .. note::

            Do not use this, instead use ``playlistinfo``.
    """
    warnings.warn(
        'Do not use this, instead use playlistinfo', DeprecationWarning)
    return playlistinfo(context)


@protocol.commands.add('playlistfind')
def playlistfind(context, tag, needle):
    """
    *musicpd.org, current playlist section:*

        ``playlistfind {TAG} {NEEDLE}``

        Finds songs in the current playlist with strict matching.

    *GMPC:*

    - does not add quotes around the tag.
    """
    if tag == 'filename':
        tl_tracks = context.core.tracklist.filter(uri=[needle]).get()
        if not tl_tracks:
            return None
        position = context.core.tracklist.index(tl_tracks[0]).get()
        return translator.track_to_mpd_format(tl_tracks[0], position=position)
    raise exceptions.MpdNotImplemented  # TODO


@protocol.commands.add('playlistid', tlid=protocol.UINT)
def playlistid(context, tlid=None):
    """
    *musicpd.org, current playlist section:*

        ``playlistid {SONGID}``

        Displays a list of songs in the playlist. ``SONGID`` is optional
        and specifies a single song to display info for.
    """
    if tlid is not None:
        tl_tracks = context.core.tracklist.filter(tlid=[tlid]).get()
        if not tl_tracks:
            raise exceptions.MpdNoExistError('No such song')
        position = context.core.tracklist.index(tl_tracks[0]).get()
        return translator.track_to_mpd_format(tl_tracks[0], position=position)
    else:
        return translator.tracks_to_mpd_format(
            context.core.tracklist.tl_tracks.get())


@protocol.commands.add('playlistinfo')
def playlistinfo(context, parameter=None):
    """
    *musicpd.org, current playlist section:*

        ``playlistinfo [[SONGPOS] | [START:END]]``

        Displays a list of all songs in the playlist, or if the optional
        argument is given, displays information only for the song
        ``SONGPOS`` or the range of songs ``START:END``.

    *ncmpc and mpc:*

    - uses negative indexes, like ``playlistinfo "-1"``, to request
      the entire playlist
    """
    if parameter is None or parameter == '-1':
        start, end = 0, None
    else:
        tracklist_slice = protocol.RANGE(parameter)
        start, end = tracklist_slice.start, tracklist_slice.stop

    tl_tracks = context.core.tracklist.tl_tracks.get()
    if start and start > len(tl_tracks):
        raise exceptions.MpdArgError('Bad song index')
    if end and end > len(tl_tracks):
        end = None
    return translator.tracks_to_mpd_format(tl_tracks, start, end)


@protocol.commands.add('playlistsearch')
def playlistsearch(context, tag, needle):
    """
    *musicpd.org, current playlist section:*

        ``playlistsearch {TAG} {NEEDLE}``

        Searches case-sensitively for partial matches in the current
        playlist.

    *GMPC:*

    - does not add quotes around the tag
    - uses ``filename`` and ``any`` as tags
    """
    raise exceptions.MpdNotImplemented  # TODO


@protocol.commands.add('plchanges', version=protocol.INT)
def plchanges(context, version):
    """
    *musicpd.org, current playlist section:*

        ``plchanges {VERSION}``

        Displays changed songs currently in the playlist since ``VERSION``.

        To detect songs that were deleted at the end of the playlist, use
        ``playlistlength`` returned by status command.

    *MPDroid:*

    - Calls ``plchanges "-1"`` two times per second to get the entire playlist.
    """
    # XXX Naive implementation that returns all tracks as changed
    if int(version) < context.core.tracklist.version.get():
        return translator.tracks_to_mpd_format(
            context.core.tracklist.tl_tracks.get())


@protocol.commands.add('plchangesposid', version=protocol.INT)
def plchangesposid(context, version):
    """
    *musicpd.org, current playlist section:*

        ``plchangesposid {VERSION}``

        Displays changed songs currently in the playlist since ``VERSION``.
        This function only returns the position and the id of the changed
        song, not the complete metadata. This is more bandwidth efficient.

        To detect songs that were deleted at the end of the playlist, use
        ``playlistlength`` returned by status command.
    """
    # XXX Naive implementation that returns all tracks as changed
    if int(version) != context.core.tracklist.version.get():
        result = []
        for (position, (tlid, _)) in enumerate(
                context.core.tracklist.tl_tracks.get()):
            result.append(('cpos', position))
            result.append(('Id', tlid))
        return result


@protocol.commands.add('shuffle', position=protocol.RANGE)
def shuffle(context, position=None):
    """
    *musicpd.org, current playlist section:*

        ``shuffle [START:END]``

        Shuffles the current playlist. ``START:END`` is optional and
        specifies a range of songs.
    """
    if position is None:
        start, end = None, None
    else:
        start, end = position.start, position.stop
    context.core.tracklist.shuffle(start, end)


@protocol.commands.add('swap', songpos1=protocol.UINT, songpos2=protocol.UINT)
def swap(context, songpos1, songpos2):
    """
    *musicpd.org, current playlist section:*

        ``swap {SONG1} {SONG2}``

        Swaps the positions of ``SONG1`` and ``SONG2``.
    """
    tracks = context.core.tracklist.tracks.get()
    song1 = tracks[songpos1]
    song2 = tracks[songpos2]
    del tracks[songpos1]
    tracks.insert(songpos1, song2)
    del tracks[songpos2]
    tracks.insert(songpos2, song1)
    context.core.tracklist.clear()
    context.core.tracklist.add(tracks)


@protocol.commands.add('swapid', tlid1=protocol.UINT, tlid2=protocol.UINT)
def swapid(context, tlid1, tlid2):
    """
    *musicpd.org, current playlist section:*

        ``swapid {SONG1} {SONG2}``

        Swaps the positions of ``SONG1`` and ``SONG2`` (both song ids).
    """
    tl_tracks1 = context.core.tracklist.filter(tlid=[tlid1]).get()
    tl_tracks2 = context.core.tracklist.filter(tlid=[tlid2]).get()
    if not tl_tracks1 or not tl_tracks2:
        raise exceptions.MpdNoExistError('No such song')
    position1 = context.core.tracklist.index(tl_tracks1[0]).get()
    position2 = context.core.tracklist.index(tl_tracks2[0]).get()
    swap(context, position1, position2)


# TODO: add at least reflection tests before adding NotImplemented version
# @protocol.commands.add(
#     'prio', priority=protocol.UINT, position=protocol.RANGE)
def prio(context, priority, position):
    """
    *musicpd.org, current playlist section:*

        ``prio {PRIORITY} {START:END...}``

        Set the priority of the specified songs. A higher priority means that
        it will be played first when "random" mode is enabled.

        A priority is an integer between 0 and 255. The default priority of new
        songs is 0.
    """
    pass


# TODO: add at least reflection tests before adding NotImplemented version
# @protocol.commands.add('prioid')
def prioid(context, *args):
    """
    *musicpd.org, current playlist section:*

        ``prioid {PRIORITY} {ID...}``

        Same as prio, but address the songs with their id.
    """
    pass


# TODO: add at least reflection tests before adding NotImplemented version
# @protocol.commands.add('addtagid', tlid=protocol.UINT)
def addtagid(context, tlid, tag, value):
    """
    *musicpd.org, current playlist section:*

        ``addtagid {SONGID} {TAG} {VALUE}``

        Adds a tag to the specified song. Editing song tags is only possible
        for remote songs. This change is volatile: it may be overwritten by
        tags received from the server, and the data is gone when the song gets
        removed from the queue.
    """
    pass


# TODO: add at least reflection tests before adding NotImplemented version
# @protocol.commands.add('cleartagid', tlid=protocol.UINT)
def cleartagid(context, tlid, tag):
    """
    *musicpd.org, current playlist section:*

        ``cleartagid {SONGID} [TAG]``

        Removes tags from the specified song. If TAG is not specified, then all
        tag values will be removed. Editing song tags is only possible for
        remote songs.
    """
    pass

########NEW FILE########
__FILENAME__ = music_db
from __future__ import unicode_literals

import functools
import itertools

from mopidy.models import Track
from mopidy.mpd import exceptions, protocol, translator

_SEARCH_MAPPING = {
    'album': 'album',
    'albumartist': 'albumartist',
    'any': 'any',
    'artist': 'artist',
    'comment': 'comment',
    'composer': 'composer',
    'date': 'date',
    'file': 'uri',
    'filename': 'uri',
    'genre': 'genre',
    'performer': 'performer',
    'title': 'track_name',
    'track': 'track_no'}

_LIST_MAPPING = {
    'album': 'album',
    'albumartist': 'albumartist',
    'artist': 'artist',
    'composer': 'composer',
    'date': 'date',
    'genre': 'genre',
    'performer': 'performer'}


def _query_from_mpd_search_parameters(parameters, mapping):
    query = {}
    parameters = list(parameters)
    while parameters:
        # TODO: does it matter that this is now case insensitive
        field = mapping.get(parameters.pop(0).lower())
        if not field:
            raise exceptions.MpdArgError('incorrect arguments')
        if not parameters:
            raise ValueError
        query.setdefault(field, []).append(parameters.pop(0))
    return query


def _get_field(field, search_results):
    return list(itertools.chain(*[getattr(r, field) for r in search_results]))


_get_albums = functools.partial(_get_field, 'albums')
_get_artists = functools.partial(_get_field, 'artists')
_get_tracks = functools.partial(_get_field, 'tracks')


def _album_as_track(album):
    return Track(
        uri=album.uri,
        name='Album: ' + album.name,
        artists=album.artists,
        album=album,
        date=album.date)


def _artist_as_track(artist):
    return Track(
        uri=artist.uri,
        name='Artist: ' + artist.name,
        artists=[artist])


@protocol.commands.add('count')
def count(context, *args):
    """
    *musicpd.org, music database section:*

        ``count {TAG} {NEEDLE}``

        Counts the number of songs and their total playtime in the db
        matching ``TAG`` exactly.

    *GMPC:*

    - does not add quotes around the tag argument.
    - use multiple tag-needle pairs to make more specific searches.
    """
    try:
        query = _query_from_mpd_search_parameters(args, _SEARCH_MAPPING)
    except ValueError:
        raise exceptions.MpdArgError('incorrect arguments')
    results = context.core.library.find_exact(**query).get()
    result_tracks = _get_tracks(results)
    return [
        ('songs', len(result_tracks)),
        ('playtime', sum(track.length for track in result_tracks) / 1000),
    ]


@protocol.commands.add('find')
def find(context, *args):
    """
    *musicpd.org, music database section:*

        ``find {TYPE} {WHAT}``

        Finds songs in the db that are exactly ``WHAT``. ``TYPE`` can be any
        tag supported by MPD, or one of the two special parameters - ``file``
        to search by full path (relative to database root), and ``any`` to
        match against all available tags. ``WHAT`` is what to find.

    *GMPC:*

    - does not add quotes around the field argument.
    - also uses ``find album "[ALBUM]" artist "[ARTIST]"`` to list album
      tracks.

    *ncmpc:*

    - does not add quotes around the field argument.
    - capitalizes the type argument.

    *ncmpcpp:*

    - also uses the search type "date".
    - uses "file" instead of "filename".
    """
    try:
        query = _query_from_mpd_search_parameters(args, _SEARCH_MAPPING)
    except ValueError:
        return

    results = context.core.library.find_exact(**query).get()
    result_tracks = []
    if ('artist' not in query and
            'albumartist' not in query and
            'composer' not in query and
            'performer' not in query):
        result_tracks += [_artist_as_track(a) for a in _get_artists(results)]
    if 'album' not in query:
        result_tracks += [_album_as_track(a) for a in _get_albums(results)]
    result_tracks += _get_tracks(results)
    return translator.tracks_to_mpd_format(result_tracks)


@protocol.commands.add('findadd')
def findadd(context, *args):
    """
    *musicpd.org, music database section:*

        ``findadd {TYPE} {WHAT}``

        Finds songs in the db that are exactly ``WHAT`` and adds them to
        current playlist. Parameters have the same meaning as for ``find``.
    """
    try:
        query = _query_from_mpd_search_parameters(args, _SEARCH_MAPPING)
    except ValueError:
        return
    results = context.core.library.find_exact(**query).get()
    context.core.tracklist.add(_get_tracks(results))


@protocol.commands.add('list')
def list_(context, *args):
    """
    *musicpd.org, music database section:*

        ``list {TYPE} [ARTIST]``

        Lists all tags of the specified type. ``TYPE`` should be ``album``,
        ``artist``, ``albumartist``, ``date``, or ``genre``.

        ``ARTIST`` is an optional parameter when type is ``album``,
        ``date``, or ``genre``. This filters the result list by an artist.

    *Clarifications:*

        The musicpd.org documentation for ``list`` is far from complete. The
        command also supports the following variant:

        ``list {TYPE} {QUERY}``

        Where ``QUERY`` applies to all ``TYPE``. ``QUERY`` is one or more pairs
        of a field name and a value. If the ``QUERY`` consists of more than one
        pair, the pairs are AND-ed together to find the result. Examples of
        valid queries and what they should return:

        ``list "artist" "artist" "ABBA"``
            List artists where the artist name is "ABBA". Response::

                Artist: ABBA
                OK

        ``list "album" "artist" "ABBA"``
            Lists albums where the artist name is "ABBA". Response::

                Album: More ABBA Gold: More ABBA Hits
                Album: Absolute More Christmas
                Album: Gold: Greatest Hits
                OK

        ``list "artist" "album" "Gold: Greatest Hits"``
            Lists artists where the album name is "Gold: Greatest Hits".
            Response::

                Artist: ABBA
                OK

        ``list "artist" "artist" "ABBA" "artist" "TLC"``
            Lists artists where the artist name is "ABBA" *and* "TLC". Should
            never match anything. Response::

                OK

        ``list "date" "artist" "ABBA"``
            Lists dates where artist name is "ABBA". Response::

                Date:
                Date: 1992
                Date: 1993
                OK

        ``list "date" "artist" "ABBA" "album" "Gold: Greatest Hits"``
            Lists dates where artist name is "ABBA" and album name is "Gold:
            Greatest Hits". Response::

                Date: 1992
                OK

        ``list "genre" "artist" "The Rolling Stones"``
            Lists genres where artist name is "The Rolling Stones". Response::

                Genre:
                Genre: Rock
                OK

    *GMPC:*

    - does not add quotes around the field argument.

    *ncmpc:*

    - does not add quotes around the field argument.
    - capitalizes the field argument.
    """
    parameters = list(args)
    if not parameters:
        raise exceptions.MpdArgError('incorrect arguments')
    field = parameters.pop(0).lower()

    if field not in _LIST_MAPPING:
        raise exceptions.MpdArgError('incorrect arguments')

    if len(parameters) == 1:
        if field != 'album':
            raise exceptions.MpdArgError('should be "Album" for 3 arguments')
        return _list_artist(context, {'artist': parameters})

    try:
        query = _query_from_mpd_search_parameters(parameters, _LIST_MAPPING)
    except exceptions.MpdArgError as e:
        e.message = 'not able to parse args'
        raise
    except ValueError:
        return

    if field == 'artist':
        return _list_artist(context, query)
    if field == 'albumartist':
        return _list_albumartist(context, query)
    elif field == 'album':
        return _list_album(context, query)
    elif field == 'composer':
        return _list_composer(context, query)
    elif field == 'performer':
        return _list_performer(context, query)
    elif field == 'date':
        return _list_date(context, query)
    elif field == 'genre':
        return _list_genre(context, query)


def _list_artist(context, query):
    artists = set()
    results = context.core.library.find_exact(**query).get()
    for track in _get_tracks(results):
        for artist in track.artists:
            if artist.name:
                artists.add(('Artist', artist.name))
    return artists


def _list_albumartist(context, query):
    albumartists = set()
    results = context.core.library.find_exact(**query).get()
    for track in _get_tracks(results):
        if track.album:
            for artist in track.album.artists:
                if artist.name:
                    albumartists.add(('AlbumArtist', artist.name))
    return albumartists


def _list_album(context, query):
    albums = set()
    results = context.core.library.find_exact(**query).get()
    for track in _get_tracks(results):
        if track.album and track.album.name:
            albums.add(('Album', track.album.name))
    return albums


def _list_composer(context, query):
    composers = set()
    results = context.core.library.find_exact(**query).get()
    for track in _get_tracks(results):
        for composer in track.composers:
            if composer.name:
                composers.add(('Composer', composer.name))
    return composers


def _list_performer(context, query):
    performers = set()
    results = context.core.library.find_exact(**query).get()
    for track in _get_tracks(results):
        for performer in track.performers:
            if performer.name:
                performers.add(('Performer', performer.name))
    return performers


def _list_date(context, query):
    dates = set()
    results = context.core.library.find_exact(**query).get()
    for track in _get_tracks(results):
        if track.date:
            dates.add(('Date', track.date))
    return dates


def _list_genre(context, query):
    genres = set()
    results = context.core.library.find_exact(**query).get()
    for track in _get_tracks(results):
        if track.genre:
            genres.add(('Genre', track.genre))
    return genres


@protocol.commands.add('listall')
def listall(context, uri=None):
    """
    *musicpd.org, music database section:*

        ``listall [URI]``

        Lists all songs and directories in ``URI``.
    """
    result = []
    for path, track_ref in context.browse(uri, lookup=False):
        if not track_ref:
            result.append(('directory', path))
        else:
            result.append(('file', track_ref.uri))

    if not result:
        raise exceptions.MpdNoExistError('Not found')
    return result


@protocol.commands.add('listallinfo')
def listallinfo(context, uri=None):
    """
    *musicpd.org, music database section:*

        ``listallinfo [URI]``

        Same as ``listall``, except it also returns metadata info in the
        same format as ``lsinfo``.
    """
    result = []
    for path, lookup_future in context.browse(uri):
        if not lookup_future:
            result.append(('directory', path))
        else:
            for track in lookup_future.get():
                result.extend(translator.track_to_mpd_format(track))
    return result


@protocol.commands.add('lsinfo')
def lsinfo(context, uri=None):
    """
    *musicpd.org, music database section:*

        ``lsinfo [URI]``

        Lists the contents of the directory ``URI``.

        When listing the root directory, this currently returns the list of
        stored playlists. This behavior is deprecated; use
        ``listplaylists`` instead.

    MPD returns the same result, including both playlists and the files and
    directories located at the root level, for both ``lsinfo``, ``lsinfo
    ""``, and ``lsinfo "/"``.
    """
    result = []
    if uri in (None, '', '/'):
        result.extend(protocol.stored_playlists.listplaylists(context))

    for path, lookup_future in context.browse(uri, recursive=False):
        if not lookup_future:
            result.append(('directory', path.lstrip('/')))
        else:
            tracks = lookup_future.get()
            if tracks:
                result.extend(translator.track_to_mpd_format(tracks[0]))

    if not result:
        raise exceptions.MpdNoExistError('Not found')
    return result


@protocol.commands.add('rescan')
def rescan(context, uri=None):
    """
    *musicpd.org, music database section:*

        ``rescan [URI]``

        Same as ``update``, but also rescans unmodified files.
    """
    return {'updating_db': 0}  # TODO


@protocol.commands.add('search')
def search(context, *args):
    """
    *musicpd.org, music database section:*

        ``search {TYPE} {WHAT} [...]``

        Searches for any song that contains ``WHAT``. Parameters have the same
        meaning as for ``find``, except that search is not case sensitive.

    *GMPC:*

    - does not add quotes around the field argument.
    - uses the undocumented field ``any``.
    - searches for multiple words like this::

        search any "foo" any "bar" any "baz"

    *ncmpc:*

    - does not add quotes around the field argument.
    - capitalizes the field argument.

    *ncmpcpp:*

    - also uses the search type "date".
    - uses "file" instead of "filename".
    """
    try:
        query = _query_from_mpd_search_parameters(args, _SEARCH_MAPPING)
    except ValueError:
        return
    results = context.core.library.search(**query).get()
    artists = [_artist_as_track(a) for a in _get_artists(results)]
    albums = [_album_as_track(a) for a in _get_albums(results)]
    tracks = _get_tracks(results)
    return translator.tracks_to_mpd_format(artists + albums + tracks)


@protocol.commands.add('searchadd')
def searchadd(context, *args):
    """
    *musicpd.org, music database section:*

        ``searchadd {TYPE} {WHAT} [...]``

        Searches for any song that contains ``WHAT`` in tag ``TYPE`` and adds
        them to current playlist.

        Parameters have the same meaning as for ``find``, except that search is
        not case sensitive.
    """
    try:
        query = _query_from_mpd_search_parameters(args, _SEARCH_MAPPING)
    except ValueError:
        return
    results = context.core.library.search(**query).get()
    context.core.tracklist.add(_get_tracks(results))


@protocol.commands.add('searchaddpl')
def searchaddpl(context, *args):
    """
    *musicpd.org, music database section:*

        ``searchaddpl {NAME} {TYPE} {WHAT} [...]``

        Searches for any song that contains ``WHAT`` in tag ``TYPE`` and adds
        them to the playlist named ``NAME``.

        If a playlist by that name doesn't exist it is created.

        Parameters have the same meaning as for ``find``, except that search is
        not case sensitive.
    """
    parameters = list(args)
    if not parameters:
        raise exceptions.MpdArgError('incorrect arguments')
    playlist_name = parameters.pop(0)
    try:
        query = _query_from_mpd_search_parameters(parameters, _SEARCH_MAPPING)
    except ValueError:
        return
    results = context.core.library.search(**query).get()

    playlist = context.lookup_playlist_from_name(playlist_name)
    if not playlist:
        playlist = context.core.playlists.create(playlist_name).get()
    tracks = list(playlist.tracks) + _get_tracks(results)
    playlist = playlist.copy(tracks=tracks)
    context.core.playlists.save(playlist)


@protocol.commands.add('update')
def update(context, uri=None):
    """
    *musicpd.org, music database section:*

        ``update [URI]``

        Updates the music database: find new files, remove deleted files,
        update modified files.

        ``URI`` is a particular directory or song/file to update. If you do
        not specify it, everything is updated.

        Prints ``updating_db: JOBID`` where ``JOBID`` is a positive number
        identifying the update job. You can read the current job id in the
        ``status`` response.
    """
    return {'updating_db': 0}  # TODO


# TODO: add at least reflection tests before adding NotImplemented version
# @protocol.commands.add('readcomments')
def readcomments(context, uri):
    """
    *musicpd.org, music database section:*

        ``readcomments [URI]``

        Read "comments" (i.e. key-value pairs) from the file specified by
        "URI". This "URI" can be a path relative to the music directory or a
        URL in the form "file:///foo/bar.ogg".

        This command may be used to list metadata of remote files (e.g. URI
        beginning with "http://" or "smb://").

        The response consists of lines in the form "KEY: VALUE". Comments with
        suspicious characters (e.g. newlines) are ignored silently.

        The meaning of these depends on the codec, and not all decoder plugins
        support it. For example, on Ogg files, this lists the Vorbis comments.
    """
    pass

########NEW FILE########
__FILENAME__ = playback
from __future__ import unicode_literals

import warnings

from mopidy.core import PlaybackState
from mopidy.mpd import exceptions, protocol


@protocol.commands.add('consume', state=protocol.BOOL)
def consume(context, state):
    """
    *musicpd.org, playback section:*

        ``consume {STATE}``

        Sets consume state to ``STATE``, ``STATE`` should be 0 or
        1. When consume is activated, each song played is removed from
        playlist.
    """
    context.core.tracklist.consume = state


@protocol.commands.add('crossfade', seconds=protocol.UINT)
def crossfade(context, seconds):
    """
    *musicpd.org, playback section:*

        ``crossfade {SECONDS}``

        Sets crossfading between songs.
    """
    raise exceptions.MpdNotImplemented  # TODO


# TODO: add at least reflection tests before adding NotImplemented version
# @protocol.commands.add('mixrampdb')
def mixrampdb(context, decibels):
    """
    *musicpd.org, playback section:*

        ``mixrampdb {deciBels}``

    Sets the threshold at which songs will be overlapped. Like crossfading but
    doesn't fade the track volume, just overlaps. The songs need to have
    MixRamp tags added by an external tool. 0dB is the normalized maximum
    volume so use negative values, I prefer -17dB. In the absence of mixramp
    tags crossfading will be used. See http://sourceforge.net/projects/mixramp
    """
    pass


# TODO: add at least reflection tests before adding NotImplemented version
# @protocol.commands.add('mixrampdelay', seconds=protocol.UINT)
def mixrampdelay(context, seconds):
    """
    *musicpd.org, playback section:*

        ``mixrampdelay {SECONDS}``

        Additional time subtracted from the overlap calculated by mixrampdb. A
        value of "nan" disables MixRamp overlapping and falls back to
        crossfading.
    """
    pass


@protocol.commands.add('next')
def next_(context):
    """
    *musicpd.org, playback section:*

        ``next``

        Plays next song in the playlist.

    *MPD's behaviour when affected by repeat/random/single/consume:*

        Given a playlist of three tracks numbered 1, 2, 3, and a currently
        playing track ``c``. ``next_track`` is defined at the track that
        will be played upon calls to ``next``.

        Tests performed on MPD 0.15.4-1ubuntu3.

        ======  ======  ======  =======  =====  =====  =====  =====
                    Inputs                    next_track
        -------------------------------  -------------------  -----
        repeat  random  single  consume  c = 1  c = 2  c = 3  Notes
        ======  ======  ======  =======  =====  =====  =====  =====
        T       T       T       T        2      3      EOPL
        T       T       T       .        Rand   Rand   Rand   [1]
        T       T       .       T        Rand   Rand   Rand   [4]
        T       T       .       .        Rand   Rand   Rand   [4]
        T       .       T       T        2      3      EOPL
        T       .       T       .        2      3      1
        T       .       .       T        3      3      EOPL
        T       .       .       .        2      3      1
        .       T       T       T        Rand   Rand   Rand   [3]
        .       T       T       .        Rand   Rand   Rand   [3]
        .       T       .       T        Rand   Rand   Rand   [2]
        .       T       .       .        Rand   Rand   Rand   [2]
        .       .       T       T        2      3      EOPL
        .       .       T       .        2      3      EOPL
        .       .       .       T        2      3      EOPL
        .       .       .       .        2      3      EOPL
        ======  ======  ======  =======  =====  =====  =====  =====

        - When end of playlist (EOPL) is reached, the current track is
          unset.
        - [1] When *random* and *single* is combined, ``next`` selects
          a track randomly at each invocation, and not just the next track
          in an internal prerandomized playlist.
        - [2] When *random* is active, ``next`` will skip through
          all tracks in the playlist in random order, and finally EOPL is
          reached.
        - [3] *single* has no effect in combination with *random*
          alone, or *random* and *consume*.
        - [4] When *random* and *repeat* is active, EOPL is never
          reached, but the playlist is played again, in the same random
          order as the first time.

    """
    return context.core.playback.next().get()


@protocol.commands.add('pause', state=protocol.BOOL)
def pause(context, state=None):
    """
    *musicpd.org, playback section:*

        ``pause {PAUSE}``

        Toggles pause/resumes playing, ``PAUSE`` is 0 or 1.

    *MPDroid:*

    - Calls ``pause`` without any arguments to toogle pause.
    """
    if state is None:
        warnings.warn(
            'The use of pause command w/o the PAUSE argument is deprecated.',
            DeprecationWarning)

        if (context.core.playback.state.get() == PlaybackState.PLAYING):
            context.core.playback.pause()
        elif (context.core.playback.state.get() == PlaybackState.PAUSED):
            context.core.playback.resume()
    elif state:
        context.core.playback.pause()
    else:
        context.core.playback.resume()


@protocol.commands.add('play', tlid=protocol.INT)
def play(context, tlid=None):
    """
    *musicpd.org, playback section:*

        ``play [SONGPOS]``

        Begins playing the playlist at song number ``SONGPOS``.

    The original MPD server resumes from the paused state on ``play``
    without arguments.

    *Clarifications:*

    - ``play "-1"`` when playing is ignored.
    - ``play "-1"`` when paused resumes playback.
    - ``play "-1"`` when stopped with a current track starts playback at the
      current track.
    - ``play "-1"`` when stopped without a current track, e.g. after playlist
      replacement, starts playback at the first track.

    *BitMPC:*

    - issues ``play 6`` without quotes around the argument.
    """
    if tlid is None:
        return context.core.playback.play().get()
    elif tlid == -1:
        return _play_minus_one(context)

    try:
        tl_track = context.core.tracklist.slice(tlid, tlid + 1).get()[0]
        return context.core.playback.play(tl_track).get()
    except IndexError:
        raise exceptions.MpdArgError('Bad song index')


def _play_minus_one(context):
    if (context.core.playback.state.get() == PlaybackState.PLAYING):
        return  # Nothing to do
    elif (context.core.playback.state.get() == PlaybackState.PAUSED):
        return context.core.playback.resume().get()
    elif context.core.playback.current_tl_track.get() is not None:
        tl_track = context.core.playback.current_tl_track.get()
        return context.core.playback.play(tl_track).get()
    elif context.core.tracklist.slice(0, 1).get():
        tl_track = context.core.tracklist.slice(0, 1).get()[0]
        return context.core.playback.play(tl_track).get()
    else:
        return  # Fail silently


@protocol.commands.add('playid', tlid=protocol.INT)
def playid(context, tlid):
    """
    *musicpd.org, playback section:*

        ``playid [SONGID]``

        Begins playing the playlist at song ``SONGID``.

    *Clarifications:*

    - ``playid "-1"`` when playing is ignored.
    - ``playid "-1"`` when paused resumes playback.
    - ``playid "-1"`` when stopped with a current track starts playback at the
      current track.
    - ``playid "-1"`` when stopped without a current track, e.g. after playlist
      replacement, starts playback at the first track.
    """
    if tlid == -1:
        return _play_minus_one(context)
    tl_tracks = context.core.tracklist.filter(tlid=[tlid]).get()
    if not tl_tracks:
        raise exceptions.MpdNoExistError('No such song')
    return context.core.playback.play(tl_tracks[0]).get()


@protocol.commands.add('previous')
def previous(context):
    """
    *musicpd.org, playback section:*

        ``previous``

        Plays previous song in the playlist.

    *MPD's behaviour when affected by repeat/random/single/consume:*

        Given a playlist of three tracks numbered 1, 2, 3, and a currently
        playing track ``c``. ``previous_track`` is defined at the track
        that will be played upon ``previous`` calls.

        Tests performed on MPD 0.15.4-1ubuntu3.

        ======  ======  ======  =======  =====  =====  =====
                    Inputs                  previous_track
        -------------------------------  -------------------
        repeat  random  single  consume  c = 1  c = 2  c = 3
        ======  ======  ======  =======  =====  =====  =====
        T       T       T       T        Rand?  Rand?  Rand?
        T       T       T       .        3      1      2
        T       T       .       T        Rand?  Rand?  Rand?
        T       T       .       .        3      1      2
        T       .       T       T        3      1      2
        T       .       T       .        3      1      2
        T       .       .       T        3      1      2
        T       .       .       .        3      1      2
        .       T       T       T        c      c      c
        .       T       T       .        c      c      c
        .       T       .       T        c      c      c
        .       T       .       .        c      c      c
        .       .       T       T        1      1      2
        .       .       T       .        1      1      2
        .       .       .       T        1      1      2
        .       .       .       .        1      1      2
        ======  ======  ======  =======  =====  =====  =====

        - If :attr:`time_position` of the current track is 15s or more,
          ``previous`` should do a seek to time position 0.

    """
    return context.core.playback.previous().get()


@protocol.commands.add('random', state=protocol.BOOL)
def random(context, state):
    """
    *musicpd.org, playback section:*

        ``random {STATE}``

        Sets random state to ``STATE``, ``STATE`` should be 0 or 1.
    """
    context.core.tracklist.random = state


@protocol.commands.add('repeat', state=protocol.BOOL)
def repeat(context, state):
    """
    *musicpd.org, playback section:*

        ``repeat {STATE}``

        Sets repeat state to ``STATE``, ``STATE`` should be 0 or 1.
    """
    context.core.tracklist.repeat = state


@protocol.commands.add('replay_gain_mode')
def replay_gain_mode(context, mode):
    """
    *musicpd.org, playback section:*

        ``replay_gain_mode {MODE}``

        Sets the replay gain mode. One of ``off``, ``track``, ``album``.

        Changing the mode during playback may take several seconds, because
        the new settings does not affect the buffered data.

        This command triggers the options idle event.
    """
    raise exceptions.MpdNotImplemented  # TODO


@protocol.commands.add('replay_gain_status')
def replay_gain_status(context):
    """
    *musicpd.org, playback section:*

        ``replay_gain_status``

        Prints replay gain options. Currently, only the variable
        ``replay_gain_mode`` is returned.
    """
    return 'off'  # TODO


@protocol.commands.add('seek', tlid=protocol.UINT, seconds=protocol.UINT)
def seek(context, tlid, seconds):
    """
    *musicpd.org, playback section:*

        ``seek {SONGPOS} {TIME}``

        Seeks to the position ``TIME`` (in seconds) of entry ``SONGPOS`` in
        the playlist.

    *Droid MPD:*

    - issues ``seek 1 120`` without quotes around the arguments.
    """
    tl_track = context.core.playback.current_tl_track.get()
    if context.core.tracklist.index(tl_track).get() != tlid:
        play(context, tlid)
    context.core.playback.seek(seconds * 1000).get()


@protocol.commands.add('seekid', tlid=protocol.UINT, seconds=protocol.UINT)
def seekid(context, tlid, seconds):
    """
    *musicpd.org, playback section:*

        ``seekid {SONGID} {TIME}``

        Seeks to the position ``TIME`` (in seconds) of song ``SONGID``.
    """
    tl_track = context.core.playback.current_tl_track.get()
    if not tl_track or tl_track.tlid != tlid:
        playid(context, tlid)
    context.core.playback.seek(seconds * 1000).get()


@protocol.commands.add('seekcur')
def seekcur(context, time):
    """
    *musicpd.org, playback section:*

        ``seekcur {TIME}``

        Seeks to the position ``TIME`` within the current song. If prefixed by
        '+' or '-', then the time is relative to the current playing position.
    """
    if time.startswith(('+', '-')):
        position = context.core.playback.time_position.get()
        position += protocol.INT(time) * 1000
        context.core.playback.seek(position).get()
    else:
        position = protocol.UINT(time) * 1000
        context.core.playback.seek(position).get()


@protocol.commands.add('setvol', volume=protocol.INT)
def setvol(context, volume):
    """
    *musicpd.org, playback section:*

        ``setvol {VOL}``

        Sets volume to ``VOL``, the range of volume is 0-100.

    *Droid MPD:*

    - issues ``setvol 50`` without quotes around the argument.
    """
    # NOTE: we use INT as clients can pass in +N etc.
    context.core.playback.volume = min(max(0, volume), 100)


@protocol.commands.add('single', state=protocol.BOOL)
def single(context, state):
    """
    *musicpd.org, playback section:*

        ``single {STATE}``

        Sets single state to ``STATE``, ``STATE`` should be 0 or 1. When
        single is activated, playback is stopped after current song, or
        song is repeated if the ``repeat`` mode is enabled.
    """
    context.core.tracklist.single = state


@protocol.commands.add('stop')
def stop(context):
    """
    *musicpd.org, playback section:*

        ``stop``

        Stops playing.
    """
    context.core.playback.stop()

########NEW FILE########
__FILENAME__ = reflection
from __future__ import unicode_literals

from mopidy.mpd import exceptions, protocol


@protocol.commands.add('config', list_command=False)
def config(context):
    """
    *musicpd.org, reflection section:*

        ``config``

        Dumps configuration values that may be interesting for the client. This
        command is only permitted to "local" clients (connected via UNIX domain
        socket).
    """
    raise exceptions.MpdPermissionError(command='config')


@protocol.commands.add('commands', auth_required=False)
def commands(context):
    """
    *musicpd.org, reflection section:*

        ``commands``

        Shows which commands the current user has access to.
    """
    command_names = set()
    for name, handler in protocol.commands.handlers.items():
        if not handler.list_command:
            continue
        if context.dispatcher.authenticated or not handler.auth_required:
            command_names.add(name)

    return [
        ('command', command_name) for command_name in sorted(command_names)]


@protocol.commands.add('decoders')
def decoders(context):
    """
    *musicpd.org, reflection section:*

        ``decoders``

        Print a list of decoder plugins, followed by their supported
        suffixes and MIME types. Example response::

            plugin: mad
            suffix: mp3
            suffix: mp2
            mime_type: audio/mpeg
            plugin: mpcdec
            suffix: mpc

    *Clarifications:*

    - ncmpcpp asks for decoders the first time you open the browse view. By
      returning nothing and OK instead of an not implemented error, we avoid
      "Not implemented" showing up in the ncmpcpp interface, and we get the
      list of playlists without having to enter the browse interface twice.
    """
    return  # TODO


@protocol.commands.add('notcommands', auth_required=False)
def notcommands(context):
    """
    *musicpd.org, reflection section:*

        ``notcommands``

        Shows which commands the current user does not have access to.
    """
    command_names = set(['config', 'kill'])  # No permission to use
    for name, handler in protocol.commands.handlers.items():
        if not handler.list_command:
            continue
        if not context.dispatcher.authenticated and handler.auth_required:
            command_names.add(name)

    return [
        ('command', command_name) for command_name in sorted(command_names)]


@protocol.commands.add('tagtypes')
def tagtypes(context):
    """
    *musicpd.org, reflection section:*

        ``tagtypes``

        Shows a list of available song metadata.
    """
    pass  # TODO


@protocol.commands.add('urlhandlers')
def urlhandlers(context):
    """
    *musicpd.org, reflection section:*

        ``urlhandlers``

        Gets a list of available URL handlers.
    """
    return [
        ('handler', uri_scheme)
        for uri_scheme in context.core.uri_schemes.get()]

########NEW FILE########
__FILENAME__ = status
from __future__ import unicode_literals

import pykka

from mopidy.core import PlaybackState
from mopidy.mpd import exceptions, protocol, translator

#: Subsystems that can be registered with idle command.
SUBSYSTEMS = [
    'database', 'mixer', 'options', 'output', 'player', 'playlist',
    'stored_playlist', 'update']


@protocol.commands.add('clearerror')
def clearerror(context):
    """
    *musicpd.org, status section:*

        ``clearerror``

        Clears the current error message in status (this is also
        accomplished by any command that starts playback).
    """
    raise exceptions.MpdNotImplemented  # TODO


@protocol.commands.add('currentsong')
def currentsong(context):
    """
    *musicpd.org, status section:*

        ``currentsong``

        Displays the song info of the current song (same song that is
        identified in status).
    """
    tl_track = context.core.playback.current_tl_track.get()
    if tl_track is not None:
        position = context.core.tracklist.index(tl_track).get()
        return translator.track_to_mpd_format(tl_track, position=position)


@protocol.commands.add('idle', list_command=False)
def idle(context, *subsystems):
    """
    *musicpd.org, status section:*

        ``idle [SUBSYSTEMS...]``

        Waits until there is a noteworthy change in one or more of MPD's
        subsystems. As soon as there is one, it lists all changed systems
        in a line in the format ``changed: SUBSYSTEM``, where ``SUBSYSTEM``
        is one of the following:

        - ``database``: the song database has been modified after update.
        - ``update``: a database update has started or finished. If the
          database was modified during the update, the database event is
          also emitted.
        - ``stored_playlist``: a stored playlist has been modified,
          renamed, created or deleted
        - ``playlist``: the current playlist has been modified
        - ``player``: the player has been started, stopped or seeked
        - ``mixer``: the volume has been changed
        - ``output``: an audio output has been enabled or disabled
        - ``options``: options like repeat, random, crossfade, replay gain

        While a client is waiting for idle results, the server disables
        timeouts, allowing a client to wait for events as long as MPD runs.
        The idle command can be canceled by sending the command ``noidle``
        (no other commands are allowed). MPD will then leave idle mode and
        print results immediately; might be empty at this time.

        If the optional ``SUBSYSTEMS`` argument is used, MPD will only send
        notifications when something changed in one of the specified
        subsystems.
    """
    # TODO: test against valid subsystems

    if not subsystems:
        subsystems = SUBSYSTEMS

    for subsystem in subsystems:
        context.subscriptions.add(subsystem)

    active = context.subscriptions.intersection(context.events)
    if not active:
        context.session.prevent_timeout = True
        return

    response = []
    context.events = set()
    context.subscriptions = set()

    for subsystem in active:
        response.append('changed: %s' % subsystem)
    return response


@protocol.commands.add('noidle', list_command=False)
def noidle(context):
    """See :meth:`_status_idle`."""
    if not context.subscriptions:
        return
    context.subscriptions = set()
    context.events = set()
    context.session.prevent_timeout = False


@protocol.commands.add('stats')
def stats(context):
    """
    *musicpd.org, status section:*

        ``stats``

        Displays statistics.

        - ``artists``: number of artists
        - ``songs``: number of albums
        - ``uptime``: daemon uptime in seconds
        - ``db_playtime``: sum of all song times in the db
        - ``db_update``: last db update in UNIX time
        - ``playtime``: time length of music played
    """
    return {
        'artists': 0,  # TODO
        'albums': 0,  # TODO
        'songs': 0,  # TODO
        'uptime': 0,  # TODO
        'db_playtime': 0,  # TODO
        'db_update': 0,  # TODO
        'playtime': 0,  # TODO
    }


@protocol.commands.add('status')
def status(context):
    """
    *musicpd.org, status section:*

        ``status``

        Reports the current status of the player and the volume level.

        - ``volume``: 0-100 or -1
        - ``repeat``: 0 or 1
        - ``single``: 0 or 1
        - ``consume``: 0 or 1
        - ``playlist``: 31-bit unsigned integer, the playlist version
          number
        - ``playlistlength``: integer, the length of the playlist
        - ``state``: play, stop, or pause
        - ``song``: playlist song number of the current song stopped on or
          playing
        - ``songid``: playlist songid of the current song stopped on or
          playing
        - ``nextsong``: playlist song number of the next song to be played
        - ``nextsongid``: playlist songid of the next song to be played
        - ``time``: total time elapsed (of current playing/paused song)
        - ``elapsed``: Total time elapsed within the current song, but with
          higher resolution.
        - ``bitrate``: instantaneous bitrate in kbps
        - ``xfade``: crossfade in seconds
        - ``audio``: sampleRate``:bits``:channels
        - ``updatings_db``: job id
        - ``error``: if there is an error, returns message here

    *Clarifications based on experience implementing*
        - ``volume``: can also be -1 if no output is set.
        - ``elapsed``: Higher resolution means time in seconds with three
          decimal places for millisecond precision.
    """
    futures = {
        'tracklist.length': context.core.tracklist.length,
        'tracklist.version': context.core.tracklist.version,
        'playback.volume': context.core.playback.volume,
        'tracklist.consume': context.core.tracklist.consume,
        'tracklist.random': context.core.tracklist.random,
        'tracklist.repeat': context.core.tracklist.repeat,
        'tracklist.single': context.core.tracklist.single,
        'playback.state': context.core.playback.state,
        'playback.current_tl_track': context.core.playback.current_tl_track,
        'tracklist.index': (
            context.core.tracklist.index(
                context.core.playback.current_tl_track.get())),
        'playback.time_position': context.core.playback.time_position,
    }
    pykka.get_all(futures.values())
    result = [
        ('volume', _status_volume(futures)),
        ('repeat', _status_repeat(futures)),
        ('random', _status_random(futures)),
        ('single', _status_single(futures)),
        ('consume', _status_consume(futures)),
        ('playlist', _status_playlist_version(futures)),
        ('playlistlength', _status_playlist_length(futures)),
        ('xfade', _status_xfade(futures)),
        ('state', _status_state(futures)),
    ]
    if futures['playback.current_tl_track'].get() is not None:
        result.append(('song', _status_songpos(futures)))
        result.append(('songid', _status_songid(futures)))
    if futures['playback.state'].get() in (
            PlaybackState.PLAYING, PlaybackState.PAUSED):
        result.append(('time', _status_time(futures)))
        result.append(('elapsed', _status_time_elapsed(futures)))
        result.append(('bitrate', _status_bitrate(futures)))
    return result


def _status_bitrate(futures):
    current_tl_track = futures['playback.current_tl_track'].get()
    if current_tl_track is None:
        return 0
    if current_tl_track.track.bitrate is None:
        return 0
    return current_tl_track.track.bitrate


def _status_consume(futures):
    if futures['tracklist.consume'].get():
        return 1
    else:
        return 0


def _status_playlist_length(futures):
    return futures['tracklist.length'].get()


def _status_playlist_version(futures):
    return futures['tracklist.version'].get()


def _status_random(futures):
    return int(futures['tracklist.random'].get())


def _status_repeat(futures):
    return int(futures['tracklist.repeat'].get())


def _status_single(futures):
    return int(futures['tracklist.single'].get())


def _status_songid(futures):
    current_tl_track = futures['playback.current_tl_track'].get()
    if current_tl_track is not None:
        return current_tl_track.tlid
    else:
        return _status_songpos(futures)


def _status_songpos(futures):
    return futures['tracklist.index'].get()


def _status_state(futures):
    state = futures['playback.state'].get()
    if state == PlaybackState.PLAYING:
        return 'play'
    elif state == PlaybackState.STOPPED:
        return 'stop'
    elif state == PlaybackState.PAUSED:
        return 'pause'


def _status_time(futures):
    return '%d:%d' % (
        futures['playback.time_position'].get() // 1000,
        _status_time_total(futures) // 1000)


def _status_time_elapsed(futures):
    return '%.3f' % (futures['playback.time_position'].get() / 1000.0)


def _status_time_total(futures):
    current_tl_track = futures['playback.current_tl_track'].get()
    if current_tl_track is None:
        return 0
    elif current_tl_track.track.length is None:
        return 0
    else:
        return current_tl_track.track.length


def _status_volume(futures):
    volume = futures['playback.volume'].get()
    if volume is not None:
        return volume
    else:
        return -1


def _status_xfade(futures):
    return 0  # Not supported

########NEW FILE########
__FILENAME__ = stickers
from __future__ import unicode_literals

from mopidy.mpd import exceptions, protocol


@protocol.commands.add('sticker', list_command=False)
def sticker(context, action, field, uri, name=None, value=None):
    """
    *musicpd.org, sticker section:*

        ``sticker list {TYPE} {URI}``

        Lists the stickers for the specified object.

        ``sticker find {TYPE} {URI} {NAME}``

        Searches the sticker database for stickers with the specified name,
        below the specified directory (``URI``). For each matching song, it
        prints the ``URI`` and that one sticker's value.

        ``sticker get {TYPE} {URI} {NAME}``

        Reads a sticker value for the specified object.

        ``sticker set {TYPE} {URI} {NAME} {VALUE}``

        Adds a sticker value to the specified object. If a sticker item
        with that name already exists, it is replaced.

        ``sticker delete {TYPE} {URI} [NAME]``

        Deletes a sticker value from the specified object. If you do not
        specify a sticker name, all sticker values are deleted.

    """
    # TODO: check that action in ('list', 'find', 'get', 'set', 'delete')
    # TODO: check name/value matches with action
    raise exceptions.MpdNotImplemented  # TODO

########NEW FILE########
__FILENAME__ = stored_playlists
from __future__ import division, unicode_literals

import datetime

from mopidy.mpd import exceptions, protocol, translator


@protocol.commands.add('listplaylist')
def listplaylist(context, name):
    """
    *musicpd.org, stored playlists section:*

        ``listplaylist {NAME}``

        Lists the files in the playlist ``NAME.m3u``.

    Output format::

        file: relative/path/to/file1.flac
        file: relative/path/to/file2.ogg
        file: relative/path/to/file3.mp3
    """
    playlist = context.lookup_playlist_from_name(name)
    if not playlist:
        raise exceptions.MpdNoExistError('No such playlist')
    return ['file: %s' % t.uri for t in playlist.tracks]


@protocol.commands.add('listplaylistinfo')
def listplaylistinfo(context, name):
    """
    *musicpd.org, stored playlists section:*

        ``listplaylistinfo {NAME}``

        Lists songs in the playlist ``NAME.m3u``.

    Output format:

        Standard track listing, with fields: file, Time, Title, Date,
        Album, Artist, Track
    """
    playlist = context.lookup_playlist_from_name(name)
    if not playlist:
        raise exceptions.MpdNoExistError('No such playlist')
    return translator.playlist_to_mpd_format(playlist)


@protocol.commands.add('listplaylists')
def listplaylists(context):
    """
    *musicpd.org, stored playlists section:*

        ``listplaylists``

        Prints a list of the playlist directory.

        After each playlist name the server sends its last modification
        time as attribute ``Last-Modified`` in ISO 8601 format. To avoid
        problems due to clock differences between clients and the server,
        clients should not compare this value with their local clock.

    Output format::

        playlist: a
        Last-Modified: 2010-02-06T02:10:25Z
        playlist: b
        Last-Modified: 2010-02-06T02:11:08Z

    *Clarifications:*

    - ncmpcpp 0.5.10 segfaults if we return 'playlist: ' on a line, so we must
      ignore playlists without names, which isn't very useful anyway.
    """
    result = []
    for playlist in context.core.playlists.playlists.get():
        if not playlist.name:
            continue
        name = context.lookup_playlist_name_from_uri(playlist.uri)
        result.append(('playlist', name))
        result.append(('Last-Modified', _get_last_modified(playlist)))
    return result


# TODO: move to translators?
def _get_last_modified(playlist):
    """Formats last modified timestamp of a playlist for MPD.

    Time in UTC with second precision, formatted in the ISO 8601 format, with
    the "Z" time zone marker for UTC. For example, "1970-01-01T00:00:00Z".
    """
    if playlist.last_modified is None:
        # If unknown, assume the playlist is modified
        dt = datetime.datetime.utcnow()
    else:
        dt = datetime.datetime.utcfromtimestamp(
            playlist.last_modified / 1000.0)
    dt = dt.replace(microsecond=0)
    return '%sZ' % dt.isoformat()


@protocol.commands.add('load', playlist_slice=protocol.RANGE)
def load(context, name, playlist_slice=slice(0, None)):
    """
    *musicpd.org, stored playlists section:*

        ``load {NAME} [START:END]``

        Loads the playlist into the current queue. Playlist plugins are
        supported. A range may be specified to load only a part of the
        playlist.

    *Clarifications:*

    - ``load`` appends the given playlist to the current playlist.

    - MPD 0.17.1 does not support open-ended ranges, i.e. without end
      specified, for the ``load`` command, even though MPD's general range docs
      allows open-ended ranges.

    - MPD 0.17.1 does not fail if the specified range is outside the playlist,
      in either or both ends.
    """
    playlist = context.lookup_playlist_from_name(name)
    if not playlist:
        raise exceptions.MpdNoExistError('No such playlist')
    context.core.tracklist.add(playlist.tracks[playlist_slice])


@protocol.commands.add('playlistadd')
def playlistadd(context, name, uri):
    """
    *musicpd.org, stored playlists section:*

        ``playlistadd {NAME} {URI}``

        Adds ``URI`` to the playlist ``NAME.m3u``.

        ``NAME.m3u`` will be created if it does not exist.
    """
    raise exceptions.MpdNotImplemented  # TODO


@protocol.commands.add('playlistclear')
def playlistclear(context, name):
    """
    *musicpd.org, stored playlists section:*

        ``playlistclear {NAME}``

        Clears the playlist ``NAME.m3u``.
    """
    raise exceptions.MpdNotImplemented  # TODO


@protocol.commands.add('playlistdelete', songpos=protocol.UINT)
def playlistdelete(context, name, songpos):
    """
    *musicpd.org, stored playlists section:*

        ``playlistdelete {NAME} {SONGPOS}``

        Deletes ``SONGPOS`` from the playlist ``NAME.m3u``.
    """
    raise exceptions.MpdNotImplemented  # TODO


@protocol.commands.add(
    'playlistmove', from_pos=protocol.UINT, to_pos=protocol.UINT)
def playlistmove(context, name, from_pos, to_pos):
    """
    *musicpd.org, stored playlists section:*

        ``playlistmove {NAME} {SONGID} {SONGPOS}``

        Moves ``SONGID`` in the playlist ``NAME.m3u`` to the position
        ``SONGPOS``.

    *Clarifications:*

    - The second argument is not a ``SONGID`` as used elsewhere in the protocol
      documentation, but just the ``SONGPOS`` to move *from*, i.e.
      ``playlistmove {NAME} {FROM_SONGPOS} {TO_SONGPOS}``.
    """
    raise exceptions.MpdNotImplemented  # TODO


@protocol.commands.add('rename')
def rename(context, old_name, new_name):
    """
    *musicpd.org, stored playlists section:*

        ``rename {NAME} {NEW_NAME}``

        Renames the playlist ``NAME.m3u`` to ``NEW_NAME.m3u``.
    """
    raise exceptions.MpdNotImplemented  # TODO


@protocol.commands.add('rm')
def rm(context, name):
    """
    *musicpd.org, stored playlists section:*

        ``rm {NAME}``

        Removes the playlist ``NAME.m3u`` from the playlist directory.
    """
    raise exceptions.MpdNotImplemented  # TODO


@protocol.commands.add('save')
def save(context, name):
    """
    *musicpd.org, stored playlists section:*

        ``save {NAME}``

        Saves the current playlist to ``NAME.m3u`` in the playlist
        directory.
    """
    raise exceptions.MpdNotImplemented  # TODO

########NEW FILE########
__FILENAME__ = session
from __future__ import unicode_literals

import logging

from mopidy.mpd import dispatcher, protocol
from mopidy.utils import formatting, network

logger = logging.getLogger(__name__)


class MpdSession(network.LineProtocol):
    """
    The MPD client session. Keeps track of a single client session. Any
    requests from the client is passed on to the MPD request dispatcher.
    """

    terminator = protocol.LINE_TERMINATOR
    encoding = protocol.ENCODING
    delimiter = r'\r?\n'

    def __init__(self, connection, config=None, core=None):
        super(MpdSession, self).__init__(connection)
        self.dispatcher = dispatcher.MpdDispatcher(
            session=self, config=config, core=core)

    def on_start(self):
        logger.info('New MPD connection from [%s]:%s', self.host, self.port)
        self.send_lines(['OK MPD %s' % protocol.VERSION])

    def on_line_received(self, line):
        logger.debug('Request from [%s]:%s: %s', self.host, self.port, line)

        response = self.dispatcher.handle_request(line)
        if not response:
            return

        logger.debug(
            'Response to [%s]:%s: %s', self.host, self.port,
            formatting.indent(self.terminator.join(response)))

        self.send_lines(response)

    def on_idle(self, subsystem):
        self.dispatcher.handle_idle(subsystem)

    def decode(self, line):
        try:
            return super(MpdSession, self).decode(line)
        except ValueError:
            logger.warning(
                'Stopping actor due to unescaping error, data '
                'supplied by client was not valid.')
            self.stop()

    def close(self):
        self.stop()

########NEW FILE########
__FILENAME__ = tokenize
from __future__ import unicode_literals

import re

from mopidy.mpd import exceptions


WORD_RE = re.compile(r"""
    ^
    (\s*)             # Leading whitespace not allowed, capture it to report.
    ([a-z][a-z0-9_]*) # A command name
    (?:\s+|$)         # trailing whitespace or EOS
    (.*)              # Possibly a remainder to be parsed
    """, re.VERBOSE)

# Quotes matching is an unrolled version of "(?:[^"\\]|\\.)*"
PARAM_RE = re.compile(r"""
    ^                               # Leading whitespace is not allowed
    (?:
        ([^%(unprintable)s"']+)     # ord(char) < 0x20, not ", not '
        |                           # or
        "([^"\\]*(?:\\.[^"\\]*)*)"  # anything surrounded by quotes
    )
    (?:\s+|$)                       # trailing whitespace or EOS
    (.*)                            # Possibly a remainder to be parsed
    """ % {'unprintable': ''.join(map(chr, range(0x21)))}, re.VERBOSE)

BAD_QUOTED_PARAM_RE = re.compile(r"""
    ^
    "[^"\\]*(?:\\.[^"\\]*)*  # start of a quoted value
    (?:                      # followed by:
        ("[^\s])             # non-escaped quote, followed by non-whitespace
        |                    # or
        ([^"])               # anything that is not a quote
    )
    """, re.VERBOSE)

UNESCAPE_RE = re.compile(r'\\(.)')  # Backslash escapes any following char.


def split(line):
    """Splits a line into tokens using same rules as MPD.

    - Lines may not start with whitespace
    - Tokens are split by arbitrary amount of spaces or tabs
    - First token must match `[a-z][a-z0-9_]*`
    - Remaining tokens can be unquoted or quoted tokens.
    - Unquoted tokens consist of all printable characters except double quotes,
      single quotes, spaces and tabs.
    - Quoted tokens are surrounded by a matching pair of double quotes.
    - The closing quote must be followed by space, tab or end of line.
    - Any value is allowed inside a quoted token. Including double quotes,
      assuming it is correctly escaped.
    - Backslash inside a quoted token is used to escape the following
      character.

    For examples see the tests for this function.
    """
    if not line.strip():
        raise exceptions.MpdNoCommand('No command given')
    match = WORD_RE.match(line)
    if not match:
        raise exceptions.MpdUnknownError('Invalid word character')
    whitespace, command, remainder = match.groups()
    if whitespace:
        raise exceptions.MpdUnknownError('Letter expected')

    result = [command]
    while remainder:
        match = PARAM_RE.match(remainder)
        if not match:
            msg = _determine_error_message(remainder)
            raise exceptions.MpdArgError(msg, command=command)
        unquoted, quoted, remainder = match.groups()
        result.append(unquoted or UNESCAPE_RE.sub(r'\g<1>', quoted))
    return result


def _determine_error_message(remainder):
    """Helper to emulate MPD errors."""
    # Following checks are simply to match MPD error messages:
    match = BAD_QUOTED_PARAM_RE.match(remainder)
    if match:
        if match.group(1):
            return 'Space expected after closing \'"\''
        else:
            return 'Missing closing \'"\''
    return 'Invalid unquoted character'

########NEW FILE########
__FILENAME__ = translator
from __future__ import unicode_literals

import re

from mopidy.models import TlTrack

# TODO: special handling of local:// uri scheme
normalize_path_re = re.compile(r'[^/]+')


def normalize_path(path, relative=False):
    parts = normalize_path_re.findall(path or '')
    if not relative:
        parts.insert(0, '')
    return '/'.join(parts)


def track_to_mpd_format(track, position=None):
    """
    Format track for output to MPD client.

    :param track: the track
    :type track: :class:`mopidy.models.Track` or :class:`mopidy.models.TlTrack`
    :param position: track's position in playlist
    :type position: integer
    :param key: if we should set key
    :type key: boolean
    :param mtime: if we should set mtime
    :type mtime: boolean
    :rtype: list of two-tuples
    """
    if isinstance(track, TlTrack):
        (tlid, track) = track
    else:
        (tlid, track) = (None, track)
    result = [
        ('file', track.uri or ''),
        ('Time', track.length and (track.length // 1000) or 0),
        ('Artist', artists_to_mpd_format(track.artists)),
        ('Title', track.name or ''),
        ('Album', track.album and track.album.name or ''),
    ]

    if track.date:
        result.append(('Date', track.date))

    if track.album is not None and track.album.num_tracks != 0:
        result.append(('Track', '%d/%d' % (
            track.track_no, track.album.num_tracks)))
    else:
        result.append(('Track', track.track_no))
    if position is not None and tlid is not None:
        result.append(('Pos', position))
        result.append(('Id', tlid))
    if track.album is not None and track.album.musicbrainz_id is not None:
        result.append(('MUSICBRAINZ_ALBUMID', track.album.musicbrainz_id))
    # FIXME don't use first and best artist?
    # FIXME don't duplicate following code?
    if track.album is not None and track.album.artists:
        artists = artists_to_mpd_format(track.album.artists)
        result.append(('AlbumArtist', artists))
        artists = filter(
            lambda a: a.musicbrainz_id is not None, track.album.artists)
        if artists:
            result.append(
                ('MUSICBRAINZ_ALBUMARTISTID', artists[0].musicbrainz_id))
    if track.artists:
        artists = filter(lambda a: a.musicbrainz_id is not None, track.artists)
        if artists:
            result.append(('MUSICBRAINZ_ARTISTID', artists[0].musicbrainz_id))

    if track.composers:
        result.append(('Composer', artists_to_mpd_format(track.composers)))

    if track.performers:
        result.append(('Performer', artists_to_mpd_format(track.performers)))

    if track.genre:
        result.append(('Genre', track.genre))

    if track.disc_no:
        result.append(('Disc', track.disc_no))

    if track.comment:
        result.append(('Comment', track.comment))

    if track.musicbrainz_id is not None:
        result.append(('MUSICBRAINZ_TRACKID', track.musicbrainz_id))
    return result


def artists_to_mpd_format(artists):
    """
    Format track artists for output to MPD client.

    :param artists: the artists
    :type track: array of :class:`mopidy.models.Artist`
    :rtype: string
    """
    artists = list(artists)
    artists.sort(key=lambda a: a.name)
    return ', '.join([a.name for a in artists if a.name])


def tracks_to_mpd_format(tracks, start=0, end=None):
    """
    Format list of tracks for output to MPD client.

    Optionally limit output to the slice ``[start:end]`` of the list.

    :param tracks: the tracks
    :type tracks: list of :class:`mopidy.models.Track` or
        :class:`mopidy.models.TlTrack`
    :param start: position of first track to include in output
    :type start: int (positive or negative)
    :param end: position after last track to include in output
    :type end: int (positive or negative) or :class:`None` for end of list
    :rtype: list of lists of two-tuples
    """
    if end is None:
        end = len(tracks)
    tracks = tracks[start:end]
    positions = range(start, end)
    assert len(tracks) == len(positions)
    result = []
    for track, position in zip(tracks, positions):
        result.append(track_to_mpd_format(track, position))
    return result


def playlist_to_mpd_format(playlist, *args, **kwargs):
    """
    Format playlist for output to MPD client.

    Arguments as for :func:`tracks_to_mpd_format`, except the first one.
    """
    return tracks_to_mpd_format(playlist.tracks, *args, **kwargs)

########NEW FILE########
__FILENAME__ = actor
from __future__ import unicode_literals

import logging
import urlparse

import pykka

from mopidy import audio as audio_lib, backend, exceptions
from mopidy.audio import scan
from mopidy.models import Track

logger = logging.getLogger(__name__)


class StreamBackend(pykka.ThreadingActor, backend.Backend):
    def __init__(self, config, audio):
        super(StreamBackend, self).__init__()

        self.library = StreamLibraryProvider(
            backend=self, timeout=config['stream']['timeout'])
        self.playback = backend.PlaybackProvider(audio=audio, backend=self)
        self.playlists = None

        self.uri_schemes = audio_lib.supported_uri_schemes(
            config['stream']['protocols'])


class StreamLibraryProvider(backend.LibraryProvider):
    def __init__(self, backend, timeout):
        super(StreamLibraryProvider, self).__init__(backend)
        self._scanner = scan.Scanner(min_duration=None, timeout=timeout)

    def lookup(self, uri):
        if urlparse.urlsplit(uri).scheme not in self.backend.uri_schemes:
            return []

        try:
            data = self._scanner.scan(uri)
            track = scan.audio_data_to_track(data)
        except exceptions.ScannerError as e:
            logger.warning('Problem looking up %s: %s', uri, e)
            track = Track(uri=uri, name=uri)

        return [track]

########NEW FILE########
__FILENAME__ = deps
from __future__ import unicode_literals

import functools
import os
import platform

import pygst
pygst.require('0.10')
import gst  # noqa

import pkg_resources

from mopidy.utils import formatting


def format_dependency_list(adapters=None):
    if adapters is None:
        dist_names = set([
            ep.dist.project_name for ep in
            pkg_resources.iter_entry_points('mopidy.ext')
            if ep.dist.project_name != 'Mopidy'])
        dist_infos = [
            functools.partial(pkg_info, dist_name)
            for dist_name in dist_names]

        adapters = [
            platform_info,
            python_info,
            functools.partial(pkg_info, 'Mopidy', True)
        ] + dist_infos + [
            gstreamer_info,
        ]

    return '\n'.join([_format_dependency(a()) for a in adapters])


def _format_dependency(dep_info):
    lines = []

    if 'version' not in dep_info:
        lines.append('%s: not found' % dep_info['name'])
    else:
        if 'path' in dep_info:
            source = ' from %s' % dep_info['path']
        else:
            source = ''
        lines.append('%s: %s%s' % (
            dep_info['name'],
            dep_info['version'],
            source,
        ))

    if 'other' in dep_info:
        lines.append('  Detailed information: %s' % (
            formatting.indent(dep_info['other'], places=4)),)

    if dep_info.get('dependencies', []):
        for sub_dep_info in dep_info['dependencies']:
            sub_dep_lines = _format_dependency(sub_dep_info)
            lines.append(
                formatting.indent(sub_dep_lines, places=2, singles=True))

    return '\n'.join(lines)


def platform_info():
    return {
        'name': 'Platform',
        'version': platform.platform(),
    }


def python_info():
    return {
        'name': 'Python',
        'version': '%s %s' % (
            platform.python_implementation(), platform.python_version()),
        'path': os.path.dirname(platform.__file__),
    }


def pkg_info(project_name=None, include_extras=False):
    if project_name is None:
        project_name = 'Mopidy'
    try:
        distribution = pkg_resources.get_distribution(project_name)
        extras = include_extras and distribution.extras or []
        dependencies = [
            pkg_info(d) for d in distribution.requires(extras)]
        return {
            'name': project_name,
            'version': distribution.version,
            'path': distribution.location,
            'dependencies': dependencies,
        }
    except pkg_resources.ResolutionError:
        return {
            'name': project_name,
        }


def gstreamer_info():
    other = []
    other.append('Python wrapper: gst-python %s' % (
        '.'.join(map(str, gst.get_pygst_version()))))

    found_elements = []
    missing_elements = []
    for name, status in _gstreamer_check_elements():
        if status:
            found_elements.append(name)
        else:
            missing_elements.append(name)

    other.append('Relevant elements:')
    other.append('  Found:')
    for element in found_elements:
        other.append('    %s' % element)
    if not found_elements:
        other.append('    none')
    other.append('  Not found:')
    for element in missing_elements:
        other.append('    %s' % element)
    if not missing_elements:
        other.append('    none')

    return {
        'name': 'GStreamer',
        'version': '.'.join(map(str, gst.get_gst_version())),
        'path': os.path.dirname(gst.__file__),
        'other': '\n'.join(other),
    }


def _gstreamer_check_elements():
    elements_to_check = [
        # Core playback
        'uridecodebin',

        # External HTTP streams
        'souphttpsrc',

        # Spotify
        'appsrc',

        # Mixers and sinks
        'alsamixer',
        'alsasink',
        'ossmixer',
        'osssink',
        'oss4mixer',
        'oss4sink',
        'pulsemixer',
        'pulsesink',

        # MP3 encoding and decoding
        'mp3parse',
        'mad',
        'id3demux',
        'id3v2mux',
        'lame',

        # Ogg Vorbis encoding and decoding
        'vorbisdec',
        'vorbisenc',
        'vorbisparse',
        'oggdemux',
        'oggmux',
        'oggparse',

        # Flac decoding
        'flacdec',
        'flacparse',

        # Shoutcast output
        'shout2send',
    ]
    known_elements = [
        factory.get_name() for factory in
        gst.registry_get_default().get_feature_list(gst.TYPE_ELEMENT_FACTORY)]
    return [
        (element, element in known_elements) for element in elements_to_check]

########NEW FILE########
__FILENAME__ = encoding
from __future__ import unicode_literals

import locale


def locale_decode(bytestr):
    try:
        return unicode(bytestr)
    except UnicodeError:
        return str(bytestr).decode(locale.getpreferredencoding())

########NEW FILE########
__FILENAME__ = formatting
from __future__ import unicode_literals

import re
import unicodedata


def indent(string, places=4, linebreak='\n', singles=False):
    lines = string.split(linebreak)
    if not singles and len(lines) == 1:
        return string
    for i, line in enumerate(lines):
        lines[i] = ' ' * places + line
    result = linebreak.join(lines)
    if not singles:
        result = linebreak + result
    return result


def slugify(value):
    """
    Converts to lowercase, removes non-word characters (alphanumerics and
    underscores) and converts spaces to hyphens. Also strips leading and
    trailing whitespace.

    This function is based on Django's slugify implementation.
    """
    value = unicodedata.normalize('NFKD', value)
    value = value.encode('ascii', 'ignore').decode('ascii')
    value = re.sub(r'[^\w\s-]', '', value).strip().lower()
    return re.sub(r'[-\s]+', '-', value)

########NEW FILE########
__FILENAME__ = jsonrpc
from __future__ import unicode_literals

import inspect
import json
import traceback

import pykka


class JsonRpcWrapper(object):
    """
    Wrap objects and make them accessible through JSON-RPC 2.0 messaging.

    This class takes responsibility of communicating with the objects and
    processing of JSON-RPC 2.0 messages. The transport of the messages over
    HTTP, WebSocket, TCP, or whatever is of no concern to this class.

    The wrapper supports exporting the methods of one or more objects. Either
    way, the objects must be exported with method name prefixes, called
    "mounts".

    To expose objects, add them all to the objects mapping. The key in the
    mapping is used as the object's mounting point in the exposed API::

       jrw = JsonRpcWrapper(objects={
           'foo': foo,
           'hello': lambda: 'Hello, world!',
       })

    This will export the Python callables on the left as the JSON-RPC 2.0
    method names on the right::

        foo.bar() -> foo.bar
        foo.baz() -> foo.baz
        lambda    -> hello

    Only the public methods of the mounted objects, or functions/methods
    included directly in the mapping, will be exposed.

    If a method returns a :class:`pykka.Future`, the future will be completed
    and its value unwrapped before the JSON-RPC wrapper returns the response.

    For further details on the JSON-RPC 2.0 spec, see
    http://www.jsonrpc.org/specification

    :param objects: mapping between mounting points and exposed functions or
        class instances
    :type objects: dict
    :param decoders: object builders to be used by :func`json.loads`
    :type decoders: list of functions taking a dict and returning a dict
    :param encoders: object serializers to be used by :func:`json.dumps`
    :type encoders: list of :class:`json.JSONEncoder` subclasses with the
        method :meth:`default` implemented
    """

    def __init__(self, objects, decoders=None, encoders=None):
        if '' in objects.keys():
            raise AttributeError(
                'The empty string is not allowed as an object mount')
        self.objects = objects
        self.decoder = get_combined_json_decoder(decoders or [])
        self.encoder = get_combined_json_encoder(encoders or [])

    def handle_json(self, request):
        """
        Handles an incoming request encoded as a JSON string.

        Returns a response as a JSON string for commands, and :class:`None` for
        notifications.

        :param request: the serialized JSON-RPC request
        :type request: string
        :rtype: string or :class:`None`
        """
        try:
            request = json.loads(request, object_hook=self.decoder)
        except ValueError:
            response = JsonRpcParseError().get_response()
        else:
            response = self.handle_data(request)
        if response is None:
            return None
        return json.dumps(response, cls=self.encoder)

    def handle_data(self, request):
        """
        Handles an incoming request in the form of a Python data structure.

        Returns a Python data structure for commands, or a :class:`None` for
        notifications.

        :param request: the unserialized JSON-RPC request
        :type request: dict
        :rtype: dict, list, or :class:`None`
        """
        if isinstance(request, list):
            return self._handle_batch(request)
        else:
            return self._handle_single_request(request)

    def _handle_batch(self, requests):
        if not requests:
            return JsonRpcInvalidRequestError(
                data='Batch list cannot be empty').get_response()

        responses = []
        for request in requests:
            response = self._handle_single_request(request)
            if response:
                responses.append(response)

        return responses or None

    def _handle_single_request(self, request):
        try:
            self._validate_request(request)
            args, kwargs = self._get_params(request)
        except JsonRpcInvalidRequestError as error:
            return error.get_response()

        try:
            method = self._get_method(request['method'])

            try:
                result = method(*args, **kwargs)

                if self._is_notification(request):
                    return None

                result = self._unwrap_result(result)

                return {
                    'jsonrpc': '2.0',
                    'id': request['id'],
                    'result': result,
                }
            except TypeError as error:
                raise JsonRpcInvalidParamsError(data={
                    'type': error.__class__.__name__,
                    'message': unicode(error),
                    'traceback': traceback.format_exc(),
                })
            except Exception as error:
                raise JsonRpcApplicationError(data={
                    'type': error.__class__.__name__,
                    'message': unicode(error),
                    'traceback': traceback.format_exc(),
                })
        except JsonRpcError as error:
            if self._is_notification(request):
                return None
            return error.get_response(request['id'])

    def _validate_request(self, request):
        if not isinstance(request, dict):
            raise JsonRpcInvalidRequestError(
                data='Request must be an object')
        if 'jsonrpc' not in request:
            raise JsonRpcInvalidRequestError(
                data='"jsonrpc" member must be included')
        if request['jsonrpc'] != '2.0':
            raise JsonRpcInvalidRequestError(
                data='"jsonrpc" value must be "2.0"')
        if 'method' not in request:
            raise JsonRpcInvalidRequestError(
                data='"method" member must be included')
        if not isinstance(request['method'], unicode):
            raise JsonRpcInvalidRequestError(
                data='"method" must be a string')

    def _get_params(self, request):
        if 'params' not in request:
            return [], {}
        params = request['params']
        if isinstance(params, list):
            return params, {}
        elif isinstance(params, dict):
            return [], params
        else:
            raise JsonRpcInvalidRequestError(
                data='"params", if given, must be an array or an object')

    def _get_method(self, method_path):
        if callable(self.objects.get(method_path, None)):
            # The mounted object is the callable
            return self.objects[method_path]

        # The mounted object contains the callable

        if '.' not in method_path:
            raise JsonRpcMethodNotFoundError(
                data='Could not find object mount in method name "%s"' % (
                    method_path))

        mount, method_name = method_path.rsplit('.', 1)

        if method_name.startswith('_'):
            raise JsonRpcMethodNotFoundError(
                data='Private methods are not exported')

        try:
            obj = self.objects[mount]
        except KeyError:
            raise JsonRpcMethodNotFoundError(
                data='No object found at "%s"' % mount)

        try:
            return getattr(obj, method_name)
        except AttributeError:
            raise JsonRpcMethodNotFoundError(
                data='Object mounted at "%s" has no member "%s"' % (
                    mount, method_name))

    def _is_notification(self, request):
        return 'id' not in request

    def _unwrap_result(self, result):
        if isinstance(result, pykka.Future):
            result = result.get()
        return result


class JsonRpcError(Exception):
    code = -32000
    message = 'Unspecified server error'

    def __init__(self, data=None):
        self.data = data

    def get_response(self, request_id=None):
        response = {
            'jsonrpc': '2.0',
            'id': request_id,
            'error': {
                'code': self.code,
                'message': self.message,
            },
        }
        if self.data:
            response['error']['data'] = self.data
        return response


class JsonRpcParseError(JsonRpcError):
    code = -32700
    message = 'Parse error'


class JsonRpcInvalidRequestError(JsonRpcError):
    code = -32600
    message = 'Invalid Request'


class JsonRpcMethodNotFoundError(JsonRpcError):
    code = -32601
    message = 'Method not found'


class JsonRpcInvalidParamsError(JsonRpcError):
    code = -32602
    message = 'Invalid params'


class JsonRpcApplicationError(JsonRpcError):
    code = 0
    message = 'Application error'


def get_combined_json_decoder(decoders):
    def decode(dct):
        for decoder in decoders:
            dct = decoder(dct)
        return dct
    return decode


def get_combined_json_encoder(encoders):
    class JsonRpcEncoder(json.JSONEncoder):
        def default(self, obj):
            for encoder in encoders:
                try:
                    return encoder().default(obj)
                except TypeError:
                    pass  # Try next encoder
            return json.JSONEncoder.default(self, obj)
    return JsonRpcEncoder


class JsonRpcInspector(object):
    """
    Inspects a group of classes and functions to create a description of what
    methods they can expose over JSON-RPC 2.0.

    To inspect one or more classes, add them all to the objects mapping. The
    key in the mapping is used as the classes' mounting point in the exposed
    API::

        jri = JsonRpcInspector(objects={
            'foo': Foo,
            'hello': lambda: 'Hello, world!',
        })

    Since the inspector is based on inspecting classes and not instances, it
    will not include methods added dynamically. The wrapper works with
    instances, and it will thus export dynamically added methods as well.

    :param objects: mapping between mounts and exposed functions or classes
    :type objects: dict
    """

    def __init__(self, objects):
        if '' in objects.keys():
            raise AttributeError(
                'The empty string is not allowed as an object mount')
        self.objects = objects

    def describe(self):
        """
        Inspects the object and returns a data structure which describes the
        available properties and methods.
        """
        methods = {}
        for mount, obj in self.objects.iteritems():
            if inspect.isroutine(obj):
                methods[mount] = self._describe_method(obj)
            else:
                obj_methods = self._get_methods(obj)
                for name, description in obj_methods.iteritems():
                    if mount:
                        name = '%s.%s' % (mount, name)
                    methods[name] = description
        return methods

    def _get_methods(self, obj):
        methods = {}
        for name, value in inspect.getmembers(obj):
            if name.startswith('_'):
                continue
            if not inspect.isroutine(value):
                continue
            method = self._describe_method(value)
            if method:
                methods[name] = method
        return methods

    def _describe_method(self, method):
        return {
            'description': inspect.getdoc(method),
            'params': self._describe_params(method),
        }

    def _describe_params(self, method):
        argspec = inspect.getargspec(method)

        defaults = argspec.defaults and list(argspec.defaults) or []
        num_args_without_default = len(argspec.args) - len(defaults)
        no_defaults = [None] * num_args_without_default
        defaults = no_defaults + defaults

        params = []

        for arg, default in zip(argspec.args, defaults):
            if arg == 'self':
                continue
            params.append({'name': arg})

        if argspec.defaults:
            for i, default in enumerate(reversed(argspec.defaults)):
                params[len(params) - i - 1]['default'] = default

        if argspec.varargs:
            params.append({
                'name': argspec.varargs,
                'varargs': True,
            })

        if argspec.keywords:
            params.append({
                'name': argspec.keywords,
                'kwargs': True,
            })

        return params

########NEW FILE########
__FILENAME__ = log
from __future__ import unicode_literals

import logging
import logging.config
import logging.handlers


class DelayedHandler(logging.Handler):
    def __init__(self):
        logging.Handler.__init__(self)
        self._released = False
        self._buffer = []

    def handle(self, record):
        if not self._released:
            self._buffer.append(record)

    def release(self):
        self._released = True
        root = logging.getLogger('')
        while self._buffer:
            root.handle(self._buffer.pop(0))


_delayed_handler = DelayedHandler()


def bootstrap_delayed_logging():
    root = logging.getLogger('')
    root.setLevel(logging.NOTSET)
    root.addHandler(_delayed_handler)


def setup_logging(config, verbosity_level, save_debug_log):
    logging.captureWarnings(True)

    if config['logging']['config_file']:
        # Logging config from file must be read before other handlers are
        # added. If not, the other handlers will have no effect.
        logging.config.fileConfig(config['logging']['config_file'])

    setup_console_logging(config, verbosity_level)
    if save_debug_log:
        setup_debug_logging_to_file(config)

    _delayed_handler.release()


LOG_LEVELS = {
    -1: dict(root=logging.ERROR, mopidy=logging.WARNING),
    0: dict(root=logging.ERROR, mopidy=logging.INFO),
    1: dict(root=logging.WARNING, mopidy=logging.DEBUG),
    2: dict(root=logging.INFO, mopidy=logging.DEBUG),
    3: dict(root=logging.DEBUG, mopidy=logging.DEBUG),
}


class VerbosityFilter(logging.Filter):
    def __init__(self, verbosity_level, loglevels):
        self.verbosity_level = verbosity_level
        self.loglevels = loglevels

    def filter(self, record):
        for name, required_log_level in self.loglevels.items():
            if record.name == name or record.name.startswith(name + '.'):
                return record.levelno >= required_log_level

        if record.name.startswith('mopidy'):
            required_log_level = LOG_LEVELS[self.verbosity_level]['mopidy']
        else:
            required_log_level = LOG_LEVELS[self.verbosity_level]['root']
        return record.levelno >= required_log_level


def setup_console_logging(config, verbosity_level):
    if verbosity_level < min(LOG_LEVELS.keys()):
        verbosity_level = min(LOG_LEVELS.keys())
    if verbosity_level > max(LOG_LEVELS.keys()):
        verbosity_level = max(LOG_LEVELS.keys())

    loglevels = config.get('loglevels', {})
    has_debug_loglevels = any([
        level < logging.INFO for level in loglevels.values()])

    verbosity_filter = VerbosityFilter(verbosity_level, loglevels)

    if verbosity_level < 1 and not has_debug_loglevels:
        log_format = config['logging']['console_format']
    else:
        log_format = config['logging']['debug_format']
    formatter = logging.Formatter(log_format)

    handler = logging.StreamHandler()
    handler.addFilter(verbosity_filter)
    handler.setFormatter(formatter)

    logging.getLogger('').addHandler(handler)


def setup_debug_logging_to_file(config):
    formatter = logging.Formatter(config['logging']['debug_format'])
    handler = logging.handlers.RotatingFileHandler(
        config['logging']['debug_file'], maxBytes=10485760, backupCount=3)
    handler.setFormatter(formatter)

    logging.getLogger('').addHandler(handler)

########NEW FILE########
__FILENAME__ = network
from __future__ import unicode_literals

import errno
import logging
import re
import socket
import sys
import threading

import gobject

import pykka

from mopidy.utils import encoding


logger = logging.getLogger(__name__)


class ShouldRetrySocketCall(Exception):
    """Indicate that attempted socket call should be retried"""


def try_ipv6_socket():
    """Determine if system really supports IPv6"""
    if not socket.has_ipv6:
        return False
    try:
        socket.socket(socket.AF_INET6).close()
        return True
    except IOError as error:
        logger.debug(
            'Platform supports IPv6, but socket creation failed, '
            'disabling: %s',
            encoding.locale_decode(error))
    return False


#: Boolean value that indicates if creating an IPv6 socket will succeed.
has_ipv6 = try_ipv6_socket()


def create_socket():
    """Create a TCP socket with or without IPv6 depending on system support"""
    if has_ipv6:
        sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        # Explicitly configure socket to work for both IPv4 and IPv6
        if hasattr(socket, 'IPPROTO_IPV6'):
            sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
        elif sys.platform == 'win32':  # also match 64bit windows.
            # Python 2.7 on windows does not have the IPPROTO_IPV6 constant
            # Use values extracted from Windows Vista/7/8's header
            sock.setsockopt(41, 27, 0)
    else:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    return sock


def format_hostname(hostname):
    """Format hostname for display."""
    if (has_ipv6 and re.match(r'\d+.\d+.\d+.\d+', hostname) is not None):
        hostname = '::ffff:%s' % hostname
    return hostname


class Server(object):
    """Setup listener and register it with gobject's event loop."""

    def __init__(self, host, port, protocol, protocol_kwargs=None,
                 max_connections=5, timeout=30):
        self.protocol = protocol
        self.protocol_kwargs = protocol_kwargs or {}
        self.max_connections = max_connections
        self.timeout = timeout
        self.server_socket = self.create_server_socket(host, port)

        self.register_server_socket(self.server_socket.fileno())

    def create_server_socket(self, host, port):
        sock = create_socket()
        sock.setblocking(False)
        sock.bind((host, port))
        sock.listen(1)
        return sock

    def register_server_socket(self, fileno):
        gobject.io_add_watch(fileno, gobject.IO_IN, self.handle_connection)

    def handle_connection(self, fd, flags):
        try:
            sock, addr = self.accept_connection()
        except ShouldRetrySocketCall:
            return True

        if self.maximum_connections_exceeded():
            self.reject_connection(sock, addr)
        else:
            self.init_connection(sock, addr)
        return True

    def accept_connection(self):
        try:
            return self.server_socket.accept()
        except socket.error as e:
            if e.errno in (errno.EAGAIN, errno.EINTR):
                raise ShouldRetrySocketCall
            raise

    def maximum_connections_exceeded(self):
        return (self.max_connections is not None and
                self.number_of_connections() >= self.max_connections)

    def number_of_connections(self):
        return len(pykka.ActorRegistry.get_by_class(self.protocol))

    def reject_connection(self, sock, addr):
        # FIXME provide more context in logging?
        logger.warning('Rejected connection from [%s]:%s', addr[0], addr[1])
        try:
            sock.close()
        except socket.error:
            pass

    def init_connection(self, sock, addr):
        Connection(
            self.protocol, self.protocol_kwargs, sock, addr, self.timeout)


class Connection(object):
    # NOTE: the callback code is _not_ run in the actor's thread, but in the
    # same one as the event loop. If code in the callbacks blocks, the rest of
    # gobject code will likely be blocked as well...
    #
    # Also note that source_remove() return values are ignored on purpose, a
    # false return value would only tell us that what we thought was registered
    # is already gone, there is really nothing more we can do.

    def __init__(self, protocol, protocol_kwargs, sock, addr, timeout):
        sock.setblocking(False)

        self.host, self.port = addr[:2]  # IPv6 has larger addr

        self.sock = sock
        self.protocol = protocol
        self.protocol_kwargs = protocol_kwargs
        self.timeout = timeout

        self.send_lock = threading.Lock()
        self.send_buffer = b''

        self.stopping = False

        self.recv_id = None
        self.send_id = None
        self.timeout_id = None

        self.actor_ref = self.protocol.start(self, **self.protocol_kwargs)

        self.enable_recv()
        self.enable_timeout()

    def stop(self, reason, level=logging.DEBUG):
        if self.stopping:
            logger.log(level, 'Already stopping: %s' % reason)
            return
        else:
            self.stopping = True

        logger.log(level, reason)

        try:
            self.actor_ref.stop(block=False)
        except pykka.ActorDeadError:
            pass

        self.disable_timeout()
        self.disable_recv()
        self.disable_send()

        try:
            self.sock.close()
        except socket.error:
            pass

    def queue_send(self, data):
        """Try to send data to client exactly as is and queue rest."""
        self.send_lock.acquire(True)
        self.send_buffer = self.send(self.send_buffer + data)
        self.send_lock.release()
        if self.send_buffer:
            self.enable_send()

    def send(self, data):
        """Send data to client, return any unsent data."""
        try:
            sent = self.sock.send(data)
            return data[sent:]
        except socket.error as e:
            if e.errno in (errno.EWOULDBLOCK, errno.EINTR):
                return data
            self.stop('Unexpected client error: %s' % e)
            return b''

    def enable_timeout(self):
        """Reactivate timeout mechanism."""
        if self.timeout <= 0:
            return

        self.disable_timeout()
        self.timeout_id = gobject.timeout_add_seconds(
            self.timeout, self.timeout_callback)

    def disable_timeout(self):
        """Deactivate timeout mechanism."""
        if self.timeout_id is None:
            return
        gobject.source_remove(self.timeout_id)
        self.timeout_id = None

    def enable_recv(self):
        if self.recv_id is not None:
            return

        try:
            self.recv_id = gobject.io_add_watch(
                self.sock.fileno(),
                gobject.IO_IN | gobject.IO_ERR | gobject.IO_HUP,
                self.recv_callback)
        except socket.error as e:
            self.stop('Problem with connection: %s' % e)

    def disable_recv(self):
        if self.recv_id is None:
            return
        gobject.source_remove(self.recv_id)
        self.recv_id = None

    def enable_send(self):
        if self.send_id is not None:
            return

        try:
            self.send_id = gobject.io_add_watch(
                self.sock.fileno(),
                gobject.IO_OUT | gobject.IO_ERR | gobject.IO_HUP,
                self.send_callback)
        except socket.error as e:
            self.stop('Problem with connection: %s' % e)

    def disable_send(self):
        if self.send_id is None:
            return

        gobject.source_remove(self.send_id)
        self.send_id = None

    def recv_callback(self, fd, flags):
        if flags & (gobject.IO_ERR | gobject.IO_HUP):
            self.stop('Bad client flags: %s' % flags)
            return True

        try:
            data = self.sock.recv(4096)
        except socket.error as e:
            if e.errno not in (errno.EWOULDBLOCK, errno.EINTR):
                self.stop('Unexpected client error: %s' % e)
            return True

        if not data:
            self.actor_ref.tell({'close': True})
            self.disable_recv()
            return True

        try:
            self.actor_ref.tell({'received': data})
        except pykka.ActorDeadError:
            self.stop('Actor is dead.')

        return True

    def send_callback(self, fd, flags):
        if flags & (gobject.IO_ERR | gobject.IO_HUP):
            self.stop('Bad client flags: %s' % flags)
            return True

        # If with can't get the lock, simply try again next time socket is
        # ready for sending.
        if not self.send_lock.acquire(False):
            return True

        try:
            self.send_buffer = self.send(self.send_buffer)
            if not self.send_buffer:
                self.disable_send()
        finally:
            self.send_lock.release()

        return True

    def timeout_callback(self):
        self.stop('Client inactive for %ds; closing connection' % self.timeout)
        return False


class LineProtocol(pykka.ThreadingActor):
    """
    Base class for handling line based protocols.

    Takes care of receiving new data from server's client code, decoding and
    then splitting data along line boundaries.
    """

    #: Line terminator to use for outputed lines.
    terminator = '\n'

    #: Regex to use for spliting lines, will be set compiled version of its
    #: own value, or to ``terminator``s value if it is not set itself.
    delimiter = None

    #: What encoding to expect incomming data to be in, can be :class:`None`.
    encoding = 'utf-8'

    def __init__(self, connection):
        super(LineProtocol, self).__init__()
        self.connection = connection
        self.prevent_timeout = False
        self.recv_buffer = b''

        if self.delimiter:
            self.delimiter = re.compile(self.delimiter)
        else:
            self.delimiter = re.compile(self.terminator)

    @property
    def host(self):
        return self.connection.host

    @property
    def port(self):
        return self.connection.port

    def on_line_received(self, line):
        """
        Called whenever a new line is found.

        Should be implemented by subclasses.
        """
        raise NotImplementedError

    def on_receive(self, message):
        """Handle messages with new data from server."""
        if 'close' in message:
            self.connection.stop('Client most likely disconnected.')
            return

        if 'received' not in message:
            return

        self.connection.disable_timeout()
        self.recv_buffer += message['received']

        for line in self.parse_lines():
            line = self.decode(line)
            if line is not None:
                self.on_line_received(line)

        if not self.prevent_timeout:
            self.connection.enable_timeout()

    def on_stop(self):
        """Ensure that cleanup when actor stops."""
        self.connection.stop('Actor is shutting down.')

    def parse_lines(self):
        """Consume new data and yield any lines found."""
        while re.search(self.terminator, self.recv_buffer):
            line, self.recv_buffer = self.delimiter.split(
                self.recv_buffer, 1)
            yield line

    def encode(self, line):
        """
        Handle encoding of line.

        Can be overridden by subclasses to change encoding behaviour.
        """
        try:
            return line.encode(self.encoding)
        except UnicodeError:
            logger.warning(
                'Stopping actor due to encode problem, data '
                'supplied by client was not valid %s',
                self.encoding)
            self.stop()

    def decode(self, line):
        """
        Handle decoding of line.

        Can be overridden by subclasses to change decoding behaviour.
        """
        try:
            return line.decode(self.encoding)
        except UnicodeError:
            logger.warning(
                'Stopping actor due to decode problem, data '
                'supplied by client was not valid %s',
                self.encoding)
            self.stop()

    def join_lines(self, lines):
        if not lines:
            return ''
        return self.terminator.join(lines) + self.terminator

    def send_lines(self, lines):
        """
        Send array of lines to client via connection.

        Join lines using the terminator that is set for this class, encode it
        and send it to the client.
        """
        if not lines:
            return

        data = self.join_lines(lines)
        self.connection.queue_send(self.encode(data))

########NEW FILE########
__FILENAME__ = path
from __future__ import unicode_literals

import Queue as queue
import logging
import os
import stat
import string
import threading
import urllib
import urlparse

import glib


logger = logging.getLogger(__name__)


XDG_DIRS = {
    'XDG_CACHE_DIR': glib.get_user_cache_dir(),
    'XDG_CONFIG_DIR': glib.get_user_config_dir(),
    'XDG_DATA_DIR': glib.get_user_data_dir(),
    'XDG_MUSIC_DIR': glib.get_user_special_dir(glib.USER_DIRECTORY_MUSIC),
}

# XDG_MUSIC_DIR can be none, so filter out any bad data.
XDG_DIRS = dict((k, v) for k, v in XDG_DIRS.items() if v is not None)


def get_or_create_dir(dir_path):
    if not isinstance(dir_path, bytes):
        raise ValueError('Path is not a bytestring.')
    dir_path = expand_path(dir_path)
    if os.path.isfile(dir_path):
        raise OSError(
            'A file with the same name as the desired dir, '
            '"%s", already exists.' % dir_path)
    elif not os.path.isdir(dir_path):
        logger.info('Creating dir %s', dir_path)
        os.makedirs(dir_path, 0755)
    return dir_path


def get_or_create_file(file_path, mkdir=True, content=None):
    if not isinstance(file_path, bytes):
        raise ValueError('Path is not a bytestring.')
    file_path = expand_path(file_path)
    if mkdir:
        get_or_create_dir(os.path.dirname(file_path))
    if not os.path.isfile(file_path):
        logger.info('Creating file %s', file_path)
        with open(file_path, 'w') as fh:
            if content:
                fh.write(content)
    return file_path


def path_to_uri(path):
    """
    Convert OS specific path to file:// URI.

    Accepts either unicode strings or bytestrings. The encoding of any
    bytestring will be maintained so that :func:`uri_to_path` can return the
    same bytestring.

    Returns a file:// URI as an unicode string.
    """
    if isinstance(path, unicode):
        path = path.encode('utf-8')
    path = urllib.quote(path)
    return urlparse.urlunsplit((b'file', b'', path, b'', b''))


def uri_to_path(uri):
    """
    Convert an URI to a OS specific path.

    Returns a bytestring, since the file path can contain chars with other
    encoding than UTF-8.

    If we had returned these paths as unicode strings, you wouldn't be able to
    look up the matching dir or file on your file system because the exact path
    would be lost by ignoring its encoding.
    """
    if isinstance(uri, unicode):
        uri = uri.encode('utf-8')
    return urllib.unquote(urlparse.urlsplit(uri).path)


def split_path(path):
    parts = []
    while True:
        path, part = os.path.split(path)
        if part:
            parts.insert(0, part)
        if not path or path == b'/':
            break
    return parts


def expand_path(path):
    # TODO: document as we want people to use this.
    if not isinstance(path, bytes):
        raise ValueError('Path is not a bytestring.')
    try:
        path = string.Template(path).substitute(XDG_DIRS)
    except KeyError:
        return None
    path = os.path.expanduser(path)
    path = os.path.abspath(path)
    return path


def _find_worker(relative, hidden, done, work, results, errors):
    """Worker thread for collecting stat() results.

    :param str relative: directory to make results relative to
    :param bool hidden: whether to include files and dirs starting with '.'
    :param threading.Event done: event indicating that all work has been done
    :param queue.Queue work: queue of paths to process
    :param dict results: shared dictionary for storing all the stat() results
    :param dict errors: shared dictionary for storing any per path errors
    """
    while not done.is_set():
        try:
            entry = work.get(block=False)
        except queue.Empty:
            continue

        if relative:
            path = os.path.relpath(entry, relative)
        else:
            path = entry

        try:
            st = os.lstat(entry)
            if stat.S_ISDIR(st.st_mode):
                for e in os.listdir(entry):
                    if hidden or not e.startswith(b'.'):
                        work.put(os.path.join(entry, e))
            elif stat.S_ISREG(st.st_mode):
                results[path] = st
            else:
                errors[path] = 'Not a file or directory'
        except os.error as e:
            errors[path] = str(e)
        finally:
            work.task_done()


def _find(root, thread_count=10, hidden=True, relative=False):
    """Threaded find implementation that provides stat results for files.

    Note that we do _not_ handle loops from bad sym/hardlinks in any way.

    :param str root: root directory to search from, may not be a file
    :param int thread_count: number of workers to use, mainly useful to
        mitigate network lag when scanning on NFS etc.
    :param bool hidden: whether to include files and dirs starting with '.'
    :param bool relative: if results should be relative to root or absolute
    """
    threads = []
    results = {}
    errors = {}
    done = threading.Event()
    work = queue.Queue()
    work.put(os.path.abspath(root))

    if not relative:
        root = None

    for i in range(thread_count):
        t = threading.Thread(target=_find_worker,
                             args=(root, hidden, done, work, results, errors))
        t.daemon = True
        t.start()
        threads.append(t)

    work.join()
    done.set()
    for t in threads:
        t.join()
    return results, errors


def find_mtimes(root):
    results, errors = _find(root, hidden=False, relative=False)
    return dict((f, int(st.st_mtime)) for f, st in results.iteritems())


def check_file_path_is_inside_base_dir(file_path, base_path):
    assert not file_path.endswith(os.sep), (
        'File path %s cannot end with a path separator' % file_path)

    # Expand symlinks
    real_base_path = os.path.realpath(base_path)
    real_file_path = os.path.realpath(file_path)

    # Use dir of file for prefix comparision, so we don't accept
    # /tmp/foo.m3u as being inside /tmp/foo, simply because they have a
    # common prefix, /tmp/foo, which matches the base path, /tmp/foo.
    real_dir_path = os.path.dirname(real_file_path)

    # Check if dir of file is the base path or a subdir
    common_prefix = os.path.commonprefix([real_base_path, real_dir_path])
    assert common_prefix == real_base_path, (
        'File path %s must be in %s' % (real_file_path, real_base_path))


# FIXME replace with mock usage in tests.
class Mtime(object):
    def __init__(self):
        self.fake = None

    def __call__(self, path):
        if self.fake is not None:
            return self.fake
        return int(os.stat(path).st_mtime)

    def set_fake_time(self, time):
        self.fake = time

    def undo_fake(self):
        self.fake = None

mtime = Mtime()

########NEW FILE########
__FILENAME__ = process
from __future__ import unicode_literals

import logging
import signal
import thread
import threading

from pykka import ActorDeadError
from pykka.registry import ActorRegistry

logger = logging.getLogger(__name__)

SIGNALS = dict(
    (k, v) for v, k in signal.__dict__.iteritems()
    if v.startswith('SIG') and not v.startswith('SIG_'))


def exit_process():
    logger.debug('Interrupting main...')
    thread.interrupt_main()
    logger.debug('Interrupted main')


def exit_handler(signum, frame):
    """A :mod:`signal` handler which will exit the program on signal."""
    logger.info('Got %s signal', SIGNALS[signum])
    exit_process()


def stop_actors_by_class(klass):
    actors = ActorRegistry.get_by_class(klass)
    logger.debug('Stopping %d instance(s) of %s', len(actors), klass.__name__)
    for actor in actors:
        actor.stop()


def stop_remaining_actors():
    num_actors = len(ActorRegistry.get_all())
    while num_actors:
        logger.error(
            'There are actor threads still running, this is probably a bug')
        logger.debug(
            'Seeing %d actor and %d non-actor thread(s): %s',
            num_actors, threading.active_count() - num_actors,
            ', '.join([t.name for t in threading.enumerate()]))
        logger.debug('Stopping %d actor(s)...', num_actors)
        ActorRegistry.stop_all()
        num_actors = len(ActorRegistry.get_all())
    logger.debug('All actors stopped.')


class BaseThread(threading.Thread):
    def __init__(self):
        super(BaseThread, self).__init__()
        # No thread should block process from exiting
        self.daemon = True

    def run(self):
        logger.debug('%s: Starting thread', self.name)
        try:
            self.run_inside_try()
        except KeyboardInterrupt:
            logger.info('Interrupted by user')
        except ImportError as e:
            logger.error(e)
        except ActorDeadError as e:
            logger.warning(e)
        except Exception as e:
            logger.exception(e)
        logger.debug('%s: Exiting thread', self.name)

    def run_inside_try(self):
        raise NotImplementedError

########NEW FILE########
__FILENAME__ = versioning
from __future__ import unicode_literals

from subprocess import PIPE, Popen

from mopidy import __version__


def get_version():
    try:
        return get_git_version()
    except EnvironmentError:
        return __version__


def get_git_version():
    process = Popen(['git', 'describe'], stdout=PIPE, stderr=PIPE)
    if process.wait() != 0:
        raise EnvironmentError('Execution of "git describe" failed')
    version = process.stdout.read().strip()
    if version.startswith('v'):
        version = version[1:]
    return version

########NEW FILE########
__FILENAME__ = zeroconf
from __future__ import unicode_literals

import logging
import socket
import string

logger = logging.getLogger(__name__)

try:
    import dbus
except ImportError:
    dbus = None

_AVAHI_IF_UNSPEC = -1
_AVAHI_PROTO_UNSPEC = -1
_AVAHI_PUBLISHFLAGS_NONE = 0


def _is_loopback_address(host):
    return host.startswith('127.') or host == '::1'


def _convert_text_to_dbus_bytes(text):
    return [dbus.Byte(ord(c)) for c in text]


class Zeroconf(object):
    """Publish a network service with Zeroconf.

    Currently, this only works on Linux using Avahi via D-Bus.

    :param str name: human readable name of the service, e.g. 'MPD on neptune'
    :param int port: TCP port of the service, e.g. 6600
    :param str stype: service type, e.g. '_mpd._tcp'
    :param str domain: local network domain name, defaults to ''
    :param str host: interface to advertise the service on, defaults to all
        interfaces
    :param text: extra information depending on ``stype``, defaults to empty
        list
    :type text: list of str
    """

    def __init__(self, name, port, stype=None, domain=None,
                 host=None, text=None):
        self.group = None
        self.stype = stype or '_http._tcp'
        self.domain = domain or ''
        self.port = port
        self.text = text or []
        if host in ('::', '0.0.0.0'):
            self.host = ''
        else:
            self.host = host

        template = string.Template(name)
        self.name = template.safe_substitute(
            hostname=self.host or socket.getfqdn(), port=self.port)

    def publish(self):
        """Publish the service.

        Call when your service starts.
        """

        if _is_loopback_address(self.host):
            logger.debug(
                'Zeroconf publish on loopback interface is not supported.')
            return False

        if not dbus:
            logger.debug('Zeroconf publish failed: dbus not installed.')
            return False

        try:
            bus = dbus.SystemBus()

            if not bus.name_has_owner('org.freedesktop.Avahi'):
                logger.debug(
                    'Zeroconf publish failed: Avahi service not running.')
                return False

            server = dbus.Interface(
                bus.get_object('org.freedesktop.Avahi', '/'),
                'org.freedesktop.Avahi.Server')

            self.group = dbus.Interface(
                bus.get_object(
                    'org.freedesktop.Avahi', server.EntryGroupNew()),
                'org.freedesktop.Avahi.EntryGroup')

            text = [_convert_text_to_dbus_bytes(t) for t in self.text]
            self.group.AddService(
                _AVAHI_IF_UNSPEC, _AVAHI_PROTO_UNSPEC,
                dbus.UInt32(_AVAHI_PUBLISHFLAGS_NONE), self.name, self.stype,
                self.domain, self.host, dbus.UInt16(self.port), text)

            self.group.Commit()
            return True
        except dbus.exceptions.DBusException as e:
            logger.debug('Zeroconf publish failed: %s', e)
            return False

    def unpublish(self):
        """Unpublish the service.

        Call when your service shuts down.
        """

        if self.group:
            try:
                self.group.Reset()
            except dbus.exceptions.DBusException as e:
                logger.debug('Zeroconf unpublish failed: %s', e)
            finally:
                self.group = None

########NEW FILE########
__FILENAME__ = __main__
from __future__ import print_function, unicode_literals

import logging
import os
import signal
import sys

import gobject
gobject.threads_init()

try:
    # Make GObject's mainloop the event loop for python-dbus
    import dbus.mainloop.glib
    dbus.mainloop.glib.threads_init()
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
except ImportError:
    pass

import pykka.debug


# Extract any command line arguments. This needs to be done before GStreamer is
# imported, so that GStreamer doesn't hijack e.g. ``--help``.
mopidy_args = sys.argv[1:]
sys.argv[1:] = []


from mopidy import commands, config as config_lib, ext
from mopidy.utils import encoding, log, path, process, versioning

logger = logging.getLogger(__name__)


def main():
    log.bootstrap_delayed_logging()
    logger.info('Starting Mopidy %s', versioning.get_version())

    signal.signal(signal.SIGTERM, process.exit_handler)
    # Windows does not have signal.SIGUSR1
    if hasattr(signal, 'SIGUSR1'):
        signal.signal(signal.SIGUSR1, pykka.debug.log_thread_tracebacks)

    try:
        registry = ext.Registry()

        root_cmd = commands.RootCommand()
        config_cmd = commands.ConfigCommand()
        deps_cmd = commands.DepsCommand()

        root_cmd.set(extension=None, registry=registry)
        root_cmd.add_child('config', config_cmd)
        root_cmd.add_child('deps', deps_cmd)

        installed_extensions = ext.load_extensions()

        for extension in installed_extensions:
            ext_cmd = extension.get_command()
            if ext_cmd:
                ext_cmd.set(extension=extension)
                root_cmd.add_child(extension.ext_name, ext_cmd)

        args = root_cmd.parse(mopidy_args)

        create_file_structures_and_config(args, installed_extensions)
        check_old_locations()

        config, config_errors = config_lib.load(
            args.config_files, installed_extensions, args.config_overrides)

        verbosity_level = args.base_verbosity_level
        if args.verbosity_level:
            verbosity_level += args.verbosity_level

        log.setup_logging(config, verbosity_level, args.save_debug_log)

        extensions = {
            'validate': [], 'config': [], 'disabled': [], 'enabled': []}
        for extension in installed_extensions:
            if not ext.validate_extension(extension):
                config[extension.ext_name] = {'enabled': False}
                config_errors[extension.ext_name] = {
                    'enabled': 'extension disabled by self check.'}
                extensions['validate'].append(extension)
            elif not config[extension.ext_name]['enabled']:
                config[extension.ext_name] = {'enabled': False}
                config_errors[extension.ext_name] = {
                    'enabled': 'extension disabled by user config.'}
                extensions['disabled'].append(extension)
            elif config_errors.get(extension.ext_name):
                config[extension.ext_name]['enabled'] = False
                config_errors[extension.ext_name]['enabled'] = (
                    'extension disabled due to config errors.')
                extensions['config'].append(extension)
            else:
                extensions['enabled'].append(extension)

        log_extension_info(installed_extensions, extensions['enabled'])

        # Config and deps commands are simply special cased for now.
        if args.command == config_cmd:
            return args.command.run(
                config, config_errors, installed_extensions)
        elif args.command == deps_cmd:
            return args.command.run()

        check_config_errors(config, config_errors, extensions)

        if not extensions['enabled']:
            logger.error('No extension enabled, exiting...')
            sys.exit(1)

        # Read-only config from here on, please.
        proxied_config = config_lib.Proxy(config)

        if args.extension and args.extension not in extensions['enabled']:
            logger.error(
                'Unable to run command provided by disabled extension %s',
                args.extension.ext_name)
            return 1

        for extension in extensions['enabled']:
            extension.setup(registry)

        # Anything that wants to exit after this point must use
        # mopidy.utils.process.exit_process as actors can have been started.
        try:
            return args.command.run(args, proxied_config)
        except NotImplementedError:
            print(root_cmd.format_help())
            return 1

    except KeyboardInterrupt:
        pass
    except Exception as ex:
        logger.exception(ex)
        raise


def create_file_structures_and_config(args, extensions):
    path.get_or_create_dir(b'$XDG_DATA_DIR/mopidy')
    path.get_or_create_dir(b'$XDG_CONFIG_DIR/mopidy')

    # Initialize whatever the last config file is with defaults
    config_file = args.config_files[-1]
    if os.path.exists(path.expand_path(config_file)):
        return

    try:
        default = config_lib.format_initial(extensions)
        path.get_or_create_file(config_file, mkdir=False, content=default)
        logger.info('Initialized %s with default config', config_file)
    except IOError as error:
        logger.warning(
            'Unable to initialize %s with default config: %s',
            config_file, encoding.locale_decode(error))


def check_old_locations():
    dot_mopidy_dir = path.expand_path(b'~/.mopidy')
    if os.path.isdir(dot_mopidy_dir):
        logger.warning(
            'Old Mopidy dot dir found at %s. Please migrate your config to '
            'the ini-file based config format. See release notes for further '
            'instructions.', dot_mopidy_dir)

    old_settings_file = path.expand_path(b'$XDG_CONFIG_DIR/mopidy/settings.py')
    if os.path.isfile(old_settings_file):
        logger.warning(
            'Old Mopidy settings file found at %s. Please migrate your '
            'config to the ini-file based config format. See release notes '
            'for further instructions.', old_settings_file)


def log_extension_info(all_extensions, enabled_extensions):
    # TODO: distinguish disabled vs blocked by env?
    enabled_names = set(e.ext_name for e in enabled_extensions)
    disabled_names = set(e.ext_name for e in all_extensions) - enabled_names
    logger.info(
        'Enabled extensions: %s', ', '.join(enabled_names) or 'none')
    logger.info(
        'Disabled extensions: %s', ', '.join(disabled_names) or 'none')


def check_config_errors(config, errors, extensions):
    fatal_errors = []
    extension_names = {}
    all_extension_names = set()

    for state in extensions:
        extension_names[state] = set(e.ext_name for e in extensions[state])
        all_extension_names.update(extension_names[state])

    for section in sorted(errors):
        if not errors[section]:
            continue

        if section not in all_extension_names:
            logger.warning('Found fatal %s configuration errors:', section)
            fatal_errors.append(section)
        elif section in extension_names['config']:
            del errors[section]['enabled']
            logger.warning('Found %s configuration errors, the extension '
                           'has been automatically disabled:', section)
        else:
            continue

        for field, msg in errors[section].items():
            logger.warning('  %s/%s %s', section, field, msg)

    if extensions['config']:
        logger.warning('Please fix the extension configuration errors or '
                       'disable the extensions to silence these messages.')

    if fatal_errors:
        logger.error('Please fix fatal configuration errors, exiting...')
        sys.exit(1)


if __name__ == '__main__':
    sys.exit(main())

########NEW FILE########
__FILENAME__ = test_actor
from __future__ import unicode_literals

import unittest

import gobject
gobject.threads_init()

import pygst
pygst.require('0.10')
import gst  # noqa

import mock

import pykka

from mopidy import audio
from mopidy.utils.path import path_to_uri

from tests import path_to_data_dir


class AudioTest(unittest.TestCase):
    def setUp(self):
        config = {
            'audio': {
                'mixer': 'fakemixer track_max_volume=65536',
                'mixer_track': None,
                'mixer_volume': None,
                'output': 'fakesink',
                'visualizer': None,
            },
            'proxy': {
                'hostname': '',
            },
        }
        self.song_uri = path_to_uri(path_to_data_dir('song1.wav'))
        self.audio = audio.Audio.start(config=config).proxy()

    def tearDown(self):
        pykka.ActorRegistry.stop_all()

    def prepare_uri(self, uri):
        self.audio.prepare_change()
        self.audio.set_uri(uri)

    def test_start_playback_existing_file(self):
        self.prepare_uri(self.song_uri)
        self.assertTrue(self.audio.start_playback().get())

    def test_start_playback_non_existing_file(self):
        self.prepare_uri(self.song_uri + 'bogus')
        self.assertFalse(self.audio.start_playback().get())

    def test_pause_playback_while_playing(self):
        self.prepare_uri(self.song_uri)
        self.audio.start_playback()
        self.assertTrue(self.audio.pause_playback().get())

    def test_stop_playback_while_playing(self):
        self.prepare_uri(self.song_uri)
        self.audio.start_playback()
        self.assertTrue(self.audio.stop_playback().get())

    @unittest.SkipTest
    def test_deliver_data(self):
        pass  # TODO

    @unittest.SkipTest
    def test_end_of_data_stream(self):
        pass  # TODO

    def test_set_volume(self):
        for value in range(0, 101):
            self.assertTrue(self.audio.set_volume(value).get())
            self.assertEqual(value, self.audio.get_volume().get())

    def test_set_volume_with_mixer_max_below_100(self):
        config = {
            'audio': {
                'mixer': 'fakemixer track_max_volume=40',
                'mixer_track': None,
                'mixer_volume': None,
                'output': 'fakesink',
                'visualizer': None,
            }
        }
        self.audio = audio.Audio.start(config=config).proxy()

        for value in range(0, 101):
            self.assertTrue(self.audio.set_volume(value).get())
            self.assertEqual(value, self.audio.get_volume().get())

    def test_set_volume_with_mixer_min_equal_max(self):
        config = {
            'audio': {
                'mixer': 'fakemixer track_max_volume=0',
                'mixer_track': None,
                'mixer_volume': None,
                'output': 'fakesink',
                'visualizer': None,
            }
        }
        self.audio = audio.Audio.start(config=config).proxy()
        self.assertEqual(0, self.audio.get_volume().get())

    @unittest.SkipTest
    def test_set_mute(self):
        pass  # TODO Probably needs a fakemixer with a mixer track

    @unittest.SkipTest
    def test_set_state_encapsulation(self):
        pass  # TODO

    @unittest.SkipTest
    def test_set_position(self):
        pass  # TODO

    @unittest.SkipTest
    def test_invalid_output_raises_error(self):
        pass  # TODO


class AudioStateTest(unittest.TestCase):
    def setUp(self):
        self.audio = audio.Audio(config=None)

    def test_state_starts_as_stopped(self):
        self.assertEqual(audio.PlaybackState.STOPPED, self.audio.state)

    def test_state_does_not_change_when_in_gst_ready_state(self):
        self.audio._on_playbin_state_changed(
            gst.STATE_NULL, gst.STATE_READY, gst.STATE_VOID_PENDING)

        self.assertEqual(audio.PlaybackState.STOPPED, self.audio.state)

    def test_state_changes_from_stopped_to_playing_on_play(self):
        self.audio._on_playbin_state_changed(
            gst.STATE_NULL, gst.STATE_READY, gst.STATE_PLAYING)
        self.audio._on_playbin_state_changed(
            gst.STATE_READY, gst.STATE_PAUSED, gst.STATE_PLAYING)
        self.audio._on_playbin_state_changed(
            gst.STATE_PAUSED, gst.STATE_PLAYING, gst.STATE_VOID_PENDING)

        self.assertEqual(audio.PlaybackState.PLAYING, self.audio.state)

    def test_state_changes_from_playing_to_paused_on_pause(self):
        self.audio.state = audio.PlaybackState.PLAYING

        self.audio._on_playbin_state_changed(
            gst.STATE_PLAYING, gst.STATE_PAUSED, gst.STATE_VOID_PENDING)

        self.assertEqual(audio.PlaybackState.PAUSED, self.audio.state)

    def test_state_changes_from_playing_to_stopped_on_stop(self):
        self.audio.state = audio.PlaybackState.PLAYING

        self.audio._on_playbin_state_changed(
            gst.STATE_PLAYING, gst.STATE_PAUSED, gst.STATE_NULL)
        self.audio._on_playbin_state_changed(
            gst.STATE_PAUSED, gst.STATE_READY, gst.STATE_NULL)
        # We never get the following call, so the logic must work without it
        # self.audio._on_playbin_state_changed(
        #     gst.STATE_READY, gst.STATE_NULL, gst.STATE_VOID_PENDING)

        self.assertEqual(audio.PlaybackState.STOPPED, self.audio.state)


class AudioBufferingTest(unittest.TestCase):
    def setUp(self):
        self.audio = audio.Audio(config=None)
        self.audio._playbin = mock.Mock(spec=['set_state'])

        self.buffer_full_message = mock.Mock()
        self.buffer_full_message.type = gst.MESSAGE_BUFFERING
        self.buffer_full_message.parse_buffering = mock.Mock(return_value=100)

        self.buffer_empty_message = mock.Mock()
        self.buffer_empty_message.type = gst.MESSAGE_BUFFERING
        self.buffer_empty_message.parse_buffering = mock.Mock(return_value=0)

    def test_pause_when_buffer_empty(self):
        playbin = self.audio._playbin
        self.audio.start_playback()
        playbin.set_state.assert_called_with(gst.STATE_PLAYING)
        playbin.set_state.reset_mock()

        self.audio._on_message(None, self.buffer_empty_message)
        playbin.set_state.assert_called_with(gst.STATE_PAUSED)

    def test_stay_paused_when_buffering_finished(self):
        playbin = self.audio._playbin
        self.audio.pause_playback()
        playbin.set_state.assert_called_with(gst.STATE_PAUSED)
        playbin.set_state.reset_mock()

        self.audio._on_message(None, self.buffer_full_message)
        self.assertEqual(playbin.set_state.call_count, 0)

########NEW FILE########
__FILENAME__ = test_listener
from __future__ import unicode_literals

import unittest

import mock

from mopidy import audio


class AudioListenerTest(unittest.TestCase):
    def setUp(self):
        self.listener = audio.AudioListener()

    def test_on_event_forwards_to_specific_handler(self):
        self.listener.state_changed = mock.Mock()

        self.listener.on_event(
            'state_changed', old_state='stopped', new_state='playing')

        self.listener.state_changed.assert_called_with(
            old_state='stopped', new_state='playing')

    def test_listener_has_default_impl_for_reached_end_of_stream(self):
        self.listener.reached_end_of_stream()

    def test_listener_has_default_impl_for_state_changed(self):
        self.listener.state_changed(None, None)

########NEW FILE########
__FILENAME__ = test_playlists
# encoding: utf-8

from __future__ import unicode_literals

import io
import unittest

from mopidy.audio import playlists


BAD = b'foobarbaz'

M3U = b"""#EXTM3U
#EXTINF:123, Sample artist - Sample title
file:///tmp/foo
#EXTINF:321,Example Artist - Example title
file:///tmp/bar
#EXTINF:213,Some Artist - Other title
file:///tmp/baz
"""

PLS = b"""[Playlist]
NumberOfEntries=3
File1=file:///tmp/foo
Title1=Sample Title
Length1=123
File2=file:///tmp/bar
Title2=Example title
Length2=321
File3=file:///tmp/baz
Title3=Other title
Length3=213
Version=2
"""

ASX = b"""<asx version="3.0">
  <title>Example</title>
  <entry>
    <title>Sample Title</title>
    <ref href="file:///tmp/foo" />
  </entry>
  <entry>
    <title>Example title</title>
    <ref href="file:///tmp/bar" />
  </entry>
  <entry>
    <title>Other title</title>
    <ref href="file:///tmp/baz" />
  </entry>
</asx>
"""

XSPF = b"""<?xml version="1.0" encoding="UTF-8"?>
<playlist version="1" xmlns="http://xspf.org/ns/0/">
  <trackList>
    <track>
      <title>Sample Title</title>
      <location>file:///tmp/foo</location>
    </track>
    <track>
      <title>Example title</title>
      <location>file:///tmp/bar</location>
    </track>
    <track>
      <title>Other title</title>
      <location>file:///tmp/baz</location>
    </track>
  </trackList>
</playlist>
"""


class TypeFind(object):
    def __init__(self, data):
        self.data = data

    def peek(self, start, end):
        return self.data[start:end]


class BasePlaylistTest(object):
    valid = None
    invalid = None
    detect = None
    parse = None

    def test_detect_valid_header(self):
        self.assertTrue(self.detect(TypeFind(self.valid)))

    def test_detect_invalid_header(self):
        self.assertFalse(self.detect(TypeFind(self.invalid)))

    def test_parse_valid_playlist(self):
        uris = list(self.parse(io.BytesIO(self.valid)))
        expected = [b'file:///tmp/foo', b'file:///tmp/bar', b'file:///tmp/baz']
        self.assertEqual(uris, expected)

    def test_parse_invalid_playlist(self):
        uris = list(self.parse(io.BytesIO(self.invalid)))
        self.assertEqual(uris, [])


class M3uPlaylistTest(BasePlaylistTest, unittest.TestCase):
    valid = M3U
    invalid = BAD
    detect = staticmethod(playlists.detect_m3u_header)
    parse = staticmethod(playlists.parse_m3u)


class PlsPlaylistTest(BasePlaylistTest, unittest.TestCase):
    valid = PLS
    invalid = BAD
    detect = staticmethod(playlists.detect_pls_header)
    parse = staticmethod(playlists.parse_pls)


class AsxPlsPlaylistTest(BasePlaylistTest, unittest.TestCase):
    valid = ASX
    invalid = BAD
    detect = staticmethod(playlists.detect_asx_header)
    parse = staticmethod(playlists.parse_asx)


class XspfPlaylistTest(BasePlaylistTest, unittest.TestCase):
    valid = XSPF
    invalid = BAD
    detect = staticmethod(playlists.detect_xspf_header)
    parse = staticmethod(playlists.parse_xspf)

########NEW FILE########
__FILENAME__ = test_scan
from __future__ import unicode_literals

import os
import unittest

import gobject
gobject.threads_init()

from mopidy import exceptions
from mopidy.audio import scan
from mopidy.models import Album, Artist, Track
from mopidy.utils import path as path_lib

from tests import path_to_data_dir


class FakeGstDate(object):
    def __init__(self, year, month, day):
        self.year = year
        self.month = month
        self.day = day


# TODO: keep ids without name?
class TranslatorTest(unittest.TestCase):
    def setUp(self):
        self.data = {
            'uri': 'uri',
            'duration': 4531000000,
            'mtime': 1234,
            'tags': {
                'album': ['album'],
                'track-number': [1],
                'artist': ['artist'],
                'composer': ['composer'],
                'performer': ['performer'],
                'album-artist': ['albumartist'],
                'title': ['track'],
                'track-count': [2],
                'album-disc-number': [2],
                'album-disc-count': [3],
                'date': [FakeGstDate(2006, 1, 1,)],
                'container-format': ['ID3 tag'],
                'genre': ['genre'],
                'comment': ['comment'],
                'musicbrainz-trackid': ['trackid'],
                'musicbrainz-albumid': ['albumid'],
                'musicbrainz-artistid': ['artistid'],
                'musicbrainz-albumartistid': ['albumartistid'],
                'bitrate': [1000],
            },
        }

        artist = Artist(name='artist', musicbrainz_id='artistid')
        composer = Artist(name='composer')
        performer = Artist(name='performer')
        albumartist = Artist(name='albumartist',
                             musicbrainz_id='albumartistid')

        album = Album(name='album', num_tracks=2, num_discs=3,
                      musicbrainz_id='albumid', artists=[albumartist])

        self.track = Track(uri='uri', name='track', date='2006-01-01',
                           genre='genre', track_no=1, disc_no=2, length=4531,
                           comment='comment', musicbrainz_id='trackid',
                           last_modified=1234, album=album, bitrate=1000,
                           artists=[artist], composers=[composer],
                           performers=[performer])

    def check(self, expected):
        actual = scan.audio_data_to_track(self.data)
        self.assertEqual(expected, actual)

    def test_track(self):
        self.check(self.track)

    def test_none_track_length(self):
        self.data['duration'] = None
        self.check(self.track.copy(length=None))

    def test_none_track_last_modified(self):
        self.data['mtime'] = None
        self.check(self.track.copy(last_modified=None))

    def test_missing_track_no(self):
        del self.data['tags']['track-number']
        self.check(self.track.copy(track_no=None))

    def test_multiple_track_no(self):
        self.data['tags']['track-number'].append(9)
        self.check(self.track)

    def test_missing_track_disc_no(self):
        del self.data['tags']['album-disc-number']
        self.check(self.track.copy(disc_no=None))

    def test_multiple_track_disc_no(self):
        self.data['tags']['album-disc-number'].append(9)
        self.check(self.track)

    def test_missing_track_name(self):
        del self.data['tags']['title']
        self.check(self.track.copy(name=None))

    def test_multiple_track_name(self):
        self.data['tags']['title'] = ['name1', 'name2']
        self.check(self.track.copy(name='name1; name2'))

    def test_missing_track_musicbrainz_id(self):
        del self.data['tags']['musicbrainz-trackid']
        self.check(self.track.copy(musicbrainz_id=None))

    def test_multiple_track_musicbrainz_id(self):
        self.data['tags']['musicbrainz-trackid'].append('id')
        self.check(self.track)

    def test_missing_track_bitrate(self):
        del self.data['tags']['bitrate']
        self.check(self.track.copy(bitrate=None))

    def test_multiple_track_bitrate(self):
        self.data['tags']['bitrate'].append(1234)
        self.check(self.track)

    def test_missing_track_genre(self):
        del self.data['tags']['genre']
        self.check(self.track.copy(genre=None))

    def test_multiple_track_genre(self):
        self.data['tags']['genre'] = ['genre1', 'genre2']
        self.check(self.track.copy(genre='genre1; genre2'))

    def test_missing_track_date(self):
        del self.data['tags']['date']
        self.check(self.track.copy(date=None))

    def test_multiple_track_date(self):
        self.data['tags']['date'].append(FakeGstDate(2030, 1, 1))
        self.check(self.track)

    def test_invalid_track_date(self):
        self.data['tags']['date'] = [FakeGstDate(65535, 1, 1)]
        self.check(self.track.copy(date=None))

    def test_missing_track_comment(self):
        del self.data['tags']['comment']
        self.check(self.track.copy(comment=None))

    def test_multiple_track_comment(self):
        self.data['tags']['comment'] = ['comment1', 'comment2']
        self.check(self.track.copy(comment='comment1; comment2'))

    def test_missing_track_artist_name(self):
        del self.data['tags']['artist']
        self.check(self.track.copy(artists=[]))

    def test_multiple_track_artist_name(self):
        self.data['tags']['artist'] = ['name1', 'name2']
        artists = [Artist(name='name1'), Artist(name='name2')]
        self.check(self.track.copy(artists=artists))

    def test_missing_track_artist_musicbrainz_id(self):
        del self.data['tags']['musicbrainz-artistid']
        artist = list(self.track.artists)[0].copy(musicbrainz_id=None)
        self.check(self.track.copy(artists=[artist]))

    def test_multiple_track_artist_musicbrainz_id(self):
        self.data['tags']['musicbrainz-artistid'].append('id')
        self.check(self.track)

    def test_missing_track_composer_name(self):
        del self.data['tags']['composer']
        self.check(self.track.copy(composers=[]))

    def test_multiple_track_composer_name(self):
        self.data['tags']['composer'] = ['composer1', 'composer2']
        composers = [Artist(name='composer1'), Artist(name='composer2')]
        self.check(self.track.copy(composers=composers))

    def test_missing_track_performer_name(self):
        del self.data['tags']['performer']
        self.check(self.track.copy(performers=[]))

    def test_multiple_track_performe_name(self):
        self.data['tags']['performer'] = ['performer1', 'performer2']
        performers = [Artist(name='performer1'), Artist(name='performer2')]
        self.check(self.track.copy(performers=performers))

    def test_missing_album_name(self):
        del self.data['tags']['album']
        album = self.track.album.copy(name=None)
        self.check(self.track.copy(album=album))

    def test_multiple_album_name(self):
        self.data['tags']['album'].append('album2')
        self.check(self.track)

    def test_missing_album_musicbrainz_id(self):
        del self.data['tags']['musicbrainz-albumid']
        album = self.track.album.copy(musicbrainz_id=None)
        self.check(self.track.copy(album=album))

    def test_multiple_album_musicbrainz_id(self):
        self.data['tags']['musicbrainz-albumid'].append('id')
        self.check(self.track)

    def test_missing_album_num_tracks(self):
        del self.data['tags']['track-count']
        album = self.track.album.copy(num_tracks=None)
        self.check(self.track.copy(album=album))

    def test_multiple_album_num_tracks(self):
        self.data['tags']['track-count'].append(9)
        self.check(self.track)

    def test_missing_album_num_discs(self):
        del self.data['tags']['album-disc-count']
        album = self.track.album.copy(num_discs=None)
        self.check(self.track.copy(album=album))

    def test_multiple_album_num_discs(self):
        self.data['tags']['album-disc-count'].append(9)
        self.check(self.track)

    def test_missing_album_artist_name(self):
        del self.data['tags']['album-artist']
        album = self.track.album.copy(artists=[])
        self.check(self.track.copy(album=album))

    def test_multiple_album_artist_name(self):
        self.data['tags']['album-artist'] = ['name1', 'name2']
        artists = [Artist(name='name1'), Artist(name='name2')]
        album = self.track.album.copy(artists=artists)
        self.check(self.track.copy(album=album))

    def test_missing_album_artist_musicbrainz_id(self):
        del self.data['tags']['musicbrainz-albumartistid']
        albumartist = list(self.track.album.artists)[0]
        albumartist = albumartist.copy(musicbrainz_id=None)
        album = self.track.album.copy(artists=[albumartist])
        self.check(self.track.copy(album=album))

    def test_multiple_album_artist_musicbrainz_id(self):
        self.data['tags']['musicbrainz-albumartistid'].append('id')
        self.check(self.track)

    def test_stream_organization_track_name(self):
        del self.data['tags']['title']
        self.data['tags']['organization'] = ['organization']
        self.check(self.track.copy(name='organization'))

    def test_multiple_organization_track_name(self):
        del self.data['tags']['title']
        self.data['tags']['organization'] = ['organization1', 'organization2']
        self.check(self.track.copy(name='organization1; organization2'))

    # TODO: combine all comment types?
    def test_stream_location_track_comment(self):
        del self.data['tags']['comment']
        self.data['tags']['location'] = ['location']
        self.check(self.track.copy(comment='location'))

    def test_multiple_location_track_comment(self):
        del self.data['tags']['comment']
        self.data['tags']['location'] = ['location1', 'location2']
        self.check(self.track.copy(comment='location1; location2'))

    def test_stream_copyright_track_comment(self):
        del self.data['tags']['comment']
        self.data['tags']['copyright'] = ['copyright']
        self.check(self.track.copy(comment='copyright'))

    def test_multiple_copyright_track_comment(self):
        del self.data['tags']['comment']
        self.data['tags']['copyright'] = ['copyright1', 'copyright2']
        self.check(self.track.copy(comment='copyright1; copyright2'))


class ScannerTest(unittest.TestCase):
    def setUp(self):
        self.errors = {}
        self.data = {}

    def find(self, path):
        media_dir = path_to_data_dir(path)
        for path in path_lib.find_mtimes(media_dir):
            yield os.path.join(media_dir, path)

    def scan(self, paths):
        scanner = scan.Scanner()
        for path in paths:
            uri = path_lib.path_to_uri(path)
            key = uri[len('file://'):]
            try:
                self.data[key] = scanner.scan(uri)
            except exceptions.ScannerError as error:
                self.errors[key] = error

    def check(self, name, key, value):
        name = path_to_data_dir(name)
        self.assertEqual(self.data[name][key], value)

    def check_tag(self, name, key, value):
        name = path_to_data_dir(name)
        self.assertEqual(self.data[name]['tags'][key], value)

    def test_data_is_set(self):
        self.scan(self.find('scanner/simple'))
        self.assert_(self.data)

    def test_errors_is_not_set(self):
        self.scan(self.find('scanner/simple'))
        self.assert_(not self.errors)

    def test_uri_is_set(self):
        self.scan(self.find('scanner/simple'))
        self.check(
            'scanner/simple/song1.mp3', 'uri',
            'file://%s' % path_to_data_dir('scanner/simple/song1.mp3'))
        self.check(
            'scanner/simple/song1.ogg', 'uri',
            'file://%s' % path_to_data_dir('scanner/simple/song1.ogg'))

    def test_duration_is_set(self):
        self.scan(self.find('scanner/simple'))
        self.check('scanner/simple/song1.mp3', 'duration', 4680000000)
        self.check('scanner/simple/song1.ogg', 'duration', 4680000000)

    def test_artist_is_set(self):
        self.scan(self.find('scanner/simple'))
        self.check_tag('scanner/simple/song1.mp3', 'artist', ['name'])
        self.check_tag('scanner/simple/song1.ogg', 'artist', ['name'])

    def test_album_is_set(self):
        self.scan(self.find('scanner/simple'))
        self.check_tag('scanner/simple/song1.mp3', 'album', ['albumname'])
        self.check_tag('scanner/simple/song1.ogg', 'album', ['albumname'])

    def test_track_is_set(self):
        self.scan(self.find('scanner/simple'))
        self.check_tag('scanner/simple/song1.mp3', 'title', ['trackname'])
        self.check_tag('scanner/simple/song1.ogg', 'title', ['trackname'])

    def test_nonexistant_dir_does_not_fail(self):
        self.scan(self.find('scanner/does-not-exist'))
        self.assert_(not self.errors)

    def test_other_media_is_ignored(self):
        self.scan(self.find('scanner/image'))
        self.assert_(self.errors)

    def test_log_file_that_gst_thinks_is_mpeg_1_is_ignored(self):
        self.scan([path_to_data_dir('scanner/example.log')])
        self.assert_(self.errors)

    def test_empty_wav_file_is_ignored(self):
        self.scan([path_to_data_dir('scanner/empty.wav')])
        self.assert_(self.errors)

    @unittest.SkipTest
    def test_song_without_time_is_handeled(self):
        pass

########NEW FILE########
__FILENAME__ = test_listener
from __future__ import unicode_literals

import unittest

import mock

from mopidy import backend


class BackendListenerTest(unittest.TestCase):
    def setUp(self):
        self.listener = backend.BackendListener()

    def test_on_event_forwards_to_specific_handler(self):
        self.listener.playlists_loaded = mock.Mock()

        self.listener.on_event('playlists_loaded')

        self.listener.playlists_loaded.assert_called_with()

    def test_listener_has_default_impl_for_playlists_loaded(self):
        self.listener.playlists_loaded()

########NEW FILE########
__FILENAME__ = test_config
# encoding: utf-8

from __future__ import unicode_literals

import unittest

import mock

from mopidy import config

from tests import path_to_data_dir


class LoadConfigTest(unittest.TestCase):
    def test_load_nothing(self):
        self.assertEqual({}, config._load([], [], []))

    def test_load_single_default(self):
        default = b'[foo]\nbar = baz'
        expected = {'foo': {'bar': 'baz'}}
        result = config._load([], [default], [])
        self.assertEqual(expected, result)

    def test_unicode_default(self):
        default = '[foo]\nbar = æøå'
        expected = {'foo': {'bar': 'æøå'.encode('utf-8')}}
        result = config._load([], [default], [])
        self.assertEqual(expected, result)

    def test_load_defaults(self):
        default1 = b'[foo]\nbar = baz'
        default2 = b'[foo2]\n'
        expected = {'foo': {'bar': 'baz'}, 'foo2': {}}
        result = config._load([], [default1, default2], [])
        self.assertEqual(expected, result)

    def test_load_single_override(self):
        override = ('foo', 'bar', 'baz')
        expected = {'foo': {'bar': 'baz'}}
        result = config._load([], [], [override])
        self.assertEqual(expected, result)

    def test_load_overrides(self):
        override1 = ('foo', 'bar', 'baz')
        override2 = ('foo2', 'bar', 'baz')
        expected = {'foo': {'bar': 'baz'}, 'foo2': {'bar': 'baz'}}
        result = config._load([], [], [override1, override2])
        self.assertEqual(expected, result)

    def test_load_single_file(self):
        file1 = path_to_data_dir('file1.conf')
        expected = {'foo': {'bar': 'baz'}}
        result = config._load([file1], [], [])
        self.assertEqual(expected, result)

    def test_load_files(self):
        file1 = path_to_data_dir('file1.conf')
        file2 = path_to_data_dir('file2.conf')
        expected = {'foo': {'bar': 'baz'}, 'foo2': {'bar': 'baz'}}
        result = config._load([file1, file2], [], [])
        self.assertEqual(expected, result)

    def test_load_file_with_utf8(self):
        expected = {'foo': {'bar': 'æøå'.encode('utf-8')}}
        result = config._load([path_to_data_dir('file3.conf')], [], [])
        self.assertEqual(expected, result)

    def test_load_file_with_error(self):
        expected = {'foo': {'bar': 'baz'}}
        result = config._load([path_to_data_dir('file4.conf')], [], [])
        self.assertEqual(expected, result)


class ValidateTest(unittest.TestCase):
    def setUp(self):
        self.schema = config.ConfigSchema('foo')
        self.schema['bar'] = config.ConfigValue()

    def test_empty_config_no_schemas(self):
        conf, errors = config._validate({}, [])
        self.assertEqual({}, conf)
        self.assertEqual({}, errors)

    def test_config_no_schemas(self):
        raw_config = {'foo': {'bar': 'baz'}}
        conf, errors = config._validate(raw_config, [])
        self.assertEqual({}, conf)
        self.assertEqual({}, errors)

    def test_empty_config_single_schema(self):
        conf, errors = config._validate({}, [self.schema])
        self.assertEqual({'foo': {'bar': None}}, conf)
        self.assertEqual({'foo': {'bar': 'config key not found.'}}, errors)

    def test_config_single_schema(self):
        raw_config = {'foo': {'bar': 'baz'}}
        conf, errors = config._validate(raw_config, [self.schema])
        self.assertEqual({'foo': {'bar': 'baz'}}, conf)
        self.assertEqual({}, errors)

    def test_config_single_schema_config_error(self):
        raw_config = {'foo': {'bar': 'baz'}}
        self.schema['bar'] = mock.Mock()
        self.schema['bar'].deserialize.side_effect = ValueError('bad')
        conf, errors = config._validate(raw_config, [self.schema])
        self.assertEqual({'foo': {'bar': None}}, conf)
        self.assertEqual({'foo': {'bar': 'bad'}}, errors)

    # TODO: add more tests


INPUT_CONFIG = """# comments before first section should work

[section] anything goes ; after the [] block it seems.
; this is a valid comment
this-should-equal-baz = baz ; as this is a comment
this-should-equal-everything = baz # as this is not a comment

# this is also a comment ; and the next line should be a blank comment.
;
# foo # = should all be treated as a comment."""

PROCESSED_CONFIG = """[__COMMENTS__]
__HASH0__ = comments before first section should work
__BLANK1__ =
[section]
__SECTION2__ = anything goes
__INLINE3__ = after the [] block it seems.
__SEMICOLON4__ = this is a valid comment
this-should-equal-baz = baz
__INLINE5__ = as this is a comment
this-should-equal-everything = baz # as this is not a comment
__BLANK6__ =
__HASH7__ = this is also a comment
__INLINE8__ = and the next line should be a blank comment.
__SEMICOLON9__ =
__HASH10__ = foo # = should all be treated as a comment."""


class PreProcessorTest(unittest.TestCase):
    maxDiff = None  # Show entire diff.

    def test_empty_config(self):
        result = config._preprocess('')
        self.assertEqual(result, '[__COMMENTS__]')

    def test_plain_section(self):
        result = config._preprocess('[section]\nfoo = bar')
        self.assertEqual(result, '[__COMMENTS__]\n'
                                 '[section]\n'
                                 'foo = bar')

    def test_initial_comments(self):
        result = config._preprocess('; foobar')
        self.assertEqual(result, '[__COMMENTS__]\n'
                                 '__SEMICOLON0__ = foobar')

        result = config._preprocess('# foobar')
        self.assertEqual(result, '[__COMMENTS__]\n'
                                 '__HASH0__ = foobar')

        result = config._preprocess('; foo\n# bar')
        self.assertEqual(result, '[__COMMENTS__]\n'
                                 '__SEMICOLON0__ = foo\n'
                                 '__HASH1__ = bar')

    def test_initial_comment_inline_handling(self):
        result = config._preprocess('; foo ; bar ; baz')
        self.assertEqual(result, '[__COMMENTS__]\n'
                                 '__SEMICOLON0__ = foo\n'
                                 '__INLINE1__ = bar\n'
                                 '__INLINE2__ = baz')

    def test_inline_semicolon_comment(self):
        result = config._preprocess('[section]\nfoo = bar ; baz')
        self.assertEqual(result, '[__COMMENTS__]\n'
                                 '[section]\n'
                                 'foo = bar\n'
                                 '__INLINE0__ = baz')

    def test_no_inline_hash_comment(self):
        result = config._preprocess('[section]\nfoo = bar # baz')
        self.assertEqual(result, '[__COMMENTS__]\n'
                                 '[section]\n'
                                 'foo = bar # baz')

    def test_section_extra_text(self):
        result = config._preprocess('[section] foobar')
        self.assertEqual(result, '[__COMMENTS__]\n'
                                 '[section]\n'
                                 '__SECTION0__ = foobar')

    def test_section_extra_text_inline_semicolon(self):
        result = config._preprocess('[section] foobar ; baz')
        self.assertEqual(result, '[__COMMENTS__]\n'
                                 '[section]\n'
                                 '__SECTION0__ = foobar\n'
                                 '__INLINE1__ = baz')

    def test_conversion(self):
        """Tests all of the above cases at once."""
        result = config._preprocess(INPUT_CONFIG)
        self.assertEqual(result, PROCESSED_CONFIG)


class PostProcessorTest(unittest.TestCase):
    maxDiff = None  # Show entire diff.

    def test_empty_config(self):
        result = config._postprocess('[__COMMENTS__]')
        self.assertEqual(result, '')

    def test_plain_section(self):
        result = config._postprocess('[__COMMENTS__]\n'
                                     '[section]\n'
                                     'foo = bar')
        self.assertEqual(result, '[section]\nfoo = bar')

    def test_initial_comments(self):
        result = config._postprocess('[__COMMENTS__]\n'
                                     '__SEMICOLON0__ = foobar')
        self.assertEqual(result, '; foobar')

        result = config._postprocess('[__COMMENTS__]\n'
                                     '__HASH0__ = foobar')
        self.assertEqual(result, '# foobar')

        result = config._postprocess('[__COMMENTS__]\n'
                                     '__SEMICOLON0__ = foo\n'
                                     '__HASH1__ = bar')
        self.assertEqual(result, '; foo\n# bar')

    def test_initial_comment_inline_handling(self):
        result = config._postprocess('[__COMMENTS__]\n'
                                     '__SEMICOLON0__ = foo\n'
                                     '__INLINE1__ = bar\n'
                                     '__INLINE2__ = baz')
        self.assertEqual(result, '; foo ; bar ; baz')

    def test_inline_semicolon_comment(self):
        result = config._postprocess('[__COMMENTS__]\n'
                                     '[section]\n'
                                     'foo = bar\n'
                                     '__INLINE0__ = baz')
        self.assertEqual(result, '[section]\nfoo = bar ; baz')

    def test_no_inline_hash_comment(self):
        result = config._preprocess('[section]\nfoo = bar # baz')
        self.assertEqual(result, '[__COMMENTS__]\n'
                                 '[section]\n'
                                 'foo = bar # baz')

    def test_section_extra_text(self):
        result = config._postprocess('[__COMMENTS__]\n'
                                     '[section]\n'
                                     '__SECTION0__ = foobar')
        self.assertEqual(result, '[section] foobar')

    def test_section_extra_text_inline_semicolon(self):
        result = config._postprocess('[__COMMENTS__]\n'
                                     '[section]\n'
                                     '__SECTION0__ = foobar\n'
                                     '__INLINE1__ = baz')
        self.assertEqual(result, '[section] foobar ; baz')

    def test_conversion(self):
        result = config._postprocess(PROCESSED_CONFIG)
        self.assertEqual(result, INPUT_CONFIG)

########NEW FILE########
__FILENAME__ = test_schemas
from __future__ import unicode_literals

import logging
import unittest

import mock

from mopidy.config import schemas, types

from tests import any_unicode


class ConfigSchemaTest(unittest.TestCase):
    def setUp(self):
        self.schema = schemas.ConfigSchema('test')
        self.schema['foo'] = mock.Mock()
        self.schema['bar'] = mock.Mock()
        self.schema['baz'] = mock.Mock()
        self.values = {'bar': '123', 'foo': '456', 'baz': '678'}

    def test_deserialize(self):
        self.schema.deserialize(self.values)

    def test_deserialize_with_missing_value(self):
        del self.values['foo']

        result, errors = self.schema.deserialize(self.values)
        self.assertEqual({'foo': any_unicode}, errors)
        self.assertIsNone(result.pop('foo'))
        self.assertIsNotNone(result.pop('bar'))
        self.assertIsNotNone(result.pop('baz'))
        self.assertEqual({}, result)

    def test_deserialize_with_extra_value(self):
        self.values['extra'] = '123'

        result, errors = self.schema.deserialize(self.values)
        self.assertEqual({'extra': any_unicode}, errors)
        self.assertIsNotNone(result.pop('foo'))
        self.assertIsNotNone(result.pop('bar'))
        self.assertIsNotNone(result.pop('baz'))
        self.assertEqual({}, result)

    def test_deserialize_with_deserialization_error(self):
        self.schema['foo'].deserialize.side_effect = ValueError('failure')

        result, errors = self.schema.deserialize(self.values)
        self.assertEqual({'foo': 'failure'}, errors)
        self.assertIsNone(result.pop('foo'))
        self.assertIsNotNone(result.pop('bar'))
        self.assertIsNotNone(result.pop('baz'))
        self.assertEqual({}, result)

    def test_deserialize_with_multiple_deserialization_errors(self):
        self.schema['foo'].deserialize.side_effect = ValueError('failure')
        self.schema['bar'].deserialize.side_effect = ValueError('other')

        result, errors = self.schema.deserialize(self.values)
        self.assertEqual({'foo': 'failure', 'bar': 'other'}, errors)
        self.assertIsNone(result.pop('foo'))
        self.assertIsNone(result.pop('bar'))
        self.assertIsNotNone(result.pop('baz'))
        self.assertEqual({}, result)

    def test_deserialize_deserialization_unknown_and_missing_errors(self):
        self.values['extra'] = '123'
        self.schema['bar'].deserialize.side_effect = ValueError('failure')
        del self.values['baz']

        result, errors = self.schema.deserialize(self.values)
        self.assertIn('unknown', errors['extra'])
        self.assertNotIn('foo', errors)
        self.assertIn('failure', errors['bar'])
        self.assertIn('not found', errors['baz'])

        self.assertNotIn('unknown', result)
        self.assertIn('foo', result)
        self.assertIsNone(result['bar'])
        self.assertIsNone(result['baz'])

    def test_deserialize_deprecated_value(self):
        self.schema['foo'] = types.Deprecated()

        result, errors = self.schema.deserialize(self.values)
        self.assertItemsEqual(['bar', 'baz'], result.keys())
        self.assertNotIn('foo', errors)


class LogLevelConfigSchemaTest(unittest.TestCase):
    def test_conversion(self):
        schema = schemas.LogLevelConfigSchema('test')
        result, errors = schema.deserialize(
            {'foo.bar': 'DEBUG', 'baz': 'INFO'})

        self.assertEqual(logging.DEBUG, result['foo.bar'])
        self.assertEqual(logging.INFO, result['baz'])


class DidYouMeanTest(unittest.TestCase):
    def testSuggestoins(self):
        choices = ('enabled', 'username', 'password', 'bitrate', 'timeout')

        suggestion = schemas._did_you_mean('bitrate', choices)
        self.assertEqual(suggestion, 'bitrate')

        suggestion = schemas._did_you_mean('bitrote', choices)
        self.assertEqual(suggestion, 'bitrate')

        suggestion = schemas._did_you_mean('Bitrot', choices)
        self.assertEqual(suggestion, 'bitrate')

        suggestion = schemas._did_you_mean('BTROT', choices)
        self.assertEqual(suggestion, 'bitrate')

        suggestion = schemas._did_you_mean('btro', choices)
        self.assertEqual(suggestion, None)

########NEW FILE########
__FILENAME__ = test_types
# encoding: utf-8

from __future__ import unicode_literals

import logging
import socket
import unittest

import mock

from mopidy.config import types

# TODO: DecodeTest and EncodeTest


class ConfigValueTest(unittest.TestCase):
    def test_deserialize_passes_through(self):
        value = types.ConfigValue()
        sentinel = object()
        self.assertEqual(sentinel, value.deserialize(sentinel))

    def test_serialize_conversion_to_string(self):
        value = types.ConfigValue()
        self.assertIsInstance(value.serialize(object()), bytes)

    def test_serialize_none(self):
        value = types.ConfigValue()
        result = value.serialize(None)
        self.assertIsInstance(result, bytes)
        self.assertEqual(b'', result)

    def test_serialize_supports_display(self):
        value = types.ConfigValue()
        self.assertIsInstance(value.serialize(object(), display=True), bytes)


class DeprecatedTest(unittest.TestCase):
    def test_deserialize_returns_deprecated_value(self):
        self.assertIsInstance(types.Deprecated().deserialize(b'foobar'),
                              types.DeprecatedValue)

    def test_serialize_returns_deprecated_value(self):
        self.assertIsInstance(types.Deprecated().serialize('foobar'),
                              types.DeprecatedValue)


class StringTest(unittest.TestCase):
    def test_deserialize_conversion_success(self):
        value = types.String()
        self.assertEqual('foo', value.deserialize(b' foo '))
        self.assertIsInstance(value.deserialize(b'foo'), unicode)

    def test_deserialize_decodes_utf8(self):
        value = types.String()
        result = value.deserialize('æøå'.encode('utf-8'))
        self.assertEqual('æøå', result)

    def test_deserialize_does_not_double_encode_unicode(self):
        value = types.String()
        result = value.deserialize('æøå')
        self.assertEqual('æøå', result)

    def test_deserialize_handles_escapes(self):
        value = types.String(optional=True)
        result = value.deserialize(b'a\\t\\nb')
        self.assertEqual('a\t\nb', result)

    def test_deserialize_enforces_choices(self):
        value = types.String(choices=['foo', 'bar', 'baz'])
        self.assertEqual('foo', value.deserialize(b'foo'))
        self.assertRaises(ValueError, value.deserialize, b'foobar')

    def test_deserialize_enforces_required(self):
        value = types.String()
        self.assertRaises(ValueError, value.deserialize, b'')

    def test_deserialize_respects_optional(self):
        value = types.String(optional=True)
        self.assertIsNone(value.deserialize(b''))
        self.assertIsNone(value.deserialize(b' '))

    def test_deserialize_decode_failure(self):
        value = types.String()
        incorrectly_encoded_bytes = u'æøå'.encode('iso-8859-1')
        self.assertRaises(
            ValueError, value.deserialize, incorrectly_encoded_bytes)

    def test_serialize_encodes_utf8(self):
        value = types.String()
        result = value.serialize('æøå')
        self.assertIsInstance(result, bytes)
        self.assertEqual('æøå'.encode('utf-8'), result)

    def test_serialize_does_not_encode_bytes(self):
        value = types.String()
        result = value.serialize('æøå'.encode('utf-8'))
        self.assertIsInstance(result, bytes)
        self.assertEqual('æøå'.encode('utf-8'), result)

    def test_serialize_handles_escapes(self):
        value = types.String()
        result = value.serialize('a\n\tb')
        self.assertIsInstance(result, bytes)
        self.assertEqual(r'a\n\tb'.encode('utf-8'), result)

    def test_serialize_none(self):
        value = types.String()
        result = value.serialize(None)
        self.assertIsInstance(result, bytes)
        self.assertEqual(b'', result)

    def test_deserialize_enforces_choices_optional(self):
        value = types.String(optional=True, choices=['foo', 'bar', 'baz'])
        self.assertEqual(None, value.deserialize(b''))
        self.assertRaises(ValueError, value.deserialize, b'foobar')


class SecretTest(unittest.TestCase):
    def test_deserialize_decodes_utf8(self):
        value = types.Secret()
        result = value.deserialize('æøå'.encode('utf-8'))
        self.assertIsInstance(result, unicode)
        self.assertEqual('æøå', result)

    def test_deserialize_enforces_required(self):
        value = types.Secret()
        self.assertRaises(ValueError, value.deserialize, b'')

    def test_deserialize_respects_optional(self):
        value = types.Secret(optional=True)
        self.assertIsNone(value.deserialize(b''))
        self.assertIsNone(value.deserialize(b' '))

    def test_serialize_none(self):
        value = types.Secret()
        result = value.serialize(None)
        self.assertIsInstance(result, bytes)
        self.assertEqual(b'', result)

    def test_serialize_for_display_masks_value(self):
        value = types.Secret()
        result = value.serialize('s3cret', display=True)
        self.assertIsInstance(result, bytes)
        self.assertEqual(b'********', result)

    def test_serialize_none_for_display(self):
        value = types.Secret()
        result = value.serialize(None, display=True)
        self.assertIsInstance(result, bytes)
        self.assertEqual(b'', result)


class IntegerTest(unittest.TestCase):
    def test_deserialize_conversion_success(self):
        value = types.Integer()
        self.assertEqual(123, value.deserialize('123'))
        self.assertEqual(0, value.deserialize('0'))
        self.assertEqual(-10, value.deserialize('-10'))

    def test_deserialize_conversion_failure(self):
        value = types.Integer()
        self.assertRaises(ValueError, value.deserialize, 'asd')
        self.assertRaises(ValueError, value.deserialize, '3.14')
        self.assertRaises(ValueError, value.deserialize, '')
        self.assertRaises(ValueError, value.deserialize, ' ')

    def test_deserialize_enforces_choices(self):
        value = types.Integer(choices=[1, 2, 3])
        self.assertEqual(3, value.deserialize('3'))
        self.assertRaises(ValueError, value.deserialize, '5')

    def test_deserialize_enforces_minimum(self):
        value = types.Integer(minimum=10)
        self.assertEqual(15, value.deserialize('15'))
        self.assertRaises(ValueError, value.deserialize, '5')

    def test_deserialize_enforces_maximum(self):
        value = types.Integer(maximum=10)
        self.assertEqual(5, value.deserialize('5'))
        self.assertRaises(ValueError, value.deserialize, '15')

    def test_deserialize_respects_optional(self):
        value = types.Integer(optional=True)
        self.assertEqual(None, value.deserialize(''))


class BooleanTest(unittest.TestCase):
    def test_deserialize_conversion_success(self):
        value = types.Boolean()
        for true in ('1', 'yes', 'true', 'on'):
            self.assertIs(value.deserialize(true), True)
            self.assertIs(value.deserialize(true.upper()), True)
            self.assertIs(value.deserialize(true.capitalize()), True)
        for false in ('0', 'no', 'false', 'off'):
            self.assertIs(value.deserialize(false), False)
            self.assertIs(value.deserialize(false.upper()), False)
            self.assertIs(value.deserialize(false.capitalize()), False)

    def test_deserialize_conversion_failure(self):
        value = types.Boolean()
        self.assertRaises(ValueError, value.deserialize, 'nope')
        self.assertRaises(ValueError, value.deserialize, 'sure')
        self.assertRaises(ValueError, value.deserialize, '')

    def test_serialize_true(self):
        value = types.Boolean()
        result = value.serialize(True)
        self.assertEqual(b'true', result)
        self.assertIsInstance(result, bytes)

    def test_serialize_false(self):
        value = types.Boolean()
        result = value.serialize(False)
        self.assertEqual(b'false', result)
        self.assertIsInstance(result, bytes)

    # TODO: test None or other invalid values into serialize?


class ListTest(unittest.TestCase):
    # TODO: add test_deserialize_ignores_blank
    # TODO: add test_serialize_ignores_blank
    # TODO: add test_deserialize_handles_escapes

    def test_deserialize_conversion_success(self):
        value = types.List()

        expected = ('foo', 'bar', 'baz')
        self.assertEqual(expected, value.deserialize(b'foo, bar ,baz '))

        expected = ('foo,bar', 'bar', 'baz')
        self.assertEqual(expected, value.deserialize(b' foo,bar\nbar\nbaz'))

    def test_deserialize_creates_tuples(self):
        value = types.List(optional=True)
        self.assertIsInstance(value.deserialize(b'foo,bar,baz'), tuple)
        self.assertIsInstance(value.deserialize(b''), tuple)

    def test_deserialize_decodes_utf8(self):
        value = types.List()

        result = value.deserialize('æ, ø, å'.encode('utf-8'))
        self.assertEqual(('æ', 'ø', 'å'), result)

        result = value.deserialize('æ\nø\nå'.encode('utf-8'))
        self.assertEqual(('æ', 'ø', 'å'), result)

    def test_deserialize_does_not_double_encode_unicode(self):
        value = types.List()

        result = value.deserialize('æ, ø, å')
        self.assertEqual(('æ', 'ø', 'å'), result)

        result = value.deserialize('æ\nø\nå')
        self.assertEqual(('æ', 'ø', 'å'), result)

    def test_deserialize_enforces_required(self):
        value = types.List()
        self.assertRaises(ValueError, value.deserialize, b'')

    def test_deserialize_respects_optional(self):
        value = types.List(optional=True)
        self.assertEqual(tuple(), value.deserialize(b''))

    def test_serialize(self):
        value = types.List()
        result = value.serialize(('foo', 'bar', 'baz'))
        self.assertIsInstance(result, bytes)
        self.assertRegexpMatches(result, r'foo\n\s*bar\n\s*baz')


class LogLevelTest(unittest.TestCase):
    levels = {'critical': logging.CRITICAL,
              'error': logging.ERROR,
              'warning': logging.WARNING,
              'info': logging.INFO,
              'debug': logging.DEBUG}

    def test_deserialize_conversion_success(self):
        value = types.LogLevel()
        for name, level in self.levels.items():
            self.assertEqual(level, value.deserialize(name))
            self.assertEqual(level, value.deserialize(name.upper()))
            self.assertEqual(level, value.deserialize(name.capitalize()))

    def test_deserialize_conversion_failure(self):
        value = types.LogLevel()
        self.assertRaises(ValueError, value.deserialize, 'nope')
        self.assertRaises(ValueError, value.deserialize, 'sure')
        self.assertRaises(ValueError, value.deserialize, '')
        self.assertRaises(ValueError, value.deserialize, ' ')

    def test_serialize(self):
        value = types.LogLevel()
        for name, level in self.levels.items():
            self.assertEqual(name, value.serialize(level))
        self.assertEqual(b'', value.serialize(1337))


class HostnameTest(unittest.TestCase):
    @mock.patch('socket.getaddrinfo')
    def test_deserialize_conversion_success(self, getaddrinfo_mock):
        value = types.Hostname()
        value.deserialize('example.com')
        getaddrinfo_mock.assert_called_once_with('example.com', None)

    @mock.patch('socket.getaddrinfo')
    def test_deserialize_conversion_failure(self, getaddrinfo_mock):
        value = types.Hostname()
        getaddrinfo_mock.side_effect = socket.error
        self.assertRaises(ValueError, value.deserialize, 'example.com')

    @mock.patch('socket.getaddrinfo')
    def test_deserialize_enforces_required(self, getaddrinfo_mock):
        value = types.Hostname()
        self.assertRaises(ValueError, value.deserialize, '')
        self.assertEqual(0, getaddrinfo_mock.call_count)

    @mock.patch('socket.getaddrinfo')
    def test_deserialize_respects_optional(self, getaddrinfo_mock):
        value = types.Hostname(optional=True)
        self.assertIsNone(value.deserialize(''))
        self.assertIsNone(value.deserialize(' '))
        self.assertEqual(0, getaddrinfo_mock.call_count)


class PortTest(unittest.TestCase):
    def test_valid_ports(self):
        value = types.Port()
        self.assertEqual(0, value.deserialize('0'))
        self.assertEqual(1, value.deserialize('1'))
        self.assertEqual(80, value.deserialize('80'))
        self.assertEqual(6600, value.deserialize('6600'))
        self.assertEqual(65535, value.deserialize('65535'))

    def test_invalid_ports(self):
        value = types.Port()
        self.assertRaises(ValueError, value.deserialize, '65536')
        self.assertRaises(ValueError, value.deserialize, '100000')
        self.assertRaises(ValueError, value.deserialize, '-1')
        self.assertRaises(ValueError, value.deserialize, '')


class ExpandedPathTest(unittest.TestCase):
    def test_is_bytes(self):
        self.assertIsInstance(types.ExpandedPath(b'/tmp', b'foo'), bytes)

    def test_defaults_to_expanded(self):
        original = b'~'
        expanded = b'expanded_path'
        self.assertEqual(expanded, types.ExpandedPath(original, expanded))

    @mock.patch('mopidy.utils.path.expand_path')
    def test_orginal_stores_unexpanded(self, expand_path_mock):
        original = b'~'
        expanded = b'expanded_path'
        result = types.ExpandedPath(original, expanded)
        self.assertEqual(original, result.original)


class PathTest(unittest.TestCase):
    def test_deserialize_conversion_success(self):
        result = types.Path().deserialize(b'/foo')
        self.assertEqual('/foo', result)
        self.assertIsInstance(result, types.ExpandedPath)
        self.assertIsInstance(result, bytes)

    def test_deserialize_enforces_required(self):
        value = types.Path()
        self.assertRaises(ValueError, value.deserialize, b'')

    def test_deserialize_respects_optional(self):
        value = types.Path(optional=True)
        self.assertIsNone(value.deserialize(b''))
        self.assertIsNone(value.deserialize(b' '))

    def test_serialize_uses_original(self):
        path = types.ExpandedPath(b'original_path', b'expanded_path')
        value = types.Path()
        self.assertEqual('expanded_path', path)
        self.assertEqual('original_path', value.serialize(path))

    def test_serialize_plain_string(self):
        value = types.Path()
        self.assertEqual('path', value.serialize(b'path'))

    def test_serialize_unicode_string(self):
        value = types.Path()
        self.assertRaises(ValueError, value.serialize, 'æøå')

########NEW FILE########
__FILENAME__ = test_validator
from __future__ import unicode_literals

import unittest

from mopidy.config import validators


class ValidateChoiceTest(unittest.TestCase):
    def test_no_choices_passes(self):
        validators.validate_choice('foo', None)

    def test_valid_value_passes(self):
        validators.validate_choice('foo', ['foo', 'bar', 'baz'])
        validators.validate_choice(1, [1, 2, 3])

    def test_empty_choices_fails(self):
        self.assertRaises(ValueError, validators.validate_choice, 'foo', [])

    def test_invalid_value_fails(self):
        words = ['foo', 'bar', 'baz']
        self.assertRaises(
            ValueError, validators.validate_choice, 'foobar', words)
        self.assertRaises(
            ValueError, validators.validate_choice, 5, [1, 2, 3])


class ValidateMinimumTest(unittest.TestCase):
    def test_no_minimum_passes(self):
        validators.validate_minimum(10, None)

    def test_valid_value_passes(self):
        validators.validate_minimum(10, 5)

    def test_to_small_value_fails(self):
        self.assertRaises(ValueError, validators.validate_minimum, 10, 20)

    def test_to_small_value_fails_with_zero_as_minimum(self):
        self.assertRaises(ValueError, validators.validate_minimum, -1, 0)


class ValidateMaximumTest(unittest.TestCase):
    def test_no_maximum_passes(self):
        validators.validate_maximum(5, None)

    def test_valid_value_passes(self):
        validators.validate_maximum(5, 10)

    def test_to_large_value_fails(self):
        self.assertRaises(ValueError, validators.validate_maximum, 10, 5)

    def test_to_large_value_fails_with_zero_as_maximum(self):
        self.assertRaises(ValueError, validators.validate_maximum, 5, 0)


class ValidateRequiredTest(unittest.TestCase):
    def test_passes_when_false(self):
        validators.validate_required('foo', False)
        validators.validate_required('', False)
        validators.validate_required('  ', False)
        validators.validate_required([], False)

    def test_passes_when_required_and_set(self):
        validators.validate_required('foo', True)
        validators.validate_required(' foo ', True)
        validators.validate_required([1], True)

    def test_blocks_when_required_and_emtpy(self):
        self.assertRaises(ValueError, validators.validate_required, '', True)
        self.assertRaises(ValueError, validators.validate_required, [], True)

########NEW FILE########
__FILENAME__ = test_actor
from __future__ import unicode_literals

import unittest

import mock

import pykka

from mopidy.core import Core
from mopidy.utils import versioning


class CoreActorTest(unittest.TestCase):
    def setUp(self):
        self.backend1 = mock.Mock()
        self.backend1.uri_schemes.get.return_value = ['dummy1']
        self.backend1.actor_ref.actor_class.__name__ = b'B1'

        self.backend2 = mock.Mock()
        self.backend2.uri_schemes.get.return_value = ['dummy2']
        self.backend2.actor_ref.actor_class.__name__ = b'B2'

        self.core = Core(audio=None, backends=[self.backend1, self.backend2])

    def tearDown(self):
        pykka.ActorRegistry.stop_all()

    def test_uri_schemes_has_uris_from_all_backends(self):
        result = self.core.uri_schemes

        self.assertIn('dummy1', result)
        self.assertIn('dummy2', result)

    def test_backends_with_colliding_uri_schemes_fails(self):
        self.backend2.uri_schemes.get.return_value = ['dummy1', 'dummy2']

        self.assertRaisesRegexp(
            AssertionError,
            'Cannot add URI scheme dummy1 for B2, it is already handled by B1',
            Core, audio=None, backends=[self.backend1, self.backend2])

    def test_version(self):
        self.assertEqual(self.core.version, versioning.get_version())

########NEW FILE########
__FILENAME__ = test_events
from __future__ import unicode_literals

import unittest

import mock

import pykka

from mopidy import core
from mopidy.backend import dummy
from mopidy.models import Track


@mock.patch.object(core.CoreListener, 'send')
class BackendEventsTest(unittest.TestCase):
    def setUp(self):
        self.backend = dummy.create_dummy_backend_proxy()
        self.core = core.Core.start(backends=[self.backend]).proxy()

    def tearDown(self):
        pykka.ActorRegistry.stop_all()

    def test_backends_playlists_loaded_forwards_event_to_frontends(self, send):
        self.core.playlists_loaded().get()

        self.assertEqual(send.call_args[0][0], 'playlists_loaded')

    def test_tracklist_add_sends_tracklist_changed_event(self, send):
        send.reset_mock()

        self.core.tracklist.add([Track(uri='dummy:a')]).get()

        self.assertEqual(send.call_args[0][0], 'tracklist_changed')

    def test_tracklist_clear_sends_tracklist_changed_event(self, send):
        self.core.tracklist.add([Track(uri='dummy:a')]).get()
        send.reset_mock()

        self.core.tracklist.clear().get()

        self.assertEqual(send.call_args[0][0], 'tracklist_changed')

    def test_tracklist_move_sends_tracklist_changed_event(self, send):
        self.core.tracklist.add(
            [Track(uri='dummy:a'), Track(uri='dummy:b')]).get()
        send.reset_mock()

        self.core.tracklist.move(0, 1, 1).get()

        self.assertEqual(send.call_args[0][0], 'tracklist_changed')

    def test_tracklist_remove_sends_tracklist_changed_event(self, send):
        self.core.tracklist.add([Track(uri='dummy:a')]).get()
        send.reset_mock()

        self.core.tracklist.remove(uri=['dummy:a']).get()

        self.assertEqual(send.call_args[0][0], 'tracklist_changed')

    def test_tracklist_shuffle_sends_tracklist_changed_event(self, send):
        self.core.tracklist.add(
            [Track(uri='dummy:a'), Track(uri='dummy:b')]).get()
        send.reset_mock()

        self.core.tracklist.shuffle().get()

        self.assertEqual(send.call_args[0][0], 'tracklist_changed')

    def test_playlists_refresh_sends_playlists_loaded_event(self, send):
        send.reset_mock()

        self.core.playlists.refresh().get()

        self.assertEqual(send.call_args[0][0], 'playlists_loaded')

    def test_playlists_refresh_uri_sends_playlists_loaded_event(self, send):
        send.reset_mock()

        self.core.playlists.refresh(uri_scheme='dummy').get()

        self.assertEqual(send.call_args[0][0], 'playlists_loaded')

    def test_playlists_create_sends_playlist_changed_event(self, send):
        send.reset_mock()

        self.core.playlists.create('foo').get()

        self.assertEqual(send.call_args[0][0], 'playlist_changed')

    @unittest.SkipTest
    def test_playlists_delete_sends_playlist_deleted_event(self, send):
        # TODO We should probably add a playlist_deleted event
        pass

    def test_playlists_save_sends_playlist_changed_event(self, send):
        playlist = self.core.playlists.create('foo').get()
        playlist = playlist.copy(name='bar')
        send.reset_mock()

        self.core.playlists.save(playlist).get()

        self.assertEqual(send.call_args[0][0], 'playlist_changed')

########NEW FILE########
__FILENAME__ = test_library
from __future__ import unicode_literals

import unittest

import mock

from mopidy import backend, core
from mopidy.models import Ref, SearchResult, Track


class CoreLibraryTest(unittest.TestCase):
    def setUp(self):
        dummy1_root = Ref.directory(uri='dummy1:directory', name='dummy1')
        self.backend1 = mock.Mock()
        self.backend1.uri_schemes.get.return_value = ['dummy1']
        self.library1 = mock.Mock(spec=backend.LibraryProvider)
        self.library1.root_directory.get.return_value = dummy1_root
        self.backend1.library = self.library1

        dummy2_root = Ref.directory(uri='dummy2:directory', name='dummy2')
        self.backend2 = mock.Mock()
        self.backend2.uri_schemes.get.return_value = ['dummy2']
        self.library2 = mock.Mock(spec=backend.LibraryProvider)
        self.library2.root_directory.get.return_value = dummy2_root
        self.backend2.library = self.library2

        # A backend without the optional library provider
        self.backend3 = mock.Mock()
        self.backend3.uri_schemes.get.return_value = ['dummy3']
        self.backend3.has_library().get.return_value = False
        self.backend3.has_library_browse().get.return_value = False

        self.core = core.Core(audio=None, backends=[
            self.backend1, self.backend2, self.backend3])

    def test_browse_root_returns_dir_ref_for_each_lib_with_root_dir_name(self):
        result = self.core.library.browse(None)

        self.assertEqual(result, [
            Ref.directory(uri='dummy1:directory', name='dummy1'),
            Ref.directory(uri='dummy2:directory', name='dummy2'),
        ])
        self.assertFalse(self.library1.browse.called)
        self.assertFalse(self.library2.browse.called)
        self.assertFalse(self.backend3.library.browse.called)

    def test_browse_empty_string_returns_nothing(self):
        result = self.core.library.browse('')

        self.assertEqual(result, [])
        self.assertFalse(self.library1.browse.called)
        self.assertFalse(self.library2.browse.called)

    def test_browse_dummy1_selects_dummy1_backend(self):
        self.library1.browse().get.return_value = [
            Ref.directory(uri='dummy1:directory:/foo/bar', name='bar'),
            Ref.track(uri='dummy1:track:/foo/baz.mp3', name='Baz'),
        ]
        self.library1.browse.reset_mock()

        self.core.library.browse('dummy1:directory:/foo')

        self.assertEqual(self.library1.browse.call_count, 1)
        self.assertEqual(self.library2.browse.call_count, 0)
        self.library1.browse.assert_called_with('dummy1:directory:/foo')

    def test_browse_dummy2_selects_dummy2_backend(self):
        self.library2.browse().get.return_value = [
            Ref.directory(uri='dummy2:directory:/bar/baz', name='quux'),
            Ref.track(uri='dummy2:track:/bar/foo.mp3', name='Baz'),
        ]
        self.library2.browse.reset_mock()

        self.core.library.browse('dummy2:directory:/bar')

        self.assertEqual(self.library1.browse.call_count, 0)
        self.assertEqual(self.library2.browse.call_count, 1)
        self.library2.browse.assert_called_with('dummy2:directory:/bar')

    def test_browse_dummy3_returns_nothing(self):
        result = self.core.library.browse('dummy3:test')

        self.assertEqual(result, [])
        self.assertEqual(self.library1.browse.call_count, 0)
        self.assertEqual(self.library2.browse.call_count, 0)

    def test_browse_dir_returns_subdirs_and_tracks(self):
        self.library1.browse().get.return_value = [
            Ref.directory(uri='dummy1:directory:/foo/bar', name='Bar'),
            Ref.track(uri='dummy1:track:/foo/baz.mp3', name='Baz'),
        ]
        self.library1.browse.reset_mock()

        result = self.core.library.browse('dummy1:directory:/foo')
        self.assertEqual(result, [
            Ref.directory(uri='dummy1:directory:/foo/bar', name='Bar'),
            Ref.track(uri='dummy1:track:/foo/baz.mp3', name='Baz'),
        ])

    def test_lookup_selects_dummy1_backend(self):
        self.core.library.lookup('dummy1:a')

        self.library1.lookup.assert_called_once_with('dummy1:a')
        self.assertFalse(self.library2.lookup.called)

    def test_lookup_selects_dummy2_backend(self):
        self.core.library.lookup('dummy2:a')

        self.assertFalse(self.library1.lookup.called)
        self.library2.lookup.assert_called_once_with('dummy2:a')

    def test_lookup_returns_nothing_for_dummy3_track(self):
        result = self.core.library.lookup('dummy3:a')

        self.assertEqual(result, [])
        self.assertFalse(self.library1.lookup.called)
        self.assertFalse(self.library2.lookup.called)

    def test_refresh_with_uri_selects_dummy1_backend(self):
        self.core.library.refresh('dummy1:a')

        self.library1.refresh.assert_called_once_with('dummy1:a')
        self.assertFalse(self.library2.refresh.called)

    def test_refresh_with_uri_selects_dummy2_backend(self):
        self.core.library.refresh('dummy2:a')

        self.assertFalse(self.library1.refresh.called)
        self.library2.refresh.assert_called_once_with('dummy2:a')

    def test_refresh_with_uri_fails_silently_for_dummy3_uri(self):
        self.core.library.refresh('dummy3:a')

        self.assertFalse(self.library1.refresh.called)
        self.assertFalse(self.library2.refresh.called)

    def test_refresh_without_uri_calls_all_backends(self):
        self.core.library.refresh()

        self.library1.refresh.assert_called_once_with(None)
        self.library2.refresh.assert_called_once_with(None)

    def test_find_exact_combines_results_from_all_backends(self):
        track1 = Track(uri='dummy1:a')
        track2 = Track(uri='dummy2:a')
        result1 = SearchResult(tracks=[track1])
        result2 = SearchResult(tracks=[track2])

        self.library1.find_exact().get.return_value = result1
        self.library1.find_exact.reset_mock()
        self.library2.find_exact().get.return_value = result2
        self.library2.find_exact.reset_mock()

        result = self.core.library.find_exact(any=['a'])

        self.assertIn(result1, result)
        self.assertIn(result2, result)
        self.library1.find_exact.assert_called_once_with(
            query=dict(any=['a']), uris=None)
        self.library2.find_exact.assert_called_once_with(
            query=dict(any=['a']), uris=None)

    def test_find_exact_with_uris_selects_dummy1_backend(self):
        self.core.library.find_exact(
            any=['a'], uris=['dummy1:', 'dummy1:foo', 'dummy3:'])

        self.library1.find_exact.assert_called_once_with(
            query=dict(any=['a']), uris=['dummy1:', 'dummy1:foo'])
        self.assertFalse(self.library2.find_exact.called)

    def test_find_exact_with_uris_selects_both_backends(self):
        self.core.library.find_exact(
            any=['a'], uris=['dummy1:', 'dummy1:foo', 'dummy2:'])

        self.library1.find_exact.assert_called_once_with(
            query=dict(any=['a']), uris=['dummy1:', 'dummy1:foo'])
        self.library2.find_exact.assert_called_once_with(
            query=dict(any=['a']), uris=['dummy2:'])

    def test_find_exact_filters_out_none(self):
        track1 = Track(uri='dummy1:a')
        result1 = SearchResult(tracks=[track1])

        self.library1.find_exact().get.return_value = result1
        self.library1.find_exact.reset_mock()
        self.library2.find_exact().get.return_value = None
        self.library2.find_exact.reset_mock()

        result = self.core.library.find_exact(any=['a'])

        self.assertIn(result1, result)
        self.assertNotIn(None, result)
        self.library1.find_exact.assert_called_once_with(
            query=dict(any=['a']), uris=None)
        self.library2.find_exact.assert_called_once_with(
            query=dict(any=['a']), uris=None)

    def test_find_accepts_query_dict_instead_of_kwargs(self):
        track1 = Track(uri='dummy1:a')
        track2 = Track(uri='dummy2:a')
        result1 = SearchResult(tracks=[track1])
        result2 = SearchResult(tracks=[track2])

        self.library1.find_exact().get.return_value = result1
        self.library1.find_exact.reset_mock()
        self.library2.find_exact().get.return_value = result2
        self.library2.find_exact.reset_mock()

        result = self.core.library.find_exact(dict(any=['a']))

        self.assertIn(result1, result)
        self.assertIn(result2, result)
        self.library1.find_exact.assert_called_once_with(
            query=dict(any=['a']), uris=None)
        self.library2.find_exact.assert_called_once_with(
            query=dict(any=['a']), uris=None)

    def test_search_combines_results_from_all_backends(self):
        track1 = Track(uri='dummy1:a')
        track2 = Track(uri='dummy2:a')
        result1 = SearchResult(tracks=[track1])
        result2 = SearchResult(tracks=[track2])

        self.library1.search().get.return_value = result1
        self.library1.search.reset_mock()
        self.library2.search().get.return_value = result2
        self.library2.search.reset_mock()

        result = self.core.library.search(any=['a'])

        self.assertIn(result1, result)
        self.assertIn(result2, result)
        self.library1.search.assert_called_once_with(
            query=dict(any=['a']), uris=None)
        self.library2.search.assert_called_once_with(
            query=dict(any=['a']), uris=None)

    def test_search_with_uris_selects_dummy1_backend(self):
        self.core.library.search(
            query=dict(any=['a']), uris=['dummy1:', 'dummy1:foo', 'dummy3:'])

        self.library1.search.assert_called_once_with(
            query=dict(any=['a']), uris=['dummy1:', 'dummy1:foo'])
        self.assertFalse(self.library2.search.called)

    def test_search_with_uris_selects_both_backends(self):
        self.core.library.search(
            query=dict(any=['a']), uris=['dummy1:', 'dummy1:foo', 'dummy2:'])

        self.library1.search.assert_called_once_with(
            query=dict(any=['a']), uris=['dummy1:', 'dummy1:foo'])
        self.library2.search.assert_called_once_with(
            query=dict(any=['a']), uris=['dummy2:'])

    def test_search_filters_out_none(self):
        track1 = Track(uri='dummy1:a')
        result1 = SearchResult(tracks=[track1])

        self.library1.search().get.return_value = result1
        self.library1.search.reset_mock()
        self.library2.search().get.return_value = None
        self.library2.search.reset_mock()

        result = self.core.library.search(any=['a'])

        self.assertIn(result1, result)
        self.assertNotIn(None, result)
        self.library1.search.assert_called_once_with(
            query=dict(any=['a']), uris=None)
        self.library2.search.assert_called_once_with(
            query=dict(any=['a']), uris=None)

    def test_search_accepts_query_dict_instead_of_kwargs(self):
        track1 = Track(uri='dummy1:a')
        track2 = Track(uri='dummy2:a')
        result1 = SearchResult(tracks=[track1])
        result2 = SearchResult(tracks=[track2])

        self.library1.search().get.return_value = result1
        self.library1.search.reset_mock()
        self.library2.search().get.return_value = result2
        self.library2.search.reset_mock()

        result = self.core.library.search(dict(any=['a']))

        self.assertIn(result1, result)
        self.assertIn(result2, result)
        self.library1.search.assert_called_once_with(
            query=dict(any=['a']), uris=None)
        self.library2.search.assert_called_once_with(
            query=dict(any=['a']), uris=None)

########NEW FILE########
__FILENAME__ = test_listener
from __future__ import unicode_literals

import unittest

import mock

from mopidy.core import CoreListener, PlaybackState
from mopidy.models import Playlist, TlTrack


class CoreListenerTest(unittest.TestCase):
    def setUp(self):
        self.listener = CoreListener()

    def test_on_event_forwards_to_specific_handler(self):
        self.listener.track_playback_paused = mock.Mock()

        self.listener.on_event(
            'track_playback_paused', track=TlTrack(), position=0)

        self.listener.track_playback_paused.assert_called_with(
            track=TlTrack(), position=0)

    def test_listener_has_default_impl_for_track_playback_paused(self):
        self.listener.track_playback_paused(TlTrack(), 0)

    def test_listener_has_default_impl_for_track_playback_resumed(self):
        self.listener.track_playback_resumed(TlTrack(), 0)

    def test_listener_has_default_impl_for_track_playback_started(self):
        self.listener.track_playback_started(TlTrack())

    def test_listener_has_default_impl_for_track_playback_ended(self):
        self.listener.track_playback_ended(TlTrack(), 0)

    def test_listener_has_default_impl_for_playback_state_changed(self):
        self.listener.playback_state_changed(
            PlaybackState.STOPPED, PlaybackState.PLAYING)

    def test_listener_has_default_impl_for_tracklist_changed(self):
        self.listener.tracklist_changed()

    def test_listener_has_default_impl_for_playlists_loaded(self):
        self.listener.playlists_loaded()

    def test_listener_has_default_impl_for_playlist_changed(self):
        self.listener.playlist_changed(Playlist())

    def test_listener_has_default_impl_for_options_changed(self):
        self.listener.options_changed()

    def test_listener_has_default_impl_for_volume_changed(self):
        self.listener.volume_changed(70)

    def test_listener_has_default_impl_for_mute_changed(self):
        self.listener.mute_changed(True)

    def test_listener_has_default_impl_for_seeked(self):
        self.listener.seeked(0)

########NEW FILE########
__FILENAME__ = test_playback
from __future__ import unicode_literals

import unittest

import mock

from mopidy import backend, core
from mopidy.models import Track


class CorePlaybackTest(unittest.TestCase):
    def setUp(self):
        self.backend1 = mock.Mock()
        self.backend1.uri_schemes.get.return_value = ['dummy1']
        self.playback1 = mock.Mock(spec=backend.PlaybackProvider)
        self.playback1.get_time_position().get.return_value = 1000
        self.playback1.reset_mock()
        self.backend1.playback = self.playback1

        self.backend2 = mock.Mock()
        self.backend2.uri_schemes.get.return_value = ['dummy2']
        self.playback2 = mock.Mock(spec=backend.PlaybackProvider)
        self.playback2.get_time_position().get.return_value = 2000
        self.playback2.reset_mock()
        self.backend2.playback = self.playback2

        # A backend without the optional playback provider
        self.backend3 = mock.Mock()
        self.backend3.uri_schemes.get.return_value = ['dummy3']
        self.backend3.has_playback().get.return_value = False

        self.tracks = [
            Track(uri='dummy1:a', length=40000),
            Track(uri='dummy2:a', length=40000),
            Track(uri='dummy3:a', length=40000),  # Unplayable
            Track(uri='dummy1:b', length=40000),
        ]

        self.core = core.Core(audio=None, backends=[
            self.backend1, self.backend2, self.backend3])
        self.core.tracklist.add(self.tracks)

        self.tl_tracks = self.core.tracklist.tl_tracks
        self.unplayable_tl_track = self.tl_tracks[2]

    # TODO Test get_current_tl_track

    # TODO Test get_current_track

    # TODO Test state

    def test_play_selects_dummy1_backend(self):
        self.core.playback.play(self.tl_tracks[0])

        self.playback1.play.assert_called_once_with(self.tracks[0])
        self.assertFalse(self.playback2.play.called)

    def test_play_selects_dummy2_backend(self):
        self.core.playback.play(self.tl_tracks[1])

        self.assertFalse(self.playback1.play.called)
        self.playback2.play.assert_called_once_with(self.tracks[1])

    def test_play_skips_to_next_on_unplayable_track(self):
        self.core.playback.play(self.unplayable_tl_track)

        self.playback1.play.assert_called_once_with(self.tracks[3])
        self.assertFalse(self.playback2.play.called)

        self.assertEqual(
            self.core.playback.current_tl_track, self.tl_tracks[3])

    @mock.patch(
        'mopidy.core.playback.listener.CoreListener', spec=core.CoreListener)
    def test_play_when_stopped_emits_events(self, listener_mock):
        self.core.playback.play(self.tl_tracks[0])

        self.assertListEqual(
            listener_mock.send.mock_calls,
            [
                mock.call(
                    'playback_state_changed',
                    old_state='stopped', new_state='playing'),
                mock.call(
                    'track_playback_started', tl_track=self.tl_tracks[0]),
            ])

    @mock.patch(
        'mopidy.core.playback.listener.CoreListener', spec=core.CoreListener)
    def test_play_when_playing_emits_events(self, listener_mock):
        self.core.playback.play(self.tl_tracks[0])
        listener_mock.reset_mock()

        self.core.playback.play(self.tl_tracks[3])

        self.assertListEqual(
            listener_mock.send.mock_calls,
            [
                mock.call(
                    'playback_state_changed',
                    old_state='playing', new_state='stopped'),
                mock.call(
                    'track_playback_ended',
                    tl_track=self.tl_tracks[0], time_position=1000),
                mock.call(
                    'playback_state_changed',
                    old_state='stopped', new_state='playing'),
                mock.call(
                    'track_playback_started', tl_track=self.tl_tracks[3]),
            ])

    def test_pause_selects_dummy1_backend(self):
        self.core.playback.play(self.tl_tracks[0])
        self.core.playback.pause()

        self.playback1.pause.assert_called_once_with()
        self.assertFalse(self.playback2.pause.called)

    def test_pause_selects_dummy2_backend(self):
        self.core.playback.play(self.tl_tracks[1])
        self.core.playback.pause()

        self.assertFalse(self.playback1.pause.called)
        self.playback2.pause.assert_called_once_with()

    def test_pause_changes_state_even_if_track_is_unplayable(self):
        self.core.playback.current_tl_track = self.unplayable_tl_track
        self.core.playback.pause()

        self.assertEqual(self.core.playback.state, core.PlaybackState.PAUSED)
        self.assertFalse(self.playback1.pause.called)
        self.assertFalse(self.playback2.pause.called)

    @mock.patch(
        'mopidy.core.playback.listener.CoreListener', spec=core.CoreListener)
    def test_pause_emits_events(self, listener_mock):
        self.core.playback.play(self.tl_tracks[0])
        listener_mock.reset_mock()

        self.core.playback.pause()

        self.assertListEqual(
            listener_mock.send.mock_calls,
            [
                mock.call(
                    'playback_state_changed',
                    old_state='playing', new_state='paused'),
                mock.call(
                    'track_playback_paused',
                    tl_track=self.tl_tracks[0], time_position=1000),
            ])

    def test_resume_selects_dummy1_backend(self):
        self.core.playback.play(self.tl_tracks[0])
        self.core.playback.pause()
        self.core.playback.resume()

        self.playback1.resume.assert_called_once_with()
        self.assertFalse(self.playback2.resume.called)

    def test_resume_selects_dummy2_backend(self):
        self.core.playback.play(self.tl_tracks[1])
        self.core.playback.pause()
        self.core.playback.resume()

        self.assertFalse(self.playback1.resume.called)
        self.playback2.resume.assert_called_once_with()

    def test_resume_does_nothing_if_track_is_unplayable(self):
        self.core.playback.current_tl_track = self.unplayable_tl_track
        self.core.playback.state = core.PlaybackState.PAUSED
        self.core.playback.resume()

        self.assertEqual(self.core.playback.state, core.PlaybackState.PAUSED)
        self.assertFalse(self.playback1.resume.called)
        self.assertFalse(self.playback2.resume.called)

    @mock.patch(
        'mopidy.core.playback.listener.CoreListener', spec=core.CoreListener)
    def test_resume_emits_events(self, listener_mock):
        self.core.playback.play(self.tl_tracks[0])
        self.core.playback.pause()
        listener_mock.reset_mock()

        self.core.playback.resume()

        self.assertListEqual(
            listener_mock.send.mock_calls,
            [
                mock.call(
                    'playback_state_changed',
                    old_state='paused', new_state='playing'),
                mock.call(
                    'track_playback_resumed',
                    tl_track=self.tl_tracks[0], time_position=1000),
            ])

    def test_stop_selects_dummy1_backend(self):
        self.core.playback.play(self.tl_tracks[0])
        self.core.playback.stop()

        self.playback1.stop.assert_called_once_with()
        self.assertFalse(self.playback2.stop.called)

    def test_stop_selects_dummy2_backend(self):
        self.core.playback.play(self.tl_tracks[1])
        self.core.playback.stop()

        self.assertFalse(self.playback1.stop.called)
        self.playback2.stop.assert_called_once_with()

    def test_stop_changes_state_even_if_track_is_unplayable(self):
        self.core.playback.current_tl_track = self.unplayable_tl_track
        self.core.playback.state = core.PlaybackState.PAUSED
        self.core.playback.stop()

        self.assertEqual(self.core.playback.state, core.PlaybackState.STOPPED)
        self.assertFalse(self.playback1.stop.called)
        self.assertFalse(self.playback2.stop.called)

    @mock.patch(
        'mopidy.core.playback.listener.CoreListener', spec=core.CoreListener)
    def test_stop_emits_events(self, listener_mock):
        self.core.playback.play(self.tl_tracks[0])
        listener_mock.reset_mock()

        self.core.playback.stop()

        self.assertListEqual(
            listener_mock.send.mock_calls,
            [
                mock.call(
                    'playback_state_changed',
                    old_state='playing', new_state='stopped'),
                mock.call(
                    'track_playback_ended',
                    tl_track=self.tl_tracks[0], time_position=1000),
            ])

    # TODO Test next() more

    @mock.patch(
        'mopidy.core.playback.listener.CoreListener', spec=core.CoreListener)
    def test_next_emits_events(self, listener_mock):
        self.core.playback.play(self.tl_tracks[0])
        listener_mock.reset_mock()

        self.core.playback.next()

        self.assertListEqual(
            listener_mock.send.mock_calls,
            [
                mock.call(
                    'playback_state_changed',
                    old_state='playing', new_state='stopped'),
                mock.call(
                    'track_playback_ended',
                    tl_track=self.tl_tracks[0], time_position=mock.ANY),
                mock.call(
                    'playback_state_changed',
                    old_state='stopped', new_state='playing'),
                mock.call(
                    'track_playback_started', tl_track=self.tl_tracks[1]),
            ])

    # TODO Test previous() more

    @mock.patch(
        'mopidy.core.playback.listener.CoreListener', spec=core.CoreListener)
    def test_previous_emits_events(self, listener_mock):
        self.core.playback.play(self.tl_tracks[1])
        listener_mock.reset_mock()

        self.core.playback.previous()

        self.assertListEqual(
            listener_mock.send.mock_calls,
            [
                mock.call(
                    'playback_state_changed',
                    old_state='playing', new_state='stopped'),
                mock.call(
                    'track_playback_ended',
                    tl_track=self.tl_tracks[1], time_position=mock.ANY),
                mock.call(
                    'playback_state_changed',
                    old_state='stopped', new_state='playing'),
                mock.call(
                    'track_playback_started', tl_track=self.tl_tracks[0]),
            ])

    # TODO Test on_end_of_track() more

    @mock.patch(
        'mopidy.core.playback.listener.CoreListener', spec=core.CoreListener)
    def test_on_end_of_track_emits_events(self, listener_mock):
        self.core.playback.play(self.tl_tracks[0])
        listener_mock.reset_mock()

        self.core.playback.on_end_of_track()

        self.assertListEqual(
            listener_mock.send.mock_calls,
            [
                mock.call(
                    'playback_state_changed',
                    old_state='playing', new_state='stopped'),
                mock.call(
                    'track_playback_ended',
                    tl_track=self.tl_tracks[0], time_position=mock.ANY),
                mock.call(
                    'playback_state_changed',
                    old_state='stopped', new_state='playing'),
                mock.call(
                    'track_playback_started', tl_track=self.tl_tracks[1]),
            ])

    def test_seek_selects_dummy1_backend(self):
        self.core.playback.play(self.tl_tracks[0])
        self.core.playback.seek(10000)

        self.playback1.seek.assert_called_once_with(10000)
        self.assertFalse(self.playback2.seek.called)

    def test_seek_selects_dummy2_backend(self):
        self.core.playback.play(self.tl_tracks[1])
        self.core.playback.seek(10000)

        self.assertFalse(self.playback1.seek.called)
        self.playback2.seek.assert_called_once_with(10000)

    def test_seek_fails_for_unplayable_track(self):
        self.core.playback.current_tl_track = self.unplayable_tl_track
        self.core.playback.state = core.PlaybackState.PLAYING
        success = self.core.playback.seek(1000)

        self.assertFalse(success)
        self.assertFalse(self.playback1.seek.called)
        self.assertFalse(self.playback2.seek.called)

    @mock.patch(
        'mopidy.core.playback.listener.CoreListener', spec=core.CoreListener)
    def test_seek_emits_seeked_event(self, listener_mock):
        self.core.playback.play(self.tl_tracks[0])
        listener_mock.reset_mock()

        self.core.playback.seek(1000)

        listener_mock.send.assert_called_once_with(
            'seeked', time_position=1000)

    def test_time_position_selects_dummy1_backend(self):
        self.core.playback.play(self.tl_tracks[0])
        self.core.playback.seek(10000)
        self.core.playback.time_position

        self.playback1.get_time_position.assert_called_once_with()
        self.assertFalse(self.playback2.get_time_position.called)

    def test_time_position_selects_dummy2_backend(self):
        self.core.playback.play(self.tl_tracks[1])
        self.core.playback.seek(10000)
        self.core.playback.time_position

        self.assertFalse(self.playback1.get_time_position.called)
        self.playback2.get_time_position.assert_called_once_with()

    def test_time_position_returns_0_if_track_is_unplayable(self):
        self.core.playback.current_tl_track = self.unplayable_tl_track

        result = self.core.playback.time_position

        self.assertEqual(result, 0)
        self.assertFalse(self.playback1.get_time_position.called)
        self.assertFalse(self.playback2.get_time_position.called)

    # TODO Test on_tracklist_change

    # TODO Test volume

    @mock.patch(
        'mopidy.core.playback.listener.CoreListener', spec=core.CoreListener)
    def test_set_volume_emits_volume_changed_event(self, listener_mock):
        self.core.playback.set_volume(10)
        listener_mock.reset_mock()

        self.core.playback.set_volume(20)

        listener_mock.send.assert_called_once_with('volume_changed', volume=20)

    def test_mute(self):
        self.assertEqual(self.core.playback.mute, False)

        self.core.playback.mute = True

        self.assertEqual(self.core.playback.mute, True)

########NEW FILE########
__FILENAME__ = test_playlists
from __future__ import unicode_literals

import unittest

import mock

from mopidy import backend, core
from mopidy.models import Playlist, Track


class PlaylistsTest(unittest.TestCase):
    def setUp(self):
        self.backend1 = mock.Mock()
        self.backend1.uri_schemes.get.return_value = ['dummy1']
        self.sp1 = mock.Mock(spec=backend.PlaylistsProvider)
        self.backend1.playlists = self.sp1

        self.backend2 = mock.Mock()
        self.backend2.uri_schemes.get.return_value = ['dummy2']
        self.sp2 = mock.Mock(spec=backend.PlaylistsProvider)
        self.backend2.playlists = self.sp2

        # A backend without the optional playlists provider
        self.backend3 = mock.Mock()
        self.backend3.uri_schemes.get.return_value = ['dummy3']
        self.backend3.has_playlists().get.return_value = False
        self.backend3.playlists = None

        self.pl1a = Playlist(name='A', tracks=[Track(uri='dummy1:a')])
        self.pl1b = Playlist(name='B', tracks=[Track(uri='dummy1:b')])
        self.sp1.playlists.get.return_value = [self.pl1a, self.pl1b]

        self.pl2a = Playlist(name='A', tracks=[Track(uri='dummy2:a')])
        self.pl2b = Playlist(name='B', tracks=[Track(uri='dummy2:b')])
        self.sp2.playlists.get.return_value = [self.pl2a, self.pl2b]

        self.core = core.Core(audio=None, backends=[
            self.backend3, self.backend1, self.backend2])

    def test_get_playlists_combines_result_from_backends(self):
        result = self.core.playlists.playlists

        self.assertIn(self.pl1a, result)
        self.assertIn(self.pl1b, result)
        self.assertIn(self.pl2a, result)
        self.assertIn(self.pl2b, result)

    def test_get_playlists_includes_tracks_by_default(self):
        result = self.core.playlists.get_playlists()

        self.assertEqual(result[0].name, 'A')
        self.assertEqual(len(result[0].tracks), 1)
        self.assertEqual(result[1].name, 'B')
        self.assertEqual(len(result[1].tracks), 1)

    def test_get_playlist_can_strip_tracks_from_returned_playlists(self):
        result = self.core.playlists.get_playlists(include_tracks=False)

        self.assertEqual(result[0].name, 'A')
        self.assertEqual(len(result[0].tracks), 0)
        self.assertEqual(result[1].name, 'B')
        self.assertEqual(len(result[1].tracks), 0)

    def test_create_without_uri_scheme_uses_first_backend(self):
        playlist = Playlist()
        self.sp1.create().get.return_value = playlist
        self.sp1.reset_mock()

        result = self.core.playlists.create('foo')

        self.assertEqual(playlist, result)
        self.sp1.create.assert_called_once_with('foo')
        self.assertFalse(self.sp2.create.called)

    def test_create_with_uri_scheme_selects_the_matching_backend(self):
        playlist = Playlist()
        self.sp2.create().get.return_value = playlist
        self.sp2.reset_mock()

        result = self.core.playlists.create('foo', uri_scheme='dummy2')

        self.assertEqual(playlist, result)
        self.assertFalse(self.sp1.create.called)
        self.sp2.create.assert_called_once_with('foo')

    def test_create_with_unsupported_uri_scheme_uses_first_backend(self):
        playlist = Playlist()
        self.sp1.create().get.return_value = playlist
        self.sp1.reset_mock()

        result = self.core.playlists.create('foo', uri_scheme='dummy3')

        self.assertEqual(playlist, result)
        self.sp1.create.assert_called_once_with('foo')
        self.assertFalse(self.sp2.create.called)

    def test_delete_selects_the_dummy1_backend(self):
        self.core.playlists.delete('dummy1:a')

        self.sp1.delete.assert_called_once_with('dummy1:a')
        self.assertFalse(self.sp2.delete.called)

    def test_delete_selects_the_dummy2_backend(self):
        self.core.playlists.delete('dummy2:a')

        self.assertFalse(self.sp1.delete.called)
        self.sp2.delete.assert_called_once_with('dummy2:a')

    def test_delete_with_unknown_uri_scheme_does_nothing(self):
        self.core.playlists.delete('unknown:a')

        self.assertFalse(self.sp1.delete.called)
        self.assertFalse(self.sp2.delete.called)

    def test_delete_ignores_backend_without_playlist_support(self):
        self.core.playlists.delete('dummy3:a')

        self.assertFalse(self.sp1.delete.called)
        self.assertFalse(self.sp2.delete.called)

    def test_filter_returns_matching_playlists(self):
        result = self.core.playlists.filter(name='A')

        self.assertEqual(2, len(result))

    def test_filter_accepts_dict_instead_of_kwargs(self):
        result = self.core.playlists.filter({'name': 'A'})

        self.assertEqual(2, len(result))

    def test_lookup_selects_the_dummy1_backend(self):
        self.core.playlists.lookup('dummy1:a')

        self.sp1.lookup.assert_called_once_with('dummy1:a')
        self.assertFalse(self.sp2.lookup.called)

    def test_lookup_selects_the_dummy2_backend(self):
        self.core.playlists.lookup('dummy2:a')

        self.assertFalse(self.sp1.lookup.called)
        self.sp2.lookup.assert_called_once_with('dummy2:a')

    def test_lookup_track_in_backend_without_playlists_fails(self):
        result = self.core.playlists.lookup('dummy3:a')

        self.assertIsNone(result)
        self.assertFalse(self.sp1.lookup.called)
        self.assertFalse(self.sp2.lookup.called)

    def test_refresh_without_uri_scheme_refreshes_all_backends(self):
        self.core.playlists.refresh()

        self.sp1.refresh.assert_called_once_with()
        self.sp2.refresh.assert_called_once_with()

    def test_refresh_with_uri_scheme_refreshes_matching_backend(self):
        self.core.playlists.refresh(uri_scheme='dummy2')

        self.assertFalse(self.sp1.refresh.called)
        self.sp2.refresh.assert_called_once_with()

    def test_refresh_with_unknown_uri_scheme_refreshes_nothing(self):
        self.core.playlists.refresh(uri_scheme='foobar')

        self.assertFalse(self.sp1.refresh.called)
        self.assertFalse(self.sp2.refresh.called)

    def test_refresh_ignores_backend_without_playlist_support(self):
        self.core.playlists.refresh(uri_scheme='dummy3')

        self.assertFalse(self.sp1.refresh.called)
        self.assertFalse(self.sp2.refresh.called)

    def test_save_selects_the_dummy1_backend(self):
        playlist = Playlist(uri='dummy1:a')
        self.sp1.save().get.return_value = playlist
        self.sp1.reset_mock()

        result = self.core.playlists.save(playlist)

        self.assertEqual(playlist, result)
        self.sp1.save.assert_called_once_with(playlist)
        self.assertFalse(self.sp2.save.called)

    def test_save_selects_the_dummy2_backend(self):
        playlist = Playlist(uri='dummy2:a')
        self.sp2.save().get.return_value = playlist
        self.sp2.reset_mock()

        result = self.core.playlists.save(playlist)

        self.assertEqual(playlist, result)
        self.assertFalse(self.sp1.save.called)
        self.sp2.save.assert_called_once_with(playlist)

    def test_save_does_nothing_if_playlist_uri_is_unset(self):
        result = self.core.playlists.save(Playlist())

        self.assertIsNone(result)
        self.assertFalse(self.sp1.save.called)
        self.assertFalse(self.sp2.save.called)

    def test_save_does_nothing_if_playlist_uri_has_unknown_scheme(self):
        result = self.core.playlists.save(Playlist(uri='foobar:a'))

        self.assertIsNone(result)
        self.assertFalse(self.sp1.save.called)
        self.assertFalse(self.sp2.save.called)

    def test_save_ignores_backend_without_playlist_support(self):
        result = self.core.playlists.save(Playlist(uri='dummy3:a'))

        self.assertIsNone(result)
        self.assertFalse(self.sp1.save.called)
        self.assertFalse(self.sp2.save.called)

########NEW FILE########
__FILENAME__ = test_tracklist
from __future__ import unicode_literals

import unittest

import mock

from mopidy import backend, core
from mopidy.models import Track


class TracklistTest(unittest.TestCase):
    def setUp(self):
        self.tracks = [
            Track(uri='dummy1:a', name='foo'),
            Track(uri='dummy1:b', name='foo'),
            Track(uri='dummy1:c', name='bar'),
        ]

        self.backend = mock.Mock()
        self.backend.uri_schemes.get.return_value = ['dummy1']
        self.library = mock.Mock(spec=backend.LibraryProvider)
        self.backend.library = self.library

        self.core = core.Core(audio=None, backends=[self.backend])
        self.tl_tracks = self.core.tracklist.add(self.tracks)

    def test_add_by_uri_looks_up_uri_in_library(self):
        track = Track(uri='dummy1:x', name='x')
        self.library.lookup().get.return_value = [track]
        self.library.lookup.reset_mock()

        tl_tracks = self.core.tracklist.add(uri='dummy1:x')

        self.library.lookup.assert_called_once_with('dummy1:x')
        self.assertEqual(1, len(tl_tracks))
        self.assertEqual(track, tl_tracks[0].track)
        self.assertEqual(tl_tracks, self.core.tracklist.tl_tracks[-1:])

    def test_remove_removes_tl_tracks_matching_query(self):
        tl_tracks = self.core.tracklist.remove(name=['foo'])

        self.assertEqual(2, len(tl_tracks))
        self.assertListEqual(self.tl_tracks[:2], tl_tracks)

        self.assertEqual(1, self.core.tracklist.length)
        self.assertListEqual(self.tl_tracks[2:], self.core.tracklist.tl_tracks)

    def test_remove_works_with_dict_instead_of_kwargs(self):
        tl_tracks = self.core.tracklist.remove({'name': ['foo']})

        self.assertEqual(2, len(tl_tracks))
        self.assertListEqual(self.tl_tracks[:2], tl_tracks)

        self.assertEqual(1, self.core.tracklist.length)
        self.assertListEqual(self.tl_tracks[2:], self.core.tracklist.tl_tracks)

    def test_filter_returns_tl_tracks_matching_query(self):
        tl_tracks = self.core.tracklist.filter(name=['foo'])

        self.assertEqual(2, len(tl_tracks))
        self.assertListEqual(self.tl_tracks[:2], tl_tracks)

    def test_filter_works_with_dict_instead_of_kwargs(self):
        tl_tracks = self.core.tracklist.filter({'name': ['foo']})

        self.assertEqual(2, len(tl_tracks))
        self.assertListEqual(self.tl_tracks[:2], tl_tracks)

    def test_filter_fails_if_values_isnt_iterable(self):
        self.assertRaises(ValueError, self.core.tracklist.filter, tlid=3)

    def test_filter_fails_if_values_is_a_string(self):
        self.assertRaises(ValueError, self.core.tracklist.filter, uri='a')

    # TODO Extract tracklist tests from the local backend tests

########NEW FILE########
__FILENAME__ = test_events
from __future__ import unicode_literals

import json
import unittest

import mock

from mopidy.http import actor


@mock.patch('mopidy.http.handlers.WebSocketHandler.broadcast')
class HttpEventsTest(unittest.TestCase):
    def setUp(self):
        config = {
            'http': {
                'hostname': '127.0.0.1',
                'port': 6680,
                'static_dir': None,
                'zeroconf': '',
            }
        }
        self.http = actor.HttpFrontend(config=config, core=mock.Mock())

    def test_track_playback_paused_is_broadcasted(self, broadcast):
        broadcast.reset_mock()
        self.http.on_event('track_playback_paused', foo='bar')
        self.assertDictEqual(
            json.loads(str(broadcast.call_args[0][0])), {
                'event': 'track_playback_paused',
                'foo': 'bar',
            })

    def test_track_playback_resumed_is_broadcasted(self, broadcast):
        broadcast.reset_mock()
        self.http.on_event('track_playback_resumed', foo='bar')
        self.assertDictEqual(
            json.loads(str(broadcast.call_args[0][0])), {
                'event': 'track_playback_resumed',
                'foo': 'bar',
            })

########NEW FILE########
__FILENAME__ = test_handlers
from __future__ import unicode_literals

import os

import tornado.testing
import tornado.web

import mopidy
from mopidy.http import handlers


class StaticFileHandlerTest(tornado.testing.AsyncHTTPTestCase):
    def get_app(self):
        return tornado.web.Application([
            (r'/(.*)', handlers.StaticFileHandler, {
                'path': os.path.dirname(__file__),
                'default_filename': 'test_router.py'
            })
        ])

    def test_static_handler(self):
        response = self.fetch('/test_router.py', method='GET')

        self.assertEqual(
            response.headers['X-Mopidy-Version'], mopidy.__version__)
        self.assertEqual(
            response.headers['Cache-Control'], 'no-cache')

    def test_static_default_filename(self):
        response = self.fetch('/', method='GET')

        self.assertEqual(
            response.headers['X-Mopidy-Version'], mopidy.__version__)
        self.assertEqual(
            response.headers['Cache-Control'], 'no-cache')

########NEW FILE########
__FILENAME__ = test_router
from __future__ import unicode_literals

import os
import unittest

import mock

from mopidy import http
from mopidy.http import handlers


class TestRouter(http.Router):
    name = 'test'
    static_file_path = os.path.join(os.path.dirname(__file__), 'static')


class TestRouterMissingPath(http.Router):
    name = 'test'


class TestRouterMissingName(http.Router):
    static_file_path = os.path.join(os.path.dirname(__file__), 'static')


class HttpRouterTest(unittest.TestCase):
    def setUp(self):
        self.config = {
            'http': {
                'hostname': '127.0.0.1',
                'port': 6680,
                'static_dir': None,
                'zeroconf': '',
            }
        }
        self.core = mock.Mock()

    def test_keeps_reference_to_config_and_core(self):
        router = TestRouter(self.config, self.core)

        self.assertIs(router.config, self.config)
        self.assertIs(router.core, self.core)

    def test_default_request_handlers(self):
        router = TestRouter(self.config, self.core)

        (pattern, handler_class, kwargs) = router.get_request_handlers()[0]

        self.assertEqual(pattern, r'/(.*)')
        self.assertIs(handler_class, handlers.StaticFileHandler)
        self.assertEqual(
            kwargs['path'], os.path.join(os.path.dirname(__file__), 'static'))

    def test_default_router_missing_name(self):
        with self.assertRaises(ValueError):
            TestRouterMissingName(self.config, self.core)

    def test_default_router_missing_path(self):
        router = TestRouterMissingPath(self.config, self.core)

        with self.assertRaises(ValueError):
            router.get_request_handlers()

    def test_get_root_url(self):
        router = TestRouter(self.config, self.core)

        self.assertEqual('http://127.0.0.1:6680/test/', router.get_root_url())

########NEW FILE########
__FILENAME__ = test_server
from __future__ import unicode_literals

import mock

import tornado.testing
import tornado.wsgi

import mopidy
from mopidy import http
from mopidy.http import actor, handlers


class HttpServerTest(tornado.testing.AsyncHTTPTestCase):
    def get_app(self):
        config = {
            'http': {
                'hostname': '127.0.0.1',
                'port': 6680,
                'static_dir': None,
                'zeroconf': '',
            }
        }
        core = mock.Mock()
        core.get_version = mock.MagicMock(name='get_version')
        core.get_version.return_value = mopidy.__version__

        http_frontend = actor.HttpFrontend(config=config, core=core)
        http_frontend.routers = [handlers.MopidyHttpRouter]

        return tornado.web.Application(http_frontend._get_request_handlers())

    def test_root_should_return_index(self):
        response = self.fetch('/', method='GET')

        self.assertIn(
            'Static content serving',
            tornado.escape.to_unicode(response.body))
        self.assertEqual(
            response.headers['X-Mopidy-Version'], mopidy.__version__)
        self.assertEqual(response.headers['Cache-Control'], 'no-cache')

    def test_mopidy_should_return_index(self):
        response = self.fetch('/mopidy/', method='GET')

        self.assertIn(
            'Here you can see events arriving from Mopidy in real time:',
            tornado.escape.to_unicode(response.body))
        self.assertEqual(
            response.headers['X-Mopidy-Version'], mopidy.__version__)
        self.assertEqual(response.headers['Cache-Control'], 'no-cache')

    def test_should_return_js(self):
        response = self.fetch('/mopidy/mopidy.js', method='GET')

        self.assertIn(
            'function Mopidy',
            tornado.escape.to_unicode(response.body))
        self.assertEqual(
            response.headers['X-Mopidy-Version'], mopidy.__version__)
        self.assertEqual(response.headers['Cache-Control'], 'no-cache')

    def test_should_return_ws(self):
        response = self.fetch('/mopidy/ws', method='GET')

        self.assertEqual(
            'Can "Upgrade" only to "WebSocket".',
            tornado.escape.to_unicode(response.body))

    def test_should_return_ws_old(self):
        response = self.fetch('/mopidy/ws/', method='GET')

        self.assertEqual(
            'Can "Upgrade" only to "WebSocket".',
            tornado.escape.to_unicode(response.body))

    def test_should_return_rpc_error(self):
        cmd = tornado.escape.json_encode({'action': 'get_version'})

        response = self.fetch('/mopidy/rpc', method='POST', body=cmd)

        self.assertEqual(
            {'jsonrpc': '2.0', 'id': None, 'error':
                {'message': 'Invalid Request', 'code': -32600,
                 'data': '"jsonrpc" member must be included'}},
            tornado.escape.json_decode(response.body))

    def test_should_return_parse_error(self):
        cmd = '{[[[]}'

        response = self.fetch('/mopidy/rpc', method='POST', body=cmd)

        self.assertEqual(
            {'jsonrpc': '2.0', 'id': None, 'error':
                {'message': 'Parse error', 'code': -32700}},
            tornado.escape.json_decode(response.body))

    def test_should_return_mopidy_version(self):
        cmd = tornado.escape.json_encode({
            'method': 'core.get_version',
            'params': [],
            'jsonrpc': '2.0',
            'id': 1,
        })

        response = self.fetch('/mopidy/rpc', method='POST', body=cmd)

        self.assertEqual(
            {'jsonrpc': '2.0', 'id': 1, 'result': mopidy.__version__},
            tornado.escape.json_decode(response.body))

    def test_should_return_extra_headers(self):
        response = self.fetch('/mopidy/rpc', method='HEAD')

        self.assertIn('Accept', response.headers)
        self.assertIn('X-Mopidy-Version', response.headers)
        self.assertIn('Cache-Control', response.headers)
        self.assertIn('Content-Type', response.headers)


class WsgiAppRouter(http.Router):
    name = 'wsgi'

    def get_request_handlers(self):
        def wsgi_app(environ, start_response):
            status = '200 OK'
            response_headers = [('Content-type', 'text/plain')]
            start_response(status, response_headers)
            return ['Hello, world!\n']

        return [
            ('(.*)', tornado.web.FallbackHandler, {
                'fallback': tornado.wsgi.WSGIContainer(wsgi_app),
            }),
        ]


class HttpServerWithWsgiAppTest(tornado.testing.AsyncHTTPTestCase):
    def get_app(self):
        config = {
            'http': {
                'hostname': '127.0.0.1',
                'port': 6680,
                'static_dir': None,
                'zeroconf': '',
            }
        }
        core = mock.Mock()

        http_frontend = actor.HttpFrontend(config=config, core=core)
        http_frontend.routers = [WsgiAppRouter]

        return tornado.web.Application(http_frontend._get_request_handlers())

    def test_can_wrap_wsgi_apps(self):
        response = self.fetch('/wsgi', method='GET')

        self.assertEqual(200, response.code)
        self.assertIn(
            'Hello, world!', tornado.escape.to_unicode(response.body))

########NEW FILE########
__FILENAME__ = test_events
from __future__ import unicode_literals

import unittest

import mock

import pykka

from mopidy import audio, backend, core
from mopidy.local import actor

from tests import path_to_data_dir


@mock.patch.object(backend.BackendListener, 'send')
class LocalBackendEventsTest(unittest.TestCase):
    config = {
        'local': {
            'media_dir': path_to_data_dir(''),
            'data_dir': path_to_data_dir(''),
            'playlists_dir': b'',
            'library': 'json',
        }
    }

    def setUp(self):
        self.audio = audio.DummyAudio.start().proxy()
        self.backend = actor.LocalBackend.start(
            config=self.config, audio=self.audio).proxy()
        self.core = core.Core.start(backends=[self.backend]).proxy()

    def tearDown(self):
        pykka.ActorRegistry.stop_all()

    def test_playlists_refresh_sends_playlists_loaded_event(self, send):
        send.reset_mock()
        self.core.playlists.refresh().get()
        self.assertEqual(send.call_args[0][0], 'playlists_loaded')

########NEW FILE########
__FILENAME__ = test_json
from __future__ import unicode_literals

import unittest

from mopidy.local import json
from mopidy.models import Ref


class BrowseCacheTest(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        self.uris = ['local:track:foo/bar/song1',
                     'local:track:foo/bar/song2',
                     'local:track:foo/baz/song3',
                     'local:track:foo/song4',
                     'local:track:song5']
        self.cache = json._BrowseCache(self.uris)

    def test_lookup_root(self):
        expected = [Ref.directory(uri='local:directory:foo', name='foo'),
                    Ref.track(uri='local:track:song5', name='song5')]
        self.assertEqual(expected, self.cache.lookup('local:directory'))

    def test_lookup_foo(self):
        expected = [Ref.directory(uri='local:directory:foo/bar', name='bar'),
                    Ref.directory(uri='local:directory:foo/baz', name='baz'),
                    Ref.track(uri=self.uris[3], name='song4')]
        result = self.cache.lookup('local:directory:foo')
        self.assertEqual(expected, result)

    def test_lookup_foo_bar(self):
        expected = [Ref.track(uri=self.uris[0], name='song1'),
                    Ref.track(uri=self.uris[1], name='song2')]
        self.assertEqual(
            expected, self.cache.lookup('local:directory:foo/bar'))

    def test_lookup_foo_baz(self):
        result = self.cache.lookup('local:directory:foo/unknown')
        self.assertEqual([], result)

########NEW FILE########
__FILENAME__ = test_library
from __future__ import unicode_literals

import os
import shutil
import tempfile
import unittest

import pykka

from mopidy import core
from mopidy.local import actor, json
from mopidy.models import Album, Artist, Track

from tests import path_to_data_dir


# TODO: update tests to only use backend, not core. we need a seperate
# core test that does this integration test.
class LocalLibraryProviderTest(unittest.TestCase):
    artists = [
        Artist(name='artist1'),
        Artist(name='artist2'),
        Artist(name='artist3'),
        Artist(name='artist4'),
        Artist(name='artist5'),
        Artist(name='artist6'),
        Artist(),
    ]

    albums = [
        Album(name='album1', artists=[artists[0]]),
        Album(name='album2', artists=[artists[1]]),
        Album(name='album3', artists=[artists[2]]),
        Album(name='album4'),
        Album(artists=[artists[-1]]),
    ]

    tracks = [
        Track(
            uri='local:track:path1', name='track1',
            artists=[artists[0]], album=albums[0],
            date='2001-02-03', length=4000, track_no=1),
        Track(
            uri='local:track:path2', name='track2',
            artists=[artists[1]], album=albums[1],
            date='2002', length=4000, track_no=2),
        Track(
            uri='local:track:path3', name='track3',
            artists=[artists[3]], album=albums[2],
            date='2003', length=4000, track_no=3),
        Track(
            uri='local:track:path4', name='track4',
            artists=[artists[2]], album=albums[3],
            date='2004', length=60000, track_no=4,
            comment='This is a fantastic track'),
        Track(
            uri='local:track:path5', name='track5', genre='genre1',
            album=albums[3], length=4000, composers=[artists[4]]),
        Track(
            uri='local:track:path6', name='track6', genre='genre2',
            album=albums[3], length=4000, performers=[artists[5]]),
        Track(uri='local:track:nameless', album=albums[-1]),
    ]

    config = {
        'local': {
            'media_dir': path_to_data_dir(''),
            'data_dir': path_to_data_dir(''),
            'playlists_dir': b'',
            'library': 'json',
        },
    }

    def setUp(self):
        actor.LocalBackend.libraries = [json.JsonLibrary]
        self.backend = actor.LocalBackend.start(
            config=self.config, audio=None).proxy()
        self.core = core.Core(backends=[self.backend])
        self.library = self.core.library

    def tearDown(self):
        pykka.ActorRegistry.stop_all()
        actor.LocalBackend.libraries = []

    def test_refresh(self):
        self.library.refresh()

    @unittest.SkipTest
    def test_refresh_uri(self):
        pass

    def test_refresh_missing_uri(self):
        # Verifies that https://github.com/mopidy/mopidy/issues/500
        # has been fixed.

        tmpdir = tempfile.mkdtemp()
        try:
            tmplib = os.path.join(tmpdir, 'library.json.gz')
            shutil.copy(path_to_data_dir('library.json.gz'), tmplib)

            config = {'local': self.config['local'].copy()}
            config['local']['data_dir'] = tmpdir
            backend = actor.LocalBackend(config=config, audio=None)

            # Sanity check that value is in the library
            result = backend.library.lookup(self.tracks[0].uri)
            self.assertEqual(result, self.tracks[0:1])

            # Clear and refresh.
            open(tmplib, 'w').close()
            backend.library.refresh()

            # Now it should be gone.
            result = backend.library.lookup(self.tracks[0].uri)
            self.assertEqual(result, [])

        finally:
            shutil.rmtree(tmpdir)

    @unittest.SkipTest
    def test_browse(self):
        pass  # TODO

    def test_lookup(self):
        tracks = self.library.lookup(self.tracks[0].uri)
        self.assertEqual(tracks, self.tracks[0:1])

    def test_lookup_unknown_track(self):
        tracks = self.library.lookup('fake uri')
        self.assertEqual(tracks, [])

    # TODO: move to search_test module
    def test_find_exact_no_hits(self):
        result = self.library.find_exact(track_name=['unknown track'])
        self.assertEqual(list(result[0].tracks), [])

        result = self.library.find_exact(artist=['unknown artist'])
        self.assertEqual(list(result[0].tracks), [])

        result = self.library.find_exact(albumartist=['unknown albumartist'])
        self.assertEqual(list(result[0].tracks), [])

        result = self.library.find_exact(composer=['unknown composer'])
        self.assertEqual(list(result[0].tracks), [])

        result = self.library.find_exact(performer=['unknown performer'])
        self.assertEqual(list(result[0].tracks), [])

        result = self.library.find_exact(album=['unknown album'])
        self.assertEqual(list(result[0].tracks), [])

        result = self.library.find_exact(date=['1990'])
        self.assertEqual(list(result[0].tracks), [])

        result = self.library.find_exact(genre=['unknown genre'])
        self.assertEqual(list(result[0].tracks), [])

        result = self.library.find_exact(track_no=['9'])
        self.assertEqual(list(result[0].tracks), [])

        result = self.library.find_exact(track_no=['no_match'])
        self.assertEqual(list(result[0].tracks), [])

        result = self.library.find_exact(comment=['fake comment'])
        self.assertEqual(list(result[0].tracks), [])

        result = self.library.find_exact(uri=['fake uri'])
        self.assertEqual(list(result[0].tracks), [])

        result = self.library.find_exact(any=['unknown any'])
        self.assertEqual(list(result[0].tracks), [])

    def test_find_exact_uri(self):
        track_1_uri = 'local:track:path1'
        result = self.library.find_exact(uri=track_1_uri)
        self.assertEqual(list(result[0].tracks), self.tracks[:1])

        track_2_uri = 'local:track:path2'
        result = self.library.find_exact(uri=track_2_uri)
        self.assertEqual(list(result[0].tracks), self.tracks[1:2])

    def test_find_exact_track_name(self):
        result = self.library.find_exact(track_name=['track1'])
        self.assertEqual(list(result[0].tracks), self.tracks[:1])

        result = self.library.find_exact(track_name=['track2'])
        self.assertEqual(list(result[0].tracks), self.tracks[1:2])

    def test_find_exact_artist(self):
        result = self.library.find_exact(artist=['artist1'])
        self.assertEqual(list(result[0].tracks), self.tracks[:1])

        result = self.library.find_exact(artist=['artist2'])
        self.assertEqual(list(result[0].tracks), self.tracks[1:2])

        result = self.library.find_exact(artist=['artist3'])
        self.assertEqual(list(result[0].tracks), self.tracks[3:4])

    def test_find_exact_composer(self):
        result = self.library.find_exact(composer=['artist5'])
        self.assertEqual(list(result[0].tracks), self.tracks[4:5])

        result = self.library.find_exact(composer=['artist6'])
        self.assertEqual(list(result[0].tracks), [])

    def test_find_exact_performer(self):
        result = self.library.find_exact(performer=['artist6'])
        self.assertEqual(list(result[0].tracks), self.tracks[5:6])

        result = self.library.find_exact(performer=['artist5'])
        self.assertEqual(list(result[0].tracks), [])

    def test_find_exact_album(self):
        result = self.library.find_exact(album=['album1'])
        self.assertEqual(list(result[0].tracks), self.tracks[:1])

        result = self.library.find_exact(album=['album2'])
        self.assertEqual(list(result[0].tracks), self.tracks[1:2])

    def test_find_exact_albumartist(self):
        # Artist is both track artist and album artist
        result = self.library.find_exact(albumartist=['artist1'])
        self.assertEqual(list(result[0].tracks), [self.tracks[0]])

        # Artist is both track and album artist
        result = self.library.find_exact(albumartist=['artist2'])
        self.assertEqual(list(result[0].tracks), [self.tracks[1]])

        # Artist is just album artist
        result = self.library.find_exact(albumartist=['artist3'])
        self.assertEqual(list(result[0].tracks), [self.tracks[2]])

    def test_find_exact_track_no(self):
        result = self.library.find_exact(track_no=['1'])
        self.assertEqual(list(result[0].tracks), self.tracks[:1])

        result = self.library.find_exact(track_no=['2'])
        self.assertEqual(list(result[0].tracks), self.tracks[1:2])

    def test_find_exact_genre(self):
        result = self.library.find_exact(genre=['genre1'])
        self.assertEqual(list(result[0].tracks), self.tracks[4:5])

        result = self.library.find_exact(genre=['genre2'])
        self.assertEqual(list(result[0].tracks), self.tracks[5:6])

    def test_find_exact_date(self):
        result = self.library.find_exact(date=['2001'])
        self.assertEqual(list(result[0].tracks), [])

        result = self.library.find_exact(date=['2001-02-03'])
        self.assertEqual(list(result[0].tracks), self.tracks[:1])

        result = self.library.find_exact(date=['2002'])
        self.assertEqual(list(result[0].tracks), self.tracks[1:2])

    def test_find_exact_comment(self):
        result = self.library.find_exact(
            comment=['This is a fantastic track'])
        self.assertEqual(list(result[0].tracks), self.tracks[3:4])

        result = self.library.find_exact(
            comment=['This is a fantastic'])
        self.assertEqual(list(result[0].tracks), [])

    def test_find_exact_any(self):
        # Matches on track artist
        result = self.library.find_exact(any=['artist1'])
        self.assertEqual(list(result[0].tracks), self.tracks[:1])

        result = self.library.find_exact(any=['artist2'])
        self.assertEqual(list(result[0].tracks), self.tracks[1:2])

        # Matches on track name
        result = self.library.find_exact(any=['track1'])
        self.assertEqual(list(result[0].tracks), self.tracks[:1])

        result = self.library.find_exact(any=['track2'])
        self.assertEqual(list(result[0].tracks), self.tracks[1:2])

        # Matches on track album
        result = self.library.find_exact(any=['album1'])
        self.assertEqual(list(result[0].tracks), self.tracks[:1])

        # Matches on track album artists
        result = self.library.find_exact(any=['artist3'])
        self.assertEqual(len(result[0].tracks), 2)
        self.assertIn(self.tracks[2], result[0].tracks)
        self.assertIn(self.tracks[3], result[0].tracks)

        # Matches on track composer
        result = self.library.find_exact(any=['artist5'])
        self.assertEqual(list(result[0].tracks), self.tracks[4:5])

        # Matches on track performer
        result = self.library.find_exact(any=['artist6'])
        self.assertEqual(list(result[0].tracks), self.tracks[5:6])

        # Matches on track genre
        result = self.library.find_exact(any=['genre1'])
        self.assertEqual(list(result[0].tracks), self.tracks[4:5])

        result = self.library.find_exact(any=['genre2'])
        self.assertEqual(list(result[0].tracks), self.tracks[5:6])

        # Matches on track date
        result = self.library.find_exact(any=['2002'])
        self.assertEqual(list(result[0].tracks), self.tracks[1:2])

        # Matches on track comment
        result = self.library.find_exact(
            any=['This is a fantastic track'])
        self.assertEqual(list(result[0].tracks), self.tracks[3:4])

        # Matches on URI
        result = self.library.find_exact(any=['local:track:path1'])
        self.assertEqual(list(result[0].tracks), self.tracks[:1])

    def test_find_exact_wrong_type(self):
        test = lambda: self.library.find_exact(wrong=['test'])
        self.assertRaises(LookupError, test)

    def test_find_exact_with_empty_query(self):
        test = lambda: self.library.find_exact(artist=[''])
        self.assertRaises(LookupError, test)

        test = lambda: self.library.find_exact(albumartist=[''])
        self.assertRaises(LookupError, test)

        test = lambda: self.library.find_exact(track_name=[''])
        self.assertRaises(LookupError, test)

        test = lambda: self.library.find_exact(composer=[''])
        self.assertRaises(LookupError, test)

        test = lambda: self.library.find_exact(performer=[''])
        self.assertRaises(LookupError, test)

        test = lambda: self.library.find_exact(album=[''])
        self.assertRaises(LookupError, test)

        test = lambda: self.library.find_exact(track_no=[''])
        self.assertRaises(LookupError, test)

        test = lambda: self.library.find_exact(genre=[''])
        self.assertRaises(LookupError, test)

        test = lambda: self.library.find_exact(date=[''])
        self.assertRaises(LookupError, test)

        test = lambda: self.library.find_exact(comment=[''])
        self.assertRaises(LookupError, test)

        test = lambda: self.library.find_exact(any=[''])
        self.assertRaises(LookupError, test)

    def test_search_no_hits(self):
        result = self.library.search(track_name=['unknown track'])
        self.assertEqual(list(result[0].tracks), [])

        result = self.library.search(artist=['unknown artist'])
        self.assertEqual(list(result[0].tracks), [])

        result = self.library.search(albumartist=['unknown albumartist'])
        self.assertEqual(list(result[0].tracks), [])

        result = self.library.search(composer=['unknown composer'])
        self.assertEqual(list(result[0].tracks), [])

        result = self.library.search(performer=['unknown performer'])
        self.assertEqual(list(result[0].tracks), [])

        result = self.library.search(album=['unknown album'])
        self.assertEqual(list(result[0].tracks), [])

        result = self.library.search(track_no=['9'])
        self.assertEqual(list(result[0].tracks), [])

        result = self.library.search(track_no=['no_match'])
        self.assertEqual(list(result[0].tracks), [])

        result = self.library.search(genre=['unknown genre'])
        self.assertEqual(list(result[0].tracks), [])

        result = self.library.search(date=['unknown date'])
        self.assertEqual(list(result[0].tracks), [])

        result = self.library.search(comment=['unknown comment'])
        self.assertEqual(list(result[0].tracks), [])

        result = self.library.search(uri=['unknown uri'])
        self.assertEqual(list(result[0].tracks), [])

        result = self.library.search(any=['unknown anything'])
        self.assertEqual(list(result[0].tracks), [])

    def test_search_uri(self):
        result = self.library.search(uri=['TH1'])
        self.assertEqual(list(result[0].tracks), self.tracks[:1])

        result = self.library.search(uri=['TH2'])
        self.assertEqual(list(result[0].tracks), self.tracks[1:2])

    def test_search_track_name(self):
        result = self.library.search(track_name=['Rack1'])
        self.assertEqual(list(result[0].tracks), self.tracks[:1])

        result = self.library.search(track_name=['Rack2'])
        self.assertEqual(list(result[0].tracks), self.tracks[1:2])

    def test_search_artist(self):
        result = self.library.search(artist=['Tist1'])
        self.assertEqual(list(result[0].tracks), self.tracks[:1])

        result = self.library.search(artist=['Tist2'])
        self.assertEqual(list(result[0].tracks), self.tracks[1:2])

    def test_search_albumartist(self):
        # Artist is both track artist and album artist
        result = self.library.search(albumartist=['Tist1'])
        self.assertEqual(list(result[0].tracks), [self.tracks[0]])

        # Artist is both track artist and album artist
        result = self.library.search(albumartist=['Tist2'])
        self.assertEqual(list(result[0].tracks), [self.tracks[1]])

        # Artist is just album artist
        result = self.library.search(albumartist=['Tist3'])
        self.assertEqual(list(result[0].tracks), [self.tracks[2]])

    def test_search_composer(self):
        result = self.library.search(composer=['Tist5'])
        self.assertEqual(list(result[0].tracks), self.tracks[4:5])

    def test_search_performer(self):
        result = self.library.search(performer=['Tist6'])
        self.assertEqual(list(result[0].tracks), self.tracks[5:6])

    def test_search_album(self):
        result = self.library.search(album=['Bum1'])
        self.assertEqual(list(result[0].tracks), self.tracks[:1])

        result = self.library.search(album=['Bum2'])
        self.assertEqual(list(result[0].tracks), self.tracks[1:2])

    def test_search_genre(self):
        result = self.library.search(genre=['Enre1'])
        self.assertEqual(list(result[0].tracks), self.tracks[4:5])

        result = self.library.search(genre=['Enre2'])
        self.assertEqual(list(result[0].tracks), self.tracks[5:6])

    def test_search_date(self):
        result = self.library.search(date=['2001'])
        self.assertEqual(list(result[0].tracks), self.tracks[:1])

        result = self.library.search(date=['2001-02-03'])
        self.assertEqual(list(result[0].tracks), self.tracks[:1])

        result = self.library.search(date=['2001-02-04'])
        self.assertEqual(list(result[0].tracks), [])

        result = self.library.search(date=['2002'])
        self.assertEqual(list(result[0].tracks), self.tracks[1:2])

    def test_search_track_no(self):
        result = self.library.search(track_no=['1'])
        self.assertEqual(list(result[0].tracks), self.tracks[:1])

        result = self.library.search(track_no=['2'])
        self.assertEqual(list(result[0].tracks), self.tracks[1:2])

    def test_search_comment(self):
        result = self.library.search(comment=['fantastic'])
        self.assertEqual(list(result[0].tracks), self.tracks[3:4])

        result = self.library.search(comment=['antasti'])
        self.assertEqual(list(result[0].tracks), self.tracks[3:4])

    def test_search_any(self):
        # Matches on track artist
        result = self.library.search(any=['Tist1'])
        self.assertEqual(list(result[0].tracks), self.tracks[:1])

        # Matches on track composer
        result = self.library.search(any=['Tist5'])
        self.assertEqual(list(result[0].tracks), self.tracks[4:5])

        # Matches on track performer
        result = self.library.search(any=['Tist6'])
        self.assertEqual(list(result[0].tracks), self.tracks[5:6])

        # Matches on track
        result = self.library.search(any=['Rack1'])
        self.assertEqual(list(result[0].tracks), self.tracks[:1])

        result = self.library.search(any=['Rack2'])
        self.assertEqual(list(result[0].tracks), self.tracks[1:2])

        # Matches on track album
        result = self.library.search(any=['Bum1'])
        self.assertEqual(list(result[0].tracks), self.tracks[:1])

        # Matches on track album artists
        result = self.library.search(any=['Tist3'])
        self.assertEqual(len(result[0].tracks), 2)
        self.assertIn(self.tracks[2], result[0].tracks)
        self.assertIn(self.tracks[3], result[0].tracks)

        # Matches on track genre
        result = self.library.search(any=['Enre1'])
        self.assertEqual(list(result[0].tracks), self.tracks[4:5])

        result = self.library.search(any=['Enre2'])
        self.assertEqual(list(result[0].tracks), self.tracks[5:6])

        # Matches on track comment
        result = self.library.search(any=['fanta'])
        self.assertEqual(list(result[0].tracks), self.tracks[3:4])

        result = self.library.search(any=['is a fan'])
        self.assertEqual(list(result[0].tracks), self.tracks[3:4])

        # Matches on URI
        result = self.library.search(any=['TH1'])
        self.assertEqual(list(result[0].tracks), self.tracks[:1])

    def test_search_wrong_type(self):
        test = lambda: self.library.search(wrong=['test'])
        self.assertRaises(LookupError, test)

    def test_search_with_empty_query(self):
        test = lambda: self.library.search(artist=[''])
        self.assertRaises(LookupError, test)

        test = lambda: self.library.search(albumartist=[''])
        self.assertRaises(LookupError, test)

        test = lambda: self.library.search(composer=[''])
        self.assertRaises(LookupError, test)

        test = lambda: self.library.search(performer=[''])
        self.assertRaises(LookupError, test)

        test = lambda: self.library.search(track_name=[''])
        self.assertRaises(LookupError, test)

        test = lambda: self.library.search(album=[''])
        self.assertRaises(LookupError, test)

        test = lambda: self.library.search(genre=[''])
        self.assertRaises(LookupError, test)

        test = lambda: self.library.search(date=[''])
        self.assertRaises(LookupError, test)

        test = lambda: self.library.search(comment=[''])
        self.assertRaises(LookupError, test)

        test = lambda: self.library.search(uri=[''])
        self.assertRaises(LookupError, test)

        test = lambda: self.library.search(any=[''])
        self.assertRaises(LookupError, test)

########NEW FILE########
__FILENAME__ = test_playback
from __future__ import unicode_literals

import time
import unittest

import mock

import pykka

from mopidy import audio, core
from mopidy.core import PlaybackState
from mopidy.local import actor
from mopidy.models import Track

from tests import path_to_data_dir
from tests.local import generate_song, populate_tracklist


# TODO Test 'playlist repeat', e.g. repeat=1,single=0


class LocalPlaybackProviderTest(unittest.TestCase):
    config = {
        'local': {
            'media_dir': path_to_data_dir(''),
            'data_dir': path_to_data_dir(''),
            'playlists_dir': b'',
            'library': 'json',
        }
    }

    # We need four tracks so that our shuffled track tests behave nicely with
    # reversed as a fake shuffle. Ensuring that shuffled order is [4,3,2,1] and
    # normal order [1,2,3,4] which means next_track != next_track_with_random
    tracks = [
        Track(uri=generate_song(i), length=4464) for i in (1, 2, 3, 4)]

    def add_track(self, uri):
        track = Track(uri=uri, length=4464)
        self.tracklist.add([track])

    def setUp(self):
        self.audio = audio.DummyAudio.start().proxy()
        self.backend = actor.LocalBackend.start(
            config=self.config, audio=self.audio).proxy()
        self.core = core.Core(backends=[self.backend])
        self.playback = self.core.playback
        self.tracklist = self.core.tracklist

        assert len(self.tracks) >= 3, \
            'Need at least three tracks to run tests.'
        assert self.tracks[0].length >= 2000, \
            'First song needs to be at least 2000 miliseconds'

    def tearDown(self):
        pykka.ActorRegistry.stop_all()

    def test_uri_scheme(self):
        self.assertNotIn('file', self.core.uri_schemes)
        self.assertIn('local', self.core.uri_schemes)

    def test_play_mp3(self):
        self.add_track('local:track:blank.mp3')
        self.playback.play()
        self.assertEqual(self.playback.state, PlaybackState.PLAYING)

    def test_play_ogg(self):
        self.add_track('local:track:blank.ogg')
        self.playback.play()
        self.assertEqual(self.playback.state, PlaybackState.PLAYING)

    def test_play_flac(self):
        self.add_track('local:track:blank.flac')
        self.playback.play()
        self.assertEqual(self.playback.state, PlaybackState.PLAYING)

    def test_play_uri_with_non_ascii_bytes(self):
        # Regression test: If trying to do .split(u':') on a bytestring, the
        # string will be decoded from ASCII to Unicode, which will crash on
        # non-ASCII strings, like the bytestring the following URI decodes to.
        self.add_track('local:track:12%20Doin%E2%80%99%20It%20Right.flac')
        self.playback.play()
        self.assertEqual(self.playback.state, PlaybackState.PLAYING)

    def test_initial_state_is_stopped(self):
        self.assertEqual(self.playback.state, PlaybackState.STOPPED)

    def test_play_with_empty_playlist(self):
        self.assertEqual(self.playback.state, PlaybackState.STOPPED)
        self.playback.play()
        self.assertEqual(self.playback.state, PlaybackState.STOPPED)

    def test_play_with_empty_playlist_return_value(self):
        self.assertEqual(self.playback.play(), None)

    @populate_tracklist
    def test_play_state(self):
        self.assertEqual(self.playback.state, PlaybackState.STOPPED)
        self.playback.play()
        self.assertEqual(self.playback.state, PlaybackState.PLAYING)

    @populate_tracklist
    def test_play_return_value(self):
        self.assertEqual(self.playback.play(), None)

    @populate_tracklist
    def test_play_track_state(self):
        self.assertEqual(self.playback.state, PlaybackState.STOPPED)
        self.playback.play(self.tracklist.tl_tracks[-1])
        self.assertEqual(self.playback.state, PlaybackState.PLAYING)

    @populate_tracklist
    def test_play_track_return_value(self):
        self.assertEqual(self.playback.play(
            self.tracklist.tl_tracks[-1]), None)

    @populate_tracklist
    def test_play_when_playing(self):
        self.playback.play()
        track = self.playback.current_track
        self.playback.play()
        self.assertEqual(track, self.playback.current_track)

    @populate_tracklist
    def test_play_when_paused(self):
        self.playback.play()
        track = self.playback.current_track
        self.playback.pause()
        self.playback.play()
        self.assertEqual(self.playback.state, PlaybackState.PLAYING)
        self.assertEqual(track, self.playback.current_track)

    @populate_tracklist
    def test_play_when_pause_after_next(self):
        self.playback.play()
        self.playback.next()
        self.playback.next()
        track = self.playback.current_track
        self.playback.pause()
        self.playback.play()
        self.assertEqual(self.playback.state, PlaybackState.PLAYING)
        self.assertEqual(track, self.playback.current_track)

    @populate_tracklist
    def test_play_sets_current_track(self):
        self.playback.play()
        self.assertEqual(self.playback.current_track, self.tracks[0])

    @populate_tracklist
    def test_play_track_sets_current_track(self):
        self.playback.play(self.tracklist.tl_tracks[-1])
        self.assertEqual(self.playback.current_track, self.tracks[-1])

    @populate_tracklist
    def test_play_skips_to_next_track_on_failure(self):
        # If backend's play() returns False, it is a failure.
        self.backend.playback.play = lambda track: track != self.tracks[0]
        self.playback.play()
        self.assertNotEqual(self.playback.current_track, self.tracks[0])
        self.assertEqual(self.playback.current_track, self.tracks[1])

    @populate_tracklist
    def test_current_track_after_completed_playlist(self):
        self.playback.play(self.tracklist.tl_tracks[-1])
        self.playback.on_end_of_track()
        self.assertEqual(self.playback.state, PlaybackState.STOPPED)
        self.assertEqual(self.playback.current_track, None)

        self.playback.play(self.tracklist.tl_tracks[-1])
        self.playback.next()
        self.assertEqual(self.playback.state, PlaybackState.STOPPED)
        self.assertEqual(self.playback.current_track, None)

    @populate_tracklist
    def test_previous(self):
        self.playback.play()
        self.playback.next()
        self.playback.previous()
        self.assertEqual(self.playback.current_track, self.tracks[0])

    @populate_tracklist
    def test_previous_more(self):
        self.playback.play()  # At track 0
        self.playback.next()  # At track 1
        self.playback.next()  # At track 2
        self.playback.previous()  # At track 1
        self.assertEqual(self.playback.current_track, self.tracks[1])

    @populate_tracklist
    def test_previous_return_value(self):
        self.playback.play()
        self.playback.next()
        self.assertEqual(self.playback.previous(), None)

    @populate_tracklist
    def test_previous_does_not_trigger_playback(self):
        self.playback.play()
        self.playback.next()
        self.playback.stop()
        self.playback.previous()
        self.assertEqual(self.playback.state, PlaybackState.STOPPED)

    @populate_tracklist
    def test_previous_at_start_of_playlist(self):
        self.playback.previous()
        self.assertEqual(self.playback.state, PlaybackState.STOPPED)
        self.assertEqual(self.playback.current_track, None)

    def test_previous_for_empty_playlist(self):
        self.playback.previous()
        self.assertEqual(self.playback.state, PlaybackState.STOPPED)
        self.assertEqual(self.playback.current_track, None)

    @populate_tracklist
    def test_previous_skips_to_previous_track_on_failure(self):
        # If backend's play() returns False, it is a failure.
        self.backend.playback.play = lambda track: track != self.tracks[1]
        self.playback.play(self.tracklist.tl_tracks[2])
        self.assertEqual(self.playback.current_track, self.tracks[2])
        self.playback.previous()
        self.assertNotEqual(self.playback.current_track, self.tracks[1])
        self.assertEqual(self.playback.current_track, self.tracks[0])

    @populate_tracklist
    def test_next(self):
        self.playback.play()

        tl_track = self.playback.current_tl_track
        old_position = self.tracklist.index(tl_track)
        old_uri = tl_track.track.uri

        self.playback.next()

        tl_track = self.playback.current_tl_track
        self.assertEqual(
            self.tracklist.index(tl_track), old_position + 1)
        self.assertNotEqual(self.playback.current_track.uri, old_uri)

    @populate_tracklist
    def test_next_return_value(self):
        self.playback.play()
        self.assertEqual(self.playback.next(), None)

    @populate_tracklist
    def test_next_does_not_trigger_playback(self):
        self.playback.next()
        self.assertEqual(self.playback.state, PlaybackState.STOPPED)

    @populate_tracklist
    def test_next_at_end_of_playlist(self):
        self.playback.play()

        for i, track in enumerate(self.tracks):
            self.assertEqual(self.playback.state, PlaybackState.PLAYING)
            self.assertEqual(self.playback.current_track, track)
            tl_track = self.playback.current_tl_track
            self.assertEqual(self.tracklist.index(tl_track), i)

            self.playback.next()

        self.assertEqual(self.playback.state, PlaybackState.STOPPED)

    @populate_tracklist
    def test_next_until_end_of_playlist_and_play_from_start(self):
        self.playback.play()

        for _ in self.tracks:
            self.playback.next()

        self.assertEqual(self.playback.current_track, None)
        self.assertEqual(self.playback.state, PlaybackState.STOPPED)

        self.playback.play()
        self.assertEqual(self.playback.state, PlaybackState.PLAYING)
        self.assertEqual(self.playback.current_track, self.tracks[0])

    def test_next_for_empty_playlist(self):
        self.playback.next()
        self.assertEqual(self.playback.state, PlaybackState.STOPPED)

    @populate_tracklist
    def test_next_skips_to_next_track_on_failure(self):
        # If backend's play() returns False, it is a failure.
        self.backend.playback.play = lambda track: track != self.tracks[1]
        self.playback.play()
        self.assertEqual(self.playback.current_track, self.tracks[0])
        self.playback.next()
        self.assertNotEqual(self.playback.current_track, self.tracks[1])
        self.assertEqual(self.playback.current_track, self.tracks[2])

    @populate_tracklist
    def test_next_track_before_play(self):
        tl_track = self.playback.current_tl_track
        self.assertEqual(
            self.tracklist.next_track(tl_track), self.tl_tracks[0])

    @populate_tracklist
    def test_next_track_during_play(self):
        self.playback.play()
        tl_track = self.playback.current_tl_track
        self.assertEqual(
            self.tracklist.next_track(tl_track), self.tl_tracks[1])

    @populate_tracklist
    def test_next_track_after_previous(self):
        self.playback.play()
        self.playback.next()
        self.playback.previous()
        tl_track = self.playback.current_tl_track
        self.assertEqual(
            self.tracklist.next_track(tl_track), self.tl_tracks[1])

    def test_next_track_empty_playlist(self):
        tl_track = self.playback.current_tl_track
        self.assertEqual(self.tracklist.next_track(tl_track), None)

    @populate_tracklist
    def test_next_track_at_end_of_playlist(self):
        self.playback.play()
        for _ in self.tracklist.tl_tracks[1:]:
            self.playback.next()
        tl_track = self.playback.current_tl_track
        self.assertEqual(self.tracklist.next_track(tl_track), None)

    @populate_tracklist
    def test_next_track_at_end_of_playlist_with_repeat(self):
        self.tracklist.repeat = True
        self.playback.play()
        for _ in self.tracks[1:]:
            self.playback.next()
        tl_track = self.playback.current_tl_track
        self.assertEqual(
            self.tracklist.next_track(tl_track), self.tl_tracks[0])

    @populate_tracklist
    @mock.patch('random.shuffle')
    def test_next_track_with_random(self, shuffle_mock):
        shuffle_mock.side_effect = lambda tracks: tracks.reverse()

        self.tracklist.random = True
        current_tl_track = self.playback.current_tl_track
        next_tl_track = self.tracklist.next_track(current_tl_track)
        self.assertEqual(next_tl_track, self.tl_tracks[-1])

    @populate_tracklist
    def test_next_with_consume(self):
        self.tracklist.consume = True
        self.playback.play()
        self.playback.next()
        self.assertIn(self.tracks[0], self.tracklist.tracks)

    @populate_tracklist
    def test_next_with_single_and_repeat(self):
        self.tracklist.single = True
        self.tracklist.repeat = True
        self.playback.play()
        self.assertEqual(self.playback.current_track, self.tracks[0])
        self.playback.next()
        self.assertEqual(self.playback.current_track, self.tracks[1])

    @populate_tracklist
    @mock.patch('random.shuffle')
    def test_next_with_random(self, shuffle_mock):
        shuffle_mock.side_effect = lambda tracks: tracks.reverse()

        self.tracklist.random = True
        self.playback.play()
        self.assertEqual(self.playback.current_track, self.tracks[-1])
        self.playback.next()
        self.assertEqual(self.playback.current_track, self.tracks[-2])

    @populate_tracklist
    @mock.patch('random.shuffle')
    def test_next_track_with_random_after_append_playlist(self, shuffle_mock):
        shuffle_mock.side_effect = lambda tracks: tracks.reverse()

        self.tracklist.random = True
        current_tl_track = self.playback.current_tl_track

        expected_tl_track = self.tracklist.tl_tracks[-1]
        next_tl_track = self.tracklist.next_track(current_tl_track)

        # Baseline checking that first next_track is last tl track per our fake
        # shuffle.
        self.assertEqual(next_tl_track, expected_tl_track)

        self.tracklist.add(self.tracks[:1])

        old_next_tl_track = next_tl_track
        expected_tl_track = self.tracklist.tl_tracks[-1]
        next_tl_track = self.tracklist.next_track(current_tl_track)

        # Verify that first next track has changed since we added to the
        # playlist.
        self.assertEqual(next_tl_track, expected_tl_track)
        self.assertNotEqual(next_tl_track, old_next_tl_track)

    @populate_tracklist
    def test_end_of_track(self):
        self.playback.play()

        tl_track = self.playback.current_tl_track
        old_position = self.tracklist.index(tl_track)
        old_uri = tl_track.track.uri

        self.playback.on_end_of_track()

        tl_track = self.playback.current_tl_track
        self.assertEqual(
            self.tracklist.index(tl_track), old_position + 1)
        self.assertNotEqual(self.playback.current_track.uri, old_uri)

    @populate_tracklist
    def test_end_of_track_return_value(self):
        self.playback.play()
        self.assertEqual(self.playback.on_end_of_track(), None)

    @populate_tracklist
    def test_end_of_track_does_not_trigger_playback(self):
        self.playback.on_end_of_track()
        self.assertEqual(self.playback.state, PlaybackState.STOPPED)

    @populate_tracklist
    def test_end_of_track_at_end_of_playlist(self):
        self.playback.play()

        for i, track in enumerate(self.tracks):
            self.assertEqual(self.playback.state, PlaybackState.PLAYING)
            self.assertEqual(self.playback.current_track, track)
            tl_track = self.playback.current_tl_track
            self.assertEqual(self.tracklist.index(tl_track), i)

            self.playback.on_end_of_track()

        self.assertEqual(self.playback.state, PlaybackState.STOPPED)

    @populate_tracklist
    def test_end_of_track_until_end_of_playlist_and_play_from_start(self):
        self.playback.play()

        for _ in self.tracks:
            self.playback.on_end_of_track()

        self.assertEqual(self.playback.current_track, None)
        self.assertEqual(self.playback.state, PlaybackState.STOPPED)

        self.playback.play()
        self.assertEqual(self.playback.state, PlaybackState.PLAYING)
        self.assertEqual(self.playback.current_track, self.tracks[0])

    def test_end_of_track_for_empty_playlist(self):
        self.playback.on_end_of_track()
        self.assertEqual(self.playback.state, PlaybackState.STOPPED)

    @populate_tracklist
    def test_end_of_track_skips_to_next_track_on_failure(self):
        # If backend's play() returns False, it is a failure.
        self.backend.playback.play = lambda track: track != self.tracks[1]
        self.playback.play()
        self.assertEqual(self.playback.current_track, self.tracks[0])
        self.playback.on_end_of_track()
        self.assertNotEqual(self.playback.current_track, self.tracks[1])
        self.assertEqual(self.playback.current_track, self.tracks[2])

    @populate_tracklist
    def test_end_of_track_track_before_play(self):
        tl_track = self.playback.current_tl_track
        self.assertEqual(
            self.tracklist.next_track(tl_track), self.tl_tracks[0])

    @populate_tracklist
    def test_end_of_track_track_during_play(self):
        self.playback.play()
        tl_track = self.playback.current_tl_track
        self.assertEqual(
            self.tracklist.next_track(tl_track), self.tl_tracks[1])

    @populate_tracklist
    def test_end_of_track_track_after_previous(self):
        self.playback.play()
        self.playback.on_end_of_track()
        self.playback.previous()
        tl_track = self.playback.current_tl_track
        self.assertEqual(
            self.tracklist.next_track(tl_track), self.tl_tracks[1])

    def test_end_of_track_track_empty_playlist(self):
        tl_track = self.playback.current_tl_track
        self.assertEqual(self.tracklist.next_track(tl_track), None)

    @populate_tracklist
    def test_end_of_track_track_at_end_of_playlist(self):
        self.playback.play()
        for _ in self.tracklist.tl_tracks[1:]:
            self.playback.on_end_of_track()
        tl_track = self.playback.current_tl_track
        self.assertEqual(self.tracklist.next_track(tl_track), None)

    @populate_tracklist
    def test_end_of_track_track_at_end_of_playlist_with_repeat(self):
        self.tracklist.repeat = True
        self.playback.play()
        for _ in self.tracks[1:]:
            self.playback.on_end_of_track()
        tl_track = self.playback.current_tl_track
        self.assertEqual(
            self.tracklist.next_track(tl_track), self.tl_tracks[0])

    @populate_tracklist
    @mock.patch('random.shuffle')
    def test_end_of_track_track_with_random(self, shuffle_mock):
        shuffle_mock.side_effect = lambda tracks: tracks.reverse()

        self.tracklist.random = True
        tl_track = self.playback.current_tl_track
        self.assertEqual(
            self.tracklist.next_track(tl_track), self.tl_tracks[-1])

    @populate_tracklist
    def test_end_of_track_with_consume(self):
        self.tracklist.consume = True
        self.playback.play()
        self.playback.on_end_of_track()
        self.assertNotIn(self.tracks[0], self.tracklist.tracks)

    @populate_tracklist
    @mock.patch('random.shuffle')
    def test_end_of_track_with_random(self, shuffle_mock):
        shuffle_mock.side_effect = lambda tracks: tracks.reverse()

        self.tracklist.random = True
        self.playback.play()
        self.assertEqual(self.playback.current_track, self.tracks[-1])
        self.playback.on_end_of_track()
        self.assertEqual(self.playback.current_track, self.tracks[-2])

    @populate_tracklist
    @mock.patch('random.shuffle')
    def test_end_of_track_track_with_random_after_append_playlist(
            self, shuffle_mock):
        shuffle_mock.side_effect = lambda tracks: tracks.reverse()

        self.tracklist.random = True
        current_tl_track = self.playback.current_tl_track

        expected_tl_track = self.tracklist.tl_tracks[-1]
        eot_tl_track = self.tracklist.eot_track(current_tl_track)

        # Baseline checking that first eot_track is last tl track per our fake
        # shuffle.
        self.assertEqual(eot_tl_track, expected_tl_track)

        self.tracklist.add(self.tracks[:1])

        old_eot_tl_track = eot_tl_track
        expected_tl_track = self.tracklist.tl_tracks[-1]
        eot_tl_track = self.tracklist.eot_track(current_tl_track)

        # Verify that first next track has changed since we added to the
        # playlist.
        self.assertEqual(eot_tl_track, expected_tl_track)
        self.assertNotEqual(eot_tl_track, old_eot_tl_track)

    @populate_tracklist
    def test_previous_track_before_play(self):
        tl_track = self.playback.current_tl_track
        self.assertEqual(self.tracklist.previous_track(tl_track), None)

    @populate_tracklist
    def test_previous_track_after_play(self):
        self.playback.play()
        tl_track = self.playback.current_tl_track
        self.assertEqual(self.tracklist.previous_track(tl_track), None)

    @populate_tracklist
    def test_previous_track_after_next(self):
        self.playback.play()
        self.playback.next()
        tl_track = self.playback.current_tl_track
        self.assertEqual(
            self.tracklist.previous_track(tl_track), self.tl_tracks[0])

    @populate_tracklist
    def test_previous_track_after_previous(self):
        self.playback.play()  # At track 0
        self.playback.next()  # At track 1
        self.playback.next()  # At track 2
        self.playback.previous()  # At track 1
        tl_track = self.playback.current_tl_track
        self.assertEqual(
            self.tracklist.previous_track(tl_track), self.tl_tracks[0])

    def test_previous_track_empty_playlist(self):
        tl_track = self.playback.current_tl_track
        self.assertEqual(self.tracklist.previous_track(tl_track), None)

    @populate_tracklist
    def test_previous_track_with_consume(self):
        self.tracklist.consume = True
        for _ in self.tracks:
            self.playback.next()
            tl_track = self.playback.current_tl_track
            self.assertEqual(
                self.tracklist.previous_track(tl_track),
                self.playback.current_tl_track)

    @populate_tracklist
    def test_previous_track_with_random(self):
        self.tracklist.random = True
        for _ in self.tracks:
            self.playback.next()
            tl_track = self.playback.current_tl_track
            self.assertEqual(
                self.tracklist.previous_track(tl_track),
                self.playback.current_tl_track)

    @populate_tracklist
    def test_initial_current_track(self):
        self.assertEqual(self.playback.current_track, None)

    @populate_tracklist
    def test_current_track_during_play(self):
        self.playback.play()
        self.assertEqual(self.playback.current_track, self.tracks[0])

    @populate_tracklist
    def test_current_track_after_next(self):
        self.playback.play()
        self.playback.next()
        self.assertEqual(self.playback.current_track, self.tracks[1])

    @populate_tracklist
    def test_initial_tracklist_position(self):
        tl_track = self.playback.current_tl_track
        self.assertEqual(self.tracklist.index(tl_track), None)

    @populate_tracklist
    def test_tracklist_position_during_play(self):
        self.playback.play()
        tl_track = self.playback.current_tl_track
        self.assertEqual(self.tracklist.index(tl_track), 0)

    @populate_tracklist
    def test_tracklist_position_after_next(self):
        self.playback.play()
        self.playback.next()
        tl_track = self.playback.current_tl_track
        self.assertEqual(self.tracklist.index(tl_track), 1)

    @populate_tracklist
    def test_tracklist_position_at_end_of_playlist(self):
        self.playback.play(self.tracklist.tl_tracks[-1])
        self.playback.on_end_of_track()
        tl_track = self.playback.current_tl_track
        self.assertEqual(self.tracklist.index(tl_track), None)

    def test_on_tracklist_change_gets_called(self):
        callback = self.playback.on_tracklist_change

        def wrapper():
            wrapper.called = True
            return callback()
        wrapper.called = False

        self.playback.on_tracklist_change = wrapper
        self.tracklist.add([Track()])

        self.assert_(wrapper.called)

    @unittest.SkipTest  # Blocks for 10ms
    @populate_tracklist
    def test_end_of_track_callback_gets_called(self):
        self.playback.play()
        result = self.playback.seek(self.tracks[0].length - 10)
        self.assertTrue(result, 'Seek failed')
        message = self.core_queue.get(True, 1)
        self.assertEqual('end_of_track', message['command'])

    @populate_tracklist
    def test_on_tracklist_change_when_playing(self):
        self.playback.play()
        current_track = self.playback.current_track
        self.tracklist.add([self.tracks[2]])
        self.assertEqual(self.playback.state, PlaybackState.PLAYING)
        self.assertEqual(self.playback.current_track, current_track)

    @populate_tracklist
    def test_on_tracklist_change_when_stopped(self):
        self.tracklist.add([self.tracks[2]])
        self.assertEqual(self.playback.state, PlaybackState.STOPPED)
        self.assertEqual(self.playback.current_track, None)

    @populate_tracklist
    def test_on_tracklist_change_when_paused(self):
        self.playback.play()
        self.playback.pause()
        current_track = self.playback.current_track
        self.tracklist.add([self.tracks[2]])
        self.assertEqual(self.playback.state, PlaybackState.PAUSED)
        self.assertEqual(self.playback.current_track, current_track)

    @populate_tracklist
    def test_pause_when_stopped(self):
        self.playback.pause()
        self.assertEqual(self.playback.state, PlaybackState.PAUSED)

    @populate_tracklist
    def test_pause_when_playing(self):
        self.playback.play()
        self.playback.pause()
        self.assertEqual(self.playback.state, PlaybackState.PAUSED)

    @populate_tracklist
    def test_pause_when_paused(self):
        self.playback.play()
        self.playback.pause()
        self.playback.pause()
        self.assertEqual(self.playback.state, PlaybackState.PAUSED)

    @populate_tracklist
    def test_pause_return_value(self):
        self.playback.play()
        self.assertEqual(self.playback.pause(), None)

    @populate_tracklist
    def test_resume_when_stopped(self):
        self.playback.resume()
        self.assertEqual(self.playback.state, PlaybackState.STOPPED)

    @populate_tracklist
    def test_resume_when_playing(self):
        self.playback.play()
        self.playback.resume()
        self.assertEqual(self.playback.state, PlaybackState.PLAYING)

    @populate_tracklist
    def test_resume_when_paused(self):
        self.playback.play()
        self.playback.pause()
        self.playback.resume()
        self.assertEqual(self.playback.state, PlaybackState.PLAYING)

    @populate_tracklist
    def test_resume_return_value(self):
        self.playback.play()
        self.playback.pause()
        self.assertEqual(self.playback.resume(), None)

    @unittest.SkipTest  # Uses sleep and might not work with LocalBackend
    @populate_tracklist
    def test_resume_continues_from_right_position(self):
        self.playback.play()
        time.sleep(0.2)
        self.playback.pause()
        self.playback.resume()
        self.assertNotEqual(self.playback.time_position, 0)

    @populate_tracklist
    def test_seek_when_stopped(self):
        result = self.playback.seek(1000)
        self.assert_(result, 'Seek return value was %s' % result)

    @populate_tracklist
    def test_seek_when_stopped_updates_position(self):
        self.playback.seek(1000)
        position = self.playback.time_position
        self.assertGreaterEqual(position, 990)

    def test_seek_on_empty_playlist(self):
        self.assertFalse(self.playback.seek(0))

    def test_seek_on_empty_playlist_updates_position(self):
        self.playback.seek(0)
        self.assertEqual(self.playback.state, PlaybackState.STOPPED)

    @populate_tracklist
    def test_seek_when_stopped_triggers_play(self):
        self.playback.seek(0)
        self.assertEqual(self.playback.state, PlaybackState.PLAYING)

    @populate_tracklist
    def test_seek_when_playing(self):
        self.playback.play()
        result = self.playback.seek(self.tracks[0].length - 1000)
        self.assert_(result, 'Seek return value was %s' % result)

    @populate_tracklist
    def test_seek_when_playing_updates_position(self):
        length = self.tracklist.tracks[0].length
        self.playback.play()
        self.playback.seek(length - 1000)
        position = self.playback.time_position
        self.assertGreaterEqual(position, length - 1010)

    @populate_tracklist
    def test_seek_when_paused(self):
        self.playback.play()
        self.playback.pause()
        result = self.playback.seek(self.tracks[0].length - 1000)
        self.assert_(result, 'Seek return value was %s' % result)

    @populate_tracklist
    def test_seek_when_paused_updates_position(self):
        length = self.tracklist.tracks[0].length
        self.playback.play()
        self.playback.pause()
        self.playback.seek(length - 1000)
        position = self.playback.time_position
        self.assertGreaterEqual(position, length - 1010)

    @populate_tracklist
    def test_seek_when_paused_triggers_play(self):
        self.playback.play()
        self.playback.pause()
        self.playback.seek(0)
        self.assertEqual(self.playback.state, PlaybackState.PLAYING)

    @unittest.SkipTest
    @populate_tracklist
    def test_seek_beyond_end_of_song(self):
        # FIXME need to decide return value
        self.playback.play()
        result = self.playback.seek(self.tracks[0].length * 100)
        self.assert_(not result, 'Seek return value was %s' % result)

    @populate_tracklist
    def test_seek_beyond_end_of_song_jumps_to_next_song(self):
        self.playback.play()
        self.playback.seek(self.tracks[0].length * 100)
        self.assertEqual(self.playback.current_track, self.tracks[1])

    @populate_tracklist
    def test_seek_beyond_end_of_song_for_last_track(self):
        self.playback.play(self.tracklist.tl_tracks[-1])
        self.playback.seek(self.tracklist.tracks[-1].length * 100)
        self.assertEqual(self.playback.state, PlaybackState.STOPPED)

    @unittest.SkipTest
    @populate_tracklist
    def test_seek_beyond_start_of_song(self):
        # FIXME need to decide return value
        self.playback.play()
        result = self.playback.seek(-1000)
        self.assert_(not result, 'Seek return value was %s' % result)

    @populate_tracklist
    def test_seek_beyond_start_of_song_update_postion(self):
        self.playback.play()
        self.playback.seek(-1000)
        position = self.playback.time_position
        self.assertGreaterEqual(position, 0)
        self.assertEqual(self.playback.state, PlaybackState.PLAYING)

    @populate_tracklist
    def test_stop_when_stopped(self):
        self.playback.stop()
        self.assertEqual(self.playback.state, PlaybackState.STOPPED)

    @populate_tracklist
    def test_stop_when_playing(self):
        self.playback.play()
        self.playback.stop()
        self.assertEqual(self.playback.state, PlaybackState.STOPPED)

    @populate_tracklist
    def test_stop_when_paused(self):
        self.playback.play()
        self.playback.pause()
        self.playback.stop()
        self.assertEqual(self.playback.state, PlaybackState.STOPPED)

    def test_stop_return_value(self):
        self.playback.play()
        self.assertEqual(self.playback.stop(), None)

    def test_time_position_when_stopped(self):
        future = mock.Mock()
        future.get = mock.Mock(return_value=0)
        self.audio.get_position = mock.Mock(return_value=future)

        self.assertEqual(self.playback.time_position, 0)

    @populate_tracklist
    def test_time_position_when_stopped_with_playlist(self):
        future = mock.Mock()
        future.get = mock.Mock(return_value=0)
        self.audio.get_position = mock.Mock(return_value=future)

        self.assertEqual(self.playback.time_position, 0)

    @unittest.SkipTest  # Uses sleep and does might not work with LocalBackend
    @populate_tracklist
    def test_time_position_when_playing(self):
        self.playback.play()
        first = self.playback.time_position
        time.sleep(1)
        second = self.playback.time_position
        self.assertGreater(second, first)

    @unittest.SkipTest  # Uses sleep
    @populate_tracklist
    def test_time_position_when_paused(self):
        self.playback.play()
        time.sleep(0.2)
        self.playback.pause()
        time.sleep(0.2)
        first = self.playback.time_position
        second = self.playback.time_position
        self.assertEqual(first, second)

    @populate_tracklist
    def test_play_with_consume(self):
        self.tracklist.consume = True
        self.playback.play()
        self.assertEqual(self.playback.current_track, self.tracks[0])

    @populate_tracklist
    def test_playlist_is_empty_after_all_tracks_are_played_with_consume(self):
        self.tracklist.consume = True
        self.playback.play()
        for _ in range(len(self.tracklist.tracks)):
            self.playback.on_end_of_track()
        self.assertEqual(len(self.tracklist.tracks), 0)

    @populate_tracklist
    @mock.patch('random.shuffle')
    def test_play_with_random(self, shuffle_mock):
        shuffle_mock.side_effect = lambda tracks: tracks.reverse()

        self.tracklist.random = True
        self.playback.play()
        self.assertEqual(self.playback.current_track, self.tracks[-1])

    @populate_tracklist
    @mock.patch('random.shuffle')
    def test_previous_with_random(self, shuffle_mock):
        shuffle_mock.side_effect = lambda tracks: tracks.reverse()

        self.tracklist.random = True
        self.playback.play()
        self.playback.next()
        current_track = self.playback.current_track
        self.playback.previous()
        self.assertEqual(self.playback.current_track, current_track)

    @populate_tracklist
    def test_end_of_song_starts_next_track(self):
        self.playback.play()
        self.playback.on_end_of_track()
        self.assertEqual(self.playback.current_track, self.tracks[1])

    @populate_tracklist
    def test_end_of_song_with_single_and_repeat_starts_same(self):
        self.tracklist.single = True
        self.tracklist.repeat = True
        self.playback.play()
        self.assertEqual(self.playback.current_track, self.tracks[0])
        self.playback.on_end_of_track()
        self.assertEqual(self.playback.current_track, self.tracks[0])

    @populate_tracklist
    def test_end_of_song_with_single_random_and_repeat_starts_same(self):
        self.tracklist.single = True
        self.tracklist.repeat = True
        self.tracklist.random = True
        self.playback.play()
        current_track = self.playback.current_track
        self.playback.on_end_of_track()
        self.assertEqual(self.playback.current_track, current_track)

    @populate_tracklist
    def test_end_of_song_with_single_stops(self):
        self.tracklist.single = True
        self.playback.play()
        self.assertEqual(self.playback.current_track, self.tracks[0])
        self.playback.on_end_of_track()
        self.assertEqual(self.playback.current_track, None)
        self.assertEqual(self.playback.state, PlaybackState.STOPPED)

    @populate_tracklist
    def test_end_of_song_with_single_and_random_stops(self):
        self.tracklist.single = True
        self.tracklist.random = True
        self.playback.play()
        self.playback.on_end_of_track()
        self.assertEqual(self.playback.current_track, None)
        self.assertEqual(self.playback.state, PlaybackState.STOPPED)

    @populate_tracklist
    def test_end_of_playlist_stops(self):
        self.playback.play(self.tracklist.tl_tracks[-1])
        self.playback.on_end_of_track()
        self.assertEqual(self.playback.state, PlaybackState.STOPPED)

    def test_repeat_off_by_default(self):
        self.assertEqual(self.tracklist.repeat, False)

    def test_random_off_by_default(self):
        self.assertEqual(self.tracklist.random, False)

    def test_consume_off_by_default(self):
        self.assertEqual(self.tracklist.consume, False)

    @populate_tracklist
    def test_random_until_end_of_playlist(self):
        self.tracklist.random = True
        self.playback.play()
        for _ in self.tracks[1:]:
            self.playback.next()
        tl_track = self.playback.current_tl_track
        self.assertEqual(self.tracklist.next_track(tl_track), None)

    @populate_tracklist
    def test_random_with_eot_until_end_of_playlist(self):
        self.tracklist.random = True
        self.playback.play()
        for _ in self.tracks[1:]:
            self.playback.on_end_of_track()
        tl_track = self.playback.current_tl_track
        self.assertEqual(self.tracklist.eot_track(tl_track), None)

    @populate_tracklist
    def test_random_until_end_of_playlist_and_play_from_start(self):
        self.tracklist.random = True
        self.playback.play()
        for _ in self.tracks:
            self.playback.next()
        tl_track = self.playback.current_tl_track
        self.assertNotEqual(self.tracklist.next_track(tl_track), None)
        self.assertEqual(self.playback.state, PlaybackState.STOPPED)
        self.playback.play()
        self.assertEqual(self.playback.state, PlaybackState.PLAYING)

    @populate_tracklist
    def test_random_with_eot_until_end_of_playlist_and_play_from_start(self):
        self.tracklist.random = True
        self.playback.play()
        for _ in self.tracks:
            self.playback.on_end_of_track()
        tl_track = self.playback.current_tl_track
        self.assertNotEqual(self.tracklist.eot_track(tl_track), None)
        self.assertEqual(self.playback.state, PlaybackState.STOPPED)
        self.playback.play()
        self.assertEqual(self.playback.state, PlaybackState.PLAYING)

    @populate_tracklist
    def test_random_until_end_of_playlist_with_repeat(self):
        self.tracklist.repeat = True
        self.tracklist.random = True
        self.playback.play()
        for _ in self.tracks[1:]:
            self.playback.next()
        tl_track = self.playback.current_tl_track
        self.assertNotEqual(self.tracklist.next_track(tl_track), None)

    @populate_tracklist
    def test_played_track_during_random_not_played_again(self):
        self.tracklist.random = True
        self.playback.play()
        played = []
        for _ in self.tracks:
            self.assertNotIn(self.playback.current_track, played)
            played.append(self.playback.current_track)
            self.playback.next()

    @populate_tracklist
    @mock.patch('random.shuffle')
    def test_play_track_then_enable_random(self, shuffle_mock):
        # Covers underlying issue IssueGH17RegressionTest tests for.
        shuffle_mock.side_effect = lambda tracks: tracks.reverse()

        expected = self.tl_tracks[::-1] + [None]
        actual = []

        self.playback.play()
        self.tracklist.random = True
        while self.playback.state != PlaybackState.STOPPED:
            self.playback.next()
            actual.append(self.playback.current_tl_track)
        self.assertEqual(actual, expected)

    @populate_tracklist
    def test_playing_track_that_isnt_in_playlist(self):
        test = lambda: self.playback.play((17, Track()))
        self.assertRaises(AssertionError, test)

########NEW FILE########
__FILENAME__ = test_playlists
from __future__ import unicode_literals

import os
import shutil
import tempfile
import unittest

import pykka

from mopidy import audio, core
from mopidy.local import actor
from mopidy.models import Playlist, Track

from tests import path_to_data_dir
from tests.local import generate_song


class LocalPlaylistsProviderTest(unittest.TestCase):
    backend_class = actor.LocalBackend
    config = {
        'local': {
            'media_dir': path_to_data_dir(''),
            'data_dir': path_to_data_dir(''),
            'library': 'json',
        }
    }

    def setUp(self):
        self.config['local']['playlists_dir'] = tempfile.mkdtemp()
        self.playlists_dir = self.config['local']['playlists_dir']

        self.audio = audio.DummyAudio.start().proxy()
        self.backend = actor.LocalBackend.start(
            config=self.config, audio=self.audio).proxy()
        self.core = core.Core(backends=[self.backend])

    def tearDown(self):
        pykka.ActorRegistry.stop_all()

        if os.path.exists(self.playlists_dir):
            shutil.rmtree(self.playlists_dir)

    def test_created_playlist_is_persisted(self):
        path = os.path.join(self.playlists_dir, 'test.m3u')
        self.assertFalse(os.path.exists(path))

        self.core.playlists.create('test')
        self.assertTrue(os.path.exists(path))

    def test_create_slugifies_playlist_name(self):
        path = os.path.join(self.playlists_dir, 'test-foo-bar.m3u')
        self.assertFalse(os.path.exists(path))

        playlist = self.core.playlists.create('test FOO baR')
        self.assertEqual('test-foo-bar', playlist.name)
        self.assertTrue(os.path.exists(path))

    def test_create_slugifies_names_which_tries_to_change_directory(self):
        path = os.path.join(self.playlists_dir, 'test-foo-bar.m3u')
        self.assertFalse(os.path.exists(path))

        playlist = self.core.playlists.create('../../test FOO baR')
        self.assertEqual('test-foo-bar', playlist.name)
        self.assertTrue(os.path.exists(path))

    def test_saved_playlist_is_persisted(self):
        path1 = os.path.join(self.playlists_dir, 'test1.m3u')
        path2 = os.path.join(self.playlists_dir, 'test2-foo-bar.m3u')

        playlist = self.core.playlists.create('test1')

        self.assertTrue(os.path.exists(path1))
        self.assertFalse(os.path.exists(path2))

        playlist = playlist.copy(name='test2 FOO baR')
        playlist = self.core.playlists.save(playlist)

        self.assertEqual('test2-foo-bar', playlist.name)
        self.assertFalse(os.path.exists(path1))
        self.assertTrue(os.path.exists(path2))

    def test_deleted_playlist_is_removed(self):
        path = os.path.join(self.playlists_dir, 'test.m3u')
        self.assertFalse(os.path.exists(path))

        playlist = self.core.playlists.create('test')
        self.assertTrue(os.path.exists(path))

        self.core.playlists.delete(playlist.uri)
        self.assertFalse(os.path.exists(path))

    def test_playlist_contents_is_written_to_disk(self):
        track = Track(uri=generate_song(1))
        playlist = self.core.playlists.create('test')
        playlist_path = os.path.join(self.playlists_dir, 'test.m3u')
        playlist = playlist.copy(tracks=[track])
        playlist = self.core.playlists.save(playlist)

        with open(playlist_path) as playlist_file:
            contents = playlist_file.read()

        self.assertEqual(track.uri, contents.strip())

    def test_extended_playlist_contents_is_written_to_disk(self):
        track = Track(uri=generate_song(1), name='Test', length=60000)
        playlist = self.core.playlists.create('test')
        playlist_path = os.path.join(self.playlists_dir, 'test.m3u')
        playlist = playlist.copy(tracks=[track])
        playlist = self.core.playlists.save(playlist)

        with open(playlist_path) as playlist_file:
            contents = playlist_file.read().splitlines()

        self.assertEqual(contents, ['#EXTM3U', '#EXTINF:60,Test', track.uri])

    def test_playlists_are_loaded_at_startup(self):
        track = Track(uri='local:track:path2')
        playlist = self.core.playlists.create('test')
        playlist = playlist.copy(tracks=[track])
        playlist = self.core.playlists.save(playlist)

        backend = self.backend_class(config=self.config, audio=self.audio)

        self.assert_(backend.playlists.playlists)
        self.assertEqual(
            'local:playlist:test', backend.playlists.playlists[0].uri)
        self.assertEqual(
            playlist.name, backend.playlists.playlists[0].name)
        self.assertEqual(
            track.uri, backend.playlists.playlists[0].tracks[0].uri)

    @unittest.SkipTest
    def test_santitising_of_playlist_filenames(self):
        pass

    @unittest.SkipTest
    def test_playlist_dir_is_created(self):
        pass

    def test_create_returns_playlist_with_name_set(self):
        playlist = self.core.playlists.create('test')
        self.assertEqual(playlist.name, 'test')

    def test_create_returns_playlist_with_uri_set(self):
        playlist = self.core.playlists.create('test')
        self.assert_(playlist.uri)

    def test_create_adds_playlist_to_playlists_collection(self):
        playlist = self.core.playlists.create('test')
        self.assert_(self.core.playlists.playlists)
        self.assertIn(playlist, self.core.playlists.playlists)

    def test_playlists_empty_to_start_with(self):
        self.assert_(not self.core.playlists.playlists)

    def test_delete_non_existant_playlist(self):
        self.core.playlists.delete('file:///unknown/playlist')

    def test_delete_playlist_removes_it_from_the_collection(self):
        playlist = self.core.playlists.create('test')
        self.assertIn(playlist, self.core.playlists.playlists)

        self.core.playlists.delete(playlist.uri)

        self.assertNotIn(playlist, self.core.playlists.playlists)

    def test_filter_without_criteria(self):
        self.assertEqual(
            self.core.playlists.playlists, self.core.playlists.filter())

    def test_filter_with_wrong_criteria(self):
        self.assertEqual([], self.core.playlists.filter(name='foo'))

    def test_filter_with_right_criteria(self):
        playlist = self.core.playlists.create('test')
        playlists = self.core.playlists.filter(name='test')
        self.assertEqual([playlist], playlists)

    def test_filter_by_name_returns_single_match(self):
        playlist = Playlist(name='b')
        self.backend.playlists.playlists = [Playlist(name='a'), playlist]
        self.assertEqual([playlist], self.core.playlists.filter(name='b'))

    def test_filter_by_name_returns_multiple_matches(self):
        playlist = Playlist(name='b')
        self.backend.playlists.playlists = [
            playlist, Playlist(name='a'), Playlist(name='b')]
        playlists = self.core.playlists.filter(name='b')
        self.assertIn(playlist, playlists)
        self.assertEqual(2, len(playlists))

    def test_filter_by_name_returns_no_matches(self):
        self.backend.playlists.playlists = [
            Playlist(name='a'), Playlist(name='b')]
        self.assertEqual([], self.core.playlists.filter(name='c'))

    def test_lookup_finds_playlist_by_uri(self):
        original_playlist = self.core.playlists.create('test')

        looked_up_playlist = self.core.playlists.lookup(original_playlist.uri)

        self.assertEqual(original_playlist, looked_up_playlist)

    @unittest.SkipTest
    def test_refresh(self):
        pass

    def test_save_replaces_existing_playlist_with_updated_playlist(self):
        playlist1 = self.core.playlists.create('test1')
        self.assertIn(playlist1, self.core.playlists.playlists)

        playlist2 = playlist1.copy(name='test2')
        playlist2 = self.core.playlists.save(playlist2)
        self.assertNotIn(playlist1, self.core.playlists.playlists)
        self.assertIn(playlist2, self.core.playlists.playlists)

    def test_playlist_with_unknown_track(self):
        track = Track(uri='file:///dev/null')
        playlist = self.core.playlists.create('test')
        playlist = playlist.copy(tracks=[track])
        playlist = self.core.playlists.save(playlist)

        backend = self.backend_class(config=self.config, audio=self.audio)

        self.assert_(backend.playlists.playlists)
        self.assertEqual(
            'local:playlist:test', backend.playlists.playlists[0].uri)
        self.assertEqual(
            playlist.name, backend.playlists.playlists[0].name)
        self.assertEqual(
            track.uri, backend.playlists.playlists[0].tracks[0].uri)

########NEW FILE########
__FILENAME__ = test_tracklist
from __future__ import unicode_literals

import random
import unittest

import pykka

from mopidy import audio, core
from mopidy.core import PlaybackState
from mopidy.local import actor
from mopidy.models import Playlist, TlTrack, Track

from tests import path_to_data_dir
from tests.local import generate_song, populate_tracklist


class LocalTracklistProviderTest(unittest.TestCase):
    config = {
        'local': {
            'media_dir': path_to_data_dir(''),
            'data_dir': path_to_data_dir(''),
            'playlists_dir': b'',
            'library': 'json',
        }
    }
    tracks = [
        Track(uri=generate_song(i), length=4464) for i in range(1, 4)]

    def setUp(self):
        self.audio = audio.DummyAudio.start().proxy()
        self.backend = actor.LocalBackend.start(
            config=self.config, audio=self.audio).proxy()
        self.core = core.Core(audio=self.audio, backends=[self.backend])
        self.controller = self.core.tracklist
        self.playback = self.core.playback

        assert len(self.tracks) == 3, 'Need three tracks to run tests.'

    def tearDown(self):
        pykka.ActorRegistry.stop_all()

    def test_length(self):
        self.assertEqual(0, len(self.controller.tl_tracks))
        self.assertEqual(0, self.controller.length)
        self.controller.add(self.tracks)
        self.assertEqual(3, len(self.controller.tl_tracks))
        self.assertEqual(3, self.controller.length)

    def test_add(self):
        for track in self.tracks:
            tl_tracks = self.controller.add([track])
            self.assertEqual(track, self.controller.tracks[-1])
            self.assertEqual(tl_tracks[0], self.controller.tl_tracks[-1])
            self.assertEqual(track, tl_tracks[0].track)

    def test_add_at_position(self):
        for track in self.tracks[:-1]:
            tl_tracks = self.controller.add([track], 0)
            self.assertEqual(track, self.controller.tracks[0])
            self.assertEqual(tl_tracks[0], self.controller.tl_tracks[0])
            self.assertEqual(track, tl_tracks[0].track)

    @populate_tracklist
    def test_add_at_position_outside_of_playlist(self):
        for track in self.tracks:
            tl_tracks = self.controller.add([track], len(self.tracks) + 2)
            self.assertEqual(track, self.controller.tracks[-1])
            self.assertEqual(tl_tracks[0], self.controller.tl_tracks[-1])
            self.assertEqual(track, tl_tracks[0].track)

    @populate_tracklist
    def test_filter_by_tlid(self):
        tl_track = self.controller.tl_tracks[1]
        self.assertEqual(
            [tl_track], self.controller.filter(tlid=[tl_track.tlid]))

    @populate_tracklist
    def test_filter_by_uri(self):
        tl_track = self.controller.tl_tracks[1]
        self.assertEqual(
            [tl_track], self.controller.filter(uri=[tl_track.track.uri]))

    @populate_tracklist
    def test_filter_by_uri_returns_nothing_for_invalid_uri(self):
        self.assertEqual([], self.controller.filter(uri=['foobar']))

    def test_filter_by_uri_returns_single_match(self):
        track = Track(uri='a')
        self.controller.add([Track(uri='z'), track, Track(uri='y')])
        self.assertEqual(track, self.controller.filter(uri=['a'])[0].track)

    def test_filter_by_uri_returns_multiple_matches(self):
        track = Track(uri='a')
        self.controller.add([Track(uri='z'), track, track])
        tl_tracks = self.controller.filter(uri=['a'])
        self.assertEqual(track, tl_tracks[0].track)
        self.assertEqual(track, tl_tracks[1].track)

    def test_filter_by_uri_returns_nothing_if_no_match(self):
        self.controller.playlist = Playlist(
            tracks=[Track(uri=['z']), Track(uri=['y'])])
        self.assertEqual([], self.controller.filter(uri=['a']))

    def test_filter_by_multiple_criteria_returns_elements_matching_all(self):
        track1 = Track(uri='a', name='x')
        track2 = Track(uri='b', name='x')
        track3 = Track(uri='b', name='y')
        self.controller.add([track1, track2, track3])
        self.assertEqual(
            track1, self.controller.filter(uri=['a'], name=['x'])[0].track)
        self.assertEqual(
            track2, self.controller.filter(uri=['b'], name=['x'])[0].track)
        self.assertEqual(
            track3, self.controller.filter(uri=['b'], name=['y'])[0].track)

    def test_filter_by_criteria_that_is_not_present_in_all_elements(self):
        track1 = Track()
        track2 = Track(uri='b')
        track3 = Track()
        self.controller.add([track1, track2, track3])
        self.assertEqual(track2, self.controller.filter(uri=['b'])[0].track)

    @populate_tracklist
    def test_clear(self):
        self.controller.clear()
        self.assertEqual(len(self.controller.tracks), 0)

    def test_clear_empty_playlist(self):
        self.controller.clear()
        self.assertEqual(len(self.controller.tracks), 0)

    @populate_tracklist
    def test_clear_when_playing(self):
        self.playback.play()
        self.assertEqual(self.playback.state, PlaybackState.PLAYING)
        self.controller.clear()
        self.assertEqual(self.playback.state, PlaybackState.STOPPED)

    def test_add_appends_to_the_tracklist(self):
        self.controller.add([Track(uri='a'), Track(uri='b')])
        self.assertEqual(len(self.controller.tracks), 2)
        self.controller.add([Track(uri='c'), Track(uri='d')])
        self.assertEqual(len(self.controller.tracks), 4)
        self.assertEqual(self.controller.tracks[0].uri, 'a')
        self.assertEqual(self.controller.tracks[1].uri, 'b')
        self.assertEqual(self.controller.tracks[2].uri, 'c')
        self.assertEqual(self.controller.tracks[3].uri, 'd')

    def test_add_does_not_reset_version(self):
        version = self.controller.version
        self.controller.add([])
        self.assertEqual(self.controller.version, version)

    @populate_tracklist
    def test_add_preserves_playing_state(self):
        self.playback.play()
        track = self.playback.current_track
        self.controller.add(self.controller.tracks[1:2])
        self.assertEqual(self.playback.state, PlaybackState.PLAYING)
        self.assertEqual(self.playback.current_track, track)

    @populate_tracklist
    def test_add_preserves_stopped_state(self):
        self.controller.add(self.controller.tracks[1:2])
        self.assertEqual(self.playback.state, PlaybackState.STOPPED)
        self.assertEqual(self.playback.current_track, None)

    @populate_tracklist
    def test_add_returns_the_tl_tracks_that_was_added(self):
        tl_tracks = self.controller.add(self.controller.tracks[1:2])
        self.assertEqual(tl_tracks[0].track, self.controller.tracks[1])

    def test_index_returns_index_of_track(self):
        tl_tracks = self.controller.add(self.tracks)
        self.assertEqual(0, self.controller.index(tl_tracks[0]))
        self.assertEqual(1, self.controller.index(tl_tracks[1]))
        self.assertEqual(2, self.controller.index(tl_tracks[2]))

    def test_index_returns_none_if_item_not_found(self):
        tl_track = TlTrack(0, Track())
        self.assertEqual(self.controller.index(tl_track), None)

    @populate_tracklist
    def test_move_single(self):
        self.controller.move(0, 0, 2)

        tracks = self.controller.tracks
        self.assertEqual(tracks[2], self.tracks[0])

    @populate_tracklist
    def test_move_group(self):
        self.controller.move(0, 2, 1)

        tracks = self.controller.tracks
        self.assertEqual(tracks[1], self.tracks[0])
        self.assertEqual(tracks[2], self.tracks[1])

    @populate_tracklist
    def test_moving_track_outside_of_playlist(self):
        tracks = len(self.controller.tracks)
        test = lambda: self.controller.move(0, 0, tracks + 5)
        self.assertRaises(AssertionError, test)

    @populate_tracklist
    def test_move_group_outside_of_playlist(self):
        tracks = len(self.controller.tracks)
        test = lambda: self.controller.move(0, 2, tracks + 5)
        self.assertRaises(AssertionError, test)

    @populate_tracklist
    def test_move_group_out_of_range(self):
        tracks = len(self.controller.tracks)
        test = lambda: self.controller.move(tracks + 2, tracks + 3, 0)
        self.assertRaises(AssertionError, test)

    @populate_tracklist
    def test_move_group_invalid_group(self):
        test = lambda: self.controller.move(2, 1, 0)
        self.assertRaises(AssertionError, test)

    def test_tracks_attribute_is_immutable(self):
        tracks1 = self.controller.tracks
        tracks2 = self.controller.tracks
        self.assertNotEqual(id(tracks1), id(tracks2))

    @populate_tracklist
    def test_remove(self):
        track1 = self.controller.tracks[1]
        track2 = self.controller.tracks[2]
        version = self.controller.version
        self.controller.remove(uri=[track1.uri])
        self.assertLess(version, self.controller.version)
        self.assertNotIn(track1, self.controller.tracks)
        self.assertEqual(track2, self.controller.tracks[1])

    @populate_tracklist
    def test_removing_track_that_does_not_exist_does_nothing(self):
        self.controller.remove(uri=['/nonexistant'])

    def test_removing_from_empty_playlist_does_nothing(self):
        self.controller.remove(uri=['/nonexistant'])

    @populate_tracklist
    def test_remove_lists(self):
        track0 = self.controller.tracks[0]
        track1 = self.controller.tracks[1]
        track2 = self.controller.tracks[2]
        version = self.controller.version
        self.controller.remove(uri=[track0.uri, track2.uri])
        self.assertLess(version, self.controller.version)
        self.assertNotIn(track0, self.controller.tracks)
        self.assertNotIn(track2, self.controller.tracks)
        self.assertEqual(track1, self.controller.tracks[0])

    @populate_tracklist
    def test_shuffle(self):
        random.seed(1)
        self.controller.shuffle()

        shuffled_tracks = self.controller.tracks

        self.assertNotEqual(self.tracks, shuffled_tracks)
        self.assertEqual(set(self.tracks), set(shuffled_tracks))

    @populate_tracklist
    def test_shuffle_subset(self):
        random.seed(1)
        self.controller.shuffle(1, 3)

        shuffled_tracks = self.controller.tracks

        self.assertNotEqual(self.tracks, shuffled_tracks)
        self.assertEqual(self.tracks[0], shuffled_tracks[0])
        self.assertEqual(set(self.tracks), set(shuffled_tracks))

    @populate_tracklist
    def test_shuffle_invalid_subset(self):
        test = lambda: self.controller.shuffle(3, 1)
        self.assertRaises(AssertionError, test)

    @populate_tracklist
    def test_shuffle_superset(self):
        tracks = len(self.controller.tracks)
        test = lambda: self.controller.shuffle(1, tracks + 5)
        self.assertRaises(AssertionError, test)

    @populate_tracklist
    def test_shuffle_open_subset(self):
        random.seed(1)
        self.controller.shuffle(1)

        shuffled_tracks = self.controller.tracks

        self.assertNotEqual(self.tracks, shuffled_tracks)
        self.assertEqual(self.tracks[0], shuffled_tracks[0])
        self.assertEqual(set(self.tracks), set(shuffled_tracks))

    @populate_tracklist
    def test_slice_returns_a_subset_of_tracks(self):
        track_slice = self.controller.slice(1, 3)
        self.assertEqual(2, len(track_slice))
        self.assertEqual(self.tracks[1], track_slice[0].track)
        self.assertEqual(self.tracks[2], track_slice[1].track)

    @populate_tracklist
    def test_slice_returns_empty_list_if_indexes_outside_tracks_list(self):
        self.assertEqual(0, len(self.controller.slice(7, 8)))
        self.assertEqual(0, len(self.controller.slice(-1, 1)))

    def test_version_does_not_change_when_adding_nothing(self):
        version = self.controller.version
        self.controller.add([])
        self.assertEquals(version, self.controller.version)

    def test_version_increases_when_adding_something(self):
        version = self.controller.version
        self.controller.add([Track()])
        self.assertLess(version, self.controller.version)

########NEW FILE########
__FILENAME__ = test_translator
# encoding: utf-8

from __future__ import unicode_literals

import os
import tempfile
import unittest

from mopidy.local.translator import parse_m3u
from mopidy.models import Track
from mopidy.utils.path import path_to_uri

from tests import path_to_data_dir

data_dir = path_to_data_dir('')
song1_path = path_to_data_dir('song1.mp3')
song2_path = path_to_data_dir('song2.mp3')
encoded_path = path_to_data_dir('æøå.mp3')
song1_uri = path_to_uri(song1_path)
song2_uri = path_to_uri(song2_path)
encoded_uri = path_to_uri(encoded_path)
song1_track = Track(uri=song1_uri)
song2_track = Track(uri=song2_uri)
encoded_track = Track(uri=encoded_uri)
song1_ext_track = song1_track.copy(name='song1')
song2_ext_track = song2_track.copy(name='song2', length=60000)
encoded_ext_track = encoded_track.copy(name='æøå')


# FIXME use mock instead of tempfile.NamedTemporaryFile

class M3UToUriTest(unittest.TestCase):
    def test_empty_file(self):
        tracks = parse_m3u(path_to_data_dir('empty.m3u'), data_dir)
        self.assertEqual([], tracks)

    def test_basic_file(self):
        tracks = parse_m3u(path_to_data_dir('one.m3u'), data_dir)
        self.assertEqual([song1_track], tracks)

    def test_file_with_comment(self):
        tracks = parse_m3u(path_to_data_dir('comment.m3u'), data_dir)
        self.assertEqual([song1_track], tracks)

    def test_file_is_relative_to_correct_dir(self):
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write('song1.mp3')
        try:
            tracks = parse_m3u(tmp.name, data_dir)
            self.assertEqual([song1_track], tracks)
        finally:
            if os.path.exists(tmp.name):
                os.remove(tmp.name)

    def test_file_with_absolute_files(self):
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(song1_path)
        try:
            tracks = parse_m3u(tmp.name, data_dir)
            self.assertEqual([song1_track], tracks)
        finally:
            if os.path.exists(tmp.name):
                os.remove(tmp.name)

    def test_file_with_multiple_absolute_files(self):
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(song1_path + '\n')
            tmp.write('# comment \n')
            tmp.write(song2_path)
        try:
            tracks = parse_m3u(tmp.name, data_dir)
            self.assertEqual([song1_track, song2_track], tracks)
        finally:
            if os.path.exists(tmp.name):
                os.remove(tmp.name)

    def test_file_with_uri(self):
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(song1_uri)
        try:
            tracks = parse_m3u(tmp.name, data_dir)
            self.assertEqual([song1_track], tracks)
        finally:
            if os.path.exists(tmp.name):
                os.remove(tmp.name)

    def test_encoding_is_latin1(self):
        tracks = parse_m3u(path_to_data_dir('encoding.m3u'), data_dir)
        self.assertEqual([encoded_track], tracks)

    def test_open_missing_file(self):
        tracks = parse_m3u(path_to_data_dir('non-existant.m3u'), data_dir)
        self.assertEqual([], tracks)

    def test_empty_ext_file(self):
        tracks = parse_m3u(path_to_data_dir('empty-ext.m3u'), data_dir)
        self.assertEqual([], tracks)

    def test_basic_ext_file(self):
        tracks = parse_m3u(path_to_data_dir('one-ext.m3u'), data_dir)
        self.assertEqual([song1_ext_track], tracks)

    def test_multi_ext_file(self):
        tracks = parse_m3u(path_to_data_dir('two-ext.m3u'), data_dir)
        self.assertEqual([song1_ext_track, song2_ext_track], tracks)

    def test_ext_file_with_comment(self):
        tracks = parse_m3u(path_to_data_dir('comment-ext.m3u'), data_dir)
        self.assertEqual([song1_ext_track], tracks)

    def test_ext_encoding_is_latin1(self):
        tracks = parse_m3u(path_to_data_dir('encoding-ext.m3u'), data_dir)
        self.assertEqual([encoded_ext_track], tracks)


class URItoM3UTest(unittest.TestCase):
    pass

########NEW FILE########
__FILENAME__ = test_audio_output
from __future__ import unicode_literals

from tests.mpd import protocol


class AudioOutputHandlerTest(protocol.BaseTestCase):
    def test_enableoutput(self):
        self.core.playback.mute = False

        self.sendRequest('enableoutput "0"')

        self.assertInResponse('OK')
        self.assertEqual(self.core.playback.mute.get(), True)

    def test_enableoutput_unknown_outputid(self):
        self.sendRequest('enableoutput "7"')

        self.assertInResponse('ACK [50@0] {enableoutput} No such audio output')

    def test_disableoutput(self):
        self.core.playback.mute = True

        self.sendRequest('disableoutput "0"')

        self.assertInResponse('OK')
        self.assertEqual(self.core.playback.mute.get(), False)

    def test_disableoutput_unknown_outputid(self):
        self.sendRequest('disableoutput "7"')

        self.assertInResponse(
            'ACK [50@0] {disableoutput} No such audio output')

    def test_outputs_when_unmuted(self):
        self.core.playback.mute = False

        self.sendRequest('outputs')

        self.assertInResponse('outputid: 0')
        self.assertInResponse('outputname: Mute')
        self.assertInResponse('outputenabled: 0')
        self.assertInResponse('OK')

    def test_outputs_when_muted(self):
        self.core.playback.mute = True

        self.sendRequest('outputs')

        self.assertInResponse('outputid: 0')
        self.assertInResponse('outputname: Mute')
        self.assertInResponse('outputenabled: 1')
        self.assertInResponse('OK')

########NEW FILE########
__FILENAME__ = test_authentication
from __future__ import unicode_literals

from tests.mpd import protocol


class AuthenticationActiveTest(protocol.BaseTestCase):
    def get_config(self):
        config = super(AuthenticationActiveTest, self).get_config()
        config['mpd']['password'] = 'topsecret'
        return config

    def test_authentication_with_valid_password_is_accepted(self):
        self.sendRequest('password "topsecret"')
        self.assertTrue(self.dispatcher.authenticated)
        self.assertInResponse('OK')

    def test_authentication_with_invalid_password_is_not_accepted(self):
        self.sendRequest('password "secret"')
        self.assertFalse(self.dispatcher.authenticated)
        self.assertEqualResponse('ACK [3@0] {password} incorrect password')

    def test_anything_when_not_authenticated_should_fail(self):
        self.sendRequest('any request at all')
        self.assertFalse(self.dispatcher.authenticated)
        self.assertEqualResponse(
            u'ACK [4@0] {any} you don\'t have permission for "any"')

    def test_close_is_allowed_without_authentication(self):
        self.sendRequest('close')
        self.assertFalse(self.dispatcher.authenticated)

    def test_commands_is_allowed_without_authentication(self):
        self.sendRequest('commands')
        self.assertFalse(self.dispatcher.authenticated)
        self.assertInResponse('OK')

    def test_notcommands_is_allowed_without_authentication(self):
        self.sendRequest('notcommands')
        self.assertFalse(self.dispatcher.authenticated)
        self.assertInResponse('OK')

    def test_ping_is_allowed_without_authentication(self):
        self.sendRequest('ping')
        self.assertFalse(self.dispatcher.authenticated)
        self.assertInResponse('OK')


class AuthenticationInactiveTest(protocol.BaseTestCase):
    def test_authentication_with_anything_when_password_check_turned_off(self):
        self.sendRequest('any request at all')
        self.assertTrue(self.dispatcher.authenticated)
        self.assertEqualResponse('ACK [5@0] {} unknown command "any"')

    def test_any_password_is_not_accepted_when_password_check_turned_off(self):
        self.sendRequest('password "secret"')
        self.assertEqualResponse('ACK [3@0] {password} incorrect password')

########NEW FILE########
__FILENAME__ = test_channels
from __future__ import unicode_literals

from tests.mpd import protocol


class ChannelsHandlerTest(protocol.BaseTestCase):
    def test_subscribe(self):
        self.sendRequest('subscribe "topic"')
        self.assertEqualResponse('ACK [0@0] {subscribe} Not implemented')

    def test_unsubscribe(self):
        self.sendRequest('unsubscribe "topic"')
        self.assertEqualResponse('ACK [0@0] {unsubscribe} Not implemented')

    def test_channels(self):
        self.sendRequest('channels')
        self.assertEqualResponse('ACK [0@0] {channels} Not implemented')

    def test_readmessages(self):
        self.sendRequest('readmessages')
        self.assertEqualResponse('ACK [0@0] {readmessages} Not implemented')

    def test_sendmessage(self):
        self.sendRequest('sendmessage "topic" "a message"')
        self.assertEqualResponse('ACK [0@0] {sendmessage} Not implemented')

########NEW FILE########
__FILENAME__ = test_command_list
from __future__ import unicode_literals

from tests.mpd import protocol


class CommandListsTest(protocol.BaseTestCase):
    def test_command_list_begin(self):
        response = self.sendRequest('command_list_begin')
        self.assertEquals([], response)

    def test_command_list_end(self):
        self.sendRequest('command_list_begin')
        self.sendRequest('command_list_end')
        self.assertInResponse('OK')

    def test_command_list_end_without_start_first_is_an_unknown_command(self):
        self.sendRequest('command_list_end')
        self.assertEqualResponse(
            'ACK [5@0] {} unknown command "command_list_end"')

    def test_command_list_with_ping(self):
        self.sendRequest('command_list_begin')
        self.assertTrue(self.dispatcher.command_list_receiving)
        self.assertFalse(self.dispatcher.command_list_ok)
        self.assertEqual([], self.dispatcher.command_list)

        self.sendRequest('ping')
        self.assertIn('ping', self.dispatcher.command_list)

        self.sendRequest('command_list_end')
        self.assertInResponse('OK')
        self.assertFalse(self.dispatcher.command_list_receiving)
        self.assertFalse(self.dispatcher.command_list_ok)
        self.assertEqual([], self.dispatcher.command_list)

    def test_command_list_with_error_returns_ack_with_correct_index(self):
        self.sendRequest('command_list_begin')
        self.sendRequest('play')  # Known command
        self.sendRequest('paly')  # Unknown command
        self.sendRequest('command_list_end')
        self.assertEqualResponse('ACK [5@1] {} unknown command "paly"')

    def test_command_list_ok_begin(self):
        response = self.sendRequest('command_list_ok_begin')
        self.assertEquals([], response)

    def test_command_list_ok_with_ping(self):
        self.sendRequest('command_list_ok_begin')
        self.assertTrue(self.dispatcher.command_list_receiving)
        self.assertTrue(self.dispatcher.command_list_ok)
        self.assertEqual([], self.dispatcher.command_list)

        self.sendRequest('ping')
        self.assertIn('ping', self.dispatcher.command_list)

        self.sendRequest('command_list_end')
        self.assertInResponse('list_OK')
        self.assertInResponse('OK')
        self.assertFalse(self.dispatcher.command_list_receiving)
        self.assertFalse(self.dispatcher.command_list_ok)
        self.assertEqual([], self.dispatcher.command_list)

    # FIXME this should also include the special handling of idle within a
    # command list. That is that once a idle/noidle command is found inside a
    # commad list, the rest of the list seems to be ignored.

########NEW FILE########
__FILENAME__ = test_connection
from __future__ import unicode_literals

from mock import patch

from tests.mpd import protocol


class ConnectionHandlerTest(protocol.BaseTestCase):
    def test_close_closes_the_client_connection(self):
        with patch.object(self.session, 'close') as close_mock:
            self.sendRequest('close')
            close_mock.assertEqualResponsecalled_once_with()
        self.assertEqualResponse('OK')

    def test_empty_request(self):
        self.sendRequest('')
        self.assertEqualResponse('ACK [5@0] {} No command given')

        self.sendRequest('  ')
        self.assertEqualResponse('ACK [5@0] {} No command given')

    def test_kill(self):
        self.sendRequest('kill')
        self.assertEqualResponse(
            'ACK [4@0] {kill} you don\'t have permission for "kill"')

    def test_ping(self):
        self.sendRequest('ping')
        self.assertEqualResponse('OK')

########NEW FILE########
__FILENAME__ = test_current_playlist
from __future__ import unicode_literals

from mopidy.models import Ref, Track

from tests.mpd import protocol


class CurrentPlaylistHandlerTest(protocol.BaseTestCase):
    def test_add(self):
        needle = Track(uri='dummy://foo')
        self.backend.library.dummy_library = [
            Track(), Track(), needle, Track()]
        self.core.tracklist.add(
            [Track(), Track(), Track(), Track(), Track()])
        self.assertEqual(len(self.core.tracklist.tracks.get()), 5)

        self.sendRequest('add "dummy://foo"')
        self.assertEqual(len(self.core.tracklist.tracks.get()), 6)
        self.assertEqual(self.core.tracklist.tracks.get()[5], needle)
        self.assertEqualResponse('OK')

    def test_add_with_uri_not_found_in_library_should_ack(self):
        self.sendRequest('add "dummy://foo"')
        self.assertEqualResponse(
            'ACK [50@0] {add} directory or file not found')

    def test_add_with_empty_uri_should_not_add_anything_and_ok(self):
        self.backend.library.dummy_library = [Track(uri='dummy:/a', name='a')]
        self.backend.library.dummy_browse_result = {
            'dummy:/': [Ref.track(uri='dummy:/a', name='a')]}

        self.sendRequest('add ""')
        self.assertEqual(len(self.core.tracklist.tracks.get()), 0)
        self.assertInResponse('OK')

    def test_add_with_library_should_recurse(self):
        tracks = [Track(uri='dummy:/a', name='a'),
                  Track(uri='dummy:/foo/b', name='b')]

        self.backend.library.dummy_library = tracks
        self.backend.library.dummy_browse_result = {
            'dummy:/': [Ref.track(uri='dummy:/a', name='a'),
                        Ref.directory(uri='dummy:/foo', name='foo')],
            'dummy:/foo': [Ref.track(uri='dummy:/foo/b', name='b')]}

        self.sendRequest('add "/dummy"')
        self.assertEqual(self.core.tracklist.tracks.get(), tracks)
        self.assertInResponse('OK')

    def test_add_root_should_not_add_anything_and_ok(self):
        self.backend.library.dummy_library = [Track(uri='dummy:/a', name='a')]
        self.backend.library.dummy_browse_result = {
            'dummy:/': [Ref.track(uri='dummy:/a', name='a')]}

        self.sendRequest('add "/"')
        self.assertEqual(len(self.core.tracklist.tracks.get()), 0)
        self.assertInResponse('OK')

    def test_addid_without_songpos(self):
        needle = Track(uri='dummy://foo')
        self.backend.library.dummy_library = [
            Track(), Track(), needle, Track()]
        self.core.tracklist.add(
            [Track(), Track(), Track(), Track(), Track()])
        self.assertEqual(len(self.core.tracklist.tracks.get()), 5)

        self.sendRequest('addid "dummy://foo"')
        self.assertEqual(len(self.core.tracklist.tracks.get()), 6)
        self.assertEqual(self.core.tracklist.tracks.get()[5], needle)
        self.assertInResponse(
            'Id: %d' % self.core.tracklist.tl_tracks.get()[5].tlid)
        self.assertInResponse('OK')

    def test_addid_with_empty_uri_acks(self):
        self.sendRequest('addid ""')
        self.assertEqualResponse('ACK [50@0] {addid} No such song')

    def test_addid_with_songpos(self):
        needle = Track(uri='dummy://foo')
        self.backend.library.dummy_library = [
            Track(), Track(), needle, Track()]
        self.core.tracklist.add(
            [Track(), Track(), Track(), Track(), Track()])
        self.assertEqual(len(self.core.tracklist.tracks.get()), 5)

        self.sendRequest('addid "dummy://foo" "3"')
        self.assertEqual(len(self.core.tracklist.tracks.get()), 6)
        self.assertEqual(self.core.tracklist.tracks.get()[3], needle)
        self.assertInResponse(
            'Id: %d' % self.core.tracklist.tl_tracks.get()[3].tlid)
        self.assertInResponse('OK')

    def test_addid_with_songpos_out_of_bounds_should_ack(self):
        needle = Track(uri='dummy://foo')
        self.backend.library.dummy_library = [
            Track(), Track(), needle, Track()]
        self.core.tracklist.add(
            [Track(), Track(), Track(), Track(), Track()])
        self.assertEqual(len(self.core.tracklist.tracks.get()), 5)

        self.sendRequest('addid "dummy://foo" "6"')
        self.assertEqualResponse('ACK [2@0] {addid} Bad song index')

    def test_addid_with_uri_not_found_in_library_should_ack(self):
        self.sendRequest('addid "dummy://foo"')
        self.assertEqualResponse('ACK [50@0] {addid} No such song')

    def test_clear(self):
        self.core.tracklist.add(
            [Track(), Track(), Track(), Track(), Track()])
        self.assertEqual(len(self.core.tracklist.tracks.get()), 5)

        self.sendRequest('clear')
        self.assertEqual(len(self.core.tracklist.tracks.get()), 0)
        self.assertEqual(self.core.playback.current_track.get(), None)
        self.assertInResponse('OK')

    def test_delete_songpos(self):
        self.core.tracklist.add(
            [Track(), Track(), Track(), Track(), Track()])
        self.assertEqual(len(self.core.tracklist.tracks.get()), 5)

        self.sendRequest(
            'delete "%d"' % self.core.tracklist.tl_tracks.get()[2].tlid)
        self.assertEqual(len(self.core.tracklist.tracks.get()), 4)
        self.assertInResponse('OK')

    def test_delete_songpos_out_of_bounds(self):
        self.core.tracklist.add(
            [Track(), Track(), Track(), Track(), Track()])
        self.assertEqual(len(self.core.tracklist.tracks.get()), 5)

        self.sendRequest('delete "5"')
        self.assertEqual(len(self.core.tracklist.tracks.get()), 5)
        self.assertEqualResponse('ACK [2@0] {delete} Bad song index')

    def test_delete_open_range(self):
        self.core.tracklist.add(
            [Track(), Track(), Track(), Track(), Track()])
        self.assertEqual(len(self.core.tracklist.tracks.get()), 5)

        self.sendRequest('delete "1:"')
        self.assertEqual(len(self.core.tracklist.tracks.get()), 1)
        self.assertInResponse('OK')

    def test_delete_closed_range(self):
        self.core.tracklist.add(
            [Track(), Track(), Track(), Track(), Track()])
        self.assertEqual(len(self.core.tracklist.tracks.get()), 5)

        self.sendRequest('delete "1:3"')
        self.assertEqual(len(self.core.tracklist.tracks.get()), 3)
        self.assertInResponse('OK')

    def test_delete_range_out_of_bounds(self):
        self.core.tracklist.add(
            [Track(), Track(), Track(), Track(), Track()])
        self.assertEqual(len(self.core.tracklist.tracks.get()), 5)

        self.sendRequest('delete "5:7"')
        self.assertEqual(len(self.core.tracklist.tracks.get()), 5)
        self.assertEqualResponse('ACK [2@0] {delete} Bad song index')

    def test_deleteid(self):
        self.core.tracklist.add([Track(), Track()])
        self.assertEqual(len(self.core.tracklist.tracks.get()), 2)

        self.sendRequest('deleteid "1"')
        self.assertEqual(len(self.core.tracklist.tracks.get()), 1)
        self.assertInResponse('OK')

    def test_deleteid_does_not_exist(self):
        self.core.tracklist.add([Track(), Track()])
        self.assertEqual(len(self.core.tracklist.tracks.get()), 2)

        self.sendRequest('deleteid "12345"')
        self.assertEqual(len(self.core.tracklist.tracks.get()), 2)
        self.assertEqualResponse('ACK [50@0] {deleteid} No such song')

    def test_move_songpos(self):
        self.core.tracklist.add([
            Track(name='a'), Track(name='b'), Track(name='c'),
            Track(name='d'), Track(name='e'), Track(name='f'),
        ])

        self.sendRequest('move "1" "0"')
        tracks = self.core.tracklist.tracks.get()
        self.assertEqual(tracks[0].name, 'b')
        self.assertEqual(tracks[1].name, 'a')
        self.assertEqual(tracks[2].name, 'c')
        self.assertEqual(tracks[3].name, 'd')
        self.assertEqual(tracks[4].name, 'e')
        self.assertEqual(tracks[5].name, 'f')
        self.assertInResponse('OK')

    def test_move_open_range(self):
        self.core.tracklist.add([
            Track(name='a'), Track(name='b'), Track(name='c'),
            Track(name='d'), Track(name='e'), Track(name='f'),
        ])

        self.sendRequest('move "2:" "0"')
        tracks = self.core.tracklist.tracks.get()
        self.assertEqual(tracks[0].name, 'c')
        self.assertEqual(tracks[1].name, 'd')
        self.assertEqual(tracks[2].name, 'e')
        self.assertEqual(tracks[3].name, 'f')
        self.assertEqual(tracks[4].name, 'a')
        self.assertEqual(tracks[5].name, 'b')
        self.assertInResponse('OK')

    def test_move_closed_range(self):
        self.core.tracklist.add([
            Track(name='a'), Track(name='b'), Track(name='c'),
            Track(name='d'), Track(name='e'), Track(name='f'),
        ])

        self.sendRequest('move "1:3" "0"')
        tracks = self.core.tracklist.tracks.get()
        self.assertEqual(tracks[0].name, 'b')
        self.assertEqual(tracks[1].name, 'c')
        self.assertEqual(tracks[2].name, 'a')
        self.assertEqual(tracks[3].name, 'd')
        self.assertEqual(tracks[4].name, 'e')
        self.assertEqual(tracks[5].name, 'f')
        self.assertInResponse('OK')

    def test_moveid(self):
        self.core.tracklist.add([
            Track(name='a'), Track(name='b'), Track(name='c'),
            Track(name='d'), Track(name='e'), Track(name='f'),
        ])

        self.sendRequest('moveid "4" "2"')
        tracks = self.core.tracklist.tracks.get()
        self.assertEqual(tracks[0].name, 'a')
        self.assertEqual(tracks[1].name, 'b')
        self.assertEqual(tracks[2].name, 'e')
        self.assertEqual(tracks[3].name, 'c')
        self.assertEqual(tracks[4].name, 'd')
        self.assertEqual(tracks[5].name, 'f')
        self.assertInResponse('OK')

    def test_moveid_with_tlid_not_found_in_tracklist_should_ack(self):
        self.sendRequest('moveid "9" "0"')
        self.assertEqualResponse(
            'ACK [50@0] {moveid} No such song')

    def test_playlist_returns_same_as_playlistinfo(self):
        playlist_response = self.sendRequest('playlist')
        playlistinfo_response = self.sendRequest('playlistinfo')
        self.assertEqual(playlist_response, playlistinfo_response)

    def test_playlistfind(self):
        self.sendRequest('playlistfind "tag" "needle"')
        self.assertEqualResponse('ACK [0@0] {playlistfind} Not implemented')

    def test_playlistfind_by_filename_not_in_tracklist(self):
        self.sendRequest('playlistfind "filename" "file:///dev/null"')
        self.assertEqualResponse('OK')

    def test_playlistfind_by_filename_without_quotes(self):
        self.sendRequest('playlistfind filename "file:///dev/null"')
        self.assertEqualResponse('OK')

    def test_playlistfind_by_filename_in_tracklist(self):
        self.core.tracklist.add([Track(uri='file:///exists')])

        self.sendRequest('playlistfind filename "file:///exists"')
        self.assertInResponse('file: file:///exists')
        self.assertInResponse('Id: 0')
        self.assertInResponse('Pos: 0')
        self.assertInResponse('OK')

    def test_playlistid_without_songid(self):
        self.core.tracklist.add([Track(name='a'), Track(name='b')])

        self.sendRequest('playlistid')
        self.assertInResponse('Title: a')
        self.assertInResponse('Title: b')
        self.assertInResponse('OK')

    def test_playlistid_with_songid(self):
        self.core.tracklist.add([Track(name='a'), Track(name='b')])

        self.sendRequest('playlistid "1"')
        self.assertNotInResponse('Title: a')
        self.assertNotInResponse('Id: 0')
        self.assertInResponse('Title: b')
        self.assertInResponse('Id: 1')
        self.assertInResponse('OK')

    def test_playlistid_with_not_existing_songid_fails(self):
        self.core.tracklist.add([Track(name='a'), Track(name='b')])

        self.sendRequest('playlistid "25"')
        self.assertEqualResponse('ACK [50@0] {playlistid} No such song')

    def test_playlistinfo_without_songpos_or_range(self):
        self.core.tracklist.add([
            Track(name='a'), Track(name='b'), Track(name='c'),
            Track(name='d'), Track(name='e'), Track(name='f'),
        ])

        self.sendRequest('playlistinfo')
        self.assertInResponse('Title: a')
        self.assertInResponse('Pos: 0')
        self.assertInResponse('Title: b')
        self.assertInResponse('Pos: 1')
        self.assertInResponse('Title: c')
        self.assertInResponse('Pos: 2')
        self.assertInResponse('Title: d')
        self.assertInResponse('Pos: 3')
        self.assertInResponse('Title: e')
        self.assertInResponse('Pos: 4')
        self.assertInResponse('Title: f')
        self.assertInResponse('Pos: 5')
        self.assertInResponse('OK')

    def test_playlistinfo_with_songpos(self):
        # Make the track's CPID not match the playlist position
        self.core.tracklist.tlid = 17
        self.core.tracklist.add([
            Track(name='a'), Track(name='b'), Track(name='c'),
            Track(name='d'), Track(name='e'), Track(name='f'),
        ])

        self.sendRequest('playlistinfo "4"')
        self.assertNotInResponse('Title: a')
        self.assertNotInResponse('Pos: 0')
        self.assertNotInResponse('Title: b')
        self.assertNotInResponse('Pos: 1')
        self.assertNotInResponse('Title: c')
        self.assertNotInResponse('Pos: 2')
        self.assertNotInResponse('Title: d')
        self.assertNotInResponse('Pos: 3')
        self.assertInResponse('Title: e')
        self.assertInResponse('Pos: 4')
        self.assertNotInResponse('Title: f')
        self.assertNotInResponse('Pos: 5')
        self.assertInResponse('OK')

    def test_playlistinfo_with_negative_songpos_same_as_playlistinfo(self):
        response1 = self.sendRequest('playlistinfo "-1"')
        response2 = self.sendRequest('playlistinfo')
        self.assertEqual(response1, response2)

    def test_playlistinfo_with_open_range(self):
        self.core.tracklist.add([
            Track(name='a'), Track(name='b'), Track(name='c'),
            Track(name='d'), Track(name='e'), Track(name='f'),
        ])

        self.sendRequest('playlistinfo "2:"')
        self.assertNotInResponse('Title: a')
        self.assertNotInResponse('Pos: 0')
        self.assertNotInResponse('Title: b')
        self.assertNotInResponse('Pos: 1')
        self.assertInResponse('Title: c')
        self.assertInResponse('Pos: 2')
        self.assertInResponse('Title: d')
        self.assertInResponse('Pos: 3')
        self.assertInResponse('Title: e')
        self.assertInResponse('Pos: 4')
        self.assertInResponse('Title: f')
        self.assertInResponse('Pos: 5')
        self.assertInResponse('OK')

    def test_playlistinfo_with_closed_range(self):
        self.core.tracklist.add([
            Track(name='a'), Track(name='b'), Track(name='c'),
            Track(name='d'), Track(name='e'), Track(name='f'),
        ])

        self.sendRequest('playlistinfo "2:4"')
        self.assertNotInResponse('Title: a')
        self.assertNotInResponse('Title: b')
        self.assertInResponse('Title: c')
        self.assertInResponse('Title: d')
        self.assertNotInResponse('Title: e')
        self.assertNotInResponse('Title: f')
        self.assertInResponse('OK')

    def test_playlistinfo_with_too_high_start_of_range_returns_arg_error(self):
        self.sendRequest('playlistinfo "10:20"')
        self.assertEqualResponse('ACK [2@0] {playlistinfo} Bad song index')

    def test_playlistinfo_with_too_high_end_of_range_returns_ok(self):
        self.sendRequest('playlistinfo "0:20"')
        self.assertInResponse('OK')

    def test_playlistinfo_with_zero_returns_ok(self):
        self.sendRequest('playlistinfo "0"')
        self.assertInResponse('OK')

    def test_playlistsearch(self):
        self.sendRequest('playlistsearch "any" "needle"')
        self.assertEqualResponse('ACK [0@0] {playlistsearch} Not implemented')

    def test_playlistsearch_without_quotes(self):
        self.sendRequest('playlistsearch any "needle"')
        self.assertEqualResponse('ACK [0@0] {playlistsearch} Not implemented')

    def test_plchanges_with_lower_version_returns_changes(self):
        self.core.tracklist.add(
            [Track(name='a'), Track(name='b'), Track(name='c')])

        self.sendRequest('plchanges "0"')
        self.assertInResponse('Title: a')
        self.assertInResponse('Title: b')
        self.assertInResponse('Title: c')
        self.assertInResponse('OK')

    def test_plchanges_with_equal_version_returns_nothing(self):
        self.core.tracklist.add(
            [Track(name='a'), Track(name='b'), Track(name='c')])

        self.assertEqual(self.core.tracklist.version.get(), 1)
        self.sendRequest('plchanges "1"')
        self.assertNotInResponse('Title: a')
        self.assertNotInResponse('Title: b')
        self.assertNotInResponse('Title: c')
        self.assertInResponse('OK')

    def test_plchanges_with_greater_version_returns_nothing(self):
        self.core.tracklist.add(
            [Track(name='a'), Track(name='b'), Track(name='c')])

        self.assertEqual(self.core.tracklist.version.get(), 1)
        self.sendRequest('plchanges "2"')
        self.assertNotInResponse('Title: a')
        self.assertNotInResponse('Title: b')
        self.assertNotInResponse('Title: c')
        self.assertInResponse('OK')

    def test_plchanges_with_minus_one_returns_entire_playlist(self):
        self.core.tracklist.add(
            [Track(name='a'), Track(name='b'), Track(name='c')])

        self.sendRequest('plchanges "-1"')
        self.assertInResponse('Title: a')
        self.assertInResponse('Title: b')
        self.assertInResponse('Title: c')
        self.assertInResponse('OK')

    def test_plchanges_without_quotes_works(self):
        self.core.tracklist.add(
            [Track(name='a'), Track(name='b'), Track(name='c')])

        self.sendRequest('plchanges 0')
        self.assertInResponse('Title: a')
        self.assertInResponse('Title: b')
        self.assertInResponse('Title: c')
        self.assertInResponse('OK')

    def test_plchangesposid(self):
        self.core.tracklist.add([Track(), Track(), Track()])

        self.sendRequest('plchangesposid "0"')
        tl_tracks = self.core.tracklist.tl_tracks.get()
        self.assertInResponse('cpos: 0')
        self.assertInResponse('Id: %d' % tl_tracks[0].tlid)
        self.assertInResponse('cpos: 2')
        self.assertInResponse('Id: %d' % tl_tracks[1].tlid)
        self.assertInResponse('cpos: 2')
        self.assertInResponse('Id: %d' % tl_tracks[2].tlid)
        self.assertInResponse('OK')

    def test_shuffle_without_range(self):
        self.core.tracklist.add([
            Track(name='a'), Track(name='b'), Track(name='c'),
            Track(name='d'), Track(name='e'), Track(name='f'),
        ])
        version = self.core.tracklist.version.get()

        self.sendRequest('shuffle')
        self.assertLess(version, self.core.tracklist.version.get())
        self.assertInResponse('OK')

    def test_shuffle_with_open_range(self):
        self.core.tracklist.add([
            Track(name='a'), Track(name='b'), Track(name='c'),
            Track(name='d'), Track(name='e'), Track(name='f'),
        ])
        version = self.core.tracklist.version.get()

        self.sendRequest('shuffle "4:"')
        self.assertLess(version, self.core.tracklist.version.get())
        tracks = self.core.tracklist.tracks.get()
        self.assertEqual(tracks[0].name, 'a')
        self.assertEqual(tracks[1].name, 'b')
        self.assertEqual(tracks[2].name, 'c')
        self.assertEqual(tracks[3].name, 'd')
        self.assertInResponse('OK')

    def test_shuffle_with_closed_range(self):
        self.core.tracklist.add([
            Track(name='a'), Track(name='b'), Track(name='c'),
            Track(name='d'), Track(name='e'), Track(name='f'),
        ])
        version = self.core.tracklist.version.get()

        self.sendRequest('shuffle "1:3"')
        self.assertLess(version, self.core.tracklist.version.get())
        tracks = self.core.tracklist.tracks.get()
        self.assertEqual(tracks[0].name, 'a')
        self.assertEqual(tracks[3].name, 'd')
        self.assertEqual(tracks[4].name, 'e')
        self.assertEqual(tracks[5].name, 'f')
        self.assertInResponse('OK')

    def test_swap(self):
        self.core.tracklist.add([
            Track(name='a'), Track(name='b'), Track(name='c'),
            Track(name='d'), Track(name='e'), Track(name='f'),
        ])

        self.sendRequest('swap "1" "4"')
        tracks = self.core.tracklist.tracks.get()
        self.assertEqual(tracks[0].name, 'a')
        self.assertEqual(tracks[1].name, 'e')
        self.assertEqual(tracks[2].name, 'c')
        self.assertEqual(tracks[3].name, 'd')
        self.assertEqual(tracks[4].name, 'b')
        self.assertEqual(tracks[5].name, 'f')
        self.assertInResponse('OK')

    def test_swapid(self):
        self.core.tracklist.add([
            Track(name='a'), Track(name='b'), Track(name='c'),
            Track(name='d'), Track(name='e'), Track(name='f'),
        ])

        self.sendRequest('swapid "1" "4"')
        tracks = self.core.tracklist.tracks.get()
        self.assertEqual(tracks[0].name, 'a')
        self.assertEqual(tracks[1].name, 'e')
        self.assertEqual(tracks[2].name, 'c')
        self.assertEqual(tracks[3].name, 'd')
        self.assertEqual(tracks[4].name, 'b')
        self.assertEqual(tracks[5].name, 'f')
        self.assertInResponse('OK')

    def test_swapid_with_first_id_unknown_should_ack(self):
        self.core.tracklist.add([Track()])
        self.sendRequest('swapid "0" "4"')
        self.assertEqualResponse(
            'ACK [50@0] {swapid} No such song')

    def test_swapid_with_second_id_unknown_should_ack(self):
        self.core.tracklist.add([Track()])
        self.sendRequest('swapid "4" "0"')
        self.assertEqualResponse(
            'ACK [50@0] {swapid} No such song')

########NEW FILE########
__FILENAME__ = test_idle
from __future__ import unicode_literals

from mock import patch

from mopidy.mpd.protocol.status import SUBSYSTEMS

from tests.mpd import protocol


class IdleHandlerTest(protocol.BaseTestCase):
    def idleEvent(self, subsystem):
        self.session.on_idle(subsystem)

    def assertEqualEvents(self, events):
        self.assertEqual(set(events), self.context.events)

    def assertEqualSubscriptions(self, events):
        self.assertEqual(set(events), self.context.subscriptions)

    def assertNoEvents(self):
        self.assertEqualEvents([])

    def assertNoSubscriptions(self):
        self.assertEqualSubscriptions([])

    def test_base_state(self):
        self.assertNoSubscriptions()
        self.assertNoEvents()
        self.assertNoResponse()

    def test_idle(self):
        self.sendRequest('idle')
        self.assertEqualSubscriptions(SUBSYSTEMS)
        self.assertNoEvents()
        self.assertNoResponse()

    def test_idle_disables_timeout(self):
        self.sendRequest('idle')
        self.connection.disable_timeout.assert_called_once_with()

    def test_noidle(self):
        self.sendRequest('noidle')
        self.assertNoSubscriptions()
        self.assertNoEvents()
        self.assertNoResponse()

    def test_idle_player(self):
        self.sendRequest('idle player')
        self.assertEqualSubscriptions(['player'])
        self.assertNoEvents()
        self.assertNoResponse()

    def test_idle_player_playlist(self):
        self.sendRequest('idle player playlist')
        self.assertEqualSubscriptions(['player', 'playlist'])
        self.assertNoEvents()
        self.assertNoResponse()

    def test_idle_then_noidle(self):
        self.sendRequest('idle')
        self.sendRequest('noidle')
        self.assertNoSubscriptions()
        self.assertNoEvents()
        self.assertOnceInResponse('OK')

    def test_idle_then_noidle_enables_timeout(self):
        self.sendRequest('idle')
        self.sendRequest('noidle')
        self.connection.enable_timeout.assert_called_once_with()

    def test_idle_then_play(self):
        with patch.object(self.session, 'stop') as stop_mock:
            self.sendRequest('idle')
            self.sendRequest('play')
            stop_mock.assert_called_once_with()

    def test_idle_then_idle(self):
        with patch.object(self.session, 'stop') as stop_mock:
            self.sendRequest('idle')
            self.sendRequest('idle')
            stop_mock.assert_called_once_with()

    def test_idle_player_then_play(self):
        with patch.object(self.session, 'stop') as stop_mock:
            self.sendRequest('idle player')
            self.sendRequest('play')
            stop_mock.assert_called_once_with()

    def test_idle_then_player(self):
        self.sendRequest('idle')
        self.idleEvent('player')
        self.assertNoSubscriptions()
        self.assertNoEvents()
        self.assertOnceInResponse('changed: player')
        self.assertOnceInResponse('OK')

    def test_idle_player_then_event_player(self):
        self.sendRequest('idle player')
        self.idleEvent('player')
        self.assertNoSubscriptions()
        self.assertNoEvents()
        self.assertOnceInResponse('changed: player')
        self.assertOnceInResponse('OK')

    def test_idle_player_then_noidle(self):
        self.sendRequest('idle player')
        self.sendRequest('noidle')
        self.assertNoSubscriptions()
        self.assertNoEvents()
        self.assertOnceInResponse('OK')

    def test_idle_player_playlist_then_noidle(self):
        self.sendRequest('idle player playlist')
        self.sendRequest('noidle')
        self.assertNoEvents()
        self.assertNoSubscriptions()
        self.assertOnceInResponse('OK')

    def test_idle_player_playlist_then_player(self):
        self.sendRequest('idle player playlist')
        self.idleEvent('player')
        self.assertNoEvents()
        self.assertNoSubscriptions()
        self.assertOnceInResponse('changed: player')
        self.assertNotInResponse('changed: playlist')
        self.assertOnceInResponse('OK')

    def test_idle_playlist_then_player(self):
        self.sendRequest('idle playlist')
        self.idleEvent('player')
        self.assertEqualEvents(['player'])
        self.assertEqualSubscriptions(['playlist'])
        self.assertNoResponse()

    def test_idle_playlist_then_player_then_playlist(self):
        self.sendRequest('idle playlist')
        self.idleEvent('player')
        self.idleEvent('playlist')
        self.assertNoEvents()
        self.assertNoSubscriptions()
        self.assertNotInResponse('changed: player')
        self.assertOnceInResponse('changed: playlist')
        self.assertOnceInResponse('OK')

    def test_player(self):
        self.idleEvent('player')
        self.assertEqualEvents(['player'])
        self.assertNoSubscriptions()
        self.assertNoResponse()

    def test_player_then_idle_player(self):
        self.idleEvent('player')
        self.sendRequest('idle player')
        self.assertNoEvents()
        self.assertNoSubscriptions()
        self.assertOnceInResponse('changed: player')
        self.assertNotInResponse('changed: playlist')
        self.assertOnceInResponse('OK')

    def test_player_then_playlist(self):
        self.idleEvent('player')
        self.idleEvent('playlist')
        self.assertEqualEvents(['player', 'playlist'])
        self.assertNoSubscriptions()
        self.assertNoResponse()

    def test_player_then_idle(self):
        self.idleEvent('player')
        self.sendRequest('idle')
        self.assertNoEvents()
        self.assertNoSubscriptions()
        self.assertOnceInResponse('changed: player')
        self.assertOnceInResponse('OK')

    def test_player_then_playlist_then_idle(self):
        self.idleEvent('player')
        self.idleEvent('playlist')
        self.sendRequest('idle')
        self.assertNoEvents()
        self.assertNoSubscriptions()
        self.assertOnceInResponse('changed: player')
        self.assertOnceInResponse('changed: playlist')
        self.assertOnceInResponse('OK')

    def test_player_then_idle_playlist(self):
        self.idleEvent('player')
        self.sendRequest('idle playlist')
        self.assertEqualEvents(['player'])
        self.assertEqualSubscriptions(['playlist'])
        self.assertNoResponse()

    def test_player_then_idle_playlist_then_noidle(self):
        self.idleEvent('player')
        self.sendRequest('idle playlist')
        self.sendRequest('noidle')
        self.assertNoEvents()
        self.assertNoSubscriptions()
        self.assertOnceInResponse('OK')

    def test_player_then_playlist_then_idle_playlist(self):
        self.idleEvent('player')
        self.idleEvent('playlist')
        self.sendRequest('idle playlist')
        self.assertNoEvents()
        self.assertNoSubscriptions()
        self.assertNotInResponse('changed: player')
        self.assertOnceInResponse('changed: playlist')
        self.assertOnceInResponse('OK')

########NEW FILE########
__FILENAME__ = test_music_db
from __future__ import unicode_literals

import unittest

from mopidy.models import Album, Artist, Playlist, Ref, SearchResult, Track
from mopidy.mpd.protocol import music_db

from tests.mpd import protocol


class QueryFromMpdSearchFormatTest(unittest.TestCase):
    def test_dates_are_extracted(self):
        result = music_db._query_from_mpd_search_parameters(
            ['Date', '1974-01-02', 'Date', '1975'], music_db._SEARCH_MAPPING)
        self.assertEqual(result['date'][0], '1974-01-02')
        self.assertEqual(result['date'][1], '1975')

    # TODO Test more mappings


class QueryFromMpdListFormatTest(unittest.TestCase):
    pass  # TODO


class MusicDatabaseHandlerTest(protocol.BaseTestCase):
    def test_count(self):
        self.sendRequest('count "artist" "needle"')
        self.assertInResponse('songs: 0')
        self.assertInResponse('playtime: 0')
        self.assertInResponse('OK')

    def test_count_without_quotes(self):
        self.sendRequest('count artist "needle"')
        self.assertInResponse('songs: 0')
        self.assertInResponse('playtime: 0')
        self.assertInResponse('OK')

    def test_count_with_multiple_pairs(self):
        self.sendRequest('count "artist" "foo" "album" "bar"')
        self.assertInResponse('songs: 0')
        self.assertInResponse('playtime: 0')
        self.assertInResponse('OK')

    def test_count_correct_length(self):
        # Count the lone track
        self.backend.library.dummy_find_exact_result = SearchResult(
            tracks=[
                Track(uri='dummy:a', name="foo", date="2001", length=4000),
            ])
        self.sendRequest('count "title" "foo"')
        self.assertInResponse('songs: 1')
        self.assertInResponse('playtime: 4')
        self.assertInResponse('OK')

        # Count multiple tracks
        self.backend.library.dummy_find_exact_result = SearchResult(
            tracks=[
                Track(uri='dummy:b', date="2001", length=50000),
                Track(uri='dummy:c', date="2001", length=600000),
            ])
        self.sendRequest('count "date" "2001"')
        self.assertInResponse('songs: 2')
        self.assertInResponse('playtime: 650')
        self.assertInResponse('OK')

    def test_findadd(self):
        self.backend.library.dummy_find_exact_result = SearchResult(
            tracks=[Track(uri='dummy:a', name='A')])
        self.assertEqual(self.core.tracklist.length.get(), 0)

        self.sendRequest('findadd "title" "A"')

        self.assertEqual(self.core.tracklist.length.get(), 1)
        self.assertEqual(self.core.tracklist.tracks.get()[0].uri, 'dummy:a')
        self.assertInResponse('OK')

    def test_searchadd(self):
        self.backend.library.dummy_search_result = SearchResult(
            tracks=[Track(uri='dummy:a', name='A')])
        self.assertEqual(self.core.tracklist.length.get(), 0)

        self.sendRequest('searchadd "title" "a"')

        self.assertEqual(self.core.tracklist.length.get(), 1)
        self.assertEqual(self.core.tracklist.tracks.get()[0].uri, 'dummy:a')
        self.assertInResponse('OK')

    def test_searchaddpl_appends_to_existing_playlist(self):
        playlist = self.core.playlists.create('my favs').get()
        playlist = playlist.copy(tracks=[
            Track(uri='dummy:x', name='X'),
            Track(uri='dummy:y', name='y'),
        ])
        self.core.playlists.save(playlist)
        self.backend.library.dummy_search_result = SearchResult(
            tracks=[Track(uri='dummy:a', name='A')])
        playlists = self.core.playlists.filter(name='my favs').get()
        self.assertEqual(len(playlists), 1)
        self.assertEqual(len(playlists[0].tracks), 2)

        self.sendRequest('searchaddpl "my favs" "title" "a"')

        playlists = self.core.playlists.filter(name='my favs').get()
        self.assertEqual(len(playlists), 1)
        self.assertEqual(len(playlists[0].tracks), 3)
        self.assertEqual(playlists[0].tracks[0].uri, 'dummy:x')
        self.assertEqual(playlists[0].tracks[1].uri, 'dummy:y')
        self.assertEqual(playlists[0].tracks[2].uri, 'dummy:a')
        self.assertInResponse('OK')

    def test_searchaddpl_creates_missing_playlist(self):
        self.backend.library.dummy_search_result = SearchResult(
            tracks=[Track(uri='dummy:a', name='A')])
        self.assertEqual(
            len(self.core.playlists.filter(name='my favs').get()), 0)

        self.sendRequest('searchaddpl "my favs" "title" "a"')

        playlists = self.core.playlists.filter(name='my favs').get()
        self.assertEqual(len(playlists), 1)
        self.assertEqual(playlists[0].tracks[0].uri, 'dummy:a')
        self.assertInResponse('OK')

    def test_listall_without_uri(self):
        tracks = [Track(uri='dummy:/a', name='a'),
                  Track(uri='dummy:/foo/b', name='b')]
        self.backend.library.dummy_library = tracks
        self.backend.library.dummy_browse_result = {
            'dummy:/': [Ref.track(uri='dummy:/a', name='a'),
                        Ref.directory(uri='dummy:/foo', name='foo')],
            'dummy:/foo': [Ref.track(uri='dummy:/foo/b', name='b')]}

        self.sendRequest('listall')

        self.assertInResponse('file: dummy:/a')
        self.assertInResponse('directory: /dummy/foo')
        self.assertInResponse('file: dummy:/foo/b')
        self.assertInResponse('OK')

    def test_listall_with_uri(self):
        tracks = [Track(uri='dummy:/a', name='a'),
                  Track(uri='dummy:/foo/b', name='b')]
        self.backend.library.dummy_library = tracks
        self.backend.library.dummy_browse_result = {
            'dummy:/': [Ref.track(uri='dummy:/a', name='a'),
                        Ref.directory(uri='dummy:/foo', name='foo')],
            'dummy:/foo': [Ref.track(uri='dummy:/foo/b', name='b')]}

        self.sendRequest('listall "/dummy/foo"')

        self.assertNotInResponse('file: dummy:/a')
        self.assertInResponse('directory: /dummy/foo')
        self.assertInResponse('file: dummy:/foo/b')
        self.assertInResponse('OK')

    def test_listall_with_unknown_uri(self):
        self.sendRequest('listall "/unknown"')

        self.assertEqualResponse('ACK [50@0] {listall} Not found')

    def test_listall_for_dir_with_and_without_leading_slash_is_the_same(self):
        self.backend.library.dummy_browse_result = {
            'dummy:/': [Ref.track(uri='dummy:/a', name='a'),
                        Ref.directory(uri='dummy:/foo', name='foo')]}

        response1 = self.sendRequest('listall "dummy"')
        response2 = self.sendRequest('listall "/dummy"')
        self.assertEqual(response1, response2)

    def test_listall_for_dir_with_and_without_trailing_slash_is_the_same(self):
        self.backend.library.dummy_browse_result = {
            'dummy:/': [Ref.track(uri='dummy:/a', name='a'),
                        Ref.directory(uri='dummy:/foo', name='foo')]}

        response1 = self.sendRequest('listall "dummy"')
        response2 = self.sendRequest('listall "dummy/"')
        self.assertEqual(response1, response2)

    def test_listallinfo_without_uri(self):
        tracks = [Track(uri='dummy:/a', name='a'),
                  Track(uri='dummy:/foo/b', name='b')]
        self.backend.library.dummy_library = tracks
        self.backend.library.dummy_browse_result = {
            'dummy:/': [Ref.track(uri='dummy:/a', name='a'),
                        Ref.directory(uri='dummy:/foo', name='foo')],
            'dummy:/foo': [Ref.track(uri='dummy:/foo/b', name='b')]}

        self.sendRequest('listallinfo')

        self.assertInResponse('file: dummy:/a')
        self.assertInResponse('Title: a')
        self.assertInResponse('directory: /dummy/foo')
        self.assertInResponse('file: dummy:/foo/b')
        self.assertInResponse('Title: b')
        self.assertInResponse('OK')

    def test_listallinfo_with_uri(self):
        tracks = [Track(uri='dummy:/a', name='a'),
                  Track(uri='dummy:/foo/b', name='b')]
        self.backend.library.dummy_library = tracks
        self.backend.library.dummy_browse_result = {
            'dummy:/': [Ref.track(uri='dummy:/a', name='a'),
                        Ref.directory(uri='dummy:/foo', name='foo')],
            'dummy:/foo': [Ref.track(uri='dummy:/foo/b', name='b')]}

        self.sendRequest('listallinfo "/dummy/foo"')

        self.assertNotInResponse('file: dummy:/a')
        self.assertNotInResponse('Title: a')
        self.assertInResponse('directory: /dummy/foo')
        self.assertInResponse('file: dummy:/foo/b')
        self.assertInResponse('Title: b')
        self.assertInResponse('OK')

    def test_listallinfo_with_unknown_uri(self):
        self.sendRequest('listallinfo "/unknown"')

        self.assertEqualResponse('ACK [50@0] {listallinfo} Not found')

    def test_listallinfo_for_dir_with_and_without_leading_slash_is_same(self):
        self.backend.library.dummy_browse_result = {
            'dummy:/': [Ref.track(uri='dummy:/a', name='a'),
                        Ref.directory(uri='dummy:/foo', name='foo')]}

        response1 = self.sendRequest('listallinfo "dummy"')
        response2 = self.sendRequest('listallinfo "/dummy"')
        self.assertEqual(response1, response2)

    def test_listallinfo_for_dir_with_and_without_trailing_slash_is_same(self):
        self.backend.library.dummy_browse_result = {
            'dummy:/': [Ref.track(uri='dummy:/a', name='a'),
                        Ref.directory(uri='dummy:/foo', name='foo')]}

        response1 = self.sendRequest('listallinfo "dummy"')
        response2 = self.sendRequest('listallinfo "dummy/"')
        self.assertEqual(response1, response2)

    def test_lsinfo_without_path_returns_same_as_for_root(self):
        last_modified = 1390942873222
        self.backend.playlists.playlists = [
            Playlist(name='a', uri='dummy:/a', last_modified=last_modified)]

        response1 = self.sendRequest('lsinfo')
        response2 = self.sendRequest('lsinfo "/"')
        self.assertEqual(response1, response2)

    def test_lsinfo_with_empty_path_returns_same_as_for_root(self):
        last_modified = 1390942873222
        self.backend.playlists.playlists = [
            Playlist(name='a', uri='dummy:/a', last_modified=last_modified)]

        response1 = self.sendRequest('lsinfo ""')
        response2 = self.sendRequest('lsinfo "/"')
        self.assertEqual(response1, response2)

    def test_lsinfo_for_root_includes_playlists(self):
        last_modified = 1390942873222
        self.backend.playlists.playlists = [
            Playlist(name='a', uri='dummy:/a', last_modified=last_modified)]

        self.sendRequest('lsinfo "/"')
        self.assertInResponse('playlist: a')
        # Date without milliseconds and with time zone information
        self.assertInResponse('Last-Modified: 2014-01-28T21:01:13Z')
        self.assertInResponse('OK')

    def test_lsinfo_for_root_includes_dirs_for_each_lib_with_content(self):
        self.backend.library.dummy_browse_result = {
            'dummy:/': [Ref.track(uri='dummy:/a', name='a'),
                        Ref.directory(uri='dummy:/foo', name='foo')]}

        self.sendRequest('lsinfo "/"')
        self.assertInResponse('directory: dummy')
        self.assertInResponse('OK')

    def test_lsinfo_for_dir_with_and_without_leading_slash_is_the_same(self):
        self.backend.library.dummy_browse_result = {
            'dummy:/': [Ref.track(uri='dummy:/a', name='a'),
                        Ref.directory(uri='dummy:/foo', name='foo')]}

        response1 = self.sendRequest('lsinfo "dummy"')
        response2 = self.sendRequest('lsinfo "/dummy"')
        self.assertEqual(response1, response2)

    def test_lsinfo_for_dir_with_and_without_trailing_slash_is_the_same(self):
        self.backend.library.dummy_browse_result = {
            'dummy:/': [Ref.track(uri='dummy:/a', name='a'),
                        Ref.directory(uri='dummy:/foo', name='foo')]}

        response1 = self.sendRequest('lsinfo "dummy"')
        response2 = self.sendRequest('lsinfo "dummy/"')
        self.assertEqual(response1, response2)

    def test_lsinfo_for_dir_includes_tracks(self):
        self.backend.library.dummy_library = [
            Track(uri='dummy:/a', name='a'),
        ]
        self.backend.library.dummy_browse_result = {
            'dummy:/': [Ref.track(uri='dummy:/a', name='a')]}

        self.sendRequest('lsinfo "/dummy"')
        self.assertInResponse('file: dummy:/a')
        self.assertInResponse('Title: a')
        self.assertInResponse('OK')

    def test_lsinfo_for_dir_includes_subdirs(self):
        self.backend.library.dummy_browse_result = {
            'dummy:/': [Ref.directory(uri='dummy:/foo', name='foo')]}

        self.sendRequest('lsinfo "/dummy"')
        self.assertInResponse('directory: dummy/foo')
        self.assertInResponse('OK')

    def test_lsinfo_for_dir_does_not_recurse(self):
        self.backend.library.dummy_library = [
            Track(uri='dummy:/a', name='a'),
        ]
        self.backend.library.dummy_browse_result = {
            'dummy:/': [Ref.directory(uri='dummy:/foo', name='foo')],
            'dummy:/foo': [Ref.track(uri='dummy:/a', name='a')]}

        self.sendRequest('lsinfo "/dummy"')
        self.assertNotInResponse('file: dummy:/a')
        self.assertInResponse('OK')

    def test_lsinfo_for_dir_does_not_include_self(self):
        self.backend.library.dummy_browse_result = {
            'dummy:/': [Ref.directory(uri='dummy:/foo', name='foo')],
            'dummy:/foo': [Ref.track(uri='dummy:/a', name='a')]}

        self.sendRequest('lsinfo "/dummy"')
        self.assertNotInResponse('directory: dummy')
        self.assertInResponse('OK')

    def test_update_without_uri(self):
        self.sendRequest('update')
        self.assertInResponse('updating_db: 0')
        self.assertInResponse('OK')

    def test_update_with_uri(self):
        self.sendRequest('update "file:///dev/urandom"')
        self.assertInResponse('updating_db: 0')
        self.assertInResponse('OK')

    def test_rescan_without_uri(self):
        self.sendRequest('rescan')
        self.assertInResponse('updating_db: 0')
        self.assertInResponse('OK')

    def test_rescan_with_uri(self):
        self.sendRequest('rescan "file:///dev/urandom"')
        self.assertInResponse('updating_db: 0')
        self.assertInResponse('OK')


class MusicDatabaseFindTest(protocol.BaseTestCase):
    def test_find_includes_fake_artist_and_album_tracks(self):
        self.backend.library.dummy_find_exact_result = SearchResult(
            albums=[Album(uri='dummy:album:a', name='A', date='2001')],
            artists=[Artist(uri='dummy:artist:b', name='B')],
            tracks=[Track(uri='dummy:track:c', name='C')])

        self.sendRequest('find "any" "foo"')

        self.assertInResponse('file: dummy:artist:b')
        self.assertInResponse('Title: Artist: B')

        self.assertInResponse('file: dummy:album:a')
        self.assertInResponse('Title: Album: A')
        self.assertInResponse('Date: 2001')

        self.assertInResponse('file: dummy:track:c')
        self.assertInResponse('Title: C')

        self.assertInResponse('OK')

    def test_find_artist_does_not_include_fake_artist_tracks(self):
        self.backend.library.dummy_find_exact_result = SearchResult(
            albums=[Album(uri='dummy:album:a', name='A', date='2001')],
            artists=[Artist(uri='dummy:artist:b', name='B')],
            tracks=[Track(uri='dummy:track:c', name='C')])

        self.sendRequest('find "artist" "foo"')

        self.assertNotInResponse('file: dummy:artist:b')
        self.assertNotInResponse('Title: Artist: B')

        self.assertInResponse('file: dummy:album:a')
        self.assertInResponse('Title: Album: A')
        self.assertInResponse('Date: 2001')

        self.assertInResponse('file: dummy:track:c')
        self.assertInResponse('Title: C')

        self.assertInResponse('OK')

    def test_find_albumartist_does_not_include_fake_artist_tracks(self):
        self.backend.library.dummy_find_exact_result = SearchResult(
            albums=[Album(uri='dummy:album:a', name='A', date='2001')],
            artists=[Artist(uri='dummy:artist:b', name='B')],
            tracks=[Track(uri='dummy:track:c', name='C')])

        self.sendRequest('find "albumartist" "foo"')

        self.assertNotInResponse('file: dummy:artist:b')
        self.assertNotInResponse('Title: Artist: B')

        self.assertInResponse('file: dummy:album:a')
        self.assertInResponse('Title: Album: A')
        self.assertInResponse('Date: 2001')

        self.assertInResponse('file: dummy:track:c')
        self.assertInResponse('Title: C')

        self.assertInResponse('OK')

    def test_find_artist_and_album_does_not_include_fake_tracks(self):
        self.backend.library.dummy_find_exact_result = SearchResult(
            albums=[Album(uri='dummy:album:a', name='A', date='2001')],
            artists=[Artist(uri='dummy:artist:b', name='B')],
            tracks=[Track(uri='dummy:track:c', name='C')])

        self.sendRequest('find "artist" "foo" "album" "bar"')

        self.assertNotInResponse('file: dummy:artist:b')
        self.assertNotInResponse('Title: Artist: B')

        self.assertNotInResponse('file: dummy:album:a')
        self.assertNotInResponse('Title: Album: A')
        self.assertNotInResponse('Date: 2001')

        self.assertInResponse('file: dummy:track:c')
        self.assertInResponse('Title: C')

        self.assertInResponse('OK')

    def test_find_album(self):
        self.sendRequest('find "album" "what"')
        self.assertInResponse('OK')

    def test_find_album_without_quotes(self):
        self.sendRequest('find album "what"')
        self.assertInResponse('OK')

    def test_find_artist(self):
        self.sendRequest('find "artist" "what"')
        self.assertInResponse('OK')

    def test_find_artist_without_quotes(self):
        self.sendRequest('find artist "what"')
        self.assertInResponse('OK')

    def test_find_albumartist(self):
        self.sendRequest('find "albumartist" "what"')
        self.assertInResponse('OK')

    def test_find_albumartist_without_quotes(self):
        self.sendRequest('find albumartist "what"')
        self.assertInResponse('OK')

    def test_find_composer(self):
        self.sendRequest('find "composer" "what"')
        self.assertInResponse('OK')

    def test_find_composer_without_quotes(self):
        self.sendRequest('find composer "what"')
        self.assertInResponse('OK')

    def test_find_performer(self):
        self.sendRequest('find "performer" "what"')
        self.assertInResponse('OK')

    def test_find_performer_without_quotes(self):
        self.sendRequest('find performer "what"')
        self.assertInResponse('OK')

    def test_find_filename(self):
        self.sendRequest('find "filename" "afilename"')
        self.assertInResponse('OK')

    def test_find_filename_without_quotes(self):
        self.sendRequest('find filename "afilename"')
        self.assertInResponse('OK')

    def test_find_file(self):
        self.sendRequest('find "file" "afilename"')
        self.assertInResponse('OK')

    def test_find_file_without_quotes(self):
        self.sendRequest('find file "afilename"')
        self.assertInResponse('OK')

    def test_find_title(self):
        self.sendRequest('find "title" "what"')
        self.assertInResponse('OK')

    def test_find_title_without_quotes(self):
        self.sendRequest('find title "what"')
        self.assertInResponse('OK')

    def test_find_track_no(self):
        self.sendRequest('find "track" "10"')
        self.assertInResponse('OK')

    def test_find_track_no_without_quotes(self):
        self.sendRequest('find track "10"')
        self.assertInResponse('OK')

    def test_find_track_no_without_filter_value(self):
        self.sendRequest('find "track" ""')
        self.assertInResponse('OK')

    def test_find_genre(self):
        self.sendRequest('find "genre" "what"')
        self.assertInResponse('OK')

    def test_find_genre_without_quotes(self):
        self.sendRequest('find genre "what"')
        self.assertInResponse('OK')

    def test_find_date(self):
        self.sendRequest('find "date" "2002-01-01"')
        self.assertInResponse('OK')

    def test_find_date_without_quotes(self):
        self.sendRequest('find date "2002-01-01"')
        self.assertInResponse('OK')

    def test_find_date_with_capital_d_and_incomplete_date(self):
        self.sendRequest('find Date "2005"')
        self.assertInResponse('OK')

    def test_find_else_should_fail(self):
        self.sendRequest('find "somethingelse" "what"')
        self.assertEqualResponse('ACK [2@0] {find} incorrect arguments')

    def test_find_album_and_artist(self):
        self.sendRequest('find album "album_what" artist "artist_what"')
        self.assertInResponse('OK')

    def test_find_without_filter_value(self):
        self.sendRequest('find "album" ""')
        self.assertInResponse('OK')


class MusicDatabaseListTest(protocol.BaseTestCase):
    def test_list(self):
        self.backend.library.dummy_find_exact_result = SearchResult(
            tracks=[
                Track(uri='dummy:a', name='A', artists=[
                    Artist(name='A Artist')])])

        self.sendRequest('list "artist" "artist" "foo"')

        self.assertInResponse('Artist: A Artist')
        self.assertInResponse('OK')

    def test_list_foo_returns_ack(self):
        self.sendRequest('list "foo"')
        self.assertEqualResponse('ACK [2@0] {list} incorrect arguments')

    # Artist

    def test_list_artist_with_quotes(self):
        self.sendRequest('list "artist"')
        self.assertInResponse('OK')

    def test_list_artist_without_quotes(self):
        self.sendRequest('list artist')
        self.assertInResponse('OK')

    def test_list_artist_without_quotes_and_capitalized(self):
        self.sendRequest('list Artist')
        self.assertInResponse('OK')

    def test_list_artist_with_query_of_one_token(self):
        self.sendRequest('list "artist" "anartist"')
        self.assertEqualResponse(
            'ACK [2@0] {list} should be "Album" for 3 arguments')

    def test_list_artist_with_unknown_field_in_query_returns_ack(self):
        self.sendRequest('list "artist" "foo" "bar"')
        self.assertEqualResponse('ACK [2@0] {list} not able to parse args')

    def test_list_artist_by_artist(self):
        self.sendRequest('list "artist" "artist" "anartist"')
        self.assertInResponse('OK')

    def test_list_artist_by_album(self):
        self.sendRequest('list "artist" "album" "analbum"')
        self.assertInResponse('OK')

    def test_list_artist_by_full_date(self):
        self.sendRequest('list "artist" "date" "2001-01-01"')
        self.assertInResponse('OK')

    def test_list_artist_by_year(self):
        self.sendRequest('list "artist" "date" "2001"')
        self.assertInResponse('OK')

    def test_list_artist_by_genre(self):
        self.sendRequest('list "artist" "genre" "agenre"')
        self.assertInResponse('OK')

    def test_list_artist_by_artist_and_album(self):
        self.sendRequest(
            'list "artist" "artist" "anartist" "album" "analbum"')
        self.assertInResponse('OK')

    def test_list_artist_without_filter_value(self):
        self.sendRequest('list "artist" "artist" ""')
        self.assertInResponse('OK')

    def test_list_artist_should_not_return_artists_without_names(self):
        self.backend.library.dummy_find_exact_result = SearchResult(
            tracks=[Track(artists=[Artist(name='')])])

        self.sendRequest('list "artist"')
        self.assertNotInResponse('Artist: ')
        self.assertInResponse('OK')

    # Albumartist

    def test_list_albumartist_with_quotes(self):
        self.sendRequest('list "albumartist"')
        self.assertInResponse('OK')

    def test_list_albumartist_without_quotes(self):
        self.sendRequest('list albumartist')
        self.assertInResponse('OK')

    def test_list_albumartist_without_quotes_and_capitalized(self):
        self.sendRequest('list Albumartist')
        self.assertInResponse('OK')

    def test_list_albumartist_with_query_of_one_token(self):
        self.sendRequest('list "albumartist" "anartist"')
        self.assertEqualResponse(
            'ACK [2@0] {list} should be "Album" for 3 arguments')

    def test_list_albumartist_with_unknown_field_in_query_returns_ack(self):
        self.sendRequest('list "albumartist" "foo" "bar"')
        self.assertEqualResponse('ACK [2@0] {list} not able to parse args')

    def test_list_albumartist_by_artist(self):
        self.sendRequest('list "albumartist" "artist" "anartist"')
        self.assertInResponse('OK')

    def test_list_albumartist_by_album(self):
        self.sendRequest('list "albumartist" "album" "analbum"')
        self.assertInResponse('OK')

    def test_list_albumartist_by_full_date(self):
        self.sendRequest('list "albumartist" "date" "2001-01-01"')
        self.assertInResponse('OK')

    def test_list_albumartist_by_year(self):
        self.sendRequest('list "albumartist" "date" "2001"')
        self.assertInResponse('OK')

    def test_list_albumartist_by_genre(self):
        self.sendRequest('list "albumartist" "genre" "agenre"')
        self.assertInResponse('OK')

    def test_list_albumartist_by_artist_and_album(self):
        self.sendRequest(
            'list "albumartist" "artist" "anartist" "album" "analbum"')
        self.assertInResponse('OK')

    def test_list_albumartist_without_filter_value(self):
        self.sendRequest('list "albumartist" "artist" ""')
        self.assertInResponse('OK')

    def test_list_albumartist_should_not_return_artists_without_names(self):
        self.backend.library.dummy_find_exact_result = SearchResult(
            tracks=[Track(album=Album(artists=[Artist(name='')]))])

        self.sendRequest('list "albumartist"')
        self.assertNotInResponse('Artist: ')
        self.assertNotInResponse('Albumartist: ')
        self.assertNotInResponse('Composer: ')
        self.assertNotInResponse('Performer: ')
        self.assertInResponse('OK')

    # Composer

    def test_list_composer_with_quotes(self):
        self.sendRequest('list "composer"')
        self.assertInResponse('OK')

    def test_list_composer_without_quotes(self):
        self.sendRequest('list composer')
        self.assertInResponse('OK')

    def test_list_composer_without_quotes_and_capitalized(self):
        self.sendRequest('list Composer')
        self.assertInResponse('OK')

    def test_list_composer_with_query_of_one_token(self):
        self.sendRequest('list "composer" "anartist"')
        self.assertEqualResponse(
            'ACK [2@0] {list} should be "Album" for 3 arguments')

    def test_list_composer_with_unknown_field_in_query_returns_ack(self):
        self.sendRequest('list "composer" "foo" "bar"')
        self.assertEqualResponse('ACK [2@0] {list} not able to parse args')

    def test_list_composer_by_artist(self):
        self.sendRequest('list "composer" "artist" "anartist"')
        self.assertInResponse('OK')

    def test_list_composer_by_album(self):
        self.sendRequest('list "composer" "album" "analbum"')
        self.assertInResponse('OK')

    def test_list_composer_by_full_date(self):
        self.sendRequest('list "composer" "date" "2001-01-01"')
        self.assertInResponse('OK')

    def test_list_composer_by_year(self):
        self.sendRequest('list "composer" "date" "2001"')
        self.assertInResponse('OK')

    def test_list_composer_by_genre(self):
        self.sendRequest('list "composer" "genre" "agenre"')
        self.assertInResponse('OK')

    def test_list_composer_by_artist_and_album(self):
        self.sendRequest(
            'list "composer" "artist" "anartist" "album" "analbum"')
        self.assertInResponse('OK')

    def test_list_composer_without_filter_value(self):
        self.sendRequest('list "composer" "artist" ""')
        self.assertInResponse('OK')

    def test_list_composer_should_not_return_artists_without_names(self):
        self.backend.library.dummy_find_exact_result = SearchResult(
            tracks=[Track(composers=[Artist(name='')])])

        self.sendRequest('list "composer"')
        self.assertNotInResponse('Artist: ')
        self.assertNotInResponse('Albumartist: ')
        self.assertNotInResponse('Composer: ')
        self.assertNotInResponse('Performer: ')
        self.assertInResponse('OK')

    # Performer

    def test_list_performer_with_quotes(self):
        self.sendRequest('list "performer"')
        self.assertInResponse('OK')

    def test_list_performer_without_quotes(self):
        self.sendRequest('list performer')
        self.assertInResponse('OK')

    def test_list_performer_without_quotes_and_capitalized(self):
        self.sendRequest('list Albumartist')
        self.assertInResponse('OK')

    def test_list_performer_with_query_of_one_token(self):
        self.sendRequest('list "performer" "anartist"')
        self.assertEqualResponse(
            'ACK [2@0] {list} should be "Album" for 3 arguments')

    def test_list_performer_with_unknown_field_in_query_returns_ack(self):
        self.sendRequest('list "performer" "foo" "bar"')
        self.assertEqualResponse('ACK [2@0] {list} not able to parse args')

    def test_list_performer_by_artist(self):
        self.sendRequest('list "performer" "artist" "anartist"')
        self.assertInResponse('OK')

    def test_list_performer_by_album(self):
        self.sendRequest('list "performer" "album" "analbum"')
        self.assertInResponse('OK')

    def test_list_performer_by_full_date(self):
        self.sendRequest('list "performer" "date" "2001-01-01"')
        self.assertInResponse('OK')

    def test_list_performer_by_year(self):
        self.sendRequest('list "performer" "date" "2001"')
        self.assertInResponse('OK')

    def test_list_performer_by_genre(self):
        self.sendRequest('list "performer" "genre" "agenre"')
        self.assertInResponse('OK')

    def test_list_performer_by_artist_and_album(self):
        self.sendRequest(
            'list "performer" "artist" "anartist" "album" "analbum"')
        self.assertInResponse('OK')

    def test_list_performer_without_filter_value(self):
        self.sendRequest('list "performer" "artist" ""')
        self.assertInResponse('OK')

    def test_list_performer_should_not_return_artists_without_names(self):
        self.backend.library.dummy_find_exact_result = SearchResult(
            tracks=[Track(performers=[Artist(name='')])])

        self.sendRequest('list "performer"')
        self.assertNotInResponse('Artist: ')
        self.assertNotInResponse('Albumartist: ')
        self.assertNotInResponse('Composer: ')
        self.assertNotInResponse('Performer: ')
        self.assertInResponse('OK')

    # Album

    def test_list_album_with_quotes(self):
        self.sendRequest('list "album"')
        self.assertInResponse('OK')

    def test_list_album_without_quotes(self):
        self.sendRequest('list album')
        self.assertInResponse('OK')

    def test_list_album_without_quotes_and_capitalized(self):
        self.sendRequest('list Album')
        self.assertInResponse('OK')

    def test_list_album_with_artist_name(self):
        self.sendRequest('list "album" "anartist"')
        self.assertInResponse('OK')

    def test_list_album_with_artist_name_without_filter_value(self):
        self.sendRequest('list "album" ""')
        self.assertInResponse('OK')

    def test_list_album_by_artist(self):
        self.sendRequest('list "album" "artist" "anartist"')
        self.assertInResponse('OK')

    def test_list_album_by_album(self):
        self.sendRequest('list "album" "album" "analbum"')
        self.assertInResponse('OK')

    def test_list_album_by_albumartist(self):
        self.sendRequest('list "album" "albumartist" "anartist"')
        self.assertInResponse('OK')

    def test_list_album_by_composer(self):
        self.sendRequest('list "album" "composer" "anartist"')
        self.assertInResponse('OK')

    def test_list_album_by_performer(self):
        self.sendRequest('list "album" "performer" "anartist"')
        self.assertInResponse('OK')

    def test_list_album_by_full_date(self):
        self.sendRequest('list "album" "date" "2001-01-01"')
        self.assertInResponse('OK')

    def test_list_album_by_year(self):
        self.sendRequest('list "album" "date" "2001"')
        self.assertInResponse('OK')

    def test_list_album_by_genre(self):
        self.sendRequest('list "album" "genre" "agenre"')
        self.assertInResponse('OK')

    def test_list_album_by_artist_and_album(self):
        self.sendRequest(
            'list "album" "artist" "anartist" "album" "analbum"')
        self.assertInResponse('OK')

    def test_list_album_without_filter_value(self):
        self.sendRequest('list "album" "artist" ""')
        self.assertInResponse('OK')

    def test_list_album_should_not_return_albums_without_names(self):
        self.backend.library.dummy_find_exact_result = SearchResult(
            tracks=[Track(album=Album(name=''))])

        self.sendRequest('list "album"')
        self.assertNotInResponse('Album: ')
        self.assertInResponse('OK')

    # Date

    def test_list_date_with_quotes(self):
        self.sendRequest('list "date"')
        self.assertInResponse('OK')

    def test_list_date_without_quotes(self):
        self.sendRequest('list date')
        self.assertInResponse('OK')

    def test_list_date_without_quotes_and_capitalized(self):
        self.sendRequest('list Date')
        self.assertInResponse('OK')

    def test_list_date_with_query_of_one_token(self):
        self.sendRequest('list "date" "anartist"')
        self.assertEqualResponse(
            'ACK [2@0] {list} should be "Album" for 3 arguments')

    def test_list_date_by_artist(self):
        self.sendRequest('list "date" "artist" "anartist"')
        self.assertInResponse('OK')

    def test_list_date_by_album(self):
        self.sendRequest('list "date" "album" "analbum"')
        self.assertInResponse('OK')

    def test_list_date_by_full_date(self):
        self.sendRequest('list "date" "date" "2001-01-01"')
        self.assertInResponse('OK')

    def test_list_date_by_year(self):
        self.sendRequest('list "date" "date" "2001"')
        self.assertInResponse('OK')

    def test_list_date_by_genre(self):
        self.sendRequest('list "date" "genre" "agenre"')
        self.assertInResponse('OK')

    def test_list_date_by_artist_and_album(self):
        self.sendRequest('list "date" "artist" "anartist" "album" "analbum"')
        self.assertInResponse('OK')

    def test_list_date_without_filter_value(self):
        self.sendRequest('list "date" "artist" ""')
        self.assertInResponse('OK')

    def test_list_date_should_not_return_blank_dates(self):
        self.backend.library.dummy_find_exact_result = SearchResult(
            tracks=[Track(date='')])

        self.sendRequest('list "date"')
        self.assertNotInResponse('Date: ')
        self.assertInResponse('OK')

    # Genre

    def test_list_genre_with_quotes(self):
        self.sendRequest('list "genre"')
        self.assertInResponse('OK')

    def test_list_genre_without_quotes(self):
        self.sendRequest('list genre')
        self.assertInResponse('OK')

    def test_list_genre_without_quotes_and_capitalized(self):
        self.sendRequest('list Genre')
        self.assertInResponse('OK')

    def test_list_genre_with_query_of_one_token(self):
        self.sendRequest('list "genre" "anartist"')
        self.assertEqualResponse(
            'ACK [2@0] {list} should be "Album" for 3 arguments')

    def test_list_genre_by_artist(self):
        self.sendRequest('list "genre" "artist" "anartist"')
        self.assertInResponse('OK')

    def test_list_genre_by_album(self):
        self.sendRequest('list "genre" "album" "analbum"')
        self.assertInResponse('OK')

    def test_list_genre_by_full_date(self):
        self.sendRequest('list "genre" "date" "2001-01-01"')
        self.assertInResponse('OK')

    def test_list_genre_by_year(self):
        self.sendRequest('list "genre" "date" "2001"')
        self.assertInResponse('OK')

    def test_list_genre_by_genre(self):
        self.sendRequest('list "genre" "genre" "agenre"')
        self.assertInResponse('OK')

    def test_list_genre_by_artist_and_album(self):
        self.sendRequest(
            'list "genre" "artist" "anartist" "album" "analbum"')
        self.assertInResponse('OK')

    def test_list_genre_without_filter_value(self):
        self.sendRequest('list "genre" "artist" ""')
        self.assertInResponse('OK')


class MusicDatabaseSearchTest(protocol.BaseTestCase):
    def test_search(self):
        self.backend.library.dummy_search_result = SearchResult(
            albums=[Album(uri='dummy:album:a', name='A')],
            artists=[Artist(uri='dummy:artist:b', name='B')],
            tracks=[Track(uri='dummy:track:c', name='C')])

        self.sendRequest('search "any" "foo"')

        self.assertInResponse('file: dummy:album:a')
        self.assertInResponse('Title: Album: A')
        self.assertInResponse('file: dummy:artist:b')
        self.assertInResponse('Title: Artist: B')
        self.assertInResponse('file: dummy:track:c')
        self.assertInResponse('Title: C')

        self.assertInResponse('OK')

    def test_search_album(self):
        self.sendRequest('search "album" "analbum"')
        self.assertInResponse('OK')

    def test_search_album_without_quotes(self):
        self.sendRequest('search album "analbum"')
        self.assertInResponse('OK')

    def test_search_album_without_filter_value(self):
        self.sendRequest('search "album" ""')
        self.assertInResponse('OK')

    def test_search_artist(self):
        self.sendRequest('search "artist" "anartist"')
        self.assertInResponse('OK')

    def test_search_artist_without_quotes(self):
        self.sendRequest('search artist "anartist"')
        self.assertInResponse('OK')

    def test_search_artist_without_filter_value(self):
        self.sendRequest('search "artist" ""')
        self.assertInResponse('OK')

    def test_search_albumartist(self):
        self.sendRequest('search "albumartist" "analbumartist"')
        self.assertInResponse('OK')

    def test_search_albumartist_without_quotes(self):
        self.sendRequest('search albumartist "analbumartist"')
        self.assertInResponse('OK')

    def test_search_albumartist_without_filter_value(self):
        self.sendRequest('search "albumartist" ""')
        self.assertInResponse('OK')

    def test_search_composer(self):
        self.sendRequest('search "composer" "acomposer"')
        self.assertInResponse('OK')

    def test_search_composer_without_quotes(self):
        self.sendRequest('search composer "acomposer"')
        self.assertInResponse('OK')

    def test_search_composer_without_filter_value(self):
        self.sendRequest('search "composer" ""')
        self.assertInResponse('OK')

    def test_search_performer(self):
        self.sendRequest('search "performer" "aperformer"')
        self.assertInResponse('OK')

    def test_search_performer_without_quotes(self):
        self.sendRequest('search performer "aperformer"')
        self.assertInResponse('OK')

    def test_search_performer_without_filter_value(self):
        self.sendRequest('search "performer" ""')
        self.assertInResponse('OK')

    def test_search_filename(self):
        self.sendRequest('search "filename" "afilename"')
        self.assertInResponse('OK')

    def test_search_filename_without_quotes(self):
        self.sendRequest('search filename "afilename"')
        self.assertInResponse('OK')

    def test_search_filename_without_filter_value(self):
        self.sendRequest('search "filename" ""')
        self.assertInResponse('OK')

    def test_search_file(self):
        self.sendRequest('search "file" "afilename"')
        self.assertInResponse('OK')

    def test_search_file_without_quotes(self):
        self.sendRequest('search file "afilename"')
        self.assertInResponse('OK')

    def test_search_file_without_filter_value(self):
        self.sendRequest('search "file" ""')
        self.assertInResponse('OK')

    def test_search_title(self):
        self.sendRequest('search "title" "atitle"')
        self.assertInResponse('OK')

    def test_search_title_without_quotes(self):
        self.sendRequest('search title "atitle"')
        self.assertInResponse('OK')

    def test_search_title_without_filter_value(self):
        self.sendRequest('search "title" ""')
        self.assertInResponse('OK')

    def test_search_any(self):
        self.sendRequest('search "any" "anything"')
        self.assertInResponse('OK')

    def test_search_any_without_quotes(self):
        self.sendRequest('search any "anything"')
        self.assertInResponse('OK')

    def test_search_any_without_filter_value(self):
        self.sendRequest('search "any" ""')
        self.assertInResponse('OK')

    def test_search_track_no(self):
        self.sendRequest('search "track" "10"')
        self.assertInResponse('OK')

    def test_search_track_no_without_quotes(self):
        self.sendRequest('search track "10"')
        self.assertInResponse('OK')

    def test_search_track_no_without_filter_value(self):
        self.sendRequest('search "track" ""')
        self.assertInResponse('OK')

    def test_search_genre(self):
        self.sendRequest('search "genre" "agenre"')
        self.assertInResponse('OK')

    def test_search_genre_without_quotes(self):
        self.sendRequest('search genre "agenre"')
        self.assertInResponse('OK')

    def test_search_genre_without_filter_value(self):
        self.sendRequest('search "genre" ""')
        self.assertInResponse('OK')

    def test_search_date(self):
        self.sendRequest('search "date" "2002-01-01"')
        self.assertInResponse('OK')

    def test_search_date_without_quotes(self):
        self.sendRequest('search date "2002-01-01"')
        self.assertInResponse('OK')

    def test_search_date_with_capital_d_and_incomplete_date(self):
        self.sendRequest('search Date "2005"')
        self.assertInResponse('OK')

    def test_search_date_without_filter_value(self):
        self.sendRequest('search "date" ""')
        self.assertInResponse('OK')

    def test_search_comment(self):
        self.sendRequest('search "comment" "acomment"')
        self.assertInResponse('OK')

    def test_search_comment_without_quotes(self):
        self.sendRequest('search comment "acomment"')
        self.assertInResponse('OK')

    def test_search_comment_without_filter_value(self):
        self.sendRequest('search "comment" ""')
        self.assertInResponse('OK')

    def test_search_else_should_fail(self):
        self.sendRequest('search "sometype" "something"')
        self.assertEqualResponse('ACK [2@0] {search} incorrect arguments')

########NEW FILE########
__FILENAME__ = test_playback
from __future__ import unicode_literals

import unittest

from mopidy.core import PlaybackState
from mopidy.models import Track

from tests.mpd import protocol


PAUSED = PlaybackState.PAUSED
PLAYING = PlaybackState.PLAYING
STOPPED = PlaybackState.STOPPED


class PlaybackOptionsHandlerTest(protocol.BaseTestCase):
    def test_consume_off(self):
        self.sendRequest('consume "0"')
        self.assertFalse(self.core.tracklist.consume.get())
        self.assertInResponse('OK')

    def test_consume_off_without_quotes(self):
        self.sendRequest('consume 0')
        self.assertFalse(self.core.tracklist.consume.get())
        self.assertInResponse('OK')

    def test_consume_on(self):
        self.sendRequest('consume "1"')
        self.assertTrue(self.core.tracklist.consume.get())
        self.assertInResponse('OK')

    def test_consume_on_without_quotes(self):
        self.sendRequest('consume 1')
        self.assertTrue(self.core.tracklist.consume.get())
        self.assertInResponse('OK')

    def test_crossfade(self):
        self.sendRequest('crossfade "10"')
        self.assertInResponse('ACK [0@0] {crossfade} Not implemented')

    def test_random_off(self):
        self.sendRequest('random "0"')
        self.assertFalse(self.core.tracklist.random.get())
        self.assertInResponse('OK')

    def test_random_off_without_quotes(self):
        self.sendRequest('random 0')
        self.assertFalse(self.core.tracklist.random.get())
        self.assertInResponse('OK')

    def test_random_on(self):
        self.sendRequest('random "1"')
        self.assertTrue(self.core.tracklist.random.get())
        self.assertInResponse('OK')

    def test_random_on_without_quotes(self):
        self.sendRequest('random 1')
        self.assertTrue(self.core.tracklist.random.get())
        self.assertInResponse('OK')

    def test_repeat_off(self):
        self.sendRequest('repeat "0"')
        self.assertFalse(self.core.tracklist.repeat.get())
        self.assertInResponse('OK')

    def test_repeat_off_without_quotes(self):
        self.sendRequest('repeat 0')
        self.assertFalse(self.core.tracklist.repeat.get())
        self.assertInResponse('OK')

    def test_repeat_on(self):
        self.sendRequest('repeat "1"')
        self.assertTrue(self.core.tracklist.repeat.get())
        self.assertInResponse('OK')

    def test_repeat_on_without_quotes(self):
        self.sendRequest('repeat 1')
        self.assertTrue(self.core.tracklist.repeat.get())
        self.assertInResponse('OK')

    def test_setvol_below_min(self):
        self.sendRequest('setvol "-10"')
        self.assertEqual(0, self.core.playback.volume.get())
        self.assertInResponse('OK')

    def test_setvol_min(self):
        self.sendRequest('setvol "0"')
        self.assertEqual(0, self.core.playback.volume.get())
        self.assertInResponse('OK')

    def test_setvol_middle(self):
        self.sendRequest('setvol "50"')
        self.assertEqual(50, self.core.playback.volume.get())
        self.assertInResponse('OK')

    def test_setvol_max(self):
        self.sendRequest('setvol "100"')
        self.assertEqual(100, self.core.playback.volume.get())
        self.assertInResponse('OK')

    def test_setvol_above_max(self):
        self.sendRequest('setvol "110"')
        self.assertEqual(100, self.core.playback.volume.get())
        self.assertInResponse('OK')

    def test_setvol_plus_is_ignored(self):
        self.sendRequest('setvol "+10"')
        self.assertEqual(10, self.core.playback.volume.get())
        self.assertInResponse('OK')

    def test_setvol_without_quotes(self):
        self.sendRequest('setvol 50')
        self.assertEqual(50, self.core.playback.volume.get())
        self.assertInResponse('OK')

    def test_single_off(self):
        self.sendRequest('single "0"')
        self.assertFalse(self.core.tracklist.single.get())
        self.assertInResponse('OK')

    def test_single_off_without_quotes(self):
        self.sendRequest('single 0')
        self.assertFalse(self.core.tracklist.single.get())
        self.assertInResponse('OK')

    def test_single_on(self):
        self.sendRequest('single "1"')
        self.assertTrue(self.core.tracklist.single.get())
        self.assertInResponse('OK')

    def test_single_on_without_quotes(self):
        self.sendRequest('single 1')
        self.assertTrue(self.core.tracklist.single.get())
        self.assertInResponse('OK')

    def test_replay_gain_mode_off(self):
        self.sendRequest('replay_gain_mode "off"')
        self.assertInResponse('ACK [0@0] {replay_gain_mode} Not implemented')

    def test_replay_gain_mode_track(self):
        self.sendRequest('replay_gain_mode "track"')
        self.assertInResponse('ACK [0@0] {replay_gain_mode} Not implemented')

    def test_replay_gain_mode_album(self):
        self.sendRequest('replay_gain_mode "album"')
        self.assertInResponse('ACK [0@0] {replay_gain_mode} Not implemented')

    def test_replay_gain_status_default(self):
        self.sendRequest('replay_gain_status')
        self.assertInResponse('OK')
        self.assertInResponse('off')

    @unittest.SkipTest
    def test_replay_gain_status_off(self):
        pass

    @unittest.SkipTest
    def test_replay_gain_status_track(self):
        pass

    @unittest.SkipTest
    def test_replay_gain_status_album(self):
        pass


class PlaybackControlHandlerTest(protocol.BaseTestCase):
    def test_next(self):
        self.sendRequest('next')
        self.assertInResponse('OK')

    def test_pause_off(self):
        self.core.tracklist.add([Track(uri='dummy:a')])

        self.sendRequest('play "0"')
        self.sendRequest('pause "1"')
        self.sendRequest('pause "0"')
        self.assertEqual(PLAYING, self.core.playback.state.get())
        self.assertInResponse('OK')

    def test_pause_on(self):
        self.core.tracklist.add([Track(uri='dummy:a')])

        self.sendRequest('play "0"')
        self.sendRequest('pause "1"')
        self.assertEqual(PAUSED, self.core.playback.state.get())
        self.assertInResponse('OK')

    def test_pause_toggle(self):
        self.core.tracklist.add([Track(uri='dummy:a')])

        self.sendRequest('play "0"')
        self.assertEqual(PLAYING, self.core.playback.state.get())
        self.assertInResponse('OK')

        self.sendRequest('pause')
        self.assertEqual(PAUSED, self.core.playback.state.get())
        self.assertInResponse('OK')

        self.sendRequest('pause')
        self.assertEqual(PLAYING, self.core.playback.state.get())
        self.assertInResponse('OK')

    def test_play_without_pos(self):
        self.core.tracklist.add([Track(uri='dummy:a')])

        self.sendRequest('play')
        self.assertEqual(PLAYING, self.core.playback.state.get())
        self.assertInResponse('OK')

    def test_play_with_pos(self):
        self.core.tracklist.add([Track(uri='dummy:a')])

        self.sendRequest('play "0"')
        self.assertEqual(PLAYING, self.core.playback.state.get())
        self.assertInResponse('OK')

    def test_play_with_pos_without_quotes(self):
        self.core.tracklist.add([Track(uri='dummy:a')])

        self.sendRequest('play 0')
        self.assertEqual(PLAYING, self.core.playback.state.get())
        self.assertInResponse('OK')

    def test_play_with_pos_out_of_bounds(self):
        self.core.tracklist.add([])

        self.sendRequest('play "0"')
        self.assertEqual(STOPPED, self.core.playback.state.get())
        self.assertInResponse('ACK [2@0] {play} Bad song index')

    def test_play_minus_one_plays_first_in_playlist_if_no_current_track(self):
        self.assertEqual(self.core.playback.current_track.get(), None)
        self.core.tracklist.add([Track(uri='dummy:a'), Track(uri='dummy:b')])

        self.sendRequest('play "-1"')
        self.assertEqual(PLAYING, self.core.playback.state.get())
        self.assertEqual(
            'dummy:a', self.core.playback.current_track.get().uri)
        self.assertInResponse('OK')

    def test_play_minus_one_plays_current_track_if_current_track_is_set(self):
        self.core.tracklist.add([Track(uri='dummy:a'), Track(uri='dummy:b')])
        self.assertEqual(self.core.playback.current_track.get(), None)
        self.core.playback.play()
        self.core.playback.next()
        self.core.playback.stop()
        self.assertNotEqual(self.core.playback.current_track.get(), None)

        self.sendRequest('play "-1"')
        self.assertEqual(PLAYING, self.core.playback.state.get())
        self.assertEqual(
            'dummy:b', self.core.playback.current_track.get().uri)
        self.assertInResponse('OK')

    def test_play_minus_one_on_empty_playlist_does_not_ack(self):
        self.core.tracklist.clear()

        self.sendRequest('play "-1"')
        self.assertEqual(STOPPED, self.core.playback.state.get())
        self.assertEqual(None, self.core.playback.current_track.get())
        self.assertInResponse('OK')

    def test_play_minus_is_ignored_if_playing(self):
        self.core.tracklist.add([Track(uri='dummy:a', length=40000)])
        self.core.playback.seek(30000)
        self.assertGreaterEqual(
            self.core.playback.time_position.get(), 30000)
        self.assertEquals(PLAYING, self.core.playback.state.get())

        self.sendRequest('play "-1"')
        self.assertEqual(PLAYING, self.core.playback.state.get())
        self.assertGreaterEqual(
            self.core.playback.time_position.get(), 30000)
        self.assertInResponse('OK')

    def test_play_minus_one_resumes_if_paused(self):
        self.core.tracklist.add([Track(uri='dummy:a', length=40000)])
        self.core.playback.seek(30000)
        self.assertGreaterEqual(
            self.core.playback.time_position.get(), 30000)
        self.assertEquals(PLAYING, self.core.playback.state.get())
        self.core.playback.pause()
        self.assertEquals(PAUSED, self.core.playback.state.get())

        self.sendRequest('play "-1"')
        self.assertEqual(PLAYING, self.core.playback.state.get())
        self.assertGreaterEqual(
            self.core.playback.time_position.get(), 30000)
        self.assertInResponse('OK')

    def test_playid(self):
        self.core.tracklist.add([Track(uri='dummy:a')])

        self.sendRequest('playid "0"')
        self.assertEqual(PLAYING, self.core.playback.state.get())
        self.assertInResponse('OK')

    def test_playid_without_quotes(self):
        self.core.tracklist.add([Track(uri='dummy:a')])

        self.sendRequest('playid 0')
        self.assertEqual(PLAYING, self.core.playback.state.get())
        self.assertInResponse('OK')

    def test_playid_minus_1_plays_first_in_playlist_if_no_current_track(self):
        self.assertEqual(self.core.playback.current_track.get(), None)
        self.core.tracklist.add([Track(uri='dummy:a'), Track(uri='dummy:b')])

        self.sendRequest('playid "-1"')
        self.assertEqual(PLAYING, self.core.playback.state.get())
        self.assertEqual(
            'dummy:a', self.core.playback.current_track.get().uri)
        self.assertInResponse('OK')

    def test_playid_minus_1_plays_current_track_if_current_track_is_set(self):
        self.core.tracklist.add([Track(uri='dummy:a'), Track(uri='dummy:b')])
        self.assertEqual(self.core.playback.current_track.get(), None)
        self.core.playback.play()
        self.core.playback.next()
        self.core.playback.stop()
        self.assertNotEqual(None, self.core.playback.current_track.get())

        self.sendRequest('playid "-1"')
        self.assertEqual(PLAYING, self.core.playback.state.get())
        self.assertEqual(
            'dummy:b', self.core.playback.current_track.get().uri)
        self.assertInResponse('OK')

    def test_playid_minus_one_on_empty_playlist_does_not_ack(self):
        self.core.tracklist.clear()

        self.sendRequest('playid "-1"')
        self.assertEqual(STOPPED, self.core.playback.state.get())
        self.assertEqual(None, self.core.playback.current_track.get())
        self.assertInResponse('OK')

    def test_playid_minus_is_ignored_if_playing(self):
        self.core.tracklist.add([Track(uri='dummy:a', length=40000)])
        self.core.playback.seek(30000)
        self.assertGreaterEqual(
            self.core.playback.time_position.get(), 30000)
        self.assertEquals(PLAYING, self.core.playback.state.get())

        self.sendRequest('playid "-1"')
        self.assertEqual(PLAYING, self.core.playback.state.get())
        self.assertGreaterEqual(
            self.core.playback.time_position.get(), 30000)
        self.assertInResponse('OK')

    def test_playid_minus_one_resumes_if_paused(self):
        self.core.tracklist.add([Track(uri='dummy:a', length=40000)])
        self.core.playback.seek(30000)
        self.assertGreaterEqual(
            self.core.playback.time_position.get(), 30000)
        self.assertEquals(PLAYING, self.core.playback.state.get())
        self.core.playback.pause()
        self.assertEquals(PAUSED, self.core.playback.state.get())

        self.sendRequest('playid "-1"')
        self.assertEqual(PLAYING, self.core.playback.state.get())
        self.assertGreaterEqual(
            self.core.playback.time_position.get(), 30000)
        self.assertInResponse('OK')

    def test_playid_which_does_not_exist(self):
        self.core.tracklist.add([Track(uri='dummy:a')])

        self.sendRequest('playid "12345"')
        self.assertInResponse('ACK [50@0] {playid} No such song')

    def test_previous(self):
        self.sendRequest('previous')
        self.assertInResponse('OK')

    def test_seek_in_current_track(self):
        seek_track = Track(uri='dummy:a', length=40000)
        self.core.tracklist.add([seek_track])
        self.core.playback.play()

        self.sendRequest('seek "0" "30"')

        self.assertEqual(self.core.playback.current_track.get(), seek_track)
        self.assertGreaterEqual(self.core.playback.time_position, 30000)
        self.assertInResponse('OK')

    def test_seek_in_another_track(self):
        seek_track = Track(uri='dummy:b', length=40000)
        self.core.tracklist.add(
            [Track(uri='dummy:a', length=40000), seek_track])
        self.core.playback.play()
        self.assertNotEqual(self.core.playback.current_track.get(), seek_track)

        self.sendRequest('seek "1" "30"')

        self.assertEqual(self.core.playback.current_track.get(), seek_track)
        self.assertInResponse('OK')

    def test_seek_without_quotes(self):
        self.core.tracklist.add([Track(uri='dummy:a', length=40000)])
        self.core.playback.play()

        self.sendRequest('seek 0 30')
        self.assertGreaterEqual(
            self.core.playback.time_position.get(), 30000)
        self.assertInResponse('OK')

    def test_seekid_in_current_track(self):
        seek_track = Track(uri='dummy:a', length=40000)
        self.core.tracklist.add([seek_track])
        self.core.playback.play()

        self.sendRequest('seekid "0" "30"')

        self.assertEqual(self.core.playback.current_track.get(), seek_track)
        self.assertGreaterEqual(
            self.core.playback.time_position.get(), 30000)
        self.assertInResponse('OK')

    def test_seekid_in_another_track(self):
        seek_track = Track(uri='dummy:b', length=40000)
        self.core.tracklist.add(
            [Track(uri='dummy:a', length=40000), seek_track])
        self.core.playback.play()

        self.sendRequest('seekid "1" "30"')

        self.assertEqual(1, self.core.playback.current_tl_track.get().tlid)
        self.assertEqual(seek_track, self.core.playback.current_track.get())
        self.assertInResponse('OK')

    def test_seekcur_absolute_value(self):
        self.core.tracklist.add([Track(uri='dummy:a', length=40000)])
        self.core.playback.play()

        self.sendRequest('seekcur "30"')

        self.assertGreaterEqual(self.core.playback.time_position.get(), 30000)
        self.assertInResponse('OK')

    def test_seekcur_positive_diff(self):
        self.core.tracklist.add([Track(uri='dummy:a', length=40000)])
        self.core.playback.play()
        self.core.playback.seek(10000)
        self.assertGreaterEqual(self.core.playback.time_position.get(), 10000)

        self.sendRequest('seekcur "+20"')

        self.assertGreaterEqual(self.core.playback.time_position.get(), 30000)
        self.assertInResponse('OK')

    def test_seekcur_negative_diff(self):
        self.core.tracklist.add([Track(uri='dummy:a', length=40000)])
        self.core.playback.play()
        self.core.playback.seek(30000)
        self.assertGreaterEqual(self.core.playback.time_position.get(), 30000)

        self.sendRequest('seekcur "-20"')

        self.assertLessEqual(self.core.playback.time_position.get(), 15000)
        self.assertInResponse('OK')

    def test_stop(self):
        self.sendRequest('stop')
        self.assertEqual(STOPPED, self.core.playback.state.get())
        self.assertInResponse('OK')

########NEW FILE########
__FILENAME__ = test_reflection
from __future__ import unicode_literals

from tests.mpd import protocol


class ReflectionHandlerTest(protocol.BaseTestCase):
    def test_config_is_not_allowed_across_the_network(self):
        self.sendRequest('config')
        self.assertEqualResponse(
            'ACK [4@0] {config} you don\'t have permission for "config"')

    def test_commands_returns_list_of_all_commands(self):
        self.sendRequest('commands')
        # Check if some random commands are included
        self.assertInResponse('command: commands')
        self.assertInResponse('command: play')
        self.assertInResponse('command: status')
        # Check if commands you do not have access to are not present
        self.assertNotInResponse('command: config')
        self.assertNotInResponse('command: kill')
        # Check if the blacklisted commands are not present
        self.assertNotInResponse('command: command_list_begin')
        self.assertNotInResponse('command: command_list_ok_begin')
        self.assertNotInResponse('command: command_list_end')
        self.assertNotInResponse('command: idle')
        self.assertNotInResponse('command: noidle')
        self.assertNotInResponse('command: sticker')
        self.assertInResponse('OK')

    def test_decoders(self):
        self.sendRequest('decoders')
        self.assertInResponse('OK')

    def test_notcommands_returns_only_config_and_kill_and_ok(self):
        response = self.sendRequest('notcommands')
        self.assertEqual(3, len(response))
        self.assertInResponse('command: config')
        self.assertInResponse('command: kill')
        self.assertInResponse('OK')

    def test_tagtypes(self):
        self.sendRequest('tagtypes')
        self.assertInResponse('OK')

    def test_urlhandlers(self):
        self.sendRequest('urlhandlers')
        self.assertInResponse('OK')
        self.assertInResponse('handler: dummy')


class ReflectionWhenNotAuthedTest(protocol.BaseTestCase):
    def get_config(self):
        config = super(ReflectionWhenNotAuthedTest, self).get_config()
        config['mpd']['password'] = 'topsecret'
        return config

    def test_commands_show_less_if_auth_required_and_not_authed(self):
        self.sendRequest('commands')
        # Not requiring auth
        self.assertInResponse('command: close')
        self.assertInResponse('command: commands')
        self.assertInResponse('command: notcommands')
        self.assertInResponse('command: password')
        self.assertInResponse('command: ping')
        # Requiring auth
        self.assertNotInResponse('command: play')
        self.assertNotInResponse('command: status')

    def test_notcommands_returns_more_if_auth_required_and_not_authed(self):
        self.sendRequest('notcommands')
        # Not requiring auth
        self.assertNotInResponse('command: close')
        self.assertNotInResponse('command: commands')
        self.assertNotInResponse('command: notcommands')
        self.assertNotInResponse('command: password')
        self.assertNotInResponse('command: ping')
        # Requiring auth
        self.assertInResponse('command: play')
        self.assertInResponse('command: status')

########NEW FILE########
__FILENAME__ = test_regression
from __future__ import unicode_literals

import random

from mopidy.models import Track

from tests.mpd import protocol


class IssueGH17RegressionTest(protocol.BaseTestCase):
    """
    The issue: http://github.com/mopidy/mopidy/issues/17

    How to reproduce:

    - Play a playlist where one track cannot be played
    - Turn on random mode
    - Press next until you get to the unplayable track
    """
    def test(self):
        self.core.tracklist.add([
            Track(uri='dummy:a'),
            Track(uri='dummy:b'),
            Track(uri='dummy:error'),
            Track(uri='dummy:d'),
            Track(uri='dummy:e'),
            Track(uri='dummy:f'),
        ])
        random.seed(1)  # Playlist order: abcfde

        self.sendRequest('play')
        self.assertEquals(
            'dummy:a', self.core.playback.current_track.get().uri)
        self.sendRequest('random "1"')
        self.sendRequest('next')
        self.assertEquals(
            'dummy:b', self.core.playback.current_track.get().uri)
        self.sendRequest('next')
        # Should now be at track 'c', but playback fails and it skips ahead
        self.assertEquals(
            'dummy:f', self.core.playback.current_track.get().uri)
        self.sendRequest('next')
        self.assertEquals(
            'dummy:d', self.core.playback.current_track.get().uri)
        self.sendRequest('next')
        self.assertEquals(
            'dummy:e', self.core.playback.current_track.get().uri)


class IssueGH18RegressionTest(protocol.BaseTestCase):
    """
    The issue: http://github.com/mopidy/mopidy/issues/18

    How to reproduce:

        Play, random on, next, random off, next, next.

        At this point it gives the same song over and over.
    """

    def test(self):
        self.core.tracklist.add([
            Track(uri='dummy:a'), Track(uri='dummy:b'), Track(uri='dummy:c'),
            Track(uri='dummy:d'), Track(uri='dummy:e'), Track(uri='dummy:f')])
        random.seed(1)

        self.sendRequest('play')
        self.sendRequest('random "1"')
        self.sendRequest('next')
        self.sendRequest('random "0"')
        self.sendRequest('next')

        self.sendRequest('next')
        tl_track_1 = self.core.playback.current_tl_track.get()
        self.sendRequest('next')
        tl_track_2 = self.core.playback.current_tl_track.get()
        self.sendRequest('next')
        tl_track_3 = self.core.playback.current_tl_track.get()

        self.assertNotEqual(tl_track_1, tl_track_2)
        self.assertNotEqual(tl_track_2, tl_track_3)


class IssueGH22RegressionTest(protocol.BaseTestCase):
    """
    The issue: http://github.com/mopidy/mopidy/issues/22

    How to reproduce:

        Play, random on, remove all tracks from the current playlist (as in
        "delete" each one, not "clear").

        Alternatively: Play, random on, remove a random track from the current
        playlist, press next until it crashes.
    """

    def test(self):
        self.core.tracklist.add([
            Track(uri='dummy:a'), Track(uri='dummy:b'), Track(uri='dummy:c'),
            Track(uri='dummy:d'), Track(uri='dummy:e'), Track(uri='dummy:f')])
        random.seed(1)

        self.sendRequest('play')
        self.sendRequest('random "1"')
        self.sendRequest('deleteid "1"')
        self.sendRequest('deleteid "2"')
        self.sendRequest('deleteid "3"')
        self.sendRequest('deleteid "4"')
        self.sendRequest('deleteid "5"')
        self.sendRequest('deleteid "6"')
        self.sendRequest('status')


class IssueGH69RegressionTest(protocol.BaseTestCase):
    """
    The issue: https://github.com/mopidy/mopidy/issues/69

    How to reproduce:

        Play track, stop, clear current playlist, load a new playlist, status.

        The status response now contains "song: None".
    """

    def test(self):
        self.core.playlists.create('foo')
        self.core.tracklist.add([
            Track(uri='dummy:a'), Track(uri='dummy:b'), Track(uri='dummy:c'),
            Track(uri='dummy:d'), Track(uri='dummy:e'), Track(uri='dummy:f')])

        self.sendRequest('play')
        self.sendRequest('stop')
        self.sendRequest('clear')
        self.sendRequest('load "foo"')
        self.assertNotInResponse('song: None')


class IssueGH113RegressionTest(protocol.BaseTestCase):
    """
    The issue: https://github.com/mopidy/mopidy/issues/113

    How to reproduce:

    - Have a playlist with a name contining backslashes, like
      "all lart spotify:track:\w\{22\} pastes".
    - Try to load the playlist with the backslashes in the playlist name
      escaped.
    """

    def test(self):
        self.core.playlists.create(
            u'all lart spotify:track:\w\{22\} pastes')

        self.sendRequest('lsinfo "/"')
        self.assertInResponse(
            u'playlist: all lart spotify:track:\w\{22\} pastes')

        self.sendRequest(
            r'listplaylistinfo "all lart spotify:track:\\w\\{22\\} pastes"')
        self.assertInResponse('OK')


class IssueGH137RegressionTest(protocol.BaseTestCase):
    """
    The issue: https://github.com/mopidy/mopidy/issues/137

    How to reproduce:

    - Send "list" query with mismatching quotes
    """

    def test(self):
        self.sendRequest(
            u'list Date Artist "Anita Ward" '
            u'Album "This Is Remixed Hits - Mashups & Rare 12" Mixes"')

        self.assertInResponse('ACK [2@0] {list} Invalid unquoted character')

########NEW FILE########
__FILENAME__ = test_status
from __future__ import unicode_literals

from mopidy.models import Track

from tests.mpd import protocol


class StatusHandlerTest(protocol.BaseTestCase):
    def test_clearerror(self):
        self.sendRequest('clearerror')
        self.assertEqualResponse('ACK [0@0] {clearerror} Not implemented')

    def test_currentsong(self):
        track = Track()
        self.core.tracklist.add([track])
        self.core.playback.play()
        self.sendRequest('currentsong')
        self.assertInResponse('file: ')
        self.assertInResponse('Time: 0')
        self.assertInResponse('Artist: ')
        self.assertInResponse('Title: ')
        self.assertInResponse('Album: ')
        self.assertInResponse('Track: 0')
        self.assertNotInResponse('Date: ')
        self.assertInResponse('Pos: 0')
        self.assertInResponse('Id: 0')
        self.assertInResponse('OK')

    def test_currentsong_without_song(self):
        self.sendRequest('currentsong')
        self.assertInResponse('OK')

    def test_stats_command(self):
        self.sendRequest('stats')
        self.assertInResponse('OK')

    def test_status_command(self):
        self.sendRequest('status')
        self.assertInResponse('OK')

########NEW FILE########
__FILENAME__ = test_stickers
from __future__ import unicode_literals

from tests.mpd import protocol


class StickersHandlerTest(protocol.BaseTestCase):
    def test_sticker_get(self):
        self.sendRequest(
            'sticker get "song" "file:///dev/urandom" "a_name"')
        self.assertEqualResponse('ACK [0@0] {sticker} Not implemented')

    def test_sticker_set(self):
        self.sendRequest(
            'sticker set "song" "file:///dev/urandom" "a_name" "a_value"')
        self.assertEqualResponse('ACK [0@0] {sticker} Not implemented')

    def test_sticker_delete_with_name(self):
        self.sendRequest(
            'sticker delete "song" "file:///dev/urandom" "a_name"')
        self.assertEqualResponse('ACK [0@0] {sticker} Not implemented')

    def test_sticker_delete_without_name(self):
        self.sendRequest(
            'sticker delete "song" "file:///dev/urandom"')
        self.assertEqualResponse('ACK [0@0] {sticker} Not implemented')

    def test_sticker_list(self):
        self.sendRequest(
            'sticker list "song" "file:///dev/urandom"')
        self.assertEqualResponse('ACK [0@0] {sticker} Not implemented')

    def test_sticker_find(self):
        self.sendRequest(
            'sticker find "song" "file:///dev/urandom" "a_name"')
        self.assertEqualResponse('ACK [0@0] {sticker} Not implemented')

########NEW FILE########
__FILENAME__ = test_stored_playlists
from __future__ import unicode_literals

from mopidy.models import Playlist, Track

from tests.mpd import protocol


class PlaylistsHandlerTest(protocol.BaseTestCase):
    def test_listplaylist(self):
        self.backend.playlists.playlists = [
            Playlist(
                name='name', uri='dummy:name', tracks=[Track(uri='dummy:a')])]

        self.sendRequest('listplaylist "name"')
        self.assertInResponse('file: dummy:a')
        self.assertInResponse('OK')

    def test_listplaylist_without_quotes(self):
        self.backend.playlists.playlists = [
            Playlist(
                name='name', uri='dummy:name', tracks=[Track(uri='dummy:a')])]

        self.sendRequest('listplaylist name')
        self.assertInResponse('file: dummy:a')
        self.assertInResponse('OK')

    def test_listplaylist_fails_if_no_playlist_is_found(self):
        self.sendRequest('listplaylist "name"')
        self.assertEqualResponse('ACK [50@0] {listplaylist} No such playlist')

    def test_listplaylist_duplicate(self):
        playlist1 = Playlist(name='a', uri='dummy:a1', tracks=[Track(uri='b')])
        playlist2 = Playlist(name='a', uri='dummy:a2', tracks=[Track(uri='c')])
        self.backend.playlists.playlists = [playlist1, playlist2]

        self.sendRequest('listplaylist "a [2]"')
        self.assertInResponse('file: c')
        self.assertInResponse('OK')

    def test_listplaylistinfo(self):
        self.backend.playlists.playlists = [
            Playlist(
                name='name', uri='dummy:name', tracks=[Track(uri='dummy:a')])]

        self.sendRequest('listplaylistinfo "name"')
        self.assertInResponse('file: dummy:a')
        self.assertInResponse('Track: 0')
        self.assertNotInResponse('Pos: 0')
        self.assertInResponse('OK')

    def test_listplaylistinfo_without_quotes(self):
        self.backend.playlists.playlists = [
            Playlist(
                name='name', uri='dummy:name', tracks=[Track(uri='dummy:a')])]

        self.sendRequest('listplaylistinfo name')
        self.assertInResponse('file: dummy:a')
        self.assertInResponse('Track: 0')
        self.assertNotInResponse('Pos: 0')
        self.assertInResponse('OK')

    def test_listplaylistinfo_fails_if_no_playlist_is_found(self):
        self.sendRequest('listplaylistinfo "name"')
        self.assertEqualResponse(
            'ACK [50@0] {listplaylistinfo} No such playlist')

    def test_listplaylistinfo_duplicate(self):
        playlist1 = Playlist(name='a', uri='dummy:a1', tracks=[Track(uri='b')])
        playlist2 = Playlist(name='a', uri='dummy:a2', tracks=[Track(uri='c')])
        self.backend.playlists.playlists = [playlist1, playlist2]

        self.sendRequest('listplaylistinfo "a [2]"')
        self.assertInResponse('file: c')
        self.assertInResponse('Track: 0')
        self.assertNotInResponse('Pos: 0')
        self.assertInResponse('OK')

    def test_listplaylists(self):
        last_modified = 1390942873222
        self.backend.playlists.playlists = [
            Playlist(name='a', uri='dummy:a', last_modified=last_modified)]

        self.sendRequest('listplaylists')
        self.assertInResponse('playlist: a')
        # Date without milliseconds and with time zone information
        self.assertInResponse('Last-Modified: 2014-01-28T21:01:13Z')
        self.assertInResponse('OK')

    def test_listplaylists_duplicate(self):
        playlist1 = Playlist(name='a', uri='dummy:a1')
        playlist2 = Playlist(name='a', uri='dummy:a2')
        self.backend.playlists.playlists = [playlist1, playlist2]

        self.sendRequest('listplaylists')
        self.assertInResponse('playlist: a')
        self.assertInResponse('playlist: a [2]')
        self.assertInResponse('OK')

    def test_listplaylists_ignores_playlists_without_name(self):
        last_modified = 1390942873222
        self.backend.playlists.playlists = [
            Playlist(name='', uri='dummy:', last_modified=last_modified)]

        self.sendRequest('listplaylists')
        self.assertNotInResponse('playlist: ')
        self.assertInResponse('OK')

    def test_listplaylists_replaces_newline_with_space(self):
        self.backend.playlists.playlists = [
            Playlist(name='a\n', uri='dummy:')]
        self.sendRequest('listplaylists')
        self.assertInResponse('playlist: a ')
        self.assertNotInResponse('playlist: a\n')
        self.assertInResponse('OK')

    def test_listplaylists_replaces_carriage_return_with_space(self):
        self.backend.playlists.playlists = [
            Playlist(name='a\r', uri='dummy:')]
        self.sendRequest('listplaylists')
        self.assertInResponse('playlist: a ')
        self.assertNotInResponse('playlist: a\r')
        self.assertInResponse('OK')

    def test_listplaylists_replaces_forward_slash_with_space(self):
        self.backend.playlists.playlists = [
            Playlist(name='a/', uri='dummy:')]
        self.sendRequest('listplaylists')
        self.assertInResponse('playlist: a ')
        self.assertNotInResponse('playlist: a/')
        self.assertInResponse('OK')

    def test_load_appends_to_tracklist(self):
        self.core.tracklist.add([Track(uri='a'), Track(uri='b')])
        self.assertEqual(len(self.core.tracklist.tracks.get()), 2)
        self.backend.playlists.playlists = [
            Playlist(name='A-list', uri='dummy:A-list', tracks=[
                Track(uri='c'), Track(uri='d'), Track(uri='e')])]

        self.sendRequest('load "A-list"')

        tracks = self.core.tracklist.tracks.get()
        self.assertEqual(5, len(tracks))
        self.assertEqual('a', tracks[0].uri)
        self.assertEqual('b', tracks[1].uri)
        self.assertEqual('c', tracks[2].uri)
        self.assertEqual('d', tracks[3].uri)
        self.assertEqual('e', tracks[4].uri)
        self.assertInResponse('OK')

    def test_load_with_range_loads_part_of_playlist(self):
        self.core.tracklist.add([Track(uri='a'), Track(uri='b')])
        self.assertEqual(len(self.core.tracklist.tracks.get()), 2)
        self.backend.playlists.playlists = [
            Playlist(name='A-list', uri='dummy:A-list', tracks=[
                Track(uri='c'), Track(uri='d'), Track(uri='e')])]

        self.sendRequest('load "A-list" "1:2"')

        tracks = self.core.tracklist.tracks.get()
        self.assertEqual(3, len(tracks))
        self.assertEqual('a', tracks[0].uri)
        self.assertEqual('b', tracks[1].uri)
        self.assertEqual('d', tracks[2].uri)
        self.assertInResponse('OK')

    def test_load_with_range_without_end_loads_rest_of_playlist(self):
        self.core.tracklist.add([Track(uri='a'), Track(uri='b')])
        self.assertEqual(len(self.core.tracklist.tracks.get()), 2)
        self.backend.playlists.playlists = [
            Playlist(name='A-list', uri='dummy:A-list', tracks=[
                Track(uri='c'), Track(uri='d'), Track(uri='e')])]

        self.sendRequest('load "A-list" "1:"')

        tracks = self.core.tracklist.tracks.get()
        self.assertEqual(4, len(tracks))
        self.assertEqual('a', tracks[0].uri)
        self.assertEqual('b', tracks[1].uri)
        self.assertEqual('d', tracks[2].uri)
        self.assertEqual('e', tracks[3].uri)
        self.assertInResponse('OK')

    def test_load_unknown_playlist_acks(self):
        self.sendRequest('load "unknown playlist"')
        self.assertEqual(0, len(self.core.tracklist.tracks.get()))
        self.assertEqualResponse('ACK [50@0] {load} No such playlist')

    def test_playlistadd(self):
        self.sendRequest('playlistadd "name" "dummy:a"')
        self.assertEqualResponse('ACK [0@0] {playlistadd} Not implemented')

    def test_playlistclear(self):
        self.sendRequest('playlistclear "name"')
        self.assertEqualResponse('ACK [0@0] {playlistclear} Not implemented')

    def test_playlistdelete(self):
        self.sendRequest('playlistdelete "name" "5"')
        self.assertEqualResponse('ACK [0@0] {playlistdelete} Not implemented')

    def test_playlistmove(self):
        self.sendRequest('playlistmove "name" "5" "10"')
        self.assertEqualResponse('ACK [0@0] {playlistmove} Not implemented')

    def test_rename(self):
        self.sendRequest('rename "old_name" "new_name"')
        self.assertEqualResponse('ACK [0@0] {rename} Not implemented')

    def test_rm(self):
        self.sendRequest('rm "name"')
        self.assertEqualResponse('ACK [0@0] {rm} Not implemented')

    def test_save(self):
        self.sendRequest('save "name"')
        self.assertEqualResponse('ACK [0@0] {save} Not implemented')

########NEW FILE########
__FILENAME__ = test_commands
# encoding: utf-8

from __future__ import unicode_literals

import unittest

from mopidy.mpd import exceptions, protocol


class TestConverts(unittest.TestCase):
    def test_integer(self):
        self.assertEqual(123, protocol.INT('123'))
        self.assertEqual(-123, protocol.INT('-123'))
        self.assertEqual(123, protocol.INT('+123'))
        self.assertRaises(ValueError, protocol.INT, '3.14')
        self.assertRaises(ValueError, protocol.INT, '')
        self.assertRaises(ValueError, protocol.INT, 'abc')
        self.assertRaises(ValueError, protocol.INT, '12 34')

    def test_unsigned_integer(self):
        self.assertEqual(123, protocol.UINT('123'))
        self.assertRaises(ValueError, protocol.UINT, '-123')
        self.assertRaises(ValueError, protocol.UINT, '+123')
        self.assertRaises(ValueError, protocol.UINT, '3.14')
        self.assertRaises(ValueError, protocol.UINT, '')
        self.assertRaises(ValueError, protocol.UINT, 'abc')
        self.assertRaises(ValueError, protocol.UINT, '12 34')

    def test_boolean(self):
        self.assertEqual(True, protocol.BOOL('1'))
        self.assertEqual(False, protocol.BOOL('0'))
        self.assertRaises(ValueError, protocol.BOOL, '3.14')
        self.assertRaises(ValueError, protocol.BOOL, '')
        self.assertRaises(ValueError, protocol.BOOL, 'true')
        self.assertRaises(ValueError, protocol.BOOL, 'false')
        self.assertRaises(ValueError, protocol.BOOL, 'abc')
        self.assertRaises(ValueError, protocol.BOOL, '12 34')

    def test_range(self):
        self.assertEqual(slice(1, 2), protocol.RANGE('1'))
        self.assertEqual(slice(0, 1), protocol.RANGE('0'))
        self.assertEqual(slice(0, None), protocol.RANGE('0:'))
        self.assertEqual(slice(1, 3), protocol.RANGE('1:3'))
        self.assertRaises(ValueError, protocol.RANGE, '3.14')
        self.assertRaises(ValueError, protocol.RANGE, '1:abc')
        self.assertRaises(ValueError, protocol.RANGE, 'abc:1')
        self.assertRaises(ValueError, protocol.RANGE, '2:1')
        self.assertRaises(ValueError, protocol.RANGE, '-1:2')
        self.assertRaises(ValueError, protocol.RANGE, '1 : 2')
        self.assertRaises(ValueError, protocol.RANGE, '')
        self.assertRaises(ValueError, protocol.RANGE, 'true')
        self.assertRaises(ValueError, protocol.RANGE, 'false')
        self.assertRaises(ValueError, protocol.RANGE, 'abc')
        self.assertRaises(ValueError, protocol.RANGE, '12 34')


class TestCommands(unittest.TestCase):
    def setUp(self):
        self.commands = protocol.Commands()

    def test_add_as_a_decorator(self):
        @self.commands.add('test')
        def test(context):
            pass

    def test_register_second_command_to_same_name_fails(self):
        func = lambda context: True

        self.commands.add('foo')(func)
        with self.assertRaises(Exception):
            self.commands.add('foo')(func)

    def test_function_only_takes_context_succeeds(self):
        sentinel = object()
        self.commands.add('bar')(lambda context: sentinel)
        self.assertEqual(sentinel, self.commands.call(['bar']))

    def test_function_has_required_arg_succeeds(self):
        sentinel = object()
        self.commands.add('bar')(lambda context, required: sentinel)
        self.assertEqual(sentinel, self.commands.call(['bar', 'arg']))

    def test_function_has_optional_args_succeeds(self):
        sentinel = object()
        self.commands.add('bar')(lambda context, optional=None: sentinel)
        self.assertEqual(sentinel, self.commands.call(['bar']))
        self.assertEqual(sentinel, self.commands.call(['bar', 'arg']))

    def test_function_has_required_and_optional_args_succeeds(self):
        sentinel = object()
        func = lambda context, required, optional=None: sentinel
        self.commands.add('bar')(func)
        self.assertEqual(sentinel, self.commands.call(['bar', 'arg']))
        self.assertEqual(sentinel, self.commands.call(['bar', 'arg', 'arg']))

    def test_function_has_varargs_succeeds(self):
        sentinel, args = object(), []
        self.commands.add('bar')(lambda context, *args: sentinel)
        for i in range(10):
            self.assertEqual(sentinel, self.commands.call(['bar'] + args))
            args.append('test')

    def test_function_has_only_varags_succeeds(self):
        sentinel = object()
        self.commands.add('baz')(lambda *args: sentinel)
        self.assertEqual(sentinel, self.commands.call(['baz']))

    def test_function_has_no_arguments_fails(self):
        with self.assertRaises(TypeError):
            self.commands.add('test')(lambda: True)

    def test_function_has_required_and_varargs_fails(self):
        with self.assertRaises(TypeError):
            func = lambda context, required, *args: True
            self.commands.add('test')(func)

    def test_function_has_optional_and_varargs_fails(self):
        with self.assertRaises(TypeError):
            func = lambda context, optional=None, *args: True
            self.commands.add('test')(func)

    def test_function_hash_keywordargs_fails(self):
        with self.assertRaises(TypeError):
            self.commands.add('test')(lambda context, **kwargs: True)

    def test_call_chooses_correct_handler(self):
        sentinel1, sentinel2, sentinel3 = object(), object(), object()
        self.commands.add('foo')(lambda context: sentinel1)
        self.commands.add('bar')(lambda context: sentinel2)
        self.commands.add('baz')(lambda context: sentinel3)

        self.assertEqual(sentinel1, self.commands.call(['foo']))
        self.assertEqual(sentinel2, self.commands.call(['bar']))
        self.assertEqual(sentinel3, self.commands.call(['baz']))

    def test_call_with_nonexistent_handler(self):
        with self.assertRaises(exceptions.MpdUnknownCommand):
            self.commands.call(['bar'])

    def test_call_passes_context(self):
        sentinel = object()
        self.commands.add('foo')(lambda context: context)
        self.assertEqual(
            sentinel, self.commands.call(['foo'], context=sentinel))

    def test_call_without_args_fails(self):
        with self.assertRaises(exceptions.MpdNoCommand):
            self.commands.call([])

    def test_call_passes_required_argument(self):
        self.commands.add('foo')(lambda context, required: required)
        self.assertEqual('test123', self.commands.call(['foo', 'test123']))

    def test_call_passes_optional_argument(self):
        sentinel = object()
        self.commands.add('foo')(lambda context, optional=sentinel: optional)
        self.assertEqual(sentinel, self.commands.call(['foo']))
        self.assertEqual('test', self.commands.call(['foo', 'test']))

    def test_call_passes_required_and_optional_argument(self):
        func = lambda context, required, optional=None: (required, optional)
        self.commands.add('foo')(func)
        self.assertEqual(('arg', None), self.commands.call(['foo', 'arg']))
        self.assertEqual(
            ('arg', 'kwarg'), self.commands.call(['foo', 'arg', 'kwarg']))

    def test_call_passes_varargs(self):
        self.commands.add('foo')(lambda context, *args: args)

    def test_call_incorrect_args(self):
        self.commands.add('foo')(lambda context: context)
        with self.assertRaises(TypeError):
            self.commands.call(['foo', 'bar'])

        self.commands.add('bar')(lambda context, required: context)
        with self.assertRaises(TypeError):
            self.commands.call(['bar', 'bar', 'baz'])

        self.commands.add('baz')(lambda context, optional=None: context)
        with self.assertRaises(TypeError):
            self.commands.call(['baz', 'bar', 'baz'])

    def test_validator_gets_applied_to_required_arg(self):
        sentinel = object()
        func = lambda context, required: required
        self.commands.add('test', required=lambda v: sentinel)(func)
        self.assertEqual(sentinel, self.commands.call(['test', 'foo']))

    def test_validator_gets_applied_to_optional_arg(self):
        sentinel = object()
        func = lambda context, optional=None: optional
        self.commands.add('foo', optional=lambda v: sentinel)(func)

        self.assertEqual(sentinel, self.commands.call(['foo', '123']))

    def test_validator_skips_optional_default(self):
        sentinel = object()
        func = lambda context, optional=sentinel: optional
        self.commands.add('foo', optional=lambda v: None)(func)

        self.assertEqual(sentinel, self.commands.call(['foo']))

    def test_validator_applied_to_non_existent_arg_fails(self):
        self.commands.add('foo')(lambda context, arg: arg)
        with self.assertRaises(TypeError):
            func = lambda context, wrong_arg: wrong_arg
            self.commands.add('bar', arg=lambda v: v)(func)

    def test_validator_called_context_fails(self):
        return  # TODO: how to handle this
        with self.assertRaises(TypeError):
            func = lambda context: True
            self.commands.add('bar', context=lambda v: v)(func)

    def test_validator_value_error_is_converted(self):
        def validdate(value):
            raise ValueError

        func = lambda context, arg: True
        self.commands.add('bar', arg=validdate)(func)

        with self.assertRaises(exceptions.MpdArgError):
            self.commands.call(['bar', 'test'])

    def test_auth_required_gets_stored(self):
        func1 = lambda context: context
        func2 = lambda context: context
        self.commands.add('foo')(func1)
        self.commands.add('bar', auth_required=False)(func2)

        self.assertTrue(self.commands.handlers['foo'].auth_required)
        self.assertFalse(self.commands.handlers['bar'].auth_required)

    def test_list_command_gets_stored(self):
        func1 = lambda context: context
        func2 = lambda context: context
        self.commands.add('foo')(func1)
        self.commands.add('bar', list_command=False)(func2)

        self.assertTrue(self.commands.handlers['foo'].list_command)
        self.assertFalse(self.commands.handlers['bar'].list_command)

########NEW FILE########
__FILENAME__ = test_dispatcher
from __future__ import unicode_literals

import unittest

import pykka

from mopidy import core
from mopidy.backend import dummy
from mopidy.mpd.dispatcher import MpdDispatcher
from mopidy.mpd.exceptions import MpdAckError


class MpdDispatcherTest(unittest.TestCase):
    def setUp(self):
        config = {
            'mpd': {
                'password': None,
            }
        }
        self.backend = dummy.create_dummy_backend_proxy()
        self.core = core.Core.start(backends=[self.backend]).proxy()
        self.dispatcher = MpdDispatcher(config=config)

    def tearDown(self):
        pykka.ActorRegistry.stop_all()

    def test_call_handler_for_unknown_command_raises_exception(self):
        try:
            self.dispatcher._call_handler('an_unknown_command with args')
            self.fail('Should raise exception')
        except MpdAckError as e:
            self.assertEqual(
                e.get_mpd_ack(),
                'ACK [5@0] {} unknown command "an_unknown_command"')

    def test_handling_unknown_request_yields_error(self):
        result = self.dispatcher.handle_request('an unhandled request')
        self.assertEqual(result[0], 'ACK [5@0] {} unknown command "an"')

########NEW FILE########
__FILENAME__ = test_exceptions
from __future__ import unicode_literals

import unittest

from mopidy.mpd.exceptions import (
    MpdAckError, MpdNoCommand, MpdNotImplemented, MpdPermissionError,
    MpdSystemError, MpdUnknownCommand)


class MpdExceptionsTest(unittest.TestCase):
    def test_key_error_wrapped_in_mpd_ack_error(self):
        try:
            try:
                raise KeyError('Track X not found')
            except KeyError as e:
                raise MpdAckError(e[0])
        except MpdAckError as e:
            self.assertEqual(e.message, 'Track X not found')

    def test_mpd_not_implemented_is_a_mpd_ack_error(self):
        try:
            raise MpdNotImplemented
        except MpdAckError as e:
            self.assertEqual(e.message, 'Not implemented')

    def test_get_mpd_ack_with_default_values(self):
        e = MpdAckError('A description')
        self.assertEqual(e.get_mpd_ack(), 'ACK [0@0] {None} A description')

    def test_get_mpd_ack_with_values(self):
        try:
            raise MpdAckError('A description', index=7, command='foo')
        except MpdAckError as e:
            self.assertEqual(e.get_mpd_ack(), 'ACK [0@7] {foo} A description')

    def test_mpd_unknown_command(self):
        try:
            raise MpdUnknownCommand(command='play')
        except MpdAckError as e:
            self.assertEqual(
                e.get_mpd_ack(), 'ACK [5@0] {} unknown command "play"')

    def test_mpd_no_command(self):
        try:
            raise MpdNoCommand
        except MpdAckError as e:
            self.assertEqual(
                e.get_mpd_ack(), 'ACK [5@0] {} No command given')

    def test_mpd_system_error(self):
        try:
            raise MpdSystemError('foo')
        except MpdSystemError as e:
            self.assertEqual(
                e.get_mpd_ack(), 'ACK [52@0] {None} foo')

    def test_mpd_permission_error(self):
        try:
            raise MpdPermissionError(command='foo')
        except MpdPermissionError as e:
            self.assertEqual(
                e.get_mpd_ack(),
                'ACK [4@0] {foo} you don\'t have permission for "foo"')

########NEW FILE########
__FILENAME__ = test_status
from __future__ import unicode_literals

import unittest

import pykka

from mopidy import core
from mopidy.backend import dummy
from mopidy.core import PlaybackState
from mopidy.models import Track
from mopidy.mpd import dispatcher
from mopidy.mpd.protocol import status

PAUSED = PlaybackState.PAUSED
PLAYING = PlaybackState.PLAYING
STOPPED = PlaybackState.STOPPED

# FIXME migrate to using protocol.BaseTestCase instead of status.stats
# directly?


class StatusHandlerTest(unittest.TestCase):
    def setUp(self):
        self.backend = dummy.create_dummy_backend_proxy()
        self.core = core.Core.start(backends=[self.backend]).proxy()
        self.dispatcher = dispatcher.MpdDispatcher(core=self.core)
        self.context = self.dispatcher.context

    def tearDown(self):
        pykka.ActorRegistry.stop_all()

    def test_stats_method(self):
        result = status.stats(self.context)
        self.assertIn('artists', result)
        self.assertGreaterEqual(int(result['artists']), 0)
        self.assertIn('albums', result)
        self.assertGreaterEqual(int(result['albums']), 0)
        self.assertIn('songs', result)
        self.assertGreaterEqual(int(result['songs']), 0)
        self.assertIn('uptime', result)
        self.assertGreaterEqual(int(result['uptime']), 0)
        self.assertIn('db_playtime', result)
        self.assertGreaterEqual(int(result['db_playtime']), 0)
        self.assertIn('db_update', result)
        self.assertGreaterEqual(int(result['db_update']), 0)
        self.assertIn('playtime', result)
        self.assertGreaterEqual(int(result['playtime']), 0)

    def test_status_method_contains_volume_with_na_value(self):
        result = dict(status.status(self.context))
        self.assertIn('volume', result)
        self.assertEqual(int(result['volume']), -1)

    def test_status_method_contains_volume(self):
        self.core.playback.volume = 17
        result = dict(status.status(self.context))
        self.assertIn('volume', result)
        self.assertEqual(int(result['volume']), 17)

    def test_status_method_contains_repeat_is_0(self):
        result = dict(status.status(self.context))
        self.assertIn('repeat', result)
        self.assertEqual(int(result['repeat']), 0)

    def test_status_method_contains_repeat_is_1(self):
        self.core.tracklist.repeat = 1
        result = dict(status.status(self.context))
        self.assertIn('repeat', result)
        self.assertEqual(int(result['repeat']), 1)

    def test_status_method_contains_random_is_0(self):
        result = dict(status.status(self.context))
        self.assertIn('random', result)
        self.assertEqual(int(result['random']), 0)

    def test_status_method_contains_random_is_1(self):
        self.core.tracklist.random = 1
        result = dict(status.status(self.context))
        self.assertIn('random', result)
        self.assertEqual(int(result['random']), 1)

    def test_status_method_contains_single(self):
        result = dict(status.status(self.context))
        self.assertIn('single', result)
        self.assertIn(int(result['single']), (0, 1))

    def test_status_method_contains_consume_is_0(self):
        result = dict(status.status(self.context))
        self.assertIn('consume', result)
        self.assertEqual(int(result['consume']), 0)

    def test_status_method_contains_consume_is_1(self):
        self.core.tracklist.consume = 1
        result = dict(status.status(self.context))
        self.assertIn('consume', result)
        self.assertEqual(int(result['consume']), 1)

    def test_status_method_contains_playlist(self):
        result = dict(status.status(self.context))
        self.assertIn('playlist', result)
        self.assertIn(int(result['playlist']), xrange(0, 2 ** 31 - 1))

    def test_status_method_contains_playlistlength(self):
        result = dict(status.status(self.context))
        self.assertIn('playlistlength', result)
        self.assertGreaterEqual(int(result['playlistlength']), 0)

    def test_status_method_contains_xfade(self):
        result = dict(status.status(self.context))
        self.assertIn('xfade', result)
        self.assertGreaterEqual(int(result['xfade']), 0)

    def test_status_method_contains_state_is_play(self):
        self.core.playback.state = PLAYING
        result = dict(status.status(self.context))
        self.assertIn('state', result)
        self.assertEqual(result['state'], 'play')

    def test_status_method_contains_state_is_stop(self):
        self.core.playback.state = STOPPED
        result = dict(status.status(self.context))
        self.assertIn('state', result)
        self.assertEqual(result['state'], 'stop')

    def test_status_method_contains_state_is_pause(self):
        self.core.playback.state = PLAYING
        self.core.playback.state = PAUSED
        result = dict(status.status(self.context))
        self.assertIn('state', result)
        self.assertEqual(result['state'], 'pause')

    def test_status_method_when_playlist_loaded_contains_song(self):
        self.core.tracklist.add([Track(uri='dummy:a')])
        self.core.playback.play()
        result = dict(status.status(self.context))
        self.assertIn('song', result)
        self.assertGreaterEqual(int(result['song']), 0)

    def test_status_method_when_playlist_loaded_contains_tlid_as_songid(self):
        self.core.tracklist.add([Track(uri='dummy:a')])
        self.core.playback.play()
        result = dict(status.status(self.context))
        self.assertIn('songid', result)
        self.assertEqual(int(result['songid']), 0)

    def test_status_method_when_playing_contains_time_with_no_length(self):
        self.core.tracklist.add([Track(uri='dummy:a', length=None)])
        self.core.playback.play()
        result = dict(status.status(self.context))
        self.assertIn('time', result)
        (position, total) = result['time'].split(':')
        position = int(position)
        total = int(total)
        self.assertLessEqual(position, total)

    def test_status_method_when_playing_contains_time_with_length(self):
        self.core.tracklist.add([Track(uri='dummy:a', length=10000)])
        self.core.playback.play()
        result = dict(status.status(self.context))
        self.assertIn('time', result)
        (position, total) = result['time'].split(':')
        position = int(position)
        total = int(total)
        self.assertLessEqual(position, total)

    def test_status_method_when_playing_contains_elapsed(self):
        self.core.tracklist.add([Track(uri='dummy:a', length=60000)])
        self.core.playback.play()
        self.core.playback.pause()
        self.core.playback.seek(59123)
        result = dict(status.status(self.context))
        self.assertIn('elapsed', result)
        self.assertEqual(result['elapsed'], '59.123')

    def test_status_method_when_starting_playing_contains_elapsed_zero(self):
        self.core.tracklist.add([Track(uri='dummy:a', length=10000)])
        self.core.playback.play()
        self.core.playback.pause()
        result = dict(status.status(self.context))
        self.assertIn('elapsed', result)
        self.assertEqual(result['elapsed'], '0.000')

    def test_status_method_when_playing_contains_bitrate(self):
        self.core.tracklist.add([Track(uri='dummy:a', bitrate=320)])
        self.core.playback.play()
        result = dict(status.status(self.context))
        self.assertIn('bitrate', result)
        self.assertEqual(int(result['bitrate']), 320)

########NEW FILE########
__FILENAME__ = test_tokenizer
# encoding: utf-8

from __future__ import unicode_literals

import unittest

from mopidy.mpd import exceptions, tokenize


class TestTokenizer(unittest.TestCase):
    def assertTokenizeEquals(self, expected, line):
        self.assertEqual(expected, tokenize.split(line))

    def assertTokenizeRaises(self, exception, message, line):
        with self.assertRaises(exception) as cm:
            tokenize.split(line)
        self.assertEqual(cm.exception.message, message)

    def test_empty_string(self):
        ex = exceptions.MpdNoCommand
        msg = 'No command given'
        self.assertTokenizeRaises(ex, msg, '')
        self.assertTokenizeRaises(ex, msg, '      ')
        self.assertTokenizeRaises(ex, msg, '\t\t\t')

    def test_command(self):
        self.assertTokenizeEquals(['test'], 'test')
        self.assertTokenizeEquals(['test123'], 'test123')
        self.assertTokenizeEquals(['foo_bar'], 'foo_bar')

    def test_command_trailing_whitespace(self):
        self.assertTokenizeEquals(['test'], 'test   ')
        self.assertTokenizeEquals(['test'], 'test\t\t\t')

    def test_command_leading_whitespace(self):
        ex = exceptions.MpdUnknownError
        msg = 'Letter expected'
        self.assertTokenizeRaises(ex, msg, '  test')
        self.assertTokenizeRaises(ex, msg, '\ttest')

    def test_invalid_command(self):
        ex = exceptions.MpdUnknownError
        msg = 'Invalid word character'
        self.assertTokenizeRaises(ex, msg, 'foo/bar')
        self.assertTokenizeRaises(ex, msg, 'æøå')
        self.assertTokenizeRaises(ex, msg, 'test?')
        self.assertTokenizeRaises(ex, msg, 'te"st')

    def test_unquoted_param(self):
        self.assertTokenizeEquals(['test', 'param'], 'test param')
        self.assertTokenizeEquals(['test', 'param'], 'test\tparam')

    def test_unquoted_param_leading_whitespace(self):
        self.assertTokenizeEquals(['test', 'param'], 'test  param')
        self.assertTokenizeEquals(['test', 'param'], 'test\t\tparam')

    def test_unquoted_param_trailing_whitespace(self):
        self.assertTokenizeEquals(['test', 'param'], 'test param  ')
        self.assertTokenizeEquals(['test', 'param'], 'test param\t\t')

    def test_unquoted_param_invalid_chars(self):
        ex = exceptions.MpdArgError
        msg = 'Invalid unquoted character'
        self.assertTokenizeRaises(ex, msg, 'test par"m')
        self.assertTokenizeRaises(ex, msg, 'test foo\bbar')
        self.assertTokenizeRaises(ex, msg, 'test foo"bar"baz')
        self.assertTokenizeRaises(ex, msg, 'test foo\'bar')

    def test_unquoted_param_numbers(self):
        self.assertTokenizeEquals(['test', '123'], 'test 123')
        self.assertTokenizeEquals(['test', '+123'], 'test +123')
        self.assertTokenizeEquals(['test', '-123'], 'test -123')
        self.assertTokenizeEquals(['test', '3.14'], 'test 3.14')

    def test_unquoted_param_extended_chars(self):
        self.assertTokenizeEquals(['test', 'æøå'], 'test æøå')
        self.assertTokenizeEquals(['test', '?#$'], 'test ?#$')
        self.assertTokenizeEquals(['test', '/foo/bar/'], 'test /foo/bar/')
        self.assertTokenizeEquals(['test', 'foo\\bar'], 'test foo\\bar')

    def test_unquoted_params(self):
        self.assertTokenizeEquals(['test', 'foo', 'bar'], 'test foo bar')

    def test_quoted_param(self):
        self.assertTokenizeEquals(['test', 'param'], 'test "param"')
        self.assertTokenizeEquals(['test', 'param'], 'test\t"param"')

    def test_quoted_param_leading_whitespace(self):
        self.assertTokenizeEquals(['test', 'param'], 'test  "param"')
        self.assertTokenizeEquals(['test', 'param'], 'test\t\t"param"')

    def test_quoted_param_trailing_whitespace(self):
        self.assertTokenizeEquals(['test', 'param'], 'test "param"  ')
        self.assertTokenizeEquals(['test', 'param'], 'test "param"\t\t')

    def test_quoted_param_invalid_chars(self):
        ex = exceptions.MpdArgError
        msg = 'Space expected after closing \'"\''
        self.assertTokenizeRaises(ex, msg, 'test "foo"bar"')
        self.assertTokenizeRaises(ex, msg, 'test "foo"bar" ')
        self.assertTokenizeRaises(ex, msg, 'test "foo"bar')
        self.assertTokenizeRaises(ex, msg, 'test "foo"bar ')

    def test_quoted_param_numbers(self):
        self.assertTokenizeEquals(['test', '123'], 'test "123"')
        self.assertTokenizeEquals(['test', '+123'], 'test "+123"')
        self.assertTokenizeEquals(['test', '-123'], 'test "-123"')
        self.assertTokenizeEquals(['test', '3.14'], 'test "3.14"')

    def test_quoted_param_spaces(self):
        self.assertTokenizeEquals(['test', 'foo bar'], 'test "foo bar"')
        self.assertTokenizeEquals(['test', 'foo bar'], 'test "foo bar"')
        self.assertTokenizeEquals(['test', ' param\t'], 'test " param\t"')

    def test_quoted_param_extended_chars(self):
        self.assertTokenizeEquals(['test', 'æøå'], 'test "æøå"')
        self.assertTokenizeEquals(['test', '?#$'], 'test "?#$"')
        self.assertTokenizeEquals(['test', '/foo/bar/'], 'test "/foo/bar/"')

    def test_quoted_param_escaping(self):
        self.assertTokenizeEquals(['test', '\\'], r'test "\\"')
        self.assertTokenizeEquals(['test', '"'], r'test "\""')
        self.assertTokenizeEquals(['test', ' '], r'test "\ "')
        self.assertTokenizeEquals(['test', '\\n'], r'test "\\\n"')

    def test_quoted_params(self):
        self.assertTokenizeEquals(['test', 'foo', 'bar'], 'test "foo" "bar"')

    def test_mixed_params(self):
        self.assertTokenizeEquals(['test', 'foo', 'bar'], 'test foo "bar"')
        self.assertTokenizeEquals(['test', 'foo', 'bar'], 'test "foo" bar')
        self.assertTokenizeEquals(['test', '1', '2'], 'test 1 "2"')
        self.assertTokenizeEquals(['test', '1', '2'], 'test "1" 2')

        self.assertTokenizeEquals(['test', 'foo bar', 'baz', '123'],
                                  'test "foo bar" baz 123')
        self.assertTokenizeEquals(['test', 'foo"bar', 'baz', '123'],
                                  r'test "foo\"bar" baz 123')

    def test_unbalanced_quotes(self):
        ex = exceptions.MpdArgError
        msg = 'Invalid unquoted character'
        self.assertTokenizeRaises(ex, msg, 'test "foo bar" baz"')

    def test_missing_closing_quote(self):
        ex = exceptions.MpdArgError
        msg = 'Missing closing \'"\''
        self.assertTokenizeRaises(ex, msg, 'test "foo')
        self.assertTokenizeRaises(ex, msg, 'test "foo a ')

########NEW FILE########
__FILENAME__ = test_translator
from __future__ import unicode_literals

import datetime
import unittest

from mopidy.models import Album, Artist, Playlist, TlTrack, Track
from mopidy.mpd import translator
from mopidy.utils.path import mtime


class TrackMpdFormatTest(unittest.TestCase):
    track = Track(
        uri='a uri',
        artists=[Artist(name='an artist')],
        name='a name',
        album=Album(
            name='an album', num_tracks=13,
            artists=[Artist(name='an other artist')]),
        track_no=7,
        composers=[Artist(name='a composer')],
        performers=[Artist(name='a performer')],
        genre='a genre',
        date=datetime.date(1977, 1, 1),
        disc_no='1',
        comment='a comment',
        length=137000,
    )

    def setUp(self):
        self.media_dir = '/dir/subdir'
        mtime.set_fake_time(1234567)

    def tearDown(self):
        mtime.undo_fake()

    def test_track_to_mpd_format_for_empty_track(self):
        result = translator.track_to_mpd_format(Track())
        self.assertIn(('file', ''), result)
        self.assertIn(('Time', 0), result)
        self.assertIn(('Artist', ''), result)
        self.assertIn(('Title', ''), result)
        self.assertIn(('Album', ''), result)
        self.assertIn(('Track', 0), result)
        self.assertNotIn(('Date', ''), result)
        self.assertEqual(len(result), 6)

    def test_track_to_mpd_format_with_position(self):
        result = translator.track_to_mpd_format(Track(), position=1)
        self.assertNotIn(('Pos', 1), result)

    def test_track_to_mpd_format_with_tlid(self):
        result = translator.track_to_mpd_format(TlTrack(1, Track()))
        self.assertNotIn(('Id', 1), result)

    def test_track_to_mpd_format_with_position_and_tlid(self):
        result = translator.track_to_mpd_format(
            TlTrack(2, Track()), position=1)
        self.assertIn(('Pos', 1), result)
        self.assertIn(('Id', 2), result)

    def test_track_to_mpd_format_for_nonempty_track(self):
        result = translator.track_to_mpd_format(
            TlTrack(122, self.track), position=9)
        self.assertIn(('file', 'a uri'), result)
        self.assertIn(('Time', 137), result)
        self.assertIn(('Artist', 'an artist'), result)
        self.assertIn(('Title', 'a name'), result)
        self.assertIn(('Album', 'an album'), result)
        self.assertIn(('AlbumArtist', 'an other artist'), result)
        self.assertIn(('Composer', 'a composer'), result)
        self.assertIn(('Performer', 'a performer'), result)
        self.assertIn(('Genre', 'a genre'), result)
        self.assertIn(('Track', '7/13'), result)
        self.assertIn(('Date', datetime.date(1977, 1, 1)), result)
        self.assertIn(('Disc', '1'), result)
        self.assertIn(('Comment', 'a comment'), result)
        self.assertIn(('Pos', 9), result)
        self.assertIn(('Id', 122), result)
        self.assertEqual(len(result), 15)

    def test_track_to_mpd_format_musicbrainz_trackid(self):
        track = self.track.copy(musicbrainz_id='foo')
        result = translator.track_to_mpd_format(track)
        self.assertIn(('MUSICBRAINZ_TRACKID', 'foo'), result)

    def test_track_to_mpd_format_musicbrainz_albumid(self):
        album = self.track.album.copy(musicbrainz_id='foo')
        track = self.track.copy(album=album)
        result = translator.track_to_mpd_format(track)
        self.assertIn(('MUSICBRAINZ_ALBUMID', 'foo'), result)

    def test_track_to_mpd_format_musicbrainz_albumartistid(self):
        artist = list(self.track.artists)[0].copy(musicbrainz_id='foo')
        album = self.track.album.copy(artists=[artist])
        track = self.track.copy(album=album)
        result = translator.track_to_mpd_format(track)
        self.assertIn(('MUSICBRAINZ_ALBUMARTISTID', 'foo'), result)

    def test_track_to_mpd_format_musicbrainz_artistid(self):
        artist = list(self.track.artists)[0].copy(musicbrainz_id='foo')
        track = self.track.copy(artists=[artist])
        result = translator.track_to_mpd_format(track)
        self.assertIn(('MUSICBRAINZ_ARTISTID', 'foo'), result)

    def test_artists_to_mpd_format(self):
        artists = [Artist(name='ABBA'), Artist(name='Beatles')]
        translated = translator.artists_to_mpd_format(artists)
        self.assertEqual(translated, 'ABBA, Beatles')

    def test_artists_to_mpd_format_artist_with_no_name(self):
        artists = [Artist(name=None)]
        translated = translator.artists_to_mpd_format(artists)
        self.assertEqual(translated, '')


class PlaylistMpdFormatTest(unittest.TestCase):
    def test_mpd_format(self):
        playlist = Playlist(tracks=[
            Track(track_no=1), Track(track_no=2), Track(track_no=3)])
        result = translator.playlist_to_mpd_format(playlist)
        self.assertEqual(len(result), 3)

    def test_mpd_format_with_range(self):
        playlist = Playlist(tracks=[
            Track(track_no=1), Track(track_no=2), Track(track_no=3)])
        result = translator.playlist_to_mpd_format(playlist, 1, 2)
        self.assertEqual(len(result), 1)
        self.assertEqual(dict(result[0])['Track'], 2)

########NEW FILE########
__FILENAME__ = test_commands
from __future__ import unicode_literals

import argparse
import unittest

import mock

from mopidy import commands


class ConfigOverrideTypeTest(unittest.TestCase):
    def test_valid_override(self):
        expected = (b'section', b'key', b'value')
        self.assertEqual(
            expected, commands.config_override_type(b'section/key=value'))
        self.assertEqual(
            expected, commands.config_override_type(b'section/key=value '))
        self.assertEqual(
            expected, commands.config_override_type(b'section/key =value'))
        self.assertEqual(
            expected, commands.config_override_type(b'section /key=value'))

    def test_valid_override_is_bytes(self):
        section, key, value = commands.config_override_type(
            b'section/key=value')
        self.assertIsInstance(section, bytes)
        self.assertIsInstance(key, bytes)
        self.assertIsInstance(value, bytes)

    def test_empty_override(self):
        expected = ('section', 'key', '')
        self.assertEqual(
            expected, commands.config_override_type(b'section/key='))
        self.assertEqual(
            expected, commands.config_override_type(b'section/key=  '))

    def test_invalid_override(self):
        self.assertRaises(
            argparse.ArgumentTypeError,
            commands.config_override_type, b'section/key')
        self.assertRaises(
            argparse.ArgumentTypeError,
            commands.config_override_type, b'section=')
        self.assertRaises(
            argparse.ArgumentTypeError,
            commands.config_override_type, b'section')


class CommandParsingTest(unittest.TestCase):
    def setUp(self):
        self.exit_patcher = mock.patch.object(commands.Command, 'exit')
        self.exit_mock = self.exit_patcher.start()
        self.exit_mock.side_effect = SystemExit

    def tearDown(self):
        self.exit_patcher.stop()

    def test_command_parsing_returns_namespace(self):
        cmd = commands.Command()
        self.assertIsInstance(cmd.parse([]), argparse.Namespace)

    def test_command_parsing_does_not_contain_args(self):
        cmd = commands.Command()
        result = cmd.parse([])
        self.assertFalse(hasattr(result, '_args'))

    def test_unknown_options_bails(self):
        cmd = commands.Command()
        with self.assertRaises(SystemExit):
            cmd.parse(['--foobar'])

    def test_invalid_sub_command_bails(self):
        cmd = commands.Command()
        with self.assertRaises(SystemExit):
            cmd.parse(['foo'])

    def test_command_arguments(self):
        cmd = commands.Command()
        cmd.add_argument('--bar')

        result = cmd.parse(['--bar', 'baz'])
        self.assertEqual(result.bar, 'baz')

    def test_command_arguments_and_sub_command(self):
        child = commands.Command()
        child.add_argument('--baz')

        cmd = commands.Command()
        cmd.add_argument('--bar')
        cmd.add_child('foo', child)

        result = cmd.parse(['--bar', 'baz', 'foo'])
        self.assertEqual(result.bar, 'baz')
        self.assertEqual(result.baz, None)

    def test_subcommand_may_have_positional(self):
        child = commands.Command()
        child.add_argument('bar')

        cmd = commands.Command()
        cmd.add_child('foo', child)

        result = cmd.parse(['foo', 'baz'])
        self.assertEqual(result.bar, 'baz')

    def test_subcommand_may_have_remainder(self):
        child = commands.Command()
        child.add_argument('bar', nargs=argparse.REMAINDER)

        cmd = commands.Command()
        cmd.add_child('foo', child)

        result = cmd.parse(['foo', 'baz', 'bep', 'bop'])
        self.assertEqual(result.bar, ['baz', 'bep', 'bop'])

    def test_result_stores_choosen_command(self):
        child = commands.Command()

        cmd = commands.Command()
        cmd.add_child('foo', child)

        result = cmd.parse(['foo'])
        self.assertEqual(result.command, child)

        result = cmd.parse([])
        self.assertEqual(result.command, cmd)

        child2 = commands.Command()
        cmd.add_child('bar', child2)

        subchild = commands.Command()
        child.add_child('baz', subchild)

        result = cmd.parse(['bar'])
        self.assertEqual(result.command, child2)

        result = cmd.parse(['foo', 'baz'])
        self.assertEqual(result.command, subchild)

    def test_invalid_type(self):
        cmd = commands.Command()
        cmd.add_argument('--bar', type=int)

        with self.assertRaises(SystemExit):
            cmd.parse(['--bar', b'zero'], prog='foo')

        self.exit_mock.assert_called_once_with(
            1, "argument --bar: invalid int value: 'zero'",
            'usage: foo [--bar BAR]')

    @mock.patch('sys.argv')
    def test_command_error_usage_prog(self, argv_mock):
        argv_mock.__getitem__.return_value = '/usr/bin/foo'

        cmd = commands.Command()
        cmd.add_argument('--bar', required=True)

        with self.assertRaises(SystemExit):
            cmd.parse([])
        self.exit_mock.assert_called_once_with(
            mock.ANY, mock.ANY, 'usage: foo --bar BAR')

        self.exit_mock.reset_mock()
        with self.assertRaises(SystemExit):
            cmd.parse([], prog='baz')

        self.exit_mock.assert_called_once_with(
            mock.ANY, mock.ANY, 'usage: baz --bar BAR')

    def test_missing_required(self):
        cmd = commands.Command()
        cmd.add_argument('--bar', required=True)

        with self.assertRaises(SystemExit):
            cmd.parse([], prog='foo')

        self.exit_mock.assert_called_once_with(
            1, 'argument --bar is required', 'usage: foo --bar BAR')

    def test_missing_positionals(self):
        cmd = commands.Command()
        cmd.add_argument('bar')

        with self.assertRaises(SystemExit):
            cmd.parse([], prog='foo')

        self.exit_mock.assert_called_once_with(
            1, 'too few arguments', 'usage: foo bar')

    def test_missing_positionals_subcommand(self):
        child = commands.Command()
        child.add_argument('baz')

        cmd = commands.Command()
        cmd.add_child('bar', child)

        with self.assertRaises(SystemExit):
            cmd.parse(['bar'], prog='foo')

        self.exit_mock.assert_called_once_with(
            1, 'too few arguments', 'usage: foo bar baz')

    def test_unknown_command(self):
        cmd = commands.Command()

        with self.assertRaises(SystemExit):
            cmd.parse(['--help'], prog='foo')

        self.exit_mock.assert_called_once_with(
            1, 'unrecognized arguments: --help', 'usage: foo')

    def test_invalid_subcommand(self):
        cmd = commands.Command()
        cmd.add_child('baz', commands.Command())

        with self.assertRaises(SystemExit):
            cmd.parse(['bar'], prog='foo')

        self.exit_mock.assert_called_once_with(
            1, 'unrecognized command: bar', 'usage: foo')

    def test_set(self):
        cmd = commands.Command()
        cmd.set(foo='bar')

        result = cmd.parse([])
        self.assertEqual(result.foo, 'bar')

    def test_set_propegate(self):
        child = commands.Command()

        cmd = commands.Command()
        cmd.set(foo='bar')
        cmd.add_child('command', child)

        result = cmd.parse(['command'])
        self.assertEqual(result.foo, 'bar')

    def test_innermost_set_wins(self):
        child = commands.Command()
        child.set(foo='bar', baz=1)

        cmd = commands.Command()
        cmd.set(foo='baz', baz=None)
        cmd.add_child('command', child)

        result = cmd.parse(['command'])
        self.assertEqual(result.foo, 'bar')
        self.assertEqual(result.baz, 1)

    def test_help_action_works(self):
        cmd = commands.Command()
        cmd.add_argument('-h', action='help')
        cmd.format_help = mock.Mock()

        with self.assertRaises(SystemExit):
            cmd.parse(['-h'])

        cmd.format_help.assert_called_once_with(mock.ANY)
        self.exit_mock.assert_called_once_with(0, cmd.format_help.return_value)


class UsageTest(unittest.TestCase):
    @mock.patch('sys.argv')
    def test_prog_name_default_and_override(self, argv_mock):
        argv_mock.__getitem__.return_value = '/usr/bin/foo'
        cmd = commands.Command()
        self.assertEqual('usage: foo', cmd.format_usage().strip())
        self.assertEqual('usage: baz', cmd.format_usage('baz').strip())

    def test_basic_usage(self):
        cmd = commands.Command()
        self.assertEqual('usage: foo', cmd.format_usage('foo').strip())

        cmd.add_argument('-h', '--help', action='store_true')
        self.assertEqual('usage: foo [-h]', cmd.format_usage('foo').strip())

        cmd.add_argument('bar')
        self.assertEqual('usage: foo [-h] bar',
                         cmd.format_usage('foo').strip())

    def test_nested_usage(self):
        child = commands.Command()
        cmd = commands.Command()
        cmd.add_child('bar', child)

        self.assertEqual('usage: foo', cmd.format_usage('foo').strip())
        self.assertEqual('usage: foo bar', cmd.format_usage('foo bar').strip())

        cmd.add_argument('-h', '--help', action='store_true')
        self.assertEqual('usage: foo bar',
                         child.format_usage('foo bar').strip())

        child.add_argument('-h', '--help', action='store_true')
        self.assertEqual('usage: foo bar [-h]',
                         child.format_usage('foo bar').strip())


class HelpTest(unittest.TestCase):
    @mock.patch('sys.argv')
    def test_prog_name_default_and_override(self, argv_mock):
        argv_mock.__getitem__.return_value = '/usr/bin/foo'
        cmd = commands.Command()
        self.assertEqual('usage: foo', cmd.format_help().strip())
        self.assertEqual('usage: bar', cmd.format_help('bar').strip())

    def test_command_without_documenation_or_options(self):
        cmd = commands.Command()
        self.assertEqual('usage: bar', cmd.format_help('bar').strip())

    def test_command_with_option(self):
        cmd = commands.Command()
        cmd.add_argument('-h', '--help', action='store_true',
                         help='show this message')

        expected = ('usage: foo [-h]\n\n'
                    'OPTIONS:\n\n'
                    '  -h, --help  show this message')
        self.assertEqual(expected, cmd.format_help('foo').strip())

    def test_command_with_option_and_positional(self):
        cmd = commands.Command()
        cmd.add_argument('-h', '--help', action='store_true',
                         help='show this message')
        cmd.add_argument('bar', help='some help text')

        expected = ('usage: foo [-h] bar\n\n'
                    'OPTIONS:\n\n'
                    '  -h, --help  show this message\n'
                    '  bar         some help text')
        self.assertEqual(expected, cmd.format_help('foo').strip())

    def test_command_with_documentation(self):
        cmd = commands.Command()
        cmd.help = 'some text about everything this command does.'

        expected = ('usage: foo\n\n'
                    'some text about everything this command does.')
        self.assertEqual(expected, cmd.format_help('foo').strip())

    def test_command_with_documentation_and_option(self):
        cmd = commands.Command()
        cmd.help = 'some text about everything this command does.'
        cmd.add_argument('-h', '--help', action='store_true',
                         help='show this message')

        expected = ('usage: foo [-h]\n\n'
                    'some text about everything this command does.\n\n'
                    'OPTIONS:\n\n'
                    '  -h, --help  show this message')
        self.assertEqual(expected, cmd.format_help('foo').strip())

    def test_subcommand_without_documentation_or_options(self):
        child = commands.Command()
        cmd = commands.Command()
        cmd.add_child('bar', child)

        self.assertEqual('usage: foo', cmd.format_help('foo').strip())

    def test_subcommand_with_documentation_shown(self):
        child = commands.Command()
        child.help = 'some text about everything this command does.'

        cmd = commands.Command()
        cmd.add_child('bar', child)
        expected = ('usage: foo\n\n'
                    'COMMANDS:\n\n'
                    'bar\n\n'
                    '  some text about everything this command does.')
        self.assertEqual(expected, cmd.format_help('foo').strip())

    def test_subcommand_with_options_shown(self):
        child = commands.Command()
        child.add_argument('-h', '--help', action='store_true',
                           help='show this message')

        cmd = commands.Command()
        cmd.add_child('bar', child)

        expected = ('usage: foo\n\n'
                    'COMMANDS:\n\n'
                    'bar [-h]\n\n'
                    '    -h, --help  show this message')
        self.assertEqual(expected, cmd.format_help('foo').strip())

    def test_subcommand_with_positional_shown(self):
        child = commands.Command()
        child.add_argument('baz', help='the great and wonderful')

        cmd = commands.Command()
        cmd.add_child('bar', child)

        expected = ('usage: foo\n\n'
                    'COMMANDS:\n\n'
                    'bar baz\n\n'
                    '    baz  the great and wonderful')
        self.assertEqual(expected, cmd.format_help('foo').strip())

    def test_subcommand_with_options_and_documentation(self):
        child = commands.Command()
        child.help = '  some text about everything this command does.'
        child.add_argument('-h', '--help', action='store_true',
                           help='show this message')

        cmd = commands.Command()
        cmd.add_child('bar', child)

        expected = ('usage: foo\n\n'
                    'COMMANDS:\n\n'
                    'bar [-h]\n\n'
                    '  some text about everything this command does.\n\n'
                    '    -h, --help  show this message')
        self.assertEqual(expected, cmd.format_help('foo').strip())

    def test_nested_subcommands_with_options(self):
        subchild = commands.Command()
        subchild.add_argument('--test', help='the great and wonderful')

        child = commands.Command()
        child.add_child('baz', subchild)
        child.add_argument('-h', '--help', action='store_true',
                           help='show this message')

        cmd = commands.Command()
        cmd.add_child('bar', child)

        expected = ('usage: foo\n\n'
                    'COMMANDS:\n\n'
                    'bar [-h]\n\n'
                    '    -h, --help  show this message\n\n'
                    'bar baz [--test TEST]\n\n'
                    '    --test TEST  the great and wonderful')
        self.assertEqual(expected, cmd.format_help('foo').strip())

    def test_nested_subcommands_skipped_intermediate(self):
        subchild = commands.Command()
        subchild.add_argument('--test', help='the great and wonderful')

        child = commands.Command()
        child.add_child('baz', subchild)

        cmd = commands.Command()
        cmd.add_child('bar', child)

        expected = ('usage: foo\n\n'
                    'COMMANDS:\n\n'
                    'bar baz [--test TEST]\n\n'
                    '    --test TEST  the great and wonderful')
        self.assertEqual(expected, cmd.format_help('foo').strip())

    def test_command_with_option_and_subcommand_with_option(self):
        child = commands.Command()
        child.add_argument('--test', help='the great and wonderful')

        cmd = commands.Command()
        cmd.add_argument('-h', '--help', action='store_true',
                         help='show this message')
        cmd.add_child('bar', child)

        expected = ('usage: foo [-h]\n\n'
                    'OPTIONS:\n\n'
                    '  -h, --help  show this message\n\n'
                    'COMMANDS:\n\n'
                    'bar [--test TEST]\n\n'
                    '    --test TEST  the great and wonderful')
        self.assertEqual(expected, cmd.format_help('foo').strip())

    def test_command_with_options_doc_and_subcommand_with_option_and_doc(self):
        child = commands.Command()
        child.help = 'some text about this sub-command.'
        child.add_argument('--test', help='the great and wonderful')

        cmd = commands.Command()
        cmd.help = 'some text about everything this command does.'
        cmd.add_argument('-h', '--help', action='store_true',
                         help='show this message')
        cmd.add_child('bar', child)

        expected = ('usage: foo [-h]\n\n'
                    'some text about everything this command does.\n\n'
                    'OPTIONS:\n\n'
                    '  -h, --help  show this message\n\n'
                    'COMMANDS:\n\n'
                    'bar [--test TEST]\n\n'
                    '  some text about this sub-command.\n\n'
                    '    --test TEST  the great and wonderful')
        self.assertEqual(expected, cmd.format_help('foo').strip())


class RunTest(unittest.TestCase):
    def test_default_implmentation_raises_error(self):
        with self.assertRaises(NotImplementedError):
            commands.Command().run()

########NEW FILE########
__FILENAME__ = test_exceptions
from __future__ import unicode_literals

import unittest

from mopidy import exceptions


class ExceptionsTest(unittest.TestCase):
    def test_exception_can_include_message_string(self):
        exc = exceptions.MopidyException('foo')

        self.assertEqual(exc.message, 'foo')
        self.assertEqual(str(exc), 'foo')

    def test_extension_error_is_a_mopidy_exception(self):
        self.assert_(issubclass(
            exceptions.ExtensionError, exceptions.MopidyException))

########NEW FILE########
__FILENAME__ = test_ext
from __future__ import unicode_literals

import unittest

from mopidy import config, ext


class ExtensionTest(unittest.TestCase):
    def setUp(self):
        self.ext = ext.Extension()

    def test_dist_name_is_none(self):
        self.assertIsNone(self.ext.dist_name)

    def test_ext_name_is_none(self):
        self.assertIsNone(self.ext.ext_name)

    def test_version_is_none(self):
        self.assertIsNone(self.ext.version)

    def test_get_default_config_raises_not_implemented(self):
        self.assertRaises(NotImplementedError, self.ext.get_default_config)

    def test_get_config_schema_returns_extension_schema(self):
        schema = self.ext.get_config_schema()
        self.assertIsInstance(schema['enabled'], config.Boolean)

    def test_validate_environment_does_nothing_by_default(self):
        self.assertIsNone(self.ext.validate_environment())

########NEW FILE########
__FILENAME__ = test_help
from __future__ import unicode_literals

import os
import subprocess
import sys
import unittest

import mopidy


class HelpTest(unittest.TestCase):
    def test_help_has_mopidy_options(self):
        mopidy_dir = os.path.dirname(mopidy.__file__)
        args = [sys.executable, mopidy_dir, '--help']
        process = subprocess.Popen(
            args,
            env={'PYTHONPATH': os.path.join(mopidy_dir, '..')},
            stdout=subprocess.PIPE)
        output = process.communicate()[0]
        self.assertIn('--version', output)
        self.assertIn('--help', output)
        self.assertIn('--quiet', output)
        self.assertIn('--verbose', output)
        self.assertIn('--save-debug-log', output)
        self.assertIn('--config', output)
        self.assertIn('--option', output)

########NEW FILE########
__FILENAME__ = test_models
from __future__ import unicode_literals

import json
import unittest

from mopidy.models import (
    Album, Artist, ModelJSONEncoder, Playlist, Ref, SearchResult, TlTrack,
    Track, model_json_decoder)


class GenericCopyTest(unittest.TestCase):
    def compare(self, orig, other):
        self.assertEqual(orig, other)
        self.assertNotEqual(id(orig), id(other))

    def test_copying_track(self):
        track = Track()
        self.compare(track, track.copy())

    def test_copying_artist(self):
        artist = Artist()
        self.compare(artist, artist.copy())

    def test_copying_album(self):
        album = Album()
        self.compare(album, album.copy())

    def test_copying_playlist(self):
        playlist = Playlist()
        self.compare(playlist, playlist.copy())

    def test_copying_track_with_basic_values(self):
        track = Track(name='foo', uri='bar')
        copy = track.copy(name='baz')
        self.assertEqual('baz', copy.name)
        self.assertEqual('bar', copy.uri)

    def test_copying_track_with_missing_values(self):
        track = Track(uri='bar')
        copy = track.copy(name='baz')
        self.assertEqual('baz', copy.name)
        self.assertEqual('bar', copy.uri)

    def test_copying_track_with_private_internal_value(self):
        artist1 = Artist(name='foo')
        artist2 = Artist(name='bar')
        track = Track(artists=[artist1])
        copy = track.copy(artists=[artist2])
        self.assertIn(artist2, copy.artists)

    def test_copying_track_with_invalid_key(self):
        test = lambda: Track().copy(invalid_key=True)
        self.assertRaises(TypeError, test)

    def test_copying_track_to_remove(self):
        track = Track(name='foo').copy(name=None)
        self.assertEquals(track.__dict__, Track().__dict__)


class RefTest(unittest.TestCase):
    def test_uri(self):
        uri = 'an_uri'
        ref = Ref(uri=uri)
        self.assertEqual(ref.uri, uri)
        self.assertRaises(AttributeError, setattr, ref, 'uri', None)

    def test_name(self):
        name = 'a name'
        ref = Ref(name=name)
        self.assertEqual(ref.name, name)
        self.assertRaises(AttributeError, setattr, ref, 'name', None)

    def test_invalid_kwarg(self):
        test = lambda: SearchResult(foo='baz')
        self.assertRaises(TypeError, test)

    def test_repr_without_results(self):
        self.assertEquals(
            "Ref(name=u'foo', type=u'artist', uri=u'uri')",
            repr(Ref(uri='uri', name='foo', type='artist')))

    def test_serialize_without_results(self):
        self.assertDictEqual(
            {'__model__': 'Ref', 'uri': 'uri'},
            Ref(uri='uri').serialize())

    def test_to_json_and_back(self):
        ref1 = Ref(uri='uri')
        serialized = json.dumps(ref1, cls=ModelJSONEncoder)
        ref2 = json.loads(serialized, object_hook=model_json_decoder)
        self.assertEqual(ref1, ref2)

    def test_type_constants(self):
        self.assertEqual(Ref.ALBUM, 'album')
        self.assertEqual(Ref.ARTIST, 'artist')
        self.assertEqual(Ref.DIRECTORY, 'directory')
        self.assertEqual(Ref.PLAYLIST, 'playlist')
        self.assertEqual(Ref.TRACK, 'track')

    def test_album_constructor(self):
        ref = Ref.album(uri='foo', name='bar')
        self.assertEqual(ref.uri, 'foo')
        self.assertEqual(ref.name, 'bar')
        self.assertEqual(ref.type, Ref.ALBUM)

    def test_artist_constructor(self):
        ref = Ref.artist(uri='foo', name='bar')
        self.assertEqual(ref.uri, 'foo')
        self.assertEqual(ref.name, 'bar')
        self.assertEqual(ref.type, Ref.ARTIST)

    def test_directory_constructor(self):
        ref = Ref.directory(uri='foo', name='bar')
        self.assertEqual(ref.uri, 'foo')
        self.assertEqual(ref.name, 'bar')
        self.assertEqual(ref.type, Ref.DIRECTORY)

    def test_playlist_constructor(self):
        ref = Ref.playlist(uri='foo', name='bar')
        self.assertEqual(ref.uri, 'foo')
        self.assertEqual(ref.name, 'bar')
        self.assertEqual(ref.type, Ref.PLAYLIST)

    def test_track_constructor(self):
        ref = Ref.track(uri='foo', name='bar')
        self.assertEqual(ref.uri, 'foo')
        self.assertEqual(ref.name, 'bar')
        self.assertEqual(ref.type, Ref.TRACK)


class ArtistTest(unittest.TestCase):
    def test_uri(self):
        uri = 'an_uri'
        artist = Artist(uri=uri)
        self.assertEqual(artist.uri, uri)
        self.assertRaises(AttributeError, setattr, artist, 'uri', None)

    def test_name(self):
        name = 'a name'
        artist = Artist(name=name)
        self.assertEqual(artist.name, name)
        self.assertRaises(AttributeError, setattr, artist, 'name', None)

    def test_musicbrainz_id(self):
        mb_id = 'mb-id'
        artist = Artist(musicbrainz_id=mb_id)
        self.assertEqual(artist.musicbrainz_id, mb_id)
        self.assertRaises(
            AttributeError, setattr, artist, 'musicbrainz_id', None)

    def test_invalid_kwarg(self):
        test = lambda: Artist(foo='baz')
        self.assertRaises(TypeError, test)

    def test_invalid_kwarg_with_name_matching_method(self):
        test = lambda: Artist(copy='baz')
        self.assertRaises(TypeError, test)

        test = lambda: Artist(serialize='baz')
        self.assertRaises(TypeError, test)

    def test_repr(self):
        self.assertEquals(
            "Artist(name=u'name', uri=u'uri')",
            repr(Artist(uri='uri', name='name')))

    def test_serialize(self):
        self.assertDictEqual(
            {'__model__': 'Artist', 'uri': 'uri', 'name': 'name'},
            Artist(uri='uri', name='name').serialize())

    def test_serialize_falsy_values(self):
        self.assertDictEqual(
            {'__model__': 'Artist', 'uri': '', 'name': None},
            Artist(uri='', name=None).serialize())

    def test_to_json_and_back(self):
        artist1 = Artist(uri='uri', name='name')
        serialized = json.dumps(artist1, cls=ModelJSONEncoder)
        artist2 = json.loads(serialized, object_hook=model_json_decoder)
        self.assertEqual(artist1, artist2)

    def test_to_json_and_back_with_unknown_field(self):
        artist = Artist(uri='uri', name='name').serialize()
        artist['foo'] = 'foo'
        serialized = json.dumps(artist)
        test = lambda: json.loads(serialized, object_hook=model_json_decoder)
        self.assertRaises(TypeError, test)

    def test_to_json_and_back_with_field_matching_method(self):
        artist = Artist(uri='uri', name='name').serialize()
        artist['copy'] = 'foo'
        serialized = json.dumps(artist)
        test = lambda: json.loads(serialized, object_hook=model_json_decoder)
        self.assertRaises(TypeError, test)

    def test_to_json_and_back_with_field_matching_internal_field(self):
        artist = Artist(uri='uri', name='name').serialize()
        artist['__mro__'] = 'foo'
        serialized = json.dumps(artist)
        test = lambda: json.loads(serialized, object_hook=model_json_decoder)
        self.assertRaises(TypeError, test)

    def test_eq_name(self):
        artist1 = Artist(name='name')
        artist2 = Artist(name='name')
        self.assertEqual(artist1, artist2)
        self.assertEqual(hash(artist1), hash(artist2))

    def test_eq_uri(self):
        artist1 = Artist(uri='uri')
        artist2 = Artist(uri='uri')
        self.assertEqual(artist1, artist2)
        self.assertEqual(hash(artist1), hash(artist2))

    def test_eq_musibrainz_id(self):
        artist1 = Artist(musicbrainz_id='id')
        artist2 = Artist(musicbrainz_id='id')
        self.assertEqual(artist1, artist2)
        self.assertEqual(hash(artist1), hash(artist2))

    def test_eq(self):
        artist1 = Artist(uri='uri', name='name', musicbrainz_id='id')
        artist2 = Artist(uri='uri', name='name', musicbrainz_id='id')
        self.assertEqual(artist1, artist2)
        self.assertEqual(hash(artist1), hash(artist2))

    def test_eq_none(self):
        self.assertNotEqual(Artist(), None)

    def test_eq_other(self):
        self.assertNotEqual(Artist(), 'other')

    def test_ne_name(self):
        artist1 = Artist(name='name1')
        artist2 = Artist(name='name2')
        self.assertNotEqual(artist1, artist2)
        self.assertNotEqual(hash(artist1), hash(artist2))

    def test_ne_uri(self):
        artist1 = Artist(uri='uri1')
        artist2 = Artist(uri='uri2')
        self.assertNotEqual(artist1, artist2)
        self.assertNotEqual(hash(artist1), hash(artist2))

    def test_ne_musicbrainz_id(self):
        artist1 = Artist(musicbrainz_id='id1')
        artist2 = Artist(musicbrainz_id='id2')
        self.assertNotEqual(artist1, artist2)
        self.assertNotEqual(hash(artist1), hash(artist2))

    def test_ne(self):
        artist1 = Artist(uri='uri1', name='name1', musicbrainz_id='id1')
        artist2 = Artist(uri='uri2', name='name2', musicbrainz_id='id2')
        self.assertNotEqual(artist1, artist2)
        self.assertNotEqual(hash(artist1), hash(artist2))


class AlbumTest(unittest.TestCase):
    def test_uri(self):
        uri = 'an_uri'
        album = Album(uri=uri)
        self.assertEqual(album.uri, uri)
        self.assertRaises(AttributeError, setattr, album, 'uri', None)

    def test_name(self):
        name = 'a name'
        album = Album(name=name)
        self.assertEqual(album.name, name)
        self.assertRaises(AttributeError, setattr, album, 'name', None)

    def test_artists(self):
        artist = Artist()
        album = Album(artists=[artist])
        self.assertIn(artist, album.artists)
        self.assertRaises(AttributeError, setattr, album, 'artists', None)

    def test_artists_none(self):
        self.assertEqual(set(), Album(artists=None).artists)

    def test_num_tracks(self):
        num_tracks = 11
        album = Album(num_tracks=num_tracks)
        self.assertEqual(album.num_tracks, num_tracks)
        self.assertRaises(AttributeError, setattr, album, 'num_tracks', None)

    def test_num_discs(self):
        num_discs = 2
        album = Album(num_discs=num_discs)
        self.assertEqual(album.num_discs, num_discs)
        self.assertRaises(AttributeError, setattr, album, 'num_discs', None)

    def test_date(self):
        date = '1977-01-01'
        album = Album(date=date)
        self.assertEqual(album.date, date)
        self.assertRaises(AttributeError, setattr, album, 'date', None)

    def test_musicbrainz_id(self):
        mb_id = 'mb-id'
        album = Album(musicbrainz_id=mb_id)
        self.assertEqual(album.musicbrainz_id, mb_id)
        self.assertRaises(
            AttributeError, setattr, album, 'musicbrainz_id', None)

    def test_images(self):
        image = 'data:foobar'
        album = Album(images=[image])
        self.assertIn(image, album.images)
        self.assertRaises(AttributeError, setattr, album, 'images', None)

    def test_images_none(self):
        self.assertEqual(set(), Album(images=None).images)

    def test_invalid_kwarg(self):
        test = lambda: Album(foo='baz')
        self.assertRaises(TypeError, test)

    def test_repr_without_artists(self):
        self.assertEquals(
            "Album(artists=[], images=[], name=u'name', uri=u'uri')",
            repr(Album(uri='uri', name='name')))

    def test_repr_with_artists(self):
        self.assertEquals(
            "Album(artists=[Artist(name=u'foo')], images=[], name=u'name', "
            "uri=u'uri')",
            repr(Album(uri='uri', name='name', artists=[Artist(name='foo')])))

    def test_serialize_without_artists(self):
        self.assertDictEqual(
            {'__model__': 'Album', 'uri': 'uri', 'name': 'name'},
            Album(uri='uri', name='name').serialize())

    def test_serialize_with_artists(self):
        artist = Artist(name='foo')
        self.assertDictEqual(
            {'__model__': 'Album', 'uri': 'uri', 'name': 'name',
                'artists': [artist.serialize()]},
            Album(uri='uri', name='name', artists=[artist]).serialize())

    def test_serialize_with_images(self):
        image = 'data:foobar'
        self.assertDictEqual(
            {'__model__': 'Album', 'uri': 'uri', 'name': 'name',
                'images': [image]},
            Album(uri='uri', name='name', images=[image]).serialize())

    def test_to_json_and_back(self):
        album1 = Album(uri='uri', name='name', artists=[Artist(name='foo')])
        serialized = json.dumps(album1, cls=ModelJSONEncoder)
        album2 = json.loads(serialized, object_hook=model_json_decoder)
        self.assertEqual(album1, album2)

    def test_eq_name(self):
        album1 = Album(name='name')
        album2 = Album(name='name')
        self.assertEqual(album1, album2)
        self.assertEqual(hash(album1), hash(album2))

    def test_eq_uri(self):
        album1 = Album(uri='uri')
        album2 = Album(uri='uri')
        self.assertEqual(album1, album2)
        self.assertEqual(hash(album1), hash(album2))

    def test_eq_artists(self):
        artists = [Artist()]
        album1 = Album(artists=artists)
        album2 = Album(artists=artists)
        self.assertEqual(album1, album2)
        self.assertEqual(hash(album1), hash(album2))

    def test_eq_artists_order(self):
        artist1 = Artist(name='name1')
        artist2 = Artist(name='name2')
        album1 = Album(artists=[artist1, artist2])
        album2 = Album(artists=[artist2, artist1])
        self.assertEqual(album1, album2)
        self.assertEqual(hash(album1), hash(album2))

    def test_eq_num_tracks(self):
        album1 = Album(num_tracks=2)
        album2 = Album(num_tracks=2)
        self.assertEqual(album1, album2)
        self.assertEqual(hash(album1), hash(album2))

    def test_eq_date(self):
        date = '1977-01-01'
        album1 = Album(date=date)
        album2 = Album(date=date)
        self.assertEqual(album1, album2)
        self.assertEqual(hash(album1), hash(album2))

    def test_eq_musibrainz_id(self):
        album1 = Album(musicbrainz_id='id')
        album2 = Album(musicbrainz_id='id')
        self.assertEqual(album1, album2)
        self.assertEqual(hash(album1), hash(album2))

    def test_eq(self):
        artists = [Artist()]
        album1 = Album(
            name='name', uri='uri', artists=artists, num_tracks=2,
            musicbrainz_id='id')
        album2 = Album(
            name='name', uri='uri', artists=artists, num_tracks=2,
            musicbrainz_id='id')
        self.assertEqual(album1, album2)
        self.assertEqual(hash(album1), hash(album2))

    def test_eq_none(self):
        self.assertNotEqual(Album(), None)

    def test_eq_other(self):
        self.assertNotEqual(Album(), 'other')

    def test_ne_name(self):
        album1 = Album(name='name1')
        album2 = Album(name='name2')
        self.assertNotEqual(album1, album2)
        self.assertNotEqual(hash(album1), hash(album2))

    def test_ne_uri(self):
        album1 = Album(uri='uri1')
        album2 = Album(uri='uri2')
        self.assertNotEqual(album1, album2)
        self.assertNotEqual(hash(album1), hash(album2))

    def test_ne_artists(self):
        album1 = Album(artists=[Artist(name='name1')])
        album2 = Album(artists=[Artist(name='name2')])
        self.assertNotEqual(album1, album2)
        self.assertNotEqual(hash(album1), hash(album2))

    def test_ne_num_tracks(self):
        album1 = Album(num_tracks=1)
        album2 = Album(num_tracks=2)
        self.assertNotEqual(album1, album2)
        self.assertNotEqual(hash(album1), hash(album2))

    def test_ne_date(self):
        album1 = Album(date='1977-01-01')
        album2 = Album(date='1977-01-02')
        self.assertNotEqual(album1, album2)
        self.assertNotEqual(hash(album1), hash(album2))

    def test_ne_musicbrainz_id(self):
        album1 = Album(musicbrainz_id='id1')
        album2 = Album(musicbrainz_id='id2')
        self.assertNotEqual(album1, album2)
        self.assertNotEqual(hash(album1), hash(album2))

    def test_ne(self):
        album1 = Album(
            name='name1', uri='uri1', artists=[Artist(name='name1')],
            num_tracks=1, musicbrainz_id='id1')
        album2 = Album(
            name='name2', uri='uri2', artists=[Artist(name='name2')],
            num_tracks=2, musicbrainz_id='id2')
        self.assertNotEqual(album1, album2)
        self.assertNotEqual(hash(album1), hash(album2))


class TrackTest(unittest.TestCase):
    def test_uri(self):
        uri = 'an_uri'
        track = Track(uri=uri)
        self.assertEqual(track.uri, uri)
        self.assertRaises(AttributeError, setattr, track, 'uri', None)

    def test_name(self):
        name = 'a name'
        track = Track(name=name)
        self.assertEqual(track.name, name)
        self.assertRaises(AttributeError, setattr, track, 'name', None)

    def test_artists(self):
        artists = [Artist(name='name1'), Artist(name='name2')]
        track = Track(artists=artists)
        self.assertEqual(set(track.artists), set(artists))
        self.assertRaises(AttributeError, setattr, track, 'artists', None)

    def test_artists_none(self):
        self.assertEqual(set(), Track(artists=None).artists)

    def test_composers(self):
        artists = [Artist(name='name1'), Artist(name='name2')]
        track = Track(composers=artists)
        self.assertEqual(set(track.composers), set(artists))
        self.assertRaises(AttributeError, setattr, track, 'composers', None)

    def test_composers_none(self):
        self.assertEqual(set(), Track(composers=None).composers)

    def test_performers(self):
        artists = [Artist(name='name1'), Artist(name='name2')]
        track = Track(performers=artists)
        self.assertEqual(set(track.performers), set(artists))
        self.assertRaises(AttributeError, setattr, track, 'performers', None)

    def test_performers_none(self):
        self.assertEqual(set(), Track(performers=None).performers)

    def test_album(self):
        album = Album()
        track = Track(album=album)
        self.assertEqual(track.album, album)
        self.assertRaises(AttributeError, setattr, track, 'album', None)

    def test_track_no(self):
        track_no = 7
        track = Track(track_no=track_no)
        self.assertEqual(track.track_no, track_no)
        self.assertRaises(AttributeError, setattr, track, 'track_no', None)

    def test_disc_no(self):
        disc_no = 2
        track = Track(disc_no=disc_no)
        self.assertEqual(track.disc_no, disc_no)
        self.assertRaises(AttributeError, setattr, track, 'disc_no', None)

    def test_date(self):
        date = '1977-01-01'
        track = Track(date=date)
        self.assertEqual(track.date, date)
        self.assertRaises(AttributeError, setattr, track, 'date', None)

    def test_length(self):
        length = 137000
        track = Track(length=length)
        self.assertEqual(track.length, length)
        self.assertRaises(AttributeError, setattr, track, 'length', None)

    def test_bitrate(self):
        bitrate = 160
        track = Track(bitrate=bitrate)
        self.assertEqual(track.bitrate, bitrate)
        self.assertRaises(AttributeError, setattr, track, 'bitrate', None)

    def test_musicbrainz_id(self):
        mb_id = 'mb-id'
        track = Track(musicbrainz_id=mb_id)
        self.assertEqual(track.musicbrainz_id, mb_id)
        self.assertRaises(
            AttributeError, setattr, track, 'musicbrainz_id', None)

    def test_invalid_kwarg(self):
        test = lambda: Track(foo='baz')
        self.assertRaises(TypeError, test)

    def test_repr_without_artists(self):
        self.assertEquals(
            "Track(artists=[], composers=[], name=u'name', "
            "performers=[], uri=u'uri')",
            repr(Track(uri='uri', name='name')))

    def test_repr_with_artists(self):
        self.assertEquals(
            "Track(artists=[Artist(name=u'foo')], composers=[], name=u'name', "
            "performers=[], uri=u'uri')",
            repr(Track(uri='uri', name='name', artists=[Artist(name='foo')])))

    def test_serialize_without_artists(self):
        self.assertDictEqual(
            {'__model__': 'Track', 'uri': 'uri', 'name': 'name'},
            Track(uri='uri', name='name').serialize())

    def test_serialize_with_artists(self):
        artist = Artist(name='foo')
        self.assertDictEqual(
            {'__model__': 'Track', 'uri': 'uri', 'name': 'name',
                'artists': [artist.serialize()]},
            Track(uri='uri', name='name', artists=[artist]).serialize())

    def test_serialize_with_album(self):
        album = Album(name='foo')
        self.assertDictEqual(
            {'__model__': 'Track', 'uri': 'uri', 'name': 'name',
                'album': album.serialize()},
            Track(uri='uri', name='name', album=album).serialize())

    def test_to_json_and_back(self):
        track1 = Track(
            uri='uri', name='name', album=Album(name='foo'),
            artists=[Artist(name='foo')])
        serialized = json.dumps(track1, cls=ModelJSONEncoder)
        track2 = json.loads(serialized, object_hook=model_json_decoder)
        self.assertEqual(track1, track2)

    def test_eq_uri(self):
        track1 = Track(uri='uri1')
        track2 = Track(uri='uri1')
        self.assertEqual(track1, track2)
        self.assertEqual(hash(track1), hash(track2))

    def test_eq_name(self):
        track1 = Track(name='name1')
        track2 = Track(name='name1')
        self.assertEqual(track1, track2)
        self.assertEqual(hash(track1), hash(track2))

    def test_eq_artists(self):
        artists = [Artist()]
        track1 = Track(artists=artists)
        track2 = Track(artists=artists)
        self.assertEqual(track1, track2)
        self.assertEqual(hash(track1), hash(track2))

    def test_eq_artists_order(self):
        artist1 = Artist(name='name1')
        artist2 = Artist(name='name2')
        track1 = Track(artists=[artist1, artist2])
        track2 = Track(artists=[artist2, artist1])
        self.assertEqual(track1, track2)
        self.assertEqual(hash(track1), hash(track2))

    def test_eq_album(self):
        album = Album()
        track1 = Track(album=album)
        track2 = Track(album=album)
        self.assertEqual(track1, track2)
        self.assertEqual(hash(track1), hash(track2))

    def test_eq_track_no(self):
        track1 = Track(track_no=1)
        track2 = Track(track_no=1)
        self.assertEqual(track1, track2)
        self.assertEqual(hash(track1), hash(track2))

    def test_eq_date(self):
        date = '1977-01-01'
        track1 = Track(date=date)
        track2 = Track(date=date)
        self.assertEqual(track1, track2)
        self.assertEqual(hash(track1), hash(track2))

    def test_eq_length(self):
        track1 = Track(length=100)
        track2 = Track(length=100)
        self.assertEqual(track1, track2)
        self.assertEqual(hash(track1), hash(track2))

    def test_eq_bitrate(self):
        track1 = Track(bitrate=100)
        track2 = Track(bitrate=100)
        self.assertEqual(track1, track2)
        self.assertEqual(hash(track1), hash(track2))

    def test_eq_musibrainz_id(self):
        track1 = Track(musicbrainz_id='id')
        track2 = Track(musicbrainz_id='id')
        self.assertEqual(track1, track2)
        self.assertEqual(hash(track1), hash(track2))

    def test_eq(self):
        date = '1977-01-01'
        artists = [Artist()]
        album = Album()
        track1 = Track(
            uri='uri', name='name', artists=artists, album=album, track_no=1,
            date=date, length=100, bitrate=100, musicbrainz_id='id')
        track2 = Track(
            uri='uri', name='name', artists=artists, album=album, track_no=1,
            date=date, length=100, bitrate=100, musicbrainz_id='id')
        self.assertEqual(track1, track2)
        self.assertEqual(hash(track1), hash(track2))

    def test_eq_none(self):
        self.assertNotEqual(Track(), None)

    def test_eq_other(self):
        self.assertNotEqual(Track(), 'other')

    def test_ne_uri(self):
        track1 = Track(uri='uri1')
        track2 = Track(uri='uri2')
        self.assertNotEqual(track1, track2)
        self.assertNotEqual(hash(track1), hash(track2))

    def test_ne_name(self):
        track1 = Track(name='name1')
        track2 = Track(name='name2')
        self.assertNotEqual(track1, track2)
        self.assertNotEqual(hash(track1), hash(track2))

    def test_ne_artists(self):
        track1 = Track(artists=[Artist(name='name1')])
        track2 = Track(artists=[Artist(name='name2')])
        self.assertNotEqual(track1, track2)
        self.assertNotEqual(hash(track1), hash(track2))

    def test_ne_album(self):
        track1 = Track(album=Album(name='name1'))
        track2 = Track(album=Album(name='name2'))
        self.assertNotEqual(track1, track2)
        self.assertNotEqual(hash(track1), hash(track2))

    def test_ne_track_no(self):
        track1 = Track(track_no=1)
        track2 = Track(track_no=2)
        self.assertNotEqual(track1, track2)
        self.assertNotEqual(hash(track1), hash(track2))

    def test_ne_date(self):
        track1 = Track(date='1977-01-01')
        track2 = Track(date='1977-01-02')
        self.assertNotEqual(track1, track2)
        self.assertNotEqual(hash(track1), hash(track2))

    def test_ne_length(self):
        track1 = Track(length=100)
        track2 = Track(length=200)
        self.assertNotEqual(track1, track2)
        self.assertNotEqual(hash(track1), hash(track2))

    def test_ne_bitrate(self):
        track1 = Track(bitrate=100)
        track2 = Track(bitrate=200)
        self.assertNotEqual(track1, track2)
        self.assertNotEqual(hash(track1), hash(track2))

    def test_ne_musicbrainz_id(self):
        track1 = Track(musicbrainz_id='id1')
        track2 = Track(musicbrainz_id='id2')
        self.assertNotEqual(track1, track2)
        self.assertNotEqual(hash(track1), hash(track2))

    def test_ne(self):
        track1 = Track(
            uri='uri1', name='name1', artists=[Artist(name='name1')],
            album=Album(name='name1'), track_no=1, date='1977-01-01',
            length=100, bitrate=100, musicbrainz_id='id1')
        track2 = Track(
            uri='uri2', name='name2', artists=[Artist(name='name2')],
            album=Album(name='name2'), track_no=2, date='1977-01-02',
            length=200, bitrate=200, musicbrainz_id='id2')
        self.assertNotEqual(track1, track2)
        self.assertNotEqual(hash(track1), hash(track2))


class TlTrackTest(unittest.TestCase):
    def test_tlid(self):
        tlid = 123
        tl_track = TlTrack(tlid=tlid)
        self.assertEqual(tl_track.tlid, tlid)
        self.assertRaises(AttributeError, setattr, tl_track, 'tlid', None)

    def test_track(self):
        track = Track()
        tl_track = TlTrack(track=track)
        self.assertEqual(tl_track.track, track)
        self.assertRaises(AttributeError, setattr, tl_track, 'track', None)

    def test_invalid_kwarg(self):
        test = lambda: TlTrack(foo='baz')
        self.assertRaises(TypeError, test)

    def test_positional_args(self):
        tlid = 123
        track = Track()
        tl_track = TlTrack(tlid, track)
        self.assertEqual(tl_track.tlid, tlid)
        self.assertEqual(tl_track.track, track)

    def test_iteration(self):
        tlid = 123
        track = Track()
        tl_track = TlTrack(tlid, track)
        (tlid2, track2) = tl_track
        self.assertEqual(tlid2, tlid)
        self.assertEqual(track2, track)

    def test_repr(self):
        self.assertEquals(
            "TlTrack(tlid=123, track=Track(artists=[], composers=[], "
            "performers=[], uri=u'uri'))",
            repr(TlTrack(tlid=123, track=Track(uri='uri'))))

    def test_serialize(self):
        track = Track(uri='uri', name='name')
        self.assertDictEqual(
            {'__model__': 'TlTrack', 'tlid': 123, 'track': track.serialize()},
            TlTrack(tlid=123, track=track).serialize())

    def test_to_json_and_back(self):
        tl_track1 = TlTrack(tlid=123, track=Track(uri='uri', name='name'))
        serialized = json.dumps(tl_track1, cls=ModelJSONEncoder)
        tl_track2 = json.loads(serialized, object_hook=model_json_decoder)
        self.assertEqual(tl_track1, tl_track2)

    def test_eq(self):
        tlid = 123
        track = Track()
        tl_track1 = TlTrack(tlid=tlid, track=track)
        tl_track2 = TlTrack(tlid=tlid, track=track)
        self.assertEqual(tl_track1, tl_track2)
        self.assertEqual(hash(tl_track1), hash(tl_track2))

    def test_eq_none(self):
        self.assertNotEqual(TlTrack(), None)

    def test_eq_other(self):
        self.assertNotEqual(TlTrack(), 'other')

    def test_ne_tlid(self):
        tl_track1 = TlTrack(tlid=123)
        tl_track2 = TlTrack(tlid=321)
        self.assertNotEqual(tl_track1, tl_track2)
        self.assertNotEqual(hash(tl_track1), hash(tl_track2))

    def test_ne_track(self):
        tl_track1 = TlTrack(track=Track(uri='a'))
        tl_track2 = TlTrack(track=Track(uri='b'))
        self.assertNotEqual(tl_track1, tl_track2)
        self.assertNotEqual(hash(tl_track1), hash(tl_track2))


class PlaylistTest(unittest.TestCase):
    def test_uri(self):
        uri = 'an_uri'
        playlist = Playlist(uri=uri)
        self.assertEqual(playlist.uri, uri)
        self.assertRaises(AttributeError, setattr, playlist, 'uri', None)

    def test_name(self):
        name = 'a name'
        playlist = Playlist(name=name)
        self.assertEqual(playlist.name, name)
        self.assertRaises(AttributeError, setattr, playlist, 'name', None)

    def test_tracks(self):
        tracks = [Track(), Track(), Track()]
        playlist = Playlist(tracks=tracks)
        self.assertEqual(list(playlist.tracks), tracks)
        self.assertRaises(AttributeError, setattr, playlist, 'tracks', None)

    def test_length(self):
        tracks = [Track(), Track(), Track()]
        playlist = Playlist(tracks=tracks)
        self.assertEqual(playlist.length, 3)

    def test_last_modified(self):
        last_modified = 1390942873000
        playlist = Playlist(last_modified=last_modified)
        self.assertEqual(playlist.last_modified, last_modified)
        self.assertRaises(
            AttributeError, setattr, playlist, 'last_modified', None)

    def test_with_new_uri(self):
        tracks = [Track()]
        last_modified = 1390942873000
        playlist = Playlist(
            uri='an uri', name='a name', tracks=tracks,
            last_modified=last_modified)
        new_playlist = playlist.copy(uri='another uri')
        self.assertEqual(new_playlist.uri, 'another uri')
        self.assertEqual(new_playlist.name, 'a name')
        self.assertEqual(list(new_playlist.tracks), tracks)
        self.assertEqual(new_playlist.last_modified, last_modified)

    def test_with_new_name(self):
        tracks = [Track()]
        last_modified = 1390942873000
        playlist = Playlist(
            uri='an uri', name='a name', tracks=tracks,
            last_modified=last_modified)
        new_playlist = playlist.copy(name='another name')
        self.assertEqual(new_playlist.uri, 'an uri')
        self.assertEqual(new_playlist.name, 'another name')
        self.assertEqual(list(new_playlist.tracks), tracks)
        self.assertEqual(new_playlist.last_modified, last_modified)

    def test_with_new_tracks(self):
        tracks = [Track()]
        last_modified = 1390942873000
        playlist = Playlist(
            uri='an uri', name='a name', tracks=tracks,
            last_modified=last_modified)
        new_tracks = [Track(), Track()]
        new_playlist = playlist.copy(tracks=new_tracks)
        self.assertEqual(new_playlist.uri, 'an uri')
        self.assertEqual(new_playlist.name, 'a name')
        self.assertEqual(list(new_playlist.tracks), new_tracks)
        self.assertEqual(new_playlist.last_modified, last_modified)

    def test_with_new_last_modified(self):
        tracks = [Track()]
        last_modified = 1390942873000
        new_last_modified = last_modified + 1000
        playlist = Playlist(
            uri='an uri', name='a name', tracks=tracks,
            last_modified=last_modified)
        new_playlist = playlist.copy(last_modified=new_last_modified)
        self.assertEqual(new_playlist.uri, 'an uri')
        self.assertEqual(new_playlist.name, 'a name')
        self.assertEqual(list(new_playlist.tracks), tracks)
        self.assertEqual(new_playlist.last_modified, new_last_modified)

    def test_invalid_kwarg(self):
        test = lambda: Playlist(foo='baz')
        self.assertRaises(TypeError, test)

    def test_repr_without_tracks(self):
        self.assertEquals(
            "Playlist(name=u'name', tracks=[], uri=u'uri')",
            repr(Playlist(uri='uri', name='name')))

    def test_repr_with_tracks(self):
        self.assertEquals(
            "Playlist(name=u'name', tracks=[Track(artists=[], composers=[], "
            "name=u'foo', performers=[])], uri=u'uri')",
            repr(Playlist(uri='uri', name='name', tracks=[Track(name='foo')])))

    def test_serialize_without_tracks(self):
        self.assertDictEqual(
            {'__model__': 'Playlist', 'uri': 'uri', 'name': 'name'},
            Playlist(uri='uri', name='name').serialize())

    def test_serialize_with_tracks(self):
        track = Track(name='foo')
        self.assertDictEqual(
            {'__model__': 'Playlist', 'uri': 'uri', 'name': 'name',
                'tracks': [track.serialize()]},
            Playlist(uri='uri', name='name', tracks=[track]).serialize())

    def test_to_json_and_back(self):
        playlist1 = Playlist(uri='uri', name='name')
        serialized = json.dumps(playlist1, cls=ModelJSONEncoder)
        playlist2 = json.loads(serialized, object_hook=model_json_decoder)
        self.assertEqual(playlist1, playlist2)

    def test_eq_name(self):
        playlist1 = Playlist(name='name')
        playlist2 = Playlist(name='name')
        self.assertEqual(playlist1, playlist2)
        self.assertEqual(hash(playlist1), hash(playlist2))

    def test_eq_uri(self):
        playlist1 = Playlist(uri='uri')
        playlist2 = Playlist(uri='uri')
        self.assertEqual(playlist1, playlist2)
        self.assertEqual(hash(playlist1), hash(playlist2))

    def test_eq_tracks(self):
        tracks = [Track()]
        playlist1 = Playlist(tracks=tracks)
        playlist2 = Playlist(tracks=tracks)
        self.assertEqual(playlist1, playlist2)
        self.assertEqual(hash(playlist1), hash(playlist2))

    def test_eq_last_modified(self):
        playlist1 = Playlist(last_modified=1)
        playlist2 = Playlist(last_modified=1)
        self.assertEqual(playlist1, playlist2)
        self.assertEqual(hash(playlist1), hash(playlist2))

    def test_eq(self):
        tracks = [Track()]
        playlist1 = Playlist(
            uri='uri', name='name', tracks=tracks, last_modified=1)
        playlist2 = Playlist(
            uri='uri', name='name', tracks=tracks, last_modified=1)
        self.assertEqual(playlist1, playlist2)
        self.assertEqual(hash(playlist1), hash(playlist2))

    def test_eq_none(self):
        self.assertNotEqual(Playlist(), None)

    def test_eq_other(self):
        self.assertNotEqual(Playlist(), 'other')

    def test_ne_name(self):
        playlist1 = Playlist(name='name1')
        playlist2 = Playlist(name='name2')
        self.assertNotEqual(playlist1, playlist2)
        self.assertNotEqual(hash(playlist1), hash(playlist2))

    def test_ne_uri(self):
        playlist1 = Playlist(uri='uri1')
        playlist2 = Playlist(uri='uri2')
        self.assertNotEqual(playlist1, playlist2)
        self.assertNotEqual(hash(playlist1), hash(playlist2))

    def test_ne_tracks(self):
        playlist1 = Playlist(tracks=[Track(uri='uri1')])
        playlist2 = Playlist(tracks=[Track(uri='uri2')])
        self.assertNotEqual(playlist1, playlist2)
        self.assertNotEqual(hash(playlist1), hash(playlist2))

    def test_ne_last_modified(self):
        playlist1 = Playlist(last_modified=1)
        playlist2 = Playlist(last_modified=2)
        self.assertNotEqual(playlist1, playlist2)
        self.assertNotEqual(hash(playlist1), hash(playlist2))

    def test_ne(self):
        playlist1 = Playlist(
            uri='uri1', name='name1', tracks=[Track(uri='uri1')],
            last_modified=1)
        playlist2 = Playlist(
            uri='uri2', name='name2', tracks=[Track(uri='uri2')],
            last_modified=2)
        self.assertNotEqual(playlist1, playlist2)
        self.assertNotEqual(hash(playlist1), hash(playlist2))


class SearchResultTest(unittest.TestCase):
    def test_uri(self):
        uri = 'an_uri'
        result = SearchResult(uri=uri)
        self.assertEqual(result.uri, uri)
        self.assertRaises(AttributeError, setattr, result, 'uri', None)

    def test_tracks(self):
        tracks = [Track(), Track(), Track()]
        result = SearchResult(tracks=tracks)
        self.assertEqual(list(result.tracks), tracks)
        self.assertRaises(AttributeError, setattr, result, 'tracks', None)

    def test_artists(self):
        artists = [Artist(), Artist(), Artist()]
        result = SearchResult(artists=artists)
        self.assertEqual(list(result.artists), artists)
        self.assertRaises(AttributeError, setattr, result, 'artists', None)

    def test_albums(self):
        albums = [Album(), Album(), Album()]
        result = SearchResult(albums=albums)
        self.assertEqual(list(result.albums), albums)
        self.assertRaises(AttributeError, setattr, result, 'albums', None)

    def test_invalid_kwarg(self):
        test = lambda: SearchResult(foo='baz')
        self.assertRaises(TypeError, test)

    def test_repr_without_results(self):
        self.assertEquals(
            "SearchResult(albums=[], artists=[], tracks=[], uri=u'uri')",
            repr(SearchResult(uri='uri')))

    def test_serialize_without_results(self):
        self.assertDictEqual(
            {'__model__': 'SearchResult', 'uri': 'uri'},
            SearchResult(uri='uri').serialize())

    def test_to_json_and_back(self):
        result1 = SearchResult(uri='uri')
        serialized = json.dumps(result1, cls=ModelJSONEncoder)
        result2 = json.loads(serialized, object_hook=model_json_decoder)
        self.assertEqual(result1, result2)

########NEW FILE########
__FILENAME__ = test_version
from __future__ import unicode_literals

import unittest
from distutils.version import StrictVersion as SV

from mopidy import __version__


class VersionTest(unittest.TestCase):
    def test_current_version_is_parsable_as_a_strict_version_number(self):
        SV(__version__)

    def test_versions_can_be_strictly_ordered(self):
        self.assertLess(SV('0.1.0a0'), SV('0.1.0a1'))
        self.assertLess(SV('0.1.0a1'), SV('0.1.0a2'))
        self.assertLess(SV('0.1.0a2'), SV('0.1.0a3'))
        self.assertLess(SV('0.1.0a3'), SV('0.1.0'))
        self.assertLess(SV('0.1.0'), SV('0.2.0'))
        self.assertLess(SV('0.1.0'), SV('1.0.0'))
        self.assertLess(SV('0.2.0'), SV('0.3.0'))
        self.assertLess(SV('0.3.0'), SV('0.3.1'))
        self.assertLess(SV('0.3.1'), SV('0.4.0'))
        self.assertLess(SV('0.4.0'), SV('0.4.1'))
        self.assertLess(SV('0.4.1'), SV('0.5.0'))
        self.assertLess(SV('0.5.0'), SV('0.6.0'))
        self.assertLess(SV('0.6.0'), SV('0.6.1'))
        self.assertLess(SV('0.6.1'), SV('0.7.0'))
        self.assertLess(SV('0.7.0'), SV('0.7.1'))
        self.assertLess(SV('0.7.1'), SV('0.7.2'))
        self.assertLess(SV('0.7.2'), SV('0.7.3'))
        self.assertLess(SV('0.7.3'), SV('0.8.0'))
        self.assertLess(SV('0.8.0'), SV('0.8.1'))
        self.assertLess(SV('0.8.1'), SV('0.9.0'))
        self.assertLess(SV('0.9.0'), SV('0.10.0'))
        self.assertLess(SV('0.10.0'), SV('0.11.0'))
        self.assertLess(SV('0.11.0'), SV('0.11.1'))
        self.assertLess(SV('0.11.1'), SV('0.12.0'))
        self.assertLess(SV('0.12.0'), SV('0.13.0'))
        self.assertLess(SV('0.13.0'), SV('0.14.0'))
        self.assertLess(SV('0.14.0'), SV('0.14.1'))
        self.assertLess(SV('0.14.1'), SV('0.14.2'))
        self.assertLess(SV('0.14.2'), SV('0.15.0'))
        self.assertLess(SV('0.15.0'), SV('0.16.0'))
        self.assertLess(SV('0.16.0'), SV('0.17.0'))
        self.assertLess(SV('0.17.0'), SV('0.18.0'))
        self.assertLess(SV('0.18.0'), SV('0.18.1'))
        self.assertLess(SV('0.18.1'), SV('0.18.2'))
        self.assertLess(SV('0.18.2'), SV(__version__))
        self.assertLess(SV(__version__), SV('0.18.4'))

########NEW FILE########
__FILENAME__ = test_connection
from __future__ import unicode_literals

import errno
import logging
import socket
import unittest

import gobject

from mock import Mock, patch, sentinel

import pykka

from mopidy.utils import network

from tests import any_int, any_unicode


class ConnectionTest(unittest.TestCase):
    def setUp(self):
        self.mock = Mock(spec=network.Connection)

    def test_init_ensure_nonblocking_io(self):
        sock = Mock(spec=socket.SocketType)

        network.Connection.__init__(
            self.mock, Mock(), {}, sock, (sentinel.host, sentinel.port),
            sentinel.timeout)
        sock.setblocking.assert_called_once_with(False)

    def test_init_starts_actor(self):
        protocol = Mock(spec=network.LineProtocol)

        network.Connection.__init__(
            self.mock, protocol, {}, Mock(), (sentinel.host, sentinel.port),
            sentinel.timeout)
        protocol.start.assert_called_once_with(self.mock)

    def test_init_enables_recv_and_timeout(self):
        network.Connection.__init__(
            self.mock, Mock(), {}, Mock(), (sentinel.host, sentinel.port),
            sentinel.timeout)
        self.mock.enable_recv.assert_called_once_with()
        self.mock.enable_timeout.assert_called_once_with()

    def test_init_stores_values_in_attributes(self):
        addr = (sentinel.host, sentinel.port)
        protocol = Mock(spec=network.LineProtocol)
        protocol_kwargs = {}
        sock = Mock(spec=socket.SocketType)

        network.Connection.__init__(
            self.mock, protocol, protocol_kwargs, sock, addr, sentinel.timeout)
        self.assertEqual(sock, self.mock.sock)
        self.assertEqual(protocol, self.mock.protocol)
        self.assertEqual(protocol_kwargs, self.mock.protocol_kwargs)
        self.assertEqual(sentinel.timeout, self.mock.timeout)
        self.assertEqual(sentinel.host, self.mock.host)
        self.assertEqual(sentinel.port, self.mock.port)

    def test_init_handles_ipv6_addr(self):
        addr = (
            sentinel.host, sentinel.port, sentinel.flowinfo, sentinel.scopeid)
        protocol = Mock(spec=network.LineProtocol)
        protocol_kwargs = {}
        sock = Mock(spec=socket.SocketType)

        network.Connection.__init__(
            self.mock, protocol, protocol_kwargs, sock, addr, sentinel.timeout)
        self.assertEqual(sentinel.host, self.mock.host)
        self.assertEqual(sentinel.port, self.mock.port)

    def test_stop_disables_recv_send_and_timeout(self):
        self.mock.stopping = False
        self.mock.actor_ref = Mock()
        self.mock.sock = Mock(spec=socket.SocketType)

        network.Connection.stop(self.mock, sentinel.reason)
        self.mock.disable_timeout.assert_called_once_with()
        self.mock.disable_recv.assert_called_once_with()
        self.mock.disable_send.assert_called_once_with()

    def test_stop_closes_socket(self):
        self.mock.stopping = False
        self.mock.actor_ref = Mock()
        self.mock.sock = Mock(spec=socket.SocketType)

        network.Connection.stop(self.mock, sentinel.reason)
        self.mock.sock.close.assert_called_once_with()

    def test_stop_closes_socket_error(self):
        self.mock.stopping = False
        self.mock.actor_ref = Mock()
        self.mock.sock = Mock(spec=socket.SocketType)
        self.mock.sock.close.side_effect = socket.error

        network.Connection.stop(self.mock, sentinel.reason)
        self.mock.sock.close.assert_called_once_with()

    def test_stop_stops_actor(self):
        self.mock.stopping = False
        self.mock.actor_ref = Mock()
        self.mock.sock = Mock(spec=socket.SocketType)

        network.Connection.stop(self.mock, sentinel.reason)
        self.mock.actor_ref.stop.assert_called_once_with(block=False)

    def test_stop_handles_actor_already_being_stopped(self):
        self.mock.stopping = False
        self.mock.actor_ref = Mock()
        self.mock.actor_ref.stop.side_effect = pykka.ActorDeadError()
        self.mock.sock = Mock(spec=socket.SocketType)

        network.Connection.stop(self.mock, sentinel.reason)
        self.mock.actor_ref.stop.assert_called_once_with(block=False)

    def test_stop_sets_stopping_to_true(self):
        self.mock.stopping = False
        self.mock.actor_ref = Mock()
        self.mock.sock = Mock(spec=socket.SocketType)

        network.Connection.stop(self.mock, sentinel.reason)
        self.assertEqual(True, self.mock.stopping)

    def test_stop_does_not_proceed_when_already_stopping(self):
        self.mock.stopping = True
        self.mock.actor_ref = Mock()
        self.mock.sock = Mock(spec=socket.SocketType)

        network.Connection.stop(self.mock, sentinel.reason)
        self.assertEqual(0, self.mock.actor_ref.stop.call_count)
        self.assertEqual(0, self.mock.sock.close.call_count)

    @patch.object(network.logger, 'log', new=Mock())
    def test_stop_logs_reason(self):
        self.mock.stopping = False
        self.mock.actor_ref = Mock()
        self.mock.sock = Mock(spec=socket.SocketType)

        network.Connection.stop(self.mock, sentinel.reason)
        network.logger.log.assert_called_once_with(
            logging.DEBUG, sentinel.reason)

    @patch.object(network.logger, 'log', new=Mock())
    def test_stop_logs_reason_with_level(self):
        self.mock.stopping = False
        self.mock.actor_ref = Mock()
        self.mock.sock = Mock(spec=socket.SocketType)

        network.Connection.stop(
            self.mock, sentinel.reason, level=sentinel.level)
        network.logger.log.assert_called_once_with(
            sentinel.level, sentinel.reason)

    @patch.object(network.logger, 'log', new=Mock())
    def test_stop_logs_that_it_is_calling_itself(self):
        self.mock.stopping = True
        self.mock.actor_ref = Mock()
        self.mock.sock = Mock(spec=socket.SocketType)

        network.Connection.stop(self.mock, sentinel.reason)
        network.logger.log(any_int, any_unicode)

    @patch.object(gobject, 'io_add_watch', new=Mock())
    def test_enable_recv_registers_with_gobject(self):
        self.mock.recv_id = None
        self.mock.sock = Mock(spec=socket.SocketType)
        self.mock.sock.fileno.return_value = sentinel.fileno
        gobject.io_add_watch.return_value = sentinel.tag

        network.Connection.enable_recv(self.mock)
        gobject.io_add_watch.assert_called_once_with(
            sentinel.fileno,
            gobject.IO_IN | gobject.IO_ERR | gobject.IO_HUP,
            self.mock.recv_callback)
        self.assertEqual(sentinel.tag, self.mock.recv_id)

    @patch.object(gobject, 'io_add_watch', new=Mock())
    def test_enable_recv_already_registered(self):
        self.mock.sock = Mock(spec=socket.SocketType)
        self.mock.recv_id = sentinel.tag

        network.Connection.enable_recv(self.mock)
        self.assertEqual(0, gobject.io_add_watch.call_count)

    def test_enable_recv_does_not_change_tag(self):
        self.mock.recv_id = sentinel.tag
        self.mock.sock = Mock(spec=socket.SocketType)

        network.Connection.enable_recv(self.mock)
        self.assertEqual(sentinel.tag, self.mock.recv_id)

    @patch.object(gobject, 'source_remove', new=Mock())
    def test_disable_recv_deregisters(self):
        self.mock.recv_id = sentinel.tag

        network.Connection.disable_recv(self.mock)
        gobject.source_remove.assert_called_once_with(sentinel.tag)
        self.assertEqual(None, self.mock.recv_id)

    @patch.object(gobject, 'source_remove', new=Mock())
    def test_disable_recv_already_deregistered(self):
        self.mock.recv_id = None

        network.Connection.disable_recv(self.mock)
        self.assertEqual(0, gobject.source_remove.call_count)
        self.assertEqual(None, self.mock.recv_id)

    def test_enable_recv_on_closed_socket(self):
        self.mock.recv_id = None
        self.mock.sock = Mock(spec=socket.SocketType)
        self.mock.sock.fileno.side_effect = socket.error(errno.EBADF, '')

        network.Connection.enable_recv(self.mock)
        self.mock.stop.assert_called_once_with(any_unicode)
        self.assertEqual(None, self.mock.recv_id)

    @patch.object(gobject, 'io_add_watch', new=Mock())
    def test_enable_send_registers_with_gobject(self):
        self.mock.send_id = None
        self.mock.sock = Mock(spec=socket.SocketType)
        self.mock.sock.fileno.return_value = sentinel.fileno
        gobject.io_add_watch.return_value = sentinel.tag

        network.Connection.enable_send(self.mock)
        gobject.io_add_watch.assert_called_once_with(
            sentinel.fileno,
            gobject.IO_OUT | gobject.IO_ERR | gobject.IO_HUP,
            self.mock.send_callback)
        self.assertEqual(sentinel.tag, self.mock.send_id)

    @patch.object(gobject, 'io_add_watch', new=Mock())
    def test_enable_send_already_registered(self):
        self.mock.sock = Mock(spec=socket.SocketType)
        self.mock.send_id = sentinel.tag

        network.Connection.enable_send(self.mock)
        self.assertEqual(0, gobject.io_add_watch.call_count)

    def test_enable_send_does_not_change_tag(self):
        self.mock.send_id = sentinel.tag
        self.mock.sock = Mock(spec=socket.SocketType)

        network.Connection.enable_send(self.mock)
        self.assertEqual(sentinel.tag, self.mock.send_id)

    @patch.object(gobject, 'source_remove', new=Mock())
    def test_disable_send_deregisters(self):
        self.mock.send_id = sentinel.tag

        network.Connection.disable_send(self.mock)
        gobject.source_remove.assert_called_once_with(sentinel.tag)
        self.assertEqual(None, self.mock.send_id)

    @patch.object(gobject, 'source_remove', new=Mock())
    def test_disable_send_already_deregistered(self):
        self.mock.send_id = None

        network.Connection.disable_send(self.mock)
        self.assertEqual(0, gobject.source_remove.call_count)
        self.assertEqual(None, self.mock.send_id)

    def test_enable_send_on_closed_socket(self):
        self.mock.send_id = None
        self.mock.sock = Mock(spec=socket.SocketType)
        self.mock.sock.fileno.side_effect = socket.error(errno.EBADF, '')

        network.Connection.enable_send(self.mock)
        self.assertEqual(None, self.mock.send_id)

    @patch.object(gobject, 'timeout_add_seconds', new=Mock())
    def test_enable_timeout_clears_existing_timeouts(self):
        self.mock.timeout = 10

        network.Connection.enable_timeout(self.mock)
        self.mock.disable_timeout.assert_called_once_with()

    @patch.object(gobject, 'timeout_add_seconds', new=Mock())
    def test_enable_timeout_add_gobject_timeout(self):
        self.mock.timeout = 10
        gobject.timeout_add_seconds.return_value = sentinel.tag

        network.Connection.enable_timeout(self.mock)
        gobject.timeout_add_seconds.assert_called_once_with(
            10, self.mock.timeout_callback)
        self.assertEqual(sentinel.tag, self.mock.timeout_id)

    @patch.object(gobject, 'timeout_add_seconds', new=Mock())
    def test_enable_timeout_does_not_add_timeout(self):
        self.mock.timeout = 0
        network.Connection.enable_timeout(self.mock)
        self.assertEqual(0, gobject.timeout_add_seconds.call_count)

        self.mock.timeout = -1
        network.Connection.enable_timeout(self.mock)
        self.assertEqual(0, gobject.timeout_add_seconds.call_count)

        self.mock.timeout = None
        network.Connection.enable_timeout(self.mock)
        self.assertEqual(0, gobject.timeout_add_seconds.call_count)

    def test_enable_timeout_does_not_call_disable_for_invalid_timeout(self):
        self.mock.timeout = 0
        network.Connection.enable_timeout(self.mock)
        self.assertEqual(0, self.mock.disable_timeout.call_count)

        self.mock.timeout = -1
        network.Connection.enable_timeout(self.mock)
        self.assertEqual(0, self.mock.disable_timeout.call_count)

        self.mock.timeout = None
        network.Connection.enable_timeout(self.mock)
        self.assertEqual(0, self.mock.disable_timeout.call_count)

    @patch.object(gobject, 'source_remove', new=Mock())
    def test_disable_timeout_deregisters(self):
        self.mock.timeout_id = sentinel.tag

        network.Connection.disable_timeout(self.mock)
        gobject.source_remove.assert_called_once_with(sentinel.tag)
        self.assertEqual(None, self.mock.timeout_id)

    @patch.object(gobject, 'source_remove', new=Mock())
    def test_disable_timeout_already_deregistered(self):
        self.mock.timeout_id = None

        network.Connection.disable_timeout(self.mock)
        self.assertEqual(0, gobject.source_remove.call_count)
        self.assertEqual(None, self.mock.timeout_id)

    def test_queue_send_acquires_and_releases_lock(self):
        self.mock.send_lock = Mock()
        self.mock.send_buffer = ''

        network.Connection.queue_send(self.mock, 'data')
        self.mock.send_lock.acquire.assert_called_once_with(True)
        self.mock.send_lock.release.assert_called_once_with()

    def test_queue_send_calls_send(self):
        self.mock.send_buffer = ''
        self.mock.send_lock = Mock()
        self.mock.send.return_value = ''

        network.Connection.queue_send(self.mock, 'data')
        self.mock.send.assert_called_once_with('data')
        self.assertEqual(0, self.mock.enable_send.call_count)
        self.assertEqual('', self.mock.send_buffer)

    def test_queue_send_calls_enable_send_for_partial_send(self):
        self.mock.send_buffer = ''
        self.mock.send_lock = Mock()
        self.mock.send.return_value = 'ta'

        network.Connection.queue_send(self.mock, 'data')
        self.mock.send.assert_called_once_with('data')
        self.mock.enable_send.assert_called_once_with()
        self.assertEqual('ta', self.mock.send_buffer)

    def test_queue_send_calls_send_with_existing_buffer(self):
        self.mock.send_buffer = 'foo'
        self.mock.send_lock = Mock()
        self.mock.send.return_value = ''

        network.Connection.queue_send(self.mock, 'bar')
        self.mock.send.assert_called_once_with('foobar')
        self.assertEqual(0, self.mock.enable_send.call_count)
        self.assertEqual('', self.mock.send_buffer)

    def test_recv_callback_respects_io_err(self):
        self.mock.sock = Mock(spec=socket.SocketType)
        self.mock.actor_ref = Mock()

        self.assertTrue(network.Connection.recv_callback(
            self.mock, sentinel.fd, gobject.IO_IN | gobject.IO_ERR))
        self.mock.stop.assert_called_once_with(any_unicode)

    def test_recv_callback_respects_io_hup(self):
        self.mock.sock = Mock(spec=socket.SocketType)
        self.mock.actor_ref = Mock()

        self.assertTrue(network.Connection.recv_callback(
            self.mock, sentinel.fd, gobject.IO_IN | gobject.IO_HUP))
        self.mock.stop.assert_called_once_with(any_unicode)

    def test_recv_callback_respects_io_hup_and_io_err(self):
        self.mock.sock = Mock(spec=socket.SocketType)
        self.mock.actor_ref = Mock()

        self.assertTrue(network.Connection.recv_callback(
            self.mock, sentinel.fd,
            gobject.IO_IN | gobject.IO_HUP | gobject.IO_ERR))
        self.mock.stop.assert_called_once_with(any_unicode)

    def test_recv_callback_sends_data_to_actor(self):
        self.mock.sock = Mock(spec=socket.SocketType)
        self.mock.sock.recv.return_value = 'data'
        self.mock.actor_ref = Mock()

        self.assertTrue(network.Connection.recv_callback(
            self.mock, sentinel.fd, gobject.IO_IN))
        self.mock.actor_ref.tell.assert_called_once_with(
            {'received': 'data'})

    def test_recv_callback_handles_dead_actors(self):
        self.mock.sock = Mock(spec=socket.SocketType)
        self.mock.sock.recv.return_value = 'data'
        self.mock.actor_ref = Mock()
        self.mock.actor_ref.tell.side_effect = pykka.ActorDeadError()

        self.assertTrue(network.Connection.recv_callback(
            self.mock, sentinel.fd, gobject.IO_IN))
        self.mock.stop.assert_called_once_with(any_unicode)

    def test_recv_callback_gets_no_data(self):
        self.mock.sock = Mock(spec=socket.SocketType)
        self.mock.sock.recv.return_value = ''
        self.mock.actor_ref = Mock()

        self.assertTrue(network.Connection.recv_callback(
            self.mock, sentinel.fd, gobject.IO_IN))
        self.mock.actor_ref.tell.assert_called_once_with({'close': True})
        self.mock.disable_recv.assert_called_once_with()

    def test_recv_callback_recoverable_error(self):
        self.mock.sock = Mock(spec=socket.SocketType)

        for error in (errno.EWOULDBLOCK, errno.EINTR):
            self.mock.sock.recv.side_effect = socket.error(error, '')
            self.assertTrue(network.Connection.recv_callback(
                self.mock, sentinel.fd, gobject.IO_IN))
            self.assertEqual(0, self.mock.stop.call_count)

    def test_recv_callback_unrecoverable_error(self):
        self.mock.sock = Mock(spec=socket.SocketType)
        self.mock.sock.recv.side_effect = socket.error

        self.assertTrue(network.Connection.recv_callback(
            self.mock, sentinel.fd, gobject.IO_IN))
        self.mock.stop.assert_called_once_with(any_unicode)

    def test_send_callback_respects_io_err(self):
        self.mock.sock = Mock(spec=socket.SocketType)
        self.mock.sock.send.return_value = 1
        self.mock.send_lock = Mock()
        self.mock.actor_ref = Mock()
        self.mock.send_buffer = ''

        self.assertTrue(network.Connection.send_callback(
            self.mock, sentinel.fd, gobject.IO_IN | gobject.IO_ERR))
        self.mock.stop.assert_called_once_with(any_unicode)

    def test_send_callback_respects_io_hup(self):
        self.mock.sock = Mock(spec=socket.SocketType)
        self.mock.sock.send.return_value = 1
        self.mock.send_lock = Mock()
        self.mock.actor_ref = Mock()
        self.mock.send_buffer = ''

        self.assertTrue(network.Connection.send_callback(
            self.mock, sentinel.fd, gobject.IO_IN | gobject.IO_HUP))
        self.mock.stop.assert_called_once_with(any_unicode)

    def test_send_callback_respects_io_hup_and_io_err(self):
        self.mock.sock = Mock(spec=socket.SocketType)
        self.mock.sock.send.return_value = 1
        self.mock.send_lock = Mock()
        self.mock.actor_ref = Mock()
        self.mock.send_buffer = ''

        self.assertTrue(network.Connection.send_callback(
            self.mock, sentinel.fd,
            gobject.IO_IN | gobject.IO_HUP | gobject.IO_ERR))
        self.mock.stop.assert_called_once_with(any_unicode)

    def test_send_callback_acquires_and_releases_lock(self):
        self.mock.send_lock = Mock()
        self.mock.send_lock.acquire.return_value = True
        self.mock.send_buffer = ''
        self.mock.sock = Mock(spec=socket.SocketType)
        self.mock.sock.send.return_value = 0

        self.assertTrue(network.Connection.send_callback(
            self.mock, sentinel.fd, gobject.IO_IN))
        self.mock.send_lock.acquire.assert_called_once_with(False)
        self.mock.send_lock.release.assert_called_once_with()

    def test_send_callback_fails_to_acquire_lock(self):
        self.mock.send_lock = Mock()
        self.mock.send_lock.acquire.return_value = False
        self.mock.send_buffer = ''
        self.mock.sock = Mock(spec=socket.SocketType)
        self.mock.sock.send.return_value = 0

        self.assertTrue(network.Connection.send_callback(
            self.mock, sentinel.fd, gobject.IO_IN))
        self.mock.send_lock.acquire.assert_called_once_with(False)
        self.assertEqual(0, self.mock.sock.send.call_count)

    def test_send_callback_sends_all_data(self):
        self.mock.send_lock = Mock()
        self.mock.send_lock.acquire.return_value = True
        self.mock.send_buffer = 'data'
        self.mock.send.return_value = ''

        self.assertTrue(network.Connection.send_callback(
            self.mock, sentinel.fd, gobject.IO_IN))
        self.mock.disable_send.assert_called_once_with()
        self.mock.send.assert_called_once_with('data')
        self.assertEqual('', self.mock.send_buffer)

    def test_send_callback_sends_partial_data(self):
        self.mock.send_lock = Mock()
        self.mock.send_lock.acquire.return_value = True
        self.mock.send_buffer = 'data'
        self.mock.send.return_value = 'ta'

        self.assertTrue(network.Connection.send_callback(
            self.mock, sentinel.fd, gobject.IO_IN))
        self.mock.send.assert_called_once_with('data')
        self.assertEqual('ta', self.mock.send_buffer)

    def test_send_recoverable_error(self):
        self.mock.sock = Mock(spec=socket.SocketType)

        for error in (errno.EWOULDBLOCK, errno.EINTR):
            self.mock.sock.send.side_effect = socket.error(error, '')

            network.Connection.send(self.mock, 'data')
            self.assertEqual(0, self.mock.stop.call_count)

    def test_send_calls_socket_send(self):
        self.mock.sock = Mock(spec=socket.SocketType)
        self.mock.sock.send.return_value = 4

        self.assertEqual('', network.Connection.send(self.mock, 'data'))
        self.mock.sock.send.assert_called_once_with('data')

    def test_send_calls_socket_send_partial_send(self):
        self.mock.sock = Mock(spec=socket.SocketType)
        self.mock.sock.send.return_value = 2

        self.assertEqual('ta', network.Connection.send(self.mock, 'data'))
        self.mock.sock.send.assert_called_once_with('data')

    def test_send_unrecoverable_error(self):
        self.mock.sock = Mock(spec=socket.SocketType)
        self.mock.sock.send.side_effect = socket.error

        self.assertEqual('', network.Connection.send(self.mock, 'data'))
        self.mock.stop.assert_called_once_with(any_unicode)

    def test_timeout_callback(self):
        self.mock.timeout = 10

        self.assertFalse(network.Connection.timeout_callback(self.mock))
        self.mock.stop.assert_called_once_with(any_unicode)

########NEW FILE########
__FILENAME__ = test_lineprotocol
# encoding: utf-8

from __future__ import unicode_literals

import re
import unittest

from mock import Mock, sentinel

from mopidy.utils import network

from tests import any_unicode


class LineProtocolTest(unittest.TestCase):
    def setUp(self):
        self.mock = Mock(spec=network.LineProtocol)

        self.mock.terminator = network.LineProtocol.terminator
        self.mock.encoding = network.LineProtocol.encoding
        self.mock.delimiter = network.LineProtocol.delimiter
        self.mock.prevent_timeout = False

    def test_init_stores_values_in_attributes(self):
        delimiter = re.compile(network.LineProtocol.terminator)
        network.LineProtocol.__init__(self.mock, sentinel.connection)
        self.assertEqual(sentinel.connection, self.mock.connection)
        self.assertEqual('', self.mock.recv_buffer)
        self.assertEqual(delimiter, self.mock.delimiter)
        self.assertFalse(self.mock.prevent_timeout)

    def test_init_compiles_delimiter(self):
        self.mock.delimiter = '\r?\n'
        delimiter = re.compile('\r?\n')

        network.LineProtocol.__init__(self.mock, sentinel.connection)
        self.assertEqual(delimiter, self.mock.delimiter)

    def test_on_receive_close_calls_stop(self):
        self.mock.connection = Mock(spec=network.Connection)
        self.mock.recv_buffer = ''
        self.mock.parse_lines.return_value = []

        network.LineProtocol.on_receive(self.mock, {'close': True})
        self.mock.connection.stop.assert_called_once_with(any_unicode)

    def test_on_receive_no_new_lines_adds_to_recv_buffer(self):
        self.mock.connection = Mock(spec=network.Connection)
        self.mock.recv_buffer = ''
        self.mock.parse_lines.return_value = []

        network.LineProtocol.on_receive(self.mock, {'received': 'data'})
        self.assertEqual('data', self.mock.recv_buffer)
        self.mock.parse_lines.assert_called_once_with()
        self.assertEqual(0, self.mock.on_line_received.call_count)

    def test_on_receive_toggles_timeout(self):
        self.mock.connection = Mock(spec=network.Connection)
        self.mock.recv_buffer = ''
        self.mock.parse_lines.return_value = []

        network.LineProtocol.on_receive(self.mock, {'received': 'data'})
        self.mock.connection.disable_timeout.assert_called_once_with()
        self.mock.connection.enable_timeout.assert_called_once_with()

    def test_on_receive_toggles_unless_prevent_timeout_is_set(self):
        self.mock.connection = Mock(spec=network.Connection)
        self.mock.recv_buffer = ''
        self.mock.parse_lines.return_value = []
        self.mock.prevent_timeout = True

        network.LineProtocol.on_receive(self.mock, {'received': 'data'})
        self.mock.connection.disable_timeout.assert_called_once_with()
        self.assertEqual(0, self.mock.connection.enable_timeout.call_count)

    def test_on_receive_no_new_lines_calls_parse_lines(self):
        self.mock.connection = Mock(spec=network.Connection)
        self.mock.recv_buffer = ''
        self.mock.parse_lines.return_value = []

        network.LineProtocol.on_receive(self.mock, {'received': 'data'})
        self.mock.parse_lines.assert_called_once_with()
        self.assertEqual(0, self.mock.on_line_received.call_count)

    def test_on_receive_with_new_line_calls_decode(self):
        self.mock.connection = Mock(spec=network.Connection)
        self.mock.recv_buffer = ''
        self.mock.parse_lines.return_value = [sentinel.line]

        network.LineProtocol.on_receive(self.mock, {'received': 'data\n'})
        self.mock.parse_lines.assert_called_once_with()
        self.mock.decode.assert_called_once_with(sentinel.line)

    def test_on_receive_with_new_line_calls_on_recieve(self):
        self.mock.connection = Mock(spec=network.Connection)
        self.mock.recv_buffer = ''
        self.mock.parse_lines.return_value = [sentinel.line]
        self.mock.decode.return_value = sentinel.decoded

        network.LineProtocol.on_receive(self.mock, {'received': 'data\n'})
        self.mock.on_line_received.assert_called_once_with(sentinel.decoded)

    def test_on_receive_with_new_line_with_failed_decode(self):
        self.mock.connection = Mock(spec=network.Connection)
        self.mock.recv_buffer = ''
        self.mock.parse_lines.return_value = [sentinel.line]
        self.mock.decode.return_value = None

        network.LineProtocol.on_receive(self.mock, {'received': 'data\n'})
        self.assertEqual(0, self.mock.on_line_received.call_count)

    def test_on_receive_with_new_lines_calls_on_recieve(self):
        self.mock.connection = Mock(spec=network.Connection)
        self.mock.recv_buffer = ''
        self.mock.parse_lines.return_value = ['line1', 'line2']
        self.mock.decode.return_value = sentinel.decoded

        network.LineProtocol.on_receive(
            self.mock, {'received': 'line1\nline2\n'})
        self.assertEqual(2, self.mock.on_line_received.call_count)

    def test_parse_lines_emtpy_buffer(self):
        self.mock.delimiter = re.compile(r'\n')
        self.mock.recv_buffer = ''

        lines = network.LineProtocol.parse_lines(self.mock)
        self.assertRaises(StopIteration, lines.next)

    def test_parse_lines_no_terminator(self):
        self.mock.delimiter = re.compile(r'\n')
        self.mock.recv_buffer = 'data'

        lines = network.LineProtocol.parse_lines(self.mock)
        self.assertRaises(StopIteration, lines.next)

    def test_parse_lines_termintor(self):
        self.mock.delimiter = re.compile(r'\n')
        self.mock.recv_buffer = 'data\n'

        lines = network.LineProtocol.parse_lines(self.mock)
        self.assertEqual('data', lines.next())
        self.assertRaises(StopIteration, lines.next)
        self.assertEqual('', self.mock.recv_buffer)

    def test_parse_lines_termintor_with_carriage_return(self):
        self.mock.delimiter = re.compile(r'\r?\n')
        self.mock.recv_buffer = 'data\r\n'

        lines = network.LineProtocol.parse_lines(self.mock)
        self.assertEqual('data', lines.next())
        self.assertRaises(StopIteration, lines.next)
        self.assertEqual('', self.mock.recv_buffer)

    def test_parse_lines_no_data_before_terminator(self):
        self.mock.delimiter = re.compile(r'\n')
        self.mock.recv_buffer = '\n'

        lines = network.LineProtocol.parse_lines(self.mock)
        self.assertEqual('', lines.next())
        self.assertRaises(StopIteration, lines.next)
        self.assertEqual('', self.mock.recv_buffer)

    def test_parse_lines_extra_data_after_terminator(self):
        self.mock.delimiter = re.compile(r'\n')
        self.mock.recv_buffer = 'data1\ndata2'

        lines = network.LineProtocol.parse_lines(self.mock)
        self.assertEqual('data1', lines.next())
        self.assertRaises(StopIteration, lines.next)
        self.assertEqual('data2', self.mock.recv_buffer)

    def test_parse_lines_unicode(self):
        self.mock.delimiter = re.compile(r'\n')
        self.mock.recv_buffer = 'æøå\n'.encode('utf-8')

        lines = network.LineProtocol.parse_lines(self.mock)
        self.assertEqual('æøå'.encode('utf-8'), lines.next())
        self.assertRaises(StopIteration, lines.next)
        self.assertEqual('', self.mock.recv_buffer)

    def test_parse_lines_multiple_lines(self):
        self.mock.delimiter = re.compile(r'\n')
        self.mock.recv_buffer = 'abc\ndef\nghi\njkl'

        lines = network.LineProtocol.parse_lines(self.mock)
        self.assertEqual('abc', lines.next())
        self.assertEqual('def', lines.next())
        self.assertEqual('ghi', lines.next())
        self.assertRaises(StopIteration, lines.next)
        self.assertEqual('jkl', self.mock.recv_buffer)

    def test_parse_lines_multiple_calls(self):
        self.mock.delimiter = re.compile(r'\n')
        self.mock.recv_buffer = 'data1'

        lines = network.LineProtocol.parse_lines(self.mock)
        self.assertRaises(StopIteration, lines.next)
        self.assertEqual('data1', self.mock.recv_buffer)

        self.mock.recv_buffer += '\ndata2'

        lines = network.LineProtocol.parse_lines(self.mock)
        self.assertEqual('data1', lines.next())
        self.assertRaises(StopIteration, lines.next)
        self.assertEqual('data2', self.mock.recv_buffer)

    def test_send_lines_called_with_no_lines(self):
        self.mock.connection = Mock(spec=network.Connection)

        network.LineProtocol.send_lines(self.mock, [])
        self.assertEqual(0, self.mock.encode.call_count)
        self.assertEqual(0, self.mock.connection.queue_send.call_count)

    def test_send_lines_calls_join_lines(self):
        self.mock.connection = Mock(spec=network.Connection)
        self.mock.join_lines.return_value = 'lines'

        network.LineProtocol.send_lines(self.mock, sentinel.lines)
        self.mock.join_lines.assert_called_once_with(sentinel.lines)

    def test_send_line_encodes_joined_lines_with_final_terminator(self):
        self.mock.connection = Mock(spec=network.Connection)
        self.mock.join_lines.return_value = 'lines\n'

        network.LineProtocol.send_lines(self.mock, sentinel.lines)
        self.mock.encode.assert_called_once_with('lines\n')

    def test_send_lines_sends_encoded_string(self):
        self.mock.connection = Mock(spec=network.Connection)
        self.mock.join_lines.return_value = 'lines'
        self.mock.encode.return_value = sentinel.data

        network.LineProtocol.send_lines(self.mock, sentinel.lines)
        self.mock.connection.queue_send.assert_called_once_with(sentinel.data)

    def test_join_lines_returns_empty_string_for_no_lines(self):
        self.assertEqual('', network.LineProtocol.join_lines(self.mock, []))

    def test_join_lines_returns_joined_lines(self):
        self.assertEqual('1\n2\n', network.LineProtocol.join_lines(
            self.mock, ['1', '2']))

    def test_decode_calls_decode_on_string(self):
        string = Mock()

        network.LineProtocol.decode(self.mock, string)
        string.decode.assert_called_once_with(self.mock.encoding)

    def test_decode_plain_ascii(self):
        result = network.LineProtocol.decode(self.mock, 'abc')
        self.assertEqual('abc', result)
        self.assertEqual(unicode, type(result))

    def test_decode_utf8(self):
        result = network.LineProtocol.decode(
            self.mock, 'æøå'.encode('utf-8'))
        self.assertEqual('æøå', result)
        self.assertEqual(unicode, type(result))

    def test_decode_invalid_data(self):
        string = Mock()
        string.decode.side_effect = UnicodeError

        network.LineProtocol.decode(self.mock, string)
        self.mock.stop.assert_called_once_with()

    def test_encode_calls_encode_on_string(self):
        string = Mock()

        network.LineProtocol.encode(self.mock, string)
        string.encode.assert_called_once_with(self.mock.encoding)

    def test_encode_plain_ascii(self):
        result = network.LineProtocol.encode(self.mock, 'abc')
        self.assertEqual('abc', result)
        self.assertEqual(str, type(result))

    def test_encode_utf8(self):
        result = network.LineProtocol.encode(self.mock, 'æøå')
        self.assertEqual('æøå'.encode('utf-8'), result)
        self.assertEqual(str, type(result))

    def test_encode_invalid_data(self):
        string = Mock()
        string.encode.side_effect = UnicodeError

        network.LineProtocol.encode(self.mock, string)
        self.mock.stop.assert_called_once_with()

    def test_host_property(self):
        mock = Mock(spec=network.Connection)
        mock.host = sentinel.host

        lineprotocol = network.LineProtocol(mock)
        self.assertEqual(sentinel.host, lineprotocol.host)

    def test_port_property(self):
        mock = Mock(spec=network.Connection)
        mock.port = sentinel.port

        lineprotocol = network.LineProtocol(mock)
        self.assertEqual(sentinel.port, lineprotocol.port)

########NEW FILE########
__FILENAME__ = test_server
from __future__ import unicode_literals

import errno
import socket
import unittest

import gobject

from mock import Mock, patch, sentinel

from mopidy.utils import network

from tests import any_int


class ServerTest(unittest.TestCase):
    def setUp(self):
        self.mock = Mock(spec=network.Server)

    def test_init_calls_create_server_socket(self):
        network.Server.__init__(
            self.mock, sentinel.host, sentinel.port, sentinel.protocol)
        self.mock.create_server_socket.assert_called_once_with(
            sentinel.host, sentinel.port)

    def test_init_calls_register_server(self):
        sock = Mock(spec=socket.SocketType)
        sock.fileno.return_value = sentinel.fileno
        self.mock.create_server_socket.return_value = sock

        network.Server.__init__(
            self.mock, sentinel.host, sentinel.port, sentinel.protocol)
        self.mock.register_server_socket.assert_called_once_with(
            sentinel.fileno)

    def test_init_fails_on_fileno_call(self):
        sock = Mock(spec=socket.SocketType)
        sock.fileno.side_effect = socket.error
        self.mock.create_server_socket.return_value = sock

        self.assertRaises(
            socket.error, network.Server.__init__, self.mock, sentinel.host,
            sentinel.port, sentinel.protocol)

    def test_init_stores_values_in_attributes(self):
        # This need to be a mock and no a sentinel as fileno() is called on it
        sock = Mock(spec=socket.SocketType)
        self.mock.create_server_socket.return_value = sock

        network.Server.__init__(
            self.mock, sentinel.host, sentinel.port, sentinel.protocol,
            max_connections=sentinel.max_connections, timeout=sentinel.timeout)
        self.assertEqual(sentinel.protocol, self.mock.protocol)
        self.assertEqual(sentinel.max_connections, self.mock.max_connections)
        self.assertEqual(sentinel.timeout, self.mock.timeout)
        self.assertEqual(sock, self.mock.server_socket)

    @patch.object(network, 'create_socket', spec=socket.SocketType)
    def test_create_server_socket_sets_up_listener(self, create_socket):
        sock = create_socket.return_value

        network.Server.create_server_socket(
            self.mock, sentinel.host, sentinel.port)
        sock.setblocking.assert_called_once_with(False)
        sock.bind.assert_called_once_with((sentinel.host, sentinel.port))
        sock.listen.assert_called_once_with(any_int)

    @patch.object(network, 'create_socket', new=Mock())
    def test_create_server_socket_fails(self):
        network.create_socket.side_effect = socket.error
        self.assertRaises(
            socket.error, network.Server.create_server_socket, self.mock,
            sentinel.host, sentinel.port)

    @patch.object(network, 'create_socket', new=Mock())
    def test_create_server_bind_fails(self):
        sock = network.create_socket.return_value
        sock.bind.side_effect = socket.error

        self.assertRaises(
            socket.error, network.Server.create_server_socket, self.mock,
            sentinel.host, sentinel.port)

    @patch.object(network, 'create_socket', new=Mock())
    def test_create_server_listen_fails(self):
        sock = network.create_socket.return_value
        sock.listen.side_effect = socket.error

        self.assertRaises(
            socket.error, network.Server.create_server_socket, self.mock,
            sentinel.host, sentinel.port)

    @patch.object(gobject, 'io_add_watch', new=Mock())
    def test_register_server_socket_sets_up_io_watch(self):
        network.Server.register_server_socket(self.mock, sentinel.fileno)
        gobject.io_add_watch.assert_called_once_with(
            sentinel.fileno, gobject.IO_IN, self.mock.handle_connection)

    def test_handle_connection(self):
        self.mock.accept_connection.return_value = (
            sentinel.sock, sentinel.addr)
        self.mock.maximum_connections_exceeded.return_value = False

        self.assertTrue(network.Server.handle_connection(
            self.mock, sentinel.fileno, gobject.IO_IN))
        self.mock.accept_connection.assert_called_once_with()
        self.mock.maximum_connections_exceeded.assert_called_once_with()
        self.mock.init_connection.assert_called_once_with(
            sentinel.sock, sentinel.addr)
        self.assertEqual(0, self.mock.reject_connection.call_count)

    def test_handle_connection_exceeded_connections(self):
        self.mock.accept_connection.return_value = (
            sentinel.sock, sentinel.addr)
        self.mock.maximum_connections_exceeded.return_value = True

        self.assertTrue(network.Server.handle_connection(
            self.mock, sentinel.fileno, gobject.IO_IN))
        self.mock.accept_connection.assert_called_once_with()
        self.mock.maximum_connections_exceeded.assert_called_once_with()
        self.mock.reject_connection.assert_called_once_with(
            sentinel.sock, sentinel.addr)
        self.assertEqual(0, self.mock.init_connection.call_count)

    def test_accept_connection(self):
        sock = Mock(spec=socket.SocketType)
        sock.accept.return_value = (sentinel.sock, sentinel.addr)
        self.mock.server_socket = sock

        sock, addr = network.Server.accept_connection(self.mock)
        self.assertEqual(sentinel.sock, sock)
        self.assertEqual(sentinel.addr, addr)

    def test_accept_connection_recoverable_error(self):
        sock = Mock(spec=socket.SocketType)
        self.mock.server_socket = sock

        for error in (errno.EAGAIN, errno.EINTR):
            sock.accept.side_effect = socket.error(error, '')
            self.assertRaises(
                network.ShouldRetrySocketCall,
                network.Server.accept_connection, self.mock)

    # FIXME decide if this should be allowed to propegate
    def test_accept_connection_unrecoverable_error(self):
        sock = Mock(spec=socket.SocketType)
        self.mock.server_socket = sock
        sock.accept.side_effect = socket.error
        self.assertRaises(
            socket.error, network.Server.accept_connection, self.mock)

    def test_maximum_connections_exceeded(self):
        self.mock.max_connections = 10

        self.mock.number_of_connections.return_value = 11
        self.assertTrue(network.Server.maximum_connections_exceeded(self.mock))

        self.mock.number_of_connections.return_value = 10
        self.assertTrue(network.Server.maximum_connections_exceeded(self.mock))

        self.mock.number_of_connections.return_value = 9
        self.assertFalse(
            network.Server.maximum_connections_exceeded(self.mock))

    @patch('pykka.registry.ActorRegistry.get_by_class')
    def test_number_of_connections(self, get_by_class):
        self.mock.protocol = sentinel.protocol

        get_by_class.return_value = [1, 2, 3]
        self.assertEqual(3, network.Server.number_of_connections(self.mock))

        get_by_class.return_value = []
        self.assertEqual(0, network.Server.number_of_connections(self.mock))

    @patch.object(network, 'Connection', new=Mock())
    def test_init_connection(self):
        self.mock.protocol = sentinel.protocol
        self.mock.protocol_kwargs = {}
        self.mock.timeout = sentinel.timeout

        network.Server.init_connection(self.mock, sentinel.sock, sentinel.addr)
        network.Connection.assert_called_once_with(
            sentinel.protocol, {}, sentinel.sock, sentinel.addr,
            sentinel.timeout)

    def test_reject_connection(self):
        sock = Mock(spec=socket.SocketType)

        network.Server.reject_connection(
            self.mock, sock, (sentinel.host, sentinel.port))
        sock.close.assert_called_once_with()

    def test_reject_connection_error(self):
        sock = Mock(spec=socket.SocketType)
        sock.close.side_effect = socket.error

        network.Server.reject_connection(
            self.mock, sock, (sentinel.host, sentinel.port))
        sock.close.assert_called_once_with()

########NEW FILE########
__FILENAME__ = test_utils
from __future__ import unicode_literals

import socket
import unittest

from mock import Mock, patch

from mopidy.utils import network


class FormatHostnameTest(unittest.TestCase):
    @patch('mopidy.utils.network.has_ipv6', True)
    def test_format_hostname_prefixes_ipv4_addresses_when_ipv6_available(self):
        network.has_ipv6 = True
        self.assertEqual(network.format_hostname('0.0.0.0'), '::ffff:0.0.0.0')
        self.assertEqual(network.format_hostname('1.0.0.1'), '::ffff:1.0.0.1')

    @patch('mopidy.utils.network.has_ipv6', False)
    def test_format_hostname_does_nothing_when_only_ipv4_available(self):
        network.has_ipv6 = False
        self.assertEqual(network.format_hostname('0.0.0.0'), '0.0.0.0')


class TryIPv6SocketTest(unittest.TestCase):
    @patch('socket.has_ipv6', False)
    def test_system_that_claims_no_ipv6_support(self):
        self.assertFalse(network.try_ipv6_socket())

    @patch('socket.has_ipv6', True)
    @patch('socket.socket')
    def test_system_with_broken_ipv6(self, socket_mock):
        socket_mock.side_effect = IOError()
        self.assertFalse(network.try_ipv6_socket())

    @patch('socket.has_ipv6', True)
    @patch('socket.socket')
    def test_with_working_ipv6(self, socket_mock):
        socket_mock.return_value = Mock()
        self.assertTrue(network.try_ipv6_socket())


class CreateSocketTest(unittest.TestCase):
    @patch('mopidy.utils.network.has_ipv6', False)
    @patch('socket.socket')
    def test_ipv4_socket(self, socket_mock):
        network.create_socket()
        self.assertEqual(
            socket_mock.call_args[0], (socket.AF_INET, socket.SOCK_STREAM))

    @patch('mopidy.utils.network.has_ipv6', True)
    @patch('socket.socket')
    def test_ipv6_socket(self, socket_mock):
        network.create_socket()
        self.assertEqual(
            socket_mock.call_args[0], (socket.AF_INET6, socket.SOCK_STREAM))

    @unittest.SkipTest
    def test_ipv6_only_is_set(self):
        pass

########NEW FILE########
__FILENAME__ = test_deps
from __future__ import unicode_literals

import platform
import unittest

import mock

import pygst
pygst.require('0.10')
import gst  # noqa

import pkg_resources

from mopidy.utils import deps


class DepsTest(unittest.TestCase):
    def test_format_dependency_list(self):
        adapters = [
            lambda: dict(name='Python', version='FooPython 2.7.3'),
            lambda: dict(name='Platform', version='Loonix 4.0.1'),
            lambda: dict(
                name='Pykka', version='1.1',
                path='/foo/bar', other='Quux'),
            lambda: dict(name='Foo'),
            lambda: dict(name='Mopidy', version='0.13', dependencies=[
                dict(name='pylast', version='0.5', dependencies=[
                    dict(name='setuptools', version='0.6')
                ])
            ])
        ]

        result = deps.format_dependency_list(adapters)

        self.assertIn('Python: FooPython 2.7.3', result)

        self.assertIn('Platform: Loonix 4.0.1', result)

        self.assertIn('Pykka: 1.1 from /foo/bar', result)
        self.assertNotIn('/baz.py', result)
        self.assertIn('Detailed information: Quux', result)

        self.assertIn('Foo: not found', result)

        self.assertIn('Mopidy: 0.13', result)
        self.assertIn('  pylast: 0.5', result)
        self.assertIn('    setuptools: 0.6', result)

    def test_platform_info(self):
        result = deps.platform_info()

        self.assertEquals('Platform', result['name'])
        self.assertIn(platform.platform(), result['version'])

    def test_python_info(self):
        result = deps.python_info()

        self.assertEquals('Python', result['name'])
        self.assertIn(platform.python_implementation(), result['version'])
        self.assertIn(platform.python_version(), result['version'])
        self.assertIn('python', result['path'])
        self.assertNotIn('platform.py', result['path'])

    def test_gstreamer_info(self):
        result = deps.gstreamer_info()

        self.assertEquals('GStreamer', result['name'])
        self.assertEquals(
            '.'.join(map(str, gst.get_gst_version())), result['version'])
        self.assertIn('gst', result['path'])
        self.assertNotIn('__init__.py', result['path'])
        self.assertIn('Python wrapper: gst-python', result['other'])
        self.assertIn(
            '.'.join(map(str, gst.get_pygst_version())), result['other'])
        self.assertIn('Relevant elements:', result['other'])

    @mock.patch('pkg_resources.get_distribution')
    def test_pkg_info(self, get_distribution_mock):
        dist_mopidy = mock.Mock()
        dist_mopidy.project_name = 'Mopidy'
        dist_mopidy.version = '0.13'
        dist_mopidy.location = '/tmp/example/mopidy'
        dist_mopidy.requires.return_value = ['Pykka']

        dist_pykka = mock.Mock()
        dist_pykka.project_name = 'Pykka'
        dist_pykka.version = '1.1'
        dist_pykka.location = '/tmp/example/pykka'
        dist_pykka.requires.return_value = ['setuptools']

        dist_setuptools = mock.Mock()
        dist_setuptools.project_name = 'setuptools'
        dist_setuptools.version = '0.6'
        dist_setuptools.location = '/tmp/example/setuptools'
        dist_setuptools.requires.return_value = []

        get_distribution_mock.side_effect = [
            dist_mopidy, dist_pykka, dist_setuptools]

        result = deps.pkg_info()

        self.assertEquals('Mopidy', result['name'])
        self.assertEquals('0.13', result['version'])
        self.assertIn('mopidy', result['path'])

        dep_info_pykka = result['dependencies'][0]
        self.assertEquals('Pykka', dep_info_pykka['name'])
        self.assertEquals('1.1', dep_info_pykka['version'])

        dep_info_setuptools = dep_info_pykka['dependencies'][0]
        self.assertEquals('setuptools', dep_info_setuptools['name'])
        self.assertEquals('0.6', dep_info_setuptools['version'])

    @mock.patch('pkg_resources.get_distribution')
    def test_pkg_info_for_missing_dist(self, get_distribution_mock):
        get_distribution_mock.side_effect = pkg_resources.DistributionNotFound

        result = deps.pkg_info()

        self.assertEquals('Mopidy', result['name'])
        self.assertNotIn('version', result)
        self.assertNotIn('path', result)

    @mock.patch('pkg_resources.get_distribution')
    def test_pkg_info_for_wrong_dist_version(self, get_distribution_mock):
        get_distribution_mock.side_effect = pkg_resources.VersionConflict

        result = deps.pkg_info()

        self.assertEquals('Mopidy', result['name'])
        self.assertNotIn('version', result)
        self.assertNotIn('path', result)

########NEW FILE########
__FILENAME__ = test_encoding
from __future__ import unicode_literals

import unittest

import mock

from mopidy.utils.encoding import locale_decode


@mock.patch('mopidy.utils.encoding.locale.getpreferredencoding')
class LocaleDecodeTest(unittest.TestCase):
    def test_can_decode_utf8_strings_with_french_content(self, mock):
        mock.return_value = 'UTF-8'

        result = locale_decode(
            b'[Errno 98] Adresse d\xc3\xa9j\xc3\xa0 utilis\xc3\xa9e')

        self.assertEqual('[Errno 98] Adresse d\xe9j\xe0 utilis\xe9e', result)

    def test_can_decode_an_ioerror_with_french_content(self, mock):
        mock.return_value = 'UTF-8'

        error = IOError(98, b'Adresse d\xc3\xa9j\xc3\xa0 utilis\xc3\xa9e')
        result = locale_decode(error)
        expected = '[Errno 98] Adresse d\xe9j\xe0 utilis\xe9e'

        self.assertEqual(
            expected, result,
            '%r decoded to %r does not match expected %r' % (
                error, result, expected))

    def test_does_not_use_locale_to_decode_unicode_strings(self, mock):
        mock.return_value = 'UTF-8'

        locale_decode('abc')

        self.assertFalse(mock.called)

    def test_does_not_use_locale_to_decode_ascii_bytestrings(self, mock):
        mock.return_value = 'UTF-8'

        locale_decode('abc')

        self.assertFalse(mock.called)

########NEW FILE########
__FILENAME__ = test_jsonrpc
from __future__ import unicode_literals

import json
import unittest

import mock

import pykka

from mopidy import core, models
from mopidy.backend import dummy
from mopidy.utils import jsonrpc


class Calculator(object):
    def model(self):
        return 'TI83'

    def add(self, a, b):
        """Returns the sum of the given numbers"""
        return a + b

    def sub(self, a, b):
        return a - b

    def describe(self):
        return {
            'add': 'Returns the sum of the terms',
            'sub': 'Returns the diff of the terms',
        }

    def take_it_all(self, a, b, c=True, *args, **kwargs):
        pass

    def _secret(self):
        return 'Grand Unified Theory'

    def fail(self):
        raise ValueError('What did you expect?')


class JsonRpcTestBase(unittest.TestCase):
    def setUp(self):
        self.backend = dummy.create_dummy_backend_proxy()
        self.core = core.Core.start(backends=[self.backend]).proxy()

        self.jrw = jsonrpc.JsonRpcWrapper(
            objects={
                'hello': lambda: 'Hello, world!',
                'calc': Calculator(),
                'core': self.core,
                'core.playback': self.core.playback,
                'core.tracklist': self.core.tracklist,
                'get_uri_schemes': self.core.get_uri_schemes,
            },
            encoders=[models.ModelJSONEncoder],
            decoders=[models.model_json_decoder])

    def tearDown(self):
        pykka.ActorRegistry.stop_all()


class JsonRpcSetupTest(JsonRpcTestBase):
    def test_empty_object_mounts_is_not_allowed(self):
        test = lambda: jsonrpc.JsonRpcWrapper(objects={'': Calculator()})
        self.assertRaises(AttributeError, test)


class JsonRpcSerializationTest(JsonRpcTestBase):
    def test_handle_json_converts_from_and_to_json(self):
        self.jrw.handle_data = mock.Mock()
        self.jrw.handle_data.return_value = {'foo': 'response'}

        request = '{"foo": "request"}'
        response = self.jrw.handle_json(request)

        self.jrw.handle_data.assert_called_once_with({'foo': 'request'})
        self.assertEqual(response, '{"foo": "response"}')

    def test_handle_json_decodes_mopidy_models(self):
        self.jrw.handle_data = mock.Mock()
        self.jrw.handle_data.return_value = []

        request = '{"foo": {"__model__": "Artist", "name": "bar"}}'
        self.jrw.handle_json(request)

        self.jrw.handle_data.assert_called_once_with(
            {'foo': models.Artist(name='bar')})

    def test_handle_json_encodes_mopidy_models(self):
        self.jrw.handle_data = mock.Mock()
        self.jrw.handle_data.return_value = {'foo': models.Artist(name='bar')}

        request = '[]'
        response = json.loads(self.jrw.handle_json(request))

        self.assertIn('foo', response)
        self.assertIn('__model__', response['foo'])
        self.assertEqual(response['foo']['__model__'], 'Artist')
        self.assertIn('name', response['foo'])
        self.assertEqual(response['foo']['name'], 'bar')

    def test_handle_json_returns_nothing_for_notices(self):
        request = '{"jsonrpc": "2.0", "method": "core.get_uri_schemes"}'
        response = self.jrw.handle_json(request)

        self.assertEqual(response, None)

    def test_invalid_json_command_causes_parse_error(self):
        request = (
            '{"jsonrpc": "2.0", "method": "foobar, "params": "bar", "baz]')
        response = self.jrw.handle_json(request)
        response = json.loads(response)

        self.assertEqual(response['jsonrpc'], '2.0')
        error = response['error']
        self.assertEqual(error['code'], -32700)
        self.assertEqual(error['message'], 'Parse error')

    def test_invalid_json_batch_causes_parse_error(self):
        request = """[
            {"jsonrpc": "2.0", "method": "sum", "params": [1,2,4], "id": "1"},
            {"jsonrpc": "2.0", "method"
        ]"""
        response = self.jrw.handle_json(request)
        response = json.loads(response)

        self.assertEqual(response['jsonrpc'], '2.0')
        error = response['error']
        self.assertEqual(error['code'], -32700)
        self.assertEqual(error['message'], 'Parse error')


class JsonRpcSingleCommandTest(JsonRpcTestBase):
    def test_call_method_on_root(self):
        request = {
            'jsonrpc': '2.0',
            'method': 'hello',
            'id': 1,
        }
        response = self.jrw.handle_data(request)

        self.assertEqual(response['jsonrpc'], '2.0')
        self.assertEqual(response['id'], 1)
        self.assertNotIn('error', response)
        self.assertEqual(response['result'], 'Hello, world!')

    def test_call_method_on_plain_object(self):
        request = {
            'jsonrpc': '2.0',
            'method': 'calc.model',
            'id': 1,
        }
        response = self.jrw.handle_data(request)

        self.assertEqual(response['jsonrpc'], '2.0')
        self.assertEqual(response['id'], 1)
        self.assertNotIn('error', response)
        self.assertEqual(response['result'], 'TI83')

    def test_call_method_which_returns_dict_from_plain_object(self):
        request = {
            'jsonrpc': '2.0',
            'method': 'calc.describe',
            'id': 1,
        }
        response = self.jrw.handle_data(request)

        self.assertEqual(response['jsonrpc'], '2.0')
        self.assertEqual(response['id'], 1)
        self.assertNotIn('error', response)
        self.assertIn('add', response['result'])
        self.assertIn('sub', response['result'])

    def test_call_method_on_actor_root(self):
        request = {
            'jsonrpc': '2.0',
            'method': 'core.get_uri_schemes',
            'id': 1,
        }
        response = self.jrw.handle_data(request)

        self.assertEqual(response['jsonrpc'], '2.0')
        self.assertEqual(response['id'], 1)
        self.assertNotIn('error', response)
        self.assertEqual(response['result'], ['dummy'])

    def test_call_method_on_actor_member(self):
        request = {
            'jsonrpc': '2.0',
            'method': 'core.playback.get_volume',
            'id': 1,
        }
        response = self.jrw.handle_data(request)

        self.assertEqual(response['result'], None)

    def test_call_method_which_is_a_directly_mounted_actor_member(self):
        # 'get_uri_schemes' isn't a regular callable, but a Pykka
        # CallableProxy. This test checks that CallableProxy objects are
        # threated by JsonRpcWrapper like any other callable.

        request = {
            'jsonrpc': '2.0',
            'method': 'get_uri_schemes',
            'id': 1,
        }
        response = self.jrw.handle_data(request)

        self.assertEqual(response['jsonrpc'], '2.0')
        self.assertEqual(response['id'], 1)
        self.assertNotIn('error', response)
        self.assertEqual(response['result'], ['dummy'])

    def test_call_method_with_positional_params(self):
        request = {
            'jsonrpc': '2.0',
            'method': 'core.playback.set_volume',
            'params': [37],
            'id': 1,
        }
        response = self.jrw.handle_data(request)

        self.assertEqual(response['result'], None)
        self.assertEqual(self.core.playback.get_volume().get(), 37)

    def test_call_methods_with_named_params(self):
        request = {
            'jsonrpc': '2.0',
            'method': 'core.playback.set_volume',
            'params': {'volume': 37},
            'id': 1,
        }
        response = self.jrw.handle_data(request)

        self.assertEqual(response['result'], None)
        self.assertEqual(self.core.playback.get_volume().get(), 37)


class JsonRpcSingleNotificationTest(JsonRpcTestBase):
    def test_notification_does_not_return_a_result(self):
        request = {
            'jsonrpc': '2.0',
            'method': 'core.get_uri_schemes',
        }
        response = self.jrw.handle_data(request)

        self.assertIsNone(response)

    def test_notification_makes_an_observable_change(self):
        self.assertEqual(self.core.playback.get_volume().get(), None)

        request = {
            'jsonrpc': '2.0',
            'method': 'core.playback.set_volume',
            'params': [37],
        }
        response = self.jrw.handle_data(request)

        self.assertIsNone(response)
        self.assertEqual(self.core.playback.get_volume().get(), 37)

    def test_notification_unknown_method_returns_nothing(self):
        request = {
            'jsonrpc': '2.0',
            'method': 'bogus',
            'params': ['bogus'],
        }
        response = self.jrw.handle_data(request)

        self.assertIsNone(response)


class JsonRpcBatchTest(JsonRpcTestBase):
    def test_batch_of_only_commands_returns_all(self):
        self.core.tracklist.set_random(True).get()

        request = [
            {'jsonrpc': '2.0', 'method': 'core.tracklist.get_repeat', 'id': 1},
            {'jsonrpc': '2.0', 'method': 'core.tracklist.get_random', 'id': 2},
            {'jsonrpc': '2.0', 'method': 'core.tracklist.get_single', 'id': 3},
        ]
        response = self.jrw.handle_data(request)

        self.assertEqual(len(response), 3)

        response = dict((row['id'], row) for row in response)
        self.assertEqual(response[1]['result'], False)
        self.assertEqual(response[2]['result'], True)
        self.assertEqual(response[3]['result'], False)

    def test_batch_of_commands_and_notifications_returns_some(self):
        self.core.tracklist.set_random(True).get()

        request = [
            {'jsonrpc': '2.0', 'method': 'core.tracklist.get_repeat'},
            {'jsonrpc': '2.0', 'method': 'core.tracklist.get_random', 'id': 2},
            {'jsonrpc': '2.0', 'method': 'core.tracklist.get_single', 'id': 3},
        ]
        response = self.jrw.handle_data(request)

        self.assertEqual(len(response), 2)

        response = dict((row['id'], row) for row in response)
        self.assertNotIn(1, response)
        self.assertEqual(response[2]['result'], True)
        self.assertEqual(response[3]['result'], False)

    def test_batch_of_only_notifications_returns_nothing(self):
        self.core.tracklist.set_random(True).get()

        request = [
            {'jsonrpc': '2.0', 'method': 'core.tracklist.get_repeat'},
            {'jsonrpc': '2.0', 'method': 'core.tracklist.get_random'},
            {'jsonrpc': '2.0', 'method': 'core.tracklist.get_single'},
        ]
        response = self.jrw.handle_data(request)

        self.assertIsNone(response)


class JsonRpcSingleCommandErrorTest(JsonRpcTestBase):
    def test_application_error_response(self):
        request = {
            'jsonrpc': '2.0',
            'method': 'calc.fail',
            'params': [],
            'id': 1,
        }
        response = self.jrw.handle_data(request)

        self.assertNotIn('result', response)

        error = response['error']
        self.assertEqual(error['code'], 0)
        self.assertEqual(error['message'], 'Application error')

        data = error['data']
        self.assertEqual(data['type'], 'ValueError')
        self.assertIn('What did you expect?', data['message'])
        self.assertIn('traceback', data)
        self.assertIn('Traceback (most recent call last):', data['traceback'])

    def test_missing_jsonrpc_member_causes_invalid_request_error(self):
        request = {
            'method': 'core.get_uri_schemes',
            'id': 1,
        }
        response = self.jrw.handle_data(request)

        self.assertIsNone(response['id'])
        error = response['error']
        self.assertEqual(error['code'], -32600)
        self.assertEqual(error['message'], 'Invalid Request')
        self.assertEqual(error['data'], '"jsonrpc" member must be included')

    def test_wrong_jsonrpc_version_causes_invalid_request_error(self):
        request = {
            'jsonrpc': '3.0',
            'method': 'core.get_uri_schemes',
            'id': 1,
        }
        response = self.jrw.handle_data(request)

        self.assertIsNone(response['id'])
        error = response['error']
        self.assertEqual(error['code'], -32600)
        self.assertEqual(error['message'], 'Invalid Request')
        self.assertEqual(error['data'], '"jsonrpc" value must be "2.0"')

    def test_missing_method_member_causes_invalid_request_error(self):
        request = {
            'jsonrpc': '2.0',
            'id': 1,
        }
        response = self.jrw.handle_data(request)

        self.assertIsNone(response['id'])
        error = response['error']
        self.assertEqual(error['code'], -32600)
        self.assertEqual(error['message'], 'Invalid Request')
        self.assertEqual(error['data'], '"method" member must be included')

    def test_invalid_method_value_causes_invalid_request_error(self):
        request = {
            'jsonrpc': '2.0',
            'method': 1,
            'id': 1,
        }
        response = self.jrw.handle_data(request)

        self.assertIsNone(response['id'])
        error = response['error']
        self.assertEqual(error['code'], -32600)
        self.assertEqual(error['message'], 'Invalid Request')
        self.assertEqual(error['data'], '"method" must be a string')

    def test_invalid_params_value_causes_invalid_request_error(self):
        request = {
            'jsonrpc': '2.0',
            'method': 'core.get_uri_schemes',
            'params': 'foobar',
            'id': 1,
        }
        response = self.jrw.handle_data(request)

        self.assertIsNone(response['id'])
        error = response['error']
        self.assertEqual(error['code'], -32600)
        self.assertEqual(error['message'], 'Invalid Request')
        self.assertEqual(
            error['data'], '"params", if given, must be an array or an object')

    def test_method_on_without_object_causes_unknown_method_error(self):
        request = {
            'jsonrpc': '2.0',
            'method': 'bogus',
            'id': 1,
        }
        response = self.jrw.handle_data(request)

        error = response['error']
        self.assertEqual(error['code'], -32601)
        self.assertEqual(error['message'], 'Method not found')
        self.assertEqual(
            error['data'],
            'Could not find object mount in method name "bogus"')

    def test_method_on_unknown_object_causes_unknown_method_error(self):
        request = {
            'jsonrpc': '2.0',
            'method': 'bogus.bogus',
            'id': 1,
        }
        response = self.jrw.handle_data(request)

        error = response['error']
        self.assertEqual(error['code'], -32601)
        self.assertEqual(error['message'], 'Method not found')
        self.assertEqual(error['data'], 'No object found at "bogus"')

    def test_unknown_method_on_known_object_causes_unknown_method_error(self):
        request = {
            'jsonrpc': '2.0',
            'method': 'core.bogus',
            'id': 1,
        }
        response = self.jrw.handle_data(request)

        error = response['error']
        self.assertEqual(error['code'], -32601)
        self.assertEqual(error['message'], 'Method not found')
        self.assertEqual(
            error['data'], 'Object mounted at "core" has no member "bogus"')

    def test_private_method_causes_unknown_method_error(self):
        request = {
            'jsonrpc': '2.0',
            'method': 'core._secret',
            'id': 1,
        }
        response = self.jrw.handle_data(request)

        error = response['error']
        self.assertEqual(error['code'], -32601)
        self.assertEqual(error['message'], 'Method not found')
        self.assertEqual(error['data'], 'Private methods are not exported')

    def test_invalid_params_causes_invalid_params_error(self):
        request = {
            'jsonrpc': '2.0',
            'method': 'core.get_uri_schemes',
            'params': ['bogus'],
            'id': 1,
        }
        response = self.jrw.handle_data(request)

        error = response['error']
        self.assertEqual(error['code'], -32602)
        self.assertEqual(error['message'], 'Invalid params')

        data = error['data']
        self.assertEqual(data['type'], 'TypeError')
        self.assertEqual(
            data['message'],
            'get_uri_schemes() takes exactly 1 argument (2 given)')
        self.assertIn('traceback', data)
        self.assertIn('Traceback (most recent call last):', data['traceback'])


class JsonRpcBatchErrorTest(JsonRpcTestBase):
    def test_empty_batch_list_causes_invalid_request_error(self):
        request = []
        response = self.jrw.handle_data(request)

        self.assertIsNone(response['id'])
        error = response['error']
        self.assertEqual(error['code'], -32600)
        self.assertEqual(error['message'], 'Invalid Request')
        self.assertEqual(error['data'], 'Batch list cannot be empty')

    def test_batch_with_invalid_command_causes_invalid_request_error(self):
        request = [1]
        response = self.jrw.handle_data(request)

        self.assertEqual(len(response), 1)
        response = response[0]
        self.assertIsNone(response['id'])
        error = response['error']
        self.assertEqual(error['code'], -32600)
        self.assertEqual(error['message'], 'Invalid Request')
        self.assertEqual(error['data'], 'Request must be an object')

    def test_batch_with_invalid_commands_causes_invalid_request_error(self):
        request = [1, 2, 3]
        response = self.jrw.handle_data(request)

        self.assertEqual(len(response), 3)
        response = response[2]
        self.assertIsNone(response['id'])
        error = response['error']
        self.assertEqual(error['code'], -32600)
        self.assertEqual(error['message'], 'Invalid Request')
        self.assertEqual(error['data'], 'Request must be an object')

    def test_batch_of_both_successfull_and_failing_requests(self):
        request = [
            # Call with positional params
            {'jsonrpc': '2.0', 'method': 'core.playback.set_volume',
                'params': [47], 'id': '1'},
            # Notification
            {'jsonrpc': '2.0', 'method': 'core.tracklist.set_consume',
                'params': [True]},
            # Call with positional params
            {'jsonrpc': '2.0', 'method': 'core.tracklist.set_repeat',
                'params': [False], 'id': '2'},
            # Invalid request
            {'foo': 'boo'},
            # Unknown method
            {'jsonrpc': '2.0', 'method': 'foo.get',
                'params': {'name': 'myself'}, 'id': '5'},
            # Call without params
            {'jsonrpc': '2.0', 'method': 'core.tracklist.get_random',
                'id': '9'},
        ]
        response = self.jrw.handle_data(request)

        self.assertEqual(len(response), 5)
        response = dict((row['id'], row) for row in response)
        self.assertEqual(response['1']['result'], None)
        self.assertEqual(response['2']['result'], None)
        self.assertEqual(response[None]['error']['code'], -32600)
        self.assertEqual(response['5']['error']['code'], -32601)
        self.assertEqual(response['9']['result'], False)


class JsonRpcInspectorTest(JsonRpcTestBase):
    def test_empty_object_mounts_is_not_allowed(self):
        test = lambda: jsonrpc.JsonRpcInspector(objects={'': Calculator})
        self.assertRaises(AttributeError, test)

    def test_can_describe_method_on_root(self):
        inspector = jsonrpc.JsonRpcInspector({
            'hello': lambda: 'Hello, world!',
        })

        methods = inspector.describe()

        self.assertIn('hello', methods)
        self.assertEqual(len(methods['hello']['params']), 0)

    def test_inspector_can_describe_an_object_with_methods(self):
        inspector = jsonrpc.JsonRpcInspector({
            'calc': Calculator,
        })

        methods = inspector.describe()

        self.assertIn('calc.add', methods)
        self.assertEqual(
            methods['calc.add']['description'],
            'Returns the sum of the given numbers')

        self.assertIn('calc.sub', methods)
        self.assertIn('calc.take_it_all', methods)
        self.assertNotIn('calc._secret', methods)
        self.assertNotIn('calc.__init__', methods)

        method = methods['calc.take_it_all']
        self.assertIn('params', method)

        params = method['params']

        self.assertEqual(params[0]['name'], 'a')
        self.assertNotIn('default', params[0])

        self.assertEqual(params[1]['name'], 'b')
        self.assertNotIn('default', params[1])

        self.assertEqual(params[2]['name'], 'c')
        self.assertEqual(params[2]['default'], True)

        self.assertEqual(params[3]['name'], 'args')
        self.assertNotIn('default', params[3])
        self.assertEqual(params[3]['varargs'], True)

        self.assertEqual(params[4]['name'], 'kwargs')
        self.assertNotIn('default', params[4])
        self.assertEqual(params[4]['kwargs'], True)

    def test_inspector_can_describe_a_bunch_of_large_classes(self):
        inspector = jsonrpc.JsonRpcInspector({
            'core.get_uri_schemes': core.Core.get_uri_schemes,
            'core.library': core.LibraryController,
            'core.playback': core.PlaybackController,
            'core.playlists': core.PlaylistsController,
            'core.tracklist':  core.TracklistController,
        })

        methods = inspector.describe()

        self.assertIn('core.get_uri_schemes', methods)
        self.assertEquals(len(methods['core.get_uri_schemes']['params']), 0)

        self.assertIn('core.library.lookup', methods.keys())
        self.assertEquals(
            methods['core.library.lookup']['params'][0]['name'], 'uri')

        self.assertIn('core.playback.next', methods)
        self.assertEquals(len(methods['core.playback.next']['params']), 0)

        self.assertIn('core.playlists.get_playlists', methods)
        self.assertEquals(
            len(methods['core.playlists.get_playlists']['params']), 1)

        self.assertIn('core.tracklist.filter', methods.keys())
        self.assertEquals(
            methods['core.tracklist.filter']['params'][0]['name'], 'criteria')
        self.assertEquals(
            methods['core.tracklist.filter']['params'][1]['name'], 'kwargs')
        self.assertEquals(
            methods['core.tracklist.filter']['params'][1]['kwargs'], True)

########NEW FILE########
__FILENAME__ = test_path
# encoding: utf-8

from __future__ import unicode_literals

import os
import shutil
import tempfile
import unittest

import glib

from mopidy.utils import path

from tests import any_int, path_to_data_dir


class GetOrCreateDirTest(unittest.TestCase):
    def setUp(self):
        self.parent = tempfile.mkdtemp()

    def tearDown(self):
        if os.path.isdir(self.parent):
            shutil.rmtree(self.parent)

    def test_creating_dir(self):
        dir_path = os.path.join(self.parent, b'test')
        self.assert_(not os.path.exists(dir_path))
        created = path.get_or_create_dir(dir_path)
        self.assert_(os.path.exists(dir_path))
        self.assert_(os.path.isdir(dir_path))
        self.assertEqual(created, dir_path)

    def test_creating_nested_dirs(self):
        level2_dir = os.path.join(self.parent, b'test')
        level3_dir = os.path.join(self.parent, b'test', b'test')
        self.assert_(not os.path.exists(level2_dir))
        self.assert_(not os.path.exists(level3_dir))
        created = path.get_or_create_dir(level3_dir)
        self.assert_(os.path.exists(level2_dir))
        self.assert_(os.path.isdir(level2_dir))
        self.assert_(os.path.exists(level3_dir))
        self.assert_(os.path.isdir(level3_dir))
        self.assertEqual(created, level3_dir)

    def test_creating_existing_dir(self):
        created = path.get_or_create_dir(self.parent)
        self.assert_(os.path.exists(self.parent))
        self.assert_(os.path.isdir(self.parent))
        self.assertEqual(created, self.parent)

    def test_create_dir_with_name_of_existing_file_throws_oserror(self):
        conflicting_file = os.path.join(self.parent, b'test')
        open(conflicting_file, 'w').close()
        dir_path = os.path.join(self.parent, b'test')
        self.assertRaises(OSError, path.get_or_create_dir, dir_path)

    def test_create_dir_with_unicode(self):
        with self.assertRaises(ValueError):
            dir_path = unicode(os.path.join(self.parent, b'test'))
            path.get_or_create_dir(dir_path)

    def test_create_dir_with_none(self):
        with self.assertRaises(ValueError):
            path.get_or_create_dir(None)


class GetOrCreateFileTest(unittest.TestCase):
    def setUp(self):
        self.parent = tempfile.mkdtemp()

    def tearDown(self):
        if os.path.isdir(self.parent):
            shutil.rmtree(self.parent)

    def test_creating_file(self):
        file_path = os.path.join(self.parent, b'test')
        self.assert_(not os.path.exists(file_path))
        created = path.get_or_create_file(file_path)
        self.assert_(os.path.exists(file_path))
        self.assert_(os.path.isfile(file_path))
        self.assertEqual(created, file_path)

    def test_creating_nested_file(self):
        level2_dir = os.path.join(self.parent, b'test')
        file_path = os.path.join(self.parent, b'test', b'test')
        self.assert_(not os.path.exists(level2_dir))
        self.assert_(not os.path.exists(file_path))
        created = path.get_or_create_file(file_path)
        self.assert_(os.path.exists(level2_dir))
        self.assert_(os.path.isdir(level2_dir))
        self.assert_(os.path.exists(file_path))
        self.assert_(os.path.isfile(file_path))
        self.assertEqual(created, file_path)

    def test_creating_existing_file(self):
        file_path = os.path.join(self.parent, b'test')
        path.get_or_create_file(file_path)
        created = path.get_or_create_file(file_path)
        self.assert_(os.path.exists(file_path))
        self.assert_(os.path.isfile(file_path))
        self.assertEqual(created, file_path)

    def test_create_file_with_name_of_existing_dir_throws_ioerror(self):
        conflicting_dir = os.path.join(self.parent)
        with self.assertRaises(IOError):
            path.get_or_create_file(conflicting_dir)

    def test_create_dir_with_unicode(self):
        with self.assertRaises(ValueError):
            file_path = unicode(os.path.join(self.parent, b'test'))
            path.get_or_create_file(file_path)

    def test_create_file_with_none(self):
        with self.assertRaises(ValueError):
            path.get_or_create_file(None)

    def test_create_dir_without_mkdir(self):
        file_path = os.path.join(self.parent, b'foo', b'bar')
        with self.assertRaises(IOError):
            path.get_or_create_file(file_path, mkdir=False)

    def test_create_dir_with_default_content(self):
        file_path = os.path.join(self.parent, b'test')
        created = path.get_or_create_file(file_path, content=b'foobar')
        with open(created) as fh:
            self.assertEqual(fh.read(), b'foobar')


class PathToFileURITest(unittest.TestCase):
    def test_simple_path(self):
        result = path.path_to_uri('/etc/fstab')
        self.assertEqual(result, 'file:///etc/fstab')

    def test_space_in_path(self):
        result = path.path_to_uri('/tmp/test this')
        self.assertEqual(result, 'file:///tmp/test%20this')

    def test_unicode_in_path(self):
        result = path.path_to_uri('/tmp/æøå')
        self.assertEqual(result, 'file:///tmp/%C3%A6%C3%B8%C3%A5')

    def test_utf8_in_path(self):
        result = path.path_to_uri('/tmp/æøå'.encode('utf-8'))
        self.assertEqual(result, 'file:///tmp/%C3%A6%C3%B8%C3%A5')

    def test_latin1_in_path(self):
        result = path.path_to_uri('/tmp/æøå'.encode('latin-1'))
        self.assertEqual(result, 'file:///tmp/%E6%F8%E5')


class UriToPathTest(unittest.TestCase):
    def test_simple_uri(self):
        result = path.uri_to_path('file:///etc/fstab')
        self.assertEqual(result, '/etc/fstab'.encode('utf-8'))

    def test_space_in_uri(self):
        result = path.uri_to_path('file:///tmp/test%20this')
        self.assertEqual(result, '/tmp/test this'.encode('utf-8'))

    def test_unicode_in_uri(self):
        result = path.uri_to_path('file:///tmp/%C3%A6%C3%B8%C3%A5')
        self.assertEqual(result, '/tmp/æøå'.encode('utf-8'))

    def test_latin1_in_uri(self):
        result = path.uri_to_path('file:///tmp/%E6%F8%E5')
        self.assertEqual(result, '/tmp/æøå'.encode('latin-1'))


class SplitPathTest(unittest.TestCase):
    def test_empty_path(self):
        self.assertEqual([], path.split_path(''))

    def test_single_dir(self):
        self.assertEqual(['foo'], path.split_path('foo'))

    def test_dirs(self):
        self.assertEqual(['foo', 'bar', 'baz'], path.split_path('foo/bar/baz'))

    def test_initial_slash_is_ignored(self):
        self.assertEqual(
            ['foo', 'bar', 'baz'], path.split_path('/foo/bar/baz'))

    def test_only_slash(self):
        self.assertEqual([], path.split_path('/'))


class ExpandPathTest(unittest.TestCase):
    # TODO: test via mocks?

    def test_empty_path(self):
        self.assertEqual(os.path.abspath(b'.'), path.expand_path(b''))

    def test_absolute_path(self):
        self.assertEqual(b'/tmp/foo', path.expand_path(b'/tmp/foo'))

    def test_home_dir_expansion(self):
        self.assertEqual(
            os.path.expanduser(b'~/foo'), path.expand_path(b'~/foo'))

    def test_abspath(self):
        self.assertEqual(os.path.abspath(b'./foo'), path.expand_path(b'./foo'))

    def test_xdg_subsititution(self):
        self.assertEqual(
            glib.get_user_data_dir() + b'/foo',
            path.expand_path(b'$XDG_DATA_DIR/foo'))

    def test_xdg_subsititution_unknown(self):
        self.assertIsNone(
            path.expand_path(b'/tmp/$XDG_INVALID_DIR/foo'))


class FindMTimesTest(unittest.TestCase):
    maxDiff = None

    def find(self, value):
        return path.find_mtimes(path_to_data_dir(value))

    def test_basic_dir(self):
        self.assert_(self.find(''))

    def test_nonexistant_dir(self):
        self.assertEqual(self.find('does-not-exist'), {})

    def test_file(self):
        self.assertEqual({path_to_data_dir('blank.mp3'): any_int},
                         self.find('blank.mp3'))

    def test_files(self):
        mtimes = self.find('find')
        expected_files = [
            b'find/foo/bar/file', b'find/foo/file', b'find/baz/file']
        expected = {path_to_data_dir(p): any_int for p in expected_files}
        self.assertEqual(expected, mtimes)

    def test_names_are_bytestrings(self):
        is_bytes = lambda f: isinstance(f, bytes)
        for name in self.find(''):
            self.assert_(
                is_bytes(name), '%s is not bytes object' % repr(name))


# TODO: kill this in favour of just os.path.getmtime + mocks
class MtimeTest(unittest.TestCase):
    def tearDown(self):
        path.mtime.undo_fake()

    def test_mtime_of_current_dir(self):
        mtime_dir = int(os.stat('.').st_mtime)
        self.assertEqual(mtime_dir, path.mtime('.'))

    def test_fake_time_is_returned(self):
        path.mtime.set_fake_time(123456)
        self.assertEqual(path.mtime('.'), 123456)

########NEW FILE########
__FILENAME__ = __main__
from __future__ import unicode_literals

import nose

nose.main()

########NEW FILE########
