__FILENAME__ = actor
from __future__ import unicode_literals

import pygst
pygst.require('0.10')
import gst
import gobject

import logging

import pykka

from mopidy.utils import process

from . import mixers, playlists, utils
from .constants import PlaybackState
from .listener import AudioListener

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

        self._connect(playbin, 'about-to-finish', self._on_about_to_finish)
        self._connect(playbin, 'notify::source', self._on_new_source)

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
__FILENAME__ = actor
from __future__ import unicode_literals

import logging
import json
import os

import cherrypy
import pykka
from ws4py.messaging import TextMessage
from ws4py.server.cherrypyserver import WebSocketPlugin, WebSocketTool

from mopidy import models, zeroconf
from mopidy.core import CoreListener
from . import ws

from configobj import ConfigObj, ConfigObjError
from validate import Validator
import jinja2

logger = logging.getLogger(__name__)

config_file = '/boot/config/settings.ini'
spec_file = '/opt/musicbox/settingsspec.ini'
template_file = '/opt/webclient/settings/index.html'
log_file = '/var/log/mopidy/mopidy.log'
password_mask = '******'

class HttpFrontend(pykka.ThreadingActor, CoreListener):
    def __init__(self, config, core):
        super(HttpFrontend, self).__init__()
        self.config = config
        self.core = core

        self.hostname = config['http']['hostname']
        self.port = config['http']['port']
        self.zeroconf_name = config['http']['zeroconf']
        self.zeroconf_service = None

        self._setup_server()
        self._setup_websocket_plugin()
        app = self._create_app()
        self._setup_logging(app)

    def _setup_server(self):
        cherrypy.config.update({
            'engine.autoreload_on': False,
            'server.socket_host': self.hostname,
            'server.socket_port': self.port,
        })

    def _setup_websocket_plugin(self):
        WebSocketPlugin(cherrypy.engine).subscribe()
        cherrypy.tools.websocket = WebSocketTool()

    def _create_app(self):
        root = RootResource()
        root.mopidy = MopidyResource()
        root.mopidy.ws = ws.WebSocketResource(self.core)

        if self.config['http']['static_dir']:
            static_dir = self.config['http']['static_dir']
        else:
            static_dir = os.path.join(os.path.dirname(__file__), 'data')
        logger.debug('HTTP server will serve "%s" at /', static_dir)

        mopidy_dir = os.path.join(os.path.dirname(__file__), 'data')
        favicon = os.path.join(mopidy_dir, 'favicon.png')

        config = {
            b'/': {
                'tools.staticdir.on': True,
                'tools.staticdir.index': 'index.html',
                'tools.staticdir.dir': static_dir,
            },
            b'/favicon.ico': {
                'tools.staticfile.on': True,
                'tools.staticfile.filename': favicon,
            },
            b'/mopidy': {
                'tools.staticdir.on': True,
                'tools.staticdir.index': 'mopidy.html',
                'tools.staticdir.dir': mopidy_dir,
            },
            b'/mopidy/ws': {
                'tools.websocket.on': True,
                'tools.websocket.handler_cls': ws.WebSocketHandler,
            },
        }

        return cherrypy.tree.mount(root, '/', config)

    def _setup_logging(self, app):
        cherrypy.log.access_log.setLevel(logging.NOTSET)
        cherrypy.log.error_log.setLevel(logging.NOTSET)
        cherrypy.log.screen = False

        app.log.access_log.setLevel(logging.NOTSET)
        app.log.error_log.setLevel(logging.NOTSET)

    def on_start(self):
        logger.debug('Starting HTTP server')
        cherrypy.engine.start()
        logger.info('HTTP server running at %s', cherrypy.server.base())

        if self.zeroconf_name:
            self.zeroconf_service = zeroconf.Zeroconf(
                stype='_http._tcp', name=self.zeroconf_name,
                host=self.hostname, port=self.port)

            if self.zeroconf_service.publish():
                logger.debug(
                    'Registered HTTP with Zeroconf as "%s"',
                    self.zeroconf_service.name)
            else:
                logger.debug('Registering HTTP with Zeroconf failed.')

    def on_stop(self):
        if self.zeroconf_service:
            self.zeroconf_service.unpublish()

        logger.debug('Stopping HTTP server')
        cherrypy.engine.exit()
        logger.info('Stopped HTTP server')

    def on_event(self, name, **data):
        event = data
        event['event'] = name
        message = json.dumps(event, cls=models.ModelJSONEncoder)
        cherrypy.engine.publish('websocket-broadcast', TextMessage(message))


class RootResource(object):
    @cherrypy.expose
    @cherrypy.tools.allow(methods=['POST'])
    def updateSettings(self, **params):
        error = ''
        try:
            config = ConfigObj(config_file, configspec=spec_file, file_error=True)
        except (ConfigObjError, IOError), e:
            error = 'Could not load ini file!'
#        print (params)
        validItems = ConfigObj(spec_file)
        templateVars = { 
            "error": error
        }
        #iterate over the items, so that only valid items are processed
        for item in validItems:
            for subitem in validItems[item]:
                itemName = item + '__' + subitem
#                print itemName
                if itemName in params.keys():
                    #don't edit config value if password mask
                    if subitem[-8:] == 'password':
                      if params[itemName] == password_mask:
                          continue
                    config[item][subitem] = params[itemName]
#                    print params[itemName]
        config.write()
        logger.info('Rebooting system')
        os.system("shutdown -r now")
#        os.system("/opt/musicbox/startup.sh")
        return "<html><body><h1>Settings Saved!</h1><script>toast('Applying changes (might need a rebbot)...', 10000);setTimeout(function(){window.location('/');}, 10000);</script><a href='/'>Back</a></body></html>"

    @cherrypy.expose
    def Settings(self, **params):
        templateLoader = jinja2.FileSystemLoader( searchpath = "/" )
        templateEnv = jinja2.Environment( loader=templateLoader )
        template = templateEnv.get_template(template_file)
        error = ''
        #read config file
        try:
            config = ConfigObj(config_file, configspec=spec_file, file_error=True)
        except (ConfigObjError, IOError), e:
            error = 'Could not load ini file!'
#        print (error)
        #read values of valid items (in the spec-file)
        validItems = ConfigObj(spec_file)
        templateVars = { 
            "error": error
        }
        #iterate over the valid items to get them into the template
        for item in validItems:
#            print(item)
            for subitem in validItems[item]:
#                print('['+subitem)
                itemName = item + '__' + subitem
                try:
                    configValue = config[item][subitem]
                    #compare last 8 caracters of subitemname
                    if subitem[-8:] == 'password':
                        configValue = password_mask
                    templateVars[itemName] = configValue
                except:
                    pass
#        print templateVars
        return template.render ( templateVars )

    @cherrypy.expose
    @cherrypy.tools.allow(methods=['POST'])
    def haltSystem(self, **params):
        logger.info('Halting system')
        os.system("shutdown -h now")

    @cherrypy.expose
    @cherrypy.tools.allow(methods=['POST'])
    def rebootSystem(self, **params):
        logger.info('Rebooting system')
        os.system("shutdown -r now")

    @cherrypy.expose
    def log(self, **params):
        page = '<html><body><h2>MusicBox/Mopidy Log (can take a while to load...)</h2><pre>'
        with open(log_file, 'r') as f:
            page += f.read()
            page += '</pre></body></html>'
        return page

class MopidyResource(object):
    pass

########NEW FILE########
__FILENAME__ = musicboxwebserver
#!/usr/bin/python
# Webserver for musicbox functions
# (c) Wouter van Wijk 2014
# GPL 3 License

import cherrypy
from configobj import ConfigObj, ConfigObjError
from validate import Validator
import os
import jinja2

config_file = '/boot/config/settings.ini'
spec_file = '/opt/musicbox/settingsspec.ini'
template_file = '/opt/webclient/settings/index.html'
log_file = '/var/log/mopidy/mopidy.log'

class runServer(object):
    #setup static files
    _cp_config = {'tools.staticdir.on' : True,
            'tools.staticdir.dir' : '/opt/defaultwebclient',
            'tools.staticdir.index' : 'index.html',
    }

    @cherrypy.expose
    @cherrypy.tools.allow(methods=['POST'])
    def updateSettings(self, **params):
        error = ''
        try:
            config = ConfigObj(config_file, configspec=spec_file, file_error=True)
        except (ConfigObjError, IOError), e:
            error = 'Could not load ini file!'
        print (params)
        validItems = ConfigObj(spec_file)
        templateVars = { 
            "error": error
        }
        #iterate over the items, so that only valid items are processed
        for item in validItems:
            for subitem in validItems[item]:
                itemName = item + '__' + subitem
                print itemName
                if itemName in params.keys():
                    config[item][subitem] = params[itemName]
                    print params[itemName]
        config.write()
        #os.system("shutdown -r now")
        return '<html><body><h1>Settings Saved!</h1>Rebooting MusicBox...<br/><a href="/">Back</a></body></html>'
        
    updateSettings._cp_config = {'tools.staticdir.on': False}

    @cherrypy.expose
    def settings(self, **params):
        templateLoader = jinja2.FileSystemLoader( searchpath = "/" )
        templateEnv = jinja2.Environment( loader=templateLoader )
        template = templateEnv.get_template(template_file)
        error = ''
        #read config file
        try:
            config = ConfigObj(config_file, configspec=spec_file, file_error=True)
        except (ConfigObjError, IOError), e:
            error = 'Could not load ini file!'
        print (error)
        #read values of valid items (in the spec-file)
        validItems = ConfigObj(spec_file)
        templateVars = { 
            "error": error
        }
        #iterate over the valid items to get them into the template
        for item in validItems:
            print(item)
            for subitem in validItems[item]:
                print('-'+subitem)
                itemName = item + '__' + subitem
                try:
                    templateVars[itemName] = config[item][subitem]
                    print templateVars[itemName]
                except:
                    pass
        print templateVars
        return template.render ( templateVars )
    settings._cp_config = {'tools.staticdir.on': False}

    @cherrypy.expose
    @cherrypy.tools.allow(methods=['POST'])
    def haltSystem(self, **params):
        os.system("shutdown -h now")
    haltSystem._cp_config = {'tools.staticdir.on': False}

    @cherrypy.expose
    @cherrypy.tools.allow(methods=['POST'])
    def rebootSystem(self, **params):
        os.system("shutdown -r now")
    rebootSystem._cp_config = {'tools.staticdir.on': False}

    @cherrypy.expose
    def log(self, **params):
        page = '<html><body><h2>MusicBox/Mopidy Log (can take a while to load...)</h2>'
        with open(log_file, 'r') as f:
            page += '<pre>%s</pre>' % f.read()
            page += '</body></html>'
        return page
    log._cp_config = {'tools.staticdir.on': False}

cherrypy.config.update({'server.socket_host': '0.0.0.0', 'server.socket_port': 8080 })
cherrypy.quickstart(runServer())

########NEW FILE########
__FILENAME__ = webserver
# Webserver for musicbox functions
# (c) Wouter van Wijk 2014
# GPL 3 License

import cherrypy
import os

config_file = '/boot/config/settings.ini'
template_file = '/opt/webclient/settings/index.html'
log_file = '/var/log/mopidy/mopidy.log'


class runServer(object):
    _cp_config = {'tools.staticdir.on' : True,
            'tools.staticdir.dir' : '/opt/defaultwebclient',
            'tools.staticdir.index' : 'index.html',
    }

    @cherrypy.expose
    @cherrypy.tools.allow(methods=['POST'])
    def updateSettings(self, **params):
        #set the username & password
        for key, value in params.iteritems():
            sysstring = "sed -i -e \"/^\[MusicBox\]/,/^\[.*\]/ s|^\(%s[ \t]*=[ \t]*\).*$|\1'%s'\r|\" /boot/config/settings.ini" % (key, value)
            subprocess.Popen(sysstring, shell=True)
        subprocess.Popen("/opt/restartmopidy.sh", shell=True)
    updateSettings._cp_config = {'tools.staticdir.on': False}

    @cherrypy.expose
    def settings(self, **params):
        templatefile = open(template_file, 'r')
        for line in templatefile:
            for src, target in replacements.iteritems():
                line = line.replace(src, target)
                page += line
        return page
    settings._cp_config = {'tools.staticdir.on': False}

    @cherrypy.expose
    @cherrypy.tools.allow(methods=['POST'])
    def haltSystem(self, **params):
        os.system("shutdown -h now")
    haltSystem._cp_config = {'tools.staticdir.on': False}

    @cherrypy.expose
    @cherrypy.tools.allow(methods=['POST'])
    def rebootSystem(self, **params):
        os.system("shutdown -r now")
    rebootSystem._cp_config = {'tools.staticdir.on': False}

    @cherrypy.expose
    def log(self, **params):
        page = '<html><body><h2>MusicBox/Mopidy Log (can take a while to load...)</h2>'
        with open(log_file, 'r') as f:
            page += '<pre>%s</pre>' % f.read()
            page += '</body></html>'
        return page
    log._cp_config = {'tools.staticdir.on': False}

cherrypy.config.update({'server.socket_host': '0.0.0.0', 'server.socket_port': 80 })
cherrypy.quickstart(runServer())

########NEW FILE########
__FILENAME__ = BeautifulSoup
"""Beautiful Soup
Elixir and Tonic
"The Screen-Scraper's Friend"
http://www.crummy.com/software/BeautifulSoup/

Beautiful Soup parses a (possibly invalid) XML or HTML document into a
tree representation. It provides methods and Pythonic idioms that make
it easy to navigate, search, and modify the tree.

A well-formed XML/HTML document yields a well-formed data
structure. An ill-formed XML/HTML document yields a correspondingly
ill-formed data structure. If your document is only locally
well-formed, you can use this library to find and process the
well-formed part of it.

Beautiful Soup works with Python 2.2 and up. It has no external
dependencies, but you'll have more success at converting data to UTF-8
if you also install these three packages:

* chardet, for auto-detecting character encodings
  http://chardet.feedparser.org/
* cjkcodecs and iconv_codec, which add more encodings to the ones supported
  by stock Python.
  http://cjkpython.i18n.org/

Beautiful Soup defines classes for two main parsing strategies:

 * BeautifulStoneSoup, for parsing XML, SGML, or your domain-specific
   language that kind of looks like XML.

 * BeautifulSoup, for parsing run-of-the-mill HTML code, be it valid
   or invalid. This class has web browser-like heuristics for
   obtaining a sensible parse tree in the face of common HTML errors.

Beautiful Soup also defines a class (UnicodeDammit) for autodetecting
the encoding of an HTML or XML document, and converting it to
Unicode. Much of this code is taken from Mark Pilgrim's Universal Feed Parser.

For more than you ever wanted to know about Beautiful Soup, see the
documentation:
http://www.crummy.com/software/BeautifulSoup/documentation.html

Here, have some legalese:

Copyright (c) 2004-2010, Leonard Richardson

All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are
met:

  * Redistributions of source code must retain the above copyright
    notice, this list of conditions and the following disclaimer.

  * Redistributions in binary form must reproduce the above
    copyright notice, this list of conditions and the following
    disclaimer in the documentation and/or other materials provided
    with the distribution.

  * Neither the name of the the Beautiful Soup Consortium and All
    Night Kosher Bakery nor the names of its contributors may be
    used to endorse or promote products derived from this software
    without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
"AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR
CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE, DAMMIT.

"""
from __future__ import generators

__author__ = "Leonard Richardson (leonardr@segfault.org)"
__version__ = "3.2.1"
__copyright__ = "Copyright (c) 2004-2012 Leonard Richardson"
__license__ = "New-style BSD"

from sgmllib import SGMLParser, SGMLParseError
import codecs
import markupbase
import types
import re
import sgmllib
try:
  from htmlentitydefs import name2codepoint
except ImportError:
  name2codepoint = {}
try:
    set
except NameError:
    from sets import Set as set

#These hacks make Beautiful Soup able to parse XML with namespaces
sgmllib.tagfind = re.compile('[a-zA-Z][-_.:a-zA-Z0-9]*')
markupbase._declname_match = re.compile(r'[a-zA-Z][-_.:a-zA-Z0-9]*\s*').match

DEFAULT_OUTPUT_ENCODING = "utf-8"

def _match_css_class(str):
    """Build a RE to match the given CSS class."""
    return re.compile(r"(^|.*\s)%s($|\s)" % str)

# First, the classes that represent markup elements.

class PageElement(object):
    """Contains the navigational information for some part of the page
    (either a tag or a piece of text)"""

    def _invert(h):
        "Cheap function to invert a hash."
        i = {}
        for k,v in h.items():
            i[v] = k
        return i

    XML_ENTITIES_TO_SPECIAL_CHARS = { "apos" : "'",
                                      "quot" : '"',
                                      "amp" : "&",
                                      "lt" : "<",
                                      "gt" : ">" }

    XML_SPECIAL_CHARS_TO_ENTITIES = _invert(XML_ENTITIES_TO_SPECIAL_CHARS)

    def setup(self, parent=None, previous=None):
        """Sets up the initial relations between this element and
        other elements."""
        self.parent = parent
        self.previous = previous
        self.next = None
        self.previousSibling = None
        self.nextSibling = None
        if self.parent and self.parent.contents:
            self.previousSibling = self.parent.contents[-1]
            self.previousSibling.nextSibling = self

    def replaceWith(self, replaceWith):
        oldParent = self.parent
        myIndex = self.parent.index(self)
        if hasattr(replaceWith, "parent")\
                  and replaceWith.parent is self.parent:
            # We're replacing this element with one of its siblings.
            index = replaceWith.parent.index(replaceWith)
            if index and index < myIndex:
                # Furthermore, it comes before this element. That
                # means that when we extract it, the index of this
                # element will change.
                myIndex = myIndex - 1
        self.extract()
        oldParent.insert(myIndex, replaceWith)

    def replaceWithChildren(self):
        myParent = self.parent
        myIndex = self.parent.index(self)
        self.extract()
        reversedChildren = list(self.contents)
        reversedChildren.reverse()
        for child in reversedChildren:
            myParent.insert(myIndex, child)

    def extract(self):
        """Destructively rips this element out of the tree."""
        if self.parent:
            try:
                del self.parent.contents[self.parent.index(self)]
            except ValueError:
                pass

        #Find the two elements that would be next to each other if
        #this element (and any children) hadn't been parsed. Connect
        #the two.
        lastChild = self._lastRecursiveChild()
        nextElement = lastChild.next

        if self.previous:
            self.previous.next = nextElement
        if nextElement:
            nextElement.previous = self.previous
        self.previous = None
        lastChild.next = None

        self.parent = None
        if self.previousSibling:
            self.previousSibling.nextSibling = self.nextSibling
        if self.nextSibling:
            self.nextSibling.previousSibling = self.previousSibling
        self.previousSibling = self.nextSibling = None
        return self

    def _lastRecursiveChild(self):
        "Finds the last element beneath this object to be parsed."
        lastChild = self
        while hasattr(lastChild, 'contents') and lastChild.contents:
            lastChild = lastChild.contents[-1]
        return lastChild

    def insert(self, position, newChild):
        if isinstance(newChild, basestring) \
            and not isinstance(newChild, NavigableString):
            newChild = NavigableString(newChild)

        position =  min(position, len(self.contents))
        if hasattr(newChild, 'parent') and newChild.parent is not None:
            # We're 'inserting' an element that's already one
            # of this object's children.
            if newChild.parent is self:
                index = self.index(newChild)
                if index > position:
                    # Furthermore we're moving it further down the
                    # list of this object's children. That means that
                    # when we extract this element, our target index
                    # will jump down one.
                    position = position - 1
            newChild.extract()

        newChild.parent = self
        previousChild = None
        if position == 0:
            newChild.previousSibling = None
            newChild.previous = self
        else:
            previousChild = self.contents[position-1]
            newChild.previousSibling = previousChild
            newChild.previousSibling.nextSibling = newChild
            newChild.previous = previousChild._lastRecursiveChild()
        if newChild.previous:
            newChild.previous.next = newChild

        newChildsLastElement = newChild._lastRecursiveChild()

        if position >= len(self.contents):
            newChild.nextSibling = None

            parent = self
            parentsNextSibling = None
            while not parentsNextSibling:
                parentsNextSibling = parent.nextSibling
                parent = parent.parent
                if not parent: # This is the last element in the document.
                    break
            if parentsNextSibling:
                newChildsLastElement.next = parentsNextSibling
            else:
                newChildsLastElement.next = None
        else:
            nextChild = self.contents[position]
            newChild.nextSibling = nextChild
            if newChild.nextSibling:
                newChild.nextSibling.previousSibling = newChild
            newChildsLastElement.next = nextChild

        if newChildsLastElement.next:
            newChildsLastElement.next.previous = newChildsLastElement
        self.contents.insert(position, newChild)

    def append(self, tag):
        """Appends the given tag to the contents of this tag."""
        self.insert(len(self.contents), tag)

    def findNext(self, name=None, attrs={}, text=None, **kwargs):
        """Returns the first item that matches the given criteria and
        appears after this Tag in the document."""
        return self._findOne(self.findAllNext, name, attrs, text, **kwargs)

    def findAllNext(self, name=None, attrs={}, text=None, limit=None,
                    **kwargs):
        """Returns all items that match the given criteria and appear
        after this Tag in the document."""
        return self._findAll(name, attrs, text, limit, self.nextGenerator,
                             **kwargs)

    def findNextSibling(self, name=None, attrs={}, text=None, **kwargs):
        """Returns the closest sibling to this Tag that matches the
        given criteria and appears after this Tag in the document."""
        return self._findOne(self.findNextSiblings, name, attrs, text,
                             **kwargs)

    def findNextSiblings(self, name=None, attrs={}, text=None, limit=None,
                         **kwargs):
        """Returns the siblings of this Tag that match the given
        criteria and appear after this Tag in the document."""
        return self._findAll(name, attrs, text, limit,
                             self.nextSiblingGenerator, **kwargs)
    fetchNextSiblings = findNextSiblings # Compatibility with pre-3.x

    def findPrevious(self, name=None, attrs={}, text=None, **kwargs):
        """Returns the first item that matches the given criteria and
        appears before this Tag in the document."""
        return self._findOne(self.findAllPrevious, name, attrs, text, **kwargs)

    def findAllPrevious(self, name=None, attrs={}, text=None, limit=None,
                        **kwargs):
        """Returns all items that match the given criteria and appear
        before this Tag in the document."""
        return self._findAll(name, attrs, text, limit, self.previousGenerator,
                           **kwargs)
    fetchPrevious = findAllPrevious # Compatibility with pre-3.x

    def findPreviousSibling(self, name=None, attrs={}, text=None, **kwargs):
        """Returns the closest sibling to this Tag that matches the
        given criteria and appears before this Tag in the document."""
        return self._findOne(self.findPreviousSiblings, name, attrs, text,
                             **kwargs)

    def findPreviousSiblings(self, name=None, attrs={}, text=None,
                             limit=None, **kwargs):
        """Returns the siblings of this Tag that match the given
        criteria and appear before this Tag in the document."""
        return self._findAll(name, attrs, text, limit,
                             self.previousSiblingGenerator, **kwargs)
    fetchPreviousSiblings = findPreviousSiblings # Compatibility with pre-3.x

    def findParent(self, name=None, attrs={}, **kwargs):
        """Returns the closest parent of this Tag that matches the given
        criteria."""
        # NOTE: We can't use _findOne because findParents takes a different
        # set of arguments.
        r = None
        l = self.findParents(name, attrs, 1)
        if l:
            r = l[0]
        return r

    def findParents(self, name=None, attrs={}, limit=None, **kwargs):
        """Returns the parents of this Tag that match the given
        criteria."""

        return self._findAll(name, attrs, None, limit, self.parentGenerator,
                             **kwargs)
    fetchParents = findParents # Compatibility with pre-3.x

    #These methods do the real heavy lifting.

    def _findOne(self, method, name, attrs, text, **kwargs):
        r = None
        l = method(name, attrs, text, 1, **kwargs)
        if l:
            r = l[0]
        return r

    def _findAll(self, name, attrs, text, limit, generator, **kwargs):
        "Iterates over a generator looking for things that match."

        if isinstance(name, SoupStrainer):
            strainer = name
        # (Possibly) special case some findAll*(...) searches
        elif text is None and not limit and not attrs and not kwargs:
            # findAll*(True)
            if name is True:
                return [element for element in generator()
                        if isinstance(element, Tag)]
            # findAll*('tag-name')
            elif isinstance(name, basestring):
                return [element for element in generator()
                        if isinstance(element, Tag) and
                        element.name == name]
            else:
                strainer = SoupStrainer(name, attrs, text, **kwargs)
        # Build a SoupStrainer
        else:
            strainer = SoupStrainer(name, attrs, text, **kwargs)
        results = ResultSet(strainer)
        g = generator()
        while True:
            try:
                i = g.next()
            except StopIteration:
                break
            if i:
                found = strainer.search(i)
                if found:
                    results.append(found)
                    if limit and len(results) >= limit:
                        break
        return results

    #These Generators can be used to navigate starting from both
    #NavigableStrings and Tags.
    def nextGenerator(self):
        i = self
        while i is not None:
            i = i.next
            yield i

    def nextSiblingGenerator(self):
        i = self
        while i is not None:
            i = i.nextSibling
            yield i

    def previousGenerator(self):
        i = self
        while i is not None:
            i = i.previous
            yield i

    def previousSiblingGenerator(self):
        i = self
        while i is not None:
            i = i.previousSibling
            yield i

    def parentGenerator(self):
        i = self
        while i is not None:
            i = i.parent
            yield i

    # Utility methods
    def substituteEncoding(self, str, encoding=None):
        encoding = encoding or "utf-8"
        return str.replace("%SOUP-ENCODING%", encoding)

    def toEncoding(self, s, encoding=None):
        """Encodes an object to a string in some encoding, or to Unicode.
        ."""
        if isinstance(s, unicode):
            if encoding:
                s = s.encode(encoding)
        elif isinstance(s, str):
            if encoding:
                s = s.encode(encoding)
            else:
                s = unicode(s)
        else:
            if encoding:
                s  = self.toEncoding(str(s), encoding)
            else:
                s = unicode(s)
        return s

    BARE_AMPERSAND_OR_BRACKET = re.compile("([<>]|"
                                           + "&(?!#\d+;|#x[0-9a-fA-F]+;|\w+;)"
                                           + ")")

    def _sub_entity(self, x):
        """Used with a regular expression to substitute the
        appropriate XML entity for an XML special character."""
        return "&" + self.XML_SPECIAL_CHARS_TO_ENTITIES[x.group(0)[0]] + ";"


