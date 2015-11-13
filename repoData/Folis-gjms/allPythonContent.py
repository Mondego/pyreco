__FILENAME__ = app
"""

    gjms.backend.app

    The app container for GJMS.

"""

import os
import sys
import flask
import jinja2_hamlpy

from werkzeug.contrib.fixers import ProxyFix

sys.path.append(os.path.abspath(os.path.dirname(__file__) + '/' + '../..'))

app = flask.Flask(__name__, static_folder="../media", template_folder="../templates")
app.jinja_env.add_extension("jinja2_hamlpy.HamlPyExtension")
app.secret_key = os.urandom(24)
app.wsgi_app = ProxyFix(app.wsgi_app)
app.debug = True

########NEW FILE########
__FILENAME__ = routes
"""

    gjms.backend.routes

    All backend routes.

"""

import os
import sys
import flask
import elixir
import datetime

sys.path.append(os.path.abspath(os.path.dirname(__file__) + '/' + '../..'))

import gjms.util.report
import gjms.util.password
import gjms.util.database

import gjms.core.system
import gjms.core.users
import gjms.core.events
import gjms.core.games
import gjms.core.platforms
import gjms.core.ratings
import gjms.core.exceptions
import gjms.backend.forms

from gjms.backend.app import app
from gjms.config import parser

"""
@app.route("/login/<name>/<pwd>")
def gjms_login(name, pwd):
    try:
        user = gjms.core.users.get(name)
        if gjms.core.users.login(name, pwd):
            flask.ext.login.login_user(user)
            return "YEP."
        else:
            return "NOPE."
    except gjms.core.exceptions.NonExistentUser:
        return "User does not exist. Sorry."
gjms.util.report.output("Setup route /login/<name>/<pwd>")
"""

@app.route("/populate/<entries>")
def gjms_populate(entries):
    import gjms.util

    try:
        entries = int(entries)
    except TypeError:
        return "Please enter an integer."
    else:
        return gjms.util.populate_db(entries)

@app.route("/game/<id_slug>")
def gjms_game(id_slug):
    """ Display a game. """
    try:
        game = gjms.core.games.get(id_slug)
        system = gjms.core.system.get(1)
        return flask.render_template("frontend/game.haml", game=game, time=datetime, system=system, config=parser, users=gjms.core.users, events=gjms.core.events, games=gjms.core.games, platforms=gjms.core.platforms, ratings=gjms.core.ratings)
    except gjms.core.exceptions.NonExistentGame:
        try:
            game = gjms.core.games.by_slug(id_slug)
            system = gjms.core.system.get(1)
            return flask.render_template("frontend/game.haml", game=game, time=datetime, system=system, config=parser, users=gjms.core.users, events=gjms.core.events, games=gjms.core.games, platforms=gjms.core.platforms, ratings=gjms.core.ratings)
        except gjms.core.exceptions.NonExistentGame:
            return "We couldn't find the game you were looking for. Sorry."

@app.route("/gjms/home/")
def gjms_central():
    if parser.getboolean("gjms", "database_setup") == False:
        return flask.redirect("../../gjms/config/")
    system = gjms.core.system.get(1)
    return flask.render_template("backend/home.haml", time=datetime, system=system, config=parser, users=gjms.core.users, events=gjms.core.events, games=gjms.core.games, platforms=gjms.core.platforms, ratings=gjms.core.ratings)
gjms.util.report.output("Setup route /gjms/home/")

@app.route("/gjms/users/")
def gjms_users():
    if parser.getboolean("gjms", "database_setup") == False:
        return flask.redirect("../../gjms/config/")
    system = gjms.core.system.get(1)
    return flask.render_template("backend/users.haml", time=datetime, system=system, config=parser, users=gjms.core.users, events=gjms.core.events, games=gjms.core.games, platforms=gjms.core.platforms, ratings=gjms.core.ratings)
gjms.util.report.output("Setup route /gjms/users/")

@app.route("/gjms/games/")
def gjms_games():
    if parser.getboolean("gjms", "database_setup") == False:
        return flask.redirect("../../gjms/config/")
    system = gjms.core.system.get(1)
    return flask.render_template("backend/games.haml", time=datetime, system=system, config=parser, users=gjms.core.users, events=gjms.core.events, games=gjms.core.games, platforms=gjms.core.platforms, ratings=gjms.core.ratings)
