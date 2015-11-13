__FILENAME__ = config
import sys
class config(object):
    import yaml, uuid, os, logging
    """
        Magical config class that allows for real-time updating of config variables.
        Every attribute access to this class (i.e.: config.config.thumbnail_size) will
        check the fmod time of the config YAML file, and read the file if necessary.

        Fast, although it does an os.stat on every attribute access. Worth it.
    """

    # Format of track identifiers (currently UUIDs)
    uid = lambda(self): str( object.__getattribute__(self, 'uuid').uuid4() ).replace( '-', '' )
    uid_re = r'[a-f0-9]{32}'

    last_updated = 0
    config_file = 'config.yml'
    
    def __init__(self):
        # Variables to be passed through to javascript.
        self.javascript = {
            'socket_io_port': self.socket_io_port,
            'remember_transport': False,
            'monitor_resource': self.monitor_resource,
            'progress_resource': self.progress_resource,
            'socket_extra_sep': self.socket_extra_sep,
            'allowed_file_extensions': [x[1:] for x in self.allowed_file_extensions],
            'drop_text': 'Drop a song here to remix!',
            'upload_text': 'Click here (or drag in a song) to create a remix.',
            'soundcloud_consumer': self.soundcloud_consumer,
            'soundcloud_redirect': self.soundcloud_redirect,
        }

    def update(self, filename=None):
        """
            Update the object's attributes.
        """
        object.__getattribute__(self, 'logging').getLogger().info("Config file has changed, updating...")
        if not filename:
            filename = object.__getattribute__(self, 'config_file')
        for k, v in object.__getattribute__(self, 'yaml').load(open(filename)).iteritems():
            setattr(self, k, v)

    def __getattribute__(self, name):
        """
            When trying to access an attribute, check if the underlying file has changed first.
        """
        if name in ['update', 'javascript', 'uid', 'uid_re']:
            return object.__getattribute__(self, name)
        else:
            last_updated = object.__getattribute__(self, 'last_updated')
            fmod_time = object.__getattribute__(self, 'os').stat(object.__getattribute__(self, 'config_file'))[9]
            if last_updated < fmod_time:
                self.last_updated = fmod_time
                self.update()
            return object.__getattribute__(self, name)

# This is a dirty, dirty hack, but lets you just do:
#   import config
# and have access to an instantiated config object.
sys.modules[__name__] = config()

########NEW FILE########
__FILENAME__ = database
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, scoped_session
from sqlalchemy.pool import QueuePool
from sqlalchemy import Column, Integer, CHAR, DateTime, String, ForeignKey, Boolean, Text, create_engine
import config, datetime

Base = declarative_base()

###
# Models
###

class Track(Base):
    __tablename__ = 'tracks'
    id = Column(Integer, primary_key=True)
    uid = Column(CHAR(length=32))
    time = Column(DateTime)
    hash = Column(CHAR(length=32))
    size = Column(Integer)
    style = Column(String)
    
    # Tag Attributes
    length = Column(Integer)
    samplerate = Column(Integer)
    channels = Column(Integer)
    extension = Column(String)
    bitrate = Column(Integer)

    title = Column(String)
    artist = Column(String)
    album = Column(String)
    
    art = Column(String)
    thumbnail = Column(String)
    
    events = relationship("Event")

    def __init__(self, uid, hash = None, size = None, style = None, length = None, samplerate = None, channels = None, extension = None, bitrate = None, title = None, artist = None, album = None, art = None, thumbnail = None):
        self.uid = uid
        self.time = datetime.datetime.now()
        
        self.hash = hash
        self.size = size
        self.style = style

        self.length = length
        self.samplerate = samplerate
        self.channels = channels
        self.extension = extension
        self.bitrate = bitrate

        self.title = title
        self.artist = artist
        self.album = album

        self.art = art
        self.thumbnail = thumbnail

class Event(Base):
    __tablename__ = 'events'
    id = Column(Integer, primary_key=True)
    uid = Column(CHAR(length=32) , ForeignKey('tracks.uid'))
    action = Column(String)
    start = Column(DateTime)
    end = Column(DateTime)
    success = Column(Boolean)
    ip = Column(String)
    detail = Column(Text)
    track = relationship("Track")

    def __init__(self, uid, action, success = None, ip = None, detail = None):
        self.uid = uid
        self.start = datetime.datetime.now()
        if success is not None:
            self.end = datetime.datetime.now()
        self.action = action
        self.success = success 
        self.ip = ip
        self.detail = detail

    def time(self):
        try:
            return self.end - self.start
        except:
            return datetime.timedelta(0)


###
# DB Connection Handling
###

engine = create_engine(
    config.database_connect_string,
    echo=config.echo_database_queries,
    poolclass=QueuePool,
    pool_recycle=10
)
Session = scoped_session(sessionmaker(engine))

########NEW FILE########
__FILENAME__ = cleanup
import config, os, database, traceback, time

class Cleanup():
    directories = ['tmp', 'uploads', 'static/songs']
    keep = ['thumb', 'empty']
    artdir = "static/songs"
    log = None
    db = None
    remixQueue = None

    def __init__(self, log, remixQueue):
        self.log = log
        self.remixQueue = remixQueue

    def all(self):
        for d in self.directories:
            if not os.path.exists(d):
                self.log.info("\t\Creating directory %s..." % d)
                os.mkdir(d)
            else:
                self.log.info("\t\tPurging directory %s..." % d)
                for f in os.listdir(d):
                    if not any([k in f for k in self.keep]):
                        p = os.path.join(d, f)
                        self.log.info("\t\t\tRemoving %s..." % p)
                        try:
                            os.remove(p)
                        except:
                            self.log.warning("Failed to remove %s:\n%s" % (p, traceback.format_exc()))
                            pass
        self.thumbnails()

    def active(self):
        self.log.info("Cleaning up...")
        for uid, remixer in self.remixQueue.finished.items():
            # If remix was last touched within cleanup_timeout seconds, leave it alone
            if 'time' in remixer and remixer['time'] > (time.time() - config.cleanup_timeout):
                continue
            self.log.info("\tClearing: %s" % uid)
            for d in self.directories:
                for f in os.listdir(d):
                    if uid in f and not any([k in f for k in self.keep]):
                        p = os.path.join(d, f)
                        self.log.info("\t\tRemoving %s..." % f)
                        os.remove(p)
            del self.remixQueue.finished[uid]
        self.thumbnails()

    def thumbnails(self):
        self.log.info("\tRemoving old thumbnails...")
        db = database.Session()
        try:
            thumbs = [os.path.basename(thumb) for (thumb,) in db.query(database.Track.thumbnail).order_by(database.Track.id.desc()).limit(config.monitor_limit).all() if thumb is not None]
            for f in os.listdir(self.artdir):
                if os.path.basename(f) not in thumbs:
                    p = os.path.join(self.artdir, f)
                    self.log.info("\t\tRemoving %s..." % p)
                    os.remove(p)
        except:
            self.log.error("DB read exception:\n%s" % traceback.format_exc())

########NEW FILE########
__FILENAME__ = daemon
import os, subprocess, sys, config

class Daemon():
    """
        Dirty little class to daemonize a script.
        Uses Linux/Unix/OS X commands to do its dirty work.
        Works for daemonizing a Tornado server, while other
        pythonic ways of daemonizing a process fail.
    """
    def __init__(self, pidfile=None):
        self.pidfile = "%s.pid" % sys.argv[0] if not pidfile else pidfile
        self.file = os.path.abspath(sys.argv[0])
        self.handleDaemon()

    def start(self):
        if os.path.exists('wubmachine.pid'):
            print '%s is already running!' % config.app_name
            exit(1)
        print ("Starting %s..." % config.app_name),
        devnull = open(os.devnull, 'w')
        pid = subprocess.Popen(
              ['nohup', 'python', self.file], 
              stdin=devnull,
              stdout=devnull,
              stderr=devnull 
            ).pid
        print "done. (PID: %s)" % pid
        open(self.pidfile, 'w').write(str(pid))

    def stop(self):
        if not os.path.exists(self.pidfile):
            print '%s is not running!' % config.app_name
        else:
            print ("Stopping %s..." % config.app_name),
            subprocess.Popen(['kill', '-2', open(self.pidfile).read()])
            print "done."
            if os.path.exists(self.pidfile):
                os.remove(self.pidfile)

    def handleDaemon(self):
        # The main process should be stopped only with a SIGINT for graceful cleanup.
        # i.e.: kill -2 `wubmachine.pid` if you really need to do it manually.

        if len(sys.argv) == 2:
            if sys.argv[1] == "start":    #   fast and cheap
                self.start()
                exit(0)
            elif sys.argv[1] == "stop":
                self.stop()
                exit(0)
            elif sys.argv[1] == 'restart':
                self.stop()
                self.start()
                exit(0)

########NEW FILE########
__FILENAME__ = fastmodify
"""
fastmodify.py

Provides similar functionality to echonest.Modify, but faster and lighter.
Requires soundstretch command-line binary to be installed.

Based on code by Ben Lacker on 2009-06-12.
Modified by Peter Sobot for speed on 2011-08-12
"""
from echonest.audio import *
import uuid, os

class FastModify():
    def processAudio( self, ad, arg, tempdir="tmp/" ):
        if not os.access( tempdir, os.W_OK ):
            tempdir = './'
        u = str( uuid.uuid1() )
        ad.encode( '%s%s.wav' % ( tempdir, u ) )
        process = subprocess.Popen(   ['soundstretch', '%s%s.wav' % ( tempdir, u ), '%s%s.out.wav' % ( tempdir, u ), arg],
                            stdin=None,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE
                        )
        process.wait()
        os.unlink( '%s%s.wav' % ( tempdir, u ) )
        ad = AudioData( '%s%s.out.wav' % ( tempdir, u ), verbose=False )
        os.unlink( '%s%s.out.wav' % ( tempdir, u ) )
        return ad

    def shiftTempo(self, audio_data, ratio):
        if not isinstance(audio_data, AudioData):
            raise TypeError('First argument must be an AudioData object.')
        if not (isinstance(ratio, int) or isinstance(ratio, float)):
            raise ValueError('Ratio must be an int or float.')
        if (ratio < 0) or (ratio > 10):
            raise ValueError('Ratio must be between 0 and 10.')
        return self.processAudio(audio_data, '-tempo=%s' % float((ratio-1)*100))


########NEW FILE########
__FILENAME__ = remixqueue
import config, os, time, database, traceback, logging
from helpers.web import ordinal
from datetime import datetime, timedelta