class NavigableString(unicode, PageElement):

    def __new__(cls, value):
        """Create a new NavigableString.

        When unpickling a NavigableString, this method is called with
        the string in DEFAULT_OUTPUT_ENCODING. That encoding needs to be
        passed in to the superclass's __new__ or the superclass won't know
        how to handle non-ASCII characters.
        """
        if isinstance(value, unicode):
            return unicode.__new__(cls, value)
        return unicode.__new__(cls, value, DEFAULT_OUTPUT_ENCODING)

    def __getnewargs__(self):
        return (NavigableString.__str__(self),)

    def __getattr__(self, attr):
        """text.string gives you text. This is for backwards
        compatibility for Navigable*String, but for CData* it lets you
        get the string without the CData wrapper."""
        if attr == 'string':
            return self
        else:
            raise AttributeError, "'%s' object has no attribute '%s'" % (self.__class__.__name__, attr)

    def __unicode__(self):
        return str(self).decode(DEFAULT_OUTPUT_ENCODING)

    def __str__(self, encoding=DEFAULT_OUTPUT_ENCODING):
        # Substitute outgoing XML entities.
        data = self.BARE_AMPERSAND_OR_BRACKET.sub(self._sub_entity, self)
        if encoding:
            return data.encode(encoding)
        else:
            return data

class CData(NavigableString):

    def __str__(self, encoding=DEFAULT_OUTPUT_ENCODING):
        return "<![CDATA[%s]]>" % NavigableString.__str__(self, encoding)

class ProcessingInstruction(NavigableString):
    def __str__(self, encoding=DEFAULT_OUTPUT_ENCODING):
        output = self
        if "%SOUP-ENCODING%" in output:
            output = self.substituteEncoding(output, encoding)
        return "<?%s?>" % self.toEncoding(output, encoding)

class Comment(NavigableString):
    def __str__(self, encoding=DEFAULT_OUTPUT_ENCODING):
        return "<!--%s-->" % NavigableString.__str__(self, encoding)

class Declaration(NavigableString):
    def __str__(self, encoding=DEFAULT_OUTPUT_ENCODING):
        return "<!%s>" % NavigableString.__str__(self, encoding)

class Tag(PageElement):

    """Represents a found HTML tag with its attributes and contents."""

    def _convertEntities(self, match):
        """Used in a call to re.sub to replace HTML, XML, and numeric
        entities with the appropriate Unicode characters. If HTML
        entities are being converted, any unrecognized entities are
        escaped."""
        x = match.group(1)
        if self.convertHTMLEntities and x in name2codepoint:
            return unichr(name2codepoint[x])
        elif x in self.XML_ENTITIES_TO_SPECIAL_CHARS:
            if self.convertXMLEntities:
                return self.XML_ENTITIES_TO_SPECIAL_CHARS[x]
            else:
                return u'&%s;' % x
        elif len(x) > 0 and x[0] == '#':
            # Handle numeric entities
            if len(x) > 1 and x[1] == 'x':
                return unichr(int(x[2:], 16))
            else:
                return unichr(int(x[1:]))

        elif self.escapeUnrecognizedEntities:
            return u'&amp;%s;' % x
        else:
            return u'&%s;' % x

    def __init__(self, parser, name, attrs=None, parent=None,
                 previous=None):
        "Basic constructor."

        # We don't actually store the parser object: that lets extracted
        # chunks be garbage-collected
        self.parserClass = parser.__class__
        self.isSelfClosing = parser.isSelfClosingTag(name)
        self.name = name
        if attrs is None:
            attrs = []
        elif isinstance(attrs, dict):
            attrs = attrs.items()
        self.attrs = attrs
        self.contents = []
        self.setup(parent, previous)
        self.hidden = False
        self.containsSubstitutions = False
        self.convertHTMLEntities = parser.convertHTMLEntities
        self.convertXMLEntities = parser.convertXMLEntities
        self.escapeUnrecognizedEntities = parser.escapeUnrecognizedEntities

        # Convert any HTML, XML, or numeric entities in the attribute values.
        convert = lambda(k, val): (k,
                                   re.sub("&(#\d+|#x[0-9a-fA-F]+|\w+);",
                                          self._convertEntities,
                                          val))
        self.attrs = map(convert, self.attrs)

    def getString(self):
        if (len(self.contents) == 1
            and isinstance(self.contents[0], NavigableString)):
            return self.contents[0]

    def setString(self, string):
        """Replace the contents of the tag with a string"""
        self.clear()
        self.append(string)

    string = property(getString, setString)

    def getText(self, separator=u""):
        if not len(self.contents):
            return u""
        stopNode = self._lastRecursiveChild().next
        strings = []
        current = self.contents[0]
        while current is not stopNode:
            if isinstance(current, NavigableString):
                strings.append(current.strip())
            current = current.next
        return separator.join(strings)

    text = property(getText)

    def get(self, key, default=None):
        """Returns the value of the 'key' attribute for the tag, or
        the value given for 'default' if it doesn't have that
        attribute."""
        return self._getAttrMap().get(key, default)

    def clear(self):
        """Extract all children."""
        for child in self.contents[:]:
            child.extract()

    def index(self, element):
        for i, child in enumerate(self.contents):
            if child is element:
                return i
        raise ValueError("Tag.index: element not in tag")

    def has_key(self, key):
        return self._getAttrMap().has_key(key)

    def __getitem__(self, key):
        """tag[key] returns the value of the 'key' attribute for the tag,
        and throws an exception if it's not there."""
        return self._getAttrMap()[key]

    def __iter__(self):
        "Iterating over a tag iterates over its contents."
        return iter(self.contents)

    def __len__(self):
        "The length of a tag is the length of its list of contents."
        return len(self.contents)

    def __contains__(self, x):
        return x in self.contents

    def __nonzero__(self):
        "A tag is non-None even if it has no contents."
        return True

    def __setitem__(self, key, value):
        """Setting tag[key] sets the value of the 'key' attribute for the
        tag."""
        self._getAttrMap()
        self.attrMap[key] = value
        found = False
        for i in range(0, len(self.attrs)):
            if self.attrs[i][0] == key:
                self.attrs[i] = (key, value)
                found = True
        if not found:
            self.attrs.append((key, value))
        self._getAttrMap()[key] = value

    def __delitem__(self, key):
        "Deleting tag[key] deletes all 'key' attributes for the tag."
        for item in self.attrs:
            if item[0] == key:
                self.attrs.remove(item)
                #We don't break because bad HTML can define the same
                #attribute multiple times.
            self._getAttrMap()
            if self.attrMap.has_key(key):
                del self.attrMap[key]

    def __call__(self, *args, **kwargs):
        """Calling a tag like a function is the same as calling its
        findAll() method. Eg. tag('a') returns a list of all the A tags
        found within this tag."""
        return apply(self.findAll, args, kwargs)

    def __getattr__(self, tag):
        #print "Getattr %s.%s" % (self.__class__, tag)
        if len(tag) > 3 and tag.rfind('Tag') == len(tag)-3:
            return self.find(tag[:-3])
        elif tag.find('__') != 0:
            return self.find(tag)
        raise AttributeError, "'%s' object has no attribute '%s'" % (self.__class__, tag)

    def __eq__(self, other):
        """Returns true iff this tag has the same name, the same attributes,
        and the same contents (recursively) as the given tag.

        NOTE: right now this will return false if two tags have the
        same attributes in a different order. Should this be fixed?"""
        if other is self:
            return True
        if not hasattr(other, 'name') or not hasattr(other, 'attrs') or not hasattr(other, 'contents') or self.name != other.name or self.attrs != other.attrs or len(self) != len(other):
            return False
        for i in range(0, len(self.contents)):
            if self.contents[i] != other.contents[i]:
                return False
        return True

    def __ne__(self, other):
        """Returns true iff this tag is not identical to the other tag,
        as defined in __eq__."""
        return not self == other

    def __repr__(self, encoding=DEFAULT_OUTPUT_ENCODING):
        """Renders this tag as a string."""
        return self.__str__(encoding)

    def __unicode__(self):
        return self.__str__(None)

    def __str__(self, encoding=DEFAULT_OUTPUT_ENCODING,
                prettyPrint=False, indentLevel=0):
        """Returns a string or Unicode representation of this tag and
        its contents. To get Unicode, pass None for encoding.

        NOTE: since Python's HTML parser consumes whitespace, this
        method is not certain to reproduce the whitespace present in
        the original string."""

        encodedName = self.toEncoding(self.name, encoding)

        attrs = []
        if self.attrs:
            for key, val in self.attrs:
                fmt = '%s="%s"'
                if isinstance(val, basestring):
                    if self.containsSubstitutions and '%SOUP-ENCODING%' in val:
                        val = self.substituteEncoding(val, encoding)

                    # The attribute value either:
                    #
                    # * Contains no embedded double quotes or single quotes.
                    #   No problem: we enclose it in double quotes.
                    # * Contains embedded single quotes. No problem:
                    #   double quotes work here too.
                    # * Contains embedded double quotes. No problem:
                    #   we enclose it in single quotes.
                    # * Embeds both single _and_ double quotes. This
                    #   can't happen naturally, but it can happen if
                    #   you modify an attribute value after parsing
                    #   the document. Now we have a bit of a
                    #   problem. We solve it by enclosing the
                    #   attribute in single quotes, and escaping any
                    #   embedded single quotes to XML entities.
                    if '"' in val:
                        fmt = "%s='%s'"
                        if "'" in val:
                            # TODO: replace with apos when
                            # appropriate.
                            val = val.replace("'", "&squot;")

                    # Now we're okay w/r/t quotes. But the attribute
                    # value might also contain angle brackets, or
                    # ampersands that aren't part of entities. We need
                    # to escape those to XML entities too.
                    val = self.BARE_AMPERSAND_OR_BRACKET.sub(self._sub_entity, val)

                attrs.append(fmt % (self.toEncoding(key, encoding),
                                    self.toEncoding(val, encoding)))
        close = ''
        closeTag = ''
        if self.isSelfClosing:
            close = ' /'
        else:
            closeTag = '</%s>' % encodedName

        indentTag, indentContents = 0, 0
        if prettyPrint:
            indentTag = indentLevel
            space = (' ' * (indentTag-1))
            indentContents = indentTag + 1
        contents = self.renderContents(encoding, prettyPrint, indentContents)
        if self.hidden:
            s = contents
        else:
            s = []
            attributeString = ''
            if attrs:
                attributeString = ' ' + ' '.join(attrs)
            if prettyPrint:
                s.append(space)
            s.append('<%s%s%s>' % (encodedName, attributeString, close))
            if prettyPrint:
                s.append("\n")
            s.append(contents)
            if prettyPrint and contents and contents[-1] != "\n":
                s.append("\n")
            if prettyPrint and closeTag:
                s.append(space)
            s.append(closeTag)
            if prettyPrint and closeTag and self.nextSibling:
                s.append("\n")
            s = ''.join(s)
        return s

    def decompose(self):
        """Recursively destroys the contents of this tree."""
        self.extract()
        if len(self.contents) == 0:
            return
        current = self.contents[0]
        while current is not None:
            next = current.next
            if isinstance(current, Tag):
                del current.contents[:]
            current.parent = None
            current.previous = None
            current.previousSibling = None
            current.next = None
            current.nextSibling = None
            current = next

    def prettify(self, encoding=DEFAULT_OUTPUT_ENCODING):
        return self.__str__(encoding, True)

    def renderContents(self, encoding=DEFAULT_OUTPUT_ENCODING,
                       prettyPrint=False, indentLevel=0):
        """Renders the contents of this tag as a string in the given
        encoding. If encoding is None, returns a Unicode string.."""
        s=[]
        for c in self:
            text = None
            if isinstance(c, NavigableString):
                text = c.__str__(encoding)
            elif isinstance(c, Tag):
                s.append(c.__str__(encoding, prettyPrint, indentLevel))
            if text and prettyPrint:
                text = text.strip()
            if text:
                if prettyPrint:
                    s.append(" " * (indentLevel-1))
                s.append(text)
                if prettyPrint:
                    s.append("\n")
        return ''.join(s)

    #Soup methods

    def find(self, name=None, attrs={}, recursive=True, text=None,
             **kwargs):
        """Return only the first child of this Tag matching the given
        criteria."""
        r = None
        l = self.findAll(name, attrs, recursive, text, 1, **kwargs)
        if l:
            r = l[0]
        return r
    findChild = find

    def findAll(self, name=None, attrs={}, recursive=True, text=None,
                limit=None, **kwargs):
        """Extracts a list of Tag objects that match the given
        criteria.  You can specify the name of the Tag and any
        attributes you want the Tag to have.

        The value of a key-value pair in the 'attrs' map can be a
        string, a list of strings, a regular expression object, or a
        callable that takes a string and returns whether or not the
        string matches for some custom definition of 'matches'. The
        same is true of the tag name."""
        generator = self.recursiveChildGenerator
        if not recursive:
            generator = self.childGenerator
        return self._findAll(name, attrs, text, limit, generator, **kwargs)
    findChildren = findAll

    # Pre-3.x compatibility methods
    first = find
    fetch = findAll

    def fetchText(self, text=None, recursive=True, limit=None):
        return self.findAll(text=text, recursive=recursive, limit=limit)

    def firstText(self, text=None, recursive=True):
        return self.find(text=text, recursive=recursive)

    #Private methods

    def _getAttrMap(self):
        """Initializes a map representation of this tag's attributes,
        if not already initialized."""
        if not getattr(self, 'attrMap'):
            self.attrMap = {}
            for (key, value) in self.attrs:
                self.attrMap[key] = value
        return self.attrMap

    #Generator methods
    def childGenerator(self):
        # Just use the iterator from the contents
        return iter(self.contents)

    def recursiveChildGenerator(self):
        if not len(self.contents):
            raise StopIteration
        stopNode = self._lastRecursiveChild().next
        current = self.contents[0]
        while current is not stopNode:
            yield current
            current = current.next


# Next, a couple classes to represent queries and their results.
class SoupStrainer:
    """Encapsulates a number of ways of matching a markup element (tag or
    text)."""

    def __init__(self, name=None, attrs={}, text=None, **kwargs):
        self.name = name
        if isinstance(attrs, basestring):
            kwargs['class'] = _match_css_class(attrs)
            attrs = None
        if kwargs:
            if attrs:
                attrs = attrs.copy()
                attrs.update(kwargs)
            else:
                attrs = kwargs
        self.attrs = attrs
        self.text = text

    def __str__(self):
        if self.text:
            return self.text
        else:
            return "%s|%s" % (self.name, self.attrs)

    def searchTag(self, markupName=None, markupAttrs={}):
        found = None
        markup = None
        if isinstance(markupName, Tag):
            markup = markupName
            markupAttrs = markup
        callFunctionWithTagData = callable(self.name) \
                                and not isinstance(markupName, Tag)

        if (not self.name) \
               or callFunctionWithTagData \
               or (markup and self._matches(markup, self.name)) \
               or (not markup and self._matches(markupName, self.name)):
            if callFunctionWithTagData:
                match = self.name(markupName, markupAttrs)
            else:
                match = True
                markupAttrMap = None
                for attr, matchAgainst in self.attrs.items():
                    if not markupAttrMap:
                         if hasattr(markupAttrs, 'get'):
                            markupAttrMap = markupAttrs
                         else:
                            markupAttrMap = {}
                            for k,v in markupAttrs:
                                markupAttrMap[k] = v
                    attrValue = markupAttrMap.get(attr)
                    if not self._matches(attrValue, matchAgainst):
                        match = False
                        break
            if match:
                if markup:
                    found = markup
                else:
                    found = markupName
        return found

    def search(self, markup):
        #print 'looking for %s in %s' % (self, markup)
        found = None
        # If given a list of items, scan it for a text element that
        # matches.
        if hasattr(markup, "__iter__") \
                and not isinstance(markup, Tag):
            for element in markup:
                if isinstance(element, NavigableString) \
                       and self.search(element):
                    found = element
                    break
        # If it's a Tag, make sure its name or attributes match.
        # Don't bother with Tags if we're searching for text.
        elif isinstance(markup, Tag):
            if not self.text:
                found = self.searchTag(markup)
        # If it's text, make sure the text matches.
        elif isinstance(markup, NavigableString) or \
                 isinstance(markup, basestring):
            if self._matches(markup, self.text):
                found = markup
        else:
            raise Exception, "I don't know how to match against a %s" \
                  % markup.__class__
        return found

    def _matches(self, markup, matchAgainst):
        #print "Matching %s against %s" % (markup, matchAgainst)
        result = False
        if matchAgainst is True:
            result = markup is not None
        elif callable(matchAgainst):
            result = matchAgainst(markup)
        else:
            #Custom match methods take the tag as an argument, but all
            #other ways of matching match the tag name as a string.
            if isinstance(markup, Tag):
                markup = markup.name
            if markup and not isinstance(markup, basestring):
                markup = unicode(markup)
            #Now we know that chunk is either a string, or None.
            if hasattr(matchAgainst, 'match'):
                # It's a regexp object.
                result = markup and matchAgainst.search(markup)
            elif hasattr(matchAgainst, '__iter__'): # list-like
                result = markup in matchAgainst
            elif hasattr(matchAgainst, 'items'):
                result = markup.has_key(matchAgainst)
            elif matchAgainst and isinstance(markup, basestring):
                if isinstance(markup, unicode):
                    matchAgainst = unicode(matchAgainst)
                else:
                    matchAgainst = str(matchAgainst)

            if not result:
                result = matchAgainst == markup
        return result

class ResultSet(list):
    """A ResultSet is just a list that keeps track of the SoupStrainer
    that created it."""
    def __init__(self, source):
        list.__init__([])
        self.source = source

# Now, some helper functions.

def buildTagMap(default, *args):
    """Turns a list of maps, lists, or scalars into a single map.
    Used to build the SELF_CLOSING_TAGS, NESTABLE_TAGS, and
    NESTING_RESET_TAGS maps out of lists and partial maps."""
    built = {}
    for portion in args:
        if hasattr(portion, 'items'):
            #It's a map. Merge it.
            for k,v in portion.items():
                built[k] = v
        elif hasattr(portion, '__iter__'): # is a list
            #It's a list. Map each item to the default.
            for k in portion:
                built[k] = default
        else:
            #It's a scalar. Map it to the default.
            built[portion] = default
    return built