gjms.util.report.output("Setup route /gjms/games/")

@app.route("/gjms/event/<event>")
def gjms_event_overview(event):
    if parser.getboolean("gjms", "database_setup") == False:
        return flask.redirect("../../gjms/config/")
    system = gjms.core.system.get(1)
    req_event = gjms.core.events.by_slug(event)

    return flask.render_template("backend/show_event_overview.haml", time=datetime, system=system, config=parser, users=gjms.core.users, events=gjms.core.events, games=gjms.core.games, platforms=gjms.core.platforms, ratings=gjms.core.ratings, event=req_event)


@app.route("/gjms/events/")
def gjms_events():
    if parser.getboolean("gjms", "database_setup") == False:
        return flask.redirect("../../gjms/config/")
    system = gjms.core.system.get(1)
    return flask.render_template("backend/events.haml", time=datetime, system=system, config=parser, users=gjms.core.users, events=gjms.core.events, games=gjms.core.games, platforms=gjms.core.platforms, ratings=gjms.core.ratings)
gjms.util.report.output("Setup route /gjms/events/")

@app.route("/gjms/config/", methods=["GET", "POST"])
def gjms_config():
    """ Setup backend config """
    form = gjms.backend.forms.config(flask.request.form)

    if flask.request.method == "POST":
        if form.validate_on_submit():
            parser.set("gjms", "label", form.label.data)
            parser.set("gjms", "manager", form.manager.data)
            parser.set("gjms", "manager_email", form.m_email.data)
            parser.set("gjms", "theme_voting", form.v_theme.data)
            parser.set("gjms", "game_ratings", form.ratings.data)
            parser.set("gjms", "game_comments", form.comments.data)

            parser.set("gjms", "database_engine", form.engine.data)
            parser.set("gjms", "database_host", form.host.data)
            parser.set("gjms", "database_port", form.port.data)
            parser.set("gjms", "database_user", form.user.data)
            parser.set("gjms", "database_password", form.password.data)
            parser.set("gjms", "database", form.db.data)

            if form.engine.data == "sqlite":
                db_url = "sqlite:///%s?check_same_thread=False" % form.host.data
            elif form.engine.data != "sqlite" and form.port.data == "":
                db_url = "%s://%s:%s@%s/%s" % (form.engine.data, form.user.data, form.password.data, form.host.data, form.db.data)
            else:
                db_url = "%s://%s:%s@%s:%s/%s" % (form.engine.data, form.user.data, form.password.data, form.host.data, form.port.data, form.db.data)

            gjms.util.database.setup(db_url)
            elixir.setup_all()
            elixir.create_all()

            parser.set("gjms", "db_url", db_url)
            parser.set("gjms", "database_setup", True)

            cfgfile = open(os.path.abspath(os.path.dirname(__file__)+"/../gjms.cfg"), "w")
            gjms.config.parser.write(cfgfile)

            flask.flash(u"Your settings have been saved!", "success")
        else:
            flask.flash(u"Woops! That didn't work! Check below for details.", "error")
    else:
        form.label.data = parser.get("gjms", "label")
        form.manager.data = parser.get("gjms", "manager")
        form.m_email.data = parser.get("gjms", "manager_email")
        form.v_theme.data = parser.getboolean("gjms", "theme_voting")
        form.ratings.data = parser.getboolean("gjms", "game_ratings")
        form.comments.data = parser.getboolean("gjms", "game_comments")

        form.engine.data = parser.get("gjms", "database_engine")
        form.host.data = parser.get("gjms", "database_host")
        form.port.data = parser.get("gjms", "database_port")
        form.user.data = parser.get("gjms", "database_user")
        form.password.data = parser.get("gjms", "database_password")
        form.db.data = parser.get("gjms", "database")

    if parser.getboolean("gjms", "database_setup") is False:
        flask.flash(u"Welcome to the Game Jam Management System!", "success")
        flask.flash(u"To get you started, we need to set up a database for the system to use.", "note")
        flask.flash(u"""
            If you want to get started quickly, just hit the Save button and
            be done with it. The system is pre-configured to use SQLite.
            You can use MySQL or Postgres too, though! It's up to you, really.
        """, "note")

    system = gjms.core.system.get(1)
    return flask.render_template("backend/config.haml", form=form, time=datetime, system=system, config=parser, users=gjms.core.users, events=gjms.core.events, games=gjms.core.games, platforms=gjms.core.platforms, ratings=gjms.core.ratings)