class RemixQueue():
    def __init__(self, monitor):
        self.log = logging.getLogger()
        self.monitor_callback = monitor.update

        self.remixers = {}
        self.finished = {}
        self.cleanups = {}

        self.watching = {}

        self.queue    = []
        self.running  = []

    def add(self, uid, ext, remixer, _user_callback, done_callback):
        self.log.debug("Adding remixer %s to queue..." % uid)
        if uid in self.remixers:
            raise Exception("Song already receieved!")

        infile = os.path.join("uploads/", "%s%s" % (uid, ext))
        outfile = os.path.join("static/songs/", "%s.mp3" % uid)

        user_callback = lambda data: _user_callback(uid, data)
        self.remixers[uid] = remixer(self, str(infile), str(outfile), [self.monitor_callback, user_callback])
        self.watching[uid] = user_callback
        self.cleanups[uid] = done_callback
        self.queue.append(uid)

    def updateTrack(self, uid, tag):
        # This may be called from another thread: let's use a unique DB connection.
        self.log.info("Updating track %s..." % uid)
        db = database.Session()
        try:
            track = db.query(database.Track).filter_by(uid = uid).first()
            keep = ['length', 'samplerate', 'channels', 'bitrate', 'title', 'artist', 'album', 'art', 'thumbnail']
            for a in tag:
                if a in keep:
                    try:
                        track.__setattr__(a, tag[a])
                    except:
                        pass
            db.commit()
            self.log.info("Track %s updated!" % uid)
        except:
            self.log.error("DB error when updating %s, rolling back:\n%s" % (uid, traceback.format_exc()))
            db.rollback()
            
    def finish(self, uid, final=None):
        self.log.debug("Finishing remixer %s from queue..." % uid)
        try:
            if not uid in self.remixers:
                return False
            if self.remixers[uid].isAlive():
                self.stop(uid)
            del self.remixers[uid]
            if not final:
                final = { 'status': -1, 'text': "Sorry, this remix is taking too long. Try again later!", 'progress': 0, 'uid': uid, 'time': time.time() }
            self.running.remove(uid)
            self.finished[uid] = final
            if self.cleanups[uid]:
                self.cleanups[uid](final)
                del self.cleanups[uid]
            
            # DB stuff
            db = database.Session()
            try:
                event = db.query(database.Event).filter_by(action='remix', uid=uid).first()
                event.end = datetime.now()
                if final['status'] is -1:
                    event.success = False
                    event.detail = final.get('debug')
                else:
                    event.success = True
                db.commit()
            except:
                db.rollback()
                self.log.error("DB error when finishing %s from queue:\n%s" % (uid, traceback.format_exc()))
            self.notifyWatchers()
            self.monitor_callback(uid)
            self.log.debug("Remixer %s finished! Calling next()..." % uid)
            self.next()
        except:
            self.log.error("Could not finish %s from queue:\n %s" % (uid, traceback.format_exc()))           

    def remove(self, uid):
        try:
            if uid in self.remixers:
                if self.remixers[uid].isAlive():
                    self.stop(uid)
                del self.remixers[uid]
                final = { 'status': -1, 'text': "Sorry, this remix is taking too long. Try again later!", 'progress': 0, 'uid': uid, 'time': time.time() }
                if uid in self.watching:
                    try:
                        self.watching(final)
                    except:
                        pass
                self.finished[uid] = final
                if self.cleanups[uid]:
                    self.cleanups[uid](None)
                    del self.cleanups[uid]
                # DB stuff
                db = database.Session()
                try:
                    event = db.query(database.Event).filter_by(action='remix', uid=uid).first()
                    if event:
                        event.end = datetime.now()
                        event.success = False
                        event.detail = "Timed out"
                    db.commit()
                except:
                    self.log.error("DB exception, rolling back:\n%s" % traceback.format_exc())
                    db.rollback()
                self.notifyWatchers()
                self.monitor_callback(uid)
            if uid in self.queue:
                self.queue.remove(uid)
            if uid in self.running:
                self.running.remove(uid)
            self.log.info("Removed %s from queue." % uid)
        except:
            self.log.error("Could not remove %s from queue:\n %s" % (uid, traceback.format_exc()))

    def start(self, uid):
        if not uid in self.queue:
            raise Exception("Cannot start, remixer not waiting: %s" % uid)
        if not self.remixers[uid].being_watched:
            raise Exception("Cannot start, nobody watching remixer: %s" % uid)
        self.running.append(uid)
        self.queue.remove(uid)
        del self.watching[uid]
        self.remixers[uid].start()

        db = database.Session()
        try:
            db.add(database.Event(uid, "remix"))
            db.commit()
        except:
            self.log.error("DB exception, rolling back:\n%s" % traceback.format_exc())
            db.rollback()
        self.monitor_callback(uid)
      

    def stop(self, uid):
        if uid in self.remixers and self.remixers[uid].isAlive():
            self.log.info("Stopping thread %s..." % uid)
            self.remixers[uid].stop()

    def notifyWatchers(self):
        for uid, callback in self.watching.iteritems():
            callback(self.waitingResponse(uid))

    def waitingResponse(self, uid):
        if uid in self.queue:
            position = self.queue.index(uid)
            if position is 0 and not len(self.running):
                text = "Starting..."
            elif position is 0 or position is 1:
                text = "Waiting... (next in line)"
            else:
                text = "Waiting in line... (%s)" % ordinal(position)
        else:
            text = "Starting..."
        return { 'status': 0, 'text': text, 'progress': 0, 'uid': uid, 'time': time.time() }

    def next(self):
        for uid in self.queue:
            if uid in self.watching:
                try:
                    self.start(uid)
                    self.log.info("Started remixer %s..." % uid)
                    break
                except:
                    pass
        else:
            self.log.info("No remixers in queue!")

    def cleanup(self):
        try:
            for uid, remixer in self.remixers.items():
                if config.watch_timeout and not remixer.started and not remixer.being_watched and remixer.added < (time.time() - config.watch_timeout):
                    self.log.info("Remixer %s is not being watched and has been waiting for more than %s seconds. Removing..." % (uid, config.watch_timeout)) 
                    self.remove(uid)
                elif config.wait_timeout and not remixer.started and remixer.added < (time.time() - config.wait_timeout):
                    self.log.info("Remixer %s has been waiting for more than %s minutes. Removing..." % (uid, config.wait_timeout/60)) 
                    self.remove(uid)
                elif config.remix_timeout and remixer.added < (time.time() - config.remix_timeout):
                    self.log.info("Remixer %s was added more than %s minutes ago. Removing..." % (uid, config.remix_timeout/60)) 
                    self.remove(uid)
                elif uid in self.running and not self.remixers[uid].isAlive():
                    self.log.info("Remixer %s is no longer alive. Removing..." % uid) 
                    self.remove(uid)
        except:
            self.log.error("RemixQueue cleanup went wrong:\n%s" % traceback.format_exc())

    def isAvailable(self):
        # Whatever condition this returns should result in next() being called once it no longer holds.
        # E.g.: If this returns False due to 25 remixers working, then at the end, next() should be called so the waiting remixer can start.
        return len(self.running) < config.maximum_concurrent_remixes

    def isAccepting(self):
        return len(self.queue) < config.maximum_waiting_remixes and self.countInHour() < config.hourly_remix_limit

    def countInHour(self):
        try:
            return len([v for k, v in self.finished.iteritems() if 'time' in v and v['time'] > time.time() - 3600])
        except:
            self.log.error("RemixQueue countInHour went wrong:\n%s\n%s" % (self.finished, traceback.format_exc()))
            return 0

    def errorRate(self):
        try:
            return len([r for r in self.finished if r.status == -1]) / len(r.finished)
        except:
            return 0

    def errorRateExceeded(self):
        return self.errorRate() > 0.5


########NEW FILE########
__FILENAME__ = soundcloud
import config, tornado.httpclient, json, time, logging, traceback
from random import choice

class SoundCloud():
    tracks =            []
    trackage =          None
    log = None

    supermassive = {
        'title' :         "Supermassive Black Hole (Wub Machine Remix)",
        'uri' :           "http://api.soundcloud.com/tracks/17047599",
        'permalink_url' : "http://soundcloud.com/plamere/supermassive-black-hole-wub",
        'artwork_url' :   "http://i1.sndcdn.com/artworks-000008186991-lnrin1-large.jpg?dd4912a",
        'created_with' :  {"id": config.soundcloud_app_id}
    }
    def __init__(self, log):
        self.log = log
        self.ht = tornado.httpclient.AsyncHTTPClient()
        self.fetchTracks()
    
    def fetchTracks(self):
        self.log.info("\tFetching SoundCloud tracks...")
        self.ht.fetch('https://api.soundcloud.com/tracks.json?client_id=%s&tags=wubmachine&order=created_at&limit=30&license=no-rights-reserved&filter=downloadable' % config.soundcloud_consumer, self._fetchTracks)

    def _fetchTracks(self, response):
        try:
            if not response.error:
                tracks = json.loads(response.body)
                self.tracks = [e for e in tracks if self.valid(e)]
                self.trackage = time.gmtime()
                self.log.info("SoundCloud tracks received!")
            else:
                self.log.error("SoundCloud fetch resulted in error: %s" % response.error)
        except:
            self.log.error("SoundCloud track update failed completely with an exception:\n%s" % traceback.format_exc())

    def frontPageTrack(self):
        if choice(xrange(0, 4)) % 4 and self.tracks:
            track = choice(self.tracks)
        else:
            track = self.supermassive
        return track

    def valid(self, track):
        return (track['created_with']['id'] == config.soundcloud_app_id) and (track['title'] != "[untitled] (Wub Machine Remix)") and (len(track['title']) > 20) and (len(track['title']) < 60)


########NEW FILE########
__FILENAME__ = web
import os, mimetools, itertools, mimetypes

class Daemonize():
    # Default daemon parameters.
    # File mode creation mask of the daemon.
    UMASK = 0
    # Default working directory for the daemon.
    WORKDIR = os.getcwd()
    # Default maximum for the number of available file descriptors.
    MAXFD = 1024
    # The standard I/O file descriptors are redirected to /dev/null by default.
    def __init__( self ):
        """Detach a process from the controlling terminal and run it in the
        background as a daemon.
        """
        if ( hasattr( os, "devnull" ) ):
           REDIRECT_TO = os.devnull
        else:
           REDIRECT_TO = "/dev/null"
        try:
            pid = os.fork()
        except OSError, e:
            raise Exception, "%s [%d]" % ( e.strerror, e.errno )

        if (pid == 0):	# The first child.
            os.setsid()
            try:
                pid = os.fork()	# Fork a second child.
            except OSError, e:
                raise Exception, "%s [%d]" % ( e.strerror, e.errno )

            if (pid == 0):	# The second child.
                os.chdir( self.WORKDIR )
                #os.umask( self.UMASK )
            else:
                os._exit( 0)
        else:
            os._exit( 0 )	# Exit parent of the first child.
        import resource		# Resource usage information.
        maxfd = resource.getrlimit( resource.RLIMIT_NOFILE )[1]
        if ( maxfd == resource.RLIM_INFINITY ):
            maxfd = self.MAXFD

        # Iterate through and close all file descriptors.
        for fd in xrange( 0, maxfd ):
            try:
                os.close(fd)
            except OSError:	# ERROR, fd wasn't open to begin with (ignored)
                pass
        os.open( REDIRECT_TO, os.O_RDWR )	# standard input (0)

        # Duplicate standard input to standard output and standard error.
        os.dup2(0, 1)			# standard output (1)
        os.dup2(0, 2)			# standard error (2)

class MultiPartForm(object):
    """Accumulate the data to be used when posting a form."""

    def __init__(self):
        self.form_fields = []
        self.files = []
        self.boundary = mimetools.choose_boundary()
        return

    def get_content_type(self):
        return 'multipart/form-data; boundary=%s' % self.boundary

    def add_field(self, name, value):
        """Add a simple field to the form data."""
        self.form_fields.append((name, value))
        return

    def add_file(self, fieldname, filename, fileHandle, mimetype=None):
        """Add a file to be uploaded."""
        body = fileHandle.read()
        if mimetype is None:
            mimetype = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
        self.files.append((fieldname, filename, mimetype, body))
        return

    def __str__(self):
        """Return a string representing the form data, including attached files."""
        # Build a list of lists, each containing "lines" of the
        # request.  Each part is separated by a boundary string.
        # Once the list is built, return a string where each
        # line is separated by '\r\n'.  
        parts = []
        part_boundary = '--' + self.boundary

        # Add the form fields
        parts.extend(
            [ part_boundary,
              'Content-Disposition: form-data; name="%s"' % str( name ),
              '',
              str( value ),
            ]
            for name, value in self.form_fields
            )

        # Add the files to upload
        parts.extend(
            [ part_boundary,
              'Content-Disposition: file; name="%s"; filename="%s"' % \
                 ( str( field_name ), str( filename ) ),
              'Content-Type: %s' % str( content_type ),
              '',
              str( body ),
            ]
            for field_name, filename, content_type, body in self.files
            )

        # Flatten the list and add closing boundary marker,
        # then return CR+LF separated data
        flattened = list(itertools.chain(*parts))
        flattened.append('--' + self.boundary + '--')
        flattened.append('')
        return '\r\n'.join(flattened)

def time_ago_in_words( time = None ):
    """
    Get a datetime object or a int() Epoch timestamp and return a
    pretty string like 'an hour ago', 'Yesterday', '3 months ago',
    'just now', etc
    """
    from datetime import datetime, timedelta
    now = datetime.now()
    if type( time ) is int:
        diff = now - datetime.fromtimestamp( time )
    elif isinstance( time, datetime ):
        diff = now - time 
    elif isinstance( time, timedelta ):
        diff = now - timedelta
    elif not time:
        diff = now - now
    second_diff = diff.seconds
    day_diff = diff.days

    if day_diff < 0:
        return ''

    if day_diff == 0:
        if second_diff < 10:
            return "just now"
        if second_diff < 60:
            return str(second_diff) + " seconds ago"
        if second_diff < 120:
            return  "a minute ago"
        if second_diff < 3600:
            return str( second_diff / 60 ) + " minutes ago"
        if second_diff < 7200:
            return "an hour ago"
        if second_diff < 86400:
            return str( second_diff / 3600 ) + " hours ago"
    if day_diff == 1:
        return "yesterday"
    if day_diff < 7:
        return str(day_diff) + " days ago"
    if day_diff < 31:
        return str(day_diff/7) + " weeks ago"
    if day_diff < 365:
        return str(day_diff/30) + " months ago"
    return str(day_diff/365) + " years ago"

def time_in_words( time = None ):
    """
    Get a datetime object or a int() Epoch timestamp and return a
    pretty string like 'an hour ago', 'Yesterday', '3 months ago',
    'just now', etc
    """
    if time < 10:
        return "just now"
    if time < 60:
        return str(time) + " seconds"
    if time < 120:
        return  "a minute"
    if time < 3600:
        return str( time / 60 ) + " minutes"
    if time < 7200:
        return "an hour"
    if time < 86400:
        return str( time / 3600 ) + " hours"

