__FILENAME__ = demo
#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4
# see LICENSE file (it's BSD)


import time
from pygsm import GsmModem


class CountLettersApp(object):
    def __init__(self, modem):
        self.modem = modem

    def incoming(self, msg):
        msg.respond("Thanks for those %d characters!" %\
            len(msg.text))

    def serve_forever(self):
        while True:
            print "Checking for message..."
            msg = self.modem.next_message()

            if msg is not None:
                print "Got Message: %r" % (msg)
                self.incoming(msg)

            time.sleep(2)


# all arguments to GsmModem.__init__ are optional, and passed straight
# along to pySerial. for many devices, this will be enough:
gsm = GsmModem(
    port="/dev/ttyUSB0",
    logger=GsmModem.debug_logger).boot()


print "Waiting for network..."
s = gsm.wait_for_network()


# start the demo app
app = CountLettersApp(gsm)
app.serve_forever()

########NEW FILE########
__FILENAME__ = errors
#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4
# see LICENSE file (it's BSD)


import serial


class GsmError(serial.SerialException):
    pass


class GsmConnectError(GsmError):
    pass


class GsmIOError(GsmError):
    pass


class GsmWriteError(GsmIOError):
    pass


class GsmReadError(GsmIOError):
    pass


class GsmReadTimeoutError(GsmReadError):
    def __init__(self, pending_data):
        self.pending_data = pending_data


class GsmParseError(GsmReadError):
    def __init__(self, data):
        self.data = data

    def __str__(self):
        return "Couldn't parse: %s" %\
            (self.data)


class GsmModemError(GsmError):

    # strings and error codes seem to vary a bit by vendor,
    # but they're sort-of standard. for a good reference, see:
    # http://www.activexperts.com/xmstoolkit/sms/gsmerrorcodes/

    STRINGS = {
        "CME": {
            3:   "Operation not allowed",
            4:   "Operation not supported",
            5:   "PH-SIM PIN required (SIM lock)",
            10:  "SIM not inserted",
            11:  "SIM PIN required",
            12:  "SIM PUK required",
            13:  "SIM failure",
            14:  "SIM busy",
            16:  "Incorrect password",
            17:  "SIM PIN2 required",
            18:  "SIM PUK2 required",
            20:  "Memory full",
            21:  "Invalid index",
            22:  "Not found",
            24:  "Text string too long",
            26:  "Dial string too long",
            27:  "Invalid characters in dial string",
            30:  "No network service",
            32:  "Network not allowed. Emergency calls only",
            40:  "Network personal PIN required (Network lock)",
            103: "Illegal MS (#3)",
            106: "Illegal ME (#6)",
            107: "GPRS services not allowed",
            111: "PLMN not allowed",
            112: "Location area not allowed",
            113: "Roaming not allowed in this area",
            132: "Service option not supported",
            133: "Requested service option not subscribed",
            134: "Service option temporarily out of order",
            148: "unspecified GPRS error",
            149: "PDP authentication failure",
            150: "Invalid mobile class" },

        "CMS": {
            021: "Call Rejected (out of credit?)",
            301: "SMS service of ME reserved",
            302: "Operation not allowed",
            303: "Operation not supported",
            304: "Invalid PDU mode parameter",
            305: "Invalid text mode parameter",
            310: "SIM not inserted",
            311: "SIM PIN required",
            312: "PH-SIM PIN required",
            313: "SIM failure",
            316: "SIM PUK required",
            317: "SIM PIN2 required",
            318: "SIM PUK2 required",
            321: "Invalid memory index",
            322: "SIM memory full",
            330: "SC address unknown",
            340: "No +CNMA acknowledgement expected",
            500: "Unknown error",
            512: "MM establishment failure (for SMS)",
            513: "Lower layer failure (for SMS)",
            514: "CP error (for SMS)",
            515: "Please wait, init or command processing in progress",
            517: "SIM Toolkit facility not supported",
            518: "SIM Toolkit indication not received",
            519: "Reset product to activate or change new echo cancellation algo",
            520: "Automatic abort about get PLMN list for an incomming call",
            526: "PIN deactivation forbidden with this SIM card",
            527: "Please wait, RR or MM is busy. Retry your selection later",
            528: "Location update failure. Emergency calls only",
            529: "PLMN selection failure. Emergency calls only",
            531: "SMS not send: the <da> is not in FDN phonebook, and FDN lock is enabled (for SMS)" }}

    def __init__(self, type=None, code=None):
        self.type = type
        self.code = code

    def __str__(self):
        if self.type and self.code:
            return "%s ERROR %d: %s" % (
                self.type, self.code,
                self.STRINGS[self.type][self.code])

        # no type and/or code were provided
        else: return "Unknown GSM Error"

########NEW FILE########
__FILENAME__ = gsmmodem
#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4
# see LICENSE file (it's BSD)


from __future__ import with_statement

import re, csv, datetime, time
import errors, message
import traceback
import StringIO
import threading

# arch: pacman -S python-pyserial
# debian: apt-get install pyserial
import serial

# Constants
CMGL_STATUS="REC UNREAD"
CMGL_MATCHER=re.compile(r'^\+CMGL: (\d+),"(.+?)","(.+?)",.*?,"(.+?)".*?$')


