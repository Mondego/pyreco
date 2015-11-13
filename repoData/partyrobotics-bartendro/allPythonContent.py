__FILENAME__ = pump_id
#!/usr/bin/env python

import sys
import struct
import subprocess
import random
import argparse
import errno

PUMP_ID_FILE = "last_pump_id.txt"

def get_random_pump_id():
    random.seed()
    return random.randint(0, 254)

def get_pump_id():

    # Get a random id, just in case.
    id = get_random_pump_id()
    id_file = None

    # now try and see if we've got a saved pump id. If so, increment by one and save it
    try:
        id_file = open(PUMP_ID_FILE, "r")
        id = int(id_file.readline().strip()) + 1

        # Roll over the id, avoiding 255 and 0
        if id == 255:
            id = 1
    except IOError:
        pass
    except ValueError:
        print "Warning: Cannot read saved pump id. Try removing file %s " % PUMP_ID_FILE

    if id_file:
        id_file.close()

    try:
        id_file = open(PUMP_ID_FILE, "w")
        id_file.write("%d\n" % id)
    except IOError:
        print "Failed to save pump id to %s" % PUMP_ID_FILE

    if id_file:
        id_file.close()

    return id

parser = argparse.ArgumentParser()
parser.add_argument("file", help="The filename to write the pump id to")
parser.add_argument("id", nargs='?', help="The pump id to write to the file.", type=int, default=-1)
args = parser.parse_args()

if args.id < 0:
    id = get_pump_id()
else:
    id = args.id

try:
    f = open(args.file, "a")
    f.write(struct.pack("B", id))
    f.close()
except IOError, e:
    print "Error: ", e
    sys.exit(-1)

#cmd = "sudo avrdude -p m168 -P usb -c avrispmkII -U eeprom:w:%s:r -B 1.0" % sys.argv[1]
#subprocess.check_output(cmd)
print "Pump id %x written to %s" % (id, sys.argv[1])
sys.exit(0)

########NEW FILE########
__FILENAME__ = i2c-test
#!/usr/bin/env python

import smbus
import time
bus = smbus.SMBus(0)
address = 4 

while True:
    bus.write_byte(address, 34)
    time.sleep(.1)
    bus.write_byte(address, 75)
    time.sleep(.1)

########NEW FILE########
__FILENAME__ = user_button
#!/usr/bin/env python

# Beagleboard user button
# Copyright 2009 mechomaniac.com
import struct
import sys
import os

def wait_for_button():
	inputDevice = "/dev/input/event0"
	# format of the event structure (int, int, short, short, int)
	inputEventFormat = 'iihhi'
	inputEventSize = 16
	 
	try:
	    file = open(inputDevice, "rb") # standard binary file input
	except IOError:
	    print "Cannot open %s. Are you root?" % inputDevice
	    sys.exit(1)

	event = file.read(inputEventSize)
	while event:
	    (time1, time2, type, code, value) = struct.unpack(inputEventFormat, event)
	    if type == 1 and code == 276 and value == 1:
		file.close()
		return True
	    event = file.read(inputEventSize)

while True:
	wait_for_button()
        os.system("kill -9 `ps x | grep bartendro_server | grep -v grep | cut -d ' ' -f 2`")
        # MASSIVE HACK
        os.system("kill -9 `ps x | grep bartendro_server | grep -v grep | cut -d ' ' -f 3`")

########NEW FILE########
__FILENAME__ = clean
# -*- coding: utf-8 -*-
import logging
from time import sleep, time
from threading import Thread
from bartendro import db, app
from bartendro.error import BartendroBrokenError
from bartendro.router.driver import MOTOR_DIRECTION_FORWARD

CLEAN_DURATION = 10 # seconds

log = logging.getLogger('bartendro')

class CleanCycle(object):
    left_set = [4, 5, 6, 7, 8, 9, 10]
    right_set = [0, 1, 2, 3, 11, 12, 13, 14]
    STAGGER_DELAY = .150 # ms

    def __init__(self, mixer, mode):
        self.mixer = mixer
        self.mode = mode

    def clean(self):
        disp_list = []

        if self.mixer.disp_count == 15:
            if self.mode == "all":
                disp_list.extend(self.left_set)
                disp_list.extend(self.right_set)
            elif self.mode == "right":
                disp_list.extend(self.right_set)
            else:
                disp_list.extend(self.left_set)
        else:
            for d in xrange(self.mixer.disp_count):
                disp_list.append(d)

        self.mixer.driver.led_clean()
        for disp in disp_list:
            self.mixer.driver.set_motor_direction(disp, MOTOR_DIRECTION_FORWARD);
            self.mixer.driver.start(disp)
            sleep(self.STAGGER_DELAY)

        sleep(CLEAN_DURATION)
        for disp in disp_list:
            self.mixer.driver.stop(disp)
            sleep(self.STAGGER_DELAY)

        # Give bartendro a moment to collect himself
        sleep(.1)

        self.mixer.driver.led_idle()

        try:
            self.mixer.check_levels()
        except BartendroBrokenError, msg:
            log.error("Post clean: %s" % msg) 

########NEW FILE########
__FILENAME__ = constant
ML_PER_FL_OZ = 30 # ml per fl oz

########NEW FILE########
__FILENAME__ = error
# -*- coding: utf-8 -*-
import logging

log = logging.getLogger('bartendro')

class BartendroBusyError(Exception):
    def __init__(self, err):
        self.err = err
    def __str__(self):
        return repr(self.err)

class BartendroBrokenError(Exception):
    def __init__(self, err):
        self.err = err
    def __str__(self):
        return repr(self.err)

class BartendroCantPourError(Exception):
    def __init__(self, err):
        self.err = err
    def __str__(self):
        return repr(self.err)

class BartendroCurrentSenseError(Exception):
    def __init__(self, err):
        self.err = err
    def __str__(self):
        return repr(self.err)

class BartendroLiquidLevelReadError(Exception):
    def __init__(self, err):
        self.err = err
    def __str__(self):
        return repr(self.err)

class I2CIOError(Exception):
    pass

class SerialIOError(Exception):
    pass

########NEW FILE########
__FILENAME__ = booze
#!/usr/bin/env python
from wtforms import Form, TextField, DecimalField, HiddenField, validators, \
                          TextAreaField, SubmitField, SelectField
from bartendro.model import booze

class BoozeForm(Form):
    id = HiddenField(u"id", default=0)
    name = TextField(u"Name", [validators.Length(min=3, max=255)])
    brand = TextField(u"Brand") # Currently unused
    desc = TextAreaField(u"Description", [validators.Length(min=3, max=1024)])
    abv = DecimalField(u"ABV", [validators.NumberRange(0, 97)], default=0, places=0)
    type = SelectField(u"Type", [validators.NumberRange(0, len(booze.booze_types))], 
                                choices=booze.booze_types,
                                coerce=int)
    save = SubmitField(u"save")
    cancel = SubmitField(u"cancel")

form = BoozeForm()

########NEW FILE########
__FILENAME__ = dispenser
#!/usr/bin/env python
from wtforms import Form, SelectField, SubmitField

class DispenserForm(Form):

    save = SubmitField(u"save")
    cancel = SubmitField(u"cancel")

form = DispenserForm()

########NEW FILE########
__FILENAME__ = drink
#!/usr/bin/env python
from wtforms import Form, TextField, DecimalField, HiddenField, validators, TextAreaField, SubmitField, BooleanField

MAX_SUGGESTED_DRINK_SIZE = 5000 # in ml

class DrinkForm(Form):
    id = HiddenField(u"id", default=0)
    drink_name = TextField(u"Name", [validators.Length(min=3, max=255)])
    desc = TextAreaField(u"Description", [validators.Length(min=3, max=1024)])
    popular = BooleanField(u"List this drink in the <i>the essentials</i> section.")
    available = BooleanField(u"List this drink in the main menu")
    save = SubmitField(u"save")
    cancel = SubmitField(u"cancel")

form = DrinkForm()

########NEW FILE########
__FILENAME__ = login
#!/usr/bin/env python
from wtforms import Form, TextField, PasswordField, SubmitField, SelectField, validators

class LoginForm(Form):
    user = TextField(u"Name", [validators.Length(min=3, max=255)])
    password = PasswordField(u"Password", [validators.Length(min=3, max=255)])

    login = SubmitField(u"login")

form = LoginForm()

########NEW FILE########
__FILENAME__ = fsm
# States that Bartendro can be in
STATE_START =         0
STATE_CHECK =         1
STATE_READY =         2
STATE_LOW =           3
STATE_OUT =           4
STATE_HARD_OUT =      5
STATE_PRE_POUR =      6
STATE_POURING  =      7
STATE_POUR_DONE =     8
STATE_CURRENT_SENSE = 9
STATE_ERROR =         10
STATE_TEST_DISPENSE = 11
STATE_PRE_SHOT      = 12
STATE_POUR_SHOT     = 13

# Events that cause changes in Bartendro states
EVENT_START =          0
EVENT_LL_OK =          1
EVENT_LL_LOW =         2
EVENT_LL_OUT =         3
EVENT_LL_HARD_OUT =    4
EVENT_MAKE_DRINK =     5
EVENT_CHECK_LEVELS =   6
EVENT_POUR_DONE =      7
EVENT_CURRENT_SENSE =  8
EVENT_ERROR =          9
EVENT_POST_POUR_DONE = 10
EVENT_RESET          = 11
EVENT_DONE           = 12
EVENT_TEST_DISPENSE  = 13
EVENT_MAKE_SHOT      = 14

# Transition table for Bartendro
transition_table = [
#   Current state                     Event                         Next state
    (STATE_START,                     EVENT_START,                  STATE_CHECK),

    (STATE_READY,                     EVENT_MAKE_DRINK,             STATE_PRE_POUR),
    (STATE_READY,                     EVENT_CHECK_LEVELS,           STATE_CHECK),
    (STATE_READY,                     EVENT_TEST_DISPENSE,          STATE_TEST_DISPENSE),
    (STATE_READY,                     EVENT_MAKE_SHOT,              STATE_PRE_SHOT),
    (STATE_LOW,                       EVENT_MAKE_DRINK,             STATE_PRE_POUR),
    (STATE_LOW,                       EVENT_CHECK_LEVELS,           STATE_CHECK),
    (STATE_LOW,                       EVENT_TEST_DISPENSE,          STATE_TEST_DISPENSE),
    (STATE_LOW,                       EVENT_MAKE_SHOT,              STATE_PRE_SHOT),
    (STATE_OUT,                       EVENT_MAKE_DRINK,             STATE_PRE_POUR),
    (STATE_OUT,                       EVENT_CHECK_LEVELS,           STATE_CHECK),
    (STATE_OUT,                       EVENT_TEST_DISPENSE,          STATE_TEST_DISPENSE),
    (STATE_OUT,                       EVENT_MAKE_SHOT,              STATE_PRE_SHOT),
    (STATE_HARD_OUT,                  EVENT_CHECK_LEVELS,           STATE_CHECK),
    (STATE_HARD_OUT,                  EVENT_TEST_DISPENSE,          STATE_TEST_DISPENSE),
    # A shot can still be possible even when in HARD_OUT
    (STATE_HARD_OUT,                  EVENT_MAKE_DRINK,             STATE_PRE_POUR),
    (STATE_HARD_OUT,                  EVENT_MAKE_SHOT,              STATE_PRE_SHOT),
    (STATE_CURRENT_SENSE,             EVENT_RESET,                  STATE_CHECK),
    (STATE_ERROR,                     EVENT_RESET,                  STATE_CHECK),
    (STATE_ERROR,                     EVENT_TEST_DISPENSE,          STATE_TEST_DISPENSE),
    (STATE_ERROR,                     EVENT_CHECK_LEVELS,           STATE_CHECK),

    (STATE_TEST_DISPENSE,             EVENT_POUR_DONE,              STATE_CHECK),

    (STATE_PRE_POUR,                  EVENT_LL_OK,                  STATE_POURING),
    (STATE_PRE_POUR,                  EVENT_LL_LOW,                 STATE_POURING),
    (STATE_PRE_POUR,                  EVENT_LL_OUT,                 STATE_POURING),
    (STATE_PRE_POUR,                  EVENT_LL_HARD_OUT,            STATE_HARD_OUT),

    (STATE_POURING,                   EVENT_POUR_DONE,              STATE_POUR_DONE),
    (STATE_POURING,                   EVENT_CURRENT_SENSE,          STATE_CURRENT_SENSE),
    (STATE_POURING,                   EVENT_ERROR,                  STATE_ERROR),

    (STATE_POUR_DONE,                 EVENT_POST_POUR_DONE,         STATE_CHECK),

    (STATE_PRE_SHOT,                  EVENT_LL_OK,                  STATE_POUR_SHOT),
    (STATE_PRE_SHOT,                  EVENT_LL_LOW,                 STATE_POUR_SHOT),

    (STATE_POUR_SHOT,                 EVENT_POUR_DONE,              STATE_POUR_DONE),
    (STATE_POUR_SHOT,                 EVENT_CURRENT_SENSE,          STATE_CURRENT_SENSE),
    (STATE_POUR_SHOT,                 EVENT_ERROR,                  STATE_ERROR),

    (STATE_POUR_DONE,                 EVENT_POST_POUR_DONE,         STATE_CHECK),

    (STATE_CHECK,                     EVENT_LL_OK,                  STATE_READY),
    (STATE_CHECK,                     EVENT_LL_LOW,                 STATE_LOW),
    (STATE_CHECK,                     EVENT_LL_OUT,                 STATE_OUT),
    (STATE_CHECK,                     EVENT_LL_HARD_OUT,            STATE_HARD_OUT),
]

end_states = [STATE_READY, STATE_LOW, STATE_OUT, STATE_HARD_OUT, STATE_CURRENT_SENSE, STATE_ERROR]

########NEW FILE########
__FILENAME__ = global_lock
#!/usr/bin/env python

from bartendro import fsm
from bartendro.error import BartendroBusyError

try:
    import uwsgi
    have_uwsgi = True
except ImportError:
    have_uwsgi = False

class BartendroLock(object):
    def __init__(self, globals):
        self.globals = globals

    def __enter__(self):
        if not self.globals.lock_bartendro():
            raise BartendroBusyError("Bartendro is busy dispensing")

    def __exit__(self, type, value, traceback):
        self.globals.unlock_bartendro()
    
class BartendroGlobalLock(object):
    '''This class manages the few global settings that Bartendro needs including a global state and
       a global Bartendro lock to prevent concurrent access to the hardware'''


    def __init__(self):
        self.state = fsm.STATE_START

    def lock_bartendro(self):
        """Call this function before making a drink or doing anything that where two users' action may conflict.
           This function will return True if the lock was granted, of False is someone else has already locked 
           Bartendro."""

        # If we're not running inside uwsgi, then don't try to use the lock
        if not have_uwsgi: return True

        uwsgi.lock()
        is_locked = uwsgi.sharedarea_readbyte(0)
        if is_locked:
           uwsgi.unlock()
           return False
        uwsgi.sharedarea_writebyte(0, 1)
        uwsgi.unlock()

        return True

    def unlock_bartendro(self):
        """Call this function when you've previously locked bartendro and now you want to unlock it."""

        # If we're not running inside uwsgi, then don't try to use the lock
        if not have_uwsgi: return True

        uwsgi.lock()
        is_locked = uwsgi.sharedarea_readbyte(0)
        if not is_locked:
           uwsgi.unlock()
           return False
        uwsgi.sharedarea_writebyte(0, 0)
        uwsgi.unlock()

        return True

    def get_state(self):
        '''Get the current state of Bartendro'''

        # If we're not running inside uwsgi, then we can't keep global state
        if not have_uwsgi: return self.state

        uwsgi.lock()
        state = uwsgi.sharedarea_readbyte(1)
        uwsgi.unlock()

        return state

    def set_state(self, state):
        """Set the current state of Bartendro"""

        # If we're not running inside uwsgi, then don't try to use the lock
        if not have_uwsgi: 
            self.state = state
            return

        uwsgi.lock()
        uwsgi.sharedarea_writebyte(1, state)
        uwsgi.unlock()

        return True