def seconds_to_time( time ):
    """
    Get a datetime object or a int() Epoch timestamp and return a
    pretty string like 'an hour ago', 'Yesterday', '3 months ago',
    'just now', etc
    """
    if not time:
        return "0s"
    from datetime import datetime, timedelta
    if isinstance( time, timedelta ) or isinstance( time, datetime ):
        if time.days < 0:
            diff = timedelta( )
        else:
            diff = time
    else:
        diff = timedelta( seconds = int(time if time >= 0 else 0) )

    second_diff = diff.seconds
    if second_diff < 0:
        second_diff = 0

    if second_diff > 60:
        return "%sm%ss" % ( str( second_diff / 60 ), ( second_diff % 60 ) )
    else:
        return "%ss" % second_diff

def convert_bytes(bytes):
    try:
        bytes = float(bytes)
        if bytes >= 1099511627776:
            terabytes = bytes / 1099511627776
            size = '%.2fTb' % terabytes
        elif bytes >= 1073741824:
            gigabytes = bytes / 1073741824
            size = '%.2fGb' % gigabytes
        elif bytes >= 1048576:
            megabytes = bytes / 1048576
            size = '%.2fMb' % megabytes
        elif bytes >= 1024:
            kilobytes = bytes / 1024
            size = '%.2fKb' % kilobytes
        else:
            size = '%.2fb' % bytes
        return size
    except:
        return "? Kb"

def list_in_words( l ):
    return "%s and %s" % (', '.join(l[:-1]), l[-1])

def ordinal(number):
    suffixes = { 0:'th', 1:'st', 2:'nd', 3:'rd' }
    numstring = str(number)
    if numstring[-2:len(numstring)] in ('11','12') or number % 10 > 3:
        return numstring + 'th'
    else:
        return numstring + suffixes[number % 10]

########NEW FILE########
__FILENAME__ = remixer
#!/usr/bin/env python
"""
remixer.py

Provides a basic remix superclass to build music remixers into bigger apps. (i.e.: web apps)
The heart of the Wub Machine (wubmachine.com) and hopefully more to come.

by Peter Sobot <hi@petersobot.com>
    v1: started Jan. 2011
    v2: August-Sept 2011
"""
from numpy import array
from os import rename, unlink, path, access, W_OK
from threading import Thread
from multiprocessing import Queue, Process
from traceback import print_exception, format_exc
from subprocess import check_call, call
from mutagen import File, id3
from PIL import Image
from echonest.selection import *
from echonest.sorting import *
import echonest.audio as audio
import time, sys, wave, mimetypes, config, logging, traceback

class Remixer(Thread):
    """
        Generic song remixer to be inherited from and
        embedded in something bigger - i.e. a web app.
        (like the Wub Machine...)

        Inherits from Thread to allow for asynchronous processing.

        Workhorse function (run()) spawns a child process for the remixer,
        then blocks for progress updates and calls callback functions when they occur.
        Progress updates are kept in a queue and callbacks fired immediately if the
        queue is not empty. Otherwise, the callback is fired when the progress update comes in.

        Child process is used for memory efficiency and to leverage multiple cores better.
        Spawn 4 remixers on a quad-core machine, and remix 4 tracks at once!

        Includes convenience methods for all remixers to use, as well as metadata functions
        and a memory-light alternative to AudioQuantumList: partialEncode().
    """
    def __init__(self, parent, infile, outfile=None, callbacks=None):
        """
            Takes in parent (whatever class spawns the remixer), in/out filenames,
            and a UID to identify the remix by.
            Logger should be a non-blocking function that needs to know *all* progress updates.
        """
        #   Thread variables
        if isinstance(callbacks, list):
            self.callbacks =   callbacks
        else:
            self.callbacks =   [callbacks]
        self.being_watched = False #  If nobody is watching, this remix can/should be killed.
        self.parent =    parent
        self.uid =       path.splitext(path.basename(infile))[0]
        self.extension = path.splitext(infile)[-1]
        self.timeout =   600     #   seconds
        self.queue =     None    #   queue between thread and process
        self.errortext = "Sorry, that song didn't work. Try another!"
        self.started =   None
        self.status =    0
        self.added =     time.time()

        #   Remixer variables
        self.keys =      {0: "C", 1: "C#", 2: "D", 3: "Eb", 4: "E", 5:"F", 6:"F#", 7:"G", 8:"G#", 9:"A", 10:"Bb", 11:"B"}
        self.infile  =   str(infile)
        if access('tmp/', W_OK):
            self.tempdir =   'tmp/'
        else:
            self.tempdir =   './'
        self.tempfile =  path.join(self.tempdir, "%s.wav" % self.uid)
        self.outdir =    'static/songs/'
        self.overlay =   'static/img/overlay.png' # Transparent overlay to put on top of song artwork
        self.outfile =   outfile or path.join(path.dirname(self.infile), "%s.out.mp3" % self.uid)
        self.artmime = None
        self.artpath = None
        self.artprocessed = False
        self.progress =  0.0
        self.step =      None
        self.encoded =   0
        self.deleteOriginal = True

        self.sample_path = 'samples/%s/' % str(self.__class__.__name__).lower()
        
        self.tag =       {}      #   Remix metadata tag
        self.original =  None    #   audio.LocalAudioFile-returned analysis
        self.tonic =     None
        self.tempo =     None
        self.bars =      None
        self.beats =     None
        self.sections =  None

        Thread.__init__(self)


    """
        All of the following progress methods should be of the form:
        {
            'status':
                -1 is error
                0 is waiting
                1 is OK
            'uid':
                uid of the track
            'time':
                current timestamp (not yet used)
            'text':
                progress text or user string to display for errors
            'progress':
                0-1 measure of progress, 1 being finished, 0 being not started
            'tag':
                Song-specific tag including all of its metadata
            ['debug']:
                Optional debug info if error.
        }
    """
    def logbase(self):
        return { 'status': self.status, 'text': self.step, 'progress': self.progress, 'tag': self.tag, 'uid': self.uid, 'time': time.time() }

    def log(self, text, progress):
        """
            Pass progress updates back to the run() function, which then bubbles up to everybody watching this remix.
            Automatically increments progress, which can be a fractional percentage or decimal percentage.
        """
        if progress > 1:
            progress *= 0.01
        self.progress += progress
        self.step = text

        self.processqueue.put(self.logbase())

    def handleError(self, e):
        self.step = "Hmm... something went wrong. Please try again later!"
        progress = self.logbase()
        progress['debug'] = unicode(e)
        self.last = progress

    def error(self, text):
        """
            In case of emergency, break glass.
            In case of remixer error, log an error and close the queue.
        """
        self.step = text
        self.status = -1

        update = self.logbase()
        update['text'] = self.errortext
        update['debug'] = text

        self.processqueue.put(update)
        self.close()

    def finish(self, text):
        """
            When the remixing's all done, log it and close the queue.
        """
        self.progress = 1
        self.step = text
        self.processqueue.put(self.logbase())
        self.close()

    def close(self):
        """
            When it's all over, the run() function needs to know when to go home.
        """
        self.processqueue.put(False)

    def stop(self):
        """
            Set status flag to error, which stops the remixing, terminates the child process and returns.
        """
        print "Trying to stop remixer %s" % self.uid
        self.status = -1

    def attach(self, callback): 
        """
            Attaches a given callback to the remix, to be called on the next progress update.
            Intended to send asynchronous updates to a user who's remixing a song. (i.e.: via HTTP)
        """
        if callback not in self.callbacks:
            self.callbacks.append(callback)

    def cleanup(self):
        """
            Remove all temporary files, and clear unused memory.
            Remixin's a messy business.
        """
        if path.isfile(self.tempfile):
            unlink(self.tempfile)
        if self.deleteOriginal and path.isfile(self.infile):
            unlink(self.infile)

        i = 0
        f = "%s%s%s.wav" % (self.tempdir, self.uid, i)
        while path.isfile(f):
            unlink(f)
            i += 1
            f = "%s%s%s.wav" % (self.tempdir, self.uid, i)
        if self.original:
            self.original.unload()

    def run(self):
        """
            Spawns a child process to do the actual remixing.
            Blocks until a progress update comes from the child process.
            When a progress update comes through:
                if someone is watching (i.e.: there's a callback) then fire the callback
                if not, put the progress update into a queue
                if somebody is *monitoring* and doesn't care about missing an update,
                  fire the monitors callback. (Useful for watching an entire server of remixers.)
            The "loggers" callback gets fired on each update, no matter what.

            After remixing is complete and the communication queue is closed,
            the subprocess is joined, deleted, and the parent's "finish" method
            is called if it exists.
        """
        self.started = time.time()
        self.status = 1
        self.processqueue = Queue()
        self.p = Process(target=self._remix)                    #   Actual remix process started with Multiprocessing
        self.p.start()

        self.last = None
        try:
            progress = self.processqueue.get(True, self.timeout)          #   Queue that blocks until progress updates happen
            while progress and self.status is not -1:                       #   MUST END WITH False value, or else this will block forever
                self.last = progress
                for callback in self.callbacks:                             #   Send all progress updates
                    callback(progress)
                progress = self.processqueue.get(True, self.timeout)      #   Grab another progress update from the process
        except Exception, e:
            self.status = -1
            self.handleError(e)
        else:
            if self.status is -1:
                try:
                  self.handleError(Exception("RemixTermination. Last was:\n%s" % last))
                except:
                    self.handleError(Exception("RemixTermination"))
        self.processqueue.close()
        self.p.terminate()
        self.cleanup()
        del self.p
        if hasattr(self.parent, 'finish'):
            self.parent.finish(self.uid, self.last)

    def _remix(self):
        """
          Failure-tolerant wrapper around main remix method that allows for cleanup and such.
        """
        try:
            self.tag['style'] = str(self.__class__.__name__)
            self.tag['remixed'] = self.remix()
            self.finish("Done!")
        except:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            print_exception(exc_type, exc_value, exc_traceback,limit=4, file=sys.stderr)
            fname = path.split(exc_traceback.tb_frame.f_code.co_filename)[1]
            lines = format_exc().splitlines()
            self.error("%s @ %s:%s\n\n%s" % (exc_value, fname, exc_traceback.tb_lineno, '\n'.join(lines)))
        finally:
            self.cleanup()

    """
    Audio methods for encoding, partial encoding, custom mixing, 
    """
    def lame(self, infile, outfile):
        """
            Use the installed (hopefully latest) build of
            LAME to get a really, really high quality MP3.
        """
        r = check_call(['lame', '-S', '--preset', 'fast', 'medium', str(infile), str(outfile)])
        return r

    def mono_to_stereo(self, audio_data):
        """
            Take in an AudioData with two channels,
            return one with one. This here's a theivin' method.
        """
        data = audio_data.data.flatten().tolist()
        new_data = array((data,data))
        audio_data.data = new_data.swapaxes(0,1)
        audio_data.numChannels = 2
        return audio_data

    def truncatemix(self, dataA, dataB, mix=0.5):
        """
        Mixes two "AudioData" objects. Assumes they have the same sample rate
        and number of channels.
        
        Mix takes a float 0-1 and determines the relative mix of two audios.
        i.e., mix=0.9 yields greater presence of dataA in the final mix.

        If dataB is longer than dataA, dataB is truncated to dataA's length.
        """
        newdata = audio.AudioData(ndarray=dataA.data, sampleRate=dataA.sampleRate,
            numChannels=dataA.numChannels, defer=False, verbose=False)
        newdata.data *= float(mix)
        if dataB.endindex > dataA.endindex:
            newdata.data[:] += dataB.data[:dataA.endindex] * (1 - float(mix))
        else:
            newdata.data[:dataB.endindex] += dataB.data[:] * (1 - float(mix))
        return newdata

    def partialEncode(self, audiodata):
        """
            A neat alternative to AudioQuantumList.
            Instead of making a list, holding it in memory and encoding it all at once,
            each element in the list is encoded upon addition.

            After many partialEncode()s, the mixwav() function should be called,
            which calls shntool on the command line for super-fast audio concatenation.
        """
        audiodata.encode("%s%s%03d.wav" % (self.tempdir, self.uid, self.encoded))
        audiodata.verbose = False
        audiodata.unload()
        self.encoded += 1

    def mixwav(self, filename):
        """
            When used after partialEncode(), this concatenates a number of audio
            files into one with a given filename. (Super fast, super memory-efficient.)
            
            Requires the shntool binary to be installed.
        """
        if self.encoded is 1:
            rename("%s%s%03d.wav" % (self.tempdir, self.uid, 0), filename)
            return
        args = ['shntool', 'join', '-z', self.uid, '-q', '-d', self.tempdir]
        for i in xrange(0, self.encoded):
            args.append("%s%s%03d.wav" % (self.tempdir, self.uid, i))
        call(args)
        rename("%sjoined%s.wav" % (self.tempdir, self.uid), filename)
        for i in xrange(0, self.encoded):
            unlink("%s%s%03d.wav" % (self.tempdir, self.uid, i))

    """
    Metadata methods for tagging
    """
    def getTag(self):
        """
            Tries to get the metadata tag from the input file.
            May not work. Only set up to do mp3, m4a and wav.
            Returns its success value as a boolean.
        """
        try:
            self.mt = File(self.infile)
            tag = {}

            # technical track metadata
            if hasattr(self.mt, 'info'):
                tag['bitrate'] = self.mt.info.bitrate if hasattr(self.mt.info, 'bitrate') else None
                tag['length'] = self.mt.info.length if hasattr(self.mt.info, 'length') else None
                tag['samplerate'] = self.mt.info.sample_rate if hasattr(self.mt.info, 'sample_rate') else None
                tag['channels'] = self.mt.info.channels if hasattr(self.mt.info, 'channels') else None
            elif self.extension == ".wav":
                wav = wave.open(self.infile)
                tag['samplerate'] = wav.getframerate()
                tag['channels'] = wav.getnchannels()
                tag['length'] = float(wav.getnframes()) / tag['samplerate']
                tag['bitrate'] = (wav._file.getsize() / tag['length']) / 0.125  # value in kilobits
                wav.close()
                del wav

            if self.mt:
                if self.extension == ".mp3":
                    if 'TIT2' in self.mt: tag["title"] = self.mt['TIT2'].text[0]
                    if 'TPE1' in self.mt: tag["artist"] = self.mt['TPE1'].text[0]
                    if 'TALB' in self.mt: tag["album"] = self.mt['TALB'].text[0]
                elif self.extension == ".m4a":
                    if '\xa9nam' in self.mt: tag["title"] = self.mt['\xa9nam'][0]
                    if '\xa9ART' in self.mt: tag["artist"] = self.mt['\xa9ART'][0]
                    if '\xa9alb' in self.mt: tag["album"] = self.mt['\xa9alb'][0]

            self.tag = dict(self.tag.items() + tag.items()) # Merge all new tags into tag object
            if hasattr(self.parent, 'updateTrack'):
                self.parent.updateTrack(self.uid, tag)
            return True
        except:
            return False

    def detectSong(self, analysis):
        """
            Uses an EchoNest analysis to try to detect the name and tag info of a song.
        """
        try:
            for k in ['title', 'artist', 'album']:
                if k in self.original.analysis.metadata and not k in self.tag:
                    self.tag[k] = self.original.analysis.metadata[k]
        except:
           pass


    def processArt(self):
        """
            Tries to parse artwork from the incoming file.
            Saves artwork in a configurable location, along with a thumbnail.
            Useful for web frontends and the like.
            If an overlay is provided, that overlay is pasted on top of the artwork.

            Returns success value as a boolean.
        """
        try:
            if not self.mt:
                return False
            imgmime = False
            imgdata = False
            if self.extension == ".mp3":
                if "APIC:" in self.mt:
                    imgmime = self.mt['APIC:'].mime
                    imgdata = self.mt['APIC:'].data
            elif self.extension == ".m4a":
                if "covr" in self.mt:
                    if self.mt['covr'][0][0:4] == '\x89PNG':
                        imgmime = u'image/png'
                    elif self.mt['covr'][0][0:10] == '\xff\xd8\xff\xe0\x00\x10JFIF':  # I think this is right...
                        imgmime = u'image/jpeg'
                    imgdata = self.mt['covr'][0]
            if imgmime and imgdata:
                self.artmime = imgmime
                ext = mimetypes.guess_extension(imgmime)
                if not ext:
                    raise Exception("Unknown artwork format!")
                artname = path.join(self.tempdir, "%s%s" % (self.uid, ext))
                self.artpath = path.join(self.outdir, "%s%s" % (self.uid, ext))
                self.thumbpath = path.join(self.outdir, "%s.thumb%s" % (self.uid, ext))

                artwork = open(artname, "w")
                artwork.write(imgdata)
                artwork.close()
                
                if self.overlay:
                    overlay = Image.open(self.overlay)
                    artwork = Image.open(artname).resize(overlay.size, Image.BICUBIC)
                    artwork.paste(overlay, None, overlay)

                artwork.save(self.artpath)
                artwork.resize((config.thumbnail_size,config.thumbnail_size), Image.ANTIALIAS).convert("RGB").save(self.thumbpath)

                unlink(artname)

                self.tag["art"] = self.artpath
                self.tag["thumbnail"] = self.thumbpath
                self.artprocessed = True
                if hasattr(self.parent, 'updateTrack'):
                    self.parent.updateTrack(self.uid, self.tag)
                return True
        except:
            logging.getLogger().warning("Artwork processing failed for %s:\n%s" % (self.uid, traceback.format_exc()))
            self.artprocessed = False
            return False

    def updateTags(self, titleSuffix=''):
        """
            Updates the MP3 tag.
            Can use a mutagen tag (mt) from an MP3 or an M4A.
        """
        try:
            self.tag['new_title'] = "%s%s" % (
              (self.tag['title']
                if ('title' in self.tag and self.tag['title'].strip() != '')
                else '[untitled]'),
              titleSuffix
            )

            if 'TIT2' in self.mt:
                self.mt['TIT2'].text[0] += titleSuffix
            elif '\xa9nam' in self.mt:
                self.mt['\xa9nam'][0] += titleSuffix

            outtag = File(self.outfile)  
            outtag.add_tags()
            outtag.tags.add(id3.TBPM(encoding=0, text=unicode(self.template['tempo'])))
            if self.extension == ".mp3":
                for k, v in self.mt.iteritems():
                    if k != 'APIC:':
                        outtag.tags.add(v)
            elif self.extension == ".m4a":
                tags = {
                    '\xa9alb': id3.TALB,
                    '\xa9ART': id3.TPE1,
                    '\xa9nam': id3.TIT2,
                    '\xa9gen': id3.TCON                    
                }
                for k, v in self.mt.iteritems():
                    if k in tags:
                        outtag.tags.add(tags[ k ](encoding=0, text=v[0]))
                if 'trkn' in self.mt:
                    if type(self.mt['trkn'][0] == tuple):
                        outtag.tags.add(id3.TRCK(encoding=0, text=("%s/%s" % (self.mt['trkn'][0][0], self.mt['trkn'][0][1]))))
                    else:
                        outtag.tags.add(id3.TRCK(encoding=0, text=(self.mt['trkn'][0])))
                if 'disk' in self.mt:
                    if type(self.mt['disk'][0] == tuple):
                        outtag.tags.add(id3.TPOS(encoding=0, text=("%s/%s" % (self.mt['disk'][0][0], self.mt['disk'][0][1]))))
                    else:
                        outtag.tags.add(id3.TPOS(encoding=0, text=(self.mt['disk'][0])))     

            if self.artprocessed:
                outtag.tags.add(
                    id3.APIC(
                        encoding=3, # 3 is for utf-8
                        mime=self.artmime, # image/jpeg or image/png
                        type=3, # 3 is for the cover image
                        desc=u'Cover',
                        data=open(self.artpath).read()
                    )
                )
            outtag.save()
        except:
            pass

    def loudness(self, segments, bar):
        """
            Given a list of segments (a.k.a: song.analysis.segments) and a bar,
            calculate the average loudness of the bar.
        """
        b = segments.that(overlap_range(bar[0].start, bar[len(bar)-1].end))
        maximums = [x.loudness_max for x in b]
        if len(maximums):   
            return float(sum(maximums) / len(maximums))
        else:
            return None


