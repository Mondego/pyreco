__FILENAME__ = app
# -*- coding: utf-8 -*-
import sys

from flask import Flask, g, request
from flask.ext.restful import Api

from shiva import resources
from shiva.config import Configurator
from shiva.models import db

app = Flask(__name__)
app.config.from_object(Configurator())
db.app = app
db.init_app(app)

# RESTful API
api = Api(app)

# Artists
api.add_resource(resources.ArtistResource, '/artists',
                 '/artists/<int:artist_id>', '/artists/<artist_slug>',
                 endpoint='artists')
api.add_resource(resources.ShowsResource, '/artists/<int:artist_id>/shows',
                 '/artists/<artist_slug>/shows', endpoint='shows')

# Albums
api.add_resource(resources.AlbumResource, '/albums', '/albums/<int:album_id>',
                 '/albums/<album_slug>', endpoint='albums')

# Tracks
api.add_resource(resources.TrackResource, '/tracks', '/tracks/<int:track_id>',
                 '/tracks/<track_slug>', endpoint='tracks')
api.add_resource(resources.LyricsResource, '/tracks/<int:track_id>/lyrics',
                 '/tracks/<track_slug>/lyrics', endpoint='lyrics')
api.add_resource(resources.ConvertResource, '/tracks/<int:track_id>/convert',
                 '/tracks/<track_slug>/convert', endpoint='convert')

# Other
api.add_resource(resources.RandomResource, '/random/<resource_name>',
                 endpoint='random')
api.add_resource(resources.WhatsNewResource, '/whatsnew', endpoint='whatsnew')
api.add_resource(resources.ClientResource, '/clients', endpoint='client')
api.add_resource(resources.AboutResource, '/about', endpoint='about')


@app.before_request
def before_request():
    g.db = db


@app.after_request
def after_request(response):
    if getattr(g, 'cors', False):
        response.headers['Access-Control-Allow-Origin'] = g.cors
        response.headers['Access-Control-Allow-Headers'] = \
            'Accept, Content-Type, Origin, X-Requested-With'

    return response


def main():
    try:
        port = int(sys.argv[1])
    except:
        port = 9002

    app.run(host='0.0.0.0', port=port, debug=True)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = project
# -*- coding: utf-8 -*-
from shiva.converter import Converter
from shiva.media import MimeType

DEBUG = True

SQLALCHEMY_DATABASE_URI = 'sqlite:///shiva.db'
ACCEPTED_FORMATS = (
    'mp3',
)
MIMETYPES = (
    MimeType(type='audio', subtype='mp3', extension='mp3',
             acodec='libmp3lame'),
    MimeType(type='audio', subtype='ogg', extension='ogg',
             acodec='libvorbis'),
)
CONVERTER_CLASS = Converter
DEFAULT_ALBUM_COVER = ('http://wortraub.com/wp-content/uploads/2012/07/'
                       'Vinyl_Close_Up.jpg')
DEFAULT_ARTIST_IMAGE = 'http://www.super8duncan.com/images/band_silhouette.jpg'

# https://en.wikipedia.org/wiki/Cross-origin_resource_sharing
CORS_ENABLED = False
# CORS_ALLOWED_ORIGINS accepts the following values:
# The string '*' to allow all origins
# An specific domain: 'google.com'
# A tuple of strings to allow multiple domains: ('google.com', 'napster.com')
CORS_ALLOWED_ORIGINS = '*'

########NEW FILE########
__FILENAME__ = converter
# -*- coding: utf-8 -*-
import os
import subprocess
import urllib

from flask import current_app as app

from shiva.exceptions import InvalidMimeTypeError
from shiva.media import MimeType


def get_converter():
    ConverterClass = app.config.get('CONVERTER_CLASS', Converter)

    return ConverterClass


class Converter(object):
    """
    Class responsible for format conversion. Receives the path to a track (as a
    string) and decides where to save the converted files. It also decides
    which external software to use for conversion.

    """

    CONVERSION_URI = '/tracks/%s/convert?%s'

    def __init__(self, track, mimetype):
        self.track = track
        self.mimetypes = self.get_mimetypes()
        self.set_mimetype(mimetype)

    def get_mimetypes(self):
        """
        Returns the list of mimetypes that the system supports, provided by the
        MIMETYPES setting.

        """

        return app.config.get('MIMETYPES', [])

    def set_mimetype(self, mimetype):
        """
        Sets the mimetype or raises an InvalidMimeTypeError exception if it's
        not found in the settings.
        """

        mimetype_object = None
        if issubclass(mimetype.__class__, MimeType):
            mimetype_object = mimetype
        else:
            for _mime in self.mimetypes:
                if hasattr(_mime, 'matches') and callable(_mime.matches):
                    if _mime.matches(mimetype):
                        mimetype_object = _mime

        if mimetype_object:
            self.fullpath = None
            self.uri = None
            self.mimetype = mimetype_object
        else:
            raise InvalidMimeTypeError(mimetype)

    def get_dest_directory(self, mime=None):
        """
        Retrieves the path on which a track's duplicates, i.e. that same track
        converted to other formats, will be stored.

        In this case they will be stored along the original track, in the same
        directory.

        """

        return os.path.dirname(self.track.path)

    def get_dest_filename(self):
        filename = os.path.basename(self.track.path)
        filename = '.'.join(filename.split('.')[0:-1])

        return '.'.join((filename, self.mimetype.extension))

    def get_dest_fullpath(self):
        if self.fullpath:
            return self.fullpath

        directory = self.get_dest_directory()
        filename = self.get_dest_filename()
        self.fullpath = os.path.join(directory, filename)

        return self.fullpath

    def get_conversion_uri(self):
        mimetype = urllib.urlencode({'mimetype': str(self.mimetype)})
        uri = self.CONVERSION_URI % (self.track.pk, mimetype)

        return ''.join((app.config.get('SERVER_URI') or '', uri))

    def get_uri(self):
        if self.converted_file_exists():
            self.uri = self.get_file_uri()
        else:
            self.uri = self.get_conversion_uri()

        return self.uri

    def get_file_uri(self):
        for mdir in app.config['MEDIA_DIRS']:
            return mdir.urlize(self.get_dest_fullpath())

    def convert(self):
        path = self.get_dest_fullpath()
        if self.converted_file_exists():
            return path

        # Don't do app.config.get('FFMPEG_PATH', 'ffmpeg'). That will cause an
        # error when FFMPEG_PATH is set to None or empty string.
        ffmpeg = app.config.get('FFMPEG_PATH') or 'ffmpeg'
        cmd = [ffmpeg, '-i', self.track.path, '-aq', '60', '-acodec',
               self.mimetype.acodec, path]

        proc = subprocess.call(cmd)

        return path

    def converted_file_exists(self):
        return os.path.exists(self.get_dest_fullpath())

########NEW FILE########
__FILENAME__ = decorators
from functools import wraps
from flask import g, request, make_response
from flask import current_app as app


def allow_origins(func=None, custom_origins=None):
    """
    Add headers for Cross-origin resource sharing based on
    `CORS_ALLOWED_ORIGINS` in config, or parameters passed to the decorator.
    `CORS_ALLOWED_ORIGINS` can be a list of allowed origins or `"*"` to allow
    all origins.

    """

    def wrapped(func):
        def _get_origin(allowed_origins, origin):
            """ Helper method to discover the proper value for
            Access-Control-Allow-Origin to use.

            If the allowed origin is a string it will check if it's '*'
            wildcard or an actual domain. When a tuple or list is given
            instead, it will look for the current domain in the list. If any of
            the checks fail it will return False.

            """

            if type(allowed_origins) in (str, unicode):
                if allowed_origins == '*' or allowed_origins == origin:
                    return allowed_origins

            elif type(allowed_origins) in (list, tuple):
                if origin in allowed_origins:
                    return origin

            return False

        @wraps(func)
        def decorated(*args, **kwargs):
            origin = request.headers.get('Origin')

            # `app.config.get('CORS_ALLOWED_ORIGINS', [])` should really be the
            # default option in `def allow_origins` for `custom_origins` but
            # that would use `app` outside of the application context
            allowed_origins = custom_origins or \
                app.config.get('CORS_ALLOWED_ORIGINS', [])

            # Actual headers are added in `after_request`
            g.cors = _get_origin(allowed_origins, origin)

            return func(*args, **kwargs)

        return decorated

    if func:
        return wrapped(func)

    return wrapped

########NEW FILE########
__FILENAME__ = exceptions
# -*- coding: utf-8 -*-


class MetadataManagerReadError(Exception):
    pass


class InvalidMimeTypeError(Exception):
    def __init__(self, mimetype):
        msg = "Invalid mimetype '%s'" % str(mimetype)

        super(InvalidMimeTypeError, self).__init__(msg)


class NoConfigFoundError(Exception):
    def __init__(self, *args, **kwargs):
        msg = ('No configuration file found. Please define one:\n'
               '\t* config/local.py\n'
               '\t* Set the environment variable $SHIVA_CONFIG pointing to a '
               'config file.\n'
               '\t* $XDG_CONFIG_HOME/shiva/config.py which defaults to \n'
               '\t  $HOME/.config/shiva/config.py')

        super(NoConfigFoundError, self).__init__(msg)

########NEW FILE########
__FILENAME__ = fileserver
# -*- coding: utf-8 -*-
import mimetypes
import os
import re
import sys

from flask import abort, Flask, Response, request, send_file

from shiva.config import Configurator
from shiva.utils import get_logger

app = Flask(__name__)
app.config.from_object(Configurator())

log = get_logger()
RANGE_RE = re.compile(r'(\d+)-(\d*)')


@app.after_request
def after_request(response):
    response.headers['Accept-Ranges'] = 'bytes'

    return response


def get_absolute_path(relative_path):
    for mdir in app.config.get('MEDIA_DIRS', []):
        full_path = os.path.join(mdir.root, relative_path)

        for excluded in mdir.get_excluded_dirs():
            if full_path.startswith(excluded):
                return None

        if os.path.exists(full_path):
            return full_path

    return None


def get_range_bytes(range_header):
    """
    Returns a tuple of the form (start_byte, end_byte) with the information
    provided by range_header. Defaults to (0, None) in case one of the provided
    values is not an int.

    """

    _range = RANGE_RE.search(range_header).groups()
    try:
        start_byte, end_byte = [int(bit) for bit in _range]
    except:
        start_byte = 0
        end_byte = None

    return (start_byte, end_byte)


