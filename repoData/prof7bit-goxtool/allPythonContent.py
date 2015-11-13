__FILENAME__ = goxapi
"""Mt.Gox API."""

#  Copyright (c) 2013 Bernd Kreuss <prof7bit@gmail.com>
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.

# pylint: disable=C0302,C0301,R0902,R0903,R0912,R0913,R0914,R0915,W0703,W0105

import sys
PY_VERSION = sys.version_info

if PY_VERSION < (2, 7):
    print("Sorry, minimal Python version is 2.7, you have: %d.%d"
          % (PY_VERSION.major, PY_VERSION.minor))
    sys.exit(1)

from ConfigParser import SafeConfigParser
import base64
import bisect
import binascii
import contextlib
from Crypto.Cipher import AES
import getpass
import gzip
import hashlib
import hmac
import inspect
import io
import json
import logging
import pubnub_light
import Queue
import time
import traceback
import threading
from urllib2 import Request as URLRequest
from urllib2 import urlopen, HTTPError
from urllib import urlencode
import weakref
import websocket

input = raw_input  # pylint: disable=W0622,C0103

FORCE_PROTOCOL = ""
FORCE_NO_FULLDEPTH = False
FORCE_NO_DEPTH = False
FORCE_NO_LAG = False
FORCE_NO_HISTORY = False
FORCE_HTTP_API = False
FORCE_NO_HTTP_API = False

SOCKETIO_HOST = "socketio.mtgox.com"
WEBSOCKET_HOST = "websocket.mtgox.com"
HTTP_HOST = "data.mtgox.com"

USER_AGENT = "goxtool.py"

# available channels as per https://mtgox.com/api/2/stream/list_public?pretty
# queried on 2013-12-14 - this must be updated when they add new currencies,
# I'm too lazy now to do that dynamically, it doesn't change often (if ever)
CHANNELS = {
        "ticker.LTCGBP": "0102a446-e4d4-4082-8e83-cc02822f9172",
        "ticker.LTCCNY": "0290378c-e3d7-4836-8cb1-2bfae20cc492",
        "depth.BTCHKD": "049f65dc-3af3-4ffd-85a5-aac102b2a579",
        "depth.BTCEUR": "057bdc6b-9f9c-44e4-bc1a-363e4443ce87",
        "ticker.NMCAUD": "08c65460-cbd9-492e-8473-8507dfa66ae6",
        "ticker.BTCEUR": "0bb6da8b-f6c6-4ecf-8f0d-a544ad948c15",
        "depth.BTCKRW": "0c84bda7-e613-4b19-ae2a-6d26412c9f70",
        "depth.BTCCNY": "0d1ecad8-e20f-459e-8bed-0bdcf927820f",
        "ticker.BTCCAD": "10720792-084d-45ba-92e3-cf44d9477775",
        "depth.BTCCHF": "113fec5f-294d-4929-86eb-8ca4c3fd1bed",
        "ticker.LTCNOK": "13616ae8-9268-4a43-bdf7-6b8d1ac814a2",
        "ticker.LTCUSD": "1366a9f3-92eb-4c6c-9ccc-492a959eca94",
        "ticker.BTCBTC": "13edff67-cfa0-4d99-aa76-52bd15d6a058",
        "ticker.LTCCAD": "18b55737-3f5c-4583-af63-6eb3951ead72",
        "ticker.NMCCNY": "249fdefd-c6eb-4802-9f54-064bc83908aa",
        "depth.BTCUSD": "24e67e0d-1cad-4cc0-9e7a-f8523ef460fe",
        "ticker.BTCCHF": "2644c164-3db7-4475-8b45-c7042efe3413",
        "depth.BTCAUD": "296ee352-dd5d-46f3-9bea-5e39dede2005",
        "ticker.BTCCZK": "2a968b7f-6638-40ba-95e7-7284b3196d52",
        "ticker.BTCSGD": "2cb73ed1-07f4-45e0-8918-bcbfda658912",
        "ticker.NMCJPY": "314e2b7a-a9fa-4249-bc46-b7f662ecbc3a",
        "ticker.BTCNMC": "36189b8c-cffa-40d2-b205-fb71420387ae",
        "depth.BTCINR": "414fdb18-8f70-471c-a9df-b3c2740727ea",
        "depth.BTCSGD": "41e5c243-3d44-4fad-b690-f39e1dbb86a8",
        "ticker.BTCLTC": "48b6886f-49c0-4614-b647-ba5369b449a9",
        "ticker.LTCEUR": "491bc9bb-7cd8-4719-a9e8-16dad802ffac",
        "ticker.BTCINR": "55e5feb8-fea5-416b-88fa-40211541deca",
        "ticker.LTCJPY": "5ad8e40f-6df3-489f-9cf1-af28426a50cf",
        "depth.BTCCAD": "5b234cc3-a7c1-47ce-854f-27aee4cdbda5",
        "ticker.BTCNZD": "5ddd27ca-2466-4d1a-8961-615dedb68bf1",
        "depth.BTCGBP": "60c3af1b-5d40-4d0e-b9fc-ccab433d2e9c",
        "depth.BTCNOK": "66da7fb4-6b0c-4a10-9cb7-e2944e046eb5",
        "depth.BTCTHB": "67879668-532f-41f9-8eb0-55e7593a5ab8",
        "ticker.BTCSEK": "6caf1244-655b-460f-beaf-5c56d1f4bea7",
        "ticker.BTCNOK": "7532e866-3a03-4514-a4b1-6f86e3a8dc11",
        "ticker.BTCGBP": "7b842b7d-d1f9-46fa-a49c-c12f1ad5a533",
        "trade.lag": "85174711-be64-4de1-b783-0628995d7914",
        "depth.BTCSEK": "8f1fefaa-7c55-4420-ada0-4de15c1c38f3",
        "depth.BTCDKK": "9219abb0-b50c-4007-b4d2-51d1711ab19c",
        "depth.BTCJPY": "94483e07-d797-4dd4-bc72-dc98f1fd39e3",
        "ticker.NMCUSD": "9aaefd15-d101-49f3-a2fd-6b63b85b6bed",
        "ticker.LTCAUD": "a046600a-a06c-4ebf-9ffb-bdc8157227e8",
        "ticker.BTCJPY": "a39ae532-6a3c-4835-af8c-dda54cb4874e",
        "depth.BTCCZK": "a7a970cf-4f6c-4d85-a74e-ac0979049b87",
        "ticker.LTCDKK": "b10a706e-e8c7-4ea8-9148-669f86930b36",
        "ticker.BTCPLN": "b4a02cb3-2e2d-4a88-aeea-3c66cb604d01",
        "ticker.BTCRUB": "bd04f720-3c70-4dce-ae71-2422ab862c65",
        "ticker.NMCGBP": "bf5126ba-5187-456f-8ae6-963678d0607f",
        "ticker.BTCKRW": "bf85048d-4db9-4dbe-9ca3-5b83a1a4186e",
        "ticker.BTCCNY": "c251ec35-56f9-40ab-a4f6-13325c349de4",
        "depth.BTCNZD": "cedf8730-bce6-4278-b6fe-9bee42930e95",
        "ticker.BTCHKD": "d3ae78dd-01dd-4074-88a7-b8aa03cd28dd",
        "ticker.BTCTHB": "d58e3b69-9560-4b9e-8c58-b5c0f3fda5e1",
        "ticker.BTCUSD": "d5f06780-30a8-4a48-a2f8-7ed181b4a13f",
        "depth.BTCRUB": "d6412ca0-b686-464c-891a-d1ba3943f3c6",
        "ticker.NMCEUR": "d8512d04-f262-4a14-82f2-8e5c96c15e68",
        "trade.BTC": "dbf1dee9-4f2e-4a08-8cb7-748919a71b21",
        "ticker.NMCCAD": "dc28033e-7506-484c-905d-1c811a613323",
        "depth.BTCPLN": "e4ff055a-f8bf-407e-af76-676cad319a21",
        "ticker.BTCDKK": "e5ce0604-574a-4059-9493-80af46c776b3",
        "ticker.BTCAUD": "eb6aaa11-99d0-4f64-9e8c-1140872a423d"
    }


# deprecated, use gox.quote2str() and gox.base2str() instead
def int2str(value_int, currency):
    """return currency integer formatted as a string"""
    if currency in "BTC LTC NMC":
        return ("%16.8f" % (value_int / 100000000.0))
    elif currency in "JPY SEK":
        return ("%12.3f" % (value_int / 1000.0))
    else:
        return ("%12.5f" % (value_int / 100000.0))


# deprecated, use gox.quote2float() and gox.base2float() instead
def int2float(value_int, currency):
    """convert integer to float, determine the factor by currency name"""
    if currency in "BTC LTC NMC":
        return value_int / 100000000.0
    elif currency in "JPY SEK":
        return value_int / 1000.0
    else:
        return value_int / 100000.0


# deprecated, use gox.quote2int() and gox.base2int() instead
def float2int(value_float, currency):
    """convert float value to integer, determine the factor by currency name"""
    if currency in "BTC LTC NMC":
        return int(round(value_float * 100000000))
    elif currency in "JPY SEK":
        return int(round(value_float * 1000))
    else:
        return int(round(value_float * 100000))


def http_request(url, post=None, headers=None):
    """request data from the HTTP API, returns the response a string. If a
    http error occurs it will *not* raise an exception, instead it will
    return the content of the error document. This is because  MtGox will
    send 5xx http status codes even if application level errors occur
    (such as canceling the same order twice or things like that) and the
    real error message will be in the json that is returned, so the return
    document is always much more interesting than the http status code."""

    def read_gzipped(response):
        """read data from the response object,
        unzip if necessary, return text string"""
        if response.info().get('Content-Encoding') == 'gzip':
            with io.BytesIO(response.read()) as buf:
                with gzip.GzipFile(fileobj=buf) as unzipped:
                    data = unzipped.read()
        else:
            data = response.read()
        return data

    if not headers:
        headers = {}
    request = URLRequest(url, post, headers)
    request.add_header('Accept-encoding', 'gzip')
    request.add_header('User-Agent', USER_AGENT)
    data = ""
    try:
        with contextlib.closing(urlopen(request, post)) as res:
            data = read_gzipped(res)
    except HTTPError as err:
        data = read_gzipped(err)

    return data

def start_thread(thread_func, name=None):
    """start a new thread to execute the supplied function"""
    thread = threading.Thread(None, thread_func)
    thread.daemon = True
    thread.start()
    if name:
        thread.name = name
    return thread

def pretty_format(something):
    """pretty-format a nested dict or list for debugging purposes.
    If it happens to be a valid json string then it will be parsed first"""
    try:
        return pretty_format(json.loads(something))
    except Exception:
        try:
            return json.dumps(something, indent=5)
        except Exception:
            return str(something)


# pylint: disable=R0904
class GoxConfig(SafeConfigParser):
    """return a config parser object with default values. If you need to run
    more Gox() objects at the same time you will also need to give each of them
    them a separate GoxConfig() object. For this reason it takes a filename
    in its constructor for the ini file, you can have separate configurations
    for separate Gox() instances"""

    _DEFAULTS = [["gox", "base_currency", "BTC"]
                ,["gox", "quote_currency", "USD"]
                ,["gox", "use_ssl", "True"]
                ,["gox", "use_plain_old_websocket", "True"]
                ,["gox", "use_http_api", "True"]
                ,["gox", "use_tonce", "True"]
                ,["gox", "load_fulldepth", "True"]
                ,["gox", "load_history", "True"]
                ,["gox", "history_timeframe", "15"]
                ,["gox", "secret_key", ""]
                ,["gox", "secret_secret", ""]
                ,["pubnub", "stream_sorter_time_window", "0.5"]
                ]

    def __init__(self, filename):
        self.filename = filename
        SafeConfigParser.__init__(self)
        self.load()
        self.init_defaults(self._DEFAULTS)
        # upgrade from deprecated "currency" to "quote_currency"
        # todo: remove this piece of code again in a few months
        if self.has_option("gox", "currency"):
            self.set("gox", "quote_currency", self.get_string("gox", "currency"))
            self.remove_option("gox", "currency")
            self.save()

    def init_defaults(self, defaults):
        """add the missing default values, default is a list of defaults"""
        for (sect, opt, default) in defaults:
            self._default(sect, opt, default)

    def save(self):
        """save the config to the .ini file"""
        with open(self.filename, 'wb') as configfile:
            self.write(configfile)

    def load(self):
        """(re)load the onfig from the .ini file"""
        self.read(self.filename)

    def get_safe(self, sect, opt):
        """get value without throwing exception."""
        try:
            return self.get(sect, opt)

        except: # pylint: disable=W0702
            for (dsect, dopt, default) in self._DEFAULTS:
                if dsect == sect and dopt == opt:
                    self._default(sect, opt, default)
                    return default
            return ""

    def get_bool(self, sect, opt):
        """get boolean value from config"""
        return self.get_safe(sect, opt) == "True"

    def get_string(self, sect, opt):
        """get string value from config"""
        return self.get_safe(sect, opt)

    def get_int(self, sect, opt):
        """get int value from config"""
        vstr = self.get_safe(sect, opt)
        try:
            return int(vstr)
        except ValueError:
            return 0

    def get_float(self, sect, opt):
        """get int value from config"""
        vstr = self.get_safe(sect, opt)
        try:
            return float(vstr)
        except ValueError:
            return 0.0

    def _default(self, section, option, default):
        """create a default option if it does not yet exist"""
        if not self.has_section(section):
            self.add_section(section)
        if not self.has_option(section, option):
            self.set(section, option, default)
            self.save()

class Signal():
    """callback functions (so called slots) can be connected to a signal and
    will be called when the signal is called (Signal implements __call__).
    The slots receive two arguments: the sender of the signal and a custom
    data object. Two different threads won't be allowed to send signals at the
    same time application-wide, concurrent threads will have to wait until
    the lock is releaesed again. The lock allows recursive reentry of the same
    thread to avoid deadlocks when a slot wants to send a signal itself."""

    _lock = threading.RLock()
    signal_error = None

    def __init__(self):
        self._functions = weakref.WeakSet()
        self._methods = weakref.WeakKeyDictionary()

        # the Signal class itself has a static member signal_error where it
        # will send tracebacks of exceptions that might happen. Here we
        # initialize it if it does not exist already
        if not Signal.signal_error:
            Signal.signal_error = 1
            Signal.signal_error = Signal()

    def connect(self, slot):
        """connect a slot to this signal. The parameter slot can be a funtion
        that takes exactly 2 arguments or a method that takes self plus 2 more
        arguments, or it can even be even another signal. the first argument
        is a reference to the sender of the signal and the second argument is
        the payload. The payload can be anything, it totally depends on the
        sender and type of the signal."""
        if inspect.ismethod(slot):
            instance = slot.__self__
            function = slot.__func__
            if instance not in self._methods:
                self._methods[instance] = set()
            if function not in self._methods[instance]:
                self._methods[instance].add(function)
        else:
            if slot not in self._functions:
                self._functions.add(slot)

    def __call__(self, sender, data, error_signal_on_error=True):
        """dispatch signal to all connected slots. This is a synchronuos
        operation, It will not return before all slots have been called.
        Also only exactly one thread is allowed to emit signals at any time,
        all other threads that try to emit *any* signal anywhere in the
        application at the same time will be blocked until the lock is released
        again. The lock will allow recursive reentry of the seme thread, this
        means a slot can itself emit other signals before it returns (or
        signals can be directly connected to other signals) without problems.
        If a slot raises an exception a traceback will be sent to the static
        Signal.signal_error() or to logging.critical()"""
        with self._lock:
            sent = False
            errors = []
            for func in self._functions:
                try:
                    func(sender, data)
                    sent = True

                except: # pylint: disable=W0702
                    errors.append(traceback.format_exc())

            for instance, functions in self._methods.items():
                for func in functions:
                    try:
                        func(instance, sender, data)
                        sent = True

                    except: # pylint: disable=W0702
                        errors.append(traceback.format_exc())

            for error in errors:
                if error_signal_on_error:
                    Signal.signal_error(self, (error), False)
                else:
                    logging.critical(error)

            return sent


class BaseObject():
    """This base class only exists because of the debug() method that is used
    in many of the goxtool objects to send debug output to the signal_debug."""

    def __init__(self):
        self.signal_debug = Signal()

    def debug(self, *args):
        """send a string composed of all *args to all slots who
        are connected to signal_debug or send it to the logger if
        nobody is connected"""
        msg = " ".join([str(x) for x in args])
        if not self.signal_debug(self, (msg)):
            logging.debug(msg)


class Timer(Signal):
    """a simple timer (used for stuff like keepalive)."""

    def __init__(self, interval, one_shot=False):
        """create a new timer, interval is in seconds"""
        Signal.__init__(self)
        self._one_shot = one_shot
        self._canceled = False
        self._interval = interval
        self._timer = None
        self._start()

    def _fire(self):
        """fire the signal and restart it"""
        if not self._canceled:
            self.__call__(self, None)
            if not (self._canceled or self._one_shot):
                self._start()

    def _start(self):
        """start the timer"""
        self._timer = threading.Timer(self._interval, self._fire)
        self._timer.daemon = True
        self._timer.start()

    def cancel(self):
        """cancel the timer"""
        self._canceled = True
        self._timer.cancel()
        self._timer = None


class Secret:
    """Manage the MtGox API secret. This class has methods to decrypt the
    entries in the ini file and it also provides a method to create these
    entries. The methods encrypt() and decrypt() will block and ask
    questions on the command line, they are called outside the curses
    environment (yes, its a quick and dirty hack but it works for now)."""

    S_OK            = 0
    S_FAIL          = 1
    S_NO_SECRET     = 2
    S_FAIL_FATAL    = 3

    def __init__(self, config):
        """initialize the instance"""
        self.config = config
        self.key = ""
        self.secret = ""

        # pylint: disable=C0103
        self.password_from_commandline_option = None

    def decrypt(self, password):
        """decrypt "secret_secret" from the ini file with the given password.
        This will return false if decryption did not seem to be successful.
        After this menthod succeeded the application can access the secret"""

        key = self.config.get_string("gox", "secret_key")
        sec = self.config.get_string("gox", "secret_secret")
        if sec == "" or key == "":
            return self.S_NO_SECRET

        # pylint: disable=E1101
        hashed_pass = hashlib.sha512(password.encode("utf-8")).digest()
        crypt_key = hashed_pass[:32]
        crypt_ini = hashed_pass[-16:]
        aes = AES.new(crypt_key, AES.MODE_OFB, crypt_ini)
        try:
            encrypted_secret = base64.b64decode(sec.strip().encode("ascii"))
            self.secret = aes.decrypt(encrypted_secret).strip()
            self.key = key.strip()
        except ValueError:
            return self.S_FAIL

        # now test if we now have something plausible
        try:
            print("testing secret...")
            # is it plain ascii? (if not this will raise exception)
            dummy = self.secret.decode("ascii")
            # can it be decoded? correct size afterwards?
            if len(base64.b64decode(self.secret)) != 64:
                raise Exception("decrypted secret has wrong size")

            print("testing key...")
            # key must be only hex digits and have the right size
            hex_key = self.key.replace("-", "").encode("ascii")
            if len(binascii.unhexlify(hex_key)) != 16:
                raise Exception("key has wrong size")

            print("ok :-)")
            return self.S_OK

        except Exception as exc:
            # this key and secret do not work :-(
            self.secret = ""
            self.key = ""
            print("### Error occurred while testing the decrypted secret:")
            print("    '%s'" % exc)
            print("    This does not seem to be a valid MtGox API secret")
            return self.S_FAIL

    def prompt_decrypt(self):
        """ask the user for password on the command line
        and then try to decrypt the secret."""
        if self.know_secret():
            return self.S_OK

        key = self.config.get_string("gox", "secret_key")
        sec = self.config.get_string("gox", "secret_secret")
        if sec == "" or key == "":
            return self.S_NO_SECRET

        if self.password_from_commandline_option:
            password = self.password_from_commandline_option
        else:
            password = getpass.getpass("enter passphrase for secret: ")

        result = self.decrypt(password)
        if result != self.S_OK:
            print("")
            print("secret could not be decrypted")
            answer = input("press any key to continue anyways " \
                + "(trading disabled) or 'q' to quit: ")
            if answer == "q":
                result = self.S_FAIL_FATAL
            else:
                result = self.S_NO_SECRET
        return result

    # pylint: disable=R0201
    def prompt_encrypt(self):
        """ask for key, secret and password on the command line,
        then encrypt the secret and store it in the ini file."""
        print("Please copy/paste key and secret from MtGox and")
        print("then provide a password to encrypt them.")
        print("")


        key =    input("             key: ").strip()
        secret = input("          secret: ").strip()
        while True:
            password1 = getpass.getpass("        password: ").strip()
            if password1 == "":
                print("aborting")
                return
            password2 = getpass.getpass("password (again): ").strip()
            if password1 != password2:
                print("you had a typo in the password. try again...")
            else:
                break

        # pylint: disable=E1101
        hashed_pass = hashlib.sha512(password1.encode("utf-8")).digest()
        crypt_key = hashed_pass[:32]
        crypt_ini = hashed_pass[-16:]
        aes = AES.new(crypt_key, AES.MODE_OFB, crypt_ini)

        # since the secret is a base64 string we can just just pad it with
        # spaces which can easily be stripped again after decryping
        print(len(secret))
        secret += " " * (16 - len(secret) % 16)
        print(len(secret))
        secret = base64.b64encode(aes.encrypt(secret)).decode("ascii")

        self.config.set("gox", "secret_key", key)
        self.config.set("gox", "secret_secret", secret)
        self.config.save()

        print("encrypted secret has been saved in %s" % self.config.filename)

    def know_secret(self):
        """do we know the secret key? The application must be able to work
        without secret and then just don't do any account related stuff"""
        return(self.secret != "") and (self.key != "")


class OHLCV():
    """represents a chart candle. tim is POSIX timestamp of open time,
    prices and volume are integers like in the other parts of the gox API"""

    def __init__(self, tim, opn, hig, low, cls, vol):
        self.tim = tim
        self.opn = opn
        self.hig = hig
        self.low = low
        self.cls = cls
        self.vol = vol

    def update(self, price, volume):
        """update high, low and close values and add to volume"""
        if price > self.hig:
            self.hig = price
        if price < self.low:
            self.low = price
        self.cls = price
        self.vol += volume