class CMDRemix():
    """
        Remix from the command line with this handy little class.
        Instantiate this class from any remixer, and this wraps around
        the remixer, pushes progress updates to the console, and allows
        command line based remixing. Very basic, but useful.

        Instantiate the class, but don't try to call any functions, i.e.:
            if __name__ == "__main__":
                CMDRemix(Dubstep)
        will handle all command line remixing for the "Dubstep" remixer.
    """
    def __init__(self, remixer):
        """
            Handles command line argument parsing and sets up a new remixer.
        """
        if len(sys.argv) < 2:
            print "Error: no file specified!"
            print "Usage: python -m remixers.%s <song.[mp3|m4a|wav|aif]>" % str(remixer.__name__.lower())
        elif not path.exists(sys.argv[1]):
            print "Error: song does not exist!"
        else:
            r = remixer(self, sys.argv[1], callbacks=self.log)
            r.deleteOriginal = False
            r.start()
            r.join()

    def log(self, s):
        """
            Prints progress updates to the console.
        """
        print "(%s%%) %s" % (round(s['progress']*100, 2), s['text']) 

if __name__ == "__main__":
    raise Exception("This class is a superclass of all remixers. Call the appropriate remixer instead.")

########NEW FILE########
__FILENAME__ = beatbox
"""
Dependencies:
    Remixer
    lame (command line binary)
"""

from remixer import *
from echonest.selection import *
from echonest.sorting import *
import math
import numpy

def avg(xArr):
    return round(float(sum(xArr)/len(xArr)),1)

def stddev(xArr):
    return "std"

def are_kicks(x):
    bright = x.timbre[1] < 20
    #flat =  x.timbre[2] < 0 
    attack = x.timbre[3] > 80
    return bright

def are_snares(x):
    loud = x.timbre[0] > 10
    bright = x.timbre[1] > 100 and x.timbre[1] < 150
    flat =  x.timbre[2] < 30
    attack = x.timbre[3] > 20
    return loud and bright and flat and attack

def are_hats(x):
    loud = x.timbre[0] < 45
    bright = x.timbre[1] > 90
    flat =  x.timbre[2] < 0
    attack = x.timbre[3] > 70
    what = x.timbre[4] < 40
    return loud and bright and flat and attack and what

class Beatbox(Remixer):
    template = {
      'hats': 'hat.wav',
      'kick': 'kick.wav',
      'snare': 'snare.wav'
        }

    def remix(self):
        """
            Remixing happens here. Take your input file from self.infile and write your remix to self.outfile.
            If necessary, self.tempfile can be used for temp files. 
        """
        self.original = audio.LocalAudioFile(self.infile)
        #for i, segment in enumerate(self.original.analysis.segments):
        #    segment.encode("seg_%s.mp3" % i)
        print "\n\n\n"
        loudnesses = [x.timbre[0] for i, x in enumerate(self.original.analysis.segments)]
        brightnesses = [x.timbre[1] for i, x in enumerate(self.original.analysis.segments)]
        flatnesses = [x.timbre[2] for i, x in enumerate(self.original.analysis.segments)]
        attacks = [x.timbre[3] for i, x in enumerate(self.original.analysis.segments)]
        timbre5 = [x.timbre[4] for i, x in enumerate(self.original.analysis.segments)]
        timbre6 = [x.timbre[5] for i, x in enumerate(self.original.analysis.segments)]
        timbre7 = [x.timbre[6] for i, x in enumerate(self.original.analysis.segments)]
        timbre8 = [x.timbre[7] for i, x in enumerate(self.original.analysis.segments)]
        timbre9 = [x.timbre[8] for i, x in enumerate(self.original.analysis.segments)]
        timbre10 = [x.timbre[9] for i, x in enumerate(self.original.analysis.segments)]
        timbre11 = [x.timbre[10] for i, x in enumerate(self.original.analysis.segments)]
        timbre12 = [x.timbre[11] for i, x in enumerate(self.original.analysis.segments)]

        print "AVERAGES"
        print "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s" % ('loud','bright','flat','attack','t5','t6','t7','t8','t9','t10','t11','t12')
        print "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s" % (avg(loudnesses),avg(brightnesses),avg(flatnesses),avg(attacks),avg(timbre5),avg(timbre6),avg(timbre7),avg(timbre8),avg(timbre9),avg(timbre10),avg(timbre11),avg(timbre12))
        print
        print "STDVS"
        print "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s" % ('loud','bright','flat','attack','t5','t6','t7','t8','t9','t10','t11','t12')
        print "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s" % (stddev(loudnesses),stddev(brightnesses),stddev(flatnesses),stddev(attacks),stddev(timbre5),stddev(timbre6),stddev(timbre7),stddev(timbre8),stddev(timbre9),stddev(timbre10),stddev(timbre11),stddev(timbre12))


        print "\tLoud\tBright\tFlat\tAttack\ttim5\ttim6\ttim7\ttim8\ttim9\ttim10\ttim11\ttim12"
        for segment in self.original.analysis.segments:
            if are_kicks(segment): print "Kick",
            elif are_snares(segment): print "Snar",
            elif are_hats(segment): print "Hats",
            else: print "else",
            print "\t%s\t%s\t%s\t%s\t%s" % (segment.timbre[0], segment.timbre[1], segment.timbre[2], segment.timbre[3], segment.timbre[4])

        kicks = self.original.analysis.segments.that(are_kicks)
        #if kicks: kicks.encode('kicks.mp3')
        snares = self.original.analysis.segments.that(are_snares)
        #if snares: snares.encode('snares.mp3')
        hats = self.original.analysis.segments.that(are_hats)
        #if hats: hats.encode('hats.mp3')

        # Time to replace
        hat_sample = audio.AudioData(self.sample_path + self.template['hats'], sampleRate=44100, numChannels=2, verbose=False)
        kick_sample = audio.AudioData(self.sample_path + self.template['kick'], sampleRate=44100, numChannels=2, verbose=False)
        snare_sample = audio.AudioData(self.sample_path + self.template['snare'], sampleRate=44100, numChannels=2, verbose=False)
  
        empty = audio.AudioData(ndarray=numpy.zeros(((self.original.sampleRate * self.original.analysis.duration), 2), dtype=numpy.int16), numChannels=2, sampleRate=44100)

        last = 0
        for segment in kicks:
            if last + len(kick_sample.data) > segment.start:
                print "Adding kick at %s" % segment.start
                empty.data[self.original.sampleRate*segment.start:self.original.sampleRate*segment.start + len(kick_sample.data)] += kick_sample.data
            last = segment.start

        last = 0
        for segment in snares:
            if last + len(snare_sample.data) > segment.start:
                print "Adding snare at %s" % segment.start
                empty.data[self.original.sampleRate*segment.start:self.original.sampleRate*segment.start + len(snare_sample.data)] += snare_sample.data     
            last = segment.start
        for segment in hats:
            if last + len(hat_sample.data) > segment.start:
                print "Adding hat at %s" % segment.start
                empty.data[self.original.sampleRate*segment.start:self.original.sampleRate*segment.start + len(hat_sample.data)] += hat_sample.data
            last  = segment.start

        audio.mix(empty, self.original, 0.5).encode('mixed.mp3')