@app.route('/<path:relative_path>')
def serve(relative_path):
    absolute_path = get_absolute_path(relative_path)
    if not absolute_path:
        abort(404)

    range_header = request.headers.get('Range', None)
    if not range_header:
        return send_file(absolute_path)

    size = os.path.getsize(absolute_path)
    start_byte, end_byte = get_range_bytes(range_header)
    length = (end_byte or size) - start_byte

    content = None
    with open(absolute_path, 'rb') as f:
        f.seek(start_byte)
        content = f.read(length)

    status_code = 206  # Partial Content
    mimetype = mimetypes.guess_type(absolute_path)[0]
    response = Response(content, status_code, mimetype=mimetype,
                        direct_passthrough=True)

    response.headers.add('Content-Range', 'bytes %d-%d/%d' % (
        start_byte, start_byte + length - 1, size))

    return response


def main():
    try:
        port = int(sys.argv[1])
    except:
        port = 8001

    log.warn("""
    +------------------------------------------------------------+
    | This is a *development* server, for testing purposes only. |
    | Do NOT use in a live environment.                          |
    +------------------------------------------------------------+
    """)

    app.run('0.0.0.0', port=port, debug=False)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = http
from flask import current_app as app, Response
from flask.ext import restful

from shiva.decorators import allow_origins


class Resource(restful.Resource):
    def __new__(cls, *args, **kwargs):
        if app.config.get('CORS_ENABLED') is True:
            # Applies to all inherited resources
            cls.method_decorators = [allow_origins]

        return super(Resource, cls).__new__(cls, *args, **kwargs)

    # Without this the shiva.decorator.allow_origins method won't get called
    # when issuing an OPTIONS request.
    def options(self, *args, **kwargs):
        return JSONResponse()


class JSONResponse(Response):
    """
    A subclass of flask.Response that sets the Content-Type header by default
    to "application/json".

    """

    def __init__(self, status=200, **kwargs):
        params = {
            'headers': [],
            'mimetype': 'application/json',
            'response': '',
            'status': status,
        }
        params.update(kwargs)

        super(JSONResponse, self).__init__(**params)

########NEW FILE########
__FILENAME__ = cache
# -*- coding: utf-8 -*-
from sqlalchemy.orm.exc import NoResultFound

from shiva import models as m
from shiva.app import db
from shiva.utils import get_logger

q = db.session.query
log = get_logger()


class CacheManager(object):
    """
    Class that handles object caching and retrieval. The indexer should not
    access DB directly, it should instead ask for the objects to this class.

    """

    def __init__(self, ram_cache=True, use_db=True):
        log.debug('[CACHE] Initilizing...')

        if not ram_cache:
            log.debug('[CACHE] Ignoring RAM cache')
        self.ram_cache = ram_cache
        self.use_db = use_db

        self.artists = {}
        self.albums = {}
        self.hashes = set()

    def get_artist(self, name):
        artist = self.artists.get(name)

        if not artist:
            if self.use_db:
                try:
                    artist = q(m.Artist).filter_by(name=name).one()
                except NoResultFound:
                    pass
                if artist and self.ram_cache:
                    self.add_artist(artist)

        return artist

    def add_artist(self, artist):
        if self.ram_cache:
            self.artists[artist.name] = artist

    def get_album(self, name, artist):
        album = self.albums.get(artist.name, {}).get(name)

        if not album:
            if self.use_db:
                try:
                    album = q(m.Album).filter_by(name=name).one()
                except NoResultFound:
                    pass
                if album and self.ram_cache:
                    self.add_album(album, artist)

        return album

    def add_album(self, album, artist):
        if self.ram_cache:
            if not self.albums.get(artist.name):
                self.albums[artist.name] = {}

            self.albums[artist.name][album.name] = album

    def add_hash(self, hash):
        if self.ram_cache:
            self.hashes.add(hash)

    def hash_exists(self, hash):
        if hash in self.hashes:
            return True

        if self.use_db:
            return bool(q(m.Track).filter_by(hash=hash).count())

        return False

    def clear(self):
        self.artists = {}
        self.albums = {}
        self.hashes = set()

########NEW FILE########
__FILENAME__ = lastfm
# -*- coding: utf-8 -*-
from shiva.utils import ignored, get_logger

log = get_logger()


class LastFM(object):
    def __init__(self, api_key, use_cache=True):
        """
        Wrapper around LastFM's library, pylast. Simplifies handling and adds
        caching.

        Cache's schema:
            self.cache[artist.name]
            self.cache[artist.name]['object']
            self.cache[artist.name]['albums']
            self.cache[artist.name]['albums'][album.name]
        """
        import pylast

        self.pylast = pylast
        self.use_cache = use_cache
        self.lib = self.pylast.LastFMNetwork(api_key=api_key)
        self.cache = {}

    def get_artist(self, name):
        artist = self.cache.get(name, {}).get('object')

        if not artist:
            log.debug('[ Last.FM ] Retrieving artist "%s"' % name)
            with ignored(Exception, print_traceback=True):
                artist = self.lib.get_artist(name)
            if artist and self.use_cache:
                self.cache.update({
                    name: {
                        'object': artist
                    }
                })

        return artist

    def get_artist_image(self, name):
        image = None

        log.debug('[ Last.FM ] Retrieving artist image for "%s"' % name)
        with ignored(Exception, print_traceback=True):
            image = self.get_artist(name).get_cover_image()

        return image

    def get_album(self, name, artist_name):
        album = self.cache.get(artist_name, {}).get('albums', {}).get(name)

        if not album:
            artist = self.get_artist(artist_name)
            log.debug('[ Last.FM ] Retrieving album "%s" by "%s"' % (
                      name, artist.name))
            with ignored(Exception, print_traceback=True):
                album = self.lib.get_album(artist, name)

            if album and self.use_cache:
                self.cache.update({
                    artist.name: {
                        'albums': {
                            album.name: album
                        }
                    }
                })

        return album

    def get_release_date(self, album_name, artist_name):
        rdate = None
        album = self.get_album(album_name, artist_name)

        if not album:
            return None

        log.debug('[ Last.FM ] album "%s" by "%s" release date' % (
                  album_name, artist_name))
        with ignored(Exception, print_traceback=True):
            rdate = album.get_release_date()
            rdate = datetime.strptime(rdate, '%d %b %Y, %H:%M')

        return rdate

    def get_album_cover(self, album_name, artist_name):
        cover = None
        album = self.get_album(album_name, artist_name)

        if not album:
            return None

        log.debug('[ Last.FM ] Retrieving album "%s" by "%s" cover image' % (
                  album_name, artist_name))
        with ignored(Exception, print_traceback=True):
            cover = album.get_cover_image(size=self.pylast.COVER_EXTRA_LARGE)

        return cover

    def clear_cache(self):
        self.cache = {}

########NEW FILE########
__FILENAME__ = main
# -*- coding: utf-8 -*-
"""Music indexer for the Shiva-Server API.
Index your music collection and (optionally) retrieve album covers and artist
pictures from Last.FM.

Usage:
    shiva-indexer [-h] [-v] [-q] [--lastfm] [--hash] [--nometadata] [--reindex]
                  [--write-every=<num>] [--verbose-sql]

Options:
    -h, --help           Show this help message and exit
    --lastfm             Retrieve artist and album covers from Last.FM API.
    --hash               Hash each file to find (and ignore) duplicates.
    --nometadata         Don't read file's metadata when indexing.
    --reindex            Remove all existing data from the database before
                         indexing.
    --write-every=<num>  Write to disk and clear cache every <num> tracks
                         indexed.
    --verbose-sql        Print every SQL statement. Be careful, it's a little
                         too verbose.
    -v --verbose         Show debugging messages about the progress.
    -q --quiet           Suppress warnings.
"""
# K-Pg
from datetime import datetime
from time import time
import logging
import os
import sys
import traceback

from docopt import docopt
from sqlalchemy import func
from sqlalchemy.exc import OperationalError

from shiva import models as m
from shiva.app import app, db
from shiva.exceptions import MetadataManagerReadError
from shiva.indexer.cache import CacheManager
from shiva.indexer.lastfm import LastFM
from shiva.utils import ignored, get_logger

q = db.session.query
log = get_logger()