class History(BaseObject):
    """represents the trading history"""

    def __init__(self, gox, timeframe):
        BaseObject.__init__(self)

        self.signal_fullhistory_processed = Signal()
        self.signal_changed               = Signal()

        self.gox = gox
        self.candles = []
        self.timeframe = timeframe

        self.ready_history = False

        gox.signal_trade.connect(self.slot_trade)
        gox.signal_fullhistory.connect(self.slot_fullhistory)

    def add_candle(self, candle):
        """add a new candle to the history"""
        self._add_candle(candle)
        self.signal_changed(self, (self.length()))

    def slot_trade(self, dummy_sender, data):
        """slot for gox.signal_trade"""
        (date, price, volume, dummy_typ, own) = data
        if not own:
            time_round = int(date / self.timeframe) * self.timeframe
            candle = self.last_candle()
            if candle:
                if candle.tim == time_round:
                    candle.update(price, volume)
                    self.signal_changed(self, (1))
                else:
                    self.debug("### opening new candle")
                    self.add_candle(OHLCV(
                        time_round, price, price, price, price, volume))
            else:
                self.add_candle(OHLCV(
                    time_round, price, price, price, price, volume))

    def _add_candle(self, candle):
        """add a new candle to the history but don't fire signal_changed"""
        self.candles.insert(0, candle)

    def slot_fullhistory(self, dummy_sender, data):
        """process the result of the fullhistory request"""
        (history) = data

        if not len(history):
            self.debug("### history download was empty")
            return

        def get_time_round(date):
            """round timestamp to current candle timeframe"""
            return int(date / self.timeframe) * self.timeframe

        #remove existing recent candle(s) if any, we will create them fresh
        date_begin = get_time_round(int(history[0]["date"]))
        while len(self.candles) and self.candles[0].tim >= date_begin:
            self.candles.pop(0)

        new_candle = OHLCV(0, 0, 0, 0, 0, 0) #this is a dummy, not actually inserted
        count_added = 0
        for trade in history:
            date = int(trade["date"])
            price = int(trade["price_int"])
            volume = int(trade["amount_int"])
            time_round = get_time_round(date)
            if time_round > new_candle.tim:
                if new_candle.tim > 0:
                    self._add_candle(new_candle)
                    count_added += 1
                new_candle = OHLCV(
                    time_round, price, price, price, price, volume)
            new_candle.update(price, volume)

        # insert current (incomplete) candle
        self._add_candle(new_candle)
        count_added += 1
        self.debug("### got %d updated candle(s)" % count_added)
        self.ready_history = True
        self.signal_fullhistory_processed(self, None)
        self.signal_changed(self, (self.length()))

    def last_candle(self):
        """return the last (current) candle or None if empty"""
        if self.length() > 0:
            return self.candles[0]
        else:
            return None

    def length(self):
        """return the number of candles in the history"""
        return len(self.candles)


class BaseClient(BaseObject):
    """abstract base class for SocketIOClient and WebsocketClient"""

    _last_unique_microtime = 0
    _nonce_lock = threading.Lock()

    def __init__(self, curr_base, curr_quote, secret, config):
        BaseObject.__init__(self)

        self.signal_recv         = Signal()
        self.signal_fulldepth    = Signal()
        self.signal_fullhistory  = Signal()
        self.signal_connected    = Signal()
        self.signal_disconnected = Signal()

        self._timer = Timer(60)
        self._timer.connect(self.slot_timer)

        self._info_timer = None # used when delayed requesting private/info

        self.curr_base = curr_base
        self.curr_quote = curr_quote

        self.currency = curr_quote # deprecated, use curr_quote instead

        self.secret = secret
        self.config = config
        self.socket = None
        self.http_requests = Queue.Queue()

        self._recv_thread = None
        self._http_thread = None
        self._terminating = False
        self.connected = False
        self._time_last_received = 0
        self._time_last_subscribed = 0
        self.history_last_candle = None

    def start(self):
        """start the client"""
        self._recv_thread = start_thread(self._recv_thread_func, "socket receive thread")
        self._http_thread = start_thread(self._http_thread_func, "http thread")

    def stop(self):
        """stop the client"""
        self._terminating = True
        self._timer.cancel()
        if self.socket:
            self.debug("### closing socket")
            self.socket.sock.close()

    def force_reconnect(self):
        """force client to reconnect"""
        self.socket.close()

    def _try_send_raw(self, raw_data):
        """send raw data to the websocket or disconnect and close"""
        if self.connected:
            try:
                self.socket.send(raw_data)
            except Exception as exc:
                self.debug(exc)
                self.connected = False
                self.socket.close()

    def send(self, json_str):
        """there exist 2 subtly different ways to send a string over a
        websocket. Each client class will override this send method"""
        raise NotImplementedError()

    def get_unique_mirotime(self):
        """produce a unique nonce that is guaranteed to be ever increasing"""
        with self._nonce_lock:
            microtime = int(time.time() * 1E6)
            if microtime <= self._last_unique_microtime:
                microtime = self._last_unique_microtime + 1
            self._last_unique_microtime = microtime
            return microtime

    def use_http(self):
        """should we use http api? return true if yes"""
        use_http = self.config.get_bool("gox", "use_http_api")
        if FORCE_HTTP_API:
            use_http = True
        if FORCE_NO_HTTP_API:
            use_http = False
        return use_http

    def use_tonce(self):
        """should we use tonce instead on nonce? tonce is current microtime
        and also works when messages come out of order (which happens at
        the mtgox server in certain siuations). They still have to be unique
        because mtgox will remember all recently used tonce values. It will
        only be accepted when the local clock is +/- 10 seconds exact."""
        return self.config.get_bool("gox", "use_tonce")

    def request_fulldepth(self):
        """start the fulldepth thread"""

        def fulldepth_thread():
            """request the full market depth, initialize the order book
            and then terminate. This is called in a separate thread after
            the streaming API has been connected."""
            self.debug("### requesting initial full depth")
            use_ssl = self.config.get_bool("gox", "use_ssl")
            proto = {True: "https", False: "http"}[use_ssl]
            fulldepth = http_request("%s://%s/api/2/%s%s/money/depth/full" % (
                proto,
                HTTP_HOST,
                self.curr_base,
                self.curr_quote
            ))
            self.signal_fulldepth(self, (json.loads(fulldepth)))

        start_thread(fulldepth_thread, "http request full depth")

    def request_history(self):
        """request trading history"""

        # Gox() will have set this field to the timestamp of the last
        # known candle, so we only request data since this time
        since = self.history_last_candle

        def history_thread():
            """request trading history"""

            # 1308503626, 218868 <-- last small transacion ID
            # 1309108565, 1309108565842636 <-- first big transaction ID

            if since:
                querystring = "?since=%i" % (since * 1000000)
            else:
                querystring = ""

            self.debug("### requesting history")
            use_ssl = self.config.get_bool("gox", "use_ssl")
            proto = {True: "https", False: "http"}[use_ssl]
            json_hist = http_request("%s://%s/api/2/%s%s/money/trades%s" % (
                proto,
                HTTP_HOST,
                self.curr_base,
                self.curr_quote,
                querystring
            ))
            history = json.loads(json_hist)
            if history["result"] == "success":
                self.signal_fullhistory(self, history["data"])

        start_thread(history_thread, "http request trade history")

    def _recv_thread_func(self):
        """this will be executed as the main receiving thread, each type of
        client (websocket or socketio) will implement its own"""
        raise NotImplementedError()

    def channel_subscribe(self, download_market_data=True):
        """subscribe to needed channnels and download initial data (orders,
        account info, depth, history, etc. Some of these might be redundant but
        at the time I wrote this code the socketio server seemed to have a bug,
        not being able to subscribe via the GET parameters, so I send all
        needed subscription requests here again, just to be on the safe side."""

        symb = "%s%s" % (self.curr_base, self.curr_quote)
        if not FORCE_NO_DEPTH:
            self.send(json.dumps({"op":"mtgox.subscribe", "channel":"depth.%s" % symb}))
        self.send(json.dumps({"op":"mtgox.subscribe", "channel":"ticker.%s" % symb}))

        # trades and lag are the same channels for all currencies
        self.send(json.dumps({"op":"mtgox.subscribe", "type":"trades"}))
        if not FORCE_NO_LAG:
            self.send(json.dumps({"op":"mtgox.subscribe", "type":"lag"}))

        self.request_idkey()
        self.request_orders()
        self.request_info()

        if download_market_data:
            if self.config.get_bool("gox", "load_fulldepth"):
                if not FORCE_NO_FULLDEPTH:
                    self.request_fulldepth()

            if self.config.get_bool("gox", "load_history"):
                if not FORCE_NO_HISTORY:
                    self.request_history()

        self._time_last_subscribed = time.time()

    def _slot_timer_info_later(self, _sender, _data):
        """the slot for the request_info_later() timer signal"""
        self.request_info()
        self._info_timer = None

    def request_info_later(self, delay):
        """request the private/info in delay seconds from now"""
        if self._info_timer:
            self._info_timer.cancel()
        self._info_timer = Timer(delay, True)
        self._info_timer.connect(self._slot_timer_info_later)

    def request_info(self):
        """request the private/info object"""
        if self.use_http():
            self.enqueue_http_request("money/info", {}, "info")
        else:
            self.send_signed_call("private/info", {}, "info")

    def request_idkey(self):
        """request the private/idkey object"""
        if self.use_http():
            self.enqueue_http_request("money/idkey", {}, "idkey")
        else:
            self.send_signed_call("private/idkey", {}, "idkey")

    def request_orders(self):
        """request the private/orders object"""
        if self.use_http():
            self.enqueue_http_request("money/orders", {}, "orders")
        else:
            self.send_signed_call("private/orders", {}, "orders")

    def _http_thread_func(self):
        """send queued http requests to the http API (only used when
        http api is forced, normally this is much slower)"""
        while not self._terminating:
            # pop queued request from the queue and process it
            (api_endpoint, params, reqid) = self.http_requests.get(True)
            translated = None
            try:
                answer = self.http_signed_call(api_endpoint, params)
                if answer["result"] == "success":
                    # the following will reformat the answer in such a way
                    # that we can pass it directly to signal_recv()
                    # as if it had come directly from the websocket
                    translated = {
                        "op": "result",
                        "result": answer["data"],
                        "id": reqid
                    }
                else:
                    if "error" in answer:
                        if answer["token"] == "unknown_error":
                            # enqueue it again, it will eventually succeed.
                            self.enqueue_http_request(api_endpoint, params, reqid)
                        else:

                            # these are errors like "Order amount is too low"
                            # or "Order not found" and the like, we send them
                            # to signal_recv() as if they had come from the
                            # streaming API beause Gox() can handle these errors.
                            translated = {
                                "op": "remark",
                                "success": False,
                                "message": answer["error"],
                                "token": answer["token"],
                                "id": reqid
                            }

                    else:
                        self.debug("### unexpected http result:", answer, reqid)

            except Exception as exc:
                # should this ever happen? HTTP 5xx wont trigger this,
                # something else must have gone wrong, a totally malformed
                # reply or something else.
                #
                # After some time of testing during times of heavy
                # volatility it appears that this happens mostly when
                # there is heavy load on their servers. Resubmitting
                # the API call will then eventally succeed.
                self.debug("### exception in _http_thread_func:",
                    exc, api_endpoint, params, reqid)

                # enqueue it again, it will eventually succeed.
                self.enqueue_http_request(api_endpoint, params, reqid)

            if translated:
                self.signal_recv(self, (json.dumps(translated)))

            self.http_requests.task_done()

    def enqueue_http_request(self, api_endpoint, params, reqid):
        """enqueue a request for sending to the HTTP API, returns
        immediately, behaves exactly like sending it over the websocket."""
        if self.secret and self.secret.know_secret():
            self.http_requests.put((api_endpoint, params, reqid))

    def http_signed_call(self, api_endpoint, params):
        """send a signed request to the HTTP API V2"""
        if (not self.secret) or (not self.secret.know_secret()):
            self.debug("### don't know secret, cannot call %s" % api_endpoint)
            return

        key = self.secret.key
        sec = self.secret.secret

        if self.use_tonce():
            params["tonce"] = self.get_unique_mirotime()
        else:
            params["nonce"] = self.get_unique_mirotime()

        post = urlencode(params)
        prefix = api_endpoint + chr(0)
        # pylint: disable=E1101
        sign = hmac.new(base64.b64decode(sec), prefix + post, hashlib.sha512).digest()

        headers = {
            'Rest-Key': key,
            'Rest-Sign': base64.b64encode(sign)
        }

        use_ssl = self.config.get_bool("gox", "use_ssl")
        proto = {True: "https", False: "http"}[use_ssl]
        url = "%s://%s/api/2/%s" % (
            proto,
            HTTP_HOST,
            api_endpoint
        )
        self.debug("### (%s) calling %s" % (proto, url))
        return json.loads(http_request(url, post, headers))

    def send_signed_call(self, api_endpoint, params, reqid):
        """send a signed (authenticated) API call over the socket.io.
        This method will only succeed if the secret key is available,
        otherwise it will just log a warning and do nothing."""
        if (not self.secret) or (not self.secret.know_secret()):
            self.debug("### don't know secret, cannot call %s" % api_endpoint)
            return

        key = self.secret.key
        sec = self.secret.secret

        call = {
            "id"       : reqid,
            "call"     : api_endpoint,
            "params"   : params,
            "currency" : self.curr_quote,
            "item"     : self.curr_base
        }
        if self.use_tonce():
            call["tonce"] = self.get_unique_mirotime()
        else:
            call["nonce"] = self.get_unique_mirotime()
        call = json.dumps(call)

        # pylint: disable=E1101
        sign = hmac.new(base64.b64decode(sec), call, hashlib.sha512).digest()
        signedcall = key.replace("-", "").decode("hex") + sign + call

        self.debug("### (socket) calling %s" % api_endpoint)
        self.send(json.dumps({
            "op"      : "call",
            "call"    : base64.b64encode(signedcall),
            "id"      : reqid,
            "context" : "mtgox.com"
        }))

    def send_order_add(self, typ, price, volume):
        """send an order"""
        reqid = "order_add:%s:%d:%d" % (typ, price, volume)
        if price > 0:
            params = {"type": typ, "price_int": price, "amount_int": volume}
        else:
            params = {"type": typ, "amount_int": volume}

        if self.use_http():
            api = "%s%s/money/order/add" % (self.curr_base , self.curr_quote)
            self.enqueue_http_request(api, params, reqid)
        else:
            api = "order/add"
            self.send_signed_call(api, params, reqid)

    def send_order_cancel(self, oid):
        """cancel an order"""
        params = {"oid": oid}
        reqid = "order_cancel:%s" % oid
        if self.use_http():
            api = "money/order/cancel"
            self.enqueue_http_request(api, params, reqid)
        else:
            api = "order/cancel"
            self.send_signed_call(api, params, reqid)

    def on_idkey_received(self, data):
        """id key was received, subscribe to private channel"""
        self.send(json.dumps({"op":"mtgox.subscribe", "key":data}))

    def slot_timer(self, _sender, _data):
        """check timeout (last received, dead socket?)"""
        if self.connected:
            if time.time() - self._time_last_received > 60:
                self.debug("### did not receive anything for a long time, disconnecting.")
                self.force_reconnect()
                self.connected = False
            if time.time() - self._time_last_subscribed > 1800:
                # sometimes after running for a few hours it
                # will lose some of the subscriptons for no
                # obvious reason. I've seen it losing the trades
                # and the lag channel channel already, and maybe
                # even others. Simply subscribing again completely
                # fixes this condition. For this reason we renew
                # all channel subscriptions once every hour.
                self.debug("### refreshing channel subscriptions")
                self.channel_subscribe(False)


class WebsocketClient(BaseClient):
    """this implements a connection to MtGox through the websocket protocol."""
    def __init__(self, curr_base, curr_quote, secret, config):
        BaseClient.__init__(self, curr_base, curr_quote, secret, config)
        self.hostname = WEBSOCKET_HOST

    def _recv_thread_func(self):
        """connect to the websocket and start receiving in an infinite loop.
        Try to reconnect whenever connection is lost. Each received json
        string will be dispatched with a signal_recv signal"""
        reconnect_time = 1
        use_ssl = self.config.get_bool("gox", "use_ssl")
        wsp = {True: "wss://", False: "ws://"}[use_ssl]
        port = {True: 443, False: 80}[use_ssl]
        ws_origin = "%s:%d" % (self.hostname, port)
        ws_headers = ["User-Agent: %s" % USER_AGENT]
        while not self._terminating:  #loop 0 (connect, reconnect)
            try:
                # channels separated by "/", wildcards allowed. Available
                # channels see here: https://mtgox.com/api/2/stream/list_public
                # example: ws://websocket.mtgox.com/?Channel=depth.LTCEUR/ticker.LTCEUR
                # the trades and lag channel will be subscribed after connect
                sym = "%s%s" % (self.curr_base, self.curr_quote)
                if not FORCE_NO_DEPTH:
                    ws_url = "%s%s?Channel=depth.%s/ticker.%s" % \
                    (wsp, self.hostname, sym, sym)
                else:
                    ws_url = "%s%s?Channel=ticker.%s" % \
                    (wsp, self.hostname, sym)
                self.debug("### trying plain old Websocket: %s ... " % ws_url)

                self.socket = websocket.WebSocket()
                # The server is somewhat picky when it comes to the exact
                # host:port syntax of the origin header, so I am supplying
                # my own origin header instead of the auto-generated one
                self.socket.connect(ws_url, origin=ws_origin, header=ws_headers)
                self._time_last_received = time.time()
                self.connected = True
                self.debug("### connected, subscribing needed channels")
                self.channel_subscribe()
                self.debug("### waiting for data...")
                self.signal_connected(self, None)
                while not self._terminating: #loop1 (read messages)
                    str_json = self.socket.recv()
                    self._time_last_received = time.time()
                    if str_json[0] == "{":
                        self.signal_recv(self, (str_json))

            except Exception as exc:
                self.connected = False
                self.signal_disconnected(self, None)
                if not self._terminating:
                    self.debug("### ", exc.__class__.__name__, exc,
                        "reconnecting in %i seconds..." % reconnect_time)
                    if self.socket:
                        self.socket.close()
                    time.sleep(reconnect_time)

    def send(self, json_str):
        """send the json encoded string over the websocket"""
        self._try_send_raw(json_str)


class SocketIO(websocket.WebSocket):
    """This is the WebSocket() class with added Super Cow Powers. It has a
    different connect method so that it can connect to socket.io. It will do
    the initial HTTP request with keep-alive and then use that same socket
    to upgrade to websocket"""
    def __init__(self, get_mask_key = None):
        websocket.WebSocket.__init__(self, get_mask_key)

    def connect(self, url, **options):
        """connect to socketio and then upgrade to websocket transport. Example:
        connect('wss://websocket.mtgox.com/socket.io/1', query='Currency=EUR')"""

        def read_block(sock):
            """read from the socket until empty line, return list of lines"""
            lines = []
            line = ""
            while True:
                res = sock.recv(1)
                line += res
                if res == "":
                    return None
                if res == "\n":
                    line = line.strip()
                    if line == "":
                        return lines
                    lines.append(line)
                    line = ""

        # pylint: disable=W0212
        hostname, port, resource, is_secure = websocket._parse_url(url)
        self.sock.connect((hostname, port))
        if is_secure:
            self.io_sock = websocket._SSLSocketWrapper(self.sock)

        path_a = resource
        if "query" in options:
            path_a += "?" + options["query"]
        self.io_sock.send("GET %s HTTP/1.1\r\n" % path_a)
        self.io_sock.send("Host: %s:%d\r\n" % (hostname, port))
        self.io_sock.send("User-Agent: %s\r\n" % USER_AGENT)
        self.io_sock.send("Accept: text/plain\r\n")
        self.io_sock.send("Connection: keep-alive\r\n")
        self.io_sock.send("\r\n")

        headers = read_block(self.io_sock)
        if not headers:
            raise IOError("disconnected while reading headers")
        if not "200" in headers[0]:
            raise IOError("wrong answer: %s" % headers[0])
        result = read_block(self.io_sock)
        if not result:
            raise IOError("disconnected while reading socketio session ID")
        if len(result) != 3:
            raise IOError("invalid response from socket.io server")

        ws_id = result[1].split(":")[0]
        resource = "%s/websocket/%s" % (resource, ws_id)
        if "query" in options:
            resource = "%s?%s" % (resource, options["query"])

        # now continue with the normal websocket GET and upgrade request
        self._handshake(hostname, port, resource, **options)