if __name__ == "__main__":
    CMDRemix(Beatbox)


########NEW FILE########
__FILENAME__ = blank
"""
blank.py

Blank remix template.
Dependencies:
    Remixer
    lame (command line binary)
"""

from remixer import *

class Blank(Remixer):
    def remix(self):
        """
            Remixing happens here. Take your input file from self.infile and write your remix to self.outfile.
            If necessary, self.tempfile can be used for temp files. 
        """
        open(self.outfile, 'w').write(open(self.infile).read())

if __name__ == "__main__":
    CMDRemix(Blank)


########NEW FILE########
__FILENAME__ = doubletime
"""
doubletime.py

Double-speed remix template.
Dependencies:
    FastModify
    Remixer
    lame (command line binary)
    soundstretch (command line binary)
"""

from remixer import *
from fastmodify import FastModify

class DoubleTime(Remixer):
    speedFactor = 2
    def remix(self):
        """
            Remixing happens here. Take your input file from self.infile and write your remix to self.outfile.
            Be sure to .unload() all of your read-in audioData objects to conserve memory.
        """
        # Use the Echo Nest Remix API to open the audio file
        a = audio.AudioData(self.infile)

        # Tell somebody about our progress (add 25%)
        self.log("Shifting tempo...", 25)

        # Use FastModify (a fork of echonest.Modify that uses soundstretch) to stretch beats
        FastModify().shiftTempo(a, self.speedFactor).encode(self.tempfile)

        self.log("Cleaning up...", 25)

        # Remove temporary file auto-generated by the Echo Nest Remix API
        a.unload() 

        self.log("Encoding MP3...", 25)

        # Encode the temporary file into the output file
        self.lame(self.tempfile, self.outfile)

if __name__ == "__main__":
    CMDRemix(DoubleTime)



########NEW FILE########
__FILENAME__ = dubstep
"""
dubstep.py <ex: dubstepize.py, wubmachine.py, wubwub.py, etc...>

Turns a song into a dubstep remix.
Dubstep inherits from the Remixer class.
Dependencies:
    FastModify
    Remixer
    lame (command line binary)
    shntool (command line binary)
    soundstretch (command line binary)

by Peter Sobot <hi@petersobot.com>
    v1: started Jan. 2011
    v2: August 2011
based off of code by Ben Lacker, 2009-02-24.
"""

from remixer import Remixer, CMDRemix
from helpers.fastmodify import FastModify

from os import unlink
from echonest.selection import *
from echonest.sorting import *
import echonest.audio as audio

class Dubstep(Remixer):
    """
        The heart of the Wub Machine. The wubalizer, the dubstepper - or the Dubstep class, as it's now been refactored.
        Inherits from Remixer. Call the remix() method to start a remix. (This is forked and called by RemixQueue in the web interface.)
        Template defined in the self.template object: tempo and locations of audio samples.

        A couple custom modifications to the Remix API:
            FastModify is used instead of Modify, which requires the `soundstretch` binary to be installed.
            Remixer.partialEncode() and Remixer.mixwav() are used instead of an AudioQuantumList,
            to save memory and increase processing speed at the expense of disk space. (Requires `shntool` binary.)
            
    """
    template = {
        'tempo':        140,
        'intro':        'intro-eight.wav',
        'hats':         'hats.wav',
        'wubs':         [  'wubs/c.wav',
                            'wubs/c-sharp.wav',
                            'wubs/d.wav',
                            'wubs/d-sharp.wav',
                            'wubs/e.wav',
                            'wubs/f.wav',
                            'wubs/f-sharp.wav',
                            'wubs/g.wav',
                            'wubs/g-sharp.wav',
                            'wubs/a.wav',
                            'wubs/a-sharp.wav',
                            'wubs/b.wav'
                        ],
        'wub_breaks':   [  'break-ends/c.wav',
                            'break-ends/c-sharp.wav',
                            'break-ends/d.wav',
                            'break-ends/d-sharp.wav',
                            'break-ends/e.wav',
                            'break-ends/f.wav',
                            'break-ends/f-sharp.wav',
                            'break-ends/g.wav',
                            'break-ends/g-sharp.wav',
                            'break-ends/a.wav',
                            'break-ends/a-sharp.wav',
                            'break-ends/b.wav'
                        ],
        'splashes':     [  'splashes/splash_03.wav',
                            'splashes/splash_04.wav',
                            'splashes/splash_02.wav',
                            'splashes/splash_01.wav',
                            'splashes/splash_05.wav',
                            'splashes/splash_07.wav',
                            'splashes/splash_06.wav',
                            'splashes/splash_08.wav',
                            'splashes/splash_10.wav',
                            'splashes/splash_09.wav',
                            'splashes/splash_11.wav'
                        ],
        'splash_ends':  [  'splash-ends/1.wav',
                            'splash-ends/2.wav',
                            'splash-ends/3.wav',
                            'splash-ends/4.wav'
                        ],
        'mixpoint': 18,     # "db factor" of wubs - 0 is softest wubs, infinity is... probably extremely loud 
        'target': "beats"
    }
    st = None

    def searchSamples(self, j, key):
        """
            Find all samples (beats) of a given key in a given section.
        """
        a = self.getSamples(self.sections[j], key)
        for tries in xrange(0, 5):
            if len(a):
                break
            key = (key + 7) % 12
            a = self.getSamples(self.sections[j], key)
        else:
            for tries in xrange(0, 5):
                if len(a):
                    break
                j = (j + 1) % len(self.sections)
                key = (key + 2) % 12
                a = self.getSamples(self.sections[j], key)
        return a

    def getSamples(self, section, pitch, target="beats"):
        """
            The EchoNest-y workhorse. Finds all beats/bars in a given section, of a given pitch.
        """
        sample_list = audio.AudioQuantumList()
        if target == "beats":
            sample_list.extend([b for x in section.children() for b in x.children()]);
        elif target == "bars":
            sample_list.extend(section.children())
        return sample_list.that(overlap_ends_of(self.original.analysis.segments.that(have_pitch_max(pitch)).that(overlap_starts_of(sample_list))))

    def mixfactor(self, segment):
        """
            Computes a rough "mixfactor" - the balance between wubs and original audio for a given segment.
            Mixfactor returned:
              1: full wub
              0: full original
            Result can be fed into echonest.audio.mix() as the third parameter.
        """
        mixfactor = 0
        a = (89.0/1.5) + self.template['mixpoint']
        b = (188.0/1.5) + self.template['mixpoint']
        loud = self.loudness(self.original.analysis.segments, segment)
        if not loud:
            loud = self.original.analysis.loudness
        if loud != -1 * b:
            mixfactor = float(float(loud + a)/float(loud + b))
        if mixfactor > 0.8:
            mixfactor = 0.8
        elif mixfactor < 0.3:
            mixfactor = 0.3
        return mixfactor

    def compileIntro(self):
        """
            Compiles the dubstep introduction. Returns an AudioData of the first 8 bars.
            (8 bars at 140 bpm = ~13.71 seconds of audio)
            If song is not 4/4, tries to even things out by speeding it up by the appropriate amount.

            Pattern:
                first 4 bars of song
                first beat of 1st bar x 4   (quarter notes)
                first beat of 2nd bar x 4   (quarter notes)
                first beat of 3rd bar x 8   (eighth notes)
                first beat of 4th bar x 8   (sixteenth notes)
                third beat of 4th bar x 8   (sixteenth notes)
        """
        out = audio.AudioQuantumList()
        intro = audio.AudioData(self.sample_path + self.template['intro'], sampleRate=44100, numChannels=2, verbose=False)
        
        #   First 4 bars of song
        custom_bars = []

        if not self.beats or len(self.beats) < 16:
            #   Song is not long or identifiable enough
            #   Take our best shot at making something
            self.tempo = 60.0 * 16.0 / self.original.duration
            for i in xrange(0, 4):
                bar = []
                for j in xrange(0, 4):
                    length = self.original.duration / 16.0
                    start = ((i * 4) + j) * length
                    bar.append(audio.AudioQuantum(start, length, None, 0, self.original.source))
                custom_bars.append(bar)
        else:
            for i in xrange(0, 4):
                custom_bars.append(self.beats[i*4:(i*4)+4])
        out.extend([x for bar in custom_bars for x in bar])

        #   First beat of first bar x 4
        for i in xrange(0, 4):
            out.append(custom_bars[0][0])
        
        #   First beat of second bar x 4
        for i in xrange(0, 4):
            out.append(custom_bars[1][0])

        beatone = custom_bars[2][0]
        beattwo = custom_bars[3][0]
        beatthree = custom_bars[3][2]
        
        #   First beat of third bar x 8
        for x in xrange(0, 8):
            out.append(audio.AudioQuantum(beatone.start, beatone.duration/2, None, beatone.confidence, beatone.source))

        #   First beat of fourth bar x 8
        for x in xrange(0, 8):
            out.append(audio.AudioQuantum(beattwo.start, beattwo.duration/4, None, beattwo.confidence, beattwo.source))

        #   Third beat of fourth bar x 8
        for x in xrange(0, 8):
            out.append(audio.AudioQuantum(beatthree.start, beatthree.duration/4, None, beatthree.confidence, beatthree.source))
        
        if self.original.analysis.time_signature == 4:
            shifted = self.st.shiftTempo(audio.getpieces(self.original, out), self.template['tempo']/self.tempo)
        else:
            shifted1 = audio.getpieces(self.original, out)
            shifted = self.st.shiftTempo(shifted1, len(shifted1) / ((44100 * 16 * 2 * 60.0)/self.template['tempo']))
            shifted1.unload()
        if shifted.numChannels == 1:    
            shifted = self.mono_to_stereo(shifted)
        return self.truncatemix(intro, shifted, self.mixfactor(out))

    def compileSection(self, j, section, hats):
        """
            Compiles one "section" of dubstep - that is, one section (verse/chorus) of the original song,
            but appropriately remixed as dubstep.

            Chooses appropriate samples from the section of the original song in three keys (P1, m3, m7)
            then plays them back in order in the generic "dubstep" pattern (all 8th notes):

            |                         |                         :|
            |: 1  1  1  1  1  1  1  1 | m3 m3 m3 m3 m7 m7 m7 m7 :| x2
            |                         |                         :|

            On the first iteration, the dubstep bar is mixed with a "splash" sound - high-passed percussion or whatnot.
            On the second iteration, hats are mixed in on the offbeats and the wubs break on the last beat to let the
            original song's samples shine through for a second, before dropping back down in the next section.

            If samples are missing of one pitch, the searchSamples algorithm tries to find samples
            a fifth from that pitch that will sound good. (If none exist, it keeps trying, in fifths up the scale.)
            
            If the song is not 4/4, the resulting remix is sped up or slowed down by the appropriate amount.
            (That can get really wonky, but sounds cool sometimes, and fixes a handful of edge cases.)
        """
        onebar = audio.AudioQuantumList()

        s1 = self.searchSamples(j, self.tonic)
        s2 = self.searchSamples(j, (self.tonic + 3) % 12)
        s3 = self.searchSamples(j, (self.tonic + 9) % 12)

        biggest = max([s1, s2, s3]) #for music that's barely tonal
        if not biggest:
            for i in xrange(0, 12):
                biggest = self.searchSamples(j, self.tonic + i)
                if biggest:
                    break

        if not biggest:
            raise Exception('Missing samples in section %s of the song!' % j+1)

        if not s1: s1 = biggest
        if not s2: s2 = biggest
        if not s3: s3 = biggest

        if self.template['target'] == "tatums":
            f = 4
            r = 2
        elif self.template['target'] == "beats":
            f = 2
            r = 2
        elif self.template['target'] == "bars":
            f = 1
            r = 1
        for k in xrange(0, r):
            for i in xrange(0, 4*f):
                onebar.append(s1[i % len(s1)])
            for i in xrange(4*f, 6*f):
                onebar.append( s2[i % len(s2)] )
            for i in xrange(6*f, 8*f):
                onebar.append( s3[i % len(s3)] )
        if self.original.analysis.time_signature == 4:
            orig_bar = self.st.shiftTempo(audio.getpieces(self.original, onebar), self.template['tempo']/self.tempo)
        else:
            orig_bar = audio.getpieces(self.original, onebar)
            orig_bar = self.st.shiftTempo(orig_bar, len(orig_bar) / ((44100 * 16 * 2 * 60.0)/self.template['tempo']))
        if orig_bar.numChannels == 1:
            orig_bar = self.mono_to_stereo(orig_bar)
        mixfactor = self.mixfactor(onebar)
        a = self.truncatemix(
                audio.mix(
                    audio.AudioData(
                        self.sample_path + self.template['wubs'][self.tonic], 
                        sampleRate=44100,
                        numChannels=2,
                        verbose=False
                    ),
                    audio.AudioData(
                        self.sample_path + self.template['splashes'][(j+1) % len(self.template['splashes'])],
                        sampleRate=44100,
                        numChannels=2,
                        verbose=False
                    )
                ),
            orig_bar,
            mixfactor
        )
        b = self.truncatemix(
                audio.mix(
                    audio.AudioData(
                        self.sample_path + self.template['wub_breaks'][self.tonic],
                        sampleRate=44100,
                        numChannels=2,
                        verbose=False
                    ),
                    hats
                ),
            orig_bar,
            mixfactor
        )
        return (a, b)

    def remix(self):
        """
            Wub wub wub wub wub wub wub wub wub wub wub wub wub wub wub wub wub wub.
        """
        self.log("Looking up track...", 5)
        self.getTag()
        self.processArt()

        self.log("Listening to %s..." % ('"%s"' % self.tag['title'] if 'title' in self.tag else 'song'), 5)
        self.original = audio.LocalAudioFile(self.infile, False)
        if not 'title' in self.tag:
            self.detectSong(self.original)
        self.st = FastModify()
        
        self.log("Choosing key and tempo...", 10)
        self.tonic = self.original.analysis.key['value']
        self.tempo = self.original.analysis.tempo['value']
        self.bars = self.original.analysis.bars
        self.beats = self.original.analysis.beats
        self.sections = self.original.analysis.sections
        self.tag['key'] = self.keys[self.tonic] if self.tonic >= 0 and self.tonic < 12 else '?'
        self.tag['tempo'] = self.template['tempo']

        self.log("Arranging intro...", 40.0/(len(self.sections) + 1))
        self.partialEncode(self.compileIntro())

        past_progress = 0
        hats  = audio.AudioData(self.sample_path + self.template['hats'], sampleRate=44100, numChannels=2, verbose=False)

        i = 0 # Required if there are no sections
        for i, section in enumerate(self.sections):
            self.log("Arranging section %s of %s..." % (i+1, len(self.sections)), 40.0/(len(self.sections) + 1))
            a, b = self.compileSection(i, section, hats)
            self.partialEncode(a)
            self.partialEncode(b)
            del a, b
        del hats
        self.original.unload()

        self.log("Adding ending...", 5)
        self.partialEncode(
            audio.AudioData(
                self.sample_path + self.template['splash_ends'][(i + 1) % len(self.template['splash_ends'])],
                sampleRate=44100,
                numChannels=2,
                verbose=False
            )
        )
        
        self.log("Mixing...", 5)
        self.mixwav(self.tempfile)

        if self.deleteOriginal:
            try:
                unlink(self.infile)
            except:
                pass  # File could have been deleted by an eager cleanup script

        self.log("Mastering...", 5)
        self.lame(self.tempfile, self.outfile)
        unlink(self.tempfile)
        
        self.log("Adding artwork...", 20)
        self.updateTags(titleSuffix = " (Wub Machine Remix)")
        
        return self.outfile

