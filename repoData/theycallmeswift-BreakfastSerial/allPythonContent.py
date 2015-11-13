__FILENAME__ = BreakfastSerial
import os
import re
import threading
from time import sleep

import pyfirmata


def find_arduino():
    rport = re.compile('usb|acm', re.IGNORECASE)
    ports = filter(rport.search, os.listdir('/dev'))

    if len(ports) == 0:
        raise ArduinoNotFoundException

    print("Connecting to /dev/{0}".format(ports[0]))
    return "/dev/%s" % ports[0]


class ArduinoNotFoundException(Exception):
    pass


class FirmataNotOnBoardException(Exception):
    pass


class Arduino(pyfirmata.Arduino):

    def __init__(self, *args, **kwargs):
        # If no port was supplied, auto detect the arduino
        if len(args) >= 1:
            super(Arduino, self).__init__(*args, **kwargs)
        else:
            newargs = (find_arduino(),)
            super(Arduino, self).__init__(*newargs)

        if not self.get_firmata_version():
            raise FirmataNotOnBoardException

        self._observers = {}

        # Register a new handler for digital messages so we can tell sensors to
        # update
        self.add_cmd_handler(
            pyfirmata.DIGITAL_MESSAGE,
            self._handle_digital_message_interceptor)
        self.add_cmd_handler(
            pyfirmata.ANALOG_MESSAGE,
            self._handle_analog_message_interceptor)
        self._monitor = Monitor(self)

    def _handle_digital_message_interceptor(self, port_nr, lsb, msb):
        self._handle_digital_message(port_nr, lsb, msb)
        self.emit('data')  # TODO: Make less generic

    def _handle_analog_message_interceptor(self, port_nr, lsb, msb):
        self._handle_analog_message(port_nr, lsb, msb)
        self.emit('data')  # TODO: Make less generic

    # TODO: Make generic eventemitter class and inherit
    def on(self, event, cb):
        if event not in self._observers:
            self._observers[event] = [cb, ]
        else:
            if cb not in self._observers[event]:
                self._observers[event].append(cb)
            else:
                raise ValueError(
                    "Observer is already registered to event: ",
                    event)

    def off(self, event, cb):
        if event not in self._observers:
            raise KeyError(
                "No observers are registered for the event: ",
                event)
        else:
            if cb not in self._observers[event]:
                raise ValueError(
                    "Observer is not registered for the event: ",
                    event)
            else:
                self._observers[event].remove(cb)

    def emit(self, event, *args):
        if event in self._observers:
            for observer in self._observers[event]:
                observer(*args)


class Monitor(threading.Thread):

    def __init__(self, board):
        threading.Thread.__init__(self)

        self.board = board
        self._shouldContinue = True

        self.setDaemon(True)
        self.start()

    def run(self):
        while True:
            while self.board.bytes_available():
                self.board.iterate()

            sleep(0.004)

            if not self._shouldContinue:
                break

    def stop(self):
        self._shouldContinue = False

########NEW FILE########
__FILENAME__ = components
import re
import threading
import pyfirmata
from util import EventEmitter, setInterval, debounce


class ArduinoNotSuppliedException(Exception):
    pass


class ServoOutOfRangeException(Exception):
    pass


class InvalidPercentageException(Exception):
    pass


class Component(EventEmitter):

    def __init__(self, board, pin):
        if not board:
            raise ArduinoNotSuppliedException

        super(Component, self).__init__()

        self._board = board

        analog_regex = re.compile('A(\d)')
        match = analog_regex.match(str(pin))

        if match:
            self._pin = self._board.analog[int(match.group(1))]
        else:
            self._pin = self._board.digital[int(pin)]

    @property
    def value(self):
        return self._pin.value