# Now, the parser classes.

class BeautifulStoneSoup(Tag, SGMLParser):

    """This class contains the basic parser and search code. It defines
    a parser that knows nothing about tag behavior except for the
    following:

      You can't close a tag without closing all the tags it encloses.
      That is, "<foo><bar></foo>" actually means
      "<foo><bar></bar></foo>".

    [Another possible explanation is "<foo><bar /></foo>", but since
    this class defines no SELF_CLOSING_TAGS, it will never use that
    explanation.]

    This class is useful for parsing XML or made-up markup languages,
    or when BeautifulSoup makes an assumption counter to what you were
    expecting."""

    SELF_CLOSING_TAGS = {}
    NESTABLE_TAGS = {}
    RESET_NESTING_TAGS = {}
    QUOTE_TAGS = {}
    PRESERVE_WHITESPACE_TAGS = []

    MARKUP_MASSAGE = [(re.compile('(<[^<>]*)/>'),
                       lambda x: x.group(1) + ' />'),
                      (re.compile('<!\s+([^<>]*)>'),
                       lambda x: '<!' + x.group(1) + '>')
                      ]

    ROOT_TAG_NAME = u'[document]'

    HTML_ENTITIES = "html"
    XML_ENTITIES = "xml"
    XHTML_ENTITIES = "xhtml"
    # TODO: This only exists for backwards-compatibility
    ALL_ENTITIES = XHTML_ENTITIES

    # Used when determining whether a text node is all whitespace and
    # can be replaced with a single space. A text node that contains
    # fancy Unicode spaces (usually non-breaking) should be left
    # alone.
    STRIP_ASCII_SPACES = { 9: None, 10: None, 12: None, 13: None, 32: None, }

    def __init__(self, markup="", parseOnlyThese=None, fromEncoding=None,
                 markupMassage=True, smartQuotesTo=XML_ENTITIES,
                 convertEntities=None, selfClosingTags=None, isHTML=False):
        """The Soup object is initialized as the 'root tag', and the
        provided markup (which can be a string or a file-like object)
        is fed into the underlying parser.

        sgmllib will process most bad HTML, and the BeautifulSoup
        class has some tricks for dealing with some HTML that kills
        sgmllib, but Beautiful Soup can nonetheless choke or lose data
        if your data uses self-closing tags or declarations
        incorrectly.

        By default, Beautiful Soup uses regexes to sanitize input,
        avoiding the vast majority of these problems. If the problems
        don't apply to you, pass in False for markupMassage, and
        you'll get better performance.

        The default parser massage techniques fix the two most common
        instances of invalid HTML that choke sgmllib:

         <br/> (No space between name of closing tag and tag close)
         <! --Comment--> (Extraneous whitespace in declaration)

        You can pass in a custom list of (RE object, replace method)
        tuples to get Beautiful Soup to scrub your input the way you
        want."""

        self.parseOnlyThese = parseOnlyThese
        self.fromEncoding = fromEncoding
        self.smartQuotesTo = smartQuotesTo
        self.convertEntities = convertEntities
        # Set the rules for how we'll deal with the entities we
        # encounter
        if self.convertEntities:
            # It doesn't make sense to convert encoded characters to
            # entities even while you're converting entities to Unicode.
            # Just convert it all to Unicode.
            self.smartQuotesTo = None
            if convertEntities == self.HTML_ENTITIES:
                self.convertXMLEntities = False
                self.convertHTMLEntities = True
                self.escapeUnrecognizedEntities = True
            elif convertEntities == self.XHTML_ENTITIES:
                self.convertXMLEntities = True
                self.convertHTMLEntities = True
                self.escapeUnrecognizedEntities = False
            elif convertEntities == self.XML_ENTITIES:
                self.convertXMLEntities = True
                self.convertHTMLEntities = False
                self.escapeUnrecognizedEntities = False
        else:
            self.convertXMLEntities = False
            self.convertHTMLEntities = False
            self.escapeUnrecognizedEntities = False

        self.instanceSelfClosingTags = buildTagMap(None, selfClosingTags)
        SGMLParser.__init__(self)

        if hasattr(markup, 'read'):        # It's a file-type object.
            markup = markup.read()
        self.markup = markup
        self.markupMassage = markupMassage
        try:
            self._feed(isHTML=isHTML)
        except StopParsing:
            pass
        self.markup = None                 # The markup can now be GCed

    def convert_charref(self, name):
        """This method fixes a bug in Python's SGMLParser."""
        try:
            n = int(name)
        except ValueError:
            return
        if not 0 <= n <= 127 : # ASCII ends at 127, not 255
            return
        return self.convert_codepoint(n)

    def _feed(self, inDocumentEncoding=None, isHTML=False):
        # Convert the document to Unicode.
        markup = self.markup
        if isinstance(markup, unicode):
            if not hasattr(self, 'originalEncoding'):
                self.originalEncoding = None
        else:
            dammit = UnicodeDammit\
                     (markup, [self.fromEncoding, inDocumentEncoding],
                      smartQuotesTo=self.smartQuotesTo, isHTML=isHTML)
            markup = dammit.unicode
            self.originalEncoding = dammit.originalEncoding
            self.declaredHTMLEncoding = dammit.declaredHTMLEncoding
        if markup:
            if self.markupMassage:
                if not hasattr(self.markupMassage, "__iter__"):
                    self.markupMassage = self.MARKUP_MASSAGE
                for fix, m in self.markupMassage:
                    markup = fix.sub(m, markup)
                # TODO: We get rid of markupMassage so that the
                # soup object can be deepcopied later on. Some
                # Python installations can't copy regexes. If anyone
                # was relying on the existence of markupMassage, this
                # might cause problems.
                del(self.markupMassage)
        self.reset()

        SGMLParser.feed(self, markup)
        # Close out any unfinished strings and close all the open tags.
        self.endData()
        while self.currentTag.name != self.ROOT_TAG_NAME:
            self.popTag()

    def __getattr__(self, methodName):
        """This method routes method call requests to either the SGMLParser
        superclass or the Tag superclass, depending on the method name."""
        #print "__getattr__ called on %s.%s" % (self.__class__, methodName)

        if methodName.startswith('start_') or methodName.startswith('end_') \
               or methodName.startswith('do_'):
            return SGMLParser.__getattr__(self, methodName)
        elif not methodName.startswith('__'):
            return Tag.__getattr__(self, methodName)
        else:
            raise AttributeError

    def isSelfClosingTag(self, name):
        """Returns true iff the given string is the name of a
        self-closing tag according to this parser."""
        return self.SELF_CLOSING_TAGS.has_key(name) \
               or self.instanceSelfClosingTags.has_key(name)

    def reset(self):
        Tag.__init__(self, self, self.ROOT_TAG_NAME)
        self.hidden = 1
        SGMLParser.reset(self)
        self.currentData = []
        self.currentTag = None
        self.tagStack = []
        self.quoteStack = []
        self.pushTag(self)

    def popTag(self):
        tag = self.tagStack.pop()

        #print "Pop", tag.name
        if self.tagStack:
            self.currentTag = self.tagStack[-1]
        return self.currentTag

    def pushTag(self, tag):
        #print "Push", tag.name
        if self.currentTag:
            self.currentTag.contents.append(tag)
        self.tagStack.append(tag)
        self.currentTag = self.tagStack[-1]

    def endData(self, containerClass=NavigableString):
        if self.currentData:
            currentData = u''.join(self.currentData)
            if (currentData.translate(self.STRIP_ASCII_SPACES) == '' and
                not set([tag.name for tag in self.tagStack]).intersection(
                    self.PRESERVE_WHITESPACE_TAGS)):
                if '\n' in currentData:
                    currentData = '\n'
                else:
                    currentData = ' '
            self.currentData = []
            if self.parseOnlyThese and len(self.tagStack) <= 1 and \
                   (not self.parseOnlyThese.text or \
                    not self.parseOnlyThese.search(currentData)):
                return
            o = containerClass(currentData)
            o.setup(self.currentTag, self.previous)
            if self.previous:
                self.previous.next = o
            self.previous = o
            self.currentTag.contents.append(o)


    def _popToTag(self, name, inclusivePop=True):
        """Pops the tag stack up to and including the most recent
        instance of the given tag. If inclusivePop is false, pops the tag
        stack up to but *not* including the most recent instqance of
        the given tag."""
        #print "Popping to %s" % name
        if name == self.ROOT_TAG_NAME:
            return

        numPops = 0
        mostRecentTag = None
        for i in range(len(self.tagStack)-1, 0, -1):
            if name == self.tagStack[i].name:
                numPops = len(self.tagStack)-i
                break
        if not inclusivePop:
            numPops = numPops - 1

        for i in range(0, numPops):
            mostRecentTag = self.popTag()
        return mostRecentTag

    def _smartPop(self, name):

        """We need to pop up to the previous tag of this type, unless
        one of this tag's nesting reset triggers comes between this
        tag and the previous tag of this type, OR unless this tag is a
        generic nesting trigger and another generic nesting trigger
        comes between this tag and the previous tag of this type.

        Examples:
         <p>Foo<b>Bar *<p>* should pop to 'p', not 'b'.
         <p>Foo<table>Bar *<p>* should pop to 'table', not 'p'.
         <p>Foo<table><tr>Bar *<p>* should pop to 'tr', not 'p'.

         <li><ul><li> *<li>* should pop to 'ul', not the first 'li'.
         <tr><table><tr> *<tr>* should pop to 'table', not the first 'tr'
         <td><tr><td> *<td>* should pop to 'tr', not the first 'td'
        """

        nestingResetTriggers = self.NESTABLE_TAGS.get(name)
        isNestable = nestingResetTriggers != None
        isResetNesting = self.RESET_NESTING_TAGS.has_key(name)
        popTo = None
        inclusive = True
        for i in range(len(self.tagStack)-1, 0, -1):
            p = self.tagStack[i]
            if (not p or p.name == name) and not isNestable:
                #Non-nestable tags get popped to the top or to their
                #last occurance.
                popTo = name
                break
            if (nestingResetTriggers is not None
                and p.name in nestingResetTriggers) \
                or (nestingResetTriggers is None and isResetNesting
                    and self.RESET_NESTING_TAGS.has_key(p.name)):

                #If we encounter one of the nesting reset triggers
                #peculiar to this tag, or we encounter another tag
                #that causes nesting to reset, pop up to but not
                #including that tag.
                popTo = p.name
                inclusive = False
                break
            p = p.parent
        if popTo:
            self._popToTag(popTo, inclusive)

    def unknown_starttag(self, name, attrs, selfClosing=0):
        #print "Start tag %s: %s" % (name, attrs)
        if self.quoteStack:
            #This is not a real tag.
            #print "<%s> is not real!" % name
            attrs = ''.join([' %s="%s"' % (x, y) for x, y in attrs])
            self.handle_data('<%s%s>' % (name, attrs))
            return
        self.endData()

        if not self.isSelfClosingTag(name) and not selfClosing:
            self._smartPop(name)

        if self.parseOnlyThese and len(self.tagStack) <= 1 \
               and (self.parseOnlyThese.text or not self.parseOnlyThese.searchTag(name, attrs)):
            return

        tag = Tag(self, name, attrs, self.currentTag, self.previous)
        if self.previous:
            self.previous.next = tag
        self.previous = tag
        self.pushTag(tag)
        if selfClosing or self.isSelfClosingTag(name):
            self.popTag()
        if name in self.QUOTE_TAGS:
            #print "Beginning quote (%s)" % name
            self.quoteStack.append(name)
            self.literal = 1
        return tag

    def unknown_endtag(self, name):
        #print "End tag %s" % name
        if self.quoteStack and self.quoteStack[-1] != name:
            #This is not a real end tag.
            #print "</%s> is not real!" % name
            self.handle_data('</%s>' % name)
            return
        self.endData()
        self._popToTag(name)
        if self.quoteStack and self.quoteStack[-1] == name:
            self.quoteStack.pop()
            self.literal = (len(self.quoteStack) > 0)

    def handle_data(self, data):
        self.currentData.append(data)

    def _toStringSubclass(self, text, subclass):
        """Adds a certain piece of text to the tree as a NavigableString
        subclass."""
        self.endData()
        self.handle_data(text)
        self.endData(subclass)

    def handle_pi(self, text):
        """Handle a processing instruction as a ProcessingInstruction
        object, possibly one with a %SOUP-ENCODING% slot into which an
        encoding will be plugged later."""
        if text[:3] == "xml":
            text = u"xml version='1.0' encoding='%SOUP-ENCODING%'"
        self._toStringSubclass(text, ProcessingInstruction)

    def handle_comment(self, text):
        "Handle comments as Comment objects."
        self._toStringSubclass(text, Comment)

    def handle_charref(self, ref):
        "Handle character references as data."
        if self.convertEntities:
            data = unichr(int(ref))
        else:
            data = '&#%s;' % ref
        self.handle_data(data)

    def handle_entityref(self, ref):
        """Handle entity references as data, possibly converting known
        HTML and/or XML entity references to the corresponding Unicode
        characters."""
        data = None
        if self.convertHTMLEntities:
            try:
                data = unichr(name2codepoint[ref])
            except KeyError:
                pass

        if not data and self.convertXMLEntities:
                data = self.XML_ENTITIES_TO_SPECIAL_CHARS.get(ref)

        if not data and self.convertHTMLEntities and \
            not self.XML_ENTITIES_TO_SPECIAL_CHARS.get(ref):
                # TODO: We've got a problem here. We're told this is
                # an entity reference, but it's not an XML entity
                # reference or an HTML entity reference. Nonetheless,
                # the logical thing to do is to pass it through as an
                # unrecognized entity reference.
                #
                # Except: when the input is "&carol;" this function
                # will be called with input "carol". When the input is
                # "AT&T", this function will be called with input
                # "T". We have no way of knowing whether a semicolon
                # was present originally, so we don't know whether
                # this is an unknown entity or just a misplaced
                # ampersand.
                #
                # The more common case is a misplaced ampersand, so I
                # escape the ampersand and omit the trailing semicolon.
                data = "&amp;%s" % ref
        if not data:
            # This case is different from the one above, because we
            # haven't already gone through a supposedly comprehensive
            # mapping of entities to Unicode characters. We might not
            # have gone through any mapping at all. So the chances are
            # very high that this is a real entity, and not a
            # misplaced ampersand.
            data = "&%s;" % ref
        self.handle_data(data)

    def handle_decl(self, data):
        "Handle DOCTYPEs and the like as Declaration objects."
        self._toStringSubclass(data, Declaration)

    def parse_declaration(self, i):
        """Treat a bogus SGML declaration as raw data. Treat a CDATA
        declaration as a CData object."""
        j = None
        if self.rawdata[i:i+9] == '<![CDATA[':
             k = self.rawdata.find(']]>', i)
             if k == -1:
                 k = len(self.rawdata)
             data = self.rawdata[i+9:k]
             j = k+3
             self._toStringSubclass(data, CData)
        else:
            try:
                j = SGMLParser.parse_declaration(self, i)
            except SGMLParseError:
                toHandle = self.rawdata[i:]
                self.handle_data(toHandle)
                j = i + len(toHandle)
        return j

class BeautifulSoup(BeautifulStoneSoup):

    """This parser knows the following facts about HTML:

    * Some tags have no closing tag and should be interpreted as being
      closed as soon as they are encountered.

    * The text inside some tags (ie. 'script') may contain tags which
      are not really part of the document and which should be parsed
      as text, not tags. If you want to parse the text as tags, you can
      always fetch it and parse it explicitly.

    * Tag nesting rules:

      Most tags can't be nested at all. For instance, the occurance of
      a <p> tag should implicitly close the previous <p> tag.

       <p>Para1<p>Para2
        should be transformed into:
       <p>Para1</p><p>Para2

      Some tags can be nested arbitrarily. For instance, the occurance
      of a <blockquote> tag should _not_ implicitly close the previous
      <blockquote> tag.

       Alice said: <blockquote>Bob said: <blockquote>Blah
        should NOT be transformed into:
       Alice said: <blockquote>Bob said: </blockquote><blockquote>Blah

      Some tags can be nested, but the nesting is reset by the
      interposition of other tags. For instance, a <tr> tag should
      implicitly close the previous <tr> tag within the same <table>,
      but not close a <tr> tag in another table.

       <table><tr>Blah<tr>Blah
        should be transformed into:
       <table><tr>Blah</tr><tr>Blah
        but,
       <tr>Blah<table><tr>Blah
        should NOT be transformed into
       <tr>Blah<table></tr><tr>Blah

    Differing assumptions about tag nesting rules are a major source
    of problems with the BeautifulSoup class. If BeautifulSoup is not
    treating as nestable a tag your page author treats as nestable,
    try ICantBelieveItsBeautifulSoup, MinimalSoup, or
    BeautifulStoneSoup before writing your own subclass."""

    def __init__(self, *args, **kwargs):
        if not kwargs.has_key('smartQuotesTo'):
            kwargs['smartQuotesTo'] = self.HTML_ENTITIES
        kwargs['isHTML'] = True
        BeautifulStoneSoup.__init__(self, *args, **kwargs)

    SELF_CLOSING_TAGS = buildTagMap(None,
                                    ('br' , 'hr', 'input', 'img', 'meta',
                                    'spacer', 'link', 'frame', 'base', 'col'))

    PRESERVE_WHITESPACE_TAGS = set(['pre', 'textarea'])

    QUOTE_TAGS = {'script' : None, 'textarea' : None}

    #According to the HTML standard, each of these inline tags can
    #contain another tag of the same type. Furthermore, it's common
    #to actually use these tags this way.
    NESTABLE_INLINE_TAGS = ('span', 'font', 'q', 'object', 'bdo', 'sub', 'sup',
                            'center')

    #According to the HTML standard, these block tags can contain
    #another tag of the same type. Furthermore, it's common
    #to actually use these tags this way.
    NESTABLE_BLOCK_TAGS = ('blockquote', 'div', 'fieldset', 'ins', 'del')

    #Lists can contain other lists, but there are restrictions.
    NESTABLE_LIST_TAGS = { 'ol' : [],
                           'ul' : [],
                           'li' : ['ul', 'ol'],
                           'dl' : [],
                           'dd' : ['dl'],
                           'dt' : ['dl'] }

    #Tables can contain other tables, but there are restrictions.
    NESTABLE_TABLE_TAGS = {'table' : [],
                           'tr' : ['table', 'tbody', 'tfoot', 'thead'],
                           'td' : ['tr'],
                           'th' : ['tr'],
                           'thead' : ['table'],
                           'tbody' : ['table'],
                           'tfoot' : ['table'],
                           }

    NON_NESTABLE_BLOCK_TAGS = ('address', 'form', 'p', 'pre')

    #If one of these tags is encountered, all tags up to the next tag of
    #this type are popped.
    RESET_NESTING_TAGS = buildTagMap(None, NESTABLE_BLOCK_TAGS, 'noscript',
                                     NON_NESTABLE_BLOCK_TAGS,
                                     NESTABLE_LIST_TAGS,
                                     NESTABLE_TABLE_TAGS)

    NESTABLE_TAGS = buildTagMap([], NESTABLE_INLINE_TAGS, NESTABLE_BLOCK_TAGS,
                                NESTABLE_LIST_TAGS, NESTABLE_TABLE_TAGS)

    # Used to detect the charset in a META tag; see start_meta
    CHARSET_RE = re.compile("((^|;)\s*charset=)([^;]*)", re.M)

    def start_meta(self, attrs):
        """Beautiful Soup can detect a charset included in a META tag,
        try to convert the document to that charset, and re-parse the
        document from the beginning."""
        httpEquiv = None
        contentType = None
        contentTypeIndex = None
        tagNeedsEncodingSubstitution = False

        for i in range(0, len(attrs)):
            key, value = attrs[i]
            key = key.lower()
            if key == 'http-equiv':
                httpEquiv = value
            elif key == 'content':
                contentType = value
                contentTypeIndex = i

        if httpEquiv and contentType: # It's an interesting meta tag.
            match = self.CHARSET_RE.search(contentType)
            if match:
                if (self.declaredHTMLEncoding is not None or
                    self.originalEncoding == self.fromEncoding):
                    # An HTML encoding was sniffed while converting
                    # the document to Unicode, or an HTML encoding was
                    # sniffed during a previous pass through the
                    # document, or an encoding was specified
                    # explicitly and it worked. Rewrite the meta tag.
                    def rewrite(match):
                        return match.group(1) + "%SOUP-ENCODING%"
                    newAttr = self.CHARSET_RE.sub(rewrite, contentType)
                    attrs[contentTypeIndex] = (attrs[contentTypeIndex][0],
                                               newAttr)
                    tagNeedsEncodingSubstitution = True
                else:
                    # This is our first pass through the document.
                    # Go through it again with the encoding information.
                    newCharset = match.group(3)
                    if newCharset and newCharset != self.originalEncoding:
                        self.declaredHTMLEncoding = newCharset
                        self._feed(self.declaredHTMLEncoding)
                        raise StopParsing
                    pass
        tag = self.unknown_starttag("meta", attrs)
        if tag and tagNeedsEncodingSubstitution:
            tag.containsSubstitutions = True

class StopParsing(Exception):
    pass

