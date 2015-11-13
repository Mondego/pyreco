__FILENAME__ = engine
# -*- coding: utf-8 -*-

# Copyright (C) 2010 The Tegaki project contributors
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

# Contributors to this file:
# - Mathieu Blondel

import gobject
import gtk

import ibus

from tegakigtk.recognizer import SmartRecognizerWidget

class Engine(ibus.EngineBase):

    def __init__(self, bus, object_path):
        super(Engine, self).__init__(bus, object_path)
        self._window = None

    # See ibus.EngineBase for a list of overridable methods

    def enable(self):
        if not self._window:
            self._window = gtk.Window()
            self._window.set_title("Tegaki")
            self._window.set_position(gtk.WIN_POS_CENTER_ALWAYS)
            self._window.set_accept_focus(False)
            rw = SmartRecognizerWidget()
            self._window.add(rw)

            self._window.show_all()

            self._window.connect("delete-event", self._on_close)
            rw.connect("commit-string", self._on_commit)

    def disable(self):
        if self._window:
            self._window.destroy()
            self._window = None

    def do_destroy(self):
        self.disable()
        super(ibus.EngineBase, self).do_destroy()

    def _on_close(self, *args):
        self.disable()

    def _on_commit(self, widget, string):
        self.commit_text(ibus.Text(string))


########NEW FILE########
__FILENAME__ = factory
# vim:set et sts=4 sw=4:
#
# ibus-tmpl - The Input Bus template project
#
# Copyright (c) 2007-2008 Huang Peng <shawn.p.huang@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

import ibus
import engine


class EngineFactory(ibus.EngineFactoryBase):
    def __init__(self, bus):
        self.__bus = bus
        super(EngineFactory, self).__init__(self.__bus)

        self.__id = 0

    def create_engine(self, engine_name):
        print engine_name
        if engine_name == "tegaki":
            self.__id += 1
            return engine.Engine(self.__bus, "%s/%d" % \
                ("/org/freedesktop/IBus/Tegaki/Engine", self.__id))

        return super(EngineFactory, self).create_engine(engine_name)


########NEW FILE########
__FILENAME__ = main
# -*- coding: utf-8 -*-

# Copyright (C) 2010 The Tegaki project contributors
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

# Contributors to this file:
# - Mathieu Blondel

import os
import sys
import getopt
import ibus
import factory
import gobject

from __init__ import *

class IMApp:
    def __init__(self, exec_by_ibus):
        self.__component = ibus.Component(BUS_NAME,
                                          BUS_DESCRIPTION,
                                          VERSION,
                                          LICENSE,
                                          AUTHOR,
                                          HOMEPAGE)

        self.__component.add_engine(ENGINE_NAME,
                                    ENGINE_LONG_NAME,
                                    ENGINE_DESCRIPTION,
                                    LANGUAGE,
                                    LICENSE,
                                    AUTHOR,
                                    ICON,
                                    LAYOUT)


        self.__mainloop = gobject.MainLoop()
        self.__bus = ibus.Bus()
        self.__bus.connect("disconnected", self.__bus_disconnected_cb)
        self.__factory = factory.EngineFactory(self.__bus)
        if exec_by_ibus:
            self.__bus.request_name(BUS_NAME, 0)
        else:
            self.__bus.register_component(self.__component)

    def run(self):
        self.__mainloop.run()

    def __bus_disconnected_cb(self, bus):
        self.__mainloop.quit()


def launch_engine(exec_by_ibus):
    IMApp(exec_by_ibus).run()

def print_help(out, v = 0):
    print >> out, "-i, --ibus             executed by ibus."
    print >> out, "-h, --help             show this message."
    print >> out, "-d, --daemonize        daemonize ibus"
    sys.exit(v)

def main():
    exec_by_ibus = False
    daemonize = False

    shortopt = "ihd"
    longopt = ["ibus", "help", "daemonize"]

    try:
        opts, args = getopt.getopt(sys.argv[1:], shortopt, longopt)
    except getopt.GetoptError, err:
        print_help(sys.stderr, 1)

    for o, a in opts:
        if o in ("-h", "--help"):
            print_help(sys.stdout)
        elif o in ("-d", "--daemonize"):
            daemonize = True
        elif o in ("-i", "--ibus"):
            exec_by_ibus = True
        else:
            print >> sys.stderr, "Unknown argument: %s" % o
            print_help(sys.stderr, 1)

    if daemonize:
        if os.fork():
            sys.exit()

    launch_engine(exec_by_ibus)

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = scimtegaki
# -*- coding: utf-8 -*-

# Copyright (C) 2009 The Tegaki project contributors
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

# Contributors to this file:
# - Mathieu Blondel

import scim
import gobject
import gtk

from gettext import dgettext
_ = lambda a : dgettext ("scim-tegaki", a)
N_ = lambda x : x

from tegakigtk.recognizer import SmartRecognizerWidget

VERSION = '0.1'

class TegakiHelper(scim.HelperAgent):

    def __init__(self, helper_info):
        self._helper_info = helper_info
        scim.HelperAgent.__init__(self)

    def run(self, uuid, config, display):
        self.config = config
        self._uuid = uuid
        self._display = display
        self._init_agent()
        self._create_ui()
        #self.load_config(config)
        gtk.main()
        self.config.flush()
        self.reload_config()
        self.close_connection()

    def _create_ui (self):
        self._window = gtk.Window()
        self._window.set_title("Tegaki")
        self._window.set_position(gtk.WIN_POS_CENTER)
        self._window.set_accept_focus(False)
        rw = SmartRecognizerWidget()
        self._window.add(rw)
        self._window.show_all()

        self._window.connect("destroy", self._on_destroy)
        rw.connect("commit-string", self._on_commit)

    def _on_destroy(self, window):
        gtk.main_quit()

    def _on_commit(self, widget, string):
        self.commit_string(-1, "", string)

    def _init_properties (self):
        prop = scim.Property("/Tegaki", _("Tegaki"),
                             self._helper_info[2],
                             _("Show/Hide Tegaki."))

        self.register_properties((prop, ))

    def _init_agent(self):
        fd = self.open_connection(self._helper_info,
                                  self._display)
        if fd >= 0:
            self._init_properties()

            condition = gobject.IO_IN | gobject.IO_ERR | gobject.IO_HUP
            gobject.io_add_watch(fd, condition, self.on_agent_event)

    def on_agent_event(self, fd, condition):
        if condition == gobject.IO_IN:
            while self.has_pending_event():
                self.filter_event()
            return True
        elif condition == gobject.IO_ERR or condition == gobject.IO_HUP:
            gtk.main_quit()
            return False
        
        return False

    def trigger_property(self, ic, uuid, prop):
        if prop == "/Tegaki":
            if self._window.get_property("visible"):
                self._xpos, self._ypos = self._window.get_position()
                self._window.hide()
            else:
                self._window.move(self._xpos, self._ypos)
                self._window.show()

if __name__ == "__main__":
    class CC:
        def __init__ (self):
            pass

        def read (self, name, v):
            return v
        def write (self, name, v):
            pass
        def flush(self):
            pass

    __UUID__ = "6937480c-e1a4-11dd-b959-080027da9e6f"
    helper_info = (__UUID__, "", "", "", 1)
    
    TegakiHelper(helper_info).run (__UUID__, CC(), ":0.0")
########NEW FILE########
__FILENAME__ = settings
# Sample Django settings for tegakidb project.
# Copy your own to ../../tegakidb/ and edit it with your personal settings.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

import os
TEGAKIDB_ROOT = '/path/to/hwr/tegaki-db'
WEBCANVAS_ROOT = '/path/to/hwr/tegaki-webcanvas/webcanvas'


DATABASE_ENGINE = 'sqlite3'     # 'postgresql_psycopg2', 'postgresql',
                                # 'mysql', 'sqlite3' or 'ado_mssql'.
DATABASE_NAME = os.path.join(TEGAKIDB_ROOT, 'db.db') # Or path to database file if using sqlite3
DATABASE_USER = ''              # Not used with sqlite3
DATABASE_PASSWORD = ''          # Not used with sqlite3
DATABASE_HOST = ''              # Set to empty string for localhost. 
                                # Not used with sqlite3.
DATABASE_PORT = ''              # Set to empty string for localhost. 
                                # Not used with sqlite3.       

# Local time zone for this installation. Choices can be found here:
# http://www.postgresql.org/docs/8.1/static/datetime-keywords.html#DATETIME-TIMEZONE-SET-TABLE
# although not all variations may be possible on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Chicago'

# Language code for this installation. All choices can be found here:
# http://www.w3.org/TR/REC-html40/struct/dirlang.html#langcodes
# http://blogs.law.harvard.edu/tech/stories/storyReader$15
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = os.path.join(TEGAKIDB_ROOT, 'data/www/')

# URL that handles the media served from MEDIA_ROOT.
# Example: "http://media.lawrence.com"
# This should of course point to the actual domain using to host (see usage
# guide for setting up apache)
MEDIA_URL = 'http://localhost:8000/static/'

#if you are hosting site like mydomain.com/tegaki/
#set BASE_URL = 'tegaki/'
#or for http://db.tegaki.com/
#set BASE_URL = ''
BASE_URL = ''

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/static/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'secret-key'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    "django.core.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "django.core.context_processors.request",
    "dojango.context_processors.config",
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.middleware.doc.XViewMiddleware',
    'dojango.middleware.DojoCollector',
)

AUTH_PROFILE_MODULE = 'users.TegakiUser'

DOJANGO_DATAGRID_ACCESS = (
    'users.TegakiUser',
    'hwdb.HandwritingSample',
)

DOJANGO_DOJO_THEME="soria"

ROOT_URLCONF = 'tegakidb.urls'

LOGIN_URL =  '/%slogin/' % BASE_URL
LOGIN_REDIRECT_URL = '/%s' % BASE_URL

TEMPLATE_DIRS = (
    os.path.join(TEGAKIDB_ROOT, 'data/templates/'),
)

FIXTURE_DIRS = (
    os.path.join(TEGAKIDB_ROOT, 'data/fixtures/'),
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.admin',

    'dojango',
                
    'tegakidb.hwdb',    
    'tegakidb.news',
    'tegakidb.users',
    'tegakidb.utils',
)

########NEW FILE########
__FILENAME__ = forms
#from django import forms
from dojango import forms

from tegakidb.users.models import TegakiUser
from django.contrib.auth.models import User
from tegakidb.hwdb.models import *
from tegakidb.utils.models import *

FILTERS = (
    (u"\u4e00-\u9fff", 'CJK'),
#    ('Chinese'),
#    ('Japanese'),
#    ('Korean'),
    )



#form for editing tegaki users
class CharacterSetForm(forms.ModelForm):
    """
    We use this form to create Character set objects, and update them.
    It creates the form from the CharacterSet model and adds the filter and range fields
    as a form of input.
    Filter takes in any input text and filters out (by default CJK) characters.
    Range takes in a range of the format
     e.g. "8,A..F,11"

    """
    filter_text = forms.CharField(required=False, widget=forms.widgets.Textarea(), label="Enter any text and the text will be filtered")
    filter = forms.ChoiceField(required=False, label="A regex for filtering submission text", choices=FILTERS)
    range = forms.CharField(required=False, widget=forms.widgets.Textarea(), label="Enter a range like: 8,10..15,17 is equivalent to 8,10,11,12,13,14,15,17")
    class Meta:
        model = CharacterSet
        exclude = ('id','user', 'characters')

    def __init__(self, *args, **kwargs):
        super(CharacterSetForm, self).__init__(*args, **kwargs)
        #self.fields['lang'].label = "Language"
        try:
            self.fields['lang'].label = "Language"
        except:
            pass

    def save(self, *args, **kwargs):
        m = super(CharacterSetForm, self).save(commit=False, *args, **kwargs)
        #print self.cleaned_data['range'], "___", self.cleaned_data['filter']
        if self.cleaned_data['range'] != "":
            m.set = CharacterSet.get_set_from_range_string(self.cleaned_data['range'])
            #print "in range:", m.set
            m.save_string()
        elif self.cleaned_data['filter_text'] != "":
            f = self.cleaned_data['filter']
            m.set = CharacterSet.get_set_with_filter(self.cleaned_data['filter_text'],f)
            #print "in filter:", m.set, f
            m.save_string()
        m.save()
        return m

########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-
from django.db import models
from django.contrib import admin
from django.db.models.signals import pre_save
from django.utils import simplejson

from django.contrib.auth.models import User
from tegakidb.users.models import TegakiUser
from tegakidb.utils.models import Language

import random
#from random import randint
from datetime import datetime
import re
sets = set #wanna use set as a class variable

class CharacterSet(models.Model):
    name = models.CharField(max_length=30)
    lang = models.ForeignKey(Language)
    description = models.CharField(max_length=255)
    # characters is a string representation of character code lists
    ## and/or character code ranges.
    ## e.g. 8,10..15,17 is equivalent to 8,10,11,12,13,14,15,17
    # internally we won't use ranges, its more convenient to use built-in sets
    characters = models.TextField()
    user = models.ForeignKey(User,blank=True, null=True)
    public = models.BooleanField(default=True) 
    set = None
    def __init__(self, *args, **kwargs):
        super(CharacterSet, self).__init__(*args, **kwargs)
        #print "in init"
        #print self.characters, len(self.characters)
        #print self.set
        try: 
            self.set = sets(simplejson.loads(self.characters))
        except:
            #print "no json yet"
            pass
        #print self.set
        #print "leaving init"

    @staticmethod
    def get_array_from_string(s):
        """
        Returns an an array representation of the string representation.
        e.g. "8,A..F,11" => [0x8, [0x10,0xF], 0x11]

        raises ValueError if the input is not valid.
        """
        if not isinstance(s, str) and not isinstance(s, unicode):
            raise ValueError

        ret = []
        for ele in s.strip().split(","):
            arr = [int(x, 16) for x in ele.strip().split("..")]
            if len(arr) == 1:
                ret.append(arr[0])
            else:
                ret.append(arr)
        return ret

    @staticmethod
    def get_set_from_range_string(s):
        """
        Returns a set representation of the string representation.
        e.g. "8,A..F,11" => Set([0x8, 0x10, 0xE, 0xF, 0x11])

        raises ValueError if the input is not valid.
        """
        if not isinstance(s, str) and not isinstance(s, unicode):
            raise ValueError

        retset = sets()
        for ele in s.strip().split(","):
            arr = [int(x, 16) for x in ele.strip().split("..")]
            if len(arr) == 1:
                retset.add(arr[0])
            else:
                for i in range(arr[0], arr[1]):
                    retset.add(i)
        return retset


    @staticmethod
    def get_set_with_filter(s, filter=u"\u0400-\u9fff"):
        """
        Returns an array of characters (unicode ordinals) found in the input string
        filtered by the given filter.
        default usage
        CharacterSet.get_set_with_filter(u"我是一个人。你也是一个好人")
        will return
        [19968, 20320, 20010, 26159, 25105, 20154, 22909, 20063]
        the default filter will grab anything in the CJK codepoints
        """
        matches = re.findall(u"[%s]+" % filter, s)
        range = sets()
        #print "in set with filter", u"[%s]+" % filter
        #print matches
        for m in matches:
            #print m.encode("utf-8")
            #print ord(m)
            for c in m:
                range.add(ord(c))
        #print range
        return range
        
    def save_string(self):
        """
        Saves the current set into the string representation
        """
        #print "saving a string:", self.set
        self.characters = unicode(repr(self.set)[4:-1])

    def display_characters(self):
        """
        Display all the characters in the set
        """
        s = ""
        for c in self.set:
            s = s + "%s,"%unichr(c)
        s = s[:-1]
        return s

    def __subtract__(first, second):
        """
        Subtract two CharacterSets
        """
        return first.difference(second)
        #if not self.set:
        #    self.set = CharacterSet.get_set_from_string(self.characters)

        #self.set = self.set.difference(other_set)
        #self.save_string()
        #for ele in other_set:
        #    if isinstance(ele, int):
        #        if self.contains(ele):
        #            self.remove_element(ele)

    def __add__(first, second):
        """
        Add two CharacterSets
        """
        return first.union(second)

    def contains(self, char_code):
        """
        Returns whether a given character code belongs to the character set
        or not.
        """
        #if not self.arr:
        #    self.arr = CharacterSet.get_set_from_string(self.characters)
        return char_code in self.set

        # FIXME: replaces linear search with binary search
        #        (get_array_from_string must return a sorted array)
        """for ele in arr:
            if isinstance(ele, int): # individual character code
                if ele == char_code:
                    return True
            elif isinstance(ele, list): # character code range
                #if ele[0] <= char_code and char_code <= ele[1]:
                #    return True
                return in_range(ele, list)
        return False"""

    def __len__(self):
        """
        Returns the number of characters in the character set.
        """
        return len(self.set)
        #if not self.arr:
        #   arr = CharacterSet.get_set_from_string(self.characters)
        """
        length = 0
        for ele in arr:
            if isinstance(ele, int): # individual character code
                length += 1
            elif isinstance(ele, list): # character code range
                length += ele[1] - ele[0] + 1
        return length
        """

    #def get_list(self):
        """
        Returns the character set as a python list
        """
        #return CharacterSet.get_array_from_string(self.characters)


    def get_random(self):
        """
        Returns a random character code from the set.
        Character codes are equally probable.
        """
        #if not self.arr:
        #    self.arr = CharacterSet.get_set_from_string(self.characters)
        #i = randint(0, len(self.set)-1)
        #return repr(self.set)[i]
        return random.sample(self.set, 1)[0]
        """
        n = 0
        for ele in arr:
            if isinstance(ele, int): # individual character code
                if i == n:
                    return ele
                else:
                    n += 1
            elif isinstance(ele, list): # character code range
                range_len = ele[1] - ele[0] + 1
                if n <= i and i <= n + range_len - 1:
                    return ele[0] + i - n
                else:
                    n += range_len
        return None # should never be reached
        """


    def __unicode__(self):
        return self.name

def handle_cs_save(sender, instance, signal, *args, **kwargs):
    """
    Save the set into the character string for the database
    """
    try:
        a = sender.objects.get(pk=instance._get_pk_val())
        a.save_string()
    except:
        print "umm"
    #instance.save_string()
pre_save.connect(handle_cs_save, sender=CharacterSet)

admin.site.register(CharacterSet)

class Character(models.Model):
    lang = models.ForeignKey(Language)
    unicode = models.IntegerField()
    n_correct_handwriting_samples = models.IntegerField(default=0)
    n_handwriting_samples = models.IntegerField(default=0)
    
    def __unicode__(self):      #this is the display name
        return unichr(self.unicode)#.encode("UTF-8") 

    def utf8(self):
        return unichr(self.unicode)

admin.site.register(Character)


#TODO: create choices for each of the enum fields
class HandWritingSample(models.Model):
    character = models.ForeignKey(Character)
    user = models.ForeignKey(User)
    character_set = models.ForeignKey(CharacterSet)
    data = models.TextField()
    compressed = models.IntegerField(default=0) #(NON_COMPRESSED=0, GZIP=1, BZ2=2)
    date = models.DateTimeField(default=datetime.today())
    n_proofread = models.IntegerField(default=0)
    proofread_by = models.ManyToManyField(TegakiUser, related_name='tegaki_user', blank=True)
    device_used = models.IntegerField(default=0) #(MOUSE, TABLET, PDA)
    model = models.BooleanField(default=False)
    stroke_order_incorrect = models.BooleanField(default=False)
    stroke_number_incorrect = models.BooleanField(default=False)
    wrong_stroke = models.BooleanField(default=False)
    wrong_spacing = models.BooleanField(default=False)
    client = models.TextField(blank=True)

    def __unicode__(self):      #this is the display name
        return self.character.__unicode__()

admin.site.register(HandWritingSample)

########NEW FILE########
__FILENAME__ = tests
# -*- coding: utf-8 -*-
import unittest
from tegakidb.hwdb.models import CharacterSet

class CharacterSetTestCase(unittest.TestCase):
    def setUp(self):
        self.ascii = CharacterSet.objects.create(name="ascii", 
                                                 lang="en",
                                                 description="Ascii",
                                                 characters="0..FF")
        self.fake = CharacterSet.objects.create(name="fake", 
                                                lang="en",
                                                description="fake",
                                                characters="9,A..F,11,12")

    def testGetArrayFromString(self):
        self.assertEquals(CharacterSet.get_array_from_string("0..FF"),
                          [[0,0xFF]])
        self.assertEquals(CharacterSet.get_array_from_string("9,A..F,11,12"),
                          [0x9, [0xA,0xF], 0x11, 0x12])
        self.assertEquals(CharacterSet.get_array_from_string(unicode("0..FF")),
                          [[0,0xFF]])
        self.assertEquals(CharacterSet.get_array_from_string(
                              unicode("9,A..F,11,12")),
                          [0x9, [0xA,0xF], 0x11, 0x12])

    def testContains(self):
        for i in range(0,256):
            self.assertTrue(self.ascii.contains(i))
        for i in range(257,500):
            self.assertFalse(self.ascii.contains(i))

        for i in range(0,9):
            self.assertFalse(self.fake.contains(i))
        for i in range(9,16):
            self.assertTrue(self.fake.contains(i))
        self.assertFalse(self.fake.contains(0x10))
        self.assertTrue(self.fake.contains(0x11))
        self.assertTrue(self.fake.contains(0x12))
        for i in range(19, 200):
            self.assertFalse(self.fake.contains(i))

    def testLength(self):
        self.assertEquals(len(self.ascii), 256)
        self.assertEquals(len(self.fake), 9)

    def testGetRandom(self):
        for i in range(1000):
            self.assertTrue(self.ascii.contains(self.ascii.get_random()))

        for i in range(1000):
            self.assertTrue(self.fake.contains(self.fake.get_random()))

########NEW FILE########
__FILENAME__ = urls
from django .conf.urls.defaults import *

urlpatterns = patterns('tegakidb.hwdb.views',
    url(r'^$', 'index', name="hwdb"),
    url(r'^input/$', 'input', name="hwdb-input"),
    url(r'^input_submit/$', 'input_submit', name="hwdb-input-submit"),
    url(r'^recognize/$', 'recognize', name="hwdb-recognize"),
    url(r'^recognize_submit/$', 'recognize_submit', name="hwdb-recognize-submit"),
    url(r'^samples/$', 'samples', name="hwdb-samples"),
    url(r'^view_sample/$', 'view_sample', name="hwdb-view-sample"),
    url(r'^samples_datagrid/$', 'samples_datagrid', name="hwdb-samples-datagrid"),
    url(r'^charsets/$', 'charsets', name="hwdb-charsets"),
    url(r'^charset_datagrid/$', 'charset_datagrid', name="hwdb-charset-datagrid"),
    url(r'^create_charset/$', 'create_charset', name="hwdb-create-charset"),
    url(r'^edit_charset/$', 'edit_charset', name="hwdb-edit-charset"),
    url(r'^select_charset/$', 'select_charset', name="hwdb-select-charset"),
    url(r'^view_charset/$', 'view_charset', name="hwdb-view-charset"),
    url(r'^random_char/$', 'random_char', name="hwdb-random-char"),
)

########NEW FILE########
__FILENAME__ = views
# coding: UTF-8
from django.shortcuts import render_to_response, get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse

from django.conf import settings

#from tegaki.character import Stroke, Point, Writing
from tegaki import character

from tegaki.recognizer import Recognizer

from tegakidb.hwdb.models import *
from tegakidb.hwdb.forms import *
from tegakidb.users.models import TegakiUser

from django.utils import simplejson
from tegakidb.utils import render_to, datagrid_helper

from dojango.util import to_dojo_data
from dojango.decorators import json_response


@render_to('hwdb/index.html')
def index(request):
    return {'utf8': ""}


@login_required
@render_to('hwdb/input.html')
def input(request):
    charset = request.session.get('current_charset', None)
    if charset is None: #if they haven't selected a charset send them to the list
        return HttpResponseRedirect(reverse("hwdb-charsets"))

    #charlist = charset.get_list()
    char = request.GET.get('char', None)
    if char is not None:
        pass
    else:
        char = unichr(charset.get_random())

    return {'char':char}


@login_required         #utilize django's built in login magic
def input_submit(request):
    if settings.DEBUG:
        xml = request.REQUEST['xml']    #if testing we want to be able to pass stuff in with GET request
        utf8 = request.REQUEST['utf8']
    else:
        xml = request.POST['xml']
        utf8 = request.POST['utf8']

    #if request.session.get('tegakiuser', None):
    user = request.user

    char = character.Character()
    char.set_utf8(utf8)
    char.read_string(xml)
    writing = char.get_writing()
    uni = ord(unicode(utf8))

    cs = request.session['current_charset']
    lang = cs.lang

    try:
        tdbChar = Character.objects.get(unicode=uni)  #this is the Character from the database
    except:
        tdbChar = Character(lang=lang, unicode=uni, n_handwriting_samples=1)
        tdbChar.save()
    w = HandWritingSample(character=tdbChar, user=user, data=writing.to_xml(), character_set=cs)  #minimum fields needed to store
    w.save()
    tdbChar.n_handwriting_samples += 1
    tdbChar.save()
    tu = user.get_profile()
    if tu.n_handwriting_samples:
        tu.n_handwriting_samples += 1
    else:
        tu.n_handwriting_samples = 1
    tu.save()
    return HttpResponse("%s" % w.id)

@render_to('hwdb/samples.html')
def samples(request):
    return {}

@login_required
@json_response
def samples_datagrid(request):
    ### need to hand pick fields from TegakiUser, if some are None, need to pass back empty strings for dojo
    dojo_obs = []
    samples, num = datagrid_helper(HandWritingSample, request)
    for s in samples:
        djob = {}
        #'id', 'user__username', 'country', 'lang', 'description', 'n_handwriting_samples'
        djob['id'] = s.id
        djob['character__utf8'] = s.character.utf8()
        djob['character__lang__description'] = s.character.lang.description
        djob['date'] = s.date
        djob['character_set__name'] = s.character_set.name
        djob['user__username'] = s.user.username
        if s.user.get_profile().show_handwriting_samples or request.user == s.user: 
            #only if they publicly display this charset
            #or it's their charset
            dojo_obs += [djob]
        else:
            num = num -1
    return to_dojo_data(dojo_obs, identifier='id', num_rows=num)


@login_required
@render_to('hwdb/view_sample.html')
def view_sample(request):
    id = request.REQUEST.get('id')
    sample = get_object_or_404(HandWritingSample, id=id)
    if sample.user == request.user:
        pass    #no editing of samples for now
    elif not request.user.get_profile().show_handwriting_samples:  
        #check that people don't try to see private samples
        return HttpResponseRedirect(reverse("hwdb-samples"))

    char = character.Character()
    char.set_utf8(sample.character)
    #here we should actually check to see if sample.data is compressed first
    xml = "<?xml version=\"1.0\" encoding=\"UTF-8\"?><character>%s</character>" % sample.data
    char.read_string(xml) #later need to check for compression
    writing = char.get_writing()
    json = writing.to_json()
    print json

    return {'sample':sample, 'char':char.get_utf8(), 'json':json}




@login_required
@render_to('hwdb/create_charset.html')
def create_charset(request):
    if request.method == 'POST':
        form = CharacterSetForm(request.POST)
        if form.is_valid():
            charset = form.save()
            charset.user = request.user #to be changed later where admins can assign users
            charset.save()
            request.session['current_charset'] = charset
            return HttpResponseRedirect(reverse("hwdb-charsets")) #TODO: add support for next redirection
    else:
        form = CharacterSetForm()

    return {'form':form}

@login_required
@render_to('hwdb/create_charset.html')
def create_random_charset(request):
    return {}


@login_required
@render_to('hwdb/charsets.html')
def charsets(request):
    return {}

@login_required
@json_response
def charset_datagrid(request):
    ### need to hand pick fields from TegakiUser, if some are None, need to pass back empty strings for dojo
    dojo_obs = []
    charsets, num = datagrid_helper(CharacterSet, request)
    for c in charsets:
        print c
        djob = {}
        #'id', 'user__username', 'country', 'lang', 'description', 'n_handwriting_samples'
        djob['id'] = c.id
        djob['name'] = c.name
        djob['lang__description'] = c.lang.description
        djob['description'] = c.description
        #print c.get_random()
        djob['random_char'] = unichr(c.get_random())
        #djob['characters'] = c.characters       #might want to do something else for display
        djob['number_of_characters'] = len(c)
        if c.user:
            djob['user__username'] = c.user.username
        if c.public or request.user == c.user:  #only if they publicly display this charset
                                                #or it's their charset
            dojo_obs += [djob]
        else:
            num = num -1
    return to_dojo_data(dojo_obs, identifier='id', num_rows=num)

@login_required
def select_charset(request):
    id = request.REQUEST.get('id')      #checks both POST and GET fields
    request.session['current_charset'] = get_object_or_404(CharacterSet, id=id)
    return HttpResponse(request.session['current_charset'].name)

@login_required
@render_to('hwdb/view_charset.html')
def view_charset(request):
    id = request.REQUEST.get('id')
    cs = get_object_or_404(CharacterSet, id=id)
    if cs.user == request.user:
        return HttpResponseRedirect("%s?id=%d" % (reverse("hwdb-edit-charset"), int(id)))
    elif not cs.public:  #check that people don't try to see private charsets
        return HttpResponseRedirect(reverse("hwdb-charsets"))
    return {'charset':cs}

@login_required
@render_to('hwdb/edit_charset.html')
def edit_charset(request):
    id = request.REQUEST.get('id')
    cs = get_object_or_404(CharacterSet, id=id)
    if request.method == 'POST':
        form = CharacterSetForm(request.POST, instance=cs)
        if form.is_valid():
            charset = form.save()
            request.session['current_charset'] = charset
            #return HttpResponseRedirect(reverse("hwdb-charset"))
    else:
        form = CharacterSetForm(instance=cs)

    return {'form':form, 'charset':cs }




@login_required
def random_char(request):
    charset = request.session.get('current_charset', None)
    if charset is not None:
        return HttpResponse(unichr(charset.get_random()))
    else:
        return HttpResponse("no charset selected")

@login_required
def random_charset(request):
    request.session['current_charset'] = CharacterSet.objects.get(id=1) #should be random
    return HttpResponse(request.session['current_charset'].name)

@render_to('hwdb/recognize.html')
def recognize(request):
    return {}

def recognize_submit(request):
    if settings.DEBUG:
        xml = request.REQUEST['xml']    #if testing we want to be able to pass stuff in with GET request
    else:
        xml = request.POST['xml']
    char = character.Character()
    char.read_string(xml)
    klass = Recognizer.get_available_recognizers()['zinnia']
    rec = klass()
    rec.set_model('Simplified Chinese')
    writing = char.get_writing()
    #writing = writing.copy()
    results = rec.recognize(writing) 
    return HttpResponse(u"%s" % jsonify_results(results))

def jsonify_results(res):
    results = []
    for r in res:
        d = {"character":unicode(r[0], encoding='utf-8'), "score":r[1]}
        results += [d]
    s = simplejson.dumps(results, encoding='utf-8', ensure_ascii=False)
    return s




########NEW FILE########
__FILENAME__ = models
from tegakidb.hwdb.models import *

class Assignment(CharacterSet):
    """
    A CharacterSet which is made just for doing homework assignments.
    Needs special properties like being ordered
    """
    pass
admin.site.register(Assignment)



########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates two different styles of tests (one doctest and one
unittest). These will both pass when you run "manage.py test".

Replace these with more appropriate tests for your application.
"""

from django.test import TestCase

class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.failUnlessEqual(1 + 1, 2)

__test__ = {"doctest": """
Another way to test that 1 + 1 is equal to 2.

>>> 1 + 1 == 2
True
"""}


########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

urlpatterns = patterns('tegakidb.lianxi.views',
    url(r'^$', 'index', name="lianxi"),
    url(r'^assignments/$', 'assignments', name="lianxi-assignments"),
    url(r'^assignments_datagrid/$', 'assignments_datagrid', name="lianxi-assignments-datagrid"),
)



########NEW FILE########
__FILENAME__ = views
# coding: UTF-8
from django.shortcuts import render_to_response, get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse

from django.conf import settings

from tegakidb.users.models import TegakiUser

from django.utils import simplejson
from tegakidb.utils import render_to, datagrid_helper

from dojango.util import to_dojo_data
from dojango.decorators import json_response


from tegakidb.lianxi.models import *
from tegakidb.hwdb.forms import *

@login_required
@render_to('lianxi/index.html')
def index(request):
    """
    Home page of Lianxi
    """
#    return HttpResponse("hi")
    return {}

@login_required
@render_to('lianxi/assignments.html')
def assignments(request):
    """
    List all assignments
    """
    return {}


@login_required
@json_response
def assignments_datagrid(request):
    ### need to hand pick fields from Assignments, if some are None, need to pass back empty strings for dojo
    dojo_obs = []
    assignments, num = datagrid_helper(Assigment, request)
    for a in assignments:
        djob = {}
        #'id', 'user__username', 'country', 'lang', 'description', 'n_handwriting_samples'
        djob['id'] = a.id
        #djob['character__utf8'] = s.character.utf8()
        #djob['character__lang__description'] = s.character.lang.description
        #djob['date'] = s.date
        #djob['character_set__name'] = s.character_set.name
        #djob['user__username'] = s.user.username
        #if s.user.get_profile().show_handwriting_samples or request.user == s.user: 
            #only if they publicly display this charset
            #or it's their charset
        #    dojo_obs += [djob]
        #else:
        #    num = num -1
    return to_dojo_data(dojo_obs, identifier='id', num_rows=num)

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/python
from django.core.management import execute_manager
try:
    import settings # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
    sys.exit(1)

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.contrib import admin

from django.contrib.auth.models import User

class NewsItem(models.Model):
 
    title = models.CharField(max_length=50)
    description = models.CharField(max_length=250)
    body = models.TextField()
    pub_date = models.DateTimeField('date published')
    user = models.ForeignKey(User)

    def __str__(self):
        return "%d - %s " % (self.id, self.title)

admin.site.register(NewsItem)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

urlpatterns = patterns('tegakidb.news.views',
    url(r'^$', 'index', name="news"),
    url(r'^(?P<news_item_id>\d+)/$', 'detail', name="detail"),
)


########NEW FILE########
__FILENAME__ = views
from django.shortcuts import render_to_response, get_object_or_404

from tegakidb.news.models import NewsItem

from tegakidb.utils import render_to

@render_to('news/index.html')
def index(request):
    latest_news = NewsItem.objects.all().order_by('-pub_date')[:5]
    return {'latest_news': latest_news}

@render_to('news/detail.html')
def detail(request, news_item_id):
    news_item = get_object_or_404(NewsItem, pk=news_item_id)
    return {'news_item': news_item}


########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
from django.contrib import admin
from django.conf import settings
admin.autodiscover()

urlpatterns = patterns('',
    url(r'^$', 'tegakidb.news.views.index', name="index"),        #this view could be changed
    url(r'^login/$', 'django.contrib.auth.views.login', {'template_name': 'users/login.html'}, name="login"),
    url(r'^logout/$', 'django.contrib.auth.views.logout', {'template_name': 'users/logout.html', 'next_page':'/%s' % settings.BASE_URL}, name="logout"),


    (r'^lianxi/', include('tegakidb.lianxi.urls')),
    (r'^news/', include('tegakidb.news.urls')),

    (r'^users/', include('tegakidb.users.urls')),
    
    (r'^hwdb/', include('tegakidb.hwdb.urls')),


    (r'^dojango/', include('tegakidb.dojango.urls')),

#    (r'^lianxi/', include('tegakidb.lianxi.urls')),
    (r'^admin/(.*)', admin.site.root),
    #(r'^admin/', include(admin.site.urls)), #this is Django 1.1 version 
)

# We serve static content through Django in DEBUG mode only.
# In production mode, the proper directory aliases (Alias directive in Apache)
# should be defined.
if settings.DEBUG:
    urlpatterns += patterns('',
    (r'^static/webcanvas/(?P<path>.*)$', 'django.views.static.serve',
            {'document_root': settings.WEBCANVAS_ROOT, 'show_indexes': True}),

    (r'^static/(?P<path>.*)$', 'django.views.static.serve',
            {'document_root': settings.MEDIA_ROOT, 'show_indexes': True}),
    #(r'^dojo/(?P<path>.*)$', 'django.views.static.serve',
    #        {'document_root': settings.DOJO_ROOT, 'show_indexes': True}),
        )

########NEW FILE########
__FILENAME__ = forms
#from django import forms
from dojango import forms

from tegakidb.users.models import TegakiUser
from django.contrib.auth.models import User

#form for editing tegaki users
class TegakiUserForm(forms.ModelForm):
    class Meta:
        model = TegakiUser
        exclude = ('user',)

    def __init__(self, *args, **kwargs):
        super(TegakiUserForm, self).__init__(*args, **kwargs)
        self.fields['lang'].label = "Language"
        try:
            self.fields['n_handwriting_samples'].label = "# of Handwriting Samples"
        except:
            pass 

#we don't want to let the user edit EVERYTHING about themselves
class SelfTUForm(TegakiUserForm):
    class Meta(TegakiUserForm.Meta):
        exclude = ('user', 'n_handwriting_samples')

#we only want to show public info about users
#class PublicTUForm(TegakiUserForm):
#    class Meta(TegakiUserForm.Meta):
#        exclude = ('user', 'n_handwriting_samples')


class RegisterForm(SelfTUForm):
    username = forms.CharField(label="Username")
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirm Password", widget=forms.PasswordInput)

    def clean_username(self):
        username = self.cleaned_data["username"]
        try:
            User.objects.get(username=username)
        except User.DoesNotExist:
            return username
        raise forms.ValidationError("A user with that username already exists.")

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1", "")
        password2 = self.cleaned_data["password2"]
        if password1 != password2:
            raise forms.ValidationError("The two password fields didn't match.")
        return password2

    #I hope I'm doing this right. It works but may not be the most elegant way.
    def save(self, commit=True):
        username = self.clean_username()
        password = self.clean_password2()
        new_user = User.objects.create(username=username)
        new_user.save()
        user = User.objects.get(username=username)
        user.set_password(password)
        user.save()
        self.instance.user_id = user.id
        forms.models.save_instance(self, user.get_profile(), commit=True)
        return user



########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.contrib import admin
from django.contrib.auth.models import User
from django.db.models.signals import post_save

from tegakidb.utils.models import Language

#this creates a custom User class that inherits all of the functionality of standard Django Users
#The only problem here is deleting a TegakiUser doesn't delete the Django user
class TegakiUser(models.Model):
    user = models.ForeignKey(User, unique=True)
    #info    
    country = models.CharField(max_length=100, blank=True)
    lang = models.ForeignKey(Language, null=True, blank=True)
    description = models.TextField(blank=True)

    #preferences
    show_handwriting_samples = models.BooleanField(default=True) #should be default=False
    #stats
    n_handwriting_samples = models.IntegerField(default=0)

    def __unicode__(self):
        return self.user.username


#Creates the User profile automatically when a User is created
def create_profile(sender, **kw):
    user = kw["instance"]
    if kw["created"]:
        tu = TegakiUser(user=user)
        tu.save()
post_save.connect(create_profile, sender=User)

admin.site.register(TegakiUser)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

urlpatterns = patterns('tegakidb.users.views',
    url(r'^$', 'user_list', name="users"),
    url(r'^list_datagrid/$', 'user_list_datagrid', name="user-list-datagrid"),
    url(r'^register/$', 'register', name="register"),
    url(r'^(?P<userid>\d+)/$', 'profile', name="user-profile"),
    url(r'^edit/(?P<userid>\d+)/$', 'edit_profile', name="user-edit-profile"),
)


########NEW FILE########
__FILENAME__ = views
from django.shortcuts import render_to_response, get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect
from django.core.urlresolvers import reverse

#from django.contrib.auth.models import User
from tegakidb.users.models import *
from tegakidb.users.forms import *

from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate

#@render_to: decorator for render_to_response
from tegakidb.utils import render_to, datagrid_helper

from dojango.util import to_dojo_data
from dojango.decorators import json_response


@render_to('users/register.html')
def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            new_user = form.save()
            user = authenticate(username=form.cleaned_data["username"], password=form.cleaned_data["password2"])
            login(request, user)
            return HttpResponseRedirect(reverse("news")) #TODO: add support for next redirection
    else:
        form = RegisterForm()
        #TODO: add support for next redirection
    
    return {'form':form}

@login_required
@render_to('users/profile.html')
def profile(request, userid):
    tu = get_object_or_404(TegakiUser, pk=userid)
    if tu.user == request.user:
        return HttpResponseRedirect(reverse('user-edit-profile', args=[userid]))
    else:
        return {'tegaki_user':tu}

@login_required
#need a permission decorator here
@render_to('users/edit_profile.html')
def edit_profile(request, userid):
    tu = get_object_or_404(TegakiUser, pk=userid)
    if request.method == 'POST':
        data = request.POST
        if tu.user == request.user:
            form = SelfTUForm(data=data, instance=tu)
        else:
            form = TegakiUserForm(data=data, instance=tu)
        if form.is_valid():
            form.save()

    else:
        if tu.user == request.user:
            form = SelfTUForm(instance=tu)
        else:
            form = TegakiUserForm(instance=tu)

    return {'tegaki_user':tu, 'form':form }

@login_required
@render_to('users/list.html')
def user_list(request):
    return {}




@login_required
@json_response
def user_list_datagrid(request):
    ### need to hand pick fields from TegakiUser, if some are None, need to pass back empty strings for dojo
    dojo_obs = []
    users, num = datagrid_helper(TegakiUser, request)
    for u in users:
        djob = {}
        #'id', 'user__username', 'country', 'lang', 'description', 'n_handwriting_samples'
        djob['id'] = u.user.id
        djob['user__username'] = u.user.username
        if u.country:
            djob['country'] = u.country
        if u.lang:
            djob['lang__description'] = u.lang.description
        if u.description:
            djob['description'] = u.description
        if u.show_handwriting_samples:  #only if they publicly display their samples
            djob['n_handwriting_samples'] = u.n_handwriting_samples
        dojo_obs += [djob]
    return to_dojo_data(dojo_obs, identifier='user__username', num_rows=num)

    

########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-
from django.db import models
from django.contrib import admin

class Language(models.Model):
    """
    Store langauge codes (subtags) and their descriptions
    http://www.iana.org/assignments/language-subtag-registry
    """
    subtag = models.CharField(max_length=10)
    description = models.TextField()

    def __unicode__(self):
        return self.subtag
admin.site.register(Language)

"""
class Filter(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    filter = models.CharField(max_length=255) #regex of which characters to filter

    def __unicode__(self):
            return self.name
admin.site.register(Filter)
"""

########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
__FILENAME__ = tegakiwagomu
# -*- coding: utf-8 -*-

# Copyright (C) 2009 The Tegaki project contributors
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

# Contributors to this file:
# - Mathieu Blondel

VERSION = '0.3.1'

import os
import struct
from array import array

from tegaki.recognizer import Results, Recognizer, RecognizerError
from tegaki.trainer import Trainer, TrainerError
from tegaki.arrayutils import array_flatten
from tegaki.dictutils import SortedDict
from tegaki.mathutils import euclidean_distance

VECTOR_DIMENSION_MAX = 4
INT_SIZE = 4
FLOAT_SIZE = 4
MAGIC_NUMBER = 0x77778888

# Features

FEATURE_EXTRACTION_FUNCTIONS = ["get_xy_features", "get_delta_features"]

def get_xy_features(writing):
    """
    Returns (x,y) for each point.
    """
    return [(x, y, 0.0, 0.0) for s in writing.get_strokes() for x,y in s]

get_xy_features.DIMENSION = 2

def get_delta_features(writing):   
    """
    Returns (delta x, delta y) for each point.
    """
    strokes = writing.get_strokes()
    vectors = [(x,y) for stroke in strokes for x,y in stroke]

    arr = []

    for i in range(1, len(vectors)):
        ((x1, y1), (x2, y2)) = (vectors[i-1], vectors[i])
        deltax = float(abs(x2 - x1))
        deltay = float(abs(y2 - y1))

        # we add two floats to make it 16 bytes
        arr.append((deltax, deltay, 0.0, 0.0))

    return arr

get_delta_features.DIMENSION = 2

# DTW

class DtwMatrix:
    # we use 1d-vector V instead of a n*m 2d-matrix M
    # M[i,j] can be accessed by V[k], k = j*n + i

    def __init__(self, n, m):
        self.a = array("f", [0.0] * (n*m))
        self.n = n
        self.m = m

    def __getitem__(self, p):
        return self.a[p[1] * self.n + p[0]]

    def __setitem__(self, p, value):
        self.a[p[1] * self.n + p[0]] = value

def dtw(s, t, d, f=euclidean_distance):
    """
    s; first sequence
    t: second sequence
    d: vector dimension
    f: distance function

    s and t are flat sequences of feature vectors of dimension d, so 
    their length should be multiple of d
    """    
    assert(len(s) % d == 0)
    assert(len(t) % d == 0)

    n = len(s) / d
    m = len(t) / d
   
    DTW = DtwMatrix(n, m)
   
    infinity = 4294967296 # 2^32
    
    for i in range(1, m):
        DTW[(0, i)] = infinity
        
    for i in range(1, n):
        DTW[(i, 0)] = infinity

    DTW[(0, 0)] = 0.0
       
    for i in range(1, n):
        # retrieve 1st d-dimension vector
        v1 = s[i*d:i*d+d]

        for j in range(1, m):
            # retrieve 2nd d-dimension vector
            v2 = t[j*d:j*d+d]
            # distance function
            cost = f(v1, v2)
            # DTW recursion step
            DTW[(i, j)] = cost + min(DTW[(i-1, j)],
                                     DTW[(i-1, j-1)],
                                     DTW[(i, j-1)])
       
    return DTW[(n-1, m-1)]

# Small utils

def argmin(arr):
    return arr.index(min(arr))

# File utils

def read_uints(f, n):
    return struct.unpack("@%dI" % n, f.read(n*4))

def read_uint(f):
    return read_uints(f, 1)[0]

def write_uints(f, *args):
    f.write(struct.pack("@%dI" % len(args), *args))
write_uint = write_uints

def read_floats(f, n):
    return struct.unpack("@%df" % n, f.read(n*4))

def read_float(f):
    return read_floats(f, 1)[0]

def write_floats(f, *args):
    f.write(struct.pack("@%df" % len(args), *args))
write_float = write_floats    

def get_padded_offset(offset, align):
    padding = (align - (offset % align)) % align
    return offset + ((align - (offset % align)) % align)

class _WagomuBase(object):

    def __init__(self):
        # The bigger the threshold, the fewer points the algorithm has to
        # compare. However, the fewer points, the more the character
        # quality deteriorates. 
        # The value is a distance in a 1000 * 1000 square
        self._downsample_threshold = 50

        self._feature_extraction_function = eval("get_delta_features")
        self._vector_dimension = self._feature_extraction_function.DIMENSION

        if isinstance(self, Recognizer):
            self._error = RecognizerError
        else:
            self._error = TrainerError

    def get_features(self, writing):
        writing.normalize()
        writing.downsample_threshold(self._downsample_threshold)
        flat = array_flatten(self._feature_extraction_function(writing))
        return [float(f) for f in flat]

    def set_options(self, opt):
        if "downsample_threshold" in opt:
            try:
                self._downsample_threshold = int(opt["downsample_threshold"])
            except ValueError:
                raise self._error, "downsample_threshold must be an integer"

        if "feature_extraction_function" in opt:
            if not opt["feature_extraction_function"] in \
                FEATURE_EXTRACTION_FUNCTIONS:
                raise self._error, "The feature function does not exist"
            else:
                self._feature_extraction_function = \
                    eval(opt["feature_extraction_function"])
                self._vector_dimension = \
                    self._feature_extraction_function.DIMENSION

        if "window_size" in opt:
            try:
                ws = int(opt["window_size"])
                if ws < 0: raise ValueError
                if isinstance(self, Recognizer):
                    self._recognizer.set_window_size(ws)
            except ValueError:
                raise self._error, "window_size must be a positive integer"    
       

# Recognizer

try:
    import wagomu

    class WagomuRecognizer(_WagomuBase, Recognizer):

        RECOGNIZER_NAME = "wagomu"

        def __init__(self):
            Recognizer.__init__(self)
            _WagomuBase.__init__(self)

            self._recognizer = wagomu.Recognizer()

        def open(self, path):
            ret = self._recognizer.open(path)
            if not ret: 
                raise RecognizerError, self._recognizer.get_error_message()

        def _recognize(self, writing, n=10):
            n_strokes = writing.get_n_strokes()
            feat = self.get_features(writing)
            nfeat = len(feat) 
            nvectors = nfeat / VECTOR_DIMENSION_MAX

            ch = wagomu.Character(nvectors, n_strokes)
            for i in range(nfeat):
                ch.set_value(i, feat[i])

            res = self._recognizer.recognize(ch, n)

            candidates = []
            for i in range(res.get_size()):
                utf8 = unichr(res.get_unicode(i)).encode("utf8")
                candidates.append((utf8, res.get_distance(i)))

            return Results(candidates)

    RECOGNIZER_CLASS = WagomuRecognizer

except ImportError:
    pass # no recognizer available here


# Trainer

class WagomuTrainer(_WagomuBase, Trainer):

    TRAINER_NAME = "wagomu"

    def __init__(self):
        Trainer.__init__(self)
        _WagomuBase.__init__(self)

    def train(self, charcol, meta, path=None):
        self._check_meta(meta)

        if not path:
            if "path" in meta:
                path = meta["path"]
            else:
                path = os.path.join(os.environ['HOME'], ".tegaki", "models",
                                    "wagomu", meta["name"] + ".model")
        else:
            path = os.path.abspath(path)

        if not os.path.exists(os.path.dirname(path)):
            os.makedirs(os.path.dirname(path))

        meta_file = path.replace(".model", ".meta")
        if not meta_file.endswith(".meta"): meta_file += ".meta"
        
        self.set_options(meta)
        self._save_model_from_charcol(charcol, path)
        self._write_meta_file(meta, meta_file)

    def _get_representative_writing(self, writings):
        n_writings = len(writings)
        sum_ = [0] * n_writings
        features = [self.get_features(w) for w in writings]

        # dtw is a symmetric distance so d(i,j) = d(j,i)
        # we only need to compute the values on the right side of the
        # diagonale
        for i in range(n_writings):
            for j in range (i+1, n_writings):
                distance = dtw(features[i], features[j],
                                self._vector_dimension)
                sum_[i] += distance
                sum_[j] += distance
        
        i = argmin(sum_)

        return writings[i]

    def _save_model_from_charcol(self, charcol, output_path):
        chargroups = {} 

        n_chars = 0

        # get non-empty set list
        set_list = []
        for set_name in charcol.get_set_list():
            chars = charcol.get_characters(set_name)
            if len(chars) == 0: continue # empty set

            utf8 = chars[0].get_utf8()
            if utf8 is None: continue

            set_list.append(set_name)

        # each set may contain more than 1 sample per character
        # but we only need one ("the template") so we find the set
        # representative,  which we define as the sample which is, on
        # average, the closest to the other samples of that set
        for set_name in set_list:
            chars = charcol.get_characters(set_name)
            if len(chars) == 0: continue # empty set

            utf8 = chars[0].get_utf8()
            if utf8 is None: continue

            if len(chars) == 1 or len(chars) == 2:
                # take the first one if only 1 or 2 samples available
                writing = chars[0].get_writing()
            else:
                # we need to find the set representative
                writings = [c.get_writing() for c in chars]
                writing = self._get_representative_writing(writings)

            # artificially increase the number of points
            # this is useful when training data is made of straight lines
            # and thus has very few points
            writing.upsample_threshold(10)

            feat = self.get_features(writing)
            n_strokes = writing.get_n_strokes()

            if not n_strokes in chargroups: chargroups[n_strokes] = []
            chargroups[n_strokes].append((utf8, feat))

            print "%s (%d/%d)" % (utf8, n_chars+1, len(set_list))
            n_chars += 1

        stroke_counts = chargroups.keys()
        stroke_counts.sort()

        # Sort templates in stroke groups by length
        for sc in stroke_counts:
            chargroups[sc].sort(lambda x,y: cmp(len(x[1]),len(y[1])))

        # save model in binary format
        # this file is architecture dependent
        f = open(output_path, "wb")

        # magical number
        write_uint(f, MAGIC_NUMBER)

        # number of characters/templates
        write_uint(f, n_chars)

        # number of character groups
        write_uint(f, len(chargroups))

        # vector dimensionality
        write_uint(f, self._vector_dimension)

        # downsample threshold
        write_uint(f, self._downsample_threshold)

        strokedatasize = {}

        # character information
        for sc in stroke_counts:
            strokedatasize[sc] = 0

            for utf8, feat in chargroups[sc]:
                # unicode integer
                write_uint(f, ord(unicode(utf8, "utf-8")))
                
                # n_vectors
                write_uint(f, len(feat) / VECTOR_DIMENSION_MAX)

                strokedatasize[sc] += len(feat) * FLOAT_SIZE

        offset = 5 * INT_SIZE # header
        offset += n_chars * 2 * INT_SIZE # character information 
        offset += len(chargroups) * 4 * INT_SIZE # character group
        poffset = get_padded_offset(offset, VECTOR_DIMENSION_MAX * FLOAT_SIZE)
        pad = poffset - offset

        # character group information
        for sc in stroke_counts:
            # number of strokes
            write_uint(f, sc)
    
            # number of characters
            write_uint(f, len(chargroups[sc]))

            # offset from the start of the file
            write_uint(f, poffset)

            # padding
            f.write("".join(["\0"] * 4))

            poffset += strokedatasize[sc] 

        # padding
        if pad > 0:
            f.write("".join(["\0"] * pad))

        assert(f.tell() % (VECTOR_DIMENSION_MAX * FLOAT_SIZE) == 0)

        # stroke data
        for sc in stroke_counts:
            for utf8, feat in chargroups[sc]:
                assert(f.tell() % (VECTOR_DIMENSION_MAX * FLOAT_SIZE) == 0)

                # stroke data as flat list of vectors
                # e.g. [[x1, y1], [x2, y2]] is stored as [x1, y1, x2, y2]
                write_floats(f, *feat)

        f.close()
            
TRAINER_CLASS = WagomuTrainer


########NEW FILE########
__FILENAME__ = tomoe2tegaki
# Converts Tomoe format (all characters in one XML file)
# to Tegaki Lab format (one file per character)

import sys
import os
import tomoe

from tegaki.character import *

def tomoechar2tegakichar(tomoechar):
    tegakichar = Character()
    tegakichar.set_utf8(tomoechar.get_utf8())

    writing = Writing()

    for stroke in tomoechar.get_writing().get_strokes():
        s = Stroke()
        for x, y in stroke:
            s.append_point(Point(x=x, y=y))
        writing.append_stroke(s)

    tegakichar.set_writing(writing)

    return tegakichar 

def is_kanji(char):
    if not (
            (char >= 0x4E00 and char <= 0x9FBF) or \
            (char >= 0x3400 and char <= 0x4DBF) or \
            (char >= 0x20000 and char <= 0x2A6DF) or \
            (char >= 0x3190 and char <= 0x319F) or \
            (char >= 0xF900 and char <= 0xFAFF) or \
            (char >= 0x2F800 and char <= 0x2FA1F)
            ):

        return False
    else:
        return True

dictfile = sys.argv[1]
output_dir = sys.argv[2]

dictobject = tomoe.Dict("XML", filename = dictfile, editable = False)
query = tomoe.Query()

candidates = dictobject.search(query)

for c in candidates:
    char = tomoechar2tegakichar(c.get_char())
    charunicode = unicode(char.get_utf8(), "utf8")
    if len(charunicode) == 1:
        charcode = int(ord(unicode(charunicode)))
        if not is_kanji(charcode):
            continue
        char.write(os.path.join(output_dir, "%d.xml.gz" % charcode), 
                   gzip=True)
########NEW FILE########
__FILENAME__ = dtw
# -*- coding: utf-8 -*-

# Copyright (C) 2009 The Tegaki project contributors
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

# Contributors to this file:
# - Mathieu Blondel

import numpy

def dtw(s, t, d):
    n = len(s)
    m = len(t)
    
    DTW = numpy.zeros((n, m))
   
    infinity = float('infinity')
    
    for i in range(1, m):
        DTW[0, i] = infinity
        
    for i in range(1, n):
        DTW[i, 0] = infinity
       
    for i in range(0, n):
        for j in range(0, m):
            cost = d(s[i], t[j])
            DTW[i, j] = cost + min(DTW[i-1, j], DTW[i, j-1], DTW[i-1, j-1])

    return DTW[n - 1, m - 1]

########NEW FILE########
__FILENAME__ = exceptions
# -*- coding: utf-8 -*-

# Copyright (C) 2008 The Tegaki project contributors
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

# Contributors to this file:
# - Mathieu Blondel

class ModelException(Exception):
    pass


########NEW FILE########
__FILENAME__ = hmm
# -*- coding: utf-8 -*-

# Copyright (C) 2008 The Tegaki project contributors
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

# Contributors to this file:
# - Mathieu Blondel

import os
from math import sqrt, log
try:
    import cPickle as pickle
except ImportError:
    import pickle
from tegaki.arrayutils import *

def assert_almost_equals(a, b, eps=0.001):
    assert(abs(a-b) < eps)

class _Pickable:

    @classmethod
    def from_file(cls, input_file):
        f = open(input_file)
        ret = pickle.load(f)
        f.close()
        return ret

    def write(self, output_file):
        if os.path.exists(output_file):
            os.unlink(output_file)

        f = open(output_file, "w")
        pickle.dump(self, f)
        f.close()

class Sequence(list, _Pickable):
    pass

class SequenceSet(list, _Pickable):
    pass

class MultivariateHmm(object, _Pickable):

    def __init__(self, A, B, pi):
        self.A = A
        self.B = B
        self.pi = pi

    def get_n_states(self):
        return len(self.pi)

class ViterbiTrainer(object):
    """
    Supports left-right HMMs only for now.
    """

    def __init__(self, calculator, n_iterations=5, eps=0.0001,
                       non_diagonal=False):
        self._calculator = calculator
        self._n_iterations = n_iterations
        self._eps = abs(log(eps))
        self._non_diagonal = non_diagonal

    def train(self, hmm, sset):
        last_logp_avg = None

        for it in range(self._n_iterations):
            
            # contains vectors assigned to states
            containers = []
            for i in range(hmm.get_n_states()):
                containers.append([])

            # contains first state counts
            init = [0] * hmm.get_n_states()

            # contains outgoing transition counts
            out_trans = [0] * hmm.get_n_states()

            # contains transition counts
            trans_mat = []
            for i in range(hmm.get_n_states()):
                trans_mat.append([0] * hmm.get_n_states())

            logp_avg = 0

            for seq in sset:
                states, logp = self._calculator.viterbi(hmm, seq)
                logp_avg += logp
                assert(len(states) == len(seq))

                init[states[0]] += 1

                for i, state in enumerate(states):
                    containers[state].append(seq[i])
                    out_trans[state] += 1
                    
                    if i != len(states) - 1:
                        next_state = states[i+1]
                        trans_mat[state][next_state] += 1

            logp_avg /= float(len(sset))

            if last_logp_avg is not None:
                diff = abs(logp_avg - last_logp_avg)
                if  diff < self._eps:
                    #print "Viterbi training stopped on iteration %d" % it
                    break

            last_logp_avg = logp_avg

           # estimate observertion distribution
            opdfs = []
            for container in containers:
                if container == []:
                    # no vectors assigned to that state
                    # this means that the new HMM will have potentially
                    # fewer states
                    break

                means = array_mean_vector(container)
                covmatrix = array_covariance_matrix(container,
                                                    self._non_diagonal)
                opdfs.append([means, covmatrix])

            n_states = len(opdfs)

            # estimate initial state probabilities
            pi = [float(v) / len(sset) for v in init[0:n_states]]
            assert_almost_equals(sum(pi), 1.0)

            trans_mat = trans_mat[0:n_states]

            # estimate state transition probabilities
            for i in range(n_states): 
                for j in range(n_states):
                    if out_trans[i] > 0:
                        trans_mat[i][j] /= float(out_trans[i])

                trans_mat[i] = trans_mat[i][0:n_states]
                sum_= sum(trans_mat[i])

                if sum_ == 0:
                    trans_mat[i][-1] = 1.0
                else:
                    # normalize so that the sum of probabilities 
                    # always equals 1.0
                    for j in range(n_states):
                        trans_mat[i][j] /= sum_
               
                assert_almost_equals(sum(trans_mat[i]), 1.0)

            hmm.pi = pi
            hmm.A = trans_mat
            hmm.B = opdfs

try:
    import ghmm

    DOMAIN = ghmm.Float()

    class _GhmmBase(object):

        def _get_hmm(self, hmm):
            return ghmm.HMMFromMatrices(DOMAIN,
                            ghmm.MultivariateGaussianDistribution(DOMAIN),
                            hmm.A, hmm.B, hmm.pi)    

    class GhmmBaumWelchTrainer(_GhmmBase):

        def train(self, hmm, sset):
            sset = [array_flatten(s) for s in sset]
            hmm_ = self._get_hmm(hmm)
            hmm_.baumWelch(ghmm.SequenceSet(DOMAIN, sset))
            hmm.A, hmm.B, hmm.pi = hmm_.asMatrices()

    class GhmmViterbiCalculator(_GhmmBase):

        def viterbi(self, hmm, obj):
            hmm_ = self._get_hmm(hmm)

            if isinstance(obj, SequenceSet):
                obj = [array_flatten(s[:]) for s in obj]
                obj = ghmm.SequenceSet(DOMAIN, obj)
                res = hmm_.viterbi(obj)
                # ghmm returns a scalar even though a sequence set was passed
                # if length == 1 but we want an array
                if len(obj) == 1:
                    res = [[res[0]], [res[1]]]
            else:
                obj = ghmm.EmissionSequence(DOMAIN, array_flatten(obj[:]))
                res = hmm_.viterbi(obj)
    
            return res

except ImportError:
    pass

try:
    from hydroml.hmm import Hmm
    from hydroml.distribution import MultivariateGaussianDistribution

    class _HydromlBase(object):

        def _get_hmm(self, hmm):
            opdfs = []
            for means, covmatrix in hmm.B:
                covmatrix = array_split(covmatrix, int(sqrt(len(covmatrix))))
                opdfs.append(MultivariateGaussianDistribution(means, covmatrix))

            return Hmm(hmm.pi, hmm.A, opdfs)

    class HydromlViterbiCalculator(_HydromlBase):

        def viterbi(self, hmm, obj):
            hmm_ = self._get_hmm(hmm)

            if isinstance(obj, SequenceSet):
                res = [hmm_.viterbi(seq) for seq in obj]
                all_paths = [res[i][0] for i in range(len(res))]
                all_logp = [res[i][1] for i in range(len(res))]
                return all_paths, all_logp
            else:
                return hmm_.viterbi(obj)

except ImportError:
    pass

import platform

if platform.system() == "Java": # Jython 2.5

    import java
    from java.util import ArrayList

    from be.ac.ulg.montefiore.run.jahmm import ObservationVector
    from be.ac.ulg.montefiore.run.jahmm import OpdfMultiGaussian
    from be.ac.ulg.montefiore.run.jahmm import Hmm
    from be.ac.ulg.montefiore.run.jahmm.learn import BaumWelchLearner
    from be.ac.ulg.montefiore.run.jahmm.learn import BaumWelchScaledLearner
    from be.ac.ulg.montefiore.run.jahmm import ViterbiCalculator

    class _JahmmBase(object):

        def _get_hmm(self, hmm):
            """
            Gets the internal HMM as a Jahmm object.
            """
            opdfs = []
            for means, covmatrix in hmm.B:
                covmatrix = array_split(covmatrix, int(sqrt(len(covmatrix))))
                opdfs.append(OpdfMultiGaussian(means, covmatrix))

            return Hmm(hmm.pi, hmm.A, ArrayList(opdfs))

        def _vectors_to_observations(self, vectors):
            arr = [ObservationVector(v) for v in vectors]
            return ArrayList(arr)

        def _sset_to_array_list(self, sset):
            obs_set = ArrayList()
            for seq in sset:
                obs_set.add(self._vectors_to_observations(seq))
            return obs_set

    class JahmmBaumWelchTrainer(_JahmmBase):

        def _update_hmm(self, hmm, hmm_):
            """
            Updates the internal HMM from a Jahmm object.
            """
            hmm.pi = [hmm_.getPi(i) for i in range(hmm_.nbStates())]

            hmm.A = []
            for i in range(hmm_.nbStates()):
                arr = []
                for j in range(hmm_.nbStates()):
                    arr.append(hmm_.getAij(i, j))
                hmm.A.append(arr)

            opdfs = [hmm_.getOpdf(i) for i in range(hmm_.nbStates())]
            hmm.B = []
            for opdf in opdfs:
                means = opdf.mean().tolist()
                covmatrix = [a.tolist() for a in opdf.covariance()]
                covmatrix = array_flatten(covmatrix)
                hmm.B.append([means, covmatrix])

        def train(self, hmm, sset):
            hmm_ = self._get_hmm(hmm)
            learner = BaumWelchScaledLearner()

            obs_set = self._sset_to_array_list(sset)

            try:
                hmm_ = learner.learn(hmm_, obs_set)
                self._update_hmm(hmm, hmm_)
            except java.lang.IllegalArgumentException:
                print "Couldn't train HMM"

    class JahmmViterbiCalculator(_JahmmBase):

        def _viterbi(self, seq, hmm_):
            calc = ViterbiCalculator(self._vectors_to_observations(seq), hmm_)
            return calc.stateSequence().tolist(), calc.lnProbability()

        def viterbi(self, hmm, obj):
            hmm_ = self._get_hmm(hmm)

            if isinstance(obj, SequenceSet):
                res = [self._viterbi(seq, hmm_) for seq in obj]
                all_paths = [res[i][0] for i in range(len(res))]
                all_logp = [res[i][1] for i in range(len(res))]
                return all_paths, all_logp
            else:
                return self._viterbi(obj, hmm_)

########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-

# Copyright (C) 2008 The Tegaki project contributors
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

# Contributors to this file:
# - Mathieu Blondel

try:
    import cPickle as pickle
except ImportError:
    import pickle

from random import random, randint, choice

from tegaki.character import *

def writing_to_xml(writing):
    character = Character()
    character.set_utf8("?")
    character.set_writing(writing)
    return character.to_xml()

def writing_to_json(writing):
    character = Character()
    character.set_utf8("?")
    character.set_writing(writing)
    return character.to_json() 

def xml_to_writing(xml):
    character = Character()
    character.read_string(xml)
    return character.get_writing()

def random_choose(objects):
    """
    Choose an object randomly in the list, remove it from the list 
    and return it.
    """
    if len(objects) == 1:
        i = 0
    else:
        i = randint(0, len(objects) - 1)
    obj = objects[i]
    del objects[i]
    return obj

def load_object(path):
    f = open(path)
    ret = pickle.load(f)
    f.close()
    return ret

def save_object(path, obj, del_first=False):
    if del_first and os.path.exists(path):
        os.unlink(path)

    f = open(path, "w")
    pickle.dump(obj, f)
    f.close()

def sort_files_by_numeric_id(files, reverse=False):
    """This only works with files having the form somenumber.ext"""
    def mycmp(a,b):
        a = os.path.basename(a)
        a = a[0:a.index(".")]
        b = os.path.basename(b)
        b = b[0:b.index(".")]
        return cmp(int(a), int(b))
    files.sort(mycmp, reverse=reverse)

def remove_duplicates(l):
    """
    Remove duplicates from a list and preserve order. 
    Elements from the list must be hashable.
    """
    d = {}
    ret = []
    for e in l:
        if not e in d:
            ret.append(e)
            d[e] = 1
    return ret
           
if __name__ == "__main__":
    assert(remove_duplicates(["b", "a", "b", 12, "z", 16, 12]) == \
           ["b", "a", 12, "z", 16])
########NEW FILE########
__FILENAME__ = writing_pad
# -*- coding: utf-8 -*-

# Copyright (C) 2008 The Tegaki project contributors
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

# Contributors to this file:
# - Mathieu Blondel

import gtk
import os
from tegakigtk.canvas import Canvas

class WritingPad(object):

    def canvas_clear(self, clear_button, data=None):
        self.canvas.clear()
        self.clear_label()

    def canvas_undo(self, save_button, data=None):
        writing = self.canvas.get_writing()
        if writing.get_n_strokes() > 0:
            self.canvas.revert_stroke()

    def canvas_find(self, save_button, data=None):
        writing = self.canvas.get_writing()

        self.clear_label()

        if self.find_method:
            res = self.find_method(writing)

            if res:
                text = " ".join(res)
                self.label.set_text(text)

    def canvas_set_writing(self, writing):
        self.canvas.set_writing(writing)

    def clear_label(self):
        self.label.set_text("")

    def delete_event(self, widget, event, data=None):
        return False

    def destroy(self, widget, data=None):
        gtk.main_quit()

    def __init__(self, find_method=None):
        self.find_method = find_method
        
        # window
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.connect("delete_event", self.delete_event)
        self.window.connect("destroy", self.destroy)
        self.window.set_border_width(10)
        self.window.set_resizable(False)

        # find button
        self.find_button = gtk.Button(stock=gtk.STOCK_FIND)
        self.find_button.connect("clicked", self.canvas_find)

        # undo button
        self.undo_button = gtk.Button(stock=gtk.STOCK_UNDO)
        self.undo_button.connect("clicked", self.canvas_undo)

        # clear button
        self.clear_button = gtk.Button(stock=gtk.STOCK_CLEAR)
        self.clear_button.connect("clicked", self.canvas_clear)

        # vbox
        self.vbox = gtk.VBox()
        self.vbox.pack_start(self.find_button)
        self.vbox.pack_start(self.undo_button)
        self.vbox.pack_start(self.clear_button)

        # canvas
        self.canvas = Canvas()
        self.canvas.set_size_request(300, 300)

        # hbox
        self.hbox = gtk.HBox(spacing=5)
        self.hbox.pack_start(self.canvas, expand=False)
        self.hbox.pack_start(self.vbox, expand=False)

        # result label
        self.label = gtk.Label()

        # final vbox
        self.fvbox = gtk.VBox(spacing=3)
        self.fvbox.pack_start(self.hbox)
        self.fvbox.pack_start(gtk.HSeparator())
        self.fvbox.pack_start(self.label)

        self.window.add(self.fvbox)
        self.window.show_all()

    def run(self):
        gtk.main()


########NEW FILE########
__FILENAME__ = model
# -*- coding: utf-8 -*-

# Copyright (C) 2008 The Tegaki project contributors
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

# Contributors to this file:
# - Mathieu Blondel

import os
import glob

from tegaki.arrayutils import *

import models.basic.model

class Model(models.basic.model.Model):
    """
    Title: 6dim
    Feature vectors: (x, y, delta x, delta y, delta2 x, delta2 y)
    """

    def __init__(self, *args):
        models.basic.model.Model.__init__(self, *args)

        self.SAMPLING = 0.5
        self.N_STATES_PER_STROKE = 3
        self.N_DIMENSIONS = 6
        self.NON_DIAGONAL = True

        self.TRAIN_CORPORA = ["japanese-learner1", "japanese-native1"]
        self.EVAL_CORPORA = ["japanese-learner1", "japanese-native1"]

        self.ROOT = os.path.join("models", "6dim")
        self.update_folder_paths()

    ########################################
    # Feature extraction...
    ########################################

    def get_feature_vectors(self, writing):
        """
        Get (x, y, delta x, delta y, delta2 x, delta2 y)

        delta x and delta y are the velocity up to a factor

        delta2 x and delta2 y are the acceleration up to a factor
        """
        strokes = writing.get_strokes()
        vectors = [[x,y] for stroke in strokes for x,y in stroke]
        vectors = array_sample(vectors, self.SAMPLING)

        # arr contains (delta x, delta y) pairs
        arr = []

        for i in range(1, len(vectors)):
            ((x1, y1), (x2, y2)) = (vectors[i-1], vectors[i])
            deltax = float(abs(x2 - x1))
            deltay = float(abs(y2 - y1))

            arr.append([deltax, deltay])

        # arr2 contains (delta2 x, delta2 y) pairs
        arr2 = []

        for i in range(1, len(arr)):
            ((x1, y1), (x2, y2)) = (arr[i-1], arr[i])
            delta2x = float(abs(x2 - x1))
            delta2y = float(abs(y2 - y1))

            arr2.append([delta2x, delta2y])

        # "vectors" contains 2 elements less than arr2
        # "arr" contains 1 element less than arr2
        ret = array_add(vectors[2:], arr[1:])
        ret = array_add(ret, arr2)
        
        return ret

########NEW FILE########
__FILENAME__ = model
# -*- coding: utf-8 -*-

# Copyright (C) 2008 The Tegaki project contributors
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

# Contributors to this file:
# - Mathieu Blondel

import os
import sys
import glob
import shutil
import tarfile
import datetime
import platform

from tegaki.character import *
from tegaki.arrayutils import *
from tegaki.mathutils import *
from tegaki.dictutils import SortedDict

from lib.exceptions import *
from lib.utils import *
from lib.hmm import Sequence, SequenceSet, MultivariateHmm, ViterbiTrainer
from lib import hmm

class Model(object):
    """
    Title: basic
    HMM: whole character
    Feature vectors: (dx, dy)
    Number of states: 3 per stroke
    Initialization: vectors distributed equally among states
    State transitions: 0.5 itself, 0.5 next state
    """

    TRAINING_NONE = 0
    TRAINING_BAUM_WELCH = 1
    TRAINING_VITERBI = 2
    TRAINING_BOTH = 3

    def __init__(self, options):

        if platform.system() == "Java": # Jython 2.5
            self.Trainer = hmm.JahmmBaumWelchTrainer
            self.ViterbiCalculator = hmm.JahmmViterbiCalculator
        else:
            self.Trainer = hmm.GhmmBaumWelchTrainer
            self.ViterbiCalculator = hmm.GhmmViterbiCalculator

        self.ALL = ["clean", "fextract", "init", "train", "eval"]
        self.COMMANDS = self.ALL + ["pad", "find", "commands", "archive"]
    
        self.verbose = options.verbose
        self.options = options

        self.SELF_TRANSITION = 0.5
        self.NEXT_TRANSITION = 0.5
        self.SAMPLING = 0.5
        self.N_STATES_PER_STROKE = 3
        self.N_DIMENSIONS = 2
        # whether to calculate non-diagonal values in the covariance matrix
        # or not
        self.NON_DIAGONAL = False
        self.TRAINING = self.TRAINING_BAUM_WELCH

        self.TRAIN_CORPORA = ["japanese-learner1", "japanese-native1"]
        self.EVAL_CORPORA = ["japanese-learner1", "japanese-native1"]
        self.ROOT = os.path.join("models", "basic")
        self.update_folder_paths()

    ########################################
    # General utils...
    ########################################

    def stderr_print(self, *args):
        sys.stderr.write("".join([str(arg) for arg in args]) + "\n")

    def update_folder_paths(self):
        self.DATA_ROOT = "data"
        self.EVAL_ROOT = os.path.join(self.DATA_ROOT, "eval")
        self.TRAIN_ROOT = os.path.join(self.DATA_ROOT, "train")
        
        self.FEATURES_ROOT = os.path.join(self.ROOT, "features")
        self.TRAIN_FEATURES_ROOT = os.path.join(self.FEATURES_ROOT, "train")
        self.EVAL_FEATURES_ROOT = os.path.join(self.FEATURES_ROOT, "eval")

        self.HMM_ROOT = os.path.join(self.ROOT, "hmms")
        self.INIT_HMM_ROOT = os.path.join(self.HMM_ROOT, "init")
        self.TRAIN_HMM_ROOT = os.path.join(self.HMM_ROOT, "train")

        self.eval_char_dict = None
        self.train_char_dict = None

    def load_char_dicts(self):
        self.load_eval_char_dict()
        self.load_train_char_dict()

    def load_eval_char_dict(self):
        if not self.eval_char_dict:
            self.eval_char_dict = self.get_eval_char_dict()
        self.print_verbose("Eval data loading done")

    def load_train_char_dict(self):
        if not self.train_char_dict:
            self.train_char_dict = self.get_train_char_dict()
        self.print_verbose("Training data loading done")

    def get_char_dict(self, directory, corpora):
        """
        Returns a dictionary with xml file list.
            keys are character codes.
            values are arrays of xml files.

        directory: root directory
        corpora: corpora list to restrict to
        """
        charcol = CharacterCollection()
        for file in glob.glob(os.path.join(directory, "*", "*")):
            corpus_name = file.split("/")[-2]
            # exclude data which are not in the wanted corpora
            if corpus_name not in corpora:
                continue

            if os.path.isdir(file):
                self.print_verbose("Loading dir %s" % file)
                charcol += CharacterCollection.from_character_directory(file)
            elif ".charcol" in file:
                self.print_verbose("Loading charcol %s" % file)
                gzip = False; bz2 = False
                if file.endswith(".gz"): gzip = True
                if file.endswith(".bz2"): bz2 = True
                charcol2 = CharacterCollection()
                charcol2.read(file, gzip=gzip, bz2=bz2)
                charcol += charcol2

        self.print_verbose("Grouping characters together...")
        dic = SortedDict()
        for set_name in charcol.get_set_list():
            for char in charcol.get_characters(set_name):
                charcode = ord(char.get_unicode())
                if not charcode in dic: dic[charcode] = []
                dic[charcode].append(char)

        return dic

    def get_chardict_n_characters(self, chardict):
        return sum([len(cl) for cc,cl in chardict.items()])
                    
    def get_eval_char_dict(self):
        return self.get_char_dict(self.EVAL_ROOT, self.EVAL_CORPORA)

    def get_train_char_dict(self):
        return self.get_char_dict(self.TRAIN_ROOT, self.TRAIN_CORPORA)

    def get_character(self, char_path):
        char = Character()
        if char_path.endswith(".gz"):
            char.read(char_path, gzip=True)
        else:
             char.read(char_path)
        return char

    def get_sequence_set(self, file_path):
        return SequenceSet.from_file(file_path)

    def get_utf8_from_char_code(self, char_code):
        return unichr(int(char_code)).encode("utf8")

    def print_verbose(self, *args, **kw):
        if "verbose" in kw: verbose = kw["verbose"]
        elif "v" in kw: verbose = kw["v"]
        else: verbose = 1

        if self.verbose >= verbose:
            self.stderr_print(*args)

    ########################################
    # Feature extraction...
    ########################################

    def get_feature_vectors(self, writing, normalize=True):
        """
        Get deltax and deltay as feature vectors.
        """
        if normalize:
            writing.downsample_threshold(50)
            writing.normalize()
            
        strokes = writing.get_strokes()
        vectors = [(x,y) for stroke in strokes for x,y in stroke]
        #vectors = array_sample(vectors, self.SAMPLING)

        arr = []

        for i in range(1, len(vectors)):
            ((x1, y1), (x2, y2)) = (vectors[i-1], vectors[i])
            deltax = float(abs(x2 - x1))
            deltay = float(abs(y2 - y1))

            arr.append((deltax, deltay))

        return arr

    def fextract(self):
        """Extract features"""

        self.load_char_dicts()

        for dirname, char_dict in (("eval", self.eval_char_dict),
                                   ("train", self.train_char_dict)):
            
            for char_code, char_list in char_dict.items():
                output_dir = os.path.join(self.FEATURES_ROOT, dirname)

                if not os.path.exists(output_dir):
                    os.makedirs(output_dir)

                sequence_set = []

                for character in char_list:

                    writing = character.get_writing()

                    char_features = self.get_feature_vectors(writing)

                    sequence_set.append(char_features)

                output_file = os.path.join(output_dir,
                                           str(char_code) + ".sset")

                self.print_verbose(output_file + " (%d chars)" % \
                                       len(sequence_set))

                sset = SequenceSet(sequence_set)
                sset.write(output_file)

    ########################################
    # Initialization...
    ########################################

    def get_train_feature_files(self):
        return glob.glob(os.path.join(self.TRAIN_FEATURES_ROOT, "*.sset"))

    def get_n_strokes(self, char_code):
        character = self.train_char_dict[char_code][0]
        return character.get_writing().get_n_strokes()

    def get_initial_state_probabilities(self, n_states):
        pi = [0.0] * n_states
        pi[0] = 1.0
        return pi

    def get_state_transition_matrix(self, n_states):
        matrix = []
        
        for i in range(n_states):
            # set all transitions to 0
            state = [0.0] * n_states
            
            if i == n_states - 1:
                # when the last state is reached,
                # the probability to stay in the state is 1
                state[n_states - 1] = 1.0
            else:
                # else, as an initial value, we set the prob to stay in
                # the same state to SELF_TRANSITION and to jump to the next
                # state to NEXT_TRANSITION
                # the values will be updated by the training
                state[i] = self.SELF_TRANSITION
                state[i + 1] = self.NEXT_TRANSITION

            matrix.append(state)
       
        return matrix

    def get_initial_state_alignment(self, n_states, sset):
        all_segments = [[] for i in range(n_states)]

        for seq in sset:
            # Segments vectors uniformly. One segment per state.
            segments = array_split(seq, n_states)

            # Concatenate each segments[i] with the segments[i] obtained
            # at the previous iteration
            all_segments = array_add(all_segments, segments)

        return all_segments

    def get_emission_matrix(self, n_states, sset):
        all_segments = self.get_initial_state_alignment(n_states, sset)

        matrix = []

        for i in range(n_states):
            matrix.append([
            
                # the means of our multivariate gaussian
                array_mean_vector(all_segments[i]),
                
                # the covariance matrix of our multivariate gaussian
                array_covariance_matrix(all_segments[i],
                                        non_diagonal=self.NON_DIAGONAL)
                
            ])

        return matrix

    def get_initial_hmm(self, sset):
        n_states = self.get_n_strokes(sset.char_code) * \
                   self.N_STATES_PER_STROKE

        pi = self.get_initial_state_probabilities(n_states)
        A = self.get_state_transition_matrix(n_states)
        B = self.get_emission_matrix(n_states, sset)

        hmm = MultivariateHmm(A, B, pi)
        
        return hmm
          

    def init(self):
        """Init HMMs"""

        self.load_char_dicts()

        feature_files = self.get_train_feature_files()

        if len(feature_files) == 0:
            raise ModelException, "No feature files found."
        
        if not os.path.exists(self.INIT_HMM_ROOT):
            os.makedirs(self.INIT_HMM_ROOT)

        for sset_file in feature_files:
            char_code = int(os.path.basename(sset_file[:-5]))

            sset = self.get_sequence_set(sset_file)
            sset.char_code = char_code

            hmm = self.get_initial_hmm(sset)

            output_file = os.path.join(self.INIT_HMM_ROOT,
                                       "%d.xml" % char_code)

            self.print_verbose(output_file)

            hmm.write(output_file)

    ########################################
    # Training...
    ########################################
    
    def get_initial_hmm_files(self):
        return glob.glob(os.path.join(self.INIT_HMM_ROOT, "*.xml"))

    def train(self):
        """Train HMMs"""
        initial_hmm_files = self.get_initial_hmm_files()

        if len(initial_hmm_files) == 0:
            raise ModelException, "No initial HMM files found."
        
        if not os.path.exists(self.TRAIN_HMM_ROOT):
            os.makedirs(self.TRAIN_HMM_ROOT)

        trainer = self.Trainer()
        viterbi_trainer = ViterbiTrainer(self.ViterbiCalculator(),
                                         non_diagonal=self.NON_DIAGONAL)
        
        for file in initial_hmm_files:
            char_code = int(os.path.basename(file).split(".")[0])
            hmm = MultivariateHmm.from_file(file)
            sset_file = os.path.join(self.TRAIN_FEATURES_ROOT,
                                     str(char_code) + ".sset")

            sset = self.get_sequence_set(sset_file)
            output_file = os.path.join(self.TRAIN_HMM_ROOT,
                                       "%d.xml" % char_code)

            if self.TRAINING in (self.TRAINING_VITERBI, self.TRAINING_BOTH):
                self.print_verbose("Viterbi training: " + output_file)
                viterbi_trainer.train(hmm, sset)

            if self.TRAINING in (self.TRAINING_BAUM_WELCH, self.TRAINING_BOTH):
                self.print_verbose("Baum-Welch training: " + output_file)
                trainer.train(hmm, sset)

            hmm.write(output_file)

    ########################################
    # Evaluation...
    ########################################    

    def get_eval_feature_files(self):
        return glob.glob(os.path.join(self.EVAL_FEATURES_ROOT, "*.sset"))

    def get_trained_hmm_files(self):
        return glob.glob(os.path.join(self.TRAIN_HMM_ROOT, "*.xml"))

    def eval_sequence(self, seq, hmms):
        res = []
        
        calculator = self.ViterbiCalculator()

        for hmm in hmms:
            logp = calculator.viterbi(hmm, seq)[1]
            res.append([hmm.char_code, logp])

        if str(seq.__class__.__name__) == "SequenceSet":
            # logp contains an array of log probabilities
            res.sort(key=lambda x:array_mean(x[1]), reverse=True)
        else:
            # logp contains a scalar
            res.sort(key=lambda x:x[1], reverse=True)

        return res

    def get_hmms_from_files(self, files):
        hmms = []
        
        for file in files:
            char_code = int(os.path.basename(file).split(".")[0])
            hmm = MultivariateHmm.from_file(file)
            hmm.char_code = char_code     
            hmms.append(hmm)
            
        return hmms

    def eval(self):
        """Evaluate HMMs"""
        trained_hmm_files = self.get_trained_hmm_files()

        if len(trained_hmm_files) == 0:
            raise ModelException, "No trained HMM files found."

        hmms = self.get_hmms_from_files(trained_hmm_files)
        
        n_total = 0
        n_match1 = 0
        n_match5 = 0
        n_match10 = 0
        char_codes = {}

        s = ""
        
        for file in self.get_eval_feature_files():
            char_code = int(os.path.basename(file).split(".")[0])
            char_codes[char_code] = 1
            sset = self.get_sequence_set(file)

            for seq in sset:
                res = [x[0] for x in self.eval_sequence(seq, hmms)][:10]

                if char_code in res:
                    n_match10 += 1 

                if char_code in res[:5]:
                    n_match5 += 1

                    position = str(res.index(char_code) + 1)
                else:
                    position = "X"

                matches = ", ".join([self.get_utf8_from_char_code(x) \
                                        for x in res[:5]])

                if char_code == res[0]:
                    n_match1 += 1

                utf8 = self.get_utf8_from_char_code(char_code)

                s += "%s\t%s\t%s\n" % (utf8, position, matches)

                n_total += 1

            self.print_verbose(file)

        n_classes = len(char_codes.keys())

        self.stderr_print("%d characters (%d samples)" % \
                           (n_classes, n_total))
        self.stderr_print("match1: ",
                          float(n_match1)/float(n_total) * 100,
                          "%")
        self.stderr_print("match5: ",
                          float(n_match5)/float(n_total) * 100,
                          "%")
        self.stderr_print("match10: ",
                          float(n_match10)/float(n_total) * 100,
                          "%")
        
        self.print_verbose(s)

    ########################################
    # Writing pad...
    ########################################

    def find_writing(self, writing):
        seq = Sequence(self.get_feature_vectors(writing))
        trained_hmm_files = self.get_trained_hmm_files()

        if len(trained_hmm_files) == 0:
            raise ModelException, "No trained HMM files found."
        
        hmms = self.get_hmms_from_files(trained_hmm_files)
        res = [x[0] for x in self.eval_sequence(seq, hmms)][:10]
        return [self.get_utf8_from_char_code(x) for x in res]
       

    def pad(self):
        """Find characters using a pad"""
        from lib.writing_pad import WritingPad
        
        trained_hmm_files = self.get_trained_hmm_files()

        if len(trained_hmm_files) == 0:
            raise ModelException, "No trained HMM files found."
        
        pad = WritingPad(self.find_writing)
        pad.run()

    def find(self):
        """Find a character in XML format"""
        if self.options.stdin:
            lines = []

            while True:
                line = sys.stdin.readline()
                lines.append(line)
                
                if line.strip() == "</character>":
                    xml = "\n".join(lines)
                    writing = xml_to_writing(xml)
                    print " ".join(self.find_writing(writing))
                    lines = []

                if len(line) == 0:
                    break

    ########################################
    # Clean...
    ########################################

    def get_pyc_files(self, folder):
        pyc_files = []
        
        for name in os.listdir(folder):
            full_path = os.path.join(folder, name)
            if os.path.isdir(full_path):
                pyc_files += self.get_pyc_files(full_path)
            elif full_path.endswith(".pyc"):
                pyc_files.append(full_path)
                
        return pyc_files

    def clean(self):
        """Delete temporary files"""
        for folder in (self.FEATURES_ROOT, self.HMM_ROOT):
            if os.path.exists(folder):
                shutil.rmtree(folder)

        for pyc_file in self.get_pyc_files(self.ROOT):
            os.unlink(pyc_file)

    ########################################
    # Commands...
    ########################################
    def commands(self):
        """Display command list"""
        for cmd in self.COMMANDS:
            meth = getattr(self, cmd)
            print "- %s (%s)" % (cmd, meth.__doc__)

    ########################################
    # Archive...
    ########################################

    def archive(self):
        """Make a copy of the model in a tar.gz file"""
        if not os.path.exists("archives"):
            os.mkdir("archives")

        filename = os.path.basename(self.ROOT) + "-" + \
                  str(datetime.datetime.now()).replace(" ", "@") + ".tar.gz"
        path = os.path.join("archives", filename)
        targz = tarfile.open(path, mode="w:gz")
        targz.add(self.ROOT)
        targz.close()
########NEW FILE########
__FILENAME__ = model
# -*- coding: utf-8 -*-

# Copyright (C) 2008 The Tegaki project contributors
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

# Contributors to this file:
# - Mathieu Blondel

import os
from tegaki.arrayutils import *
import models.basic.model

class Model(models.basic.model.Model):
    """
    Title: basic_latin
    """

    def __init__(self, *args):
        models.basic.model.Model.__init__(self, *args)

        self.N_STATES_PER_STROKE = 8
        self.TRAIN_CORPORA = ["latin-writer1"]
        self.EVAL_CORPORA = self.TRAIN_CORPORA

        self.ROOT = os.path.join("models", "basic_latin")
        self.update_folder_paths()

    def get_feature_vectors(self, writing):
        """
        Get deltax and deltay as feature vectors.
        """
        return models.basic.model.Model.get_feature_vectors(self,
                                                            writing,
                                                            normalize=True)
        
########NEW FILE########
__FILENAME__ = model
# -*- coding: utf-8 -*-

# Copyright (C) 2008 The Tegaki project contributors
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

# Contributors to this file:
# - Mathieu Blondel

import os
import glob

from tegaki.arrayutils import *
import models.basic.model

class Model(models.basic.model.Model):
    """
    Title: cartesian
    Feature vectors: (x, y)!
    """

    def __init__(self, *args):
        models.basic.model.Model.__init__(self, *args)

        self.SAMPLING = 0.5
        self.N_STATES_PER_STROKE = 3
        self.N_DIMENSIONS = 2

        self.TRAIN_CORPORA = ["japanese-learner1", "japanese-native1"]
        self.EVAL_CORPORA = ["japanese-learner1", "japanese-native1"]

        self.ROOT = os.path.join("models", "cartesian")
        self.update_folder_paths()

    ########################################
    # Feature extraction...
    ########################################

    def get_feature_vectors(self, writing):
        """
        Get cartesian coordinates.
        """
        strokes = writing.get_strokes()
        vectors = [(x,y) for stroke in strokes for x,y in stroke]
        vectors = array_sample(vectors, self.SAMPLING)
        return vectors

########NEW FILE########
__FILENAME__ = model
# -*- coding: utf-8 -*-

# Copyright (C) 2008 The Tegaki project contributors
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

# Contributors to this file:
# - Mathieu Blondel

import os
import glob

from tegaki.arrayutils import *
import models.basic.model

class Model(models.basic.model.Model):
    """
    Feature vectors: derivative
    """

    def __init__(self, *args):
        models.basic.model.Model.__init__(self, *args)

        self.SAMPLING = 0.5
        self.N_STATES_PER_STROKE = 3
        self.N_DIMENSIONS = 2
        self.WINDOW_SIZE = 2

        self.TRAIN_CORPORA = ["japanese-learner1", "japanese-native1"]
        self.EVAL_CORPORA = ["japanese-learner1", "japanese-native1"]

        self.ROOT = os.path.join("models", "derivative")
        self.update_folder_paths()

    ########################################
    # Feature extraction...
    ########################################

    def get_feature_vectors(self, writing):
        """
        Get derivative as feature vectors.
        Formula obtained from
        "An Online Handwriting Recognition System For Turkish"
        Esra Vural, Hakan Erdogan, Kemal Oflazer, Berrin Yanikoglu
        Sabanci University, Tuzla, Istanbul, Turkey
        """
        arr = []
        
        strokes = writing.get_strokes()

        sampling = int(1 / self.SAMPLING)

        for stroke in strokes:

            for i in range(self.WINDOW_SIZE,
                           len(stroke) - self.WINDOW_SIZE,
                           sampling):
            
                xnum = 0
                ynum = 0
            
                for teta in range(1, self.WINDOW_SIZE + 1):
                    xnum += (stroke[i+teta][0] - stroke[i-teta][0]) * teta
                    ynum += (stroke[i+teta][1] - stroke[i-teta][1]) * teta

                denom = 0

                for teta in range(1, self.WINDOW_SIZE + 1):
                    denom += teta ** 2

                denom *= 2

                xderivative = xnum / denom
                yderivative = ynum / denom

                arr.append([xderivative, yderivative])
                
        return arr    

########NEW FILE########
__FILENAME__ = model
# -*- coding: utf-8 -*-

# Copyright (C) 2008 The Tegaki project contributors
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

# Contributors to this file:
# - Mathieu Blondel

import os
import glob
import math

from tegaki.arrayutils import *
from tegaki.mathutils import *
import models.basic.model

class Model(models.basic.model.Model):
    """
    Title: direction
    Feature vectors: (distance, angle)
        distance = euclidean distance between two consecutive samples.
        angle = angle of the current sample to the origin.
    """

    def __init__(self, *args):
        models.basic.model.Model.__init__(self, *args)

        self.SAMPLING = 0.5
        self.N_STATES_PER_STROKE = 3
        self.N_DIMENSIONS = 2

        self.TRAIN_CORPORA = ["japanese-learner1", "japanese-native1"]
        self.EVAL_CORPORA = ["japanese-learner1", "japanese-native1"]

        self.ROOT = os.path.join("models", "direction")
        self.update_folder_paths()

    ########################################
    # Feature extraction...
    ########################################

    def get_feature_vectors(self, writing):
        """
        Get (distance, angle).
        """
        strokes = writing.get_strokes()
        vectors = [(x,y) for stroke in strokes for x,y in stroke]
        vectors = array_sample(vectors, self.SAMPLING)

        arr = []

        for i in range(1, len(vectors)):
            ((x1, y1), (x2, y2)) = (vectors[i-1], vectors[i])

            distance = euclidean_distance((x1,y1), (x2,y2))
            r, teta = cartesian_to_polar(x2, y2)

            arr.append((distance, teta))

        return arr
########NEW FILE########
__FILENAME__ = model
# -*- coding: utf-8 -*-

# Copyright (C) 2008 The Tegaki project contributors
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

# Contributors to this file:
# - Mathieu Blondel

import os
import glob
import math

from tegaki.arrayutils import *
from tegaki.mathutils import *
import models.basic.model as base_model

class Model(base_model.Model):
    
    def __init__(self, *args):
        base_model.Model.__init__(self, *args)

        self.SAMPLING = 0.5
        self.N_STATES_PER_STROKE = 3
        self.N_DIMENSIONS = 2

        self.TRAIN_CORPORA = ["japanese-learner1", "japanese-native1"]
        self.EVAL_CORPORA = ["japanese-learner1", "japanese-native1"]

        self.ROOT = os.path.join("models", "init-cum-sum")
        self.update_folder_paths()

    def get_consecutive_distances(self, seq):
        dists = []
        for i in range(len(seq)-1):
            vect = seq[i]
            next_vect = seq[i+1]
            dists.append(euclidean_distance(vect, next_vect))
        return dists # contains N-1 distances for a sequence of size N

    def get_initial_state_alignment(self, n_states, sset):
        # the idea of this segmentation is to assign more states
        # to portions that vary a lot
        # it doesn't work well for characters with a high degree of stationarity

        all_segments = [[] for i in range(n_states)]

        for seq in sset:
            dists = self.get_consecutive_distances(seq)
            cum_sum = sum(dists)
            step = cum_sum / n_states

            curr_state = 0
            curr_cum_sum = 0
            
            all_segments[0].append(seq[0])

            for i, dist in enumerate(dists):
                curr_cum_sum += dist
                if curr_cum_sum > (curr_state + 1) * step and \
                   curr_state < n_states - 1:
                    curr_state += 1
                all_segments[curr_state].append(seq[i+1])

        if [] in all_segments:
            # there was an empty segment, fall back to uniform segmentation
            all_segments = base_model.Model.get_initial_state_alignment(
                                self, n_states, sset)
       
        return all_segments


########NEW FILE########
__FILENAME__ = model
# -*- coding: utf-8 -*-

# Copyright (C) 2008 The Tegaki project contributors
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

# Contributors to this file:
# - Mathieu Blondel

import os
import glob
import math

from tegaki.arrayutils import *
from tegaki.mathutils import *
import models.basic.model

class Model(models.basic.model.Model):
    """
    Title: polar
    Feature vectors: (r, teta)
    """

    def __init__(self, *args):
        models.basic.model.Model.__init__(self, *args)

        self.SAMPLING = 0.5
        self.N_STATES_PER_STROKE = 3
        self.N_DIMENSIONS = 2

        self.TRAIN_CORPORA = ["japanese-learner1", "japanese-native1"]
        self.EVAL_CORPORA = ["japanese-learner1", "japanese-native1"]

        self.ROOT = os.path.join("models", "polar")
        self.update_folder_paths()

    ########################################
    # Feature extraction...
    ########################################

    def get_feature_vectors(self, writing):
        """
        Get polar coordinates.
        """
        strokes = writing.get_strokes()
        vectors = [(x,y) for stroke in strokes for x,y in stroke]
        vectors = array_sample(vectors, self.SAMPLING)
        vectors = [cartesian_to_polar(x,y) for x, y in vectors]
        vectors = [(r, math.degrees(teta)) for r, teta in vectors]
        return vectors

########NEW FILE########
__FILENAME__ = model
# -*- coding: utf-8 -*-

# Copyright (C) 2008 The Tegaki project contributors
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

# Contributors to this file:
# - Mathieu Blondel

import os
import glob

from tegaki.arrayutils import *
import models.basic.model

from lib.exceptions import *

from lib.hmm import Sequence, SequenceSet, MultivariateHmm
from lib import hmm

class Model(models.basic.model.Model):
    """
    Title: prop-n-states
    Number of states: proportional to the number of observations
    """

    def __init__(self, *args):
        models.basic.model.Model.__init__(self, *args)

        self.SAMPLING = 0.5
        self.AVERAGE_N_STATES = 25
        self.N_DIMENSIONS = 2
        self.NON_DIAGONAL = True

        self.CORPORA = ["japanese-learner1", "japanese-native1"]

        self.ROOT = os.path.join("models", "prop_n_states")
        self.update_folder_paths()


    def get_n_observations(self, sset):
        n_observations = sum([len(seq) for seq in sset])
        n_characters = len(sset)
        return (n_observations, n_characters)

    def get_initial_hmm(self, sset, avg_n_obs_per_char):
        obs, chars = self.get_n_observations(sset)

        n_obs = float(obs) / chars
        
        n_states = round(n_obs / avg_n_obs_per_char * self.AVERAGE_N_STATES)
        n_states = int(n_states)

        self.print_verbose("%s (%d): %d" % \
                            (self.get_utf8_from_char_code(sset.char_code),
                             sset.char_code,
                             n_states))
        
        pi = self.get_initial_state_probabilities(n_states)
        A = self.get_state_transition_matrix(n_states)
        B = self.get_emission_matrix(n_states, sset)

        return MultivariateHmm(A, B, pi)
          

    def init(self):
        self.load_char_dicts()

        feature_files = self.get_train_feature_files()

        if len(feature_files) == 0:
            raise ModelException, "No feature files found."
        
        if not os.path.exists(self.INIT_HMM_ROOT):
            os.makedirs(self.INIT_HMM_ROOT)

        ssets = []

        # calculate the average number of observations for all characters
        n_observations = 0
        n_characters = 0
        
        for sset_file in feature_files:
            char_code = int(os.path.basename(sset_file[:-5]))
            
            sset = self.get_sequence_set(sset_file)
            sset.char_code = char_code
            ssets.append(sset)

            obs, chars = self.get_n_observations(sset)
            n_observations += obs
            n_characters += chars

        avg_n_obs_per_char = float(n_observations) / n_characters
            
        for sset in ssets:
            hmm = self.get_initial_hmm(sset, avg_n_obs_per_char)

            output_file = os.path.join(self.INIT_HMM_ROOT,
                                       "%d.xml" % sset.char_code)

            hmm.write(output_file)
            
########NEW FILE########
__FILENAME__ = model
# -*- coding: utf-8 -*-

# Copyright (C) 2008 The Tegaki project contributors
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

# Contributors to this file:
# - Mathieu Blondel

import os
import sys
import glob

import zinnia

from tegaki.character import *
from lib.exceptions import *

import models.basic.model

class Model(models.basic.model.Model):
    """
    Model using Support Vector Machines with the Zinnia library.
    """

    def __init__(self, *args):
        models.basic.model.Model.__init__(self, *args)

        self.TRAIN_CORPORA = ["japanese-learner1", "japanese-native1"]
        self.EVAL_CORPORA = ["japanese-learner1", "japanese-native1"]

        self.ROOT = os.path.join("models", "svm")
        self.update_folder_paths()

    ########################################
    # Feature extraction...
    ########################################

    def fextract(self):
        pass # nothing to do

    ########################################
    # Initialization...
    ########################################
    
    def init(self):
        pass # nothing to do

    ########################################
    # Training...
    ########################################

    def char_to_sexp(self, char):
        strokes_str = ""
        for stroke in char.get_writing().get_strokes():
            strokes_str += "("
            strokes_str += "".join(["(%d %d)" % (x,y) for x,y in stroke])
            strokes_str += ")"

        return "(character (value %s)(width 1000)(height 1000)(strokes %s))" % \
                    (char.get_utf8(), strokes_str)
        

    def train(self):
        trainer = zinnia.Trainer()
        zinnia_char = zinnia.Character()
            
        for char_code, xml_list in self.train_xml_files_dict.items():

            for xml_file in xml_list:
                character = self.get_character(xml_file)
                sexp = self.char_to_sexp(character)
                
                if (not zinnia_char.parse(sexp)):
                    print zinnia_char.what()
                    exit(1)
                else:
                    trainer.add(zinnia_char)

        path = os.path.join(self.ROOT, "model")
        trainer.train(path)
                
                    

    ########################################
    # Evaluation...
    ########################################
      
    def recognize(self, recognizer, writing):
        character = Character()
        character.set_utf8("?")
        character.set_writing(writing)
        sexp = self.char_to_sexp(character)

        zinnia_char = zinnia.Character()

        if (not zinnia_char.parse(sexp)):
            print zinnia_char.what()
            exit(1)

        results = recognizer.classify(zinnia_char, 10)

        return [results.value(i) for i in range(0, (results.size() - 1))]

    def eval(self):   
        path = os.path.join(self.ROOT, "model")

        if not os.path.exists(path):
            raise ModelException, "No model found."
        
        n_total = 0
        n_match1 = 0
        n_match5 = 0
        n_match10 = 0

        s = ""

        recognizer = zinnia.Recognizer()
        recognizer.open(path)
        
        for char_code, xml_list in self.eval_xml_files_dict.items():
            for xml_file in xml_list:
                utf8 = self.get_utf8_from_char_code(char_code)
                character = self.get_character(xml_file)
                res = self.recognize(recognizer, character.get_writing())

                if utf8 in res:
                    n_match10 += 1 

                if utf8 in res[:5]:
                    n_match5 += 1

                    position = str(res.index(utf8) + 1)
                    matches = ", ".join(res[:5])
                else:
                    position = "X"
                    matches = ""

                if utf8 == res[0]:
                    n_match1 += 1

                n_total += 1

                s += "%s\t%s\t%s\n" % (utf8, position, matches)

            

        self.stderr_print("match1: ",
                          float(n_match1)/float(n_total) * 100,
                          "%")
        self.stderr_print("match5: ",
                          float(n_match5)/float(n_total) * 100,
                          "%")
        self.stderr_print("match10: ",
                          float(n_match10)/float(n_total) * 100,
                          "%")
        
        self.print_verbose(s)

    ########################################
    # Writing pad...
    ########################################

    def find_writing(self, writing):

        path = os.path.join(self.ROOT, "model")

        if not os.path.exists(path):
            raise ModelException, "No model found."

        recognizer = zinnia.Recognizer()
        recognizer.open(path)

        return self.recognize(recognizer, writing)


    def writing_pad(self):
        from lib.writing_pad import WritingPad

        path = os.path.join(self.ROOT, "model")

        if not os.path.exists(path):
            raise ModelException, "No model found."
        
        pad = WritingPad(self.find_writing)
        pad.run()
        
########NEW FILE########
__FILENAME__ = canvas
# -*- coding: utf-8 -*-

# Copyright (C) 2008 The Tegaki project contributors
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

# Contributors to this file:
# - Mathieu Blondel

import gtk
from gtk import gdk
import gobject
import pango
import math
import time

from tegaki.character import *

class Canvas(gtk.Widget):
    """
    A character drawing canvas.

    This widget receives the input from the user and can return the
    corresponding L{tegaki.Writing} objects.

    It also has a "replay" method which can display a stroke-by-stroke
    animation of the current writing.

    The code was originally ported from Tomoe (C language).
    Since then many additional features were added.
    """

    #: Default canvas size
    DEFAULT_WIDTH = 400
    DEFAULT_HEIGHT = 400

    #: Default canvas size
    DEFAULT_REPLAY_SPEED = 50 # msec

    #: - the stroke-added signal is emitted when the user has added a stroke
    #: - the drawing-stopped signal is emitted when the user has stopped drawing
    __gsignals__ = {
        "stroke_added" :     (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, []),
        "drawing_stopped" :  (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, [])
    }
    
    def __init__(self):
        gtk.Widget.__init__(self)
        
        self._width = self.DEFAULT_WIDTH
        self._height = self.DEFAULT_HEIGHT

        self._drawing = False
        self._pixmap = None

        self._writing = Writing()

        self._locked = False

        self._drawing_stopped_time = 0
        self._drawing_stopped_id = 0
        self._draw_annotations = True
        self._need_draw_axis = True

        self._handwriting_line_gc = None
        self._annotation_gc = None
        self._axis_gc = None
        self._stroke_gc = None
        self._background_writing_gc = None
        self._background_gc = None

        self._background_color = (0xFFFF, 0xFFFF, 0xFFFF)

        self._background_character = None
        self._background_writing = None

        self._first_point_time = None

        self.connect("motion_notify_event", self.motion_notify_event)
        
    # Events...

    def do_realize(self):
        """
        Called when the widget should create all of its
        windowing resources.  We will create our gtk.gdk.Window.
        """
        # Set an internal flag telling that we're realized
        self.set_flags(self.flags() | gtk.REALIZED)

        # Create a new gdk.Window which we can draw on.
        # Also say that we want to receive exposure events
        # and button click and button press events
        self.window = gdk.Window(self.get_parent_window(),

                                 x=self.allocation.x,
                                 y=self.allocation.y,
                                 width=self.allocation.width,
                                 height=self.allocation.height,

                                 window_type=gdk.WINDOW_CHILD,
                                 wclass=gdk.INPUT_OUTPUT,
                                 visual=self.get_visual(),
                                 colormap=self.get_colormap(),

                                 event_mask=gdk.EXPOSURE_MASK |
                                            gdk.BUTTON_PRESS_MASK |
                                            gdk.BUTTON_RELEASE_MASK |
                                            gdk.POINTER_MOTION_MASK |
                                            gdk.POINTER_MOTION_HINT_MASK |
                                            gdk.ENTER_NOTIFY_MASK |
                                            gdk.LEAVE_NOTIFY_MASK)


        # Associate the gdk.Window with ourselves, Gtk+ needs a reference
        # between the widget and the gdk window
        self.window.set_user_data(self)

        # Attach the style to the gdk.Window, a style contains colors and
        # GC contextes used for drawing
        self.style.attach(self.window)

        # The default color of the background should be what
        # the style (theme engine) tells us.
        self.style.set_background(self.window, gtk.STATE_NORMAL)
        self.window.move_resize(*self.allocation)

        # Font
        font_desc = pango.FontDescription("Sans 12")
        self.modify_font(font_desc)

        self._init_gc()

    def do_unrealize(self):
        """
        The do_unrealized method is responsible for freeing the GDK resources
        De-associate the window we created in do_realize with ourselves
        """
        self.window.destroy()
    
    def do_size_request(self, requisition):
       """
       The do_size_request method Gtk+ is called on a widget to ask it the
       widget how large it wishes to be.
       It's not guaranteed that gtk+ will actually give this size to the
       widget.
       """
       requisition.height = self.DEFAULT_HEIGHT
       requisition.width = self.DEFAULT_WIDTH

    def do_size_allocate(self, allocation):
        """
        The do_size_allocate is called when the actual
        size is known and the widget is told how much space
        could actually be allocated."""

        self.allocation = allocation
        self._width = self.allocation.width
        self._height = self.allocation.height        
 
        if self.flags() & gtk.REALIZED:
            self.window.move_resize(*allocation)
            
            self._pixmap = gdk.Pixmap(self.window,
                                      self._width,
                                      self._height)

            self.refresh()

    def do_expose_event(self, event):
        """
        This is where the widget must draw itself.
        """
        retval = False
        
        self.window.draw_drawable(self.style.fg_gc[self.state],
                                  self._pixmap,
                                  event.area.x, event.area.y,
                                  event.area.x, event.area.y,
                                  event.area.width, event.area.height)

        return retval
    
    def motion_notify_event(self, widget, event):
        retval = False

        if self._locked or not self._drawing:
            return retval

        if event.is_hint:
            x, y, state = event.window.get_pointer()
        else:
            x = event.x
            y = event.y
            state = event.state

        x, y = self._internal_coordinates(x, y)

        point = Point()
        point.x = x
        point.y = y
        point.timestamp = event.time - self._first_point_time
        #point.pressure = pressure
        #point.xtilt = xtilt
        #point.ytilt = ytilt

        self._append_point(point)

        return retval

    def do_button_press_event(self, event):
        retval = False

        if self._locked:
            return retval

        if self._drawing_stopped_id > 0:
            gobject.source_remove(self._drawing_stopped_id)
            self._drawing_stopped_id = 0

        if event.button == 1:
            self._drawing = True

            x, y = self._internal_coordinates(event.x, event.y)

            point = Point()
            point.x = x
            point.y = y

            if self._writing.get_n_strokes() == 0:
                self._first_point_time = event.time
                point.timestamp = 0
            else:
                if self._first_point_time is None:
                    # in the case we add strokes to an imported character
                    self._first_point_time = event.time - \
                                             self._writing.get_duration() - 50
                                         
                point.timestamp = event.time - self._first_point_time
                
            #point.pressure = pressure
            #point.xtilt = xtilt
            #point.ytilt = ytilt
            
            self._writing.move_to_point(point)

        return retval

    def do_button_release_event(self, event):
        retval = False

        if self._locked or not self._drawing:
            return retval

        self._drawing = False

        self.refresh(force_draw=True)

        self.emit("stroke_added")

        if self._drawing_stopped_time > 0:

            def _on_drawing_stopped():
                self.emit("drawing_stopped")
                return False
             
            self._drawing_stopped_id = \
                            gobject.timeout_add(self._drawing_stopped_time,
                            _on_drawing_stopped)

        self._draw_background_writing_stroke()

        return retval

    # Private...

    def _gc_set_foreground (self, gc, color):
        colormap = gdk.colormap_get_system ()

        if color:
            color = colormap.alloc_color(color, True, True)
            gc.set_foreground(color)
        else:
            default_color = gdk.Color(0x0000, 0x0000, 0x0000, 0)
            default_color = colormap.alloc_color(default_color, True, True)
            gc.set_foreground(default_color)

    def _init_gc(self):
                                                  
        if not self._handwriting_line_gc:
            color = gdk.Color(red=0x0000, blue=0x0000, green=0x0000)
            self._handwriting_line_gc = gdk.GC(self.window)
            self._gc_set_foreground(self._handwriting_line_gc, color)
            self._handwriting_line_gc.set_line_attributes(4,
                                                         gdk.LINE_SOLID,
                                                         gdk.CAP_ROUND,
                                                         gdk.JOIN_ROUND)

        if not self._stroke_gc:
            color = gdk.Color(red=0xff00, blue=0x0000, green=0x0000)
            self._stroke_gc = gdk.GC(self.window)
            self._gc_set_foreground(self._stroke_gc, color)
            self._stroke_gc.set_line_attributes(4,
                                                gdk.LINE_SOLID,
                                                gdk.CAP_ROUND,
                                                gdk.JOIN_ROUND)

        if not self._background_writing_gc:
            color = gdk.Color(red=0xcccc, blue=0xcccc, green=0xcccc)
            self._background_writing_gc = gdk.GC(self.window)
            self._gc_set_foreground(self._background_writing_gc, color)
            self._background_writing_gc.set_line_attributes(4,
                                                            gdk.LINE_SOLID,
                                                            gdk.CAP_ROUND,
                                                            gdk.JOIN_ROUND)
        if not self._annotation_gc:
            color = gdk.Color(red=0x8000, blue=0x0000, green=0x0000)
            self._annotation_gc = gdk.GC(self.window)
            self._gc_set_foreground(self._annotation_gc, color)

        if not self._axis_gc:
            color = gdk.Color(red=0x8000, blue=0x8000, green=0x8000)
            self._axis_gc = gdk.GC(self.window)
            self._gc_set_foreground(self._axis_gc, color)
            self._axis_gc.set_line_attributes(1,
                                             gdk.LINE_ON_OFF_DASH,
                                             gdk.CAP_BUTT,
                                             gdk.JOIN_ROUND)

        if not self._background_gc:
            color = gdk.Color(*self._background_color)
            self._background_gc = gdk.GC(self.window)
            self._gc_set_foreground(self._background_gc, color)

    def _internal_coordinates(self, x, y):
        """
        Converts window coordinates to internal coordinates.
        """
        sx = float(self._writing.get_width()) / self._width
        sy = float(self._writing.get_height()) / self._height
        
        return (int(x * sx), int(y * sy))
    
    def _window_coordinates(self, x, y):
        """
        Converts internal coordinates to window coordinates.
        """
        sx = float(self._width) / self._writing.get_width()
        sy = float(self._height) / self._writing.get_height()
        
        return (int(x * sx), int(y * sy))

    def _append_point(self, point):
        # x and y are internal coordinates
        
        p2 = (point.x, point.y)
        
        strokes = self._writing.get_strokes(full=True) 

        p1 = strokes[-1][-1].get_coordinates()

        self._draw_line(p1, p2, self._handwriting_line_gc, force_draw=True)

        self._writing.line_to_point(point)
        
    def _draw_stroke(self, stroke, index, gc, draw_annotation=True):
        l = len(stroke)
        
        for i in range(l):
            if i == l - 1:
                break

            p1 = stroke[i]
            p1 = (p1.x, p1.y)
            p2 = stroke[i+1]
            p2 = (p2.x, p2.y)

            self._draw_line(p1, p2, gc)

        if draw_annotation:
            self._draw_annotation(stroke, index)

    def _draw_line(self, p1, p2, line_gc, force_draw=False):
        # p1 and p2 are two points in internal coordinates
        
        p1 = self._window_coordinates(*p1)
        p2 = self._window_coordinates(*p2)
        
        self._pixmap.draw_line(line_gc, p1[0], p1[1], p2[0], p2[1])

        if force_draw:
            x = min(p1[0], p2[0]) - 2
            y = min(p1[1], p2[1]) - 2
            width = abs(p1[0] - p2[0]) + 2 * 2
            height = abs(p1[1] - p2[1]) + 2 * 2

            self.queue_draw_area(x, y, width, height)

    def _draw_annotation(self, stroke, index, force_draw=False):
        x, y = self._window_coordinates(stroke[0].x, stroke[0].y)

        if len(stroke) == 1:
            dx, dy = x, y
        else:
            last_x, last_y = self._window_coordinates(stroke[-1].x,
                                                      stroke[-1].y)
            dx, dy = last_x - x, last_y - y
            if dx == dy == 0:
                dx, dy = x, y

        dl = math.sqrt(dx*dx + dy*dy)

        if dy <= dx:
            sign = 1
        else:
            sign = -1

        num = str(index + 1)
        layout = self.create_pango_layout(num)
        width, height = layout.get_pixel_size()

        r = math.sqrt (width*width + height*height)

        x += (0.5 + (0.5 * r * dx / dl) + (sign * 0.5 * r * dy / dl) - \
              (width / 2))
              
        y += (0.5 + (0.5 * r * dy / dl) - (sign * 0.5 * r * dx / dl) - \
              (height / 2))

        x, y = int(x), int(y)

        self._pixmap.draw_layout(self._annotation_gc, x, y, layout)

        if force_draw:
            self.queue_draw_area(x-2, y-2, width+4, height+4)

    def _draw_axis(self):        
        self._pixmap.draw_line(self._axis_gc,
                               self._width / 2, 0,
                               self._width / 2, self._height)

        self._pixmap.draw_line(self._axis_gc,
                               0, self._height / 2,
                               self._width, self._height / 2)

    def _draw_background(self):
        self._pixmap.draw_rectangle(self._background_gc,
                                    True,
                                    0, 0,
                                    self.allocation.width,
                                    self.allocation.height)

        if self._need_draw_axis:
            self._draw_axis()


    def _draw_background_character(self):
        if self._background_character:
            raise NotImplementedError

    def _draw_background_writing(self):
        if self._background_writing:
            strokes = self._background_writing.get_strokes(full=True)

            start = self._writing.get_n_strokes() + 1
            
            for i in range(start, len(strokes)):
                self._draw_stroke(strokes[i],
                                  i,
                                  self._background_writing_gc,
                                  draw_annotation=False)

    def _draw_background_writing_stroke(self):
        if self._background_writing and self._writing.get_n_strokes() < \
           self._background_writing.get_n_strokes():

            time.sleep(0.5)

            l = self._writing.get_n_strokes()

            self._strokes = self._background_writing.get_strokes(full=True)
            self._strokes = self._strokes[l:l+1]
        
            self._curr_stroke = 0
            self._curr_point = 1
            self._refresh_writing = False

            speed = self._get_speed(self._curr_stroke)

            gobject.timeout_add(speed, self._on_animate)

                

    def _redraw(self):
        self.window.draw_drawable(self.style.fg_gc[self.state],
                                  self._pixmap,
                                  0, 0,
                                  0, 0,
                                  self.allocation.width,
                                  self.allocation.height)

    def _get_speed(self, index):
        if self._speed:
            speed = self._speed
        else:
            duration = self._strokes[index].get_duration()
            if duration:
                speed = duration / len(self._strokes[index])
            else:
                speed = self.DEFAULT_REPLAY_SPEED
        return speed       

    def _on_animate(self):
        self._locked = True
        
        if self._curr_stroke > 0 and self._curr_point == 1 and \
           not self._speed:            
            # inter stroke duration
            # t2 = self._strokes[self._curr_stroke][0].timestamp
            # t1 = self._strokes[self._curr_stroke - 1][-1].timestamp
            # time.sleep(float(t2 - t1) / 1000)
            time.sleep(float(self._get_speed(self._curr_stroke))/1000)
        
        p1 = self._strokes[self._curr_stroke][self._curr_point - 1]
        p1 = (p1.x, p1.y)
        p2 = self._strokes[self._curr_stroke][self._curr_point]
        p2 = (p2.x, p2.y)

        self._draw_line(p1, p2, self._stroke_gc, force_draw=True)

        if len(self._strokes[self._curr_stroke]) == self._curr_point + 1:
            # if we reach the stroke last point
                         
            if self._draw_annotations:
                self._draw_annotation(self._strokes[self._curr_stroke],
                                                    self._curr_stroke)
                                                
            self._curr_point = 1
            self._curr_stroke += 1
                
            if len(self._strokes) != self._curr_stroke:
                # if there are remaining strokes to process

                speed = self._get_speed(self._curr_stroke)

                gobject.timeout_add(speed, self._on_animate)
            else:
                # last stroke and last point was reached
                self._locked = False
                
            if self._refresh_writing:
                self.refresh(n_strokes=self._curr_stroke, force_draw=True)
                
            return False
        else:
            self._curr_point += 1

        return True

    def _refresh(self, writing, n_strokes=None, force_draw=False):
        if self.flags() & gtk.REALIZED and self._pixmap:
            self._draw_background()

            self._draw_background_character()
            self._draw_background_writing()

            strokes = writing.get_strokes(full=True)

            if not n_strokes:
                n_strokes = len(strokes)

            for i in range(n_strokes):
                self._draw_stroke(strokes[i], i, self._handwriting_line_gc,
                                  draw_annotation=self._draw_annotations)

            if force_draw:
                self._redraw()

    # Public...

    def get_drawing_stopped_time(self):
        """
        Get the inactivity time after which a character is considered drawn.

        @rtype: int
        @return: time in milliseconds
        """
        return self._drawing_stopped_time

    def set_drawing_stopped_time(self, time_msec):
        """
        Set the inactivity time after which a character is considered drawn.

        @type time_msec: int
        @param time_msec: time in milliseconds
        """
        self._drawing_stopped_time = time_msec

    def set_draw_annotations(self, draw_annotations):
        """
        Set whether to display stroke-number annotations or not.

        @type draw_annotations: boolean
        """
        self._draw_annotations = draw_annotations

    def get_draw_annotations(self):
        """
        Return whether stroke-number annotations are displayed or not.
        """
        return self._draw_annotations

    def set_draw_axis(self, draw_axis):
        self._need_draw_axis = draw_axis

    def get_draw_axis(self):
        return self._need_draw_axis

    def refresh(self, n_strokes=None, force_draw=False):
        """
        Update the screen.
        """
        if self._writing:
            self._refresh(self._writing,
                         n_strokes=n_strokes,
                         force_draw=force_draw)

    def replay(self, speed=None):
        """
        Display an animation of the current writing.
        One point is drawn every "speed" msec.

        If speed is None, uses the writing original speed when available or
        DEFAULT_REPLAY_SPEED when not available.

        @type speed: int
        @type speed: time between each point in milliseconds
        """
        self._draw_background()
        self._redraw()

        self._strokes = self._writing.get_strokes(full=True)

        if len(self._strokes) == 0:
            return
        
        self._curr_stroke = 0
        self._curr_point = 1
        self._speed = speed
        self._refresh_writing = True

        speed = self._get_speed(self._curr_stroke)

        gobject.timeout_add(speed, self._on_animate)

    def get_writing(self, writing_width=None, writing_height=None):
        """
        Return a L{tegaki.Writing} object for the current handwriting.

        @type writing_width: int
        @param writing_width: the width that the writing should have or \
                              None if default
        @type writing_height: int
        @param writing_height: the height that the writing should have or \
                              None if default
        @rtype: Writing

        """

        if writing_width and writing_height:
            # Convert to requested size
            xratio = float(writing_width) / self._writing.get_width()
            yratio = float(writing_height) / self._writing.get_height()

            return self._writing.resize(xratio, yratio)
        else:
            return self._writing

    def set_writing(self, writing, writing_width=None, writing_height=None):

        if writing_width and writing_height:
            # Convert to internal size
            xratio = float(self._writing.get_width()) / writing_width
            yratio = float(self._writing.get_height()) / writing_height
           
            self._writing = self._writing.resize(xratio, yratio)
        else:
            self._writing = writing

        
        self.refresh(force_draw=True)

    def clear(self):
        """
        Erase the current writing.
        """
        self._writing.clear()

        self.refresh(force_draw=True)

    def revert_stroke(self):
        """
        Undo the latest stroke
        """
        n = self._writing.get_n_strokes()

        if n > 0:
            self._writing.remove_last_stroke()
            self.refresh(force_draw=True)

    def normalize(self):
        """
        Normalize the current writing. (See L{tegaki.normalize})
        """
        self._writing.normalize()
        self.refresh(force_draw=True)

    def smooth(self):
        """
        Smooth the current writing. (See L{tegaki.smooth})
        """
        self._writing.smooth()
        self.refresh(force_draw=True)

    def set_background_character(self, character):
        """
        Set a character as background.

        @type character: str
        """
        self._background_character = character

    def get_background_writing(self):
        return self._background_writing
    
    def set_background_writing(self, writing, speed=25):
        """
        Set a writing as background. 

        Strokes of the background writing are displayed one at a time. 
        This is intended to let users "follow" the background writing like a
        template.

        @type writing: L{tegaki.Writing}
        """
        self.clear()
        self._background_writing = writing
        self._speed = speed
        time.sleep(0.5)
        self._draw_background_writing_stroke()
        self.refresh(force_draw=True)

    def set_background_color(self, r, g, b):
        """
        Set background color.

        @type r: int
        @param r: red
        @type g: int
        @param g: green
        @type b: int
        @param b: blue
        """
        self._background_color = (r, g, b)
        
        if self._background_gc:
            # This part can only be called after the widget is visible
            color = gdk.Color(red=r, green=g, blue=b)
            self._background_gc = gdk.GC(self.window)
            self._gc_set_foreground(self._background_gc, color)
            self.refresh(force_draw=True)
        
gobject.type_register(Canvas)
        
if __name__ == "__main__":
    import sys
    import copy
    
    def on_stroke_added(widget):
        print "stroke added!"
        
    window = gtk.Window(gtk.WINDOW_TOPLEVEL)
    
    canvas = Canvas()
    
    canvas.connect("stroke_added", on_stroke_added)
    
    if len(sys.argv) >= 2:

        if sys.argv[1] == "upsample":
            try:
                n = int(sys.argv[2])
            except IndexError:
                n = 5

            def on_drawing_stopped(widget):
                print "before: %d pts" % widget.get_writing().get_n_points()
                widget.get_writing().upsample(n)
                widget.refresh(force_draw=True)
                print "after: %d pts" % widget.get_writing().get_n_points()

        elif sys.argv[1] == "upsamplet":
            try:
                n = int(sys.argv[2])
            except IndexError:
                n = 10

            def on_drawing_stopped(widget):
                print "before: %d pts" % widget.get_writing().get_n_points()
                widget.get_writing().upsample_threshold(n)
                widget.refresh(force_draw=True)
                print "after: %d pts" % widget.get_writing().get_n_points()

        elif sys.argv[1] == "downsample":
            try:
                n = int(sys.argv[2])
            except IndexError:
                n = 5

            def on_drawing_stopped(widget):
                print "before: %d pts" % widget.get_writing().get_n_points()
                widget.get_writing().downsample(n)
                widget.refresh(force_draw=True)
                print "after: %d pts" % widget.get_writing().get_n_points()

        elif sys.argv[1] == "downsamplet":
            try:
                n = int(sys.argv[2])
            except IndexError:
                n = 10

            def on_drawing_stopped(widget):
                print "before: %d pts" % widget.get_writing().get_n_points()
                widget.get_writing().downsample_threshold(n)
                widget.refresh(force_draw=True)
                print "after: %d pts" % widget.get_writing().get_n_points()
                
        elif sys.argv[1] == "smooth":
            def on_drawing_stopped(widget):
                widget.smooth()

        elif sys.argv[1] == "normalize":
            def on_drawing_stopped(widget):
                widget.normalize()
                
        elif sys.argv[1] == "replay":
            def on_drawing_stopped(widget):
                widget.replay()

        elif sys.argv[1] == "replay-speed":
            def on_drawing_stopped(widget):
                widget.replay(speed=25)

        elif sys.argv[1] == "background-writing":
            def on_drawing_stopped(widget):
                background_writing = widget.get_background_writing()
                if not background_writing:
                    writing = copy.copy(widget.get_writing())
                    widget.set_background_writing(writing)
 
        else:
            def on_drawing_stopped(widget):
                print "drawing stopped!"

        if sys.argv[1] == "background-char":
            canvas.set_background_character("愛")

    else:
        def on_drawing_stopped(widget):
            print "drawing stopped!"
            print widget.get_writing().to_xml()
                             
    canvas.set_draw_annotations(False)
    canvas.set_drawing_stopped_time(1000)
    canvas.connect("drawing_stopped", on_drawing_stopped)
    
    window.add(canvas)
    
    window.show_all()
    window.connect('delete-event', gtk.main_quit)
    
    gtk.main()
########NEW FILE########
__FILENAME__ = chartable
# -*- coding: utf-8 -*-

# Copyright (C) 2009 The Tegaki project contributors
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

# Contributors to this file:
# - Mathieu Blondel

import gtk
from gtk import gdk
import gobject
import pango
import math
import time

from tegaki.character import *

class CharTable(gtk.Widget):
    """
    A nifty character table.

    A port of Takuro Ashie's TomoeCharTable to pygtk.
    """

    LAYOUT_SINGLE_HORIZONTAL = 0
    LAYOUT_SINGLE_VERTICAL = 1
    LAYOUT_HORIZONTAL = 2
    LAYOUT_VERTICAL = 3

    DEFAULT_FONT_SCALE = 2.0 #pango.SCALE_XX_LARGE

    __gsignals__ = {
        "character_selected" : (gobject.SIGNAL_RUN_LAST,
                                gobject.TYPE_NONE,
                                [gobject.TYPE_PYOBJECT])
    }
    
    def __init__(self):
        gtk.Widget.__init__(self)

        self._pixmap = None

        self._padding = 2
        self._selected = None
        self._prelighted = None
        self._layout = self.LAYOUT_SINGLE_HORIZONTAL

        self._h_adj = None
        self._v_adj = None

        self.clear()

        self.connect("motion_notify_event", self.motion_notify_event)
        
    # Events...

    def do_realize(self):
        """
        Called when the widget should create all of its
        windowing resources.  We will create our gtk.gdk.Window.
        """
        # Set an internal flag telling that we're realized
        self.set_flags(self.flags() | gtk.REALIZED)

        # Create a new gdk.Window which we can draw on.
        # Also say that we want to receive exposure events
        # and button click and button press events
        self.window = gdk.Window(self.get_parent_window(),

                                 x=self.allocation.x,
                                 y=self.allocation.y,
                                 width=self.allocation.width,
                                 height=self.allocation.height,

                                 window_type=gdk.WINDOW_CHILD,
                                 wclass=gdk.INPUT_OUTPUT,
                                 visual=self.get_visual(),
                                 colormap=self.get_colormap(),

                                 event_mask=gdk.EXPOSURE_MASK |
                                            gdk.BUTTON_PRESS_MASK |
                                            gdk.BUTTON_RELEASE_MASK |
                                            gdk.POINTER_MOTION_MASK |
                                            gdk.POINTER_MOTION_HINT_MASK |
                                            gdk.ENTER_NOTIFY_MASK |
                                            gdk.LEAVE_NOTIFY_MASK)


        # Associate the gdk.Window with ourselves, Gtk+ needs a reference
        # between the widget and the gdk window
        self.window.set_user_data(self)

        # Attach the style to the gdk.Window, a style contains colors and
        # GC contextes used for drawing
        self.style.attach(self.window)

        # The default color of the background should be what
        # the style (theme engine) tells us.
        self.style.set_background(self.window, gtk.STATE_NORMAL)
        self.window.move_resize(*self.allocation)

        # Font
        font_desc = self.style.font_desc.copy()
        size = font_desc.get_size()
        font_desc.set_size(int(size * self.DEFAULT_FONT_SCALE))
        self.modify_font(font_desc)

    def do_unrealize(self):
        """
        The do_unrealized method is responsible for freeing the GDK resources
        De-associate the window we created in do_realize with ourselves
        """
        self.window.destroy()
    
    def do_size_request(self, requisition):
        """
        The do_size_request method Gtk+ is called on a widget to ask it the
        widget how large it wishes to be.
        It's not guaranteed that gtk+ will actually give this size to the
        widget.
        """
        self.ensure_style()
        context = self.get_pango_context()
        metrics = context.get_metrics(self.style.font_desc,
                                      context.get_language())

        # width
        char_width = metrics.get_approximate_char_width()
        digit_width = metrics.get_approximate_digit_width()
        char_pixels = pango.PIXELS(int(max(char_width, digit_width) *
                                        self.DEFAULT_FONT_SCALE))
        requisition.width = char_pixels + self._padding * 2

        # height
        ascent = metrics.get_ascent()
        descent = metrics.get_descent()
        requisition.height = pango.PIXELS(ascent + descent) + self._padding * 2

    def do_size_allocate(self, allocation):
        """
        The do_size_allocate is called when the actual
        size is known and the widget is told how much space
        could actually be allocated."""

        self.allocation = allocation
        self.width = self.allocation.width
        self.height = self.allocation.height        
 
        if self.flags() & gtk.REALIZED:
            self.window.move_resize(*allocation)
            
            self._pixmap = gdk.Pixmap(self.window,
                                      self.width,
                                      self.height)

            self.draw()

    def do_expose_event(self, event):
        """
        This is where the widget must draw itself.
        """
        retval = False
       
        if self.flags() & gtk.REALIZED and not self._pixmap:
            self._pixmap = gdk.Pixmap(self.window,
                                      self.allocation.width,
                                      self.allocation.height)

            self._adjust_adjustments()
            self.draw()

        if self._pixmap:
            self.window.draw_drawable(self.style.fg_gc[self.state],
                                     self._pixmap,
                                     event.area.x, event.area.y,
                                     event.area.x, event.area.y,
                                     event.area.width, event.area.height)

        return retval
    
    def motion_notify_event(self, widget, event):
        retval = False

        if event.is_hint:
            x, y, state = event.window.get_pointer()
        else:
            x = event.x
            y = event.y
            state = event.state

        prev_prelighted = self._prelighted
        self._prelighted = self._get_char_id_from_coordinates(x, y)

        if prev_prelighted != self._prelighted:
            self.draw()

        return retval

    def do_button_press_event(self, event):
        retval = False

        prev_selected = self._selected
        self._selected = self._get_char_id_from_coordinates(event.x, event.y)

        if prev_selected != self._selected:
            self.draw()

        if self._selected >= 0:
            self.emit("character_selected", event)

        return retval

    def do_button_release_event(self, event):
        return False

    def get_max_char_size(self):
        context = self.get_pango_context()
        metrics = context.get_metrics(self.style.font_desc,
                                      context.get_language())

        # width
        char_width = metrics.get_approximate_char_width()
        digit_width = metrics.get_approximate_digit_width()
        max_char_width = pango.PIXELS(int(max(char_width, digit_width) *
                                           self.DEFAULT_FONT_SCALE))

        # height
        ascent = metrics.get_ascent()
        descent = metrics.get_descent()
        max_char_height = pango.PIXELS(int((ascent + descent) *
                                            self.DEFAULT_FONT_SCALE))

        return (max_char_width, max_char_height)

    def _get_char_frame_size(self):
        sizes = [layout.get_pixel_size() for layout in self._layouts]

        if len(sizes) > 0:
            inner_width = max([size[0] for size in sizes])
            inner_height = max([size[1] for size in sizes])
        else:
            inner_width, inner_height = self.get_max_char_size()

        outer_width = inner_width + 2 * self._padding
        outer_height = inner_height + 2 * self._padding

        return [inner_width, inner_height, outer_width, outer_height]



    def _get_char_id_from_coordinates(self, x, y):
        inner_width, inner_height, outer_width, outer_height = \
            self._get_char_frame_size()

        h_offset = 0; v_offset = 0

        if self._h_adj: h_offset = h_adj.get_value()
        if self._v_adj: v_offset = v_adj.get_value()

        # Calculate columns for horizontal layout
        cols = self.allocation.width / outer_width
        if cols <= 0: cols = 1

        # Calculate rows for vertical layout
        rows = self.allocation.height / outer_height
        if rows <= 0: rows = 1

        for i in range(len(self._layouts)):

            if self._layout == self.LAYOUT_SINGLE_HORIZONTAL:
                area_x = outer_width * i - h_offset

                if x >= area_x and x < area_x + outer_width:
                    return i

            elif self._layout == self.LAYOUT_SINGLE_VERTICAL:
                area_y = outer_height * i - v_offset

                if y >= area_y and y < area_y + outer_height:
                    return i

            elif self._layout == self.LAYOUT_HORIZONTAL:
                area_x = outer_width  * (i % cols) - h_offset
                area_y = outer_height * (i / cols) - v_offset

                if x >= area_x and x < area_x + outer_width and \
                   y >= area_y and y < area_y + outer_height:
                
                    return i

            elif self._layout == self.LAYOUT_VERTICAL:
                area_x = outer_width  * (i / rows) - h_offset
                area_y = outer_height * (i % rows) - v_offset

                if x >= area_x and x < area_x + outer_width and \
                    y >= area_y and y < area_y + outer_height:

                    return i

        return None

    def _adjust_adjustments(self):
        pass

    def draw(self):
        if not self._pixmap:
            return

        inner_width, inner_height, outer_width, outer_height = \
            self._get_char_frame_size()

        y_pos = (self.allocation.height - inner_height) / 2
        x_pos = (self.allocation.width - inner_width) / 2

        cols = self.allocation.width / outer_width
        if cols <= 0: cols = 1

        rows = self.allocation.height / outer_height
        if rows <= 0: rows = 1

        h_offset = 0; v_offset = 0

        if self._h_adj: h_offset = h_adj.get_value()
        if self._v_adj: v_offset = v_adj.get_value()

        # Fill background
        self._pixmap.draw_rectangle(self.style.white_gc,
                                    True,
                                    0, 0,
                                    self.allocation.width,
                                    self.allocation.height)

        # Draw characters
        for i in range(len(self._layouts)):
            layout = self._layouts[i]
            selected = i == self._selected
            char_width, char_height = layout.get_pixel_size()

           
            if self._layout == self.LAYOUT_SINGLE_HORIZONTAL:
                outer_x = outer_width * i - h_offset
                outer_y = 0
                outer_height = self.allocation.height
                inner_x = outer_x + (outer_width  - char_width)  / 2
                inner_y = y_pos

                if outer_x + outer_width < 0:
                    continue

                if outer_x + outer_width > self.allocation.width:
                    break

            elif self._layout == self.LAYOUT_SINGLE_VERTICAL:
                outer_x = 0
                outer_y = outer_height * i - v_offset
                outer_width = self.allocation.width
                inner_x = x_pos
                inner_y = outer_y + (outer_height - char_height) / 2

                if outer_y + outer_height < 0:
                    continue

                if outer_y + outer_height > self.allocation.height:
                    break

            elif self._layout == self.LAYOUT_HORIZONTAL:
                outer_x      = outer_width  * (i % cols) - h_offset
                outer_y      = outer_height * (i / cols) - v_offset
                inner_x      = outer_x + (outer_width  - char_width)  / 2
                inner_y      = outer_y + (outer_height - char_height) / 2

                if outer_y + outer_height < 0:
                    continue

                if outer_y + outer_height > self.allocation.height:
                    break

            elif self._layout == self.LAYOUT_VERTICAL:
                outer_x      = outer_width  * (i / rows) - h_offset
                outer_y      = outer_height * (i % rows) - v_offset
                inner_x      = outer_x + (outer_width  - char_width)  / 2
                inner_y      = outer_y + (outer_height - char_height) / 2

                if outer_x + outer_width < 0:
                    continue

                if outer_x + outer_width > self.allocation.width:
                    break

            if selected:
                outer_gc = self.style.bg_gc[gtk.STATE_SELECTED]
                inner_gc = self.style.white_gc
            else:
                outer_gc = self.style.white_gc
                inner_gc = self.style.black_gc

            self._pixmap.draw_rectangle(outer_gc,
                                        True,
                                        outer_x, outer_y,
                                        outer_width, outer_height)

            self._pixmap.draw_layout(inner_gc, 
                                     inner_x, inner_y,
                                     layout)

            if i == self._prelighted:
                # FIXME: doesn't seem to work
                self.style.paint_shadow(self.window,
                                        gtk.STATE_PRELIGHT, gtk.SHADOW_OUT,
                                        None, None, None,
                                        outer_x, outer_y,
                                        outer_width, outer_height)


        self.window.draw_drawable(self.style.fg_gc[self.state],
                                  self._pixmap,
                                  0, 0,
                                  0, 0,
                                  self.allocation.width, self.allocation.height)

    def set_characters(self, characters):
        self._layouts = []
        for character in characters:
            self._layouts.append(self.create_pango_layout(character))
        self.draw()
        self._characters = characters

    def get_characters(self):
        return self._characters

    def get_selected(self):
        return self._selected

    def unselect(self):
        self._selected = None
        self.draw()

    def clear(self):
        self._selected = None
        self._prelighted = None
        self.set_characters([])

    def set_layout(self, layout):
        self._layout = layout
        
gobject.type_register(CharTable)
        
if __name__ == "__main__":
    import sys

    window = gtk.Window()
    chartable = CharTable()
    chartable.set_characters(["あ", "い","う", "え", "お", 
                              "か", "き", "く", "け", "こ",
                              "さ", "し", "す", "せ", "そ"])

    try:
        layout = int(sys.argv[1])
        if layout > 3: layout = 0
    except IndexError:
        layout = 0

    chartable.set_layout(layout)


    def on_selected(widget, event):
        print "char_selected", chartable.get_selected()
        print "ev button", event.button
        print "ev time", event.time
       
    chartable.connect("character-selected", on_selected)

    window.add(chartable)
    window.show_all()
    gtk.main()
    

########NEW FILE########
__FILENAME__ = fakekey
# -*- coding: utf-8 -*-

# Copyright (C) 2009 The Tegaki project contributors
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

# Contributors to this file:
# - Mathieu Blondel

"""
Send fake key events in order to display text
where the cursor is currently located.
"""

import time
import os
import platform

if os.name == 'nt':
    from ctypes import *

    PUL = POINTER(c_ulong)
    class KeyBdInput(Structure):
        _fields_ = [("wVk", c_ushort),
                    ("wScan", c_ushort),
                    ("dwFlags", c_ulong),
                    ("time", c_ulong),
                    ("dwExtraInfo", PUL)]

    class HardwareInput(Structure):
        _fields_ = [("uMsg", c_ulong),
                    ("wParamL", c_short),
                    ("wParamH", c_ushort)]

    class MouseInput(Structure):
        _fields_ = [("dx", c_long),
                    ("dy", c_long),
                    ("mouseData", c_ulong),
                    ("dwFlags", c_ulong),
                    ("time",c_ulong),
                    ("dwExtraInfo", PUL)]

    class Input_I(Union):
        _fields_ = [("ki", KeyBdInput),
                    ("mi", MouseInput),
                    ("hi", HardwareInput)]

    class Input(Structure):
        _fields_ = [("type", c_ulong),
                    ("ii", Input_I)]

    INPUT_KEYBOARD = 1
    KEYEVENTF_KEYUP = 0x2
    KEYEVENTF_UNICODE = 0x4

    def _send_unicode_win(unistr):
        for ch in unistr:
            inp = Input()
            inp.type = INPUT_KEYBOARD

            inp.ii.ki.wVk = 0
            inp.ii.ki.wScan = ord(ch)
            inp.ii.ki.dwFlags = KEYEVENTF_UNICODE

            windll.user32.SendInput(1, byref(inp), sizeof(inp))
            
            inp.ii.ki.dwFlags = KEYEVENTF_UNICODE | KEYEVENTF_KEYUP
            windll.user32.SendInput(1, byref(inp), sizeof(inp))

    _send_unicode = _send_unicode_win

elif platform.system() == "Darwin":
    def _send_unicode_osx(unistr):
        # TODO: use CGPostKeyboardEvent?
        raise NotImplementedError

    _send_unicode = _send_unicode_osx

else:

    try:
        import pyatspi
        from gtk import gdk   

        def _send_unicode_atspi(unistr):
            for ch in unistr:
                keyval = gdk.unicode_to_keyval(ord(ch))
                pyatspi.Registry.generateKeyboardEvent(keyval, None,
                                                        pyatspi.KEY_SYM)

        _send_unicode = _send_unicode_atspi

    except ImportError:

        from ctypes import *

        try:
            Xlib = CDLL("libX11.so.6")
            Xtst = CDLL("libXtst.so.6")
            KeySym = c_uint
            Xlib.XGetKeyboardMapping.restype = POINTER(KeySym)
        except OSError:
            Xlib = None

        def _send_unicode_x11(unistr):
            if Xlib is None: raise NameError

            dpy = Xlib.XOpenDisplay(None)

            if not dpy: raise OSError # no display

            min_, max_, numcodes = c_int(0), c_int(0), c_int(0)
            Xlib.XDisplayKeycodes(dpy, byref(min_), byref(max_))

            for ch in unistr:
                sym = Xlib.XStringToKeysym("U" + hex(ord(ch)).replace("0x", ""))

                keysym = Xlib.XGetKeyboardMapping(dpy, min_,
                                                max_.value-min_.value+1,
                                                byref(numcodes))

                keysym[(max_.value-min_.value-1)*numcodes.value] = sym

                Xlib.XChangeKeyboardMapping(dpy,min_,numcodes,keysym,
                                            (max_.value-min_.value))

                Xlib.XFree(keysym)
                Xlib.XFlush(dpy)

                code = Xlib.XKeysymToKeycode(dpy, sym)

                Xtst.XTestFakeKeyEvent(dpy, code, True, 1)
                Xtst.XTestFakeKeyEvent(dpy, code, False, 1)

            Xlib.XFlush(dpy)
            Xlib.XCloseDisplay(dpy)

        _send_unicode = _send_unicode_x11

def send_unicode(unistr):
    assert(isinstance(unistr, unicode))
    try:
        _send_unicode(unistr)
        return True
    except (OSError, NotImplementedError, NameError), e:
        return False
    except e, msg:
        print "send_unicode", e, msg
        return False

if __name__ == "__main__":
    send_unicode(u"漢字")
########NEW FILE########
__FILENAME__ = iconview
# -*- coding: utf-8 -*-

# Copyright (C) 2009 The Tegaki project contributors
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

# Contributors to this file:
# - Mathieu Blondel

import gtk
from gtk import gdk
from tegakigtk.renderers import WritingImageRenderer 

class _WritingPixbufRenderer(WritingImageRenderer):

    def get_pixbuf(self):
        w, h = self.surface.get_width(), self.surface.get_height()
        pixmap = gdk.Pixmap(None, w, h, 24)
        cr = pixmap.cairo_create()
        cr.set_source_surface(self.surface, 0, 0)
        cr.paint ()
        pixbuf = gtk.gdk.Pixbuf (gdk.COLORSPACE_RGB, True, 8, w, h)
        pixbuf = pixbuf.get_from_drawable(pixmap,
                                          gdk.colormap_get_system(), 
                                          0, 0, 0, 0, w, h)
        return pixbuf

class WritingIconView(gtk.IconView):

    def __init__(self):
        self._model = gtk.ListStore(gdk.Pixbuf, str)
        gtk.IconView.__init__(self, self._model)
        self.set_selection_mode(gtk.SELECTION_SINGLE)
        self.set_reorderable(False)
        self.set_pixbuf_column(0)
        self.set_text_column(1)
        self.set_item_width(100)

    def set_writings(self, writings):
        """
        writings: a list of tegaki.Writing objects.
        """
        self._model.clear()
        characters = []
        for writing in writings:
            char = Character()
            char.set_writing(writing)
            char.set_utf8("?")
            characters.append(char)
        self.set_characters(characters)

    def set_characters(self, characters):
        """
        characters: a list of tegaki.Character objects.
        """
        self._model.clear()
        for char in characters:
            writing = char.get_writing()
            renderer = _WritingPixbufRenderer(writing, 
                                              self.get_item_width(),
                                              self.get_item_width())
            renderer.set_draw_annotations(False)
            renderer.draw_background()
            renderer.draw_border()
            #renderer.draw_axis()
            renderer.draw_writing()
            self._model.append((renderer.get_pixbuf(), char.get_utf8()))

    def show_icon_text(self):
        self.set_text_column(1)

    def hide_icon_text(self):
        self.set_text_column(-1)

if __name__ == "__main__":
    import sys
    from glob import glob
    import os.path

    from tegaki.character import Character

    folder = sys.argv[1] # a folder contains XML character files

    window = gtk.Window(gtk.WINDOW_TOPLEVEL)
    window.set_default_size(500, 500)
    iconview = WritingIconView()
    scrolledwindow = gtk.ScrolledWindow()
    scrolledwindow.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
  
    characters = []
    for path in glob(os.path.join(folder, "*.xml")):
        char = Character()
        char.read(path)
        characters.append(char)

    iconview.set_item_width(80)
    iconview.set_characters(characters)
    iconview.hide_icon_text()

    scrolledwindow.add(iconview)
    window.add(scrolledwindow)
    window.show_all()

    gtk.main()
########NEW FILE########
__FILENAME__ = recognizer
# -*- coding: utf-8 -*-

# Copyright (C) 2009 The Tegaki project contributors
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

# Contributors to this file:
# - Mathieu Blondel

import os
from ConfigParser import SafeConfigParser, NoSectionError, NoOptionError

import gtk
from gtk import gdk
import gobject

from canvas import Canvas
from chartable import CharTable

from tegaki.recognizer import Recognizer

class RecognizerWidgetBase(gtk.HBox):

    DEFAULT_CANVAS_WIDTH = 250

    __gsignals__ = {

        "commit-string" :         (gobject.SIGNAL_RUN_LAST, 
                                   gobject.TYPE_NONE,
                                   [gobject.TYPE_STRING])
    }

    def __init__(self):
        gtk.HBox.__init__(self)

        self._recognizer = None
        self._search_on_stroke = True

        self._create_ui()
        self.clear_canvas()
        self.clear_characters()

        self._load_preferences()

    def _load_preferences(self):
        pm = PreferenceManager()
        pm.load()
        self.set_drawing_stopped_time(pm["GENERAL"]["DRAWING_STOPPED_TIME"])
        self.set_search_on_stroke(pm["GENERAL"]["SEARCH_ON_STROKE"])
        self.set_selected_model(pm["GENERAL"]["SELECTED_MODEL"])
        self.set_draw_annotations(pm["GENERAL"]["DRAW_ANNOTATIONS"])

    def _save_preferences(self):
        pm = PreferenceManager()
        pm["GENERAL"]["DRAWING_STOPPED_TIME"] = self.get_drawing_stopped_time()
        pm["GENERAL"]["SEARCH_ON_STROKE"] = self.get_search_on_stroke()
        pm["GENERAL"]["SELECTED_MODEL"] = self.get_selected_model()
        pm["GENERAL"]["DRAW_ANNOTATIONS"] = self.get_draw_annotations()
        pm.save()

    def _create_toolbar_separator(self):
        self._toolbar.pack_start(gtk.HSeparator(), expand=False)

    def _create_clear_button(self):
        self._clear_button = gtk.Button()
        image = gtk.image_new_from_stock(gtk.STOCK_CLEAR, gtk.ICON_SIZE_BUTTON)
        self._clear_button.set_image(image)
        self._clear_button.connect("clicked", self._on_clear)
        self._toolbar.pack_start(self._clear_button, expand=False)

    def _create_find_button(self):
        self._find_button = gtk.Button()
        image = gtk.image_new_from_stock(gtk.STOCK_FIND, gtk.ICON_SIZE_BUTTON)
        self._find_button.set_image(image)
        self._find_button.connect("clicked", self._on_find)
        self._toolbar.pack_start(self._find_button, expand=False)

    def _create_undo_button(self):
        self._undo_button = gtk.Button()
        image = gtk.image_new_from_stock(gtk.STOCK_UNDO, gtk.ICON_SIZE_BUTTON)
        self._undo_button.set_image(image)
        self._undo_button.connect("clicked", self._on_undo)
        self._toolbar.pack_start(self._undo_button, expand=False)

    def _create_prefs_button(self):
        self._prefs_button = gtk.Button()
        image = gtk.image_new_from_stock(gtk.STOCK_PREFERENCES,
                                         gtk.ICON_SIZE_BUTTON)
        self._prefs_button.set_image(image)
        self._prefs_button.connect("clicked", self._on_prefs)
        self._toolbar.pack_start(self._prefs_button, expand=False)

    def _create_models_button(self):
        self._models_button = gtk.Button("Models")
        self._models_button.connect("button-press-event", self._on_models)
        self._toolbar.pack_start(self._models_button, expand=False)

    def _create_model_menu(self):
        menu = gtk.Menu()

        all_models = Recognizer.get_all_available_models()

        if len(all_models) == 0:
            return None

        i = 0
        for r_name, model_name, meta in all_models:
            item = gtk.MenuItem("%d. %s (%s)" % (i+1, model_name, r_name))
            item.connect("activate", self._on_activate_model, i)
            menu.append(item)
            i += 1

        return menu

    def _create_canvas(self, canvas_name):
        canvas = Canvas()
        canvas.set_size_request(self.DEFAULT_CANVAS_WIDTH,
                                self.DEFAULT_CANVAS_WIDTH)

        canvas.connect("button-press-event",
                       self._on_canvas_button_press,
                       canvas_name)

        canvas.connect("drawing-stopped",
                       self._on_canvas_drawing_stopped,
                       canvas_name)

        canvas.connect("stroke-added",
                       self._on_canvas_stroke_added,
                       canvas_name)

        setattr(self, canvas_name, canvas)

        frame = gtk.Frame()
        frame.add(canvas)

        setattr(self, canvas_name + "_frame", frame)

    def _create_chartable(self):    
        self._chartable_frame = gtk.Frame()
        self._chartable = CharTable()
        self._chartable_frame.add(self._chartable)

        self._chartable.connect("character-selected", 
                                self._on_character_selected)

    def _on_models(self, button, event):
        menu = self._create_model_menu()
        if menu:
            menu.show_all()
            menu.popup(None, None, None, event.button, event.time)
        else:
            parent = self.get_toplevel()
            msg = "No recognizers and/or no models installed!"
            dialog = ErrorDialog(parent, msg).run()

    def _on_activate_model(self, item, i):
        self.set_selected_model(i)
        self._save_preferences()

    def _on_find(self, button):
        self.find()

    def _on_undo(self, button):
        self.revert_stroke()

    def _on_prefs(self, button):
        parent = self.get_toplevel()
        if not parent.flags() & gtk.TOPLEVEL:
            parent = None
        pref_dialog = PreferenceDialog(parent)

        pref_dialog.connect("response", self._on_pref_validate)

        pref_dialog.set_search_on_stroke(self.get_search_on_stroke())
        pref_dialog.set_drawing_stopped_time(self.get_drawing_stopped_time())
        pref_dialog.set_draw_annotations(self.get_draw_annotations())

        pref_dialog.run()

    def _on_pref_validate(self, dialog, response):
        if response == gtk.RESPONSE_OK:
            if dialog.get_search_on_stroke():
                self.set_search_on_stroke(True)
            else:
                self.set_drawing_stopped_time(dialog.get_drawing_stopped_time())
            self.set_draw_annotations(dialog.get_draw_annotations())
            self._save_preferences()

        dialog.destroy()

    def _on_clear(self, button):
        self.clear_canvas()

    def clear_all(self):
        self.clear_characters()
        self.clear_canvas()

    def get_search_on_stroke(self):
        return self._search_on_stroke

    def set_search_on_stroke(self, enabled):
        self._search_on_stroke = enabled

    def get_characters(self):
        return self._chartable.get_characters()

    def get_selected_model(self):
       return self._models_button.selected_model

    def set_selected_model(self, i):
        try:
            r_name, model_name, meta = Recognizer.get_all_available_models()[i]

            klass = Recognizer.get_available_recognizers()[r_name]
            self._recognizer = klass()
            self._recognizer.set_model(meta["name"])
            self._models_button.set_label(meta["shortname"])
            # a hack to retain the model id the button
            self._models_button.selected_model = i

            self._ready = True
        except IndexError:
            self._ready = False

    def get_toolbar_vbox(self):
        return self._toolbar

class SimpleRecognizerWidget(RecognizerWidgetBase):

    def __init__(self):
        RecognizerWidgetBase.__init__(self)

    def _create_toolbar(self):
        self._toolbar = gtk.VBox(spacing=2)
        self._create_find_button()
        self._create_toolbar_separator()
        self._create_undo_button()
        self._create_clear_button()
        self._create_toolbar_separator()
        self._create_models_button()
        self._create_prefs_button()

    def _create_ui(self):
        self._create_canvasbox()
        self._create_chartable()

        vbox = gtk.VBox(spacing=2)
        vbox.pack_start(self._canvasbox, expand=True)
        vbox.pack_start(self._chartable_frame, expand=False)

        self._create_toolbar()
        self.set_spacing(2)
        self.pack_start(vbox, expand=True)
        self.pack_start(self._toolbar, expand=False)

    def _create_canvasbox(self):
        self._create_canvas("_canvas")
        self._canvasbox = self._canvas_frame  

    def _on_canvas_button_press(self, widget, event, curr_canv):
        pass
  
    def _on_canvas_drawing_stopped(self, widget, curr_canv):
        if not self._search_on_stroke:
            self.find()

    def _on_canvas_stroke_added(self, widget, curr_canv):
        if self._search_on_stroke:
            self.find()

    def _on_character_selected(self, chartable, event):
        chars = self._chartable.get_characters()
        selected = self._chartable.get_selected()
        self.emit("commit-string", chars[selected])

    def clear_canvas(self):
        self._canvas.clear()
        self.clear_characters()

    def clear_characters(self):
        self._chartable.clear() 

    def get_drawing_stopped_time(self):
        return self._canvas.get_drawing_stopped_time()

    def set_drawing_stopped_time(self, time_msec):
        self._search_on_stroke = False
        self._canvas.set_drawing_stopped_time(time_msec)

    def get_draw_annotations(self):
        return self._canvas.get_draw_annotations()

    def set_draw_annotations(self, active):
        self._canvas.set_draw_annotations(active)

    def revert_stroke(self):
        self._canvas.revert_stroke()
        if self._search_on_stroke:
            self.find()

    def find(self):
        if not self._ready:
            return

        writing = self._canvas.get_writing().copy()

        if writing.get_n_strokes() > 0:
            candidates = self._recognizer.recognize(writing, n=9)
            candidates = [char for char, prob in candidates]
            self._chartable.set_characters(candidates)

    def get_writing(self):
        self._canvas.get_writing()

    def set_writing(self, writing):
        self._canvas.set_writing(writing)

class SmartRecognizerWidget(RecognizerWidgetBase):

    OTHER_CANVAS_COLOR = (0xFFFF, 0xFFFF, 0xFFFF) 
    CURR_CANVAS_COLOR =  map(lambda x: x * 256, (255, 235, 235))

    def __init__(self):
        RecognizerWidgetBase.__init__(self)

    def _create_toolbar(self):
        self._toolbar = gtk.VBox(spacing=2)
        self._create_commit_button()
        self._create_del_button()
        self._create_toolbar_separator()
        self._create_find_button()
        self._create_toolbar_separator()
        self._create_undo_button()
        self._create_clear_button()
        self._create_toolbar_separator()
        self._create_models_button()
        self._create_prefs_button()

    def _create_commit_button(self):
        self._commit_button = gtk.Button()
        image = gtk.image_new_from_stock(gtk.STOCK_OK, gtk.ICON_SIZE_BUTTON)
        self._commit_button.set_image(image)
        self._commit_button.connect("clicked", self._on_commit)
        self._toolbar.pack_start(self._commit_button, expand=False)

    def _create_del_button(self):
        self._del_button = gtk.Button("Del")
        self._del_button.connect("clicked", self._on_delete)
        self._toolbar.pack_start(self._del_button, expand=False)

    def _create_ui(self):
        self._create_canvasbox()
        self._create_chartable()

        vbox = gtk.VBox(spacing=2)
        vbox.pack_start(self._chartable_frame, expand=False)
        vbox.pack_start(self._canvasbox, expand=True)

        self._create_toolbar()
        self.set_spacing(2)
        self.pack_start(vbox, expand=True)
        self.pack_start(self._toolbar, expand=False)

    def _create_canvasbox(self):
        self._canvasbox = gtk.HBox(spacing=2)
        self._create_canvas("_canvas1")
        self._create_canvas("_canvas2")
        self._canvasbox.pack_start(self._canvas1_frame)
        self._canvasbox.pack_start(self._canvas2_frame)

    def _find(self, canvas):
        if not self._ready:
            return

        writing = getattr(self, canvas).get_writing()

        if writing.get_n_strokes() == 0:
            return

        writing = writing.copy()
        candidates = self._recognizer.recognize(writing)
        candidates = [char for char, prob in candidates]     
        
        if candidates:
            candidate_list = CandidateList(candidates)

            if canvas == self._last_completed_canvas:
                # update the current character if the same canvas was used
                last = len(self.get_characters()) - 1
                self.replace_character(last, candidate_list)
                self._writings[last] = writing
            else:
                # append character otherwise
                self.add_character(candidate_list)
                self._writings.append(writing)

        self._last_completed_canvas = canvas

    def _other_canvas(self, canvas):
        if canvas == "_canvas1":
            othr_canv = "_canvas2"
        else:
            othr_canv = "_canvas1"
        return othr_canv
    
    def _set_canvas_focus(self, curr_canv):
        othr_canv = self._other_canvas(curr_canv)
        self._focused_canvas = curr_canv

        # set background color
        for canvas, color in ((curr_canv, self.CURR_CANVAS_COLOR),
                            (othr_canv, self.OTHER_CANVAS_COLOR)):

            getattr(self, canvas).set_background_color(*color)

    def _on_canvas_button_press(self, widget, event, curr_canv):
        othr_canv = self._other_canvas(curr_canv)

        if self._focused_canvas == othr_canv:
            getattr(self, curr_canv).clear()

            if getattr(self, othr_canv).get_writing().get_n_strokes() > 0 and \
               self._last_completed_canvas != othr_canv and \
               not self._search_on_stroke:

                self._find(othr_canv)

        self._set_canvas_focus(curr_canv)
  
    def _on_canvas_drawing_stopped(self, widget, curr_canv):
        if self._focused_canvas == curr_canv and not self._search_on_stroke:
            self._find(curr_canv)

    def _on_canvas_stroke_added(self, widget, curr_canv):
        if self._search_on_stroke:
            self._find(curr_canv)

    def _on_commit(self, button):
        chars = self.get_selected_characters()
        if len(chars) > 0:
            self.clear_all()
            self.emit("commit-string", "".join(chars))

    def _on_delete(self, button):
        self.delete_character()

    def _on_character_selected(self, chartable, event):
        selected = self._chartable.get_selected()

        candidates = self._characters[selected]
        popup = CandidatePopup(candidates)
        popup.move(int(event.x_root), int(event.y_root) + \
                    int(self._chartable.allocation.height/3))


        popup.connect("character-selected", self._on_candidate_selected)
        popup.connect("hide", self._on_popup_close)
        popup.connect("edit-character", self._on_edit_character)
        popup.connect("delete-character", self._on_delete_character)

        popup.popup()

    def _on_candidate_selected(self, popup, event):
        char_selected = self._chartable.get_selected()
        cand_selected = popup.get_selected()
        self._characters[char_selected].selected = cand_selected
        self._chartable.set_characters(self.get_selected_characters())
        self._chartable.unselect()
       
    def _on_edit_character(self, popup):
        char_selected = self._chartable.get_selected()
        edit_window = gtk.Window()
        edit_window.set_title("Edit character")
        rw = SimpleRecognizerWidget()
        rw.set_writing(self._writings[char_selected])
        edit_window.add(rw)

        parent = self.get_toplevel()
        if parent.flags() & gtk.TOPLEVEL:
            edit_window.set_transient_for(parent)
            edit_window.set_position(gtk.WIN_POS_CENTER_ON_PARENT)
            edit_window.set_type_hint(gdk.WINDOW_TYPE_HINT_DIALOG)
        edit_window.set_modal(True)
       
        rw.connect("commit-string", self._on_commit_edited_char, char_selected)
        
        edit_window.show_all()

    def _on_commit_edited_char(self, rw, char, char_selected):
        candidate_list = CandidateList(rw.get_characters())
        candidate_list.set_selected(char)
        self.replace_character(char_selected, candidate_list)
        rw.get_parent().destroy()

    def _on_delete_character(self, popup):
        char_selected = self._chartable.get_selected()
        self.remove_character(char_selected)

    def _on_popup_close(self, popup):
        self._chartable.unselect()

    def clear_canvas(self):
        self._canvas1.clear()
            
        if self._canvas2:
            self._canvas2.clear()
        
        self._set_canvas_focus("_canvas1")
        self._last_completed_canvas = None

    def delete_character(self):
        try:
            self._characters.pop()
            self._writings.pop()
            self._chartable.set_characters(self.get_selected_characters())
            self._chartable.unselect()
        except IndexError:
            pass

    def clear_characters(self):
        self._characters = []
        self._writings = []
        self._chartable.clear() 

    def add_character(self, candidate_list):
        if len(candidate_list) > 0:
            self._characters.append(candidate_list)
            self._chartable.set_characters(self.get_selected_characters())

    def replace_character(self, index, candidate_list):
        if len(candidate_list) > 0:
            try:
                self._characters[index] = candidate_list
                self._chartable.set_characters(self.get_selected_characters())
            except IndexError:
                pass

    def remove_character(self, index):
        length = len(self._chartable.get_characters())
        if length > 0 and index <= length - 1:
            del self._characters[index]
            del self._writings[index]
            self._chartable.set_characters(self.get_selected_characters())    
       
    def get_selected_characters(self):
        return [char[char.selected] for char in self._characters]

    def get_drawing_stopped_time(self):
        return self._canvas1.get_drawing_stopped_time()

    def set_drawing_stopped_time(self, time_msec):
        self._search_on_stroke = False
        for canvas in (self._canvas1, self._canvas2):
            canvas.set_drawing_stopped_time(time_msec)

    def get_draw_annotations(self):
        return self._canvas1.get_draw_annotations()

    def set_draw_annotations(self, active):
        for canvas in (self._canvas1, self._canvas2):
            canvas.set_draw_annotations(active)

    def revert_stroke(self):
        if self._focused_canvas:
            getattr(self, self._focused_canvas).revert_stroke()

    def find(self):
        if self._focused_canvas:
            self._find(self._focused_canvas)

class CandidatePopup(gtk.Window):

    __gsignals__ = {

        "character_selected" : (gobject.SIGNAL_RUN_LAST,
                                gobject.TYPE_NONE,
                                [gobject.TYPE_PYOBJECT]),

        "edit-character"     : (gobject.SIGNAL_RUN_LAST, 
                                gobject.TYPE_NONE,
                                []),

        "delete-character"   : (gobject.SIGNAL_RUN_LAST, 
                                gobject.TYPE_NONE,
                                [])
    }

    def __init__(self, candidates):
        gtk.Window.__init__(self, gtk.WINDOW_POPUP)
        self._candidates = candidates
        self._create_ui()

    def get_selected(self):
        return self._chartable.get_selected()

    def _create_ui(self):
        self.add_events(gdk.BUTTON_PRESS_MASK)

        self.set_title("Candidates")

        frame = gtk.Frame()
        self._chartable = CharTable()
        self._chartable.add_events(gdk.BUTTON_PRESS_MASK)
        self._chartable.set_characters(self._candidates)
        self._chartable.set_layout(CharTable.LAYOUT_HORIZONTAL)
        max_width, max_height = self._chartable.get_max_char_size()
        self._chartable.set_size_request(int(max_width*3.5),
                                         int(max_height*3.5))
        frame.add(self._chartable)

        self.connect("button-press-event", self._on_button_press)
        self._chartable.connect("character-selected",
                                self._on_character_selected)

        vbox = gtk.VBox(spacing=2)
        vbox.pack_start(frame)

        self._edit_button = gtk.Button()
        image = gtk.image_new_from_stock(gtk.STOCK_EDIT,
                                         gtk.ICON_SIZE_BUTTON)
        self._edit_button.set_image(image)
        self._edit_button.set_relief(gtk.RELIEF_NONE)
        self._edit_button.connect("clicked", self._on_edit)

        self._delete_button = gtk.Button()
        image = gtk.image_new_from_stock(gtk.STOCK_DELETE,
                                         gtk.ICON_SIZE_BUTTON)
        self._delete_button.set_image(image)
        self._delete_button.set_relief(gtk.RELIEF_NONE)
        self._delete_button.connect("clicked", self._on_delete)

        self._close_button = gtk.Button()
        image = gtk.image_new_from_stock(gtk.STOCK_CLOSE,
                                         gtk.ICON_SIZE_BUTTON)
        self._close_button.set_image(image)
        self._close_button.set_relief(gtk.RELIEF_NONE)
        self._close_button.connect("clicked", self._on_close)

        frame = gtk.Frame()
        buttonbox = gtk.HBox()
        buttonbox.pack_start(self._edit_button, expand=False)
        buttonbox.pack_start(self._delete_button, expand=False)
        buttonbox.pack_start(self._close_button, expand=False)
        frame.add(buttonbox)
        vbox.pack_start(frame)

        self.add(vbox)

    def _on_close(self, button):
        self.popdown()

    def _on_edit(self, button):
        self.emit("edit-character")
        self.popdown()

    def _on_delete(self, button):
        self.emit("delete-character")
        self.popdown()

    def _on_character_selected(self, chartable, event):
        self.emit("character-selected", event)

    def _on_button_press(self, window, event):
        # If we're clicking outside of the window or in the chartable
        # close the popup
        if (event.window != self.window or
            (tuple(self.allocation.intersect(
                   gdk.Rectangle(x=int(event.x), y=int(event.y),
                                 width=1, height=1)))) == (0, 0, 0, 0)):
            self.popdown()

    def popup(self):
        self.show_all()

        # grab pointer
        self.grab_add()
        gdk.pointer_grab(self.window,
                         True,
                         gdk.BUTTON_PRESS_MASK|
                         gdk.BUTTON_RELEASE_MASK|
                         gdk.POINTER_MOTION_MASK,
                         None, None, 
                         gtk.get_current_event_time())

    def popdown(self):
        gdk.pointer_ungrab(gtk.get_current_event_time())
        self.grab_remove()
        self.destroy()

class CandidateList(list):
    def __init__(self, initial_candidates=[]):
        self.extend(initial_candidates)
        self.selected = 0

    def get_selected(self):
        try:
            return self[self.selected]
        except IndexError:
            return None

    def set_selected(self, name):
        try:
            i = self.index(name)
            self.selected = i
        except ValueError:
            pass

class ErrorDialog(gtk.MessageDialog):

    def __init__(self, parent, msg):
        gtk.MessageDialog.__init__(self, parent, gtk.DIALOG_MODAL,
                                   gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, msg)

        self.connect("response", lambda w,r: self.destroy())

class PreferenceManager(dict):

    def __init__(self):
        dict.__init__(self)
        self._init_paths()
        self._init_dirs()
        self._init_defaults()

    def _init_defaults(self):
        self["GENERAL"] = {}

    def _init_paths(self):
        try:
            self._home_dir = os.environ['HOME']
            self._tegaki_dir = os.path.join(self._home_dir, ".tegaki")
        except KeyError:
            self._home_dir = os.environ['USERPROFILE']
            self._tegaki_dir = os.path.join(self._home_dir, "tegaki")

        self._conf_file = os.path.join(self._tegaki_dir, "recognizer.ini")

    def _init_dirs(self):
        if not os.path.exists(self._tegaki_dir):
            os.makedirs(self._tegaki_dir)

    def load(self):
        config = SafeConfigParser()
        config.read(self._conf_file)

        for opt, dflt, meth  in [("SEARCH_ON_STROKE", True, config.getboolean),
                                 ("DRAWING_STOPPED_TIME", 0, config.getint),
                                 ("SELECTED_MODEL", 0, config.getint),
                                 ("DRAW_ANNOTATIONS", 1, config.getboolean)]:

            try:
                self["GENERAL"][opt] = meth("GENERAL", opt)
            except (NoSectionError, NoOptionError, ValueError), e:
                self["GENERAL"][opt] = dflt

    def save(self):
        config = SafeConfigParser()
        
        for section in self.keys():
            if not config.has_section(section):
                config.add_section(section)

            for opt, value in self[section].items():
                config.set(section, opt, str(value))

        f = open(self._conf_file, "w")
        config.write(f)
        f.close()

class PreferenceDialog(gtk.Dialog):

    def __init__(self, parent):
        gtk.Dialog.__init__(self)
        self._init_dialog(parent)
        self._create_ui()

    def _init_dialog(self, parent):
        self.add_button(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
        self.add_button(gtk.STOCK_OK, gtk.RESPONSE_OK)
        self.set_default_response(gtk.RESPONSE_OK)
        self.set_has_separator(True)
        self.set_transient_for(parent)
        self.set_border_width(6)
        self.set_modal(True)
        self.set_title("Preferences")

    def _create_ui(self):
        self._search_on_stroke = gtk.RadioButton(group=None, 
                                                 label="Search on stroke")
        self._search_on_stroke.connect("toggled", self._on_search_on_stroke)

        
        self._search_after = gtk.RadioButton(group=self._search_on_stroke,
                                             label="Search after:")
        self._search_after.connect("toggled", self._on_search_after)
        adjustment = gtk.Adjustment(value=0, lower=0, upper=3000, step_incr=100,
                                    page_incr=0, page_size=0)
        self._spinbutton = gtk.SpinButton(adjustment)
        self._spinbutton.set_sensitive(False)
        self._search_after_hbox = gtk.HBox(spacing=2)
        self._search_after_hbox.pack_start(self._search_after, expand=False)
        self._search_after_hbox.pack_start(self._spinbutton, expand=False)
        self._search_after_hbox.pack_start(gtk.Label("[msecs]"), expand=False)

        self._draw_annotations = gtk.CheckButton(label="Draw annotations")

        main_vbox = self.get_child()
        main_vbox.set_spacing(10)
        main_vbox.pack_start(self._search_on_stroke)
        main_vbox.pack_start(self._search_after_hbox)
        main_vbox.pack_start(self._draw_annotations)
        self.show_all()

    def _on_search_on_stroke(self, radiobutton):
        self._spinbutton.set_sensitive(False)

    def _on_search_after(self, radiobutton):
        self._spinbutton.set_sensitive(True)

    def get_search_on_stroke(self):
        return self._search_on_stroke.get_active()

    def set_search_on_stroke(self, active):
        self._search_on_stroke.set_active(active)
        self._search_after.set_active(not(active))

    def get_draw_annotations(self):
        return self._draw_annotations.get_active()

    def set_draw_annotations(self, active):
        self._draw_annotations.set_active(active)

    def get_search_after(self):
        return self._search_after.get_active()

    def set_search_after(self, active):
        self._search_after.set_active(active)
        self._search_on_stroke.set_active(not(active))

    def get_drawing_stopped_time(self):
        return int(self._spinbutton.get_value())

    def set_drawing_stopped_time(self, time):
        self._spinbutton.set_value(int(time))

if __name__ == "__main__":
    import sys

    try:
        simple = int(sys.argv[1])
    except IndexError:
        simple = False

    window = gtk.Window()

    if simple:
        recognizer_widget = SimpleRecognizerWidget()
    else:
        recognizer_widget = SmartRecognizerWidget()

    def on_commit_string(rw, string):
        print string

    recognizer_widget.connect("commit-string", on_commit_string)

    window.add(recognizer_widget)
    window.show_all()

    gtk.main()
########NEW FILE########
__FILENAME__ = renderers
# -*- coding: utf-8 -*-

# Copyright (C) 2008 The Tegaki project contributors
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

# Contributors to this file:
# - Mathieu Blondel

import math
import cairo
from math import pi

from tegaki.character import *
from tegaki.mathutils import euclidean_distance

class _CairoRendererBase(object):

    def __init__(self, cairo_context, writing):
        self.cr = cairo_context
        self._init_colors()
        self.writing = writing
        self.draw_annotations = False
        self.draw_circles = False
        self.stroke_width = 8
        self.area_changed_cb = None
        self.stroke_added_cb = None

    def set_area_changed_callback(self, cb):
        self.area_changed_cb = cb

    def set_stroke_added_callback(self, cb):
        self.stroke_added_cb = cb

    def _area_changed(self, x, y, w, h, delay_ms):
        if self.area_changed_cb:
            sx = float(self.width) / self.writing.get_width() # scale x
            sy = float(self.height) / self.writing.get_height() # scale y
            self.area_changed_cb(int(sx*x), int(sy*y), 
                                 int(sx*w), int(sy*h), delay_ms)

    def _init_colors(self):
        self.handwriting_line_color = (0x0000, 0x0000, 0x0000, 1.0)
        self.axis_line_color = (0, 0, 0, 0.2)
        self.annotations_color = (255, 0, 0, 0.8)
        self.stroke_line_color = (255, 0, 0, 0.5)
        self.border_line_color = (0, 0, 0, 1.0)
        self.circle_color = (0, 0, 255, 0.5)

    def _with_handwriting_line(self):
        self.cr.set_line_width(self.stroke_width)
        self.cr.set_line_cap(cairo.LINE_CAP_ROUND)
        self.cr.set_line_join(cairo.LINE_JOIN_ROUND)

    def _with_circle_line(self):
        self.cr.set_line_width(self.stroke_width)
        self.cr.set_line_cap(cairo.LINE_CAP_ROUND)
        self.cr.set_line_join(cairo.LINE_JOIN_ROUND)
        self.cr.set_source_rgba (*self.circle_color)

    def _with_axis_line(self):
        self.cr.set_source_rgba (*self.axis_line_color)
        self.cr.set_line_width (4)
        self.cr.set_dash ([8, 8], 2)
        self.cr.set_line_cap(cairo.LINE_CAP_BUTT)
        self.cr.set_line_join(cairo.LINE_JOIN_ROUND)

    def _with_border_line(self):
        self.cr.set_source_rgba (*self.border_line_color)
        self.cr.set_line_width (8)
        self.cr.set_line_cap(cairo.LINE_CAP_BUTT)
        self.cr.set_line_join(cairo.LINE_JOIN_ROUND)

    def _with_annotations(self):
        self.cr.set_source_rgba (*self.annotations_color)
        self.annotation_font_size = 30 # user space units
        self.cr.set_font_size(self.annotation_font_size)

    def _draw_small_circle(self, x, y):
        self.cr.save()
        self._with_circle_line()
        self.cr.arc(x, y, 10, 0, 2*pi)
        self.cr.fill_preserve()
        self.cr.stroke()
        self.cr.restore()

    def set_draw_circles(self, draw_circles):
        self.draw_circles = draw_circles

    def set_draw_annotations(self, draw_annotations):
        self.draw_annotations = draw_annotations

    def set_stroke_width(self, stroke_width):
        self.stroke_width = stroke_width

    def draw_stroke(self, stroke, index, color, 
                    draw_annotation=False, draw_circle=False):

        l = len(stroke)

        self.cr.save()
        
        self._with_handwriting_line()
        self.cr.set_source_rgba(*color)

        point0 = stroke[0]

        if draw_circle: self._draw_small_circle(point0.x, point0.y)

        self.cr.move_to(point0.x, point0.y)
        last_point = point0
        n_points = len(stroke)

        i = 1

        for point in stroke[1:]:
            self.cr.line_to(point.x, point.y)
            self.cr.stroke()
            self.cr.move_to(point.x, point.y)

            dist = euclidean_distance(point.get_coordinates(),
                                      last_point.get_coordinates())

            if  dist > 50 or i == n_points - 1:
                win = 100 # window size
                x1 = last_point.x - win; y1 = last_point.y - win
                x2 = point.x + win; y2 = point.y + win
                if x1 > x2: x1, x2 = x2, x1
                if y1 > y2: y1, y2 = y2, y1
                w = x2 - x1; h = y2 - y1
                if point.timestamp and last_point.timestamp:
                    delay = point.timestamp - last_point.timestamp
                else:
                    delay = None
                if w > 0 and h > 0:
                    self._area_changed(x1, y1, w, h, delay) 

                last_point = point

            i += 1

        self.cr.stroke()
        self.cr.restore()

        if self.stroke_added_cb:
            self.stroke_added_cb()

        if draw_annotation:
            self._draw_annotation(stroke, index)

    def _draw_annotation(self, stroke, index):
        self.cr.save()

        self._with_annotations()
        
        x, y = stroke[0].x, stroke[0].y

        if len(stroke) == 1:
            dx, dy = x, y
        else:
            last_x, last_y = stroke[-1].x, stroke[-1].y
            dx, dy = last_x - x, last_y - y

        dl = math.sqrt(dx*dx + dy*dy)

        if dy <= dx:
            sign = 1
        else:
            sign = -1

        num = str(index + 1)
        # FIXME: how to know the actual size of the text?
        width, height = [int(self.annotation_font_size * 11.0/10.0)] * 2

        r = math.sqrt (width*width + height*height)

        x += (0.5 + (0.5 * r * dx / dl) + (sign * 0.5 * r * dy / dl) - \
              (width / 2))
              
        y += (0.5 + (0.5 * r * dy / dl) - (sign * 0.5 * r * dx / dl) - \
              (height / 2))

        x, y = int(x), int(y)

        self.cr.move_to(x, y)
        self.cr.show_text(num)
        self.cr.stroke()
        
        self._area_changed(x-50, y-50, 100, 100, 0) 

        self.cr.restore()

    def draw_background(self, color=(1, 1, 1)):
        self.cr.save()
        self.cr.set_source_rgb(*color)
        self.cr.paint()
        self.cr.restore()

    def draw_border(self):
        self.cr.save()

        self._with_axis_line()

        self.cr.move_to(0, 0)
        self.cr.line_to(0, 1000)
        self.cr.line_to(1000, 1000)
        self.cr.line_to(1000, 0)
        self.cr.line_to(0, 0)
        
        self.cr.stroke()
        self.cr.restore()        

    def draw_axis(self):
        self.cr.save()

        self._with_axis_line()

        self.cr.move_to(500, 0)
        self.cr.line_to(500, 1000)
        self.cr.move_to(0, 500)
        self.cr.line_to(1000, 500)
        
        self.cr.stroke()
        self.cr.restore()

class _SurfaceRendererBase(object):

    def get_width(self):
        return self.width

    def get_height(self):
        return self.height

    def get_size(self):
        return (self.width, self.height)

class _ImageRendererBase(_SurfaceRendererBase):
    
    def write_to_png(self, filename):
        self.surface.write_to_png(filename)

    def get_data(self):
        return self.surface.get_data()

    def get_area_data(self, x, y, width, height):
        data = self.get_data()
        stride = self.surface.get_stride() # number of bytes per line
        bpp = stride / self.surface.get_width() # bytes per pixel
        start = 0
        if y > 0:
            start += y * stride
        if x > 0:
            start += x * bpp
        buf = ""
        for i in range(height):
            buf += data[start:start+width*bpp]
            start += stride
        return buf

    def get_stride(self):
        return self.surface.get_stride()
    
class WritingCairoRenderer(_CairoRendererBase):

    def __init__(self, *a, **kw):
        _CairoRendererBase.__init__(self, *a, **kw)
        self.draw_annotations = True

    def draw_writing(self):
        strokes = self.writing.get_strokes(full=True)
        n_strokes = len(strokes)

        for i in range(n_strokes):
            self.draw_stroke(strokes[i],
                             i,
                             self.handwriting_line_color,
                             draw_annotation=self.draw_annotations,
                             draw_circle=self.draw_circles)

class WritingStepsCairoRenderer(_CairoRendererBase):

    def __init__(self, cairo_context, writing,
                       stroke_groups=None,
                       start=0,
                       length=None,
                       n_chars_per_row=None):
        
        _CairoRendererBase.__init__(self, cairo_context, writing)

    def _init(self):
        n_strokes = self.writing.get_n_strokes()
        
        if not self.stroke_groups:
            self.stroke_groups = [1] * n_strokes
        else:
            n = sum(self.stroke_groups)
            diff = n_strokes - n
            if diff > 0:
                # fix the number of groups if not enough
                self.stroke_groups += [1] * diff
            elif diff < 0:
                # fix the number of groups if too big
                tmp = []
                i = 0
                while sum(tmp) <= n_strokes:
                    tmp.append(self.stroke_groups[i])
                    i += 1
                self.stroke_groups = tmp

        n_stroke_groups = len(self.stroke_groups)

        if not self.length or self.start + self.length > n_stroke_groups:
            self.length = n_stroke_groups - self.start

        # interval groups are used to know which strokes are grouped together
        interval_groups = []
        
        interval_groups.append((0, self.stroke_groups[0] - 1))
        
        for i in range(1, n_stroke_groups):
            prev = interval_groups[i-1][1]
            interval_groups.append((prev + 1, prev + self.stroke_groups[i]))

        self.interval_groups = interval_groups

        # rows and cols
        if not self.n_chars_per_row:
            self.n_rows = 1
            self.n_cols = self.length
        else:
            self.n_cols = self.n_chars_per_row
            self.n_rows = int(math.ceil(float(self.length) / self.n_cols))

        # this factor is a multiplication factor used to determine
        # the amount of space to leave between two character steps
        self.FACTOR = 1.05
        
        # find proportional image size
        # we use width / n_cols == height / n_rows
        if self.width and not self.height:
            self.height = int(self.width / self.n_cols * self.n_rows)
        elif self.height and not self.width:
            self.width = int(self.n_cols * self.height / self.n_rows)
        elif not self.height and not self.width:
            raise ValueError, \
                  "At least one of height or width should be defined."
    
    def draw_writing_steps(self):       
        strokes = self.writing.get_strokes(full=True)
        n_strokes = len(strokes)
        n_stroke_groups = len(self.interval_groups)

        self.cr.save()

        x_scale = 1.0 / (self.n_cols * self.FACTOR)

        if self.n_rows == 1:
            y_scale = 1.0
        else:
            y_scale = 1.0 / (self.n_rows * self.FACTOR)
            
        self.cr.scale(x_scale, y_scale)

        for i in range(self.start, self.start + self.length):
            if i != self.start:
                if self.n_rows > 1 and i % self.n_cols == 0:
                    self.cr.translate((-self.n_cols+1) *
                                       self.writing.get_width() * self.FACTOR,
                                       self.writing.get_height() * self.FACTOR)
                else:
                    self.cr.translate(self.writing.get_width() * self.FACTOR,0) 
                
            # draw the character step
            for j in range(n_strokes):
                interval_min, interval_max = self.interval_groups[i]
                
                if interval_min <= j and j <= interval_max:
                    color = self.handwriting_line_color
                    draw_annotation = self.draw_annotations
                    draw_circle = self.draw_circles
                else:
                    color = self.stroke_line_color
                    draw_annotation = False
                    draw_circle = False
                   
                self.draw_stroke(strokes[j],
                                 j,
                                 color,
                                 draw_annotation=draw_annotation,
                                 draw_circle=draw_circle)

        self.cr.restore()

class WritingImageRenderer(WritingCairoRenderer, _ImageRendererBase):

    def __init__(self, writing, width, height):
        """
        width and height are in pixels.
        """
        self.width = width
        self.height = height
        
        self.surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
        cr = cairo.Context(self.surface)
        cr.scale(float(width) / writing.get_width(), 
                 float(height) / writing.get_height())
        WritingCairoRenderer.__init__(self, cr, writing)

class WritingSVGRenderer(WritingCairoRenderer, _SurfaceRendererBase):
    
    def __init__(self, writing, filename, width, height):
        """
        width and height are in points (1 point == 1/72.0 inch).
        """
        self.width = width
        self.height = height
        
        self.surface = cairo.SVGSurface(filename, width, height)
        cr = cairo.Context(self.surface)
        cr.scale(float(width) / writing.get_width(), 
                 float(height) / writing.get_height())
        WritingCairoRenderer.__init__(self, cr, writing)

class WritingPDFRenderer(WritingCairoRenderer, _SurfaceRendererBase):
    
    def __init__(self, writing, filename, width, height):
        """
        width and height are in points (1 point == 1/72.0 inch).
        """
        self.width = width
        self.height = height
        
        self.surface = cairo.PDFSurface(filename, width, height)
        cr = cairo.Context(self.surface)
        cr.scale(float(width) / writing.get_width(), 
                 float(height) / writing.get_height())
        WritingCairoRenderer.__init__(self, cr, writing)

class WritingStepsImageRenderer(WritingStepsCairoRenderer, _ImageRendererBase):

    def __init__(self, writing,
                       width=None, height=None,
                       stroke_groups=None,
                       start=0,
                       length=None,
                       n_chars_per_row=None):
        """
        width and height are in pixels.
        """
        self.writing = writing
        self.width = width
        self.height = height
        self.stroke_groups = stroke_groups
        self.start = start
        self.length = length
        self.n_chars_per_row = n_chars_per_row

        self._init()
        
        self.surface = cairo.ImageSurface(cairo.FORMAT_ARGB32,
                                          self.width, self.height)
        cr = cairo.Context(self.surface)
        cr.scale(float(self.width) / writing.get_width(),
                 float(self.height) / writing.get_height())
        WritingStepsCairoRenderer.__init__(self, cr, writing)
        
    def write_to_png(self, filename):
        self.surface.write_to_png(filename)
    
class WritingStepsSVGRenderer(WritingStepsCairoRenderer, _SurfaceRendererBase):
    
    def __init__(self, writing,
                       filename,
                       width=None, height=None,
                       stroke_groups=None,
                       start=0,
                       length=None,
                       n_chars_per_row=None):
        """
        width and height are in points (1 point == 1/72.0 inch).
        """
        self.writing = writing
        self.width = width
        self.height = height
        self.stroke_groups = stroke_groups
        self.start = start
        self.length = length
        self.n_chars_per_row = n_chars_per_row

        self._init()
        
        self.surface = cairo.SVGSurface(filename, self.width, self.height)
        cr = cairo.Context(self.surface)
        cr.scale(float(self.width) / writing.get_width(),
                 float(self.height) / writing.get_height())
        WritingStepsCairoRenderer.__init__(self, cr, writing)

class WritingStepsPDFRenderer(WritingStepsCairoRenderer, _SurfaceRendererBase):
    
    def __init__(self, writing,
                       filename,
                       width=None, height=None,
                       stroke_groups=None,
                       start=0,
                       length=None,
                       n_chars_per_row=None):
        """
        width and height are in points (1 point == 1/72.0 inch).
        """
        self.writing = writing
        self.width = width
        self.height = height
        self.stroke_groups = stroke_groups
        self.start = start
        self.length = length
        self.n_chars_per_row = n_chars_per_row

        self._init()
        
        self.surface = cairo.PDFSurface(filename, self.width, self.height)
        cr = cairo.Context(self.surface)
        cr.scale(float(self.width) / writing.get_width(),
                 float(self.height) / writing.get_height())
        WritingStepsCairoRenderer.__init__(self, cr, writing)

def inch_to_pt(*arr):
    arr = [inch * 72 for inch in arr]
    if len(arr) == 1:
        return arr[0]
    else:
        return arr

def cm_to_pt(*arr):
    arr = [int(round(cm * 28.3464567)) for cm in arr]
    if len(arr) == 1:
        return arr[0]
    else:
        return arr

########NEW FILE########
__FILENAME__ = arrayutils
# -*- coding: utf-8 -*-

# Copyright (C) 2008 The Tegaki project contributors
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

# Contributors to this file:
# - Mathieu Blondel

__doctest__ = True

def array_sample(arr, rate):
    """
    Sample array.

    @type  arr: list/tuple/array
    @param arr: the list/tuple/array to sample
    @type rate: float
    @param rate: the rate (between 0 and 1.0) at which to sample
    @rtype: list
    @return: the sampled list

    >>> array_sample([1,2,3,4,5,6], 0.5)
    [1, 3, 5]
    """
    n = int(round(1 / rate))
    
    return [arr[i] for i in range(0, len(arr), n)]

def array_flatten(l, ltypes=(list, tuple)):
    """
    Reduce array of possibly multiple dimensions to one dimension.

    @type  l: list/tuple/array
    @param l: the list/tuple/array to flatten
    @rtype: list
    @return: the flatten list

    >>> array_flatten([[1,2,3], [4,5], [[7,8]]])
    [1, 2, 3, 4, 5, 7, 8]
    """
    i = 0
    while i < len(l):
        while isinstance(l[i], ltypes):
            if not l[i]:
                l.pop(i)
                if not len(l):
                    break
            else:
                l[i:i+1] = list(l[i])
        i += 1
    return l

def array_reshape(arr, n):
    """
    Reshape one-dimensional array to a list of n-element lists.

    @type  arr: list/tuple/array
    @param arr: the array to reshape
    @type  n: int
    @param n: the number of elements in each list
    @rtype: list
    @return: the reshaped array

    >>> array_reshape([1,2,3,4,5,6,7,8,9], 3)
    [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
    """
    newarr = []
    subarr = []
    
    i = 0
    
    for ele in arr:
        subarr.append(ele)
        i += 1

        if i % n == 0 and i != 0:
            newarr.append(subarr)
            subarr = []
            
    return newarr

def array_split(seq, p):
    """
    Split an array into p arrays of about the same size.

    @type  seq: list/tuple/array
    @param seq: the array to split
    @type  p: int
    @param p: the split size
    @rtype: list
    @return: the split array

    >>> array_split([1,2,3,4,5,6,7], 3)
    [[1, 2, 3], [4, 5], [6, 7]]
    """
    newseq = []
    n = len(seq) / p    # min items per subsequence
    r = len(seq) % p    # remaindered items
    b,e = 0, n + min(1, r)  # first split
    for i in range(p):
        newseq.append(seq[b:e])
        r = max(0, r-1)  # use up remainders
        b,e = e, e + n + min(1, r)  # min(1,r) is always 0 or 1

    return newseq

def array_mean(arr):
    """
    Calculate the mean of the elements contained in an array.

    @type  arr: list/tuple/array
    @rtype: float
    @return: mean

    >>> array_mean([100, 150, 300])
    183.33333333333334
    """
    return float(sum(arr)) / float(len(arr))

def array_variance(arr, mean=None):
    """
    Calculate the variance of the elements contained in an array.

    @type  arr: list/tuple/array
    @rtype: float
    @return: variance

    >>> array_variance([100, 150, 300])
    7222.2222222222226
    """
    if mean is None:
        mean = array_mean(arr)
    var = array_mean([(val - mean) ** 2 for val in arr])
    if var == 0.0:
        return 1.0
    else:
        return var

def array_mean_vector(vectors):
    """
    Calculate the mean of the vectors, element-wise.

    @type arr: list of vectors
    @rtype: list of floats
    @return: list of means

    >>> array_mean_vector([[10,20], [100, 200]])
    [55.0, 110.0]
    """
    assert(len(vectors) > 0)

    n_dimensions = len(vectors[0])

    mean_vector = []

    for i in range(n_dimensions):
        arr = [vector[i] for vector in vectors]
        mean_vector.append(array_mean(arr))
        
    return mean_vector

def array_variance_vector(vectors, means=None):
    """
    Calculate the variance of the vectors, element-wise.

    @type  arr: list of vectors
    @rtype: list of floats
    @return: list of variances

    >>> array_variance_vector([[10,20], [100, 200]])
    [2025.0, 8100.0]
    """
    assert(len(vectors) > 0)
    
    n_dimensions = len(vectors[0])

    if means is not None:
        assert(n_dimensions == len(means))
    else:
        means = array_mean_vector(vectors)

    variance_vector = []

    for i in range(n_dimensions):
        arr = [vector[i] for vector in vectors]
        variance_vector.append(array_variance(arr, means[i]))
        
    return variance_vector

def array_covariance_matrix(vectors, non_diagonal=False):
    """
    Calculate the covariance matrix of vectors.

    @type vectors: list of arrays
    @type non_diagonal: boolean
    @param non_diagonal: whether to calculate non-diagonal elements of the \
                         matrix or not

    >>> array_covariance_matrix([[10,20], [100, 200]])
    [2025.0, 0.0, 0.0, 8100.0]

    >>> array_covariance_matrix([[10,20], [100, 200]], non_diagonal=True)
    [2025.0, 4050.0, 4050.0, 8100.0]
    """
    assert(len(vectors) > 0)

    n_dimensions = len(vectors[0])

    cov_matrix = []

    for i in range(n_dimensions):
        for j in range(n_dimensions):
            if i == j:
                # diagonal value: COV(X,X) = VAR(X)
                arr = [vector[i] for vector in vectors]
                cov_matrix.append(array_variance(arr))
            else:
                # non-diagonal value
                if non_diagonal:
                    # COV(X,Y) = E(XY) - E(X)E(Y)
                    arr_x = [vector[i] for vector in vectors]
                    arr_y = [vector[j] for vector in vectors]
                    arr_xy = array_mul(arr_x, arr_y)
                    
                    mean_xy = array_mean(arr_xy)
                    
                    mean_x = array_mean(arr_x)
                    mean_y = array_mean(arr_y)

                    cov_matrix.append(mean_xy - mean_x * mean_y)
                else:
                    # X and Y indep => COV(X,Y) = 0
                    cov_matrix.append(0.0)

    return cov_matrix

def array_add(arr1, arr2):
    """
    Add two arrays element-wise.

    >>> array_add([1,2],[3,4])
    [4, 6]
    """
    assert(len(arr1) == len(arr1))

    newarr = []

    for i in range(len(arr1)):
        newarr.append(arr1[i] + arr2[i])

    return newarr

def array_mul(arr1, arr2):
    """
    Multiply two arrays element-wise.

    >>> array_mul([1,2],[3,4])
    [3, 8]
    """
    assert(len(arr1) == len(arr1))

    newarr = []

    for i in range(len(arr1)):
        newarr.append(arr1[i] * arr2[i])

    return newarr

if __name__ == '__main__':
    import doctest
    doctest.testmod()
########NEW FILE########
__FILENAME__ = character
# -*- coding: utf-8 -*-

# Copyright (C) 2008-2009 The Tegaki project contributors
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

# Contributors to this file:
# - Mathieu Blondel

import xml.parsers.expat
import cStringIO
import gzip as gzipm
try:
    import bz2 as bz2m
except ImportError:
    pass
from math import floor, atan, sin, cos, pi
import os
import hashlib

try:
    # lxml is used for DTD validation
    # for server-side applications, it is recommended to install it
    # for desktop applications, it is optional
    from lxml import etree
except ImportError:
    pass

from tegaki.mathutils import euclidean_distance
from tegaki.dictutils import SortedDict

class Point(dict):
    """
    A point in a 2-dimensional space.
    """

    #: Attributes that a point can have.
    KEYS = ("x", "y", "pressure", "xtilt", "ytilt", "timestamp")

    def __init__(self, x=None, y=None,
                       pressure=None, xtilt=None, ytilt=None,
                       timestamp=None):
        """
        @type x: int
        @type y: int
        @type pressure: float
        @type xtilt: float
        @type ytilt: float
        @type timestamp: int
        @param timestamp: ellapsed time since first point in milliseconds
        """

        dict.__init__(self)

        self.x = x
        self.y = y

        self.pressure = pressure
        self.xtilt = xtilt
        self.ytilt = ytilt

        self.timestamp = timestamp

    def __getattr__(self, attr):
        try:
            return self[attr]
        except KeyError:
            raise AttributeError

    def __setattr__(self, attr, value):
        try:
            self[attr] = value
        except KeyError:
            raise AttributeError

    def get_coordinates(self):
        """
        Return (x,y) coordinates.

        @rtype: tuple of two int
        @return: (x,y) coordinates
        """
        return (self.x, self.y)

    def resize(self, xrate, yrate):
        """
        Scale point.

        @type xrate: float
        @param xrate: the x scaling factor
        @type yrate: float
        @param yrate: the y scaling factor
        """
        self.x = int(self.x * xrate)
        self.y = int(self.y * yrate)

    def move_rel(self, dx, dy):
        """
        Translate point.

        @type dx: int
        @param dx: relative distance from x
        @type dy: int
        @param yrate: relative distance from y
        """
        self.x = self.x + dx
        self.y = self.y + dy

    def to_xml(self):
        """
        Converts point to XML.

        @rtype: str
        """
        attrs = []

        for key in self.KEYS:
            if self[key] is not None:
                attrs.append("%s=\"%s\"" % (key, str(self[key])))

        return "<point %s />" % " ".join(attrs)

    def to_json(self):
        """
        Converts point to JSON.

        @rtype: str
        """
        attrs = []

        for key in self.KEYS:
            if self[key] is not None:
                attrs.append("\"%s\" : %d" % (key, int(self[key])))

        return "{ %s }" % ", ".join(attrs)

    def to_sexp(self):
        """
        Converts point to S-expressions.

        @rtype: str
        """
        return "(%d %d)" % (self.x, self.y)

    def __eq__(self, othr):
        if not othr.__class__.__name__ in ("Point", "PointProxy"):
            return False

        for key in self.KEYS:
            if self[key] != othr[key]:
                return False

        return True

    def __ne__(self, othr):
        return not(self == othr)

    def copy_from(self, p):
        """
        Replace point with another point.

        @type p: L{Point}
        @param p: the point to copy from
        """
        self.clear()
        for k in p.keys():
            if p[k] is not None:
                self[k] = p[k]

    def copy(self):
        """
        Return a copy of point.

        @rtype: L{Point}
        """
        return Point(**self)

    def __repr__(self):
        return "<Point (%s, %s) (ref %d)>" % (self.x, self.y, id(self))

class Stroke(list):
    """
    A sequence of L{Points<Point>}.
    """

    def __init__(self):
        list.__init__(self)
        self._is_smoothed = False

    def get_coordinates(self):
        """
        Return (x,y) coordinates.

        @rtype: a list of tuples
        """
        return [(p.x, p.y) for p in self]

    def get_duration(self):
        """
        Return the time that it took to draw the stroke.

        @rtype: int or None
        @return: time in millisecons or None if the information is not available
        """
        if len(self) > 0:
            if self[-1].timestamp is not None and self[0].timestamp is not None:
                return self[-1].timestamp - self[0].timestamp
        return None

    def append_point(self, point):
        """
        Append point to stroke.

        @type point: L{Point}
        """
        self.append(point)

    def append_points(self, points):
        self.extend(points)

    def to_xml(self):
        """
        Converts stroke to XML.

        @rtype: str
        """
        s = "<stroke>\n"

        for point in self:
            s += "  %s\n" % point.to_xml()

        s += "</stroke>"

        return s

    def to_json(self):
        """
        Converts stroke to JSON.

        @rtype: str
        """
        s = "{\"points\" : ["

        s += ",".join([point.to_json() for point in self])

        s += "]}"

        return s

    def to_sexp(self):
        """
        Converts stroke to S-expressions.

        @rtype: str
        """
        return "(" + "".join([p.to_sexp() for p in self]) + ")"

    def __eq__(self, othr):
        if not othr.__class__.__name__ in ("Stroke", "StrokeProxy"):
            return False

        if len(self) != len(othr):
            return False

        for i in range(len(self)):
            if self[i] != othr[i]:
                return False

        return True

    def __ne__(self, othr):
        return not(self == othr)

    def copy_from(self, s):
        """
        Replace stroke with another stroke.

        @type s: L{Stroke}
        @param s: the stroke to copy from
        """
        self.clear()
        self._is_smoothed = s.get_is_smoothed()
        for p in s:
            self.append_point(p.copy())

    def copy(self):
        """
        Return a copy of stroke.

        @rtype: L{Stroke}
        """
        c = Stroke()
        c.copy_from(self)
        return c

    def get_is_smoothed(self):
        """
        Return whether the stroke has been smoothed already or not.

        @rtype: boolean
        """
        return self._is_smoothed

    def smooth(self):
        """
        Visually improve the rendering of stroke by averaging points
        with their neighbours.

        The method is based on a (simple) moving average algorithm.

        Let p = p(0), ..., p(N) be the set points of this stroke,
            w = w(-M), ..., w(0), ..., w(M) be a set of weights.

        This algorithm aims at replacing p with a set p' such as

            p'(i) = (w(-M)*p(i-M) + ... + w(0)*p(i) + ... + w(M)*p(i+M)) / S

        and where S = w(-M) + ... + w(0) + ... w(M). End points are not
        affected.
        """
        if self._is_smoothed:
            return

        weights = [1, 1, 2, 1, 1] # Weights to be used
        times = 3 # Number of times to apply the algorithm

        if len(self) < len(weights):
            return

        offset = int(floor(len(weights) / 2.0))
        wsum = sum(weights)

        for n in range(times):
            s = self.copy()

            for i in range(offset, len(self) - offset):
                self[i].x = 0
                self[i].y = 0

                for j in range(len(weights)):
                    self[i].x += weights[j] * s[i + j - offset].x
                    self[i].y += weights[j] * s[i + j - offset].y

                self[i].x = int(round(self[i].x / wsum))
                self[i].y = int(round(self[i].y / wsum))

        self._is_smoothed = True

    def clear(self):
        """
        Remove all points from stroke.
        """
        while len(self) != 0:
            del self[0]
        self._is_smoothed = False

    def downsample(self, n):
        """
        Downsample by keeping only 1 sample every n samples.

        @type n: int
        """
        if len(self) == 0:
            return

        new_s = Stroke()
        for i in range(len(self)):
            if i % n == 0:
                new_s.append_point(self[i])

        self.copy_from(new_s)

    def downsample_threshold(self, threshold):
        """
        Downsample by removing consecutive samples for which
        the euclidean distance is inferior to threshold.

        @type threshod: int
        """
        if len(self) == 0:
            return

        new_s = Stroke()
        new_s.append_point(self[0])

        last = 0
        for i in range(1, len(self) - 2):
            u = [self[last].x, self[last].y]
            v = [self[i].x, self[i].y]

            if euclidean_distance(u, v) > threshold:
                new_s.append_point(self[i])
                last = i

        new_s.append_point(self[-1])

        self.copy_from(new_s)

    def upsample(self, n):
        """
        'Artificially' increase sampling by adding n linearly spaced points
        between consecutive points.

        @type n: int
        """
        self._upsample(lambda d: n)

    def upsample_threshold(self, threshold):
        """
        'Artificially' increase sampling, using threshold to determine
        how many samples to add between consecutive points.

        @type threshold: int
        """
        self._upsample(lambda d: int(floor(float(d) / threshold - 1)))

    def _upsample(self, func):
        """
        'Artificially' increase sampling, using func(distance) to determine how
        many samples to add between consecutive points.
        """
        if len(self) == 0:
            return

        new_s = Stroke()

        for i in range(len(self)- 1):
            x1, y1 = [self[i].x, self[i].y]
            x2, y2 = [self[i+1].x, self[i+1].y]

            new_s.append_point(self[i])

            dx = x2 - x1
            dy = y2 - y1

            if dx == 0:
                alpha = pi / 2
                cosalpha = 0.0
                sinalpha = 1.0
            else:
                alpha = atan(float(abs(dy)) / abs(x2 - x1))
                cosalpha = cos(alpha)
                sinalpha = sin(alpha)

            d = euclidean_distance([x1, y1], [x2, y2])
            signx = cmp(dx, 0)
            signy = cmp(dy, 0)

            n = func(d)

            for j in range(1, n+1):
                dx = cosalpha * 1.0 / (n + 1) * d
                dy = sinalpha * 1.0 / (n + 1) * d
                new_s.append_point(Point(x=int(x1+j*dx*signx),
                                         y=int(y1+j*dy*signy)))

        new_s.append_point(self[-1])

        self.copy_from(new_s)

    def __repr__(self):
        return "<Stroke %d pts (ref %d)>" % (len(self), id(self))

class Writing(object):
    """
    A sequence of L{Strokes<Stroke>}.
    """

    #: Default width and height of the canvas
    #: If the canvas used to create the Writing object
    #: has a different width or height, then
    #: the methods set_width and set_height need to be used
    WIDTH = 1000
    HEIGHT = 1000

    NORMALIZE_PROPORTION = 0.7 # percentage of the drawing area
    NORMALIZE_MIN_SIZE = 0.1 # don't nornalize if below that percentage

    def __init__(self):
        self._width = Writing.WIDTH
        self._height = Writing.HEIGHT
        self.clear()

    def clear(self):
        """
        Remove all strokes from writing.
        """
        self._strokes = []

    def get_duration(self):
        """
        Return the time that it took to draw the strokes.

        @rtype: int or None
        @return: time in millisecons or None if the information is not available
        """
        if self.get_n_strokes() > 0:
            if self._strokes[0][0].timestamp is not None and \
               self._strokes[-1][-1].timestamp is not None:
                return self._strokes[-1][-1].timestamp - \
                       self._strokes[0][0].timestamp
        return None

    def move_to(self, x, y):
        """
        Start a new stroke at (x,y).

        @type x: int
        @type y: int
        """
        # For compatibility
        point = Point()
        point.x = x
        point.y = y

        self.move_to_point(point)

    def line_to(self, x, y):
        """
        Add point with coordinates (x,y) to the current stroke.

        @type x: int
        @type y: int
        """
        # For compatibility
        point = Point()
        point.x = x
        point.y = y

        self.line_to_point(point)

    def move_to_point(self, point):
        """
        Start a new stroke at point.

        @type point: L{Point}
        """
        stroke = Stroke()
        stroke.append_point(point)

        self.append_stroke(stroke)

    def line_to_point(self, point):
        """
        Add point to the current stroke.

        @type point: L{Point}
        """
        self._strokes[-1].append(point)

    def get_n_strokes(self):
        """
        Return the number of strokes.

        @rtype: int
        """
        return len(self._strokes)

    def get_n_points(self):
        """
        Return the total number of points.
        """
        return sum([len(s) for s in self._strokes])

    def get_strokes(self, full=False):
        """
        Return strokes.

        @type full: boolean
        @param full: whether to return strokes as objects or as (x,y) pairs
        """
        if not full:
            # For compatibility
            return [[(int(p.x), int(p.y)) for p in s] for s in self._strokes]
        else:
            return self._strokes

    def append_stroke(self, stroke):
        """
        Add a new stroke.

        @type stroke: L{Stroke}
        """
        self._strokes.append(stroke)

    def insert_stroke(self, i, stroke):
        """
        Insert a stroke at a given position.

        @type stroke: L{Stroke}
        @type i: int
        @param i: position at which to add the stroke (starts at 0)
        """
        self._strokes.insert(i, stroke)

    def remove_stroke(self, i):
        """
        Remove the ith stroke.

        @type i: int
        @param i: position at which to delete a stroke (starts at 0)
        """
        if self.get_n_strokes() - 1 >= i:
            del self._strokes[i]

    def remove_last_stroke(self):
        """
        Remove last stroke.

        Equivalent to remove_stroke(n-1) where n is the number of strokes.
        """
        if self.get_n_strokes() > 0:
            del self._strokes[-1]

    def replace_stroke(self, i, stroke):
        """
        Replace the ith stroke with a new stroke.

        @type i: int
        @param i: position at which to replace a stroke (starts at 0)
        @type stroke: L{Stroke}
        @param stroke: the new stroke
        """
        if self.get_n_strokes() - 1 >= i:
            self.remove_stroke(i)
            self.insert_stroke(i, stroke)

    def resize(self, xrate, yrate):
        """
        Scale writing.

        @type xrate: float
        @param xrate: the x scaling factor
        @type yrate: float
        @param yrate: the y scaling factor
        """
        for stroke in self._strokes:
            if len(stroke) == 0:
                continue

            stroke[0].resize(xrate, yrate)

            for point in stroke[1:]:
                point.resize(xrate, yrate)

    def move_rel(self, dx, dy):
        """
        Translate writing.

        @type dx: int
        @param dx: relative distance from current position
        @type dy: int
        @param yrate: relative distance from current position
        """
        for stroke in self._strokes:
            if len(stroke) == 0:
                continue

            stroke[0].move_rel(dx, dy)

            for point in stroke[1:]:
                point.move_rel(dx, dy)

    def size(self):
        """
        Return writing size.

        @rtype: (x, y, width, height)
        @return: (x,y) are the coordinates of the upper-left point
        """
        xmin, ymin = 4294967296, 4294967296 # 2^32
        xmax, ymax = 0, 0

        for stroke in self._strokes:
            for point in stroke:
                xmin = min(xmin, point.x)
                ymin = min(ymin, point.y)
                xmax = max(xmax, point.x)
                ymax = max(ymax, point.y)

        return (xmin, ymin, xmax-xmin, ymax-ymin)

    def is_small(self):
        """
        Return whether the writing is small or not.

        A writing is considered small when it is written in a corner.
        This is used in Japanese to detect small hiragana and katakana.

        Note: is_small() should be used before normalize().

        @rtype: boolean
        @return: whether the writing is small or not
        """
        x, y, w, h = self.size()
        # 0.44 and 0.56 are used instead of 0.5 to allow the character to go a
        # little bit beyond the corners
        return ((x+w <= self.get_width() * 0.56 and
                 y+h <= 0.56 * self.get_height()) or # top-left
                (x >= 0.44 * self.get_width() and
                 y+h <= 0.56 * self.get_height()) or # top-right
                (x+w <= self.get_width() * 0.56 and
                 y >= 0.44 * self.get_height()) or # bottom-left
                (x >= 0.44 * self.get_width() and
                 y >= 0.44 * self.get_height())) # bottom-right

    def normalize(self):
        """
        Call L{normalize_size} and L{normalize_position} consecutively.
        """
        self.normalize_size()
        self.normalize_position()

    def normalize_position(self):
        """
        Translate character so as to have the same amount of space to
        each side of the drawing box.

        It improves the quality of characters by making them
        more centered on the drawing box.
        """
        x, y, width, height = self.size()

        dx = (self._width - width) / 2 - x
        dy = (self._height - height) / 2 - y

        self.move_rel(dx, dy)

    def normalize_size(self):
        """
        Scale character to match a given, fixed size.

        This improves the quality of characters which are too big or too small.
        """

        # Note: you should call normalize_position() after normalize_size()
        x, y, width, height = self.size()


        if float(width) / self._width > Writing.NORMALIZE_MIN_SIZE:
            xrate = self._width * Writing.NORMALIZE_PROPORTION / width
        else:
            # Don't normalize if too thin in width
            xrate = 1.0


        if float(height) / self._height > Writing.NORMALIZE_MIN_SIZE:
            yrate = self._height * Writing.NORMALIZE_PROPORTION / height
        else:
            # Don't normalize if too thin in height
            yrate = 1.0

        self.resize(xrate, yrate)

    def downsample(self, n):
        """
        Downsample by keeping only 1 sample every n samples.

        @type n: int
        """
        for s in self._strokes:
            s.downsample(n)

    def downsample_threshold(self, threshold):
        """
        Downsample by removing consecutive samples for which
        the euclidean distance is inferior to threshold.

        @type threshod: int
        """
        for s in self._strokes:
            s.downsample_threshold(threshold)

    def upsample(self, n):
        """
        'Artificially' increase sampling by adding n linearly spaced points
        between consecutive points.

        @type n: int
        """
        for s in self._strokes:
            s.upsample(n)

    def upsample_threshold(self, threshold):
        """
        'Artificially' increase sampling, using threshold to determine
        how many samples to add between consecutive points.

        @type threshold: int
        """
        for s in self._strokes:
            s.upsample_threshold(threshold)

    def get_size(self):
        """
        Return the size of the drawing box.

        @rtype: tuple

        Not to be confused with size() which returns the size the writing.
        """
        return (self.get_width(), self.get_height())

    def set_size(self, w, h):
        self.set_width(w)
        self.set_height(h)

    def get_width(self):
        """
        Return the width of the drawing box.

        @rtype: int
        """
        return self._width

    def set_width(self, width):
        """
        Set the drawing box width.

        This is necessary if the points which are added were not drawn in
        1000x1000 drawing box.
        """
        self._width = width

    def get_height(self):
        """
        Return the height of the drawing box.

        @rtype: int
        """
        return self._height

    def set_height(self, height):
        """
        Set the drawing box height.

        This is necessary if the points which are added were not drawn in
        1000x1000 drawing box.
        """
        self._height = height

    def to_xml(self):
        """
        Converts writing to XML.

        @rtype: str
        """
        s = "<width>%d</width>\n" % self.get_width()
        s += "<height>%d</height>\n" % self.get_height()

        s += "<strokes>\n"

        for stroke in self._strokes:
            for line in stroke.to_xml().split("\n"):
                s += "  %s\n" % line

        s += "</strokes>"

        return s

    def to_json(self):
        """
        Converts writing to JSON.

        @rtype: str
        """
        s = "{ \"width\" : %d, " % self.get_width()
        s += "\"height\" : %d, " % self.get_height()
        s += "\"strokes\" : ["

        s += ", ".join([stroke.to_json() for stroke in self._strokes])

        s += "]}"

        return s

    def to_sexp(self):
        """
        Converts writing to S-expressions.

        @rtype: str
        """
        return "((width %d)(height %d)(strokes %s))" % \
            (self._width, self._height,
             "".join([s.to_sexp() for s in self._strokes]))

    def __eq__(self, othr):
        if not othr.__class__.__name__ in ("Writing", "WritingProxy"):
            return False

        if self.get_n_strokes() != othr.get_n_strokes():
            return False

        if self.get_width() != othr.get_width():
            return False

        if self.get_height() != othr.get_height():
            return False

        othr_strokes = othr.get_strokes(full=True)

        for i in range(len(self._strokes)):
            if self._strokes[i] != othr_strokes[i]:
                return False

        return True

    def __ne__(self, othr):
        return not(self == othr)


        self.clear()
        self._is_smoothed = s.get_is_smoothed()
        for p in s:
            self.append_point(p.copy())

    def copy_from(self, w):
        """
        Replace writing with another writing.

        @type w: L{Writing}
        @param w: the writing to copy from
        """
        self.clear()
        self.set_width(w.get_width())
        self.set_height(w.get_height())

        for s in w.get_strokes(True):
            self.append_stroke(s.copy())

    def copy(self):
        """
        Return a copy writing.

        @rtype: L{Writing}
        """
        c = Writing()
        c.copy_from(self)
        return c

    def smooth(self):
        """
        Smooth all strokes. See L{Stroke.smooth}.
        """
        for stroke in self._strokes:
            stroke.smooth()

    def __repr__(self):
        return "<Writing %d strokes (ref %d)>" % (self.get_n_strokes(),
                                                  id(self))

class _IOBase(object):
    """
    Class providing IO functionality to L{Character} and \
    L{CharacterCollection}.
    """

    def __init__(self, path=None):
        self._path = path

        if path is not None:
            gzip = True if path.endswith(".gz") or path.endswith(".gzip") \
                        else False
            bz2 = True if path.endswith(".bz2") or path.endswith(".bzip2") \
                       else False

            self.read(path, gzip=gzip, bz2=bz2)

    def read(self, file, gzip=False, bz2=False, compresslevel=9):
        """
        Read XML from a file.

        @type file: str or file
        @param file: path to file or file object

        @type gzip: boolean
        @param gzip: whether the file is gzip-compressed or not

        @type bz2: boolean
        @param bz2: whether the file is bzip2-compressed or not

        @type compresslevel: int
        @param compresslevel: compression level (see gzip module documentation)

        Raises ValueError if incorrect XML.
        """
        try:
            if type(file) == str:
                if gzip:
                    file = gzipm.GzipFile(file, compresslevel=compresslevel)
                elif bz2:
                    try:
                        file = bz2m.BZ2File(file, compresslevel=compresslevel)
                    except NameError:
                        raise NotImplementedError
                else:
                    file = open(file)

                self._parse_file(file)
                file.close()
            else:
                self._parse_file(file)
        except (IOError, xml.parsers.expat.ExpatError):
            raise ValueError

    def read_string(self, string, gzip=False, bz2=False, compresslevel=9):
        """
        Read XML from string.

        @type string: str
        @param string: string containing XML

        Other parameters are identical to L{read}.
        """
        if gzip:
            io = cStringIO.StringIO(string)
            io = gzipm.GzipFile(fileobj=io, compresslevel=compresslevel)
            string = io.read()
        elif bz2:
            try:
                string = bz2m.decompress(string)
            except NameError:
                raise NotImplementedError

        self._parse_str(string)

    def write(self, file, gzip=False, bz2=False, compresslevel=9):
        """
        Write XML to a file.

        @type file: str or file
        @param file: path to file or file object

        @type gzip: boolean
        @param gzip: whether the file need be gzip-compressed or not

        @type bz2: boolean
        @param bz2: whether the file need be bzip2-compressed or not

        @type compresslevel: int
        @param compresslevel: compression level (see gzip module documentation)
        """
        if type(file) == str:
            if gzip:
                file = gzipm.GzipFile(file, "w", compresslevel=compresslevel)
            elif bz2:
                try:
                    file = bz2m.BZ2File(file, "w", compresslevel=compresslevel)
                except NameError:
                    raise NotImplementedError
            else:
                file = open(file, "w")

            file.write(self.to_str())
            file.close()
        else:
            file.write(self.to_str())

    def write_string(self, gzip=False, bz2=False, compresslevel=9):
        """
        Write XML to string.

        @rtype: str
        @return: string containing XML

        Other parameters are identical to L{write}.
        """
        if bz2:
            try:
                return bz2m.compress(self.to_str(), compresslevel=compresslevel)
            except NameError:
                raise NotImplementedError
        elif gzip:
            io = cStringIO.StringIO()
            f = gzipm.GzipFile(fileobj=io, mode="w",
                               compresslevel=compresslevel)
            f.write(self.to_str())
            f.close()
            return io.getvalue()
        else:
            return self.to_str()

    def save(self, path=None):
        """
        Save character to file.

        @type path: str
        @param path: path where to write the file or None if use the path \
                     that was given to the constructor

        The file extension is used to determine whether the file is plain,
        gzip-compressed or bzip2-compressed XML.
        """
        if [path, self._path] == [None, None]:
            raise ValueError, "A path must be specified"
        elif path is None:
            path = self._path

        gzip = True if path.endswith(".gz") or path.endswith(".gzip") \
                    else False
        bz2 = True if path.endswith(".bz2") or path.endswith(".bzip2") \
                       else False

        self.write(path, gzip=gzip, bz2=bz2)

class _XmlBase(_IOBase):
    """
    Class providing XML functionality to L{Character} and \
    L{CharacterCollection}.
    """

    @classmethod
    def validate(cls, string):
        """
        Validate XML against a DTD.

        @type string: str
        @param string: a string containing XML

        DTD must be an attribute of cls.
        """
        try:
            # first check whether etree is available or not
            etree
            try:
                dtd = etree.DTD(cStringIO.StringIO(cls.DTD))
                root = etree.XML(string.strip())
                return dtd.validate(root)
            except etree.XMLSyntaxError:
                return False
        except NameError:
            # this means that the functionality is not available on that
            # system so you have to catch that exception if you want to
            # ignore it
            raise NotImplementedError

    def _parse_file(self, file):
        parser = self._get_parser()
        parser.ParseFile(file)

    def _parse_str(self, string):
        parser = self._get_parser()
        parser.Parse(string)

    def _get_parser(self):
        parser = xml.parsers.expat.ParserCreate(encoding="UTF-8")
        parser.StartElementHandler = self._start_element
        parser.EndElementHandler = self._end_element
        parser.CharacterDataHandler = self._char_data
        self._first_tag = True
        return parser

class Character(_XmlBase):
    """
    A handwritten character.

    A Character is composed of meta-data and handwriting data.
    Handwriting data are contained in L{Writing} objects.

    Building character objects
    ==========================

    A character can be built from scratch progmatically:

    >>> s = Stroke()
    >>> s.append_point(Point(10, 20))
    >>> w = Writing()
    >>> w.append_stroke(s)
    >>> c = Character()
    >>> c.set_writing(writing)

    Reading XML files
    =================

    A character can be read from an XML file:

    >>> c = Character()
    >>> c.read("myfile")

    Gzip-compressed and bzip2-compressed XML files can also be read:

    >>> c = Character()
    >>> c.read("myfilegz", gzip=True)

    >>> c = Character()
    >>> c.read("myfilebz", bz2=True)

    A similar method read_string exists to read the XML from a string
    instead of a file.

    For convenience, you can directly load a character by passing it the
    file to load. In that case, compression is automatically detected based on
    file extension (.gz, .bz2).

    >>> c = Character("myfile.xml.gz")

    The recommended extension for XML character files is .xml.

    Writing XML files
    =================

    A character can be saved to an XML file by using the write() method.

    >>> c.write("myfile")

    The write method has gzip and bz2 arguments just like read(). In addition,
    there is a write_string method which generates a string instead of a file.

    For convenience, you can save a character with the save() method.
    It automatically detects compression based on the file extension.

    >>> c.save("mynewfile.xml.bz2")

    If the Character object was passed a file when it was constructed,
    the path can ce omitted.

    >>> c = Character("myfile.gz")
    >>> c.save()

    >>> c = Character()
    >>> c.save()
    Traceback (most recent call last):
    File "<stdin>", line 1, in <module>
    File "tegaki/character.py", line 1238, in save
        raise ValueError, "A path must be specified"
    ValueError: A path must be specified

    """

    DTD = \
"""
<!ELEMENT character (utf8?,width?,height?,strokes)>
<!ELEMENT utf8 (#PCDATA)>
<!ELEMENT width (#PCDATA)>
<!ELEMENT height (#PCDATA)>
<!ELEMENT strokes (stroke+)>
<!ELEMENT stroke (point+)>
<!ELEMENT point EMPTY>

<!ATTLIST point x CDATA #REQUIRED>
<!ATTLIST point y CDATA #REQUIRED>
<!ATTLIST point timestamp CDATA #IMPLIED>
<!ATTLIST point pressure CDATA #IMPLIED>
<!ATTLIST point xtilt CDATA #IMPLIED>
<!ATTLIST point ytilt CDATA #IMPLIED>

"""

    def __init__(self, path=None):
        """
        Creates a new Character.

        @type path: str or None
        @param path: path to file to load or None if empty character

        The file extension is used to determine whether the file is plain,
        gzip-compressed or bzip2-compressed XML.
        """
        self._writing = Writing()
        self._utf8 = None
        _XmlBase.__init__(self, path)

    def get_utf8(self):
        """
        Return the label of the character.

        @rtype: str
        """
        return self._utf8

    def get_unicode(self):
        """
        Return the label character.

        @rtype: unicode
        """
        return unicode(self.get_utf8(), "utf8")

    def set_utf8(self, utf8):
        """
        Set the label the character.

        @type utf8: str
        """
        self._utf8 = utf8

    def set_unicode(self, uni):
        """
        Set the label of the character.

        @type uni: unicode
        """
        self._utf8 = uni.encode("utf8")

    def get_writing(self):
        """
        Return the handwriting data of the character.

        @rtype: L{Writing}
        """
        return self._writing

    def set_writing(self, writing):
        """
        Set the handwriting data of the character.

        @type writing: L{Writing}
        """

        self._writing = writing

    def hash(self):
        """
        Return a sha1 digest for that character.
        """
        return hashlib.sha1(self.to_xml()).hexdigest()

    def to_str(self):
        return self.to_xml()

    def to_xml(self):
        """
        Converts character to XML.

        @rtype: str
        """
        s = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"

        s += "<character>\n"

        if self._utf8:
            s += "  <utf8>%s</utf8>\n" % self._utf8

        for line in self._writing.to_xml().split("\n"):
            s += "  %s\n" % line

        s += "</character>"

        return s

    def to_json(self):
        """
        Converts character to JSON.

        @rtype: str
        """
        s = "{"

        attrs = ["\"utf8\" : \"%s\"" % self._utf8,
                 "\"writing\" : " + self._writing.to_json()]

        s += ", ".join(attrs)

        s += "}"

        return s

    def to_sexp(self):
        """
        Converts character to S-expressions.

        @rtype: str
        """
        return "(character (value %s)" % self._utf8 + \
                    self._writing.to_sexp()[1:-1]

    def __eq__(self, char):
        if not char.__class__.__name__ in ("Character", "CharacterProxy"):
            return False

        return self._utf8 == char.get_utf8() and \
               self._writing == char.get_writing()

    def __ne__(self, othr):
        return not(self == othr)


        self.clear()
        self.set_width(w.get_width())
        self.set_height(w.get_height())

        for s in w.get_strokes(True):
            self.append_stroke(s.copy())

    def copy_from(self, c):
        """
        Replace character with another character.

        @type c: L{Character}
        @param c: the character to copy from
        """
        self.set_utf8(c.get_utf8())
        self.set_writing(c.get_writing().copy())

    def copy(self):
        """
        Return a copy of character.

        @rtype: L{Character}
        """
        c = Character()
        c.copy_from(self)
        return c

    def __repr__(self):
        return "<Character %s (ref %d)>" % (str(self.get_utf8()), id(self))

    # Private...

    def _start_element(self, name, attrs):
        self._tag = name

        if self._first_tag:
            self._first_tag = False
            if self._tag != "character":
                raise ValueError, "The very first tag should be <character>"

        if self._tag == "stroke":
            self._stroke = Stroke()

        elif self._tag == "point":
            point = Point()

            for key in ("x", "y", "pressure", "xtilt", "ytilt", "timestamp"):
                if attrs.has_key(key):
                    value = attrs[key].encode("UTF-8")
                    if key in ("pressure", "xtilt", "ytilt"):
                        value = float(value)
                    else:
                        value = int(float(value))
                else:
                    value = None

                setattr(point, key, value)

            self._stroke.append_point(point)

    def _end_element(self, name):
        if name == "character":
            for s in ["_tag", "_stroke"]:
                if s in self.__dict__:
                    del self.__dict__[s]

        if name == "stroke":
            if len(self._stroke) > 0:
                self._writing.append_stroke(self._stroke)
            self._stroke = None

        self._tag = None

    def _char_data(self, data):
        if self._tag == "utf8":
            self._utf8 = data.encode("UTF-8")
        elif self._tag == "width":
            self._writing.set_width(int(data))
        elif self._tag == "height":
            self._writing.set_height(int(data))


########NEW FILE########
__FILENAME__ = charcol
# -*- coding: utf-8 -*-

# Copyright (C) 2009 The Tegaki project contributors
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

# Contributors to this file:
# - Mathieu Blondel

import sqlite3
import base64
import tempfile
import re
import os

from tegaki.dictutils import SortedDict
from tegaki.character import _XmlBase, Point, Stroke, Writing, Character

def _dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = d[idx] = row[idx]
    return d

class ObjectProxy(object):
    """
    An object that forwards all attribute and method calls to another object.

    Object proxies are used to automatically reflect back in the db
    changes that are made to objects. For example:

    >>> char = charcol.get_all_characters()[0]
    >>> char.set_utf8(newvalue) # will be automatically changed in the db
    """

    WRITE_METHODS = []
    READ_METHODS = []
    WRITE_ATTRIBUTES = []

    def __init__(self, charpool, obj, charobj=None):
        self._charpool = charpool
        # the object to redirect attributes and method calls to
        self._obj = obj
        # the original character object
        self._charobj = obj if charobj is None else charobj

    def __getattr__(self, attr_):
        attr = getattr(self._obj, attr_)

        write = False
        if attr_ in self.WRITE_METHODS:
            write = True
        elif not attr_ in self.READ_METHODS:
            return attr
        def wrapper(*args, **kw):
            if write: self._charpool.add_char(self._charobj)
            return _apply_proxy(self._charpool, attr(*args, **kw),
self._charobj)
        return wrapper


    def __setattr__(self, attr, value):
        if attr in self.WRITE_ATTRIBUTES:
            self._charpool.add_char(self._charobj)
            setattr(self._obj, attr, value)
        self.__dict__[attr] = value

    def __eq__(self, othr):
        if othr.__class__.__name__.endswith("Proxy"):
            othr = othr._obj
        return self._obj == othr

    def __ne__(self, othr):
        return not(self == othr)

class PointProxy(ObjectProxy):
    """
    Proxy to Point.
    """
    WRITE_METHODS = ["resize", "move_rel", "copy_from"]
    WRITE_ATTRIBUTES = Point.KEYS

    def __getitem__(self, x):
        return self._obj[x]

class StrokeProxy(ObjectProxy):
    """
    Proxy to Stroke.
    """

    WRITE_METHODS = ["append_point", "insert", "smooth", "clear",
                     "downsample", "downsample_threshold",
                     "upsample", "upsample_threshod"]
    READ_METHODS = []

    def __getitem__(self, i):
        return _apply_proxy(self._charpool, self._obj[i], self._charobj)

    def __len__(self):
        return len(self._obj)

class WritingProxy(ObjectProxy):
    """
    Proxy to Writing.
    """

    # Note: Some method calls need not be mentioned below
    # because they automatically update the db thanks to
    # Point and Stroke methods that are being used in their implementation.

    WRITE_METHODS = ["clear", "move_to_point", "line_to_point",
                     "set_width", "set_height", "remove_stroke"]
    READ_METHODS = ["get_strokes"]

class CharacterProxy(ObjectProxy):
    """
    Proxy to Writing.
    """

    WRITE_METHODS = ["set_utf8", "set_unicode", "set_writing",
                     "read", "read_string"]
    READ_METHODS = ["get_writing"]

    def __repr__(self):
        return "<CharacterProxy %s (ref %d)>" % (str(self.get_utf8()), id(self))

OBJ_PROXY = {Character: CharacterProxy,
             Writing : WritingProxy,
             Stroke : StrokeProxy,
             Point : PointProxy}

def _apply_proxy(charpool, obj, charobj):
    return _apply_proxy_rec(charpool, obj, charobj)

def _apply_proxy_rec(charpool, obj, charobj, reclevel=0):
    try:
        return OBJ_PROXY[obj.__class__](charpool, obj, charobj)
    except KeyError:
        if (isinstance(obj, tuple) or isinstance(obj, list)) and reclevel <= 1:
            return [_apply_proxy_rec(charpool, ele, charobj, reclevel+1) \
                        for ele in obj]
        else:
            return obj

class _CharPool(dict):
    """
    Holds characters that need be updated.

    We don't want changes to be immediately reflected back to the db
    for performance reasons. The _CharPool keeps track of what objects need
    be updated.
    """

    def __init__(self, cursor):
        self._c = cursor

    def add_char(self, char):
        self[char.charid] = char

    def _update_character(self, char):
        self._c.execute("""UPDATE characters
SET utf8=?, n_strokes=?, data=?, sha1=?
WHERE charid=?""", (char.get_utf8(), char.get_writing().get_n_strokes(),
                    _adapt_character(char), char.hash(), char.charid))

    def clear_pool_threshold(self, threshold=100):
        if len(self) > threshold:
            self.clear_pool()

    def clear_pool(self):
        for charid, char in self.items():
            self._update_character(char)
        self.clear()

def _convert_character(data):
    # converts a BLOB into an object
    char = Character()
    char.read_string(base64.b64decode(data), gzip=True)
    return char

def _adapt_character(char):
    # converts an object into a BLOB
    return base64.b64encode(char.write_string(gzip=True))

def _gzipbz2(path):
   return (True if path.endswith(".gz") or path.endswith(".gzip") else False,
           True if path.endswith(".bz2") or path.endswith(".bzip2") else False)

class CharacterCollection(_XmlBase):
    """
    A collection of L{Characters<Character>}.

    A CharacterCollection is composed of sets.
    Each set can be composed of zero, one, or more characters.

    /!\ Sets do not necessarily contain only characters of the same class
    / utf8 value. Sets may also be used to group characters in other fashions
    (e.g. by number of strokes, by handwriting quality, etc...).
    Therefore the set name is not guaranteed to contain the utf8 value of
    the characters of that set. The utf8 value must be retrieved from each
    character individually.

    Building character collection objects
    =====================================

    A character collection can be built from scratch progmatically:


    >>> char = Character()
    >>> charcol = CharacterCollection()
    >>> charcol.add_set("my set")
    >>> charcol.append_character("my set", char)

    Reading XML files
    =================

    A character collection can be read from an XML file:

    >>> charcol = CharacterCollection()
    >>> charcol.read("myfile")

    Gzip-compressed and bzip2-compressed XML files can also be read:

    >>> charcol = CharacterCollection()
    >>> charcol.read("myfilegz", gzip=True)

    >>> charcol = Character()
    >>> charcol.read("myfilebz", bz2=True)

    A similar method read_string exists to read the XML from a string
    instead of a file.

    For convenience, you can directly load a character collection by passing it
    the file to load. In that case, compression is automatically detected based
    on file extension (.gz, .bz2).

    >>> charcol = Character("myfile.xml.gz")

    The recommended extension for XML character collection files is .charcol.

    Writing XML files
    =================

    A character collection can be saved to an XML file by using the write()
    method.

    >>> charcol.write("myfile")

    The write method has gzip and bz2 arguments just like read(). In addition,
    there is a write_string method which generates a string instead of a file.

    For convenience, you can save a character collection with the save() method.
    It automatically detects compression based on the file extension.

    >>> charcol.save("mynewfile.xml.bz2")

    If the CharacterCollection object was passed a file when it was constructed,
    the path can ce omitted.

    >>> charcol = Character("myfile.gz")
    >>> charcol.save()

    Using .chardb files
    ===================

    XML files allow to retain human-readability and are ideal for small
    character collections. However, they force the whole database to be kept
    in memory. For larger collections, it's recommended to use .chardb files
    instead. Their loading is faster and the whole collection doesn't
    need be kept entirely in memory. However human-readability ist lost.

    >>> charcol = CharacterCollection("charcol.chardb")
    [...]
    >>> charcol.save()

    The .chardb extension is required.
    """

    #: With WRITE_BACK set to True, proxy objects are returned in place of
    #: character, writing, stroke and point objects in order to automatically
    #: reflect changes to these objects back to the sqlite db.
    #: However, there is probably overhead usigng them.
    WRITE_BACK = True

    def get_auto_commit(self):
        return True if self._con.isolation_level is None else False

    def set_auto_commit(self, auto):
        self._con.isolation_level = None if auto else ""

    #: With AUTO_COMMIT set to true, data is immediately written to disk
    AUTO_COMMIT = property(get_auto_commit, set_auto_commit)

    DTD = \
"""
<!ELEMENT character-collection (set*)>
<!ELEMENT set (character*)>

<!-- The name attribute identifies a set uniquely -->
<!ATTLIST set name CDATA #REQUIRED>

<!ELEMENT character (utf8?,width?,height?,strokes)>
<!ELEMENT utf8 (#PCDATA)>
<!ELEMENT width (#PCDATA)>
<!ELEMENT height (#PCDATA)>
<!ELEMENT strokes (stroke+)>
<!ELEMENT stroke (point+)>
<!ELEMENT point EMPTY>

<!ATTLIST point x CDATA #REQUIRED>
<!ATTLIST point y CDATA #REQUIRED>
<!ATTLIST point timestamp CDATA #IMPLIED>
<!ATTLIST point pressure CDATA #IMPLIED>
<!ATTLIST point xtilt CDATA #IMPLIED>
<!ATTLIST point ytilt CDATA #IMPLIED>
"""

    def __init__(self, path=":memory:"):
        """
        Construct a collection.

        @type path: str
        @param path: an XML file or a DB file (see also L{bind})
        """
        if path is None:
            path = ":memory:"

        if not path in ("", ":memory:") and not path.endswith(".chardb"):
            # this should be an XML character collection

            gzip, bz2 = _gzipbz2(path)

            self.bind(":memory:")

            self.read(path, gzip=gzip, bz2=bz2)

            self._path = path # contains the path to the xml file
        else:
            # this should be either a .chardb, ":memory:" or ""
            self.bind(path)
            self._path = None

    # DB utils

    def _e(self, req, *a, **kw):
        self._charpool.clear_pool()
        #print req, a, kw
        return self._c.execute(req, *a, **kw)

    def _em(self, req, *a, **kw):
        self._charpool.clear_pool()
        #print req, a, kw
        return self._c.executemany(req, *a, **kw)

    def _fo(self):
        return self._c.fetchone()

    def _fa(self):
        return self._c.fetchall()

    def _efo(self, req, *a, **kw):
        self._e(req, *a, **kw)
        return self._fo()

    def _efa(self, req, *a, **kw):
        self._e(req, *a, **kw)
        return self._fa()

    def _has_tables(self):
        self._e("SELECT count(type) FROM sqlite_master WHERE type = 'table'")
        return self._fo()[0] > 0

    def _create_tables(self):
        self._c.executescript("""
CREATE TABLE character_sets(
  setid    INTEGER PRIMARY KEY,
  name     TEXT
);

CREATE TABLE characters(
  charid     INTEGER PRIMARY KEY,
  setid      INTEGER REFERENCES character_sets,
  utf8       TEXT,
  n_strokes  INTEGER,
  data       BLOB, -- gz xml
  sha1       TEXT
);

CREATE INDEX character_setid_index ON characters(setid);
""")

    def get_character_from_row(self, row):
        # charid, setid, utf8, n_strokes, data, sha1
        char = _convert_character(row['data'])
        char.charid = row['charid']
        if self.WRITE_BACK:
            return CharacterProxy(self._charpool, char)
        else:
            return char

    def _update_set_ids(self):
        self._SETIDS = SortedDict()
        for row in self._efa("SELECT * FROM character_sets ORDER BY setid"):
            self._SETIDS[row['name']] = row['setid']

    # Public API

    def __repr__(self):
        return "<CharacterCollection %d characters (ref %d)>" % \
                    (self.get_total_n_characters(), id(self))

    def bind(self, path):
        """
        Bind database to a db file.

        All changes to the previous binded database will be lost
        if you haven't committed changes with commit().

        @type path: str

        Possible values for path:
            ":memory:"                  for fully in memory database

            ""                          for a in memory database that uses
                                        temp files under pressure

            "/path/to/file.chardb"      for file-based database
        """
        self._con = sqlite3.connect(path)
        self._con.text_factory = str
        self._con.row_factory = _dict_factory #sqlite3.Row
        self._c = self._con.cursor()
        self._charpool = _CharPool(self._c)

        if not self._has_tables():
            self._create_tables()

        self._update_set_ids()
        self._dbpath = path

    def get_db_filename(self):
        """
        Returns the db file which is internally used by the collection.

        @rtype: str or None
        @return: file path or None if in memory db
        """
        return None if self._dbpath in (":memory:", "") else self._dbpath

    def commit(self):
        """
        Commit changes since last commit.
        """
        self._charpool.clear_pool()
        self._con.commit()

    def save(self, path=None):
        """
        Save collection to a file.

        @type path: str
        @param path: path where to write the file or None if use the path \
                     that was given to the constructor

        If path ends with .chardb, it's saved as binary db file. Otherwise, it
        will be saved as XML.

        In the latter case, the file extension is used to determine whether the
        file must be saved as plain, gzip-compressed or bzip2-compressed XML.

        If path is omitted, the path that was given to the CharacterCollection
        constructor is used.
        """
        if path is None:
            if self._path is not None:
                # an XML file was provided to constructor
                gzip, bz2 = _gzipbz2(self._path)
                self.write(self._path, gzip=gzip, bz2=bz2)
        else:
            if path.endswith(".chardb"):
                if self._dbpath != path:
                    # the collection changed its database name
                    # FIXME: this can rewritten more efficiently with
                    # the ATTACH command
                    if os.path.exists(path):
                        os.unlink(path)
                    newcc = CharacterCollection(path)
                    newcc.merge([self])
                    newcc.commit()
                    del newcc
                    self.bind(path)
            else:
                gzip, bz2 = _gzipbz2(path)
                self.write(path, gzip=gzip, bz2=bz2)

        self.commit()

    def to_stroke_collection(self, dictionary, silent=True):
        """
        @type dictionary: L{CharacterStrokeDictionary
        """
        strokecol = CharacterCollection()
        for char in self.get_all_characters_gen():
            stroke_labels = dictionary.get_strokes(char.get_unicode())[0]
            strokes = char.get_writing().get_strokes(full=True)

            if len(strokes) != len(stroke_labels):
                if silent:
                    continue
                else:
                    raise ValueError, "The number of strokes doesn't " \
                                      "match with reference character"

            for stroke, label in zip(strokes, stroke_labels):
                utf8 = label.encode("utf-8")
                strokecol.add_set(utf8)
                writing = Writing()
                writing.append_stroke(stroke)
                writing.normalize_position()
                schar = Character()
                schar.set_utf8(utf8)
                schar.set_writing(writing)
                strokecol.append_character(utf8, schar)

        return strokecol


    @staticmethod
    def from_character_directory(directory,
                                 extensions=["xml", "bz2", "gz"],
                                 recursive=True,
                                 check_duplicate=False):
        """
        Creates a character collection from a directory containing
        individual character files.
        """
        regexp = re.compile("\.(%s)$" % "|".join(extensions))
        charcol = CharacterCollection()

        for name in os.listdir(directory):
            full_path = os.path.join(directory, name)
            if os.path.isdir(full_path) and recursive:
                charcol += CharacterCollection.from_character_directory(
                               full_path, extensions)
            elif regexp.search(full_path):
                char = Character()
                gzip = False; bz2 = False
                if full_path.endswith(".gz"): gzip = True
                if full_path.endswith(".bz2"): bz2 = True

                try:
                    char.read(full_path, gzip=gzip, bz2=bz2)
                except ValueError:
                    continue # ignore malformed XML files

                utf8 = char.get_utf8()
                if utf8 is None: utf8 = "Unknown"

                charcol.add_set(utf8)
                if not check_duplicate or \
                   not char in charcol.get_characters(utf8):
                    charcol.append_character(utf8, char)

        return charcol

    def concatenate(self, other, check_duplicate=False):
        """
        Merge two charcols together and return a new charcol

        @type other: CharacterCollection
        """
        new = CharacterCollection()
        new.merge([self, other], check_duplicate=check_duplicate)
        return new

    def merge(self, charcols, check_duplicate=False):
        """
        Merge several charcacter collections into the current collection.

        @type charcols: list
        @param charcols: a list of CharacterCollection to merge
        """

        try:
            # it's faster to delete the whole index and rewrite it afterwards
            self._e("""DROP INDEX character_setid_index;""")

            for charcol in charcols:
                for set_name in charcol.get_set_list():
                    self.add_set(set_name)

                    if check_duplicate:
                        existing_chars = self.get_characters(set_name)
                        chars = charcol.get_characters(set_name)
                        chars = [c for c in chars if not c in existing_chars]
                        self.append_characters(set_name, chars)
                    else:
                        chars = charcol.get_character_rows(set_name)
                        self.append_character_rows(set_name, chars)

        finally:
            self._e("""CREATE INDEX character_setid_index
ON characters(setid);""")

    def __add__(self, other):
        return self.concatenate(other)

    def add_set(self, set_name):
        """
        Add a new set to collection.

        @type set_name: str
        """
        self.add_sets([set_name])

    def add_sets(self, set_names):
        """
        Add new sets to collection.

        @type set_names: list of str
        """
        set_names = [(set_name,) for set_name in set_names  \
                        if not set_name in self._SETIDS]
        self._em("INSERT INTO character_sets(name) VALUES (?)", set_names)
        self._update_set_ids()

    def remove_set(self, set_name):
        """
        Remove set_name from collection.

        @type set_name: str
        """
        self.remove_sets([set_name])

    def remove_sets(self, set_names):
        """
        Remove set_name from collection.

        @type set_name: str
        """
        set_names = [(set_name,) for set_name in set_names]
        self._em("DELETE FROM character_sets WHERE name=?", set_names)
        self._update_set_ids()

    def get_set_list(self):
        """
        Return the sets available in collection.

        @rtype: list of str
        """
        return self._SETIDS.keys()

    def get_n_sets(self):
        """
        Return the number of sets available in collection.

        @rtype: int
        """
        return len(self._SETIDS)

    def get_characters(self, set_name, limit=-1, offset=0):
        """
        Return character belonging to a set.

        @type set_name: str
        @param set_name: the set characters belong to

        @type limit: int
        @param limit: the number of characters needed or -1 if all

        @type offset: int
        @param offset: the offset to start from (0 if from beginning)

        @rtype: list of L{Character}
        """
        return list(self.get_characters_gen(set_name, limit, offset))

    def get_characters_gen(self, set_name, limit=-1, offset=0):
        """
        Return a generator to iterate over characters. See L{get_characters).
        """
        rows = self.get_character_rows(set_name, limit, offset)
        return (self.get_character_from_row(r) for r in rows)

    def get_character_rows(self, set_name, limit=-1, offset=0):
        i = self._SETIDS[set_name]
        self._e("""SELECT * FROM characters
WHERE setid=? ORDER BY charid LIMIT ? OFFSET ?""", (i, int(limit), int(offset)))
        return self._fa()

    def get_random_characters(self, n):
        """
        Return characters at random.

        @type n: int
        @param n: number of random characters needed.
        """
        return list(self.get_random_characters_gen(n))

    def get_random_characters_gen(self, n):
        """
        Return a generator to iterate over random characters. See \
        L{get_random_characters).
        """
        self._e("""SELECT DISTINCT * from characters
ORDER BY RANDOM() LIMIT ?""", (int(n),))
        return (self.get_character_from_row(r) for r in self._fa())

    def get_n_characters(self, set_name):
        """
        Return the number of character belonging to a set.

        @type set_name: str
        @param set_name: the set characters belong to

        @rtype int
        """
        try:
            i = self._SETIDS[set_name]
            return self._efo("""SELECT count(charid) FROM characters
WHERE setid=?""", (i,))[0]

        except KeyError:
            return 0

    def get_all_characters(self, limit=-1, offset=0):
        """
        Return all characters in collection.

        @type limit: int
        @param limit: the number of characters needed or -1 if all

        @type offset: int
        @param offset: the offset to start from (0 if from beginning)

        @rtype: list of L{Character}
        """
        return list(self.get_all_characters_gen(limit=-1, offset=0))

    def get_all_characters_gen(self, limit=-1, offset=0):
        """
        Return a generator to iterate over all characters. See \
        L{get_all_characters).
        """
        self._e("""SELECT * FROM characters
ORDER BY charid LIMIT ? OFFSET ?""", (int(limit), int(offset)))
        return (self.get_character_from_row(r) for r in self._fa())

    def get_total_n_characters(self):
        """
        Return the total number of characters in collection.

        @rtype: int
        """
        return self._efo("SELECT COUNT(charid) FROM characters")[0]

    def get_total_n_strokes(self):
        """
        Return the total number of strokes in collection.

        @rtype: int
        """
        return self._efo("SELECT SUM(n_strokes) FROM characters")[0]

    def get_average_n_strokes(self, set_name):
        """
        Return the average number of stroke of the characters in that set.
        """
        i = self._SETIDS[set_name]
        return self._efo("""SELECT AVG(n_strokes) FROM characters
WHERE setid=?""", (i,))[0]

    def set_characters(self, set_name, characters):
        """
        Set/Replace the characters of a set.

        @type set_name: str
        @param set_name: the set that needs be updated

        @type characters: list of L{Character}
        """
        i = self._SETIDS[set_name]
        self._e("DELETE FROM characters WHERE setid=?", (i,))
        for char in characters:
            self.append_character(set_name, char)

    def append_character(self, set_name, character):
        """
        Append a new character to a set.

        @type set_name: str
        @param set_name: the set to which the character needs be added

        @type character: L{Character}
        """
        self.append_characters(set_name, [character])

    def append_characters(self, set_name, characters):
        rows = [{'utf8':c.get_utf8(),
                 'n_strokes':c.get_writing().get_n_strokes(),
                 'data':_adapt_character(c),
                 'sha1':c.hash()} for c in characters]

        self.append_character_rows(set_name, rows)

    def append_character_rows(self, set_name, rows):
        i = self._SETIDS[set_name]
        tupls = [(i, r['utf8'], r['n_strokes'], r['data'], r['sha1']) \
                  for r in rows]

        self._em("""INSERT INTO
characters (setid, utf8, n_strokes, data, sha1)
VALUES (?,?,?,?,?)""", tupls)

    def insert_character(self, set_name, i, character):
        """
        Insert a new character to a set at a given position.

        @type set_name: str
        @param set_name: the set to which the character needs be inserted

        @type i: int
        @param i: position

        @type character: L{Character}
        """
        chars = self.get_characters(set_name)
        chars.insert(i, character)
        self.set_characters(set_name, chars)

    def remove_character(self, set_name, i):
        """
        Remove a character from a set at a given position.

        @type set_name: str
        @param set_name: the set from which the character needs be removed

        @type i: int
        @param i: position
        """
        setid = self._SETIDS[set_name]
        charid = self._efo("""SELECT charid FROM characters
WHERE setid=? ORDER BY charid LIMIT 1 OFFSET ?""", (setid, i))[0]
        if charid:
            self._e("DELETE FROM characters WHERE charid=?", (charid,))

    def remove_last_character(self, set_name):
        """
        Remove the last character from a set.

        @type set_name: str
        @param set_name: the set from which the character needs be removed
        """
        setid = self._SETIDS[set_name]
        charid = self._efo("""SELECT charid FROM characters
WHERE setid=? ORDER BY charid DESC LIMIT 1""", (setid,))[0]
        if charid:
            self._e("DELETE FROM characters WHERE charid=?", (charid,))

    def update_character_object(self, character):
        """
        Update a character.

        @type character: L{Character}

        character must have been previously retrieved from the collection.
        """
        if not hasattr(character, "charid"):
            raise ValueError, "The character object needs a charid attribute"
        self._e("""UPDATE characters
SET utf8=?, n_strokes=?, data=?, sha1=?
WHERE charid=?""", (character.get_utf8(),
                    character.get_writing().get_n_strokes(),
                    _adapt_character(character),
                    character.hash(),
                    character.charid))

    def replace_character(self, set_name, i, character):
        """
        Replace the character at a given position with a new character.

        @type set_name: str
        @param set_name: the set where the character needs be replaced

        @type i: int
        @param i: position

        @type character: L{Character}
        """
        setid = self._SETIDS[set_name]
        charid = self._efo("""SELECT charid FROM characters
WHERE setid=? ORDER BY charid LIMIT 1 OFFSET ?""", (setid, i))[0]
        if charid:
            character.charid = charid
            self.update_character_object(character)

    def _get_dict_from_text(self, text):
        text = text.replace(" ", "").replace("\n", "").replace("\t", "")
        dic = {}
        for c in text:
            dic[c] = 1
        return dic

    def include_characters_from_text(self, text):
        """
        Only keep characters found in a text.

        Or put differently, remove all characters but those found in a text.

        @type text: str
        """
        dic = self._get_dict_from_text(unicode(text, "utf8"))
        utf8values = ",".join(["'%s'" % k for k in dic.keys()])
        self._e("DELETE FROM characters WHERE utf8 NOT IN(%s)" % utf8values)
        self.remove_empty_sets()

    def include_characters_from_files(self, text_files):
        """
        Only keep characters found in text_files.

        @type text_files: list
        @param text_files: a list of file paths
        """
        buf = ""
        for inc_path in text_files:
            f = open(inc_path)
            buf += f.read()
            f.close()

        if len(buf) > 0:
            self.include_characters_from_text(buf)

    def exclude_characters_from_text(self, text):
        """
        Exclude characters found in a text.

        @type text: str
        """
        dic = self._get_dict_from_text(unicode(text, "utf8"))
        utf8values = ",".join(["'%s'" % k for k in dic.keys()])
        self._e("DELETE FROM characters WHERE utf8 IN(%s)" % utf8values)
        self.remove_empty_sets()

    def exclude_characters_from_files(self, text_files):
        """
        Exclude characters found in text_files.

        @type text_files: list
        @param text_files: a list of file paths
        """
        buf = ""
        for exc_path in text_files:
            f = open(exc_path)
            buf += f.read()
            f.close()

        if len(buf) > 0:
            self.exclude_characters_from_text(buf)

    def remove_samples(self, keep_at_most):
        """
        Remove samples.

        @type keep_at_most: the maximum number of samples to keep.
        """
        for set_name in self.get_set_list():
            if self.get_n_characters(set_name) > keep_at_most:
                setid = self._SETIDS[set_name]
                self._e("""DELETE FROM characters
WHERE charid IN(SELECT charid FROM characters
                WHERE setid=? ORDER BY charid LIMIT -1 OFFSET ?)""",
                        (setid, keep_at_most))

    def _get_set_char_counts(self):
        rows = self._efa("""SELECT setid, COUNT(charid) AS n_chars
FROM characters GROUP BY setid""")
        d = {}
        for row in rows:
            d[row['setid']] = row['n_chars']
        return d

    def remove_empty_sets(self):
        """
        Remove sets that don't include any character.
        """
        charcounts = self._get_set_char_counts()
        empty_sets = []

        for set_name, setid in self._SETIDS.items():
            try:
                if charcounts[setid] == 0:
                    empty_sets.append(set_name)
            except KeyError:
                empty_sets.append(set_name)

        self.remove_sets(empty_sets)

    def to_str(self):
        return self.to_xml()

    def to_xml(self):
        """
        Converts collection to XML.

        @rtype: str
        """
        s = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
        s += "<character-collection>\n"

        for set_name in self.get_set_list():
            s += "<set name=\"%s\">\n" % set_name

            for character in self.get_characters(set_name):
                s += "  <character>\n"

                utf8 = character.get_utf8()
                if utf8:
                    s += "    <utf8>%s</utf8>\n" % utf8

                for line in character.get_writing().to_xml().split("\n"):
                    s += "    %s\n" % line

                s += "  </character>\n"

            s += "</set>\n"

        s += "</character-collection>\n"

        return s

    # XML processing...

    def _start_element(self, name, attrs):
        self._tag = name

        if self._first_tag:
            self._first_tag = False
            if self._tag != "character-collection":
                raise ValueError, \
                      "The very first tag should be <character-collection>"

        if self._tag == "set":
            if not attrs.has_key("name"):
                raise ValueError, "<set> should have a name attribute"

            self._curr_set_name = attrs["name"].encode("UTF-8")
            self.add_set(self._curr_set_name)

        if self._tag == "character":
            self._curr_char = Character()
            self._curr_writing = self._curr_char.get_writing()
            self._curr_width = None
            self._curr_height = None
            self._curr_utf8 = None

        if self._tag == "stroke":
            self._curr_stroke = Stroke()

        elif self._tag == "point":
            point = Point()

            for key in ("x", "y", "pressure", "xtilt", "ytilt", "timestamp"):
                if attrs.has_key(key):
                    value = attrs[key].encode("UTF-8")
                    if key in ("pressure", "xtilt", "ytilt"):
                        value = float(value)
                    else:
                        value = int(float(value))
                else:
                    value = None

                setattr(point, key, value)

            self._curr_stroke.append_point(point)

    def _end_element(self, name):
        if name == "character-collection":
            for s in ["_tag", "_curr_char", "_curr_writing", "_curr_width",
                      "_curr_height", "_curr_utf8", "_curr_stroke",
                      "_curr_chars", "_curr_set_name"]:
                if s in self.__dict__:
                    del self.__dict__[s]

        if name == "character":
            if self._curr_utf8:
                self._curr_char.set_utf8(self._curr_utf8)
            if self._curr_width:
                self._curr_writing.set_width(self._curr_width)
            if self._curr_height:
                self._curr_writing.set_height(self._curr_height)
            self.append_character(self._curr_set_name, self._curr_char)

        if name == "stroke":
            if len(self._curr_stroke) > 0:
                self._curr_writing.append_stroke(self._curr_stroke)
            self._stroke = None

        self._tag = None

    def _char_data(self, data):
        if self._tag == "utf8":
            self._curr_utf8 = data.encode("UTF-8")
        if self._tag == "width":
            self._curr_width = int(data)
        elif self._tag == "height":
            self._curr_height = int(data)

########NEW FILE########
__FILENAME__ = chardict
# -*- coding: utf-8 -*-

# Copyright (C) 2010 The Tegaki project contributors
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

# Contributors to this file:
# - Mathieu Blondel

import cStringIO
import gzip as gzipm
try:
    import bz2 as bz2m
except ImportError:
    pass

from tegaki.character import _IOBase
from tegaki.dag import Node

class StrokeNode(Node):
    def __init__(self, *args, **kw):
        Node.__init__(self, *args, **kw)
        self.char_label = None

    def __repr__(self):
        value = self.get_value_string()
        if value is None:
            return "Stroke()"
        elif self.char_label is not None:
            return "Stroke(%s, %s)" % (value, self.char_label)
        else:
            return "Stroke(%s)" % value

    def __str__(self):
        value = self.get_value_string()
        if value is None:
            return ""
        elif self.char_label is not None:
            return "%s (%s)" % (value, self.char_label)
        else:
            return value

class CharacterStrokeDictionary(dict, _IOBase):
    """
    A dictionary used to map characters to their stroke sequences.
    This class supports strokes only to keep things simple.
    """

    def __init__(self, path=None):
        _IOBase.__init__(self, path)

    def get_characters(self):
        return self.keys()

    def get_strokes(self, char):
        if isinstance(char, str): char = unicode(char, "utf-8")
        return self[char]

    def set_strokes(self, char, strokes):
        if isinstance(char, str): char = unicode(char, "utf-8")

        for stroke_list in strokes:
            if not isinstance(stroke_list, list):
                raise ValueError

        self[char] = strokes

    def _parse_str(self, string):
        string = unicode(string, "utf-8")

        for line in string.strip().split("\n"):
            try:
                char, strokes = line.split("\t")
                strokes = strokes.strip()
                if len(strokes) == 0: continue
                strokes = strokes.split(" ")
                if not char in self: self[char] = []
                self[char].append(strokes)
            except ValueError:
                pass

    def _parse_file(self, file):
        self._parse_str(file.read())


    def to_str(self):
        s = ""
        for char, strokes in self.items():
            for stroke_list in strokes:
                s += "%s\t%s\n" % (char.encode("utf8"),
                                 " ".join(stroke_list).encode("utf8"))
        return s

    def to_dag(self):
        root = StrokeNode()

        for char in self.get_characters():
            utf8 = char.encode("utf8")
            node = root

            for stroke_list in self.get_strokes(char):
                for i, stroke_label in enumerate(stroke_list):
                    stroke_label = stroke_label.encode("utf8")
                    if not node.has_child_node_value(stroke_label):
                        node.set_child_node(StrokeNode(stroke_label))

                    # we reached the last stroke of the character
                    # so we assign the utf8 value of the character to it
                    if i == len(stroke_list)-1:
                        node.get_child_node(stroke_label).char_label = utf8

                    node = node.get_child_node(stroke_label)

        root.update_depths()

        return root

if __name__ == "__main__":
    import os
    import sys
    import pickle

#     if not os.path.exists("dag.pp"):
#         chardict = CharacterStrokeDictionary(sys.argv[1])
#         pickle.dump(chardict.to_dag(), file("dag.pp", "w"), pickle.HIGHEST_PROTOCOL)
#     else:
#         chardict = pickle.load(file("dag.pp"))

    chardict = CharacterStrokeDictionary(sys.argv[1])
    print chardict.to_dag().tree()

########NEW FILE########
__FILENAME__ = dag
# -*- coding: utf-8 -*-

# Copyright (C) 2010 The Tegaki project contributors
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

# Contributors to this file:
# - Mathieu Blondel

"""
Directed Acyclic Graph
"""

from dictutils import *

class Node(object):
    """
    A node can have several children and several parents.
    However, children can't be the parent of their parents (no cycle).
    """
    def __init__(self, value=None, parents={}):
        self._child_nodes = SortedDict()
        self._value = value
        self._parent_nodes = SortedDict(parents)
        self._depth = 0

    # value

    def get_value(self):
        return self._value

    def set_value(self, value):
        self._value = value

    def get_value_string(self):
        return self._value

    def __repr__(self):
        value = self.get_value_string()
        if value is None:
            return "Node()"
        else:
            return "Node(%s)" % value

    def __str__(self):
        return self.__repr__()

    def __hash__(self):
        return hash(self._value)

    # children

    def get_n_child_nodes(self):
        return len(self._child_nodes)

    def is_leaf_node(self):
        return self.get_n_child_nodes() == 0

    def get_child_nodes(self):
        return self._child_nodes.values()

    def get_child_node(self, value):
        return self._child_nodes[value]

    def has_child_node(self, node):
        return self.has_child_node_value(node.get_value())

    def has_child_node_value(self, value):
        return value in self._child_nodes

    def set_child_node(self, node):
        node.set_parent_node(self)
        self._child_nodes[node.get_value()] = node

    def set_child_nodes(self, nodelist):
        self._child_nodes = SortedDict()
        for node in nodelist:
            self.set_child_node(node)

    # parent

    def has_parent_node(self, parent):
        return parent.get_value() in self._parent_nodes

    def has_ancestor_node(self, parent):
        for node, depth in parent.depth_first_search():
            if node == self:
                return True
        return False

    def get_parent_nodes(self):
        return self._parent_nodes.values()

    def get_parent_node(self, value):
        return self._parent_nodes[value]

    def set_parent_node(self, node):
        self._parent_nodes[node.get_value()] = node

    def set_parent_nodes(self, nodelist):
        self._parent_nodes = SortedDict()
        for node in nodelist:
            self.set_parent_node(node)

    def get_generative_sequence(self):
        """
        One sequence of nodes that led to this node.
        """
        seq = []
        node = self

        while len(node.get_parent_nodes()) > 0:
            seq.insert(0, node)
            node = node.get_parent_nodes()[0]

        seq.insert(0, node)

        return seq

    # depth

    def get_depth(self):
        return self._depth

    def set_depth(self, depth):
        self._depth = depth

    def update_depths(self):
        for node, depth in self.depth_first_search():
            node.set_depth(depth)

    def get_max_depth(self):
        return max(depth for node, depth in self.depth_first_search())

    def get_n_nodes(self):
        return len(dict((node,1) for node, dep in self.depth_first_search()))

    # search

#     def depth_first_search(self):
#         yield self, 0 # root
#         for child in self.get_child_nodes():
#             for node, depth in child.depth_first_search():
#                 stop = (yield node, depth+1)
#                 if stop is not None:
#                     yield None
#                     break

    def depth_first_search(self):
        it = self.depth_first_search_args()
        for node, depth, visited, args in it:
            yield node, depth
            it.send(((),True))

    def depth_first_search_unique(self):
        d = {}
        for node, depth in self.depth_first_search():
            if not node in d:
                d[node] = 1
                yield node, depth

    def depth_first_search_args(self, *args):
        stack = [(self,0,args)]
        d = {}

        def _add_children(node):
            for child in node.get_child_nodes():
                for node_, depth in child.depth_first_search():
                    d[node_] = 1

        while len(stack) > 0:
            node,depth,args = stack.pop()
            d[node] = 1
            args, continue_ = (yield node, depth, len(d), args)
            yield None

            if continue_:
                stack += [(n,depth+1,args) for n in reversed(node.get_child_nodes())
                                           if not n in d]
            else:
                _add_children(node)

#     def breadth_first_search(self):
#         yield self, 0 # root
#         last = self
#
#         for node, depth in self.breadth_first_search():
#             for child in node.get_child_nodes():
#
#                 yield child, depth+1
#                 last = child
#
#             if last == node:
#                 raise StopIteration

    # iterative version
    def breadth_first_search(self):
        yield self, 0 # root
        stack = [self]

        while len(stack) > 0:
            node = stack.pop()

            for i, child in enumerate(node.get_child_nodes()):
                yield child, 0
                stack.insert(0, child)

    @classmethod
    def child_nodes_all(cls, nodes):
        children = []
        for node in nodes:
            children += node.get_child_nodes()
        return children


    def tree(self):
        """
        Returns a tree representation in text format.
        """
        s = ""

        for node, depth in self.depth_first_search():
            s += ("  " * depth) + str(node) + "\n"

        return s

if __name__ == "__main__":
    treestring = \
"""
          R
       /  |  \
      1   2  3
    / |   |  \
    4 5   6  9
         / \
        7  8
"""
    node7 = Node(7)
    node8 = Node(8)
    node6 = Node(6)
    node6.set_child_nodes([node7, node8])

    node4 = Node(4)
    node5 = Node(5)
    node1 = Node(1)
    node1.set_child_nodes([node4, node5])

    node2 = Node(2)
    node2.set_child_nodes([node6])

    node3 = Node(3)
    node9 = Node(9)
    node3.set_child_nodes([node9])

    root = Node()
    root.set_child_nodes([node1, node2, node3])

    def print_and_assert(prefix, got, expected):
        print prefix
        try:
            assert(got == expected)
            print got
        except AssertionError:
            print "got: ", got
            print "but expected: ", expected

    print "tree:\n", root.tree()

    print_and_assert("depth-first",
        [(n.get_value(), d) for n,d in list(root.depth_first_search())],
        [(None, 0), (1, 1), (4, 2), (5, 2), (2, 1), (6, 2), (7, 3), (8, 3), (3,
            1), (9, 2)])

    print_and_assert("breadth-first",
        [n.get_value() for n,d in list(root.breadth_first_search())],
        [None, 1, 2, 3, 4, 5, 6, 9, 7, 8])

    depth1_nodes = Node.child_nodes_all([root])
    print "child nodes of root: ", depth1_nodes

    print "parent of parent of 8: ", node8.get_parent_nodes()[0].get_parent_nodes()[0]
    print "generative sequence of 8: ", node8.get_generative_sequence()

    assert(node8.get_depth() == 0)
    assert(node6.get_depth() == 0)
    assert(node2.get_depth() == 0)
    assert(root.get_depth() == 0)

    root.update_depths()

    assert(node8.get_depth() == 3)
    assert(node6.get_depth() == 2)
    assert(node2.get_depth() == 1)
    assert(root.get_depth() == 0)

    print "depth-first search with args"
    it = root.depth_first_search_args(0)
    for node, depth, visited, args in it:
        print node, depth, visited, args
        it.send(((args[0]+1,),True))

    print "depth-first search unique"
    it = root.depth_first_search_unique()
    for node, depth in it:
        print node, depth

########NEW FILE########
__FILENAME__ = characterdb
#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Exports a stroke table from characterdb.cjklib.org and prints a CSV list to
stdout.

Copyright (c) 2008, 2010, Christoph Burgmer

Released unter the MIT License.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

import urllib
import codecs
import sys
import re

QUERY_URL = ("http://characterdb.cjklib.org/wiki/Special:Ask/"
             "%(query)s/%(properties)s/format=csv/sep=,/headers=hide/"
             "limit=%(limit)d/offset=%(offset)d")
"""Basic query URL."""

MAX_ENTRIES = 500
"""Maximum entries per GET request."""

#class AppURLopener(urllib.FancyURLopener):
    #version="Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1)"

#urllib._urlopener = AppURLopener()

def strokeorder_entry_preparator(entryList):
    columns = ['glyph', 'strokeorder']
    entry_dict = dict(zip(columns, entryList))

    character, glyph_index = entry_dict['glyph'].split('/', 1)
    if 'strokeorder' in entry_dict:
        return [(character, ' '.join(entry_dict['strokeorder'].strip('"')))]
    else:
        return []

DATA_SETS = {
             'ja': ({'query': '[[Category:Glyph]] [[Locale::J]] [[StrokeOrderForms::!]] [[StrokeOrderForms::!~*span*]]',
                     'properties': ['StrokeOrderForms']},
                    strokeorder_entry_preparator),
             'zh_CN': ({'query': '[[Category:Glyph]] [[Locale::C]] [[StrokeOrderForms::!]] [[StrokeOrderForms::!~*span*]]',
                        'properties': ['StrokeOrderForms']},
                       strokeorder_entry_preparator),
             'zh_TW': ({'query': '[[Category:Glyph]] [[Locale::T]] [[StrokeOrderForms::!]] [[StrokeOrderForms::!~*span*]]',
                        'properties': ['StrokeOrderForms']},
                       strokeorder_entry_preparator),
            }
"""Defined download sets."""

def get_data_set_iterator(name):
    try:
        parameter, preparator_func = DATA_SETS[name]
    except KeyError:
        raise ValueError("Unknown data set %r" % name)

    parameter = parameter.copy()
    if 'properties' in parameter:
        parameter['properties'] = '/'.join(('?' + prop) for prop
                                           in parameter['properties'])

    codec_reader = codecs.getreader('UTF-8')
    run = 0
    while True:
        query_dict = {'offset': run * MAX_ENTRIES, 'limit': MAX_ENTRIES}
        query_dict.update(parameter)

        query = QUERY_URL % query_dict
        query = urllib.quote(query, safe='/:=').replace('%', '-')
        f = codec_reader(urllib.urlopen(query))

        line_count = 0
        line = f.readline()
        while line:
            line = line.rstrip('\n')
            entry = re.findall(r'"[^"]+"|[^,]+', line)
            if preparator_func:
                for e in preparator_func(entry):
                    yield e
            else:
                yield entry

            line_count += 1
            line = f.readline()

        f.close()
        if line_count < MAX_ENTRIES:
            break
        run += 1


def main():
    if len(sys.argv) != 2:
        print """usage: python characterdb.py LANG
Exports a list of stroke orders from characterdb.cjklib.org and prints a
CSV list to stdout.

Available languages:"""
        print "\n".join(('  ' + name) for name in DATA_SETS.keys())
        sys.exit(1)

    for a in get_data_set_iterator(sys.argv[1]):
        print '\t'.join(cell for cell in a).encode('utf8')


if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = kanjivg
# -*- coding: utf-8 -*-
#
#  Copyright (C) 2009  Alexandre Courbot
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.

import xml.sax.handler

class BasicHandler(xml.sax.handler.ContentHandler):
	def __init__(self):
		xml.sax.handler.ContentHandler.__init__(self)
		self.elementsTree = []
	
	def currentElement(self):
		return str(self.elementsTree[-1])
		
	def startElement(self, qName, atts):
		self.elementsTree.append(str(qName))
		attrName = "handle_start_" + str(qName)
		if hasattr(self, attrName):
			rfunc = getattr(self, attrName)
			rfunc(atts)
		self.characters = ""
		return True
	
	def endElement(self, qName):
		attrName = "handle_data_" + qName
		if hasattr(self, attrName):
			rfunc = getattr(self, attrName)
			rfunc(self.characters)
		attrName = "handle_end_" + str(qName)
		if hasattr(self, attrName):
			rfunc = getattr(self, attrName)
			rfunc()
		self.elementsTree.pop()
		return True
	
	def characters(self, string):
		self.characters += string
		return True

# Sample licence header
licenseString = """Copyright (C) 2009 Ulrich Apel.
This work is distributed under the conditions of the Creative Commons 
Attribution-Noncommercial-Share Alike 3.0 Licence. This means you are free:
* to Share - to copy, distribute and transmit the work
* to Remix - to adapt the work

Under the following conditions:
* Attribution. You must attribute the work by stating your use of KanjiVG in
  your own copyright header and linking to KanjiVG's website
  (http://kanjivg.tagaini.net)
* Noncommercial. You may not use this work for commercial purposes.
* Share Alike. If you alter, transform, or build upon this work, you may
  distribute the resulting work only under the same or similar license to this
  one.

See http://creativecommons.org/licenses/by-nc-sa/3.0/ for more details."""

class Kanji:
	"""Describes a kanji. The root stroke group is accessible from the root member."""
	def __init__(self, id):
		self.id = id
		self.midashi = None
		self.root = None

	def toXML(self, out, indent = 0):
		out.write("\t" * indent + '<kanji midashi="%s" id="%s">\n' % (self.midashi, self.id))
		self.root.toXML(out, 0)

	def simplify(self):
		self.root.simplify()

	def getStrokes(self):
		return self.root.getStrokes()
		

class StrokeGr:
	"""Describes a stroke group belonging to a kanji. Sub-stroke groups or strokes are available in the childs member. They can either be of class StrokeGr or Stroke so their type should be checked."""
	def __init__(self, parent):
		self.parent = parent
		if parent: parent.childs.append(self)
		# Element of strokegr, or midashi for kanji
		self.element = None
		# A more common, safer element this one derives of
		self.original = None
		self.part = None
		self.variant = False
		self.partial = False
		self.tradForm = False
		self.radicalForm = False
		self.position = None
		self.radical = None
		self.phon = None
		
		self.childs = []

	def toXML(self, out, indent = 0):
		eltString = ""
		if self.element: eltString = ' element="%s"' % (self.element)
		variantString = ""
		if self.variant: variantString = ' variant="true"'
		partialString = ""
		if self.partial: partialString = ' partial="true"'
		origString = ""
		if self.original: origString = ' original="%s"' % (self.original)
		partString = ""
		if self.part: partString = ' part="%d"' % (self.part)
		tradFormString = ""
		if self.tradForm: tradFormString = ' tradForm="true"'
		radicalFormString = ""
		if self.radicalForm: radicalFormString = ' radicalForm="true"'
		posString = ""
		if self.position: posString = ' position="%s"' % (self.position)
		radString = ""
		if self.radical: radString = ' radical="%s"' % (self.radical)
		phonString = ""
		if self.phon: phonString = ' phon="%s"' % (self.phon)
		out.write("\t" * indent + '<strokegr%s%s%s%s%s%s%s%s%s%s>\n' % (eltString, partString, variantString, origString, partialString, tradFormString, radicalFormString, posString, radString, phonString))

		for child in self.childs: child.toXML(out, indent + 1)

		out.write("\t" * indent + '</strokegr>\n')

		if not self.parent: out.write("\t" * indent + '</kanji>\n')

	def simplify(self):
		for child in self.childs: 
			if isinstance(child, StrokeGr): child.simplify()
		if len(self.childs) == 1 and isinstance(self.childs[0], StrokeGr):
			# Check if there is no conflict
			if child.element and self.element and child.element != self.element: return
			if child.original and self.original and child.original != self.original: return
			# Parts cannot be merged
			if child.part and self.part: return
			if child.variant and self.variant and child.variant != self.variant: return
			if child.partial and self.partial and child.partial != self.partial: return
			if child.tradForm and self.tradForm and child.tradForm != self.tradForm: return
			if child.radicalForm and self.radicalForm and child.radicalForm != self.radicalForm: return
			# We want to preserve inner identical positions - we may have something at the top
			# of another top element, for instance.
			if child.position and self.position: return
			if child.radical and self.radical and child.radical != self.radical: return
			if child.phon and self.phon and child.phon != self.phon: return

			# Ok, let's merge!
			child = self.childs[0]
			self.childs = child.childs
			if child.element: self.element = child.element
			if child.original: self.original = child.original
			if child.part: self.part = child.part
			if child.variant: self.variant = child.variant
			if child.partial: self.partial = child.partial
			if child.tradForm: self.tradForm = child.tradForm
			if child.radicalForm: self.radicalForm = child.radicalForm
			if child.position: self.position = child.position
			if child.radical: self.radical = child.radical
			if child.phon: self.phon = child.phon

	def getStrokes(self):
		ret = []
		for child in self.childs: 
			if isinstance(child, StrokeGr): ret += child.getStrokes()
			else: ret.append(child)
		return ret
		

class Stroke:
	"""A single stroke, containing its type and (optionally) its SVG data."""
	def __init__(self):
		self.stype = None
		self.svg = None

	def toXML(self, out, indent = 0):
		if not self.svg: out.write("\t" * indent + '<stroke type="%s"/>\n' % (self.stype))
		else: out.write("\t" * indent + '<stroke type="%s" path="%s"/>\n' % (self.stype, self.svg))

class KanjisHandler(BasicHandler):
	"""XML handler for parsing kanji files. It can handle single-kanji files or aggregation files. After parsing, the kanjis are accessible through the kanjis member, indexed by their svg file name."""
	def __init__(self):
		BasicHandler.__init__(self)
		self.kanjis = {}
		self.currentKanji = None
		self.groups = []

	def handle_start_kanji(self, attrs):
		id = str(attrs["id"])
		self.currentKanji = Kanji(id)
		self.currentKanji.midashi = unicode(attrs["midashi"])
		self.kanjis[id] = self.currentKanji

	def handle_end_kanji(self):
		if len(self.groups) != 0:
			print "WARNING: stroke groups remaining after reading kanji!"
		self.currentKanji = None
		self.groups = []

	def handle_start_strokegr(self, attrs):
		if len(self.groups) == 0: parent = None
		else: parent = self.groups[-1]
		group = StrokeGr(parent)

		# Now parse group attributes
		if attrs.has_key("element"): group.element = unicode(attrs["element"])
		if attrs.has_key("variant"): group.variant = str(attrs["variant"])
		if attrs.has_key("partial"): group.partial = str(attrs["partial"])
		if attrs.has_key("original"): group.original = unicode(attrs["original"])
		if attrs.has_key("part"): group.part = int(attrs["part"])
		if attrs.has_key("tradForm") and str(attrs["tradForm"]) == "true": group.tradForm = True
		if attrs.has_key("radicalForm") and str(attrs["radicalForm"]) == "true": group.radicalForm = True
		if attrs.has_key("position"): group.position = unicode(attrs["position"])
		if attrs.has_key("radical"): group.radical = unicode(attrs["radical"])
		if attrs.has_key("phon"): group.phon = unicode(attrs["phon"])

		self.groups.append(group)

	def handle_end_strokegr(self):
		group = self.groups.pop()
		if len(self.groups) == 0:
			if self.currentKanji.root:
				print "WARNING: overwriting root of kanji!"
			self.currentKanji.root = group

	def handle_start_stroke(self, attrs):
		stroke = Stroke()
		stroke.stype = unicode(attrs["type"])
		if attrs.has_key("path"): stroke.svg = unicode(attrs["path"])
		self.groups[-1].childs.append(stroke)

########NEW FILE########
__FILENAME__ = kanjivg2strokes
#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import codecs
import xml.sax
from kanjivg import *
import sys

# Read all kanjis
handler = KanjisHandler()
xml.sax.parse(sys.argv[1], handler)
kanjis = handler.kanjis.values()

kanjis.sort(lambda x,y: cmp(x.id, y.id))

sdict_v = {}
sdict = {}
kdict_v = {}
kdict = {}

for kanji in kanjis:
    strokes_v = [s.stype for s in kanji.getStrokes()]

    if "None" in strokes_v: continue

    # strokes without stroke variants
    strokes = [s[0] for s in strokes_v]

    # convert to byte-strings
    strokes_v = [s.encode("utf8") for s in strokes_v]
    strokes = [s.encode("utf8") for s in strokes]

    utf8 = kanji.midashi.encode("utf8")

    kdict_v[utf8] = strokes_v
    kdict[utf8] = strokes
    
    for _strokes,d in ((strokes,sdict),(strokes_v,sdict_v)):
       for s in _strokes:
           d[s] = d.get(s, 0) + 1
 


print >> sys.stderr, "n strokes", len(sdict_v)
print >> sys.stderr, "n strokes (without variants)", len(sdict)
print >> sys.stderr, "n characters", len(kdict)

for utf8 in sorted(kdict.keys()):
    print "%s\t%s" % (utf8, " ".join(kdict[utf8]))


########NEW FILE########
__FILENAME__ = dictutils
# -*- coding: utf-8 -*-
# Copyright (c) 2005, the Lawrence Journal-World
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#    1. Redistributions of source code must retain the above copyright notice, 
#       this list of conditions and the following disclaimer.
#    
#    2. Redistributions in binary form must reproduce the above copyright 
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#
#    3. Neither the name of Django nor the names of its contributors may be used
#       to endorse or promote products derived from this software without
#       specific prior written permission.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

class SortedDict(dict):
    """
    A dictionary that keeps its keys in the order in which they're inserted.
    """
    def __new__(cls, *args, **kwargs):
        instance = super(SortedDict, cls).__new__(cls, *args, **kwargs)
        instance.keyOrder = []
        return instance

    def __init__(self, data=None):
        if data is None:
            data = {}
        super(SortedDict, self).__init__(data)
        if isinstance(data, dict):
            self.keyOrder = data.keys()
        else:
            self.keyOrder = []
            for key, value in data:
                if key not in self.keyOrder:
                    self.keyOrder.append(key)

    def __deepcopy__(self, memo):
        from copy import deepcopy
        return self.__class__([(key, deepcopy(value, memo))
                               for key, value in self.iteritems()])

    def __setitem__(self, key, value):
        super(SortedDict, self).__setitem__(key, value)
        if key not in self.keyOrder:
            self.keyOrder.append(key)

    def __delitem__(self, key):
        super(SortedDict, self).__delitem__(key)
        self.keyOrder.remove(key)

    def __iter__(self):
        for k in self.keyOrder:
            yield k

    def pop(self, k, *args):
        result = super(SortedDict, self).pop(k, *args)
        try:
            self.keyOrder.remove(k)
        except ValueError:
            # Key wasn't in the dictionary in the first place. No problem.
            pass
        return result

    def popitem(self):
        result = super(SortedDict, self).popitem()
        self.keyOrder.remove(result[0])
        return result

    def items(self):
        return zip(self.keyOrder, self.values())

    def iteritems(self):
        for key in self.keyOrder:
            yield key, super(SortedDict, self).__getitem__(key)

    def keys(self):
        return self.keyOrder[:]

    def iterkeys(self):
        return iter(self.keyOrder)

    def values(self):
        return map(super(SortedDict, self).__getitem__, self.keyOrder)

    def itervalues(self):
        for key in self.keyOrder:
            yield super(SortedDict, self).__getitem__(key)

    def update(self, dict_):
        for k, v in dict_.items():
            self.__setitem__(k, v)

    def setdefault(self, key, default):
        if key not in self.keyOrder:
            self.keyOrder.append(key)
        return super(SortedDict, self).setdefault(key, default)

    def value_for_index(self, index):
        """Returns the value of the item at the given zero-based index."""
        return self[self.keyOrder[index]]

    def insert(self, index, key, value):
        """Inserts the key, value pair before the item with the given index."""
        if key in self.keyOrder:
            n = self.keyOrder.index(key)
            del self.keyOrder[n]
            if n < index:
                index -= 1
        self.keyOrder.insert(index, key)
        super(SortedDict, self).__setitem__(key, value)

    def copy(self):
        """Returns a copy of this object."""
        # This way of initializing the copy means it works for subclasses, too.
        obj = self.__class__(self)
        obj.keyOrder = self.keyOrder[:]
        return obj

    def __repr__(self):
        """
        Replaces the normal dict.__repr__ with a version that returns the keys
        in their sorted order.
        """
        return '{%s}' % ', '.join(['%r: %r' % (k, v) for k, v in self.items()])

    def clear(self):
        super(SortedDict, self).clear()
        self.keyOrder = []
########NEW FILE########
__FILENAME__ = engine
# -*- coding: utf-8 -*-

# Copyright (C) 2009 The Tegaki project contributors
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import os
import platform

from tegaki.dictutils import SortedDict

class Engine(object):
    """
    Base class for Recognizer and Trainer.
    """

    @classmethod
    def _get_search_path(cls, what):
        """
        Return a list of search path.  

        @typ what: str
        @param what: "models" or "engines"
        """
        libdir = os.path.dirname(os.path.abspath(__file__))

        try:
            # UNIX
            homedir = os.environ['HOME']
            homeengines = os.path.join(homedir, ".tegaki", what)
        except KeyError:
            # Windows
            homedir = os.environ['USERPROFILE']
            homeengines = os.path.join(homedir, "tegaki", what)

        search_path = [# For Unix
                       "/usr/local/share/tegaki/%s/" % what,
                       "/usr/share/tegaki/%s/" % what,
                       # for Maemo
                       "/media/mmc1/tegaki/%s/" % what,
                       "/media/mmc2/tegaki/%s/" % what,
                       # personal directory
                       homeengines,
                       # lib dir
                       os.path.join(libdir, what)]

        # For Windows
        try:
            search_path += [os.path.join(os.environ["APPDATA"], "tegaki",
                                         what),
                            r"C:\Python25\share\tegaki\%s" % what,
                            r"C:\Python26\share\tegaki\%s" % what]
        except KeyError:
            pass

        # For OSX
        if platform.system() == "Darwin":
            search_path += [os.path.join(homedir, "Library", 
                                         "Application Support", "tegaki", what),
                            os.path.join("/Library", "Application Support",
                                         "tegaki", what)]

        try:
            env = {"engines": "TEGAKI_ENGINE_PATH", 
                   "models" : "TEGAKI_MODEL_PATH"}[what]

            if env in os.environ and \
               os.environ[env].strip() != "":
                search_path += os.environ[env].strip().split(os.path.pathsep)

        except KeyError:
            pass

        return search_path

    @classmethod
    def read_meta_file(cls, meta_file):
        """
        Read a .meta file.

        @type meta_file: str
        @param meta_file: meta file file to read

        @rtype: dict
        """
        f = open(meta_file)
        ret = SortedDict()
        for line in f.readlines():
            try:
                key, value = [s.strip() for s in line.strip().split("=")]
                ret[key] = value
            except ValueError:
                continue
        f.close()
        return ret

########NEW FILE########
__FILENAME__ = tegakizinnia
# -*- coding: utf-8 -*-

# Copyright (C) 2008-2009 The Tegaki project contributors
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

# Contributors to this file:
# - Mathieu Blondel

import os

from tegaki.recognizer import Results, Recognizer, RecognizerError
from tegaki.trainer import Trainer, TrainerError

try:
    import zinnia    

    class ZinniaRecognizer(Recognizer):

        RECOGNIZER_NAME = "zinnia"

        def __init__(self):
            Recognizer.__init__(self)
            self._recognizer = zinnia.Recognizer()

        def open(self, path):
            ret = self._recognizer.open(path) 
            if not ret: raise RecognizerError, "Could not open!"

        def _recognize(self, writing, n=10):
            s = zinnia.Character()

            s.set_width(writing.get_width())
            s.set_height(writing.get_height())

            strokes = writing.get_strokes()
            for i in range(len(strokes)):
                stroke = strokes[i]

                for x, y in stroke:
                    s.add(i, x, y)

            result = self._recognizer.classify(s, n+1)
            size = result.size()

            return Results([(result.value(i), result.score(i)) \
                               for i in range(0, (size - 1))])

    RECOGNIZER_CLASS = ZinniaRecognizer

    class ZinniaTrainer(Trainer):

        TRAINER_NAME = "zinnia"

        def __init__(self):
            Trainer.__init__(self)

        def train(self, charcol, meta, path=None):
            self._check_meta(meta)

            trainer = zinnia.Trainer()
            zinnia_char = zinnia.Character()

            for set_name in charcol.get_set_list():
                for character in charcol.get_characters(set_name):      
                    if (not zinnia_char.parse(character.to_sexp())):
                        raise TrainerError, zinnia_char.what()
                    else:
                        trainer.add(zinnia_char)

            if not path:
                if "path" in meta:
                    path = meta["path"]
                else:
                    path = os.path.join(os.environ['HOME'], ".tegaki", "models",
                                        "zinnia", meta["name"] + ".model")
            else:
                path = os.path.abspath(path)

            if not os.path.exists(os.path.dirname(path)):
                os.makedirs(os.path.dirname(path))

            meta_file = path.replace(".model", ".meta")
            if not meta_file.endswith(".meta"): meta_file += ".meta"
            
            trainer.train(path)
            self._write_meta_file(meta, meta_file)

    TRAINER_CLASS = ZinniaTrainer

except ImportError:
    pass


########NEW FILE########
__FILENAME__ = mathutils
# -*- coding: utf-8 -*-

# Copyright (C) 2008 The Tegaki project contributors
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

# Contributors to this file:
# - Mathieu Blondel

from math import sqrt, hypot, atan2, pi

def euclidean_distance(v1, v2):
    assert(len(v1) == len(v2))

    return sqrt(sum([(v2[i] - v1[i]) ** 2 for i in range(len(v1))]))
  
def cartesian_to_polar(x, y):
    """
    Cartesian to polar coordinates conversion.
    r is the distance to the point.
    teta is the angle to the point between 0 and 2 pi.
    """
    r = hypot(x, y)
    teta = atan2(y, x) + pi
    return (r, teta)
########NEW FILE########
__FILENAME__ = recognizer
# -*- coding: utf-8 -*-

# Copyright (C) 2008-2009 The Tegaki project contributors
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

# Contributors to this file:
# - Mathieu Blondel

import glob
import os
import imp

from tegaki.engine import Engine
from tegaki.dictutils import SortedDict

SMALL_HIRAGANA = {
"あ":"ぁ","い":"ぃ","う":"ぅ","え":"ぇ","お":"ぉ","つ":"っ",
"や":"ゃ","ゆ":"ゅ","よ":"ょ","わ":"ゎ"
}

SMALL_KATAKANA = {
"ア":"ァ","イ":"ィ","ウ":"ゥ","エ":"ェ","オ":"ォ","ツ":"ッ",
"ヤ":"ャ","ユ":"ュ","ヨ":"ョ","ワ":"ヮ"
}

class Results(list):
    """
    Object containing recognition results.
    """

    def get_candidates(self):
        return [c[0] for c in self]

    def get_scores(self):
        return [c[1] for c in self]

    def to_small_kana(self):
        cand = [SMALL_HIRAGANA[c] if c in SMALL_HIRAGANA else c \
                    for c in self.get_candidates()]
        cand = [SMALL_KATAKANA[c] if c in SMALL_KATAKANA else c \
                    for c in cand]
        return Results(zip(cand, self.get_scores()))

class RecognizerError(Exception):
    """
    Raised when something went wrong in a Recognizer.
    """
    pass

class Recognizer(Engine):
    """
    Base Recognizer class.

    A recognizer can recognize handwritten characters based on a model.

    The L{open} method should be used to load a model from an
    absolute path on the disk.

    The L{set_model} method should be used to load a model from its name.
    Two models can't have the same name within one recognizer.
    However, two models can be named the same if they belong to two different
    recognizers.

    Recognizers usually have a corresponding L{Trainer}.
    """

    def __init__(self):
        self._model = None
        self._lang = None
   
    @classmethod
    def get_available_recognizers(cls):
        """
        Return recognizers installed on the system.

        @rtype: dict
        @return: a dict where keys are recognizer names and values \
                 are recognizer classes
        """
        if not "available_recognizers" in cls.__dict__:
            cls._load_available_recognizers()
        return cls.available_recognizers

    @classmethod
    def _load_available_recognizers(cls):
        cls.available_recognizers  = SortedDict()

        for directory in cls._get_search_path("engines"):
            if not os.path.exists(directory):
                continue

            for f in glob.glob(os.path.join(directory, "*.py")):
                if f.endswith("__init__.py") or f.endswith("setup.py"):
                    continue

                module_name = os.path.basename(f).replace(".py", "")
                module_name += "recognizer"
                module = imp.load_source(module_name, f)

                try:
                    name = module.RECOGNIZER_CLASS.RECOGNIZER_NAME
                    cls.available_recognizers[name] = module.RECOGNIZER_CLASS
                except AttributeError:
                    pass       

    @staticmethod
    def get_all_available_models():
        """
        Return available models from all recognizers.

        @rtype: list
        @return: a list of tuples (recognizer_name, model_name, meta_dict)
        """
        all_models = []
        for r_name, klass in Recognizer.get_available_recognizers().items():
            for model_name, meta in klass.get_available_models().items():
                all_models.append([r_name, model_name, meta])
        return all_models

    @classmethod
    def get_available_models(cls):
        """
        Return available models for the current recognizer.

        @rtype; dict
        @return: a dict where keys are models names and values are meta dict
        """
        if "available_models" in cls.__dict__: 
            return cls.available_models
        else:
            name = cls.RECOGNIZER_NAME
            cls.available_models = cls._get_available_models(name)
            return cls.__dict__["available_models"]

    @classmethod
    def _get_available_models(cls, recognizer):
        available_models = SortedDict()

        for directory in cls._get_search_path("models"):
            directory = os.path.join(directory, recognizer)

            if not os.path.exists(directory):
                continue

            meta_files = glob.glob(os.path.join(directory, "*.meta"))

            for meta_file in meta_files:
                meta = Recognizer.read_meta_file(meta_file)

                if not meta.has_key("name") or \
                    not meta.has_key("shortname"):
                    continue

                model_file = meta_file.replace(".meta", ".model")
            
                if meta.has_key("path") and not os.path.exists(meta["path"]):
                    # skip model if specified path is incorrect
                    continue
                elif not meta.has_key("path") and os.path.exists(model_file):
                    # if path option is missing, assume the .model file
                    # is in the same directory
                    meta["path"] = model_file

                available_models[meta["name"]] = meta

        return available_models

    def open(self, path):
        """
        Open a model.

        @type path: str
        @param path: model path
        
        Raises RecognizerError if could not open.
        """
        raise NotImplementedError

    def set_options(self, options):
        """
        Process recognizer/model specific options.

        @type options: dict
        @param options: a dict where keys are option names and values are \
                        option values
        """
        pass

    def get_model(self):
        """
        Return the currently selected model.

        @rtype: str
        @return: name which identifies model uniquely on the system
        """
        return self._model

    def set_model(self, model_name):
        """
        Set the currently selected model.

        @type model_name: str
        @param model_name: name which identifies model uniquely on the system

        model_name must exist for that recognizer.
        """
        if not model_name in self.__class__.get_available_models():
            raise RecognizerError, "Model does not exist"

        self._model = model_name

        meta = self.__class__.get_available_models()[model_name]

        self.set_options(meta)

        if "language" in meta: self._lang = meta["language"]

        self.open(meta["path"])

    # To be implemented by child class
    def recognize(self, writing, n=10):
        """
        Recognizes handwriting.

        @type writing: L{Writing}
        @param writing: the handwriting to recognize

        @type n: int
        @param n: the number of candidates to return

        @rtype: list
        @return: a list of tuple (label, probability/distance)
        
        A model must be loaded with open or set_model() beforehand.
        """
        is_small = False
        if self._lang == "ja":
            is_small = writing.is_small()

        results = self._recognize(writing, n)

        if is_small:
            return results.to_small_kana()
        else:
            return results


if __name__ == "__main__":
    import sys
    from tegaki.character import Character

    recognizer = sys.argv[1] # name of recognizer
    model = sys.argv[2] # name of model file
    char = Character()
    char.read(sys.argv[3]) # path of .xml file
    writing = char.get_writing() 

    recognizers = Recognizer.get_available_recognizers()
    print "Available recognizers", recognizers

    if not recognizer in recognizers:
        raise Exception, "Not an available recognizer"

    recognizer_klass = recognizers[recognizer]
    recognizer = recognizer_klass()

    models = recognizer_klass.get_available_models()
    print "Available models", models

    if not model in models:
        raise Exception, "Not an available model"

    recognizer.set_model(model)

    print recognizer.recognize(writing)

########NEW FILE########
__FILENAME__ = trainer
# -*- coding: utf-8 -*-

# Copyright (C) 2008-2009 The Tegaki project contributors
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

# Contributors to this file:
# - Mathieu Blondel

import glob
import os
import imp
from cStringIO import StringIO

from tegaki.engine import Engine
from tegaki.dictutils import SortedDict

class TrainerError(Exception):
    """
    Raised when something went wrong in a Trainer.
    """
    pass

class Trainer(Engine):
    """
    Base Trainer class.

    A trainer can train models based on sample data annotated with labels.
    """

    def __init__(self):
        pass
   
    @classmethod
    def get_available_trainers(cls):
        """
        Return trainers installed on the system.

        @rtype: dict
        @return: a dict where keys are trainer names and values \
                 are trainer classes
        """
        if not "available_trainers" in cls.__dict__:
            cls._load_available_trainers()
        return cls.available_trainers

    @classmethod
    def _load_available_trainers(cls):
        cls.available_trainers  = SortedDict()

        for directory in cls._get_search_path("engines"):
            if not os.path.exists(directory):
                continue

            for f in glob.glob(os.path.join(directory, "*.py")):
                if f.endswith("__init__.py") or f.endswith("setup.py"):
                    continue

                module_name = os.path.basename(f).replace(".py", "")
                module_name += "trainer"
                module = imp.load_source(module_name, f)

                try:
                    name = module.TRAINER_CLASS.TRAINER_NAME
                    cls.available_trainers[name] = module.TRAINER_CLASS
                except AttributeError:
                    pass         

    def set_options(self, options):
        """
        Process trainer/model specific options.

        @type options: dict
        @param options: a dict where keys are option names and values are \
                        option values
        """
        pass

    # To be implemented by child class
    def train(self, character_collection, meta, path=None):
        """
        Train a model.

        @type character_collection: L{CharacterCollection}
        @param character_collection: collection containing training data

        @type meta: dict
        @param meta: meta dict obtained with L{Engine.read_meta_file}

        @type path: str
        @param path: path to the ouput model \
                     (if None, the personal directory is assumed)

        The meta dict needs the following keys:
            - name: full name (mandatory)
            - shortname: name with less than 3 characters (mandatory)
            - language: model language (optional)
        """
        raise NotImplementedError

    def _check_meta(self, meta):
        if not meta.has_key("name") or not meta.has_key("shortname"):
            raise TrainerError, "meta must contain a name and a shortname"

    def _write_meta_file(self, meta, meta_file):
        io = StringIO()
        for k,v in meta.items():
            io.write("%s = %s\n" % (k,v))

        if os.path.exists(meta_file):
            f = open(meta_file)
            contents = f.read() 
            f.close()
            # don't rewrite the file if same
            if io.getvalue() == contents:
                return

        f = open(meta_file, "w")
        f.write(io.getvalue())
        f.close()

########NEW FILE########
__FILENAME__ = minjson
##############################################################################
#
# Copyright (c) 2006 Zope Corporation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################

# minjson.py
# reads minimal javascript objects.
# str's objects and fixes the text to write javascript.

#UNICODE USAGE:  Minjson tries hard to accommodate naive usage in a 
#"Do what I mean" manner.  Real applications should handle unicode separately.
# The "right" way to use minjson in an application is to provide minjson a 
# python unicode string for reading and accept a unicode output from minjson's
# writing.  That way, the assumptions for unicode are yours and not minjson's.

# That said, the minjson code has some (optional) unicode handling that you 
# may look at as a model for the unicode handling your application may need.

# Thanks to Patrick Logan for starting the json-py project and making so many
# good test cases.

# Additional thanks to Balazs Ree for replacing the writing module.

# Jim Washington 6 Dec 2006.

# 2006-12-06 Thanks to Koen van de Sande, now handles the case where someone 
#            might want e.g., a literal "\n" in text not a new-line.
# 2005-12-30 writing now traverses the object tree instead of relying on 
#            str() or unicode()
# 2005-10-10 on reading, looks for \\uxxxx and replaces with u'\uxxxx'
# 2005-10-09 now tries hard to make all strings unicode when reading.
# 2005-10-07 got rid of eval() completely, makes object as found by the
#            tokenizer.
# 2005-09-06 imported parsing constants from tokenize; they changed a bit from
#            python2.3 to 2.4
# 2005-08-22 replaced the read sanity code
# 2005-08-21 Search for exploits on eval() yielded more default bad operators.
# 2005-08-18 Added optional code from Koen van de Sande to escape
#            outgoing unicode chars above 128


from re import compile, sub, search, DOTALL
from token import ENDMARKER, NAME, NUMBER, STRING, OP, ERRORTOKEN
from tokenize import tokenize, TokenError, NL

#Usually, utf-8 will work, set this to utf-16 if you dare.
emergencyEncoding = 'utf-8'

class ReadException(Exception):
    pass

class WriteException(Exception):
    pass

#################################
#      read JSON object         #
#################################

slashstarcomment = compile(r'/\*.*?\*/',DOTALL)
doubleslashcomment = compile(r'//.*\n')

unichrRE = compile(r"\\u[0-9a-fA-F]{4,4}")

def unichrReplace(match):
    return unichr(int(match.group()[2:],16))

escapeStrs = (('\n',r'\n'),('\b',r'\b'),
    ('\f',r'\f'),('\t',r'\t'),('\r',r'\r'), ('"',r'\"')
    )

class DictToken:
    __slots__=[]
    pass
class ListToken:
    __slots__=[]
    pass
class ColonToken:
    __slots__=[]
    pass
class CommaToken:
    __slots__=[]
    pass

class JSONReader(object):
    """raise SyntaxError if it is not JSON, and make the object available"""
    def __init__(self,data):
        self.stop = False
        #make an iterator of data so that next() works in tokenize.
        self._data = iter([data])
        self.lastOp = None
        self.objects = []
        self.tokenize()

    def tokenize(self):
        try:
            tokenize(self._data.next,self.readTokens)
        except TokenError:
            raise SyntaxError

    def resolveList(self):
        #check for empty list
        if isinstance(self.objects[-1],ListToken):
            self.objects[-1] = []
            return
        theList = []
        commaCount = 0
        try:
            item = self.objects.pop()
        except IndexError:
            raise SyntaxError
        while not isinstance(item,ListToken):
            if isinstance(item,CommaToken):
                commaCount += 1
            else:
                theList.append(item)
            try:
                item = self.objects.pop()
            except IndexError:
                raise SyntaxError
        if not commaCount == (len(theList) -1):
            raise SyntaxError
        theList.reverse()
        item = theList
        self.objects.append(item)

    def resolveDict(self):
        theList = []
        #check for empty dict
        if isinstance(self.objects[-1], DictToken):
            self.objects[-1] = {}
            return
        #not empty; must have at least three values
        try:
            #value (we're going backwards!)
            value = self.objects.pop()
        except IndexError:
            raise SyntaxError
        try:
            #colon
            colon = self.objects.pop()
            if not isinstance(colon, ColonToken):
                raise SyntaxError
        except IndexError:
            raise SyntaxError
        try:
            #key
            key = self.objects.pop()
            if not isinstance(key,basestring):
                raise SyntaxError
        except IndexError:

            raise SyntaxError
        #salt the while
        comma = value
        while not isinstance(comma,DictToken):
            # store the value
            theList.append((key,value))
            #do it again...
            try:
                #might be a comma
                comma = self.objects.pop()
            except IndexError:
                raise SyntaxError
            if isinstance(comma,CommaToken):
                #if it's a comma, get the values
                try:
                    value = self.objects.pop()
                except IndexError:
                    #print self.objects
                    raise SyntaxError
                try:
                    colon = self.objects.pop()
                    if not isinstance(colon, ColonToken):
                        raise SyntaxError
                except IndexError:
                    raise SyntaxError
                try:
                    key = self.objects.pop()
                    if not isinstance(key,basestring):
                        raise SyntaxError
                except IndexError:
                    raise SyntaxError
        theDict = {}
        for k in theList:
            theDict[k[0]] = k[1]
        self.objects.append(theDict)

    def readTokens(self,type, token, (srow, scol), (erow, ecol), line):
        # UPPERCASE consts from tokens.py or tokenize.py
        if type == OP:
            if token not in "[{}],:-":
                raise SyntaxError
            else:
                self.lastOp = token
            if token == '[':
                self.objects.append(ListToken())
            elif token == '{':
                self.objects.append(DictToken())
            elif token == ']':
                self.resolveList()
            elif token == '}':
                self.resolveDict()
            elif token == ':':
                self.objects.append(ColonToken())
            elif token == ',':
                self.objects.append(CommaToken())
        elif type == STRING:
            tok = token[1:-1]
            parts = tok.split("\\\\")
            for k in escapeStrs:
                if k[1] in tok:
                    parts = [part.replace(k[1],k[0]) for part in parts]
            self.objects.append("\\".join(parts))
        elif type == NUMBER:
            if self.lastOp == '-':
                factor = -1
            else:
                factor = 1
            try:
                self.objects.append(factor * int(token))
            except ValueError:
                self.objects.append(factor * float(token))
        elif type == NAME:
            try:
                self.objects.append({'true':True,
                    'false':False,'null':None}[token])
            except KeyError:
                raise SyntaxError
        elif type == ENDMARKER:
            pass
        elif type == NL:
            pass
        elif type == ERRORTOKEN:
            if ecol == len(line):
                #it's a char at the end of the line.  (mostly) harmless.
                pass
            else:
                raise SyntaxError
        else:
            raise SyntaxError
    def output(self):
        try:
            assert len(self.objects) == 1
        except AssertionError:
            raise SyntaxError
        return self.objects[0]

def safeRead(aString, encoding=None):
    """read the js, first sanitizing a bit and removing any c-style comments
    If the input is a unicode string, great.  That's preferred.  If the input 
    is a byte string, strings in the object will be produced as unicode anyway.
    """
    # get rid of trailing null. Konqueror appends this.
    CHR0 = chr(0)
    while aString.endswith(CHR0):
        aString = aString[:-1]
    # strip leading and trailing whitespace
    aString = aString.strip()
    # zap /* ... */ comments
    aString = slashstarcomment.sub('',aString)
    # zap // comments
    aString = doubleslashcomment.sub('',aString)
    # detect and handle \\u unicode characters. Note: This has the side effect
    # of converting the entire string to unicode. This is probably OK.
    unicodechars = unichrRE.search(aString)
    if unicodechars:
        aString = unichrRE.sub(unichrReplace, aString)
    #if it's already unicode, we won't try to decode it
    if isinstance(aString, unicode):
        s = aString
    else:
        if encoding:
            # note: no "try" here.  the encoding provided must work for the
            # incoming byte string.  UnicodeDecode error will be raised
            # in that case.  Often, it will be best not to provide the encoding
            # and allow the default
            s = unicode(aString, encoding)
            #print "decoded %s from %s" % (s,encoding)
        else:
            # let's try to decode to unicode in system default encoding
            try:
                s = unicode(aString)
                #import sys
                #print "decoded %s from %s" % (s,sys.getdefaultencoding())
            except UnicodeDecodeError:
                # last choice: handle as emergencyEncoding
                enc = emergencyEncoding
                s = unicode(aString, enc)
                #print "%s decoded from %s" % (s, enc)
    # parse and get the object.
    try:
        data = JSONReader(s).output()
    except SyntaxError:
        raise ReadException, 'Unacceptable JSON expression: %s' % aString
    return data

read = safeRead

#################################
#   write object as JSON        #
#################################

import re, codecs
from cStringIO import StringIO

### Codec error handler

def jsonreplace_handler(exc):
    '''Error handler for json

    If encoding fails, \\uxxxx must be emitted. This
    is similar to the "backshashreplace" handler, only
    that we never emit \\xnn since this is not legal
    according to the JSON syntax specs.
    '''
    if isinstance(exc, UnicodeEncodeError):
        part = exc.object[exc.start]
        # repr(part) will convert u'\unnnn' to u'u\\nnnn'
        return u'\\u%04x' % ord(part), exc.start+1
    else:
        raise exc

# register the error handler
codecs.register_error('jsonreplace', jsonreplace_handler)

### Writer

def write(input, encoding='utf-8', outputEncoding=None):
    writer = JsonWriter(input_encoding=encoding, output_encoding=outputEncoding)
    writer.write(input)
    return writer.getvalue()

re_strmangle = re.compile('"|\b|\f|\n|\r|\t|\\\\')

def func_strmangle(match):
    return {
        '"': '\\"',
        '\b': '\\b',
        '\f': '\\f',
        '\n': '\\n',
        '\r': '\\r',
        '\t': '\\t',
        '\\': '\\\\',
        }[match.group(0)]

def strmangle(text):
    return re_strmangle.sub(func_strmangle, text)

class JsonStream(object):

    def __init__(self):
        self.buf = []

    def write(self, text):
        self.buf.append(text)

    def getvalue(self):
        return ''.join(self.buf)

class JsonWriter(object):

    def __init__(self, stream=None, input_encoding='utf-8', output_encoding=None):
        '''
        - stream is optional, if specified must also give output_encoding
        - The input strings can be unicode or in input_encoding
        - output_encoding is optional, if omitted, result will be unicode
        '''
        if stream is not None:
            if output_encoding is None:
                raise WriteException, 'If a stream is given, output encoding must also be provided'
        else:
            stream = JsonStream()
        self.stream = stream
        self.input_encoding = input_encoding
        self.output_encoding = output_encoding

    def write(self, obj):
        if isinstance(obj, (list, tuple)):
            self.stream.write('[')
            first = True
            for elem in obj:
                if first:
                    first = False
                else:
                    self.stream.write(',')
                self.write(elem)
            self.stream.write(']'),
        elif isinstance(obj, dict):
            self.stream.write('{')
            first = True
            for key, value in obj.iteritems():
                if first:
                    first = False
                else:
                    self.stream.write(',')
                self.write(key)
                self.stream.write(':')
                self.write(value)
            self.stream.write('}')
        elif obj is True:
            self.stream.write('true')
        elif obj is False:
            self.stream.write('false')
        elif obj is None:
            self.stream.write('null')
        elif not isinstance(obj, basestring):
            # if we are not baseobj, convert to it
            try:
                obj = str(obj)
            except Exception, exc:
                raise WriteException, 'Cannot write object (%s: %s)' % (exc.__class__, exc)
            self.stream.write(obj)
        else:
            # convert to unicode first
            if not isinstance(obj, unicode):
                try:
                    obj = unicode(obj, self.input_encoding)
                except (UnicodeDecodeError, UnicodeTranslateError):
                    obj = unicode(obj, 'utf-8', 'replace')
            # do the mangling
            obj = strmangle(obj)
            # make the encoding
            if self.output_encoding is not None:
                obj = obj.encode(self.output_encoding, 'jsonreplace')
            self.stream.write('"')
            self.stream.write(obj)
            self.stream.write('"')

    def getvalue(self):
        return self.stream.getvalue()



########NEW FILE########
__FILENAME__ = runtests
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (C) 2008 The Tegaki project contributors
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

# Contributors to this file:
# - Mathieu Blondel

import glob
import os
import sys
import unittest
import doctest

import tegaki

currdir = os.path.dirname(os.path.abspath(__file__))
parentdir = os.path.join(currdir, "..")

os.chdir(currdir)
sys.path = sys.path + [parentdir]                   

def gettestnames():
    return [name[:-3] for name in glob.glob('test_*.py')]

# Run doctests

for attr in dir(tegaki):
    attr = getattr(tegaki, attr)
    if type(attr) == type(tegaki):
        if hasattr(attr, "__doctest__") and attr.__doctest__:
            doctest.testmod(attr)

# Run unittests

suite = unittest.TestSuite()
loader = unittest.TestLoader()

for name in gettestnames():
    suite.addTest(loader.loadTestsFromName(name))

testRunner = unittest.TextTestRunner(verbosity=1)
testRunner.run(suite)



########NEW FILE########
__FILENAME__ = test_arrayutils
# -*- coding: utf-8 -*-

# Copyright (C) 2008 The Tegaki project contributors
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

# Contributors to this file:
# - Mathieu Blondel

import unittest

from tegaki.arrayutils import *


class ArrayTest(unittest.TestCase):

    def testArrayFlatten(self):
        for arr, expected in (
                                ([[1,2], [3,4]], [1, 2, 3, 4]),
                                ([[]], [])
                             ):
            
            self.assertEquals(array_flatten(arr), expected)

    def testArrayReshape(self):
        for arr, expected, n in (
                                ([1, 2, 3, 4], [[1,2], [3,4]], 2),
                                ([], [], 2),
                                ([1, 2, 3], [[1, 2]], 2) # expected 4 values
                             ):
            
            self.assertEquals(array_reshape(arr, n), expected)


    def testArraySplit(self):
        arr = [[1,2], [3,4], [5,6], [7,8], [9, 10], [11, 12]]
        expected = [ [[1,2],[3,4]], [[5,6],[7, 8]], [[9,10],[11,12]] ]

        self.assertEquals(array_split(arr, 3), expected)

    def testArrayMean(self):
        arr = [1, 2, 3, 4]
        expected = 2.5

        self.assertEquals(array_mean(arr), expected)

    def testArrayVariance(self):
        arr = [1, 2, 3, 4]
        expected = 1.25

        self.assertEquals(array_variance(arr), expected)

    def testArrayMeanVector(self):
        arr = [ [1,2], [3,4] ]
        expected = [2, 3]

        self.assertEquals(array_mean_vector(arr), expected)

    def testArrayVarianceVector(self):
        arr = [ [1,2], [3,4] ]
        expected = [1.0, 1.0]

        self.assertEquals(array_variance_vector(arr), expected)
        
    def testArrayAdd(self):
        arr1 = [1,2]
        arr2 = [3,4]
        expected = [4, 6]
        
        self.assertEquals(array_add(arr1, arr2), expected)

    def testArrayMul(self):
        arr1 = [1,2]
        arr2 = [3,4]
        expected = [3, 8]
        
        self.assertEquals(array_mul(arr1, arr2), expected)

########NEW FILE########
__FILENAME__ = test_character
# -*- coding: utf-8 -*-

# Copyright (C) 2008 The Tegaki project contributors
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

# Contributors to this file:
# - Mathieu Blondel

import unittest
import os
import sys
import StringIO
import minjson
import tempfile

from tegaki.character import Point, Stroke, Writing, Character

class CharacterTest(unittest.TestCase):

    def setUp(self):
        self.currdir = os.path.dirname(os.path.abspath(__file__))

        self.strokes = [[(210, 280), (213, 280), (216, 280), (220, 280), (223,
280), (226, 280), (230, 280), (233, 280), (236, 280), (243, 280), (246, 280),
(253, 280), (260, 280), (263, 280), (270, 283), (276, 283), (283, 286), (286,
286), (293, 290), (296, 290), (300, 290), (303, 290), (306, 290), (310, 290),
(313, 290), (316, 293), (320, 293), (320, 296), (320, 300), (316, 303), (316,
306), (316, 310), (316, 313), (313, 316), (313, 320), (310, 323), (310, 326),
(306, 330), (306, 333), (303, 340), (300, 346), (300, 350), (300, 356), (296,
360), (293, 366), (290, 366), (286, 373), (283, 376), (280, 380), (276, 386),
(273, 386), (273, 390), (270, 390), (270, 396), (266, 396), (263, 400), (260,
403), (256, 406), (253, 406), (253, 410), (250, 410), (250, 413), (246, 413),
(250, 413), (253, 413), (256, 413), (260, 413), (263, 413), (286, 423), (290,
423), (296, 423), (300, 423), (306, 426), (310, 426), (313, 426), (316, 426),
(316, 430), (320, 430), (323, 430), (326, 430), (326, 433), (330, 433), (333,
433), (333, 436), (336, 436), (336, 440), (336, 443), (336, 446), (336, 450),
(336, 453), (336, 456), (336, 460), (336, 463), (336, 466), (336, 470), (336,
476), (333, 480), (333, 483), (333, 486), (330, 490), (330, 496), (326, 496),
(326, 500), (326, 503), (323, 506), (323, 510), (320, 516), (316, 520), (316,
523), (313, 526), (310, 526), (306, 530), (306, 533), (303, 536), (300, 536),
(300, 540), (296, 546), (293, 546), (290, 553), (286, 556), (283, 556), (283,
560), (276, 563), (270, 566), (266, 566), (263, 573), (260, 573), (256, 576),
(253, 576), (250, 580), (250, 583), (246, 583), (243, 586), (240, 586), (240,
590), (236, 590), (233, 593), (230, 596), (226, 596), (220, 596), (220, 600),
(216, 600), (213, 600), (210, 603), (206, 603), (203, 603)], [(200, 276), (200,
280), (200, 283), (200, 286), (200, 290), (203, 293), (203, 296), (203, 300),
(206, 300), (206, 306), (206, 310), (206, 316), (206, 320), (210, 323), (210,
326), (210, 333), (210, 336), (210, 340), (210, 343), (210, 346), (213, 353),
(213, 356), (213, 360), (213, 363), (216, 363), (216, 370), (216, 373), (216,
376), (220, 380), (220, 386), (220, 393), (220, 396), (220, 400), (220, 403),
(220, 410), (220, 416), (220, 420), (220, 423), (220, 426), (220, 433), (220,
436), (220, 443), (220, 446), (220, 450), (220, 453), (220, 460), (220, 466),
(220, 470), (220, 473), (220, 476), (220, 483), (220, 486), (220, 490), (220,
493), (220, 496), (220, 500), (220, 503), (220, 506), (220, 510), (220, 513),
(220, 516), (220, 520), (220, 526), (220, 530), (223, 536), (223, 540), (223,
543), (223, 546), (223, 553), (223, 556), (223, 560), (223, 566), (223, 570),
(223, 573), (223, 576), (223, 580), (223, 583), (223, 590), (223, 593), (223,
596), (223, 603), (223, 606), (223, 613), (223, 616), (223, 620), (223, 626),
(223, 633), (223, 640), (223, 643), (223, 650), (223, 653), (223, 660), (223,
663), (223, 666), (223, 673), (223, 676), (223, 683), (223, 686), (223, 690),
(223, 693), (223, 696), (223, 700), (223, 706), (223, 710), (223, 713), (223,
720), (223, 723), (223, 726), (223, 730), (223, 736), (223, 740), (223, 746),
(223, 750), (223, 753), (223, 756), (223, 760), (223, 763), (223, 766), (223,
773), (223, 776), (223, 780)], [(493, 216), (493, 220), (496, 223), (496, 226),
(496, 230), (500, 233), (500, 236), (500, 240), (500, 243), (503, 246), (503,
250), (506, 253), (506, 256), (506, 260), (510, 263), (510, 266), (510, 270),
(510, 273)], [(370, 283), (373, 283), (376, 283), (380, 283), (386, 283), (390,
283), (400, 283), (403, 283), (413, 283), (423, 283), (426, 283), (436, 283),
(443, 283), (450, 283), (456, 283), (466, 283), (470, 283), (476, 283), (486,
283), (493, 283), (500, 283), (503, 283), (513, 283), (516, 283), (523, 283),
(526, 283), (533, 283), (536, 283), (540, 283), (546, 283), (550, 283), (583,
283), (586, 283), (593, 283), (596, 283), (600, 283), (606, 283), (610, 283),
(616, 283), (620, 283), (626, 283), (633, 283), (636, 283), (643, 283), (646,
283), (650, 283), (653, 283), (656, 283), (663, 283), (666, 283), (670, 283),
(673, 283), (676, 283), (680, 283), (683, 283), (686, 283), (690, 283), (693,
283), (696, 283), (700, 283), (703, 286)], [(530, 370), (536, 373), (540, 373),
(546, 373), (550, 373), (570, 380), (573, 380), (580, 380), (600, 386), (603,
386), (613, 386), (616, 386), (626, 386), (630, 386), (636, 386), (640, 386),
(646, 386), (650, 386), (653, 386), (656, 386), (656, 390), (656, 393), (660,
396), (660, 400), (660, 403), (660, 406), (663, 410), (663, 413), (663, 416),
(663, 420), (663, 423), (663, 426), (663, 430), (663, 433), (663, 436), (663,
440), (663, 446), (663, 450), (663, 456), (663, 460), (663, 463), (663, 470),
(663, 473), (663, 480), (663, 483), (663, 490), (660, 496), (660, 500), (660,
506), (660, 510), (660, 516), (656, 520), (656, 526), (656, 530), (656, 536),
(656, 543), (656, 546), (656, 553), (653, 556), (653, 563), (653, 566), (653,
570), (650, 573), (650, 576), (646, 583), (646, 586), (643, 590), (643, 593),
(640, 596), (640, 600), (636, 603), (636, 606), (633, 606), (633, 610), (630,
610), (626, 610), (623, 610), (623, 613), (620, 613), (616, 613), (613, 613),
(610, 613), (606, 613)], [(490, 293), (490, 296), (490, 300), (490, 303), (490,
306), (490, 310), (490, 316), (490, 320), (493, 323), (493, 330), (493, 336),
(493, 343), (493, 346), (493, 353), (493, 363), (493, 366), (493, 373), (493,
376), (493, 386), (493, 390), (493, 396), (493, 403), (493, 406), (493, 413),
(493, 416), (493, 423), (493, 426), (493, 433), (493, 436), (493, 443), (493,
453), (493, 456), (493, 463), (493, 470), (486, 490), (486, 520), (483, 530),
(483, 530), (483, 540), (480, 543), (480, 550), (480, 553), (476, 560), (476,
563), (476, 566), (476, 576), (476, 580), (473, 586), (473, 590), (460, 603),
(460, 606), (460, 613), (460, 620), (456, 626), (456, 636), (456, 640), (453,
646), (453, 650), (453, 656), (453, 660), (450, 666), (450, 673), (446, 676),
(443, 680), (443, 683), (443, 686), (440, 690), (440, 696), (436, 696), (436,
703), (433, 706), (433, 713), (430, 716), (430, 720), (426, 723), (426, 726),
(423, 730), (420, 736), (420, 740), (420, 743), (420, 746), (416, 746), (416,
750), (416, 753), (413, 756), (413, 760), (410, 760), (410, 763), (406, 763)]]

    def _testReadXML(self, char):
        self.assertEquals(char.get_utf8(), "防")

        self.assertEquals(self.strokes, char.get_writing().get_strokes())      
 

    def testConstructorAndSave(self):
        file_ = os.path.join(self.currdir, "data", "character.xml")

        for f in (file_, file_ + ".gzip", file_ + ".bz2", None):
            char = Character(f)
            if f:
                self._testReadXML(char) # check that it is correctly loaded

            files = map(tempfile.mkstemp, (".xml", ".xml.gz", ".xml.bz2"))
            output_paths = [path for fd,path in files]
            
            for path in output_paths:                
                try:
                    # check that save with a path argument works
                    char.save(path)
                    newchar = Character(path)
                    self.assertEquals(char, newchar)
                finally:
                    os.unlink(path)

                try:
                    # check that save with a path argument works
                    newchar.save()
                    newchar2 = Character(path)
                    self.assertEquals(char, newchar2)
                finally:
                    os.unlink(path)

        char = Character()
        self.assertRaises(ValueError, char.save)

                


    def testReadXMLFile(self):
        file = os.path.join(self.currdir, "data", "character.xml")
        char = Character()
        char.read(file)

        self._testReadXML(char)

    def testReadXMLGzipFile(self):
        file = os.path.join(self.currdir, "data", "character.xml.gzip")
        char = Character()
        char.read(file, gzip=True)

        self._testReadXML(char)

    def testReadXMLBZ2File(self):
        file = os.path.join(self.currdir, "data", "character.xml.bz2")
        char = Character()
        char.read(file, bz2=True)

        self._testReadXML(char)

    def testReadXMLString(self):
        file = os.path.join(self.currdir, "data", "character.xml")
        
        f = open(file)
        buf = f.read()
        f.close()
        
        char = Character()
        char.read_string(buf)

        self._testReadXML(char)

    def testReadXMLGzipString(self):
        file = os.path.join(self.currdir, "data", "character.xml.gzip")
        file = open(file)
        string = file.read()
        file.close()
        
        char = Character()
        char.read_string(string, gzip=True)

        self._testReadXML(char)

    def testReadXMLBZ2String(self):
        file = os.path.join(self.currdir, "data", "character.xml.bz2")
        file = open(file)
        string = file.read()
        file.close()
        
        char = Character()
        char.read_string(string, bz2=True)

        self._testReadXML(char)

    def _getPoint(self):
        point = Point()
        point.x = 1
        point.y = 2
        point.timestamp = 3
        return point

    def testPointToXML(self):
        point = self._getPoint()
        self.assertEquals(point.to_xml(), '<point x="1" y="2" timestamp="3" />')

    def testPointToJSON(self):
        point = self._getPoint()
        self.assertEquals(minjson.read(point.to_json()),
                          {u'y': 2, u'timestamp': 3, u'x': 1})

    def _getStroke(self):
        point = Point()
        point.x = 1
        point.y = 2
        point.timestamp = 3
                
        point2 = Point()
        point2.x = 4
        point2.y = 5
        point2.pressure = 0.1

        stroke = Stroke()
        stroke.append_point(point)
        stroke.append_point(point2)
                
        return stroke

    def testStrokeToXML(self):
        stroke = self._getStroke()

        expected = """<stroke>
  <point x="1" y="2" timestamp="3" />
  <point x="4" y="5" pressure="0.1" />
</stroke>"""

        self.assertEquals(expected, stroke.to_xml())

    def testStrokeToJSON(self):
        stroke = self._getStroke()

        expected = {u'points': [{u'y': 2, u'timestamp': 3, u'x': 1}, {u'y': 5,
u'pressure': 0, u'x': 4}]}

        self.assertEquals(minjson.read(stroke.to_json()), expected)

    def _getWriting(self):
        point = Point()
        point.x = 1
        point.y = 2
        point.timestamp = 3
                
        point2 = Point()
        point2.x = 4
        point2.y = 5
        point2.pressure = 0.1

        stroke = Stroke()
        stroke.append_point(point)
        stroke.append_point(point2)
                
        writing = Writing()
        writing.append_stroke(stroke)
                
        return writing

    def testWritingToXML(self):
        writing = self._getWriting()

        expected = """<width>1000</width>
<height>1000</height>
<strokes>
  <stroke>
    <point x="1" y="2" timestamp="3" />
    <point x="4" y="5" pressure="0.1" />
  </stroke>
</strokes>"""

        self.assertEquals(expected, writing.to_xml())

    def testWritingToJSON(self):
        writing = self._getWriting()

        expected = {u'width': 1000, u'height': 1000, u'strokes': [{u'points':
[{u'y': 2, u'timestamp': 3, u'x': 1}, {u'y': 5, u'pressure': 0, u'x': 4}]}]}

        self.assertEquals(minjson.read(writing.to_json()), expected)

    def _getCharacter(self):
        writing = self._getWriting()

        char = Character()
        char.set_writing(writing)
        char.set_utf8("A")

        return char

    def testWriteXMLFile(self):
        char = self._getCharacter()

        io = StringIO.StringIO()
        char.write(io)

        new_char = Character()
        new_char.read_string(io.getvalue())

        self.assertEquals(char, new_char)

    def testCharacterToJSON(self):
        char = self._getCharacter()

        expected = {u'utf8': u'A', u'writing': {u'width' : 1000, 
                    u'height': 1000, 'strokes': [{u'points': [{u'y':
                    2, u'timestamp': 3, u'x': 1}, 
                    {u'y': 5, u'pressure': 0, u'x': 4}]}]}}

        self.assertEquals(minjson.read(char.to_json()), expected)

    def testNewWriting(self):
        writing = Writing()

        writing.move_to(0,0)
        writing.line_to(1,1)
        writing.line_to(2,2)
        writing.line_to(3,3)

        writing.move_to(4,4)
        writing.line_to(5,5)

        writing.move_to(6,6)
        writing.line_to(7,7)
        writing.line_to(8,8)

        strokes = writing.get_strokes()
        expected = [ [(0, 0), (1,1), (2,2), (3,3)],
                     [(4,4), (5,5)],
                     [(6,6), (7,7), (8,8)] ]

        self.assertEquals(strokes, expected)

    def testDuration(self):
        point = Point()
        point.x = 1
        point.y = 2
        point.timestamp = 0
                
        point2 = Point()
        point2.x = 4
        point2.y = 5
        point2.timestamp = 5

        stroke = Stroke()
        stroke.append_point(point)
        stroke.append_point(point2)

        point3 = Point()
        point3.x = 1
        point3.y = 2
        point3.timestamp = 7
                
        point4 = Point()
        point4.x = 4
        point4.y = 5
        point4.timestamp = 10

        stroke2 = Stroke()
        stroke2.append_point(point3)
        stroke2.append_point(point4)
              
        self.assertEquals(stroke2.get_duration(), 3)

        writing = Writing()
        writing.append_stroke(stroke)
        writing.append_stroke(stroke2)
        
        self.assertEquals(writing.get_duration(), 10)

    def testPointEquality(self):
        p1 = Point(x=2, y=3)
        p2 = Point(x=2, y=3)
        p3 = Point(x=2, y=4)

        self.assertTrue(p1 == p2)
        self.assertFalse(p1 == p3)

    def testPointEqualityNone(self):
        p1 = Point(x=2, y=3)
        self.assertFalse(p1 == None)
        self.assertTrue(p1 != None)

    def testPointCopy(self):
        p1 = Point(x=2, y=3)
        p2 = p1.copy()

        self.assertTrue(p1 == p2)

    def testStrokeEquality(self):
        s1 = Stroke()
        s1.append_point(Point(x=2, y=3))
        s1.append_point(Point(x=3, y=4))

        s2 = Stroke()
        s2.append_point(Point(x=2, y=3))
        s2.append_point(Point(x=3, y=4))

        s3 = Stroke()
        s3.append_point(Point(x=2, y=3))
        s3.append_point(Point(x=4, y=5))

        self.assertTrue(s1 == s2)
        self.assertFalse(s1 == s3)

    def testStrokeEqualityNone(self):
        s1 = Stroke()
        s1.append_point(Point(x=2, y=3))
        s1.append_point(Point(x=3, y=4))

        self.assertFalse(s1 == None)
        self.assertTrue(s1 != None)

    def testStrokeCopy(self):
        s1 = Stroke()
        s1.append_point(Point(x=2, y=3))
        s1.append_point(Point(x=3, y=4))

        s2 = s1.copy()

        self.assertTrue(s1 == s2)

    def testWritingEquality(self):
        s1 = Stroke()
        s1.append_point(Point(x=2, y=3))
        s1.append_point(Point(x=3, y=4))

        s2 = Stroke()
        s2.append_point(Point(x=2, y=3))
        s2.append_point(Point(x=3, y=4))

        w1 = Writing()
        w1.append_stroke(s1)
        w1.append_stroke(s2)

        s1 = Stroke()
        s1.append_point(Point(x=2, y=3))
        s1.append_point(Point(x=3, y=4))

        s2 = Stroke()
        s2.append_point(Point(x=2, y=3))
        s2.append_point(Point(x=3, y=4))

        w2 = Writing()
        w2.append_stroke(s1)
        w2.append_stroke(s2)

        s1 = Stroke()
        s1.append_point(Point(x=2, y=3))
        s1.append_point(Point(x=3, y=4))

        s2 = Stroke()
        s2.append_point(Point(x=2, y=3))
        s2.append_point(Point(x=3, y=5))

        w3 = Writing()
        w3.append_stroke(s1)
        w3.append_stroke(s2)

        self.assertEquals(w1, w2)
        self.assertNotEqual(w1, w3)

    def testWritingEqualityNone(self):
        s1 = Stroke()
        s1.append_point(Point(x=2, y=3))
        s1.append_point(Point(x=3, y=4))

        s2 = Stroke()
        s2.append_point(Point(x=2, y=3))
        s2.append_point(Point(x=3, y=4))

        w1 = Writing()
        w1.append_stroke(s1)
        w1.append_stroke(s2)

        self.assertTrue(w1 != None)
        self.assertFalse(w1 == None)

    def testCharacterEqualityNone(self):
        c = Character()
        self.assertTrue(c != None)
        self.assertFalse(c == None)        

    def testWritingCopy(self):
        s1 = Stroke()
        s1.append_point(Point(x=2, y=3))
        s1.append_point(Point(x=3, y=4))

        s2 = Stroke()
        s2.append_point(Point(x=2, y=3))
        s2.append_point(Point(x=3, y=4))

        w1 = Writing()
        w1.append_stroke(s1)
        w1.append_stroke(s2)

        w2 = w1.copy()

        self.assertTrue(w1 == w2)

    def testGetNPoints(self):
        writing = self._getWriting()
        self.assertEquals(writing.get_n_points(), 2)

    def testRemoveStroke(self):
        s1 = Stroke()
        s1.append_point(Point(x=2, y=3))
        s1.append_point(Point(x=3, y=4))

        s2 = Stroke()
        s2.append_point(Point(x=2, y=3))
        s2.append_point(Point(x=3, y=4))

        w = Writing()
        w.append_stroke(s1)
        w.append_stroke(s2)

        w.remove_stroke(1)
        
        self.assertEquals(w.get_strokes(), [[(2,3),(3,4)]])

    def testInsertStroke(self):
        s1 = Stroke()
        s1.append_point(Point(x=2, y=3))
        s1.append_point(Point(x=3, y=4))

        s2 = Stroke()
        s2.append_point(Point(x=2, y=3))
        s2.append_point(Point(x=3, y=4))

        w = Writing()
        w.append_stroke(s1)
        w.append_stroke(s2)

        s3 = Stroke()      
        s3.append_point(Point(x=22, y=33))
        s3.append_point(Point(x=33, y=44))

        w.insert_stroke(1, s3)

        self.assertEquals(w.get_strokes(), [[(2,3),(3,4)], [(22,33),(33,44)],
                                            [(2,3),(3,4)]])    

    def testReplaceStroke(self):
        s1 = Stroke()
        s1.append_point(Point(x=2, y=3))
        s1.append_point(Point(x=3, y=4))

        s2 = Stroke()
        s2.append_point(Point(x=2, y=3))
        s2.append_point(Point(x=3, y=4))

        w = Writing()
        w.append_stroke(s1)
        w.append_stroke(s2)  

        s3 = Stroke()      
        s3.append_point(Point(x=22, y=33))
        s3.append_point(Point(x=33, y=44))

        w.replace_stroke(1, s3)
        self.assertEquals(w.get_strokes(), [[(2,3),(3,4)],[(22,33),(33,44)]])

    def testClearStroke(self):
        s1 = Stroke()
        s1.append_point(Point(x=2, y=3))
        s1.append_point(Point(x=3, y=4))
        s1.clear()
        
        self.assertEquals(len(s1), 0)

    def testValidate(self):
        path = os.path.join(self.currdir, "data", "character.xml")
        f = open(path)
        buf = f.read()
        f.close()

        invalid = \
"""
<?xml version="1.0" encoding="UTF-8"?>
  <character>
    <utf8>防</utf8>
    <strokes>
      <stroke>
      </stroke>
    </strokes>
  </character>
"""

        malformed = \
"""
<?xml version="1.0" encoding="UTF-8"?>
  <character>
    <utf8>防</utf8>
    <strokes>
      <stroke>
      </stroke>
    </strokes>
"""

        try:
            self.assertTrue(Character.validate(buf))
            self.assertFalse(Character.validate(invalid))
            self.assertFalse(Character.validate(malformed))
        except NotImplementedError:
            sys.stderr.write("lxml missing!\n")
            pass

    def testToSexp(self):
        f = os.path.join(self.currdir, "data", "character.xml")
        char = Character()
        char.read(f)
        f = open(os.path.join(self.currdir, "data", "character.sexp"))
        sexp = f.read().strip()
        f.close()
        self.assertEquals(char.to_sexp(), sexp)

    def testIsSmall(self):
        for filename, res in (("small.xml", True),
                              ("small2.xml", True),
                              ("small3.xml", True),
                              ("small4.xml", True),
                              ("small5.xml", True),
                              ("non-small.xml", False)):
            f = os.path.join(self.currdir, "data", "small", filename)
            char = Character()
            char.read(f)
            self.assertEquals(char.get_writing().is_small(), res)

       
########NEW FILE########
__FILENAME__ = test_charcol
# -*- coding: utf-8 -*-

# Copyright (C) 2009 The Tegaki project contributors
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

# Contributors to this file:
# - Mathieu Blondel

import unittest
import os
import sys
import StringIO

from tegaki.character import Point, Stroke, Writing, Character
from tegaki.charcol import CharacterCollection

class CharacterCollectionTest(unittest.TestCase):

    def setUp(self):
        self.currdir = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(self.currdir, "data", "collection", "test.charcol")
        self.cc = CharacterCollection()
        self.cc.read(path)
        f = os.path.join(self.currdir, "data", "character.xml")
        self.c = Character()
        self.c.read(f)

    def testValidate(self):
        path = os.path.join(self.currdir, "data", "collection", "test.charcol")
        f = open(path)
        buf = f.read()
        f.close()

        invalid = \
"""
<?xml version="1.0" encoding="UTF-8"?>
  <character>
    <utf8>防</utf8>
    <strokes>
      <stroke>
      </stroke>
    </strokes>
  </character>
"""

        malformed = \
"""
<?xml version="1.0" encoding="UTF-8"?>
  <character>
"""

        try:
            self.assertTrue(CharacterCollection.validate(buf))
            self.assertFalse(CharacterCollection.validate(invalid))
            self.assertFalse(CharacterCollection.validate(malformed))
        except NotImplementedError:
            sys.stderr.write("lxml missing!\n")
            pass

    def _testReadXML(self, charcol):
        self.assertEquals(charcol.get_set_list(), ["一", "三", "二", "四"])

        c = {}
        for k in ["19968_1", "19968_2", "19968_3", "19977_1", "19977_2",
                 "20108_1"]:
            c[k] = Character()
            c[k].read(os.path.join(self.currdir, "data", "collection",
                      k + ".xml"))

        self.assertEquals(charcol.get_characters("一"),
                          [c["19968_1"], c["19968_2"], c["19968_3"]])
        self.assertEquals(charcol.get_characters("三"),
                          [c["19977_1"], c["19977_2"]])
        self.assertEquals(charcol.get_characters("二"),
                          [c["20108_1"]])
        self.assertEquals(charcol.get_characters("四"), [])
        self.assertEquals(charcol.get_all_characters(),
                          [c["19968_1"], c["19968_2"], c["19968_3"],
                           c["19977_1"], c["19977_2"], c["20108_1"]])

    def testReadXMLFile(self):
        self._testReadXML(self.cc)

    def testToXML(self):
        charcol2 = CharacterCollection()
        charcol2.read_string(self.cc.to_xml())
        self.assertEquals(self.cc.get_set_list(), charcol2.get_set_list())
        self.assertEquals(self.cc.get_all_characters(),
                          charcol2.get_all_characters())

    def testWriteGzipString(self):
        charcol2 = CharacterCollection()
        charcol2.read_string(self.cc.write_string(gzip=True), gzip=True)
        self.assertEquals(self.cc.get_set_list(), charcol2.get_set_list())
        self.assertEquals(self.cc.get_all_characters(),
                          charcol2.get_all_characters())

    def testWriteBz2String(self):
        charcol2 = CharacterCollection()
        charcol2.read_string(self.cc.write_string(bz2=True), bz2=True)
        self.assertEquals(self.cc.get_set_list(), charcol2.get_set_list())
        self.assertEquals(self.cc.get_all_characters(),
                          charcol2.get_all_characters())

    def testAddSame(self):
        path = os.path.join(self.currdir, "data", "collection", "test.charcol")
        charcol = CharacterCollection()
        charcol.read(path)
        charcol2 = CharacterCollection()
        charcol2.read(path)
        charcol3 = charcol.concatenate(charcol2, check_duplicate=True)
        self.assertEquals(charcol3.get_set_list(), ["一", "三", "二", "四"])
        self.assertEquals(len(charcol3.get_characters("一")), 3)
        self.assertEquals(len(charcol3.get_characters("三")), 2)
        self.assertEquals(len(charcol3.get_characters("二")), 1)
        self.assertEquals(len(charcol3.get_characters("四")), 0)

    def testGetChars(self):
        all_ = self.cc.get_characters("一")
        self.assertEquals(self.cc.get_characters("一", limit=2), all_[0:2])
        self.assertEquals(self.cc.get_characters("一", offset=2), all_[2:])
        self.assertEquals(self.cc.get_characters("一", limit=1, offset=1),
                          all_[1:2])

    def testAdd(self):
        path = os.path.join(self.currdir, "data", "collection", "test.charcol")
        charcol = CharacterCollection()
        charcol.read(path)
        path2 = os.path.join(self.currdir, "data", "collection",
                             "test2.charcol")
        charcol2 = CharacterCollection()
        charcol2.read(path2)
        charcol3 = charcol + charcol2
        self.assertEquals(charcol3.get_set_list(), ["一", "三", "二", "四",
                                                    "a", "b", "c", "d"])
        self.assertEquals(len(charcol3.get_characters("一")), 3)
        self.assertEquals(len(charcol3.get_characters("三")), 2)
        self.assertEquals(len(charcol3.get_characters("二")), 1)
        self.assertEquals(len(charcol3.get_characters("四")), 0)
        self.assertEquals(len(charcol3.get_characters("a")), 3)
        self.assertEquals(len(charcol3.get_characters("b")), 2)
        self.assertEquals(len(charcol3.get_characters("c")), 1)
        self.assertEquals(len(charcol3.get_characters("d")), 0)

    def testFromCharDirRecursive(self):
        directory = os.path.join(self.currdir, "data")
        charcol = CharacterCollection.from_character_directory(directory,
                                                        check_duplicate=True)
        self.assertEquals(sorted(charcol.get_set_list()),
                          sorted(["yo", "防", "三", "一", "二"]))
        self.assertEquals(len(charcol.get_characters("一")), 3)
        self.assertEquals(len(charcol.get_characters("三")), 2)
        self.assertEquals(len(charcol.get_characters("二")), 1)
        self.assertEquals(len(charcol.get_characters("防")), 1)

    def testFromCharDirNotRecursive(self):
        directory = os.path.join(self.currdir, "data")
        charcol = CharacterCollection.from_character_directory(directory,
                                        recursive=False, check_duplicate=True)
        self.assertEquals(charcol.get_set_list(), ["防"])
        self.assertEquals(len(charcol.get_characters("防")), 1)

    def testIncludeChars(self):
        self.cc.include_characters_from_text("一三")
        self.assertEquals(self.cc.get_set_list(), ["一", "三"])

    def testExcludeChars(self):
        self.cc.exclude_characters_from_text("三")
        self.assertEquals(self.cc.get_set_list(), ["一", "二"])

    def testProxy(self):
        char = self.cc.get_all_characters()[0]
        writing = char.get_writing()
        writing.normalize()
        strokes = writing.get_strokes(full=True)
        stroke = strokes[0]
        stroke.smooth()
        p = stroke[0]
        p.x = 10

        char2 = self.cc.get_all_characters()[0]
        self.assertEquals(char, char2)

    def testNoProxy(self):
        self.cc.WRITE_BACK = False

        char = self.cc.get_all_characters()[0]
        writing = char.get_writing()
        writing.normalize()
        strokes = writing.get_strokes(full=True)
        stroke = strokes[0]
        stroke.smooth()
        p = stroke[0]
        p.x = 10

        char2 = self.cc.get_all_characters()[0]
        self.assertNotEqual(char, char2)

        # manually update the object
        self.cc.update_character_object(char)

        char2 = self.cc.get_all_characters()[0]
        self.assertEquals(char, char2)

    def testAddSet(self):
        self.cc.add_set("toto")
        self.assertEquals(self.cc.get_set_list()[-1], "toto")

    def testRemoveSet(self):
        before = self.cc.get_set_list()
        self.cc.remove_set(before[-1])
        after = self.cc.get_set_list()
        self.assertEquals(len(before)-1, len(after))
        self.assertEquals(before[0:-1], after)

    def testGetNSets(self):
        self.assertEquals(len(self.cc.get_set_list()), self.cc.get_n_sets())
        self.assertEquals(4, self.cc.get_n_sets())

    def testGetTotalNCharacters(self):
        self.assertEquals(len(self.cc.get_all_characters()),
                          self.cc.get_total_n_characters())
        self.assertEquals(6, self.cc.get_total_n_characters())

    def testGetNCharacters(self):
        for set_name in self.cc.get_set_list():
            self.assertEquals(len(self.cc.get_characters(set_name)),
                              self.cc.get_n_characters(set_name))

        self.assertEquals(self.cc.get_n_characters("一"), 3)
        self.assertEquals(self.cc.get_n_characters("三"), 2)
        self.assertEquals(self.cc.get_n_characters("二"), 1)

    def testSetCharacters(self):
        before = self.cc.get_characters("一")[0:2]
        self.cc.set_characters("一", before)
        after = self.cc.get_characters("一")
        self.assertEquals(before, after)

    def testAppendCharacter(self):
        len_before = len(self.cc.get_characters("一"))
        self.cc.append_character("一", self.c)
        len_after = len(self.cc.get_characters("一"))
        self.assertEquals(len_before + 1, len_after)

    def testInsertCharacter(self):
        before = self.cc.get_characters("一")[0]
        len_before = len(self.cc.get_characters("一"))
        self.cc.insert_character("一", 0, self.c)

        after = self.cc.get_characters("一")[0]
        self.assertNotEqual(before, after)
        len_after = len(self.cc.get_characters("一"))

        self.assertEqual(len_before+1, len_after)

    def testReplaceCharacter(self):
        before = self.cc.get_characters("一")[0]
        len_before = len(self.cc.get_characters("一"))
        self.cc.replace_character("一", 0, self.c)

        after = self.cc.get_characters("一")[0]
        self.assertNotEqual(before, after)
        len_after = len(self.cc.get_characters("一"))

        self.assertEqual(len_before, len_after)

    def testRemoveCharacter(self):
        before = self.cc.get_characters("一")[0]
        len_before = len(self.cc.get_characters("一"))
        self.cc.remove_character("一", 0)

        after = self.cc.get_characters("一")[0]
        self.assertNotEqual(before, after)
        len_after = len(self.cc.get_characters("一"))

        self.assertEqual(len_before-1, len_after)

    def testRemoveLastCharacter(self):
        before = self.cc.get_characters("一")[-1]
        len_before = len(self.cc.get_characters("一"))
        self.cc.remove_last_character("一")

        after = self.cc.get_characters("一")[-1]
        self.assertNotEqual(before, after)
        len_after = len(self.cc.get_characters("一"))

        self.assertEqual(len_before-1, len_after)

    def testRemoveSamples(self):
        self.cc.remove_samples(keep_at_most=2)
        self.assertEquals(self.cc.get_n_characters("一"), 2)
        self.assertEquals(self.cc.get_n_characters("三"), 2)
        self.assertEquals(self.cc.get_n_characters("二"), 1)

        self.cc.remove_samples(keep_at_most=1)
        self.assertEquals(self.cc.get_n_characters("一"), 1)
        self.assertEquals(self.cc.get_n_characters("三"), 1)
        self.assertEquals(self.cc.get_n_characters("二"), 1)

    def testRemoveEmptySets(self):
        self.cc.remove_empty_sets()
        self.assertEquals(self.cc.get_set_list(), ["一", "三", "二"])

########NEW FILE########
__FILENAME__ = test_chardict
# -*- coding: utf-8 -*-

# Copyright (C) 2010 The Tegaki project contributors
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

# Contributors to this file:
# - Mathieu Blondel

import unittest
import os
import sys
import StringIO
import minjson
import tempfile

from tegaki.chardict import CharacterStrokeDictionary

class CharacterStrokeDictionaryTest(unittest.TestCase):

    def setUp(self):
        self.currdir = os.path.dirname(os.path.abspath(__file__))
        self.txt = os.path.join(self.currdir, "data", "strokes_ja.txt")
        self.gz = os.path.join(self.currdir, "data", "strokes_ja.txt.gz")

    def testRead(self):
        cdict = CharacterStrokeDictionary(self.txt)
        cdictgz = CharacterStrokeDictionary(self.gz)

        for d in (cdict, cdictgz):
            self.assertEquals(len(d), 8)
            self.assertTrue(u"⺕" in d.get_characters())

    def testWrite(self):
        cdict = CharacterStrokeDictionary(self.txt)
        io = StringIO.StringIO()
        cdict.write(io)
        io.seek(0) # need to rewind the file
        cdict2 = CharacterStrokeDictionary()
        cdict2.read(io)
        self.assertEquals(cdict, cdict2)

########NEW FILE########
__FILENAME__ = test_mathutils
# -*- coding: utf-8 -*-

# Copyright (C) 2008 The Tegaki project contributors
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

# Contributors to this file:
# - Mathieu Blondel

import unittest

from tegaki.mathutils import *

class MathTest(unittest.TestCase):

    def testEuclideanDistance(self):
        for v1, v2, expected in ( ( (2, 10, 12), (3, 10, 7), 5.0 ),
                                  ( (5, 5), (5, 5), 0.0)
                                ):

            res = round(euclidean_distance(v1, v2))
            self.assertEquals(res, expected)

########NEW FILE########
__FILENAME__ = test_recognizer
# -*- coding: utf-8 -*-

# Copyright (C) 2010 The Tegaki project contributors
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

# Contributors to this file:
# - Mathieu Blondel

import unittest

from tegaki.recognizer import *

class ResultsTest(unittest.TestCase):

    def testToSmallKana(self):
        res = Results([("マ",1),("チ",2),("ユ",3),("ー",4)]).to_small_kana()
        res2 = Results([("ま",1),("ち",2),("ゆ",3),("ー",4)]).to_small_kana()
        self.assertEquals(res[2][0], "ュ")
        self.assertEquals(res2[2][0], "ゅ")
        
########NEW FILE########
__FILENAME__ = charcol
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (C) 2009 The Tegaki project contributors
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

# Contributors to this file:
# - Mathieu Blondel

import os

from tegaki.charcol import CharacterCollection

from tegakitools.tomoe import tomoe_dict_to_character_collection
from tegakitools.kuchibue import kuchibue_to_character_collection
try:
  from tegakitools.kanjivg import kanjivg_to_character_collection
  HAS_KANJIVG_SUPPORT = True
except:
  HAS_KANJIVG_SUPPORT = False

TYPE_CHARCOL, TYPE_CHARCOL_DB, TYPE_DIRECTORY, TYPE_TOMOE, TYPE_KANJIVG, TYPE_KUCHIBUE = \
range(6)

def _get_charcol(charcol_type, charcol_path):
    if charcol_type == TYPE_DIRECTORY:
        # charcol_path is actually a directory here
        return CharacterCollection.from_character_directory(charcol_path)

    elif charcol_type in (TYPE_CHARCOL, TYPE_CHARCOL_DB):
        return CharacterCollection(charcol_path)

    elif charcol_type == TYPE_TOMOE:
        return tomoe_dict_to_character_collection(charcol_path)

    elif charcol_type == TYPE_KUCHIBUE:
        return kuchibue_to_character_collection(charcol_path)

    elif charcol_type == TYPE_KANJIVG:
        return kanjivg_to_character_collection(charcol_path)
    

def get_aggregated_charcol(tuples, dbpath=None):
    """
    Create a character collection out of other character collections,
    character directories, tomoe dictionaries or kuchibue databases.

    tuples: a list of tuples (TYPE, path list)
    """

    # number of files for each character collection type
    n_files = [len(t[1]) for t in tuples]
    
    # we don't need to merge character collections if only one is provided
    # this can save a lot of time for large collections
    if sum(n_files) == 1 and dbpath is None:
        idx = n_files.index(1)
        return _get_charcol(tuples[idx][0], tuples[idx][1][0])

    if dbpath is not None and dbpath.endswith(".chardb"):
        if os.path.exists(dbpath):
            print "%s exists already." % dbpath
            print "Continuing will modify it..."
            answer = raw_input("Continue anyway? (y/N)")
            if answer == "y":
                print "Overwrite to concatenate collections together " + \
                      "in a new database"
                print "Don't overwrite to append new characters or "  + \
                      "filter (-i,-e,-m) existing database"
                answer = raw_input("Overwrite it? (y/N)")
                if answer == "y":
                    os.unlink(dbpath)
            else:
                exit()

        charcol = CharacterCollection(dbpath)
        #charcol.WRITE_BACK = False
        #charcol.AUTO_COMMIT = True
    else:
        charcol = CharacterCollection() # in memory db

    charcols = [_get_charcol(typ, path) \
                    for typ, paths in tuples for path in paths]

    charcol.merge(charcols)

    return charcol

########NEW FILE########
__FILENAME__ = kanjivg
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (C) 2009 The Tegaki project contributors
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

# Contributors to this file:
# - Mathieu Blondel
# - Roger Braun
#
# -------------
# NOTES:
# 
# This will read the KanjiVG xml files you can find at 
# http://kanjivg.tagaini.net/.
# Search for "resolution" if you want to control how many points are being
# created for the tegaki-xml. 

from tegaki.character import Point, Stroke, Writing, Character, \
                             _XmlBase
from tegaki.charcol import CharacterCollection
from math import sqrt  

from pyparsing import *

import re, sys

class SVG_Point(Point):
    def add(self, point):
        return SVG_Point(self.x + point.x, self.y + point.y)

    def subtract(self, point):
        return SVG_Point(self.x - point.x, self.y - point.y)

    def dist(self, point):
        return sqrt((point.x - self.x) ** 2 + (point.y - self.y) ** 2)

    def multiply(self, number):
        return SVG_Point(self.x * number, self.y * number)

    def reflect(self, mirror):
        return mirror.add(mirror.subtract(self))
    

class SVG_Parser:

    def __init__(self, svg):
        # This replaces small "m"s at the beginning of a path by the equivalent
        # capital "M".
        # See http://groups.google.com/group/kanjivg/browse_thread/thread/3a85fb72dfd81ef9
        self._svg = re.sub("^m","M",svg)
        self._points = []

    def get_points(self):
        return self._points
    
    def linear_interpolation(self,a,b,factor):
        xr = a.x + ((b.x - a.x) * factor)
        yr = a.y + ((b.y - a.y) * factor)
        return SVG_Point(xr,yr)

    def make_curvepoint(self,c1,c2,p,current_cursor,factor):
        ab = self.linear_interpolation(current_cursor,c1,factor)
        bc = self.linear_interpolation(c1,c2,factor)
        cd = self.linear_interpolation(c2,p,factor)
        abbc = self.linear_interpolation(ab,bc,factor)
        bccd = self.linear_interpolation(bc,cd,factor)
        return self.linear_interpolation(abbc, bccd, factor)

    def length(self,c1,c2,p,current_cursor,points):
        length = current_cursor.dist(p)
        return length

    def make_curvepoints_array(self,c1,c2,p,current_cursor,distance):
        result = []
        l = self.length(c1,c2,p,current_cursor,10.0)
        points = l * distance
        factor = points
        for i in range(0, int(points)):
            self._points.append(self.make_curvepoint(c1,c2,p,current_cursor,i / factor)) 
        

    def parse(self):
        # Taken and (rather heavily) modified from http://annarchy.cairographics.org/svgtopycairo/
        dot = Literal(".")
        comma = Literal(",").suppress()
        floater = Combine(Optional("-") + Word(nums) + Optional(dot + Word(nums)))
        floater.setParseAction(lambda toks:float(toks[0]))
        couple = floater + Optional(comma) + floater
        M_command = "M" + Group(couple)
        C_command = "C" + Group(couple + Optional(comma) + couple + Optional(comma) + couple)
        L_command = "L" + Group(couple)
        Z_command = "Z"
        c_command = "c" + Group(couple + Optional(comma) + couple + Optional(comma) + couple)
        s_command = "s" + Group(couple + Optional(comma) + couple)
        S_command = "S" + Group(couple + Optional(comma) + couple)
        svgcommand = M_command | C_command | L_command | Z_command | c_command | s_command | S_command
        phrase = OneOrMore(Group(svgcommand)) 
        self._svg_array = phrase.parseString(self._svg)
        self.make_points()

    def resize(self,n):
        return n * 1000.0 / 109.0

    def make_points(self):
        current_cursor = SVG_Point(0,0)
  # ATTENTION: This is the place where you can change the resolution of the created xmls, i.e. how many points are generated. Higher value = More points
        resolution = 0.1
        for command in self._svg_array:
            if command[0] == "M":
                point = SVG_Point(self.resize(command[1][0]),self.resize(command[1][1]))
                self._points.append(point)
                current_cursor = point

            if command[0] == "c":
                c1 = SVG_Point(self.resize(command[1][0]),self.resize(command[1][1])).add(current_cursor) 
                c2 = SVG_Point(self.resize(command[1][2]),self.resize(command[1][3])).add(current_cursor)
                p  = SVG_Point(self.resize(command[1][4]),self.resize(command[1][5])).add(current_cursor)
                self.make_curvepoints_array(c1,c2,p,current_cursor,resolution)             
                current_cursor = self._points[-1]

            if command[0] == "C":
                c1 = SVG_Point(self.resize(command[1][0]),self.resize(command[1][1])) 
                c2 = SVG_Point(self.resize(command[1][2]),self.resize(command[1][3]))
                p  = SVG_Point(self.resize(command[1][4]),self.resize(command[1][5]))
                self.make_curvepoints_array(c1,c2,p,current_cursor,resolution)             
                current_cursor = self._points[-1]

            if command[0] == "s":
                c2 = SVG_Point(self.resize(command[1][0]),self.resize(command[1][1])).add(current_cursor) 
                p = SVG_Point(self.resize(command[1][2]),self.resize(command[1][3])).add(current_cursor)
                c1 = self._points[-2].reflect(current_cursor)
                self.make_curvepoints_array(c1,c2,p,current_cursor,resolution)             
                current_cursor = self._points[-1]     

            if command[0] == "S":
                c2 = SVG_Point(self.resize(command[1][0]),self.resize(command[1][1])) 
                p = SVG_Point(self.resize(command[1][2]),self.resize(command[1][3]))
                c1 = self._points[-2].reflect(current_cursor)
                self.make_curvepoints_array(c1,c2,p,current_cursor,resolution)             
                current_cursor = self._points[-1]     
    
class KVGXmlDictionaryReader(_XmlBase):

    def __init__(self):
        self._charcol = CharacterCollection()

    def get_character_collection(self):
        return self._charcol

    def _start_element(self, name, attrs):
        self._tag = name

        if self._first_tag:
            self._first_tag = False
            if self._tag != "kanjivg":
                raise ValueError, "The very first tag should be <kanjivg>"

        if self._tag == "kanji":
            self._writing = Writing()
            self._utf8 = unichr(int(attrs["id"].split('_')[1], 16)).encode("UTF-8")

        if self._tag == "path":
            self._stroke = Stroke()
            if attrs.has_key("d"):
                self._stroke_svg = attrs["d"].encode("UTF-8")
                svg_parser = SVG_Parser(self._stroke_svg) 
                svg_parser.parse()
                self._stroke.append_points(svg_parser.get_points())
            else:
                sys.stderr.write("Missing data in <path> element: " + self._utf8 + "\n")
    
            
    def _end_element(self, name):
        if name == "kanji":
            char = Character()
            char.set_utf8(self._utf8)
            char.set_writing(self._writing)
            self._charcol.add_set(self._utf8)
            self._charcol.append_character(self._utf8, char)
            for s in ["_tag", "_stroke"]:
                if s in self.__dict__:
                    del self.__dict__[s]

        if name == "path":
            self._writing.append_stroke(self._stroke)
            self._stroke = None

        self._tag = None

    def _char_data(self, data):
        if self._tag == "utf8":
            self._utf8 = data.encode("UTF-8")
        elif self._tag == "width":
            self._writing.set_width(int(data))
        elif self._tag == "height":
            self._writing.set_height(int(data))

def kanjivg_to_character_collection(path):
    reader = KVGXmlDictionaryReader()
    gzip = False; bz2 = False
    if path.endswith(".gz"): gzip = True
    if path.endswith(".bz2"): bz2 = True
    reader.read(path, gzip=gzip, bz2=bz2)
    return reader.get_character_collection()


########NEW FILE########
__FILENAME__ = kuchibue
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (C) 2009 The Tegaki project contributors
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

# Contributors to this file:
# - Mathieu Blondel

# Incomplete parser for the unipen version of the kuchibue database
# See http://www.tuat.ac.jp/~nakagawa/database/

import re
import os

from tegaki.character import Point, Stroke, Writing, Character
from tegaki.charcol import CharacterCollection

from unipen import UnipenParser
from shiftjis import SHIFT_JIS_TABLE

class KuchibueParser(UnipenParser):

    # The Kuchibue database has three major differences with Tegaki
    #
    # 1) (0, 0) is the left-bottom corner in the former while it's the top-
    #    left corner in the latter.
    # 2) the default screen size is 1280*960 for the former while it's
    #    1000 * 1000 for the latter
    # 3) the screen contains 152 boxes (19 columns, 8 rows) for the former
    #    while it contains only 1 for the latter

    def __init__(self):
        UnipenParser.__init__(self)
        self._labels = []
        self._characters = []
        self._char = None
        self._row = 0
        self._col = 0
        self._screen = None
        self._line = None

    def _handle_SEGMENT(self, args):
        seg_type, delimit, quality, label = args.split(" ")
        if seg_type == "SCREEN":
            self._screen = []
        elif seg_type == "LINE":
            self._screen.append(0) # number of characters in line
        elif seg_type == "CHARACTER":
            label = label.strip()[1:-1]
            if label.startswith("SJIS"):
                charcode = int("0" + label[4:], 16)
                try:
                    label = SHIFT_JIS_TABLE[charcode]
                except KeyError:
                    pass #print "missing character", hex(charcode)
                    
            self._labels.append(label)
            self._screen[-1] += 1

    def _handle_X_DIM(self, args):
        self.FRAME_WIDTH = int(args)

    def _handle_Y_DIM(self, args):
        self.FRAME_HEIGHT = int(args)

    def _get_int_pair_from_line(self, line):
        k, v = line.split(":")
        return [int(val) for val in v.strip().split(" ")]

    def _handle_PAD(self, args):
        lines = [l.strip() for l in args.split("\n")]
        for line in lines:
            if line.startswith("Input Resolution"):
                self.INPUT_RESOLUTION_WIDTH, self.INPUT_RESOLUTION_HEIGHT = \
                    self._get_int_pair_from_line(line)

    def _handle_DATA_INFO(self, args):
        lines = [l.strip() for l in args.split("\n")]
        for line in lines:
            if line.startswith("Frame start"):
                self.FRAME_START_X, self.FRAME_START_Y = \
                    self._get_int_pair_from_line(line)
            elif line.startswith("Frame  step"):
                self.FRAME_STEP_X, self.FRAME_STEP_Y = \
                    self._get_int_pair_from_line(line)  
            elif line.startswith("Frame count"):
                self.FRAME_COUNT_COL, self.FRAME_COUNT_ROW = \
                    self._get_int_pair_from_line(line)    

    def _handle_START_BOX(self, args):
        if self._char:
            self._characters.append(self._char)
            if self._col == self.FRAME_COUNT_COL - 1:
                self._col = 0
                if self._row == self.FRAME_COUNT_ROW - 1:
                    self._row = 0
                else:
                    self._row += 1
            else:
                self._col += 1

        self._char = Character()

    def handle_eof(self):
        if self._char:
            self._characters.append(self._char)

    def _get_coordinates(self, x, y):
        y = abs(y - self.INPUT_RESOLUTION_HEIGHT) # change basis
        x -= self.FRAME_START_X # remove the padding
        x -= self.FRAME_STEP_X * self._col # translate to the left
        x *= float(Writing.WIDTH) / self.FRAME_WIDTH # scale for x = 1000
        y -= (self.INPUT_RESOLUTION_HEIGHT - self.FRAME_START_Y) # padding
        y -= self.FRAME_STEP_Y * self._row # translate to the top
        y *= float(Writing.HEIGHT) / self.FRAME_HEIGHT # scale for y = 1000
        return (int(x), int(y))

    def _handle_PEN_DOWN(self, args):
        writing = self._char.get_writing()
        points = [[int(p_) for p_ in p.split(" ")] \
                    for p in args.strip().split("\n")]
        stroke = Stroke()
        for x, y in points:
            x, y = self._get_coordinates(x,y)
            #assert(x >= 0 and x <= 1000)
            #assert(y >= 0 and y <= 1000)
            stroke.append_point(Point(x,y))
        writing.append_stroke(stroke)

    def _handle_PEN_UP(self, args):
        writing = self._char.get_writing()
        x, y = [int(p) for p in args.strip().split(" ")]
        x, y = self._get_coordinates(x,y)
        strokes = writing.get_strokes()
        strokes[-1].append(Point(x,y))

def kuchibue_to_character_collection(path):
    parser = KuchibueParser()
    parser.parse_file(path)
    return parser.get_character_collection()

if __name__ == "__main__":
    import sys
    charcol = kuchibue_to_character_collection(sys.argv[1])
    print charcol.to_xml()

########NEW FILE########
__FILENAME__ = shiftjis
# -*- coding: utf-8 -*-
SHIFT_JIS_TABLE = {
0x8140 : "　",
0x8141 : "、",
0x8142 : "。",
0x8143 : "，",
0x8144 : "．",
0x8145 : "・",
0x8146 : "：",
0x8147 : "；",
0x8148 : "？",
0x8149 : "！",
0x814a : "゛",
0x814b : "゜",
0x814c : "´",
0x814d : "｀",
0x814e : "¨",
0x814f : "＾",
0x8150 : "￣",
0x8151 : "＿",
0x8152 : "ヽ",
0x8153 : "ヾ",
0x8154 : "ゝ",
0x8155 : "ゞ",
0x8156 : "〃",
0x8157 : "仝",
0x8158 : "々",
0x8159 : "〆",
0x815a : "〇",
0x815b : "ー",
0x815c : "―",
0x815d : "‐",
0x815e : "／",
0x815f : "＼",
0x8160 : "〜",
0x8161 : "‖",
0x8162 : "｜",
0x8163 : "…",
0x8164 : "‥",
0x8165 : "‘",
0x8166 : "’",
0x8167 : "“",
0x8168 : "”",
0x8169 : "（",
0x816a : "）",
0x816b : "〔",
0x816c : "〕",
0x816d : "［",
0x816e : "］",
0x816f : "｛",
0x8170 : "｝",
0x8171 : "〈",
0x8172 : "〉",
0x8173 : "《",
0x8174 : "》",
0x8175 : "「",
0x8176 : "」",
0x8177 : "『",
0x8178 : "』",
0x8179 : "【",
0x817a : "】",
0x817b : "＋",
0x817c : "−",
0x817d : "±",
0x817e : "×",
0x8180 : "÷",
0x8181 : "＝",
0x8182 : "≠",
0x8183 : "＜",
0x8184 : "＞",
0x8185 : "≦",
0x8186 : "≧",
0x8187 : "∞",
0x8188 : "∴",
0x8189 : "♂",
0x818a : "♀",
0x818b : "°",
0x818c : "′",
0x818d : "″",
0x818e : "℃",
0x818f : "￥",
0x8190 : "＄",
0x8191 : "¢",
0x8192 : "£",
0x8193 : "％",
0x8194 : "＃",
0x8195 : "＆",
0x8196 : "＊",
0x8197 : "＠",
0x8198 : "§",
0x8199 : "☆",
0x819a : "★",
0x819b : "○",
0x819c : "●",
0x819d : "◎",
0x819e : "◇",
0x819f : "◆",
0x81a0 : "□",
0x81a1 : "■",
0x81a2 : "△",
0x81a3 : "▲",
0x81a4 : "▽",
0x81a5 : "▼",
0x81a6 : "※",
0x81a7 : "〒",
0x81a8 : "→",
0x81a9 : "←",
0x81aa : "↑",
0x81ab : "↓",
0x81ac : "〓",
0x81b8 : "∈",
0x81b9 : "∋",
0x81ba : "⊆",
0x81bb : "⊇",
0x81bc : "⊂",
0x81bd : "⊃",
0x81be : "∪",
0x81bf : "∩",
0x81c8 : "∧",
0x81c9 : "∨",
0x81ca : "¬",
0x81cb : "⇒",
0x81cc : "⇔",
0x81cd : "∀",
0x81ce : "∃",
0x81da : "∠",
0x81db : "⊥",
0x81dc : "⌒",
0x81dd : "∂",
0x81de : "∇",
0x81df : "≡",
0x81e0 : "≒",
0x81e1 : "≪",
0x81e2 : "≫",
0x81e3 : "√",
0x81e4 : "∽",
0x81e5 : "∝",
0x81e6 : "∵",
0x81e7 : "∫",
0x81e8 : "∬",
0x81f0 : "Å",
0x81f1 : "‰",
0x81f2 : "♯",
0x81f3 : "♭",
0x81f4 : "♪",
0x81f5 : "†",
0x81f6 : "‡",
0x81f7 : "¶",
0x81fc : "◯",
0x824f : "０",
0x8250 : "１",
0x8251 : "２",
0x8252 : "３",
0x8253 : "４",
0x8254 : "５",
0x8255 : "６",
0x8256 : "７",
0x8257 : "８",
0x8258 : "９",
0x8260 : "Ａ",
0x8261 : "Ｂ",
0x8262 : "Ｃ",
0x8263 : "Ｄ",
0x8264 : "Ｅ",
0x8265 : "Ｆ",
0x8266 : "Ｇ",
0x8267 : "Ｈ",
0x8268 : "Ｉ",
0x8269 : "Ｊ",
0x826a : "Ｋ",
0x826b : "Ｌ",
0x826c : "Ｍ",
0x826d : "Ｎ",
0x826e : "Ｏ",
0x826f : "Ｐ",
0x8270 : "Ｑ",
0x8271 : "Ｒ",
0x8272 : "Ｓ",
0x8273 : "Ｔ",
0x8274 : "Ｕ",
0x8275 : "Ｖ",
0x8276 : "Ｗ",
0x8277 : "Ｘ",
0x8278 : "Ｙ",
0x8279 : "Ｚ",
0x8281 : "ａ",
0x8282 : "ｂ",
0x8283 : "ｃ",
0x8284 : "ｄ",
0x8285 : "ｅ",
0x8286 : "ｆ",
0x8287 : "ｇ",
0x8288 : "ｈ",
0x8289 : "ｉ",
0x828a : "ｊ",
0x828b : "ｋ",
0x828c : "ｌ",
0x828d : "ｍ",
0x828e : "ｎ",
0x828f : "ｏ",
0x8290 : "ｐ",
0x8291 : "ｑ",
0x8292 : "ｒ",
0x8293 : "ｓ",
0x8294 : "ｔ",
0x8295 : "ｕ",
0x8296 : "ｖ",
0x8297 : "ｗ",
0x8298 : "ｘ",
0x8299 : "ｙ",
0x829a : "ｚ",
0x829f : "ぁ",
0x82a0 : "あ",
0x82a1 : "ぃ",
0x82a2 : "い",
0x82a3 : "ぅ",
0x82a4 : "う",
0x82a5 : "ぇ",
0x82a6 : "え",
0x82a7 : "ぉ",
0x82a8 : "お",
0x82a9 : "か",
0x82aa : "が",
0x82ab : "き",
0x82ac : "ぎ",
0x82ad : "く",
0x82ae : "ぐ",
0x82af : "け",
0x82b0 : "げ",
0x82b1 : "こ",
0x82b2 : "ご",
0x82b3 : "さ",
0x82b4 : "ざ",
0x82b5 : "し",
0x82b6 : "じ",
0x82b7 : "す",
0x82b8 : "ず",
0x82b9 : "せ",
0x82ba : "ぜ",
0x82bb : "そ",
0x82bc : "ぞ",
0x82bd : "た",
0x82be : "だ",
0x82bf : "ち",
0x82c0 : "ぢ",
0x82c1 : "っ",
0x82c2 : "つ",
0x82c3 : "づ",
0x82c4 : "て",
0x82c5 : "で",
0x82c6 : "と",
0x82c7 : "ど",
0x82c8 : "な",
0x82c9 : "に",
0x82ca : "ぬ",
0x82cb : "ね",
0x82cc : "の",
0x82cd : "は",
0x82ce : "ば",
0x82cf : "ぱ",
0x82d0 : "ひ",
0x82d1 : "び",
0x82d2 : "ぴ",
0x82d3 : "ふ",
0x82d4 : "ぶ",
0x82d5 : "ぷ",
0x82d6 : "へ",
0x82d7 : "べ",
0x82d8 : "ぺ",
0x82d9 : "ほ",
0x82da : "ぼ",
0x82db : "ぽ",
0x82dc : "ま",
0x82dd : "み",
0x82de : "む",
0x82df : "め",
0x82e0 : "も",
0x82e1 : "ゃ",
0x82e2 : "や",
0x82e3 : "ゅ",
0x82e4 : "ゆ",
0x82e5 : "ょ",
0x82e6 : "よ",
0x82e7 : "ら",
0x82e8 : "り",
0x82e9 : "る",
0x82ea : "れ",
0x82eb : "ろ",
0x82ec : "ゎ",
0x82ed : "わ",
0x82ee : "ゐ",
0x82ef : "ゑ",
0x82f0 : "を",
0x82f1 : "ん",
0x8340 : "ァ",
0x8341 : "ア",
0x8342 : "ィ",
0x8343 : "イ",
0x8344 : "ゥ",
0x8345 : "ウ",
0x8346 : "ェ",
0x8347 : "エ",
0x8348 : "ォ",
0x8349 : "オ",
0x834a : "カ",
0x834b : "ガ",
0x834c : "キ",
0x834d : "ギ",
0x834e : "ク",
0x834f : "グ",
0x8350 : "ケ",
0x8351 : "ゲ",
0x8352 : "コ",
0x8353 : "ゴ",
0x8354 : "サ",
0x8355 : "ザ",
0x8356 : "シ",
0x8357 : "ジ",
0x8358 : "ス",
0x8359 : "ズ",
0x835a : "セ",
0x835b : "ゼ",
0x835c : "ソ",
0x835d : "ゾ",
0x835e : "タ",
0x835f : "ダ",
0x8360 : "チ",
0x8361 : "ヂ",
0x8362 : "ッ",
0x8363 : "ツ",
0x8364 : "ヅ",
0x8365 : "テ",
0x8366 : "デ",
0x8367 : "ト",
0x8368 : "ド",
0x8369 : "ナ",
0x836a : "ニ",
0x836b : "ヌ",
0x836c : "ネ",
0x836d : "ノ",
0x836e : "ハ",
0x836f : "バ",
0x8370 : "パ",
0x8371 : "ヒ",
0x8372 : "ビ",
0x8373 : "ピ",
0x8374 : "フ",
0x8375 : "ブ",
0x8376 : "プ",
0x8377 : "ヘ",
0x8378 : "ベ",
0x8379 : "ペ",
0x837a : "ホ",
0x837b : "ボ",
0x837c : "ポ",
0x837d : "マ",
0x837e : "ミ",
0x8380 : "ム",
0x8381 : "メ",
0x8382 : "モ",
0x8383 : "ャ",
0x8384 : "ヤ",
0x8385 : "ュ",
0x8386 : "ユ",
0x8387 : "ョ",
0x8388 : "ヨ",
0x8389 : "ラ",
0x838a : "リ",
0x838b : "ル",
0x838c : "レ",
0x838d : "ロ",
0x838e : "ヮ",
0x838f : "ワ",
0x8390 : "ヰ",
0x8391 : "ヱ",
0x8392 : "ヲ",
0x8393 : "ン",
0x8394 : "ヴ",
0x8395 : "ヵ",
0x8396 : "ヶ",
0x839f : "Α",
0x83a0 : "Β",
0x83a1 : "Γ",
0x83a2 : "Δ",
0x83a3 : "Ε",
0x83a4 : "Ζ",
0x83a5 : "Η",
0x83a6 : "Θ",
0x83a7 : "Ι",
0x83a8 : "Κ",
0x83a9 : "Λ",
0x83aa : "Μ",
0x83ab : "Ν",
0x83ac : "Ξ",
0x83ad : "Ο",
0x83ae : "Π",
0x83af : "Ρ",
0x83b0 : "Σ",
0x83b1 : "Τ",
0x83b2 : "Υ",
0x83b3 : "Φ",
0x83b4 : "Χ",
0x83b5 : "Ψ",
0x83b6 : "Ω",
0x83bf : "α",
0x83c0 : "β",
0x83c1 : "γ",
0x83c2 : "δ",
0x83c3 : "ε",
0x83c4 : "ζ",
0x83c5 : "η",
0x83c6 : "θ",
0x83c7 : "ι",
0x83c8 : "κ",
0x83c9 : "λ",
0x83ca : "μ",
0x83cb : "ν",
0x83cc : "ξ",
0x83cd : "ο",
0x83ce : "π",
0x83cf : "ρ",
0x83d0 : "σ",
0x83d1 : "τ",
0x83d2 : "υ",
0x83d3 : "φ",
0x83d4 : "χ",
0x83d5 : "ψ",
0x83d6 : "ω",
0x8440 : "А",
0x8441 : "Б",
0x8442 : "В",
0x8443 : "Г",
0x8444 : "Д",
0x8445 : "Е",
0x8446 : "Ё",
0x8447 : "Ж",
0x8448 : "З",
0x8449 : "И",
0x844a : "Й",
0x844b : "К",
0x844c : "Л",
0x844d : "М",
0x844e : "Н",
0x844f : "О",
0x8450 : "П",
0x8451 : "Р",
0x8452 : "С",
0x8453 : "Т",
0x8454 : "У",
0x8455 : "Ф",
0x8456 : "Х",
0x8457 : "Ц",
0x8458 : "Ч",
0x8459 : "Ш",
0x845a : "Щ",
0x845b : "Ъ",
0x845c : "Ы",
0x845d : "Ь",
0x845e : "Э",
0x845f : "Ю",
0x8460 : "Я",
0x8470 : "а",
0x8471 : "б",
0x8472 : "в",
0x8473 : "г",
0x8474 : "д",
0x8475 : "е",
0x8476 : "ё",
0x8477 : "ж",
0x8478 : "з",
0x8479 : "и",
0x847a : "й",
0x847b : "к",
0x847c : "л",
0x847d : "м",
0x847e : "н",
0x8480 : "о",
0x8481 : "п",
0x8482 : "р",
0x8483 : "с",
0x8484 : "т",
0x8485 : "у",
0x8486 : "ф",
0x8487 : "х",
0x8488 : "ц",
0x8489 : "ч",
0x848a : "ш",
0x848b : "щ",
0x848c : "ъ",
0x848d : "ы",
0x848e : "ь",
0x848f : "э",
0x8490 : "ю",
0x8491 : "я",
0x849f : "─",
0x84a0 : "│",
0x84a1 : "┌",
0x84a2 : "┐",
0x84a3 : "┘",
0x84a4 : "└",
0x84a5 : "├",
0x84a6 : "┬",
0x84a7 : "┤",
0x84a8 : "┴",
0x84a9 : "┼",
0x84aa : "━",
0x84ab : "┃",
0x84ac : "┏",
0x84ad : "┓",
0x84ae : "┛",
0x84af : "┗",
0x84b0 : "┣",
0x84b1 : "┳",
0x84b2 : "┫",
0x84b3 : "┻",
0x84b4 : "╋",
0x84b5 : "┠",
0x84b6 : "┯",
0x84b7 : "┨",
0x84b8 : "┷",
0x84b9 : "┿",
0x84ba : "┝",
0x84bb : "┰",
0x84bc : "┥",
0x84bd : "┸",
0x84be : "╂",
0x889f : "亜",
0x88a0 : "唖",
0x88a1 : "娃",
0x88a2 : "阿",
0x88a3 : "哀",
0x88a4 : "愛",
0x88a5 : "挨",
0x88a6 : "姶",
0x88a7 : "逢",
0x88a8 : "葵",
0x88a9 : "茜",
0x88aa : "穐",
0x88ab : "悪",
0x88ac : "握",
0x88ad : "渥",
0x88ae : "旭",
0x88af : "葦",
0x88b0 : "芦",
0x88b1 : "鯵",
0x88b2 : "梓",
0x88b3 : "圧",
0x88b4 : "斡",
0x88b5 : "扱",
0x88b6 : "宛",
0x88b7 : "姐",
0x88b8 : "虻",
0x88b9 : "飴",
0x88ba : "絢",
0x88bb : "綾",
0x88bc : "鮎",
0x88bd : "或",
0x88be : "粟",
0x88bf : "袷",
0x88c0 : "安",
0x88c1 : "庵",
0x88c2 : "按",
0x88c3 : "暗",
0x88c4 : "案",
0x88c5 : "闇",
0x88c6 : "鞍",
0x88c7 : "杏",
0x88c8 : "以",
0x88c9 : "伊",
0x88ca : "位",
0x88cb : "依",
0x88cc : "偉",
0x88cd : "囲",
0x88ce : "夷",
0x88cf : "委",
0x88d0 : "威",
0x88d1 : "尉",
0x88d2 : "惟",
0x88d3 : "意",
0x88d4 : "慰",
0x88d5 : "易",
0x88d6 : "椅",
0x88d7 : "為",
0x88d8 : "畏",
0x88d9 : "異",
0x88da : "移",
0x88db : "維",
0x88dc : "緯",
0x88dd : "胃",
0x88de : "萎",
0x88df : "衣",
0x88e0 : "謂",
0x88e1 : "違",
0x88e2 : "遺",
0x88e3 : "医",
0x88e4 : "井",
0x88e5 : "亥",
0x88e6 : "域",
0x88e7 : "育",
0x88e8 : "郁",
0x88e9 : "磯",
0x88ea : "一",
0x88eb : "壱",
0x88ec : "溢",
0x88ed : "逸",
0x88ee : "稲",
0x88ef : "茨",
0x88f0 : "芋",
0x88f1 : "鰯",
0x88f2 : "允",
0x88f3 : "印",
0x88f4 : "咽",
0x88f5 : "員",
0x88f6 : "因",
0x88f7 : "姻",
0x88f8 : "引",
0x88f9 : "飲",
0x88fa : "淫",
0x88fb : "胤",
0x88fc : "蔭",
0x8940 : "院",
0x8941 : "陰",
0x8942 : "隠",
0x8943 : "韻",
0x8944 : "吋",
0x8945 : "右",
0x8946 : "宇",
0x8947 : "烏",
0x8948 : "羽",
0x8949 : "迂",
0x894a : "雨",
0x894b : "卯",
0x894c : "鵜",
0x894d : "窺",
0x894e : "丑",
0x894f : "碓",
0x8950 : "臼",
0x8951 : "渦",
0x8952 : "嘘",
0x8953 : "唄",
0x8954 : "欝",
0x8955 : "蔚",
0x8956 : "鰻",
0x8957 : "姥",
0x8958 : "厩",
0x8959 : "浦",
0x895a : "瓜",
0x895b : "閏",
0x895c : "噂",
0x895d : "云",
0x895e : "運",
0x895f : "雲",
0x8960 : "荏",
0x8961 : "餌",
0x8962 : "叡",
0x8963 : "営",
0x8964 : "嬰",
0x8965 : "影",
0x8966 : "映",
0x8967 : "曳",
0x8968 : "栄",
0x8969 : "永",
0x896a : "泳",
0x896b : "洩",
0x896c : "瑛",
0x896d : "盈",
0x896e : "穎",
0x896f : "頴",
0x8970 : "英",
0x8971 : "衛",
0x8972 : "詠",
0x8973 : "鋭",
0x8974 : "液",
0x8975 : "疫",
0x8976 : "益",
0x8977 : "駅",
0x8978 : "悦",
0x8979 : "謁",
0x897a : "越",
0x897b : "閲",
0x897c : "榎",
0x897d : "厭",
0x897e : "円",
0x8980 : "園",
0x8981 : "堰",
0x8982 : "奄",
0x8983 : "宴",
0x8984 : "延",
0x8985 : "怨",
0x8986 : "掩",
0x8987 : "援",
0x8988 : "沿",
0x8989 : "演",
0x898a : "炎",
0x898b : "焔",
0x898c : "煙",
0x898d : "燕",
0x898e : "猿",
0x898f : "縁",
0x8990 : "艶",
0x8991 : "苑",
0x8992 : "薗",
0x8993 : "遠",
0x8994 : "鉛",
0x8995 : "鴛",
0x8996 : "塩",
0x8997 : "於",
0x8998 : "汚",
0x8999 : "甥",
0x899a : "凹",
0x899b : "央",
0x899c : "奥",
0x899d : "往",
0x899e : "応",
0x899f : "押",
0x89a0 : "旺",
0x89a1 : "横",
0x89a2 : "欧",
0x89a3 : "殴",
0x89a4 : "王",
0x89a5 : "翁",
0x89a6 : "襖",
0x89a7 : "鴬",
0x89a8 : "鴎",
0x89a9 : "黄",
0x89aa : "岡",
0x89ab : "沖",
0x89ac : "荻",
0x89ad : "億",
0x89ae : "屋",
0x89af : "憶",
0x89b0 : "臆",
0x89b1 : "桶",
0x89b2 : "牡",
0x89b3 : "乙",
0x89b4 : "俺",
0x89b5 : "卸",
0x89b6 : "恩",
0x89b7 : "温",
0x89b8 : "穏",
0x89b9 : "音",
0x89ba : "下",
0x89bb : "化",
0x89bc : "仮",
0x89bd : "何",
0x89be : "伽",
0x89bf : "価",
0x89c0 : "佳",
0x89c1 : "加",
0x89c2 : "可",
0x89c3 : "嘉",
0x89c4 : "夏",
0x89c5 : "嫁",
0x89c6 : "家",
0x89c7 : "寡",
0x89c8 : "科",
0x89c9 : "暇",
0x89ca : "果",
0x89cb : "架",
0x89cc : "歌",
0x89cd : "河",
0x89ce : "火",
0x89cf : "珂",
0x89d0 : "禍",
0x89d1 : "禾",
0x89d2 : "稼",
0x89d3 : "箇",
0x89d4 : "花",
0x89d5 : "苛",
0x89d6 : "茄",
0x89d7 : "荷",
0x89d8 : "華",
0x89d9 : "菓",
0x89da : "蝦",
0x89db : "課",
0x89dc : "嘩",
0x89dd : "貨",
0x89de : "迦",
0x89df : "過",
0x89e0 : "霞",
0x89e1 : "蚊",
0x89e2 : "俄",
0x89e3 : "峨",
0x89e4 : "我",
0x89e5 : "牙",
0x89e6 : "画",
0x89e7 : "臥",
0x89e8 : "芽",
0x89e9 : "蛾",
0x89ea : "賀",
0x89eb : "雅",
0x89ec : "餓",
0x89ed : "駕",
0x89ee : "介",
0x89ef : "会",
0x89f0 : "解",
0x89f1 : "回",
0x89f2 : "塊",
0x89f3 : "壊",
0x89f4 : "廻",
0x89f5 : "快",
0x89f6 : "怪",
0x89f7 : "悔",
0x89f8 : "恢",
0x89f9 : "懐",
0x89fa : "戒",
0x89fb : "拐",
0x89fc : "改",
0x8a40 : "魁",
0x8a41 : "晦",
0x8a42 : "械",
0x8a43 : "海",
0x8a44 : "灰",
0x8a45 : "界",
0x8a46 : "皆",
0x8a47 : "絵",
0x8a48 : "芥",
0x8a49 : "蟹",
0x8a4a : "開",
0x8a4b : "階",
0x8a4c : "貝",
0x8a4d : "凱",
0x8a4e : "劾",
0x8a4f : "外",
0x8a50 : "咳",
0x8a51 : "害",
0x8a52 : "崖",
0x8a53 : "慨",
0x8a54 : "概",
0x8a55 : "涯",
0x8a56 : "碍",
0x8a57 : "蓋",
0x8a58 : "街",
0x8a59 : "該",
0x8a5a : "鎧",
0x8a5b : "骸",
0x8a5c : "浬",
0x8a5d : "馨",
0x8a5e : "蛙",
0x8a5f : "垣",
0x8a60 : "柿",
0x8a61 : "蛎",
0x8a62 : "鈎",
0x8a63 : "劃",
0x8a64 : "嚇",
0x8a65 : "各",
0x8a66 : "廓",
0x8a67 : "拡",
0x8a68 : "撹",
0x8a69 : "格",
0x8a6a : "核",
0x8a6b : "殻",
0x8a6c : "獲",
0x8a6d : "確",
0x8a6e : "穫",
0x8a6f : "覚",
0x8a70 : "角",
0x8a71 : "赫",
0x8a72 : "較",
0x8a73 : "郭",
0x8a74 : "閣",
0x8a75 : "隔",
0x8a76 : "革",
0x8a77 : "学",
0x8a78 : "岳",
0x8a79 : "楽",
0x8a7a : "額",
0x8a7b : "顎",
0x8a7c : "掛",
0x8a7d : "笠",
0x8a7e : "樫",
0x8a80 : "橿",
0x8a81 : "梶",
0x8a82 : "鰍",
0x8a83 : "潟",
0x8a84 : "割",
0x8a85 : "喝",
0x8a86 : "恰",
0x8a87 : "括",
0x8a88 : "活",
0x8a89 : "渇",
0x8a8a : "滑",
0x8a8b : "葛",
0x8a8c : "褐",
0x8a8d : "轄",
0x8a8e : "且",
0x8a8f : "鰹",
0x8a90 : "叶",
0x8a91 : "椛",
0x8a92 : "樺",
0x8a93 : "鞄",
0x8a94 : "株",
0x8a95 : "兜",
0x8a96 : "竃",
0x8a97 : "蒲",
0x8a98 : "釜",
0x8a99 : "鎌",
0x8a9a : "噛",
0x8a9b : "鴨",
0x8a9c : "栢",
0x8a9d : "茅",
0x8a9e : "萱",
0x8a9f : "粥",
0x8aa0 : "刈",
0x8aa1 : "苅",
0x8aa2 : "瓦",
0x8aa3 : "乾",
0x8aa4 : "侃",
0x8aa5 : "冠",
0x8aa6 : "寒",
0x8aa7 : "刊",
0x8aa8 : "勘",
0x8aa9 : "勧",
0x8aaa : "巻",
0x8aab : "喚",
0x8aac : "堪",
0x8aad : "姦",
0x8aae : "完",
0x8aaf : "官",
0x8ab0 : "寛",
0x8ab1 : "干",
0x8ab2 : "幹",
0x8ab3 : "患",
0x8ab4 : "感",
0x8ab5 : "慣",
0x8ab6 : "憾",
0x8ab7 : "換",
0x8ab8 : "敢",
0x8ab9 : "柑",
0x8aba : "桓",
0x8abb : "棺",
0x8abc : "款",
0x8abd : "歓",
0x8abe : "汗",
0x8abf : "漢",
0x8ac0 : "澗",
0x8ac1 : "潅",
0x8ac2 : "環",
0x8ac3 : "甘",
0x8ac4 : "監",
0x8ac5 : "看",
0x8ac6 : "竿",
0x8ac7 : "管",
0x8ac8 : "簡",
0x8ac9 : "緩",
0x8aca : "缶",
0x8acb : "翰",
0x8acc : "肝",
0x8acd : "艦",
0x8ace : "莞",
0x8acf : "観",
0x8ad0 : "諌",
0x8ad1 : "貫",
0x8ad2 : "還",
0x8ad3 : "鑑",
0x8ad4 : "間",
0x8ad5 : "閑",
0x8ad6 : "関",
0x8ad7 : "陥",
0x8ad8 : "韓",
0x8ad9 : "館",
0x8ada : "舘",
0x8adb : "丸",
0x8adc : "含",
0x8add : "岸",
0x8ade : "巌",
0x8adf : "玩",
0x8ae0 : "癌",
0x8ae1 : "眼",
0x8ae2 : "岩",
0x8ae3 : "翫",
0x8ae4 : "贋",
0x8ae5 : "雁",
0x8ae6 : "頑",
0x8ae7 : "顔",
0x8ae8 : "願",
0x8ae9 : "企",
0x8aea : "伎",
0x8aeb : "危",
0x8aec : "喜",
0x8aed : "器",
0x8aee : "基",
0x8aef : "奇",
0x8af0 : "嬉",
0x8af1 : "寄",
0x8af2 : "岐",
0x8af3 : "希",
0x8af4 : "幾",
0x8af5 : "忌",
0x8af6 : "揮",
0x8af7 : "机",
0x8af8 : "旗",
0x8af9 : "既",
0x8afa : "期",
0x8afb : "棋",
0x8afc : "棄",
0x8b40 : "機",
0x8b41 : "帰",
0x8b42 : "毅",
0x8b43 : "気",
0x8b44 : "汽",
0x8b45 : "畿",
0x8b46 : "祈",
0x8b47 : "季",
0x8b48 : "稀",
0x8b49 : "紀",
0x8b4a : "徽",
0x8b4b : "規",
0x8b4c : "記",
0x8b4d : "貴",
0x8b4e : "起",
0x8b4f : "軌",
0x8b50 : "輝",
0x8b51 : "飢",
0x8b52 : "騎",
0x8b53 : "鬼",
0x8b54 : "亀",
0x8b55 : "偽",
0x8b56 : "儀",
0x8b57 : "妓",
0x8b58 : "宜",
0x8b59 : "戯",
0x8b5a : "技",
0x8b5b : "擬",
0x8b5c : "欺",
0x8b5d : "犠",
0x8b5e : "疑",
0x8b5f : "祇",
0x8b60 : "義",
0x8b61 : "蟻",
0x8b62 : "誼",
0x8b63 : "議",
0x8b64 : "掬",
0x8b65 : "菊",
0x8b66 : "鞠",
0x8b67 : "吉",
0x8b68 : "吃",
0x8b69 : "喫",
0x8b6a : "桔",
0x8b6b : "橘",
0x8b6c : "詰",
0x8b6d : "砧",
0x8b6e : "杵",
0x8b6f : "黍",
0x8b70 : "却",
0x8b71 : "客",
0x8b72 : "脚",
0x8b73 : "虐",
0x8b74 : "逆",
0x8b75 : "丘",
0x8b76 : "久",
0x8b77 : "仇",
0x8b78 : "休",
0x8b79 : "及",
0x8b7a : "吸",
0x8b7b : "宮",
0x8b7c : "弓",
0x8b7d : "急",
0x8b7e : "救",
0x8b80 : "朽",
0x8b81 : "求",
0x8b82 : "汲",
0x8b83 : "泣",
0x8b84 : "灸",
0x8b85 : "球",
0x8b86 : "究",
0x8b87 : "窮",
0x8b88 : "笈",
0x8b89 : "級",
0x8b8a : "糾",
0x8b8b : "給",
0x8b8c : "旧",
0x8b8d : "牛",
0x8b8e : "去",
0x8b8f : "居",
0x8b90 : "巨",
0x8b91 : "拒",
0x8b92 : "拠",
0x8b93 : "挙",
0x8b94 : "渠",
0x8b95 : "虚",
0x8b96 : "許",
0x8b97 : "距",
0x8b98 : "鋸",
0x8b99 : "漁",
0x8b9a : "禦",
0x8b9b : "魚",
0x8b9c : "亨",
0x8b9d : "享",
0x8b9e : "京",
0x8b9f : "供",
0x8ba0 : "侠",
0x8ba1 : "僑",
0x8ba2 : "兇",
0x8ba3 : "競",
0x8ba4 : "共",
0x8ba5 : "凶",
0x8ba6 : "協",
0x8ba7 : "匡",
0x8ba8 : "卿",
0x8ba9 : "叫",
0x8baa : "喬",
0x8bab : "境",
0x8bac : "峡",
0x8bad : "強",
0x8bae : "彊",
0x8baf : "怯",
0x8bb0 : "恐",
0x8bb1 : "恭",
0x8bb2 : "挟",
0x8bb3 : "教",
0x8bb4 : "橋",
0x8bb5 : "況",
0x8bb6 : "狂",
0x8bb7 : "狭",
0x8bb8 : "矯",
0x8bb9 : "胸",
0x8bba : "脅",
0x8bbb : "興",
0x8bbc : "蕎",
0x8bbd : "郷",
0x8bbe : "鏡",
0x8bbf : "響",
0x8bc0 : "饗",
0x8bc1 : "驚",
0x8bc2 : "仰",
0x8bc3 : "凝",
0x8bc4 : "尭",
0x8bc5 : "暁",
0x8bc6 : "業",
0x8bc7 : "局",
0x8bc8 : "曲",
0x8bc9 : "極",
0x8bca : "玉",
0x8bcb : "桐",
0x8bcc : "粁",
0x8bcd : "僅",
0x8bce : "勤",
0x8bcf : "均",
0x8bd0 : "巾",
0x8bd1 : "錦",
0x8bd2 : "斤",
0x8bd3 : "欣",
0x8bd4 : "欽",
0x8bd5 : "琴",
0x8bd6 : "禁",
0x8bd7 : "禽",
0x8bd8 : "筋",
0x8bd9 : "緊",
0x8bda : "芹",
0x8bdb : "菌",
0x8bdc : "衿",
0x8bdd : "襟",
0x8bde : "謹",
0x8bdf : "近",
0x8be0 : "金",
0x8be1 : "吟",
0x8be2 : "銀",
0x8be3 : "九",
0x8be4 : "倶",
0x8be5 : "句",
0x8be6 : "区",
0x8be7 : "狗",
0x8be8 : "玖",
0x8be9 : "矩",
0x8bea : "苦",
0x8beb : "躯",
0x8bec : "駆",
0x8bed : "駈",
0x8bee : "駒",
0x8bef : "具",
0x8bf0 : "愚",
0x8bf1 : "虞",
0x8bf2 : "喰",
0x8bf3 : "空",
0x8bf4 : "偶",
0x8bf5 : "寓",
0x8bf6 : "遇",
0x8bf7 : "隅",
0x8bf8 : "串",
0x8bf9 : "櫛",
0x8bfa : "釧",
0x8bfb : "屑",
0x8bfc : "屈",
0x8c40 : "掘",
0x8c41 : "窟",
0x8c42 : "沓",
0x8c43 : "靴",
0x8c44 : "轡",
0x8c45 : "窪",
0x8c46 : "熊",
0x8c47 : "隈",
0x8c48 : "粂",
0x8c49 : "栗",
0x8c4a : "繰",
0x8c4b : "桑",
0x8c4c : "鍬",
0x8c4d : "勲",
0x8c4e : "君",
0x8c4f : "薫",
0x8c50 : "訓",
0x8c51 : "群",
0x8c52 : "軍",
0x8c53 : "郡",
0x8c54 : "卦",
0x8c55 : "袈",
0x8c56 : "祁",
0x8c57 : "係",
0x8c58 : "傾",
0x8c59 : "刑",
0x8c5a : "兄",
0x8c5b : "啓",
0x8c5c : "圭",
0x8c5d : "珪",
0x8c5e : "型",
0x8c5f : "契",
0x8c60 : "形",
0x8c61 : "径",
0x8c62 : "恵",
0x8c63 : "慶",
0x8c64 : "慧",
0x8c65 : "憩",
0x8c66 : "掲",
0x8c67 : "携",
0x8c68 : "敬",
0x8c69 : "景",
0x8c6a : "桂",
0x8c6b : "渓",
0x8c6c : "畦",
0x8c6d : "稽",
0x8c6e : "系",
0x8c6f : "経",
0x8c70 : "継",
0x8c71 : "繋",
0x8c72 : "罫",
0x8c73 : "茎",
0x8c74 : "荊",
0x8c75 : "蛍",
0x8c76 : "計",
0x8c77 : "詣",
0x8c78 : "警",
0x8c79 : "軽",
0x8c7a : "頚",
0x8c7b : "鶏",
0x8c7c : "芸",
0x8c7d : "迎",
0x8c7e : "鯨",
0x8c80 : "劇",
0x8c81 : "戟",
0x8c82 : "撃",
0x8c83 : "激",
0x8c84 : "隙",
0x8c85 : "桁",
0x8c86 : "傑",
0x8c87 : "欠",
0x8c88 : "決",
0x8c89 : "潔",
0x8c8a : "穴",
0x8c8b : "結",
0x8c8c : "血",
0x8c8d : "訣",
0x8c8e : "月",
0x8c8f : "件",
0x8c90 : "倹",
0x8c91 : "倦",
0x8c92 : "健",
0x8c93 : "兼",
0x8c94 : "券",
0x8c95 : "剣",
0x8c96 : "喧",
0x8c97 : "圏",
0x8c98 : "堅",
0x8c99 : "嫌",
0x8c9a : "建",
0x8c9b : "憲",
0x8c9c : "懸",
0x8c9d : "拳",
0x8c9e : "捲",
0x8c9f : "検",
0x8ca0 : "権",
0x8ca1 : "牽",
0x8ca2 : "犬",
0x8ca3 : "献",
0x8ca4 : "研",
0x8ca5 : "硯",
0x8ca6 : "絹",
0x8ca7 : "県",
0x8ca8 : "肩",
0x8ca9 : "見",
0x8caa : "謙",
0x8cab : "賢",
0x8cac : "軒",
0x8cad : "遣",
0x8cae : "鍵",
0x8caf : "険",
0x8cb0 : "顕",
0x8cb1 : "験",
0x8cb2 : "鹸",
0x8cb3 : "元",
0x8cb4 : "原",
0x8cb5 : "厳",
0x8cb6 : "幻",
0x8cb7 : "弦",
0x8cb8 : "減",
0x8cb9 : "源",
0x8cba : "玄",
0x8cbb : "現",
0x8cbc : "絃",
0x8cbd : "舷",
0x8cbe : "言",
0x8cbf : "諺",
0x8cc0 : "限",
0x8cc1 : "乎",
0x8cc2 : "個",
0x8cc3 : "古",
0x8cc4 : "呼",
0x8cc5 : "固",
0x8cc6 : "姑",
0x8cc7 : "孤",
0x8cc8 : "己",
0x8cc9 : "庫",
0x8cca : "弧",
0x8ccb : "戸",
0x8ccc : "故",
0x8ccd : "枯",
0x8cce : "湖",
0x8ccf : "狐",
0x8cd0 : "糊",
0x8cd1 : "袴",
0x8cd2 : "股",
0x8cd3 : "胡",
0x8cd4 : "菰",
0x8cd5 : "虎",
0x8cd6 : "誇",
0x8cd7 : "跨",
0x8cd8 : "鈷",
0x8cd9 : "雇",
0x8cda : "顧",
0x8cdb : "鼓",
0x8cdc : "五",
0x8cdd : "互",
0x8cde : "伍",
0x8cdf : "午",
0x8ce0 : "呉",
0x8ce1 : "吾",
0x8ce2 : "娯",
0x8ce3 : "後",
0x8ce4 : "御",
0x8ce5 : "悟",
0x8ce6 : "梧",
0x8ce7 : "檎",
0x8ce8 : "瑚",
0x8ce9 : "碁",
0x8cea : "語",
0x8ceb : "誤",
0x8cec : "護",
0x8ced : "醐",
0x8cee : "乞",
0x8cef : "鯉",
0x8cf0 : "交",
0x8cf1 : "佼",
0x8cf2 : "侯",
0x8cf3 : "候",
0x8cf4 : "倖",
0x8cf5 : "光",
0x8cf6 : "公",
0x8cf7 : "功",
0x8cf8 : "効",
0x8cf9 : "勾",
0x8cfa : "厚",
0x8cfb : "口",
0x8cfc : "向",
0x8d40 : "后",
0x8d41 : "喉",
0x8d42 : "坑",
0x8d43 : "垢",
0x8d44 : "好",
0x8d45 : "孔",
0x8d46 : "孝",
0x8d47 : "宏",
0x8d48 : "工",
0x8d49 : "巧",
0x8d4a : "巷",
0x8d4b : "幸",
0x8d4c : "広",
0x8d4d : "庚",
0x8d4e : "康",
0x8d4f : "弘",
0x8d50 : "恒",
0x8d51 : "慌",
0x8d52 : "抗",
0x8d53 : "拘",
0x8d54 : "控",
0x8d55 : "攻",
0x8d56 : "昂",
0x8d57 : "晃",
0x8d58 : "更",
0x8d59 : "杭",
0x8d5a : "校",
0x8d5b : "梗",
0x8d5c : "構",
0x8d5d : "江",
0x8d5e : "洪",
0x8d5f : "浩",
0x8d60 : "港",
0x8d61 : "溝",
0x8d62 : "甲",
0x8d63 : "皇",
0x8d64 : "硬",
0x8d65 : "稿",
0x8d66 : "糠",
0x8d67 : "紅",
0x8d68 : "紘",
0x8d69 : "絞",
0x8d6a : "綱",
0x8d6b : "耕",
0x8d6c : "考",
0x8d6d : "肯",
0x8d6e : "肱",
0x8d6f : "腔",
0x8d70 : "膏",
0x8d71 : "航",
0x8d72 : "荒",
0x8d73 : "行",
0x8d74 : "衡",
0x8d75 : "講",
0x8d76 : "貢",
0x8d77 : "購",
0x8d78 : "郊",
0x8d79 : "酵",
0x8d7a : "鉱",
0x8d7b : "砿",
0x8d7c : "鋼",
0x8d7d : "閤",
0x8d7e : "降",
0x8d80 : "項",
0x8d81 : "香",
0x8d82 : "高",
0x8d83 : "鴻",
0x8d84 : "剛",
0x8d85 : "劫",
0x8d86 : "号",
0x8d87 : "合",
0x8d88 : "壕",
0x8d89 : "拷",
0x8d8a : "濠",
0x8d8b : "豪",
0x8d8c : "轟",
0x8d8d : "麹",
0x8d8e : "克",
0x8d8f : "刻",
0x8d90 : "告",
0x8d91 : "国",
0x8d92 : "穀",
0x8d93 : "酷",
0x8d94 : "鵠",
0x8d95 : "黒",
0x8d96 : "獄",
0x8d97 : "漉",
0x8d98 : "腰",
0x8d99 : "甑",
0x8d9a : "忽",
0x8d9b : "惚",
0x8d9c : "骨",
0x8d9d : "狛",
0x8d9e : "込",
0x8d9f : "此",
0x8da0 : "頃",
0x8da1 : "今",
0x8da2 : "困",
0x8da3 : "坤",
0x8da4 : "墾",
0x8da5 : "婚",
0x8da6 : "恨",
0x8da7 : "懇",
0x8da8 : "昏",
0x8da9 : "昆",
0x8daa : "根",
0x8dab : "梱",
0x8dac : "混",
0x8dad : "痕",
0x8dae : "紺",
0x8daf : "艮",
0x8db0 : "魂",
0x8db1 : "些",
0x8db2 : "佐",
0x8db3 : "叉",
0x8db4 : "唆",
0x8db5 : "嵯",
0x8db6 : "左",
0x8db7 : "差",
0x8db8 : "査",
0x8db9 : "沙",
0x8dba : "瑳",
0x8dbb : "砂",
0x8dbc : "詐",
0x8dbd : "鎖",
0x8dbe : "裟",
0x8dbf : "坐",
0x8dc0 : "座",
0x8dc1 : "挫",
0x8dc2 : "債",
0x8dc3 : "催",
0x8dc4 : "再",
0x8dc5 : "最",
0x8dc6 : "哉",
0x8dc7 : "塞",
0x8dc8 : "妻",
0x8dc9 : "宰",
0x8dca : "彩",
0x8dcb : "才",
0x8dcc : "採",
0x8dcd : "栽",
0x8dce : "歳",
0x8dcf : "済",
0x8dd0 : "災",
0x8dd1 : "采",
0x8dd2 : "犀",
0x8dd3 : "砕",
0x8dd4 : "砦",
0x8dd5 : "祭",
0x8dd6 : "斎",
0x8dd7 : "細",
0x8dd8 : "菜",
0x8dd9 : "裁",
0x8dda : "載",
0x8ddb : "際",
0x8ddc : "剤",
0x8ddd : "在",
0x8dde : "材",
0x8ddf : "罪",
0x8de0 : "財",
0x8de1 : "冴",
0x8de2 : "坂",
0x8de3 : "阪",
0x8de4 : "堺",
0x8de5 : "榊",
0x8de6 : "肴",
0x8de7 : "咲",
0x8de8 : "崎",
0x8de9 : "埼",
0x8dea : "碕",
0x8deb : "鷺",
0x8dec : "作",
0x8ded : "削",
0x8dee : "咋",
0x8def : "搾",
0x8df0 : "昨",
0x8df1 : "朔",
0x8df2 : "柵",
0x8df3 : "窄",
0x8df4 : "策",
0x8df5 : "索",
0x8df6 : "錯",
0x8df7 : "桜",
0x8df8 : "鮭",
0x8df9 : "笹",
0x8dfa : "匙",
0x8dfb : "冊",
0x8dfc : "刷",
0x8e40 : "察",
0x8e41 : "拶",
0x8e42 : "撮",
0x8e43 : "擦",
0x8e44 : "札",
0x8e45 : "殺",
0x8e46 : "薩",
0x8e47 : "雑",
0x8e48 : "皐",
0x8e49 : "鯖",
0x8e4a : "捌",
0x8e4b : "錆",
0x8e4c : "鮫",
0x8e4d : "皿",
0x8e4e : "晒",
0x8e4f : "三",
0x8e50 : "傘",
0x8e51 : "参",
0x8e52 : "山",
0x8e53 : "惨",
0x8e54 : "撒",
0x8e55 : "散",
0x8e56 : "桟",
0x8e57 : "燦",
0x8e58 : "珊",
0x8e59 : "産",
0x8e5a : "算",
0x8e5b : "纂",
0x8e5c : "蚕",
0x8e5d : "讃",
0x8e5e : "賛",
0x8e5f : "酸",
0x8e60 : "餐",
0x8e61 : "斬",
0x8e62 : "暫",
0x8e63 : "残",
0x8e64 : "仕",
0x8e65 : "仔",
0x8e66 : "伺",
0x8e67 : "使",
0x8e68 : "刺",
0x8e69 : "司",
0x8e6a : "史",
0x8e6b : "嗣",
0x8e6c : "四",
0x8e6d : "士",
0x8e6e : "始",
0x8e6f : "姉",
0x8e70 : "姿",
0x8e71 : "子",
0x8e72 : "屍",
0x8e73 : "市",
0x8e74 : "師",
0x8e75 : "志",
0x8e76 : "思",
0x8e77 : "指",
0x8e78 : "支",
0x8e79 : "孜",
0x8e7a : "斯",
0x8e7b : "施",
0x8e7c : "旨",
0x8e7d : "枝",
0x8e7e : "止",
0x8e80 : "死",
0x8e81 : "氏",
0x8e82 : "獅",
0x8e83 : "祉",
0x8e84 : "私",
0x8e85 : "糸",
0x8e86 : "紙",
0x8e87 : "紫",
0x8e88 : "肢",
0x8e89 : "脂",
0x8e8a : "至",
0x8e8b : "視",
0x8e8c : "詞",
0x8e8d : "詩",
0x8e8e : "試",
0x8e8f : "誌",
0x8e90 : "諮",
0x8e91 : "資",
0x8e92 : "賜",
0x8e93 : "雌",
0x8e94 : "飼",
0x8e95 : "歯",
0x8e96 : "事",
0x8e97 : "似",
0x8e98 : "侍",
0x8e99 : "児",
0x8e9a : "字",
0x8e9b : "寺",
0x8e9c : "慈",
0x8e9d : "持",
0x8e9e : "時",
0x8e9f : "次",
0x8ea0 : "滋",
0x8ea1 : "治",
0x8ea2 : "爾",
0x8ea3 : "璽",
0x8ea4 : "痔",
0x8ea5 : "磁",
0x8ea6 : "示",
0x8ea7 : "而",
0x8ea8 : "耳",
0x8ea9 : "自",
0x8eaa : "蒔",
0x8eab : "辞",
0x8eac : "汐",
0x8ead : "鹿",
0x8eae : "式",
0x8eaf : "識",
0x8eb0 : "鴫",
0x8eb1 : "竺",
0x8eb2 : "軸",
0x8eb3 : "宍",
0x8eb4 : "雫",
0x8eb5 : "七",
0x8eb6 : "叱",
0x8eb7 : "執",
0x8eb8 : "失",
0x8eb9 : "嫉",
0x8eba : "室",
0x8ebb : "悉",
0x8ebc : "湿",
0x8ebd : "漆",
0x8ebe : "疾",
0x8ebf : "質",
0x8ec0 : "実",
0x8ec1 : "蔀",
0x8ec2 : "篠",
0x8ec3 : "偲",
0x8ec4 : "柴",
0x8ec5 : "芝",
0x8ec6 : "屡",
0x8ec7 : "蕊",
0x8ec8 : "縞",
0x8ec9 : "舎",
0x8eca : "写",
0x8ecb : "射",
0x8ecc : "捨",
0x8ecd : "赦",
0x8ece : "斜",
0x8ecf : "煮",
0x8ed0 : "社",
0x8ed1 : "紗",
0x8ed2 : "者",
0x8ed3 : "謝",
0x8ed4 : "車",
0x8ed5 : "遮",
0x8ed6 : "蛇",
0x8ed7 : "邪",
0x8ed8 : "借",
0x8ed9 : "勺",
0x8eda : "尺",
0x8edb : "杓",
0x8edc : "灼",
0x8edd : "爵",
0x8ede : "酌",
0x8edf : "釈",
0x8ee0 : "錫",
0x8ee1 : "若",
0x8ee2 : "寂",
0x8ee3 : "弱",
0x8ee4 : "惹",
0x8ee5 : "主",
0x8ee6 : "取",
0x8ee7 : "守",
0x8ee8 : "手",
0x8ee9 : "朱",
0x8eea : "殊",
0x8eeb : "狩",
0x8eec : "珠",
0x8eed : "種",
0x8eee : "腫",
0x8eef : "趣",
0x8ef0 : "酒",
0x8ef1 : "首",
0x8ef2 : "儒",
0x8ef3 : "受",
0x8ef4 : "呪",
0x8ef5 : "寿",
0x8ef6 : "授",
0x8ef7 : "樹",
0x8ef8 : "綬",
0x8ef9 : "需",
0x8efa : "囚",
0x8efb : "収",
0x8efc : "周",
0x8f40 : "宗",
0x8f41 : "就",
0x8f42 : "州",
0x8f43 : "修",
0x8f44 : "愁",
0x8f45 : "拾",
0x8f46 : "洲",
0x8f47 : "秀",
0x8f48 : "秋",
0x8f49 : "終",
0x8f4a : "繍",
0x8f4b : "習",
0x8f4c : "臭",
0x8f4d : "舟",
0x8f4e : "蒐",
0x8f4f : "衆",
0x8f50 : "襲",
0x8f51 : "讐",
0x8f52 : "蹴",
0x8f53 : "輯",
0x8f54 : "週",
0x8f55 : "酋",
0x8f56 : "酬",
0x8f57 : "集",
0x8f58 : "醜",
0x8f59 : "什",
0x8f5a : "住",
0x8f5b : "充",
0x8f5c : "十",
0x8f5d : "従",
0x8f5e : "戎",
0x8f5f : "柔",
0x8f60 : "汁",
0x8f61 : "渋",
0x8f62 : "獣",
0x8f63 : "縦",
0x8f64 : "重",
0x8f65 : "銃",
0x8f66 : "叔",
0x8f67 : "夙",
0x8f68 : "宿",
0x8f69 : "淑",
0x8f6a : "祝",
0x8f6b : "縮",
0x8f6c : "粛",
0x8f6d : "塾",
0x8f6e : "熟",
0x8f6f : "出",
0x8f70 : "術",
0x8f71 : "述",
0x8f72 : "俊",
0x8f73 : "峻",
0x8f74 : "春",
0x8f75 : "瞬",
0x8f76 : "竣",
0x8f77 : "舜",
0x8f78 : "駿",
0x8f79 : "准",
0x8f7a : "循",
0x8f7b : "旬",
0x8f7c : "楯",
0x8f7d : "殉",
0x8f7e : "淳",
0x8f80 : "準",
0x8f81 : "潤",
0x8f82 : "盾",
0x8f83 : "純",
0x8f84 : "巡",
0x8f85 : "遵",
0x8f86 : "醇",
0x8f87 : "順",
0x8f88 : "処",
0x8f89 : "初",
0x8f8a : "所",
0x8f8b : "暑",
0x8f8c : "曙",
0x8f8d : "渚",
0x8f8e : "庶",
0x8f8f : "緒",
0x8f90 : "署",
0x8f91 : "書",
0x8f92 : "薯",
0x8f93 : "藷",
0x8f94 : "諸",
0x8f95 : "助",
0x8f96 : "叙",
0x8f97 : "女",
0x8f98 : "序",
0x8f99 : "徐",
0x8f9a : "恕",
0x8f9b : "鋤",
0x8f9c : "除",
0x8f9d : "傷",
0x8f9e : "償",
0x8f9f : "勝",
0x8fa0 : "匠",
0x8fa1 : "升",
0x8fa2 : "召",
0x8fa3 : "哨",
0x8fa4 : "商",
0x8fa5 : "唱",
0x8fa6 : "嘗",
0x8fa7 : "奨",
0x8fa8 : "妾",
0x8fa9 : "娼",
0x8faa : "宵",
0x8fab : "将",
0x8fac : "小",
0x8fad : "少",
0x8fae : "尚",
0x8faf : "庄",
0x8fb0 : "床",
0x8fb1 : "廠",
0x8fb2 : "彰",
0x8fb3 : "承",
0x8fb4 : "抄",
0x8fb5 : "招",
0x8fb6 : "掌",
0x8fb7 : "捷",
0x8fb8 : "昇",
0x8fb9 : "昌",
0x8fba : "昭",
0x8fbb : "晶",
0x8fbc : "松",
0x8fbd : "梢",
0x8fbe : "樟",
0x8fbf : "樵",
0x8fc0 : "沼",
0x8fc1 : "消",
0x8fc2 : "渉",
0x8fc3 : "湘",
0x8fc4 : "焼",
0x8fc5 : "焦",
0x8fc6 : "照",
0x8fc7 : "症",
0x8fc8 : "省",
0x8fc9 : "硝",
0x8fca : "礁",
0x8fcb : "祥",
0x8fcc : "称",
0x8fcd : "章",
0x8fce : "笑",
0x8fcf : "粧",
0x8fd0 : "紹",
0x8fd1 : "肖",
0x8fd2 : "菖",
0x8fd3 : "蒋",
0x8fd4 : "蕉",
0x8fd5 : "衝",
0x8fd6 : "裳",
0x8fd7 : "訟",
0x8fd8 : "証",
0x8fd9 : "詔",
0x8fda : "詳",
0x8fdb : "象",
0x8fdc : "賞",
0x8fdd : "醤",
0x8fde : "鉦",
0x8fdf : "鍾",
0x8fe0 : "鐘",
0x8fe1 : "障",
0x8fe2 : "鞘",
0x8fe3 : "上",
0x8fe4 : "丈",
0x8fe5 : "丞",
0x8fe6 : "乗",
0x8fe7 : "冗",
0x8fe8 : "剰",
0x8fe9 : "城",
0x8fea : "場",
0x8feb : "壌",
0x8fec : "嬢",
0x8fed : "常",
0x8fee : "情",
0x8fef : "擾",
0x8ff0 : "条",
0x8ff1 : "杖",
0x8ff2 : "浄",
0x8ff3 : "状",
0x8ff4 : "畳",
0x8ff5 : "穣",
0x8ff6 : "蒸",
0x8ff7 : "譲",
0x8ff8 : "醸",
0x8ff9 : "錠",
0x8ffa : "嘱",
0x8ffb : "埴",
0x8ffc : "飾",
0x9040 : "拭",
0x9041 : "植",
0x9042 : "殖",
0x9043 : "燭",
0x9044 : "織",
0x9045 : "職",
0x9046 : "色",
0x9047 : "触",
0x9048 : "食",
0x9049 : "蝕",
0x904a : "辱",
0x904b : "尻",
0x904c : "伸",
0x904d : "信",
0x904e : "侵",
0x904f : "唇",
0x9050 : "娠",
0x9051 : "寝",
0x9052 : "審",
0x9053 : "心",
0x9054 : "慎",
0x9055 : "振",
0x9056 : "新",
0x9057 : "晋",
0x9058 : "森",
0x9059 : "榛",
0x905a : "浸",
0x905b : "深",
0x905c : "申",
0x905d : "疹",
0x905e : "真",
0x905f : "神",
0x9060 : "秦",
0x9061 : "紳",
0x9062 : "臣",
0x9063 : "芯",
0x9064 : "薪",
0x9065 : "親",
0x9066 : "診",
0x9067 : "身",
0x9068 : "辛",
0x9069 : "進",
0x906a : "針",
0x906b : "震",
0x906c : "人",
0x906d : "仁",
0x906e : "刃",
0x906f : "塵",
0x9070 : "壬",
0x9071 : "尋",
0x9072 : "甚",
0x9073 : "尽",
0x9074 : "腎",
0x9075 : "訊",
0x9076 : "迅",
0x9077 : "陣",
0x9078 : "靭",
0x9079 : "笥",
0x907a : "諏",
0x907b : "須",
0x907c : "酢",
0x907d : "図",
0x907e : "厨",
0x9080 : "逗",
0x9081 : "吹",
0x9082 : "垂",
0x9083 : "帥",
0x9084 : "推",
0x9085 : "水",
0x9086 : "炊",
0x9087 : "睡",
0x9088 : "粋",
0x9089 : "翠",
0x908a : "衰",
0x908b : "遂",
0x908c : "酔",
0x908d : "錐",
0x908e : "錘",
0x908f : "随",
0x9090 : "瑞",
0x9091 : "髄",
0x9092 : "崇",
0x9093 : "嵩",
0x9094 : "数",
0x9095 : "枢",
0x9096 : "趨",
0x9097 : "雛",
0x9098 : "据",
0x9099 : "杉",
0x909a : "椙",
0x909b : "菅",
0x909c : "頗",
0x909d : "雀",
0x909e : "裾",
0x909f : "澄",
0x90a0 : "摺",
0x90a1 : "寸",
0x90a2 : "世",
0x90a3 : "瀬",
0x90a4 : "畝",
0x90a5 : "是",
0x90a6 : "凄",
0x90a7 : "制",
0x90a8 : "勢",
0x90a9 : "姓",
0x90aa : "征",
0x90ab : "性",
0x90ac : "成",
0x90ad : "政",
0x90ae : "整",
0x90af : "星",
0x90b0 : "晴",
0x90b1 : "棲",
0x90b2 : "栖",
0x90b3 : "正",
0x90b4 : "清",
0x90b5 : "牲",
0x90b6 : "生",
0x90b7 : "盛",
0x90b8 : "精",
0x90b9 : "聖",
0x90ba : "声",
0x90bb : "製",
0x90bc : "西",
0x90bd : "誠",
0x90be : "誓",
0x90bf : "請",
0x90c0 : "逝",
0x90c1 : "醒",
0x90c2 : "青",
0x90c3 : "静",
0x90c4 : "斉",
0x90c5 : "税",
0x90c6 : "脆",
0x90c7 : "隻",
0x90c8 : "席",
0x90c9 : "惜",
0x90ca : "戚",
0x90cb : "斥",
0x90cc : "昔",
0x90cd : "析",
0x90ce : "石",
0x90cf : "積",
0x90d0 : "籍",
0x90d1 : "績",
0x90d2 : "脊",
0x90d3 : "責",
0x90d4 : "赤",
0x90d5 : "跡",
0x90d6 : "蹟",
0x90d7 : "碩",
0x90d8 : "切",
0x90d9 : "拙",
0x90da : "接",
0x90db : "摂",
0x90dc : "折",
0x90dd : "設",
0x90de : "窃",
0x90df : "節",
0x90e0 : "説",
0x90e1 : "雪",
0x90e2 : "絶",
0x90e3 : "舌",
0x90e4 : "蝉",
0x90e5 : "仙",
0x90e6 : "先",
0x90e7 : "千",
0x90e8 : "占",
0x90e9 : "宣",
0x90ea : "専",
0x90eb : "尖",
0x90ec : "川",
0x90ed : "戦",
0x90ee : "扇",
0x90ef : "撰",
0x90f0 : "栓",
0x90f1 : "栴",
0x90f2 : "泉",
0x90f3 : "浅",
0x90f4 : "洗",
0x90f5 : "染",
0x90f6 : "潜",
0x90f7 : "煎",
0x90f8 : "煽",
0x90f9 : "旋",
0x90fa : "穿",
0x90fb : "箭",
0x90fc : "線",
0x9140 : "繊",
0x9141 : "羨",
0x9142 : "腺",
0x9143 : "舛",
0x9144 : "船",
0x9145 : "薦",
0x9146 : "詮",
0x9147 : "賎",
0x9148 : "践",
0x9149 : "選",
0x914a : "遷",
0x914b : "銭",
0x914c : "銑",
0x914d : "閃",
0x914e : "鮮",
0x914f : "前",
0x9150 : "善",
0x9151 : "漸",
0x9152 : "然",
0x9153 : "全",
0x9154 : "禅",
0x9155 : "繕",
0x9156 : "膳",
0x9157 : "糎",
0x9158 : "噌",
0x9159 : "塑",
0x915a : "岨",
0x915b : "措",
0x915c : "曾",
0x915d : "曽",
0x915e : "楚",
0x915f : "狙",
0x9160 : "疏",
0x9161 : "疎",
0x9162 : "礎",
0x9163 : "祖",
0x9164 : "租",
0x9165 : "粗",
0x9166 : "素",
0x9167 : "組",
0x9168 : "蘇",
0x9169 : "訴",
0x916a : "阻",
0x916b : "遡",
0x916c : "鼠",
0x916d : "僧",
0x916e : "創",
0x916f : "双",
0x9170 : "叢",
0x9171 : "倉",
0x9172 : "喪",
0x9173 : "壮",
0x9174 : "奏",
0x9175 : "爽",
0x9176 : "宋",
0x9177 : "層",
0x9178 : "匝",
0x9179 : "惣",
0x917a : "想",
0x917b : "捜",
0x917c : "掃",
0x917d : "挿",
0x917e : "掻",
0x9180 : "操",
0x9181 : "早",
0x9182 : "曹",
0x9183 : "巣",
0x9184 : "槍",
0x9185 : "槽",
0x9186 : "漕",
0x9187 : "燥",
0x9188 : "争",
0x9189 : "痩",
0x918a : "相",
0x918b : "窓",
0x918c : "糟",
0x918d : "総",
0x918e : "綜",
0x918f : "聡",
0x9190 : "草",
0x9191 : "荘",
0x9192 : "葬",
0x9193 : "蒼",
0x9194 : "藻",
0x9195 : "装",
0x9196 : "走",
0x9197 : "送",
0x9198 : "遭",
0x9199 : "鎗",
0x919a : "霜",
0x919b : "騒",
0x919c : "像",
0x919d : "増",
0x919e : "憎",
0x919f : "臓",
0x91a0 : "蔵",
0x91a1 : "贈",
0x91a2 : "造",
0x91a3 : "促",
0x91a4 : "側",
0x91a5 : "則",
0x91a6 : "即",
0x91a7 : "息",
0x91a8 : "捉",
0x91a9 : "束",
0x91aa : "測",
0x91ab : "足",
0x91ac : "速",
0x91ad : "俗",
0x91ae : "属",
0x91af : "賊",
0x91b0 : "族",
0x91b1 : "続",
0x91b2 : "卒",
0x91b3 : "袖",
0x91b4 : "其",
0x91b5 : "揃",
0x91b6 : "存",
0x91b7 : "孫",
0x91b8 : "尊",
0x91b9 : "損",
0x91ba : "村",
0x91bb : "遜",
0x91bc : "他",
0x91bd : "多",
0x91be : "太",
0x91bf : "汰",
0x91c0 : "詑",
0x91c1 : "唾",
0x91c2 : "堕",
0x91c3 : "妥",
0x91c4 : "惰",
0x91c5 : "打",
0x91c6 : "柁",
0x91c7 : "舵",
0x91c8 : "楕",
0x91c9 : "陀",
0x91ca : "駄",
0x91cb : "騨",
0x91cc : "体",
0x91cd : "堆",
0x91ce : "対",
0x91cf : "耐",
0x91d0 : "岱",
0x91d1 : "帯",
0x91d2 : "待",
0x91d3 : "怠",
0x91d4 : "態",
0x91d5 : "戴",
0x91d6 : "替",
0x91d7 : "泰",
0x91d8 : "滞",
0x91d9 : "胎",
0x91da : "腿",
0x91db : "苔",
0x91dc : "袋",
0x91dd : "貸",
0x91de : "退",
0x91df : "逮",
0x91e0 : "隊",
0x91e1 : "黛",
0x91e2 : "鯛",
0x91e3 : "代",
0x91e4 : "台",
0x91e5 : "大",
0x91e6 : "第",
0x91e7 : "醍",
0x91e8 : "題",
0x91e9 : "鷹",
0x91ea : "滝",
0x91eb : "瀧",
0x91ec : "卓",
0x91ed : "啄",
0x91ee : "宅",
0x91ef : "托",
0x91f0 : "択",
0x91f1 : "拓",
0x91f2 : "沢",
0x91f3 : "濯",
0x91f4 : "琢",
0x91f5 : "託",
0x91f6 : "鐸",
0x91f7 : "濁",
0x91f8 : "諾",
0x91f9 : "茸",
0x91fa : "凧",
0x91fb : "蛸",
0x91fc : "只",
0x9240 : "叩",
0x9241 : "但",
0x9242 : "達",
0x9243 : "辰",
0x9244 : "奪",
0x9245 : "脱",
0x9246 : "巽",
0x9247 : "竪",
0x9248 : "辿",
0x9249 : "棚",
0x924a : "谷",
0x924b : "狸",
0x924c : "鱈",
0x924d : "樽",
0x924e : "誰",
0x924f : "丹",
0x9250 : "単",
0x9251 : "嘆",
0x9252 : "坦",
0x9253 : "担",
0x9254 : "探",
0x9255 : "旦",
0x9256 : "歎",
0x9257 : "淡",
0x9258 : "湛",
0x9259 : "炭",
0x925a : "短",
0x925b : "端",
0x925c : "箪",
0x925d : "綻",
0x925e : "耽",
0x925f : "胆",
0x9260 : "蛋",
0x9261 : "誕",
0x9262 : "鍛",
0x9263 : "団",
0x9264 : "壇",
0x9265 : "弾",
0x9266 : "断",
0x9267 : "暖",
0x9268 : "檀",
0x9269 : "段",
0x926a : "男",
0x926b : "談",
0x926c : "値",
0x926d : "知",
0x926e : "地",
0x926f : "弛",
0x9270 : "恥",
0x9271 : "智",
0x9272 : "池",
0x9273 : "痴",
0x9274 : "稚",
0x9275 : "置",
0x9276 : "致",
0x9277 : "蜘",
0x9278 : "遅",
0x9279 : "馳",
0x927a : "築",
0x927b : "畜",
0x927c : "竹",
0x927d : "筑",
0x927e : "蓄",
0x9280 : "逐",
0x9281 : "秩",
0x9282 : "窒",
0x9283 : "茶",
0x9284 : "嫡",
0x9285 : "着",
0x9286 : "中",
0x9287 : "仲",
0x9288 : "宙",
0x9289 : "忠",
0x928a : "抽",
0x928b : "昼",
0x928c : "柱",
0x928d : "注",
0x928e : "虫",
0x928f : "衷",
0x9290 : "註",
0x9291 : "酎",
0x9292 : "鋳",
0x9293 : "駐",
0x9294 : "樗",
0x9295 : "瀦",
0x9296 : "猪",
0x9297 : "苧",
0x9298 : "著",
0x9299 : "貯",
0x929a : "丁",
0x929b : "兆",
0x929c : "凋",
0x929d : "喋",
0x929e : "寵",
0x929f : "帖",
0x92a0 : "帳",
0x92a1 : "庁",
0x92a2 : "弔",
0x92a3 : "張",
0x92a4 : "彫",
0x92a5 : "徴",
0x92a6 : "懲",
0x92a7 : "挑",
0x92a8 : "暢",
0x92a9 : "朝",
0x92aa : "潮",
0x92ab : "牒",
0x92ac : "町",
0x92ad : "眺",
0x92ae : "聴",
0x92af : "脹",
0x92b0 : "腸",
0x92b1 : "蝶",
0x92b2 : "調",
0x92b3 : "諜",
0x92b4 : "超",
0x92b5 : "跳",
0x92b6 : "銚",
0x92b7 : "長",
0x92b8 : "頂",
0x92b9 : "鳥",
0x92ba : "勅",
0x92bb : "捗",
0x92bc : "直",
0x92bd : "朕",
0x92be : "沈",
0x92bf : "珍",
0x92c0 : "賃",
0x92c1 : "鎮",
0x92c2 : "陳",
0x92c3 : "津",
0x92c4 : "墜",
0x92c5 : "椎",
0x92c6 : "槌",
0x92c7 : "追",
0x92c8 : "鎚",
0x92c9 : "痛",
0x92ca : "通",
0x92cb : "塚",
0x92cc : "栂",
0x92cd : "掴",
0x92ce : "槻",
0x92cf : "佃",
0x92d0 : "漬",
0x92d1 : "柘",
0x92d2 : "辻",
0x92d3 : "蔦",
0x92d4 : "綴",
0x92d5 : "鍔",
0x92d6 : "椿",
0x92d7 : "潰",
0x92d8 : "坪",
0x92d9 : "壷",
0x92da : "嬬",
0x92db : "紬",
0x92dc : "爪",
0x92dd : "吊",
0x92de : "釣",
0x92df : "鶴",
0x92e0 : "亭",
0x92e1 : "低",
0x92e2 : "停",
0x92e3 : "偵",
0x92e4 : "剃",
0x92e5 : "貞",
0x92e6 : "呈",
0x92e7 : "堤",
0x92e8 : "定",
0x92e9 : "帝",
0x92ea : "底",
0x92eb : "庭",
0x92ec : "廷",
0x92ed : "弟",
0x92ee : "悌",
0x92ef : "抵",
0x92f0 : "挺",
0x92f1 : "提",
0x92f2 : "梯",
0x92f3 : "汀",
0x92f4 : "碇",
0x92f5 : "禎",
0x92f6 : "程",
0x92f7 : "締",
0x92f8 : "艇",
0x92f9 : "訂",
0x92fa : "諦",
0x92fb : "蹄",
0x92fc : "逓",
0x9340 : "邸",
0x9341 : "鄭",
0x9342 : "釘",
0x9343 : "鼎",
0x9344 : "泥",
0x9345 : "摘",
0x9346 : "擢",
0x9347 : "敵",
0x9348 : "滴",
0x9349 : "的",
0x934a : "笛",
0x934b : "適",
0x934c : "鏑",
0x934d : "溺",
0x934e : "哲",
0x934f : "徹",
0x9350 : "撤",
0x9351 : "轍",
0x9352 : "迭",
0x9353 : "鉄",
0x9354 : "典",
0x9355 : "填",
0x9356 : "天",
0x9357 : "展",
0x9358 : "店",
0x9359 : "添",
0x935a : "纏",
0x935b : "甜",
0x935c : "貼",
0x935d : "転",
0x935e : "顛",
0x935f : "点",
0x9360 : "伝",
0x9361 : "殿",
0x9362 : "澱",
0x9363 : "田",
0x9364 : "電",
0x9365 : "兎",
0x9366 : "吐",
0x9367 : "堵",
0x9368 : "塗",
0x9369 : "妬",
0x936a : "屠",
0x936b : "徒",
0x936c : "斗",
0x936d : "杜",
0x936e : "渡",
0x936f : "登",
0x9370 : "菟",
0x9371 : "賭",
0x9372 : "途",
0x9373 : "都",
0x9374 : "鍍",
0x9375 : "砥",
0x9376 : "砺",
0x9377 : "努",
0x9378 : "度",
0x9379 : "土",
0x937a : "奴",
0x937b : "怒",
0x937c : "倒",
0x937d : "党",
0x937e : "冬",
0x9380 : "凍",
0x9381 : "刀",
0x9382 : "唐",
0x9383 : "塔",
0x9384 : "塘",
0x9385 : "套",
0x9386 : "宕",
0x9387 : "島",
0x9388 : "嶋",
0x9389 : "悼",
0x938a : "投",
0x938b : "搭",
0x938c : "東",
0x938d : "桃",
0x938e : "梼",
0x938f : "棟",
0x9390 : "盗",
0x9391 : "淘",
0x9392 : "湯",
0x9393 : "涛",
0x9394 : "灯",
0x9395 : "燈",
0x9396 : "当",
0x9397 : "痘",
0x9398 : "祷",
0x9399 : "等",
0x939a : "答",
0x939b : "筒",
0x939c : "糖",
0x939d : "統",
0x939e : "到",
0x939f : "董",
0x93a0 : "蕩",
0x93a1 : "藤",
0x93a2 : "討",
0x93a3 : "謄",
0x93a4 : "豆",
0x93a5 : "踏",
0x93a6 : "逃",
0x93a7 : "透",
0x93a8 : "鐙",
0x93a9 : "陶",
0x93aa : "頭",
0x93ab : "騰",
0x93ac : "闘",
0x93ad : "働",
0x93ae : "動",
0x93af : "同",
0x93b0 : "堂",
0x93b1 : "導",
0x93b2 : "憧",
0x93b3 : "撞",
0x93b4 : "洞",
0x93b5 : "瞳",
0x93b6 : "童",
0x93b7 : "胴",
0x93b8 : "萄",
0x93b9 : "道",
0x93ba : "銅",
0x93bb : "峠",
0x93bc : "鴇",
0x93bd : "匿",
0x93be : "得",
0x93bf : "徳",
0x93c0 : "涜",
0x93c1 : "特",
0x93c2 : "督",
0x93c3 : "禿",
0x93c4 : "篤",
0x93c5 : "毒",
0x93c6 : "独",
0x93c7 : "読",
0x93c8 : "栃",
0x93c9 : "橡",
0x93ca : "凸",
0x93cb : "突",
0x93cc : "椴",
0x93cd : "届",
0x93ce : "鳶",
0x93cf : "苫",
0x93d0 : "寅",
0x93d1 : "酉",
0x93d2 : "瀞",
0x93d3 : "噸",
0x93d4 : "屯",
0x93d5 : "惇",
0x93d6 : "敦",
0x93d7 : "沌",
0x93d8 : "豚",
0x93d9 : "遁",
0x93da : "頓",
0x93db : "呑",
0x93dc : "曇",
0x93dd : "鈍",
0x93de : "奈",
0x93df : "那",
0x93e0 : "内",
0x93e1 : "乍",
0x93e2 : "凪",
0x93e3 : "薙",
0x93e4 : "謎",
0x93e5 : "灘",
0x93e6 : "捺",
0x93e7 : "鍋",
0x93e8 : "楢",
0x93e9 : "馴",
0x93ea : "縄",
0x93eb : "畷",
0x93ec : "南",
0x93ed : "楠",
0x93ee : "軟",
0x93ef : "難",
0x93f0 : "汝",
0x93f1 : "二",
0x93f2 : "尼",
0x93f3 : "弐",
0x93f4 : "迩",
0x93f5 : "匂",
0x93f6 : "賑",
0x93f7 : "肉",
0x93f8 : "虹",
0x93f9 : "廿",
0x93fa : "日",
0x93fb : "乳",
0x93fc : "入",
0x9440 : "如",
0x9441 : "尿",
0x9442 : "韮",
0x9443 : "任",
0x9444 : "妊",
0x9445 : "忍",
0x9446 : "認",
0x9447 : "濡",
0x9448 : "禰",
0x9449 : "祢",
0x944a : "寧",
0x944b : "葱",
0x944c : "猫",
0x944d : "熱",
0x944e : "年",
0x944f : "念",
0x9450 : "捻",
0x9451 : "撚",
0x9452 : "燃",
0x9453 : "粘",
0x9454 : "乃",
0x9455 : "廼",
0x9456 : "之",
0x9457 : "埜",
0x9458 : "嚢",
0x9459 : "悩",
0x945a : "濃",
0x945b : "納",
0x945c : "能",
0x945d : "脳",
0x945e : "膿",
0x945f : "農",
0x9460 : "覗",
0x9461 : "蚤",
0x9462 : "巴",
0x9463 : "把",
0x9464 : "播",
0x9465 : "覇",
0x9466 : "杷",
0x9467 : "波",
0x9468 : "派",
0x9469 : "琶",
0x946a : "破",
0x946b : "婆",
0x946c : "罵",
0x946d : "芭",
0x946e : "馬",
0x946f : "俳",
0x9470 : "廃",
0x9471 : "拝",
0x9472 : "排",
0x9473 : "敗",
0x9474 : "杯",
0x9475 : "盃",
0x9476 : "牌",
0x9477 : "背",
0x9478 : "肺",
0x9479 : "輩",
0x947a : "配",
0x947b : "倍",
0x947c : "培",
0x947d : "媒",
0x947e : "梅",
0x9480 : "楳",
0x9481 : "煤",
0x9482 : "狽",
0x9483 : "買",
0x9484 : "売",
0x9485 : "賠",
0x9486 : "陪",
0x9487 : "這",
0x9488 : "蝿",
0x9489 : "秤",
0x948a : "矧",
0x948b : "萩",
0x948c : "伯",
0x948d : "剥",
0x948e : "博",
0x948f : "拍",
0x9490 : "柏",
0x9491 : "泊",
0x9492 : "白",
0x9493 : "箔",
0x9494 : "粕",
0x9495 : "舶",
0x9496 : "薄",
0x9497 : "迫",
0x9498 : "曝",
0x9499 : "漠",
0x949a : "爆",
0x949b : "縛",
0x949c : "莫",
0x949d : "駁",
0x949e : "麦",
0x949f : "函",
0x94a0 : "箱",
0x94a1 : "硲",
0x94a2 : "箸",
0x94a3 : "肇",
0x94a4 : "筈",
0x94a5 : "櫨",
0x94a6 : "幡",
0x94a7 : "肌",
0x94a8 : "畑",
0x94a9 : "畠",
0x94aa : "八",
0x94ab : "鉢",
0x94ac : "溌",
0x94ad : "発",
0x94ae : "醗",
0x94af : "髪",
0x94b0 : "伐",
0x94b1 : "罰",
0x94b2 : "抜",
0x94b3 : "筏",
0x94b4 : "閥",
0x94b5 : "鳩",
0x94b6 : "噺",
0x94b7 : "塙",
0x94b8 : "蛤",
0x94b9 : "隼",
0x94ba : "伴",
0x94bb : "判",
0x94bc : "半",
0x94bd : "反",
0x94be : "叛",
0x94bf : "帆",
0x94c0 : "搬",
0x94c1 : "斑",
0x94c2 : "板",
0x94c3 : "氾",
0x94c4 : "汎",
0x94c5 : "版",
0x94c6 : "犯",
0x94c7 : "班",
0x94c8 : "畔",
0x94c9 : "繁",
0x94ca : "般",
0x94cb : "藩",
0x94cc : "販",
0x94cd : "範",
0x94ce : "釆",
0x94cf : "煩",
0x94d0 : "頒",
0x94d1 : "飯",
0x94d2 : "挽",
0x94d3 : "晩",
0x94d4 : "番",
0x94d5 : "盤",
0x94d6 : "磐",
0x94d7 : "蕃",
0x94d8 : "蛮",
0x94d9 : "匪",
0x94da : "卑",
0x94db : "否",
0x94dc : "妃",
0x94dd : "庇",
0x94de : "彼",
0x94df : "悲",
0x94e0 : "扉",
0x94e1 : "批",
0x94e2 : "披",
0x94e3 : "斐",
0x94e4 : "比",
0x94e5 : "泌",
0x94e6 : "疲",
0x94e7 : "皮",
0x94e8 : "碑",
0x94e9 : "秘",
0x94ea : "緋",
0x94eb : "罷",
0x94ec : "肥",
0x94ed : "被",
0x94ee : "誹",
0x94ef : "費",
0x94f0 : "避",
0x94f1 : "非",
0x94f2 : "飛",
0x94f3 : "樋",
0x94f4 : "簸",
0x94f5 : "備",
0x94f6 : "尾",
0x94f7 : "微",
0x94f8 : "枇",
0x94f9 : "毘",
0x94fa : "琵",
0x94fb : "眉",
0x94fc : "美",
0x9540 : "鼻",
0x9541 : "柊",
0x9542 : "稗",
0x9543 : "匹",
0x9544 : "疋",
0x9545 : "髭",
0x9546 : "彦",
0x9547 : "膝",
0x9548 : "菱",
0x9549 : "肘",
0x954a : "弼",
0x954b : "必",
0x954c : "畢",
0x954d : "筆",
0x954e : "逼",
0x954f : "桧",
0x9550 : "姫",
0x9551 : "媛",
0x9552 : "紐",
0x9553 : "百",
0x9554 : "謬",
0x9555 : "俵",
0x9556 : "彪",
0x9557 : "標",
0x9558 : "氷",
0x9559 : "漂",
0x955a : "瓢",
0x955b : "票",
0x955c : "表",
0x955d : "評",
0x955e : "豹",
0x955f : "廟",
0x9560 : "描",
0x9561 : "病",
0x9562 : "秒",
0x9563 : "苗",
0x9564 : "錨",
0x9565 : "鋲",
0x9566 : "蒜",
0x9567 : "蛭",
0x9568 : "鰭",
0x9569 : "品",
0x956a : "彬",
0x956b : "斌",
0x956c : "浜",
0x956d : "瀕",
0x956e : "貧",
0x956f : "賓",
0x9570 : "頻",
0x9571 : "敏",
0x9572 : "瓶",
0x9573 : "不",
0x9574 : "付",
0x9575 : "埠",
0x9576 : "夫",
0x9577 : "婦",
0x9578 : "富",
0x9579 : "冨",
0x957a : "布",
0x957b : "府",
0x957c : "怖",
0x957d : "扶",
0x957e : "敷",
0x9580 : "斧",
0x9581 : "普",
0x9582 : "浮",
0x9583 : "父",
0x9584 : "符",
0x9585 : "腐",
0x9586 : "膚",
0x9587 : "芙",
0x9588 : "譜",
0x9589 : "負",
0x958a : "賦",
0x958b : "赴",
0x958c : "阜",
0x958d : "附",
0x958e : "侮",
0x958f : "撫",
0x9590 : "武",
0x9591 : "舞",
0x9592 : "葡",
0x9593 : "蕪",
0x9594 : "部",
0x9595 : "封",
0x9596 : "楓",
0x9597 : "風",
0x9598 : "葺",
0x9599 : "蕗",
0x959a : "伏",
0x959b : "副",
0x959c : "復",
0x959d : "幅",
0x959e : "服",
0x959f : "福",
0x95a0 : "腹",
0x95a1 : "複",
0x95a2 : "覆",
0x95a3 : "淵",
0x95a4 : "弗",
0x95a5 : "払",
0x95a6 : "沸",
0x95a7 : "仏",
0x95a8 : "物",
0x95a9 : "鮒",
0x95aa : "分",
0x95ab : "吻",
0x95ac : "噴",
0x95ad : "墳",
0x95ae : "憤",
0x95af : "扮",
0x95b0 : "焚",
0x95b1 : "奮",
0x95b2 : "粉",
0x95b3 : "糞",
0x95b4 : "紛",
0x95b5 : "雰",
0x95b6 : "文",
0x95b7 : "聞",
0x95b8 : "丙",
0x95b9 : "併",
0x95ba : "兵",
0x95bb : "塀",
0x95bc : "幣",
0x95bd : "平",
0x95be : "弊",
0x95bf : "柄",
0x95c0 : "並",
0x95c1 : "蔽",
0x95c2 : "閉",
0x95c3 : "陛",
0x95c4 : "米",
0x95c5 : "頁",
0x95c6 : "僻",
0x95c7 : "壁",
0x95c8 : "癖",
0x95c9 : "碧",
0x95ca : "別",
0x95cb : "瞥",
0x95cc : "蔑",
0x95cd : "箆",
0x95ce : "偏",
0x95cf : "変",
0x95d0 : "片",
0x95d1 : "篇",
0x95d2 : "編",
0x95d3 : "辺",
0x95d4 : "返",
0x95d5 : "遍",
0x95d6 : "便",
0x95d7 : "勉",
0x95d8 : "娩",
0x95d9 : "弁",
0x95da : "鞭",
0x95db : "保",
0x95dc : "舗",
0x95dd : "鋪",
0x95de : "圃",
0x95df : "捕",
0x95e0 : "歩",
0x95e1 : "甫",
0x95e2 : "補",
0x95e3 : "輔",
0x95e4 : "穂",
0x95e5 : "募",
0x95e6 : "墓",
0x95e7 : "慕",
0x95e8 : "戊",
0x95e9 : "暮",
0x95ea : "母",
0x95eb : "簿",
0x95ec : "菩",
0x95ed : "倣",
0x95ee : "俸",
0x95ef : "包",
0x95f0 : "呆",
0x95f1 : "報",
0x95f2 : "奉",
0x95f3 : "宝",
0x95f4 : "峰",
0x95f5 : "峯",
0x95f6 : "崩",
0x95f7 : "庖",
0x95f8 : "抱",
0x95f9 : "捧",
0x95fa : "放",
0x95fb : "方",
0x95fc : "朋",
0x9640 : "法",
0x9641 : "泡",
0x9642 : "烹",
0x9643 : "砲",
0x9644 : "縫",
0x9645 : "胞",
0x9646 : "芳",
0x9647 : "萌",
0x9648 : "蓬",
0x9649 : "蜂",
0x964a : "褒",
0x964b : "訪",
0x964c : "豊",
0x964d : "邦",
0x964e : "鋒",
0x964f : "飽",
0x9650 : "鳳",
0x9651 : "鵬",
0x9652 : "乏",
0x9653 : "亡",
0x9654 : "傍",
0x9655 : "剖",
0x9656 : "坊",
0x9657 : "妨",
0x9658 : "帽",
0x9659 : "忘",
0x965a : "忙",
0x965b : "房",
0x965c : "暴",
0x965d : "望",
0x965e : "某",
0x965f : "棒",
0x9660 : "冒",
0x9661 : "紡",
0x9662 : "肪",
0x9663 : "膨",
0x9664 : "謀",
0x9665 : "貌",
0x9666 : "貿",
0x9667 : "鉾",
0x9668 : "防",
0x9669 : "吠",
0x966a : "頬",
0x966b : "北",
0x966c : "僕",
0x966d : "卜",
0x966e : "墨",
0x966f : "撲",
0x9670 : "朴",
0x9671 : "牧",
0x9672 : "睦",
0x9673 : "穆",
0x9674 : "釦",
0x9675 : "勃",
0x9676 : "没",
0x9677 : "殆",
0x9678 : "堀",
0x9679 : "幌",
0x967a : "奔",
0x967b : "本",
0x967c : "翻",
0x967d : "凡",
0x967e : "盆",
0x9680 : "摩",
0x9681 : "磨",
0x9682 : "魔",
0x9683 : "麻",
0x9684 : "埋",
0x9685 : "妹",
0x9686 : "昧",
0x9687 : "枚",
0x9688 : "毎",
0x9689 : "哩",
0x968a : "槙",
0x968b : "幕",
0x968c : "膜",
0x968d : "枕",
0x968e : "鮪",
0x968f : "柾",
0x9690 : "鱒",
0x9691 : "桝",
0x9692 : "亦",
0x9693 : "俣",
0x9694 : "又",
0x9695 : "抹",
0x9696 : "末",
0x9697 : "沫",
0x9698 : "迄",
0x9699 : "侭",
0x969a : "繭",
0x969b : "麿",
0x969c : "万",
0x969d : "慢",
0x969e : "満",
0x969f : "漫",
0x96a0 : "蔓",
0x96a1 : "味",
0x96a2 : "未",
0x96a3 : "魅",
0x96a4 : "巳",
0x96a5 : "箕",
0x96a6 : "岬",
0x96a7 : "密",
0x96a8 : "蜜",
0x96a9 : "湊",
0x96aa : "蓑",
0x96ab : "稔",
0x96ac : "脈",
0x96ad : "妙",
0x96ae : "粍",
0x96af : "民",
0x96b0 : "眠",
0x96b1 : "務",
0x96b2 : "夢",
0x96b3 : "無",
0x96b4 : "牟",
0x96b5 : "矛",
0x96b6 : "霧",
0x96b7 : "鵡",
0x96b8 : "椋",
0x96b9 : "婿",
0x96ba : "娘",
0x96bb : "冥",
0x96bc : "名",
0x96bd : "命",
0x96be : "明",
0x96bf : "盟",
0x96c0 : "迷",
0x96c1 : "銘",
0x96c2 : "鳴",
0x96c3 : "姪",
0x96c4 : "牝",
0x96c5 : "滅",
0x96c6 : "免",
0x96c7 : "棉",
0x96c8 : "綿",
0x96c9 : "緬",
0x96ca : "面",
0x96cb : "麺",
0x96cc : "摸",
0x96cd : "模",
0x96ce : "茂",
0x96cf : "妄",
0x96d0 : "孟",
0x96d1 : "毛",
0x96d2 : "猛",
0x96d3 : "盲",
0x96d4 : "網",
0x96d5 : "耗",
0x96d6 : "蒙",
0x96d7 : "儲",
0x96d8 : "木",
0x96d9 : "黙",
0x96da : "目",
0x96db : "杢",
0x96dc : "勿",
0x96dd : "餅",
0x96de : "尤",
0x96df : "戻",
0x96e0 : "籾",
0x96e1 : "貰",
0x96e2 : "問",
0x96e3 : "悶",
0x96e4 : "紋",
0x96e5 : "門",
0x96e6 : "匁",
0x96e7 : "也",
0x96e8 : "冶",
0x96e9 : "夜",
0x96ea : "爺",
0x96eb : "耶",
0x96ec : "野",
0x96ed : "弥",
0x96ee : "矢",
0x96ef : "厄",
0x96f0 : "役",
0x96f1 : "約",
0x96f2 : "薬",
0x96f3 : "訳",
0x96f4 : "躍",
0x96f5 : "靖",
0x96f6 : "柳",
0x96f7 : "薮",
0x96f8 : "鑓",
0x96f9 : "愉",
0x96fa : "愈",
0x96fb : "油",
0x96fc : "癒",
0x9740 : "諭",
0x9741 : "輸",
0x9742 : "唯",
0x9743 : "佑",
0x9744 : "優",
0x9745 : "勇",
0x9746 : "友",
0x9747 : "宥",
0x9748 : "幽",
0x9749 : "悠",
0x974a : "憂",
0x974b : "揖",
0x974c : "有",
0x974d : "柚",
0x974e : "湧",
0x974f : "涌",
0x9750 : "猶",
0x9751 : "猷",
0x9752 : "由",
0x9753 : "祐",
0x9754 : "裕",
0x9755 : "誘",
0x9756 : "遊",
0x9757 : "邑",
0x9758 : "郵",
0x9759 : "雄",
0x975a : "融",
0x975b : "夕",
0x975c : "予",
0x975d : "余",
0x975e : "与",
0x975f : "誉",
0x9760 : "輿",
0x9761 : "預",
0x9762 : "傭",
0x9763 : "幼",
0x9764 : "妖",
0x9765 : "容",
0x9766 : "庸",
0x9767 : "揚",
0x9768 : "揺",
0x9769 : "擁",
0x976a : "曜",
0x976b : "楊",
0x976c : "様",
0x976d : "洋",
0x976e : "溶",
0x976f : "熔",
0x9770 : "用",
0x9771 : "窯",
0x9772 : "羊",
0x9773 : "耀",
0x9774 : "葉",
0x9775 : "蓉",
0x9776 : "要",
0x9777 : "謡",
0x9778 : "踊",
0x9779 : "遥",
0x977a : "陽",
0x977b : "養",
0x977c : "慾",
0x977d : "抑",
0x977e : "欲",
0x9780 : "沃",
0x9781 : "浴",
0x9782 : "翌",
0x9783 : "翼",
0x9784 : "淀",
0x9785 : "羅",
0x9786 : "螺",
0x9787 : "裸",
0x9788 : "来",
0x9789 : "莱",
0x978a : "頼",
0x978b : "雷",
0x978c : "洛",
0x978d : "絡",
0x978e : "落",
0x978f : "酪",
0x9790 : "乱",
0x9791 : "卵",
0x9792 : "嵐",
0x9793 : "欄",
0x9794 : "濫",
0x9795 : "藍",
0x9796 : "蘭",
0x9797 : "覧",
0x9798 : "利",
0x9799 : "吏",
0x979a : "履",
0x979b : "李",
0x979c : "梨",
0x979d : "理",
0x979e : "璃",
0x979f : "痢",
0x97a0 : "裏",
0x97a1 : "裡",
0x97a2 : "里",
0x97a3 : "離",
0x97a4 : "陸",
0x97a5 : "律",
0x97a6 : "率",
0x97a7 : "立",
0x97a8 : "葎",
0x97a9 : "掠",
0x97aa : "略",
0x97ab : "劉",
0x97ac : "流",
0x97ad : "溜",
0x97ae : "琉",
0x97af : "留",
0x97b0 : "硫",
0x97b1 : "粒",
0x97b2 : "隆",
0x97b3 : "竜",
0x97b4 : "龍",
0x97b5 : "侶",
0x97b6 : "慮",
0x97b7 : "旅",
0x97b8 : "虜",
0x97b9 : "了",
0x97ba : "亮",
0x97bb : "僚",
0x97bc : "両",
0x97bd : "凌",
0x97be : "寮",
0x97bf : "料",
0x97c0 : "梁",
0x97c1 : "涼",
0x97c2 : "猟",
0x97c3 : "療",
0x97c4 : "瞭",
0x97c5 : "稜",
0x97c6 : "糧",
0x97c7 : "良",
0x97c8 : "諒",
0x97c9 : "遼",
0x97ca : "量",
0x97cb : "陵",
0x97cc : "領",
0x97cd : "力",
0x97ce : "緑",
0x97cf : "倫",
0x97d0 : "厘",
0x97d1 : "林",
0x97d2 : "淋",
0x97d3 : "燐",
0x97d4 : "琳",
0x97d5 : "臨",
0x97d6 : "輪",
0x97d7 : "隣",
0x97d8 : "鱗",
0x97d9 : "麟",
0x97da : "瑠",
0x97db : "塁",
0x97dc : "涙",
0x97dd : "累",
0x97de : "類",
0x97df : "令",
0x97e0 : "伶",
0x97e1 : "例",
0x97e2 : "冷",
0x97e3 : "励",
0x97e4 : "嶺",
0x97e5 : "怜",
0x97e6 : "玲",
0x97e7 : "礼",
0x97e8 : "苓",
0x97e9 : "鈴",
0x97ea : "隷",
0x97eb : "零",
0x97ec : "霊",
0x97ed : "麗",
0x97ee : "齢",
0x97ef : "暦",
0x97f0 : "歴",
0x97f1 : "列",
0x97f2 : "劣",
0x97f3 : "烈",
0x97f4 : "裂",
0x97f5 : "廉",
0x97f6 : "恋",
0x97f7 : "憐",
0x97f8 : "漣",
0x97f9 : "煉",
0x97fa : "簾",
0x97fb : "練",
0x97fc : "聯",
0x9840 : "蓮",
0x9841 : "連",
0x9842 : "錬",
0x9843 : "呂",
0x9844 : "魯",
0x9845 : "櫓",
0x9846 : "炉",
0x9847 : "賂",
0x9848 : "路",
0x9849 : "露",
0x984a : "労",
0x984b : "婁",
0x984c : "廊",
0x984d : "弄",
0x984e : "朗",
0x984f : "楼",
0x9850 : "榔",
0x9851 : "浪",
0x9852 : "漏",
0x9853 : "牢",
0x9854 : "狼",
0x9855 : "篭",
0x9856 : "老",
0x9857 : "聾",
0x9858 : "蝋",
0x9859 : "郎",
0x985a : "六",
0x985b : "麓",
0x985c : "禄",
0x985d : "肋",
0x985e : "録",
0x985f : "論",
0x9860 : "倭",
0x9861 : "和",
0x9862 : "話",
0x9863 : "歪",
0x9864 : "賄",
0x9865 : "脇",
0x9866 : "惑",
0x9867 : "枠",
0x9868 : "鷲",
0x9869 : "亙",
0x986a : "亘",
0x986b : "鰐",
0x986c : "詫",
0x986d : "藁",
0x986e : "蕨",
0x986f : "椀",
0x9870 : "湾",
0x9871 : "碗",
0x9872 : "腕",
0x989f : "弌",
0x98a0 : "丐",
0x98a1 : "丕",
0x98a2 : "个",
0x98a3 : "丱",
0x98a4 : "丶",
0x98a5 : "丼",
0x98a6 : "丿",
0x98a7 : "乂",
0x98a8 : "乖",
0x98a9 : "乘",
0x98aa : "亂",
0x98ab : "亅",
0x98ac : "豫",
0x98ad : "亊",
0x98ae : "舒",
0x98af : "弍",
0x98b0 : "于",
0x98b1 : "亞",
0x98b2 : "亟",
0x98b3 : "亠",
0x98b4 : "亢",
0x98b5 : "亰",
0x98b6 : "亳",
0x98b7 : "亶",
0x98b8 : "从",
0x98b9 : "仍",
0x98ba : "仄",
0x98bb : "仆",
0x98bc : "仂",
0x98bd : "仗",
0x98be : "仞",
0x98bf : "仭",
0x98c0 : "仟",
0x98c1 : "价",
0x98c2 : "伉",
0x98c3 : "佚",
0x98c4 : "估",
0x98c5 : "佛",
0x98c6 : "佝",
0x98c7 : "佗",
0x98c8 : "佇",
0x98c9 : "佶",
0x98ca : "侈",
0x98cb : "侏",
0x98cc : "侘",
0x98cd : "佻",
0x98ce : "佩",
0x98cf : "佰",
0x98d0 : "侑",
0x98d1 : "佯",
0x98d2 : "來",
0x98d3 : "侖",
0x98d4 : "儘",
0x98d5 : "俔",
0x98d6 : "俟",
0x98d7 : "俎",
0x98d8 : "俘",
0x98d9 : "俛",
0x98da : "俑",
0x98db : "俚",
0x98dc : "俐",
0x98dd : "俤",
0x98de : "俥",
0x98df : "倚",
0x98e0 : "倨",
0x98e1 : "倔",
0x98e2 : "倪",
0x98e3 : "倥",
0x98e4 : "倅",
0x98e5 : "伜",
0x98e6 : "俶",
0x98e7 : "倡",
0x98e8 : "倩",
0x98e9 : "倬",
0x98ea : "俾",
0x98eb : "俯",
0x98ec : "們",
0x98ed : "倆",
0x98ee : "偃",
0x98ef : "假",
0x98f0 : "會",
0x98f1 : "偕",
0x98f2 : "偐",
0x98f3 : "偈",
0x98f4 : "做",
0x98f5 : "偖",
0x98f6 : "偬",
0x98f7 : "偸",
0x98f8 : "傀",
0x98f9 : "傚",
0x98fa : "傅",
0x98fb : "傴",
0x98fc : "傲",
0x9940 : "僉",
0x9941 : "僊",
0x9942 : "傳",
0x9943 : "僂",
0x9944 : "僖",
0x9945 : "僞",
0x9946 : "僥",
0x9947 : "僭",
0x9948 : "僣",
0x9949 : "僮",
0x994a : "價",
0x994b : "僵",
0x994c : "儉",
0x994d : "儁",
0x994e : "儂",
0x994f : "儖",
0x9950 : "儕",
0x9951 : "儔",
0x9952 : "儚",
0x9953 : "儡",
0x9954 : "儺",
0x9955 : "儷",
0x9956 : "儼",
0x9957 : "儻",
0x9958 : "儿",
0x9959 : "兀",
0x995a : "兒",
0x995b : "兌",
0x995c : "兔",
0x995d : "兢",
0x995e : "竸",
0x995f : "兩",
0x9960 : "兪",
0x9961 : "兮",
0x9962 : "冀",
0x9963 : "冂",
0x9964 : "囘",
0x9965 : "册",
0x9966 : "冉",
0x9967 : "冏",
0x9968 : "冑",
0x9969 : "冓",
0x996a : "冕",
0x996b : "冖",
0x996c : "冤",
0x996d : "冦",
0x996e : "冢",
0x996f : "冩",
0x9970 : "冪",
0x9971 : "冫",
0x9972 : "决",
0x9973 : "冱",
0x9974 : "冲",
0x9975 : "冰",
0x9976 : "况",
0x9977 : "冽",
0x9978 : "凅",
0x9979 : "凉",
0x997a : "凛",
0x997b : "几",
0x997c : "處",
0x997d : "凩",
0x997e : "凭",
0x9980 : "凰",
0x9981 : "凵",
0x9982 : "凾",
0x9983 : "刄",
0x9984 : "刋",
0x9985 : "刔",
0x9986 : "刎",
0x9987 : "刧",
0x9988 : "刪",
0x9989 : "刮",
0x998a : "刳",
0x998b : "刹",
0x998c : "剏",
0x998d : "剄",
0x998e : "剋",
0x998f : "剌",
0x9990 : "剞",
0x9991 : "剔",
0x9992 : "剪",
0x9993 : "剴",
0x9994 : "剩",
0x9995 : "剳",
0x9996 : "剿",
0x9997 : "剽",
0x9998 : "劍",
0x9999 : "劔",
0x999a : "劒",
0x999b : "剱",
0x999c : "劈",
0x999d : "劑",
0x999e : "辨",
0x999f : "辧",
0x99a0 : "劬",
0x99a1 : "劭",
0x99a2 : "劼",
0x99a3 : "劵",
0x99a4 : "勁",
0x99a5 : "勍",
0x99a6 : "勗",
0x99a7 : "勞",
0x99a8 : "勣",
0x99a9 : "勦",
0x99aa : "飭",
0x99ab : "勠",
0x99ac : "勳",
0x99ad : "勵",
0x99ae : "勸",
0x99af : "勹",
0x99b0 : "匆",
0x99b1 : "匈",
0x99b2 : "甸",
0x99b3 : "匍",
0x99b4 : "匐",
0x99b5 : "匏",
0x99b6 : "匕",
0x99b7 : "匚",
0x99b8 : "匣",
0x99b9 : "匯",
0x99ba : "匱",
0x99bb : "匳",
0x99bc : "匸",
0x99bd : "區",
0x99be : "卆",
0x99bf : "卅",
0x99c0 : "丗",
0x99c1 : "卉",
0x99c2 : "卍",
0x99c3 : "凖",
0x99c4 : "卞",
0x99c5 : "卩",
0x99c6 : "卮",
0x99c7 : "夘",
0x99c8 : "卻",
0x99c9 : "卷",
0x99ca : "厂",
0x99cb : "厖",
0x99cc : "厠",
0x99cd : "厦",
0x99ce : "厥",
0x99cf : "厮",
0x99d0 : "厰",
0x99d1 : "厶",
0x99d2 : "參",
0x99d3 : "簒",
0x99d4 : "雙",
0x99d5 : "叟",
0x99d6 : "曼",
0x99d7 : "燮",
0x99d8 : "叮",
0x99d9 : "叨",
0x99da : "叭",
0x99db : "叺",
0x99dc : "吁",
0x99dd : "吽",
0x99de : "呀",
0x99df : "听",
0x99e0 : "吭",
0x99e1 : "吼",
0x99e2 : "吮",
0x99e3 : "吶",
0x99e4 : "吩",
0x99e5 : "吝",
0x99e6 : "呎",
0x99e7 : "咏",
0x99e8 : "呵",
0x99e9 : "咎",
0x99ea : "呟",
0x99eb : "呱",
0x99ec : "呷",
0x99ed : "呰",
0x99ee : "咒",
0x99ef : "呻",
0x99f0 : "咀",
0x99f1 : "呶",
0x99f2 : "咄",
0x99f3 : "咐",
0x99f4 : "咆",
0x99f5 : "哇",
0x99f6 : "咢",
0x99f7 : "咸",
0x99f8 : "咥",
0x99f9 : "咬",
0x99fa : "哄",
0x99fb : "哈",
0x99fc : "咨",
0x9a40 : "咫",
0x9a41 : "哂",
0x9a42 : "咤",
0x9a43 : "咾",
0x9a44 : "咼",
0x9a45 : "哘",
0x9a46 : "哥",
0x9a47 : "哦",
0x9a48 : "唏",
0x9a49 : "唔",
0x9a4a : "哽",
0x9a4b : "哮",
0x9a4c : "哭",
0x9a4d : "哺",
0x9a4e : "哢",
0x9a4f : "唹",
0x9a50 : "啀",
0x9a51 : "啣",
0x9a52 : "啌",
0x9a53 : "售",
0x9a54 : "啜",
0x9a55 : "啅",
0x9a56 : "啖",
0x9a57 : "啗",
0x9a58 : "唸",
0x9a59 : "唳",
0x9a5a : "啝",
0x9a5b : "喙",
0x9a5c : "喀",
0x9a5d : "咯",
0x9a5e : "喊",
0x9a5f : "喟",
0x9a60 : "啻",
0x9a61 : "啾",
0x9a62 : "喘",
0x9a63 : "喞",
0x9a64 : "單",
0x9a65 : "啼",
0x9a66 : "喃",
0x9a67 : "喩",
0x9a68 : "喇",
0x9a69 : "喨",
0x9a6a : "嗚",
0x9a6b : "嗅",
0x9a6c : "嗟",
0x9a6d : "嗄",
0x9a6e : "嗜",
0x9a6f : "嗤",
0x9a70 : "嗔",
0x9a71 : "嘔",
0x9a72 : "嗷",
0x9a73 : "嘖",
0x9a74 : "嗾",
0x9a75 : "嗽",
0x9a76 : "嘛",
0x9a77 : "嗹",
0x9a78 : "噎",
0x9a79 : "噐",
0x9a7a : "營",
0x9a7b : "嘴",
0x9a7c : "嘶",
0x9a7d : "嘲",
0x9a7e : "嘸",
0x9a80 : "噫",
0x9a81 : "噤",
0x9a82 : "嘯",
0x9a83 : "噬",
0x9a84 : "噪",
0x9a85 : "嚆",
0x9a86 : "嚀",
0x9a87 : "嚊",
0x9a88 : "嚠",
0x9a89 : "嚔",
0x9a8a : "嚏",
0x9a8b : "嚥",
0x9a8c : "嚮",
0x9a8d : "嚶",
0x9a8e : "嚴",
0x9a8f : "囂",
0x9a90 : "嚼",
0x9a91 : "囁",
0x9a92 : "囃",
0x9a93 : "囀",
0x9a94 : "囈",
0x9a95 : "囎",
0x9a96 : "囑",
0x9a97 : "囓",
0x9a98 : "囗",
0x9a99 : "囮",
0x9a9a : "囹",
0x9a9b : "圀",
0x9a9c : "囿",
0x9a9d : "圄",
0x9a9e : "圉",
0x9a9f : "圈",
0x9aa0 : "國",
0x9aa1 : "圍",
0x9aa2 : "圓",
0x9aa3 : "團",
0x9aa4 : "圖",
0x9aa5 : "嗇",
0x9aa6 : "圜",
0x9aa7 : "圦",
0x9aa8 : "圷",
0x9aa9 : "圸",
0x9aaa : "坎",
0x9aab : "圻",
0x9aac : "址",
0x9aad : "坏",
0x9aae : "坩",
0x9aaf : "埀",
0x9ab0 : "垈",
0x9ab1 : "坡",
0x9ab2 : "坿",
0x9ab3 : "垉",
0x9ab4 : "垓",
0x9ab5 : "垠",
0x9ab6 : "垳",
0x9ab7 : "垤",
0x9ab8 : "垪",
0x9ab9 : "垰",
0x9aba : "埃",
0x9abb : "埆",
0x9abc : "埔",
0x9abd : "埒",
0x9abe : "埓",
0x9abf : "堊",
0x9ac0 : "埖",
0x9ac1 : "埣",
0x9ac2 : "堋",
0x9ac3 : "堙",
0x9ac4 : "堝",
0x9ac5 : "塲",
0x9ac6 : "堡",
0x9ac7 : "塢",
0x9ac8 : "塋",
0x9ac9 : "塰",
0x9aca : "毀",
0x9acb : "塒",
0x9acc : "堽",
0x9acd : "塹",
0x9ace : "墅",
0x9acf : "墹",
0x9ad0 : "墟",
0x9ad1 : "墫",
0x9ad2 : "墺",
0x9ad3 : "壞",
0x9ad4 : "墻",
0x9ad5 : "墸",
0x9ad6 : "墮",
0x9ad7 : "壅",
0x9ad8 : "壓",
0x9ad9 : "壑",
0x9ada : "壗",
0x9adb : "壙",
0x9adc : "壘",
0x9add : "壥",
0x9ade : "壜",
0x9adf : "壤",
0x9ae0 : "壟",
0x9ae1 : "壯",
0x9ae2 : "壺",
0x9ae3 : "壹",
0x9ae4 : "壻",
0x9ae5 : "壼",
0x9ae6 : "壽",
0x9ae7 : "夂",
0x9ae8 : "夊",
0x9ae9 : "夐",
0x9aea : "夛",
0x9aeb : "梦",
0x9aec : "夥",
0x9aed : "夬",
0x9aee : "夭",
0x9aef : "夲",
0x9af0 : "夸",
0x9af1 : "夾",
0x9af2 : "竒",
0x9af3 : "奕",
0x9af4 : "奐",
0x9af5 : "奎",
0x9af6 : "奚",
0x9af7 : "奘",
0x9af8 : "奢",
0x9af9 : "奠",
0x9afa : "奧",
0x9afb : "奬",
0x9afc : "奩",
0x9b40 : "奸",
0x9b41 : "妁",
0x9b42 : "妝",
0x9b43 : "佞",
0x9b44 : "侫",
0x9b45 : "妣",
0x9b46 : "妲",
0x9b47 : "姆",
0x9b48 : "姨",
0x9b49 : "姜",
0x9b4a : "妍",
0x9b4b : "姙",
0x9b4c : "姚",
0x9b4d : "娥",
0x9b4e : "娟",
0x9b4f : "娑",
0x9b50 : "娜",
0x9b51 : "娉",
0x9b52 : "娚",
0x9b53 : "婀",
0x9b54 : "婬",
0x9b55 : "婉",
0x9b56 : "娵",
0x9b57 : "娶",
0x9b58 : "婢",
0x9b59 : "婪",
0x9b5a : "媚",
0x9b5b : "媼",
0x9b5c : "媾",
0x9b5d : "嫋",
0x9b5e : "嫂",
0x9b5f : "媽",
0x9b60 : "嫣",
0x9b61 : "嫗",
0x9b62 : "嫦",
0x9b63 : "嫩",
0x9b64 : "嫖",
0x9b65 : "嫺",
0x9b66 : "嫻",
0x9b67 : "嬌",
0x9b68 : "嬋",
0x9b69 : "嬖",
0x9b6a : "嬲",
0x9b6b : "嫐",
0x9b6c : "嬪",
0x9b6d : "嬶",
0x9b6e : "嬾",
0x9b6f : "孃",
0x9b70 : "孅",
0x9b71 : "孀",
0x9b72 : "孑",
0x9b73 : "孕",
0x9b74 : "孚",
0x9b75 : "孛",
0x9b76 : "孥",
0x9b77 : "孩",
0x9b78 : "孰",
0x9b79 : "孳",
0x9b7a : "孵",
0x9b7b : "學",
0x9b7c : "斈",
0x9b7d : "孺",
0x9b7e : "宀",
0x9b80 : "它",
0x9b81 : "宦",
0x9b82 : "宸",
0x9b83 : "寃",
0x9b84 : "寇",
0x9b85 : "寉",
0x9b86 : "寔",
0x9b87 : "寐",
0x9b88 : "寤",
0x9b89 : "實",
0x9b8a : "寢",
0x9b8b : "寞",
0x9b8c : "寥",
0x9b8d : "寫",
0x9b8e : "寰",
0x9b8f : "寶",
0x9b90 : "寳",
0x9b91 : "尅",
0x9b92 : "將",
0x9b93 : "專",
0x9b94 : "對",
0x9b95 : "尓",
0x9b96 : "尠",
0x9b97 : "尢",
0x9b98 : "尨",
0x9b99 : "尸",
0x9b9a : "尹",
0x9b9b : "屁",
0x9b9c : "屆",
0x9b9d : "屎",
0x9b9e : "屓",
0x9b9f : "屐",
0x9ba0 : "屏",
0x9ba1 : "孱",
0x9ba2 : "屬",
0x9ba3 : "屮",
0x9ba4 : "乢",
0x9ba5 : "屶",
0x9ba6 : "屹",
0x9ba7 : "岌",
0x9ba8 : "岑",
0x9ba9 : "岔",
0x9baa : "妛",
0x9bab : "岫",
0x9bac : "岻",
0x9bad : "岶",
0x9bae : "岼",
0x9baf : "岷",
0x9bb0 : "峅",
0x9bb1 : "岾",
0x9bb2 : "峇",
0x9bb3 : "峙",
0x9bb4 : "峩",
0x9bb5 : "峽",
0x9bb6 : "峺",
0x9bb7 : "峭",
0x9bb8 : "嶌",
0x9bb9 : "峪",
0x9bba : "崋",
0x9bbb : "崕",
0x9bbc : "崗",
0x9bbd : "嵜",
0x9bbe : "崟",
0x9bbf : "崛",
0x9bc0 : "崑",
0x9bc1 : "崔",
0x9bc2 : "崢",
0x9bc3 : "崚",
0x9bc4 : "崙",
0x9bc5 : "崘",
0x9bc6 : "嵌",
0x9bc7 : "嵒",
0x9bc8 : "嵎",
0x9bc9 : "嵋",
0x9bca : "嵬",
0x9bcb : "嵳",
0x9bcc : "嵶",
0x9bcd : "嶇",
0x9bce : "嶄",
0x9bcf : "嶂",
0x9bd0 : "嶢",
0x9bd1 : "嶝",
0x9bd2 : "嶬",
0x9bd3 : "嶮",
0x9bd4 : "嶽",
0x9bd5 : "嶐",
0x9bd6 : "嶷",
0x9bd7 : "嶼",
0x9bd8 : "巉",
0x9bd9 : "巍",
0x9bda : "巓",
0x9bdb : "巒",
0x9bdc : "巖",
0x9bdd : "巛",
0x9bde : "巫",
0x9bdf : "已",
0x9be0 : "巵",
0x9be1 : "帋",
0x9be2 : "帚",
0x9be3 : "帙",
0x9be4 : "帑",
0x9be5 : "帛",
0x9be6 : "帶",
0x9be7 : "帷",
0x9be8 : "幄",
0x9be9 : "幃",
0x9bea : "幀",
0x9beb : "幎",
0x9bec : "幗",
0x9bed : "幔",
0x9bee : "幟",
0x9bef : "幢",
0x9bf0 : "幤",
0x9bf1 : "幇",
0x9bf2 : "幵",
0x9bf3 : "并",
0x9bf4 : "幺",
0x9bf5 : "麼",
0x9bf6 : "广",
0x9bf7 : "庠",
0x9bf8 : "廁",
0x9bf9 : "廂",
0x9bfa : "廈",
0x9bfb : "廐",
0x9bfc : "廏",
0x9c40 : "廖",
0x9c41 : "廣",
0x9c42 : "廝",
0x9c43 : "廚",
0x9c44 : "廛",
0x9c45 : "廢",
0x9c46 : "廡",
0x9c47 : "廨",
0x9c48 : "廩",
0x9c49 : "廬",
0x9c4a : "廱",
0x9c4b : "廳",
0x9c4c : "廰",
0x9c4d : "廴",
0x9c4e : "廸",
0x9c4f : "廾",
0x9c50 : "弃",
0x9c51 : "弉",
0x9c52 : "彝",
0x9c53 : "彜",
0x9c54 : "弋",
0x9c55 : "弑",
0x9c56 : "弖",
0x9c57 : "弩",
0x9c58 : "弭",
0x9c59 : "弸",
0x9c5a : "彁",
0x9c5b : "彈",
0x9c5c : "彌",
0x9c5d : "彎",
0x9c5e : "弯",
0x9c5f : "彑",
0x9c60 : "彖",
0x9c61 : "彗",
0x9c62 : "彙",
0x9c63 : "彡",
0x9c64 : "彭",
0x9c65 : "彳",
0x9c66 : "彷",
0x9c67 : "徃",
0x9c68 : "徂",
0x9c69 : "彿",
0x9c6a : "徊",
0x9c6b : "很",
0x9c6c : "徑",
0x9c6d : "徇",
0x9c6e : "從",
0x9c6f : "徙",
0x9c70 : "徘",
0x9c71 : "徠",
0x9c72 : "徨",
0x9c73 : "徭",
0x9c74 : "徼",
0x9c75 : "忖",
0x9c76 : "忻",
0x9c77 : "忤",
0x9c78 : "忸",
0x9c79 : "忱",
0x9c7a : "忝",
0x9c7b : "悳",
0x9c7c : "忿",
0x9c7d : "怡",
0x9c7e : "恠",
0x9c80 : "怙",
0x9c81 : "怐",
0x9c82 : "怩",
0x9c83 : "怎",
0x9c84 : "怱",
0x9c85 : "怛",
0x9c86 : "怕",
0x9c87 : "怫",
0x9c88 : "怦",
0x9c89 : "怏",
0x9c8a : "怺",
0x9c8b : "恚",
0x9c8c : "恁",
0x9c8d : "恪",
0x9c8e : "恷",
0x9c8f : "恟",
0x9c90 : "恊",
0x9c91 : "恆",
0x9c92 : "恍",
0x9c93 : "恣",
0x9c94 : "恃",
0x9c95 : "恤",
0x9c96 : "恂",
0x9c97 : "恬",
0x9c98 : "恫",
0x9c99 : "恙",
0x9c9a : "悁",
0x9c9b : "悍",
0x9c9c : "惧",
0x9c9d : "悃",
0x9c9e : "悚",
0x9c9f : "悄",
0x9ca0 : "悛",
0x9ca1 : "悖",
0x9ca2 : "悗",
0x9ca3 : "悒",
0x9ca4 : "悧",
0x9ca5 : "悋",
0x9ca6 : "惡",
0x9ca7 : "悸",
0x9ca8 : "惠",
0x9ca9 : "惓",
0x9caa : "悴",
0x9cab : "忰",
0x9cac : "悽",
0x9cad : "惆",
0x9cae : "悵",
0x9caf : "惘",
0x9cb0 : "慍",
0x9cb1 : "愕",
0x9cb2 : "愆",
0x9cb3 : "惶",
0x9cb4 : "惷",
0x9cb5 : "愀",
0x9cb6 : "惴",
0x9cb7 : "惺",
0x9cb8 : "愃",
0x9cb9 : "愡",
0x9cba : "惻",
0x9cbb : "惱",
0x9cbc : "愍",
0x9cbd : "愎",
0x9cbe : "慇",
0x9cbf : "愾",
0x9cc0 : "愨",
0x9cc1 : "愧",
0x9cc2 : "慊",
0x9cc3 : "愿",
0x9cc4 : "愼",
0x9cc5 : "愬",
0x9cc6 : "愴",
0x9cc7 : "愽",
0x9cc8 : "慂",
0x9cc9 : "慄",
0x9cca : "慳",
0x9ccb : "慷",
0x9ccc : "慘",
0x9ccd : "慙",
0x9cce : "慚",
0x9ccf : "慫",
0x9cd0 : "慴",
0x9cd1 : "慯",
0x9cd2 : "慥",
0x9cd3 : "慱",
0x9cd4 : "慟",
0x9cd5 : "慝",
0x9cd6 : "慓",
0x9cd7 : "慵",
0x9cd8 : "憙",
0x9cd9 : "憖",
0x9cda : "憇",
0x9cdb : "憬",
0x9cdc : "憔",
0x9cdd : "憚",
0x9cde : "憊",
0x9cdf : "憑",
0x9ce0 : "憫",
0x9ce1 : "憮",
0x9ce2 : "懌",
0x9ce3 : "懊",
0x9ce4 : "應",
0x9ce5 : "懷",
0x9ce6 : "懈",
0x9ce7 : "懃",
0x9ce8 : "懆",
0x9ce9 : "憺",
0x9cea : "懋",
0x9ceb : "罹",
0x9cec : "懍",
0x9ced : "懦",
0x9cee : "懣",
0x9cef : "懶",
0x9cf0 : "懺",
0x9cf1 : "懴",
0x9cf2 : "懿",
0x9cf3 : "懽",
0x9cf4 : "懼",
0x9cf5 : "懾",
0x9cf6 : "戀",
0x9cf7 : "戈",
0x9cf8 : "戉",
0x9cf9 : "戍",
0x9cfa : "戌",
0x9cfb : "戔",
0x9cfc : "戛",
0x9d40 : "戞",
0x9d41 : "戡",
0x9d42 : "截",
0x9d43 : "戮",
0x9d44 : "戰",
0x9d45 : "戲",
0x9d46 : "戳",
0x9d47 : "扁",
0x9d48 : "扎",
0x9d49 : "扞",
0x9d4a : "扣",
0x9d4b : "扛",
0x9d4c : "扠",
0x9d4d : "扨",
0x9d4e : "扼",
0x9d4f : "抂",
0x9d50 : "抉",
0x9d51 : "找",
0x9d52 : "抒",
0x9d53 : "抓",
0x9d54 : "抖",
0x9d55 : "拔",
0x9d56 : "抃",
0x9d57 : "抔",
0x9d58 : "拗",
0x9d59 : "拑",
0x9d5a : "抻",
0x9d5b : "拏",
0x9d5c : "拿",
0x9d5d : "拆",
0x9d5e : "擔",
0x9d5f : "拈",
0x9d60 : "拜",
0x9d61 : "拌",
0x9d62 : "拊",
0x9d63 : "拂",
0x9d64 : "拇",
0x9d65 : "抛",
0x9d66 : "拉",
0x9d67 : "挌",
0x9d68 : "拮",
0x9d69 : "拱",
0x9d6a : "挧",
0x9d6b : "挂",
0x9d6c : "挈",
0x9d6d : "拯",
0x9d6e : "拵",
0x9d6f : "捐",
0x9d70 : "挾",
0x9d71 : "捍",
0x9d72 : "搜",
0x9d9f : "據",
0x9da0 : "擒",
0x9da1 : "擅",
0x9da2 : "擇",
0x9da3 : "撻",
0x9da4 : "擘",
0x9da5 : "擂",
0x9da6 : "擱",
0x9da7 : "擧",
0x9da8 : "舉",
0x9da9 : "擠",
0x9daa : "擡",
0x9dab : "抬",
0x9dac : "擣",
0x9dad : "擯",
0x9dae : "攬",
0x9daf : "擶",
0x9db0 : "擴",
0x9db1 : "擲",
0x9db2 : "擺",
0x9db3 : "攀",
0x9db4 : "擽",
0x9db5 : "攘",
0x9db6 : "攜",
0x9db7 : "攅",
0x9db8 : "攤",
0x9db9 : "攣",
0x9dba : "攫",
0x9dbb : "攴",
0x9dbc : "攵",
0x9dbd : "攷",
0x9dbe : "收",
0x9dbf : "攸",
0x9dc0 : "畋",
0x9dc1 : "效",
0x9dc2 : "敖",
0x9dc3 : "敕",
0x9dc4 : "敍",
0x9dc5 : "敘",
0x9dc6 : "敞",
0x9dc7 : "敝",
0x9dc8 : "敲",
0x9dc9 : "數",
0x9dca : "斂",
0x9dcb : "斃",
0x9dcc : "變",
0x9dcd : "斛",
0x9dce : "斟",
0x9dcf : "斫",
0x9dd0 : "斷",
0x9dd1 : "旃",
0x9dd2 : "旆",
0x9dd3 : "旁",
0x9dd4 : "旄",
0x9dd5 : "旌",
0x9dd6 : "旒",
0x9dd7 : "旛",
0x9dd8 : "旙",
0x9dd9 : "无",
0x9dda : "旡",
0x9ddb : "旱",
0x9ddc : "杲",
0x9ddd : "昊",
0x9dde : "昃",
0x9ddf : "旻",
0x9de0 : "杳",
0x9de1 : "昵",
0x9de2 : "昶",
0x9de3 : "昴",
0x9de4 : "昜",
0x9de5 : "晏",
0x9de6 : "晄",
0x9de7 : "晉",
0x9de8 : "晁",
0x9de9 : "晞",
0x9dea : "晝",
0x9deb : "晤",
0x9dec : "晧",
0x9ded : "晨",
0x9dee : "晟",
0x9def : "晢",
0x9df0 : "晰",
0x9df1 : "暃",
0x9df2 : "暈",
0x9df3 : "暎",
0x9df4 : "暉",
0x9df5 : "暄",
0x9df6 : "暘",
0x9df7 : "暝",
0x9df8 : "曁",
0x9df9 : "暹",
0x9dfa : "曉",
0x9dfb : "暾",
0x9dfc : "暼",
0x9e40 : "曄",
0x9e41 : "暸",
0x9e42 : "曖",
0x9e43 : "曚",
0x9e44 : "曠",
0x9e45 : "昿",
0x9e46 : "曦",
0x9e47 : "曩",
0x9e48 : "曰",
0x9e49 : "曵",
0x9e4a : "曷",
0x9e4b : "朏",
0x9e4c : "朖",
0x9e4d : "朞",
0x9e4e : "朦",
0x9e4f : "朧",
0x9e50 : "霸",
0x9e51 : "朮",
0x9e52 : "朿",
0x9e53 : "朶",
0x9e54 : "杁",
0x9e55 : "朸",
0x9e56 : "朷",
0x9e57 : "杆",
0x9e58 : "杞",
0x9e59 : "杠",
0x9e5a : "杙",
0x9e5b : "杣",
0x9e5c : "杤",
0x9e5d : "枉",
0x9e5e : "杰",
0x9e5f : "枩",
0x9e60 : "杼",
0x9e61 : "杪",
0x9e62 : "枌",
0x9e63 : "枋",
0x9e64 : "枦",
0x9e65 : "枡",
0x9e66 : "枅",
0x9e67 : "枷",
0x9e68 : "柯",
0x9e69 : "枴",
0x9e6a : "柬",
0x9e6b : "枳",
0x9e6c : "柩",
0x9e6d : "枸",
0x9e6e : "柤",
0x9e6f : "柞",
0x9e70 : "柝",
0x9e71 : "柢",
0x9e72 : "柮",
0x9e73 : "枹",
0x9e74 : "柎",
0x9e75 : "柆",
0x9e76 : "柧",
0x9e77 : "檜",
0x9e78 : "栞",
0x9e79 : "框",
0x9e7a : "栩",
0x9e7b : "桀",
0x9e7c : "桍",
0x9e7d : "栲",
0x9e7e : "桎",
0x9e80 : "梳",
0x9e81 : "栫",
0x9e82 : "桙",
0x9e83 : "档",
0x9e84 : "桷",
0x9e85 : "桿",
0x9e86 : "梟",
0x9e87 : "梏",
0x9e88 : "梭",
0x9e89 : "梔",
0x9e8a : "條",
0x9e8b : "梛",
0x9e8c : "梃",
0x9e8d : "檮",
0x9e8e : "梹",
0x9e8f : "桴",
0x9e90 : "梵",
0x9e91 : "梠",
0x9e92 : "梺",
0x9e93 : "椏",
0x9e94 : "梍",
0x9e95 : "桾",
0x9e96 : "椁",
0x9e97 : "棊",
0x9e98 : "椈",
0x9e99 : "棘",
0x9e9a : "椢",
0x9e9b : "椦",
0x9e9c : "棡",
0x9e9d : "椌",
0x9e9e : "棍",
0x9e9f : "棔",
0x9ea0 : "棧",
0x9ea1 : "棕",
0x9ea2 : "椶",
0x9ea3 : "椒",
0x9ea4 : "椄",
0x9ea5 : "棗",
0x9ea6 : "棣",
0x9ea7 : "椥",
0x9ea8 : "棹",
0x9ea9 : "棠",
0x9eaa : "棯",
0x9eab : "椨",
0x9eac : "椪",
0x9ead : "椚",
0x9eae : "椣",
0x9eaf : "椡",
0x9eb0 : "棆",
0x9eb1 : "楹",
0x9eb2 : "楷",
0x9eb3 : "楜",
0x9eb4 : "楸",
0x9eb5 : "楫",
0x9eb6 : "楔",
0x9eb7 : "楾",
0x9eb8 : "楮",
0x9eb9 : "椹",
0x9eba : "楴",
0x9ebb : "椽",
0x9ebc : "楙",
0x9ebd : "椰",
0x9ebe : "楡",
0x9ebf : "楞",
0x9ec0 : "楝",
0x9ec1 : "榁",
0x9ec2 : "楪",
0x9ec3 : "榲",
0x9ec4 : "榮",
0x9ec5 : "槐",
0x9ec6 : "榿",
0x9ec7 : "槁",
0x9ec8 : "槓",
0x9ec9 : "榾",
0x9eca : "槎",
0x9ecb : "寨",
0x9ecc : "槊",
0x9ecd : "槝",
0x9ece : "榻",
0x9ecf : "槃",
0x9ed0 : "榧",
0x9ed1 : "樮",
0x9ed2 : "榑",
0x9ed3 : "榠",
0x9ed4 : "榜",
0x9ed5 : "榕",
0x9ed6 : "榴",
0x9ed7 : "槞",
0x9ed8 : "槨",
0x9ed9 : "樂",
0x9eda : "樛",
0x9edb : "槿",
0x9edc : "權",
0x9edd : "槹",
0x9ede : "槲",
0x9edf : "槧",
0x9ee0 : "樅",
0x9ee1 : "榱",
0x9ee2 : "樞",
0x9ee3 : "槭",
0x9ee4 : "樔",
0x9ee5 : "槫",
0x9ee6 : "樊",
0x9ee7 : "樒",
0x9ee8 : "櫁",
0x9ee9 : "樣",
0x9eea : "樓",
0x9eeb : "橄",
0x9eec : "樌",
0x9eed : "橲",
0x9eee : "樶",
0x9eef : "橸",
0x9ef0 : "橇",
0x9ef1 : "橢",
0x9ef2 : "橙",
0x9ef3 : "橦",
0x9ef4 : "橈",
0x9ef5 : "樸",
0x9ef6 : "樢",
0x9ef7 : "檐",
0x9ef8 : "檍",
0x9ef9 : "檠",
0x9efa : "檄",
0x9efb : "檢",
0x9efc : "檣",
0x9f40 : "檗",
0x9f41 : "蘗",
0x9f42 : "檻",
0x9f43 : "櫃",
0x9f44 : "櫂",
0x9f45 : "檸",
0x9f46 : "檳",
0x9f47 : "檬",
0x9f48 : "櫞",
0x9f49 : "櫑",
0x9f4a : "櫟",
0x9f4b : "檪",
0x9f4c : "櫚",
0x9f4d : "櫪",
0x9f4e : "櫻",
0x9f4f : "欅",
0x9f50 : "蘖",
0x9f51 : "櫺",
0x9f52 : "欒",
0x9f53 : "欖",
0x9f54 : "鬱",
0x9f55 : "欟",
0x9f56 : "欸",
0x9f57 : "欷",
0x9f58 : "盜",
0x9f59 : "欹",
0x9f5a : "飮",
0x9f5b : "歇",
0x9f5c : "歃",
0x9f5d : "歉",
0x9f5e : "歐",
0x9f5f : "歙",
0x9f60 : "歔",
0x9f61 : "歛",
0x9f62 : "歟",
0x9f63 : "歡",
0x9f64 : "歸",
0x9f65 : "歹",
0x9f66 : "歿",
0x9f67 : "殀",
0x9f68 : "殄",
0x9f69 : "殃",
0x9f6a : "殍",
0x9f6b : "殘",
0x9f6c : "殕",
0x9f6d : "殞",
0x9f6e : "殤",
0x9f6f : "殪",
0x9f70 : "殫",
0x9f71 : "殯",
0x9f72 : "殲",
0x9f73 : "殱",
0x9f74 : "殳",
0x9f75 : "殷",
0x9f76 : "殼",
0x9f77 : "毆",
0x9f78 : "毋",
0x9f79 : "毓",
0x9f7a : "毟",
0x9f7b : "毬",
0x9f7c : "毫",
0x9f7d : "毳",
0x9f7e : "毯",
0x9f80 : "麾",
0x9f81 : "氈",
0x9f82 : "氓",
0x9f83 : "气",
0x9f84 : "氛",
0x9f85 : "氤",
0x9f86 : "氣",
0x9f87 : "汞",
0x9f88 : "汕",
0x9f89 : "汢",
0x9f8a : "汪",
0x9f8b : "沂",
0x9f8c : "沍",
0x9f8d : "沚",
0x9f8e : "沁",
0x9f8f : "沛",
0x9f90 : "汾",
0x9f91 : "汨",
0x9f92 : "汳",
0x9f93 : "沒",
0x9f94 : "沐",
0x9f95 : "泄",
0x9f96 : "泱",
0x9f97 : "泓",
0x9f98 : "沽",
0x9f99 : "泗",
0x9f9a : "泅",
0x9f9b : "泝",
0x9f9c : "沮",
0x9f9d : "沱",
0x9f9e : "沾",
0x9f9f : "沺",
0x9fa0 : "泛",
0x9fa1 : "泯",
0x9fa2 : "泙",
0x9fa3 : "泪",
0x9fa4 : "洟",
0x9fa5 : "衍",
0x9fa6 : "洶",
0x9fa7 : "洫",
0x9fa8 : "洽",
0x9fa9 : "洸",
0x9faa : "洙",
0x9fab : "洵",
0x9fac : "洳",
0x9fad : "洒",
0x9fae : "洌",
0x9faf : "浣",
0x9fb0 : "涓",
0x9fb1 : "浤",
0x9fb2 : "浚",
0x9fb3 : "浹",
0x9fb4 : "浙",
0x9fb5 : "涎",
0x9fb6 : "涕",
0x9fb7 : "濤",
0x9fb8 : "涅",
0x9fb9 : "淹",
0x9fba : "渕",
0x9fbb : "渊",
0x9fbc : "涵",
0x9fbd : "淇",
0x9fbe : "淦",
0x9fbf : "涸",
0x9fc0 : "淆",
0x9fc1 : "淬",
0x9fc2 : "淞",
0x9fc3 : "淌",
0x9fc4 : "淨",
0x9fc5 : "淒",
0x9fc6 : "淅",
0x9fc7 : "淺",
0x9fc8 : "淙",
0x9fc9 : "淤",
0x9fca : "淕",
0x9fcb : "淪",
0x9fcc : "淮",
0x9fcd : "渭",
0x9fce : "湮",
0x9fcf : "渮",
0x9fd0 : "渙",
0x9fd1 : "湲",
0x9fd2 : "湟",
0x9fd3 : "渾",
0x9fd4 : "渣",
0x9fd5 : "湫",
0x9fd6 : "渫",
0x9fd7 : "湶",
0x9fd8 : "湍",
0x9fd9 : "渟",
0x9fda : "湃",
0x9fdb : "渺",
0x9fdc : "湎",
0x9fdd : "渤",
0x9fde : "滿",
0x9fdf : "渝",
0x9fe0 : "游",
0x9fe1 : "溂",
0x9fe2 : "溪",
0x9fe3 : "溘",
0x9fe4 : "滉",
0x9fe5 : "溷",
0x9fe6 : "滓",
0x9fe7 : "溽",
0x9fe8 : "溯",
0x9fe9 : "滄",
0x9fea : "溲",
0x9feb : "滔",
0x9fec : "滕",
0x9fed : "溏",
0x9fee : "溥",
0x9fef : "滂",
0x9ff0 : "溟",
0x9ff1 : "潁",
0x9ff2 : "漑",
0x9ff3 : "灌",
0x9ff4 : "滬",
0x9ff5 : "滸",
0x9ff6 : "滾",
0x9ff7 : "漿",
0x9ff8 : "滲",
0x9ff9 : "漱",
0x9ffa : "滯",
0x9ffb : "漲",
0x9ffc : "滌",
0xe040 : "漾",
0xe041 : "漓",
0xe042 : "滷",
0xe043 : "澆",
0xe044 : "潺",
0xe045 : "潸",
0xe046 : "澁",
0xe047 : "澀",
0xe048 : "潯",
0xe049 : "潛",
0xe04a : "濳",
0xe04b : "潭",
0xe04c : "澂",
0xe04d : "潼",
0xe04e : "潘",
0xe04f : "澎",
0xe050 : "澑",
0xe051 : "濂",
0xe052 : "潦",
0xe053 : "澳",
0xe054 : "澣",
0xe055 : "澡",
0xe056 : "澤",
0xe057 : "澹",
0xe058 : "濆",
0xe059 : "澪",
0xe05a : "濟",
0xe05b : "濕",
0xe05c : "濬",
0xe05d : "濔",
0xe05e : "濘",
0xe05f : "濱",
0xe060 : "濮",
0xe061 : "濛",
0xe062 : "瀉",
0xe063 : "瀋",
0xe064 : "濺",
0xe065 : "瀑",
0xe066 : "瀁",
0xe067 : "瀏",
0xe068 : "濾",
0xe069 : "瀛",
0xe06a : "瀚",
0xe06b : "潴",
0xe06c : "瀝",
0xe06d : "瀘",
0xe06e : "瀟",
0xe06f : "瀰",
0xe070 : "瀾",
0xe071 : "瀲",
0xe072 : "灑",
0xe073 : "灣",
0xe074 : "炙",
0xe075 : "炒",
0xe076 : "炯",
0xe077 : "烱",
0xe078 : "炬",
0xe079 : "炸",
0xe07a : "炳",
0xe07b : "炮",
0xe07c : "烟",
0xe07d : "烋",
0xe07e : "烝",
0xe080 : "烙",
0xe081 : "焉",
0xe082 : "烽",
0xe083 : "焜",
0xe084 : "焙",
0xe085 : "煥",
0xe086 : "煕",
0xe087 : "熈",
0xe088 : "煦",
0xe089 : "煢",
0xe08a : "煌",
0xe08b : "煖",
0xe08c : "煬",
0xe08d : "熏",
0xe08e : "燻",
0xe08f : "熄",
0xe090 : "熕",
0xe091 : "熨",
0xe092 : "熬",
0xe093 : "燗",
0xe094 : "熹",
0xe095 : "熾",
0xe096 : "燒",
0xe097 : "燉",
0xe098 : "燔",
0xe099 : "燎",
0xe09a : "燠",
0xe09b : "燬",
0xe09c : "燧",
0xe09d : "燵",
0xe09e : "燼",
0xe09f : "燹",
0xe0a0 : "燿",
0xe0a1 : "爍",
0xe0a2 : "爐",
0xe0a3 : "爛",
0xe0a4 : "爨",
0xe0a5 : "爭",
0xe0a6 : "爬",
0xe0a7 : "爰",
0xe0a8 : "爲",
0xe0a9 : "爻",
0xe0aa : "爼",
0xe0ab : "爿",
0xe0ac : "牀",
0xe0ad : "牆",
0xe0ae : "牋",
0xe0af : "牘",
0xe0b0 : "牴",
0xe0b1 : "牾",
0xe0b2 : "犂",
0xe0b3 : "犁",
0xe0b4 : "犇",
0xe0b5 : "犒",
0xe0b6 : "犖",
0xe0b7 : "犢",
0xe0b8 : "犧",
0xe0b9 : "犹",
0xe0ba : "犲",
0xe0bb : "狃",
0xe0bc : "狆",
0xe0bd : "狄",
0xe0be : "狎",
0xe0bf : "狒",
0xe0c0 : "狢",
0xe0c1 : "狠",
0xe0c2 : "狡",
0xe0c3 : "狹",
0xe0c4 : "狷",
0xe0c5 : "倏",
0xe0c6 : "猗",
0xe0c7 : "猊",
0xe0c8 : "猜",
0xe0c9 : "猖",
0xe0ca : "猝",
0xe0cb : "猴",
0xe0cc : "猯",
0xe0cd : "猩",
0xe0ce : "猥",
0xe0cf : "猾",
0xe0d0 : "獎",
0xe0d1 : "獏",
0xe0d2 : "默",
0xe0d3 : "獗",
0xe0d4 : "獪",
0xe0d5 : "獨",
0xe0d6 : "獰",
0xe0d7 : "獸",
0xe0d8 : "獵",
0xe0d9 : "獻",
0xe0da : "獺",
0xe0db : "珈",
0xe0dc : "玳",
0xe0dd : "珎",
0xe0de : "玻",
0xe0df : "珀",
0xe0e0 : "珥",
0xe0e1 : "珮",
0xe0e2 : "珞",
0xe0e3 : "璢",
0xe0e4 : "琅",
0xe0e5 : "瑯",
0xe0e6 : "琥",
0xe0e7 : "珸",
0xe0e8 : "琲",
0xe0e9 : "琺",
0xe0ea : "瑕",
0xe0eb : "琿",
0xe0ec : "瑟",
0xe0ed : "瑙",
0xe0ee : "瑁",
0xe0ef : "瑜",
0xe0f0 : "瑩",
0xe0f1 : "瑰",
0xe0f2 : "瑣",
0xe0f3 : "瑪",
0xe0f4 : "瑶",
0xe0f5 : "瑾",
0xe0f6 : "璋",
0xe0f7 : "璞",
0xe0f8 : "璧",
0xe0f9 : "瓊",
0xe0fa : "瓏",
0xe0fb : "瓔",
0xe0fc : "珱",
0xe140 : "瓠",
0xe141 : "瓣",
0xe142 : "瓧",
0xe143 : "瓩",
0xe144 : "瓮",
0xe145 : "瓲",
0xe146 : "瓰",
0xe147 : "瓱",
0xe148 : "瓸",
0xe149 : "瓷",
0xe14a : "甄",
0xe14b : "甃",
0xe14c : "甅",
0xe14d : "甌",
0xe14e : "甎",
0xe14f : "甍",
0xe150 : "甕",
0xe151 : "甓",
0xe152 : "甞",
0xe153 : "甦",
0xe154 : "甬",
0xe155 : "甼",
0xe156 : "畄",
0xe157 : "畍",
0xe158 : "畊",
0xe159 : "畉",
0xe15a : "畛",
0xe15b : "畆",
0xe15c : "畚",
0xe15d : "畩",
0xe15e : "畤",
0xe15f : "畧",
0xe160 : "畫",
0xe161 : "畭",
0xe162 : "畸",
0xe163 : "當",
0xe164 : "疆",
0xe165 : "疇",
0xe166 : "畴",
0xe167 : "疊",
0xe168 : "疉",
0xe169 : "疂",
0xe16a : "疔",
0xe16b : "疚",
0xe16c : "疝",
0xe16d : "疥",
0xe16e : "疣",
0xe16f : "痂",
0xe170 : "疳",
0xe171 : "痃",
0xe172 : "疵",
0xe173 : "疽",
0xe174 : "疸",
0xe175 : "疼",
0xe176 : "疱",
0xe177 : "痍",
0xe178 : "痊",
0xe179 : "痒",
0xe17a : "痙",
0xe17b : "痣",
0xe17c : "痞",
0xe17d : "痾",
0xe17e : "痿",
0xe180 : "痼",
0xe181 : "瘁",
0xe182 : "痰",
0xe183 : "痺",
0xe184 : "痲",
0xe185 : "痳",
0xe186 : "瘋",
0xe187 : "瘍",
0xe188 : "瘉",
0xe189 : "瘟",
0xe18a : "瘧",
0xe18b : "瘠",
0xe18c : "瘡",
0xe18d : "瘢",
0xe18e : "瘤",
0xe18f : "瘴",
0xe190 : "瘰",
0xe191 : "瘻",
0xe192 : "癇",
0xe193 : "癈",
0xe194 : "癆",
0xe195 : "癜",
0xe196 : "癘",
0xe197 : "癡",
0xe198 : "癢",
0xe199 : "癨",
0xe19a : "癩",
0xe19b : "癪",
0xe19c : "癧",
0xe19d : "癬",
0xe19e : "癰",
0xe19f : "癲",
0xe1a0 : "癶",
0xe1a1 : "癸",
0xe1a2 : "發",
0xe1a3 : "皀",
0xe1a4 : "皃",
0xe1a5 : "皈",
0xe1a6 : "皋",
0xe1a7 : "皎",
0xe1a8 : "皖",
0xe1a9 : "皓",
0xe1aa : "皙",
0xe1ab : "皚",
0xe1ac : "皰",
0xe1ad : "皴",
0xe1ae : "皸",
0xe1af : "皹",
0xe1b0 : "皺",
0xe1b1 : "盂",
0xe1b2 : "盍",
0xe1b3 : "盖",
0xe1b4 : "盒",
0xe1b5 : "盞",
0xe1b6 : "盡",
0xe1b7 : "盥",
0xe1b8 : "盧",
0xe1b9 : "盪",
0xe1ba : "蘯",
0xe1bb : "盻",
0xe1bc : "眈",
0xe1bd : "眇",
0xe1be : "眄",
0xe1bf : "眩",
0xe1c0 : "眤",
0xe1c1 : "眞",
0xe1c2 : "眥",
0xe1c3 : "眦",
0xe1c4 : "眛",
0xe1c5 : "眷",
0xe1c6 : "眸",
0xe1c7 : "睇",
0xe1c8 : "睚",
0xe1c9 : "睨",
0xe1ca : "睫",
0xe1cb : "睛",
0xe1cc : "睥",
0xe1cd : "睿",
0xe1ce : "睾",
0xe1cf : "睹",
0xe1d0 : "瞎",
0xe1d1 : "瞋",
0xe1d2 : "瞑",
0xe1d3 : "瞠",
0xe1d4 : "瞞",
0xe1d5 : "瞰",
0xe1d6 : "瞶",
0xe1d7 : "瞹",
0xe1d8 : "瞿",
0xe1d9 : "瞼",
0xe1da : "瞽",
0xe1db : "瞻",
0xe1dc : "矇",
0xe1dd : "矍",
0xe1de : "矗",
0xe1df : "矚",
0xe1e0 : "矜",
0xe1e1 : "矣",
0xe1e2 : "矮",
0xe1e3 : "矼",
0xe1e4 : "砌",
0xe1e5 : "砒",
0xe1e6 : "礦",
0xe1e7 : "砠",
0xe1e8 : "礪",
0xe1e9 : "硅",
0xe1ea : "碎",
0xe1eb : "硴",
0xe1ec : "碆",
0xe1ed : "硼",
0xe1ee : "碚",
0xe1ef : "碌",
0xe1f0 : "碣",
0xe1f1 : "碵",
0xe1f2 : "碪",
0xe1f3 : "碯",
0xe1f4 : "磑",
0xe1f5 : "磆",
0xe1f6 : "磋",
0xe1f7 : "磔",
0xe1f8 : "碾",
0xe1f9 : "碼",
0xe1fa : "磅",
0xe1fb : "磊",
0xe1fc : "磬",
0xe240 : "磧",
0xe241 : "磚",
0xe242 : "磽",
0xe243 : "磴",
0xe244 : "礇",
0xe245 : "礒",
0xe246 : "礑",
0xe247 : "礙",
0xe248 : "礬",
0xe249 : "礫",
0xe24a : "祀",
0xe24b : "祠",
0xe24c : "祗",
0xe24d : "祟",
0xe24e : "祚",
0xe24f : "祕",
0xe250 : "祓",
0xe251 : "祺",
0xe252 : "祿",
0xe253 : "禊",
0xe254 : "禝",
0xe255 : "禧",
0xe256 : "齋",
0xe257 : "禪",
0xe258 : "禮",
0xe259 : "禳",
0xe25a : "禹",
0xe25b : "禺",
0xe25c : "秉",
0xe25d : "秕",
0xe25e : "秧",
0xe25f : "秬",
0xe260 : "秡",
0xe261 : "秣",
0xe262 : "稈",
0xe263 : "稍",
0xe264 : "稘",
0xe265 : "稙",
0xe266 : "稠",
0xe267 : "稟",
0xe268 : "禀",
0xe269 : "稱",
0xe26a : "稻",
0xe26b : "稾",
0xe26c : "稷",
0xe26d : "穃",
0xe26e : "穗",
0xe26f : "穉",
0xe270 : "穡",
0xe271 : "穢",
0xe272 : "穩",
0xe29f : "筺",
0xe2a0 : "笄",
0xe2a1 : "筍",
0xe2a2 : "笋",
0xe2a3 : "筌",
0xe2a4 : "筅",
0xe2a5 : "筵",
0xe2a6 : "筥",
0xe2a7 : "筴",
0xe2a8 : "筧",
0xe2a9 : "筰",
0xe2aa : "筱",
0xe2ab : "筬",
0xe2ac : "筮",
0xe2ad : "箝",
0xe2ae : "箘",
0xe2af : "箟",
0xe2b0 : "箍",
0xe2b1 : "箜",
0xe2b2 : "箚",
0xe2b3 : "箋",
0xe2b4 : "箒",
0xe2b5 : "箏",
0xe2b6 : "筝",
0xe2b7 : "箙",
0xe2b8 : "篋",
0xe2b9 : "篁",
0xe2ba : "篌",
0xe2bb : "篏",
0xe2bc : "箴",
0xe2bd : "篆",
0xe2be : "篝",
0xe2bf : "篩",
0xe2c0 : "簑",
0xe2c1 : "簔",
0xe2c2 : "篦",
0xe2c3 : "篥",
0xe2c4 : "籠",
0xe2c5 : "簀",
0xe2c6 : "簇",
0xe2c7 : "簓",
0xe2c8 : "篳",
0xe2c9 : "篷",
0xe2ca : "簗",
0xe2cb : "簍",
0xe2cc : "篶",
0xe2cd : "簣",
0xe2ce : "簧",
0xe2cf : "簪",
0xe2d0 : "簟",
0xe2d1 : "簷",
0xe2d2 : "簫",
0xe2d3 : "簽",
0xe2d4 : "籌",
0xe2d5 : "籃",
0xe2d6 : "籔",
0xe2d7 : "籏",
0xe2d8 : "籀",
0xe2d9 : "籐",
0xe2da : "籘",
0xe2db : "籟",
0xe2dc : "籤",
0xe2dd : "籖",
0xe2de : "籥",
0xe2df : "籬",
0xe2e0 : "籵",
0xe2e1 : "粃",
0xe2e2 : "粐",
0xe2e3 : "粤",
0xe2e4 : "粭",
0xe2e5 : "粢",
0xe2e6 : "粫",
0xe2e7 : "粡",
0xe2e8 : "粨",
0xe2e9 : "粳",
0xe2ea : "粲",
0xe2eb : "粱",
0xe2ec : "粮",
0xe2ed : "粹",
0xe2ee : "粽",
0xe2ef : "糀",
0xe2f0 : "糅",
0xe2f1 : "糂",
0xe2f2 : "糘",
0xe2f3 : "糒",
0xe2f4 : "糜",
0xe2f5 : "糢",
0xe2f6 : "鬻",
0xe2f7 : "糯",
0xe2f8 : "糲",
0xe2f9 : "糴",
0xe2fa : "糶",
0xe2fb : "糺",
0xe2fc : "紆",
0xe340 : "紂",
0xe341 : "紜",
0xe342 : "紕",
0xe343 : "紊",
0xe344 : "絅",
0xe345 : "絋",
0xe346 : "紮",
0xe347 : "紲",
0xe348 : "紿",
0xe349 : "紵",
0xe34a : "絆",
0xe34b : "絳",
0xe34c : "絖",
0xe34d : "絎",
0xe34e : "絲",
0xe34f : "絨",
0xe350 : "絮",
0xe351 : "絏",
0xe352 : "絣",
0xe353 : "經",
0xe354 : "綉",
0xe355 : "絛",
0xe356 : "綏",
0xe357 : "絽",
0xe358 : "綛",
0xe359 : "綺",
0xe35a : "綮",
0xe35b : "綣",
0xe35c : "綵",
0xe35d : "緇",
0xe35e : "綽",
0xe35f : "綫",
0xe360 : "總",
0xe361 : "綢",
0xe362 : "綯",
0xe363 : "緜",
0xe364 : "綸",
0xe365 : "綟",
0xe366 : "綰",
0xe367 : "緘",
0xe368 : "緝",
0xe369 : "緤",
0xe36a : "緞",
0xe36b : "緻",
0xe36c : "緲",
0xe36d : "緡",
0xe36e : "縅",
0xe36f : "縊",
0xe370 : "縣",
0xe371 : "縡",
0xe372 : "縒",
0xe373 : "縱",
0xe374 : "縟",
0xe375 : "縉",
0xe376 : "縋",
0xe377 : "縢",
0xe378 : "繆",
0xe379 : "繦",
0xe37a : "縻",
0xe37b : "縵",
0xe37c : "縹",
0xe37d : "繃",
0xe37e : "縷",
0xe380 : "縲",
0xe381 : "縺",
0xe382 : "繧",
0xe383 : "繝",
0xe384 : "繖",
0xe385 : "繞",
0xe386 : "繙",
0xe387 : "繚",
0xe388 : "繹",
0xe389 : "繪",
0xe38a : "繩",
0xe38b : "繼",
0xe38c : "繻",
0xe38d : "纃",
0xe38e : "緕",
0xe38f : "繽",
0xe390 : "辮",
0xe391 : "繿",
0xe392 : "纈",
0xe393 : "纉",
0xe394 : "續",
0xe395 : "纒",
0xe396 : "纐",
0xe397 : "纓",
0xe398 : "纔",
0xe399 : "纖",
0xe39a : "纎",
0xe39b : "纛",
0xe39c : "纜",
0xe39d : "缸",
0xe39e : "缺",
0xe39f : "罅",
0xe3a0 : "罌",
0xe3a1 : "罍",
0xe3a2 : "罎",
0xe3a3 : "罐",
0xe3a4 : "网",
0xe3a5 : "罕",
0xe3a6 : "罔",
0xe3a7 : "罘",
0xe3a8 : "罟",
0xe3a9 : "罠",
0xe3aa : "罨",
0xe3ab : "罩",
0xe3ac : "罧",
0xe3ad : "罸",
0xe3ae : "羂",
0xe3af : "羆",
0xe3b0 : "羃",
0xe3b1 : "羈",
0xe3b2 : "羇",
0xe3b3 : "羌",
0xe3b4 : "羔",
0xe3b5 : "羞",
0xe3b6 : "羝",
0xe3b7 : "羚",
0xe3b8 : "羣",
0xe3b9 : "羯",
0xe3ba : "羲",
0xe3bb : "羹",
0xe3bc : "羮",
0xe3bd : "羶",
0xe3be : "羸",
0xe3bf : "譱",
0xe3c0 : "翅",
0xe3c1 : "翆",
0xe3c2 : "翊",
0xe3c3 : "翕",
0xe3c4 : "翔",
0xe3c5 : "翡",
0xe3c6 : "翦",
0xe3c7 : "翩",
0xe3c8 : "翳",
0xe3c9 : "翹",
0xe3ca : "飜",
0xe3cb : "耆",
0xe3cc : "耄",
0xe3cd : "耋",
0xe3ce : "耒",
0xe3cf : "耘",
0xe3d0 : "耙",
0xe3d1 : "耜",
0xe3d2 : "耡",
0xe3d3 : "耨",
0xe3d4 : "耿",
0xe3d5 : "耻",
0xe3d6 : "聊",
0xe3d7 : "聆",
0xe3d8 : "聒",
0xe3d9 : "聘",
0xe3da : "聚",
0xe3db : "聟",
0xe3dc : "聢",
0xe3dd : "聨",
0xe3de : "聳",
0xe3df : "聲",
0xe3e0 : "聰",
0xe3e1 : "聶",
0xe3e2 : "聹",
0xe3e3 : "聽",
0xe3e4 : "聿",
0xe3e5 : "肄",
0xe3e6 : "肆",
0xe3e7 : "肅",
0xe3e8 : "肛",
0xe3e9 : "肓",
0xe3ea : "肚",
0xe3eb : "肭",
0xe3ec : "冐",
0xe3ed : "肬",
0xe3ee : "胛",
0xe3ef : "胥",
0xe3f0 : "胙",
0xe3f1 : "胝",
0xe3f2 : "胄",
0xe3f3 : "胚",
0xe3f4 : "胖",
0xe3f5 : "脉",
0xe3f6 : "胯",
0xe3f7 : "胱",
0xe3f8 : "脛",
0xe3f9 : "脩",
0xe3fa : "脣",
0xe3fb : "脯",
0xe3fc : "腋",
0xe440 : "隋",
0xe441 : "腆",
0xe442 : "脾",
0xe443 : "腓",
0xe444 : "腑",
0xe445 : "胼",
0xe446 : "腱",
0xe447 : "腮",
0xe448 : "腥",
0xe449 : "腦",
0xe44a : "腴",
0xe44b : "膃",
0xe44c : "膈",
0xe44d : "膊",
0xe44e : "膀",
0xe44f : "膂",
0xe450 : "膠",
0xe451 : "膕",
0xe452 : "膤",
0xe453 : "膣",
0xe454 : "腟",
0xe455 : "膓",
0xe456 : "膩",
0xe457 : "膰",
0xe458 : "膵",
0xe459 : "膾",
0xe45a : "膸",
0xe45b : "膽",
0xe45c : "臀",
0xe45d : "臂",
0xe45e : "膺",
0xe45f : "臉",
0xe460 : "臍",
0xe461 : "臑",
0xe462 : "臙",
0xe463 : "臘",
0xe464 : "臈",
0xe465 : "臚",
0xe466 : "臟",
0xe467 : "臠",
0xe468 : "臧",
0xe469 : "臺",
0xe46a : "臻",
0xe46b : "臾",
0xe46c : "舁",
0xe46d : "舂",
0xe46e : "舅",
0xe46f : "與",
0xe470 : "舊",
0xe471 : "舍",
0xe472 : "舐",
0xe473 : "舖",
0xe474 : "舩",
0xe475 : "舫",
0xe476 : "舸",
0xe477 : "舳",
0xe478 : "艀",
0xe479 : "艙",
0xe47a : "艘",
0xe47b : "艝",
0xe47c : "艚",
0xe47d : "艟",
0xe47e : "艤",
0xe480 : "艢",
0xe481 : "艨",
0xe482 : "艪",
0xe483 : "艫",
0xe484 : "舮",
0xe485 : "艱",
0xe486 : "艷",
0xe487 : "艸",
0xe488 : "艾",
0xe489 : "芍",
0xe48a : "芒",
0xe48b : "芫",
0xe48c : "芟",
0xe48d : "芻",
0xe48e : "芬",
0xe48f : "苡",
0xe490 : "苣",
0xe491 : "苟",
0xe492 : "苒",
0xe493 : "苴",
0xe494 : "苳",
0xe495 : "苺",
0xe496 : "莓",
0xe497 : "范",
0xe498 : "苻",
0xe499 : "苹",
0xe49a : "苞",
0xe49b : "茆",
0xe49c : "苜",
0xe49d : "茉",
0xe49e : "苙",
0xe49f : "茵",
0xe4a0 : "茴",
0xe4a1 : "茖",
0xe4a2 : "茲",
0xe4a3 : "茱",
0xe4a4 : "荀",
0xe4a5 : "茹",
0xe4a6 : "荐",
0xe4a7 : "荅",
0xe4a8 : "茯",
0xe4a9 : "茫",
0xe4aa : "茗",
0xe4ab : "茘",
0xe4ac : "莅",
0xe4ad : "莚",
0xe4ae : "莪",
0xe4af : "莟",
0xe4b0 : "莢",
0xe4b1 : "莖",
0xe4b2 : "茣",
0xe4b3 : "莎",
0xe4b4 : "莇",
0xe4b5 : "莊",
0xe4b6 : "荼",
0xe4b7 : "莵",
0xe4b8 : "荳",
0xe4b9 : "荵",
0xe4ba : "莠",
0xe4bb : "莉",
0xe4bc : "莨",
0xe4bd : "菴",
0xe4be : "萓",
0xe4bf : "菫",
0xe4c0 : "菎",
0xe4c1 : "菽",
0xe4c2 : "萃",
0xe4c3 : "菘",
0xe4c4 : "萋",
0xe4c5 : "菁",
0xe4c6 : "菷",
0xe4c7 : "萇",
0xe4c8 : "菠",
0xe4c9 : "菲",
0xe4ca : "萍",
0xe4cb : "萢",
0xe4cc : "萠",
0xe4cd : "莽",
0xe4ce : "萸",
0xe4cf : "蔆",
0xe4d0 : "菻",
0xe4d1 : "葭",
0xe4d2 : "萪",
0xe4d3 : "萼",
0xe4d4 : "蕚",
0xe4d5 : "蒄",
0xe4d6 : "葷",
0xe4d7 : "葫",
0xe4d8 : "蒭",
0xe4d9 : "葮",
0xe4da : "蒂",
0xe4db : "葩",
0xe4dc : "葆",
0xe4dd : "萬",
0xe4de : "葯",
0xe4df : "葹",
0xe4e0 : "萵",
0xe4e1 : "蓊",
0xe4e2 : "葢",
0xe4e3 : "蒹",
0xe4e4 : "蒿",
0xe4e5 : "蒟",
0xe4e6 : "蓙",
0xe4e7 : "蓍",
0xe4e8 : "蒻",
0xe4e9 : "蓚",
0xe4ea : "蓐",
0xe4eb : "蓁",
0xe4ec : "蓆",
0xe4ed : "蓖",
0xe4ee : "蒡",
0xe4ef : "蔡",
0xe4f0 : "蓿",
0xe4f1 : "蓴",
0xe4f2 : "蔗",
0xe4f3 : "蔘",
0xe4f4 : "蔬",
0xe4f5 : "蔟",
0xe4f6 : "蔕",
0xe4f7 : "蔔",
0xe4f8 : "蓼",
0xe4f9 : "蕀",
0xe4fa : "蕣",
0xe4fb : "蕘",
0xe4fc : "蕈",
0xe540 : "蕁",
0xe541 : "蘂",
0xe542 : "蕋",
0xe543 : "蕕",
0xe544 : "薀",
0xe545 : "薤",
0xe546 : "薈",
0xe547 : "薑",
0xe548 : "薊",
0xe549 : "薨",
0xe54a : "蕭",
0xe54b : "薔",
0xe54c : "薛",
0xe54d : "藪",
0xe54e : "薇",
0xe54f : "薜",
0xe550 : "蕷",
0xe551 : "蕾",
0xe552 : "薐",
0xe553 : "藉",
0xe554 : "薺",
0xe555 : "藏",
0xe556 : "薹",
0xe557 : "藐",
0xe558 : "藕",
0xe559 : "藝",
0xe55a : "藥",
0xe55b : "藜",
0xe55c : "藹",
0xe55d : "蘊",
0xe55e : "蘓",
0xe55f : "蘋",
0xe560 : "藾",
0xe561 : "藺",
0xe562 : "蘆",
0xe563 : "蘢",
0xe564 : "蘚",
0xe565 : "蘰",
0xe566 : "蘿",
0xe567 : "虍",
0xe568 : "乕",
0xe569 : "虔",
0xe56a : "號",
0xe56b : "虧",
0xe56c : "虱",
0xe56d : "蚓",
0xe56e : "蚣",
0xe56f : "蚩",
0xe570 : "蚪",
0xe571 : "蚋",
0xe572 : "蚌",
0xe573 : "蚶",
0xe574 : "蚯",
0xe575 : "蛄",
0xe576 : "蛆",
0xe577 : "蚰",
0xe578 : "蛉",
0xe579 : "蠣",
0xe57a : "蚫",
0xe57b : "蛔",
0xe57c : "蛞",
0xe57d : "蛩",
0xe57e : "蛬",
0xe580 : "蛟",
0xe581 : "蛛",
0xe582 : "蛯",
0xe583 : "蜒",
0xe584 : "蜆",
0xe585 : "蜈",
0xe586 : "蜀",
0xe587 : "蜃",
0xe588 : "蛻",
0xe589 : "蜑",
0xe58a : "蜉",
0xe58b : "蜍",
0xe58c : "蛹",
0xe58d : "蜊",
0xe58e : "蜴",
0xe58f : "蜿",
0xe590 : "蜷",
0xe591 : "蜻",
0xe592 : "蜥",
0xe593 : "蜩",
0xe594 : "蜚",
0xe595 : "蝠",
0xe596 : "蝟",
0xe597 : "蝸",
0xe598 : "蝌",
0xe599 : "蝎",
0xe59a : "蝴",
0xe59b : "蝗",
0xe59c : "蝨",
0xe59d : "蝮",
0xe59e : "蝙",
0xe59f : "蝓",
0xe5a0 : "蝣",
0xe5a1 : "蝪",
0xe5a2 : "蠅",
0xe5a3 : "螢",
0xe5a4 : "螟",
0xe5a5 : "螂",
0xe5a6 : "螯",
0xe5a7 : "蟋",
0xe5a8 : "螽",
0xe5a9 : "蟀",
0xe5aa : "蟐",
0xe5ab : "雖",
0xe5ac : "螫",
0xe5ad : "蟄",
0xe5ae : "螳",
0xe5af : "蟇",
0xe5b0 : "蟆",
0xe5b1 : "螻",
0xe5b2 : "蟯",
0xe5b3 : "蟲",
0xe5b4 : "蟠",
0xe5b5 : "蠏",
0xe5b6 : "蠍",
0xe5b7 : "蟾",
0xe5b8 : "蟶",
0xe5b9 : "蟷",
0xe5ba : "蠎",
0xe5bb : "蟒",
0xe5bc : "蠑",
0xe5bd : "蠖",
0xe5be : "蠕",
0xe5bf : "蠢",
0xe5c0 : "蠡",
0xe5c1 : "蠱",
0xe5c2 : "蠶",
0xe5c3 : "蠹",
0xe5c4 : "蠧",
0xe5c5 : "蠻",
0xe5c6 : "衄",
0xe5c7 : "衂",
0xe5c8 : "衒",
0xe5c9 : "衙",
0xe5ca : "衞",
0xe5cb : "衢",
0xe5cc : "衫",
0xe5cd : "袁",
0xe5ce : "衾",
0xe5cf : "袞",
0xe5d0 : "衵",
0xe5d1 : "衽",
0xe5d2 : "袵",
0xe5d3 : "衲",
0xe5d4 : "袂",
0xe5d5 : "袗",
0xe5d6 : "袒",
0xe5d7 : "袮",
0xe5d8 : "袙",
0xe5d9 : "袢",
0xe5da : "袍",
0xe5db : "袤",
0xe5dc : "袰",
0xe5dd : "袿",
0xe5de : "袱",
0xe5df : "裃",
0xe5e0 : "裄",
0xe5e1 : "裔",
0xe5e2 : "裘",
0xe5e3 : "裙",
0xe5e4 : "裝",
0xe5e5 : "裹",
0xe5e6 : "褂",
0xe5e7 : "裼",
0xe5e8 : "裴",
0xe5e9 : "裨",
0xe5ea : "裲",
0xe5eb : "褄",
0xe5ec : "褌",
0xe5ed : "褊",
0xe5ee : "褓",
0xe5ef : "襃",
0xe5f0 : "褞",
0xe5f1 : "褥",
0xe5f2 : "褪",
0xe5f3 : "褫",
0xe5f4 : "襁",
0xe5f5 : "襄",
0xe5f6 : "褻",
0xe5f7 : "褶",
0xe5f8 : "褸",
0xe5f9 : "襌",
0xe5fa : "褝",
0xe5fb : "襠",
0xe5fc : "襞",
0xe640 : "襦",
0xe641 : "襤",
0xe642 : "襭",
0xe643 : "襪",
0xe644 : "襯",
0xe645 : "襴",
0xe646 : "襷",
0xe647 : "襾",
0xe648 : "覃",
0xe649 : "覈",
0xe64a : "覊",
0xe64b : "覓",
0xe64c : "覘",
0xe64d : "覡",
0xe64e : "覩",
0xe64f : "覦",
0xe650 : "覬",
0xe651 : "覯",
0xe652 : "覲",
0xe653 : "覺",
0xe654 : "覽",
0xe655 : "覿",
0xe656 : "觀",
0xe657 : "觚",
0xe658 : "觜",
0xe659 : "觝",
0xe65a : "觧",
0xe65b : "觴",
0xe65c : "觸",
0xe65d : "訃",
0xe65e : "訖",
0xe65f : "訐",
0xe660 : "訌",
0xe661 : "訛",
0xe662 : "訝",
0xe663 : "訥",
0xe664 : "訶",
0xe665 : "詁",
0xe666 : "詛",
0xe667 : "詒",
0xe668 : "詆",
0xe669 : "詈",
0xe66a : "詼",
0xe66b : "詭",
0xe66c : "詬",
0xe66d : "詢",
0xe66e : "誅",
0xe66f : "誂",
0xe670 : "誄",
0xe671 : "誨",
0xe672 : "誡",
0xe673 : "誑",
0xe674 : "誥",
0xe675 : "誦",
0xe676 : "誚",
0xe677 : "誣",
0xe678 : "諄",
0xe679 : "諍",
0xe67a : "諂",
0xe67b : "諚",
0xe67c : "諫",
0xe67d : "諳",
0xe67e : "諧",
0xe680 : "諤",
0xe681 : "諱",
0xe682 : "謔",
0xe683 : "諠",
0xe684 : "諢",
0xe685 : "諷",
0xe686 : "諞",
0xe687 : "諛",
0xe688 : "謌",
0xe689 : "謇",
0xe68a : "謚",
0xe68b : "諡",
0xe68c : "謖",
0xe68d : "謐",
0xe68e : "謗",
0xe68f : "謠",
0xe690 : "謳",
0xe691 : "鞫",
0xe692 : "謦",
0xe693 : "謫",
0xe694 : "謾",
0xe695 : "謨",
0xe696 : "譁",
0xe697 : "譌",
0xe698 : "譏",
0xe699 : "譎",
0xe69a : "證",
0xe69b : "譖",
0xe69c : "譛",
0xe69d : "譚",
0xe69e : "譫",
0xe69f : "譟",
0xe6a0 : "譬",
0xe6a1 : "譯",
0xe6a2 : "譴",
0xe6a3 : "譽",
0xe6a4 : "讀",
0xe6a5 : "讌",
0xe6a6 : "讎",
0xe6a7 : "讒",
0xe6a8 : "讓",
0xe6a9 : "讖",
0xe6aa : "讙",
0xe6ab : "讚",
0xe6ac : "谺",
0xe6ad : "豁",
0xe6ae : "谿",
0xe6af : "豈",
0xe6b0 : "豌",
0xe6b1 : "豎",
0xe6b2 : "豐",
0xe6b3 : "豕",
0xe6b4 : "豢",
0xe6b5 : "豬",
0xe6b6 : "豸",
0xe6b7 : "豺",
0xe6b8 : "貂",
0xe6b9 : "貉",
0xe6ba : "貅",
0xe6bb : "貊",
0xe6bc : "貍",
0xe6bd : "貎",
0xe6be : "貔",
0xe6bf : "豼",
0xe6c0 : "貘",
0xe6c1 : "戝",
0xe6c2 : "貭",
0xe6c3 : "貪",
0xe6c4 : "貽",
0xe6c5 : "貲",
0xe6c6 : "貳",
0xe6c7 : "貮",
0xe6c8 : "貶",
0xe6c9 : "賈",
0xe6ca : "賁",
0xe6cb : "賤",
0xe6cc : "賣",
0xe6cd : "賚",
0xe6ce : "賽",
0xe6cf : "賺",
0xe6d0 : "賻",
0xe6d1 : "贄",
0xe6d2 : "贅",
0xe6d3 : "贊",
0xe6d4 : "贇",
0xe6d5 : "贏",
0xe6d6 : "贍",
0xe6d7 : "贐",
0xe6d8 : "齎",
0xe6d9 : "贓",
0xe6da : "賍",
0xe6db : "贔",
0xe6dc : "贖",
0xe6dd : "赧",
0xe6de : "赭",
0xe6df : "赱",
0xe6e0 : "赳",
0xe6e1 : "趁",
0xe6e2 : "趙",
0xe6e3 : "跂",
0xe6e4 : "趾",
0xe6e5 : "趺",
0xe6e6 : "跏",
0xe6e7 : "跚",
0xe6e8 : "跖",
0xe6e9 : "跌",
0xe6ea : "跛",
0xe6eb : "跋",
0xe6ec : "跪",
0xe6ed : "跫",
0xe6ee : "跟",
0xe6ef : "跣",
0xe6f0 : "跼",
0xe6f1 : "踈",
0xe6f2 : "踉",
0xe6f3 : "跿",
0xe6f4 : "踝",
0xe6f5 : "踞",
0xe6f6 : "踐",
0xe6f7 : "踟",
0xe6f8 : "蹂",
0xe6f9 : "踵",
0xe6fa : "踰",
0xe6fb : "踴",
0xe6fc : "蹊",
0xe740 : "蹇",
0xe741 : "蹉",
0xe742 : "蹌",
0xe743 : "蹐",
0xe744 : "蹈",
0xe745 : "蹙",
0xe746 : "蹤",
0xe747 : "蹠",
0xe748 : "踪",
0xe749 : "蹣",
0xe74a : "蹕",
0xe74b : "蹶",
0xe74c : "蹲",
0xe74d : "蹼",
0xe74e : "躁",
0xe74f : "躇",
0xe750 : "躅",
0xe751 : "躄",
0xe752 : "躋",
0xe753 : "躊",
0xe754 : "躓",
0xe755 : "躑",
0xe756 : "躔",
0xe757 : "躙",
0xe758 : "躪",
0xe759 : "躡",
0xe75a : "躬",
0xe75b : "躰",
0xe75c : "軆",
0xe75d : "躱",
0xe75e : "躾",
0xe75f : "軅",
0xe760 : "軈",
0xe761 : "軋",
0xe762 : "軛",
0xe763 : "軣",
0xe764 : "軼",
0xe765 : "軻",
0xe766 : "軫",
0xe767 : "軾",
0xe768 : "輊",
0xe769 : "輅",
0xe76a : "輕",
0xe76b : "輒",
0xe76c : "輙",
0xe76d : "輓",
0xe76e : "輜",
0xe76f : "輟",
0xe770 : "輛",
0xe771 : "輌",
0xe772 : "輦",
0xe79f : "遏",
0xe7a0 : "遐",
0xe7a1 : "遑",
0xe7a2 : "遒",
0xe7a3 : "逎",
0xe7a4 : "遉",
0xe7a5 : "逾",
0xe7a6 : "遖",
0xe7a7 : "遘",
0xe7a8 : "遞",
0xe7a9 : "遨",
0xe7aa : "遯",
0xe7ab : "遶",
0xe7ac : "隨",
0xe7ad : "遲",
0xe7ae : "邂",
0xe7af : "遽",
0xe7b0 : "邁",
0xe7b1 : "邀",
0xe7b2 : "邊",
0xe7b3 : "邉",
0xe7b4 : "邏",
0xe7b5 : "邨",
0xe7b6 : "邯",
0xe7b7 : "邱",
0xe7b8 : "邵",
0xe7b9 : "郢",
0xe7ba : "郤",
0xe7bb : "扈",
0xe7bc : "郛",
0xe7bd : "鄂",
0xe7be : "鄒",
0xe7bf : "鄙",
0xe7c0 : "鄲",
0xe7c1 : "鄰",
0xe7c2 : "酊",
0xe7c3 : "酖",
0xe7c4 : "酘",
0xe7c5 : "酣",
0xe7c6 : "酥",
0xe7c7 : "酩",
0xe7c8 : "酳",
0xe7c9 : "酲",
0xe7ca : "醋",
0xe7cb : "醉",
0xe7cc : "醂",
0xe7cd : "醢",
0xe7ce : "醫",
0xe7cf : "醯",
0xe7d0 : "醪",
0xe7d1 : "醵",
0xe7d2 : "醴",
0xe7d3 : "醺",
0xe7d4 : "釀",
0xe7d5 : "釁",
0xe7d6 : "釉",
0xe7d7 : "釋",
0xe7d8 : "釐",
0xe7d9 : "釖",
0xe7da : "釟",
0xe7db : "釡",
0xe7dc : "釛",
0xe7dd : "釼",
0xe7de : "釵",
0xe7df : "釶",
0xe7e0 : "鈞",
0xe7e1 : "釿",
0xe7e2 : "鈔",
0xe7e3 : "鈬",
0xe7e4 : "鈕",
0xe7e5 : "鈑",
0xe7e6 : "鉞",
0xe7e7 : "鉗",
0xe7e8 : "鉅",
0xe7e9 : "鉉",
0xe7ea : "鉤",
0xe7eb : "鉈",
0xe7ec : "銕",
0xe7ed : "鈿",
0xe7ee : "鉋",
0xe7ef : "鉐",
0xe7f0 : "銜",
0xe7f1 : "銖",
0xe7f2 : "銓",
0xe7f3 : "銛",
0xe7f4 : "鉚",
0xe7f5 : "鋏",
0xe7f6 : "銹",
0xe7f7 : "銷",
0xe7f8 : "鋩",
0xe7f9 : "錏",
0xe7fa : "鋺",
0xe7fb : "鍄",
0xe7fc : "錮",
0xe840 : "錙",
0xe841 : "錢",
0xe842 : "錚",
0xe843 : "錣",
0xe844 : "錺",
0xe845 : "錵",
0xe846 : "錻",
0xe847 : "鍜",
0xe848 : "鍠",
0xe849 : "鍼",
0xe84a : "鍮",
0xe84b : "鍖",
0xe84c : "鎰",
0xe84d : "鎬",
0xe84e : "鎭",
0xe84f : "鎔",
0xe850 : "鎹",
0xe851 : "鏖",
0xe852 : "鏗",
0xe853 : "鏨",
0xe854 : "鏥",
0xe855 : "鏘",
0xe856 : "鏃",
0xe857 : "鏝",
0xe858 : "鏐",
0xe859 : "鏈",
0xe85a : "鏤",
0xe85b : "鐚",
0xe85c : "鐔",
0xe85d : "鐓",
0xe85e : "鐃",
0xe85f : "鐇",
0xe860 : "鐐",
0xe861 : "鐶",
0xe862 : "鐫",
0xe863 : "鐵",
0xe864 : "鐡",
0xe865 : "鐺",
0xe866 : "鑁",
0xe867 : "鑒",
0xe868 : "鑄",
0xe869 : "鑛",
0xe86a : "鑠",
0xe86b : "鑢",
0xe86c : "鑞",
0xe86d : "鑪",
0xe86e : "鈩",
0xe86f : "鑰",
0xe870 : "鑵",
0xe871 : "鑷",
0xe872 : "鑽",
0xe873 : "鑚",
0xe874 : "鑼",
0xe875 : "鑾",
0xe876 : "钁",
0xe877 : "鑿",
0xe878 : "閂",
0xe879 : "閇",
0xe87a : "閊",
0xe87b : "閔",
0xe87c : "閖",
0xe87d : "閘",
0xe87e : "閙",
0xe880 : "閠",
0xe881 : "閨",
0xe882 : "閧",
0xe883 : "閭",
0xe884 : "閼",
0xe885 : "閻",
0xe886 : "閹",
0xe887 : "閾",
0xe888 : "闊",
0xe889 : "濶",
0xe88a : "闃",
0xe88b : "闍",
0xe88c : "闌",
0xe88d : "闕",
0xe88e : "闔",
0xe88f : "闖",
0xe890 : "關",
0xe891 : "闡",
0xe892 : "闥",
0xe893 : "闢",
0xe894 : "阡",
0xe895 : "阨",
0xe896 : "阮",
0xe897 : "阯",
0xe898 : "陂",
0xe899 : "陌",
0xe89a : "陏",
0xe89b : "陋",
0xe89c : "陷",
0xe89d : "陜",
0xe89e : "陞",
0xe89f : "陝",
0xe8a0 : "陟",
0xe8a1 : "陦",
0xe8a2 : "陲",
0xe8a3 : "陬",
0xe8a4 : "隍",
0xe8a5 : "隘",
0xe8a6 : "隕",
0xe8a7 : "隗",
0xe8a8 : "險",
0xe8a9 : "隧",
0xe8aa : "隱",
0xe8ab : "隲",
0xe8ac : "隰",
0xe8ad : "隴",
0xe8ae : "隶",
0xe8af : "隸",
0xe8b0 : "隹",
0xe8b1 : "雎",
0xe8b2 : "雋",
0xe8b3 : "雉",
0xe8b4 : "雍",
0xe8b5 : "襍",
0xe8b6 : "雜",
0xe8b7 : "霍",
0xe8b8 : "雕",
0xe8b9 : "雹",
0xe8ba : "霄",
0xe8bb : "霆",
0xe8bc : "霈",
0xe8bd : "霓",
0xe8be : "霎",
0xe8bf : "霑",
0xe8c0 : "霏",
0xe8c1 : "霖",
0xe8c2 : "霙",
0xe8c3 : "霤",
0xe8c4 : "霪",
0xe8c5 : "霰",
0xe8c6 : "霹",
0xe8c7 : "霽",
0xe8c8 : "霾",
0xe8c9 : "靄",
0xe8ca : "靆",
0xe8cb : "靈",
0xe8cc : "靂",
0xe8cd : "靉",
0xe8ce : "靜",
0xe8cf : "靠",
0xe8d0 : "靤",
0xe8d1 : "靦",
0xe8d2 : "靨",
0xe8d3 : "勒",
0xe8d4 : "靫",
0xe8d5 : "靱",
0xe8d6 : "靹",
0xe8d7 : "鞅",
0xe8d8 : "靼",
0xe8d9 : "鞁",
0xe8da : "靺",
0xe8db : "鞆",
0xe8dc : "鞋",
0xe8dd : "鞏",
0xe8de : "鞐",
0xe8df : "鞜",
0xe8e0 : "鞨",
0xe8e1 : "鞦",
0xe8e2 : "鞣",
0xe8e3 : "鞳",
0xe8e4 : "鞴",
0xe8e5 : "韃",
0xe8e6 : "韆",
0xe8e7 : "韈",
0xe8e8 : "韋",
0xe8e9 : "韜",
0xe8ea : "韭",
0xe8eb : "齏",
0xe8ec : "韲",
0xe8ed : "竟",
0xe8ee : "韶",
0xe8ef : "韵",
0xe8f0 : "頏",
0xe8f1 : "頌",
0xe8f2 : "頸",
0xe8f3 : "頤",
0xe8f4 : "頡",
0xe8f5 : "頷",
0xe8f6 : "頽",
0xe8f7 : "顆",
0xe8f8 : "顏",
0xe8f9 : "顋",
0xe8fa : "顫",
0xe8fb : "顯",
0xe8fc : "顰",
0xe940 : "顱",
0xe941 : "顴",
0xe942 : "顳",
0xe943 : "颪",
0xe944 : "颯",
0xe945 : "颱",
0xe946 : "颶",
0xe947 : "飄",
0xe948 : "飃",
0xe949 : "飆",
0xe94a : "飩",
0xe94b : "飫",
0xe94c : "餃",
0xe94d : "餉",
0xe94e : "餒",
0xe94f : "餔",
0xe950 : "餘",
0xe951 : "餡",
0xe952 : "餝",
0xe953 : "餞",
0xe954 : "餤",
0xe955 : "餠",
0xe956 : "餬",
0xe957 : "餮",
0xe958 : "餽",
0xe959 : "餾",
0xe95a : "饂",
0xe95b : "饉",
0xe95c : "饅",
0xe95d : "饐",
0xe95e : "饋",
0xe95f : "饑",
0xe960 : "饒",
0xe961 : "饌",
0xe962 : "饕",
0xe963 : "馗",
0xe964 : "馘",
0xe965 : "馥",
0xe966 : "馭",
0xe967 : "馮",
0xe968 : "馼",
0xe969 : "駟",
0xe96a : "駛",
0xe96b : "駝",
0xe96c : "駘",
0xe96d : "駑",
0xe96e : "駭",
0xe96f : "駮",
0xe970 : "駱",
0xe971 : "駲",
0xe972 : "駻",
0xe973 : "駸",
0xe974 : "騁",
0xe975 : "騏",
0xe976 : "騅",
0xe977 : "駢",
0xe978 : "騙",
0xe979 : "騫",
0xe97a : "騷",
0xe97b : "驅",
0xe97c : "驂",
0xe97d : "驀",
0xe97e : "驃",
0xe980 : "騾",
0xe981 : "驕",
0xe982 : "驍",
0xe983 : "驛",
0xe984 : "驗",
0xe985 : "驟",
0xe986 : "驢",
0xe987 : "驥",
0xe988 : "驤",
0xe989 : "驩",
0xe98a : "驫",
0xe98b : "驪",
0xe98c : "骭",
0xe98d : "骰",
0xe98e : "骼",
0xe98f : "髀",
0xe990 : "髏",
0xe991 : "髑",
0xe992 : "髓",
0xe993 : "體",
0xe994 : "髞",
0xe995 : "髟",
0xe996 : "髢",
0xe997 : "髣",
0xe998 : "髦",
0xe999 : "髯",
0xe99a : "髫",
0xe99b : "髮",
0xe99c : "髴",
0xe99d : "髱",
0xe99e : "髷",
0xe99f : "髻",
0xe9a0 : "鬆",
0xe9a1 : "鬘",
0xe9a2 : "鬚",
0xe9a3 : "鬟",
0xe9a4 : "鬢",
0xe9a5 : "鬣",
0xe9a6 : "鬥",
0xe9a7 : "鬧",
0xe9a8 : "鬨",
0xe9a9 : "鬩",
0xe9aa : "鬪",
0xe9ab : "鬮",
0xe9ac : "鬯",
0xe9ad : "鬲",
0xe9ae : "魄",
0xe9af : "魃",
0xe9b0 : "魏",
0xe9b1 : "魍",
0xe9b2 : "魎",
0xe9b3 : "魑",
0xe9b4 : "魘",
0xe9b5 : "魴",
0xe9b6 : "鮓",
0xe9b7 : "鮃",
0xe9b8 : "鮑",
0xe9b9 : "鮖",
0xe9ba : "鮗",
0xe9bb : "鮟",
0xe9bc : "鮠",
0xe9bd : "鮨",
0xe9be : "鮴",
0xe9bf : "鯀",
0xe9c0 : "鯊",
0xe9c1 : "鮹",
0xe9c2 : "鯆",
0xe9c3 : "鯏",
0xe9c4 : "鯑",
0xe9c5 : "鯒",
0xe9c6 : "鯣",
0xe9c7 : "鯢",
0xe9c8 : "鯤",
0xe9c9 : "鯔",
0xe9ca : "鯡",
0xe9cb : "鰺",
0xe9cc : "鯲",
0xe9cd : "鯱",
0xe9ce : "鯰",
0xe9cf : "鰕",
0xe9d0 : "鰔",
0xe9d1 : "鰉",
0xe9d2 : "鰓",
0xe9d3 : "鰌",
0xe9d4 : "鰆",
0xe9d5 : "鰈",
0xe9d6 : "鰒",
0xe9d7 : "鰊",
0xe9d8 : "鰄",
0xe9d9 : "鰮",
0xe9da : "鰛",
0xe9db : "鰥",
0xe9dc : "鰤",
0xe9dd : "鰡",
0xe9de : "鰰",
0xe9df : "鱇",
0xe9e0 : "鰲",
0xe9e1 : "鱆",
0xe9e2 : "鰾",
0xe9e3 : "鱚",
0xe9e4 : "鱠",
0xe9e5 : "鱧",
0xe9e6 : "鱶",
0xe9e7 : "鱸",
0xe9e8 : "鳧",
0xe9e9 : "鳬",
0xe9ea : "鳰",
0xe9eb : "鴉",
0xe9ec : "鴈",
0xe9ed : "鳫",
0xe9ee : "鴃",
0xe9ef : "鴆",
0xe9f0 : "鴪",
0xe9f1 : "鴦",
0xe9f2 : "鶯",
0xe9f3 : "鴣",
0xe9f4 : "鴟",
0xe9f5 : "鵄",
0xe9f6 : "鴕",
0xe9f7 : "鴒",
0xe9f8 : "鵁",
0xe9f9 : "鴿",
0xe9fa : "鴾",
0xe9fb : "鵆",
0xe9fc : "鵈",
0xea40 : "鵝",
0xea41 : "鵞",
0xea42 : "鵤",
0xea43 : "鵑",
0xea44 : "鵐",
0xea45 : "鵙",
0xea46 : "鵲",
0xea47 : "鶉",
0xea48 : "鶇",
0xea49 : "鶫",
0xea4a : "鵯",
0xea4b : "鵺",
0xea4c : "鶚",
0xea4d : "鶤",
0xea4e : "鶩",
0xea4f : "鶲",
0xea50 : "鷄",
0xea51 : "鷁",
0xea52 : "鶻",
0xea53 : "鶸",
0xea54 : "鶺",
0xea55 : "鷆",
0xea56 : "鷏",
0xea57 : "鷂",
0xea58 : "鷙",
0xea59 : "鷓",
0xea5a : "鷸",
0xea5b : "鷦",
0xea5c : "鷭",
0xea5d : "鷯",
0xea5e : "鷽",
0xea5f : "鸚",
0xea60 : "鸛",
0xea61 : "鸞",
0xea62 : "鹵",
0xea63 : "鹹",
0xea64 : "鹽",
0xea65 : "麁",
0xea66 : "麈",
0xea67 : "麋",
0xea68 : "麌",
0xea69 : "麒",
0xea6a : "麕",
0xea6b : "麑",
0xea6c : "麝",
0xea6d : "麥",
0xea6e : "麩",
0xea6f : "麸",
0xea70 : "麪",
0xea71 : "麭",
0xea72 : "靡",
0xea73 : "黌",
0xea74 : "黎",
0xea75 : "黏",
0xea76 : "黐",
0xea77 : "黔",
0xea78 : "黜",
0xea79 : "點",
0xea7a : "黝",
0xea7b : "黠",
0xea7c : "黥",
0xea7d : "黨",
0xea7e : "黯",
0xea80 : "黴",
0xea81 : "黶",
0xea82 : "黷",
0xea83 : "黹",
0xea84 : "黻",
0xea85 : "黼",
0xea86 : "黽",
0xea87 : "鼇",
0xea88 : "鼈",
0xea89 : "皷",
0xea8a : "鼕",
0xea8b : "鼡",
0xea8c : "鼬",
0xea8d : "鼾",
0xea8e : "齊",
0xea8f : "齒",
0xea90 : "齔",
0xea91 : "齣",
0xea92 : "齟",
0xea93 : "齠",
0xea94 : "齡",
0xea95 : "齦",
0xea96 : "齧",
0xea97 : "齬",
0xea98 : "齪",
0xea99 : "齷",
0xea9a : "齲",
0xea9b : "齶",
0xea9c : "龕",
0xea9d : "龜",
0xea9e : "龠",
0xea9f : "堯",
0xeaa0 : "槇",
0xeaa1 : "遙",
0xeaa2 : "瑤",
0xeaa3 : "凜",
0xeaa4 : "熙",
}
########NEW FILE########
__FILENAME__ = tomoe
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (C) 2009 The Tegaki project contributors
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

# Contributors to this file:
# - Mathieu Blondel

from tegaki.character import Point, Stroke, Writing, Character, _XmlBase
from tegaki.charcol import CharacterCollection

class TomoeXmlDictionaryReader(_XmlBase):

    def __init__(self):
        self._charcol = CharacterCollection()

    def get_character_collection(self):
        return self._charcol

    def _start_element(self, name, attrs):
        self._tag = name

        if self._first_tag:
            self._first_tag = False
            if self._tag != "dictionary":
                raise ValueError, "The very first tag should be <dictionary>"

        if self._tag == "character":
            self._writing = Writing()

        if self._tag == "stroke":
            self._stroke = Stroke()
            
        elif self._tag == "point":
            point = Point()

            for key in ("x", "y", "pressure", "xtilt", "ytilt", "timestamp"):
                if attrs.has_key(key):
                    value = attrs[key].encode("UTF-8")
                    if key in ("pressure", "xtilt", "ytilt"):
                        value = float(value)
                    else:
                        value = int(float(value))
                else:
                    value = None

                setattr(point, key, value)

            self._stroke.append_point(point)

    def _end_element(self, name):
        if name == "character":
            char = Character()
            char.set_utf8(self._utf8)
            char.set_writing(self._writing)
            self._charcol.add_set(self._utf8)
            self._charcol.append_character(self._utf8, char)

            for s in ["_tag", "_stroke"]:
                if s in self.__dict__:
                    del self.__dict__[s]

        if name == "stroke":
            self._writing.append_stroke(self._stroke)
            self._stroke = None

        self._tag = None

    def _char_data(self, data):
        if self._tag == "utf8":
            self._utf8 = data.encode("UTF-8")
        elif self._tag == "width":
            self._writing.set_width(int(data))
        elif self._tag == "height":
            self._writing.set_height(int(data))

def tomoe_dict_to_character_collection(path):
    reader = TomoeXmlDictionaryReader()
    gzip = False; bz2 = False
    if path.endswith(".gz"): gzip = True
    if path.endswith(".bz2"): bz2 = True
    reader.read(path, gzip=gzip, bz2=bz2)
    return reader.get_character_collection()


########NEW FILE########
__FILENAME__ = unipen
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (C) 2009 The Tegaki project contributors
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

# Contributors to this file:
# - Mathieu Blondel

# Incomplete unipen format parser
# See http://hwr.nici.kun.nl/unipen/unipen.def for the format specification

import re
import os

from tegaki.character import Point, Stroke, Writing, Character
from tegaki.charcol import CharacterCollection

class UnipenEventParser(object):
    """SAX-like event-based parser"""

    KEYWORD_LINE_REGEXP = re.compile(r"^\.[A-Z]+")

    def __init__(self):
        self._parsed_file = None

    def parse_file(self, path):
        self._parsed_file = path
        f = open(path)

        keyword, args = None, None
        for line in f.readlines():
            if self._is_keyword_line(line):
                if keyword is not None and args is not None:
                    self.handle_keyword(keyword.strip(), args.strip())
                    keyword, args = None, None

                arr = line.split(" ", 1)

                keyword = arr[0][1:]
                if len(arr) == 1: 
                    args = ""
                else: 
                    args = arr[1]

            elif keyword is not None and args is not None:
                args += line

        if keyword is not None and args is not None:
            self.handle_keyword(keyword, args)

        f.close()

        self.handle_eof()

        self._parsed_file = None

    def handle_keyword(self, keyword, args):
        # default keyword handler
        print keyword, args

    def handle_eof(self):
        # default end-of-file handler
        print "end of file"

    def _is_keyword_line(self, line):
        return (self.KEYWORD_LINE_REGEXP.match(line) is not None)

class UnipenProxyParser(UnipenEventParser):
    
    def __init__(self, redirect):
        UnipenEventParser.__init__(self)
        self._redirect = redirect

    def handle_keyword(self, keyword, args):
        self._redirect(keyword, args)

    def handle_eof(self):
        pass

class UnipenParser(UnipenEventParser):

    def __init__(self):
        UnipenEventParser.__init__(self)
        self._labels = []
        self._characters = []
        self._char = None

    def _handle_SEGMENT(self, args):
        seg_type, delimit, quality, label = args.split(" ")
        if seg_type == "CHARACTER":
            label = label.strip()[1:-1]
            self._labels.append(label)

    def _handle_START_BOX(self, args):
        if self._char:
            self._characters.append(self._char)
        self._char = Character() 

    def _handle_PEN_DOWN(self, args):
        writing = self._char.get_writing()
        points = [[int(p_) for p_ in p.split(" ")] \
                    for p in args.strip().split("\n")]
        stroke = Stroke()
        for x, y in points:
            stroke.append_point(Point(x,y))
        writing.append_stroke(stroke)

    def _handle_INCLUDE(self, args):
        if not self._parsed_file: return

        include_filename = args.upper()
        currdir = os.path.dirname(os.path.abspath(self._parsed_file))

        # FIXME: don't hardcode include paths
        include1 = os.path.join(currdir, "INCLUDE")
        include2 = os.path.join(currdir, "..", "INCLUDE")

        for include in (include1, include2, currdir):   
            path = os.path.join(include, include_filename)
            if os.path.exists(path):
                parser = UnipenProxyParser(self.handle_keyword)
                parser.parse_file(path)
                break

    def handle_keyword(self, keyword, args):
        try:
            func = getattr(self, "_handle_" + keyword)
        except AttributeError:
            pass
        else:
            func(args)

    def get_character_collection(self):
        charcol = CharacterCollection()
        assert(len(self._labels) == len(self._characters))

        # group characters with the same label into sets
        sets = {}
        for i in range(len(self._characters)):
            utf8 = self._labels[i]
            self._characters[i].set_utf8(utf8)
            sets[utf8] = sets.get(utf8, []) + [self._characters[i]]

        charcol.add_sets(sets.keys())

        for set_name, characters in sets.items():
            charcol.append_characters(set_name, characters)

        return charcol

########NEW FILE########