class GsmModem(object):
    """
    pyGSM is a Python module which uses pySerial to provide a nifty
    interface to send and receive SMS via a GSM Modem. It was ported
    from RubyGSM, and provides (almost) all of the same features. It's
    easy to get started:

      # create a GsmModem object:
      >>> modem = pygsm.GsmModem(port="/dev/ttyUSB0")

      # harass Evan over SMS:
      # (try to do this before 11AM)
      >>> modem.send_sms(*REDACTED*, "Hey, wake up!")

      # check for incoming SMS:
      >>> print modem.next_message()
      <pygsm.IncomingMessage from *REDACTED*: "Leave me alone!">

    pyGSM is distributed via GitHub:
    http://github.com/adammck/pygsm

    Bug reports (especially for
    unsupported devices) are welcome:
    http://github.com/adammck/pygsm/issues
    """


    # override these after init, and
    # before boot. they're not sanity
    # checked, so go crazy.
    cmd_delay = 0.1
    retry_delay = 2
    max_retries = 10
    _modem_lock = threading.RLock()


    def __init__(self, *args, **kwargs):
        """
        Create a GsmModem object. All of the arguments are passed along
        to serial.Serial.__init__ when GsmModem.connect is called. For
        all of the possible configration options, see:

        http://pyserial.wiki.sourceforge.net/pySerial#tocpySerial10

        Alternatively, a single 'device' kwarg can be passed, which
        overrides the default proxy-args-to-pySerial behavior. This is
        useful when testing, or wrapping the serial connection with some
        custom logic.

        NOTE: The serial connection isn't created until GsmModem.connect
        is called. It might still fail (but should raise GsmConnectError
        when it does so.)
        """

        if "logger" in kwargs:
            self.logger = kwargs.pop("logger")

        # if a ready-made device was provided, store it -- self.connect
        # will see that we're already connected, and do nothing. we'll
        # just assume it quacks like a serial port
        if "device" in kwargs:
            self.device = kwargs.pop("device")

            # if a device is given, the other args are never
            # used, so were probably included by mistake.
            if len(args) or len(kwargs):
                raise(TypeError("__init__() does not accept other arguments when a 'device' is given"))

        # for regular serial connections, store the connection args, since
        # we might need to recreate the serial connection again later
        else:
            self.device = None
            self.device_args = args
            self.device_kwargs = kwargs

        # to cache parts of multi-part messages
        # until the last part is delivered
        self.multipart = {}

        # to store unhandled incoming messages
        self.incoming_queue = []


    LOG_LEVELS = {
        "traffic": 4,
        "read":    4,
        "write":   4,
        "debug":   3,
        "warn":    2,
        "error":   1 }


    def _log(self, msg_str, event_type="debug"):
        """
        Proxy a log message to this Modem's logger, if one has been set.
        This is useful for applications embedding pyGSM that wish to
        show or log what's going on inside.

        The 'logger' should be a function with three arguments:
            modem:      a reference to this GsmModem instance
            msg_str:    the log message (a unicode string)
            event_type: a string contaning one of the keys
                        of GsmModem.LOG_LEVELS, indicating
                        the importance of this message.

        GsmModem.__init__ accepts an optional 'logger' kwarg, and a
        minimal (dump to STDOUT) logger is at GsmModem.debug_logger:

        >>> GsmModem("/dev/ttyUSB0", logger=GsmModem.debug_logger)
        """

        if hasattr(self, "logger"):
            self.logger(self, msg_str, event_type)


    @classmethod
    def debug_logger(cls, modem, msg_str, event_type):
        print "%8s %s" % (event_type, msg_str)


    def connect(self, reconnect=False):
        """
        Connect to the modem via pySerial, using the args and kwargs
        provided to the constructor. If 'reconnect' is True, and the
        modem is already connected, the entire serial.Serial object is
        destroyed and re-established.

        Returns self.device, or raises GsmConnectError
        """

        self._log("Connecting")

        # if no connection exists, create it
        # the reconnect flag is irrelevant
        if not hasattr(self, "device") or (self.device is None):
            try:
                with self._modem_lock:
                    self.device = serial.Serial(
                        *self.device_args,
                        **self.device_kwargs)

            # if the connection failed, re-raise the serialexception as
            # a gsm error, so the owner of this object doesn't have to
            # worry about catching anything other than gsm exceptions
            except serial.SerialException, err:
                msg = str(err)
                if msg.startswith("could not open port"):
                    pyserial_err, real_err = msg.split(":", 1)
                    raise errors.GsmConnectError(real_err.strip())

                # other (more obscure) errors don't get their own class,
                # but wrap them in a gsmerror all the same
                else:
                    raise errors.GsmError(msg)

        # the port already exists, but if we're
        # reconnecting, then kill it and recurse
        # to recreate it. this is useful when the
        # connection has died, but nobody noticed
        elif reconnect:
            self.disconnect()
            self.connect(False)

        return self.device


    def disconnect(self):
        """Disconnect from the modem."""

        self._log("Disconnecting")

        # attempt to close and destroy the device
        if hasattr(self, "device") and (self.device is None):
            with self._modem_lock:
                if self.device.isOpen():
                    self.device.close()
                    self.device = None
                    return True

        # for some reason, the device
        # couldn't be closed. it probably
        # just isn't open yet
        return False


    def boot(self, reboot=False):
        """
        (Re-)Connect to the modem and configure it in an (often vain)
        attempt to standardize the behavior of the many vendors and
        models. Should be called before reading or writing.

        This method isn't called during __init__ (since 5f41ba6d), since
        it's often useful to create GsmModem objects without writing to
        the modem. To compensate, this method returns 'self', so it can
        be easily chained onto the constructor, like so:

        >>> gsm = GsmModem(port="whatever").boot()

        This is exactly the same as:

        >>> gsm = GsmModem(port="whatever")
        >>> gsm.boot()
        """

        self._log("Booting")

        if reboot:
            self.connect(reconnect=True)
            self.command("AT+CFUN=1")

        else:
            self.connect()

        # set some sensible defaults, to make
        # the various modems more consistant
        self.command("ATE0",      raise_errors=False) # echo off
        self.command("AT+CMEE=1", raise_errors=False) # useful error messages
        self.command("AT+WIND=0", raise_errors=False) # disable notifications
        self.command("AT+CMGF=1"                    ) # switch to TEXT mode

        return self
        # enable new message notification. (most
        # handsets don't support this; no matter)
        #self.command(
        #    "AT+CNMI=2,2,0,0,0",
        #    raise_errors=False)


    def reboot(self):
        """
        Disconnect from the modem, reconnect, and reboot it (AT+CFUN=1,
        which clears all volatile state). This drops the connection to
        the network, so it's wise to call _GsmModem.wait_for_network_
        after rebooting.
        """

        self.boot(reboot=True)


    def _write(self, str_):
        """Write a string to the modem."""

        self._log(repr(str_), "write")

        try:
            self.device.write(str_)

        # if the device couldn't be written to,
        # wrap the error in something that can
        # sensibly be caught at a higher level
        except OSError, err:
            raise(errors.GsmWriteError)


    def _read(self, read_term=None, read_timeout=None):
        """
        Keep reading and buffering characters from the modem (blocking)
        until 'read_term' (which defaults to \r\n, to read a single
        "line") is hit, then return the buffer.
        """

        buffer = []

        # if a different timeout was requested just
        # for _this_ read, store and override the
        # current device setting (not thread safe!)
        if read_timeout is not None:
            old_timeout = self.device.timeout
            self.device.timeout = read_timeout

        def __reset_timeout():
            """restore the device's previous timeout
               setting, if we overrode it earlier."""
            if read_timeout is not None:
                self.device.timeout =\
                    old_timeout

        # the default terminator reads
        # until a newline is hit
        if not read_term:
            read_term = "\r\n"

        while(True):
            buf = self.device.read()
            buffer.append(buf)

            # if a timeout was hit, raise an exception including the raw data that
            # we've already read (in case the calling func was _expecting_ a timeout
            # (wouldn't it be nice if serial.Serial.read returned None for this?)
            if buf == "":
                __reset_timeout()
                raise(errors.GsmReadTimeoutError(buffer))

            # if last n characters of the buffer match the read
            # terminator, return what we've received so far
            if buffer[-len(read_term)::] == list(read_term):
                buf_str = "".join(buffer)
                __reset_timeout()

                self._log(repr(buf_str), "read")
                return buf_str


    def _wait(self, read_term=None, read_timeout=None):
        """
        Read (blocking) from the modem, one line at a time, until a
        response terminator ("OK", "ERROR", or "CMx ERROR...") is hit,
        then return a list containing the lines.
        """

        buffer = []

        # keep on looping until a response terminator
        # is encountered. these are NOT the same as the
        # "read_term" argument - only OK or ERROR is valid
        while(True):
            buf = self._read(
                read_term=read_term,
                read_timeout=read_timeout)

            buf = buf.strip()
            buffer.append(buf)

            # most commands return OK for success, but there
            # are some exceptions. we're not checking those
            # here (unlike RubyGSM), because they should be
            # handled when they're _expected_
            if buf == "OK":
                return buffer

            # some errors contain useful error codes, so raise a
            # proper error with a description from pygsm/errors.py
            m = re.match(r"^\+(CM[ES]) ERROR: (\d+)$", buf)
            if m is not None:
                type, code = m.groups()
                raise(errors.GsmModemError(type, int(code)))

            # ...some errors are not so useful
            # (at+cmee=1 should enable error codes)
            if buf == "ERROR":
                raise(errors.GsmModemError)

            # some (but not all) huawei e220s (an otherwise splendid
            # modem) return this useless and non-standard error
            if buf == "COMMAND NOT SUPPORT":
                raise(errors.GsmModemError)


    _SCTS_FMT = "%y/%m/%d,%H:%M:%S"

    def _parse_incoming_timestamp(self, timestamp):
        """
        Parse a Service Center Time Stamp (SCTS) string into a Python
        datetime object, or None if the timestamp couldn't be parsed.
        The SCTS format does not seem to be standardized, but looks
        something like: YY/MM/DD,HH:MM:SS.
        """

        # timestamps usually have trailing timezones, measured
        # in 15-minute intervals (?!), which is not handled by
        # python's datetime lib. if _this_ timezone does, chop
        # it off, and note the actual offset in minutes
        tz_pattern = r"\-(\d+)$"
        m = re.search(tz_pattern, timestamp)
        if m is not None:
            timestamp = re.sub(tz_pattern, "", timestamp)
            tz_offset = datetime.timedelta(minutes=int(m.group(0)) * 15)

        # we won't be modifying the output, but
        # still need an empty timedelta to subtract
        else: tz_offset = datetime.timedelta()

        # attempt to parse the (maybe modified) timestamp into
        # a time_struct, and convert it into a datetime object
        try:
            time_struct = time.strptime(timestamp, self._SCTS_FMT)
            dt = datetime.datetime(*time_struct[:6])

            # patch the time to represent LOCAL TIME, since
            # the datetime object doesn't seem to represent
            # timezones... at all
            return dt - tz_offset

        # if the timestamp couldn't be parsed, we've encountered
        # a format the pyGSM doesn't support. this sucks, but isn't
        # important enough to explode like RubyGSM does
        except ValueError:
            return None


    def _parse_incoming_sms(self, lines):
        """
        Parse a list of 'lines' (output of GsmModem._wait), to extract
        any incoming SMS and append them to _GsmModem.incoming_queue_.
        Returns the same lines with the incoming SMS removed. Other
        unsolicited data may remain, which must be cropped separately.
        """

        output_lines = []
        n = 0

        # iterate the lines like it's 1984
        # (because we're patching the array,
        # which is hard work for iterators)
        while n < len(lines):

            # not a CMT string? add it back into the
            # output (since we're not interested in it)
            # and move on to the next
            if lines[n][0:5] != "+CMT:":
                output_lines.append(lines[n])
                n += 1
                continue

            # since this line IS a CMT string (an incoming
            # SMS), parse it and store it to deal with later
            m = re.match(r'^\+CMT: "(.+?)",.*?,"(.+?)".*?$', lines[n])
            if m is None:

                # couldn't parse the string, so just move
                # on to the next line. TODO: log this error
                n += 1
                next

            # extract the meta-info from the CMT line,
            # and the message from the FOLLOWING line
            sender, timestamp = m.groups()
            text = lines[n+1].strip()

            # notify the network that we accepted
            # the incoming message (for read receipt)
            # BEFORE pushing it to the incoming queue
            # (to avoid really ugly race condition if
            # the message is grabbed from the queue
            # and responded to quickly, before we get
            # a chance to issue at+cnma)
            try:
                self.command("AT+CNMA")

            # Some networks don't handle notification, in which case this
            # fails. Not a big deal, so ignore.
            except errors.GsmError:
                #self.log("Receipt acknowledgement (CNMA) was rejected")
                # TODO: also log this!
                pass

            # (i'm using while/break as an alternative to catch/throw
            # here, since python doesn't have one. we might abort early
            # if this is part of a multi-part message, but not the last
            while True:

                # multi-part messages begin with ASCII 130 followed
                # by "@" (ASCII 64). TODO: more docs on this, i wrote
                # this via reverse engineering and lost my notes
                if (ord(text[0]) == 130) and (text[1] == "@"):
                    part_text = text[7:]

                    # ensure we have a place for the incoming
                    # message part to live as they are delivered
                    if sender not in self.multipart:
                        self.multipart[sender] = []

                    # append THIS PART
                    self.multipart[sender].append(part_text)

                    # abort if this is not the last part
                    if ord(text[5]) != 173:
                        break

                    # last part, so switch out the received
                    # part with the whole message, to be processed
                    # below (the sender and timestamp are the same
                    # for all parts, so no change needed there)
                    text = "".join(self.multipart[sender])
                    del self.multipart[sender]

                # store the incoming data to be picked up
                # from the attr_accessor as a tuple (this
                # is kind of ghetto, and WILL change later)
                self._add_incoming(timestamp, sender, text)

                # don't loop! the only reason that this
                # "while" exists is to jump out early
                break

            # jump over the CMT line, and the
            # text line, and continue iterating
            n += 2

        # return the lines that we weren't
        # interested in (almost all of them!)
        return output_lines


    def _add_incoming(self, timestamp, sender, text):

        # since neither message notifications nor messages
        # fetched from storage give any indication of their
        # encoding, we're going to have to guess. if the
        # text has a multiple-of-four length and starts
        # with a UTF-16 Byte Order Mark, try to decode it
        # into a unicode string
        try:
            if (len(text) % 4 == 0) and (len(text) > 0):
                if re.match('^[0-9A-F]+$', text):

                    # insert a bom if there isn't one
                    bom = text[:4].lower()
                    if bom != "fffe" and bom != "feff":
                        text = "feff" + text

                    # decode the text into a unicode string,
                    # so developers embedding pyGSM need never
                    # experience this confusion and pain
                    text = text.decode("hex").decode("utf-16")

        # oh dear. it looked like hex-encoded utf-16,
        # but wasn't. who sends a message like that?!
        except:
            pass

        # create and store the IncomingMessage object
        self._log("Adding incoming message")
        time_sent = self._parse_incoming_timestamp(timestamp)
        msg = message.IncomingMessage(self, sender, time_sent, text)
        self.incoming_queue.append(msg)
        return msg


    def command(self, cmd, read_term=None, read_timeout=None, write_term="\r", raise_errors=True):
        """
        Issue an AT command to the modem, and return the sanitized
        response. Sanitization removes status notifications, command
        echo, and incoming messages, (hopefully) leaving only the actual
        response to the command.

        If Error 515 (init or command in progress) is returned, the
        command is automatically retried up to 'GsmModem.max_retries'
        times.
        """

        # keep looping until the command
        # succeeds or we hit the limit
        retries = 0
        while retries < self.max_retries:
            try:

                # issue the command, and wait for the
                # response
                with self._modem_lock:
                    self._write(cmd + write_term)
                    lines = self._wait(
                        read_term=read_term,
                        read_timeout=read_timeout)

                # no exception was raised, so break
                # out of the enclosing WHILE loop
                break

            # Outer handler: if the command caused an error,
            # maybe wrap it and return None
            except errors.GsmError, err:

                # if GSM Error 515 (init or command in progress) was raised,
                # lock the thread for a short while, and retry. don't lock
                # the modem while we're waiting, because most commands WILL
                # work during the init period - just not _cmd_
                if getattr(err, "code", None) == 515:
                    time.sleep(self.retry_delay)
                    retries += 1
                    continue

                # if raise_errors is disabled, it doesn't matter
                # *what* went wrong - we'll just ignore it
                if not raise_errors:
                    return None

                # otherwise, allow errors to propagate upwards,
                # and hope someone is waiting to catch them
                else: raise(err)

        # if the first line of the response echoes the cmd
        # (it shouldn't, if ATE0 worked), silently drop it
        if lines[0] == cmd:
            lines.pop(0)

        # remove all blank lines and unsolicited
        # status messages. i can't seem to figure
        # out how to reliably disable them, and
        # AT+WIND=0 doesn't work on this modem
        lines = [
            line
            for line in lines
            if line      != "" or\
               line[0:6] == "+WIND:" or\
               line[0:6] == "+CREG:" or\
               line[0:7] == "+CGRED:"]

        # parse out any incoming sms that were bundled
        # with this data (to be fetched later by an app)
        lines = self._parse_incoming_sms(lines)

        # rest up for a bit (modems are
        # slow, and get confused easily)
        time.sleep(self.cmd_delay)

        return lines


    def query_list(self, cmd, prefix=None):
        """
        Issue a single AT command to the modem, checks that the last
        line of the response is "OK", and returns a list containing the
        other lines. An empty list is returned if a command fails, so
        the output of this method can always be assumed to be iterable.

        The 'prefix' argument can optionally specify a string to filter
        the output lines by. Matching lines are returned (sans prefix),
        and the rest are dropped.

        Most AT commands return a single line, which is better handled
        by GsmModem.query, which returns a single value.
        """

        # issue the command, which might return incoming
        # messages, but we'll leave them in the queue
        lines = self.command(cmd, raise_errors=False)

        # check that the query was successful
        # if not, we'll skip straight to return
        if lines is not None and lines[-1] == "OK":

            # if a prefix was provided, return all of the
            # lines (except for OK) that start with _prefix_
            if prefix is not None:
                return [
                    line[len(prefix):].strip()
                    for line in lines[:-1]
                    if line[:len(prefix)] == prefix]

            # otherwise, return all lines
            # (except for the trailing OK)
            else:
                return lines[:-1]

        # something went wrong, so return the very
        # ambiguous None. it's better than blowing up
        return None


    def query(self, cmd, prefix=None):
        """
        Issue an AT command to the modem, and returns the relevant part
        of the response. This only works for commands that return a
        single line followed by "OK", but conveniently, this covers
        almost all AT commands that I've ever needed to use. Example:

        >>> modem.query("AT+CSQ")
        "+CSQ: 20,99"

        Optionally, the 'prefix' argument can specify a string to check
        for at the beginning of the output, and strip it from the return
        value. This is useful when you want to both verify that the
        output was as expected, but ignore the prefix. For example:

        >>> modem.query("AT+CSQ", prefix="+CSQ:")
        "20,99"

        For all unexpected responses (errors, no output, or too much
        output), returns None.
        """

        lines = self.query_list(cmd, prefix)
        return lines[0] if len(lines) == 1 else None


    def _csv_str(self, out):
        """
        Many queries will return comma-separated output, which is not
        formally specified (far as I can tell), but strongly resembles
        CSV. This method splits the output of self.query into a list. No
        typecasting is performed on the elements -- they're all strings,
        as returned by the Python CSV module. For example:

        >>> modem.query("AT+COPS?", prefix="+COPS:", split_output=True)
        ["0", "0", "MTN Rwanda", "2"]

        If the string couldn't be parsed, GsmParseError is raised.
        """

        try:
            # parse the query output as if it were a single-line
            # csv file. override line terminator in case there
            # are any \r\n terminators within the output
            reader = csv.reader([out], lineterminator="\0\0")

            # attempt to return the parsed row. this will raise
            # an internal _csv.Error exception if the string is
            # badly formed, which we will wrap, below
            return list(reader)[0]

        except:
            raise errors.GsmParseError(out)


    def send_sms(self, recipient, text):
        """
        Send an SMS to 'recipient' containing 'text'. Some networks will
        automatically split long messages into multiple parts, and join
        them upon delivery -- but some will silently drop them. pyGSM
        does nothing to avoid this (for now), so try to keep 'text'
        under 160 characters.
        """

        old_mode = None
        with self._modem_lock:
            try:
                try:
                    # cast the text to a string, to check that
                    # it doesn't contain non-ascii characters
                    try:
                        text = str(text)

                    # uh-oh. unicode ahoy
                    except UnicodeEncodeError:

                        # fetch and store the current mode (so we can
                        # restore it later), and override it with UCS2
                        csmp = self.query("AT+CSMP?", "+CSMP:")
                        if csmp is not None:
                            old_mode = csmp.split(",")
                            mode = old_mode[:]
                            mode[3] = "8"

                            # enable hex mode, and set the encoding
                            # to UCS2 for the full character set
                            self.command('AT+CSCS="HEX"')
                            self.command("AT+CSMP=%s" % ",".join(mode))
                            text = text.encode("utf-16").encode("hex")

                    # initiate the sms, and give the device a second
                    # to raise an error. unfortunately, we can't just
                    # wait for the "> " prompt, because some modems
                    # will echo it FOLLOWED BY a CMS error
                    result = self.command(
                        'AT+CMGS=\"%s\"' % (recipient),
                        read_timeout=1)

                # if no error is raised within the timeout period,
                # and the text-mode prompt WAS received, send the
                # sms text, wait until it is accepted or rejected
                # (text-mode messages are terminated with ascii char 26
                # "SUBSTITUTE" (ctrl+z)), and return True (message sent)
                except errors.GsmReadTimeoutError, err:
                    if err.pending_data[0] == ">":
                        self.command(text, write_term=chr(26))
                        return True

                    # a timeout was raised, but no prompt nor
                    # error was received. i have no idea what
                    # is going on, so allow the error to propagate
                    else:
                        raise

            # for all other errors...
            # (likely CMS or CME from device)
            except Exception, err:

                # whatever went wrong, break out of the
                # message prompt. if this is missed, all
                # subsequent writes will go into the message!
                self._write(chr(27))

                # rule of thumb: pyGSM is meant to be embedded,
                # so DO NOT EVER allow exceptions to propagate
                # (obviously, this sucks. there should be an
                # option, at least, but i'm being cautious)
                return None

            finally:

                # if the mode was overridden above, (if this
                # message contained unicode), switch it back
                if old_mode is not None:
                    self.command("AT+CSMP=%s" % ",".join(old_mode))
                    self.command('AT+CSCS="GSM"')


    def hardware(self):
        """
        Return a dict of containing information about the modem. The
        contents of each value are entirely manufacturer-dependant, and
        can vary wildly between devices.
        """

        return {
            "manufacturer": self.query("AT+CGMI"),
            "model":        self.query("AT+CGMM"),
            "revision":     self.query("AT+CGMR"),
            "serial":       self.query("AT+CGSN") }


    def _get_service_center(self):

        # fetch the current service center,
        # which returns something like:
        # +CSCA: "+250788110333",145
        data = self.query("AT+CSCA?")
        if data is not None:

            # extract the service center number
            # (the first argument) from the output
            md = re.match(r'^\+CSCA:\s+"(\+?\d+)",', data)
            if md is not None:
                return md.group(1)

        # if we have not returned yet, something
        # went wrong. this modem probably doesn't
        # support AT+CSCA, so return None/unknown
        return None

    def _set_service_center(self, value):
        self.command(
            'AT+CSCA="%s"' % value,
            raise_errors=False)

    # allow the service center to be get or set like an attribute,
    # while transparently reconfiguring the modem behind the scenes
    service_center =\
        property(
            _get_service_center,
            _set_service_center,
            doc=\
        """
        Get or set the service center address currently in use by the
        modem. Returns None if the modem does not support the AT+CSCA
        command.
        """)


    @property
    def _known_networks(self):
        """
        Return a dict containing all networks known to this modem, keyed
        by their numeric ID, valued by their alphanumeric operator name.
        This is not especially useful externally, but is used internally
        to resolve operator IDs to their alphanumeric name.

        Many devices can do this internally, via the AT+WOPN command,
        but the Huawei dongle I'm on today happens not to support that,
        and I expect many others are the same.

        This method will always return a dict (even if it's empty), and
        caches its own output, since it can be quite slow and large.
        """

        # if the cache hasn't already been built, do so
        if not hasattr(self, "_known_networks_cache"):
            self._known_networks_cache = {}

            try:

                # fetch a list of ALL networks known to this modem,
                # which returns a CME error (caught below) or many
                # lines in the format:
                #   +COPN: <NumOper>, <AlphaOper>
                #   +COPN: <NumOper>, <AlphaOper>
                #   ...
                #   OK
                #
                # where <NumOper> is the numeric operator ID
                # where <AlphaOper> is long alphanumeric operator name
                lines = self.query_list("AT+COPN", "+COPN:")

                # parse each line into a two-element
                # array, and cast the result to a dict
                self._known_networks_cache =\
                    dict(map(self._csv_str, lines))

            # if anything went wrong (and many things can)
            # during this operation, we will return the empty,
            # dict to indicate that we don't know _any_ networks
            except errors.GsmError:
                pass

        return self._known_networks_cache


    _PLMN_MODES = {
        "0": "(Automatic)",
        "1": "(Manual)",
        "2": "(Deregistered)",
        "3": "(Unreadable)"
    }

    @property
    def network(self):
        """
        Return the name of the currently selected GSM network.
        """

        # fetch the current PLMN (Public Land Mobile Network)
        # setting, which should return something like:
        #   +COPS: <mode> [, <format>, <oper>]
        #
        # where <mode> is one of:
        #   0 - automatic (default)
        #   1 - manual
        #   2 - deregistered
        #   3 - set only (the network cannot be read, only set)
        #
        # where <format> is one of:
        #   0 - long alphanumeric
        #   1 - short alphanumeric
        #   2 - numeric (default)
        #
        # and <oper> is the operator identifier in the format
        # specified by <format>

        data = self.query("AT+COPS?", "+COPS:")
        if data is not None:

            # parse the csv-style output
            fields = self._csv_str(data)

            # if the operator fields weren't returned (ie, "+COPS: 0"),
            # just return a rough description of what's going on
            if len(fields) == 1:
                return self._PLMN_MODES[fields[0]]

            # if the <oper> was in long or short alphanumerics,
            # (according to <format>), return it as-is. this
            # happens when the network is unknown to the modem
            elif fields[1] in ["0", "1"]:
                return fields[2]

            # if the <oper> was numeric, we're going to
            # have to look up the PLMN string separately.
            # return if it's known, or fall through to None
            elif fields[1] == "2":
                network_id = fields[2]
                if network_id in self._known_networks:
                    return self._known_networks[network_id]

        # if we have not returned yet, something wernt
        # wrong during the query or parsing the response
        return None


    def signal_strength(self):
        """
        Return an integer between 1 and 99, representing the current
        signal strength of the GSM network, False if we don't know, or
        None if the modem can't report it.
        """

        data = self.query("AT+CSQ")
        if data is not None:

            # extract the signal strength (the
            # first argument) from the output
            md = re.match(r"^\+CSQ: (\d+),", data)

            # 99 represents "not known or not detectable". we'll
            # return False for that (so we can test it for boolean
            # equality), or an integer of the signal strength.
            if md is not None:
                csq = int(md.group(1))
                return csq if csq < 99 else False

        # the response from AT+CSQ couldn't be parsed. return
        # None, so we can test it in the same way as False, but
        # check the type without raising an exception
        return None


    def wait_for_network(self):
        """
        Block until the signal strength indicates that the device is
        active on the GSM network. It's a good idea to call this before
        trying to send or receive anything.
        """

        while True:
            csq = self.signal_strength()
            if csq: return csq
            time.sleep(1)


    def ping(self):
        """
        Send the "AT" command to the device, and return true if it is
        acknowledged. Since incoming notifications and messages are
        intercepted automatically, this is a good way to poll for new
        messages without using a worker thread like RubyGSM.
        """

        try:
            self.command("AT")
            return True

        except errors.GsmError:
            return None


    def _strip_ok(self,lines):
        """
        Strip "OK" from the end of a command response. But DON'T USE
        THIS. Parse the response properly.
        """

        if lines is not None and len(lines)>0 and \
                lines[-1]=='OK':
            lines=lines[:-1] # strip last entry
        return lines


    def _fetch_stored_messages(self):
        """
        Fetch stored unread messages, and add them to incoming queue.
        Return number fetched.
        """

        lines = self._strip_ok(self.command('AT+CMGL="%s"' % CMGL_STATUS))
        # loop through all the lines attempting to match CMGL lines (the header)
        # and then match NOT CMGL lines (the content)
        # need to seed the loop first
        num_found=0
        if len(lines)>0:
            m=CMGL_MATCHER.match(lines[0])

        while len(lines)>0:
            if m is None:
                # couldn't match OR no text data following match
                raise(errors.GsmReadError())

            # if here, we have a match AND text
            # start by popping the header (which we have stored in the 'm'
            # matcher object already)
            lines.pop(0)

            # now put the captures into independent vars
            index, status, sender, timestamp = m.groups()

            # now loop through, popping content until we get
            # the next CMGL or out of lines
            msg_buf=StringIO.StringIO()
            while len(lines)>0:
                m=CMGL_MATCHER.match(lines[0])
                if m is not None:
                    # got another header, get out
                    break
                else:
                    msg_buf.write(lines.pop(0))

            # get msg text
            msg_text=msg_buf.getvalue().strip()

            # now create message
            self._add_incoming(timestamp,sender,msg_text)
            num_found+=1

        return num_found


    def next_message(self, ping=True, fetch=True):
        """
        Returns the next waiting IncomingMessage object, or None if the
        queue is empty. The optional 'ping' and 'fetch' args control
        whether the modem is pinged (to allow new messages to be
        delivered instantly, on those modems which support it) and
        queried for unread messages in storage, which can both be
        disabled in case you're already polling in a separate thread.
        """

        # optionally ping the modem, to give it a
        # chance to deliver any waiting messages
        if ping:
            self.ping()

        # optionally check the storage for unread messages.
        # we must do this just as often as ping, because most
        # handsets don't support CNMI-style delivery
        if fetch:
            self._fetch_stored_messages()

        # abort if there are no messages waiting
        if not self.incoming_queue:
            return None

        # remove the message that has been waiting
        # longest from the queue, and return it
        return self.incoming_queue.pop(0)