########NEW FILE########
__FILENAME__ = mixer
# -*- coding: utf-8 -*-
import logging
import sys
import traceback
from time import sleep, time
from threading import Thread
from flask import Flask, current_app
from flask.ext.sqlalchemy import SQLAlchemy
import memcache
from sqlalchemy.orm import mapper, relationship, backref
from bartendro import db, app
from bartendro import fsm
from bartendro.clean import CleanCycle
from bartendro.pourcomplete import PourCompleteDelay
from bartendro.router.driver import MOTOR_DIRECTION_FORWARD
from bartendro.model.drink import Drink
from bartendro.model.dispenser import Dispenser
from bartendro.model.drink_log import DrinkLog
from bartendro.model.shot_log import ShotLog
from bartendro.global_lock import BartendroLock
from bartendro.error import BartendroBusyError, BartendroBrokenError, BartendroCantPourError, BartendroCurrentSenseError

TICKS_PER_ML = 2.78
CALIBRATE_ML = 60 
CALIBRATION_TICKS = TICKS_PER_ML * CALIBRATE_ML

FULL_SPEED = 255
HALF_SPEED = 166
SLOW_DISPENSE_THRESHOLD = 20 # ml
MAX_DISPENSE = 1000 # ml max dispense per call. Just for sanity. :)

LIQUID_OUT_THRESHOLD   = 75
LIQUID_LOW_THRESHOLD   = 120 

LL_OUT     = 0
LL_OK      = 1
LL_LOW     = 2

log = logging.getLogger('bartendro')

class BartendroLiquidLevelReadError(Exception):
    pass

class Recipe(object):
    ''' Define everything related to dispensing one or more liquids at the same time '''
    def __init__(self):
        self.data = {}
        self.drink = None   # Use for dispensing drinks
        self.booze  = None  # Use for dispensing single shots of one booze

class Mixer(object):
    '''The mixer object is the heart of Bartendro. This is where the state of the bot
       is managed, checked if drinks can be made, and actually make drinks. Everything
       else in Bartendro lives for *this* *code*. :) '''

    def __init__(self, driver, mc):
        self.driver = driver
        self.mc = mc
        self.disp_count = self.driver.count()
        self.do_event(fsm.EVENT_START)
        self.err = ""

    def check_levels(self):
        with BartendroLock(app.globals):
            self.do_event(fsm.EVENT_CHECK_LEVELS)

    def dispense_shot(self, dispenser, ml):
        r = Recipe()
        r.data = { dispenser.booze.id : ml }
        r.booze = dispenser.booze
        self.recipe = r

        with BartendroLock(app.globals):
            self.do_event(fsm.EVENT_MAKE_SHOT)
            t = int(time())
            slog = ShotLog(dispenser.booze.id, t, ml)
            db.session.add(slog)
            db.session.commit()

    def dispense_ml(self, dispenser, ml):
        r = Recipe()
        r.data = { dispenser.booze.id : ml }
        r.booze = dispenser.booze
        self.recipe = r

        with BartendroLock(app.globals):
            self.do_event(fsm.EVENT_TEST_DISPENSE)

    def make_drink(self, drink, recipe):
        r = Recipe()
        r.data = recipe
        r.drink = drink
        self.recipe = r

        with BartendroLock(app.globals):
            self.do_event(fsm.EVENT_MAKE_DRINK)
            if drink and drink.id:
                size = 0
                for k in recipe.keys():
                    size += recipe[k] 
                t = int(time())
                dlog = DrinkLog(drink.id, t, size)
                db.session.add(dlog)
                db.session.commit()

    def do_event(self, event):
        cur_state = app.globals.get_state()
    
        while True:
            next_state = None
            for t_state, t_event, t_next_state in fsm.transition_table:
                if t_state == cur_state and event == t_event:
                    next_state = t_next_state
                    break
            
            if not next_state:
                log.error("Current state %d, event %d. No next state." % (cur_state, event))
                raise BartendroBrokenError("Bartendro is unable to pour drinks right now. Sorry.")
            #print "cur state: %d event: %d next state: %d" % (cur_state, event, next_state)

            try:
                if next_state == fsm.STATE_PRE_POUR:
                    event = self._state_pre_pour()
                elif next_state == fsm.STATE_CHECK:
                    event = self._state_check()
                elif next_state == fsm.STATE_PRE_SHOT:
                    event = self._state_pre_shot()
                elif next_state == fsm.STATE_READY:
                    event = self._state_ready()
                elif next_state == fsm.STATE_LOW:
                    event = self._state_low()
                elif next_state == fsm.STATE_OUT:
                    event = self._state_out()
                elif next_state == fsm.STATE_HARD_OUT:
                    event = self._state_hard_out()
                elif next_state == fsm.STATE_POURING or next_state == fsm.STATE_POUR_SHOT:
                    event = self._state_pouring()
                elif next_state == fsm.STATE_POUR_DONE:
                    event = self._state_pour_done()
                elif next_state == fsm.STATE_CURRENT_SENSE:
                    event = self._state_current_sense()
                elif next_state == fsm.STATE_ERROR:
                    event = self._state_error()
                elif next_state == fsm.STATE_TEST_DISPENSE:
                    event = self._state_test_dispense()
                else:
                    self._state_error()
                    app.globals.set_state(fsm.STATE_ERROR)
                    log.error("Current state: %d, event %d. Can't find next state." % (cur_state, event))
                    raise BartendroBrokenError("Internal error. Bartendro has had one too many.")

            except BartendroBrokenError, err:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                #traceback.print_tb(exc_traceback)
                self._state_error()
                app.globals.set_state(fsm.STATE_ERROR)
                raise

            except BartendroCantPourError, err:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                #traceback.print_tb(exc_traceback)
                raise
                
            except BartendroCurrentSenseError, err:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                #traceback.print_tb(exc_traceback)
                raise BartendroBrokenError(err)

            cur_state = next_state
            if cur_state in fsm.end_states:
                break

        app.globals.set_state(cur_state)

    def _state_check(self):
        try:
            ll = self._check_liquid_levels()
        except BartendroLiquidLevelReadError:
            raise BartendroBrokenError("Failed to read liquid levels")

        # update the list of drinks we can make
        drinks = self.get_available_drink_list()
        if len(drinks) == 0:
            return fsm.EVENT_LL_HARD_OUT

        if ll == LL_OK:
            return fsm.EVENT_LL_OK

        if ll == LL_LOW:
            return fsm.EVENT_LL_LOW

        return fsm.EVENT_LL_OUT

    def _state_pre_pour(self):
        try:
            ll = self._check_liquid_levels()
        except BartendroLiquidLevelReadError:
            raise BartendroBrokenError("Failed to read liquid levels")

        # update the list of drinks we can make
        drinks = self.get_available_drink_list()
        if len(drinks) == 0:
            raise BartendroCantPourError("Cannot make this drink now.")

        if ll == LL_OK:
            return fsm.EVENT_LL_OK

        if ll == LL_LOW:
            return fsm.EVENT_LL_LOW

        return LL_OUT

    def _state_pre_shot(self):

        if not app.options.use_liquid_level_sensors:
            return fsm.EVENT_LL_OK

        try:
            ll = self._check_liquid_levels()
        except BartendroLiquidLevelReadError:
            raise BartendroBrokenError("Failed to read liquid levels")

        booze_id = self.recipe.data.keys()[0]
        dispensers = db.session.query(Dispenser).order_by(Dispenser.id).all()
        for i, disp in enumerate(dispensers):
            if disp.booze_id == booze_id:
                if disp.out == LL_OUT:
                    if ll == LL_OK:
                        app.globals.set_state(fsm.STATE_OK)
                    elif ll == LL_LOW:
                        app.globals.set_state(fsm.STATE_LOW)
                    elif ll == LL_OUT:
                        app.globals.set_state(fsm.STATE_OUT)
                    else:
                        app.globals.set_state(fsm.STATE_HARD_OUT)

                    raise BartendroCantPourError("Cannot make drink: Dispenser %d is out of booze." % (i+1))
                break

        return fsm.EVENT_LL_OK

    def _state_ready(self):
        self.driver.set_status_color(0, 1, 0)
        return fsm.EVENT_DONE

    def _state_low(self):
        self.driver.led_idle()
        self.driver.set_status_color(1, 1, 0)
        return fsm.EVENT_DONE

    def _state_out(self):
        self.driver.led_idle()
        self.driver.set_status_color(1, 0, 0)
        return fsm.EVENT_DONE

    # TODO: Make the hard out blink the status led
    def _state_hard_out(self):
        self.driver.led_idle()
        self.driver.set_status_color(1, 0, 0)
        return fsm.EVENT_DONE

    def _state_current_sense(self):
        return fsm.EVENT_DONE

    def _state_error(self):
        self.driver.led_idle()
        self.driver.set_status_color(1, 0, 0)
        return fsm.EVENT_DONE

    def _state_pouring(self):
        self.driver.led_dispense()

        recipe = {}
        size = 0
        log_lines = {}
        dispensers = db.session.query(Dispenser).order_by(Dispenser.id).all()
        for booze_id in sorted(self.recipe.data.keys()):
            found = False
            for i in xrange(self.disp_count):
                disp = dispensers[i]

                if booze_id == disp.booze_id:
                    # if we're out of booze, don't consider this drink
                    if app.options.use_liquid_level_sensors and disp.out == LL_OUT:
                        raise BartendroCantPourError("Cannot make drink: Dispenser %d is out of booze." % (i+1))

                    found = True
                    ml = self.recipe.data[booze_id]
                    if ml <= 0:
                        log_lines[i] = "  %-2d %-32s %d ml (not dispensed)" % (i, "%s (%d)" % (disp.booze.name, disp.booze.id), ml)
                        continue

                    if ml > MAX_DISPENSE:
                        raise BartendroCantPourError("Cannot make drink. Invalid dispense quantity: %d ml. (Max %d ml)" % (ml, MAX_DISPENSE))

                    recipe[i] =  ml
                    size += ml
                    log_lines[i] = "  %-2d %-32s %d ml" % (i, "%s (%d)" % (disp.booze.name, disp.booze.id), ml)
                    self.driver.set_motor_direction(i, MOTOR_DIRECTION_FORWARD);
                    continue

            if not found:
                raise BartendroCantPourErro("Cannot make drink. I don't have the required booze: %d" % booze_id)

        self._dispense_recipe(recipe)

        if self.recipe.drink:
            log.info("Made cocktail: %s" % self.recipe.drink.name.name)
        else:
            log.info("Made custom drink:")
        for line in sorted(log_lines.keys()):
            log.info(log_lines[line])
        log.info("%s ml dispensed. done." % size)

        return fsm.EVENT_POUR_DONE

    def _state_test_dispense(self):

        booze_id = self.recipe.data.keys()[0]
        ml = self.recipe.data[booze_id]

        recipe = {}
        dispensers = db.session.query(Dispenser).order_by(Dispenser.id).all()
        for i in xrange(self.disp_count):
            if booze_id == dispensers[i].booze_id:
                recipe[i] =  ml
                self._dispense_recipe(recipe, True)
                break

        return fsm.EVENT_POUR_DONE

    def _state_pour_done(self):
        self.driver.led_complete()
        PourCompleteDelay(self).start()

        return fsm.EVENT_POST_POUR_DONE

    def reset(self):
        self.driver.led_idle()
        app.globals.set_state(fsm.STATE_START)
        self.do_event(fsm.EVENT_START)

    def clean(self):
        CleanCycle(self, "all").clean()

    def clean_right(self):
        CleanCycle(self, "right").clean()

    def clean_left(self):
        CleanCycle(self, "left").clean()

    def liquid_level_test(self, dispenser, threshold):
        if app.globals.get_state() == fsm.STATE_ERROR:
            return 
        if not app.options.use_liquid_level_sensors: return

        log.info("Start liquid level test: (disp %s thres: %d)" % (dispenser, threshold))

        if not self.driver.update_liquid_levels():
            raise BartendroBrokenError("Failed to update liquid levels")
        sleep(.01)

        level = self.driver.get_liquid_level(dispenser)
	log.info("initial reading: %d" % level)
        if level <= threshold:
	    log.info("liquid is out before starting: %d" % level)
	    return

        last = -1
        self.driver.start(dispenser)
        while level > threshold:
            if not self.driver.update_liquid_levels():
                raise BartendroBrokenError("Failed to update liquid levels")
                return
            sleep(.01)
            level = self.driver.get_liquid_level(dispenser)
            if level != last:
                 log.info("  %d" % level)
            last = level

        self.driver.stop(dispenser)
        log.info("Stopped at level: %d" % level)
        sleep(.1);
        level = self.driver.get_liquid_level(dispenser)
        log.info("motor stopped at level: %d" % level)

    def get_available_drink_list(self):
        if app.globals.get_state() == fsm.STATE_ERROR:
            return []

        can_make = self.mc.get("available_drink_list")
        if can_make: 
            return can_make

        add_boozes = db.session.query("abstract_booze_id") \
                            .from_statement("""SELECT bg.abstract_booze_id 
                                                 FROM booze_group bg 
                                                WHERE id 
                                                   IN (SELECT distinct(bgb.booze_group_id) 
                                                         FROM booze_group_booze bgb, dispenser 
                                                        WHERE bgb.booze_id = dispenser.booze_id)""")

        if app.options.use_liquid_level_sensors: 
            sql = "SELECT booze_id FROM dispenser WHERE out == 1 or out == 2 ORDER BY id LIMIT :d"
        else:
            sql = "SELECT booze_id FROM dispenser ORDER BY id LIMIT :d"

        boozes = db.session.query("booze_id") \
                        .from_statement(sql) \
                        .params(d=self.disp_count).all()
        boozes.extend(add_boozes)

        booze_dict = {}
        for booze_id in boozes:
            booze_dict[booze_id[0]] = 1

        drinks = db.session.query("drink_id", "booze_id") \
                        .from_statement("SELECT d.id AS drink_id, db.booze_id AS booze_id FROM drink d, drink_booze db WHERE db.drink_id = d.id ORDER BY d.id, db.booze_id") \
                        .all()
        last_drink = -1
        boozes = []
        can_make = []
        for drink_id, booze_id in drinks:
            if last_drink < 0: last_drink = drink_id
            if drink_id != last_drink:
                if self._can_make_drink(boozes, booze_dict): 
                    can_make.append(last_drink)
                boozes = []
            boozes.append(booze_id)
            last_drink = drink_id

        if self._can_make_drink(boozes, booze_dict): 
            can_make.append(last_drink)

        self.mc.set("available_drink_list", can_make)
        return can_make

    # ----------------------------------------
    # Private methods
    # ----------------------------------------

    def _check_liquid_levels(self):
        """ Ask the dispense to update their own liquid levels and then fetch the levels
            and set the machine state accordingly. """

        if not app.options.use_liquid_level_sensors: 
            return LL_OK

        ll_state = LL_OK

        log.info("mixer.check_liquid_levels: check levels");
        # step 1: ask the dispensers to update their liquid levels
        if not self.driver.update_liquid_levels():
            raise BartendroLiquidLevelReadError("Failed to update liquid levels")

        # wait for the dispensers to determine the levels
        sleep(.01)

        # Now ask each dispenser for the actual level
        dispensers = db.session.query(Dispenser).order_by(Dispenser.id).all()

        clear_cache = False
        for i, dispenser in enumerate(dispensers):
            if i >= self.disp_count:
                break

            level = self.driver.get_liquid_level(i)
            if level < 0:
                raise BartendroLiquidLevelReadError("Failed to read liquid levels from dispenser %d" % (i+1))

            log.info("dispenser %d level: %d (stored: %d)" % (i, level, dispenser.out))

            if level <= LIQUID_OUT_THRESHOLD:
                ll_state = LL_OUT
                if dispenser.out != LL_OUT:
                    clear_cache = True
                dispenser.out = LL_OUT

            elif level <= LIQUID_LOW_THRESHOLD:
                if ll_state == LL_OK:
                    ll_state = LL_LOW

                if dispenser.out == LL_OUT:
                    clear_cache = True
                dispenser.out = LL_LOW

            else:
                if dispenser.out == LL_OUT:
                    clear_cache = True

                dispenser.out = LL_OK

        db.session.commit()

        if clear_cache:
            self.mc.delete("top_drinks")
            self.mc.delete("other_drinks")
            self.mc.delete("available_drink_list")

        log.info("Checking levels done. New state: %d" % ll_state)

        return ll_state

    def _dispense_recipe(self, recipe, always_fast = False):

        active_disp = []
        for disp in recipe:
            if not recipe[disp]:
                continue
            ticks = int(recipe[disp] * TICKS_PER_ML)
            if recipe[disp] < SLOW_DISPENSE_THRESHOLD and not always_fast:
                speed = HALF_SPEED 
            else:
                speed = FULL_SPEED 

            self.driver.set_motor_direction(disp, MOTOR_DIRECTION_FORWARD);
            if not self.driver.dispense_ticks(disp, ticks, speed):
                raise BartendroBrokenError("Dispense error. Dispense %d ticks, speed %d on dispenser %d failed." % (ticks, speed, disp + 1))

            active_disp.append(disp)
            sleep(.01)

        for disp in active_disp:
            while True:
                (is_dispensing, over_current) = app.driver.is_dispensing(disp)
                log.debug("is_disp %d, over_cur %d" % (is_dispensing, over_current))

                # If we get errors here, try again. Running motors can cause noisy comm lines
                if is_dispensing < 0 or over_current < 0:
                    log.error("Is dispensing test on dispenser %d failed. Ignoring." % (disp + 1))
                    sleep(.2)
                    continue

                if over_current:
                    raise BartendroCurrentSenseError("One of the pumps did not operate properly. Your drink is broken. Sorry. :(")

                if is_dispensing == 0: 
                    break 

                sleep(.1)

    def _can_make_drink(self, boozes, booze_dict):
        ok = True
        for booze in boozes:
            try:
                foo = booze_dict[booze]
            except KeyError:
                ok = False
        return ok