class Sensor(Component):

    def __init__(self, board, pin):
        super(Sensor, self).__init__(board, pin)

        self.threshold = 0.01

        self._pin.mode = pyfirmata.INPUT
        self._pin.enable_reporting()

        self._old_value = self.value
        self._board.on('data', self._handle_data)

    def _handle_data(self):
        value = self.value or 0
        high_value = value + self.threshold
        low_value = value - self.threshold

        if self._old_value < low_value or self._old_value > high_value:
            self._old_value = value
            self._handle_state_changed()

    @debounce(0.005)
    def _handle_state_changed(self):
        self.emit('change')

    def change(self, cb):
        self.on('change', cb)


class Led(Component):

    def __init__(self, board, pin):
        super(Led, self).__init__(board, pin)
        self._isOn = False
        self._interval = None

    def on(self):
        self._pin.write(1)
        self._isOn = True
        return self

    def off(self, clear=True):
        self._pin.write(0)
        self._isOn = False

        if self._interval and clear:
            self._interval.clear()

        return self

    def toggle(self):
        if self._isOn:
            return self.off(clear=False)
        else:
            return self.on()

    def blink(self, millis):
        if self._interval:
            self._interval.clear()

        self._interval = setInterval(self.toggle, millis)

    def brightness(self, value):
        if int(value) > 100 or int(value) < 0:
            raise InvalidPercentageException

        if self._pin.mode != pyfirmata.PWM:
            self._pin.mode = pyfirmata.PWM

        _new_value = value / 100.0

        if _new_value == 0:
            self._isOn = False
        else:
            self.isOn = True

        self._pin.write(_new_value)
        return self


class RGBLed(EventEmitter):

    def __init__(self, board, pins):
        if not board:
            raise ArduinoNotSuppliedException

        # TODO: Check that pins is dict

        super(RGBLed, self).__init__()

        self._red = Led(board, pins["red"])
        self._green = Led(board, pins["green"])
        self._blue = Led(board, pins["blue"])

    def off(self):
        self._red.off()
        self._green.off()
        self._blue.off()
        return self

    def red(self):
        self._red.on()
        self._green.off()
        self._blue.off()
        return self

    def green(self):
        self._red.off()
        self._green.on()
        self._blue.off()
        return self

    def blue(self):
        self._red.off()
        self._green.off()
        self._blue.on()
        return self

    def yellow(self):
        self._red.on()
        self._green.on()
        self._blue.off()
        return self

    def cyan(self):
        self._red.off()
        self._green.on()
        self._blue.on()
        return self

    def purple(self):
        self._red.on()
        self._green.off()
        self._blue.on()
        return self

    def white(self):
        self._red.on()
        self._green.on()
        self._blue.on()
        return self


class Buzzer(Led):
    pass


class Button(Sensor):

    def __init__(self, board, pin):
        super(Button, self).__init__(board, pin)
        self._old_value = False
        self._timeout = None

        self.change(self._emit_button_events)

    def _handle_data(self):
        value = self.value

        if self._old_value != value:
            self._old_value = value
            # This sucks, wish I could just call Super
            self._handle_state_changed()

    def _emit_button_events(self):
        if self.value is False:
            if(self._timeout):
                self._timeout.cancel()

            self.emit('up')
        elif self.value:
            def emit_hold():
                self.emit('hold')

            self._timeout = threading.Timer(1, emit_hold)
            self._timeout.start()

            self.emit('down')

    def down(self, cb):
        self.on('down', cb)

    def up(self, cb):
        self.on('up', cb)

    def hold(self, cb):
        self.on('hold', cb)


class Servo(Component):

    def __init__(self, board, pin):
        super(Servo, self).__init__(board, pin)
        self._pin.mode = pyfirmata.SERVO

    def set_position(self, degrees):
        if int(degrees) > 180 or int(degrees) < 0:
            raise ServoOutOfRangeException
        self._pin.write(degrees)

    def move(self, degrees):
        self.set_position(self.value + int(degrees))

    def center(self):
        self.set_position(90)

    def reset(self):
        self.set_position(0)