gjms.util.report.output("Setup route /gjms/config/")



########NEW FILE########
__FILENAME__ = config
#coding: utf8

"""

    gjms.config

    A parser for the gjms.cfg file.
    Used for config updates within the scripts.

"""

import os
import sys
import ConfigParser

import gjms.util.report

sys.path.append(os.path.abspath(os.path.dirname(__file__) + '/' + '../..'))

class ConfigParserFix(ConfigParser.RawConfigParser):
    """
        Apparently the getboolean method of the RawConfigParser is broken.
        Here's a fix.
    """

    def getboolean(self, section, option):
        result = self.get(section, option)
        try:
            trues = ["1", "yes", "true", "on"]
            falses = ["0", "no", "false", "off"]
            if result.lower() in trues:
                return True
            if result.lower() in falses:
                return False
        except AttributeError as err:
            if str(err) == "\'bool\' object has no attribute \'lower\'":
                return result
            raise err

parser = ConfigParserFix()
parser.read(os.path.abspath(os.path.dirname(__file__)+"/gjms.cfg"))

gjms.util.report.output(parser.sections())

########NEW FILE########
__FILENAME__ = routes
"""

    gjms.frontend.routes

    All the frontend routes.

"""

import os
import sys
import flask
import datetime

import gjms.core.system
import gjms.core.users
import gjms.core.events
import gjms.core.games
import gjms.core.platforms
import gjms.core.ratings

import gjms.util.report

from gjms.backend.app import app
from gjms.config import parser

sys.path.append(os.path.abspath(os.path.dirname(__file__) + '/' + '../..'))

@app.route("/")
def gjms_root():
    """ The root route. """
    system = gjms.core.system.get(1)
    return flask.render_template("frontend/home.haml", time=datetime, system=system, config=parser, users=gjms.core.users, events=gjms.core.events, games=gjms.core.games, platforms=gjms.core.platforms, ratings=gjms.core.ratings)
gjms.util.report.output("Setup route /")

########NEW FILE########
__FILENAME__ = test
#coding: utf8

"""

    gjms.test.test

    A thorough unit test of the whole GJMS module.
    If you add a new feature, be sure to include a unit test
    for said feature and make sure the unit test passes.

"""

import os
import sys

sys.path.append(os.path.abspath(os.path.dirname(__file__) + '/' + '../..'))

#Import nose-specific tools.
from nose.tools import assert_raises
from nose.tools import with_setup

# Import core modules.
import gjms.core.users as users
import gjms.core.games as games
import gjms.core.models as models
import gjms.core.events as events
import gjms.core.ratings as ratings
import gjms.core.platforms as platforms
import gjms.core.exceptions as exceptions

# Import util modules.
import gjms.util.url as url
import gjms.util.email as email
import gjms.util.password as password


def init():
    """ Turn off harmless SQLAlchemy warnings. """

    import warnings
    from sqlalchemy import exc as sa_exc

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=sa_exc.SAWarning)


def teardown():
    """ Provided for nosetests. No use. """
    pass

##
## START TESTING:
##


@with_setup(init, teardown)
def test_email_parsing_pass():
    """ Test if correct email passes parsing. """

    assert True == email.validate("user@example.com")


@with_setup(init, teardown)
def test_email_parsing_fail():
    """ Test if wrong email fails parsing. """

    assert_raises(exceptions.InvalidEmail, email.validate, "userexample.com")
    assert_raises(exceptions.InvalidEmail, email.validate, "user@examplecom")
    assert_raises(exceptions.InvalidEmail, email.validate, "userexamplecom")


