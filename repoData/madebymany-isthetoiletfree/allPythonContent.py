__FILENAME__ = client
#!/usr/bin/env python

import os
import hmac
import hashlib
import datetime
import urllib
import json

from tornado.ioloop import IOLoop, PeriodicCallback
from tornado.httpclient import AsyncHTTPClient
from gpiocrust import Header, PWMOutputPin, InputPin


def percentage_filter(function, iterable):
    count = 0
    for element in iterable:
        if function(element):
            count += 1
    return float(count) / float(len(iterable))


def one(iterable):
    elements = [e for e in iterable if e]
    return len(elements) == 1


SERVER_URL = os.getenv("ITTF_SERVER_URL", "http://localhost:8888/")
INTERVAL = 2000.0
HMAC_SECRET = open(os.path.join(os.path.dirname(__file__),
                                ".hmac_secret")).read().strip()

led_map = {"r": 8, "g": 10, "b": 12}
switch_map = (22, 24, 26)


class RGBLED(object):
    def __init__(self, r, g, b, hz=50.0, color=(0, 0, 0)):
        self.pulses = [PWMOutputPin(p, frequency=hz) for p in (r, g, b)]
        self._frequency = hz
        self._color = color

    @property
    def frequency(self):
        return self._frequency

    @frequency.setter
    def frequency(self, value):
        self._frequency = value
        for p in self.pulses:
            p.frequency = value

    @property
    def color(self):
        return self._color

    @color.setter
    def color(self, color):
        self._color = color
        for p, c in zip(self.pulses, self._color):
            p.value = c / 255.0

    def color_between(self, c1, c2, delta):
        return tuple(b + ((a - b) * delta) for a, b in zip(c1, c2))


class Toilet(object):
    def __init__(self, tid=None, pin=None):
        self.tid = tid
        self.pin = pin
        self.input = InputPin(self.pin)

    @property
    def is_free(self):
        return not self.input.value

    def has_changed_state(self):
        try:
            return self.is_free != self.latest_is_free
        except AttributeError:
            return True
        finally:
            self.latest_is_free = self.is_free


def call_server(params):
    data = json.dumps(params)
    AsyncHTTPClient().fetch(SERVER_URL, method="POST", body=urllib.urlencode({
        "data": data,
        "token": hmac.new(HMAC_SECRET, data, hashlib.sha256).hexdigest()
    }))


if __name__ == "__main__":
    with Header() as header:
        toilets = [Toilet(tid=i, pin=p) for i, p in enumerate(switch_map)]
        led = RGBLED(**led_map)

        def update_state():
            percentage_free = percentage_filter(
                lambda e: e, [t.is_free for t in toilets])
            led.color = led.color_between(
                (0, 255, 0), (255, 0, 0), percentage_free)

            timestamp = datetime.datetime.now().isoformat()
            params = []
            for t in toilets:
                if t.has_changed_state():
                    params.append(dict(
                        toilet_id=t.tid,
                        is_free="yes" if t.is_free else "no",
                        timestamp=timestamp
                    ))
            if len(params):
                call_server(params)

        try:
            PeriodicCallback(update_state, INTERVAL).start()
            IOLoop.instance().start()
        except KeyboardInterrupt:
            pass

########NEW FILE########
__FILENAME__ = leds
#!/usr/env/bin python

from RPi import GPIO
from time import sleep

GPIO.setmode(GPIO.BOARD)

PINS = (8, 10, 12)

for p in PINS:
    GPIO.setup(p, GPIO.OUT)
    GPIO.output(p, False)

r, g, b = PINS

try:
    while True:
        GPIO.output(b, False)
        GPIO.output(r, True)
        sleep(1)
        GPIO.output(r, False)
        GPIO.output(g, True)
        sleep(1)
        GPIO.output(g, False)
        GPIO.output(b, True)
        sleep(1)
except KeyboardInterrupt:
    pass

########NEW FILE########
__FILENAME__ = switches
#!/usr/env/bin python

from RPi import GPIO
from time import sleep

GPIO.setmode(GPIO.BOARD)

PINS = (22, 24, 26)

latest_states = {}
for p in PINS:
    GPIO.setup(p, GPIO.IN)
    latest_states[p] = GPIO.input(p)

try:
    while True:
        for p in PINS:
            state = GPIO.input(p)
            if state and state != latest_states[p]:
                print "%s on" % p
            latest_states[p] = state
        sleep(0.5)
except KeyboardInterrupt:
    pass

########NEW FILE########
__FILENAME__ = server
#!/usr/bin/env python

