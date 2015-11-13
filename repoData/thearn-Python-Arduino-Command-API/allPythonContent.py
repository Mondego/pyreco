__FILENAME__ = arduino
#!/usr/bin/env python
import logging
import itertools
import platform
import serial
import time
from serial.tools import list_ports
if platform.system() == 'Windows':
    import _winreg as winreg
else:
    import glob


log = logging.getLogger(__name__)


def enumerate_serial_ports():
    """
    Uses the Win32 registry to return a iterator of serial
        (COM) ports existing on this computer.
    """
    path = 'HARDWARE\\DEVICEMAP\\SERIALCOMM'
    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path)
    except WindowsError:
        raise Exception
  
    for i in itertools.count():
        try:
            val = winreg.EnumValue(key, i)
            yield (str(val[1]))  # , str(val[0]))
        except EnvironmentError:
            break


def build_cmd_str(cmd, args=None):
    """
    Build a command string that can be sent to the arduino.

    Input:
        cmd (str): the command to send to the arduino, must not
            contain a % character
        args (iterable): the arguments to send to the command

    @TODO: a strategy is needed to escape % characters in the args
    """
    if args:
        args = '%'.join(map(str, args))
    else:
        args = ''
    return "@{cmd}%{args}$!".format(cmd=cmd, args=args)


def find_port(baud, timeout):
    """
    Find the first port that is connected to an arduino with a compatible
    sketch installed.
    """
    if platform.system() == 'Windows':
        ports = enumerate_serial_ports()
    elif platform.system() == 'Darwin':
        ports = [i[0] for i in list_ports.comports()]
    else:
        ports = glob.glob("/dev/ttyUSB*") + glob.glob("/dev/ttyACM*")
    for p in ports:
        log.debug('Found {0}, testing...'.format(p))
        try:
            sr = serial.Serial(p, baud, timeout=timeout)
        except (serial.serialutil.SerialException, OSError) as e:
            log.debug(str(e))
            continue
        time.sleep(2)
        version = get_version(sr)
        if version != 'version':
            log.debug('Bad version {0}. This is not a Shrimp/Arduino!'.format(
                version))
            sr.close()
            continue
        log.info('Using port {0}.'.format(p))
        if sr:
            return sr
    return None


def get_version(sr):
    cmd_str = build_cmd_str("version")
    try:
        sr.write(cmd_str)
        sr.flush()
    except Exception:
        return None
    return sr.readline().replace("\r\n", "")