class Motor(Component):

    def __init__(self, board, pin):
        super(Motor, self).__init__(board, pin)
        self._speed = 0
        self._pin.mode = pyfirmata.PWM

    def start(self, speed=50):
        self.speed = speed

    def stop(self):
        self.speed = 0

    @property
    def speed(self):
        return self._speed

    @speed.setter
    def speed(self, speed):
        if int(speed) > 100 or int(speed) < 0:
            raise InvalidPercentageException

        self._speed = speed
        self._pin.write(speed / 100.0)
        self.emit('change', speed)

########NEW FILE########
__FILENAME__ = util
import threading
from time import sleep


class EventEmitter(object):

    def __init__(self, *args, **kwargs):
        self._observers = {}

    def on(self, event, cb):
        if event not in self._observers:
            self._observers[event] = [cb, ]
        else:
            if cb not in self._observers[event]:
                self._observers[event].append(cb)
            else:
                raise ValueError(
                    "Observer is already registered to event: ",
                    event)

    def off(self, event, cb):
        if event not in self._observers:
            raise KeyError(
                "No observers are registered for the event: ",
                event)
        else:
            if cb not in self._observers[event]:
                raise ValueError(
                    "Observer is not registered for the event: ",
                    event)
            else:
                self._observers[event].remove(cb)

    def emit(self, event, *args):
        if event in self._observers:
            for observer in self._observers[event]:
                observer(*args)


def debounce(wait):
    """ Decorator that will postpone a functions
        execution until after wait seconds
        have elapsed since the last time it was invoked. """
    def decorator(fn):
        def debounced(*args, **kwargs):
            def call_it():
                fn(*args, **kwargs)
            try:
                debounced.t.cancel()
            except(AttributeError):
                pass
            debounced.t = threading.Timer(wait, call_it)
            debounced.t.start()
        return debounced
    return decorator


class setInterval(threading.Thread):

    def __init__(self, func, millis):
        threading.Thread.__init__(self)
        self.event = threading.Event()
        self.func = func
        self.seconds = millis / 1000.0
        self.shouldRun = True

        self.setDaemon(True)
        self.start()

    def run(self):
        while self.shouldRun:
            self.func()
            sleep(self.seconds)

    def clear(self):
        self.shouldRun = False

########NEW FILE########
__FILENAME__ = button
#! /usr/bin/env python
"""
This is an example that demonstrates how to use a
button with BreakfastSerial.  It assumes you have an
button wired up to pin 8.
"""
from BreakfastSerial import Button, Arduino

board = Arduino()
button = Button(board, 8)

def down_cb():
  print "button down"

def up_cb():
  print "button up"

button.down(down_cb)
button.up(up_cb)

# Run an interactive shell so you can play (not required)
import code
code.InteractiveConsole(locals=globals()).interact()

########NEW FILE########
__FILENAME__ = buzzer
#! /usr/bin/env python
"""
This is an example that demonstrates how to use a
photoresistor to control a buzzer (piezo element)
using BreakfastSerial.  It assumes you have an
photoresistor (or some equivalent analog input) 
wired up to pin A0 and a buzzer on pin 8.
"""
from BreakfastSerial import Arduino, Buzzer, Sensor, setInterval
from time import sleep

board = Arduino()
buzzer = Buzzer(board, "8")
sensor = Sensor(board, "A0")

def loop():
  value = sensor.value or 1 # value is initially None
  value = value / 2

  buzzer.on()
  sleep(value)
  buzzer.off()
  sleep(value)

setInterval(loop, 0)

# Run an interactive shell so you can play (not required)
import code
code.InteractiveConsole(locals=globals()).interact()

########NEW FILE########
__FILENAME__ = led
#! /usr/bin/env python
"""
This is an example that demonstrates how to blink an
led using BreakfastSerial.  It assumes you have an
led wired up to pin 13.
"""
from BreakfastSerial import Led, Arduino

