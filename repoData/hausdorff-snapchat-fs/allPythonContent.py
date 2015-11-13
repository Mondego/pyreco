__FILENAME__ = api
#!/usr/bin/env python

"""
api.py provides an opaque entry point to the Snapchat API. It backs all
the requests we will issue to the Snapchat service.
"""

import hashlib, requests, time
from Crypto.Cipher import AES
import constants
from friend import Friend
from snaps import Snap, SentSnap, ReceivedSnap

__author__ = "Alex Clemmer, Chad Brubaker"
__copyright__ = "Copyright 2013, Alex Clemmer and Chad Brubaker"
__credits__ = ["Alex Clemmer", "Chad Brubaker"]

__license__ = "MIT"
__version__ = "0.1"
__maintainer__ = "Alex Clemmer"
__email__ = "clemmer.alexander@gmail.com"
__status__ = "Prototype"

# CONSTANTS; encodes strings used in the request headers by the Snapchat
# API. If they change, we only need to update these variables.
AUTH_TOKEN             = 'auth_token'
CAN_SEE_CUSTOM_STORIES = 'can_see_custom_stories'
CLIENT_ID              = 'id'
COUNTRY_CODE           = 'country_code'
DISPLAY                = 'display'
FRIENDS                = 'friends'
MEDIA_ID               = 'media_id'
NAME                   = 'name'
PASSWORD               = 'password'
RECIPIENT              = 'recipient'
REQ_TOKEN              = 'req_token'
SNAPS                  = 'snaps'
TIME                   = 'time'
TIMESTAMP              = 'timestamp'
TYPE                   = 'type'
USERNAME               = 'username'