class Arduino(object):

    def __init__(self, baud=9600, port=None, timeout=2, sr=None):
        """
        Initializes serial communication with Arduino if no connection is
        given. Attempts to self-select COM port, if not specified.
        """
        if not sr:
            if not port:
                sr = find_port(baud, timeout)
                if not sr:
                    raise ValueError("Could not find port.")
            else:
                sr = serial.Serial(port, baud, timeout=timeout)
        sr.flush()
        self.sr = sr
        self.SoftwareSerial = SoftwareSerial(self)
        self.Servos = Servos(self)
        self.EEPROM = EEPROM(self)

    def version(self):
        return get_version(self.sr)

    def digitalWrite(self, pin, val):
        """
        Sends digitalWrite command
        to digital pin on Arduino
        -------------
        inputs:
           pin : digital pin number
           val : either "HIGH" or "LOW"
        """
        if val == "LOW":
            pin_ = -pin
        else:
            pin_ = pin
        cmd_str = build_cmd_str("dw", (pin_,))
        try:
            self.sr.write(cmd_str)
            self.sr.flush()
        except:
            pass

    def analogWrite(self, pin, val):
        """
        Sends analogWrite pwm command
        to pin on Arduino
        -------------
        inputs:
           pin : pin number
           val : integer 0 (off) to 255 (always on)
        """
        if val > 255:
            val = 255
        elif val < 0:
            val = 0
        cmd_str = build_cmd_str("aw", (pin, val))
        try:
            self.sr.write(cmd_str)
            self.sr.flush()
        except:
            pass

    def analogRead(self, pin):
        """
        Returns the value of a specified
        analog pin.
        inputs:
           pin : analog pin number for measurement
        returns:
           value: integer from 1 to 1023
        """
        cmd_str = build_cmd_str("ar", (pin,))
        try:
            self.sr.write(cmd_str)
            self.sr.flush()
        except:
            pass
        rd = self.sr.readline().replace("\r\n", "")
        try:
            return int(rd)
        except:
            return 0

    def pinMode(self, pin, val):
        """
        Sets I/O mode of pin
        inputs:
           pin: pin number to toggle
           val: "INPUT" or "OUTPUT"
        """
        if val == "INPUT":
            pin_ = -pin
        else:
            pin_ = pin
        cmd_str = build_cmd_str("pm", (pin_,))
        try:
            self.sr.write(cmd_str)
            self.sr.flush()
        except:
            pass

    def pulseIn(self, pin, val):
        """
        Reads a pulse from a pin

        inputs:
           pin: pin number for pulse measurement
        returns:
           duration : pulse length measurement
        """
        if val == "LOW":
            pin_ = -pin
        else:
            pin_ = pin
        cmd_str = build_cmd_str("pi", (pin_,))
        try:
            self.sr.write(cmd_str)
            self.sr.flush()
        except:
            pass
        rd = self.sr.readline().replace("\r\n", "")
        try:
            return float(rd)
        except:
            return -1

    def pulseIn_set(self, pin, val, numTrials=5):
        """
        Sets a digital pin value, then reads the response
        as a pulse width.
        Useful for some ultrasonic rangefinders, etc.

        inputs:
           pin: pin number for pulse measurement
           val: "HIGH" or "LOW". Pulse is measured
                when this state is detected
           numTrials: number of trials (for an average)
        returns:
           duration : an average of pulse length measurements

        This method will automatically toggle
        I/O modes on the pin and precondition the
        measurment with a clean LOW/HIGH pulse.
        Arduino.pulseIn_set(pin,"HIGH") is
        equivalent to the Arduino sketch code:

        pinMode(pin, OUTPUT);
        digitalWrite(pin, LOW);
        delayMicroseconds(2);
        digitalWrite(pin, HIGH);
        delayMicroseconds(5);
        digitalWrite(pin, LOW);
        pinMode(pin, INPUT);
        long duration = pulseIn(pin, HIGH);
        """
        if val == "LOW":
            pin_ = -pin
        else:
            pin_ = pin
        cmd_str = build_cmd_str("ps", (pin_,))
        durations = []
        for s in range(numTrials):
            try:
                self.sr.write(cmd_str)
                self.sr.flush()
            except:
                pass
            rd = self.sr.readline().replace("\r\n", "")
            if rd.isdigit():
                if (int(rd) > 1):
                    durations.append(int(rd))
        if len(durations) > 0:
            duration = int(sum(durations)) / int(len(durations))
        else:
            duration = None

        try:
            return float(duration)
        except:
            return -1

    def close(self):
        if self.sr.isOpen():
            self.sr.flush()
            self.sr.close()

    def digitalRead(self, pin):
        """
        Returns the value of a specified
        digital pin.
        inputs:
           pin : digital pin number for measurement
        returns:
           value: 0 for "LOW", 1 for "HIGH"
        """
        cmd_str = build_cmd_str("dr", (pin,))
        try:
            self.sr.write(cmd_str)
            self.sr.flush()
        except:
            pass
        rd = self.sr.readline().replace("\r\n", "")
        try:
            return int(rd)
        except:
            return 0

    def Melody(self, pin, melody, durations):
        """
        Plays a melody.
        inputs:
            pin: digital pin number for playback
            melody: list of tones
            durations: list of duration (4=quarter note, 8=eighth note, etc.)
        length of melody should be of same
        length as length of duration

        Melodies of the following lenght, can cause trouble
        when playing it multiple times.
            board.Melody(9,["C4","G3","G3","A3","G3",0,"B3","C4"],
                                                [4,8,8,4,4,4,4,4])
        Playing short melodies (1 or 2 tones) didn't cause
        trouble during testing
        """
        NOTES = dict(
            B0=31, C1=33, CS1=35, D1=37, DS1=39, E1=41, F1=44, FS1=46, G1=49,
            GS1=52, A1=55, AS1=58, B1=62, C2=65, CS2=69, D2=73, DS2=78, E2=82,
            F2=87, FS2=93, G2=98, GS2=104, A2=110, AS2=117, B2=123, C3=131,
            CS3=139, D3=147, DS3=156, E3=165, F3=175, FS3=185, G3=196, GS3=208,
            A3=220, AS3=233, B3=247, C4=262, CS4=277, D4=294, DS4=311, E4=330,
            F4=349, FS4=370, G4=392, GS4=415, A4=440,
            AS4=466, B4=494, C5=523, CS5=554, D5=587, DS5=622, E5=659, F5=698,
            FS5=740, G5=784, GS5=831, A5=880, AS5=932, B5=988, C6=1047,
            CS6=1109, D6=1175, DS6=1245, E6=1319, F6=1397, FS6=1480, G6=1568,
            GS6=1661, A6=1760, AS6=1865, B6=1976, C7=2093, CS7=2217, D7=2349,
            DS7=2489, E7=2637, F7=2794, FS7=2960, G7=3136, GS7=3322, A7=3520,
            AS7=3729, B7=3951, C8=4186, CS8=4435, D8=4699, DS8=4978)
        if (isinstance(melody, list)) and (isinstance(durations, list)):
            length = len(melody)
            cmd_args = [length, pin]
            if length == len(durations):
                cmd_args.extend([NOTES.get(melody[note])
                                for note in range(length)])
                cmd_args.extend([durations[duration]
                                for duration in range(len(durations))])
                cmd_str = build_cmd_str("to", cmd_args)
                try:
                    self.sr.write(cmd_str)
                    self.sr.flush()
                except:
                    pass
                cmd_str = build_cmd_str("nto", [pin])
                try:
                    self.sr.write(cmd_str)
                    self.sr.flush()
                except:
                    pass
            else:
                return -1
        else:
            return -1

    def capacitivePin(self, pin):
        '''
        Input:
            pin (int): pin to use as capacitive sensor

        Use it in a loop!
        DO NOT CONNECT ANY ACTIVE DRIVER TO THE USED PIN !

        the pin is toggled to output mode to discharge the port,
        and if connected to a voltage source,
        will short circuit the pin, potentially damaging
        the Arduino/Shrimp and any hardware attached to the pin.
        '''
        cmd_str = build_cmd_str("cap", (pin,))
        self.sr.write(cmd_str)
        rd = self.sr.readline().replace("\r\n", "")
        if rd.isdigit():
            return int(rd)

    def shiftOut(self, dataPin, clockPin, pinOrder, value):
        """
        Shift a byte out on the datapin using Arduino's shiftOut()

        Input:
            dataPin (int): pin for data
            clockPin (int): pin for clock
            pinOrder (String): either 'MSBFIRST' or 'LSBFIRST'
            value (int): an integer from 0 and 255
        """
        cmd_str = build_cmd_str("so",
                               (dataPin, clockPin, pinOrder, value))
        self.sr.write(cmd_str)
        self.sr.flush()

    def shiftIn(self, dataPin, clockPin, pinOrder):
        """
        Shift a byte in from the datapin using Arduino's shiftIn().

        Input:
            dataPin (int): pin for data
            clockPin (int): pin for clock
            pinOrder (String): either 'MSBFIRST' or 'LSBFIRST'
        Output:
            (int) an integer from 0 to 255
        """
        cmd_str = build_cmd_str("si", (dataPin, clockPin, pinOrder))
        self.sr.write(cmd_str)
        self.sr.flush()
        rd = self.sr.readline().replace("\r\n", "")
        if rd.isdigit():
            return int(rd)