########NEW FILE########
__FILENAME__ = booze
# -*- coding: utf-8 -*-
from bartendro import db
from sqlalchemy.orm import mapper, relationship
from sqlalchemy import Table, Column, Integer, String, MetaData, Unicode, UnicodeText, UniqueConstraint, Text, Index
from sqlalchemy.ext.declarative import declarative_base

BOOZE_TYPE_UNKNOWN = 0
BOOZE_TYPE_ALCOHOL = 1
BOOZE_TYPE_TART = 2
BOOZE_TYPE_SWEET = 3
booze_types = [
               (0, "Unknown"),
               (1, "Alcohol"),
               (2, "Tart"),
               (3, "Sweet")
              ]

class Booze(db.Model):
    """
    Information about a booze. e.g. water, vodka, grandine, bailies, oj 
    """

    __tablename__ = 'booze'
    id = Column(Integer, primary_key=True)
    name = Column(UnicodeText, nullable=False)
    brand = Column(UnicodeText, nullable=True)
    desc = Column(UnicodeText, nullable=False)
    abv = Column(Integer, default=0)
    type = Column(Integer, default=0)

    # add unique constraint for name
    UniqueConstraint('name', name='booze_name_undx')
 
    query = db.session.query_property()
    def __init__(self, name = u'', brand = u'', desc = u'', abv = 0, type = 0, out = 0, data = None):
        if data: 
            self.update(data)
            return
        self.name = name
        self.brand = brand
        self.desc = desc
        self.abv = abv
        self.type = type
        self.out = out

    def update(self, data):
        self.name = data['name']
        self.desc = data['desc']
        self.brand = data['brand']
        self.abv = int(data['abv'])
        self.type = int(data['type'])

    def is_abstract(self):
        return len(self.booze_group)

    def __repr__(self):
        return "<Booze('%s','%s')>" % (self.id, self.name)

Index('booze_name_ndx', Booze.name)

########NEW FILE########
__FILENAME__ = booze_group
# -*- coding: utf-8 -*-
from bartendro import db
from sqlalchemy.orm import mapper, relationship
from sqlalchemy import Table, Column, Integer, String, MetaData, UnicodeText, ForeignKey
from sqlalchemy.ext.declarative import declarative_base

class BoozeGroup(db.Model):
    """
    This table groups boozes into a booze class. Titos, Smirnoff and Grey Goose
    are all part of the Vodka booze class.
    """

    __tablename__ = 'booze_group'
    id = Column(Integer, primary_key=True)
    abstract_booze_id = Column(Integer, ForeignKey('booze.id'), nullable=False)
    name = Column(UnicodeText, nullable=False)
 
    query = db.session.query_property()

    def __init__(self, name = u''):
        self.name = name
        db.session.add(self)

    def json(self):
        return { 
                 'id' : self.id, 
                 'name' : self.name,
               }

    def __repr__(self):
        return "<BoozeGroup(%d,<Booze>(%d),'%s',%s)>" % (self.id or -1, 
                                                      self.abstract_booze_id,
                                                      self.name,
                                                      " ".join(["<BoozeGroupBooze>(%d)" % (bgb.id or -1) for bgb in self.booze_group_boozes]))

########NEW FILE########
__FILENAME__ = booze_group_booze
# -*- coding: utf-8 -*-
from bartendro import db
from sqlalchemy.orm import mapper, relationship
from sqlalchemy import Table, Column, Integer, String, MetaData, UnicodeText, ForeignKey
from sqlalchemy.ext.declarative import declarative_base

class BoozeGroupBooze(db.Model):
    """
    Join between the Drink table and the Booze table for 1:n relationship
    """

    __tablename__ = 'booze_group_booze'
    id = Column(Integer, primary_key=True)
    booze_group_id = Column(Integer, ForeignKey('booze_group.id'), nullable=False)
    booze_id = Column(Integer, ForeignKey('booze.id'), nullable=False)
    sequence = Column(Integer, default=0)
 
    query = db.session.query_property()

    def __init__(self, sequence):
        self.sequence = sequence
        db.session.add(self)

    def __repr__(self):
        return "<BoozeGroupBooze(%d,BoozeGroup(%d),<Booze>(%d),%d)>" % (self.id or -1, 
                                                 self.booze_group_id,
                                                 self.booze.id or -1,
                                                 self.sequence)


########NEW FILE########
__FILENAME__ = custom_drink
# -*- coding: utf-8 -*-
from bartendro import db
from sqlalchemy.orm import mapper, relationship
from sqlalchemy import Table, Column, Integer, String, MetaData, UnicodeText, ForeignKey
from sqlalchemy.ext.declarative import declarative_base

class CustomDrink(db.Model):
    """
    This class provides details about customizable drinks. 
    """

    __tablename__ = 'custom_drink'
    id = Column(Integer, primary_key=True)
    drink_id = Column(Integer, ForeignKey('drink.id'), nullable=False)
    name = Column(UnicodeText, nullable=False)
 
    query = db.session.query_property()

    def __init__(self, name = u''):
        self.name = name
        db.session.add(self)

    def __repr__(self):
        return "<CustomDrink(%d,<Drink>(%d),'%s')>" % (self.id or -1, 
                                                      self.drink_id,
                                                      self.name)

########NEW FILE########
__FILENAME__ = dispenser
# -*- coding: utf-8 -*-
from bartendro import db
from sqlalchemy.orm import mapper, relationship
from sqlalchemy import Table, Column, Integer, ForeignKey
from sqlalchemy.ext.declarative import declarative_base

class Dispenser(db.Model):
    """
    Information about a dispenser
    """

    __tablename__ = 'dispenser'
    id = Column(Integer, primary_key=True)
    booze_id = Column(Integer, ForeignKey('booze.id'), nullable=False)
    actual = Column(Integer, default = 0)
    out = Column(Integer, default=0)

    query = db.session.query_property()
    def __init__(self, booze, actual):
        self.booze = booze
        self.booze_id = booze.id
        self.actual = actual

    def json(self):
        return { 
                 'id' : self.id, 
                 'booze' : self.booze_id
               }

    def __repr__(self):
        return "<Dispenser('%s','%s')>" % (self.id, self.booze_id)

########NEW FILE########
__FILENAME__ = drink
# -*- coding: utf-8 -*-
from bartendro import db
from sqlalchemy.orm import mapper, relationship
from sqlalchemy import Table, Column, Integer, String, MetaData, UnicodeText, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from bartendro.model.drink_name import DrinkName
from operator import attrgetter

DEFAULT_SUGGESTED_DRINK_SIZE = 118 #ml (4 oz)

class Drink(db.Model):
    """
    Defintion of a drink. Pretty bare since name is in drink_name and drink details are in drink_liquid
    """

    __tablename__ = 'drink'
    id = Column(Integer, primary_key=True)
    desc = Column(UnicodeText, nullable=False)
    name_id = Column(Integer, ForeignKey('drink_name.id'), nullable=False)
    sugg_size = Column(Integer)
    popular = Column(Boolean)
    available = Column(Boolean)

    # Not for storing in the DB, but for telling the UI if a drink is lucky
    am_lucky = 0

    query = db.session.query_property()

    def __init__(self, desc = u'', data = None, size = DEFAULT_SUGGESTED_DRINK_SIZE, popular = False, available = True):
        self.name = DrinkName()
        if data: 
            self.update(data)
            return
        self.desc = desc
        self.size = size
        self.popular = popular
        self.available = available
        self.sugg_size = 0
        db.session.add(self)
    
    def set_ingredients_text(self, txt=""):
        self.ingredients = [{ 'name' : txt, 
                              'id' : 0, 
                              'parts' : 1, 
                              'type' : 0 
                           }]

    def process_ingredients(self):
        ing = []

        self.drink_boozes = sorted(self.drink_boozes, key=attrgetter('booze.abv', 'booze.name'), reverse=True)
        for db in self.drink_boozes:
            ing.append({ 'name' : db.booze.name, 
                         'id' : db.booze.id, 
                         'parts' : db.value, 
                         'type' : db.booze.type 
                       })
        self.ingredients = ing

    def set_lucky(self, lucky):
        self.am_lucky = lucky

    def __repr__(self):
        return "<Drink>(%d,%s,%s,%s)>" % (self.id or -1, self.name.name, self.desc, " ".join(["<DrinkBooze>(%d)" % (db.id or -1) for db in self.drink_boozes]))


########NEW FILE########
__FILENAME__ = drink_booze
# -*- coding: utf-8 -*-
from bartendro import db
from sqlalchemy.orm import mapper, relationship
from sqlalchemy import Table, Column, Integer, String, MetaData, UnicodeText, ForeignKey
from sqlalchemy.ext.declarative import declarative_base

class DrinkBooze(db.Model):
    """
    Join between the Drink table and the Booze table for 1:n relationship
    """

    __tablename__ = 'drink_booze'
    id = Column(Integer, primary_key=True)
    drink_id = Column(Integer, ForeignKey('drink.id'), nullable=False)
    booze_id = Column(Integer, ForeignKey('booze.id'), nullable=False)
    value = Column(Integer, default=1)
    unit = Column(Integer, default=1)
 
    query = db.session.query_property()

    def __init__(self, drink, booze, value, unit):
        self.drink = drink
        self.drink_id = drink.id
        self.booze = booze
        self.booze_id = booze.id
        self.value = value
        self.unit = unit
#        db.session.add(self)

    def json(self):
        return { 
                 'id' : self.id, 
                 'value' : self.value,
                 'unit' : self.unit,
               }

    def __repr__(self):
        return "<DrinkBooze(%d,<Drink>(%d),<Booze>(%d),%d,%d)>" % (self.id or -1, 
                                                 self.drink.id,
                                                 self.booze.id or -1,
                                                 self.value, 
                                                 self.unit)


########NEW FILE########
__FILENAME__ = drink_log
# -*- coding: utf-8 -*-
from bartendro import db
from sqlalchemy.orm import mapper, relationship
from sqlalchemy import Table, Column, Integer, String, MetaData, Unicode, UnicodeText, UniqueConstraint, ForeignKey
from sqlalchemy.ext.declarative import declarative_base

class DrinkLog(db.Model):
    """
    Keeps a record of everything we've dispensed
    """

    __tablename__ = 'drink_log'
    id = Column(Integer, primary_key=True)
    drink_id = Column(Integer, ForeignKey('drink.id'), nullable=False)
    time = Column(Integer, nullable=False, default=0)
    size = Column(Integer, nullable=False, default=-1)
 
    query = db.session.query_property()

    def __init__(self, drink_id, time, size):
        self.drink_id = drink_id
        self.time = time
        self.size = size
        db.session.add(self)

    def __repr__(self):
        return "<DrinkLog(%d,'%s')>" % (self.id, self.drink_id)


########NEW FILE########
__FILENAME__ = drink_name
# -*- coding: utf-8 -*-
from bartendro import db
from sqlalchemy.orm import mapper, relationship
from sqlalchemy import Table, Column, Integer, String, MetaData, Unicode, UnicodeText, UniqueConstraint, Text
from sqlalchemy.ext.declarative import declarative_base

class DrinkName(db.Model):
    """
    Name of a drink, complete with a sortname
    """

    __tablename__ = 'drink_name'
    id = Column(Integer, primary_key=True)
    name = Column(UnicodeText, nullable=False)
    sortname = Column(UnicodeText, nullable=False)
    is_common = Column(Integer, default=False)
 
    query = db.session.query_property()

    def __init__(self, name = u'', sortname = u'', is_common = False):
        self.name = name
        self.sortname = sortname
        self.is_common = is_common
        db.session.add(self)

    def json(self):
        return { 
                 'id' : self.id, 
                 'name' : self.name,
                 'sortname' : self.sortname,
                 'is_common' : self.is_common
               }

    def __repr__(self):
        return "<DrinkName(%d,'%s')>" % (self.id, self.name)


########NEW FILE########
__FILENAME__ = option
# -*- coding: utf-8 -*-
from bartendro import db
from sqlalchemy.orm import mapper, relationship
from sqlalchemy import Table, Column, Integer, UnicodeText, Text, Index

class Option(db.Model):
    """
    Configuration options for Bartendro
    """

    __tablename__ = 'option'
    id = Column(Integer, primary_key=True)
    key = Column(UnicodeText, nullable=False)
    value = Column(UnicodeText)

    query = db.session.query_property()
    def __init__(self, key='', value=''):
        self.key = key
        self.value = value

    def __repr__(self):
        return "<Option('%s','%s'='%s')>" % (self.id, self.key, self.value)

Index('options_key_ndx', Option.key)

########NEW FILE########
__FILENAME__ = shot_log
# -*- coding: utf-8 -*-
from bartendro import db
from sqlalchemy.orm import mapper, relationship
from sqlalchemy import Table, Column, Integer, String, MetaData, Unicode, UnicodeText, UniqueConstraint, ForeignKey
from sqlalchemy.ext.declarative import declarative_base

class ShotLog(db.Model):
    """
    Keeps a record of shots we've dispensed. This should be in DrinkLog, but that requires a schema change. :(
    """

    __tablename__ = 'shot_log'
    id = Column(Integer, primary_key=True)
    booze_id = Column(Integer, ForeignKey('booze.id'), nullable=False)
    time = Column(Integer, nullable=False, default=0)
    size = Column(Integer, nullable=False, default=-1)
 
    query = db.session.query_property()

    def __init__(self, booze_id=-1, time=0, size=0):
        self.booze_id = booze_id
        self.time = time
        self.size = size
        db.session.add(self)

    def __repr__(self):
        return "<ShotLog(%d,'%s')>" % (self.id, self.booze_id)


########NEW FILE########
__FILENAME__ = version
# -*- coding: utf-8 -*-
from bartendro import db
from sqlalchemy.orm import mapper, relationship
from sqlalchemy import Table, Column, Integer
from sqlalchemy.ext.declarative import declarative_base

