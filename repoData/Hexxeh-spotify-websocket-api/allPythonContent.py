__FILENAME__ = respotify-helper
#!/usr/bin/env python

import sys
sys.path.append("../..")
from spotify_web.friendly import Spotify
import cherrypy


class SpotifyURIHandler(object):
    def default(self, uri=None):
        if uri is None:
            raise cherrypy.HTTPError(400, "A paramater was expected but not supplied.")

        spotify = Spotify(sys.argv[1], sys.argv[2])
        track = spotify.objectFromURI(uri)
        if track is None:
            spotify.logout()
            raise cherrypy.HTTPError(404, "Could not find a track with that URI.")

        url = track.getFileURL()
        if not url:
            spotify.logout()
            raise cherrypy.HTTPError(404, "Could not find a track URL for that URI.")

        spotify.logout()
        raise cherrypy.HTTPRedirect(url)

    default.exposed = True

cherrypy.engine.autoreload.unsubscribe()
cherrypy.config.update({"environment": "production"})
cherrypy.quickstart(SpotifyURIHandler())

########NEW FILE########
__FILENAME__ = respotify
#!/usr/bin/env python

import argparse
import getpass
import sys
sys.path.append("../..")
from spotify_web.friendly import Spotify, SpotifyTrack, SpotifyUserlist
from threading import Thread, Lock, Event
from mpd import MPDClient
import os
import subprocess

playing_playlist = None
current_playlist = None
uri_resolver = None


class LockableMPDClient(MPDClient):
    def __init__(self, use_unicode=False):
        super(LockableMPDClient, self).__init__()
        self.use_unicode = use_unicode
        self._lock = Lock()

    def acquire(self):
        self._lock.acquire()

    def release(self):
        self._lock.release()

    def __enter__(self):
        self.acquire()

    def __exit__(self, type, value, traceback):
        self.release()

client = LockableMPDClient()


def header():
    os.system("clear")
    print """                                   _    ___
                               _  (_)  / __)
  ____ _____  ___ ____   ___ _| |_ _ _| |__ _   _
 / ___) ___ |/___)  _ \ / _ (_   _) (_   __) | | |
| |   | ____|___ | |_| | |_| || |_| | | |  | |_| |
|_|   |_____|___/|  __/ \___/  \__)_| |_|   \__  |
                 |_|                       (____/

    """


def display_playlist(playlist=None):
    if current_playlist is None and playlist is None:
        return

    playlist = current_playlist if playlist is None else playlist

    print playlist.getName()+"\n"

    if playlist.getNumTracks() == 0:
        print "No tracks currently in playlist"
    else:
        with client:
            status = client.status()
        playing_index = int(status["song"]) + 1 if "song" in status else -1
        index = 1
        tracks = playlist.getTracks()
        for track in tracks:
            status
            prefix = " * " if playlist == playing_playlist and index == playing_index and status["state"] == "play" else "   "
            print prefix + "[" + str(index) + "] " + track.getName() + " - " + track.getArtists(nameOnly=True)
            index += 1


def set_current_playlist(playlist):
    global current_playlist
    current_playlist = playlist
    display_playlist()


def command_list(*args):
    global rootlist
    global current_playlist

    rootlist = spotify.getPlaylists()

    if len(*args) == 0 or args[0][0] == "":
        print "Playlists\n"
        index = 1
        for playlist in rootlist:
            print " ["+str(index)+"] "+playlist.getName()
            index += 1
    else:
        try:
            if len(rootlist) >= int(args[0][0]):
                playlist_index = int(args[0][0])-1
                set_current_playlist(rootlist[playlist_index])
        except:
            command_list([])


def command_uri(*args):
    if len(*args) > 0:
        uri = args[0][0]

        obj = spotify.objectFromURI(uri)
        if obj is None:
            print "Invalid URI"
            return

        if isinstance(obj, SpotifyTrack):
            obj = SpotifyUserlist(spotify, obj.getName(), [obj])

        set_current_playlist(obj)


def command_album(*args):
    if args[0][0] == "" or current_playlist is None:
        return

    index = int(args[0][0])-1
    if current_playlist.getNumTracks() < index:
        return

    album = current_playlist.getTracks()[index].getAlbum()
    set_current_playlist(album)


def command_artist(*args):
    if args[0][0] == "" or current_playlist is None:
        return

    index = int(args[0][0])-1
    if current_playlist.getNumTracks() < index:
        return

    artist = current_playlist.getTracks()[index].getArtists()[0]
    set_current_playlist(artist)


def command_search(*args):
    if len(*args) == 0 or args[0][0] == "":
        return

    query = " ".join(args[0])

    results = spotify.search(query, query_type="tracks")
    tracks = results.getTracks()

    if len(tracks) == 0:
        print "No tracks found!"
        return

    set_current_playlist(results)


def command_play(*args):
    if len(*args) == 0 or args[0][0] == "":
        return

    try:
        play_index = int(args[0][0])-1
    except:
        return

    global playing_playlist
    playing_playlist = current_playlist
    with client:
        client.clear()
        for track in current_playlist.getTracks():
            client.add("http://localhost:8080/?uri="+track.getURI())
        client.play(play_index)

    display_playlist()


def command_stop(*args):
    with client:
        client.stop()
    display_playlist()


def command_next(*args):
    with client:
        client.next()
    display_playlist()


def command_prev(*args):
    with client:
        status = client.status()
    if "song" in status:
        if status["song"] != "0":
            client.previous()
        elif status["state"] == "play":
            client.stop()
    display_playlist()


def command_info(*args):
    print "Username: " + spotify.api.username
    print "Account type: " + spotify.api.account_type
    print "Country: " + spotify.api.country
    print "Connected to " + spotify.api.settings["wss"].replace("wss://", "").replace(":443", "").replace("/", "")


def command_help(*args):
    for k, v in command_map.items():
        print k+"\t\t"+v[1]

quitting = False


def command_quit(*args):
    spotify.logout()
    global quitting
    quitting = True


def command_current_playlist(*args):
    display_playlist(playing_playlist)

command_map = {
    "search": (command_search, "search for tracks"),
    "artist": (command_artist, "view the artist for a specific track"),
    "album":  (command_album, "view the album for a specific track"),
    "stop": (command_stop, "stops any currently playing track"),
    "play": (command_play, "plays the track with given index"),
    "next": (command_next, "plays the next track in the current playlist"),
    "prev": (command_prev, "plays the previous track in the current playlist"),
    "current": (command_current_playlist, "shows the current playlist we're playing"),
    "uri": (command_uri, "lists metadata for a URI (album)"),
    "list": (command_list, "lists your rootlist or a playlist"),
    "info": (command_info, "shows account information"),
    "help": (command_help, "shows help information"),
    "quit": (command_quit, "quits the application"),
}


def command_loop():
    header()
    command_help()
    while False == spotify.api.disconnecting and False == quitting:
        sys.stdout.write("\n> ")
        sys.stdout.flush()
        command = raw_input().split(" ")
        command_name = command[0]

        header()
        if command_name in command_map:
            command_map[command_name][0](command[1:])
        else:
            command_help()

heartbeat_marker = Event()


def heartbeat_handler():
    while client is not None:
        with client:
            client.status()
        heartbeat_marker.wait(timeout=15)


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Command line Spotify client')
    parser.add_argument('username', help='Your spotify username')
    parser.add_argument('password', nargs='?', default=None,
                        help='<Optional> your spotify password')

    args = parser.parse_args()

    if args.password is None:
        args.password = getpass.getpass("Please enter your Spotify password")

    spotify = Spotify(args.username, args.password)
    if spotify.logged_in():
        os.system("kill `pgrep -f respotify-helper` &> /dev/null")
        uri_resolver = subprocess.Popen([sys.executable, "respotify-helper.py",
                                        args.username, args.password])
        with client:
            client.connect(host="localhost", port="6600")
        Thread(target=heartbeat_handler).start()
        command_loop()
        os.system("clear")
        with client:
            client.clear()
            client.disconnect()
            client = None
            heartbeat_marker.set()
        uri_resolver.kill()
    else:
        print "Login failed"
        sys.exit(1)

########NEW FILE########
__FILENAME__ = blocking
#!/usr/bin/env python

import sys
sys.path.append("..")
from spotify_web.spotify import SpotifyAPI, SpotifyUtil

if len(sys.argv) < 4:
    print "Usage: "+sys.argv[0]+" <username> <password> <action> [URI]"
    sys.exit(1)

action = sys.argv[3]

sp = SpotifyAPI()
sp.connect(sys.argv[1], sys.argv[2])


def display_playlist(playlist):
    print playlist.attributes.name+"\n"

    if playlist.length > 0:
        track_uris = [track.uri for track in playlist.contents.items if not SpotifyUtil.is_local(track.uri)]
        tracks = sp.metadata_request(track_uris)
        for track in tracks:
            print track.name
    else:
        print "no tracks"

    print "\n"

if action == "track":
    uri = sys.argv[4] if len(sys.argv) > 4 else "spotify:track:3IKSCoHEblCE60IKr4SVNd"

    track = sp.metadata_request(uri)
    print track.name

elif action == "album":
    uri = sys.argv[4] if len(sys.argv) > 4 else "spotify:album:3OmHoatMS34vM7ZKb4WCY3"

    album = sp.metadata_request(uri)
    print album.name+" - "+album.artist[0].name+"\n"

    uris = [SpotifyUtil.gid2uri("track", track.gid) for track in album.disc[0].track]
    tracks = sp.metadata_request(uris)
    for track in tracks:
        print track.name

elif action == "playlists":
    username = sys.argv[4] if len(sys.argv) > 4 else sp.username

    playlist_uris = [playlist.uri for playlist in sp.playlists_request(username).contents.items]
    playlists = [sp.playlist_request(playlist_uri) for playlist_uri in playlist_uris]

    for playlist in playlists:
        display_playlist(playlist)

elif action == "playlist":
    uri = sys.argv[4] if len(sys.argv) > 4 else "spotify:user:topsify:playlist:1QM1qz09ZzsAPiXphF1l4S"

    playlist = sp.playlist_request(uri)
    display_playlist(playlist)

elif action == "tracks_toplist":
    top_tracks = sp.toplist_request("tracks")
    print top_tracks

elif action == "restriction":
    uri = sys.argv[4] if len(sys.argv) > 4 else "spotify:track:3IKSCoHEblCE60IKr4SVNd"

    track = sp.metadata_request(uri)
    resp = sp.track_uri(track)

    if False != resp and "uri" in resp:
        print "Track is available!"
    else:
        print "Track is NOT available! Double-check this using the official client"

elif action == "newplaylist":
    name = sys.argv[4] if len(sys.argv) > 4 else "foobar"
    uri = sp.new_playlist(name)
    print uri

########NEW FILE########
__FILENAME__ = ctype
#!/usr/bin/env python

import sys
sys.path.append("..")
import ctypes
from spotify_web.friendly import Spotify
import pycurl


mpg123 = ctypes.CDLL('libmpg123.so.0')
ao = ctypes.CDLL('libao.so.4')
pycurl.global_init(pycurl.GLOBAL_ALL)
ao.ao_initialize()
mpg123.mpg123_init()
mpg123_new = mpg123.mpg123_new
mpg123_new.restype = ctypes.c_void_p
mh = mpg123_new(ctypes.c_char_p(None), None)
mpg123.mpg123_open_feed(ctypes.c_void_p(mh))

MPG123_NEW_FORMAT = -11
MPG123_DONE = -12
MPG123_OK = 0
MPG123_NEED_MORE = -10

AO_FMT_NATIVE = 4

BITS = 8


class AOSampleFormat(ctypes.Structure):
    _fields_ = [("bits", ctypes.c_int),
                ("rate", ctypes.c_int),
                ("channels", ctypes.c_int),
                ("byte_format", ctypes.c_int),
                ("matrix", ctypes.c_char_p)]

aodev = None
count = 0


def play_stream(buf):
    global count
    global aodev

    mpg123.mpg123_feed(ctypes.c_void_p(mh), buf, len(buf))
    done = ctypes.c_int(1)
    offset = ctypes.c_size_t(0)

    channels = ctypes.c_int(0)
    encoding = ctypes.c_int(0)
    rate = ctypes.c_int(0)

    audio = ctypes.c_char_p()

    while done.value > 0:
        err = mpg123.mpg123_decode_frame(ctypes.c_void_p(mh), ctypes.pointer(offset), ctypes.pointer(audio), ctypes.pointer(done))
        if err == MPG123_NEW_FORMAT:
            mpg123.mpg123_getformat(ctypes.c_void_p(mh), ctypes.pointer(rate), ctypes.pointer(channels), ctypes.pointer(encoding))
            fmt = AOSampleFormat()
            fmt.bits = ctypes.c_int(mpg123.mpg123_encsize(encoding)*BITS)
            fmt.rate = rate
            fmt.channels = channels
            fmt.byte_format = AO_FMT_NATIVE
            fmt.matrix = 0
            ao_open_live = ao.ao_open_live
            ao_open_live.restype = ctypes.c_void_p
            aodev = ao_open_live(ao.ao_default_driver_id(), ctypes.pointer(fmt), None)
        elif err == MPG123_OK:
            ao.ao_play(ctypes.c_void_p(aodev), audio, done)
    return len(buf)


def play_track(uri):
    global aodev

    curl_obj = pycurl.Curl()
    curl_obj.setopt(pycurl.WRITEFUNCTION, play_stream)
    curl_obj.setopt(pycurl.URL, str(uri))
    curl_obj.perform()
    curl_obj.close()

    mpg123.mpg123_close(ctypes.c_void_p(mh))
    mpg123.mpg123_delete(ctypes.c_void_p(mh))
    mpg123.mpg123_exit()

    ao.ao_close(ctypes.c_void_p(aodev))
    ao.ao_shutdown()

if len(sys.argv) < 3:
    print "Usage: "+sys.argv[0]+" <username> <password> [URI]"
else:
    sp = Spotify(sys.argv[1], sys.argv[2])
    if not sp.logged_in():
        print "Login failed"
    else:
        uri = sys.argv[3] if len(sys.argv) > 3 else "spotify:track:6NwbeybX6TDtXlpXvnUOZC"
        obj = sp.objectFromURI(uri)
        if obj is not None:
            if obj.uri_type == "track":
                print obj.getName(), obj.getDuration()/1000.0, "seconds"
                play_track(obj.getFileURL())
            else:
                print "No support for yet for", obj.uri_type
        else:
            print "Request for %s failed" % uri
        sp.logout()

########NEW FILE########
__FILENAME__ = decode_mercury
#!/usr/bin/env python
import sys
sys.path.append("..")
import base64
from spotify_web.proto import mercury_pb2, metadata_pb2, playlist4ops_pb2, playlist4service_pb2, playlist4changes_pb2


msg_types = {
    "request": mercury_pb2.MercuryRequest,
    "reply": mercury_pb2.MercuryReply,
    "mget_request": mercury_pb2.MercuryMultiGetRequest,
    "mget_reply": mercury_pb2.MercuryMultiGetReply,
    "track": metadata_pb2.Track,
    "album": metadata_pb2.Album,
    "createlistreply": playlist4service_pb2.CreateListReply,
    "listdump": playlist4changes_pb2.ListDump,
    "oplist": playlist4ops_pb2.OpList
}

msg = sys.argv[2]

if sys.argv[1] == "op":
    request = msg_types["request"]()
    request.ParseFromString(base64.decodestring(msg))
    print request.__str__()
    op = playlist4ops_pb2.Op()
    op.ParseFromString(str(request.uri))
    obj = op
else:
    ctor = msg_types[sys.argv[1]]
    obj = ctor()
    obj.ParseFromString(base64.decodestring(msg))
print obj.__str__()

########NEW FILE########
__FILENAME__ = decode_session
#!/usr/bin/python

import base64, json, re, sys

sys.path.append("..")
from spotify_web.proto import mercury_pb2, metadata_pb2, playlist4ops_pb2, playlist4service_pb2, playlist4changes_pb2

def decode_hermes(prefix, json_obj):
	if prefix == ">>":
		ctor = mercury_pb2.MercuryRequest
		msg = json_obj["args"][1]
	else:
		ctor = mercury_pb2.MercuryReply
		msg = json_obj["result"][0]

	obj = ctor()
	obj.ParseFromString(base64.decodestring(msg))
	return obj.__str__()

undecoded = 0
undecoded_names = set()

with open(sys.argv[1], "r") as f:
	for line in f.readlines():
		prefix = line[:2]
		if prefix != ">>" and prefix != "<<":
			continue

		rx = re.compile("(\{.*\})")
		r = rx.search(line)

		if len(r.groups()) < 1:
			break
		
		obj_str = r.groups()[0]
		obj = json.loads(obj_str)

		if "id" not in obj or "name" not in obj:
			continue

		#if int(obj["id"]) > 20:
			#break

		cmd = obj["name"]
		cmd = cmd[3:] if "sp/" in cmd else cmd
		if cmd == "hm_b64":
			decode_hermes(prefix, obj)
		elif cmd == "track_uri":
			print obj
		elif cmd == "connect":
			continue
		elif cmd == "echo" or cmd == "log":
			continue
		elif cmd == "log_ce" or cmd == "log_view":
			continue
		else:
			undecoded += 1
			undecoded_names.add(cmd)

print "%d messages were not decoded" % undecoded
print ', '.join(undecoded_names)
########NEW FILE########
__FILENAME__ = gstreamer
#!/usr/bin/env python

import sys
sys.path.append("..")
import signal
from spotify_web.friendly import Spotify
import pygst
pygst.require('0.10')
import gst
import gobject


def sigint(sig, frame):
    global mainloop
    mainloop.quit()


def player_message(bus, msg, player, mainloop):
    if msg.type == gst.MESSAGE_EOS:
        player.set_state(gst.STATE_NULL)
        mainloop.quit()
    elif msg.type == gst.MESSAGE_ERROR:
        player.set_state(gst.STATE_NULL)
        print msg.parse_error()

if len(sys.argv) < 3:
    print "Usage: " + sys.argv[0] + " <username> <password> [track URI]"
else:

    sp = Spotify(sys.argv[1], sys.argv[2])
    mainloop = gobject.MainLoop()

    player = gst.parse_launch('uridecodebin name=uridecode ! autoaudiosink')

    bus = player.get_bus()
    bus.add_signal_watch()
    bus.connect('message', player_message, player, mainloop)

    uri = sys.argv[3] if len(sys.argv) > 3 else "spotify:track:6NwbeybX6TDtXlpXvnUOZC"
    track = sp.objectFromURI(uri)

    print ','.join([a.getName() for a in track.getArtists()]) + ' - ' + track.getName()

    mp3_uri = track.getFileURL()
    player.get_by_name('uridecode').set_property('uri', mp3_uri)
    player.set_state(gst.STATE_PLAYING)

    signal.signal(signal.SIGINT, sigint)
    mainloop.run()

    sp.logout()

########NEW FILE########
__FILENAME__ = nonblocking
#!/usr/bin/env python

import sys
sys.path.append("..")
from spotify_web.spotify import SpotifyAPI, SpotifyUtil


def track_callback(sp, tracks):
    for track in tracks:
        print track.name


def album_callback(sp, album):
    print album.name + " - " + album.artist[0].name + "\n"
    uris = [SpotifyUtil.gid2uri("track", track.gid) for track in album.disc[0].track]
    sp.metadata_request(uris, track_callback)


def new_playlist_callback(sp, resp):
    print "callback!"
    print resp


def login_callback(sp, logged_in):
    if logged_in:
        # uri = sys.argv[3] if len(sys.argv) > 3 else "spotify:album:3OmHoatMS34vM7ZKb4WCY3"
        # sp.metadata_request(uri, album_callback)
        sp.new_playlist("foobar", new_playlist_callback)
    else:
        print "There was an error logging in"

if len(sys.argv) < 3:
    print "Usage: " + sys.argv[0] + " <username> <password> [track URI]"
else:
    sp = SpotifyAPI(login_callback)
    sp.connect(sys.argv[1], sys.argv[2])

########NEW FILE########
__FILENAME__ = play
#!/usr/bin/env python

import sys
sys.path.append("..")
import os
from spotify_web.spotify import SpotifyAPI


def track_uri_callback(sp, result):
    if sys.platform == "darwin":
        script = """
            tell application "VLC"
                Stop
                OpenURL "%s"
                Play
            end tell
        """ % result["uri"]
        os.system("osascript -e '%s'" % script)
    elif sys.platform == "linux" or sys.platform == "linux2" or sys.platform[:7] == "freebsd":
        os.system("vlc \""+result["uri"]+"\"")
    else:
        print "URL: "+result["uri"]
    sp.disconnect()


def track_callback(sp, track):
    sp.track_uri(track, track_uri_callback)


def login_callback(sp, logged_in):
    if logged_in:
        uri = sys.argv[3] if len(sys.argv) > 3 else "spotify:track:4a0TeZNKWwoLu4C7H6n95D"
        track = sp.metadata_request(uri)
        sp.track_uri(track, track_uri_callback)
    else:
        print "There was an error logging in"

if len(sys.argv) < 3:
    print "Usage: "+sys.argv[0]+" <username> <password> [album URI]"
else:
    sp = SpotifyAPI(login_callback)
    sp.connect(sys.argv[1], sys.argv[2])

########NEW FILE########
__FILENAME__ = serve
#!/usr/bin/env python

import sys
sys.path.append("..")
from spotify_web.friendly import Spotify
import cherrypy


sessions = {}


def get_or_create_session(username, password):
    if username not in sessions:
        spotify = Spotify(username, password)

        if not spotify:
            return False
        else:
            sessions[username] = spotify

    return sessions[username]


def disconnect_sessions():
    for username, session in sessions.items():
        session.logout()


class SpotifyURIHandler(object):
    def default(self, username=None, password=None, uri=None, action="proxymp3"):
        if uri is None or username is None or password is None:
            raise cherrypy.HTTPError(400, "A paramater was expected but not supplied.")

        spotify = get_or_create_session(username, password)
        if not spotify:
            raise cherrypy.HTTPError(403, "Username or password given were incorrect.")

        track = spotify.objectFromURI(uri)
        if track is None:
            raise cherrypy.HTTPError(404, "Could not find a track with that URI.")

        if action == "proxymp3":
            url = track.getFileURL()
            if not url:
                raise cherrypy.HTTPError(404, "Could not find a track URL for that URI.")
        elif action == "proxycover":
            covers = track.getAlbum().getCovers()
            url = covers["640"]
        else:
            raise cherrypy.HTTPError(400, "An invalid action was requested.")

        raise cherrypy.HTTPRedirect(url)

    default.exposed = True

cherrypy.engine.subscribe("exit", disconnect_sessions)
cherrypy.engine.autoreload.unsubscribe()
cherrypy.config.update({"environment": "production"})
cherrypy.quickstart(SpotifyURIHandler())

########NEW FILE########
__FILENAME__ = friendly
from functools import partial
from lxml import etree
from threading import Thread
from Queue import Queue

from .spotify import SpotifyAPI, SpotifyUtil
# from spotify_web.proto import mercury_pb2, metadata_pb2


class Cache(object):
    def __init__(self, func):
        self.func = func

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self.func
        return partial(self, obj)

    def __call__(self, *args, **kw):
        obj = args[0]
        try:
            cache = obj.__cache
        except AttributeError:
            cache = obj.__cache = {}

        arglist = list(args[1:])
        for i in xrange(0, len(arglist)):
            if type(arglist[i]) == list:
                astring = True
                for item in arglist[i]:
                    if type(item) != str and type(item) != unicode:
                        astring = False
                        break
                if astring:
                    arglist[i] = "".join(arglist[i])
        arglist = tuple(arglist)

        key = (self.func, arglist, frozenset(kw.items()))
        try:
            res = cache[key]
        except KeyError:
            res = cache[key] = self.func(*args, **kw)
        return res


class SpotifyCacheManager():
    def __init__(self):
        self.track_cache = {}
        self.album_cache = {}
        self.artist_cache = {}

    def get(self, uri):
        cache = {
            "track": self.track_cache,
            "album": self.album_cache,
            "artist": self.artist_cache,
        }

        uri_type = SpotifyUtil.get_uri_type(uri)
        if uri_type not in cache:
            return False


class SpotifyObject():
    def __str__(self):
        return unicode(self)

    def __unicode__(self):
        return self.getName()

    def getID(self):
        return SpotifyUtil.gid2id(self.obj.gid)

    def getURI(self):
        return SpotifyUtil.gid2uri(self.uri_type, self.obj.gid)


class SpotifyMetadataObject(SpotifyObject):
    def __init__(self, spotify, uri=None, obj=None):
        if obj is not None:
            self.obj = obj
        else:
            self.obj = spotify.api.metadata_request(uri)
        self.spotify = spotify

    def getName(self):
        return self.obj.name

    def getPopularity(self):
        return self.obj.popularity