import tornado.ioloop
import tornado.web
import tornado.gen
import tornado.websocket
import tornado.auth
import tornado.escape
import hmac
import hashlib
import functools
import os
import momoko
import urlparse
import time
import datetime
import parsedatetime
import prettytable
import ascii_graph
import logging

from tornado.options import define, options

define("port", default=8888, help="run on the given port", type=int)
define("db_host", default="localhost", help="database hostname", type=str)
define("db_port", default=5432, help="database port", type=int)
define("db_name", default="callum", help="database name", type=str)
define("db_user", default="callum", help="database username", type=str)
define("db_pass", default="", help="database password", type=str)


class HumanDateParser(object):
    def __init__(self):
        self.calendar = parsedatetime.Calendar()

    def parse(self, str):
        return datetime.datetime.fromtimestamp(
            time.mktime(self.calendar.parse(str)[0]))


def get_psql_credentials():
    try:
        urlparse.uses_netloc.append("postgres")
        url = urlparse.urlparse(os.getenv("DATABASE_URL"))
        credentials = { "host": url.hostname, "port": url.port,
                        "dbname": url.path[1:], "user": url.username,
                        "password": url.password }
    except:
        credentials = { "host": options.db_host, "port": options.db_port,
                        "dbname": options.db_name, "user": options.db_user,
                        "password": options.db_pass }
    return credentials


def _get_secret(filename, envvar):
    try:
        with open(os.path.join(os.path.dirname(__file__), filename)) as f:
            return f.read().strip()
    except IOError:
        return os.getenv(envvar)

get_hmac_secret = \
    functools.partial(_get_secret, ".hmac_secret", "ITTF_HMAC_SECRET")
get_cookie_secret = \
    functools.partial(_get_secret, ".cookie_secret", "ITTF_COOKIE_SECRET")


def hmac_authenticated(method):
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        hash = hmac.new(
            self.settings["hmac_secret"],
            self.get_argument("data"),
            hashlib.sha256
        )
        if self.get_argument("token") != hash.hexdigest():
            raise tornado.web.HTTPError(401, "Invalid token")
        return method(self, *args, **kwargs)
    return wrapper


def bool2str(boolean):
    return "yes" if boolean else "no"


class HasFreeWebSocketHandler(tornado.websocket.WebSocketHandler):
    connections = set()

    def open(self):
        HasFreeWebSocketHandler.connections.add(self)

    def on_message(self, message):
        pass

    def on_close(self):
        HasFreeWebSocketHandler.connections.remove(self)


class BaseHandler(tornado.web.RequestHandler):
    @property
    def db(self):
        return self.application.db

    def get_current_user(self):
        return self.get_secure_cookie("ittf_user")

    @tornado.gen.coroutine
    def has_free_toilet(self):
        cursor = yield momoko.Op(self.db.callproc, "any_are_free")
        raise tornado.gen.Return(cursor.fetchone()[0])


class GoogleLoginHandler(BaseHandler, tornado.auth.GoogleMixin):
    @tornado.gen.coroutine
    def get(self):
        if self.get_argument("openid.mode", None):
            email = (yield self.get_authenticated_user())["email"]
            if email.endswith("@madebymany.co.uk") or \
               email.endswith("@madebymany.com"):
                self.set_secure_cookie("ittf_user", email)
                self.redirect("/stats")
            self.redirect("/")
        else:
            yield self.authenticate_redirect()


class MainHandler(BaseHandler):
    @tornado.gen.coroutine
    def get(self):
        has_free = bool2str((yield self.has_free_toilet()))
        self.render("index.html", has_free_toilet=has_free)

    @hmac_authenticated
    @tornado.gen.coroutine
    def post(self):
        values = yield [momoko.Op(self.db.mogrify,
            "(%(toilet_id)s, %(is_free)s, %(timestamp)s)", t) \
            for t in tornado.escape.json_decode(self.get_argument("data"))
        ]
        yield momoko.Op(self.db.execute,
                        "INSERT INTO events (toilet_id, is_free, recorded_at) "
                        "VALUES %s;" % ", ".join(values))
        self.notify_has_free()
        self.finish()

    @tornado.gen.coroutine
    def notify_has_free(self):
        has_free = bool2str((yield self.has_free_toilet()))
        for connected in HasFreeWebSocketHandler.connections:
            try:
                connected.write_message({
                    "hasFree": has_free
                })
            except:
                logging.error("Error sending message", exc_info=True)


