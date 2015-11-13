__FILENAME__ = about
import gtk
import sys
import os

import liblookit

class AboutDialog:
    def __init__(self):
        try:
            builder = gtk.Builder()
            datadir = liblookit.get_data_dir()
            xmlfile = os.path.join(datadir, 'about.xml')
            builder.add_from_file(xmlfile)
        except:
            print "Error loading XML file"
            sys.exit(1)

        self.dialog = builder.get_object("about_dialog")
        self.dialog.connect("response", self.on_about_dialog_close)
        builder.connect_signals(self)
        self.dialog.set_version(liblookit.VERSION_STR)

    def run(self):
        self.dialog.run()

    def on_about_dialog_response(self, widget, data=None):
        self.dialog.destroy()

    def on_about_dialog_close(self, widget, data=None):
        self.dialog.destroy()

if __name__=="__main__":
    AboutDialog().run() # For testing purposes only

########NEW FILE########
__FILENAME__ = cloud
"""
Cloud is a CloudApp API Wrapper, obviously written in Python.

The code is under GNU GPL V3.0.
The complete license text should have been shipped with this file. If this is
not the case you can find it under http://www.gnu.org/licenses/gpl-3.0.txt.

In order to have this fully functional you need:
    - poster
        This is needed as Python does not (yet) support
        multipart/form-data-requests out of the box.
    - Python 2.7 or ordereddict
        Necessary because Amazon's S3 expects the file to be the last
        value in the upload request.

The following values are available:
    - *cloud.__version_info__*
        a 3-tuple containing the version number.
        Format: '(major, minor, maintenance)'
    - *cloud.__version__*
        a string generated from __version_info__.
        Format: 'major.minor.maintenance'
    - *cloud.PROTOCOL*
        a string specifying the protocol to be used.
        Default: '\'http://\''
    - *cloud.URI*
        a string containing the URL used by non-authed requests.
        Default: '\'cl.ly\''
    - *cloud.AUTH_URI*
        a string containg the URL used by authed requests.
        Default: '\'my.cl.ly\''
    - *cloud.FILE_TYPES*
        a tuple filled with available filetypes.

The following classes are available:
    - CloudException
        An exception thrown on errors with Cloud.
    - DeleteRequest
        A HTTP DELETE request.
    - Cloud
        The pythonic CloudApp API Wrapper.

"""

import urllib2
import urllib
import json
import os

__version_info__ = (0, 7, 0)
__version__ = '.'.join([str(x) for x in __version_info__])


# Python does not support multipart/form-data encoding out of the box
try:
    import poster
    POSTER = True
except ImportError:
    POSTER = False

# We need ordereddicts as Amazon S3 expects 'file' to be the last param
# in the request's body when uploading.
ORDERED_DICT = True
try:
    from collections import OrderedDict
except ImportError:
    try:
        from ordereddict import OrderedDict
    except ImportError:
        ORDERED_DICT = False

PROTOCOL = 'http://'
    
URI = 'cl.ly'
AUTH_URI = 'my.cl.ly'
USER_AGENT = 'Cloud API Python Wrapper/%s' % __version__

FILE_TYPES = ('image', 'bookmark', 'test', 'archive', 'audio', 'video', 'unknown')


class CloudException(Exception):
    """An exception thrown on errors with cloud."""
    pass

class DeleteRequest(urllib2.Request):
    """
    A HTTP DELETE request.

    Public methods:
        - get_method
            Sets the HTTP method to DELETE.

    """
    def get_method(self):
        """Sets the HTTP method to DELETE."""
        return 'DELETE'

class Cloud(object):
    """
    The pythonic CloudApp API Wrapper.

    Public methods:
        - auth(username, password)
            Authenticates a user.
        - item_info(url)
            Get metadata about a cl.ly URL.
        - list_items(page=False, per_page=False, file_type=False, deleted=False)
            List the authenticated user's items.
        - create_bookmark(name, url)
            Creates a bookmark with the given name and url.
        - upload_file(path)
            Upload a file.
            
    """
    def __init__(self):
        """
        Init.

        *opener* is for functions that do not need authentication.
        
        """
        self.opener = urllib2.build_opener()
        self.opener.addheaders = [('User-Agent', USER_AGENT),
                                  ('Accept', 'application/json'),]
        self.auth_success = 0

    def auth(self, username, password):
        """
        Authenticate the given username with the given password.

        If poster is installed, build an upload handler.

        """
        if self.auth_success == 1:
            return True
        
        passwordmgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
        passwordmgr.add_password(None, AUTH_URI, username, password)
        auth = urllib2.HTTPDigestAuthHandler(passwordmgr)

        self.auth_opener = urllib2.build_opener(auth)
        self.auth_opener.addheaders = [('User-Agent', USER_AGENT),
                                       ('Accept', 'application/json'),]

        if POSTER:
            self.upload_auth_opener = poster.streaminghttp.register_openers()
            self.upload_auth_opener.add_handler(auth)
            self.upload_auth_opener.addheaders = [('User-Agent', USER_AGENT),
                                                  ('Accept', 'application/json'),]

        if self.auth_success == 0:
            self._test_auth()

    def _test_auth(self):
        """Test authentication."""
        query = urllib.urlencode({'page': 1, 'per_page': 1})
        page = self.auth_opener.open('%s%s/items?%s' % (PROTOCOL, AUTH_URI, query))
        if page.code == 200:
            self.auth_success = 1
            return True
        return False

    def item_info(self, uri):
        """Get metadata about a cl.ly URL."""
        validator = '%s%s' % (PROTOCOL, URI)
        if validator in uri:
            return json.load(self.opener.open(uri))
        raise CloudException('URI not valid')

    def list_items(self, page=False, per_page=False, file_type=False, deleted=False):
        """
        List the authenticated user's items.

        Optional arguments:
            - *page*
                an integer representing the page number.
            - *per_page*
                an integer representing number of items per page.
            - *type*
                Filter items by types found in FILTER_TYPES
            - *deleted*
                a boolean. Show trashed items.
        
        """
        if self.auth_success == 0:
            raise CloudException('Not authed')
        
        params = {}
        if page:
            params['page'] = int(page)
        if per_page:
            params['per_page'] = int(per_page)
        if file_type:
            if isinstance(file_type, basestring) and \
               file_type.lower() in FILE_TYPES:
                params['type'] = file_type
        if deleted:
            params['deleted'] = bool(deleted)

        query = urllib.urlencode(params)
        return json.load(self.auth_opener.open('%s%s/items?%s' % (PROTOCOL, AUTH_URI, query)),
                         encoding='utf-8')

    def create_bookmark(self, name, bookmark_uri):
        """Creates a bookmark with the given name and url."""
        if self.auth_success == 0:
            raise CloudException('Not authed')

        values = {'item': {'name': name, 'redirect_url': bookmark_uri}}
        data = json.dumps(values, encoding='utf-8')
        request = urllib2.Request('%s%s/items' % (PROTOCOL, AUTH_URI), data)
        request.add_header('Content-Type', 'application/json')

        return json.load(self.auth_opener.open(request))

    def upload_file(self, path):
        """
        Upload a file.

        This function requires you to be authenticated.
        
        Furthermore you need to have poster installed as well as python 2.7 or
        ordereddict.
        
        """
        if not POSTER:
            raise CloudException('Poster is not installed')
        if not ORDERED_DICT:
            raise CloudException('Python 2.7 or ordereddict are not installed')
        
        if self.auth_success == 0:
            raise CloudException('Not authed')

        if not os.path.exists(path):
            raise CloudException('File does not exist')
        if not os.path.isfile(path):
            raise CloudException('The given path does not point to a file')

        directives = json.load(self.auth_opener.open('%s%s/items/new' % (PROTOCOL, AUTH_URI)))
        directives['params']['key'] = directives['params']['key'] \
                                      .replace('${filename}',
                                               os.path.split(path)[-1])
        upload_values = OrderedDict(sorted(directives['params'].items(), key=lambda t: t[0]))
        upload_values['file'] = open(path, 'rb').read()
        datagen, headers = poster.encode.multipart_encode(upload_values)
        request = urllib2.Request(directives['url'], datagen, headers)

        return json.load(self.upload_auth_opener.open(request))

    def delete_file(self, href):
        """Delete a file with the given href."""
        if self.auth_success == 0:
            raise CloudException('Not authed')
        result = self.auth_opener.open(DeleteRequest(href))
        if result.code == 200:
            return True
        raise CloudException('Deletion failed')