class ICantBelieveItsBeautifulSoup(BeautifulSoup):

    """The BeautifulSoup class is oriented towards skipping over
    common HTML errors like unclosed tags. However, sometimes it makes
    errors of its own. For instance, consider this fragment:

     <b>Foo<b>Bar</b></b>

    This is perfectly valid (if bizarre) HTML. However, the
    BeautifulSoup class will implicitly close the first b tag when it
    encounters the second 'b'. It will think the author wrote
    "<b>Foo<b>Bar", and didn't close the first 'b' tag, because
    there's no real-world reason to bold something that's already
    bold. When it encounters '</b></b>' it will close two more 'b'
    tags, for a grand total of three tags closed instead of two. This
    can throw off the rest of your document structure. The same is
    true of a number of other tags, listed below.

    It's much more common for someone to forget to close a 'b' tag
    than to actually use nested 'b' tags, and the BeautifulSoup class
    handles the common case. This class handles the not-co-common
    case: where you can't believe someone wrote what they did, but
    it's valid HTML and BeautifulSoup screwed up by assuming it
    wouldn't be."""

    I_CANT_BELIEVE_THEYRE_NESTABLE_INLINE_TAGS = \
     ('em', 'big', 'i', 'small', 'tt', 'abbr', 'acronym', 'strong',
      'cite', 'code', 'dfn', 'kbd', 'samp', 'strong', 'var', 'b',
      'big')

    I_CANT_BELIEVE_THEYRE_NESTABLE_BLOCK_TAGS = ('noscript',)

    NESTABLE_TAGS = buildTagMap([], BeautifulSoup.NESTABLE_TAGS,
                                I_CANT_BELIEVE_THEYRE_NESTABLE_BLOCK_TAGS,
                                I_CANT_BELIEVE_THEYRE_NESTABLE_INLINE_TAGS)

class MinimalSoup(BeautifulSoup):
    """The MinimalSoup class is for parsing HTML that contains
    pathologically bad markup. It makes no assumptions about tag
    nesting, but it does know which tags are self-closing, that
    <script> tags contain Javascript and should not be parsed, that
    META tags may contain encoding information, and so on.

    This also makes it better for subclassing than BeautifulStoneSoup
    or BeautifulSoup."""

    RESET_NESTING_TAGS = buildTagMap('noscript')
    NESTABLE_TAGS = {}

class BeautifulSOAP(BeautifulStoneSoup):
    """This class will push a tag with only a single string child into
    the tag's parent as an attribute. The attribute's name is the tag
    name, and the value is the string child. An example should give
    the flavor of the change:

    <foo><bar>baz</bar></foo>
     =>
    <foo bar="baz"><bar>baz</bar></foo>

    You can then access fooTag['bar'] instead of fooTag.barTag.string.

    This is, of course, useful for scraping structures that tend to
    use subelements instead of attributes, such as SOAP messages. Note
    that it modifies its input, so don't print the modified version
    out.

    I'm not sure how many people really want to use this class; let me
    know if you do. Mainly I like the name."""

    def popTag(self):
        if len(self.tagStack) > 1:
            tag = self.tagStack[-1]
            parent = self.tagStack[-2]
            parent._getAttrMap()
            if (isinstance(tag, Tag) and len(tag.contents) == 1 and
                isinstance(tag.contents[0], NavigableString) and
                not parent.attrMap.has_key(tag.name)):
                parent[tag.name] = tag.contents[0]
        BeautifulStoneSoup.popTag(self)

#Enterprise class names! It has come to our attention that some people
#think the names of the Beautiful Soup parser classes are too silly
#and "unprofessional" for use in enterprise screen-scraping. We feel
#your pain! For such-minded folk, the Beautiful Soup Consortium And
#All-Night Kosher Bakery recommends renaming this file to
#"RobustParser.py" (or, in cases of extreme enterprisiness,
#"RobustParserBeanInterface.class") and using the following
#enterprise-friendly class aliases:
class RobustXMLParser(BeautifulStoneSoup):
    pass
class RobustHTMLParser(BeautifulSoup):
    pass
class RobustWackAssHTMLParser(ICantBelieveItsBeautifulSoup):
    pass
class RobustInsanelyWackAssHTMLParser(MinimalSoup):
    pass
class SimplifyingSOAPParser(BeautifulSOAP):
    pass

######################################################
#
# Bonus library: Unicode, Dammit
#
# This class forces XML data into a standard format (usually to UTF-8
# or Unicode).  It is heavily based on code from Mark Pilgrim's
# Universal Feed Parser. It does not rewrite the XML or HTML to
# reflect a new encoding: that happens in BeautifulStoneSoup.handle_pi
# (XML) and BeautifulSoup.start_meta (HTML).

# Autodetects character encodings.
# Download from http://chardet.feedparser.org/
try:
    import chardet
#    import chardet.constants
#    chardet.constants._debug = 1
except ImportError:
    chardet = None

# cjkcodecs and iconv_codec make Python know about more character encodings.
# Both are available from http://cjkpython.i18n.org/
# They're built in if you use Python 2.4.
try:
    import cjkcodecs.aliases
except ImportError:
    pass
try:
    import iconv_codec
except ImportError:
    pass

class UnicodeDammit:
    """A class for detecting the encoding of a *ML document and
    converting it to a Unicode string. If the source encoding is
    windows-1252, can replace MS smart quotes with their HTML or XML
    equivalents."""

    # This dictionary maps commonly seen values for "charset" in HTML
    # meta tags to the corresponding Python codec names. It only covers
    # values that aren't in Python's aliases and can't be determined
    # by the heuristics in find_codec.
    CHARSET_ALIASES = { "macintosh" : "mac-roman",
                        "x-sjis" : "shift-jis" }

    def __init__(self, markup, overrideEncodings=[],
                 smartQuotesTo='xml', isHTML=False):
        self.declaredHTMLEncoding = None
        self.markup, documentEncoding, sniffedEncoding = \
                     self._detectEncoding(markup, isHTML)
        self.smartQuotesTo = smartQuotesTo
        self.triedEncodings = []
        if markup == '' or isinstance(markup, unicode):
            self.originalEncoding = None
            self.unicode = unicode(markup)
            return

        u = None
        for proposedEncoding in overrideEncodings:
            u = self._convertFrom(proposedEncoding)
            if u: break
        if not u:
            for proposedEncoding in (documentEncoding, sniffedEncoding):
                u = self._convertFrom(proposedEncoding)
                if u: break

        # If no luck and we have auto-detection library, try that:
        if not u and chardet and not isinstance(self.markup, unicode):
            u = self._convertFrom(chardet.detect(self.markup)['encoding'])

        # As a last resort, try utf-8 and windows-1252:
        if not u:
            for proposed_encoding in ("utf-8", "windows-1252"):
                u = self._convertFrom(proposed_encoding)
                if u: break

        self.unicode = u
        if not u: self.originalEncoding = None

    def _subMSChar(self, orig):
        """Changes a MS smart quote character to an XML or HTML
        entity."""
        sub = self.MS_CHARS.get(orig)
        if isinstance(sub, tuple):
            if self.smartQuotesTo == 'xml':
                sub = '&#x%s;' % sub[1]
            else:
                sub = '&%s;' % sub[0]
        return sub

    def _convertFrom(self, proposed):
        proposed = self.find_codec(proposed)
        if not proposed or proposed in self.triedEncodings:
            return None
        self.triedEncodings.append(proposed)
        markup = self.markup

        # Convert smart quotes to HTML if coming from an encoding
        # that might have them.
        if self.smartQuotesTo and proposed.lower() in("windows-1252",
                                                      "iso-8859-1",
                                                      "iso-8859-2"):
            markup = re.compile("([\x80-\x9f])").sub \
                     (lambda(x): self._subMSChar(x.group(1)),
                      markup)

        try:
            # print "Trying to convert document to %s" % proposed
            u = self._toUnicode(markup, proposed)
            self.markup = u
            self.originalEncoding = proposed
        except Exception, e:
            # print "That didn't work!"
            # print e
            return None
        #print "Correct encoding: %s" % proposed
        return self.markup

    def _toUnicode(self, data, encoding):
        '''Given a string and its encoding, decodes the string into Unicode.
        %encoding is a string recognized by encodings.aliases'''

        # strip Byte Order Mark (if present)
        if (len(data) >= 4) and (data[:2] == '\xfe\xff') \
               and (data[2:4] != '\x00\x00'):
            encoding = 'utf-16be'
            data = data[2:]
        elif (len(data) >= 4) and (data[:2] == '\xff\xfe') \
                 and (data[2:4] != '\x00\x00'):
            encoding = 'utf-16le'
            data = data[2:]
        elif data[:3] == '\xef\xbb\xbf':
            encoding = 'utf-8'
            data = data[3:]
        elif data[:4] == '\x00\x00\xfe\xff':
            encoding = 'utf-32be'
            data = data[4:]
        elif data[:4] == '\xff\xfe\x00\x00':
            encoding = 'utf-32le'
            data = data[4:]
        newdata = unicode(data, encoding)
        return newdata

    def _detectEncoding(self, xml_data, isHTML=False):
        """Given a document, tries to detect its XML encoding."""
        xml_encoding = sniffed_xml_encoding = None
        try:
            if xml_data[:4] == '\x4c\x6f\xa7\x94':
                # EBCDIC
                xml_data = self._ebcdic_to_ascii(xml_data)
            elif xml_data[:4] == '\x00\x3c\x00\x3f':
                # UTF-16BE
                sniffed_xml_encoding = 'utf-16be'
                xml_data = unicode(xml_data, 'utf-16be').encode('utf-8')
            elif (len(xml_data) >= 4) and (xml_data[:2] == '\xfe\xff') \
                     and (xml_data[2:4] != '\x00\x00'):
                # UTF-16BE with BOM
                sniffed_xml_encoding = 'utf-16be'
                xml_data = unicode(xml_data[2:], 'utf-16be').encode('utf-8')
            elif xml_data[:4] == '\x3c\x00\x3f\x00':
                # UTF-16LE
                sniffed_xml_encoding = 'utf-16le'
                xml_data = unicode(xml_data, 'utf-16le').encode('utf-8')
            elif (len(xml_data) >= 4) and (xml_data[:2] == '\xff\xfe') and \
                     (xml_data[2:4] != '\x00\x00'):
                # UTF-16LE with BOM
                sniffed_xml_encoding = 'utf-16le'
                xml_data = unicode(xml_data[2:], 'utf-16le').encode('utf-8')
            elif xml_data[:4] == '\x00\x00\x00\x3c':
                # UTF-32BE
                sniffed_xml_encoding = 'utf-32be'
                xml_data = unicode(xml_data, 'utf-32be').encode('utf-8')
            elif xml_data[:4] == '\x3c\x00\x00\x00':
                # UTF-32LE
                sniffed_xml_encoding = 'utf-32le'
                xml_data = unicode(xml_data, 'utf-32le').encode('utf-8')
            elif xml_data[:4] == '\x00\x00\xfe\xff':
                # UTF-32BE with BOM
                sniffed_xml_encoding = 'utf-32be'
                xml_data = unicode(xml_data[4:], 'utf-32be').encode('utf-8')
            elif xml_data[:4] == '\xff\xfe\x00\x00':
                # UTF-32LE with BOM
                sniffed_xml_encoding = 'utf-32le'
                xml_data = unicode(xml_data[4:], 'utf-32le').encode('utf-8')
            elif xml_data[:3] == '\xef\xbb\xbf':
                # UTF-8 with BOM
                sniffed_xml_encoding = 'utf-8'
                xml_data = unicode(xml_data[3:], 'utf-8').encode('utf-8')
            else:
                sniffed_xml_encoding = 'ascii'
                pass
        except:
            xml_encoding_match = None
        xml_encoding_match = re.compile(
            '^<\?.*encoding=[\'"](.*?)[\'"].*\?>').match(xml_data)
        if not xml_encoding_match and isHTML:
            regexp = re.compile('<\s*meta[^>]+charset=([^>]*?)[;\'">]', re.I)
            xml_encoding_match = regexp.search(xml_data)
        if xml_encoding_match is not None:
            xml_encoding = xml_encoding_match.groups()[0].lower()
            if isHTML:
                self.declaredHTMLEncoding = xml_encoding
            if sniffed_xml_encoding and \
               (xml_encoding in ('iso-10646-ucs-2', 'ucs-2', 'csunicode',
                                 'iso-10646-ucs-4', 'ucs-4', 'csucs4',
                                 'utf-16', 'utf-32', 'utf_16', 'utf_32',
                                 'utf16', 'u16')):
                xml_encoding = sniffed_xml_encoding
        return xml_data, xml_encoding, sniffed_xml_encoding


    def find_codec(self, charset):
        return self._codec(self.CHARSET_ALIASES.get(charset, charset)) \
               or (charset and self._codec(charset.replace("-", ""))) \
               or (charset and self._codec(charset.replace("-", "_"))) \
               or charset

    def _codec(self, charset):
        if not charset: return charset
        codec = None
        try:
            codecs.lookup(charset)
            codec = charset
        except (LookupError, ValueError):
            pass
        return codec

    EBCDIC_TO_ASCII_MAP = None
    def _ebcdic_to_ascii(self, s):
        c = self.__class__
        if not c.EBCDIC_TO_ASCII_MAP:
            emap = (0,1,2,3,156,9,134,127,151,141,142,11,12,13,14,15,
                    16,17,18,19,157,133,8,135,24,25,146,143,28,29,30,31,
                    128,129,130,131,132,10,23,27,136,137,138,139,140,5,6,7,
                    144,145,22,147,148,149,150,4,152,153,154,155,20,21,158,26,
                    32,160,161,162,163,164,165,166,167,168,91,46,60,40,43,33,
                    38,169,170,171,172,173,174,175,176,177,93,36,42,41,59,94,
                    45,47,178,179,180,181,182,183,184,185,124,44,37,95,62,63,
                    186,187,188,189,190,191,192,193,194,96,58,35,64,39,61,34,
                    195,97,98,99,100,101,102,103,104,105,196,197,198,199,200,
                    201,202,106,107,108,109,110,111,112,113,114,203,204,205,
                    206,207,208,209,126,115,116,117,118,119,120,121,122,210,
                    211,212,213,214,215,216,217,218,219,220,221,222,223,224,
                    225,226,227,228,229,230,231,123,65,66,67,68,69,70,71,72,
                    73,232,233,234,235,236,237,125,74,75,76,77,78,79,80,81,
                    82,238,239,240,241,242,243,92,159,83,84,85,86,87,88,89,
                    90,244,245,246,247,248,249,48,49,50,51,52,53,54,55,56,57,
                    250,251,252,253,254,255)
            import string
            c.EBCDIC_TO_ASCII_MAP = string.maketrans( \
            ''.join(map(chr, range(256))), ''.join(map(chr, emap)))
        return s.translate(c.EBCDIC_TO_ASCII_MAP)

    MS_CHARS = { '\x80' : ('euro', '20AC'),
                 '\x81' : ' ',
                 '\x82' : ('sbquo', '201A'),
                 '\x83' : ('fnof', '192'),
                 '\x84' : ('bdquo', '201E'),
                 '\x85' : ('hellip', '2026'),
                 '\x86' : ('dagger', '2020'),
                 '\x87' : ('Dagger', '2021'),
                 '\x88' : ('circ', '2C6'),
                 '\x89' : ('permil', '2030'),
                 '\x8A' : ('Scaron', '160'),
                 '\x8B' : ('lsaquo', '2039'),
                 '\x8C' : ('OElig', '152'),
                 '\x8D' : '?',
                 '\x8E' : ('#x17D', '17D'),
                 '\x8F' : '?',
                 '\x90' : '?',
                 '\x91' : ('lsquo', '2018'),
                 '\x92' : ('rsquo', '2019'),
                 '\x93' : ('ldquo', '201C'),
                 '\x94' : ('rdquo', '201D'),
                 '\x95' : ('bull', '2022'),
                 '\x96' : ('ndash', '2013'),
                 '\x97' : ('mdash', '2014'),
                 '\x98' : ('tilde', '2DC'),
                 '\x99' : ('trade', '2122'),
                 '\x9a' : ('scaron', '161'),
                 '\x9b' : ('rsaquo', '203A'),
                 '\x9c' : ('oelig', '153'),
                 '\x9d' : '?',
                 '\x9e' : ('#x17E', '17E'),
                 '\x9f' : ('Yuml', ''),}

#######################################################################


#By default, act as an HTML pretty-printer.
if __name__ == '__main__':
    import sys
    soup = BeautifulSoup(sys.stdin)
    print soup.prettify()

########NEW FILE########
__FILENAME__ = compat
"""Python 3 compatibility shims
"""
import sys
if sys.version_info[0] < 3:
    PY3 = False
    def b(s):
        return s
    def u(s):
        return unicode(s, 'unicode_escape')
    import cStringIO as StringIO
    StringIO = BytesIO = StringIO.StringIO
    text_type = unicode
    binary_type = str
    string_types = (basestring,)
    integer_types = (int, long)
    unichr = unichr
    reload_module = reload
    def fromhex(s):
        return s.decode('hex')

else:
    PY3 = True
    from imp import reload as reload_module
    import codecs
    def b(s):
        return codecs.latin_1_encode(s)[0]
    def u(s):
        return s
    import io
    StringIO = io.StringIO
    BytesIO = io.BytesIO
    text_type = str
    binary_type = bytes
    string_types = (str,)
    integer_types = (int,)

    def unichr(s):
        return u(chr(s))

    def fromhex(s):
        return bytes.fromhex(s)

long_type = integer_types[-1]

########NEW FILE########
__FILENAME__ = decoder
"""Implementation of JSONDecoder
"""
from __future__ import absolute_import
import re
import sys
import struct
from .compat import fromhex, b, u, text_type, binary_type, PY3, unichr
from .scanner import make_scanner, JSONDecodeError

def _import_c_scanstring():
    try:
        from ._speedups import scanstring
        return scanstring
    except ImportError:
        return None
c_scanstring = _import_c_scanstring()

# NOTE (3.1.0): JSONDecodeError may still be imported from this module for
# compatibility, but it was never in the __all__
__all__ = ['JSONDecoder']

FLAGS = re.VERBOSE | re.MULTILINE | re.DOTALL

def _floatconstants():
    _BYTES = fromhex('7FF80000000000007FF0000000000000')
    # The struct module in Python 2.4 would get frexp() out of range here
    # when an endian is specified in the format string. Fixed in Python 2.5+
    if sys.byteorder != 'big':
        _BYTES = _BYTES[:8][::-1] + _BYTES[8:][::-1]
    nan, inf = struct.unpack('dd', _BYTES)
    return nan, inf, -inf

NaN, PosInf, NegInf = _floatconstants()

_CONSTANTS = {
    '-Infinity': NegInf,
    'Infinity': PosInf,
    'NaN': NaN,
}

STRINGCHUNK = re.compile(r'(.*?)(["\\\x00-\x1f])', FLAGS)
BACKSLASH = {
    '"': u('"'), '\\': u('\u005c'), '/': u('/'),
    'b': u('\b'), 'f': u('\f'), 'n': u('\n'), 'r': u('\r'), 't': u('\t'),
}

DEFAULT_ENCODING = "utf-8"

def py_scanstring(s, end, encoding=None, strict=True,
        _b=BACKSLASH, _m=STRINGCHUNK.match, _join=u('').join,
        _PY3=PY3, _maxunicode=sys.maxunicode):
    """Scan the string s for a JSON string. End is the index of the
    character in s after the quote that started the JSON string.
    Unescapes all valid JSON string escape sequences and raises ValueError
    on attempt to decode an invalid string. If strict is False then literal
    control characters are allowed in the string.

    Returns a tuple of the decoded string and the index of the character in s
    after the end quote."""
    if encoding is None:
        encoding = DEFAULT_ENCODING
    chunks = []
    _append = chunks.append
    begin = end - 1
    while 1:
        chunk = _m(s, end)
        if chunk is None:
            raise JSONDecodeError(
                "Unterminated string starting at", s, begin)
        end = chunk.end()
        content, terminator = chunk.groups()
        # Content is contains zero or more unescaped string characters
        if content:
            if not _PY3 and not isinstance(content, text_type):
                content = text_type(content, encoding)
            _append(content)
        # Terminator is the end of string, a literal control character,
        # or a backslash denoting that an escape sequence follows
        if terminator == '"':
            break
        elif terminator != '\\':
            if strict:
                msg = "Invalid control character %r at"
                raise JSONDecodeError(msg, s, end)
            else:
                _append(terminator)
                continue
        try:
            esc = s[end]
        except IndexError:
            raise JSONDecodeError(
                "Unterminated string starting at", s, begin)
        # If not a unicode escape sequence, must be in the lookup table
        if esc != 'u':
            try:
                char = _b[esc]
            except KeyError:
                msg = "Invalid \\X escape sequence %r"
                raise JSONDecodeError(msg, s, end)
            end += 1
        else:
            # Unicode escape sequence
            msg = "Invalid \\uXXXX escape sequence"
            esc = s[end + 1:end + 5]
            escX = esc[1:2]
            if len(esc) != 4 or escX == 'x' or escX == 'X':
                raise JSONDecodeError(msg, s, end - 1)
            try:
                uni = int(esc, 16)
            except ValueError:
                raise JSONDecodeError(msg, s, end - 1)
            end += 5
            # Check for surrogate pair on UCS-4 systems
            # Note that this will join high/low surrogate pairs
            # but will also pass unpaired surrogates through
            if (_maxunicode > 65535 and
                uni & 0xfc00 == 0xd800 and
                s[end:end + 2] == '\\u'):
                esc2 = s[end + 2:end + 6]
                escX = esc2[1:2]
                if len(esc2) == 4 and not (escX == 'x' or escX == 'X'):
                    try:
                        uni2 = int(esc2, 16)
                    except ValueError:
                        raise JSONDecodeError(msg, s, end)
                    if uni2 & 0xfc00 == 0xdc00:
                        uni = 0x10000 + (((uni - 0xd800) << 10) |
                                         (uni2 - 0xdc00))
                        end += 6
            char = unichr(uni)
        # Append the unescaped character
        _append(char)
    return _join(chunks), end


# Use speedup if available
scanstring = c_scanstring or py_scanstring

WHITESPACE = re.compile(r'[ \t\n\r]*', FLAGS)
WHITESPACE_STR = ' \t\n\r'