class Indexer(object):

    VALID_FILE_EXTENSIONS = (
        'asf', 'wma',  # ASF
        'flac',  # FLAC
        'mp4', 'm4a', 'm4b', 'm4p',  # M4A
        'ape',  # Monkey's Audio
        'mp3',  # MP3
        'mpc', 'mp+', 'mpp',  # Musepack
        'spx',  # Ogg Speex
        'ogg', 'oga',  # Ogg Vorbis / Theora
        'tta',  # True Audio
        'wv',  # WavPack
        'ofr',  # OptimFROG
    )

    def __init__(self, config=None, use_lastfm=False, hash_files=False,
                 no_metadata=False, reindex=False, write_every=0):
        self.config = config
        self.use_lastfm = use_lastfm
        self.hash_files = hash_files
        self.no_metadata = no_metadata
        self.reindex = reindex
        self.write_every = write_every
        self.empty_db = reindex

        # If we are going to have only 1 track in cache at any time we might as
        # well just ignore it completely.
        use_cache = (write_every != 1)
        self.cache = CacheManager(ram_cache=use_cache, use_db=not use_cache)

        self.session = db.session
        self.media_dirs = config.get('MEDIA_DIRS', [])
        self.allowed_extensions = app.config.get('ALLOWED_FILE_EXTENSIONS',
                                                 self.VALID_FILE_EXTENSIONS)

        self._ext = None
        self._meta = None
        self.track_count = 0
        self.skipped_tracks = 0
        self.count_by_extension = {}
        for extension in self.allowed_extensions:
            self.count_by_extension[extension] = 0

        if self.use_lastfm:
            self.lastfm = LastFM(api_key=config['LASTFM_API_KEY'],
                                 use_cache=(write_every > 1))

        if not len(self.media_dirs):
            log.error("Remember to set the MEDIA_DIRS option, otherwise I "
                      "don't know where to look for.")

        if reindex:
            log.info('Dropping database...')

            confirmed = raw_input('This will destroy all the information. '
                                  'Proceed? [y/N] ') in ('y', 'Y')
            if not confirmed:
                log.error('Aborting.')
                sys.exit(1)

            db.drop_all()

            log.info('Recreating database...')
            db.create_all()

        # This is useful to know if the DB is empty, and avoid some checks
        if not self.reindex:
            try:
                m.Track.query.limit(1).all()
            except OperationalError:
                self.empty_db = True

    def get_artist(self, name):
        name = name.strip() if type(name) in (str, unicode) else None
        if not name:
            return None

        artist = self.cache.get_artist(name)
        if artist:
            return artist

        artist = m.Artist(name=name, image=self.get_artist_image(name))

        self.session.add(artist)
        self.cache.add_artist(artist)

        return artist

    def get_artist_image(self, name):
        if self.use_lastfm:
            return self.lastfm.get_artist_image(name)

        return None

    def get_album(self, name, artist):
        name = name.strip() if type(name) in (str, unicode) else None
        if not name or not artist:
            return None

        album = self.cache.get_album(name, artist)
        if album:
            return album

        release_year = self.get_release_year(name, artist)
        cover = self.get_album_cover(name, artist)
        album = m.Album(name=name, year=release_year, cover=cover)

        self.session.add(album)
        self.cache.add_album(album, artist)

        return album

    def get_album_cover(self, album, artist):
        if self.use_lastfm:
            return self.lastfm.get_album_cover(album, artist)

        return None

    def get_release_year(self, album, artist):
        if self.use_lastfm:
            rdate = self.lastfm.get_release_date(album, artist)
            return rdate.year if rdate else None

        return self.get_metadata_reader().release_year

    def add_to_session(self, track):
        self.session.add(track)
        ext = self.get_extension()
        self.count_by_extension[ext] += 1

        log.info('[ OK ] %s' % track.path)

        return True

    def skip(self, reason=None, print_traceback=None):
        self.skipped_tracks += 1

        if log.getEffectiveLevel() <= logging.INFO:
            _reason = ' (%s)' % reason if reason else ''
            log.info('[ SKIPPED ] %s%s' % (self.file_path, _reason))
            if print_traceback:
                log.info(traceback.format_exc())

        return True

    def commit(self, force=False):
        if not force:
            if not self.write_every:
                return False

            if self.track_count % self.write_every != 0:
                return False

        log.debug('Writing to database...')
        self.session.commit()

        if self.write_every > 1:
            log.debug('Clearing cache')
            self.cache.clear()
            if self.use_lastfm:
                self.lastfm.clear_cache()

        return True

    def save_track(self):
        """
        Takes a path to a track, reads its metadata and stores everything in
        the database.

        """

        try:
            full_path = self.file_path.decode('utf-8')
        except UnicodeDecodeError:
            self.skip('Unrecognized encoding', print_traceback=True)

            # If file name is in an strange encoding ignore it.
            return False

        try:
            track = m.Track(full_path, no_metadata=self.no_metadata,
                            hash_file=self.hash_files)
        except MetadataManagerReadError:
            self.skip('Corrupted file', print_traceback=True)

            # If the metadata manager can't read the file, it's probably not an
            # actual music file, or it's corrupted. Ignore it.
            return False

        if not self.empty_db:
            if q(m.Track).filter_by(path=full_path).count():
                self.skip()

                return True

        if self.hash_files:
            if self.cache.hash_exists(track.hash):
                self.skip('Duplicated file')

                return True

        if self.no_metadata:
            self.add_to_session(track)

            return True

        meta = self.set_metadata_reader(track)

        artist = self.get_artist(meta.artist)
        album = self.get_album(meta.album, artist)

        if album and artist:
            if artist not in album.artists:
                album.artists.append(artist)

        track.album = album
        track.artist = artist
        self.add_to_session(track)
        self.cache.add_hash(track.hash)

        self.commit()

    def get_metadata_reader(self):
        return self._meta

    def set_metadata_reader(self, track):
        self._meta = track.get_metadata_reader()

        return self._meta

    def get_extension(self):
        return self.file_path.rsplit('.', 1)[1].lower()

    def is_track(self):
        """Try to guess whether the file is a valid track or not."""
        if not os.path.isfile(self.file_path):
            return False

        if '.' not in self.file_path:
            return False

        ext = self.get_extension()
        if ext not in self.VALID_FILE_EXTENSIONS:
            log.debug('[ SKIPPED ] %s (Unrecognized extension)' %
                      self.file_path)

            return False
        elif ext not in self.allowed_extensions:
            log.debug('[ SKIPPED ] %s (Ignored extension)' % self.file_path)

            return False

        return True

    def walk(self, target, exclude=tuple()):
        """Recursively walks through a directory looking for tracks."""

        if not os.path.isdir(target):
            return False

        for root, dirs, files in os.walk(target, exclude):
            for name in files:
                self.file_path = os.path.join(root, name)
                if root in exclude:
                    log.debug('[ EXCLUDED ] %s' % self.file_path)
                else:
                    if self.is_track():
                        self.track_count += 1
                        self.save_track()

    def _make_unique(self, model):
        """
        Retrieves all repeated slugs for a given model and appends the
        instance's primary key to it.

        """

        slugs = q(model).group_by(model.slug).\
            having(func.count(model.slug) > 1)

        for row in slugs:
            slug = row.slug
            for instance in q(model).filter_by(slug=row.slug):
                instance.slug += '-%s' % instance.pk

        return slugs

    # SELECT pk, slug, COUNT(*) FROM tracks GROUP BY slug HAVING COUNT(*) > 1;
    def make_slugs_unique(self):
        query = self._make_unique(m.Artist)
        self.session.add_all(query)

        query = self._make_unique(m.Track)
        self.session.add_all(query)

        self.session.commit()

    def print_stats(self):
        if self.track_count == 0:
            log.info('\nNo track indexed.\n')

            return True

        elapsed_time = self.final_time - self.initial_time
        log.info('\nRun in %d seconds. Avg %.3fs/track.' % (
                 elapsed_time,
                 (elapsed_time / self.track_count)))
        log.info('Found %d tracks. Skipped: %d. Indexed: %d.' % (
                 self.track_count,
                 self.skipped_tracks,
                 (self.track_count - self.skipped_tracks)))
        for extension, count in self.count_by_extension.iteritems():
            if count:
                log.info('%s: %d tracks' % (extension, count))

    def run(self):
        self.initial_time = time()

        for mobject in self.media_dirs:
            for mdir in mobject.get_valid_dirs():
                self.walk(mdir, exclude=mobject.get_excluded_dirs())

        self.final_time = time()


def main():
    arguments = docopt(__doc__)

    if arguments['--quiet']:
        log.setLevel(logging.ERROR)
    elif arguments['--verbose']:
        log.setLevel(logging.DEBUG)
    else:
        log.setLevel(logging.INFO)

    if arguments['--verbose-sql']:
        app.config['SQLALCHEMY_ECHO'] = True

    kwargs = {
        'use_lastfm': arguments['--lastfm'],
        'hash_files': arguments['--hash'],
        'no_metadata': arguments['--nometadata'],
        'reindex': arguments['--reindex'],
        'write_every': arguments['--write-every'],
    }

    if kwargs['no_metadata']:
        kwargs['use_lastfm'] = False

    if kwargs['use_lastfm'] and not app.config.get('LASTFM_API_KEY'):
        sys.stderr.write('ERROR: You need a Last.FM API key if you set the '
                         '--lastfm flag.\n')
        sys.exit(2)

    try:
        if kwargs['write_every'] is not None:
            kwargs['write_every'] = int(kwargs['write_every'])
    except TypeError:
        sys.stderr.write('ERROR: Invalid value for --write-every, expected '
                         '<int>, got "%s" <%s>. instead' % (
            kwargs['write_every'], type(kwargs['write_every'])))
        sys.exit(3)

    # Generate database
    db.create_all()

    lola = Indexer(app.config, **kwargs)
    lola.run()

    lola.print_stats()

    # Petit performance hack: Every track will be added to the session but they
    # will be written down to disk only once, at the end. Unless the
    # --write-every flag is set, then tracks are persisted in batch.
    lola.commit(force=True)

    log.debug('Checking for duplicated tracks...')
    lola.make_slugs_unique()

########NEW FILE########
__FILENAME__ = azlyrics
import re
import urllib2

import requests

from shiva.lyrics import LyricScraper
from shiva.utils import get_logger

log = get_logger()


class AZLyrics(LyricScraper):
    """
    """

    def __init__(self, artist, title):
        self.artist = artist
        self.title = title
        self.lyrics = None
        self.source = None

        self.search_url = 'http://search.azlyrics.com/search.php?q=%s'
        self.lyric_url_re = re.compile(r'http://www\.azlyrics\.com/lyrics/'
                                       r'[a-z0-9]+/[a-z0-9]+\.html')
        self.lyric_re = re.compile(r'<!-- start of lyrics -->(.*)'
                                   r'<!-- end of lyrics -->', re.M + re.S)
        self.title_re = re.compile(r'<title>(?P<artist>.*?) LYRICS - '
                                   r'(?P<title>.*?)</title>')

    def fetch(self):
        self.search()
        if not self.source:
            return None

        response = requests.get(self.source)
        self.html = response.text

        if not self.check():
            return False

        log.info('[FOUND] %s' % self.source)
        lyrics = self.lyric_re.findall(self.html)[0]
        lyrics = re.sub(r'<br[ /]?>', '\r', lyrics)
        lyrics = re.sub(r'<.*?>', '', lyrics)

        self.lyrics = lyrics.strip()

        return True

    def search(self):
        query = urllib2.quote('%s %s' % (self.artist, self.title))
        log.info('[SEARCH] %s' % (self.search_url % query))
        response = requests.get(self.search_url % query)
        results = self.lyric_url_re.findall(response.text)

        if results:
            self.source = results[0]

    def check(self):
        match = self.title_re.search(self.html)

        if match.group('artist').lower() != self.artist.lower():
            return False

        if match.group('title').lower() != self.title.lower():
            return False

        return True

########NEW FILE########
__FILENAME__ = base
from flask import g, current_app as app

from shiva.models import LyricsCache
from shiva.utils import _import


class LyricScraper(object):
    """
    """

    def __init__(self, artist, title):
        self.artist = artist
        self.title = title
        self.lyrics = None
        self.source = None

    def fetch(self):
        raise NotImplementedError


def get_lyrics(track):
    try:
        scrapers = app.config['SCRAPERS']['lyrics']
    except IndexError:
        return None

    for scraper_cls in scrapers:
        Scraper = _import('shiva.lyrics.%s' % scraper_cls)
        if issubclass(Scraper, LyricScraper):
            scraper = Scraper(track.artist.name.encode('utf-8'),
                              track.title.encode('utf-8'))
            if scraper.fetch():
                lyrics = LyricsCache(source=scraper.source, track=track)
                g.db.session.add(lyrics)
                g.db.session.commit()

                return lyrics

    return None

########NEW FILE########
__FILENAME__ = letrascanciones
import re
import urllib2

import requests
import lxml.html
from slugify import slugify