class PubnubClient(BaseClient):
    """"This implements the pubnub client. This client cannot send trade
    requests over the streamin API, therefore all interaction with MtGox has
    to happen through http(s) api, this client will enforce this flag to be
    set automatically."""
    def __init__(self, curr_base, curr_quote, secret, config):
        global FORCE_HTTP_API #pylint: disable=W0603
        BaseClient.__init__(self, curr_base, curr_quote, secret, config)
        FORCE_HTTP_API = True
        self._pubnub = None
        self._pubnub_priv = None
        self._private_thread_started = False
        self.stream_sorter = PubnubStreamSorter(
            self.config.get_float("pubnub", "stream_sorter_time_window"))
        self.stream_sorter.signal_pop.connect(self.signal_recv)
        self.stream_sorter.signal_debug.connect(self.signal_debug)

    def start(self):
        BaseClient.start(self)
        self.stream_sorter.start()

    def stop(self):
        """stop the client"""
        self._terminating = True
        self.stream_sorter.stop()
        self._timer.cancel()
        self.force_reconnect()

    def force_reconnect(self):
        self.connected = False
        self.signal_disconnected(self, None)
        # as long as the _terinating flag is not set
        # a hup() will just make them reconnect,
        # the same way a network failure would do.
        if self._pubnub_priv:
            self._pubnub_priv.hup()
        if self._pubnub:
            self._pubnub.hup()

    def send(self, _msg):
        # can't send with this client,
        self.debug("### invalid attempt to use send() with Pubnub client")

    def _recv_thread_func(self):
        self._pubnub = pubnub_light.PubNub()
        self._pubnub.subscribe(
            'sub-c-50d56e1e-2fd9-11e3-a041-02ee2ddab7fe',
            ",".join([
                CHANNELS['depth.%s%s' % (self.curr_base, self.curr_quote)],
                CHANNELS['ticker.%s%s' % (self.curr_base, self.curr_quote)],
                CHANNELS['trade.%s' % self.curr_base],
                CHANNELS['trade.lag']
            ]),
            "",
            "",
            self.config.get_bool("gox", "use_ssl")
        )

        # the following doesn't actually subscribe to the public channels
        # in this implementation, it only gets acct info and market data
        # and enqueue a request for the pricate channel auth credentials
        self.channel_subscribe(True)

        self.debug("### starting public channel pubnub client")
        while not self._terminating:
            try:
                while not self._terminating:
                    messages = self._pubnub.read()
                    self._time_last_received = time.time()
                    if not self.connected:
                        self.connected = True
                        self.signal_connected(self, None)
                    for _channel, message in messages:
                        self.stream_sorter.put(message)
            except Exception:
                self.debug("### public channel interrupted")
                #self.debug(traceback.format_exc())
                if not self._terminating:
                    time.sleep(1)
                    self.debug("### public channel restarting")

        self.debug("### public channel thread terminated")

    def _recv_private_thread_func(self):
        """thread for receiving the private messages"""
        self.debug("### starting private channel pubnub client")
        while not self._terminating:
            try:
                while not self._terminating:
                    messages = self._pubnub_priv.read()
                    self._time_last_received = time.time()
                    for _channel, message in messages:
                        self.stream_sorter.put(message)

            except Exception:
                self.debug("### private channel interrupted")
                #self.debug(traceback.format_exc())
                if not self._terminating:
                    time.sleep(1)
                    self.debug("### private channel restarting")

        self.debug("### private channel thread terminated")

    def _pubnub_receive(self, msg):
        """callback method called by pubnub when a message is received"""
        self.signal_recv(self, msg)
        self._time_last_received = time.time()
        return not self._terminating

    def channel_subscribe(self, download_market_data=False):
        # no channels to subscribe, this happened in PubNub.__init__ already
        if self.secret and self.secret.know_secret():
            self.enqueue_http_request("stream/private_get", {}, "idkey")

        self.request_info()
        self.request_orders()

        if download_market_data:
            if self.config.get_bool("gox", "load_fulldepth"):
                if not FORCE_NO_FULLDEPTH:
                    self.request_fulldepth()
            if self.config.get_bool("gox", "load_history"):
                if not FORCE_NO_HISTORY:
                    self.request_history()

        self._time_last_subscribed = time.time()

    def on_idkey_received(self, data):
        if not self._pubnub_priv:
            self.debug("### init private pubnub")
            self._pubnub_priv = pubnub_light.PubNub()

        self._pubnub_priv.subscribe(
            data["sub"],
            data["channel"],
            data["auth"],
            data["cipher"],
            self.config.get_bool("gox", "use_ssl")
        )

        if not self._private_thread_started:
            start_thread(self._recv_private_thread_func, "private channel thread")
            self._private_thread_started = True


class PubnubStreamSorter(BaseObject):
    """sort the incoming messages by "stamp" field. This will introduce
    a delay but its the only way to get these messages into proper order."""
    def __init__(self, delay):
        BaseObject.__init__(self)
        self.delay = delay
        self.queue = []
        self.terminating = False
        self.stat_last = 0
        self.stat_bad = 0
        self.stat_good = 0
        self.signal_pop = Signal()
        self.lock = threading.Lock()

    def start(self):
        """start the extraction thread"""
        start_thread(self._extract_thread_func, "message sorter thread")
        self.debug("### initialized stream sorter with %g s time window"
            % (self.delay))

    def put(self, message):
        """put a message into the queue"""
        stamp = int(message["stamp"]) / 1000000.0

        # sort it into the existing waiting messages
        self.lock.acquire()
        bisect.insort(self.queue, (stamp, time.time(), message))
        self.lock.release()

    def stop(self):
        """terminate the sorter thread"""
        self.terminating = True

    def _extract_thread_func(self):
        """this thread will permanently pop oldest messages
        from the queue after they have stayed delay time in
        it and fire signal_pop for each message."""
        while not self.terminating:
            self.lock.acquire()
            while self.queue \
            and self.queue[0][1] + self.delay < time.time():
                (stamp, _received, msg) = self.queue.pop(0)
                self._update_statistics(stamp, msg)
                self.signal_pop(self, (msg))
            self.lock.release()
            time.sleep(50E-3)

    def _update_statistics(self, stamp, _msg):
        """collect some statistics and print to log occasionally"""
        if stamp < self.stat_last:
            self.stat_bad += 1
            self.debug("### message late:", self.stat_last - stamp)
        else:
            self.stat_good += 1
        self.stat_last = stamp
        if self.stat_good % 2000 == 0:
            if self.stat_good + self.stat_bad > 0:
                self.debug("### stream sorter: good:%i bad:%i (%g%%)" % \
                    (self.stat_good, self.stat_bad, \
                    100.0 * self.stat_bad / (self.stat_bad + self.stat_good)))


class SocketIOClient(BaseClient):
    """this implements a connection to MtGox using the socketIO protocol."""

    def __init__(self, curr_base, curr_quote, secret, config):
        BaseClient.__init__(self, curr_base, curr_quote, secret, config)
        self.hostname = SOCKETIO_HOST
        self._timer.connect(self.slot_keepalive_timer)

    def _recv_thread_func(self):
        """this is the main thread that is running all the time. It will
        connect and then read (blocking) on the socket in an infinite
        loop. SocketIO messages ('2::', etc.) are handled here immediately
        and all received json strings are dispathed with signal_recv."""
        use_ssl = self.config.get_bool("gox", "use_ssl")
        wsp = {True: "wss://", False: "ws://"}[use_ssl]
        while not self._terminating: #loop 0 (connect, reconnect)
            try:
                url = "%s%s/socket.io/1" % (wsp, self.hostname)

                # subscribing depth and ticker through the querystring,
                # the trade and lag will be subscribed later after connect
                sym = "%s%s" % (self.curr_base, self.curr_quote)
                if not FORCE_NO_DEPTH:
                    querystring = "Channel=depth.%s/ticker.%s" % (sym, sym)
                else:
                    querystring = "Channel=ticker.%s" % (sym)
                self.debug("### trying Socket.IO: %s?%s ..." % (url, querystring))
                self.socket = SocketIO()
                self.socket.connect(url, query=querystring)

                self._time_last_received = time.time()
                self.connected = True
                self.debug("### connected")
                self.socket.send("1::/mtgox")

                self.debug(self.socket.recv())
                self.debug(self.socket.recv())

                self.debug("### subscribing to channels")
                self.channel_subscribe()

                self.debug("### waiting for data...")
                self.signal_connected(self, None)
                while not self._terminating: #loop1 (read messages)
                    msg = self.socket.recv()
                    self._time_last_received = time.time()
                    if msg == "2::":
                        #self.debug("### ping -> pong")
                        self.socket.send("2::")
                        continue
                    prefix = msg[:10]
                    if prefix == "4::/mtgox:":
                        str_json = msg[10:]
                        if str_json[0] == "{":
                            self.signal_recv(self, (str_json))

            except Exception as exc:
                self.connected = False
                self.signal_disconnected(self, None)
                if not self._terminating:
                    self.debug("### ", exc.__class__.__name__, exc, \
                        "reconnecting in 1 seconds...")
                    self.socket.close()
                    time.sleep(1)

    def send(self, json_str):
        """send a string to the websocket. This method will prepend it
        with the 1::/mtgox: that is needed for the socket.io protocol
        (as opposed to plain websockts) and the underlying websocket
        will then do the needed framing on top of that."""
        self._try_send_raw("4::/mtgox:" + json_str)

    def slot_keepalive_timer(self, _sender, _data):
        """send a keepalive, just to make sure our socket is not dead"""
        if self.connected:
            #self.debug("### sending keepalive")
            self._try_send_raw("2::")


# pylint: disable=R0902
class Gox(BaseObject):
    """represents the API of the MtGox exchange. An Instance of this
    class will connect to the streaming socket.io API, receive live
    events, it will emit signals you can hook into for all events,
    it has methods to buy and sell"""

    def __init__(self, secret, config):
        """initialize the gox API but do not yet connect to it."""
        BaseObject.__init__(self)

        self.signal_depth           = Signal()
        self.signal_trade           = Signal()
        self.signal_ticker          = Signal()
        self.signal_fulldepth       = Signal()
        self.signal_fullhistory     = Signal()
        self.signal_wallet          = Signal()
        self.signal_userorder       = Signal()
        self.signal_orderlag        = Signal()
        self.signal_disconnected    = Signal() # socket connection lost
        self.signal_ready           = Signal() # connected and fully initialized

        self.signal_order_too_fast  = Signal() # don't use that

        self.strategies = weakref.WeakValueDictionary()

        # the following are not fired by gox itself but by the
        # application controlling it to pass some of its events
        self.signal_keypress        = Signal()
        self.signal_strategy_unload = Signal()

        self._idkey      = ""
        self.wallet = {}
        self.trade_fee = 0  # percent (float, for example 0.6 means 0.6%)
        self.monthly_volume = 0 # BTC (satoshi int)
        self.order_lag = 0  # microseconds
        self.socket_lag = 0 # microseconds
        self.last_tid = 0
        self.count_submitted = 0  # number of submitted orders not yet acked
        self.msg = {} # the incoming message that is currently processed

        # the following will be set to true once the information
        # has been received after connect, once all thes flags are
        # true it will emit the signal_connected.
        self.ready_idkey = False
        self.ready_info = False
        self._was_disconnected = True

        self.config = config
        self.curr_base = config.get_string("gox", "base_currency")
        self.curr_quote = config.get_string("gox", "quote_currency")

        self.currency = self.curr_quote # deprecated, use curr_quote instead

        # these are needed for conversion from/to intereger, float, string
        if self.curr_quote in "JPY SEK":
            self.mult_quote = 1e3
            self.format_quote = "%12.3f"
        else:
            self.mult_quote = 1e5
            self.format_quote = "%12.5f"
        self.mult_base = 1e8
        self.format_base = "%16.8f"

        Signal.signal_error.connect(self.signal_debug)

        timeframe = 60 * config.get_int("gox", "history_timeframe")
        if not timeframe:
            timeframe = 60 * 15
        self.history = History(self, timeframe)
        self.history.signal_debug.connect(self.signal_debug)

        self.orderbook = OrderBook(self)
        self.orderbook.signal_debug.connect(self.signal_debug)

        use_websocket = self.config.get_bool("gox", "use_plain_old_websocket")
        use_pubnub = False

        if "socketio" in FORCE_PROTOCOL:
            use_websocket = False
        if "websocket" in FORCE_PROTOCOL:
            use_websocket = True
        if "pubnub" in FORCE_PROTOCOL:
            use_websocket = False
            use_pubnub = True

        if use_websocket:
            self.client = WebsocketClient(self.curr_base, self.curr_quote, secret, config)
        else:
            if use_pubnub:
                self.client = PubnubClient(self.curr_base, self.curr_quote, secret, config)
            else:
                self.client = SocketIOClient(self.curr_base, self.curr_quote, secret, config)

        self.client.signal_debug.connect(self.signal_debug)
        self.client.signal_disconnected.connect(self.slot_disconnected)
        self.client.signal_connected.connect(self.slot_client_connected)
        self.client.signal_recv.connect(self.slot_recv)
        self.client.signal_fulldepth.connect(self.signal_fulldepth)
        self.client.signal_fullhistory.connect(self.signal_fullhistory)

        self.timer_poll = Timer(120)
        self.timer_poll.connect(self.slot_poll)

        self.history.signal_changed.connect(self.slot_history_changed)
        self.history.signal_fullhistory_processed.connect(self.slot_fullhistory_processed)
        self.orderbook.signal_fulldepth_processed.connect(self.slot_fulldepth_processed)
        self.orderbook.signal_owns_initialized.connect(self.slot_owns_initialized)

    def start(self):
        """connect to MtGox and start receiving events."""
        self.debug("### starting gox streaming API, trading %s%s" %
            (self.curr_base, self.curr_quote))
        self.client.start()

    def stop(self):
        """shutdown the client"""
        self.debug("### shutdown...")
        self.client.stop()

    def order(self, typ, price, volume):
        """place pending order. If price=0 then it will be filled at market"""
        self.count_submitted += 1
        self.client.send_order_add(typ, price, volume)

    def buy(self, price, volume):
        """new buy order, if price=0 then buy at market"""
        self.order("bid", price, volume)

    def sell(self, price, volume):
        """new sell order, if price=0 then sell at market"""
        self.order("ask", price, volume)

    def cancel(self, oid):
        """cancel order"""
        self.client.send_order_cancel(oid)

    def cancel_by_price(self, price):
        """cancel all orders at price"""
        for i in reversed(range(len(self.orderbook.owns))):
            order = self.orderbook.owns[i]
            if order.price == price:
                if order.oid != "":
                    self.cancel(order.oid)

    def cancel_by_type(self, typ=None):
        """cancel all orders of type (or all orders if typ=None)"""
        for i in reversed(range(len(self.orderbook.owns))):
            order = self.orderbook.owns[i]
            if typ == None or typ == order.typ:
                if order.oid != "":
                    self.cancel(order.oid)

    def base2float(self, int_number):
        """convert base currency values from mtgox integer to float. Base
        currency are the coins you are trading (BTC, LTC, etc). Use this method
        to convert order volumes (amount of coins) from int to float."""
        return float(int_number) / self.mult_base

    def base2str(self, int_number):
        """convert base currency values from mtgox integer to formatted string"""
        return self.format_base % (float(int_number) / self.mult_base)

    def base2int(self, float_number):
        """convert base currency values from float to mtgox integer"""
        return int(round(float_number * self.mult_base))

    def quote2float(self, int_number):
        """convert quote currency values from mtgox integer to float. Quote
        currency is the currency used to quote prices (USD, EUR, etc), use this
        method to convert the prices of orders, bid or ask from int to float."""
        return float(int_number) / self.mult_quote

    def quote2str(self, int_number):
        """convert quote currency values from mtgox integer to formatted string"""
        return self.format_quote % (float(int_number) / self.mult_quote)

    def quote2int(self, float_number):
        """convert quote currency values from float to mtgox integer"""
        return int(round(float_number * self.mult_quote))

    def check_connect_ready(self):
        """check if everything that is needed has been downloaded
        and emit the connect signal if everything is ready"""
        need_no_account = not self.client.secret.know_secret()
        need_no_depth = not self.config.get_bool("gox", "load_fulldepth")
        need_no_history = not self.config.get_bool("gox", "load_history")
        need_no_depth = need_no_depth or FORCE_NO_FULLDEPTH
        need_no_history = need_no_history or FORCE_NO_HISTORY
        ready_account = \
            self.ready_idkey and self.ready_info and self.orderbook.ready_owns
        if ready_account or need_no_account:
            if self.orderbook.ready_depth or need_no_depth:
                if self.history.ready_history or need_no_history:
                    if self._was_disconnected:
                        self.signal_ready(self, None)
                        self._was_disconnected = False

    def slot_client_connected(self, _sender, _data):
        """connected to the client"""
        self.check_connect_ready()

    def slot_fulldepth_processed(self, _sender, _data):
        """connected to the orderbook"""
        self.check_connect_ready()

    def slot_fullhistory_processed(self, _sender, _data):
        """connected to the history"""
        self.check_connect_ready()

    def slot_owns_initialized(self, _sender, _data):
        """connected to the orderbook"""
        self.check_connect_ready()

    def slot_disconnected(self, _sender, _data):
        """this slot is connected to the client object, all it currently
        does is to emit a disconnected signal itself"""
        self.ready_idkey = False
        self.ready_info = False
        self.orderbook.ready_owns = False
        self.orderbook.ready_depth = False
        self.history.ready_history = False
        self._was_disconnected = True
        self.signal_disconnected(self, None)

    def slot_recv(self, dummy_sender, data):
        """Slot for signal_recv, handle new incoming JSON message. Decode the
        JSON string into a Python object and dispatch it to the method that
        can handle it."""
        (str_json) = data
        handler = None
        if type(str_json) == dict:
            msg = str_json # was already a dict
        else:
            msg = json.loads(str_json)
        self.msg = msg

        if "stamp" in msg:
            delay = time.time() * 1e6 - int(msg["stamp"])
            self.socket_lag = (self.socket_lag * 29 + delay) / 30

        if "op" in msg:
            try:
                msg_op = msg["op"]
                handler = getattr(self, "_on_op_" + msg_op)

            except AttributeError:
                self.debug("slot_recv() ignoring: op=%s" % msg_op)
        else:
            self.debug("slot_recv() ignoring:", msg)

        if handler:
            handler(msg)

    def slot_poll(self, _sender, _data):
        """poll stuff from http in regular intervals, not yet implemented"""
        if self.client.secret and self.client.secret.know_secret():
            # poll recent own trades
            # fixme: how do i do this, whats the api for this?
            pass

    def slot_history_changed(self, _sender, _data):
        """this is a small optimzation, if we tell the client the time
        of the last known candle then it won't fetch full history next time"""
        last_candle = self.history.last_candle()
        if last_candle:
            self.client.history_last_candle = last_candle.tim

    def _on_op_error(self, msg):
        """handle error mesages (op:error)"""
        self.debug("### _on_op_error()", msg)

    def _on_op_subscribe(self, msg):
        """handle subscribe messages (op:subscribe)"""
        self.debug("### subscribed channel", msg["channel"])

    def _on_op_result(self, msg):
        """handle result of authenticated API call (op:result, id:xxxxxx)"""
        result = msg["result"]
        reqid = msg["id"]

        if reqid == "idkey":
            self.debug("### got key, subscribing to account messages")
            self._idkey = result
            self.client.on_idkey_received(result)
            self.ready_idkey = True
            self.check_connect_ready()

        elif reqid == "orders":
            self.debug("### got own order list")
            self.count_submitted = 0
            self.orderbook.init_own(result)
            self.debug("### have %d own orders for %s/%s" %
                (len(self.orderbook.owns), self.curr_base, self.curr_quote))

        elif reqid == "info":
            self.debug("### got account info")
            gox_wallet = result["Wallets"]
            self.wallet = {}
            self.monthly_volume = int(result["Monthly_Volume"]["value_int"])
            self.trade_fee = float(result["Trade_Fee"])
            for currency in gox_wallet:
                self.wallet[currency] = int(
                    gox_wallet[currency]["Balance"]["value_int"])

            self.signal_wallet(self, None)
            self.ready_info = True
            self.check_connect_ready()

        elif reqid == "order_lag":
            lag_usec = result["lag"]
            lag_text = result["lag_text"]
            self.debug("### got order lag: %s" % lag_text)
            self.order_lag = lag_usec
            self.signal_orderlag(self, (lag_usec, lag_text))

        elif "order_add:" in reqid:
            # order/add has been acked and we got an oid, now we can already
            # insert a pending order into the owns list (it will be pending
            # for a while when the server is busy but the most important thing
            # is that we have the order-id already).
            parts = reqid.split(":")
            typ = parts[1]
            price = int(parts[2])
            volume = int(parts[3])
            oid = result
            self.debug("### got ack for order/add:", typ, price, volume, oid)
            self.count_submitted -= 1
            self.orderbook.add_own(Order(price, volume, typ, oid, "pending"))

        elif "order_cancel:" in reqid:
            # cancel request has been acked but we won't remove it from our
            # own list now because it is still active on the server.
            # do nothing now, let things happen in the user_order message
            parts = reqid.split(":")
            oid = parts[1]
            self.debug("### got ack for order/cancel:", oid)

        else:
            self.debug("### _on_op_result() ignoring:", msg)

    def _on_op_private(self, msg):
        """handle op=private messages, these are the messages of the channels
        we subscribed (trade, depth, ticker) and also the per-account messages
        (user_order, wallet, own trades, etc)"""
        private = msg["private"]
        handler = None
        try:
            handler = getattr(self, "_on_op_private_" + private)
        except AttributeError:
            self.debug("### _on_op_private() ignoring: private=%s" % private)
            self.debug(pretty_format(msg))

        if handler:
            handler(msg)

    def _on_op_private_ticker(self, msg):
        """handle incoming ticker message (op=private, private=ticker)"""
        msg = msg["ticker"]
        if msg["sell"]["currency"] != self.curr_quote:
            return
        if msg["item"] != self.curr_base:
            return
        bid = int(msg["buy"]["value_int"])
        ask = int(msg["sell"]["value_int"])

        self.debug(" tick: %s %s" % (
            self.quote2str(bid),
            self.quote2str(ask)
        ))
        self.signal_ticker(self, (bid, ask))

    def _on_op_private_depth(self, msg):
        """handle incoming depth message (op=private, private=depth)"""
        msg = msg["depth"]
        if msg["currency"] != self.curr_quote:
            return
        if msg["item"] != self.curr_base:
            return
        typ = msg["type_str"]
        price = int(msg["price_int"])
        volume = int(msg["volume_int"])
        timestamp = int(msg["now"])
        total_volume = int(msg["total_volume_int"])

        delay = time.time() * 1e6 - timestamp

        self.debug("depth: %s: %s @ %s total vol: %s (age: %0.2f s)" % (
            typ,
            self.base2str(volume),
            self.quote2str(price),
            self.base2str(total_volume),
            delay / 1e6
        ))
        self.signal_depth(self, (typ, price, volume, total_volume))

    def _on_op_private_trade(self, msg):
        """handle incoming trade mesage (op=private, private=trade)"""
        if msg["trade"]["price_currency"] != self.curr_quote:
            return
        if msg["trade"]["item"] != self.curr_base:
            return
        if msg["channel"] == CHANNELS["trade.%s" % self.curr_base]:
            own = False
        else:
            own = True
        date = int(msg["trade"]["date"])
        price = int(msg["trade"]["price_int"])
        volume = int(msg["trade"]["amount_int"])
        typ = msg["trade"]["trade_type"]

        if own:
            self.debug("trade: %s: %s @ %s (own order filled)" % (
                typ,
                self.base2str(volume),
                self.quote2str(price)
            ))
            # send another private/info request because the fee might have
            # changed. We request it a minute later because the server
            # seems to need some time until the new values are available.
            self.client.request_info_later(60)
        else:
            self.debug("trade: %s: %s @ %s" % (
                typ,
                self.base2str(volume),
                self.quote2str(price)
            ))

        self.signal_trade(self, (date, price, volume, typ, own))

    def _on_op_private_user_order(self, msg):
        """handle incoming user_order message (op=private, private=user_order)"""
        order = msg["user_order"]
        oid = order["oid"]

        # there exist 3 fundamentally different types of user_order messages,
        # they differ in the presence or absence of certain parts of the message

        if "status" in order:
            # these are limit orders or market orders (new or updated).
            #
            # we also need to check whether they belong to our own gox instance,
            # since they contain currency this is easy, we compare the currency
            # and simply ignore mesages for all unrelated currencies.
            if order["currency"] == self.curr_quote and order["item"] == self.curr_base:
                volume = int(order["amount"]["value_int"])
                typ = order["type"]
                status = order["status"]
                if "price" in order:
                    # these are limit orders (new or updated)
                    price = int(order["price"]["value_int"])
                else:
                    # these are market orders (new or updated)
                    price = 0
                self.signal_userorder(self, (price, volume, typ, oid, status))

        else:
            # these are remove messages (cancel or fill)
            # here it is a bit more expensive to check whether they belong to
            # this gox instance, they don't carry any other useful data besides
            # the order id and the remove reason but since a remove message can
            # only affect us if the oid is in the owns list already we just
            # ask the orderbook instance whether it knows about this order
            # and ignore all the ones that have unknown oid
            if self.orderbook.have_own_oid(oid):
                # they don't contain a status field either, so we make up
                # our own status string to make it more useful. It will
                # be "removed:" followed by the reason. Possible reasons are:
                # "requested", "completed_passive", "completed_active"
                # so for example a cancel would be "removed:requested"
                # and a limit order fill would be "removed:completed_passive".
                status = "removed:" + order["reason"]
                self.signal_userorder(self, (0, 0, "", oid, status))

    def _on_op_private_wallet(self, msg):
        """handle incoming wallet message (op=private, private=wallet)"""
        balance = msg["wallet"]["balance"]
        currency = balance["currency"]
        total = int(balance["value_int"])
        self.wallet[currency] = total
        self.signal_wallet(self, None)

    def _on_op_private_lag(self, msg):
        """handle the lag message"""
        self.order_lag = int(msg["lag"]["age"])
        if self.order_lag < 60000000:
            text = "%0.3f s" % (int(self.order_lag / 1000) / 1000.0)
        else:
            text = "%d s" % (int(self.order_lag / 1000000))
        self.signal_orderlag(self, (self.order_lag, text))

    def _on_op_remark(self, msg):
        """handler for op=remark messages"""

        if "success" in msg and not msg["success"]:
            if msg["message"] == "Invalid call":
                self._on_invalid_call(msg)
            elif msg["message"] == "Order not found":
                self._on_order_not_found(msg)
            elif msg["message"] == "Order amount is too low":
                self._on_order_amount_too_low(msg)
            elif "Too many orders placed" in msg["message"]:
                self._on_too_many_orders(msg)
            else:
                # we should log this, helps with debugging
                self.debug(msg)

    def _on_invalid_call(self, msg):
        """this comes as an op=remark message and is a strange mystery"""
        # Workaround: Maybe a bug in their server software,
        # I don't know what's missing. Its all poorly documented :-(
        # Sometimes some API calls fail the first time for no reason,
        # if this happens just send them again. This happens only
        # somtimes (10%) and sending them again will eventually succeed.

        if msg["id"] == "idkey":
            self.debug("### resending private/idkey")
            self.client.send_signed_call(
                "private/idkey", {}, "idkey")

        elif msg["id"] == "info":
            self.debug("### resending private/info")
            self.client.send_signed_call(
                "private/info", {}, "info")

        elif msg["id"] == "orders":
            self.debug("### resending private/orders")
            self.client.send_signed_call(
                "private/orders", {}, "orders")

        elif "order_add:" in msg["id"]:
            parts = msg["id"].split(":")
            typ = parts[1]
            price = int(parts[2])
            volume = int(parts[3])
            self.debug("### resending failed", msg["id"])
            self.client.send_order_add(typ, price, volume)

        elif "order_cancel:" in msg["id"]:
            parts = msg["id"].split(":")
            oid = parts[1]
            self.debug("### resending failed", msg["id"])
            self.client.send_order_cancel(oid)

        else:
            self.debug("### _on_invalid_call() ignoring:", msg)

    def _on_order_not_found(self, msg):
        """this means we have sent order/cancel with non-existing oid"""
        parts = msg["id"].split(":")
        oid = parts[1]
        self.debug("### got 'Order not found' for", oid)
        # we are now going to fake a user_order message (the one we
        # obviously missed earlier) that will have the effect of
        # removing the order cleanly.
        fakemsg = {"user_order": {"oid": oid, "reason": "requested"}}
        self._on_op_private_user_order(fakemsg)

    def _on_order_amount_too_low(self, _msg):
        """we received an order_amount too low message."""
        self.debug("### Server said: 'Order amount is too low'")
        self.count_submitted -= 1

    def _on_too_many_orders(self, msg):
        """server complains too many orders were placd too fast"""
        self.debug("### Server said: '%s" % msg["message"])
        self.count_submitted -= 1
        self.signal_order_too_fast(self, msg)