########NEW FILE########
__FILENAME__ = imgur
import os
import pycurl
import xml.parsers.expat

import liblookit

IMGUR_ALLOWED = ['JPEG', 'GIF', 'PNG', 'APNG', 'TIFF', 'BMP', 'PDF', 'XCF']

class ImgurUploader:
    def __init__(self):
        self.response = ''
        self.current_key = None
        self.mapping = {}

    def xml_ele_start(self, name, attrs):
        self.current_key = str(name)

    def xml_ele_end(self, name):
        self.current_key = None

    def xml_ele_data(self, data):
        if self.current_key is not None:
            self.mapping[self.current_key] = str(data)

    def curl_response(self, buf):
        self.response = self.response + buf

    def upload(self, image):
        # Note: This key is specific for Lookit. If you want to use
        # the Imgur API in your application, please register for a new
        # API key at: http://imgur.com/register/api/
        client_id = 'cde2ab3f2b4972c'
        key = os.getenv('IMGUR_CLIENT_ID', client_id)

        c = pycurl.Curl()
        values = [('image', (c.FORM_FILE, image))]
        c.setopt(pycurl.HTTPHEADER, ['Authorization:  Client-ID ' + key])
        c.setopt(c.URL, 'https://api.imgur.com/3/upload.xml')
        c.setopt(c.HTTPPOST, values)
        c.setopt(c.WRITEFUNCTION, self.curl_response)
        c.setopt(c.USERAGENT, 'liblookit/' + liblookit.VERSION_STR)

        c.perform()
        c.close()

        p = xml.parsers.expat.ParserCreate()

        p.StartElementHandler = self.xml_ele_start
        p.EndElementHandler = self.xml_ele_end
        p.CharacterDataHandler = self.xml_ele_data

        p.Parse(self.response)

########NEW FILE########
__FILENAME__ = liblookit
import os
import pynotify
import time

import about
import lookitconfig
import preferences
import screencapper
import selector
import uploader

from xdg import BaseDirectory

XDG_CACHE_HOME = os.environ.get('XDG_CACHE_HOME', os.path.expanduser('~/.cache'))

CONFIG_DIR = BaseDirectory.save_config_path('lookit')
LOG_FILE = os.path.join(CONFIG_DIR, 'log')

VERSION = (1, 2, 0)
VERSION_STR = '.'.join(str(num) for num in VERSION)

def enum(*sequential, **named):
    enums = dict(zip(sequential, range(len(sequential))), **named)
    return type('Enum', (), enums)

def str_to_tuple(s):
    return tuple(int(x) for x in s.split('.'))

def get_data_dir():
    p = os.path.abspath(__file__)
    p = os.path.dirname(p)
    p = os.path.join(p, 'data')
    return p

def show_notification(title, message):
    try:
        pynotify.init('Lookit')
        n = pynotify.Notification(title, message, 'lookit')
        n.set_hint_string('append', '')
        n.show()
    except Exception as e:
        print 'An error occurred trying to show notifications:'
        print e

def migrate_from_1_0():
    old_config = os.path.expanduser('~/.config/lookit.conf')
    if os.path.isfile(old_config):
        config = lookitconfig.LookitConfig(old_config)
        config.filename = lookitconfig.CONFIG_FILE
        config.save()
        os.remove(old_config)

def upload_file(filename, existing_file=False):
    uploader.upload_file(filename, existing_file)

def handle_delay():
    delay_value = lookitconfig.LookitConfig().getint('General', 'delay')
    time.sleep(delay_value)

def do_capture_area():
    handle_delay()
    ffb = lookitconfig.LookitConfig().getboolean('General', 'force_fallback')
    selection = selector.Selector().get_selection(ffb)
    if selection is None:
        show_notification('Lookit', 'Selection cancelled')
        return
    pb = screencapper.capture_selection(selection)
    return uploader.upload_pixbuf(pb)

def do_capture_window():
    handle_delay()
    pb = screencapper.capture_active_window()
    return uploader.upload_pixbuf(pb)

def do_capture_screen():
    handle_delay()
    pb = screencapper.capture_screen()
    return uploader.upload_pixbuf(pb)

def do_preferences():
    preferences.PreferencesDialog().run()

def do_about():
    about.AboutDialog().run()

########NEW FILE########
__FILENAME__ = lookitconfig
from ConfigParser import RawConfigParser, NoSectionError, NoOptionError
import gconf
import keyring
import os
import subprocess

from xdg import BaseDirectory

CONFIG_DIR = BaseDirectory.save_config_path('lookit')
CONFIG_FILE = os.path.join(CONFIG_DIR, 'config')

try:
    PICTURE_DIR = subprocess.Popen(['xdg-user-dir', 'PICTURES'], \
                stdout=subprocess.PIPE).communicate()[0] \
                .strip('\n')
except OSError:
    PICTURE_DIR = os.path.expanduser('~')

HOTKEY_NAMES = {'capturearea': 'Lookit: Capture Area',
                'capturescreen': 'Lookit: Capture Screen',
                'capturewindow': 'Lookit: Capture Window'}
HOTKEY_IDENTS = {'capturearea': 'lookit_capture_area',
                'capturescreen': 'lookit_capture_screen',
                'capturewindow': 'lookit_capture_window'}
HOTKEY_ACTIONS = {'capturearea': 'lookit --capture-area',
                'capturescreen': 'lookit --capture-screen',
                'capturewindow': 'lookit --capture-window'}

KEYBINDING_DIR = '/desktop/gnome/keybindings/'

DEFAULTS = {'General': {'shortenurl': False,
                        'trash': False,
                        'savedir': PICTURE_DIR,
                        'autostart': False,
                        'delay': 0,
                        'force_fallback': False},
            'Hotkeys': {'capturearea': '<Control><Alt>4',
                        'capturescreen': '<Control><Alt>5',
                        'capturewindow': '<Control><Alt>6'},
            'Upload':  {'enableupload': True,
                        'type': 'None',
                        'hostname': '',
                        'port': 0,
                        'username': '',
                        'ssh_key_file': '',
                        'directory': '',
                        'url': 'http://'}
}