class Shrimp(Arduino):

    def __init__(self):
        Arduino.__init__(self)


class Wires(object):

    """
    Class for Arduino wire (i2c) support
    """

    def __init__(self, board):
        self.board = board
        self.sr = board.sr


class Servos(object):

    """
    Class for Arduino servo support
    0.03 second delay noted
    """

    def __init__(self, board):
        self.board = board
        self.sr = board.sr
        self.servo_pos = {}

    def attach(self, pin, min=544, max=2400):
        cmd_str = build_cmd_str("sva", (pin, min, max))

        while True:
            self.sr.write(cmd_str)
            self.sr.flush()

            rd = self.sr.readline().replace("\r\n", "")
            if rd:
                break
            else:
                log.debug("trying to attach servo to pin {0}".format(pin))
        position = int(rd)
        self.servo_pos[pin] = position
        return 1

    def detach(self, pin):
        position = self.servo_pos[pin]
        cmd_str = build_cmd_str("svd", (position,))
        try:
            self.sr.write(cmd_str)
            self.sr.flush()
        except:
            pass
        del self.servo_pos[pin]

    def write(self, pin, angle):
        position = self.servo_pos[pin]
        cmd_str = build_cmd_str("svw", (position, angle))

        self.sr.write(cmd_str)
        self.sr.flush()

    def writeMicroseconds(self, pin, uS):
        position = self.servo_pos[pin]
        cmd_str = build_cmd_str("svwm", (position, uS))

        self.sr.write(cmd_str)
        self.sr.flush()

    def read(self, pin):
        if pin not in self.servo_pos.keys():
            self.attach(pin)
        position = self.servo_pos[pin]
        cmd_str = build_cmd_str("svr", (position,))
        try:
            self.sr.write(cmd_str)
            self.sr.flush()
        except:
            pass
        rd = self.sr.readline().replace("\r\n", "")
        try:
            angle = int(rd)
            return angle
        except:
            return None