class DatabaseVersion(db.Model):
    """
    This table stores the version of the Bartendro database
    """

    __tablename__ = 'version'
    schema = Column(Integer, primary_key=True)

    query = db.session.query_property()
    def __init__(self, schema = 1):
        self.schema = schema

    def update(self, schema):
        self.schema = schema

    def __repr__(self):
        return "<Version(schema %d)>" % (self.schema)

########NEW FILE########
__FILENAME__ = options
# -*- coding: utf-8 -*-
import logging
from bartendro import app, db
from bartendro.model.option import Option
from bartendro.model.shot_log import ShotLog
from sqlalchemy.exc import OperationalError

log = logging.getLogger('bartendro')

bartendro_options = {
    u'use_liquid_level_sensors': False,
    u'must_login_to_dispense'  : False,
    u'login_name'              : u"bartendro",
    u'login_passwd'            : u"boozemeup",
    u'metric'                  : False,
    u'drink_size'              : 150,
    u'taster_size'             : 30,
    u'shot_size'               : 30,
    u'test_dispense_ml'        : 10,
    u'show_strength'           : True,
    u'show_size'               : True,
    u'show_taster'             : False,
    u'strength_steps'          : 2,
    u'use_shotbot_ui'          : False,
    u'show_feeling_lucky'      : False
}

class BadConfigOptionsError(Exception):
    pass

class Options(object):
    '''A simple placeholder for options'''

    def add(self, key, value):
        self.__attr__

def setup_options_table():
    '''Check to make sure the options table is present'''

    if not db.engine.dialect.has_table(db.engine.connect(), "option"):
        log.info("Creating options table")
        option = Option()
        option.__table__.create(db.engine)


    # Try and see if we have a legacy config.py kicking around. If so,
    # import the options and save them in the DB
    try:
        import config
    except ImportError:
        config = None

    # Figure out which, if any options are missing from the options table
    options = db.session.query(Option).all()
    opt_dict = {}
    for o in options:
        opt_dict[o.key] = o.value

    # Now populate missing keys from old config or defaults
    for opt in bartendro_options:
        if not opt in opt_dict:
            log.info("option %s is not in DB." % opt)
            try:
                value = getattr(config, opt)
                log.info("Get option from legacy: %s" % value)
            except AttributeError:
                value = bartendro_options[opt]
                log.info("Get option from defaults: %s" % value)

            log.info("Adding option '%s'" % opt)
            o = Option(opt, value)
            db.session.add(o)

    db.session.commit()

    # This should go someplace else, but not right this second
    if not db.engine.dialect.has_table(db.engine.connect(), "shot_log"):
        log.info("Creating shot_log table")
        shot_log = ShotLog()
        shot_log.__table__.create(db.engine)

def load_options():
    '''Load options from the db and make them into a nice an accessible modules'''

    setup_options_table()

    options = Options()
    for o in db.session.query(Option).all():
        try:
            if isinstance(bartendro_options[o.key], int):
               value = int(o.value)
            elif isinstance(bartendro_options[o.key], unicode):
               value = unicode(o.value)
            elif isinstance(bartendro_options[o.key], boolean):
               value = boolean(o.value)
            else:
                raise BadConfigOptionsError
        except KeyError:
            # Ignore options we don't understand
            pass

        setattr(options, o.key, value)

    if app.driver.count() == 1:
        setattr(options, "i_am_shotbot", True)
        setattr(options, "use_shotbot_ui", True)
    else:
        setattr(options, "i_am_shotbot", False)

    return options

########NEW FILE########
__FILENAME__ = pourcomplete
# -*- coding: utf-8 -*-
from time import sleep, time
from threading import Thread

class PourCompleteDelay(Thread):
    def __init__(self, mixer):
        Thread.__init__(self)
        self.mixer = mixer

    def run(self):
        sleep(5);
        self.mixer.driver.led_idle()

########NEW FILE########
__FILENAME__ = dispenser_select
#!/usr/bin/env python

import sys
import os
import logging
from time import sleep
from bartendro.error import I2CIOError

ROUTER_BUS              = 1
ROUTER_ADDRESS          = 4
ROUTER_SELECT_CMD_BEGIN = 0
ROUTER_CMD_SYNC_ON      = 251
ROUTER_CMD_SYNC_OFF     = 252
ROUTER_CMD_PING         = 253
ROUTER_CMD_COUNT        = 254
ROUTER_CMD_RESET        = 255

log = logging.getLogger('bartendro')

try:
    import smbus
    smbus_missing = 0
except ImportError, e:
    if e.message != 'No module named smbus':
        raise
    smbus_missing = 1

class DispenserSelect(object):
    '''This object interacts with the bartendro router controller to select dispensers'''

    def __init__(self, max_dispensers, software_only):
        self.software_only = software_only
        self.max_dispensers = max_dispensers
        self.router = None
        self.num_dispensers = 3
        self.selected = 255 

    def reset(self):
        if self.software_only: return
        self.router.write_byte(ROUTER_ADDRESS, ROUTER_CMD_RESET)
        sleep(.15)

    def select(self, dispenser):
        if self.software_only: return

        # NOTE: This code used to only send the select message if the dispenser changed.
        # but tracking which dispenser was last selected across many web server threads
        # is an extra pain I dont care to handle now. For now we'll just set the dispenser
        # for each packet we send.
        if dispenser < self.max_dispensers:
            self.selected = dispenser
            self.router.write_byte(ROUTER_ADDRESS, dispenser)
            sleep(.01)

    def sync(self, state):
        if self.software_only: return
        if (state):
            self.router.write_byte(ROUTER_ADDRESS, ROUTER_CMD_SYNC_ON)
        else:
            self.router.write_byte(ROUTER_ADDRESS, ROUTER_CMD_SYNC_OFF)

    def count(self):
        return self.num_dispensers

    def open(self):
        '''Open the i2c connection to the router'''

        if self.software_only: return

        if smbus_missing:
            log.error("You must install the smbus module!")
            sys.exit(-1)

        log.info("Opening I2C bus to router")
        try:
            self.router = smbus.SMBus(ROUTER_BUS)
        except IOError:
            raise I2CIOError
        log.info("Done.")

if __name__ == "__main__":
    ds = DispenserSelect(15, 0)
    ds.open()
    ds.reset()

########NEW FILE########
__FILENAME__ = driver
import sys
import os
import collections
import logging
from subprocess import call
from time import sleep, localtime, time
import serial
from struct import pack, unpack
import pack7
import dispenser_select
from bartendro.error import SerialIOError
import random

DISPENSER_DEFAULT_VERSION = 2
DISPENSER_DEFAULT_VERSION_SOFTWARE_ONLY = 3

BAUD_RATE       = 9600
DEFAULT_TIMEOUT = 2 # in seconds

MAX_DISPENSERS = 15
SHOT_TICKS     = 20

RAW_PACKET_SIZE      = 10
PACKET_SIZE          =  8

PACKET_ACK_OK               = 0
PACKET_CRC_FAIL             = 1
PACKET_ACK_TIMEOUT          = 2
PACKET_ACK_INVALID          = 3
PACKET_ACK_INVALID_HEADER   = 4
PACKET_ACK_HEADER_IN_PACKET = 5
PACKET_ACK_CRC_FAIL         = 6

PACKET_PING                   = 3
PACKET_SET_MOTOR_SPEED        = 4
PACKET_TICK_DISPENSE          = 5
PACKET_TIME_DISPENSE          = 6
PACKET_LED_OFF                = 7
PACKET_LED_IDLE               = 8
PACKET_LED_DISPENSE           = 9
PACKET_LED_DRINK_DONE         = 10
PACKET_IS_DISPENSING          = 11
PACKET_LIQUID_LEVEL           = 12
PACKET_UPDATE_LIQUID_LEVEL    = 13
PACKET_ID_CONFLICT            = 14
PACKET_LED_CLEAN              = 15
PACKET_SET_CS_THRESHOLD       = 16
PACKET_SAVED_TICK_COUNT       = 17
PACKET_RESET_SAVED_TICK_COUNT = 18
PACKET_GET_LIQUID_THRESHOLDS  = 19
PACKET_SET_LIQUID_THRESHOLDS  = 20
PACKET_FLUSH_SAVED_TICK_COUNT = 21
PACKET_TICK_SPEED_DISPENSE    = 22
PACKET_PATTERN_DEFINE         = 23
PACKET_PATTERN_ADD_SEGMENT    = 24
PACKET_PATTERN_FINISH         = 25
PACKET_SET_MOTOR_DIRECTION    = 26
PACKET_GET_VERSION            = 27
PACKET_COMM_TEST              = 0xFE

DEST_BROADCAST         = 0xFF

MOTOR_DIRECTION_FORWARD       = 1
MOTOR_DIRECTION_BACKWARD      = 0

LED_PATTERN_IDLE          = 0
LED_PATTERN_DISPENSE      = 1
LED_PATTERN_DRINK_DONE    = 2
LED_PATTERN_CLEAN         = 3
LED_PATTERN_CURRENT_SENSE = 4

MOTOR_DIRECTION_FORWARD         = 1
MOTOR_DIRECTION_BACKWARD        = 0

log = logging.getLogger('bartendro')

def crc16_update(crc, a):
    crc ^= a
    for i in xrange(0, 8):
        if crc & 1:
            crc = (crc >> 1) ^ 0xA001
        else:
            crc = (crc >> 1)
    return crc