def JSONObject(state, encoding, strict, scan_once, object_hook,
        object_pairs_hook, memo=None,
        _w=WHITESPACE.match, _ws=WHITESPACE_STR):
    (s, end) = state
    # Backwards compatibility
    if memo is None:
        memo = {}
    memo_get = memo.setdefault
    pairs = []
    # Use a slice to prevent IndexError from being raised, the following
    # check will raise a more specific ValueError if the string is empty
    nextchar = s[end:end + 1]
    # Normally we expect nextchar == '"'
    if nextchar != '"':
        if nextchar in _ws:
            end = _w(s, end).end()
            nextchar = s[end:end + 1]
        # Trivial empty object
        if nextchar == '}':
            if object_pairs_hook is not None:
                result = object_pairs_hook(pairs)
                return result, end + 1
            pairs = {}
            if object_hook is not None:
                pairs = object_hook(pairs)
            return pairs, end + 1
        elif nextchar != '"':
            raise JSONDecodeError(
                "Expecting property name enclosed in double quotes",
                s, end)
    end += 1
    while True:
        key, end = scanstring(s, end, encoding, strict)
        key = memo_get(key, key)

        # To skip some function call overhead we optimize the fast paths where
        # the JSON key separator is ": " or just ":".
        if s[end:end + 1] != ':':
            end = _w(s, end).end()
            if s[end:end + 1] != ':':
                raise JSONDecodeError("Expecting ':' delimiter", s, end)

        end += 1

        try:
            if s[end] in _ws:
                end += 1
                if s[end] in _ws:
                    end = _w(s, end + 1).end()
        except IndexError:
            pass

        value, end = scan_once(s, end)
        pairs.append((key, value))

        try:
            nextchar = s[end]
            if nextchar in _ws:
                end = _w(s, end + 1).end()
                nextchar = s[end]
        except IndexError:
            nextchar = ''
        end += 1

        if nextchar == '}':
            break
        elif nextchar != ',':
            raise JSONDecodeError("Expecting ',' delimiter or '}'", s, end - 1)

        try:
            nextchar = s[end]
            if nextchar in _ws:
                end += 1
                nextchar = s[end]
                if nextchar in _ws:
                    end = _w(s, end + 1).end()
                    nextchar = s[end]
        except IndexError:
            nextchar = ''

        end += 1
        if nextchar != '"':
            raise JSONDecodeError(
                "Expecting property name enclosed in double quotes",
                s, end - 1)

    if object_pairs_hook is not None:
        result = object_pairs_hook(pairs)
        return result, end
    pairs = dict(pairs)
    if object_hook is not None:
        pairs = object_hook(pairs)
    return pairs, end

def JSONArray(state, scan_once, _w=WHITESPACE.match, _ws=WHITESPACE_STR):
    (s, end) = state
    values = []
    nextchar = s[end:end + 1]
    if nextchar in _ws:
        end = _w(s, end + 1).end()
        nextchar = s[end:end + 1]
    # Look-ahead for trivial empty array
    if nextchar == ']':
        return values, end + 1
    elif nextchar == '':
        raise JSONDecodeError("Expecting value or ']'", s, end)
    _append = values.append
    while True:
        value, end = scan_once(s, end)
        _append(value)
        nextchar = s[end:end + 1]
        if nextchar in _ws:
            end = _w(s, end + 1).end()
            nextchar = s[end:end + 1]
        end += 1
        if nextchar == ']':
            break
        elif nextchar != ',':
            raise JSONDecodeError("Expecting ',' delimiter or ']'", s, end - 1)

        try:
            if s[end] in _ws:
                end += 1
                if s[end] in _ws:
                    end = _w(s, end + 1).end()
        except IndexError:
            pass

    return values, end

class JSONDecoder(object):
    """Simple JSON <http://json.org> decoder

    Performs the following translations in decoding by default:

    +---------------+-------------------+
    | JSON          | Python            |
    +===============+===================+
    | object        | dict              |
    +---------------+-------------------+
    | array         | list              |
    +---------------+-------------------+
    | string        | unicode           |
    +---------------+-------------------+
    | number (int)  | int, long         |
    +---------------+-------------------+
    | number (real) | float             |
    +---------------+-------------------+
    | true          | True              |
    +---------------+-------------------+
    | false         | False             |
    +---------------+-------------------+
    | null          | None              |
    +---------------+-------------------+

    It also understands ``NaN``, ``Infinity``, and ``-Infinity`` as
    their corresponding ``float`` values, which is outside the JSON spec.

    """

    def __init__(self, encoding=None, object_hook=None, parse_float=None,
            parse_int=None, parse_constant=None, strict=True,
            object_pairs_hook=None):
        """
        *encoding* determines the encoding used to interpret any
        :class:`str` objects decoded by this instance (``'utf-8'`` by
        default).  It has no effect when decoding :class:`unicode` objects.

        Note that currently only encodings that are a superset of ASCII work,
        strings of other encodings should be passed in as :class:`unicode`.

        *object_hook*, if specified, will be called with the result of every
        JSON object decoded and its return value will be used in place of the
        given :class:`dict`.  This can be used to provide custom
        deserializations (e.g. to support JSON-RPC class hinting).

        *object_pairs_hook* is an optional function that will be called with
        the result of any object literal decode with an ordered list of pairs.
        The return value of *object_pairs_hook* will be used instead of the
        :class:`dict`.  This feature can be used to implement custom decoders
        that rely on the order that the key and value pairs are decoded (for
        example, :func:`collections.OrderedDict` will remember the order of
        insertion). If *object_hook* is also defined, the *object_pairs_hook*
        takes priority.

        *parse_float*, if specified, will be called with the string of every
        JSON float to be decoded.  By default, this is equivalent to
        ``float(num_str)``. This can be used to use another datatype or parser
        for JSON floats (e.g. :class:`decimal.Decimal`).

        *parse_int*, if specified, will be called with the string of every
        JSON int to be decoded.  By default, this is equivalent to
        ``int(num_str)``.  This can be used to use another datatype or parser
        for JSON integers (e.g. :class:`float`).

        *parse_constant*, if specified, will be called with one of the
        following strings: ``'-Infinity'``, ``'Infinity'``, ``'NaN'``.  This
        can be used to raise an exception if invalid JSON numbers are
        encountered.

        *strict* controls the parser's behavior when it encounters an
        invalid control character in a string. The default setting of
        ``True`` means that unescaped control characters are parse errors, if
        ``False`` then control characters will be allowed in strings.

        """
        if encoding is None:
            encoding = DEFAULT_ENCODING
        self.encoding = encoding
        self.object_hook = object_hook
        self.object_pairs_hook = object_pairs_hook
        self.parse_float = parse_float or float
        self.parse_int = parse_int or int
        self.parse_constant = parse_constant or _CONSTANTS.__getitem__
        self.strict = strict
        self.parse_object = JSONObject
        self.parse_array = JSONArray
        self.parse_string = scanstring
        self.memo = {}
        self.scan_once = make_scanner(self)

    def decode(self, s, _w=WHITESPACE.match, _PY3=PY3):
        """Return the Python representation of ``s`` (a ``str`` or ``unicode``
        instance containing a JSON document)

        """
        if _PY3 and isinstance(s, binary_type):
            s = s.decode(self.encoding)
        obj, end = self.raw_decode(s)
        end = _w(s, end).end()
        if end != len(s):
            raise JSONDecodeError("Extra data", s, end, len(s))
        return obj

    def raw_decode(self, s, idx=0, _w=WHITESPACE.match, _PY3=PY3):
        """Decode a JSON document from ``s`` (a ``str`` or ``unicode``
        beginning with a JSON document) and return a 2-tuple of the Python
        representation and the index in ``s`` where the document ended.
        Optionally, ``idx`` can be used to specify an offset in ``s`` where
        the JSON document begins.

        This can be used to decode a JSON document from a string that may
        have extraneous data at the end.

        """
        if _PY3 and not isinstance(s, text_type):
            raise TypeError("Input string must be text, not bytes")
        return self.scan_once(s, idx=_w(s, idx).end())

########NEW FILE########
__FILENAME__ = encoder
"""Implementation of JSONEncoder
"""
from __future__ import absolute_import
import re
from operator import itemgetter
from decimal import Decimal
from .compat import u, unichr, binary_type, string_types, integer_types, PY3
def _import_speedups():
    try:
        from . import _speedups
        return _speedups.encode_basestring_ascii, _speedups.make_encoder
    except ImportError:
        return None, None
c_encode_basestring_ascii, c_make_encoder = _import_speedups()

from simplejson.decoder import PosInf

#ESCAPE = re.compile(ur'[\x00-\x1f\\"\b\f\n\r\t\u2028\u2029]')
# This is required because u() will mangle the string and ur'' isn't valid
# python3 syntax
ESCAPE = re.compile(u'[\\x00-\\x1f\\\\"\\b\\f\\n\\r\\t\u2028\u2029]')
ESCAPE_ASCII = re.compile(r'([\\"]|[^\ -~])')
HAS_UTF8 = re.compile(r'[\x80-\xff]')
ESCAPE_DCT = {
    '\\': '\\\\',
    '"': '\\"',
    '\b': '\\b',
    '\f': '\\f',
    '\n': '\\n',
    '\r': '\\r',
    '\t': '\\t',
}
for i in range(0x20):
    #ESCAPE_DCT.setdefault(chr(i), '\\u{0:04x}'.format(i))
    ESCAPE_DCT.setdefault(chr(i), '\\u%04x' % (i,))
for i in [0x2028, 0x2029]:
    ESCAPE_DCT.setdefault(unichr(i), '\\u%04x' % (i,))

FLOAT_REPR = repr

def encode_basestring(s, _PY3=PY3, _q=u('"')):
    """Return a JSON representation of a Python string

    """
    if _PY3:
        if isinstance(s, binary_type):
            s = s.decode('utf-8')
    else:
        if isinstance(s, str) and HAS_UTF8.search(s) is not None:
            s = s.decode('utf-8')
    def replace(match):
        return ESCAPE_DCT[match.group(0)]
    return _q + ESCAPE.sub(replace, s) + _q


def py_encode_basestring_ascii(s, _PY3=PY3):
    """Return an ASCII-only JSON representation of a Python string

    """
    if _PY3:
        if isinstance(s, binary_type):
            s = s.decode('utf-8')
    else:
        if isinstance(s, str) and HAS_UTF8.search(s) is not None:
            s = s.decode('utf-8')
    def replace(match):
        s = match.group(0)
        try:
            return ESCAPE_DCT[s]
        except KeyError:
            n = ord(s)
            if n < 0x10000:
                #return '\\u{0:04x}'.format(n)
                return '\\u%04x' % (n,)
            else:
                # surrogate pair
                n -= 0x10000
                s1 = 0xd800 | ((n >> 10) & 0x3ff)
                s2 = 0xdc00 | (n & 0x3ff)
                #return '\\u{0:04x}\\u{1:04x}'.format(s1, s2)
                return '\\u%04x\\u%04x' % (s1, s2)
    return '"' + str(ESCAPE_ASCII.sub(replace, s)) + '"'


encode_basestring_ascii = (
    c_encode_basestring_ascii or py_encode_basestring_ascii)

class JSONEncoder(object):
    """Extensible JSON <http://json.org> encoder for Python data structures.

    Supports the following objects and types by default:

    +-------------------+---------------+
    | Python            | JSON          |
    +===================+===============+
    | dict, namedtuple  | object        |
    +-------------------+---------------+
    | list, tuple       | array         |
    +-------------------+---------------+
    | str, unicode      | string        |
    +-------------------+---------------+
    | int, long, float  | number        |
    +-------------------+---------------+
    | True              | true          |
    +-------------------+---------------+
    | False             | false         |
    +-------------------+---------------+
    | None              | null          |
    +-------------------+---------------+

    To extend this to recognize other objects, subclass and implement a
    ``.default()`` method with another method that returns a serializable
    object for ``o`` if possible, otherwise it should call the superclass
    implementation (to raise ``TypeError``).

    """
    item_separator = ', '
    key_separator = ': '
    def __init__(self, skipkeys=False, ensure_ascii=True,
            check_circular=True, allow_nan=True, sort_keys=False,
            indent=None, separators=None, encoding='utf-8', default=None,
            use_decimal=True, namedtuple_as_object=True,
            tuple_as_array=True, bigint_as_string=False,
            item_sort_key=None, for_json=False, ignore_nan=False):
        """Constructor for JSONEncoder, with sensible defaults.

        If skipkeys is false, then it is a TypeError to attempt
        encoding of keys that are not str, int, long, float or None.  If
        skipkeys is True, such items are simply skipped.

        If ensure_ascii is true, the output is guaranteed to be str
        objects with all incoming unicode characters escaped.  If
        ensure_ascii is false, the output will be unicode object.

        If check_circular is true, then lists, dicts, and custom encoded
        objects will be checked for circular references during encoding to
        prevent an infinite recursion (which would cause an OverflowError).
        Otherwise, no such check takes place.

        If allow_nan is true, then NaN, Infinity, and -Infinity will be
        encoded as such.  This behavior is not JSON specification compliant,
        but is consistent with most JavaScript based encoders and decoders.
        Otherwise, it will be a ValueError to encode such floats.

        If sort_keys is true, then the output of dictionaries will be
        sorted by key; this is useful for regression tests to ensure
        that JSON serializations can be compared on a day-to-day basis.

        If indent is a string, then JSON array elements and object members
        will be pretty-printed with a newline followed by that string repeated
        for each level of nesting. ``None`` (the default) selects the most compact
        representation without any newlines. For backwards compatibility with
        versions of simplejson earlier than 2.1.0, an integer is also accepted
        and is converted to a string with that many spaces.

        If specified, separators should be an (item_separator, key_separator)
        tuple.  The default is (', ', ': ') if *indent* is ``None`` and
        (',', ': ') otherwise.  To get the most compact JSON representation,
        you should specify (',', ':') to eliminate whitespace.

        If specified, default is a function that gets called for objects
        that can't otherwise be serialized.  It should return a JSON encodable
        version of the object or raise a ``TypeError``.

        If encoding is not None, then all input strings will be
        transformed into unicode using that encoding prior to JSON-encoding.
        The default is UTF-8.

        If use_decimal is true (not the default), ``decimal.Decimal`` will
        be supported directly by the encoder. For the inverse, decode JSON
        with ``parse_float=decimal.Decimal``.

        If namedtuple_as_object is true (the default), objects with
        ``_asdict()`` methods will be encoded as JSON objects.

        If tuple_as_array is true (the default), tuple (and subclasses) will
        be encoded as JSON arrays.

        If bigint_as_string is true (not the default), ints 2**53 and higher
        or lower than -2**53 will be encoded as strings. This is to avoid the
        rounding that happens in Javascript otherwise.

        If specified, item_sort_key is a callable used to sort the items in
        each dictionary. This is useful if you want to sort items other than
        in alphabetical order by key.

        If for_json is true (not the default), objects with a ``for_json()``
        method will use the return value of that method for encoding as JSON
        instead of the object.

        If *ignore_nan* is true (default: ``False``), then out of range
        :class:`float` values (``nan``, ``inf``, ``-inf``) will be serialized
        as ``null`` in compliance with the ECMA-262 specification. If true,
        this will override *allow_nan*.

        """

        self.skipkeys = skipkeys
        self.ensure_ascii = ensure_ascii
        self.check_circular = check_circular
        self.allow_nan = allow_nan
        self.sort_keys = sort_keys
        self.use_decimal = use_decimal
        self.namedtuple_as_object = namedtuple_as_object
        self.tuple_as_array = tuple_as_array
        self.bigint_as_string = bigint_as_string
        self.item_sort_key = item_sort_key
        self.for_json = for_json
        self.ignore_nan = ignore_nan
        if indent is not None and not isinstance(indent, string_types):
            indent = indent * ' '
        self.indent = indent
        if separators is not None:
            self.item_separator, self.key_separator = separators
        elif indent is not None:
            self.item_separator = ','
        if default is not None:
            self.default = default
        self.encoding = encoding

    def default(self, o):
        """Implement this method in a subclass such that it returns
        a serializable object for ``o``, or calls the base implementation
        (to raise a ``TypeError``).

        For example, to support arbitrary iterators, you could
        implement default like this::

            def default(self, o):
                try:
                    iterable = iter(o)
                except TypeError:
                    pass
                else:
                    return list(iterable)
                return JSONEncoder.default(self, o)

        """
        raise TypeError(repr(o) + " is not JSON serializable")

    def encode(self, o):
        """Return a JSON string representation of a Python data structure.

        >>> from simplejson import JSONEncoder
        >>> JSONEncoder().encode({"foo": ["bar", "baz"]})
        '{"foo": ["bar", "baz"]}'

        """
        # This is for extremely simple cases and benchmarks.
        if isinstance(o, binary_type):
            _encoding = self.encoding
            if (_encoding is not None and not (_encoding == 'utf-8')):
                o = o.decode(_encoding)
        if isinstance(o, string_types):
            if self.ensure_ascii:
                return encode_basestring_ascii(o)
            else:
                return encode_basestring(o)
        # This doesn't pass the iterator directly to ''.join() because the
        # exceptions aren't as detailed.  The list call should be roughly
        # equivalent to the PySequence_Fast that ''.join() would do.
        chunks = self.iterencode(o, _one_shot=True)
        if not isinstance(chunks, (list, tuple)):
            chunks = list(chunks)
        if self.ensure_ascii:
            return ''.join(chunks)
        else:
            return u''.join(chunks)

    def iterencode(self, o, _one_shot=False):
        """Encode the given object and yield each string
        representation as available.

        For example::

            for chunk in JSONEncoder().iterencode(bigobject):
                mysocket.write(chunk)

        """
        if self.check_circular:
            markers = {}
        else:
            markers = None
        if self.ensure_ascii:
            _encoder = encode_basestring_ascii
        else:
            _encoder = encode_basestring
        if self.encoding != 'utf-8':
            def _encoder(o, _orig_encoder=_encoder, _encoding=self.encoding):
                if isinstance(o, binary_type):
                    o = o.decode(_encoding)
                return _orig_encoder(o)

        def floatstr(o, allow_nan=self.allow_nan, ignore_nan=self.ignore_nan,
                _repr=FLOAT_REPR, _inf=PosInf, _neginf=-PosInf):
            # Check for specials. Note that this type of test is processor
            # and/or platform-specific, so do tests which don't depend on
            # the internals.

            if o != o:
                text = 'NaN'
            elif o == _inf:
                text = 'Infinity'
            elif o == _neginf:
                text = '-Infinity'
            else:
                return _repr(o)

            if ignore_nan:
                text = 'null'
            elif not allow_nan:
                raise ValueError(
                    "Out of range float values are not JSON compliant: " +
                    repr(o))

            return text


        key_memo = {}
        if (_one_shot and c_make_encoder is not None
                and self.indent is None):
            _iterencode = c_make_encoder(
                markers, self.default, _encoder, self.indent,
                self.key_separator, self.item_separator, self.sort_keys,
                self.skipkeys, self.allow_nan, key_memo, self.use_decimal,
                self.namedtuple_as_object, self.tuple_as_array,
                self.bigint_as_string, self.item_sort_key,
                self.encoding, self.for_json, self.ignore_nan,
                Decimal)
        else:
            _iterencode = _make_iterencode(
                markers, self.default, _encoder, self.indent, floatstr,
                self.key_separator, self.item_separator, self.sort_keys,
                self.skipkeys, _one_shot, self.use_decimal,
                self.namedtuple_as_object, self.tuple_as_array,
                self.bigint_as_string, self.item_sort_key,
                self.encoding, self.for_json,
                Decimal=Decimal)
        try:
            return _iterencode(o, 0)
        finally:
            key_memo.clear()


class JSONEncoderForHTML(JSONEncoder):
    """An encoder that produces JSON safe to embed in HTML.

    To embed JSON content in, say, a script tag on a web page, the
    characters &, < and > should be escaped. They cannot be escaped
    with the usual entities (e.g. &amp;) because they are not expanded
    within <script> tags.
    """

    def encode(self, o):
        # Override JSONEncoder.encode because it has hacks for
        # performance that make things more complicated.
        chunks = self.iterencode(o, True)
        if self.ensure_ascii:
            return ''.join(chunks)
        else:
            return u''.join(chunks)

    def iterencode(self, o, _one_shot=False):
        chunks = super(JSONEncoderForHTML, self).iterencode(o, _one_shot)
        for chunk in chunks:
            chunk = chunk.replace('&', '\\u0026')
            chunk = chunk.replace('<', '\\u003c')
            chunk = chunk.replace('>', '\\u003e')
            yield chunk