from shiva.lyrics import LyricScraper
from shiva.utils import get_logger

log = get_logger()


class MP3Lyrics(LyricScraper):
    """
    """

    def __init__(self, artist, title):
        self.artist = artist
        self.title = title
        self.lyrics = None
        self.source = None

        self.search_url = 'http://letrascanciones.mp3lyrics.org/Buscar/%s'
        self.lyric_url_re = re.compile(r'href="(/[a-z0-9]{1}/[a-z0-9\-]+'
                                       r'/[a-z0-9\-]+/)"')
        self.lyric_re = re.compile(r'<div id="lyrics_text" .*?>(.*?)'
                                   r'</div>', re.M + re.S)
        self.title_re = re.compile(r'<title>(?P<title>.*?) Letras de '
                                   r'Canciones de (?P<artist>.*?)</title>')

    def fetch(self):
        self.search()
        if not self.source:
            return None

        response = requests.get(self.source)
        self.html = response.text

        if not self.check():
            return False

        log.info('[FOUND] %s' % self.source)
        self.lyric_re.pattern
        lyrics = self.lyric_re.findall(self.html)[0]
        lyrics = re.sub(r'<span id="findmorespan">.*?</span>', '', lyrics)
        lyrics = re.sub(r'<br[ /]?>', '\r', lyrics)
        lyrics = lyrics[lyrics.find('\r\r'):]

        self.lyrics = lyrics.strip()

        return True

    def search(self):
        query = urllib2.quote('%s %s' % (self.artist, self.title))
        log.info('[SEARCH] %s' % (self.search_url % query))
        response = requests.get(self.search_url % query)
        results = self.lyric_url_re.findall(response.text)

        if results:
            self.source = 'http://letrascanciones.mp3lyrics.org%s' % results[0]

    def check(self):
        match = self.title_re.search(self.html)

        if slugify(match.group('artist')) != slugify(self.artist):
            log.info('%s != %s' % (slugify(match.group('artist')),
                                   slugify(self.artist)))
            return False

        if slugify(match.group('title')) != slugify(self.title):
            log.info('%s != %s' % (slugify(match.group('title')),
                                   slugify(self.title)))
            return False

        return True

########NEW FILE########
__FILENAME__ = metrolyrics
import re
import urllib2
import urllib

import lxml.html
import requests
from flask import current_app as app

from shiva.lyrics import LyricScraper
from shiva.utils import get_logger

log = get_logger()


class MetroLyrics(LyricScraper):
    """
    """

    def __init__(self, artist, title):
        self.artist = artist
        self.title = title
        self.search_url = 'http://www.metrolyrics.com/api/v1/search/artistsong'
        self.title_re = re.compile(r'<title>(?P<artist>.*?) - '
                                   r'(?P<title>.*?) LYRICS</title>')

        self.lyrics = None
        self.source = None

    def fetch(self):
        self.search()
        if not self.source:
            return None

        response = requests.get(self.source)
        self.html = response.text
        html = lxml.html.fromstring(self.html)

        if not self.check():
            return False

        log.info('[FOUND] %s' % self.source)
        div = html.get_element_by_id('lyrics-body')
        lyrics = re.sub(r'\n\[ From: .*? \]', '', div.text_content())

        self.lyrics = lyrics.strip()

        return True

    def search(self):
        params = {'artist': self.artist,
                  'song': self.title,
                  'X-API-KEY': app.config['METROLYRICS_API_KEY']}
        _url = '?'.join((self.search_url, urllib.urlencode(params)))
        log.info('[SEARCH] %s' % _url)
        response = requests.get(_url)
        if response.status_code == 200:
            self.source = response.json()['items'][0]['url']

    def check(self):
        match = self.title_re.search(self.html)

        if match.group('artist').lower() != self.artist.lower():
            return False

        if match.group('title').lower() != self.title.lower():
            return False

        return True

########NEW FILE########
__FILENAME__ = media
# -*- coding: utf-8 -*-
import os
import urllib2

from shiva.utils import get_logger

log = get_logger()


class MediaDir(object):
    """This object allows for media configuration. By instantiating a MediaDir
    class you can tell Shiva where to look for the media files and how to serve
    those files. It's possible to configure the system to look for files on a
    directory and serve those files through a different server.

    MediaDir(root='/srv/http', dirs=('/music', '/songs),
             url='http://localhost:8080/')

    Given that configuration Shiva will scan the directories /srv/http/music
    and /srv/http/songs for media files, but they will be served through
    http://localhost:8080/music/ and http://localhost:8080/songs/

    If just a dir is provided Shiva will serve it through the same instance.
    This is *NOT* recommended, but is useful for developing.

    MediaDir('/home/fatmike/music')
    """

    def __init__(self, root='/', dirs=tuple(), exclude=tuple(),
                 url='http://127.0.0.1:8001'):
        """If you provide just 1 argument it will be assumed as a path to
    serve. Like:

    MediaDir('/home/fatmike/music')

    However, you can't just provide the dirs argument, you have to define
    several MediaDirs.

    If the dirs share the same root you can define them both at once:

    MediaDir(root='/srv/http', dirs=('/music', '/songs'))

    If you don't provide a ``url`` parameter, 'http://127.0.0.1:8001' will be
    assumed.
        """

        if type(root) not in (str, unicode):
            raise TypeError("The 'root' attribute has to be a string.")

        # MediaDir('/path/to/dir')
        if not dirs and not url:
            dirs = (root,)
            root = '/'

        # MediaDir('/path/to/dir', dirs='sub/path')
        if type(dirs) != tuple:
            raise TypeError("The 'dirs' attribute has to be a tuple.")

        if type(exclude) not in (tuple, str, unicode):
            raise TypeError("The 'exclude' attribute has to be tuple or " +
                            'string.')
        if type(exclude) in (str, unicode):
            exclude = (exclude,)

        # MediaDir(root='/', url='http://localhost')
        if root == '/' and not dirs and url:
            raise TypeError('Please define at least one directory different ' +
                            "from '/'.")

        if url and type(url) not in (str, unicode):
            raise TypeError('URL has to be a string.')

        if url:
            if not root:
                raise TypeError('You need to supply a root directory for ' +
                                'this url.')

        if type(root) in (str, unicode) and root != '/':
            root = self.root_slashes(root)

        if type(dirs) == tuple:
            dirs = tuple((self.dirs_slashes(d) for d in dirs))

        if type(url) in (str, unicode) and not url.endswith('/'):
            url += '/'

        for d in dirs:
            if d.startswith('/'):
                raise TypeError("The 'dirs' tuple can't contain an absolute " +
                                'path')
            if root.startswith(d):
                raise TypeError("The 'dirs' tuple must be relative to " +
                                "'%s'." % root)

        self.root = root
        self.dirs = dirs
        self.exclude = exclude
        self.excluded_dirs = None
        self.url = url

    def root_slashes(self, path):
        """Removes the trailing slash, and makes sure the path begins with a
        slash.
        """

        path = path.rstrip('/')
        if not path.startswith('/'):
            path = '/%s' % path

        return path

    def dirs_slashes(self, path):
        """Removes the first slash, if exists, and makes sure the path has a
        trailing slash.
        """

        path = path.lstrip('/')
        if not path.endswith('/'):
            path += '/'

        return path

    def get_dirs(self):
        """Returns a list containing directories to look for multimedia files.
        """

        dirs = []

        if self.root:
            if self.dirs:
                for music_dir in self.dirs:
                    dirs.append('/%s' % '/'.join(p.strip('/')
                                for p in (self.root, music_dir)).lstrip('/'))
            else:
                dirs.append(self.root)
        else:
            if self.dirs:
                for music_dir in self.dirs:
                    dirs.append(music_dir)

        return dirs

    def get_excluded_dirs(self):
        if type(self.excluded_dirs) is list:
            return self.excluded_dirs

        self.excluded_dirs = []

        if not len(self.exclude):
            return self.excluded_dirs

        media_dirs = self.dirs if len(self.dirs) else (self.root,)
        for media_dir in media_dirs:
            for _excluded in self.exclude:
                if _excluded.startswith('/'):
                    self.excluded_dirs.append(_excluded)
                else:
                    _path = os.path.join(self.root, media_dir, _excluded)
                    self.excluded_dirs.append(_path)

        return self.excluded_dirs

    def _is_valid_path(self, path):
        """Validates that the given path exists.
        """

        if not os.path.exists(path):
            log.warn("Path '%s' does not exist. Ignoring." % path)
            return False

        return True

    def get_valid_dirs(self):
        """Returns a list containing valid (existing) directories to look for
        multimedia files.

        """

        for path in self.get_dirs():
            if self._is_valid_path(path):
                yield path

    # TODO: Simplify this method and document it better.
    def urlize(self, path):
        """
        """

        url = None
        for mdir in self.get_dirs():
            if path.startswith(mdir):
                if self.url:
                    # Remove trailing slash to avoid double-slashed URL.
                    url = path[len(self.root):]
                    url = str(url.encode('utf-8'))

        if self.url:
            url = ''.join((self.url.rstrip('/'), urllib2.quote(url)))

        return url

    def allowed_to_stream(self, path):
        """
        """

        for mdir in self.get_dirs():
            if path.startswith(mdir):
                return True

        return False


class MimeType(object):
    """Represents a valid mimetype. Holds information like the codecs to be
    used when converting.

    """

    def __init__(self, type, subtype, extension, **kwargs):
        self.type = type
        self.subtype = subtype
        self.extension = extension
        self.acodec = kwargs.get('acodec')
        self.vcodec = kwargs.get('vcodec')

    def is_audio(self):
        return self.type == 'audio'

    def get_audio_codec(self):
        return getattr(self, 'acodec')

    def get_video_codec(self):
        return getattr(self, 'vcodec')

    def matches(self, mimetype):
        return self.__repr__() == unicode(mimetype)

    def __unicode__(self):
        return u'%s/%s' % (self.type, self.subtype)

    def __repr__(self):
        return self.__unicode__()

    def __str__(self):
        return self.__unicode__()


def get_mimetypes():
    from flask import current_app as app

    return app.config.get('MIMETYPES', [])

########NEW FILE########
__FILENAME__ = mocks
from datetime import datetime

from lxml import etree
import requests

from shiva.models import Artist