@with_setup(init, teardown)
def test_url_parsing_pass():
    """ Test if correct URL passes parsing. """

    assert True == url.validate("http://example.com")
    assert True == url.validate("http://example.com/")
    assert True == url.validate("http://www.example.com")
    assert True == url.validate("http://www.example.com/")


@with_setup(init, teardown)
def test_url_parsing_fail():
    """ Test if wrong URL fails parsing. """

    assert_raises(exceptions.InvalidURL, url.validate, "example.com")
    assert_raises(exceptions.InvalidURL, url.validate, "examplecom")
    assert_raises(exceptions.InvalidURL, url.validate, "example;com")


@with_setup(init, teardown)
def test_password_hashing():
    """ Test if password is being hashed. """

    pwd = "password"
    hashed_pwd = password.encrypt(pwd)

    assert pwd != hashed_pwd


@with_setup(init, teardown)
def test_password_validation():
    """ Test if password validation works. """

    pwd = "password"
    hashed_pwd = password.encrypt(pwd)

    assert True == password.validate(pwd, hashed_pwd)


@with_setup(init, teardown)
def test_user_add_right():
    """ Test correct way of adding a user. """

    user = users.add("user", "password", "user@example.com")
    assert type(user) == models.User


@with_setup(init, teardown)
def test_user_add_wrong():
    """ Test wrong way of adding a user. """

    assert_raises(exceptions.InvalidEmail, users.add, "user2", "password", "userexample.com")
    assert_raises(exceptions.InvalidEmail, users.add, "user2", "password", "user@examplecom")
    assert_raises(exceptions.InvalidEmail, users.add, "user2", "password", "userexamplecom")


@with_setup(init, teardown)
def test_user_get():
    """ Test user getting. """

    user = None
    user = users.get("user")

    assert type(user) == models.User


def test_user_get_incorrect():
    """ Test incorrect getting of userss. """

    assert_raises(exceptions.NonExistentUser, users.get, 200)


@with_setup(init, teardown)
def test_user_update():
    """ Test user updating. """

    user = users.get("user")
    user.name = "test_user"

    assert user.name == "test_user"


def test_game_add():
    """ Test game adding. """

    game = games.add("Flingler", "LD26 physics game", "http://hostagamejam.com/flingler.png")
    game2 = games.add("Flingler II", "LD27 physics game", "hostagamejam.com/flingler.png")

    assert type(game) == models.Game
    assert type(game2) == models.Game


def test_game_get_correct():
    """ Test game getting. """

    game = games.get("Flingler")
    assert type(game) == models.Game


def test_game_get_incorrect():
    """ Test incorrect game getting """

    assert_raises(exceptions.NonExistentGame, games.get, 200)


def test_user_game_relation_user():
    """ Test user-game relationship from a user viewpoint. """

    user = users.get("test_user")
    game = games.get("Flingler")
    game2 = games.get("Flingler II")

    user.games.append(game)
    user.games.append(game2)

    assert game in user.games
    assert game2 in user.games


def test_user_game_relation_game():
    """ Test user-game relationship from a game viewpoint. """

    game = games.get("Flingler")

    assert game.author.name == "test_user"


def test_platform_add():
    """ Test platform adding. """

    windows = platforms.add("Windows", "http://hostagamejam.com/flingler.exe")
    android = platforms.add("Android", "hostagamejam.com/flingler.apk")

    assert type(windows) == models.Platform
    assert type(android) == models.Platform


def test_platform_get():
    """ Test platform getting. """

    platform = platforms.get("Windows")

    assert type(platform) == models.Platform


def test_platform_get_incorrect():
    """ Test incorrect getting of platforms. """

    assert_raises(exceptions.NonExistentPlatform, platforms.get, 200)


def test_plat_game_relation_game():
    """ Test platform-game relationship from a game viewpoint. """

    game = games.get("Flingler")
    platform = platforms.get("Windows")
    platform2 = platforms.get("Android")

    game.platforms.append(platform)
    game.platforms.append(platform2)

    assert platform in game.platforms
    assert platform2 in game.platforms


def test_plat_game_relation_plat():
    """ Test platform-game relationship from a platform viewpoint. """

    platform = platforms.get("Android")
    game = games.get("Flingler")

    assert game in platform.games