class Level:
    """represents a level in the orderbook"""
    def __init__(self, price, volume):
        self.price = price
        self.volume = volume
        self.own_volume = 0

        # these fields are only used to store temporary cache values
        # in some (not all!) levels and is calculated by the OrderBook
        # on demand, do not access this, use get_total_up_to() instead!
        self._cache_total_vol = 0
        self._cache_total_vol_quote = 0

class Order:
    """represents an order"""
    def __init__(self, price, volume, typ, oid="", status=""):
        """initialize a new order object"""
        self.price = price
        self.volume = volume
        self.typ = typ
        self.oid = oid
        self.status = status

class OrderBook(BaseObject):
    """represents the orderbook. Each Gox instance has one
    instance of OrderBook to maintain the open orders. This also
    maintains a list of own orders belonging to this account"""

    def __init__(self, gox):
        """create a new empty orderbook and associate it with its
        Gox instance, initialize it and connect its slots to gox"""
        BaseObject.__init__(self)
        self.gox = gox

        self.signal_changed             = Signal()
        """orderbook state has changed
        param: None
        an update to the state of the orderbook happened, this is emitted very
        often, it happens after every depth message, after every trade and
        also after every user_order message. This signal is for example used
        in goxtool.py to repaint the user interface of the orderbook window."""

        self.signal_fulldepth_processed = Signal()
        """fulldepth download is complete
        param: None
        The orderbook (fulldepth) has been downloaded from the server.
        This happens soon after connect."""

        self.signal_owns_initialized    = Signal()
        """own order list has been initialized
        param: None
        The owns list has been initialized. This happens soon after connect
        after it has downloaded the authoritative list of pending and open
        orders. This will also happen if it reinitialized after lost connection."""

        self.signal_owns_changed        = Signal()
        """owns list has changed
        param: None
        an update to the owns list has happened, this can be order added,
        removed or filled, status or volume of an order changed. For specific
        changes to individual orders see the signal_own_* signals below."""

        self.signal_own_added           = Signal()
        """order was added
        param: (order)
        order is a reference to the Order() instance
        This signal will be emitted whenever a new order is added to
        the owns list. Orders will initially have status "pending" and
        some time later there will be signal_own_opened when the status
        changed to open."""

        self.signal_own_removed         = Signal()
        """order has been removed
        param: (order, reason)
        order is a reference to the Order() instance
        reason is a string that can have the following values:
          "requested" order was canceled
          "completed_passive" limit order was filled completely
          "completed_active" market order was filled completely
        Bots will probably be interested in this signal because this is a
        reliable way to determine that a trade has fully completed because the
        trade signal alone won't tell you whether its partial or complete"""

        self.signal_own_opened          = Signal()
        """order status went to "open"
        param: (order)
        order is a reference to the Order() instance
        when the order changes from 'post-pending' to 'open' then this
        signal will be emitted. It won't be emitted for market orders because
        market orders can't have an "open" status, they never move beyond
        "executing", they just execute and emit volume and removed signals."""

        self.signal_own_volume          = Signal()
        """order volume changed (partial fill)
        param: (order, voldiff)
        order is a reference to the Order() instance
        voldiff is the differenc in volume, so for a partial or a complete fill
        it would contain a negative value (integer number of satoshi) of the
        difference between now and the previous volume. This signal is always
        emitted when an order is filled or partially filled, it can be emitted
        multiple times just like the trade messages. It will be emitted for
        all types of orders. The last volume signal that finally brouhgt the
        remaining order volume down to zero will be immediately followed by
        a removed signal."""

        self.bids = [] # list of Level(), lowest ask first
        self.asks = [] # list of Level(), highest bid first
        self.owns = [] # list of Order(), unordered list

        self.bid = 0
        self.ask = 0
        self.total_bid = 0
        self.total_ask = 0

        self.ready_depth = False
        self.ready_owns = False

        self.last_change_type = None # ("bid", "ask", None) this can be used
        self.last_change_price = 0   # for highlighting relative changes
        self.last_change_volume = 0  # of orderbook levels in goxtool.py

        self._valid_bid_cache = -1   # index of bid with valid _cache_total_vol
        self._valid_ask_cache = -1   # index of ask with valid _cache_total_vol

        gox.signal_ticker.connect(self.slot_ticker)
        gox.signal_depth.connect(self.slot_depth)
        gox.signal_trade.connect(self.slot_trade)
        gox.signal_userorder.connect(self.slot_user_order)
        gox.signal_fulldepth.connect(self.slot_fulldepth)

    def slot_ticker(self, dummy_sender, data):
        """Slot for signal_ticker, incoming ticker message"""
        (bid, ask) = data
        self.bid = bid
        self.ask = ask
        self.last_change_type = None
        self.last_change_price = 0
        self.last_change_volume = 0
        self._repair_crossed_asks(ask)
        self._repair_crossed_bids(bid)
        self.signal_changed(self, None)

    def slot_depth(self, dummy_sender, data):
        """Slot for signal_depth, process incoming depth message"""
        (typ, price, _voldiff, total_vol) = data
        if self._update_book(typ, price, total_vol):
            self.signal_changed(self, None)

    def slot_trade(self, dummy_sender, data):
        """Slot for signal_trade event, process incoming trade messages.
        For trades that also affect own orders this will be called twice:
        once during the normal public trade message, affecting the public
        bids and asks and then another time with own=True to update our
        own orders list"""
        (dummy_date, price, volume, typ, own) = data
        if own:
            # nothing special to do here (yet), there will also be
            # separate user_order messages to update my owns list
            # and a copy of this trade message in the public channel
            pass
        else:
            # we update the orderbook. We could also wait for the depth
            # message but we update the orderbook immediately.
            voldiff = -volume
            if typ == "bid":  # tryde_type=bid means an ask order was filled
                self._repair_crossed_asks(price)
                if len(self.asks):
                    if self.asks[0].price == price:
                        self.asks[0].volume -= volume
                        if self.asks[0].volume <= 0:
                            voldiff -= self.asks[0].volume
                            self.asks.pop(0)
                        self.last_change_type = "ask" #the asks have changed
                        self.last_change_price = price
                        self.last_change_volume = voldiff
                        self._update_total_ask(voldiff)
                        self._valid_ask_cache = -1
                if len(self.asks):
                    self.ask = self.asks[0].price

            if typ == "ask":  # trade_type=ask means a bid order was filled
                self._repair_crossed_bids(price)
                if len(self.bids):
                    if self.bids[0].price == price:
                        self.bids[0].volume -= volume
                        if self.bids[0].volume <= 0:
                            voldiff -= self.bids[0].volume
                            self.bids.pop(0)
                        self.last_change_type = "bid" #the bids have changed
                        self.last_change_price = price
                        self.last_change_volume = voldiff
                        self._update_total_bid(voldiff, price)
                        self._valid_bid_cache = -1
                if len(self.bids):
                    self.bid = self.bids[0].price

        self.signal_changed(self, None)

    def slot_user_order(self, dummy_sender, data):
        """Slot for signal_userorder, process incoming user_order mesage"""
        (price, volume, typ, oid, status) = data
        found   = False
        removed = False # was the order removed?
        opened  = False # did the order change from 'post-pending' to 'open'"?
        voldiff = 0     # did the order volume change (full or partial fill)
        if "executing" in status:
            # don't need this status at all
            return
        if "post-pending" in status:
            # don't need this status at all
            return
        if "removed" in status:
            for i in range(len(self.owns)):
                if self.owns[i].oid == oid:
                    order = self.owns[i]

                    # work around MtGox strangeness:
                    # for some reason it will send a "completed_passive"
                    # immediately followed by a "completed_active" when a
                    # market order is filled and removed. Since "completed_passive"
                    # is meant for limit orders only we will just completely
                    # IGNORE all "completed_passive" if it affects a market order,
                    # there WILL follow a "completed_active" immediately after.
                    if order.price == 0:
                        if "passive" in status:
                            # ignore it, the correct one with
                            # "active" will follow soon
                            return

                    self.debug(
                        "### removing order %s " % oid,
                        "price:", self.gox.quote2str(order.price),
                        "type:", order.typ)

                    # remove it from owns...
                    self.owns.pop(i)

                    # ...and update own volume cache in the bids or asks
                    self._update_level_own_volume(
                        order.typ,
                        order.price,
                        self.get_own_volume_at(order.price, order.typ)
                    )
                    removed = True
                    break
        else:
            for order in self.owns:
                if order.oid == oid:
                    found = True
                    self.debug(
                        "### updating order %s " % oid,
                        "volume:", self.gox.base2str(volume),
                        "status:", status)
                    voldiff = volume - order.volume
                    opened = (order.status != "open" and status == "open")
                    order.volume = volume
                    order.status = status
                    break

            if not found:
                # This can happen if we added the order with a different
                # application or the gox server sent the user_order message
                # before the reply to "order/add" (this can happen because
                # actually there is no guarantee which one arrives first).
                # We will treat this like a reply to "order/add"
                self.add_own(Order(price, volume, typ, oid, status))

                # The add_own() method has handled everything that was needed
                # for new orders and also emitted all signals already, we
                # can immediately return here because the job is done.
                return

            # update level own volume cache
            self._update_level_own_volume(
                typ, price, self.get_own_volume_at(price, typ))

        # We try to help the strategy with tracking the orders as good
        # as we can by sending different signals for different events.
        if removed:
            reason = self.gox.msg["user_order"]["reason"]
            self.signal_own_removed(self, (order, reason))
        if opened:
            self.signal_own_opened(self, (order))
        if voldiff:
            self.signal_own_volume(self, (order, voldiff))
        self.signal_changed(self, None)
        self.signal_owns_changed(self, None)

    def slot_fulldepth(self, dummy_sender, data):
        """Slot for signal_fulldepth, process received fulldepth data.
        This will clear the book and then re-initialize it from scratch."""
        (depth) = data
        self.debug("### got full depth, updating orderbook...")
        self.bids = []
        self.asks = []
        self.total_ask = 0
        self.total_bid = 0
        if "error" in depth:
            self.debug("### ", depth["error"])
            return
        for order in depth["data"]["asks"]:
            price = int(order["price_int"])
            volume = int(order["amount_int"])
            self._update_total_ask(volume)
            self.asks.append(Level(price, volume))
        for order in depth["data"]["bids"]:
            price = int(order["price_int"])
            volume = int(order["amount_int"])
            self._update_total_bid(volume, price)
            self.bids.insert(0, Level(price, volume))

        # update own volume cache
        for order in self.owns:
            self._update_level_own_volume(
                order.typ, order.price, self.get_own_volume_at(order.price, order.typ))

        if len(self.bids):
            self.bid = self.bids[0].price
        if len(self.asks):
            self.ask = self.asks[0].price

        self._valid_ask_cache = -1
        self._valid_bid_cache = -1
        self.ready_depth = True
        self.signal_fulldepth_processed(self, None)
        self.signal_changed(self, None)

    def _repair_crossed_bids(self, bid):
        """remove all bids that are higher that official current bid value,
        this should actually never be necessary if their feed would not
        eat depth- and trade-messages occaionally :-("""
        while len(self.bids) and self.bids[0].price > bid:
            price = self.bids[0].price
            volume = self.bids[0].volume
            self._update_total_bid(-volume, price)
            self.bids.pop(0)
            self._valid_bid_cache = -1
            #self.debug("### repaired bid")

    def _repair_crossed_asks(self, ask):
        """remove all asks that are lower that official current ask value,
        this should actually never be necessary if their feed would not
        eat depth- and trade-messages occaionally :-("""
        while len(self.asks) and self.asks[0].price < ask:
            volume = self.asks[0].volume
            self._update_total_ask(-volume)
            self.asks.pop(0)
            self._valid_ask_cache = -1
            #self.debug("### repaired ask")

    def _update_book(self, typ, price, total_vol):
        """update the bids or asks list, insert or remove level and
        also update all other stuff that needs to be tracked such as
        total volumes and invalidate the total volume cache index.
        Return True if book has changed, return False otherwise"""
        (lst, index, level) = self._find_level(typ, price)
        if total_vol == 0:
            if level == None:
                return False
            else:
                voldiff = -level.volume
                lst.pop(index)
        else:
            if level == None:
                voldiff = total_vol
                level = Level(price, total_vol)
                lst.insert(index, level)
            else:
                voldiff = total_vol - level.volume
                if voldiff == 0:
                    return False
                level.volume = total_vol

        # now keep all the other stuff in sync with it
        self.last_change_type = typ
        self.last_change_price = price
        self.last_change_volume = voldiff
        if typ == "ask":
            self._update_total_ask(voldiff)
            if len(self.asks):
                self.ask = self.asks[0].price
            self._valid_ask_cache = min(self._valid_ask_cache, index - 1)
        else:
            self._update_total_bid(voldiff, price)
            if len(self.bids):
                self.bid = self.bids[0].price
            self._valid_bid_cache = min(self._valid_bid_cache, index - 1)

        return True

    def _update_total_ask(self, volume):
        """update total volume of base currency on the ask side"""
        self.total_ask += self.gox.base2float(volume)

    def _update_total_bid(self, volume, price):
        """update total volume of quote currency on the bid side"""
        self.total_bid += \
            self.gox.base2float(volume) * self.gox.quote2float(price)

    def _update_level_own_volume(self, typ, price, own_volume):
        """update the own_volume cache in the Level object at price"""

        if price == 0:
            # market orders have price == 0, we don't add them
            # to the orderbook, own_volume is meant for limit orders.
            # Also a price level of 0 makes no sense anyways, this
            # would only insert empty rows at price=0 into the book
            return

        (index, level) = self._find_level_or_insert_new(typ, price)
        if level.volume == 0 and own_volume == 0:
            if typ == "ask":
                self.asks.pop(index)
            else:
                self.bids.pop(index)
        else:
            level.own_volume = own_volume

    def _find_level(self, typ, price):
        """find the level in the orderbook and return a triple
        (list, index, level) where list is a reference to the list,
        index is the index if its an exact match or the index of the next
        element if it was not found (can be used for inserting) and level
        is either a reference to the found level or None if not found."""
        lst = {"ask": self.asks, "bid": self.bids}[typ]
        comp = {"ask": lambda x, y: x < y, "bid": lambda x, y: x > y}[typ]
        low = 0
        high = len(lst)

        # binary search
        while low < high:
            mid = (low + high) // 2
            midval = lst[mid].price
            if comp(midval, price):
                low = mid + 1
            elif comp(price, midval):
                high = mid
            else:
                return (lst, mid, lst[mid])

        # not found, return insertion point (index of next higher level)
        return (lst, high, None)

    def _find_level_or_insert_new(self, typ, price):
        """find the Level() object in bids or asks or insert a new
        Level() at the correct position. Returns tuple (index, level)"""
        (lst, index, level) = self._find_level(typ, price)
        if level:
            return (index, level)

        # no exact match found, create new Level() and insert
        level = Level(price, 0)
        lst.insert(index, level)

        # invalidate the total volume cache at and beyond this level
        if typ == "ask":
            self._valid_ask_cache = min(self._valid_ask_cache, index - 1)
        else:
            self._valid_bid_cache = min(self._valid_bid_cache, index - 1)

        return (index, level)

    def get_own_volume_at(self, price, typ=None):
        """returns the sum of the volume of own orders at a given price. This
        method will not look up the cache in the bids or asks lists, it will
        use the authoritative data from the owns list bacause this method is
        also used to calculate these cached values in the first place."""
        volume = 0
        for order in self.owns:
            if order.price == price and (not typ or typ == order.typ):
                volume += order.volume
        return volume

    def have_own_oid(self, oid):
        """do we have an own order with this oid in our list already?"""
        for order in self.owns:
            if order.oid == oid:
                return True
        return False

    # pylint: disable=W0212
    def get_total_up_to(self, price, is_ask):
        """return a tuple of the total volume in coins and in fiat between top
        and this price. This will calculate the total on demand, it has a cache
        to not repeat the same calculations more often than absolutely needed"""
        if is_ask:
            lst = self.asks
            known_level = self._valid_ask_cache
            comp = lambda x, y: x < y
        else:
            lst = self.bids
            known_level = self._valid_bid_cache
            comp = lambda x, y: x > y

        # now first we need the list index of the level we are looking for or
        # if it doesn't match exactly the index of the level right before that
        # price, for this we do a quick binary search for the price
        low = 0
        high = len(lst)
        while low < high:
            mid = (low + high) // 2
            midval = lst[mid].price
            if comp(midval, price):
                low = mid + 1
            elif comp(price, midval):
                high = mid
            else:
                break
        if comp(price, midval):
            needed_level = mid - 1
        else:
            needed_level = mid

        # if the total volume at this level has been calculated
        # already earlier then we don't need to do anything further,
        # we can immediately return the cached value from that level.
        if needed_level <= known_level:
            lvl = lst[needed_level]
            return (lvl._cache_total_vol, lvl._cache_total_vol_quote)

        # we are still here, this means we must calculate and update
        # all totals in all levels between last_known and needed_level
        # after that is done we can return the total at needed_level.
        if known_level == -1:
            total = 0
            total_quote = 0
        else:
            total = lst[known_level]._cache_total_vol
            total_quote = lst[known_level]._cache_total_vol_quote

        mult_base = self.gox.mult_base
        for i in range(known_level, needed_level):
            that = lst[i+1]
            total += that.volume
            total_quote += that.volume * that.price / mult_base
            that._cache_total_vol = total
            that._cache_total_vol_quote = total_quote

        if is_ask:
            self._valid_ask_cache = needed_level
        else:
            self._valid_bid_cache = needed_level

        return (total, total_quote)

    def init_own(self, own_orders):
        """called by gox when the initial order list is downloaded,
        this will happen after connect or reconnect"""
        self.owns = []

        # also reset the own volume cache in bids and ass list
        for level in self.bids + self.asks:
            level.own_volume = 0

        if own_orders:
            for order in own_orders:
                if order["currency"] == self.gox.curr_quote \
                and order["item"] == self.gox.curr_base:
                    self._add_own(Order(
                        int(order["price"]["value_int"]),
                        int(order["amount"]["value_int"]),
                        order["type"],
                        order["oid"],
                        order["status"]
                    ))

        self.ready_owns = True
        self.signal_changed(self, None)
        self.signal_owns_initialized(self, None)
        self.signal_owns_changed(self, None)

    def add_own(self, order):
        """called by gox when a new order has been acked after it has been
        submitted or after a receiving a user_order message for a new order.
        This is a separate method from _add_own because we additionally need
        to fire the a bunch of signals when this happens"""
        if not self.have_own_oid(order.oid):
            self.debug("### adding order:",
                order.typ, order.price, order.volume, order.oid)
            self._add_own(order)
            self.signal_own_added(self, (order))
            self.signal_changed(self, None)
            self.signal_owns_changed(self, None)

    def _add_own(self, order):
        """add order to the list of own orders. This method is used during
        initial download of complete order list."""
        if not self.have_own_oid(order.oid):
            self.owns.append(order)

            # update own volume in that level:
            self._update_level_own_volume(
                order.typ,
                order.price,
                self.get_own_volume_at(order.price, order.typ)
            )