class ShowModel(object):
    """
    Mock model that encapsulates the show logic for converting a JSON structure
    into an object.

    """

    def __init__(self, artist, json):
        self.json = json
        self.id = json['id']
        self.artists, self.other_artists = self.split_artists(json['artists'])
        self.datetime = self.to_datetime(json['datetime'])
        self.title = json['title']
        self.tickets_left = (json['ticket_status'] == 'available')
        self.venue = json['venue']

    def split_artists(self, json):
        if len(json) == 0:
            ([], [])
        elif len(json) == 1:
            artist = Artist.query.filter_by(name=json[0]['name']).first()

            return ([artist], [])

        my_artists = []
        other_artists = []
        for artist_dict in json:
            artist = Artist.query.filter_by(name=artist_dict['name'])
            if artist.count():
                my_artists.append(artist.first())
            else:
                del artist_dict['thumb_url']
                other_artists.append(artist_dict)

        return (my_artists, other_artists)

    def to_datetime(self, timestamp):
        return datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%S')

    def get_mbid(self, artist):
        mb_uri = 'http://musicbrainz.org/ws/2/artist?query=%(artist)s' % {
            'artist': urllib2.quote(artist)
        }

        logger.info(mb_uri)

        response = requests.get(mb_uri)
        mb_xml = etree.fromstring(response.text)
        # /root/artist-list/artist.id
        artist_list = mb_xml.getchildren()[0].getchildren()
        if artist_list:
            return artist_list[0].get('id')

        return None

    def __getitem__(self, key):
        return getattr(self, key, None)

########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-
from datetime import datetime
import hashlib
import os

from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy.exc import OperationalError
from sqlalchemy.sql.expression import func

from shiva.utils import slugify, MetadataManager

db = SQLAlchemy()

__all__ = ('db', 'Artist', 'Album', 'Track', 'LyricsCache')


def random_row(model):
    """Retrieves a random row for the given model."""

    try:
        # PostgreSQL, SQLite
        instance = model.query.order_by(func.random()).limit(1).first()
    except OperationalError:
        # MySQL
        instance = model.query.order_by(func.rand()).limit(1).first()

    return instance


class Artist(db.Model):
    """
    """

    __tablename__ = 'artists'

    pk = db.Column(db.Integer, primary_key=True)
    # TODO: Update the files' Metadata when changing this info.
    name = db.Column(db.String(128), nullable=False)
    slug = db.Column(db.String(128), nullable=False)
    image = db.Column(db.String(256))
    events = db.Column(db.String(256))
    date_added = db.Column(db.Date(), nullable=False)

    tracks = db.relationship('Track', backref='artist', lazy='dynamic')

    def __init__(self, *args, **kwargs):
        if 'date_added' not in kwargs:
            kwargs['date_added'] = datetime.today()

        super(Artist, self).__init__(*args, **kwargs)

    @classmethod
    def random(cls):
        return random_row(cls)

    def __setattr__(self, attr, value):
        if attr == 'name':
            super(Artist, self).__setattr__('slug', slugify(value))

        super(Artist, self).__setattr__(attr, value)

    def __repr__(self):
        return '<Artist (%s)>' % self.name


artists = db.Table('albumartists',
    db.Column('artist_pk', db.Integer, db.ForeignKey('artists.pk')),
    db.Column('album_pk', db.Integer, db.ForeignKey('albums.pk'))
)


class Album(db.Model):
    """
    """

    __tablename__ = 'albums'

    pk = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    slug = db.Column(db.String(128), nullable=False)
    year = db.Column(db.Integer)
    cover = db.Column(db.String(256))
    date_added = db.Column(db.Date(), nullable=False)

    tracks = db.relationship('Track', backref='album', lazy='dynamic')

    artists = db.relationship('Artist', secondary=artists,
                              backref=db.backref('albums', lazy='dynamic'))

    def __init__(self, *args, **kwargs):
        if 'date_added' not in kwargs:
            kwargs['date_added'] = datetime.today()

        super(Album, self).__init__(*args, **kwargs)

    @classmethod
    def random(cls):
        return random_row(cls)

    def __setattr__(self, attr, value):
        if attr == 'name':
            super(Album, self).__setattr__('slug', slugify(value))

        super(Album, self).__setattr__(attr, value)

    def __repr__(self):
        return '<Album (%s)>' % self.name


class Track(db.Model):
    """Track model."""

    __tablename__ = 'tracks'

    pk = db.Column(db.Integer, primary_key=True)
    path = db.Column(db.Unicode(256), unique=True, nullable=False)
    title = db.Column(db.String(128))
    slug = db.Column(db.String(128))
    bitrate = db.Column(db.Integer)
    file_size = db.Column(db.Integer)
    # TODO could be float if number weren't converted to an int in metadata
    # manager
    length = db.Column(db.Integer)
    # TODO number should probably be renamed to track or track_number
    number = db.Column(db.Integer)
    date_added = db.Column(db.Date(), nullable=False)
    hash = db.Column(db.String(32))

    lyrics = db.relationship('LyricsCache', backref='track', uselist=False)

    album_pk = db.Column(db.Integer, db.ForeignKey('albums.pk'), nullable=True)
    artist_pk = db.Column(db.Integer, db.ForeignKey('artists.pk'),
                          nullable=True)

    def __init__(self, path, *args, **kwargs):
        if not isinstance(path, (basestring, file)):
            raise ValueError('Invalid parameter for Track. Path or File '
                             'expected, got %s' % type(path))

        _path = path
        if isinstance(path, file):
            _path = path.name

        no_metadata = False
        if 'no_metadata' in kwargs:
            no_metadata = kwargs.get('no_metadata', False)
            del(kwargs['no_metadata'])

        hash_file = False
        if 'hash_file' in kwargs:
            hash_file = kwargs.get('hash_file', False)
            del(kwargs['hash_file'])

        self._meta = None
        self.set_path(_path, no_metadata=no_metadata)
        if hash_file:
            self.hash = self.calculate_hash()

        if 'date_added' not in kwargs:
            kwargs['date_added'] = datetime.today()

        super(Track, self).__init__(*args, **kwargs)

    @classmethod
    def random(cls):
        return random_row(cls)

    def __setattr__(self, attr, value):
        if attr == 'title':
            super(Track, self).__setattr__('slug', slugify(value))

        super(Track, self).__setattr__(attr, value)

    def get_path(self):
        if self.path:
            return self.path.encode('utf-8')

        return None

    def set_path(self, path, no_metadata=False):
        if path != self.get_path():
            self.path = path
            if no_metadata:
                return None

            if os.path.exists(self.get_path()):
                meta = self.get_metadata_reader()
                self.file_size = meta.filesize
                self.bitrate = meta.bitrate
                self.length = meta.length
                self.number = meta.track_number
                self.title = meta.title

    def calculate_hash(self):
        md5 = hashlib.md5()
        block_size = 128 * md5.block_size

        with open(self.get_path(), 'rb') as f:
            for chunk in iter(lambda: f.read(block_size), b''):
                md5.update(chunk)

        return md5.hexdigest()

    def get_metadata_reader(self):
        """Return a MetadataManager object."""
        if not getattr(self, '_meta', None):
            self._meta = MetadataManager(self.get_path())

        return self._meta

    def __repr__(self):
        return "<Track ('%s')>" % self.title


class LyricsCache(db.Model):
    """
    """

    __tablename__ = 'lyricscache'

    pk = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text)
    source = db.Column(db.String(256))

    track_pk = db.Column(db.Integer, db.ForeignKey('tracks.pk'),
                         nullable=False)

    def __repr__(self):
        return "<LyricsCache ('%s')>" % self.track.title

########NEW FILE########
__FILENAME__ = base
# -*- coding: utf-8 -*-
from flask import request, current_app as app, g
from flask.ext.restful import abort, fields, marshal
from werkzeug.exceptions import NotFound

from shiva.http import Resource, JSONResponse
from shiva.models import Artist, Album, Track
from shiva.resources.fields import (ForeignKeyField, InstanceURI, TrackFiles,
                                    ManyToManyField)


def full_tree():
    """ Checks the GET parameters to see if a full tree was requested. """

    arg = request.args.get('fulltree')

    return (arg and arg not in ('false', '0'))


def paginate(queryset):
    """
    Function that receives a queryset and paginates it based on the GET
    parameters.

    """

    try:
        page_size = int(request.args.get('page_size', 0))
    except ValueError:
        page_size = 0

    try:
        page_number = int(request.args.get('page', 0))
    except ValueError:
        page_number = 0

    if not page_size or not page_number:
        return queryset

    total = queryset.count()

    limit = page_size
    offset = page_size * (page_number - 1)

    return queryset.limit(limit).offset(offset)


class ArtistResource(Resource):
    """ The resource resposible for artists. """

    def get_resource_fields(self):
        return {
            'id': fields.Integer(attribute='pk'),
            'name': fields.String,
            'slug': fields.String,
            'uri': InstanceURI('artists'),
            'image': fields.String(default=app.config['DEFAULT_ARTIST_IMAGE']),
            'events_uri': fields.String(attribute='events'),
        }

    def get(self, artist_id=None, artist_slug=None):
        if not artist_id and not artist_slug:
            return list(self.get_all())

        if not artist_id and artist_slug:
            artist = self.get_by_slug(artist_slug)
        else:
            artist = self.get_one(artist_id)

        if full_tree():
            return self.get_full_tree(artist)

        return marshal(artist, self.get_resource_fields())

    def get_all(self):
        for artist in paginate(Artist.query.order_by(Artist.name)):
            yield marshal(artist, self.get_resource_fields())

    def get_one(self, artist_id):
        artist = Artist.query.get(artist_id)

        if not artist:
            abort(404)

        return artist

    def get_by_slug(self, artist_slug):
        artist = Artist.query.filter_by(slug=artist_slug).first()

        if not artist:
            abort(404)

        return artist

    def get_full_tree(self, artist):
        _artist = marshal(artist, self.get_resource_fields())
        _artist['albums'] = []

        albums = AlbumResource()

        for album in artist.albums:
            _artist['albums'].append(albums.get_full_tree(album))

        return _artist

    def delete(self, artist_id=None):
        if not artist_id:
            return JSONResponse(405)

        artist = Artist.query.get(artist_id)
        if not artist:
            abort(404)

        g.db.session.delete(artist)
        g.db.session.commit()

        return {}