class SpotifyTrack(SpotifyMetadataObject):
    uri_type = "track"
    replaced = False

    @Cache
    def isAvailable(self, country=None):
        country = self.spotify.api.country if country is None else country
        new_obj = self.spotify.api.recurse_alternatives(self.obj, country=country)
        if not new_obj:
            return False
        else:
            # invalidate cache
            self._Cache__cache = {}

            if not new_obj.HasField("name"):
                new_obj = self.spotify.api.metadata_request(SpotifyUtil.gid2uri("track", new_obj.gid))
            self.old_obj = self.obj
            self.obj = new_obj
            self.replaced = True
            return True

    def setStarred(self, starred=True):
        self.spotify.api.set_starred(self.getURI(), starred)

    def getNumber(self):
        return self.obj.number

    def getDiscNumber(self):
        return self.obj.disc_number

    def getDuration(self):
        return self.obj.duration

    def getFileURL(self, urlOnly=True):
        resp = self.spotify.api.track_uri(self.obj)

        if False != resp and "uri" in resp:
            return resp["uri"] if urlOnly else resp
        else:
            return False

    @Cache
    def getAlbum(self, nameOnly=False):
        if nameOnly:
            return self.obj.album.name
        else:
            return self.spotify.objectFromInternalObj("album", self.obj.album)[0]

    @Cache
    def getArtists(self, nameOnly=False):
        return self.spotify.objectFromInternalObj("artist", self.obj.artist, nameOnly)


class SpotifyArtist(SpotifyMetadataObject):
    uri_type = "artist"

    def getPortraits(self):
        return Spotify.imagesFromArray(self.obj.portrait)

    def getBiography(self):
        return self.obj.biography[0].text if len(self.obj.biography) else None

    def getNumTracks(self):
        # this means the number of top tracks, really
        return len(self.getTracks(objOnly=True))

    def getRelatedArtists(self, nameOnly=False):
        return self.spotify.objectFromInternalObj("artist", self.obj.related, nameOnly)

    @Cache
    def getTracks(self, objOnly=False):
        top_tracks = []

        for obj in self.obj.top_track:
            if obj.country == self.spotify.api.country:
                top_tracks = obj

        if objOnly:
            return top_tracks.track

        if len(top_tracks.track) == 0:
            return None

        return self.spotify.objectFromInternalObj("track", top_tracks.track)


class SpotifyAlbum(SpotifyMetadataObject):
    uri_type = "album"

    def getLabel(self):
        return self.obj.label

    @Cache
    def getArtists(self, nameOnly=False):
        return self.spotify.objectFromInternalObj("artist", self.obj.artist, nameOnly)

    def getCovers(self):
        return Spotify.imagesFromArray(self.obj.cover)

    def getNumDiscs(self):
        return len(self.obj.disc)

    def getNumTracks(self):
        return len(self.getTracks(objOnly=True))

    @Cache
    def getTracks(self, disc_num=None, objOnly=False):
        track_objs = []

        for disc in self.obj.disc:
            if disc.number == disc_num or disc_num is None:
                track_objs += disc.track

        if objOnly:
            return track_objs

        if len(track_objs) == 0:
            return None

        return self.spotify.objectFromInternalObj("track", track_objs)


class SpotifyPlaylist(SpotifyObject):
    uri_type = "playlist"
    refs = []

    def __init__(self, spotify, uri):
        self.spotify = spotify
        self.obj = spotify.api.playlist_request(uri)
        self.uri = uri
        SpotifyPlaylist.refs.append(self)

    def __getitem__(self, index):
        if index >= self.getNumTracks():
            raise IndexError

        return self.getTracks()[index]

    def __len__(self):
        return self.getNumTracks()

    def reload(self):
        self._Cache__cache = {}
        self.obj = self.spotify.api.playlist_request(self.uri)

    def reload_refs(self):
        for playlist in self.refs:
            if playlist.getURI() == self.uri:
                playlist.reload()

    def getID(self):
        uri_parts = self.uri.split(":")
        if len(uri_parts) == 4:
            return uri_parts[3]
        else:
            return uri_parts[4]

    def getURI(self):
        return self.uri

    def getName(self):
        return "Starred" if self.getID() == "starred" else self.obj.attributes.name

    def rename(self, name):
        ret = self.spotify.api.rename_playlist(self.getURI(), name)
        self.reload_refs()
        return ret

    def addTracks(self, tracks):
        tracks = [tracks] if type(tracks) != list else tracks
        uris = [track.getURI() for track in tracks]

        uris_str = ",".join(uris)
        self.spotify.api.playlist_add_track(self.getURI(), uris_str)

        self.reload_refs()

    def removeTracks(self, tracks):
        tracks = [tracks] if type(tracks) != list else tracks

        uris = []
        for track in tracks:
            if track.replaced:
                uris.append(SpotifyUtil.gid2uri("track", track.old_obj.gid))
            else:
                uris.append(self.getURI())

        self.spotify.api.playlist_remove_track(self.getURI(), uris)

        self.reload_refs()

    def getNumTracks(self):
        # we can't rely on the stated length, some might not be available
        return len(self.getTracks())

    @Cache
    def getTracks(self):
        track_uris = [item.uri for item in self.obj.contents.items]
        tracks = self.spotify.objectFromURI(track_uris, asArray=True)

        if self.obj.contents.truncated:
            def work_function(spotify, uri, start, tracks):
                track_uris = [item.uri for item in spotify.api.playlist_request(uri, start).contents.items]
                tracks += spotify.objectFromURI(track_uris, asArray=True)

            results = {}
            jobs = []
            tracks_per_call = 100
            start = tracks_per_call
            while start < self.obj.length:
                results[start] = []
                jobs.append((self.spotify, self.uri, start, results[start]))
                start += tracks_per_call

            Spotify.doWorkerQueue(work_function, jobs)

            for k, v in sorted(results.items()):
                tracks += v

        return tracks


class SpotifyUserlist():
    def __init__(self, spotify, name, tracks):
        self.spotify = spotify
        self.name = name
        self.tracks = tracks

    def __getitem__(self, index):
        if index >= self.getNumTracks():
            raise IndexError

        return self.getTracks()[index]

    def __len__(self):
        return self.getNumTracks()

    def getID(self):
        return None

    def getURI(self):
        return None

    def getName(self):
        return self.name

    def getNumTracks(self):
        return len(self.tracks)

    def getTracks(self):
        return self.tracks


class SpotifySearch():
    def __init__(self, spotify, query, query_type, max_results, offset):
        self.spotify = spotify
        self.query = query
        self.query_type = query_type
        self.max_results = max_results
        self.offset = offset
        self.populate()

    def populate(self):
        xml = self.spotify.api.search_request(self.query, query_type=self.query_type, max_results=self.max_results, offset=self.offset)
        xml = xml[38:]  # trim UTF8 declaration
        self.result = etree.fromstring(xml)

        # invalidate cache
        self._Cache__cache = {}

    def next(self):
        self.offset += self.max_results
        self.populate()

    def prev(self):
        self.offset = self.offset - self.max_results if self.offset >= self.max_results else 0
        self.populate()

    def getName(self):
        return "Search "+self.query_type+": "+self.query

    def getTracks(self):
        return self.getObjByID(self.result, "track")

    def getNumTracks(self):
        return len(self.getTracks())

    def getAlbums(self):
        return self.getObjByID(self.result, "album")

    def getArtists(self):
        return self.getObjByID(self.result, "artist")

    def getPlaylists(self):
        return self.getObjByURI(self.result, "playlist")

    def getObjByID(self, result, obj_type):
        elems = result.find(obj_type+"s")
        if elems is None:
            elems = []
        ids = [elem[0].text for elem in list(elems)]
        objs = self.spotify.objectFromID(obj_type, ids)
        return objs

    def getObjByURI(self, result, obj_type):
        elems = result.find(obj_type+"s")
        if elems is None:
            elems = []
        uris = [elem[0].text for elem in list(elems)]
        objs = self.spotify.objectFromURI(uris, asArray=True)
        return objs


class SpotifyToplist():
    def __init__(self, spotify, toplist_content_type, toplist_type, username, region):
        self.spotify = spotify
        self.toplist_type = toplist_type
        self.toplist_content_type = toplist_content_type
        self.username = username
        self.region = region
        self.toplist = self.spotify.api.toplist_request(toplist_content_type, toplist_type, username, region)

    def getTracks(self):
        if self.toplist_content_type != "track":
            return []
        return self.spotify.objectFromID(self.toplist_content_type, self.toplist.items)

    def getAlbums(self):
        if self.toplist_content_type != "album":
            return []
        return self.spotify.objectFromID(self.toplist_content_type, self.toplist.items)

    def getArtists(self):
        if self.toplist_content_type != "artist":
            return []
        return self.spotify.objectFromID(self.toplist_content_type, self.toplist.items)


class Spotify():
    AUTOREPLACE_TRACKS = True

    def __init__(self, username, password):
        self.api = SpotifyAPI()
        self.api.connect(username, password)

    def logged_in(self):
        return self.api.is_logged_in and not self.api.disconnecting

    def logout(self):
        self.api.disconnect()

    @Cache
    def getPlaylists(self, username=None):
        username = self.api.username if username is None else username
        playlist_uris = []
        if username == self.api.username:
            playlist_uris += ["spotify:user:"+username+":starred"]

        playlist_uris += [playlist.uri for playlist in self.api.playlists_request(username).contents.items]
        return self.objectFromURI(playlist_uris)

    def newPlaylist(self, name):
        self._Cache__cache = {}

        uri = self.api.new_playlist(name)
        return SpotifyPlaylist(self, uri=uri)

    def removePlaylist(self, playlist):
        self._Cache__cache = {}
        return self.api.remove_playlist(playlist.getURI())

    def getUserToplist(self, toplist_content_type="track", username=None):
        return SpotifyToplist(self, toplist_content_type, "user", username, None)

    def getRegionToplist(self, toplist_content_type="track", region=None):
        return SpotifyToplist(self, toplist_content_type, "region", None, region)

    def search(self, query, query_type="all", max_results=50, offset=0):
        return SpotifySearch(self, query, query_type=query_type, max_results=max_results, offset=offset)

    def objectFromInternalObj(self, object_type, objs, nameOnly=False):
        if nameOnly:
            return ", ".join([obj.name for obj in objs])

        try:
            uris = [SpotifyUtil.gid2uri(object_type, obj.gid) for obj in objs]
        except:
            uris = SpotifyUtil.gid2uri(object_type, objs.gid)

        return self.objectFromURI(uris, asArray=True)

    def objectFromID(self, object_type, ids):
        try:
            uris = [SpotifyUtil.id2uri(object_type, id) for id in ids]
        except:
            uris = SpotifyUtil.id2uri(object_type, ids)

        return self.objectFromURI(uris, asArray=True)

    @Cache
    def objectFromURI(self, uris, asArray=False):
        if not self.logged_in():
            return False

        uris = [uris] if type(uris) != list else uris
        if len(uris) == 0:
            return [] if asArray else None

        uri_type = SpotifyUtil.get_uri_type(uris[0])
        if not uri_type:
            return [] if asArray else None
        elif uri_type == "playlist":
            if len(uris) == 1:
                results = [SpotifyPlaylist(self, uri=uris[0])]
            else:
                thread_results = {}
                jobs = []
                for index in range(0, len(uris)):
                    jobs.append((self, uris[index], thread_results, index))

                def work_function(spotify, uri, results, index):
                    results[index] = SpotifyPlaylist(spotify, uri=uri)

                Spotify.doWorkerQueue(work_function, jobs)

                results = [v for k, v in thread_results.items()]

        elif uri_type in ["track", "album", "artist"]:
            uris = [uri for uri in uris if not SpotifyUtil.is_local(uri)]
            objs = self.api.metadata_request(uris)
            objs = [objs] if type(objs) != list else objs

            failed_requests = len([obj for obj in objs if False == obj])
            if failed_requests > 0:
                print failed_requests, "metadata requests failed"

            objs = [obj for obj in objs if False != obj]
            if uri_type == "track":
                tracks = [SpotifyTrack(self, obj=obj) for obj in objs]
                results = [track for track in tracks if False == self.AUTOREPLACE_TRACKS or track.isAvailable()]
            elif uri_type == "album":
                results = [SpotifyAlbum(self, obj=obj) for obj in objs]
            elif uri_type == "artist":
                results = [SpotifyArtist(self, obj=obj) for obj in objs]
        else:
            return [] if asArray else None

        if not asArray:
            if len(results) == 1:
                results = results[0]
            elif len(results) == 0:
                return [] if asArray else None

        return results

    @staticmethod
    def doWorkerQueue(work_function, args, worker_thread_count=5):
        def worker():
            while not q.empty():
                args = q.get()
                work_function(*args)
                q.task_done()

        q = Queue()
        for arg in args:
            q.put(arg)

        for i in range(worker_thread_count):
            t = Thread(target=worker)
            t.start()
        q.join()

    @staticmethod
    def imagesFromArray(image_objs):
        images = {}
        for image_obj in image_objs:
            size = str(image_obj.width)
            images[size] = "https://d3rt1990lpmkn.cloudfront.net/" + size + "/" + SpotifyUtil.gid2id(image_obj.file_id)

        return images

########NEW FILE########
__FILENAME__ = mercury_pb2
# Generated by the protocol buffer compiler.  DO NOT EDIT!

from google.protobuf import descriptor
from google.protobuf import message
from google.protobuf import reflection
from google.protobuf import descriptor_pb2
# @@protoc_insertion_point(imports)



DESCRIPTOR = descriptor.FileDescriptor(
  name='mercury.proto',
  package='spotify.mercury.proto',
  serialized_pb='\n\rmercury.proto\x12\x15spotify.mercury.proto\"P\n\x16MercuryMultiGetRequest\x12\x36\n\x07request\x18\x01 \x03(\x0b\x32%.spotify.mercury.proto.MercuryRequest\"J\n\x14MercuryMultiGetReply\x12\x32\n\x05reply\x18\x01 \x03(\x0b\x32#.spotify.mercury.proto.MercuryReply\"O\n\x0eMercuryRequest\x12\x0b\n\x03uri\x18\x01 \x01(\t\x12\x14\n\x0c\x63ontent_type\x18\x02 \x01(\t\x12\x0c\n\x04\x62ody\x18\x03 \x01(\x0c\x12\x0c\n\x04\x65tag\x18\x04 \x01(\x0c\"\x83\x02\n\x0cMercuryReply\x12\x13\n\x0bstatus_code\x18\x01 \x01(\x11\x12\x16\n\x0estatus_message\x18\x02 \x01(\t\x12\x45\n\x0c\x63\x61\x63he_policy\x18\x03 \x01(\x0e\x32/.spotify.mercury.proto.MercuryReply.CachePolicy\x12\x0b\n\x03ttl\x18\x04 \x01(\x11\x12\x0c\n\x04\x65tag\x18\x05 \x01(\x0c\x12\x14\n\x0c\x63ontent_type\x18\x06 \x01(\x0c\x12\x0c\n\x04\x62ody\x18\x07 \x01(\x0c\"@\n\x0b\x43\x61\x63hePolicy\x12\x0c\n\x08\x43\x41\x43HE_NO\x10\x01\x12\x11\n\rCACHE_PRIVATE\x10\x02\x12\x10\n\x0c\x43\x41\x43HE_PUBLIC\x10\x03')



_MERCURYREPLY_CACHEPOLICY = descriptor.EnumDescriptor(
  name='CachePolicy',
  full_name='spotify.mercury.proto.MercuryReply.CachePolicy',
  filename=None,
  file=DESCRIPTOR,
  values=[
    descriptor.EnumValueDescriptor(
      name='CACHE_NO', index=0, number=1,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='CACHE_PRIVATE', index=1, number=2,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='CACHE_PUBLIC', index=2, number=3,
      options=None,
      type=None),
  ],
  containing_type=None,
  options=None,
  serialized_start=475,
  serialized_end=539,
)


_MERCURYMULTIGETREQUEST = descriptor.Descriptor(
  name='MercuryMultiGetRequest',
  full_name='spotify.mercury.proto.MercuryMultiGetRequest',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='request', full_name='spotify.mercury.proto.MercuryMultiGetRequest.request', index=0,
      number=1, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=40,
  serialized_end=120,
)


_MERCURYMULTIGETREPLY = descriptor.Descriptor(
  name='MercuryMultiGetReply',
  full_name='spotify.mercury.proto.MercuryMultiGetReply',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='reply', full_name='spotify.mercury.proto.MercuryMultiGetReply.reply', index=0,
      number=1, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=122,
  serialized_end=196,
)


_MERCURYREQUEST = descriptor.Descriptor(
  name='MercuryRequest',
  full_name='spotify.mercury.proto.MercuryRequest',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='uri', full_name='spotify.mercury.proto.MercuryRequest.uri', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='content_type', full_name='spotify.mercury.proto.MercuryRequest.content_type', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='body', full_name='spotify.mercury.proto.MercuryRequest.body', index=2,
      number=3, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value="",
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='etag', full_name='spotify.mercury.proto.MercuryRequest.etag', index=3,
      number=4, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value="",
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=198,
  serialized_end=277,
)


_MERCURYREPLY = descriptor.Descriptor(
  name='MercuryReply',
  full_name='spotify.mercury.proto.MercuryReply',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='status_code', full_name='spotify.mercury.proto.MercuryReply.status_code', index=0,
      number=1, type=17, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='status_message', full_name='spotify.mercury.proto.MercuryReply.status_message', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='cache_policy', full_name='spotify.mercury.proto.MercuryReply.cache_policy', index=2,
      number=3, type=14, cpp_type=8, label=1,
      has_default_value=False, default_value=1,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='ttl', full_name='spotify.mercury.proto.MercuryReply.ttl', index=3,
      number=4, type=17, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='etag', full_name='spotify.mercury.proto.MercuryReply.etag', index=4,
      number=5, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value="",
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='content_type', full_name='spotify.mercury.proto.MercuryReply.content_type', index=5,
      number=6, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value="",
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='body', full_name='spotify.mercury.proto.MercuryReply.body', index=6,
      number=7, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value="",
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
    _MERCURYREPLY_CACHEPOLICY,
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=280,
  serialized_end=539,
)

_MERCURYMULTIGETREQUEST.fields_by_name['request'].message_type = _MERCURYREQUEST
_MERCURYMULTIGETREPLY.fields_by_name['reply'].message_type = _MERCURYREPLY
_MERCURYREPLY.fields_by_name['cache_policy'].enum_type = _MERCURYREPLY_CACHEPOLICY
_MERCURYREPLY_CACHEPOLICY.containing_type = _MERCURYREPLY;
DESCRIPTOR.message_types_by_name['MercuryMultiGetRequest'] = _MERCURYMULTIGETREQUEST
DESCRIPTOR.message_types_by_name['MercuryMultiGetReply'] = _MERCURYMULTIGETREPLY
DESCRIPTOR.message_types_by_name['MercuryRequest'] = _MERCURYREQUEST
DESCRIPTOR.message_types_by_name['MercuryReply'] = _MERCURYREPLY