if __name__ == "__main__":

    import sys, re
    if len(sys.argv) >= 2:

        # the first argument is SERIAL PORT
        # (required, since we have no autodetect yet)
        port = sys.argv[1]

        # all subsequent options are parsed as key=value
        # pairs, to be passed on to GsmModem.__init__ as
        # kwargs, to configure the serial connection
        conf = dict([
            arg.split("=", 1)
            for arg in sys.argv[2:]
            if arg.find("=") > -1
        ])

        # dump the connection settings
        print "pyGSM Demo App"
        print "  Port: %s" % (port)
        print "  Config: %r" % (conf)
        print

        # connect to the modem (this might hang
        # if the connection settings are wrong)
        print "Connecting to GSM Modem..."
        modem = GsmModem(port=port, **conf).boot()
        print "Waiting for incoming messages..."

        # check for new messages every two
        # seconds for the rest of forever
        while True:
            msg = modem.next_message()

            # we got a message! respond with
            # something useless, as an example
            if msg is not None:
                print "Got Message: %r" % msg
                msg.respond("Thanks for those %d characters!" %
                    len(msg.text))

            # no messages? wait a couple
            # of seconds and try again
            else: time.sleep(2)

    # the serial port must be provided
    # we're not auto-detecting, yet
    else:
        print "Usage: python -m pygsm.gsmmodem PORT [OPTIONS]"