########NEW FILE########
__FILENAME__ = goxtool
#!/usr/bin/env python2

"""
Tool to display live MtGox market info and
framework for experimenting with trading bots
"""
#  Copyright (c) 2013 Bernd Kreuss <prof7bit@gmail.com>
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.

# pylint: disable=C0301,C0302,R0902,R0903,R0912,R0913,R0914,R0915,R0922,W0703

import argparse
import curses
import curses.panel
import curses.textpad
import goxapi
import logging
import locale
import math
import os
import sys
import time
import traceback
import threading

sys_out = sys.stdout #pylint: disable=C0103

#
#
# curses user interface
#

HEIGHT_STATUS   = 2
HEIGHT_CON      = 7
WIDTH_ORDERBOOK = 45

COLORS =    [["con_text",       curses.COLOR_BLUE,    curses.COLOR_CYAN]
            ,["con_text_buy",   curses.COLOR_BLUE,    curses.COLOR_GREEN]
            ,["con_text_sell",  curses.COLOR_BLUE,    curses.COLOR_RED]
            ,["status_text",    curses.COLOR_BLUE,    curses.COLOR_CYAN]

            ,["book_text",      curses.COLOR_BLACK,   curses.COLOR_CYAN]
            ,["book_bid",       curses.COLOR_BLACK,   curses.COLOR_GREEN]
            ,["book_ask",       curses.COLOR_BLACK,   curses.COLOR_RED]
            ,["book_own",       curses.COLOR_BLACK,   curses.COLOR_YELLOW]
            ,["book_vol",       curses.COLOR_BLACK,   curses.COLOR_CYAN]

            ,["chart_text",     curses.COLOR_BLACK,   curses.COLOR_WHITE]
            ,["chart_up",       curses.COLOR_BLACK,   curses.COLOR_GREEN]
            ,["chart_down",     curses.COLOR_BLACK,   curses.COLOR_RED]
            ,["order_pending",  curses.COLOR_BLACK,   curses.COLOR_RED]

            ,["dialog_text",     curses.COLOR_BLUE,   curses.COLOR_CYAN]
            ,["dialog_sel",      curses.COLOR_CYAN,   curses.COLOR_BLUE]
            ,["dialog_sel_text", curses.COLOR_BLUE,   curses.COLOR_YELLOW]
            ,["dialog_sel_sel",  curses.COLOR_YELLOW, curses.COLOR_BLUE]
            ,["dialog_bid_text", curses.COLOR_GREEN,  curses.COLOR_BLACK]
            ,["dialog_ask_text", curses.COLOR_RED,    curses.COLOR_WHITE]
            ]

INI_DEFAULTS =  [["goxtool", "set_xterm_title", "True"]
                ,["goxtool", "dont_truncate_logfile", "False"]
                ,["goxtool", "show_orderbook_stats", "True"]
                ,["goxtool", "highlight_changes", "True"]
                ,["goxtool", "orderbook_group", "0"]
                ,["goxtool", "orderbook_sum_total", "False"]
                ,["goxtool", "display_right", "history_chart"]
                ,["goxtool", "depth_chart_group", "1"]
                ,["goxtool", "depth_chart_sum_total", "True"]
                ,["goxtool", "show_ticker", "True"]
                ,["goxtool", "show_depth", "True"]
                ,["goxtool", "show_trade", "True"]
                ,["goxtool", "show_trade_own", "True"]
                ]

COLOR_PAIR = {}

def init_colors():
    """initialize curses color pairs and give them names. The color pair
    can then later quickly be retrieved from the COLOR_PAIR[] dict"""
    index = 1
    for (name, back, fore) in COLORS:
        if curses.has_colors():
            curses.init_pair(index, fore, back)
            COLOR_PAIR[name] = curses.color_pair(index)
        else:
            COLOR_PAIR[name] = 0
        index += 1

def dump_all_stacks():
    """dump a stack trace for all running threads for debugging purpose"""

    def get_name(thread_id):
        """return the human readable name that was assigned to a thread"""
        for thread in threading.enumerate():
            if thread.ident == thread_id:
                return thread.name

    ret = "\n# Full stack trace of all running threads:\n"
    #pylint: disable=W0212
    for thread_id, stack in sys._current_frames().items():
        ret += "\n# %s (%s)\n" % (get_name(thread_id), thread_id)
        for filename, lineno, name, line in traceback.extract_stack(stack):
            ret += 'File: "%s", line %d, in %s\n' % (filename, lineno, name)
            if line:
                ret += "  %s\n" % (line.strip())
    return ret

def try_get_lock_or_break_open():
    """this is an ugly hack to workaround possible deadlock problems.
    It is used during shutdown to make sure we can properly exit even when
    some slot is stuck (due to a programming error) and won't release the lock.
    If we can't acquire it within 2 seconds we just break it open forcefully."""
    #pylint: disable=W0212
    time_end = time.time() + 2
    while time.time() < time_end:
        if goxapi.Signal._lock.acquire(False):
            return
        time.sleep(0.001)

    # something keeps holding the lock, apparently some slot is stuck
    # in an infinite loop. In order to be able to shut down anyways
    # we just throw away that lock and replace it with a new one
    lock = threading.RLock()
    lock.acquire()
    goxapi.Signal._lock = lock
    print "### could not acquire signal lock, frozen slot somewhere?"
    print "### please see the stacktrace log to determine the cause."

class Win:
    """represents a curses window"""
    # pylint: disable=R0902

    def __init__(self, stdscr):
        """create and initialize the window. This will also subsequently
        call the paint() method."""
        self.stdscr = stdscr
        self.posx = 0
        self.posy = 0
        self.width = 10
        self.height = 10
        self.termwidth = 10
        self.termheight = 10
        self.win = None
        self.panel = None
        self.__create_win()

    def __del__(self):
        del self.panel
        del self.win
        curses.panel.update_panels()
        curses.doupdate()

    def calc_size(self):
        """override this method to change posx, posy, width, height.
        It will be called before window creation and on resize."""
        pass

    def do_paint(self):
        """call this if you want the window to repaint itself"""
        curses.curs_set(0)
        if self.win:
            self.paint()
            self.done_paint()

    # method could be a function - pylint: disable=R0201
    def done_paint(self):
        """update the sreen after paint operations, this will invoke all
        necessary stuff to refresh all (possibly overlapping) windows in
        the right order and then push it to the screen"""
        curses.panel.update_panels()
        curses.doupdate()

    def paint(self):
        """paint the window. Override this with your own implementation.
        This method must paint the entire window contents from scratch.
        It is automatically called after the window has been initially
        created and also after every resize. Call it explicitly when
        your data has changed and must be displayed"""
        pass

    def resize(self):
        """You must call this method from your main loop when the
        terminal has been resized. It will subsequently make it
        recalculate its own new size and then call its paint() method"""
        del self.win
        self.__create_win()

    def addstr(self, *args):
        """drop-in replacement for addstr that will never raie exceptions
        and that will cut off at end of line instead of wrapping"""
        if len(args) > 0:
            line, col = self.win.getyx()
            string = args[0]
            attr = 0
        if len(args) > 1:
            attr = args[1]
        if len(args) > 2:
            line, col, string = args[:3]
            attr = 0
        if len(args) > 3:
            attr = args[3]
        if line >= self.height:
            return
        space_left = self.width - col - 1 #always omit last column, avoids problems.
        if space_left <= 0:
            return
        self.win.addstr(line, col, string[:space_left], attr)

    def addch(self, posy, posx, character, color_pair):
        """place a character but don't throw error in lower right corner"""
        if posy < 0 or posy > self.height - 1:
            return
        if posx < 0 or posx > self.width - 1:
            return
        if posx == self.width - 1 and posy == self.height - 1:
            return
        self.win.addch(posy, posx, character, color_pair)

    def __create_win(self):
        """create the window. This will also be called on every resize,
        windows won't be moved, they will be deleted and recreated."""
        self.__calc_size()
        try:
            self.win = curses.newwin(self.height, self.width, self.posy, self.posx)
            self.panel = curses.panel.new_panel(self.win)
            self.win.scrollok(True)
            self.win.keypad(1)
            self.do_paint()
        except Exception:
            self.win = None
            self.panel = None

    def __calc_size(self):
        """calculate the default values for positionand size. By default
        this will result in a window covering the entire terminal.
        Implement the calc_size() method (which will be called afterwards)
        to change (some of) these values according to your needs."""
        maxyx = self.stdscr.getmaxyx()
        self.termwidth = maxyx[1]
        self.termheight = maxyx[0]
        self.posx = 0
        self.posy = 0
        self.width = self.termwidth
        self.height = self.termheight
        self.calc_size()


class WinConsole(Win):
    """The console window at the bottom"""
    def __init__(self, stdscr, gox):
        """create the console window and connect it to the Gox debug
        callback function"""
        self.gox = gox
        gox.signal_debug.connect(self.slot_debug)
        Win.__init__(self, stdscr)

    def paint(self):
        """just empty the window after resize (I am lazy)"""
        self.win.bkgd(" ", COLOR_PAIR["con_text"])

    def resize(self):
        """resize and print a log message. Old messages will have been
        lost after resize because of my dumb paint() implementation, so
        at least print a message indicating that fact into the
        otherwise now empty console window"""
        Win.resize(self)
        self.write("### console has been resized")

    def calc_size(self):
        """put it at the bottom of the screen"""
        self.height = HEIGHT_CON
        self.posy = self.termheight - self.height

    def slot_debug(self, dummy_gox, (txt)):
        """this slot will be connected to all debug signals."""
        self.write(txt)

    def write(self, txt):
        """write a line of text, scroll if needed"""
        if not self.win:
            return

        # This code would break if the format of
        # the log messages would ever change!
        if " tick:" in txt:
            if not self.gox.config.get_bool("goxtool", "show_ticker"):
                return
        if "depth:" in txt:
            if not self.gox.config.get_bool("goxtool", "show_depth"):
                return
        if "trade:" in txt:
            if "own order" in txt:
                if not self.gox.config.get_bool("goxtool", "show_trade_own"):
                    return
            else:
                if not self.gox.config.get_bool("goxtool", "show_trade"):
                    return

        col = COLOR_PAIR["con_text"]
        if "trade: bid:" in txt:
            col = COLOR_PAIR["con_text_buy"] + curses.A_BOLD
        if "trade: ask:" in txt:
            col = COLOR_PAIR["con_text_sell"] + curses.A_BOLD
        self.win.addstr("\n" + txt,  col)
        self.done_paint()


class WinOrderBook(Win):
    """the orderbook window"""

    def __init__(self, stdscr, gox):
        """create the orderbook window and connect it to the
        onChanged callback of the gox.orderbook instance"""
        self.gox = gox
        gox.orderbook.signal_changed.connect(self.slot_changed)
        Win.__init__(self, stdscr)

    def calc_size(self):
        """put it into the middle left side"""
        self.height = self.termheight - HEIGHT_CON - HEIGHT_STATUS
        self.posy = HEIGHT_STATUS
        self.width = WIDTH_ORDERBOOK

    def paint(self):
        """paint the visible portion of the orderbook"""

        def paint_row(pos, price, vol, ownvol, color, changevol):
            """paint a row in the orderbook (bid or ask)"""
            if changevol > 0:
                col2 = col_bid + curses.A_BOLD
            elif changevol < 0:
                col2 = col_ask + curses.A_BOLD
            else:
                col2 = col_vol
            self.addstr(pos, 0,  book.gox.quote2str(price), color)
            self.addstr(pos, 12, book.gox.base2str(vol), col2)
            if ownvol:
                self.addstr(pos, 28, book.gox.base2str(ownvol), col_own)

        self.win.bkgd(" ",  COLOR_PAIR["book_text"])
        self.win.erase()

        gox = self.gox
        book = gox.orderbook

        mid = self.height / 2
        col_bid = COLOR_PAIR["book_bid"]
        col_ask = COLOR_PAIR["book_ask"]
        col_vol = COLOR_PAIR["book_vol"]
        col_own = COLOR_PAIR["book_own"]

        sum_total = gox.config.get_bool("goxtool", "orderbook_sum_total")
        group = gox.config.get_float("goxtool", "orderbook_group")
        group = gox.quote2int(group)
        if group == 0:
            group = 1

        #
        #
        # paint the asks (first we put them into bins[] then we paint them)
        #
        if len(book.asks):
            i = 0
            bins = []
            pos = mid - 1
            vol = 0
            prev_vol = 0

            # no grouping, bins can be created in one simple and fast loop
            if group == 1:
                cnt = len(book.asks)
                while pos >= 0 and i < cnt:
                    level = book.asks[i]
                    price = level.price
                    if sum_total:
                        vol += level.volume
                    else:
                        vol = level.volume
                    ownvol = level.own_volume
                    bins.append([pos, price, vol, ownvol, 0])
                    pos -= 1
                    i += 1

            # with gouping its a bit more complicated
            else:
                # first bin is exact lowest ask price
                price = book.asks[0].price
                vol = book.asks[0].volume
                bins.append([pos, price, vol, 0, 0])
                prev_vol = vol
                pos -= 1

                # now all following bins
                bin_price = int(math.ceil(float(price) / group) * group)
                if bin_price == price:
                    # first level was exact bin price already, skip to next bin
                    bin_price += group
                while pos >= 0 and bin_price < book.asks[-1].price + group:
                    vol, _vol_quote = book.get_total_up_to(bin_price, True)          ## 01 freeze
                    if vol > prev_vol:
                        # append only non-empty bins
                        if sum_total:
                            bins.append([pos, bin_price, vol, 0, 0])
                        else:
                            bins.append([pos, bin_price, vol - prev_vol, 0, 0])
                        prev_vol = vol
                        pos -= 1
                    bin_price += group

                # now add the own volumes to their bins
                for order in book.owns:
                    if order.typ == "ask" and order.price > 0:
                        order_bin_price = int(math.ceil(float(order.price) / group) * group)
                        for abin in bins:
                            if abin[1] == order.price:
                                abin[3] += order.volume
                                break
                            if abin[1] == order_bin_price:
                                abin[3] += order.volume
                                break

            # mark the level where change took place (optional)
            if gox.config.get_bool("goxtool", "highlight_changes"):
                if book.last_change_type == "ask":
                    change_bin_price = int(math.ceil(float(book.last_change_price) / group) * group)
                    for abin in bins:
                        if abin[1] == book.last_change_price:
                            abin[4] = book.last_change_volume
                            break
                        if abin[1] == change_bin_price:
                            abin[4] = book.last_change_volume
                            break

            # now finally paint the asks
            for pos, price, vol, ownvol, changevol in bins:
                paint_row(pos, price, vol, ownvol, col_ask, changevol)

        #
        #
        # paint the bids (first we put them into bins[] then we paint them)
        #
        if len(book.bids):
            i = 0
            bins = []
            pos = mid + 1
            vol = 0
            prev_vol = 0

            # no grouping, bins can be created in one simple and fast loop
            if group == 1:
                cnt = len(book.bids)
                while pos < self.height and i < cnt:
                    level = book.bids[i]
                    price = level.price
                    if sum_total:
                        vol += level.volume
                    else:
                        vol = level.volume
                    ownvol = level.own_volume
                    bins.append([pos, price, vol, ownvol, 0])
                    prev_vol = vol
                    pos += 1
                    i += 1

            # with gouping its a bit more complicated
            else:
                # first bin is exact lowest ask price
                price = book.bids[0].price
                vol = book.bids[0].volume
                bins.append([pos, price, vol, 0, 0])
                prev_vol = vol
                pos += 1

                # now all following bins
                bin_price = int(math.floor(float(price) / group) * group)
                if bin_price == price:
                    # first level was exact bin price already, skip to next bin
                    bin_price -= group
                while pos < self.height and bin_price >= 0:
                    vol, _vol_quote = book.get_total_up_to(bin_price, False)
                    if vol > prev_vol:
                        # append only non-empty bins
                        if sum_total:
                            bins.append([pos, bin_price, vol, 0, 0])
                        else:
                            bins.append([pos, bin_price, vol - prev_vol, 0, 0])
                        prev_vol = vol
                        pos += 1
                    bin_price -= group

                # now add the own volumes to their bins
                for order in book.owns:
                    if order.typ == "bid" and order.price > 0:
                        order_bin_price = int(math.floor(float(order.price) / group) * group)
                        for abin in bins:
                            if abin[1] == order.price:
                                abin[3] += order.volume
                                break
                            if abin[1] == order_bin_price:
                                abin[3] += order.volume
                                break

            # mark the level where change took place (optional)
            if gox.config.get_bool("goxtool", "highlight_changes"):
                if book.last_change_type == "bid":
                    change_bin_price = int(math.floor(float(book.last_change_price) / group) * group)
                    for abin in bins:
                        if abin[1] == book.last_change_price:
                            abin[4] = book.last_change_volume
                            break
                        if abin[1] == change_bin_price:
                            abin[4] = book.last_change_volume
                            break

            # now finally paint the bids
            for pos, price, vol, ownvol, changevol in bins:
                paint_row(pos, price, vol, ownvol, col_bid, changevol)

        # update the xterm title bar
        if self.gox.config.get_bool("goxtool", "set_xterm_title"):
            last_candle = self.gox.history.last_candle()
            if last_candle:
                title = self.gox.quote2str(last_candle.cls).strip()
                title += " - goxtool -"
                title += " bid:" + self.gox.quote2str(book.bid).strip()
                title += " ask:" + self.gox.quote2str(book.ask).strip()

                term = os.environ["TERM"]
                # the following is incomplete but better safe than sorry
                # if you know more terminals then please provide a patch
                if "xterm" in term or "rxvt" in term:
                    sys_out.write("\x1b]0;%s\x07" % title)
                    sys_out.flush()

    def slot_changed(self, _book, _dummy):
        """Slot for orderbook.signal_changed"""
        self.do_paint()


TYPE_HISTORY = 1
TYPE_ORDERBOOK = 2