class StatsHandler(BaseHandler):
    @tornado.web.authenticated
    @tornado.gen.coroutine
    def get(self):
        parser = HumanDateParser()
        text = None
        op = None
        where = ""
        and_where = ""
        start = self.get_argument("from", None)
        end = self.get_argument("to", None)

        if start and end:
            parsed_start = parser.parse(start)
            parsed_end = parser.parse(end)
            text = "Showing from %s to %s" % (parsed_start, parsed_end)
            op = ("WHERE recorded_at BETWEEN %s AND %s",
                  (parsed_start, parsed_end))
        elif start:
            parsed_start = parser.parse(start)
            text = "Showing from %s onward" % parsed_start
            op = ("WHERE recorded_at >= %s", (parsed_start,))
        elif end:
            parsed_end = parser.parse(end)
            text = "Showing from %s backward" % parsed_end
            op = ("WHERE recorded_at <= %s", (parsed_end,))

        if op:
            where = yield momoko.Op(self.db.mogrify, *op)
            and_where = where.replace("WHERE", "AND", 1)

        queries = [
            ("Number of visits",
             "SELECT toilet_id, count(*) "
             "AS num_visits FROM visits %(where)s "
             "GROUP BY toilet_id ORDER BY toilet_id;"),
            ("Average visit duration",
             "SELECT toilet_id, avg(duration) "
             "AS duration_avg FROM visits %(where)s "
             "GROUP BY toilet_id ORDER BY toilet_id;"),
            ("Minimum visit duration",
             "SELECT toilet_id, min(duration) "
             "AS duration_min FROM visits %(where)s "
             "GROUP BY toilet_id ORDER BY toilet_id;"),
            ("Maximum visit duration",
             "SELECT toilet_id, max(duration) "
             "AS duration_max FROM visits %(where)s "
             "GROUP BY toilet_id ORDER BY toilet_id;"),
            ("Visits by hour",
             "SELECT s.hour AS hour_of_day, count(v.hour) "
             "FROM generate_series(0, 23) s(hour) "
             "LEFT OUTER JOIN (SELECT recorded_at, "
             "EXTRACT('hour' from recorded_at) "
             "AS hour FROM visits %(where)s) v on s.hour = v.hour "
             "GROUP BY s.hour ORDER BY s.hour;"),
            ("Visits by day",
             "SELECT s.dow AS day_of_week, count(v.dow) "
             "FROM generate_series(0, 6) s(dow) "
             "LEFT OUTER JOIN (SELECT recorded_at, "
             "EXTRACT('dow' from recorded_at) "
             "AS dow FROM visits %(where)s) v on s.dow = v.dow "
             "GROUP BY s.dow ORDER BY s.dow;")
        ]
        results = yield [momoko.Op(self.db.execute,
                                   q % {"where": where,
                                        "and_where": and_where}) \
                         for _, q in queries]

        cursor = yield momoko.Op(self.db.execute, (
            "SELECT (s.period * 10) AS seconds, count(v.duration) "
            "FROM generate_series(0, 500) s(period) "
            "LEFT OUTER JOIN (SELECT EXTRACT(EPOCH from duration) "
            "AS duration FROM visits) v on s.period = FLOOR(v.duration / 10) "
            "GROUP BY s.period HAVING s.period <= 36 ORDER BY s.period;")
        )
        graph = "\n".join(ascii_graph.Pyasciigraph()
                          .graph("Frequency graph", cursor.fetchall()))

        self.render("stats.html", text=text, start=start, end=end,
                    tables=[(queries[i][0], prettytable.from_db_cursor(r)) \
                            for i, r in enumerate(results)],
                    frequency_graph=graph)


class APIHandler(BaseHandler):
    @tornado.gen.coroutine
    def get(self):
        response = tornado.escape.json_encode({
            "has_free_toilet": (yield self.has_free_toilet())
        })
        callback = self.get_argument("callback", None)
        if callback:
            response = "%s(%s)" % (callback, response)
        self.set_header("content-type", "application/json")
        self.write(response)


if __name__ == "__main__":
    tornado.options.parse_command_line()
    app = tornado.web.Application(
        [(r"/login", GoogleLoginHandler),
         (r"/", MainHandler),
         (r"/stats", StatsHandler),
         (r"/api", APIHandler),
         (r"/hasfreesocket", HasFreeWebSocketHandler)],
        template_path=os.path.join(os.path.dirname(__file__), "templates"),
        hmac_secret=get_hmac_secret(),
        cookie_secret=get_cookie_secret(),
        login_url="/login"
    )
    app.db = momoko.Pool(
        dsn=" ".join(["%s=%s" % c for c in get_psql_credentials().iteritems()]),
        size=6
    )
    app.listen(options.port)

    try:
        tornado.ioloop.IOLoop.instance().start()
    except KeyboardInterrupt:
        pass

########NEW FILE########