class LookitConfig(RawConfigParser):
    def __init__(self, filename=CONFIG_FILE):
        RawConfigParser.__init__(self)
        self.filename = filename
        self.load()

    def get(self, section, option):
        if option == 'password':
            password = keyring.get_password('lookit', 'lookit')
            if password is None:
                return ''
            else:
                return password
        else:
            try:
                return RawConfigParser.get(self, section, option)
            except (NoSectionError, NoOptionError):
                return DEFAULTS[section][option]

    def set(self, section, option, value):
        if not section in self.sections():
            self.add_section(section)
        if section == 'Hotkeys':
            client = gconf.client_get_default()
            key = HOTKEY_IDENTS[option]
            client.set_string(KEYBINDING_DIR + key + '/name', HOTKEY_NAMES[option])
            client.set_string(KEYBINDING_DIR + key + '/action', HOTKEY_ACTIONS[option])
            client.set_string(KEYBINDING_DIR + key + '/binding', value)
        if option == 'autostart':
            try:
                if value:
                    os.symlink('/usr/share/applications/lookit.desktop', \
                        os.path.expanduser( \
                        '~/.config/autostart/lookit.desktop'))
                else:
                    os.unlink(os.path.expanduser( \
                        '~/.config/autostart/lookit.desktop'))
            except OSError:
                pass
        if option == 'password':
            keyring.set_password('lookit', 'lookit', value)
        else:
            RawConfigParser.set(self, section, option, value)

    def rename_section(self, old_name, new_name):
        if not self.has_section(old_name) or self.has_section(new_name):
            return False
        for (name, value) in self.items(old_name):
            self.set(new_name, name, value)
        self.remove_section(old_name)
        return True

    def getboolean(self, section, option):
        try:
            return RawConfigParser.getboolean(self, section, option)
        except AttributeError:
            # XXX:
            # For some reason, getboolean likes to die sometimes.
            # Until I figure it out, this will act as a band-aid
            # to prevent the error from causing Lookit to not work
            value = self.get(section, option)
            if type(value) == bool:
                return value
            elif type(value) == str:
                return value == 'True'
            else:
                return bool(value)

    def load(self):
        self.read(self.filename)

    def save(self):
        f = open(self.filename, 'w')
        self.write(f)
        f.flush()
        f.close()

if __name__ == '__main__':
    lc = LookitConfig()


########NEW FILE########
__FILENAME__ = lookitindicator
try:
    import appindicator
    INDICATOR_SUPPORT = True
except ImportError:
    INDICATOR_SUPPORT = False

import gtk
import time
import webbrowser

import liblookit
import lookitconfig

from liblookit import enum
cmd = enum('CAPTURE_AREA', 'CAPTURE_ACTIVE_WINDOW', 'CAPTURE_SCREEN',
                'SHOW_PREFERENCES', 'SHOW_ABOUT', 'EXIT',
                'DELAY_0', 'DELAY_3', 'DELAY_5', 'DELAY_10', 'TOGGLE_UPLOAD')
MAX_IMAGE_COUNTS = 3

class LookitIndicator:

    def __init__(self):
        self.indicator = appindicator.Indicator(
            "Lookit",
            "lookit-panel",
            appindicator.CATEGORY_APPLICATION_STATUS)
        self.indicator.set_status(appindicator.STATUS_ACTIVE)

        self.menu = gtk.Menu()
        self.add_menu_item('Capture Area', cmd.CAPTURE_AREA)
        self.add_menu_item('Capture Entire Screen', cmd.CAPTURE_SCREEN)
        self.add_menu_item('Capture Active Window', cmd.CAPTURE_ACTIVE_WINDOW)

        self.add_menu_separator()

        delaymenu = gtk.Menu()
        self.add_menu_item('0 seconds', cmd.DELAY_0, delaymenu)
        self.add_menu_item('3 seconds', cmd.DELAY_3, delaymenu)
        self.add_menu_item('5 seconds', cmd.DELAY_5, delaymenu)
        self.add_menu_item('10 seconds', cmd.DELAY_10, delaymenu)
        sub = gtk.MenuItem('Set Delay:')
        sub.set_submenu(delaymenu)
        self.menu.append(sub)

        config = lookitconfig.LookitConfig()
        enableupload = config.getboolean('Upload', 'enableupload')
        self.add_check_menu_item('Upload to server', cmd.TOGGLE_UPLOAD, value=enableupload)

        self.add_menu_separator()
        self.add_menu_item('Preferences', cmd.SHOW_PREFERENCES)
        self.add_menu_item('About', cmd.SHOW_ABOUT)

        self.image_position = len(self.menu)
        self.image_list = []

        self.add_menu_separator()
        self.add_menu_item('Exit', cmd.EXIT)

        self.menu.show_all()
        self.indicator.set_menu(self.menu)

    def add_menu_item(self, label, command, menu=None):
        item = gtk.MenuItem(label)
        item.connect('activate', self.handle_menu_item, command)
        if menu is None:
            menu = self.menu
        menu.append(item)

    def add_check_menu_item(self, label, command, menu=None, value=True):
        item = gtk.CheckMenuItem(label)
        item.set_active(value)
        item.connect('activate', self.handle_menu_item, command)
        if menu is None:
            menu = self.menu
        menu.append(item)

    def add_menu_separator(self):
        item = gtk.SeparatorMenuItem()
        item.show()
        self.menu.append(item)

    def set_delay(self, value):
        config = lookitconfig.LookitConfig()
        config.set('General', 'delay', value)
        config.save()

    def set_upload(self, value):
        config = lookitconfig.LookitConfig()
        config.set('Upload', 'enableupload', value)
        config.save()

    def add_image(self, uri):
        """ Add image into menu and throw away an old image """
        if len(self.image_list) == 0:
            item = gtk.SeparatorMenuItem()
            item.show()
            self.menu.insert(item, self.image_position)
            self.image_position += 1

        if len(self.image_list) >= MAX_IMAGE_COUNTS:
            item = self.image_list.pop(0)
            self.menu.remove(item)

        label = time.strftime('%H:%M:%S')
        item = gtk.MenuItem(label)
        item.connect('activate', self.open_image, uri)
        item.show()
        position = self.image_position + len(self.image_list)
        self.menu.insert(item, position)
        self.image_list.append(item)

    def open_image(self, widget=None, uri=None):
        """ Open image and copy URI into clipboard """
        clipboard = gtk.clipboard_get()
        clipboard.set_text(uri)
        clipboard.store()

        webbrowser.open(uri)

    def handle_menu_item(self, widget=None, command=None):
        uri = None
        if command == cmd.CAPTURE_AREA:
            uri = liblookit.do_capture_area()
        elif command == cmd.CAPTURE_ACTIVE_WINDOW:
            uri = liblookit.do_capture_window()
        elif command == cmd.CAPTURE_SCREEN:
            uri = liblookit.do_capture_screen()
        elif command == cmd.SHOW_PREFERENCES:
            liblookit.do_preferences()
        elif command == cmd.SHOW_ABOUT:
            liblookit.do_about()
        elif command == cmd.EXIT:
            gtk.main_quit()
        elif command == cmd.DELAY_0:
            self.set_delay(0)
        elif command == cmd.DELAY_3:
            self.set_delay(3)
        elif command == cmd.DELAY_5:
            self.set_delay(5)
        elif command == cmd.DELAY_10:
            self.set_delay(10)
        elif command == cmd.TOGGLE_UPLOAD:
            self.set_upload(widget.get_active())
        else:
            print 'Error: reached end of handle_menu_item'

        if uri is not None:
            self.add_image(uri)

if __name__ == '__main__':
	i = LookitIndicator()
	gtk.main()

########NEW FILE########
__FILENAME__ = encode
"""multipart/form-data encoding module

This module provides functions that faciliate encoding name/value pairs
as multipart/form-data suitable for a HTTP POST or PUT request.

multipart/form-data is the standard way to upload files over HTTP"""

__all__ = ['gen_boundary', 'encode_and_quote', 'MultipartParam',
        'encode_string', 'encode_file_header', 'get_body_size', 'get_headers',
        'multipart_encode']