class SoftwareSerial(object):

    """
    Class for Arduino software serial functionality
    """

    def __init__(self, board):
        self.board = board
        self.sr = board.sr
        self.connected = False

    def begin(self, p1, p2, baud):
        """
        Create software serial instance on
        specified tx,rx pins, at specified baud
        """
        cmd_str = build_cmd_str("ss", (p1, p2, baud))
        try:
            self.sr.write(cmd_str)
            self.sr.flush()
        except:
            pass
        response = self.sr.readline().replace("\r\n", "")
        if response == "ss OK":
            self.connected = True
            return True
        else:
            self.connected = False
            return False

    def write(self, data):
        """
        sends data to existing software serial instance
        using Arduino's 'write' function
        """
        if self.connected:
            cmd_str = build_cmd_str("sw", (data,))
            try:
                self.sr.write(cmd_str)
                self.sr.flush()
            except:
                pass
            response = self.sr.readline().replace("\r\n", "")
            if response == "ss OK":
                return True
        else:
            return False

    def read(self):
        """
        returns first character read from
        existing software serial instance
        """
        if self.connected:
            cmd_str = build_cmd_str("sr")
            self.sr.write(cmd_str)
            self.sr.flush()
            response = self.sr.readline().replace("\r\n", "")
            if response:
                return response
        else:
            return False


class EEPROM(object):
    """
    Class for reading and writing to EEPROM. 
    """

    def __init__(self, board):
        self.board = board
        self.sr = board.sr

    def size(self):
        """
        Returns size of EEPROM memory.
        """
        cmd_str = build_cmd_str("sz")
   
        try:
            self.sr.write(cmd_str)
            self.sr.flush()
            response = self.sr.readline().replace("\r\n", "")
            return int(response)
        except:
            return 0
        
    def write(self, address, value=0):
        """ Write a byte to the EEPROM.
            
        :address: the location to write to, starting from 0 (int)
        :value: the value to write, from 0 to 255 (byte)
        """
        
        if value > 255:
            value = 255
        elif value < 0:
            value = 0
        cmd_str = build_cmd_str("eewr", (address, value))
        try:
            self.sr.write(cmd_str)
            self.sr.flush()
        except:
            pass
    
    def read(self, adrress):
        """ Reads a byte from the EEPROM.
        
        :address: the location to write to, starting from 0 (int)
        """
        cmd_str = build_cmd_str("eer", (adrress,))
        try:
            self.sr.write(cmd_str)
            self.sr.flush()            
            response = self.sr.readline().replace("\r\n", "")
            if response:
                return int(response)
        except:
            return 0
                                