def _make_iterencode(markers, _default, _encoder, _indent, _floatstr,
        _key_separator, _item_separator, _sort_keys, _skipkeys, _one_shot,
        _use_decimal, _namedtuple_as_object, _tuple_as_array,
        _bigint_as_string, _item_sort_key, _encoding, _for_json,
        ## HACK: hand-optimized bytecode; turn globals into locals
        _PY3=PY3,
        ValueError=ValueError,
        string_types=string_types,
        Decimal=Decimal,
        dict=dict,
        float=float,
        id=id,
        integer_types=integer_types,
        isinstance=isinstance,
        list=list,
        str=str,
        tuple=tuple,
    ):
    if _item_sort_key and not callable(_item_sort_key):
        raise TypeError("item_sort_key must be None or callable")
    elif _sort_keys and not _item_sort_key:
        _item_sort_key = itemgetter(0)

    def _iterencode_list(lst, _current_indent_level):
        if not lst:
            yield '[]'
            return
        if markers is not None:
            markerid = id(lst)
            if markerid in markers:
                raise ValueError("Circular reference detected")
            markers[markerid] = lst
        buf = '['
        if _indent is not None:
            _current_indent_level += 1
            newline_indent = '\n' + (_indent * _current_indent_level)
            separator = _item_separator + newline_indent
            buf += newline_indent
        else:
            newline_indent = None
            separator = _item_separator
        first = True
        for value in lst:
            if first:
                first = False
            else:
                buf = separator
            if (isinstance(value, string_types) or
                (_PY3 and isinstance(value, binary_type))):
                yield buf + _encoder(value)
            elif value is None:
                yield buf + 'null'
            elif value is True:
                yield buf + 'true'
            elif value is False:
                yield buf + 'false'
            elif isinstance(value, integer_types):
                yield ((buf + str(value))
                       if (not _bigint_as_string or
                           (-1 << 53) < value < (1 << 53))
                           else (buf + '"' + str(value) + '"'))
            elif isinstance(value, float):
                yield buf + _floatstr(value)
            elif _use_decimal and isinstance(value, Decimal):
                yield buf + str(value)
            else:
                yield buf
                for_json = _for_json and getattr(value, 'for_json', None)
                if for_json and callable(for_json):
                    chunks = _iterencode(for_json(), _current_indent_level)
                elif isinstance(value, list):
                    chunks = _iterencode_list(value, _current_indent_level)
                else:
                    _asdict = _namedtuple_as_object and getattr(value, '_asdict', None)
                    if _asdict and callable(_asdict):
                        chunks = _iterencode_dict(_asdict(),
                                                  _current_indent_level)
                    elif _tuple_as_array and isinstance(value, tuple):
                        chunks = _iterencode_list(value, _current_indent_level)
                    elif isinstance(value, dict):
                        chunks = _iterencode_dict(value, _current_indent_level)
                    else:
                        chunks = _iterencode(value, _current_indent_level)
                for chunk in chunks:
                    yield chunk
        if newline_indent is not None:
            _current_indent_level -= 1
            yield '\n' + (_indent * _current_indent_level)
        yield ']'
        if markers is not None:
            del markers[markerid]

    def _stringify_key(key):
        if isinstance(key, string_types): # pragma: no cover
            pass
        elif isinstance(key, binary_type):
            key = key.decode(_encoding)
        elif isinstance(key, float):
            key = _floatstr(key)
        elif key is True:
            key = 'true'
        elif key is False:
            key = 'false'
        elif key is None:
            key = 'null'
        elif isinstance(key, integer_types):
            key = str(key)
        elif _use_decimal and isinstance(key, Decimal):
            key = str(key)
        elif _skipkeys:
            key = None
        else:
            raise TypeError("key " + repr(key) + " is not a string")
        return key

    def _iterencode_dict(dct, _current_indent_level):
        if not dct:
            yield '{}'
            return
        if markers is not None:
            markerid = id(dct)
            if markerid in markers:
                raise ValueError("Circular reference detected")
            markers[markerid] = dct
        yield '{'
        if _indent is not None:
            _current_indent_level += 1
            newline_indent = '\n' + (_indent * _current_indent_level)
            item_separator = _item_separator + newline_indent
            yield newline_indent
        else:
            newline_indent = None
            item_separator = _item_separator
        first = True
        if _PY3:
            iteritems = dct.items()
        else:
            iteritems = dct.iteritems()
        if _item_sort_key:
            items = []
            for k, v in dct.items():
                if not isinstance(k, string_types):
                    k = _stringify_key(k)
                    if k is None:
                        continue
                items.append((k, v))
            items.sort(key=_item_sort_key)
        else:
            items = iteritems
        for key, value in items:
            if not (_item_sort_key or isinstance(key, string_types)):
                key = _stringify_key(key)
                if key is None:
                    # _skipkeys must be True
                    continue
            if first:
                first = False
            else:
                yield item_separator
            yield _encoder(key)
            yield _key_separator
            if (isinstance(value, string_types) or
                (_PY3 and isinstance(value, binary_type))):
                yield _encoder(value)
            elif value is None:
                yield 'null'
            elif value is True:
                yield 'true'
            elif value is False:
                yield 'false'
            elif isinstance(value, integer_types):
                yield (str(value)
                       if (not _bigint_as_string or
                           (-1 << 53) < value < (1 << 53))
                           else ('"' + str(value) + '"'))
            elif isinstance(value, float):
                yield _floatstr(value)
            elif _use_decimal and isinstance(value, Decimal):
                yield str(value)
            else:
                for_json = _for_json and getattr(value, 'for_json', None)
                if for_json and callable(for_json):
                    chunks = _iterencode(for_json(), _current_indent_level)
                elif isinstance(value, list):
                    chunks = _iterencode_list(value, _current_indent_level)
                else:
                    _asdict = _namedtuple_as_object and getattr(value, '_asdict', None)
                    if _asdict and callable(_asdict):
                        chunks = _iterencode_dict(_asdict(),
                                                  _current_indent_level)
                    elif _tuple_as_array and isinstance(value, tuple):
                        chunks = _iterencode_list(value, _current_indent_level)
                    elif isinstance(value, dict):
                        chunks = _iterencode_dict(value, _current_indent_level)
                    else:
                        chunks = _iterencode(value, _current_indent_level)
                for chunk in chunks:
                    yield chunk
        if newline_indent is not None:
            _current_indent_level -= 1
            yield '\n' + (_indent * _current_indent_level)
        yield '}'
        if markers is not None:
            del markers[markerid]

    def _iterencode(o, _current_indent_level):
        if (isinstance(o, string_types) or
            (_PY3 and isinstance(o, binary_type))):
            yield _encoder(o)
        elif o is None:
            yield 'null'
        elif o is True:
            yield 'true'
        elif o is False:
            yield 'false'
        elif isinstance(o, integer_types):
            yield (str(o)
                   if (not _bigint_as_string or
                       (-1 << 53) < o < (1 << 53))
                       else ('"' + str(o) + '"'))
        elif isinstance(o, float):
            yield _floatstr(o)
        else:
            for_json = _for_json and getattr(o, 'for_json', None)
            if for_json and callable(for_json):
                for chunk in _iterencode(for_json(), _current_indent_level):
                    yield chunk
            elif isinstance(o, list):
                for chunk in _iterencode_list(o, _current_indent_level):
                    yield chunk
            else:
                _asdict = _namedtuple_as_object and getattr(o, '_asdict', None)
                if _asdict and callable(_asdict):
                    for chunk in _iterencode_dict(_asdict(),
                            _current_indent_level):
                        yield chunk
                elif (_tuple_as_array and isinstance(o, tuple)):
                    for chunk in _iterencode_list(o, _current_indent_level):
                        yield chunk
                elif isinstance(o, dict):
                    for chunk in _iterencode_dict(o, _current_indent_level):
                        yield chunk
                elif _use_decimal and isinstance(o, Decimal):
                    yield str(o)
                else:
                    if markers is not None:
                        markerid = id(o)
                        if markerid in markers:
                            raise ValueError("Circular reference detected")
                        markers[markerid] = o
                    o = _default(o)
                    for chunk in _iterencode(o, _current_indent_level):
                        yield chunk
                    if markers is not None:
                        del markers[markerid]

    return _iterencode

########NEW FILE########
__FILENAME__ = ordered_dict
"""Drop-in replacement for collections.OrderedDict by Raymond Hettinger

http://code.activestate.com/recipes/576693/

"""
from UserDict import DictMixin

# Modified from original to support Python 2.4, see
# http://code.google.com/p/simplejson/issues/detail?id=53
try:
    all
except NameError:
    def all(seq):
        for elem in seq:
            if not elem:
                return False
        return True

class OrderedDict(dict, DictMixin):

    def __init__(self, *args, **kwds):
        if len(args) > 1:
            raise TypeError('expected at most 1 arguments, got %d' % len(args))
        try:
            self.__end
        except AttributeError:
            self.clear()
        self.update(*args, **kwds)

    def clear(self):
        self.__end = end = []
        end += [None, end, end]         # sentinel node for doubly linked list
        self.__map = {}                 # key --> [key, prev, next]
        dict.clear(self)

    def __setitem__(self, key, value):
        if key not in self:
            end = self.__end
            curr = end[1]
            curr[2] = end[1] = self.__map[key] = [key, curr, end]
        dict.__setitem__(self, key, value)

    def __delitem__(self, key):
        dict.__delitem__(self, key)
        key, prev, next = self.__map.pop(key)
        prev[2] = next
        next[1] = prev

    def __iter__(self):
        end = self.__end
        curr = end[2]
        while curr is not end:
            yield curr[0]
            curr = curr[2]

    def __reversed__(self):
        end = self.__end
        curr = end[1]
        while curr is not end:
            yield curr[0]
            curr = curr[1]

    def popitem(self, last=True):
        if not self:
            raise KeyError('dictionary is empty')
        # Modified from original to support Python 2.4, see
        # http://code.google.com/p/simplejson/issues/detail?id=53
        if last:
            key = reversed(self).next()
        else:
            key = iter(self).next()
        value = self.pop(key)
        return key, value

    def __reduce__(self):
        items = [[k, self[k]] for k in self]
        tmp = self.__map, self.__end
        del self.__map, self.__end
        inst_dict = vars(self).copy()
        self.__map, self.__end = tmp
        if inst_dict:
            return (self.__class__, (items,), inst_dict)
        return self.__class__, (items,)

    def keys(self):
        return list(self)

    setdefault = DictMixin.setdefault
    update = DictMixin.update
    pop = DictMixin.pop
    values = DictMixin.values
    items = DictMixin.items
    iterkeys = DictMixin.iterkeys
    itervalues = DictMixin.itervalues
    iteritems = DictMixin.iteritems

    def __repr__(self):
        if not self:
            return '%s()' % (self.__class__.__name__,)
        return '%s(%r)' % (self.__class__.__name__, self.items())

    def copy(self):
        return self.__class__(self)

    @classmethod
    def fromkeys(cls, iterable, value=None):
        d = cls()
        for key in iterable:
            d[key] = value
        return d

    def __eq__(self, other):
        if isinstance(other, OrderedDict):
            return len(self)==len(other) and \
                   all(p==q for p, q in  zip(self.items(), other.items()))
        return dict.__eq__(self, other)

    def __ne__(self, other):
        return not self == other

########NEW FILE########
__FILENAME__ = scanner
"""JSON token scanner
"""
import re
def _import_c_make_scanner():
    try:
        from simplejson._speedups import make_scanner
        return make_scanner
    except ImportError:
        return None
c_make_scanner = _import_c_make_scanner()

__all__ = ['make_scanner', 'JSONDecodeError']

NUMBER_RE = re.compile(
    r'(-?(?:0|[1-9]\d*))(\.\d+)?([eE][-+]?\d+)?',
    (re.VERBOSE | re.MULTILINE | re.DOTALL))

class JSONDecodeError(ValueError):
    """Subclass of ValueError with the following additional properties:

    msg: The unformatted error message
    doc: The JSON document being parsed
    pos: The start index of doc where parsing failed
    end: The end index of doc where parsing failed (may be None)
    lineno: The line corresponding to pos
    colno: The column corresponding to pos
    endlineno: The line corresponding to end (may be None)
    endcolno: The column corresponding to end (may be None)

    """
    # Note that this exception is used from _speedups
    def __init__(self, msg, doc, pos, end=None):
        ValueError.__init__(self, errmsg(msg, doc, pos, end=end))
        self.msg = msg
        self.doc = doc
        self.pos = pos
        self.end = end
        self.lineno, self.colno = linecol(doc, pos)
        if end is not None:
            self.endlineno, self.endcolno = linecol(doc, end)
        else:
            self.endlineno, self.endcolno = None, None


def linecol(doc, pos):
    lineno = doc.count('\n', 0, pos) + 1
    if lineno == 1:
        colno = pos + 1
    else:
        colno = pos - doc.rindex('\n', 0, pos)
    return lineno, colno


def errmsg(msg, doc, pos, end=None):
    lineno, colno = linecol(doc, pos)
    msg = msg.replace('%r', repr(doc[pos:pos + 1]))
    if end is None:
        fmt = '%s: line %d column %d (char %d)'
        return fmt % (msg, lineno, colno, pos)
    endlineno, endcolno = linecol(doc, end)
    fmt = '%s: line %d column %d - line %d column %d (char %d - %d)'
    return fmt % (msg, lineno, colno, endlineno, endcolno, pos, end)


def py_make_scanner(context):
    parse_object = context.parse_object
    parse_array = context.parse_array
    parse_string = context.parse_string
    match_number = NUMBER_RE.match
    encoding = context.encoding
    strict = context.strict
    parse_float = context.parse_float
    parse_int = context.parse_int
    parse_constant = context.parse_constant
    object_hook = context.object_hook
    object_pairs_hook = context.object_pairs_hook
    memo = context.memo

    def _scan_once(string, idx):
        errmsg = 'Expecting value'
        try:
            nextchar = string[idx]
        except IndexError:
            raise JSONDecodeError(errmsg, string, idx)

        if nextchar == '"':
            return parse_string(string, idx + 1, encoding, strict)
        elif nextchar == '{':
            return parse_object((string, idx + 1), encoding, strict,
                _scan_once, object_hook, object_pairs_hook, memo)
        elif nextchar == '[':
            return parse_array((string, idx + 1), _scan_once)
        elif nextchar == 'n' and string[idx:idx + 4] == 'null':
            return None, idx + 4
        elif nextchar == 't' and string[idx:idx + 4] == 'true':
            return True, idx + 4
        elif nextchar == 'f' and string[idx:idx + 5] == 'false':
            return False, idx + 5

        m = match_number(string, idx)
        if m is not None:
            integer, frac, exp = m.groups()
            if frac or exp:
                res = parse_float(integer + (frac or '') + (exp or ''))
            else:
                res = parse_int(integer)
            return res, m.end()
        elif nextchar == 'N' and string[idx:idx + 3] == 'NaN':
            return parse_constant('NaN'), idx + 3
        elif nextchar == 'I' and string[idx:idx + 8] == 'Infinity':
            return parse_constant('Infinity'), idx + 8
        elif nextchar == '-' and string[idx:idx + 9] == '-Infinity':
            return parse_constant('-Infinity'), idx + 9
        else:
            raise JSONDecodeError(errmsg, string, idx)

    def scan_once(string, idx):
        try:
            return _scan_once(string, idx)
        finally:
            memo.clear()

    return scan_once

make_scanner = c_make_scanner or py_make_scanner

########NEW FILE########
__FILENAME__ = tool
r"""Command-line tool to validate and pretty-print JSON

Usage::

    $ echo '{"json":"obj"}' | python -m simplejson.tool
    {
        "json": "obj"
    }
    $ echo '{ 1.2:3.4}' | python -m simplejson.tool
    Expecting property name: line 1 column 2 (char 2)

"""
from __future__ import with_statement
import sys
import simplejson as json

def main():
    if len(sys.argv) == 1:
        infile = sys.stdin
        outfile = sys.stdout
    elif len(sys.argv) == 2:
        infile = open(sys.argv[1], 'r')
        outfile = sys.stdout
    elif len(sys.argv) == 3:
        infile = open(sys.argv[1], 'r')
        outfile = open(sys.argv[2], 'w')
    else:
        raise SystemExit(sys.argv[0] + " [infile [outfile]]")
    with infile:
        try:
            obj = json.load(infile,
                            object_pairs_hook=json.OrderedDict,
                            use_decimal=True)
        except ValueError:
            raise SystemExit(sys.exc_info()[1])
    with outfile:
        json.dump(obj, outfile, sort_keys=True, indent='    ', use_decimal=True)
        outfile.write('\n')


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = default
#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#     Copyright (C) 2012 Team-XBMC
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#
#    This script is based on script.randomitems & script.wacthlist
#    Thanks to their original authors

import os
import sys
import xbmc
import xbmcgui
import xbmcaddon
import subprocess

script_xbmc_starts = ''
script_player_starts = ''
script_player_stops = ''
script_player_pauses = ''
script_player_resumes = ''
script_screensaver_starts = ''
script_screensaver_stops = ''

__addon__        = xbmcaddon.Addon()
__addonversion__ = __addon__.getAddonInfo('version')
__addonid__      = __addon__.getAddonInfo('id')
__addonname__    = __addon__.getAddonInfo('name')

def log(txt):
    message = '%s: %s' % (__addonname__, txt.encode('ascii', 'ignore'))
    xbmc.log(msg=message, level=xbmc.LOGDEBUG)

class Main:
  def __init__(self):
    self._init_vars()
    self._init_property()
    global script_xbmc_starts
    if script_xbmc_starts:
      log('Going to execute script = "' + script_xbmc_starts + '"')
      subprocess.Popen([script_xbmc_starts])
    self._daemon()

  def _init_vars(self):
    self.Player = MyPlayer()
    self.Monitor = MyMonitor(update_settings = self._init_property, player_status = self._player_status)

  def _init_property(self):
    log('Reading properties')
    global script_xbmc_starts
    global script_player_starts
    global script_player_stops
    global script_player_pauses
    global script_player_resumes
    global script_screensaver_starts
    global script_screensaver_stops
    script_xbmc_starts = xbmc.translatePath(__addon__.getSetting("xbmc_starts"))
    script_player_starts = xbmc.translatePath(__addon__.getSetting("player_starts"))
    script_player_stops = xbmc.translatePath(__addon__.getSetting("player_stops"))
    script_player_pauses = xbmc.translatePath(__addon__.getSetting("player_pauses"))
    script_player_resumes = xbmc.translatePath(__addon__.getSetting("player_resumes"))
    script_screensaver_starts = xbmc.translatePath(__addon__.getSetting("screensaver_starts"))
    script_screensaver_stops = xbmc.translatePath(__addon__.getSetting("screensaver_stops"))
    log('script xbmc starts = "' + script_xbmc_starts + '"')
    log('script player starts = "' + script_player_starts + '"')
    log('script player stops = "' + script_player_stops + '"')
    log('script player pauses = "' + script_player_pauses + '"')
    log('script player resumes = "' + script_player_resumes + '"')
    log('script screensaver starts = "' + script_screensaver_starts + '"')
    log('script screensaver stops = "' + script_screensaver_stops + '"')

  def _player_status(self):
    return self.Player.playing_status()

  def _daemon(self):
    while (not xbmc.abortRequested):
      # Do nothing
      xbmc.sleep(600)
    log('abort requested')


class MyMonitor(xbmc.Monitor):
  def __init__(self, *args, **kwargs):
    xbmc.Monitor.__init__(self)
    self.get_player_status = kwargs['player_status']
    self.update_settings = kwargs['update_settings']

  def onSettingsChanged(self):
    self.update_settings()

  def onScreensaverActivated(self):
    log('screensaver starts')
    global script_screensaver_starts
    if script_screensaver_starts:
      log('Going to execute script = "' + script_screensaver_starts + '"')
      subprocess.Popen([script_screensaver_starts,self.get_player_status()])

  def onScreensaverDeactivated(self):
    log('screensaver stops')
    global script_screensaver_stops
    if script_screensaver_stops:
      log('Going to execute script = "' + script_screensaver_stops + '"')
      subprocess.Popen([script_screensaver_stops])

class MyPlayer(xbmc.Player):
  def __init__(self):
    xbmc.Player.__init__(self)
    self.substrings = [ '-trailer', 'http://' ]

  def playing_status(self):
    if self.isPlaying():
      return 'status=playing' + ';' + self.playing_type()
    else:
      return 'status=stopped'

  def playing_type(self):
    type = 'unkown'
    if (self.isPlayingAudio()):
      type = "music"  
    else:
      if xbmc.getCondVisibility('VideoPlayer.Content(movies)'):
        filename = ''
        isMovie = True
        try:
          filename = self.getPlayingFile()
        except:
          pass
        if filename != '':
          for string in self.substrings:
            if string in filename:
              isMovie = False
              break
        if isMovie:
          type = "movie"
      elif xbmc.getCondVisibility('VideoPlayer.Content(episodes)'):
        # Check for tv show title and season to make sure it's really an episode
        if xbmc.getInfoLabel('VideoPlayer.Season') != "" and xbmc.getInfoLabel('VideoPlayer.TVShowTitle') != "":
           type = "episode"
    return 'type=' + type

  def onPlayBackStarted(self):
    log('player starts')
    global script_player_starts
    if script_player_starts:
      log('Going to execute script = "' + script_player_starts + '"')
      subprocess.Popen([script_player_starts,self.playing_type()])

  def onPlayBackEnded(self):
    self.onPlayBackStopped()

  def onPlayBackStopped(self):
    log('player stops')
    global script_player_stops
    if script_player_stops:
      log('Going to execute script = "' + script_player_stops + '"')
      subprocess.Popen([script_player_stops,self.playing_type()])

  def onPlayBackPaused(self):
    log('player pauses')
    global script_player_pauses
    if script_player_pauses:
      log('Going to execute script = "' + script_player_pauses + '"')
      subprocess.Popen([script_player_pauses,self.playing_type()])

  def onPlayBackResumed(self):
    log('player resumes')
    global script_player_resumes
    if script_player_resumes:
      log('Going to execute script = "' + script_player_resumes + '"')
      subprocess.Popen([script_player_resumes,self.playing_type()])

if (__name__ == "__main__"):
    log('script version %s started' % __addonversion__)
    Main()
    del MyPlayer
    del MyMonitor
    del Main
    log('script version %s stopped' % __addonversion__)

########NEW FILE########
__FILENAME__ = default
# -*- coding: utf-8 -*-

# *  This Program is free software; you can redistribute it and/or modify
# *  it under the terms of the GNU General Public License as published by
# *  the Free Software Foundation; either version 2, or (at your option)
# *  any later version.
# *
# *  This Program is distributed in the hope that it will be useful,
# *  but WITHOUT ANY WARRANTY; without even the implied warranty of
# *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# *  GNU General Public License for more details.
# *
# *  You should have received a copy of the GNU General Public License
# *  along with XBMC; see the file COPYING. If not, write to
# *  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
# *  http://www.gnu.org/copyleft/gpl.html


import os, sys, socket, unicodedata, urllib2, time, base64, gzip
from datetime import date
from StringIO import StringIO
import xbmc, xbmcgui, xbmcaddon, xbmcvfs
if sys.version_info < (2, 7):
    import simplejson
else:
    import json as simplejson

__addon__      = xbmcaddon.Addon()
__addonname__  = __addon__.getAddonInfo('name')
__addonid__    = __addon__.getAddonInfo('id')
__cwd__        = __addon__.getAddonInfo('path').decode("utf-8")
__version__    = __addon__.getAddonInfo('version')
__language__   = __addon__.getLocalizedString
__resource__   = xbmc.translatePath( os.path.join( __cwd__, 'resources', 'lib' ).encode("utf-8") ).decode("utf-8")

sys.path.append(__resource__)

from utilities import *
from wunderground import wundergroundapi

WUNDERGROUND_LOC = 'http://autocomplete.wunderground.com/aq?query=%s&format=JSON'
WEATHER_FEATURES = 'hourly/conditions/forecast10day/astronomy/almanac/alerts/satellite'
FORMAT           = 'json'
ENABLED          = __addon__.getSetting('Enabled')
DEBUG            = __addon__.getSetting('Debug')
XBMC_PYTHON      = xbmcaddon.Addon(id='xbmc.python').getAddonInfo('version')
WEATHER_ICON     = xbmc.translatePath('special://temp/weather/%s.png').decode("utf-8")
WEATHER_WINDOW   = xbmcgui.Window(12600)
LANGUAGE         = xbmc.getLanguage().lower()
SPEEDUNIT        = xbmc.getRegion('speedunit')
TEMPUNIT         = unicode(xbmc.getRegion('tempunit'),encoding='utf-8')
TIMEFORMAT       = xbmc.getRegion('meridiem')
DATEFORMAT       = xbmc.getRegion('dateshort')
MAXDAYS          = 6