try:
    import uuid
    def gen_boundary():
        """Returns a random string to use as the boundary for a message"""
        return uuid.uuid4().hex
except ImportError:
    import random, sha
    def gen_boundary():
        """Returns a random string to use as the boundary for a message"""
        bits = random.getrandbits(160)
        return sha.new(str(bits)).hexdigest()

import urllib, re, os, mimetypes
try:
    from email.header import Header
except ImportError:
    # Python 2.4
    from email.Header import Header

def encode_and_quote(data):
    """If ``data`` is unicode, return urllib.quote_plus(data.encode("utf-8"))
    otherwise return urllib.quote_plus(data)"""
    if data is None:
        return None

    if isinstance(data, unicode):
        data = data.encode("utf-8")
    return urllib.quote_plus(data)

def _strify(s):
    """If s is a unicode string, encode it to UTF-8 and return the results,
    otherwise return str(s), or None if s is None"""
    if s is None:
        return None
    if isinstance(s, unicode):
        return s.encode("utf-8")
    return str(s)

class MultipartParam(object):
    """Represents a single parameter in a multipart/form-data request

    ``name`` is the name of this parameter.

    If ``value`` is set, it must be a string or unicode object to use as the
    data for this parameter.

    If ``filename`` is set, it is what to say that this parameter's filename
    is.  Note that this does not have to be the actual filename any local file.

    If ``filetype`` is set, it is used as the Content-Type for this parameter.
    If unset it defaults to "text/plain; charset=utf8"

    If ``filesize`` is set, it specifies the length of the file ``fileobj``

    If ``fileobj`` is set, it must be a file-like object that supports
    .read().

    Both ``value`` and ``fileobj`` must not be set, doing so will
    raise a ValueError assertion.

    If ``fileobj`` is set, and ``filesize`` is not specified, then
    the file's size will be determined first by stat'ing ``fileobj``'s
    file descriptor, and if that fails, by seeking to the end of the file,
    recording the current position as the size, and then by seeking back to the
    beginning of the file.

    ``cb`` is a callable which will be called from iter_encode with (self,
    current, total), representing the current parameter, current amount
    transferred, and the total size.
    """
    def __init__(self, name, value=None, filename=None, filetype=None,
                        filesize=None, fileobj=None, cb=None):
        self.name = Header(name).encode()
        self.value = _strify(value)
        if filename is None:
            self.filename = None
        else:
            if isinstance(filename, unicode):
                # Encode with XML entities
                self.filename = filename.encode("ascii", "xmlcharrefreplace")
            else:
                self.filename = str(filename)
            self.filename = self.filename.encode("string_escape").\
                    replace('"', '\\"')
        self.filetype = _strify(filetype)

        self.filesize = filesize
        self.fileobj = fileobj
        self.cb = cb

        if self.value is not None and self.fileobj is not None:
            raise ValueError("Only one of value or fileobj may be specified")

        if fileobj is not None and filesize is None:
            # Try and determine the file size
            try:
                self.filesize = os.fstat(fileobj.fileno()).st_size
            except (OSError, AttributeError):
                try:
                    fileobj.seek(0, 2)
                    self.filesize = fileobj.tell()
                    fileobj.seek(0)
                except:
                    raise ValueError("Could not determine filesize")

    def __cmp__(self, other):
        attrs = ['name', 'value', 'filename', 'filetype', 'filesize', 'fileobj']
        myattrs = [getattr(self, a) for a in attrs]
        oattrs = [getattr(other, a) for a in attrs]
        return cmp(myattrs, oattrs)

    def reset(self):
        if self.fileobj is not None:
            self.fileobj.seek(0)
        elif self.value is None:
            raise ValueError("Don't know how to reset this parameter")

    @classmethod
    def from_file(cls, paramname, filename):
        """Returns a new MultipartParam object constructed from the local
        file at ``filename``.

        ``filesize`` is determined by os.path.getsize(``filename``)

        ``filetype`` is determined by mimetypes.guess_type(``filename``)[0]

        ``filename`` is set to os.path.basename(``filename``)
        """

        return cls(paramname, filename=os.path.basename(filename),
                filetype=mimetypes.guess_type(filename)[0],
                filesize=os.path.getsize(filename),
                fileobj=open(filename, "rb"))

    @classmethod
    def from_params(cls, params):
        """Returns a list of MultipartParam objects from a sequence of
        name, value pairs, MultipartParam instances,
        or from a mapping of names to values

        The values may be strings or file objects, or MultipartParam objects.
        MultipartParam object names must match the given names in the
        name,value pairs or mapping, if applicable."""
        if hasattr(params, 'items'):
            params = params.items()

        retval = []
        for item in params:
            if isinstance(item, cls):
                retval.append(item)
                continue
            name, value = item
            if isinstance(value, cls):
                assert value.name == name
                retval.append(value)
                continue
            if hasattr(value, 'read'):
                # Looks like a file object
                filename = getattr(value, 'name', None)
                if filename is not None:
                    filetype = mimetypes.guess_type(filename)[0]
                else:
                    filetype = None

                retval.append(cls(name=name, filename=filename,
                    filetype=filetype, fileobj=value))
            else:
                retval.append(cls(name, value))
        return retval

    def encode_hdr(self, boundary):
        """Returns the header of the encoding of this parameter"""
        boundary = encode_and_quote(boundary)

        headers = ["--%s" % boundary]

        if self.filename:
            disposition = 'form-data; name="%s"; filename="%s"' % (self.name,
                    self.filename)
        else:
            disposition = 'form-data; name="%s"' % self.name

        headers.append("Content-Disposition: %s" % disposition)

        if self.filetype:
            filetype = self.filetype
        else:
            filetype = "text/plain; charset=utf-8"

        headers.append("Content-Type: %s" % filetype)

        headers.append("")
        headers.append("")

        return "\r\n".join(headers)

    def encode(self, boundary):
        """Returns the string encoding of this parameter"""
        if self.value is None:
            value = self.fileobj.read()
        else:
            value = self.value

        if re.search("^--%s$" % re.escape(boundary), value, re.M):
            raise ValueError("boundary found in encoded string")

        return "%s%s\r\n" % (self.encode_hdr(boundary), value)

    def iter_encode(self, boundary, blocksize=4096):
        """Yields the encoding of this parameter
        If self.fileobj is set, then blocks of ``blocksize`` bytes are read and
        yielded."""
        total = self.get_size(boundary)
        current = 0
        if self.value is not None:
            block = self.encode(boundary)
            current += len(block)
            yield block
            if self.cb:
                self.cb(self, current, total)
        else:
            block = self.encode_hdr(boundary)
            current += len(block)
            yield block
            if self.cb:
                self.cb(self, current, total)
            last_block = ""
            encoded_boundary = "--%s" % encode_and_quote(boundary)
            boundary_exp = re.compile("^%s$" % re.escape(encoded_boundary),
                    re.M)
            while True:
                block = self.fileobj.read(blocksize)
                if not block:
                    current += 2
                    yield "\r\n"
                    if self.cb:
                        self.cb(self, current, total)
                    break
                last_block += block
                if boundary_exp.search(last_block):
                    raise ValueError("boundary found in file data")
                last_block = last_block[-len(encoded_boundary)-2:]
                current += len(block)
                yield block
                if self.cb:
                    self.cb(self, current, total)

    def get_size(self, boundary):
        """Returns the size in bytes that this param will be when encoded
        with the given boundary."""
        if self.filesize is not None:
            valuesize = self.filesize
        else:
            valuesize = len(self.value)

        return len(self.encode_hdr(boundary)) + 2 + valuesize