def test_add_rating_correct():
    """ Test rating adding correctly. """

    rating = ratings.add(4.0)
    rating = ratings.add(3.0)
    rating = ratings.add(2.0)

    assert type(rating) == models.Rating


def test_add_rating_incorrect():
    """ Test rating adding incorrectly. """

    assert_raises(exceptions.InvalidValue, ratings.add, 4)


def test_rating_get_correct():
    """ Test correct getting of ratings. """

    rating = ratings.get(1)
    assert type(rating) == models.Rating


def test_rating_get_incorrect():
    """ Test incorrect getting of ratings. """

    assert_raises(exceptions.NonExistentRating, ratings.get, 200)


def test_game_add_rating():
    """ Test adding ratings to a game. """

    game = games.get("Flingler")

    rating = ratings.get(1)
    rating2 = ratings.get(2)
    rating3 = rating.get(3)

    game.ratings.append(rating)
    game.ratings.append(rating2)
    game.ratings.append(rating3)

    assert rating in game.ratings
    assert rating3 in game.ratings


def test_calculate_rating_correct():
    """ Test if rating is calculated correctly. """

    game = games.get("Flingler")
    rating = ratings.calculate(game)

    assert 3.0 == rating


def test_calculate_rating_incorrect():
    """ Test if rating calculation fails when not passing a game object. """

    assert_raises(exceptions.InvalidParameter, ratings.calculate, "Flingler")


def test_add_event_correct():
    """ Test correct event adding. """

    import datetime as d

    starts = d.datetime(2014, 3, 17, 1)
    ends = d.datetime(2014, 3, 21, 1)

    event = events.add(starts, ends, "Spring Jam Week", "Some theme")
    assert type(event) == models.Event


def test_add_event_incorrect():
    """ Test incorrect event adding. """

    assert_raises(exceptions.InvalidValue, events.add, 3, 2, "Test Event")


def test_event_get():
    """ Test event getting """

    event = events.get(1)
    assert type(event) == models.Event


def test_game_event():
    """ Test event game adding """

    event = events.get(1)
    game = games.get(1)

    event.games.append(game)

    assert game in event.games


def test_participant_event():
    """ Test event participant adding """

    event = events.get(1)
    user = users.get(1)

    event.participants.append(user)

    assert user in event.participants


def test_participant_event_reverse():
    """ Test user events """

    event = events.get(1)
    user = users.get(1)

    assert event in user.participated


def test_delete_game():
    """ Test game deleting. """

    game = games.get("Flingler")
    game.delete()

    assert_raises(exceptions.NonExistentGame, games.get, "Flingler")


def test_delete_user():
    """ Test user deleting. """

    user = users.get("test_user")
    user.delete()

    assert_raises(exceptions.NonExistentUser, users.get, "test_user")


def test_delete_platform():
    """ Test platform deleting. """

    platform = platforms.get("Windows")
    platform.delete()

    assert_raises(exceptions.NonExistentPlatform, platforms.get, "Windows")


def test_delete_rating():
    """ Test rating deleting. """

    rating = ratings.get(1)
    rating.delete()

    assert_raises(exceptions.NonExistentRating, ratings.get, 1)


def test_delete_event():
    """ Test event deleting. """

    event = events.get(1)
    event.delete()

    assert_raises(exceptions.NonExistentEvent, events.get, 1)



########NEW FILE########
__FILENAME__ = database
#coding: utf8
""" Module for connecting and setting up a database. """

import os
import sys

import elixir
import gjms.util.report

sys.path.append(os.path.abspath(os.path.dirname(__file__) + '/' + '../..'))
gjms_database = elixir.metadata

def setup(database):
    """ Connect to database and setup all models """
    gjms_database.bind = "%s" % database
    gjms_database.bind.echo = False

    gjms.util.report.output("Database (%s) initialized." % database)
    gjms.util.report.log("Database (%s) initialized." % database)

########NEW FILE########
__FILENAME__ = email
#coding: utf8

""" Check if a given e-mail fits the format x@y.z """

import os
import sys

sys.path.append(os.path.abspath(os.path.dirname(__file__) + '/' + '../..'))

import re
import gjms.core.exceptions