class WinChart(Win):
    """the chart window"""

    def __init__(self, stdscr, gox):
        self.gox = gox
        self.pmin = 0
        self.pmax = 0
        self.change_type = None
        gox.history.signal_changed.connect(self.slot_history_changed)
        gox.orderbook.signal_changed.connect(self.slot_orderbook_changed)

        # some terminals do not support reverse video
        # so we cannot use reverse space for candle bodies
        if curses.A_REVERSE & curses.termattrs():
            self.body_char = " "
            self.body_attr = curses.A_REVERSE
        else:
            self.body_char = curses.ACS_CKBOARD # pylint: disable=E1101
            self.body_attr = 0

        Win.__init__(self, stdscr)

    def calc_size(self):
        """position in the middle, right to the orderbook"""
        self.posx = WIDTH_ORDERBOOK
        self.posy = HEIGHT_STATUS
        self.width = self.termwidth - WIDTH_ORDERBOOK
        self.height = self.termheight - HEIGHT_CON - HEIGHT_STATUS

    def is_in_range(self, price):
        """is this price in the currently visible range?"""
        return price <= self.pmax and price >= self.pmin

    def get_optimal_step(self, num_min):
        """return optimal step size for painting y-axis labels so that the
        range will be divided into at least num_min steps"""
        if self.pmax <= self.pmin:
            return None
        stepex = float(self.pmax - self.pmin) / num_min
        step1 = math.pow(10, math.floor(math.log(stepex, 10)))
        step2 = step1 * 2
        step5 = step1 * 5
        if step5 <= stepex:
            return step5
        if step2 <= stepex:
            return step2
        return step1

    def price_to_screen(self, price):
        """convert price into screen coordinates (y=0 is at the top!)"""
        relative_from_bottom = \
            float(price - self.pmin) / float(self.pmax - self.pmin)
        screen_from_bottom = relative_from_bottom * self.height
        return int(self.height - screen_from_bottom)

    def paint_y_label(self, posy, posx, price):
        """paint the y label of the history chart, formats the number
        so that it needs not more room than necessary but it also uses
        pmax to determine how many digits are needed so that all numbers
        will be nicely aligned at the decimal point"""

        fprice = self.gox.quote2float(price)
        labelstr = ("%f" % fprice).rstrip("0").rstrip(".")

        # look at pmax to determine the max number of digits before the decimal
        # and then pad all smaller prices with spaces to make them align nicely.
        need_digits = int(math.log10(self.gox.quote2float(self.pmax))) + 1
        have_digits = len(str(int(fprice)))
        if have_digits < need_digits:
            padding = " " * (need_digits - have_digits)
            labelstr = padding + labelstr

        self.addstr(
            posy, posx,
            labelstr,
            COLOR_PAIR["chart_text"]
        )

    def paint_candle(self, posx, candle):
        """paint a single candle"""

        sopen  = self.price_to_screen(candle.opn)
        shigh  = self.price_to_screen(candle.hig)
        slow   = self.price_to_screen(candle.low)
        sclose = self.price_to_screen(candle.cls)

        for posy in range(self.height):
            if posy >= shigh and posy < sopen and posy < sclose:
                # upper wick
                # pylint: disable=E1101
                self.addch(posy, posx, curses.ACS_VLINE, COLOR_PAIR["chart_text"])
            if posy >= sopen and posy < sclose:
                # red body
                self.addch(posy, posx, self.body_char, self.body_attr + COLOR_PAIR["chart_down"])
            if posy >= sclose and posy < sopen:
                # green body
                self.addch(posy, posx, self.body_char, self.body_attr + COLOR_PAIR["chart_up"])
            if posy >= sopen and posy >= sclose and posy < slow:
                # lower wick
                # pylint: disable=E1101
                self.addch(posy, posx, curses.ACS_VLINE, COLOR_PAIR["chart_text"])

    def paint(self):
        typ = self.gox.config.get_string("goxtool", "display_right")
        if typ == "history_chart":
            self.paint_history_chart()
        elif typ == "depth_chart":
            self.paint_depth_chart()
        else:
            self.paint_history_chart()

    def paint_depth_chart(self):
        """paint a depth chart"""

        # pylint: disable=C0103
        if self.gox.curr_quote in "JPY SEK":
            BAR_LEFT_EDGE = 7
            FORMAT_STRING = "%6.0f"
        else:
            BAR_LEFT_EDGE = 8
            FORMAT_STRING = "%7.2f"

        def paint_depth(pos, price, vol, own, col_price, change):
            """paint one row of the depth chart"""
            if change > 0:
                col = col_bid + curses.A_BOLD
            elif change < 0:
                col = col_ask + curses.A_BOLD
            else:
                col = col_bar
            pricestr = FORMAT_STRING % self.gox.quote2float(price)
            self.addstr(pos, 0, pricestr, col_price)
            length = int(vol * mult_x)
            # pylint: disable=E1101
            self.win.hline(pos, BAR_LEFT_EDGE, curses.ACS_CKBOARD, length, col)
            if own:
                self.addstr(pos, length + BAR_LEFT_EDGE, "o", col_own)

        self.win.bkgd(" ",  COLOR_PAIR["chart_text"])
        self.win.erase()

        book = self.gox.orderbook
        if not (book.bid and book.ask and len(book.bids) and len(book.asks)):
            # orderbook is not initialized yet, paint nothing
            return

        col_bar = COLOR_PAIR["book_vol"]
        col_bid = COLOR_PAIR["book_bid"]
        col_ask = COLOR_PAIR["book_ask"]
        col_own = COLOR_PAIR["book_own"]

        group = self.gox.config.get_float("goxtool", "depth_chart_group")
        if group == 0:
            group = 1
        group = self.gox.quote2int(group)

        max_vol_ask = 0
        max_vol_bid = 0
        bin_asks = []
        bin_bids = []
        mid = self.height / 2
        sum_total = self.gox.config.get_bool("goxtool", "depth_chart_sum_total")

        #
        #
        # bin the asks
        #
        pos = mid - 1
        prev_vol = 0
        bin_price = int(math.ceil(float(book.asks[0].price) / group) * group)
        while pos >= 0 and bin_price < book.asks[-1].price + group:
            bin_vol, _bin_vol_quote = book.get_total_up_to(bin_price, True)
            if bin_vol > prev_vol:
                # add only non-empty bins
                if sum_total:
                    bin_asks.append([pos, bin_price, bin_vol, 0, 0])
                    max_vol_ask = max(bin_vol, max_vol_ask)
                else:
                    bin_asks.append([pos, bin_price, bin_vol - prev_vol, 0, 0])
                    max_vol_ask = max(bin_vol - prev_vol, max_vol_ask)
                prev_vol = bin_vol
                pos -= 1
            bin_price += group

        #
        #
        # bin the bids
        #
        pos = mid + 1
        prev_vol = 0
        bin_price = int(math.floor(float(book.bids[0].price) / group) * group)
        while pos < self.height and bin_price >= 0:
            _bin_vol_base, bin_vol_quote = book.get_total_up_to(bin_price, False)
            bin_vol = self.gox.base2int(bin_vol_quote / book.bid)
            if bin_vol > prev_vol:
                # add only non-empty bins
                if sum_total:
                    bin_bids.append([pos, bin_price, bin_vol, 0, 0])
                    max_vol_bid = max(bin_vol, max_vol_bid)
                else:
                    bin_bids.append([pos, bin_price, bin_vol - prev_vol, 0, 0])
                    max_vol_bid = max(bin_vol - prev_vol, max_vol_bid)
                prev_vol = bin_vol
                pos += 1
            bin_price -= group

        max_vol_tot = max(max_vol_ask, max_vol_bid)
        if not max_vol_tot:
            return
        mult_x = float(self.width - BAR_LEFT_EDGE - 2) / max_vol_tot

        # add the own volume to the bins
        for order in book.owns:
            if order.price > 0:
                if order.typ == "ask":
                    bin_price = int(math.ceil(float(order.price) / group) * group)
                    for abin in bin_asks:
                        if abin[1] == bin_price:
                            abin[3] += order.volume
                            break
                else:
                    bin_price = int(math.floor(float(order.price) / group) * group)
                    for abin in bin_bids:
                        if abin[1] == bin_price:
                            abin[3] += order.volume
                            break

        # highlight the relative change (optional)
        if self.gox.config.get_bool("goxtool", "highlight_changes"):
            price = book.last_change_price
            if book.last_change_type == "ask":
                bin_price = int(math.ceil(float(price) / group) * group)
                for abin in bin_asks:
                    if abin[1] == bin_price:
                        abin[4] = book.last_change_volume
                        break
            if book.last_change_type == "bid":
                bin_price = int(math.floor(float(price) / group) * group)
                for abin in bin_bids:
                    if abin[1] == bin_price:
                        abin[4] = book.last_change_volume
                        break

        # paint the asks
        for pos, price, vol, own, change in bin_asks:
            paint_depth(pos, price, vol, own, col_ask, change)

        # paint the bids
        for pos, price, vol, own, change in bin_bids:
            paint_depth(pos, price, vol, own, col_bid, change)

    def paint_history_chart(self):
        """paint a history candlestick chart"""

        if self.change_type == TYPE_ORDERBOOK:
            # erase only the rightmost column to redraw bid/ask and orders
            # beause we won't redraw the chart, its only an orderbook change
            self.win.vline(0, self.width - 1, " ", self.height, COLOR_PAIR["chart_text"])
        else:
            self.win.bkgd(" ",  COLOR_PAIR["chart_text"])
            self.win.erase()

        hist = self.gox.history
        book = self.gox.orderbook

        self.pmax = 0
        self.pmin = 9999999999

        # determine y range
        posx = self.width - 2
        index = 0
        while index < hist.length() and posx >= 0:
            candle = hist.candles[index]
            if self.pmax < candle.hig:
                self.pmax = candle.hig
            if self.pmin > candle.low:
                self.pmin = candle.low
            index += 1
            posx -= 1

        if self.pmax == self.pmin:
            return

        # paint the candlestick chart.
        # We won't paint it if it was triggered from an orderbook change
        # signal because that would be redundant and only waste CPU.
        # In that case we only repaint the bid/ask markers (see below)
        if self.change_type != TYPE_ORDERBOOK:
            # paint the candles
            posx = self.width - 2
            index = 0
            while index < hist.length() and posx >= 0:
                candle = hist.candles[index]
                self.paint_candle(posx, candle)
                index += 1
                posx -= 1

            # paint the y-axis labels
            posx = 0
            step = self.get_optimal_step(4)
            if step:
                labelprice = int(self.pmin / step) * step
                while not labelprice > self.pmax:
                    posy = self.price_to_screen(labelprice)
                    if posy < self.height - 1:
                        self.paint_y_label(posy, posx, labelprice)
                    labelprice += step

        # paint bid, ask, own orders
        posx = self.width - 1
        for order in book.owns:
            if self.is_in_range(order.price):
                posy = self.price_to_screen(order.price)
                if order.status == "pending":
                    self.addch(posy, posx,
                        ord("p"), COLOR_PAIR["order_pending"])
                else:
                    self.addch(posy, posx,
                        ord("o"), COLOR_PAIR["book_own"])

        if self.is_in_range(book.bid):
            posy = self.price_to_screen(book.bid)
            # pylint: disable=E1101
            self.addch(posy, posx,
                curses.ACS_HLINE, COLOR_PAIR["chart_up"])

        if self.is_in_range(book.ask):
            posy = self.price_to_screen(book.ask)
            # pylint: disable=E1101
            self.addch(posy, posx,
                curses.ACS_HLINE, COLOR_PAIR["chart_down"])


    def slot_history_changed(self, _sender, _data):
        """Slot for history changed"""
        self.change_type = TYPE_HISTORY
        self.do_paint()
        self.change_type = None

    def slot_orderbook_changed(self, _sender, _data):
        """Slot for orderbook changed"""
        self.change_type = TYPE_ORDERBOOK
        self.do_paint()
        self.change_type = None


class WinStatus(Win):
    """the status window at the top"""

    def __init__(self, stdscr, gox):
        """create the status window and connect the needed callbacks"""
        self.gox = gox
        self.order_lag = 0
        self.order_lag_txt = ""
        self.sorted_currency_list = []
        gox.signal_orderlag.connect(self.slot_orderlag)
        gox.signal_wallet.connect(self.slot_changed)
        gox.orderbook.signal_changed.connect(self.slot_changed)
        Win.__init__(self, stdscr)

    def calc_size(self):
        """place it at the top of the terminal"""
        self.height = HEIGHT_STATUS

    def sort_currency_list_if_changed(self):
        """sort the currency list in the wallet for better display,
        sort it only if it has changed, otherwise leave it as it is"""
        currency_list = self.gox.wallet.keys()
        if len(currency_list) == len(self.sorted_currency_list):
            return

        # now we will bring base and quote currency to the front and sort the
        # the rest of the list of names by acount balance in descending order
        if self.gox.curr_base in currency_list:
            currency_list.remove(self.gox.curr_base)
        if self.gox.curr_quote in currency_list:
            currency_list.remove(self.gox.curr_quote)
        currency_list.sort(key=lambda name: -self.gox.wallet[name])
        currency_list.insert(0, self.gox.curr_quote)
        currency_list.insert(0, self.gox.curr_base)
        self.sorted_currency_list = currency_list

    def paint(self):
        """paint the complete status"""
        cbase = self.gox.curr_base
        cquote = self.gox.curr_quote
        self.sort_currency_list_if_changed()
        self.win.bkgd(" ", COLOR_PAIR["status_text"])
        self.win.erase()

        #
        # first line
        #
        line1 = "Market: %s%s | " % (cbase, cquote)
        line1 += "Account: "
        if len(self.sorted_currency_list):
            for currency in self.sorted_currency_list:
                if currency in self.gox.wallet:
                    line1 += currency + " " \
                    + goxapi.int2str(self.gox.wallet[currency], currency).strip() \
                    + " + "
            line1 = line1.strip(" +")
        else:
            line1 += "No info (yet)"

        #
        # second line
        #
        line2 = ""
        if self.gox.config.get_bool("goxtool", "show_orderbook_stats"):
            str_btc = locale.format('%d', self.gox.orderbook.total_ask, 1)
            str_fiat = locale.format('%d', self.gox.orderbook.total_bid, 1)
            if self.gox.orderbook.total_ask:
                str_ratio = locale.format('%1.2f',
                    self.gox.orderbook.total_bid / self.gox.orderbook.total_ask, 1)
            else:
                str_ratio = "-"

            line2 += "sum_bid: %s %s | " % (str_fiat, cquote)
            line2 += "sum_ask: %s %s | " % (str_btc, cbase)
            line2 += "ratio: %s %s/%s | " % (str_ratio, cquote, cbase)

        line2 += "o_lag: %s | " % self.order_lag_txt
        line2 += "s_lag: %.3f s" % (self.gox.socket_lag / 1e6)
        self.addstr(0, 0, line1, COLOR_PAIR["status_text"])
        self.addstr(1, 0, line2, COLOR_PAIR["status_text"])


    def slot_changed(self, dummy_sender, dummy_data):
        """the callback funtion called by the Gox() instance"""
        self.do_paint()

    def slot_orderlag(self, dummy_sender, (usec, text)):
        """slot for order_lag mesages"""
        self.order_lag = usec
        self.order_lag_txt = text
        self.do_paint()


class DlgListItems(Win):
    """dialog with a scrollable list of items"""
    def __init__(self, stdscr, width, title, hlp, keys):
        self.items = []
        self.selected = []
        self.item_top = 0
        self.item_sel = 0
        self.dlg_width = width
        self.dlg_title = title
        self.dlg_hlp = hlp
        self.dlg_keys = keys
        self.reserved_lines = 5  # how many lines NOT used for order list
        self.init_items()
        Win.__init__(self, stdscr)

    def init_items(self):
        """initialize the items list, must override and implement this"""
        raise NotImplementedError()

    def calc_size(self):
        maxh = self.termheight - 4
        self.height = len(self.items) + self.reserved_lines
        if self.height > maxh:
            self.height = maxh
        self.posy = (self.termheight - self.height) / 2

        self.width = self.dlg_width
        self.posx = (self.termwidth - self.width) / 2

    def paint_item(self, posx, index):
        """paint the item. Must override and implement this"""
        raise NotImplementedError()

    def paint(self):
        self.win.bkgd(" ", COLOR_PAIR["dialog_text"])
        self.win.erase()
        self.win.border()
        self.addstr(0, 1, " %s " % self.dlg_title, COLOR_PAIR["dialog_text"])
        index = self.item_top
        posy = 2
        while posy < self.height - 3 and index < len(self.items):
            self.paint_item(posy, index)
            index += 1
            posy += 1

        self.win.move(self.height - 2, 2)
        for key, desc in self.dlg_hlp:
            self.addstr(key + " ",  COLOR_PAIR["dialog_sel"])
            self.addstr(desc + " ", COLOR_PAIR["dialog_text"])

    def down(self, num):
        """move the cursor down (or up)"""
        if not len(self.items):
            return
        self.item_sel += num
        if self.item_sel < 0:
            self.item_sel = 0
        if self.item_sel > len(self.items) - 1:
            self.item_sel = len(self.items) - 1

        last_line = self.height - 1 - self.reserved_lines
        if self.item_sel < self.item_top:
            self.item_top = self.item_sel
        if self.item_sel - self.item_top > last_line:
            self.item_top = self.item_sel - last_line

        self.do_paint()

    def toggle_select(self):
        """toggle selection under cursor"""
        if not len(self.items):
            return
        item = self.items[self.item_sel]
        if item in self.selected:
            self.selected.remove(item)
        else:
            self.selected.append(item)
        self.do_paint()

    def modal(self):
        """run the modal getch-loop for this dialog"""
        if self.win:
            done = False
            while not done:
                key_pressed = self.win.getch()
                if key_pressed in [27, ord("q"), curses.KEY_F10]:
                    done = True
                if key_pressed == curses.KEY_DOWN:
                    self.down(1)
                if key_pressed == curses.KEY_UP:
                    self.down(-1)
                if key_pressed == curses.KEY_IC:
                    self.toggle_select()
                    self.down(1)

                for key, func in self.dlg_keys:
                    if key == key_pressed:
                        func()
                        done = True

        # help the garbage collector clean up circular references
        # to make sure __del__() will be called to close the dialog
        del self.dlg_keys


class DlgCancelOrders(DlgListItems):
    """modal dialog to cancel orders"""
    def __init__(self, stdscr, gox):
        self.gox = gox
        hlp = [("INS", "select"), ("F8", "cancel selected"), ("F10", "exit")]
        keys = [(curses.KEY_F8, self._do_cancel)]
        DlgListItems.__init__(self, stdscr, 45, "Cancel order(s)", hlp, keys)

    def init_items(self):
        for order in self.gox.orderbook.owns:
            self.items.append(order)
        self.items.sort(key = lambda o: -o.price)

    def paint_item(self, posy, index):
        """paint one single order"""
        order = self.items[index]
        if order in self.selected:
            marker = "*"
            if index == self.item_sel:
                attr = COLOR_PAIR["dialog_sel_sel"]
            else:
                attr = COLOR_PAIR["dialog_sel_text"] + curses.A_BOLD
        else:
            marker = ""
            if index == self.item_sel:
                attr = COLOR_PAIR["dialog_sel"]
            else:
                attr = COLOR_PAIR["dialog_text"]

        self.addstr(posy, 2, marker, attr)
        self.addstr(posy, 5, order.typ, attr)
        self.addstr(posy, 9, self.gox.quote2str(order.price), attr)
        self.addstr(posy, 22, self.gox.base2str(order.volume), attr)

    def _do_cancel(self):
        """cancel all selected orders (or the order under cursor if empty)"""

        def do_cancel(order):
            """cancel a single order"""
            self.gox.cancel(order.oid)

        if not len(self.items):
            return
        if not len(self.selected):
            order = self.items[self.item_sel]
            do_cancel(order)
        else:
            for order in self.selected:
                do_cancel(order)


class TextBox():
    """wrapper for curses.textpad.Textbox"""

    def __init__(self, dlg, posy, posx, length):
        self.dlg = dlg
        self.win = dlg.win.derwin(1, length, posy, posx)
        self.win.keypad(1)
        self.box = curses.textpad.Textbox(self.win, insert_mode=True)
        self.value = ""
        self.result = None
        self.editing = False

    def __del__(self):
        self.box = None
        self.win = None

    def modal(self):
        """enter te edit box modal loop"""
        self.win.move(0, 0)
        self.editing = True
        goxapi.start_thread(self.cursor_placement_thread, "TextBox cursor placement")
        self.value = self.box.edit(self.validator)
        self.editing = False
        return self.result

    def validator(self, char):
        """here we tweak the behavior slightly, especially we want to
        end modal editing mode immediately on arrow up/down and on enter
        and we also want to catch ESC and F10, to abort the entire dialog"""
        if curses.ascii.isprint(char):
            return char
        if char == curses.ascii.TAB:
            char = curses.KEY_DOWN
        if char in [curses.KEY_DOWN, curses.KEY_UP]:
            self.result = char
            return curses.ascii.BEL
        if char in [10, 13, curses.KEY_ENTER, curses.ascii.BEL]:
            self.result = 10
            return curses.ascii.BEL
        if char in [27, curses.KEY_F10]:
            self.result = -1
            return curses.ascii.BEL
        return char

    def cursor_placement_thread(self):
        """this is the most ugly hack of the entire program. During the
        signals hat are fired while we are editing there will be many repaints
        of other other panels below this dialog and when curses is done
        repainting everything the blinking cursor is not in the correct
        position. This is only a cosmetic problem but very annnoying. Try to
        force it into the edit field by repainting it very often."""
        while self.editing:
            # pylint: disable=W0212
            with goxapi.Signal._lock:
                curses.curs_set(2)
                self.win.touchwin()
                self.win.refresh()
            time.sleep(0.1)
        curses.curs_set(0)


class NumberBox(TextBox):
    """TextBox that only accepts numbers"""
    def __init__(self, dlg, posy, posx, length):
        TextBox.__init__(self, dlg, posy, posx, length)

    def validator(self, char):
        """allow only numbers to be entered"""
        if char == ord("q"):
            char = curses.KEY_F10
        if curses.ascii.isprint(char):
            if chr(char) not in "0123456789.":
                char = 0
        return TextBox.validator(self, char)


class DlgNewOrder(Win):
    """abtract base class for entering new orders"""
    def __init__(self, stdscr, gox, color, title):
        self.gox = gox
        self.color = color
        self.title = title
        self.edit_price = None
        self.edit_volume = None
        Win.__init__(self, stdscr)

    def calc_size(self):
        Win.calc_size(self)
        self.width = 35
        self.height = 8
        self.posx = (self.termwidth - self.width) / 2
        self.posy = (self.termheight - self.height) / 2

    def paint(self):
        self.win.bkgd(" ", self.color)
        self.win.border()
        self.addstr(0, 1, " %s " % self.title, self.color)
        self.addstr(2, 2, " price", self.color)
        self.addstr(2, 30, self.gox.curr_quote)
        self.addstr(4, 2, "volume", self.color)
        self.addstr(4, 30, self.gox.curr_base)
        self.addstr(6, 2, "F10 ", self.color + curses.A_REVERSE)
        self.addstr("cancel ", self.color)
        self.addstr("Enter ", self.color + curses.A_REVERSE)
        self.addstr("submit ", self.color)
        self.edit_price = NumberBox(self, 2, 10, 20)
        self.edit_volume = NumberBox(self, 4, 10, 20)

    def do_submit(self, price_float, volume_float):
        """sumit the order. implementating class will do eiter buy or sell"""
        raise NotImplementedError()

    def modal(self):
        """enter the modal getch() loop of this dialog"""
        if self.win:
            focus = 1
            # next time I am going to use some higher level
            # wrapper on top of curses, i promise...
            while True:
                if focus == 1:
                    res = self.edit_price.modal()
                    if res == -1:
                        break # cancel entire dialog
                    if res in [10, curses.KEY_DOWN, curses.KEY_UP]:
                        try:
                            price_float = float(self.edit_price.value)
                            focus = 2
                        except ValueError:
                            pass # can't move down until this is a valid number

                if focus == 2:
                    res = self.edit_volume.modal()
                    if res == -1:
                        break # cancel entire dialog
                    if res in [curses.KEY_UP, curses.KEY_DOWN]:
                        focus = 1
                    if res == 10:
                        try:
                            volume_float = float(self.edit_volume.value)
                            break # have both values now, can submit order
                        except ValueError:
                            pass # no float number, stay in this edit field

            if res == -1:
                #user has hit f10. just end here, do nothing
                pass
            if res == 10:
                self.do_submit(price_float, volume_float)

        # make sure all cyclic references are garbage collected or
        # otherwise the curses window won't disappear
        self.edit_price = None
        self.edit_volume = None