def encode_string(boundary, name, value):
    """Returns ``name`` and ``value`` encoded as a multipart/form-data
    variable.  ``boundary`` is the boundary string used throughout
    a single request to separate variables."""

    return MultipartParam(name, value).encode(boundary)

def encode_file_header(boundary, paramname, filesize, filename=None,
        filetype=None):
    """Returns the leading data for a multipart/form-data field that contains
    file data.

    ``boundary`` is the boundary string used throughout a single request to
    separate variables.

    ``paramname`` is the name of the variable in this request.

    ``filesize`` is the size of the file data.

    ``filename`` if specified is the filename to give to this field.  This
    field is only useful to the server for determining the original filename.

    ``filetype`` if specified is the MIME type of this file.

    The actual file data should be sent after this header has been sent.
    """

    return MultipartParam(paramname, filesize=filesize, filename=filename,
            filetype=filetype).encode_hdr(boundary)

def get_body_size(params, boundary):
    """Returns the number of bytes that the multipart/form-data encoding
    of ``params`` will be."""
    size = sum(p.get_size(boundary) for p in MultipartParam.from_params(params))
    return size + len(boundary) + 6

def get_headers(params, boundary):
    """Returns a dictionary with Content-Type and Content-Length headers
    for the multipart/form-data encoding of ``params``."""
    headers = {}
    boundary = urllib.quote_plus(boundary)
    headers['Content-Type'] = "multipart/form-data; boundary=%s" % boundary
    headers['Content-Length'] = str(get_body_size(params, boundary))
    return headers

class multipart_yielder:
    def __init__(self, params, boundary, cb):
        self.params = params
        self.boundary = boundary
        self.cb = cb

        self.i = 0
        self.p = None
        self.param_iter = None
        self.current = 0
        self.total = get_body_size(params, boundary)

    def __iter__(self):
        return self

    def next(self):
        """generator function to yield multipart/form-data representation
        of parameters"""
        if self.param_iter is not None:
            try:
                block = self.param_iter.next()
                self.current += len(block)
                if self.cb:
                    self.cb(self.p, self.current, self.total)
                return block
            except StopIteration:
                self.p = None
                self.param_iter = None

        if self.i is None:
            raise StopIteration
        elif self.i >= len(self.params):
            self.param_iter = None
            self.p = None
            self.i = None
            block = "--%s--\r\n" % self.boundary
            self.current += len(block)
            if self.cb:
                self.cb(self.p, self.current, self.total)
            return block

        self.p = self.params[self.i]
        self.param_iter = self.p.iter_encode(self.boundary)
        self.i += 1
        return self.next()

    def reset(self):
        self.i = 0
        self.current = 0
        for param in self.params:
            param.reset()

def multipart_encode(params, boundary=None, cb=None):
    """Encode ``params`` as multipart/form-data.

    ``params`` should be a sequence of (name, value) pairs or MultipartParam
    objects, or a mapping of names to values.
    Values are either strings parameter values, or file-like objects to use as
    the parameter value.  The file-like objects must support .read() and either
    .fileno() or both .seek() and .tell().

    If ``boundary`` is set, then it as used as the MIME boundary.  Otherwise
    a randomly generated boundary will be used.  In either case, if the
    boundary string appears in the parameter values a ValueError will be
    raised.

    If ``cb`` is set, it should be a callback which will get called as blocks
    of data are encoded.  It will be called with (param, current, total),
    indicating the current parameter being encoded, the current amount encoded,
    and the total amount to encode.

    Returns a tuple of `datagen`, `headers`, where `datagen` is a
    generator that will yield blocks of data that make up the encoded
    parameters, and `headers` is a dictionary with the assoicated
    Content-Type and Content-Length headers.

    Examples:

    >>> datagen, headers = multipart_encode( [("key", "value1"), ("key", "value2")] )
    >>> s = "".join(datagen)
    >>> assert "value2" in s and "value1" in s

    >>> p = MultipartParam("key", "value2")
    >>> datagen, headers = multipart_encode( [("key", "value1"), p] )
    >>> s = "".join(datagen)
    >>> assert "value2" in s and "value1" in s

    >>> datagen, headers = multipart_encode( {"key": "value1"} )
    >>> s = "".join(datagen)
    >>> assert "value2" not in s and "value1" in s

    """
    if boundary is None:
        boundary = gen_boundary()
    else:
        boundary = urllib.quote_plus(boundary)

    headers = get_headers(params, boundary)
    params = MultipartParam.from_params(params)

    return multipart_yielder(params, boundary, cb), headers

########NEW FILE########
__FILENAME__ = streaminghttp
"""Streaming HTTP uploads module.

This module extends the standard httplib and urllib2 objects so that
iterable objects can be used in the body of HTTP requests.

In most cases all one should have to do is call :func:`register_openers()`
to register the new streaming http handlers which will take priority over
the default handlers, and then you can use iterable objects in the body
of HTTP requests.

**N.B.** You must specify a Content-Length header if using an iterable object
since there is no way to determine in advance the total size that will be
yielded, and there is no way to reset an interator.

Example usage:

>>> from StringIO import StringIO
>>> import urllib2, poster.streaminghttp

>>> opener = poster.streaminghttp.register_openers()

>>> s = "Test file data"
>>> f = StringIO(s)

>>> req = urllib2.Request("http://localhost:5000", f,
...                       {'Content-Length': str(len(s))})
"""

import httplib, urllib2, socket
from httplib import NotConnected

__all__ = ['StreamingHTTPConnection', 'StreamingHTTPRedirectHandler',
        'StreamingHTTPHandler', 'register_openers']

if hasattr(httplib, 'HTTPS'):
    __all__.extend(['StreamingHTTPSHandler', 'StreamingHTTPSConnection'])

class _StreamingHTTPMixin:
    """Mixin class for HTTP and HTTPS connections that implements a streaming
    send method."""
    def send(self, value):
        """Send ``value`` to the server.

        ``value`` can be a string object, a file-like object that supports
        a .read() method, or an iterable object that supports a .next()
        method.
        """
        # Based on python 2.6's httplib.HTTPConnection.send()
        if self.sock is None:
            if self.auto_open:
                self.connect()
            else:
                raise NotConnected()

        # send the data to the server. if we get a broken pipe, then close
        # the socket. we want to reconnect when somebody tries to send again.
        #
        # NOTE: we DO propagate the error, though, because we cannot simply
        #       ignore the error... the caller will know if they can retry.
        if self.debuglevel > 0:
            print "send:", repr(value)
        try:
            blocksize = 8192
            if hasattr(value, 'read') :
                if hasattr(value, 'seek'):
                    value.seek(0)
                if self.debuglevel > 0:
                    print "sendIng a read()able"
                data = value.read(blocksize)
                while data:
                    self.sock.sendall(data)
                    data = value.read(blocksize)
            elif hasattr(value, 'next'):
                if hasattr(value, 'reset'):
                    value.reset()
                if self.debuglevel > 0:
                    print "sendIng an iterable"
                for data in value:
                    self.sock.sendall(data)
            else:
                self.sock.sendall(value)
        except socket.error, v:
            if v[0] == 32:      # Broken pipe
                self.close()
            raise

class StreamingHTTPConnection(_StreamingHTTPMixin, httplib.HTTPConnection):
    """Subclass of `httplib.HTTPConnection` that overrides the `send()` method
    to support iterable body objects"""