socket.setdefaulttimeout(10)

def recode(alert): # workaround: wunderground provides a corrupt alerts message
    try:
        alert = alert.encode("latin-1").rstrip('&nbsp)').decode("utf-8")
    except:
        pass
    return alert

def log(txt):
    if DEBUG == 'true':
        if isinstance (txt,str):
            txt = txt.decode("utf-8")
        message = u'%s: %s' % (__addonid__, txt)
        xbmc.log(msg=message.encode("utf-8"), level=xbmc.LOGDEBUG)

def set_property(name, value):
    WEATHER_WINDOW.setProperty(name, value)

def refresh_locations():
    locations = 0
    for count in range(1, 6):
        loc_name = __addon__.getSetting('Location%s' % count)
        if loc_name != '':
            locations += 1
        else:
            __addon__.setSetting('Location%sid' % count, '')
        set_property('Location%s' % count, loc_name)
    set_property('Locations', str(locations))
    log('available locations: %s' % str(locations))

def find_location(loc):
    url = WUNDERGROUND_LOC % urllib2.quote(loc)
    try:
        req = urllib2.urlopen(url)
        response = req.read()
        req.close()
    except:
        response = ''
    return response

def location(string):
    locs   = []
    locids = []
    log('location: %s' % string)
    loc = unicodedata.normalize('NFKD', unicode(string, 'utf-8')).encode('ascii','ignore')
    log('searching for location: %s' % loc)
    query = find_location(loc)
    log('location data: %s' % query)
    data = parse_data(query)
    if data != '' and data.has_key('RESULTS'):
        for item in data['RESULTS']:
            location   = item['name']
            locationid = item['l'][3:]
            locs.append(location)
            locids.append(locationid)
    return locs, locids

def geoip():
    retry = 0
    while (retry < 6) and (not xbmc.abortRequested):
        query = wundergroundapi('geolookup', 'lang:EN', 'autoip', FORMAT)
        if query != '':
            retry = 6
        else:
            retry += 1
            xbmc.sleep(10000)
            log('geoip download failed')
    log('geoip data: %s' % query)
    data = parse_data(query)
    if data != '' and data.has_key('location'):
        location   = data['location']['city']
        locationid = data['location']['l'][3:]
        __addon__.setSetting('Location1', location)
        __addon__.setSetting('Location1id', locationid)
        log('geoip location: %s' % location)
    else:
        location = ''
        locationid = ''
    return location, locationid

def forecast(loc,locid):
    try:
        lang = LANG[LANGUAGE]
    except:
        lang = 'EN'
    opt = 'lang:' + lang
    log('weather location: %s' % locid)
    retry = 0
    while (retry < 6) and (not xbmc.abortRequested):
        query = wundergroundapi(WEATHER_FEATURES, opt, locid, FORMAT)
        if query != '':
            retry = 6
        else:
            retry += 1
            xbmc.sleep(10000)
            log('weather download failed')
    log('forecast data: %s' % query)
    data = parse_data(query)
    if data != '' and data.has_key('response') and not data['response'].has_key('error'):
        properties(data,loc,locid)
    else:
        clear()

def clear():
    set_property('Current.Condition'     , 'N/A')
    set_property('Current.Temperature'   , '0')
    set_property('Current.Wind'          , '0')
    set_property('Current.WindDirection' , 'N/A')
    set_property('Current.Humidity'      , '0')
    set_property('Current.FeelsLike'     , '0')
    set_property('Current.UVIndex'       , '0')
    set_property('Current.DewPoint'      , '0')
    set_property('Current.OutlookIcon'   , 'na.png')
    set_property('Current.FanartCode'    , 'na')
    for count in range (0, MAXDAYS+1):
        set_property('Day%i.Title'       % count, 'N/A')
        set_property('Day%i.HighTemp'    % count, '0')
        set_property('Day%i.LowTemp'     % count, '0')
        set_property('Day%i.Outlook'     % count, 'N/A')
        set_property('Day%i.OutlookIcon' % count, 'na.png')
        set_property('Day%i.FanartCode'  % count, 'na')

def parse_data(json):
    try:
        raw = json.replace('<br>',' ').replace('&auml;','ä') # wu api bugs
        reply = raw.replace('"-999%"','""').replace('"-9999.00"','""').replace('"-9998"','""').replace('"NA"','""') # wu will change these to null responses in the future
        data = simplejson.loads(reply)
    except:
        log('failed to parse weather data')
        data = ''
    return data

def properties(data,loc,locid):
# standard properties
    weathercode = WEATHER_CODES[data['current_observation']['icon_url'][31:-4]]
    set_property('Current.Location'      , loc)
    set_property('Current.Condition'     , data['current_observation']['weather'])
    set_property('Current.Temperature'   , str(data['current_observation']['temp_c']))
    set_property('Current.Wind'          , str(data['current_observation']['wind_kph']))
    set_property('Current.WindDirection' , data['current_observation']['wind_dir'])
    set_property('Current.Humidity'      , data['current_observation']['relative_humidity'].rstrip('%'))
    set_property('Current.FeelsLike'     , data['current_observation']['feelslike_c'])
    set_property('Current.UVIndex'       , data['current_observation']['UV'])
    set_property('Current.DewPoint'      , str(data['current_observation']['dewpoint_c']))
    set_property('Current.OutlookIcon'   , '%s.png' % weathercode) # xbmc translates it to Current.ConditionIcon
    set_property('Current.FanartCode'    , weathercode)
    for count, item in enumerate(data['forecast']['simpleforecast']['forecastday']):
        weathercode = WEATHER_CODES[item['icon_url'][31:-4]]
        set_property('Day%i.Title'       % count, item['date']['weekday'])
        set_property('Day%i.HighTemp'    % count, str(item['high']['celsius']))
        set_property('Day%i.LowTemp'     % count, str(item['low']['celsius']))
        set_property('Day%i.Outlook'     % count, item['conditions'])
        set_property('Day%i.OutlookIcon' % count, '%s.png' % weathercode)
        set_property('Day%i.FanartCode'  % count, weathercode)
        if count == MAXDAYS:
            break
# forecast properties
    set_property('Forecast.IsFetched'        , 'true')
    set_property('Forecast.City'             , data['current_observation']['display_location']['city'])
    set_property('Forecast.State'            , data['current_observation']['display_location']['state_name'])
    set_property('Forecast.Country'          , data['current_observation']['display_location']['country'])
    update = time.localtime(float(data['current_observation']['observation_epoch']))
    local = time.localtime(float(data['current_observation']['local_epoch']))
    if DATEFORMAT[1] == 'd':
        updatedate = WEEKDAY[update[6]] + ' ' + str(update[2]) + ' ' + MONTH[update[1]] + ' ' + str(update[0])
        localdate = WEEKDAY[local[6]] + ' ' + str(local[2]) + ' ' + MONTH[local[1]] + ' ' + str(local[0])
    elif DATEFORMAT[1] == 'm':
        updatedate = WEEKDAY[update[6]] + ' ' + MONTH[update[1]] + ' ' + str(update[2]) + ', ' + str(update[0])
        localdate = WEEKDAY[local[6]] + ' ' + str(local[2]) + ' ' + MONTH[local[1]] + ' ' + str(local[0])
    else:
        updatedate = WEEKDAY[update[6]] + ' ' + str(update[0]) + ' ' + MONTH[update[1]] + ' ' + str(update[2])
        localdate = WEEKDAY[local[6]] + ' ' + str(local[0]) + ' ' + MONTH[local[1]] + ' ' + str(local[2])
    if TIMEFORMAT != '/':
        updatetime = time.strftime('%I:%M%p', update)
        localtime = time.strftime('%I:%M%p', local)
    else:
        updatetime = time.strftime('%H:%M', update)
        localtime = time.strftime('%H:%M', local)
    set_property('Forecast.Updated'          , updatedate + ' - ' + updatetime)
# current properties
    set_property('Current.IsFetched'         , 'true')
    set_property('Current.LocalTime'         , localtime)
    set_property('Current.LocalDate'         , localdate)
    set_property('Current.WindDegree'        , str(data['current_observation']['wind_degrees']) + u'°')
    set_property('Current.SolarRadiation'    , str(data['current_observation']['solarradiation']))
    if 'F' in TEMPUNIT:
        set_property('Current.Pressure'      , data['current_observation']['pressure_in'] + ' inHg')
        set_property('Current.Precipitation' , data['current_observation']['precip_1hr_in'] + ' in')
        set_property('Current.HeatIndex'     , str(data['current_observation']['heat_index_f']) + TEMPUNIT)
        set_property('Current.WindChill'     , str(data['current_observation']['windchill_f']) + TEMPUNIT)
    else:
        set_property('Current.Pressure'      , data['current_observation']['pressure_mb'] + ' mb')
        set_property('Current.Precipitation' , data['current_observation']['precip_1hr_metric'] + ' mm')
        set_property('Current.HeatIndex'     , str(data['current_observation']['heat_index_c']) + TEMPUNIT)
        set_property('Current.WindChill'     , str(data['current_observation']['windchill_c']) + TEMPUNIT)
    if SPEEDUNIT == 'mph':
        set_property('Current.Visibility'    , data['current_observation']['visibility_mi'] + ' mi')
        set_property('Current.WindGust'      , str(data['current_observation']['wind_gust_mph']) + ' ' + SPEEDUNIT)
    else:
        set_property('Current.Visibility'    , data['current_observation']['visibility_km'] + ' km')
        set_property('Current.WindGust'      , str(data['current_observation']['wind_gust_kph']) + ' ' + SPEEDUNIT)
# today properties
    set_property('Today.IsFetched'                     , 'true')
    if TIMEFORMAT != '/':
        AM = unicode(TIMEFORMAT.split('/')[0],encoding='utf-8')
        PM = unicode(TIMEFORMAT.split('/')[1],encoding='utf-8')
        hour = int(data['moon_phase']['sunrise']['hour']) % 24
        isam = (hour >= 0) and (hour < 12)
        if isam:
            hour = ('12' if (hour == 0) else '%02d' % (hour))
            set_property('Today.Sunrise'               , hour.lstrip('0') + ':' + data['moon_phase']['sunrise']['minute'] + ' ' + AM)
        else:
            hour = ('12' if (hour == 12) else '%02d' % (hour-12))
            set_property('Today.Sunrise'               , hour.lstrip('0') + ':' + data['moon_phase']['sunrise']['minute'] + ' ' + PM)
        hour = int(data['moon_phase']['sunset']['hour']) % 24
        isam = (hour >= 0) and (hour < 12)
        if isam:
            hour = ('12' if (hour == 0) else '%02d' % (hour))
            set_property('Today.Sunset'               , hour.lstrip('0') + ':' + data['moon_phase']['sunset']['minute'] + ' ' + AM)
        else:
            hour = ('12' if (hour == 12) else '%02d' % (hour-12))
            set_property('Today.Sunset'               , hour.lstrip('0') + ':' + data['moon_phase']['sunset']['minute'] + ' ' + PM)
    else:
        set_property('Today.Sunrise'                   , data['moon_phase']['sunrise']['hour'] + ':' + data['moon_phase']['sunrise']['minute'])
        set_property('Today.Sunset'                    , data['moon_phase']['sunset']['hour'] + ':' + data['moon_phase']['sunset']['minute'])
    set_property('Today.moonphase'                     , MOONPHASE(int(data['moon_phase']['ageOfMoon']), int(data['moon_phase']['percentIlluminated'])))
    if 'F' in TEMPUNIT:
        set_property('Today.AvgHighTemperature'        , data['almanac']['temp_high']['normal']['F'] + TEMPUNIT)
        set_property('Today.AvgLowTemperature'         , data['almanac']['temp_low']['normal']['F'] + TEMPUNIT)
        try:
            set_property('Today.RecordHighTemperature' , data['almanac']['temp_high']['record']['F'] + TEMPUNIT)
            set_property('Today.RecordLowTemperature'  , data['almanac']['temp_low']['record']['F'] + TEMPUNIT)
        except:
            set_property('Today.RecordHighTemperature' , '')
            set_property('Today.RecordLowTemperature'  , '')
    else:
        set_property('Today.AvgHighTemperature'        , data['almanac']['temp_high']['normal']['C'] + TEMPUNIT)
        set_property('Today.AvgLowTemperature'         , data['almanac']['temp_low']['normal']['C'] + TEMPUNIT)
        try:
            set_property('Today.RecordHighTemperature' , data['almanac']['temp_high']['record']['C'] + TEMPUNIT)
            set_property('Today.RecordLowTemperature'  , data['almanac']['temp_low']['record']['C'] + TEMPUNIT)
        except:
            set_property('Today.RecordHighTemperature' , '')
            set_property('Today.RecordLowTemperature'  , '')
    try:
        set_property('Today.RecordHighYear'            , data['almanac']['temp_high']['recordyear'])
        set_property('Today.RecordLowYear'             , data['almanac']['temp_low']['recordyear'])
    except:
        set_property('Today.RecordHighYear'            , '')
        set_property('Today.RecordLowYear'             , '')
# daily properties
    set_property('Daily.IsFetched', 'true')
    for count, item in enumerate(data['forecast']['simpleforecast']['forecastday']):
        weathercode = WEATHER_CODES[item['icon_url'][31:-4]]
        set_property('Daily.%i.LongDay'              % (count+1), item['date']['weekday'])
        set_property('Daily.%i.ShortDay'             % (count+1), item['date']['weekday_short'])
        if DATEFORMAT[1] == 'd':
            set_property('Daily.%i.LongDate'         % (count+1), str(item['date']['day']) + ' ' + item['date']['monthname'])
            set_property('Daily.%i.ShortDate'        % (count+1), str(item['date']['day']) + ' ' + MONTH[item['date']['month']])
        else:
            set_property('Daily.%i.LongDate'         % (count+1), item['date']['monthname'] + ' ' + str(item['date']['day']))
            set_property('Daily.%i.ShortDate'        % (count+1), MONTH[item['date']['month']] + ' ' + str(item['date']['day']))
        set_property('Daily.%i.Outlook'              % (count+1), item['conditions'])
        set_property('Daily.%i.OutlookIcon'          % (count+1), WEATHER_ICON % weathercode)
        set_property('Daily.%i.FanartCode'           % (count+1), weathercode)
        if SPEEDUNIT == 'mph':
            set_property('Daily.%i.WindSpeed'        % (count+1), str(item['avewind']['mph']) + ' ' + SPEEDUNIT)
            set_property('Daily.%i.MaxWind'          % (count+1), str(item['maxwind']['mph']) + ' ' + SPEEDUNIT)
        elif SPEEDUNIT == 'Beaufort':
            set_property('Daily.%i.WindSpeed'        % (count+1), KPHTOBFT(item['avewind']['kph']))
            set_property('Daily.%i.MaxWind'          % (count+1), KPHTOBFT(item['maxwind']['kph']))
        else:
            set_property('Daily.%i.WindSpeed'        % (count+1), str(item['avewind']['kph']) + ' ' + SPEEDUNIT)
            set_property('Daily.%i.MaxWind'          % (count+1), str(item['maxwind']['kph']) + ' ' + SPEEDUNIT)
        set_property('Daily.%i.WindDirection'        % (count+1), item['avewind']['dir'])
        set_property('Daily.%i.ShortWindDirection'   % (count+1), item['avewind']['dir'])
        set_property('Daily.%i.WindDegree'           % (count+1), str(item['avewind']['degrees']) + u'°')
        set_property('Daily.%i.Humidity'             % (count+1), str(item['avehumidity']) + '%')
        set_property('Daily.%i.MinHumidity'          % (count+1), str(item['minhumidity']) + '%')
        set_property('Daily.%i.MaxHumidity'          % (count+1), str(item['maxhumidity']) + '%')
        if 'F' in TEMPUNIT:
            set_property('Daily.%i.HighTemperature'  % (count+1), str(item['high']['fahrenheit']) + TEMPUNIT)
            set_property('Daily.%i.LowTemperature'   % (count+1), str(item['low']['fahrenheit']) + TEMPUNIT)
            set_property('Daily.%i.LongOutlookDay'   % (count+1), data['forecast']['txt_forecast']['forecastday'][2*count]['fcttext'])
            set_property('Daily.%i.LongOutlookNight' % (count+1), data['forecast']['txt_forecast']['forecastday'][2*count+1]['fcttext'])
            set_property('Daily.%i.Precipitation'    % (count+1), str(item['qpf_day']['in']) + ' in')
            set_property('Daily.%i.Snow'             % (count+1), str(item['snow_day']['in']) + ' in')
        else:
            set_property('Daily.%i.HighTemperature'  % (count+1), str(item['high']['celsius']) + TEMPUNIT)
            set_property('Daily.%i.LowTemperature'   % (count+1), str(item['low']['celsius']) + TEMPUNIT)
            set_property('Daily.%i.LongOutlookDay'   % (count+1), data['forecast']['txt_forecast']['forecastday'][2*count]['fcttext_metric'])
            set_property('Daily.%i.LongOutlookNight' % (count+1), data['forecast']['txt_forecast']['forecastday'][2*count+1]['fcttext_metric'])
            set_property('Daily.%i.Precipitation'    % (count+1), str(item['qpf_day']['mm']) + ' mm')
            set_property('Daily.%i.Snow'             % (count+1), str(item['snow_day']['cm']) + ' mm')
        set_property('Daily.%i.ChancePrecipitation'  % (count+1), data['forecast']['txt_forecast']['forecastday'][2*count]['pop'] + '%')
# weekend properties
    set_property('Weekend.IsFetched', 'true')
    if __addon__.getSetting('Weekend') == '2':
        weekend = [4,5]
    elif __addon__.getSetting('Weekend') == '1':
        weekend = [5,6]
    else:
        weekend = [6,7]
    count = 0
    for item in data['forecast']['simpleforecast']['forecastday']:
        if date(item['date']['year'], item['date']['month'], item['date']['day']).isoweekday() in weekend:
            weathercode = WEATHER_CODES[item['icon_url'][31:-4]]
            set_property('Weekend.%i.LongDay'                  % (count+1), item['date']['weekday'])
            set_property('Weekend.%i.ShortDay'                 % (count+1), item['date']['weekday_short'])
            if DATEFORMAT[1] == 'd':
                set_property('Weekend.%i.LongDate'             % (count+1), str(item['date']['day']) + ' ' + item['date']['monthname'])
                set_property('Weekend.%i.ShortDate'            % (count+1), str(item['date']['day']) + ' ' + MONTH[item['date']['month']])
            else:
                set_property('Weekend.%i.LongDate'             % (count+1), item['date']['monthname'] + ' ' + str(item['date']['day']))
                set_property('Weekend.%i.ShortDate'            % (count+1), MONTH[item['date']['month']] + ' ' + str(item['date']['day']))
            set_property('Weekend.%i.Outlook'                  % (count+1), item['conditions'])
            set_property('Weekend.%i.OutlookIcon'              % (count+1), WEATHER_ICON % weathercode)
            set_property('Weekend.%i.FanartCode'               % (count+1), weathercode)
            if SPEEDUNIT == 'mph':
                set_property('Weekend.%i.WindSpeed'            % (count+1), str(item['avewind']['mph']) + ' ' + SPEEDUNIT)
                set_property('Weekend.%i.MaxWind'              % (count+1), str(item['maxwind']['mph']) + ' ' + SPEEDUNIT)
            elif SPEEDUNIT == 'Beaufort':
                set_property('Weekend.%i.WindSpeed'            % (count+1), KPHTOBFT(item['avewind']['kph']))
                set_property('Weekend.%i.MaxWind'              % (count+1), KPHTOBFT(item['maxwind']['kph']))
            else:
                set_property('Weekend.%i.WindSpeed'            % (count+1), str(item['avewind']['kph']) + ' ' + SPEEDUNIT)
                set_property('Weekend.%i.MaxWind'              % (count+1), str(item['maxwind']['kph']) + ' ' + SPEEDUNIT)
            set_property('Weekend.%i.WindDirection'            % (count+1), item['avewind']['dir'])
            set_property('Weekend.%i.ShortWindDirection'       % (count+1), item['avewind']['dir'])
            set_property('Weekend.%i.WindDegree'               % (count+1), str(item['avewind']['degrees']) + u'°')
            set_property('Weekend.%i.Humidity'                 % (count+1), str(item['avehumidity']) + '%')
            set_property('Weekend.%i.MinHumidity'              % (count+1), str(item['minhumidity']) + '%')
            set_property('Weekend.%i.MaxHumidity'              % (count+1), str(item['maxhumidity']) + '%')
            set_property('Weekend.%i.ChancePrecipitation'      % (count+1), data['forecast']['txt_forecast']['forecastday'][2*count]['pop'] + '%')
            if 'F' in TEMPUNIT:
                set_property('Weekend.%i.HighTemperature'      % (count+1), str(item['high']['fahrenheit']) + TEMPUNIT)
                set_property('Weekend.%i.LowTemperature'       % (count+1), str(item['low']['fahrenheit']) + TEMPUNIT)
                set_property('Weekend.%i.Precipitation'        % (count+1), str(item['qpf_day']['in']) + ' in')
                set_property('Weekend.%i.Snow'                 % (count+1), str(item['snow_day']['in']) + ' in')
                set_property('Weekend.%i.LongOutlookDay'       % (count+1), data['forecast']['txt_forecast']['forecastday'][2*count]['fcttext'])
                set_property('Weekend.%i.LongOutlookNight'     % (count+1), data['forecast']['txt_forecast']['forecastday'][2*count+1]['fcttext'])
            else:
                set_property('Weekend.%i.HighTemperature'      % (count+1), str(item['high']['celsius']) + TEMPUNIT)
                set_property('Weekend.%i.LowTemperature'       % (count+1), str(item['low']['celsius']) + TEMPUNIT)
                set_property('Weekend.%i.Precipitation'        % (count+1), str(item['qpf_day']['mm']) + ' mm')
                set_property('Weekend.%i.Snow'                 % (count+1), str(item['snow_day']['cm']) + ' mm')
                if data['current_observation']['display_location']['country'] == 'UK': # for the brits
                    dfcast_e = data['forecast']['txt_forecast']['forecastday'][2*count]['fcttext'].split('.')
                    dfcast_m = data['forecast']['txt_forecast']['forecastday'][2*count]['fcttext_metric'].split('.')
                    nfcast_e = data['forecast']['txt_forecast']['forecastday'][2*count+1]['fcttext'].split('.')
                    nfcast_m = data['forecast']['txt_forecast']['forecastday'][2*count+1]['fcttext_metric'].split('.')
                    for field in dfcast_e:
                        if field.endswith('mph'): # find windspeed in mph
                            wind = field
                            break
                    for field in dfcast_m:
                        if field.endswith('km/h'): # find windspeed in km/h
                            dfcast_m[dfcast_m.index(field)] = wind # replace windspeed in km/h with windspeed in mph
                            break
                    for field in nfcast_e:
                        if field.endswith('mph'): # find windspeed in mph
                            wind = field
                            break
                    for field in nfcast_m:
                        if field.endswith('km/h'): # find windspeed in km/h
                            nfcast_m[nfcast_m.index(field)] = wind # replace windspeed in km/h with windspeed in mph
                            break
                    set_property('Weekend.%i.LongOutlookDay'   % (count+1), '. '.join(dfcast_m))
                    set_property('Weekend.%i.LongOutlookNight' % (count+1), '. '.join(nfcast_m))
                else:
                    set_property('Weekend.%i.LongOutlookDay'   % (count+1), data['forecast']['txt_forecast']['forecastday'][2*count]['fcttext_metric'])
                    set_property('Weekend.%i.LongOutlookNight' % (count+1), data['forecast']['txt_forecast']['forecastday'][2*count+1]['fcttext_metric'])
            count += 1
            if count == 2:
                break