if __name__ == "__main__":
    CMDRemix(Dubstep)

########NEW FILE########
__FILENAME__ = electrohouse
"""
dubstep.py <ex: dubstepize.py, wubmachine.py, wubwub.py, etc...>

Turns a song into a dubstep remix.
ElectroHouse inherits from the Remixer class.
Dependencies:
    FastModify
    Remixer
    lame (command line binary)
    shntool (command line binary)
    soundstretch (command line binary)

by Peter Sobot <hi@petersobot.com>
    v1: started Jan. 2011
    v2: August 2011
based off of code by Ben Lacker, 2009-02-24.
"""

from remixer import *
from helpers.fastmodify import FastModify
from echonest.modify import Modify
from echonest.action import make_stereo
import numpy

tempo = 128.0

# Audio Division
def half_of(audioData):
    return divide(audioData, 2)[0]

def third_of(audioData):
    return divide(audioData, 3)[0]

def quarter_of(audioData):
    return divide(audioData, 4)[0]

def eighth_of(audioData):
    return divide(audioData, 8)[0]

def eighth_triplet(audioData):
    return cutnote(audioData, 6)

def quarter_triplet(audioData):
    return cutnote(audioData, 3)

def sixteenth_note(audioData):
    return cutnote(audioData, 4)

def eighth_note(audioData):
    return cutnote(audioData, 2)

def dotted_eighth_note(audioData):
    return cutnote(audioData, 0.75)

def quarter_note(audioData):
    return cutnote(audioData, 1)
    
def cutnote(audioData, length):
    beatlength = (audioData.sampleRate * 60 / tempo) #in samples
    i = beatlength/length
    data = audioData.data[0:i]
    if len(data) < i:
        if audioData.numChannels == 2:
            shape = (i - len(data),2)
        else:
            shape = (i - len(data),)
        data = numpy.append(data, numpy.zeros(shape, dtype=numpy.int16), 0)
    r = audio.AudioData(
        ndarray=data,
        numChannels=audioData.numChannels,
        sampleRate = audioData.sampleRate
    )
    return make_stereo(r) if (r.numChannels == 1) else r

def divide(audioData, by):
    return [audio.AudioData(
        ndarray=audioData.data[i:len(audioData.data)/by],
        numChannels=audioData.numChannels,
        sampleRate = audioData.sampleRate
    ) for i in xrange(0, len(audioData.data), len(audioData.data)/by)]

quarter_rest = audio.AudioData(ndarray=numpy.zeros(         ((44100 * 60 / tempo), 2),      dtype=numpy.int16), numChannels=2, sampleRate=44100)
eighth_rest = audio.AudioData(ndarray=numpy.zeros(          ((44100 * 60 / tempo)/2, 2),    dtype=numpy.int16), numChannels=2, sampleRate=44100)
dotted_eighth_rest = audio.AudioData(ndarray=numpy.zeros(   ((44100 * 60 / tempo)/0.75, 2), dtype=numpy.int16), numChannels=2, sampleRate=44100)
quarter_triplet_rest = audio.AudioData(ndarray=numpy.zeros( ((44100 * 60 / tempo)/3, 2),    dtype=numpy.int16), numChannels=2, sampleRate=44100)
sixteenth_rest = audio.AudioData(ndarray=numpy.zeros(       ((44100 * 60 / tempo)/4, 2),    dtype=numpy.int16), numChannels=2, sampleRate=44100)

rhythm_map = {1: sixteenth_note, 2: eighth_note, 3: dotted_eighth_note, 4: quarter_note}
rest_map = {1: sixteenth_rest, 2: eighth_rest, 3: dotted_eighth_rest, 4: quarter_rest}

class note():
  def __init__(self, pitch=None, length=1):
        self.pitch = pitch
        self.length = length
        self.data = rest_map[length]
        self.function = rhythm_map[length]
  def __repr__(self):
        return "%s x 16th note %s" % (self.length, self.pitch if self.pitch is not None else "rest")

def readPattern(filename):
    f = open(filename)
    f.readline()
    # Two spaces for each beat.
    # number 1 through 12 means that note (rather, that interval from root)
    # dash means continue previous
    pattern = []
    for s in f:
        if "+" in s or '#' in s or s == "\n":
            continue
        pattern.extend([''.join(x) for x in zip(*[list(s[z::2]) for z in xrange(2)])])

    bar = [] 
    for sixteenth in pattern:
        if sixteenth == "" or sixteenth == " \n":
            continue
        elif sixteenth == "  ":
            bar.append(note())
        elif sixteenth == "- ":
            last = bar.pop()
            bar.append(note(last.pitch, last.length+1))
        else:
            bar.append(note(int(sixteenth)))
    return bar

class ElectroHouse(Remixer):
    template = {
        'tempo':        128,
        'beat':        ['beat_%s.wav' % i for i in xrange(0, 4)],
        'intro': 'intro_16.wav',
        'splash':     'splash.wav',
        'build':      'build.wav',
        'body' : [
          'body/c.wav',
          'body/c-sharp.wav',
          'body/d.wav',
          'body/d-sharp.wav',
          'body/e.wav',
          'body/f.wav',
          'body/f-sharp.wav',
          'body/g.wav',
          'body/g-sharp.wav',
          'body/a.wav',
          'body/a-sharp.wav',
          'body/b.wav'
        ],
        'mixpoint': 18,     # "db factor" of wubs - 0 is softest wubs, infinity is... probably extremely loud 
        'target': "beats",
        'splash_ends':  [  'splash-ends/1.wav',
                            'splash-ends/2.wav',
                            'splash-ends/3.wav',
                            'splash-ends/4.wav'
                        ],
    }
    st = None
    sampleCache = {}

    def searchSamples(self, j, key):
        """
            Find all samples (beats) of a given key in a given section.
        """
        hashkey = "_%s-%s" % (j, key)
        if not hashkey in self.sampleCache:
            if self.sections:
                pool = self.sections[j % len(self.sections)]
            elif self.original.analysis.bars:
                pool = self.original.analysis.bars
            elif self.original.analysis.segments:
                pool = self.original.analysis.segments
            else:
                raise Exception("No samples found for section %s." % j+1)
            a = self.getSamples(pool, key)
            for tries in xrange(0, 5):
                if len(a):
                    break
                key = (key + 7) % 12
                a = self.getSamples(pool, key)
            else:
                for tries in xrange(0, 5):
                    if len(a):
                        break
                    if self.sections:
                        j = (j + 1) % len(self.sections)
                    elif self.original.analysis.bars:
                        j = (j + 1) % len(self.original.analysis.bars)
                    elif self.original.analysis.segments:
                        j = (j + 1) % len(self.original.analysis.segments)
                    key = (key + 2) % 12
                    a = self.getSamples(pool, key)
            self.sampleCache[hashkey] = a
        return self.sampleCache[hashkey]

    def getSamples(self, section, pitch, target="beats"):
        """
            The EchoNest-y workhorse. Finds all beats/bars in a given section, of a given pitch.
        """
        hashkey = "__%s.%s" % (str(section), pitch)
        if not hashkey in self.sampleCache:
            sample_list = audio.AudioQuantumList()
            if target == "beats":
                try:
                    sample_list.extend([b for x in section.children() for b in x.children()])
                except:
                    sample_list.extend(section)
            elif target == "bars":
                sample_list.extend(section.children())
            self.sampleCache[hashkey] = sample_list.that(overlap_ends_of(self.original.analysis.segments.that(have_pitch_max(pitch)).that(overlap_starts_of(sample_list))))
        return self.sampleCache[hashkey]

    def mixfactor(self, segment):
        """
            Computes a rough "mixfactor" - the balance between wubs and original audio for a given segment.
            Mixfactor returned:
              1: full wub
              0: full original
            Result can be fed into echonest.audio.mix() as the third parameter.
        """
        mixfactor = 0
        a = (89.0/1.5) + self.template['mixpoint']
        b = (188.0/1.5) + self.template['mixpoint']
        loud = self.loudness(self.original.analysis.segments, segment)
        if not loud:
            loud = self.original.analysis.loudness
        if loud != -1 * b:
            mixfactor = float(float(loud + a)/float(loud + b))
        if mixfactor > 0.8:
            mixfactor = 0.8
        elif mixfactor < 0.3:
            mixfactor = 0.3
        return mixfactor

    def compileIntro(self, section=0, intro=None):
        if not intro:
            intro = audio.AudioData(self.sample_path + self.template['intro'], sampleRate=44100, numChannels=2, verbose=False)
        out = audio.AudioQuantumList()
        section_hash_keys = []

        for i, item in enumerate(readPattern('samples/electrohouse/intro.txt')):
            if item.pitch is None:
                out.append(item.data)
            else:
                samples = self.searchSamples(section, (item.pitch + self.tonic) % 12) 
                if not samples:
                    out.append(item.data)
                else:
                    hash_key = str(samples[i%len(samples)])
                    if not hash_key in self.sampleCache:
                        self.sampleCache[hash_key] = self.st.shiftTempo(samples[i%len(samples)].render(), self.template['tempo']/self.tempo)
                        section_hash_keys.append(hash_key)
                    out.append(
                      item.function(
                        self.sampleCache[hash_key]
                      )
                    )
        shifted = audio.assemble(out, numChannels = 2)
        if shifted.numChannels == 1:    
            shifted = self.mono_to_stereo(shifted)
        for hash_key in section_hash_keys:
            del self.sampleCache[hash_key]
        return self.truncatemix(intro, shifted, 0.3)

    def compileSection(self, j, section, backing):
        out = audio.AudioQuantumList()
        section_hash_keys = []

        for i, item in enumerate(readPattern('samples/electrohouse/section.txt')):
            if item.pitch is None:
                out.append(item.data)
            else:
                samples = self.searchSamples(j, (item.pitch + self.tonic) % 12)
                if not samples:
                    out.append(item.data)
                else:
                    hash_key = str(samples[i%len(samples)])
                    if not hash_key in self.sampleCache:
                        self.sampleCache[hash_key] = self.st.shiftTempo(samples[i%len(samples)].render(), self.template['tempo']/self.tempo)
                        section_hash_keys.append(hash_key)
                    out.append(
                      item.function(
                          self.sampleCache[hash_key]
                      )
                    )
        shifted = audio.assemble(out, numChannels = 2)
        if shifted.numChannels == 1:
            shifted = self.mono_to_stereo(shifted)
        for hash_key in section_hash_keys:
            del self.sampleCache[hash_key]
        return self.truncatemix(backing, shifted, 0.3)

    def remix(self):
        """
            Wub wub wub wub wub wub wub wub wub wub wub wub wub wub wub wub wub wub.
        """
        self.log("Looking up track...", 5)
        self.getTag()
        self.processArt()

        self.log("Listening to %s..." % ('"%s"' % self.tag['title'] if 'title' in self.tag else 'song'), 5)
        self.original = audio.LocalAudioFile(self.infile, False)
        if not 'title' in self.tag:
            self.detectSong(self.original)
        self.st = FastModify()
        
        self.log("Choosing key and tempo...", 10)
        self.tonic = self.original.analysis.key['value']
        self.tempo = self.original.analysis.tempo['value']
        if not self.tempo:
            self.tempo = 128.0
        self.bars = self.original.analysis.bars
        self.beats = self.original.analysis.beats
        self.sections = self.original.analysis.sections
        self.tag['key'] = self.keys[self.tonic] if self.tonic >= 0 and self.tonic < 12 else '?'
        if 'title' in self.tag and self.tag['title'] == u'I Wish':
            self.tonic += 2
            self.tag['key'] = 'D#'
        self.tag['tempo'] = self.template['tempo']

        self.log("Arranging intro...", 40.0/(len(self.sections) + 1))
        intro = audio.AudioData(self.sample_path + self.template['intro'], sampleRate=44100, numChannels=2, verbose=False)
        self.partialEncode(self.compileIntro(0, intro))

        i = 0 # Required if there are no sections
        sections = self.sections[1:] if len(self.sections) % 2 else self.sections
        if len(sections) > 2:
            backing = audio.AudioData(self.sample_path + self.template['body'][self.tonic], sampleRate=44100, numChannels=2, verbose=False)
            for i, section in enumerate(sections):
                self.log("Arranging section %s of %s..." % (i+1, len(sections)), 40.0/(len(sections) + 1))
                a = self.compileSection(i, section, backing) if i != (len(sections)/2 + 1) else self.compileIntro(i, intro)
                self.partialEncode(a)
                del a
        self.original.unload()

        self.log("Adding ending...", 5)
        self.partialEncode(
            audio.AudioData(
                self.sample_path + self.template['splash_ends'][(i + 1) % len(self.template['splash_ends'])],
                sampleRate=44100,
                numChannels=2,
                verbose=False
            )
        )
        
        self.log("Mixing...", 5)
        self.mixwav(self.tempfile)

        if self.deleteOriginal:
            try:
                unlink(self.infile)
            except:
                pass  # File could have been deleted by an eager cleanup script

        self.log("Mastering...", 5)
        self.lame(self.tempfile, self.outfile)
        unlink(self.tempfile)
        
        self.log("Adding artwork...", 20)
        self.updateTags(titleSuffix = " (Wub Machine Electro Remix)")
        
        return self.outfile