class SnapchatSession():
    """
    Interacts with Snapchat API as a session. That is, you:
      (1) initialize the object with a username and password, which will
          result in a session being opened for you, and
      (2) issue different types of requests (send, upload, retry, etc.)
          using the corresponding methods.
    """

    def __init__(self, username, password):
        self.username = username  # string
        self.password = password  # string
        self.session_token = None # string
        self.snaps = None         # [Snap()]

    #
    # PUBLIC FACING API METHODS
    #
    def login(self):
        """
        Generates and executes the login request, populate session with
        state like number of friends, etc.
        """
        # wipe session state from previous sessions
        self.session_token = None

        # create parameters for current request, and issue request
        timestamp = SnapchatSession._generate_timestamp()
        req_params = {
              USERNAME  : self.username
            , PASSWORD  : self.password
            , TIMESTAMP : timestamp
            , REQ_TOKEN : SnapchatSession._generate_req_token(
                constants.LOGIN_TOKEN, timestamp)
        }

        result = SnapchatSession._post_or_fail(constants.LOGIN_RESOURCE
                                    , req_params).json()

        # make sure login was successful
        if result['logged'] == False:
            raise Exception("Login failed, invalid credentials")

        # update session state with login response information
        self.session_token = result[AUTH_TOKEN]
        self.login_data = result
        self._update_session_state(result)

    def upload_image(self, image_data, media_id):
        """
        Uploads an image to Snapchat.
        @image_data Image data to upload
        @media_id The ID to give the image we upload.
        """
        # generate request parameters
        encrypted_data = SnapchatSession._snapchat_basic_encrypt(
            image_data)
        timestamp = SnapchatSession._generate_timestamp()
        req_params = {
              USERNAME  : self.username
            , TIMESTAMP : timestamp
            , MEDIA_ID  : media_id
            , TYPE      : Snap.Type.IMAGE
            , REQ_TOKEN : SnapchatSession._generate_req_token(
                self.session_token, timestamp)
        }
        files = {'data' : ('file', encrypted_data)}

        # dispatch request
        result = SnapchatSession._post_or_fail(constants.UPLOAD_RESOURCE
                                               , req_params, files)

    def send_image_to(self, recipient, media_id, time = 10
                      , country_code = "US"):
        """
        Instructs Snapchat to send data to a user. Note that data must be
        uploaded to Snapchat before calling send_to.
        @recipient The username to send the snap to.
        @media_id The ID of the image to send.
        @time
        @country_code
        """
        #generate request parameters
        timestamp = SnapchatSession._generate_timestamp()
        params = {
              USERNAME     : self.username
            , TIMESTAMP    : timestamp
            , MEDIA_ID     : media_id
            , TYPE         : Snap.Type.IMAGE
            , COUNTRY_CODE : country_code
            , RECIPIENT    : recipient
            , TIME         : time
            , REQ_TOKEN    : SnapchatSession._generate_req_token(
                self.session_token, timestamp)
        }

        # dispatch request
        result = SnapchatSession._post_or_fail(constants.SEND_RESOURCE
                                               , params)

    def get_snaps(self, filter_func=lambda snap: True):
        """
        Returns array of Snaps sent to current user, represented as a list
        of Snap objects.
        @filter_func Filter function for snaps; takes a Snap object as
            input, returns `False` if we are to filter the Snap from our
            collection.
        """
        return filter(filter_func, self.snaps)

    def blob(self, client_id):
        timestamp = SnapchatSession._generate_timestamp()
        params = {
              USERNAME  : self.username
            , TIMESTAMP : timestamp
            , CLIENT_ID : client_id
            , REQ_TOKEN : SnapchatSession._generate_req_token(
                self.session_token, timestamp)
        }

        result = SnapchatSession._post_or_fail(constants.BLOB_RESOURCE
                                               , params).content
        
        if result[:3] == '\x00\x00\x00' \
           and results[5:12] == '\x66\x74\x79\x70\x33\x67\x70\x35':
            return result
        elif result[:3] == '\xFF\xD8\xFF':
            return result

        # otherwise encrypted, decrypt it.
        crypt = AES.new(constants.SECRET_KEY, AES.MODE_ECB)
        result = bytes(crypt.decrypt(result))
        # remove padding
        result = result[:-ord(result[-1])]
        return result


    #
    # PRIVATE UTILITY METHODS
    #
    @staticmethod
    def _snapchat_basic_encrypt(data):
        """
        Basic encryption technique used by Snapchat. It's ECB mode, which
        is a mode that should pretty much never be used, but we didn't
        pick it.
        @data The data to encrypt.
        """
        length = 16 - (len(data) % 16)
        data += chr(length) * length
        crypt = AES.new(constants.SECRET_KEY, AES.MODE_ECB)
        return crypt.encrypt(data)

    @staticmethod
    def _generate_req_token(server_token, timestamp):
        """
        Generates request token used by Snapchat's servers to "verify"
        that we don't have unauthorized access to their API.

        This consists of: generating two hashes, then zipping up the
        hashes from a pre-defined pattern.
        @server_token String representing session token given at login.
        @timestamp String representing timestamp of this request.
        """
        sha = hashlib.sha256()
        sha.update(constants.SALT + server_token)
        hash0 = sha.hexdigest()
        sha = hashlib.sha256()
        sha.update(timestamp + constants.SALT)
        hash1 = sha.hexdigest()

        output = [hash0[i] if constants.PATTERN[i] == '0' else hash1[i]
              for i in range(len(hash0))]
        
        return ''.join(output)

    @staticmethod
    def _generate_timestamp():
        """
        Generates string timestamp in the format used by Snapchat's API.
        """
        return str(int(time.time() * 100))

    @staticmethod
    def _post_or_fail(resource, request_params, files=None):
        """
        Issues a post request to the Snapchat API and fails if not 200 OK.
        @resource The resource to append to the URL root, e.g., /bq/login.
        @request_params Dictionary containing requests parameters, like
            username and password.
        @files A dict containing data from a file that we're adding to
            the POST request. Formatted like: {'data': ('file', data)}
        """
        uri = "%s%s" % (constants.ROOT_URL, resource)
        result = requests.post(uri, request_params, files = files)
        if result.status_code != 200:
            raise Exception("POST request failed with status code %d" %
                            (result.status_code))
        return result

    def _update_friends_list(self, json_update):
        """
        Updates the friends list using a dict representing the JSON object
        that was returned by the Snapchat API.
        @json_update Dictionary representing the JSON update returned by
            the Snapchat API.
        """
        friends = [Friend(friend[NAME], friend[DISPLAY], friend[TYPE]
                    , friend[CAN_SEE_CUSTOM_STORIES])
                   for friend in json_update[FRIENDS]]
        self.friends = friends

    def _update_session_state(self, json_update):
        """
        Updates the session's friends and snaps lists using a dict
        representing the JSON object that was returned by the Snapchat
        API.
        @json_update Dictionary representing the JSON update returned by
            the Snapchat API.
        """
        self._update_friends_list(json_update)
        self._update_snaps_list(json_update)

    def _update_snaps_list(self, json_update):
        """
        Updates the session's snaps list using a dict representing the
        JSON object that was returned by the Snapchat API.
        @json_update Dictionary representing the JSON update returned by
            the Snapchat API.
        """
        def _build_appropriate_snap_obj(snap):
            if snap.has_key('rp'):
                return SentSnap.from_json(self, snap)
            elif snap.has_key('sn'):
                return ReceivedSnap.from_json(self, snap)
            else:
                raise Exception("Unknown snap, no sender or receiver")            
        self.snaps = [_build_appropriate_snap_obj(snap)
                      for snap in json_update[SNAPS]]