########NEW FILE########
__FILENAME__ = examples
#!/usr/bin/env python
from Arduino import Arduino
import time


def Blink(led_pin, baud, port=""):
    """
    Blinks an LED in 1 sec intervals
    """
    board = Arduino(baud, port=port)
    board.pinMode(13, "OUTPUT")
    while True:
        board.digitalWrite(led_pin, "LOW")
        print board.digitalRead(led_pin)  # confirm LOW (0)
        time.sleep(1)
        board.digitalWrite(led_pin, "HIGH")
        print board.digitalRead(led_pin)  # confirm HIGH (1)
        time.sleep(1)


def softBlink(led_pin, baud, port=""):
    """
    Fades an LED off and on, using
    Arduino's analogWrite (PWM) function
    """
    board = Arduino(baud, port=port)
    i = 0
    while True:
        i += 1
        k = i % 510
        if k % 5 == 0:
            if k > 255:
                k = 510 - k
            board.analogWrite(led_pin, k)


def adjustBrightness(pot_pin, led_pin, baud, port=""):
    """
    Adjusts brightness of an LED using a
    potentiometer.
    """
    board = Arduino(baud, port=port)
    while True:
        time.sleep(0.01)
        val = board.analogRead(pot_pin) / 4
        print val
        board.analogWrite(led_pin, val)


def PingSonar(pw_pin, baud, port=""):
    """
    Gets distance measurement from Ping)))
    ultrasonic rangefinder connected to pw_pin
    """
    board = Arduino(baud, port=port)
    pingPin = pw_pin
    while True:
        duration = board.pulseIn(pingPin, "HIGH")
        inches = duration / 72. / 2.
        # cent = duration / 29. / 2.
        print inches, "inches"
        time.sleep(0.1)


def LCD(tx, baud, ssbaud, message, port=""):
    """
    Prints to two-line LCD connected to
    pin tx
    """
    board = Arduino(baud, port=port)
    board.SoftwareSerial.begin(0, tx, ssbaud)
    while True:
        board.SoftwareSerial.write(" test ")

if __name__ == "__main__":
    Blink(13, '9600')

########NEW FILE########
__FILENAME__ = test_arduino
import logging
import unittest


logging.basicConfig(level=logging.DEBUG)


class MockSerial(object):

    def __init__(self, baud, port, timeout=None):
        self.port = port
        self.baud = baud
        self.timeout = timeout
        self.output = []
        self.input = []
        self.is_open = True

    def flush(self):
        pass

    def write(self, line):
        self.output.append(line)

    def isOpen(self):
        return self.is_open

    def close(self):
        if self.is_open:
            self.is_open = False
        else:
            raise ValueError('Mock serial port is already closed.')

    def readline(self):
        """
        @TODO: This does not take timeout into account at all.
        """
        return self.input.pop(0)

    def reset_mock(self):
        self.output = []
        self.input = []

    def push_line(self, line, term='\r\n'):
        self.input.append(str(line) + term)


INPUT = "INPUT"
OUTPUT = "OUTPUT"
LOW = "LOW"
HIGH = "HIGH"
READ_LOW = 0
READ_HIGH = 1
MSBFIRST = "MSBFIRST"
LSBFIRST = "LSBFIRST"


class ArduinoTestCase(unittest.TestCase):

    def setUp(self):
        from Arduino.arduino import Arduino
        self.mock_serial = MockSerial(9600, '/dev/ttyACM0')
        self.board = Arduino(sr=self.mock_serial)