board = Arduino()
led = Led(board, 13)

led.blink(200)

# Run an interactive shell so you can play (not required)
import code
code.InteractiveConsole(locals=globals()).interact()

########NEW FILE########
__FILENAME__ = light_switch
#! /usr/bin/env python
"""
This is an example that demonstrates how to use a
button to control an led with BreakfastSerial. It
assumes you have an button wired up to pin 8 and an
led wired to pin 13.
"""
from BreakfastSerial import Arduino, Led, Button

board = Arduino()
button = Button(board, 8)
led = Led(board, 13)

button.down(led.toggle)
button.hold(lambda: led.blink(200))

# Run an interactive shell so you can play (not required)
import code
code.InteractiveConsole(locals=globals()).interact()

########NEW FILE########
__FILENAME__ = motor
#! /usr/bin/env python
"""
This is an example that demonstrates how to use a
a DC Motor with BreakfastSerial. It assumes you have 
a motor wired up to PWM pin 9.  Expected behavior is:

0 Seconds: Turn on motor to 80% speed
3 Seconds: Set speed to 50%
6 Seconds: Turn off motor
"""
from BreakfastSerial import Arduino, Motor
from time import sleep

board = Arduino()
motor = Motor(board, 9)

motor.start(80)
sleep(3)
motor.speed = 50
sleep(3)
motor.stop()

# Run an interactive shell so you can play (not required)
import code
code.InteractiveConsole(locals=globals()).interact()

########NEW FILE########
__FILENAME__ = potentiometer
#! /usr/bin/env python
"""
This is an example that demonstrates how to use a
potentiometer to fade an LED with BreakfastSerial.
It assumes you have an potentiometer wired up to
pin A0 and a LED on pin 9.
"""
from BreakfastSerial import Arduino, Sensor, Led

board = Arduino()
sensor = Sensor(board, "A0")
led = Led(board, 9)

def change_led_brightness():
  led.brightness(100 * sensor.value)

sensor.change(change_led_brightness)

# Run an interactive shell so you can play (not required)
import code
code.InteractiveConsole(locals=globals()).interact()


########NEW FILE########
__FILENAME__ = rgb_led
#! /usr/bin/env python
"""
This is an example that demonstrates how to use an
RGB led with BreakfastSerial.  It assumes you have an
RGB led wired up with red on pin 10, green on pin 9,
and blue on pin 8.
"""
from BreakfastSerial import RGBLed, Arduino
from time import sleep

board = Arduino()
led = RGBLed(board, { "red": 10, "green": 9, "blue": 8 })

# Red (R: on, G: off, B: off)
led.red()
sleep(1)

# Green (R: off, G: on, B: off)
led.green()
sleep(1)

# Blue (R: off, G: off, B: on)
led.blue()
sleep(1)

# Yellow (R: on, G: on, B: off)
led.yellow()
sleep(1)

# Cyan (R: off, G: on, B: on)
led.cyan()
sleep(1)

# Purple (R: on, G: off, B: on)
led.purple()
sleep(1)

# White (R: on, G: on, B: on)
led.white()
sleep(1)

# Off (R: off, G: off, B: off)
led.off()

# Run an interactive shell so you can play (not required)
import code
code.InteractiveConsole(locals=globals()).interact()

########NEW FILE########
__FILENAME__ = servo
#! /usr/bin/env python
"""
This is an example that demonstrates how to use a
servo with BreakfastSerial. It assumes you have a 
servo wired up to pin 10.
"""
from BreakfastSerial import Arduino, Servo
from time import sleep

board = Arduino()
servo = Servo(board,10)

servo.set_position(180)
sleep(2)
servo.move(-135)
sleep(2)
servo.center()
sleep(2)
servo.reset()

# Run an interactive shell so you can play (not required)
import code
code.InteractiveConsole(locals=globals()).interact()

########NEW FILE########