class SfsSession(SnapchatSession):
    @staticmethod
    def generate_sfs_id(basename, file_data):
        """
        Produces an ID for a file stored in Snapchat FS. ID consists of a
        prefix, the
        filename, and a unique identifier based on file data.
        @filename Name of the file as it exists on the filesystem.
        @file_data The data inside the file.
        """
        sha = hashlib.sha256()
        sha.update(file_data)
        content_id = sha.hexdigest()
        return "snapchatfs-%s-%s" % (basename, content_id)

    @staticmethod
    def is_sfs_id(id):
        """
        Returns True if `id` is a valid Snapchat FS file identifier.
        @id The identifier to test.
        """
        return id.startswith('snapchatfs-')

    def parse_sfs_id(self, id):
        """
        Parses an identifier for a file in Snapchat FS. Returns the
        filename and a hash of
        the contents of the file.
        @id The Snapchat FS identifier to parse.
        """
        assert(SfsSession.is_sfs_id(id))
        # valid ids are of the form
        # """snapchat-[filename]-[hash of content][username]"""
        prefix = id[:11]                     # 'snapchat-'
        filename = id[11:-76]                # filename
        content_id = id[-75:-len(self.username)]  # hash of content
        return filename, content_id


########NEW FILE########
__FILENAME__ = constants
import os

VERSION = 'Snapchat FS 0.1'
CONFIG_FILE_PATH = os.getenv("HOME") + '/.snapchat_fs'

ROOT_URL = "https://feelinsonice-hrd.appspot.com"
# appened to the ROOT_URL to get the login resource
LOGIN_RESOURCE = "/bq/login"
SEND_RESOURCE = "/bq/send"
UPLOAD_RESOURCE = "/bq/upload"
BLOB_RESOURCE = "/bq/blob"

# we pass this token to the service to "authenticate" that we're supposed
# to be able to log in
LOGIN_TOKEN = "m198sOkJEn37DjqZ32lpRu76xmw288xSQ9"

# secret key hardcoded into app; is used for things like encrypting the images
SECRET_KEY = "M02cnQ51Ji97vwT4"
# the secret salt they use for the hashes they use to generate req tokens
SALT = "iEk21fuwZApXlz93750dmW22pw389dPwOk"
# used to generate all request tokens
PATTERN = "0001110111101110001111010101111011010001001110011000110001000110"

########NEW FILE########
__FILENAME__ = friend
class Friend():
    class State():
        FRIEND = 0
        PENDING = 1
        BLOCKED = 2
        DELETED = 3
    def __init__(self, name, display, type, can_see_custom_stories):
        self.name = name
        self.display = display
        self.type = type
        self.can_see_custom_stories = can_see_custom_stories
    def __repr__(self):
        return "%s(%r)" % (self.__class__, self.__dict__)

########NEW FILE########
__FILENAME__ = snaps
#!/usr/bin/env python

"""
snaps.py provides Python objects that represent Snaps of various forms --
received, sent, and so on. Methods in these classes encapsulate actions
that are useful to perform on snaps.
"""

import time
from Crypto.Cipher import AES
import constants

__author__ = "Alex Clemmer, Chad Brubaker"
__copyright__ = "Copyright 2013, Alex Clemmer and Chad Brubaker"
__credits__ = ["Alex Clemmer", "Chad Brubaker"]

__license__ = "MIT"
__version__ = "0.1"
__maintainer__ = "Alex Clemmer"
__email__ = "clemmer.alexander@gmail.com"
__status__ = "Prototype"


class Caption():
    def __init__(self, text, location, orientation):
        self.text = text
        self.location = location
        self.orientation = orientation

    @staticmethod
    def from_json(snap):
        if not snap.has_key('cap_text'):
            return None
        return Caption(snap['cap_text'],
                       snap['cap_pos'],
                       snap['cap_ori'])