class TestArduino(ArduinoTestCase):

    def parse_cmd_sr(self, cmd_str):
        assert cmd_str[0] == '@'
        first_index = cmd_str.find('%')
        assert first_index != -1
        assert cmd_str[-2:] == '$!'
        # Skip over the @ and read up to but not including the %.
        cmd = cmd_str[1:first_index]
        # Skip over the first % and ignore the trailing $!.
        args_str = cmd_str[first_index+1:-2]
        args = args_str.split('%')
        return cmd, args

    def test_close(self):
        self.board.close()
        # Call again, should skip calling close.
        self.board.close()

    def test_version(self):
        from Arduino.arduino import build_cmd_str
        expected_version = "version"
        self.mock_serial.push_line(expected_version)
        self.assertEquals(self.board.version(), expected_version)
        self.assertEquals(self.mock_serial.output[0], build_cmd_str('version'))

    def test_pinMode_input(self):
        from Arduino.arduino import build_cmd_str
        pin = 9
        self.board.pinMode(pin, INPUT)
        self.assertEquals(self.mock_serial.output[0],
            build_cmd_str('pm', (-pin,)))

    def test_pinMode_output(self):
        from Arduino.arduino import build_cmd_str
        pin = 9
        self.board.pinMode(pin, OUTPUT)
        self.assertEquals(self.mock_serial.output[0],
            build_cmd_str('pm', (pin,)))

    def test_pulseIn_low(self):
        from Arduino.arduino import build_cmd_str
        expected_duration = 230
        self.mock_serial.push_line(expected_duration)
        pin = 9
        self.assertEquals(self.board.pulseIn(pin, LOW), expected_duration)
        self.assertEquals(self.mock_serial.output[0],
            build_cmd_str('pi', (-pin,)))

    def test_pulseIn_high(self):
        from Arduino.arduino import build_cmd_str
        expected_duration = 230
        pin = 9
        self.mock_serial.push_line(expected_duration)
        self.assertEquals(self.board.pulseIn(pin, HIGH), expected_duration)
        self.assertEquals(self.mock_serial.output[0], build_cmd_str('pi', (pin,)))

    def test_digitalRead(self):
        from Arduino.arduino import build_cmd_str
        pin = 9
        self.mock_serial.push_line(READ_LOW)
        self.assertEquals(self.board.digitalRead(pin), READ_LOW)
        self.assertEquals(self.mock_serial.output[0], build_cmd_str('dr', (pin,)))

    def test_digitalWrite_low(self):
        from Arduino.arduino import build_cmd_str
        pin = 9
        self.board.digitalWrite(pin, LOW)
        self.assertEquals(self.mock_serial.output[0], build_cmd_str('dw', (-pin,)))

    def test_digitalWrite_high(self):
        from Arduino.arduino import build_cmd_str
        pin = 9
        self.board.digitalWrite(pin, HIGH)
        self.assertEquals(self.mock_serial.output[0], build_cmd_str('dw', (pin,)))

    def test_melody(self):
        from Arduino.arduino import build_cmd_str
        pin = 9
        notes = ["C4"]
        duration = 4
        C4_NOTE = 262
        self.board.Melody(pin, notes, [duration])
        self.assertEquals(self.mock_serial.output[0],
            build_cmd_str('to', (len(notes), pin, C4_NOTE, duration)))
        self.assertEquals(self.mock_serial.output[1],
            build_cmd_str('nto', (pin,)))

    def test_shiftIn(self):
        from Arduino.arduino import build_cmd_str
        dataPin = 2
        clockPin = 3
        pinOrder = MSBFIRST
        expected = 0xff
        self.mock_serial.push_line(expected)
        self.assertEquals(self.board.shiftIn(dataPin, clockPin, pinOrder),
            expected)
        self.assertEquals(self.mock_serial.output[0],
            build_cmd_str('si', (dataPin, clockPin, pinOrder,)))

    def test_shiftOut(self):
        from Arduino.arduino import build_cmd_str
        dataPin = 2
        clockPin = 3
        pinOrder = MSBFIRST
        value = 0xff
        self.board.shiftOut(dataPin, clockPin, pinOrder, value)
        self.assertEquals(self.mock_serial.output[0],
            build_cmd_str('so', (dataPin, clockPin, pinOrder, value)))

    def test_analogRead(self):
        from Arduino.arduino import build_cmd_str
        pin = 9
        expected = 1023
        self.mock_serial.push_line(expected)
        self.assertEquals(self.board.analogRead(pin), expected)
        self.assertEquals(self.mock_serial.output[0],
            build_cmd_str('ar', (pin,)))

    def test_analogWrite(self):
        from Arduino.arduino import build_cmd_str
        pin = 9
        value = 255
        self.board.analogWrite(pin, value)
        self.assertEquals(self.mock_serial.output[0],
            build_cmd_str('aw', (pin, value)))