if __name__ == "__main__":
    CMDRemix(ElectroHouse)


########NEW FILE########
__FILENAME__ = server
"""
    The Wub Machine
    Python web interface
    started August 5 2011 by Peter Sobot (petersobot.com)
"""

__author__ = "Peter Sobot"
__copyright__ = "Copyright (C) 2011 Peter Sobot"
__version__ = "2.2"

import json, time, locale, traceback, gc, logging, os, database, urllib
import tornado.ioloop, tornado.web, tornado.template, tornado.httpclient, tornado.escape, tornado.websocket
import tornadio, tornadio.server
import config
from datetime import datetime, timedelta
from hashlib import md5

# Wubmachine-specific libraries
from helpers.remixqueue import RemixQueue
from helpers.soundcloud import SoundCloud
from helpers.cleanup import Cleanup
from helpers.daemon import Daemon
from helpers.web import *

# Kinds of remixers.
from remixers.dubstep import Dubstep
from remixers.electrohouse import ElectroHouse
remixers = {
  'Dubstep': Dubstep,
  'ElectroHouse': ElectroHouse
}

# Check dependencies...
# Check required version numbers
assert tornado.version_info >= (2, 0, 0), "Tornado v2 or greater is required!"
assert tornadio.__version__ >= (0, 0, 4), "Tornadio v0.0.4 or greater is required!"

# Instead of using xheaders, which doesn't seem to work under Tornadio, we do this:
if config.nginx:
    class RequestHandler(tornado.web.RequestHandler):
        """
            Patched Tornado RequestHandler to take care of Nginx ip proxying
        """
        def __init__(self, application, request, **kwargs):
            if 'X-Real-Ip' in request.headers:
                request.remote_ip = request.headers['X-Real-Ip']
            tornado.web.RequestHandler.__init__(self, application, request, **kwargs)
else:
    RequestHandler = tornado.web.RequestHandler

# Handlers

class MainHandler(RequestHandler):
    def get(self):
        js = ("window.wubconfig = %s;" % json.dumps(config.javascript)) + javascripts
        kwargs = {
            "isOpen": r.isAccepting(),
            "track": sc.frontPageTrack(),
            "isErroring": r.errorRateExceeded(),
            'count': locale.format("%d", trackCount, grouping=True),
            'cleanup_timeout': time_in_words(config.cleanup_timeout),
            'javascript': js,
            'connectform': connectform
        }
        self.write(templates.load('index.html').generate(**kwargs)) 
    def head(self):
        self.finish()

class ProgressSocket(tornadio.SocketConnection):
    listeners = {}

    @classmethod
    def update(self, uid, data):
        try:  
            self.listeners[uid].send(data)
        except:
            pass

    def on_open(self, *args, **kwargs):
        try:
            self.uid = kwargs['extra']
            if self.uid in r.finished:
                try:
                    self.close()
                except:
                    pass
            else:
                self.listeners[self.uid] = self
                if self.uid in r.remixers:
                    r.remixers[self.uid].being_watched = True
                    log.info("Remixer %s is now being watched..." % self.uid)
                r.cleanup()
                if r.isAvailable():
                    try:
                        r.start(self.uid)
                    except:
                        self.send({ 'status': -1, 'text': "Sorry, something went wrong. Please try again later!", 'progress': 0, 'uid': self.uid, 'time': time.time() })
                        self.close()
                log.info("Opened progress socket for %s" % self.uid)
        except:
            log.error("Failed to open progress socket for %s because: %s" % (self.uid, traceback.format_exc()) )

    def on_close(self):
        try:
            log.info("Progress socket for %s received on_close event. Stopping..." % self.uid)
            try:
                r.stop(self.uid)
            except:
                pass
            if self.uid in r.remixers:
                r.remixers[self.uid].being_watched = False
            if self.uid in self.listeners:
                del self.listeners[self.uid]
            log.info("Closed progress socket for %s" % self.uid)
        except:
          log.warning("Failed to close progress socket for %s due to:\n%s" % (self.uid, traceback.format_exc()))

    def on_message(self, message):
        pass

class MonitorSocket(tornadio.SocketConnection):
    monitors = set()

    @classmethod
    def update(self, uid):
        try:
            if self.monitors:
                data = MonitorHandler.track(uid)
            for m in self.monitors.copy():
                try:  
                    m.send(data.decode('utf-8'))
                    m.send(MonitorHandler.overview())
                except:
                    log.error("Failed to send data to monitor.")
        except:
            log.error("Major failure in MonitorSocket.update.")

    def on_open(self, *args, **kwargs):
        log.info("Opened monitor socket.")
        self.monitors.add(self)

    def on_close(self):
        log.info("Closed monitor socket.")
        self.monitors.remove(self)

    def on_message(self, message):
        pass

class MonitorHandler(RequestHandler):
    keys = ['upload', 'download', 'remixTrue', 'remixFalse', 'shareTrue', 'shareFalse']

    @tornado.web.asynchronous
    def get(self, sub=None, uid=None):
        if sub:
            sections = {
                'graph': self.graph,
                'overview': self.overview,
                'latest': self.latest,
                'remixqueue': self.remixqueue,
                'timespan' : self.timespan
            }
            if sub in sections:
                self.write(sections[sub]())
                self.finish()
            else:
                raise tornado.web.HTTPError(404)
        else:
            kwargs = {
                'overview': self.overview(),
                'latest': self.latest(),
                'config': "window.wubconfig = %s;" % json.dumps(config.javascript)
            }
            self.write(templates.load('monitor.html').generate(**kwargs))
            self.finish()

    def clearqueue(self):
        del self.watchqueue[:]

    @classmethod
    def histogram(self, interval=None):
        db = database.Session()
        try:
            query = db.query(database.Event).add_columns('count(*)', database.Event.action, database.Event.success).group_by('action', 'success')
            if interval:
                limit = datetime.now() - timedelta(**{ interval: 1 })
                d = query.filter(database.Event.start > limit).all()
            else:
                d = query.all()
            n = {}
            for k in self.keys:
                n[k] = 0
            for a in d:
                if a.action == 'upload' or a.action == 'download':
                    n[a.action] = int(a.__dict__['count(*)'])
                elif a.action == 'remix' or a.action == 'share':
                    n["%s%s" % (a.action, a.success)] = int(a.__dict__['count(*)'])
            return n
        except:
            log.error("DB read exception:\n%s" % traceback.format_exc())
            return {}

    def remixqueue(self):
        self.set_header("Content-Type", 'text/plain')
        return str("Remixers: %s\nFinished: %s\nQueue:    %s\nRunning:  %s" % (r.remixers, r.finished, r.queue, r.running))

    @classmethod
    def overview(self):
        kwargs = {
            'ct': str(datetime.now()),
            'inqueue': len(r.queue),
            'processing': len(r.running),
            'maximum': config.maximum_concurrent_remixes,
            'maximumexceeded': len(r.remixers) > config.maximum_concurrent_remixes,
            'hourly': config.hourly_remix_limit,
            'hourlyexceeded': r.countInHour() >= config.hourly_remix_limit,
            'errorInterval': 1,
            'errorRate': r.errorRate(),
            'errorRateExceeded': r.errorRateExceeded(),
            'isOpen': r.isAccepting(),
            'hour': MonitorHandler.histogram('hours'),
            'day': MonitorHandler.histogram('days'),
            'ever': MonitorHandler.histogram(),
        }
        return templates.load('overview.html').generate(**kwargs)

    def current(self):
        running = [v for k, v in r.remixers.iteritems() if k in r.running]
        return templates.load('current.html').generate(c=running)

    def shared(self):
        db = database.Session()
        try:
            d = db.query(database.Event).filter_by(action = "sharing", success = True).group_by(database.Event.uid).order_by(database.Event.id.desc()).limit(6).all()
        except:
            log.error("DB read exception:\n%s" % traceback.format_exc())
        return templates.load('shared.html').generate(tracks=d)

    @classmethod
    def track(self, track):
        db = database.Session()

        if not track:
            raise tornado.web.HTTPError(400)

        if isinstance(track, database.Track):
            try:
                track = db.merge(track)
            except:
                log.error("DB read exception:\n%s" % traceback.format_exc())
                db.rollback()
        else:
            if isinstance(track, dict) and 'uid' in track:
                track = track['uid']
            elif not isinstance(track, str) or len(track) != 32:
                return ''
            try:
                tracks =  db.query(database.Track).filter(database.Track.uid == track).all()
            except:
                log.error("DB read exception:\n%s" % traceback.format_exc())
                db.rollback()
            if not tracks:
                return ''
            else:
                track = tracks[0]

        for stat in ['upload', 'remix', 'share', 'download']:
            track.__setattr__(stat, None)
        
        events = {}
        for event in track.events:
            events[event.action] = event
        track.upload = events.get('upload')
        track.remix = events.get('remix')
        track.share = events.get('share')
        track.download = events.get('download')
        track.running = track.uid in r.running or (track.share and track.share.start and not track.share.end and track.share.success is None)
        track.failed = (track.remix and track.remix.success == False) or (track.share and track.share.success == False)
        if track.failed:
            if track.remix.success is False:
                track.failure = track.remix.detail 
            elif track.share.detail is not None:
                track.failure = track.share.detail
            else:
                track.failure = ''
        try:
            track.progress = r.remixers[track.uid].last['progress']
            track.text = r.remixers[track.uid].last['text']
        except:
            track.progress = None
            track.text = None

        kwargs = {
            'track': track,
            'exists': os.path.exists,
            'time_ago_in_words': time_ago_in_words,
            'seconds_to_time': seconds_to_time,
            'convert_bytes': convert_bytes
        }
        return templates.load('track.html').generate(**kwargs)

    def latest(self):
        db = database.Session()
        try:
            tracks = db.query(database.Track).order_by(database.Track.id.desc()).limit(config.monitor_limit).all()
        except:
            log.error("DB read exception, rolling back:\n%s" % traceback.format_exc())
            db.rollback()
        return ''.join([self.track(track) for track in tracks])

    def timespan(self):
        start = float(self.get_argument('start'))
        end = float(self.get_argument('end'))
        
        if end - start < 0:
            raise tornado.web.HTTPError(400)
        elif end - start > config.monitor_time_limit:
            start = end - config.monitor_time_limit

        db = database.Session()
        try:
            tracks = db.query(database.Track).filter(database.Track.time < datetime.fromtimestamp(end)).filter(database.Track.time > datetime.fromtimestamp(start)).order_by(database.Track.id.desc()).all()
        except:
            log.error("DB read exception, rolling back:\n%s" % traceback.format_exc())
            db.rollback()
        return ''.join([self.track(track) for track in tracks])

    def graph(self):
        history = {}
        db = database.Session()
        for i in xrange(1, 24*2): # last 3 days
            low = datetime.now() - timedelta(hours = i)
            high = low + timedelta(hours = 1)
            timestamp = 1000 * time.mktime(high.timetuple())
            try:
                dayr = db.query(database.Event).add_columns('count(*)', database.Event.action, database.Event.success).group_by('action', 'success').filter(database.Event.start.between(low, high)).all()
                n = {}
                for daya in dayr:
                    if daya.action == 'download':
                        n[daya.action] = [timestamp , int(daya.__dict__['count(*)'])]
                    elif daya.action == 'remix' or daya.action == 'share':
                        n["%s%s" % (daya.action, daya.success)] = [timestamp, int(daya.__dict__['count(*)'])]

                for k in self.keys:
                    if not k in history:
                        history[k] = []
                    if k in n:
                        history[k].append(n[k])
                    else:
                        history[k].append([timestamp, int(0)])
            except:
                log.error("DB read exception, rolling back:\n%s" % traceback.format_exc())
                db.rollback()
        return history 