########NEW FILE########
__FILENAME__ = incoming
#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4
# see LICENSE file (it's BSD)


import datetime


class IncomingMessage(object):
    def __init__(self, device, sender, sent, text):

        # move the arguments into "private" attrs,
        # to try to prevent from from being modified
        self._device = device
        self._sender = sender
        self._sent   = sent
        self._text   = text

        # assume that the message was
        # received right now, since we
        # don't have an incoming buffer
        self._received = datetime.datetime.now()


    def __repr__(self):
        return "<pygsm.IncomingMessage from %s: %r>" %\
            (self.sender, self.text)


    def respond(self, text):
        """Responds to this IncomingMessage by sending a message containing
           _text_ back to the sender via the modem that created this object."""
        return self.device.send_sms(self.sender, text)


    @property
    def device(self):
        """Returns the pygsm.GsmModem device which received
           the SMS, and created this IncomingMessage object."""
        return self._device

    @property
    def sender(self):
        """Returns the phone number of the originator of this IncomingMessage.
           It is stored directly as reported by the modem, so no assumptions
           can be made about it's format."""
        return self._sender

    @property
    def sent(self):
        """Returns a datetime object containing the date and time that this
           IncomingMessage was sent, as reported by the modem. Sometimes, a
           network or modem will not report this field, so it will be None."""
        return self._sent

    @property
    def text(self):
        """Returns the text contents of this IncomingMessage. It will usually
           be 160 characters or less, by virtue of being an SMS, but multipart
           messages can, technically, be up to 39015 characters long."""
        return self._text

    @property
    def received(self):
        """Returns a datetime object containing the date and time that this
           IncomingMessage was created, which is a close aproximation of when
           the SMS was received."""
        return self._received