class Snap():
    class Type():
        """
        The media type of Snap
        """
        IMAGE = 0
        VIDEO = 1
        VIDEO_NO_AUDIO = 2
        FRIEND_REQ = 3
        FRIEND_REQ_IMAGE = 4
        FRIEND_REQ_VIDEO = 5
        FRIEND_REQ_VIDEO_NO_AUDIO = 6

    class State():
        """
        The state of the Snap.

        Snaps that are viewed are (claimed to be) deleted from the server
        """
        SENT = 0
        DELIVERED = 1
        VIEWED = 2
        SCREENSHOT = 3


    @property
    def viewable(self):
        return self.state == Snap.State.DELIVERED and self.type != Snap.Type.FRIEND_REQ

    def download(self, when = None, skip_decrypt = False):
        """
        Download a snap from the server.
        """
        if not self.viewable:
            raise Exception("Snap not viewable, cannot download")

        return self.connection.blob(self.id)

    def __repr__(self):
        return "%s(%r)" % (self.__class__, self.__dict__)

class SentSnap(Snap):

    def __init__(self, connection, id, client_id, recipient, type, state, timestamp, send_timestamp,\
                 view_time = 0, screenshots = 0, caption = None):
        self.connection = connection
        self.id = id
        self.client_id = client_id
        self.recipient = recipient
        self.user = recipient
        self.type = type
        self.state = state
        self.timestamp = timestamp
        self.send_timestamp = timestamp
        self.screenshots = screenshots
        self.caption = caption

    @staticmethod
    def from_json(conn, snap):
        return SentSnap(conn,
                        snap['id'],
                        snap['c_id'],
                        snap['rp'],
                        snap['m'],
                        snap['st'],
                        snap['ts'],
                        snap['sts'],
                        snap.get('t',0),
                        snap.get('ss', 0),
                        Caption.from_json(snap))
    @property
    def viewable(self):
        return False

class ReceivedSnap(Snap):

    def __init__(self, connection, id, sender, type, state, timestamp, send_timestamp,\
            view_time = 0, screenshots = 0, caption = None):
        self.connection = connection
        self.id = id
        self.sender = sender
        self.user = sender
        self.type = type
        self.state = state
        self.timestamp = timestamp
        self.send_timestamp = timestamp
        self.screenshots = screenshots
        self.caption = caption

    @staticmethod
    def from_json(conn, snap):
        return ReceivedSnap(conn,
                        snap['id'],
                        snap['sn'],
                        snap['m'],
                        snap['st'],
                        snap['ts'],
                        snap['sts'],
                        snap.get('t',0),
                        snap.get('ss', 0),
                        Caption.from_json(snap))

########NEW FILE########
__FILENAME__ = snapchatfs
#!/usr/bin/env python

"""
snapchatfs.py provides a clean CLI for uploading, storing, managing, and
downloading arbitrary data files from Snapchat.
"""

from __future__ import absolute_import
import hashlib, os
import snapchat_fs.util as util
from snapchat_core import *

__author__ = "Alex Clemmer, Chad Brubaker"
__copyright__ = "Copyright 2013, Alex Clemmer and Chad Brubaker"
__credits__ = ["Alex Clemmer", "Chad Brubaker"]

__license__ = "MIT"
__version__ = "0.1"
__maintainer__ = "Alex Clemmer"
__email__ = "clemmer.alexander@gmail.com"
__status__ = "Prototype"


def sent_id_to_received_id(id):
    """
    Transforms a sent_id to a received_id.
    
    Sent IDs have an 's' at the end, while received IDs have an 'r' on the
    end. This method strips 's' off and replaces it with an 'r'.

    @id Id to transform.
    @return Transformed id.
    """
    return id[:-1] + 'r'

def download_all_sfs(session, target_dir):
    """
    Downloads all files managed by Snapchat FS, writing them to `target_dir`
    
    @session An SfsSession object that has been logged in.
    @target_dir Where to download the files to.
    """
    files = all_downloadable_sfs_files(session)
    download_from_sfs(target_dir, files)

def download_by_id(session, target_dir, snap_ids):
    """
    Downloads files managed by Snapchat FS with specified ids,
    writing them to `target_dir`
    
    @session An SfsSession object that has been logged in.
    @target_dir Where to download the files to.
    @snap_ids The ids of the snaps to download
    """
    def should_download_file(f):
        (_, _, _, snap) = f
        return snap.id in snap_ids

    # get all downloadable files tracked by Snapchat FS
    available_files = all_downloadable_sfs_files(session)
    files_to_download = filter(should_download_file, available_files)
    download_from_sfs(target_dir, files_to_download)