class StreamingHTTPRedirectHandler(urllib2.HTTPRedirectHandler):
    """Subclass of `urllib2.HTTPRedirectHandler` that overrides the
    `redirect_request` method to properly handle redirected POST requests

    This class is required because python 2.5's HTTPRedirectHandler does
    not remove the Content-Type or Content-Length headers when requesting
    the new resource, but the body of the original request is not preserved.
    """

    handler_order = urllib2.HTTPRedirectHandler.handler_order - 1

    # From python2.6 urllib2's HTTPRedirectHandler
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        """Return a Request or None in response to a redirect.

        This is called by the http_error_30x methods when a
        redirection response is received.  If a redirection should
        take place, return a new Request to allow http_error_30x to
        perform the redirect.  Otherwise, raise HTTPError if no-one
        else should try to handle this url.  Return None if you can't
        but another Handler might.
        """
        m = req.get_method()
        if (code in (301, 302, 303, 307) and m in ("GET", "HEAD")
            or code in (301, 302, 303) and m == "POST"):
            # Strictly (according to RFC 2616), 301 or 302 in response
            # to a POST MUST NOT cause a redirection without confirmation
            # from the user (of urllib2, in this case).  In practice,
            # essentially all clients do redirect in this case, so we
            # do the same.
            # be conciliant with URIs containing a space
            newurl = newurl.replace(' ', '%20')
            newheaders = dict((k, v) for k, v in req.headers.items()
                              if k.lower() not in (
                                  "content-length", "content-type")
                             )
            return urllib2.Request(newurl,
                           headers=newheaders,
                           origin_req_host=req.get_origin_req_host(),
                           unverifiable=True)
        else:
            raise urllib2.HTTPError(req.get_full_url(), code, msg, headers, fp)

class StreamingHTTPHandler(urllib2.HTTPHandler):
    """Subclass of `urllib2.HTTPHandler` that uses
    StreamingHTTPConnection as its http connection class."""

    handler_order = urllib2.HTTPHandler.handler_order - 1

    def http_open(self, req):
        """Open a StreamingHTTPConnection for the given request"""
        return self.do_open(StreamingHTTPConnection, req)

    def http_request(self, req):
        """Handle a HTTP request.  Make sure that Content-Length is specified
        if we're using an interable value"""
        # Make sure that if we're using an iterable object as the request
        # body, that we've also specified Content-Length
        if req.has_data():
            data = req.get_data()
            if hasattr(data, 'read') or hasattr(data, 'next'):
                if not req.has_header('Content-length'):
                    raise ValueError(
                            "No Content-Length specified for iterable body")
        return urllib2.HTTPHandler.do_request_(self, req)

if hasattr(httplib, 'HTTPS'):
    class StreamingHTTPSConnection(_StreamingHTTPMixin,
            httplib.HTTPSConnection):
        """Subclass of `httplib.HTTSConnection` that overrides the `send()`
        method to support iterable body objects"""

    class StreamingHTTPSHandler(urllib2.HTTPSHandler):
        """Subclass of `urllib2.HTTPSHandler` that uses
        StreamingHTTPSConnection as its http connection class."""

        handler_order = urllib2.HTTPSHandler.handler_order - 1

        def https_open(self, req):
            return self.do_open(StreamingHTTPSConnection, req)

        def https_request(self, req):
            # Make sure that if we're using an iterable object as the request
            # body, that we've also specified Content-Length
            if req.has_data():
                data = req.get_data()
                if hasattr(data, 'read') or hasattr(data, 'next'):
                    if not req.has_header('Content-length'):
                        raise ValueError(
                                "No Content-Length specified for iterable body")
            return urllib2.HTTPSHandler.do_request_(self, req)


def get_handlers():
    handlers = [StreamingHTTPHandler, StreamingHTTPRedirectHandler]
    if hasattr(httplib, "HTTPS"):
        handlers.append(StreamingHTTPSHandler)
    return handlers
    
def register_openers():
    """Register the streaming http handlers in the global urllib2 default
    opener object.

    Returns the created OpenerDirector object."""
    opener = urllib2.build_opener(*get_handlers())

    urllib2.install_opener(opener)

    return opener

########NEW FILE########
__FILENAME__ = preferences
import gtk
import os
import sys

import liblookit
import lookitconfig

from uploader import PROTO_LIST as CONNECTION_TYPES

WIDGETS = ( (bool, 'trash', 'General', 'trash'),
            (bool, 'shortenurl', 'General', 'shortenurl'),
            (bool, 'autostart', 'General', 'autostart'),
            (bool, 'force_fallback', 'General', 'force_fallback'),
            (int, 'delayscale', 'General', 'delay'),
            (file, 'savedir', 'General', 'savedir'),
            (str, 'capturearea', 'Hotkeys', 'capturearea'),
            (str, 'capturescreen', 'Hotkeys', 'capturescreen'),
            (str, 'capturewindow', 'Hotkeys', 'capturewindow'),
            (str, 'server', 'Upload', 'hostname'),
            (str, 'username', 'Upload', 'username'),
            (str, 'password', 'Upload', 'password'),
            (int, 'port', 'Upload', 'port'),
            (str, 'ssh_key_file', 'Upload', 'ssh_key_file'),
            (str, 'directory', 'Upload', 'directory'),
            (str, 'url', 'Upload', 'url'),
            (None, 'combobox', 'Upload', 'type'),
)

class PreferencesDialog:
    def __init__(self):
        try:
            self.builder = gtk.Builder()
            datadir = liblookit.get_data_dir()
            xmlfile = os.path.join(datadir, 'preferences.xml')
            self.builder.add_from_file(xmlfile)
        except Exception as e:
            print e
            sys.exit(1)

        connections = gtk.ListStore(str)
        for connection in CONNECTION_TYPES:
            connections.append([connection])
        cell = gtk.CellRendererText()
        combobox = self.builder.get_object('combobox')
        combobox.set_model(connections)
        combobox.pack_start(cell)
        combobox.add_attribute(cell, 'text', 0)
        combobox.set_active(0)

        self.config = lookitconfig.LookitConfig()
        self.builder.connect_signals(self)

    def run(self):
        for (kind, name, section, option) in WIDGETS:
            widget = self.builder.get_object(name)
            if kind == bool:
                value = self.config.getboolean(section, option)
                widget.set_active(value)
            elif kind == int:
                value = self.config.getint(section, option)
                widget.set_value(value)
            elif kind == str:
                value = self.config.get(section, option)
                widget.set_text(value)
            elif kind == file:
                value = self.config.get(section, option)
                widget.set_filename(value)
            elif kind == None:
                value = self.config.get(section, option)
                widget.set_active(CONNECTION_TYPES.index(value))

        self.builder.get_object('dialog').run()

    def on_proto_changed(self, widget, data=None):
        proto = widget.get_active_text()

        user_pass = ('username', 'password')
        server_port_dir_url = ('server', 'port', 'directory', 'url')
        all_fields = user_pass + server_port_dir_url

        # Set to False as only used for SSH.
        self.builder.get_object('ssh_key_file').set_sensitive(False)

        if proto in ['FTP', 'SSH']:
            for field in all_fields:
                self.builder.get_object(field).set_sensitive(True)
        elif proto in ['CloudApp']:
            for field in user_pass:
                self.builder.get_object(field).set_sensitive(True)
            for field in server_port_dir_url:
                self.builder.get_object(field).set_sensitive(False)
	elif proto in ['HTTP']:
		for field in all_fields:
			self.builder.get_object(field).set_sensitive(False)
		self.builder.get_object('url').set_sensitive(True)
        else:
            for field in all_fields:
                self.builder.get_object(field).set_sensitive(False)

        if proto == 'FTP':
            self.builder.get_object('port').set_value(21)
        elif proto == 'SSH':
            self.builder.get_object('ssh_key_file').set_sensitive(True)
            self.builder.get_object('port').set_value(22)
	elif proto == 'HTTP':
	    self.builder.get_object('port').set_value(80)

    def on_dialog_response(self, widget, data=None):
        if data != 1:
            widget.destroy()
            return
        for (kind, name, section, option) in WIDGETS:
            field = self.builder.get_object(name)
            if kind == bool:
                value = field.get_active()
            elif kind == int:
                value = int(field.get_value())
            elif kind == str:
                value = field.get_text()
            elif kind == file:
                value = field.get_filename()
            elif kind == None:
                value = field.get_active_text()
            self.config.set(section, option, value)
        self.config.save()
        widget.destroy()