class TestServos(ArduinoTestCase):

    def test_attach(self):
        from Arduino.arduino import build_cmd_str
        pin = 10
        position = 0
        self.mock_serial.push_line(position)
        servo_min = 544
        servo_max = 2400
        self.board.Servos.attach(pin, min=servo_min, max=servo_max)
        self.assertEquals(self.mock_serial.output[0],
            build_cmd_str('sva', (pin, servo_min, servo_max)))

    def test_detach(self):
        from Arduino.arduino import build_cmd_str
        pin = 10
        position = 0
        # Attach first.
        self.mock_serial.push_line(position)
        self.board.Servos.attach(pin)
        self.mock_serial.reset_mock()
        self.board.Servos.detach(pin)
        self.assertEquals(self.mock_serial.output[0],
            build_cmd_str('svd', (position,)))

    def test_write(self):
        from Arduino.arduino import build_cmd_str
        pin = 10
        position = 0
        angle = 90
        # Attach first.
        self.mock_serial.push_line(position)
        self.board.Servos.attach(pin)
        self.mock_serial.reset_mock()
        self.board.Servos.write(pin, angle)
        self.assertEquals(self.mock_serial.output[0],
            build_cmd_str("svw", (position, angle)))

    def test_writeMicroseconds(self):
        from Arduino.arduino import build_cmd_str
        pin = 10
        position = 0
        microseconds = 1500
        # Attach first.
        self.mock_serial.push_line(position)
        self.board.Servos.attach(pin)
        self.mock_serial.reset_mock()
        self.board.Servos.writeMicroseconds(pin, microseconds)
        self.assertEquals(self.mock_serial.output[0],
            build_cmd_str("svwm", (position, microseconds)))

    def test_read(self):
        from Arduino.arduino import build_cmd_str
        pin = 10
        position = 0
        angle = 90
        # Attach first.
        self.mock_serial.push_line(position)
        self.board.Servos.attach(pin)
        self.mock_serial.reset_mock()
        self.mock_serial.push_line(angle)
        self.assertEquals(self.board.Servos.read(pin), angle)
        self.assertEquals(self.mock_serial.output[0],
            build_cmd_str("svr", (position,)))


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_main
import logging
import unittest
import time

"""
A collection of some basic tests for the Arduino library.

Extensive coverage is a bit difficult, since a positive test involves actually
connecting and issuing commands to a live Arduino, hosting any hardware
required to test a particular function. But a core of basic communication tests
should at least be maintained here.
"""


logging.basicConfig(level=logging.DEBUG)


class TestBasics(unittest.TestCase):

    def test_find(self):
        """ Tests auto-connection/board detection. """
        raw_input(
            'Plug in Arduino board w/LED at pin 13, reset, then press enter')
        from Arduino import Arduino
        board = None
        try:
            # This will trigger automatic port resolution.
            board = Arduino(9600)
        finally:
            if board:
                board.close()

    def test_open(self):
        """ Tests connecting to an explicit port. """
        port = None
        while not port:
            port = raw_input(
                'Plug in Arduino board w/LED at pin 13, reset.\n'\
                'Enter the port where the Arduino is connected, then press enter:')
            if not port:
                print 'You must enter a port.'
        from Arduino import Arduino
        board = None
        try:
            board = Arduino(9600, port=port)
        finally:
            if board:
                board.close()

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