class AlbumResource(Resource):
    """ The resource resposible for albums. """

    def get_resource_fields(self):
        return {
            'id': fields.Integer(attribute='pk'),
            'name': fields.String,
            'slug': fields.String,
            'year': fields.Integer,
            'uri': InstanceURI('albums'),
            'artists': ManyToManyField(Artist, {
                'id': fields.Integer(attribute='pk'),
                'uri': InstanceURI('artists'),
            }),
            'cover': fields.String(default=app.config['DEFAULT_ALBUM_COVER']),
        }

    def get(self, album_id=None, album_slug=None):
        if not album_id and not album_slug:
            return list(self.get_many())

        if not album_id and album_slug:
            album = self.get_by_slug(album_slug)
        else:
            album = self.get_one(album_id)

        if full_tree():
            return self.get_full_tree(album)

        return marshal(album, self.get_resource_fields())

    def get_many(self):
        artist_pk = request.args.get('artist')
        if artist_pk:
            albums = Album.query.join(Album.artists).filter(
                Artist.pk == artist_pk)
        else:
            albums = Album.query

        queryset = albums.order_by(Album.year, Album.name, Album.pk)
        for album in paginate(queryset):
            yield marshal(album, self.get_resource_fields())

    def get_one(self, album_id):
        album = Album.query.get(album_id)

        if not album:
            abort(404)

        return album

    def get_by_slug(self, album_slug):
        album = Album.query.filter_by(slug=album_slug).first()

        if not album:
            abort(404)

        return album

    def get_full_tree(self, album):
        _album = marshal(album, self.get_resource_fields())
        _album['tracks'] = []

        tracks = TrackResource()

        for track in album.tracks.order_by('number', 'title'):
            _album['tracks'].append(tracks.get_full_tree(track))

        return _album

    def delete(self, album_id=None):
        if not album_id:
            return JSONResponse(405)

        album = Album.query.get(album_id)
        if not album:
            abort(404)

        g.db.session.delete(album)
        g.db.session.commit()

        return {}


class TrackResource(Resource):
    """ The resource resposible for tracks. """

    def get_resource_fields(self):
        return {
            'id': fields.Integer(attribute='pk'),
            'uri': InstanceURI('tracks'),
            'files': TrackFiles,
            'bitrate': fields.Integer,
            'length': fields.Integer,
            'title': fields.String,
            'slug': fields.String,
            'artist': ForeignKeyField(Artist, {
                'id': fields.Integer(attribute='pk'),
                'uri': InstanceURI('artists'),
            }),
            'album': ForeignKeyField(Album, {
                'id': fields.Integer(attribute='pk'),
                'uri': InstanceURI('albums'),
            }),
            'number': fields.Integer,
        }

    def get(self, track_id=None, track_slug=None):
        if not track_id and not track_slug:
            return list(self.get_many())

        if not track_id and track_slug:
            track = self.get_by_slug(track_slug)
        else:
            track = self.get_one(track_id)

        if full_tree():
            return self.get_full_tree(track, include_scraped=True,
                                      include_related=True)

        return marshal(track, self.get_resource_fields())

    # TODO: Pagination
    def get_many(self):
        album_pk = request.args.get('album')
        artist_pk = request.args.get('artist')
        if album_pk:
            album_pk = None if album_pk == 'null' else album_pk
            tracks = Track.query.filter_by(album_pk=album_pk)
        elif artist_pk:
            tracks = Track.query.filter(Track.artist_pk == artist_pk)
        else:
            tracks = Track.query

        queryset = tracks.order_by(Track.album_pk, Track.number, Track.pk)
        for track in paginate(queryset):
            if full_tree():
                yield self.get_full_tree(track, include_related=True)
            else:
                yield marshal(track, self.get_resource_fields())

    def get_one(self, track_id):
        track = Track.query.get(track_id)

        if not track:
            abort(404)

        return track

    def get_by_slug(self, track_slug):
        track = Track.query.filter_by(slug=track_slug).first()

        if not track:
            abort(404)

        return track

    def get_full_tree(self, track, include_scraped=False,
                      include_related=False):
        """
        Retrives the full tree for a track. If the include_related option is
        not set then a normal track structure will be retrieved. If its set
        external resources that need to be scraped, like lyrics, will also be
        included. Also related objects like artist and album will be expanded
        to provide all their respective information.

        This is disabled by default to avois DoS'ing lyrics' websites when
        requesting many tracks at once.

        """

        resource_fields = self.get_resource_fields()
        if include_related:
            artist = ArtistResource()
            resource_fields['artist'] = ForeignKeyField(
                Artist,
                artist.get_resource_fields())
            album = AlbumResource()
            resource_fields['album'] = ForeignKeyField(
                Album,
                album.get_resource_fields())

        _track = marshal(track, resource_fields)

        if include_scraped:
            lyrics = LyricsResource()
            try:
                _track['lyrics'] = lyrics.get_for(track)
            except NotFound:
                _track['lyrics'] = None

        # tabs = TabsResource()
        # _track['tabs'] = tabs.get()

        return _track

    def delete(self, track_id=None):
        if not track_id:
            return JSONResponse(405)

        track = Track.query.get(track_id)
        if not track:
            abort(404)

        g.db.session.delete(track)
        g.db.session.commit()

        return {}

########NEW FILE########
__FILENAME__ = dynamic
# -*- coding: utf-8 -*-
from datetime import datetime
import urllib2
import traceback

from flask import request, current_app as app, g
from flask.ext.restful import abort, fields, marshal
import requests

from shiva.converter import get_converter
from shiva.exceptions import InvalidMimeTypeError
from shiva.http import Resource, JSONResponse
from shiva.lyrics import get_lyrics
from shiva.mocks import ShowModel
from shiva.models import Artist, Album, Track, LyricsCache
from shiva.resources.fields import (Boolean, ForeignKeyField, InstanceURI,
                                    ManyToManyField)
from shiva.utils import get_logger

log = get_logger()


def paginate(queryset):
    """
    Function that receives a queryset and paginates it based on the GET
    parameters.

    """

    try:
        page_size = int(request.args.get('page_size', 0))
    except ValueError:
        page_size = 0

    try:
        page_number = int(request.args.get('page', 0))
    except ValueError:
        page_number = 0

    if not page_size or not page_number:
        return queryset

    total = queryset.count()

    limit = page_size
    offset = page_size * (page_number - 1)

    return queryset.limit(limit).offset(offset)


class LyricsResource(Resource):
    """
    The resource responsible for a track's lyrics. Lyrics are scraped on
    demand, and only the URI where they are found is stored in the database.

    """

    def get_resource_fields(self):
        return {
            'id': fields.Integer(attribute='pk'),
            'uri': InstanceURI('lyrics'),
            'text': fields.String,
            'source_uri': fields.String(attribute='source'),
            'track': ForeignKeyField(Track, {
                'id': fields.Integer(attribute='pk'),
                'uri': InstanceURI('track'),
            }),
        }

    def get(self, track_id=None, track_slug=None):
        if not track_id and not track_slug:
            abort(404)

        if not track_id and track_slug:
            track = Track.query.filter_by(slug=track_slug).first()
        else:
            track = Track.query.get(track_id)

        return self.get_for(track)

    def get_for(self, track):
        if track.lyrics:
            return marshal(track.lyrics, self.get_resource_fields())

        try:
            lyrics = get_lyrics(track)
        except:
            log.debug(traceback.format_exc())
            lyrics = None

        if not lyrics:
            abort(404)

        return marshal(lyrics, self.get_resource_fields())

    def post(self, track_id):
        text = request.form.get('text', None)
        if not text:
            return JSONResponse(400)

        track = Track.query.get(track_id)
        lyric = LyricsCache(track=track, text=text)

        g.db.session.add(lyric)
        g.db.commit()

        return JSONResponse(200)

    def delete(self, track_id):
        track = Track.query.get(track_id)
        g.db.session.delete(track.lyrics)
        g.db.session.commit()

        return JSONResponse(200)


class ConvertResource(Resource):
    """ Resource in charge of converting tracks from one format to another. """

    def get(self, track_id):
        track = Track.query.get(track_id)
        mimetype = request.args.get('mimetype')
        if not track or not mimetype:
            abort(404)

        ConverterClass = get_converter()
        try:
            converter = ConverterClass(track, mimetype=mimetype)
        except InvalidMimeTypeError, e:
            log.error(e)
            abort(400)

        converter.convert()
        uri = converter.get_uri()

        return JSONResponse(status=301, headers={'Location': uri})


class ShowsResource(Resource):
    """
    """

    def get_resource_fields(self):
        return {
            'id': fields.String,
            'artists': ManyToManyField(Artist, {
                'id': fields.Integer(attribute='pk'),
                'uri': InstanceURI('artist'),
            }),
            'other_artists': fields.List(fields.Raw),
            'datetime': fields.DateTime,
            'title': fields.String,
            'tickets_left': Boolean,
            'venue': fields.Nested({
                'latitude': fields.String,
                'longitude': fields.String,
                'name': fields.String,
            }),
        }

    def get(self, artist_id=None, artist_slug=None):
        if not artist_id and not artist_slug:
            abort(404)

        if not artist_id and artist_slug:
            artist = Artist.query.filter_by(slug=artist_slug).first()
        else:
            artist = Artist.query.get(artist_id)

        if not artist:
            abort(404)

        latitude = request.args.get('latitude')
        longitude = request.args.get('longitude')

        country = request.args.get('country')
        city = request.args.get('city')

        if latitude and longitude:
            location = (latitude, longitude)
        elif country and city:
            location = (city, country)
        else:
            location = ()

        response = self.fetch(artist.name, location)

        return list(response) if response else []

    def fetch(self, artist_name, location):
        bit_uri = ('http://api.bandsintown.com/artists/%(artist)s/events'
                   '/search?format=json&app_id=%(app_id)s&api_version=2.0')
        bit_uri = bit_uri % {
            'artist': urllib2.quote(artist_name),
            'app_id': app.config['BANDSINTOWN_APP_ID'],
        }

        _location = urllib2.quote('%s, %s' % location) if location else \
            'use_geoip'

        bit_uri = '&'.join((bit_uri, '='.join(('location', _location))))

        log.info(bit_uri)

        try:
            response = requests.get(bit_uri)
        except requests.exceptions.RequestException:
            return

        for event in response.json():
            yield marshal(ShowModel(artist_name, event),
                          self.get_resource_fields())


class RandomResource(Resource):
    """ Retrieves a random instance of a specified resource. """

    def get(self, resource_name):
        get_resource = getattr(self, 'get_%s' % resource_name)

        if get_resource and callable(get_resource):
            resource_fields = {
                'id': fields.Integer(attribute='pk'),
                'uri': InstanceURI(resource_name),
            }

            return marshal(get_resource(), resource_fields)

        abort(404)

    def get_track(self):
        return Track.random()

    def get_album(self):
        return Album.random()

    def get_artist(self):
        return Artist.random()


