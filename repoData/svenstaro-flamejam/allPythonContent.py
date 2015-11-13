__FILENAME__ = env
from __future__ import with_statement
import os
import sys
from alembic import context
from sqlalchemy import engine_from_config, pool
from logging.config import fileConfig

sys.path.append(os.getcwd())

from flamejam import app, db

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# set the sqlalchemy url to the one defined for flask-sqlalchemy
config.set_main_option('sqlalchemy.url', app.config['SQLALCHEMY_DATABASE_URI'])

# Interpret the config file for Python logging.
# This line sets up loggers basically.
fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = db.Model.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(compare_type=True, url=url)

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    engine = engine_from_config(
                config.get_section(config.config_ini_section),
                prefix='sqlalchemy.',
                poolclass=pool.NullPool)

    connection = engine.connect()
    context.configure(
                compare_type=True,
                connection=connection,
                target_metadata=target_metadata
                )

    try:
        with context.begin_transaction():
            context.run_migrations()
    finally:
        connection.close()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()


########NEW FILE########
__FILENAME__ = fabfile
from __future__ import with_statement
from fabric.api import *
from fabric.contrib.console import confirm

env.hosts = ['apoc']
env.use_ssh_config = True

def deploy():
    code_dir = '/home/svenstaro/prj/flamejam'
    deploy_dir = '/srv/flamejam'

    # clone/pull using keybearer first
    with settings(warn_only=True):
        if run("test -d %s" % code_dir).failed:
            run("git clone git@github.com:svenstaro/flamejam.git %s" % code_dir)
    with cd(code_dir):
        run("git pull")
        sudo("make install")
        sudo("touch %s/flamejam.wsgi" % deploy_dir)

########NEW FILE########
__FILENAME__ = filters
from flamejam import app
from datetime import *
from dateutil import relativedelta
from flask import Markup
import time

# format a timestamp in default format (0000-00-00 00:00:00)
@app.template_filter()
def formattime(s):
    return s.strftime("%Y-%m-%d %H:%M:%S")

@app.template_filter()
def nicedate(s):
    return s.strftime("%A, %B %d, %Y - %H:%M")

def _s(n, s):
    if n == 0:
        return ""
    return str(n) + " " + s + ("s" if n > 1 else "")

def _delta(delta, short = True):
    threshold = 2
    if delta.years > 0:
        return _s(delta.years, "year") + ("" if short and delta.years > threshold else (" " + _s(delta.months, "month")))
    if delta.months > 0:
        return _s(delta.months, "month") + ("" if short and delta.months > threshold else (" " + _s(delta.days, "day")))
    if delta.days > 0:
        return _s(delta.days, "day") + ("" if short and delta.days > threshold else (" " + _s(delta.hours, "hour")))
    if delta.hours > 0:
        return _s(delta.hours, "hour") + ("" if short and delta.hours > threshold else (" " + _s(delta.minutes, "minute")))
    if delta.minutes > 0:
        return _s(delta.minutes, "minute") + ("" if short and delta.minutes > threshold else (" " + _s(delta.seconds, "second")))
    return _s(delta.seconds, "second")

def timedelta(starttime, endtime):
    return relativedelta.relativedelta(starttime, endtime)

def _absdelta(d):
    if d.seconds < 0 or d.minutes < 0 or d.hours < 0 or d.days < 0 or d.months < 0 or d.years < 0:
        return -d
    return d

# format a timedelta in human-readable format (e.g. "in 20 minutes" or "3 weeks ago")
@app.template_filter()
def humandelta(s, other = None, short = True):
    if other:
        # we got 2 datetimes
        return _delta(_absdelta(timedelta(other, s))).strip()

    if s.seconds < 0 or s.minutes < 0 or s.hours < 0 or s.days < 0 or s.months < 0 or s.years < 0:
        return "%s ago" % _delta(-s, short).strip()
    elif s.seconds > 0 or s.minutes > 0 or s.hours > 0 or s.days > 0 or s.months > 0 or s.years > 0:
        return "in %s" % _delta(s, short).strip()
    else:
        return str(s)

@app.template_filter()
def humantime(s, short = True):
    diff = timedelta(s, datetime.utcnow())
    if diff.months < 1:
        return Markup('<span title="' + str(formattime(s)) + '" class="time-title">' + str(humandelta(diff, short = short)) + '</span>')
    else:
        return formattime(s)


@app.template_filter()
def countdowndelta(s):
    hours, remainder = divmod(s.seconds, 60*60)
    minutes, seconds = divmod(remainder, 60)
    return '%02d:%02d:%02d:%02d' % (s.days, hours, minutes, seconds)

@app.template_filter()
def epoch(s):
    # s = datetime.utcnow()
    return time.mktime(s.timetuple())

########NEW FILE########
__FILENAME__ = forms
# -*- coding: utf-8 -*-

from wtforms.fields import *
from wtforms.validators import *
from wtforms.validators import ValidationError
from wtforms.ext.sqlalchemy.fields import QuerySelectField
from flask.ext.wtf import Form, RecaptchaField
from flask.ext.wtf.file import FileField, FileAllowed, FileRequired
from flask.ext.wtf.html5 import IntegerField, EmailField, IntegerRangeField, IntegerField
import re
from flamejam import app, models, utils
from flamejam.models.rating import RATING_CATEGORIES

############## VALIDATORS ####################

class Not(object):
    def __init__(self, call, message = None):
        self.call = call
        self.message = message

    def __call__(self, form, field):
        errored = False
        try:
            self.call(form, field)
        except ValidationError:
            # there was an error, so don't do anything
            errored = True

        if not errored:
            raise ValidationError(self.call.message if self.message == None else self.message)

class MatchesRegex(object):
    def __init__(self, regex, message = "This field matches the regex {0}"):
        self.regex = regex
        self.message = message

    def __call__(self, form, field):
        if not re.search(self.regex, field.data):
            raise ValidationError(self.message.format(self.regex))

class UsernameExists(object):
    def __call__(self, form, field):
        u = models.User.query.filter_by(username = field.data).first()
        if not u:
            raise ValidationError("The username does not exist.")

class EmailExists(object):
    def __call__(self, form, field):
        e = models.User.query.filter_by(email = field.data).first()
        if not e:
            raise ValidationError("That email does not exist")

class LoginValidator(object):
    def __init__(self, pw_field, message_username = "The username or password is incorrect.", message_password = "The username or password is incorrect."):
        self.pw_field = pw_field
        self.message_username = message_username
        self.message_password = message_password

    def __call__(self, form, field):
        u = models.User.query.filter_by(username = field.data).first()
        if not u:
            raise ValidationError(self.message_username)
        elif not utils.verify_password(u.password, form[self.pw_field].data):
            raise ValidationError(self.message_password)

class UsernameValidator(object):
    def __init__(self, message_username = "The username is incorrect."):
        self.message_username = message_username

    def __call__(self, form, field):
        u = models.User.query.filter_by(username = field.data).first()
        if not u:
            raise ValidationError(self.message_username)

############## FORMS ####################

class UserLogin(Form):
    username = TextField("Username", validators=[LoginValidator("password")])
    password = PasswordField("Password", validators = [])
    remember_me = BooleanField("Remember me", default = False)

class UserRegistration(Form):
    username = TextField("Username", validators=[
        Not(MatchesRegex("[^0-9a-zA-Z\-_]"), message = "Your username contains invalid characters. Only use alphanumeric characters, dashes and underscores."),
        Not(UsernameExists(), message = "That username already exists."),
        Length(min=3, max=80, message="You have to enter a username of 3 to 80 characters length.")])
    password = PasswordField("Password", validators=[Length(min=8, message = "Please enter a password of at least 8 characters.")])
    password2 = PasswordField("Password, again", validators=[EqualTo("password", "Passwords do not match.")])
    email = EmailField("Email", validators=[
            Not(EmailExists(), message = "That email address is already in use."),
            Email(message = "The email address you entered is invalid.")])
    captcha = RecaptchaField()

class ResetPassword(Form):
    username = TextField("Username", validators=[UsernameValidator()])
    captcha = RecaptchaField()

class NewPassword(Form):
    password = PasswordField("Password", validators=[Length(min=8, message = "Please enter a password of at least 8 characters.")])
    password2 = PasswordField("Password, again", validators=[EqualTo("password", "Passwords do not match.")])

class VerifyForm(Form):
    pass

class ContactUserForm(Form):
    message = TextAreaField("Message", validators=[Required()])
    captcha = RecaptchaField("Captcha")

class JamDetailsForm(Form):
    title = TextField("Title", validators=[Required(), Length(max=128)])
    theme = TextField("Theme", validators=[Length(max=128)])
    team_limit = IntegerField("Team size limit", validators=[NumberRange(min = 0)])
    start_time = DateTimeField("Start time", format="%Y-%m-%d %H:%M", validators=[Required()])

    registration_duration = IntegerField("Registration duration", validators=[Required(), NumberRange(min = 0)], default = 14 * 24)
    packaging_duration = IntegerField("Packaging duration", validators=[Required(), NumberRange(min = 0)], default = 24)
    rating_duration = IntegerField("Rating duration", validators=[Required(), NumberRange(min = 0)], default = 24 * 5)
    duration = IntegerField("Duration", validators=[Required(), NumberRange(min = 0)], default = 24 * 2)

    description = TextAreaField("Description")
    restrictions = TextAreaField("Restrictions")

class GameCreateForm(Form):
    title = TextField("Game title", validators=[Required(), Length(max=128)])

class GameEditForm(Form):
    title = TextField("Game title", validators=[Required(), Length(max=128)])
    description = TextAreaField("Description", validators=[Required()])
    technology = TextAreaField("Technlogoy used")
    help = TextAreaField("Help / Controls")

    def get(self, name):
        return getattr(self, "score_" + name + "_enabled")

# Adds fields "dynamically" (which score categories are enabled?)
for c in RATING_CATEGORIES:
    setattr(GameEditForm, "score_" + c + "_enabled", BooleanField(c.title()))

class GameAddScreenshotForm(Form):
    url = TextField("URL", validators = [Required(), URL()])
    caption = TextField("Caption", validators = [Required()])

class GameAddTeamMemberForm(Form):
    username = TextField("Username:", validators = [Required(), UsernameExists()])

from models import GamePackage

class GameAddPackageForm(Form):
    url = TextField("URL", validators = [Required(), URL()])
    type = SelectField("Type", choices = [
        ("web",          GamePackage.typeString("web")),
        ("linux",        GamePackage.typeString("linux")),
        ("linux32",      GamePackage.typeString("linux32")),
        ("linux64",      GamePackage.typeString("linux64")),
        ("windows",      GamePackage.typeString("windows")),
        ("windows64",    GamePackage.typeString("windows64")),
        ("mac",          GamePackage.typeString("mac")),
        ("source",       GamePackage.typeString("source")),
        ("git",          GamePackage.typeString("git")),
        ("svn",          GamePackage.typeString("svn")),
        ("hg",           GamePackage.typeString("hg")),
        ("combi",        GamePackage.typeString("combi")),
        ("love",         GamePackage.typeString("love")),
        ("blender",      GamePackage.typeString("blender")),
        ("unknown",      GamePackage.typeString("unknown"))])

class RateGameForm(Form):
    score = IntegerField("Overall rating", validators=[Required(), NumberRange(min=0, max=10)], default = 5)
    # score_CATEGORY = IntegerField("Category rating", validators=[Required(), NumberRange(min=0, max=10)], default = 5)
    note = TextAreaField("Additional notes", validators=[Optional()])

    def get(self, name):
        return getattr(self, "score" if name in (None, "overall") else ("score_" + name))