class ShareHandler(RequestHandler):
    @tornado.web.asynchronous
    def get(self, uid):
        self.uid = uid
        try:
            token = str(self.get_argument('token'))
            timeout = config.soundcloud_timeout
            self.event = database.Event(uid, "share", ip = self.request.remote_ip) 

            if not uid in r.finished:
                raise tornado.web.HTTPError(404)

            t = r.finished[uid]['tag']

            description = config.soundcloud_description
            if 'artist' in t and 'album' in t and t['artist'].strip() != '' and t['album'].strip() != '':
                description = ("Original song by %s, from the album \"%s\".<br />" % (t['artist'].strip(), t['album'].strip())) + description
            elif 'artist' in t and t['artist'].strip() != '':
                description = ("Original song by %s.<br />" % t['artist'].strip()) + description

            form = MultiPartForm()
            form.add_field('oauth_token', token)
            form.add_field('track[title]', t['new_title'].encode('utf-8'))
            form.add_field('track[genre]', t['style'])
            form.add_field('track[license]', "no-rights-reserved")
            form.add_field('track[tag_list]', ' '.join(['"%s"' % tag for tag in config.soundcloud_tag_list]))
            form.add_field('track[description]', description.encode('utf-8'))
            form.add_field('track[track_type]', 'remix')
            form.add_field('track[downloadable]', 'true')
            form.add_field('track[sharing_note]', config.soundcloud_sharing_note)
            form.add_file('track[asset_data]', '%s.mp3' % uid, open(t['remixed']))

            if 'tempo' in t:
                form.add_field('track[bpm]', t['tempo'])
            if 'art' in t:
                form.add_file('track[artwork_data]', '%s.png' % uid, open(t['art']))
            if 'key' in t:
                form.add_field('track[key_signature]', t['key'])

            MonitorSocket.update(self.uid)

            self.ht = tornado.httpclient.AsyncHTTPClient()
            self.ht.fetch(
                "https://api.soundcloud.com/tracks.json",
                self._get,
                method = 'POST',
                headers = {"Content-Type": form.get_content_type()},
                body = str(form),
                request_timeout = timeout,
                connect_timeout = timeout
            )
        except:
            self.write({ 'error': traceback.format_exc().splitlines()[-1] })
            self.event.success = False
            self.event.end = datetime.now()
            self.event.detail = traceback.format_exc()
            MonitorSocket.update(self.uid)
        finally:
            db = database.Session()
            try:
                db.add(self.event)
                db.commit()
            except:
                log.error("DB exception, rolling back:\n%s" % traceback.format_exc())
                db.rollback()
    
    def _get(self, response):
        self.write(response.body)
        self.finish()
        r = json.loads(response.body)
        try:
            db = database.Session()
            self.event = db.merge(self.event)
            self.event.success = True
            self.event.end = datetime.now()
            self.event.detail = r['permalink_url'].encode('ascii', 'ignore')
            db.commit()
        except:
            log.error("DB exception, rolling back:\n%s" % traceback.format_exc())
            db.rollback()
        MonitorSocket.update(self.uid)
        sc.fetchTracks()

class DownloadHandler(RequestHandler):
    def get(self, uid):
        if not uid in r.finished or not os.path.isfile('static/songs/%s.mp3' % uid):
            raise tornado.web.HTTPError(404)
        else:
            db = database.Session()
            try:
                uploader = db.query(database.Event.ip).filter_by(uid = uid, action = "upload").first()[0]
            except:
                log.error("DB exception, rolling back:\n%s" % traceback.format_exc())
                db.rollback()
                uploader = self.request.remote_ip
            if uploader != self.request.remote_ip:
                log.error("Download attempt on remix %s by IP %s, not uploader %s!" % (uid, self.request.remote_ip, uploader))
                raise tornado.web.HTTPError(403)
            filename = "%s.mp3" % (r.finished[uid]['tag']['new_title'] if 'new_title' in r.finished[uid]['tag'] else uid)
            self.set_header('Content-disposition', 'attachment; filename="%s"' % filename)
            self.set_header('Content-type', 'audio/mpeg')
            self.set_header('Content-Length', os.stat('static/songs/%s.mp3' % uid)[6])
            self.write(open('static/songs/%s.mp3' % uid).read())
            self.finish()
            try:
                db.add(database.Event(uid, "download", success = True, ip = self.request.remote_ip))
                db.commit()
            except:
                log.error("DB exception, rolling back:\n%s" % traceback.format_exc())
                db.rollback()
            MonitorSocket.update(uid)

class UploadHandler(RequestHandler):
    def trackDone(self, final):
        # [TODO]: Why is this here? Move this somewhere more appropriate.
        global trackCount
        trackCount += 1
        if self.uid in ProgressSocket.listeners:
            log.info("Closing client connection for track %s..." % self.uid)
            ProgressSocket.listeners[self.uid].close()
            log.info("Closed client connection for track %s." % self.uid)

    def post(self):
        self.uid = config.uid()
        try:
            remixer = remixers[self.get_argument('style')]
        except:
            log.error("Error when trying to handle upload: %s" % traceback.format_exc())
            self.write({ "error" : "No remixer type specified!" })
        
        self.track = database.Track(self.uid, style=self.get_argument('style'))
        self.event = database.Event(self.uid, "upload", None, self.request.remote_ip, urllib.unquote_plus(self.get_argument('qqfile').encode('ascii', 'ignore')))

        try:
            extension = os.path.splitext(self.get_argument('qqfile'))[1]
        except:
            extension = '.mp3'
        self.track.extension = extension
        targetPath = os.path.join('uploads/', '%s%s' % (self.uid, extension))

        if extension not in config.allowed_file_extensions:
            self.write({ 'error': "Sorry, but %s only works with %s." % (config.app_name, list_in_words([e[1:] for e in config.allowed_file_extensions])) })
            return

        try:
            f = open(targetPath, 'w')
            data = self.request.body if not self.request.files else self.request.files['upload'][0]['body'] 
            f.write(data)
            f.close()

            self.track.hash = md5(data).hexdigest()
            self.track.size = len(data)
            del data

            if not self.request.files:
                del self.request.body
            else:
                del self.request.files['upload'][0]['body']

            r.add(self.uid, extension, remixer, ProgressSocket.update, self.trackDone)
            self.event.success = True
            response = r.waitingResponse(self.uid)
            response['success'] = True
            self.write(response)
        except Exception as e:
            log.error("Error when trying to handle upload: %s" % traceback.format_exc())
            self.write({ "error" : "Could not save file." })
            self.event.success = False
        self.event.end = datetime.now()

        db = database.Session()
        try:
            db.add(self.track)
            db.add(self.event)
            db.commit()
        except:
            log.error("DB exception, rolling back:\n%s" % traceback.format_exc())
            db.rollback()

        MonitorSocket.update(self.uid)
        gc.collect()

application = tornado.web.Application([
    (r"/(favicon.ico)", tornado.web.StaticFileHandler, {"path": "static/img/"}),
    (r"/static/(.*)", tornado.web.StaticFileHandler, {"path": "static/"}),
    (r"/monitor[/]?([^/]+)?[/]?(.*)", MonitorHandler), #Fix this
    (r"/upload", UploadHandler),
    (r"/share/(%s)" % config.uid_re, ShareHandler),
    (r"/download/(%s)" % config.uid_re, DownloadHandler),
    (r"/", MainHandler),
    tornadio.get_router(
        MonitorSocket,
        resource = config.monitor_resource
    ).route(),
    tornadio.get_router(
        ProgressSocket,
        resource = config.progress_resource,
        extra_re = config.uid_re,
        extra_sep = config.socket_extra_sep
    ).route()],
    socket_io_port = config.socket_io_port,
    enabled_protocols = ['websocket', 'xhr-multipart', 'xhr-polling', 'jsonp-polling'],
    )


if __name__ == "__main__":
    Daemon()

    log = logging.getLogger()
    log.name = config.log_name
    handler = logging.FileHandler(config.log_file)
    handler.setFormatter(logging.Formatter(config.log_format)) 
    handler.setLevel(logging.DEBUG)
    log.addHandler(handler)

    try:
        log.info("Starting %s..." % config.app_name)
        try:
            locale.setlocale(locale.LC_ALL, 'en_US.utf8')
        except:
            locale.setlocale(locale.LC_ALL, 'en_US')
        
        log.info("\tConnecting to MySQL...")
        db = database.Session()
        if not db:
            log.critical("Can't connect to DB!")
            exit(1)

        log.info("\tGrabbing track count from DB...")
        trackCount = db.query(database.Event).filter_by(action='remix', success = True).count()

        log.info("\tClearing temp directories...")
        cleanup = Cleanup(log, None)
        cleanup.all()

        log.info("\tStarting RemixQueue...")
        r = RemixQueue(MonitorSocket)
        cleanup.remixQueue = r

        log.info("\tInstantiating SoundCloud object...")
        sc = SoundCloud(log)

        log.info("\tLoading templates...")
        templates = tornado.template.Loader("templates/")
        templates.autoescape = None

        log.info("\tStarting cleanup timers...")
        fileCleanupTimer = tornado.ioloop.PeriodicCallback(cleanup.active, 1000*config.cleanup_timeout)
        fileCleanupTimer.start()
        
        queueCleanupTimer = tornado.ioloop.PeriodicCallback(r.cleanup, 100*min(config.watch_timeout, config.remix_timeout, config.wait_timeout))
        queueCleanupTimer.start()

        log.info("\tCaching javascripts...")
        javascripts = '\n'.join([
            open('./static/js/jquery.fileupload.js').read(),
            open('./static/js/front.js').read(),
            open('./static/js/player.js').read(),
        ])
        connectform = open('./static/js/connectform.js').read()

        log.info("\tStarting Tornado...")
        application.listen(8888)
        log.info("...started!")
        tornadio.server.SocketServer(application, xheaders=config.nginx)
    except:
        raise
    finally:
        log.critical("Error: %s" % traceback.format_exc())
        log.critical("IOLoop instance stopped. About to shutdown...")
        try:
            cleanup.all()
        except:
            pass
        log.critical("Shutting down!")
        if os.path.exists('server.py.pid'):
            os.remove('server.py.pid')
        exit(0)


########NEW FILE########