class DlgNewOrderBid(DlgNewOrder):
    """Modal dialog for new buy order"""
    def __init__(self, stdscr, gox):
        DlgNewOrder.__init__(self, stdscr, gox,
            COLOR_PAIR["dialog_bid_text"],
            "New buy order")

    def do_submit(self, price, volume):
        price = self.gox.quote2int(price)
        volume = self.gox.base2int(volume)
        self.gox.buy(price, volume)


class DlgNewOrderAsk(DlgNewOrder):
    """Modal dialog for new sell order"""
    def __init__(self, stdscr, gox):
        DlgNewOrder.__init__(self, stdscr, gox,
             COLOR_PAIR["dialog_ask_text"],
            "New sell order")

    def do_submit(self, price, volume):
        price = self.gox.quote2int(price)
        volume = self.gox.base2int(volume)
        self.gox.sell(price, volume)



#
#
# logging, printing, etc...
#

class LogWriter():
    """connects to gox.signal_debug and logs it all to the logfile"""
    def __init__(self, gox):
        self.gox = gox
        if self.gox.config.get_bool("goxtool", "dont_truncate_logfile"):
            logfilemode = 'a'
        else:
            logfilemode = 'w'

        logging.basicConfig(filename='goxtool.log'
                           ,filemode=logfilemode
                           ,format='%(asctime)s:%(levelname)s:%(message)s'
                           ,level=logging.DEBUG
                           )
        self.gox.signal_debug.connect(self.slot_debug)

    def close(self):
        """stop logging"""
        #not needed
        pass

    # pylint: disable=R0201
    def slot_debug(self, sender, (msg)):
        """handler for signal_debug signals"""
        name = "%s.%s" % (sender.__class__.__module__, sender.__class__.__name__)
        logging.debug("%s:%s", name, msg)


class PrintHook():
    """intercept stdout/stderr and send it all to gox.signal_debug instead"""
    def __init__(self, gox):
        self.gox = gox
        self.stdout = sys.stdout
        self.stderr = sys.stderr
        sys.stdout = self
        sys.stderr = self

    def close(self):
        """restore normal stdio"""
        sys.stdout = self.stdout
        sys.stderr = self.stderr

    def write(self, string):
        """called when someone uses print(), send it to gox"""
        string = string.strip()
        if string != "":
            self.gox.signal_debug(self, string)



#
#
# dynamically (re)loadable strategy module
#

class StrategyManager():
    """load the strategy module"""

    def __init__(self, gox, strategy_name_list):
        self.strategy_object_list = []
        self.strategy_name_list = strategy_name_list
        self.gox = gox
        self.reload()

    def unload(self):
        """unload the strategy, will trigger its the __del__ method"""
        self.gox.signal_strategy_unload(self, None)
        self.strategy_object_list = []

    def reload(self):
        """reload and re-initialize the strategy module"""
        self.unload()
        for name in self.strategy_name_list:
            name = name.replace(".py", "").strip()

            try:
                strategy_module = __import__(name)
                try:
                    reload(strategy_module)
                    strategy_object = strategy_module.Strategy(self.gox)
                    self.strategy_object_list.append(strategy_object)
                    if hasattr(strategy_object, "name"):
                        self.gox.strategies[strategy_object.name] = strategy_object

                except Exception:
                    self.gox.debug("### error while loading strategy %s.py, traceback follows:" % name)
                    self.gox.debug(traceback.format_exc())

            except ImportError:
                self.gox.debug("### could not import %s.py, traceback follows:" % name)
                self.gox.debug(traceback.format_exc())


def toggle_setting(gox, alternatives, option_name, direction):
    """toggle a setting in the ini file"""
    # pylint: disable=W0212
    with goxapi.Signal._lock:
        setting = gox.config.get_string("goxtool", option_name)
        try:
            newindex = (alternatives.index(setting) + direction) % len(alternatives)
        except ValueError:
            newindex = 0
        gox.config.set("goxtool", option_name, alternatives[newindex])
        gox.config.save()

def toggle_depth_group(gox, direction):
    """toggle the step width of the depth chart"""
    if gox.curr_quote in "JPY SEK":
        alt = ["5", "10", "25", "50", "100", "200", "500", "1000", "2000", "5000", "10000"]
    else:
        alt = ["0.05", "0.1", "0.25", "0.5", "1", "2", "5", "10", "20", "50", "100"]
    toggle_setting(gox, alt, "depth_chart_group", direction)
    gox.orderbook.signal_changed(gox.orderbook, None)

def toggle_orderbook_group(gox, direction):
    """toggle the group width of the orderbook"""
    if gox.curr_quote in "JPY SEK":
        alt = ["0", "5", "10", "25", "50", "100", "200", "500", "1000", "2000", "5000", "10000"]
    else:
        alt = ["0", "0.05", "0.1", "0.25", "0.5", "1", "2", "5", "10", "20", "50", "100"]
    toggle_setting(gox, alt, "orderbook_group", direction)
    gox.orderbook.signal_changed(gox.orderbook, None)

def toggle_orderbook_sum(gox):
    """toggle the summing in the orderbook on and off"""
    alt = ["False", "True"]
    toggle_setting(gox, alt, "orderbook_sum_total", 1)
    gox.orderbook.signal_changed(gox.orderbook, None)

def toggle_depth_sum(gox):
    """toggle the summing in the depth chart on and off"""
    alt = ["False", "True"]
    toggle_setting(gox, alt, "depth_chart_sum_total", 1)
    gox.orderbook.signal_changed(gox.orderbook, None)

def set_ini(gox, setting, value, signal, signal_sender, signal_params):
    """set the ini value and then send a signal"""
    # pylint: disable=W0212
    with goxapi.Signal._lock:
        gox.config.set("goxtool", setting, value)
        gox.config.save()
    signal(signal_sender, signal_params)



#
#
# main program
#

def main():
    """main funtion, called at the start of the program"""

    debug_tb = []
    def curses_loop(stdscr):
        """Only the code inside this function runs within the curses wrapper"""

        # this function may under no circumstancs raise an exception, so I'm
        # wrapping everything into try/except (should actually never happen
        # anyways but when it happens during coding or debugging it would
        # leave the terminal in an unusable state and this must be avoded).
        # We have a list debug_tb[] where we can append tracebacks and
        # after curses uninitialized properly and the terminal is restored
        # we can print them.
        try:
            init_colors()
            gox = goxapi.Gox(secret, config)

            logwriter = LogWriter(gox)
            printhook = PrintHook(gox)

            conwin = WinConsole(stdscr, gox)
            bookwin = WinOrderBook(stdscr, gox)
            statuswin = WinStatus(stdscr, gox)
            chartwin = WinChart(stdscr, gox)

            strategy_manager = StrategyManager(gox, strat_mod_list)

            gox.start()
            while True:
                key = stdscr.getch()
                if key == ord("q"):
                    break
                elif key == curses.KEY_F4:
                    DlgNewOrderBid(stdscr, gox).modal()
                elif key == curses.KEY_F5:
                    DlgNewOrderAsk(stdscr, gox).modal()
                elif key == curses.KEY_F6:
                    DlgCancelOrders(stdscr, gox).modal()
                elif key == curses.KEY_RESIZE:
                    # pylint: disable=W0212
                    with goxapi.Signal._lock:
                        stdscr.erase()
                        stdscr.refresh()
                        conwin.resize()
                        bookwin.resize()
                        chartwin.resize()
                        statuswin.resize()
                elif key == ord("l"):
                    strategy_manager.reload()

                # which chart to show on the right side
                elif key == ord("H"):
                    set_ini(gox, "display_right", "history_chart",
                        gox.history.signal_changed, gox.history, None)
                elif key == ord("D"):
                    set_ini(gox, "display_right", "depth_chart",
                        gox.orderbook.signal_changed, gox.orderbook, None)

                #  depth chart step
                elif key == ord(","): # zoom out
                    toggle_depth_group(gox, +1)
                elif key == ord("."): # zoom in
                    toggle_depth_group(gox, -1)

                # orderbook grouping step
                elif key == ord("-"): # zoom out (larger step)
                    toggle_orderbook_group(gox, +1)
                elif key == ord("+"): # zoom in (smaller step)
                    toggle_orderbook_group(gox, -1)

                elif key == ord("S"):
                    toggle_orderbook_sum(gox)

                elif key == ord("T"):
                    toggle_depth_sum(gox)

                # lowercase keys go to the strategy module
                elif key >= ord("a") and key <= ord("z"):
                    gox.signal_keypress(gox, (key))
                else:
                    gox.debug("key pressed: key=%i" % key)

        except KeyboardInterrupt:
            # Ctrl+C has been pressed
            pass

        except Exception:
            debug_tb.append(traceback.format_exc())

        # we are here because shutdown was requested.
        #
        # Before we do anything we dump stacktraces of all currently running
        # threads to a separate logfile because this helps debugging freezes
        # and deadlocks that might occur if things went totally wrong.
        with open("goxtool.stacktrace.log", "w") as stacklog:
            stacklog.write(dump_all_stacks())

        # we need the signal lock to be able to shut down. And we cannot
        # wait for any frozen slot to return, so try really hard to get
        # the lock and if that fails then unlock it forcefully.
        try_get_lock_or_break_open()

        # Now trying to shutdown everything in an orderly manner.it in the
        # Since we are still inside curses but we don't know whether
        # the printhook or the logwriter was initialized properly already
        # or whether it crashed earlier we cannot print here and we also
        # cannot log, so we put all tracebacks into the debug_tb list to
        # print them later once the terminal is properly restored again.
        try:
            strategy_manager.unload()
        except Exception:
            debug_tb.append(traceback.format_exc())

        try:
            gox.stop()
        except Exception:
            debug_tb.append(traceback.format_exc())

        try:
            printhook.close()
        except Exception:
            debug_tb.append(traceback.format_exc())

        try:
            logwriter.close()
        except Exception:
            debug_tb.append(traceback.format_exc())

        # curses_loop() ends here, we must reach this point under all circumstances.
        # Now curses will restore the terminal back to cooked (normal) mode.


    # Here it begins. The very first thing is to always set US or GB locale
    # to have always the same well defined behavior for number formatting.
    for loc in ["en_US.UTF8", "en_GB.UTF8", "en_EN", "en_GB", "C"]:
        try:
            locale.setlocale(locale.LC_NUMERIC, loc)
            break
        except locale.Error:
            continue

    # before we can finally start the curses UI we might need to do some user
    # interaction on the command line, regarding the encrypted secret
    argp = argparse.ArgumentParser(description='MtGox live market data monitor'
        + ' and trading bot experimentation framework')
    argp.add_argument('--add-secret', action="store_true",
        help="prompt for API secret, encrypt it and then exit")
    argp.add_argument('--strategy', action="store", default="strategy.py",
        help="name of strategy module files, comma separated list, default=strategy.py")
    argp.add_argument('--protocol', action="store", default="",
        help="force protocol (socketio or websocket), ignore setting in .ini")
    argp.add_argument('--no-fulldepth', action="store_true", default=False,
        help="do not download full depth (useful for debugging)")
    argp.add_argument('--no-depth', action="store_true", default=False,
        help="do not request depth messages (implies no-fulldeph), useful for low traffic")
    argp.add_argument('--no-lag', action="store_true", default=False,
        help="do not request order-lag updates, useful for low traffic")
    argp.add_argument('--no-history', action="store_true", default=False,
        help="do not download full history (useful for debugging)")
    argp.add_argument('--use-http', action="store_true", default=False,
        help="use http api for trading (more reliable, recommended")
    argp.add_argument('--no-http', action="store_true", default=False,
        help="use streaming api for trading (problematic when streaming api disconnects often)")
    argp.add_argument('--password', action="store", default=None,
        help="password for decryption of stored key. This is a dangerous option "
            +"because the password might end up being stored in the history file "
            +"of your shell, for example in ~/.bash_history. Use this only when "
            +"starting it from within a script and then of course you need to "
            +"keep this start script in a secure place!")
    args = argp.parse_args()

    config = goxapi.GoxConfig("goxtool.ini")
    config.init_defaults(INI_DEFAULTS)
    secret = goxapi.Secret(config)
    secret.password_from_commandline_option = args.password
    if args.add_secret:
        # prompt for secret, encrypt, write to .ini and then exit the program
        secret.prompt_encrypt()
    else:
        strat_mod_list = args.strategy.split(",")
        goxapi.FORCE_PROTOCOL = args.protocol
        goxapi.FORCE_NO_FULLDEPTH = args.no_fulldepth
        goxapi.FORCE_NO_DEPTH = args.no_depth
        goxapi.FORCE_NO_LAG = args.no_lag
        goxapi.FORCE_NO_HISTORY = args.no_history
        goxapi.FORCE_HTTP_API = args.use_http
        goxapi.FORCE_NO_HTTP_API = args.no_http
        if goxapi.FORCE_NO_DEPTH:
            goxapi.FORCE_NO_FULLDEPTH = True

        # if its ok then we can finally enter the curses main loop
        if secret.prompt_decrypt() != secret.S_FAIL_FATAL:

            ###
            #
            # now going to enter cbreak mode and start the curses loop...
            curses.wrapper(curses_loop)
            # curses ended, terminal is back in normal (cooked) mode
            #
            ###

            if len(debug_tb):
                print "\n\n*** error(s) in curses_loop() that caused unclean shutdown:\n"
                for trb in debug_tb:
                    print trb
            else:
                print
                print "*******************************************************"
                print "*  Please donate: 1C8aDabADaYvTKvCAG1htqYcEgpAhkeYoW  *"
                print "*******************************************************"

if __name__ == "__main__":
    main()


########NEW FILE########
__FILENAME__ = pubnub_light
"""pubnub light API (only subscribe, not publish)"""

#  Copyright (c) 2013 Bernd Kreuss <prof7bit@gmail.com>
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.

import base64
from Crypto.Cipher import AES
import gzip
import hashlib
import io
import json
import socket
import ssl
import uuid

class SocketClosedException(Exception):
    """raised when socket read fails. This normally happens when the
    hup() method is invoked, your thread that loops over read() should
    catch this exception and then decide whether to retry or terminate"""
    pass


class PubNub(): #pylint: disable=R0902
    """implements a simple pubnub client that tries to stay connected
    and is interruptible immediately (using socket instead of urllib2).
    This client supports multiplexing, SSL and gzip compression."""
    def __init__(self):
        self.sock = None
        self.uuid = uuid.uuid4()
        self.timestamp = 0
        self.connected = False
        self.sub = ""
        self.chan = ""
        self.auth = ""
        self.cipher = ""
        self.use_ssl = False

    #pylint: disable=R0913
    def subscribe(self, sub, chan, auth="", cipher="", use_ssl=False):
        """set the subscription parameters. This is needed after __init__(),
        chan is a string containing a channel name or a comma separated list of
        multiple cannels, it will replace all previously set subscriptions."""
        self.sub = sub
        self.chan = chan
        self.auth = auth
        self.cipher = cipher
        self.use_ssl = use_ssl

        # force disconnect of currently active longpoll.
        self.hup()

    def read(self):
        """read (blocking) and return list of messages. Each message in the
        list a tuple of (channel, msg) where channel is the name of the channel
        the message came from and msg is the payload. Right after subscribe()
        you should enter a loop over this blocking read() call to read messages
        from the subscribed channels. It will raise an exception if interrupted
        (for example by hup() or by subscribe() or if something goes wrong),
        so you should catch exceptions and then decide whether to re-enter your
        loop because you merely called subscribe() again or whether you want
        to terminate because your application ends.
        """
        try:
            if not self.connected:
                self._connect()

            (length, encoding, chunked) = self._send_request()

            if chunked:
                data = self._read_chunked()
            else:
                data = self._read_num_bytes(length)

            if encoding == "gzip":
                data = self._unzip(data)

            data = json.loads(data)
            self.timestamp = int(data[1])
            if len(data[0]):
                if self.cipher:
                    msg_list = [self._decrypt(m) for m in data[0]]
                else:
                    msg_list = data[0]

                if len(data) > 2:
                    chan_list = data[2].split(",")
                else:
                    chan_list = [self.chan for m in msg_list]

                return zip(chan_list, msg_list)
            else:
                return []

        except:
            self.connected = False
            self.sock.close()
            raise

    def hup(self):
        """close socket and force the blocking read() to exit with an Exception.
        Usually the thread in your app that does the read() will then have
        the opportunity to decide whether to re-enter the read() because you
        only set new subscription parameters or to terminate because you want
        to shut down the client completely."""
        if self.sock:
            self.connected = False
            self.sock.shutdown(2)
            self.sock.close()

    def _connect(self):
        """connect and set self.connected flag, raise exception if error.
        This method is used internally, you don't explicitly call it yourself,
        the read() method will invoke it automatically if necessary."""
        self.sock = socket.socket()
        host = "pubsub.pubnub.com"
        port = 80
        if self.use_ssl:
            self.sock = ssl.wrap_socket(self.sock)
            port = 443
        self.sock.connect((host, port))
        self.connected = True

    def _send_request(self):
        """send http request, read response header and return
        response header info tuple (see: _read_response_header)."""
        headers = [
            "GET /subscribe/%s/%s/0/%i?uuid=%s&auth=%s HTTP/1.1" \
                % (self.sub, self.chan, self.timestamp, self.uuid, self.auth),
            "Accept-Encoding: gzip",
            "Host: pubsub.pubnub.com",
            "Connection: keep-alive"]
        str_headers = "%s\r\n\r\n" % "\r\n".join(headers)
        self.sock.send(str_headers)
        return self._read_response_header()

    def _read_response_header(self):
        """read the http response header and return a tuple containing
        the values (length, encoding, chunked) which will be needed to
        correctly read and interpret the rest of the response."""
        length = None
        encoding = "identity"
        chunked = False

        hdr = []
        while True:
            line = self._read_line()
            if not line:
                break
            hdr.append(line)

        for line in hdr:
            if "Content-Length" in line:
                length = int(line[15:])
            if "Content-Encoding" in line:
                encoding = line[17:].strip()
            if "Transfer-Encoding: chunked" in line:
                chunked = True

        return (length, encoding, chunked)

    def _read_line(self):
        """read one line from socket until and including CRLF, return stripped
        line or raise SocketClosedException if socket was closed"""
        line = ""
        while not line[-2:] == "\r\n":
            char = self.sock.recv(1)
            if not char:
                raise SocketClosedException
            line += char
        return line.strip()

    def _read_num_bytes(self, num):
        """read (blocking) exactly num bytes from socket,
        raise SocketClosedException if the socket is closed."""
        buf = ""
        while len(buf) < num:
            chunk = self.sock.recv(num - len(buf))
            if not chunk:
                raise SocketClosedException
            buf += chunk
        return buf

    def _read_chunked(self):
        """read chunked transfer encoding"""
        buf = ""
        size = 1
        while size:
            size = int(self._read_line(), 16)
            buf += self._read_num_bytes(size)
            self._read_num_bytes(2) # CRLF
        return buf

    #pylint: disable=R0201
    def _unzip(self, data):
        """unzip the gzip content encoding"""
        with io.BytesIO(data) as buf:
            with gzip.GzipFile(fileobj=buf) as unzipped:
                return unzipped.read()

    def _decrypt(self, msg):
        """decrypt a single pubnub message"""
        # they must be real crypto experts at pubnub.com
        # two lines of code and two capital mistakes :-(
        # pylint: disable=E1101
        key = hashlib.sha256(self.cipher).hexdigest()[0:32]
        aes = AES.new(key, AES.MODE_CBC, "0123456789012345")
        decrypted = aes.decrypt(base64.decodestring(msg))
        return json.loads(decrypted[0:-ord(decrypted[-1])])

########NEW FILE########
__FILENAME__ = strategy
"""
trading robot breadboard
"""

import goxapi

class Strategy(goxapi.BaseObject):
    # pylint: disable=C0111,W0613,R0201

    def __init__(self, gox):
        goxapi.BaseObject.__init__(self)
        self.signal_debug.connect(gox.signal_debug)
        gox.signal_keypress.connect(self.slot_keypress)
        gox.signal_strategy_unload.connect(self.slot_before_unload)
        gox.signal_ticker.connect(self.slot_tick)
        gox.signal_depth.connect(self.slot_depth)
        gox.signal_trade.connect(self.slot_trade)
        gox.signal_userorder.connect(self.slot_userorder)
        gox.orderbook.signal_owns_changed.connect(self.slot_owns_changed)
        gox.history.signal_changed.connect(self.slot_history_changed)
        gox.signal_wallet.connect(self.slot_wallet_changed)
        self.gox = gox
        self.name = "%s.%s" % \
            (self.__class__.__module__, self.__class__.__name__)
        self.debug("%s loaded" % self.name)

    def __del__(self):
        """the strategy object will be garbage collected now, this mainly
        only exists to produce the log message, so you can make sure it
        really garbage collects and won't stay in memory on reload. If you
        don't see this log mesage on reload then you have circular references"""
        self.debug("%s unloaded" % self.name)

    def slot_before_unload(self, _sender, _data):
        """the strategy is about to be unloaded. Use this signal to persist
        any state and also use it to forcefully destroy any circular references
        to allow it to be properly garbage collected (you might need to do
        this if you instantiated linked lists or similar structures, the
        symptom would be that you don't see the 'unloaded' message above."""
        pass

    def slot_keypress(self, gox, (key)):
        """a key in has been pressed (only a..z without "q" and "l")
        The argument key contains the ascii code. To react to a certain
        key use something like if key == ord('a')
        """
        pass

    def slot_tick(self, gox, (bid, ask)):
        """a tick message has been received from the streaming API"""
        pass

    def slot_depth(self, gox, (typ, price, volume, total_volume)):
        """a depth message has been received. Use this only if you want to
        keep track of the depth and orderbook updates yourself or if you
        for example want to log all depth messages to a database. This
        signal comes directly from the streaming API and the gox.orderbook
        might not yet be updated at this time."""
        pass

    def slot_trade(self, gox, (date, price, volume, typ, own)):
        """a trade message has been received. Note that this signal comes
        directly from the streaming API, it might come before orderbook.owns
        list has been updated, don't rely on the own orders and wallet already
        having been updated when this is fired."""
        pass

    def slot_userorder(self, gox, (price, volume, typ, oid, status)):
        """this comes directly from the API and owns list might not yet be
        updated, if you need the new owns list then use slot_owns_changed"""
        pass

    def slot_owns_changed(self, orderbook, _dummy):
        """this comes *after* userorder and orderbook.owns is updated already.
        Also note that this signal is sent by the orderbook object, not by gox,
        so the sender argument is orderbook and not gox. This signal might be
        useful if you want to detect whether an order has been filled, you
        count open orders, count pending orders and compare with last count"""
        pass

    def slot_wallet_changed(self, gox, _dummy):
        """this comes after the wallet has been updated. Access the new balances
        like so: gox.wallet[gox.curr_base] or gox.wallet[gox.curr_quote] and use
        gox.base2float() or gox.quote2float() if you need float values. You can
        also access balances from other currenies like gox.wallet["JPY"] but it
        is not guaranteed that they exist if you never had a balance in that
        particular currency. Always test for their existence first. Note that
        there will be multiple wallet signals after every trade. You can look
        into gox.msg to inspect the original server message that triggered this
        signal to filter the flood a little bit."""
        pass

    def slot_history_changed(self, history, _dummy):
        """this is fired whenever a new trade is inserted into the history,
        you can also use this to query the close price of the most recent
        candle which is effectvely the price of the last trade message.
        Contrary to the slot_trade this also fires when streaming API
        reconnects and re-downloads the trade history, you can use this
        to implement a stoploss or you could also use it for example to detect
        when a new candle is opened"""
        pass