########NEW FILE########
__FILENAME__ = outgoing
#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4
# see LICENSE file (it's BSD)


class OutgoingMessage(object):
    pass

########NEW FILE########
__FILENAME__ = gsmmodem
#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4
# see LICENSE file (it's BSD)


import unittest
import pygsm

from mock.device import MockDevice, MockSenderDevice


class TestGsmModem(unittest.TestCase):

    def testWritesNothingDuringInit(self):
        """Nothing is written to the modem during __init__"""

        device = MockDevice()
        gsm = pygsm.GsmModem(device=device)
        self.assertEqual(device.buf_write, [])


    def testKnownOperatorkName(self):
        """Long operator names are returned as-is."""

        class MockCopsDevice(MockDevice):
            def process(self, cmd):

                # return a valid +COPS response for AT+COPS?, but error
                # for other commands (except built-in MockDevice stuff)
                if cmd == "AT+COPS?":
                    return self._respond('+COPS: 0,0,"MOCK-NETWORK",0')

                return False

        device = MockCopsDevice()
        gsm = pygsm.GsmModem(device=device)
        self.assertEqual(gsm.network, "MOCK-NETWORK")


    def testUnknownOperatorName(self):
        """Unknown or missing operator names return a status string."""

        class MockCopsDevice(MockDevice):
            def process(self, cmd):

                # return a valid +COPS response for AT+COPS?, but error
                # for other commands (except built-in MockDevice stuff)
                if cmd == "AT+COPS?":
                    return self._respond('+COPS: 0')

                return False

        device = MockCopsDevice()
        gsm = pygsm.GsmModem(device=device)
        self.assertEqual(gsm.network, "(Automatic)")


    def testSendSms(self):
        """Checks that the GsmModem accepts outgoing SMS,
           when the text is within ASCII chars 22 - 126."""

        # this device is much more complicated than
        # most, so is tucked away in mock.device
        device = MockSenderDevice()
        gsm = pygsm.GsmModem(device=device).boot()

        # send an sms, and check that it arrived safely
        gsm.send_sms("1234", "Test Message")
        self.assertEqual(device.sent_messages[0]["recipient"], "1234")
        self.assertEqual(device.sent_messages[0]["text"], "Test Message")


    def testRetryCommands(self):
        """Checks that the GsmModem automatically retries
           commands that fail with a CMS 515 error, and does
           not retry those that fail with other errors."""

        class MockBusyDevice(MockDevice):
            def __init__(self):
                MockDevice.__init__(self)
                self.last_cmd = None
                self.retried = []

            # this command is special (and totally made up)
            # it does not return 515 errors like the others
            def at_test(self, one):
                return True

            def process(self, cmd):

                # if this is the first time we've seen
                # this command, return a BUSY error to
                # (hopefully) prompt a retry
                if self.last_cmd != cmd:
                    self._output("+CMS ERROR: 515")
                    self.last_cmd = cmd
                    return None

                # the second time, note that this command was
                # retried, then fail. kind of anticlimatic
                self.retried.append(cmd)
                return False

        device = MockBusyDevice()
        gsm = pygsm.GsmModem(device=device)
        n = len(device.retried)

        # override the usual retry delay, to run the tests fast
        gsm.retry_delay = 0.01

        # boot the modem, and make sure that
        # some commands were retried (i won't
        # check _exactly_ how many, since we
        # change the boot sequence often)
        gsm.boot()
        self.assert_(len(device.retried) > n)

        # try the special AT+TEST command, which doesn't
        # fail - the number of retries shouldn't change
        n = len(device.retried)
        gsm.command("AT+TEST=1")
        self.assertEqual(len(device.retried), n)


    def testEchoOff(self):
        """Checks that GsmModem disables echo at some point
           during boot, to simplify logging and processing."""

        class MockEchoDevice(MockDevice):
            def process(self, cmd):

                # raise and error for any
                # cmd other than ECHO OFF
                if cmd != "ATE0":
                    return False

                self.echo = False
                return True

        device = MockEchoDevice()
        gsm = pygsm.GsmModem(device=device).boot()
        self.assertEqual(device.echo, False)


    def testUsefulErrors(self):
        """Checks that GsmModem attempts to enable useful errors
           during boot, to make the errors raised useful to humans.
           Many modems don't support this, but it's very useful."""

        class MockUsefulErrorsDevice(MockDevice):
            def __init__(self):
                MockDevice.__init__(self)
                self.useful_errors = False

            def at_cmee(self, error_mode):
                if error_mode == "1":
                    self.useful_errors = True 
                    return True

                elif error_mode == "0":
                    self.useful_errors = False
                    return True

                # invalid mode
                return False

        device = MockUsefulErrorsDevice()
        gsm = pygsm.GsmModem(device=device).boot()
        self.assertEqual(device.useful_errors, True)


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = incoming
#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4
# see LICENSE file (it's BSD)