class WhatsNewResource(Resource):
    """
    Resource consisting of artists, albums and tracks that were indexed after a
    given date.

    """

    def get(self):
        news = {'artists': [], 'albums': [], 'tracks': []}
        try:
            self.since = datetime.strptime(request.args.get('since'), '%Y%m%d')
        except:
            log.error(traceback.format_exc())
            return news

        news = {
            'artists': self.get_new_for(Artist, 'artist'),
            'albums': self.get_new_for(Album, 'album'),
            'tracks': self.get_new_for(Track, 'track'),
        }

        return news

    def get_new_for(self, model, resource_name):
        """
        Fetches all the instances with ``date_added`` older than
        ``self.since``.

        """

        query = model.query.filter(model.date_added > self.since)
        resource_fields = {
            'id': fields.Integer(attribute='pk'),
            'uri': InstanceURI(resource_name),
        }

        return [marshal(row, resource_fields) for row in query.all()]

########NEW FILE########
__FILENAME__ = fields
# -*- coding: utf-8 -*-
from flask import current_app as app
from flask.ext.restful import fields, marshal

from shiva.converter import get_converter
from shiva.media import get_mimetypes


class InstanceURI(fields.String):
    def __init__(self, base_uri):
        server_uri = app.config.get('SERVER_URI') or ''
        self.base_uri = '/'.join((server_uri, base_uri))

    def output(self, key, obj):
        return '/'.join((self.base_uri, str(obj.pk)))


class TrackFiles(fields.Raw):
    """
    Returns a list of files, one for each available mediatype, for a given
    track.

    """

    def output(self, key, track):
        ConverterClass = get_converter()
        paths = {}

        for mimetype in get_mimetypes():
            converter = ConverterClass(track, mimetype)
            paths[str(mimetype)] = converter.get_uri()

        return paths


class ManyToManyField(fields.Raw):
    def __init__(self, foreign_obj, nested):
        self.foreign_obj = foreign_obj
        self.nested = nested

        super(ManyToManyField, self).__init__()

    def output(self, key, obj):
        items = list()
        for item in getattr(obj, key):
            items.append(marshal(item, self.nested))

        return items


class ForeignKeyField(fields.Raw):
    def __init__(self, foreign_obj, nested):
        self.foreign_obj = foreign_obj
        self.nested = nested

        super(ForeignKeyField, self).__init__()

    def output(self, key, obj):
        _id = getattr(obj, '%s_pk' % key)
        if not _id:
            return None

        obj = self.foreign_obj.query.get(_id)

        return marshal(obj, self.nested)


class Boolean(fields.Raw):
    def output(self, key, obj):
        return bool(super(Boolean, self).output(key, obj))

########NEW FILE########
__FILENAME__ = static
# -*- coding: utf-8 -*-
from shiva import get_version, get_contributors
from shiva.http import Resource, JSONResponse


class ClientResource(Resource):
    """ Resource that lists the known clients for Shiva. """

    def get(self):
        clients = [
            {
                'name': 'Shiva-Client',
                'uri': 'https://github.com/tooxie/shiva-client',
                'authors': [
                    u'Alvaro Mouriño <alvaro@mourino.net>',
                ],
            },
            {
                'name': 'Shiva4J',
                'uri': 'https://github.com/instant-solutions/shiva4j',
                'authors': [
                    u'instant:solutions <office@instant-it.at>'
                ],
            },
            {
                'name': 'Shakti',
                'uri': 'https://github.com/gonz/shakti',
                'authors': [
                    u'Gonzalo Saavedra <gonzalosaavedra@gmail.com>',
                ],
            },
        ]

        return clients


class AboutResource(Resource):
    """ Just some information about Shiva. """

    def get(self):
        info = {
            'name': 'Shiva',
            'version': get_version(),
            'author': u'Alvaro Mouriño <alvaro@mourino.net>',
            'uri': 'https://github.com/tooxie/shiva-server',
            'contributors': get_contributors(),
        }

        return info

########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-
from contextlib import contextmanager
from hashlib import md5
from random import random
import datetime
import logging
import logging.config
import os
import traceback

from slugify import slugify as do_slug
import dateutil.parser
import mutagen

import shiva
from shiva.exceptions import MetadataManagerReadError


def get_shiva_path():
    return os.path.dirname(os.path.abspath(shiva.__file__))


def get_logger():
    logging_conf = os.path.join(get_shiva_path(), 'logging.conf')
    logging.config.fileConfig(logging_conf)

    return logging.getLogger('shiva')


def randstr(length=None):
    """ Generates a random string of the given length. """

    if length < 1:
        return ''

    digest = ''
    while len(digest) < length:
        digest += md5(str(random())).hexdigest()

    if length:
        return digest[:length]

    return digest


def slugify(text):
    """
    Generates an alphanumeric slug. If the resulting slug is numeric-only a
    hyphen and a random string is appended to it.

    """

    if not text:
        return ''

    slug = do_slug(text)
    if not slug:
        slug = randstr(length=6)

    try:
        is_int = isinstance(int(slug), int)
    except ValueError:
        is_int = False

    if is_int:
        slug += u'-%s' % randstr(6)

    return slug


def _import(class_path):
    """ Imports a module or class from a string in dot notation. """

    bits = class_path.split('.')
    mod_name = '.'.join(bits[:-1])
    cls_name = bits[-1]

    mod = __import__(mod_name, None, None, cls_name)

    return getattr(mod, cls_name)


@contextmanager
def ignored(*exceptions, **kwargs):
    """Context manager that ignores all of the specified exceptions. This will
    be in the standard library starting with Python 3.4."""

    log = get_logger()
    try:
        yield
    except exceptions:
        if kwargs.get('print_traceback'):
            log.debug(traceback.format_exc())


class MetadataManager(object):
    """A format-agnostic metadata wrapper around Mutagen.

    This makes reading/writing audio metadata easy across all possible audio
    formats by using properties for the different keys.

    In order to persist changes to the metadata, the ``save()`` method needs to
    be called.

    """

    def __init__(self, filepath):
        self._original_path = filepath
        try:
            self.reader = mutagen.File(filepath, easy=True)
        except Exception, e:
            raise MetadataManagerReadError(e.message)

    @property
    def title(self):
        return self._getter('title')

    @property
    def artist(self):
        """The artist name."""
        return self._getter('artist')

    @artist.setter
    def artist(self, value):
        self.reader['artist'] = value

    @property
    def album(self):
        """The album name."""
        return self._getter('album')

    @album.setter
    def album(self, value):
        self.reader['album'] = value

    @property
    def release_year(self):
        """The album release year."""
        default_date = datetime.datetime(datetime.MINYEAR, 1, 1)
        default_date = default_date.replace(tzinfo=None)
        date = self._getter('date', '')
        try:
            parsed_date = dateutil.parser.parse(date, default=default_date)
        except ValueError:
            return None

        parsed_date = parsed_date.replace(tzinfo=None)
        if parsed_date != default_date:
            return parsed_date.year

        return None

    @release_year.setter
    def release_year(self, value):
        self.reader['year'] = value

    @property
    def track_number(self):
        """The track number."""

        try:
            _number = int(self._getter('tracknumber'))
        except (TypeError, ValueError):
            _number = None

        return _number

    @track_number.setter
    def track_number(self, value):
        self.reader['tracknumber'] = value

    @property
    def genre(self):
        """The music genre."""
        return self._getter('genre')

    @genre.setter
    def genre(self, value):
        self.genre = value

    @property
    def length(self):
        """The length of the song in seconds."""
        return int(round(self.reader.info.length))

    @property
    def bitrate(self):
        """The audio bitrate."""
        if hasattr(self.reader.info, 'bitrate'):
            return self.reader.info.bitrate / 1000

    @property
    def sample_rate(self):
        """The audio sample rate."""
        return self.reader.info.sample_rate

    @property
    def filename(self):
        """The file name of this audio file."""
        return os.path.basename(self.reader.filename)

    @property
    def filepath(self):
        """The absolute path to this audio file."""
        return os.path.abspath(self.reader.filename)

    @property
    def origpath(self):
        """The original path with which this class was instantiated. This
        function avoids a call to ``os.path``.  Usually you'll want to use
        either :meth:`.filename` or :meth:`.filepath` instead."""
        return self._original_path

    @property
    def filesize(self):
        """The size of this audio file in the filesystem."""
        return os.stat(self.reader.filename).st_size

    # Helper functions

    def _getter(self, attr, fallback=None):
        """Return the first list item of the specified attribute or fall back
        to a default value if attribute is not available."""
        return self.reader[attr][0] if attr in self.reader else fallback

    def save(self):
        """Save changes to file metadata."""
        self.reader.save()

########NEW FILE########
__FILENAME__ = indexer-test
# -*- coding: utf-8 -*-
from nose import tools as nose
import unittest

from shiva.app import app, db
from shiva.indexer import Indexer


class IndexerTestCase(unittest.TestCase):

    def setUp(self):
        db.create_all()

    def test_main(self):
        with app.app_context():
            app.config['MEDIA_DIRS'] = []
            lola = Indexer(app.config)
            nose.eq_(lola.run(), None)

    def tearDown(self):
        db.drop_all()

########NEW FILE########
__FILENAME__ = statuscodes-test
# -*- coding: utf-8 -*-
from nose import tools as nose
import os
import tempfile
import unittest

from shiva import app as shiva


class StatusCodesTestCase(unittest.TestCase):

    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp()
        db_uri = 'sqlite:///%s' % self.db_path
        shiva.app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
        shiva.app.config['TESTING'] = True
        shiva.db.create_all()
        self.app = shiva.app.test_client()

    def tearDown(self):
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def test_root(self):
        rv = self.app.get('/')
        nose.eq_(rv.status_code, 404)

    def test_artists(self):
        rv = self.app.get('/artists')
        nose.eq_(rv.status_code, 200)

    def test_artist_404(self):
        rv = self.app.get('/artist/1')
        nose.eq_(rv.status_code, 404)

    def test_albums(self):
        rv = self.app.get('/albums')
        nose.eq_(rv.status_code, 200)

    def test_album_404(self):
        rv = self.app.get('/album/1')
        nose.eq_(rv.status_code, 404)

    def test_tracks(self):
        rv = self.app.get('/tracks')
        nose.eq_(rv.status_code, 200)

    def test_track_404(self):
        rv = self.app.get('/track/1')
        nose.eq_(rv.status_code, 404)

########NEW FILE########
__FILENAME__ = app-test
# -*- coding: utf-8 -*-
from nose import tools as nose
import unittest
from mock import Mock

from shiva import app


class AppTestCase(unittest.TestCase):

    def setUp(self):
        app.app.run = Mock()

    def test_main(self):
        app.main()
        nose.assert_true(app.app.run.called)