########NEW FILE########
__FILENAME__ = websocket
"""
websocket - WebSocket client library for Python

Copyright (C) 2010 Hiroki Ohtani(liris)

    This library is free software; you can redistribute it and/or
    modify it under the terms of the GNU Lesser General Public
    License as published by the Free Software Foundation; either
    version 2.1 of the License, or (at your option) any later version.

    This library is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
    Lesser General Public License for more details.

    You should have received a copy of the GNU Lesser General Public
    License along with this library; if not, write to the Free Software
    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

"""


import socket
from urlparse import urlparse
import os
import array
import struct
import uuid
import hashlib
import base64
import logging

"""
websocket python client.
=========================

This version support only hybi-13.
Please see http://tools.ietf.org/html/rfc6455 for protocol.
"""


# websocket supported version.
VERSION = 13

# closing frame status codes.
STATUS_NORMAL = 1000
STATUS_GOING_AWAY = 1001
STATUS_PROTOCOL_ERROR = 1002
STATUS_UNSUPPORTED_DATA_TYPE = 1003
STATUS_STATUS_NOT_AVAILABLE = 1005
STATUS_ABNORMAL_CLOSED = 1006
STATUS_INVALID_PAYLOAD = 1007
STATUS_POLICY_VIOLATION = 1008
STATUS_MESSAGE_TOO_BIG = 1009
STATUS_INVALID_EXTENSION = 1010
STATUS_UNEXPECTED_CONDITION = 1011
STATUS_TLS_HANDSHAKE_ERROR = 1015

logger = logging.getLogger()


class WebSocketException(Exception):
    """
    websocket exeception class.
    """
    pass


class WebSocketConnectionClosedException(WebSocketException):
    """
    If remote host closed the connection or some network error happened,
    this exception will be raised.
    """
    pass

default_timeout = None
traceEnabled = False


def enableTrace(tracable):
    """
    turn on/off the tracability.

    tracable: boolean value. if set True, tracability is enabled.
    """
    global traceEnabled
    traceEnabled = tracable
    if tracable:
        if not logger.handlers:
            logger.addHandler(logging.StreamHandler())
        logger.setLevel(logging.DEBUG)


def setdefaulttimeout(timeout):
    """
    Set the global timeout setting to connect.

    timeout: default socket timeout time. This value is second.
    """
    global default_timeout
    default_timeout = timeout


def getdefaulttimeout():
    """
    Return the global timeout setting(second) to connect.
    """
    return default_timeout


def _parse_url(url):
    """
    parse url and the result is tuple of
    (hostname, port, resource path and the flag of secure mode)

    url: url string.
    """
    if ":" not in url:
        raise ValueError("url is invalid")

    scheme, url = url.split(":", 1)

    parsed = urlparse(url, scheme="http")
    if parsed.hostname:
        hostname = parsed.hostname
    else:
        raise ValueError("hostname is invalid")
    port = 0
    if parsed.port:
        port = parsed.port

    is_secure = False
    if scheme == "ws":
        if not port:
            port = 80
    elif scheme == "wss":
        is_secure = True
        if not port:
            port = 443
    else:
        raise ValueError("scheme %s is invalid" % scheme)

    if parsed.path:
        resource = parsed.path
    else:
        resource = "/"

    if parsed.query:
        resource += "?" + parsed.query

    return (hostname, port, resource, is_secure)


def create_connection(url, timeout=None, **options):
    """
    connect to url and return websocket object.

    Connect to url and return the WebSocket object.
    Passing optional timeout parameter will set the timeout on the socket.
    If no timeout is supplied, the global default timeout setting returned by getdefauttimeout() is used.
    You can customize using 'options'.
    If you set "header" dict object, you can set your own custom header.

    >>> conn = create_connection("ws://echo.websocket.org/",
         ...     header={"User-Agent: MyProgram",
         ...             "x-custom: header"})


    timeout: socket timeout time. This value is integer.
             if you set None for this value, it means "use default_timeout value"

    options: current support option is only "header".
             if you set header as dict value, the custom HTTP headers are added.
    """
    websock = WebSocket()
    websock.settimeout(timeout != None and timeout or default_timeout)
    websock.connect(url, **options)
    return websock

_MAX_INTEGER = (1 << 32) -1
_AVAILABLE_KEY_CHARS = range(0x21, 0x2f + 1) + range(0x3a, 0x7e + 1)
_MAX_CHAR_BYTE = (1<<8) -1

# ref. Websocket gets an update, and it breaks stuff.
# http://axod.blogspot.com/2010/06/websocket-gets-update-and-it-breaks.html


def _create_sec_websocket_key():
    uid = uuid.uuid4()
    return base64.encodestring(uid.bytes).strip()

_HEADERS_TO_CHECK = {
    "upgrade": "websocket",
    "connection": "upgrade",
    }


class _SSLSocketWrapper(object):
    def __init__(self, sock):
        self.ssl = socket.ssl(sock)

    def recv(self, bufsize):
        return self.ssl.read(bufsize)

    def send(self, payload):
        return self.ssl.write(payload)

_BOOL_VALUES = (0, 1)


def _is_bool(*values):
    for v in values:
        if v not in _BOOL_VALUES:
            return False

    return True


class ABNF(object):
    """
    ABNF frame class.
    see http://tools.ietf.org/html/rfc5234
    and http://tools.ietf.org/html/rfc6455#section-5.2
    """

    # operation code values.
    OPCODE_TEXT   = 0x1
    OPCODE_BINARY = 0x2
    OPCODE_CLOSE  = 0x8
    OPCODE_PING   = 0x9
    OPCODE_PONG   = 0xa

    # available operation code value tuple
    OPCODES = (OPCODE_TEXT, OPCODE_BINARY, OPCODE_CLOSE,
                OPCODE_PING, OPCODE_PONG)

    # opcode human readable string
    OPCODE_MAP = {
        OPCODE_TEXT: "text",
        OPCODE_BINARY: "binary",
        OPCODE_CLOSE: "close",
        OPCODE_PING: "ping",
        OPCODE_PONG: "pong"
        }

    # data length threashold.
    LENGTH_7  = 0x7d
    LENGTH_16 = 1 << 16
    LENGTH_63 = 1 << 63

    def __init__(self, fin = 0, rsv1 = 0, rsv2 = 0, rsv3 = 0,
                 opcode = OPCODE_TEXT, mask = 1, data = ""):
        """
        Constructor for ABNF.
        please check RFC for arguments.
        """
        self.fin = fin
        self.rsv1 = rsv1
        self.rsv2 = rsv2
        self.rsv3 = rsv3
        self.opcode = opcode
        self.mask = mask
        self.data = data
        self.get_mask_key = os.urandom

    @staticmethod
    def create_frame(data, opcode):
        """
        create frame to send text, binary and other data.

        data: data to send. This is string value(byte array).
            if opcode is OPCODE_TEXT and this value is uniocde,
            data value is conveted into unicode string, automatically.

        opcode: operation code. please see OPCODE_XXX.
        """
        if opcode == ABNF.OPCODE_TEXT and isinstance(data, unicode):
            data = data.encode("utf-8")
        # mask must be set if send data from client
        return ABNF(1, 0, 0, 0, opcode, 1, data)

    def format(self):
        """
        format this object to string(byte array) to send data to server.
        """
        if not _is_bool(self.fin, self.rsv1, self.rsv2, self.rsv3):
            raise ValueError("not 0 or 1")
        if self.opcode not in ABNF.OPCODES:
            raise ValueError("Invalid OPCODE")
        length = len(self.data)
        if length >= ABNF.LENGTH_63:
            raise ValueError("data is too long")

        frame_header = chr(self.fin << 7
                           | self.rsv1 << 6 | self.rsv2 << 5 | self.rsv3 << 4
                           | self.opcode)
        if length < ABNF.LENGTH_7:
            frame_header += chr(self.mask << 7 | length)
        elif length < ABNF.LENGTH_16:
            frame_header += chr(self.mask << 7 | 0x7e)
            frame_header += struct.pack("!H", length)
        else:
            frame_header += chr(self.mask << 7 | 0x7f)
            frame_header += struct.pack("!Q", length)

        if not self.mask:
            return frame_header + self.data
        else:
            mask_key = self.get_mask_key(4)
            return frame_header + self._get_masked(mask_key)

    def _get_masked(self, mask_key):
        s = ABNF.mask(mask_key, self.data)
        return mask_key + "".join(s)

    @staticmethod
    def mask(mask_key, data):
        """
        mask or unmask data. Just do xor for each byte

        mask_key: 4 byte string(byte).

        data: data to mask/unmask.
        """
        _m = array.array("B", mask_key)
        _d = array.array("B", data)
        for i in xrange(len(_d)):
            _d[i] ^= _m[i % 4]
        return _d.tostring()


class WebSocket(object):
    """
    Low level WebSocket interface.
    This class is based on
      The WebSocket protocol draft-hixie-thewebsocketprotocol-76
      http://tools.ietf.org/html/draft-hixie-thewebsocketprotocol-76

    We can connect to the websocket server and send/recieve data.
    The following example is a echo client.

    >>> import websocket
    >>> ws = websocket.WebSocket()
    >>> ws.connect("ws://echo.websocket.org")
    >>> ws.send("Hello, Server")
    >>> ws.recv()
    'Hello, Server'
    >>> ws.close()

    get_mask_key: a callable to produce new mask keys, see the set_mask_key
      function's docstring for more details
    """

    def __init__(self, get_mask_key = None):
        """
        Initalize WebSocket object.
        """
        self.connected = False
        self.io_sock = self.sock = socket.socket()
        self.get_mask_key = get_mask_key

    def set_mask_key(self, func):
        """
        set function to create musk key. You can custumize mask key generator.
        Mainly, this is for testing purpose.

        func: callable object. the fuct must 1 argument as integer.
              The argument means length of mask key.
              This func must be return string(byte array),
              which length is argument specified.
        """
        self.get_mask_key = func

    def settimeout(self, timeout):
        """
        Set the timeout to the websocket.

        timeout: timeout time(second).
        """
        self.sock.settimeout(timeout)

    def gettimeout(self):
        """
        Get the websocket timeout(second).
        """
        return self.sock.gettimeout()

    def connect(self, url, **options):
        """
        Connect to url. url is websocket url scheme. ie. ws://host:port/resource
        You can customize using 'options'.
        If you set "header" dict object, you can set your own custom header.

        >>> ws = WebSocket()
        >>> ws.connect("ws://echo.websocket.org/",
                ...     header={"User-Agent: MyProgram",
                ...             "x-custom: header"})

        timeout: socket timeout time. This value is integer.
                 if you set None for this value,
                 it means "use default_timeout value"

        options: current support option is only "header".
                 if you set header as dict value,
                 the custom HTTP headers are added.

        """
        hostname, port, resource, is_secure = _parse_url(url)
        # TODO: we need to support proxy
        self.sock.connect((hostname, port))
        if is_secure:
            self.io_sock = _SSLSocketWrapper(self.sock)
        self._handshake(hostname, port, resource, **options)

    def _handshake(self, host, port, resource, **options):
        sock = self.io_sock
        headers = []
        headers.append("GET %s HTTP/1.1" % resource)
        headers.append("Upgrade: websocket")
        headers.append("Connection: Upgrade")
        if port == 80:
            hostport = host
        else:
            hostport = "%s:%d" % (host, port)
        headers.append("Host: %s" % hostport)

        if "origin" in options:
            headers.append("Origin: %s" % options["origin"])
        else:
            headers.append("Origin: %s" % hostport)

        key = _create_sec_websocket_key()
        headers.append("Sec-WebSocket-Key: %s" % key)
        headers.append("Sec-WebSocket-Version: %s" % VERSION)
        if "header" in options:
            headers.extend(options["header"])

        headers.append("")
        headers.append("")

        header_str = "\r\n".join(headers)
        sock.send(header_str)
        if traceEnabled:
            logger.debug("--- request header ---")
            logger.debug(header_str)
            logger.debug("-----------------------")

        status, resp_headers = self._read_headers()
        if status != 101:
            self.close()
            raise WebSocketException("Handshake Status %d" % status)

        success = self._validate_header(resp_headers, key)
        if not success:
            self.close()
            raise WebSocketException("Invalid WebSocket Header")

        self.connected = True

    def _validate_header(self, headers, key):
        for k, v in _HEADERS_TO_CHECK.iteritems():
            r = headers.get(k, None)
            if not r:
                return False
            r = r.lower()
            if v != r:
                return False

        result = headers.get("sec-websocket-accept", None)
        if not result:
            return False
        result = result.lower()

        value = key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
        hashed = base64.encodestring(hashlib.sha1(value).digest()).strip().lower()
        return hashed == result

    def _read_headers(self):
        status = None
        headers = {}
        if traceEnabled:
            logger.debug("--- response header ---")

        while True:
            line = self._recv_line()
            if line == "\r\n":
                break
            line = line.strip()
            if traceEnabled:
                logger.debug(line)
            if not status:
                status_info = line.split(" ", 2)
                status = int(status_info[1])
            else:
                kv = line.split(":", 1)
                if len(kv) == 2:
                    key, value = kv
                    headers[key.lower()] = value.strip().lower()
                else:
                    raise WebSocketException("Invalid header")

        if traceEnabled:
            logger.debug("-----------------------")

        return status, headers

    def send(self, payload, opcode = ABNF.OPCODE_TEXT):
        """
        Send the data as string.

        payload: Payload must be utf-8 string or unicoce,
                  if the opcode is OPCODE_TEXT.
                  Otherwise, it must be string(byte array)

        opcode: operation code to send. Please see OPCODE_XXX.
        """
        frame = ABNF.create_frame(payload, opcode)
        if self.get_mask_key:
            frame.get_mask_key = self.get_mask_key
        data = frame.format()
        self.io_sock.send(data)
        if traceEnabled:
            logger.debug("send: " + repr(data))

    def ping(self, payload = ""):
        """
        send ping data.

        payload: data payload to send server.
        """
        self.send(payload, ABNF.OPCODE_PING)

    def pong(self, payload):
        """
        send pong data.

        payload: data payload to send server.
        """
        self.send(payload, ABNF.OPCODE_PONG)

    def recv(self):
        """
        Receive string data(byte array) from the server.

        return value: string(byte array) value.
        """
        opcode, data = self.recv_data()
        return data

    def recv_data(self):
        """
        Recieve data with operation code.

        return  value: tuple of operation code and string(byte array) value.
        """
        while True:
            frame = self.recv_frame()
            if not frame:
                # handle error:
                # 'NoneType' object has no attribute 'opcode'
                raise WebSocketException("Not a valid frame %s" % frame)
            elif frame.opcode in (ABNF.OPCODE_TEXT, ABNF.OPCODE_BINARY):
                return (frame.opcode, frame.data)
            elif frame.opcode == ABNF.OPCODE_CLOSE:
                self.send_close()
                return (frame.opcode, None)
            elif frame.opcode == ABNF.OPCODE_PING:
                self.pong(frame.data)

    def recv_frame(self):
        """
        recieve data as frame from server.

        return value: ABNF frame object.
        """
        header_bytes = self._recv_strict(2)
        if not header_bytes:
            return None
        b1 = ord(header_bytes[0])
        fin = b1 >> 7 & 1
        rsv1 = b1 >> 6 & 1
        rsv2 = b1 >> 5 & 1
        rsv3 = b1 >> 4 & 1
        opcode = b1 & 0xf
        b2 = ord(header_bytes[1])
        mask = b2 >> 7 & 1
        length = b2 & 0x7f

        length_data = ""
        if length == 0x7e:
            length_data = self._recv_strict(2)
            length = struct.unpack("!H", length_data)[0]
        elif length == 0x7f:
            length_data = self._recv_strict(8)
            length = struct.unpack("!Q", length_data)[0]

        mask_key = ""
        if mask:
            mask_key = self._recv_strict(4)
        data = self._recv_strict(length)
        if traceEnabled:
            recieved = header_bytes + length_data + mask_key + data
            logger.debug("recv: " + repr(recieved))

        if mask:
            data = ABNF.mask(mask_key, data)

        frame = ABNF(fin, rsv1, rsv2, rsv3, opcode, mask, data)
        return frame

    def send_close(self, status = STATUS_NORMAL, reason = ""):
        """
        send close data to the server.

        status: status code to send. see STATUS_XXX.

        reason: the reason to close. This must be string.
        """
        if status < 0 or status >= ABNF.LENGTH_16:
            raise ValueError("code is invalid range")
        self.send(struct.pack('!H', status) + reason, ABNF.OPCODE_CLOSE)

    def close(self, status = STATUS_NORMAL, reason = ""):
        """
        Close Websocket object

        status: status code to send. see STATUS_XXX.

        reason: the reason to close. This must be string.
        """
        if self.connected:
            if status < 0 or status >= ABNF.LENGTH_16:
                raise ValueError("code is invalid range")

            try:
                self.send(struct.pack('!H', status) + reason, ABNF.OPCODE_CLOSE)
                timeout = self.sock.gettimeout()
                self.sock.settimeout(3)
                try:
                    frame = self.recv_frame()
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.error("close status: " + repr(frame.data))
                except:
                    pass
                self.sock.settimeout(timeout)
                self.sock.shutdown(socket.SHUT_RDWR)
            except:
                pass
        self._closeInternal()

    def _closeInternal(self):
        self.connected = False
        self.sock.close()
        self.io_sock = self.sock

    def _recv(self, bufsize):
        bytes = self.io_sock.recv(bufsize)
        if not bytes:
            raise WebSocketConnectionClosedException()
        return bytes

    def _recv_strict(self, bufsize):
        remaining = bufsize
        bytes = ""
        while remaining:
            bytes += self._recv(remaining)
            remaining = bufsize - len(bytes)

        return bytes

    def _recv_line(self):
        line = []
        while True:
            c = self._recv(1)
            line.append(c)
            if c == "\n":
                break
        return "".join(line)


class WebSocketApp(object):
    """
    Higher level of APIs are provided.
    The interface is like JavaScript WebSocket object.
    """
    def __init__(self, url,
                 on_open = None, on_message = None, on_error = None,
                 on_close = None, keep_running = True, get_mask_key = None):
        """
        url: websocket url.
        on_open: callable object which is called at opening websocket.
          this function has one argument. The arugment is this class object.
        on_message: callbale object which is called when recieved data.
         on_message has 2 arguments.
         The 1st arugment is this class object.
         The passing 2nd arugment is utf-8 string which we get from the server.
       on_error: callable object which is called when we get error.
         on_error has 2 arguments.
         The 1st arugment is this class object.
         The passing 2nd arugment is exception object.
       on_close: callable object which is called when closed the connection.
         this function has one argument. The arugment is this class object.
       keep_running: a boolean flag indicating whether the app's main loop should
         keep running, defaults to True
       get_mask_key: a callable to produce new mask keys, see the WebSocket.set_mask_key's
         docstring for more information
        """
        self.url = url
        self.on_open = on_open
        self.on_message = on_message
        self.on_error = on_error
        self.on_close = on_close
        self.keep_running = keep_running
        self.get_mask_key = get_mask_key
        self.sock = None

    def send(self, data, opcode = ABNF.OPCODE_TEXT):
        """
        send message.
        data: message to send. If you set opcode to OPCODE_TEXT, data must be utf-8 string or unicode.
        opcode: operation code of data. default is OPCODE_TEXT.
        """
        if self.sock.send(data, opcode) == 0:
            raise WebSocketConnectionClosedException()

    def close(self):
        """
        close websocket connection.
        """
        self.keep_running = False
        self.sock.close()

    def run_forever(self):
        """
        run event loop for WebSocket framework.
        This loop is infinite loop and is alive during websocket is available.
        """
        if self.sock:
            raise WebSocketException("socket is already opened")
        try:
            self.sock = WebSocket(self.get_mask_key)
            self.sock.connect(self.url)
            self._run_with_no_err(self.on_open)
            while self.keep_running:
                data = self.sock.recv()
                if data is None:
                    break
                self._run_with_no_err(self.on_message, data)
        except Exception, e:
            self._run_with_no_err(self.on_error, e)
        finally:
            self.sock.close()
            self._run_with_no_err(self.on_close)
            self.sock = None

    def _run_with_no_err(self, callback, *args):
        if callback:
            try:
                callback(self, *args)
            except Exception, e:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.error(e)


if __name__ == "__main__":
    enableTrace(True)
    ws = create_connection("ws://echo.websocket.org/")
    print "Sending 'Hello, World'..."
    ws.send("Hello, World")
    print "Sent"
    print "Receiving..."
    result = ws.recv()
    print "Received '%s'" % result
    ws.close()

########NEW FILE########