for x in models.rating.RATING_CATEGORIES:
    setattr(RateGameForm, "score_" + x, IntegerField(x.capitalize() + " rating",
        validators=[Required(), NumberRange(min=0, max=10)], default = 5))

class WriteComment(Form):
    text = TextAreaField("Comment", validators=[Required(), Length(max=65535)])

class TeamFinderFilter(Form):
    need_programmer = BooleanField("Programmer", default = True)
    need_gamedesigner = BooleanField("Game Designer", default = True)
    need_2dartist = BooleanField("2D Artist", default = True)
    need_3dartist = BooleanField("3D Artist", default = True)
    need_composer = BooleanField("Composer", default = True)
    need_sounddesigner = BooleanField("Sound Designer", default = True)

    show_teamed = BooleanField("people with a team")
    show_empty = BooleanField("people w/o abilities set", default = True)

    order = SelectField("Sort by", choices = [
        ("abilities", "Ability match"),
        ("username", "Username"),
        ("location", "Location")
    ], default = "abilities")

class SettingsForm(Form):
    ability_programmer = BooleanField("Programming")
    ability_gamedesigner = BooleanField("Game Design")
    ability_2dartist = BooleanField("Graphics / 2D Art")
    ability_3dartist = BooleanField("Modelling / 3D Art")
    ability_composer = BooleanField("Composing")
    ability_sounddesigner = BooleanField("Sound Design")
    abilities_extra = TextField("Detailed abilities")
    location = TextField("Location")
    real_name = TextField("Real Name")
    about = TextAreaField("About me")
    website = TextField("Website / Blog")
    avatar = TextField("Avatar URL", validators=[Optional(), URL()])

    old_password = PasswordField("Old Password", validators=[Optional()])
    new_password = PasswordField("New Password", validators=[Optional(), Length(min=8, message = "Please enter a password of at least 8 characters.")])
    new_password2 = PasswordField("New Password, again", validators=[EqualTo("new_password", "Passwords do not match.")])

    email = EmailField("Email", validators=[
        Optional(),
        Email(message = "The email address you entered is invalid.")])

    pm_mode = SelectField("Allow PM", choices = [
        ("email", "show my address"),
        ("form", "use email form"),
        ("disabled", "disable email")
    ], default = "form")

    notify_new_jam = BooleanField("when a jam is announced")
    notify_jam_start = BooleanField("when a jam I participate in starts")
    notify_jam_finish = BooleanField("when a jam I participate in finishes")
    notify_game_comment = BooleanField("when someone comments on a game of mine")
    notify_team_invitation = BooleanField("when someone invites me to a team")

    notify_newsletter = BooleanField("send me newsletters")

class ParticipateForm(Form):
    show_in_finder = BooleanField("Show me in the team finder")

class CancelParticipationForm(Form):
    confirm = BooleanField("I understand that, please cancel my participation", validators = [Required()])

class LeaveTeamForm(Form):
    confirm = BooleanField("I understand that, and want to leave the team", validators = [Required()])

class TeamSettingsForm(Form):
    name = TextField("Team Name", validators=[Required()])
    description = TextAreaField("Description")
    livestreams = TextAreaField("Livestreams")
    irc = TextField("IRC Channel")

class InviteForm(Form):
    username = TextField("Username", validators=[Required()])

class AdminWriteAnnouncement(Form):
    subject = TextField("Subject", validators=[Required()])
    message = TextAreaField("Content", validators=[Required()])

class AdminUserForm(Form):
    username = TextField("Username", validators=[
        Not(MatchesRegex("[^0-9a-zA-Z\-_]"), message = "Your username contains invalid characters. Only use alphanumeric characters, dashes and underscores."),
        Length(min=3, max=80, message="You have to enter a username of 3 to 80 characters length.")])
    avatar = TextField("Avatar URL", validators=[Optional(), URL()])
    email = EmailField("Email", validators=[
        Optional(),
        Email(message = "The email address you entered is invalid.")])

########NEW FILE########
__FILENAME__ = comment
# -*- coding: utf-8 -*-