def download_from_sfs(target_dir, files):
    """
    Downloads snaps given a list of Snap objects, writing them to `target_dir`

    @target_dir Where to download the files to.
    @files The list of (filename, content_hash, recv_id, snap) tuples to download
    """

    # download each file in sequence; if we find two files with the same
    # name, we give the file a name that includes a hash of the contents
    filenames_downloaded = set()
    for filename, content_hash, received_id, snap in files:
        try:
            data = snap.download()
            if filename not in filenames_downloaded:
                print(util.green("Downloading snap ") + filename)
                path = os.path.join(target_dir, filename)
            else:
                print(util.green("Downloading snap ") + filename +
                      (util.red("but filename is not unique; ") +
                       ("downloading as: %s" %
                        (filename + "-" + content_hash))))
                path = os.path.join(target_dir
                                    , filename + "-" + content_hash)

            filenames_downloaded.add(filename)
            with open(os.path.join(target_dir, filename+content_hash)
                      , 'w') as w:
                w.write(data)

        except Exception as e:
            print("Failed to download %s: %s" % (filename, e))
            raise

def all_downloadable_sfs_files(session):
    """
    Gets all files managed in Snapchat FS for a specific user; returns
    them as a list of Snap objects, whose IDs can be used to download
    all or some of the files from Snapchat's DB.
    
    @session An SfsSession object that has been logged in.
    @return List of Snap objects representing the files.
    """

    # get list of downloadable ids
    downloadable_snaps = session.get_snaps(lambda snap: snap.viewable)
    downloadable_snaps_dict = {snap.id: snap
                              for snap in downloadable_snaps}

    # get list of snaps sent
    snaps_sent = session.get_snaps(lambda snap: isinstance(snap, SentSnap)
                                   and SfsSession.is_sfs_id(snap.client_id))

    # for deduping -- a file is a duplicate if its content and its name
    # are the same
    filenames_seen_so_far = set()
    content_seen_so_far = set()

    # grab all "unique" files stored in Snapchat FS
    sfs_files = []
    for snap in snaps_sent:
        filename, content_hash = session.parse_sfs_id(snap.client_id)
        received_id = sent_id_to_received_id(snap.id)

        if (filename in filenames_seen_so_far) \
           and (content_hash in content_seen_so_far):
            continue
        elif received_id in downloadable_snaps_dict:
            filenames_seen_so_far.add(filename)
            content_seen_so_far.add(content_hash)
            downloadable_snap = downloadable_snaps_dict[received_id]
            sfs_files.append((filename, content_hash, received_id
                              , downloadable_snap))

    return sfs_files

def list_all_downloadable_sfs_files(session):
    """
    Produces a list of Snap objects representing all downloadable files
    managed by Snapchat FS for a particular user.
    
    @session An SfsSession object that has been logged in.
    @return List of Snap objects representing all downloadable files in SFS.
    """
    files = all_downloadable_sfs_files(session)

    print '\t'.join([util.bold('Filename'), util.bold('Content hash'), util.bold('Snap ID')])
    for filename, content_hash, received_id, snap in files:
        print '%s\t%s...%s\t%s' % (filename, content_hash[:17]
                               , content_hash[-3:], snap.id)

def upload_sfs_file(session, filename):
    """
    Uploads a file to Snapchat FS.

    @session An SfsSession object that has been logged in.
    @filename Path of the file to upload.
    """
    with open(filename) as f:
        data = f.read()

    basename = os.path.basename(filename)
    print util.green('Uploading file ') + (basename)
    sfs_id = session.generate_sfs_id(basename, data)
    session.upload_image(data, sfs_id)
    session.send_image_to(session.username, sfs_id)

########NEW FILE########
__FILENAME__ = util
#!/usr/bin/env python

"""
util.py provides a set of nice utility functions that support the snapchat_fs pkg
"""

__author__ = "Alex Clemmer, Chad Brubaker"
__copyright__ = "Copyright 2013, Alex Clemmer and Chad Brubaker"
__credits__ = ["Alex Clemmer", "Chad Brubaker"]

__license__ = "MIT"
__version__ = "0.1"
__maintainer__ = "Alex Clemmer"
__email__ = "clemmer.alexander@gmail.com"
__status__ = "Prototype"


def bold(text):
    return '\033[1m%s\033[0m' % text

def green(text):
    return '\033[1;32m%s\033[0m' % text

def red(text):
    return '\033[1;31m%s\033[0m' % text


########NEW FILE########