class RouterDriver(object):
    '''This object interacts with the bartendro router controller.'''

    def __init__(self, device, software_only):
        self.device = device
        self.ser = None
        self.msg = ""
        self.ret = 0
        self.software_only = software_only
        self.dispenser_select = None
        self.dispenser_version = DISPENSER_DEFAULT_VERSION
        self.startup_log = ""
        self.debug_levels = [ 200, 180, 120 ]

        # dispenser_ids are the ids the dispensers have been assigned. These are logical ids 
        # used for dispenser communication.
        self.dispenser_ids = [255 for i in xrange(MAX_DISPENSERS)]

        # dispenser_ports are the ports the dispensers have been plugged into.
        self.dispenser_ports = [255 for i in xrange(MAX_DISPENSERS)]

        if software_only:
            self.num_dispensers = MAX_DISPENSERS
        else:
            self.num_dispensers = 0 

    def get_startup_log(self):
        return self.startup_log
    
    def get_dispenser_version(self):
        return self.dispenser_version

    def reset(self):
        """Reset the hardware. Do this if there is shit going wrong. All motors will be stopped
           and reset."""
        if self.software_only: return

        self.close()
        self.open()

    def count(self):
        return self.num_dispensers

    def set_timeout(self, timeout):
        self.ser.timeout = timeout

    def open(self):
        '''Open the serial connection to the router'''

        if self.software_only: return

        self._clear_startup_log()

        try:
            log.info("Opening %s" % self.device)
            self.ser = serial.Serial(self.device, 
                                     BAUD_RATE, 
                                     bytesize=serial.EIGHTBITS, 
                                     parity=serial.PARITY_NONE, 
                                     stopbits=serial.STOPBITS_ONE,
                                     timeout=.01)
        except serial.serialutil.SerialException, e:
            raise SerialIOError(e)

        log.info("Done.\n")

        import status_led
        self.status = status_led.StatusLED(self.software_only)
        self.status.set_color(0, 0, 1)

        self.dispenser_select = dispenser_select.DispenserSelect(MAX_DISPENSERS, self.software_only)
        self.dispenser_select.open()
        self.dispenser_select.reset()

        # This primes the communication line. 
        self.ser.write(chr(170) + chr(170) + chr(170))
        sleep(.001)

        log.info("Discovering dispensers")
        self.num_dispensers = 0
        for port in xrange(MAX_DISPENSERS):
            self._log_startup("port %d:" % port)
            self.dispenser_select.select(port)
            sleep(.01)
            while True:
                self.ser.flushInput()
                self.ser.write("???") 
                data = self.ser.read(3)
                ll = ""
                for ch in data:
                    ll += "%02X " % ord(ch)
                if len(data) == 3: 
                    if data[0] != data[1] or data[0] != data[2]:
                        self._log_startup("  %s -- inconsistent" % ll)
                        continue
                    id = ord(data[0])
                    self.dispenser_ids[self.num_dispensers] = id
                    self.dispenser_ports[self.num_dispensers] = port
                    self.num_dispensers += 1
                    self._log_startup("  %s -- Found dispenser with pump id %02X, index %d" % (ll, id, self.num_dispensers))
                    break
                elif len(data) > 1:
                    self._log_startup("  %s -- Did not receive 3 characters back. Trying again." % ll)
                    sleep(.5)
                else:
                    break

        self._select(0)
        self.set_timeout(DEFAULT_TIMEOUT)
        self.ser.write(chr(255));

        duplicate_ids = [x for x, y in collections.Counter(self.dispenser_ids).items() if y > 1]
        if len(duplicate_ids):
            for dup in duplicate_ids:
                if dup == 255: continue
                self._log_startup("ERROR: Dispenser id conflict!\n")
                sent = False
                for i, d in enumerate(self.dispenser_ids):
                    if d == dup: 
                        if not sent: 
                            self._send_packet8(i, PACKET_ID_CONFLICT, 0)
                            sent = True
                        self._log_startup("  dispenser %d has id %d\n" % (i, d))
                        self.dispenser_ids[i] = 255
                        self.num_dispensers -= 1

        self.dispenser_version = self.get_dispenser_version(0)
        if self.dispenser_version < 0:
            self.dispenser_version = DISPENSER_DEFAULT_VERSION 
        else:
            self.status.swap_blue_green()
        log.info("Detected dispensers version %d. (Only checked first dispenser)" % self.dispenser_version)

        self.led_idle()

    def close(self):
        if self.software_only: return
        self.ser.close()
        self.ser = None
        self.status = None
        self.dispenser_select = None

    def log(self, msg):
        return
        if self.software_only: return
        try:
            t = localtime()
            self.cl.write("%d-%d-%d %d:%02d %s" % (t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min, msg))
            self.cl.flush()
        except IOError:
            pass

    def make_shot(self):
        if self.software_only: return True
        self._send_packet32(0, PACKET_TICK_DISPENSE, 90)
        return True

    def ping(self, dispenser):
        if self.software_only: return True
        return self._send_packet32(dispenser, PACKET_PING, 0)

    def start(self, dispenser):
        if self.software_only: return True
        return self._send_packet8(dispenser, PACKET_SET_MOTOR_SPEED, 255, True)

    def set_motor_direction(self, dispenser, direction):
        if self.software_only: return True
        return self._send_packet8(dispenser, PACKET_SET_MOTOR_DIRECTION, direction)

    def stop(self, dispenser):
        if self.software_only: return True
        return self._send_packet8(dispenser, PACKET_SET_MOTOR_SPEED, 0)

    def dispense_time(self, dispenser, duration):
        if self.software_only: return True
        return self._send_packet32(dispenser, PACKET_TIME_DISPENSE, duration)

    def dispense_ticks(self, dispenser, ticks, speed=255):
        if self.software_only: return True
        return self._send_packet16(dispenser, PACKET_TICK_SPEED_DISPENSE, ticks, speed)

    def led_off(self):
        if self.software_only: return True
        self._sync(0)
        self._send_packet8(DEST_BROADCAST, PACKET_LED_OFF, 0)
        return True

    def led_idle(self):
        if self.software_only: return True
        self._sync(0)
        self._send_packet8(DEST_BROADCAST, PACKET_LED_IDLE, 0)
        sleep(.01)
        self._sync(1)
        return True

    def led_dispense(self):
        if self.software_only: return True
        self._sync(0)
        self._send_packet8(DEST_BROADCAST, PACKET_LED_DISPENSE, 0)
        sleep(.01)
        self._sync(1)
        return True

    def led_complete(self):
        if self.software_only: return True
        self._sync(0)
        self._send_packet8(DEST_BROADCAST, PACKET_LED_DRINK_DONE, 0)
        sleep(.01)
        self._sync(1)
        return True

    def led_clean(self):
        if self.software_only: return True
        self._sync(0)
        self._send_packet8(DEST_BROADCAST, PACKET_LED_CLEAN, 0)
        sleep(.01)
        self._sync(1)
        return True

    def led_error(self):
        if self.software_only: return True
        self._sync(0)
        self._send_packet8(DEST_BROADCAST, PACKET_LED_CLEAN, 0)
        sleep(.01)
        self._sync(1)
        return True

    def comm_test(self):
        self._sync(0)
        return self._send_packet8(0, PACKET_COMM_TEST, 0)

    def is_dispensing(self, dispenser):
        """
        Returns a tuple of (dispensing, is_over_current) 
        """

        if self.software_only: return (False, False)

        # Sometimes the motors can interfere with communications.
        # In such cases, assume the motor is still running and 
        # then assume the caller will again to see if it is still running
        self.set_timeout(.1)
        ret = self._send_packet8(dispenser, PACKET_IS_DISPENSING, 0)
        self.set_timeout(DEFAULT_TIMEOUT)
        if ret: 
            ack, value0, value1 = self._receive_packet8_2()
            if ack == PACKET_ACK_OK:
                return (value0, value1)
            if ack == PACKET_ACK_TIMEOUT:
                return (-1, -1)
        return (True, False)

    def update_liquid_levels(self):
        if self.software_only: return True
        return self._send_packet8(DEST_BROADCAST, PACKET_UPDATE_LIQUID_LEVEL, 0)

    def get_liquid_level(self, dispenser):
        if self.software_only: return 100
        if self._send_packet8(dispenser, PACKET_LIQUID_LEVEL, 0):
            ack, value, dummy = self._receive_packet16()
            if ack == PACKET_ACK_OK:
                # Returning a random value as below is really useful for testing. :)
                #self.debug_levels[dispenser] = max(self.debug_levels[dispenser] - 20, 50)
                #return self.debug_levels[dispenser]
                #return random.randint(50, 200)
                return value
        return -1

    def get_liquid_level_thresholds(self, dispenser):
        if self.software_only: return True
        if self._send_packet8(dispenser, PACKET_GET_LIQUID_THRESHOLDS, 0):
            ack, low, out = self._receive_packet16()
            if ack == PACKET_ACK_OK:
                return (low, out)
        return (-1, -1)
                
    def set_liquid_level_thresholds(self, dispenser, low, out):
        if self.software_only: return True
        return self._send_packet16(dispenser, PACKET_SET_LIQUID_THRESHOLDS, low, out)

    def set_motor_direction(self, dispenser, dir):
        if self.software_only: return True
        return self._send_packet8(dispenser, PACKET_SET_MOTOR_DIRECTION, dir)

    def get_dispenser_version(self, dispenser):
        if self.software_only: return DISPENSER_DEFAULT_VERSION_SOFTWARE_ONLY
        if self._send_packet8(dispenser, PACKET_GET_VERSION, 0):
            # set a short timeout, in case its a v2 dispenser
            self.set_timeout(.1)
            ack, ver, dummy = self._receive_packet16(True)
            self.set_timeout(DEFAULT_TIMEOUT)
            if ack == PACKET_ACK_OK:
                return ver
        return -1

    def set_status_color(self, red, green, blue):
        if self.software_only: return
        if not self.status: return
        self.status.set_color(red, green, blue)

    def get_saved_tick_count(self, dispenser):
        if self.software_only: return True
        if self._send_packet8(dispenser, PACKET_SAVED_TICK_COUNT, 0):
            ack, ticks, dummy = self._receive_packet16()
            if ack == PACKET_ACK_OK:
                return ticks
        return -1

    def flush_saved_tick_count(self):
        if self.software_only: return True
        return self._send_packet8(DEST_BROADCAST, PACKET_FLUSH_SAVED_TICK_COUNT, 0)

    def pattern_define(self, dispenser, pattern):
        if self.software_only: return True
        return self._send_packet8(dispenser, PACKET_PATTERN_DEFINE, pattern)

    def pattern_add_segment(self, dispenser, red, green, blue, steps):
        if self.software_only: return True
        return self._send_packet8(dispenser, PACKET_PATTERN_ADD_SEGMENT, red, green, blue, steps)

    def pattern_finish(self, dispenser):
        if self.software_only: return True
        return self._send_packet8(dispenser, PACKET_PATTERN_FINISH, 0)

    # -----------------------------------------------
    # Past this point we only have private functions. 
    # -----------------------------------------------

    def _sync(self, state):
        """Turn on/off the sync signal from the router. This signal is used to syncronize the LEDs"""

        if self.software_only: return
        self.dispenser_select.sync(state)

    def _select(self, dispenser):
        """Private function to select a dispenser."""

        if self.software_only: return True

        # If for broadcast, then ignore this select
        if dispenser == 255: return

        port = self.dispenser_ports[dispenser]
        self.dispenser_select.select(port)


    def _send_packet(self, dest, packet):
        if self.software_only: return True

        self._select(dest);
        self.ser.flushInput()
        self.ser.flushOutput()

        crc = 0
        for ch in packet:
            crc = crc16_update(crc, ord(ch))

        encoded = pack7.pack_7bit(packet + pack("<H", crc))
        if len(encoded) != RAW_PACKET_SIZE:
            log.error("send_packet: Encoded packet size is wrong: %d vs %s" % (len(encoded), RAW_PACKET_SIZE))
            return False

        try:
            t0 = time()
            written = self.ser.write(chr(0xFF) + chr(0xFF) + encoded)
            if written != RAW_PACKET_SIZE + 2:
                log.error("Send timeout")
                return False

            if dest == DEST_BROADCAST:
                return True

            ch = self.ser.read(1)
            t1 = time()
            log.debug("packet time: %f" % (t1 - t0))
            if len(ch) < 1:
                log.error("send packet: read timeout")
                return False
        except SerialException, err:
            log.error("SerialException: %s" % err);
            return False

        ack = ord(ch)
        if ack == PACKET_ACK_OK: 
            return True
        if ack == PACKET_CRC_FAIL: 
            log.error("send packet: packet ack crc fail")
            return False
        if ack == PACKET_ACK_TIMEOUT: 
            log.error("send_packet: ack timeout")
            return False
        if ack == PACKET_ACK_INVALID: 
            log.error("send_packet: dispenser received invalid packet")
            return False
        if ack == PACKET_ACK_INVALID_HEADER: 
            log.error("send_packet: dispenser received invalid header")
            return False
        if ack == PACKET_ACK_HEADER_IN_PACKET:
            log.error("send_packet: header in packet error")
            return False

        # if we get an invalid ack code, it might be ok. 
        log.error("send_packet: Invalid ACK code %d" % ord(ch))
        return False

    def _send_packet8(self, dest, type, val0, val1=0, val2=0, val3=0):
        if dest != DEST_BROADCAST: 
            dispenser_id = self.dispenser_ids[dest]
            if dispenser_id == 255: return False
        else:
            dispenser_id = dest

        return self._send_packet(dest, pack("BBBBBB", dispenser_id, type, val0, val1, val2, val3))

    def _send_packet16(self, dest, type, val0, val1):
        if dest != DEST_BROADCAST: 
            dispenser_id = self.dispenser_ids[dest]
            if dispenser_id == 255: return False
        else:
            dispenser_id = dest
        return self._send_packet(dest, pack("<BBHH", dispenser_id, type, val0, val1))

    def _send_packet32(self, dest, type, val):
        if dest != DEST_BROADCAST: 
            dispenser_id = self.dispenser_ids[dest]
            if dispenser_id == 255: return False
        else:
            dispenser_id = dest
        return self._send_packet(dest, pack("<BBI", dispenser_id, type, val))

    def _receive_packet(self, quiet = False):
        if self.software_only: return True

        header = 0
        while True:
            ch = self.ser.read(1)
            if len(ch) < 1:
                if not quiet:
                    log.error("receive packet: response timeout")
                return (PACKET_ACK_TIMEOUT, "")

            if (ord(ch) == 0xFF):
                header += 1
            else:
                header = 0

            if header == 2:
                break

        ack = PACKET_ACK_OK
        raw_packet = self.ser.read(RAW_PACKET_SIZE)
        if len(raw_packet) != RAW_PACKET_SIZE:
            if not quiet:
                log.error("receive packet: timeout")
            ack = PACKET_ACK_TIMEOUT

        if ack == PACKET_ACK_OK:
            packet = pack7.unpack_7bit(raw_packet)
            if len(packet) != PACKET_SIZE:
                ack = PACKET_ACK_INVALID
                if not quiet:
                    log.error("receive_packet: Unpacked length incorrect")

            if ack == PACKET_ACK_OK:
                received_crc = unpack("<H", packet[6:8])[0]
                packet = packet[0:6]

                crc = 0
                for ch in packet:
                    crc = crc16_update(crc, ord(ch))

                if received_crc != crc:
                    if not quiet:
                        log.error("receive_packet: CRC fail")
                    ack = PACKET_ACK_CRC_FAIL

        # Send the response back to the dispenser
        if self.ser.write(chr(ack)) != 1:
            if not quiet:
                log.error("receive_packet: Send ack timeout!")
            ack = PACKET_ACK_TIMEOUT

        if ack == PACKET_ACK_OK:
            return (ack, packet)
        else:
            return (ack, "")

    def _receive_packet8(self, quiet = False):
        ack, packet = self._receive_packet(quiet)
        if ack == PACKET_ACK_OK:
            data = unpack("BBBBBB", packet)
            return (ack, data[2])
        else:
            return (ack, 0)

    def _receive_packet8_2(self, quiet = False):
        ack, packet = self._receive_packet(quiet)
        if ack == PACKET_ACK_OK:
            data = unpack("BBBBBB", packet)
            return (ack, data[2], data[3])
        else:
            return (ack, 0, 0)

    def _receive_packet16(self, quiet = False):
        ack, packet = self._receive_packet(quiet)
        if ack == PACKET_ACK_OK:
            data = unpack("<BBHH", packet)
            return (ack, data[2], data[3])
        else:
            return (ack, 0, 0)

    def _clear_startup_log(self):
        self.startup_log = ""

    def _log_startup(self, txt):
        log.info(txt)
        self.startup_log += "%s\n" % txt

########NEW FILE########
__FILENAME__ = gpio
#!/usr/bin/env python

import sys
from time import sleep

class GPIO(object):
    def __init__(self, pin):
        self.pin = pin

    def setup(self):
        try:
            f = open("/sys/class/gpio/gpio%d/direction" % self.pin, "w")
        except IOError:
            return False
        f.write("high\n")
        f.close()

    def low(self):
        try:
            f = open("/sys/class/gpio/gpio%d/value" % self.pin, "w")
        except IOError:
            return False
        f.write("0\n")
        f.close()
        return True

    def high(self):
        try:
            f = open("/sys/class/gpio/gpio%d/value" % self.pin, "w")
        except IOError:
            return False
        f.write("1\n")
        f.close()
        return True

########NEW FILE########
__FILENAME__ = pack7
#!/usr/bin/env python

bits = [''.join(['01'[i&(1<<b)>0] for b in xrange(7,-1,-1)]) for i in xrange(256)]

def pack_7bit(data):
    buffer = 0
    bitcount = 0
    out = ""

    while True:
        if bitcount < 7:
            buffer <<= 8
            buffer |= ord(data[0])
            data = data[1:]
            bitcount += 8
        out += chr(buffer >> (bitcount - 7))
        buffer &= (1 << (bitcount - 7)) - 1
        bitcount -= 7

        if len(data) == 0: break

    out += chr(buffer << (7 - bitcount))
    return out

def unpack_7bit(data):
    buffer = 0
    bitcount = 0
    out = ""

    while True:
        if bitcount < 8:
            buffer <<= 7
            buffer |= ord(data[0])
            data = data[1:]
            bitcount += 7

        if bitcount >= 8:
            out += chr(buffer >> (bitcount - 8))
            buffer &= (1 << (bitcount - 8)) - 1
            bitcount -= 8

        if len(data) == 0: break

    return out


########NEW FILE########
__FILENAME__ = status_led
#!/usr/bin/env python

import sys
import logging
from time import sleep
try:
    import RPi.GPIO as gpio
    gpio_missing = 0
except ImportError, e:
    if e.message != 'No module named RPi.GPIO':
        raise
    gpio_missing = 1

log= logging.getLogger('bartendro')

class StatusLED(object):

    # pin definitions
    red = 18
    green = 16
    blue = 22

    def __init__(self, software_only):
        self.software_only = software_only
        if self.software_only: return

        if gpio_missing:
            loglogerror("You must install the RPi.GPIO module")
            sys.exit(-1)

        # select the method by which we want to identify GPIO pins
        gpio.setmode(gpio.BOARD)

        # set our gpio pins to OUTPUT
        gpio.setup(self.red, gpio.OUT)
        gpio.setup(self.green, gpio.OUT)
        gpio.setup(self.blue, gpio.OUT)

    def swap_blue_green(self):
        self.green = 22
        self.blue = 16

    def set_color(self, red, green, blue):
        if self.software_only: return
        if red:
            gpio.output(self.red, gpio.HIGH)
        else:
            gpio.output(self.red, gpio.LOW)
            
        if green:
            gpio.output(self.green, gpio.HIGH)
        else:
            gpio.output(self.green, gpio.LOW)

        if blue:
            gpio.output(self.blue, gpio.HIGH)
        else:
            gpio.output(self.blue, gpio.LOW)

########NEW FILE########
__FILENAME__ = booze
# -*- coding: utf-8 -*-
from bartendro import app, db
from sqlalchemy import func, asc
from flask import Flask, request, redirect, render_template
from flask.ext.login import login_required
from bartendro.model.drink import Drink
from bartendro.model.booze import Booze
from bartendro.model.booze_group import BoozeGroup
from bartendro.form.booze import BoozeForm

@app.route('/admin/booze')
@login_required
def admin_booze():
    form = BoozeForm(request.form)
    boozes = Booze.query.order_by(asc(func.lower(Booze.name)))
    return render_template("admin/booze", options=app.options, boozes=boozes, form=form, title="Booze")

@app.route('/admin/booze/edit/<id>')
@login_required
def admin_booze_edit(id):
    saved = int(request.args.get('saved', "0"))
    booze = Booze.query.filter_by(id=int(id)).first()
    form = BoozeForm(obj=booze)
    boozes = Booze.query.order_by(asc(func.lower(Booze.name)))
    return render_template("admin/booze", options=app.options, booze=booze, boozes=boozes, form=form, title="Booze", saved=saved)

@app.route('/admin/booze/save', methods=['POST'])
@login_required
def admin_booze_save():

    cancel = request.form.get("cancel")
    if cancel: return redirect('/admin/booze')

    form = BoozeForm(request.form)
    if request.method == 'POST' and form.validate():
        id = int(request.form.get("id") or '0')
        if id:
            booze = Booze.query.filter_by(id=int(id)).first()
            booze.update(form.data)
        else:
            booze = Booze(data=form.data)
            db.session.add(booze)

        db.session.commit()
        mc = app.mc
        mc.delete("top_drinks")
        mc.delete("other_drinks")
        mc.delete("available_drink_list")
        return redirect('/admin/booze/edit/%d?saved=1' % booze.id)

    boozes = Booze.query.order_by(asc(func.lower(Booze.name)))
    return render_template("admin/booze", options=app.options, boozes=boozes, form=form, title="")

########NEW FILE########
__FILENAME__ = debug
# -*- coding: utf-8 -*-
import time
from bartendro import app, db
from flask import Flask, request, render_template
from flask.ext.login import login_required

LOG_LINES_TO_SHOW = 1000

@app.route('/admin/debug')
@login_required
def debug_index():

    startup_log = app.driver.get_startup_log()
    try:
        b_log = open("logs/bartendro.log", "r")
        lines = b_log.readlines()
        b_log.close()
        lines = lines[-LOG_LINES_TO_SHOW:]
        bartendro_log = "".join(lines)
        print bartendro_log
    except IOError, e:
        print "file open fail"
        bartendro_log = "%s" % e 

    return render_template("admin/debug", options=app.options, 
                                          title="Debug bartendro", 
                                          startup_log=startup_log,
                                          bartendro_log=bartendro_log)