class MercuryMultiGetRequest(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _MERCURYMULTIGETREQUEST
  
  # @@protoc_insertion_point(class_scope:spotify.mercury.proto.MercuryMultiGetRequest)

class MercuryMultiGetReply(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _MERCURYMULTIGETREPLY
  
  # @@protoc_insertion_point(class_scope:spotify.mercury.proto.MercuryMultiGetReply)

class MercuryRequest(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _MERCURYREQUEST
  
  # @@protoc_insertion_point(class_scope:spotify.mercury.proto.MercuryRequest)

class MercuryReply(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _MERCURYREPLY
  
  # @@protoc_insertion_point(class_scope:spotify.mercury.proto.MercuryReply)

# @@protoc_insertion_point(module_scope)

########NEW FILE########
__FILENAME__ = metadata_pb2
# Generated by the protocol buffer compiler.  DO NOT EDIT!

from google.protobuf import descriptor
from google.protobuf import message
from google.protobuf import reflection
from google.protobuf import descriptor_pb2
# @@protoc_insertion_point(imports)



DESCRIPTOR = descriptor.FileDescriptor(
  name='metadata.proto',
  package='spotify.metadata.proto',
  serialized_pb='\n\x0emetadata.proto\x12\x16spotify.metadata.proto\"J\n\tTopTracks\x12\x0f\n\x07\x63ountry\x18\x01 \x01(\t\x12,\n\x05track\x18\x02 \x03(\x0b\x32\x1d.spotify.metadata.proto.Track\"F\n\x0e\x41\x63tivityPeriod\x12\x12\n\nstart_year\x18\x01 \x01(\x11\x12\x10\n\x08\x65nd_year\x18\x02 \x01(\x11\x12\x0e\n\x06\x64\x65\x63\x61\x64\x65\x18\x03 \x01(\x11\"\xb8\x05\n\x06\x41rtist\x12\x0b\n\x03gid\x18\x01 \x01(\x0c\x12\x0c\n\x04name\x18\x02 \x01(\t\x12\x12\n\npopularity\x18\x03 \x01(\x11\x12\x34\n\ttop_track\x18\x04 \x03(\x0b\x32!.spotify.metadata.proto.TopTracks\x12\x37\n\x0b\x61lbum_group\x18\x05 \x03(\x0b\x32\".spotify.metadata.proto.AlbumGroup\x12\x38\n\x0csingle_group\x18\x06 \x03(\x0b\x32\".spotify.metadata.proto.AlbumGroup\x12=\n\x11\x63ompilation_group\x18\x07 \x03(\x0b\x32\".spotify.metadata.proto.AlbumGroup\x12<\n\x10\x61ppears_on_group\x18\x08 \x03(\x0b\x32\".spotify.metadata.proto.AlbumGroup\x12\r\n\x05genre\x18\t \x03(\t\x12\x37\n\x0b\x65xternal_id\x18\n \x03(\x0b\x32\".spotify.metadata.proto.ExternalId\x12/\n\x08portrait\x18\x0b \x03(\x0b\x32\x1d.spotify.metadata.proto.Image\x12\x34\n\tbiography\x18\x0c \x03(\x0b\x32!.spotify.metadata.proto.Biography\x12?\n\x0f\x61\x63tivity_period\x18\r \x03(\x0b\x32&.spotify.metadata.proto.ActivityPeriod\x12\x38\n\x0brestriction\x18\x0e \x03(\x0b\x32#.spotify.metadata.proto.Restriction\x12/\n\x07related\x18\x0f \x03(\x0b\x32\x1e.spotify.metadata.proto.Artist\":\n\nAlbumGroup\x12,\n\x05\x61lbum\x18\x01 \x03(\x0b\x32\x1d.spotify.metadata.proto.Album\"0\n\x04\x44\x61te\x12\x0c\n\x04year\x18\x01 \x01(\x11\x12\r\n\x05month\x18\x02 \x01(\x11\x12\x0b\n\x03\x64\x61y\x18\x03 \x01(\x11\"\xd5\x04\n\x05\x41lbum\x12\x0b\n\x03gid\x18\x01 \x01(\x0c\x12\x0c\n\x04name\x18\x02 \x01(\t\x12.\n\x06\x61rtist\x18\x03 \x03(\x0b\x32\x1e.spotify.metadata.proto.Artist\x12\x30\n\x04type\x18\x04 \x01(\x0e\x32\".spotify.metadata.proto.Album.Type\x12\r\n\x05label\x18\x05 \x01(\t\x12*\n\x04\x64\x61te\x18\x06 \x01(\x0b\x32\x1c.spotify.metadata.proto.Date\x12\x12\n\npopularity\x18\x07 \x01(\x11\x12\r\n\x05genre\x18\x08 \x03(\t\x12,\n\x05\x63over\x18\t \x03(\x0b\x32\x1d.spotify.metadata.proto.Image\x12\x37\n\x0b\x65xternal_id\x18\n \x03(\x0b\x32\".spotify.metadata.proto.ExternalId\x12*\n\x04\x64isc\x18\x0b \x03(\x0b\x32\x1c.spotify.metadata.proto.Disc\x12\x0e\n\x06review\x18\x0c \x03(\t\x12\x34\n\tcopyright\x18\r \x03(\x0b\x32!.spotify.metadata.proto.Copyright\x12\x38\n\x0brestriction\x18\x0e \x03(\x0b\x32#.spotify.metadata.proto.Restriction\x12.\n\x07related\x18\x0f \x03(\x0b\x32\x1d.spotify.metadata.proto.Album\".\n\x04Type\x12\t\n\x05\x41LBUM\x10\x01\x12\n\n\x06SINGLE\x10\x02\x12\x0f\n\x0b\x43OMPILATION\x10\x03\"\xb5\x03\n\x05Track\x12\x0b\n\x03gid\x18\x01 \x01(\x0c\x12\x0c\n\x04name\x18\x02 \x01(\t\x12,\n\x05\x61lbum\x18\x03 \x01(\x0b\x32\x1d.spotify.metadata.proto.Album\x12.\n\x06\x61rtist\x18\x04 \x03(\x0b\x32\x1e.spotify.metadata.proto.Artist\x12\x0e\n\x06number\x18\x05 \x01(\x11\x12\x13\n\x0b\x64isc_number\x18\x06 \x01(\x11\x12\x10\n\x08\x64uration\x18\x07 \x01(\x11\x12\x12\n\npopularity\x18\x08 \x01(\x11\x12\x10\n\x08\x65xplicit\x18\t \x01(\x08\x12\x37\n\x0b\x65xternal_id\x18\n \x03(\x0b\x32\".spotify.metadata.proto.ExternalId\x12\x38\n\x0brestriction\x18\x0b \x03(\x0b\x32#.spotify.metadata.proto.Restriction\x12/\n\x04\x66ile\x18\x0c \x03(\x0b\x32!.spotify.metadata.proto.AudioFile\x12\x32\n\x0b\x61lternative\x18\r \x03(\x0b\x32\x1d.spotify.metadata.proto.Track\"\xa0\x01\n\x05Image\x12\x0f\n\x07\x66ile_id\x18\x01 \x01(\x0c\x12\x30\n\x04size\x18\x02 \x01(\x0e\x32\".spotify.metadata.proto.Image.Size\x12\r\n\x05width\x18\x03 \x01(\x11\x12\x0e\n\x06height\x18\x04 \x01(\x11\"5\n\x04Size\x12\x0b\n\x07\x44\x45\x46\x41ULT\x10\x00\x12\t\n\x05SMALL\x10\x01\x12\t\n\x05LARGE\x10\x02\x12\n\n\x06XLARGE\x10\x03\"J\n\tBiography\x12\x0c\n\x04text\x18\x01 \x01(\t\x12/\n\x08portrait\x18\x02 \x03(\x0b\x32\x1d.spotify.metadata.proto.Image\"R\n\x04\x44isc\x12\x0e\n\x06number\x18\x01 \x01(\x11\x12\x0c\n\x04name\x18\x02 \x01(\t\x12,\n\x05track\x18\x03 \x03(\x0b\x32\x1d.spotify.metadata.proto.Track\"e\n\tCopyright\x12\x34\n\x04type\x18\x01 \x01(\x0e\x32&.spotify.metadata.proto.Copyright.Type\x12\x0c\n\x04text\x18\x02 \x01(\t\"\x14\n\x04Type\x12\x05\n\x01P\x10\x00\x12\x05\n\x01\x43\x10\x01\"\xfd\x01\n\x0bRestriction\x12@\n\tcatalogue\x18\x01 \x03(\x0e\x32-.spotify.metadata.proto.Restriction.Catalogue\x12\x19\n\x11\x63ountries_allowed\x18\x02 \x01(\t\x12\x1b\n\x13\x63ountries_forbidden\x18\x03 \x01(\t\x12\x36\n\x04type\x18\x04 \x01(\x0e\x32(.spotify.metadata.proto.Restriction.Type\"%\n\tCatalogue\x12\x06\n\x02\x41\x44\x10\x00\x12\x10\n\x0cSUBSCRIPTION\x10\x01\"\x15\n\x04Type\x12\r\n\tSTREAMING\x10\x00\"&\n\nExternalId\x12\x0c\n\x04type\x18\x01 \x01(\t\x12\n\n\x02id\x18\x02 \x01(\t\"\xc2\x01\n\tAudioFile\x12\x0f\n\x07\x66ile_id\x18\x01 \x01(\x0c\x12\x38\n\x06\x66ormat\x18\x02 \x01(\x0e\x32(.spotify.metadata.proto.AudioFile.Format\"j\n\x06\x46ormat\x12\x11\n\rOGG_VORBIS_96\x10\x00\x12\x12\n\x0eOGG_VORBIS_160\x10\x01\x12\x12\n\x0eOGG_VORBIS_320\x10\x02\x12\x0b\n\x07MP3_256\x10\x03\x12\x0b\n\x07MP3_320\x10\x04\x12\x0b\n\x07MP3_160\x10\x05\x42(\n\x1a\x63om.spotify.metadata.protoB\x08MetadataH\x01')



_ALBUM_TYPE = descriptor.EnumDescriptor(
  name='Type',
  full_name='spotify.metadata.proto.Album.Type',
  filename=None,
  file=DESCRIPTOR,
  values=[
    descriptor.EnumValueDescriptor(
      name='ALBUM', index=0, number=1,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='SINGLE', index=1, number=2,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='COMPILATION', index=2, number=3,
      options=None,
      type=None),
  ],
  containing_type=None,
  options=None,
  serialized_start=1551,
  serialized_end=1597,
)

_IMAGE_SIZE = descriptor.EnumDescriptor(
  name='Size',
  full_name='spotify.metadata.proto.Image.Size',
  filename=None,
  file=DESCRIPTOR,
  values=[
    descriptor.EnumValueDescriptor(
      name='DEFAULT', index=0, number=0,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='SMALL', index=1, number=1,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='LARGE', index=2, number=2,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='XLARGE', index=3, number=3,
      options=None,
      type=None),
  ],
  containing_type=None,
  options=None,
  serialized_start=2147,
  serialized_end=2200,
)

_COPYRIGHT_TYPE = descriptor.EnumDescriptor(
  name='Type',
  full_name='spotify.metadata.proto.Copyright.Type',
  filename=None,
  file=DESCRIPTOR,
  values=[
    descriptor.EnumValueDescriptor(
      name='P', index=0, number=0,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='C', index=1, number=1,
      options=None,
      type=None),
  ],
  containing_type=None,
  options=None,
  serialized_start=2443,
  serialized_end=2463,
)

_RESTRICTION_CATALOGUE = descriptor.EnumDescriptor(
  name='Catalogue',
  full_name='spotify.metadata.proto.Restriction.Catalogue',
  filename=None,
  file=DESCRIPTOR,
  values=[
    descriptor.EnumValueDescriptor(
      name='AD', index=0, number=0,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='SUBSCRIPTION', index=1, number=1,
      options=None,
      type=None),
  ],
  containing_type=None,
  options=None,
  serialized_start=2659,
  serialized_end=2696,
)

_RESTRICTION_TYPE = descriptor.EnumDescriptor(
  name='Type',
  full_name='spotify.metadata.proto.Restriction.Type',
  filename=None,
  file=DESCRIPTOR,
  values=[
    descriptor.EnumValueDescriptor(
      name='STREAMING', index=0, number=0,
      options=None,
      type=None),
  ],
  containing_type=None,
  options=None,
  serialized_start=2698,
  serialized_end=2719,
)

_AUDIOFILE_FORMAT = descriptor.EnumDescriptor(
  name='Format',
  full_name='spotify.metadata.proto.AudioFile.Format',
  filename=None,
  file=DESCRIPTOR,
  values=[
    descriptor.EnumValueDescriptor(
      name='OGG_VORBIS_96', index=0, number=0,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='OGG_VORBIS_160', index=1, number=1,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='OGG_VORBIS_320', index=2, number=2,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='MP3_256', index=3, number=3,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='MP3_320', index=4, number=4,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='MP3_160', index=5, number=5,
      options=None,
      type=None),
  ],
  containing_type=None,
  options=None,
  serialized_start=2850,
  serialized_end=2956,
)


_TOPTRACKS = descriptor.Descriptor(
  name='TopTracks',
  full_name='spotify.metadata.proto.TopTracks',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='country', full_name='spotify.metadata.proto.TopTracks.country', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='track', full_name='spotify.metadata.proto.TopTracks.track', index=1,
      number=2, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=42,
  serialized_end=116,
)


_ACTIVITYPERIOD = descriptor.Descriptor(
  name='ActivityPeriod',
  full_name='spotify.metadata.proto.ActivityPeriod',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='start_year', full_name='spotify.metadata.proto.ActivityPeriod.start_year', index=0,
      number=1, type=17, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='end_year', full_name='spotify.metadata.proto.ActivityPeriod.end_year', index=1,
      number=2, type=17, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='decade', full_name='spotify.metadata.proto.ActivityPeriod.decade', index=2,
      number=3, type=17, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=118,
  serialized_end=188,
)


_ARTIST = descriptor.Descriptor(
  name='Artist',
  full_name='spotify.metadata.proto.Artist',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='gid', full_name='spotify.metadata.proto.Artist.gid', index=0,
      number=1, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value="",
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='name', full_name='spotify.metadata.proto.Artist.name', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='popularity', full_name='spotify.metadata.proto.Artist.popularity', index=2,
      number=3, type=17, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='top_track', full_name='spotify.metadata.proto.Artist.top_track', index=3,
      number=4, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='album_group', full_name='spotify.metadata.proto.Artist.album_group', index=4,
      number=5, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='single_group', full_name='spotify.metadata.proto.Artist.single_group', index=5,
      number=6, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='compilation_group', full_name='spotify.metadata.proto.Artist.compilation_group', index=6,
      number=7, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='appears_on_group', full_name='spotify.metadata.proto.Artist.appears_on_group', index=7,
      number=8, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='genre', full_name='spotify.metadata.proto.Artist.genre', index=8,
      number=9, type=9, cpp_type=9, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='external_id', full_name='spotify.metadata.proto.Artist.external_id', index=9,
      number=10, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='portrait', full_name='spotify.metadata.proto.Artist.portrait', index=10,
      number=11, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='biography', full_name='spotify.metadata.proto.Artist.biography', index=11,
      number=12, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='activity_period', full_name='spotify.metadata.proto.Artist.activity_period', index=12,
      number=13, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='restriction', full_name='spotify.metadata.proto.Artist.restriction', index=13,
      number=14, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='related', full_name='spotify.metadata.proto.Artist.related', index=14,
      number=15, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=191,
  serialized_end=887,
)


_ALBUMGROUP = descriptor.Descriptor(
  name='AlbumGroup',
  full_name='spotify.metadata.proto.AlbumGroup',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='album', full_name='spotify.metadata.proto.AlbumGroup.album', index=0,
      number=1, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=889,
  serialized_end=947,
)


_DATE = descriptor.Descriptor(
  name='Date',
  full_name='spotify.metadata.proto.Date',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='year', full_name='spotify.metadata.proto.Date.year', index=0,
      number=1, type=17, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='month', full_name='spotify.metadata.proto.Date.month', index=1,
      number=2, type=17, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='day', full_name='spotify.metadata.proto.Date.day', index=2,
      number=3, type=17, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=949,
  serialized_end=997,
)


_ALBUM = descriptor.Descriptor(
  name='Album',
  full_name='spotify.metadata.proto.Album',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='gid', full_name='spotify.metadata.proto.Album.gid', index=0,
      number=1, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value="",
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='name', full_name='spotify.metadata.proto.Album.name', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='artist', full_name='spotify.metadata.proto.Album.artist', index=2,
      number=3, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='type', full_name='spotify.metadata.proto.Album.type', index=3,
      number=4, type=14, cpp_type=8, label=1,
      has_default_value=False, default_value=1,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='label', full_name='spotify.metadata.proto.Album.label', index=4,
      number=5, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='date', full_name='spotify.metadata.proto.Album.date', index=5,
      number=6, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='popularity', full_name='spotify.metadata.proto.Album.popularity', index=6,
      number=7, type=17, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='genre', full_name='spotify.metadata.proto.Album.genre', index=7,
      number=8, type=9, cpp_type=9, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='cover', full_name='spotify.metadata.proto.Album.cover', index=8,
      number=9, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='external_id', full_name='spotify.metadata.proto.Album.external_id', index=9,
      number=10, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='disc', full_name='spotify.metadata.proto.Album.disc', index=10,
      number=11, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='review', full_name='spotify.metadata.proto.Album.review', index=11,
      number=12, type=9, cpp_type=9, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='copyright', full_name='spotify.metadata.proto.Album.copyright', index=12,
      number=13, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='restriction', full_name='spotify.metadata.proto.Album.restriction', index=13,
      number=14, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='related', full_name='spotify.metadata.proto.Album.related', index=14,
      number=15, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
    _ALBUM_TYPE,
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1000,
  serialized_end=1597,
)


_TRACK = descriptor.Descriptor(
  name='Track',
  full_name='spotify.metadata.proto.Track',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='gid', full_name='spotify.metadata.proto.Track.gid', index=0,
      number=1, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value="",
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='name', full_name='spotify.metadata.proto.Track.name', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='album', full_name='spotify.metadata.proto.Track.album', index=2,
      number=3, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='artist', full_name='spotify.metadata.proto.Track.artist', index=3,
      number=4, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='number', full_name='spotify.metadata.proto.Track.number', index=4,
      number=5, type=17, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='disc_number', full_name='spotify.metadata.proto.Track.disc_number', index=5,
      number=6, type=17, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='duration', full_name='spotify.metadata.proto.Track.duration', index=6,
      number=7, type=17, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='popularity', full_name='spotify.metadata.proto.Track.popularity', index=7,
      number=8, type=17, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='explicit', full_name='spotify.metadata.proto.Track.explicit', index=8,
      number=9, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='external_id', full_name='spotify.metadata.proto.Track.external_id', index=9,
      number=10, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='restriction', full_name='spotify.metadata.proto.Track.restriction', index=10,
      number=11, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='file', full_name='spotify.metadata.proto.Track.file', index=11,
      number=12, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='alternative', full_name='spotify.metadata.proto.Track.alternative', index=12,
      number=13, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1600,
  serialized_end=2037,
)


_IMAGE = descriptor.Descriptor(
  name='Image',
  full_name='spotify.metadata.proto.Image',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='file_id', full_name='spotify.metadata.proto.Image.file_id', index=0,
      number=1, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value="",
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='size', full_name='spotify.metadata.proto.Image.size', index=1,
      number=2, type=14, cpp_type=8, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='width', full_name='spotify.metadata.proto.Image.width', index=2,
      number=3, type=17, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='height', full_name='spotify.metadata.proto.Image.height', index=3,
      number=4, type=17, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
    _IMAGE_SIZE,
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=2040,
  serialized_end=2200,
)


_BIOGRAPHY = descriptor.Descriptor(
  name='Biography',
  full_name='spotify.metadata.proto.Biography',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='text', full_name='spotify.metadata.proto.Biography.text', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='portrait', full_name='spotify.metadata.proto.Biography.portrait', index=1,
      number=2, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=2202,
  serialized_end=2276,
)


_DISC = descriptor.Descriptor(
  name='Disc',
  full_name='spotify.metadata.proto.Disc',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='number', full_name='spotify.metadata.proto.Disc.number', index=0,
      number=1, type=17, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='name', full_name='spotify.metadata.proto.Disc.name', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='track', full_name='spotify.metadata.proto.Disc.track', index=2,
      number=3, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=2278,
  serialized_end=2360,
)


_COPYRIGHT = descriptor.Descriptor(
  name='Copyright',
  full_name='spotify.metadata.proto.Copyright',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='type', full_name='spotify.metadata.proto.Copyright.type', index=0,
      number=1, type=14, cpp_type=8, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='text', full_name='spotify.metadata.proto.Copyright.text', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
    _COPYRIGHT_TYPE,
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=2362,
  serialized_end=2463,
)


_RESTRICTION = descriptor.Descriptor(
  name='Restriction',
  full_name='spotify.metadata.proto.Restriction',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='catalogue', full_name='spotify.metadata.proto.Restriction.catalogue', index=0,
      number=1, type=14, cpp_type=8, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='countries_allowed', full_name='spotify.metadata.proto.Restriction.countries_allowed', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='countries_forbidden', full_name='spotify.metadata.proto.Restriction.countries_forbidden', index=2,
      number=3, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='type', full_name='spotify.metadata.proto.Restriction.type', index=3,
      number=4, type=14, cpp_type=8, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
    _RESTRICTION_CATALOGUE,
    _RESTRICTION_TYPE,
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=2466,
  serialized_end=2719,
)


_EXTERNALID = descriptor.Descriptor(
  name='ExternalId',
  full_name='spotify.metadata.proto.ExternalId',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='type', full_name='spotify.metadata.proto.ExternalId.type', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='id', full_name='spotify.metadata.proto.ExternalId.id', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=2721,
  serialized_end=2759,
)


_AUDIOFILE = descriptor.Descriptor(
  name='AudioFile',
  full_name='spotify.metadata.proto.AudioFile',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='file_id', full_name='spotify.metadata.proto.AudioFile.file_id', index=0,
      number=1, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value="",
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='format', full_name='spotify.metadata.proto.AudioFile.format', index=1,
      number=2, type=14, cpp_type=8, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
    _AUDIOFILE_FORMAT,
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=2762,
  serialized_end=2956,
)

_TOPTRACKS.fields_by_name['track'].message_type = _TRACK
_ARTIST.fields_by_name['top_track'].message_type = _TOPTRACKS
_ARTIST.fields_by_name['album_group'].message_type = _ALBUMGROUP
_ARTIST.fields_by_name['single_group'].message_type = _ALBUMGROUP
_ARTIST.fields_by_name['compilation_group'].message_type = _ALBUMGROUP
_ARTIST.fields_by_name['appears_on_group'].message_type = _ALBUMGROUP
_ARTIST.fields_by_name['external_id'].message_type = _EXTERNALID
_ARTIST.fields_by_name['portrait'].message_type = _IMAGE
_ARTIST.fields_by_name['biography'].message_type = _BIOGRAPHY
_ARTIST.fields_by_name['activity_period'].message_type = _ACTIVITYPERIOD
_ARTIST.fields_by_name['restriction'].message_type = _RESTRICTION
_ARTIST.fields_by_name['related'].message_type = _ARTIST
_ALBUMGROUP.fields_by_name['album'].message_type = _ALBUM
_ALBUM.fields_by_name['artist'].message_type = _ARTIST
_ALBUM.fields_by_name['type'].enum_type = _ALBUM_TYPE
_ALBUM.fields_by_name['date'].message_type = _DATE
_ALBUM.fields_by_name['cover'].message_type = _IMAGE
_ALBUM.fields_by_name['external_id'].message_type = _EXTERNALID
_ALBUM.fields_by_name['disc'].message_type = _DISC
_ALBUM.fields_by_name['copyright'].message_type = _COPYRIGHT
_ALBUM.fields_by_name['restriction'].message_type = _RESTRICTION
_ALBUM.fields_by_name['related'].message_type = _ALBUM
_ALBUM_TYPE.containing_type = _ALBUM;
_TRACK.fields_by_name['album'].message_type = _ALBUM
_TRACK.fields_by_name['artist'].message_type = _ARTIST
_TRACK.fields_by_name['external_id'].message_type = _EXTERNALID
_TRACK.fields_by_name['restriction'].message_type = _RESTRICTION
_TRACK.fields_by_name['file'].message_type = _AUDIOFILE
_TRACK.fields_by_name['alternative'].message_type = _TRACK
_IMAGE.fields_by_name['size'].enum_type = _IMAGE_SIZE
_IMAGE_SIZE.containing_type = _IMAGE;
_BIOGRAPHY.fields_by_name['portrait'].message_type = _IMAGE
_DISC.fields_by_name['track'].message_type = _TRACK
_COPYRIGHT.fields_by_name['type'].enum_type = _COPYRIGHT_TYPE
_COPYRIGHT_TYPE.containing_type = _COPYRIGHT;
_RESTRICTION.fields_by_name['catalogue'].enum_type = _RESTRICTION_CATALOGUE
_RESTRICTION.fields_by_name['type'].enum_type = _RESTRICTION_TYPE
_RESTRICTION_CATALOGUE.containing_type = _RESTRICTION;
_RESTRICTION_TYPE.containing_type = _RESTRICTION;
_AUDIOFILE.fields_by_name['format'].enum_type = _AUDIOFILE_FORMAT
_AUDIOFILE_FORMAT.containing_type = _AUDIOFILE;
DESCRIPTOR.message_types_by_name['TopTracks'] = _TOPTRACKS
DESCRIPTOR.message_types_by_name['ActivityPeriod'] = _ACTIVITYPERIOD
DESCRIPTOR.message_types_by_name['Artist'] = _ARTIST
DESCRIPTOR.message_types_by_name['AlbumGroup'] = _ALBUMGROUP
DESCRIPTOR.message_types_by_name['Date'] = _DATE
DESCRIPTOR.message_types_by_name['Album'] = _ALBUM
DESCRIPTOR.message_types_by_name['Track'] = _TRACK
DESCRIPTOR.message_types_by_name['Image'] = _IMAGE
DESCRIPTOR.message_types_by_name['Biography'] = _BIOGRAPHY
DESCRIPTOR.message_types_by_name['Disc'] = _DISC
DESCRIPTOR.message_types_by_name['Copyright'] = _COPYRIGHT
DESCRIPTOR.message_types_by_name['Restriction'] = _RESTRICTION
DESCRIPTOR.message_types_by_name['ExternalId'] = _EXTERNALID
DESCRIPTOR.message_types_by_name['AudioFile'] = _AUDIOFILE

class TopTracks(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _TOPTRACKS
  
  # @@protoc_insertion_point(class_scope:spotify.metadata.proto.TopTracks)

class ActivityPeriod(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _ACTIVITYPERIOD
  
  # @@protoc_insertion_point(class_scope:spotify.metadata.proto.ActivityPeriod)

class Artist(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _ARTIST
  
  # @@protoc_insertion_point(class_scope:spotify.metadata.proto.Artist)

class AlbumGroup(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _ALBUMGROUP
  
  # @@protoc_insertion_point(class_scope:spotify.metadata.proto.AlbumGroup)

class Date(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _DATE
  
  # @@protoc_insertion_point(class_scope:spotify.metadata.proto.Date)

class Album(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _ALBUM
  
  # @@protoc_insertion_point(class_scope:spotify.metadata.proto.Album)

class Track(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _TRACK
  
  # @@protoc_insertion_point(class_scope:spotify.metadata.proto.Track)

class Image(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _IMAGE
  
  # @@protoc_insertion_point(class_scope:spotify.metadata.proto.Image)

class Biography(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _BIOGRAPHY
  
  # @@protoc_insertion_point(class_scope:spotify.metadata.proto.Biography)

class Disc(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _DISC
  
  # @@protoc_insertion_point(class_scope:spotify.metadata.proto.Disc)

class Copyright(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _COPYRIGHT
  
  # @@protoc_insertion_point(class_scope:spotify.metadata.proto.Copyright)

class Restriction(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _RESTRICTION
  
  # @@protoc_insertion_point(class_scope:spotify.metadata.proto.Restriction)

class ExternalId(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _EXTERNALID
  
  # @@protoc_insertion_point(class_scope:spotify.metadata.proto.ExternalId)

class AudioFile(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _AUDIOFILE
  
  # @@protoc_insertion_point(class_scope:spotify.metadata.proto.AudioFile)

# @@protoc_insertion_point(module_scope)

########NEW FILE########
__FILENAME__ = playlist4changes_pb2
# Generated by the protocol buffer compiler.  DO NOT EDIT!

from google.protobuf import descriptor
from google.protobuf import message
from google.protobuf import reflection
from google.protobuf import descriptor_pb2
# @@protoc_insertion_point(imports)


import playlist4content_pb2
import playlist4issues_pb2
import playlist4meta_pb2
import playlist4ops_pb2

DESCRIPTOR = descriptor.FileDescriptor(
  name='playlist4changes.proto',
  package='spotify.playlist4.proto',
  serialized_pb='\n\x16playlist4changes.proto\x12\x17spotify.playlist4.proto\x1a\x16playlist4content.proto\x1a\x15playlist4issues.proto\x1a\x13playlist4meta.proto\x1a\x12playlist4ops.proto\"\x8e\x01\n\nChangeInfo\x12\x0c\n\x04user\x18\x01 \x01(\t\x12\x11\n\ttimestamp\x18\x02 \x01(\x05\x12\r\n\x05\x61\x64min\x18\x03 \x01(\x08\x12\x0c\n\x04undo\x18\x04 \x01(\x08\x12\x0c\n\x04redo\x18\x05 \x01(\x08\x12\r\n\x05merge\x18\x06 \x01(\x08\x12\x12\n\ncompressed\x18\x07 \x01(\x08\x12\x11\n\tmigration\x18\x08 \x01(\x08\"z\n\x05\x44\x65lta\x12\x14\n\x0c\x62\x61se_version\x18\x01 \x01(\x0c\x12(\n\x03ops\x18\x02 \x03(\x0b\x32\x1b.spotify.playlist4.proto.Op\x12\x31\n\x04info\x18\x04 \x01(\x0b\x32#.spotify.playlist4.proto.ChangeInfo\"g\n\x05Merge\x12\x14\n\x0c\x62\x61se_version\x18\x01 \x01(\x0c\x12\x15\n\rmerge_version\x18\x02 \x01(\x0c\x12\x31\n\x04info\x18\x04 \x01(\x0b\x32#.spotify.playlist4.proto.ChangeInfo\"\xd0\x01\n\tChangeSet\x12\x35\n\x04kind\x18\x01 \x02(\x0e\x32\'.spotify.playlist4.proto.ChangeSet.Kind\x12-\n\x05\x64\x65lta\x18\x02 \x01(\x0b\x32\x1e.spotify.playlist4.proto.Delta\x12-\n\x05merge\x18\x03 \x01(\x0b\x32\x1e.spotify.playlist4.proto.Merge\".\n\x04Kind\x12\x10\n\x0cKIND_UNKNOWN\x10\x00\x12\t\n\x05\x44\x45LTA\x10\x02\x12\t\n\x05MERGE\x10\x03\"c\n\x17RevisionTaggedChangeSet\x12\x10\n\x08revision\x18\x01 \x02(\x0c\x12\x36\n\nchange_set\x18\x02 \x02(\x0b\x32\".spotify.playlist4.proto.ChangeSet\"\\\n\x04\x44iff\x12\x15\n\rfrom_revision\x18\x01 \x02(\x0c\x12(\n\x03ops\x18\x02 \x03(\x0b\x32\x1b.spotify.playlist4.proto.Op\x12\x13\n\x0bto_revision\x18\x03 \x02(\x0c\"\x95\x02\n\x08ListDump\x12\x16\n\x0elatestRevision\x18\x01 \x01(\x0c\x12\x0e\n\x06length\x18\x02 \x01(\x05\x12;\n\nattributes\x18\x03 \x01(\x0b\x32\'.spotify.playlist4.proto.ListAttributes\x12\x37\n\x08\x63hecksum\x18\x04 \x01(\x0b\x32%.spotify.playlist4.proto.ListChecksum\x12\x34\n\x08\x63ontents\x18\x05 \x01(\x0b\x32\".spotify.playlist4.proto.ListItems\x12\x35\n\rpendingDeltas\x18\x07 \x03(\x0b\x32\x1e.spotify.playlist4.proto.Delta\"\xcc\x01\n\x0bListChanges\x12\x14\n\x0c\x62\x61seRevision\x18\x01 \x01(\x0c\x12.\n\x06\x64\x65ltas\x18\x02 \x03(\x0b\x32\x1e.spotify.playlist4.proto.Delta\x12\x1e\n\x16wantResultingRevisions\x18\x03 \x01(\x08\x12\x16\n\x0ewantSyncResult\x18\x04 \x01(\x08\x12/\n\x04\x64ump\x18\x05 \x01(\x0b\x32!.spotify.playlist4.proto.ListDump\x12\x0e\n\x06nonces\x18\x06 \x03(\x05\"\x93\x04\n\x13SelectedListContent\x12\x10\n\x08revision\x18\x01 \x01(\x0c\x12\x0e\n\x06length\x18\x02 \x01(\x05\x12;\n\nattributes\x18\x03 \x01(\x0b\x32\'.spotify.playlist4.proto.ListAttributes\x12\x37\n\x08\x63hecksum\x18\x04 \x01(\x0b\x32%.spotify.playlist4.proto.ListChecksum\x12\x34\n\x08\x63ontents\x18\x05 \x01(\x0b\x32\".spotify.playlist4.proto.ListItems\x12+\n\x04\x64iff\x18\x06 \x01(\x0b\x32\x1d.spotify.playlist4.proto.Diff\x12\x31\n\nsyncResult\x18\x07 \x01(\x0b\x32\x1d.spotify.playlist4.proto.Diff\x12\x1a\n\x12resultingRevisions\x18\x08 \x03(\x0c\x12\x15\n\rmultipleHeads\x18\t \x01(\x08\x12\x10\n\x08upToDate\x18\n \x01(\x08\x12\x43\n\rresolveAction\x18\x0c \x03(\x0b\x32,.spotify.playlist4.proto.ClientResolveAction\x12\x34\n\x06issues\x18\r \x03(\x0b\x32$.spotify.playlist4.proto.ClientIssue\x12\x0e\n\x06nonces\x18\x0e \x03(\x05\x42\x1f\n\x1b\x63om.spotify.playlist4.protoH\x01')



_CHANGESET_KIND = descriptor.EnumDescriptor(
  name='Kind',
  full_name='spotify.playlist4.proto.ChangeSet.Kind',
  filename=None,
  file=DESCRIPTOR,
  values=[
    descriptor.EnumValueDescriptor(
      name='KIND_UNKNOWN', index=0, number=0,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='DELTA', index=1, number=2,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='MERGE', index=2, number=3,
      options=None,
      type=None),
  ],
  containing_type=None,
  options=None,
  serialized_start=676,
  serialized_end=722,
)


_CHANGEINFO = descriptor.Descriptor(
  name='ChangeInfo',
  full_name='spotify.playlist4.proto.ChangeInfo',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='user', full_name='spotify.playlist4.proto.ChangeInfo.user', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='timestamp', full_name='spotify.playlist4.proto.ChangeInfo.timestamp', index=1,
      number=2, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='admin', full_name='spotify.playlist4.proto.ChangeInfo.admin', index=2,
      number=3, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='undo', full_name='spotify.playlist4.proto.ChangeInfo.undo', index=3,
      number=4, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='redo', full_name='spotify.playlist4.proto.ChangeInfo.redo', index=4,
      number=5, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='merge', full_name='spotify.playlist4.proto.ChangeInfo.merge', index=5,
      number=6, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='compressed', full_name='spotify.playlist4.proto.ChangeInfo.compressed', index=6,
      number=7, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='migration', full_name='spotify.playlist4.proto.ChangeInfo.migration', index=7,
      number=8, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=140,
  serialized_end=282,
)


_DELTA = descriptor.Descriptor(
  name='Delta',
  full_name='spotify.playlist4.proto.Delta',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='base_version', full_name='spotify.playlist4.proto.Delta.base_version', index=0,
      number=1, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value="",
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='ops', full_name='spotify.playlist4.proto.Delta.ops', index=1,
      number=2, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='info', full_name='spotify.playlist4.proto.Delta.info', index=2,
      number=4, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=284,
  serialized_end=406,
)


_MERGE = descriptor.Descriptor(
  name='Merge',
  full_name='spotify.playlist4.proto.Merge',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='base_version', full_name='spotify.playlist4.proto.Merge.base_version', index=0,
      number=1, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value="",
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='merge_version', full_name='spotify.playlist4.proto.Merge.merge_version', index=1,
      number=2, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value="",
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='info', full_name='spotify.playlist4.proto.Merge.info', index=2,
      number=4, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=408,
  serialized_end=511,
)


_CHANGESET = descriptor.Descriptor(
  name='ChangeSet',
  full_name='spotify.playlist4.proto.ChangeSet',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='kind', full_name='spotify.playlist4.proto.ChangeSet.kind', index=0,
      number=1, type=14, cpp_type=8, label=2,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='delta', full_name='spotify.playlist4.proto.ChangeSet.delta', index=1,
      number=2, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='merge', full_name='spotify.playlist4.proto.ChangeSet.merge', index=2,
      number=3, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
    _CHANGESET_KIND,
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=514,
  serialized_end=722,
)


_REVISIONTAGGEDCHANGESET = descriptor.Descriptor(
  name='RevisionTaggedChangeSet',
  full_name='spotify.playlist4.proto.RevisionTaggedChangeSet',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='revision', full_name='spotify.playlist4.proto.RevisionTaggedChangeSet.revision', index=0,
      number=1, type=12, cpp_type=9, label=2,
      has_default_value=False, default_value="",
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='change_set', full_name='spotify.playlist4.proto.RevisionTaggedChangeSet.change_set', index=1,
      number=2, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=724,
  serialized_end=823,
)


_DIFF = descriptor.Descriptor(
  name='Diff',
  full_name='spotify.playlist4.proto.Diff',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='from_revision', full_name='spotify.playlist4.proto.Diff.from_revision', index=0,
      number=1, type=12, cpp_type=9, label=2,
      has_default_value=False, default_value="",
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='ops', full_name='spotify.playlist4.proto.Diff.ops', index=1,
      number=2, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='to_revision', full_name='spotify.playlist4.proto.Diff.to_revision', index=2,
      number=3, type=12, cpp_type=9, label=2,
      has_default_value=False, default_value="",
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=825,
  serialized_end=917,
)


_LISTDUMP = descriptor.Descriptor(
  name='ListDump',
  full_name='spotify.playlist4.proto.ListDump',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='latestRevision', full_name='spotify.playlist4.proto.ListDump.latestRevision', index=0,
      number=1, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value="",
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='length', full_name='spotify.playlist4.proto.ListDump.length', index=1,
      number=2, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='attributes', full_name='spotify.playlist4.proto.ListDump.attributes', index=2,
      number=3, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='checksum', full_name='spotify.playlist4.proto.ListDump.checksum', index=3,
      number=4, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='contents', full_name='spotify.playlist4.proto.ListDump.contents', index=4,
      number=5, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='pendingDeltas', full_name='spotify.playlist4.proto.ListDump.pendingDeltas', index=5,
      number=7, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=920,
  serialized_end=1197,
)


_LISTCHANGES = descriptor.Descriptor(
  name='ListChanges',
  full_name='spotify.playlist4.proto.ListChanges',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='baseRevision', full_name='spotify.playlist4.proto.ListChanges.baseRevision', index=0,
      number=1, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value="",
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='deltas', full_name='spotify.playlist4.proto.ListChanges.deltas', index=1,
      number=2, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='wantResultingRevisions', full_name='spotify.playlist4.proto.ListChanges.wantResultingRevisions', index=2,
      number=3, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='wantSyncResult', full_name='spotify.playlist4.proto.ListChanges.wantSyncResult', index=3,
      number=4, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='dump', full_name='spotify.playlist4.proto.ListChanges.dump', index=4,
      number=5, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='nonces', full_name='spotify.playlist4.proto.ListChanges.nonces', index=5,
      number=6, type=5, cpp_type=1, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1200,
  serialized_end=1404,
)


_SELECTEDLISTCONTENT = descriptor.Descriptor(
  name='SelectedListContent',
  full_name='spotify.playlist4.proto.SelectedListContent',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='revision', full_name='spotify.playlist4.proto.SelectedListContent.revision', index=0,
      number=1, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value="",
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='length', full_name='spotify.playlist4.proto.SelectedListContent.length', index=1,
      number=2, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='attributes', full_name='spotify.playlist4.proto.SelectedListContent.attributes', index=2,
      number=3, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='checksum', full_name='spotify.playlist4.proto.SelectedListContent.checksum', index=3,
      number=4, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='contents', full_name='spotify.playlist4.proto.SelectedListContent.contents', index=4,
      number=5, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='diff', full_name='spotify.playlist4.proto.SelectedListContent.diff', index=5,
      number=6, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='syncResult', full_name='spotify.playlist4.proto.SelectedListContent.syncResult', index=6,
      number=7, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='resultingRevisions', full_name='spotify.playlist4.proto.SelectedListContent.resultingRevisions', index=7,
      number=8, type=12, cpp_type=9, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='multipleHeads', full_name='spotify.playlist4.proto.SelectedListContent.multipleHeads', index=8,
      number=9, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='upToDate', full_name='spotify.playlist4.proto.SelectedListContent.upToDate', index=9,
      number=10, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='resolveAction', full_name='spotify.playlist4.proto.SelectedListContent.resolveAction', index=10,
      number=12, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='issues', full_name='spotify.playlist4.proto.SelectedListContent.issues', index=11,
      number=13, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='nonces', full_name='spotify.playlist4.proto.SelectedListContent.nonces', index=12,
      number=14, type=5, cpp_type=1, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1407,
  serialized_end=1938,
)

_DELTA.fields_by_name['ops'].message_type = playlist4ops_pb2._OP
_DELTA.fields_by_name['info'].message_type = _CHANGEINFO
_MERGE.fields_by_name['info'].message_type = _CHANGEINFO
_CHANGESET.fields_by_name['kind'].enum_type = _CHANGESET_KIND
_CHANGESET.fields_by_name['delta'].message_type = _DELTA
_CHANGESET.fields_by_name['merge'].message_type = _MERGE
_CHANGESET_KIND.containing_type = _CHANGESET;
_REVISIONTAGGEDCHANGESET.fields_by_name['change_set'].message_type = _CHANGESET
_DIFF.fields_by_name['ops'].message_type = playlist4ops_pb2._OP
_LISTDUMP.fields_by_name['attributes'].message_type = playlist4meta_pb2._LISTATTRIBUTES
_LISTDUMP.fields_by_name['checksum'].message_type = playlist4meta_pb2._LISTCHECKSUM
_LISTDUMP.fields_by_name['contents'].message_type = playlist4content_pb2._LISTITEMS
_LISTDUMP.fields_by_name['pendingDeltas'].message_type = _DELTA
_LISTCHANGES.fields_by_name['deltas'].message_type = _DELTA
_LISTCHANGES.fields_by_name['dump'].message_type = _LISTDUMP
_SELECTEDLISTCONTENT.fields_by_name['attributes'].message_type = playlist4meta_pb2._LISTATTRIBUTES
_SELECTEDLISTCONTENT.fields_by_name['checksum'].message_type = playlist4meta_pb2._LISTCHECKSUM
_SELECTEDLISTCONTENT.fields_by_name['contents'].message_type = playlist4content_pb2._LISTITEMS
_SELECTEDLISTCONTENT.fields_by_name['diff'].message_type = _DIFF
_SELECTEDLISTCONTENT.fields_by_name['syncResult'].message_type = _DIFF
_SELECTEDLISTCONTENT.fields_by_name['resolveAction'].message_type = playlist4issues_pb2._CLIENTRESOLVEACTION
_SELECTEDLISTCONTENT.fields_by_name['issues'].message_type = playlist4issues_pb2._CLIENTISSUE
DESCRIPTOR.message_types_by_name['ChangeInfo'] = _CHANGEINFO
DESCRIPTOR.message_types_by_name['Delta'] = _DELTA
DESCRIPTOR.message_types_by_name['Merge'] = _MERGE
DESCRIPTOR.message_types_by_name['ChangeSet'] = _CHANGESET
DESCRIPTOR.message_types_by_name['RevisionTaggedChangeSet'] = _REVISIONTAGGEDCHANGESET
DESCRIPTOR.message_types_by_name['Diff'] = _DIFF
DESCRIPTOR.message_types_by_name['ListDump'] = _LISTDUMP
DESCRIPTOR.message_types_by_name['ListChanges'] = _LISTCHANGES
DESCRIPTOR.message_types_by_name['SelectedListContent'] = _SELECTEDLISTCONTENT

class ChangeInfo(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CHANGEINFO
  
  # @@protoc_insertion_point(class_scope:spotify.playlist4.proto.ChangeInfo)

class Delta(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _DELTA
  
  # @@protoc_insertion_point(class_scope:spotify.playlist4.proto.Delta)

class Merge(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _MERGE
  
  # @@protoc_insertion_point(class_scope:spotify.playlist4.proto.Merge)

class ChangeSet(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CHANGESET
  
  # @@protoc_insertion_point(class_scope:spotify.playlist4.proto.ChangeSet)

class RevisionTaggedChangeSet(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _REVISIONTAGGEDCHANGESET
  
  # @@protoc_insertion_point(class_scope:spotify.playlist4.proto.RevisionTaggedChangeSet)

class Diff(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _DIFF
  
  # @@protoc_insertion_point(class_scope:spotify.playlist4.proto.Diff)

class ListDump(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _LISTDUMP
  
  # @@protoc_insertion_point(class_scope:spotify.playlist4.proto.ListDump)

class ListChanges(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _LISTCHANGES
  
  # @@protoc_insertion_point(class_scope:spotify.playlist4.proto.ListChanges)

class SelectedListContent(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _SELECTEDLISTCONTENT
  
  # @@protoc_insertion_point(class_scope:spotify.playlist4.proto.SelectedListContent)

# @@protoc_insertion_point(module_scope)

########NEW FILE########
__FILENAME__ = playlist4content_pb2
# Generated by the protocol buffer compiler.  DO NOT EDIT!

from google.protobuf import descriptor
from google.protobuf import message
from google.protobuf import reflection
from google.protobuf import descriptor_pb2
# @@protoc_insertion_point(imports)


import playlist4meta_pb2
import playlist4issues_pb2

DESCRIPTOR = descriptor.FileDescriptor(
  name='playlist4content.proto',
  package='spotify.playlist4.proto',
  serialized_pb='\n\x16playlist4content.proto\x12\x17spotify.playlist4.proto\x1a\x13playlist4meta.proto\x1a\x15playlist4issues.proto\"P\n\x04Item\x12\x0b\n\x03uri\x18\x01 \x02(\t\x12;\n\nattributes\x18\x02 \x01(\x0b\x32\'.spotify.playlist4.proto.ItemAttributes\"Y\n\tListItems\x12\x0b\n\x03pos\x18\x01 \x02(\x05\x12\x11\n\ttruncated\x18\x02 \x02(\x08\x12,\n\x05items\x18\x03 \x03(\x0b\x32\x1d.spotify.playlist4.proto.Item\"+\n\x0c\x43ontentRange\x12\x0b\n\x03pos\x18\x01 \x02(\x05\x12\x0e\n\x06length\x18\x02 \x01(\x05\"\xb3\x03\n\x14ListContentSelection\x12\x14\n\x0cwantRevision\x18\x01 \x01(\x08\x12\x12\n\nwantLength\x18\x02 \x01(\x08\x12\x16\n\x0ewantAttributes\x18\x03 \x01(\x08\x12\x14\n\x0cwantChecksum\x18\x04 \x01(\x08\x12\x13\n\x0bwantContent\x18\x05 \x01(\x08\x12;\n\x0c\x63ontentRange\x18\x06 \x01(\x0b\x32%.spotify.playlist4.proto.ContentRange\x12\x10\n\x08wantDiff\x18\x07 \x01(\x08\x12\x14\n\x0c\x62\x61seRevision\x18\x08 \x01(\x0c\x12\x14\n\x0chintRevision\x18\t \x01(\x0c\x12\x1d\n\x15wantNothingIfUpToDate\x18\n \x01(\x08\x12\x19\n\x11wantResolveAction\x18\x0c \x01(\x08\x12\x34\n\x06issues\x18\r \x03(\x0b\x32$.spotify.playlist4.proto.ClientIssue\x12\x43\n\rresolveAction\x18\x0e \x03(\x0b\x32,.spotify.playlist4.proto.ClientResolveActionB\x1f\n\x1b\x63om.spotify.playlist4.protoH\x01')




_ITEM = descriptor.Descriptor(
  name='Item',
  full_name='spotify.playlist4.proto.Item',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='uri', full_name='spotify.playlist4.proto.Item.uri', index=0,
      number=1, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='attributes', full_name='spotify.playlist4.proto.Item.attributes', index=1,
      number=2, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=95,
  serialized_end=175,
)


_LISTITEMS = descriptor.Descriptor(
  name='ListItems',
  full_name='spotify.playlist4.proto.ListItems',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='pos', full_name='spotify.playlist4.proto.ListItems.pos', index=0,
      number=1, type=5, cpp_type=1, label=2,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='truncated', full_name='spotify.playlist4.proto.ListItems.truncated', index=1,
      number=2, type=8, cpp_type=7, label=2,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='items', full_name='spotify.playlist4.proto.ListItems.items', index=2,
      number=3, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=177,
  serialized_end=266,
)


_CONTENTRANGE = descriptor.Descriptor(
  name='ContentRange',
  full_name='spotify.playlist4.proto.ContentRange',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='pos', full_name='spotify.playlist4.proto.ContentRange.pos', index=0,
      number=1, type=5, cpp_type=1, label=2,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='length', full_name='spotify.playlist4.proto.ContentRange.length', index=1,
      number=2, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=268,
  serialized_end=311,
)


_LISTCONTENTSELECTION = descriptor.Descriptor(
  name='ListContentSelection',
  full_name='spotify.playlist4.proto.ListContentSelection',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='wantRevision', full_name='spotify.playlist4.proto.ListContentSelection.wantRevision', index=0,
      number=1, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='wantLength', full_name='spotify.playlist4.proto.ListContentSelection.wantLength', index=1,
      number=2, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='wantAttributes', full_name='spotify.playlist4.proto.ListContentSelection.wantAttributes', index=2,
      number=3, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='wantChecksum', full_name='spotify.playlist4.proto.ListContentSelection.wantChecksum', index=3,
      number=4, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='wantContent', full_name='spotify.playlist4.proto.ListContentSelection.wantContent', index=4,
      number=5, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='contentRange', full_name='spotify.playlist4.proto.ListContentSelection.contentRange', index=5,
      number=6, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='wantDiff', full_name='spotify.playlist4.proto.ListContentSelection.wantDiff', index=6,
      number=7, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='baseRevision', full_name='spotify.playlist4.proto.ListContentSelection.baseRevision', index=7,
      number=8, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value="",
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='hintRevision', full_name='spotify.playlist4.proto.ListContentSelection.hintRevision', index=8,
      number=9, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value="",
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='wantNothingIfUpToDate', full_name='spotify.playlist4.proto.ListContentSelection.wantNothingIfUpToDate', index=9,
      number=10, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='wantResolveAction', full_name='spotify.playlist4.proto.ListContentSelection.wantResolveAction', index=10,
      number=12, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='issues', full_name='spotify.playlist4.proto.ListContentSelection.issues', index=11,
      number=13, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='resolveAction', full_name='spotify.playlist4.proto.ListContentSelection.resolveAction', index=12,
      number=14, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=314,
  serialized_end=749,
)

_ITEM.fields_by_name['attributes'].message_type = playlist4meta_pb2._ITEMATTRIBUTES
_LISTITEMS.fields_by_name['items'].message_type = _ITEM
_LISTCONTENTSELECTION.fields_by_name['contentRange'].message_type = _CONTENTRANGE
_LISTCONTENTSELECTION.fields_by_name['issues'].message_type = playlist4issues_pb2._CLIENTISSUE
_LISTCONTENTSELECTION.fields_by_name['resolveAction'].message_type = playlist4issues_pb2._CLIENTRESOLVEACTION
DESCRIPTOR.message_types_by_name['Item'] = _ITEM
DESCRIPTOR.message_types_by_name['ListItems'] = _LISTITEMS
DESCRIPTOR.message_types_by_name['ContentRange'] = _CONTENTRANGE
DESCRIPTOR.message_types_by_name['ListContentSelection'] = _LISTCONTENTSELECTION

class Item(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _ITEM
  
  # @@protoc_insertion_point(class_scope:spotify.playlist4.proto.Item)

class ListItems(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _LISTITEMS
  
  # @@protoc_insertion_point(class_scope:spotify.playlist4.proto.ListItems)

class ContentRange(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CONTENTRANGE
  
  # @@protoc_insertion_point(class_scope:spotify.playlist4.proto.ContentRange)

class ListContentSelection(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _LISTCONTENTSELECTION
  
  # @@protoc_insertion_point(class_scope:spotify.playlist4.proto.ListContentSelection)

# @@protoc_insertion_point(module_scope)

########NEW FILE########
__FILENAME__ = playlist4issues_pb2
# Generated by the protocol buffer compiler.  DO NOT EDIT!

from google.protobuf import descriptor
from google.protobuf import message
from google.protobuf import reflection
from google.protobuf import descriptor_pb2
# @@protoc_insertion_point(imports)



DESCRIPTOR = descriptor.FileDescriptor(
  name='playlist4issues.proto',
  package='spotify.playlist4.proto',
  serialized_pb='\n\x15playlist4issues.proto\x12\x17spotify.playlist4.proto\"\xaa\x03\n\x0b\x43lientIssue\x12\x39\n\x05level\x18\x01 \x01(\x0e\x32*.spotify.playlist4.proto.ClientIssue.Level\x12\x37\n\x04\x63ode\x18\x02 \x01(\x0e\x32).spotify.playlist4.proto.ClientIssue.Code\x12\x13\n\x0brepeatCount\x18\x03 \x01(\x05\"q\n\x05Level\x12\x11\n\rLEVEL_UNKNOWN\x10\x00\x12\x0f\n\x0bLEVEL_DEBUG\x10\x01\x12\x0e\n\nLEVEL_INFO\x10\x02\x12\x10\n\x0cLEVEL_NOTICE\x10\x03\x12\x11\n\rLEVEL_WARNING\x10\x04\x12\x0f\n\x0bLEVEL_ERROR\x10\x05\"\x9e\x01\n\x04\x43ode\x12\x10\n\x0c\x43ODE_UNKNOWN\x10\x00\x12\x1c\n\x18\x43ODE_INDEX_OUT_OF_BOUNDS\x10\x01\x12\x19\n\x15\x43ODE_VERSION_MISMATCH\x10\x02\x12\x16\n\x12\x43ODE_CACHED_CHANGE\x10\x03\x12\x17\n\x13\x43ODE_OFFLINE_CHANGE\x10\x04\x12\x1a\n\x16\x43ODE_CONCURRENT_CHANGE\x10\x05\"\x95\x03\n\x13\x43lientResolveAction\x12?\n\x04\x63ode\x18\x01 \x01(\x0e\x32\x31.spotify.playlist4.proto.ClientResolveAction.Code\x12I\n\tinitiator\x18\x02 \x01(\x0e\x32\x36.spotify.playlist4.proto.ClientResolveAction.Initiator\"\xa1\x01\n\x04\x43ode\x12\x10\n\x0c\x43ODE_UNKNOWN\x10\x00\x12\x12\n\x0e\x43ODE_NO_ACTION\x10\x01\x12\x0e\n\nCODE_RETRY\x10\x02\x12\x0f\n\x0b\x43ODE_RELOAD\x10\x03\x12\x1e\n\x1a\x43ODE_DISCARD_LOCAL_CHANGES\x10\x04\x12\x12\n\x0e\x43ODE_SEND_DUMP\x10\x05\x12\x1e\n\x1a\x43ODE_DISPLAY_ERROR_MESSAGE\x10\x06\"N\n\tInitiator\x12\x15\n\x11INITIATOR_UNKNOWN\x10\x00\x12\x14\n\x10INITIATOR_SERVER\x10\x01\x12\x14\n\x10INITIATOR_CLIENT\x10\x02\x42\x1f\n\x1b\x63om.spotify.playlist4.protoH\x01')



_CLIENTISSUE_LEVEL = descriptor.EnumDescriptor(
  name='Level',
  full_name='spotify.playlist4.proto.ClientIssue.Level',
  filename=None,
  file=DESCRIPTOR,
  values=[
    descriptor.EnumValueDescriptor(
      name='LEVEL_UNKNOWN', index=0, number=0,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='LEVEL_DEBUG', index=1, number=1,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='LEVEL_INFO', index=2, number=2,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='LEVEL_NOTICE', index=3, number=3,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='LEVEL_WARNING', index=4, number=4,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='LEVEL_ERROR', index=5, number=5,
      options=None,
      type=None),
  ],
  containing_type=None,
  options=None,
  serialized_start=203,
  serialized_end=316,
)

_CLIENTISSUE_CODE = descriptor.EnumDescriptor(
  name='Code',
  full_name='spotify.playlist4.proto.ClientIssue.Code',
  filename=None,
  file=DESCRIPTOR,
  values=[
    descriptor.EnumValueDescriptor(
      name='CODE_UNKNOWN', index=0, number=0,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='CODE_INDEX_OUT_OF_BOUNDS', index=1, number=1,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='CODE_VERSION_MISMATCH', index=2, number=2,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='CODE_CACHED_CHANGE', index=3, number=3,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='CODE_OFFLINE_CHANGE', index=4, number=4,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='CODE_CONCURRENT_CHANGE', index=5, number=5,
      options=None,
      type=None),
  ],
  containing_type=None,
  options=None,
  serialized_start=319,
  serialized_end=477,
)

_CLIENTRESOLVEACTION_CODE = descriptor.EnumDescriptor(
  name='Code',
  full_name='spotify.playlist4.proto.ClientResolveAction.Code',
  filename=None,
  file=DESCRIPTOR,
  values=[
    descriptor.EnumValueDescriptor(
      name='CODE_UNKNOWN', index=0, number=0,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='CODE_NO_ACTION', index=1, number=1,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='CODE_RETRY', index=2, number=2,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='CODE_RELOAD', index=3, number=3,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='CODE_DISCARD_LOCAL_CHANGES', index=4, number=4,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='CODE_SEND_DUMP', index=5, number=5,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='CODE_DISPLAY_ERROR_MESSAGE', index=6, number=6,
      options=None,
      type=None),
  ],
  containing_type=None,
  options=None,
  serialized_start=644,
  serialized_end=805,
)

_CLIENTRESOLVEACTION_INITIATOR = descriptor.EnumDescriptor(
  name='Initiator',
  full_name='spotify.playlist4.proto.ClientResolveAction.Initiator',
  filename=None,
  file=DESCRIPTOR,
  values=[
    descriptor.EnumValueDescriptor(
      name='INITIATOR_UNKNOWN', index=0, number=0,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='INITIATOR_SERVER', index=1, number=1,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='INITIATOR_CLIENT', index=2, number=2,
      options=None,
      type=None),
  ],
  containing_type=None,
  options=None,
  serialized_start=807,
  serialized_end=885,
)


_CLIENTISSUE = descriptor.Descriptor(
  name='ClientIssue',
  full_name='spotify.playlist4.proto.ClientIssue',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='level', full_name='spotify.playlist4.proto.ClientIssue.level', index=0,
      number=1, type=14, cpp_type=8, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='code', full_name='spotify.playlist4.proto.ClientIssue.code', index=1,
      number=2, type=14, cpp_type=8, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='repeatCount', full_name='spotify.playlist4.proto.ClientIssue.repeatCount', index=2,
      number=3, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
    _CLIENTISSUE_LEVEL,
    _CLIENTISSUE_CODE,
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=51,
  serialized_end=477,
)


_CLIENTRESOLVEACTION = descriptor.Descriptor(
  name='ClientResolveAction',
  full_name='spotify.playlist4.proto.ClientResolveAction',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='code', full_name='spotify.playlist4.proto.ClientResolveAction.code', index=0,
      number=1, type=14, cpp_type=8, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='initiator', full_name='spotify.playlist4.proto.ClientResolveAction.initiator', index=1,
      number=2, type=14, cpp_type=8, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
    _CLIENTRESOLVEACTION_CODE,
    _CLIENTRESOLVEACTION_INITIATOR,
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=480,
  serialized_end=885,
)

_CLIENTISSUE.fields_by_name['level'].enum_type = _CLIENTISSUE_LEVEL
_CLIENTISSUE.fields_by_name['code'].enum_type = _CLIENTISSUE_CODE
_CLIENTISSUE_LEVEL.containing_type = _CLIENTISSUE;
_CLIENTISSUE_CODE.containing_type = _CLIENTISSUE;
_CLIENTRESOLVEACTION.fields_by_name['code'].enum_type = _CLIENTRESOLVEACTION_CODE
_CLIENTRESOLVEACTION.fields_by_name['initiator'].enum_type = _CLIENTRESOLVEACTION_INITIATOR
_CLIENTRESOLVEACTION_CODE.containing_type = _CLIENTRESOLVEACTION;
_CLIENTRESOLVEACTION_INITIATOR.containing_type = _CLIENTRESOLVEACTION;
DESCRIPTOR.message_types_by_name['ClientIssue'] = _CLIENTISSUE
DESCRIPTOR.message_types_by_name['ClientResolveAction'] = _CLIENTRESOLVEACTION

class ClientIssue(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CLIENTISSUE
  
  # @@protoc_insertion_point(class_scope:spotify.playlist4.proto.ClientIssue)

class ClientResolveAction(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CLIENTRESOLVEACTION
  
  # @@protoc_insertion_point(class_scope:spotify.playlist4.proto.ClientResolveAction)

# @@protoc_insertion_point(module_scope)

########NEW FILE########
__FILENAME__ = playlist4meta_pb2
# Generated by the protocol buffer compiler.  DO NOT EDIT!

from google.protobuf import descriptor
from google.protobuf import message
from google.protobuf import reflection
from google.protobuf import descriptor_pb2
# @@protoc_insertion_point(imports)



DESCRIPTOR = descriptor.FileDescriptor(
  name='playlist4meta.proto',
  package='spotify.playlist4.proto',
  serialized_pb='\n\x13playlist4meta.proto\x12\x17spotify.playlist4.proto\"-\n\x0cListChecksum\x12\x0f\n\x07version\x18\x01 \x02(\x05\x12\x0c\n\x04sha1\x18\x04 \x01(\x0c\"\x98\x01\n\x0e\x44ownloadFormat\x12<\n\x05\x63odec\x18\x01 \x02(\x0e\x32-.spotify.playlist4.proto.DownloadFormat.Codec\"H\n\x05\x43odec\x12\x11\n\rCODEC_UNKNOWN\x10\x00\x12\x0e\n\nOGG_VORBIS\x10\x01\x12\x08\n\x04\x46LAC\x10\x02\x12\x12\n\x0eMPEG_1_LAYER_3\x10\x03\"\xac\x01\n\x0eListAttributes\x12\x0c\n\x04name\x18\x01 \x01(\t\x12\x13\n\x0b\x64\x65scription\x18\x02 \x01(\t\x12\x0f\n\x07picture\x18\x03 \x01(\x0c\x12\x15\n\rcollaborative\x18\x04 \x01(\x08\x12\x13\n\x0bpl3_version\x18\x05 \x01(\t\x12\x18\n\x10\x64\x65leted_by_owner\x18\x06 \x01(\x08\x12 \n\x18restricted_collaborative\x18\x07 \x01(\x08\"\x9c\x01\n\x0eItemAttributes\x12\x10\n\x08\x61\x64\x64\x65\x64_by\x18\x01 \x01(\t\x12\x0f\n\x07message\x18\x03 \x01(\t\x12\x0c\n\x04seen\x18\x04 \x01(\x08\x12@\n\x0f\x64ownload_format\x18\x06 \x01(\x0b\x32\'.spotify.playlist4.proto.DownloadFormat\x12\x17\n\x0fsevendigital_id\x18\x07 \x01(\t\"-\n\x0fStringAttribute\x12\x0b\n\x03key\x18\x01 \x02(\t\x12\r\n\x05value\x18\x02 \x02(\t\"O\n\x10StringAttributes\x12;\n\tattribute\x18\x01 \x03(\x0b\x32(.spotify.playlist4.proto.StringAttribute*\xc8\x01\n\x11ListAttributeKind\x12\x10\n\x0cLIST_UNKNOWN\x10\x00\x12\r\n\tLIST_NAME\x10\x01\x12\x14\n\x10LIST_DESCRIPTION\x10\x02\x12\x10\n\x0cLIST_PICTURE\x10\x03\x12\x16\n\x12LIST_COLLABORATIVE\x10\x04\x12\x14\n\x10LIST_PL3_VERSION\x10\x05\x12\x19\n\x15LIST_DELETED_BY_OWNER\x10\x06\x12!\n\x1dLIST_RESTRICTED_COLLABORATIVE\x10\x07*\xe8\x01\n\x11ItemAttributeKind\x12\x10\n\x0cITEM_UNKNOWN\x10\x00\x12\x11\n\rITEM_ADDED_BY\x10\x01\x12\x12\n\x0eITEM_TIMESTAMP\x10\x02\x12\x10\n\x0cITEM_MESSAGE\x10\x03\x12\r\n\tITEM_SEEN\x10\x04\x12\x17\n\x13ITEM_DOWNLOAD_COUNT\x10\x05\x12\x18\n\x14ITEM_DOWNLOAD_FORMAT\x10\x06\x12\x18\n\x14ITEM_SEVENDIGITAL_ID\x10\x07\x12\x1a\n\x16ITEM_SEVENDIGITAL_LEFT\x10\x08\x12\x10\n\x0cITEM_SEEN_AT\x10\tB\x1f\n\x1b\x63om.spotify.playlist4.protoH\x01')

_LISTATTRIBUTEKIND = descriptor.EnumDescriptor(
  name='ListAttributeKind',
  full_name='spotify.playlist4.proto.ListAttributeKind',
  filename=None,
  file=DESCRIPTOR,
  values=[
    descriptor.EnumValueDescriptor(
      name='LIST_UNKNOWN', index=0, number=0,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='LIST_NAME', index=1, number=1,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='LIST_DESCRIPTION', index=2, number=2,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='LIST_PICTURE', index=3, number=3,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='LIST_COLLABORATIVE', index=4, number=4,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='LIST_PL3_VERSION', index=5, number=5,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='LIST_DELETED_BY_OWNER', index=6, number=6,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='LIST_RESTRICTED_COLLABORATIVE', index=7, number=7,
      options=None,
      type=None),
  ],
  containing_type=None,
  options=None,
  serialized_start=713,
  serialized_end=913,
)


_ITEMATTRIBUTEKIND = descriptor.EnumDescriptor(
  name='ItemAttributeKind',
  full_name='spotify.playlist4.proto.ItemAttributeKind',
  filename=None,
  file=DESCRIPTOR,
  values=[
    descriptor.EnumValueDescriptor(
      name='ITEM_UNKNOWN', index=0, number=0,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='ITEM_ADDED_BY', index=1, number=1,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='ITEM_TIMESTAMP', index=2, number=2,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='ITEM_MESSAGE', index=3, number=3,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='ITEM_SEEN', index=4, number=4,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='ITEM_DOWNLOAD_COUNT', index=5, number=5,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='ITEM_DOWNLOAD_FORMAT', index=6, number=6,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='ITEM_SEVENDIGITAL_ID', index=7, number=7,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='ITEM_SEVENDIGITAL_LEFT', index=8, number=8,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='ITEM_SEEN_AT', index=9, number=9,
      options=None,
      type=None),
  ],
  containing_type=None,
  options=None,
  serialized_start=916,
  serialized_end=1148,
)


LIST_UNKNOWN = 0
LIST_NAME = 1
LIST_DESCRIPTION = 2
LIST_PICTURE = 3
LIST_COLLABORATIVE = 4
LIST_PL3_VERSION = 5
LIST_DELETED_BY_OWNER = 6
LIST_RESTRICTED_COLLABORATIVE = 7
ITEM_UNKNOWN = 0
ITEM_ADDED_BY = 1
ITEM_TIMESTAMP = 2
ITEM_MESSAGE = 3
ITEM_SEEN = 4
ITEM_DOWNLOAD_COUNT = 5
ITEM_DOWNLOAD_FORMAT = 6
ITEM_SEVENDIGITAL_ID = 7
ITEM_SEVENDIGITAL_LEFT = 8
ITEM_SEEN_AT = 9


_DOWNLOADFORMAT_CODEC = descriptor.EnumDescriptor(
  name='Codec',
  full_name='spotify.playlist4.proto.DownloadFormat.Codec',
  filename=None,
  file=DESCRIPTOR,
  values=[
    descriptor.EnumValueDescriptor(
      name='CODEC_UNKNOWN', index=0, number=0,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='OGG_VORBIS', index=1, number=1,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='FLAC', index=2, number=2,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='MPEG_1_LAYER_3', index=3, number=3,
      options=None,
      type=None),
  ],
  containing_type=None,
  options=None,
  serialized_start=176,
  serialized_end=248,
)


_LISTCHECKSUM = descriptor.Descriptor(
  name='ListChecksum',
  full_name='spotify.playlist4.proto.ListChecksum',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='version', full_name='spotify.playlist4.proto.ListChecksum.version', index=0,
      number=1, type=5, cpp_type=1, label=2,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='sha1', full_name='spotify.playlist4.proto.ListChecksum.sha1', index=1,
      number=4, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value="",
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=48,
  serialized_end=93,
)


_DOWNLOADFORMAT = descriptor.Descriptor(
  name='DownloadFormat',
  full_name='spotify.playlist4.proto.DownloadFormat',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='codec', full_name='spotify.playlist4.proto.DownloadFormat.codec', index=0,
      number=1, type=14, cpp_type=8, label=2,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
    _DOWNLOADFORMAT_CODEC,
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=96,
  serialized_end=248,
)


_LISTATTRIBUTES = descriptor.Descriptor(
  name='ListAttributes',
  full_name='spotify.playlist4.proto.ListAttributes',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='name', full_name='spotify.playlist4.proto.ListAttributes.name', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='description', full_name='spotify.playlist4.proto.ListAttributes.description', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='picture', full_name='spotify.playlist4.proto.ListAttributes.picture', index=2,
      number=3, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value="",
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='collaborative', full_name='spotify.playlist4.proto.ListAttributes.collaborative', index=3,
      number=4, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='pl3_version', full_name='spotify.playlist4.proto.ListAttributes.pl3_version', index=4,
      number=5, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='deleted_by_owner', full_name='spotify.playlist4.proto.ListAttributes.deleted_by_owner', index=5,
      number=6, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='restricted_collaborative', full_name='spotify.playlist4.proto.ListAttributes.restricted_collaborative', index=6,
      number=7, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=251,
  serialized_end=423,
)


_ITEMATTRIBUTES = descriptor.Descriptor(
  name='ItemAttributes',
  full_name='spotify.playlist4.proto.ItemAttributes',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='added_by', full_name='spotify.playlist4.proto.ItemAttributes.added_by', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='message', full_name='spotify.playlist4.proto.ItemAttributes.message', index=1,
      number=3, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='seen', full_name='spotify.playlist4.proto.ItemAttributes.seen', index=2,
      number=4, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='download_format', full_name='spotify.playlist4.proto.ItemAttributes.download_format', index=3,
      number=6, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='sevendigital_id', full_name='spotify.playlist4.proto.ItemAttributes.sevendigital_id', index=4,
      number=7, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=426,
  serialized_end=582,
)


_STRINGATTRIBUTE = descriptor.Descriptor(
  name='StringAttribute',
  full_name='spotify.playlist4.proto.StringAttribute',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='key', full_name='spotify.playlist4.proto.StringAttribute.key', index=0,
      number=1, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='value', full_name='spotify.playlist4.proto.StringAttribute.value', index=1,
      number=2, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=584,
  serialized_end=629,
)


_STRINGATTRIBUTES = descriptor.Descriptor(
  name='StringAttributes',
  full_name='spotify.playlist4.proto.StringAttributes',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='attribute', full_name='spotify.playlist4.proto.StringAttributes.attribute', index=0,
      number=1, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=631,
  serialized_end=710,
)

_DOWNLOADFORMAT.fields_by_name['codec'].enum_type = _DOWNLOADFORMAT_CODEC
_DOWNLOADFORMAT_CODEC.containing_type = _DOWNLOADFORMAT;
_ITEMATTRIBUTES.fields_by_name['download_format'].message_type = _DOWNLOADFORMAT
_STRINGATTRIBUTES.fields_by_name['attribute'].message_type = _STRINGATTRIBUTE
DESCRIPTOR.message_types_by_name['ListChecksum'] = _LISTCHECKSUM
DESCRIPTOR.message_types_by_name['DownloadFormat'] = _DOWNLOADFORMAT
DESCRIPTOR.message_types_by_name['ListAttributes'] = _LISTATTRIBUTES
DESCRIPTOR.message_types_by_name['ItemAttributes'] = _ITEMATTRIBUTES
DESCRIPTOR.message_types_by_name['StringAttribute'] = _STRINGATTRIBUTE
DESCRIPTOR.message_types_by_name['StringAttributes'] = _STRINGATTRIBUTES

class ListChecksum(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _LISTCHECKSUM
  
  # @@protoc_insertion_point(class_scope:spotify.playlist4.proto.ListChecksum)

class DownloadFormat(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _DOWNLOADFORMAT
  
  # @@protoc_insertion_point(class_scope:spotify.playlist4.proto.DownloadFormat)

class ListAttributes(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _LISTATTRIBUTES
  
  # @@protoc_insertion_point(class_scope:spotify.playlist4.proto.ListAttributes)

class ItemAttributes(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _ITEMATTRIBUTES
  
  # @@protoc_insertion_point(class_scope:spotify.playlist4.proto.ItemAttributes)

class StringAttribute(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _STRINGATTRIBUTE
  
  # @@protoc_insertion_point(class_scope:spotify.playlist4.proto.StringAttribute)

class StringAttributes(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _STRINGATTRIBUTES
  
  # @@protoc_insertion_point(class_scope:spotify.playlist4.proto.StringAttributes)

# @@protoc_insertion_point(module_scope)

########NEW FILE########
__FILENAME__ = playlist4ops_pb2
# Generated by the protocol buffer compiler.  DO NOT EDIT!

from google.protobuf import descriptor
from google.protobuf import message
from google.protobuf import reflection
from google.protobuf import descriptor_pb2
# @@protoc_insertion_point(imports)


import playlist4content_pb2
import playlist4meta_pb2

DESCRIPTOR = descriptor.FileDescriptor(
  name='playlist4ops.proto',
  package='spotify.playlist4.proto',
  serialized_pb='\n\x12playlist4ops.proto\x12\x17spotify.playlist4.proto\x1a\x16playlist4content.proto\x1a\x13playlist4meta.proto\"\xa7\x01\n\x03\x41\x64\x64\x12\x11\n\tfromIndex\x18\x01 \x01(\x05\x12,\n\x05items\x18\x02 \x03(\x0b\x32\x1d.spotify.playlist4.proto.Item\x12<\n\rlist_checksum\x18\x03 \x01(\x0b\x32%.spotify.playlist4.proto.ListChecksum\x12\x0f\n\x07\x61\x64\x64Last\x18\x04 \x01(\x08\x12\x10\n\x08\x61\x64\x64\x46irst\x18\x05 \x01(\x08\"\xa5\x02\n\x03Rem\x12\x11\n\tfromIndex\x18\x01 \x01(\x05\x12\x0e\n\x06length\x18\x02 \x01(\x05\x12,\n\x05items\x18\x03 \x03(\x0b\x32\x1d.spotify.playlist4.proto.Item\x12<\n\rlist_checksum\x18\x04 \x01(\x0b\x32%.spotify.playlist4.proto.ListChecksum\x12=\n\x0eitems_checksum\x18\x05 \x01(\x0b\x32%.spotify.playlist4.proto.ListChecksum\x12<\n\ruris_checksum\x18\x06 \x01(\x0b\x32%.spotify.playlist4.proto.ListChecksum\x12\x12\n\nitemsAsKey\x18\x07 \x01(\x08\"\xf4\x01\n\x03Mov\x12\x11\n\tfromIndex\x18\x01 \x02(\x05\x12\x0e\n\x06length\x18\x02 \x02(\x05\x12\x0f\n\x07toIndex\x18\x03 \x02(\x05\x12<\n\rlist_checksum\x18\x04 \x01(\x0b\x32%.spotify.playlist4.proto.ListChecksum\x12=\n\x0eitems_checksum\x18\x05 \x01(\x0b\x32%.spotify.playlist4.proto.ListChecksum\x12<\n\ruris_checksum\x18\x06 \x01(\x0b\x32%.spotify.playlist4.proto.ListChecksum\"\x93\x01\n\x1aItemAttributesPartialState\x12\x37\n\x06values\x18\x01 \x02(\x0b\x32\'.spotify.playlist4.proto.ItemAttributes\x12<\n\x08no_value\x18\x02 \x03(\x0e\x32*.spotify.playlist4.proto.ItemAttributeKind\"\x93\x01\n\x1aListAttributesPartialState\x12\x37\n\x06values\x18\x01 \x02(\x0b\x32\'.spotify.playlist4.proto.ListAttributes\x12<\n\x08no_value\x18\x02 \x03(\x0e\x32*.spotify.playlist4.proto.ListAttributeKind\"\xc5\x02\n\x14UpdateItemAttributes\x12\r\n\x05index\x18\x01 \x02(\x05\x12K\n\x0enew_attributes\x18\x02 \x02(\x0b\x32\x33.spotify.playlist4.proto.ItemAttributesPartialState\x12K\n\x0eold_attributes\x18\x03 \x01(\x0b\x32\x33.spotify.playlist4.proto.ItemAttributesPartialState\x12<\n\rlist_checksum\x18\x04 \x01(\x0b\x32%.spotify.playlist4.proto.ListChecksum\x12\x46\n\x17old_attributes_checksum\x18\x05 \x01(\x0b\x32%.spotify.playlist4.proto.ListChecksum\"\xb6\x02\n\x14UpdateListAttributes\x12K\n\x0enew_attributes\x18\x01 \x02(\x0b\x32\x33.spotify.playlist4.proto.ListAttributesPartialState\x12K\n\x0eold_attributes\x18\x02 \x01(\x0b\x32\x33.spotify.playlist4.proto.ListAttributesPartialState\x12<\n\rlist_checksum\x18\x03 \x01(\x0b\x32%.spotify.playlist4.proto.ListChecksum\x12\x46\n\x17old_attributes_checksum\x18\x04 \x01(\x0b\x32%.spotify.playlist4.proto.ListChecksum\"\xc0\x03\n\x02Op\x12.\n\x04kind\x18\x01 \x02(\x0e\x32 .spotify.playlist4.proto.Op.Kind\x12)\n\x03\x61\x64\x64\x18\x02 \x01(\x0b\x32\x1c.spotify.playlist4.proto.Add\x12)\n\x03rem\x18\x03 \x01(\x0b\x32\x1c.spotify.playlist4.proto.Rem\x12)\n\x03mov\x18\x04 \x01(\x0b\x32\x1c.spotify.playlist4.proto.Mov\x12M\n\x16update_item_attributes\x18\x05 \x01(\x0b\x32-.spotify.playlist4.proto.UpdateItemAttributes\x12M\n\x16update_list_attributes\x18\x06 \x01(\x0b\x32-.spotify.playlist4.proto.UpdateListAttributes\"k\n\x04Kind\x12\x10\n\x0cKIND_UNKNOWN\x10\x00\x12\x07\n\x03\x41\x44\x44\x10\x02\x12\x07\n\x03REM\x10\x03\x12\x07\n\x03MOV\x10\x04\x12\x1a\n\x16UPDATE_ITEM_ATTRIBUTES\x10\x05\x12\x1a\n\x16UPDATE_LIST_ATTRIBUTES\x10\x06\"2\n\x06OpList\x12(\n\x03ops\x18\x01 \x03(\x0b\x32\x1b.spotify.playlist4.proto.OpB\x1f\n\x1b\x63om.spotify.playlist4.protoH\x01')



_OP_KIND = descriptor.EnumDescriptor(
  name='Kind',
  full_name='spotify.playlist4.proto.Op.Kind',
  filename=None,
  file=DESCRIPTOR,
  values=[
    descriptor.EnumValueDescriptor(
      name='KIND_UNKNOWN', index=0, number=0,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='ADD', index=1, number=2,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='REM', index=2, number=3,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='MOV', index=3, number=4,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='UPDATE_ITEM_ATTRIBUTES', index=4, number=5,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='UPDATE_LIST_ATTRIBUTES', index=5, number=6,
      options=None,
      type=None),
  ],
  containing_type=None,
  options=None,
  serialized_start=2088,
  serialized_end=2195,
)


_ADD = descriptor.Descriptor(
  name='Add',
  full_name='spotify.playlist4.proto.Add',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='fromIndex', full_name='spotify.playlist4.proto.Add.fromIndex', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='items', full_name='spotify.playlist4.proto.Add.items', index=1,
      number=2, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='list_checksum', full_name='spotify.playlist4.proto.Add.list_checksum', index=2,
      number=3, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='addLast', full_name='spotify.playlist4.proto.Add.addLast', index=3,
      number=4, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='addFirst', full_name='spotify.playlist4.proto.Add.addFirst', index=4,
      number=5, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=93,
  serialized_end=260,
)


_REM = descriptor.Descriptor(
  name='Rem',
  full_name='spotify.playlist4.proto.Rem',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='fromIndex', full_name='spotify.playlist4.proto.Rem.fromIndex', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='length', full_name='spotify.playlist4.proto.Rem.length', index=1,
      number=2, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='items', full_name='spotify.playlist4.proto.Rem.items', index=2,
      number=3, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='list_checksum', full_name='spotify.playlist4.proto.Rem.list_checksum', index=3,
      number=4, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='items_checksum', full_name='spotify.playlist4.proto.Rem.items_checksum', index=4,
      number=5, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='uris_checksum', full_name='spotify.playlist4.proto.Rem.uris_checksum', index=5,
      number=6, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='itemsAsKey', full_name='spotify.playlist4.proto.Rem.itemsAsKey', index=6,
      number=7, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=263,
  serialized_end=556,
)


_MOV = descriptor.Descriptor(
  name='Mov',
  full_name='spotify.playlist4.proto.Mov',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='fromIndex', full_name='spotify.playlist4.proto.Mov.fromIndex', index=0,
      number=1, type=5, cpp_type=1, label=2,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='length', full_name='spotify.playlist4.proto.Mov.length', index=1,
      number=2, type=5, cpp_type=1, label=2,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='toIndex', full_name='spotify.playlist4.proto.Mov.toIndex', index=2,
      number=3, type=5, cpp_type=1, label=2,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='list_checksum', full_name='spotify.playlist4.proto.Mov.list_checksum', index=3,
      number=4, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='items_checksum', full_name='spotify.playlist4.proto.Mov.items_checksum', index=4,
      number=5, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='uris_checksum', full_name='spotify.playlist4.proto.Mov.uris_checksum', index=5,
      number=6, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=559,
  serialized_end=803,
)


_ITEMATTRIBUTESPARTIALSTATE = descriptor.Descriptor(
  name='ItemAttributesPartialState',
  full_name='spotify.playlist4.proto.ItemAttributesPartialState',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='values', full_name='spotify.playlist4.proto.ItemAttributesPartialState.values', index=0,
      number=1, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='no_value', full_name='spotify.playlist4.proto.ItemAttributesPartialState.no_value', index=1,
      number=2, type=14, cpp_type=8, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=806,
  serialized_end=953,
)


_LISTATTRIBUTESPARTIALSTATE = descriptor.Descriptor(
  name='ListAttributesPartialState',
  full_name='spotify.playlist4.proto.ListAttributesPartialState',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='values', full_name='spotify.playlist4.proto.ListAttributesPartialState.values', index=0,
      number=1, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='no_value', full_name='spotify.playlist4.proto.ListAttributesPartialState.no_value', index=1,
      number=2, type=14, cpp_type=8, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=956,
  serialized_end=1103,
)


_UPDATEITEMATTRIBUTES = descriptor.Descriptor(
  name='UpdateItemAttributes',
  full_name='spotify.playlist4.proto.UpdateItemAttributes',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='index', full_name='spotify.playlist4.proto.UpdateItemAttributes.index', index=0,
      number=1, type=5, cpp_type=1, label=2,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='new_attributes', full_name='spotify.playlist4.proto.UpdateItemAttributes.new_attributes', index=1,
      number=2, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='old_attributes', full_name='spotify.playlist4.proto.UpdateItemAttributes.old_attributes', index=2,
      number=3, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='list_checksum', full_name='spotify.playlist4.proto.UpdateItemAttributes.list_checksum', index=3,
      number=4, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='old_attributes_checksum', full_name='spotify.playlist4.proto.UpdateItemAttributes.old_attributes_checksum', index=4,
      number=5, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1106,
  serialized_end=1431,
)


_UPDATELISTATTRIBUTES = descriptor.Descriptor(
  name='UpdateListAttributes',
  full_name='spotify.playlist4.proto.UpdateListAttributes',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='new_attributes', full_name='spotify.playlist4.proto.UpdateListAttributes.new_attributes', index=0,
      number=1, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='old_attributes', full_name='spotify.playlist4.proto.UpdateListAttributes.old_attributes', index=1,
      number=2, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='list_checksum', full_name='spotify.playlist4.proto.UpdateListAttributes.list_checksum', index=2,
      number=3, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='old_attributes_checksum', full_name='spotify.playlist4.proto.UpdateListAttributes.old_attributes_checksum', index=3,
      number=4, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1434,
  serialized_end=1744,
)


_OP = descriptor.Descriptor(
  name='Op',
  full_name='spotify.playlist4.proto.Op',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='kind', full_name='spotify.playlist4.proto.Op.kind', index=0,
      number=1, type=14, cpp_type=8, label=2,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='add', full_name='spotify.playlist4.proto.Op.add', index=1,
      number=2, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='rem', full_name='spotify.playlist4.proto.Op.rem', index=2,
      number=3, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='mov', full_name='spotify.playlist4.proto.Op.mov', index=3,
      number=4, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='update_item_attributes', full_name='spotify.playlist4.proto.Op.update_item_attributes', index=4,
      number=5, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='update_list_attributes', full_name='spotify.playlist4.proto.Op.update_list_attributes', index=5,
      number=6, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
    _OP_KIND,
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1747,
  serialized_end=2195,
)


_OPLIST = descriptor.Descriptor(
  name='OpList',
  full_name='spotify.playlist4.proto.OpList',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='ops', full_name='spotify.playlist4.proto.OpList.ops', index=0,
      number=1, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=2197,
  serialized_end=2247,
)

_ADD.fields_by_name['items'].message_type = playlist4content_pb2._ITEM
_ADD.fields_by_name['list_checksum'].message_type = playlist4meta_pb2._LISTCHECKSUM
_REM.fields_by_name['items'].message_type = playlist4content_pb2._ITEM
_REM.fields_by_name['list_checksum'].message_type = playlist4meta_pb2._LISTCHECKSUM
_REM.fields_by_name['items_checksum'].message_type = playlist4meta_pb2._LISTCHECKSUM
_REM.fields_by_name['uris_checksum'].message_type = playlist4meta_pb2._LISTCHECKSUM
_MOV.fields_by_name['list_checksum'].message_type = playlist4meta_pb2._LISTCHECKSUM
_MOV.fields_by_name['items_checksum'].message_type = playlist4meta_pb2._LISTCHECKSUM
_MOV.fields_by_name['uris_checksum'].message_type = playlist4meta_pb2._LISTCHECKSUM
_ITEMATTRIBUTESPARTIALSTATE.fields_by_name['values'].message_type = playlist4meta_pb2._ITEMATTRIBUTES
_ITEMATTRIBUTESPARTIALSTATE.fields_by_name['no_value'].enum_type = playlist4meta_pb2._ITEMATTRIBUTEKIND
_LISTATTRIBUTESPARTIALSTATE.fields_by_name['values'].message_type = playlist4meta_pb2._LISTATTRIBUTES
_LISTATTRIBUTESPARTIALSTATE.fields_by_name['no_value'].enum_type = playlist4meta_pb2._LISTATTRIBUTEKIND
_UPDATEITEMATTRIBUTES.fields_by_name['new_attributes'].message_type = _ITEMATTRIBUTESPARTIALSTATE
_UPDATEITEMATTRIBUTES.fields_by_name['old_attributes'].message_type = _ITEMATTRIBUTESPARTIALSTATE
_UPDATEITEMATTRIBUTES.fields_by_name['list_checksum'].message_type = playlist4meta_pb2._LISTCHECKSUM
_UPDATEITEMATTRIBUTES.fields_by_name['old_attributes_checksum'].message_type = playlist4meta_pb2._LISTCHECKSUM
_UPDATELISTATTRIBUTES.fields_by_name['new_attributes'].message_type = _LISTATTRIBUTESPARTIALSTATE
_UPDATELISTATTRIBUTES.fields_by_name['old_attributes'].message_type = _LISTATTRIBUTESPARTIALSTATE
_UPDATELISTATTRIBUTES.fields_by_name['list_checksum'].message_type = playlist4meta_pb2._LISTCHECKSUM
_UPDATELISTATTRIBUTES.fields_by_name['old_attributes_checksum'].message_type = playlist4meta_pb2._LISTCHECKSUM
_OP.fields_by_name['kind'].enum_type = _OP_KIND
_OP.fields_by_name['add'].message_type = _ADD
_OP.fields_by_name['rem'].message_type = _REM
_OP.fields_by_name['mov'].message_type = _MOV
_OP.fields_by_name['update_item_attributes'].message_type = _UPDATEITEMATTRIBUTES
_OP.fields_by_name['update_list_attributes'].message_type = _UPDATELISTATTRIBUTES
_OP_KIND.containing_type = _OP;
_OPLIST.fields_by_name['ops'].message_type = _OP
DESCRIPTOR.message_types_by_name['Add'] = _ADD
DESCRIPTOR.message_types_by_name['Rem'] = _REM
DESCRIPTOR.message_types_by_name['Mov'] = _MOV
DESCRIPTOR.message_types_by_name['ItemAttributesPartialState'] = _ITEMATTRIBUTESPARTIALSTATE
DESCRIPTOR.message_types_by_name['ListAttributesPartialState'] = _LISTATTRIBUTESPARTIALSTATE
DESCRIPTOR.message_types_by_name['UpdateItemAttributes'] = _UPDATEITEMATTRIBUTES
DESCRIPTOR.message_types_by_name['UpdateListAttributes'] = _UPDATELISTATTRIBUTES
DESCRIPTOR.message_types_by_name['Op'] = _OP
DESCRIPTOR.message_types_by_name['OpList'] = _OPLIST

class Add(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _ADD
  
  # @@protoc_insertion_point(class_scope:spotify.playlist4.proto.Add)

class Rem(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _REM
  
  # @@protoc_insertion_point(class_scope:spotify.playlist4.proto.Rem)

class Mov(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _MOV
  
  # @@protoc_insertion_point(class_scope:spotify.playlist4.proto.Mov)

class ItemAttributesPartialState(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _ITEMATTRIBUTESPARTIALSTATE
  
  # @@protoc_insertion_point(class_scope:spotify.playlist4.proto.ItemAttributesPartialState)

class ListAttributesPartialState(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _LISTATTRIBUTESPARTIALSTATE
  
  # @@protoc_insertion_point(class_scope:spotify.playlist4.proto.ListAttributesPartialState)

class UpdateItemAttributes(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _UPDATEITEMATTRIBUTES
  
  # @@protoc_insertion_point(class_scope:spotify.playlist4.proto.UpdateItemAttributes)

class UpdateListAttributes(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _UPDATELISTATTRIBUTES
  
  # @@protoc_insertion_point(class_scope:spotify.playlist4.proto.UpdateListAttributes)

class Op(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _OP
  
  # @@protoc_insertion_point(class_scope:spotify.playlist4.proto.Op)

class OpList(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _OPLIST
  
  # @@protoc_insertion_point(class_scope:spotify.playlist4.proto.OpList)

# @@protoc_insertion_point(module_scope)

########NEW FILE########
__FILENAME__ = playlist4service_pb2
# Generated by the protocol buffer compiler.  DO NOT EDIT!

from google.protobuf import descriptor
from google.protobuf import message
from google.protobuf import reflection
from google.protobuf import descriptor_pb2
# @@protoc_insertion_point(imports)


import playlist4changes_pb2
import playlist4content_pb2

DESCRIPTOR = descriptor.FileDescriptor(
  name='playlist4service.proto',
  package='spotify.playlist4.proto',
  serialized_pb='\n\x16playlist4service.proto\x12\x17spotify.playlist4.proto\x1a\x16playlist4changes.proto\x1a\x16playlist4content.proto\"{\n\x0eRequestContext\x12\x16\n\x0e\x61\x64ministrative\x18\x02 \x01(\x08\x12\x11\n\tmigration\x18\x04 \x01(\x08\x12\x0b\n\x03tag\x18\x07 \x01(\t\x12\x16\n\x0euseStarredView\x18\x08 \x01(\x08\x12\x19\n\x11syncWithPublished\x18\t \x01(\x08\"_\n\x16GetCurrentRevisionArgs\x12\x0b\n\x03uri\x18\x01 \x01(\x0c\x12\x38\n\x07\x63ontext\x18\x02 \x01(\x0b\x32\'.spotify.playlist4.proto.RequestContext\"\x9c\x01\n\x1dGetChangesInSequenceRangeArgs\x12\x0b\n\x03uri\x18\x01 \x01(\x0c\x12\x38\n\x07\x63ontext\x18\x02 \x01(\x0b\x32\'.spotify.playlist4.proto.RequestContext\x12\x1a\n\x12\x66romSequenceNumber\x18\x03 \x01(\x05\x12\x18\n\x10toSequenceNumber\x18\x04 \x01(\x05\"\xc2\x01\n/GetChangesInSequenceRangeMatchingPl3VersionArgs\x12\x0b\n\x03uri\x18\x01 \x01(\x0c\x12\x38\n\x07\x63ontext\x18\x02 \x01(\x0b\x32\'.spotify.playlist4.proto.RequestContext\x12\x1a\n\x12\x66romSequenceNumber\x18\x03 \x01(\x05\x12\x18\n\x10toSequenceNumber\x18\x04 \x01(\x05\x12\x12\n\npl3Version\x18\x05 \x01(\t\"c\n\x1fGetChangesInSequenceRangeReturn\x12@\n\x06result\x18\x01 \x03(\x0b\x32\x30.spotify.playlist4.proto.RevisionTaggedChangeSet\"[\n\x12ObliterateListArgs\x12\x0b\n\x03uri\x18\x01 \x01(\x0c\x12\x38\n\x07\x63ontext\x18\x02 \x01(\x0b\x32\'.spotify.playlist4.proto.RequestContext\"\x87\x01\n\x13UpdatePublishedArgs\x12\x14\n\x0cpublishedUri\x18\x01 \x01(\x0c\x12\x38\n\x07\x63ontext\x18\x02 \x01(\x0b\x32\'.spotify.playlist4.proto.RequestContext\x12\x0b\n\x03uri\x18\x03 \x01(\x0c\x12\x13\n\x0bisPublished\x18\x04 \x01(\x08\"\xd1\x01\n\x0fSynchronizeArgs\x12\x0b\n\x03uri\x18\x01 \x01(\x0c\x12\x38\n\x07\x63ontext\x18\x02 \x01(\x0b\x32\'.spotify.playlist4.proto.RequestContext\x12@\n\tselection\x18\x03 \x01(\x0b\x32-.spotify.playlist4.proto.ListContentSelection\x12\x35\n\x07\x63hanges\x18\x04 \x01(\x0b\x32$.spotify.playlist4.proto.ListChanges\"t\n\x19GetSnapshotAtRevisionArgs\x12\x0b\n\x03uri\x18\x01 \x01(\x0c\x12\x38\n\x07\x63ontext\x18\x02 \x01(\x0b\x32\'.spotify.playlist4.proto.RequestContext\x12\x10\n\x08revision\x18\x03 \x01(\x0c\" \n\x10SubscribeRequest\x12\x0c\n\x04uris\x18\x01 \x03(\x0c\"\"\n\x12UnsubscribeRequest\x12\x0c\n\x04uris\x18\x01 \x03(\x0c\"\xb0\x01\n\x19Playlist4ServiceException\x12\x0b\n\x03why\x18\x01 \x01(\t\x12\x0e\n\x06symbol\x18\x02 \x01(\t\x12\x11\n\tpermanent\x18\x03 \x01(\x08\x12\x19\n\x11serviceErrorClass\x18\x04 \x01(\t\x12H\n\x0einboxErrorKind\x18\x05 \x01(\x0e\x32\x30.spotify.playlist4.proto.Playlist4InboxErrorKind\"\x98\x01\n\x11SynchronizeReturn\x12<\n\x06result\x18\x01 \x01(\x0b\x32,.spotify.playlist4.proto.SelectedListContent\x12\x45\n\texception\x18\x04 \x01(\x0b\x32\x32.spotify.playlist4.proto.Playlist4ServiceException\"\xbb\x05\n\x14Playlist4ServiceCall\x12\x41\n\x04kind\x18\x01 \x01(\x0e\x32\x33.spotify.playlist4.proto.Playlist4ServiceMethodKind\x12O\n\x16getCurrentRevisionArgs\x18\x02 \x01(\x0b\x32/.spotify.playlist4.proto.GetCurrentRevisionArgs\x12]\n\x1dgetChangesInSequenceRangeArgs\x18\x03 \x01(\x0b\x32\x36.spotify.playlist4.proto.GetChangesInSequenceRangeArgs\x12G\n\x12obliterateListArgs\x18\x04 \x01(\x0b\x32+.spotify.playlist4.proto.ObliterateListArgs\x12\x41\n\x0fsynchronizeArgs\x18\x05 \x01(\x0b\x32(.spotify.playlist4.proto.SynchronizeArgs\x12I\n\x13updatePublishedArgs\x18\x06 \x01(\x0b\x32,.spotify.playlist4.proto.UpdatePublishedArgs\x12\x81\x01\n/getChangesInSequenceRangeMatchingPl3VersionArgs\x18\x07 \x01(\x0b\x32H.spotify.playlist4.proto.GetChangesInSequenceRangeMatchingPl3VersionArgs\x12U\n\x19getSnapshotAtRevisionArgs\x18\x08 \x01(\x0b\x32\x32.spotify.playlist4.proto.GetSnapshotAtRevisionArgs\"\xa0\x04\n\x16Playlist4ServiceReturn\x12\x41\n\x04kind\x18\x01 \x01(\x0e\x32\x33.spotify.playlist4.proto.Playlist4ServiceMethodKind\x12\x45\n\texception\x18\x02 \x01(\x0b\x32\x32.spotify.playlist4.proto.Playlist4ServiceException\x12 \n\x18getCurrentRevisionReturn\x18\x03 \x01(\x0c\x12\x61\n\x1fgetChangesInSequenceRangeReturn\x18\x04 \x01(\x0b\x32\x38.spotify.playlist4.proto.GetChangesInSequenceRangeReturn\x12\x1c\n\x14obliterateListReturn\x18\x05 \x01(\x08\x12\x45\n\x11synchronizeReturn\x18\x06 \x01(\x0b\x32*.spotify.playlist4.proto.SynchronizeReturn\x12\x1d\n\x15updatePublishedReturn\x18\x07 \x01(\x08\x12s\n1getChangesInSequenceRangeMatchingPl3VersionReturn\x18\x08 \x01(\x0b\x32\x38.spotify.playlist4.proto.GetChangesInSequenceRangeReturn\"0\n\x0f\x43reateListReply\x12\x0b\n\x03uri\x18\x01 \x02(\x0c\x12\x10\n\x08revision\x18\x02 \x01(\x0c*x\n\x17Playlist4InboxErrorKind\x12\x15\n\x11INBOX_NOT_ALLOWED\x10\x02\x12\x16\n\x12INBOX_INVALID_USER\x10\x03\x12\x15\n\x11INBOX_INVALID_URI\x10\x04\x12\x17\n\x13INBOX_LIST_TOO_LONG\x10\x05*\xb0\x02\n\x1aPlaylist4ServiceMethodKind\x12\x12\n\x0eMETHOD_UNKNOWN\x10\x00\x12\x1f\n\x1bMETHOD_GET_CURRENT_REVISION\x10\x02\x12(\n$METHOD_GET_CHANGES_IN_SEQUENCE_RANGE\x10\x03\x12\x1a\n\x16METHOD_OBLITERATE_LIST\x10\x04\x12\x16\n\x12METHOD_SYNCHRONIZE\x10\x05\x12\x1b\n\x17METHOD_UPDATE_PUBLISHED\x10\x06\x12=\n9METHOD_GET_CHANGES_IN_SEQUENCE_RANGE_MATCHING_PL3_VERSION\x10\x07\x12#\n\x1fMETHOD_GET_SNAPSHOT_AT_REVISION\x10\x08\x42\x02H\x01')

_PLAYLIST4INBOXERRORKIND = descriptor.EnumDescriptor(
  name='Playlist4InboxErrorKind',
  full_name='spotify.playlist4.proto.Playlist4InboxErrorKind',
  filename=None,
  file=DESCRIPTOR,
  values=[
    descriptor.EnumValueDescriptor(
      name='INBOX_NOT_ALLOWED', index=0, number=2,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='INBOX_INVALID_USER', index=1, number=3,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='INBOX_INVALID_URI', index=2, number=4,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='INBOX_LIST_TOO_LONG', index=3, number=5,
      options=None,
      type=None),
  ],
  containing_type=None,
  options=None,
  serialized_start=3042,
  serialized_end=3162,
)


_PLAYLIST4SERVICEMETHODKIND = descriptor.EnumDescriptor(
  name='Playlist4ServiceMethodKind',
  full_name='spotify.playlist4.proto.Playlist4ServiceMethodKind',
  filename=None,
  file=DESCRIPTOR,
  values=[
    descriptor.EnumValueDescriptor(
      name='METHOD_UNKNOWN', index=0, number=0,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='METHOD_GET_CURRENT_REVISION', index=1, number=2,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='METHOD_GET_CHANGES_IN_SEQUENCE_RANGE', index=2, number=3,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='METHOD_OBLITERATE_LIST', index=3, number=4,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='METHOD_SYNCHRONIZE', index=4, number=5,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='METHOD_UPDATE_PUBLISHED', index=5, number=6,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='METHOD_GET_CHANGES_IN_SEQUENCE_RANGE_MATCHING_PL3_VERSION', index=6, number=7,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='METHOD_GET_SNAPSHOT_AT_REVISION', index=7, number=8,
      options=None,
      type=None),
  ],
  containing_type=None,
  options=None,
  serialized_start=3165,
  serialized_end=3469,
)


INBOX_NOT_ALLOWED = 2
INBOX_INVALID_USER = 3
INBOX_INVALID_URI = 4
INBOX_LIST_TOO_LONG = 5
METHOD_UNKNOWN = 0
METHOD_GET_CURRENT_REVISION = 2
METHOD_GET_CHANGES_IN_SEQUENCE_RANGE = 3
METHOD_OBLITERATE_LIST = 4
METHOD_SYNCHRONIZE = 5
METHOD_UPDATE_PUBLISHED = 6
METHOD_GET_CHANGES_IN_SEQUENCE_RANGE_MATCHING_PL3_VERSION = 7
METHOD_GET_SNAPSHOT_AT_REVISION = 8



_REQUESTCONTEXT = descriptor.Descriptor(
  name='RequestContext',
  full_name='spotify.playlist4.proto.RequestContext',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='administrative', full_name='spotify.playlist4.proto.RequestContext.administrative', index=0,
      number=2, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='migration', full_name='spotify.playlist4.proto.RequestContext.migration', index=1,
      number=4, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='tag', full_name='spotify.playlist4.proto.RequestContext.tag', index=2,
      number=7, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='useStarredView', full_name='spotify.playlist4.proto.RequestContext.useStarredView', index=3,
      number=8, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='syncWithPublished', full_name='spotify.playlist4.proto.RequestContext.syncWithPublished', index=4,
      number=9, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=99,
  serialized_end=222,
)


_GETCURRENTREVISIONARGS = descriptor.Descriptor(
  name='GetCurrentRevisionArgs',
  full_name='spotify.playlist4.proto.GetCurrentRevisionArgs',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='uri', full_name='spotify.playlist4.proto.GetCurrentRevisionArgs.uri', index=0,
      number=1, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value="",
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='context', full_name='spotify.playlist4.proto.GetCurrentRevisionArgs.context', index=1,
      number=2, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=224,
  serialized_end=319,
)


_GETCHANGESINSEQUENCERANGEARGS = descriptor.Descriptor(
  name='GetChangesInSequenceRangeArgs',
  full_name='spotify.playlist4.proto.GetChangesInSequenceRangeArgs',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='uri', full_name='spotify.playlist4.proto.GetChangesInSequenceRangeArgs.uri', index=0,
      number=1, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value="",
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='context', full_name='spotify.playlist4.proto.GetChangesInSequenceRangeArgs.context', index=1,
      number=2, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='fromSequenceNumber', full_name='spotify.playlist4.proto.GetChangesInSequenceRangeArgs.fromSequenceNumber', index=2,
      number=3, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='toSequenceNumber', full_name='spotify.playlist4.proto.GetChangesInSequenceRangeArgs.toSequenceNumber', index=3,
      number=4, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=322,
  serialized_end=478,
)


_GETCHANGESINSEQUENCERANGEMATCHINGPL3VERSIONARGS = descriptor.Descriptor(
  name='GetChangesInSequenceRangeMatchingPl3VersionArgs',
  full_name='spotify.playlist4.proto.GetChangesInSequenceRangeMatchingPl3VersionArgs',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='uri', full_name='spotify.playlist4.proto.GetChangesInSequenceRangeMatchingPl3VersionArgs.uri', index=0,
      number=1, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value="",
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='context', full_name='spotify.playlist4.proto.GetChangesInSequenceRangeMatchingPl3VersionArgs.context', index=1,
      number=2, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='fromSequenceNumber', full_name='spotify.playlist4.proto.GetChangesInSequenceRangeMatchingPl3VersionArgs.fromSequenceNumber', index=2,
      number=3, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='toSequenceNumber', full_name='spotify.playlist4.proto.GetChangesInSequenceRangeMatchingPl3VersionArgs.toSequenceNumber', index=3,
      number=4, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='pl3Version', full_name='spotify.playlist4.proto.GetChangesInSequenceRangeMatchingPl3VersionArgs.pl3Version', index=4,
      number=5, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=481,
  serialized_end=675,
)


_GETCHANGESINSEQUENCERANGERETURN = descriptor.Descriptor(
  name='GetChangesInSequenceRangeReturn',
  full_name='spotify.playlist4.proto.GetChangesInSequenceRangeReturn',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='result', full_name='spotify.playlist4.proto.GetChangesInSequenceRangeReturn.result', index=0,
      number=1, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=677,
  serialized_end=776,
)


_OBLITERATELISTARGS = descriptor.Descriptor(
  name='ObliterateListArgs',
  full_name='spotify.playlist4.proto.ObliterateListArgs',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='uri', full_name='spotify.playlist4.proto.ObliterateListArgs.uri', index=0,
      number=1, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value="",
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='context', full_name='spotify.playlist4.proto.ObliterateListArgs.context', index=1,
      number=2, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=778,
  serialized_end=869,
)


_UPDATEPUBLISHEDARGS = descriptor.Descriptor(
  name='UpdatePublishedArgs',
  full_name='spotify.playlist4.proto.UpdatePublishedArgs',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='publishedUri', full_name='spotify.playlist4.proto.UpdatePublishedArgs.publishedUri', index=0,
      number=1, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value="",
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='context', full_name='spotify.playlist4.proto.UpdatePublishedArgs.context', index=1,
      number=2, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='uri', full_name='spotify.playlist4.proto.UpdatePublishedArgs.uri', index=2,
      number=3, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value="",
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='isPublished', full_name='spotify.playlist4.proto.UpdatePublishedArgs.isPublished', index=3,
      number=4, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=872,
  serialized_end=1007,
)


_SYNCHRONIZEARGS = descriptor.Descriptor(
  name='SynchronizeArgs',
  full_name='spotify.playlist4.proto.SynchronizeArgs',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='uri', full_name='spotify.playlist4.proto.SynchronizeArgs.uri', index=0,
      number=1, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value="",
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='context', full_name='spotify.playlist4.proto.SynchronizeArgs.context', index=1,
      number=2, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='selection', full_name='spotify.playlist4.proto.SynchronizeArgs.selection', index=2,
      number=3, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='changes', full_name='spotify.playlist4.proto.SynchronizeArgs.changes', index=3,
      number=4, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1010,
  serialized_end=1219,
)


_GETSNAPSHOTATREVISIONARGS = descriptor.Descriptor(
  name='GetSnapshotAtRevisionArgs',
  full_name='spotify.playlist4.proto.GetSnapshotAtRevisionArgs',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='uri', full_name='spotify.playlist4.proto.GetSnapshotAtRevisionArgs.uri', index=0,
      number=1, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value="",
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='context', full_name='spotify.playlist4.proto.GetSnapshotAtRevisionArgs.context', index=1,
      number=2, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='revision', full_name='spotify.playlist4.proto.GetSnapshotAtRevisionArgs.revision', index=2,
      number=3, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value="",
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1221,
  serialized_end=1337,
)


_SUBSCRIBEREQUEST = descriptor.Descriptor(
  name='SubscribeRequest',
  full_name='spotify.playlist4.proto.SubscribeRequest',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='uris', full_name='spotify.playlist4.proto.SubscribeRequest.uris', index=0,
      number=1, type=12, cpp_type=9, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1339,
  serialized_end=1371,
)


_UNSUBSCRIBEREQUEST = descriptor.Descriptor(
  name='UnsubscribeRequest',
  full_name='spotify.playlist4.proto.UnsubscribeRequest',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='uris', full_name='spotify.playlist4.proto.UnsubscribeRequest.uris', index=0,
      number=1, type=12, cpp_type=9, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1373,
  serialized_end=1407,
)


_PLAYLIST4SERVICEEXCEPTION = descriptor.Descriptor(
  name='Playlist4ServiceException',
  full_name='spotify.playlist4.proto.Playlist4ServiceException',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='why', full_name='spotify.playlist4.proto.Playlist4ServiceException.why', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='symbol', full_name='spotify.playlist4.proto.Playlist4ServiceException.symbol', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='permanent', full_name='spotify.playlist4.proto.Playlist4ServiceException.permanent', index=2,
      number=3, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='serviceErrorClass', full_name='spotify.playlist4.proto.Playlist4ServiceException.serviceErrorClass', index=3,
      number=4, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='inboxErrorKind', full_name='spotify.playlist4.proto.Playlist4ServiceException.inboxErrorKind', index=4,
      number=5, type=14, cpp_type=8, label=1,
      has_default_value=False, default_value=2,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1410,
  serialized_end=1586,
)


_SYNCHRONIZERETURN = descriptor.Descriptor(
  name='SynchronizeReturn',
  full_name='spotify.playlist4.proto.SynchronizeReturn',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='result', full_name='spotify.playlist4.proto.SynchronizeReturn.result', index=0,
      number=1, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='exception', full_name='spotify.playlist4.proto.SynchronizeReturn.exception', index=1,
      number=4, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1589,
  serialized_end=1741,
)


_PLAYLIST4SERVICECALL = descriptor.Descriptor(
  name='Playlist4ServiceCall',
  full_name='spotify.playlist4.proto.Playlist4ServiceCall',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='kind', full_name='spotify.playlist4.proto.Playlist4ServiceCall.kind', index=0,
      number=1, type=14, cpp_type=8, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='getCurrentRevisionArgs', full_name='spotify.playlist4.proto.Playlist4ServiceCall.getCurrentRevisionArgs', index=1,
      number=2, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='getChangesInSequenceRangeArgs', full_name='spotify.playlist4.proto.Playlist4ServiceCall.getChangesInSequenceRangeArgs', index=2,
      number=3, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='obliterateListArgs', full_name='spotify.playlist4.proto.Playlist4ServiceCall.obliterateListArgs', index=3,
      number=4, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='synchronizeArgs', full_name='spotify.playlist4.proto.Playlist4ServiceCall.synchronizeArgs', index=4,
      number=5, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='updatePublishedArgs', full_name='spotify.playlist4.proto.Playlist4ServiceCall.updatePublishedArgs', index=5,
      number=6, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='getChangesInSequenceRangeMatchingPl3VersionArgs', full_name='spotify.playlist4.proto.Playlist4ServiceCall.getChangesInSequenceRangeMatchingPl3VersionArgs', index=6,
      number=7, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='getSnapshotAtRevisionArgs', full_name='spotify.playlist4.proto.Playlist4ServiceCall.getSnapshotAtRevisionArgs', index=7,
      number=8, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1744,
  serialized_end=2443,
)


_PLAYLIST4SERVICERETURN = descriptor.Descriptor(
  name='Playlist4ServiceReturn',
  full_name='spotify.playlist4.proto.Playlist4ServiceReturn',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='kind', full_name='spotify.playlist4.proto.Playlist4ServiceReturn.kind', index=0,
      number=1, type=14, cpp_type=8, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='exception', full_name='spotify.playlist4.proto.Playlist4ServiceReturn.exception', index=1,
      number=2, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='getCurrentRevisionReturn', full_name='spotify.playlist4.proto.Playlist4ServiceReturn.getCurrentRevisionReturn', index=2,
      number=3, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value="",
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='getChangesInSequenceRangeReturn', full_name='spotify.playlist4.proto.Playlist4ServiceReturn.getChangesInSequenceRangeReturn', index=3,
      number=4, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='obliterateListReturn', full_name='spotify.playlist4.proto.Playlist4ServiceReturn.obliterateListReturn', index=4,
      number=5, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='synchronizeReturn', full_name='spotify.playlist4.proto.Playlist4ServiceReturn.synchronizeReturn', index=5,
      number=6, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='updatePublishedReturn', full_name='spotify.playlist4.proto.Playlist4ServiceReturn.updatePublishedReturn', index=6,
      number=7, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='getChangesInSequenceRangeMatchingPl3VersionReturn', full_name='spotify.playlist4.proto.Playlist4ServiceReturn.getChangesInSequenceRangeMatchingPl3VersionReturn', index=7,
      number=8, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=2446,
  serialized_end=2990,
)


_CREATELISTREPLY = descriptor.Descriptor(
  name='CreateListReply',
  full_name='spotify.playlist4.proto.CreateListReply',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='uri', full_name='spotify.playlist4.proto.CreateListReply.uri', index=0,
      number=1, type=12, cpp_type=9, label=2,
      has_default_value=False, default_value="",
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='revision', full_name='spotify.playlist4.proto.CreateListReply.revision', index=1,
      number=2, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value="",
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=2992,
  serialized_end=3040,
)

_GETCURRENTREVISIONARGS.fields_by_name['context'].message_type = _REQUESTCONTEXT
_GETCHANGESINSEQUENCERANGEARGS.fields_by_name['context'].message_type = _REQUESTCONTEXT
_GETCHANGESINSEQUENCERANGEMATCHINGPL3VERSIONARGS.fields_by_name['context'].message_type = _REQUESTCONTEXT
_GETCHANGESINSEQUENCERANGERETURN.fields_by_name['result'].message_type = playlist4changes_pb2._REVISIONTAGGEDCHANGESET
_OBLITERATELISTARGS.fields_by_name['context'].message_type = _REQUESTCONTEXT
_UPDATEPUBLISHEDARGS.fields_by_name['context'].message_type = _REQUESTCONTEXT
_SYNCHRONIZEARGS.fields_by_name['context'].message_type = _REQUESTCONTEXT
_SYNCHRONIZEARGS.fields_by_name['selection'].message_type = playlist4content_pb2._LISTCONTENTSELECTION
_SYNCHRONIZEARGS.fields_by_name['changes'].message_type = playlist4changes_pb2._LISTCHANGES
_GETSNAPSHOTATREVISIONARGS.fields_by_name['context'].message_type = _REQUESTCONTEXT
_PLAYLIST4SERVICEEXCEPTION.fields_by_name['inboxErrorKind'].enum_type = _PLAYLIST4INBOXERRORKIND
_SYNCHRONIZERETURN.fields_by_name['result'].message_type = playlist4changes_pb2._SELECTEDLISTCONTENT
_SYNCHRONIZERETURN.fields_by_name['exception'].message_type = _PLAYLIST4SERVICEEXCEPTION
_PLAYLIST4SERVICECALL.fields_by_name['kind'].enum_type = _PLAYLIST4SERVICEMETHODKIND
_PLAYLIST4SERVICECALL.fields_by_name['getCurrentRevisionArgs'].message_type = _GETCURRENTREVISIONARGS
_PLAYLIST4SERVICECALL.fields_by_name['getChangesInSequenceRangeArgs'].message_type = _GETCHANGESINSEQUENCERANGEARGS
_PLAYLIST4SERVICECALL.fields_by_name['obliterateListArgs'].message_type = _OBLITERATELISTARGS
_PLAYLIST4SERVICECALL.fields_by_name['synchronizeArgs'].message_type = _SYNCHRONIZEARGS
_PLAYLIST4SERVICECALL.fields_by_name['updatePublishedArgs'].message_type = _UPDATEPUBLISHEDARGS
_PLAYLIST4SERVICECALL.fields_by_name['getChangesInSequenceRangeMatchingPl3VersionArgs'].message_type = _GETCHANGESINSEQUENCERANGEMATCHINGPL3VERSIONARGS
_PLAYLIST4SERVICECALL.fields_by_name['getSnapshotAtRevisionArgs'].message_type = _GETSNAPSHOTATREVISIONARGS
_PLAYLIST4SERVICERETURN.fields_by_name['kind'].enum_type = _PLAYLIST4SERVICEMETHODKIND
_PLAYLIST4SERVICERETURN.fields_by_name['exception'].message_type = _PLAYLIST4SERVICEEXCEPTION
_PLAYLIST4SERVICERETURN.fields_by_name['getChangesInSequenceRangeReturn'].message_type = _GETCHANGESINSEQUENCERANGERETURN
_PLAYLIST4SERVICERETURN.fields_by_name['synchronizeReturn'].message_type = _SYNCHRONIZERETURN
_PLAYLIST4SERVICERETURN.fields_by_name['getChangesInSequenceRangeMatchingPl3VersionReturn'].message_type = _GETCHANGESINSEQUENCERANGERETURN
DESCRIPTOR.message_types_by_name['RequestContext'] = _REQUESTCONTEXT
DESCRIPTOR.message_types_by_name['GetCurrentRevisionArgs'] = _GETCURRENTREVISIONARGS
DESCRIPTOR.message_types_by_name['GetChangesInSequenceRangeArgs'] = _GETCHANGESINSEQUENCERANGEARGS
DESCRIPTOR.message_types_by_name['GetChangesInSequenceRangeMatchingPl3VersionArgs'] = _GETCHANGESINSEQUENCERANGEMATCHINGPL3VERSIONARGS
DESCRIPTOR.message_types_by_name['GetChangesInSequenceRangeReturn'] = _GETCHANGESINSEQUENCERANGERETURN
DESCRIPTOR.message_types_by_name['ObliterateListArgs'] = _OBLITERATELISTARGS
DESCRIPTOR.message_types_by_name['UpdatePublishedArgs'] = _UPDATEPUBLISHEDARGS
DESCRIPTOR.message_types_by_name['SynchronizeArgs'] = _SYNCHRONIZEARGS
DESCRIPTOR.message_types_by_name['GetSnapshotAtRevisionArgs'] = _GETSNAPSHOTATREVISIONARGS
DESCRIPTOR.message_types_by_name['SubscribeRequest'] = _SUBSCRIBEREQUEST
DESCRIPTOR.message_types_by_name['UnsubscribeRequest'] = _UNSUBSCRIBEREQUEST
DESCRIPTOR.message_types_by_name['Playlist4ServiceException'] = _PLAYLIST4SERVICEEXCEPTION
DESCRIPTOR.message_types_by_name['SynchronizeReturn'] = _SYNCHRONIZERETURN
DESCRIPTOR.message_types_by_name['Playlist4ServiceCall'] = _PLAYLIST4SERVICECALL
DESCRIPTOR.message_types_by_name['Playlist4ServiceReturn'] = _PLAYLIST4SERVICERETURN
DESCRIPTOR.message_types_by_name['CreateListReply'] = _CREATELISTREPLY

class RequestContext(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _REQUESTCONTEXT
  
  # @@protoc_insertion_point(class_scope:spotify.playlist4.proto.RequestContext)

class GetCurrentRevisionArgs(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _GETCURRENTREVISIONARGS
  
  # @@protoc_insertion_point(class_scope:spotify.playlist4.proto.GetCurrentRevisionArgs)

class GetChangesInSequenceRangeArgs(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _GETCHANGESINSEQUENCERANGEARGS
  
  # @@protoc_insertion_point(class_scope:spotify.playlist4.proto.GetChangesInSequenceRangeArgs)

class GetChangesInSequenceRangeMatchingPl3VersionArgs(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _GETCHANGESINSEQUENCERANGEMATCHINGPL3VERSIONARGS
  
  # @@protoc_insertion_point(class_scope:spotify.playlist4.proto.GetChangesInSequenceRangeMatchingPl3VersionArgs)

class GetChangesInSequenceRangeReturn(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _GETCHANGESINSEQUENCERANGERETURN
  
  # @@protoc_insertion_point(class_scope:spotify.playlist4.proto.GetChangesInSequenceRangeReturn)

class ObliterateListArgs(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _OBLITERATELISTARGS
  
  # @@protoc_insertion_point(class_scope:spotify.playlist4.proto.ObliterateListArgs)

class UpdatePublishedArgs(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _UPDATEPUBLISHEDARGS
  
  # @@protoc_insertion_point(class_scope:spotify.playlist4.proto.UpdatePublishedArgs)

class SynchronizeArgs(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _SYNCHRONIZEARGS
  
  # @@protoc_insertion_point(class_scope:spotify.playlist4.proto.SynchronizeArgs)

class GetSnapshotAtRevisionArgs(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _GETSNAPSHOTATREVISIONARGS
  
  # @@protoc_insertion_point(class_scope:spotify.playlist4.proto.GetSnapshotAtRevisionArgs)

class SubscribeRequest(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _SUBSCRIBEREQUEST
  
  # @@protoc_insertion_point(class_scope:spotify.playlist4.proto.SubscribeRequest)

class UnsubscribeRequest(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _UNSUBSCRIBEREQUEST
  
  # @@protoc_insertion_point(class_scope:spotify.playlist4.proto.UnsubscribeRequest)

class Playlist4ServiceException(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _PLAYLIST4SERVICEEXCEPTION
  
  # @@protoc_insertion_point(class_scope:spotify.playlist4.proto.Playlist4ServiceException)

class SynchronizeReturn(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _SYNCHRONIZERETURN
  
  # @@protoc_insertion_point(class_scope:spotify.playlist4.proto.SynchronizeReturn)

class Playlist4ServiceCall(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _PLAYLIST4SERVICECALL
  
  # @@protoc_insertion_point(class_scope:spotify.playlist4.proto.Playlist4ServiceCall)

class Playlist4ServiceReturn(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _PLAYLIST4SERVICERETURN
  
  # @@protoc_insertion_point(class_scope:spotify.playlist4.proto.Playlist4ServiceReturn)

class CreateListReply(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CREATELISTREPLY
  
  # @@protoc_insertion_point(class_scope:spotify.playlist4.proto.CreateListReply)

# @@protoc_insertion_point(module_scope)

########NEW FILE########
__FILENAME__ = toplist_pb2
# Generated by the protocol buffer compiler.  DO NOT EDIT!

from google.protobuf import descriptor
from google.protobuf import message
from google.protobuf import reflection
from google.protobuf import descriptor_pb2
# @@protoc_insertion_point(imports)



DESCRIPTOR = descriptor.FileDescriptor(
  name='toplist.proto',
  package='',
  serialized_pb='\n\rtoplist.proto\"\x18\n\x07Toplist\x12\r\n\x05items\x18\x01 \x03(\t')




_TOPLIST = descriptor.Descriptor(
  name='Toplist',
  full_name='Toplist',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='items', full_name='Toplist.items', index=0,
      number=1, type=9, cpp_type=9, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=17,
  serialized_end=41,
)

DESCRIPTOR.message_types_by_name['Toplist'] = _TOPLIST

class Toplist(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _TOPLIST
  
  # @@protoc_insertion_point(class_scope:Toplist)

# @@protoc_insertion_point(module_scope)

########NEW FILE########
__FILENAME__ = spotify
#!/usr/bin/python
import re
import json
import operator
import binascii
import base64
from ssl import SSLError
from threading import Thread, Event, Lock

import requests
from ws4py.client.threadedclient import WebSocketClient

from .proto import mercury_pb2, metadata_pb2, playlist4changes_pb2,\
    playlist4ops_pb2, playlist4service_pb2, toplist_pb2

# from .proto import playlist4meta_pb2, playlist4issues_pb2,
# playlist4content_pb2


base62 = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"


class Logging():
    log_level = 1

    @staticmethod
    def debug(str):
        if Logging.log_level >= 3:
            print "[DEBUG] " + str

    @staticmethod
    def notice(str):
        if Logging.log_level >= 2:
            print "[NOTICE] " + str

    @staticmethod
    def warn(str):
        if Logging.log_level >= 1:
            print "[WARN] " + str

    @staticmethod
    def error(str):
        if Logging.log_level >= 0:
            print "[ERROR] " + str


class WrapAsync():
    timeout = 10

    def __init__(self, callback, func, *args):
        self.marker = Event()

        if callback is None:
            callback = self.callback
        elif type(callback) == list:
            callback = callback+[self.callback]
        else:
            callback = [callback, self.callback]

        self.data = False
        func(*args, callback=callback)

    def callback(self, *args):
        self.data = args
        self.marker.set()

    def get_data(self):
        try:
            self.marker.wait(timeout=self.timeout)

            if len(self.data) > 0 and type(self.data[0] == SpotifyAPI):
                self.data = self.data[1:]

            return self.data if len(self.data) > 1 else self.data[0]
        except:
            return False


class SpotifyClient(WebSocketClient):
    def set_api(self, api):
        self.api_object = api

    def opened(self):
        self.api_object.login()

    def received_message(self, m):
        self.api_object.recv_packet(m)

    def closed(self, code, message):
        self.api_object.shutdown()


class SpotifyUtil():
    @staticmethod
    def gid2id(gid):
        return binascii.hexlify(gid).rjust(32, "0")

    @staticmethod
    def id2uri(uritype, v):
        res = []
        v = int(v, 16)
        while v > 0:
            res = [v % 62] + res
            v /= 62
        id = ''.join([base62[i] for i in res])
        return ("spotify:"+uritype+":"+id).rjust(22, "0")

    @staticmethod
    def uri2id(uri):
        parts = uri.split(":")
        if len(parts) > 3 and parts[3] == "playlist":
            s = parts[4]
        else:
            s = parts[2]

        v = 0
        for c in s:
            v = v * 62 + base62.index(c)
        return hex(v)[2:-1].rjust(32, "0")

    @staticmethod
    def gid2uri(uritype, gid):
        id = SpotifyUtil.gid2id(gid)
        uri = SpotifyUtil.id2uri(uritype, id)
        return uri

    @staticmethod
    def get_uri_type(uri):
        uri_parts = uri.split(":")

        if len(uri_parts) >= 3 and uri_parts[1] == "local":
            return "local"
        elif len(uri_parts) >= 5:
            return uri_parts[3]
        elif len(uri_parts) >= 4 and uri_parts[3] == "starred":
            return "playlist"
        elif len(uri_parts) >= 3:
            return uri_parts[1]
        else:
            return False

    @staticmethod
    def is_local(uri):
        return SpotifyUtil.get_uri_type(uri) == "local"


class SpotifyAPI():
    def __init__(self, login_callback_func=False):
        self.auth_server = "play.spotify.com"

        self.logged_in_marker = Event()
        self.heartbeat_marker = Event()
        self.username = None
        self.password = None
        self.account_type = None
        self.country = None

        self.settings = None

        self.disconnecting = False
        self.ws = None
        self.ws_lock = Lock()
        self.seq = 0
        self.cmd_callbacks = {}
        self.login_callback = login_callback_func
        self.is_logged_in = False

    def auth(self, username, password):
        if self.settings is not None:
            Logging.warn("You must only authenticate once per API object")
            return False

        headers = {
            #"User-Agent": "node-spotify-web in python (Chrome/13.37 compatible-ish)",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/31.0.1650.63 Safari/537.36"
        }

        session = requests.session()

        resp = session.get("https://" + self.auth_server, headers=headers)
        data = resp.text

        #csrftoken
        rx = re.compile("\"csrftoken\":\"(.*?)\"")
        r = rx.search(data)

        if not r or len(r.groups()) < 1:
            Logging.error("There was a problem authenticating, no auth secret found")
            self.do_login_callback(False)
            return False
        secret = r.groups()[0]

        #trackingID
        rx = re.compile("\"trackingId\":\"(.*?)\"")
        r = rx.search(data)

        if not r or len(r.groups()) < 1:
            Logging.error("There was a problem authenticating, no auth trackingId found")
            self.do_login_callback(False)
            return False
        trackingId = r.groups()[0]

        #referrer
        rx = re.compile("\"referrer\":\"(.*?)\"")
        r = rx.search(data)

        if not r or len(r.groups()) < 1:
            Logging.error("There was a problem authenticating, no auth referrer found")
            self.do_login_callback(False)
            return False
        referrer = r.groups()[0]

        #landingURL
        rx = re.compile("\"landingURL\":\"(.*?)\"")
        r = rx.search(data)

        if not r or len(r.groups()) < 1:
            Logging.error("There was a problem authenticating, no auth landingURL found")
            self.do_login_callback(False)
            return False
        landingURL = r.groups()[0]

        login_payload = {
            "type": "sp",
            "username": username,
            "password": password,
            "secret": secret,
            "trackingId":trackingId,
            "referrer": referrer,
            "landingURL": landingURL,
            "cf":"",
        }

        Logging.notice(str(login_payload))
        
        resp = session.post("https://" + self.auth_server + "/xhr/json/auth.php", data=login_payload, headers=headers)
        resp_json = resp.json()

        if resp_json["status"] != "OK":
            Logging.error("There was a problem authenticating, authentication failed")
            self.do_login_callback(False)
            return False

        self.settings = resp.json()["config"]

        #Get wss settings
        resolver_payload = {
            "client": "24:0:0:" + str(self.settings["version"])
        }

        resp = session.get('http://' + self.settings["aps"]["resolver"]["hostname"], params=resolver_payload, headers=headers)

        resp_json = resp.json()
        wss_hostname = resp_json["ap_list"][0].split(":")[0]

        self.settings["wss"] = "wss://" + wss_hostname + "/"

        return True

    def populate_userdata_callback(self, sp, resp):
        
        # Send screen size
        self.send_command("sp/log", [41, 1, 0, 0, 0, 0], None)
        
        self.username = resp["user"]
        self.country = resp["country"]
        self.account_type = resp["catalogue"]

        # If you're thinking about changing this: don't.
        # I don't want to play cat and mouse with Spotify.
        # I just want an open-library that works for paying
        # users.
        magic = base64.b64encode(resp["catalogue"]) == "cHJlbWl1bQ=="
        self.is_logged_in = True if magic else False

        if not magic:
            Logging.error("Please upgrade to Premium")
            self.disconnect()
        else:
            heartbeat_thread = Thread(target=self.heartbeat_handler)
            heartbeat_thread.daemon = True
            heartbeat_thread.start()

        if self.login_callback:
            self.do_login_callback(self.is_logged_in)
        else:
            self.logged_in_marker.set()

    def logged_in(self, sp, resp):
        self.user_info_request(self.populate_userdata_callback)

    def login(self):
        Logging.notice("Logging in")
        credentials = self.settings["credentials"][0].split(":", 2)
        credentials[2] = credentials[2].decode("string_escape")
        # credentials_enc = json.dumps(credentials, separators=(',',':'))

        self.send_command("connect", credentials, self.logged_in)

    def do_login_callback(self, result):
        if self.login_callback:
            Thread(target=self.login_callback, args=(self, result)).start()
        else:
            self.logged_in_marker.set()

    def track_uri(self, track, callback=False):
        track = self.recurse_alternatives(track)
        if not track:
            return False
        args = ["mp3160", SpotifyUtil.gid2id(track.gid)]
        return self.wrap_request("sp/track_uri", args, callback)

    def parse_metadata(self, sp, resp, callback_data):
        header = mercury_pb2.MercuryReply()
        header.ParseFromString(base64.decodestring(resp[0]))

        if header.status_message == "vnd.spotify/mercury-mget-reply":
            if len(resp) < 2:
                ret = False

            mget_reply = mercury_pb2.MercuryMultiGetReply()
            mget_reply.ParseFromString(base64.decodestring(resp[1]))
            items = []
            for reply in mget_reply.reply:
                if reply.status_code != 200:
                    continue

                item = self.parse_metadata_item(reply.content_type, reply.body)
                items.append(item)
            ret = items
        else:
            ret = self.parse_metadata_item(header.status_message, base64.decodestring(resp[1]))

        self.chain_callback(sp, ret, callback_data)

    def parse_metadata_item(self, content_type, body):
        if content_type == "vnd.spotify/metadata-album":
            obj = metadata_pb2.Album()
        elif content_type == "vnd.spotify/metadata-artist":
            obj = metadata_pb2.Artist()
        elif content_type == "vnd.spotify/metadata-track":
            obj = metadata_pb2.Track()
        else:
            Logging.error("Unrecognised metadata type " + content_type)
            return False

        obj.ParseFromString(body)

        return obj

    def parse_toplist(self, sp, resp, callback_data):
        obj = toplist_pb2.Toplist()
        res = base64.decodestring(resp[1])
        obj.ParseFromString(res)
        self.chain_callback(sp, obj, callback_data)

    def parse_playlist(self, sp, resp, callback_data):
        obj = playlist4changes_pb2.ListDump()
        try:
            res = base64.decodestring(resp[1])
            obj.ParseFromString(res)
        except:
            obj = False

        self.chain_callback(sp, obj, callback_data)

    def chain_callback(self, sp, data, callback_data):
        if len(callback_data) > 1:
            callback_data[0](self, data, callback_data[1:])
        elif len(callback_data) == 1:
            callback_data[0](self, data)

    def is_track_available(self, track, country):
        allowed_countries = []
        forbidden_countries = []
        available = False

        for restriction in track.restriction:
            allowed_str = restriction.countries_allowed
            allowed_countries += [allowed_str[i:i+2] for i in range(0, len(allowed_str), 2)]

            forbidden_str = restriction.countries_forbidden
            forbidden_countries += [forbidden_str[i:i+2] for i in range(0, len(forbidden_str), 2)]

            allowed = not restriction.HasField("countries_allowed") or country in allowed_countries
            forbidden = self.country in forbidden_countries and len(forbidden_countries) > 0

            if country in allowed_countries and country in forbidden_countries:
                allowed = True
                forbidden = False

            # guessing at names here, corrections welcome
            account_type_map = {
                "premium": 1,
                "unlimited": 1,
                "free": 0
            }

            applicable = account_type_map[self.account_type] in restriction.catalogue

            # enable this to help debug restriction issues
            if False:
                print restriction
                print allowed_countries
                print forbidden_countries
                print "allowed: "+str(allowed)
                print "forbidden: "+str(forbidden)
                print "applicable: "+str(applicable)

            available = True == allowed and False == forbidden and True == applicable
            if available:
                break

        if available:
            Logging.notice(SpotifyUtil.gid2uri("track", track.gid) + " is available!")
        else:
            Logging.notice(SpotifyUtil.gid2uri("track", track.gid) + " is NOT available!")

        return available

    def recurse_alternatives(self, track, attempted=None, country=None):
        if not attempted:
            attempted = []
        country = self.country if country is None else country
        if self.is_track_available(track, country):
            return track
        else:
            for alternative in track.alternative:
                if self.is_track_available(alternative, country):
                    return alternative
            return False
            for alternative in track.alternative:
                uri = SpotifyUtil.gid2uri("track", alternative.gid)
                if uri not in attempted:
                    attempted += [uri]
                    subtrack = self.metadata_request(uri)
                    return self.recurse_alternatives(subtrack, attempted)
            return False

    def generate_multiget_args(self, metadata_type, requests):
        args = [0]

        if len(requests.request) == 1:
            req = base64.encodestring(requests.request[0].SerializeToString())
            args.append(req)
        else:
            header = mercury_pb2.MercuryRequest()
            header.body = "GET"
            header.uri = "hm://metadata/"+metadata_type+"s"
            header.content_type = "vnd.spotify/mercury-mget-request"

            header_str = base64.encodestring(header.SerializeToString())
            req = base64.encodestring(requests.SerializeToString())
            args.extend([header_str, req])

        return args

    def wrap_request(self, command, args, callback, int_callback=None, retries=3):
        if not callback:
            for attempt in range(0, retries):
                data = WrapAsync(int_callback, self.send_command, command, args).get_data()
                if data:
                    break
            return data
        else:
            callback = [callback] if type(callback) != list else callback
            if int_callback is not None:
                int_callback = [int_callback] if type(int_callback) != list else int_callback
                callback += int_callback
            self.send_command(command, args, callback)

    def metadata_request(self, uris, callback=False):
        mercury_requests = mercury_pb2.MercuryMultiGetRequest()

        if type(uris) != list:
            uris = [uris]

        for uri in uris:
            uri_type = SpotifyUtil.get_uri_type(uri)
            if uri_type == "local":
                Logging.warn("Track with URI "+uri+" is a local track, we can't request metadata, skipping")
                continue

            id = SpotifyUtil.uri2id(uri)

            mercury_request = mercury_pb2.MercuryRequest()
            mercury_request.body = "GET"
            mercury_request.uri = "hm://metadata/"+uri_type+"/"+id

            mercury_requests.request.extend([mercury_request])

        args = self.generate_multiget_args(SpotifyUtil.get_uri_type(uris[0]), mercury_requests)

        return self.wrap_request("sp/hm_b64", args, callback, self.parse_metadata)

    def toplist_request(self, toplist_content_type="track", toplist_type="user", username=None, region="global", callback=False):
        if username is None:
            username = self.username

        mercury_request = mercury_pb2.MercuryRequest()
        mercury_request.body = "GET"
        if toplist_type == "user":
            mercury_request.uri = "hm://toplist/toplist/user/"+username
        elif toplist_type == "region":
            mercury_request.uri = "hm://toplist/toplist/region"
            if region is not None and region != "global":
                mercury_request.uri += "/"+region
        else:
            return False
        mercury_request.uri += "?type="+toplist_content_type

        # playlists don't appear to work?
        if toplist_type == "user" and toplist_content_type == "playlist":
            if username != self.username:
                return False
            mercury_request.uri = "hm://socialgraph/suggestions/topplaylists"

        req = base64.encodestring(mercury_request.SerializeToString())

        args = [0, req]

        return self.wrap_request("sp/hm_b64", args, callback, self.parse_toplist)

    def playlists_request(self, user, fromnum=0, num=100, callback=False):
        if num > 100:
            Logging.error("You may only request up to 100 playlists at once")
            return False

        mercury_request = mercury_pb2.MercuryRequest()
        mercury_request.body = "GET"
        mercury_request.uri = "hm://playlist/user/"+user+"/rootlist?from=" + str(fromnum) + "&length=" + str(num)
        req = base64.encodestring(mercury_request.SerializeToString())

        args = [0, req]

        return self.wrap_request("sp/hm_b64", args, callback, self.parse_playlist)

    def playlist_request(self, uri, fromnum=0, num=100, callback=False):
        # mercury_requests = mercury_pb2.MercuryRequest()

        playlist = uri[8:].replace(":", "/")
        mercury_request = mercury_pb2.MercuryRequest()
        mercury_request.body = "GET"
        mercury_request.uri = "hm://playlist/" + playlist + "?from=" + str(fromnum) + "&length=" + str(num)

        req = base64.encodestring(mercury_request.SerializeToString())
        args = [0, req]

        return self.wrap_request("sp/hm_b64", args, callback, self.parse_playlist)

    def playlist_op_track(self, playlist_uri, track_uri, op, callback=None):
        playlist = playlist_uri.split(":")

        if playlist_uri == "rootlist":
            user = self.username
            playlist_id = "rootlist"
        else:
            user = playlist[2]
            if playlist[3] == "starred":
                playlist_id = "starred"
            else:
                playlist_id = "playlist/"+playlist[4]

        mercury_request = mercury_pb2.MercuryRequest()
        mercury_request.body = op
        mercury_request.uri = "hm://playlist/user/"+user+"/" + playlist_id + "?syncpublished=1"
        req = base64.encodestring(mercury_request.SerializeToString())
        args = [0, req, base64.encodestring(track_uri)]
        return self.wrap_request("sp/hm_b64", args, callback)

    def playlist_add_track(self, playlist_uri, track_uri, callback=False):
        return self.playlist_op_track(playlist_uri, track_uri, "ADD", callback)

    def playlist_remove_track(self, playlist_uri, track_uri, callback=False):
        return self.playlist_op_track(playlist_uri, track_uri, "REMOVE", callback)

    def set_starred(self, track_uri, starred=True, callback=False):
        if starred:
            return self.playlist_add_track("spotify:user:"+self.username+":starred", track_uri, callback)
        else:
            return self.playlist_remove_track("spotify:user:"+self.username+":starred", track_uri, callback)

    def playlist_op(self, op, path, optype="update", name=None, index=None, callback=None):
        mercury_request = mercury_pb2.MercuryRequest()
        mercury_request.body = op
        mercury_request.uri = "hm://" + path

        req = base64.encodestring(mercury_request.SerializeToString())

        op = playlist4ops_pb2.Op()
        if optype == "update":
            op.kind = playlist4ops_pb2.Op.UPDATE_LIST_ATTRIBUTES
            op.update_list_attributes.new_attributes.values.name = name
        elif optype == "remove":
            op.kind = playlist4ops_pb2.Op.REM
            op.rem.fromIndex = index
            op.rem.length = 1

        mercury_request_payload = mercury_pb2.MercuryRequest()
        mercury_request_payload.uri = op.SerializeToString()

        payload = base64.encodestring(mercury_request_payload.SerializeToString())

        args = [0, req, payload]
        return self.wrap_request("sp/hm_b64", args, callback, self.new_playlist_callback)

    def new_playlist(self, name, callback=False):
        return self.playlist_op("PUT", "playlist/user/"+self.username, name=name, callback=callback)

    def rename_playlist(self, playlist_uri, name, callback=False):
        path = "playlist/user/"+self.username+"/playlist/"+playlist_uri.split(":")[4]+"?syncpublished=true"
        return self.playlist_op("MODIFY", path, name=name, callback=callback)

    def remove_playlist(self, playlist_uri, callback=False):
        return self.playlist_op_track("rootlist", playlist_uri, "REMOVE", callback=callback)
        #return self.playlist_op("REMOVE", "playlist/user/"+self.username+"/rootlist?syncpublished=true",
                                #optype="remove", index=index, callback=callback)

    def new_playlist_callback(self, sp, data, callback_data):
        try:
            reply = playlist4service_pb2.CreateListReply()
            reply.ParseFromString(base64.decodestring(data[1]))
        except:
            self.chain_callback(sp, False, callback_data)

        mercury_request = mercury_pb2.MercuryRequest()
        mercury_request.body = "ADD"
        mercury_request.uri = "hm://playlist/user/"+self.username+"/rootlist?add_first=1&syncpublished=1"
        req = base64.encodestring(mercury_request.SerializeToString())
        args = [0, req, base64.encodestring(reply.uri)]

        self.chain_callback(sp, reply.uri, callback_data)
        self.send_command("sp/hm_b64", args)

    def search_request(self, query, query_type="all", max_results=50, offset=0, callback=False):
        if max_results > 50:
            Logging.warn("Maximum of 50 results per request, capping at 50")
            max_results = 50

        search_types = {
            "tracks": 1,
            "albums": 2,
            "artists": 4,
            "playlists": 8

        }

        query_type = [k for k, v in search_types.items()] if query_type == "all" else query_type
        query_type = [query_type] if type(query_type) != list else query_type
        query_type = reduce(operator.or_, [search_types[type_name] for type_name in query_type if type_name in search_types])

        args = [query, query_type, max_results, offset]

        return self.wrap_request("sp/search", args, callback)

    def user_info_request(self, callback=None):
        return self.wrap_request("sp/user_info", [], callback)

    def heartbeat(self):
        self.send_command("sp/echo", "h", callback=False)

    def send_track_end(self, lid, track_uri, ms_played, callback=False):
        ms_played = int(ms_played)
        ms_played_union = ms_played
        n_seeks_forward = 0
        n_seeks_backward = 0
        ms_seeks_forward = 0
        ms_seeks_backward = 0
        ms_latency = 100
        display_track = None
        play_context = "unknown"
        source_start = "unknown"
        source_end = "unknown"
        reason_start = "unknown"
        reason_end = "unknown"
        referrer = "unknown"
        referrer_version = "0.1.0"
        referrer_vendor = "com.spotify"
        max_continuous = ms_played
        args = [lid, ms_played, ms_played_union, n_seeks_forward, n_seeks_backward, ms_seeks_forward, ms_seeks_backward, ms_latency, display_track, play_context, source_start, source_end, reason_start, reason_end, referrer, referrer_version, referrer_vendor, max_continuous]
        return self.wrap_request("sp/track_end", args, callback)

    def send_track_event(self, lid, event, ms_where, callback=False):
        if event == "pause" or event == "stop":
            ev_n = 4
        elif event == "unpause" or "continue" or "play":
            ev_n = 3
        else:
            return False
        return self.wrap_request("sp/track_event", [lid, ev_n, int(ms_where)], callback)

    def send_track_progress(self, lid, ms_played, callback=False):
        source_start = "unknown"
        reason_start = "unknown"
        ms_latency = 100
        play_context = "unknown"
        display_track = ""
        referrer = "unknown"
        referrer_version = "0.1.0"
        referrer_vendor = "com.spotify"
        args = [lid, source_start, reason_start, int(ms_played), int(ms_latency), play_context, display_track, referrer, referrer_version, referrer_vendor]
        return self.wrap_request("sp/track_progress", args, callback)

    def send_command(self, name, args=None, callback=None):
        if not args:
            args = []
        msg = {
            "name": name,
            "id": str(self.seq),
            "args": args
        }

        if callback is not None:
            self.cmd_callbacks[self.seq] = callback
        self.seq += 1

        self.send_string(msg)

    def send_string(self, msg):
        if self.disconnecting:
            return

        msg_enc = json.dumps(msg, separators=(',', ':'))
        Logging.debug("sent " + msg_enc)
        try:
            with self.ws_lock:
                self.ws.send(msg_enc)
        except SSLError:
            Logging.notice("SSL error, attempting to continue")

    def recv_packet(self, msg):
        Logging.debug("recv " + str(msg))
        packet = json.loads(str(msg))
        if "error" in packet:
            self.handle_error(packet)
            return
        elif "message" in packet:
            self.handle_message(packet["message"])
        elif "id" in packet:
            pid = packet["id"]
            if pid in self.cmd_callbacks:
                callback = self.cmd_callbacks[pid]

                if not callback:
                    Logging.debug("No callback was requested for command " + str(pid) + ", ignoring")
                elif type(callback) == list:
                    if len(callback) > 1:
                        callback[0](self, packet["result"], callback[1:])
                    else:
                        callback[0](self, packet["result"])
                else:
                    callback(self, packet["result"])

                self.cmd_callbacks.pop(pid)
            else:
                Logging.debug("Unhandled command response with id " + str(pid))

    def work_callback(self, sp, resp):
        Logging.debug("Got ack for message reply")

    def handle_message(self, msg):
        cmd = msg[0]
        if len(msg) > 1:
            payload = msg[1]
        if cmd == "do_work":
            Logging.debug("Got do_work message, payload: "+payload)
            self.send_command("sp/work_done", ["v1"], self.work_callback)
        if cmd == "ping_flash2":
            if len(msg[1]) >= 20:
                key = [[7, 203], [15, 15], [1, 96], [19, 93], [3, 165], [14, 130], [12, 16], [4, 6], [6, 225], [13, 37]]
                input = [ int(x) for x in msg[1].split(" ") ]
                pong = u' ' .join([unicode((input[i[0]] ^ i[1])) for i in key ])
                Logging.debug("Sending pong %s" % pong)
                self.send_command("sp/pong_flash2", [pong,], None)
        if cmd == "login_complete":
            Logging.debug("Login Complete")
	    self.user_info_request(self.populate_userdata_callback)
    def handle_error(self, err):
        if len(err) < 2:
            Logging.error("Unknown error "+str(err))

        major = err["error"][0]
        minor = err["error"][1]

        major_err = {
            8: "Rate request error",
            12: "Track error",
            13: "Hermes error",
            14: "Hermes service error",
        }

        minor_err = {
            1: "failed to send to backend",
            8: "rate limited",
            408: "timeout",
            429: "too many requests",
        }

        if major in major_err:
            major_str = major_err[major]
        else:
            major_str = "unknown (" + str(major) + ")"

        if minor in minor_err:
            minor_str = minor_err[minor]
        else:
            minor_str = "unknown (" + str(minor) + ")"

        if minor == 0:
            Logging.error(major_str)
        else:
            Logging.error(major_str + " - " + minor_str)

    def heartbeat_handler(self):
        while not self.disconnecting:
            self.heartbeat()
            self.heartbeat_marker.wait(timeout=18)

    def connect(self, username, password, timeout=10):
        if self.settings is None:
            if not self.auth(username, password):
                return False
            self.username = username
            self.password = password

        Logging.notice("Connecting to "+self.settings["wss"])
        
        try:
            self.ws = SpotifyClient(self.settings["wss"])
            self.ws.set_api(self)
            self.ws.daemon = True
            self.ws.connect()
            if not self.login_callback:
                try:
                    self.logged_in_marker.wait(timeout=timeout)
                    return self.is_logged_in
                except:
                    return False
        except:
            self.disconnect()
            return False

    def set_log_level(self, level):
        Logging.log_level = level

    def shutdown(self):
        self.disconnecting = True
        self.heartbeat_marker.set()

    def disconnect(self):
        if self.ws is not None:
            self.ws.close()

########NEW FILE########
__FILENAME__ = test
#!/usr/bin/env python

import os
import sys
import time
import unittest

from spotify_web.friendly import Spotify


class SpotifyTest(unittest.TestCase):
    def setUp(self):
        self.spotify = Spotify(USERNAME, PASSWORD)
        if not self.spotify.logged_in():
            print "Login failed"

    def tearDown(self):
        self.spotify.logout()

    def test_get_track_by_uri(self):
        test_uris = {
            "spotify:track:4DoiEk7AaubTkIkYencvx7": {
                "title": "Figure 8",
                "artist": "Ellie Goulding",
                "album": "Halcyon"
            },
            "spotify:track:6Qmmzzo9Sdk0QZp0dfLpGk": {
                "title": "Commander",
                "artist": "Kelly Rowland, David Guetta",
                "album": "Commander"
            }
        }

        for uri, reference in test_uris.items():
            track = self.spotify.objectFromURI(uri)
            self.assertEqual(reference["title"], track.getName())
            self.assertEqual(reference["artist"], track.getArtists(nameOnly=True))
            self.assertEqual(reference["album"], track.getAlbum(nameOnly=True))

    def test_playlist_add_delete(self):
        playlist_name = "unittests"
        before = len(self.spotify.getPlaylists())
        new_playlist = self.spotify.newPlaylist(playlist_name)
        time.sleep(2)
        playlist_names = [playlist.getName() for playlist in self.spotify.getPlaylists()]
        self.assertIn(playlist_name, playlist_names)
        self.assertEqual(before+1, len(self.spotify.getPlaylists()))

        self.spotify.removePlaylist(new_playlist)
        time.sleep(2)
        playlist_names = [playlist.getName() for playlist in self.spotify.getPlaylists()]
        self.assertNotIn(playlist_name, playlist_names)
        self.assertEqual(before, len(self.spotify.getPlaylists()))

if __name__ == '__main__':
    if "USERNAME" not in os.environ or "PASSWORD" not in os.environ:
        print "Missing USERNAME/PASSWORD environment variables"
        sys.exit(1)
    USERNAME = os.environ["USERNAME"]
    PASSWORD = os.environ["PASSWORD"]
    unittest.main()

########NEW FILE########