# 36 hour properties
    set_property('36Hour.IsFetched', 'true')
    for count, item in enumerate(data['forecast']['txt_forecast']['forecastday']):
        weathercode = WEATHER_CODES[item['icon_url'][31:-4]]
        if 'F' in TEMPUNIT:
            try:
                fcast = item['fcttext'].split('.')
                for line in fcast:
                    if line.endswith('F'):
                        set_property('36Hour.%i.TemperatureHeading' % (count+1), line.rsplit(' ',1)[0])
                        set_property('36Hour.%i.Temperature'        % (count+1), line.rsplit(' ',1)[1].rstrip('F').strip() + TEMPUNIT)
                        break
            except:
                set_property('36Hour.%i.TemperatureHeading'         % (count+1), '')
                set_property('36Hour.%i.Temperature'                % (count+1), '')
            set_property('36Hour.%i.Forecast'                       % (count+1), item['fcttext'])
        else:
            try:
                fcast = item['fcttext_metric'].split('.')
                for line in fcast:
                    if line.endswith('C'):
                        set_property('36Hour.%i.TemperatureHeading' % (count+1), line.rsplit(' ',1)[0])
                        set_property('36Hour.%i.Temperature'        % (count+1), line.rsplit(' ',1)[1].rstrip('C').strip() + TEMPUNIT)
                        break
            except:
                set_property('36Hour.%i.TemperatureHeading' % (count+1), '')
                set_property('36Hour.%i.Temperature'        % (count+1), '')
            if data['current_observation']['display_location']['country'] == 'UK': # for the brits
                fcast_e = item['fcttext'].split('.')
                for field in fcast_e:
                    if field.endswith('mph'): # find windspeed in mph
                        wind = field
                        break
                for field in fcast:
                    if field.endswith('km/h'): # find windspeed in km/h
                        fcast[fcast.index(field)] = wind # replace windspeed in km/h with windspeed in mph
                        break
                set_property('36Hour.%i.Forecast'                   % (count+1), '. '.join(fcast))
            else:
                set_property('36Hour.%i.Forecast'                   % (count+1), item['fcttext_metric'])
        set_property('36Hour.%i.Heading'                    % (count+1), item['title'])
        set_property('36Hour.%i.ChancePrecipitation'        % (count+1), item['pop']  + '%')
        set_property('36Hour.%i.OutlookIcon'                % (count+1), WEATHER_ICON % weathercode)
        set_property('36Hour.%i.FanartCode'                 % (count+1), weathercode)
        if count == 2:
            break
# hourly properties
    set_property('Hourly.IsFetched', 'true')
    for count, item in enumerate(data['hourly_forecast']):
        weathercode = WEATHER_CODES[item['icon_url'][31:-4]]
        if TIMEFORMAT != '/':
            set_property('Hourly.%i.Time'            % (count+1), item['FCTTIME']['civil'])
        else:
            set_property('Hourly.%i.Time'            % (count+1), item['FCTTIME']['hour_padded'] + ':' + item['FCTTIME']['min'])
        if DATEFORMAT[1] == 'd':
            set_property('Hourly.%i.ShortDate'       % (count+1), item['FCTTIME']['mday_padded'] + ' ' + item['FCTTIME']['month_name_abbrev'])
            set_property('Hourly.%i.LongDate'        % (count+1), item['FCTTIME']['mday_padded'] + ' ' + item['FCTTIME']['month_name'])
        else:
            set_property('Hourly.%i.ShortDate'       % (count+1), item['FCTTIME']['month_name_abbrev'] + ' ' + item['FCTTIME']['mday_padded'])
            set_property('Hourly.%i.LongDate'        % (count+1), item['FCTTIME']['month_name'] + ' ' + item['FCTTIME']['mday_padded'])
        if 'F' in TEMPUNIT:
            set_property('Hourly.%i.Temperature'     % (count+1), item['temp']['english'] + TEMPUNIT)
            set_property('Hourly.%i.DewPoint'        % (count+1), item['dewpoint']['english'] + TEMPUNIT)
            set_property('Hourly.%i.FeelsLike'       % (count+1), item['feelslike']['english'] + TEMPUNIT)
            set_property('Hourly.%i.Precipitation'   % (count+1), item['qpf']['english'] + ' in')
            set_property('Hourly.%i.Snow'            % (count+1), item['snow']['english'] + ' in')
            set_property('Hourly.%i.HeatIndex'       % (count+1), item['heatindex']['english'] + TEMPUNIT)
            set_property('Hourly.%i.WindChill'       % (count+1), item['windchill']['english'] + TEMPUNIT)
            set_property('Hourly.%i.Mslp'            % (count+1), item['mslp']['english'] + ' inHg')
        else:
            set_property('Hourly.%i.Temperature'     % (count+1), item['temp']['metric'] + TEMPUNIT)
            set_property('Hourly.%i.DewPoint'        % (count+1), item['dewpoint']['metric'] + TEMPUNIT)
            set_property('Hourly.%i.FeelsLike'       % (count+1), item['feelslike']['metric'] + TEMPUNIT)
            set_property('Hourly.%i.Precipitation'   % (count+1), item['qpf']['metric'] + ' mm')
            set_property('Hourly.%i.Snow'            % (count+1), item['snow']['metric'] + ' mm')
            set_property('Hourly.%i.HeatIndex'       % (count+1), item['heatindex']['metric'] + TEMPUNIT)
            set_property('Hourly.%i.WindChill'       % (count+1), item['windchill']['metric'] + TEMPUNIT)
            set_property('Hourly.%i.Mslp'            % (count+1), item['mslp']['metric'] + ' inHg')
        if SPEEDUNIT == 'mph':
            set_property('Hourly.%i.WindSpeed'       % (count+1), item['wspd']['english'] + ' ' + SPEEDUNIT)
        elif SPEEDUNIT == 'Beaufort':
            set_property('Hourly.%i.WindSpeed'       % (count+1), KPHTOBFT(int(item['wspd']['metric'])))
        else:
            set_property('Hourly.%i.WindSpeed'       % (count+1), item['wspd']['metric'] + ' ' + SPEEDUNIT)
        set_property('Hourly.%i.WindDirection'       % (count+1), item['wdir']['dir'])
        set_property('Hourly.%i.ShortWindDirection'  % (count+1), item['wdir']['dir'])
        set_property('Hourly.%i.WindDegree'          % (count+1), item['wdir']['degrees'] + u'°')
        set_property('Hourly.%i.Humidity'            % (count+1), item['humidity'] + '%')
        set_property('Hourly.%i.UVIndex'             % (count+1), item['uvi'])
        set_property('Hourly.%i.ChancePrecipitation' % (count+1), item['pop'] + '%')
        set_property('Hourly.%i.Outlook'             % (count+1), item['condition'])
        set_property('Hourly.%i.OutlookIcon'         % (count+1), WEATHER_ICON % weathercode)
        set_property('Hourly.%i.FanartCode'          % (count+1), weathercode)
# alert properties
    set_property('Alerts.IsFetched', 'true')
    if str(data['alerts']) != '[]':
        rss = ''
        alerts = ''
        for count, item in enumerate(data['alerts']):
            description = recode(item['description']) # workaround: wunderground provides a corrupt alerts message
            message = recode(item['message']) # workaround: wunderground provides a corrupt alerts message
            set_property('Alerts.%i.Description'     % (count+1), description)
            set_property('Alerts.%i.Message'         % (count+1), message)
            set_property('Alerts.%i.StartDate'       % (count+1), item['date'])
            set_property('Alerts.%i.EndDate'         % (count+1), item['expires'])
            set_property('Alerts.%i.Significance'    % (count+1), SEVERITY[item['significance']])
            rss    = rss + description.replace('\n','') + ' - '
            alerts = alerts + message + '[CR][CR]'
        set_property('Alerts.RSS'   , rss.rstrip(' - '))
        set_property('Alerts'       , alerts.rstrip('[CR][CR]'))
        set_property('Alerts.Count' , str(count+1))
    else:
        set_property('Alerts.RSS'   , '')
        set_property('Alerts'       , '')
        set_property('Alerts.Count' , '0')
# map properties
    set_property('Map.IsFetched', 'true')
    filelist = []
    locid = base64.b16encode(locid)
    addondir = os.path.join(__cwd__, 'resources', 'logo')
    mapdir = xbmc.translatePath('special://profile/addon_data/%s/map' % __addonid__)
    set_property('MapPath', addondir)
    if not xbmcvfs.exists(mapdir):
        xbmcvfs.mkdir(mapdir)
    dirs, filelist = xbmcvfs.listdir(mapdir)
    animate = __addon__.getSetting('Animate')
    for img in filelist:
        item = xbmc.translatePath('special://profile/addon_data/%s/map/%s' % (__addonid__,img)).decode("utf-8")
        if animate == 'true':
            if (time.time() - os.path.getmtime(item) > 14400) or (not locid in item):
                xbmcvfs.delete(item)
        else:
            xbmcvfs.delete(item)
    zoom = __addon__.getSetting('Zoom')
    if zoom == '10': # default setting does not return decimals, changed setting will
        zoom = '10.0'
    url = data['satellite']['image_url_ir4'].replace('width=300&height=300','width=640&height=360').replace('radius=75','radius=%i' % int(1000/int(zoom.rstrip('0').rstrip('.,'))))
    log('map url: %s' % url)
    try:
        req = urllib2.Request(url)
        req.add_header('Accept-encoding', 'gzip')
        response = urllib2.urlopen(req)
        if response.info().get('Content-Encoding') == 'gzip':
            buf = StringIO(response.read())
            compr = gzip.GzipFile(fileobj=buf)
            data = compr.read()
        else:
            data = response.read()
        response.close()
        log('satellite image downloaded')
    except:
        data = ''
        log('satellite image downloaded failed')
    if data != '':
        timestamp = time.strftime('%Y%m%d%H%M%S')
        mapfile = xbmc.translatePath('special://profile/addon_data/%s/map/%s-%s.png' % (__addonid__,locid,timestamp)).decode("utf-8")
        try:
            tmpmap = open(mapfile, 'wb')
            tmpmap.write(data)
            tmpmap.close()
            set_property('MapPath', mapdir)
        except:
            log('failed to save satellite image')

log('version %s started: %s' % (__version__, sys.argv))
log('lang: %s'    % LANGUAGE)
log('speed: %s'   % SPEEDUNIT)
log('temp: %s'    % TEMPUNIT[1])
log('time: %s'    % TIMEFORMAT)
log('date: %s'    % DATEFORMAT)

set_property('WeatherProvider', __addonname__)
set_property('WeatherProviderLogo', xbmc.translatePath(os.path.join(__cwd__, 'resources', 'banner.png')))

if sys.argv[1].startswith('Location'):
    keyboard = xbmc.Keyboard('', xbmc.getLocalizedString(14024), False)
    keyboard.doModal()
    if (keyboard.isConfirmed() and keyboard.getText() != ''):
        text = keyboard.getText()
        locations, locationids = location(text)
        dialog = xbmcgui.Dialog()
        if locations != []:
            selected = dialog.select(xbmc.getLocalizedString(396), locations)
            if selected != -1:
                __addon__.setSetting(sys.argv[1], locations[selected])
                __addon__.setSetting(sys.argv[1] + 'id', locationids[selected])
                log('selected location: %s' % locations[selected])
                log('selected location id: %s' % locationids[selected])
        else:
            dialog.ok(__addonname__, xbmc.getLocalizedString(284))
elif ENABLED == 'false':
    clear()
    log('you need to enable weather retrieval in the weather underground addon settings')
elif XBMC_PYTHON == '1.0' or XBMC_PYTHON == '2.0' or XBMC_PYTHON == '2.0.0':
    clear()
    log('older versions of XBMC are not supported by the weather underground addon')
else:
    location = __addon__.getSetting('Location%s' % sys.argv[1])
    locationid = __addon__.getSetting('Location%sid' % sys.argv[1])
    if (locationid == '') and (sys.argv[1] != '1'):
        location = __addon__.getSetting('Location1')
        locationid = __addon__.getSetting('Location1id')
        log('trying location 1 instead')
    if locationid == '':
        log('fallback to geoip')
        location, locationid = geoip()
    if not locationid == '':
        forecast(location, locationid)
    else:
        log('no location found')
        clear()
    refresh_locations()

log('finished')

########NEW FILE########
__FILENAME__ = utilities
# -*- coding: utf-8 -*-

import sys
import xbmc

__language__ = sys.modules[ "__main__" ].__language__

#http://www.wunderground.com/weather/api/d/docs?d=language-support
        # xbmc lang name         # wu code
LANG = { 'afrikaans'             : 'AF',
         'albanian'              : 'AL',
         'amharic'               : 'EN', # AM is n/a, use AR or EN? 
         'arabic'                : 'AR',
         'azerbaijani'           : 'AZ',
         'basque'                : 'EU',
         'belarusian'            : 'BY',
         'bosnian'               : 'CR', # BS is n/a, use CR or SR? 
         'bulgarian'             : 'BU',
         'burmese'               : 'MY',
         'catalan'               : 'CA',
         'chinese (simple)'      : 'CN',
         'chinese (traditional)' : 'TW',
         'croatian'              : 'CR',
         'czech'                 : 'CZ',
         'danish'                : 'DK',
         'dutch'                 : 'NL',
         'english'               : 'LI',
         'english (us)'          : 'EN',
         'esperanto'             : 'EO',
         'estonian'              : 'ET',
         'faroese'               : 'DK', # FO is n/a, use DK
         'finnish'               : 'FI',
         'french'                : 'FR',
         'galician'              : 'GZ',
         'german'                : 'DL',
         'greek'                 : 'GR',
         'hebrew'                : 'IL',
         'hindi (devanagiri)'    : 'HI',
         'hungarian'             : 'HU',
         'icelandic'             : 'IS',
         'indonesian'            : 'ID',
         'italian'               : 'IT',
         'japanese'              : 'JP',
         'korean'                : 'KR',
         'latvian'               : 'LV',
         'lithuanian'            : 'LT',
         'macedonian'            : 'MK',
         'malay'                 : 'EN', # MS is n/a, use EN
         'malayalam'             : 'EN', # ML is n/a, use EN
         'maltese'               : 'MT',
         'norwegian'             : 'NO',
         'ossetic'               : 'EN', # OS is n/a, use EN
         'persian'               : 'FA',
         'persian (iran)'        : 'FA',
         'polish'                : 'PL',
         'portuguese'            : 'BR',
         'portuguese (brazil)'   : 'BR',
         'romanian'              : 'RO',
         'russian'               : 'RU',
         'serbian'               : 'SR',
         'serbian (cyrillic)'    : 'SR',
         'slovak'                : 'SK',
         'slovenian'             : 'SL',
         'spanish'               : 'SP',
         'spanish (argentina)'   : 'SP',
         'spanish (mexico)'      : 'SP',
         'swedish'               : 'SW',
         'tamil (india)'         : 'EN', # TA is n/a, use EN
         'thai'                  : 'TH',
         'turkish'               : 'TU',
         'ukrainian'             : 'UA',
         'uzbek'                 : 'UZ',
         'vietnamese'            : 'VU',
         'vietnamese (viet nam)' : 'VU',
         'welsh'                 : 'CY'}

WEATHER_CODES = { 'chanceflurries'    : '41',
                  'chancerain'        : '39',
                  'chancesleet'       : '6',
                  'chancesnow'        : '41',
                  'chancetstorms'     : '38',
                  'clear'             : '32',
                  'cloudy'            : '26',
                  'flurries'          : '13',
                  'fog'               : '20',
                  'hazy'              : '21',
                  'mostlycloudy'      : '28',
                  'mostlysunny'       : '34',
                  'partlycloudy'      : '30',
                  'partlysunny'       : '34',
                  'sleet'             : '18',
                  'rain'              : '11',
                  'snow'              : '42',
                  'sunny'             : '32',
                  'tstorms'           : '38',
                  'unknown'           : 'na',
                  ''                  : 'na',
                  'nt_chanceflurries' : '46',
                  'nt_chancerain'     : '45',
                  'nt_chancesleet'    : '45',
                  'nt_chancesnow'     : '46',
                  'nt_chancetstorms'  : '47',
                  'nt_clear'          : '31',
                  'nt_cloudy'         : '27',
                  'nt_flurries'       : '46',
                  'nt_fog'            : '20',
                  'nt_hazy'           : '21',
                  'nt_mostlycloudy'   : '27',
                  'nt_mostlysunny'    : '33',
                  'nt_partlycloudy'   : '29',
                  'nt_partlysunny'    : '33',
                  'nt_sleet'          : '45',
                  'nt_rain'           : '45',
                  'nt_snow'           : '46',
                  'nt_sunny'          : '31',
                  'nt_tstorms'        : '47',
                  'nt_unknown'        : 'na',
                  'nt_'               : 'na'}

MONTH = { 1  : xbmc.getLocalizedString(51),
          2  : xbmc.getLocalizedString(52),
          3  : xbmc.getLocalizedString(53),
          4  : xbmc.getLocalizedString(54),
          5  : xbmc.getLocalizedString(55),
          6  : xbmc.getLocalizedString(56),
          7  : xbmc.getLocalizedString(57),
          8  : xbmc.getLocalizedString(58),
          9  : xbmc.getLocalizedString(59),
          10 : xbmc.getLocalizedString(60),
          11 : xbmc.getLocalizedString(61),
          12 : xbmc.getLocalizedString(62)}

WEEKDAY = { 0  : xbmc.getLocalizedString(41),
            1  : xbmc.getLocalizedString(42),
            2  : xbmc.getLocalizedString(43),
            3  : xbmc.getLocalizedString(44),
            4  : xbmc.getLocalizedString(45),
            5  : xbmc.getLocalizedString(46),
            6  : xbmc.getLocalizedString(47)}

SEVERITY = { 'W' : __language__(32510),
             'A' : __language__(32511),
             'Y' : __language__(32512),
             'S' : __language__(32513),
             'O' : __language__(32514),
             'F' : __language__(32515),
             'N' : __language__(32516),
             'L' :'', # no idea
             ''  : ''}

def MOONPHASE(age, percent):
    if (percent == 0) and (age == 0):
        phase = __language__(32501)
    elif (age < 17) and (age > 0) and (percent > 0) and (percent < 50):
        phase = __language__(32502)
    elif (age < 17) and (age > 0) and (percent == 50):
        phase = __language__(32503)
    elif (age < 17) and (age > 0) and (percent > 50) and (percent < 100):
        phase = __language__(32504)
    elif (age > 0) and (percent == 100):
        phase = __language__(32505)
    elif (age > 15) and (percent < 100) and (percent > 50):
        phase = __language__(32506)
    elif (age > 15) and (percent == 50):
        phase = __language__(32507)
    elif (age > 15) and (percent < 50) and (percent > 0):
        phase = __language__(32508)
    else:
        phase = ''
    return phase

def KPHTOBFT(spd):
    if (spd < 1.0):
        bft = '0'
    elif (spd >= 1.0) and (spd < 5.6):
        bft = '1'
    elif (spd >= 5.6) and (spd < 12.0):
        bft = '2'
    elif (spd >= 12.0) and (spd < 20.0):
        bft = '3'
    elif (spd >= 20.0) and (spd < 29.0):
        bft = '4'
    elif (spd >= 29.0) and (spd < 39.0):
        bft = '5'
    elif (spd >= 39.0) and (spd < 50.0):
        bft = '6'
    elif (spd >= 50.0) and (spd < 62.0):
        bft = '7'
    elif (spd >= 62.0) and (spd < 75.0):
        bft = '8'
    elif (spd >= 75.0) and (spd < 89.0):
        bft = '9'
    elif (spd >= 89.0) and (spd < 103.0):
        bft = '10'
    elif (spd >= 103.0) and (spd < 118.0):
        bft = '11'
    elif (spd >= 118.0):
        bft = '12'
    else:
        bft = ''
    return bft

########NEW FILE########
__FILENAME__ = wunderground
# -*- coding: utf-8 -*-

import urllib2, gzip, base64
from StringIO import StringIO

WAIK             = 'NDEzNjBkMjFkZjFhMzczNg=='
WUNDERGROUND_URL = 'http://api.wunderground.com/api/%s/%s/%s/q/%s.%s'

def wundergroundapi(features, settings, query, fmt):
    url = WUNDERGROUND_URL % (base64.b64decode(WAIK)[::-1], features, settings, query, fmt)
    try:
        req = urllib2.Request(url)
        req.add_header('Accept-encoding', 'gzip')
        response = urllib2.urlopen(req)
        if response.info().get('Content-Encoding') == 'gzip':
            buf = StringIO(response.read())
            compr = gzip.GzipFile(fileobj=buf)
            data = compr.read()
        else:
            data = response.read()
        response.close()
    except:
        data = ''
    return data

########NEW FILE########