########NEW FILE########
__FILENAME__ = dispenser
# -*- coding: utf-8 -*-
from sqlalchemy import func, asc
import memcache
from bartendro import app, db
from flask import Flask, request, redirect, render_template
from flask.ext.login import login_required
from wtforms import Form, SelectField, IntegerField, validators
from bartendro.model.drink import Drink
from bartendro.model.booze import Booze
from bartendro.model.dispenser import Dispenser
from bartendro.form.dispenser import DispenserForm
from bartendro.mixer import CALIBRATE_ML
from operator import itemgetter
from bartendro import fsm
from bartendro.mixer import LL_OK

@app.route('/admin')
@login_required
def dispenser():
    driver = app.driver
    count = driver.count()

    saved = int(request.args.get('saved', "0"))
    updated = int(request.args.get('updated', "0"))

    class F(DispenserForm):
        pass

    dispensers = db.session.query(Dispenser).order_by(Dispenser.id).all()
    boozes = db.session.query(Booze).order_by(Booze.id).all()
    booze_list = [(b.id, b.name) for b in boozes]
    sorted_booze_list = sorted(booze_list, key=itemgetter(1))

    if app.options.use_liquid_level_sensors:
        states = [dispenser.out for dispenser in dispensers]
    else:
        states = [LL_OK for dispenser in dispensers]

    kwargs = {}
    fields = []
    for i in xrange(1, 17):
        dis = "dispenser%d" % i
        actual = "actual%d" % i
        setattr(F, dis, SelectField("%d" % i, choices=sorted_booze_list)) 
        setattr(F, actual, IntegerField(actual, [validators.NumberRange(min=1, max=100)]))
        kwargs[dis] = "1" # string of selected booze
        fields.append((dis, actual))

    form = F(**kwargs)
    for i, dispenser in enumerate(dispensers):
        form["dispenser%d" % (i + 1)].data = "%d" % booze_list[dispenser.booze_id - 1][0]
        form["actual%d" % (i + 1)].data = dispenser.actual

    bstate = app.globals.get_state()
    error = False
    if bstate == fsm.STATE_START:
        state = "Bartendro is starting up."
    elif bstate == fsm.STATE_READY:
        state = "Bartendro is ready!"
    elif bstate == fsm.STATE_LOW:
        state = "Bartendro is ready, but one or more boozes is low!"
    elif bstate == fsm.STATE_OUT:
        state = "Bartendro is ready, but one or more boozes is out!"
    elif bstate == fsm.STATE_HARD_OUT:
        state = "Bartendro cannot make any drinks from the available booze!"
    elif bstate == fsm.STATE_ERROR:
        state = "Bartendro is out of commission. Please reset Bartendro!"
        error = True
    else:
        state = "Bartendro is in bad state: %d" % bstate

    avail_drinks = app.mixer.get_available_drink_list()
    return render_template("admin/dispenser", 
                           title="Dispensers",
                           calibrate_ml=CALIBRATE_ML, 
                           form=form, count=count, 
                           fields=fields, 
                           saved=saved,
                           state=state,
                           error=error,
                           updated=updated,
                           num_drinks=len(avail_drinks),
                           options=app.options,
                           dispenser_version=driver.dispenser_version,
                           states=states)

@app.route('/admin/save', methods=['POST'])
@login_required
def save():
    cancel = request.form.get("cancel")
    if cancel: return redirect('/admin/dispenser')

    form = DispenserForm(request.form)
    if request.method == 'POST' and form.validate():
        dispensers = db.session.query(Dispenser).order_by(Dispenser.id).all()
        for dispenser in dispensers:
            try:
                dispenser.booze_id = request.form['dispenser%d' % dispenser.id]
                #dispenser.actual = request.form['actual%d' % dispenser.id]
            except KeyError:
                continue
        db.session.commit()

    app.mixer.check_levels()
    return redirect('/admin?saved=1')

########NEW FILE########
__FILENAME__ = drink
# -*- coding: utf-8 -*-
from sqlalchemy import func, asc
from operator import itemgetter
from bartendro import app, db
from flask import Flask, request, redirect, render_template
from flask.ext.login import login_required
from bartendro.model.drink import Drink
from bartendro.model.booze import Booze
from bartendro.model.dispenser import Dispenser
from bartendro.model.drink_booze import DrinkBooze
from bartendro.model.drink_name import DrinkName

@app.route('/admin/drink')
@login_required
def admin_drink_new():
    drinks = db.session.query(Drink).join(DrinkName).filter(Drink.name_id == DrinkName.id) \
                                 .order_by(asc(func.lower(DrinkName.name))).all()

    boozes = db.session.query(Booze).order_by(asc(func.lower(Booze.name))).all()
    booze_list = [(b.id, b.name) for b in boozes] 
    dispensers = db.session.query(Dispenser).order_by(Dispenser.id).all()
    return render_template("admin/drink", options=app.options, 
                                          title="Drinks",
                                          booze_list=booze_list,
                                          drinks=drinks,
                                          dispensers=dispensers,
                                          count=app.driver.count())

########NEW FILE########
__FILENAME__ = liquidlevel
# -*- coding: utf-8 -*-
from bartendro import app, db
from flask import Flask, request, render_template
from flask.ext.login import login_required

@app.route('/admin/liquidlevel')
@login_required
def admin_liquidlevel():
    driver = app.driver
    count = driver.count()
    thresholds = []
    for disp in xrange(count):
        low, out = driver.get_liquid_level_thresholds(disp)
        thresholds.append((low, out))

    return render_template("admin/liquidlevel", options=app.options, 
                                                count=count, 
                                                title="Liquid level calibration",
                                                thresholds=thresholds)

########NEW FILE########
__FILENAME__ = options
# -*- coding: utf-8 -*-
import socket
import fcntl
import struct
import time
import os
from bartendro import app
from flask import Flask, request, render_template, Response
from werkzeug.exceptions import Unauthorized
from flask.ext.login import login_required
from bartendro.model.version import DatabaseVersion