if __name__ == '__main__':
    dialog = PreferencesDialog()
    dialog.run()

########NEW FILE########
__FILENAME__ = screencapper
import gtk
import time

import lookitconfig

def capture_screen():
    if lookitconfig.LookitConfig().getint('General', 'delay') == 0:
        time.sleep(1)
    root = gtk.gdk.get_default_root_window()
    size = root.get_geometry()
    pixbuf = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, False,
                     8, size[2], size[3])
    pixbuf.get_from_drawable(root,
                      root.get_colormap(),
                      0, 0, 0, 0, size[2],
                      size[3])
    return pixbuf

def capture_active_window():
    if lookitconfig.LookitConfig().getint('General', 'delay') == 0:
        time.sleep(1)
    root = gtk.gdk.get_default_root_window()
    window = gtk.gdk.screen_get_default().get_active_window()
    size = window.get_geometry()
    origin = window.get_root_origin()
    # Calculating window decorations offset
    delta_x = window.get_origin()[0] - window.get_root_origin()[0]
    delta_y = window.get_origin()[1] - window.get_root_origin()[1]
    size_x = size[2] + delta_x
    size_y = size[3] + delta_y
    pixbuf = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, False,
                     8, size_x, size_y)
    pixbuf.get_from_drawable(root,
                      root.get_colormap(),
                      origin[0], origin[1], 0, 0, size_x, size_y)
    return pixbuf

def capture_selection(rect):
    root = gtk.gdk.get_default_root_window()
    pixbuf = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB,
                     False, 8, rect[2], rect[3])
    pixbuf.get_from_drawable(root,
                      root.get_colormap(),
                      rect[0], rect[1], 0, 0,
                      rect[2], rect[3])
    return pixbuf

########NEW FILE########
__FILENAME__ = selector
import cairo
import gtk
import gtk.gdk

import screencapper

class Selector:
    def __init__(self):
        self.x = 0
        self.y = 0
        self.dx = 0
        self.dy = 0

        self.is_composited = False
        self.supports_alpha = False
        self.mouse_down = False

        self.pixbuf = None

        self.overlay = gtk.Window(gtk.WINDOW_POPUP)

        self.overlay.set_app_paintable(True)
        self.overlay.set_decorated(False)

        self.overlay.add_events(gtk.gdk.POINTER_MOTION_MASK |
                                gtk.gdk.BUTTON_PRESS_MASK |
                                gtk.gdk.BUTTON_RELEASE_MASK |
                                gtk.gdk.KEY_PRESS_MASK)

        self.overlay.connect('expose-event',            self.expose)
        self.overlay.connect('screen-changed',          self.screen_changed)
        self.overlay.connect('realize',                 self.realize)
        self.overlay.connect('show',                    self.on_show)
        self.overlay.connect('button-press-event',      self.button_pressed)
        self.overlay.connect('button-release-event',    self.button_released)
        self.overlay.connect('motion-notify-event',     self.motion_notify)
        self.overlay.connect('key-press-event',         self.key_pressed)

    def expose(self, widget, event=None):
        cr = widget.window.cairo_create()
        if self.is_composited and self.supports_alpha and not self.ffb:
            cr.set_operator(cairo.OPERATOR_CLEAR)
            cr.set_source_rgba(0, 0, 0, 0)
            cr.paint()
            if self.mouse_down:
                cr.rectangle(self.x, self.y, self.dx, self.dy)
            
        else:
            cr.set_operator(cairo.OPERATOR_SOURCE)
            if self.pixbuf is None:
                self.pixbuf = screencapper.capture_screen()
                cr.set_source_pixbuf(self.pixbuf, 0, 0)
                cr.paint()

            if self.mouse_down:
                cr.rectangle(self.x, self.y, self.dx, self.dy)
                cr.stroke()
        
        return False

    def undraw_rect(self, widget):
        cr = widget.window.cairo_create()
        cr.set_source_pixbuf(self.pixbuf, 0, 0)
        cr.rectangle(self.x, self.y, self.dx, self.dy)
        cr.stroke()

    def screen_changed(self, widget, old_screen=None):
        screen = widget.get_screen()
        self.is_composited = screen.is_composited()
        widget.move(0, 0)
        widget.resize(screen.get_width(), screen.get_height())

        colormap = screen.get_rgba_colormap()
        if colormap == None:
            colormap = screen.get_rgb_colormap()
            self.supports_alpha = False
        else:
            self.supports_alpha = True

        widget.set_colormap(colormap)

        return True

    def realize(self, widget):
        widget.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.CROSS))

    def on_show(self, widget):
        gtk.gdk.keyboard_grab(widget.window)

    def button_pressed(self, widget, event):
        self.mouse_down = True
        self.x = event.x
        self.y = event.y

    def button_released(self, widget, event):
        self.mouse_down = False
        gtk.main_quit()
        self.overlay.destroy()

    def motion_notify(self, widget, event):
        if self.mouse_down:
            if not self.is_composited or self.ffb:
                self.undraw_rect(widget)
            self.dx = event.x - self.x
            self.dy = event.y - self.y

            self.expose(self.overlay)

    def key_pressed(self, widget, event):
        if event.keyval == gtk.gdk.keyval_from_name('Escape'):
            self.button_released(widget, event)
        else:
            return False

    def selection_rectangle(self):
        if self.dx == 0 or self.dy == 0:
            return None
        if self.dx < 0:
            self.x += self.dx
            self.dx = -self.dx
        if self.dy < 0:
            self.y += self.dy
            self.dy = -self.dy
        return int(self.x), int(self.y), int(self.dx), int(self.dy)


    def get_selection(self, ffb=False):
        self.ffb = ffb
        self.screen_changed(self.overlay)
        self.overlay.show_all()
        gtk.main()
        return self.selection_rectangle()

if __name__ == '__main__':
    # For testing purposes only
    print Selector().get_selection()

########NEW FILE########
__FILENAME__ = uploader
import os
import sys
import gtk
import ftplib
import pynotify
import shutil
import socket
import tempfile
import time
import urllib
import urlparse

PROTO_LIST = ['None']

try:
	import ftplib
	PROTO_LIST.append('FTP')
except ImportError:
	print 'FTP support not found'

try:
	import paramiko
	PROTO_LIST.append('SSH')
except ImportError:
	print 'SFTP support not found'

try:
	import ubuntuone
	import ubuntuone.storageprotocol
	# PROTO_LIST.append('Ubuntu One') # Not yet supported
except ImportError:
	print 'Ubuntu One support not found'

try:
    import imgur
    PROTO_LIST.append('Imgur')
except ImportError:
    print 'Imgur support not available'

try:
	import pycurl
	import re
	PROTO_LIST.append('Omploader')
	PROTO_LIST.append('HTTP')
except ImportError:
	print 'Omploader support not available'
	print 'HTTP support not available'

try:
    import cloud
    if cloud.POSTER and cloud.ORDERED_DICT:
        PROTO_LIST.append('CloudApp')
    else:
        print 'CloudApp support not available'