import unittest
import pygsm


class TestIncomingMessage(unittest.TestCase):
    def testRespond(self):
        """
        Check that the IncomingMessage calls send_sms (with the correct
        arguments) when .respond is called.
        """

        caller   = "123"
        in_text  = "alpha"
        out_text = "beta"

        # this mock pygsm.gsmmodem does nothing, except note
        # down the parameters which .send_sms is called with
        class MockGsmModem(object):
            def __init__(self):
                self.sent_sms = []

            def send_sms(self, recipient, text):
                self.sent_sms.append({
                    "recipient": recipient,
                    "text": text
                })

        mock_gsm = MockGsmModem()

        # simulate an incoming message, and a respond to it
        msg = pygsm.message.IncomingMessage(mock_gsm, caller, None, in_text)
        msg.respond(out_text)

        # check that MockDevice.send_sms was called with
        # the correct args by IncomingMessage.respond
        self.assertEqual(mock_gsm.sent_sms[0]["recipient"], caller)
        self.assertEqual(mock_gsm.sent_sms[0]["text"], out_text)


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = device
#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4
# see LICENSE file (it's BSD)


import time, re


class MockDevice(object):

    print_traffic = False
    read_interval = 0.1
    mode = "PDU" # or TEXT
    echo = True


    def __init__(self):
        self.buf_read = []
        self.buf_write = []
        self.timeout = None


    def _debug(self, str):
        """If self.print_traffic is True, prints
           _str_ to STDOUT. Otherwise, does nothing."""

        if self.print_traffic:
            print str


    def read(self, size=1):
        """Reads and returns _size_ characters from the read buffer, which
           represents the output of the "serial port" of this "modem". This
           method is a very rough port of Serial.write. If the self.timeout
           attribute is set, this method may time out and return only as many
           characters as possible -- just like a modem."""

        waited = 0
        read = ""

        # keep on reading until we have _size_
        # number of characters/bytes
        while len(read) < size:
            if len(self.buf_read):
                read += self.buf_read.pop(0)

            else:
                # there's no data in the buffer. if we've
                # been waiting longer than self.timeout,
                # just return what we have
                if self.timeout and waited > self.timeout:
                    self._debug("TIMEOUT (%d)" % self.timeout)
                    break

                # otherwise, wait for a short while
                # before trying the buffer again
                time.sleep(self.read_interval)
                waited += self.read_interval

        self._debug("READ (%d): %r" % (size, read))
        return read


    def write(self, str):
        """Appends _str_ to the write buffer, which represents input to this "modem".
           If _str_ ends with a GSM command terminator (\r), the contents of the write
           buffer are passed on to self._process."""

        self._debug("WRITE: %r" % (str))

        # push each character
        # to the write buffer
        for char in str:
            self.buf_write.append(char)

            # if character echo is currently ON, also
            # push this character back to read buffer
            if self.echo:
                self.buf_read.append(char)

        # if the last character is a terminator, process
        # the current contents of the buffer, and clear it.
        # TODO: this doesn't work if "AT\rAT\rAT\r" if passed.
        if self.buf_write[-1] == "\r":
            self._process("".join(self.buf_write))
            self.buf_write = []

        return True


    def _process(self, cmd):
        """Receives a command, and passes it on to self.process, which should be defined
           by subclasses to respond to the command(s) which their testcase is interested
           in, and return True or False when done. If the call succeeds, this method will
           call self._ok -- otherwise, calls self._error."""

        self._debug("CMD: %r" % (cmd))

        # we can probably ignore whitespace,
        # even though a modem never would
        cmd = cmd.strip()
        
        # if this command looks like an AT+SOMETHING=VAL string (which most
        # do), check for an at_something method to handle the command. this
        # is bad, since mock modems should handle as little as possible (and
        # return ERROR for everything else), but some commands are _required_
        # (AT+CMGF=1 # switch to text mode) for anything to work.
        m = re.match(r"^AT\+([A-Z]+)=(.+)$", cmd)
        if m is not None:
            key, val = m.groups()
            method = "at_%s" % key.lower()

            # if the value is wrapped in "quotes", remove
            # them. this is sloppy, but we're only mocking
            val = val.strip('"')

            # call the method, and insert OK or ERROR into the
            # read buffer depending on the True/False output
            if hasattr(self, method):
                out = getattr(self, method)(val)
                return self._respond(out)

        # if this command looks like an AT+SOMETHING? string, check for
        # an at_something_query method to handle it, inject the output
        # into the read buffer, and respond with OK (most of the time)
        # or ERROR (if the method returns None or False)
        m = re.match(r"^AT\+([A-Z]+)\?$", cmd)
        if m is not None:
            method = "at_%s_query" %\
                m.group(0).lower()

            if hasattr(self, method):
                out = getattr(self, method)()
                return self._respond(out)

        # attempt to hand off this
        # command to the subclass
        if hasattr(self, "process"):
            out = self.process(cmd)
            return self._respond(out)

        # this modem has no "process" method,
        # or it was called and failed. either
        # way, report an unknown error
        return self._error()


    def at_cmgf(self, mode):
        """Switches this "modem" into PDU mode (0) or TEXT mode (1).
           Returns True for success, or False for unrecognized modes."""

        if mode == "0":
            self.mode = "PDU"
            return True

        elif mode == "1":
            self.mode = "TEXT"
            return True

        else:
            self.mode = None
            return False




    def _respond(self, out):
        """
        Inject the usual output from an AT command handler (at_*) into
        the read buffer, to save repeating it in every single handler.

        When 'out' is a str or unicode, it is injected verbatim,
        followed by OK. If it is a boolean, just OK (True) or ERROR
        (False) are injected. All other types are ignored.
        """

        # string responses are injected verbatim, followed by OK
        # (i've never seen an ERROR preceeded by output.)
        if isinstance(out, basestring):
            self._output(out)
            return self._ok()

        # boolean values result in OK or ERROR
        # being injected into the read buffer
        elif out == True:  return self._ok()
        elif out == False: return self._error()

        # for any other return value, leave the
        # read buffer alone (we'll assume that
        # the method has injected its own output)
        else: return None


    def _output(self, str, delimiters=True):
        """Insert a GSM response into the read buffer, with leading and
           trailing terminators (\r\n). This spews whitespace everywhere,
           but is (curiously) how most modems work."""

        def _delimit():
            self.buf_read.extend(["\r", "\n"])

        # add each letter to the buf_read array,
        # optionally surrounded by the delimiters
        if delimiters: _delimit()
        self.buf_read.extend(str)
        if delimiters: _delimit()

        # what could possibly
        # have gone wrong?
        return True


    def _ok(self):
        """Insert a GSM "OK" string into the read buffer.
           This should be called when a command succeeds."""

        self._output("OK")
        return True


    def _error(self):
        """Insert a GSM "ERROR" string into the read buffer.
           This should be called when a command fails."""

        self._output("ERROR")
        return False