def get_ip_address_from_interface(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        return socket.inet_ntoa(fcntl.ioctl(s.fileno(), 0x8915,  
                                struct.pack('256s', ifname[:15]))[20:24])
    except IOError:
        return "[none]"

@app.route('/admin/options')
@login_required
def admin_options():
    ver = DatabaseVersion.query.one()
    recover = not request.remote_addr.startswith("10.0.0")

    wlan0 = get_ip_address_from_interface("wlan0")
    eth0 = get_ip_address_from_interface("eth0")

    return render_template("admin/options", 
                           options=app.options,
                           show_passwd_recovery=recover,
                           title="Options", 
                           eth0=eth0,
                           wlan0=wlan0,
                           version = app.version,
                           schema = ver.schema)

@app.route('/admin/lost-passwd')
def admin_lost_passwd():
    if request.remote_addr.startswith("10.0.0"):
        raise Unauthorized

    return render_template("admin/lost-passwd", 
                           options=app.options)

@app.route('/admin/upload')
@login_required
def admin_upload_db():
    return render_template("admin/upload", 
                           title="Upload database",
                           options=app.options)

########NEW FILE########
__FILENAME__ = report
# -*- coding: utf-8 -*-
import time
from bartendro import app, db
from flask import Flask, request, render_template
from flask.ext.login import login_required
from bartendro.model.drink import Drink
from bartendro.model.booze import Booze
from bartendro.model.booze_group import BoozeGroup
from bartendro.form.booze import BoozeForm

@app.route('/admin/report')
@login_required
def report_index():
    return render_template("admin/report", options=app.options, title="Top drinks report")

@app.route('/admin/report/<begin>/<end>')
@login_required
def report_view(begin, end):
    try:
        begindate = int(time.mktime(time.strptime(begin, "%Y-%m-%d %H:%M")))
    except ValueError:
        try:
            begindate = int(time.mktime(time.strptime(begin, "%Y-%m-%d")))
        except ValueError:
            return render_template("admin/report", options=app.options, error="Invalid begin date")

    try:
        enddate = int(time.mktime(time.strptime(end, "%Y-%m-%d %H:%M")))
    except ValueError:
        try:
            enddate = int(time.mktime(time.strptime(end, "%Y-%m-%d")))
        except ValueError:
            return render_template("admin/report", options=app.options, error="Invalid end date")

    total_number = db.session.query("number")\
                 .from_statement("""SELECT count(*) as number
                                      FROM drink_log 
                                     WHERE drink_log.time >= :begin 
                                       AND drink_log.time <= :end""")\
                 .params(begin=begindate, end=enddate).first()

    total_volume = db.session.query("volume")\
                 .from_statement("""SELECT sum(drink_log.size) as volume 
                                      FROM drink_log 
                                     WHERE drink_log.time >= :begin 
                                       AND drink_log.time <= :end""")\
                 .params(begin=begindate, end=enddate).first()

    top_drinks = db.session.query("name", "number", "volume")\
                 .from_statement("""SELECT drink_name.name,
                                           count(drink_log.drink_id) AS number, 
                                           sum(drink_log.size) AS volume 
                                      FROM drink_log, drink_name 
                                     WHERE drink_log.drink_id = drink_name.id 
                                       AND drink_log.time >= :begin AND drink_log.time <= :end 
                                  GROUP BY drink_name.name 
                                  ORDER BY count(drink_log.drink_id) desc;""")\
                 .params(begin=begindate, end=enddate).all()

    return render_template("admin/report", options=app.options,
                                           top_drinks = top_drinks, 
                                           title="Top drinks report",
                                           total_number=total_number[0],
                                           total_volume=total_volume[0],
                                           begin=begin, 
                                           end=end)

########NEW FILE########
__FILENAME__ = user
# -*- coding: utf-8 -*-
from bartendro import app, db, login_manager
from bartendro.form.login import LoginForm
from flask import Flask, request, render_template, flash, redirect, url_for
from flask.ext.login import login_required, login_user, logout_user

class User(object):
    id = 0
    username = ""

    def __init__(self, username):
        self.username = username

    def is_authenticated(self):
        return self.username != ""

    def is_active(self):
        return True

    def is_anonymous(self):
        return self.username == ""

    def get_id(self):
        return self.username

    def __repr__(self):
        return '<User %d>' % self.username

@login_manager.user_loader
def load_user(userid):
    return User(userid)

@app.route("/admin/login", methods=["GET", "POST"])
def login():
    form = LoginForm(request.form)
    if request.method == 'POST' and form.validate():
        user = request.form.get("user" or '')
        password = request.form.get("password" or '')
        if (user == app.options.login_name and password == app.options.login_passwd):
            login_user(User(user))
            return redirect(request.args.get("next") or url_for("dispenser"))
        return render_template("/admin/login", options=app.options, form=form, fail=1)
    return render_template("/admin/login", options=app.options, form=form, fail=0)

@app.route("/admin/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))

########NEW FILE########
__FILENAME__ = drink
# -*- coding: utf-8 -*-
from bartendro import app, db
from flask import Flask, request, render_template
from bartendro.model.drink import Drink
from bartendro.model.drink_booze import DrinkBooze
from bartendro.model.custom_drink import CustomDrink
from bartendro.model.booze import Booze, booze_types
from bartendro.model.booze import BOOZE_TYPE_UNKNOWN, BOOZE_TYPE_ALCOHOL, BOOZE_TYPE_TART, BOOZE_TYPE_SWEET
from bartendro.model.booze_group import BoozeGroup
from bartendro.model.booze_group_booze import BoozeGroupBooze
from bartendro.model.drink_name import DrinkName
from bartendro.model.dispenser import Dispenser
from bartendro import constant 

@app.route('/drink/<int:id>')
def normal_drink(id):
    return drink(id, 0)

@app.route('/drink/<int:id>/go')
def lucky_drink(id):
    return drink(id, 1)

def drink(id, go):
    """If go is True, tell the web page to pour the drink right away. No dallying!"""

    # can we make this drink??
    can_make = id in app.mixer.get_available_drink_list()

    drink = db.session.query(Drink) \
                          .filter(Drink.id == id) \
                          .first() 

    boozes = db.session.query(Booze) \
                          .join(DrinkBooze.booze) \
                          .filter(DrinkBooze.drink_id == drink.id)

    custom_drink = db.session.query(CustomDrink) \
                          .filter(drink.id == CustomDrink.drink_id) \
                          .first()
    drink.process_ingredients()

    has_non_alcohol = False
    has_alcohol = False
    has_sweet = False
    has_tart = False
    show_sobriety = 0 #drink.id == 46
    for booze in boozes:
        if booze.type == BOOZE_TYPE_ALCOHOL: 
            has_alcohol = True
        else:
            has_non_alcohol = True
        if booze.type == BOOZE_TYPE_SWEET: has_sweet = True
        if booze.type == BOOZE_TYPE_TART: has_tart = True

    show_sweet_tart = has_sweet and has_tart
    show_strength = has_alcohol and has_non_alcohol

    if not custom_drink:
        return render_template("drink/index", 
                               drink=drink, 
                               options=app.options,
                               title=drink.name.name,
                               is_custom=0,
                               show_sweet_tart=show_sweet_tart,
                               show_sobriety=show_sobriety,
                               can_change_strength=show_strength,
                               go=go,
                               can_make=can_make)

    dispensers = db.session.query(Dispenser).all()
    disp_boozes = {}
    for dispenser in dispensers:
        disp_boozes[dispenser.booze_id] = 1

    booze_group = db.session.query(BoozeGroup) \
                          .join(DrinkBooze, DrinkBooze.booze_id == BoozeGroup.abstract_booze_id) \
                          .join(BoozeGroupBooze) \
                          .filter(Drink.id == id) \
                          .first()

    filtered = []
    for bgb in booze_group.booze_group_boozes:
        try:
            dummy = disp_boozes[bgb.booze_id]
            filtered.append(bgb)
        except KeyError:
            pass

    booze_group.booze_group_boozes = sorted(filtered, key=lambda booze: booze.sequence ) 
    return render_template("drink/index", 
                           drink=drink, 
                           options=app.options,
                           title=drink.name.name,
                           is_custom=1,
                           custom_drink=drink.custom_drink[0],
                           booze_group=booze_group,
                           show_sweet_tart=show_sweet_tart,
                           show_sobriety=show_sobriety,
                           can_change_strength=show_strength,
                           go=go,
                           can_make=can_make)

@app.route('/drink/sobriety')
def drink_sobriety():
    return render_template("drink/sobriety")

########NEW FILE########
__FILENAME__ = root
# -*- coding: utf-8 -*-
import memcache
import random
from sqlalchemy import func, asc
from sqlalchemy.exc import OperationalError
from bartendro import app, db
from flask import Flask, request, render_template, redirect
from bartendro.model.dispenser import Dispenser
from bartendro.model.drink import Drink
from bartendro.model.drink_name import DrinkName
from bartendro import fsm
from bartendro.mixer import LL_LOW, LL_OK

def process_ingredients(drinks):
    for drink in drinks:
        drink.process_ingredients()

def filter_drink_list(can_make_dict, drinks):
    filtered = []
    for drink in drinks:
        try:
            foo =can_make_dict[drink.id]
            filtered.append(drink)
        except KeyError:
            pass
    return filtered

@app.route('/')
def index():
    if app.globals.get_state() == fsm.STATE_ERROR:
        return render_template("index", 
                               options=app.options, 
                               top_drinks=[], 
                               other_drinks=[],
                               error_message="Bartendro is in trouble!<br/><br/>I need some attention! Please find my master, so they can make me feel better.",
                               title="Bartendro error")

    try:
        can_make = app.mixer.get_available_drink_list()
    except OperationalError:
        return render_template("index", 
                               options=app.options, 
                               top_drinks=[], 
                               other_drinks=[],
                               error_message="Bartendro database errror.<br/><br/>There doesn't seem to be a valid database installed.",
                               title="Bartendro error")

    can_make_dict = {}
    for drink in can_make:
        can_make_dict[drink] = 1

    top_drinks = db.session.query(Drink) \
                        .join(DrinkName) \
                        .filter(Drink.name_id == DrinkName.id)  \
                        .filter(Drink.popular == 1)  \
                        .filter(Drink.available == 1)  \
                        .order_by(asc(func.lower(DrinkName.name))).all() 

    top_drinks = filter_drink_list(can_make_dict, top_drinks)
    process_ingredients(top_drinks)

    other_drinks = db.session.query(Drink) \
                        .join(DrinkName) \
                        .filter(Drink.name_id == DrinkName.id)  \
                        .filter(Drink.popular == 0)  \
                        .filter(Drink.available == 1)  \
                        .order_by(asc(func.lower(DrinkName.name))).all() 
    other_drinks = filter_drink_list(can_make_dict, other_drinks)
    process_ingredients(other_drinks)

    print "%d, %d" % (len(top_drinks), len(other_drinks))

    if (not len(top_drinks) and not len(other_drinks)) or app.globals.get_state() == fsm.STATE_HARD_OUT:
        return render_template("index", 
                               options=app.options, 
                               top_drinks=[], 
                               other_drinks=[],
                               error_message="Drinks can't be made with the available boozes.<br/><br/>I need some attention! Please find my master, so they can make me feel better.",
                               title="Bartendro error")
            
    if app.options.show_feeling_lucky:
        lucky = Drink("<em>Make sure there is a cup under the spout, the drink will pour immediately!</em>")
        lucky.name = DrinkName("I'm feeling lucky!")
        lucky.id = can_make[int(random.randint(0, len(can_make) - 1))]
        lucky.set_lucky(True)
        lucky.set_ingredients_text("Pour a random drink now")
        top_drinks.insert(0, lucky)

    return render_template("index", 
                           options=app.options, 
                           top_drinks=top_drinks, 
                           other_drinks=other_drinks,
                           title="Bartendro")

@app.route('/shots')
def shots():

    if not app.options.use_shotbot_ui:
        return redirect("/")

    if app.globals.get_state() == fsm.STATE_ERROR:
        return render_template("shots", 
                               num_shots_ready=0,
                               options=app.options, 
                               error_message="Bartendro is in trouble!<br/><br/>I need some attention! Please find my master, so they can make me feel better.",
                               title="Bartendro error")

    dispensers = db.session.query(Dispenser).all()
    dispensers = dispensers[:app.driver.count()]

    shots = []
    for disp in dispensers:
        if disp.out == LL_OK or disp.out == LL_LOW or not app.options.use_liquid_level_sensors:
            shots.append(disp.booze)

    if len(shots) == 0:
        return render_template("shots", 
                               num_shots_ready=0,
                               options=app.options, 
                               error_message="Bartendro is out of all boozes. Oh no!<br/><br/>I need some attention! Please find my master, so they can make me feel better.",
                               title="Bartendro error")

    return render_template("shots", 
                           num_shots_ready= len(shots),
                           options=app.options, 
                           shots=shots, 
                           title="Shots")

########NEW FILE########
__FILENAME__ = trending
# -*- coding: utf-8 -*-
import time
from bartendro import app, db
from sqlalchemy import desc
from flask import Flask, request, render_template
from flask.ext.login import login_required
from bartendro.model.drink import Drink
from bartendro.model.drink_log import DrinkLog
from bartendro.model.booze import Booze
from bartendro.model.booze_group import BoozeGroup
from bartendro.form.booze import BoozeForm

DEFAULT_TIME = 12
display_info = {
    12 : 'Drinks poured in the last 12 hours.',
    72 : 'Drinks poured in the last 3 days.',
    168 : 'Drinks poured in the last week.',
    0 : 'All drinks ever poured'
}

@app.route('/trending')
def trending_drinks():
    return trending_drinks_detail(DEFAULT_TIME)

@app.route('/trending/<int:hours>')
def trending_drinks_detail(hours):

    title = "Trending drinks"
    log = db.session.query(DrinkLog).order_by(desc(DrinkLog.time)).first() or 0
    if log:
        if not log.time:
            enddate = int(time.time())
        else:
            enddate = log.time
    
        try:
            txt = display_info[hours]
        except IndexError:
            txt = "Drinks poured in the last %d hours" % hours

        # if a number of hours is 0, then show for "all time"
        if hours:
            begindate = enddate - (hours * 60 * 60)
        else:
            begindate = 0
    else:
	begindate = 0
        enddate = 0
        txt = ""

    total_number = db.session.query("number")\
                 .from_statement("""SELECT count(*) as number
                                      FROM drink_log 
                                     WHERE drink_log.time >= :begin 
                                       AND drink_log.time <= :end""")\
                 .params(begin=begindate, end=enddate).first()

    total_volume = db.session.query("volume")\
                 .from_statement("""SELECT sum(drink_log.size) as volume 
                                      FROM drink_log 
                                     WHERE drink_log.time >= :begin 
                                       AND drink_log.time <= :end""")\
                 .params(begin=begindate, end=enddate).first()

    top_drinks = db.session.query("id", "name", "number", "volume")\
                 .from_statement("""SELECT drink.id, 
                                           drink_name.name,
                                           count(drink_log.drink_id) AS number, 
                                           sum(drink_log.size) AS volume 
                                      FROM drink_log, drink_name, drink 
                                     WHERE drink_log.drink_id = drink_name.id 
                                       AND drink_name.id = drink.id
                                       AND drink_log.time >= :begin AND drink_log.time <= :end 
                                  GROUP BY drink_name.name 
                                  ORDER BY count(drink_log.drink_id) desc;""")\
                 .params(begin=begindate, end=enddate).all()

    return render_template("trending", top_drinks = top_drinks, options=app.options,
                                       title="Trending drinks",
                                       txt=txt,
                                       total_number=total_number[0],
                                       total_volume=total_volume[0],
                                       hours=hours)

########NEW FILE########
__FILENAME__ = booze
# -*- coding: utf-8 -*-
from bartendro import app, db
from flask import Flask, request, jsonify
from bartendro.model.drink import Drink
from bartendro.model.booze import Booze
from bartendro.form.booze import BoozeForm

@app.route('/ws/booze/match/<str>')
def ws_booze(request, str):
    str = str + "%%"
    boozes = db.session.query("id", "name").from_statement("SELECT id, name FROM booze WHERE name LIKE :s").params(s=str).all()
    return jsonify(boozes)

########NEW FILE########
__FILENAME__ = dispenser
# -*- coding: utf-8 -*-
import logging
from time import sleep
from werkzeug.exceptions import ServiceUnavailable
from bartendro import app, db, mixer
from flask import Flask, request
from flask.ext.login import current_user
from bartendro.model.drink import Drink
from bartendro.model.booze import Booze
from bartendro.model.dispenser import Dispenser
from bartendro.form.booze import BoozeForm
from bartendro import fsm
from bartendro.error import BartendroBusyError, BartendroBrokenError, BartendroCantPourError, BartendroCurrentSenseError
from bartendro.router.driver import MOTOR_DIRECTION_FORWARD, MOTOR_DIRECTION_BACKWARD

log = logging.getLogger('bartendro')


@app.route('/ws/dispenser/<int:disp>/on')
def ws_dispenser_on(disp):
    if app.options.must_login_to_dispense and not current_user.is_authenticated():
        return "login required"

    return run_dispenser(disp, True)

@app.route('/ws/dispenser/<int:disp>/on/reverse')
def ws_dispenser_reverse(disp):
    if app.options.must_login_to_dispense and not current_user.is_authenticated():
        return "login required"

    return run_dispenser(disp, False)

def run_dispenser(disp, forward):
    if forward:
        app.driver.set_motor_direction(disp - 1, MOTOR_DIRECTION_FORWARD)
    else:
        app.driver.set_motor_direction(disp - 1, MOTOR_DIRECTION_BACKWARD)

    err = ""
    if not app.driver.start(disp - 1):
        err = "Failed to start dispenser %d" % disp
        log.error(err)

    return err

@app.route('/ws/dispenser/<int:disp>/off')
def ws_dispenser_off(disp):
    if app.options.must_login_to_dispense and not current_user.is_authenticated():
        return "login required"

    err = ""
    if not app.driver.stop(disp - 1):
        err = "Failed to stop dispenser %d" % disp
        log.error(err)

    app.driver.set_motor_direction(disp, MOTOR_DIRECTION_FORWARD) 
        
    return err

@app.route('/ws/dispenser/<int:disp>/test')
def ws_dispenser_test(disp):
    if app.options.must_login_to_dispense and not current_user.is_authenticated():
        return "login required"

    if app.globals.get_state() == fsm.STATE_ERROR:
        return "error state"

    dispenser = db.session.query(Dispenser).filter_by(id=disp).first()
    if not dispenser:
        return "Cannot test dispenser. Incorrect dispenser."

    try:
        app.mixer.dispense_ml(dispenser, app.options.test_dispense_ml)
    except BartendroBrokenError:
        raise InternalServerError

    return ""

@app.route('/ws/clean')
def ws_dispenser_clean():
    if app.options.must_login_to_dispense and not current_user.is_authenticated():
        return "login required"

    if app.globals.get_state() == fsm.STATE_ERROR:
        return "error state"

    try:
        app.mixer.clean()
    except BartendroCantPourError, err:
        raise BadRequest(err)
    except BartendroBrokenError, err:
        raise InternalServerError(err)
    except BartendroBusyError, err:
        raise ServiceUnavailable(err)

    return ""

@app.route('/ws/clean/right')
def ws_dispenser_clean_right():
    if app.options.must_login_to_dispense and not current_user.is_authenticated():
        return "login required"

    if app.globals.get_state() == fsm.STATE_ERROR:
        return "error state"

    try:
        app.mixer.clean_right()
    except BartendroCantPourError, err:
        raise BadRequest(err)
    except BartendroBrokenError, err:
        raise InternalServerError(err)
    except BartendroBusyError, err:
        raise ServiceUnavailable(err)
    return ""

@app.route('/ws/clean/left')
def ws_dispenser_clean_left():
    if app.options.must_login_to_dispense and not current_user.is_authenticated():
        return "login required"

    if app.globals.get_state() == fsm.STATE_ERROR:
        return "error state"

    try:
        app.mixer.clean_left()
    except BartendroCantPourError, err:
        raise BadRequest(err)
    except BartendroBrokenError, err:
        raise InternalServerError(err)
    except BartendroBusyError, err:
        raise ServiceUnavailable(err)

    return ""

########NEW FILE########
__FILENAME__ = drink
# -*- coding: utf-8 -*-
import json
from time import sleep
from operator import itemgetter
from bartendro import app, db, mixer
from flask import Flask, request
from flask.ext.login import login_required, current_user
from werkzeug.exceptions import ServiceUnavailable, BadRequest, InternalServerError
from bartendro.model.drink import Drink
from bartendro.model.drink_name import DrinkName
from bartendro.model.booze import Booze
from bartendro.model.drink_booze import DrinkBooze
from bartendro.model.dispenser import Dispenser
from bartendro.error import BartendroBusyError, BartendroBrokenError, BartendroCantPourError, BartendroCurrentSenseError

def ws_make_drink(drink_id):
    recipe = {}
    for arg in request.args:
        disp = int(arg[5:])
        recipe[disp] = int(request.args.get(arg))

    drink = Drink.query.filter_by(id=int(drink_id)).first()
    try:
        app.mixer.make_drink(drink, recipe)
    except mixer.BartendroCantPourError, err:
        raise BadRequest(err)
    except mixer.BartendroBrokenError, err:
        raise InternalServerError(err)
    except mixer.BartendroBusyError, err:
        raise ServiceUnavailable(err)

    return "ok\n"

@app.route('/ws/drink/<int:drink>')
def ws_drink(drink):
    drink_mixer = app.mixer
    if app.options.must_login_to_dispense and not current_user.is_authenticated():
        return "login required"

    return ws_make_drink(drink)

@app.route('/ws/drink/custom')
def ws_custom_drink():
    if app.options.must_login_to_dispense and not current_user.is_authenticated():
        return "login required"

    return ws_make_drink(0)

@app.route('/ws/drink/<int:drink>/available/<int:state>')
def ws_drink_available(drink, state):
    if not drink:
        db.session.query(Drink).update({'available' : state})
    else:
        db.session.query(Drink).filter(Drink.id==drink).update({'available' : state})
    db.session.flush()
    db.session.commit()
    return "ok\n"

@app.route('/ws/shots/<int:booze_id>')
def ws_shots(booze_id):
    if app.options.must_login_to_dispense and not current_user.is_authenticated():
        return "login required"

    dispensers = db.session.query(Dispenser).all()
    dispenser = None
    for d in dispensers:
        if d.booze.id == booze_id:
            dispenser = d

    if not dispenser:
        return "this booze is not available"

    try:
        app.mixer.dispense_shot(dispenser, app.options.shot_size)
    except mixer.BartendroCantPourError, err:
        raise BadRequest(err)
    except mixer.BartendroBrokenError, err:
        raise InternalServerError(err)
    except mixer.BartendroBusyError, err:
        raise ServiceUnavailable(err)

    return ""

@app.route('/ws/drink/<int:id>/load')
@login_required
def ws_drink_load(id):
    return drink_load(id)

def drink_load(id):
    drink = Drink.query.filter_by(id=int(id)).first()
    boozes = []
    for booze in drink.drink_boozes:
        boozes.append((booze.booze_id, booze.value))
    drink = { 
        'id'         : id,
        'name'       : drink.name.name,
        'desc'       : drink.desc,
        'popular'    : drink.popular,
        'available'  : drink.available,
        'boozes'     : boozes,
        'num_boozes' : len(boozes)
    }
    return json.dumps(drink)

@app.route('/ws/drink/<int:drink>/save', methods=["POST"])
def ws_drink_save(drink):

    data = request.json['drink']
    id = int(data["id"] or 0)
    if id > 0:
        drink = Drink.query.filter_by(id=int(id)).first()
    else:
        id = 0
        drink = Drink()
        db.session.add(drink)

    try:
        drink.name.name = data['name']
        drink.desc = data['desc']
        if data['popular']:
            drink.popular = True
        else:
            drink.popular = False
            
        if data['available']:
            drink.available = True
        else:
            drink.available = False
    except ValueError:
        raise BadRequest

    for selected_booze_id, parts, old_booze_id in data['boozes']:
        try:
            selected_booze_id = int(selected_booze_id) # this is the id that comes from the most recent selection
            old_booze_id = int(old_booze_id)     # this id is the id that was previously used by this slot. Used for
                                                 # cleaning up or updateing existing entries
            parts = int(parts)                   
        except ValueError:
            raise BadRequest

        # if the parts are set to zero, remove this drink_booze from this drink
        if parts == 0:
            if old_booze_id != 0:
                for i, dbooze in enumerate(drink.drink_boozes):
                    if dbooze.booze_id == old_booze_id:
                        db.session.delete(drink.drink_boozes[i])
                        break
            continue

        # if there is an old_booze_id, then update the existing entry
        if old_booze_id > 0:
            for drink_booze in drink.drink_boozes:
                if old_booze_id == drink_booze.booze_id:
                    drink_booze.value = parts
                    if (selected_booze_id != drink_booze.booze_id):
                        drink_booze.booze = Booze.query.filter_by(id=selected_booze_id).first()
                    break
        else:
            # Create a new drink-booze entry
            booze = Booze.query.filter_by(id=selected_booze_id).first()
            DrinkBooze(drink, booze, parts, 0)

    db.session.commit()
    mc = app.mc
    mc.delete("top_drinks")
    mc.delete("other_drinks")
    mc.delete("available_drink_list")

    return drink_load(drink.id) 

########NEW FILE########
__FILENAME__ = liquidlevel
# -*- coding: utf-8 -*-
import os
import json
import logging
from time import sleep
from werkzeug.exceptions import BadRequest, InternalServerError
from bartendro import app, db
from flask import Flask, request, Response
from flask.ext.login import login_required

log = logging.getLogger('bartendro')

@app.route('/ws/liquidlevel/test/<int:disp>')
@login_required
def ws_liquidlevel_test(disp):
    low, out = app.driver.get_liquid_level_thresholds(disp)
    if low < 0 or out < 0: 
        log.error("Failed to read liquid level threshold from dispenser %d" % (disp + 1))
        raise InternalServerError
    app.mixer.liquid_level_test(disp, out)
    return "ok"

@app.route('/ws/liquidlevel/out/<int:disp>/set')
@login_required
def ws_liquidlevel_out_set(disp):
    driver = app.driver
    if disp < 0 or disp >= driver.count():
        raise BadRequest

    if not driver.update_liquid_levels():
        log.error("Failed to update liquid level thresholds")
        raise InternalServerError
    sleep(.01)

    out = driver.get_liquid_level(disp)
    if out < 0: 
        log.error("Failed to read liquid level threshold from dispenser %d" % (disp + 1))
        raise InternalServerError

    low, dummy = driver.get_liquid_level_thresholds(disp)
    if low < 0 or dummy < 0: 
        log.error("Failed to read liquid level threshold from dispenser %d" % (disp + 1))
        raise InternalServerError

    driver.set_liquid_level_thresholds(disp, low, out)
    return "%d\n" % out

@app.route('/ws/liquidlevel/low/<int:disp>/set')
@login_required
def ws_liquidlevel_low_set(disp):
    driver = app.driver
    if not driver.update_liquid_levels():
        log.error("Failed to update liquid level thresholds")
        raise InternalServerError
    sleep(.01)

    low = driver.get_liquid_level(disp)
    if low < 0: 
        log.error("Failed to read liquid level threshold from dispenser %d" % (disp + 1))
        raise InternalServerError

    dummy, out = driver.get_liquid_level_thresholds(disp)
    if dummy < 0 or out < 0: 
        log.error("Failed to read liquid level threshold from dispenser %d" % (disp + 1))
        raise InternalServerError

    driver.set_liquid_level_thresholds(disp, low, out)
    return "%d\n" % low


from random import randint

@app.route('/ws/liquidlevel/out/all/set')
@login_required
def ws_liquidlevel_out_all_set():
    driver = app.driver

    data = []
    for disp in xrange(driver.count()):
        out = driver.get_liquid_level(disp)
        if out < 0: 
            log.error("Failed to read liquid level threshold from dispenser %d" % (disp + 1))
            raise InternalServerError

        low, dummy = driver.get_liquid_level_thresholds(disp)
        if low < 0 or dummy < 0: 
            log.error("Failed to read liquid level threshold from dispenser %d" % (disp + 1))
            raise InternalServerError

        driver.set_liquid_level_thresholds(disp, low, out)
        data.append(out)

    if not driver.update_liquid_levels():
        log.error("Failed to update liquid level thresholds")
        raise InternalServerError
    sleep(.01)

    return json.dumps({ 'levels' : data })

@app.route('/ws/liquidlevel/low/all/set')
@login_required
def ws_liquidlevel_low_all_set():
    driver = app.driver

    data = []
    for disp in xrange(driver.count()):
        low = driver.get_liquid_level(disp)
        if low < 0: 
            log.error("Failed to read liquid level threshold from dispenser %d" % (disp + 1))
            raise InternalServerError

        dummy, out = driver.get_liquid_level_thresholds(disp)
        if dummy < 0 or out < 0: 
            log.error("Failed to read liquid level threshold from dispenser %d" % (disp + 1))
            raise InternalServerError

        driver.set_liquid_level_thresholds(disp, low, out)
        data.append(low)

    if not driver.update_liquid_levels():
        log.error("Failed to update liquid level thresholds")
        raise InternalServerError
    sleep(.01)

    return json.dumps({ 'levels' : data })

########NEW FILE########
__FILENAME__ = misc
# -*- coding: utf-8 -*-
import os
import logging
from werkzeug.exceptions import ServiceUnavailable, InternalServerError
from bartendro import app, db, STATIC_FOLDER
from flask import Flask, request, Response
from flask.ext.login import login_required
from bartendro.model.drink import Drink
from bartendro.model.booze import Booze
from bartendro.form.booze import BoozeForm
from bartendro.error import BartendroBusyError, BartendroBrokenError, BartendroCantPourError, BartendroCurrentSenseError

log = logging.getLogger('bartendro')

@app.route('/ws/reset')
@login_required
def ws_reset():
    driver = app.driver
    mc = app.mc
    mc.delete("top_drinks")
    mc.delete("other_drinks")
    mc.delete("available_drink_list")
    driver.reset()
    app.mixer.reset()
    return "ok\n"

@app.route('/ws/test')
@login_required
def ws_test_chain():
    driver = app.driver
    for disp in xrange(driver.count()):
	if not driver.ping(disp):
            log.error("Dispense %d failed ping" % (disp + 1))
	    return "Dispenser %d failed ping." % (disp + 1)

    return ""

@app.route('/ws/checklevels')
@login_required
def ws_check_levels():
    mixer = app.mixer
    try:
        mixer.check_levels()
    except BartendroCantPourError, err:
        raise BadRequest(err)
    except BartendroBrokenError, err:
        raise InternalServerError(err)
    except BartendroBusyError, err:
        raise ServiceUnavailable(err)

    return ""

@app.route('/ws/download/bartendro.db')
@login_required
def ws_download_db():

    # close the connection to the database to flush anything that might still be in a cache somewhere
    db.session.bind.dispose()

    # Now read the database into memory
    try:
        fh = open("bartendro.db", "r")
        db_data = fh.read()
        fh.close()
    except IOError, e:
        raise ServiceUnavailable("Error: downloading database failed: %s" % e)

    r = Response(db_data, mimetype='application/x-sqlite')
    r.set_cookie("fileDownload", "true")
    return r

########NEW FILE########
__FILENAME__ = option
# -*- coding: utf-8 -*-
import json
import os
import sqlite3
import shutil
from time import time
from tempfile import mktemp
from sqlalchemy import asc, func
from bartendro import app, db, mixer
from flask import Flask, request
from flask.ext.login import login_required, logout_user
from werkzeug.exceptions import InternalServerError, BadRequest
from bartendro.model.option import Option
from bartendro.options import bartendro_options

DB_BACKUP_DIR = '.db-backups'

@app.route('/ws/options', methods=["POST", "GET"])
@login_required
def ws_options():
    if request.method == 'GET':
        options = Option.query.order_by(asc(func.lower(Option.key)))
        data = {}
        for o in options:
            try:    
                if isinstance(bartendro_options[o.key], int):
                   value = int(o.value)
                elif isinstance(bartendro_options[o.key], unicode):
                   value = unicode(o.value)
                elif isinstance(bartendro_options[o.key], boolean):
                   value = boolean(o.value)
                else:
                    raise InternalServerError
            except KeyError:
                pass

            data[o.key] = value

        return json.dumps({ 'options' : data });

    if request.method == 'POST':
        try:
            data = request.json['options']
            logout = request.json['logout']
        except KeyError:
            raise BadRequest

        if logout: logout_user()

        Option.query.delete()

        for key in data:
            option = Option(key, data[key])
            db.session.add(option)

        db.session.commit()
        try:
            import uwsgi
            uwsgi.reload()
            reload = True
        except ImportError:
            reload = False
        return json.dumps({ 'reload' : reload });

    raise BadRequest

@app.route('/ws/upload', methods=["POST"])
@login_required
def ws_upload():
    db_file = request.files['file']
    file_name = mktemp()
    try:
        db_file.save(file_name)
    except IOError:
        raise InternalServerError

    try:
        con = sqlite3.connect(file_name)
        cur = con.cursor()    
        cur.execute("SELECT * FROM dispenser")
    except sqlite3.DatabaseError:
        os.unlink(file_name)
        raise BadRequest

    return json.dumps('{ "file_name": "%s" }' % file_name)

@app.route('/ws/upload/confirm', methods=["POST"])
@login_required
def ws_upload_confirm():
    file_name = request.json['file_name']
    print file_name
    print "Move file '%s' into place." % file_name

    if not os.path.exists(DB_BACKUP_DIR):
        try:
            os.mkdir(DB_BACKUP_DIR)
        except OSError:
            return json.dumps({ 'error' : "Cannot create backup dir" })

    # close the connection to the database to flush anything that might still be in a cache somewhere
    db.session.bind.dispose()

    try:
        shutil.move("bartendro.db", os.path.join(DB_BACKUP_DIR, "%d.db" % int(time())))
    except OSError:
        return json.dumps({ 'error' : "Cannot backup old database" })

    try:
        shutil.move(file_name, "bartendro.db")
    except OSError:
        return json.dumps({ 'error' : "Cannot backup old database" })

    mc = app.mc
    mc.delete("top_drinks")
    mc.delete("other_drinks")
    mc.delete("available_drink_list")
    return json.dumps({ 'error' : "" })

########NEW FILE########
__FILENAME__ = bartendro_server
#!/usr/bin/env python

from bartendro import app
import logging
import logging.handlers
import os
import memcache
import sys
import argparse
import subprocess
import traceback

from bartendro.global_lock import BartendroGlobalLock
from bartendro.router import driver
from bartendro import mixer
from bartendro.error import I2CIOError, SerialIOError
from bartendro.options import load_options

if os.path.exists("version.txt"):
    with open("version.txt", "r") as f:
        version = f.read()
else:
    version = subprocess.check_output(["git", "rev-parse", "HEAD"])
    if version:
        version = "git commit " + version[:10]
    else:
        version = "[unknown]"

LOG_SIZE = 1024 * 500  # 500k maximum log file size
LOG_FILES_SAVED = 3    # number of log files to compress and save


parser = argparse.ArgumentParser(description='Bartendro application process')
parser.add_argument("-d", "--debug", help="Turn on debugging mode to see stack traces in the error log", default=True, action='store_true')
parser.add_argument("-t", "--host", help="Which interfaces to listen on. Default: 127.0.0.1", default="127.0.0.1", type=str)
parser.add_argument("-p", "--port", help="Which port to listen on. Default: 8080", default="8080", type=int)
parser.add_argument("-s", "--software-only", help="Run only the server software, without hardware interaction.", default=False, action='store_true')

args = parser.parse_args()

try:
    import uwsgi
    have_uwsgi = True
except ImportError:
    have_uwsgi = False

def print_software_only_notice():
    print """If you're trying to run this code without having Bartendro hardware,
you can still run the software portion of it in a simulation mode. In this mode no 
communication with the Bartendro hardware will happen to allow the software to run.
To enable this mode, set the BARTENDRO_SOFTWARE_ONLY environment variable to 1 and 
try again:

    > export BARTENDRO_SOFTWARE_ONLY=1

"""

# Set up logging
if not os.path.exists("logs"):
    os.mkdir("logs")

handler = logging.handlers.RotatingFileHandler(os.path.join("logs", "bartendro.log"), 
                                               maxBytes=LOG_SIZE, 
                                               backupCount=LOG_FILES_SAVED)
logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.INFO)
logger = logging.getLogger('bartendro')
logger.addHandler(handler)
logger.info("Bartendro start up sequence:")

try: 
    app.software_only = args.software_only or int(os.environ['BARTENDRO_SOFTWARE_ONLY'])
    app.num_dispensers = 15
except KeyError:
    app.software_only = 0

if not os.path.exists("bartendro.db"):
    print "bartendro.db file not found. Please copy bartendro.db.default to "
    print "bartendro.db in order to provide Bartendro with a starting database."
    sys.exit(-1)

# Create a memcache connection and flush everything
app.mc = memcache.Client(['127.0.0.1:11211'], debug=0)
app.mc.flush_all()

# Create the Bartendro globals to prevent multiple people from using it at the same time.
app.globals = BartendroGlobalLock()

startup_err = ""
# Start the driver, which talks to the hardware
try:
    app.driver = driver.RouterDriver("/dev/ttyAMA0", app.software_only);
    app.driver.open()
    logging.info("Found %d dispensers." % app.driver.count())
except I2CIOError:
    err = "Cannot open I2C interface to a router board."
    if have_uwsgi:
        startup_err = err
    else:
        print
        print err
        print
        print_software_only_notice()
        sys.exit(-1)
except SerialIOError:
    err = "Cannot open serial interface to a router board."
    if have_uwsgi:
        startup_err = err
    else:
        print
        print err
        print
        print_software_only_notice()
        sys.exit(-1)
except:
    err = traceback.format_exc()
    if have_uwsgi:
        startup_err = err
    else:
        print
        print err
        print
        print_software_only_notice()
        sys.exit(-1)

app.startup_err = startup_err
if app.startup_err:
    logger.info("Bartendro failed to start:")
    logger.error(err)
else:
    app.options = load_options()
    app.mixer = mixer.Mixer(app.driver, app.mc)
    if app.software_only:
        logging.info("Running SOFTWARE ONLY VERSION. No communication between software and hardware chain will happen!")

    logging.info("Bartendro started")
    app.debug = args.debug
    app.version = version

if __name__ == '__main__':
    app.run(host=args.host, port=args.port)

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
from werkzeug import script

def make_app():
    from bartendro.application import BartendroUIServer
    return BartendroUIServer('sqlite:///bartendro.db')

def make_shell():
    from bartendro import models, utils
    application = make_app()
    return locals()

action_runserver = script.make_runserver(make_app, use_reloader=True)
action_shell = script.make_shell(make_shell)
action_initdb = lambda: make_app().init_database()

script.run()

########NEW FILE########
__FILENAME__ = program_and_test_dispenser
#!/usr/bin/env python

import os
import memcache
import sys
import logging
import logging.handlers
import argparse
import subprocess
from time import sleep
from bartendro import app
from bartendro.router import driver

parser = argparse.ArgumentParser()
parser.add_argument('--ll', help="Test liquid level sensor", dest='ll',action='store_true')
parser.add_argument('--no-ll', help="Don't test liquid level sensor", dest='ll',action='store_false')
parser.set_defaults(ll=True)
args = parser.parse_args()

def test(ll):
    try:
        subprocess.check_call(["make", "-C", "../firmware/dispenser", "dispenser"])
    except subprocess.CalledProcessError:
        print "Failed to program dispenser!"
        sys.exit(-1)

    sleep(1)

    dt = driver.RouterDriver("/dev/ttyAMA0", False)
    dt.open()
    sleep(.1)
    if dt.ping(0):
        print "ping ok"
    else:
        print "ping failed"
        sys.exit(-1)

    dt.set_motor_direction(0, driver.MOTOR_DIRECTION_FORWARD)

    print "timed forward"
    if not dt.dispense_time(0, 950):
        print "timed dispense forward failed."
        sys.exit(-1)

    sleep(1.5)

    dt.set_motor_direction(0, driver.MOTOR_DIRECTION_BACKWARD)

    print "ticks backward"
    if not dt.dispense_ticks(0, 24):
        print "ticks dispense backward failed."
        sys.exit(-1)
    sleep(1.5)

    dt.set_motor_direction(0, driver.MOTOR_DIRECTION_FORWARD)

    print "ticks forward"
    if not dt.dispense_ticks(0, 24):
        print "tick dispense forward failed."
        sys.exit(-1)
    sleep(1.5)

    dt.set_motor_direction(0, driver.MOTOR_DIRECTION_BACKWARD)

    print "time backward"
    if not dt.dispense_time(0, 950):
        print "timed dispense backward failed."
        sys.exit(-1)
    sleep(1.5)

    dt.set_motor_direction(0, driver.MOTOR_DIRECTION_FORWARD)

    if ll:
        while True:
            line = raw_input("Press Enter to check the liquid level sensor. Type 'q' to move on to the next dispenser... ")
            if line == 'q':
                break

            if not dt.update_liquid_levels():
                print "updating liquid levels failed."
                sys.exit(-1)

            sleep(.1)
           
            ll = dt.get_liquid_level(0)
            if ll < 0:
                print "updating liquid levels failed."
                sys.exit(-1)

            print "Current level: %d" % ll

    print "All tests passed!"
    print
    print

while True:
    test(args.ll)

    line = raw_input("Press Enter to program/test the next dispenser.... Type 'q' to exit.")
    if line == 'q':
        break

sys.exit(0)

########NEW FILE########