except ImportError:
    print 'CloudApp support not available'

import liblookit
import lookitconfig

class OmploaderUploader:
	def __init__(self):
		self.response = ''
		self.mapping = {}

	def curl_response(self, buf):
		self.response = self.response + buf

	def upload(self, image):
		c = pycurl.Curl()
		values = [	('file1', (c.FORM_FILE, image))]
		c.setopt(c.URL, 'http://ompldr.org/upload')
		c.setopt(c.HTTPPOST, values)
		c.setopt(c.WRITEFUNCTION, self.curl_response)

		c.perform()
		c.close()

		m = re.findall("v\w+", self.response)
		self.mapping['original_image'] = "http://ompldr.org/%s" % m[2]


class HTTPUploader:
	def __init__(self):
		self.response = ''

	def curl_response(self, buf):
		self.response = self.response + buf

	def upload(self, image, url):
		c = pycurl.Curl()
		values = [	('file', (c.FORM_FILE, image))]
		c.setopt(c.URL, url)
		c.setopt(c.HTTPPOST, values)
		c.setopt(c.WRITEFUNCTION, self.curl_response)

		try:
			c.perform()
		except pycurl.error:
			c.close()
			return False, "There was an error during HTTP upload."

		c.close()

		return True, self.response

def get_proto_list():
	return PROTO_LIST

def upload_file_ftp(f, hostname, port, username, password, directory, url):
	i = open(f, 'rb')

	try:
		ftp = ftplib.FTP()
		ftp.connect(hostname, port)
		ftp.login(username, password)
		ftp.cwd(directory)
		ftp.storbinary('STOR ' + os.path.basename(f), i)
		ftp.quit()
	except Exception as error:
		return False, 'Error occured during FTP upload'

	i.close()

	return True, None

def upload_file_http(f, url):
	i = HTTPUploader()

	status, data = i.upload(f, url)

	if status:
		obj = {}
		obj['original_image'] = data;

		return True, obj
	else:
		return False, data

def upload_file_sftp(f, hostname, port, username, password, ssh_key_file, directory, url):
    try:
        # Debug info.
        #paramiko.util.log_to_file('paramiko.log')

        # Paramiko needs 'None' for these two, probably a bad place to put them
        # but I'm lazy.
        if password == '':
            password = None
        if ssh_key_file == '':
            ssh_key_file = None

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(hostname, port, username, password, key_filename=ssh_key_file)
        sftp = client.open_sftp()
        sftp.chdir(directory)
        sftp.put(f, os.path.basename(f))
    except socket.gaierror:
        return False, 'Name or service not known'
    except paramiko.AuthenticationException:
        return False, 'Authentication failed'
    except IOError:
        return False, 'Destination directory does not exist'
    return True, None

def upload_file_omploader(f):
	if not 'Omploader' in PROTO_LIST:
		print 'Error: Omploader not supported'
	i = OmploaderUploader()
	i.upload(f)
	if not 'error_msg' in i.mapping:
		return True, i.mapping
	else:
		return False, i.mapping.get('error_msg')

def upload_file_imgur(f):
	if not 'Imgur' in PROTO_LIST:
		print 'Error: Imgur not supported'
	i = imgur.ImgurUploader()
	i.upload(f)
	if not 'error_msg' in i.mapping:
		return True, i.mapping
	else:
		return False, i.mapping.get('error_msg')

def upload_file_cloud(f, username, password):
    if not 'CloudApp' in PROTO_LIST:
        print 'Error: CloudApp not supported'
    try:
        mycloud = cloud.Cloud()
        mycloud.auth(username, password)
        result = mycloud.upload_file(f)
        data = {'original_image': result['url']}
        return True, data
    except cloud.CloudException as e:
        return False, e.message

def upload_pixbuf(pb):
    if pb is not None:
        ftmp = tempfile.NamedTemporaryFile(suffix='.png', prefix='', delete=False)
        pb.save_to_callback(ftmp.write, 'png')
        ftmp.flush()
        ftmp.close()
        return upload_file(ftmp.name)

def upload_file(image, existing_file=False):
    config = lookitconfig.LookitConfig()

    proto = config.get('Upload', 'type')
    # Temporary disable upload
    if not config.getboolean('Upload', 'enableupload'):
        proto = 'None'

    if proto == 'None':
        success = True
        data = False
    elif proto == 'SSH':
        success, data = upload_file_sftp(image,
                    config.get('Upload', 'hostname'),
                    int(config.get('Upload', 'port')),
                    config.get('Upload', 'username'),
                    config.get('Upload', 'password'),
                    config.get('Upload', 'ssh_key_file'),
                    config.get('Upload', 'directory'),
                    config.get('Upload', 'url'),
                    )
    elif proto == 'HTTP':
	success, data = upload_file_http(image, config.get('Upload', 'URL'))
    elif proto == 'FTP':
        success, data = upload_file_ftp(image,
                    config.get('Upload', 'hostname'),
                    int(config.get('Upload', 'port')),
                    config.get('Upload', 'username'),
                    config.get('Upload', 'password'),
                    config.get('Upload', 'directory'),
                    config.get('Upload', 'url'),
                    )
    elif proto == 'Omploader':
        success, data = upload_file_omploader(image)
        try:
            f = open(liblookit.LOG_FILE, 'ab')
            f.write(time.ctime() + ' Uploaded screenshot to Omploader: ' + data['original_image'] + '\n')
        except IOError, e:
            pass
        finally:
            f.close()
    elif proto == 'Imgur':
        success, data = upload_file_imgur(image)
        # Backwards compatibility
        data['original_image'] = data['link']
        try:
            f = open(liblookit.LOG_FILE, 'ab')
            f.write(time.ctime() + ' Uploaded screenshot to Imgur: ' + data['original_image'] + '\n')
        except IOError, e:
            pass
        finally:
            f.close()
    elif proto == 'CloudApp':
        success, data = upload_file_cloud(image,
                    config.get('Upload', 'username'),
                    config.get('Upload', 'password'))
    else:
        success = False
        data = "Error: no such protocol: {0}".format(proto)

    if not success:
        liblookit.show_notification('Lookit', 'Error: ' + data)
        return

    if data:
        url = data['original_image']
    else:
        url = urlparse.urljoin(config.get('Upload', 'url'),
            os.path.basename(image))

    if config.getboolean('General', 'shortenurl') and proto != None:
        url = urllib.urlopen('http://is.gd/api.php?longurl={0}'
                        .format(url)).readline()
    if not existing_file:
        if config.getboolean('General', 'trash'):
            os.remove(os.path.abspath(image))
        else:
            try:
                timestamp = time.strftime('%Y-%m-%d_%H-%M-%S')
                filename = timestamp + '.png'
                destination = os.path.join(config.get('General', 'savedir'), filename)
                i = 0
                while os.path.exists(destination):
                    filename = timestamp + '_' + str(i) + '.png'
                    destination = os.path.join(config.get('General', 'savedir'), filename)
                    i += 1
                shutil.move(image, destination)
                image = destination
            except IOError:
                print 'Error moving file'

    clipboard = gtk.clipboard_get()
    clipboard.set_text(url)
    clipboard.store()

    if proto == 'None':
        if config.getboolean('General', 'trash'):
            liblookit.show_notification('Lookit', 'Error: No upload type selected')
        else:
            liblookit.show_notification('Lookit', 'Image saved: ' + image)
            return image
    else:
        liblookit.show_notification('Lookit', 'Upload complete: ' + url)
        return url


########NEW FILE########