########NEW FILE########
__FILENAME__ = cachemanager-test
# -*- coding: utf-8 -*-
try:
    import unittest2 as unittest
except ImportError:
    import unittest

from shiva.indexer.cache import CacheManager


class MockArtist(object):
    """ Mock artist """

    def __init__(self, name):
        self.name = name


class MockAlbum(object):
    """ Mock album """

    def __init__(self, name):
        self.name = name


class CacheManagerTestCase(unittest.TestCase):

    def setUp(self):
        self.cache = CacheManager(use_db=False)

    def test_non_existent_artist(self):
        self.assertIsNone(self.cache.get_artist('NQH'))

    def test_save_artist(self):
        pirexia = MockArtist('Pirexia')
        self.cache.add_artist(pirexia)

        self.assertIs(self.cache.get_artist('Pirexia'), pirexia)

    def test_save_album(self):
        fun_people = MockArtist('Fun People')
        kum_kum = MockAlbum('Kum Kum')

        self.cache.add_album(kum_kum, fun_people)

        self.assertIs(self.cache.get_album('Kum Kum', fun_people),
                      kum_kum)

    def test_clear(self):
        eterna = MockArtist('Eterna Inocencia')
        ei = MockAlbum('EI')

        self.cache.add_artist(eterna)
        self.cache.add_album(ei, eterna)

        self.cache.clear()

        self.assertIsNone(self.cache.get_artist('Eterna Inocencia'))
        self.assertIsNone(self.cache.get_album('EI', eterna))

    def test_no_ram_cache(self):
        cache = CacheManager(ram_cache=False, use_db=False)
        rudos = MockArtist('Rudos Wild')
        cache.add_artist(rudos)

        self.assertIsNone(cache.get_artist('Rudos Wild'))

########NEW FILE########
__FILENAME__ = config-test
# -*- coding: utf-8 -*-
from mock import Mock
from nose import tools as nose
import unittest

from shiva.config import Configurator
from shiva import exceptions as exc


class ConfigTestCase(unittest.TestCase):

    def test_no_config(self):
        Configurator.from_xdg_config = Mock(return_value=False)
        Configurator.from_env = Mock(return_value=False)
        Configurator.from_local = Mock(return_value=False)

        nose.assert_raises(exc.NoConfigFoundError, Configurator)

########NEW FILE########
__FILENAME__ = exceptions-test
# -*- coding: utf-8 -*-
from nose import tools as nose
import unittest

from shiva import exceptions as exc


class ExceptionsTestCase(unittest.TestCase):

    def test_invalid_mimetype_error(self):
        error = exc.InvalidMimeTypeError('audio/mp3')
        nose.eq_(error.__str__(), "Invalid mimetype 'audio/mp3'")

    def test_no_config_found_error(self):
        error = exc.NoConfigFoundError()
        nose.assert_not_equal(error.__str__(), '')

########NEW FILE########
__FILENAME__ = http-test
# -*- coding: utf-8 -*-
from nose import tools as nose
import unittest

from shiva import http
from shiva.app import app


class HTTPTestCase(unittest.TestCase):

    def test_options_method_returns_json_response(self):
        with app.app_context():
            resource = http.Resource()
            nose.assert_true(isinstance(resource.options(), http.JSONResponse))

########NEW FILE########
__FILENAME__ = indexer-test
# -*- coding: utf-8 -*-
from mock import Mock
try:
    import unittest2 as unittest
except ImportError:
    import unittest
import os

from shiva.indexer.main import Indexer


class IndexerTestCase(unittest.TestCase):

    def setUp(self):
        self.config = {
            'MEDIA_DIRS': [],
            'VALID_FILE_EXTENSIONS': ('mp3',),
        }
        self.indexer = Indexer(self.config)

        os.path.isfile = Mock()

    def test_track_detection(self):
        self.indexer.file_path = 'valid_track.mp3'

        self.assertTrue(self.indexer.is_track())

    def test_extension_detection(self):
        self.indexer.file_path = 'valid_track.mp3'

        self.assertEqual(self.indexer.get_extension(), 'mp3')

    def test_runs(self):
        self.assertIsNone(self.indexer.run())

########NEW FILE########
__FILENAME__ = lastfm-test
# -*- coding: utf-8 -*-
try:
    import unittest2 as unittest
except ImportError:
    import unittest
from mock import Mock, patch

from shiva.indexer.lastfm import LastFM


class LastFMTestCase(unittest.TestCase):

    def setUp(self):
        import sys
        sys.modules["pylast"] = Mock()

        api_key = 'FAKE_API_KEY'
        self.lastfm = LastFM(api_key)

    def test_caches_artists(self):
        artist = self.lastfm.get_artist('Artist')

        self.assertEqual(self.lastfm.get_artist('Artist'), artist)
        self.assertEqual(self.lastfm.cache, {
            'Artist': {
                'object': artist
            }
        })

    def test_clear_cache(self):
        self.lastfm.get_artist('Artist')
        _cache = self.lastfm.cache
        self.lastfm.clear_cache()

        self.assertNotEqual(self.lastfm.cache, _cache)

    def test_caches_albums(self):
        artist = self.lastfm.get_artist('Artist')
        artist.name = 'Artist'

        album = self.lastfm.get_album('Album name', 'Artist')
        album.name = 'Album name'

        self.assertEqual(self.lastfm.get_album('Album name', 'Artist'), album)
        self.assertEqual(self.lastfm.cache, {
            'Artist': {
                'albums': {
                    'Album name': album
                }
            }
        })

########NEW FILE########
__FILENAME__ = metadata-test
# -*- coding: utf-8 -*-
from nose import tools as nose
import unittest

import shiva


class MetaDataTestCase(unittest.TestCase):

    def test_version(self):
        nose.eq_(shiva.get_version(), shiva.__version__)

    def test_contributors(self):
        nose.eq_(shiva.get_contributors(), shiva.__contributors__)

########NEW FILE########
__FILENAME__ = restideas
# -*- coding: utf-8 -*-
"""
cat /dev/brain
==============

Just a series of thoughts about how the Flask-Restless' API could be modified
to allow for the creation of non db-backed resources. None of this has been
through any serious thought about fesibility, they are just random ideas.
"""
from flask import Flask
from flask.ext.restless import APIManager, Resource
from flapi.models import session, Audio

app = Flask(__name__)


class SongResource(Resource):
    """
    This approach is based on
    https://code.google.com/p/django-rest-interface/wiki/RestifyDjango
    and
    http://django-tastypie.readthedocs.org/en/latest/resources.html
    """

    def create(self):
        pass

    def read(self, id=None, ids_only=False, nesting_levels=1):
        """
        The ids_only parameter would force the method to return only the IDs of
        the matching element. Useful for nesting.

        Not sure about the nesting_levels.
        """

        pass

    def update(self, *args, **kwargs):
        pass

    def delete(self, id):
        pass

    def patch(self):
        pass

    def head(self):
        pass

    def options(self):
        pass

    def connect(self):
        raise NotImplementedError

    def trace(self):
        raise NotImplementedError

    def validator(self, data):
        """
        Validates the data sent by the client. Run always before every method.
        Maybe could be turn into a decorator (like before_request)
        """

        pass

    def authorize(self):
        pass

    def get_format(self):
        """
        /api/songs.json
        /api/songs?format=json
        Accept: application/json
        """

        raise NotImplementedError


# --


class SongResource(Resource):
    """
    A less django-ish approach.
    """

    # A more SQLAlchemy-ish approach.
    __basemodel__ = Audio
    __resource__ = '/songs/'

    # This method decorator should be defined once and only once per Verb. It
    # would tell the Resource how to read/write. Me gusta.
    @method('GET')
    def get_all_or_one(self, id=None):
        pass

    @method(['POST', 'PUT', 'PATCH'])
    def write(self, data):
        pass

    def authorize(self):
        pass

    def get_format(self):
        pass


# --


# Registering the Route. For both previous examples.
# Maybe decorate the class? /me not likes
@app.route('/songs/')
class SongResource(Resource):
    pass


# Use the add_url_rule decorator.
app.add_url_rule('/songs/', 'songs', SongResource)

# Downside: Duplication.
app.add_url_rule('/songs/<int:song_id>', 'song', SongResource)

# Possible solution, delegate to the Resource?
SongResource.create_rules(app)

# Or do it in batch.
api = APIManager(app, session=session)
api.resources([SongResource, ArtistResouce, SomeOtherResource])
api.create_rules(app)  # Explicit is better than implicit


# --


# This is a more flasky approach. Simple, extensible.
# ME GUSTA
api = APIManager(app, session=session)

@api.resource('/songs')
def songs(song_id=None):
    pass

# Note that the decorator now is the previous function.
@songs.method('PUT')
def save_song(data):
    pass

@songs.authorize
def check_permissions():
    pass

# This method should rarely be ovewritten.
@songs.get_format
def get_format():
    pass

# (...)

# The problem I see with this is how to build a resource from existing models
# using this approach. Doesn't look very straightforward at first.
# Maybe...
api.resource(Audio, methods=['GET', 'POST', 'DELETE'])


# --


# Traversal
# =========

# As seen on:
# http://docs.pylonsproject.org/projects/pyramid/en/latest/narr/traversal.html
# and
# http://docs.pylonsproject.org/projects/pyramid/en/latest/narr/resources.html


class RootResource(object):
    """
    """

    __name__ = ''
    __parent__ = None


class SongResource(object):
    """
    """

    def __resource_url__(self):
        from flask import request

        return request.base_url

from flask.ext.restless import inside, lineage, find_root


class Thing(object):
    pass

a = Thing()
b = Thing()
b.__parent__ = a

inside(b, a)  # >>> True
inside(a, b)  # >>> False

list(lineage(b))
# >>> [ <Thing object at b>, <Thing object at a>]

find_root(b)
# >>> a


# --


# The present way:
manager = APIManager(app, session=session)
# Not a big fan of the 'create_api' method name.
manager.create_api(Audio, methods=['GET', 'POST', 'DELETE'])


# --


"""
Unsolved issues
---------------

* Define nested resources.
    * Serializers?
* Permissions for nested resources.
* Depth of nested resources.
* Definition of formats to retrieve.
* Multiple API versions.

Ideas:
* https://github.com/tryolabs/django-tastypie-extendedmodelresource#readme
* http://django-rest-framework.org/tutorial/1-serialization.html
* http://django-rest-framework.org/api-guide/serializers.html
* https://github.com/ametaireau/flask-rest/

"""

# :wq

########NEW FILE########