from flamejam import app, db
from datetime import datetime

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text)
    posted = db.Column(db.DateTime)
    game_id = db.Column(db.Integer, db.ForeignKey('game.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    def __init__(self, text, game, user):
        self.text = text
        self.game = game
        self.user = user
        self.posted = datetime.utcnow()

    def __repr__(self):
        return '<Comment %r>' % self.id


########NEW FILE########
__FILENAME__ = game
# -*- coding: utf-8 -*-

from flamejam import app, db
from flamejam.utils import get_slug, average, average_non_zero
from flamejam.models.gamescreenshot import GameScreenshot
from flamejam.models.rating import Rating, RATING_CATEGORIES
from flask import url_for
from datetime import datetime

class Game(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(128))
    slug = db.Column(db.String(128))
    created = db.Column(db.DateTime)
    description = db.Column(db.Text)
    technology = db.Column(db.Text)
    help = db.Column(db.Text)
    is_deleted = db.Column(db.Boolean, default = False)
    has_cheated = db.Column(db.Boolean, default = False)

    jam_id = db.Column(db.Integer, db.ForeignKey('jam.id'))
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'))
    ratings = db.relationship('Rating', backref = 'game', lazy = "subquery")
    comments = db.relationship('Comment', backref='game', lazy = "subquery")
    packages = db.relationship('GamePackage', backref='game', lazy = "subquery")
    screenshots = db.relationship('GameScreenshot', backref='game', lazy = "subquery")

    # score_CATEGORY_enabled = db.Column(db.Boolean, default = True)

    def __init__(self, team, title):
        self.team = team
        self.jam = team.jam
        self.title = title
        self.slug = get_slug(title)
        self.created = datetime.utcnow()

    def __repr__(self):
        return '<Game %r>' % self.title

    def destroy(self):
        # destroy all ratings, comments, packages, screenshots
        for rating in self.ratings:
            db.session.delete(rating)
        for comment in self.comments:
            db.session.delete(comment)
        for package in self.packages:
            db.session.delete(package)
        for screenshot in self.screenshots:
            db.session.delete(screenshot)
        db.session.delete(self)

    def url(self, **values):
        return url_for("show_game", jam_slug = self.jam.slug, game_id = self.id, **values)

    @property
    def screenshotsOrdered(self):
        return sorted(self.screenshots, lambda s1, s2: int(s1.index - s2.index))

    @property
    def score(self):
        if self.has_cheated:
            return -10

        return average([r.score for r in self.ratings if not r.user.is_deleted]) or 0

    def feedbackAverage(self, category):
        if category in (None, "overall"):
            return self.score
        return average_non_zero([r.get(category) for r in self.ratings])

    @property
    def rank(self):
        jam_games = list(self.jam.games.all())
        jam_games.sort(key="score", reverse=True)
        return jam_games.index(self) + 1

    @property
    def numberRatings(self):
        return len(self.ratings)

    @property
    def ratingCategories(self):
        return [c for c in RATING_CATEGORIES if getattr(self, "score_" + c + "_enabled")]

    def getRatingByUser(self, user):
        return Rating.query.filter_by(user_id=user.id).first()

# Adds fields "dynamically" (which score categories are enabled?)
for c in RATING_CATEGORIES:
    setattr(Game, "score_" + c + "_enabled", db.Column(db.Boolean, default = True))

########NEW FILE########
__FILENAME__ = gamepackage
# -*- coding: utf-8 -*-

from flamejam import app, db
from flask import Markup

PACKAGE_TYPES = {
    "web":           ("Web link (Flash etc.)", "Web"),
    "linux":         ("Binaries: Linux 32/64-bit", "Linux"),
    "linux32":       ("Binaries: Linux 32-bit", "Linux32"),
    "linux64":       ("Binaries: Linux 64-bit", "Linux64"),
    "windows":       ("Binaries: Windows", "Windows"),
    "windows64":     ("Binaries: Windows 64-bit", "Windows64"),
    "mac":           ("Binaries: MacOS Application", "MacOS"),
    "source":        ("Source: package", "Source"),
    "git":           ("Source: Git repository", "git"),
    "svn":           ("Source: SVN repository", "svn"),
    "hg":            ("Source: HG repository", "hg"),
    "combi":         ("Combined package: Linux + Windows + Source (+ more, optional)", "Combined"),
    "love":          ("Love package", ".love"),
    "blender":       ("Blender file", ".blend"),
    "unknown":       ("Other", "other")
}

class GamePackage(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    url = db.Column(db.String(255))
    game_id = db.Column(db.Integer, db.ForeignKey("game.id"))
    type = db.Column(db.Enum(
        "web",      # Flash, html5, js...
        "linux",    # Linux binaries (e.g. *.tar.gz)
        "linux32",  # Linux32 binaries (e.g. *.tar.gz)
        "linux64",  # Linux64 binaries (e.g. *.tar.gz)
        "windows",  # Windows binaries (e.g. *.zip, *.exe)
        "windows64",# Windows64 binaries (e.g. *.zip, *.exe)
        "mac",      # MacOS application packages
        "combi",    # Linux + Windows + Source (and more, optional)
        "love",     # Löve packages
        "blender",  # Blender save file (*.blend)
        "source",   # Source package (e.g. *.zip or *.tar.gz)
        "git",      # Version control repository: GIT
        "svn",      # Version control repository: SVN
        "hg",       # Version control repository: HG
        "unknown"))

    def __init__(self, game, url, type = "unknown"):
        self.url = url
        self.type = type
        self.game = game

    def getLink(self):
        return Markup('<a href="%s" target="_blank">%s</a>' % (self.url, GamePackage.typeString(self.type)))

    def getLinkShort(self):
        return Markup('<a href="%s">%s</a>' % (self.url, GamePackage.typeStringShort(self.type)))

    def __repr__(self):
        return "<GamePackage %r>" % self.id

    @staticmethod
    def typeString(type):
        if type in PACKAGE_TYPES:
            return PACKAGE_TYPES[type][0]
        return "Unknown"

    @staticmethod
    def typeStringShort(type):
        if type in PACKAGE_TYPES:
            return PACKAGE_TYPES[type][1]
        return "Unknown"

    @staticmethod
    def packageTypes():
        return PACKAGE_TYPES

    @staticmethod
    def compare(left, right):
        x = right.getTotalScore() - left.getTotalScore()
        if x > 0:
            return 1
        elif x < 0:
            return -1
        else:
            return 0


########NEW FILE########
__FILENAME__ = gamescreenshot
# -*- coding: utf-8 -*-

from flamejam import app, db

class GameScreenshot(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    url = db.Column(db.String(255))
    caption = db.Column(db.Text)
    index = db.Column(db.Integer) # 0..n-1
    game_id = db.Column(db.Integer, db.ForeignKey("game.id"))

    def __init__(self, url, caption, game):
        self.game = game
        self.url = url
        self.caption = caption
        self.index = len(self.game.screenshots) - 1

    def __repr__(self):
        return "<GameScreenshot %r>" % self.id

    def move(self, x):
        all = self.game.screenshotsOrdered

        old = self.index
        new = self.index + x

        if new >= len(all):
            new = len(all) - 1
        if new < 0:
            new = 0

        if new != self.index:
            other = all[new]
            self.index = new
            other.index = old

########NEW FILE########
__FILENAME__ = invitation
# -*- coding: utf-8 -*-

from flamejam import app, db
from flamejam.models.jam import JamStatusCode
from flask import url_for

class Invitation(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    team_id = db.Column(db.Integer, db.ForeignKey("team.id"))
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))

    def __init__(self, team, user):
        self.team = team
        self.user = user

    def url(self, **values):
        return url_for("invitation", id = self.id, _external = True, **values)

    def canAccept(self):
        return self.team.jam.getStatus().code <= JamStatusCode.PACKAGING

    def accept(self):
        self.team.userJoin(self.user)
        db.session.delete(self)
        db.session.commit()

    def decline(self):
        db.session.delete(self)
        db.session.commit()


########NEW FILE########
__FILENAME__ = jam
# -*- coding: utf-8 -*-

from flamejam import app, db, mail
from flamejam.utils import get_slug
from flamejam.filters import formattime, humandelta
from flamejam.models import Game, GamePackage
from datetime import datetime, timedelta
from flask import url_for, Markup, render_template
from flask.ext.mail import Message
from random import shuffle
from smtplib import SMTPRecipientsRefused

class Jam(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(128), unique=True)
    title = db.Column(db.String(128), unique=True)
    theme = db.Column(db.String(128))
    announced = db.Column(db.DateTime) # Date on which the jam was announced
    start_time = db.Column(db.DateTime) # The jam starts at this moment
    team_limit = db.Column(db.Integer) # 0 = no limit
    games = db.relationship('Game', backref="jam", lazy = "subquery")
    participations = db.relationship("Participation", backref = "jam", lazy = "subquery")
    teams = db.relationship("Team", backref = "jam", lazy = "subquery")

    description = db.Column(db.Text)
    restrictions = db.Column(db.Text)

    registration_duration = db.Column(db.Integer) # hours
    packaging_duration = db.Column(db.Integer) # hours
    rating_duration = db.Column(db.Integer) # hours
    duration = db.Column(db.Integer) # hours

    # last notification that was sent, e.g. 0 = announcement, 1 = registration, (see status codes)
    last_notification_sent = db.Column(db.Integer, default = -1)

    def __init__(self, title, start_time, duration = 48, team_limit = 0, theme = ''):
        self.title = title
        self.slug = get_slug(title)
        self.start_time = start_time
        self.duration = duration
        self.registration_duration = 24 * 14
        self.packaging_duration = 24 * 1
        self.rating_duration = 24 * 5
        self.announced = datetime.utcnow()
        self.theme = theme
        self.team_limit = team_limit

    @property
    def participants(self):
        return [r.user for r in self.participations]

    @property
    def end_time(self):
        return self.start_time + timedelta(hours = self.duration)

    @property
    def packaging_deadline(self):
        return self.end_time + timedelta(hours = self.packaging_duration)

    @property
    def rating_end(self):
        return self.packaging_deadline + timedelta(hours = self.rating_duration)

    @property
    def registration_start(self):
        return self.start_time - timedelta(hours = self.registration_duration)

    def __repr__(self):
        return '<Jam %r>' % self.slug

    def getStatus(self):
        now = datetime.utcnow()
        if self.registration_start > now:
            return JamStatus(JamStatusCode.ANNOUNCED, self.start_time)
        elif self.start_time > now:
            return JamStatus(JamStatusCode.REGISTRATION, self.start_time)
        elif self.end_time > now:
            return JamStatus(JamStatusCode.RUNNING, self.end_time)
        elif self.packaging_deadline > now:
            return JamStatus(JamStatusCode.PACKAGING, self.packaging_deadline)
        elif self.rating_end > now:
            return JamStatus(JamStatusCode.RATING, self.rating_end)
        else:
            return JamStatus(JamStatusCode.FINISHED, self.end_time)

    def url(self, **values):
        return url_for('jam_info', jam_slug = self.slug, **values)

    def gamesFilteredByPackageTypes(self, filters):
        games = Game.query.filter_by(is_deleted=False).filter_by(jam_id=self.id)
        if filters == set():
            games = games
        elif 'packaged' in filters:
            games = games.join(GamePackage)
        else:
            games = games.filter(GamePackage.type.in_(filters)).join(GamePackage)
        return games.all()

    def gamesByScore(self, filters=set()):
        e = self.gamesFilteredByPackageTypes(filters)
        e.sort(key = Game.score.fget, reverse = True)
        return e

    def gamesByTotalRatings(self, filters=set()):
        e = self.gamesFilteredByPackageTypes(filters)
        e.sort(key = Game.numberRatings.fget)
        return e

    @property
    def showTheme(self):
        return self.getStatus().code >= JamStatusCode.RUNNING and self.theme

    @property
    def showRatings(self):
        return self.getStatus().code == JamStatusCode.FINISHED

    def getLink(self):
        s = '<a class="jam" href="%s">%s</a>' % (self.url(), self.title)
        if self.showTheme:
            s += ' <span class="theme">%s</span>' % self.theme
        return Markup(s)

    def sendAllNotifications(self):
        last = -1
        for n in range(self.last_notification_sent + 1, self.getStatus().code + 1):
            if self.sendNotification(n): last = n
        return last

    def sendNotification(self, n):
        if not JamStatusCode.ANNOUNCED <= n <= JamStatusCode.FINISHED: return False

        kwargs = {}

        if n == JamStatusCode.ANNOUNCED:
            template = "announcement"
            notify = "new_jam"
            subject = "Jam announced: " + self.title
        elif n == JamStatusCode.REGISTRATION:
            template = "registration_start"
            notify = "new_jam"
            subject = "Registrations for " + self.title + " now open"
        elif n == JamStatusCode.RUNNING:
            template = "start"
            notify = "jam_start"
            subject = self.title + " starts now!"
        elif n == JamStatusCode.PACKAGING:
            template = "packaging_start"
            notify = "jam_finish"
            subject = self.title + " is over"
        elif n == JamStatusCode.RATING:
            template = "rating_start"
            notify = "jam_finish"
            subject = "Rating for " + self.title + " starts now"
        elif n == JamStatusCode.FINISHED:
            template = "finished"
            notify = "jam_finish"
            subject = "Rating for " + self.title + " finished - Winners"
            kwargs = { "games": self.gamesByScore()[:3] }

        if n >= JamStatusCode.RUNNING and n != JamStatusCode.RATING:
            users = [r.user for r in self.participations]
        else:
            from flamejam.models import User
            users = User.query.all()

        # Set this first because we might send for longer than a minute at which point the
        # next tick will come around.
        self.last_notification_sent = n
        db.session.commit()

        subject = app.config["LONG_NAME"] + ": " + subject

        with mail.connect() as conn:
            for user in users:
                if getattr(user, "notify_" + notify):
                    body = render_template("emails/jam/" + template + ".txt", recipient=user, jam=self, **kwargs)
                    sender = app.config['MAIL_DEFAULT_SENDER']
                    recipients = [user.email]
                    message = Message(subject=subject, sender=sender, body=body, recipients=recipients)
                    try:
                        conn.send(message)
                    except SMTPRecipientsRefused:
                        pass
        return True

    @property
    def livestreamTeams(self):
        return [t for t in self.teams if t.livestream]

class JamStatusCode(object):
    ANNOUNCED    = 0
    REGISTRATION = 1
    RUNNING      = 2
    PACKAGING    = 3
    RATING       = 4
    FINISHED     = 5

class JamStatus(object):
    def __init__(self, code, time):
        self.code = code
        self.time = time

    def __repr__(self):
        t = formattime(self.time)
        d = humandelta(datetime.utcnow(), self.time)
        if self.code == JamStatusCode.ANNOUNCED:
            return "Announced for {0}".format(t)
        elif self.code == JamStatusCode.REGISTRATION:
            return "Registrations until {0}".format(t)
        elif self.code == JamStatusCode.RUNNING:
            return "Running until {0} ({1} left)".format(t, d)
        elif self.code == JamStatusCode.PACKAGING:
            return "Packaging until {0} ({1} left)".format(t, d)
        elif self.code == JamStatusCode.RATING:
            return "Rating until {0} ({1} left)".format(t, d)
        elif self.code == JamStatusCode.PACKAGING:
            return "Finished since {0}".format(t)

        return "Database error."

########NEW FILE########
__FILENAME__ = participation
# -*- coding: utf-8 -*-

from flamejam import app, db
from datetime import datetime

class Participation(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    team_id = db.Column(db.Integer, db.ForeignKey("team.id"))
    jam_id = db.Column(db.Integer, db.ForeignKey("jam.id"))
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    show_in_finder = db.Column(db.Boolean, default = True)
    registered = db.Column(db.DateTime)

    def __init__(self, user, jam, show_in_finder = True):
        self.user = user
        self.jam = jam
        self.show_in_finder = show_in_finder
        self.registered = datetime.utcnow()


########NEW FILE########
__FILENAME__ = rating
# -*- coding: utf-8 -*-

from flamejam import app, db
from datetime import datetime

RATING_CATEGORIES = ("gameplay", "graphics", "audio", "innovation", "story", "technical", "controls", "humor")

class Rating(db.Model):
    """The rating of a category is set to 0 to disable this category. It is
    then not counted into the average score.
    """

    id = db.Column(db.Integer, primary_key=True)
    score = db.Column(db.SmallInteger)
    # score_CATEGORY = db.Column(db.SmallInteger, default = 5)
    text = db.Column(db.Text)
    posted = db.Column(db.DateTime)
    game_id = db.Column(db.Integer, db.ForeignKey('game.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    def __init__(self, game, user, text, score):
        self.game = game
        self.user = user
        self.text = text
        self.posted = datetime.utcnow()
        self.score = score

    def __repr__(self):
        return '<Rating %r:%r>' % (self.id, self.score)

    def set(self, category, value):
        if category in (None, "overall"):
            self.score = value
        else:
            setattr(self, "score_" + category, value)

    def get(self, category):
        return self.score if category in (None, "overall") else getattr(self, "score_" + category)

# Add fields "dynamically"
for c in RATING_CATEGORIES:
    setattr(Rating, "score_" + c, db.Column(db.SmallInteger, default = 5))


########NEW FILE########
__FILENAME__ = team
# -*- coding: utf-8 -*-

from flamejam import app, db, mail
from flamejam.models import Invitation, Game
from flask import url_for, render_template

class Team(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    jam_id = db.Column(db.Integer, db.ForeignKey("jam.id"))
    name = db.Column(db.String(80))

    description = db.Column(db.Text)
    livestreams = db.Column(db.Text) # list of livestreams, one URL per file
    irc = db.Column(db.String(128))

    participations = db.relationship("Participation", backref = "team", lazy = "subquery")
    invitations = db.relationship("Invitation", backref = "team", lazy = "subquery")
    games = db.relationship("Game", backref = "team", lazy = "subquery")

    def __init__(self, user, jam):
        self.jam = jam
        self.userJoin(user)
        self.name = user.username + "'s team"

    @property
    def members(self):
        return [r.user for r in self.participations]

    @property
    def game(self):
        return self.games[0] if self.games else None

    @property
    def isSingleTeam(self):
        return len(self.participations) == 1

    def url(self, **values):
        return url_for("jam_team", jam_slug = self.jam.slug, team_id = self.id, **values)

    def userJoin(self, user):
        r = user.getParticipation(self.jam)
        if not r:
            # register user, but do not create automatic team, we don't need
            # that anyway
            user.joinJam(self.jam, False)
        elif r in self.participations:
            return # user is already in this team
        elif r.team and r.team != self:
            r.team.userLeave(user)

        r.team = self
        db.session.commit()

    def userLeave(self, user):
        r = user.getParticipation(self.jam)

        if r.team != self:
            return # not in this team, nevermind ;)

        if self.isSingleTeam:
            # only user in team, we can destroy this team
            self.destroy()

        r.team = None
        db.session.commit()

    def destroy(self):
        # also destroy all the games, invitations
        for game in self.games:
            game.destroy()
        for invitation in self.invitations:
            db.session.delete(invitation)
        db.session.delete(self)

    @property
    def numberMembersAndInvitations(self):
        return len(self.members) + len(self.invitations)

    def canInvite(self, user):
        return user in self.members and (self.jam.team_limit == 0 or self.jam.team_limit > self.numberMembersAndInvitations)

    def getInvitation(self, user):
        return Invitation.query.filter_by(user_id = user.id, team_id = self.id).first()

    def inviteUser(self, user, sender): # sender: which user sent the invitation
        if not user.notify_team_invitation:
            return None

        if self.getInvitation(user):
            i = self.getInvitation(user) # already invited
        else:
            i = Invitation(self, user)
            db.session.add(i)
            db.session.commit()
            body = render_template("emails/invitation.txt", team=self, sender=sender, recipient=user, invitation=i)
            mail.send_message(subject=app.config["LONG_NAME"] +": You have been invited to " + self.name, recipients=[user.email], body=body)
        return i


########NEW FILE########
__FILENAME__ = user
# -*- coding: utf-8 -*-

from flamejam import app, db, login_manager
from flamejam.utils import hash_password, verify_password, findLocation
from flamejam.models import Participation, Team, Game
from flask import url_for, Markup
from datetime import datetime
from hashlib import md5
import scrypt

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True)
    password = db.Column(db.LargeBinary())
    token = db.Column(db.BigInteger, nullable=True, default=None)
    email = db.Column(db.String(191), unique=True)
    new_email = db.Column(db.String(191), unique=True)
    is_admin = db.Column(db.Boolean, default=False)
    is_verified = db.Column(db.Boolean)
    is_deleted = db.Column(db.Boolean, default = False)
    registered = db.Column(db.DateTime)
    ratings = db.relationship('Rating', backref='user', lazy = "dynamic")
    comments = db.relationship('Comment', backref='user', lazy = "dynamic")
    invitations = db.relationship("Invitation", backref = "user", lazy = "dynamic")
    participations = db.relationship("Participation", backref = db.backref("user", lazy="joined"), lazy = "subquery")

    ability_programmer = db.Column(db.Boolean)
    ability_gamedesigner = db.Column(db.Boolean)
    ability_2dartist = db.Column(db.Boolean)
    ability_3dartist = db.Column(db.Boolean)
    ability_composer = db.Column(db.Boolean)
    ability_sounddesigner = db.Column(db.Boolean)
    abilities_extra = db.Column(db.String(128))
    location = db.Column(db.String(128))
    location_coords = db.Column(db.String(128))
    location_display = db.Column(db.String(128))
    location_flag = db.Column(db.String(16), default = "unknown")
    real_name = db.Column(db.String(128))
    about = db.Column(db.Text)
    website = db.Column(db.String(128))
    avatar = db.Column(db.String(128))

    pm_mode = db.Column(db.Enum("email", "form", "disabled"), default = "form")

    notify_new_jam = db.Column(db.Boolean, default = True)
    notify_jam_start = db.Column(db.Boolean, default = True)
    notify_jam_finish = db.Column(db.Boolean, default = True)
    notify_game_comment = db.Column(db.Boolean, default = True)
    notify_team_invitation = db.Column(db.Boolean, default = True)
    notify_newsletter = db.Column(db.Boolean, default = True)

    def __init__(self, username, password, email, is_admin = False, is_verified = False):
        self.username = username
        self.password = hash_password(password)
        self.email = email
        self.new_email = email
        self.is_admin = is_admin
        self.is_verified = is_verified
        self.registered = datetime.utcnow()

    def __repr__(self):
        return '<User %r>' % self.username

    def get_id(self):
        return self.id

    def is_active(self):
        return self.is_verified

    def is_anonymous(self):
        return False

    def is_authenticated(self):
        return True

    def getVerificationHash(self):
        # combine a few properties, hash it
        # take first 16 chars for simplicity
        # make it email specific
        hash = scrypt.hash(str(self.username) + str(self.new_email), app.config['SECRET_KEY'])
        return hash.encode('hex')[:16]

    def getResetToken(self):
        # combine a few properties, hash it
        # take first 16 chars for simplicity
        hash = scrypt.hash(str(self.token), app.config['SECRET_KEY'])
        return hash.encode('hex')[:16]

    def ratedGame(self, game):
        return self.ratings.filter_by(game = game).first() != None

    def getRatingCount(self, jam):
        i = 0
        for r in self.ratings:
            if r.game.jam == jam:
                i += 1
        return i

    @property
    def games(self):
        g = []
        for p in self.participations:
            if p.team:
                for game in p.team.games:
                    if not game.is_deleted:
                        g.append(game)

        import operator
        g.sort(key = operator.attrgetter("created"))

        return g

    def url(self, **values):
        return url_for('show_user', username = self.username, **values)

    def getAvatar(self, size = 32):
        if self.avatar:
            return self.avatar.replace("%s", str(size))
        return "//gravatar.com/avatar/{0}?s={1}&d=identicon".format(md5(self.email.lower()).hexdigest(), size)

    def setLocation(self, location):
        if not location:
            self.location = ""
            self.location_display = ""
            self.location_coords = ""
            self.location_flag = "unknown"
            return True

        new_loc, new_coords, new_flag = findLocation(location)
        if not new_loc:
            return False
        self.location = location
        self.location_display = new_loc
        self.location_coords = new_coords
        self.location_flag = new_flag
        return True

    def getLocation(self):
        return Markup('<span class="location"><span class="flag %s"></span> <span class="city">%s</span></span>' % (self.location_flag, self.location_display or "n/a"))

    def getLink(self, class_ = "", real = True, avatar = True):
        if self.is_deleted:
            return Markup('<span class="user deleted">[DELETED]</span>')

        s = 16
        if self.is_admin:
            class_ += " admin"

        link = ''
        link += '<a class="user {0}" href="{1}">'.format(class_, self.url())
        if avatar:
            link += '<img width="{0}" height="{0}" src="{1}" class="icon"/> '.format(s, self.getAvatar(s))
        link += '<span class="name"><span class="username">{0}</span>'.format(self.username)
        link += u' <span class="real">({0})</span>'.format(self.real_name) if self.real_name and real else ''
        link += '</span></a>'

        return Markup(link)

    @property
    def abilities(self):
        a = []
        if self.ability_programmer:
            a.append("Programming")
        if self.ability_gamedesigner:
            a.append("Game Design")
        if self.ability_2dartist:
            a.append("Graphics / 2D Art")
        if self.ability_3dartist:
            a.append("Modelling / 3D Art")
        if self.ability_composer:
            a.append("Composing")
        if self.ability_sounddesigner:
            a.append("Sound Design")
        return a

    def abilityString(self):
        a = ", ".join(self.abilities)
        if self.abilities_extra:
            a += '<div class="ability-extra">' + self.abilities_extra + '</div>'
        return a

    def getParticipation(self, jam):
        return Participation.query.filter_by(user_id = self.id, jam_id = jam.id).first()

    def getTeam(self, jam):
        p = self.getParticipation(jam)
        return p.team if p and p.team else None

    def inTeam(self, team):
        return self in team.members

    def canRate(self, game):
        return not self.inTeam(game.team)

    def canEdit(self, game):
        return self.inTeam(game.team)

    def joinJam(self, jam, generateTeam = True):
        p = Participation(self, jam)
        db.session.add(p)
        db.session.commit() # need to commit so the team does not register us automatically

        if generateTeam:
            self.generateTeam(jam)
        else:
            db.session.commit()

    def generateTeam(self, jam):
        t = Team(self, jam)
        db.session.add(t)
        db.session.commit()

    def leaveJam(self, jam):
        # leave team
        if self.getTeam(jam):
            self.getTeam(jam).userLeave(self) #  will destroy the team if then empty

        # delete registration
        if self.getParticipation(jam):
            db.session.delete(self.getParticipation(jam))

    def numberOfGames(self):
        return len(self.games)

    @property
    def openInvitations(self):
        invitations = []
        for invitation in self.invitations:
            if invitation.canAccept():
                invitations.append(invitation)
        return invitations

# we need this so Flask-Login can load a user into a session
@login_manager.user_loader
def load_user(user_id):
    user = User.query.filter_by(id=user_id).first()
    if user:
        return user
    else:
        return None

########NEW FILE########
__FILENAME__ = utils
from flamejam import app
import random
import scrypt
import requests
import re

def average(list):
    return sum(list) / float(len(list)) if len(list) else 0

def average_non_zero(list):
    list = [x for x in list if x != 0]
    return average(list)

def get_slug(s):
    s = s.lower()
    s = re.sub(r"[\s_+]+", "-", s)
    s = re.sub("[^a-z0-9\-]", "", s)
    s = re.sub("-+", "-", s)
    return s

def findLocation(loc):
    try:
        r = requests.get("http://maps.googleapis.com/maps/api/geocode/json?address=%s&sensor=false&language=en" % loc)
        c = r.json()["results"][0]
        a = c["address_components"]

        city = ""
        state = ""
        region = ""
        flag = ""
        coords = "%s,%s" % (c["geometry"]["location"]["lat"], c["geometry"]["location"]["lng"])

        for comp in a:
            if comp["types"][0] == "locality": city = comp["long_name"]
            elif comp["types"][0] == "administrative_area_level_1": region = comp["long_name"]
            elif comp["types"][0] == "country":
                state = comp["long_name"]
                flag = comp["short_name"].lower()

        first = state

        if state == "United States" and region:
            first += ", " + region

        if city:
            first += ", " + city
        return first, coords, flag
    except:
        return None, None, None

def randstr(length):
    return ''.join(chr(random.randint(0,255)) for i in range(length))

def hash_password(password, maxtime=0.5, datalength=256):
    salt = randstr(datalength)
    hashed_password = scrypt.encrypt(salt, password.encode('utf-8'), maxtime=maxtime)
    return bytearray(hashed_password)

def verify_password(hashed_password, guessed_password, maxtime=300):
    try:
        scrypt.decrypt(hashed_password, guessed_password.encode('utf-8'), maxtime)
        return True
    except scrypt.error as e:
        print "scrypt error: %s" % e    # Not fatal but a necessary measure if server is under heavy load
        return False

def get_current_jam():
    from flamejam.models import Jam, JamStatusCode
    next = None
    previous = None
    for jam in Jam.query.all():
        if jam.getStatus().code == JamStatusCode.RUNNING:
            return jam
        elif jam.getStatus().code <= JamStatusCode.RUNNING:
            if not next or next.start_time > jam.start_time:
                next = jam
        else:
            if not previous or previous.end_time < jam.end_time:
                previous = jam

    return next or previous

########NEW FILE########
__FILENAME__ = account
import sys
from random import randint

from flamejam import app, db, mail
from flamejam.models import User
from flamejam.utils import hash_password, verify_password
from flamejam.forms import UserLogin, UserRegistration, ResetPassword, NewPassword, SettingsForm, ContactUserForm
from flask import render_template, redirect, flash, url_for, current_app, session, request, abort, Markup
from flask.ext.login import login_required, login_user, logout_user, current_user
from flask.ext.principal import AnonymousIdentity, Identity, UserNeed, identity_changed, identity_loaded, Permission, RoleNeed, PermissionDenied

@app.route('/login', methods=['GET', 'POST'])
def login():
    login_form = UserLogin()
    register_form = UserRegistration()

    if login_form.validate_on_submit():
        username = login_form.username.data
        password = login_form.password.data
        remember_me = login_form.remember_me.data
        user = User.query.filter_by(username=username).first()
        if login_user(user, remember_me):
            flash("You were logged in.", "success")
            if user.invitations.count():
                flash(Markup('You have %s team invitations - click <a href="%s">here</a> to view them.' % (user.invitations.count(), url_for("invitations"))), "info")
            return redirect(request.args.get("next") or url_for('index'))

            # Tell Flask-Principal the identity changed
            identity_changed.send(current_app._get_current_object(),
                                  identity=Identity(user.id))
        else:
            flash("Login failed, user not validated", "error")
            return redirect(url_for("verify_status", username=username))

    elif register_form.validate_on_submit():
        username = register_form.username.data.strip()
        password = register_form.password.data
        email = register_form.email.data

        new_user = User(username, password, email)

        body = render_template("emails/account/verification.txt", recipient = new_user, email_changed = False)
        mail.send_message(subject="Welcome to " + app.config["LONG_NAME"] + ", " + username, recipients=[new_user.email], body=body)

        db.session.add(new_user)
        db.session.commit()

        flash("Your account has been created, confirm your email to verify.", "success")
        return redirect(url_for('verify_status', username = username))
    return render_template('account/login.html', login_form = login_form, register_form = register_form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("You were logged out.", "success")

    # Remove session keys set by Flask-Principal
    for key in ('identity.name', 'identity.auth_type'):
        session.pop(key, None)

    # Tell Flask-Principal the user is anonymous
    identity_changed.send(current_app._get_current_object(),
                          identity=AnonymousIdentity())

    return redirect(url_for('index'))

# we need this so Flask Principal knows what to do when a user is loaded
@identity_loaded.connect_via(app)
def on_identity_loaded(sender, identity):
    # Set the identity user object
    identity.user = current_user

    # Add the UserNeed to the identity
    if hasattr(current_user, 'id'):
        identity.provides.add(UserNeed(current_user.id))

    if hasattr(current_user, 'is_admin'):
        if current_user.is_admin:
            identity.provides.add(RoleNeed('admin'))

@app.route('/reset', methods=['GET', 'POST'])
def reset_request():
    if current_user.is_authenticated():
        flash("You are already logged in.", "info")
        return redirect(url_for("index"))
    error = None
    form = ResetPassword()
    if form.validate_on_submit():
        # thanks to the UsernameValidator we cam assume the username exists
        user = User.query.filter_by(username=form.username.data).first()
        user.token = randint(0, sys.maxint)
        db.session.commit()

        body = render_template("emails/account/reset_password.txt", recipient=user)
        mail.send_message(subject=app.config["LONG_NAME"] + ": Reset your password", recipients=[user.email], body=body)

        flash("Your password has been reset, check your email.", "success")
    return render_template('account/reset_request.html', form=form, error=error)

@app.route('/reset/<username>/<token>', methods=['GET', 'POST'])
def reset_verify(username, token):
    user = User.query.filter_by(username=username).first_or_404()
    if user.token == None:
        flash("%s's account has not requested a password reset." % user.username.capitalize(), "error")
        return redirect(url_for('index'))
    if user.getResetToken() != token:
        flash("This does not seem to be a valid reset link, if you reset your account multiple times make sure you are using the link in the last email you received!", "error")
        return redirect(url_for('index'))
    form = NewPassword()
    error = None
    if form.validate_on_submit():
        # null the reset token
        user.token = None
        # set the new password
        user.password = hash_password(form.password.data)
        db.session.commit()
        flash("Your password was updated and you can login with it now.", "success")
        return redirect(url_for('login'))
    return render_template('account/reset_newpassword.html', user = user, form = form, error = error)


@app.route('/verify/', methods=["POST", "GET"])
def verify_send():
    if request.method == 'GET':
        return redirect(url_for('index'))

    username = request.form.get('username', "")
    user = User.query.filter_by(username = username).first_or_404()

    if user.is_verified:
        flash("%s's account is already validated." % user.username.capitalize(), "info")
        return redirect(url_for('index'))

    body=render_template("emails/account/verification.txt", recipient=user)
    mail.send_message(subject="Welcome to " + app.config["LONG_NAME"] + ", " + username, recipients=[user.new_email], body=body)

    flash("Verification has been resent, check your email", "success")
    return redirect(url_for('verify_status', username=username))

@app.route('/verify/<username>', methods=["GET"])
def verify_status(username):
    submitted = request.args.get('submitted', None)
    user = User.query.filter_by(username = username).first_or_404()

    if user.is_verified:
        flash("%s's account is already validated." % user.username.capitalize(), "info")
        return redirect(url_for('index'))

    return render_template('misc/verify_status.html', submitted=submitted, username=username)

@app.route('/verify/<username>/<verification>', methods=["GET"])
def verify(username, verification):
    user = User.query.filter_by(username = username).first_or_404()

    if user.is_verified:
        flash("%s's account is already validated." % user.username.capitalize(), "success")
        return redirect(url_for('index'))

    # verification success
    if verification == user.getVerificationHash():
        user.is_verified = True
        user.email = user.new_email
        db.session.commit()

        flash("Your email has been confirmed, you may now login")
        return redirect(url_for('login'))

    # verification failure
    else:
        return redirect(url_for('verify_status', username=username, submitted=True))

@app.route('/profile')
@login_required
def profile():
    return render_template("account/profile.html", user = current_user)

@app.route('/users/<username>/')
def show_user(username):
    user = User.query.filter_by(is_deleted = False, username = username).first_or_404()
    return render_template("account/profile.html", user = user)

@app.route('/users/<username>/contact/', methods = ("POST", "GET"))
@login_required
def contact_user(username):
    user = User.query.filter_by(is_deleted = False, username = username).first_or_404()
    if user == current_user or user.pm_mode == "disabled":
        abort(403)

    form = ContactUserForm()

    if form.validate_on_submit():
        message = form.message.data
        body = render_template("emails/account/message.txt", recipient=user, sender=current_user, message=message)
        mail.send_message(subject=app.config["LONG_NAME"] + ": New message from " + current_user.username,
            recipients=[user.email], reply_to=current_user.email, body=body)
        flash("Message successfully sent", "success")

    return render_template("account/contact.html", user = user, form = form)

@app.route('/settings', methods = ["POST", "GET"])
@login_required
def settings():
    user = current_user
    form = SettingsForm(obj=user)
    logout = False

    if form.validate_on_submit():
        user.ability_programmer = form.ability_programmer.data
        user.ability_gamedesigner = form.ability_gamedesigner.data
        user.ability_2dartist = form.ability_2dartist.data
        user.ability_3dartist = form.ability_3dartist.data
        user.ability_composer = form.ability_composer.data
        user.ability_sounddesigner = form.ability_sounddesigner.data
        user.abilities_extra = form.abilities_extra.data
        user.real_name = form.real_name.data
        user.about = form.about.data
        user.website = form.website.data
        user.pm_mode = form.pm_mode.data
        user.avatar = form.avatar.data
        user.notify_new_jam = form.notify_new_jam.data
        user.notify_jam_start = form.notify_jam_start.data
        user.notify_jam_finish = form.notify_jam_finish.data
        user.notify_game_comment = form.notify_game_comment.data
        user.notify_team_invitation = form.notify_team_invitation.data
        user.notify_newsletter = form.notify_newsletter.data

        if user.location != form.location.data and form.location.data:
            if user.setLocation(form.location.data):
                flash("Location was set to: " + user.location_display, "success")
            else:
                flash("Could not find the location you entered.", "error")
        if not form.location.data:
            user.setLocation("")

        if form.old_password.data and form.new_password.data and form.new_password2.data:
            if not verify_password(user.password, form.old_password.data):
                flash("Your password is incorrect. The password was not changed.", "error")
            else:
                user.password = hash_password(form.new_password.data)
                flash("Your password was changed", "success")

        if user.email != form.email.data and form.email.data:
            user.new_email = form.email.data
            user.is_verified = False

            same_email = User.query.filter_by(email = user.new_email).all()
            if not(len(same_email) == 0 or (len(same_email) == 1 and same_email[0] == user)):
                flash("This email address is already in use by another account.", "error")
                return redirect(url_for("settings"))

            body = render_template("emails/account/verification.txt", recipient=user, email_changed = True)
            mail.send_message(subject=app.config["LONG_NAME"] + ": eMail verification", recipients=[user.new_email], body=body)

            logout = True
            flash("Your email address has changed. Please check your inbox for the verification.", "info")

        db.session.commit()
        flash("Your settings were saved.", "success")

        if logout:
            return redirect(url_for("logout"))
        else:
            return redirect(url_for("settings"))

    return render_template('account/settings.html', form = form)

########NEW FILE########
__FILENAME__ = admin
from flamejam import app, db, admin_permission, mail
from flamejam.utils import get_slug
from flamejam.models import User, Jam, Game
from flamejam.forms import JamDetailsForm, AdminWriteAnnouncement, AdminUserForm
from flask import render_template, redirect, url_for, request, flash
from flask.ext.mail import Message
from datetime import datetime
from smtplib import SMTPRecipientsRefused

@app.route("/admin")
def admin_index():
    return redirect(url_for('admin_users'))

@app.route("/admin/users")
@admin_permission.require()
def admin_users():
    users = User.query.all()
    return render_template("admin/users.html", users = users)

@app.route("/admin/users/form", methods = ["POST"])
@admin_permission.require()
def admin_users_form():
    users = []
    for field in request.form:
        if field[:5] == "user-" and request.form[field] == "on":
            i = field[5:]
            users.append(User.query.filter_by(id = i).first_or_404())

    for user in users:
        if request.form["submit"] == "Toggle Deleted":
            user.is_deleted = not user.is_deleted
        if request.form["submit"] == "Toggle Admin":
            user.is_admin = not user.is_admin
        if request.form["submit"] == "Toggle Verified":
            user.is_verified = not user.is_verified
            if user.is_verified and user.new_email:
                user.email = user.new_email

    db.session.commit()

    flash(str(len(users)) + " users were changed", "success")

    return redirect(url_for("admin_users"))

@app.route("/admin/games/form", methods = ["POST"])
@admin_permission.require()
def admin_games_form():
    games = []
    for field in request.form:
        if field[:5] == "game-" and request.form[field] == "on":
            i = field[5:]
            games.append(Game.query.filter_by(id = i).first_or_404())

    for game in games:
        if request.form["submit"] == "Toggle Deleted":
            game.is_deleted = not game.is_deleted
        if request.form["submit"] == "Toggle Cheated":
            game.has_cheated = not game.has_cheated

    db.session.commit()

    flash(str(len(games)) + " games were changed", "success")

    return redirect(url_for("admin_games"))

@app.route("/admin/user/<username>", methods = ["POST", "GET"])
@admin_permission.require()
def admin_user(username):
    user = User.query.filter_by(username = username).first_or_404()
    form = AdminUserForm(obj=user)

    if form.validate_on_submit():
        other = User.query.filter_by(username = form.username.data).first()
        if other and other.id != user.id:
            flash("A user with that username already exists. Please choose another.", "error")
        else:
            user.username = form.username.data
            user.avatar = form.avatar.data
            user.email = form.email.data
            db.session.commit()
            flash("User changed successfully.", "success")
            return redirect(url_for("admin_user", username = user.username))

    return render_template("admin/user.html", user = user, form = form)

@app.route("/admin/jams")
@admin_permission.require()
def admin_jams():
    return render_template("admin/jams.html", jams = Jam.query.all())

@app.route("/admin/jams/<int:id>/send/<int:n>", methods = ["POST", "GET"])
@admin_permission.require()
def admin_jam_notification(id, n):
    jam = Jam.query.filter_by(id = id).first_or_404()
    jam.sendNotification(n)
    flash("Notification sent.", "success")
    return redirect(url_for("admin_jam", id = id))

@app.route("/admin/jams/<int:id>", methods = ["POST", "GET"])
@app.route("/admin/jams/create/", methods = ["POST", "GET"])
@admin_permission.require()
def admin_jam(id = 0):
    mode = "create"
    jam = None

    if id != 0:
        jam = Jam.query.filter_by(id = id).first_or_404()
        mode = "edit"

    form = JamDetailsForm(obj=jam)

    if form.validate_on_submit():
        slug_jam = Jam.query.filter_by(slug = get_slug(form.title.data.strip())).first()
        if slug_jam and slug_jam != jam:
            flash("A jam with a similar title already exists (slug conflict).", "error")
        else:
            if mode == "create":
                jam = Jam("", datetime.utcnow())
                db.session.add(jam)

            form.populate_obj(jam)
            jam.title.strip()
            jam.slug = get_slug(jam.title)
            jam.theme.strip()
            jam.description.strip()
            jam.restrictions.strip()

            db.session.commit()
            flash("Jam settings have been saved.", "success")
            return redirect(url_for("admin_jam", id = jam.id))

    return render_template("admin/jam.html", id = id, mode = mode, jam = jam, form = form)

@app.route("/admin/games")
@admin_permission.require()
def admin_games():
    return render_template("admin/games.html", jams = Jam.query.all())

@app.route("/admin/games/<int:id>/<flag>")
@admin_permission.require()
def admin_game_flag(id, flag):
    game = Game.query.filter_by(id=id).first_or_404()
    if flag == "deleted":
        flash("Toggled deleted flag")
        game.is_deleted = not game.is_deleted
        db.session.commit()
    if flag == "cheated":
        flash("Toggled cheated flag")
        game.has_cheated = not game.has_cheated
        db.session.commit()
    return redirect(url_for('admin_games'))

@app.route("/admin/announcement", methods = ["GET", "POST"])
@admin_permission.require()
def admin_announcement():
    form = AdminWriteAnnouncement()

    if form.validate_on_submit():
        with mail.connect() as conn:
            for user in User.query.filter_by(notify_newsletter = True).all():
                body = render_template("emails/newsletter.txt", recipient=user, message=form.message.data)
                subject = app.config["LONG_NAME"] + " Newsletter: " + form.subject.data
                sender = app.config['MAIL_DEFAULT_SENDER']
                recipients = [user.email]
                message = Message(subject=subject, sender=sender, body=body, recipients=recipients)
                try:
                    conn.send(message)
                except SMTPRecipientsRefused:
                    pass
        flash("Your announcement has been sent to the users.")

    return render_template("admin/announcement.html", form = form)

@app.route("/admin/users/delete/<username>")
@admin_permission.require()
def admin_user_delete(username):
    u = User.query.filter_by(username = username).first()
    if not u: return "User not found"

    for r in u.participations:
        u.leaveJam(r.jam)
    for i in u.invitations:
        db.session.delete(i)
    db.session.delete(u)
    db.session.commit()

    return "User " + username + " deleted"

########NEW FILE########
__FILENAME__ = ajax
from flamejam import app, markdown_object
from flamejam.models import User
from flask import request, render_template

@app.route("/ajax/markdown", methods = ["POST"])
def ajax_markdown():
    return str(markdown_object(request.form["input"]))

@app.route("/ajax/map-user/<username>/")
def ajax_mapuser(username):
    user = User.query.filter_by(username = username).first()
    return render_template("ajax/mapuser.html", user = user)

########NEW FILE########
__FILENAME__ = game
from flamejam import app, db, mail
from flamejam.utils import get_slug
from flamejam.models import Jam, Game, User, Comment, GamePackage, \
    GameScreenshot, JamStatusCode, Rating
from flamejam.models.rating import RATING_CATEGORIES
from flamejam.forms import WriteComment, GameEditForm, GameAddScreenshotForm, \
    GameAddPackageForm, GameAddTeamMemberForm, GameCreateForm, RateGameForm
from flask import render_template, url_for, redirect, flash, request, abort
from flask.ext.login import login_required, current_user

@app.route("/jams/<jam_slug>/create-game/", methods = ("GET", "POST"))
@login_required
def create_game(jam_slug):
    jam = Jam.query.filter_by(slug = jam_slug).first_or_404()

    r = current_user.getParticipation(jam)
    if not r or not r.team:
        flash("You cannot create a game without participating in the jam.", category = "error")
        return redirect(jam.url())
    if r.team.game:
        flash("You already have a game.")
        return redirect(r.team.game.url())

    enabled = (JamStatusCode.RUNNING <= jam.getStatus().code <= JamStatusCode.PACKAGING)

    form = GameCreateForm(request.form, obj = None)
    if enabled and form.validate_on_submit():
        game = Game(r.team, form.title.data)
        db.session.add(game)
        db.session.commit()
        return redirect(url_for("edit_game", jam_slug = jam_slug, game_id = game.id))

    return render_template("jam/game/create.html", jam = jam, enabled = enabled, form = form)

@app.route("/jams/<jam_slug>/<game_id>/edit/", methods = ("GET", "POST"))
@login_required
def edit_game(jam_slug, game_id):
    jam = Jam.query.filter_by(slug = jam_slug).first_or_404()
    game = Game.query.filter_by(is_deleted = False, id = game_id).first_or_404()

    if not game or not current_user in game.team.members:
        abort(403)

    form = GameEditForm(request.form, obj = game)
    package_form = GameAddPackageForm()
    screenshot_form = GameAddScreenshotForm()

    if form.validate_on_submit():
        slug = get_slug(form.title.data)
        # if not jam.games.filter_by(slug = slug).first() in (game, None):
            # flash("A game with a similar title already exists. Please choose another title.", category = "error")
        # else:
        #form.populate_obj(game) this breaks dynamic stuff below

        game.title = form.title.data
        game.description = form.description.data
        game.technology = form.technology.data
        game.help = form.help.data

        if game.jam.getStatus().code < 4:
            for c in RATING_CATEGORIES:
                setattr(game, "score_" + c + "_enabled", form.get(c).data)

        game.slug = get_slug(game.title)
        db.session.commit()
        flash("Your settings have been applied.", category = "success")
        return redirect(game.url())

    if package_form.validate_on_submit():
        s = GamePackage(game, package_form.url.data, package_form.type.data)
        db.session.add(s)
        db.session.commit()
        flash("Your package has been added.", "success")
        return redirect(request.url)

    if screenshot_form.validate_on_submit():
        s = GameScreenshot(screenshot_form.url.data, screenshot_form.caption.data, game)
        db.session.add(s)
        db.session.commit()
        flash("Your screenshot has been added.", "success")
        return redirect(request.url)

    return render_template("jam/game/edit.html", jam = jam, game = game,
        form = form, package_form = package_form, screenshot_form = screenshot_form)

@app.route('/edit/package/<id>/<action>/')
@login_required
def game_package_edit(id, action):
    if not action in ("delete"):
        abort(404)

    p = GamePackage.query.filter_by(id = id).first_or_404()
    if not current_user in p.game.team.members:
        abort(403)

    if action == "delete":
        db.session.delete(p)
    db.session.commit()
    return redirect(url_for("edit_game", jam_slug = p.game.jam.slug, game_id = p.game.id))

@app.route('/edit/screenshot/<id>/<action>/')
@login_required
def game_screenshot_edit(id, action):
    if not action in ("up", "down", "delete"):
        abort(404)

    s = GameScreenshot.query.filter_by(id = id).first_or_404()
    if not current_user in s.game.team.members:
        abort(403)

    if action == "up":
        s.move(-1)
    elif action == "down":
        s.move(1)
    elif action == "delete":
        db.session.delete(s)
        i = 0
        for x in s.game.screenshotsOrdered:
            x.index = i
            i += 1
    db.session.commit()
    return redirect(url_for("edit_game", jam_slug = s.game.jam.slug, game_id = s.game.id))

@app.route('/jams/<jam_slug>/<game_id>/', methods = ("POST", "GET"))
def show_game(jam_slug, game_id):
    comment_form = WriteComment()
    jam = Jam.query.filter_by(slug = jam_slug).first_or_404()
    game = Game.query.filter_by(is_deleted = False, id = game_id).filter_by(jam = jam).first_or_404()

    if current_user.is_authenticated() and comment_form.validate_on_submit():
        comment = Comment(comment_form.text.data, game, current_user)
        db.session.add(comment)
        db.session.commit()

        # notify the team
        for user in game.team.members:
            if user.notify_game_comment:
                body = render_template("emails/comment.txt", recipient=user, comment=comment)
                mail.send_message(subject=current_user.username + " commented on " + game.title, recipients=[user.email], body=body)

        flash("Your comment has been posted.", "success")
        return redirect(game.url())

    rating = Rating.query.filter_by(game_id = game.id, user_id = current_user.get_id()).first()
    return render_template('jam/game/info.html', game = game, form = comment_form, rating = rating)

@app.route("/jams/<jam_slug>/<game_id>/rate/", methods = ("GET", "POST"))
@login_required
def rate_game(jam_slug, game_id):
    jam = Jam.query.filter_by(slug = jam_slug).first_or_404()
    game = Game.query.filter_by(jam_id=jam.id, is_deleted=False, id=game_id).first_or_404()

    form = RateGameForm()
    if jam.getStatus().code != JamStatusCode.RATING:
        flash("This jam is not in the rating phase. Sorry, but you cannot rate right now.", "error")
        return redirect(game.url())

    if current_user in game.team.members:
        flash("You cannot rate on your own game. Go rate on one of these!", "warning")
        return redirect(url_for("jam_games", jam_slug = jam.slug))

    # Allow only users who participate in this jam to vote.
    if not current_user in jam.participants:
        flash("You cannot rate on this game. Only participants are eligible for vote.", "error")
        return redirect(url_for("jam_games", jam_slug = jam.slug))

    rating = Rating.query.filter_by(game_id=game.id, user_id=current_user.id).first()
    if rating:
        flash("You are editing your previous rating of this game.", "info")

    if form.validate_on_submit():
        new = rating == None
        if not rating:
            rating = Rating(game, current_user, form.note.data, form.score.data)
            db.session.add(rating)
        else:
            rating.text = form.note.data

        for c in ["overall"] + game.ratingCategories:
            rating.set(c, form.get(c).data)

        db.session.commit()
        flash("Your rating has been " + ("submitted" if new else "updated") + ".", "success")
        return redirect(url_for("jam_games", jam_slug = jam.slug))

    elif rating:
        for c in ["overall"] + game.ratingCategories:
            form.get(c).data = rating.get(c)
        form.note.data = rating.text

    return render_template('jam/game/rate.html', jam = jam, game = game, form = form)

########NEW FILE########
__FILENAME__ = index
from flamejam import app
from flamejam.utils import get_current_jam
from flamejam.models import Jam
from flask import render_template, url_for, redirect

@app.route("/")
def index():
    jam = get_current_jam()
    return redirect(jam.url() if jam else url_for("home"))

@app.route("/home")
def home():
    return render_template("index.html", all_jams = Jam.query.all())

########NEW FILE########
__FILENAME__ = jams
from flamejam import app, db
from flamejam.models import Jam, JamStatusCode, GamePackage
from flamejam.forms import ParticipateForm, CancelParticipationForm, TeamFinderFilter
from flask import render_template, url_for, redirect, flash, request
from flask.ext.login import login_required, current_user

@app.route('/jams/')
def jams():
    return render_template("misc/search.html", jams = Jam.query.all())

@app.route('/jams/<jam_slug>/', methods=("GET", "POST"))
def jam_info(jam_slug):
    jam = Jam.query.filter_by(slug = jam_slug).first_or_404()
    return render_template('jam/info.html', jam = jam)

@app.route('/jams/<jam_slug>/countdown', methods=("GET", "POST"))
def countdown(jam_slug):
    jam = Jam.query.filter_by(slug = jam_slug).first_or_404()
    return render_template('misc/countdown.html', jam = jam)

@app.route('/jams/<jam_slug>/participate/', methods = ["POST", "GET"])
@login_required
def jam_participate(jam_slug):
    jam = Jam.query.filter_by(slug = jam_slug).first_or_404()
    user = current_user

    if jam.getStatus().code > JamStatusCode.PACKAGING:
        flash("You cannot register for participation in a jam after it has finished or is in rating phase.", "error")
        return redirect(jam.url())

    if jam.getStatus().code < JamStatusCode.REGISTRATION:
        flash("You cannot register for participation before the registration started.", "error")
        return redirect(jam.url())

    if user.getParticipation(jam):
        flash("You already participate in this jam.", "warning")
        return redirect(jam.url())

    form = ParticipateForm()

    if form.validate_on_submit():
        user.joinJam(jam)
        user.getParticipation(jam).show_in_finder = form.show_in_finder.data
        db.session.commit()
        flash("You are now registered for this jam.", "success")
        return redirect(jam.url())

    return render_template('jam/participate.html', jam = jam, form = form)

@app.route('/jams/<jam_slug>/cancel-participation/', methods = ["POST", "GET"])
@login_required
def jam_cancel_participation(jam_slug):
    jam = Jam.query.filter_by(slug = jam_slug).first_or_404()

    if jam.getStatus().code > JamStatusCode.PACKAGING:
        flash("You cannot unregister from a jam after it has finished or is in rating phase.", "error")
        return redirect(jam.url())

    form = CancelParticipationForm()

    if form.validate_on_submit():
        current_user.leaveJam(jam)
        db.session.commit()
        flash("You are now unregistered from this jam.", "success")
        return redirect(jam.url())

    return render_template('jam/cancel_participation.html', jam = jam, form = form)

@app.route('/jams/<jam_slug>/games/')
def jam_games(jam_slug):
    jam = Jam.query.filter_by(slug = jam_slug).first_or_404()
    filters = set(request.args['filter'].split(' ')) if 'filter' in request.args else set()
    games = jam.gamesByScore(filters) if jam.showRatings else jam.gamesByTotalRatings(filters)
    return render_template('jam/games.html', jam = jam, games = games, filters = filters, package_types = GamePackage.packageTypes(), typeStringShort = GamePackage.typeStringShort)

@app.route('/jams/<jam_slug>/participants/')
def jam_participants(jam_slug):
    jam = Jam.query.filter_by(slug = jam_slug).first_or_404()
    return render_template('jam/participants.html', jam = jam)

@app.route('/jams/<jam_slug>/team_finder/toggle/')
def jam_toggle_show_in_finder(jam_slug):
    jam = Jam.query.filter_by(slug = jam_slug).first_or_404()
    r = current_user.getParticipation(jam)
    if not r: abort(404)
    r.show_in_finder = not r.show_in_finder
    db.session.commit()
    flash("You are now %s in the team finder for the jam \"%s\"." % ("shown" if r.show_in_finder else "hidden", jam.title), "success")
    return redirect(jam.url())

@app.route('/jams/<jam_slug>/team_finder/', methods=("GET", "POST"))
def jam_team_finder(jam_slug):
    jam = Jam.query.filter_by(slug = jam_slug).first_or_404()
    form = TeamFinderFilter()
    l = []
    for r in jam.participations:
        u = r.user
        if (not form.show_teamed.data) and r.team and (not r.team.isSingleTeam):
            continue # don't show teamed people

        if not r.show_in_finder:
            continue

        matches = 0

        if form.need_programmer.data and u.ability_programmer: matches += 1
        if form.need_gamedesigner.data and u.ability_gamedesigner: matches += 1
        if form.need_2dartist.data and u.ability_2dartist: matches += 1
        if form.need_3dartist.data and u.ability_3dartist: matches += 1
        if form.need_composer.data and u.ability_composer: matches += 1
        if form.need_sounddesigner.data and u.ability_sounddesigner: matches += 1

        if matches == 0 and not form.show_empty.data: continue

        l.append((r, matches))

    if form.order.data == "abilities":
        l.sort(key = lambda pair: pair[1], reverse = True)
    elif form.order.data == "location":
        l.sort(key = lambda pair: pair[0].user.location)
    else: # username
        l.sort(key = lambda pair: pair[0].user.username)

    return render_template('jam/team_finder.html', jam = jam, form = form, results = l)

########NEW FILE########
__FILENAME__ = misc
import traceback

from flask.ext.mail import Message
from flask.ext.principal import PermissionDenied
from smtplib import SMTPRecipientsRefused

from flamejam import app, db, mail, cache
from flamejam.models import Jam, User, Team, Game, JamStatusCode
from flamejam.utils import get_current_jam
from flask import render_template, request, url_for, redirect, flash, jsonify
from werkzeug.exceptions import *

@app.errorhandler(404)
@app.errorhandler(403)
def error(e):
    return render_template("error.html", error = e), e.code

@app.errorhandler(PermissionDenied)
def error_permission(e):
    return error(Forbidden())

@app.errorhandler(500)
def application_error(e):
    msg = Message("[%s] Exception Detected: %s" % (app.config['SHORT_NAME'], e.message),
                    recipients=app.config['ADMINS'])
    msg_contents = [
        'Traceback:',
        '='*80,
        traceback.format_exc(),
        '\n',
        'Request Information:',
        '='*80
    ]
    environ = request.environ
    environkeys = sorted(environ.keys())
    for key in environkeys:
        msg_contents.append('%s: %s' % (key, environ.get(key)))

    msg.body = '\n'.join(msg_contents) + '\n'

    mail.send(msg)
    return error(InternalServerError())

@app.errorhandler(SMTPRecipientsRefused)
def invalid_email(exception):
    flash("Invalid email address.", "error")
    return redirect(url_for('login'))

@app.route("/map")
@app.route("/map/<mode>")
@app.route("/map/<mode>/<int:id>")
def map(mode = "users", id = 0):
    users = []
    extra = None
    if mode == "jam":
        extra = Jam.query.filter_by(id = id).first_or_404()
        users = extra.participants
    elif mode == "user":
        extra = User.query.filter_by(id = id).first_or_404()
        users = [extra]
    elif mode == "team":
        extra = Team.query.filter_by(id = id).first_or_404()
        users = extra.members
    else:
        mode = "users"
        users = User.query.all()

    x = 0
    for user in users:
        if user.location_coords:
            x += 1

    return render_template("misc/map.html", users = users, mode = mode, extra = extra, x = x)

@app.route("/search")
def search():
    q = request.args.get("q", "")
    if not q:
        return redirect(url_for("index"))
    like = "%" + q + "%"

    jams = Jam.query.filter(db.or_(
        Jam.title.like(like))).all()

    games = Game.query.filter_by(is_deleted = False).filter(
        db.or_(Game.description.like(like),
               Game.title.like(like))).all()

    users = User.query.filter_by(is_deleted = False).filter(
        User.username.like(like)).all()

    total = len(jams) + len(games) + len(users)

    if len(jams) == total == 1:
        return redirect(jams[0].url())
    elif len(games) == total == 1:
        return redirect(games[0].url())
    elif len(users) == total == 1:
        return redirect(users[0].url())

    return render_template("misc/search.html", q = q, jams = jams, games = games, users = users)

@app.route('/contact')
def contact():
    return render_template('misc/contact.html')

@app.route('/rules')
@app.route('/rulez')
def rules():
    return render_template('misc/rules.html')

@app.route('/stats')
@app.route('/statistics')
def statistics():
    # collect all the data
    stats = {}

    stats["total_jams"] = Jam.query.count()
    stats["total_users"] = User.query.count()

    all_jam_users = 0
    most_users_per_jam = 0
    most_users_jam = None
    most_games_per_jam = 0
    most_games_jam = None
    biggest_team_size = 0
    biggest_team_game = None

    for jam in Jam.query.all():
        users = 0
        for game in jam.games:
            if not game.is_deleted:
                teamsize = len(game.team.members) # for the author
                users += teamsize

                if teamsize > biggest_team_size:
                    biggest_team_size = teamsize
                    biggest_team_game = game

        if users > most_users_per_jam:
            most_users_per_jam = users
            most_users_jam = jam

        games = Game.query.filter_by(is_deleted = False).count()

        if games > most_games_per_jam:
            most_games_per_jam = games
            most_games_jam = jam

        all_jam_users += users

    all_games = Game.query.filter_by(is_deleted = False).all()
    finished_games = []
    for game in all_games:
        if game.jam.getStatus() == JamStatusCode.FINISHED:
            finished_games.append(game)
    finished_games.sort(key = Game.score.fget, reverse = True)
    stats["best_games"] = finished_games[:3]

    user_most_games = User.query.filter_by(is_deleted = False).all()
    user_most_games.sort(key = User.numberOfGames, reverse = True)
    stats["user_most_games"] = user_most_games[:3]

    if stats["total_jams"]: # against division by zero
        stats["average_users"] = all_jam_users * 1.0 / stats["total_jams"];
    else:
        stats["average_users"] = 0
    stats["most_users_per_jam"] = most_users_per_jam
    stats["most_users_jam"] = most_users_jam

    stats["total_games"] = Game.query.filter_by(is_deleted=False).count()
    if stats["total_jams"]: # against division by zero
        stats["average_games"] = stats["total_games"] * 1.0 / stats["total_jams"]
    else:
        stats["average_games"] = 0
    stats["most_games_per_jam"] = most_games_per_jam
    stats["most_games_jam"] = most_games_jam

    if stats["average_games"]: # against division by zero
        stats["average_team_size"] = stats["average_users"] * 1.0 / stats["average_games"]
    else:
        stats["average_team_size"] = 0
    stats["biggest_team_size"] = biggest_team_size
    stats["biggest_team_game"] = biggest_team_game


    #Best rated games
    #User with most games

    return render_template('misc/statistics.html', stats = stats)

@app.route('/faq')
@app.route('/faq/<page>')
def faq(page = ""):
    if page.lower() == "packaging":
        return render_template('misc/faq_packaging.html')
    return render_template('misc/faq.html')

@app.route('/links')
def links():
    return render_template('misc/links.html')

@app.route('/subreddit')
def subreddit():
    return redirect("http://www.reddit.com/r/bacongamejam")

@app.route('/current_jam_info')
def current_jam_info():
    jam = get_current_jam()
    return jsonify(slug=jam.slug,
                   title=jam.title,
                   announced=str(jam.announced),
                   start_time=str(jam.start_time),
                   duration=jam.duration,
                   team_limit=jam.team_limit,
                   participants_count=len(jam.participations),
                   teams_count=len(jam.teams))

@app.route('/site_info')
def site_info():
    stats = {}
    stats["total_jams"] = db.session.query(db.func.count(Jam.id)).first()[0]
    stats["total_users"] = db.session.query(db.func.count(User.id)).first()[0]
    stats["total_games"] = db.session.query(db.func.count(not Game.is_deleted)).first()[0]
    return jsonify(total_jams=stats["total_jams"],
                   total_users=stats["total_users"],
                   total_games=stats["total_games"],
                   subreddit=url_for('subreddit', _external=True),
                   rules=url_for('rules', _external=True))

@app.route('/tick')
def tick():
    """This function is meant to be called regularly by a cronjob.
    Its purpose is to send out mails and do site maitenance even
    when there are no visitors.

    Your cronjob could look like this:
    * * * * * /usr/bin/curl http://domain.tld/tick
    """

    msg = ""

    # Send Notifications
    for jam in Jam.query.all():
        n = jam.sendAllNotifications()
        if n >= 0:
            msg += "sending notification " + str(n) + " on jam " + jam.slug + "\n"

    # Delete unverified users
    for user in User.query.filter_by(is_verified = False):
        # new_mail is set on users that *changed* their address
        if not user.new_email and user.registered < datetime.utcnow() - timedelta(days=7):
            msg += "deleted user " + user.username + " for being unverified too long\n"
            db.session.delete(user)

    # Remove invitations after game rating has started
    for jam in Jam.query.all():
        if jam.getStatus().code >= JamStatusCode.RATING:
            for team in jam.teams:
                for i in team.invitations:
                    msg += "deleted invitation " + str(i.id) + " on jam " + jam.slug + " - jam rating has started\n"
                    db.session.delete(i)

    db.session.commit()

    return msg

########NEW FILE########
__FILENAME__ = team
from flamejam import app, db
from flamejam.models import Jam, Team, Invitation, JamStatusCode, User
from flamejam.forms import TeamSettingsForm, InviteForm, LeaveTeamForm
from flask import render_template, url_for, redirect, flash, request, abort
from flask.ext.login import login_required, current_user

@app.route('/jams/<jam_slug>/team/<int:team_id>/')
def jam_team(jam_slug, team_id):
    jam = Jam.query.filter_by(slug = jam_slug).first_or_404()
    team = Team.query.filter_by(id = team_id, jam_id = jam.id).first_or_404()
    return render_template('jam/team/info.html', jam = jam, team = team)

@app.route('/jams/<jam_slug>/team/')
@login_required
def jam_current_team(jam_slug):
    jam = Jam.query.filter_by(slug = jam_slug).first_or_404()
    user = current_user
    r = user.getParticipation(jam)
    if r:
        return redirect(r.team.url())
    else:
        return redirect(jam.url())

@app.route('/jams/<jam_slug>/team/settings', methods = ["POST", "GET"])
@login_required
def team_settings(jam_slug):
    jam = Jam.query.filter_by(slug = jam_slug).first_or_404()
    if jam.getStatus().code >= JamStatusCode.RATING:
        flash("The jam rating has started, so changes to the team are locked.", "error")
        return redirect(jam.url())

    r = current_user.getParticipation(jam)
    if not r or not r.team: abort(404)
    team = r.team

    settings_form = TeamSettingsForm(obj=team)
    invite_form = InviteForm()
    invite_username = None

    if settings_form.validate_on_submit():
        settings_form.populate_obj(team)
        team.livestreams.strip()
        db.session.commit()
        flash("The team settings were saved.", "success")
        return redirect(team.url())
    elif invite_form.validate_on_submit():
        invite_username = invite_form.username.data

    if "invite" in request.args:
        invite_username = request.args["invite"]

    if invite_username:
        if not team.canInvite(current_user):
            flash("You cannot invite someone right now.", "error")
            abort(403)

        user = User.query.filter_by(username = invite_username, is_deleted = False).first()
        if not user:
            flash("Could not find user: %s" % invite_username, "error")
        elif user.inTeam(team):
            flash("User %s is already in this team." % invite_username, "warning")
        elif team.getInvitation(user):
            flash("User %s is already invited." % user.username, "warning")
        else:
            i = team.inviteUser(user, current_user)
            flash("Invited user %s." % invite_username, "success")

        return redirect(url_for("team_settings", jam_slug = team.jam.slug))

    return render_template('jam/team/edit.html', team = team, invite_form = invite_form, settings_form = settings_form)

@app.route('/invitations/')
@login_required
def invitations():
    return render_template("account/invitations.html", user = current_user)

@app.route('/invitations/<int:id>', methods = ["POST", "GET"])
@app.route('/invitations/<int:id>/<action>', methods = ["POST", "GET"])
@login_required
def invitation(id, action = ""):
    invitation = Invitation.query.filter_by(id = id).first_or_404()
    team = invitation.team

    if team.jam.getStatus().code >= JamStatusCode.RATING:
        flash("The jam rating has started, so changes to the team are locked.", "error")
        return redirect(team.url())

    if action == "accept":
        if current_user != invitation.user: abort(403)
        invitation.accept()
        flash("You have accepted the invitation.", "success")
        return redirect(team.url())
    elif action == "decline":
        if current_user != invitation.user: abort(403)
        invitation.decline()
        flash("You have declined the invitation.", "success")
        return redirect(team.url())
    elif action == "revoke":
        if current_user not in team.members: abort(403)
        flash("You have revoked the invitation for %s." % invitation.user.username, "success")
        db.session.delete(invitation)
        db.session.commit()
        return redirect(url_for("team_settings", jam_slug = team.jam.slug))
    else:
        if current_user != invitation.user and current_user not in team.members:
            abort(403)
        return render_template("jam/invitation.html", invitation=invitation)

@app.route("/jams/<jam_slug>/leave-team/", methods = ("POST", "GET"))
@login_required
def leave_team(jam_slug):
    jam = Jam.query.filter_by(slug = jam_slug).first_or_404()

    if jam.getStatus().code >= JamStatusCode.RATING:
        flash("The jam rating has started, so changes to the team are locked.", "error")
        return redirect(jam.url())

    user = current_user
    r = user.getParticipation(jam)

    if not r or not r.team:
        flash("You are in no team.", "info")
        return redirect(jam.url())

    if jam.getStatus().code > JamStatusCode.PACKAGING:
        flash("You cannot change the team after packaging is finished.", "error")
        return redirect(jam.url())

    team = r.team
    form = LeaveTeamForm()

    if form.validate_on_submit():
        team.userLeave(user)
        user.generateTeam(jam)
        db.session.commit()
        flash("You left the team.", "success")
        return redirect(jam.url())

    return render_template("jam/team/leave.html", jam = jam, form = form, team = team)



########NEW FILE########
__FILENAME__ = runserver
from flamejam import app

app.run(host="0.0.0.0")

########NEW FILE########
__FILENAME__ = init-db
#
# This is a short script to kill all tables and add a single admin, given as parameters.
# It should be run from a virtualenv.
#

import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from flamejam import db
from flamejam.models import User, Jam, Game, Rating, Comment, GameScreenshot
from datetime import datetime, timedelta

db.drop_all()
db.create_all()

if len(sys.argv) < 4 or len(sys.argv) >= 5 or \
        sys.argv[1] == "-h" or sys.argv[1] == "--help":
    print "Provide initial admin data using these parameters:"
    print sys.argv[0] + " <username> <password> <email>"
    exit(1)

username = sys.argv[1]
password = sys.argv[2]
email = sys.argv[3]

print "Creating user '%s' with password '%s' and email '%s'" % (username, password, email)

admin = User(username, password, email, is_admin = True, is_verified = True)
db.session.add(admin)

db.session.commit()

########NEW FILE########
__FILENAME__ = seed-db
#!/usr/bin/env python2
# -*- coding: utf-8 -*-
#
# This is a short script to kill all tables and fill them with new test data.
# It should be run from a virtualenv.
#

import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from flamejam import db
from flamejam.models import User, Jam, Game, Rating, Comment, GameScreenshot
from datetime import datetime, timedelta

# Kill everything and recreate tables
db.drop_all()
db.create_all()

# Make users
peter = User("peter", "lol", "roflomg-peter@mailinator.com")
paul = User("opatut", "lol", "opatutlol@aol.com", is_admin = True, is_verified = True)
per = User("per", "lol", "roflomg-per@mailinator.com", is_verified = True)
pablo = User("pablo", "lol", "roflomg-pablo@mailinator.com", is_verified = True)
paddy = User("paddy", u"löl", "roflomg-paddy@mailinator.com")
paddy.real_name = u"löl"

# Add users
db.session.add(peter)
db.session.add(paul)
db.session.add(per)
db.session.add(pablo)
db.session.add(paddy)

paul.setLocation("Hohenbalk")
paul.ability_programmer = True
paul.ability_gamedesigner = True
paul.ability_3dartist = True
paul.abilities_extra = u"C++, Löve/Lua, Python, Java, SVG, HTML5, JS, Blender"
per.setLocation("Thesdorfer Weg 20, Pinneberg")
pablo.setLocation("Hamburg")
paddy.setLocation("San Francisco")

# Make jams
rgj1 = Jam("BaconGameJam 01", datetime.utcnow() - timedelta(days=30))
rgj2 = Jam("BaconGameJam 2", datetime.utcnow() - timedelta(days=2))
rgj3 = Jam("BaconGameJam 3", datetime.utcnow())
loljam = Jam("Test Jam", datetime.utcnow() - timedelta(days=3))
rgj4 = Jam("BaconGameJam 4", datetime.utcnow() + timedelta(days=14))
rgj4.team_limit = 4

rgj1.theme = "Bacon"
rgj2.theme = "Zombies"
rgj3.theme = "Space"
loljam.theme = "Funny"
rgj4.theme = "HIDDEN, SHOULD NOT BE SHOWN"

# Add jams
db.session.add(rgj1)
db.session.add(rgj2)
db.session.add(rgj3)
db.session.add(loljam)
db.session.add(rgj4)

# make people participate
peter.joinJam(rgj1)
paul.joinJam(rgj1)
paddy.joinJam(rgj2)
peter.joinJam(rgj3)
paul.joinJam(rgj3)
per.joinJam(rgj3)
pablo.joinJam(rgj3)
paddy.joinJam(rgj3)
paddy.joinJam(rgj4)
paul.joinJam(rgj4)
paul.joinJam(loljam)
paddy.joinJam(loljam)
pablo.joinJam(loljam)

aTeam = paul.getTeam(rgj3)
aTeam.userJoin(pablo)

# Make games
best_game = Game(paddy.getTeam(rgj3), "Bessy the Best Game")
best_game.description = "Simply the best game"

space_game = Game(aTeam, "CloneStars - The war wars")
space_game.description = "A space shooter game."

lolgame = Game(pablo.getTeam(loljam), "Lolol")
lolgame.description = "Lol."

clone = Game(peter.getTeam(rgj3), "Shooterz")
clone.description = "I got this idea while taking a dump."

test_game = Game(per.getTeam(rgj3), "RIP VIP")

# Add games
db.session.add(best_game)
db.session.add(space_game)
db.session.add(lolgame)
db.session.add(clone)
db.session.add(test_game)

# Add screenshots
s1 = GameScreenshot("http://2.bp.blogspot.com/_gx7OZdt7Uhs/SwwanX_-API/AAAAAAAADAM/vbZbIPERdhs/s1600/Star-Wars-Wallpaper-star-wars-6363340-1024-768.jpg", "Awesome cover art", space_game)
s2 = GameScreenshot("http://images.psxextreme.com/wallpapers/ps3/star_wars___battle_1182.jpg", "Sample vehicles", space_game)
s3 = GameScreenshot("http://sethspopcorn.com/wp-content/uploads/2010/10/CloneTrooper.jpg", "Character selection screen", space_game)

db.session.add(s1)
db.session.add(s2)
db.session.add(s3)

# Make ratings
rating1 = Rating(best_game, peter, "Cool stuff", 3)
rating2 = Rating(best_game, paul, "", 10)
rating3 = Rating(space_game, paul, "Awesome space action!", 3)
rating4 = Rating(clone, paul, "Something something", 9)
rating5 = Rating(clone, paddy, "", 3)

# Add ratings
db.session.add(rating1)
db.session.add(rating2)
db.session.add(rating3)
db.session.add(rating4)
db.session.add(rating5)

# Make comments
comment1 = Comment("lol so bad", best_game, peter)
comment2 = Comment("the worst", best_game, paul)
comment3 = Comment("You don't provide a download for your game. Please add one via \"Add package\".", space_game, paul)
comment4 = Comment("I really *love* this game. It is just awesome.", space_game, paul)
comment5 = Comment("@paul Now you have a download", space_game, paddy)

# Add comments
db.session.add(comment1)
db.session.add(comment2)
db.session.add(comment3)
db.session.add(comment4)
db.session.add(comment5)

# Flood db
if "--flood" in sys.argv:
    for u in range(1000):
        user = User("user"+str(u), "lol", "lol"+str(u)+"@example.com", is_verified = True)
        user.joinJam(rgj3)
        db.session.add(user)

# Commmit it all
db.session.commit()

########NEW FILE########