def validate(email):
    """ Validate e-mail according to regex """
    if re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return True
    else:
        raise gjms.core.exceptions.InvalidEmail("E-mail not in a valid format.")


########NEW FILE########
__FILENAME__ = password
# coding: utf8
"""

Securely hash and check passwords using PBKDF2.

Use random salts to protect against rainbowtables, many iterations against
brute-force, and constant-time comparison against timing attacks.

Keep parameters to the algorithm together with the hash so that we can
change the parameters and keep older hashes working.

See more details at http://exyr.org/2011/hashing-passwords/

Author: Simon Sapin
License: BSD

"""

import os
import sys

sys.path.append(os.path.abspath(os.path.dirname(__file__) + '/' + '../..'))

import hashlib
from os import urandom
from base64 import b64encode, b64decode
from itertools import izip

# From https://github.com/mitsuhiko/python-pbkdf2
from pbkdf2 import pbkdf2_bin


# Parameters to PBKDF2. Only affect new passwords.
SALT_LENGTH = 12
KEY_LENGTH = 24
HASH_FUNCTION = 'sha256'  # Must be in hashlib.
# Linear to the hashing time. Adjust to be high but take a reasonable
# amount of time on your server. Measure with:
# python -m timeit -s 'import passwords as p' 'p.make_hash("something")'
COST_FACTOR = 10000


def encrypt(password):
    """Generate a random salt and return a new hash for the password."""
    if isinstance(password, unicode):
        password = password.encode('utf-8')
    salt = b64encode(urandom(SALT_LENGTH))
    return 'PBKDF2${}${}${}${}'.format(
        HASH_FUNCTION,
        COST_FACTOR,
        salt,
        b64encode(pbkdf2_bin(password, salt, COST_FACTOR, KEY_LENGTH,
                             getattr(hashlib, HASH_FUNCTION))))


def validate(password, hash_):
    """Check a password against an existing hash."""
    if isinstance(password, unicode):
        password = password.encode('utf-8')
    algorithm, hash_function, cost_factor, salt, hash_a = hash_.split('$')
    assert algorithm == 'PBKDF2'
    hash_a = b64decode(hash_a)
    hash_b = pbkdf2_bin(password, salt, int(cost_factor), len(hash_a),
                        getattr(hashlib, hash_function))
    assert len(hash_a) == len(hash_b)  # we requested this from pbkdf2_bin()
    # Same as "return hash_a == hash_b" but takes a constant time.
    # See http://carlos.bueno.org/2011/10/timing.html
    diff = 0
    for char_a, char_b in izip(hash_a, hash_b):
        diff |= ord(char_a) ^ ord(char_b)
    return diff == 0

########NEW FILE########
__FILENAME__ = report
# coding: utf8

"""

    gjms.util.report

    Output, logging and reporting of various things.

"""

import inspect
import time


def log(string):
    """ Log to gjms.log """

    module = inspect.currentframe().f_back
    gjms_log = open("gjms.log", "w")

    gjms_log.write("[%s] %s - %s \n" % (time.strftime("%d/%m/%Y | %H:%M:%S"), module.f_globals['__name__'], string))


def output(string):
    """ Log into console """

    module = inspect.currentframe().f_back
    print "[%s] %s - %s" % (time.strftime("%d/%m/%Y | %H:%M:%S"), module.f_globals['__name__'], string)

########NEW FILE########
__FILENAME__ = url
#coding: utf8

"""

    gjms.util.url

    A module for checking if the user has provided a valid URL and not
    a random string.

"""

import os
import sys

import gjms.core.exceptions


sys.path.append(os.path.abspath(os.path.dirname(__file__) + '/' + '../..'))

import re


def validate(url):
    """ Check if the provided string matches a URL regex. """
    regex = re.compile(
        r'^(?:http|ftp)s?://'    # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'    # domain...
        r'localhost|'    # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}|'  # ...or ipv4
        r'\[?[A-F0-9]*:[A-F0-9:]+\]?)'   # ...or ipv6
        r'(?::\d+)?'     # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    if regex.match(url):
        return True
    else:
        raise gjms.core.exceptions.InvalidURL("URL not in a valid format.")

########NEW FILE########