class MockSenderDevice(MockDevice):
    """This mock device accepts outgoing SMS (in text mode), and stores them in
       self.sent_messages for later retrieval. This functionality is encapsulated
       here, because it's confusing and ugly."""

    def __init__(self):
        MockDevice.__init__(self)
        self.sent_messages = []
        self.recipient = None
        self.message = None


    def _prompt(self):
        """Outputs the message prompt, which indicates that the device
           is currently accepting the text contents of an SMS."""
        self._output("\r\n>", False)
        return None


    def write(self, str):

        # if we are currently writing a message, and
        # ascii 26 (ctrl+z) was hit, it's time to send!
        if self.recipient:
            if str[-1] == chr(26):
                MockDevice.write(self, str[0:-1])
                self.message.append("".join(self.buf_write))
                self.buf_write = []

                # just store this outgoing message to be checked
                # later on. we're not _really_ sending anything
                self.sent_messages.append({
                    "recipient": self.recipient,
                    "text": "\n".join(self.message)
                })

                # confirm that the message was
                # accepted, and clear the state
                self._output("+CMGS: 1")
                self.recipient = None
                self.message = None
                return self._ok()

        # most of the time, invoke the superclass
        return MockDevice.write(self, str)


    def _process(self, cmd):

        # if we're currently building a message,
        # store this line and prompt for the next
        if self.recipient:
            self.message.append(cmd)
            return self._prompt()

        # otherwise, behave normally
        else: MockDevice._process(self, cmd)    


    def at_cmgs(self, recipient):

        # note the recipient's number (to attach to
        # the message when we're finished), and make
        # a space for the text to be collected
        self.recipient = recipient
        self.message = []

        # start prompting for text
        return self._prompt()

########NEW FILE########
