__FILENAME__ = settings
# Django settings for httpi project.
#dir_prefix = "/home/X09/prestotx/raspberry_pi/piface/django/"
dir_prefix = "/home/pi/piface/django/"

DEBUG = True

TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
    ('Thomas Preston', 'thomasmarkpreston@gmail.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': dir_prefix + 'projects/httpi/database.db', # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'Europe/London'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-gb'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = ''

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = dir_prefix + 'projects/httpi/static/'

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    dir_prefix + 'projects/httpi/httpi/static',
    dir_prefix + 'projects/httpi/httpiface/static',
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'dsl64*0nv^&amp;d_c&amp;uv#8#)yj-5kg5q=$%0^ar^(ip6tl7oh*vj8'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#    'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    # Uncomment the next line for simple clickjacking protection:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'httpi.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'httpi.wsgi.application'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    dir_prefix + "templates/"
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Uncomment the next line to enable the admin:
    # 'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
)

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url
from django.conf import settings

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    url(r'^$', 'httpi.views.index'),
    url(r'^piface/', include('httpiface.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # url(r'^admin/', include(admin.site.urls)),
)

########NEW FILE########
__FILENAME__ = views
from django.shortcuts import render_to_response
from django.http import HttpResponse, QueryDict
from django.template import RequestContext


def index(request):
    return render_to_response(
            "httpi/index.html",
            {'test' : 1},
            context_instance=RequestContext(request))

########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for httpi project.

This module contains the WSGI application used by Django's development server
and any production WSGI deployments. It should expose a module-level variable
named ``application``. Django's ``runserver`` and ``runfcgi`` commands discover
this application via the ``WSGI_APPLICATION`` setting.

Usually you will have the standard Django WSGI application here, but it also
might make sense to replace the whole Django WSGI application with a custom one
that later delegates to the Django one. For example, you could introduce WSGI
middleware here, or combine a Django application with an application of another
framework.

"""
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "httpi.settings")

# This application object is used by any WSGI server configured to use this
# file. This includes Django's development server, if the WSGI_APPLICATION
# setting points here.
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

# Apply WSGI middleware here.
# from helloworld.wsgi import HelloWorldApplication
# application = HelloWorldApplication(application)

########NEW FILE########
__FILENAME__ = models
from django.db import models

# Create your models here.

########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase


class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.assertEqual(1 + 1, 2)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    url(r'^$', 'httpiface.views.index'),
    url(r'^ajax', 'httpiface.views.ajax'),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # url(r'^admin/', include(admin.site.urls)),
)

########NEW FILE########
__FILENAME__ = views
from django.shortcuts import render_to_response
from django.http import HttpResponse, HttpResponseBadRequest
from django.template import RequestContext
import simplejson

import piface.pfio as pfio

"""
# fake pfio stuff for testing
outpins = 0
inpins = 0
def fakepfioinit():
    pass
def fakepfiowrite(something):
    global outpins
    outpins = something
def fakepfioreadin():
    return 0b10101010
def fakepfioreadout():
    global outpins
    return outpins
pfio.init = fakepfioinit
pfio.write_output = fakepfiowrite
pfio.read_input = fakepfioreadin
pfio.read_output = fakepfioreadout
"""


def index(request):
    piface_detected = True
    piface_error_msg = ""

    try:
        pfio.init()
    except pfio.InitError as error:
        piface_detected = False
        piface_error_msg = error

    return render_to_response("httpiface/index.html",
            {'button_range' : range(8),
                'led_range' : range(4),
                'piface_detected' : piface_detected,
                'piface_error_msg' : piface_error_msg},
            context_instance=RequestContext(request))

def ajax(request):
    data = request.GET.dict()
    return_values = dict()

    if 'init' in data:
        try:
            pfio.init()
        except pfio.InitError as error:
            return_values.update({'status' : 'init failed'})
            return_values.update({'error' : str(error)})
            return HttpResponseBadRequest(simplejson.dumps(return_values))

    if 'read_input' in data:
        try:
            input_bitp = pfio.read_input()
        except Exception as e:
            return_values.update({'status' : 'read_input failed'})
            return_values.update({'error' : str(e)})
            return HttpResponseBadRequest(simplejson.dumps(return_values))
        else:
            return_values.update({'input_bitp' : input_bitp})

    if 'read_output' in data:
        try:
            output_bitp = pfio.read_output()
        except Exception as e:
            return_values.update({'status' : 'read_output failed'})
            return_values.update({'error' : str(e)})
            return HttpResponseBadRequest(simplejson.dumps(return_values))
        else:
            return_values.update({'output_bitp' : output_bitp})

    if 'write_output' in data:
        try:
            output_bitp = int(data['write_output'])
        except ValueError:
            return_values.update({'status' : 'write_output failed'})
            return_values.update({'error' : "write_output needs an integer bit pattern."})
            return HttpResponseBadRequest(simplejson.dumps(return_values))

        try:
            pfio.write_output(output_bitp)
        except Exception as e:
            return_values.update({'status' : "write_output failed"})
            return_values.update({'error' : str(e)})
            return HttpResponseBadRequest(simplejson.dumps(return_values))

    return_values.update({'status' : 'success'})
    return HttpResponse(simplejson.dumps(return_values))

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "httpi.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = talker
"""
talker.py
A speech module for the Pi Face package. Provides a simple method of talking
with the Raspberry Pi.
Note: this modules doesn't actually require a Pi Face board

Essentially this is just a wrapper around espeak
"""
import subprocess


DEFAULT_PITCH = 50  # 0-99
DEFAULT_SPEED = 160 # words per min


class PiFaceTalkerError(Exception):
    pass


def say(words, pitch=None, speed=None):
    """Says words through the audio jack on the Raspberry Pi"""
    if not pitch:
        pitch = DEFAULT_PITCH

    if not speed:
        speed = DEFAULT_SPEED
 
    devnull = open("/dev/null", "w")
    try:
        subprocess.call([
            "espeak",
            "-v", "en-rp", # english received pronounciation
            "-p", str(pitch),
            "-s", str(speed),
            words],
            stderr=devnull)

    except OSError:
        raise PiFaceTalkerError(
                "There was an error running 'espeak'. Is it installed?")

########NEW FILE########
__FILENAME__ = emtest1
from time import sleep

import piface.emulator as pfio
#import piface.pfio as pfio


if __name__ == "__main__":
    pfio.init()
    while True:
        # turn each output off, one by one
        for i in range(1, 9):
            pfio.digital_write(i, 1)
            sleep(1)
            pfio.digital_write(i, 0)
            sleep(1)

########NEW FILE########
__FILENAME__ = emtest_all
from time import sleep

#import piface.emulator as pfio
import piface.pfio as pfio


if __name__ == "__main__":
    pfio.init()
    while True:
        pfio.write_output(0xff)
        sleep(1)
        pfio.write_output(0)
        sleep(1)

########NEW FILE########
__FILENAME__ = flash
#!/usr/bin/env python

import time
import piface.pfio

piface.pfio.init()

led1 = piface.pfio.LED(1)

while True:
  led1.turn_on()
  time.sleep(1)
  led1.turn_off()
  time.sleep(1)

# vim:ts=2:sw=2:sts=2:et:ft=python


########NEW FILE########
__FILENAME__ = game
"""
RacingPi Game
Contains the code for running the actual game
"""
import time
import threading
import random

import piface.pfio as pfio
#import piface.emulator as pfio


VERBOSE_MODE = True

DEFAULT_QUESTION_FILE = "racingpi/questions.txt"


class UnknownButtonError(Exception):
    pass


class RacingPiGame(threading.Thread):
    def __init__(self, gui, question_file_name=None):
        threading.Thread.__init__(self)
        self.gui = gui

        self.question_file_name = question_file_name
        # set up the hardware interface
        pfio.init()

        # set up the buttons
        self.buttons = list()
        self.buttons.append(Button(ButtonSwitch(1), ButtonLight(3)))
        self.buttons.append(Button(ButtonSwitch(2), ButtonLight(4)))
        self.buttons.append(Button(ButtonSwitch(3), ButtonLight(5)))
        self.buttons.append(Button(ButtonSwitch(4), ButtonLight(6)))
        self.buttons.append(Button(ButtonSwitch(5), ButtonLight(7)))

        # set up the players
        self.player1 = Player("Adam", RacingCar(1), (self.buttons[0], self.buttons[1]))
        self.player2 = Player("Eve", RacingCar(2), (self.buttons[2], self.buttons[3]))

        """
        Threading stopper idea from stack overflow
        http://stackoverflow.com/questions/323972/is-there-any-way-to-kill-a-thread-in-python
        """
        self._stop = threading.Event() # a stopper to know when to end the game

    def stop(self):
        self._stop.set()

    def stopped(self):
        return self._stop.isSet()


    def run(self):
        """The main game stuff goes here"""
        while True:
            # set up the questions
            if self.question_file_name:
                question_file = open(question_file_name, "r")
            else:
                question_file = open(DEFAULT_QUESTION_FILE, "r")

            self.questions = list()
            for line in question_file.readlines():
                q_parts = line.split(",") # this can be moved into db later...
                self.questions.append(Question(q_parts[0], q_parts[1], q_parts[2]))

            random.shuffle(self.questions)

            self.ask_questions()
            if self.stopped():
                break

        self.stop()
        pfio.deinit()
    
    def ask_questions(self):
        for question in self.questions:
            # ask a question
            correct_answer_index = int(2 * random.random())
            wrong_answer_index = correct_answer_index ^ 1
            answers = ["", ""]
            answers[correct_answer_index] = question.correct_answer
            answers[wrong_answer_index] = question.wrong_answer

            values = [question.text]
            values.extend(answers)
            self.gui.update_question("%s\nA: %s\nB: %s" % tuple(values))

            # wait for a button press
            pin_bit_pattern = pfio.read_input()
            while pin_bit_pattern == 0 and not self.stopped():
                pin_bit_pattern = pfio.read_input()

            # since we can't have multi-leveled break statements...
            if self.stopped():
                break

            # find out which button was pressed
            pin_number = pfio.get_pin_number(pin_bit_pattern)

            #print "pin number: %d" % pin_number
            #print self.player1.buttons[correct_answer_index].switch.pin_number

            if pin_number == self.player1.buttons[correct_answer_index].switch.pin_number:
                self.player1.buttons[correct_answer_index].light.turn_on()
                print "Player 1 got the correct answer!"
                #print "The answer was: {}".format(question.correct_answer)
                self.gui.update_question("%s\n\nThe correct answer was: %s\n\nPlayer 1 has 3 seconds to race!" % (question.text, question.correct_answer))
                self.player1.car.drive(3)
                self.player1.buttons[correct_answer_index].light.turn_off()

            elif pin_number == self.player1.buttons[wrong_answer_index].switch.pin_number:
                self.player1.buttons[wrong_answer_index].light.turn_on()
                print "Player 1 got the WRONG answer!"
                #print "The answer was: {}".format(question.correct_answer)
                self.gui.update_question("%s\n\nThe correct answer was: %s\n\nPlayer 2 has 3 seconds to race!" % (question.text, question.correct_answer))
                self.player2.car.drive(3)
                self.player1.buttons[wrong_answer_index].light.turn_off()

            elif pin_number == self.player2.buttons[correct_answer_index].switch.pin_number:
                self.player2.buttons[correct_answer_index].light.turn_on()
                print "Player 2 got the correct answer!"
                #print "The answer was: {}".format(question.correct_answer)
                self.gui.update_question("%s\n\nThe correct answer was: %s\n\nPlayer 2 has 3 seconds to race!" % (question.text, question.correct_answer))
                self.player2.car.drive(3)
                self.player2.buttons[correct_answer_index].light.turn_off()

            elif pin_number == self.player2.buttons[wrong_answer_index].switch.pin_number:
                self.player2.buttons[wrong_answer_index].light.turn_on()
                print "Player 2 got the WRONG answer!"
                #print "The answer was: {}".format(question.correct_answer)
                self.gui.update_question("%s\n\nThe correct answer was: %s\n\nPlayer 1 has 3 seconds to race!" % (question.text, question.correct_answer))
                self.player1.car.drive(3)
                self.player2.buttons[wrong_answer_index].light.turn_off()

            elif pin_number == self.buttons[4].switch.pin_number:
                self.buttons[4].light.turn_on()
                print "PASS"
                #print "The answer was: {}".format(question.correct_answer)
                time.sleep(1)
                self.buttons[4].light.turn_off()

            else:
                raise UnknownButtonError("detected change on pin: %d" % pin_number)

            # wait until nothing is pressed
            pin_bit_pattern = pfio.read_input()
            while pin_bit_pattern != 0:
                pin_bit_pattern = pfio.read_input()

            # should we keep playing?
            if self.stopped():
                break

class RacingCar(pfio.Relay):
    def __init__(self, racing_car_number):
        # racing car number directly translates to the relay number
        pfio.Relay.__init__(self, racing_car_number)
    
    def drive(self, drive_period):
        """Move the car for the specified amount of seconds"""
        self.turn_on()
        time.sleep(drive_period)
        self.turn_off()

class ButtonLight(pfio.OutputItem):
    def __init__(self, button_number):
        # button lights are connected directly to pins
        pfio.OutputItem.__init__(self, button_number)

class ButtonSwitch(pfio.InputItem):
    def __init__(self, button_number):
        # button switches are connected directly to pins
        pfio.InputItem.__init__(self, button_number, True) # input

class Button(object):
    def __init__(self, button_switch, button_light):
        self.switch = button_switch
        self.light = button_light

class Player(object):
    def __init__(self, name, car, buttons):
        self.name = name
        self.car = car
        self.buttons = buttons
        self.points = 0

class Question(object):
    def __init__(self, question_text, correct_answer, wrong_answer):
        self.text = question_text
        self.correct_answer = correct_answer
        self.wrong_answer = wrong_answer

########NEW FILE########
__FILENAME__ = gui
#!/usr/bin/env python
"""
RacingPi gui initialisation
"""
import pygtk
pygtk.require("2.0")
import gtk

import game
import sys


VERBOSE_MODE = True

TITLE = "RacingPi"
TITLE_SIZE = 40000
DEFAULT_QUESTION = "What... is the air-speed velocity of an unladen swallow?"
QUESTION_SIZE = 12000
DEFAULT_SPACING = 10

RACING_PI_IMAGE = "racingpi/racingPi.png"


class RacingPiGUI(object):
	def __init__(self):
		self.the_game = None

		self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
		self.window.connect("delete_event", self.delete_event)
		self.window.connect("destroy", self.destroy)
		self.window.set_border_width(10)
		self.window.set_title(TITLE)
		self.window.set_icon_from_file(RACING_PI_IMAGE)
		self.generate_contents()
		self.window.show()

	def delete_event(self, widget, data=None):
		return False # call the destroy event after this

	def destroy(self, widget, data=None):
		if self.the_game:
			self.the_game.stop()
		gtk.main_quit()

	def main(self):
		gtk.main()


	def generate_contents(self):
		"""Generates the contents of the window"""
		# label
		main_title = gtk.Label()
		main_title.set_use_markup(True)
		main_title.set_markup("<span size='%d'>%s</span>"%(TITLE_SIZE, TITLE))
		main_title.show()
		
		image = gtk.Image()
		image.set_from_file(RACING_PI_IMAGE)
		image.show()

		
		# question space
		self.question_label = gtk.Label()
		self.question_label.set_use_markup(True)
		self.update_question(DEFAULT_QUESTION)
		self.question_label.show()

		main_box = make_vbox(elements=[main_title, self.question_label])
		main_box.add(image)
		self.window.add(main_box)
		"""
		try:
			self.set_icon_from_file("racingPi.png")
		except Exception, e:
			print e.message
			sys.exit(1)	
		"""
	
	
	def update_question(self, new_question):
		# clean up question
		new_question = new_question.replace("<", "\<").replace(">", "/>")
		gtk.gdk.threads_enter()
		self.question_label.set_markup("<span size='%d'>%s</span>"%(QUESTION_SIZE, new_question))
		gtk.gdk.threads_leave()


def make_vbox(homogeneous=False, spacing=DEFAULT_SPACING, elements=(), expand=False):
	return make_box(gtk.VBox, homogeneous, spacing, elements, expand)

def make_hbox(homogeneous=False, spacing=DEFAULT_SPACING, elements=(), expand=False):
	return make_box(gtk.HBox, homogeneous, spacing, elements, expand)

def make_box(box_type, homogeneous, spacing, elements, expand):
	box = box_type(False, spacing)

	for element in elements:
		box.pack_start(element, expand)
		element.show()

	box.show()
	return box

########NEW FILE########
__FILENAME__ = racingpi_db_helper
#!/usr/bin/env python
"""
racingpi_db_helper.py
A database wrapper for the RacingPi question database

TODO
Make it so that connections can be passed in for quicker database access
"""
import sqlite3


VERBOSE_MODE = True
DATABASE_NAME = "racingpi_db"


class Question(object):
	def __init__(self, question_text, correct_answer, incorrect_answer,
			difficulty, category):
		self.text = question_text
		self.correct_answer = correct_answer
		self.incorrect_answer = incorrect_answer
		self.difficulty = difficulty
		self.category = category

	def write_to_db(self):
		"""Writes the question to the database"""
		connection = get_connection()
		cursor = connection.cursor()
		self.category.write_to_db()
		sql = """
			INSERT INTO question
				(question_text, correct_answer, incorrect_answer, difficulty,
				category_id)
			VALUES (?,?,?,?,?)
		"""

		cursor.execute(sql, (
			self.text,
			self.correct_answer,
			self.incorrect_answer,
			self.difficulty,
			self.category.category_id)
		)

		self.question_id = cursor.lastrowid

		commit_connection(connection)

class Category(object):
	def __init__(self, name):
		self.cetegory_id = None
		self.name = name

	def write_to_db(self):
		"""Writes the category to the database"""
		connection = get_connection()
		cursor = connection.cursor()

		# check the category doesn't already exist
		sql = "SELECT id FROM category WHERE name=? LIMIT 1"
		cursor.execute(sql, (self.name,))
		print cursor.fetchone()[0]

		# if it doesnt then insert the category
		if count < 1:
			sql = "INSERT INTO category (name) VALUES (?)"
			cursor.execute(sql, (self.name,))
			self.category_id = cursor.lastrowid
			commit_connection(connection)


def get_connection():
	"""Returns a databse connection"""
	return sqlite3.connect(DATABASE_NAME)

def commit_connection(connection):
	"""Saves all changes to the database"""
	connection.commit()

def init_db():
	"""Initialises the RacingPi database"""
	connection = get_connection()
	cursor = connection.cursor()

	sql = """CREATE TABLE IF NOT EXISTS category (
		id integer,
		name text,
		PRIMARY KEY (id)
	)"""
	cursor.execute(sql)

	sql = """CREATE TABLE IF NOT EXISTS question (
		id integer,
		question_text text,
		correct_answer text,
		incorrect_answer text,
		difficulty integer,
		category_id integer,
		deleted integer DEFAULT 0,
		PRIMARY KEY (id)
		FOREIGN KEY (category_id) REFERENCES category(id)
	)"""
	cursor.execute(sql)

	commit_connection(connection)

def add_question(question=None):
	"""Adds a question to the database"""
	if question:
		question.write_to_db()
	else:
		question_text = raw_input("Question: ")
		correct_answer = raw_input("Correct answer: ")
		incorrect_answer = raw_input("Incorrect answer: ")
		difficulty = raw_input("Difficulty (number): ")
		category_name = raw_input("Category: ")

		question = Question(
				question_text,
				correct_answer,
				incorrect_answer,
				difficulty,
				Category(category_name))
		question.write_to_db()

def delete_question(question_id):
	"""Sets the delete flag high on a question"""
	connection = get_connection()
	cursor = connection.cursor()
	sql = """
		UPDATE question
		   SET deleted = 1
		 WHERE id = ?
	"""
	cursor.execute(sql, (question_id,))
	commit_connection(connection)

def get_question(question_id):
	"""Return a single question"""
	connection = get_connection()
	cursor = connection.cursor()
	sql = """
		SELECT question_text, correct_answer, incorrect_answer,
			   difficulty, category_id
		  FROM question
		 WHERE id = ?
		   AND deleted = 0
		 LIMIT 1
	"""
	cursor.execute(sql, (question_id,))
	row = cursor.fetchone()
	print row

def get_all_questions(category=None):
	pass

def get_all_categories():
	pass

########NEW FILE########
__FILENAME__ = simon
#!/usr/bin/env python
"""
simon.py
Simple simon game for use with pfio and the RaspberryPi interface (piface)

Objective of the game: You must remember an ever increasing sequence of flashes and input them correctly*

"""

from time import sleep 		# for delays
import random			# for random sequence generation
import piface.pfio as pfio			# piface library




pfio.init()			# initialise pfio (sets up the spi transfers)

colours = ["Red","Green","Blue","Yellow","White"]		# colour names for printing to screen



def next_colour():
	""" choses a random number between 1 and 5 to represent the coloured leds and their corresponding buttons"""
	return random.randint(1,5) 



first_in_sequence = next_colour()	# create the first colour in the sequence

array = [first_in_sequence]		# add the first colour to the array

game = 1				# keep track of game active (1 for active, 0 for game over)
score = 0				# keep track of player's score
screen_output = False			# choice to write colours and cues to the screen


sleep(1) # let them get their bearings

while game:						# while game in play
	
	game_round = score+1				
	
	if screen_output:				# print the round number
		print "\nRound %s!" %game_round
		
	for i in array:					# for each colour in current sequence (flash the sequence)

		pfio.digital_write(i+2,1)		# turn the colour on

		
		if screen_output:			# print the colour to the screen
			print colours[i-1]
			
		sleep(0.5)				# wait to keep the colour showing 
		pfio.digital_write(i+2,0)		# turn the colour off
		sleep(0.2)				# small break between colours
		

	sleep(0.4)
	pfio.write_output(0xFF)				# signify it is their turn by turning all the LEDs on then off
	sleep(0.3)
	pfio.write_output(0x0)
	
	if screen_output:	
		print "\nYour turn!"


	for i in array:						# for each colour in current sequence (check against inputted sequence)
		event = pfio.read_input()		# read the button port state
		
		while event != 0:					# wait till no buttons pressed
			event = pfio.read_input()	# so a single button press is not read as 2
			sleep(0.001)					# delay
				
		while event == 0:					# wait for any input 
			event = pfio.read_input()
		
		sleep(0.001)						# delay
		pin_number = pfio.get_pin_number(event)			# calculate the input pin
		
		if screen_output:
			print colours[pin_number -1]			# print the colour in sequence to the screen
		
		pfio.digital_write(pin_number+2,1)			# light up the buttons pressed
		
		if event != pfio.get_pin_bit_mask(i):	
			game = 0					# if any wrong buttons were pressed end the game
			break

		else:							# otherwise the correct button was pressed
			previous = event
			event = pfio.read_input()
			
			while previous == event:				# while the button is held down, wait
				previous = event
				event = pfio.read_input()
				
			pfio.digital_write(i+2,0)				# turn the button's LED off
			
			
	sleep(0.4)
	pfio.write_output(0xFF)		# signify their turn is over
	sleep(0.3)
	pfio.write_output(0x0)	

	if game:
		next = next_colour()		# set next colour
		while next == array[-1]:	# ensure the same colour isn't chosen twice in a row
			next = next_colour()
		
		array.append(next)		# add another colour to the sequence
		score +=1			# increment the score counter
		sleep(0.4)			# small break before flashing the new extended sequence



pfio.write_output(0x00)			# if the game has been lost, set all the button leds off

print "Your score was %s" %score 	# print the players score

"""
f = open('high_scores.txt','r+')

high_scores = f.readlines()


high_score = 0
index = 0

for indx, line in enumerate(high_scores):
	if "simon" in line:
		line = line.split(",")
		high_score = int(line[1])
		index = indx
		break 
		
f.close()

print "The high score was %d" %high_score


if score > high_score:
	print "Congratulations! You have the new high score"
	f = open('high_scores.txt','r+')
	f.write(replace(str(high_score),str(score)))
	f.close()
else:
	print "You haven't beaten the high score, keep trying!"

"""
pfio.deinit()				# close the pfio

########NEW FILE########
__FILENAME__ = sweep
#!/usr/bin/env python

import time
import piface.pfio
import piface.emulator

# Set thing to 
#   piface.emulator    to run with emulator
#   piface.pfio        to run without emulator

#thing = piface.emulator
thing = piface.pfio

thing.init()

led1 = thing.LED(1)

while True:
  for i in range(1, 5):
    led = thing.LED(i)
    led.turn_on()
    time.sleep(0.5)
    led.turn_off()

# vim:ts=2:sw=2:sts=2:et:ft=python


########NEW FILE########
__FILENAME__ = toggle
#!/usr/bin/env python

from time import sleep
import piface.pfio

piface.pfio.init()

# Make arrays of LEDs...
led    = [ piface.pfio.LED(i)    for i in range(1, 5) ]
# ...Switches...
switch = [ piface.pfio.Switch(i) for i in range(1, 5) ]
# ...and an array to store the switch states
down   = [ False for i in range(1, 5) ]

while True:
  for i in range(0, 4):
    if switch[i].value:
      if not down[i]:
        down[i] = True
        led[i].toggle()
    else:
      down[i] = False
  sleep(0.1)

# vim:ts=2:sw=2:sts=2:et:ft=python


########NEW FILE########
__FILENAME__ = twitterMoodCube
#!/usr/bin/env python
"""
twitterMoodCube.py

Simple moode cube that reflects the mood of the world and allows you to send your mood via a status post
author: Thomas Macpherson-Pope
date  : 20/06/2012
"""

from time import sleep
import twitter
import piface.pfio as pfio


pfio.init()

twitter = twitter.Api()

terms = ["#happy","#sad","#angry","#jelous","#guilty"]

search_term = terms[0]

twitter.GetSearch(term=search_term)

########NEW FILE########
__FILENAME__ = raspberry_pi_farm
#!/usr/bin/env python
"""
raspberry_pi_farm.py
contains a some singing/dancing animals on the Raspberry Pi!

author: Thomas Preston
date  : 18/06/2012
"""

import subprocess
import piface.pfio as pfio
#import piface.emulator as pfio
import easyteach.talker as talker


VERBOSE_MODE = True


class Chicken(pfio.Relay):
    """The wobbling/talking chicken"""
    def __init__(self):
        pfio.Relay.__init__(self, 1) # chicken is on pin 
        self.relay_pin = 1
        self.voice_pitch = 50 # 0-99
        self.voice_speed = 160 # words per min

    def start_wobble(self):
        """Starts wobbling the chicken"""
        self.turn_on()
        if VERBOSE_MODE:
            print "Chicken has started wobbling."

    def stop_wobble(self):
        """Stops wobbling the chicken"""
        self.turn_off()
        if VERBOSE_MODE:
            print "Chicken has stopped wobbling."

    def say(self, text_to_say):
        """Makes the chicken say something"""
        if VERBOSE_MODE:
            print "Chicken says: %s" % text_to_say

        talker.say(text_to_say, self.voice_pitch, self.voice_speed)


def init():
    """Initialises the raspberry pi farm"""
    pfio.init()

########NEW FILE########
__FILENAME__ = twitter_listen
#!/usr/bin/env python
"""
twitter_listen.py
listens for new tweets containing a search term and then wobbles a chicken

author: Thomas Preston
date  : 18/06/2012
"""

import time
import sys
import twitter

import raspberry_pi_farm


DEFAULT_SEARCH_TERM = "chicken"
TIME_DELAY = 2 # seconds between each status check

def main():
	api = twitter.Api()
	previous_status = twitter.Status()
	raspberry_pi_farm.init()
	chicken = raspberry_pi_farm.Chicken()

	# what are we searching for?
	if len(sys.argv) > 1:
		search_term = sys.argv[1]
	else:
		search_term = DEFAULT_SEARCH_TERM

	print "Listening to tweets containing the word '%s'." % search_term

	while True:
		# grab the first tweet containing the search_term
		current_status = api.GetSearch(term=search_term, per_page=1)[0]

		# if the status is different then give it to the chicken
		if current_status.id != previous_status.id:
			chicken.start_wobble()
			chicken.say(current_status.text)
			chicken.stop_wobble()

			previous_status = current_status

		# wait for a short while before checking again
		time.sleep(TIME_DELAY)
	
if __name__ == "__main__":
	main()

########NEW FILE########
__FILENAME__ = twitter_listen_user
#!/usr/bin/env python
"""
twitter_listen_user.py
listens for new tweets and then wobbles a chicken

author: Thomas Preston
date  : 18/06/2012
"""

import time
import sys
import twitter

import raspberry_pi_farm


DEFAULT_USER = "tommarkpreston" # the default user we should follow
TIME_DELAY = 2 # seconds between each status check

def main():
	api = twitter.Api()
	previous_status = twitter.Status()
	raspberry_pi_farm.init()
	chicken = raspberry_pi_farm.Chicken()

	# who are we listening to?
	if len(sys.argv) > 1:
		user = sys.argv[1]
	else:
		user = DEFAULT_USER

	print "Listening to tweets from '%s'." % user

	while True:
		# grab the users current status
		current_status = api.GetUser(user).status

		# if the status is different then give it to the chicken
		if current_status.id != previous_status.id:
			chicken.start_wobble()
			chicken.say(current_status.text)
			chicken.stop_wobble()

			previous_status = current_status

		# wait for a short while before checking again
		time.sleep(TIME_DELAY)
	
if __name__ == "__main__":
	main()

########NEW FILE########
__FILENAME__ = whackAMole
#!/usr/bin/env python
"""
whackAMole.py
Simple whack a mole game for use with pfio and the RaspberryPi interface (piface)

Objective of game: A random LED will light up and you must hit the corresponding button as quickly as possible.
The amount of time you have to hit the button will get shorter as the game progresses.
"""

from time import sleep		# for delays
import random			# for generating the next random button flash

import piface.pfio as pfio			# piface library		


pfio.init()			# initialise pfio (sets up the spi transfers)


def next_colour():
	""" choses a random number between 1 and 5 to represent the coloured leds and their corresponding buttons"""
	return random.randint(1,5)



current = next_colour() 			# create first random colour to be lit
pfio.digital_write(current+2,1)			# turn colour on
set_time = 2000					# time allowed to hit each light (starts off large and reduced after each hit)
time_left = set_time				# countdown timer for hitting the light
hit = 0						# the input value
score = 0					# keep track of the player's score
misses = 0					# keep track of how many the player misses

colours = ["Red","Green","Blue","Yellow","White"]	# colour list for printing to screen
previous_pressed = 255


print "Time left is: %s" %time_left		# notify the player how long they have to hit each flash


while True:

	in_bit_pattern = pfio.read_input() # see if any buttons have been hit
	
	if in_bit_pattern != previous_pressed:		# check this is a new button press
		previous_pressed = in_bit_pattern	# record button press for next time's check

		if in_bit_pattern > 0:

			if in_bit_pattern == pfio.get_pin_bit_mask(current):	# check that only the correct button was hit
			
				pfio.digital_write(current+2, 0)		# turn off hit light
				previous = current
				current = next_colour()				# get next colour
			
				while current == previous:			# ensure differnt colour each time
					current = next_colour()			# get next colour
				
				if ((score + misses) %30) ==29:
					if set_time > 125:
						set_time /= 2			# reduce the time allowed to hit the light
						print "Time left is: %s" %set_time
			
				time_left = set_time				# set the countdown time
			
				score += 1
				print "Your score %d" %score
				pfio.digital_write(current+2,1)			# turn the new light on
			

			else:							# wrong button pressed
				print "Wrong one!"
				print "Your score %d" %score
				score -= 1
			
			
	elif time_left==0:
		pfio.digital_write(current+2, 0)			# turn off hit light
		misses +=1						# increment misses
		print "Missed one!"
		
		if misses == 10:					# too many misses = Game Over!
			break
			
		previous = current					#
		current = next_colour()					# get next colour
		
		while current == previous:				# ensure differnt colour each time
			current = next_colour()				# get next colour
				
		if ((score + misses) %30)==29:
			if set_time > 125:
				set_time /= 2				# reduce the allowed time
				print "Time left is: %s" %set_time
				
		time_left = set_time					# set the countdown time
			
		pfio.digital_write(current+2,1)				# turn the new light on		
	
	time_left -=1							# decrement the time left to hit the current light

	

pfio.write_output(0)				# turn all lights off	
print "\nGame over!\n"
print "Your score was: %s" %score		# print the player's final score
#pfio.deinit()					# close the pfio
	


########NEW FILE########
__FILENAME__ = emulator
import pygtk
import gtk, gobject, cairo
import threading
from gtk import gdk
from math import pi
from time import sleep
import warnings

import emulator_parts

import pfio
import sys

VERBOSE_MODE = False
DEFAULT_SPACING = 10

EMU_WIDTH  = 302
EMU_HEIGHT = 201

#EMU_WIDTH  = 292
#EMU_HEIGHT = 193

EMU_SPEED  = 20
WINDOW_TITLE = "PiFace Emulator"

# global variables are bad, AND YOU SHOULD FEEL BAD!
rpi_emulator = None
pfio_connect = False

class EmulatorItem:
    def _get_handler(self):
        return sys.modules[__name__]

    handler = property(_get_handler, None)

class LED(EmulatorItem, pfio.LED):
    pass

class Relay(EmulatorItem, pfio.Relay):
    pass

class Switch(EmulatorItem, pfio.Switch):
    pass

class Emulator(threading.Thread):
    def __init__(self, spi_liststore_lock):
        gtk.gdk.threads_init() # init the gdk threads
        threading.Thread.__init__(self)

        self.spi_liststore_lock = spi_liststore_lock

        # a bit of spaghetti set up
        emulator_parts.pfio = pfio
        emulator_parts.rpi_emulator = self
        self.spi_visualiser_section = emulator_parts.SpiVisualiserFrame(self)
        global pfio_connect
        try:
            pfio.init()
            pfio_connect = True
        except pfio.InitError:
            print "Could not connect to the SPI module (check privileges). Starting emulator assuming that the PiFace is not connected."
            pfio_connect = False
            emulator_parts.pfio = None

        self.emu_window = gtk.Window()
        self.emu_window.connect("delete-event", gtk.main_quit)
        self.emu_window.set_title(WINDOW_TITLE)

        # emu screen
        self.emu_screen = emulator_parts.EmulatorScreen(EMU_WIDTH, EMU_HEIGHT, EMU_SPEED)
        self.emu_screen.show()

        # board connected msg
        if pfio_connect:
            msg = "Pi Face detected!"
        else:
            msg = "Pi Face not detected"
        self.board_con_msg = gtk.Label(msg)
        self.board_con_msg.show()

        if pfio_connect:
            # keep inputs updated
            self.update_input_check = gtk.CheckButton("Keep inputs updated")
            self.update_input_check.show()
            self.update_interval = gtk.Entry(5)
            self.update_interval.set_width_chars(5)
            self.update_interval.set_text("500")
            self.update_interval.show()
            update_interval_label = gtk.Label("ms interval")
            update_interval_label.show()

            self.update_input_check.connect("clicked", self.update_inputs)

            update_inputs_containter = gtk.HBox(False)
            update_inputs_containter.pack_start(self.update_input_check)
            update_inputs_containter.pack_start(self.update_interval, False, False)
            update_inputs_containter.pack_start(update_interval_label, False, False)
            update_inputs_containter.show()

            # spi visualiser checkbox
            self.spi_vis_check = gtk.CheckButton("SPI Visualiser")
            self.spi_vis_check.connect("clicked", self.toggle_spi_visualiser)
            self.spi_vis_check.show()

            # enable pullups checkbox
            self.en_pull_check = gtk.CheckButton("Enable pullups")
            self.en_pull_check.set_active(True)
            self.en_pull_check.connect("clicked", self.toggle_en_pullups)
            self.en_pull_check.show()

        # output override section
        self.output_override_section = \
                emulator_parts.OutputOverrideSection(self.emu_screen.output_pins)
        self.output_override_section.show()

        # spi visualiser
        if pfio_connect:
            #spi_visualiser_section = emulator_parts.SpiVisualiserFrame()
            self.spi_visualiser_section.set_size_request(50, 200)
            self.spi_visualiser_section.set_border_width(DEFAULT_SPACING)
            #self.spi_visualiser_section.show()
            self.spi_visualiser_section.hide()

        # vertically pack together the emu_screen and the board connected msg
        container0 = gtk.VBox(homogeneous=False, spacing=DEFAULT_SPACING)
        container0.pack_start(self.emu_screen)
        container0.pack_start(self.board_con_msg)

        if pfio_connect:
            container0.pack_start(update_inputs_containter)
            container0.pack_start(self.spi_vis_check)
            container0.pack_start(self.en_pull_check)

        container0.show()

        # horizontally pack together the emu screen+msg and the button overide
        container1 = gtk.HBox(homogeneous=True, spacing=DEFAULT_SPACING)
        container1.pack_start(container0)
        container1.pack_start(self.output_override_section)
        container1.set_border_width(DEFAULT_SPACING)
        container1.show()
        top_containter = container1

        if pfio_connect:
            # now, verticaly pack that container and the spi visualiser
            container2 = gtk.VBox(homogeneous=True, spacing=DEFAULT_SPACING)
            container2.pack_start(child=container1, expand=False, fill=False, padding=0)
            container2.pack_start(self.spi_visualiser_section)
            container2.show()
            top_containter = container2

        self.emu_window.add(top_containter)
        self.emu_window.present()

        self.input_updater = None

    def run(self):
        gtk.main()
    
    def update_inputs(self, widget, data=None):
        """
        If the checkbox has been pressed then schedule the virtual inputs
        to be updated, live
        """
        if widget.get_active():
            self.input_updater = InputUpdater(self.update_interval, self)
            self.input_updater.start()
        else:
            if self.input_updater:
                self.input_updater.stop()
                self.input_updater.join()

    def toggle_spi_visualiser(self, widget, data=None):
        if widget.get_active():
            self.spi_visualiser_section.show()
        else:
            self.spi_visualiser_section.hide()
            self.emu_window.resize(10, 10)

    def toggle_en_pullups(self, widget, data=None):
        if widget.get_active():
		pfio.write_pullups(0xff)
        else:
		pfio.write_pullups(0)

class InputUpdater(threading.Thread):
    def __init__(self, update_interval_entry, rpi_emulator):
        threading.Thread.__init__(self)
        self.update_interval_entry = update_interval_entry
        self.emu = rpi_emulator
        self._stop = threading.Event()

    def stop(self):
        self._stop.set()

    def stopped(self):
        return self._stop.isSet()

    def run(self):
        while not self.stopped():
            # get the input pin values
            input_pin_pattern = pfio.read_input()

            # set the virt input pin values
            for i in range(len(self.emu.emu_screen.input_pins)):
                if (input_pin_pattern >> i) & 1 == 1:
                    self.emu.emu_screen.input_pins[i].turn_on(True)
                else:
                    self.emu.emu_screen.input_pins[i].turn_off(True)


            self.emu.emu_screen.queue_draw()

            # sleep
            update_interval = int(self.update_interval_entry.get_text()) / 1000.0
            sleep(update_interval)


"""Input/Output functions mimicing the pfio module"""
def init():
    """Initialises the RaspberryPi emulator"""
    spi_liststore_lock = threading.Semaphore()

    global rpi_emulator
    rpi_emulator = Emulator(spi_liststore_lock)
    rpi_emulator.start()

def deinit():
    """Deinitialises the PiFace"""
    global rpi_emulator
    rpi_emulator.emu_window.destroy()

    gtk.main_quit()

    rpi_emulator.emu_screen = None

def get_pin_bit_mask(pin_number):
    """Translates a pin number to pin bit mask."""
    return pfio.get_pin_bit_mask(pin_number)

def get_pin_number(bit_pattern):
    """Returns the lowest pin number from a given bit pattern"""
    return pfio.get_pin_number(bit_pattern)

def hex_cat(items):
    return pfio.hex_cat(items)

def digital_write(pin_number, value):
    """Writes the value given to the pin specified"""
    if VERBOSE_MODE:
        emulator_parts.emu_print("digital write start")

    global rpi_emulator
    if value >= 1:
        rpi_emulator.emu_screen.output_pins[pin_number-1].turn_on()
    else:
        rpi_emulator.emu_screen.output_pins[pin_number-1].turn_off()

    rpi_emulator.emu_screen.queue_draw()

    if VERBOSE_MODE:
        emulator_parts.emu_print("digital write end")

def digital_read(pin_number):
    """Returns the value of the pin specified"""
    emulator_parts.request_digtial_read = True
    global rpi_emulator
    value = rpi_emulator.emu_screen.input_pins[pin_number-1].value
    emulator_parts.request_digtial_read = False

    rpi_emulator.emu_screen.queue_draw()
    return value

"""
Some wrapper functions so the user doesn't have to deal with
ugly port variables
"""
def read_output():
    """Returns the values of the output pins"""
    global rpi_emulator
    data = __read_pins(rpi_emulator.emu_screen.output_pins)

    global pfio_connect
    if pfio_connect:
        data |= pfio.read_output()

    return data

def read_input():
    """Returns the values of the input pins"""
    global rpi_emulator
    data = __read_pins(rpi_emulator.emu_screen.input_pins)

    global pfio_connect
    if pfio_connect:
        data |= pfio.read_input()
    print "data: %s" % data
    return data

def __read_pins(pins):
    vpin_values = [pin._value for pin in pins]
    data = 0
    for i in range(len(vpin_values)):
        data ^= (vpin_values[i] & 1) << i
    
    #global rpi_emulator
    #rpi_emulator.emu_screen.queue_draw()

    return data

def write_output(data):
    """Writes the values of the output pins"""
    global rpi_emulator
    for i in range(8):
        if ((data >> i) & 1) == 1:
            rpi_emulator.emu_screen.output_pins[i].turn_on()
        else:
            rpi_emulator.emu_screen.output_pins[i].turn_off()

    rpi_emulator.emu_screen.queue_draw()


if __name__ == "__main__":
    init()

########NEW FILE########
__FILENAME__ = emulator_parts
import pygtk
pygtk.require("2.0")
import gtk, gobject, cairo
from math import pi

import spivisualiser

TESTING = False

# relative directories
VIRT_PI_IMAGE = "images/pi.png"
VIRT_LED_ON_IMAGE = "images/smt_led_on.png"
if not TESTING:
    import os.path, sys
    package_dir = os.path.dirname(sys.modules["piface"].__file__)
    VIRT_PI_IMAGE = os.path.join(package_dir, VIRT_PI_IMAGE)
    VIRT_LED_ON_IMAGE = os.path.join(package_dir, VIRT_LED_ON_IMAGE)

EMU_PRINT_PREFIX = "EMU:"

PIN_COLOUR_RGB = (0, 1, 1)

DEFAULT_SPACING = 10

LED_Y_ROW = 33.0
INPUT_PIN_Y = 189.0

# pin circle locations
ledsX = [246.0, 234.0, 222.0, 210.0, 198.0, 186.0, 174.0, 162.0]
ledsY = [LED_Y_ROW, LED_Y_ROW, LED_Y_ROW, LED_Y_ROW, LED_Y_ROW, LED_Y_ROW, LED_Y_ROW, LED_Y_ROW]
switchesX = [19.0, 43.5, 68.0, 93.0]
switchesY = [159.0, 159.0, 159.0, 159.0]
relay1VirtPinsX = [291.0,291.0,291.0]
relay1VirtPinsY = [127.0,139.0,151.0]
relay2VirtPinsX = [291.0,291.0,291.0]
relay2VirtPinsY = [76.0,89.0,101.0]
boardInputVirtPinsX = [9.0,21.0,33.0,45.0,57.0,69.0,81.0,93.0,105]
boardInputVirtPinsY = [INPUT_PIN_Y,INPUT_PIN_Y,INPUT_PIN_Y,INPUT_PIN_Y,INPUT_PIN_Y,INPUT_PIN_Y,INPUT_PIN_Y,INPUT_PIN_Y]
# 8 <- 1
boardOutputVirtPinsX = [247.0, 235.0, 223.0, 211.0, 199.0, 187.0, 175.0, 163.0]
boardOutputVirtPinsY = [12.0, 12.0,12.0,12.0,12.0,12.0,12.0,12.0,12.0]

RELAY_PIN_PATTERN_ON  = (0, 1, 1)
RELAY_PIN_PATTERN_OFF = (1, 1, 0)

rpi_emulator = None
have_led_image = False

pfio = None # the pfio module that has been passed in

# don't update the input pins unless the user makes a digital read
# this is because an update is requested on every single mouse move
# which creates a TON of SPI traffic. Turn this to True if you want
# a full emulator mimic of the board (including inputs).
request_digtial_read = False


class VirtItem(object):
    """A virtual item connected to a pin on the RaspberryPi emulator"""
    def __init__(self, pin_number, is_input=False, is_relay_ext_pin=False):
        # an item defaults to an output device
        self.pin_number = pin_number
        self.is_input = is_input
        self.is_relay_ext_pin = is_relay_ext_pin

        self._value = 0 # hidden value for property stuff
        self._hold  = False # this value cannot be changed unless forced
        self._force = False # when true, held values can be changed

    def _get_value(self):
        # if the pfio is here then cross reference the virtual input
        # with the physical input
        global pfio
        global request_digtial_read
        if pfio and self.is_input and request_digtial_read:
            real_pin_value = pfio.digital_read(self.pin_number)
            print "readign"
            if real_pin_value == 1:
                return real_pin_value

        return self._value

    def _set_value(self, new_value):
        if not self._hold or (self._hold and self._force):
            self._value = new_value
            self._hold  = False
            self._force = False

            global pfio
            if pfio and not self.is_input and not self.is_relay_ext_pin:
                # update the state of the actual output devices
                pfio.digital_write(self.pin_number, new_value)
                #print "Setting pin %d to %d" % (self.pin_number, new_value
                
    value = property(_get_value, _set_value)

    def turn_on(self, hold=False):
        #print "turning on"
        self.value = 1;
        self._hold = hold

    def turn_off(self, force=False):
        #print "turning off..."
        self._force = force
        self.value = 0;
    
    def attach_pin(self, pin, pin_number=1, is_input=False):
        if pin:
            self.attached_pin = pin
        elif rpi_emulator.emu_screen:
            if is_input:
                self.attached_pin = rpi_emulator.emu_screen.input_pins[pin_number-1]
            else:
                self.attached_pin = rpi_emulator.emu_screen.output_pins[pin_number-1]
        else: # guess
            if is_input:
                self.attached_pin = VirtPin(pin_number)
            else:
                self.attached_pin = VirtPin(pin_number)

class VirtPin(VirtItem):
    def __init__(self, pin_number, is_input=False,
            is_relay1_pin=False, is_relay2_pin=False,
            is_relay_ext_pin=False):
        if is_relay1_pin:
            self.x = relay1VirtPinsX[pin_number]
            self.y = relay1VirtPinsY[pin_number]
        elif is_relay2_pin:
            self.x = relay2VirtPinsX[pin_number]
            self.y = relay2VirtPinsY[pin_number]
        elif is_input:
            self.x = boardInputVirtPinsX[pin_number-1]
            self.y = boardInputVirtPinsY[pin_number-1]
        else:
            self.x = boardOutputVirtPinsX[pin_number-1]
            self.y = boardOutputVirtPinsY[pin_number-1]

        VirtItem.__init__(self, pin_number, is_input, is_relay_ext_pin)

    def draw_hidden(self, cr):
        cr.arc(self.x, self.y, 5, 0, 2*pi)

    def draw(self, cr):
        if self.value == 1:
            #print "drawing pin at %d, %d" % (self.x, self.y)
            cr.save()
            pin_colour_r, pin_colour_g, pin_colour_b = PIN_COLOUR_RGB
            cr.set_source_rgb(pin_colour_r, pin_colour_g, pin_colour_b)
            cr.arc (self.x, self.y, 5, 0, 2*pi);
            cr.fill()
            cr.restore()

class VirtLED(VirtItem):
    """A virtual VirtLED on the RaspberryPi emulator"""
    def __init__(self, led_number, attached_pin=None):
        self.attach_pin(attached_pin, led_number)

        self.x = ledsX[led_number-1]
        self.y = ledsY[led_number-1]

        VirtItem.__init__(self, led_number)

    def _get_value(self):
        return self.attached_pin.value

    def _set_value(self, new_value):
        self.attached_pin.value = new_value
    
    value = property(_get_value, _set_value)

    def turn_on(self):
        #print "turning on VirtLED"
        self.value = 1;
    
    def turn_off(self):
        #print "turning off..."
        self.value = 0;

    def draw(self, cr):
        """
        Draw method requires cr drawing thingy (technical term)
        to be passed in
        """
        if self.value == 1:
            global have_led_image
            if have_led_image:
                # draw the illuminated VirtLED
                cr.save()
                led_surface = cairo.ImageSurface.create_from_png(VIRT_LED_ON_IMAGE)
                cr.set_source_surface(led_surface, self.x-6, self.y-8)
                cr.paint()
                cr.restore()
            else:
                # draw the yellow circle (r=8)
                cr.save()
                cr.set_source_rgb(1,1,0)
                cr.arc (self.x, self.y, 8, 0, 2*pi);
                cr.fill()
                cr.restore()

                # draw the red circle (r=6)
                cr.save()
                cr.set_source_rgb(1,0,0)
                cr.arc (self.x, self.y, 6, 0, 2*pi);
                cr.fill()
                cr.restore()

class VirtRelay(VirtItem):
    """A relay on the RaspberryPi"""
    def __init__(self, relay_number, attached_pin=None):
        self.attach_pin(attached_pin, relay_number)

        if relay_number == 1:
            self.pins = [VirtPin(i, False, True, False, True) for i in range(3)]
        else:
            self.pins = [VirtPin(i, False, False, True, True) for i in range(3)]

        VirtItem.__init__(self, relay_number)

        #self.value = self.attached_pin.value

    def _get_value(self):
        return self.attached_pin.value

    def _set_value(self, new_value):
        self.attached_pin.value = new_value
        self.set_pins()

    value = property(_get_value, _set_value)

    def set_pins(self):
        if self.value >= 1:
            self.pins[0].value, \
                self.pins[1].value, \
                self.pins[2].value = RELAY_PIN_PATTERN_ON
        else:
            self.pins[0].value, \
                self.pins[1].value, \
                self.pins[2].value = RELAY_PIN_PATTERN_OFF

    def turn_on(self):
        self.value = 1;
    
    def turn_off(self):
        self.value = 0;

    def draw(self, cr):
        self.set_pins()
        for pin in self.pins:
            #print "Drawing from relay %d" % self.pin_number
            pin.draw(cr)

class VirtSwitch(VirtItem):
    """A virtual switch on the RaspberryPi emulator"""
    def __init__(self, switch_number, attached_pin=None):
        self.attach_pin(attached_pin, switch_number, True)

        self.x = switchesX[switch_number-1]
        self.y = switchesY[switch_number-1]
        VirtItem.__init__(self, switch_number, True)

    def _get_value(self):
        return self.attached_pin.value

    def _set_value(self, new_value):
        self.attached_pin.value = new_value
    
    value = property(_get_value, _set_value)

    def turn_on(self):
        self.value = 1;
    
    def turn_off(self):
        self.value = 0;

    def draw_hidden(self, cr):
        cr.arc(self.x, self.y, 5, 0, 2*pi)

    def draw(self, cr):
        if self.value == 1:
            cr.save()
            cr.set_source_rgb(1,1,0)
            cr.arc (self.x, self.y, 4.5, 0, 2*pi);
            cr.fill()
            cr.restore()


class Screen(gtk.DrawingArea):
    """ This class is a Drawing Area"""
    def __init__(self, w, h, speed ):
        super(Screen, self).__init__()

        ## Old fashioned way to connect expose. I don't savvy the gobject stuff.
        self.connect("expose_event", self.do_expose_event)

        ## We want to know where the mouse is:
        self.connect("motion_notify_event", self._mouseMoved)
        self.connect("button_press_event", self._button_press)

        ## More GTK voodoo : unmask events
        self.add_events(gtk.gdk.BUTTON_PRESS_MASK | gtk.gdk.BUTTON_RELEASE_MASK | gtk.gdk.POINTER_MOTION_MASK)
        self.width, self.height = w, h
        self.set_size_request(w, h)
        self.x, self.y = 11110,11111110 # unlikely first coord to prevent false hits.

        self.button_pressed = False # check if it was a mouse move or button

    ## When expose event fires, this is run
    def do_expose_event(self, widget, event):
        self.cr = self.window.cairo_create( )
        ## Call our draw function to do stuff.
        self.draw()

    def _mouseMoved(self, widget, event):
        self.x = event.x
        self.y = event.y
        self.button_pressed = False
        self.queue_draw()

    def _button_press(self, widget, event):
        self.x = event.x
        self.y = event.y
        self.button_pressed = True
        self.queue_draw()

class EmulatorScreen(Screen):
    """This class is also a Drawing Area, coming from Screen."""
    def __init__ (self, w, h, speed):
        Screen.__init__(self, w, h, speed)

        global have_led_image
        try:
            f = open(VIRT_LED_ON_IMAGE)
            f.close()
            have_led_image = True
        except:
            emu_print("could not find the virtual led image: %s" % VIRT_LED_ON_IMAGE)
            have_led_image = False

        self.input_pins = [VirtPin(i, True) for i in range(1,9)]
        self.switches = [VirtSwitch(i+1, self.input_pins[i]) for i in range(4)]

        self.output_pins = [VirtPin(i) for i in range(1,9)]
        self.relays = [VirtRelay(i+1, self.output_pins[i]) for i in range(2)]
        self.leds = [VirtLED(i+1, self.output_pins[i]) for i in range(8)]

    def draw(self):
        cr = self.cr # Shabby shortcut.
        #---------TOP LEVEL - THE "PAGE"
        self.cr.identity_matrix  ( ) # VITAL LINE :: I'm not sure what it's doing.
        cr.save ( ) # Start a bubble

        # create the background surface
        self.surface = cairo.ImageSurface.create_from_png(VIRT_PI_IMAGE)
        cr.set_source_surface(self.surface, 0, 0)

        # blank everything
        cr.rectangle( 0, 0, 350, 250 )
        #cr.set_source_rgb( 1,0,0 )
        cr.set_source_surface(self.surface, 0, 0)
        cr.fill()
        cr.new_path() # stops the hit shape from being drawn
        cr.restore()

        if self.button_pressed:
            self.input_pin_detect(cr)
            self.button_pressed = False # stop registering the press
        else:
            self.switch_detect(cr)

        # draw all the switches
        for switch in self.switches:
            switch.draw(cr)

        # draw all the input_pins
        for pin in self.input_pins:
            pin.draw(cr)

        # draw all leds
        for led in self.leds:
            led.draw(cr)

        # draw all the relay pins
        for relay in self.relays:
            relay.draw(cr)

        # draw all output pins
        for pin in self.output_pins:
            pin.draw(cr)

    def switch_detect(self, cr):
        # detect rollover on the switches
        for switch in self.switches:
            switch.draw_hidden(cr) 
            if self.mouse_hit(cr):
                switch.turn_on()
            else:
                switch.turn_off()

    def input_pin_detect(self, cr):
        # detect clicks on the input input_pins
        for pin in self.input_pins:
            pin.draw_hidden(cr) # perhaps this is where the heavy traffic is
            if self.mouse_hit(cr):
                if pin.value == 1:
                    pin.turn_off(True) # force/hold
                else:
                    pin.turn_on(True) # force/hold

    def mouse_hit(self, cr):
        cr.save ( ) # Start a bubble
        cr.identity_matrix ( ) # Reset the matrix within it.
        hit = cr.in_fill ( self.x, self.y ) # Use Cairo's built-in hit tes
        cr.new_path ( ) # stops the hit shape from being drawn
        cr.restore ( ) # Close the bubble like this never happened.
        return hit

    def update_voutput_pins(self):
        """
        Updates the state of each virtual output pin to match
        that of the real pins
        """
        if not pfio:
            raise Exception(
                    "Looks like some sloppy programmer (probably Tom Preston...) " \
                    "is trying to update the virtual output pins when the PiFace " \
                    "isn't connected. Make sure you check for the pfio before calling " \
                    "the update_voutput_pins method. kthxbai.")

        output_bit_map = pfio.read_output()
        for i in range(len(self.output_pins)):
            # updating inner value so that we don't do more SPI reads
            self.output_pins[i]._value = (output_bit_map >> i) & 1 

        self.queue_draw()

class OutputOverrideSection(gtk.VBox):
    def __init__(self, output_pins):
        gtk.VBox.__init__(self)
        self.output_pins = output_pins
        self.number_of_override_buttons = 8
        widgets = list()

        # main override button
        self.main_override_btn = gtk.ToggleButton("Override Enable")
        self.main_override_btn.connect('clicked', self.main_override_clicked)
        self.main_override_btn.show()
        widgets.append(self.main_override_btn)

        # pin override buttons
        self.override_buttons = list()
        for i in range(self.number_of_override_buttons):
            new_button = gtk.ToggleButton("Output Pin %d" % (i))
            new_button.connect('clicked', self.output_override_clicked, i)
            new_button.show()
            new_button.set_sensitive(False)
            self.override_buttons.append(new_button)
            widgets.append(new_button)

        # all on/off, flip buttons
        self.all_on_btn = gtk.Button("All on")
        self.all_on_btn.connect('clicked', self.all_on_button_clicked)
        self.all_on_btn.set_sensitive(False)
        self.all_on_btn.show()

        self.all_off_btn = gtk.Button("All off")
        self.all_off_btn.connect('clicked', self.all_off_button_clicked)
        self.all_off_btn.set_sensitive(False)
        self.all_off_btn.show()

        self.flip_btn = gtk.Button("Flip")
        self.flip_btn.connect('clicked', self.flip_button_clicked)
        self.flip_btn.set_sensitive(False)
        self.flip_btn.show()

        bottom_button_containter = gtk.HBox()
        bottom_button_containter.pack_start(self.all_on_btn)
        bottom_button_containter.pack_start(self.all_off_btn)
        bottom_button_containter.pack_start(self.flip_btn)
        bottom_button_containter.show()
        widgets.append(bottom_button_containter)

        # pack 'em in
        for widget in widgets:
            self.pack_start(widget)

        self.batch_button = False
        self.reseting = False

    def reset_buttons(self):
        self.batch_button = True
        self.reseting = True
        for button in self.override_buttons:
            button.set_active(False)
        self.main_override_btn.set_active(False)

        self.batch_button = False
        self.reseting = False

    """Callbacks"""
    def main_override_clicked(self, main_override_btn, data=None):
        if main_override_btn.get_active():
            self.enable_override_buttons()
        else:
            self.disable_override_buttons()
            if not self.reseting:
                # turn off all the pins
                for pin in self.output_pins:
                    pin._value = 0
                global pfio
                if pfio:
                    pfio.write_output(0)


        global rpi_emulator
        rpi_emulator.emu_screen.queue_draw()

    def all_on_button_clicked(self, all_on_btn, data=None):
        self.batch_button = True
        for i in range(self.number_of_override_buttons):
            self.override_buttons[i].set_active(True)
            #self.output_pins[i]._value = 1

        self.set_pins()

        global rpi_emulator
        rpi_emulator.emu_screen.queue_draw()

        self.batch_button = False

    def all_off_button_clicked(self, all_on_btn, data=None):
        self.batch_button = True

        for i in range(self.number_of_override_buttons):
            self.override_buttons[i].set_active(False)
            #self.output_pins[i]._value = 0

        self.set_pins()

        global rpi_emulator
        rpi_emulator.emu_screen.queue_draw()

        self.batch_button = False

    def flip_button_clicked(self, flip_btn, data=None):
        self.batch_button = True
        for i in range(self.number_of_override_buttons):
            if self.override_buttons[i].get_active():
                self.override_buttons[i].set_active(False)
                #self.output_pins[i]._value = 0
            else:
                self.override_buttons[i].set_active(True)
                #self.output_pins[i]._value = 1

        self.set_pins()
        global rpi_emulator
        rpi_emulator.emu_screen.queue_draw()

        self.batch_button = False

    def output_override_clicked(self, toggle_button, data=None):
        if not self.batch_button:
            self.set_pins()

    def set_pins(self):
        global rpi_emulator
        pin_bit_mask = 0 # for the pfio
        for i in range(len(self.override_buttons)):
            if self.override_buttons[i].get_active():
                pin_bit_mask ^= 1 << i
                rpi_emulator.emu_screen.output_pins[i]._value = 1
            else:
                pin_bit_mask ^= 0 << i
                rpi_emulator.emu_screen.output_pins[i]._value = 0

        global pfio
        if pfio:
            pfio.write_output(pin_bit_mask)

        rpi_emulator.emu_screen.queue_draw()

    def enable_override_buttons(self):
        self.all_on_btn.set_sensitive(True)
        self.all_off_btn.set_sensitive(True)
        self.flip_btn.set_sensitive(True)
        for i in range(self.number_of_override_buttons):
            self.override_buttons[i].set_sensitive(True)

        self.set_pins()

        global rpi_emulator
        rpi_emulator.emu_screen.queue_draw()

    def disable_override_buttons(self):
        # disable all of the buttons
        self.all_on_btn.set_sensitive(False)
        self.all_off_btn.set_sensitive(False)
        self.flip_btn.set_sensitive(False)
        for button in self.override_buttons:
            button.set_sensitive(False)

        global rpi_emulator
        rpi_emulator.emu_screen.queue_draw()

class SpiVisualiserFrame(gtk.Frame):
    def __init__(self, rpi_emulator):
        gtk.Frame.__init__(self, "SPI Visualiser")
        container = gtk.VBox(False)

        spi_visualiser_section = spivisualiser.SpiVisualiserSection(rpi_emulator)
        spi_visualiser_section.show()
        container.pack_start(child=spi_visualiser_section, expand=True, fill=True)

        global pfio
        if pfio:
            pfio.spi_visualiser_section = spi_visualiser_section

        spi_sender_section = spivisualiser.SpiSenderSection(rpi_emulator)
        spi_sender_section.show()
        container.pack_end(child=spi_sender_section, expand=False)

        container.show()
        container.set_border_width(DEFAULT_SPACING)
        self.add(container)
        self.set_border_width(DEFAULT_SPACING)
        self.show()


def emu_print(text):
    """Prints a string with the pfio print prefix"""
    print "%s %s" % (EMU_PRINT_PREFIX, text)

########NEW FILE########
__FILENAME__ = pfio
#!/usr/bin/env python
"""
pfio.py
Provides I/O methods for interfacing with the RaspberryPi interface (piface)

piface has two ports (input/output) each with eight pins with several
peripherals connected for interacting with the raspberry pi
"""
from time import sleep
from datetime import datetime

import sys
import spi


VERBOSE_MODE = False # toggle verbosity
__pfio_print_PREFIX = "PFIO: " # prefix for pfio messages

# SPI operations
WRITE_CMD = 0x40
READ_CMD  = 0x41

# Port configuration
IODIRA = 0x00 # I/O direction A
IODIRB = 0x01 # I/O direction B
IOCON  = 0x0A # I/O config
GPIOA  = 0x12 # port A
GPIOB  = 0x13 # port B
GPPUA  = 0x0C # port A pullups
GPPUB  = 0x0D # port B pullups
OUTPUT_PORT = GPIOA
INPUT_PORT  = GPIOB
INPUT_PULLUP = GPPUB

spi_handler = None

spi_visualiser_section = None # for the emulator spi visualiser


# custom exceptions
class InitError(Exception):
    pass

class InputDeviceError(Exception):
    pass

class PinRangeError(Exception):
    pass

class LEDRangeError(Exception):
    pass

class RelayRangeError(Exception):
    pass

class SwitchRangeError(Exception):
    pass


# classes
class Item(object):
    """An item connected to a pin on the RaspberryPi"""
    def __init__(self, pin_number, handler=None):
        self.pin_number = pin_number
        if handler:
            self.handler = handler

    def _get_handler(self):
        return sys.modules[__name__]

    handler = property(_get_handler, None)

class InputItem(Item):
    """An input connected to a pin on the RaspberryPi"""
    def __init__(self, pin_number, handler=None):
        Item.__init__(self, pin_number, handler)

    def _get_value(self):
        return self.handler.digital_read(self.pin_number)

    def _set_value(self, data):
        raise InputDeviceError("You cannot set an input's values!")

    value = property(_get_value, _set_value)

class OutputItem(Item):
    """An output connected to a pin on the RaspberryPi"""
    def __init__(self, pin_number, handler=None):
        self.current = 0
        Item.__init__(self, pin_number, handler)

    def _get_value(self):
        return self.current

    def _set_value(self, data):
        self.current = data
        return self.handler.digital_write(self.pin_number, data)

    value = property(_get_value, _set_value)

    def turn_on(self):
        self.value = 1
    
    def turn_off(self):
        self.value = 0

    def toggle(self):
        self.value = not self.value

class LED(OutputItem):
    """An LED on the RaspberryPi"""
    def __init__(self, led_number, handler=None):
        if led_number < 0 or led_number > 7:
            raise LEDRangeError(
                    "Specified LED index (%d) out of range." % led_number)
        else:
            OutputItem.__init__(self, led_number, handler)

class Relay(OutputItem):
    """A relay on the RaspberryPi"""
    def __init__(self, relay_number, handler=None):
        if relay_number < 0 or relay_number > 1:
            raise RelayRangeError(
                    "Specified relay index (%d) out of range." % relay_number)
        else:
            OutputItem.__init__(self, relay_number, handler)

class Switch(InputItem):
    """A switch on the RaspberryPi"""
    def __init__(self, switch_number, handler=None):
        if switch_number < 0 or switch_number > 3:
            raise SwitchRangeError(
                  "Specified switch index (%d) out of range." % switch_number)
        else:
            InputItem.__init__(self, switch_number, handler)


# functions
def get_spi_handler():
    return spi.SPI(0,0) # spi.SPI(X,Y) is /dev/spidevX.Y

def init(init_ports=True):
    """Initialises the PiFace"""
    if VERBOSE_MODE:
         __pfio_print("initialising SPI")

    global spi_handler
    try:
        spi_handler = get_spi_handler()
    except spi.error as error:
        raise InitError(error)

    if init_ports:
        # set up the ports
        write(IOCON,  8)    # enable hardware addressing
        write(GPIOA,  0x00) # set port A on
        write(IODIRA, 0)    # set port A as outputs
        write(IODIRB, 0xFF) # set port B as inputs
        #write(GPIOA,  0xFF) # set port A on
        #write(GPIOB,  0xFF) # set port B on
        #write(GPPUA,  0xFF) # set port A pullups on
        write(GPPUB,  0xFF) # set port B pullups on

        # check the outputs are being set (primitive board detection)
        # AR removed this test as it lead to flashing of outputs which 
        # could surprise users!
        #test_value = 0b10101010
        #write_output(test_value)
        #if read_output() != test_value:
        #    spi_handler = None
        #    raise InitError("The PiFace board could not be detected")

        # initialise all outputs to 0
        write_output(0)

def deinit():
    """Deinitialises the PiFace"""
    global spi_handler
    if spi_handler:
        spi_handler.close()
        spi_handler = None

def __pfio_print(text):
    """Prints a string with the pfio print prefix"""
    print "%s %s" % (__pfio_print_PREFIX, text)

def get_pin_bit_mask(pin_number):
    """Translates a pin number to pin bit mask. First pin is pin0."""
    if pin_number > 7 or pin_number < 0:
        raise PinRangeError("Specified pin number (%d) out of range." % pin_number)
    else:
        return 1 << (pin_number)

def get_pin_number(bit_pattern):
    """Returns the lowest pin number from a given bit pattern"""
    pin_number = 0 # assume pin 0
    while (bit_pattern & 1) == 0:
        bit_pattern = bit_pattern >> 1
        pin_number += 1
        if pin_number > 7:
            pin_number = 0
            break
    
    return pin_number

def byte_cat(items):
    """
    Returns a value comprised of the concatenation of the given hex values
    Example: (0x41, 0x16, 0x01) -> 0x411601
    """
    items = list(items)
    items.reverse()
    cauldron = 0
    for i in range(len(items)):
        cauldron ^= items[i] << (i * 8)
    return cauldron

def digital_write(pin_number, value):
    """Writes the value given to the pin specified"""
    if VERBOSE_MODE:
        __pfio_print("digital write start")

    pin_bit_mask = get_pin_bit_mask(pin_number)

    if VERBOSE_MODE:
        __pfio_print("pin bit mask: %s" % bin(pin_bit_mask))

    old_pin_values = read_output()

    if VERBOSE_MODE:
        __pfio_print("old pin values: %s" % bin(old_pin_values))

    # generate the 
    if value:
        new_pin_values = old_pin_values | pin_bit_mask
    else:
        new_pin_values = old_pin_values & ~pin_bit_mask

    if VERBOSE_MODE:
        __pfio_print("new pin values: %s" % bin(new_pin_values))

    write_output(new_pin_values)

    if VERBOSE_MODE:
        __pfio_print("digital write end")

def digital_read(pin_number):
    """Returns the value of the pin specified"""
    current_pin_values = read_input()
    pin_bit_mask = get_pin_bit_mask(pin_number)

    result = current_pin_values & pin_bit_mask

    # is this correct? -thomas preston
    if result:
        return 1
    else:
        return 0

def digital_write_pullup(pin_number, value):
    """Writes the pullup value given to the pin specified"""
    if VERBOSE_MODE:
        __pfio_print("digital write pullup start")

    pin_bit_mask = get_pin_bit_mask(pin_number)

    if VERBOSE_MODE:
        __pfio_print("pin bit mask: %s" % bin(pin_bit_mask))

    old_pin_values = read_pullup()

    if VERBOSE_MODE:
        __pfio_print("old pin values: %s" % bin(old_pin_values))

    # generate the 
    if value:
        new_pin_values = old_pin_values | pin_bit_mask
    else:
        new_pin_values = old_pin_values & ~pin_bit_mask

    if VERBOSE_MODE:
        __pfio_print("new pin values: %s" % bin(new_pin_values))

    write_pullup(new_pin_values)

    if VERBOSE_MODE:
        __pfio_print("digital write end")

def digital_read_pullup(pin_number):
    """Returns the value of the pin specified"""
    current_pin_values = read_pullup()
    pin_bit_mask = get_pin_bit_mask(pin_number)

    result = current_pin_values & pin_bit_mask

    # works with true/false
    if result:
        return 1
    else:
        return 0
        
"""
Some wrapper functions so the user doesn't have to deal with
ugly port variables
"""
def read_output():
    """Returns the values of the output pins"""
    port, data = read(OUTPUT_PORT)
    return data

def read_input():
    """Returns the values of the input pins"""
    port, data = read(INPUT_PORT)
    # inputs are active low, but the user doesn't need to know this...
    return data ^ 0xff 

def read_pullup():
    """Reads value of pullup registers"""
    port, data = read(INPUT_PULLUP)
    return data

def write_pullup(data):
    port, data = write(INPUT_PULLUP, data)
    return data

def write_output(data):
    """Writed the values of the output pins"""
    port, data = write(OUTPUT_PORT, data)
    return data

"""
def write_input(data):
    " ""Writes the values of the input pins"" "
    port, data = write(INPUT_PORT, data)
    return data
"""

def read(port):
    """Reads from the port specified"""
    # data byte is padded with 1's since it isn't going to be used
    operation, port, data = send([(READ_CMD, port, 0xff)])[0] # send is expecting and returns a list
    return (port, data)

def write(port, data):
    """Writes data to the port specified"""
    #print "writing"
    operation, port, data = send([(WRITE_CMD, port, data)])[0] # send is expecting and returns a list
    return (port, data)


def send(spi_commands, custom_spi=False):
    """Sends a list of spi commands to the PiFace"""
    if spi_handler == None:
        raise InitError("The pfio module has not yet been initialised. Before send(), call init().")
    # a place to store the returned values for each transfer
    returned_values_list = list() 

    # datum is an array of three bytes
    for cmd, port, data in spi_commands:
        datum_tx = byte_cat((cmd, port, data))
        if VERBOSE_MODE:
            __pfio_print("transfering data: 0x%06x" % datum_tx)

        # transfer the data string
        returned_values = spi_handler.transfer("%06x" % datum_tx, 3)
        datum_rx = byte_cat(returned_values)

        returned_values_list.append(returned_values)

        if VERBOSE_MODE:
            __pfio_print("SPI module returned: 0x%06x" % datum_rx)

        # if we are visualising, add the data to the emulator visualiser
        global spi_visualiser_section
        if spi_visualiser_section:
            time = datetime.now()
            timestr = "%d:%d:%d.%d" % (time.hour, time.minute, time.second, time.microsecond)
            datum_tx = byte_cat((cmd, port, data)) # recalculate since the transfer changes it
            #print "writing to spi_liststore: %s" % str((timestr, hex(datum_tx), hex(datum_rx)))
            spi_visualiser_section.add_spi_log(timestr, datum_tx, datum_rx, custom_spi)

    return returned_values_list


def test_method():
    digital_write(1,1) # write pin 1 high
    sleep(2)
    digital_write(1,0) # write pin 1 low

if __name__ == "__main__":
    init()
    test_method()
    deinit()

########NEW FILE########
__FILENAME__ = pfion
"""
pfion.py
A network version of the pfio - can talk to Pi Face's over a network
"""
import socket
import threading
import struct
import pfio


DEFAULT_PORT = 15432
BUFFER_SIZE  = 100

UNKNOWN_CMD   = 0
WRITE_OUT_CMD = 1
WRITE_OUT_ACK = 2
READ_OUT_CMD  = 3
READ_OUT_ACK  = 4
READ_IN_CMD   = 5
READ_IN_ACK   = 6
DIGITAL_WRITE_CMD = 7
DIGITAL_WRITE_ACK = 8
DIGITAL_READ_CMD  = 9
DIGITAL_READ_ACK  = 10

STRUCT_UNIT_TYPE = "B"

"""
# testing without pfio
outpins = 0
inpins = 0
def fakepfioinit():
    pass
def fakepfiowrite(something):
    print "writing ", something
    global outpins
    outpins = something
def fakepfioreadin():
    print "read in"
    return 0b10101010
def fakepfioreadout():
    print "read out"
    global outpins
    return outpins
pfio.init = fakepfioinit
pfio.write_output = fakepfiowrite
pfio.read_input = fakepfioreadin
pfio.read_output = fakepfioreadout
"""


class UnknownPacketReceivedError(Exception):
    pass


class PfionPacket(object):
    """Models a Pfio network packet"""
    def __init__(self, command=UNKNOWN_CMD):
        self.command  = command
        self.cmd_data = 0  # 1 byte of data associated with the cmd
        self.data     = "" # extra data as a string

    def for_network(self):
        """Returns this pfion packet as a struct+data"""
        pcmddata = struct.pack(STRUCT_UNIT_TYPE*2, self.command, self.cmd_data)
        return  pcmddata + self.data

    def from_network(self, raw_struct):
        """Returns this pfion packet with new values interpereted from
        the struct+data given in"""
        self.command,  = struct.unpack(STRUCT_UNIT_TYPE, raw_struct[0])
        self.cmd_data, = struct.unpack(STRUCT_UNIT_TYPE, raw_struct[1])
        self.data = raw_struct[2:]
        return self

    """Pin number and pin value are stored in the upper and lower
    nibbles of the first data byte respectively. These are for digital
    read and digital write operations"""
    def _get_pin_number(self):
        return self.cmd_data >> 4

    def _set_pin_number(self, new_pin_number):
        self.cmd_data = (new_pin_number << 4) ^ (self.cmd_data & 0xf)

    pin_number = property(_get_pin_number, _set_pin_number)

    def _get_pin_value(self):
        return self.cmd_data & 0xf

    def _set_pin_value(self, new_pin_value):
        self.cmd_data = (new_pin_value & 0xf) ^ (self.cmd_data & 0xf0)

    pin_value = property(_get_pin_value, _set_pin_value)

    def _get_bit_pattern(self):
        return self.cmd_data

    def _set_bit_pattern(self, new_bit_pattern):
        self.cmd_data = new_bit_pattern & 0xff

    bit_pattern = property(_get_bit_pattern, _set_bit_pattern)


def start_pfio_server(callback=None, verbose=False, port=DEFAULT_PORT):
    """Starts listening for pfio packets over the network"""
    pfio.init()
    try:
        # this returns the loopback ip on the RPi :-(
        #hostname = socket.gethostname()

        ###################################################
        # this is pretty hacky, if anyone can find a better
        # solution, then please change this!
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80)) # try to connect to google's dns
        hostname = s.getsockname()[0] # get this device's hostname
        s.close()
        # blergh, nasty stuff
        ###################################################

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((hostname, port))

    except socket.error as e:
        print "There was an error setting up the server socket!"
        print e
        return

    else:
        if verbose:
            print "Listening at %s on port %d" % (hostname, port)

    while True:
        # get the packet
        packet, sender = sock.recvfrom(BUFFER_SIZE)
        if verbose:
            print "Recieved packet from", sender
        # make it something sensible
        packet = PfionPacket().from_network(packet)

        if packet.command == WRITE_OUT_CMD:
            pfio.write_output(packet.bit_pattern)
            p = PfionPacket(WRITE_OUT_ACK)
            sock.sendto(p.for_network(), sender)

        elif packet.command == READ_OUT_CMD:
            output_bitp = pfio.read_output()
            p = PfionPacket(READ_OUT_ACK)
            p.bit_pattern = output_bitp
            sock.sendto(p.for_network(), sender)

        elif packet.command == READ_IN_CMD:
            input_bitp = pfio.read_input()
            p = PfionPacket(READ_IN_ACK)
            p.bit_pattern = input_bitp
            sock.sendto(p.for_network(), sender)

        elif packet.command == DIGITAL_WRITE_CMD:
            pfio.digital_write(packet.pin_number, packet.pin_value)
            p = PfionPacket(DIGITAL_WRITE_ACK)
            sock.sendto(p.for_network(), sender)

        elif packet.command ==  DIGITAL_READ_CMD:
            pin_value = pfio.digital_read(packet.pin_number)
            p = PfionPacket(DIGITAL_READ_ACK)
            p.pin_number = packet.pin_number
            p.pin_value  = pin_value
            sock.sendto(p.for_network(), sender)

        elif callback != None:
            callback(packet, sender)

        elif verbose:
            print "Unkown packet command (%d). Ignoring." % packet.command

# sending functions
def send_packet(packet, hostname, port=DEFAULT_PORT):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(packet.for_network(), (hostname, port))
    return sock

def send_write_output(output_bitp, hostname, port=DEFAULT_PORT):
    packet = PfionPacket(WRITE_OUT_CMD)
    packet.bit_pattern = output_bitp
    sock = send_packet(packet, hostname)
    p, sender = sock.recvfrom(BUFFER_SIZE)
    packet = PfionPacket().from_network(p)
    if packet.command != WRITE_OUT_ACK:
        raise UnknownPacketReceivedError(
                "Received packet command (%d) was not WRITE_OUT_ACK" %
                packet.command)

def send_read_output(hostname, port=DEFAULT_PORT):
    packet = PfionPacket(READ_OUT_CMD)
    sock = send_packet(packet, hostname)
    p, sender = sock.recvfrom(BUFFER_SIZE)
    packet = PfionPacket().from_network(p)
    if packet.command == READ_OUT_ACK:
        return packet.bit_pattern
    else:
        raise UnknownPacketReceivedError(
                "Received packet command (%d) was not READ_OUT_ACK" %
                packet.command)

def send_read_input(hostname, port=DEFAULT_PORT):
    packet = PfionPacket(READ_IN_CMD)
    sock = send_packet(packet, hostname)
    p, sender = sock.recvfrom(BUFFER_SIZE)
    packet = PfionPacket().from_network(p)
    if packet.command == READ_IN_ACK:
        return packet.bit_pattern
    else:
        raise UnknownPacketReceivedError(
                "Received packet command (%d) was not READ_IN_ACK" %
                packet.command)

def send_digital_write(pin_number, pin_value, hostname, port=DEFAULT_PORT):
    packet = PfionPacket(DIGITAL_WRITE_CMD)
    packet.pin_number = pin_number
    packet.pin_value = pin_value
    sock = send_packet(packet, hostname)
    p, sender = sock.recvfrom(BUFFER_SIZE)
    packet = PfionPacket().from_network(p)
    if packet.command != DIGITAL_WRITE_ACK:
        raise UnknownPacketReceivedError(
                "Received packet command (%d) was not DIGITAL_WRITE_ACK" %
                packet.command)

def send_digital_read(pin_number, hostname, port=DEFAULT_PORT):
    packet = PfionPacket(DIGITAL_READ_CMD)
    packet.pin_number = pin_number
    sock = send_packet(packet, hostname)
    p, sender = sock.recvfrom(BUFFER_SIZE)
    packet = PfionPacket().from_network(p)
    if packet.command == DIGITAL_READ_ACK:
        return packet.pin_value
    else:
        raise UnknownPacketReceivedError(
                "Received packet command (%d) was not DIGITAL_READ_ACK" %
                packet.command)

########NEW FILE########
__FILENAME__ = spivisualiser
"""
spivisualiser.py
An SPI visualiser for sending SPI packets to the SPI port
"""
import pygtk
pygtk.require("2.0")
import gtk

import pfio


MAX_SPI_LOGS = 50


class SpiVisualiserSection(gtk.ScrolledWindow):
    def __init__(self, rpi_emulator=None):
        gtk.ScrolledWindow.__init__(self)
        self.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_ALWAYS)

        self.rpi_emulator = rpi_emulator

        # create a liststore with three string columns to use as the model
        self.liststore = gtk.ListStore(str, str, str, str, str)
        self.liststoresize = 0

        # create the TreeView using liststore
        self.treeview = gtk.TreeView(self.liststore)
        self.treeview.connect('size-allocate', self.treeview_changed)

        # create the TreeViewColumns to display the data
        self.tvcolumn = (gtk.TreeViewColumn('Time'),
                gtk.TreeViewColumn('In'),
                gtk.TreeViewColumn('In Breakdown'),
                gtk.TreeViewColumn('Out'),
                gtk.TreeViewColumn('Out Breakdown'))

        # add columns to treeview
        for column in self.tvcolumn:
            self.treeview.append_column(column)

        # create a CellRenderers to render the data
        self.cell = [gtk.CellRendererText() for i in range(5)]

        # set background color property
        self.cell[0].set_property('cell-background', 'cyan')
        self.cell[1].set_property('cell-background', '#87ea87')
        self.cell[2].set_property('cell-background', '#98fb98')
        self.cell[3].set_property('cell-background', '#ffccbb')
        self.cell[4].set_property('cell-background', '#ffddcc')

        # add the cells to the columns
        for i in range(len(self.tvcolumn)):
            self.tvcolumn[i].pack_start(self.cell[i], True)

        for i in range(len(self.tvcolumn)):
            self.tvcolumn[i].set_attributes(self.cell[i], text=i)

        # make treeview searchable
        self.treeview.set_search_column(0)

        # Allow sorting on the column
        self.tvcolumn[0].set_sort_column_id(0)

        # Allow drag and drop reordering of rows
        self.treeview.set_reorderable(True)

        self.add(self.treeview)
        self.treeview.show()

    def treeview_changed(self, widget, event, data=None):
        adjustment = self.get_vadjustment()
        adjustment.set_value(adjustment.upper - adjustment.page_size)

    def add_spi_log(self, time, data_tx, data_rx, custom_spi=False):
        if self.liststoresize >= MAX_SPI_LOGS:
            #remove the first item
            first_row_iter = self.treeview.get_model()[0].iter
            self.liststore.remove(first_row_iter)
        else:
            self.liststoresize += 1

        data_tx_breakdown = self.get_data_breakdown(data_tx)
        data_rx_breakdown = self.get_data_breakdown(data_rx)

        if custom_spi:
            in_fmt = "[0x%06x]" # use a special format
        else:
            in_fmt = "0x%06x"

        out_fmt = "0x%06x"

        data_tx_str = in_fmt  % data_tx
        data_rx_str = out_fmt % data_rx

        if self.rpi_emulator:
            self.rpi_emulator.spi_liststore_lock.acquire()

        self.liststore.append((time, data_tx_str, data_tx_breakdown, data_rx_str, data_rx_breakdown))

        if self.rpi_emulator:
            self.rpi_emulator.spi_liststore_lock.release()

    def get_data_breakdown(self, raw_data):
        cmd = (raw_data >> 16) & 0xff
        if cmd == pfio.WRITE_CMD:
            cmd = "WRITE"
        elif cmd == pfio.READ_CMD:
            cmd = "READ"
        else:
            cmd = hex(cmd)

        port = (raw_data >> 8) & 0xff
        if port == pfio.IODIRA:
            port = "IODIRA"
        elif port == pfio.IODIRB:
            port = "IODIRB"
        elif port == pfio.IOCON:
            port = "IOCON"
        elif port == pfio.GPIOA:
            port = "GPIOA"
        elif port == pfio.GPIOB:
            port = "GPIOB"
        elif port == pfio.GPPUA:
            port = "GPPUA"
        elif port == pfio.GPPUB:
            port = "GPPUB"
        else:
            port = hex(port)

        data = hex(raw_data & 0xff)

        data_breakdown = "cmd: %s, port: %s, data: %s" % (cmd, port, data)
        return data_breakdown

class SpiSenderSection(gtk.HBox):
    def __init__(self, rpi_emulator=None):
        gtk.HBox.__init__(self, False)
        
        self.rpi_emulator = rpi_emulator

        label = gtk.Label("SPI Input: ")
        label.show()

        self.spi_input = gtk.Entry()
        self.spi_input.set_text("0x0")
        self.spi_input.show()

        button = gtk.Button("Send")
        button.connect("clicked", self.send_spi_message)
        button.show()

        self.error_label = gtk.Label()
        self.error_label.show()

        if self.rpi_emulator:
            self.update_emu_button = gtk.Button("Update Emulator")
            self.update_emu_button.connect("clicked", self.update_emu_button_pressed)
            self.update_emu_button.show()
        else:
            self.pfio_init_button = gtk.Button("Initialise PFIO")
            self.pfio_init_button.connect("clicked", self.init_pfio)
            self.pfio_init_button.show()

        self.pack_start(child=label, expand=False)
        self.pack_start(child=self.spi_input, expand=False)
        self.pack_start(child=button, expand=False)
        self.pack_start(child=self.error_label, expand=False)

        if self.rpi_emulator:
            self.pack_end(child=self.update_emu_button, expand=False)
        else:
            self.pack_end(child=self.pfio_init_button, expand=False)

    def __set_error_label_text(self, text):
        self.__error_text = text
        self.error_label.set_markup("<span foreground='#ff0000'> %s</span>" % self.__error_text)

    def __get_error_label_text(self):
        return self.__error_text
    
    error_text = property(__get_error_label_text, __set_error_label_text)

    def send_spi_message(self, widget, data=None):
        self.error_text = ""
        spi_message = 0
        user_input = self.spi_input.get_text()
        try:
            if "0x" == user_input[:2]:
                spi_message = int(user_input, 16)
            elif "0b"== user_input[:2]:
                spi_message = int(user_input, 2)
            else:
                spi_message = int(user_input)

            # check we are three bytes long
            if len(hex(spi_message)[2:]) > 6:
                raise ValueError()

        except ValueError:
            msg = "Invalid SPI message"
            self.error_text = msg
            print msg
            return


        cmd  = (spi_message >> 16) & 0xff
        port = (spi_message >> 8) & 0xff
        data = (spi_message) & 0xff
        pfio.send([(cmd, port, data)], True)

    def update_emu_button_pressed(self, widget, data=None):
        self.rpi_emulator.output_override_section.reset_buttons()
        self.rpi_emulator.emu_screen.update_voutput_pins()

    def init_pfio(self, widget, data=None):
        pfio.init()


def init():
    window = gtk.Window()
    window.connect("delete-event", gtk.main_quit)
    window.set_title("SPI Visualiser")
    window.set_size_request(500, 200)

    visualiser = SpiVisualiserSection()
    sender     = SpiSenderSection()

    pfio.spi_handler = pfio.get_spi_handler()
    pfio.spi_visualiser_section = visualiser

    visualiser.show()
    sender.show()

    container = gtk.VBox()
    container.pack_start(child=visualiser, expand=True, fill=True)
    container.pack_start(child=sender, expand=False)
    container.show()
    window.add(container)
    window.show()
    gtk.main()

########NEW FILE########
__FILENAME__ = piface_test
from time import sleep
import sys
import unittest

import piface.emulator as pfio


class TestPiFace(unittest.TestCase):
	def setUp(self):
		'''Called at the start of each test'''
		pass

	def tearDown(self):
		'''Called at the end of each test'''
		pass

	def test_pin_translation(self):
		'''Tests the pin translation functions'''
		for pin in range(1, 9):
			bit_mask = pfio.get_pin_bit_mask(pin)
			self.assertEqual(bit_mask, 1 << (pin-1))
			number = pfio.get_pin_number(bit_mask)
			self.assertEqual(number, pin)

	def test_switches(self):
		print 'The left most switch is switch 1'
		for switch_num in range(1,5):
			sys.stdout.write('Press switch %d...' % switch_num)
			sys.stdout.flush()

			switch_values = self.get_switch_values()
			while switch_values == 0:
				switch_values = self.get_switch_values()

			pressed_switch = pfio.get_pin_number(switch_values)
			self.assertEqual(pressed_switch, switch_num,
					'Switch %d was pressed.' % pressed_switch)

			## bad test case, this re-queries the switch - need a way around this...
			# test the switch class
			#this_switch = pfio.Switch(switch_num)
			#self.assertEqual(this_switch.value, 1)

			print 'OK!'

			sleep(0.3)

			# before moving on, wait until no switches are pressed
			switch_values = self.get_switch_values()
			while switch_values != 0:
				switch_values = self.get_switch_values()

	def get_switch_values(self):
		'''Returns the on/off states of the switches. 1 is on 0 is off'''
		return pfio.read_input() & 0x0f

	def test_output_objects(self):
		OUTPUT_SLEEP_DELAY = 0.01
		# test there are no outputs
		self.assertEqual(0, pfio.read_output())

		for led_num in range(1, 5):
			this_led = pfio.LED(led_num)
			this_led.turn_on()
			sleep(OUTPUT_SLEEP_DELAY)
			expected_output_bpat = 1 << (led_num-1)
			self.assertEqual(expected_output_bpat, pfio.read_output())
			this_led.turn_off()
			sleep(OUTPUT_SLEEP_DELAY)
			self.assertEqual(0, pfio.read_output())

		for relay_num in range(1, 3):
			this_relay = pfio.Relay(relay_num)
			this_relay.turn_on()
			sleep(OUTPUT_SLEEP_DELAY)
			expected_output_bpat = 1 << (relay_num-1)
			self.assertEqual(expected_output_bpat, pfio.read_output())
			this_relay.turn_off()
			sleep(OUTPUT_SLEEP_DELAY)
			self.assertEqual(0, pfio.read_output())

if __name__ == '__main__':
	pfio.init()
	unittest.main()
	pfio.deinit()

########NEW FILE########
__FILENAME__ = scratch_handler
#!/usr/bin/env python

from array import array
from time import sleep
import threading
import socket
import sys
import struct

if "-e" in sys.argv:
    import piface.emulator as pfio
    sys.argv.remove("-e")
else:
    import piface.pfio as pfio

PORT = 42001
DEFAULT_HOST = '127.0.0.1'
BUFFER_SIZE = 100
SOCKET_TIMEOUT = 1
SENDER_DELAY = 0.02 # poll the Pi Face every 20ms

SCRATCH_SENSOR_NAME_INPUT = (
    'piface-input1',
    'piface-input2',
    'piface-input3',
    'piface-input4',
    'piface-input5',
    'piface-input6',
    'piface-input7',
    'piface-input8')

SCRATCH_SENSOR_NAME_OUTPUT = (
    'piface-output1',
    'piface-output2',
    'piface-output3',
    'piface-output4',
    'piface-output5',
    'piface-output6',
    'piface-output7',
    'piface-output8')


class ScratchSender(threading.Thread):
    def __init__(self, socket):
        threading.Thread.__init__(self)
        self.scratch_socket = socket
        self._stop = threading.Event()

        # make scratch aware of the pins
        for i in range(len(SCRATCH_SENSOR_NAME_INPUT)):
            self.broadcast_pin_update(i, 0)

    def stop(self):
        self._stop.set()

    def stopped(self):
        return self._stop.isSet()

    def run(self):
        last_bit_pattern = 0
        while not self.stopped():
            sleep(SENDER_DELAY)
            pin_bit_pattern = pfio.read_input()

            # if there is a change in the input pins
            changed_pins = pin_bit_pattern ^ last_bit_pattern
            if changed_pins:
                try:
                    self.broadcast_changed_pins(changed_pins, pin_bit_pattern)
                except Exception as e:
                    print e
                    break

            last_bit_pattern = pin_bit_pattern

    def broadcast_changed_pins(self, changed_pin_map, pin_value_map):
        for i in range(8):
            # if we care about this pin's value
            if (changed_pin_map >> i) & 0b1:
                pin_value = (pin_value_map >> i) & 0b1
                self.broadcast_pin_update(i, pin_value)

    def broadcast_pin_update(self, pin_index, value):
        sensor_name = SCRATCH_SENSOR_NAME_INPUT[pin_index]
        bcast_str = 'sensor-update "%s" %d' % (sensor_name, value)
        print 'sending: %s' % bcast_str
        self.send_scratch_command(bcast_str)

    def send_scratch_command(self, cmd):
        n = len(cmd)
        a = array('c')
        a.append(chr((n >> 24) & 0xFF))
        a.append(chr((n >> 16) & 0xFF))
        a.append(chr((n >>  8) & 0xFF))
        a.append(chr(n & 0xFF))
        self.scratch_socket.send(a.tostring() + cmd)

class ScratchListener(threading.Thread):
    def __init__(self, socket):
        threading.Thread.__init__(self)
        self.scratch_socket = socket
        self._stop = threading.Event()

        self.last_zero_bit_mask = 0
        self.last_one_bit_mask  = 0

    def stop(self):
        self._stop.set()

    def stopped(self):
        return self._stop.isSet()

    def run(self):
        while not self.stopped():
            try:
                data = self.scratch_socket.recv(BUFFER_SIZE)
                #length = struct.unpack(
                #        '>i',
                #        '%c%c%c%c' % (data[0], data[1], data[2], data[3])
                #    )[0]
                data = data[4:] # get rid of the length info
                #print 'Length: %d, Data: %s' % (length, data)

            except socket.timeout: # if we timeout, re-loop
                continue
            except: # exit on any other errrors
                break

            data = data.split(" ")
            
            if data[0] == 'sensor-update':
                data = data[1:]
                print 'received sensor-update:', data
                self.sensor_update(data)
                    
            elif data[0] == 'broadcast':
                data = data[1:]
                print 'received broadcast:', data

            else:
                print 'received something:', data

    def sensor_update(self, data):
        index_is_data = False # ignore the loop contents if not sensor
        zero_bit_mask = 0 # bit mask showing where zeros should be written
        one_bit_mask  = 0 # bit mask showing where ones should be written
        we_should_update_piface = False

        # go through all of the sensors that have been updated
        for i in range(len(data)):

            if index_is_data:
                index_is_data = False
                continue

            sensor_name = data[i].strip('"')
            
            # if this sensor is a piface output then reflect
            # that update on the board
            if sensor_name in SCRATCH_SENSOR_NAME_OUTPUT:
                we_should_update_piface = True
                pin_index = SCRATCH_SENSOR_NAME_OUTPUT.index(sensor_name)
                sensor_value = int(data[i+1])
                index_is_data = True

                # could this be made more efficient by sending a single write
                if sensor_value == 0:
                    zero_bit_mask ^= (1 << pin_index)

                else:
                    one_bit_mask ^= (1 << pin_index)

        if we_should_update_piface:
            old_pin_bitp = pfio.read_output() # grab the old values
            new_pin_bitp = old_pin_bitp & ~zero_bit_mask # set the zeros
            new_pin_bitp |= one_bit_mask # set the ones

            if new_pin_bitp != old_pin_bitp:
                pfio.write_output(new_pin_bitp) # write the new bit pattern


def create_socket(host, port):
    try:
        scratch_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        scratch_sock.connect((host, port))
    except socket.error:
        print "There was an error connecting to Scratch!"
        print "I couldn't find a Mesh session at host: %s, port: %s" % (host, port) 
        sys.exit(1)

    return scratch_sock

def cleanup_threads(threads):
    for thread in threads:
        thread.stop()

    for thread in threads:
        thread.join()

if __name__ == '__main__':
    if len(sys.argv) > 1:
        host = sys.argv[1]
    else:
        host = DEFAULT_HOST

    # open the socket
    print 'Connecting...' ,
    the_socket = create_socket(host, PORT)
    print 'Connected!'

    the_socket.settimeout(SOCKET_TIMEOUT)

    pfio.init()

    listener = ScratchListener(the_socket)
    sender = ScratchSender(the_socket)
    listener.start()
    sender.start()

    # wait for ctrl+c
    try:
        while True:
            pass
    except KeyboardInterrupt:
        cleanup_threads((listener, sender))
        pfio.deinit()
        sys.exit()

########NEW FILE########
